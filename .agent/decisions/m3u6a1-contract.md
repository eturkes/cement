# M3.6a1 acceptance contract — migrate every consumer off the lifecycle API

Unit: M3.6a1. Tier `kernel`, tags `-`, depends M3.5b.
Scope source: `.agent/roadmap.md` M3.6a1. Split grounds: `.agent/roadmap.md` M3.6a.

M3.6a1 moves every consumer off `System.handle` / `System.request_status` **while
both still ship**, so M3.6a2's deletion opens against a tree that no longer
depends on them. Nothing is deleted here. The gate stays green throughout, which
is the whole point of the consumer-migration-before-deletion axis: the old and
new APIs ship simultaneously, so the migration is verifiable against both.

Sections 12 and 13 are PENDING; the S3 wave fills them.

---

## 1. Ground state, measured

At `4db71a9`, tree clean.

| Fact | Value | Source |
| --- | --- | --- |
| Gate 1 suite | 949 tests, OK | `1146421` close record |
| `SCHEMA_VERSION` | 2, unchanged by this unit | M3 track order |
| Consumer definitions | 49 | `m3u6a1-census.json` `totals.definitions` |
| Consumer sites | 79 | `m3u6a1-census.json` `totals.sites` |
| Ruled MIGRATE | 25 | `totals.ruled_migrate` |
| Ruled MIGRATE-RESOLVE | 1 (the demo) | `totals.ruled_migrate_resolve` |
| Ruled RETAIN | 23 | `totals.ruled_retain` |
| Overrides | 5, each with grounds | `totals.overrides` |
| `SURVIVING-MIGRATE` at baseline | 26 | `m3u6a1-census.py` |
| Site shapes | ACTOR 2, MISS-GUARDED 4, HIT 9, FACTORY 51, UNOBSERVED 6 | `m3u6a1-fallback.json` |
| `handle` suspension writers | `system.py:1135`, `system.py:1166` | AST attribution |
| Independent suspension writers | `review` 1852, `_verify_row` 4046, `challenge` 5024 + 5120, `revoke_example` 5186, `suspend_artifact` 5233 | AST attribution |

Fixture helpers carrying the bulk of the burden, with call counts measured by
fixed-string search at `4db71a9`:

| Helper | Definition | Call sites |
| --- | --- | --- |
| `confirm` (method) | `tests/test_system.py:226` | 41 |
| `confirm` (nested, shadowing) | `tests/test_system.py:14452` | 1 |
| `_confirm_scope` | `tests/test_system.py:1412` | 65 (63 direct + 2 inside `_promote_scope`) |
| `_promote_scope` | `tests/test_system.py:1445` | 14 |
| `_confirm` | `tests/test_resolve_battery.py` | 1 |
| `_promoted_conflict_fixture` | `tests/test_proposal_binding_battery.py` | 7 |
| `_promoted_example_ledger` | `tests/test_hospital_ocr_example.py` | 4 |

---

## 2. The two premises this unit rests on

Both were measured in S1 and both were FALSE as the plan line wrote them. The
corrected forms are binding.

**P1 — row-state equivalence.** `propose` reaches the identical row state as
`handle` across `requests`, `proposals`, `events`, `examples`, `artifacts` and
`operations`, with EXACTLY ONE differing cell: the `proposal.created` event's
`payload_json`, where `handle` writes `{"request_id": "<caller id>"}` and
`propose` writes `{}`. Evidence: `m3u6a1-premise.py`. That cell is the
migration's entire behavioural signature.

**P2 — `resolve` at the demo's Act-2 ledger state.** `resolve` CANNOT replace
`handle`'s artifact-hit branch there: it fails check `persisted-function-receipt`,
because the walkthrough promotes its function set only in Act 5. It matches once
the set is promoted. Evidence: `m3u6a1-premise.py`.

---

## 3. Site shapes and their migrations

`m3u6a1-census.py` classifies a consumer by what the enclosing definition does
with the call's RETURN VALUE. `m3u6a1-fallback.py` classifies each SITE by what
the call actually claims, which is a different axis and the one that decides the
migration's shape. A site's shape, not its census verdict, selects its rewrite.

### FACTORY — 51 sites

The scope holds no once-promoted artifact for this canonical input, so
supervision is the only reachable branch and `propose` states exactly what
`handle` stated. Migration is a rename:

```
X = <sys>.handle(P, O, V, request_id=R)      ->  X = <sys>.propose(P, O, V)
self.assertIsInstance(X, ReviewRequired)     ->  deleted
assert isinstance(X, ReviewRequired)         ->  deleted
X.proposal_id                                ->  X
```

`propose` returns the proposal identifier directly, so every downstream
assertion survives unchanged.

### MISS-GUARDED — 4 sites

`tests/test_system.py` 541, 608, 827, 867. Every execution of the site sees a
once-promoted artifact for this exact input that still declines to answer,
because it is now `suspended` (541, 608, 827) or `retired` (867). The
`assertIsInstance(x, ReviewRequired)` line therefore carries a SECOND claim —
the stored artifact did not answer — and `propose` cannot express it. Migrating
these to a bare `propose` would delete a preserved invariant while leaving the
gate green, which this project's own removal standard forbids.

`resolve` measures `passed=True match=False` at all four, which is the post-trim
spelling of a verified miss. The migration prepends that assertion and keeps the
proposal, so both the claim and the row state survive:

```
resolution = <sys>.resolve(P, O, V)
self.assertTrue(resolution.verification.passed)
self.assertIsNotNone(resolution.match)
self.assertFalse(resolution.match.matched)
X = <sys>.propose(P, O, V)
```

The `propose` call is retained rather than dropped even where the identifier is
unused, because P1's equivalence is a claim about ROW STATE and dropping the
call would change it.

### ACTOR — 2 sites, NOT migratable

`tests/test_system.py:1044` and `:2698`. The same-input artifact is `promoted`
before the call and `suspended` after it, so the call PERFORMS the dispatch-time
integrity quarantine the test asserts. `propose` never consults an artifact;
`resolve` is read-only and reports `passed=False` at both sites, so it cannot
even state the post-condition. Both are re-ruled RETAIN with grounds in
`m3u6a1-census.json`; M3.6a2 owns them together with `handle`'s two suspension
writers.

### HIT — 9 sites

`handle` answered from the artifact, so the site pins a hit. Every one is
already RETAIN.

---

## 4. Obligations

### Migration completeness

- **D01** `m3u6a1-census.py` reports `SURVIVING-MIGRATE: 0`, with `UNRULED`,
  `STALE`, `MEASURE-DRIFT`, `UNGROUNDED-OVERRIDE` and `BAD-VERDICT` all 0.
- **D02** `m3u6a1-rule-census.py --check` reports `IN-SYNC`.
- **D03** No definition ruled RETAIN is edited to remove its lifecycle call. The
  census cannot see the difference between a migrated site and a deleted one, so
  the RETAIN set is pinned by name and by call count.
- **D04** `System.handle` and `System.request_status` still ship, unchanged, and
  are still reachable. The unit deletes no production surface.
- **D05** The surviving lifecycle consumers after this unit are exactly: the 23
  RETAIN definitions, the two ACTOR tests among them, and the library itself.

### Shape preservation

- **D06** Each of the four MISS-GUARDED sites carries a `resolve` call asserting
  `verification.passed` true and `match.matched` false, positioned BEFORE its
  `propose` call in the same test body.
- **D07** Each of the four MISS-GUARDED sites retains a `propose` call, so P1's
  row-state equivalence holds site by site.
- **D08** No FACTORY site gains a `resolve` call. A verified-miss assertion at a
  site with no once-promoted artifact asserts nothing and would misrepresent the
  shape table.
- **D09** `m3u6a1-fallback.py` reruns from committed state and reports
  `RESULT: PASS`, with its per-call positive control at 0 failed and 0
  unreadable. After migration its target population shrinks; the grader's
  `UNOBSERVED-MIGRATE` control stays 0.

### Helper signatures

- **D10** `tests/test_system.py::confirm` loses its `request_id` positional
  parameter. Every one of its 41 call sites drops the corresponding argument.
- **D11** `tests/test_system.py::_confirm_scope` loses its `request_id`
  positional parameter. Every one of its 65 call sites drops the corresponding
  argument.
- **D12** `tests/test_system.py::_promote_scope` loses its `prefix` positional
  parameter, because `prefix` exists only to build the two request identifiers
  `_confirm_scope` no longer takes. RULED REMOVE, not keep: a parameter that
  every caller supplies and no callee reads is exactly the residue a migration
  unit must not leave behind, and the surgery script rewrites its 14 call sites
  at the same cost as leaving them. The removal is observable — a retained
  `prefix` fails D14's dead-parameter check.
