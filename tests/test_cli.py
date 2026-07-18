import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

from cement_runtime.cli import main


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(self.temporary.cleanup)
        self.database = str(pathlib.Path(self.temporary.name) / "cli.db")
        self.base = ["--db", self.database, "--partition", "tenant"]

    def run_cli(self, *arguments: str):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main([*self.base, *arguments])
        return status, json.loads(stdout.getvalue()) if stdout.getvalue() else None, stderr.getvalue()

    def test_full_operator_lifecycle(self) -> None:
        status, registered, _ = self.run_cli(
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
        self.assertEqual(status, 0)
        self.assertEqual(registered["revision"], 1)

        adapter = pathlib.Path("examples/echo_adapter.py").resolve()
        source = json.dumps([sys.executable, str(adapter)])
        for number in (1, 2):
            status, pending, _ = self.run_cli(
                "handle",
                "echo",
                "--input",
                '{"x":1}',
                "--request-id",
                f"cli-{number}",
                "--source-command",
                source,
            )
            self.assertEqual(status, 0)
            self.assertEqual(pending["status"], "review_required")
            _, queue, _ = self.run_cli("proposal", "list")
            self.assertIn(pending["proposal_id"], {item["id"] for item in queue})
            status, resolved, _ = self.run_cli(
                "proposal",
                "review",
                pending["proposal_id"],
                "--reviewer",
                "operator",
                "--decision",
                "accept",
            )
            self.assertEqual(status, 0)
            self.assertEqual(resolved["source"], "confirmed")
            _, polled, _ = self.run_cli("request", f"cli-{number}")
            self.assertEqual(polled["example_id"], resolved["example_id"])

        _, compiled, _ = self.run_cli("compile", "echo")
        artifact_id = compiled["created"][0]
        _, report, _ = self.run_cli("verify", artifact_id)
        self.assertTrue(report["passed"])
        _, stored_report, _ = self.run_cli("report", "show", report["id"])
        self.assertEqual(stored_report["scope_hash"], report["scope_hash"])
        self.assertEqual(stored_report["test_count"], report["tests"])
        _, promotion, _ = self.run_cli(
            "promote",
            artifact_id,
            "--scope-hash",
            report["scope_hash"],
            "--actor",
            "release-manager",
        )
        self.assertEqual(promotion["artifact_id"], artifact_id)
        _, hit, _ = self.run_cli(
            "handle", "echo", "--input", '{"x":1}', "--request-id", "cli-hit"
        )
        self.assertEqual(hit["source"], "artifact")
        self.assertEqual(hit["output"], {"kind": "echo", "value": {"x": 1}})

    def test_machine_readable_error(self) -> None:
        status, output, stderr = self.run_cli("verify", "art_missing")
        self.assertEqual(status, 3)
        self.assertIsNone(output)
        self.assertEqual(json.loads(stderr)["error"], "not_found")

    def test_usage_errors_and_oversized_stdin_are_machine_readable(self) -> None:
        status, output, stderr = self.run_cli("verify")
        self.assertEqual(status, 2)
        self.assertIsNone(output)
        self.assertEqual(json.loads(stderr)["error"], "invalid")

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


if __name__ == "__main__":
    unittest.main()
