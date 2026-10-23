"""p34: `examples/command_source` ships as its own wheel, `cement-command-source`.

The distribution metadata is pinned statically here (the build itself = the two-wheel smoke
`.agent/decisions/p34-two-wheel-smoke.sh`); the runner command `main` runs in-process against a
real ledger with the bundled stub adapter.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import re
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "command_source"
sys.path.insert(0, str(EXAMPLE_DIR))

import command_source  # noqa: E402

from cement_runtime import System  # noqa: E402

ADAPTER = [sys.executable, str(EXAMPLE_DIR / "example_adapter.py")]
FAILING = [sys.executable, "-c", "raise SystemExit(1)"]


def _project(path: pathlib.Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


class DistributionMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _project(EXAMPLE_DIR / "pyproject.toml")
        self.core = _project(ROOT / "pyproject.toml")

    def test_the_runner_script_names_the_shipped_main(self) -> None:
        scripts = self.provider["project"]["scripts"]
        self.assertEqual(
            scripts, {"cement-command-source": "cement_command_source.command_source:main"}
        )
        self.assertTrue(callable(command_source.main))

    def test_the_wheel_maps_the_flat_modules_into_one_package(self) -> None:
        wheel = self.provider["tool"]["hatch"]["build"]["targets"]["wheel"]
        self.assertEqual(wheel["only-include"], ["command_source.py", "_command_supervisor.py"])
        self.assertEqual(wheel["sources"], {"": "cement_command_source"})
        for name in wheel["only-include"]:
            self.assertTrue((EXAMPLE_DIR / name).is_file(), name)

    def test_the_core_range_admits_this_core_and_stops_at_its_next_minor(self) -> None:
        (requirement,) = self.provider["project"]["dependencies"]
        floor, ceiling = re.fullmatch(
            r"cement-runtime>=(\d+\.\d+\.\d+),<(\d+\.\d+)", requirement
        ).groups()
        major, minor, _ = (int(part) for part in self.core["project"]["version"].split("."))
        self.assertEqual(floor, self.core["project"]["version"])
        self.assertEqual(ceiling, f"{major}.{minor + 1}")
        self.assertEqual(
            self.provider["project"]["requires-python"], self.core["project"]["requires-python"]
        )

    def test_the_backend_pin_equals_its_hashed_constraint(self) -> None:
        (requires,) = self.provider["build-system"]["requires"]
        constraints = (EXAMPLE_DIR / "build-constraints.txt").read_text(encoding="utf-8")
        pinned = re.findall(r"^([a-z0-9-]+)==(\S+) \\$", constraints, re.MULTILINE)
        self.assertIn(tuple(requires.split("==")), pinned)
        hashes = re.findall(r"--hash=sha256:[0-9a-f]{64}", constraints)
        self.assertGreaterEqual(len(hashes), len(pinned))
        self.assertIn(f"echo {requires} | uv pip compile", constraints)

    def test_the_license_copy_equals_the_repository_license(self) -> None:
        self.assertEqual(self.provider["project"]["license-files"], ["LICENSE"])
        self.assertEqual(
            (EXAMPLE_DIR / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes()
        )


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-p34-")
        self.addCleanup(directory.cleanup)
        self.database = str(pathlib.Path(directory.name) / "ledger.db")
        System(self.database).register_operation("tenant-a", "echo")

    def run_main(self, *argv: str, stdin: str = "") -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        streams = mock.patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin.encode())))
        with streams, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = command_source.main(list(argv))
        return status, stdout.getvalue(), stderr.getvalue()

    def proposals(self) -> list[dict]:
        return [
            event
            for event in System(self.database).events("tenant-a")
            if event["kind"] == "proposal.created"
        ]

    def test_a_proposal_carries_the_adapter_answer(self) -> None:
        status, stdout, stderr = self.run_main(
            "--db", self.database, "--partition", "tenant-a", "echo",
            "--input", '{"n": 12}', "--", *ADAPTER,
        )
        self.assertEqual((status, stderr), (0, ""))
        (created,) = self.proposals()
        self.assertEqual(json.loads(stdout), {"proposal_id": created["subject_id"]})
        proposal = System(self.database).proposal("tenant-a", created["subject_id"])
        self.assertEqual(proposal["input"], {"n": 12})
        self.assertEqual(proposal["proposed_output"], {"kind": "echo", "value": {"n": 12}})
        self.assertEqual(proposal["provenance"]["adapter"], "command")

    def test_stdin_input_and_environment_defaults(self) -> None:
        environment = {"CEMENT_DB": self.database, "CEMENT_PARTITION": "tenant-a"}
        with mock.patch.dict("os.environ", environment):
            status, stdout, _ = self.run_main(
                "echo", "--input", "-", "--", *ADAPTER, stdin='{"n": 3}'
            )
        self.assertEqual(status, 0)
        (created,) = self.proposals()
        self.assertEqual(json.loads(stdout), {"proposal_id": created["subject_id"]})
        proposal = System(self.database).proposal("tenant-a", created["subject_id"])
        self.assertEqual(proposal["proposed_output"], {"kind": "echo", "value": {"n": 3}})

    def test_stdin_input_is_bounded_on_byte_and_text_streams(self) -> None:
        argv = ("--db", self.database, "--partition", "tenant-a", "echo", "--input", "-", "--", *ADAPTER)
        limit = command_source.DEFAULT_MAX_BYTES
        oversized = '"' + "x" * limit + '"'
        bad_utf8 = io.TextIOWrapper(io.BytesIO(b'"\xff"'))
        cases = {
            "bytes over the limit": (io.TextIOWrapper(io.BytesIO(oversized.encode())), f"JSON stdin exceeds {limit} bytes"),
            "text over the limit": (io.StringIO(oversized), f"JSON stdin exceeds {limit} characters"),
            "invalid UTF-8": (bad_utf8, "JSON stdin is not valid UTF-8"),
        }
        for name, (stream, message) in cases.items():
            with self.subTest(case=name), mock.patch.object(sys, "stdin", stream):
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    status = command_source.main(list(argv))
                self.assertEqual((status, stdout.getvalue()), (2, ""))
                self.assertEqual(json.loads(stderr.getvalue()), {"error": "invalid", "message": message})
        with mock.patch.object(sys, "stdin", io.StringIO('{"n": 5}')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command_source.main(list(argv)), 0)
        (created,) = self.proposals()
        proposal = System(self.database).proposal("tenant-a", created["subject_id"])
        self.assertEqual(proposal["input"], {"n": 5})

    def test_refusals_follow_the_core_exit_classes_and_write_nothing(self) -> None:
        missing = str(pathlib.Path(self.database).with_name("absent.db"))
        base = ("--partition", "tenant-a")
        cases = {
            "adapter failure": (
                (*base, "--db", self.database, "echo", "--input", "{}", "--", *FAILING),
                2, {"error": "invalid", "message": "candidate source failed"},
            ),
            "unregistered": (
                (*base, "--db", self.database, "other", "--input", "{}", "--", *ADAPTER),
                3, {"error": "not_found", "message": "operation is not registered in this partition"},
            ),
            "no ledger path": (
                (*base, "echo", "--input", "{}", "--", *ADAPTER),
                2, {"error": "invalid", "message": "--db or CEMENT_DB is required"},
            ),
            "missing ledger": (
                (*base, "--db", missing, "echo", "--input", "{}", "--", *ADAPTER),
                5, {"error": "integrity", "message": "ledger file is missing or unreadable"},
            ),
            "abbreviated option": (
                (*base, "--db", self.database, "echo", "--inp", "{}", "--", *ADAPTER),
                2, {"error": "invalid", "message": "the following arguments are required: --input"},
            ),
            "no adapter": (
                (*base, "--db", self.database, "echo", "--input", "{}"),
                2, {"error": "invalid", "message": "the following arguments are required: adapter"},
            ),
            "repeated key": (
                (*base, "--db", self.database, "echo", "--input", '{"a":1,"a":2}', "--", *ADAPTER),
                2, None,
            ),
        }
        with mock.patch.dict("os.environ", {}, clear=False) as environment:
            environment.pop("CEMENT_DB", None)
            for name, (argv, expected, error) in cases.items():
                with self.subTest(case=name):
                    status, stdout, stderr = self.run_main(*argv)
                    self.assertEqual((status, stdout), (expected, ""))
                    payload = json.loads(stderr)
                    if error is not None:
                        self.assertEqual(payload, error)
                    else:
                        self.assertEqual(payload["error"], "invalid")
        self.assertEqual(self.proposals(), [])
        self.assertFalse(pathlib.Path(missing).exists())


if __name__ == "__main__":
    unittest.main()