- **D13** `tests/test_resolve_battery.py::_confirm`,
  `tests/test_proposal_binding_battery.py::_promoted_conflict_fixture` and
  `tests/test_hospital_ocr_example.py::_promoted_example_ledger` migrate onto
  `propose`; any parameter that becomes unread is removed with its arguments.
- **D14** No migrated helper retains a parameter that no statement in its body
  reads. Checked over the shipped source by AST, not by grep.
- **D14a** `tests/test_system.py` holds TWO definitions named `confirm`: the
  method at `:226`, called as `self.confirm(...)` 41 times, and a nested
  function at `:14452` shadowing it inside
  `test_function_report_reaches_every_compiler_block_reason_through_public_apis`,
  which takes `system` as its first parameter and is called bare. The two carry
  different signatures and different lifecycle sites (`:235` and `:14461`), so
  each is migrated under its own anchor. A bare `confirm(` anchor spans both and
  is forbidden.

### Surgery mechanics

- **D15** The migration lands through ONE idempotent script,
  `m3u6a1-surgery.py`, which asserts the expected occurrence count of every
  anchor before applying it and prints `no-op` on a second run against a
  repaired tree. A repeated fragment aborts loudly rather than mutating the
  wrong span.
- **D16** The script is replayable from a clean base: applying it to a detached
  worktree at this unit's opening commit reproduces the shipped tree, with every
  divergence recorded as a named exception in section 10.
- **D17** Multi-line anchors wherever a fragment repeats. A `count == 1`
  assertion is what converts the occurrence-index trap into a loud failure.

### Demo and transcript

- **D18** `examples/hospital_ocr/run_demo.py`'s seven `system.handle` sites
  migrate: five onto `propose`, and the two `Resolved(source="artifact")` sites
  onto `resolve`.
- **D19** The walkthrough promotes its function set immediately after each
  artifact promotion, so Acts 2 and 3 answer through `resolve`. P2 measures that
  `resolve` fails `persisted-function-receipt` at the un-checkpointed Act-2
  state and matches once the set is promoted, so the checkpoint MOVES rather
  than the assertion weakening.
- **D20** Act 5 keeps export and identity and loses its "becomes one exportable
  function" framing, because the set is now promoted earlier. The demo teaches
  M3's post-trim lifecycle: propose, review, compile, verify, promote artifact,
  promote set, resolve.
- **D21** The demo still refuses to run under `-O`/`-OO`, and its `assert`
  verdict count is re-derived rather than carried; the count moves with the act
  structure.
- **D22** The example README's `text` transcript block is regenerated from the
  demo's own output. Both dynamic-value masks and their occurrence counts move
  with the act structure, and
  `DemoTranscriptTests.test_demo_output_matches_the_pinned_readme_transcript`
  keeps asserting exactly one match per mask.
- **D23** `examples/hospital_ocr/README.md:208` and `:216` name the vanishing
  `request.resolved_by_artifact` event inside the pinned transcript. Both are
  rewritten by regeneration, never by hand. No shipped prose names an event kind
  the migrated demo no longer emits.

### Preserved invariants

- **D24** `tests/test_proposal_binding_battery.py::test_b30_...` and the
  `test_d03_...` payload pin stay RETAIN and stay green. They pin the
  `{"request_id": ...}` payload that P1 measures as the migration's sole
  attributable row difference, so retiring either would silently delete the
  record of that difference.
- **D25** M3.3's P06 byte-span freeze on `System.handle` stays green. The unit
  edits no production source, so the span must not move; the three slicing
  conventions (12,866 B `1182130a2b3a`, 12,867 B `cd60036faf5c`, 12,862 B
  `c27e71b0b4c7`) are recorded here so a lens on the wrong row is checkable.
- **D26** M3.5b's D01 pin at `tests/test_cli_removal_battery.py:617`, asserting
  `System.handle` and `System.request_status` still ship as library methods,
  stays green.
- **D27** M3.5b's D15a six-module byte-identity freeze stays green.
- **D28** Gate 1 stays green at every commit, never only at the last one. A
  migration that lands red and is repaired later forfeits the axis's own
  guarantee.

---

