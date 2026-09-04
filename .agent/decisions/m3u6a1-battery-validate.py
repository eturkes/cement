#!/usr/bin/env python3
"""Grade M3.6a1's diff-blind obligation battery against the contract itself.

The battery is `tests/test_migration_battery.py`, one test per obligation in
`m3u6a1-contract.md` section 4 (D01-D28 plus D14a, 29 in all). This grader parses
the contract rather than a hand list, so the seed cannot drift from the spec, and
`--emit-stub` is the seed's SINGLE SOURCE OF TRUTH: the stub, the coverage domain
and the correction bindings all come from the same parse.

Section 10 CORRECTS obligations after the fact. A correction OVERRIDES the bullet
it cites, so a body encoding the literal bullet goes red against correct code.
`CORRECTION-UNCITED` fails any docstring that dropped its `CORRECTED-BY C<nn>`
block, which is what keeps a corrected obligation from being encoded in its
superseded form.

Control lines, all zero for PASS: UNFILLED, UNCOVERED, ORPHAN, ASSERTIONLESS,
SKIPPED, CORRECTION-UNCITED.

Usage:
    m3u6a1-battery-validate.py --emit-stub [> tests/test_migration_battery.py]
    m3u6a1-battery-validate.py [--battery PATH] [--root DIR]
    m3u6a1-battery-validate.py --self-test
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT_NAME = "m3u6a1-contract.md"
BATTERY_RELPATH = pathlib.Path("tests") / "test_migration_battery.py"

# `- **D01** text` / `- **D14a** text` at the start of a section-4 bullet. The id
# pattern carries `\d+`, never `\d`: an `A\d` regex silently dropped every id past
# the digit boundary on M3.5a, which is the fail-open shape of a forbidden list.
OBLIGATION = re.compile(r"^- \*\*(D\d+[a-z]?)\*\*\s*(.*)$")
CORRECTION = re.compile(r"^- \*\*(C\d+)\b\s*(.*)$")
# Any indent, not exactly two: a nested sub-bullet indents its own continuation deeper, and
# `^  \S` stopped the fold there, silently dropping every id after the first nested one.
BULLET_CONT = re.compile(r"^ {2,}\S")
ID_TOKEN = re.compile(r"\b(D\d+[a-z]?)\b")
# `M3.5b's D25` is ANOTHER unit's obligation, and its number collides with a live
# local id. A bare token scan binds it here and a diff-blind author then encodes a
# foreign correction into a local obligation. Ids carrying a unit qualifier are
# foreign; ids without one are this contract's.
FOREIGN = re.compile(r"M\d+(?:\.\d+)?[a-z]?\d*(?:'s)?\s+$")

ASSERTING = re.compile(r"\bself\.(assert\w*|fail\w*)\(")
SKIPPING = re.compile(r"\bself\.skipTest\(|@unittest\.skip|@skip(?:If|Unless)?\b")
UNFILLED_MARKER = "UNFILLED:"
CORRECTED_BY = re.compile(r"\bCORRECTED-BY\s+((?:C\d+(?:,\s*)?)+)")

CLASS_NAME = "MigrationBatteryTests"


# --------------------------------------------------------------------------- parse


def _contract_lines(root: pathlib.Path) -> list[str]:
    path = root / ".agent" / "decisions" / CONTRACT_NAME
    return path.read_text(encoding="utf-8").splitlines()


def _fold(lines: list[str], start: int, pattern: re.Pattern[str]) -> tuple[str, int]:
    """Join a bullet's continuation lines. Stops at the next bullet or heading."""
    head = pattern.match(lines[start])
    assert head is not None
    parts = [head.group(2).strip()]
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            break
        if line.startswith("- ") or line.startswith("#") or line.startswith("---"):
            break
        if not BULLET_CONT.match(line):
            break
        parts.append(line.strip())
        index += 1
    return " ".join(part for part in parts if part), index


def obligations(root: pathlib.Path) -> list[tuple[str, str]]:
    lines = _contract_lines(root)
    found: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        head = OBLIGATION.match(lines[index])
        if head is not None:
            text, next_index = _fold(lines, index, OBLIGATION)
            found.append((head.group(1), text))
            index = next_index
        else:
            index += 1
    return found


