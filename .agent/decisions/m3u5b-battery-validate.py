#!/usr/bin/env python3
"""Grade the M3.5b obligation battery and its red-control catalogue against the contract.

    uv run python .agent/decisions/m3u5b-battery-validate.py
    uv run python .agent/decisions/m3u5b-battery-validate.py --emit-stub \
        > tests/test_cli_removal_battery.py
    uv run python .agent/decisions/m3u5b-battery-validate.py --emit-controls \
        > .agent/decisions/m3u5b-mutants.json

`--emit-stub` and `--emit-controls` are the seeds' SINGLE SOURCE OF TRUTH. Both parse
`m3u5b-contract.md`, so neither seed can drift from the contract it encodes: the obligation
bullets `**Dnn**` in sections 1-7, the section 10 correction table, the three section 10 scope
corrections, and the section 11 gate-2 strengthenings.

D29 is EXCLUDED from the battery by construction. It is the gate's own meta-obligation ("the
battery must fail when one obligation remains undone"), which the red-control catalogue
discharges rather than a test body. Section 11 binds the battery to D01-D28.

COMPOUND OBLIGATIONS EXPAND INTO CLAUSES. Contract X39 rules that D15, D18 and D22 cannot be
certified by one asserted clause plus an obligation citation, so each gets one test and one red
control PER CLAUSE. The clause sets are DERIVED, never hand-listed:

    D15  two clauses, from the section 10 scope correction's own split -- 6 runtime modules and
         12 example files. Each clause asserts every member of its set individually.
    D18  one clause per row of D18's own table, so a re-based frame that lost its property
         cannot hide behind a sibling frame that kept one.
    D22  one clause per DIRECTION, which section 11 names explicitly, plus the protected fence
         the section 10 scope correction adds.

Control line reports, and every one must be zero for `PASS`:

    UNFILLED-TESTS          bodies still carrying the `UNFILLED` marker
    OBLIGATIONS-UNCOVERED   contract clauses with no test named for them
    ORPHAN-TESTS            tests naming no contract clause
    ASSERTIONLESS           filled bodies that assert nothing
    SKIPPED                 bodies that skip, by call or by decorator
    CORRECTION-UNCITED      corrected obligations whose docstring dropped its correction
    CONTROLS-UNFILLED       catalogue rows still carrying an `unknown` field
    CONTROLS-UNCOVERED      battery tests with no red control aimed at them
    CONTROLS-ORPHAN         catalogue rows aiming at no battery test

`ASSERTIONLESS` and `SKIPPED` are the two cheapest ways to satisfy a coverage count while
asserting nothing. `CORRECTION-UNCITED` guards the defect this unit already found eight times:
section 10 OVERRIDES the bullet above it, so a body encoding the literal bullet for a corrected
obligation goes red against correct code.

This validator grades SHAPE only. The red/green credential is a separate artifact, produced by
`m3u5b-mutants.py`, exactly as contract X33 and X34 require.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = HERE / "m3u5b-contract.md"
DEFAULT_BATTERY = ROOT / "tests" / "test_cli_removal_battery.py"
DEFAULT_CONTROLS = HERE / "m3u5b-mutants.json"
MARKER = "UNFILLED"
UNKNOWN = "unknown"

ASSERTING = re.compile(r"\bself\.(assert|fail)\w*\(")
SKIPPING = re.compile(r"\bself\.skipTest\(|@unittest\.skip|@skip(?:If|Unless)?\b")

# `**Dnn**` or `**Dnn — TITLE**` at column 0. The obligations are paragraphs here, not the
# indented bullets M3.5a used, so folding runs to the next obligation or heading.
OBLIGATION = re.compile(r"^\*\*(D\d{2})(\s+—[^*]*)?\*\*\s*(.*)$")
STOP = re.compile(r"^(\*\*D\d{2}|#{2,3} |---\s*$|\*\*[A-Z])")
TABLE_ROW = re.compile(r"^\|(?!-)(.+)\|\s*$")

# A control may aim at any test the sweep's verdict modules run, never the battery alone. A
# D18 clause obligation protects a FRAME in another module, so restricting targets to the
# battery would report the contract's own D18 table as fourteen orphans.
VERDICT_MODULES = (
    "test_cli_removal_battery",
    "test_cli_channels",
    "test_cli_channels_battery",
    "test_cli",
    "test_submission_battery",
)

BATTERY_IDS = [f"D{index:02d}" for index in range(1, 29)]
CLAUSE_TAGS = "abcdefghijklmnopqrstuvwxyz"


def _lines() -> list[str]:
    return CONTRACT.read_text(encoding="utf-8").splitlines()


def _obligations() -> list[dict[str, str]]:
    """Fold every `**Dnn**` paragraph, its tables included, into one obligation record."""
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in _lines():
        match = OBLIGATION.match(line)
        if match:
            title = (match.group(2) or "").strip()
            current = {"id": match.group(1), "text": f"{title} {match.group(3)}".strip()}
            rows.append(current)
            continue
        if current is None:
            continue
        if STOP.match(line):
            current = None
            continue
        if line.strip():
            current["text"] = f"{current['text']} {line.strip()}"
    ids = [row["id"] for row in rows]
    wanted = [f"D{index:02d}" for index in range(1, 30)]
    if ids != wanted:
        raise SystemExit(f"ABORT   contract holds {ids}, expected D01-D29 in order")
    return [row for row in rows if row["id"] in BATTERY_IDS]


def _corrections() -> dict[str, list[tuple[str, str]]]:
    """Section 10's correction table plus its three scope-correction bullets, by obligation."""
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("## 10.")[-1].split("## 11.")[0]
    binding: dict[str, list[tuple[str, str]]] = {}

    for line in section.splitlines():
        match = TABLE_ROW.match(line)
        if not match:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        number, targets, wrong, correct = cells
        for target in re.findall(r"D\d{2}", targets):
            binding.setdefault(target, []).append(
                (f"correction {number}", f"WRONG AS WRITTEN: {wrong} -- CORRECT: {correct}")
            )

    for match in re.finditer(r"^- \*\*(D\d{2})'s ([^*]+)\*\*(.*)$", section, re.MULTILINE):
        target, headline, tail = match.groups()
        binding.setdefault(target, []).append(
            (f"scope correction ({target}'s {headline})", tail.strip())
        )
    if not binding:
        raise SystemExit("ABORT   contract section 10 holds no corrections; eight are binding")
    return binding


