#!/usr/bin/env python
"""Check that a battery module covers every acceptance-contract obligation.

    uv run python .agent/decisions/m3u2a-battery-validate.py tests/test_read_capability_battery.py

Each test method's docstring must OPEN with its obligation id, `Bnn: `. Coverage is the whole
grade: a module is valid when every id in B1..B22 appears at least once, every test name is
unique, and no docstring claims an id outside the contract. Exit 0 when valid, 1 otherwise.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys

OBLIGATIONS = [f"B{index}" for index in range(1, 23)]
CLAIM = re.compile(r"^(B\d+)\s*:")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", nargs="+", type=Path)
    arguments = parser.parse_args(argv)

    covered: dict[str, list[str]] = {}
    names: list[str] = []
    problems: list[str] = []
    for path in arguments.module:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
                continue
            names.append(node.name)
            documentation = ast.get_docstring(node) or ""
            match = CLAIM.match(documentation.strip())
            if match is None:
                problems.append(f"{path}:{node.lineno} {node.name} has no leading 'Bnn:' claim")
                continue
            covered.setdefault(match.group(1), []).append(node.name)

    duplicates = sorted({name for name in names if names.count(name) > 1})
    unknown = sorted(set(covered) - set(OBLIGATIONS), key=lambda item: int(item[1:]))
    missing = [item for item in OBLIGATIONS if item not in covered]

    print(f"tests={len(names)} obligations_covered={len(covered)}/{len(OBLIGATIONS)}")
    for item in OBLIGATIONS:
        print(f"  {item}: {' '.join(covered.get(item, ['unknown']))}")
    if duplicates:
        problems.append(f"duplicate test names: {duplicates}")
    if unknown:
        problems.append(f"obligation ids outside the contract: {unknown}")
    if missing:
        problems.append(f"UNCOVERED: {missing}")
    for problem in problems:
        print(f"PROBLEM {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
