#!/usr/bin/env python3
"""p56-strength — weaken each strength-bearing assertion in `p56-strength.json`, record what kills it.

One detached worktree of `--rev` (a temp dir; never the working tree). A pristine CONTROL run goes
first and must print `OK`; then per row: apply the weakening (`old` → `new`, the `occurrence`-th
hit inside `function`'s AST span), purge `__pycache__` (`PYTHONDONTWRITEBYTECODE=1`), run the
selected tests, collect the failing ids, restore and prove `git diff --quiet`.

Two halves (`.agent/decisions/p56-strength-{survive,die}.txt`):
  survive  --rev <a revision without the oracle>   selected = `.agent/suite --omit-d28`, the full
           suite minus D28 (insensitive by construction: its subject is committed history, which no
           working-tree weakening moves); a row the old suite already kills is recorded as such
  die      --rev <the oracle's revision> --oracle  selected = the oracle module; rc 1 unless every
           row's NAMED oracle id is among its failures (any other killer is a different fact)

Usage: uv run python .agent/decisions/p56-strength.py --rev REV [--oracle] [--only ID …]
rc 0 = control green, every row applied + restored (+ with --oracle: each named oracle killed it);
1 = a named oracle missed its row; 2 = setup, red control, anchor miss or failed restore.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOGUE = json.loads((ROOT / ".agent/decisions/p56-strength.json").read_text(encoding="utf-8"))
FAILED = re.compile(r"^(?:FAIL|ERROR): \S+ \(([\w.]+)\)", re.MULTILINE)
RAN = re.compile(r"^Ran (\d+) tests? in", re.MULTILINE)


def _git(*args: str, cwd: pathlib.Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _weaken(checkout: pathlib.Path, row: dict) -> None:
    path = checkout / row["file"]
    text = path.read_text(encoding="utf-8")
    nodes = [n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == row["function"]]
    if len(nodes) != 1:
        raise SystemExit(f"ABORT   {row['id']}: {len(nodes)} definitions of {row['function']}")
    lines = text.splitlines(keepends=True)
    start, end = nodes[0].lineno - 1, nodes[0].end_lineno or 0
    span = "".join(lines[start:end])
    hits = [m.start() for m in re.finditer(re.escape(row["old"]), span)]
    if len(hits) <= row["occurrence"]:
        raise SystemExit(f"ABORT   {row['id']}: anchor miss ({len(hits)} hits of `old` in {row['function']})")
    at = hits[row["occurrence"]]
    mutated = "".join(lines[:start]) + span[:at] + row["new"] + span[at + len(row["old"]) :] + "".join(lines[end:])
    if mutated == text:
        raise SystemExit(f"ABORT   {row['id']}: identity patch")
    path.write_text(mutated, encoding="utf-8")


def _run(checkout: pathlib.Path, argv: list[str]) -> tuple[str, list[str], int | None]:
    for cache in checkout.rglob("__pycache__"):
        shutil.rmtree(cache)
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(argv, cwd=checkout, env=environment, capture_output=True, text=True, timeout=3600)
    output = result.stdout + result.stderr
    ran = RAN.search(output)
    verdict = "OK" if result.returncode == 0 and re.search(r"^OK\b", output, re.MULTILINE) else "FAILED"
    return verdict, sorted(set(FAILED.findall(output))), int(ran.group(1)) if ran else None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rev", required=True)
    parser.add_argument("--oracle", action="store_true")
    parser.add_argument("--only", nargs="*", default=[])
    args = parser.parse_args(argv[1:])
    rows = [row for row in CATALOGUE["rows"] if not args.only or row["id"] in args.only]
    selected = (
        ["uv", "run", "python", "-m", "unittest", CATALOGUE["oracle_module"]]
        if args.oracle
        else ["uv", "run", "python", ".agent/suite", "--omit-d28"]
    )
    revision = _git("rev-parse", "--verify", f"{args.rev}^{{commit}}").strip()
    print(f"REV: {revision}")
    print(f"SELECTED: {' '.join(selected)}")
    if not args.oracle:
        print("EXCLUDED: D28 (insensitive by construction: committed history, untouched by a working-tree weakening)")
    status = 0
    with tempfile.TemporaryDirectory() as parent:
        checkout = pathlib.Path(parent) / "p56"
        _git("worktree", "add", "-q", "--detach", str(checkout), revision)
        try:
            verdict, failing, ran = _run(checkout, selected)
            print(f"CONTROL: {verdict} ran={ran}")
            if verdict != "OK":
                print("ABORT   red control: " + " ".join(failing))
                return 2
            for row in rows:
                _weaken(checkout, row)
                verdict, failing, ran = _run(checkout, selected)
                _git("checkout", "-q", "--", row["file"], cwd=checkout)
                if subprocess.run(["git", "diff", "--quiet"], cwd=checkout).returncode != 0:
                    print(f"ABORT   {row['id']}: restore left a diff")
                    return 2
                named = row["oracle"] in failing
                outcome = "survived" if verdict == "OK" else "killed"
                print(f"{row['id']}  {outcome:<8}  ran={ran}  named-oracle={'yes' if named else 'no'}  {row['file']}:{row['function']}")
                for test_id in failing:
                    print(f"      killer {test_id}")
                if args.oracle and not named:
                    status = 1
        finally:
            _git("worktree", "remove", "--force", str(checkout))
    print(f"RESULT: {'PASS' if status == 0 else 'FAIL'}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
