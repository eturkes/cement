#!/usr/bin/env python3
"""Fill the MAIN-owned `disposition` column of m3u4-attack.json. Idempotent, replayable
from the teammate's committed table (wt/rev-m3u4-1).

    uv run python .agent/decisions/m3u4-rule-attack.py [--check]

`--check` exits 1 when the table is out of sync, so a later lens fails loudly rather than
silently going unruled.

Dispositions:
  RESOLVED     the attack lands and contract section 14 or 15 already answers it
  FIXED        the attack lands and the fix shipped in code or prose this session
  CORRECTED    the attack is right about the gap and wrong about the remedy
  DEFERRED-S3  the attack lands against a gate that does not exist yet; the battery owns it
  CLEARED      no defect; the lens closed against the shipped design
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u4-attack.json")
COLUMN = "disposition"
# Measured against the raw bytes; ASCII-only ruling text keeps this stable either way.
DUMP = dict(indent=2, ensure_ascii=False, sort_keys=False)

RULINGS: dict[str, str] = {
    "A01": (
        "RESOLVED by section 14. The attack is right that D12 named no criterion. A PROJECTED VALUE "
        "is now defined as one read FROM THE LEDGER for that decision: output and example_id are "
        "ledger-derived and kept, while source is the literal 'confirmed' on this path and "
        "artifact_id defaults to None because review creates an example and never an artifact."
    ),
    "A02": (
        "DEFERRED-S3, and the attack is exactly right. Python does not enforce Literal values, so "
        "annotation and signature introspection pass while both confirming paths still return "
        "'resolved'. The shipped instrument pins annotation TEXT and cannot catch this. The battery "
        "owns one runtime test calling accept, correct and reject and asserting both the "
        "ReviewResult value and the serialized CLI status for each."
    ),
    "A03": (
        "RESOLVED by section 14. D01 is amended to one named private READER plus at most one named "
        "private WRITER. 'Exactly ONE surface' was written while both spikes were read-only, and "
        "section 12 proved a read-only surface cannot confine a write."
    ),
    "A04": (
        "CORRECTED, and narrowed. The attack's own example fails: Python concatenates ADJACENT "
        "string literals at parse time, so `'reque' 'sts'` reaches the AST as one 'requests' "
        "constant and the instrument catches it. The real hole is RUNTIME composition - explicit "
        "`+`, `.format`, f-string or `.join` - which no AST string census can see. D06 already names "
        "this class as a defect rather than a gate; the instrument is a TRIPWIRE, not a security "
        "boundary, and the contract must not claim it 'fails closed' against a hostile author. "
        "DEFERRED-S3 for the negative-control mutant that documents the boundary."
    ),
    "A05": "CLEARED. Selections carry bound values only; the adapter owns every complete statement.",
    "A06": (
        "FIXED in code this session. The attack is correct: slots=True was unpinned, and turning it "
        "off keeps the constructor signature and resolved hints identical while giving instances a "
        "__dict__. tests/test_proposal_binding.py now asserts __slots__ presence and __dict__ "
        "absence on ReviewResult, ProposalView and PendingProposalGap."
    ),
    "A07": (
        "DEFERRED-S3. D13 states a smell with no baseline metric and no rejection, so reporting it "
        "discharges it. The battery owns an AST statement-count or source-span comparison against "
        "the baseline converters, with the request_id deletion subtracted."
    ),
    "A08": (
        "DEFERRED-S3. State-only assertions cannot see write ORDER, and D15 asks for order. The "
        "battery owns a whole-channel SQL trace asserting the exact ordered subsequence for reject, "
        "accept, correct and accept-with-quarantine, including the writer helper's own statements."
    ),
    "A09": (
        "DEFERRED-S3. A count pin and a quarantine-state pin pass independently while the quarantine "
        "path persists two examples. The battery owns a before/after example count on one quarantine "
        "fixture, asserting a delta of exactly one and equating the sole row id with "
        "ReviewResult.example_id."
    ),
    "A10": (
        "DEFERRED-S3. Binding status_sequence to a trailing artifact.counterexample event passes "
        "every normal-path and quarantine-state test. The battery owns fixtures equating "
        "proposals.status_sequence to the matching proposal decision event and rejecting every "
        "intervening sequence."
    ),
    "A11": "CLEARED. The retained P12 collider corpus makes each equals-to-LIKE mutant live.",
    "A12": (
        "RESOLVED by section 15. D22's tail is COUNTED, not reachable. The API exposes no cursor past "
        "projection_limit, so the obligation is that the tail contributes to the exact count and is "
        "still validated - section 14's X32 - never that a caller can read it."
    ),
    "A13": (
        "DEFERRED-S3, and this is the sharpest lens in the table. Both assertions D23 permits survive "
        "replacing ORDER BY p.id with ORDER BY created_at_us, p.id: the page stays a stable set and "
        "stays a prefix of that same implementation's unbounded query. Self-consistency is not a "
        "pin. The battery owns a reverse-created fixture asserting the exact lexicographic p.id "
        "sequence at two projection limits."
    ),
    "A14": (
        "RESOLVED by section 15, and the premise it attacks was false. final_output_json, "
        "final_output_hash, reviewer, review_note and reviewed_at_us are nullable by schema, so a "
        "mutant dropping a None guard raises a raw TypeError from a REAL ledger. D24 must enumerate "
        "nullable versus non-null converted fields and reserve 'fabricated' for proxy-injected "
        "storage classes alone."
    ),
    "A15": (
        "DEFERRED-S3. A token grep is satisfied by one mention inside a code fence. The battery owns "
        "a check that prose OUTSIDE code fences names all four fields, defines the three statuses "
        "and the reject nulls, and positively states the request-free scope."
    ),
    "A16": (
        "FIXED in prose this session. README published accepted/corrected without saying the handle "
        "lifecycle still reports resolved, which made the change read as a system-wide rename. "
        "README now contrasts the two vocabularies and states that Cement translates neither into "
        "the other."
    ),
    "A17": (
        "CONFIRMED and closed by measurement. The burden harness measured an R1 three-field shape "
        "with no adapter, and S2 then rejected R1 and composed a third design, so the work list was "
        "never compared against what shipped. Section 7's forecast is retained as the MEASUREMENT IT "
        "WAS, not as a fit conclusion; the shipped numbers live in the S2 roadmap record, where the "
        "composed adapter is reported separately from the eight consumer edits."
    ),
    "A18": (
        "RESOLVED by section 15, and the overclaim was real. Z50 is a COUPLING CENSUS: all six "
        "consumer WHERE clauses name p. columns or binding_* aliases and never r., so an M3.6b "
        "rewrite touches no consumer. No artifact contains a performed v3 swap. 'The adapter "
        "survives the swap untouched' is a PREDICTION this unit does not verify, and M3.6b owns its "
        "proof."
    ),
    "Y1": (
        "FIXED this session, and the contradiction was real. The preface and both fork headings said "
        "PENDING while carrying S2 RULING blocks, so two careful readers could implement different "
        "contracts. The preface now states that every section is ruled and that a ruling governs "
        "where it disagrees with a numbered obligation; both headings read RULED."
    ),
    "Y2": (
        "RESOLVED by section 14 and section 15. Attribution is LEXICAL, so the SQL-free wrapper is "
        "not an owner and D03's permitted delta EXCLUDES _proposal_binding. The shipped owner set is "
        "exactly seven names. Call-closure attribution is rejected on its own merits: it drags every "
        "public consumer back into the set and makes the obligation unsatisfiable by construction."
    ),
    "Y3": (
        "RESOLVED by section 14 through the V17 and X18 rulings, which the shipped code already "
        "satisfies. An ABSENT PROPOSAL is NotFoundError; an EXISTING proposal with an absent or "
        "mismatched binding is IntegrityError on every singular read, review, list and report. "
        "Baseline P14's fail-open behaviour is not the oracle."
    ),
    "Y4": (
        "RESOLVED by section 15, and the attack found a genuine contradiction. Section 13 keeps "
        "status while changing its value, and D12 demands byte-identical remaining values; both "
        "could not hold silently. The exemption is now named and bounded to status alone, with its "
        "grounds in section 13, and every other kept value stays byte-identical."
    ),
    "Y5": (
        "RESOLVED by section 15. D13's request_id deletion is assigned to _proposal_record ALONE. "
        "_proposal_content never carried the field, so applying D13 literally forced a nonexistent "
        "deletion and hid the only change it may make, which is its argument source."
    ),
    "Y6": (
        "RESOLVED by section 15, which publishes the numbers D16 asserted as 'unchanged': reviewer "
        "nonempty, control-free, at most 256 UTF-8 bytes; note empty-allowed, control-free, at most "
        "2048 bytes; one shared now across every provenance edge. A contract-derived battery cannot "
        "author a boundary pair against a number the contract never states."
    ),
    "Y7": (
        "DEFERRED-S3. 'Every condition' has no predicate inventory, so one promoted-conflict fixture "
        "proves quarantine while a deleted promoted-status predicate survives. The battery owns "
        "one-predicate-at-a-time mutants for partition, operation, revision, input hash, input JSON, "
        "unequal output and promoted status, with reject proving zero quarantine work."
    ),
    "Y8": (
        "DEFERRED-S3, and it restates a standing project lesson: a survivor count is meaningless "
        "without its catalogue and its verdict modules. The battery owns a committed catalogue "
        "enumerating every changed predicate AND non-predicate obligation, a changed-bytes and "
        "loaded-code proof per mutant, a pristine control, and a harness that prints its verdict "
        "modules on the control line."
    ),
    "Y9": (
        "CONFIRMED, and it falsified a committed ground. Measured with EXPLAIN QUERY PLAN on the "
        "shipped schema under SQLite 3.53.1, the ALT-PROJECTION wrapper and the shipped statement "
        "produce IDENTICAL plans: SEARCH r USING INDEX requests_scope (partition=? AND operation=?), "
        "SEARCH p USING sqlite_autoindex_proposals_3, USE TEMP B-TREE FOR ORDER BY. SQLite flattens "
        "the subquery and pushes the operation predicate down. Section 15 WITHDRAWS the D22 "
        "materialization ground. Fork 1's ruling is unchanged because it never rested on it, and the "
        "LEFT JOIN ground is now sharper: strength reduction applies only where the outer query "
        "constrains the right table, so the singular read path keeps the LEFT JOIN and returns an "
        "orphan with NULL binding columns instead of failing closed."
    ),
    "Y10": (
        "RESOLVED by section 15. The exact CLI triples in section 13 are an OBLIGATION, not "
        "commentary, and the battery owns one test asserting exit 0 plus the exact sorted key set "
        "and values for all three decisions, including both explicit null-valued reject keys. An "
        "unnumbered paragraph is invisible to a one-test-per-obligation battery."
    ),
    "Y11": (
        "DEFERRED-S3, and it attacks the property the fork was decided on. A validation SELECT added "
        "inside _proposal_bindings keeps one permitted owner, correct shapes and correct behaviour "
        "while recreating the per-consumer statement cost that ruled ALT-BINDING out. The battery "
        "owns a total-channel recorder asserting exact application and requests-statement counts per "
        "path, with each adapter call issuing exactly one statement."
    ),
    "Y12": (
        "DEFERRED-S3. Verified by hand this session - Outcome's args are exactly Resolved, "
        "ReviewRequired, InProgress, FallbackFailed, Rejected, ReconciliationRequired, with "
        "ReviewResult absent - but no TEST asserts it, so inserting ReviewResult into the union "
        "passes every export and ordering pin. The battery owns the exact unchanged Outcome member "
        "assertion beside the export census."
    ),
    "Y13": (
        "CORRECTED in its remedy, right about the gap, and the same defect the sibling verdict table "
        "reported as X15 from the other side. The corpus exercises only the two already-clean "
        "creation routes. The handle route IS the one leak, at system.py:1262. But its payload must "
        "NOT become empty: section 14 rules it RETAINED under the handle-lifecycle exception, "
        "because handle is not an owned site, M3.5b removes its grammar and M3.6a deletes the "
        "method. The battery asserts that payload UNCHANGED, pinning the exception."
    ),
    "Y14": (
        "DEFERRED-S3. One unspecified scalar at two positions cannot force an every-scalar claim. "
        "The battery owns a generated field inventory mapping every converted persisted scalar to a "
        "real-ledger or explicitly fabricated probe, corrupting middle and last for each loop-owned "
        "converter."
    ),
    "Y15": (
        "CONFIRMED against the project's own authoring rule, remediation scheduled. Sections 12 and "
        "13 retain wave chronology, dispatch history and worktree state, which competes with the "
        "binding obligations. Section 15 records the disposition: the narrative moves to "
        ".agent/archive/ at milestone close and the obligations stay. Not done now because the "
        "grounds are still load-bearing for S3's battery."
    ),
    "Y16": (
        "DEFERRED-S3. Observing connection.in_transaction on the supplied connection does not prove "
        "the adapter USED it, so a second read opened inside the adapter passes the stated probe "
        "while lookup and companion write span different snapshots. The battery owns connection "
        "IDENTITY assertions across all five public paths plus a review race proving lookup and "
        "status write share one write transaction."
    ),
    "Y17": (
        "RESOLVED by section 15, and it disproves D24's premise with a real-ledger path. A supported "
        "pending proposal whose TEXT input_json is rewritten to malformed JSON is a schema-valid "
        "STRICT row, and parse_json raises ValidationError, a ValueError subclass, with no proxy and "
        "no schema violation. D24 must translate real-ledger malformed JSON to IntegrityError on all "
        "five paths."
    ),
    "Y18": (
        "RESOLVED by section 15, and the claim was false as written. Public consumers do lose "
        "access: accept and correct lose request_id, source and artifact_id, proposal readers lose "
        "request_id, and status changes value. Section 1 now claims only that NO STORED SCHEMA OR "
        "ROW INFORMATION IS DELETED, with the public losses enumerated as intentional."
    ),
    "Y19": (
        "RESOLVED by section 15. The schema freeze is an OBLIGATION, not commentary. The battery "
        "owns one test comparing SCHEMA_VERSION, SCHEMA bytes and SCHEMA_FINGERPRINT against the "
        "14580-byte baseline whose sha256 is "
        "5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77, rejecting every table, "
        "column, view or index delta."
    ),
    "Y20": (
        "DEFERRED-S3. One compound obligation is satisfiable on the dataclasses alone while "
        "_proposal_record still carries the key. The battery owns an explicit PATH MATRIX asserting "
        "identity absence from get_proposal, proposal, proposals, review, function_report, proposal "
        "events, CLI show/list/review, the public dataclasses and Outcome."
    ),
    "Y21": (
        "DEFERRED-S3. Deleting `decision != reject` from the revision fence passes every "
        "current-revision test and the one stale-accept probe. The battery owns one stale fixture "
        "crossed with all three decisions: accept and correct raise StateError with zero writes, and "
        "reject completes one rejected transition with no example."
    ),
}


def main(argv: list[str]) -> int:
    check = argv[1:] == ["--check"]
    if argv[1:] and not check:
        print(__doc__)
        return 2

    raw = TABLE.read_bytes()
    payload = json.loads(raw)
    # Serialization pin: prove the round-trip BEFORE patching, so a rewrite never reformats
    # the teammate's committed bytes as a side effect.
    if (json.dumps(payload, **DUMP) + "\n").encode() != raw:
        print(f"ABORT   {TABLE.name}: serialization does not round-trip; re-measure DUMP")
        return 1

    rows = payload["rows"]
    ids = [row["id"] for row in rows]
    if set(ids) != set(RULINGS):
        missing = sorted(set(ids) - set(RULINGS))
        extra = sorted(set(RULINGS) - set(ids))
        print(f"ABORT   id set differs. Unruled lenses: {missing}. Ruling has no lens: {extra}")
        return 1

    stale = [row["id"] for row in rows if row[COLUMN] != RULINGS[row["id"]]]
    if check:
        print(f"CHECK   {len(stale)} of {len(rows)} lenses out of sync" if stale
              else f"CHECK   in sync, {len(rows)} lenses ruled")
        return 1 if stale else 0

    for row in rows:
        row[COLUMN] = RULINGS[row["id"]]
    TABLE.write_text(json.dumps(payload, **DUMP) + "\n", encoding="utf-8")
    print(f"RULED   {len(stale)} of {len(rows)} lenses updated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