## 5. Tripwires, numbered rather than met as regressions

The standing rule from M3.5a S2, widened at M3.5a S3: every freeze pin over a
file the unit's obligations touch becomes a numbered obligation in the session
that opens the unit, or it re-emerges disguised as a regression.

| Tripwire | Locus | Obligation |
| --- | --- | --- |
| `proposal.created` payload pins | `test_b30_...`, `test_d03_...` | D24 |
| `System.handle` byte span | `test_submission.py:671`, `test_submission_battery.py:289` + `:330` | D25 |
| Lifecycle methods still ship | `test_cli_removal_battery.py:617` | D26 |
| Six-module byte freeze | M3.5b D15a | D27 |
| `_promote_scope` dead `prefix` | `test_system.py:1445` | D12, D14 |
| Two `confirm` definitions in one file | `test_system.py:226`, `:14452` | D14a |
| Transcript mask counts | `test_hospital_ocr_example.py` | D22 |
| Demo `assert` verdict count | `run_demo.py` | D21 |

This unit edits NO production source, so `B02`'s frozen tuple
(`_command_supervisor.py`, `example_adapter.py`) and gate 4's parser census and
`parser_shape` digest are not tripwires here. Both are asserted unchanged rather
than assumed: gate 4 reruns green.

---

## 6. Gates

| # | Gate | Command | Acceptance |
| --- | --- | --- | --- |
| 1 | Suite | `uv run python -m unittest discover -s tests -t .` | OK, 949 tests as a floor |
| 2 | Census | `uv run python .agent/decisions/m3u6a1-census.py` | `SURVIVING-MIGRATE: 0`, all controls 0 |
| 3 | Ruling sync | `uv run python .agent/decisions/m3u6a1-rule-census.py --check` | `IN-SYNC` |
| 4 | Shape attribution | `uv run python .agent/decisions/m3u6a1-fallback.py` | `RESULT: PASS` |
| 5 | Premises | `uv run python .agent/decisions/m3u6a1-premise.py` | P1 and P2 reproduce |
| 6 | Surgery idempotence | `uv run python .agent/decisions/m3u6a1-surgery.py` twice | second run `no-op` |
| 7 | Parser census + shape | gate 4 of M3.5b | rc 0, unchanged |
| 8 | Doc parse | `m3u5b-doc-parse.py` | rc 0 |

Every gate reruns from committed state with its SHA recorded. Gate 2 is the
acceptance gate and is RED at baseline by construction (`SURVIVING-MIGRATE: 26`).

---

## 7. Battery (S4)

A green suite is never closure for a migration, because re-basing a test
together with its pin keeps the gate green. The battery is diff-blind, one test
per obligation D01-D28, and it must fail when one obligation remains undone or
one preserved invariant disappears.

Not every obligation can be red at baseline. D04, D24-D27 are PRESERVATION
obligations that legitimately hold before the unit opens; the mutation catalogue
generalises the baseline-red credential to them through an independent red
control per obligation, exactly as M3.5b section 11 established. Report the
split; never force it.

Gate 3 for this unit is a REVERSION catalogue: a migration is bound by restoring
what was migrated away, never by mutating what remains. One row per battery
clause, tagged `reversion` or `sensitivity`, each row's `target_test` named, and
`killed` attributed separately from `misdirected`.

---

## 8. Carried findings

- **F1 — M3 loses dispatch-time quarantine, not quarantine.** `handle` owns two
  suspension writers (`system.py:1135` duplicate-promoted artifacts for one
  input; `system.py:1166` integrity failure detected at dispatch). M3.6a2
  deletes both. `verify`, `review`, `challenge`, `revoke_example` and
  `suspend_artifact` retain independent suspension writers, so quarantine
  survives; what does not survive is quarantine triggered by a resolution
  attempt, because after the trim there is no dispatch and `resolve` is a pure
  read. This is coherent with the milestone's own scope and is recorded here so
  M3.6a2 states it deliberately rather than discovering it as a deletion
  side effect. It reaches the owner before any scope-source edit.

---

## 9. Session boundaries

- **S1** DONE — measurement + rulings. `main=` 90% 216K/240K.
- **S2** — shape attribution + contract. Re-sized from the plan's three sessions
  to four on this session's own measurement: the plan budgeted a mechanical
  migration, and S2 measured a semantic fork the census could not see, which
  costs six sites of per-site judgment plus four new obligations (D06-D09).
  The contract is S3's entry state.
