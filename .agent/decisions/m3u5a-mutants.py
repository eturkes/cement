#!/usr/bin/env python
"""Mutation sweep over every predicate M3.5a's two CLI leaves add. Gate 3 of section 11.

    uv run python .agent/decisions/m3u5a-mutants.py [--id ID ...] [--verdict MODULE ...]
                                                    [--catalogue PATH] [--preflight] [--full]

A green suite is never closure. This sweep is the mechanical form of that rule: for every
predicate the unit adds, some committed test must fail when that predicate alone is weakened.

CATALOGUE-DRIVEN. Rows live in `m3u5a-mutants.json`, so a row can be added or re-anchored
without touching this runner. Each row is:

    id          stable identifier, quoted in every verdict
    site        the predicate under mutation, in words
    file        repo-relative path
    anchor      a UNIQUE substring of the file, never a line number or occurrence index
    replacement the bytes that replace it
    obligation  the contract obligation the mutant attacks
    expect      `killed` or `equivalent`; `equivalent` rows are the NAMED SURVIVOR SET
    note        why an `equivalent` row cannot be killed

MECHANICS, each one bought by a past defect:

- ANCHOR PRE-FLIGHT runs first and prints EVERY stale or ambiguous anchor at once. Aborting on
  the first one hides every later verdict, which turned a 41-mutant campaign into a mixed table.
- Each patch asserts its anchor occurs exactly once and asserts the bytes actually moved. A
  patch that silently failed to apply reports `survived` and reads exactly like a live mutant.
- `PYTHONDONTWRITEBYTECODE=1` plus a `__pycache__` purge. CPython invalidates bytecode on
  `(mtime, size)`, so a length-preserving edit inside one mtime-second otherwise runs the
  ORIGINAL code and manufactures a false survivor.
- Restore is byte-exact and proved by sha256 before the next mutant runs.
- The failing-test name is read from the summary header `FAIL: name (tests.M.C.name)`, never
  from the verbose progress line: a docstring pushes `... FAIL` onto the next line, and a
  mutant whose only witnesses carry docstrings then reads as a failure with no test.
- The UNMUTATED CONTROL runs first and its result is printed on the control line. Without it a
  broken harness reports every mutant killed and passes.
- The VERDICT MODULE LIST is printed on the control line and recorded PER ROW. A survivor count
  quoted without its verdict modules is meaningless: the same corpus read 13 survivors against
  one module and 0 against that module plus the obligation battery.

ACCEPTANCE is the NAMED SURVIVOR SET, never `zero survivors`: every `expect: killed` row must be
killed, and the survivors must equal exactly the `expect: equivalent` ids. A fifth survivor fails
while the ruled ones do not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "pyproject.toml").exists():
    if ROOT == ROOT.parent:
        raise SystemExit("pyproject.toml not found above this script")
    ROOT = ROOT.parent

DEFAULT_CATALOGUE = Path(__file__).resolve().parent / "m3u5a-mutants.json"
DEFAULT_VERDICT = ["tests.test_cli_channels", "tests.test_cli_channels_battery"]

# The summary header survives a docstring and a subtest; the verbose progress line does not.
SUMMARY = re.compile(r"^(?:FAIL|ERROR): (\S+) \(([^)]+)\)", re.MULTILINE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _purge_pycache() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def _run_modules(modules: list[str]) -> tuple[bool, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    _purge_pycache()
    # `discover` is a subcommand, so its flags follow it; module names take `-v` up front.
    argv = ["uv", "run", "python", "-m", "unittest"]
    argv += [modules[0], "-v", *modules[1:]] if modules[0] == "discover" else ["-v", *modules]
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, env=env)
    return proc.returncode == 0, proc.stdout + proc.stderr


def _witnesses(output: str) -> list[str]:
    return sorted({dotted for _, dotted in SUMMARY.findall(output)})


def _load(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["rows"] if isinstance(data, dict) else data
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"ABORT   duplicate mutant ids in {path}")
    return rows


def preflight(rows: list[dict[str, str]]) -> list[str]:
    """Report EVERY unusable anchor at once; a first-failure abort hides later verdicts."""

    bad: list[str] = []
    for row in rows:
        target = ROOT / row["file"]
        if not target.is_file():
            bad.append(f"{row['id']}: no file {row['file']}")
            continue
        anchor = row.get("anchor") or ""
        if not anchor:
            bad.append(f"{row['id']}: empty anchor")
            continue
        count = target.read_text(encoding="utf-8").count(anchor)
        if count != 1:
            bad.append(f"{row['id']}: anchor occurs {count}x in {row['file']}")
            continue
        if anchor == row.get("replacement"):
            bad.append(f"{row['id']}: replacement is identical to the anchor")
    return bad


def apply_one(row: dict[str, str], modules: list[str], full: bool) -> dict[str, object]:
    target = ROOT / row["file"]
    original = target.read_bytes()
    before = _sha256(target)
    text = original.decode("utf-8")
    if text.count(row["anchor"]) != 1:
        raise SystemExit(f"ABORT   {row['id']}: anchor is not unique at run time")
    mutated = text.replace(row["anchor"], row["replacement"])
    if mutated == text:
        raise SystemExit(f"ABORT   {row['id']}: patch changed no bytes")
    try:
        target.write_text(mutated, encoding="utf-8")
        green, output = _run_modules(modules)
        witnesses = _witnesses(output)
        verdict = "survived" if green else "killed"
        wider: list[str] = []
        if green and full:
            suite_green, suite_output = _run_modules(["discover", "-s", "tests", "-t", "."])
            if not suite_green:
                verdict = "killed-by-suite"
                wider = _witnesses(suite_output)
    finally:
        target.write_bytes(original)
        _purge_pycache()
    after = _sha256(target)
    if after != before:
        raise SystemExit(f"ABORT   {row['id']}: restore is not byte-exact ({before} -> {after})")
    return {
        "id": row["id"],
        "site": row["site"],
        "obligation": row.get("obligation", ""),
        "expect": row.get("expect", "killed"),
        "verdict": verdict,
        "verdict_modules": list(modules),
        "witnesses": witnesses[:6],
        "wider_witnesses": wider[:6],
        "restore": after,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="M3.5a mutation sweep")
    parser.add_argument("--id", action="append", default=[])
    parser.add_argument("--verdict", action="append", default=[])
    parser.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE))
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args(argv[1:])

    catalogue = Path(args.catalogue)
    rows = _load(catalogue)
    modules = args.verdict or list(DEFAULT_VERDICT)

    stale = preflight(rows)
    print(f"CATALOGUE: {catalogue} ({len(rows)} mutants)")
    print(f"STALE-ANCHORS: {len(stale)}")
    for line in stale:
        print(f"  {line}")
    if args.preflight:
        return 1 if stale else 0
    if stale:
        print("ABORT   re-anchor every row above before sweeping")
        return 1

    selected = [row for row in rows if not args.id or row["id"] in set(args.id)]
    unfilled = [row["id"] for row in selected if not row.get("anchor")]
    if unfilled:
        print(f"UNFILLED-MUTANTS: {len(unfilled)} {unfilled}")
        return 1

    control_green, control_output = _run_modules(modules)
    print(f"VERDICT-MODULES: {' '.join(modules)}")
    print(f"CONTROL: {'GREEN' if control_green else 'RED'}")
    if not control_green:
        print("ABORT   the unmutated control is red; every verdict below would be a false kill")
        for line in _witnesses(control_output)[:10]:
            print(f"  {line}")
        return 1

    results = [apply_one(row, modules, args.full) for row in selected]
    for result in results:
        marks = ",".join(result["witnesses"]) or "-"
        print(f"{result['id']:<6} {result['verdict']:<15} {result['obligation']:<6} {marks}")

    survived = sorted(r["id"] for r in results if r["verdict"] != "killed")
    declared = sorted(r["id"] for r in results if r["expect"] == "equivalent")
    print(f"MUTANTS: {len(results)}")
    print(f"KILLED: {sum(1 for r in results if r['verdict'] == 'killed')}")
    print(f"SURVIVORS: {len(survived)} {survived}")
    print(f"NAMED-SURVIVOR-SET: {len(declared)} {declared}")
    ok = survived == declared
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
