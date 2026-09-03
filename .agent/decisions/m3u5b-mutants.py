#!/usr/bin/env python3
"""Gate 3 for M3.5b: the REINSERTION sweep, and gate 2's red-control credential.

    uv run python .agent/decisions/m3u5b-mutants.py
    uv run python .agent/decisions/m3u5b-mutants.py --kind reinsertion
    uv run python .agent/decisions/m3u5b-mutants.py --id M07 --id M12
    uv run python .agent/decisions/m3u5b-mutants.py --verdict tests.test_cli_removal_battery

ONE CATALOGUE, READ TWO WAYS. `.agent/decisions/m3u5b-mutants.json` holds one row per battery
obligation clause. Rows tagged `reinsertion` restore something the removal deleted and are gate
3; rows tagged `sensitivity` perturb a preserved invariant and are gate 2's independent red
control. Contract section 11 requires both, and they are the same instrument.

WHY REINSERTION. Section 8 specified gate 3 as a sweep over TOUCHED PREDICATES read from the
final tree. The seven `EDITS` delete five predicates and add none, so that set is EMPTY and the
gate passes without running anything. Only a mutation that RESTORES what was removed can bind a
removal, which is contract A22.

Mechanics, each one paid for by a defect in this project's history:

- AN ISOLATED WORKTREE, never the primary tree. A sweep patching `src/` in place contaminates
  `git status` for its whole run, and killing it strands a live mutant in the working tree. The
  worktree shares the object store, so `git show 36f7890:<path>` still resolves for the byte
  equality obligations, and it is removed on exit.
- A PREFLIGHT ANCHOR CENSUS that reports EVERY unusable anchor at once. A first-failure abort
  hides every later verdict and leaves a MIXED table nobody can quote.
- `PYTHONDONTWRITEBYTECODE=1` plus a `__pycache__` purge. CPython invalidates bytecode on
  `(mtime, size)`, so a length-preserving edit inside one mtime-second runs the ORIGINAL code
  and reports a live mutant as surviving.
- A POSITIVE CONTROL PER MUTANT: the anchor occurs exactly once, and the patched bytes actually
  differ. A patch step that silently no-ops prints exactly like a surviving mutant.
- THE UNMUTATED CONTROL RUNS FIRST and its result is printed on the control line. A red control
  makes every verdict below a false kill.
- WITNESSES COME FROM THE SUMMARY HEADER `FAIL: name (module.Class.name)`, never from the
  verbose `... FAIL` line, which a docstring moves onto the next line.

VERDICTS. `killed` means the row's own `target_test` went red -- the credential gate 2 needs,
because a control that turns some OTHER test red proves nothing about the obligation it was
aimed at. `misdirected` means the run went red without the target: a real signal, and not a
kill. `survived` means the verdict modules stayed green.

ACCEPTANCE is the NAMED SURVIVOR SET, never `zero survivors`. Rows carrying `expect:
equivalent` are that set; every other row must be `killed`. A survivor count without names is
not checkable at the next unit, which is contract X35.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CATALOGUE = HERE / "m3u5b-mutants.json"

DEFAULT_VERDICT = (
    "tests.test_cli_removal_battery",
    "tests.test_cli_channels",
    "tests.test_cli_channels_battery",
    "tests.test_cli",
    "tests.test_submission_battery",
)
# The parenthesised group is already the FULL dotted path, test name included; pairing it with
# the leading bare name would render every witness twice.
WITNESS = re.compile(r"^(?:FAIL|ERROR): \w+ \(([\w.]+)\)", re.M)


def _purge_pycache(root: pathlib.Path) -> None:
    for cache in root.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def _run(tree: pathlib.Path, modules: list[str]) -> tuple[bool, str]:
    _purge_pycache(tree)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    argv = ["uv", "run", "--quiet", "python", "-m", "unittest", "-v", *modules]
    proc = subprocess.run(
        argv, cwd=tree, capture_output=True, text=True, env=env, check=False
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def _witnesses(output: str) -> list[str]:
    return sorted(set(WITNESS.findall(output)))


def _load() -> list[dict[str, str]]:
    document = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    rows = document["rows"]
    seen: set[str] = set()
    for row in rows:
        if row["id"] in seen:
            raise SystemExit(f"ABORT   duplicate mutant id {row['id']}")
        seen.add(row["id"])
    return rows


def preflight(tree: pathlib.Path, rows: list[dict[str, str]]) -> list[str]:
    """Report EVERY unusable row at once; a first-failure abort hides later verdicts."""
    problems: list[str] = []
    for row in rows:
        target = tree / row["path"]
        if not target.is_file():
            problems.append(f"{row['id']}   NO-FILE      {row['path']}")
            continue
        text = target.read_text(encoding="utf-8")
        count = text.count(row["anchor"])
        if count != 1:
            problems.append(
                f"{row['id']}   ANCHOR-{'MISS' if count == 0 else 'AMBIGUOUS'}  "
                f"{row['path']} count={count}"
            )
            continue
        if row["anchor"] == row["replacement"]:
            problems.append(f"{row['id']}   IDENTITY     replacement equals anchor")
    return problems


def apply_one(
    tree: pathlib.Path, row: dict[str, str], modules: list[str]
) -> dict[str, object]:
    target = tree / row["path"]
    before = target.read_text(encoding="utf-8")
    after = before.replace(row["anchor"], row["replacement"], 1)
    if after == before:
        return {**_summary(row, modules), "verdict": "patch-noop", "witnesses": []}
    target.write_text(after, encoding="utf-8")
    try:
        green, output = _run(tree, modules)
        witnesses = _witnesses(output)
        wanted = row["target_test"]
        if green:
            verdict = "survived"
        elif any(witness.endswith(f".{wanted}") for witness in witnesses):
            verdict = "killed"
        else:
            verdict = "misdirected"
    finally:
        target.write_text(before, encoding="utf-8")
        if target.read_text(encoding="utf-8") != before:
            raise SystemExit(f"ABORT   {row['id']} left {row['path']} unrestored")
    return {**_summary(row, modules), "verdict": verdict, "witnesses": witnesses}


def _summary(row: dict[str, str], modules: list[str]) -> dict[str, object]:
    return {
        "id": row["id"],
        "obligation": row["obligation"],
        "kind": row.get("kind", ""),
        "target_test": row["target_test"],
        "expect": row.get("expect", "killed"),
        "verdict_modules": list(modules),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", default=[])
    parser.add_argument("--kind", action="append", default=[])
    parser.add_argument("--verdict", action="append", default=[])
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv[1:])

    modules = args.verdict or list(DEFAULT_VERDICT)
    rows = _load()
    declared = sorted(row["id"] for row in rows if row.get("expect") == "equivalent")
    if args.id:
        rows = [row for row in rows if row["id"] in set(args.id)]
    if args.kind:
        rows = [row for row in rows if row.get("kind") in set(args.kind)]
    if not rows:
        raise SystemExit("ABORT   selection matched no mutant")

    with tempfile.TemporaryDirectory(prefix="m3u5b-sweep-") as room:
        tree = pathlib.Path(room) / "tree"
        subprocess.run(
            ["git", "-C", str(ROOT), "worktree", "add", "--detach", str(tree), "HEAD"],
            check=True,
            capture_output=True,
        )
        try:
            stale = preflight(tree, rows)
            for line in stale:
                print(line)
            if stale:
                print(f"ABORT   {len(stale)} unusable rows; re-anchor before quoting a verdict")
                return 1

            control_green, control_output = _run(tree, modules)
            print(f"VERDICT-MODULES: {' '.join(modules)}")
            print(f"CONTROL: {'GREEN' if control_green else 'RED'}")
            if not control_green:
                print(f"  {' '.join(_witnesses(control_output)) or 'no witness parsed'}")
                print("ABORT   the unmutated control is red; every verdict would be a false kill")
                return 1

            results = [apply_one(tree, row, modules) for row in rows]
        finally:
            subprocess.run(
                ["git", "-C", str(ROOT), "worktree", "remove", "--force", str(tree)],
                check=False,
                capture_output=True,
            )

    print(f"MUTANTS: {len(results)}")
    for result in results:
        marks = ",".join(str(w) for w in result["witnesses"][:2]) or "-"
        print(
            f"{result['id']:<5} {str(result['verdict']):<12} {str(result['obligation']):<6} "
            f"{str(result['kind']):<12} {marks}"
        )

    killed = [r for r in results if r["verdict"] == "killed"]
    misdirected = sorted(str(r["id"]) for r in results if r["verdict"] == "misdirected")
    survived = sorted(str(r["id"]) for r in results if r["verdict"] == "survived")
    noop = sorted(str(r["id"]) for r in results if r["verdict"] == "patch-noop")
    unexpected = sorted(set(survived) - set(declared))

    print(f"KILLED: {len(killed)}")
    print(f"MISDIRECTED: {len(misdirected)} {misdirected}")
    print(f"SURVIVORS: {len(survived)} {survived}")
    print(f"NAMED-SURVIVOR-SET: {len(declared)} {declared}")
    print(f"PATCH-NOOP: {len(noop)} {noop}")
    print(f"UNEXPECTED-SURVIVORS: {len(unexpected)} {unexpected}")
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
    failed = bool(unexpected or misdirected or noop)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
