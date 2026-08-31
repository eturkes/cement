#!/usr/bin/env python
"""Grade M3.5b wave-2 tables: the diff-blind verdict table and the contract attack.

Usage:
    uv run python .agent/decisions/m3u5b-wave2-validate.py --emit-stub verdicts > <path>
    uv run python .agent/decisions/m3u5b-wave2-validate.py <path>

Exit 0 = PASS. Exit 1 = findings printed, one per line.

Graded both ways at seed: the emitted stub scores nonzero (every cell `unknown`),
a filled table scores zero. MAIN-owned columns are EXEMPT and PRINTED, because a
teammate's completeness and MAIN's ruling are two different deliverables and a
clean grade over an exempt column certifies nothing (M3.2b measured this).

Citations are graded by WHOLE-TOKEN membership in the contract, never containment:
`24` sits inside `243` and `D01` inside `D010`, so containment certifies a dropped
token (M3.4 measured this).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".agent" / "decisions" / "m3u5b-contract.md"

UNKNOWN = "unknown"
EXEMPT = {"verdicts": ("main_verdict", "action"), "attack": ("disposition", "main_note")}

# Seeded row SUBJECTS. Seeding the deliverable is necessary; seeding the row
# SUBJECTS is what makes a generative deliverable resumable after any death.
VERDICT_SEED: tuple[tuple[str, str, str], ...] = (
    ("V01", "D07", "cement handle op --input {} exits 2 through the _UsageError channel, not through a dispatch branch"),
    ("V02", "D07", "cement request r1 exits 2 with an invalid-choice message naming command as the offending argument"),
    ("V03", "D05", "the invalid-choice message enumerates the surviving root commands, so it is a complement assertion"),
    ("V04", "D08", "cli.py defines no _source symbol, decided over the shipped module AST rather than a text grep"),
    ("V05", "D08", "cli.py imports no name from .source, decided over the module's import nodes"),
    ("V06", "D09", "no args.command == handle and no args.command == request dispatch branch survives in _run"),
    ("V07", "D09", "System is constructed with no candidate_source argument on every reachable CLI path"),
    ("V08", "D10", "--request-id offered to every surviving leaf: which refuse, with which exact message and exit"),
    ("V09", "D10", "--source-command, --source-id, --source-timeout and --retry-failed refused by every surviving leaf"),
    ("V10", "D06", "every proper prefix of every removed flag, and which prefixes a surviving flag legitimately claims"),
    ("V11", "D11", "help text at EVERY parser node names no handle, request, request id, retry or candidate source"),
    ("V12", "D12", "the surviving leaf-name SET equals the HEAD set minus handle and request, as set equality"),
    ("V13", "D02", "a count-only census cannot separate both units landed from neither landed: exhibit the collision"),
    ("V14", "D13", "the twelve surviving root commands by name, derived from _parser() rather than transcribed"),
    ("V15", "D14", "every surviving leaf keeps options, defaults, choices, types and help byte-identical"),
    ("V16", "D14", "the parser_shape digest re-derives to 151 actions and ebd2ac811bd9776d after the removal"),
    ("V17", "D15", "byte equality of the six preserved modules and every examples/ file, asserted against git objects"),
    ("V18", "D16", "proposal submit, show, list, review and resolve keep their M3.5a exit classes and payload key sets"),
    ("V19", "D17", "gate 4's five re-based checks, with BASELINE_LEAVES retained and the expectation moved"),
    ("V20", "D18", "the three fixture helpers seed through proposal submit and the 103 shielded assertions stay unchanged"),
    ("V21", "D19", "x26 inverted: CommandCandidateSource is no longer imported by cli.py"),
    ("V22", "D19", "d24 re-shaped: a mock.patch.object spy on a deleted symbol raises rather than returning a verdict"),
    ("V23", "D20", "B02's docstring records the 30 to 28 removal instead of the 28 to 30 migration"),
    ("V24", "D21", "the battery's independent parser_shape oracle is re-derived and the duplication stays deliberate"),
    ("V25", "D22", "README quick start reaches a proposal through proposal submit and names no removed command"),
    ("V26", "D22", "library-route prose naming System.handle survives byte-identical: deleting it is a defect here"),
    ("V27", "D23", "every cement invocation in README, docs/*.md and examples/*/README.md parses under _parser()"),
    ("V28", "D24", "each placeholder a shipped command block consumes has a producing command earlier in that block"),
    ("V29", "D26", "root help describes deterministic resolution plus supervised proposal capture and no lifecycle"),
    ("V30", "D01", "System.handle and System.request_status stay public with no operator route, unstated in shipped prose"),
)

ATTACK_SEED: tuple[tuple[str, str, str], ...] = (
    ("A01", "D02", "the census collision: can a conforming pin satisfy D02's letter while still counting rather than asserting the set"),
    ("A02", "D05", "invalid-choice enumeration called a complement for free: what makes it a property rather than argparse's wording"),
    ("A03", "D10", "every proper prefix that is not a prefix of a surviving flag: is that set well defined and non-empty per leaf"),
    ("A04", "D08", "AST over text grep: how would a conforming AST pin pass while the property fails"),
    ("A05", "D06", "abbreviation reaches across leaves in both directions: can a removed spelling stay reachable somewhere"),
    ("A06", "D11", "walk EVERY node: name the surface each node renders and where a ban scans a string that cannot hold the text"),
    ("A07", "D14", "carried by the digest: does parser_shape observe defaults, choices, types, help and container-level attributes"),
    ("A08", "D15", "byte equality against git objects: which object, and does a scope breach fail rather than pass silently"),
    ("A09", "D17", "BASELINE_LEAVES retained while the expectation moves: what does the frozenset now prove"),
    ("A10", "D18", "the fixture re-base: does proposal submit produce the state the 103 shielded assertions require"),
    ("A11", "D19", "an inverted pin: what stops the inversion from asserting a tautology after the symbol is gone"),
    ("A12", "D20", "a docstring corrected but ungraded: what fails the next time it goes stale"),
    ("A13", "D22", "the prose split by route: is any locus mis-assigned, and is the mixed row's re-scoping complete"),
    ("A14", "D23", "mechanical extraction of cement invocations from prose: which invocation shapes does the extractor miss"),
    ("A15", "D26", "root help positive claim: what makes the test pass while a reader still cannot learn what exists"),
    ("A16", "D27", "do the replacements really carry every property the three superseded M3.5a obligations held"),
    ("A17", "D29", "must fail when one obligation remains undone: name an obligation whose undoing the battery cannot see"),
    ("A18", "D03", "the work list is stated as eleven frames, tabled as eighteen rows and measured as seventeen"),
    ("A19", "S1", "the not-owned table: name an edit this unit must make that touches a not-owned surface"),
    ("A20", "D04", "the anchored EDITS table re-run at implementation time: what happens when an anchor has moved"),
    ("A21", "D25", "register conformance on rewritten prose: which tool grades it and is the claim re-derivable from a clone"),
    ("A22", "S8", "gate 3 over every touched predicate: what IS the predicate set when the change is a deletion"),
    ("A23", "S9", "project CLAUDE.md conformance on every durable file this unit touches, code and prose alike"),
)

CITATION = re.compile(r"^(D\d{2}|G\d|[XYZM]\d{2}|S\d{1,2})$")
CONCRETE = re.compile(r"(exit \d|\"[^\"]{2,}\"|'[^']{2,}'|\{[^}]*\}|\b\d{2,}\b|`[^`]+`)")
SEVERITY = ("blocking", "material", "minor", "cleared")
ROW_ID = {"verdicts": re.compile(r"^(V\d{2}|X\d{2})$"), "attack": re.compile(r"^(A\d{2}|Y\d{2})$")}
FIELDS = {
    "verdicts": ("id", "section", "locus", "probe", "reading", "baseline", "expected", "divergent"),
    "attack": ("id", "section", "lens", "attack", "evidence", "severity"),
}
MIN_PROSE = {"locus": 20, "probe": 12, "reading": 25, "baseline": 8, "expected": 12, "lens": 20, "attack": 30, "evidence": 12}


def contract_tokens() -> set[str]:
    text = CONTRACT.read_text(encoding="utf-8")
    return set(re.findall(r"[A-Za-z0-9_-]+", text))


def contract_sections() -> set[str]:
    text = CONTRACT.read_text(encoding="utf-8")
    return set(re.findall(r"^## (\d{1,2})\.", text, flags=re.MULTILINE))


def emit_stub(kind: str) -> str:
    seed = VERDICT_SEED if kind == "verdicts" else ATTACK_SEED
    rows = []
    for identifier, section, subject in seed:
        if kind == "verdicts":
            rows.append(
                {
                    "id": identifier,
                    "section": section,
                    "locus": subject,
                    "probe": UNKNOWN,
                    "reading": UNKNOWN,
                    "baseline": UNKNOWN,
                    "expected": UNKNOWN,
                    "divergent": UNKNOWN,
                    "main_verdict": None,
                    "action": None,
                }
            )
        else:
            rows.append(
                {
                    "id": identifier,
                    "section": section,
                    "lens": subject,
                    "attack": UNKNOWN,
                    "evidence": UNKNOWN,
                    "severity": UNKNOWN,
                    "disposition": None,
                    "main_note": None,
                }
            )
    document = {
        "kind": kind,
        "unit": "M3.5b",
        "note": (
            "Seeded rows are a FLOOR, never a cap. Add extension rows with ids "
            + ("X01, X02, ..." if kind == "verdicts" else "Y01, Y02, ...")
            + " for any locus the seed missed; extensions have outnumbered seeds in every"
            " M3 wave. A cleared claim is a filled cell: write"
            " 'no defensible alternative: <reason>' rather than leaving unknown."
        ),
        "rows": rows,
    }
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def grade(path: pathlib.Path) -> list[str]:
    findings: list[str] = []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"UNREADABLE: {exc}"]
    kind = document.get("kind")
    if kind not in FIELDS:
        return [f"BAD-KIND: {kind!r} is not verdicts or attack"]

    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        return ["NO-ROWS: rows must be a non-empty list"]

    tokens = contract_tokens()
    sections = contract_sections()
    seed = VERDICT_SEED if kind == "verdicts" else ATTACK_SEED
    seen: set[str] = set()
    unknown_cells = 0
    concrete_rows = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append(f"row {index}: not an object")
            continue
        identifier = str(row.get("id", ""))
        if not ROW_ID[kind].match(identifier):
            findings.append(f"row {index}: id {identifier!r} must match {ROW_ID[kind].pattern}")
            continue
        if identifier in seen:
            findings.append(f"{identifier}: duplicate id")
        seen.add(identifier)

        for field in FIELDS[kind]:
            if field not in row:
                findings.append(f"{identifier}: missing field {field}")
                continue
            value = row[field]
            if not isinstance(value, str) or not value.strip():
                findings.append(f"{identifier}.{field}: must be a non-empty string")
                continue
            if value.strip().lower() == UNKNOWN:
                unknown_cells += 1
                continue
            floor = MIN_PROSE.get(field)
            if floor is not None and len(value.strip()) < floor:
                findings.append(f"{identifier}.{field}: {len(value.strip())} chars, floor {floor}")

        citation = str(row.get("section", "")).strip()
        if citation and citation.lower() != UNKNOWN:
            for element in (part.strip() for part in citation.split(",")):
                head = element.split()[0] if element.split() else ""
                if not CITATION.match(head):
                    findings.append(f"{identifier}.section: {head!r} is not a citation form")
                elif head.startswith("S"):
                    if head[1:] not in sections:
                        findings.append(f"{identifier}.section: contract has no section {head[1:]}")
                elif head not in tokens:
                    findings.append(f"{identifier}.section: {head} resolves nowhere in the contract")

        if kind == "verdicts":
            divergent = str(row.get("divergent", "")).strip().lower()
            if divergent not in (UNKNOWN, "yes", "no"):
                findings.append(f"{identifier}.divergent: {divergent!r} must be yes or no")
            expected = str(row.get("expected", ""))
            if expected.strip().lower() != UNKNOWN and CONCRETE.search(expected):
                concrete_rows += 1
            elif expected.strip().lower() != UNKNOWN:
                findings.append(
                    f"{identifier}.expected: names no concrete observable"
                    " (exit code, quoted string, key set, or number)"
                )
        else:
            severity = str(row.get("severity", "")).strip().lower()
            if severity not in (UNKNOWN, *SEVERITY):
                findings.append(f"{identifier}.severity: {severity!r} must be one of {SEVERITY}")

    missing = [identifier for identifier, _, _ in seed if identifier not in seen]
    if missing:
        findings.append(f"SEED-ROWS-MISSING: {', '.join(missing)}")

    print(f"KIND: {kind}")
    print(f"ROWS: {len(rows)} ({len(seed)} seeded, {len(rows) - len(seed)} extension)")
    print(f"UNKNOWN-CELLS: {unknown_cells}")
    print(f"EXEMPT-COLUMNS (MAIN-owned, NOT graded): {', '.join(EXEMPT[kind])}")
    if kind == "verdicts":
        print(f"CONCRETE-EXPECTATIONS: {concrete_rows}")
    if unknown_cells:
        findings.append(f"UNFILLED: {unknown_cells} cells still read unknown")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="grade an M3.5b wave-2 table")
    parser.add_argument("path", nargs="?")
    parser.add_argument("--emit-stub", choices=("verdicts", "attack"))
    args = parser.parse_args(argv)
    if args.emit_stub:
        sys.stdout.write(emit_stub(args.emit_stub))
        return 0
    if not args.path:
        parser.error("a table path is required unless --emit-stub is given")
    findings = grade(pathlib.Path(args.path))
    for finding in findings:
        print(finding)
    print("PASS" if not findings else f"FAIL ({len(findings)} findings)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
