"""M5.1 closure probe: each targeted removal of a §3 obligation reds tests/test_switch_battery.py.

Usage (from a checkout): `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python
3.13 python .agent/decisions/m5u1-mutants.py` — compiles each mutant from the live method source
in memory (no file changes), runs the switch battery under it, prints KILLED/SURVIVED, exits 1 on
any survivor. Mutants = reviewer-7's C4 removals (closing review of M5.1).
"""

from __future__ import annotations

import inspect
import io
import sys
import textwrap
import unittest
from unittest.mock import patch

from cement_runtime import System

import tests.test_switch_battery as battery

MUTANTS = (
    ("P-d removed", "_pin_checks", "passed=counter == 0,", "passed=True,"),
    (
        "retired suspension refused",
        "suspend_artifact",
        'if row["status"] == "suspended":',
        'if row["status"] in {"retired", "suspended"}:',
    ),
    (
        "off verifies anyway",
        "serving",
        "return state, None",
        "self._verify_function_snapshot(connection, partition=partition, operation=operation,"
        " expected_function_hash=None)\n            return state, None",
    ),
    ("diff drops changed keys", "diff_versions", "changed=tuple(", "changed=() if True else tuple("),
    (
        "pin reads a fresh autocommit connection",
        "_verify_pinned_snapshot",
        "return self._pin_checks(\n        connection,",
        "fresh = self.store._connect(read_only=True)\n    return self._pin_checks(\n        fresh,",
    ),
)


def main() -> int:
    survivors = []
    for label, method, anchor, replacement in MUTANTS:
        original = getattr(System, method)
        source = textwrap.dedent(inspect.getsource(original))
        assert source.count(anchor) == 1, (label, method)
        mutated = source.replace(anchor, replacement)
        assert mutated != source
        namespace = dict(original.__globals__)
        exec(compile(mutated, f"<{label}>", "exec"), namespace)  # noqa: S102 — the probe compiles its own mutant
        with patch.object(System, method, namespace[method]):
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
                unittest.defaultTestLoader.loadTestsFromModule(battery)
            )
        killed = bool(result.failures or result.errors)
        print(f"{label:40} {'KILLED' if killed else 'SURVIVED'}")
        if not killed:
            survivors.append(label)
    print(f"survivors: {survivors or 'none'}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
