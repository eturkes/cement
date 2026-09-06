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

import argparse
import json
import pathlib
import re
import sys

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
CONCRETE = re.compile(r"(exit \d|\"[^\"]{2,}\"|'[^']{2,}'|\{[^}]*\}|\b\d{2,}\b|`[^`]+`)")
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


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def contract_tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_-]+", text))


def contract_sections(text: str) -> set[str]:
    return set(re.findall(r"^## (\d{1,2})\.", text, flags=re.MULTILINE))


def contract_gates(text: str) -> set[str]:
    """Gate ids are the numbered list under section 6, so `G7` resolves only while gate 7 exists."""
    block = re.search(r"^## 6\..*?(?=^## \d)", text, flags=re.MULTILINE | re.DOTALL)
    return set(re.findall(r"^(\d+)\. ", block.group(0), flags=re.MULTILINE)) if block else set()


def emit_stub(kind: str) -> str:
    seed = VERDICT_SEED if kind == "verdicts" else ATTACK_SEED
    rows = []
    for identifier, section, subject in seed:
        if kind == "verdicts":
            rows.append({
                "id": identifier, "section": section, "locus": subject,
                "probe": UNKNOWN, "reading": UNKNOWN, "baseline": UNKNOWN,
                "expected": UNKNOWN, "divergent": UNKNOWN,
                "main_verdict": None, "action": None,
            })
        else:
            rows.append({
                "id": identifier, "section": section, "lens": subject,
                "attack": UNKNOWN, "evidence": UNKNOWN, "severity": UNKNOWN,
                "disposition": None, "main_note": None,
            })
    document = {
        "kind": kind,
        "unit": "M3.6a2",
        "note": (
            "Seeded rows are a FLOOR, never a cap. Add extension rows with ids "
            + ("X01, X02, ..." if kind == "verdicts" else "Y01, Y02, ...")
            + " for any locus the seed missed; extensions have outnumbered seeds in every M3 wave."
            " A cleared claim is a FILLED cell: write 'no defensible alternative: <reason>' rather"
            " than leaving unknown."
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

    text = _contract_text()
    tokens = contract_tokens(text)
    sections = contract_sections(text)
    gates = contract_gates(text)
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
                elif head.startswith("G"):
                    if head[1:] not in gates:
                        findings.append(f"{identifier}.section: contract has no gate {head[1:]}")
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


def self_test() -> int:
    """Grade the grader both ways on a temporary file: the stub FAILS, a filled copy PASSES."""
    import contextlib
    import io
    import tempfile

    silent: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        for kind in ("verdicts", "attack"):
            path = pathlib.Path(directory) / f"{kind}.json"
            path.write_text(emit_stub(kind), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                stub_findings = grade(path)
            if not any(f.startswith("UNFILLED") for f in stub_findings):
                silent.append(f"{kind}: the all-unknown stub did not report UNFILLED")

            document = json.loads(path.read_text(encoding="utf-8"))
            for row in document["rows"]:
                for field in FIELDS[kind]:
                    if row.get(field) == UNKNOWN:
                        row[field] = (
                            "exit 0 and the key set `{a, b}` filled to clear the floor of characters"
                            if field == "expected" else
                            "no" if field == "divergent" else
                            "cleared" if field == "severity" else
                            "filled placeholder text long enough to clear every prose floor here"
                        )
            path.write_text(json.dumps(document), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                filled_findings = grade(path)
            if filled_findings:
                silent.append(f"{kind}: a filled table reported {filled_findings}")

            broken = json.loads(path.read_text(encoding="utf-8"))
            broken["rows"][0]["section"] = "L99"
            path.write_text(json.dumps(broken), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                cited = grade(path)
            if not any("resolves nowhere" in f for f in cited):
                silent.append(f"{kind}: an unresolvable citation was accepted")

            dropped = json.loads(path.read_text(encoding="utf-8"))
            dropped["rows"] = dropped["rows"][1:]
            path.write_text(json.dumps(dropped), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                missing = grade(path)
            if not any(f.startswith("SEED-ROWS-MISSING") for f in missing):
                silent.append(f"{kind}: a dropped seed row was accepted")

    for line in silent:
        print(f"SILENT: {line}")
    print(f"CONTROLS: {8 - len(silent)}/8 firing")
    return 1 if silent else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="grade an M3.6a2 wave-2 table")
    parser.add_argument("path", nargs="?")
    parser.add_argument("--emit-stub", choices=("verdicts", "attack"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
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
