import argparse
import contextlib
import dataclasses
import errno
import inspect
import io
import json
import os
import pathlib
import socket
import stat
import sqlite3
import sys
import tempfile
import types
import typing
import unittest
from dataclasses import dataclass
from unittest import mock

from cement_runtime import System
from cement_runtime import cli as cement_cli
from cement_runtime.cli import main
from cement_runtime.errors import IntegrityError, NotFoundError, StateError, ValidationError
from cement_runtime.function import FUNCTION_MAX_BYTES, FunctionMatch
from cement_runtime.json_value import DEFAULT_MAX_BYTES, canonicalize
from cement_runtime.models import (
    DraftVerification,
    FunctionCheck,
    FunctionVerification,
    VerificationReport,
)

_REPORT_KEYS = {"function_anchor", "operation", "operation_now", "partition"}
_OPERATION_NOW_KEYS = {
    "artifact_statuses",
    "compile_blocked_scope_count",
    "compile_blocked_scopes",
    "compile_ready_scope_count",
    "compile_ready_scopes",
    "operation_revision",
    "pending_proposal_count",
    "pending_proposals",
    "policy_hash",
    "projection_limit",
    "promoted_entry_count",
    "stale_revision_anomalies",
    "stale_revision_anomaly_count",
}
_ANCHOR_KEYS = {"member_count", "members", "receipt"}
_MEMBER_KEYS = {
    "artifact_id",
    "build_reviewer_count",
    "build_support",
    "input_hash",
    "ordinal",
}
_RECEIPT_KEYS = {
    "candidate_artifact_ids_hash",
    "candidate_count",
    "function_hash",
    "id",
    "member_count",
    "membership_hash",
    "operation",
    "operation_revision",
    "partition",
    "policy_hash",
    "promoted_at_us",
    "promoted_by",
    "receipt_hash",
    "retired_artifact_ids_hash",
    "retired_count",
    "sequence",
}
_ARTIFACT_STATUS_ORDER = ("draft", "verified", "promoted", "suspended", "retired")
_SCOPE_KEYS = {
    "active_reviewer_count",
    "active_span_seconds",
    "active_support",
    "input_hash",
    "reasons",
}
_PENDING_KEYS = {"input_hash", "operation_revision", "proposal_id"}
_ARTIFACT_STATUS_KEYS = {"artifacts", "count", "status"}
_ARTIFACT_KEYS = {
    "artifact_id",
    "input_hash",
    "operation_revision",
    "sequence",
    "status_reason",
}
_ANOMALY_KEYS = {
    "artifact_id",
    "artifact_revision",
    "current_revision",
    "reason",
    "status",
}
_FUNCTION_VERIFY_KEYS = {"checks", "entries", "function_hash", "passed"}
_FUNCTION_CHECK_KEYS = (
    "duplicate-input-digests",
    "abi-canonicalizer-uniform",
    "sealed-passing-reports",
    "current-promotion-receipts",
    "function-hash-matches-snapshot",
    "persisted-function-receipt",
)
_INSPECT_KEYS = {"entries", "function_hash", "operation_revision", "skipped"}
_PROMOTION_ENTRY_KEYS = {
    "artifact_hash",
    "artifact_id",
    "disposition",
    "entry_seal",
    "input_hash",
    "output_hash",
    "replaces_artifact_id",
}
_PROMOTION_KEYS = {
    "candidate_artifact_ids",
    "function_hash",
    "member_artifact_ids",
    "operation_revision",
    "promoted_at_us",
    "receipt_hash",
    "receipt_id",
    "retired_artifact_ids",
}
_SKIPPED_KEYS = {"artifact_id", "input_hash", "reason"}


@dataclass(frozen=True, slots=True)
class _CLIRun:
    status: int
    stdout_text: str
    stdout_bytes: bytes
    stdout_json: object | None
    stderr_text: str
    stderr_json: object | None


class _BinaryOutput:
    # Stdout capture carrying both the text channel and the raw `.buffer` one.
    def __init__(self) -> None:
        self.buffer = io.BytesIO()

    def write(self, value: str) -> int:
        return self.buffer.write(value.encode("utf-8"))

    def flush(self) -> None:
        pass