def _strengthenings() -> dict[str, str]:
    """Section 11's gate-2 bullets, which bind construction rather than obligation text."""
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("**Gate 2 —")[-1].split("**Gate 3 —")[0]
    found: dict[str, str] = {}
    for match in re.finditer(r"^- \*\*([^*]+)\*\*(.*)$", section, re.MULTILINE):
        headline, tail = match.groups()
        body = f"{headline.strip()}{tail}".strip()
        for target in re.findall(r"D\d{2}", headline):
            found[target] = body
    if not found:
        raise SystemExit("ABORT   section 11 names no gate-2 strengthening; three are binding")
    return found


def _d18_clauses() -> list[str]:
    """One clause per row of D18's own table, so no frame hides behind a sibling."""
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("**D18**")[-1].split("**D19**")[0]
    frames: list[str] = []
    for line in section.splitlines():
        match = TABLE_ROW.match(line)
        if not match:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if len(cells) != 2 or cells[0] == "frame":
            continue
        frames.append(f"{cells[0]} -- preserve: {cells[1]}")
    if len(frames) != 18:
        raise SystemExit(f"ABORT   D18's table holds {len(frames)} rows, expected 18")
    return frames


def _verdict_test_names() -> set[str]:
    """Every test name a control may legitimately aim at, read from the verdict modules."""
    names: set[str] = set()
    for module in VERDICT_MODULES:
        path = ROOT / "tests" / f"{module}.py"
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    return names


def _clauses() -> dict[str, list[str]]:
    return {
        "D15": [
            (
                "the SIX runtime modules stay byte-identical to their `36f7890` git objects, "
                "each asserted individually"
            ),
            (
                "the TWELVE `examples/` files stay byte-identical to their `36f7890` git "
                "objects, each asserted individually"
            ),
        ],
        "D18": _d18_clauses(),
        "D22": [
            "DIRECTION cli-route: every CLI-route locus was rewritten and names no removed command",
            (
                "DIRECTION library-route: every library-API locus is byte-identical, "
                "`System.handle` prose included, so this unit pre-empts no M3.6a doc work"
            ),
            (
                "the opening ` ```text ` `handle(request)` fence is PROTECTED and "
                "byte-identical; gate 5 cannot reach it, so the battery asserts it directly"
            ),
        ],
    }


def _slug(text: str, limit: int = 54) -> str:
    words = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return words[:limit].rstrip("_") or "obligation"


