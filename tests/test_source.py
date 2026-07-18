import os
import pathlib
import signal
import sys
import tempfile
import time
import unittest
from unittest import mock

from cement_runtime.errors import CandidateSourceError, ValidationError
from cement_runtime.models import CandidateRequest
from cement_runtime.source import CommandCandidateSource


class CommandCandidateSourceTests(unittest.TestCase):
    def request(self) -> CandidateRequest:
        return CandidateRequest(
            partition="tenant",
            operation="echo",
            operation_revision=1,
            request_id="request-1",
            input={"x": 1},
        )

    def test_json_protocol_and_provenance_binding(self) -> None:
        script = (
            "import json,sys; r=json.load(sys.stdin); "
            "json.dump({'output':r['input'],'provenance':{'model':'fake'}},sys.stdout)"
        )
        source = CommandCandidateSource(
            [sys.executable, "-c", script],
            source_id="test-source",
        )
        candidate = source.propose(self.request())
        self.assertEqual(candidate.output, {"x": 1})
        self.assertEqual(candidate.provenance["source_id"], "test-source")
        self.assertEqual(candidate.provenance["reported"], {"model": "fake"})

    def test_nonzero_stderr_is_not_reflected(self) -> None:
        source = CommandCandidateSource(
            [sys.executable, "-c", "import sys;sys.stderr.write('SECRET');sys.exit(7)"]
        )
        with self.assertRaises(CandidateSourceError) as caught:
            source.propose(self.request())
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertIn("status 7", str(caught.exception))

    def test_timeout_and_invalid_response_are_inert_failures(self) -> None:
        timeout = CommandCandidateSource(
            [sys.executable, "-c", "import time;time.sleep(0.2)"],
            timeout_seconds=0.01,
        )
        with self.assertRaisesRegex(CandidateSourceError, "timed out"):
            timeout.propose(self.request())
        invalid = CommandCandidateSource(
            [sys.executable, "-c", "print('{}')"],
        )
        with self.assertRaisesRegex(CandidateSourceError, "exactly"):
            invalid.propose(self.request())

    def test_stdout_and_stderr_are_stream_bounded(self) -> None:
        stdout = CommandCandidateSource(
            [sys.executable, "-c", "import sys;sys.stdout.write('x'*100000)"],
            max_output_bytes=1_024,
        )
        with self.assertRaisesRegex(CandidateSourceError, "byte limit"):
            stdout.propose(self.request())
        stderr = CommandCandidateSource(
            [sys.executable, "-c", "import sys;sys.stderr.write('x'*100000)"],
            max_output_bytes=1_024,
        )
        with self.assertRaisesRegex(CandidateSourceError, "byte limit"):
            stderr.propose(self.request())

    def test_oversized_provenance_is_a_candidate_source_error(self) -> None:
        script = (
            "import json,sys;"
            "json.dump({'output':None,'provenance':{'x':'y'*70000}},sys.stdout)"
        )
        source = CommandCandidateSource(
            [sys.executable, "-c", script], max_output_bytes=100_000
        )
        with self.assertRaisesRegex(CandidateSourceError, "provenance"):
            source.propose(self.request())

    def test_constructor_rejects_ambiguous_or_invalid_scalars(self) -> None:
        invalid = (
            lambda: CommandCandidateSource("python"),
            lambda: CommandCandidateSource(iter(())),
            lambda: CommandCandidateSource(["python\0bad"]),
            lambda: CommandCandidateSource(["python"], source_id="\ud800"),
            lambda: CommandCandidateSource(["python"], source_id="bad\x7fsource"),
            lambda: CommandCandidateSource(["python"], timeout_seconds=True),
            lambda: CommandCandidateSource(["python"], max_output_bytes=True),
            lambda: CommandCandidateSource(["python"], environment={"BAD\0KEY": "value"}),
            lambda: CommandCandidateSource(["\ud800"]),
        )
        for construct in invalid:
            with self.subTest(construct=construct), self.assertRaises(ValidationError):
                construct()

    def test_start_failure_is_a_domain_error(self) -> None:
        source = CommandCandidateSource(["/definitely/missing/cement-adapter"])
        with self.assertRaisesRegex(CandidateSourceError, "could not be started"):
            source.propose(self.request())

    @unittest.skipUnless(
        sys.platform.startswith("linux") and pathlib.Path("/proc").is_dir(),
        "Linux subreaper supervision requires /proc",
    )
    def test_detached_descendants_are_killed_and_reaped(self) -> None:
        script = (
            "import json,subprocess,sys;"
            "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
            "start_new_session=True);"
            "json.dump({'output':{'pid':child.pid},'provenance':{}},sys.stdout)"
        )
        source = CommandCandidateSource([sys.executable, "-c", script])
        candidate = source.propose(self.request())
        pid = candidate.output["pid"]
        self.assertIs(type(pid), int)
        self.assertFalse(pathlib.Path(f"/proc/{pid}").exists())

    @unittest.skipUnless(
        sys.platform.startswith("linux") and pathlib.Path("/proc").is_dir(),
        "Linux process-group recovery requires /proc",
    )
    def test_outer_watchdog_kills_adapter_if_supervisor_dies(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as temporary:
            pid_file = pathlib.Path(temporary) / "adapter.pid"
            script = (
                "import os,pathlib,signal,time;"
                f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()));"
                "os.kill(os.getppid(),signal.SIGKILL);time.sleep(60)"
            )
            source = CommandCandidateSource(
                [sys.executable, "-c", script], timeout_seconds=10
            )
            with self.assertRaises(CandidateSourceError):
                source.propose(self.request())
            pid = int(pid_file.read_text())
            deadline = time.monotonic() + 1.0
            while pathlib.Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            if pathlib.Path(f"/proc/{pid}").exists():
                os.kill(pid, signal.SIGKILL)
                self.fail("adapter survived supervisor death and outer watchdog cleanup")

    def test_unsupervised_inherited_stream_fails_inert(self) -> None:
        child = (
            "import sys,time;time.sleep(2.5);sys.stdout.write('x');sys.stdout.flush()"
        )
        script = (
            "import json,subprocess,sys;"
            "payload=json.dumps({'output':None,'provenance':{}},separators=(',',':'));"
            f"subprocess.Popen([sys.executable,'-c',{child!r}],stdin=subprocess.DEVNULL,"
            "stdout=sys.stdout,stderr=subprocess.DEVNULL,start_new_session=True);"
            "sys.stdout.write(payload+' '*(65536-len(payload)));sys.stdout.flush()"
        )
        source = CommandCandidateSource(
            [sys.executable, "-c", script], max_output_bytes=65_536
        )
        with mock.patch.object(sys, "platform", "darwin"):
            with self.assertRaisesRegex(CandidateSourceError, "cleanup"):
                source.propose(self.request())


if __name__ == "__main__":
    unittest.main()
