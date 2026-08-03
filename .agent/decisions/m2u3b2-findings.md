# M2 u3b2 review findings — MAIN arbitration

Reviewers: `rev-m2u3b2` (correctness/spec/claim audit, diff-blind phase 1, peak 85% 203K) and
`rev2-m2u3b2` (independent 125-mutant catalogue over the joined u3b1 surface, peak 79% 190K), plus
`rev2b-m2u3b2` (fresh successor sweeping the u3b2 surface). Landed implementation: `impl-m2u3b2`
(peak 90% 216K), suite 230 → 260, MAIN's own gate rerun green.

Verdict: **no production defect in the unmutated landed code.** One production resource-regression (A1)
and fifteen committed-test gaps, where a mutant broke a required guarantee while the suite stayed green.

Claim audit (rev, verified independently): the implementer's 92/92 author sweep is literally accurate
(92 rows, 92 unique names, 92 kills, 92 liveness proofs) and is an honest floor, not closure; all 28
pre-existing `_assert_function_checks` call sites retain their original P1-P5 booleans and append P6, with
zero removed tests; P6 is emitted in both the normal and aggregate vectors; historical reconstruction is
status-independent; byte identity and determinism hold. The implementer's contested omission — skipping
duplicate/type checks that "no valid opened ledger can violate" — was probed directly against schema v2
and **cleared**: `STRICT` storage plus PK/UNIQUE constraints reject those inputs before the core sees
them, and surviving duplicates still reach `build_function`'s duplicate-input rejection.

## Batch 1 — aggregate cost, enumeration quantification, read-only breadth

A1 — MEDIUM, production, reproduced by rev + confirmed by MAIN reading `system.py:2129-2185`. The
aggregate fast-fail path (`entry_count > FUNCTION_MAX_ENTRIES`) calls
`_persisted_function_receipt_check(document=None)`, which reconstructs and fully validates the latest
receipt *before* testing `document is None`. A ledger with a max-size valid checkpoint plus one legacy
per-entry promotion therefore materializes up to 50,000 memberships, artifacts, reports, full test child
sets and the portable document, even though the guard already decided the live set is invalid. The count
guard stops bounding verification work. Acceptance: with a 3-member receipt, a fourth legacy member and
limit 3, a `_reconstruct_function_receipt` that raises when called must not be called, and the vector must
still be the six ordered checks with P6 failed.

A2 — MEDIUM, test gap, reproduced by rev + **replayed by MAIN**: `LIMIT 1000` inserted into the
membership enumeration (`system.py:1959`) imports live and leaves all 260 tests green. u3b2 owns joined
history up to `FUNCTION_MAX_ENTRIES=50_000`, and the committed reconstruction/P6 tests use three members;
the existing 1,001-member tests stop at promotion and never reconstruct. Acceptance: a compact
1,001-member promoted receipt reconstructs exact bytes and passes P6 with a load-bearing final member;
`LIMIT 1000` replayed independently on the membership query and on both joined queries each fails a
committed test.

A3 — LOW, test gap, reproduced by rev2 (`E001`, `system.py:1841`). `_promoted_function_rows` accepts
`LIMIT 1000`; admissible cardinality 1001 returns 1000 rows with the suite green. Same family as A2, on
the P1-P5 verifier enumeration rather than u3b2's.

A4 — MEDIUM, test gap, reproduced by rev2 (`E008`, `system.py:3131`). `authorized.entries[:1000]` leaves
the suite green: with 1001 prospective members, 1000 authority calls fire and the final member is never
authorized. u3b1 pinned enumeration quantification but not authorization quantification.

A5 — LOW, test gap, reproduced by rev. The authorizer + full-dump read-only proof covers only successful
reconstruction and successful P6. A no-op `UPDATE` injected into P6's missing-receipt branch keeps all 260
tests green. Current code writes on none of these paths; the durable proof is what is missing.
Acceptance: the guarded authorizer + dump runs over empty, legacy-nonempty, corrupt-latest, aggregate,
wrong-partition and corrupt-content branches, asserting zero attempted writes on each.

## Batch 2 — joined-surface pins (rev2 counterexample-proved, u3b1 code correct)

Each is a live mutant that no committed test kills. Acceptance for every item: the named mutation fails at
least one committed test under MAIN's replay.

B1 `M003` `models.py:193` — `frozen=False` on `FunctionSetPromotion` permits attribute assignment.
B2 `D007` `system.py:195` — entry-seal `support` framed as hex instead of decimal; diverges only at ≥10
   (support=10 → mutant `426a…868e` vs ABI oracle `602f…aabb`).