def _decoded(text: str) -> object | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(self.temporary.cleanup)
        self.database = str(pathlib.Path(self.temporary.name) / "cli.db")
        self.base = ["--db", self.database, "--partition", "tenant"]

    def run_cli(self, *arguments: str, text_only: bool = False) -> _CLIRun:
        stdout: io.StringIO | _BinaryOutput = (
            io.StringIO() if text_only else _BinaryOutput()
        )
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main([*self.base, *arguments])
        if isinstance(stdout, io.StringIO):
            stdout_bytes = stdout.getvalue().encode("utf-8")
        else:
            stdout_bytes = stdout.buffer.getvalue()
        stdout_text = stdout_bytes.decode("utf-8")
        stderr_text = stderr.getvalue()
        return _CLIRun(
            status=status,
            stdout_text=stdout_text,
            stdout_bytes=stdout_bytes,
            stdout_json=_decoded(stdout_text),
            stderr_text=stderr_text,
            stderr_json=_decoded(stderr_text),
        )

    def payload(self, run: _CLIRun) -> dict[str, typing.Any]:
        self.assertEqual(run.status, 0)
        self.assertIsInstance(run.stdout_json, dict)
        return typing.cast(dict[str, typing.Any], run.stdout_json)

    def error(self, run: _CLIRun) -> dict[str, typing.Any]:
        self.assertIsInstance(run.stderr_json, dict)
        return typing.cast(dict[str, typing.Any], run.stderr_json)

    def register(self, operation: str, *, partition: str = "tenant") -> None:
        run = self.run_cli(
            "--partition",
            partition,
            "operation",
            "register",
            operation,
            "--min-confirmations",
            "2",
            "--min-reviewers",
            "1",
            "--min-span-seconds",
            "0",
        )
        self.assertEqual(run.status, 0)

    def submission(self, value: object) -> str:
        # M3.5b removed the `handle` CLI route, so every fixture seeds through
        # `proposal submit`. This envelope mirrors `examples/echo_adapter.py`
        # exactly - same output shape, same provenance - so the proposal content
        # the consuming assertions read is identical to the content the adapter
        # used to produce.
        return json.dumps(
            {
                "input": value,
                "output": {"kind": "echo", "value": value},
                "provenance": {"adapter": "example-stub", "model": None},
            }
        )

    def submit(self, operation: str, value: object) -> str:
        submitted = self.payload(
            self.run_cli(
                "proposal",
                "submit",
                operation,
                "--submission",
                self.submission(value),
            )
        )
        # `handle` answered `review_required`; `submit` acknowledges the id alone.
        # Pinning the key set here keeps the "seeded proposal is pending" property
        # the removed status assertion carried.
        self.assertEqual(set(submitted), {"proposal_id"})
        return str(submitted["proposal_id"])

    def confirm(self, operation: str, value: int, tag: str) -> None:
        # `tag` was the `handle` request identity. Submission has no idempotency
        # key, and two byte-identical submissions yield two proposals, so the
        # parameter survives for its 100+ call sites and steers nothing.
        del tag
        for _ in (1, 2):
            reviewed = self.payload(
                self.run_cli(
                    "proposal",
                    "review",
                    self.submit(operation, {"x": value}),
                    "--reviewer",
                    "operator",
                    "--decision",
                    "accept",
                )
            )
            self.assertEqual(reviewed["status"], "accepted")

    def handle_once(
        self, operation: str, value: int, tag: str, *, review: bool
    ) -> None:
        # One confirmation only: reviewed leaves a policy-blocked compile scope,
        # unreviewed leaves a pending proposal.
        del tag  # see `confirm`: submission carries no request identity
        proposal_id = self.submit(operation, {"x": value})
        if review:
            self.assertEqual(
                self.payload(
                    self.run_cli(
                        "proposal",
                        "review",
                        proposal_id,
                        "--reviewer",
                        "operator",
                        "--decision",
                        "accept",
                    )
                )["status"],
                "accepted",
            )

    def promote_set(self, operation: str) -> str:
        # Library-driven setup keeps the show/receipts/verify tests independent of
        # the inspect/promote leaves: 18 tests consume this helper, and routing
        # their setup through a leaf under test would fail all of them for the
        # wrong reason.
        system = System(self.database)
        drafts = system.verify_drafts("tenant", operation, verified_by="verifier")
        self.assertTrue(drafts.passed)
        manifest = system.inspect_function_promotion("tenant", operation)
        promotion = system.promote_function(
            "tenant",
            operation,
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        return promotion.receipt_id

    def promoted_operation(self, operation: str, members: int) -> str:
        self.register(operation)
        for index in range(members):
            self.confirm(operation, index + 1, f"{operation}-{index}")
        compiled = self.payload(self.run_cli("compile", operation))
        self.assertEqual(len(compiled["created"]), members)
        return self.promote_set(operation)

    def compile_drafts(self, operation: str, values: tuple[int, ...]) -> list[str]:
        self.register(operation)
        for index, value in enumerate(values):
            self.confirm(operation, value, f"{operation}-draft-{index}")
        created = self.payload(self.run_cli("compile", operation))["created"]
        self.assertEqual(len(created), len(values))
        return typing.cast(list[str], created)

    def corrupt_middle_draft(self, artifact_ids: list[str]) -> str:
        self.assertGreaterEqual(len(artifact_ids), 3)
        connection = sqlite3.connect(self.database)
        try:
            rows = connection.execute(
                """
                SELECT id FROM artifacts WHERE id IN (?, ?, ?)
                ORDER BY input_hash, sequence, id
                """,
                tuple(artifact_ids[:3]),
            ).fetchall()
            target = str(rows[1][0])
            # Every CLI invocation builds a fresh System, so the trigger has to
            # come back or the schema fingerprint fails before the row is read.
            trigger = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'trigger' AND name = 'artifacts_build_fields_immutable'
                """
            ).fetchone()[0]
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute(
                "UPDATE artifacts SET artifact_json = '{}' WHERE id = ?",
                (target,),
            )
            connection.execute(trigger)
            connection.commit()
        finally:
            connection.close()
        return target

    def report_and_failure_event_counts(self, artifact_id: str) -> tuple[int, int]:
        connection = sqlite3.connect(self.database)
        try:
            report_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM test_reports WHERE artifact_id = ?",
                    (artifact_id,),
                ).fetchone()[0]
            )
            event_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE subject_id = ? AND kind = 'artifact.verification_failed'
                    """,
                    (artifact_id,),
                ).fetchone()[0]
            )
        finally:
            connection.close()
        return report_count, event_count

    def receipt_history(
        self, operation: str, *, members: int, receipts: int
    ) -> list[str]:
        # Re-checkpointing an unchanged set is legal and seals a fresh receipt
        # over the same function hash, so extra receipts cost no confirmations.
        history = [self.promoted_operation(operation, members)]
        while len(history) < receipts:
            history.append(self.promote_set(operation))
        return history

    def test_full_operator_lifecycle(self) -> None:
        registered = self.payload(
            self.run_cli(
                "operation",
                "register",
                "echo",
                "--min-confirmations",
                "2",
                "--min-reviewers",
                "1",
                "--min-span-seconds",
                "0",
            )
        )
        self.assertEqual(registered["revision"], 1)

        for _ in (1, 2):
            proposal_id = self.submit("echo", {"x": 1})
            queue = self.run_cli("proposal", "list").stdout_json
            self.assertIsInstance(queue, list)
            queue = typing.cast(list[dict[str, typing.Any]], queue)
            self.assertIn(proposal_id, {item["id"] for item in queue})
            resolved = self.payload(
                self.run_cli(
                    "proposal",
                    "review",
                    proposal_id,
                    "--reviewer",
                    "operator",
                    "--decision",
                    "accept",
                )
            )
            self.assertEqual(resolved["status"], "accepted")
            # `handle`'s request poll bound the accepted proposal to its example.
            # M3.5b removes that operator route, so the binding is read off the
            # review acknowledgement, which is the surviving CLI witness.
            self.assertTrue(str(resolved["example_id"]).startswith("ex_"))

        compiled = self.payload(self.run_cli("compile", "echo"))
        artifact_id = compiled["created"][0]
        report = self.payload(self.run_cli("verify", artifact_id))
        self.assertTrue(report["passed"])
        stored_report = self.payload(self.run_cli("report", "show", report["id"]))
        self.assertEqual(stored_report["scope_hash"], report["scope_hash"])
        self.assertEqual(stored_report["test_count"], report["tests"])
        promotion = self.payload(
            self.run_cli(
                "promote",
                artifact_id,
                "--scope-hash",
                report["scope_hash"],
                "--actor",
                "release-manager",
            )
        )
        self.assertEqual(promotion["artifact_id"], artifact_id)
        # `handle` answered a promoted input straight off the artifact. `resolve`
        # is the surviving deterministic route and it reads the promoted FUNCTION
        # SET, so the operator lifecycle now runs the three function leaves that
        # build that set. Every step below is a shipped CLI leaf.
        self.assertTrue(
            self.payload(
                self.run_cli("function", "verify-drafts", "echo", "--actor", "verifier")
            )["passed"]
        )
        manifest = self.payload(self.run_cli("function", "inspect", "echo"))
        self.payload(
            self.run_cli(
                "function",
                "promote",
                "echo",
                "--expected-function-hash",
                str(manifest["function_hash"]),
                "--actor",
                "release-manager",
            )
        )
        hit = self.payload(self.run_cli("resolve", "echo", "--input", '{"x":1}'))
        self.assertIs(hit["matched"], True)
        self.assertEqual(hit["output"], {"kind": "echo", "value": {"x": 1}})

    def test_machine_readable_error(self) -> None:
        run = self.run_cli("verify", "art_missing")
        self.assertEqual(run.status, 3)
        self.assertIsNone(run.stdout_json)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "not_found")

    def test_usage_errors_and_oversized_stdin_are_machine_readable(self) -> None:
        run = self.run_cli("verify")
        self.assertEqual(run.status, 2)
        self.assertIsNone(run.stdout_json)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "invalid")

        # `resolve` checks the ledger exists BEFORE it parses `--input`
        # (M3.5a D13), so the ledger has to exist or exit 5 pre-empts the cap.
        self.register("echo")

        stdout = io.StringIO()
        stderr_stream = io.StringIO()
        original_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(" " * 1_048_577)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr_stream):
                # `handle --input -` was the oversized-stdin witness. `resolve`
                # is its successor: same `_input` helper, same DEFAULT_MAX_BYTES
                # cap, and the read precedes any ledger work on both leaves.
                status = main([*self.base, "resolve", "echo", "--input", "-"])
        finally:
            sys.stdin = original_stdin
        self.assertEqual(status, 2)
        self.assertFalse(stdout.getvalue())
        self.assertIn("stdin exceeds", json.loads(stderr_stream.getvalue())["message"])

    def test_existing_leaf_bytes_are_unchanged(self) -> None:
        run = self.run_cli(
            "operation",
            "register",
            "echo",
            "--min-confirmations",
            "2",
            "--min-reviewers",
            "1",
            "--min-span-seconds",
            "0",
        )
        self.assertEqual(run.status, 0)
        self.assertEqual(
            run.stdout_bytes,
            b'{\n  "operation": "echo",\n  "revision": 1\n}\n',
        )

    def test_function_show_without_receipt_reports_current_anchor_only(self) -> None:
        self.register("echo")
        run = self.run_cli("function", "show", "echo")
        report = self.payload(run)
        self.assertEqual(set(report), _REPORT_KEYS)
        self.assertEqual(report["partition"], "tenant")
        self.assertEqual(report["operation"], "echo")
        self.assertIsNone(report["function_anchor"])
        now = report["operation_now"]
        self.assertEqual(set(now), _OPERATION_NOW_KEYS)
        self.assertEqual(now["operation_revision"], 1)
        self.assertEqual(now["projection_limit"], 100)
        self.assertEqual(now["promoted_entry_count"], 0)
        self.assertEqual(
            tuple(status["status"] for status in now["artifact_statuses"]),
            _ARTIFACT_STATUS_ORDER,
        )
        # The whole payload is exactly `_emit`'s pretty, sorted, single-LF bytes.
        self.assertEqual(run.stderr_text, "")
        expected = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
        self.assertEqual(run.stdout_text, expected + "\n")
        self.assertEqual(run.stdout_bytes, (expected + "\n").encode("utf-8"))

    def test_function_show_reports_promoted_membership(self) -> None:
        receipt_id = self.promoted_operation("echo", 3)
        report = self.payload(self.run_cli("function", "show", "echo"))
        anchor = report["function_anchor"]
        self.assertEqual(set(anchor), _ANCHOR_KEYS)
        self.assertEqual(anchor["member_count"], 3)
        self.assertEqual(len(anchor["members"]), 3)
        self.assertEqual(set(anchor["receipt"]), _RECEIPT_KEYS)
        self.assertEqual(anchor["receipt"]["id"], receipt_id)
        self.assertEqual(anchor["receipt"]["member_count"], 3)
        self.assertEqual(anchor["receipt"]["operation"], "echo")
        self.assertEqual(anchor["receipt"]["partition"], "tenant")
        self.assertEqual(anchor["receipt"]["promoted_by"], "release-manager")
        inputs = [member["input_hash"] for member in anchor["members"]]
        self.assertEqual(inputs, sorted(inputs))
        self.assertEqual(len(set(inputs)), 3)
        for ordinal, member in enumerate(anchor["members"]):
            self.assertEqual(set(member), _MEMBER_KEYS)
            self.assertEqual(member["ordinal"], ordinal)
            self.assertEqual(member["build_support"], 2)
            self.assertEqual(member["build_reviewer_count"], 1)
        now = report["operation_now"]
        self.assertEqual(now["promoted_entry_count"], 3)
        promoted = [
            status
            for status in now["artifact_statuses"]
            if status["status"] == "promoted"
        ]
        self.assertEqual(promoted[0]["count"], 3)
        self.assertEqual(len(promoted[0]["artifacts"]), 3)

    def test_function_show_projection_limit_truncates_visibly(self) -> None:
        self.promoted_operation("echo", 3)
        for limit in (1, 2):
            report = self.payload(
                self.run_cli(
                    "function", "show", "echo", "--projection-limit", str(limit)
                )
            )
            anchor = report["function_anchor"]
            self.assertEqual(anchor["member_count"], 3)
            self.assertEqual(len(anchor["members"]), limit)
            self.assertEqual(
                [member["ordinal"] for member in anchor["members"]],
                list(range(limit)),
            )
            now = report["operation_now"]
            self.assertEqual(now["projection_limit"], limit)
            self.assertEqual(now["promoted_entry_count"], 3)
            promoted = [
                status
                for status in now["artifact_statuses"]
                if status["status"] == "promoted"
            ]
            self.assertEqual(promoted[0]["count"], 3)
            self.assertEqual(len(promoted[0]["artifacts"]), limit)
        # A limit above the true count projects the count, never padding to it.
        generous = self.payload(
            self.run_cli("function", "show", "echo", "--projection-limit", "100")
        )
        self.assertEqual(generous["function_anchor"]["member_count"], 3)
        self.assertEqual(len(generous["function_anchor"]["members"]), 3)

    def test_function_show_projects_every_detail_family_under_limit(self) -> None:
        self.promoted_operation("echo", 3)
        for index, value in enumerate((91, 92, 93)):
            self.confirm("echo", value, f"ready-{index}")
        for index, value in enumerate((81, 82, 83)):
            self.handle_once("echo", value, f"blocked-{index}", review=True)
        for index, value in enumerate((71, 72, 73)):
            self.handle_once("echo", value, f"pending-{index}", review=False)
        run = self.run_cli("function", "show", "echo", "--projection-limit", "2")
        report = self.payload(run)
        self.assertEqual(run.stderr_text, "")
        unbounded = self.payload(self.run_cli("function", "show", "echo"))

        anchor = report["function_anchor"]
        self.assertEqual(anchor["member_count"], 3)
        self.assertEqual(len(anchor["members"]), 2)

        now = report["operation_now"]
        # Every family projects the canonical prefix of its own unbounded page
        # and drops the last row, so a mutant taking a suffix or an arbitrary
        # slice of >=3 rows cannot pass.
        whole = unbounded["operation_now"]
        for family, count_key in (
            ("compile_ready_scopes", "compile_ready_scope_count"),
            ("compile_blocked_scopes", "compile_blocked_scope_count"),
            ("pending_proposals", "pending_proposal_count"),
        ):
            self.assertGreaterEqual(whole[count_key], 3)
            self.assertEqual(len(whole[family]), whole[count_key])
            self.assertEqual(now[family], whole[family][:2])
            self.assertNotIn(whole[family][-1], now[family])
        self.assertEqual(anchor["members"], unbounded["function_anchor"]["members"][:2])
        self.assertNotIn(
            unbounded["function_anchor"]["members"][-1], anchor["members"]
        )

        # Promoted inputs stay policy-satisfied scopes, so all six confirmed
        # inputs report ready while only the requested two are projected.
        self.assertEqual(now["compile_ready_scope_count"], 6)
        self.assertEqual(len(now["compile_ready_scopes"]), 2)
        ready = now["compile_ready_scopes"][0]
        self.assertEqual(set(ready), _SCOPE_KEYS)
        self.assertEqual(ready["reasons"], [])
        self.assertEqual(ready["active_support"], 2)
        self.assertEqual(ready["active_reviewer_count"], 1)

        self.assertEqual(now["compile_blocked_scope_count"], 3)
        self.assertEqual(len(now["compile_blocked_scopes"]), 2)
        blocked = now["compile_blocked_scopes"][0]
        self.assertEqual(set(blocked), _SCOPE_KEYS)
        self.assertEqual(blocked["active_support"], 1)
        self.assertEqual(blocked["reasons"], ["support 1 is below required 2"])

        self.assertEqual(now["pending_proposal_count"], 3)
        self.assertEqual(len(now["pending_proposals"]), 2)
        pending = now["pending_proposals"][0]
        self.assertEqual(set(pending), _PENDING_KEYS)
        # Pending proposals project in opaque proposal-id order, so a truncated
        # page is an arbitrary — though per-ledger stable — subset.
        pending_ids = sorted(
            str(proposal["proposal_id"]) for proposal in whole["pending_proposals"]
        )
        self.assertEqual(len(pending_ids), 3)
        self.assertEqual(len(set(pending_ids)), 3)
        for pending_id in pending_ids:
            self.assertTrue(pending_id.startswith("prop_"))
        self.assertEqual(pending["operation_revision"], 1)
        # The same ledger projects the same page every time.
        self.assertEqual(
            run.stdout_bytes,
            self.run_cli(
                "function", "show", "echo", "--projection-limit", "2"
            ).stdout_bytes,
        )

        self.assertEqual(
            tuple(status["status"] for status in now["artifact_statuses"]),
            _ARTIFACT_STATUS_ORDER,
        )
        for status in now["artifact_statuses"]:
            self.assertEqual(set(status), _ARTIFACT_STATUS_KEYS)
            self.assertEqual(len(status["artifacts"]), min(status["count"], 2))
            for artifact in status["artifacts"]:
                self.assertEqual(set(artifact), _ARTIFACT_KEYS)
        promoted = now["artifact_statuses"][_ARTIFACT_STATUS_ORDER.index("promoted")]
        self.assertEqual(promoted["count"], 3)
        self.assertEqual(len(promoted["artifacts"]), 2)
        whole_promoted = whole["artifact_statuses"][
            _ARTIFACT_STATUS_ORDER.index("promoted")
        ]
        self.assertEqual(promoted["artifacts"], whole_promoted["artifacts"][:2])
        self.assertNotIn(whole_promoted["artifacts"][-1], promoted["artifacts"])
        self.assertEqual(promoted["artifacts"][0]["operation_revision"], 1)
        self.assertIsNone(promoted["artifacts"][0]["status_reason"])

        self.assertEqual(now["stale_revision_anomaly_count"], 0)
        self.assertEqual(now["stale_revision_anomalies"], [])

    def test_function_show_projects_stale_revision_anomalies(self) -> None:
        self.register("echo")
        self.confirm("echo", 1, "stale-a")
        self.confirm("echo", 2, "stale-b")
        self.assertEqual(
            len(self.payload(self.run_cli("compile", "echo"))["created"]), 2
        )
        # `operation revise` retires artifacts it strands, so this family only
        # ever reports out-of-band ledger state; bump the revision directly.
        connection = sqlite3.connect(self.database)
        with connection:
            connection.execute(
                "UPDATE operations SET revision = 2 WHERE partition = ? AND name = ?",
                ("tenant", "echo"),
            )
        connection.close()

        report = self.payload(
            self.run_cli("function", "show", "echo", "--projection-limit", "1")
        )
        self.assertIsNone(report["function_anchor"])
        now = report["operation_now"]
        self.assertEqual(now["operation_revision"], 2)
        self.assertEqual(now["stale_revision_anomaly_count"], 2)
        self.assertEqual(len(now["stale_revision_anomalies"]), 1)
        anomaly = now["stale_revision_anomalies"][0]
        self.assertEqual(set(anomaly), _ANOMALY_KEYS)
        self.assertEqual(anomaly["status"], "draft")
        self.assertEqual(anomaly["artifact_revision"], 1)
        self.assertEqual(anomaly["current_revision"], 2)
        self.assertEqual(
            anomaly["reason"],
            "draft artifact belongs to stale operation revision 1; "
            "current revision is 2",
        )

    def test_function_show_forwards_scope_and_limit_unclamped(self) -> None:
        for operation, arguments, expected, receipt in (
            ("echo", (), 100, None),
            ("echo", ("--projection-limit", "1"), 1, None),
            ("other_operation", ("--projection-limit", "10000"), 10_000, None),
            ("other_operation", ("--projection-limit", "10001"), 10_001, None),
            # argparse `type=int` accepts every Python integer spelling and the
            # value reaches the library exactly as `int()` produced it.
            ("echo", ("--projection-limit", "+1"), 1, None),
            ("echo", ("--projection-limit", " 1 "), 1, None),
            ("echo", ("--projection-limit", "1_0"), 10, None),
            # An unsupplied `--receipt-id` forwards the library's own `None`
            # rather than being dropped, and a supplied one travels verbatim:
            # `_request_id` stays the sole validator, never a CLI copy of it.
            ("echo", ("--receipt-id", "fpr_1"), 100, "fpr_1"),
            ("echo", ("--receipt-id", "a b"), 100, "a b"),
            ("echo", ("--receipt-id", "fpr_2", "--projection-limit", "7"), 7, "fpr_2"),
        ):
            with mock.patch.object(System, "function_report", autospec=True) as spy:
                spy.return_value = {"forwarded": True}
                run = self.run_cli("function", "show", operation, *arguments)
            self.assertEqual(run.status, 0)
            self.assertEqual(run.stdout_json, {"forwarded": True})
            self.assertEqual(spy.call_count, 1)
            positional = spy.call_args.args
            self.assertEqual(positional[1:], ("tenant", operation))
            self.assertEqual(
                spy.call_args.kwargs,
                {"receipt_id": receipt, "projection_limit": expected},
            )

    def test_function_show_rejects_out_of_range_projection_limit(self) -> None:
        self.register("echo")
        for value in ("0", "-1", "10001"):
            run = self.run_cli("function", "show", "echo", "--projection-limit", value)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "invalid")
            self.assertIn("projection_limit", self.error(run)["message"])

    def test_function_show_rejects_non_integer_projection_limit(self) -> None:
        for value in ("abc", "0x10", "1e2", ""):
            run = self.run_cli("function", "show", "echo", "--projection-limit", value)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "invalid")
            self.assertIn("invalid int value", self.error(run)["message"])

    def test_function_show_requires_database_and_partition_scope(self) -> None:
        # `run_cli` always supplies both, so drive `main` with a bare argv and
        # no environment fallback.
        for arguments in (
            ["function", "show", "echo"],
            ["--db", self.database, "function", "show", "echo"],
            ["--partition", "tenant", "function", "show", "echo"],
        ):
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True):
                with contextlib.redirect_stdout(stdout):
                    with contextlib.redirect_stderr(stderr):
                        status = main(arguments)
            self.assertEqual(status, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(json.loads(stderr.getvalue())["error"], "invalid")

    def test_function_show_scope_misses_are_not_found(self) -> None:
        unregistered = self.run_cli("function", "show", "echo")
        self.assertEqual(unregistered.status, 3)
        self.assertEqual(unregistered.stdout_bytes, b"")
        self.assertEqual(self.error(unregistered)["error"], "not_found")

        self.register("echo", partition="other")
        wrong_partition = self.run_cli("function", "show", "echo")
        self.assertEqual(wrong_partition.status, 3)
        self.assertEqual(wrong_partition.stdout_bytes, b"")
        self.assertEqual(self.error(wrong_partition)["error"], "not_found")

        # The operation name matches exactly: neither case-folded nor pattern
        # matched, so `_` never behaves as a wildcard.
        self.register("echoX1")
        self.register("Echo_1")
        near_miss = self.run_cli("function", "show", "echo_1")
        self.assertEqual(near_miss.status, 3)
        self.assertEqual(self.error(near_miss)["error"], "not_found")
        self.assertEqual(
            self.payload(
                self.run_cli("--partition", "other", "function", "show", "echo")
            )["partition"],
            "other",
        )

    def test_function_group_rejects_missing_arguments(self) -> None:
        for arguments in (
            ("function",),
            ("function", "show"),
            ("function", "receipts"),
        ):
            run = self.run_cli(*arguments)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "invalid")
        # `operation` is required, so the parser rejects it before dispatch
        # rather than forwarding a missing scope to the library.
        self.assertIn(
            "the following arguments are required: operation",
            self.error(self.run_cli("function", "show"))["message"],
        )
        self.assertIn(
            "the following arguments are required: function_command",
            self.error(self.run_cli("function"))["message"],
        )

    def test_function_group_sits_between_report_and_the_audit_tail(self) -> None:
        from cement_runtime.cli import _parser

        self.assertIn("report,function,events}", _parser().format_help())

    def test_function_show_returns_the_library_report_unwrapped(self) -> None:
        from cement_runtime.cli import _Outcome, _parser, _run

        parser = _parser()
        arguments = parser.parse_args(
            ["--db", self.database, "--partition", "tenant", "function", "show", "echo"]
        )
        with mock.patch.object(System, "function_report", autospec=True) as spy:
            spy.return_value = {"bare": True}
            result = _run(arguments, parser)
        self.assertIs(result, spy.return_value)
        self.assertNotIsInstance(result, _Outcome)

    def test_function_receipts_enumerates_newest_first(self) -> None:
        history = self.receipt_history("echo", members=2, receipts=3)
        page = self.payload(self.run_cli("function", "receipts", "echo"))
        self.assertEqual(set(page), {"next_before_sequence", "receipts"})
        self.assertIsNone(page["next_before_sequence"])
        self.assertEqual([row["id"] for row in page["receipts"]], list(reversed(history)))
        self.assertEqual([row["sequence"] for row in page["receipts"]], [3, 2, 1])
        for row in page["receipts"]:
            self.assertEqual(set(row), _RECEIPT_KEYS)
            self.assertEqual(row["partition"], "tenant")
            self.assertEqual(row["operation"], "echo")
            self.assertEqual(row["operation_revision"], 1)
            self.assertEqual(row["member_count"], 2)

    def test_function_receipts_pages_through_the_exclusive_cursor(self) -> None:
        history = self.receipt_history("echo", members=2, receipts=4)
        walked: list[str] = []
        cursor: object = None
        pages = 0
        while True:
            arguments = ["function", "receipts", "echo", "--limit", "1"]
            if cursor is not None:
                arguments += ["--before-sequence", str(cursor)]
            page = self.payload(self.run_cli(*arguments))
            pages += 1
            self.assertLess(pages, 10)
            walked += [row["id"] for row in page["receipts"]]
            cursor = page["next_before_sequence"]
            if cursor is None:
                break
        # The cursor is exclusive, so a full walk visits every receipt exactly
        # once, newest first, and the terminal page reports no continuation.
        self.assertEqual(walked, list(reversed(history)))
        self.assertEqual(len(walked), len(set(walked)))
        self.assertEqual(pages, 4)

    def test_function_receipts_truncation_is_visible_without_a_flag(self) -> None:
        history = self.receipt_history("echo", members=2, receipts=3)
        page = self.payload(self.run_cli("function", "receipts", "echo", "--limit", "2"))
        self.assertEqual(len(page["receipts"]), 2)
        self.assertEqual(page["next_before_sequence"], page["receipts"][-1]["sequence"])
        rest = self.payload(
            self.run_cli(
                "function",
                "receipts",
                "echo",
                "--before-sequence",
                str(page["next_before_sequence"]),
            )
        )
        self.assertEqual([row["id"] for row in rest["receipts"]], [history[0]])
        self.assertIsNone(rest["next_before_sequence"])
        # A limit above the true count projects the count, never padding to it.
        whole = self.payload(
            self.run_cli("function", "receipts", "echo", "--limit", "10000")
        )
        self.assertEqual(len(whole["receipts"]), 3)
        self.assertIsNone(whole["next_before_sequence"])
        # Terminality is the cursor, never the page length: a page holding
        # exactly `limit` rows with nothing behind it is full AND terminal, so
        # a short page is sufficient evidence of the end but not necessary.
        exact = self.payload(self.run_cli("function", "receipts", "echo", "--limit", "3"))
        self.assertEqual(len(exact["receipts"]), 3)
        self.assertIsNone(exact["next_before_sequence"])
        one_short = self.payload(
            self.run_cli("function", "receipts", "echo", "--limit", "2")
        )
        self.assertEqual(len(one_short["receipts"]), 2)
        self.assertIsNotNone(one_short["next_before_sequence"])

    def test_function_receipts_empty_pages_do_not_distinguish_scope(self) -> None:
        # Deliberate divergence from `show`: enumeration runs no operations
        # lookup, so an unregistered operation and a registered one holding no
        # receipt collapse into one observable.
        empty = {"next_before_sequence": None, "receipts": []}
        self.assertEqual(self.payload(self.run_cli("function", "receipts", "echo")), empty)
        self.register("echo")
        self.assertEqual(self.payload(self.run_cli("function", "receipts", "echo")), empty)
        self.receipt_history("other_operation", members=2, receipts=1)
        self.assertEqual(
            self.payload(
                self.run_cli("--partition", "other", "function", "receipts", "other_operation")
            ),
            empty,
        )
        # Positive control: the same operation in its own partition is not empty.
        self.assertEqual(
            len(self.payload(self.run_cli("function", "receipts", "other_operation"))["receipts"]),
            1,
        )
        # `show` keeps separating the two conditions with exit 3.
        self.assertEqual(self.run_cli("function", "show", "absent_operation").status, 3)

    def test_function_receipts_filters_by_operation_revision(self) -> None:
        history = self.receipt_history("echo", members=2, receipts=2)
        self.assertEqual(
            self.payload(self.run_cli("operation", "revise", "echo", "--actor", "owner"))[
                "revision"
            ],
            2,
        )
        first = self.payload(
            self.run_cli("function", "receipts", "echo", "--operation-revision", "1")
        )
        self.assertEqual([row["id"] for row in first["receipts"]], list(reversed(history)))
        second = self.payload(
            self.run_cli("function", "receipts", "echo", "--operation-revision", "2")
        )
        self.assertEqual(second["receipts"], [])
        # Unfiltered enumeration still spans every revision.
        self.assertEqual(
            len(self.payload(self.run_cli("function", "receipts", "echo"))["receipts"]), 2
        )

    def test_function_receipts_rejects_out_of_range_bounds(self) -> None:
        self.register("echo")
        for flag, value, label in (
            ("--limit", "0", "limit"),
            ("--limit", "-1", "limit"),
            ("--limit", "10001", "limit"),
            ("--operation-revision", "0", "operation_revision"),
            ("--operation-revision", "-1", "operation_revision"),
            ("--before-sequence", "-1", "before_sequence"),
        ):
            run = self.run_cli("function", "receipts", "echo", flag, value)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "invalid")
            self.assertIn(label, self.error(run)["message"])
        # The library validates `operation_revision` before `limit`, so the
        # first bad argument is the one the operator is told about.
        both = self.run_cli(
            "function", "receipts", "echo", "--operation-revision", "0", "--limit", "0"
        )
        self.assertEqual(both.status, 2)
        self.assertIn("operation_revision", self.error(both)["message"])
        self.assertNotIn("limit must", self.error(both)["message"])

    def test_function_receipts_bounds_are_pinned_as_adjacent_pairs(self) -> None:
        # Each maximum is pinned by an accepted value beside its rejected
        # successor: a lone rejection would leave the boundary's position free.
        self.receipt_history("echo", members=2, receipts=1)
        signed64 = 2**63 - 1
        for flag, label, accepted in (
            ("--operation-revision", "operation_revision", 0),
            ("--before-sequence", "before_sequence", 1),
            ("--limit", "limit", 1),
        ):
            maximum = 10_000 if flag == "--limit" else signed64
            inside = self.payload(
                self.run_cli("function", "receipts", "echo", flag, str(maximum))
            )
            self.assertEqual(len(inside["receipts"]), accepted)
            outside = self.run_cli("function", "receipts", "echo", flag, str(maximum + 1))
            self.assertEqual(outside.status, 2)
            self.assertEqual(outside.stdout_bytes, b"")
            self.assertIn(label, self.error(outside)["message"])

    def test_function_receipts_accepts_a_zero_before_sequence(self) -> None:
        self.receipt_history("echo", members=2, receipts=1)
        # `0` sits inside the library's bound and selects `sequence < 0`, so
        # the page is legally empty rather than an error.
        self.assertEqual(
            self.payload(self.run_cli("function", "receipts", "echo", "--before-sequence", "0")),
            {"next_before_sequence": None, "receipts": []},
        )
        self.assertEqual(
            len(self.payload(self.run_cli("function", "receipts", "echo"))["receipts"]), 1
        )

    def test_function_receipts_forwards_scope_and_bounds_unclamped(self) -> None:
        for operation, arguments, expected in (
            ("echo", (), {"operation_revision": None, "before_sequence": None, "limit": 100}),
            (
                "echo",
                ("--limit", "10001"),
                {"operation_revision": None, "before_sequence": None, "limit": 10_001},
            ),
            (
                "other_operation",
                ("--operation-revision", "1_0", "--before-sequence", "+7", "--limit", " 3 "),
                {"operation_revision": 10, "before_sequence": 7, "limit": 3},
            ),
            # Out-of-range values travel too: the CLI owns no bound of its own.
            (
                "echo",
                ("--operation-revision", "0", "--before-sequence", "0"),
                {"operation_revision": 0, "before_sequence": 0, "limit": 100},
            ),
        ):
            with mock.patch.object(System, "function_receipts", autospec=True) as spy:
                spy.return_value = {"forwarded": True}
                run = self.run_cli("function", "receipts", operation, *arguments)
            self.assertEqual(run.status, 0)
            self.assertEqual(run.stdout_json, {"forwarded": True})
            self.assertEqual(spy.call_count, 1)
            self.assertEqual(spy.call_args.args[1:], ("tenant", operation))
            self.assertEqual(spy.call_args.kwargs, expected)

    def test_function_receipts_scope_matches_exactly(self) -> None:
        # This leaf queries the receipts table, not the operations table, so
        # the `_` and case colliders have to reach it on their own.
        history = self.receipt_history("echo_1", members=2, receipts=1)
        self.assertEqual(
            [
                row["id"]
                for row in self.payload(self.run_cli("function", "receipts", "echo_1"))["receipts"]
            ],
            history,
        )
        for near_miss in ("echoX1", "ECHO_1", "Echo_1", "echo"):
            self.assertEqual(
                self.payload(self.run_cli("function", "receipts", near_miss))["receipts"], []
            )
        self.assertEqual(
            self.payload(
                self.run_cli("--partition", "other", "function", "receipts", "echo_1")
            )["receipts"],
            [],
        )

    def test_function_receipts_returns_the_library_page_unwrapped(self) -> None:
        from cement_runtime.cli import _Outcome, _parser, _run

        parser = _parser()
        arguments = parser.parse_args(
            [
                "--db",
                self.database,
                "--partition",
                "tenant",
                "function",
                "receipts",
                "echo",
            ]
        )
        with mock.patch.object(System, "function_receipts", autospec=True) as spy:
            spy.return_value = {"bare": True}
            result = _run(arguments, parser)
        self.assertIs(result, spy.return_value)
        self.assertNotIsInstance(result, _Outcome)

    def test_function_show_receipt_id_pins_a_historical_anchor(self) -> None:
        history = self.receipt_history("echo", members=2, receipts=3)
        current = self.payload(self.run_cli("function", "show", "echo"))
        self.assertEqual(current["function_anchor"]["receipt"]["id"], history[-1])
        for index, receipt_id in enumerate(history):
            pinned = self.payload(
                self.run_cli("function", "show", "echo", "--receipt-id", receipt_id)
            )
            anchor = pinned["function_anchor"]
            self.assertEqual(anchor["receipt"]["id"], receipt_id)
            self.assertEqual(anchor["receipt"]["sequence"], index + 1)
            self.assertEqual(anchor["member_count"], 2)
            # The anchor freezes at the named receipt while the operation half
            # stays live, so the two halves never collapse into one number.
            self.assertEqual(
                pinned["operation_now"]["operation_revision"],
                current["operation_now"]["operation_revision"],
            )
            self.assertEqual(
                pinned["operation_now"]["promoted_entry_count"],
                current["operation_now"]["promoted_entry_count"],
            )
        # Naming an older receipt is observable against bare `show`.
        self.assertNotEqual(
            self.payload(
                self.run_cli("function", "show", "echo", "--receipt-id", history[0])
            )["function_anchor"]["receipt"]["id"],
            current["function_anchor"]["receipt"]["id"],
        )

    def test_function_show_receipt_id_reaches_a_superseded_revision(self) -> None:
        # The named receipt may belong to ANY revision, so the anchor freezes
        # at revision 1 while the operation half reports the current revision.
        # Three same-revision receipts cannot kill a current-revision filter.
        history = self.receipt_history("echo", members=2, receipts=1)
        self.assertEqual(
            self.payload(
                self.run_cli(
                    "operation",
                    "revise",
                    "echo",
                    "--actor",
                    "owner",
                    "--min-confirmations",
                    "4",
                    "--min-reviewers",
                    "3",
                    "--min-span-seconds",
                    "11",
                )
            )["revision"],
            2,
        )
        pinned = self.payload(
            self.run_cli("function", "show", "echo", "--receipt-id", history[0])
        )
        self.assertEqual(pinned["function_anchor"]["receipt"]["id"], history[0])
        self.assertEqual(pinned["function_anchor"]["receipt"]["operation_revision"], 1)
        self.assertEqual(pinned["operation_now"]["operation_revision"], 2)
        self.assertNotEqual(
            pinned["operation_now"]["policy_hash"],
            pinned["function_anchor"]["receipt"]["policy_hash"],
        )
        # Bare `show` resolves the current revision, which carries no receipt.
        self.assertIsNone(self.payload(self.run_cli("function", "show", "echo"))["function_anchor"])
        # Enumeration reaches the superseded receipt too, unfiltered.
        self.assertEqual(
            [row["id"] for row in self.payload(self.run_cli("function", "receipts", "echo"))["receipts"]],
            history,
        )

    def test_function_show_receipt_id_misses_are_not_found(self) -> None:
        history = self.receipt_history("echo", members=2, receipts=1)
        self.receipt_history("other_operation", members=2, receipts=1)
        for operation, receipt_id in (
            ("echo", "fpr_" + "0" * 32),
            ("other_operation", history[0]),
        ):
            run = self.run_cli("function", "show", operation, "--receipt-id", receipt_id)
            self.assertEqual(run.status, 3)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "not_found")
        self.register("echo", partition="other")
        wrong_partition = self.run_cli(
            "--partition", "other", "function", "show", "echo", "--receipt-id", history[0]
        )
        self.assertEqual(wrong_partition.status, 3)
        self.assertEqual(self.error(wrong_partition)["error"], "not_found")
        # Positive control: the same id resolves inside its own scope.
        self.assertEqual(
            self.payload(
                self.run_cli("function", "show", "echo", "--receipt-id", history[0])
            )["function_anchor"]["receipt"]["id"],
            history[0],
        )

    def test_function_show_rejects_a_malformed_receipt_id(self) -> None:
        self.register("echo")
        for value in ("", ".leading", "has space", "a" * 193, "identifiér"):
            run = self.run_cli("function", "show", "echo", "--receipt-id", value)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "invalid")
            self.assertIn("bounded ASCII identifier", self.error(run)["message"])
        # A leading `-` needs the equals spelling to reach the library at all;
        # separated, argparse claims the token first. Both exit 2, but only the
        # equals form's message is ours to pin -- the other is argparse's.
        equals = self.run_cli("function", "show", "echo", "--receipt-id=-lead")
        self.assertEqual(equals.status, 2)
        self.assertIn("bounded ASCII identifier", self.error(equals)["message"])
        separated = self.run_cli("function", "show", "echo", "--receipt-id", "-lead")
        self.assertEqual(separated.status, 2)
        self.assertEqual(separated.stdout_bytes, b"")
        self.assertEqual(self.error(separated)["error"], "invalid")
        # 192 characters is the inclusive maximum, so a well-formed id of that
        # length reaches lookup and misses rather than failing validation.
        self.assertEqual(
            self.run_cli("function", "show", "echo", "--receipt-id", "a" * 192).status, 3
        )
        # `receipt_id` is validated before `projection_limit`, so a run with
        # both bad names the receipt id.
        both = self.run_cli(
            "function", "show", "echo", "--receipt-id", "", "--projection-limit", "0"
        )
        self.assertEqual(both.status, 2)
        self.assertIn("bounded ASCII identifier", self.error(both)["message"])
        self.assertNotIn("projection_limit", self.error(both)["message"])

    def test_function_show_receipt_id_still_bounds_members(self) -> None:
        history = self.receipt_history("echo", members=3, receipts=1)
        pinned = self.payload(
            self.run_cli(
                "function",
                "show",
                "echo",
                "--receipt-id",
                history[0],
                "--projection-limit",
                "1",
            )
        )
        anchor = pinned["function_anchor"]
        self.assertEqual(anchor["member_count"], 3)
        self.assertEqual(len(anchor["members"]), 1)
        self.assertEqual(pinned["operation_now"]["projection_limit"], 1)
        whole = self.payload(
            self.run_cli("function", "show", "echo", "--receipt-id", history[0])
        )
        self.assertEqual(
            [member["ordinal"] for member in whole["function_anchor"]["members"]], [0, 1, 2]
        )

    def test_outcome_raw_channel_writes_exact_bytes(self) -> None:
        from cement_runtime.cli import _Outcome

        for text_only in (False, True):
            with mock.patch(
                "cement_runtime.cli._run", return_value=_Outcome(raw="exact-λ-text")
            ):
                run = self.run_cli(
                    "function", "show", "echo", text_only=text_only
                )
            self.assertEqual(run.status, 0)
            self.assertEqual(run.stdout_bytes, "exact-λ-text".encode("utf-8"))
            self.assertIsNone(run.stdout_json)
            self.assertEqual(run.stderr_text, "")
            self.assertIsNone(run.stderr_json)

    def test_outcome_raw_channel_returns_its_status(self) -> None:
        from cement_runtime.cli import _Outcome

        with mock.patch(
            "cement_runtime.cli._run", return_value=_Outcome(raw="x", status=6)
        ):
            run = self.run_cli("function", "show", "echo")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stdout_bytes, b"x")

    def test_outcome_raw_channel_bypasses_the_text_writer(self) -> None:
        from cement_runtime.cli import _Outcome

        class _BufferOnly(_BinaryOutput):
            def write(self, value: str) -> int:
                raise AssertionError("raw output reached the text writer")

        stdout = _BufferOnly()
        with mock.patch(
            "cement_runtime.cli._run", return_value=_Outcome(raw="raw-bytes")
        ):
            with contextlib.redirect_stdout(stdout):  # type: ignore[arg-type]
                status = main([*self.base, "function", "show", "echo"])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.buffer.getvalue(), b"raw-bytes")

    def test_outcome_nonzero_status_keeps_payload_on_stdout(self) -> None:
        from cement_runtime.cli import _Outcome

        with mock.patch(
            "cement_runtime.cli._run",
            return_value=_Outcome({"passed": False}, status=6),
        ):
            run = self.run_cli("function", "show", "echo")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stdout_json, {"passed": False})
        self.assertEqual(run.stdout_bytes, b'{\n  "passed": false\n}\n')
        self.assertEqual(run.stderr_text, "")
        self.assertIsNone(run.stderr_json)

    def test_outcome_requires_exactly_one_channel(self) -> None:
        from cement_runtime.cli import _MISSING, _Outcome

        with self.assertRaises(AssertionError):
            _Outcome()
        with self.assertRaises(AssertionError):
            _Outcome({"payload": True}, raw="text")
        with self.assertRaises(AssertionError):
            _Outcome({"payload": True}, status="6")
        with self.assertRaises(AssertionError):
            _Outcome({"payload": True}, status=True)
        self.assertEqual(_Outcome({"payload": True}, status=6).status, 6)
        self.assertEqual(_Outcome(raw="text").payload, _MISSING)
        self.assertEqual(_Outcome({"payload": True}).status, 0)
        self.assertIsNone(_Outcome({"payload": True}).raw)
        # Falsy carriers are real output: only the private sentinel means absent,
        # so every falsy JSON payload constructs and round-trips.
        self.assertIsNone(_Outcome(None).payload)
        self.assertIsNone(_Outcome(None).raw)
        self.assertEqual(_Outcome(raw="").raw, "")
        self.assertEqual(_Outcome(raw="").payload, _MISSING)
        for payload in ("", 0, False, [], {}):
            self.assertEqual(_Outcome(payload).payload, payload)
            self.assertIsNone(_Outcome(payload).raw)

    def test_cli_protocol_shape_is_exact(self) -> None:
        from cement_runtime.cli import _MISSING, _Outcome

        self.assertTrue(_Outcome.__dataclass_params__.frozen)
        self.assertIn("__slots__", _Outcome.__dict__)
        signature = inspect.signature(_Outcome)
        self.assertEqual(
            [
                (name, parameter.kind.name, parameter.default)
                for name, parameter in signature.parameters.items()
            ],
            [
                ("payload", "POSITIONAL_OR_KEYWORD", _MISSING),
                ("status", "KEYWORD_ONLY", 0),
                ("raw", "KEYWORD_ONLY", None),
            ],
        )
        self.assertEqual(
            typing.get_type_hints(_Outcome),
            {"payload": typing.Any, "status": int, "raw": str | None},
        )

    def test_audit_tail_still_dispatches_after_the_function_group(self) -> None:
        # `function` sits directly before `events` in the dispatch chain, so the
        # audit tail is what proves the new guard does not swallow its successor.
        self.register("echo")
        run = self.run_cli("events", "--limit", "10")
        self.assertEqual(run.status, 0)
        self.assertIsInstance(run.stdout_json, list)
        events = typing.cast(list[dict[str, typing.Any]], run.stdout_json)
        self.assertIn("operation.registered", {event["kind"] for event in events})

    def test_outcome_subclasses_keep_their_channel_semantics(self) -> None:
        # `main` accepts `_Outcome` by `isinstance`, so a later sub-unit may
        # specialise it without losing the raw channel or the status.
        from cement_runtime.cli import _Outcome

        class _DerivedOutcome(_Outcome):
            pass

        with mock.patch(
            "cement_runtime.cli._run", return_value=_DerivedOutcome(raw="x", status=6)
        ):
            run = self.run_cli("function", "show", "echo")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stdout_bytes, b"x")

    def test_unknown_function_leaf_is_fatal_rather_than_silent(self) -> None:
        # A leaf added to the parser but missed in dispatch must not fall
        # through to a `None` result that `main` would emit as `null`.
        from cement_runtime.cli import _parser, _run

        # The sentinel names no leaf any u4c sub-unit will claim; `show`,
        # `receipts`, `verify-drafts`, `verify`, `inspect`, `promote`, `export`
        # and `eval` are all reserved, so only a hand-built namespace reaches
        # the fall-through.
        arguments = argparse.Namespace(
            command="function",
            function_command="__unshipped__",
            db=self.database,
            partition="tenant",
        )
        with self.assertRaises(AssertionError):
            _run(arguments, _parser())

    def test_library_faults_are_not_swallowed_by_a_catch_all(self) -> None:
        # `main` maps the Cement error hierarchy only; a corrupt ledger scalar
        # escapes as its own exception instead of degrading to exit 2.
        with mock.patch.object(System, "function_report", autospec=True) as spy:
            spy.side_effect = ValueError("corrupt persisted scalar")
            with self.assertRaises(ValueError):
                self.run_cli("function", "show", "echo")

    def test_outcome_channels_survive_falsy_values_through_main(self) -> None:
        from cement_runtime.cli import _Outcome

        for outcome, expected_bytes, expected_status in (
            (_Outcome(raw=""), b"", 0),
            (_Outcome(None), b"null\n", 0),
            (_Outcome({"ok": True}, status=999), b'{\n  "ok": true\n}\n', 999),
        ):
            with mock.patch("cement_runtime.cli._run", return_value=outcome):
                run = self.run_cli("function", "show", "echo")
            self.assertEqual(run.stdout_bytes, expected_bytes)
            self.assertEqual(run.status, expected_status)

    def test_runner_decoding_is_total(self) -> None:
        self.assertIsNone(_decoded(""))
        self.assertIsNone(_decoded("not-json"))
        self.assertIsNone(_decoded("{"))
        self.assertEqual(_decoded('{"ok":true}'), {"ok": True})
        self.assertEqual(_decoded("[]"), [])

    def test_function_verify_drafts_emits_every_passing_entry_and_exits_zero(self) -> None:
        created = self.compile_drafts("drafts-pass", (3, 12, 27))
        run = self.run_cli(
            "function", "verify-drafts", "drafts-pass", "--actor", "verifier"
        )
        payload = self.payload(run)
        self.assertTrue(payload["passed"])
        self.assertEqual(len(payload["entries"]), 3)
        self.assertEqual(payload["skipped"], [])
        self.assertEqual(
            [entry["report"]["passed"] for entry in payload["entries"]],
            [True, True, True],
        )
        self.assertEqual(
            {entry["artifact_id"] for entry in payload["entries"]}, set(created)
        )
        self.assertTrue(all(entry["entry_seal"] for entry in payload["entries"]))
        self.assertEqual(run.stderr_text, "")

    def test_function_verify_drafts_treats_an_empty_eligible_batch_as_a_vacuous_pass(self) -> None:
        self.register("drafts-empty")
        run = self.run_cli(
            "function", "verify-drafts", "drafts-empty", "--actor", "verifier"
        )
        payload = self.payload(run)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["entries"], [])
        self.assertEqual(payload["skipped"], [])
        self.assertEqual(run.stderr_text, "")

    def test_function_verify_drafts_reports_a_superseded_build_as_a_benign_skip(self) -> None:
        created = self.compile_drafts("drafts-skip", (4, 15, 26))
        system = System(self.database)
        with system.store.transaction(write=False) as connection:
            rows = connection.execute(
                """
                SELECT id, input_hash, input_json FROM artifacts
                WHERE id IN (?, ?, ?) ORDER BY input_hash, sequence, id
                """,
                tuple(created),
            ).fetchall()
        middle = rows[1]
        value = typing.cast(dict[str, int], json.loads(str(middle["input_json"])))
        self.handle_once("drafts-skip", value["x"], "drafts-skip-extra", review=True)
        newer = self.payload(self.run_cli("compile", "drafts-skip"))["created"]
        self.assertEqual(len(newer), 1)

        run = self.run_cli(
            "function", "verify-drafts", "drafts-skip", "--actor", "verifier"
        )
        payload = self.payload(run)
        self.assertTrue(payload["passed"])
        self.assertEqual(len(payload["entries"]), 3)
        self.assertTrue(all(entry["report"]["passed"] for entry in payload["entries"]))
        self.assertEqual(
            payload["skipped"],
            [
                {
                    "artifact_id": str(middle["id"]),
                    "input_hash": str(middle["input_hash"]),
                    "reason": "superseded-build",
                }
            ],
        )
        self.assertNotIn(
            str(middle["id"]),
            {entry["artifact_id"] for entry in payload["entries"]},
        )
        self.assertEqual(run.stderr_text, "")

    def test_function_verify_drafts_exits_six_when_the_middle_of_three_entries_fails(self) -> None:
        created = self.compile_drafts("drafts-fail", (5, 16, 29))
        target = self.corrupt_middle_draft(created)
        run = self.run_cli(
            "function", "verify-drafts", "drafts-fail", "--actor", "verifier"
        )
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        self.assertIsInstance(run.stdout_json, dict)
        payload = typing.cast(dict[str, typing.Any], run.stdout_json)
        self.assertFalse(payload["passed"])
        self.assertEqual(
            [entry["report"]["passed"] for entry in payload["entries"]],
            [True, False, True],
        )
        self.assertEqual(payload["entries"][1]["artifact_id"], target)
        self.assertIsNone(payload["entries"][1]["entry_seal"])
        self.assertIsNotNone(payload["entries"][0]["entry_seal"])
        self.assertIsNotNone(payload["entries"][2]["entry_seal"])

    def test_function_verify_drafts_repeats_a_negative_verdict_for_the_same_corrupt_ledger(self) -> None:
        created = self.compile_drafts("drafts-rerun", (6, 17, 31))
        target = self.corrupt_middle_draft(created)
        first = self.run_cli(
            "function", "verify-drafts", "drafts-rerun", "--actor", "verifier"
        )
        first_counts = self.report_and_failure_event_counts(target)
        second = self.run_cli(
            "function", "verify-drafts", "drafts-rerun", "--actor", "verifier"
        )
        second_counts = self.report_and_failure_event_counts(target)
        for run in (first, second):
            self.assertEqual(run.status, 6)
            self.assertEqual(run.stderr_text, "")
            self.assertFalse(typing.cast(dict[str, typing.Any], run.stdout_json)["passed"])
        self.assertEqual(second_counts, (first_counts[0] + 1, first_counts[1] + 1))

    def test_function_verify_drafts_commits_the_failed_report_and_event_before_exit_six(self) -> None:
        created = self.compile_drafts("drafts-durable", (7, 18, 33))
        target = self.corrupt_middle_draft(created)
        before = self.report_and_failure_event_counts(target)
        run = self.run_cli(
            "function", "verify-drafts", "drafts-durable", "--actor", "verifier"
        )
        after = self.report_and_failure_event_counts(target)
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(after, (before[0] + 1, before[1] + 1))
        connection = sqlite3.connect(self.database)
        try:
            status = connection.execute(
                "SELECT status FROM artifacts WHERE id = ?", (target,)
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(status, "draft")

    def test_function_verify_drafts_rejects_an_unregistered_operation(self) -> None:
        run = self.run_cli(
            "function", "verify-drafts", "absent", "--actor", "verifier"
        )
        self.assertEqual(run.status, 3)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "not_found")

    def test_function_verify_drafts_does_not_cross_partition_or_like_colliding_scopes(self) -> None:
        self.register("echo_1", partition="other")
        self.register("echoX1")
        self.register("Echo_1")
        run = self.run_cli(
            "function", "verify-drafts", "echo_1", "--actor", "verifier"
        )
        self.assertEqual(run.status, 3)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "not_found")
        positive = self.run_cli(
            "--partition",
            "other",
            "function",
            "verify-drafts",
            "echo_1",
            "--actor",
            "verifier",
        )
        self.assertEqual(positive.status, 0)

    def test_function_verify_drafts_requires_the_actor_option(self) -> None:
        self.register("drafts-actor-required")
        run = self.run_cli("function", "verify-drafts", "drafts-actor-required")
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "invalid")

    def test_function_verify_drafts_rejects_an_empty_actor(self) -> None:
        self.register("drafts-actor-empty")
        run = self.run_cli(
            "function", "verify-drafts", "drafts-actor-empty", "--actor", ""
        )
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "invalid")

    def test_function_verify_projects_a_passing_promoted_set_without_document_content(self) -> None:
        self.promoted_operation("verify-pass", 3)
        system = System(self.database)
        library = system.verify_function("tenant", "verify-pass")
        self.assertIsNotNone(library.document)
        assert library.document is not None
        document_text = library.document.text

        run = self.run_cli("function", "verify", "verify-pass")
        payload = self.payload(run)
        self.assertEqual(set(payload), _FUNCTION_VERIFY_KEYS)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["entries"], 3)
        self.assertEqual(payload["function_hash"], library.function_hash)
        self.assertEqual(
            [check["key"] for check in payload["checks"]], list(_FUNCTION_CHECK_KEYS)
        )
        self.assertTrue(all(check["passed"] for check in payload["checks"]))
        self.assertNotIn("document", run.stdout_text)
        self.assertNotIn(document_text, run.stdout_text)
        self.assertNotIn("_cases", run.stdout_text)
        self.assertEqual(run.stderr_text, "")

    def test_function_verify_accepts_the_matching_expected_function_hash(self) -> None:
        self.promoted_operation("verify-match", 2)
        expected = System(self.database).verify_function(
            "tenant", "verify-match"
        ).function_hash
        self.assertIsNotNone(expected)
        run = self.run_cli(
            "function",
            "verify",
            "verify-match",
            "--expected-function-hash",
            str(expected),
        )
        self.assertEqual(run.status, 0)
        self.assertTrue(self.payload(run)["passed"])
        self.assertEqual(run.stderr_text, "")

    def test_function_verify_exits_six_with_a_diagnostic_hash_for_a_different_valid_digest(self) -> None:
        self.promoted_operation("verify-mismatch", 2)
        actual = System(self.database).verify_function(
            "tenant", "verify-mismatch"
        ).function_hash
        self.assertIsNotNone(actual)
        different = "0" * 64 if actual != "0" * 64 else "1" * 64
        run = self.run_cli(
            "function",
            "verify",
            "verify-mismatch",
            "--expected-function-hash",
            different,
        )
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        self.assertIsInstance(run.stdout_json, dict)
        payload = typing.cast(dict[str, typing.Any], run.stdout_json)
        self.assertEqual(set(payload), _FUNCTION_VERIFY_KEYS)
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["function_hash"], actual)
        self.assertIsNotNone(payload["function_hash"])

    def test_function_verify_fails_only_the_receipt_check_without_a_function_checkpoint(self) -> None:
        self.register("verify-no-checkpoint")
        self.confirm("verify-no-checkpoint", 11, "verify-no-checkpoint-a")
        self.confirm("verify-no-checkpoint", 23, "verify-no-checkpoint-b")
        created = self.payload(self.run_cli("compile", "verify-no-checkpoint"))["created"]
        self.assertEqual(len(created), 2)
        system = System(self.database)
        for artifact_id in created:
            report = system.verify("tenant", artifact_id, verified_by="verifier")
            self.assertTrue(report.passed)
            system.promote(
                "tenant",
                artifact_id,
                scope_hash=report.scope_hash,
                promoted_by="release-manager",
            )

        run = self.run_cli("function", "verify", "verify-no-checkpoint")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        payload = typing.cast(dict[str, typing.Any], run.stdout_json)
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["entries"], 2)
        self.assertEqual(
            [check["key"] for check in payload["checks"]], list(_FUNCTION_CHECK_KEYS)
        )
        self.assertEqual(
            [check["passed"] for check in payload["checks"]],
            [True, True, True, True, True, False],
        )

    def test_function_verify_treats_an_empty_promoted_set_as_a_vacuous_pass(self) -> None:
        self.register("verify-empty")
        run = self.run_cli("function", "verify", "verify-empty")
        payload = self.payload(run)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["entries"], 0)
        self.assertEqual(set(payload), _FUNCTION_VERIFY_KEYS)
        self.assertTrue(all(check["passed"] for check in payload["checks"]))
        self.assertEqual(run.stderr_text, "")

    def test_function_verify_rejects_a_digest_one_character_short_beside_an_accepted_digest(self) -> None:
        self.register("verify-lower-bound")
        accepted = self.run_cli(
            "function",
            "verify",
            "verify-lower-bound",
            "--expected-function-hash",
            "0" * 64,
        )
        self.assertIn(accepted.status, (0, 6))
        self.assertEqual(accepted.stderr_text, "")
        rejected = self.run_cli(
            "function",
            "verify",
            "verify-lower-bound",
            "--expected-function-hash",
            "0" * 63,
        )
        self.assertEqual(rejected.status, 2)
        self.assertEqual(rejected.stdout_bytes, b"")
        self.assertEqual(self.error(rejected)["error"], "invalid")

    def test_function_verify_rejects_a_digest_one_character_long_beside_an_accepted_digest(self) -> None:
        self.register("verify-upper-bound")
        accepted = self.run_cli(
            "function",
            "verify",
            "verify-upper-bound",
            "--expected-function-hash",
            "0" * 64,
        )
        self.assertIn(accepted.status, (0, 6))
        self.assertEqual(accepted.stderr_text, "")
        rejected = self.run_cli(
            "function",
            "verify",
            "verify-upper-bound",
            "--expected-function-hash",
            "0" * 65,
        )
        self.assertEqual(rejected.status, 2)
        self.assertEqual(rejected.stdout_bytes, b"")
        self.assertEqual(self.error(rejected)["error"], "invalid")

    def test_function_verify_rejects_uppercase_and_nonhex_expected_hashes_without_normalizing(self) -> None:
        self.register("verify-digest-grammar")
        accepted = self.run_cli(
            "function",
            "verify",
            "verify-digest-grammar",
            "--expected-function-hash",
            "a" * 64,
        )
        self.assertIn(accepted.status, (0, 6))
        self.assertEqual(accepted.stderr_text, "")
        for malformed in ("A" * 64, "g" * 64):
            run = self.run_cli(
                "function",
                "verify",
                "verify-digest-grammar",
                "--expected-function-hash",
                malformed,
            )
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run)["error"], "invalid")

    def test_function_verify_rejects_an_unregistered_operation(self) -> None:
        run = self.run_cli("function", "verify", "absent")
        self.assertEqual(run.status, 3)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "not_found")

    def test_function_verify_does_not_cross_partition_or_like_colliding_scopes(self) -> None:
        self.register("check_1", partition="other")
        self.register("checkX1")
        self.register("Check_1")
        run = self.run_cli("function", "verify", "check_1")
        self.assertEqual(run.status, 3)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "not_found")
        positive = self.run_cli(
            "--partition", "other", "function", "verify", "check_1"
        )
        self.assertEqual(positive.status, 0)

    def test_function_verify_drafts_forwards_scope_positionally_and_actor_by_keyword(self) -> None:
        sentinel = DraftVerification(
            passed=True, operation_revision=13, entries=(), skipped=()
        )
        with mock.patch.object(System, "verify_drafts", autospec=True) as spy:
            spy.return_value = sentinel
            run = self.run_cli(
                "function", "verify-drafts", "echo_1", "--actor", " actor "
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.args[1:], ("tenant", "echo_1"))
        self.assertEqual(spy.call_args.kwargs, {"verified_by": " actor "})

    def test_function_verify_forwards_none_as_the_default_expected_hash(self) -> None:
        sentinel = FunctionVerification(
            passed=True,
            entries=0,
            document=None,
            function_hash=None,
            checks=(),
        )
        with mock.patch.object(System, "verify_function", autospec=True) as spy:
            spy.return_value = sentinel
            run = self.run_cli("function", "verify", "echo_1")
        self.assertEqual(run.status, 0)
        self.assertEqual(spy.call_args.args[1:], ("tenant", "echo_1"))
        self.assertEqual(spy.call_args.kwargs, {"expected_function_hash": None})

    def test_function_verify_forwards_the_expected_hash_byte_for_byte(self) -> None:
        supplied = "A" * 64
        sentinel = FunctionVerification(
            passed=False,
            entries=17,
            document=None,
            function_hash="c" * 64,
            checks=(FunctionCheck(key="probe", passed=False, detail="probe"),),
        )
        with mock.patch.object(System, "verify_function", autospec=True) as spy:
            spy.return_value = sentinel
            run = self.run_cli(
                "function",
                "verify",
                "echo_1",
                "--expected-function-hash",
                supplied,
            )
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(spy.call_args.args[1:], ("tenant", "echo_1"))
        self.assertEqual(
            spy.call_args.kwargs, {"expected_function_hash": supplied}
        )

    def test_function_verify_rejects_show_only_options(self) -> None:
        run = self.run_cli(
            "function", "verify", "echo", "--projection-limit", "5"
        )
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "invalid")

    def test_function_show_rejects_verify_drafts_only_options(self) -> None:
        run = self.run_cli("function", "show", "echo", "--actor", "x")
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "invalid")

    def test_root_verify_keeps_its_default_actor_while_function_verify_drafts_requires_one(self) -> None:
        missing_nested = self.run_cli("function", "verify-drafts", "echo")
        self.assertEqual(missing_nested.status, 2)
        with mock.patch.object(System, "verify", autospec=True) as spy:
            spy.return_value = VerificationReport(
                id="report_probe",
                artifact_id="art_probe",
                scope_hash="0" * 64,
                passed=True,
                tests=11,
                failures=(),
                created_at_us=13,
            )
            root = self.run_cli("verify", "art_probe")
        self.assertEqual(root.status, 0)
        self.assertEqual(spy.call_args.args[1:], ("tenant", "art_probe"))
        self.assertEqual(spy.call_args.kwargs, {"verified_by": "local-system"})

    def test_operation_register_keeps_its_exact_runner_bytes(self) -> None:
        run = self.run_cli(
            "operation",
            "register",
            "verify-regression",
            "--min-confirmations",
            "2",
            "--min-reviewers",
            "1",
            "--min-span-seconds",
            "0",
        )
        self.assertEqual(run.status, 0)
        self.assertEqual(
            run.stdout_bytes,
            b'{\n  "operation": "verify-regression",\n  "revision": 1\n}\n',
        )
        self.assertEqual(run.stderr_text, "")

    def test_function_verdicts_preserve_the_symbol_qualified_exit_map(self) -> None:
        verdict = FunctionVerification(
            passed=False,
            entries=19,
            document=None,
            function_hash="d" * 64,
            checks=(FunctionCheck(key="probe", passed=False, detail="negative"),),
        )
        cases: tuple[tuple[BaseException | None, int], ...] = (
            (ValidationError("invalid"), 2),
            (NotFoundError("missing"), 3),
            (StateError("state"), 4),
            (IntegrityError("integrity"), 5),
            (None, 6),
        )
        for exception, expected in cases:
            with self.subTest(expected=expected):
                replacement: typing.Any
                if exception is None:
                    replacement = mock.Mock(return_value=verdict)
                else:
                    replacement = mock.Mock(side_effect=exception)
                # Patching the library boundary keeps `_run`'s own status
                # branch under test; patching `_run` would replace it.
                with mock.patch.object(System, "verify_function", replacement):
                    run = self.run_cli("function", "verify", "echo")
                self.assertEqual(run.status, expected)
                if expected == 6:
                    self.assertEqual(run.stderr_text, "")
                    self.assertFalse(
                        typing.cast(dict[str, typing.Any], run.stdout_json)["passed"]
                    )
                else:
                    self.assertEqual(run.stdout_bytes, b"")
                    self.assertIsInstance(run.stderr_json, dict)

    def test_cli_run_shape_is_exact(self) -> None:
        self.assertTrue(_CLIRun.__dataclass_params__.frozen)
        self.assertIn("__slots__", _CLIRun.__dict__)
        self.assertEqual(
            [
                (name, parameter.kind.name, parameter.default)
                for name, parameter in inspect.signature(_CLIRun).parameters.items()
            ],
            [
                ("status", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
                ("stdout_text", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
                ("stdout_bytes", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
                ("stdout_json", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
                ("stderr_text", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
                ("stderr_json", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
            ],
        )
        self.assertEqual(
            typing.get_type_hints(_CLIRun),
            {
                "status": int,
                "stdout_text": str,
                "stdout_bytes": bytes,
                "stdout_json": object | None,
                "stderr_text": str,
                "stderr_json": object | None,
            },
        )
        runner = inspect.signature(CLITests.run_cli)
        self.assertEqual(
            [
                (name, parameter.kind.name, parameter.default)
                for name, parameter in runner.parameters.items()
            ],
            [
                ("self", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
                ("arguments", "VAR_POSITIONAL", inspect.Parameter.empty),
                ("text_only", "KEYWORD_ONLY", False),
            ],
        )
        self.assertEqual(
            typing.get_type_hints(CLITests.run_cli),
            {"arguments": str, "text_only": bool, "return": _CLIRun},
        )

    def test_function_inspect_projects_three_candidates_with_exact_schema(self) -> None:
        created = self.compile_drafts("inspect-candidates", (3, 12, 27))
        verified = self.payload(
            self.run_cli(
                "function", "verify-drafts", "inspect-candidates", "--actor", "verifier"
            )
        )
        run = self.run_cli("function", "inspect", "inspect-candidates")
        payload = self.payload(run)
        self.assertEqual(set(payload), _INSPECT_KEYS)
        self.assertEqual(payload["operation_revision"], 1)
        self.assertRegex(payload["function_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(payload["skipped"], [])
        self.assertEqual(len(payload["entries"]), 3)
        self.assertEqual(
            [entry["input_hash"] for entry in payload["entries"]],
            sorted(entry["input_hash"] for entry in payload["entries"]),
        )
        self.assertEqual(
            {entry["artifact_id"] for entry in payload["entries"]}, set(created)
        )
        self.assertEqual(
            {entry["entry_seal"] for entry in payload["entries"]},
            {entry["entry_seal"] for entry in verified["entries"]},
        )
        for entry in payload["entries"]:
            self.assertEqual(set(entry), _PROMOTION_ENTRY_KEYS)
            self.assertEqual(entry["disposition"], "candidate")
            self.assertIsNone(entry["replaces_artifact_id"])
            for key in ("artifact_hash", "input_hash", "output_hash", "entry_seal"):
                self.assertRegex(entry[key], r"^[0-9a-f]{64}$")
        for forbidden in ("text", "document", "value", "input_hashes", "_cases"):
            self.assertNotIn(forbidden, run.stdout_text)
        self.assertEqual(run.stderr_text, "")

    def test_function_inspect_reports_retained_and_displacing_candidate(self) -> None:
        self.promoted_operation("inspect-mixed", 2)
        before = System(self.database).inspect_function_promotion(
            "tenant", "inspect-mixed"
        )
        connection = sqlite3.connect(self.database)
        try:
            row = connection.execute(
                "SELECT input_json FROM artifacts WHERE id = ?",
                (before.entries[0].artifact_id,),
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(row)
        assert row is not None
        value = typing.cast(dict[str, int], json.loads(str(row[0])))
        challenged = self.payload(
            self.run_cli(
                "challenge",
                "inspect-mixed",
                "--input",
                json.dumps(value),
                "--expected",
                json.dumps({"kind": "echo", "value": value}),
                "--reviewer",
                "auditor",
                "--note",
                "same-output replacement build",
            )
        )
        self.assertFalse(challenged["suspended"])
        compiled = self.payload(self.run_cli("compile", "inspect-mixed"))["created"]
        self.assertEqual(len(compiled), 1)
        verified = self.run_cli(
            "function", "verify-drafts", "inspect-mixed", "--actor", "verifier"
        )
        self.assertEqual(verified.status, 0)

        run = self.run_cli("function", "inspect", "inspect-mixed")
        payload = self.payload(run)
        self.assertEqual(set(payload), _INSPECT_KEYS)
        self.assertEqual(len(payload["entries"]), 2)
        dispositions = [entry["disposition"] for entry in payload["entries"]]
        self.assertEqual(dispositions.count("retained"), 1)
        self.assertEqual(dispositions.count("candidate"), 1)
        candidate = next(
            entry for entry in payload["entries"] if entry["disposition"] == "candidate"
        )
        retained = next(
            entry for entry in payload["entries"] if entry["disposition"] == "retained"
        )
        self.assertEqual(candidate["artifact_id"], compiled[0])
        self.assertEqual(
            candidate["replaces_artifact_id"], before.entries[0].artifact_id
        )
        self.assertNotEqual(candidate["artifact_id"], candidate["replaces_artifact_id"])
        self.assertIn(
            retained["artifact_id"],
            {entry.artifact_id for entry in before.entries},
        )
        self.assertIsNone(retained["replaces_artifact_id"])
        self.assertEqual(run.stderr_text, "")

    def test_function_inspect_reports_an_empty_union_and_hash(self) -> None:
        self.register("inspect-empty")
        library = System(self.database).inspect_function_promotion(
            "tenant", "inspect-empty"
        )
        run = self.run_cli("function", "inspect", "inspect-empty")
        payload = self.payload(run)
        self.assertEqual(payload, {
            "entries": [],
            "function_hash": library.function_hash,
            "operation_revision": 1,
            "skipped": [],
        })
        self.assertRegex(payload["function_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(run.stderr_text, "")

    def test_function_inspect_ignores_unverified_drafts(self) -> None:
        created = self.compile_drafts("inspect-drafts", (4, 15, 26))
        self.assertEqual(len(created), 3)
        run = self.run_cli("function", "inspect", "inspect-drafts")
        payload = self.payload(run)
        self.assertEqual(set(payload), _INSPECT_KEYS)
        self.assertEqual(payload["entries"], [])
        self.assertEqual(payload["skipped"], [])
        self.assertRegex(payload["function_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(run.stderr_text, "")

    def test_function_inspect_reports_superseded_verified_build_verbatim(self) -> None:
        created = self.compile_drafts("inspect-skipped", (5, 16, 29))
        old = self.payload(
            self.run_cli(
                "function", "verify-drafts", "inspect-skipped", "--actor", "verifier"
            )
        )
        self.assertEqual(len(old["entries"]), 3)
        connection = sqlite3.connect(self.database)
        try:
            row = connection.execute(
                """
                SELECT input_json FROM artifacts WHERE id = ?
                """,
                (created[1],),
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(row)
        assert row is not None
        value = typing.cast(dict[str, int], json.loads(str(row[0])))
        self.handle_once(
            "inspect-skipped", value["x"], "inspect-skipped-extra", review=True
        )
        replacement = self.payload(self.run_cli("compile", "inspect-skipped"))["created"]
        self.assertEqual(len(replacement), 1)
        verified = self.payload(
            self.run_cli(
                "function", "verify-drafts", "inspect-skipped", "--actor", "verifier"
            )
        )
        self.assertEqual(len(verified["entries"]), 1)

        payload = self.payload(self.run_cli("function", "inspect", "inspect-skipped"))
        self.assertEqual(len(payload["entries"]), 3)
        self.assertEqual(len(payload["skipped"]), 1)
        skipped = payload["skipped"][0]
        self.assertEqual(set(skipped), _SKIPPED_KEYS)
        self.assertEqual(skipped["artifact_id"], created[1])
        self.assertEqual(skipped["reason"], "superseded-build")
        self.assertEqual(
            skipped["input_hash"],
            next(entry["input_hash"] for entry in old["entries"] if entry["artifact_id"] == created[1]),
        )
        self.assertNotIn(
            created[1], {entry["artifact_id"] for entry in payload["entries"]}
        )

    def test_function_inspect_scope_misses_are_not_found(self) -> None:
        for run in (
            self.run_cli("function", "inspect", "absent"),
            self.run_cli(
                "--partition", "tenantXa", "function", "inspect", "partitioned"
            ),
        ):
            self.assertEqual(run.status, 3)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(
                self.error(run),
                {
                    "error": "not_found",
                    "message": "operation is not registered in this partition",
                },
            )
        self.register("partitioned", partition="tenant_a")
        positive = self.run_cli(
            "--partition", "tenant_a", "function", "inspect", "partitioned"
        )
        self.assertEqual(positive.status, 0)

    def test_function_inspect_rejects_non_surface_options(self) -> None:
        for arguments, message in (
            (("--projection-limit", "5"), "unrecognized arguments: --projection-limit 5"),
            (("--receipt-id", "X"), "unrecognized arguments: --receipt-id X"),
        ):
            run = self.run_cli("function", "inspect", "echo", *arguments)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run), {"error": "invalid", "message": message})
        missing = self.run_cli("function", "inspect")
        self.assertEqual(missing.status, 2)
        self.assertEqual(missing.stdout_bytes, b"")
        self.assertEqual(
            self.error(missing),
            {"error": "invalid", "message": "the following arguments are required: operation"},
        )

    def test_function_inspect_forwards_scope_positionally(self) -> None:
        from cement_runtime.models import FunctionPromotionManifest

        sentinel = FunctionPromotionManifest(
            operation_revision=13,
            function_hash="a" * 64,
            text="private-manifest",
            document=mock.sentinel.document,
            entries=(),
            skipped=(),
        )
        with mock.patch.object(
            System, "inspect_function_promotion", autospec=True
        ) as spy:
            spy.return_value = sentinel
            run = self.run_cli("function", "inspect", "echo_1")
        self.assertEqual(run.status, 0)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.args[1:], ("tenant", "echo_1"))
        self.assertEqual(spy.call_args.kwargs, {})
        self.assertEqual(
            run.stdout_json,
            {
                "entries": [],
                "function_hash": "a" * 64,
                "operation_revision": 13,
                "skipped": [],
            },
        )
        self.assertNotIn("private-manifest", run.stdout_text)
        self.assertNotIn("document", run.stdout_text)

    def test_function_inspect_scope_matches_exactly(self) -> None:
        self.register("echo_1", partition="tenant_a")
        self.register("echoX1", partition="tenantXa")
        self.register("echoX1")
        self.register("Echo_1")
        positive = self.run_cli(
            "--partition", "tenant_a", "function", "inspect", "echo_1"
        )
        self.assertEqual(positive.status, 0)
        self.assertEqual(self.payload(positive)["operation_revision"], 1)
        for arguments in (
            ("function", "inspect", "echo_1"),
            ("--partition", "tenantXa", "function", "inspect", "echo_1"),
        ):
            run = self.run_cli(*arguments)
            self.assertEqual(run.status, 3)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(
                self.error(run),
                {
                    "error": "not_found",
                    "message": "operation is not registered in this partition",
                },
            )

    def test_function_inspect_is_byte_deterministic(self) -> None:
        created = self.compile_drafts("inspect-stable", (6, 17, 31))
        self.assertEqual(len(created), 3)
        verified = self.run_cli(
            "function", "verify-drafts", "inspect-stable", "--actor", "verifier"
        )
        self.assertEqual(verified.status, 0)
        first = self.run_cli("function", "inspect", "inspect-stable")
        second = self.run_cli("function", "inspect", "inspect-stable")
        self.assertEqual(first.status, 0)
        self.assertEqual(second.status, 0)
        self.assertEqual(first.stdout_bytes, second.stdout_bytes)
        self.assertEqual(first.stdout_json, second.stdout_json)
        self.assertEqual(first.stderr_text, "")
        self.assertEqual(second.stderr_text, "")

    def test_function_inspect_emits_the_tail_beyond_one_hundred_entries(self) -> None:
        from cement_runtime.models import Candidate, ReviewRequired

        class _Source:
            def propose(self, request: typing.Any) -> Candidate:
                return Candidate(
                    output={"kind": "echo", "value": request.input},
                    provenance={"model": "tail-fixture"},
                )

        operation = "inspect-tail"
        system = System(self.database, candidate_source=_Source())
        system.register_operation(
            "tenant",
            operation,
            policy=__import__("cement_runtime").CompilePolicy(2, 1, 0),
        )
        for index in range(121):
            for witness in (1, 2):
                outcome = system.propose("tenant", operation, {"x": index})
                system.review(
                    "tenant",
                    outcome,
                    reviewer=f"reviewer-{witness}",
                    decision="accept",
                )
        compiled = system.compile("tenant", operation)
        self.assertEqual(len(compiled.created), 121)
        verified = system.verify_drafts("tenant", operation, verified_by="verifier")
        self.assertTrue(verified.passed)
        expected = system.inspect_function_promotion("tenant", operation)
        sentinel = expected.entries[-1].artifact_id

        # One expensive fixture jointly pins unbounded projection, exact
        # cardinality, canonical order, and the load-bearing final loop member.
        payload = self.payload(self.run_cli("function", "inspect", operation))
        self.assertEqual(len(payload["entries"]), 121)
        self.assertEqual(
            [entry["artifact_id"] for entry in payload["entries"]],
            [entry.artifact_id for entry in expected.entries],
        )
        self.assertEqual(payload["entries"][-1]["artifact_id"], sentinel)
        self.assertEqual(payload["function_hash"], expected.function_hash)

    def test_function_inspect_corruption_maps_to_integrity(self) -> None:
        created = self.compile_drafts("inspect-corrupt", (7, 18, 33))
        verified = self.run_cli(
            "function", "verify-drafts", "inspect-corrupt", "--actor", "verifier"
        )
        self.assertEqual(verified.status, 0)
        self.corrupt_middle_draft(created)
        run = self.run_cli("function", "inspect", "inspect-corrupt")
        self.assertEqual(run.status, 5)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "integrity",
                "message": "artifact integrity failure: artifact document digest mismatch",
            },
        )


    def test_function_promote_round_trips_the_inspected_hash_and_exact_schema(self) -> None:
        created = self.compile_drafts("promote-roundtrip", (8, 19, 34))
        verified = self.run_cli(
            "function", "verify-drafts", "promote-roundtrip", "--actor", "verifier"
        )
        self.assertEqual(verified.status, 0)
        inspected = self.payload(
            self.run_cli("function", "inspect", "promote-roundtrip")
        )
        run = self.run_cli(
            "function",
            "promote",
            "promote-roundtrip",
            "--expected-function-hash",
            inspected["function_hash"],
            "--actor",
            " release-manager ",
        )
        payload = self.payload(run)
        self.assertEqual(set(payload), _PROMOTION_KEYS)
        self.assertRegex(payload["receipt_id"], r"^fpr_[0-9a-f]{32}$")
        self.assertRegex(payload["receipt_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(payload["function_hash"], inspected["function_hash"])
        self.assertEqual(payload["operation_revision"], 1)
        self.assertEqual(set(payload["member_artifact_ids"]), set(created))
        self.assertEqual(set(payload["candidate_artifact_ids"]), set(created))
        self.assertEqual(payload["retired_artifact_ids"], [])
        self.assertEqual(payload["member_artifact_ids"], sorted(created))
        self.assertEqual(payload["candidate_artifact_ids"], sorted(created))
        self.assertIs(type(payload["promoted_at_us"]), int)
        for forbidden in ("text", "document", "value", "input_hashes", "_cases"):
            self.assertNotIn(forbidden, run.stdout_text)
        self.assertEqual(run.stderr_text, "")
        history = self.payload(
            self.run_cli("function", "receipts", "promote-roundtrip")
        )
        self.assertEqual([row["id"] for row in history["receipts"]], [payload["receipt_id"]])
        self.assertEqual(history["receipts"][0]["promoted_by"], " release-manager ")

    def test_function_promote_rejects_stale_hash_after_qualifying_change(self) -> None:
        self.compile_drafts("promote-stale", (9, 20))
        first_verification = self.run_cli(
            "function", "verify-drafts", "promote-stale", "--actor", "verifier"
        )
        self.assertEqual(first_verification.status, 0)
        stale = self.payload(self.run_cli("function", "inspect", "promote-stale"))[
            "function_hash"
        ]
        self.confirm("promote-stale", 37, "promote-stale-new")
        created = self.payload(self.run_cli("compile", "promote-stale"))["created"]
        self.assertEqual(len(created), 1)
        fresh_verification = self.run_cli(
            "function", "verify-drafts", "promote-stale", "--actor", "verifier"
        )
        self.assertEqual(fresh_verification.status, 0)
        fresh = self.payload(self.run_cli("function", "inspect", "promote-stale"))[
            "function_hash"
        ]
        self.assertNotEqual(fresh, stale)
        run = self.run_cli(
            "function",
            "promote",
            "promote-stale",
            "--expected-function-hash",
            stale,
            "--actor",
            "release-manager",
        )
        self.assertEqual(run.status, 4)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "conflict",
                "message": "expected_function_hash does not match the locked prospective function",
            },
        )

    def test_function_promote_keeps_hash_after_nonqualifying_change(self) -> None:
        self.promoted_operation("promote-nonqualifying", 2)
        inspected = self.payload(
            self.run_cli("function", "inspect", "promote-nonqualifying")
        )
        self.handle_once(
            "promote-nonqualifying", 41, "promote-nonqualifying-once", review=True
        )
        repeated = self.payload(
            self.run_cli("function", "inspect", "promote-nonqualifying")
        )
        self.assertEqual(repeated["function_hash"], inspected["function_hash"])
        self.assertEqual(repeated["entries"], inspected["entries"])
        run = self.run_cli(
            "function",
            "promote",
            "promote-nonqualifying",
            "--expected-function-hash",
            inspected["function_hash"],
            "--actor",
            "release-manager",
        )
        payload = self.payload(run)
        self.assertEqual(set(payload), _PROMOTION_KEYS)
        self.assertEqual(payload["function_hash"], inspected["function_hash"])
        self.assertEqual(payload["candidate_artifact_ids"], [])
        self.assertEqual(payload["retired_artifact_ids"], [])
        self.assertEqual(len(payload["member_artifact_ids"]), 2)
        self.assertEqual(run.stderr_text, "")

    def test_function_promote_after_revision_reports_empty_set_message(self) -> None:
        self.promoted_operation("promote-revised", 2)
        stale = self.payload(self.run_cli("function", "inspect", "promote-revised"))[
            "function_hash"
        ]
        revised = self.payload(
            self.run_cli(
                "operation",
                "revise",
                "promote-revised",
                "--actor",
                "owner",
                "--min-confirmations",
                "3",
                "--min-reviewers",
                "2",
                "--min-span-seconds",
                "1",
            )
        )
        self.assertEqual(revised["revision"], 2)
        run = self.run_cli(
            "function",
            "promote",
            "promote-revised",
            "--expected-function-hash",
            stale,
            "--actor",
            "release-manager",
        )
        self.assertEqual(run.status, 4)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "conflict",
                "message": "function promotion requires at least one member",
            },
        )

    def test_function_promote_rejects_empty_union_from_inspect(self) -> None:
        self.register("promote-empty")
        inspected = self.payload(self.run_cli("function", "inspect", "promote-empty"))
        self.assertEqual(inspected["entries"], [])
        run = self.run_cli(
            "function",
            "promote",
            "promote-empty",
            "--expected-function-hash",
            inspected["function_hash"],
            "--actor",
            "release-manager",
        )
        self.assertEqual(run.status, 4)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "conflict",
                "message": "function promotion requires at least one member",
            },
        )

    def test_function_promote_rejects_digest_one_character_short_beside_accepted(self) -> None:
        self.register("promote-hash-short")
        accepted = self.run_cli(
            "function",
            "promote",
            "promote-hash-short",
            "--expected-function-hash",
            "0" * 64,
            "--actor",
            "release-manager",
        )
        self.assertEqual(accepted.status, 4)
        self.assertEqual(
            self.error(accepted),
            {
                "error": "conflict",
                "message": "function promotion requires at least one member",
            },
        )
        rejected = self.run_cli(
            "function",
            "promote",
            "promote-hash-short",
            "--expected-function-hash",
            "0" * 63,
            "--actor",
            "release-manager",
        )
        self.assertEqual(rejected.status, 2)
        self.assertEqual(rejected.stdout_bytes, b"")
        self.assertEqual(
            self.error(rejected),
            {
                "error": "invalid",
                "message": "expected_function_hash must be a SHA-256 hex digest",
            },
        )

    def test_function_promote_rejects_digest_one_character_long_beside_accepted(self) -> None:
        self.register("promote-hash-long")
        accepted = self.run_cli(
            "function",
            "promote",
            "promote-hash-long",
            "--expected-function-hash",
            "0" * 64,
            "--actor",
            "release-manager",
        )
        self.assertEqual(accepted.status, 4)
        self.assertEqual(
            self.error(accepted),
            {
                "error": "conflict",
                "message": "function promotion requires at least one member",
            },
        )
        rejected = self.run_cli(
            "function",
            "promote",
            "promote-hash-long",
            "--expected-function-hash",
            "0" * 65,
            "--actor",
            "release-manager",
        )
        self.assertEqual(rejected.status, 2)
        self.assertEqual(rejected.stdout_bytes, b"")
        self.assertEqual(
            self.error(rejected),
            {
                "error": "invalid",
                "message": "expected_function_hash must be a SHA-256 hex digest",
            },
        )

    def test_function_promote_rejects_uppercase_and_nonhex_hashes(self) -> None:
        self.register("promote-hash-grammar")
        for malformed in ("A" * 64, "g" * 64):
            run = self.run_cli(
                "function",
                "promote",
                "promote-hash-grammar",
                "--expected-function-hash",
                malformed,
                "--actor",
                "release-manager",
            )
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(
                self.error(run),
                {
                    "error": "invalid",
                    "message": "expected_function_hash must be a SHA-256 hex digest",
                },
            )

    def test_function_promote_requires_hash_and_actor(self) -> None:
        cases = (
            (
                ("function", "promote", "echo", "--actor", "release-manager"),
                "the following arguments are required: --expected-function-hash",
            ),
            (
                (
                    "function",
                    "promote",
                    "echo",
                    "--expected-function-hash",
                    "0" * 64,
                ),
                "the following arguments are required: --actor",
            ),
            (
                ("function", "promote", "echo"),
                "the following arguments are required: --expected-function-hash, --actor",
            ),
        )
        for arguments, message in cases:
            run = self.run_cli(*arguments)
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(self.error(run), {"error": "invalid", "message": message})

    def test_function_promote_scope_misses_are_not_found(self) -> None:
        self.register("promote-partitioned", partition="tenant_a")
        for run in (
            self.run_cli(
                "function",
                "promote",
                "absent",
                "--expected-function-hash",
                "0" * 64,
                "--actor",
                "release-manager",
            ),
            self.run_cli(
                "--partition",
                "tenantXa",
                "function",
                "promote",
                "promote-partitioned",
                "--expected-function-hash",
                "0" * 64,
                "--actor",
                "release-manager",
            ),
        ):
            self.assertEqual(run.status, 3)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(
                self.error(run),
                {
                    "error": "not_found",
                    "message": "operation is not registered in this partition",
                },
            )

    def test_function_promote_forwards_hash_and_actor_verbatim(self) -> None:
        from cement_runtime.models import FunctionSetPromotion

        supplied = " A" + "B" * 62 + " "
        actor = " release manager "
        sentinel = FunctionSetPromotion(
            receipt_id="fpr_probe",
            receipt_hash="b" * 64,
            function_hash="c" * 64,
            operation_revision=17,
            member_artifact_ids=("art_member",),
            candidate_artifact_ids=("art_member",),
            retired_artifact_ids=(),
            promoted_at_us=19,
        )
        with mock.patch.object(System, "promote_function", autospec=True) as spy:
            spy.return_value = sentinel
            run = self.run_cli(
                "function",
                "promote",
                "echo_1",
                "--expected-function-hash",
                supplied,
                "--actor",
                actor,
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.args[1:], ("tenant", "echo_1"))
        self.assertEqual(
            spy.call_args.kwargs,
            {"expected_function_hash": supplied, "promoted_by": actor},
        )
        self.assertEqual(set(typing.cast(dict[str, typing.Any], run.stdout_json)), _PROMOTION_KEYS)
        self.assertEqual(run.stderr_text, "")

    def test_function_promote_scope_matches_exactly(self) -> None:
        self.register("echo_1", partition="tenant_a")
        self.register("echoX1", partition="tenantXa")
        self.register("echoX1")
        self.register("Echo_1")
        correct_hash = System(self.database).inspect_function_promotion(
            "tenant_a", "echo_1"
        ).function_hash
        positive = self.run_cli(
            "--partition",
            "tenant_a",
            "function",
            "promote",
            "echo_1",
            "--expected-function-hash",
            correct_hash,
            "--actor",
            "release-manager",
        )
        self.assertEqual(positive.status, 4)
        self.assertEqual(
            self.error(positive),
            {
                "error": "conflict",
                "message": "function promotion requires at least one member",
            },
        )
        for arguments in (
            ("function", "promote", "echo_1"),
            ("--partition", "tenantXa", "function", "promote", "echo_1"),
        ):
            run = self.run_cli(
                *arguments,
                "--expected-function-hash",
                correct_hash,
                "--actor",
                "release-manager",
            )
            self.assertEqual(run.status, 3)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(
                self.error(run),
                {
                    "error": "not_found",
                    "message": "operation is not registered in this partition",
                },
            )

    def test_function_promote_maps_library_boundary_failures(self) -> None:
        cases: tuple[tuple[BaseException, int, str, str], ...] = (
            (ValidationError("invalid hash"), 2, "invalid", "invalid hash"),
            (NotFoundError("missing scope"), 3, "not_found", "missing scope"),
            (
                StateError("function promotion requires at least one member"),
                4,
                "conflict",
                "function promotion requires at least one member",
            ),
            (IntegrityError("corrupt ledger"), 5, "integrity", "corrupt ledger"),
        )
        for exception, status, error, message in cases:
            with self.subTest(message=message):
                with mock.patch.object(
                    System, "promote_function", side_effect=exception
                ) as spy:
                    run = self.run_cli(
                        "function",
                        "promote",
                        "echo",
                        "--expected-function-hash",
                        "0" * 64,
                        "--actor",
                        "release-manager",
                    )
                self.assertEqual(run.status, status)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run), {"error": error, "message": message}
                )
                self.assertEqual(spy.call_count, 1)

    def test_function_promote_corruption_maps_to_integrity(self) -> None:
        created = self.compile_drafts("promote-corrupt", (10, 21, 35))
        verified = self.run_cli(
            "function", "verify-drafts", "promote-corrupt", "--actor", "verifier"
        )
        self.assertEqual(verified.status, 0)
        expected = System(self.database).inspect_function_promotion(
            "tenant", "promote-corrupt"
        ).function_hash
        self.corrupt_middle_draft(created)
        run = self.run_cli(
            "function",
            "promote",
            "promote-corrupt",
            "--expected-function-hash",
            expected,
            "--actor",
            "release-manager",
        )
        self.assertEqual(run.status, 5)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "integrity",
                "message": "artifact integrity failure: artifact document digest mismatch",
            },
        )

    def test_function_hash_options_do_not_leak_between_nested_leaves(self) -> None:
        required_promote = self.run_cli("function", "promote", "echo", "--actor", "a")
        self.assertEqual(required_promote.status, 2)
        self.assertEqual(required_promote.stdout_bytes, b"")
        self.assertEqual(
            self.error(required_promote),
            {
                "error": "invalid",
                "message": "the following arguments are required: --expected-function-hash",
            },
        )
        optional_verify = self.run_cli("function", "verify", "echo")
        self.assertEqual(optional_verify.status, 3)
        self.assertEqual(optional_verify.stdout_bytes, b"")
        self.assertEqual(
            self.error(optional_verify),
            {
                "error": "not_found",
                "message": "operation is not registered in this partition",
            },
        )
        actor_on_verify = self.run_cli("function", "verify", "echo", "--actor", "a")
        self.assertEqual(actor_on_verify.status, 2)
        self.assertEqual(
            self.error(actor_on_verify),
            {"error": "invalid", "message": "unrecognized arguments: --actor a"},
        )
        actor_on_inspect = self.run_cli("function", "inspect", "echo", "--actor", "a")
        self.assertEqual(actor_on_inspect.status, 2)
        self.assertEqual(
            self.error(actor_on_inspect),
            {"error": "invalid", "message": "unrecognized arguments: --actor a"},
        )

    def test_root_promote_keeps_scope_hash_surface_and_exit_map(self) -> None:
        missing_actor = self.run_cli(
            "promote", "art_probe", "--scope-hash", "0" * 64
        )
        self.assertEqual(missing_actor.status, 2)
        self.assertEqual(missing_actor.stdout_bytes, b"")
        self.assertEqual(
            self.error(missing_actor),
            {"error": "invalid", "message": "the following arguments are required: --actor"},
        )
        # argparse reports missing required options before unrecognized ones, so
        # the root flag is only visibly rejected once the nested surface is satisfied.
        nested_option = self.run_cli(
            "function",
            "promote",
            "echo",
            "--expected-function-hash",
            "0" * 64,
            "--scope-hash",
            "0" * 64,
            "--actor",
            "release-manager",
        )
        self.assertEqual(nested_option.status, 2)
        self.assertEqual(nested_option.stdout_bytes, b"")
        self.assertEqual(
            self.error(nested_option),
            {
                "error": "invalid",
                "message": "unrecognized arguments: --scope-hash " + "0" * 64,
            },
        )
        with mock.patch.object(System, "promote", autospec=True) as spy:
            spy.side_effect = NotFoundError("artifact does not exist in this partition")
            root = self.run_cli(
                "promote",
                "art_probe",
                "--scope-hash",
                "0" * 64,
                "--actor",
                "release-manager",
            )
        self.assertEqual(root.status, 3)
        self.assertEqual(root.stdout_bytes, b"")
        self.assertEqual(
            self.error(root),
            {
                "error": "not_found",
                "message": "artifact does not exist in this partition",
            },
        )
        self.assertEqual(spy.call_args.args[1:], ("tenant", "art_probe"))
        self.assertEqual(
            spy.call_args.kwargs,
            {"scope_hash": "0" * 64, "promoted_by": "release-manager"},
        )

    def test_function_inspect_and_promote_return_bare_values(self) -> None:
        from cement_runtime.cli import _Outcome, _parser, _run
        from cement_runtime.models import FunctionPromotionManifest, FunctionSetPromotion

        parser = _parser()
        inspected = FunctionPromotionManifest(
            operation_revision=1,
            function_hash="a" * 64,
            text="private",
            document=mock.sentinel.document,
            entries=(),
            skipped=(),
        )
        promoted = FunctionSetPromotion(
            receipt_id="fpr_probe",
            receipt_hash="b" * 64,
            function_hash="a" * 64,
            operation_revision=1,
            member_artifact_ids=(),
            candidate_artifact_ids=(),
            retired_artifact_ids=(),
            promoted_at_us=1,
        )
        inspect_args = argparse.Namespace(
            command="function",
            function_command="inspect",
            db=self.database,
            partition="tenant",
            operation="echo",
        )
        with mock.patch.object(
            System, "inspect_function_promotion", return_value=inspected
        ):
            inspect_result = _run(inspect_args, parser)
        self.assertNotIsInstance(inspect_result, _Outcome)
        self.assertEqual(
            inspect_result,
            {
                "entries": [],
                "function_hash": "a" * 64,
                "operation_revision": 1,
                "skipped": [],
            },
        )
        promote_args = argparse.Namespace(
            command="function",
            function_command="promote",
            db=self.database,
            partition="tenant",
            operation="echo",
            expected_function_hash="a" * 64,
            actor="manager",
        )
        with mock.patch.object(System, "promote_function", return_value=promoted):
            promote_result = _run(promote_args, parser)
        self.assertIs(promote_result, promoted)
        self.assertNotIsInstance(promote_result, _Outcome)

    # -- function export -----------------------------------------------------

    def live_document(self, operation: str, *, partition: str = "tenant") -> str:
        verification = System(self.database).verify_function(partition, operation)
        self.assertTrue(verification.passed)
        assert verification.document is not None
        return verification.document.text

    def confirm_text(self, operation: str, value: str, tag: str) -> None:
        # `confirm` hardcodes integer inputs; the byte-exactness pins need a
        # corpus whose canonical text is non-ASCII.
        del tag  # see `confirm`: submission carries no request identity
        for _ in (1, 2):
            self.run_cli(
                "proposal",
                "review",
                self.submit(operation, {"x": value}),
                "--reviewer",
                "operator",
                "--decision",
                "accept",
            )

    def corrupt_receipt_membership(self, receipt_id: str) -> None:
        connection = sqlite3.connect(self.database)
        try:
            # Same fresh-System constraint as `corrupt_middle_draft`: the
            # immutability trigger has to be restored or the CLI exits 5 on the
            # schema fingerprint before it ever reads the row.
            trigger = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'trigger' AND name = 'function_memberships_no_update'
                """
            ).fetchone()[0]
            connection.execute("DROP TRIGGER function_memberships_no_update")
            connection.execute(
                """
                UPDATE function_memberships SET entry_seal = ?
                WHERE receipt_id = ? AND ordinal = 1
                """,
                ("0" * 64, receipt_id),
            )
            connection.execute(trigger)
            connection.commit()
        finally:
            connection.close()

    def test_function_export_writes_the_live_document_bytes_exactly(self) -> None:
        self.promoted_operation("echo", 2)
        expected = self.live_document("echo").encode("utf-8")
        run = self.run_cli("function", "export", "echo")
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_bytes, expected)
        self.assertFalse(run.stdout_bytes.endswith(b"\n"))
        self.assertEqual(run.stderr_text, "")
        # The same bytes reach a host with no `.buffer`, through the text path.
        text_host = self.run_cli("function", "export", "echo", text_only=True)
        self.assertEqual(text_host.stdout_bytes, expected)
        self.assertEqual(text_host.status, 0)

    def test_function_export_round_trips_through_parse_function(self) -> None:
        from cement_runtime import evaluate, parse_function
        from cement_runtime.json_value import canonicalize

        self.promoted_operation("echo", 2)
        run = self.run_cli("function", "export", "echo")
        parsed = parse_function(run.stdout_text)
        verification = System(self.database).verify_function("tenant", "echo")
        self.assertEqual(parsed.function_hash, verification.function_hash)
        match = evaluate(parsed, input_json=canonicalize({"x": 1}))
        self.assertTrue(match.matched)
        self.assertEqual(match.output, {"kind": "echo", "value": {"x": 1}})
        miss = evaluate(parsed, input_json=canonicalize({"x": 4}))
        self.assertFalse(miss.matched)

    def test_function_export_emits_non_ascii_literally(self) -> None:
        self.register("unicode")
        self.confirm_text("unicode", "Grüße 日本語", "unicode-a")
        self.run_cli("compile", "unicode")
        self.promote_set("unicode")
        run = self.run_cli("function", "export", "unicode")
        self.assertEqual(run.status, 0)
        self.assertIn("Grüße 日本語", run.stdout_text)
        self.assertNotIn("\\u", run.stdout_text)
        self.assertGreater(len(run.stdout_bytes), len(run.stdout_text))
        self.assertEqual(run.stdout_bytes, self.live_document("unicode").encode("utf-8"))

    def test_function_export_of_an_empty_promoted_set_exports_its_document(self) -> None:
        self.register("empty")
        run = self.run_cli("function", "export", "empty")
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(run.stdout_bytes, self.live_document("empty").encode("utf-8"))
        document = typing.cast(dict[str, typing.Any], json.loads(run.stdout_text))
        self.assertEqual(document["entries"], [])
        self.assertEqual(document["abi"], "cement-function-v2")
        self.assertEqual(document["scope"]["operation"], "empty")

    def test_function_export_refuses_a_drifted_set_with_the_whole_check_vector(self) -> None:
        self.promoted_operation("echo", 2)
        anchor = self.payload(self.run_cli("function", "show", "echo"))["function_anchor"]
        member = str(anchor["members"][0]["artifact_id"])
        self.run_cli("artifact", "suspend", member, "--actor", "operator", "--reason", "drift")
        run = self.run_cli("function", "export", "echo")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stdout_bytes, b"")
        failure = self.error(run)
        self.assertEqual(set(failure), {"checks", "error", "message"})
        self.assertEqual(failure["error"], "unverified")
        checks = typing.cast(list[dict[str, typing.Any]], failure["checks"])
        self.assertEqual(
            [check["key"] for check in checks],
            [
                "duplicate-input-digests",
                "abi-canonicalizer-uniform",
                "sealed-passing-reports",
                "current-promotion-receipts",
                "function-hash-matches-snapshot",
                "persisted-function-receipt",
            ],
        )
        self.assertEqual([check["passed"] for check in checks], [True] * 5 + [False])
        self.assertEqual(set(checks[0]), {"detail", "key", "passed"})
        self.assertEqual(
            failure["message"],
            "function verification failed; no bundle exported: persisted-function-receipt: "
            "latest receipt does not bind the promoted snapshot",
        )

    def test_function_export_message_names_every_failing_check_in_order(self) -> None:
        verdict = FunctionVerification(
            passed=False,
            entries=3,
            document=None,
            function_hash="c" * 64,
            checks=(
                FunctionCheck(key="first", passed=False, detail="one failed"),
                FunctionCheck(key="second", passed=True, detail="two held"),
                FunctionCheck(key="third", passed=False, detail="three failed"),
            ),
        )
        with mock.patch.object(System, "verify_function", return_value=verdict):
            run = self.run_cli("function", "export", "echo")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stdout_bytes, b"")
        failure = self.error(run)
        self.assertEqual(
            failure["message"],
            "function verification failed; no bundle exported: first: one failed; "
            "third: three failed",
        )
        checks = typing.cast(list[dict[str, typing.Any]], failure["checks"])
        self.assertEqual([check["key"] for check in checks], ["first", "second", "third"])
        self.assertNotIn("function_hash", failure)
        self.assertNotIn("entries", failure)

    def test_unverified_stays_outside_the_cement_error_hierarchy(self) -> None:
        from cement_runtime.cli import _Unverified
        from cement_runtime.errors import CementError

        # Inheriting CementError would put every refused export inside main's
        # residual clause and silently downgrade exit 6 to exit 2.
        self.assertTrue(issubclass(_Unverified, Exception))
        self.assertFalse(issubclass(_Unverified, CementError))
        self.assertEqual(str(_Unverified({"message": "carried"})), "carried")

    def test_function_export_preserves_the_symbol_qualified_exit_map(self) -> None:
        verdict = FunctionVerification(
            passed=False,
            entries=1,
            document=None,
            function_hash="d" * 64,
            checks=(FunctionCheck(key="probe", passed=False, detail="negative"),),
        )
        cases: tuple[tuple[BaseException | None, int], ...] = (
            (ValidationError("invalid"), 2),
            (NotFoundError("missing"), 3),
            (StateError("state"), 4),
            (IntegrityError("integrity"), 5),
            (None, 6),
        )
        for exception, expected in cases:
            with self.subTest(expected=expected):
                replacement: typing.Any
                if exception is None:
                    replacement = mock.Mock(return_value=verdict)
                else:
                    replacement = mock.Mock(side_effect=exception)
                # Patch the library boundary; patching `_run` would replace the
                # branch under test.
                with mock.patch.object(System, "verify_function", replacement):
                    run = self.run_cli("function", "export", "echo")
                self.assertEqual(run.status, expected)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertIsInstance(run.stderr_json, dict)
                self.assertEqual(
                    self.error(run)["error"],
                    "unverified" if expected == 6 else self.error(run)["error"],
                )

    def test_function_export_rejects_an_unregistered_or_foreign_operation(self) -> None:
        self.promoted_operation("echo_1", 2)
        for arguments, partition in (
            (("function", "export", "ghost"), "tenant"),
            (("function", "export", "echo_1"), "tenant_other"),
        ):
            run = self.run_cli("--partition", partition, *arguments)
            self.assertEqual(run.status, 3)
            self.assertEqual(run.stdout_bytes, b"")
            self.assertEqual(
                self.error(run),
                {
                    "error": "not_found",
                    "message": "operation is not registered in this partition",
                },
            )

    def test_function_export_exports_one_historical_receipt(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        reconstruction = System(self.database).reconstruct_function_receipt("tenant", receipt)
        with mock.patch.object(System, "verify_function") as never:
            run = self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.assertEqual(never.call_count, 0)
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(run.stdout_bytes, reconstruction.document.text.encode("utf-8"))
        self.assertFalse(run.stdout_bytes.endswith(b"\n"))

    def test_function_export_cross_checks_the_receipt_operation_exactly(self) -> None:
        receipt = self.promoted_operation("echo_1", 2)
        accepted = self.run_cli("function", "export", "echo_1", "--receipt-id", receipt)
        self.assertEqual(accepted.status, 0)
        for operation in ("echoX1", "ECHO_1", "echo", "echo_12"):
            with self.subTest(operation=operation):
                run = self.run_cli("function", "export", operation, "--receipt-id", receipt)
                self.assertEqual(run.status, 3)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run),
                    {
                        "error": "not_found",
                        "message": "function receipt does not exist for this operation",
                    },
                )

    def test_function_export_reports_a_missing_receipt_row_separately(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        for partition, receipt_id in (
            ("tenant", "fpr_" + "0" * 32),
            ("tenant", "not-an-id"),
            ("tenant", "req_" + "0" * 32),
            ("tenant_other", receipt),
        ):
            with self.subTest(partition=partition, receipt_id=receipt_id):
                run = self.run_cli(
                    "--partition", partition, "function", "export", "echo", "--receipt-id", receipt_id
                )
                self.assertEqual(run.status, 3)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run),
                    {
                        "error": "not_found",
                        "message": "function receipt does not exist in this partition",
                    },
                )

    def test_function_export_bounds_the_receipt_id_grammar(self) -> None:
        self.promoted_operation("echo", 2)
        for receipt_id in ("", "a" * 193, "fpr_x!y"):
            with self.subTest(receipt_id=receipt_id):
                run = self.run_cli("function", "export", "echo", "--receipt-id", receipt_id)
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run),
                    {
                        "error": "invalid",
                        "message": "request_id must be a bounded ASCII identifier",
                    },
                )
        # Adjacent accept side: the maximum-length id is grammar-valid and
        # therefore reaches lookup, which is a not_found rather than an invalid.
        accepted = self.run_cli("function", "export", "echo", "--receipt-id", "a" * 192)
        self.assertEqual(accepted.status, 3)
        self.assertEqual(self.error(accepted)["error"], "not_found")

    def test_function_export_reports_a_corrupt_receipt_as_integrity(self) -> None:
        self.promoted_operation("echo_1", 2)
        receipt = self.promoted_operation("beta", 2)
        self.corrupt_receipt_membership(receipt)
        for operation in ("beta", "echo_1"):
            with self.subTest(operation=operation):
                # Reconstruction precedes the operation cross-check, so a
                # corrupt foreign receipt reports corruption, not not_found.
                run = self.run_cli("function", "export", operation, "--receipt-id", receipt)
                self.assertEqual(run.status, 5)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run),
                    {
                        "error": "integrity",
                        "message": "function receipt membership digest mismatch",
                    },
                )

    def test_function_export_guards_a_passing_verification_without_a_document(self) -> None:
        verdict = FunctionVerification(
            passed=True,
            entries=0,
            document=None,
            function_hash="e" * 64,
            checks=(FunctionCheck(key="probe", passed=True, detail="held"),),
        )
        with mock.patch.object(System, "verify_function", return_value=verdict):
            run = self.run_cli("function", "export", "echo")
        self.assertEqual(run.status, 5)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "integrity",
                "message": "function verification passed without an exportable document",
            },
        )

    def test_function_export_forwards_the_operator_scope_exactly(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        document = System(self.database).verify_function("tenant", "echo")
        with mock.patch.object(
            System, "verify_function", autospec=True, return_value=document
        ) as live:
            self.run_cli("function", "export", "echo")
        self.assertEqual(live.call_args.args[1:], ("tenant", "echo"))
        self.assertEqual(live.call_args.kwargs, {})
        reconstruction = System(self.database).reconstruct_function_receipt("tenant", receipt)
        with mock.patch.object(
            System,
            "reconstruct_function_receipt",
            autospec=True,
            return_value=reconstruction,
        ) as historical:
            self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.assertEqual(historical.call_args.args[1:], ("tenant", receipt))
        self.assertEqual(historical.call_args.kwargs, {})

    def test_function_export_sources_never_mix(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        historical = self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.confirm("echo", 99, "echo-grown")
        self.run_cli("compile", "echo")
        self.promote_set("echo")
        live = self.run_cli("function", "export", "echo")
        self.assertEqual(live.status, 0)
        self.assertNotEqual(live.stdout_bytes, historical.stdout_bytes)
        self.assertEqual(len(json.loads(historical.stdout_text)["entries"]), 2)
        self.assertEqual(len(json.loads(live.stdout_text)["entries"]), 3)
        # The older receipt keeps exporting its own immutable bytes.
        again = self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.assertEqual(again.stdout_bytes, historical.stdout_bytes)

    def test_function_export_serves_a_receipt_from_a_superseded_revision(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        historical = self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.assertEqual(historical.status, 0)
        revised = self.payload(
            self.run_cli(
                "operation",
                "revise",
                "echo",
                "--min-confirmations",
                "3",
                "--min-reviewers",
                "1",
                "--min-span-seconds",
                "0",
                "--actor",
                "owner",
            )
        )
        self.assertEqual(revised["revision"], 2)
        after = self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.assertEqual(after.status, 0)
        self.assertEqual(after.stdout_bytes, historical.stdout_bytes)
        live = self.run_cli("function", "export", "echo")
        self.assertEqual(live.status, 0)
        self.assertNotEqual(live.stdout_bytes, historical.stdout_bytes)
        self.assertEqual(json.loads(live.stdout_text)["scope"]["operation_revision"], 2)

    def test_function_export_grades_the_operation_by_grammar_on_both_sources(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        # An unset shell variable produces the empty operation, so both sources
        # must call it a usage error rather than a missing receipt.
        for operation in ("", "♥", ".leading", "a" * 129):
            for arguments in ((), ("--receipt-id", receipt)):
                with self.subTest(operation=operation, historical=bool(arguments)):
                    run = self.run_cli("function", "export", operation, *arguments)
                    self.assertEqual(run.status, 2)
                    self.assertEqual(run.stdout_bytes, b"")
                    self.assertEqual(
                        self.error(run),
                        {
                            "error": "invalid",
                            "message": "operation must be 1-128 ASCII letters, digits, "
                            "'.', '_', ':', '/', or '-'",
                        },
                    )
        # Adjacent accept side: the maximum-length operation is grammar-valid
        # and therefore reaches the receipt comparison.
        accepted = self.run_cli(
            "function", "export", "a" * 128, "--receipt-id", receipt
        )
        self.assertEqual(accepted.status, 3)
        self.assertEqual(
            self.error(accepted)["message"],
            "function receipt does not exist for this operation",
        )

    def test_function_export_reports_the_whole_capacity_vector(self) -> None:
        keys = (
            "duplicate-input-digests",
            "abi-canonicalizer-uniform",
            "sealed-passing-reports",
            "current-promotion-receipts",
            "function-hash-matches-snapshot",
            "persisted-function-receipt",
        )
        detail = "not evaluated because 50001 promoted entries exceed FUNCTION_MAX_ENTRIES=50000"
        verdict = FunctionVerification(
            passed=False,
            entries=50_001,
            document=None,
            function_hash=None,
            checks=tuple(FunctionCheck(key=key, passed=False, detail=detail) for key in keys),
        )
        with mock.patch.object(System, "verify_function", return_value=verdict):
            run = self.run_cli("function", "export", "echo")
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stdout_bytes, b"")
        failure = self.error(run)
        self.assertEqual(set(failure), {"checks", "error", "message"})
        checks = typing.cast(list[dict[str, typing.Any]], failure["checks"])
        self.assertEqual([check["key"] for check in checks], list(keys))
        self.assertEqual([check["passed"] for check in checks], [False] * 6)
        self.assertEqual(
            failure["message"],
            "function verification failed; no bundle exported: "
            + "; ".join(f"{key}: {detail}" for key in keys),
        )

    def test_function_export_rejects_options_it_does_not_own(self) -> None:
        for arguments, message in (
            (
                ("--expected-function-hash", "a" * 64),
                f"unrecognized arguments: --expected-function-hash {'a' * 64}",
            ),
            (("--projection-limit", "5"), "unrecognized arguments: --projection-limit 5"),
        ):
            with self.subTest(arguments=arguments):
                run = self.run_cli("function", "export", "echo", *arguments)
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(self.error(run), {"error": "invalid", "message": message})
        missing = self.run_cli("function", "export")
        self.assertEqual(missing.status, 2)
        self.assertEqual(missing.stdout_bytes, b"")
        self.assertEqual(
            self.error(missing),
            {"error": "invalid", "message": "the following arguments are required: operation"},
        )

    # `function export --out`: the atomic file channel.

    def export_root(self) -> pathlib.Path:
        return pathlib.Path(self.temporary.name).resolve()

    def temps(self, directory: pathlib.Path) -> list[str]:
        # Writer temps carry a leading dot; nothing else in the fixture does.
        return sorted(entry.name for entry in directory.glob(".*"))

    def test_function_export_out_writes_the_exact_bundle_and_reports_it(self) -> None:
        self.promoted_operation("echo", 2)
        expected = self.live_document("echo").encode("utf-8")
        root = self.export_root()
        destination = root / "bundle.json"
        run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(destination.read_bytes(), expected)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
        self.assertEqual(self.temps(root), [])
        payload = self.payload(run)
        self.assertEqual(set(payload), {"bytes", "function_hash", "out"})
        self.assertEqual(payload["out"], str(destination))
        self.assertEqual(payload["bytes"], len(expected))
        document = typing.cast(dict[str, typing.Any], json.loads(expected.decode("utf-8")))
        self.assertEqual(payload["function_hash"], document["function_hash"])
        # The bundle itself never reaches stdout on this channel.
        self.assertNotIn(b"cement-function-v2", run.stdout_bytes)

    def test_function_export_out_replaces_an_existing_destination(self) -> None:
        self.promoted_operation("echo", 2)
        expected = self.live_document("echo").encode("utf-8")
        root = self.export_root()
        destination = root / "bundle.json"
        destination.write_bytes(b"previous-bundle")
        os.chmod(destination, 0o644)
        run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        self.assertEqual(destination.read_bytes(), expected)
        # Replacement installs the temp's inode, so the previous mode is not kept.
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
        self.assertEqual(self.temps(root), [])

    def test_function_export_out_never_exposes_a_partial_destination(self) -> None:
        self.promoted_operation("echo", 2)
        expected = self.live_document("echo").encode("utf-8")
        root = self.export_root()
        destination = root / "bundle.json"
        destination.write_bytes(b"previous-bundle")
        observed: list[bytes] = []
        replace = os.replace

        def watching(source: typing.Any, target: typing.Any) -> None:
            observed.append(pathlib.Path(target).read_bytes())
            replace(source, target)

        with mock.patch("cement_runtime.cli.os.replace", watching):
            run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        # The payload is fully written and fsynced before the rename, and at that
        # moment the destination still holds the old bytes: never a prefix.
        self.assertEqual(observed, [b"previous-bundle"])
        self.assertEqual(destination.read_bytes(), expected)

    def test_function_export_out_never_writes_through_the_destination_name(self) -> None:
        self.promoted_operation("echo", 2)
        expected = self.live_document("echo").encode("utf-8")
        root = self.export_root()
        # A name that reproduces its own temp: the prefix caps at 64 characters,
        # so `. + 64 dots + .` is the leading 66 dots, and a draw of the trailing
        # 12 characters names the destination itself.
        collision = os.urandom(6)
        destination = root / ("." * 66 + collision.hex())
        draws: list[int] = []
        urandom = os.urandom

        def drawing(size: int) -> bytes:
            draws.append(size)
            return collision if len(draws) == 1 else urandom(size)

        existed: list[bool] = []
        replace = os.replace

        def watching(source: typing.Any, target: typing.Any) -> None:
            existed.append(pathlib.Path(target).exists())
            replace(source, target)

        with mock.patch("cement_runtime.cli.os.urandom", drawing):
            with mock.patch("cement_runtime.cli.os.replace", watching):
                run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        # The colliding draw is discarded before anything is created, so the
        # destination is still absent when the finished bundle is renamed onto it.
        self.assertEqual(draws, [6, 6])
        self.assertEqual(existed, [False])
        self.assertEqual(destination.read_bytes(), expected)
        self.assertEqual(self.temps(root), [destination.name])

    def test_function_export_out_rechecks_the_destination_before_replacing(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        referent = root / "referent"
        referent.write_bytes(b"referent-bytes")
        verify_function = System.verify_function

        def racing(self_: typing.Any, *arguments: typing.Any, **keywords: typing.Any) -> typing.Any:
            # The destination turns into a symlink after the structural check and
            # before the writer runs; only the recheck can still catch it.
            destination.symlink_to(referent)
            return verify_function(self_, *arguments, **keywords)

        with mock.patch.object(System, "verify_function", racing):
            run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {
                "error": "invalid",
                "message": "export output path must identify a non-symlink regular file",
            },
        )
        self.assertTrue(destination.is_symlink())
        self.assertEqual(referent.read_bytes(), b"referent-bytes")
        self.assertEqual(self.temps(root), [])

    def test_function_export_out_checks_the_destination_with_one_stat_each_time(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        observed: list[str] = []
        lstat = os.lstat

        def counting(path: typing.Any, **keywords: typing.Any) -> os.stat_result:
            if os.fspath(path) == str(destination):
                observed.append("lstat")
            return lstat(path, **keywords)

        with mock.patch("cement_runtime.cli.os.lstat", counting):
            run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        # Two checks, one syscall each. A chain of `Path` predicates would spend
        # several syscalls per check and admit a link installed between two of
        # them, which is the case the guard exists to refuse.
        self.assertEqual(observed, ["lstat", "lstat"])

    def test_function_export_out_rejects_unusable_destinations(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        regular = root / "regular"
        regular.write_bytes(b"regular")
        directory = root / "directory"
        directory.mkdir()
        referent = root / "referent"
        referent.write_bytes(b"referent-bytes")
        link = root / "link"
        link.symlink_to(referent)
        dangling = root / "dangling"
        dangling.symlink_to(root / "absent")
        fifo = root / "fifo"
        os.mkfifo(fifo)
        locked = root / "locked"
        locked.mkdir()
        os.chmod(locked, 0o500)
        self.addCleanup(os.chmod, locked, 0o700)
        blocked = root / "blocked"
        (blocked / "child").mkdir(parents=True)
        os.chmod(blocked, 0o000)
        self.addCleanup(os.chmod, blocked, 0o700)
        unusable = "export output path must identify a non-symlink regular file"
        absent = "export output directory does not exist"
        unsafe = "export output could not be written safely"
        separator = "export output path must not end with a directory separator"
        cases: tuple[tuple[str, str, str], ...] = (
            # `Path` drops a trailing separator, so these two would otherwise
            # grade as the bare name: the first replaces a regular file the
            # caller asserted was a directory, the second creates one.
            ("regular-file-with-a-trailing-slash", str(regular) + "/", separator),
            ("absent-name-with-a-trailing-slash", str(root / "absent-dir") + "/", separator),
            ("parent-missing", str(root / "missing" / "bundle.json"), absent),
            ("parent-is-a-regular-file", str(regular / "bundle.json"), absent),
            ("target-is-a-directory", str(directory), unusable),
            ("target-is-a-symlink", str(link), unusable),
            ("target-is-a-dangling-symlink", str(dangling), unusable),
            ("target-is-a-fifo", str(fifo), unusable),
            ("empty-path", "", unusable),
            ("parent-is-unwritable", str(locked / "bundle.json"), unsafe),
            # A search-denied ancestor makes the structural predicates themselves
            # raise EACCES, which `main` maps only once this leaf translates it.
            ("ancestor-is-search-denied", str(blocked / "child" / "bundle.json"), unsafe),
            ("path-contains-nul", str(root / "bundle") + "\0x", unsafe),
            ("path-contains-a-lone-surrogate", str(root / "\ud800"), unsafe),
        )
        for label, destination, message in cases:
            with self.subTest(case=label):
                run = self.run_cli("function", "export", "echo", "--out", destination)
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(self.error(run), {"error": "invalid", "message": message})
                self.assertEqual(self.temps(root), [])
        self.assertEqual(regular.read_bytes(), b"regular")
        self.assertFalse((root / "absent-dir").exists())
        self.assertTrue(link.is_symlink())
        self.assertEqual(referent.read_bytes(), b"referent-bytes")
        self.assertTrue(dangling.is_symlink())
        self.assertFalse((root / "absent").exists())
        self.assertTrue(stat.S_ISFIFO(os.stat(fifo).st_mode))
        self.assertEqual(list(directory.iterdir()), [])

    def test_function_export_out_bounds_the_target_name_at_the_filesystem_maximum(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        maximum = os.pathconf(str(root), "PC_NAME_MAX")
        accepted = root / ("A" * maximum)
        run = self.run_cli("function", "export", "echo", "--out", str(accepted))
        self.assertEqual(run.status, 0)
        self.assertEqual(accepted.read_bytes(), self.live_document("echo").encode("utf-8"))
        self.assertEqual(self.temps(root), [])
        # The temp prefix is capped so `prefix + suffix` stays inside NAME_MAX;
        # uncapped, this accepted maximum fails instead. One character above it
        # is the adjacent rejection.
        rejected = self.run_cli(
            "function", "export", "echo", "--out", str(root / ("A" * (maximum + 1)))
        )
        self.assertEqual(rejected.status, 2)
        self.assertEqual(
            self.error(rejected),
            {"error": "invalid", "message": "export output could not be written safely"},
        )
        self.assertEqual(self.temps(root), [])

    def test_function_export_out_keeps_mode_0600_under_a_permissive_umask(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        previous = os.umask(0o777)
        self.addCleanup(os.umask, previous)
        run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        # `mkstemp` requests 0600 and the kernel applies the umask, so without an
        # explicit fchmod this file lands at 0o000.
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)

    def test_function_export_out_translates_write_failures_and_keeps_the_old_bytes(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        destination.write_bytes(b"previous-bundle")
        failures: tuple[tuple[str, str, BaseException], ...] = (
            ("fsync", "cement_runtime.cli.os.fsync", OSError(errno.ENOSPC, "No space left")),
            ("replace", "cement_runtime.cli.os.replace", OSError(errno.EACCES, "Permission denied")),
        )
        for label, target, failure in failures:
            with self.subTest(stage=label):
                with mock.patch(target, side_effect=failure):
                    run = self.run_cli("function", "export", "echo", "--out", str(destination))
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run),
                    {"error": "invalid", "message": "export output could not be written safely"},
                )
                self.assertEqual(destination.read_bytes(), b"previous-bundle")
                self.assertEqual(self.temps(root), [])

    def test_function_export_out_exports_one_historical_receipt(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        expected = self.run_cli("function", "export", "echo", "--receipt-id", receipt).stdout_bytes
        run = self.run_cli(
            "function", "export", "echo", "--receipt-id", receipt, "--out", str(destination)
        )
        self.assertEqual(run.status, 0)
        self.assertEqual(destination.read_bytes(), expected)
        payload = self.payload(run)
        self.assertEqual(payload["bytes"], len(expected))
        document = typing.cast(dict[str, typing.Any], json.loads(expected.decode("utf-8")))
        self.assertEqual(payload["function_hash"], document["function_hash"])

    def test_function_export_out_writes_non_ascii_as_exact_utf8(self) -> None:
        self.register("unicode")
        self.confirm_text("unicode", "Grüße 日本語", "unicode-a")
        self.run_cli("compile", "unicode")
        self.promote_set("unicode")
        root = self.export_root()
        destination = root / "bundle.json"
        run = self.run_cli("function", "export", "unicode", "--out", str(destination))
        self.assertEqual(run.status, 0)
        written = destination.read_bytes()
        self.assertEqual(written, self.live_document("unicode").encode("utf-8"))
        self.assertIn("Grüße 日本語", written.decode("utf-8"))
        self.assertNotIn("\\u", written.decode("utf-8"))
        payload = self.payload(run)
        self.assertEqual(payload["bytes"], len(written))
        # The byte count is the written length, not the character count.
        self.assertGreater(payload["bytes"], len(written.decode("utf-8")))

    def test_function_export_out_writes_the_empty_promoted_document(self) -> None:
        self.register("empty")
        root = self.export_root()
        destination = root / "bundle.json"
        run = self.run_cli("function", "export", "empty", "--out", str(destination))
        self.assertEqual(run.status, 0)
        written = destination.read_bytes()
        self.assertEqual(written, self.live_document("empty").encode("utf-8"))
        document = typing.cast(dict[str, typing.Any], json.loads(written.decode("utf-8")))
        self.assertEqual(document["entries"], [])
        self.assertEqual(self.payload(run)["bytes"], len(written))

    def test_function_export_out_round_trips_through_parse_function(self) -> None:
        from cement_runtime import evaluate, parse_function
        from cement_runtime.json_value import canonicalize

        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        run = self.run_cli("function", "export", "echo", "--out", str(destination))
        parsed = parse_function(destination.read_bytes().decode("utf-8"))
        self.assertEqual(parsed.function_hash, self.payload(run)["function_hash"])
        match = evaluate(parsed, input_json=canonicalize({"x": 1}))
        self.assertTrue(match.matched)
        self.assertEqual(match.output, {"kind": "echo", "value": {"x": 1}})

    def test_function_export_out_and_stdout_carry_identical_bytes(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        piped = self.run_cli("function", "export", "echo")
        written = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(piped.status, 0)
        self.assertEqual(written.status, 0)
        self.assertEqual(destination.read_bytes(), piped.stdout_bytes)
        self.assertEqual(self.payload(written)["bytes"], len(piped.stdout_bytes))

    def test_function_export_out_treats_a_bare_dash_as_a_filename(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "-"
        run = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(run.status, 0)
        # `--out` selects a path, never a stream: `-` is an ordinary filename.
        self.assertTrue(destination.is_file())
        self.assertEqual(destination.read_bytes(), self.live_document("echo").encode("utf-8"))
        self.assertNotIn(b"cement-function-v2", run.stdout_bytes)

    def test_function_export_out_reports_the_resolved_destination(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        actual = root / "actual"
        actual.mkdir()
        alias = root / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        argument = str(alias / "bundle.json")
        run = self.run_cli("function", "export", "echo", "--out", argument)
        self.assertEqual(run.status, 0)
        reported = self.payload(run)["out"]
        # The reported path names the file that received the bytes, so it resolves
        # a symlinked parent instead of echoing the lexical argument back.
        self.assertEqual(reported, str(actual / "bundle.json"))
        self.assertNotEqual(reported, os.path.abspath(argument))
        self.assertTrue((actual / "bundle.json").is_file())

    def test_function_export_out_resolves_a_relative_destination_against_the_cwd(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        previous = pathlib.Path.cwd()
        os.chdir(root)
        self.addCleanup(os.chdir, previous)
        run = self.run_cli("function", "export", "echo", "--out", "bundle.json")
        self.assertEqual(run.status, 0)
        self.assertEqual(self.payload(run)["out"], str(root / "bundle.json"))
        self.assertEqual(
            (root / "bundle.json").read_bytes(), self.live_document("echo").encode("utf-8")
        )

    def test_function_export_out_writes_nothing_when_the_source_fails(self) -> None:
        foreign = self.promoted_operation("beta", 2)
        self.promoted_operation("echo", 2)
        root = self.export_root()
        destination = root / "bundle.json"
        corrupt = self.promoted_operation("gamma", 2)
        self.corrupt_receipt_membership(corrupt)
        anchor = self.payload(self.run_cli("function", "show", "echo"))["function_anchor"]
        member = str(anchor["members"][0]["artifact_id"])
        self.run_cli("artifact", "suspend", member, "--actor", "operator", "--reason", "drift")
        cases: tuple[tuple[str, tuple[str, ...], int], ...] = (
            ("drifted", ("echo",), 6),
            ("unregistered", ("ghost",), 3),
            ("unknown-receipt", ("echo", "--receipt-id", "fpr_" + "0" * 32), 3),
            ("foreign-receipt", ("echo", "--receipt-id", foreign), 3),
            ("corrupt-receipt", ("gamma", "--receipt-id", corrupt), 5),
        )
        for label, arguments, expected in cases:
            with self.subTest(case=label):
                # The good `--out` changes the code path, never the verdict.
                bare = self.run_cli("function", "export", *arguments)
                run = self.run_cli("function", "export", *arguments, "--out", str(destination))
                self.assertEqual(run.status, expected)
                self.assertEqual(bare.status, expected)
                self.assertEqual(run.stderr_json, bare.stderr_json)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertFalse(destination.exists())
                self.assertEqual(self.temps(root), [])
        verdict = FunctionVerification(
            passed=True,
            entries=0,
            document=None,
            function_hash="e" * 64,
            checks=(FunctionCheck(key="probe", passed=True, detail="held"),),
        )
        with mock.patch.object(System, "verify_function", return_value=verdict):
            guarded = self.run_cli("function", "export", "echo", "--out", str(destination))
        self.assertEqual(guarded.status, 5)
        self.assertEqual(guarded.stdout_bytes, b"")
        self.assertEqual(
            self.error(guarded),
            {
                "error": "integrity",
                "message": "function verification passed without an exportable document",
            },
        )
        self.assertFalse(destination.exists())
        self.assertEqual(self.temps(root), [])

    def test_function_export_out_path_faults_preempt_source_verdicts(self) -> None:
        self.promoted_operation("echo", 2)
        root = self.export_root()
        referent = root / "referent"
        referent.write_bytes(b"referent-bytes")
        link = root / "link"
        link.symlink_to(referent)
        blocked = root / "blocked"
        (blocked / "child").mkdir(parents=True)
        os.chmod(blocked, 0o000)
        self.addCleanup(os.chmod, blocked, 0o700)
        missing = str(root / "missing" / "bundle.json")
        absent = "export output directory does not exist"
        unusable = "export output path must identify a non-symlink regular file"
        unsafe = "export output could not be written safely"
        anchor = self.payload(self.run_cli("function", "show", "echo"))["function_anchor"]
        member = str(anchor["members"][0]["artifact_id"])
        self.run_cli("artifact", "suspend", member, "--actor", "operator", "--reason", "drift")
        cases: tuple[tuple[str, tuple[str, ...], str, str, int], ...] = (
            ("drift-parent-missing", ("echo",), missing, absent, 6),
            ("drift-symlink-target", ("echo",), str(link), unusable, 6),
            # An EACCES the predicates raise preempts the verdict exactly as the
            # structural rejections do, so the whole precheck is one class.
            ("drift-blocked-ancestor", ("echo",), str(blocked / "child" / "b.json"), unsafe, 6),
            ("unregistered-parent-missing", ("ghost",), missing, absent, 3),
            (
                "unknown-receipt-symlink-target",
                ("echo", "--receipt-id", "fpr_" + "0" * 32),
                str(link),
                unusable,
                3,
            ),
        )
        for label, arguments, destination, message, without in cases:
            with self.subTest(case=label):
                # The same ledger state without `--out` reports the source verdict.
                bare = self.run_cli("function", "export", *arguments)
                self.assertEqual(bare.status, without)
                run = self.run_cli("function", "export", *arguments, "--out", destination)
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(self.error(run), {"error": "invalid", "message": message})
                self.assertEqual(self.temps(root), [])
        # Operation grammar still precedes the destination check.
        grammar = self.run_cli("function", "export", "", "--out", missing)
        self.assertEqual(grammar.status, 2)
        self.assertEqual(
            self.error(grammar),
            {
                "error": "invalid",
                "message": "operation must be 1-128 ASCII letters, digits, "
                "'.', '_', ':', '/', or '-'",
            },
        )
        self.assertTrue(link.is_symlink())
        self.assertEqual(referent.read_bytes(), b"referent-bytes")

    def test_function_export_out_path_fault_preempts_a_corrupt_receipt(self) -> None:
        receipt = self.promoted_operation("echo", 2)
        self.corrupt_receipt_membership(receipt)
        root = self.export_root()
        bare = self.run_cli("function", "export", "echo", "--receipt-id", receipt)
        self.assertEqual(bare.status, 5)
        run = self.run_cli(
            "function", "export", "echo",
            "--receipt-id", receipt,
            "--out", str(root / "missing" / "bundle.json"),
        )
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(
            self.error(run),
            {"error": "invalid", "message": "export output directory does not exist"},
        )
        self.assertEqual(self.temps(root), [])

    def test_function_export_out_preserves_the_symbol_qualified_exit_map(self) -> None:
        verdict = FunctionVerification(
            passed=False,
            entries=1,
            document=None,
            function_hash="d" * 64,
            checks=(FunctionCheck(key="probe", passed=False, detail="negative"),),
        )
        root = self.export_root()
        destination = root / "bundle.json"
        cases: tuple[tuple[BaseException | None, int], ...] = (
            (ValidationError("invalid"), 2),
            (NotFoundError("missing"), 3),
            (StateError("state"), 4),
            (IntegrityError("integrity"), 5),
            (None, 6),
        )
        for exception, expected in cases:
            with self.subTest(expected=expected):
                replacement: typing.Any
                if exception is None:
                    replacement = mock.Mock(return_value=verdict)
                else:
                    replacement = mock.Mock(side_effect=exception)
                # Patch the library boundary; patching `_run` would replace the
                # branch under test.
                with mock.patch.object(System, "verify_function", replacement):
                    run = self.run_cli("function", "export", "echo", "--out", str(destination))
                self.assertEqual(run.status, expected)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertFalse(destination.exists())
                self.assertEqual(self.temps(root), [])

    # --- function eval -----------------------------------------------------

    def run_offline(self, *arguments: str, text_only: bool = False) -> _CLIRun:
        # The eval leaf must resolve with no ledger globals at all, so the frozen
        # runner is reused with an empty prefix rather than replaced.
        saved = self.base
        self.base = []
        try:
            return self.run_cli(*arguments, text_only=text_only)
        finally:
            self.base = saved

    def exported_bundle(self, members: int = 3) -> tuple[pathlib.Path, str, str]:
        self.promoted_operation("echo", members)
        destination = pathlib.Path(self.temporary.name) / "bundle.json"
        self.assertEqual(
            self.run_cli("function", "export", "echo", "--out", str(destination)).status, 0
        )
        text = destination.read_text(encoding="utf-8")
        return destination, text, json.loads(text)["function_hash"]

    def resealed(self, text: str, mutate: typing.Callable[[dict], None]) -> str:
        # The outer hash is recomputed over the tampered content, or the
        # whole-document check rejects first and the entry check stays unpinned.
        content = json.loads(text)
        mutate(content)
        body = {key: value for key, value in content.items() if key != "function_hash"}
        content["function_hash"] = canonicalize(body).digest
        return json.dumps(content)

    def written(self, name: str, payload: bytes) -> pathlib.Path:
        path = pathlib.Path(self.temporary.name) / name
        path.write_bytes(payload)
        return path

    def eval_error(self, bundle: object, value: str = '{"x": 1}') -> tuple[int, str]:
        run = self.run_offline("function", "eval", "--bundle", str(bundle), "--input", value)
        self.assertEqual(run.stdout_bytes, b"")
        return run.status, self.error(run)["message"]

    def test_function_eval_hit_reports_the_output_and_the_answering_identity(self) -> None:
        bundle, _, digest = self.exported_bundle()
        run = self.run_offline("function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}')
        payload = self.payload(run)
        self.assertEqual(run.stderr_text, "")
        self.assertTrue(payload["matched"])
        self.assertEqual(payload["output"], {"kind": "echo", "value": {"x": 1}})
        self.assertRegex(str(payload["artifact_hash"]), r"\A[0-9a-f]{64}\Z")
        # The answer names the function that produced it, and it is the same
        # identity the ledger-side verifier reports for the promoted set.
        self.assertEqual(payload["function_hash"], digest)
        self.assertEqual(
            self.payload(self.run_cli("function", "verify", "echo"))["function_hash"], digest
        )

    def test_function_eval_miss_is_exit_six_with_the_same_identity(self) -> None:
        bundle, _, digest = self.exported_bundle()
        run = self.run_offline("function", "eval", "--bundle", str(bundle), "--input", '{"x": 99}')
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(
            run.stdout_bytes,
            json.dumps(
                {
                    "artifact_hash": None,
                    "function_hash": digest,
                    "matched": False,
                    "output": None,
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8")
            + b"\n",
        )

    def test_function_eval_payload_key_set_is_frozen_on_both_verdicts(self) -> None:
        bundle, _, _ = self.exported_bundle()
        keys = {"artifact_hash", "function_hash", "matched", "output"}
        for value, status in (('{"x": 1}', 0), ('{"x": 99}', 6)):
            with self.subTest(value=value):
                run = self.run_offline(
                    "function", "eval", "--bundle", str(bundle), "--input", value
                )
                self.assertEqual(run.status, status)
                self.assertIsInstance(run.stdout_json, dict)
                self.assertEqual(set(typing.cast(dict, run.stdout_json)), keys)

    def test_function_eval_constructs_no_system(self) -> None:
        bundle, _, _ = self.exported_bundle()
        expected = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        )
        # Ledger freedom is proved by construction failure. The import graph
        # reaches sqlite3 through the package __init__ either way.
        with mock.patch.object(
            System, "__init__", side_effect=AssertionError("System constructed")
        ):
            run = self.run_offline(
                "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_bytes, expected.stdout_bytes)

    def test_function_eval_ignores_supplied_ledger_globals(self) -> None:
        bundle, _, _ = self.exported_bundle()
        offline = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        )
        run = self.run_cli("function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}')
        self.assertEqual(run.stdout_bytes, offline.stdout_bytes)

    def test_function_eval_lookup_is_canonical_not_textual(self) -> None:
        bundle, _, _ = self.exported_bundle()
        hits = ('{"x": 1}', '{ "x" : 1 }', '{"x":1}\n')
        for value in hits:
            with self.subTest(hit=value):
                run = self.run_offline(
                    "function", "eval", "--bundle", str(bundle), "--input", value
                )
                self.assertEqual(run.status, 0)
        for value in ('{"x": "1"}', '{"X": 1}', '{"x": 1, "y": null}', "{}"):
            with self.subTest(miss=value):
                run = self.run_offline(
                    "function", "eval", "--bundle", str(bundle), "--input", value
                )
                self.assertEqual(run.status, 6)

    def test_function_eval_reads_input_from_either_stdin_host(self) -> None:
        bundle, _, _ = self.exported_bundle()
        expected = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        ).stdout_bytes
        source = io.StringIO('{"x": 1}')
        with mock.patch.object(sys, "stdin", source):
            run = self.run_offline("function", "eval", "--bundle", str(bundle), "--input", "-")
        self.assertEqual(run.stdout_bytes, expected)
        binary = types.SimpleNamespace(buffer=io.BytesIO(b'{"x": 1}'))
        with mock.patch.object(sys, "stdin", binary):
            run = self.run_offline("function", "eval", "--bundle", str(bundle), "--input", "-")
        self.assertEqual(run.stdout_bytes, expected)

    def test_function_eval_maps_a_stdin_read_failure_on_both_hosts(self) -> None:
        # A stream fault is host I/O, not bad JSON, so it reaches the leaf as
        # `OSError`. Untranslated it escapes `main`'s map as a traceback and
        # leaves automation with no status class on every `--input -` leaf.
        bundle, _, _ = self.exported_bundle()

        class FailingText(io.StringIO):
            def read(self, *args: object) -> str:
                raise OSError("stdin read failed")

        class FailingBytes(io.BytesIO):
            def read(self, *args: object) -> bytes:
                raise OSError("stdin read failed")

        hosts = (
            ("text-only", FailingText()),
            ("buffer-bearing", types.SimpleNamespace(buffer=FailingBytes())),
        )
        for label, host in hosts:
            with self.subTest(host=label):
                with mock.patch.object(sys, "stdin", host):
                    run = self.run_offline(
                        "function", "eval", "--bundle", str(bundle), "--input", "-"
                    )
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(
                    self.error(run),
                    {"error": "invalid", "message": "JSON stdin could not be read"},
                )

    def test_function_eval_expected_hash_binds_caller_held_identity(self) -> None:
        bundle, _, digest = self.exported_bundle()
        run = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}',
            "--expected-function-hash", digest,
        )
        self.assertEqual(run.status, 0)
        self.assertEqual(self.payload(run)["function_hash"], digest)

    def test_function_eval_expected_hash_rejects_another_identity(self) -> None:
        bundle, _, digest = self.exported_bundle()
        other = ("0" if digest[0] != "0" else "1") + digest[1:]
        run = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}',
            "--expected-function-hash", other,
        )
        self.assertEqual(run.status, 5)
        self.assertEqual(run.stdout_bytes, b"")
        self.assertEqual(self.error(run)["error"], "integrity")
        self.assertEqual(
            self.error(run)["message"], "function does not match expected_function_hash"
        )

    def test_function_eval_expected_hash_must_be_a_digest(self) -> None:
        bundle, _, digest = self.exported_bundle()
        for value in ("", "zz", digest[:63], digest + "0", digest.upper()):
            with self.subTest(value=value):
                run = self.run_offline(
                    "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}',
                    "--expected-function-hash", value,
                )
                self.assertEqual(run.status, 2)
                self.assertEqual(
                    self.error(run)["message"],
                    "expected_function_hash must be a SHA-256 hex digest",
                )

    def test_function_eval_detects_entry_tamper_at_every_position(self) -> None:
        _, text, _ = self.exported_bundle()
        entries = len(json.loads(text)["entries"])
        self.assertGreaterEqual(entries, 3)
        # The middle and the last entry both, because a loop-quantified digest
        # check is weakened at the last position first.
        for index in (1, entries - 1):
            for field, replacement in (
                ("output", {"kind": "echo", "value": {"x": 4242}}),
                ("input", {"x": 4242}),
            ):
                with self.subTest(index=index, field=field):
                    victim = self.written(
                        f"tamper-{field}-{index}.json",
                        self.resealed(
                            text,
                            lambda content, i=index, f=field, r=replacement: content["entries"][
                                i
                            ].update({f: r}),
                        ).encode("utf-8"),
                    )
                    status, message = self.eval_error(victim)
                    self.assertEqual(status, 5)
                    self.assertEqual(
                        message, f"function entry {index} {field} digest mismatch"
                    )

    def test_function_eval_detects_a_flipped_embedded_hash(self) -> None:
        _, text, digest = self.exported_bundle()
        other = ("0" if digest[0] != "0" else "1") + digest[1:]
        victim = self.written("flipped.json", text.replace(digest, other).encode("utf-8"))
        self.assertEqual(self.eval_error(victim), (5, "function hash mismatch"))

    def test_function_eval_rejects_malformed_bundles(self) -> None:
        _, text, _ = self.exported_bundle()
        cases = {
            "empty.json": (b"", "invalid JSON: Expecting value: line 1 column 1 (char 0)"),
            "prose.json": (b"not-json", "invalid JSON: Expecting value: line 1 column 1 (char 0)"),
            "binary.json": (b"\xff\xfe", "function bundle is not valid UTF-8"),
            "shape.json": (
                b"{}",
                "invalid function: expected keys ['abi', 'canonicalizer', 'entries',"
                " 'function_hash', 'scope']",
            ),
            "dupe.json": (
                b'{"abi": "cement-function-v2", "abi": "cement-function-v2"}',
                "duplicate JSON object key: 'abi'",
            ),
            "abi.json": (
                text.replace("cement-function-v2", "cement-function-v3").encode("utf-8"),
                "unsupported function ABI",
            ),
            "canon.json": (
                text.replace("cement-json-v1", "cement-json-v2").encode("utf-8"),
                "unsupported function canonicalizer",
            ),
        }
        for name, (payload, message) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self.eval_error(self.written(name, payload)), (2, message)
                )

    def test_function_eval_requires_a_regular_file(self) -> None:
        root = pathlib.Path(self.temporary.name)
        (root / "folder").mkdir()
        os.mkfifo(root / "pipe")
        # Only objects whose open succeeds reach the identity verdict; a socket
        # fails during open and is graded by the neighbouring read-error test.
        for path in (
            root / "folder",
            root / "pipe",
            pathlib.Path("/dev/null"),
            pathlib.Path("/dev/zero"),
        ):
            with self.subTest(path=str(path)):
                self.assertEqual(
                    self.eval_error(path),
                    (2, "function bundle path must identify a regular file"),
                )

    def test_function_eval_reports_unreadable_paths_uniformly(self) -> None:
        root = pathlib.Path(self.temporary.name)
        (root / "dangling").symlink_to(root / "absent.json")
        blocked = root / "blocked"
        (blocked / "inner").mkdir(parents=True)
        (blocked / "inner" / "bundle.json").write_text("{}", encoding="utf-8")
        blocked.chmod(0o000)
        self.addCleanup(blocked.chmod, 0o700)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(str(root / "socket"))
        regular = root / "plain.json"
        regular.write_text("{}", encoding="utf-8")
        cases = (
            root / "absent.json",
            root / "dangling",
            blocked / "inner" / "bundle.json",
            # A socket refuses the open itself, so it never reaches `S_ISREG`.
            root / "socket",
            # A trailing slash fails during open even on a regular file.
            f"{regular}/",
            # `-` is an ordinary filename here; only `--input` reads stdin.
            "-",
            "",
        )
        for path in cases:
            with self.subTest(path=str(path)):
                self.assertEqual(
                    self.eval_error(path), (2, "function bundle could not be read")
                )

    def test_function_eval_follows_a_symlink_to_a_regular_bundle(self) -> None:
        bundle, _, _ = self.exported_bundle()
        link = pathlib.Path(self.temporary.name) / "link.json"
        link.symlink_to(bundle)
        direct = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        )
        run = self.run_offline("function", "eval", "--bundle", str(link), "--input", '{"x": 1}')
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_bytes, direct.stdout_bytes)

    def test_function_eval_bundle_size_bound_is_an_adjacent_pair(self) -> None:
        root = pathlib.Path(self.temporary.name)
        for size, expected in (
            (FUNCTION_MAX_BYTES, "invalid JSON: Expecting value: line 1 column 1 (char 0)"),
            (FUNCTION_MAX_BYTES + 1, f"function bundle exceeds {FUNCTION_MAX_BYTES} bytes"),
        ):
            with self.subTest(size=size):
                path = root / "sized.json"
                with path.open("wb") as handle:
                    # Multibyte content, so a byte cap cannot pass as a character
                    # cap; the sparse tail keeps the fixture cheap.
                    handle.write("é".encode("utf-8") * 4)
                    handle.truncate(size)
                self.assertEqual(path.stat().st_size, size)
                self.assertEqual(self.eval_error(path), (2, expected))
                path.unlink()

    def test_function_eval_reader_materializes_exactly_one_byte_past_the_bound(self) -> None:
        bundle, _, _ = self.exported_bundle()
        requested: list[int] = []
        real_fdopen = os.fdopen

        class _Recorder:
            def __init__(self, stream: typing.Any) -> None:
                self.stream = stream

            def read(self, size: int = -1) -> bytes:
                requested.append(size)
                return typing.cast(bytes, self.stream.read(size))

            def __enter__(self) -> "_Recorder":
                self.stream.__enter__()
                return self

            def __exit__(self, *arguments: object) -> object:
                return self.stream.__exit__(*arguments)

        def fdopen(descriptor: int, mode: str = "r", *rest: object) -> typing.Any:
            return _Recorder(real_fdopen(descriptor, mode, *rest))  # type: ignore[arg-type]

        # An unbounded read returns byte-identical results for every in-bounds
        # fixture, so the bind is the only observable that distinguishes them.
        # `io.BufferedReader.read` is immutable, so the stream is wrapped instead.
        with mock.patch.object(os, "fdopen", fdopen):
            run = self.run_offline(
                "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
            )
        self.assertEqual(run.status, 0)
        self.assertIn(FUNCTION_MAX_BYTES + 1, requested)

    def test_function_eval_input_keeps_the_default_channel_bounds(self) -> None:
        bundle, _, _ = self.exported_bundle()
        filler = "y" * (DEFAULT_MAX_BYTES - len('{"x": ""}'))
        accepted = json.dumps({"x": filler})
        self.assertEqual(len(accepted.encode("utf-8")), DEFAULT_MAX_BYTES)
        self.assertEqual(
            self.run_offline(
                "function", "eval", "--bundle", str(bundle), "--input", accepted
            ).status,
            6,
        )
        rejected = json.dumps({"x": filler + "y"})
        self.assertEqual(len(rejected.encode("utf-8")), DEFAULT_MAX_BYTES + 1)
        self.assertEqual(
            self.eval_error(bundle, rejected),
            (2, f"JSON source exceeds {DEFAULT_MAX_BYTES} bytes"),
        )

    def test_function_eval_input_depth_bound_is_an_adjacent_pair(self) -> None:
        bundle, _, _ = self.exported_bundle()
        self.assertEqual(
            self.run_offline(
                "function", "eval", "--bundle", str(bundle),
                "--input", "[" * 64 + "1" + "]" * 64,
            ).status,
            6,
        )
        status, message = self.eval_error(bundle, "[" * 65 + "1" + "]" * 65)
        self.assertEqual(status, 2)
        self.assertEqual(message, "JSON exceeds maximum depth 64")

    def test_function_eval_grades_the_input_before_reading_the_bundle(self) -> None:
        _, text, digest = self.exported_bundle()
        other = ("0" if digest[0] != "0" else "1") + digest[1:]
        tampered = self.written("double.json", text.replace(digest, other).encode("utf-8"))
        # A structurally unusable request is repaired by no amount of bundle
        # work, so the cheap local check wins over the 64 MiB channel.
        status, message = self.eval_error(tampered, "{oops")
        self.assertEqual(status, 2)
        self.assertNotEqual(message, "function hash mismatch")
        self.assertEqual(self.eval_error(tampered), (5, "function hash mismatch"))
        opened: list[str] = []
        real_open = os.open

        def spy(path: object, *arguments: object, **keywords: object) -> int:
            opened.append(str(path))
            return real_open(path, *arguments, **keywords)  # type: ignore[arg-type]

        with mock.patch.object(os, "open", spy):
            self.eval_error(tampered, "{oops")
        self.assertNotIn(str(tampered), opened)

    def test_function_eval_binds_the_parsed_document_to_the_evaluator(self) -> None:
        bundle, _, digest = self.exported_bundle()
        seen: dict[str, object] = {}
        real_parse = cement_cli.parse_function
        real_evaluate = cement_cli.evaluate

        def parse(source: str, **keywords: object) -> object:
            document = real_parse(source, **keywords)  # type: ignore[arg-type]
            seen["document"] = document
            return document

        def evaluate(document: object, *, input_json: object) -> object:
            seen["evaluated"] = document
            seen["input"] = input_json
            return real_evaluate(document, input_json=input_json)  # type: ignore[arg-type]

        with mock.patch.object(cement_cli, "parse_function", parse), mock.patch.object(
            cement_cli, "evaluate", evaluate
        ):
            run = self.run_offline(
                "function", "eval", "--bundle", str(bundle), "--input", '{ "x" : 1 }'
            )
        self.assertEqual(run.status, 0)
        # A validator whose result is discarded is not a check: the document that
        # answered must be the one that was validated, and the evaluated key must
        # be the canonicalized input, not the operator's raw text.
        self.assertIs(seen["evaluated"], seen["document"])
        self.assertEqual(getattr(seen["input"], "text"), '{"x":1}')
        self.assertEqual(getattr(seen["document"], "function_hash"), digest)

    def test_function_eval_exit_six_names_the_miss_and_nothing_else(self) -> None:
        bundle, text, digest = self.exported_bundle()
        other = ("0" if digest[0] != "0" else "1") + digest[1:]
        negatives = (
            ("--bundle", str(self.written("bad.json", b"{}")), "--input", '{"x": 1}'),
            ("--bundle", str(bundle), "--input", "{oops"),
            ("--bundle", str(pathlib.Path(self.temporary.name) / "absent"), "--input", '{"x": 1}'),
            (
                "--bundle", str(self.written("flip.json", text.replace(digest, other).encode())),
                "--input", '{"x": 1}',
            ),
            ("--bundle", str(bundle), "--input", '{"x": 1}', "--expected-function-hash", other),
        )
        for arguments in negatives:
            with self.subTest(arguments=arguments):
                self.assertNotEqual(
                    self.run_offline("function", "eval", *arguments).status, 6
                )
        self.assertEqual(
            self.run_offline(
                "function", "eval", "--bundle", str(bundle), "--input", '{"x": 99}'
            ).status,
            6,
        )

    def test_function_eval_requires_both_channels(self) -> None:
        bundle, _, _ = self.exported_bundle()
        for arguments, message in (
            (("--input", '{"x": 1}'), "the following arguments are required: --bundle"),
            (("--bundle", str(bundle)), "the following arguments are required: --input"),
            ((), "the following arguments are required: --bundle, --input"),
        ):
            with self.subTest(arguments=arguments):
                run = self.run_offline("function", "eval", *arguments)
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual(self.error(run)["message"], message)

    def test_function_eval_answers_an_empty_exported_function(self) -> None:
        # The spine case for a freshly registered operation: verification passes
        # vacuously, so the export is a real document with no entries.
        self.register("echo")
        destination = pathlib.Path(self.temporary.name) / "empty.json"
        self.assertEqual(
            self.run_cli("function", "export", "echo", "--out", str(destination)).status, 0
        )
        document = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(document["entries"], [])
        run = self.run_offline(
            "function", "eval", "--bundle", str(destination), "--input", '{"x": 1}'
        )
        self.assertEqual(run.status, 6)
        self.assertEqual(run.stderr_text, "")
        self.assertEqual(
            run.stdout_json,
            {
                "artifact_hash": None,
                "function_hash": document["function_hash"],
                "matched": False,
                "output": None,
            },
        )

    def test_function_eval_payload_covers_every_match_field(self) -> None:
        # The hand-built projection cannot drift silently: a field added to the
        # library model must be a deliberate CLI decision, not an omission.
        bundle, _, _ = self.exported_bundle()
        payload = self.payload(
            self.run_offline("function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}')
        )
        self.assertLessEqual(
            {field.name for field in dataclasses.fields(FunctionMatch)}, set(payload)
        )

    def test_function_eval_rejects_lexically_impossible_paths(self) -> None:
        # `ValidationError` subclasses `ValueError`, so these arrive at the same
        # residual clause as `OSError` and must not escape as raw exceptions.
        for path in ("a\x00b", "\udc80", "\x00"):
            with self.subTest(path=repr(path)):
                self.assertEqual(
                    self.eval_error(path), (2, "function bundle could not be read")
                )

    def test_function_eval_failure_precedence_is_a_matrix(self) -> None:
        bundle, text, digest = self.exported_bundle()
        other = ("0" if digest[0] != "0" else "1") + digest[1:]
        root = pathlib.Path(self.temporary.name)
        flipped = self.written("precedence.json", text.replace(digest, other).encode("utf-8"))
        shapeless = self.written("precedence-shape.json", b"{}")
        cases = (
            # bad input beats every bundle verdict, in either direction of fault
            ("{oops", str(flipped), 2, "hash"),
            ("{oops", str(root / "absent"), 2, "read"),
            ("{oops", str(root), 2, "regular file"),
            # a structurally invalid bundle beats expected-hash grading
            (None, str(shapeless), 2, "invalid function"),
        )
        for value, path, status, fragment in cases:
            with self.subTest(path=path, value=value):
                run = self.run_offline(
                    "function", "eval", "--bundle", path,
                    "--input", value if value is not None else '{"x": 1}',
                    "--expected-function-hash", other,
                )
                self.assertEqual(run.status, status)
                message = self.error(run)["message"]
                if value is None:
                    self.assertIn(fragment, message)
                else:
                    self.assertNotIn(fragment, message)
        # argparse preempts all four steps
        run = self.run_offline("function", "eval", "--bundle", str(bundle))
        self.assertEqual(run.status, 2)
        self.assertEqual(
            self.error(run)["message"], "the following arguments are required: --input"
        )

    def test_function_eval_never_reaches_the_ledger_globals(self) -> None:
        bundle, _, _ = self.exported_bundle()
        offline = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        )
        saved = self.base
        self.base = ["--db", str(pathlib.Path(self.temporary.name) / "absent" / "no.db")]
        try:
            with mock.patch.object(
                System, "__init__", side_effect=AssertionError("System constructed")
            ):
                run = self.run_cli("function", "eval", "--bundle", str(bundle),
                                   "--input", '{"x": 1}')
        finally:
            self.base = saved
        # A supplied but unusable ledger path is never opened, and the missing
        # `--partition` never reaches the gate that would reject it.
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_bytes, offline.stdout_bytes)

    def test_function_eval_null_output_hit_is_not_a_miss(self) -> None:
        # Both verdicts carry `output: null` here, so `matched` and
        # `artifact_hash` are the only discriminators the payload offers.
        _, text, _ = self.exported_bundle()

        def blank(content: dict) -> None:
            entry = next(item for item in content["entries"] if item["input"] == {"x": 1})
            entry["output"] = None
            entry["output_hash"] = canonicalize(None).digest

        path = self.written("null-output.json", self.resealed(text, blank).encode("utf-8"))
        hit = self.payload(
            self.run_offline("function", "eval", "--bundle", str(path), "--input", '{"x": 1}')
        )
        negative = self.run_offline(
            "function", "eval", "--bundle", str(path), "--input", '{"x": 99}'
        )
        self.assertEqual(negative.status, 6)
        miss = json.loads(negative.stdout_bytes)
        self.assertIsNone(hit["output"])
        self.assertIsNone(miss["output"])
        self.assertTrue(hit["matched"])
        self.assertFalse(miss["matched"])
        self.assertRegex(str(hit["artifact_hash"]), r"\A[0-9a-f]{64}\Z")
        self.assertIsNone(miss["artifact_hash"])

    def test_function_eval_maps_library_faults_without_widening(self) -> None:
        # Only the two documented classes are translated. Anything else keeps
        # travelling, so the mapping cannot mask an implementation fault.
        document = mock.Mock(function_hash="f" * 64)
        reader = mock.patch.object(cement_cli, "_read_function_bundle", return_value="sealed")
        parsed = mock.patch.object(cement_cli, "parse_function", return_value=document)
        for stage, fault, expected in (
            ("parse_function", ValidationError("bad bundle"), (2, "invalid")),
            ("parse_function", IntegrityError("bundle digest"), (5, "integrity")),
            ("evaluate", ValidationError("bad stored output"), (2, "invalid")),
        ):
            with self.subTest(stage=stage, fault=type(fault).__name__):
                with reader, contextlib.ExitStack() as stack:
                    if stage == "evaluate":
                        stack.enter_context(parsed)
                    stack.enter_context(mock.patch.object(cement_cli, stage, side_effect=fault))
                    run = self.run_offline(
                        "function", "eval", "--bundle", "bundle.json", "--input", "null"
                    )
                self.assertEqual(run.stdout_bytes, b"")
                self.assertEqual((run.status, self.error(run)["error"]), expected)
        with reader, parsed, mock.patch.object(
            cement_cli, "evaluate", side_effect=RuntimeError("unrelated")
        ), self.assertRaisesRegex(RuntimeError, "unrelated"):
            self.run_offline("function", "eval", "--bundle", "bundle.json", "--input", "null")

    def test_function_eval_translates_injected_reader_failures(self) -> None:
        # Every descriptor step can fail on an otherwise healthy path, and all
        # of them owe the caller one message rather than a traceback.
        bundle, _, _ = self.exported_bundle()
        for stage in ("open", "fstat", "fdopen"):
            with self.subTest(stage=stage):
                with mock.patch.object(
                    cement_cli.os, stage, side_effect=OSError(errno.EIO, "injected")
                ):
                    self.assertEqual(
                        self.eval_error(bundle), (2, "function bundle could not be read")
                    )
        real_fdopen = os.fdopen

        class _Failing:
            def __init__(self, stream: typing.Any) -> None:
                self.stream = stream

            def read(self, size: int = -1) -> bytes:
                raise OSError(errno.EIO, "injected")

            def __enter__(self) -> "_Failing":
                self.stream.__enter__()
                return self

            def __exit__(self, *arguments: object) -> object:
                return self.stream.__exit__(*arguments)

        def fdopen(descriptor: int, mode: str = "r", *rest: object) -> typing.Any:
            return _Failing(real_fdopen(descriptor, mode, *rest))  # type: ignore[arg-type]

        # The read owns the descriptor by then, so its failure travels through
        # the stream's own close rather than the pre-handover branch.
        with mock.patch.object(os, "fdopen", fdopen):
            self.assertEqual(
                self.eval_error(bundle), (2, "function bundle could not be read")
            )

    def test_function_eval_reads_a_file_named_dash(self) -> None:
        # `-` is an ordinary value on this flag, so a real file of that name is
        # readable. A reserved-dash special case cannot pass this.
        bundle, text, _ = self.exported_bundle()
        root = pathlib.Path(self.temporary.name)
        (root / "-").write_text(text, encoding="utf-8")
        direct = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        )
        saved = os.getcwd()
        os.chdir(root)
        try:
            run = self.run_offline("function", "eval", "--bundle", "-", "--input", '{"x": 1}')
        finally:
            os.chdir(saved)
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_bytes, direct.stdout_bytes)

    def test_function_eval_grades_only_the_last_repeated_flag(self) -> None:
        # Repetition keeps the final occurrence, so an earlier bundle is never
        # opened and an earlier input is never graded.
        bundle, _, digest = self.exported_bundle()
        run = self.run_offline(
            "function", "eval",
            "--bundle", str(pathlib.Path(self.temporary.name) / "absent.json"),
            "--bundle", str(bundle),
            "--input", "{oops",
            "--input", '{"x": 1}',
            "--expected-function-hash", "zz",
            "--expected-function-hash", digest,
        )
        self.assertEqual(run.status, 0)
        self.assertTrue(self.payload(run)["matched"])

    def test_function_eval_forwards_the_expected_hash_unvalidated(self) -> None:
        # Bundle validation runs in `parse_function`'s own order, so every
        # document fault outranks expected-hash grammar. Pre-grading the flag
        # in the leaf would reverse the reported cause.
        bundle, text, _ = self.exported_bundle()

        def flip(content: dict) -> None:
            entry = next(item for item in content["entries"] if item["input"] == {"x": 1})
            entry["output"] = {"kind": "echo", "value": {"x": 4242}}

        cases = (
            (self.written("order-shape.json", b"{}"), 2, "invalid function: expected keys"),
            (
                self.written("order-entry.json", self.resealed(text, flip).encode("utf-8")),
                5,
                "output digest mismatch",
            ),
            (bundle, 2, "expected_function_hash must be a SHA-256 hex digest"),
        )
        for path, status, fragment in cases:
            with self.subTest(path=path.name):
                run = self.run_offline(
                    "function", "eval", "--bundle", str(path),
                    "--input", '{"x": 1}', "--expected-function-hash", "zz",
                )
                self.assertEqual(run.status, status)
                self.assertIn(fragment, self.error(run)["message"])

    def test_function_eval_rejects_decimal_input_before_lookup(self) -> None:
        # A decimal token never becomes a miss: the canonicalizer refuses it, so
        # the verdict is an invalid request rather than a negative answer.
        bundle, _, _ = self.exported_bundle()
        for value in ('{"x": 1.0}', '{"x": 1e0}'):
            with self.subTest(value=value):
                status, message = self.eval_error(bundle, value)
                self.assertEqual(status, 2)
                self.assertIn("rejects decimal/exponent number", message)

    def test_function_eval_opens_no_store_or_connection(self) -> None:
        # A failing `System` alone leaves a direct store or connection unproved.
        bundle, _, _ = self.exported_bundle()
        expected = self.run_offline(
            "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
        )
        with mock.patch.object(
            System, "__init__", side_effect=AssertionError("System constructed")
        ), mock.patch.object(
            sqlite3, "connect", side_effect=AssertionError("connection opened")
        ):
            run = self.run_offline(
                "function", "eval", "--bundle", str(bundle), "--input", '{"x": 1}'
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_bytes, expected.stdout_bytes)

    def test_function_eval_help_reuses_the_shipped_flag_register(self) -> None:
        # The register is set by the shipped leaves, not invented here: short
        # lowercase fragments, except where a term the project capitalizes opens
        # the line. `--input` reuses the shipped sentence for the same channel.
        def options(*path: str) -> dict[str, argparse.Action]:
            node = cement_cli._parser()
            for name in path:
                node = next(
                    action
                    for action in node._actions
                    if isinstance(action, argparse._SubParsersAction)
                ).choices[name]
            return {action.dest: action for action in node._actions}

        actions = options("function", "eval")
        self.assertEqual(
            set(actions) - {"help"}, {"bundle", "input", "expected_function_hash"}
        )
        self.assertTrue(actions["bundle"].required)
        self.assertTrue(actions["input"].required)
        self.assertFalse(actions["expected_function_hash"].required)
        # M3.5b removed `handle`, the original reference leaf. `resolve` is the
        # surviving leaf carrying the same `--input` channel, so the register
        # claim is re-based onto it rather than dropped.
        self.assertEqual(actions["input"].help, options("resolve")["input"].help)
        for name in ("bundle", "input", "expected_function_hash"):
            with self.subTest(option=name):
                text = str(actions[name].help)
                self.assertEqual(text, text.strip())
                self.assertLessEqual(len(text.split()), 20)
                for filler in ("simply", "robust", "seamlessly", "leverage"):
                    self.assertNotIn(filler, text.lower())

    def test_function_eval_leaves_a_shipped_leaf_untouched(self) -> None:
        run = self.run_cli(
            "operation", "register", "regression",
            "--min-confirmations", "2", "--min-reviewers", "1", "--min-span-seconds", "0",
        )
        self.assertEqual(run.status, 0)
        self.assertEqual(
            run.stdout_bytes,
            b'{\n  "operation": "regression",\n  "revision": 1\n}\n',
        )


if __name__ == "__main__":
    unittest.main()
