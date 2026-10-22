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

import pathlib
import re

from wave_validate import ContractTables

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
    unit='M3.5b',
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
