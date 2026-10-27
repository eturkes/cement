#!/usr/bin/env python3
"""p10-scratch-census — every `.scratch/` path a tracked file cites, and whether it reads as retrievable.

`.scratch/` is gitignored: a path under it resolves on the machine that wrote it and nowhere else.
A tracked file may name one only (a) as a working-directory convention or output location
(`OPERATIONAL`, each entry with its reason), (b) inside a queue row or history, or (c) in a record
carrying the MARKER sentence, which states that its `.scratch/` paths are machine-local inputs no
clone can retrieve. JSON records cannot carry prose, so `MARKED_JSON` marks them here.

Usage: uv run python .agent/decisions/p10-scratch-census.py
rc 0 = every citation is operational, history or marked; 1 = an unmarked citation (each printed).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SELF = ".agent/decisions/p10-scratch-census.py"
MARKER = "Machine-local: each `.scratch/` path in this file"
OPERATIONAL = {
    "CLAUDE.md": "template: the teammate worktree location convention",
    ".claude/agents/janitor.md": "template: the repo's own ignore entries the janitor checks",
    ".claude/rules/ops.md": "worktree location + the gitignore rule itself",
    ".claude/rules/prototype.md": "where a scratch capture driver goes",
    "prototype/webui-demo/capture.sh": "capture output directory (gitignored by design)",
    "prototype/webui-demo/README.md": "capture output directory (gitignored by design)",
    ".agent/spec.md": "the queue run's RESUME row names its helpers; the row leaves at the run's close",
    "tests/test_cli_removal_battery.py": "D25 pins the p12 row's own text",
    ".claude/rules/gate-checks.md": "the census's firing record names its seed citation",
    ".agent/seeds": "the census's seed group (S27) plants a citation",
}
HISTORY = (".agent/archive/", ".agent/deferred.md", ".gitignore")
MARKED_JSON = {
    ".agent/decisions/m3u3-review.json": "reviewer evidence paths of M3.3's closing review",
    ".agent/decisions/m3u2b-review.json": "reviewer evidence paths of M3.2b's closing review",
    ".agent/decisions/m3u2b-smoke-crosswalk.json": "the M3.2b smoke script's machine-local path",
}


def main() -> int:
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "grep", "-n", "-F", ".scratch/"], capture_output=True, text=True
    ).stdout.splitlines()
    unmarked, counts = [], {"operational": 0, "history": 0, "marked": 0, "json": 0}
    for hit in listing:
        path, line, text = hit.split(":", 2)
        if path == SELF:
            continue
        if path in OPERATIONAL:
            counts["operational"] += 1
        elif path.startswith(HISTORY):
            counts["history"] += 1
        elif path in MARKED_JSON:
            counts["json"] += 1
        elif MARKER in (ROOT / path).read_text(encoding="utf-8"):
            counts["marked"] += 1
        else:
            unmarked.append(f"UNMARKED {path}:{line}: {text.strip()[:120]}")
    for row in unmarked:
        print(row)
    print(f"CITATIONS: {len(listing) - sum(1 for h in listing if h.startswith(SELF + ':'))} {counts} unmarked {len(unmarked)}")
    return 1 if unmarked else 0


if __name__ == "__main__":
    sys.exit(main())
