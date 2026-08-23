#!/usr/bin/env python
"""Mutation battery for every predicate `System.resolve` adds.

A green suite is never closure: deleting a behaviour together with its pin leaves the gate green
and the test count unchanged. This script is the mechanical form of contract section 10's closure
criterion - every obligation must have a committed test that fails when the code discharging it
alone is removed.

    uv run python .agent/decisions/m3u2b-mutants.py [--id ID ...] [--verdict MODULE ...] [--full]

Default verdict module is the unit battery, which keeps a sweep to seconds per mutant instead of
the full suite's ~154 s. `--full` re-runs the whole suite on a survivor, which separates "the
battery does not pin it" from "nothing pins it".

Each mutant is addressed by a UNIQUE anchor string, never a line number or an occurrence index.
The run asserts the anchor occurs exactly once, asserts the patch changed the file, purges
`__pycache__` under `PYTHONDONTWRITEBYTECODE=1` (CPython invalidates bytecode on `(mtime, size)`,
so a length-preserving edit inside one mtime-second would otherwise run the ORIGINAL code and
report a live mutant as surviving), restores byte-exactly, and proves the restore by hash.

Verdicts: `killed` = a verdict module fails. `survived` = it passes. `killed-by-suite` = only the
wider suite catches it, which is a battery coverage gap. Exit 0 only when every mutant is killed
by a verdict module or is a declared equivalent.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve()
while not (ROOT / "pyproject.toml").exists():
    if ROOT == ROOT.parent:
        raise SystemExit("pyproject.toml not found above this script")
    ROOT = ROOT.parent

SYSTEM = "src/cement_runtime/system.py"
MODELS = "src/cement_runtime/models.py"
PACKAGE = "src/cement_runtime/__init__.py"
BATTERY = ["tests.test_resolve_battery"]

VALIDATE3 = (
    '        partition = _name(partition, "partition")\n'
    '        operation = _name(operation, "operation")\n'
    "        if expected_function_hash is not None:"
)
HASH_THEN_INPUT = (
    "        if expected_function_hash is not None:\n"
    '            _digest(expected_function_hash, "expected_function_hash")\n'
    "        input_json = canonicalize(input_value)"
)
INPUT_THEN_VERIFY = (
    "        input_json = canonicalize(input_value)\n"
    "\n"
    "        verification = self.verify_function(\n"
    "            partition,\n"
    "            operation,\n"
    "            expected_function_hash=expected_function_hash,\n"
    "        )"
)
VERIFY_CALL = (
    "        verification = self.verify_function(\n"
    "            partition,\n"
    "            operation,\n"
    "            expected_function_hash=expected_function_hash,\n"
    "        )"
)
GATE = "        if not verification.passed or document is None:"
FAILED_RETURN = "            return FunctionResolution(verification=verification, match=None)"
BIND_AND_GATE = f"        document = verification.document\n{GATE}"
EVAL_CALL = "            match=evaluate(document, input_json=input_json),"
KEYWORD_MARKER = (
    "        input_value: object,\n"
    "        *,\n"
    "        expected_function_hash: str | None = None,\n"
    "    ) -> FunctionResolution:"
)
DOC_OPEN = '        """Verify one promoted-set snapshot, then look the input up inside it.'
RESOLUTION_DECORATOR = "@dataclass(frozen=True, slots=True)\nclass FunctionResolution:"
RESOLUTION_FIELDS = "    verification: FunctionVerification\n    match: FunctionMatch | None"


@dataclass(frozen=True)
class Mutant:
    identifier: str
    path: str
    old: str
    new: str
    obligation: str
    equivalent: bool = False


