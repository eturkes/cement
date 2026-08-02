# M2 u3a design record — MAIN arbitration

Inputs: `.scratch/agents/spike-m2u3-a.md`, `-b.md`, `-c.md`, `-e.md`, `.scratch/agents/scout-m2u3.md`.
Baseline HEAD `f28780f`; gates green under MAIN's own run (134 tests OK, `uv build` OK).

## Decision 1 — identity/receipt timing cycle: alternative A

The u1 function entry hashes `promotion_hash` (`function.py:37-46`), created only inside `promote` and
binding `promoted_by` + commit-time `now` (`system.py:2498-2517`), so no pre-promotion value can equal
the post-promotion function hash. Accepted resolution:

- Function document ABI `cement-function-v1` -> **`cement-function-v2`**.
- Entry field `promotion_hash` -> **`entry_seal`**, a pre-promotion-computable digest.
- Ledger receipt `cement-promotion-v2` stays **byte-identical**; dispatch fast path untouched.

`cement-function-entry-seal-v1`, framed by the existing `_digest_strings` (`system.py:113-124`: SHA-256
over the label then each UTF-8 value prefixed by its unsigned 64-bit big-endian byte length), over
exactly these 14 ordered fields:

1. `artifact_id`  2. `artifact_hash`  3. `build_hash`  4. `policy_hash`  5. `evidence_snapshot_hash`
6. `support`  7. `reviewer_count`  8. `span_seconds`  9. `scope_hash`  10. `report_id`
11. `report_details_hash`  12. `report_test_set_hash`  13. `report_test_count`  14. `report_passed`

Integers = canonical base-10 text; `report_passed` = SQLite `0`/`1`. Deliberately excluded:
`promoted_by`, `promoted_at_us`, stored `promotion_hash`, report creation time. `verified_by` stays
bound inside `report_details_hash`. Seal is **recomputed on demand, never stored** -> no `SCHEMA`,
column, table, trigger, or `SCHEMA_FINGERPRINT` delta in u3a.

Rationale. A adds a digest; the alternatives subtract from or duplicate one.

- **B rejected** (pre-promotion-computable ledger receipt, `cement-promotion-v3` dropping promoter/time).
  Its own probe recorded `ACTIVE_PROVENANCE_SUBSTITUTION=SUCCEEDED`: an active row's `promoted_by` /
  `promoted_at_us` can be forged undetected. MAIN confirmed independently at `system.py:3198-3215` that
  today's `_validate_promoted` recomputes the receipt from `row["promoted_by"]` and
  `row["promoted_at_us"]`, so B removes a live forgery detection and then needs a mitigation that pulls
  u3b's set receipt into the trusted path. B also mandates a schema v2 reset (`test_reports.report_hash`)
  and silently opens then invalidates every existing v2 ledger if shipped under schema v1.
- **C rejected** (distinct candidate-set hash). C's own report concedes it: "strictly weaker than
  repeating the final function hash - new entries' `promotion_hash` values depend on future
  `promoted_by` + `promoted_at_us`, so one candidate digest can lead to multiple valid function hashes
  ... cannot retroactively make the operator repeat the final identity." C also costs five new digest
  domains against A's one. C's probe never ran (two provider deaths); it is rejected on its conceded
  design property, not on missing evidence.
- **A's measured cost**: 4 files, `+54/-25`, 134/134 green, `uv build` OK, no schema delta, one existing
  expectation changed (receipt corruption no longer moves the diagnostic function hash).

MAIN completed the under-binding audit C-2 left open. A's 14 seal fields are exactly
`cement-promotion-v2`'s 16 minus `promoted_by`/`promoted_at_us`, so the seal binds everything the
established receipt binds except the activation act itself; `scope_hash` covers partition/operation/
revision/canonical input, and `artifact_hash` covers the output mapping. Two materially different
verified sets colliding on one seal requires a SHA-256 collision. **No under-binding found.**

