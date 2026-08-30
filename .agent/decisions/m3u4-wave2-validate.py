"""Structural validator for M3.4 wave-2 artifacts.

Usage:
    uv run python .agent/decisions/m3u4-wave2-validate.py <artifact.json>
    uv run python .agent/decisions/m3u4-wave2-validate.py --emit-seed verdicts
    uv run python .agent/decisions/m3u4-wave2-validate.py --emit-seed attack

The artifact's top-level ``kind`` selects the schema. Two kinds ship:

``verdicts``
    The diff-blind phase-1 divergence table. One row per LOCUS: a place where the
    acceptance contract admits more than one reading. The author states both readings
    and the outcome it expects; MAIN rules ``main_verdict`` afterwards.

``attack``
    The contract attack. One row per LENS: a claim in the contract, the attack that
    would falsify it, and the acceptance check that closes it. MAIN rules
    ``disposition`` afterwards.

Seeded ``id`` and ``locus`` values are MAIN-owned and may not be rewritten. Extension
rows are REQUIRED wherever the seed missed a real locus or lens: add ``X<n>`` rows to a
verdict table and ``Y<n>`` rows to an attack table. The seed is a floor, never a cap.

``main_verdict`` and ``disposition`` are MAIN-owned and exempt from the unfilled count.
The validator prints the exempt columns so a clean grade is never read as a closed table.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

UNKNOWN = "unknown"
PROSE_MIN = 40
SECTION = re.compile(r"(?:§|D|P|R)[0-9]{1,2}(?:[.\-][0-9A-Za-z]{1,3})?(?:,\s*\S+)*\Z")
VERDICT_EXTENSION = re.compile(r"X[0-9]{1,3}")
ATTACK_EXTENSION = re.compile(r"Y[0-9]{1,3}")

VERDICT_FIELDS = ("section", "locus", "reading_a", "reading_b", "divergent", "expected",
                  "test_name", "main_verdict")
ATTACK_FIELDS = ("section", "locus", "claim", "attack", "severity", "reproduction",
                 "acceptance_check", "disposition")
MAIN_OWNED = {"main_verdict", "disposition"}
SEVERITIES = {"blocking", "material", "minor", "cleared", UNKNOWN}

# One row per locus where the contract admits two readings. Work the named locus.
VERDICT_LOCI: dict[str, str] = {
    "V01": "ReviewResult on reject: whether example_id and output are emitted as null keys or omitted",
    "V02": "ReviewResult.status vocabulary: accepted/corrected/rejected against the baseline's resolved/rejected",
    "V03": "review's return on accept versus correct: which fields differ and which must be byte-identical",
    "V04": "ProposalView without request_id: whether every remaining field keeps its baseline value exactly",
    "V05": "PendingProposalGap without request_id: identity of a gap when two proposals share an input_hash",
    "V06": "the confinement complement set: which definitions may name requests immediately after M3.4",
    "V07": "whether a module-level SQL constant counts as a definition naming requests, and under whose name",
    "V08": "case folding and identifier tokenizing: FROM REQUESTS, requests_scope, and a quoted \"requests\"",
    "V09": "get_proposal's error precedence: missing row, wrong partition, non-pending status, broken request binding",
    "V10": "proposals feed ordering and the status filter under the adapter: exact rows for status=all",
    "V11": "function_report pending count versus detail projection past the projection limit",
    "V12": "function_report pending detail ORDER: what may be asserted about the page and what may not",
    "V13": "review's stale-revision refusal: which decisions it applies to and what it raises",
    "V14": "review's conflict quarantine: artifacts suspended, events emitted, and their payload keys",
    "V15": "the private request-status write on reject versus accept/correct: rowcount checks and failure class",
    "V16": "adapter use inside review's write transaction: statement count and connection.in_transaction",
    "V17": "a proposal whose private request row is missing or mismatched: class, message, and which paths see it",
    "V18": "partition and operation colliders through every adapted read: tenant_a beside tenantXa, case variants",
    "V19": "scalar corruption of the MIDDLE and the LAST of three proposals read through the adapter",
    "V20": "cross-partition and cross-operation proposals: invisibility in every adapted read path",
    "V21": "the CLI proposal show and list payload key sets once request_id leaves the record",
    "V22": "whether any surviving public value reachable from a proposal, read, review or report carries request identity",
}

# One row per lens attacking a claim the contract makes. Work the named lens.
ATTACK_LENSES: dict[str, str] = {
    "A01": "D12's no-other-projected-value rule applied to the ReviewResult ruling's own removals",
    "A02": "the ruled status change from resolved to accepted/corrected: every surface that still says resolved",
    "A03": "D01's exactly ONE named private surface against the shipped adapter's actual member count",
    "A04": "D02's complement assertion: how a conforming-looking instrument could pass while an access hides",
    "A05": "D06's fragment-composition prohibition against the shipped adapter's own parameter handling",
    "A06": "D11's single shape test: what a shape it does not enumerate would look like when it breaks",
    "A07": "D13's design-smell clause: whether _proposal_record or _proposal_content actually grew",
    "A08": "D15's exact row writes and their order under the adapter's writer helper",
    "A09": "D17's exactly-one-example claim against every path through review, including quarantine",
    "A10": "D19's event sequencing and status_sequence binding under a changed return type",
    "A11": "D21's = versus LIKE isolation: whether the shipped fixtures actually carry the colliders",
    "A12": "D22's bounded detail and reachable tail against the adapter's own LIMIT handling",
    "A13": "D23's preserved-not-fixed ordering: an assertion that passes twice and fails on the third run",
    "A14": "D24's fail-closed scalars: which probes are fabricated and whether any is cited as a real-ledger repro",
    "A15": "D25 and D26 publication: whether prose alone teaches ReviewResult and the lost request identity",
    "A16": "D27's unqualified-form sweep for every qualifier the S2 rulings introduce",
    "A17": "section 7's work-list measurement: whether the shipped diff stayed inside it and what moved",
    "A18": "the fork-1 ruling's Z50 grounds: whether the shipped adapter really survives the M3.6b swap untouched",
}


def _fail(message: str) -> None:
    print(f"INVALID: {message}")
    raise SystemExit(1)


def _rows(payload: dict, required: dict[str, str], extension: re.Pattern[str]) -> dict[str, dict]:
    raw = payload.get("rows")
    if not isinstance(raw, list):
        _fail("'rows' must be a list")
    seen: dict[str, dict] = {}
    for row in raw:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            _fail("every row must be an object with a string id")
        if row["id"] in seen:
            _fail(f"duplicate row id {row['id']!r}")
        seen[row["id"]] = row
    missing = [identifier for identifier in required if identifier not in seen]
    extra = [
        identifier
        for identifier in seen
        if identifier not in required and extension.fullmatch(identifier) is None
    ]
    if missing:
        _fail(f"missing row ids: {missing}")
    if extra:
        _fail(f"unexpected row ids (extensions must match {extension.pattern}): {extra}")
    return seen


def _common(identifier: str, row: dict, fields: tuple[str, ...], seeded: str | None) -> None:
    if set(row) != {"id", *fields}:
        _fail(f"{identifier} must carry exactly id plus {list(fields)}")
    if seeded is not None and row["locus"] != seeded:
        _fail(f"{identifier}.locus was rewritten; MAIN owns it, report the objection instead")
    if seeded is None and len(row["locus"]) < PROSE_MIN:
        _fail(f"{identifier}.locus is {len(row['locus'])} chars, under {PROSE_MIN}")
    section = row["section"]
    if not isinstance(section, str):
        _fail(f"{identifier}.section must be a string")
    if section != UNKNOWN and SECTION.fullmatch(section) is None:
        _fail(f"{identifier}.section {section!r} must cite contract ids, e.g. 'D12' or 'D07, D11'")


def _validate_verdicts(payload: dict) -> int:
    rows = _rows(payload, VERDICT_LOCI, VERDICT_EXTENSION)
    unknown = 0
    for identifier, row in sorted(rows.items()):
        _common(identifier, row, VERDICT_FIELDS, VERDICT_LOCI.get(identifier))
        divergent = row["divergent"]
        if divergent not in (True, False, UNKNOWN):
            _fail(f"{identifier}.divergent must be true, false or {UNKNOWN!r}")
        for field in ("section", "reading_a", "reading_b", "expected", "test_name", "main_verdict"):
            value = row[field]
            if not isinstance(value, str):
                _fail(f"{identifier}.{field} must be a string")
            if value == UNKNOWN:
                if field not in MAIN_OWNED:
                    unknown += 1
                continue
            if field in ("reading_a", "reading_b", "expected") and len(value) < PROSE_MIN:
                _fail(f"{identifier}.{field} is {len(value)} chars, under {PROSE_MIN}")
            if field == "test_name" and not value.startswith("test_"):
                _fail(f"{identifier}.test_name {value!r} must name the encoding test")
        if divergent == UNKNOWN:
            unknown += 1
        elif divergent is False and row["reading_b"] == row["reading_a"]:
            _fail(f"{identifier} is marked non-divergent but its two readings are identical text")
    return unknown


def _validate_attack(payload: dict) -> int:
    rows = _rows(payload, ATTACK_LENSES, ATTACK_EXTENSION)
    unknown = 0
    for identifier, row in sorted(rows.items()):
        _common(identifier, row, ATTACK_FIELDS, ATTACK_LENSES.get(identifier))
        if row["severity"] not in SEVERITIES:
            _fail(f"{identifier}.severity must be one of {sorted(SEVERITIES)}")
        for field in ("section", "claim", "attack", "severity", "reproduction",
                      "acceptance_check", "disposition"):
            value = row[field]
            if not isinstance(value, str):
                _fail(f"{identifier}.{field} must be a string")
            if value == UNKNOWN:
                if field not in MAIN_OWNED:
                    unknown += 1
                continue
            if field in ("claim", "attack", "reproduction", "acceptance_check"):
                if len(value) < PROSE_MIN:
                    _fail(f"{identifier}.{field} is {len(value)} chars, under {PROSE_MIN}")
    return unknown


def _seed(kind: str) -> dict:
    if kind == "verdicts":
        return {
            "kind": "verdicts",
            "rows": [
                {
                    "id": identifier,
                    "section": UNKNOWN,
                    "locus": locus,
                    "reading_a": UNKNOWN,
                    "reading_b": UNKNOWN,
                    "divergent": UNKNOWN,
                    "expected": UNKNOWN,
                    "test_name": UNKNOWN,
                    "main_verdict": UNKNOWN,
                }
                for identifier, locus in VERDICT_LOCI.items()
            ],
        }
    return {
        "kind": "attack",
        "rows": [
            {
                "id": identifier,
                "section": UNKNOWN,
                "locus": locus,
                "claim": UNKNOWN,
                "attack": UNKNOWN,
                "severity": UNKNOWN,
                "reproduction": UNKNOWN,
                "acceptance_check": UNKNOWN,
                "disposition": UNKNOWN,
            }
            for identifier, locus in ATTACK_LENSES.items()
        ],
    }


VALIDATORS = {"verdicts": _validate_verdicts, "attack": _validate_attack}
EXEMPT = {"verdicts": ["main_verdict"], "attack": ["disposition"]}


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--emit-seed" and argv[2] in VALIDATORS:
        print(json.dumps(_seed(argv[2]), indent=2))
        return 0
    if len(argv) != 2:
        print(__doc__)
        return 1
    path = Path(argv[1])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _fail(f"unreadable artifact: {exc}")
    if not isinstance(payload, dict):
        _fail("artifact must be a JSON object")
    kind = payload.get("kind")
    if kind not in VALIDATORS:
        _fail(f"kind={kind!r} is not one of {sorted(VALIDATORS)}")
    unknown = VALIDATORS[kind](payload)
    print(f"KIND: {kind}")
    print(f"ROWS: {len(payload['rows'])}")
    print(f"EXEMPT-COLUMNS: {EXEMPT[kind]} (MAIN-owned; a clean grade does NOT mean a closed table)")
    print(f"UNKNOWN-CELLS: {unknown}")
    if unknown:
        print("INCOMPLETE: fill every cell, then rerun this validator LAST")
        return 1
    print("VALID: structurally sound with zero unfilled cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
