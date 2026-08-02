from __future__ import annotations

import gc
import hashlib
import json
import pathlib
import shutil
import sqlite3
import tempfile
import threading
import unittest
import warnings
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from unittest import mock

import cement_runtime.function as function_module
import cement_runtime.system as system_module
from cement_runtime import (
    Candidate,
    CompilePolicy,
    ConflictError,
    DraftEntry,
    DraftVerification,
    FallbackFailed,
    FUNCTION_ENTRY_SEAL_ABI,
    FunctionCheck,
    FunctionEntry,
    FunctionPromotionEntry,
    FunctionPromotionManifest,
    FunctionSetPromotion,
    FunctionVerification,
    InProgress,
    IntegrityError,
    NotFoundError,
    ReconciliationRequired,
    Resolved,
    ReviewRequired,
    StateError,
    System,
    ValidationError,
    VerificationReport,
    build_function,
    evaluate,
)
from cement_runtime.artifacts import (
    ARTIFACT_ABI,
    ARTIFACT_MAX_BYTES,
    build_digest,
    build_exact_lookup,
)
from cement_runtime.json_value import CANONICALIZER, canonicalize
from cement_runtime.store import SCHEMA_VERSION
from cement_runtime.system import (
    FUNCTION_MEMBERSHIP_ABI,
    FUNCTION_PROMOTION_MANIFEST_ABI,
    FUNCTION_PROMOTION_RECEIPT_ABI,
    _CurrentBuild,
    _digest_strings,
    _function_entry_seal,
    _function_receipt_hash,
    _id_list_hash,
    _membership_hash,
)


_FUNCTION_CHECK_KEYS = (
    "duplicate-input-digests",
    "abi-canonicalizer-uniform",
    "sealed-passing-reports",
    "current-promotion-receipts",
    "function-hash-matches-snapshot",
)


class Clock:
    def __init__(self, now_us: int = 1_000_000) -> None:
        self.now_us = now_us

    def __call__(self) -> int:
        return self.now_us

    def advance(self, seconds: int) -> None:
        self.now_us += seconds * 1_000_000


class FakeSource:
    def __init__(self, output=None) -> None:
        self.calls = []
        self.output = output

    def propose(self, request):
        self.calls.append(request)
        output = self.output if self.output is not None else {"echo": request.input}
        return Candidate(output=output, provenance={"model": "fake-v1"})


class BlockingSource:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def propose(self, request):
        self.entered.set()
        self.release.wait(timeout=2)
        return Candidate(output="done", provenance={})


class SystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(self.temporary.cleanup)
        self.database = str(pathlib.Path(self.temporary.name) / "cement.db")
        self.clock = Clock()
        self.source = FakeSource()
        self.system = System(
            self.database,
            candidate_source=self.source,
            clock_us=self.clock,
        )


    def _database_dump(self) -> tuple[str, ...]:
        connection = sqlite3.connect(self.database)
        try:
            return tuple(connection.iterdump())
        finally:
            connection.close()

    def register(self, *, confirmations=3, reviewers=2, span=10) -> None:
        self.system.register_operation(
            "tenant-a",
            "echo",
            policy=CompilePolicy(confirmations, reviewers, span),
        )

    def confirm(
        self,
        request_id: str,
        *,
        reviewer="alice",
        corrected=None,
        input_value=None,
    ):
        value = {"x": 1} if input_value is None else input_value
        outcome = self.system.handle(
            "tenant-a", "echo", value, request_id=request_id
        )
        self.assertIsInstance(outcome, ReviewRequired)
        proposal = self.system.get_proposal("tenant-a", outcome.proposal_id)
        self.assertEqual(proposal.proposed_output, {"echo": value})
        if corrected is None:
            return self.system.review(
                "tenant-a", outcome.proposal_id, reviewer=reviewer, decision="accept"
            )
        return self.system.review(
            "tenant-a",
            outcome.proposal_id,
            reviewer=reviewer,
            decision="correct",
            corrected_output=corrected,
        )

    def mature_and_promote(self):
        self.confirm("r1", reviewer="alice")
        self.clock.advance(5)
        self.confirm("r2", reviewer="bob")
        too_early = self.system.compile("tenant-a", "echo")
        self.assertFalse(too_early.created)
        self.assertTrue(
            any("span" in reason for reason in too_early.blocked[0]["reasons"])
        )
        self.clock.advance(5)
        self.confirm("r3", reviewer="alice")
        build = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(build.created), 1)
        report = self.system.verify("tenant-a", build.created[0])
        self.assertTrue(report.passed)
        self.assertEqual(report.tests, 9)  # current + snapshot + 3 fixtures + 4 boundaries
        promotion = self.system.promote(
            "tenant-a",
            build.created[0],
            scope_hash=report.scope_hash,
            promoted_by="release-manager",
        )
        return build.created[0], promotion

    def test_supervised_miss_to_exact_artifact_hit(self) -> None:
        self.register()
        artifact_id, _ = self.mature_and_promote()
        calls = len(self.source.calls)
        resolved = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="artifact-hit"
        )
        self.assertEqual(resolved.source, "artifact")
        self.assertEqual(resolved.artifact_id, artifact_id)
        self.assertEqual(resolved.output, {"echo": {"x": 1}})
        self.assertEqual(len(self.source.calls), calls)

        # Exact scope: a near miss goes back to supervision.
        near = self.system.handle(
            "tenant-a", "echo", {"x": 2}, request_id="near-miss"
        )
        self.assertIsInstance(near, ReviewRequired)
        self.assertEqual(len(self.source.calls), calls + 1)

    def test_dispatch_uses_sealed_promotion_receipt_without_rehashing_tests(self) -> None:
        self.register()
        artifact_id, _ = self.mature_and_promote()
        with mock.patch.object(
            System,
            "_test_snapshot",
            side_effect=AssertionError("dispatch rehashed sealed tests"),
        ):
            resolved = self.system.handle(
                "tenant-a", "echo", {"x": 1}, request_id="sealed-fast-path"
            )
        self.assertEqual(resolved.artifact_id, artifact_id)

    def test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        pending = self.system.handle("tenant-a", "echo", {"x": 1}, request_id="reject-me")
        self.assertIsInstance(pending, ReviewRequired)
        self.assertFalse(hasattr(pending, "proposed_output"))
        rejected = self.system.review(
            "tenant-a", pending.proposal_id, reviewer="alice", decision="reject"
        )
        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(self.system.examples("tenant-a", "echo"), [])
        self.assertFalse(self.system.compile("tenant-a", "echo").created)

    def test_proposal_content_hashes_fail_closed_on_storage_mutation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        pending = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="proposal-tamper"
        )
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE proposals SET proposed_output_json = ? WHERE id = ?",
                ('{"tampered":true}', pending.proposal_id),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            self.system.get_proposal("tenant-a", pending.proposal_id)
        with self.assertRaises(IntegrityError):
            self.system.review(
                "tenant-a", pending.proposal_id, reviewer="alice", decision="accept"
            )

    def test_confirmed_request_cache_is_bound_to_immutable_example(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        for request_id, corrupted in (
            ("confirmed-cache-invalid", "{"),
            ("confirmed-cache-mismatch", '"tampered"'),
        ):
            with self.subTest(request_id=request_id):
                self.confirm(request_id)
                connection = sqlite3.connect(self.database)
                try:
                    connection.execute(
                        """
                        UPDATE requests SET output_json = ?
                        WHERE partition = ? AND id = ?
                        """,
                        (corrupted, "tenant-a", request_id),
                    )
                    connection.commit()
                finally:
                    connection.close()

                self.assertIsInstance(
                    self.system.request_status("tenant-a", request_id),
                    ReconciliationRequired,
                )
                outcome = self.system.handle(
                    "tenant-a", "echo", {"x": 1}, request_id=request_id
                )
                self.assertIsInstance(outcome, ReconciliationRequired)

    def test_artifact_request_cache_is_bound_to_current_execution(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("artifact-cache-evidence-1")
        self.confirm("artifact-cache-evidence-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        report = self.system.verify("tenant-a", artifact)
        self.system.promote(
            "tenant-a", artifact, scope_hash=report.scope_hash, promoted_by="manager"
        )
        for request_id, corrupted in (
            ("artifact-cache-invalid", "{"),
            ("artifact-cache-mismatch", '"tampered"'),
        ):
            with self.subTest(request_id=request_id):
                self.system.handle(
                    "tenant-a", "echo", {"x": 1}, request_id=request_id
                )
                connection = sqlite3.connect(self.database)
                try:
                    connection.execute(
                        """
                        UPDATE requests SET output_json = ?
                        WHERE partition = ? AND id = ?
                        """,
                        (corrupted, "tenant-a", request_id),
                    )
                    connection.commit()
                finally:
                    connection.close()
                self.assertIsInstance(
                    self.system.request_status("tenant-a", request_id),
                    ReconciliationRequired,
                )
                self.assertIsInstance(
                    self.system.handle(
                        "tenant-a", "echo", {"x": 1}, request_id=request_id
                    ),
                    ReconciliationRequired,
                )

    def test_correction_is_the_fixture_and_conflicts_block_compilation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("correct-1", corrected={"answer": "human"})
        self.confirm("correct-2", corrected={"answer": "human"})
        first = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(first.created), 1)

        self.confirm("conflict", corrected={"answer": "changed"})
        conflict = self.system.compile("tenant-a", "echo")
        self.assertFalse(conflict.created)
        self.assertIn("conflict", " ".join(conflict.blocked[0]["reasons"]))

    def test_promotion_rechecks_evidence_snapshot(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("snapshot-1")
        self.confirm("snapshot-2")
        build = self.system.compile("tenant-a", "echo")
        report = self.system.verify("tenant-a", build.created[0])
        self.confirm("snapshot-3")
        with self.assertRaisesRegex(StateError, "evidence snapshot changed"):
            self.system.promote(
                "tenant-a",
                build.created[0],
                scope_hash=report.scope_hash,
                promoted_by="alice",
            )

    def test_scope_hash_must_be_explicit(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("scope-1")
        self.confirm("scope-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        self.system.verify("tenant-a", artifact)
        with self.assertRaises(ConflictError):
            self.system.promote(
                "tenant-a", artifact, scope_hash="0" * 64, promoted_by="alice"
            )

    def test_counterexample_and_revocation_quarantine(self) -> None:
        self.register()
        artifact, _ = self.mature_and_promote()
        example_id, suspended = self.system.challenge(
            "tenant-a",
            "echo",
            {"x": 1},
            {"different": True},
            reviewer="auditor",
        )
        self.assertTrue(suspended)
        self.assertTrue(example_id.startswith("ex_"))
        fallback = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="after-challenge"
        )
        self.assertIsInstance(fallback, ReviewRequired)
        self.assertEqual(self.system.artifact("tenant-a", artifact)["status"], "suspended")

        # A fresh fixture-derived artifact is also quarantined when evidence is revoked.
        other_db = str(pathlib.Path(self.temporary.name) / "revoke.db")
        clock = Clock()
        system = System(other_db, candidate_source=FakeSource(), clock_us=clock)
        system.register_operation(
            "tenant-a", "echo", policy=CompilePolicy(2, 1, 0)
        )
        evidence = []
        for request_id in ("a", "b"):
            pending = system.handle("tenant-a", "echo", 1, request_id=request_id)
            resolved = system.review(
                "tenant-a", pending.proposal_id, reviewer="alice", decision="accept"
            )
            evidence.append(resolved.example_id)
        build = system.compile("tenant-a", "echo").created[0]
        report = system.verify("tenant-a", build)
        system.promote("tenant-a", build, scope_hash=report.scope_hash, promoted_by="alice")
        quarantined = system.revoke_example(
            "tenant-a", evidence[0], revoked_by="privacy", reason="consent withdrawn"
        )
        self.assertEqual(quarantined, (build,))
        self.assertEqual(system.artifact("tenant-a", build)["status"], "suspended")

    def test_quarantined_artifact_cannot_replay_an_old_idempotency_key(self) -> None:
        self.register()
        artifact, _ = self.mature_and_promote()
        original = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="served-before-quarantine"
        )
        self.assertEqual(original.artifact_id, artifact)
        self.system.challenge(
            "tenant-a",
            "echo",
            {"x": 1},
            {"counterexample": True},
            reviewer="auditor",
        )
        replay = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="served-before-quarantine"
        )
        self.assertIsInstance(replay, ReconciliationRequired)
        self.assertFalse(hasattr(replay, "output"))

    def test_late_review_counterexample_quarantines_promoted_scope(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        late = self.system.handle("tenant-a", "echo", {"x": 1}, request_id="late")
        self.confirm("early-1")
        self.confirm("early-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        report = self.system.verify("tenant-a", artifact)
        self.system.promote(
            "tenant-a", artifact, scope_hash=report.scope_hash, promoted_by="manager"
        )
        self.system.review(
            "tenant-a",
            late.proposal_id,
            reviewer="auditor",
            decision="correct",
            corrected_output={"changed": True},
        )
        self.assertEqual(self.system.artifact("tenant-a", artifact)["status"], "suspended")
        fresh = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="after-late-review"
        )
        self.assertIsInstance(fresh, ReviewRequired)

    def test_request_idempotency_and_partition_isolation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        first = self.system.handle("tenant-a", "echo", {"x": 1}, request_id="stable-id")
        second = self.system.handle("tenant-a", "echo", {"x": 1}, request_id="stable-id")
        self.assertEqual(first, second)
        self.assertEqual(len(self.source.calls), 1)
        with self.assertRaises(ConflictError):
            self.system.handle("tenant-a", "echo", {"x": 2}, request_id="stable-id")
        self.system.register_operation(
            "tenant-b", "echo", policy=CompilePolicy(2, 1, 0)
        )
        isolated = self.system.handle(
            "tenant-b", "echo", {"x": 1}, request_id="stable-id"
        )
        self.assertIsInstance(isolated, ReviewRequired)
        self.assertNotEqual(isolated.proposal_id, first.proposal_id)
        with self.assertRaises(NotFoundError):
            self.system.get_proposal("tenant-b", first.proposal_id)

    def test_monotonic_feeds_survive_transitions_and_clock_rollback(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        older = self.system.handle(
            "tenant-a", "echo", {"x": "older"}, request_id="feed-older"
        )
        newer = self.system.handle(
            "tenant-a", "echo", {"x": "newer"}, request_id="feed-newer"
        )
        self.system.review(
            "tenant-a", newer.proposal_id, reviewer="alice", decision="accept"
        )
        accepted = self.system.proposals("tenant-a", status="accepted")
        cursor = int(accepted[-1]["sequence"])
        self.clock.now_us = 1
        self.system.review(
            "tenant-a", older.proposal_id, reviewer="alice", decision="accept"
        )
        delta = self.system.proposals(
            "tenant-a", status="accepted", after_sequence=cursor
        )
        self.assertEqual([item["id"] for item in delta], [older.proposal_id])

        self.clock.now_us = 1_000_000
        self.confirm("feed-report-1")
        self.confirm("feed-report-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        first_report = self.system.verify("tenant-a", artifact)
        first_stored = self.system.report("tenant-a", first_report.id)
        self.clock.now_us = 2
        second_report = self.system.verify("tenant-a", artifact)
        reports = self.system.reports(
            "tenant-a", after_sequence=int(first_stored["sequence"])
        )
        self.assertEqual([item["id"] for item in reports], [second_report.id])
        self.assertLess(reports[0]["created_at_us"], first_stored["created_at_us"])

    def test_concurrent_retry_observes_generation_lease(self) -> None:
        source = BlockingSource()
        system = System(self.database, candidate_source=source, clock_us=self.clock)
        system.register_operation(
            "tenant-a", "wait", policy=CompilePolicy(2, 1, 0)
        )
        result = []

        def invoke() -> None:
            result.append(system.handle("tenant-a", "wait", 1, request_id="same"))

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(source.entered.wait(timeout=1))
        duplicate = system.handle("tenant-a", "wait", 1, request_id="same")
        self.assertIsInstance(duplicate, InProgress)
        source.release.set()
        thread.join(timeout=2)
        self.assertIsInstance(result[0], ReviewRequired)

    def test_expired_generation_poll_is_retryable_and_handle_reclaims(self) -> None:
        source = BlockingSource()
        system = System(
            self.database,
            candidate_source=source,
            clock_us=self.clock,
            generation_lease_seconds=1,
        )
        system.register_operation(
            "tenant-a", "wait", policy=CompilePolicy(2, 1, 0)
        )
        original = []
        thread = threading.Thread(
            target=lambda: original.append(
                system.handle("tenant-a", "wait", 1, request_id="expired")
            )
        )
        thread.start()
        self.assertTrue(source.entered.wait(timeout=1))
        self.clock.advance(2)
        expired = system.request_status("tenant-a", "expired")
        self.assertIsInstance(expired, FallbackFailed)
        self.assertEqual(expired.code, "generation_lease_expired")

        system.candidate_source = FakeSource(output="replacement")
        reclaimed = system.handle("tenant-a", "wait", 1, request_id="expired")
        self.assertIsInstance(reclaimed, ReviewRequired)
        source.release.set()
        thread.join(timeout=2)
        self.assertEqual(original, [reclaimed])

    def test_missing_or_broken_source_is_a_stored_inert_failure(self) -> None:
        no_source = System(self.database, clock_us=self.clock)
        no_source.register_operation(
            "tenant-a", "none", policy=CompilePolicy(2, 1, 0)
        )
        failed = no_source.handle("tenant-a", "none", 1, request_id="failure")
        self.assertIsInstance(failed, FallbackFailed)
        again = no_source.handle("tenant-a", "none", 1, request_id="failure")
        self.assertEqual(failed, again)

    def test_policy_rejects_non_integer_numeric_values_immediately(self) -> None:
        for values in ((2.0, 1, 0), (2, True, 0), (2, 1, 0.0)):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                CompilePolicy(*values)

    def test_public_scalar_validation_fails_with_domain_errors(self) -> None:
        with self.assertRaises(ValidationError):
            System(self.database, generation_lease_seconds=1.0000001)
        self.register(confirmations=2, reviewers=1, span=0)
        invalid_calls = (
            lambda: self.system.handle("tenant-a", "echo", 1, request_id=""),
            lambda: self.system.handle("tenant-a", "echo", 1, retry_failed=1),
            lambda: self.system.proposals("tenant-a", after_sequence=0.5),
            lambda: self.system.proposals("tenant-a", limit=True),
            lambda: self.system.examples("tenant-a", "echo", include_revoked=1),
            lambda: self.system.artifacts("tenant-a", "echo", limit=1.5),
            lambda: self.system.reports("tenant-a", after_sequence=False),
            lambda: self.system.events("tenant-a", after=0.25),
            lambda: self.system.report("tenant-a", "report_x", after_test_key="\ud800"),
            lambda: self.system.revise_operation(
                "tenant-a",
                "echo",
                policy=CompilePolicy(2, 1, 0),
                revised_by="\ud800",
            ),
            lambda: self.system.register_operation("tenant-a", "bad-policy", policy={}),
            lambda: self.system.revise_operation(
                "tenant-a", "echo", policy={}, revised_by="owner"
            ),
            lambda: self.system.review(
                "tenant-a", "prop_missing", reviewer="alice", decision=[]
            ),
            lambda: self.system.promote(
                "tenant-a", "art_missing", scope_hash=None, promoted_by="alice"
            ),
        )
        for invoke in invalid_calls:
            with self.subTest(invoke=invoke), self.assertRaises(ValidationError):
                invoke()
        for configuration in (
            {"candidate_source": False},
            {"authority": 1},
            {"clock_us": 0},
        ):
            with self.subTest(configuration=configuration), self.assertRaises(ValidationError):
                System(self.database, **configuration)
        overflow = System(self.database, clock_us=lambda: 2**63)
        with self.assertRaises(StateError):
            overflow.register_operation(
                "tenant-a", "clock-overflow", policy=CompilePolicy(2, 1, 0)
            )

    def test_unknown_resolved_source_kind_fails_closed_at_storage(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("source-kind")
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE requests SET source_kind = 'mystery', output_json = '"tampered"'
                    WHERE partition = ? AND id = ?
                    """,
                    ("tenant-a", "source-kind"),
                )
            connection.rollback()
        finally:
            connection.close()

    def test_receipt_can_bind_individually_valid_large_input_and_output(self) -> None:
        source = FakeSource(output="o" * 600_000)
        system = System(self.database, candidate_source=source, clock_us=self.clock)
        system.register_operation(
            "tenant-a", "large", policy=CompilePolicy(2, 1, 0)
        )
        pending = system.handle(
            "tenant-a", "large", "i" * 600_000, request_id="large-record"
        )
        resolved = system.review(
            "tenant-a", pending.proposal_id, reviewer="alice", decision="accept"
        )
        self.assertEqual(len(resolved.output), 600_000)

    def test_runtime_integrity_failure_quarantines_then_falls_back(self) -> None:
        self.register()
        artifact, _ = self.mature_and_promote()
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                "UPDATE artifacts SET artifact_json = ? WHERE id = ?",
                ('{"tampered":true}', artifact),
            )
            connection.commit()
        finally:
            connection.close()
        report = self.system.verify("tenant-a", artifact)
        self.assertFalse(report.passed)
        self.assertIn("integrity", report.failures[0])
        outcome = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="tamper-fallback"
        )
        self.assertIsInstance(outcome, ReviewRequired)
        self.assertEqual(self.system.artifacts("tenant-a", "echo")[-1]["status"], "suspended")

    def test_challenge_quarantines_corrupt_promoted_artifact(self) -> None:
        self.register()
        artifact, _ = self.mature_and_promote()
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                "UPDATE artifacts SET artifact_json = ? WHERE id = ?",
                ('{"tampered":true}', artifact),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(StateError, "quarantined"):
            self.system.challenge(
                "tenant-a",
                "echo",
                {"x": 1},
                {"echo": {"x": 1}},
                reviewer="auditor",
            )
        self.assertEqual(self.system.artifacts("tenant-a", "echo")[-1]["status"], "suspended")

    def test_operation_revision_retires_old_artifacts(self) -> None:
        self.register()
        artifact, _ = self.mature_and_promote()
        revision = self.system.revise_operation(
            "tenant-a",
            "echo",
            policy=CompilePolicy(4, 2, 20),
            revised_by="owner",
        )
        self.assertEqual(revision, 2)
        self.assertEqual(self.system.artifact("tenant-a", artifact)["status"], "retired")
        fallback = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="new-revision"
        )
        self.assertIsInstance(fallback, ReviewRequired)

    def test_operation_revision_invalidates_every_old_request_path(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("old-confirmed")
        pending = self.system.handle(
            "tenant-a", "echo", {"x": 2}, request_id="old-pending"
        )
        self.system.candidate_source = None
        failed = self.system.handle(
            "tenant-a", "echo", {"x": 3}, request_id="old-failed"
        )
        self.assertIsInstance(failed, FallbackFailed)
        self.system.candidate_source = self.source
        calls_before_revision = len(self.source.calls)

        self.system.revise_operation(
            "tenant-a",
            "echo",
            policy=CompilePolicy(2, 1, 0),
            revised_by="owner",
        )
        for request_id, value in (
            ("old-confirmed", {"x": 1}),
            ("old-pending", {"x": 2}),
            ("old-failed", {"x": 3}),
        ):
            with self.subTest(request_id=request_id):
                replay = self.system.handle(
                    "tenant-a",
                    "echo",
                    value,
                    request_id=request_id,
                    retry_failed=True,
                )
                self.assertIsInstance(replay, ReconciliationRequired)
                self.assertIsInstance(
                    self.system.request_status("tenant-a", request_id),
                    ReconciliationRequired,
                )
        self.assertEqual(len(self.source.calls), calls_before_revision)
        with self.assertRaisesRegex(StateError, "obsolete operation revision"):
            self.system.review(
                "tenant-a", pending.proposal_id, reviewer="alice", decision="accept"
            )
        rejected = self.system.review(
            "tenant-a", pending.proposal_id, reviewer="alice", decision="reject"
        )
        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(
            self.system.request_status("tenant-a", "old-pending").status,
            "rejected",
        )

        current = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="current-request"
        )
        self.assertIsInstance(current, ReviewRequired)
        self.assertEqual(self.source.calls[-1].operation_revision, 2)

    def test_revision_cancels_in_flight_old_generation(self) -> None:
        source = BlockingSource()
        system = System(self.database, candidate_source=source, clock_us=self.clock)
        system.register_operation(
            "tenant-a", "wait", policy=CompilePolicy(2, 1, 0)
        )
        outcomes = []

        thread = threading.Thread(
            target=lambda: outcomes.append(
                system.handle("tenant-a", "wait", 1, request_id="in-flight")
            )
        )
        thread.start()
        self.assertTrue(source.entered.wait(timeout=1))
        system.revise_operation(
            "tenant-a",
            "wait",
            policy=CompilePolicy(2, 1, 0),
            revised_by="owner",
        )
        source.release.set()
        thread.join(timeout=2)
        self.assertEqual(len(outcomes), 1)
        self.assertIsInstance(outcomes[0], ReconciliationRequired)
        self.assertEqual(system.proposals("tenant-a"), [])

    def test_explicit_revision_bumps_even_when_thresholds_do_not_change(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "semantic", policy=policy)
        revision = self.system.revise_operation(
            "tenant-a", "semantic", policy=policy, revised_by="owner"
        )
        self.assertEqual(revision, 2)

    def test_audit_events_and_learning_are_partition_exact(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        for partition in ("a_b", "acb", "root", "root/child"):
            self.system.register_operation(partition, "echo", policy=policy)
        for partition in ("a_b", "acb", "root", "root/child"):
            events = self.system.events(partition)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["subject_id"], f"{partition}/echo@1")

    def test_artifact_evidence_edges_are_database_immutable(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("edge-1")
        self.confirm("edge-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        extra = self.system.handle(
            "tenant-a", "echo", {"x": 2}, request_id="edge-unrelated"
        )
        extra_example = self.system.review(
            "tenant-a", extra.proposal_id, reviewer="alice", decision="accept"
        ).example_id
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM artifact_evidence WHERE artifact_id = ?", (artifact,)
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO artifact_evidence(artifact_id, example_id) VALUES (?, ?)",
                    (artifact, extra_example),
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE artifacts SET status = 'building' WHERE id = ?", (artifact,)
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE artifacts SET sequence = sequence + 100 WHERE id = ?", (artifact,)
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE artifacts SET support = support + 100 WHERE id = ?", (artifact,)
                )
            connection.rollback()
        finally:
            connection.close()

    def test_activation_requires_an_integrity_valid_promotion_receipt(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("activation-1")
        self.confirm("activation-2")
        draft = self.system.compile("tenant-a", "echo").created[0]
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE artifacts SET status = 'promoted' WHERE id = ?", (draft,)
                )
            connection.rollback()
        finally:
            connection.close()

        report = self.system.verify("tenant-a", draft)
        self.system.promote(
            "tenant-a", draft, scope_hash=report.scope_hash, promoted_by="manager"
        )
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE artifacts SET promotion_hash = ? WHERE id = ?",
                ("0" * 64, draft),
            )
            connection.commit()
        finally:
            connection.close()
        fallback = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="bad-promotion-receipt"
        )
        self.assertIsInstance(fallback, ReviewRequired)
        self.assertEqual(self.system.artifacts("tenant-a", "echo")[-1]["status"], "suspended")

    def test_verification_recomputes_build_stability_metadata(self) -> None:
        self.register(confirmations=2, reviewers=2, span=0)
        self.confirm("metadata-1", reviewer="alice")
        self.confirm("metadata-2", reviewer="bob")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact,)
            ).fetchone()
            corrupt_build = build_digest(
                artifact_digest=str(row["artifact_hash"]),
                policy_digest=str(row["policy_hash"]),
                evidence_snapshot_digest=str(row["evidence_snapshot_hash"]),
                support=999,
                reviewer_count=1,
                span_seconds=999,
            )
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                """
                UPDATE artifacts
                SET support = 999, reviewer_count = 1, span_seconds = 999, build_hash = ?
                WHERE id = ?
                """,
                (corrupt_build, artifact),
            )
            connection.commit()
        finally:
            connection.close()
        report = self.system.verify("tenant-a", artifact)
        self.assertFalse(report.passed)
        self.assertIn("support", report.failures[0])

    def test_suspension_cannot_replay_a_historical_promotion_receipt(self) -> None:
        self.register()
        artifact, _ = self.mature_and_promote()
        connection = sqlite3.connect(self.database)
        try:
            receipt = connection.execute(
                "SELECT promotion_hash FROM artifacts WHERE id = ?", (artifact,)
            ).fetchone()[0]
        finally:
            connection.close()
        _, suspended = self.system.challenge(
            "tenant-a", "echo", {"x": 1}, {"wrong": True}, reviewer="auditor"
        )
        self.assertTrue(suspended)
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE artifacts SET status = 'promoted', promotion_hash = ? WHERE id = ?",
                    (receipt, artifact),
                )
            connection.rollback()
        finally:
            connection.close()

    def test_example_listing_cursor_survives_clock_rollback(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        first_id = self.confirm("example-page-1").example_id
        first_page = self.system.examples("tenant-a", "echo", limit=1)
        self.assertEqual(first_page[0]["id"], first_id)
        self.clock.now_us = 1
        second_id = self.confirm("example-page-2").example_id
        second_page = self.system.examples(
            "tenant-a", "echo", after_sequence=first_page[0]["sequence"], limit=1
        )
        self.assertEqual(second_page[0]["id"], second_id)

    def test_terminal_build_does_not_block_safe_recompilation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("liveness-1")
        self.confirm("liveness-2")
        first = self.system.compile("tenant-a", "echo").created[0]
        first_report = self.system.verify("tenant-a", first)
        self.system.promote(
            "tenant-a", first, scope_hash=first_report.scope_hash, promoted_by="manager"
        )
        third, suspended = self.system.challenge(
            "tenant-a",
            "echo",
            {"x": 1},
            {"echo": {"x": 1}},
            reviewer="auditor",
        )
        self.assertFalse(suspended)
        second = self.system.compile("tenant-a", "echo").created[0]
        second_report = self.system.verify("tenant-a", second)
        self.system.promote(
            "tenant-a", second, scope_hash=second_report.scope_hash, promoted_by="manager"
        )
        self.assertEqual(self.system.artifact("tenant-a", first)["status"], "retired")
        self.system.revoke_example(
            "tenant-a", third, revoked_by="auditor", reason="bad extra observation"
        )
        rebuilt = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(rebuilt.created), 1)
        third_build = rebuilt.created[0]
        self.assertNotIn(third_build, {first, second})
        final_report = self.system.verify("tenant-a", third_build)
        self.system.promote(
            "tenant-a", third_build, scope_hash=final_report.scope_hash, promoted_by="manager"
        )
        self.assertEqual(
            self.system.handle(
                "tenant-a", "echo", {"x": 1}, request_id="liveness-restored"
            ).source,
            "artifact",
        )

    def test_verification_records_are_database_immutable(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("report-1")
        self.confirm("report-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        report = self.system.verify("tenant-a", artifact)
        stored = self.system.report("tenant-a", report.id)
        self.assertEqual(stored["test_count"], report.tests)
        self.assertEqual(self.system.reports("tenant-a")[0]["id"], report.id)
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE test_reports SET passed = 0 WHERE id = ?", (report.id,)
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM artifact_tests WHERE report_id = ?", (report.id,)
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO artifact_tests(report_id, test_key, passed, detail)
                    VALUES (?, 'late-test', 0, 'must be sealed')
                    """,
                    (report.id,),
                )
            connection.rollback()
        finally:
            connection.close()

    def test_report_feed_validates_the_complete_child_test_set(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self.confirm("report-feed-1")
        self.confirm("report-feed-2")
        artifact = self.system.compile("tenant-a", "echo").created[0]
        report = self.system.verify("tenant-a", artifact)
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifact_tests_no_update")
            connection.execute(
                """
                UPDATE artifact_tests SET detail = 'corrupt child test'
                WHERE report_id = ? AND test_key = (
                    SELECT MIN(test_key) FROM artifact_tests WHERE report_id = ?
                )
                """,
                (report.id, report.id),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            self.system.reports("tenant-a")

    def test_authority_denial_precedes_control_plane_mutation(self) -> None:
        allowed = True
        calls = []

        def authority(partition, actor, action, subject):
            calls.append((partition, actor, action, subject))
            return allowed

        guarded_db = str(pathlib.Path(self.temporary.name) / "guarded.db")
        guarded = System(
            guarded_db,
            candidate_source=FakeSource(),
            authority=authority,
            clock_us=self.clock,
        )
        guarded.register_operation(
            "tenant", "echo", policy=CompilePolicy(2, 1, 0), registered_by="owner"
        )
        for request_id in ("one", "two"):
            pending = guarded.handle("tenant", "echo", 1, request_id=request_id)
            guarded.review(
                "tenant", pending.proposal_id, reviewer="owner", decision="accept"
            )
        allowed = False
        with self.assertRaises(StateError):
            guarded.compile("tenant", "echo", compiled_by="blocked")
        self.assertEqual(guarded.artifacts("tenant", "echo"), [])
        with self.assertRaises(StateError):
            guarded.register_operation(
                "tenant", "other", policy=CompilePolicy(2, 1, 0), registered_by="blocked"
            )
        allowed = True
        artifact = guarded.compile("tenant", "echo", compiled_by="owner").created[0]
        allowed = False
        with self.assertRaises(StateError):
            guarded.verify("tenant", artifact, verified_by="blocked")
        self.assertEqual(guarded.artifact("tenant", artifact)["status"], "draft")
        self.assertIn(("tenant", "blocked", "artifact.verify", artifact), calls)

    def test_authority_requires_the_exact_boolean_true(self) -> None:
        for index, returned in enumerate(("allow", 1, object())):
            guarded = System(
                str(pathlib.Path(self.temporary.name) / f"truthy-{index}.db"),
                authority=lambda *_args, returned=returned: returned,
                clock_us=self.clock,
            )
            with self.subTest(returned=returned), self.assertRaises(StateError):
                guarded.register_operation(
                    "tenant", "echo", policy=CompilePolicy(2, 1, 0), registered_by="owner"
                )
            self.assertEqual(guarded.operations("tenant"), [])

    def test_review_rejects_cross_table_state_corruption(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        pending = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="cross-state"
        )
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE requests SET status = 'rejected' WHERE partition = ? AND id = ?",
                ("tenant-a", "cross-state"),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            self.system.review(
                "tenant-a", pending.proposal_id, reviewer="alice", decision="accept"
            )
        self.assertEqual(self.system.examples("tenant-a", "echo"), [])

    def test_schema_version_without_matching_schema_fails_at_open(self) -> None:
        forged = str(pathlib.Path(self.temporary.name) / "forged.db")
        connection = sqlite3.connect(forged)
        try:
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            System(forged)

    def test_unrecognized_database_is_rejected_without_mutation(self) -> None:
        for version in (0, 2):
            with self.subTest(version=version):
                unrelated = str(
                    pathlib.Path(self.temporary.name) / f"unrelated-{version}.db"
                )
                connection = sqlite3.connect(unrelated)
                try:
                    self.assertEqual(
                        connection.execute("PRAGMA journal_mode = WAL").fetchone()[0],
                        "wal",
                    )
                    connection.execute("CREATE TABLE user_data(value TEXT)")
                    connection.execute("INSERT INTO user_data VALUES ('preserve-me')")
                    connection.execute(f"PRAGMA user_version = {version}")
                    connection.commit()
                finally:
                    connection.close()
                with self.assertRaises(IntegrityError):
                    System(unrelated)
                connection = sqlite3.connect(unrelated)
                try:
                    self.assertEqual(
                        connection.execute("PRAGMA journal_mode").fetchone()[0], "wal"
                    )
                    self.assertEqual(
                        connection.execute("PRAGMA user_version").fetchone()[0], version
                    )
                    self.assertEqual(
                        connection.execute("SELECT value FROM user_data").fetchone()[0],
                        "preserve-me",
                    )
                    tables = {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_schema WHERE type = 'table'"
                        )
                    }
                    self.assertEqual(tables, {"user_data"})
                finally:
                    connection.close()

        poisoned = str(pathlib.Path(self.temporary.name) / "internal-schema.db")
        connection = sqlite3.connect(poisoned)
        try:
            connection.execute(
                "CREATE TABLE old(id INTEGER PRIMARY KEY AUTOINCREMENT)"
            )
            connection.execute("DROP TABLE old")
            connection.execute(
                "INSERT INTO sqlite_sequence(name, seq) VALUES ('examples', 99)"
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            System(poisoned)
        connection = sqlite3.connect(poisoned)
        try:
            self.assertEqual(
                connection.execute("SELECT name, seq FROM sqlite_sequence").fetchall(),
                [("examples", 99)],
            )
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)
        finally:
            connection.close()

    def test_corrupt_or_constraint_invalid_database_fails_at_open(self) -> None:
        corrupt = pathlib.Path(self.temporary.name) / "not-sqlite.db"
        corrupt.write_bytes(b"not a sqlite database")
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always", ResourceWarning)
            with self.assertRaises(IntegrityError):
                System(str(corrupt))
            gc.collect()
        self.assertEqual(
            [warning for warning in observed if warning.category is ResourceWarning],
            [],
        )

        self.register(confirmations=2, reviewers=1, span=0)
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute(
                "UPDATE operations SET revision = 0 WHERE partition = ? AND name = ?",
                ("tenant-a", "echo"),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            System(self.database)

    def test_invalid_database_path_is_a_domain_error(self) -> None:
        for path in ("bad\0path", "\ud800", ":memory:"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                System(path)

        link = pathlib.Path(self.temporary.name) / "broken-link.db"
        target = pathlib.Path(self.temporary.name) / "must-not-exist.db"
        link.symlink_to(target)
        with self.assertRaises(ValidationError):
            System(link)
        self.assertFalse(target.exists())

    def test_live_schema_mutation_fails_at_open(self) -> None:
        clean = str(pathlib.Path(self.temporary.name) / "schema-mutation.db")
        System(clean)
        connection = sqlite3.connect(clean)
        try:
            connection.execute("DROP TRIGGER artifact_evidence_no_delete")
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            System(clean)

    def test_concurrent_first_open_is_atomic_and_idempotent(self) -> None:
        concurrent = str(pathlib.Path(self.temporary.name) / "concurrent.db")
        barrier = threading.Barrier(12)
        failures = []

        def open_store() -> None:
            try:
                barrier.wait(timeout=2)
                System(concurrent)
            except Exception as exc:  # captured for assertion in the test thread
                failures.append(exc)

        threads = [threading.Thread(target=open_store) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(failures, [])
        reopened = System(concurrent)
        self.assertEqual(
            reopened.register_operation(
                "tenant", "echo", policy=CompilePolicy(2, 1, 0)
            ),
            1,
        )


    @staticmethod
    def _function_checks(result: FunctionVerification) -> dict[str, FunctionCheck]:
        return {check.key: check for check in result.checks}


    def _assert_function_checks(
        self,
        result: FunctionVerification,
        expected: tuple[bool, bool, bool, bool, bool],
    ) -> None:
        self.assertEqual(
            tuple((check.key, check.passed) for check in result.checks),
            tuple(zip(_FUNCTION_CHECK_KEYS, expected, strict=True)),
        )
        self.assertEqual(result.passed, all(expected))

    def _confirm_scope(
        self,
        partition: str,
        operation: str,
        value,
        request_id: str,
        *,
        reviewer: str,
        corrected=None,
    ) -> None:
        outcome = self.system.handle(
            partition, operation, value, request_id=request_id
        )
        self.assertIsInstance(outcome, ReviewRequired)
        assert isinstance(outcome, ReviewRequired)
        proposal = self.system.get_proposal(partition, outcome.proposal_id)
        self.assertEqual(proposal.proposed_output, {"echo": value})
        if corrected is None:
            self.system.review(
                partition,
                outcome.proposal_id,
                reviewer=reviewer,
                decision="accept",
            )
        else:
            self.system.review(
                partition,
                outcome.proposal_id,
                reviewer=reviewer,
                decision="correct",
                corrected_output=corrected,
            )

    def _promote_scope(
        self,
        partition: str,
        operation: str,
        value,
        prefix: str,
        *,
        corrected=None,
    ):
        self._confirm_scope(
            partition,
            operation,
            value,
            f"{prefix}-1",
            reviewer="alice",
            corrected=corrected,
        )
        self._confirm_scope(
            partition,
            operation,
            value,
            f"{prefix}-2",
            reviewer="bob",
            corrected=corrected,
        )
        build = self.system.compile(partition, operation)
        self.assertEqual(len(build.created), 1)
        artifact_id = build.created[0]
        report = self.system.verify(partition, artifact_id)
        self.assertTrue(report.passed)
        promotion = self.system.promote(
            partition,
            artifact_id,
            scope_hash=report.scope_hash,
            promoted_by="release-manager",
        )
        return artifact_id, report, promotion

    @staticmethod
    def _promotion_hash(artifact: sqlite3.Row, report: sqlite3.Row) -> str:
        return _digest_strings(
            "cement-promotion-v2",
            (
                str(artifact["id"]),
                str(artifact["artifact_hash"]),
                str(artifact["build_hash"]),
                str(artifact["policy_hash"]),
                str(artifact["evidence_snapshot_hash"]),
                str(artifact["support"]),
                str(artifact["reviewer_count"]),
                str(artifact["span_seconds"]),
                str(artifact["scope_hash"]),
                str(report["id"]),
                str(report["details_hash"]),
                str(report["test_set_hash"]),
                str(report["test_count"]),
                str(report["passed"]),
                str(artifact["promoted_by"]),
                str(artifact["promoted_at_us"]),
            ),
        )

    @staticmethod
    def _insert_schema_membership(
        connection: sqlite3.Connection,
        *,
        receipt_id: object,
        ordinal: object,
        function_hash: object,
        artifact_id: object,
        report_id: object,
        input_hash: object,
        entry_seal: object,
    ) -> None:
        connection.execute(
            """
            INSERT INTO function_memberships(
                receipt_id, ordinal, function_hash, artifact_id, report_id,
                input_hash, entry_seal
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                ordinal,
                function_hash,
                artifact_id,
                report_id,
                input_hash,
                entry_seal,
            ),
        )

    @staticmethod
    def _insert_schema_receipt(
        connection: sqlite3.Connection,
        *,
        receipt_id: str,
        function_hash: object = "f" * 64,
        receipt_hash: object | None = None,
        operation_revision: object = 1,
        member_count: object = 0,
        candidate_count: object = 0,
        retired_count: object = 0,
    ) -> None:
        connection.execute(
            """
            INSERT INTO function_receipts(
                id, partition, operation, operation_revision, policy_hash,
                function_hash, membership_hash, member_count,
                candidate_artifact_ids_hash, candidate_count,
                retired_artifact_ids_hash, retired_count, promoted_by,
                promoted_at_us, receipt_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                "schema-partition",
                "schema-operation",
                operation_revision,
                "p" * 64,
                function_hash,
                "m" * 64,
                member_count,
                "c" * 64,
                candidate_count,
                "r" * 64,
                retired_count,
                "schema-promoter",
                1,
                receipt_hash if receipt_hash is not None else f"{receipt_id}-hash",
            ),
        )

    def _promote_function_entry(self, value, prefix: str, *, corrected=None):
        return self._promote_scope(
            "tenant-a", "echo", value, prefix, corrected=corrected
        )

    def _promote_three_function_entries(self, prefix: str) -> tuple[str, ...]:
        return tuple(
            self._promote_function_entry(
                {"x": value}, f"{prefix}-{value}"
            )[0]
            for value in (1, 2, 3)
        )


    def _compile_three_drafts(self, prefix: str) -> tuple[str, ...]:
        for value in (1, 2, 3):
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"{prefix}-{value}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"{prefix}-{value}-b",
                reviewer="bob",
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 3)
        self.assertEqual(compiled.blocked, ())
        return compiled.created


    def _verify_three_function_candidates(self, prefix: str) -> DraftVerification:
        self._compile_three_drafts(prefix)
        result = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(result.passed)
        self.assertEqual(len(result.entries), 3)
        return result

    def _promote_three_as_function(
        self,
        prefix: str,
    ) -> tuple[FunctionPromotionManifest, FunctionSetPromotion]:
        self._verify_three_function_candidates(prefix)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        return manifest, promotion

    def _challenge_three_function_entries(self, prefix: str) -> DraftVerification:
        for value in (1, 2, 3):
            _, suspended = self.system.challenge(
                "tenant-a",
                "echo",
                {"x": value},
                {"echo": {"x": value}},
                reviewer="alice",
                note=f"{prefix}-{value}",
            )
            self.assertFalse(suspended)
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 3)
        result = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(result.passed)
        self.assertEqual(len(result.entries), 3)
        return result

    def _function_member_evidence_id(self, artifact_id: str) -> str:
        with self.system.store.transaction(write=False) as connection:
            row = connection.execute(
                """
                SELECT example_id FROM artifact_evidence
                WHERE artifact_id = ? ORDER BY example_id LIMIT 1
                """,
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise AssertionError("function member evidence disappeared")
        return str(row["example_id"])

    def _clone_promoted_function_entry(
        self,
        artifact_id: str,
        *,
        duplicate_id: str = "artifact_duplicate",
        duplicate_report_id: str = "report_duplicate",
    ) -> str:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if artifact is None:
                raise AssertionError("source artifact disappeared")
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (artifact["verified_report_id"],),
            ).fetchone()
            if report is None:
                raise AssertionError("source report disappeared")
            promotion_hash = _digest_strings(
                "cement-promotion-v2",
                (
                    duplicate_id,
                    str(artifact["artifact_hash"]),
                    str(artifact["build_hash"]),
                    str(artifact["policy_hash"]),
                    str(artifact["evidence_snapshot_hash"]),
                    str(artifact["support"]),
                    str(artifact["reviewer_count"]),
                    str(artifact["span_seconds"]),
                    str(artifact["scope_hash"]),
                    duplicate_report_id,
                    str(report["details_hash"]),
                    str(report["test_set_hash"]),
                    str(report["test_count"]),
                    str(report["passed"]),
                    str(artifact["promoted_by"]),
                    str(artifact["promoted_at_us"]),
                ),
            )
            connection.execute("DROP INDEX IF EXISTS one_promoted_exact_scope")
            connection.execute(
                """
                INSERT INTO artifacts(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                    status_reason
                )
                SELECT ?, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    ?, promoted_by, promoted_at_us, ?, status_reason
                FROM artifacts WHERE id = ?
                """,
                (duplicate_id, duplicate_report_id, promotion_hash, artifact_id),
            )
            connection.execute(
                """
                INSERT INTO artifact_tests(report_id, test_key, example_id, passed, detail)
                SELECT ?, test_key, example_id, passed, detail
                FROM artifact_tests WHERE report_id = ?
                """,
                (duplicate_report_id, report["id"]),
            )
            connection.execute(
                """
                INSERT INTO test_reports(
                    id, artifact_id, artifact_hash, build_hash, policy_hash,
                    evidence_snapshot_hash, passed, details_json, details_hash,
                    test_count, test_set_hash, created_at_us
                )
                SELECT ?, ?, artifact_hash, build_hash, policy_hash,
                    evidence_snapshot_hash, passed, details_json, details_hash,
                    test_count, test_set_hash, created_at_us
                FROM test_reports WHERE id = ?
                """,
                (duplicate_report_id, duplicate_id, report["id"]),
            )
            connection.commit()
        finally:
            connection.close()
        return duplicate_id

    def _insert_report_variant(
        self,
        artifact_id: str,
        report_id: str,
        *,
        marker: str,
        owner_id: str | None = None,
    ) -> tuple[str, str]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if artifact is None:
                raise AssertionError("artifact disappeared")
            source = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (artifact["verified_report_id"],),
            ).fetchone()
            if source is None:
                raise AssertionError("bound report disappeared")
            details = json.loads(str(source["details_json"]))
            details["mutation_probe"] = marker
            sealed = canonicalize(details)
            connection.execute(
                """
                INSERT INTO artifact_tests(
                    report_id, test_key, example_id, passed, detail
                )
                SELECT ?, test_key, example_id, passed, detail
                FROM artifact_tests WHERE report_id = ?
                """,
                (report_id, source["id"]),
            )
            connection.execute(
                """
                INSERT INTO test_reports(
                    id, artifact_id, artifact_hash, build_hash, policy_hash,
                    evidence_snapshot_hash, passed, details_json, details_hash,
                    test_count, test_set_hash, created_at_us
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    artifact_id if owner_id is None else owner_id,
                    source["artifact_hash"],
                    source["build_hash"],
                    source["policy_hash"],
                    source["evidence_snapshot_hash"],
                    source["passed"],
                    sealed.text,
                    sealed.digest,
                    source["test_count"],
                    source["test_set_hash"],
                    int(source["created_at_us"]) + 1,
                ),
            )
            connection.commit()
            return str(source["details_hash"]), sealed.digest
        finally:
            connection.close()

    def _bind_report(self, artifact_id: str, report_id: str) -> None:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?", (report_id,)
            ).fetchone()
            if artifact is None or report is None:
                raise AssertionError("report binding fixture disappeared")
            connection.execute(
                """
                UPDATE artifacts SET verified_report_id = ?, promotion_hash = ?
                WHERE id = ?
                """,
                (report_id, self._promotion_hash(artifact, report), artifact_id),
            )
            connection.commit()
        finally:
            connection.close()

    def _function_promotion_page_fixture(self, *, promoted: bool):
        self.register(confirmations=2, reviewers=1, span=0)
        example_rows = []
        for index in range(1_001):
            input_json = canonicalize({"page": index})
            output_json = canonicalize({"echo": {"page": index}})
            for witness, reviewer in (("a", "alice"), ("b", "bob")):
                example_id = f"ex_function_page_{index:04d}_{witness}"
                confirmed_at_us = self.clock.now_us + (witness == "b")
                receipt = canonicalize(
                    {
                        "confirmed_at_us": confirmed_at_us,
                        "example_id": example_id,
                        "format": "cement-confirmation-v1",
                        "input": input_json.value,
                        "note": "function promotion page-tail fixture",
                        "operation": "echo",
                        "operation_revision": 1,
                        "output": output_json.value,
                        "partition": "tenant-a",
                        "resolution": "accepted",
                        "reviewer": reviewer,
                    }
                )
                example_rows.append(
                    (
                        example_id,
                        "tenant-a",
                        "echo",
                        1,
                        input_json.text,
                        input_json.digest,
                        output_json.text,
                        output_json.digest,
                        reviewer,
                        "accepted",
                        receipt.text,
                        receipt.digest,
                        confirmed_at_us,
                    )
                )
        with self.system.store.transaction(write=True) as connection:
            connection.executemany(
                """
                INSERT INTO examples(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, reviewer, origin, receipt_json,
                    receipt_hash, confirmed_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                example_rows,
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 1_001)
        template = self.system.verify("tenant-a", compiled.created[0])
        self.assertTrue(template.passed)
        with self.system.store.transaction(write=True) as connection:
            artifacts = tuple(
                connection.execute(
                    """
                    SELECT * FROM artifacts
                    WHERE partition = 'tenant-a' AND operation = 'echo'
                      AND operation_revision = 1
                    ORDER BY input_hash, sequence, id
                    """
                )
            )
            source_report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (template.id,),
            ).fetchone()
            if source_report is None:
                raise AssertionError("page-tail template report disappeared")
            report_ids = {
                str(row["id"]): (
                    template.id
                    if str(row["id"]) == template.artifact_id
                    else f"report_function_page_{index:04d}"
                )
                for index, row in enumerate(artifacts)
            }
            connection.executemany(
                """
                INSERT INTO test_reports(
                    id, artifact_id, artifact_hash, build_hash, policy_hash,
                    evidence_snapshot_hash, passed, details_json, details_hash,
                    test_count, test_set_hash, created_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        report_ids[str(row["id"])],
                        row["id"],
                        source_report["artifact_hash"],
                        source_report["build_hash"],
                        source_report["policy_hash"],
                        source_report["evidence_snapshot_hash"],
                        source_report["passed"],
                        source_report["details_json"],
                        source_report["details_hash"],
                        source_report["test_count"],
                        source_report["test_set_hash"],
                        source_report["created_at_us"],
                    )
                    for row in artifacts
                    if str(row["id"]) != template.artifact_id
                ),
            )
            connection.executemany(
                """
                UPDATE artifacts
                SET status = 'verified', verified_report_id = ?, promoted_by = NULL,
                    promoted_at_us = NULL, promotion_hash = NULL, status_reason = NULL
                WHERE id = ?
                """,
                (
                    (report_ids[str(row["id"])], row["id"])
                    for row in artifacts
                ),
            )
            if promoted:
                connection.executemany(
                    """
                    UPDATE artifacts
                    SET status = 'promoted', promoted_by = 'page-fixture',
                        promoted_at_us = ?, promotion_hash = ?, status_reason = NULL
                    WHERE id = ?
                    """,
                    (
                        (
                            self.clock.now_us,
                            hashlib.sha256(
                                f"page-promotion:{row['id']}".encode()
                            ).hexdigest(),
                            row["id"],
                        )
                        for row in artifacts
                    ),
                )
        with self.system.store.transaction(write=False) as connection:
            rows = tuple(
                connection.execute(
                    """
                    SELECT * FROM artifacts
                    WHERE partition = 'tenant-a' AND operation = 'echo'
                      AND operation_revision = 1
                    ORDER BY input_hash, sequence, id
                    """
                )
            )
            reports = {
                str(report["id"]): report
                for report in connection.execute(
                    """
                    SELECT * FROM test_reports
                    WHERE artifact_id IN (
                        SELECT id FROM artifacts
                        WHERE partition = 'tenant-a' AND operation = 'echo'
                          AND operation_revision = 1
                    )
                    """
                )
            }
        projections = {}
        function_entries = {}
        for row in rows:
            artifact = self.system._artifact_from_row(row)
            report = reports[str(row["verified_report_id"])]
            projections[str(row["input_hash"])] = _CurrentBuild(
                input_json=artifact.input,
                output_json=artifact.output,
                artifact=artifact,
                policy_json=str(row["policy_json"]),
                policy_hash=str(row["policy_hash"]),
                evidence_snapshot_hash=str(row["evidence_snapshot_hash"]),
                support=int(row["support"]),
                reviewer_count=int(row["reviewer_count"]),
                span_seconds=int(row["span_seconds"]),
                build_hash=str(row["build_hash"]),
            )
            function_entries[str(row["id"])] = FunctionEntry(
                input=artifact.input.value,
                output=artifact.output.value,
                artifact_hash=str(row["artifact_hash"]),
                evidence_snapshot_hash=str(row["evidence_snapshot_hash"]),
                entry_seal=hashlib.sha256(
                    f"page-entry:{row['id']}".encode()
                ).hexdigest(),
                report_details_hash=str(report["details_hash"]),
                report_test_set_hash=str(report["test_set_hash"]),
            )
        expected = build_function(
            partition="tenant-a",
            operation="echo",
            operation_revision=1,
            policy_hash=str(rows[0]["policy_hash"]),
            entries=(function_entries[str(row["id"])] for row in rows),
        )
        return rows, reports, projections, function_entries, expected

    def test_function_verification_empty_set_passes_vacuously(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        result = self.system.verify_function("tenant-a", "echo")
        self.assertIsInstance(result, FunctionVerification)
        self.assertTrue(result.passed)
        self.assertEqual(result.entries, 0)
        self.assertEqual(
            tuple(check.key for check in result.checks),
            (
                "duplicate-input-digests",
                "abi-canonicalizer-uniform",
                "sealed-passing-reports",
                "current-promotion-receipts",
                "function-hash-matches-snapshot",
            ),
        )
        self.assertTrue(all(isinstance(check, FunctionCheck) for check in result.checks))
        self.assertTrue(all(check.passed for check in result.checks))
        self.assertIn("vacuously", result.checks[1].detail)
        document = result.document
        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document.value["entries"], [])
        self.assertEqual(result.function_hash, document.function_hash)
        for invalid_hash in (
            "not-a-digest",
            b"0" * 64,
            0,
            False,
            "A" * 64,
        ):
            with self.subTest(invalid_hash=invalid_hash):
                with self.assertRaisesRegex(
                    ValidationError, "expected_function_hash"
                ):
                    self.system.verify_function(
                        "tenant-a",
                        "echo",
                        expected_function_hash=invalid_hash,  # type: ignore[arg-type]
                    )
        with self.assertRaisesRegex(NotFoundError, "not registered"):
            self.system.verify_function("tenant-a", "missing")

    def test_function_verification_result_models_are_frozen_and_slotted(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        result = self.system.verify_function("tenant-a", "echo")
        check = result.checks[0]
        with self.assertRaises(FrozenInstanceError):
            check.passed = False  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            result.passed = False  # type: ignore[misc]
        self.assertFalse(hasattr(check, "__dict__"))
        self.assertFalse(hasattr(result, "__dict__"))

    def test_function_verification_rejects_incoherent_operation_policy(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        changed = canonicalize(CompilePolicy(3, 1, 0).as_json()).text
        noncanonical = json.dumps(policy.as_json(), sort_keys=True)
        corruptions = (
            ("wrong-hash", changed, "policy digest does not match"),
            ("malformed", "{", "operation policy is invalid"),
            ("noncanonical", noncanonical, "policy JSON is not canonical"),
        )
        for entries in (0, 1):
            for label, policy_json, detail in corruptions:
                with self.subTest(entries=entries, corruption=label):
                    operation = f"policy-{entries}-{label}"
                    self.system.register_operation(
                        "tenant-a", operation, policy=policy
                    )
                    if entries:
                        self._promote_scope(
                            "tenant-a",
                            operation,
                            {"x": label},
                            f"policy-entry-{label}",
                        )
                    connection = sqlite3.connect(self.database)
                    try:
                        connection.execute(
                            """
                            UPDATE operations SET policy_json = ?
                            WHERE partition = 'tenant-a' AND name = ?
                            """,
                            (policy_json, operation),
                        )
                        connection.commit()
                    finally:
                        connection.close()

                    result = self.system.verify_function("tenant-a", operation)
                    checks = self._function_checks(result)
                    self._assert_function_checks(
                        result, (True, True, True, False, False)
                    )
                    self.assertFalse(result.passed)
                    self.assertEqual(result.entries, entries)
                    self.assertIn(
                        detail,
                        checks["current-promotion-receipts"].detail,
                    )
                    self.assertIn(
                        "operation",
                        checks["function-hash-matches-snapshot"].detail,
                    )
                    self.assertIsNone(result.document)
                    self.assertIsNone(result.function_hash)

    def test_function_verification_rejects_invalid_operation_scalar_types(self) -> None:
        corruptions = (
            ("revision", b"1", "stored operation revision"),
            ("policy_hash", b"0" * 64, "stored operation policy hash"),
            ("policy_json", b"{}", "stored operation policy JSON"),
        )

        class OneRowCursor:
            def __init__(self, row) -> None:
                self.row = row

            def fetchone(self):
                return self.row

        for field, value, detail in corruptions:
            with self.subTest(field=field):
                operation = f"invalid-{field}"
                self.system.register_operation(
                    "tenant-a",
                    operation,
                    policy=CompilePolicy(2, 1, 0),
                )

                @contextmanager
                def transaction(*, write: bool):
                    self.assertFalse(write)
                    connection = sqlite3.connect(self.database)
                    connection.row_factory = sqlite3.Row

                    class ConnectionProxy:
                        def execute(self, sql, parameters=()):
                            cursor = connection.execute(sql, parameters)
                            if sql.startswith("SELECT * FROM operations WHERE"):
                                row = cursor.fetchone()
                                if row is None:
                                    return OneRowCursor(None)
                                altered = dict(row)
                                altered[field] = value
                                return OneRowCursor(altered)
                            return cursor

                    try:
                        connection.execute("BEGIN")
                        yield ConnectionProxy()
                    finally:
                        connection.rollback()
                        connection.close()

                with mock.patch.object(
                    self.system.store,
                    "transaction",
                    side_effect=transaction,
                ):
                    with self.assertRaisesRegex(IntegrityError, detail):
                        self.system.verify_function("tenant-a", operation)

    def test_function_verification_pass_is_read_only_and_authority_free(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_function_entry({"x": 1}, "function-pass")
        authority = mock.Mock(side_effect=AssertionError("authority consulted"))
        clock = mock.Mock(side_effect=AssertionError("clock consulted"))
        reader = System(self.database, authority=authority, clock_us=clock)

        def snapshot() -> tuple[str, ...]:
            connection = sqlite3.connect(self.database)
            try:
                return tuple(connection.iterdump())
            finally:
                connection.close()

        before = snapshot()
        with (
            mock.patch.object(
                reader.store,
                "transaction",
                wraps=reader.store.transaction,
            ) as transaction,
            mock.patch(
                "cement_runtime.system.uuid.uuid4",
                side_effect=AssertionError("ID allocated"),
            ),
        ):
            result = reader.verify_function("tenant-a", "echo")
        after = snapshot()
        self.assertTrue(result.passed)
        self.assertEqual(result.entries, 1)
        self.assertTrue(all(check.passed for check in result.checks))
        checks = self._function_checks(result)
        self.assertEqual(
            checks["duplicate-input-digests"].detail,
            "1 entries have unique input digests",
        )
        self.assertEqual(
            checks["abi-canonicalizer-uniform"].detail,
            f"1 entries are compatible with current {ARTIFACT_ABI} + {CANONICALIZER}",
        )
        self.assertEqual(
            checks["sealed-passing-reports"].detail,
            "1 entries carry passing full-seal reports",
        )
        self.assertEqual(
            checks["current-promotion-receipts"].detail,
            "1 entries carry current valid promotion receipts",
        )
        document = result.document
        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(result.function_hash, document.function_hash)
        self.assertEqual(
            checks["function-hash-matches-snapshot"].detail,
            f"{document.function_hash} binds 1 snapshot entry/entries",
        )
        self.assertEqual(before, after)
        self.assertNotIn("INSERT INTO function_receipts", "\n".join(after))
        transaction.assert_called_once_with(write=False)
        authority.assert_not_called()
        clock.assert_not_called()

    def test_function_verification_duplicate_gate_and_runtime_defenses(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-duplicate"
        )
        duplicate_id = self._clone_promoted_function_entry(artifact_id)
        connection = sqlite3.connect(self.database)
        try:
            input_hash = connection.execute(
                "SELECT input_hash FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()[0]
        finally:
            connection.close()

        result = self.system.verify_function("tenant-a", "echo")
        checks = self._function_checks(result)
        self.assertFalse(result.passed)
        self.assertEqual(result.entries, 2)
        self._assert_function_checks(result, (False, True, True, True, False))
        self.assertFalse(checks["duplicate-input-digests"].passed)
        self.assertIn("duplicate digest", checks["duplicate-input-digests"].detail)
        self.assertIn(input_hash, checks["duplicate-input-digests"].detail)
        self.assertTrue(checks["abi-canonicalizer-uniform"].passed)
        self.assertTrue(checks["sealed-passing-reports"].passed)
        self.assertTrue(checks["current-promotion-receipts"].passed)
        self.assertFalse(checks["function-hash-matches-snapshot"].passed)
        self.assertIn(
            "duplicate input_hash", checks["function-hash-matches-snapshot"].detail
        )
        self.assertIsNone(result.document)
        self.assertIsNone(result.function_hash)

        connection = sqlite3.connect(self.database)
        try:
            before = connection.execute(
                "SELECT id, status FROM artifacts WHERE id IN (?, ?) ORDER BY id",
                (artifact_id, duplicate_id),
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual({status for _, status in before}, {"promoted"})
        with self.assertRaisesRegex(StateError, "exactly one active artifact match"):
            self.system.challenge(
                "tenant-a",
                "echo",
                {"x": 1},
                {"echo": {"x": 1}},
                reviewer="auditor",
            )
        fallback = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="duplicate-dispatch"
        )
        self.assertIsInstance(fallback, ReviewRequired)
        connection = sqlite3.connect(self.database)
        try:
            after = connection.execute(
                """
                SELECT status, promotion_hash FROM artifacts
                WHERE id IN (?, ?) ORDER BY id
                """,
                (artifact_id, duplicate_id),
            ).fetchall()
            ambiguity_events = connection.execute(
                """
                SELECT COUNT(*) FROM events
                WHERE kind = 'artifact.ambiguity_quarantined'
                """
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual({status for status, _ in after}, {"suspended"})
        self.assertTrue(all(receipt is None for _, receipt in after))
        self.assertEqual(ambiguity_events, 1)

    def test_function_verification_duplicate_detail_is_bounded_and_ordered(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        first, _, _ = self._promote_function_entry(
            {"x": 1}, "function-duplicate-detail-a"
        )
        second, _, _ = self._promote_function_entry(
            {"x": 2}, "function-duplicate-detail-b"
        )
        first_clones = (
            "artifact_dup_a1",
            "artifact_dup_a0",
            "artifact_dup_a2",
        )
        for index, duplicate_id in enumerate(first_clones):
            self._clone_promoted_function_entry(
                first,
                duplicate_id=duplicate_id,
                duplicate_report_id=f"report_dup_a{index}",
            )
        second_clone = "artifact_dup_b0"
        self._clone_promoted_function_entry(
            second,
            duplicate_id=second_clone,
            duplicate_report_id="report_dup_b0",
        )
        connection = sqlite3.connect(self.database)
        try:
            digest_rows = connection.execute(
                "SELECT id, input_hash FROM artifacts WHERE id IN (?, ?)",
                (first, second),
            ).fetchall()
        finally:
            connection.close()
        digest_by_id = {artifact_id: digest for artifact_id, digest in digest_rows}
        expected_groups = [
            (digest_by_id[first], sorted((first, *first_clones))[:3]),
            (digest_by_id[second], sorted((second, second_clone))[:3]),
        ]
        expected_groups.sort(key=lambda item: item[0])
        expected_detail = "2 duplicate digest(s): " + "; ".join(
            f"{digest}:{','.join(source_ids)}"
            for digest, source_ids in expected_groups
        )

        result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (False, True, True, True, False))
        self.assertEqual(
            self._function_checks(result)["duplicate-input-digests"].detail,
            expected_detail,
        )

    def test_function_verification_enumeration_orders_input_before_id(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        first, _, _ = self._promote_function_entry(
            {"x": 1}, "function-order-input-a"
        )
        second, _, _ = self._promote_function_entry(
            {"x": 2}, "function-order-input-b"
        )
        connection = sqlite3.connect(self.database)
        try:
            digest_rows = connection.execute(
                "SELECT id, input_hash FROM artifacts WHERE id IN (?, ?)",
                (first, second),
            ).fetchall()
        finally:
            connection.close()
        low, high = sorted(digest_rows, key=lambda row: row[1])
        low_clone = "artifact_zzz_low_input"
        high_clone = "artifact_000_high_input"
        self._clone_promoted_function_entry(
            low[0],
            duplicate_id=low_clone,
            duplicate_report_id="report_order_low",
        )
        self._clone_promoted_function_entry(
            high[0],
            duplicate_id=high_clone,
            duplicate_report_id="report_order_high",
        )
        expected_ids = [
            artifact_id
            for _, artifact_id in sorted(
                (
                    (low[1], low[0]),
                    (low[1], low_clone),
                    (high[1], high[0]),
                    (high[1], high_clone),
                )
            )
        ]
        with mock.patch.object(
            System,
            "_artifact_from_row",
            side_effect=IntegrityError("ordered failure"),
        ):
            result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (False, True, True, False, False))
        detail = self._function_checks(result)["current-promotion-receipts"].detail
        self.assertEqual(
            detail,
            "4 failure(s): "
            + "; ".join(
                f"{artifact_id}: ordered failure" for artifact_id in expected_ids[:3]
            ),
        )

    def test_function_verification_enumeration_orders_revision_before_input(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_ids = self._promote_three_function_entries("function-order-revision")
        connection = sqlite3.connect(self.database)
        try:
            digest_rows = connection.execute(
                "SELECT id, input_hash FROM artifacts WHERE id IN (?, ?, ?)",
                artifact_ids,
            ).fetchall()
            ordered_by_input = sorted(digest_rows, key=lambda row: row[1])
            revisions = {
                ordered_by_input[0][0]: 2,
                ordered_by_input[1][0]: 2,
                ordered_by_input[2][0]: 1,
            }
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            for artifact_id, revision in revisions.items():
                connection.execute(
                    "UPDATE artifacts SET operation_revision = ? WHERE id = ?",
                    (revision, artifact_id),
                )
            connection.commit()
        finally:
            connection.close()
        expected_ids = [
            artifact_id
            for artifact_id, _ in sorted(
                revisions.items(),
                key=lambda item: (
                    item[1],
                    next(
                        digest
                        for row_id, digest in digest_rows
                        if row_id == item[0]
                    ),
                    item[0],
                ),
            )
        ]
        with mock.patch.object(
            System,
            "_artifact_from_row",
            side_effect=IntegrityError("ordered failure"),
        ):
            result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (True, True, True, False, False))
        detail = self._function_checks(result)["current-promotion-receipts"].detail
        self.assertEqual(
            detail,
            "3 failure(s): "
            + "; ".join(
                f"{artifact_id}: ordered failure" for artifact_id in expected_ids
            ),
        )

    def test_function_verification_rejects_incompatible_artifact_constants(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_function_entries("function-constants")
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT id, artifact_json, artifact_hash FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'promoted'
                ORDER BY operation_revision, input_hash, id
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            target = rows[1]
            artifact_id = str(target["id"])
            original_text = str(target["artifact_json"])
            original_hash = str(target["artifact_hash"])
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.commit()

            corruptions = (
                ("abi", "cement-exact-lookup-v2"),
                ("canonicalizer", "cement-json-v2"),
            )
            for field, wrong_value in corruptions:
                with self.subTest(field=field):
                    raw = json.loads(original_text)
                    if field == "abi":
                        raw["abi"] = wrong_value
                    else:
                        raw["scope"]["canonicalizer"] = wrong_value
                    corrupted = canonicalize(raw)
                    connection.execute(
                        """
                        UPDATE artifacts SET artifact_json = ?, artifact_hash = ?
                        WHERE id = ?
                        """,
                        (corrupted.text, corrupted.digest, artifact_id),
                    )
                    connection.commit()

                    result = self.system.verify_function("tenant-a", "echo")
                    checks = self._function_checks(result)
                    self._assert_function_checks(
                        result, (True, False, False, False, False)
                    )
                    self.assertFalse(result.passed)
                    self.assertEqual(result.entries, 3)
                    self.assertIn(
                        artifact_id,
                        checks["abi-canonicalizer-uniform"].detail,
                    )
                    self.assertIn(
                        wrong_value,
                        checks["abi-canonicalizer-uniform"].detail,
                    )
                    self.assertIn(
                        "report artifact_hash binding mismatch",
                        checks["sealed-passing-reports"].detail,
                    )
                    self.assertIn(
                        "unsupported",
                        checks["current-promotion-receipts"].detail,
                    )
                    self.assertIn(
                        "unsupported",
                        checks["function-hash-matches-snapshot"].detail,
                    )
                    self.assertIsNone(result.document)
                    self.assertIsNone(result.function_hash)

                    connection.execute(
                        """
                        UPDATE artifacts SET artifact_json = ?, artifact_hash = ?
                        WHERE id = ?
                        """,
                        (original_text, original_hash, artifact_id),
                    )
                    connection.commit()
        finally:
            connection.close()

    def test_function_verification_structures_malformed_artifact_metadata(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-malformed-artifact"
        )
        connection = sqlite3.connect(self.database)
        try:
            original_text = connection.execute(
                "SELECT artifact_json FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()[0]
            raw_scope = json.loads(original_text)
            raw_scope["scope"] = []
            raw_large = json.loads(original_text)
            raw_large["padding"] = "x" * (ARTIFACT_MAX_BYTES + 1)
            corruptions = (
                ("non-object", "[]", "artifact document is not an object"),
                ("non-object-scope", canonicalize(raw_scope).text, "canonicalizer=None"),
                ("malformed", "{", "JSON"),
                (
                    "oversized",
                    json.dumps(raw_large, sort_keys=True, separators=(",", ":")),
                    "byte",
                ),
            )
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.commit()
            for label, artifact_json, detail in corruptions:
                with self.subTest(corruption=label):
                    connection.execute(
                        "UPDATE artifacts SET artifact_json = ? WHERE id = ?",
                        (artifact_json, artifact_id),
                    )
                    connection.commit()
                    result = self.system.verify_function("tenant-a", "echo")
                    self._assert_function_checks(
                        result, (True, False, True, False, False)
                    )
                    abi_detail = self._function_checks(result)[
                        "abi-canonicalizer-uniform"
                    ].detail
                    self.assertIn(artifact_id, abi_detail)
                    self.assertIn(detail, abi_detail)
                    self.assertIn(
                        artifact_id,
                        self._function_checks(result)[
                            "function-hash-matches-snapshot"
                        ].detail,
                    )
                    connection.execute(
                        "UPDATE artifacts SET artifact_json = ? WHERE id = ?",
                        (original_text, artifact_id),
                    )
                    connection.commit()
        finally:
            connection.close()

    def test_function_verification_rehashes_sealed_reports_off_dispatch(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_function_entries("function-report")
        baseline = self.system.verify_function("tenant-a", "echo")
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT id, input_json, verified_report_id FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'promoted'
                ORDER BY operation_revision, input_hash, id
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            target = rows[1]
            artifact_id = str(target["id"])
            input_value = json.loads(str(target["input_json"]))
            report_id = str(target["verified_report_id"])
            connection.execute("DROP TRIGGER artifact_tests_no_update")
            connection.execute(
                """
                UPDATE artifact_tests SET detail = 'corrupt child test'
                WHERE report_id = ? AND test_key = (
                    SELECT MIN(test_key) FROM artifact_tests WHERE report_id = ?
                )
                """,
                (report_id, report_id),
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_function("tenant-a", "echo")
        checks = self._function_checks(result)
        self._assert_function_checks(result, (True, True, False, True, True))
        self.assertFalse(result.passed)
        self.assertEqual(result.entries, 3)
        self.assertIn(
            artifact_id,
            checks["sealed-passing-reports"].detail,
        )
        self.assertIn(
            "verification report test set mismatch",
            checks["sealed-passing-reports"].detail,
        )
        self.assertTrue(
            all(
                checks[key].passed
                for key in (
                    "duplicate-input-digests",
                    "abi-canonicalizer-uniform",
                    "current-promotion-receipts",
                    "function-hash-matches-snapshot",
                )
            )
        )
        self.assertEqual(result.function_hash, baseline.function_hash)
        self.assertIsNone(result.document)
        with mock.patch.object(
            System,
            "_test_snapshot",
            side_effect=AssertionError("dispatch rehashed sealed tests"),
        ):
            resolved = self.system.handle(
                "tenant-a",
                "echo",
                input_value,
                request_id="tampered-child-fast-path",
            )
        self.assertIsInstance(resolved, Resolved)
        assert isinstance(resolved, Resolved)
        self.assertEqual(resolved.artifact_id, artifact_id)

    def test_function_verification_rejects_later_entry_receipt(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_function_entries("function-receipt")
        baseline = self.system.verify_function("tenant-a", "echo")
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT id FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'promoted'
                ORDER BY operation_revision, input_hash, id
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            artifact_id = str(rows[-1]["id"])
            connection.execute(
                "UPDATE artifacts SET promotion_hash = ? WHERE id = ?",
                ("0" * 64, artifact_id),
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_function("tenant-a", "echo")
        checks = self._function_checks(result)
        self._assert_function_checks(result, (True, True, True, False, True))
        self.assertFalse(result.passed)
        self.assertEqual(result.entries, 3)
        self.assertIn(
            artifact_id,
            checks["current-promotion-receipts"].detail,
        )
        self.assertIn(
            "artifact promotion receipt mismatch",
            checks["current-promotion-receipts"].detail,
        )
        self.assertTrue(
            all(
                checks[key].passed
                for key in (
                    "duplicate-input-digests",
                    "abi-canonicalizer-uniform",
                    "sealed-passing-reports",
                    "function-hash-matches-snapshot",
                )
            )
        )
        self.assertIsNotNone(result.function_hash)
        self.assertEqual(result.function_hash, baseline.function_hash)
        self.assertIsNone(result.document)

    def test_function_verification_rejects_stale_promoted_revision(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-stale-revision"
        )
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                """
                UPDATE operations SET revision = revision + 1
                WHERE partition = 'tenant-a' AND name = 'echo'
                """
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_function("tenant-a", "echo")
        checks = self._function_checks(result)
        self._assert_function_checks(result, (True, True, True, False, False))
        self.assertFalse(result.passed)
        self.assertEqual(result.entries, 1)
        for key in (
            "current-promotion-receipts",
            "function-hash-matches-snapshot",
        ):
            self.assertIn(artifact_id, checks[key].detail)
            self.assertIn("operation revision 1 does not match current 2", checks[key].detail)
        self.assertIsNone(result.document)
        self.assertIsNone(result.function_hash)

    def test_function_verification_rejects_current_policy_hash_mismatch(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-policy-hash"
        )
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                """
                UPDATE operations SET policy_hash = ?
                WHERE partition = 'tenant-a' AND name = 'echo'
                """,
                ("0" * 64,),
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_function("tenant-a", "echo")
        checks = self._function_checks(result)
        self._assert_function_checks(result, (True, True, True, False, False))
        self.assertFalse(result.passed)
        self.assertEqual(result.entries, 1)
        receipt_detail = checks["current-promotion-receipts"].detail
        projection_detail = checks["function-hash-matches-snapshot"].detail
        self.assertTrue(receipt_detail.startswith("2 failure(s): "))
        self.assertIn("operation policy digest does not match policy_hash", receipt_detail)
        self.assertIn(artifact_id, receipt_detail)
        self.assertIn("policy hash does not match current operation", receipt_detail)
        self.assertIn(artifact_id, projection_detail)
        self.assertIn("policy hash does not match current operation", projection_detail)
        self.assertIsNone(result.document)
        self.assertIsNone(result.function_hash)

    def test_function_verification_pins_row_scope_types_and_policy_bytes(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-row-scope"
        )
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise AssertionError("promoted row disappeared")
        artifact = System._artifact_from_row(row)
        corruptions = (
            (
                "boolean-revision",
                "operation_revision",
                True,
                "stored operation revision is not an integer",
            ),
            (
                "policy-json",
                "policy_json",
                canonicalize(CompilePolicy(3, 1, 0).as_json()).text,
                "policy JSON does not match current operation",
            ),
        )
        for label, field, value, detail in corruptions:
            with self.subTest(corruption=label):
                row_copy = dict(row)
                row_copy[field] = value
                with (
                    mock.patch.object(
                        System, "_promoted_function_rows", return_value=[row_copy]
                    ),
                    mock.patch.object(
                        System, "_artifact_from_row", return_value=artifact
                    ),
                ):
                    result = self.system.verify_function("tenant-a", "echo")
                self._assert_function_checks(
                    result, (True, True, True, False, False)
                )
                checks = self._function_checks(result)
                self.assertIn(
                    detail, checks["current-promotion-receipts"].detail
                )
                self.assertIn(
                    detail, checks["function-hash-matches-snapshot"].detail
                )

    def test_function_verification_structures_receipt_validation_errors(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-receipt-validation"
        )
        with mock.patch.object(
            System,
            "_validate_promoted",
            side_effect=ValidationError("receipt validation probe"),
        ):
            result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (True, True, True, False, True))
        detail = self._function_checks(result)["current-promotion-receipts"].detail
        self.assertIn(artifact_id, detail)
        self.assertIn("receipt validation probe", detail)

    def test_function_verification_expected_hash_detects_set_growth(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_function_entry({"x": 1}, "function-hash-one")
        first = self.system.verify_function("tenant-a", "echo")
        first_hash = first.function_hash
        self.assertIsNotNone(first_hash)
        assert first_hash is not None
        self._promote_function_entry({"x": 2}, "function-hash-two")

        changed = self.system.verify_function(
            "tenant-a", "echo", expected_function_hash=first_hash
        )
        checks = self._function_checks(changed)
        self._assert_function_checks(changed, (True, True, True, True, False))
        self.assertEqual(changed.entries, 2)
        self.assertTrue(
            all(
                checks[key].passed
                for key in (
                    "duplicate-input-digests",
                    "abi-canonicalizer-uniform",
                    "sealed-passing-reports",
                    "current-promotion-receipts",
                )
            )
        )
        self.assertFalse(checks["function-hash-matches-snapshot"].passed)
        self.assertEqual(
            checks["function-hash-matches-snapshot"].detail,
            "function does not match expected_function_hash",
        )
        self.assertNotEqual(changed.function_hash, first_hash)
        self.assertIsNone(changed.document)
        changed_hash = changed.function_hash
        self.assertIsNotNone(changed_hash)
        assert changed_hash is not None

        current = self.system.verify_function(
            "tenant-a", "echo", expected_function_hash=changed_hash
        )
        self.assertTrue(current.passed)
        document = current.document
        self.assertIsNotNone(document)
        assert document is not None
        entries = document.value["entries"]
        self.assertIsInstance(entries, list)
        assert type(entries) is list
        self.assertEqual(len(entries), 2)

    def test_function_verification_pins_projected_input_and_output_digests(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-projected-digests"
        )
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise AssertionError("promoted row disappeared")
        artifact = System._artifact_from_row(row)
        corruptions = (
            (
                "input",
                mock.Mock(
                    input=canonicalize({"changed": "input"}),
                    output=artifact.output,
                ),
            ),
            (
                "output",
                mock.Mock(
                    input=artifact.input,
                    output=canonicalize({"changed": "output"}),
                ),
            ),
        )
        for field, altered in corruptions:
            with self.subTest(field=field):
                with mock.patch.object(
                    System, "_artifact_from_row", return_value=altered
                ):
                    result = self.system.verify_function("tenant-a", "echo")
                self._assert_function_checks(
                    result, (True, True, True, True, False)
                )
                self.assertEqual(
                    self._function_checks(result)[
                        "function-hash-matches-snapshot"
                    ].detail,
                    "1 unprojectable entry/entries: "
                    f"{artifact_id}: {field} digest changed during projection",
                )

    def test_function_verification_pins_document_and_normalization_self_checks(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-self-checks"
        )
        real_build = build_function

        def altered_build(**kwargs):
            entries = list(kwargs["entries"])
            entry = entries[0]
            entries[0] = FunctionEntry(
                input=entry.input,
                output=entry.output,
                artifact_hash="0" * 64,
                evidence_snapshot_hash=entry.evidence_snapshot_hash,
                entry_seal=entry.entry_seal,
                report_details_hash=entry.report_details_hash,
                report_test_set_hash=entry.report_test_set_hash,
            )
            kwargs["entries"] = entries
            return real_build(**kwargs)

        with mock.patch("cement_runtime.system.build_function", side_effect=altered_build):
            altered_document = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(
            altered_document, (True, True, True, True, False)
        )
        self.assertIn(
            f"{artifact_id} function entry changed during projection",
            self._function_checks(altered_document)[
                "function-hash-matches-snapshot"
            ].detail,
        )

        with mock.patch(
            "cement_runtime.system.validate_function",
            return_value=mock.Mock(text="changed normalization"),
        ):
            altered_text = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(altered_text, (True, True, True, True, False))
        self.assertEqual(
            self._function_checks(altered_text)[
                "function-hash-matches-snapshot"
            ].detail,
            "function normalization changed during self-check",
        )

    def test_function_verification_compares_entries_in_input_hash_order(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        for value in range(1, 7):
            self._promote_function_entry(
                {"x": value}, f"function-entry-order-{value}"
            )
        connection = sqlite3.connect(self.database)
        try:
            rows = connection.execute(
                """
                SELECT id, input_hash, artifact_hash FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'promoted'
                """
            ).fetchall()
        finally:
            connection.close()
        input_order = [row[0] for row in sorted(rows, key=lambda row: row[1])]
        artifact_order = [row[0] for row in sorted(rows, key=lambda row: row[2])]
        self.assertNotEqual(input_order, artifact_order)
        result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (True, True, True, True, True))


    def test_function_verification_matches_independent_scoped_membership(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "echo", policy=policy)
        retired_id, _, _ = self._promote_function_entry(
            {"x": -1}, "membership-retired"
        )
        self.assertEqual(
            self.system.revise_operation(
                "tenant-a", "echo", policy=policy, revised_by="owner"
            ),
            2,
        )

        shared_output = {"shared": True}
        target_ids = tuple(
            self._promote_function_entry(
                {"x": value},
                f"membership-target-{value}",
                corrected=shared_output,
            )[0]
            for value in (1, 2, 3)
        )
        self._confirm_scope(
            "tenant-a",
            "echo",
            {"x": 99},
            "membership-draft-1",
            reviewer="alice",
            corrected=shared_output,
        )
        self._confirm_scope(
            "tenant-a",
            "echo",
            {"x": 99},
            "membership-draft-2",
            reviewer="bob",
            corrected=shared_output,
        )
        draft_build = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(draft_build.created), 1)
        draft_id = draft_build.created[0]

        self.system.register_operation("tenant-a", "other", policy=policy)
        other_operation_id, _, _ = self._promote_scope(
            "tenant-a",
            "other",
            {"x": 1},
            "membership-other-operation",
            corrected=shared_output,
        )
        self.system.register_operation("tenant-b", "echo", policy=policy)
        other_partition_id, _, _ = self._promote_scope(
            "tenant-b",
            "echo",
            {"x": 1},
            "membership-other-partition",
            corrected=shared_output,
        )

        with self.system.store.transaction(write=False) as connection:
            operation = connection.execute(
                """
                SELECT * FROM operations
                WHERE partition = 'tenant-a' AND name = 'echo'
                """
            ).fetchone()
            if operation is None:
                raise AssertionError("target operation disappeared")
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND operation_revision = ? AND status = 'promoted'
                ORDER BY input_hash, id
                """,
                (operation["revision"],),
            ).fetchall()
            self.assertEqual(
                {str(row["id"]) for row in rows}, set(target_ids)
            )
            expected_entries = []
            for row in rows:
                report = connection.execute(
                    """
                    SELECT * FROM test_reports
                    WHERE id = ? AND artifact_id = ?
                    """,
                    (row["verified_report_id"], row["id"]),
                ).fetchone()
                if report is None:
                    raise AssertionError("bound report disappeared")
                expected_entries.append(
                    FunctionEntry(
                        input=json.loads(str(row["input_json"])),
                        output=json.loads(str(row["output_json"])),
                        artifact_hash=str(row["artifact_hash"]),
                        evidence_snapshot_hash=str(row["evidence_snapshot_hash"]),
                        entry_seal=_function_entry_seal(row, report),
                        report_details_hash=str(report["details_hash"]),
                        report_test_set_hash=str(report["test_set_hash"]),
                    )
                )
            expected = build_function(
                partition="tenant-a",
                operation="echo",
                operation_revision=int(operation["revision"]),
                policy_hash=str(operation["policy_hash"]),
                entries=expected_entries,
            )
            decoys = connection.execute(
                """
                SELECT id, status, artifact_hash FROM artifacts
                WHERE id IN (?, ?, ?, ?)
                """,
                (retired_id, draft_id, other_operation_id, other_partition_id),
            ).fetchall()

        self.assertEqual(
            {str(row["id"]): str(row["status"]) for row in decoys},
            {
                retired_id: "retired",
                draft_id: "draft",
                other_operation_id: "promoted",
                other_partition_id: "promoted",
            },
        )
        result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (True, True, True, True, True))
        document = result.document
        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document.text, expected.text)
        self.assertEqual(document.function_hash, expected.function_hash)
        self.assertEqual(result.entries, 3)
        actual = json.loads(document.text)
        self.assertTrue(
            all(entry["output"] == shared_output for entry in actual["entries"])
        )
        self.assertTrue(
            {entry["artifact_hash"] for entry in actual["entries"]}.isdisjoint(
                {str(row["artifact_hash"]) for row in decoys}
            )
        )
        self.assertFalse(
            evaluate(document, input_json=canonicalize({"x": 4})).matched
        )
        self.assertTrue(self.system.verify_function("tenant-a", "other").passed)
        self.assertTrue(self.system.verify_function("tenant-b", "echo").passed)

    def test_function_verification_uses_receipt_bound_report(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "bound-report"
        )
        baseline = self.system.verify_function("tenant-a", "echo")
        with self.system.store.transaction(write=False) as connection:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if artifact is None:
                raise AssertionError("promoted artifact disappeared")
            original_id = str(artifact["verified_report_id"])
            original = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?", (original_id,)
            ).fetchone()
            if original is None:
                raise AssertionError("bound report disappeared")
            original_details_hash = str(original["details_hash"])
            original_test_set_hash = str(original["test_set_hash"])

        latest = self.system.verify(
            "tenant-a", artifact_id, verified_by="later-verifier"
        )
        self.assertTrue(latest.passed)
        self.assertNotEqual(latest.id, original_id)
        with self.system.store.transaction(write=False) as connection:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            latest_row = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?", (latest.id,)
            ).fetchone()
            if artifact is None or latest_row is None:
                raise AssertionError("report rows disappeared")
            self.assertEqual(str(artifact["verified_report_id"]), original_id)
            self.assertNotEqual(
                str(latest_row["details_hash"]), original_details_hash
            )

        result = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(result, (True, True, True, True, True))
        self.assertEqual(result.function_hash, baseline.function_hash)
        document = result.document
        self.assertIsNotNone(document)
        assert document is not None
        entry_report = json.loads(document.text)["entries"][0]["report"]
        self.assertEqual(entry_report["details_hash"], original_details_hash)
        self.assertEqual(entry_report["test_set_hash"], original_test_set_hash)
        self.assertNotEqual(
            entry_report["details_hash"], str(latest_row["details_hash"])
        )

    def test_function_verification_binds_exact_report_id_and_owner(self) -> None:
        self.system.register_operation(
            "tenant-a", "report-identity", policy=CompilePolicy(2, 1, 0)
        )
        artifact_id, _, _ = self._promote_scope(
            "tenant-a",
            "report-identity",
            {"x": 1},
            "function-report-identity",
        )
        old_hash, new_hash = self._insert_report_variant(
            artifact_id,
            "report_newer_variant",
            marker="newer",
        )
        original = self.system.verify_function("tenant-a", "report-identity")
        self.assertTrue(original.passed)
        assert original.document is not None
        original_entries = original.document.value.get("entries")
        assert isinstance(original_entries, list)
        original_entry = original_entries[0]
        assert isinstance(original_entry, dict)
        original_report = original_entry.get("report")
        assert isinstance(original_report, dict)
        self.assertEqual(original_report.get("details_hash"), old_hash)

        self._bind_report(artifact_id, "report_newer_variant")
        rebound = self.system.verify_function("tenant-a", "report-identity")
        self.assertTrue(rebound.passed)
        assert rebound.document is not None
        rebound_entries = rebound.document.value.get("entries")
        assert isinstance(rebound_entries, list)
        rebound_entry = rebound_entries[0]
        assert isinstance(rebound_entry, dict)
        rebound_report = rebound_entry.get("report")
        assert isinstance(rebound_report, dict)
        self.assertEqual(rebound_report.get("details_hash"), new_hash)

        self.system.register_operation(
            "tenant-a", "report-owner", policy=CompilePolicy(2, 1, 0)
        )
        target, _, _ = self._promote_scope(
            "tenant-a",
            "report-owner",
            {"x": "target"},
            "function-report-owner-target",
        )
        foreign_owner, _, _ = self._promote_scope(
            "tenant-a",
            "report-owner",
            {"x": "foreign"},
            "function-report-owner-foreign",
        )
        self._insert_report_variant(
            target,
            "report_foreign_bound",
            marker="foreign-owner",
            owner_id=foreign_owner,
        )
        self._bind_report(target, "report_foreign_bound")
        foreign = self.system.verify_function("tenant-a", "report-owner")
        self._assert_function_checks(foreign, (True, True, False, False, False))
        checks = self._function_checks(foreign)
        self.assertIn(target, checks["sealed-passing-reports"].detail)
        self.assertIn(
            "missing passing bound report",
            checks["sealed-passing-reports"].detail,
        )
        self.assertIn(target, checks["function-hash-matches-snapshot"].detail)
        self.assertIn(
            "bound report is missing",
            checks["function-hash-matches-snapshot"].detail,
        )

    def test_function_verification_rejects_each_report_row_binding(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-report-bindings"
        )
        connection = sqlite3.connect(self.database)
        try:
            report_id = connection.execute(
                "SELECT verified_report_id FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()[0]
            connection.execute("DROP TRIGGER test_reports_no_update")
            original = connection.execute(
                """
                SELECT build_hash, policy_hash, evidence_snapshot_hash
                FROM test_reports WHERE id = ?
                """,
                (report_id,),
            ).fetchone()
            for index, field in enumerate(
                ("build_hash", "policy_hash", "evidence_snapshot_hash")
            ):
                with self.subTest(field=field):
                    connection.execute(
                        f"UPDATE test_reports SET {field} = ? WHERE id = ?",
                        (str(index) * 64, report_id),
                    )
                    connection.commit()
                    result = self.system.verify_function("tenant-a", "echo")
                    self._assert_function_checks(
                        result, (True, True, False, False, True)
                    )
                    detail = self._function_checks(result)[
                        "sealed-passing-reports"
                    ].detail
                    self.assertIn(artifact_id, detail)
                    self.assertIn(f"report {field} binding mismatch", detail)
                    connection.execute(
                        f"UPDATE test_reports SET {field} = ? WHERE id = ?",
                        (original[index], report_id),
                    )
                    connection.commit()
        finally:
            connection.close()

    def test_function_verification_structures_report_validator_defects(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "function-report-validator"
        )

        def assert_defect(result: FunctionVerification, detail: str) -> None:
            self._assert_function_checks(
                result, (True, True, False, False, True)
            )
            report_detail = self._function_checks(result)[
                "sealed-passing-reports"
            ].detail
            self.assertIn(artifact_id, report_detail)
            self.assertIn(detail, report_detail)

        with self.subTest(defect="non-object"):
            with mock.patch.object(
                System,
                "_validate_report",
                return_value=mock.Mock(value=[]),
            ):
                result = self.system.verify_function("tenant-a", "echo")
            assert_defect(result, "report details are not an object")

        with self.subTest(defect="scope"):
            with mock.patch.object(
                System,
                "_validate_report",
                return_value=mock.Mock(value={"scope_hash": "0" * 64}),
            ):
                result = self.system.verify_function("tenant-a", "echo")
            assert_defect(result, "report scope binding mismatch")

        with self.subTest(defect="validation-error"):
            with mock.patch.object(
                System,
                "_validate_report",
                side_effect=ValidationError("report validation probe"),
            ):
                result = self.system.verify_function("tenant-a", "echo")
            assert_defect(result, "report validation probe")

    def test_function_verification_rejects_coherent_failed_report(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        artifact_id, _, _ = self._promote_function_entry(
            {"x": 1}, "failed-report"
        )
        with self.system.store.transaction(write=True) as connection:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if artifact is None:
                raise AssertionError("promoted artifact disappeared")
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (artifact["verified_report_id"],),
            ).fetchone()
            if report is None:
                raise AssertionError("bound report disappeared")
            details_value = json.loads(str(report["details_json"]))
            details_value["failures"] = ["coherently sealed failure"]
            details = canonicalize(details_value)
            connection.execute("DROP TRIGGER test_reports_no_update")
            connection.execute(
                """
                UPDATE test_reports
                SET passed = 0, details_json = ?, details_hash = ?
                WHERE id = ?
                """,
                (details.text, details.digest, report["id"]),
            )
            failed_report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?", (report["id"],)
            ).fetchone()
            if failed_report is None:
                raise AssertionError("failed report disappeared")
            self.system._validate_report(
                connection, failed_report, verify_test_set=True
            )
            promotion_hash = self._promotion_hash(artifact, failed_report)
            connection.execute(
                "UPDATE artifacts SET promotion_hash = ? WHERE id = ?",
                (promotion_hash, artifact_id),
            )

        result = self.system.verify_function("tenant-a", "echo")
        checks = self._function_checks(result)
        self._assert_function_checks(result, (True, True, False, False, True))
        self.assertIn(
            "missing passing bound report", checks["sealed-passing-reports"].detail
        )
        self.assertIn(
            "no passing bound report", checks["current-promotion-receipts"].detail
        )
        self.assertIsNotNone(result.function_hash)
        self.assertIsNone(result.document)
        with self.system.store.transaction(write=False) as connection:
            row = connection.execute(
                "SELECT status, promotion_hash FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            self.assertEqual(tuple(row), ("promoted", promotion_hash))

    def test_function_verification_structures_missing_bound_reports(self) -> None:
        for label, report_id in (("null", None), ("dangling", "report_missing")):
            with self.subTest(binding=label):
                operation = f"missing-report-{label}"
                self.system.register_operation(
                    "tenant-a", operation, policy=CompilePolicy(2, 1, 0)
                )
                artifact_id, _, _ = self._promote_scope(
                    "tenant-a",
                    operation,
                    {"x": label},
                    f"function-missing-report-{label}",
                )
                connection = sqlite3.connect(self.database)
                try:
                    connection.execute("PRAGMA ignore_check_constraints = ON")
                    connection.execute(
                        "UPDATE artifacts SET verified_report_id = ? WHERE id = ?",
                        (report_id, artifact_id),
                    )
                    connection.commit()
                finally:
                    connection.close()
                result = self.system.verify_function("tenant-a", operation)
                self._assert_function_checks(
                    result, (True, True, False, False, False)
                )
                checks = self._function_checks(result)
                self.assertIn(
                    "missing passing bound report",
                    checks["sealed-passing-reports"].detail,
                )
                self.assertEqual(
                    checks["function-hash-matches-snapshot"].detail,
                    "1 unprojectable entry/entries: "
                    f"{artifact_id}: bound report is missing",
                )

    def test_function_verification_fails_closed_at_aggregate_limits(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_function_entry({"x": 1}, "limit-one")
        self._promote_function_entry({"x": 2}, "limit-two")

        with (
            mock.patch("cement_runtime.system.FUNCTION_MAX_ENTRIES", 1),
            mock.patch.object(
                System,
                "_promoted_function_rows",
                side_effect=AssertionError("oversized set was materialized"),
            ),
        ):
            oversized = self.system.verify_function("tenant-a", "echo")
        self._assert_function_checks(
            oversized, (False, False, False, False, False)
        )
        self.assertFalse(oversized.passed)
        self.assertEqual(oversized.entries, 2)
        self.assertTrue(
            all("not evaluated" in check.detail for check in oversized.checks[:4])
        )
        self.assertIn(
            "exceeds FUNCTION_MAX_ENTRIES=1",
            self._function_checks(oversized)[
                "function-hash-matches-snapshot"
            ].detail,
        )
        self.assertIsNone(oversized.function_hash)
        self.assertIsNone(oversized.document)

        for name, value in (
            ("FUNCTION_MAX_BYTES", 64),
            ("FUNCTION_MAX_ITEMS", 1),
        ):
            with self.subTest(limit=name):
                with mock.patch(f"cement_runtime.function.{name}", value):
                    result = self.system.verify_function("tenant-a", "echo")
                self._assert_function_checks(
                    result, (True, True, True, True, False)
                )
                self.assertFalse(result.passed)
                self.assertEqual(result.entries, 2)
                self.assertIn(
                    "exceeds",
                    self._function_checks(result)[
                        "function-hash-matches-snapshot"
                    ].detail,
                )
                self.assertIsNone(result.function_hash)
                self.assertIsNone(result.document)

    def test_function_verification_preserves_safe_same_input_replacement(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        first, _, _ = self._promote_function_entry(
            {"x": 1}, "function-replacement"
        )
        before_evidence = self.system.verify_function("tenant-a", "echo")
        _, suspended = self.system.challenge(
            "tenant-a",
            "echo",
            {"x": 1},
            {"echo": {"x": 1}},
            reviewer="auditor",
        )
        self.assertFalse(suspended)
        after_evidence = self.system.verify_function("tenant-a", "echo")
        self.assertTrue(after_evidence.passed)
        self._assert_function_checks(after_evidence, (True, True, True, True, True))
        self.assertEqual(after_evidence.function_hash, before_evidence.function_hash)
        build = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(build.created), 1)
        second = build.created[0]
        report = self.system.verify("tenant-a", second)
        self.assertTrue(report.passed)
        promotion = self.system.promote(
            "tenant-a",
            second,
            scope_hash=report.scope_hash,
            promoted_by="release-manager",
        )
        self.assertEqual(promotion.replaced_artifact_ids, (first,))
        connection = sqlite3.connect(self.database)
        try:
            rows = connection.execute(
                """
                SELECT id FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND input_hash = (SELECT input_hash FROM artifacts WHERE id = ?)
                  AND status = 'promoted'
                """,
                (second,),
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(rows, [(second,)])
        self.assertTrue(self.system.verify_function("tenant-a", "echo").passed)

    def test_function_verification_race_returns_one_coherent_snapshot(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "echo", policy=policy)
        self._promote_function_entry({"x": 1}, "function-race")
        reader = System(self.database)
        writer = System(self.database)
        before = reader.verify_function("tenant-a", "echo")
        before_hash = before.function_hash
        self.assertIsNotNone(before_hash)
        assert before_hash is not None
        enumerated = threading.Event()
        release = threading.Event()
        commit_attempted = threading.Event()
        writer_finished = threading.Event()
        original_rows = System._promoted_function_rows
        original_connect = writer.store._connect
        verified = []
        revisions = []
        errors = []

        def blocked_rows(connection, *, partition, operation):
            rows = original_rows(
                connection, partition=partition, operation=operation
            )
            enumerated.set()
            if not release.wait(timeout=3):
                raise AssertionError("race release timed out")
            return rows

        def traced_writer_connect():
            connection = original_connect()

            def trace(statement: str) -> None:
                if statement.strip().upper() == "COMMIT":
                    commit_attempted.set()

            connection.set_trace_callback(trace)
            return connection

        def run_verifier() -> None:
            try:
                verified.append(reader.verify_function("tenant-a", "echo"))
            except Exception as exc:  # thread handoff
                errors.append(exc)

        def run_writer() -> None:
            try:
                revisions.append(
                    writer.revise_operation(
                        "tenant-a",
                        "echo",
                        policy=policy,
                        revised_by="owner",
                    )
                )
            except Exception as exc:  # thread handoff
                errors.append(exc)
            finally:
                writer_finished.set()

        with (
            mock.patch.object(
                System, "_promoted_function_rows", side_effect=blocked_rows
            ),
            mock.patch.object(
                writer.store, "_connect", side_effect=traced_writer_connect
            ),
        ):
            verifier = threading.Thread(target=run_verifier)
            verifier.start()
            self.assertTrue(enumerated.wait(timeout=2))
            revision_writer = threading.Thread(target=run_writer)
            revision_writer.start()
            self.assertTrue(commit_attempted.wait(timeout=2))
            self.assertFalse(writer_finished.wait(timeout=0.1))
            release.set()
            verifier.join(timeout=5)
            revision_writer.join(timeout=5)
        self.assertFalse(verifier.is_alive())
        self.assertFalse(revision_writer.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(writer_finished.is_set())
        self.assertEqual(revisions, [2])
        self.assertEqual(len(verified), 1)
        self.assertTrue(verified[0].passed)
        self.assertEqual(verified[0].entries, 1)
        self.assertEqual(verified[0].function_hash, before_hash)
        old_document = verified[0].document
        self.assertIsNotNone(old_document)
        assert old_document is not None
        old_scope = old_document.value["scope"]
        self.assertIsInstance(old_scope, dict)
        assert type(old_scope) is dict
        self.assertEqual(old_scope["operation_revision"], 1)

        after = reader.verify_function("tenant-a", "echo")
        self.assertTrue(after.passed)
        self.assertEqual(after.entries, 0)
        self.assertNotEqual(after.function_hash, before_hash)
        new_document = after.document
        self.assertIsNotNone(new_document)
        assert new_document is not None
        new_scope = new_document.value["scope"]
        self.assertIsInstance(new_scope, dict)
        assert type(new_scope) is dict
        self.assertEqual(new_scope["operation_revision"], 2)


    def test_verify_drafts_empty_set_and_public_models(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        result = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertIsInstance(result, DraftVerification)
        self.assertTrue(result.passed)
        self.assertEqual(result.operation_revision, 1)
        self.assertEqual(result.entries, ())
        self.assertEqual(result.skipped, ())
        self.assertEqual(
            FUNCTION_ENTRY_SEAL_ABI,
            "cement-function-entry-seal-v1",
        )
        self.assertFalse(hasattr(result, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            result.passed = False  # type: ignore[misc]
        with self.assertRaises(TypeError):
            self.system.verify_drafts("tenant-a", "echo")  # type: ignore[call-arg]

    def test_verify_drafts_uses_shared_projection_and_one_locked_batch(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        project = self.system._project_current_build
        with (
            mock.patch.object(
                self.system,
                "_project_current_build",
                wraps=project,
            ) as projected,
            mock.patch.object(
                self.system.store,
                "transaction",
                wraps=self.system.store.transaction,
            ) as transaction,
        ):
            created = self._compile_three_drafts("batch-pass")
            result = self.system.verify_drafts(
                "tenant-a",
                "echo",
                verified_by="batch-verifier",
            )
        self.assertTrue(result.passed)
        self.assertEqual(len(result.entries), 3)
        self.assertEqual(result.skipped, ())
        self.assertEqual(projected.call_count, 9)
        self.assertEqual(
            transaction.call_args_list[-2:],
            [mock.call(write=False), mock.call(write=True)],
        )
        self.assertTrue(all(isinstance(entry, DraftEntry) for entry in result.entries))
        self.assertTrue(all(entry.report.passed for entry in result.entries))
        self.assertTrue(all(entry.report.tests == 8 for entry in result.entries))
        self.assertTrue(all(entry.entry_seal is not None for entry in result.entries))
        self.assertTrue(
            all(
                len(entry.entry_seal or "") == 64
                and int(entry.entry_seal or "0", 16) >= 0
                for entry in result.entries
            )
        )
        with self.system.store.transaction(write=False) as connection:
            rows = connection.execute(
                """
                SELECT id, input_hash, status, verified_report_id FROM artifacts
                WHERE id IN (?, ?, ?) ORDER BY input_hash, sequence, id
                """,
                created,
            ).fetchall()
            event_kinds = [
                str(row["kind"])
                for row in connection.execute(
                    """
                    SELECT kind FROM events
                    WHERE subject_id IN (?, ?, ?)
                      AND kind IN ('artifact.verified', 'artifact.verification_failed')
                    ORDER BY sequence
                    """,
                    created,
                )
            ]
        self.assertEqual(
            [entry.artifact_id for entry in result.entries],
            [str(row["id"]) for row in rows],
        )
        self.assertTrue(all(row["status"] == "verified" for row in rows))
        self.assertTrue(all(row["verified_report_id"] is not None for row in rows))
        self.assertEqual(event_kinds, ["artifact.verified"] * 3)


    def test_verify_drafts_locked_recheck_excludes_revision_writer(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "echo", policy=policy)
        created = self._compile_three_drafts("batch-lock")
        with self.system.store.transaction(write=False) as connection:
            expected_ids = tuple(
                str(row["id"])
                for row in connection.execute(
                    """
                    SELECT id FROM artifacts WHERE id IN (?, ?, ?)
                    ORDER BY input_hash, sequence, id
                    """,
                    created,
                )
            )

        writer = System(self.database, clock_us=self.clock)
        original_plan = self.system._draft_verification_plan
        original_verify_row = self.system._verify_row
        original_writer_connect = writer.store._connect
        enumerated = threading.Event()
        allow_plan_return = threading.Event()
        batch_writing = threading.Event()
        allow_batch_finish = threading.Event()
        batch_finished = threading.Event()
        writer_attempted = threading.Event()
        writer_committed = threading.Event()
        writer_finished = threading.Event()
        batches: list[DraftVerification] = []
        revisions: list[int] = []
        errors: list[Exception] = []
        plan_calls = 0

        class CommitObserver:
            def __init__(self, connection) -> None:
                self.connection = connection

            def __getattr__(self, name):
                return getattr(self.connection, name)

            def commit(self):
                result = self.connection.commit()
                writer_committed.set()
                return result

        def blocked_plan(connection, *, partition, operation):
            nonlocal plan_calls
            plan_calls += 1
            plan = original_plan(
                connection,
                partition=partition,
                operation=operation,
            )
            if plan_calls == 2:
                enumerated.set()
                if not allow_plan_return.wait(timeout=5):
                    raise AssertionError("locked plan release timed out")
            return plan

        def blocked_verify_row(connection, row, *, verified_by, now_us):
            batch_writing.set()
            if not allow_batch_finish.wait(timeout=5):
                raise AssertionError("batch completion release timed out")
            return original_verify_row(
                connection,
                row,
                verified_by=verified_by,
                now_us=now_us,
            )

        def observed_writer_connect():
            connection = original_writer_connect()

            def trace(statement: str) -> None:
                if statement.strip().upper() == "BEGIN IMMEDIATE":
                    writer_attempted.set()

            connection.set_trace_callback(trace)
            return CommitObserver(connection)

        def run_batch() -> None:
            try:
                batches.append(
                    self.system.verify_drafts(
                        "tenant-a", "echo", verified_by="batch-verifier"
                    )
                )
            except Exception as exc:  # thread handoff
                errors.append(exc)
            finally:
                batch_finished.set()

        def run_writer() -> None:
            try:
                revisions.append(
                    writer.revise_operation(
                        "tenant-a",
                        "echo",
                        policy=policy,
                        revised_by="owner",
                    )
                )
            except Exception as exc:  # thread handoff
                errors.append(exc)
            finally:
                writer_finished.set()

        verifier = threading.Thread(target=run_batch)
        revision_writer = threading.Thread(target=run_writer)
        writer_started = False
        with (
            mock.patch.object(
                self.system,
                "_draft_verification_plan",
                side_effect=blocked_plan,
            ),
            mock.patch.object(
                self.system,
                "_verify_row",
                side_effect=blocked_verify_row,
            ),
            mock.patch.object(
                writer.store,
                "_connect",
                side_effect=observed_writer_connect,
            ),
        ):
            verifier.start()
            try:
                self.assertTrue(enumerated.wait(timeout=2))
                revision_writer.start()
                writer_started = True
                self.assertTrue(writer_attempted.wait(timeout=2))
                self.assertFalse(writer_committed.wait(timeout=0.1))
                allow_plan_return.set()
                self.assertTrue(batch_writing.wait(timeout=2))
                self.assertFalse(batch_finished.is_set())
                self.assertFalse(writer_committed.is_set())
                inspection = sqlite3.connect(self.database)
                try:
                    current_revision = int(
                        inspection.execute(
                            """
                            SELECT revision FROM operations
                            WHERE partition = 'tenant-a' AND name = 'echo'
                            """
                        ).fetchone()[0]
                    )
                finally:
                    inspection.close()
                self.assertEqual(current_revision, 1)
            finally:
                allow_plan_return.set()
                allow_batch_finish.set()
                verifier.join(timeout=5)
                if writer_started:
                    revision_writer.join(timeout=5)

        self.assertFalse(verifier.is_alive())
        self.assertFalse(revision_writer.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(plan_calls, 2)
        self.assertTrue(batch_finished.is_set())
        self.assertTrue(writer_finished.is_set())
        self.assertTrue(writer_committed.is_set())
        self.assertEqual(revisions, [2])
        self.assertEqual(len(batches), 1)
        self.assertTrue(batches[0].passed)
        self.assertEqual(batches[0].operation_revision, 1)
        self.assertEqual(
            tuple(entry.artifact_id for entry in batches[0].entries),
            expected_ids,
        )
        self.assertTrue(all(entry.report.passed for entry in batches[0].entries))

    def test_verify_drafts_enumerates_page_tail_beyond_one_thousand(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        example_rows = []
        for index in range(1_001):
            input_json = canonicalize({"page": index})
            output_json = canonicalize({"echo": {"page": index}})
            for witness, reviewer in (("a", "alice"), ("b", "bob")):
                example_id = f"ex_page_{index:04d}_{witness}"
                confirmed_at_us = self.clock.now_us + (witness == "b")
                receipt = canonicalize(
                    {
                        "confirmed_at_us": confirmed_at_us,
                        "example_id": example_id,
                        "format": "cement-confirmation-v1",
                        "input": input_json.value,
                        "note": "page-tail fixture",
                        "operation": "echo",
                        "operation_revision": 1,
                        "output": output_json.value,
                        "partition": "tenant-a",
                        "resolution": "accepted",
                        "reviewer": reviewer,
                    }
                )
                example_rows.append(
                    (
                        example_id,
                        "tenant-a",
                        "echo",
                        1,
                        input_json.text,
                        input_json.digest,
                        output_json.text,
                        output_json.digest,
                        reviewer,
                        "accepted",
                        receipt.text,
                        receipt.digest,
                        confirmed_at_us,
                    )
                )
        with self.system.store.transaction(write=True) as connection:
            connection.executemany(
                """
                INSERT INTO examples(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, reviewer, origin, receipt_json,
                    receipt_hash, confirmed_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                example_rows,
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 1_001)
        self.assertEqual(compiled.existing, ())
        self.assertEqual(compiled.blocked, ())
        with self.system.store.transaction(write=False) as connection:
            expected = tuple(
                (
                    str(row["id"]),
                    str(row["input_hash"]),
                    str(row["scope_hash"]),
                )
                for row in connection.execute(
                    """
                    SELECT id, input_hash, scope_hash FROM artifacts
                    WHERE partition = 'tenant-a' AND operation = 'echo'
                      AND operation_revision = 1 AND status = 'draft'
                    ORDER BY input_hash, sequence, id
                    """
                )
            )
        self.assertEqual(len(expected), 1_001)
        sentinel = expected[-1][:2]

        def selection_only(connection, row, *, verified_by, now_us):
            return (
                VerificationReport(
                    id=f"report_selection_{row['sequence']}",
                    artifact_id=str(row["id"]),
                    scope_hash=str(row["scope_hash"]),
                    passed=True,
                    tests=1,
                    failures=(),
                    created_at_us=now_us,
                ),
                "0" * 64,
            )

        with mock.patch.object(
            self.system,
            "_verify_row",
            side_effect=selection_only,
        ) as selected:
            result = self.system.verify_drafts(
                "tenant-a", "echo", verified_by="page-tail-verifier"
            )
        actual = tuple(
            (entry.artifact_id, entry.input_hash) for entry in result.entries
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.operation_revision, 1)
        self.assertEqual(result.skipped, ())
        self.assertEqual(
            actual,
            tuple((artifact_id, input_hash) for artifact_id, input_hash, _ in expected),
        )
        self.assertEqual(actual[-1], sentinel)
        self.assertEqual(selected.call_count, 1_001)

    def test_verify_drafts_selects_current_middle_build_and_reports_skipped(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        original_ids = self._compile_three_drafts("batch-middle")
        with self.system.store.transaction(write=False) as connection:
            original_rows = connection.execute(
                """
                SELECT id, input_hash, input_json FROM artifacts
                WHERE id IN (?, ?, ?) ORDER BY input_hash, sequence, id
                """,
                original_ids,
            ).fetchall()
        middle = original_rows[1]
        middle_input = json.loads(str(middle["input_json"]))
        self._confirm_scope(
            "tenant-a",
            "echo",
            middle_input,
            "batch-middle-extra",
            reviewer="alice",
        )
        newer = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(newer.created), 1)
        newer_id = newer.created[0]
        authority = mock.Mock(return_value=True)
        self.system._authority = authority

        result = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        selected = {entry.artifact_id for entry in result.entries}
        expected_selected = (set(original_ids) - {str(middle["id"])}) | {newer_id}
        self.assertTrue(result.passed)
        self.assertEqual(selected, expected_selected)
        self.assertEqual(
            result.skipped,
            (
                {
                    "artifact_id": str(middle["id"]),
                    "input_hash": str(middle["input_hash"]),
                    "reason": "superseded-build",
                },
            ),
        )
        self.assertEqual(
            {call.args[3] for call in authority.call_args_list},
            expected_selected,
        )
        self.assertNotIn(str(middle["id"]), {call.args[3] for call in authority.call_args_list})
        with self.system.store.transaction(write=False) as connection:
            statuses = dict(
                connection.execute(
                    "SELECT id, status FROM artifacts WHERE id IN (?, ?)",
                    (middle["id"], newer_id),
                ).fetchall()
            )
        self.assertEqual(statuses[str(middle["id"])], "draft")
        self.assertEqual(statuses[newer_id], "verified")

    def test_verify_drafts_requalifies_older_build_after_revocation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "requalify-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "requalify-b", reviewer="bob"
        )
        older = self.system.compile("tenant-a", "echo").created[0]
        pending = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id="requalify-extra"
        )
        self.assertIsInstance(pending, ReviewRequired)
        assert isinstance(pending, ReviewRequired)
        resolved = self.system.review(
            "tenant-a",
            pending.proposal_id,
            reviewer="alice",
            decision="accept",
        )
        self.assertIsInstance(resolved, Resolved)
        assert isinstance(resolved, Resolved)
        added = resolved.example_id
        self.assertIsNotNone(added)
        newer = self.system.compile("tenant-a", "echo").created[0]
        self.assertEqual(
            self.system.revoke_example(
                "tenant-a",
                str(added),
                revoked_by="auditor",
                reason="withdraw extra evidence",
            ),
            (newer,),
        )

        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual([entry.artifact_id for entry in result.entries], [older])
        self.assertEqual(result.skipped, ())
        self.assertEqual(self.system.artifact("tenant-a", newer)["status"], "suspended")

    def test_verify_drafts_requires_exact_canonical_input_projection(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "input-projection-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "input-projection-b", reviewer="bob"
        )
        artifact_id = self.system.compile("tenant-a", "echo").created[0]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                "UPDATE artifacts SET input_json = ? WHERE id = ?",
                (canonicalize({"x": "forged"}).text, artifact_id),
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.entries, ())
        self.assertEqual(
            result.skipped,
            (
                {
                    "artifact_id": artifact_id,
                    "input_hash": canonicalize({"x": 1}).digest,
                    "reason": "superseded-build",
                },
            ),
        )


    def test_verify_drafts_eligibility_is_exactly_scoped_to_current_drafts(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "echo", policy=policy)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "scope-target-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "scope-target-b", reviewer="bob"
        )
        target = self.system.compile("tenant-a", "echo").created[0]

        self.system.register_operation("tenant-a", "other", policy=policy)
        self._confirm_scope(
            "tenant-a", "other", {"x": 1}, "scope-other-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "other", {"x": 1}, "scope-other-b", reviewer="bob"
        )
        other_operation = self.system.compile("tenant-a", "other").created[0]

        self.system.register_operation("tenant-b", "echo", policy=policy)
        self._confirm_scope(
            "tenant-b", "echo", {"x": 1}, "scope-partition-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-b", "echo", {"x": 1}, "scope-partition-b", reviewer="bob"
        )
        other_partition = self.system.compile("tenant-b", "echo").created[0]

        with self.system.store.transaction(write=True) as connection:
            for artifact_id, revision, status, reason in (
                ("art_future_revision", 2, "draft", None),
                ("art_suspended_decoy", 1, "suspended", "decoy"),
            ):
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, partition, operation, operation_revision, input_json, input_hash,
                        output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                        build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                        support, reviewer_count, span_seconds, created_at_us,
                        verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                        status_reason
                    )
                    SELECT ?, partition, operation, ?, input_json, input_hash,
                           output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                           build_hash, policy_json, policy_hash, evidence_snapshot_hash, ?,
                           support, reviewer_count, span_seconds, created_at_us,
                           verified_report_id, promoted_by, promoted_at_us, promotion_hash, ?
                    FROM artifacts WHERE id = ?
                    """,
                    (artifact_id, revision, status, reason, target),
                )

        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual([entry.artifact_id for entry in result.entries], [target])
        self.assertEqual(result.skipped, ())
        with self.system.store.transaction(write=False) as connection:
            statuses = dict(
                connection.execute(
                    """
                    SELECT id, status FROM artifacts
                    WHERE id IN (?, ?, ?, ?)
                    """,
                    (
                        other_operation,
                        other_partition,
                        "art_future_revision",
                        "art_suspended_decoy",
                    ),
                ).fetchall()
            )
        self.assertEqual(
            statuses,
            {
                other_operation: "draft",
                other_partition: "draft",
                "art_future_revision": "draft",
                "art_suspended_decoy": "suspended",
            },
        )

    def test_verify_drafts_excludes_prior_revision_draft(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "echo", policy=policy)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "prior-revision-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "prior-revision-b", reviewer="bob"
        )
        prior = self.system.compile("tenant-a", "echo").created[0]

        revision = self.system.revise_operation(
            "tenant-a", "echo", policy=policy, revised_by="owner"
        )
        self.assertEqual(revision, 2)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "current-revision-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "current-revision-b", reviewer="bob"
        )
        current = self.system.compile("tenant-a", "echo").created[0]
        with self.system.store.transaction(write=True) as connection:
            connection.execute("DROP TRIGGER artifacts_status_lifecycle")
            connection.execute(
                """
                UPDATE artifacts SET status = 'draft', status_reason = NULL
                WHERE id = ?
                """,
                (prior,),
            )

        authority = mock.Mock(return_value=True)
        self.system._authority = authority
        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.operation_revision, 2)
        self.assertEqual(
            tuple(entry.artifact_id for entry in result.entries),
            (current,),
        )
        self.assertEqual(result.skipped, ())
        self.assertEqual(
            [call.args[3] for call in authority.call_args_list],
            [current],
        )
        with self.system.store.transaction(write=False) as connection:
            prior_diagnostics = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM test_reports WHERE artifact_id = ?),
                    (SELECT COUNT(*) FROM events WHERE subject_id = ?
                        AND kind IN ('artifact.verified', 'artifact.verification_failed'))
                """,
                (prior, prior),
            ).fetchone()
            prior_status = connection.execute(
                "SELECT status FROM artifacts WHERE id = ?",
                (prior,),
            ).fetchone()
        self.assertIsNotNone(prior_diagnostics)
        self.assertEqual(tuple(prior_diagnostics), (0, 0))
        self.assertIsNotNone(prior_status)
        self.assertEqual(prior_status["status"], "draft")

    def test_verify_drafts_excludes_each_non_draft_status(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        promoted, _, _ = self._promote_function_entry(
            {"x": 1}, "non-draft-status"
        )
        status_ids = {
            "promoted": promoted,
            "verified": "art_non_draft_verified",
            "building": "art_non_draft_building",
            "retired": "art_non_draft_retired",
        }
        with self.system.store.transaction(write=True) as connection:
            for status in ("verified", "building", "retired"):
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, partition, operation, operation_revision,
                        input_json, input_hash, output_json, output_hash,
                        artifact_json, artifact_hash, scope_hash, build_hash,
                        policy_json, policy_hash, evidence_snapshot_hash,
                        status, support, reviewer_count, span_seconds,
                        created_at_us, verified_report_id, promoted_by,
                        promoted_at_us, promotion_hash, status_reason
                    )
                    SELECT ?, partition, operation, operation_revision,
                           input_json, input_hash, output_json, output_hash,
                           artifact_json, artifact_hash, scope_hash, build_hash,
                           policy_json, policy_hash, evidence_snapshot_hash,
                           ?, support, reviewer_count, span_seconds,
                           created_at_us, NULL, NULL, NULL, NULL, ?
                    FROM artifacts WHERE id = ?
                    """,
                    (
                        status_ids[status],
                        status,
                        f"controlled {status} fixture",
                        promoted,
                    ),
                )

        authority = mock.Mock(return_value=True)
        self.system._authority = authority
        before = self._database_dump()
        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.entries, ())
        self.assertEqual(result.skipped, ())
        self.assertEqual(authority.call_args_list, [])
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_orders_entries_and_authority_by_input_hash(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        hash_value_pairs = sorted(
            (canonicalize({"x": value}).digest, {"x": value})
            for value in (1, 2, 3)
        )
        created_by_hash: dict[str, str] = {}
        for index, (input_hash, value) in enumerate(
            reversed(hash_value_pairs),
            start=1,
        ):
            self._confirm_scope(
                "tenant-a",
                "echo",
                value,
                f"batch-order-{index}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                "tenant-a",
                "echo",
                value,
                f"batch-order-{index}-b",
                reviewer="bob",
            )
            build = self.system.compile("tenant-a", "echo")
            self.assertEqual(len(build.created), 1)
            created_by_hash[input_hash] = build.created[0]

        expected_hashes = tuple(input_hash for input_hash, _ in hash_value_pairs)
        expected_ids = tuple(created_by_hash[input_hash] for input_hash in expected_hashes)
        with self.system.store.transaction(write=False) as connection:
            sequence_hashes = tuple(
                str(row["input_hash"])
                for row in connection.execute(
                    """
                    SELECT input_hash FROM artifacts WHERE id IN (?, ?, ?)
                    ORDER BY sequence
                    """,
                    expected_ids,
                )
            )
        self.assertEqual(sequence_hashes, tuple(reversed(expected_hashes)))

        original_connect = self.system.store._connect

        def reverse_unordered_connect():
            connection = original_connect()
            connection.execute("PRAGMA reverse_unordered_selects = ON")
            return connection

        authority = mock.Mock(return_value=True)
        self.system._authority = authority
        with mock.patch.object(
            self.system.store,
            "_connect",
            side_effect=reverse_unordered_connect,
        ):
            result = self.system.verify_drafts(
                "tenant-a", "echo", verified_by="batch-verifier"
            )
        self.assertTrue(result.passed)
        self.assertEqual(
            tuple(entry.input_hash for entry in result.entries),
            expected_hashes,
        )
        self.assertEqual(
            tuple(entry.artifact_id for entry in result.entries),
            expected_ids,
        )
        self.assertEqual(
            tuple(call.args[3] for call in authority.call_args_list),
            expected_ids,
        )

    def test_verify_drafts_ignores_prior_revision_canonical_collisions(self) -> None:
        policy = CompilePolicy(2, 1, 0)
        self.system.register_operation("tenant-a", "echo", policy=policy)
        self._confirm_scope(
            "tenant-a", "echo", {"x": "stale"}, "stale-input-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": "stale"}, "stale-input-b", reviewer="bob"
        )

        revision = self.system.revise_operation(
            "tenant-a", "echo", policy=policy, revised_by="owner"
        )
        self.assertEqual(revision, 2)
        current_input = {"x": "current"}
        self._confirm_scope(
            "tenant-a", "echo", current_input, "current-input-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", current_input, "current-input-b", reviewer="bob"
        )
        current = self.system.compile("tenant-a", "echo").created[0]
        current_hash = canonicalize(current_input).digest
        with self.system.store.transaction(write=True) as connection:
            connection.execute("DROP TRIGGER examples_no_update")
            stale = connection.execute(
                """
                SELECT id FROM examples
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND operation_revision = 1
                ORDER BY id LIMIT 1
                """
            ).fetchone()
            if stale is None:
                raise AssertionError("prior-revision example disappeared")
            connection.execute(
                "UPDATE examples SET input_hash = ? WHERE id = ?",
                (current_hash, stale["id"]),
            )

        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual(
            tuple(entry.artifact_id for entry in result.entries),
            (current,),
        )
        self.assertEqual(result.skipped, ())

    def test_verify_drafts_skips_policy_blocked_current_projection(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "blocked-current-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "blocked-current-b", reviewer="bob"
        )
        artifact_id = self.system.compile("tenant-a", "echo").created[0]
        with self.system.store.transaction(write=False) as connection:
            example = connection.execute(
                """
                SELECT id FROM examples
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND operation_revision = 1
                ORDER BY id LIMIT 1
                """
            ).fetchone()
        if example is None:
            raise AssertionError("blocking evidence fixture disappeared")
        self.system.revoke_example(
            "tenant-a",
            str(example["id"]),
            revoked_by="auditor",
            reason="force current projection below policy",
        )
        with self.system.store.transaction(write=True) as connection:
            connection.execute("DROP TRIGGER artifacts_status_lifecycle")
            connection.execute(
                """
                UPDATE artifacts SET status = 'draft', status_reason = NULL
                WHERE id = ?
                """,
                (artifact_id,),
            )

        authority = mock.Mock(return_value=True)
        self.system._authority = authority
        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.entries, ())
        self.assertEqual(
            result.skipped,
            (
                {
                    "artifact_id": artifact_id,
                    "input_hash": canonicalize({"x": 1}).digest,
                    "reason": "superseded-build",
                },
            ),
        )
        self.assertEqual(authority.call_args_list, [])

    def test_verify_drafts_duplicate_eligible_rows_abort_full_ledger(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "duplicate-batch-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "duplicate-batch-b", reviewer="bob"
        )
        current = self.system.compile("tenant-a", "echo").created[0]
        with self.system.store.transaction(write=True) as connection:
            connection.execute(
                """
                INSERT INTO artifacts(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                    status_reason
                )
                SELECT 'art_duplicate_current', partition, operation, operation_revision,
                       input_json, input_hash, output_json, output_hash, artifact_json,
                       artifact_hash, scope_hash, build_hash, policy_json, policy_hash,
                       evidence_snapshot_hash, status, support, reviewer_count, span_seconds,
                       created_at_us, verified_report_id, promoted_by, promoted_at_us,
                       promotion_hash, status_reason
                FROM artifacts WHERE id = ?
                """,
                (current,),
            )
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "multiple drafts claim the current build",
        ):
            self.system.verify_drafts(
                "tenant-a", "echo", verified_by="batch-verifier"
            )
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_missing_canonical_input_aborts_full_ledger(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "missing-input-a", reviewer="alice"
        )
        self._confirm_scope(
            "tenant-a", "echo", {"x": 1}, "missing-input-b", reviewer="bob"
        )
        current = self.system.compile("tenant-a", "echo").created[0]
        with self.system.store.transaction(write=True) as connection:
            connection.execute(
                """
                INSERT INTO artifacts(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                    status_reason
                )
                SELECT 'art_missing_input', partition, operation, operation_revision,
                       input_json, ?, output_json, output_hash, artifact_json,
                       artifact_hash, scope_hash, build_hash, policy_json, policy_hash,
                       evidence_snapshot_hash, status, support, reviewer_count, span_seconds,
                       created_at_us, verified_report_id, promoted_by, promoted_at_us,
                       promotion_hash, status_reason
                FROM artifacts WHERE id = ?
                """,
                ("0" * 64, current),
            )
        before = self._database_dump()
        with self.assertRaisesRegex(IntegrityError, "has no canonical input"):
            self.system.verify_drafts(
                "tenant-a", "echo", verified_by="batch-verifier"
            )
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_duplicate_canonical_inputs_abort_full_ledger(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("canonical-collision")
        connection = sqlite3.connect(self.database)
        try:
            rows = connection.execute(
                """
                SELECT input_hash FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                ORDER BY input_hash LIMIT 2
                """
            ).fetchall()
            first_hash, second_hash = str(rows[0][0]), str(rows[1][0])
            connection.execute("DROP TRIGGER examples_no_update")
            connection.execute(
                """
                UPDATE examples SET input_hash = ?
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND input_hash = ?
                """,
                (first_hash, second_hash),
            )
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "one input digest maps to multiple canonical inputs",
        ):
            self.system.verify_drafts(
                "tenant-a", "echo", verified_by="batch-verifier"
            )
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_authority_denial_precedes_write_transaction(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("batch-authority")
        with self.system.store.transaction(write=False) as connection:
            selected_ids = tuple(
                str(row["id"])
                for row in connection.execute(
                    """
                    SELECT id FROM artifacts
                    WHERE partition = 'tenant-a' AND operation = 'echo'
                      AND status = 'draft'
                    ORDER BY input_hash, sequence, id
                    """
                )
            )
        denied = selected_ids[-1]
        calls: list[tuple[str, str, str, str]] = []

        def authority(partition, actor, action, subject):
            calls.append((partition, actor, action, subject))
            return subject != denied

        self.system._authority = authority
        before = self._database_dump()
        with mock.patch.object(
            self.system.store,
            "transaction",
            wraps=self.system.store.transaction,
        ) as transaction:
            with self.assertRaisesRegex(StateError, "not authorized"):
                self.system.verify_drafts(
                    "tenant-a", "echo", verified_by="blocked-verifier"
                )
        self.assertEqual(
            calls,
            [
                ("tenant-a", "blocked-verifier", "artifact.verify", artifact_id)
                for artifact_id in selected_ids
            ],
        )
        self.assertEqual(transaction.call_args_list, [mock.call(write=False)])
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_contains_middle_integrity_failure_per_row(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        created = self._compile_three_drafts("batch-local-failure")
        with self.system.store.transaction(write=False) as connection:
            rows = connection.execute(
                """
                SELECT id FROM artifacts WHERE id IN (?, ?, ?)
                ORDER BY input_hash, sequence, id
                """,
                created,
            ).fetchall()
        target = str(rows[1]["id"])
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                "UPDATE artifacts SET artifact_json = '{}' WHERE id = ?",
                (target,),
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertFalse(result.passed)
        self.assertEqual(len(result.entries), 3)
        self.assertEqual(
            [entry.report.passed for entry in result.entries],
            [True, False, True],
        )
        self.assertIsNone(result.entries[1].entry_seal)
        self.assertIsNotNone(result.entries[0].entry_seal)
        self.assertIsNotNone(result.entries[2].entry_seal)
        self.assertIn("integrity", result.entries[1].report.failures[0])
        with self.system.store.transaction(write=False) as connection:
            statuses = {
                str(row["id"]): str(row["status"])
                for row in connection.execute(
                    "SELECT id, status FROM artifacts WHERE id IN (?, ?, ?)",
                    created,
                )
            }
            report_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM test_reports WHERE artifact_id IN (?, ?, ?)",
                    created,
                ).fetchone()[0]
            )
            event_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE subject_id IN (?, ?, ?)
                      AND kind IN ('artifact.verified', 'artifact.verification_failed')
                    """,
                    created,
                ).fetchone()[0]
            )
        self.assertEqual(statuses[target], "draft")
        self.assertEqual(
            {status for artifact_id, status in statuses.items() if artifact_id != target},
            {"verified"},
        )
        self.assertEqual(report_count, 3)
        self.assertEqual(event_count, 3)

    def test_verify_drafts_aggregate_includes_last_failed_row(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        created = self._compile_three_drafts("batch-last-failure")
        with self.system.store.transaction(write=False) as connection:
            ordered_ids = tuple(
                str(row["id"])
                for row in connection.execute(
                    """
                    SELECT id FROM artifacts WHERE id IN (?, ?, ?)
                    ORDER BY input_hash, sequence, id
                    """,
                    created,
                )
            )
        target = ordered_ids[-1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                "UPDATE artifacts SET artifact_json = '{}' WHERE id = ?",
                (target,),
            )
            connection.commit()
        finally:
            connection.close()

        result = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="batch-verifier"
        )
        self.assertFalse(result.passed)
        self.assertEqual(
            tuple(entry.artifact_id for entry in result.entries),
            ordered_ids,
        )
        self.assertEqual(
            tuple(entry.report.passed for entry in result.entries),
            (True, True, False),
        )
        self.assertEqual(
            tuple(entry.entry_seal is not None for entry in result.entries),
            (True, True, False),
        )
        self.assertEqual(
            tuple(entry.report.tests for entry in result.entries),
            (8, 8, 1),
        )
        with self.system.store.transaction(write=False) as connection:
            statuses = dict(
                connection.execute(
                    "SELECT id, status FROM artifacts WHERE id IN (?, ?, ?)",
                    ordered_ids,
                ).fetchall()
            )
            report_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM test_reports
                    WHERE artifact_id IN (?, ?, ?)
                    """,
                    ordered_ids,
                ).fetchone()[0]
            )
            events = tuple(
                (str(row["subject_id"]), str(row["kind"]))
                for row in connection.execute(
                    """
                    SELECT subject_id, kind FROM events
                    WHERE subject_id IN (?, ?, ?)
                      AND kind IN ('artifact.verified', 'artifact.verification_failed')
                    ORDER BY sequence
                    """,
                    ordered_ids,
                )
            )
        self.assertEqual(
            statuses,
            {
                ordered_ids[0]: "verified",
                ordered_ids[1]: "verified",
                ordered_ids[2]: "draft",
            },
        )
        self.assertEqual(report_count, 3)
        self.assertEqual(
            events,
            (
                (ordered_ids[0], "artifact.verified"),
                (ordered_ids[1], "artifact.verified"),
                (ordered_ids[2], "artifact.verification_failed"),
            ),
        )


    def test_verify_drafts_rolls_back_flushed_children_per_row(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        created = self._compile_three_drafts("batch-flush-rollback")
        with self.system.store.transaction(write=False) as connection:
            ordered_ids = tuple(
                str(row["id"])
                for row in connection.execute(
                    """
                    SELECT id FROM artifacts WHERE id IN (?, ?, ?)
                    ORDER BY input_hash, sequence, id
                    """,
                    created,
                )
            )
        target = ordered_ids[1]
        original = self.system._run_verification

        def fail_after_flush(connection, row, *, record_test=None):
            if str(row["id"]) == target:
                if record_test is None:
                    raise AssertionError("batch row recorder was not provided")
                for index in range(513):
                    record_test(
                        f"synthetic:{index:04d}",
                        None,
                        True,
                        "pre-failure flushed child",
                    )
                raise IntegrityError("injected integrity failure after child flush")
            return original(connection, row, record_test=record_test)

        with mock.patch.object(
            self.system,
            "_run_verification",
            side_effect=fail_after_flush,
        ):
            result = self.system.verify_drafts(
                "tenant-a", "echo", verified_by="batch-verifier"
            )

        self.assertFalse(result.passed)
        self.assertEqual(
            tuple(entry.artifact_id for entry in result.entries),
            ordered_ids,
        )
        self.assertEqual(
            tuple(entry.report.passed for entry in result.entries),
            (True, False, True),
        )
        self.assertEqual(
            tuple(entry.report.tests for entry in result.entries),
            (8, 1, 8),
        )
        self.assertEqual(result.entries[1].report.failures, (
            "artifact integrity failure: "
            "injected integrity failure after child flush",
        ))
        with self.system.store.transaction(write=False) as connection:
            children = {
                entry.artifact_id: tuple(
                    (
                        str(row["test_key"]),
                        int(row["passed"]),
                    )
                    for row in connection.execute(
                        """
                        SELECT test_key, passed FROM artifact_tests
                        WHERE report_id = ? ORDER BY test_key
                        """,
                        (entry.report.id,),
                    )
                )
                for entry in result.entries
            }
            events = tuple(
                (str(row["subject_id"]), str(row["kind"]))
                for row in connection.execute(
                    """
                    SELECT subject_id, kind FROM events
                    WHERE subject_id IN (?, ?, ?)
                      AND kind IN ('artifact.verified', 'artifact.verification_failed')
                    ORDER BY sequence
                    """,
                    ordered_ids,
                )
            )
        self.assertEqual(len(children[ordered_ids[0]]), 8)
        self.assertEqual(children[target], (("artifact-integrity", 0),))
        self.assertEqual(len(children[ordered_ids[2]]), 8)
        self.assertEqual(
            events,
            (
                (ordered_ids[0], "artifact.verified"),
                (target, "artifact.verification_failed"),
                (ordered_ids[2], "artifact.verified"),
            ),
        )

    def test_verify_drafts_test_count_mismatch_aborts_full_ledger(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("batch-test-count")
        before = self._database_dump()
        original = self.system._test_snapshot

        for delta in (1, -1):
            with self.subTest(delta=delta):
                calls = 0

                def shifted_snapshot(connection, report_id):
                    nonlocal calls
                    calls += 1
                    count, digest = original(connection, report_id)
                    if calls == 2:
                        return count + delta, digest
                    return count, digest

                with mock.patch.object(
                    self.system,
                    "_test_snapshot",
                    side_effect=shifted_snapshot,
                ):
                    with self.assertRaisesRegex(
                        IntegrityError,
                        "verification test count changed while recording",
                    ):
                        self.system.verify_drafts(
                            "tenant-a",
                            "echo",
                            verified_by="batch-verifier",
                        )
                self.assertEqual(calls, 2)
                self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_missing_sealed_report_is_domain_error(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("batch-missing-sealed-report")
        before = self._database_dump()
        seal_query = (
            "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?"
        )

        class MissingSealCursor:
            @staticmethod
            def fetchone():
                return None

        class MissingSealConnection:
            def __init__(self, connection):
                self.connection = connection

            def execute(self, sql, parameters=()):
                cursor = self.connection.execute(sql, parameters)
                if " ".join(sql.split()) == seal_query:
                    return MissingSealCursor()
                return cursor

            def __getattr__(self, name):
                return getattr(self.connection, name)

        original_transaction = self.system.store.transaction

        @contextmanager
        def missing_seal_transaction(*, write=False):
            with original_transaction(write=write) as connection:
                if write:
                    yield MissingSealConnection(connection)
                else:
                    yield connection

        with mock.patch.object(
            self.system.store,
            "transaction",
            side_effect=missing_seal_transaction,
        ):
            with self.assertRaisesRegex(
                IntegrityError,
                "verification report disappeared before sealing",
            ):
                self.system.verify_drafts(
                    "tenant-a", "echo", verified_by="batch-verifier"
                )
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_unexpected_middle_failure_rolls_back_full_ledger(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("batch-atomic")
        before = self._database_dump()
        original = self.system._run_verification
        calls = 0

        def fail_middle(connection, row, *, record_test=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise StateError("injected middle batch failure")
            return original(connection, row, record_test=record_test)

        with mock.patch.object(
            self.system,
            "_run_verification",
            side_effect=fail_middle,
        ):
            with self.assertRaisesRegex(StateError, "injected middle batch failure"):
                self.system.verify_drafts(
                    "tenant-a", "echo", verified_by="batch-verifier"
                )
        self.assertEqual(calls, 2)
        self.assertEqual(self._database_dump(), before)

    def test_verify_drafts_rechecks_eligibility_after_authorization(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("batch-recheck")
        before = self._database_dump()
        original = self.system._draft_verification_plan
        calls = 0

        def changed_plan(connection, *, partition, operation):
            nonlocal calls
            calls += 1
            revision, rows, skipped = original(
                connection,
                partition=partition,
                operation=operation,
            )
            if calls == 2:
                return revision, rows[:-1], skipped
            return revision, rows, skipped

        with mock.patch.object(
            self.system,
            "_draft_verification_plan",
            side_effect=changed_plan,
        ):
            with self.assertRaisesRegex(
                StateError,
                "eligibility changed during authorization",
            ):
                self.system.verify_drafts(
                    "tenant-a", "echo", verified_by="batch-verifier"
                )
        self.assertEqual(calls, 2)
        self.assertEqual(self._database_dump(), before)

    def test_function_entry_seal_binds_each_of_fourteen_fields_independently(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("seal-fields")
        batch = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="seal-verifier"
        )
        self.assertTrue(batch.passed)
        with self.system.store.transaction(write=False) as connection:
            operation = connection.execute(
                """
                SELECT * FROM operations
                WHERE partition = 'tenant-a' AND name = 'echo'
                """
            ).fetchone()
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'verified'
                ORDER BY input_hash, sequence, id
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            reports = [
                connection.execute(
                    "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                    (row["verified_report_id"], row["id"]),
                ).fetchone()
                for row in rows
            ]
        if operation is None or any(report is None for report in reports):
            raise AssertionError("seal mutation fixture disappeared")
        sealed_reports = [report for report in reports if report is not None]
        entries = tuple(
            FunctionEntry(
                input=json.loads(str(row["input_json"])),
                output=json.loads(str(row["output_json"])),
                artifact_hash=str(row["artifact_hash"]),
                evidence_snapshot_hash=str(row["evidence_snapshot_hash"]),
                entry_seal=_function_entry_seal(row, report),
                report_details_hash=str(report["details_hash"]),
                report_test_set_hash=str(report["test_set_hash"]),
            )
            for row, report in zip(rows, sealed_reports, strict=True)
        )
        baseline_function = build_function(
            partition="tenant-a",
            operation="echo",
            operation_revision=int(operation["revision"]),
            policy_hash=str(operation["policy_hash"]),
            entries=entries,
        )
        target = rows[1]
        report = sealed_reports[1]
        baseline_seal = entries[1].entry_seal
        mutations = (
            ("artifact", "id", f"{target['id']}-changed"),
            ("artifact", "artifact_hash", "0" * 64),
            ("artifact", "build_hash", "1" * 64),
            ("artifact", "policy_hash", "2" * 64),
            ("artifact", "evidence_snapshot_hash", "3" * 64),
            ("artifact", "support", int(target["support"]) + 1),
            ("artifact", "reviewer_count", int(target["reviewer_count"]) + 1),
            ("artifact", "span_seconds", int(target["span_seconds"]) + 1),
            ("artifact", "scope_hash", "4" * 64),
            ("report", "id", f"{report['id']}-changed"),
            ("report", "details_hash", "5" * 64),
            ("report", "test_set_hash", "6" * 64),
            ("report", "test_count", int(report["test_count"]) + 1),
            ("report", "passed", 1 - int(report["passed"])),
        )
        self.assertEqual(len(mutations), 14)
        for owner, field, changed_value in mutations:
            artifact_changed = dict(target)
            report_changed = dict(report)
            changed = artifact_changed if owner == "artifact" else report_changed
            changed[field] = changed_value
            differences = [
                f"artifact.{key}"
                for key, value in artifact_changed.items()
                if value != target[key]
            ] + [
                f"report.{key}"
                for key, value in report_changed.items()
                if value != report[key]
            ]
            changed_seal = _function_entry_seal(
                artifact_changed,
                report_changed,
            )
            changed_entries = list(entries)
            changed_entries[1] = replace(entries[1], entry_seal=changed_seal)
            changed_function = build_function(
                partition="tenant-a",
                operation="echo",
                operation_revision=int(operation["revision"]),
                policy_hash=str(operation["policy_hash"]),
                entries=changed_entries,
            )
            with self.subTest(field=f"{owner}.{field}"):
                self.assertEqual(differences, [f"{owner}.{field}"])
                self.assertNotEqual(changed_seal, baseline_seal)
                self.assertNotEqual(
                    changed_function.function_hash,
                    baseline_function.function_hash,
                )


    def test_function_entry_seal_matches_independent_framing_oracle(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("seal-oracle")
        batch = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="seal-verifier"
        )
        self.assertTrue(batch.passed)
        with self.system.store.transaction(write=False) as connection:
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'verified'
                ORDER BY input_hash, sequence, id
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            target = rows[1]
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                (target["verified_report_id"], target["id"]),
            ).fetchone()
        if report is None:
            raise AssertionError("middle entry report disappeared")

        def framed_digest(label: str, values: tuple[str, ...]) -> str:
            digest = hashlib.sha256()
            for value in (label, *values):
                encoded = value.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
            return digest.hexdigest()

        ordered_fields = (
            str(target["id"]),
            str(target["artifact_hash"]),
            str(target["build_hash"]),
            str(target["policy_hash"]),
            str(target["evidence_snapshot_hash"]),
            str(target["support"]),
            str(target["reviewer_count"]),
            str(target["span_seconds"]),
            str(target["scope_hash"]),
            str(report["id"]),
            str(report["details_hash"]),
            str(report["test_set_hash"]),
            str(report["test_count"]),
            str(report["passed"]),
        )
        literal_label = "cement-function-entry-seal-v1"
        self.assertEqual(FUNCTION_ENTRY_SEAL_ABI, literal_label)
        expected = framed_digest(literal_label, ordered_fields)
        self.assertNotEqual(target["build_hash"], target["policy_hash"])
        self.assertEqual(batch.entries[1].artifact_id, target["id"])
        self.assertEqual(batch.entries[1].entry_seal, expected)

        left = ("ab", "c")
        right = ("a", "bc")
        self.assertEqual("".join(left), "".join(right))
        left_digest = framed_digest(FUNCTION_ENTRY_SEAL_ABI, left)
        right_digest = framed_digest(FUNCTION_ENTRY_SEAL_ABI, right)
        self.assertNotEqual(left_digest, right_digest)
        self.assertEqual(
            _digest_strings(FUNCTION_ENTRY_SEAL_ABI, left),
            left_digest,
        )
        self.assertEqual(
            _digest_strings(FUNCTION_ENTRY_SEAL_ABI, right),
            right_digest,
        )

    def test_entry_seal_timing_is_invariant_through_promotion_and_function_verify(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._compile_three_drafts("seal-timing")
        batch = self.system.verify_drafts(
            "tenant-a", "echo", verified_by="seal-verifier"
        )
        self.assertTrue(batch.passed)
        pre_batch = {
            entry.artifact_id: entry.entry_seal for entry in batch.entries
        }
        pre_recomputed: dict[str, str] = {}
        input_hash_by_id: dict[str, str] = {}
        with self.system.store.transaction(write=False) as connection:
            for row in connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'verified'
                ORDER BY input_hash, sequence, id
                """
            ):
                report = connection.execute(
                    "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                    (row["verified_report_id"], row["id"]),
                ).fetchone()
                if report is None:
                    raise AssertionError("bound report disappeared before promotion")
                artifact_id = str(row["id"])
                pre_recomputed[artifact_id] = _function_entry_seal(row, report)
                input_hash_by_id[artifact_id] = str(row["input_hash"])
        self.assertEqual(pre_batch, pre_recomputed)
        for entry in batch.entries:
            self.system.promote(
                "tenant-a",
                entry.artifact_id,
                scope_hash=entry.report.scope_hash,
                promoted_by="release-manager",
            )

        post_recomputed: dict[str, str] = {}
        with self.system.store.transaction(write=False) as connection:
            for row in connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND status = 'promoted'
                ORDER BY input_hash, sequence, id
                """
            ):
                report = connection.execute(
                    "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                    (row["verified_report_id"], row["id"]),
                ).fetchone()
                if report is None:
                    raise AssertionError("bound report disappeared after promotion")
                post_recomputed[str(row["id"])] = _function_entry_seal(row, report)
        self.assertEqual(post_recomputed, pre_recomputed)

        verified = self.system.verify_function("tenant-a", "echo")
        self.assertTrue(verified.passed)
        self.assertIsNotNone(verified.document)
        assert verified.document is not None
        raw_entries = verified.document.value["entries"]
        self.assertIsInstance(raw_entries, list)
        assert type(raw_entries) is list
        function_seals = {
            str(entry["input_hash"]): str(entry["entry_seal"])
            for entry in raw_entries
            if type(entry) is dict
        }
        self.assertEqual(
            function_seals,
            {
                input_hash_by_id[artifact_id]: seal
                for artifact_id, seal in pre_recomputed.items()
            },
        )


    def test_function_promotion_schema_v2_is_reference_only_and_immutable(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 2)
        self.register(confirmations=2, reviewers=1, span=0)
        _, promotion = self._promote_three_as_function("function-schema")

        def index_contract(
            connection: sqlite3.Connection,
            table: str,
        ) -> frozenset[tuple[int, str, int, tuple[str, ...]]]:
            return frozenset(
                (
                    int(index["unique"]),
                    str(index["origin"]),
                    int(index["partial"]),
                    tuple(
                        str(column["name"])
                        for column in connection.execute(
                            f"PRAGMA index_info({index['name']})"
                        )
                    ),
                )
                for index in connection.execute(f"PRAGMA index_list({table})")
            )

        with self.system.store.transaction(write=False) as connection:
            receipt_info = tuple(
                tuple(row)
                for row in connection.execute(
                    "PRAGMA table_info(function_receipts)"
                )
            )
            membership_info = tuple(
                tuple(row)
                for row in connection.execute(
                    "PRAGMA table_info(function_memberships)"
                )
            )
            receipt_columns = tuple(str(row[1]) for row in receipt_info)
            membership_columns = tuple(str(row[1]) for row in membership_info)
            membership_foreign_keys = tuple(
                tuple(row)
                for row in connection.execute(
                    "PRAGMA foreign_key_list(function_memberships)"
                )
            )
            receipt_indexes = index_contract(connection, "function_receipts")
            membership_indexes = index_contract(connection, "function_memberships")
            table_properties = {
                str(row["name"]): (
                    str(row["type"]),
                    int(row["ncol"]),
                    int(row["wr"]),
                    int(row["strict"]),
                )
                for row in connection.execute("PRAGMA table_list")
                if str(row["name"]).startswith("function_")
            }
            schema_rows = {
                (str(row["type"]), str(row["name"])): str(row["sql"])
                for row in connection.execute(
                    """
                    SELECT type, name, sql FROM sqlite_schema
                    WHERE name LIKE 'function_%' AND sql IS NOT NULL
                    """
                )
            }
            membership = connection.execute(
                """
                SELECT * FROM function_memberships
                WHERE receipt_id = ? ORDER BY ordinal LIMIT 1
                """,
                (promotion.receipt_id,),
            ).fetchone()
        self.assertEqual(
            receipt_columns,
            (
                "sequence",
                "id",
                "partition",
                "operation",
                "operation_revision",
                "policy_hash",
                "function_hash",
                "membership_hash",
                "member_count",
                "candidate_artifact_ids_hash",
                "candidate_count",
                "retired_artifact_ids_hash",
                "retired_count",
                "promoted_by",
                "promoted_at_us",
                "receipt_hash",
            ),
        )
        self.assertEqual(
            membership_columns,
            (
                "receipt_id",
                "ordinal",
                "function_hash",
                "artifact_id",
                "report_id",
                "input_hash",
                "entry_seal",
            ),
        )
        self.assertEqual(
            receipt_info,
            (
                (0, "sequence", "INTEGER", 0, None, 1),
                (1, "id", "TEXT", 1, None, 0),
                (2, "partition", "TEXT", 1, None, 0),
                (3, "operation", "TEXT", 1, None, 0),
                (4, "operation_revision", "INTEGER", 1, None, 0),
                (5, "policy_hash", "TEXT", 1, None, 0),
                (6, "function_hash", "TEXT", 1, None, 0),
                (7, "membership_hash", "TEXT", 1, None, 0),
                (8, "member_count", "INTEGER", 1, None, 0),
                (9, "candidate_artifact_ids_hash", "TEXT", 1, None, 0),
                (10, "candidate_count", "INTEGER", 1, None, 0),
                (11, "retired_artifact_ids_hash", "TEXT", 1, None, 0),
                (12, "retired_count", "INTEGER", 1, None, 0),
                (13, "promoted_by", "TEXT", 1, None, 0),
                (14, "promoted_at_us", "INTEGER", 1, None, 0),
                (15, "receipt_hash", "TEXT", 1, None, 0),
            ),
        )
        self.assertEqual(
            membership_info,
            (
                (0, "receipt_id", "TEXT", 1, None, 1),
                (1, "ordinal", "INTEGER", 1, None, 2),
                (2, "function_hash", "TEXT", 1, None, 0),
                (3, "artifact_id", "TEXT", 1, None, 0),
                (4, "report_id", "TEXT", 1, None, 0),
                (5, "input_hash", "TEXT", 1, None, 0),
                (6, "entry_seal", "TEXT", 1, None, 0),
            ),
        )
        self.assertEqual(
            membership_foreign_keys,
            (
                (
                    0,
                    0,
                    "function_receipts",
                    "receipt_id",
                    "id",
                    "NO ACTION",
                    "NO ACTION",
                    "NONE",
                ),
                (
                    0,
                    1,
                    "function_receipts",
                    "function_hash",
                    "function_hash",
                    "NO ACTION",
                    "NO ACTION",
                    "NONE",
                ),
                (
                    1,
                    0,
                    "test_reports",
                    "report_id",
                    "id",
                    "NO ACTION",
                    "NO ACTION",
                    "NONE",
                ),
                (
                    2,
                    0,
                    "artifacts",
                    "artifact_id",
                    "id",
                    "NO ACTION",
                    "NO ACTION",
                    "NONE",
                ),
            ),
        )
        self.assertEqual(
            receipt_indexes,
            frozenset(
                {
                    (0, "c", 0, ("function_hash", "sequence")),
                    (
                        0,
                        "c",
                        0,
                        ("partition", "operation", "operation_revision", "sequence"),
                    ),
                    (1, "u", 0, ("id",)),
                    (1, "u", 0, ("receipt_hash",)),
                    (1, "u", 0, ("id", "function_hash")),
                }
            ),
        )
        self.assertEqual(
            membership_indexes,
            frozenset(
                {
                    (0, "c", 0, ("artifact_id", "receipt_id")),
                    (1, "pk", 0, ("receipt_id", "ordinal")),
                    (1, "u", 0, ("receipt_id", "artifact_id")),
                    (1, "u", 0, ("receipt_id", "input_hash")),
                }
            ),
        )
        self.assertEqual(
            table_properties,
            {
                "function_memberships": ("table", 7, 0, 1),
                "function_receipts": ("table", 16, 0, 1),
            },
        )
        receipt_sql = schema_rows[("table", "function_receipts")]
        membership_sql = schema_rows[("table", "function_memberships")]
        for definition in (
            "operation_revision INTEGER NOT NULL CHECK (operation_revision >= 1)",
            "member_count INTEGER NOT NULL CHECK (member_count >= 0)",
            "candidate_count INTEGER NOT NULL CHECK (candidate_count >= 0)",
            "retired_count INTEGER NOT NULL CHECK (retired_count >= 0)",
            "receipt_hash TEXT NOT NULL UNIQUE",
        ):
            with self.subTest(receipt_definition=definition):
                self.assertIn(definition, receipt_sql)
        for definition in (
            "ordinal INTEGER NOT NULL CHECK (ordinal >= 0)",
            "artifact_id TEXT NOT NULL REFERENCES artifacts(id)",
            "report_id TEXT NOT NULL REFERENCES test_reports(id)",
            "PRIMARY KEY (receipt_id, ordinal)",
            "UNIQUE (receipt_id, artifact_id)",
            "UNIQUE (receipt_id, input_hash)",
        ):
            with self.subTest(membership_definition=definition):
                self.assertIn(definition, membership_sql)
        self.assertTrue(receipt_sql.endswith(") STRICT"))
        self.assertTrue(membership_sql.endswith(") STRICT"))
        self.assertIn(
            ("index", "function_receipts_scope"),
            schema_rows,
        )
        self.assertIn(
            ("index", "function_receipts_hash"),
            schema_rows,
        )
        self.assertIn("function_hash", schema_rows[("index", "function_receipts_hash")])
        self.assertNotIn(
            "UNIQUE",
            schema_rows[("index", "function_receipts_hash")].upper(),
        )
        self.assertIn(
            ("index", "function_memberships_artifact"),
            schema_rows,
        )
        seal_sql = schema_rows[("trigger", "function_memberships_sealed_insert")]
        self.assertIn(
            "WHEN EXISTS (SELECT 1 FROM function_receipts WHERE id = NEW.receipt_id)",
            seal_sql,
        )
        self.assertNotIn("COUNT", seal_sql.upper())
        self.assertIn(
            "DEFERRABLE INITIALLY DEFERRED",
            schema_rows[("table", "function_memberships")],
        )
        if membership is None:
            raise AssertionError("function membership fixture disappeared")

        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "memberships are immutable"):
                connection.execute(
                    """
                    UPDATE function_memberships SET entry_seal = entry_seal
                    WHERE receipt_id = ? AND ordinal = ?
                    """,
                    (promotion.receipt_id, membership["ordinal"]),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "memberships are immutable"):
                connection.execute(
                    """
                    DELETE FROM function_memberships
                    WHERE receipt_id = ? AND ordinal = ?
                    """,
                    (promotion.receipt_id, membership["ordinal"]),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "membership set is sealed"):
                connection.execute(
                    """
                    INSERT INTO function_memberships(
                        receipt_id, ordinal, function_hash, artifact_id, report_id,
                        input_hash, entry_seal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        promotion.receipt_id,
                        99,
                        membership["function_hash"],
                        membership["artifact_id"],
                        membership["report_id"],
                        membership["input_hash"],
                        membership["entry_seal"],
                    ),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "receipts are immutable"):
                connection.execute(
                    """
                    UPDATE function_receipts SET promoted_by = promoted_by
                    WHERE id = ?
                    """,
                    (promotion.receipt_id,),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "receipts are immutable"):
                connection.execute(
                    "DELETE FROM function_receipts WHERE id = ?",
                    (promotion.receipt_id,),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_function_membership_foreign_keys_reject_missing_targets(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, promotion = self._promote_three_as_function("schema-missing-target")
        with self.system.store.transaction(write=False) as connection:
            template = connection.execute(
                """
                SELECT * FROM function_memberships
                WHERE receipt_id = ? ORDER BY ordinal LIMIT 1
                """,
                (promotion.receipt_id,),
            ).fetchone()
        if template is None:
            raise AssertionError("function membership fixture disappeared")

        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            with self.subTest(target="report"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "FOREIGN KEY constraint failed",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-missing-report",
                        ordinal=0,
                        function_hash=template["function_hash"],
                        artifact_id=template["artifact_id"],
                        report_id="report-does-not-exist",
                        input_hash="1" * 64,
                        entry_seal="2" * 64,
                    )
            with self.subTest(target="artifact"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "FOREIGN KEY constraint failed",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-missing-artifact",
                        ordinal=0,
                        function_hash=template["function_hash"],
                        artifact_id="artifact-does-not-exist",
                        report_id=template["report_id"],
                        input_hash="3" * 64,
                        entry_seal="4" * 64,
                    )
        finally:
            connection.rollback()
            connection.close()

    def test_function_membership_foreign_keys_restrict_target_deletion(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, promotion = self._promote_three_as_function("schema-delete-action")
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row

        def clone_row(
            table: str,
            source: sqlite3.Row,
            **changes: object,
        ) -> None:
            values = {
                name: source[name]
                for name in source.keys()
                if name != "sequence"
            }
            values.update(changes)
            columns = tuple(values)
            connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                tuple(values[column] for column in columns),
            )

        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            template = connection.execute(
                """
                SELECT * FROM function_memberships
                WHERE receipt_id = ? ORDER BY ordinal LIMIT 1
                """,
                (promotion.receipt_id,),
            ).fetchone()
            if template is None:
                raise AssertionError("function membership fixture disappeared")
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (template["report_id"],),
            ).fetchone()
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?",
                (template["artifact_id"],),
            ).fetchone()
            if report is None or artifact is None:
                raise AssertionError("function membership target disappeared")

            report_id = "report-schema-delete-action"
            report_receipt_id = "receipt-schema-report-delete"
            clone_row("test_reports", report, id=report_id)
            self._insert_schema_membership(
                connection,
                receipt_id=report_receipt_id,
                ordinal=0,
                function_hash=template["function_hash"],
                artifact_id=template["artifact_id"],
                report_id=report_id,
                input_hash="5" * 64,
                entry_seal="6" * 64,
            )
            self._insert_schema_receipt(
                connection,
                receipt_id=report_receipt_id,
                function_hash=template["function_hash"],
                member_count=1,
            )

            artifact_id = "artifact-schema-delete-action"
            artifact_receipt_id = "receipt-schema-artifact-delete"
            clone_row(
                "artifacts",
                artifact,
                id=artifact_id,
                status="retired",
                verified_report_id=None,
                promoted_by=None,
                promoted_at_us=None,
                promotion_hash=None,
                status_reason="schema foreign-key action fixture",
            )
            self._insert_schema_membership(
                connection,
                receipt_id=artifact_receipt_id,
                ordinal=0,
                function_hash=template["function_hash"],
                artifact_id=artifact_id,
                report_id=template["report_id"],
                input_hash="7" * 64,
                entry_seal="8" * 64,
            )
            self._insert_schema_receipt(
                connection,
                receipt_id=artifact_receipt_id,
                function_hash=template["function_hash"],
                member_count=1,
            )

            # The membership foreign keys must be the only remaining delete defense.
            connection.execute("DROP TRIGGER test_reports_no_delete")
            connection.execute("DROP TRIGGER function_memberships_no_delete")
            with self.subTest(target="report", action="NO ACTION"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "FOREIGN KEY constraint failed",
                ):
                    connection.execute(
                        "DELETE FROM test_reports WHERE id = ?",
                        (report_id,),
                    )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM test_reports WHERE id = ?",
                        (report_id,),
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM function_memberships
                        WHERE receipt_id = ?
                        """,
                        (report_receipt_id,),
                    ).fetchone()[0],
                    1,
                )
            with self.subTest(target="artifact", action="NO ACTION"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "FOREIGN KEY constraint failed",
                ):
                    connection.execute(
                        "DELETE FROM artifacts WHERE id = ?",
                        (artifact_id,),
                    )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM artifacts WHERE id = ?",
                        (artifact_id,),
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM function_memberships
                        WHERE receipt_id = ?
                        """,
                        (artifact_receipt_id,),
                    ).fetchone()[0],
                    1,
                )
        finally:
            connection.rollback()
            connection.close()

    def test_function_membership_identity_constraints_reject_invalid_rows(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, promotion = self._promote_three_as_function("schema-membership-keys")
        with self.system.store.transaction(write=False) as connection:
            templates = tuple(
                connection.execute(
                    """
                    SELECT * FROM function_memberships
                    WHERE receipt_id = ? ORDER BY ordinal
                    """,
                    (promotion.receipt_id,),
                )
            )
        self.assertGreaterEqual(len(templates), 2)
        first, second = templates[:2]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")

            self._insert_schema_membership(
                connection,
                receipt_id="schema-duplicate-artifact",
                ordinal=0,
                function_hash=first["function_hash"],
                artifact_id=first["artifact_id"],
                report_id=first["report_id"],
                input_hash="1" * 64,
                entry_seal="2" * 64,
            )
            with self.subTest(key=("receipt_id", "artifact_id")):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "function_memberships.receipt_id, "
                    "function_memberships.artifact_id",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-duplicate-artifact",
                        ordinal=1,
                        function_hash=first["function_hash"],
                        artifact_id=first["artifact_id"],
                        report_id=second["report_id"],
                        input_hash="3" * 64,
                        entry_seal="4" * 64,
                    )

            self._insert_schema_membership(
                connection,
                receipt_id="schema-duplicate-input",
                ordinal=0,
                function_hash=first["function_hash"],
                artifact_id=first["artifact_id"],
                report_id=first["report_id"],
                input_hash="5" * 64,
                entry_seal="6" * 64,
            )
            with self.subTest(key=("receipt_id", "input_hash")):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "function_memberships.receipt_id, "
                    "function_memberships.input_hash",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-duplicate-input",
                        ordinal=1,
                        function_hash=second["function_hash"],
                        artifact_id=second["artifact_id"],
                        report_id=second["report_id"],
                        input_hash="5" * 64,
                        entry_seal="7" * 64,
                    )

            self._insert_schema_membership(
                connection,
                receipt_id="schema-duplicate-ordinal",
                ordinal=0,
                function_hash=first["function_hash"],
                artifact_id=first["artifact_id"],
                report_id=first["report_id"],
                input_hash="8" * 64,
                entry_seal="9" * 64,
            )
            with self.subTest(key=("receipt_id", "ordinal")):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "function_memberships.receipt_id, "
                    "function_memberships.ordinal",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-duplicate-ordinal",
                        ordinal=0,
                        function_hash=second["function_hash"],
                        artifact_id=second["artifact_id"],
                        report_id=second["report_id"],
                        input_hash="a" * 64,
                        entry_seal="b" * 64,
                    )

            with self.subTest(check="ordinal >= 0"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "CHECK constraint failed: ordinal >= 0",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-negative-ordinal",
                        ordinal=-1,
                        function_hash=first["function_hash"],
                        artifact_id=first["artifact_id"],
                        report_id=first["report_id"],
                        input_hash="c" * 64,
                        entry_seal="d" * 64,
                    )
        finally:
            connection.rollback()
            connection.close()

    def test_function_receipt_constraints_reject_invalid_rows(self) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("BEGIN IMMEDIATE")
            for field, changes, diagnostic in (
                (
                    "operation_revision",
                    {"operation_revision": 0},
                    "operation_revision >= 1",
                ),
                ("member_count", {"member_count": -1}, "member_count >= 0"),
                (
                    "candidate_count",
                    {"candidate_count": -1},
                    "candidate_count >= 0",
                ),
                (
                    "retired_count",
                    {"retired_count": -1},
                    "retired_count >= 0",
                ),
            ):
                with self.subTest(check=field):
                    with self.assertRaisesRegex(
                        sqlite3.IntegrityError,
                        f"CHECK constraint failed: {diagnostic}",
                    ):
                        self._insert_schema_receipt(
                            connection,
                            receipt_id=f"schema-invalid-{field}",
                            **changes,
                        )

            receipt_hash = "schema-duplicate-receipt-hash"
            self._insert_schema_receipt(
                connection,
                receipt_id="schema-receipt-hash-first",
                receipt_hash=receipt_hash,
            )
            with self.subTest(key=("receipt_hash",)):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "function_receipts.receipt_hash",
                ):
                    self._insert_schema_receipt(
                        connection,
                        receipt_id="schema-receipt-hash-second",
                        receipt_hash=receipt_hash,
                    )
        finally:
            connection.rollback()
            connection.close()

    def test_function_promotion_tables_reject_widened_identity_types(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, promotion = self._promote_three_as_function("schema-strict-types")
        with self.system.store.transaction(write=False) as connection:
            template = connection.execute(
                """
                SELECT * FROM function_memberships
                WHERE receipt_id = ? ORDER BY ordinal LIMIT 1
                """,
                (promotion.receipt_id,),
            ).fetchone()
        if template is None:
            raise AssertionError("function membership fixture disappeared")

        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            with self.subTest(table="function_memberships", column="entry_seal"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "cannot store BLOB value in TEXT column "
                    "function_memberships.entry_seal",
                ):
                    self._insert_schema_membership(
                        connection,
                        receipt_id="schema-membership-blob",
                        ordinal=0,
                        function_hash=template["function_hash"],
                        artifact_id=template["artifact_id"],
                        report_id=template["report_id"],
                        input_hash="e" * 64,
                        entry_seal=sqlite3.Binary(b"membership-seal"),
                    )
            with self.subTest(table="function_receipts", column="receipt_hash"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "cannot store BLOB value in TEXT column "
                    "function_receipts.receipt_hash",
                ):
                    self._insert_schema_receipt(
                        connection,
                        receipt_id="schema-receipt-blob",
                        receipt_hash=sqlite3.Binary(b"receipt-hash"),
                    )
        finally:
            connection.rollback()
            connection.close()

    def test_function_promotion_schema_one_fails_closed_with_version_diagnostic(self) -> None:
        legacy = str(pathlib.Path(self.temporary.name) / "schema-v1.db")
        connection = sqlite3.connect(legacy)
        try:
            connection.execute("CREATE TABLE legacy_payload(value TEXT)")
            connection.execute("INSERT INTO legacy_payload VALUES ('preserve-me')")
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        finally:
            connection.close()
        connection = sqlite3.connect(legacy)
        try:
            before = tuple(connection.iterdump())
        finally:
            connection.close()
        with self.assertRaisesRegex(
            IntegrityError,
            "database schema 1 is unsupported; expected 2",
        ):
            System(legacy)
        connection = sqlite3.connect(legacy)
        try:
            after = tuple(connection.iterdump())
            self.assertEqual(
                connection.execute("SELECT value FROM legacy_payload").fetchone()[0],
                "preserve-me",
            )
        finally:
            connection.close()
        self.assertEqual(after, before)

    def test_function_promotion_manifest_is_deterministic_read_only_and_complete(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-manifest")
        authority = mock.Mock(side_effect=AssertionError("authority consulted"))
        clock = mock.Mock(side_effect=AssertionError("clock consulted"))
        reader = System(self.database, authority=authority, clock_us=clock)
        independent = System(self.database)
        before = self._database_dump()
        with (
            mock.patch.object(
                reader.store,
                "transaction",
                wraps=reader.store.transaction,
            ) as transaction,
            mock.patch(
                "cement_runtime.system.uuid.uuid4",
                side_effect=AssertionError("ID allocated"),
            ),
        ):
            manifest = reader.inspect_function_promotion("tenant-a", "echo")
        repeated = independent.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)
        transaction.assert_called_once_with(write=False)
        authority.assert_not_called()
        clock.assert_not_called()
        self.assertIsInstance(manifest, FunctionPromotionManifest)
        self.assertEqual(manifest.text, repeated.text)
        self.assertEqual(manifest.operation_revision, 1)
        self.assertEqual(manifest.function_hash, manifest.document.function_hash)
        self.assertEqual(len(manifest.entries), 3)
        self.assertTrue(
            all(isinstance(entry, FunctionPromotionEntry) for entry in manifest.entries)
        )
        self.assertEqual(
            tuple(entry.input_hash for entry in manifest.entries),
            tuple(sorted(entry.input_hash for entry in manifest.entries)),
        )
        self.assertEqual(
            tuple(entry.disposition for entry in manifest.entries),
            ("candidate", "candidate", "candidate"),
        )
        self.assertTrue(
            all(entry.replaces_artifact_id is None for entry in manifest.entries)
        )
        self.assertEqual(manifest.skipped, ())
        raw = json.loads(manifest.text)
        self.assertEqual(raw["abi"], "cement-function-promotion-manifest-v1")
        self.assertEqual(FUNCTION_PROMOTION_MANIFEST_ABI, raw["abi"])
        self.assertEqual(raw["function"], manifest.document.value)
        self.assertEqual(raw["function_hash"], manifest.function_hash)
        self.assertEqual(raw["skipped"], list(manifest.skipped))
        self.assertEqual(
            raw["entries"],
            [
                {
                    "artifact_hash": entry.artifact_hash,
                    "artifact_id": entry.artifact_id,
                    "disposition": entry.disposition,
                    "entry_seal": entry.entry_seal,
                    "input_hash": entry.input_hash,
                    "output_hash": entry.output_hash,
                    "replaces_artifact_id": entry.replaces_artifact_id,
                }
                for entry in manifest.entries
            ],
        )
        document_scope = manifest.document.value["scope"]
        self.assertIsInstance(document_scope, dict)
        assert type(document_scope) is dict
        self.assertEqual(
            raw["scope"],
            {
                "operation": "echo",
                "operation_revision": 1,
                "partition": "tenant-a",
                "policy_hash": document_scope["policy_hash"],
            },
        )
        with self.assertRaises(FrozenInstanceError):
            manifest.function_hash = "0" * 64  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            manifest.entries[1].disposition = "retained"  # type: ignore[misc]
        self.assertFalse(hasattr(manifest, "__dict__"))
        self.assertFalse(hasattr(manifest.entries[1], "__dict__"))

    def test_promote_function_persists_receipt_memberships_and_projected_event(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        batch = self._verify_three_function_candidates("function-success")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        self.assertIsInstance(promotion, FunctionSetPromotion)
        self.assertEqual(promotion.function_hash, manifest.function_hash)
        self.assertEqual(promotion.operation_revision, manifest.operation_revision)
        self.assertEqual(promotion.promoted_at_us, self.clock.now_us)
        self.assertEqual(
            promotion.member_artifact_ids,
            tuple(sorted(entry.artifact_id for entry in manifest.entries)),
        )
        self.assertEqual(
            promotion.candidate_artifact_ids,
            promotion.member_artifact_ids,
        )
        self.assertEqual(promotion.retired_artifact_ids, ())
        self.assertFalse(hasattr(promotion, "__dict__"))

        verified = self.system.verify_function("tenant-a", "echo")
        self.assertTrue(verified.passed)
        self.assertEqual(verified.function_hash, manifest.function_hash)
        self.assertEqual(verified.document, manifest.document)
        with self.system.store.transaction(write=False) as connection:
            receipt = connection.execute(
                "SELECT * FROM function_receipts WHERE id = ?",
                (promotion.receipt_id,),
            ).fetchone()
            memberships = tuple(
                connection.execute(
                    """
                    SELECT * FROM function_memberships
                    WHERE receipt_id = ? ORDER BY ordinal
                    """,
                    (promotion.receipt_id,),
                )
            )
            artifacts = tuple(
                connection.execute(
                    """
                    SELECT * FROM artifacts WHERE id IN (?, ?, ?)
                    ORDER BY input_hash, sequence, id
                    """,
                    promotion.member_artifact_ids,
                )
            )
            event = connection.execute(
                """
                SELECT * FROM events
                WHERE kind = 'function.promoted' AND subject_id = ?
                """,
                (promotion.receipt_id,),
            ).fetchone()
            reports = {
                str(row["id"]): connection.execute(
                    "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                    (row["verified_report_id"], row["id"]),
                ).fetchone()
                for row in artifacts
            }
        if receipt is None or event is None or any(report is None for report in reports.values()):
            raise AssertionError("persisted function promotion fixture disappeared")
        self.assertEqual(len(memberships), 3)
        self.assertEqual(tuple(int(row["ordinal"]) for row in memberships), (0, 1, 2))
        self.assertEqual(
            tuple(str(row["input_hash"]) for row in memberships),
            tuple(entry.input_hash for entry in manifest.entries),
        )
        self.assertEqual(
            tuple(str(row["artifact_id"]) for row in memberships),
            tuple(entry.artifact_id for entry in manifest.entries),
        )
        self.assertEqual(
            tuple(str(row["entry_seal"]) for row in memberships),
            tuple(entry.entry_seal for entry in manifest.entries),
        )
        self.assertTrue(
            all(row["function_hash"] == manifest.function_hash for row in memberships)
        )
        self.assertEqual(receipt["membership_hash"], _membership_hash(memberships))
        self.assertEqual(receipt["member_count"], 3)
        self.assertEqual(
            receipt["candidate_artifact_ids_hash"],
            _id_list_hash(promotion.candidate_artifact_ids),
        )
        self.assertEqual(receipt["candidate_count"], 3)
        self.assertEqual(receipt["retired_artifact_ids_hash"], _id_list_hash(()))
        self.assertEqual(receipt["retired_count"], 0)
        self.assertEqual(receipt["receipt_hash"], _function_receipt_hash(receipt))
        self.assertEqual(receipt["receipt_hash"], promotion.receipt_hash)
        self.assertEqual(receipt["promoted_by"], "release-manager")
        self.assertEqual(receipt["promoted_at_us"], self.clock.now_us)
        self.assertEqual(
            tuple(str(row["status"]) for row in artifacts),
            ("promoted", "promoted", "promoted"),
        )
        self.assertEqual(
            {str(row["promoted_by"]) for row in artifacts},
            {"release-manager"},
        )
        self.assertEqual(
            {int(row["promoted_at_us"]) for row in artifacts},
            {self.clock.now_us},
        )
        for row in artifacts:
            report = reports[str(row["id"])]
            assert report is not None
            self.assertEqual(row["promotion_hash"], self._promotion_hash(row, report))
        payload = json.loads(str(event["payload_json"]))
        self.assertEqual(event["subject_type"], "function")
        self.assertEqual(
            payload,
            {
                "candidate_artifact_count": 3,
                "candidate_artifact_ids": list(promotion.candidate_artifact_ids),
                "candidate_artifact_ids_hash": _id_list_hash(
                    promotion.candidate_artifact_ids
                ),
                "function_hash": manifest.function_hash,
                "member_artifact_count": 3,
                "member_artifact_ids": list(promotion.member_artifact_ids),
                "member_artifact_ids_hash": _id_list_hash(
                    promotion.member_artifact_ids
                ),
                "promoted_by": "release-manager",
                "receipt_hash": promotion.receipt_hash,
                "receipt_id": promotion.receipt_id,
                "retired_artifact_count": 0,
                "retired_artifact_ids": [],
                "retired_artifact_ids_hash": _id_list_hash(()),
            },
        )
        self.assertEqual(
            {entry.artifact_id: entry.entry_seal for entry in batch.entries},
            {
                entry.artifact_id: entry.entry_seal
                for entry in manifest.entries
            },
        )

    def test_function_promotion_receipt_hash_binds_fourteen_fields_independently(self) -> None:
        fields: dict[str, object] = {
            "id": "fpr_receipt",
            "partition": "tenant-a",
            "operation": "echo",
            "operation_revision": 10,
            "policy_hash": "0" * 64,
            "function_hash": "1" * 64,
            "membership_hash": "2" * 64,
            "member_count": 11,
            "candidate_artifact_ids_hash": "3" * 64,
            "candidate_count": 12,
            "retired_artifact_ids_hash": "4" * 64,
            "retired_count": 13,
            "promoted_by": "release-manager",
            "promoted_at_us": 1_234_567,
        }
        ordered_names = (
            "id",
            "partition",
            "operation",
            "operation_revision",
            "policy_hash",
            "function_hash",
            "membership_hash",
            "member_count",
            "candidate_artifact_ids_hash",
            "candidate_count",
            "retired_artifact_ids_hash",
            "retired_count",
            "promoted_by",
            "promoted_at_us",
        )
        mutations: dict[str, object] = {
            "id": "fpr_changed",
            "partition": "tenant-b",
            "operation": "other",
            "operation_revision": 14,
            "policy_hash": "5" * 64,
            "function_hash": "6" * 64,
            "membership_hash": "7" * 64,
            "member_count": 15,
            "candidate_artifact_ids_hash": "8" * 64,
            "candidate_count": 16,
            "retired_artifact_ids_hash": "9" * 64,
            "retired_count": 17,
            "promoted_by": "other-manager",
            "promoted_at_us": 1_234_568,
        }
        self.assertEqual(len(fields), 14)
        self.assertEqual(set(mutations), set(fields))
        self.assertEqual(
            tuple(
                fields[name]
                for name in (
                    "operation_revision",
                    "member_count",
                    "candidate_count",
                    "retired_count",
                )
            ),
            (10, 11, 12, 13),
        )
        baseline = _function_receipt_hash(fields)
        for field, changed_value in mutations.items():
            changed = dict(fields)
            changed[field] = changed_value
            differences = [name for name in fields if changed[name] != fields[name]]
            with self.subTest(field=field):
                self.assertEqual(differences, [field])
                self.assertNotEqual(_function_receipt_hash(changed), baseline)

        def framed_digest(label: str, values: tuple[str, ...]) -> str:
            digest = hashlib.sha256()
            for value in (label, *values):
                encoded = value.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
            return digest.hexdigest()

        self.assertEqual(
            FUNCTION_PROMOTION_RECEIPT_ABI,
            "cement-function-promotion-v1",
        )
        self.assertEqual(
            baseline,
            framed_digest(
                "cement-function-promotion-v1",
                tuple(str(fields[name]) for name in ordered_names),
            ),
        )

    def test_function_membership_hash_binds_each_later_row_component(self) -> None:
        rows = tuple(
            {
                "ordinal": ordinal,
                "artifact_id": f"artifact-{ordinal}",
                "report_id": f"report-{ordinal}",
                "input_hash": f"{ordinal + 1:064x}",
                "entry_seal": f"{ordinal + 4:064x}",
            }
            for ordinal in range(10, 13)
        )
        self.assertEqual(tuple(row["ordinal"] for row in rows), (10, 11, 12))
        baseline = _membership_hash(rows)
        mutations: dict[str, int | str] = {
            "ordinal": 19,
            "artifact_id": "artifact-changed",
            "report_id": "report-changed",
            "input_hash": "8" * 64,
            "entry_seal": "9" * 64,
        }
        for field, changed_value in mutations.items():
            changed_rows = [dict(row) for row in rows]
            changed_rows[1][field] = changed_value
            differences = [
                (index, key)
                for index, row in enumerate(changed_rows)
                for key in row
                if row[key] != rows[index][key]
            ]
            with self.subTest(field=field):
                self.assertEqual(differences, [(1, field)])
                self.assertNotEqual(_membership_hash(changed_rows), baseline)

        def framed_digest(label: str, values: tuple[str, ...]) -> str:
            digest = hashlib.sha256()
            for value in (label, *values):
                encoded = value.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
            return digest.hexdigest()

        ordered = tuple(
            str(row[field])
            for row in rows
            for field in (
                "ordinal",
                "artifact_id",
                "report_id",
                "input_hash",
                "entry_seal",
            )
        )
        self.assertEqual(FUNCTION_MEMBERSHIP_ABI, "cement-function-membership-v1")
        self.assertEqual(
            baseline,
            framed_digest("cement-function-membership-v1", ordered),
        )
        self.assertNotEqual(_membership_hash(tuple(reversed(rows))), baseline)
        self.assertEqual(
            _id_list_hash(("artifact-c", "artifact-a", "artifact-b")),
            framed_digest(
                "cement-id-list-v1",
                ("artifact-a", "artifact-b", "artifact-c"),
            ),
        )


    def test_promote_function_growth_retains_the_complete_existing_set(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        first_manifest, first = self._promote_three_as_function("function-growth-base")
        for value in (4, 5, 6):
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-growth-{value}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-growth-{value}-b",
                reviewer="bob",
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 3)
        batch = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(batch.passed)
        self.assertEqual(len(batch.entries), 3)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        retained = tuple(
            entry.artifact_id
            for entry in manifest.entries
            if entry.disposition == "retained"
        )
        candidates = tuple(
            entry.artifact_id
            for entry in manifest.entries
            if entry.disposition == "candidate"
        )
        self.assertEqual(len(manifest.entries), 6)
        self.assertEqual(
            tuple(entry.input_hash for entry in manifest.entries),
            tuple(sorted(entry.input_hash for entry in manifest.entries)),
        )
        self.assertEqual(set(retained), set(first.member_artifact_ids))
        self.assertEqual(
            set(candidates),
            {entry.artifact_id for entry in batch.entries},
        )
        self.assertTrue(
            all(entry.replaces_artifact_id is None for entry in manifest.entries)
        )
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        self.assertEqual(len(promotion.member_artifact_ids), 6)
        self.assertEqual(set(promotion.candidate_artifact_ids), set(candidates))
        self.assertEqual(promotion.retired_artifact_ids, ())
        self.assertNotEqual(manifest.function_hash, first_manifest.function_hash)
        verified = self.system.verify_function("tenant-a", "echo")
        self.assertTrue(verified.passed)
        self.assertEqual(verified.entries, 6)
        self.assertEqual(verified.function_hash, manifest.function_hash)
        with self.system.store.transaction(write=False) as connection:
            retained_statuses = tuple(
                str(row["status"])
                for row in connection.execute(
                    "SELECT status FROM artifacts WHERE id IN (?, ?, ?)",
                    first.member_artifact_ids,
                )
            )
        self.assertEqual(retained_statuses, ("promoted", "promoted", "promoted"))

    def test_promote_function_retires_three_predecessors_before_activation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, initial = self._promote_three_as_function("function-replace-base")
        replacements = self._challenge_three_function_entries("function-replace")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        self.assertEqual(
            tuple(entry.disposition for entry in manifest.entries),
            ("candidate", "candidate", "candidate"),
        )
        self.assertEqual(
            {entry.replaces_artifact_id for entry in manifest.entries},
            set(initial.member_artifact_ids),
        )
        self.assertEqual(
            {entry.artifact_id for entry in manifest.entries},
            {entry.artifact_id for entry in replacements.entries},
        )
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        self.assertEqual(
            promotion.retired_artifact_ids,
            tuple(sorted(initial.member_artifact_ids)),
        )
        self.assertEqual(
            promotion.member_artifact_ids,
            tuple(sorted(entry.artifact_id for entry in replacements.entries)),
        )
        with self.system.store.transaction(write=False) as connection:
            retired = {
                str(row["id"]): (
                    str(row["status"]),
                    row["promotion_hash"],
                    str(row["status_reason"]),
                )
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE id IN (?, ?, ?)",
                    initial.member_artifact_ids,
                )
            }
            active = {
                str(row["id"]): str(row["status"])
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE id IN (?, ?, ?)",
                    promotion.member_artifact_ids,
                )
            }
        self.assertEqual(
            retired,
            {
                artifact_id: (
                    "retired",
                    None,
                    "replaced by function promotion",
                )
                for artifact_id in initial.member_artifact_ids
            },
        )
        self.assertEqual(set(active.values()), {"promoted"})
        verified = self.system.verify_function("tenant-a", "echo")
        self.assertTrue(verified.passed)
        self.assertEqual(verified.function_hash, manifest.function_hash)

    def test_promote_function_zero_candidate_checkpoints_legacy_set(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        legacy_ids = self._promote_three_function_entries("function-checkpoint")
        current = self.system.verify_function("tenant-a", "echo")
        self.assertTrue(current.passed)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        self.assertEqual(
            tuple(entry.disposition for entry in manifest.entries),
            ("retained", "retained", "retained"),
        )
        self.assertEqual(
            {entry.artifact_id for entry in manifest.entries},
            set(legacy_ids),
        )
        first = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        repeated_manifest = self.system.inspect_function_promotion(
            "tenant-a",
            "echo",
        )
        second = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=repeated_manifest.function_hash,
            promoted_by="release-manager",
        )
        self.assertEqual(manifest.function_hash, current.function_hash)
        self.assertEqual(repeated_manifest.function_hash, manifest.function_hash)
        self.assertEqual(first.function_hash, second.function_hash)
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        self.assertNotEqual(first.receipt_hash, second.receipt_hash)
        self.assertEqual(first.candidate_artifact_ids, ())
        self.assertEqual(second.candidate_artifact_ids, ())
        self.assertEqual(first.retired_artifact_ids, ())
        self.assertEqual(second.retired_artifact_ids, ())
        self.assertEqual(set(first.member_artifact_ids), set(legacy_ids))
        with self.system.store.transaction(write=False) as connection:
            receipts = tuple(
                connection.execute(
                    """
                    SELECT candidate_count, member_count, function_hash
                    FROM function_receipts ORDER BY sequence
                    """
                )
            )
            statuses = tuple(
                str(row["status"])
                for row in connection.execute(
                    "SELECT status FROM artifacts WHERE id IN (?, ?, ?)",
                    legacy_ids,
                )
            )
        self.assertEqual(
            tuple((row["candidate_count"], row["member_count"]) for row in receipts),
            ((0, 3), (0, 3)),
        )
        self.assertEqual(
            {str(row["function_hash"]) for row in receipts},
            {manifest.function_hash},
        )
        self.assertEqual(statuses, ("promoted", "promoted", "promoted"))

    def test_function_promotion_reports_three_superseded_verified_rows(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        old = self._verify_three_function_candidates("function-skipped-old")
        for value in (1, 2, 3):
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-skipped-new-{value}",
                reviewer="alice",
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 3)
        current = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(current.passed)
        self.assertEqual(len(current.entries), 3)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        self.assertEqual(len(manifest.skipped), 3)
        self.assertEqual(
            {entry.artifact_id for entry in manifest.entries},
            {entry.artifact_id for entry in current.entries},
        )
        self.assertEqual(
            {str(item["artifact_id"]) for item in manifest.skipped},
            {entry.artifact_id for entry in old.entries},
        )
        self.assertEqual(
            {str(item["reason"]) for item in manifest.skipped},
            {"superseded-build"},
        )
        self.assertEqual(
            json.loads(manifest.text)["skipped"],
            list(manifest.skipped),
        )
        self.assertEqual(
            tuple(
                (str(item["input_hash"]), str(item["artifact_id"]))
                for item in manifest.skipped
            ),
            tuple(
                sorted(
                    (
                        str(item["input_hash"]),
                        str(item["artifact_id"]),
                    )
                    for item in manifest.skipped
                )
            ),
        )
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        self.assertEqual(len(promotion.candidate_artifact_ids), 3)
        with self.system.store.transaction(write=False) as connection:
            old_statuses = tuple(
                str(row["status"])
                for row in connection.execute(
                    "SELECT status FROM artifacts WHERE id IN (?, ?, ?)",
                    tuple(entry.artifact_id for entry in old.entries),
                )
            )
        self.assertEqual(old_statuses, ("verified", "verified", "verified"))

    def test_function_promotion_rejects_duplicate_eligible_candidate(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-duplicate-candidate")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                """
                INSERT INTO artifacts(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                    status_reason
                )
                SELECT 'artifact_duplicate_candidate', partition, operation,
                    operation_revision, input_json, input_hash, output_json, output_hash,
                    artifact_json, artifact_hash, scope_hash, build_hash, policy_json,
                    policy_hash, evidence_snapshot_hash, status, support, reviewer_count,
                    span_seconds, created_at_us, verified_report_id, promoted_by,
                    promoted_at_us, promotion_hash, status_reason
                FROM artifacts WHERE id = ?
                """,
                (target.artifact_id,),
            )
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "multiple verified candidates claim current input",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_later_canonical_input_collision(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-input-collision")
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            groups = connection.execute(
                """
                SELECT input_hash, input_json FROM examples
                WHERE partition = 'tenant-a' AND operation = 'echo'
                GROUP BY input_hash, input_json ORDER BY input_hash, input_json
                """
            ).fetchall()
            self.assertEqual(len(groups), 3)
            target = groups[-1]
            collision = groups[1]
            example = connection.execute(
                """
                SELECT id FROM examples WHERE input_hash = ? AND input_json = ?
                ORDER BY id LIMIT 1
                """,
                (target["input_hash"], target["input_json"]),
            ).fetchone()
            if example is None:
                raise AssertionError("collision target disappeared")
            connection.execute("DROP TRIGGER examples_no_update")
            changed = connection.execute(
                "UPDATE examples SET input_hash = ? WHERE id = ?",
                (collision["input_hash"], example["id"]),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "one input digest maps to multiple canonical inputs",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)


    def test_promote_function_rejects_malformed_expected_hash_without_preflight(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-malformed-hash")
        authority = mock.Mock(side_effect=AssertionError("authority consulted"))
        clock = mock.Mock(side_effect=AssertionError("clock consulted"))
        reader = System(self.database, authority=authority, clock_us=clock)
        before = self._database_dump()
        with (
            mock.patch.object(
                reader.store,
                "transaction",
                wraps=reader.store.transaction,
            ) as transaction,
            mock.patch(
                "cement_runtime.system.uuid.uuid4",
                side_effect=AssertionError("ID allocated"),
            ),
        ):
            with self.assertRaisesRegex(
                ValidationError,
                "expected_function_hash must be a SHA-256 hex digest",
            ):
                reader.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash="not-a-digest",
                    promoted_by="release-manager",
                )
        self.assertEqual(self._database_dump(), before)
        transaction.assert_not_called()
        authority.assert_not_called()
        clock.assert_not_called()

    def test_promote_function_rejects_well_formed_hash_mismatch_atomically(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-hash-conflict")
        before = self._database_dump()
        with self.assertRaisesRegex(
            ConflictError,
            "expected_function_hash does not match the locked prospective function",
        ):
            self.system.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash="0" * 64,
                promoted_by="release-manager",
            )
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_authorizes_every_member_before_clock_or_write(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-authority")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        ordered_ids = tuple(entry.artifact_id for entry in manifest.entries)
        denied = ordered_ids[-1]
        calls: list[tuple[str, str, str, str]] = []

        def authority(partition, actor, action, subject):
            calls.append((partition, actor, action, subject))
            return subject != denied

        clock = mock.Mock(side_effect=AssertionError("clock consulted"))
        reader = System(self.database, authority=authority, clock_us=clock)
        before = self._database_dump()
        with mock.patch.object(
            reader.store,
            "transaction",
            wraps=reader.store.transaction,
        ) as transaction:
            with self.assertRaisesRegex(StateError, "not authorized"):
                reader.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="blocked-manager",
                )
        self.assertEqual(
            calls,
            [
                ("tenant-a", "blocked-manager", "artifact.promote", artifact_id)
                for artifact_id in ordered_ids
            ],
        )
        self.assertEqual(transaction.call_args_list, [mock.call(write=False)])
        clock.assert_not_called()
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_old_manifest_rejects_middle_retained_revocation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-revoked")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        target = manifest.entries[1]
        self.system.revoke_example(
            "tenant-a",
            self._function_member_evidence_id(target.artifact_id),
            revoked_by="auditor",
            reason="manifest-to-promotion retained-row probe",
        )
        before = self._database_dump()
        with self.assertRaisesRegex(
            ConflictError,
            "expected_function_hash does not match",
        ):
            self.system.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=manifest.function_hash,
                promoted_by="release-manager",
            )
        self.assertEqual(self._database_dump(), before)
        with self.system.store.transaction(write=False) as connection:
            status = connection.execute(
                "SELECT status FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()
        self.assertIsNotNone(status)
        assert status is not None
        self.assertEqual(status["status"], "suspended")

    def test_promote_function_rechecks_candidate_set_after_authorization(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-candidate-race")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1].artifact_id
        mutator = System(self.database)
        calls: list[str] = []
        post_mutation: list[tuple[str, ...]] = []

        def authority(partition, actor, action, subject):
            calls.append(subject)
            if subject == target:
                mutator.suspend_artifact(
                    "tenant-a",
                    target,
                    suspended_by="auditor",
                    reason="authorization race probe",
                )
                post_mutation.append(self._database_dump())
            return True

        reader = System(self.database, authority=authority, clock_us=self.clock)
        with self.assertRaisesRegex(
            StateError,
            "function promotion candidates changed during authorization",
        ):
            reader.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=manifest.function_hash,
                promoted_by="release-manager",
            )
        self.assertEqual(calls, [entry.artifact_id for entry in manifest.entries])
        self.assertEqual(len(post_mutation), 1)
        self.assertEqual(self._database_dump(), post_mutation[0])

    def test_promote_function_late_event_failure_rolls_back_every_write(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, initial = self._promote_three_as_function("function-late-abort-base")
        replacements = self._challenge_three_function_entries(
            "function-late-abort-replace"
        )
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        self.assertTrue(
            all(entry.replaces_artifact_id is not None for entry in manifest.entries)
        )
        before = self._database_dump()
        observed = False

        def fail_after_receipt(connection, **kwargs):
            nonlocal observed
            observed = True
            receipt_count = connection.execute(
                "SELECT COUNT(*) FROM function_receipts"
            ).fetchone()[0]
            member_count = connection.execute(
                "SELECT COUNT(*) FROM function_memberships"
            ).fetchone()[0]
            retired = connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE status = 'retired'"
            ).fetchone()[0]
            promoted = connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE status = 'promoted'"
            ).fetchone()[0]
            self.assertEqual(receipt_count, 2)
            self.assertEqual(member_count, 6)
            self.assertEqual(retired, 3)
            self.assertEqual(promoted, 3)
            self.assertEqual(kwargs["kind"], "function.promoted")
            raise StateError("injected failure after membership and receipt writes")

        with mock.patch(
            "cement_runtime.system._event",
            side_effect=fail_after_receipt,
        ):
            with self.assertRaisesRegex(
                StateError,
                "injected failure after membership and receipt writes",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertTrue(observed)
        self.assertEqual(self._database_dump(), before)
        self.assertEqual(
            {entry.artifact_id for entry in replacements.entries},
            {entry.artifact_id for entry in manifest.entries},
        )
        with self.system.store.transaction(write=False) as connection:
            initial_statuses = tuple(
                str(row["status"])
                for row in connection.execute(
                    "SELECT status FROM artifacts WHERE id IN (?, ?, ?)",
                    initial.member_artifact_ids,
                )
            )
        self.assertEqual(
            initial_statuses,
            ("promoted", "promoted", "promoted"),
        )

    def test_function_promotion_rejects_last_stale_revision_promoted_row(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-stale-promoted")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            changed = connection.execute(
                "UPDATE artifacts SET operation_revision = 2 WHERE id = ?",
                (target.artifact_id,),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            f"promoted artifact {target.artifact_id} has stale operation revision",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_replays_the_last_candidate(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-candidate-replay")
        baseline = self.system.inspect_function_promotion("tenant-a", "echo")
        target = baseline.entries[-1].artifact_id
        original = self.system._run_verification
        calls: list[str] = []

        def fail_last(connection, row, *, record_test=None):
            calls.append(str(row["id"]))
            if str(row["id"]) == target:
                artifact = self.system._artifact_from_row(row)
                return ["injected candidate replay failure"], 0, artifact
            return original(connection, row, record_test=record_test)

        before = self._database_dump()
        with mock.patch.object(
            self.system,
            "_run_verification",
            side_effect=fail_last,
        ):
            with self.assertRaisesRegex(
                StateError,
                "function candidate .* stopped qualifying: "
                "injected candidate replay failure",
            ):
                self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(calls, [entry.artifact_id for entry in baseline.entries])
        self.assertEqual(self._database_dump(), before)


    def test_function_promotion_rejects_middle_retained_policy_drift(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-policy")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            changed = connection.execute(
                "UPDATE artifacts SET policy_hash = ? WHERE id = ?",
                ("0" * 64, target.artifact_id),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            f"promoted artifact {target.artifact_id} has stale operation policy",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rehashes_last_retained_report_child_set(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-report")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        connection = sqlite3.connect(self.database)
        try:
            report_id = connection.execute(
                "SELECT verified_report_id FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()[0]
            test_key = connection.execute(
                """
                SELECT test_key FROM artifact_tests
                WHERE report_id = ? ORDER BY test_key DESC LIMIT 1
                """,
                (report_id,),
            ).fetchone()[0]
            connection.execute("DROP TRIGGER artifact_tests_no_update")
            changed = connection.execute(
                """
                UPDATE artifact_tests SET detail = detail || '-changed'
                WHERE report_id = ? AND test_key = ?
                """,
                (report_id, test_key),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "verification report test set mismatch",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_middle_retained_receipt_provenance(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-receipt")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[1]
        connection = sqlite3.connect(self.database)
        try:
            changed = connection.execute(
                "UPDATE artifacts SET promoted_by = 'forged-manager' WHERE id = ?",
                (target.artifact_id,),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(IntegrityError, "promotion receipt"):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_last_retained_artifact_document(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-artifact")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            changed = connection.execute(
                "UPDATE artifacts SET artifact_json = '{}' WHERE id = ?",
                (target.artifact_id,),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(IntegrityError, "artifact"):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rehashes_last_candidate_report_child_set(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-candidate-report")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        connection = sqlite3.connect(self.database)
        try:
            report_id = connection.execute(
                "SELECT verified_report_id FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()[0]
            test_key = connection.execute(
                """
                SELECT test_key FROM artifact_tests
                WHERE report_id = ? ORDER BY test_key DESC LIMIT 1
                """,
                (report_id,),
            ).fetchone()[0]
            connection.execute("DROP TRIGGER artifact_tests_no_update")
            changed = connection.execute(
                """
                UPDATE artifact_tests SET detail = detail || '-changed'
                WHERE report_id = ? AND test_key = ?
                """,
                (report_id, test_key),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "verification report test set mismatch",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_operation_policy_binding_mutation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-operation-policy")
        connection = sqlite3.connect(self.database)
        try:
            changed = connection.execute(
                """
                UPDATE operations SET policy_json = ?
                WHERE partition = 'tenant-a' AND name = 'echo'
                """,
                (json.dumps(CompilePolicy(2, 1, 0).as_json(), sort_keys=True),),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(IntegrityError, "operation policy binding mismatch"):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_duplicate_retained_input(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-duplicate-retained")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[1]
        self._clone_promoted_function_entry(
            target.artifact_id,
            duplicate_id="artifact_duplicate_retained",
            duplicate_report_id="report_duplicate_retained",
        )
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "multiple promoted artifacts claim input",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_uses_current_build_projection_for_all_candidates(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-shared-projection")
        original = self.system._project_current_build
        calls: list[tuple[str, str]] = []

        def projected(connection, operation_row, input_hash, input_json):
            calls.append((input_hash, input_json))
            return original(connection, operation_row, input_hash, input_json)

        with mock.patch.object(
            self.system,
            "_project_current_build",
            side_effect=projected,
        ):
            manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        self.assertEqual(
            tuple(input_hash for input_hash, _ in calls),
            tuple(entry.input_hash for entry in manifest.entries),
        )
        self.assertEqual(len(set(calls)), 3)

    def test_promote_function_predecessor_rowcount_guard_rolls_back(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retire-rowcount-base")
        self._challenge_three_function_entries("function-retire-rowcount-new")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        before = self._database_dump()
        original_transaction = self.system.store.transaction
        injected = False

        class ZeroRowcount:
            rowcount = 0

        class ConnectionProxy:
            def __init__(self, connection):
                self.connection = connection

            def execute(self, sql, parameters=()):
                nonlocal injected
                cursor = self.connection.execute(sql, parameters)
                normalized = " ".join(sql.split())
                if (
                    not injected
                    and normalized.startswith("UPDATE artifacts SET status = 'retired'")
                ):
                    injected = True
                    return ZeroRowcount()
                return cursor

            def __getattr__(self, name):
                return getattr(self.connection, name)

        @contextmanager
        def transaction(*, write=False):
            with original_transaction(write=write) as connection:
                yield ConnectionProxy(connection) if write else connection

        with mock.patch.object(
            self.system.store,
            "transaction",
            side_effect=transaction,
        ):
            with self.assertRaisesRegex(
                StateError,
                "function predecessor changed before locked retirement",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertTrue(injected)
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_candidate_rowcount_guard_rolls_back_last_activation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-activate-rowcount")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1].artifact_id
        before = self._database_dump()
        original_transaction = self.system.store.transaction
        injected = False

        class ZeroRowcount:
            rowcount = 0

        class ConnectionProxy:
            def __init__(self, connection):
                self.connection = connection

            def execute(self, sql, parameters=()):
                nonlocal injected
                cursor = self.connection.execute(sql, parameters)
                normalized = " ".join(sql.split())
                if (
                    not injected
                    and normalized.startswith(
                        "UPDATE artifacts SET status = 'promoted'"
                    )
                    and parameters[-1] == target
                ):
                    injected = True
                    return ZeroRowcount()
                return cursor

            def __getattr__(self, name):
                return getattr(self.connection, name)

        @contextmanager
        def transaction(*, write=False):
            with original_transaction(write=write) as connection:
                yield ConnectionProxy(connection) if write else connection

        with mock.patch.object(
            self.system.store,
            "transaction",
            side_effect=transaction,
        ):
            with self.assertRaisesRegex(
                StateError,
                "function candidate changed before locked activation",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertTrue(injected)
        self.assertEqual(self._database_dump(), before)


    def test_promote_function_event_projects_first_hundred_of_complete_id_set(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        for value in range(101):
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-event-bound-{value}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-event-bound-{value}-b",
                reviewer="bob",
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 101)
        batch = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(batch.passed)
        self.assertEqual(len(batch.entries), 101)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        with self.system.store.transaction(write=False) as connection:
            event = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE kind = 'function.promoted' AND subject_id = ?
                """,
                (promotion.receipt_id,),
            ).fetchone()
        if event is None:
            raise AssertionError("projected function event disappeared")
        payload = json.loads(str(event["payload_json"]))
        complete = tuple(sorted(promotion.member_artifact_ids))
        self.assertEqual(len(complete), 101)
        self.assertEqual(payload["member_artifact_count"], 101)
        self.assertEqual(payload["candidate_artifact_count"], 101)
        self.assertEqual(payload["member_artifact_ids"], list(complete[:100]))
        self.assertEqual(payload["candidate_artifact_ids"], list(complete[:100]))
        self.assertNotIn(complete[-1], payload["member_artifact_ids"])
        self.assertNotIn(complete[-1], payload["candidate_artifact_ids"])
        self.assertEqual(
            payload["member_artifact_ids_hash"],
            _id_list_hash(complete),
        )
        self.assertEqual(
            payload["candidate_artifact_ids_hash"],
            _id_list_hash(complete),
        )


    def test_function_promotion_unknown_operation_is_domain_not_found(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        with self.assertRaisesRegex(NotFoundError, "operation is not registered"):
            self.system.inspect_function_promotion("tenant-a", "missing")

    def test_function_promotion_rejects_invalid_operation_scalar_types(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-operation-scalars")
        corruptions = (
            ("revision", b"1", "stored operation revision"),
            ("policy_json", b"{}", "stored operation policy JSON"),
            ("policy_hash", b"0" * 64, "stored operation policy hash"),
        )

        class OneRowCursor:
            def __init__(self, row) -> None:
                self.row = row

            def fetchone(self):
                return self.row

        original_transaction = self.system.store.transaction
        for field, value, detail in corruptions:
            with self.subTest(field=field):

                @contextmanager
                def transaction(*, write=False):
                    self.assertFalse(write)
                    with original_transaction(write=False) as connection:

                        class ConnectionProxy:
                            def execute(self, sql, parameters=()):
                                cursor = connection.execute(sql, parameters)
                                if sql.startswith("SELECT * FROM operations WHERE"):
                                    row = cursor.fetchone()
                                    if row is None:
                                        return OneRowCursor(None)
                                    altered = dict(row)
                                    altered[field] = value
                                    return OneRowCursor(altered)
                                return cursor

                        yield ConnectionProxy()

                with mock.patch.object(
                    self.system.store,
                    "transaction",
                    side_effect=transaction,
                ):
                    with self.assertRaisesRegex(IntegrityError, detail):
                        self.system.inspect_function_promotion("tenant-a", "echo")

    def test_function_promotion_rejects_operation_policy_digest_mutation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-policy-digest")
        connection = sqlite3.connect(self.database)
        try:
            changed = connection.execute(
                """
                UPDATE operations SET policy_hash = ?
                WHERE partition = 'tenant-a' AND name = 'echo'
                """,
                ("0" * 64,),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(IntegrityError, "operation policy binding mismatch"):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_middle_retained_policy_json_drift(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-policy-json")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[1]
        changed_policy = canonicalize(CompilePolicy(3, 1, 0).as_json()).text
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            changed = connection.execute(
                "UPDATE artifacts SET policy_json = ? WHERE id = ?",
                (changed_policy, target.artifact_id),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            f"promoted artifact {target.artifact_id} has stale operation policy",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_skips_middle_candidate_with_nonexact_input(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-candidate-input")
        baseline = self.system.inspect_function_promotion("tenant-a", "echo")
        target = baseline.entries[1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            changed = connection.execute(
                "UPDATE artifacts SET input_json = 'null' WHERE id = ?",
                (target.artifact_id,),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 2)
        self.assertNotIn(
            target.artifact_id,
            {entry.artifact_id for entry in manifest.entries},
        )
        self.assertEqual(
            manifest.skipped,
            (
                {
                    "artifact_id": target.artifact_id,
                    "input_hash": target.input_hash,
                    "reason": "superseded-build",
                },
            ),
        )

    def test_function_promotion_candidate_report_binds_each_artifact_field(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-report-bindings")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        with self.system.store.transaction(write=False) as connection:
            report_id = connection.execute(
                "SELECT verified_report_id FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()[0]
        mutations = (
            ("artifact_hash", "0" * 64),
            ("build_hash", "1" * 64),
            ("policy_hash", "2" * 64),
            ("evidence_snapshot_hash", "3" * 64),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                database = pathlib.Path(self.temporary.name) / f"binding-{field}.db"
                shutil.copy2(self.database, database)
                system = System(database)
                connection = sqlite3.connect(database)
                try:
                    connection.execute("DROP TRIGGER test_reports_no_update")
                    changed = connection.execute(
                        f"UPDATE test_reports SET {field} = ? WHERE id = ?",
                        (value, report_id),
                    ).rowcount
                    self.assertEqual(changed, 1)
                    connection.commit()
                finally:
                    connection.close()
                before_connection = sqlite3.connect(database)
                try:
                    before = tuple(before_connection.iterdump())
                finally:
                    before_connection.close()
                with self.assertRaisesRegex(
                    IntegrityError,
                    f"report {field} binding mismatch",
                ):
                    system.inspect_function_promotion("tenant-a", "echo")
                connection = sqlite3.connect(database)
                try:
                    after = tuple(connection.iterdump())
                finally:
                    connection.close()
                self.assertEqual(after, before)

    def test_function_promotion_candidate_requires_present_passing_bound_report(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-report-presence")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        baseline = pathlib.Path(self.temporary.name) / "report-baseline.db"
        shutil.copy2(self.database, baseline)
        mutations = (
            ("missing", "UPDATE artifacts SET verified_report_id = 'missing-report' WHERE id = ?"),
            ("failed", None),
        )
        for label, sql in mutations:
            with self.subTest(condition=label):
                database = pathlib.Path(self.temporary.name) / f"report-{label}.db"
                shutil.copy2(baseline, database)
                system = System(database)
                connection = sqlite3.connect(database)
                try:
                    if sql is not None:
                        changed = connection.execute(
                            sql,
                            (target.artifact_id,),
                        ).rowcount
                    else:
                        report_id = connection.execute(
                            "SELECT verified_report_id FROM artifacts WHERE id = ?",
                            (target.artifact_id,),
                        ).fetchone()[0]
                        connection.execute("DROP TRIGGER test_reports_no_update")
                        changed = connection.execute(
                            "UPDATE test_reports SET passed = 0 WHERE id = ?",
                            (report_id,),
                        ).rowcount
                    self.assertEqual(changed, 1)
                    connection.commit()
                finally:
                    connection.close()
                before_connection = sqlite3.connect(database)
                try:
                    before = tuple(before_connection.iterdump())
                finally:
                    before_connection.close()
                with self.assertRaisesRegex(
                    IntegrityError,
                    "has no passing bound report",
                ):
                    system.inspect_function_promotion("tenant-a", "echo")
                after_connection = sqlite3.connect(database)
                try:
                    after = tuple(after_connection.iterdump())
                finally:
                    after_connection.close()
                self.assertEqual(after, before)

    def test_function_promotion_candidate_report_scope_binding_is_explicit(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-report-scope")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        with self.system.store.transaction(write=False) as connection:
            report_id = str(
                connection.execute(
                    "SELECT verified_report_id FROM artifacts WHERE id = ?",
                    (target.artifact_id,),
                ).fetchone()[0]
            )
        original = self.system._validate_report

        def wrong_scope(connection, row, *, verify_test_set=True):
            details = original(
                connection,
                row,
                verify_test_set=verify_test_set,
            )
            if str(row["id"]) != report_id:
                return details
            if type(details.value) is not dict:
                raise AssertionError("report details fixture is not an object")
            changed = dict(details.value)
            changed["scope_hash"] = "0" * 64
            return canonicalize(changed, max_bytes=262_144)

        before = self._database_dump()
        with mock.patch.object(
            self.system,
            "_validate_report",
            side_effect=wrong_scope,
        ):
            with self.assertRaisesRegex(
                IntegrityError,
                f"{target.artifact_id} report scope binding mismatch",
            ):
                self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)


    def test_function_promotion_union_order_interleaves_retained_and_candidates(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        values = tuple(
            sorted(
                range(100, 106),
                key=lambda value: canonicalize({"x": value}).digest,
            )
        )
        retained_values = values[::2]
        candidate_values = values[1::2]
        self.assertEqual(len(retained_values), 3)
        self.assertEqual(len(candidate_values), 3)
        for value in retained_values:
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-interleave-retained-{value}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-interleave-retained-{value}-b",
                reviewer="bob",
            )
        self.assertEqual(len(self.system.compile("tenant-a", "echo").created), 3)
        retained_batch = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(retained_batch.passed)
        retained_manifest = self.system.inspect_function_promotion(
            "tenant-a",
            "echo",
        )
        self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=retained_manifest.function_hash,
            promoted_by="release-manager",
        )
        for value in candidate_values:
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-interleave-candidate-{value}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": value},
                f"function-interleave-candidate-{value}-b",
                reviewer="bob",
            )
        self.assertEqual(len(self.system.compile("tenant-a", "echo").created), 3)
        candidate_batch = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(candidate_batch.passed)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        ordered_hashes = tuple(entry.input_hash for entry in manifest.entries)
        self.assertEqual(ordered_hashes, tuple(sorted(ordered_hashes)))
        self.assertEqual(
            tuple(entry.disposition for entry in manifest.entries),
            (
                "retained",
                "candidate",
                "retained",
                "candidate",
                "retained",
                "candidate",
            ),
        )


    def test_function_promotion_rejects_candidate_retained_input_digest_collision(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-member-collision-base")
        self._challenge_three_function_entries("function-member-collision-new")
        baseline = self.system.inspect_function_promotion("tenant-a", "echo")
        target = baseline.entries[1]
        self.assertIsNotNone(target.replaces_artifact_id)
        collision_input = canonicalize({"synthetic_sha256_collision": True})
        original_transaction = self.system.store.transaction
        original_projection = self.system._project_current_build

        class RowsCursor:
            def __init__(self, rows) -> None:
                self.rows = rows

            def fetchall(self):
                return self.rows

        class ConnectionProxy:
            def __init__(self, connection):
                self.connection = connection

            def execute(self, sql, parameters=()):
                cursor = self.connection.execute(sql, parameters)
                normalized = " ".join(sql.split())
                if (
                    normalized.startswith("SELECT * FROM artifacts")
                    and "status = 'verified'" in normalized
                ):
                    rows = cursor.fetchall()
                    altered = []
                    for row in rows:
                        if str(row["id"]) != target.artifact_id:
                            altered.append(row)
                            continue
                        changed = dict(row)
                        changed["input_json"] = collision_input.text
                        altered.append(changed)
                    return RowsCursor(altered)
                return cursor

            def __getattr__(self, name):
                return getattr(self.connection, name)

        @contextmanager
        def transaction(*, write=False):
            self.assertFalse(write)
            with original_transaction(write=False) as connection:
                yield ConnectionProxy(connection)

        def collision_projection(
            connection,
            operation_row,
            input_hash,
            input_json,
        ):
            projection = original_projection(
                connection,
                operation_row,
                input_hash,
                input_json,
            )
            if input_hash != target.input_hash:
                return projection
            return replace(projection, input_json=collision_input)

        before = self._database_dump()
        with (
            mock.patch.object(
                self.system.store,
                "transaction",
                side_effect=transaction,
            ),
            mock.patch.object(
                self.system,
                "_project_current_build",
                side_effect=collision_projection,
            ),
        ):
            with self.assertRaisesRegex(
                IntegrityError,
                "equal input digest maps to unequal canonical inputs",
            ):
                self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)


    def test_function_promotion_rejects_last_candidate_without_canonical_input(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-missing-input")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[-1]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            changed = connection.execute(
                "UPDATE artifacts SET input_hash = ? WHERE id = ?",
                ("f" * 64, target.artifact_id),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            f"current-revision verified artifact {target.artifact_id} "
            "has no canonical input",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_requires_exact_current_build_projection_type(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-projection-type")
        baseline = self.system.inspect_function_promotion("tenant-a", "echo")
        target = baseline.entries[1]
        with self.system.store.transaction(write=False) as connection:
            row = connection.execute(
                "SELECT input_json, build_hash FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()
        if row is None:
            raise AssertionError("projection type target disappeared")

        class LookalikeProjection:
            input_json = canonicalize(json.loads(str(row["input_json"])))
            build_hash = str(row["build_hash"])

        original = self.system._project_current_build

        def lookalike(connection, operation_row, input_hash, input_json):
            if input_hash == target.input_hash:
                return LookalikeProjection()
            return original(connection, operation_row, input_hash, input_json)

        with mock.patch.object(
            self.system,
            "_project_current_build",
            side_effect=lookalike,
        ):
            manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 2)
        self.assertEqual(
            manifest.skipped,
            (
                {
                    "artifact_id": target.artifact_id,
                    "input_hash": target.input_hash,
                    "reason": "superseded-build",
                },
            ),
        )

    def test_promote_function_plan_identity_binds_operation_revision(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-plan-revision")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        original = self.system._function_promotion_plan
        calls = 0

        def changed_revision(connection, *, partition, operation):
            nonlocal calls
            calls += 1
            plan = original(
                connection,
                partition=partition,
                operation=operation,
            )
            if calls == 2:
                return replace(
                    plan,
                    manifest=replace(
                        plan.manifest,
                        operation_revision=plan.manifest.operation_revision + 1,
                    ),
                )
            return plan

        before = self._database_dump()
        with mock.patch.object(
            self.system,
            "_function_promotion_plan",
            side_effect=changed_revision,
        ):
            with self.assertRaisesRegex(
                StateError,
                "function promotion candidates changed during authorization",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertEqual(calls, 2)
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_plan_identity_binds_candidate_ids_independently(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-plan-candidates")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        original = self.system._function_promotion_plan
        calls = 0

        def changed_candidates(connection, *, partition, operation):
            nonlocal calls
            calls += 1
            plan = original(
                connection,
                partition=partition,
                operation=operation,
            )
            if calls != 2:
                return plan
            target = plan.entries[-1]
            changed = replace(
                target,
                public=replace(target.public, disposition="retained"),
            )
            return replace(plan, entries=(*plan.entries[:-1], changed))

        before = self._database_dump()
        with mock.patch.object(
            self.system,
            "_function_promotion_plan",
            side_effect=changed_candidates,
        ):
            with self.assertRaisesRegex(
                StateError,
                "function promotion candidates changed during authorization",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertEqual(calls, 2)
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_plan_identity_binds_member_ids_independently(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_function_entries("function-plan-members")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        original = self.system._function_promotion_plan
        calls = 0

        def changed_members(connection, *, partition, operation):
            nonlocal calls
            calls += 1
            plan = original(
                connection,
                partition=partition,
                operation=operation,
            )
            if calls == 2:
                return replace(plan, entries=plan.entries[:-1])
            return plan

        before = self._database_dump()
        with mock.patch.object(
            self.system,
            "_function_promotion_plan",
            side_effect=changed_members,
        ):
            with self.assertRaisesRegex(
                StateError,
                "function promotion candidates changed during authorization",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertEqual(calls, 2)
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_rejects_empty_union_before_side_effects(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(manifest.entries, ())
        authority = mock.Mock(return_value=False)
        clock = mock.Mock(side_effect=AssertionError("clock consulted"))
        guarded = System(self.database, authority=authority, clock_us=clock)
        before = self._database_dump()
        with (
            mock.patch.object(
                guarded.store,
                "transaction",
                wraps=guarded.store.transaction,
            ) as transaction,
            mock.patch(
                "cement_runtime.system.uuid.uuid4",
                side_effect=AssertionError("ID allocated"),
            ),
        ):
            with self.assertRaisesRegex(
                StateError,
                "function promotion requires at least one member",
            ):
                guarded.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="blocked-manager",
                )
        self.assertEqual(transaction.call_args_list, [mock.call(write=False)])
        authority.assert_not_called()
        clock.assert_not_called()
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_plan_identity_binds_retired_ids(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-plan-retired-base")
        self._challenge_three_function_entries("function-plan-retired-new")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        predecessor = manifest.entries[1].replaces_artifact_id
        self.assertIsNotNone(predecessor)
        assert predecessor is not None
        trigger_subject = manifest.entries[-1].artifact_id
        mutator = System(self.database)
        calls: list[str] = []
        post_mutation: list[tuple[str, ...]] = []
        locked_hashes: list[str] = []

        def authority(partition, actor, action, subject):
            calls.append(subject)
            if subject == trigger_subject:
                mutator.suspend_artifact(
                    "tenant-a",
                    predecessor,
                    suspended_by="auditor",
                    reason="authorization retirement-plan race",
                )
                locked_hashes.append(
                    mutator.inspect_function_promotion(
                        "tenant-a",
                        "echo",
                    ).function_hash
                )
                post_mutation.append(self._database_dump())
            return True

        guarded = System(self.database, authority=authority, clock_us=self.clock)
        with self.assertRaisesRegex(
            StateError,
            "function promotion candidates changed during authorization",
        ):
            guarded.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=manifest.function_hash,
                promoted_by="release-manager",
            )
        self.assertEqual(calls, [entry.artifact_id for entry in manifest.entries])
        self.assertEqual(locked_hashes, [manifest.function_hash])
        self.assertEqual(len(post_mutation), 1)
        self.assertEqual(self._database_dump(), post_mutation[0])

    def test_promote_function_expected_hash_binds_locked_content(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-locked-content-hash")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        original = self.system._function_promotion_plan
        calls = 0

        def changed_content(connection, *, partition, operation):
            nonlocal calls
            calls += 1
            plan = original(
                connection,
                partition=partition,
                operation=operation,
            )
            if calls != 2:
                return plan
            entries = list(plan.entries)
            target = entries[1]
            entries[1] = replace(
                target,
                function_entry=replace(
                    target.function_entry,
                    report_details_hash="f" * 64,
                ),
            )
            document = build_function(
                partition=partition,
                operation=operation,
                operation_revision=plan.manifest.operation_revision,
                policy_hash=plan.policy_hash,
                entries=(entry.function_entry for entry in entries),
            )
            return replace(
                plan,
                entries=tuple(entries),
                manifest=replace(
                    plan.manifest,
                    document=document,
                    function_hash=document.function_hash,
                ),
            )

        before = self._database_dump()
        with mock.patch.object(
            self.system,
            "_function_promotion_plan",
            side_effect=changed_content,
        ):
            with self.assertRaisesRegex(
                ConflictError,
                "expected_function_hash does not match the locked prospective function",
            ):
                self.system.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="release-manager",
                )
        self.assertEqual(calls, 2)
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_expected_hash_compares_the_full_digest(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-hash-suffix")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        replacement_suffix = (
            "1" * 32 if manifest.function_hash[32:] == "0" * 32 else "0" * 32
        )
        wrong = manifest.function_hash[:32] + replacement_suffix
        self.assertEqual(wrong[:32], manifest.function_hash[:32])
        self.assertNotEqual(wrong, manifest.function_hash)
        before = self._database_dump()
        with self.assertRaisesRegex(
            ConflictError,
            "expected_function_hash does not match the locked prospective function",
        ):
            self.system.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=wrong,
                promoted_by="release-manager",
            )
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_authorizes_every_retained_member(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-retained-authority")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        retained_ids = tuple(entry.artifact_id for entry in manifest.entries)
        self.assertEqual(len(retained_ids), 3)
        self.assertEqual(
            tuple(entry.disposition for entry in manifest.entries),
            ("retained", "retained", "retained"),
        )
        denied = retained_ids[-1]
        calls: list[tuple[str, str, str, str]] = []

        def authority(partition, actor, action, subject):
            calls.append((partition, actor, action, subject))
            return subject != denied

        clock = mock.Mock(side_effect=AssertionError("clock consulted"))
        guarded = System(self.database, authority=authority, clock_us=clock)
        before = self._database_dump()
        with mock.patch.object(
            guarded.store,
            "transaction",
            wraps=guarded.store.transaction,
        ) as transaction:
            with self.assertRaisesRegex(StateError, "not authorized"):
                guarded.promote_function(
                    "tenant-a",
                    "echo",
                    expected_function_hash=manifest.function_hash,
                    promoted_by="blocked-manager",
                )
        self.assertEqual(
            calls,
            [
                ("tenant-a", "blocked-manager", "artifact.promote", artifact_id)
                for artifact_id in retained_ids
            ],
        )
        self.assertEqual(transaction.call_args_list, [mock.call(write=False)])
        clock.assert_not_called()
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_requires_bound_report_ownership_for_middle_candidate(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-report-owner")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        target = manifest.entries[1]
        sibling = manifest.entries[-1]
        report_id = "report_function_foreign_owner"
        self._insert_report_variant(
            target.artifact_id,
            report_id,
            marker="middle-foreign-owner",
            owner_id=sibling.artifact_id,
        )
        with self.system.store.transaction(write=True) as connection:
            changed = connection.execute(
                "UPDATE artifacts SET verified_report_id = ? WHERE id = ?",
                (report_id, target.artifact_id),
            ).rowcount
        self.assertEqual(changed, 1)
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            f"{target.artifact_id} has no passing bound report",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_rejects_middle_semantic_scope_digest_divergence(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._promote_three_as_function("function-semantic-scope")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target = manifest.entries[1]
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()
            if artifact is None:
                raise AssertionError("semantic scope target disappeared")
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (artifact["verified_report_id"],),
            ).fetchone()
            if report is None:
                raise AssertionError("semantic scope report disappeared")
            changed_artifact = build_exact_lookup(
                partition=str(artifact["partition"]),
                operation=str(artifact["operation"]),
                operation_revision=int(artifact["operation_revision"]),
                input_value={"semantic-scope-drift": target.artifact_id},
                output_value=json.loads(str(artifact["output_json"])),
            )
            self.assertNotEqual(changed_artifact.scope_digest, artifact["scope_hash"])
            changed_build_hash = build_digest(
                artifact_digest=changed_artifact.digest,
                policy_digest=str(artifact["policy_hash"]),
                evidence_snapshot_digest=str(artifact["evidence_snapshot_hash"]),
                support=int(artifact["support"]),
                reviewer_count=int(artifact["reviewer_count"]),
                span_seconds=int(artifact["span_seconds"]),
            )
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute("DROP TRIGGER test_reports_no_update")
            changed = connection.execute(
                """
                UPDATE artifacts
                SET input_json = ?, input_hash = ?, artifact_json = ?,
                    artifact_hash = ?, build_hash = ?
                WHERE id = ?
                """,
                (
                    changed_artifact.input.text,
                    changed_artifact.input.digest,
                    changed_artifact.text,
                    changed_artifact.digest,
                    changed_build_hash,
                    target.artifact_id,
                ),
            ).rowcount
            self.assertEqual(changed, 1)
            changed = connection.execute(
                """
                UPDATE test_reports SET artifact_hash = ?, build_hash = ?
                WHERE id = ?
                """,
                (
                    changed_artifact.digest,
                    changed_build_hash,
                    report["id"],
                ),
            ).rowcount
            self.assertEqual(changed, 1)
            changed_row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?",
                (target.artifact_id,),
            ).fetchone()
            changed_report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ?",
                (report["id"],),
            ).fetchone()
            if changed_row is None or changed_report is None:
                raise AssertionError("semantic scope mutation disappeared")
            promotion_hash = self._promotion_hash(changed_row, changed_report)
            changed = connection.execute(
                "UPDATE artifacts SET promotion_hash = ? WHERE id = ?",
                (promotion_hash, target.artifact_id),
            ).rowcount
            self.assertEqual(changed, 1)
            connection.commit()
        finally:
            connection.close()
        before = self._database_dump()
        with self.assertRaisesRegex(
            IntegrityError,
            "artifact semantic digest mismatch",
        ):
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_enumerates_retained_page_tail(self) -> None:
        rows, reports, _, function_entries, expected = (
            self._function_promotion_page_fixture(promoted=True)
        )
        expected_ids = tuple(str(row["id"]) for row in rows)
        sentinel = expected_ids[-1]

        def fast_entry(connection, row, *, promoted):
            self.assertTrue(promoted)
            return (
                reports[str(row["verified_report_id"])],
                function_entries[str(row["id"])],
            )

        with mock.patch.object(
            self.system,
            "_function_promotion_entry",
            side_effect=fast_entry,
        ):
            manifest = self.system.inspect_function_promotion("tenant-a", "echo")
            self.assertEqual(len(manifest.entries), 1_001)
            self.assertEqual(
                tuple(entry.artifact_id for entry in manifest.entries),
                expected_ids,
            )
            self.assertEqual(manifest.entries[-1].artifact_id, sentinel)
            self.assertEqual(manifest.document, expected)
            self.assertEqual(manifest.function_hash, expected.function_hash)
            promotion = self.system.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=manifest.function_hash,
                promoted_by="page-manager",
            )
        self.assertEqual(len(promotion.member_artifact_ids), 1_001)
        self.assertEqual(promotion.candidate_artifact_ids, ())
        self.assertIn(sentinel, promotion.member_artifact_ids)
        with self.system.store.transaction(write=False) as connection:
            receipt = connection.execute(
                "SELECT * FROM function_receipts WHERE id = ?",
                (promotion.receipt_id,),
            ).fetchone()
            memberships = tuple(
                connection.execute(
                    """
                    SELECT artifact_id FROM function_memberships
                    WHERE receipt_id = ? ORDER BY ordinal
                    """,
                    (promotion.receipt_id,),
                )
            )
        if receipt is None:
            raise AssertionError("retained page-tail receipt disappeared")
        self.assertEqual(receipt["member_count"], 1_001)
        self.assertEqual(
            tuple(str(row["artifact_id"]) for row in memberships),
            expected_ids,
        )
        self.assertEqual(str(memberships[-1]["artifact_id"]), sentinel)

    def test_function_promotion_enumerates_candidate_page_tail(self) -> None:
        rows, reports, projections, function_entries, expected = (
            self._function_promotion_page_fixture(promoted=False)
        )
        expected_ids = tuple(str(row["id"]) for row in rows)
        sentinel = expected_ids[-1]

        def projected(connection, operation_row, input_hash, input_json):
            return projections[input_hash]

        def fast_entry(connection, row, *, promoted):
            self.assertFalse(promoted)
            return (
                reports[str(row["verified_report_id"])],
                function_entries[str(row["id"])],
            )

        with (
            mock.patch.object(
                self.system,
                "_project_current_build",
                side_effect=projected,
            ),
            mock.patch.object(
                self.system,
                "_function_promotion_entry",
                side_effect=fast_entry,
            ),
        ):
            manifest = self.system.inspect_function_promotion("tenant-a", "echo")
            self.assertEqual(len(manifest.entries), 1_001)
            self.assertEqual(
                tuple(entry.artifact_id for entry in manifest.entries),
                expected_ids,
            )
            self.assertTrue(
                all(entry.disposition == "candidate" for entry in manifest.entries)
            )
            self.assertEqual(manifest.entries[-1].artifact_id, sentinel)
            self.assertEqual(manifest.document, expected)
            self.assertEqual(manifest.function_hash, expected.function_hash)
            promotion = self.system.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=manifest.function_hash,
                promoted_by="page-manager",
            )
        self.assertEqual(len(promotion.member_artifact_ids), 1_001)
        self.assertEqual(len(promotion.candidate_artifact_ids), 1_001)
        self.assertIn(sentinel, promotion.candidate_artifact_ids)
        with self.system.store.transaction(write=False) as connection:
            receipt = connection.execute(
                "SELECT * FROM function_receipts WHERE id = ?",
                (promotion.receipt_id,),
            ).fetchone()
            memberships = tuple(
                connection.execute(
                    """
                    SELECT artifact_id FROM function_memberships
                    WHERE receipt_id = ? ORDER BY ordinal
                    """,
                    (promotion.receipt_id,),
                )
            )
            promoted_count = connection.execute(
                """
                SELECT COUNT(*) FROM artifacts
                WHERE partition = 'tenant-a' AND operation = 'echo'
                  AND operation_revision = 1 AND status = 'promoted'
                """
            ).fetchone()[0]
        if receipt is None:
            raise AssertionError("candidate page-tail receipt disappeared")
        self.assertEqual(receipt["member_count"], 1_001)
        self.assertEqual(receipt["candidate_count"], 1_001)
        self.assertEqual(promoted_count, 1_001)
        self.assertEqual(
            tuple(str(row["artifact_id"]) for row in memberships),
            expected_ids,
        )
        self.assertEqual(str(memberships[-1]["artifact_id"]), sentinel)

    def test_function_promotion_retained_scope_is_partition_and_operation_exact(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        target_ids = self._promote_three_function_entries("function-retained-scope")
        self.system.register_operation(
            "tenant-b",
            "echo",
            policy=CompilePolicy(2, 1, 0),
        )
        foreign_partition, _, _ = self._promote_scope(
            "tenant-b",
            "echo",
            {"x": "foreign-partition"},
            "function-retained-foreign-partition",
        )
        self.system.register_operation(
            "tenant-a",
            "other",
            policy=CompilePolicy(2, 1, 0),
        )
        foreign_operation, _, _ = self._promote_scope(
            "tenant-a",
            "other",
            {"x": "foreign-operation"},
            "function-retained-foreign-operation",
        )
        decoy_ids = tuple(sorted((foreign_partition, foreign_operation)))
        with self.system.store.transaction(write=False) as connection:
            decoys_before = tuple(
                tuple(row)
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE id IN (?, ?) ORDER BY id",
                    decoy_ids,
                )
            )
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(
            {entry.artifact_id for entry in manifest.entries},
            set(target_ids),
        )
        self.assertEqual(
            tuple(entry.disposition for entry in manifest.entries),
            ("retained", "retained", "retained"),
        )
        calls: list[str] = []

        def authority(partition, actor, action, subject):
            calls.append(subject)
            return True

        guarded = System(self.database, authority=authority, clock_us=self.clock)
        promotion = guarded.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="scope-manager",
        )
        expected_authority = [entry.artifact_id for entry in manifest.entries]
        self.assertEqual(calls, expected_authority)
        self.assertEqual(set(promotion.member_artifact_ids), set(target_ids))
        self.assertEqual(promotion.candidate_artifact_ids, ())
        self.assertEqual(promotion.retired_artifact_ids, ())
        with self.system.store.transaction(write=False) as connection:
            memberships = tuple(
                str(row["artifact_id"])
                for row in connection.execute(
                    """
                    SELECT artifact_id FROM function_memberships
                    WHERE receipt_id = ? ORDER BY ordinal
                    """,
                    (promotion.receipt_id,),
                )
            )
            decoys_after = tuple(
                tuple(row)
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE id IN (?, ?) ORDER BY id",
                    decoy_ids,
                )
            )
        self.assertEqual(set(memberships), set(target_ids))
        self.assertEqual(decoys_after, decoys_before)

    def test_function_promotion_candidate_scope_is_partition_operation_revision_exact(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        target = self._verify_three_function_candidates("function-candidate-scope")

        def verified_scope(partition, operation, value, prefix):
            self._confirm_scope(
                partition,
                operation,
                value,
                f"{prefix}-a",
                reviewer="alice",
            )
            self._confirm_scope(
                partition,
                operation,
                value,
                f"{prefix}-b",
                reviewer="bob",
            )
            compiled = self.system.compile(partition, operation)
            self.assertEqual(len(compiled.created), 1)
            report = self.system.verify(partition, compiled.created[0])
            self.assertTrue(report.passed)
            return compiled.created[0]

        self.system.register_operation(
            "tenant-b",
            "echo",
            policy=CompilePolicy(2, 1, 0),
        )
        foreign_partition = verified_scope(
            "tenant-b",
            "echo",
            {"x": "foreign-partition"},
            "function-candidate-foreign-partition",
        )
        self.system.register_operation(
            "tenant-a",
            "other",
            policy=CompilePolicy(2, 1, 0),
        )
        foreign_operation = verified_scope(
            "tenant-a",
            "other",
            {"x": "foreign-operation"},
            "function-candidate-foreign-operation",
        )
        foreign_revision = "artifact_function_foreign_revision"
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                """
                INSERT INTO artifacts(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                    status_reason
                )
                SELECT ?, 'tenant-a', 'echo', 2, input_json, input_hash,
                    output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                    build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                    support, reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                    status_reason
                FROM artifacts WHERE id = ?
                """,
                (foreign_revision, foreign_operation),
            )
            connection.commit()
        finally:
            connection.close()
        decoy_ids = tuple(
            sorted((foreign_partition, foreign_operation, foreign_revision))
        )
        with self.system.store.transaction(write=False) as connection:
            decoys_before = tuple(
                tuple(row)
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE id IN (?, ?, ?) ORDER BY id",
                    decoy_ids,
                )
            )
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        target_ids = {entry.artifact_id for entry in target.entries}
        self.assertEqual(
            {entry.artifact_id for entry in manifest.entries},
            target_ids,
        )
        self.assertEqual(manifest.skipped, ())
        calls: list[str] = []

        def authority(partition, actor, action, subject):
            calls.append(subject)
            return True

        guarded = System(self.database, authority=authority, clock_us=self.clock)
        promotion = guarded.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="scope-manager",
        )
        self.assertEqual(calls, [entry.artifact_id for entry in manifest.entries])
        self.assertEqual(set(promotion.member_artifact_ids), target_ids)
        self.assertEqual(set(promotion.candidate_artifact_ids), target_ids)
        self.assertEqual(promotion.retired_artifact_ids, ())
        with self.system.store.transaction(write=False) as connection:
            memberships = tuple(
                str(row["artifact_id"])
                for row in connection.execute(
                    """
                    SELECT artifact_id FROM function_memberships
                    WHERE receipt_id = ? ORDER BY ordinal
                    """,
                    (promotion.receipt_id,),
                )
            )
            decoys_after = tuple(
                tuple(row)
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE id IN (?, ?, ?) ORDER BY id",
                    decoy_ids,
                )
            )
        self.assertEqual(set(memberships), target_ids)
        self.assertEqual(decoys_after, decoys_before)


    def _prepare_function_manifest_limit_fixture(
        self,
        prefix: str,
        *,
        skipped_count: int = 128,
    ) -> FunctionPromotionManifest:
        self.register(confirmations=2, reviewers=1, span=0)
        value = {"x": prefix}
        self._confirm_scope(
            "tenant-a",
            "echo",
            value,
            f"{prefix}-old-a",
            reviewer="alice",
        )
        self._confirm_scope(
            "tenant-a",
            "echo",
            value,
            f"{prefix}-old-b",
            reviewer="bob",
        )
        old = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(old.created), 1)
        old_id = old.created[0]
        self.assertTrue(self.system.verify("tenant-a", old_id).passed)
        with self.system.store.transaction(write=True) as connection:
            connection.executemany(
                """
                INSERT INTO artifacts(
                    id, partition, operation, operation_revision, input_json,
                    input_hash, output_json, output_hash, artifact_json,
                    artifact_hash, scope_hash, build_hash, policy_json,
                    policy_hash, evidence_snapshot_hash, status, support,
                    reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us,
                    promotion_hash, status_reason
                )
                SELECT ?, partition, operation, operation_revision, input_json,
                    input_hash, output_json, output_hash, artifact_json,
                    artifact_hash, scope_hash, build_hash, policy_json,
                    policy_hash, evidence_snapshot_hash, status, support,
                    reviewer_count, span_seconds, created_at_us,
                    verified_report_id, promoted_by, promoted_at_us,
                    promotion_hash, status_reason
                FROM artifacts WHERE id = ?
                """,
                (
                    (f"artifact_manifest_limit_{index:04d}", old_id)
                    for index in range(skipped_count - 1)
                ),
            )
        self._confirm_scope(
            "tenant-a",
            "echo",
            value,
            f"{prefix}-current",
            reviewer="carol",
        )
        current = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(current.created), 1)
        verified = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(verified.passed)
        self.assertEqual(len(verified.entries), 1)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 1)
        self.assertEqual(len(manifest.skipped), skipped_count)
        return manifest

    def test_promote_function_event_binds_distinct_transition_sets(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, initial = self._promote_three_as_function("function-event-mixed-base")
        for value in (1, 2):
            _, suspended = self.system.challenge(
                "tenant-a",
                "echo",
                {"x": value},
                {"echo": {"x": value}},
                reviewer="alice",
                note=f"function-event-mixed-replacement-{value}",
            )
            self.assertFalse(suspended)
        for reviewer in ("alice", "bob"):
            self._confirm_scope(
                "tenant-a",
                "echo",
                {"x": 4},
                f"function-event-mixed-growth-{reviewer}",
                reviewer=reviewer,
            )
        compiled = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(compiled.created), 3)
        replacements = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(replacements.passed)
        self.assertEqual(len(replacements.entries), 3)
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        member_ids = tuple(sorted(entry.artifact_id for entry in manifest.entries))
        candidate_ids = tuple(
            sorted(
                entry.artifact_id
                for entry in manifest.entries
                if entry.disposition == "candidate"
            )
        )
        retired_ids = tuple(
            sorted(
                {
                    entry.replaces_artifact_id
                    for entry in manifest.entries
                    if entry.replaces_artifact_id is not None
                }
            )
        )
        self.assertEqual(len(member_ids), 4)
        self.assertEqual(len(candidate_ids), 3)
        self.assertEqual(len(retired_ids), 2)
        self.assertEqual(
            len(
                {
                    frozenset(member_ids),
                    frozenset(candidate_ids),
                    frozenset(retired_ids),
                }
            ),
            3,
        )
        self.assertEqual(
            set(retired_ids),
            set(initial.member_artifact_ids) - set(member_ids),
        )
        promotion = self.system.promote_function(
            "tenant-a",
            "echo",
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        self.assertEqual(promotion.member_artifact_ids, member_ids)
        self.assertEqual(promotion.candidate_artifact_ids, candidate_ids)
        self.assertEqual(promotion.retired_artifact_ids, retired_ids)
        with self.system.store.transaction(write=False) as connection:
            event = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE kind = 'function.promoted' AND subject_id = ?
                """,
                (promotion.receipt_id,),
            ).fetchone()
        if event is None:
            raise AssertionError("mixed-set function event disappeared")
        payload_text = str(event["payload_json"])
        payload = json.loads(payload_text)
        self.assertLessEqual(len(payload_text.encode("utf-8")), 262_144)
        for name, expected in (
            ("member", member_ids),
            ("candidate", candidate_ids),
            ("retired", retired_ids),
        ):
            with self.subTest(projection=name):
                self.assertEqual(payload[f"{name}_artifact_count"], len(expected))
                self.assertEqual(
                    payload[f"{name}_artifact_ids"],
                    list(expected[:100]),
                )
                self.assertEqual(
                    payload[f"{name}_artifact_ids_hash"],
                    _digest_strings("cement-id-list-v1", expected),
                )

    def test_function_promotion_orders_skipped_rows_under_reverse_scans(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        values = ({"x": "order-a"}, {"x": "order-b"}, {"x": "order-c"})
        reverse_input_order = sorted(
            ((canonicalize(value).digest, value) for value in values),
            key=lambda item: item[0],
            reverse=True,
        )
        old_by_hash: dict[str, str] = {}
        for index, (input_hash, value) in enumerate(reverse_input_order):
            for reviewer in ("alice", "bob"):
                self._confirm_scope(
                    "tenant-a",
                    "echo",
                    value,
                    f"function-skipped-order-old-{index}-{reviewer}",
                    reviewer=reviewer,
                )
            compiled = self.system.compile("tenant-a", "echo")
            self.assertEqual(len(compiled.created), 1)
            artifact_id = compiled.created[0]
            self.assertTrue(self.system.verify("tenant-a", artifact_id).passed)
            old_by_hash[input_hash] = artifact_id
        old_ids = tuple(old_by_hash.values())
        with self.system.store.transaction(write=False) as connection:
            inserted_input_order = tuple(
                str(row["input_hash"])
                for row in connection.execute(
                    """
                    SELECT input_hash FROM artifacts
                    WHERE id IN (?, ?, ?) ORDER BY sequence
                    """,
                    old_ids,
                )
            )
        self.assertEqual(
            inserted_input_order,
            tuple(input_hash for input_hash, _ in reverse_input_order),
        )
        for index, (_, value) in enumerate(reverse_input_order):
            self._confirm_scope(
                "tenant-a",
                "echo",
                value,
                f"function-skipped-order-current-{index}",
                reviewer="carol",
            )
        current = self.system.compile("tenant-a", "echo")
        self.assertEqual(len(current.created), 3)
        verified = self.system.verify_drafts(
            "tenant-a",
            "echo",
            verified_by="batch-verifier",
        )
        self.assertTrue(verified.passed)
        self.assertEqual(len(verified.entries), 3)
        expected_skipped = tuple(
            {
                "artifact_id": old_by_hash[input_hash],
                "input_hash": input_hash,
                "reason": "superseded-build",
            }
            for input_hash in sorted(old_by_hash)
        )
        first_reader = System(self.database)
        second_reader = System(self.database)
        first_original = first_reader.store.transaction
        second_original = second_reader.store.transaction

        @contextmanager
        def first_transaction(*, write=False):
            with first_original(write=write) as connection:
                connection.execute("PRAGMA reverse_unordered_selects = ON")
                yield connection

        @contextmanager
        def second_transaction(*, write=False):
            with second_original(write=write) as connection:
                connection.execute("PRAGMA reverse_unordered_selects = ON")
                yield connection

        before = self._database_dump()
        with (
            mock.patch.object(
                first_reader.store,
                "transaction",
                side_effect=first_transaction,
            ),
            mock.patch.object(
                second_reader.store,
                "transaction",
                side_effect=second_transaction,
            ),
        ):
            first_manifest = first_reader.inspect_function_promotion(
                "tenant-a",
                "echo",
            )
            second_manifest = second_reader.inspect_function_promotion(
                "tenant-a",
                "echo",
            )
        self.assertEqual(first_manifest.skipped, expected_skipped)
        self.assertEqual(second_manifest.skipped, expected_skipped)
        self.assertEqual(first_manifest.text, second_manifest.text)
        self.assertEqual(self._database_dump(), before)

    def test_promote_function_retires_all_before_any_candidate_activation(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        _, initial = self._promote_three_as_function("function-retire-order-base")
        self._challenge_three_function_entries("function-retire-order-current")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        predecessor_ids = tuple(
            sorted(
                entry.replaces_artifact_id
                for entry in manifest.entries
                if entry.replaces_artifact_id is not None
            )
        )
        self.assertEqual(len(predecessor_ids), 3)
        self.assertEqual(set(predecessor_ids), set(initial.member_artifact_ids))
        original_transaction = self.system.store.transaction
        trigger_installed = False

        @contextmanager
        def guarded_transaction(*, write=False):
            nonlocal trigger_installed
            with original_transaction(write=write) as connection:
                if write:
                    connection.execute(
                        """
                        CREATE TEMP TABLE planned_function_predecessors(
                            id TEXT PRIMARY KEY
                        ) STRICT
                        """
                    )
                    connection.executemany(
                        "INSERT INTO planned_function_predecessors(id) VALUES (?)",
                        ((artifact_id,) for artifact_id in predecessor_ids),
                    )
                    connection.execute(
                        """
                        CREATE TEMP TRIGGER function_retire_all_before_activate_any
                        BEFORE UPDATE OF status ON artifacts
                        WHEN OLD.status = 'verified' AND NEW.status = 'promoted'
                          AND EXISTS (
                              SELECT 1
                              FROM artifacts AS predecessor
                              JOIN planned_function_predecessors AS planned
                                ON planned.id = predecessor.id
                              WHERE predecessor.status = 'promoted'
                          )
                        BEGIN
                            SELECT RAISE(ABORT, 'planned predecessor remains promoted');
                        END
                        """
                    )
                    trigger_installed = True
                yield connection

        with mock.patch.object(
            self.system.store,
            "transaction",
            side_effect=guarded_transaction,
        ):
            promotion = self.system.promote_function(
                "tenant-a",
                "echo",
                expected_function_hash=manifest.function_hash,
                promoted_by="release-manager",
            )
        self.assertTrue(trigger_installed)
        self.assertEqual(promotion.retired_artifact_ids, predecessor_ids)

    def test_function_promotion_manifest_byte_cap_is_exactly_twice_function_cap(self) -> None:
        manifest = self._prepare_function_manifest_limit_fixture(
            "function-manifest-byte-bound"
        )
        function_bytes = len(manifest.document.text.encode("utf-8"))
        manifest_bytes = len(manifest.text.encode("utf-8"))
        accepted_function_cap = manifest_bytes // 2 + 1
        rejected_function_cap = (manifest_bytes - 1) // 2
        self.assertLessEqual(function_bytes, rejected_function_cap)
        self.assertGreater(2 * accepted_function_cap, manifest_bytes)
        self.assertLessEqual(2 * accepted_function_cap - manifest_bytes, 2)
        self.assertGreater(manifest_bytes, 2 * rejected_function_cap)
        self.assertLessEqual(manifest_bytes - 2 * rejected_function_cap, 2)
        self.assertEqual(
            system_module._FUNCTION_MANIFEST_MAX_BYTES,
            2 * system_module.FUNCTION_MAX_BYTES,
        )
        first_reader = System(self.database)
        second_reader = System(self.database)
        before = self._database_dump()
        with (
            mock.patch.object(
                function_module,
                "FUNCTION_MAX_BYTES",
                accepted_function_cap,
            ),
            mock.patch.object(
                system_module,
                "_FUNCTION_MANIFEST_MAX_BYTES",
                2 * accepted_function_cap,
            ),
        ):
            accepted = tuple(
                reader.inspect_function_promotion("tenant-a", "echo")
                for reader in (first_reader, second_reader)
            )
        self.assertEqual(tuple(item.text for item in accepted), (manifest.text,) * 2)
        self.assertEqual(self._database_dump(), before)
        messages: list[str] = []
        with (
            mock.patch.object(
                function_module,
                "FUNCTION_MAX_BYTES",
                rejected_function_cap,
            ),
            mock.patch.object(
                system_module,
                "_FUNCTION_MANIFEST_MAX_BYTES",
                2 * rejected_function_cap,
            ),
        ):
            for reader in (first_reader, second_reader):
                with self.assertRaises(ValidationError) as raised:
                    reader.inspect_function_promotion("tenant-a", "echo")
                messages.append(str(raised.exception))
        self.assertEqual(
            messages,
            [
                f"canonical JSON exceeds {2 * rejected_function_cap} bytes",
                f"canonical JSON exceeds {2 * rejected_function_cap} bytes",
            ],
        )
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_manifest_item_cap_is_exactly_twice_function_cap(self) -> None:
        manifest = self._prepare_function_manifest_limit_fixture(
            "function-manifest-item-bound"
        )

        def container_items(value) -> int:
            if type(value) is list:
                return len(value) + sum(container_items(item) for item in value)
            if type(value) is dict:
                return len(value) + sum(
                    container_items(item) for item in value.values()
                )
            return 0

        function_items = container_items(manifest.document.value)
        manifest_items = container_items(json.loads(manifest.text))
        accepted_function_cap = manifest_items // 2 + 1
        rejected_function_cap = (manifest_items - 1) // 2
        self.assertLessEqual(function_items, rejected_function_cap)
        self.assertGreater(2 * accepted_function_cap, manifest_items)
        self.assertLessEqual(2 * accepted_function_cap - manifest_items, 2)
        self.assertGreater(manifest_items, 2 * rejected_function_cap)
        self.assertLessEqual(manifest_items - 2 * rejected_function_cap, 2)
        self.assertEqual(
            system_module._FUNCTION_MANIFEST_MAX_ITEMS,
            2 * system_module.FUNCTION_MAX_ITEMS,
        )
        first_reader = System(self.database)
        second_reader = System(self.database)
        before = self._database_dump()
        with (
            mock.patch.object(
                function_module,
                "FUNCTION_MAX_ITEMS",
                accepted_function_cap,
            ),
            mock.patch.object(
                system_module,
                "_FUNCTION_MANIFEST_MAX_ITEMS",
                2 * accepted_function_cap,
            ),
        ):
            accepted = tuple(
                reader.inspect_function_promotion("tenant-a", "echo")
                for reader in (first_reader, second_reader)
            )
        self.assertEqual(tuple(item.text for item in accepted), (manifest.text,) * 2)
        self.assertEqual(self._database_dump(), before)
        messages: list[str] = []
        with (
            mock.patch.object(
                function_module,
                "FUNCTION_MAX_ITEMS",
                rejected_function_cap,
            ),
            mock.patch.object(
                system_module,
                "_FUNCTION_MANIFEST_MAX_ITEMS",
                2 * rejected_function_cap,
            ),
        ):
            for reader in (first_reader, second_reader):
                with self.assertRaises(ValidationError) as raised:
                    reader.inspect_function_promotion("tenant-a", "echo")
                messages.append(str(raised.exception))
        self.assertEqual(
            messages,
            [
                "JSON exceeds maximum container item count",
                "JSON exceeds maximum container item count",
            ],
        )
        self.assertEqual(self._database_dump(), before)

    def test_function_promotion_requires_active_canonical_input_for_middle_candidate(self) -> None:
        self.register(confirmations=2, reviewers=1, span=0)
        self._verify_three_function_candidates("function-active-canonical-input")
        manifest = self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(len(manifest.entries), 3)
        target = manifest.entries[1].artifact_id
        with self.system.store.transaction(write=False) as connection:
            evidence_ids = tuple(
                str(row["example_id"])
                for row in connection.execute(
                    """
                    SELECT example_id FROM artifact_evidence
                    WHERE artifact_id = ? ORDER BY example_id
                    """,
                    (target,),
                )
            )
        self.assertGreaterEqual(len(evidence_ids), 2)
        for evidence_id in evidence_ids:
            self.system.revoke_example(
                "tenant-a",
                evidence_id,
                revoked_by="auditor",
                reason="remove every canonical input witness",
            )
        with self.system.store.transaction(write=True) as connection:
            connection.execute("DROP TRIGGER artifacts_status_lifecycle")
            changed = connection.execute(
                "UPDATE artifacts SET status = 'verified' WHERE id = ?",
                (target,),
            ).rowcount
        self.assertEqual(changed, 1)
        before = self._database_dump()
        with self.assertRaises(IntegrityError) as raised:
            self.system.inspect_function_promotion("tenant-a", "echo")
        self.assertEqual(
            str(raised.exception),
            f"current-revision verified artifact {target} has no canonical input",
        )
        self.assertEqual(self._database_dump(), before)


if __name__ == "__main__":
    unittest.main()
