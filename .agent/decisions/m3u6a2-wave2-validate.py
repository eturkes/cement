#!/usr/bin/env python
"""Grade M3.6a2 wave-2 tables: the diff-blind phase-1 verdict table and the contract attack.

Usage:
    uv run python .agent/decisions/m3u6a2-wave2-validate.py --emit-stub verdicts > <path>
    uv run python .agent/decisions/m3u6a2-wave2-validate.py <path>

Exit 0 = PASS. Exit 1 = findings printed, one per line.

Graded both ways at seed: the emitted stub scores nonzero (every cell `unknown`), a filled table
scores zero. MAIN-owned columns are EXEMPT and PRINTED, because a teammate's completeness and
MAIN's ruling are two different deliverables, and a clean grade over an exempt column certifies
nothing.

Seeded rows are a FLOOR. Seeding the deliverable is necessary but not sufficient - seeding the row
SUBJECTS is what makes a generative deliverable resumable, and extension rows have outnumbered
seeded ones in every M3 wave, so `X`/`Y` ids are first-class and never scope drift.

Citations are graded by WHOLE-TOKEN membership in the contract, never containment: `L01` sits
inside `L010`, and containment certifies a dropped token.
"""

from __future__ import annotations

import pathlib
import re

from wave_validate import ContractTables

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".agent" / "decisions" / "m3u6a2-contract.md"

UNKNOWN = "unknown"
EXEMPT = {"verdicts": ("main_verdict", "action"), "attack": ("disposition", "main_note")}

VERDICT_SEED: tuple[tuple[str, str, str], ...] = (
    ("V01", "L01", "`System` has no `handle`: which access routes the predicate must close - hasattr, dir(), getattr, inspect.getmembers, a class-level __getattr__ - and what `no def handle` means for a nested or renamed definition"),
    ("V02", "L03", "the three private names as ATTRIBUTES versus as DEFINITIONS: can one survive as a module-level function, a closure, or a name bound in the class body without being a method"),
    ("V03", "L04", "`System(db, generation_lease_seconds=1)` raises TypeError: the exact exception class and message text CPython emits for an unexpected keyword on this signature"),
    ("V04", "L04", "after the knob leaves, are `candidate_source` and `clock_us` required or defaulted, and does an `inspect.signature` pin observe requiredness as well as name and kind"),
    ("V05", "L05", "`zero occurrences under src/`: occurrences of WHAT - the token as a word, as a substring, inside comments and docstrings - and which file set `src/` denotes"),
    ("V06", "L06", "the ACCEPTED side of the new boundary: a clock returning `_MAX_SQLITE_INTEGER` must reach a real write, so name the public entry point and the observable proving the timestamp was stored"),
    ("V07", "L06", "the REJECTED side: `_MAX_SQLITE_INTEGER + 1` raises StateError, and the exact message once `lease-safe` leaves it"),
    ("V08", "L06", "the widened band itself: a clock inside `(_MAX_SQLITE_INTEGER - lease_us, _MAX_SQLITE_INTEGER]` is rejected at `da70a56` and accepted at HEAD - the one ruled behaviour change, and the probe that exhibits both sides"),
    ("V09", "L07", "a `generating` request row at the previous revision must exist for L07's probe, but `handle` was its only producer: enumerate every route to that row after the deletion and say which the probe uses"),
    ("V10", "L07", "`its source contains no UPDATE requests`: which spellings a source predicate must reject - case, whitespace, the statement split across lines, the table quoted or schema-qualified"),
    ("V11", "L08", "the `operation.revised` payload read back: through which surface, with which value types, and what the three keys carry after the fourth is gone"),
    ("V12", "L09", "`handle` as a word under `src/`: enumerate the legitimate surviving uses the count must tolerate or exclude, and say whether the predicate is over tokens or lines"),
    ("V13", "L10", "the parsed `.models` import list loses exactly seven names: `Outcome` is an alias, so state what the parsed list contains and what `no other import moves` forbids"),
    ("V14", "L11", "deriving the sixteen-kind set over all three `kind=` spellings, including resolving the f-string's interpolation through its `Literal` annotation"),
    ("V15", "L11", "`artifact.ambiguity_quarantined` loses its only producer: what happens to the surviving assertion at `tests/test_system.py:2709` and to any prose that promises the behaviour"),
    ("V16", "L12", "byte identity of `models.py` and an unchanged `__all__`: against which git object, and how `__all__` is compared - parsed list or source text"),
    ("V17", "L13", "seven surviving `requests` sites in three MODULE-LEVEL functions: the counting convention (lines or occurrences) and what a class-body-only scan reports instead"),
    ("V18", "L14", "`SCHEMA_VERSION` stays 2 and `store.py` is byte-identical: what the pin reads, and whether an import-time constant or the file bytes is the subject"),
    ("V19", "L15", "the five preserved spans under the whole-line convention: what `trailing newlines stripped` means exactly, and whether a span whose line NUMBERS move still compares equal"),
    ("V20", "L16", "the proposal round trip ending `resolved`: the store read path, and the exact `output_json` and `example_id` values the probe asserts"),
    ("V21", "L17", "`revise_operation` still retires draft, verified AND promoted artifacts at the previous revision: one probe per status, with `status_reason` asserted"),
    ("V22", "L18", "`_now`'s four rejections after the bound changes: exact class and message for a non-int, a bool, a negative value and a non-callable `clock_us`"),
    ("V23", "L19", "what a `poll-state table` IS mechanically, so a test can decide its absence, and what `names neither handle nor request_status` means for prose that names them inside a code fence"),
    ("V24", "L20", "how a test identifies `steps 1-3` and `the lease paragraph` in `docs/architecture.md` without freezing the whole document"),
    ("V25", "L21", "`names no deleted surface` for `docs/adapter-protocol.md`: the exact token set, given M3.7 relocates this file under byte equality"),
    ("V26", "L22", "the threat-model's two claims: what replaces the `handle` request ID as an idempotency key and lease recovery, and how `describes surviving behaviour` is decided"),
    ("V27", "L24", "which census tokens must reach zero and which legitimately survive - `requests` still names the private table, `lease` may survive in unrelated prose"),
    ("V28", "L25", "a closed-range pin still has to be able to FAIL: what makes `36f7890..1146421` a live assertion rather than a constant"),
    ("V29", "L26", "retirement versus inversion: what a retired P06 freeze leaves that is still checkable, and what stops the inverted D01 from asserting a tautology"),
    ("V30", "L29", "widening `_freezes()` behind a control that FIRES on a P06 frame, when L26 retires those very frames in the same unit"),
)

