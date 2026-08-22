# M3.1 acceptance contract — delete the `authority()` callback

Unit: M3.1 `tier=kernel` `tags=-` `depends=none`. Calibration unit: MAIN pays implementation +
coordination from one window; record actual `main=` at close and resize M3.2a..M3.9b against it.

Scope source: `.agent/roadmap.md` M3 seed (b) — "the `authority()` callback goes, keeping reviewer and
actor recording, which supervision genuinely requires". Surface map:
`.agent/decisions/m3-map-b-authority.md` (212 anchors, all resolving at `3a53389`, re-validated by MAIN
with `uv run python .agent/decisions/m3-report-validate.py`).

Removal closure rule (roadmap L5 CRITICAL): a green suite is NEVER closure. Every predicate below is
either an ABSENCE assertion over an enumerated residue token or a PRESERVED-invariant pin that fails
when that invariant alone disappears.

## Part 1 — decisions

Forks come from map S6. MAIN ruled each from source evidence; no spike was dispatched, because the
deciding facts are readable: both contested scaffolds already call their plan helper a second time
inside the write transaction, so "does the helper work under `BEGIN IMMEDIATE`" is answered by the
shipped code rather than by a probe.

### D1 — `System.__init__` hard-deletes `authority` (map S6-2 alternative A)

`authority`, `AuthorityCheck`, `self._authority`, `_authorize`, and the callback-shape validation are
deleted outright. `System(db, authority=...)` moves from accepted / `ValidationError` to Python
`TypeError`. No deprecated-but-ignored keyword: an accepted keyword that silently authorizes nothing is
a security-shaped lie, and the package is `0.1.0` with a documented pre-1.0 no-migration posture.

Consequence stated plainly, not hidden as prose cleanup: this REMOVES a defense-in-depth hook. Built-in
authorization of registration, revision, review, compile, verify, promote, challenge, revocation and
suspension is intentionally lost. External authentication and authorization become the sole
authorization layer for every library and CLI surface.

### D2 — actor / reviewer argument shapes preserved byte-exactly (map S6-3 alternative A)

Every current required/defaulted signature stays: `registered_by`, `compiled_by` and single-artifact
`verified_by` default to `"local-system"`; revision, batch verification, both promotions, revocation and
suspension require actors; review and challenge require reviewers. Eleven CLI leaves keep their identity
flags unchanged. Making actors uniformly required is a separate public-ABI expansion the seed does not
imply.

### D3 — callback-specific errors deleted, generic classes retained (map S6-4 alternative A)

Deleted message strings: `"authority must be callable"`, `"actor is not authorized for {action}"`,
`"draft eligibility changed during authorization"`, `"function promotion candidates changed during
authorization"`. `ValidationError`, `StateError`, their `__init__.py` exports and CLI exit 2/4 mappings
all stay — many non-authority paths reach them. No compatibility error class is added.

### D4 — `verify_drafts` collapses to one locked plan (map S6-5 alternative A)

Current shape (`system.py:3648-3671`): unlocked `_draft_verification_plan` → `_authorize` per draft ID →
`self._now()` → write transaction → recompute the plan → compare `(revision, selected_ids)` → raise.

The comparison exists only to bind the callback's subject set to the write set. Delete the callback and
NOTHING remains between the two plan computations except `self._now()`, so the comparison degenerates to
"did the ledger change between two adjacent reads" — a spurious failure source, not a guarantee. The
caller supplies no expected identity to `verify_drafts`; the result reports `operation_revision` and the
entries actually verified. Verifying whatever is eligible under the write lock is strictly more correct
than failing because an adjacent unlocked read differed.

Post-unit shape: `self._now()` → write transaction → ONE `_draft_verification_plan` → verify each row.
`revision`, `rows` and `skipped` all come from that single plan.

### D5 — `promote_function` collapses to one locked plan (map S6-6 alternative A)

Same shape and same argument (`system.py:4200-4271`). The three identity tuples
(`authorized_member_ids`, `authorized_candidate_ids`, `authorized_retired_ids`) bind the first plan to
the locked plan, and only the callback loop sits between them.

Post-unit shape: write transaction → ONE `_function_promotion_plan` → empty-union gate → clock/ID →
expected-hash `ConflictError` → retirement and candidate writes.

### D6 — the empty-union gate moves inside the write transaction (map S6-7, transaction-side)