- **S3** DONE — implementation: the surgery script, the test-tree migration, the
  demo rewrite, the transcript regeneration, gates 1-8 green at `4e72692`.
  `main=` 83% 200K/240K. Re-sized to FIVE sessions here: MAIN entered S3 at 73%
  after attached state plus the ground-state read, and the implementation is 28
  sites, 3 helpers, ~132 call sites, the demo and the transcript, so seeding a
  validator plus skeleton before a diff-blind dispatch would not have left room
  to finish. Sections 12-13 stay PENDING.
- **S4** — wave 2 (`test` diff-blind battery, `rev`/`rev2` prep) + sections
  12-13.
- **S5** — reversion catalogue + closure.

---

## 10. Corrections to this contract

Filled as the unit runs. A closure session must re-grade this section's gate
text against what the instruments actually measured; no instrument grades the
contract against its own results, which is why seven consecutive units have
closed on claim defects in MAIN's own text.

- **C01 — section 3's HIT claim is FALSE for 2 of its 9 sites.** "HIT — 9 sites.
  `handle` answered from the artifact" holds for 7. `tests/test_system.py:485`
  and `:584` carry `outcomes: ["ReconciliationRequired"]` in
  `m3u6a1-fallback.json`, which is the ambiguity branch: `handle` refused to
  choose, it did not answer. `:584` reads `before=['suspended']` with
  `resolve -> passed=True match=False`, the MISS-GUARDED signature exactly. The
  shape rule keys HIT on `outcomes != {"ReviewRequired"}`, so it collapses
  "answered" with "refused to choose". Both sites are RETAIN, so nothing
  migrates differently; the claim, not the ruling, was wrong.
- **C02 — a FOURTH blindness axis, and it is the one that costs code.** The
  census reads RETURN VALUES and the shape table reads ARTIFACT SIDE EFFECTS.
  Neither sees that `request_id` is a caller-chosen PRIMARY KEY. `propose`
  (`system.py:987`) and `submit_proposal` (`:940`) both mint `_new_id("req")`
  internally and neither returns it, so no public route sets or reads it. Four
  MIGRATE sites depended on the value: `test_system.py:344`, `:378` and `:1222`
  use it as a raw-SQL key, closed by
  `(SELECT request_id FROM proposals WHERE id = ?)`; and
  `test_function_report_pending_request_join_is_like_and_case_exact` plants five
  DELIBERATE COLLIDERS (`pending_join_1` against `pendingXjoinX1` under `LIKE`,
  `PendingCase` against `pendingcase` under case folding) against the
  `r.id = p.request_id` join at `system.py:534/547/574/591`. A minted
  `req_<32hex>` id is lowercase hex whose only `_` sits in the prefix, so
  migrating that site plainly would leave the `=` -> `LIKE` and case-folding
  mutants ALIVE with every assertion green. The colliders are re-planted after
  submission by raw `UPDATE` under `PRAGMA foreign_keys = OFF`.
- **C03 — D03 pins the RETAIN definition and says nothing about its FIXTURES.**
  Migrating a shared fixture helper changes what it PLANTS, so a RETAIN consumer
  of that helper breaks with its own lifecycle call untouched. Five reds, three
  definitions: `test_confirmed_request_cache_is_bound_to_immutable_example`,
  `test_unknown_resolved_source_kind_fails_closed_at_storage` and
  `test_operation_revision_invalidates_every_old_request_path`. Rule for a later
  unit: a fixture helper's ruling is not local to it, so migrating one obliges a
  re-read of every consumer, RETAIN included.
- **C04 — one of those reds would have passed vacuously in the other
  direction.** `test_unknown_resolved_source_kind_fails_closed_at_storage`
  asserts that a CHECK constraint raises on `source_kind='mystery'`. A zero-row
  UPDATE raises nothing, so the moment its target row stopped existing the test
  was one edit away from green-and-vacuous rather than red. It now asserts
  `count(*) == 1` on the target row before the raising UPDATE. Generalisation: a
  test whose subject is a constraint needs a positive control that the
  constrained ROW exists.
