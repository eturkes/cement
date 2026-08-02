# M2 u3b design record — MAIN arbitration

Inputs: `.scratch/agents/spike-m2u3b-members.md`, `-refs.md`, `-blob.md` (three independent full-design
spikes, each with a staging prototype + real-pipeline probes). Baseline HEAD `9e09f4c`; gates green under
MAIN's own run (162 tests OK, `uv build` OK). Every spike's staging tree independently reached 162 tests
OK + `uv build` OK, so all three costed designs are buildable, not sketches.

Council convergence (≥2 independent spikes) settled: schema strategy, API shape, union semantics, TOCTOU
closure, transaction order, receipt label, verifier placement, legacy-path treatment, event projection,
and the sizing verdict. MAIN arbitrated the one genuine fork (membership representation) and two 2-vs-1
naming/mechanism splits.

## Decision 0 — unit split: u3b → u3b1 + u3b2

All three spikes independently estimated full-unit implementation at **210-260K/240K** (members 215-235K,
refs 210-230K, blob 220-260K) and all three independently proposed the **same seam**: persisted set
promotion core, then verifier integration + historical reconstruction + mutation-bound coverage. Three
independent estimates converging above the one-window aim is decisive evidence, not a preference.

Split, following the recorded u3 → u3a/u3b precedent:

- **u3b1** = schema + models + union + manifest + expected-hash gate + atomic promotion transaction +
  set receipt + membership rows + projected event.
- **u3b2** = `verify_function` P6 receipt binding + historical reconstruction/export + the independent
  mutation sweep across both.

Scope is staged, never narrowed: every element of the roadmap's u3b line lands across the two units.
The seam is a real interface — u3b1 writes the immutable `(receipt, memberships)` pair, u3b2 reads it.

## Decision 1 — membership representation: **reference-only** (`refs`)

Membership rows carry references plus sealed identity: `receipt_id, ordinal, function_hash, artifact_id,
report_id, input_hash, entry_seal`. Entry content stays in exactly one authoritative place — the
`artifacts` / `test_reports` rows — and the `cement-function-v2` document is rebuilt by join.

Rejected, with the evidence that decided it:

- **blob** (one receipt row carrying the canonical entry list, no membership table) — **self-rejected on
  its own measurements**, which is exactly what the KISS baseline was dispatched to establish. At the
  admitted 50,000-entry ceiling: 67,050,229 stored bytes in one row (58,552 bytes under the 64 MiB
  document bound), 29.3 s parse, 867 MB Python peak / 1.90 GiB RSS, 16,386 × 4 KiB pages, and a
  structurally unindexable membership query (`json_each` scan, 194 ms per receipt, linear in history).
  Its verdict: "membership table necessary for indexed history + bounded processing." Accepted.
- **members** (membership rows carrying the full entry payload) — rejected because **blob's measured
  amplification curve applies to it unchanged**. members duplicates `input_json` + `output_json` per row,
  so it inherits blob's 1,341 bytes/entry snapshot cost per promotion; members' own weakness #1 concedes
  it ("a near-64 MiB function promoted 100 times approaches 6.4 GiB"), and blob measured the pathological
  case at 1.525 TiB for one-entry-at-a-time growth to 50K. members fixes blob's *query* and *streaming*
  weaknesses but not its *storage* weakness. refs is the only alternative that removes it (~250 vs ~1,341
  bytes/row).

Why refs' decisive weakness does not bind here. members' unique advantage is recovery after authoritative
rows are deleted or rewritten. Under today's ledger that path is closed:

- Artifact build fields and report rows are schema-immutable by committed trigger (`store.py:309`,
  `store.py:321`); ordinary API paths change *status*, never content.
- `PRAGMA foreign_keys = ON` is set on every connection (`store.py:432`), so the membership FKs to
  `artifacts(id)` and `test_reports(id)` make retention **structurally enforced**, not merely contractual
  — refs' own report understated this.
- refs probed reconstruction after supersession, after operation-revision retirement, and after every
  member was revoked: the old receipt rebuilt byte-identically in all three
  (`HISTORICAL_AFTER_SUPERSESSION=True`, `HISTORICAL_AFTER_REVISION_RETIREMENT=True`,
  `HISTORICAL_AFTER_ALL_MEMBERS_REVOKED=rebuilt:True`).
- members' snapshot is export-complete but **not audit-complete** (its weakness #5): it omits artifact
  JSON, report details JSON, and child tests, so full historical *verification* replay still needs the
  live rows. It buys partial recovery at ~5x storage plus a second source of truth.