def _units() -> list[dict[str, str]]:
    """Every graded unit: a simple obligation, or one clause of a compound one."""
    clauses = _clauses()
    units: list[dict[str, str]] = []
    for row in _obligations():
        parts = clauses.get(row["id"])
        if not parts:
            units.append(
                {
                    "key": row["id"],
                    "id": row["id"],
                    "clause": "",
                    "text": row["text"],
                    "name": f"test_{row['id'].lower()}_{_slug(row['text'])}",
                }
            )
            continue
        for index, clause in enumerate(parts):
            tag = CLAUSE_TAGS[index]
            units.append(
                {
                    "key": f"{row['id']}{tag}",
                    "id": row["id"],
                    "clause": clause,
                    "text": row["text"],
                    "name": f"test_{row['id'].lower()}{tag}_{_slug(clause)}",
                }
            )
    return units


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
    units = _units()
    corrections = _corrections()
    strengthenings = _strengthenings()
    body = [
        '"""M3.5b obligation battery: one test per contract obligation clause D01-D28.',
        "",
        "Seeded by `.agent/decisions/m3u5b-battery-validate.py --emit-stub` from the obligation",
        "paragraphs in `m3u5b-contract.md`. Each docstring carries its obligation verbatim,",
        "followed by every section 10 correction that overrides it and every section 11 gate-2",
        "strengthening that binds its construction. The body is the work.",
        "",
        "A CORRECTED obligation is encoded in its CORRECTED form. Section 10 supersedes the",
        "bullet text above it, so encoding the literal bullet is a defect that goes red against",
        "correct code.",
        "",
        "Compound obligations D15, D18 and D22 carry one test PER CLAUSE, per contract X39. A",
        "clause test asserts its own clause alone; a sibling clause is another test's work.",
        "",
        "Replace each `self.fail` marker with real assertions. A body that asserts nothing is",
        "graded ASSERTIONLESS, and a body that skips is graded SKIPPED. Both fail the validator.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import unittest",
        "",
        "",
        "class RemovalObligationBatteryTests(unittest.TestCase):",
        '    """One test per M3.5b contract obligation clause, encoded in its corrected form."""',
    ]
    for unit in units:
        body += ["", f"    def {unit['name']}(self) -> None:"]
        body.append(f'        """{unit["key"]} obligation')
        body += ["", "        CONTRACT:"]
        body += _wrap(unit["text"], "        ")
        if unit["clause"]:
            body += ["", "        THIS CLAUSE, and no sibling clause:"]
            body += _wrap(unit["clause"], "        ")
        for label, text in corrections.get(unit["id"], ()):
            body += ["", f"        CORRECTED-BY {label}, superseding the text above:"]
            body += _wrap(text, "        ")
        if unit["id"] in strengthenings:
            body += ["", "        GATE-2 STRENGTHENING, binding this test's construction:"]
            body += _wrap(strengthenings[unit["id"]], "        ")
        body.append('        """')
        body.append(f'        self.fail("{MARKER} {unit["key"]}")')
    body += ["", "", 'if __name__ == "__main__":', "    unittest.main()", ""]
    return "\n".join(body)


