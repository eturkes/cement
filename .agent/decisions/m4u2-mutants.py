"""M4.2 closure probe: each targeted removal of a §5 obligation reds the projection battery.

Usage (from a checkout): `PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python
3.13 python .agent/decisions/m4u2-mutants.py` — compiles each mutant from the live source in
memory (no file changes), runs tests/test_projection_lifecycle_battery.py under it, prints
KILLED/SURVIVED, exits 1 on a survivor outside EQUIVALENT or a kill inside it. Mutants =
reviewer-10's F5 removals + one per fix that closed F1/F2 (closing review of M4.2).
"""

from __future__ import annotations

import inspect
import io
import sys
import textwrap
import unittest
from types import FunctionType
from unittest.mock import patch

import cement_runtime.function as function_module
from cement_runtime import System

import tests.test_projection_lifecycle_battery as battery

# (label, owner, name, anchor, replacement); owner = System (method) | a module (function).
MUTANTS = (
    ("V2 unwitnessed layout accepted", System, "set_projection", 'if report["unwitnessed_layouts"]:', "if False:"),
    ("V3 merged outputs accepted", System, "set_projection", 'if report["merged_outputs"]:', "if False:"),
    ("V4 unprojecting program accepted", System, "set_projection", 'if not report["projected"]:', "if False:"),
    (
        "stale builds kept",
        System,
        "set_projection",
        "AND status IN ('draft', 'verified')",
        "AND status = 'impossible'",
    ),
    (
        "X7 review misses projected contrary",
        System,
        "review",
        'and artifact["output_json"] != final.text',
        "and False",
    ),
    ("X7 live misses projected contrary", System, "_contradicted", 'if key == row["input_json"]:', "if False:"),
    (
        "F2 review raw-key contradicts projected",
        System,
        "review",
        "AND status = 'promoted' AND projection_hash IS NULL",
        "AND status = 'promoted'",
    ),
    ("F2 live raw-key contradicts projected", System, "_contradicted", 'if row["projection_hash"] is None:', "if True:"),
    (
        "F2 P-d raw-key counts projected",
        System,
        "_pin_checks",
        "AND a.projection_hash IS NULL",
        "",
    ),
    (
        "F1 reconstruction mixes programs",
        System,
        "_reconstruct_function_receipt",
        'if artifact_row["projection_hash"] != receipt_row["projection_hash"]:',
        "if False:",
    ),
    (
        "F1 promotion keeps previous program",
        System,
        "_function_promotion_plan",
        'if row["projection_hash"] != build_program_hash:',
        "if False:",
    ),
    ("structural probe ignored", System, "_run_verification", "if not probe_ok:", "if False:"),
    (
        "preview readiness skips policy gates",
        System,
        "test_projection",
        'assessment["policy_failures"] or assessment["integrity_failures"]',
        "False",
    ),
    ("memo clears when full", System, "_case_key_text", "del memo[next(iter(memo))]", "memo.clear()"),
    ("vector drops abi check", System, "_verify_function_snapshot", "        abi_check,\n", ""),
    (
        "bundle evaluation opens a ledger",
        function_module,
        "evaluate",
        "    key = input_json",
        "    __import__('sqlite3').connect(':memory:').close()\n    key = input_json",
    ),
)

# Equivalent mutants: no input distinguishes them, so they must SURVIVE (a kill = a wrong ruling).
EQUIVALENT = {
    "V4 unprojecting program accepted": "V1 parses 1+ layouts and V2 requires each witnessed by a "
    "projecting active example, so V2 passing implies V4",
}


def _run() -> unittest.TestResult:
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(battery)
    )


def main() -> int:
    baseline = _run()
    assert baseline.wasSuccessful() and baseline.testsRun > 0, "the battery must be green unmutated"
    survivors = []
    for label, owner, name, anchor, replacement in MUTANTS:
        static = inspect.getattr_static(owner, name)
        original = getattr(owner, name)
        source = textwrap.dedent(inspect.getsource(original))
        assert source.count(anchor) == 1, (label, name, source.count(anchor))
        mutated = source.replace(anchor, replacement)
        namespace = dict(original.__globals__)
        exec(compile(mutated, f"<{label}>", "exec"), namespace)  # noqa: S102 — the probe compiles its own mutant
        mutant = namespace[name]
        if isinstance(owner, type):
            replacement_attr = staticmethod(mutant) if isinstance(static, staticmethod) else mutant
            with patch.object(owner, name, replacement_attr):
                result = _run()
        else:
            # Module functions are imported by name into the battery: swap the code object.
            assert isinstance(original, FunctionType)
            code = original.__code__
            original.__code__ = mutant.__code__
            try:
                result = _run()
            finally:
                original.__code__ = code
        killed = bool(result.failures or result.errors)
        verdict = "KILLED" if killed else "SURVIVED"
        print(f"{label:42} {verdict}{' (equivalent)' if label in EQUIVALENT else ''}")
        if killed == (label in EQUIVALENT):
            survivors.append(label)
    print(f"unexpected: {survivors or 'none'}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