`if not <plan>.entries: raise StateError("function promotion requires at least one member")` runs on the
LOCKED plan, before `self._now()` and `_new_id("fpr")`. This strengthens the invariant: emptiness is now
decided on the authoritative plan instead of a stale unlocked read.

The alternative — keep an unlocked read preflight purely to reject emptiness — is rejected: it plans the
set twice at up to 50,000 entries to avoid one lock acquisition, and it re-creates the exact
read-then-lock TOCTOU shape this unit deletes.

Observable delta: a rejected empty promotion now briefly acquires the write lock. No clock call, no ID
call, no durable write, unchanged exception class and message. A bad clock likewise now raises inside
the transaction and rolls back; no durable write either way.

### D7 — transition-set drift is NOT independently forbidden (normative ruling)

The map (S6-6) required MAIN to state whether candidate/retired drift stays forbidden after the
authorization window disappears. It does not, and the current code never gave the caller that guarantee:
the deleted comparison binds two of `promote_function`'s OWN adjacent reads, never the caller's earlier
`function inspect`. What binds the caller is unchanged:

- `expected_function_hash` binds final function CONTENT under the lock. A changed member set changes the
  content, so member drift still raises `ConflictError`.
- Each retirement executes under the same lock with `WHERE id = ? AND status = 'promoted'` and raises
  `StateError("function predecessor changed before locked retirement")` on `rowcount != 1`, so the
  locked plan's transitions self-check.

Residual, stated rather than concealed: a drift that leaves function content identical while changing
candidate disposition or the retired set no longer raises. It is coherent — every write comes from the
locked plan and every retirement re-checks its own precondition — but it is a real narrowing of what
`promote_function` refuses, and it belongs in the unit's commit body.

### D8 — documentation disposition (map S3)

| surface | current | disposition |
|---|---|---|
| `README.md:63` | `verify_function` is read-only and authority-free | term rewrite — property survives, `authority-free` no longer distinguishes it |
| `README.md:237` | exit 4 a state or authority conflict | rewrite — exit 4 keeps the state/conflict class, loses authority attribution |
| `README.md:268-269` | a library deployment can supply an `authority(...)` callback | DELETE the promise; keep the remote-authentication/encryption/retention/signing sentence |
| `README.md:273` | executes without the database and without the authority callback | causal rewrite — the bundle is outside ledger protection because it runs without the database |
| `README.md:281-283` | `The callback gates operation registration/revision, ...` | DELETE the sentence; expand the deployment-authorization obligation to every library and CLI surface |
| `docs/architecture.md:39` | The call is read-only and authority-free | term rewrite, matching `README.md:63` |
| `docs/threat-model.md:6` | authority callback or external access control | DEGRADE to external access control alone |
| `docs/threat-model.md:7` | within the authority and context represented by their partition | keep partition scoping; drop callback-enforced supervisor authority |
| `docs/threat-model.md:11` | opens no database, calls no authority callback, and starts no adapter | drop the vacuous callback clause, keep database/adapter boundary |
| `docs/threat-model.md:65` | authenticate and authorize review, revision, promotion, challenge, revocation, suspension | EXPAND — add operation registration, compilation and verification, which were callback-gated too |
| `docs/threat-model.md:18,75` | reviewer labels untrusted; re-run live policy before an effect | KEEP unchanged; both survive and matter more |

## Part 2 — residue set (absence predicates)

R1..R12 are absence assertions. Each names an exact token; the closing battery greps tracked source and
docs and fails on any hit. Counts are repo-wide over `src/`, `tests/`, `README.md`, `docs/`.

| id | token | required count after |
|---|---|---|
| R1 | `AuthorityCheck` | 0 |
| R2 | `_authorize` | 0 |
| R3 | `_authority` | 0 |
| R4 | `authority=` as a `System(...)` keyword | 0 |
| R5 | `authority must be callable` | 0 |
| R6 | `actor is not authorized for` | 0 |
| R7 | `draft eligibility changed during authorization` | 0 |
| R8 | `function promotion candidates changed during authorization` | 0 |
| R9 | `authorized_revision`, `authorized_ids`, `authorized_member_ids`, `authorized_candidate_ids`, `authorized_retired_ids` | 0 each |
| R10 | `authority callback` in `README.md` + `docs/` | 0 |
| R11 | `authority-free` | 0 |
| R12 | `authority conflict` | 0 |

