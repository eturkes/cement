"""F2: red/empty pristine tests refuse replay; green pristine tests retain kill credit."""
import argparse
import contextlib
import io
import json
import os
import pathlib
import runpy
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
PIN = "tests.test_probe.Probe.test_answer"
OPERATOR = "core/ReplaceBinaryOperator_Add_Sub"
SOURCE = "def answer():\n    return 1 + 2\n"
REAL_TEMP = tempfile.TemporaryDirectory
REAL_RUN = subprocess.run


def check(kind, expected):
    with REAL_TEMP(prefix="cr1-replay-", dir=ROOT) as directory:
        base = pathlib.Path(directory)
        template = base / "fixture"
        for folder in (template / "src/cement_runtime", template / "tests"):
            folder.mkdir(parents=True)
            (folder / "__init__.py").write_text("")
        (template / "src/cement_runtime/probe.py").write_text(SOURCE)
        test = "import unittest\nfrom cement_runtime.probe import answer\n"
        if kind != "empty":
            test += ("class Probe(unittest.TestCase):\n"
                     "    def test_answer(self):\n"
                     f"        self.assertEqual(answer(), {99 if kind == 'red' else 3})\n")
        (template / "tests/test_probe.py").write_text(test)
        selected = "tests.test_probe" if kind == "empty" else PIN
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(template / "src"))
        baseline = REAL_RUN([sys.executable, "-m", "unittest", selected], cwd=template,
                            env=env, capture_output=True, text=True)
        assert baseline.returncode in ({1} if kind == "red" else {0, 5} if kind == "empty" else {0}), baseline
        assert f"Ran {0 if kind == 'empty' else 1} test" in baseline.stderr, baseline
        print(f"CONTROL {kind}: rc={baseline.returncode}; ran={0 if kind == 'empty' else 1}")

        def temporary(*args, **kwargs):
            return REAL_TEMP(*args, **dict(kwargs, dir=base))

        def git(*args, **kwargs):
            if args[0] == "rev-parse":
                return "1" * 40 + "\n"
            if args[0] == "show":
                return SOURCE
            if args[0] == "ls-tree":
                return "__init__.py\ntest_probe.py\n"
            if args[:2] == ("worktree", "add"):
                shutil.copytree(template, pathlib.Path(args[3]))
                return ""
            raise AssertionError(args)

        def run(argv, *args, **kwargs):
            if argv[:3] == ["git", "worktree", "remove"]:
                return subprocess.CompletedProcess(argv, 0, "", "")
            return REAL_RUN(argv, *args, **kwargs)

        residue = base / "residue.jsonl"
        residue.write_text(json.dumps(dict(module="probe.py", pin=PIN, line=2,
                           operator=OPERATOR, occurrence=0, function="answer",
                           verdict="survived", verdict_at="survived-at")) + "\n")
        record = base / "record.txt"
        record.write_text(f"mutate: {PIN} @ {'1' * 40}\n")
        triage = runpy.run_path(str(ROOT / ".agent/survivor-triage"))
        triage["_at"].__globals__["_git"] = git
        args = argparse.Namespace(at="HEAD", from_file=residue, full=True,
                                  workers=1, timeout=10, out=None)
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(tempfile, "TemporaryDirectory", temporary), \
             patch.object(subprocess, "run", run), contextlib.redirect_stdout(output), \
             contextlib.redirect_stderr(errors):
            rc = triage["_at"](args, {PIN: ["probe.py:answer"]}, {PIN: "1" * 40})
        assert rc == expected, (kind, "triage", rc, output.getvalue(), errors.getvalue())
        assert ("killed-at 1" in output.getvalue()) == (expected == 0), output.getvalue()
        print(f"survivor-triage {kind}: rc={rc}; {output.getvalue().splitlines()[-1]}")

        kill = runpy.run_path(str(ROOT / ".agent/kill-check"))
        kill["main"].__globals__["ROOT"] = template
        kill["TRIAGE"]["_git"] = git
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["kill-check", str(record), str(residue), selected]), \
             patch.object(tempfile, "TemporaryDirectory", temporary), \
             patch.object(subprocess, "run", run), contextlib.redirect_stdout(output), \
             contextlib.redirect_stderr(errors):
            rc = kill["main"]()
        assert rc == expected, (kind, "kill", rc, output.getvalue(), errors.getvalue())
        assert ("1/1 killed" in output.getvalue()) == (expected == 0), output.getvalue()
        print(f"kill-check {kind}: rc={rc}; {output.getvalue().splitlines()[-1]}")


if __name__ == "__main__":
    for kind, expected in (("red", 2), ("empty", 2), ("green", 0)):
        check(kind, expected)
    print("GREEN: red/empty controls refused; green controls retain kill credit")
