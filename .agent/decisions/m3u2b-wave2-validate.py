#!/usr/bin/env python3
"""Structural validator for M3.2b wave-2 artifacts.

Usage: uv run python .agent/decisions/m3u2b-wave2-validate.py <artifact.json>

The artifact's top-level ``kind`` selects the schema:

  "divergences"  the diff-blind `tester` author's phase-1 divergence table
  "attack"       the reviewer's pre-implementation contract attack
  "review"       adversarial review of LANDED code, one finding per row
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

import re
import sys

from wave_validate import StrictWave

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
REVIEW_IDS = [f"V{index:02d}" for index in range(1, 13)]
REVIEW_FIELDS = (
    "lens",
    "anchor",
    "finding",
    "evidence",
    "acceptance_check",
    "severity",
    "disposition",
)
SEVERITIES = {"blocking", "major", "minor", "note", UNKNOWN, CANCELLED}
LENSES = {
    "correctness-vs-code",
    "claim-soundness",
    "guarantee-gap",
    "coverage-gap",
    "mutation-survivor",
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


TABLES = {
    "divergences": dict(subjects=DIVERGENCE_IDS, fields=DIVERGENCE_FIELDS, named_rows=True, cancelled=True,
                        prose={"probe", "reading_a", "reading_b", "why_ambiguous", "recommendation"}),
    "attack": dict(subjects=ATTACK_IDS, fields=ATTACK_FIELDS, named_rows=True, cancelled=True,
                   prose={"claim_as_written", "evidence"}, enums={"severity": SEVERITIES, "lens": LENSES}),
    "review": dict(subjects=REVIEW_IDS, fields=REVIEW_FIELDS, named_rows=True, cancelled=True,
                   prose={"finding", "evidence", "acceptance_check"}, enums={"severity": SEVERITIES, "lens": LENSES}),
    "oracle": dict(subjects=ORACLE_PROBES, fields=ORACLE_FIELDS, probe_object=True,
                   top=("impl_path", "driver_path", "commit"), outcomes=OUTCOMES),
}
ENGINE = StrictWave(TABLES, doc=__doc__, main_owned=MAIN_OWNED, prose_min=PROSE_MIN,
                    anchor=ANCHOR, seed=False, report="cancelled")
VALIDATORS = ENGINE.validators
main = ENGINE.main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
