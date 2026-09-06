"""Gate 2 for M3.6a2 — grade the battery against the contract's own obligation set.

The contract is the authority for the id set; the battery file is graded against it, never the
reverse. Coverage is a FLOOR of one test per obligation (contract C02): an identity makes a second
test for one obligation a gate failure, so the catalogue could not be extended per subproperty
without permission, which is how M3.6a1 shipped three conjuncts no row could see.

Ids are matched in the contract's OWN spelling. Normalising through `.upper()`/`.lower()` is what
turns a lettered id into an orphan over an uncovered one, and neither counter shows it.

Checks, each reported on its own line and each failing independently:
  OBLIGATIONS      the contract defines a contiguous L01..Lnn with no duplicates
  UNCOVERED        obligations with no battery test                       must be 0
  ORPHAN           battery tests naming an id the contract does not define must be 0
  STUB             battery tests still carrying the seed marker            must be 0
  CORRECTION-BIND  a correction states its subject: an obligation id, a section, a gate, or an
                   explicit none naming the instrument it repairs — never nothing at all

`--self-test` seeds each failure and requires it to fire, then requires a clean copy to pass. Run
that after every scale-up: a both-ways credential earned at seed size is not a credential at fill
size.
"""
import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".agent/decisions/m3u6a2-contract.md"
BATTERY = ROOT / "tests/test_lifecycle_removal_battery.py"
SEED_MARKER = "SEED STUB"

OBLIGATION = re.compile(r"^- \*\*(L\d\d)\*\* ", re.M)
# A correction ends at the next top-level bullet or heading, NEVER at end-of-file: bounding it with
# `\Z` let the LAST correction absorb the whole remaining document, so it matched some obligation id
# further down and could never be reported unbound. Measured — C02 read as bound until C03 landed
# behind it, at which point the same text read as unbound with no edit to C02.
CORRECTION = re.compile(r"^- \*\*(C\d\d)\*\* (.*?)(?=^- \*\*|^#)", re.M | re.S)
BINDS = re.compile(r"binds (?:SECTION \d+|GATE \d+|L\d\d)")
CITES = re.compile(r"\bL\d\d\b")
# An instrument OUTSIDE section 6 is repaired by a correction that binds no numbered clause (C13),
# and the check failed closed on it. The escape is granted only to a correction that BOTH declares
# the none AND names the file it repairs: a bare `binds NO obligation` would be a free bypass for
# every later correction, which is the failure this check exists to prevent.
DECLARES_NONE = re.compile(r"binds NO obligation")
NAMES_INSTRUMENT = re.compile(r"`[\w./-]+\.py`")
TEST_ID = re.compile(r"^test_(l\d\d)_")


def obligations(contract: str) -> list[str]:
    return OBLIGATION.findall(contract)


def battery_tests(source: str) -> dict[str, list[tuple[str, bool]]]:
    """id -> [(test name, is_stub)]. A stub is a body whose only content names the seed marker."""
    found: dict[str, list[tuple[str, bool]]] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        match = TEST_ID.match(node.name)
        if match is None:
            continue
        body = ast.get_source_segment(source, node) or ""
        found.setdefault(match.group(1).upper(), []).append((node.name, SEED_MARKER in body))
    return found


def report(contract: str, battery: str) -> tuple[list[str], int]:
    lines: list[str] = []
    failures = 0
    ids = obligations(contract)
    expected = [f"L{n:02d}" for n in range(1, len(ids) + 1)]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    contiguous = ids == expected and not duplicates
    lines.append(f"OBLIGATIONS: {len(ids)} {'contiguous' if contiguous else 'BROKEN'}"
                 + (f" duplicates={duplicates}" if duplicates else ""))
    failures += 0 if contiguous else 1

    tests = battery_tests(battery)
    uncovered = [i for i in ids if i not in tests]
    orphan = sorted(set(tests) - set(ids))
    stub = sorted(name for rows in tests.values() for name, is_stub in rows if is_stub)
    for label, rows in (("UNCOVERED", uncovered), ("ORPHAN", orphan), ("STUB", stub)):
        lines.append(f"{label}: {len(rows)}" + (f" {rows[:8]}" if rows else ""))
        failures += 1 if rows else 0

    unbound = [
        cid for cid, text in CORRECTION.findall(contract)
        if not CITES.search(text) and not BINDS.search(text)
        and not (DECLARES_NONE.search(text) and NAMES_INSTRUMENT.search(text))
    ]
    lines.append(f"CORRECTION-BIND: {len(unbound)} unbound" + (f" {unbound}" if unbound else ""))
    failures += 1 if unbound else 0
    return lines, failures


def self_test() -> int:
    contract = CONTRACT.read_text(encoding="utf-8")
    battery = BATTERY.read_text(encoding="utf-8")
    first = obligations(contract)[0]
    # The pass-side control must grade a FILLED battery: at seed time every test is a stub, so
    # grading the committed file both ways would only ever prove the failing half.
    filled = re.sub(rf'\s*self\.(?:fail|skipTest)\("{SEED_MARKER}[^"]*"\)', "\n        pass",
                    battery)
    controls: list[tuple[str, str, str, str]] = [
        ("clean, filled battery", contract, filled, ""),
        ("dropped obligation", contract.replace(f"- **{first}** ", f"- {first} ", 1), battery,
         "OBLIGATIONS"),
        ("uncovered obligation", contract,
         re.sub(rf"def test_{first.lower()}_", "def test_l99_", battery, count=1), "UNCOVERED"),
        ("orphan test", contract, battery.replace("class ", "class ", 1)
         + f"\n\nclass _Orphan:\n    def test_l98_orphan(self):\n        pass\n", "ORPHAN"),
        # Seeded MID-DOCUMENT on purpose: appended at the end it would fire even under a regex
        # bounded by `\Z`, and that is the exact defect this control exists to catch.
        ("unbound correction", contract.replace(
            "\n## 9. Session boundaries",
            "\n- **C99** a correction naming nothing.\n\n## 9. Session boundaries", 1),
         battery, "CORRECTION-BIND"),
        ("explicit none naming no instrument", contract.replace(
            "\n## 9. Session boundaries",
            "\n- **C97** binds NO obligation and no gate, and names no file either.\n"
            "\n## 9. Session boundaries", 1),
         battery, "CORRECTION-BIND"),
    ]
    fired = 0
    for label, c, b, expect in controls:
        lines, failures = report(c, b)
        hit = any(line.startswith(expect) and not line.endswith(" 0") for line in lines) if expect \
            else failures == 0
        print(f"  {'FIRING' if hit else 'SILENT'}  {label}")
        fired += 1 if hit else 0
    print(f"SELF-TEST: {fired}/{len(controls)} firing")
    return 0 if fired == len(controls) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grade M3.6a2's battery against its contract.")
    parser.add_argument("--self-test", action="store_true", help="seed each failure and require it")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not BATTERY.exists():
        print(f"ABSENT: {BATTERY.relative_to(ROOT)}")
        return 1
    lines, failures = report(CONTRACT.read_text(encoding="utf-8"),
                             BATTERY.read_text(encoding="utf-8"))
    print("\n".join(lines))
    print("GATE 2:", "PASS" if failures == 0 else f"FAIL ({failures} checks)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