ATTACK_SEED: tuple[tuple[str, str, str], ...] = (
    ("A01", "L01", "`system.py contains no def handle` is a text predicate: renaming satisfies it while the method ships - what structural pin forces the behaviour gone rather than the spelling"),
    ("A02", "L04", "signature exactness against a `**kwargs` tail: does the pin fail when a catch-all silently swallows `generation_lease_seconds` instead of raising"),
    ("A03", "L05", "token-absence cannot prove structural deletion - name a conforming tree where every occurrence count is zero and the behaviour survives"),
    ("A04", "L06", "the widened clock band is ruled safe because no lease deadline is computed anywhere: audit that claim against every surviving consumer that derives a value from `_now`"),
    ("A05", "L07", "L07's `generating` row probe may be reachable by no supported route once `handle` is gone; a fabricated row is legitimate evidence only if labelled - is it"),
    ("A06", "L08", "a three-key SET assertion passes while every value is wrong, and the payload may be read from the event row or from a return value - which does the obligation bind"),
    ("A07", "L09", "the CLOSED call-graph component claim: what makes closure checkable by counting, and does the count survive a dynamic reach (getattr, a registry, a string dispatch)"),
    ("A08", "L10", "`no other import moves` - does the predicate see an import ADDED as well as removed, and does it see a re-export path change in `__init__.py`"),
    ("A09", "L11", "the sixteen-kind derivation enumerates three spellings measured today: what happens when a fourth lands, and is the rule extensible or silently under-reporting again"),
    ("A10", "L11", "`artifact.ambiguity_quarantined` losing its producer is a public behaviour change with no obligation of its own - compare with section 2.1, which gave the clock widening one"),
    ("A11", "L12", "L12 freezes `models.py` while seven models lose their producers: the gate then certifies dead exported code as correct - state what that pin is actually protecting"),
    ("A12", "L13", "count plus owner names: what does the pin report when a surviving site MOVES into a new helper that did not exist at `da70a56`"),
    ("A13", "L15", "the whole-line span convention with line numbers moving: name a reformatting that preserves the compared bytes while changing the method, or prove none exists"),
    ("A14", "L16", "the round trip proves `_write_proposal_request_status` untouched only if the probe actually exercises it - name the branch and what happens on the other one"),
    ("A15", "L18", "`every surviving caller of _now is unchanged` - decided how, against which base object, and does it hold when a caller's line numbers move"),
    ("A16", "L19", "the four prose obligations are judgment predicates: which of L19-L22 can a test decide mechanically and which need a ruling recorded instead of an assertion"),
    ("A17", "L23", "`all 16 census pins green after the rewrite` is satisfiable by editing the pins - what stops the rewrite from repairing the instrument instead of the prose"),
    ("A18", "L24", "the owned-hit-count-zero predicate cannot hold for every vocabulary token, since `requests` names a surviving private table - state the token subset it actually binds"),
    ("A19", "L26", "retirement removes the only pin and records the frozen figures as PROSE - name what re-checks those figures, or concede the claim is unchecked after retirement"),
    ("A20", "L27", "an inverted D01 asserts the absence L01 and L02 already assert: is it now a duplicate rather than a pin, and does that matter"),
    ("A21", "L29", "widening `_freezes()` to see the P06 family while L26 RETIRES that family in the same unit: after both land the detector's target set is empty, so state what the control fires on"),
    ("A22", "G3", "gate 3's expectation is re-emitted by the same script that grades it, so `--emit` blesses whatever the tree currently says - name what stops a wrong post-state from grading PASS"),
    ("A23", "G8", "the reversion sweep needs one row per SUBPROPERTY and grounded exclusions: which of this unit's clauses are insensitive to every working-tree mutation, and why"),
    ("A24", "S6", "the gate list is fixed before implementation, yet gate 3's INSTRUMENT was repaired at S3 - argue whether that is an added gate under this contract's own rule"),
)

