import argparse
import contextlib
import inspect
import io
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import typing
import unittest
from dataclasses import dataclass
from unittest import mock

from cement_runtime import System
from cement_runtime.cli import main
from cement_runtime.errors import IntegrityError, NotFoundError, StateError, ValidationError
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
_PENDING_KEYS = {"input_hash", "operation_revision", "proposal_id", "request_id"}
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

    def confirm(self, operation: str, value: int, tag: str) -> None:
        adapter = pathlib.Path("examples/echo_adapter.py").resolve()
        source = json.dumps([sys.executable, str(adapter)])
        for number in (1, 2):
            handled = self.payload(
                self.run_cli(
                    "handle",
                    operation,
                    "--input",
                    json.dumps({"x": value}),
                    "--request-id",
                    f"{tag}-{number}",
                    "--source-command",
                    source,
                )
            )
            self.assertEqual(handled["status"], "review_required")
            reviewed = self.payload(
                self.run_cli(
                    "proposal",
                    "review",
                    str(handled["proposal_id"]),
                    "--reviewer",
                    "operator",
                    "--decision",
                    "accept",
                )
            )
            self.assertEqual(reviewed["source"], "confirmed")

    def handle_once(
        self, operation: str, value: int, tag: str, *, review: bool
    ) -> None:
        # One confirmation only: reviewed leaves a policy-blocked compile scope,
        # unreviewed leaves a pending proposal.
        adapter = pathlib.Path("examples/echo_adapter.py").resolve()
        source = json.dumps([sys.executable, str(adapter)])
        handled = self.payload(
            self.run_cli(
                "handle",
                operation,
                "--input",
                json.dumps({"x": value}),
                "--request-id",
                tag,
                "--source-command",
                source,
            )
        )
        if review:
            self.assertEqual(
                self.payload(
                    self.run_cli(
                        "proposal",
                        "review",
                        str(handled["proposal_id"]),
                        "--reviewer",
                        "operator",
                        "--decision",
                        "accept",
                    )
                )["source"],
                "confirmed",
            )

    def promote_set(self, operation: str) -> str:
        # The CLI cannot promote a function set until u4c3/u4c4, so drive the
        # library for setup and assert through the CLI.
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

        adapter = pathlib.Path("examples/echo_adapter.py").resolve()
        source = json.dumps([sys.executable, str(adapter)])
        for number in (1, 2):
            pending = self.payload(
                self.run_cli(
                    "handle",
                    "echo",
                    "--input",
                    '{"x":1}',
                    "--request-id",
                    f"cli-{number}",
                    "--source-command",
                    source,
                )
            )
            self.assertEqual(pending["status"], "review_required")
            queue = self.run_cli("proposal", "list").stdout_json
            self.assertIsInstance(queue, list)
            queue = typing.cast(list[dict[str, typing.Any]], queue)
            self.assertIn(pending["proposal_id"], {item["id"] for item in queue})
            resolved = self.payload(
                self.run_cli(
                    "proposal",
                    "review",
                    str(pending["proposal_id"]),
                    "--reviewer",
                    "operator",
                    "--decision",
                    "accept",
                )
            )
            self.assertEqual(resolved["source"], "confirmed")
            polled = self.payload(self.run_cli("request", f"cli-{number}"))
            self.assertEqual(polled["example_id"], resolved["example_id"])

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
        hit = self.payload(
            self.run_cli(
                "handle", "echo", "--input", '{"x":1}', "--request-id", "cli-hit"
            )
        )
        self.assertEqual(hit["source"], "artifact")
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

        stdout = io.StringIO()
        stderr_stream = io.StringIO()
        original_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(" " * 1_048_577)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr_stream):
                status = main([*self.base, "handle", "echo", "--input", "-"])
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
        self.assertEqual(
            sorted(
                proposal["request_id"]
                for proposal in whole["pending_proposals"]
            ),
            ["pending-0", "pending-1", "pending-2"],
        )
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


if __name__ == "__main__":
    unittest.main()
