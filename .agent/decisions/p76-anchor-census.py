#!/usr/bin/env python3
"""p76-anchor-census — every closed-unit mutant row's anchor count in the working tree.

Rows = each object carrying `anchor` + `path`|`file` in `.agent/decisions/*.json` (the M3.5a, M3.5b
and M3.6a1 catalogues). Later units rewrite those loci, so a HEAD run of the unit's harness cannot
apply a count-0 row. Each count-0 row must carry a RETIRED mark in `p76-retired.json` (the catalogues'
own schemas stay untouched): the commit that removed its anchor, verified both ways — the anchor
occurs in `<commit>^:<path>` and not in `<commit>:<path>` (or the path is gone there). A mark on a row
whose anchor is present again is stale and fails too.

Usage: uv run python .agent/decisions/p76-anchor-census.py [--emit] [--quiet]
  prints `<catalogue> <id> <count>` per row (`--quiet`: failures + totals only)
  --emit  derive the removal commit (`git log -S`) for every unmarked count-0 row and write the
          ledger (idempotent: existing marks are kept and re-verified)
rc 0 = every count-0 row carries a verified mark and no mark is stale; 1 otherwise (each printed).
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from collections.abc import Iterator

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".agent/decisions/p76-retired.json"


def _rows(value: object) -> Iterator[dict]:
    if isinstance(value, dict):
        if "anchor" in value and ("path" in value or "file" in value):
            yield value
        for child in value.values():
            yield from _rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from _rows(child)


def _blob(revision: str, path: str) -> str | None:
    shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{revision}:{path}"], capture_output=True, text=True)
    return shown.stdout if shown.returncode == 0 else None


def _verified(commit: str, path: str, anchor: str) -> bool:
    before, after = _blob(f"{commit}^", path), _blob(commit, path)
    return before is not None and anchor in before and (after is None or anchor not in after)


def _removal(path: str, anchor: str) -> str | None:
    for flag in (["-S", anchor], ["--diff-filter=D"]):
        found = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--format=%H", *flag, "--", path], capture_output=True, text=True
        ).stdout.split()
        for commit in found:
            if _verified(commit, path, anchor):
                return commit
    return None


def main(argv: list[str]) -> int:
    ledger: dict[str, dict] = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    failures, total, zero = [], 0, 0
    seen = set()
    for catalogue in sorted((ROOT / ".agent/decisions").glob("*.json")):
        if catalogue == LEDGER:
            continue
        for row in _rows(json.loads(catalogue.read_text(encoding="utf-8"))):
            total += 1
            key = f"{catalogue.name}:{row['id']}"
            seen.add(key)
            path = str(row.get("path") or row.get("file"))
            target = ROOT / path
            count = target.read_text(encoding="utf-8").count(row["anchor"]) if target.is_file() else 0
            if "--quiet" not in argv:
                print(f"{catalogue.name} {row['id']} {count}")
            mark = ledger.get(key)
            if count == 0:
                zero += 1
                if mark is None and "--emit" in argv:
                    commit = _removal(path, row["anchor"])
                    if commit is not None:
                        mark = ledger[key] = {"retired": commit, "path": path}
                if mark is None:
                    failures.append(f"UNMARKED {key} count 0 ({path})")
                elif not _verified(mark["retired"], path, row["anchor"]):
                    failures.append(f"UNVERIFIED {key} retired={mark['retired']} does not remove its anchor")
            elif mark is not None:
                failures.append(f"STALE {key} count {count} but marked retired={mark['retired']}")
    failures += [f"ORPHAN {key} names no catalogue row" for key in sorted(set(ledger) - seen)]
    if "--emit" in argv:
        LEDGER.write_text(json.dumps(dict(sorted(ledger.items())), indent=2) + "\n", encoding="utf-8")
    for line in failures:
        print(line)
    print(f"ROWS: {total} count-0 {zero} marked {len(ledger)} failures {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