CITATION = re.compile(r"^(L\d{2}|G\d|C\d{2}|S\d{1,2})$")
# `\d{2,}` rejected 14 rows whose observable is a single-digit count (`prints exactly 7 hit
# lines`), a boolean, an empty collection or an exception class — all checkable. A grader whose
# strict branch is guarded by recognition fails on exactly the members nobody enumerated, so the
# admitted vocabulary is widened and the vague-prose seed in --self-test holds the floor.
CONCRETE = re.compile(
    r"(exit \d|\"[^\"]{2,}\"|'[^']{2,}'|\{[^}]*\}|\b\d+\b|`[^`]+`|\b(?:True|False|None)\b"
    r"|\[\]|\b[A-Z][A-Za-z]*(?:Error|Exception)\b)"
)
SEVERITY = ("blocking", "material", "minor", "cleared")
ROW_ID = {"verdicts": re.compile(r"^(V\d{2}|X\d{2})$"), "attack": re.compile(r"^(A\d{2}|Y\d{2})$")}
FIELDS = {
    "verdicts": ("id", "section", "locus", "probe", "reading", "baseline", "expected", "divergent"),
    "attack": ("id", "section", "lens", "attack", "evidence", "severity"),
}
MIN_PROSE = {
    "locus": 20, "probe": 12, "reading": 25, "baseline": 8, "expected": 12,
    "lens": 20, "attack": 30, "evidence": 12,
}


SEED_NOTE = "Seeded rows are a FLOOR, never a cap. Add extension rows with ids {extensions} for any locus the seed missed; extensions have outnumbered seeds in every M3 wave. A cleared claim is a FILLED cell: write 'no defensible alternative: <reason>' rather than leaving unknown."

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
    unit='M3.6a2',
    gate_section=6,
    has_self_test=True,
    documentation=__doc__,
    source_path=__file__,
    seed_note=SEED_NOTE
)
_contract_text = ENGINE._contract_text
contract_tokens = ENGINE.contract_tokens
contract_sections = ENGINE.contract_sections
contract_gates = ENGINE.contract_gates
emit_stub = ENGINE.emit_stub
grade = ENGINE.grade
self_test = ENGINE.self_test
main = ENGINE.main

if __name__ == "__main__":
    raise SystemExit(main())