R13: `word-boundary` count of `authority`/`authoriz*` surviving in `src/` names ONLY external-authorization
prose and SQLite's unrelated `set_authorizer` in tests. Every survivor is classified in the closing
report; an unclassified survivor fails the unit. (Memory rule: a removal budget counted by substring is
inflated by name collisions — classify every hit before it reaches a predicate.)

## Part 3 — preserved invariants (each independently pinned)

P1..P13 must each fail the suite when that invariant ALONE is removed. A pin shared with a residue
predicate does not count.

- **P1 empty-union gate.** `promote_function` over an empty prospective union raises
  `StateError("function promotion requires at least one member")` with the clock spy and ID spy both
  uncalled and the ledger byte-identical by full `iterdump()`. This is the `cf274a4` hardening; it must
  survive the deletion of the loop it guarded.
- **P2 empty-batch verify.** `verify_drafts` over zero eligible drafts returns a `DraftVerification` with
  empty `entries`, `passed=True`, the current `operation_revision`, and writes no report and no event.
- **P3 frozen constructor shape.** `inspect.signature(System.__init__)` exposes exactly `database` plus
  keyword-only `candidate_source`, `clock_us`, `generation_lease_seconds`, with their current defaults
  and annotations, and `System(db, authority=<callable>)` raises `TypeError`. Derive the parameter set in
  the test; never hardcode a count copied from a record. No such pin exists today (map S6-3).
- **P4 CLI identity census.** Derive the leaf set from `_parser()` inside the test — never from a number
  written into a record — and assert the 11 identity-bearing leaves keep their exact flag name,
  required-vs-defaulted status and default value: `operation revise --actor` (required),
  `operation register --actor` (default `local-system`), `proposal review --reviewer` (required),
  `compile --actor` (default), `verify --actor` (default), `promote --actor` (required),
  `challenge --reviewer` (required), `example revoke --actor` (required),
  `artifact suspend --actor` (required), `function verify-drafts --actor` (required),
  `function promote --actor` (required).
- **P5 actor grammar before state work.** Each of the 11 library capture points still runs
  `_text(..., maximum=256)` before any state access: an over-long or control-bearing actor raises
  `ValidationError` and leaves the ledger byte-identical.
- **P6 persisted identity.** `proposals.reviewer`, `examples.reviewer`,
  `example_revocations.revoked_by`, `artifacts.promoted_by`, `function_receipts.promoted_by` and
  `test_reports.details_json.verified_by` are all written by the formerly gated paths and read back.
- **P7 event provenance.** Event payload keys `registered_by`, `revised_by`, `reviewer`, `compiled_by`,
  `verified_by`, `promoted_by`, `revoked_by`, `suspended_by` all still appear on their events.
- **P8 schema fingerprint EMPTY diff.** `SCHEMA_VERSION` stays 2 and the fingerprint is byte-identical to
  `3a53389`. Track (b) is schema-neutral; a nonempty diff fails the unit.
- **P9 draft selection + ordering.** Current-build selection, prior-revision exclusion, non-draft-status
  exclusion, deterministic input-hash ordering under reverse scans, and skip projection all survive the
  scaffold deletion — pinned through returned entries, memberships and full dumps rather than through
  callback observation.
- **P10 promotion scope + tail.** Retained scope partition/operation exact, candidate scope
  partition/operation/revision exact, and the 1,001-member tail sentinel (memory: `LIMIT`-shaped
  enumeration defects need a sentinel beyond any plausible limit) all survive; the sentinel currently
  counts callback calls and must be re-expressed over receipt membership.
- **P11 locked conflict paths.** `ConflictError("expected_function_hash does not match the locked
  prospective function")` and `StateError("function predecessor changed before locked retirement")` both
  still fire, the first with a stale caller hash, the second with a predecessor moved out of `promoted`.
- **P12 reviewer-diversity policy.** `min_reviewers`, `COUNT(DISTINCT e.reviewer)` active support, frozen
  `reviewer_count` on builds, and its binding into `entry_seal` are unchanged.
- **P13 CLI exit map.** Exit 2 for validation, 3 for absent objects, 4 for state conflicts, 5 for
  integrity, 6 for negative verdicts — unchanged. `test_function_promote_maps_library_boundary_failures`
  keeps one generic exit-4 `StateError` case after the two authority-window fixtures go.

