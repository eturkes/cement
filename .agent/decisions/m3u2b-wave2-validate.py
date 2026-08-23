#!/usr/bin/env python3
"""Structural validator for M3.2b wave-2 artifacts.

Usage: uv run python .agent/decisions/m3u2b-wave2-validate.py <artifact.json>

The artifact's top-level ``kind`` selects the schema:

  "divergences"  the diff-blind `test` author's phase-1 divergence table
  "attack"       the reviewer's pre-implementation contract attack
  "oracle"       observations over MAIN's probe corpus, one file per implementation

Exit 0 = structurally valid AND nothing left ``unknown`` outside a MAIN-owned
field. Exit 1 = structural defect or an unfilled cell.

Seeding contract: a first tool call that writes every required id with every
value ``unknown`` produces a STRUCTURALLY valid file that still exits 1, so
UNKNOWN-CELLS is the flush metric and each filled cell lowers it.

MAIN-owned fields (``main_verdict``, ``disposition``) are exempt from the
unknown count: the teammate never fills them.

Cancellation: MAIN alone may retire a padded row by writing ``cancelled`` into
every non-id field. Cancelled rows are counted and reported, never graded. A
teammate writing ``cancelled`` is a contract breach, not a pass.

The ``oracle`` corpus below is MAIN's single source of truth for the M3.2b
differential. Every implementation of the contract answers the same ids with the
same observation keys, so session 3 compares two files field by field.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

UNKNOWN = "unknown"
CANCELLED = "cancelled"
MAIN_OWNED = {"main_verdict", "disposition"}
ANCHOR = re.compile(r"^(§(1[0-3]|[1-9])(\.[0-9]+)?|[\w./-]+\.(py|md):\d+)$")
PROSE_MIN = 20

DIVERGENCE_IDS = [f"D{index:02d}" for index in range(1, 17)]
DIVERGENCE_FIELDS = (
    "section",
    "probe",
    "reading_a",
    "reading_b",
    "why_ambiguous",
    "recommendation",
    "main_verdict",
)

ATTACK_IDS = [f"A{index:02d}" for index in range(1, 13)]
ATTACK_FIELDS = (
    "lens",
    "anchor",
    "claim_as_written",
    "evidence",
    "severity",
    "disposition",
)
SEVERITIES = {"blocking", "major", "minor", "note", UNKNOWN, CANCELLED}
LENSES = {
    "correctness-vs-code",
    "claim-soundness",
    "guarantee-gap",
    "coverage-gap",
    "claude-md-conformance",
    UNKNOWN,
    CANCELLED,
}

OUTCOMES = {"ok", "error", "differs", "unreachable", UNKNOWN}

# id -> what the observation must demonstrate. Both implementations answer all of them.
ORACLE_PROBES: dict[str, str] = {
    # Section 3, the three states.
    "R01_hit": "promoted input: passed, matched, output, artifact_hash, document present",
    "R02_miss": "absent input: passed True, matched False, output None, artifact_hash None",
    "R03_failed_suspended": "a suspended member: passed False, match None, document None",
    "R04_expected_hash_mismatch": "a wrong expected_function_hash: passed False, match None",
    "R05_no_promoted_set": "registered operation with nothing promoted: passed, entries, match",
    "R06_over_capacity": "FUNCTION_MAX_ENTRIES patched below the real count: passed False, entries real, match None, no row enumeration",
    "R07_biconditional": "across every probed state: match is None iff passed is False, both directions",
    # Section 4, argument validation precedence, all of it before any ledger read.
    "R08_invalid_partition": "exact class and message for a rejected partition",
    "R09_invalid_operation": "exact class and message for a rejected operation",
    "R10_invalid_expected_hash": "exact class and message for a non-64-hex expected hash",
    "R11_uncanonicalizable_input": "exact class and message for an input canonicalize refuses",
    "R12_precedence_partition_before_input": "bad partition AND bad input: which one is reported",
    "R13_precedence_operation_before_expected_hash": "bad operation AND bad expected hash: which one is reported",
    "R14_unregistered_operation": "valid arguments, operation absent from the partition: class and message",
    "R15_oversize_input": "input above DEFAULT_MAX_BYTES: class, message, and that no ledger read happened",
    # Section 7, raise versus failed verdict.
    "R16_missing_ledger": "deleted ledger: class, message, and the path still absent afterwards",
    "R17_malformed_stored_revision": "corrupt stored operation scalar: class and message",
    "R18_revoked_member": "a revoked member produces a failed verdict, never an exception",
    # Section 5, purity, one observation per obligation.
    "R19_ledger_bytes_stable": "ledger sha256 AND full iterdump text identical across hit, miss, failed",
    "R20_clock_never_read": "a System whose _now raises answers all three states unchanged",
    "R21_events_unchanged": "events() byte-identical and the event sequence counter unmoved",
    "R22_source_never_invoked": "a source whose propose raises resolves a miss without calling it",
    # Section 6, snapshot obligations.
    "R23_one_snapshot": "exactly one Store.transaction call, write=False, in_transaction True throughout",
    "R24_evaluate_call_counts": "evaluate call count per state: failed 0, miss 1, hit 1",
    "R25_document_outside_snapshot": "the returned document evaluated after the snapshot equals evaluating inside it",
    # Canonicalization.
    "R26_canonical_equivalent_input": "a key-reordered equal input resolves to the same hit",
}
ORACLE_FIELDS = ("outcome", "observation", "note")


def _fail(message: str) -> None:
    print(f"INVALID: {message}")
    raise SystemExit(1)


def _rows(payload: dict, key: str, required: list[str]) -> dict[str, dict]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        _fail(f"{key!r} must be a list")
    seen: dict[str, dict] = {}
    for row in raw:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            _fail(f"every {key} row must be an object with a string id")
        if row["id"] in seen:
            _fail(f"duplicate row id {row['id']!r}")
        seen[row["id"]] = row
    missing = [identifier for identifier in required if identifier not in seen]
    extra = [identifier for identifier in seen if identifier not in required]
    if missing:
        _fail(f"missing row ids: {missing}")
    if extra:
        _fail(f"unexpected row ids: {extra}")
    return seen


def _grade_table(
    rows: dict[str, dict],
    fields: tuple[str, ...],
    *,
    prose: set[str],
    checks: dict[str, set[str]],
) -> tuple[int, int]:
    unknown = 0
    cancelled = 0
    for identifier, row in sorted(rows.items()):
        values = {field: row.get(field) for field in fields}
        for field, value in values.items():
            if not isinstance(value, str):
                _fail(f"{identifier}.{field} must be a string")
        if all(value == CANCELLED for value in values.values()):
            cancelled += 1
            continue
        for field, value in values.items():
            if value == CANCELLED:
                _fail(f"{identifier}.{field} is cancelled while siblings are not")
            if value == UNKNOWN:
                if field not in MAIN_OWNED:
                    unknown += 1
                continue
            if field in checks and value not in checks[field]:
                _fail(f"{identifier}.{field}={value!r} is not one of {sorted(checks[field])}")
            if field in prose and len(value) < PROSE_MIN:
                _fail(f"{identifier}.{field} is {len(value)} chars, under {PROSE_MIN}")
        anchor = values.get("anchor") or values.get("section")
        if anchor not in (None, UNKNOWN) and ANCHOR.fullmatch(anchor) is None:
            _fail(f"{identifier} anchor {anchor!r} is neither §N nor path:line")
    return unknown, cancelled


def _validate_divergences(payload: dict) -> tuple[int, int]:
    rows = _rows(payload, "rows", DIVERGENCE_IDS)
    return _grade_table(
        rows,
        DIVERGENCE_FIELDS,
        prose={"probe", "reading_a", "reading_b", "why_ambiguous", "recommendation"},
        checks={},
    )


def _validate_attack(payload: dict) -> tuple[int, int]:
    rows = _rows(payload, "rows", ATTACK_IDS)
    return _grade_table(
        rows,
        ATTACK_FIELDS,
        prose={"claim_as_written", "evidence"},
        checks={"severity": SEVERITIES, "lens": LENSES},
    )


def _validate_oracle(payload: dict) -> tuple[int, int]:
    unknown = 0
    for field in ("impl_path", "driver_path", "commit"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            _fail(f"top-level {field!r} must be a non-empty string")
        if payload[field] == UNKNOWN:
            unknown += 1
    probes = payload.get("probes")
    if not isinstance(probes, dict):
        _fail("'probes' must be an object")
    missing = [identifier for identifier in ORACLE_PROBES if identifier not in probes]
    extra = [identifier for identifier in probes if identifier not in ORACLE_PROBES]
    if missing:
        _fail(f"missing probe ids: {missing}")
    if extra:
        _fail(f"unexpected probe ids: {extra}")
    for identifier, probe in sorted(probes.items()):
        if not isinstance(probe, dict) or set(probe) != set(ORACLE_FIELDS):
            _fail(f"{identifier} must be an object with keys {sorted(ORACLE_FIELDS)}")
        outcome = probe["outcome"]
        if outcome not in OUTCOMES:
            _fail(f"{identifier}.outcome={outcome!r} is not one of {sorted(OUTCOMES)}")
        note = probe["note"]
        if not isinstance(note, str):
            _fail(f"{identifier}.note must be a string")
        observation = probe["observation"]
        if outcome == UNKNOWN:
            unknown += 1
            continue
        if not isinstance(observation, dict) or not observation:
            _fail(f"{identifier}.observation must be a non-empty object once outcome is filled")
        if len(note) < PROSE_MIN:
            _fail(f"{identifier}.note is {len(note)} chars, under {PROSE_MIN}")
    return unknown, 0


VALIDATORS = {
    "divergences": _validate_divergences,
    "attack": _validate_attack,
    "oracle": _validate_oracle,
}


def main(argv: list[str]) -> int:
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
    unknown, cancelled = VALIDATORS[kind](payload)
    print(f"KIND: {kind}")
    print(f"CANCELLED: {cancelled}")
    print(f"UNKNOWN-CELLS: {unknown}")
    if unknown:
        print("INCOMPLETE: fill every cell, then rerun this validator LAST")
        return 1
    print("VALID: structurally sound with zero unfilled cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
