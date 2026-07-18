from __future__ import annotations

import pathlib
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    ConflictError,
    FallbackFailed,
    InProgress,
    IntegrityError,
    NotFoundError,
    ReconciliationRequired,
    ReviewRequired,
    StateError,
    System,
    ValidationError,
)
from cement_runtime.artifacts import build_digest


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

    def confirm(self, request_id: str, *, reviewer="alice", corrected=None):
        outcome = self.system.handle(
            "tenant-a", "echo", {"x": 1}, request_id=request_id
        )
        self.assertIsInstance(outcome, ReviewRequired)
        proposal = self.system.get_proposal("tenant-a", outcome.proposal_id)
        self.assertEqual(proposal.proposed_output, {"echo": {"x": 1}})
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


if __name__ == "__main__":
    unittest.main()