## Part 4 — gate identity

Configured gate: `uv run python -m unittest discover -s tests -t .`, run from the unit's committed
checkpoint. Baseline at `3a53389` is recorded in the unit commit body.

Post-unit test count is DERIVED and reported, never asserted from this contract: map S4 measures 11
category-(i) tests to delete (409 method-span lines) and 18 category-(ii) tests to rewrite (~87 lines),
and this unit adds pins for P3 and P4 which do not exist today. MAIN reruns the gate and records the
actual number.

Schema fingerprint check and the residue grep both run from committed state.

## Part 5 — probe corpus seed

1. `System(db, authority=lambda p, a, ac, s: True)` → `TypeError`; `System(db, authority=None)` →
   `TypeError` (hard delete rejects the keyword, not just a truthy value).
2. `System(db)`, `System(db, candidate_source=...)`, `System(db, clock_us=...)`,
   `System(db, generation_lease_seconds=1)` → all still construct.
3. Empty prospective union → P1 vector: exception class, exact message, clock spy uncalled, ID spy
   uncalled, `iterdump()` identical.
4. Concurrent writer landing between a caller's `function inspect` and its `function promote`: with
   content changed → `ConflictError` on the hash; with content identical but disposition changed →
   promotion SUCCEEDS (D7). Neither path may produce a `changed during authorization` message.
5. Predecessor moved out of `promoted` between plan and retirement → `StateError("function predecessor
   changed before locked retirement")`.
6. Draft set changed between two adjacent reads → `verify_drafts` verifies the locked set and never
   raises `draft eligibility changed during authorization`.
7. Bad clock (`clock_us` returning a non-int or out-of-range value) on a nonempty promotion →
   `StateError` from `_now()`, no durable write.
8. 35 parser nodes (`cement --help`, every group, every leaf) exit 0; the 11 identity flags match P4.
9. Schema fingerprint at HEAD vs `3a53389` → byte-identical.
10. Over-long (257-byte) and control-bearing actor at each of the 11 capture points → `ValidationError`,
    ledger byte-identical; the adjacent 256-byte value accepted and read back out of its persisted row
    (memory rule: pin every bound as an adjacent accept/reject PAIR).

## Part 6 — out of scope

- Any schema change, model field change, event ABI change or CLI grammar change (M3.6b owns the single
  schema cut).
- The `_request_id` label-leak rename (`.agent/polish.md`).
- Request-lifecycle removal (M3.3-M3.6b) and the command-runtime relocation (M3.7).
- Making actor arguments uniformly required (D2 rejects it as unrequested ABI expansion).

## Part 7 — amendments from the contract attack (`rev-m3u1`, 11 findings)

The reviewer attacked this contract before implementation. Accepted corrections, in force:

- **A1 (F02, CODE DEFECT, fixed).** D4's shape read the clock BEFORE the write lock, so a draft
  committed after that read could be verified with a report timestamp older than its own build, and a
  bad clock could mask `NotFoundError` for an absent operation. `verify_drafts` now reads the clock
  INSIDE the transaction, after the plan: `now` >= lock time >= every included draft's commit time, and
  the plan's `NotFoundError` still precedes any clock work. Pinned by
  `tests/test_authority_removal.py::LockedGuardTests::test_neither_collapsed_method_reads_the_clock_before_its_lock`.
- **A2 (F04/F03, claim correction).** D5's "nothing remains between the two plan computations except
  `self._now()`" is FALSE. The interval also holds the empty gate, three tuple derivations, `_new_id`,
  the write-lock acquisition, and unbounded wall time during which any concurrent writer can land,
  because the first plan is UNLOCKED. The ruling survives on the narrower true statement: the comparison
  binds two of the method's OWN reads and never binds the caller's earlier `inspect`, so no
  caller-facing guarantee is lost. What IS lost, stated plainly: the method-entry-to-lock transition-set
  stability window. D4's "strictly more correct" is likewise withdrawn as an untestable value claim; the
  compared tuple was exactly `(operation_revision, selected_artifact_ids)` and nothing else.
- **A3 (F05, accepted narrowing).** `clock_us` and ID allocation now run under `BEGIN IMMEDIATE` in both
  collapsed methods. A caller-supplied clock that blocks, or that re-enters the same ledger, now holds
  the write lock while it runs. This is the price of A1 and it is accepted, not overlooked.
