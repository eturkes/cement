#!/usr/bin/env python3
"""Grade the M3.5a obligation battery against the contract's own D01-D30 bullets.

    uv run python .agent/decisions/m3u5a-battery-validate.py [BATTERY]
    uv run python .agent/decisions/m3u5a-battery-validate.py --emit-stub \
        > tests/test_cli_channels_battery.py

`--emit-stub` is the seed's SINGLE SOURCE OF TRUTH. It parses `m3u5a-contract.md` for every
`- **DNN**` bullet and every `- **A<k> (D..)**` amendment, so the seed cannot drift from the
contract it encodes. Sections 5-10 hold the obligations; sections 13-14 hold the amendments.

Control line reports, and every one must be zero for `PASS`:

    UNFILLED-TESTS          bodies still carrying the `UNFILLED` marker
    OBLIGATIONS-UNCOVERED   D-obligations with no test named for them
    ORPHAN-TESTS            tests naming no D-obligation
    ASSERTIONLESS           filled bodies that assert nothing
    SKIPPED                 bodies that skip, by call or by decorator
    AMENDMENT-UNCITED       amended obligations whose docstring dropped its amendment

`ASSERTIONLESS` and `SKIPPED` are the two cheapest ways to satisfy a coverage count while
asserting nothing: deleting the `self.fail` marker, and skipping the body outright.

`AMENDMENT-UNCITED` guards the failure this unit already paid for twice. Eight amendments
supersede the cited bullet text, so a body that encodes the LITERAL bullet for an amended
obligation goes red against correct code. The amendment must stay in front of the author.

The battery must be RED at the pre-implementation base and GREEN against the shipped
implementation. This validator grades SHAPE only; redness is the runner's job.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CONTRACT = HERE / "m3u5a-contract.md"
DEFAULT_BATTERY = HERE.parents[1] / "tests" / "test_cli_channels_battery.py"
MARKER = "UNFILLED"

ASSERTING = re.compile(r"\bself\.(assert|fail)\w*\(")
SKIPPING = re.compile(r"\bself\.skipTest\(|@unittest\.skip|@skip(?:If|Unless)?\b")

OBLIGATION = re.compile(r"^- \*\*(D\d{2})\*\* (.*)$")
AMENDMENT = re.compile(r"^- \*\*(A\d)\ \(([^)]+)\)\*\* (.*)$")
BULLET = re.compile(r"^- \*\*[DA]")


def _bullets(pattern: re.Pattern[str]) -> list[tuple[str, str, str]]:
    """Collect `- **ID** text` bullets, folding their indented continuation lines."""
    found: list[tuple[str, str, str]] = []
    current: list[str] | None = None
    for line in CONTRACT.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            groups = match.groups()
            current = [groups[0], groups[1] if len(groups) > 2 else "", groups[-1]]
            found.append((current[0], current[1], current[2]))
            continue
        if current is None:
            continue
        if line.startswith("  ") and line.strip():
            merged = (found[-1][0], found[-1][1], f"{found[-1][2]} {line.strip()}")
            found[-1] = merged
            continue
        current = None
    return found


def _obligations() -> list[dict[str, str]]:
    rows = [
        {"id": oid, "text": text}
        for oid, _, text in _bullets(OBLIGATION)
    ]
    ids = [row["id"] for row in rows]
    wanted = [f"D{index:02d}" for index in range(1, 31)]
    if ids != wanted:
        raise SystemExit(f"ABORT   contract holds {ids}, expected D01-D30 in order")
    return rows


def _amendments() -> dict[str, list[tuple[str, str]]]:
    """Map each amended obligation id to the amendments that bind it."""
    binding: dict[str, list[tuple[str, str]]] = {}
    for aid, targets, text in _bullets(AMENDMENT):
        for target in (part.strip() for part in targets.split(",")):
            binding.setdefault(target, []).append((aid, text))
    if not binding:
        raise SystemExit("ABORT   contract holds no amendments; A1-A8 are binding")
    return binding


def _slug(text: str, limit: int = 58) -> str:
    words = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return words[:limit].rstrip("_") or "obligation"


def _name(row: dict[str, str]) -> str:
    return f"test_{row['id'].lower()}_{_slug(row['text'])}"


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
    rows = _obligations()
    binding = _amendments()
    body = [
        '"""M3.5a obligation battery: one test per contract obligation D01-D30.',
        "",
        "Seeded by `.agent/decisions/m3u5a-battery-validate.py --emit-stub` from the",
        "obligation bullets in `m3u5a-contract.md`. Each docstring carries its obligation",
        "verbatim, followed by every amendment that binds it; the body is the work.",
        "",
        "An AMENDED obligation is encoded in its AMENDED form. The amendment supersedes the",
        "bullet text above it, so encoding the literal bullet is a defect that goes red",
        "against correct code.",
        "",
        "Replace each `self.fail` marker with real assertions. A body that asserts nothing is",
        "graded ASSERTIONLESS, and a body that skips is graded SKIPPED. Both fail the",
        "validator.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import unittest",
        "",
        "",
        "class ObligationBatteryTests(unittest.TestCase):",
        '    """One test per M3.5a contract obligation, encoded in its amended form."""',
    ]
    for row in rows:
        body += ["", f"    def {_name(row)}(self) -> None:"]
        body.append(f'        """{row["id"]} obligation')
        body += ["", "        CONTRACT:"]
        body += _wrap(row["text"], "        ")
        for aid, text in binding.get(row["id"], ()):
            body += ["", f"        AMENDED-BY {aid}, superseding the text above:"]
            body += _wrap(text, "        ")
        body.append('        """')
        body.append(f'        self.fail("{MARKER} {row["id"]}")')
    body += ["", "", 'if __name__ == "__main__":', "    unittest.main()", ""]
    return "\n".join(body)


