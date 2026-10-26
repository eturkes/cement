"""F8: each source read once; missing targets + self-anchors reuse the same snapshot."""
import contextlib
import io
import pathlib
import re
import runpy
import sys
import tempfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT
read_text = pathlib.Path.read_text


def measured(call, target):
    calls = 0
    def read(path, *args, **kwargs):
        nonlocal calls
        if path.resolve() == target.resolve():
            calls += 1
        return read_text(path, *args, **kwargs)
    with patch.object(pathlib.Path, "read_text", read), contextlib.redirect_stdout(io.StringIO()):
        rc = call()
    return rc, calls


with tempfile.TemporaryDirectory(prefix="F8-", dir=SCRATCH) as directory:
    root = pathlib.Path(directory)
    target = root / "target.txt"
    target.write_text("alpha line\n")
    report = root / "anchors.md"
    anchors = runpy.run_path(str(ROOT / ".agent/validate-anchors"))
    def run_anchor(count):
        report.write_text("```anchors\n" + "target.txt\t1\talpha line\n" * count + "```\n")
        with patch.object(sys, "argv", ["validate-anchors", str(report), "--root", str(root)]):
            return measured(anchors["main"], target)
    rc, count = run_anchor(1)
    assert (rc, count) == (0, 1), (rc, count)
    print("CONTROL: one valid anchor, one source read (rc=0)")
    rc, anchor_reads = run_anchor(64)
    assert rc == 0
    print(f"OBSERVED: 64 anchors to one file -> {anchor_reads} full-file reads")

    target.unlink()
    rc, count = run_anchor(64)
    assert (rc, count) == (1, 1), (rc, count)
    print("MISSING: 64 bad anchors -> one failed read, rc=1")
    report.write_text("```anchors\nanchors.md\t1\t```anchors\n```\n")
    with patch.object(sys, "argv", ["validate-anchors", str(report), "--root", str(root)]):
        rc, count = measured(anchors["main"], report)
    assert (rc, count) == (0, 1), (rc, count)
    print("SELF: report anchors itself -> one source read, rc=0")

    ns = runpy.run_path(str(ROOT / ".agent/decisions/m3u5a-suite-validate.py"))
    battery = root / "battery.py"
    filled = re.sub(r'self\.fail\("UNFILLED [^\"]+"\)', 'self.assertTrue(True)', ns["emit_stub"]())
    battery.write_text(filled)
    rc, suite_reads = measured(lambda: ns["grade"](battery), battery)
    assert rc == 0
    print(f"OBSERVED: 60 test bodies in one battery -> {suite_reads} full-file reads")

if anchor_reads != 1 or suite_reads != 1:
    print("RED: validator source caches/read loops re-read identical files once per row")
    raise SystemExit(1)
print("GREEN")
