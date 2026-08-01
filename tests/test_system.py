from __future__ import annotations

import json
import pathlib
import sqlite3
import tempfile
import threading
import unittest
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from unittest import mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    ConflictError,
    FallbackFailed,
    FunctionCheck,
    FunctionEntry,
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
    build_function,
    evaluate,
)
from cement_runtime.artifacts import ARTIFACT_ABI, ARTIFACT_MAX_BYTES, build_digest
from cement_runtime.json_value import CANONICALIZER, canonicalize
from cement_runtime.system import _digest_strings


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
        with self.assertRaises(IntegrityError):
            System(str(corrupt))

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
        self.assertNotIn("CREATE TABLE function", "\n".join(after))
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
        self.assertNotEqual(result.function_hash, baseline.function_hash)
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
                promotion_hash=entry.promotion_hash,
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
                        promotion_hash=str(row["promotion_hash"]),
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


if __name__ == "__main__":
    unittest.main()