def grade(path: pathlib.Path) -> int:
    if not path.is_file():
        raise SystemExit(f"ABORT   no battery at {path}; seed it with --emit-stub")
    rows = _obligations()
    binding = _amendments()
    wanted = {row["id"]: _name(row) for row in rows}
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            found[node.name] = node

    by_name = {name: oid for oid, name in wanted.items()}
    unfilled: list[str] = []
    assertionless: list[str] = []
    skipped: list[str] = []
    uncited: list[str] = []
    for name, node in found.items():
        oid = by_name.get(name, name)
        # `get_source_segment` starts at `def`, so decorators live outside it and a
        # `@unittest.skip` would otherwise read as an ordinary filled body.
        decorators = "\n".join(
            f"@{ast.unparse(item)}" for item in node.decorator_list
        )
        segment = f"{decorators}\n{ast.get_source_segment(source, node) or ''}"
        docstring = ast.get_docstring(node) or ""
        for aid, _ in binding.get(oid, ()):
            if f"AMENDED-BY {aid}" not in docstring:
                uncited.append(f"{oid}/{aid}")
        if SKIPPING.search(segment):
            skipped.append(oid)
            continue
        if MARKER in segment:
            unfilled.append(oid)
            continue
        if not ASSERTING.search(segment):
            assertionless.append(oid)

    uncovered = sorted(oid for oid, name in wanted.items() if name not in found)
    orphans = sorted(name for name in found if name not in by_name)

    print(f"BATTERY: {path}")
    print(f"OBLIGATIONS: {len(rows)}")
    print(f"TESTS: {len(found)}")
    print(f"UNFILLED-TESTS: {len(unfilled)} {sorted(unfilled)}")
    print(f"OBLIGATIONS-UNCOVERED: {len(uncovered)} {uncovered}")
    print(f"ORPHAN-TESTS: {len(orphans)} {orphans}")
    print(f"ASSERTIONLESS: {len(assertionless)} {sorted(assertionless)}")
    print(f"SKIPPED: {len(skipped)} {sorted(skipped)}")
    print(f"AMENDMENT-UNCITED: {len(uncited)} {sorted(uncited)}")
    failed = bool(unfilled or uncovered or orphans or assertionless or skipped or uncited)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-stub", action="store_true")
    parser.add_argument("battery", nargs="?", default=str(DEFAULT_BATTERY))
    args = parser.parse_args(argv[1:])
    if args.emit_stub:
        sys.stdout.write(emit_stub())
        return 0
    return grade(pathlib.Path(args.battery))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