Accepted semantic consequence: function identity becomes *verified-content* identity, not activation
identity, so re-promoting identical content yields the same function hash. This is an improvement for a
portable exportable function object, and receipt corruption still fails `verify_function` P4 with
`passed=False` and `document=None` - already the contract documented on `FunctionVerification`
(`models.py:170-173`: "A diagnostic hash may survive a failed ledger check; consumers must gate on
`passed`"). ABI v2 is a real break of v1; reject v1 documents explicitly rather than parsing changed
content under the old label.

## Decision 2 — stale-draft eligibility: rule (c), selection-side

A literal `status='draft'` filter is unusable: `compile` keys reuse by `build_hash`, so added evidence
leaves a permanently poisoned older draft. Accepted rule, from spike E's 20-ledger probe set:

- Extract `_project_current_build(connection, operation_row, input_hash, input_json)` returning the
  compiler projection (canonical input/output, artifact document/hash/scope hash, policy JSON/hash,
  evidence snapshot hash, support, reviewer count, span seconds, final `build_hash`). `compile` consumes
  it to create/reuse; batch enumeration consumes it read-only. One helper, so the two cannot drift.
- Eligible row predicate: `partition=? AND operation=? AND operation_revision=<current> AND
  status='draft' AND input_hash=? AND input_json=? AND build_hash=projection.build_hash`.
- Require one canonical input per `input_hash` and at most one qualifying draft per `input_hash`; either
  duplicate condition raises `IntegrityError` and aborts the batch. Never "latest sequence wins" -
  `ORDER BY input_hash, sequence, id` is presentation only.
- Leave non-qualifying superseded drafts untouched.

Rejected: (a) report-all + disposition retires operator history and still needs a cardinality gate;
(b) compile-side supersession **fails a probed liveness case** - after a stale verified row is
re-verified and demoted back to `draft`, the literal batch stays poisoned. Rule (c) additionally lets
revocation requalify an older correct build with no recompilation (probed: `art_ff43f8d2...` selected
directly, where (a)/(b) had already retired it).

Evaluate eligibility inside the batch's own `BEGIN IMMEDIATE`; enumerating outside the lock is a TOCTOU
bug. No schema delta.

## u3a scope

**In.**
1. ABI v2 + `entry_seal` across `function.py`, `tests/test_function.py`, and `verify_function` P5.
2. `FUNCTION_ENTRY_SEAL_ABI` + a `_function_entry_seal(...)` helper in `system.py`.
3. `_project_current_build(...)` shared projection helper; `compile` refactored onto it.
4. Eligibility enumeration + duplicate-cardinality failure.
5. Batch verification: extract a connection-taking "verify one row + seal report" helper out of
   `verify`, then `System.verify_drafts(partition, operation, *, verified_by)` - one
   `BEGIN IMMEDIATE`, one savepoint per row, N sealed reports, existing per-row state transitions, N
   `artifact.verified` events, one aggregate result.
6. Result models + exports.
7. Tests.

**Out (u3b owns).** Prospective union with retained promoted rows; the prospective function hash and its
`expected_function_hash` gate; atomic set promotion, set receipt, membership tables and their schema
delta; legacy-path demotion. **Out (u4/u5).** CLI surface; every documentation edit.

u3a is deliberately not operator-complete: the operator-visible set hash arrives with u3b's union. u3a
still pins the cycle-breaking claim directly, at entry granularity.

## API decisions

- `System.verify_drafts(partition, operation, *, verified_by) -> DraftVerification`.
- `DraftVerification`: `passed: bool`, `operation_revision: int`, `entries: tuple[DraftEntry, ...]`,
  `skipped: tuple[dict[str, JSONValue], ...]`.
- `DraftEntry`: `artifact_id: str`, `input_hash: str`, `report: VerificationReport`,
  `entry_seal: str | None` (`None` exactly when that row failed).
- `skipped` records every current-revision draft that was not eligible, with a reason
  (`superseded-build`). Silent omission is the failure mode u2 was built to avoid.
- Authority: authorize **every selected artifact before opening the write transaction**, reusing the
  existing `artifact.verify` subject. No new subject - M3 is already approved to remove `authority()`,
  and the roadmap's O(N) complaint is about human-typed hashes, not machine policy calls.

## Failure semantics

- Evaluate every selected draft against one locked snapshot.
- Per-row savepoint contains artifact-local integrity/validation failures: sealed failing report + event,
  exactly as `verify` does today. One savepoint around the whole loop would erase earlier diagnostics.
- Row transitions unchanged: passing draft -> verified; failing draft stays draft.
- Aggregate `passed` = every selected row passed.
- Whole-batch abort with no partial writes on: authority denial, duplicate-eligible rows, missing
  canonical input, and any unexpected database/state/clock failure.

## Required test construction

Per `.agent/memory.md`: single-entry corruption proves a check can reject *a* row, not that it
quantifies over *all* rows. Therefore:

- Set-level probes corrupt the **middle or last** of >=3 entries.
- One probe per condition; never mutate two constants at once.
- One independent mutation per seal field (14 probes) - a compound mutation pins nothing.
- Mutation criterion binds: for every added check, some committed test must fail when that check's logic
  alone is deleted.
- Timing invariant, committed: an entry's `entry_seal` computed pre-promotion equals the seal recomputed
  post-promotion and equals the one `verify_function` uses.
- Atomicity: prove whole-batch abort by comparing a full table/schema dump before and after, not by
  row counts.
- `test_dispatch_uses_sealed_promotion_receipt_without_rehashing_tests` stays green and its source stays
  byte-identical.
- Explicit ABI policy test: a `cement-function-v1` document is rejected.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root.
