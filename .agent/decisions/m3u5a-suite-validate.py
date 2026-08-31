#!/usr/bin/env python3
"""Grade the M3.5a phase-2 red suite against MAIN's ruled verdict table.

    uv run python .agent/decisions/m3u5a-suite-validate.py [SUITE]
    uv run python .agent/decisions/m3u5a-suite-validate.py --emit-stub > tests/test_cli_channels.py

`--emit-stub` is the seed's SINGLE SOURCE OF TRUTH: it derives one test per ruled row from
`m3u5a-verdicts.json`, so the seed cannot drift from the table it encodes.

Control line reports, and every one must be zero for `PASS`:

    UNFILLED-TESTS      bodies still carrying the `UNFILLED` marker
    ROWS-UNCOVERED      ruled rows with no test named for them
    ORPHAN-TESTS        tests naming no ruled row
    ASSERTIONLESS       filled bodies that assert nothing

`ASSERTIONLESS` exists because deleting the `self.fail` marker is the cheapest way to
turn a red test green, and a body with no assertion passes silently forever.

The suite must be RED at the worktree base and GREEN against the shipped implementation.
This validator grades SHAPE only; redness is the suite runner's job.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
TABLE = HERE / "m3u5a-verdicts.json"
DEFAULT_SUITE = HERE.parents[1] / "tests" / "test_cli_channels.py"
MARKER = "UNFILLED"

ASSERTING = re.compile(r"\bself\.(assert|fail)\w*\(")


def _rows() -> list[dict[str, str]]:
    payload = json.loads(TABLE.read_text(encoding="utf-8"))
    rows = payload["rows"]
    unruled = [row["id"] for row in rows if not row.get("main_verdict")]
    if unruled:
        raise SystemExit(f"ABORT   table holds unruled rows: {unruled}")
    return rows


def _slug(text: str, limit: int = 58) -> str:
    words = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return words[:limit].rstrip("_") or "row"


def _name(row: dict[str, str]) -> str:
    return f"test_{row['id'].lower()}_{_slug(row['locus'])}"


def _wrap(text: str, indent: str, width: int = 96) -> list[str]:
    out: list[str] = []
    line = indent
    for word in text.split():
        if len(line) + len(word) + 1 > width and line.strip():
            out.append(line.rstrip())
            line = indent
        line += word + " "
    if line.strip():
        out.append(line.rstrip())
    return out


def emit_stub() -> str:
    rows = _rows()
    body = [
        '"""M3.5a phase-2 red suite: one test per ruled verdict row.',
        "",
        "Seeded by `.agent/decisions/m3u5a-suite-validate.py --emit-stub` from the ruled",
        "`m3u5a-verdicts.json`. Each docstring carries the row's ruled observable and its",
        "battery action verbatim; the body is the work.",
        "",
        "ENCODE        pin the ruled observable as written.",
        "ENCODE-SCOPED pin the NARROWED form named in the verdict. The literal row goes red",
        "              against correct code, so encoding it as written is a defect.",
        "",
        "Replace each `self.fail` marker with real assertions. A body that asserts nothing",
        "is graded ASSERTIONLESS and fails the validator.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import unittest",
        "",
        "",
        "class CliChannelTests(unittest.TestCase):",
        '    """Ruled M3.5a CLI-channel obligations, one test per verdict row."""',
    ]
    for row in rows:
        summary = f"{row['id']} [{row['section']}] {row['locus']}"
        body += ["", f"    def {_name(row)}(self) -> None:"]
        body.append(f'        """{summary}')
        body.append("")
        body.append(f"        ACTION: {row['action']}")
        body += ["", "        EXPECTED:"]
        body += _wrap(row["expected"], "        ")
        body += ["", "        RULING:"]
        body += _wrap(row["main_verdict"], "        ")
        body.append('        """')
        body.append(f'        self.fail("{MARKER} {row["id"]}")')
    body += ["", "", 'if __name__ == "__main__":', "    unittest.main()", ""]
    return "\n".join(body)


def grade(path: pathlib.Path) -> int:
    rows = _rows()
    wanted = {row["id"]: _name(row) for row in rows}
    tree = ast.parse(path.read_text(encoding="utf-8"))

    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            found[node.name] = node

    by_name = {name: rid for rid, name in wanted.items()}
    unfilled: list[str] = []
    assertionless: list[str] = []
    for name, node in found.items():
        source = ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
        if MARKER in source:
            unfilled.append(by_name.get(name, name))
            continue
        if not ASSERTING.search(source):
            assertionless.append(by_name.get(name, name))

    uncovered = sorted(rid for rid, name in wanted.items() if name not in found)
    orphans = sorted(name for name in found if name not in by_name)

    print(f"SUITE: {path}")
    print(f"ROWS: {len(rows)}")
    print(f"TESTS: {len(found)}")
    print(f"UNFILLED-TESTS: {len(unfilled)} {sorted(unfilled)}")
    print(f"ROWS-UNCOVERED: {len(uncovered)} {uncovered}")
    print(f"ORPHAN-TESTS: {len(orphans)} {orphans}")
    print(f"ASSERTIONLESS: {len(assertionless)} {sorted(assertionless)}")
    failed = bool(unfilled or uncovered or orphans or assertionless)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-stub", action="store_true")
    parser.add_argument("suite", nargs="?", default=str(DEFAULT_SUITE))
    args = parser.parse_args(argv[1:])
    if args.emit_stub:
        sys.stdout.write(emit_stub())
        return 0
    return grade(pathlib.Path(args.suite))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