Project rule alignment: `CLAUDE.md` Engineering requires deduplication; members' duplicate truth needs an
extra divergence check to stay honest, which is complexity purchased to police complexity.

**Recorded consequence + standing invariant.** Artifact build fields and bound report rows referenced by
`function_memberships` are permanently retained. Any future retention/GC/erasure/compaction feature must
preserve rows referenced by membership, or historical reconstruction breaks. This is the one condition
that would falsify the choice; it is now an explicit ledger invariant rather than an implicit assumption.

## Decision 2 — schema strategy: **pre-1.0 ledger reset**, no migration runner

Unanimous across all three spikes, each with its own probe. Consistent with the roadmap's recorded M3
stance ("Schema fingerprint bumps; no migration path pre-1.0") and with project version `0.1.0`.

Mechanism, arbitrating the 2-vs-1 split: **bump `SCHEMA_VERSION` 1 → 2 *and* let `SCHEMA_FINGERPRINT`
change** (members' mechanism, over refs/blob's fingerprint-only change). Leaving `SCHEMA_VERSION = 1`
while the schema text changes makes one version label denote two different schemas. Both gates fail
closed, but the version check produces the readable diagnostic:

- version check `store.py:451-454` → `database schema 1 is unsupported; expected 2`
- fingerprint check → `database schema fingerprint mismatch`
- `schema_metadata` key is `f"schema-v{SCHEMA_VERSION}"` (`store.py:371,470`), so the bump moves the key
  and both mechanisms stay coherent.

Probed behavior on a populated `9e09f4c` ledger reopened under the delta: raw SQLite bytes survive intact
(`user_version=1`, all `cement-promotion-v2` receipts unchanged), and the runtime refuses the file before
any mutation. No migration runner, no downgrade path.

## Decision 3 — API surface

```python
System.inspect_function_promotion(partition, operation) -> FunctionPromotionManifest
System.promote_function(partition, operation, *, expected_function_hash, promoted_by) -> FunctionSetPromotion
```

`inspect_function_promotion` wins 2-1 over `plan_function_promotion`. Read-only: one
`Store.transaction(write=False)`, no authority call, no clock, no ID allocation, no event.

Models (`models.py`), matching the existing frozen-dataclass style:

```text
FunctionPromotionEntry = artifact_id, input_hash, artifact_hash, output_hash, entry_seal,
                         disposition('retained'|'candidate'), replaces_artifact_id: str|None
FunctionPromotionManifest = operation_revision, function_hash, text, document,
                            entries: tuple[FunctionPromotionEntry, ...],
                            skipped: tuple[dict[str, JSONValue], ...]
FunctionSetPromotion = receipt_id, receipt_hash, function_hash, operation_revision,
                       member_artifact_ids, candidate_artifact_ids, retired_artifact_ids,
                       promoted_at_us
```

Manifest ABI `cement-function-promotion-manifest-v1`; `manifest.text` = canonical JSON of scope +
`function` (the complete `cement-function-v2` value) + `function_hash` + per-entry disposition/replacement
descriptors + `skipped`. Determinism required and probed: no clock, actor, nonce, ID allocation, or
database row order enters manifest bytes; entries sort ascending `input_hash`; enumeration sorts
`(operation_revision, input_hash, sequence, id)`. refs observed `MANIFEST_BYTES_IDENTICAL=True` across
independent `System` instances.

The operator inspects `manifest.document` (every canonical input/output plus governance digests), then
disposition/replacement/skipped, then copies `manifest.function_hash` into `expected_function_hash`.

## Decision 4 — union semantics

Unanimous across all three spikes.

- **Retained**: enumerate **all** `status='promoted'` rows for `(partition, operation)` — never filter by
  revision in SQL. A promoted row whose `operation_revision` ≠ current revision is corruption and raises
  `IntegrityError`; it is never silently omitted. This preserves u2's deliberate stale-row posture.
  Each retained row must additionally pass full report validation (full child-set rehash),
  `_artifact_from_row`, `_validate_promoted`, current policy hash/JSON equality, and unique-input
  cardinality.
- **Candidates**: current-revision `status='verified'` rows that reconstruct under
  `_project_current_build` — exact `input_json` **and** `build_hash` match, one canonical input per
  digest, one qualifying candidate per digest, bound report passing + sealed. u3a's reconstruction rule
  applies unchanged; literal status filtering stays rejected.
- **Union**: `U = (retained \ keys(candidates)) ∪ candidates`, keyed by `input_hash`. Equal digest with
  unequal canonical input aborts as an integrity collision.
- **Non-qualifying** current-revision verified rows are reported in `manifest.skipped` with a reason
  (`superseded-build`), never silently omitted — u2's founding rule.
