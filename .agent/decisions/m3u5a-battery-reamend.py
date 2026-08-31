#!/usr/bin/env python
"""Re-inject the CURRENT contract's docstrings into the obligation battery, keeping every body.

    uv run python .agent/decisions/m3u5a-battery-reamend.py [BATTERY] [--check]

The battery is authored DIFF-BLIND against the contract as it stood at dispatch. MAIN then rules
the attack table, which supersedes obligations the author already encoded — M3.5a's S4 grew the
amendment set from A1-A8 to A1-A23 and the amended-obligation count from 9 to 18 while the author
was mid-file. A validator seeded before its contract grew EXPIRES, and `AMENDMENT-UNCITED` then
fails a docstring that was correct when it was written.

This script closes the mechanical half of that reconciliation and NOTHING more. It rewrites each
test's DOCSTRING from `m3u5a-battery-validate.py`'s own emitter — the seed's single source of
truth — and leaves the body byte-identical. A body that now contradicts its superseding amendment
still fails against correct code; that red is the specification question MAIN answers by hand, and
this script must never be mistaken for answering it.

Idempotent: a second run reports `NO-OP`. `--check` is the in-sync gate.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_BATTERY = HERE.parents[1] / "tests" / "test_cli_channels_battery.py"


def _validator():
    spec = importlib.util.spec_from_file_location("v", HERE / "m3u5a-battery-validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _docstring(validator, row: dict[str, str], binding) -> list[str]:
    """Rebuild one docstring exactly as `--emit-stub` would write it today."""

    body = [f'        """{row["id"]} obligation', "", "        CONTRACT:"]
    body += validator._wrap(row["text"], "        ")
    for aid, text in binding.get(row["id"], ()):
        body += ["", f"        AMENDED-BY {aid}, superseding the text above:"]
        body += validator._wrap(text, "        ")
    body.append('        """')
    return body


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("battery", nargs="?", default=str(DEFAULT_BATTERY))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv[1:])

    validator = _validator()
    rows = validator._obligations()
    binding = validator._amendments()
    wanted = {validator._name(row): row for row in rows}

    path = pathlib.Path(args.battery)
    lines = path.read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(lines))

    # Collect edits first, then apply BOTTOM-UP so earlier line numbers stay valid.
    edits: list[tuple[int, int, list[str]]] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in wanted:
            continue
        seen.add(node.name)
        first = node.body[0]
        if not (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            print(f"ABORT   {node.name} has no docstring to replace")
            return 1
        assert first.end_lineno is not None
        edits.append((first.lineno - 1, first.end_lineno, _docstring(validator, wanted[node.name], binding)))

    missing = sorted(name for name in wanted if name not in seen)
    if missing:
        print(f"MISSING-TESTS: {len(missing)} {missing}")
        return 1

    updated = list(lines)
    changed = 0
    for start, end, replacement in sorted(edits, reverse=True):
        if updated[start:end] != replacement:
            changed += 1
        updated[start:end] = replacement

    amended = sorted(oid for oid in binding if oid in {row["id"] for row in rows})
    print(f"TESTS: {len(edits)}")
    print(f"AMENDED-OBLIGATIONS: {len(amended)} {amended}")
    print(f"DOCSTRINGS-STALE: {changed}")
    if args.check:
        print("PASS" if changed == 0 else "FAIL")
        return 0 if changed == 0 else 1
    if changed:
        path.write_text("\n".join(updated) + "\n", encoding="utf-8")
        print("WROTE")
    else:
        print("NO-OP")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