def corrections(root: pathlib.Path) -> dict[str, list[str]]:
    """Map obligation id -> correction ids that cite it.

    A correction binds an obligation when its own text names that obligation as a
    whole token. Whole-token membership, never containment: `D14` sits inside
    `D14a` and a containment test certifies a binding that was never written.
    """
    lines = _contract_lines(root)
    domain = {obligation_id for obligation_id, _ in obligations(root)}
    bound: dict[str, list[str]] = {}
    index = 0
    while index < len(lines):
        head = CORRECTION.match(lines[index])
        if head is not None:
            text, next_index = _fold(lines, index, CORRECTION)
            targets: set[str] = set()
            for hit in ID_TOKEN.finditer(text):
                if FOREIGN.search(text[: hit.start()]):
                    continue
                if hit.group(1) in domain:
                    targets.add(hit.group(1))
            for target in sorted(targets):
                bound.setdefault(target, [])
                if head.group(1) not in bound[target]:
                    bound[target].append(head.group(1))
            index = next_index
        else:
            index += 1
    return bound


def correction_ids(root: pathlib.Path) -> list[str]:
    lines = _contract_lines(root)
    return [match.group(1) for line in lines if (match := CORRECTION.match(line))]


# ---------------------------------------------------------------------- stub emit


def _slug(text: str, limit: int = 58) -> str:
    plain = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    words: list[str] = []
    for word in plain.split("_"):
        if not word:
            continue
        candidate = "_".join([*words, word])
        if len(candidate) > limit:
            break
        words.append(word)
    return "_".join(words) or "obligation"


def _wrap(text: str, indent: str, width: int = 92) -> list[str]:
    return textwrap.wrap(text, width=width - len(indent)) or [""]


def emit_stub(root: pathlib.Path) -> str:
    bound = corrections(root)
    out: list[str] = [
        '"""M3.6a1 obligation battery — one test per contract obligation.',
        "",
        "DIFF-BLIND. Written from `.agent/decisions/m3u6a1-contract.md` and this",
        "worktree's own pre-implementation baseline. The migrated `tests/` and",
        "`examples/` trees, `m3u6a1-surgery.py`, `git show main:` and `git diff main`",
        "are all out of bounds.",
        "",
        "Each test asserts the PROPERTY its obligation states, derived from the shipped",
        "tree by AST or by running the named gate. It never pins a helper name, a",
        "variable name, an occurrence count or an assertion spelling that the contract",
        "does not itself state: those are the migration author's choice, and a pin on",
        "one of them goes red against correct code.",
        "",
        "Graded by `.agent/decisions/m3u6a1-battery-validate.py`.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import ast",
        "import pathlib",
        "import subprocess",
        "import sys",
        "import unittest",
        "",
        'ROOT = pathlib.Path(__file__).resolve().parents[1]',
        "",
        "",
        f"class {CLASS_NAME}(unittest.TestCase):",
    ]
    for obligation_id, text in obligations(root):
        name = f"test_{obligation_id.lower()}_{_slug(text)}"
        out.append("")
        out.append(f"    def {name}(self) -> None:")
        doc = [f"{obligation_id} — {text}"]
        body = _wrap(" ".join(doc), "        ")
        out.append(f'        """{body[0]}')
        for line in body[1:]:
            out.append(f"        {line}")
        if obligation_id in bound:
            out.append("")
            out.append(f"        CORRECTED-BY {', '.join(bound[obligation_id])}")
        out.append('        """')
        out.append(f'        self.fail("{UNFILLED_MARKER} {obligation_id}")')
    out.append("")
    out.append("")
    out.append('if __name__ == "__main__":')
    out.append("    unittest.main()")
    out.append("")
    return "\n".join(out)


# -------------------------------------------------------------------------- grade


def _segment(source: str, node: ast.AST) -> str:
    """Source of a function INCLUDING its decorators.

    `ast.get_source_segment` starts at `def`, so a `@unittest.skip` decorator reads
    as an ordinary filled body unless the decorator list is unparsed and prepended.
    """
    text = ast.get_source_segment(source, node) or ""
    decorators = getattr(node, "decorator_list", [])
    prefix = "".join(f"@{ast.unparse(item)}\n" for item in decorators)
    return prefix + text