- Shrinkage happens only through a prior explicit audited act (revocation, suspension, revision) whose
  effect the operator sees in the manifest and repeats in the hash.

## Decision 5 — transaction sequence + membership sealing

One `BEGIN IMMEDIATE`, exact order:

1. Locked operation/policy revalidation.
2. Locked re-enumeration of retained + candidate rows with full validation and replay.
3. Rebuild union + `cement-function-v2`; compare plan identity, then `expected_function_hash`. **No write
   precedes this comparison.**
4. Bulk-retire predecessors sharing a candidate's `input_hash`: `promoted → retired`,
   `promotion_hash = NULL`, reason `replaced by function promotion`. Assert exact affected-row counts.
5. Bulk-activate candidates `verified → promoted` with **unchanged** `cement-promotion-v2`, one actor and
   one timestamp across the set. Guard each `UPDATE ... WHERE status='verified'` to exactly one row.
6. Insert membership rows.
7. Insert the receipt row — **this is the physical seal**.
8. Insert the projected `function.promoted` event.
9. Commit.

Membership-before-receipt (refs) is adopted over receipt-before-membership (members). Rationale: the seal
trigger becomes `WHEN EXISTS (SELECT 1 FROM function_receipts WHERE id = NEW.receipt_id)` — O(1) per
insert. members' cardinality trigger counts existing rows per insert, which is O(N²) over 50,000 members
(~2.5e9 row visits). Exact cardinality is instead enforced by `member_count` in the receipt, checked at
verification time. The membership → receipt FK is `DEFERRABLE INITIALLY DEFERRED` so the inverted physical
order validates at commit.

Retire-before-activate is required by the partial unique index `one_promoted_exact_scope`
(`store.py:243-245`): a same-input replacement must never leave two promoted rows visible, even
transiently. All three spikes converge here.

