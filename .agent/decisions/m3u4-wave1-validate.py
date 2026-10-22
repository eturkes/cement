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

import re
import sys

from wave_validate import StrictWave

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


TABLES = {
    "map": dict(subjects=MAP_SUBJECTS, fields=MAP_FIELDS, identity="subject",
                strings=("anchor", "finding", "evidence", "action", "main_verdict"),
                prose=("finding", "evidence"), enums={"action": ACTIONS}, extension=MAP_EXTENSION),
    "spike": dict(subjects=SPIKE_PROBES, fields=SPIKE_FIELDS, identity="probe",
                  top=("alternative", "adapter_signature", "worktree_commit"), outcomes=OUTCOMES,
                  defaults={"observation": {}, "note": ""}, extension=SPIKE_EXTENSION),
}
ENGINE = StrictWave(TABLES, doc=__doc__, main_owned=MAIN_OWNED, prose_min=PROSE_MIN, anchor=ANCHOR)
VALIDATORS = ENGINE.validators
_seed = ENGINE.seed
main = ENGINE.main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
