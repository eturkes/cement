#!/usr/bin/env python
"""Grade M3.5a wave-2 tables: the diff-blind verdict table and the contract attack.

Usage:
    uv run python .agent/decisions/m3u5a-wave2-validate.py --emit-stub verdicts > <path>
    uv run python .agent/decisions/m3u5a-wave2-validate.py <path>

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
CONTRACT = ROOT / ".agent" / "decisions" / "m3u5a-contract.md"

UNKNOWN = "unknown"
EXEMPT = {"verdicts": ("main_verdict", "action"), "attack": ("disposition", "main_note")}

# Seeded row SUBJECTS. Seeding the deliverable is necessary; seeding the row
# SUBJECTS is what makes a generative deliverable resumable after any death.
VERDICT_SEED: tuple[tuple[str, str, str], ...] = (
    ("V01", "D01", "resolve grammar: one positional plus required --input plus optional --expected-function-hash"),
    ("V02", "D01", "resolve rejects every option prefix (--in, --exp, --inp) under allow_abbrev=False"),
    ("V03", "D02", "resolve --input - at DEFAULT_MAX_BYTES and at DEFAULT_MAX_BYTES + 1"),
    ("V04", "D02", "resolve --input malformed JSON: which of _input's three families answers"),
    ("V05", "D03", "a configured candidate source is never called by either new leaf"),
    ("V06", "D04", "--db and --partition gate order and exact text on the resolve path"),
    ("V07", "D05", "--expected-function-hash mismatch and malformed digest: library-owned verdict and class"),
    ("V08", "D06", "resolve writes no ledger byte, no event, no clock read, no id allocation"),
    ("V09", "D07", "the payload key set is exactly seven keys and identical in all three states"),
    ("V10", "D08", "checks projects the ordered [{key, passed, detail}] vector on success too"),
    ("V11", "D09", "verified miss is matched false; failed verdict is matched null; the two never collapse"),
    ("V12", "D09", "output and artifact_hash null-ness tracks match is None exactly"),
    ("V13", "D10", "status 0 iff matched is true else 6, with both negative states on stdout"),
    ("V14", "D11", "no FunctionDocument field reaches stdout on any resolve branch"),
    ("V15", "D12", "unregistered operation is 3; empty promoted set and retired-artifact revision are 6"),
    ("V16", "D13", "an absent --db path answers integrity at 5 and leaves the path absent"),
    ("V17", "D13", "the absent-ledger check precedes --input parsing, so a malformed input creates no ledger"),
    ("V18", "D14", "proposal submit grammar: --sub is unrecognized and `proposal sub` is an invalid choice"),
    ("V19", "D15", "--submission - read failure, oversize and invalid UTF-8 answer three distinct messages"),
    ("V20", "D16", "the aggregate cap accepts 2162722 bytes and rejects 2162723"),
    ("V21", "D17", "a duplicate envelope key fails inside the parser, before any exact-key check"),
    ("V22", "D18", "unknown keys and missing keys each name every offending key, sorted"),
    ("V23", "D19", "a non-mapping provenance answers the library's own message at exit 2"),
    ("V24", "D20", "success emits exactly one key, proposal_id, and never the bare returned string"),
    ("V25", "D22", "an unregistered operation on submit is 3 and writes zero rows"),
    ("V26", "D23", "two byte-identical submissions return two ids and write two of each row"),
    ("V27", "D25", "the parser census moves 28 to 30 leaves and 35 to 37 nodes, derived from _parser()"),
    ("V28", "D26", "cross-leaf option isolation holds in both directions for both new options"),
)

ATTACK_SEED: tuple[tuple[str, str, str], ...] = (
    ("A01", "D09", "the biconditional: construct a value making matched null while passed is true, or prove the domain closes it"),
    ("A02", "D07", "how a conforming-looking key-set pin satisfies D07's letter without forcing all seven keys"),
    ("A03", "D13", "the pre-construction check's residual race: is the stated honesty complete or does it overclaim"),
    ("A04", "D16", "re-derive 2162722 from 2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + framing"),
    ("A05", "D17", "does strict parsing really pre-empt the exact-key check on every reachable path"),
    ("A06", "D18", "provenance defaulting to {} is called a durable empty mapping: verify durability, not acceptance"),
    ("A07", "D20", "every successful submission is pending by construction: attack the premise, not the key"),
    ("A08", "D23", "no message or doc sentence may advise retry: state the mechanical test that could fail"),
    ("A09", "D24", "how a zero-source-call pin satisfies its letter without forcing the isolation"),
    ("A10", "D25", "can the census-derived test pass while abbreviation behaviour elsewhere silently changed"),
    ("A11", "D26", "is store.py byte-identity derived or transcribed, and against which object"),
    ("A12", "D27", "do D24, D25 and D26 really carry every property B02 retired, or is one lost"),
    ("A13", "D30", "is the cost figure derived from the artifact at its stated precision or transcribed"),
    ("A14", "D10", "does putting a negative resolve verdict on stdout disturb function export's stderr channel"),
    ("A15", "D06", "one read transaction per invocation: name an instrument that can actually observe it"),
    ("A16", "S1", "preservation plus no new source reach: does any obligation assert preservation mechanically"),
    ("A17", "D12", "the exit map is called unchanged and untouched: verify against main rather than assert"),
    ("A18", "D28", "positive publication: what would make the grep test pass while a reader still cannot learn the grammar"),
    ("A19", "D29", "every placeholder in a new command block has a producing command earlier in that block"),
    ("A20", "S12", "project CLAUDE.md conformance on every durable file this unit touches, and whether each deferral carries a real acceptance check"),
)

CITATION = re.compile(r"^(D\d{2}|D-[A-C]|G\d|[XYZM]\d{2}|S\d{1,2})$")
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
        "unit": "M3.5a",
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
    parser = argparse.ArgumentParser(description="grade an M3.5a wave-2 table")
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
