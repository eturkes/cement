#!/usr/bin/env python3
"""p73-review-coverage — every commit since `a8109eb` has a review record, or is listed with its reason.

A commit's record (the `.agent/review.md` preamble's scope) = a section that commit adds to the
ledger (`+## ` in its own diff), a section anywhere in the ledger naming its 7-char SHA (a unit
reviewed in a later commit), or its own body's `Teammates:` / `dispatch:` line (closes the ledger
does not cover: ITERATE rounds, template refreshes, plan + record commits). NO_RECORD lists the
commits that carry none of the three, each with its reason.

Usage: uv run python .agent/decisions/p73-review-coverage.py
rc 0 = prints nothing; 1 = each commit lacking a record (or a stale NO_RECORD entry) printed.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "a8109eb"
NO_RECORD = {
    "4e5b9aa": "template re-sync of CLAUDE.md (a copy of the shared template; nothing of this repo to review)",
    "a76c428": "template re-sync of CLAUDE.md (a copy of the shared template; nothing of this repo to review)",
    "4aa6b21": "template re-sync of CLAUDE.md (a copy of the shared template; nothing of this repo to review)",
    "0934027": "M4.1 follow-up pins inside the unit whose section reviews the squash `535a0a9`",
    "9058066": "prototype README/label fix under PROTOTYPE law (outside every gate)",
    "a97bbc3": "prototype README count fix under PROTOTYPE law (outside every gate)",
}


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    ledger = (ROOT / ".agent/review.md").read_text(encoding="utf-8")
    commits = _git("rev-list", "--reverse", f"{BASE}..HEAD").split()
    short = {_git("rev-parse", "--short=7", c).strip(): c for c in commits}
    missing = []
    for sha7, full in short.items():
        if re.search(r"(?m)^\+## ", _git("show", "--format=", "-U0", full, "--", ".agent/review.md")):
            continue
        if re.search(rf"\b{sha7}", ledger):
            continue
        if re.search(r"(?m)^(Teammates|dispatch):", _git("log", "-1", "--format=%B", full)):
            continue
        if sha7 in NO_RECORD:
            continue
        missing.append(f"NO-RECORD {sha7} {_git('log', '-1', '--format=%s', full).strip()[:100]}")
    missing += [f"STALE-ENTRY {sha7} not in {BASE}..HEAD" for sha7 in NO_RECORD if sha7 not in short]
    for line in missing:
        print(line)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
