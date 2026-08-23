#!/usr/bin/env python3
"""Fill the MAIN-owned columns of m3u3-verdicts.json. Idempotent, replayable from the
teammate's committed table (wt/test-m3u3-1 @ 3f9a053).

    python3 .agent/decisions/m3u3-rule-verdicts.py [--check]

main_verdict   = MAIN's ruling on the divergence, judged against the SHIPPED code at 4b96e4d.
contract_action = what m3u3-contract.md does about it. `none` = shipped reading already governs.

Verdict prefixes:
  CONFIRMED  shipped reading is the ruled one
  SCOPED     the obligation as written overreaches; ruling narrows its domain
  CHANGED    the ruling altered shipped code
  ACCEPTED   the row found a real gap outside the code
  OPEN       ruled, discharge deferred to the S3 battery with a named obligation
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u3-verdicts.json")

RULINGS: dict[str, tuple[str, str]] = {
    # -- frozen public shape --
    "P01": (
        "CONFIRMED. Both signatures ship verbatim; `candidate` is keyword-only and required, and "
        "argument binding owns omission and unexpected keywords. No body-level validator exists.",
        "none",
    ),
    "P02": (
        "CONFIRMED. `type(result) is str`, not a subclass, for both methods. No new model.",
        "none - section 12 V-P02 already carries it",
    ),
    "P03": (
        "CONFIRMED. `submit_proposal` never reads `self.candidate_source`. A configured source that "
        "raises on every call cannot affect it, because the attribute is never touched.",
        "none - section 12 V-P03",
    ),
    "P04": (
        "CONFIRMED and EXTENDED by X09. `propose` snapshots the attribute into one local, so the "
        "`None` check and the single invocation bind the same object. Reassignment mid-call cannot "
        "split them. Unusable non-`None` configuration is contained, not pre-validated.",
        "section 5 publishes the snapshot rule and X09's containment boundary",
    ),
    "P05": (
        "CONFIRMED. Neither name is in `__all__` nor a module attribute; both are reachable only as "
        "`System` methods.",
        "none - section 12 V-P05",
    ),
    "P06": (
        "CONFIRMED, with the convention named. `handle` is byte-identical across the unit. The "
        "figure reproduces only under the whole-line span from `lineno` to `end_lineno` with "
        "trailing newlines stripped: 12,866 B / `1182130a2b3a`. `ast.get_source_segment` drops the "
        "four-space indent and gives 12,862 B / `c27e71b0b4c7`. 'AST slice' alone is ambiguous by "
        "exactly those four bytes.",
        "section 12 MEASUREMENT states the convention with both figures",
    ),
    # -- persistence footprint --
    "D01": (
        "SCOPED. The footprint quantifies over Cement's DECLARED SCHEMA tables. `events.sequence` is "
        "AUTOINCREMENT, so every success necessarily mutates `sqlite_sequence`; a reading covering "
        "every SQLite table is unsatisfiable and would fail against correct code.",
        "section 12 V-D01",
    ),
    "D02": (
        "CONFIRMED. The request row is written directly as `pending` with `proposal_id` set. No "
        "lease column is written and no generating state exists. Spelling a defaulted column in SQL "
        "was never mandated; the persisted row shape is.",
        "none",
    ),
    "D03": (
        "CONFIRMED. kind `proposal.created`, subject_type `proposal`, subject_id equal to the "
        "returned proposal ID, payload `{}`. Request identity is absent, which is the one delta "
        "from `handle`'s write.",
        "none",
    ),
    "D04": (
        "CONFIRMED. No caller-supplied identifier exists on either signature. Byte-identical content "
        "submitted twice writes two requests, two proposals, two events, and returns two distinct "
        "IDs.",
        "none",
    ),
    "D05": (
        "CONFIRMED. Exactly one invocation on success. Zero on every failure that precedes "
        "invocation. The persistence seam never re-invokes, so a revision-race failure after "
        "generation still counts one.",
        "none",
    ),
    "D06": (
        "CONFIRMED as STRUCTURAL, not behavioural. `_persist_proposal` contains all three writes and "
        "is the sole writer for both paths. Three shared row-level helpers would produce an "
        "identical footprint, so the pin is a call-graph spy, not a footprint comparison.",
        "none - section 12 V-D06",
    ),
    "D07": (
        "CONFIRMED as a TOTAL order needing one probe per ADJACENT edge: partition before operation, "
        "operation before input canonicalization, input before candidate canonicalization.",
        "none - section 12 V-D07",
    ),
    "D08": (
        "CONFIRMED but NOT load-bearing. The partition/input pair SPANS two edges and pins neither "
        "interior one. It is a sample of D07, which carries the obligation.",
        "section 4 records that D07's adjacent-edge probes subsume D08",
    ),
    "D09": (
        "SCOPED to a call rejected by ARGUMENT VALIDATION. Read wider it contradicts D12's read "
        "transaction, D21's operation lookup, and every failure that follows one source invocation.",
        "section 12 V-D09",
    ),
    "D10": (
        "CONFIRMED. Omitted `candidate` and an unexpected `source=` both raise Python's own "
        "`TypeError`. No shipped validator produces those; the exact signatures do.",
        "none",
    ),
    "D11": (
        "CONFIRMED, reading B: no Cement-held connection may be IN A TRANSACTION while the source "
        "runs. Idle open connections are permitted. `propose` invokes the source between two closed "
        "transactions, so the pin observes every connection Cement opens and carries a positive "
        "control.",
        "none - section 12 V-D11",
    ),
    "D12": (
        "CHANGED THE SHIPPED CODE. The pre-read/re-read guard belongs to `propose` ALONE. MAIN's "
        "first implementation gave both paths a pre-read plus a seam re-read for symmetry; a direct "
        "caller captures no revision, so a concurrent `revise_operation` raised `StateError` for a "
        "submission with no generation window to protect. SHIPPED: `expected_revision: int | None`; "
        "`submit_proposal` passes `None` and opens exactly ONE transaction.",
        "section 5 D12 scoped to the source path; section 12 V-D12 carries the full record",
    ),
    "D13": (
        "CONFIRMED. Row scope is mandatory; column projection is not. `SELECT revision` ships "
        "because it is the only consumed value. Reusing `System.operations()` stays rejected: it "
        "returns the whole partition.",
        "none - section 12 V-D13",
    ),
    "D14": (
        "CONFIRMED. `CandidateRequest.request_id` is retained and populated with the generated "
        "internal ID, transitional until M3.5b. `m3u3-map.json` S01 says M3.3 removes it; that row "
        "is STALE and superseded, not followed.",
        "section 12 HISTORY CORRECTION",
    ),
    "D15": (
        "SCOPED to zero SUBMISSION-ATTRIBUTABLE mutation. The revision-race fixture's own source "
        "commits an operation revision, so an unconditional 'ledger byte-identical' reading is "
        "false for a correct implementation. Isolated failures compare call entry to exit; injected "
        "concurrent mutation compares against the post-injection state.",
        "section 6 restates D15 in the attributable form",
    ),
    "D16": (
        "SCOPED to failures occurring BEFORE commit. A `commit()` that itself raises is one "
        "invocation and no reading can forbid it. Equivalent restatement: zero SUCCESSFUL "
        "submission commits on any failure path.",
        "section 12 V-D16",
    ),
    "D17": (
        "CONFIRMED. The clock source is mandatory; the call count is not. One `self._now()` inside "
        "the write transaction, shared by all three rows, is what ships - the M3.1 ruling that a "
        "clock read ahead of the authoritative plan can commit a row older than its own build.",
        "none - section 12 V-D17",
    ),
    "D18": (
        "CONFIRMED, reading B, with the mechanism named. `raise ... from None` INSIDE an `except` "
        "block leaves `__context__` populated with the adapter's exception, so reading A fails its "
        "own prohibition. The seam discards the exception, EXITS the handler, and raises there, "
        "where `__context__` is genuinely `None`. It keeps `from None` so both readings hold.",
        "none - section 12 V-D18",
    ),
    "D19": (
        "SCOPED to observations THROUGH the raised Cement exception: class, message, repr, cause, "
        "context, frames. The caller owns the adapter and can always instrument it directly; no "
        "library can hide that.",
        "section 12 V-D19",
    ),
    "D20": (
        "CONFIRMED. Every ruled failure raises. No sentinel, no `Outcome`, no `failed` request row, "
        "no `request.fallback_failed` event. Those belong to `handle`, which keeps them.",
        "none",
    ),
    "D21": (
        "CONFIRMED, and ORDERED by X03. `NotFoundError` precedes invocation, after one scoped read "
        "transaction. It does NOT precede the missing-configuration check: with "
        "`candidate_source is None` and an unregistered operation, `propose` raises `StateError` "
        "having opened zero transactions.",
        "section 5 publishes the four-step precedence (X03)",
    ),
    "D22": (
        "CONFIRMED, reading A, CHANNEL-LOCAL. 'Publishes' covers the return value and the event: "
        "return only `proposal_id`, emit payload `{}`. D23's `get_proposal` route is transitive "
        "discovery through an authorized reader and is not a violation.",
        "section 12 V-D22",
    ),
    "D23": (
        "SCOPED. Eight NAMED high-level seams in the union - not an exhaustive security count, and "
        "not eight per path. The DIRECT path never constructs a `CandidateRequest`. Authorized "
        "ledger access exposes every storage identifier by design.",
        "section 12 V-D23",
    ),
    "D24": (
        "CONFIRMED, reading A. 'Private' names a STORAGE ROLE the two signatures neither accept nor "
        "return. It is not privacy from adapters, from existing readers, or from the ledger.",
        "none",
    ),
    "D25": (
        "CONFIRMED. A method-scoped absence claim is permitted only when the same passage states "
        "that schema v2 retains the row and existing surfaces expose its ID. README and "
        "architecture.md now carry exactly that pairing. Unqualified removal claims stay banned.",
        "section 11; the executable prose battery is D30/S3 work",
    ),
    "D26": (
        "SCOPED and MEASURED. 635 + N DISCOVERED tests, zero failures, zero errors, and zero skips "
        "AMONG THE TESTS M3.3 ADDS - a skipped test increments the count and still prints OK. "
        "Measured 668 tests, 0 failures, 0 errors, 206.045 s.",
        "section 12 V-D26",
    ),
    "D27": (
        "CONFIRMED. The three exact count assertions are tripwires that force acknowledgement of "
        "capability growth. `violations == []` is the load-bearing read-only assertion. Both stay.",
        "none",
    ),
    "D28": (
        "CONFIRMED with the reading STRENGTHENED. Updated totals alone do not 'record each site by "
        "method name' - an interior site move preserves every count. SHIPPED: 17 -> 18 read sites, "
        "16 write sites, PLUS by-method-name assertions naming `_submission_revision` and "
        "`_persist_proposal`, so relocation no longer passes.",
        "none - the shipped battery satisfies the strengthened reading",
    ),
    "D29": (
        "CONFIRMED. The scanner and `violations == []` are untouched. `reached_helpers` stays at its "
        "baseline 12: the ruled design adds no helper the scanner reaches.",
        "none",
    ),
    "D30": (
        "OPEN, deferred to S3. Closure is not yet mechanical: the obligation grader has no published "
        "command and the mutation corpus is unenumerated. The attack reported this correctly.",
        "S3 battery must publish the grader command, the enumerated predicate/mutant set, and a "
        "committed red per mutant, before the unit closes",
    ),
    "D31": (
        "CONFIRMED, reading A. The docstring is rewritten off supervised fallback. Class, name, "
        "module, and inheritance are preserved.",
        "none",
    ),
    "D32": (
        "CONFIRMED, reading B. Both docstrings state the three-row footprint and the no-idempotency "
        "cost. `submit_proposal` states that it never invokes the source; `propose` states adapter "
        "execution outside every transaction. Each lists the exact errors it raises.",
        "none",
    ),
    "D33": (
        "CONFIRMED and REFINED. `cheap`, `safe-to-retry`, and `deduplicated` are banned as submission "
        "guarantees. `request-free` is also avoided in shipped prose - it is predictably overbroad, "
        "because D14 retains a real request row. The unit's roadmap name keeps the phrase; no "
        "shipped file uses it. Scan of README, docs/, and src/ returns zero hits for all four.",
        "section 11 carries the ban and the scan",
    ),
    "D34": (
        "PARTIAL at S2, now DISCHARGED for prose. `docs/adapter-protocol.md` carried the only two "
        "sentences the new surface falsified; both are route-qualified. X11 found the harder half: "
        "README and architecture.md named NEITHER method. Both now publish the surface, and "
        "threat-model.md's request-ID idempotency obligation is route-scoped.",
        "D34's file list gains docs/adapter-protocol.md; the executable prose battery is S3 work",
    ),
    # -- error text table --
    "T01": (
        "CONFIRMED. A fresh `CandidateSourceError('candidate source failed')`, raised outside the "
        "handler with `from None`. The source's own instance is never re-raised, so its message and "
        "frames cannot survive.",
        "none",
    ),
    "T02": (
        "CONFIRMED. Every non-`CandidateSourceError` `Exception` normalizes to the identical fresh "
        "error and text, including other `CementError` subclasses and `ExceptionGroup`. `except "
        "Exception` is the exact catch; X10 rules the `BaseException` boundary above it.",
        "none",
    ),
    "T03": (
        "CONFIRMED. `candidate_source is None` after argument validation raises exact "
        "`StateError('candidate source is not configured')` with zero source calls and ZERO "
        "transactions - the check precedes the revision read (X03).",
        "none",
    ),
    "T04": (
        "CONFIRMED for `propose`. The in-write scoped revision is compared against the captured "
        "`CandidateRequest.operation_revision`. `submit_proposal` passes no expectation, so this row "
        "is unreachable from the direct path by design (V-D12).",
        "section 7 notes the row is source-path only",
    ),
    "T05": (
        "CONFIRMED for both methods. `NotFoundError('operation is not registered in this "
        "partition')`. `propose` raises it from the pre-read; `submit_proposal` raises it from "
        "inside its single write transaction, which is why its footprint is still zero.",
        "none",
    ),
    "T06": (
        "CONFIRMED, reading A, for EVERY reachable validator branch rather than one sample. The "
        "existing `_name` and canonicalization texts are unchanged; the expected matrix is generated "
        "from the baseline helpers, not transcribed.",
        "none",
    ),
    # -- extension rows, test-m3u3-1 --
    "X01": (
        "CONFIRMED, reading A, and it is what ships. `_canonical_candidate` requires "
        "`type(candidate) is Candidate`, converts a non-mapping provenance into "
        "`ValidationError('candidate provenance must be a mapping')` via a guarded `dict()` catching "
        "`(TypeError, ValueError)`, and requires a JSON object. Caller-owned output keeps the "
        "existing canonicalization texts. Every rejection precedes ledger access.",
        "section 7 gained four candidate rows; section 4 places candidate validation last",
    ),
    "X02": (
        "CONFIRMED, reading A, and it is what ships. `_canonical_candidate` runs INSIDE `propose`'s "
        "`try`, so a malformed RETURNED candidate normalizes to "
        "`CandidateSourceError('candidate source failed')` exactly like a raised adapter exception. "
        "Containment must not depend on whether the adapter raised or returned; a mapping whose "
        "`items` raises with a secret is the case that settles it. Validation runs outside every "
        "transaction.",
        "section 7 gains the malformed-return condition as a published row",
    ),
    "X03": (
        "CONFIRMED, reading A, and it is what ships. Order: arguments, `candidate_source is None`, "
        "operation lookup, invocation. Missing configuration therefore costs ZERO transactions, "
        "which is what the split spike measured. Reading B would trade that for a `NotFoundError` "
        "the caller cannot act on while unconfigured.",
        "section 5 publishes the four-step precedence",
    ),
    "X04": (
        "CONFIRMED, reading A, and it is what ships. `CandidateRequest.input` receives "
        "`input_json.value`, the canonicalizer's detached structure. Persistence reuses "
        "`input_json.text` and `.digest`, computed before invocation, so an adapter that mutates "
        "`request.input` changes neither the stored bytes nor the caller's object.",
        "section 8 records the detachment and the single-snapshot reuse",
    ),
    "X05": (
        "CONFIRMED, reading B, and MEASURED clean. `SCHEMA_VERSION == 2`; `SCHEMA` is 14,580 bytes "
        "with SHA-256 `5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77`; "
        "`SCHEMA_FINGERPRINT` equals that digest. Version-only checking would pass a whitespace DDL "
        "edit, so byte identity is the obligation.",
        "section 1 gains the schema pin with its three figures",
    ),
    "X06": (
        "CONFIRMED, reading B, and MEASURED clean against the unit-entry baseline `f9b9755`: "
        "`cli.py`, `_command_supervisor.py`, and `example_adapter.py` are byte-identical at HEAD. "
        "The row's own probe is sound but needs the baseline stated - measured against an M2-era "
        "commit, `cli.py` shows a false DIFF that is entirely M2.4 work.",
        "section 1 gains the byte pin AND names f9b9755 as the baseline",
    ),
    "X07": (
        "ACCEPTED, and already fixed at 719b48a. `docs/adapter-protocol.md` held the only two "
        "sentences the shipped surface falsified. Both are now route-qualified: `handle` stores "
        "legacy `fallback_failed` state, `propose` raises `CandidateSourceError` and writes no "
        "request row, no proposal, and no event, and never retries.",
        "D34's normative file list gains docs/adapter-protocol.md",
    ),
    "X08": (
        "ACCEPTED as a COMPLETENESS defect in the contract, with no code effect. Section 7 is a "
        "submission-DOMAIN taxonomy. Reachable clock and Store failures inherit their existing "
        "`StateError`/`IntegrityError` texts and were never respecified. Claiming exhaustiveness "
        "while those are unlisted is the error.",
        "section 7's heading is qualified: submission-domain errors plus inherited infrastructure "
        "errors",
    ),
    "X09": (
        "RULED, and the shipped behaviour DIVERGES from the row's recommendation deliberately. "
        "Shipped: snapshot once, `None` -> T03 `StateError`, and every other unusable configuration "
        "- missing `propose`, non-callable `propose`, a descriptor that raises - contained as "
        "`CandidateSourceError`. A pre-flight `callable()` check is unsound under descriptors and "
        "`__getattr__`, duplicates the failure the invocation itself produces, and would EXECUTE the "
        "descriptor to test it. A descriptor can carry secrets, so containment must cover it. "
        "Footprint stays zero: one read transaction, no rows.",
        "section 5 publishes the containment boundary for non-None unusable configuration",
    ),
    "X10": (
        "CONFIRMED, reading B, and it is what ships. `except Exception` is exact: "
        "`KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and cancellation propagate unchanged, "
        "because swallowing process control is worse than any containment gain. Footprint is still "
        "zero - nothing is written before the seam.",
        "section 7 publishes the BaseException boundary above T02",
    ),
    "X11": (
        "ACCEPTED, and it was a REAL OPEN GAP. Before this ruling, README.md matched only the "
        "adapter snippet's `def propose(self, request)`, and neither `docs/architecture.md` nor "
        "`docs/threat-model.md` named either method. Stale-claim cleanup does not publish a new "
        "public surface. FIXED: README gains an 'Explicit proposal submission' subsection with both "
        "signatures, the three-row cost, the no-idempotency statement, the error list, and the "
        "D25-compliant request-row caveat; architecture.md states that both methods enter the "
        "pipeline at step 3 alone; threat-model.md route-scopes its request-ID idempotency "
        "obligation.",
        "D34 is discharged for prose; the executable prose battery stays S3 work",
    ),
    "X12": (
        "CONFIRMED, reading B, as the OBLIGATION; discharge is OPEN. The seam is structurally atomic "
        "- one `transaction(write=True)` block containing all three INSERTs - so any interior raise "
        "rolls back by construction. That is an argument, not a measurement. D15 can currently pass "
        "on pre-write failures alone, which is exactly the hole the row names.",
        "S3 battery must ship the rollback matrix: inject after each of the request, event, and "
        "proposal writes, and assert taxonomy, counts, file digest, and zero successful commits",
    ),
}


def main() -> int:
    check = "--check" in sys.argv
    document = json.loads(TABLE.read_text())
    rows = document["rows"]
    ids = [row["id"] for row in rows]

    missing = [i for i in ids if i not in RULINGS]
    extra = [i for i in RULINGS if i not in ids]
    if missing or extra:
        print(f"MISSING RULINGS: {missing}\nUNKNOWN IDS: {extra}")
        return 2

    for row in rows:
        verdict, action = RULINGS[row["id"]]
        row["main_verdict"] = verdict
        row["contract_action"] = action

    rendered = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if check:
        same = rendered == TABLE.read_text()
        print(f"IN-SYNC: {same}")
        return 0 if same else 1

    TABLE.write_text(rendered)
    unfilled = sum(
        1 for row in rows for key in ("main_verdict", "contract_action") if row[key] == "unknown"
    )
    print(f"ROWS: {len(rows)}\nRULED: {len(RULINGS)}\nUNFILLED-MAIN-CELLS: {unfilled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
