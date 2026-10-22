#!/usr/bin/env python3
"""Structural validator for M3.3 wave-1 artifacts.

Usage:
  uv run python .agent/decisions/m3u3-wave1-validate.py <artifact.json>
  uv run python .agent/decisions/m3u3-wave1-validate.py --emit-seed map|spike

The artifact's top-level ``kind`` selects the schema:

  "map"    the unit surface map, one row per seeded subject
  "spike"  one submission-API alternative, one row per seeded probe

Exit 0 = structurally valid AND nothing left ``unknown`` outside a MAIN-owned
field. Exit 1 = structural defect or an unfilled cell.

Seeding contract: ``--emit-seed`` writes every required id with every value
``unknown``. That file is STRUCTURALLY valid and still exits 1, so UNKNOWN-CELLS
is the flush metric and each filled cell lowers it by one.

``subject`` and ``probe`` are MAIN-owned row identity: the validator rejects any
value other than the seeded text, so a row keeps its assigned subject. Report a
wrong subject to MAIN instead of rewriting it. ``main_verdict`` is MAIN-owned in
the other direction: MAIN fills it, the teammate leaves it ``unknown``, and it
never counts as unfilled.
"""

from __future__ import annotations

import re
import sys

from wave_validate import StrictWave

UNKNOWN = "unknown"
MAIN_OWNED = {"main_verdict"}
ANCHOR = re.compile(r"^([\w./-]+\.(py|md|json):\d+(-\d+)?|[0-9a-f]{7,40}|n/a)$")
PROSE_MIN = 20

ACTIONS = {
    "ships-in-m3u3",
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
    # `handle` decomposed into the responsibilities M3.3 must place.
    "H01": "argument validation: retry_failed boolean, partition/operation names, request_id, canonicalize, and their order",
    "H02": "request-row idempotency lookup and ConflictError when a request_id is rebound to different content",
    "H03": "stale-revision short circuit through _request_revision_is_current",
    "H04": "expired-lease takeover of a `generating` request",
    "H05": "retry_failed re-arm of a `failed` request",
    "H06": "operation registration lookup and NotFoundError",
    "H07": "promoted-artifact exact lookup at the current operation revision",
    "H08": "ambiguity quarantine: suspend every duplicate and emit artifact.ambiguity_quarantined",
    "H09": "_validate_promoted integrity check and artifact.integrity_quarantined quarantine",
    "H10": "hit path: INSERT a `resolved` request row and emit request.resolved_by_artifact",
    "H11": "miss path: INSERT a `generating` request row holding a lease",
    "H12": "absent candidate_source becomes _fail_generation('candidate_source_unavailable')",
    "H13": "source invocation outside every transaction, with CandidateSourceError and bare Exception both normalized to candidate_source_error",
    "H14": "post-generation re-read: terminal status, stale revision, lease-owner fencing",
    "H15": "proposal write: proposal.created event, INSERT proposals, UPDATE request to `pending`, return ReviewRequired",
    "H16": "_fail_generation: UPDATE request `failed`, emit request.fallback_failed, return FallbackFailed",
    "H17": "_outcome status projection including artifact re-validation, _assess_examples, and IntegrityError on an unknown status",
    # Consumers that read request state today.
    "C01": "System.request_status",
    "C02": "System.get_proposal and the ProposalView model",
    "C03": "System.proposal",
    "C04": "System.proposals and its join onto requests",
    "C05": "System.review and the resolved/rejected request transition it writes",
    "C06": "System.function_report and PendingProposalGap",
    "C07": "cli.py request/handle command surface and its exit mapping",
    "C08": "models.py Outcome union members and which of them M3.3 still returns",
    "C09": "__init__.py exports naming request-lifecycle types",
    # Source protocol and error normalization, which M3.3 owns outright.
    "S01": "CandidateSource protocol and the CandidateRequest.request_id field it hands the adapter",
    "S02": "CandidateSourceError's public contract and the supervised-fallback docstring M3.3 rewrites",
    "S03": "the exact public message text a failed source produces under M3.3, and the document that publishes it",
    "S04": "proof obligation: a failing source leaves no durable row and no event",
    "S05": "_command_supervisor.py and example_adapter.py coupling that M3.7 relocates and M3.3 must not break",
    # Archaeology. Every claim carries a checkable SHA.
    "A01": "M3.1's API-removal pattern: what let a deletion unit land in one implementation session",
    "A02": "history of the proposals table and its (partition, request_id) foreign key",
    "A03": "M3.2b's `resolve` as the closest analog for adding a public System method: estimate against measured production lines",
    "A04": "the roadmap's byte-identical-`handle` claim across 3b7769b, 6f4f260, 71c5eab, 83198e1, re-verified at HEAD",
}

# Probe corpus. Both alternatives answer every id with the same observation keys.
SPIKE_PROBES: dict[str, str] = {
    "P01": "direct submission of a caller-supplied candidate: result value, and every durable row and event written",
    "P02": "source-backed submission: the source runs exactly once, and the durable footprint against P01",
    "P03": "the source runs OUTSIDE every open transaction: connection.in_transaction observed during propose",
    "P04": "the source raises CandidateSourceError: exact public class and message, zero durable rows, zero events",
    "P05": "the source raises an arbitrary Exception: identical public text to P04, nothing internal leaked",
    "P06": "source-backed submission with no candidate_source configured: exact class and message",
    "P07": "direct submission while a candidate_source IS configured: the source must not be invoked",
    "P08": "both candidate and source supplied, and neither supplied: exact class and message, or the signature that makes it unreachable",
    "P09": "the operation revision changes between candidate generation and the proposal write",
    "P10": "unregistered operation: class, message, and whether the source ran before the check",
    "P11": "the identical input submitted twice: proposal count, and proof that no request_id idempotency survives",
    "P12": "argument validation precedence: a bad partition together with a bad input, and that no ledger read happened",
    "P13": "the private request row this alternative writes: status, columns, and every public method that could surface it",
    "P14": "call-site ergonomics: the exact signature, and the rewrite each of run_demo.py's 7 handle calls needs",
}


TABLES = {
    "map": dict(subjects=MAP_SUBJECTS, fields=MAP_FIELDS, identity="subject",
                strings=("anchor", "finding", "evidence", "action", "main_verdict"),
                prose=("finding", "evidence"), enums={"action": ACTIONS}),
    "spike": dict(subjects=SPIKE_PROBES, fields=SPIKE_FIELDS, identity="probe",
                  top=("alternative", "api_signature", "worktree_commit"), outcomes=OUTCOMES,
                  defaults={"observation": {}, "note": ""}),
}
ENGINE = StrictWave(TABLES, doc=__doc__, main_owned=MAIN_OWNED, prose_min=PROSE_MIN, anchor=ANCHOR)
VALIDATORS = ENGINE.validators
_seed = ENGINE.seed
main = ENGINE.main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
