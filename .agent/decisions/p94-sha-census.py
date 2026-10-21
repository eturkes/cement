#!/usr/bin/env python3
"""p94-sha-census — every commit an `.agent/decisions/*.py` instrument names, and whether a clone has it.

A revision = a 7-40 lowercase-hex token inside any string constant (docstrings and `<rev>:<path>`
specs included) that resolves to a commit in this clone. It must be an ancestor of `main`, which
every clone of `main` carries; otherwise the instrument's docstring records the dependency: a line
`Tag dependency: <sha> …` naming the ref that keeps it and the restore command. Limit: hex that
resolves to no commit here reads as data (digests, digest prefixes), so run this census in the
authoring clone, which holds every local tag.

Usage: uv run python .agent/decisions/p94-sha-census.py
rc 0 = every named revision is on `main` or recorded; 1 = an unreachable, unrecorded one (printed).
"""

from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REVISION = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def main() -> int:
    failures, counts = [], {"on-main": 0, "recorded": 0, "unreachable": 0}
    for path in sorted((ROOT / ".agent/decisions").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(tree) or ""
        named = sorted({
            token
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            for token in REVISION.findall(node.value)
        })
        for literal in named:
            resolved = _git("rev-parse", "--verify", "--quiet", f"{literal}^{{commit}}")
            if resolved.returncode != 0:
                continue  # resolves to no commit here: data (a digest or its prefix), see Limit
            if _git("merge-base", "--is-ancestor", resolved.stdout.strip(), "main").returncode == 0:
                counts["on-main"] += 1
            elif re.search(rf"(?m)^Tag dependency: {literal}\b.*\S", docstring):
                counts["recorded"] += 1
            else:
                counts["unreachable"] += 1
                failures.append(f"UNREACHABLE {path.relative_to(ROOT)}: {literal} (not on main, no `Tag dependency:` line)")
    for line in failures:
        print(line)
    print(f"REVISIONS: {counts}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