B3 `D008` `system.py:202` — same, for report `test_count`.
B4 `Q001` `system.py:1928` — `>` → `>=` on `FUNCTION_MAX_ENTRIES` rejects an exactly-maximal function,
   contradicting the inclusive contract.
B5 `Q005` `system.py:2213` — `!=` → `<` on the P5 projection cardinality lets extra document entries
   through and leaks `ValueError` from `zip(strict=True)` instead of a failed structured check.
B6 `S003` `system.py:2083` — `!=` → `<` admits a future-revision promoted row as current.
B7 `S005` `system.py:2873` — retained set widened to `('promoted','retired')` pulls historical retired
   rows into the promotion plan.
B8 `S008` `system.py:2907` — candidate revision `=` → `<=` admits prior-revision verified rows.
B9 `C009` `store.py:260` — `WHERE 0 AND status='promoted'` makes the active exact-scope unique index inert
   and admits two promoted rows for one scope.
B10 `C015` `store.py:496` — `PRAGMA foreign_keys = OFF` commits a fully dangling membership row, which is
    exactly the structural retention invariant u3b's Decision 1 rests on.
B11 `C016` `store.py:438` — deleting the fingerprint-value comparison opens a ledger whose stored
    fingerprint is `wrong-fingerprint`.

## Rejected as equivalent (rev2's own proofs, accepted by MAIN)

`O002` `O004` `O006` `O008` (orderings feeding digest-keyed maps or already-sorted inputs), `Q002`
(count and enumeration share one predicate inside one read snapshot), `Q006` (`strict=False` after an
exact cardinality check), `S011` `S012` (widened SQL branches unreachable inside one `BEGIN IMMEDIATE`
whose rows were already validated), `T008` (plan-identity guard proves the two tuples equal). Nine live
mutants, invariant-preserving under the required semantics.

## Batch 3 — u3b2-surface pins (rev2b, F01-F23)

`rev2b-m2u3b2` swept the new surface with its own catalogue: 50 non-equivalent survivors
counterexample-proved, 26 invariant-preserving survivors with explicit proofs, consolidated as 23
findings F01-F23 in `.scratch/agents/rev2b-m2u3b2.md` (each with `file:line`, mutation, counterexample,
severity and its acceptance check) plus `.scratch/agents/rev2b-m2u3b2-mutants.jsonl`.

Dominant family, and the reason the batch is large: **F07-F13 and F16 are all "pinned only in the
middle."** The implementation's set-level probes corrupt the middle member of three, so a quantifier that
stops before the final row survives — ordinal contiguity, membership function-hash binding, membership
input binding, entry-seal binding, full report child-set validation, passing-report enforcement, and the
four receipt-scope bindings each need a last-position probe. `.agent/memory.md` says middle **or** last;
on this surface the last position is the load-bearing one, because the loop index is what a mutant
weakens.

Remaining families: decimal integer decoding above nine (F01), inclusive upper bounds (F02), negative
transition counts (F03), promoter text boundaries (F04), digest exactness at the final nibble (F05, F16),
latest-P6 scope decoys including future revision and case variants (F06), canonical membership ordering
at the final position (F14), membership digest beyond three rows (F15), P6 text comparison weakening to
hash-only (F17), public partition lookup under case/LIKE widening (F18), success detail not pinning the
actual sequence (F19), broad exception masking (F20), `FunctionReconstruction` value equality (F21), root
`__all__` export membership (F22), and derived function hash on manually constructed values (F23).

## Outcome

All three batches landed; suite 230 -> 260 -> 271 -> 293, `uv build` green at every pass under MAIN's own
rerun. A1 was the sole production change: the aggregate fast-fail path now emits its failed P6 inline and
never reaches the shared core, pinned by a committed test whose patched `_reconstruct_function_receipt`
raises if called. Every other item landed as committed tests over unchanged production code.

MAIN's own verification, independent of every fixer's account:
- Batches 1-2: 17 mutants replayed from MAIN's own anchors, each proven live before its run, 17/17 killed.
- Batch 3: the reviewer's complete 108-mutant catalogue replayed against the fixed tree - 83 killed, 25
  survived, and all 25 lie inside the reviewer's own 26 explicitly-proved-equivalent IDs, so no accepted
  finding remains open.
- Harness: every replay ran from a pristine copy with `__pycache__` purged and `PYTHONDONTWRITEBYTECODE=1`,
  addressed by anchor plus nearest recorded line, since production line numbers shifted across fix passes.

## Fix sequencing

Every batch writes `tests/test_system.py`, so fix passes run sequentially, never in parallel. Batch 1
lands the sole production change (A1) plus the enumeration/read-only coverage; batch 2 lands the joined
pins. `store.py` moves from byte-identical only if a pin genuinely requires it — B9/B10/B11 are test
pins against the existing schema, not schema edits.
