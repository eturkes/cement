"""Grade the M3.4 diff-blind obligation battery for coverage.

Usage:
  uv run python .agent/decisions/m3u4-battery-validate.py --emit-stub
  uv run python .agent/decisions/m3u4-battery-validate.py

Every obligation of ``.agent/decisions/m3u4-contract.md`` needs at least one filled
test in ``tests/test_proposal_binding_battery.py``, named ``test_<id>_<slug>``.
``--emit-stub`` writes the seed: every required test present, every body the UNFILLED
marker. That seed is STRUCTURALLY valid and still exits 1, so UNFILLED-TESTS is the
flush metric and it falls while the file's line count stays flat.

The manifest is the contract's numbered obligations B01-B27 mapped one-to-one onto
D01-D27, plus B28-B38 for the obligations sections 14 and 15 added and for the
sixteen lenses ``m3u4-attack.json`` deferred to S3. Section 14 and 15 rulings GOVERN
where they disagree with a numbered obligation, so every subject below is written in
its ruled form.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATTERY = ROOT / "tests" / "test_proposal_binding_battery.py"
CONTRACT = ROOT / ".agent" / "decisions" / "m3u4-contract.md"

UNFILLED = "UNFILLED"
DOCSTRING_MIN = 40
TEST_NAME = re.compile(r"^test_(?P<id>b\d{2})_[a-z0-9_]+$")

# ---------------------------------------------------------------------------
# The obligation manifest. id -> (min_tests, subject).
#
# ``min_tests`` is 1 unless the obligation carries INDEPENDENT pins that a single
# assertion cannot separate: a claim spanning several decisions, several read
# paths, or an accept/reject boundary pair needs one filled test per side.
# The lens each row discharges is named in the subject where one applies.
# ---------------------------------------------------------------------------
OBLIGATIONS: dict[str, tuple[int, str]] = {
    # --- section 3, confinement, as amended by section 14 -------------------
    "B01": (1, "one named private reader and at most one named private writer reach the request row"),
    "B02": (1, "confinement is a complement assertion over the shipped module, never a forbidden list"),
    "B03": (1, "the permitted owner set is exactly seven names and every freed path is absent from it"),
    "B04": (1, "the walk covers module level constants, so hoisted SQL cannot leave the owner set"),
    "B05": (1, "matching is on case folded whole SQL identifiers, so requests_scope is not a match"),
    "B06": (2, "A04 tripwire boundary: a literal hidden namer is rejected and runtime composition is not"),
    # --- section 4, public shape freeze -------------------------------------
    "B07": (1, "ProposalView fields are exactly id partition operation operation_revision input proposed_output provenance created_at_us"),
    "B08": (1, "PendingProposalGap fields are exactly proposal_id operation_revision input_hash"),
    "B09": (1, "review returns a frozen ReviewResult carrying proposal_id status example_id output"),
    "B10": (2, "Y20 path matrix: request identity is absent from every read review report event CLI payload and export"),
    "B11": (1, "signature and resolved hints plus slots present and dict absent pin all three shapes at once"),
    "B12": (1, "every kept projected value stays byte identical to baseline, with status the one named exemption"),
    "B13": (1, "A07 no growth: the converters lose the request_id entry and gain no statement or span"),
    "B14": (1, "Y12 export census: alphabetical __all__ position for ReviewResult and unchanged Outcome members"),
    # --- section 5, preserved invariants ------------------------------------
    "B15": (2, "A08 write order: the exact ordered write subsequence per decision, including quarantine"),
    "B16": (2, "reviewer nonempty control free 256 bytes, note empty allowed control free 2048 bytes, one shared now"),
    "B17": (1, "A09 exactly one example on accept and correct, none on reject, id equal to ReviewResult.example_id"),
    "B18": (3, "Y7 quarantine predicate inventory: partition operation revision input_hash input_json output promoted"),
    "B19": (1, "A10 status_sequence equals the matching decision event sequence and rejects every intervening one"),
    "B20": (1, "each read path hides everything outside the scope it names, and proposals names no operation"),
    "B21": (2, "underscore colliders and case variants keep equals from weakening to LIKE on partition and operation"),
    "B22": (2, "exact pending counts, bounded detail, and a tail past 10000 that is counted and validated"),
    "B23": (1, "A13 order preserved not fixed: the exact lexicographic p.id page at two projection limits"),
    "B24": (2, "Y14 scalar inventory: nullable versus non null fields, real ledger malformed JSON, middle and last"),
    # --- section 6, publication ---------------------------------------------
    "B25": (1, "prose alone teaches ReviewResult and the removal of request identity from proposal reads"),
    "B26": (1, "A15 prose outside code fences names four fields, three statuses, reject nulls, request free scope"),
    "B27": (1, "no public surface retains the unqualified form of a claim the contract qualified"),
    # --- sections 14 and 15, obligations added after the forks were ruled ----
    "B28": (2, "X32 past the 10000 row detail cap a MISSING BINDING raises at any limit, while malformed JSON raises only once the cap reaches it"),
    "B29": (2, "an absent proposal is NotFoundError and an absent or mismatched binding is IntegrityError"),
    "B30": (2, "the six owned event payloads are request free and the handle route payload is unchanged"),
    "B31": (1, "the exact CLI triples: exit 0 and the exact sorted key set and values for all three decisions"),
    "B32": (1, "the schema freeze: SCHEMA_VERSION 2, 14580 bytes, sha256 5be3d79f, equal to SCHEMA_FINGERPRINT"),
    "B33": (1, "A02 Literal is not runtime enforced, so accept correct and reject are called and their values asserted"),
    "B34": (2, "the complete statements LEFT JOIN and the row validator refuses the NULL binding, so an orphan fails closed on all five paths and an absent proposal still answers NotFoundError"),
    "B35": (2, "Y11 statement cardinality: one statement per adapter call over the whole channel, per path"),
    "B36": (2, "Y16 one transaction and adapter connection identity per path, with review sharing one write lock"),
    "B37": (1, "Y21 one stale fixture crossed with all three decisions: accept and correct raise, reject completes"),
    "B38": (1, "Y8 the committed mutation catalogue, its liveness proofs, its control and its verdict modules"),
}

STUB_HEADER = '''"""Diff-blind obligation battery for M3.4 request-free proposal seams.