def emit_controls() -> str:
    """Seed one all-`unknown` red control per graded unit, each row's SUBJECT named."""
    rows = [
        {
            "id": f"M{index:02d}",
            "obligation": unit["key"],
            "target_test": unit["name"],
            "expect": "killed",
            "kind": UNKNOWN,
            "path": UNKNOWN,
            "anchor": UNKNOWN,
            "replacement": UNKNOWN,
            "note": UNKNOWN,
        }
        for index, unit in enumerate(_units(), start=1)
    ]
    document = {
        "kind": "m3u5b-red-controls",
        "unit": "M3.5b",
        "note": (
            "One independent RED control per battery obligation clause, per contract X33. A "
            "control is a single anchored edit to the SHIPPED tree that must turn its target "
            "test red; `kind` is `reinsertion` where the edit restores something the removal "
            "deleted and `sensitivity` otherwise. Gate 3's reinsertion subset and gate 2's red "
            "credential are the same catalogue read two ways. `anchor` must occur EXACTLY once "
            "in `path`; the harness asserts the count and aborts on a miss."
        ),
        "rows": rows,
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def grade(battery: pathlib.Path, controls: pathlib.Path) -> int:
    if not battery.is_file():
        raise SystemExit(f"ABORT   no battery at {battery}; seed it with --emit-stub")
    units = _units()
    corrections = _corrections()
    wanted = {unit["key"]: unit["name"] for unit in units}
    by_name = {unit["name"]: unit["key"] for unit in units}
    obligation_of = {unit["key"]: unit["id"] for unit in units}

    source = battery.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found: dict[str, ast.FunctionDef] = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }

    unfilled: list[str] = []
    assertionless: list[str] = []
    skipped: list[str] = []
    uncited: list[str] = []
    for name, node in found.items():
        key = by_name.get(name, name)
        # `get_source_segment` starts at `def`, so a decorator lives outside it and a
        # `@unittest.skip` would otherwise read as an ordinary filled body.
        decorators = "\n".join(f"@{ast.unparse(item)}" for item in node.decorator_list)
        segment = f"{decorators}\n{ast.get_source_segment(source, node) or ''}"
        docstring = ast.get_docstring(node) or ""
        for label, _ in corrections.get(obligation_of.get(key, ""), ()):
            if f"CORRECTED-BY {label}" not in docstring:
                uncited.append(f"{key}/{label}")
        if SKIPPING.search(segment):
            skipped.append(key)
            continue
        if MARKER in segment:
            unfilled.append(key)
            continue
        if not ASSERTING.search(segment):
            assertionless.append(key)

    uncovered = sorted(key for key, name in wanted.items() if name not in found)
    orphans = sorted(name for name in found if name not in by_name)

    control_unfilled: list[str] = []
    control_orphan: list[str] = []
    aimed: set[str] = set()
    reachable = _verdict_test_names()
    if controls.is_file():
        document = json.loads(controls.read_text(encoding="utf-8"))
        for row in document.get("rows", []):
            target = row.get("target_test", "")
            # A row covers the clause it DECLARES, once its target names a test that really
            # exists. Resolving coverage back through the target would confine every control
            # to the battery and silently drop the cross-module D18 frames.
            if target in reachable:
                aimed.add(str(row.get("obligation", "")))
            else:
                control_orphan.append(f"{row.get('id', '?')}->{target}")
            if any(value == UNKNOWN for value in row.values()):
                control_unfilled.append(str(row.get("id", "?")))
    else:
        control_orphan.append(f"missing catalogue {controls}")
    control_uncovered = sorted(key for key in wanted if key not in aimed)

    print(f"BATTERY: {battery}")
    print(f"CONTROLS: {controls}")
    print(f"OBLIGATIONS: {len(set(obligation_of.values()))} CLAUSES: {len(units)}")
    print(f"TESTS: {len(found)}")
    print(f"UNFILLED-TESTS: {len(unfilled)} {sorted(unfilled)}")
    print(f"OBLIGATIONS-UNCOVERED: {len(uncovered)} {uncovered}")
    print(f"ORPHAN-TESTS: {len(orphans)} {orphans}")
    print(f"ASSERTIONLESS: {len(assertionless)} {sorted(assertionless)}")
    print(f"SKIPPED: {len(skipped)} {sorted(skipped)}")
    print(f"CORRECTION-UNCITED: {len(uncited)} {sorted(uncited)}")
    print(f"CONTROLS-UNFILLED: {len(control_unfilled)} {sorted(control_unfilled)}")
    print(f"CONTROLS-UNCOVERED: {len(control_uncovered)} {control_uncovered}")
    print(f"CONTROLS-ORPHAN: {len(control_orphan)} {sorted(control_orphan)}")
    failed = bool(
        unfilled
        or uncovered
        or orphans
        or assertionless
        or skipped
        or uncited
        or control_unfilled
        or control_uncovered
        or control_orphan
    )
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


def _filled(stub: str) -> str:
    """Turn the seed into a minimally VALID battery: every marker becomes a real assertion."""
    return re.sub(
        rf'self\.fail\("{MARKER} [^"]+"\)', "self.assertTrue(True)  # filled", stub
    )


