#!/usr/bin/env python3
"""Fill the MAIN-owned `main_verdict` column of m3u4-verdicts.json. Idempotent, replayable
from the teammate's committed table (wt/test-m3u4-1 @ 975bb98).

    uv run python .agent/decisions/m3u4-rule-verdicts.py [--check]

`--check` exits 1 when the table is out of sync, so the wave re-derives from the committed
table and a later row addition fails loudly instead of silently going unruled.

Every ruling is judged against the SHIPPED code at bdbe94a and the contract's section 14.

Verdict prefixes:
  CONFIRMED  the row's expected outcome is the ruled one; battery encodes it as written
  SCOPED     the row overreaches; the ruling narrows its domain before the battery sees it
  CORRECTED  the row is WRONG against shipped code or a section 14 amendment
  ACCEPTED   the row found a real gap outside the shipped code
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u4-verdicts.json")
COLUMN = "main_verdict"
# Measured against the raw bytes rather than assumed; the sibling attack table differs.
DUMP = dict(indent=2, ensure_ascii=False, sort_keys=False)

RULINGS: dict[str, str] = {
    # -- ReviewResult, ruled by section 13 --
    "V01": (
        "CONFIRMED. Section 13 ships exactly this: reject emits all four keys with example_id and "
        "output null, exit 0. One frozen shape means one key set."
    ),
    "V02": (
        "CONFIRMED. Shipped Literal['accepted', 'corrected', 'rejected']. This is the ruled public "
        "behaviour change - baseline said 'resolved' for BOTH accept and correct, so the two "
        "decisions were indistinguishable without comparing outputs."
    ),
    "V03": (
        "CONFIRMED. Accept and correct differ in status and in which output is stored; each "
        "returned output is byte-identical to the stored final output, which is why R1 failed D12."
    ),
    "V04": "CONFIRMED. Shipped field tuple and order match; the instrument pins them.",
    "V05": (
        "CONFIRMED. Identity is proposal_id, two gaps for a shared input_hash, and page order is "
        "NOT asserted - D23 preserves order rather than fixing it."
    ),
    # -- confinement --
    "V06": (
        "CORRECTED. The owner set EXCLUDES _proposal_binding. Section 14 rules D02 attribution "
        "LEXICAL, and the singular wrapper carries no SQL, so it is not an owner. The shipped set "
        "is exactly seven: {_persist_proposal, handle, _fail_generation, request_status, "
        "revise_operation, _proposal_bindings, _write_proposal_request_status}. The battery encodes "
        "SEVEN, not the eight this row lists. The row's divergent=False is also wrong for the same "
        "reason; the ruling governs, not the flag."
    ),
    "V07": (
        "CONFIRMED. The instrument walks the whole module and attributes a module-level constant to "
        "its assigned name; a hoisted-constant positive control ships with it."
    ),
    "V08": (
        "CONFIRMED. Tokenizing is case-folded and whole-identifier. All three controls ship: FROM "
        "REQUESTS, quoted \"REQUESTS\", and requests_scope as a non-match."
    ),
    # -- adapted read paths --
    "V09": (
        "CONFIRMED, and this row names the exact defect the implementation hit. A first adapter "
        "hoisted the binding consistency check and PRE-EMPTED _validate_proposal_shape on every "
        "corrupt-ledger path, changing class, message and precedence for 20 tests. Every term moved "
        "back to its original position and reads row[...] rather than the binding record; "
        "get_proposal regained its bound_proposal_id term. Precedence is the obligation."
    ),
    "V10": "CONFIRMED. _ProposalFeed preserves the status_sequence feed, filter and isolation.",
    "V11": (
        "CONFIRMED. _ProposalBindingSet.total is the UNBOUNDED count for the pending selection "
        "alone, so the 10,001st row counts while the detail page stops at the cap."
    ),
    "V12": (
        "CONFIRMED, and the restraint is the point. D23 preserves opaque ledger order; asserting a "
        "documented semantic key would freeze an ordering the ledger never promised."
    ),
    "V13": "CONFIRMED. Stale-revision refusal covers accept and correct; reject still succeeds.",
    "V14": (
        "CONFIRMED against shipped payloads: artifact.counterexample {example_id, proposal_id}, "
        "then proposal.<status> {example_id, receipt_hash, reviewer, suspended_artifact_ids}. "
        "Neither carries request identity."
    ),
    "V15": (
        "CONFIRMED. _write_proposal_request_status is the SOLE review-path writer and keeps every "
        "predicate (partition, id, pending status, proposal_id) plus the rowcount check."
    ),
    "V16": (
        "CONFIRMED. Counts come from the P08 baseline census, so the battery pins a measured number "
        "rather than a design intention. Cardinality is the property that separates the shipped "
        "statement-owning adapter from a side lookup."
    ),
    "V17": (
        "CONFIRMED. Section 14 rules D24 unchanged: class plus path coverage is the whole "
        "obligation and new message text is free."
    ),
    "V18": "CONFIRMED. D21 collider fixtures carry the `_` LIKE metacharacter and case variants.",
    "V19": "CONFIRMED. Middle and last corruption both fail closed with no partial list.",
    "V20": (
        "CONFIRMED and it forced an amendment. Section 14 rules D20 SCOPE-RELATIVE: each path hides "
        "what lies outside the scope it NAMES. proposals(partition, *, status, after_sequence, "
        "limit) takes no operation, so a literal cross-operation reading made the shipped signature "
        "non-conforming while describing no reachable leak."
    ),
    "V21": "CONFIRMED. CLI show and list lose request_id and nothing else.",
    "V22": (
        "SCOPED. This is the unit's headline obligation and its event clause is over-broad. Section "
        "14 scopes D10 to the events the EIGHT OWNED SITES emit. Every review-path payload and the "
        "direct-route proposal.created are request-free as this row requires, but the handle "
        "route's proposal.created carries {\"request_id\": ...} and legitimately keeps it until "
        "M3.6a. Encode the scoped form; the literal form goes red against correct code."
    ),
    # -- extension rows --
    "X1": (
        "CONFIRMED AS AMENDED. Section 14 amends D01 to one named private READER plus at most one "
        "named private WRITER. D01's 'exactly ONE' was written while both spikes were read-only, "
        "and section 12 proved a read-only surface cannot confine a write. Two SQL-owning members "
        "is a consequence of the row having both sides, not a weakening; the wrapper is a third "
        "NAME but not a third owner."
    ),
    "X2": (
        "CONFIRMED. _ProposalIds, _ProposalFeed and _PendingProposals are pure value records. The "
        "adapter owning COMPLETE statements is what makes the M3.6b swap touch the adapter alone; a "
        "selection carrying SQL fragments would push the rewrite back into every consumer."
    ),
    "X3": (
        "CONFIRMED with one binding correction the battery must not undo. The shipped pin compares "
        "ANNOTATION TEXT, not resolved hints: typing.get_type_hints expands the recursive JSONValue "
        "alias one nesting level deeper under `| None` than without it, so an equality pin on "
        "resolved hints fails for a reason unrelated to shape. Sentinels compare by IDENTITY "
        "against dataclasses.MISSING, whose repr embeds an address and never matches as text."
    ),
    "X4": "CONFIRMED. Both converters stay pure; neither executes SQL nor names requests.",
    "X5": (
        "CONFIRMED, verified against the shipped module. Outcome's args are exactly (Resolved, "
        "ReviewRequired, InProgress, FallbackFailed, Rejected, ReconciliationRequired) with "
        "ReviewResult absent, and __all__ orders ReviewRequired before ReviewResult."
    ),
    "X6": "CONFIRMED. Write and event order is unchanged on every branch.",
    "X7": "CONFIRMED. One `now` still reaches every provenance edge; bounds are unchanged.",
    "X8": (
        "CONFIRMED. example_id alone proves the invariant only because reject returns null rather "
        "than omitting the key, which is exactly why section 13 ruled the null-key shape."
    ),
    "X9": "CONFIRMED. status_sequence still binds to the transition event's own sequence.",
    "X10": (
        "CONFIRMED. README's 'Reviewing a proposal' section and architecture step 4 ship this. D25 "
        "exists because a prior unit shipped a fully documented-in-code API that no human-facing "
        "surface named."
    ),
    "X11": "CONFIRMED. Both stale claims are gone; adapter and handle claims are untouched.",
    "X12": (
        "CONFIRMED. D27 is the rule that qualifying a claim in the contract does not qualify it in "
        "the prose, and this unit's request-free claim is exactly the kind that leaks unqualified."
    ),
    "X13": (
        "CONFIRMED, re-derived from the shipped module: SCHEMA_VERSION 2, SCHEMA 14580 UTF-8 bytes, "
        "sha256 5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77, and "
        "SCHEMA_FINGERPRINT equal to it. The schema cuts ONCE, at M3.6b."
    ),
    "X14": "CONFIRMED. The payload changed; no CLI grammar, option, default or exit class did.",
    "X15": (
        "CORRECTED, falsified against shipped code. proposal.created is payload={} on the two "
        "DIRECT routes (system.py:880) and payload={\"request_id\": request_id} on the HANDLE route "
        "(system.py:1262). Section 14 rules the handle payload retained under the same "
        "handle-lifecycle exception D10 already grants the lifecycle models, and the battery "
        "asserts it UNCHANGED so the exception is pinned rather than tolerated."
    ),
    "X16": "CONFIRMED. Every decision and corrected_output pair is validated pre-transaction.",
    "X17": (
        "CONFIRMED. _ProposalBinding carries proposal_id, partition, operation, operation_revision, "
        "input_hash, request_id, request_status and the proposal's own row, and is neither exported "
        "nor serialized."
    ),
    "X18": (
        "CONFIRMED. _proposal_binding returns None for zero rows so each consumer keeps its OWN "
        "NotFoundError - centralizing that would have rewritten error precedence, the same defect "
        "V09 records."
    ),
    "X19": (
        "CONFIRMED. This is the row that discriminates the shipped design from ALT-BINDING: a side "
        "lookup adds a second statement per consumer, and a 10,000-row feed must add zero per-row "
        "statements."
    ),
    "X20": "CONFIRMED. The adapter opens no connection and no nested transaction.",
    "X21": "CONFIRMED. Section 13 records the exact bytes for all three decisions.",
    "X22": (
        "SCOPED. Z50 is GROUNDS for choosing this adapter, not an acceptance property of M3.4. A "
        "probe that swaps the adapter's implementation for direct proposal columns tests M3.6b's "
        "design, and encoding it as a gate here freezes a future unit's schema decision. Keep it as "
        "a NON-BLOCKING differential probe whose failure is a report, never a red."
    ),
    "X23": (
        "CONFIRMED, and it is the D22 defect that sank ALT-PROJECTION: its function_report wrapped "
        "the constant in a subquery and materialized the whole partition before filtering by "
        "operation, where baseline filters r.operation inside the join."
    ),
    "X24": "CONFIRMED. Every lifecycle model keeps request_id; polling behaviour is unchanged.",
    "X25": "CONFIRMED. All three creation routes are adapter-equivalent for every read path.",
    "X26": (
        "ANSWERED by the section 14 D01 and D02 amendments read together. Attribution is LEXICAL, "
        "so the SQL-free wrapper is not an owner and D02's equality omits no D03-permitted name. "
        "Call-closure attribution is rejected on its own merits: it drags every public consumer "
        "back into the set and makes the obligation unsatisfiable by construction."
    ),
    "X27": (
        "CONFIRMED. Section 14 writes D12's missing definition: a PROJECTED VALUE is read from the "
        "ledger for that decision. Measured on the baseline return, output and example_id are "
        "ledger-derived and kept, source is the literal 'confirmed' on this path, and artifact_id "
        "defaults to None because review creates an example and never an artifact."
    ),
    "X28": (
        "CONFIRMED, and keeping the two vocabularies distinct is deliberate. The proposal side reads "
        "accepted/corrected; the private request row reads resolved. Translating either way would "
        "re-merge the two decisions section 13 just separated."
    ),
    "X29": "CONFIRMED. _ProposalFeed filters PROPOSAL status, never the bound request status.",
    "X30": (
        "CONFIRMED, re-derived at system.py:1483-1499. The map is enforced for every historical "
        "state - pending to pending, rejected to rejected, accepted and corrected to resolved - an "
        "unknown status raises IntegrityError('proposal has an unknown status'), and a mismatched "
        "pair raises IntegrityError('proposal and request states are inconsistent'). The check is "
        "guarded by `bound_proposal_id in row.keys()`, so non-adapted callers are unaffected."
    ),
    "X31": (
        "CONFIRMED, and the labelling requirement is the substance. STRICT tables cannot store most "
        "of these scalars, so an unlabelled probe would let a fabricated corruption masquerade as a "
        "real-ledger claim."
    ),
    "X32": (
        "ACCEPTED as an obligation and written into section 14. The projection cap bounds RETURNED "
        "DETAIL, never validation, and D22's counts are computed over the unbounded partition. A "
        "10,000-row page that looks valid while the 10,001st binding is missing is the exact "
        "failure a bounded instrument hides."
    ),
    "X33": (
        "CONFIRMED. This row is the unit's completeness check: all eight owned sites, each mapped to "
        "one ruled adapter member, with no site executing request SQL or taking another route."
    ),
    "X34": "CONFIRMED. Only the gap's request_id leaves; every sibling field is unchanged.",
    "X35": (
        "CONFIRMED. revise_operation and request_status are handle-lifecycle owners that keep their "
        "request access; they are in the permitted set because M3.6a deletes them, not because this "
        "unit blesses them."
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
        print(f"ABORT   id set differs. Unruled rows: {missing}. Ruling has no row: {extra}")
        return 1

    stale = [row["id"] for row in rows if row[COLUMN] != RULINGS[row["id"]]]
    if check:
        print(f"CHECK   {len(stale)} of {len(rows)} rows out of sync" if stale
              else f"CHECK   in sync, {len(rows)} rows ruled")
        return 1 if stale else 0

    for row in rows:
        row[COLUMN] = RULINGS[row["id"]]
    TABLE.write_text(json.dumps(payload, **DUMP) + "\n", encoding="utf-8")
    print(f"RULED   {len(stale)} of {len(rows)} rows updated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