MUTANTS: tuple[Mutant, ...] = (
    # Section 2 - frozen public shape.
    Mutant(
        "keyword-marker-dropped",
        SYSTEM,
        KEYWORD_MARKER,
        KEYWORD_MARKER.replace("        *,\n", ""),
        "B01",
    ),
    Mutant(
        "resolution-not-frozen",
        MODELS,
        RESOLUTION_DECORATOR,
        "@dataclass(slots=True)\nclass FunctionResolution:",
        "B02",
    ),
    Mutant(
        "resolution-no-slots",
        MODELS,
        RESOLUTION_DECORATOR,
        "@dataclass(frozen=True)\nclass FunctionResolution:",
        "B02",
    ),
    Mutant(
        "resolution-kw-only",
        MODELS,
        RESOLUTION_DECORATOR,
        "@dataclass(frozen=True, slots=True, kw_only=True)\nclass FunctionResolution:",
        "B02",
    ),
    Mutant(
        "resolution-extra-field",
        MODELS,
        RESOLUTION_FIELDS,
        f"{RESOLUTION_FIELDS}\n    matched: bool = False",
        "B02",
    ),
    Mutant(
        "export-dropped",
        PACKAGE,
        '    "FunctionResolution",\n',
        "",
        "B03",
    ),
    Mutant(
        "export-misordered",
        PACKAGE,
        '    "FunctionReport",\n    "FunctionResolution",\n',
        '    "FunctionResolution",\n    "FunctionReport",\n',
        "B03",
    ),
    # Section 3 - the three states.
    Mutant(
        "passed-gate-inverted",
        SYSTEM,
        GATE,
        "        if verification.passed or document is None:",
        "B07/B11",
    ),
    Mutant(
        "document-guard-deleted",
        SYSTEM,
        GATE,
        "        if not verification.passed:",
        "B14",
    ),
    Mutant(
        "gate-conjunction",
        SYSTEM,
        GATE,
        "        if not verification.passed and document is None:",
        "B14",
    ),
    Mutant(
        "failed-verdict-becomes-miss",
        SYSTEM,
        FAILED_RETURN,
        "            from .function import FunctionMatch as _MissShape\n"
        "\n"
        "            return FunctionResolution(\n"
        "                verification=verification,\n"
        "                match=_MissShape(matched=False, output=None, artifact_hash=None),\n"
        "            )",
        "B07/B10/B11",
    ),
    # Section 4 - argument validation and its precedence.
    Mutant(
        "partition-validation-dropped",
        SYSTEM,
        VALIDATE3,
        '        operation = _name(operation, "operation")\n'
        "        if expected_function_hash is not None:",
        "B15/B16",
    ),
    Mutant(
        "operation-validation-dropped",
        SYSTEM,
        VALIDATE3,
        '        partition = _name(partition, "partition")\n'
        "        if expected_function_hash is not None:",
        "B15/B16",
    ),
    Mutant(
        "name-validation-order-swapped",
        SYSTEM,
        VALIDATE3,
        '        operation = _name(operation, "operation")\n'
        '        partition = _name(partition, "partition")\n'
        "        if expected_function_hash is not None:",
        "B16",
    ),
    Mutant(
        "expected-hash-validation-dropped",
        SYSTEM,
        HASH_THEN_INPUT,
        "        input_json = canonicalize(input_value)",
        "B15/B16",
    ),
    Mutant(
        "expected-hash-validated-after-input",
        SYSTEM,
        HASH_THEN_INPUT,
        "        input_json = canonicalize(input_value)\n"
        "        if expected_function_hash is not None:\n"
        '            _digest(expected_function_hash, "expected_function_hash")',
        "B16",
    ),
    # Section 6 - all validation precedes the ledger read, one snapshot only.
    Mutant(
        "input-canonicalized-after-ledger-read",
        SYSTEM,
        INPUT_THEN_VERIFY,
        f"{VERIFY_CALL}\n        input_json = canonicalize(input_value)",
        "B17/B25",
    ),
    Mutant(
        "second-snapshot-for-document",
        SYSTEM,
        BIND_AND_GATE,
        "        document = self.verify_function(\n"
        "            partition,\n"
        "            operation,\n"
        "            expected_function_hash=expected_function_hash,\n"
        "        ).document\n"
        f"{GATE}",
        "B25/B26",
    ),
    # Section 7 and the forward into verify_function.
    Mutant(
        "expected-hash-not-forwarded",
        SYSTEM,
        VERIFY_CALL,
        "        verification = self.verify_function(\n"
        "            partition,\n"
        "            operation,\n"
        "        )",
        "B29",
    ),
    Mutant(
        "scope-arguments-swapped",
        SYSTEM,
        VERIFY_CALL,
        "        verification = self.verify_function(\n"
        "            operation,\n"
        "            partition,\n"
        "            expected_function_hash=expected_function_hash,\n"
        "        )",
        "B33",
    ),
    # Evaluation over the document value.
    Mutant(
        "input-not-forwarded-to-evaluate",
        SYSTEM,
        EVAL_CALL,
        '            match=evaluate(document, input_json=canonicalize({"cement": "mutant"})),',
        "B05/B06/B32",
    ),
    # Section 9 - the prose obligation.
    Mutant(
        "docstring-claims-cheap-and-cached",
        SYSTEM,
        DOC_OPEN,
        f"{DOC_OPEN}\n\n        This call is cheap, cached, and repeatable across calls.",
        "B31",
    ),
)


