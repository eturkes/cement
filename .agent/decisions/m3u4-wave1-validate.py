#!/usr/bin/env python3
"""Structural validator for M3.4 wave-1 artifacts.

Usage:
  uv run python .agent/decisions/m3u4-wave1-validate.py <artifact.json>
  uv run python .agent/decisions/m3u4-wave1-validate.py --emit-seed map|spike

The artifact's top-level ``kind`` selects the schema:

  "map"    the unit surface map, one row per seeded subject
  "spike"  one binding-adapter alternative, one row per seeded probe

Exit 0 = structurally valid AND nothing left ``unknown`` outside a MAIN-owned
field. Exit 1 = structural defect or an unfilled cell.

Seeding contract: ``--emit-seed`` writes every required id with every value
``unknown``. That file is STRUCTURALLY valid and still exits 1, so UNKNOWN-CELLS
is the flush metric and each filled cell lowers it by one. Fill rows in place and
rerun this validator LAST.

``subject`` and ``probe`` are MAIN-owned row identity: the validator rejects any
value other than the seeded text, so a row keeps its assigned subject. Report a
wrong subject to MAIN instead of rewriting it. ``main_verdict`` is MAIN-owned in
the other direction: MAIN fills it, the teammate leaves it ``unknown``, and it
never counts as unfilled.

Retarget clause: the seeded rows are a FLOOR, never a cap. Add rows with ids
``X01``, ``X02``, ... (map) or ``Z01``, ``Z02``, ... (spike) carrying your own
``subject``/``probe`` text for anything the seed missed. Extension rows are
graded exactly like seeded rows except that you own their subject text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

UNKNOWN = "unknown"
MAIN_OWNED = {"main_verdict"}
ANCHOR = re.compile(r"^([\w./-]+\.(py|md|toml|json|lock):\d+(-\d+)?|[0-9a-f]{7,40}|n/a)$")
PROSE_MIN = 20
MAP_EXTENSION = re.compile(r"^X\d{2}$")
SPIKE_EXTENSION = re.compile(r"^Z\d{2}$")

ACTIONS = {
    "ships-in-m3u4",
    "caller-owns",
    "later-unit",
    "unchanged",
    UNKNOWN,
}
OUTCOMES = {"ok", "error", "differs", "unreachable", UNKNOWN}

MAP_FIELDS = ("anchor", "subject", "finding", "evidence", "action", "main_verdict")
SPIKE_FIELDS = ("probe", "outcome", "observation", "note")

# Row identity. MAIN owns every string below; a teammate fills the other fields.
MAP_SUBJECTS: dict[str, str] = {
    # The eight `requests` sites M3.4 owns. One row each: what the site reads or
    # writes, which public field it feeds, and what the binding adapter must serve.
    "Q01": "get_proposal's requests JOIN: exact columns taken from the request row and which reach ProposalView",
    "Q02": "proposal's requests JOIN: how it differs from get_proposal and why both exist",
    "Q03": "proposals' requests JOIN: filters, ORDER BY, LIMIT, and the exact list projection",
    "Q04": "review's requests JOIN under the write lock: what it reads and which checks depend on it",
    "Q05": "review's UPDATE requests SET status='rejected': the companion write and every observable it moves",
    "Q06": "review's UPDATE requests on accept/correct: the companion write and every observable it moves",
    "Q07": "function_report's first requests JOIN: the pending-proposal count and detail projection",
    "Q08": "function_report's second requests JOIN: the pending-gap projection feeding PendingProposalGap",
    "Q09": "_proposal_record: which fields it validates, which come from the request row, and its fail-closed classes",
    "Q10": "_proposal_content: same census, plus whether it can be served without a request join",
    # Public shapes M3.4 freezes request-free, and every consumer of each.
    "S01": "ProposalView.request_id: every read of the field across src, tests, examples and docs",
    "S02": "PendingProposalGap.request_id: every read of the field, and what identifies a gap without it",
    "S03": "review's Outcome return (Resolved at system.py:1646, Rejected at 1510): every field each consumer actually uses",
    "S04": "cli.py's proposal review leaf: the exact JSON it emits today for accept, correct and reject",
    "S05": "proposal event payloads (proposal.created, proposal.rejected, any accept event): whether any carries request identity",
    "S06": "__init__.py exports and models.py ordering that adding ReviewResult and editing two shapes disturbs",
    "S07": "README plus every docs/*.md sentence naming request identity in a proposal, review or report context",
    # Invariants the unit must PRESERVE. A removal battery needs each pinned independently.
    "P01": "proposal status transitions pending -> accepted/corrected/rejected: exact row writes and their order",
    "P02": "reviewer, note and reviewed_at_us provenance capture and validation bounds",
    "P03": "immutable example creation on accept and correct, and its absence on reject",
    "P04": "review's conflict quarantine path and every condition that reaches it",
    "P05": "event sequencing and the proposals.status_sequence binding",
    "P06": "cross-partition and cross-operation proposal invisibility in every read path",
    "P07": "= versus LIKE isolation on partition and operation, including _ colliders and case folding",
    "P08": "function_report pending counts: exactness, the bounded detail cap, the tail beyond 10,000, and the documented order",
    "P09": "every persisted scalar these paths convert, and whether TypeError/ValueError/OverflowError are translated fail-closed",
    "P10": "handle's own proposal path at system.py:1029 and request_status at 1280: what M3.4 must not break while leaving them to a later unit",
    # The adapter itself. This is the fork the two spikes decide.
    "A01": "the column union all eight sites need from the request row, and the minimal binding record that serves it",
    "A02": "N+1 risk: which sites project many proposals at once and what a row-at-a-time adapter costs them",
    "A03": "where the adapter can live (module function, private System method, private class) and what pins its confinement",
    "A04": "store.py schema facts that make the binding safe: the proposals FK, uniqueness on (partition, request_id), NOT NULL columns",
    "A05": "revise_operation's UPDATE requests at system.py:548: whether M3.4 owns it, and the evidence either way",
    # Archaeology. Every claim carries a checkable SHA or file:line.
    "G01": "M3.3's _persist_proposal private-plumbing precedent: what it established and which committed tests pin it",
    "G02": "M3.3's AST closure instrument in tests/test_submission_battery.py: exactly what it measures and whether M3.4 can reuse it",
    "G03": "M3.2b's resolve as the analog for adding one public model plus method: measured production line delta",
    "G04": "M2.u4b churn re-derived at HEAD, against the plan draft's 776-production-line claim",
    "G05": "the 24 .review( call sites across tests: how many read a field M3.4 changes",
}

# Probe corpus. Both alternatives answer every id with the same observation keys.
SPIKE_PROBES: dict[str, str] = {
    "P01": "the adapter's exact signature, return type and column set, as shipped in this worktree",
    "P02": "get_proposal through the adapter: every ProposalView field value against a real ledger, versus baseline",
    "P03": "proposals over a 3-proposal ledger: SQL statement count executed, and whether ordering stays byte-identical",
    "P04": "function_report over the same ledger: SQL statement count, exact pending count, and the detail projection",
    "P05": "review's use of the adapter INSIDE the existing write transaction: connection.in_transaction and transaction count",
    "P06": "the companion request-status writes: kept, moved or dropped by this alternative, and what a later read observes",
    "P07": "confinement: run an AST or source instrument naming every function that mentions requests, and report the exact set",
    "P08": "ReviewResult: the shape this alternative ships and the exact CLI JSON for accept, correct and reject versus today",
    "P09": "PendingProposalGap without request_id: the shipped field set and every call site rewritten",
    "P10": "the .review( and ProposalView call sites this alternative breaks: count, and the mechanical rewrite for each shape",
    "P11": "scalar corruption of the MIDDLE and the LAST of >=3 proposals, read through the adapter: exact class and message",
    "P12": "partition and operation colliders (tenant_a versus tenantXa, case variants) through every adapted read",
    "P13": "measured production line delta per file for this alternative, plus the static source span it edits",
    "P14": "a proposal whose private request row is missing or mismatched: class, message, and whether the state is reachable",
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


def _validate_map(payload: dict) -> int:
    rows = _rows(payload, MAP_SUBJECTS, MAP_EXTENSION)
    unknown = 0
    for identifier, row in sorted(rows.items()):
        if set(row) != {"id", *MAP_FIELDS}:
            _fail(f"{identifier} must carry exactly id plus {list(MAP_FIELDS)}")
        seeded = MAP_SUBJECTS.get(identifier)
        if seeded is not None and row["subject"] != seeded:
            _fail(f"{identifier}.subject was rewritten; MAIN owns it, report the objection instead")
        if seeded is None and len(row["subject"]) < PROSE_MIN:
            _fail(f"{identifier}.subject is {len(row['subject'])} chars, under {PROSE_MIN}")
        for field in ("anchor", "finding", "evidence", "action", "main_verdict"):
            value = row[field]
            if not isinstance(value, str):
                _fail(f"{identifier}.{field} must be a string")
            if value == UNKNOWN:
                if field not in MAIN_OWNED:
                    unknown += 1
                continue
            if field == "action" and value not in ACTIONS:
                _fail(f"{identifier}.action={value!r} is not one of {sorted(ACTIONS)}")
            if field == "anchor" and ANCHOR.fullmatch(value) is None:
                _fail(f"{identifier}.anchor {value!r} is neither path:line[-line] nor a SHA nor n/a")
            if field in ("finding", "evidence") and len(value) < PROSE_MIN:
                _fail(f"{identifier}.{field} is {len(value)} chars, under {PROSE_MIN}")
    return unknown


def _validate_spike(payload: dict) -> int:
    unknown = 0
    for field in ("alternative", "adapter_signature", "worktree_commit"):
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            _fail(f"top-level {field!r} must be a non-empty string")
        if value == UNKNOWN:
            unknown += 1
    rows = _rows(payload, SPIKE_PROBES, SPIKE_EXTENSION)
    for identifier, row in sorted(rows.items()):
        if set(row) != {"id", *SPIKE_FIELDS}:
            _fail(f"{identifier} must carry exactly id plus {list(SPIKE_FIELDS)}")
        seeded = SPIKE_PROBES.get(identifier)
        if seeded is not None and row["probe"] != seeded:
            _fail(f"{identifier}.probe was rewritten; MAIN owns it, report the objection instead")
        if seeded is None and len(row["probe"]) < PROSE_MIN:
            _fail(f"{identifier}.probe is {len(row['probe'])} chars, under {PROSE_MIN}")
        outcome = row["outcome"]
        if outcome not in OUTCOMES:
            _fail(f"{identifier}.outcome={outcome!r} is not one of {sorted(OUTCOMES)}")
        if not isinstance(row["note"], str):
            _fail(f"{identifier}.note must be a string")
        if outcome == UNKNOWN:
            unknown += 1
            continue
        if not isinstance(row["observation"], dict) or not row["observation"]:
            _fail(f"{identifier}.observation must be a non-empty object once outcome is filled")
        if len(row["note"]) < PROSE_MIN:
            _fail(f"{identifier}.note is {len(row['note'])} chars, under {PROSE_MIN}")
    return unknown


def _seed(kind: str) -> dict:
    if kind == "map":
        return {
            "kind": "map",
            "rows": [
                {
                    "id": identifier,
                    "anchor": UNKNOWN,
                    "subject": subject,
                    "finding": UNKNOWN,
                    "evidence": UNKNOWN,
                    "action": UNKNOWN,
                    "main_verdict": UNKNOWN,
                }
                for identifier, subject in MAP_SUBJECTS.items()
            ],
        }
    return {
        "kind": "spike",
        "alternative": UNKNOWN,
        "adapter_signature": UNKNOWN,
        "worktree_commit": UNKNOWN,
        "rows": [
            {"id": identifier, "probe": probe, "outcome": UNKNOWN, "observation": {}, "note": ""}
            for identifier, probe in SPIKE_PROBES.items()
        ],
    }


VALIDATORS = {"map": _validate_map, "spike": _validate_spike}


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
    print(f"UNKNOWN-CELLS: {unknown}")
    if unknown:
        print("INCOMPLETE: fill every cell, then rerun this validator LAST")
        return 1
    print("VALID: structurally sound with zero unfilled cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