- **C05 — D15 and D16 are read as covering the WHOLE migration, demo, prose and
  transcript included, with no section-10 exception claimed.** The demo rewrite
  is not a rename, so it lands as `TEXT` anchors, and the README transcript
  lands as a fourth family that RUNS the migrated demo and rewrites the fenced
  block under D22's two mask-count assertions. `git checkout -- tests/ examples/`
  plus one script run reproduces the shipped tree exactly.
- **C06 — D17's "multi-line anchors wherever a fragment repeats" is discharged
  by the AST for `SITES` and `PARAMS`, not by anchors.** A call addressed by
  NODE cannot hit the occurrence-index trap, because nothing is matched by text.
  What replaces the count assertion is stronger: every site asserts that the
  enclosing function's remaining references to the bound name are plain loads,
  so a site consuming anything beyond `.proposal_id` ABORTS instead of migrating
  silently. `SITES` is keyed by QUALIFIED NAME and ordinal, never by line: a
  line-keyed table cannot be idempotent, because pass 1 moves every line below
  its own first edit. That keying also discharges D14a by construction.
- **C07 — TWO M3.5b OBLIGATIONS INVERT, and neither was numbered in section 5.**
  D15b ("the twelve `examples/` files stay byte-identical to `36f7890`") and
  D22b ("every library-API locus is byte-identical, so this unit pre-empts no
  M3.6a doc work") are claims about M3.5b's OWN DIFF, asserted by comparing the
  WORKING TREE against the pre-unit baseline. That comparison is an over-claim
  which holds only until a later unit legitimately enters the scope, and
  D18-D23 are that unit. Both re-scoped to `36f7890` -> `1146421`, M3.5b's own
  range. D22b's own table dispositions
  `examples/hospital_ocr/README.md` `System.handle(...)` as KEEP **for M3.6a**,
  and the roadmap's M3.6a2 doc list (README 18 lines, `docs/architecture.md` 7,
  `docs/adapter-protocol.md` 8, `docs/threat-model.md` 4) does not name the
  example README, so this unit owns it. STANDING RULE for section 5 of any later
  contract: a scope pin asserted against the working tree expires; only a
  range-scoped assertion survives the next unit.
- **C08 — D25's register gate is discharged by CLASSIFYING, never by
  defaulting.** It treats an unclassified sentence opener as a failure, and it
  diffs by PARAGRAPH, so rewriting one bullet of a list drags every sibling
  bullet in. Five imperative openers (`canonicalize`, `export`, `isolate`,
  `keep`, `treat`) and 23 descriptive openers were classified. The gate working
  as designed.
- **C09 — the demo's own verification count was a NAMING device, and it is
  re-derived rather than relaxed.**
  `test_the_offline_phase_runs_on_the_verified_bytes_after_teardown` pinned
  `len(verifications) == 1` to name the document Act 6 carries. D19 makes it 4:
  one checkpoint per artifact promotion, one `resolve` per answering act. The
  re-derivation adds the one-entry-versus-two-entry inequality, which is the
  assertion that PROVES the checkpoint moved.
- **C11 — `SURVIVING-MIGRATE` counts DEFINITIONS; section 3's "26 sites" does
  not.** The gate-2 baseline of 26 is 25 test-tree definitions plus the demo,
  measured as STALE 25 + SURVIVING-MIGRATE 1 the moment the test tree landed.
  Those 25 definitions hold 28 `handle` CALL SITES, which is why `SITES` has 28
  rows. Post-migration the census reads 23 RETAIN definitions over 45 surviving
  lifecycle sites. Three different denominators, all live in this unit's prose:
  quote the unit with its noun.

---

## 11. Interpretive grounds

Recorded where a later reader would otherwise re-litigate them.

- **The census and the shape table are different axes and both are needed.** The
  census answers "may this site move"; the shape table answers "what does this
  site claim". A migration driven by the census alone silently deletes the
  MISS-GUARDED claim at four sites; a migration driven by the shape table alone
  has no completeness predicate.
- **`propose` is retained at MISS-GUARDED sites even where its identifier is
  unused.** P1's equivalence is a claim about row state. Dropping the call to
  keep the diff small would break the claim the unit rests on.
- **`prefix` is removed rather than kept.** See D12.
- **The two ACTOR sites are not a scope reduction.** They were already inside
  M3.6a2's deletion set; this unit only stops pretending they are migratable.

---

## 12. Verdict table — PENDING (S3)

## 13. Attack table — PENDING (S3)