def grade(battery: pathlib.Path, root: pathlib.Path) -> int:
    declared = obligations(root)
    domain = [obligation_id for obligation_id, _ in declared]
    bound = corrections(root)

    if not battery.exists():
        print(f"ABSENT: {battery}")
        print("RESULT: FAIL")
        return 1

    source = battery.read_text(encoding="utf-8")
    tree = ast.parse(source)

    tests: dict[str, list[ast.FunctionDef]] = {}
    orphans: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        match = re.match(r"^test_(d\d+[a-z]?)_", node.name)
        # `D14a` is not `D14A`: normalise through the contract's own spelling rather
        # than by `.upper()`, which mangles a lettered suffix into an unknown id.
        spelling = {declared_id.lower(): declared_id for declared_id in domain}
        if match is None or match.group(1) not in spelling:
            orphans.append(node.name)
            continue
        obligation_id = spelling[match.group(1)]
        tests.setdefault(obligation_id, []).append(node)

    unfilled: list[str] = []
    assertionless: list[str] = []
    skipped: list[str] = []
    uncited: list[str] = []
    for obligation_id in domain:
        for node in tests.get(obligation_id, []):
            text = _segment(source, node)
            doc = ast.get_docstring(node) or ""
            if UNFILLED_MARKER in text:
                unfilled.append(node.name)
                continue
            if SKIPPING.search(text):
                skipped.append(node.name)
            if not ASSERTING.search(text):
                assertionless.append(node.name)
            expected = bound.get(obligation_id, [])
            if expected:
                cited: set[str] = set()
                for hit in CORRECTED_BY.findall(doc):
                    cited.update(re.findall(r"C\d+", hit))
                for correction_id in expected:
                    if correction_id not in cited:
                        uncited.append(f"{node.name}:{correction_id}")

    uncovered = [obligation_id for obligation_id in domain if obligation_id not in tests]
    duplicates = [
        f"{obligation_id}x{len(nodes)}"
        for obligation_id, nodes in tests.items()
        if len(nodes) > 1
    ]
    orphans.extend(duplicates)

    print(f"OBLIGATIONS: {len(domain)}")
    print(f"TESTS: {sum(len(nodes) for nodes in tests.values())}")
    print(f"CORRECTIONS: {len(correction_ids(root))}")
    print(f"BOUND-OBLIGATIONS: {len(bound)}")
    print(f"UNFILLED: {len(unfilled)} {sorted(unfilled)[:6]}")
    print(f"UNCOVERED: {len(uncovered)} {uncovered}")
    print(f"ORPHAN: {len(orphans)} {sorted(orphans)}")
    print(f"ASSERTIONLESS: {len(assertionless)} {sorted(assertionless)}")
    print(f"SKIPPED: {len(skipped)} {sorted(skipped)}")
    print(f"CORRECTION-UNCITED: {len(uncited)} {sorted(uncited)}")

    failures = (
        len(unfilled)
        + len(uncovered)
        + len(orphans)
        + len(assertionless)
        + len(skipped)
        + len(uncited)
    )
    print(f"RESULT: {'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------- self test


def _fill(stub: str) -> str:
    """Turn the emitted stub into a body-complete battery, verbatim otherwise."""
    return re.sub(
        r'self\.fail\("' + UNFILLED_MARKER + r' (D\d+[a-z]?)"\)',
        r'self.assertTrue(True, "\1")',
        stub,
    )


def _run(root: pathlib.Path, battery: pathlib.Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(HERE / pathlib.Path(__file__).name),
            "--battery",
            str(battery),
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def self_test() -> int:
    """Grade the grader both ways from committed state, plus negative controls."""
    failures = 0
    with tempfile.TemporaryDirectory() as raw:
        stage = pathlib.Path(raw)
        decisions = stage / ".agent" / "decisions"
        decisions.mkdir(parents=True)
        shutil.copy2(ROOT / ".agent" / "decisions" / CONTRACT_NAME, decisions / CONTRACT_NAME)
        (stage / "tests").mkdir()
        battery = stage / BATTERY_RELPATH

        stub = emit_stub(stage)
        total = len(obligations(stage))

        def check(label: str, text: str, expect_rc: int, expect: list[str]) -> None:
            nonlocal failures
            battery.write_text(text, encoding="utf-8")
            code, out = _run(stage, battery)
            ok = code == expect_rc and all(line in out for line in expect)
            print(f"{'OK  ' if ok else 'FAIL'} {label}: rc={code} expect={expect_rc} {expect}")
            if not ok:
                failures += 1
                print(textwrap.indent(out, "      "))

        check("seed graded red", stub, 1, [f"UNFILLED: {total}"])
        filled = _fill(stub)
        check("filled graded green", filled, 0, ["RESULT: PASS", f"TESTS: {total}"])

        check(
            "control pass-bodies -> ASSERTIONLESS",
            re.sub(r"self\.assertTrue\(True, \"D\d+[a-z]?\"\)", "pass", filled),
            1,
            [f"ASSERTIONLESS: {total}"],
        )
        check(
            "control skipTest -> SKIPPED",
            filled.replace(
                'self.assertTrue(True, "D01")',
                'self.skipTest("x")\n        self.assertTrue(True, "D01")',
                1,
            ),
            1,
            ["SKIPPED: 1"],
        )
        decorated = filled.replace(
            "    def test_d02_",
            '    @unittest.skip("x")\n    def test_d02_',
            1,
        )
        check("control @unittest.skip decorator -> SKIPPED", decorated, 1, ["SKIPPED: 1"])
        check(
            "control extra test -> ORPHAN",
            filled.replace(
                f"class {CLASS_NAME}(unittest.TestCase):",
                f"class {CLASS_NAME}(unittest.TestCase):\n"
                "\n"
                "    def test_d99_not_an_obligation(self) -> None:\n"
                "        self.assertTrue(True)\n",
                1,
            ),
            1,
            ["ORPHAN: 1"],
        )
        first_id = obligations(stage)[0][0]
        deleted = re.sub(
            r"\n    def test_" + first_id.lower() + r"_.*?(?=\n    def |\n\nif __name__)",
            "",
            filled,
            flags=re.DOTALL,
        )
        check("control deleted test -> UNCOVERED", deleted, 1, [f"UNCOVERED: 1 ['{first_id}']"])

        bound = corrections(stage)
        assert bound, "self-test needs at least one corrected obligation"
        victim = sorted(bound)[0]
        dropped = filled.replace(f"CORRECTED-BY {', '.join(bound[victim])}", "", 1)
        # One dropped block un-cites EVERY correction bound to that obligation, so the
        # expected count is derived. A hardcoded 1 passed until an obligation gained a
        # second correction, which is the seed credential expiring with the contract.
        check(
            f"control dropped CORRECTED-BY -> CORRECTION-UNCITED ({victim}, {len(bound[victim])})",
            dropped,
            1,
            [f"CORRECTION-UNCITED: {len(bound[victim])}"],
        )
        check(
            "control duplicate test -> ORPHAN",
            filled.replace(
                f'self.assertTrue(True, "{first_id}")',
                f'self.assertTrue(True, "{first_id}")\n'
                f"\n"
                f"    def test_{first_id.lower()}_duplicate(self) -> None:\n"
                f"        self.assertTrue(True)",
                1,
            ),
            1,
            ["ORPHAN: 1"],
        )
        battery.unlink()
        check("control absent battery -> FAIL", "", 1, ["RESULT: FAIL"])

    print(f"SELF-TEST: {'PASS' if failures == 0 else 'FAIL'} ({failures} control(s) not firing)")
    return 0 if failures == 0 else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-stub", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--battery", type=pathlib.Path, default=None)
    parser.add_argument("--root", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    root = (args.root or ROOT).resolve()
    if args.self_test:
        return self_test()
    if args.emit_stub:
        sys.stdout.write(emit_stub(root))
        return 0
    battery = args.battery or (root / BATTERY_RELPATH)
    return grade(battery.resolve(), root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