- **A4 (F06, gap closed).** P11 named two locked guards; the source has THREE. The third is
  `StateError("function candidate changed before locked activation")` on the candidate-activation
  rowcount. All four locked verdicts are now pinned together by
  `LockedGuardTests::test_promote_function_keeps_both_locked_guards`.
- **A5 (F09, gap closed).** Token-absence predicates R1-R13 cannot prove scaffold deletion: renaming
  `authorized` to `preflight` satisfies every one of them while keeping both plan calls. Structural pins
  now assert each collapsed method plans exactly ONCE
  (`LockedGuardTests::test_each_collapsed_method_plans_exactly_once`).
- **A6 (F10, gap closed).** R13 now has a stable domain, an exact regex and an explicit survivor
  allowlist, and prints every unmatched hit
  (`ResidueTests::test_every_surviving_authorization_mention_is_classified`).
- **A7 (F01/F11, gap closed).** D2 promised 11 unchanged library signatures but pinned only CLI shape.
  `FrozenShapeTests::test_library_identity_arguments_keep_their_required_or_defaulted_shape` now derives
  the census over all 11 capture points, and the constructor pin includes the return annotation.
- **A8 (F07/F08, partially deferred).** D8 covered human-facing docs only. The two source docstrings
  (`System` class contract, `promote_function`) were rewritten in this unit. A per-row KEEP/REWRITE/DELETE
  disposition for every map S3 claim, and a gated human-facing register audit, are off-spine ->
  `.agent/polish.md`.

## Part 8 — rulings on the diff-blind verdict table (`test-m3u1`, 24 rows)

Table at `.scratch/agents/test-m3u1.md`. Phase 2 was cancelled once implementation landed, so the rows
are read here as contract questions, not as a suite. One row found a real undisclosed narrowing.

- **A9 (V10, NARROWING, disclosed + pinned).** `promote_function` exception precedence FLIPPED. At
  `3a53389` the clock read sat between the unlocked plan and the locked hash comparison, so a caller
  passing both a stale `expected_function_hash` and a failing `clock_us` got the clock `StateError`. The
  collapse puts the comparison ahead of the clock, so `ConflictError` now wins. Both paths leave the
  ledger unchanged and the new order surfaces the caller's real problem, so it is accepted rather than
  reverted -- but it is an observable change and belongs beside D7 in the unit's narrowing set. Pinned by
  `LockedGuardTests::test_the_expected_hash_conflict_precedes_the_clock_read`.
- **V05/V06/V11/V12 superseded by A1/A3.** All four proposed outcomes assumed D4's pre-A1 clock-first
  shape. Measured against both `3a53389` and HEAD, plan errors precede clock errors in `verify_drafts`
  (`NotFoundError` wins) and the empty-union gate precedes the clock in `promote_function`, so those
  precedences are PRESERVED, not narrowed. What did change is A3's already-stated price: a bad clock now
  fails after the write lock is taken rather than before.
- **V13 confirms D7.** Disposition-only drift promotes as a zero-candidate checkpoint. That is the
  narrowing D7 states, not a defect.
- **V01/V03/V04/V07/V08/V17/V18/V20 already shipped.** The closure battery implements each proposal:
  binder-level `TypeError`, full resolved constructor signature, the 11-method signature census,
  plan-called-exactly-once for both methods, identifier-boundary residue tokens, and the R13 allowlist
  over the full source/test/doc corpus.
- **V19 ruled AGAINST its proposal.** The battery EXCLUDES itself from its own scans rather than
  assembling forbidden strings from fragments. A predicate that hides the token it forbids is unreadable
  at the exact moment a reader needs it, and the battery is not shipped source.
- **V02/V09/V14 out of scope.** An inert user-assigned `_authority` attribute carries no obligation;
  digest-before-actor validation order and in-transaction rollback scope are untouched baseline
  behavior.
- **V15/V16/V21/V22/V23/V24 = grading questions on P5-P10, deferred.** The rewritten `test_system.py` /
  `test_cli.py` cases carry these invariants at their pre-existing grade. Raising them -- per-writer
  identity columns, per-producer event payloads, a frozen schema digest replacing MAIN's by-hand
  byte-identity check, both 1,001-member sentinels, and UTF-8 boundary probes -- is off-spine ->
  `.agent/polish.md`.