def _fill_controls(controls: str) -> str:
    document = json.loads(controls)
    for row in document["rows"]:
        for field in ("kind", "path", "anchor", "replacement", "note"):
            row[field] = f"filled-{field}"
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def self_test() -> int:
    """Grade the validator BOTH WAYS plus one negative control per reported counter.

    A validator that passes on its first run has not been graded. Each control below mutates a
    KNOWN-GOOD pair so exactly one counter must move; a control that fails to fire is a hole in
    this file, not in the battery.
    """
    import tempfile

    stub = emit_stub()
    controls = emit_controls()
    good_battery = _filled(stub)
    good_controls = _fill_controls(controls)
    name = _units()[0]["name"]
    target = _units()[0]["key"]
    corrected = next(unit for unit in _units() if unit["id"] == "D17")

    cases: list[tuple[str, str, str, str]] = [
        ("seed is unfilled", stub, controls, "UNFILLED-TESTS: 48"),
        ("seed controls unfilled", stub, controls, "CONTROLS-UNFILLED: 48"),
        (
            "pass body asserts nothing",
            good_battery.replace(
                "self.assertTrue(True)  # filled", "pass  # filled", 1
            ),
            good_controls,
            f"ASSERTIONLESS: 1 ['{target}']",
        ),
        (
            "skipTest call",
            good_battery.replace(
                "self.assertTrue(True)  # filled", "self.skipTest('x')", 1
            ),
            good_controls,
            f"SKIPPED: 1 ['{target}']",
        ),
        (
            "skip decorator",
            good_battery.replace(
                f"    def {name}(self)", f"    @unittest.skip('x')\n    def {name}(self)", 1
            ),
            good_controls,
            f"SKIPPED: 1 ['{target}']",
        ),
        (
            "orphan test",
            good_battery.replace(
                f"    def {name}(self)",
                "    def test_zz_orphan(self) -> None:\n        self.assertTrue(True)\n\n"
                f"    def {name}(self)",
                1,
            ),
            good_controls,
            "ORPHAN-TESTS: 1 ['test_zz_orphan']",
        ),
        (
            "deleted test",
            good_battery.replace(f"    def {name}(self)", "    def test_gone_(self)", 1),
            good_controls,
            f"OBLIGATIONS-UNCOVERED: 1 ['{target}']",
        ),
        (
            "dropped correction",
            good_battery.replace("CORRECTED-BY correction 1", "SEE correction 1", 1),
            good_controls,
            f"CORRECTION-UNCITED: 1 ['{corrected['key']}/correction 1']",
        ),
        (
            "control left unknown",
            good_battery,
            good_controls.replace('"filled-path"', f'"{UNKNOWN}"', 1),
            "CONTROLS-UNFILLED: 1 ['M01']",
        ),
        (
            "control aims nowhere",
            good_battery,
            good_controls.replace(f'"{name}"', '"test_nowhere"', 1),
            "CONTROLS-ORPHAN: 1 ['M01->test_nowhere']",
        ),
        (
            "control aims nowhere leaves its clause uncovered",
            good_battery,
            good_controls.replace(f'"{name}"', '"test_nowhere"', 1),
            f"CONTROLS-UNCOVERED: 1 ['{target}']",
        ),
    ]

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as room:
        base = pathlib.Path(room)
        battery_path = base / "battery.py"
        controls_path = base / "controls.json"

        battery_path.write_text(good_battery, encoding="utf-8")
        controls_path.write_text(good_controls, encoding="utf-8")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = grade(battery_path, controls_path)
        report = buffer.getvalue()
        if code != 0 or "\nPASS" not in report:
            failures.append("POSITIVE   a fully filled pair must grade PASS")
        print(f"POSITIVE   filled pair grades PASS rc={code}")

        for label, battery_text, controls_text, expected in cases:
            battery_path.write_text(battery_text, encoding="utf-8")
            controls_path.write_text(controls_text, encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = grade(battery_path, controls_path)
            report = buffer.getvalue()
            fired = expected in report and code == 1
            print(f"{'CONTROL-OK' if fired else 'CONTROL-DEAD'}   {label} -> {expected!r}")
            if not fired:
                failures.append(f"{label}: expected {expected!r}")

    print(f"CONTROLS: {len(cases)} FIRED: {len(cases) - len(failures)}")
    print("FAIL" if failures else "PASS")
    for line in failures:
        print(f"  {line}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-stub", action="store_true")
    parser.add_argument("--emit-controls", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("battery", nargs="?", default=str(DEFAULT_BATTERY))
    parser.add_argument("controls", nargs="?", default=str(DEFAULT_CONTROLS))
    args = parser.parse_args(argv[1:])
    if args.emit_stub:
        sys.stdout.write(emit_stub())
        return 0
    if args.emit_controls:
        sys.stdout.write(emit_controls())
        return 0
    if args.self_test:
        return self_test()
    return grade(pathlib.Path(args.battery), pathlib.Path(args.controls))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
