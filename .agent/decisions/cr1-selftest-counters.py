"""F7: neutralized correction binding must fail the grader self-test."""
import contextlib
import io
import pathlib
import re
import runpy
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
ns = runpy.run_path(str(ROOT / ".agent/decisions/m3u6a2-battery-validate.py"))
contract = ns["CONTRACT"].read_text()
battery = ns["BATTERY"].read_text()
bad = contract.replace(
    "\n## 9. Session boundaries",
    "\n- **C99** a correction naming nothing.\n\n## 9. Session boundaries", 1,
)
assert bad != contract
lines, failures = ns["report"](bad, battery)
assert "CORRECTION-BIND: 1 unbound ['C99']" in lines and failures > 0, lines
print("CONTROL: real report rejects the planted unbound correction")
# Neutralize one check in memory, without editing any tracked or scratch source.
with patch.dict(ns["report"].__globals__, BINDS=re.compile("")):
    lines, failures = ns["report"](bad, battery)
    assert "CORRECTION-BIND: 0 unbound" in lines and failures == 0, lines
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = ns["self_test"]()
print(f"OBSERVED: binding check disabled; self-test rc={rc}; {output.getvalue().splitlines()[-1]}")
if rc == 0:
    print("RED: self-test declares all controls firing although both correction-binding seeds are accepted")
    raise SystemExit(1)
print("GREEN")
