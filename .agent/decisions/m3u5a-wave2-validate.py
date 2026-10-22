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

import pathlib
import re

from wave_validate import ContractTables

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


SEED_NOTE = "Seeded rows are a FLOOR, never a cap. Add extension rows with ids {extensions} for any locus the seed missed; extensions have outnumbered seeds in every M3 wave. A cleared claim is a filled cell: write 'no defensible alternative: <reason>' rather than leaving unknown."

ENGINE = ContractTables(
    ATTACK_SEED=ATTACK_SEED,
    CITATION=CITATION,
    CONCRETE=CONCRETE,
    CONTRACT=CONTRACT,
    EXEMPT=EXEMPT,
    FIELDS=FIELDS,
    MIN_PROSE=MIN_PROSE,
    ROW_ID=ROW_ID,
    SEVERITY=SEVERITY,
    UNKNOWN=UNKNOWN,
    VERDICT_SEED=VERDICT_SEED,
    unit='M3.5a',
    gate_section=None,
    has_self_test=False,
    documentation=__doc__,
    source_path=__file__,
    seed_note=SEED_NOTE
)
contract_tokens = ENGINE.contract_tokens
contract_sections = ENGINE.contract_sections
emit_stub = ENGINE.emit_stub
grade = ENGINE.grade
main = ENGINE.main

if __name__ == "__main__":
    raise SystemExit(main())