Rollback: any digest/validation/state/rowcount/constraint/trigger/event failure rolls back retirement,
activation, memberships, receipt, and event. Proven by full `sqlite3.Connection.iterdump()` equality, not
row counts (`LATE_ABORT_FULL_DUMP_EQUAL=True`, and blob's byte-identical 123-line dump hash).

## Decision 6 — authorization + TOCTOU closure

1. Read preflight computes the complete plan.
2. Authority is checked **outside** the write lock. Reuse the existing per-artifact `artifact.promote`
   subject for every prospective member — no new authority action, since M3 is already approved to remove
   `authority()` entirely.
3. `BEGIN IMMEDIATE`.
4. Full replan under the lock.
5. **Plan-identity recheck** (adopted from members): the locked revision, candidate ID set, and member ID
   set must equal what was authorized, else `StateError("function promotion candidates changed during
   authorization")`. The expected-hash gate would catch this derivatively, but an authorization guarantee
   must not rest on a digest-coincidence argument — this makes it structural.
6. `expected_function_hash` gate: malformed digest → `ValidationError`; well-formed mismatch →
   `ConflictError`.
7. Writes begin.

Probed: retained-row revoked between manifest and promote → `ConflictError` + dump-identical; candidate
loses eligibility at lock time → `ConflictError`/`StateError` + dump-identical; wrong expected hash →
`ConflictError` + dump-identical.

## Decision 7 — receipt + membership ABI

Set receipt label **`cement-function-promotion-v1`** (2-1 over `cement-function-promotion-receipt-v1`),
framed by the existing `_digest_strings` (label, then each UTF-8 value prefixed by its unsigned 64-bit
big-endian byte length; integers as canonical base-10 text). Exactly these 14 ordered fields:

1. `id` 2. `partition` 3. `operation` 4. `operation_revision` 5. `policy_hash` 6. `function_hash`
7. `membership_hash` 8. `member_count` 9. `candidate_artifact_ids_hash` 10. `candidate_count`
11. `retired_artifact_ids_hash` 12. `retired_count` 13. `promoted_by` 14. `promoted_at_us`

Membership digest label **`cement-function-membership-v1`**, over rows in ascending `input_hash`/ordinal,
each contributing `ordinal, artifact_id, report_id, input_hash, entry_seal`.

ID-list digests reuse the existing `cement-id-list-v1` over lexically sorted full ID tuples.

Binding relationships:

- `cement-function-v2` = portable **verified-content** identity; excludes activation actor/time (u3a).
- `cement-promotion-v2` stays **byte-identical** and keeps per-entry activation provenance, including its
  dispatch fast path. Retained artifacts keep their existing receipt.
- `cement-function-promotion-v1` = **set activation** provenance: binds the final function identity, the
  authoritative membership digest, the candidate and retirement transition sets, actor, and commit time.
- Re-promoting identical content preserves `function_hash` but creates a distinct set receipt.
  `function_hash` is therefore indexed, not unique.

## Decision 8 — `verify_function` integration (u3b2)

**Append** a sixth ordered check `persisted-function-receipt` after the existing P5 (2-1 over renumbering
P1-P5 — renumbering churns u2's committed check-vector assertions for no gain). P5 keeps asking "do the
live promoted rows reconstruct this function?"; P6 asks "does an immutable persisted receipt bind that
same function?"

- Nonempty promoted set with no current-revision receipt → **fail**. This is the legacy path's demotion.
- Empty set with no receipt → vacuous pass, preserving u2's empty-set semantics.
- Latest receipt selected by descending `sequence` for the current revision.

## Decision 9 — legacy per-entry path

`promote(partition, artifact_id, *, scope_hash, promoted_by)` changes **nothing**: no signature, docstring,
flag, event field, receipt, or CLI change. Unanimous across all three spikes.

Demotion is purely semantic: a nonempty set grown only through legacy promotion has no set receipt, so
u3b2's P6 fails aggregate verification until the operator inspects the union and runs a zero-candidate
`promote_function` to checkpoint it under an explicitly repeated hash. Zero-candidate promotion is
explicitly legal and is the checkpoint mechanism. u4 owns CLI preference; u5 owns documentation.

## Decision 10 — audit/event payload

Event `function.promoted`, subject type `function`, subject id `receipt_id`. Projected, never enumerated:
counts + first ≤100 lexically sorted IDs + `cement-id-list-v1` digest over the complete tuple, for each of
member / candidate / retired, plus `function_hash`, `receipt_hash`, `receipt_id`, `promoted_by`.

Worst-case measured against the 262,144-byte cap: 59,859 bytes (refs, three 100-ID previews at maximum
192-byte IDs and a 256-byte actor) — the most adversarial of the three measurements, 202,285 bytes under
cap. Membership rows stay authoritative; event previews are audit navigation only.

## u3b1 scope (this unit)

**In.**
1. Schema delta in `store.py`: `function_receipts` + `function_memberships` tables, indices, immutability
   triggers, the O(1) membership seal trigger; `SCHEMA_VERSION` 1 → 2.
2. Receipt + membership digest helpers and ABI constants in `system.py`.
3. Shared retained/candidate/union projection, reusing u3a's `_project_current_build`.
4. `System.inspect_function_promotion` + the manifest ABI and its determinism.
5. `System.promote_function`: authorization, `BEGIN IMMEDIATE`, locked replan, plan-identity recheck,
   expected-hash gate, bulk retire/activate, membership + receipt write, projected event.
6. Models + `__init__.py` exports.
7. Tests.

**Out (u3b2).** `verify_function` P6; historical reconstruction/export API; the independent mutation
sweep. **Out (u4/u5).** CLI surface; every documentation edit.

## Required test construction

Binding rules from `.agent/memory.md`, all of which cost u2/u3a real defects:

- Set-level probes corrupt the **middle or last** of ≥3 entries. A single-entry probe proves a check can
  reject *a* row, not that it quantifies over *all* rows.
- One probe per condition; never mutate two constants at once.
- One independent mutation per receipt field (14 probes). Where the outer hash is recomputed over tampered
  content so the field check is the sole rejecter, assert that; where checks are logically entangled,
  assert the complete ordered vector plus the detail of the check under test, and never report a
  derivative check as passing to manufacture isolation.
- Mutation criterion binds: for every added check, some committed test must fail when that check's logic
  alone is deleted.
- Atomicity is proven by full `iterdump()` schema+data comparison, not row counts.
- Determinism: `manifest.text` byte-identical across independent `System` instances on one snapshot.
- Timing: the prospective hash computed pre-promotion equals the hash `verify_function` reports after.
- `test_dispatch_uses_sealed_promotion_receipt_without_rehashing_tests` stays green with byte-identical
  source; `cement-promotion-v2` stays byte-identical.
- **Retarget, do not delete**, `tests/test_system.py:1795`
  `self.assertNotIn("CREATE TABLE function", ...)`. Its enclosing test proves `verify_function` persists
  nothing. The schema now legitimately contains `CREATE TABLE function_receipts`, so the assertion becomes
  `assertNotIn("INSERT INTO function_receipts", ...)`, preserving the intent (verification creates no
  persisted identity) while accommodating the table. The surrounding `assertEqual(before, after)`,
  `transaction.assert_called_once_with(write=False)`, `authority.assert_not_called()`, and
  `clock.assert_not_called()` assertions all stay.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root.