One test per numbered obligation of ``.agent/decisions/m3u4-contract.md``, named
``test_<id>_<slug>``. Coverage is graded by
``uv run python .agent/decisions/m3u4-battery-validate.py``.

Sections 14 and 15 of that contract AMEND the numbered obligations and govern where
they disagree, so every test encodes the ruled form. Each test states its obligation
in its own docstring, including how the assertion reproduces it, because a finding is
graded by whether its reproduction is stated and never by whether its number differs.
"""

from __future__ import annotations

import unittest


class ProposalBindingBatteryTests(unittest.TestCase):
    """Contract-derived pins. The author reads the contract, never the diff."""
'''


def _fail(message: str) -> None:
    print(f"INVALID: {message}")


def _slug(subject: str) -> str:
    words = re.findall(r"[a-z0-9]+", subject.lower())
    return "_".join(words[:6])


def emit_stub() -> int:
    """Write the seed: every required test present, every body UNFILLED."""
    parts = [STUB_HEADER]
    for identifier, (count, subject) in OBLIGATIONS.items():
        for index in range(count):
            suffix = "" if count == 1 else f"_{index + 1}"
            name = f"test_{identifier.lower()}_{_slug(subject)}{suffix}"
            parts.append(
                f"\n    def {name}(self) -> None:\n"
                f'        """{identifier}. {subject}\n\n'
                f"        Reproduction: state here how this test reproduces the obligation.\n"
                f'        """\n'
                f'        self.fail("{UNFILLED}: {identifier}")\n'
            )
    parts.append('\n\nif __name__ == "__main__":  # pragma: no cover\n    unittest.main()\n')
    BATTERY.parent.mkdir(parents=True, exist_ok=True)
    BATTERY.write_text("".join(parts), encoding="utf-8")
    print(f"WROTE: {BATTERY.relative_to(ROOT)}")
    return 0


def _is_unfilled(node: ast.FunctionDef) -> bool:
    for statement in ast.walk(node):
        if isinstance(statement, ast.Constant) and isinstance(statement.value, str):
            if statement.value.startswith(f"{UNFILLED}:"):
                return True
    return False


def grade() -> int:
    if not BATTERY.exists():
        _fail(f"{BATTERY.relative_to(ROOT)} is missing; run --emit-stub first")
        return 2
    try:
        tree = ast.parse(BATTERY.read_text(encoding="utf-8"))
    except SyntaxError as error:
        _fail(f"{BATTERY.relative_to(ROOT)} does not parse: {error}")
        return 2

    found: dict[str, list[str]] = {identifier: [] for identifier in OBLIGATIONS}
    unfilled: list[str] = []
    undocumented: list[str] = []
    unknown: list[str] = []
    skipped: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
            continue
        for decorator in node.decorator_list:
            if "skip" in ast.dump(decorator):
                skipped.append(node.name)
        match = TEST_NAME.match(node.name)
        if match is None:
            unknown.append(f"{node.name} (name does not match test_<id>_<slug>)")
            continue
        identifier = match.group("id").upper()
        if identifier not in OBLIGATIONS:
            unknown.append(f"{node.name} (no obligation {identifier} in the contract)")
            continue
        found[identifier].append(node.name)
        if _is_unfilled(node):
            unfilled.append(node.name)
            continue
        docstring = ast.get_docstring(node) or ""
        if not docstring.startswith(f"{identifier}.") or len(docstring) < DOCSTRING_MIN:
            undocumented.append(node.name)

    filled_count = {
        identifier: len(names) - sum(1 for name in names if name in unfilled)
        for identifier, names in found.items()
    }
    uncovered = {
        identifier: (filled_count[identifier], OBLIGATIONS[identifier][0])
        for identifier in found
        if filled_count[identifier] < OBLIGATIONS[identifier][0]
    }

    for identifier, (have, need) in sorted(uncovered.items()):
        print(f"UNCOVERED: {identifier} has {have} filled test(s), needs {need}")
    for name in sorted(unknown):
        _fail(f"unknown obligation: {name}")
    for name in sorted(undocumented):
        _fail(f"docstring must open with the obligation id and state its reproduction: {name}")
    for name in sorted(skipped):
        _fail(f"skip decorator on {name}; a skipped test increments the count and still prints OK")

    total = sum(len(names) for names in found.values())
    print(f"OBLIGATIONS: {len(OBLIGATIONS)}")
    print(f"REQUIRED-TESTS: {sum(count for count, _ in OBLIGATIONS.values())}")
    print(f"TESTS: {total}")
    print(f"UNFILLED-TESTS: {len(unfilled)}")
    print(f"OBLIGATIONS-UNCOVERED: {len(uncovered)}")
    ok = not (uncovered or unknown or undocumented or skipped or unfilled)
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-stub", action="store_true", help="write the all-UNFILLED seed")
    args = parser.parse_args(argv)
    return emit_stub() if args.emit_stub else grade()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
