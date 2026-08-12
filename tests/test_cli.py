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
        for operation, arguments, expected in (
            ("echo", (), 100),
            ("echo", ("--projection-limit", "1"), 1),
            ("other_operation", ("--projection-limit", "10000"), 10_000),
            ("other_operation", ("--projection-limit", "10001"), 10_001),
            # argparse `type=int` accepts every Python integer spelling and the
            # value reaches the library exactly as `int()` produced it.
            ("echo", ("--projection-limit", "+1"), 1),
            ("echo", ("--projection-limit", " 1 "), 1),
            ("echo", ("--projection-limit", "1_0"), 10),
        ):
            with mock.patch.object(System, "function_report", autospec=True) as spy:
                spy.return_value = {"forwarded": True}
                run = self.run_cli("function", "show", operation, *arguments)
            self.assertEqual(run.status, 0)
            self.assertEqual(run.stdout_json, {"forwarded": True})
            self.assertEqual(spy.call_count, 1)
            positional = spy.call_args.args
            self.assertEqual(positional[1:], ("tenant", operation))
            self.assertEqual(spy.call_args.kwargs, {"projection_limit": expected})

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

    def test_function_group_rejects_missing_and_future_arguments(self) -> None:
        for arguments in (
            ("function",),
            ("function", "show"),
            ("function", "show", "echo", "--receipt-id", "fpr_1"),
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

        arguments = argparse.Namespace(
            command="function",
            function_command="receipts",
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