def run(selection: list[str], verdict_modules: list[str], *, full: bool) -> int:
    targets = sorted({mutant.path for mutant in MUTANTS})
    pristine = {path: (ROOT / path).read_text(encoding="utf-8") for path in targets}
    digests = {
        path: hashlib.sha256(text.encode("utf-8")).hexdigest() for path, text in pristine.items()
    }
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def purge() -> None:
        for cache in ROOT.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)

    def suite(modules: list[str]) -> bool:
        purge()
        completed = subprocess.run(
            ["uv", "run", "python", "-m", "unittest", *modules],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0

    print(f"control: pristine verdict modules {verdict_modules} ...", flush=True)
    if not suite(verdict_modules):
        print("CONTROL FAILED - the verdict modules are not green before mutation", file=sys.stderr)
        return 1
    print("control: green")

    chosen = [m for m in MUTANTS if not selection or m.identifier in selection]
    survivors: list[Mutant] = []
    gaps: list[Mutant] = []
    for mutant in chosen:
        source = pristine[mutant.path]
        count = source.count(mutant.old)
        if count != 1:
            print(f"ANCHOR-MISS {mutant.identifier}: anchor occurs {count} times", file=sys.stderr)
            return 1
        mutated = source.replace(mutant.old, mutant.new)
        if mutated == source:
            print(f"IDENTITY {mutant.identifier}: patch changed nothing", file=sys.stderr)
            return 1
        (ROOT / mutant.path).write_text(mutated, encoding="utf-8")
        try:
            verdict = "killed" if not suite(verdict_modules) else "survived"
            if verdict == "survived" and full:
                verdict = (
                    "survived"
                    if suite(["discover", "-s", "tests", "-t", "."])
                    else "killed-by-suite"
                )
        finally:
            (ROOT / mutant.path).write_text(source, encoding="utf-8")
            restored = hashlib.sha256(
                (ROOT / mutant.path).read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            if restored != digests[mutant.path]:
                print(f"RESTORE FAILED after {mutant.identifier}", file=sys.stderr)
                return 1
        tag = " (declared equivalent)" if mutant.equivalent else ""
        print(f"{verdict:16} {mutant.identifier:38} {mutant.obligation}{tag}", flush=True)
        if mutant.equivalent:
            continue
        if verdict == "survived":
            survivors.append(mutant)
        elif verdict == "killed-by-suite":
            gaps.append(mutant)

    purge()
    print(f"\nmutants={len(chosen)} survivors={len(survivors)} battery_gaps={len(gaps)}")
    for mutant in survivors:
        print(f"SURVIVOR {mutant.identifier} -> obligation {mutant.obligation} does not pin it")
    for mutant in gaps:
        print(f"BATTERY-GAP {mutant.identifier} -> only the wider suite kills it")
    return 1 if survivors or gaps else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", default=[], dest="ids")
    parser.add_argument("--verdict", action="append", default=[], dest="verdict")
    parser.add_argument("--full", action="store_true", help="re-run the whole suite on a survivor")
    arguments = parser.parse_args(argv)
    return run(arguments.ids, arguments.verdict or list(BATTERY), full=arguments.full)


if __name__ == "__main__":
    raise SystemExit(main())
