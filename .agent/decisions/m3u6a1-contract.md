# M3.6a1 acceptance contract — migrate every consumer off the lifecycle API

Unit: M3.6a1. Tier `kernel`, tags `-`, depends M3.5b.
Scope source: `.agent/roadmap.md` M3.6a1. Split grounds: `.agent/roadmap.md` M3.6a.

M3.6a1 moves every consumer off `System.handle` / `System.request_status` **while
both still ship**, so M3.6a2's deletion opens against a tree that no longer
depends on them. Nothing is deleted here. The gate stays green throughout, which
is the whole point of the consumer-migration-before-deletion axis: the old and
new APIs ship simultaneously, so the migration is verifiable against both.

Section 12 is written (S5). Section 13 is PENDING; S6 rules it.

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
| Site shapes | ACTOR 2, MISS-GUARDED 4, HIT 7, AMBIGUOUS 2, FACTORY 51, UNOBSERVED 6 | `m3u6a1-fallback.json` |
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

### HIT — 7 sites

`handle` ANSWERED from the artifact — a `Resolved` outcome — so the site pins a
hit. Every one is already RETAIN.

### AMBIGUOUS — 2 sites

`tests/test_system.py:485` and `:584`. A once-promoted artifact was present and
`handle` REFUSED TO CHOOSE, a `ReconciliationRequired` outcome. It neither
answered nor supervised, so the site pins neither a hit nor a declared miss.
Split out of HIT by C01 and C18; both are RETAIN, so no migration ruling depends
on the split and the taxonomy's truth does.

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
- **D29** `m3u6a1-premise.py` GRADES its two premises rather than printing them:
  it names the findings it expects, reports `RESULT: PASS`, and exits nonzero on
  any divergence. A command that returns 0 for every possible output cannot fail,
  so recording its rc as a passing gate asserts a check that never ran.

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
| 9 | Reversion sweep | `uv run python .agent/decisions/m3u6a1-mutants.py` | `RESULT: PASS`, named survivor set, control GREEN |

Every gate reruns from committed state with its SHA recorded. Gate 2 is the
acceptance gate and is RED at baseline by construction (`SURVIVING-MIGRATE: 26`).
Gate 9 is section 7's catalogue; it carries its own structural grade
(`--validate`) and its own both-ways credential (`--self-test`), so the
instrument is checkable before any verdict it reports.

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

Gate 9 for this unit is a REVERSION catalogue: a migration is bound by restoring
what was migrated away, never by mutating what remains. One row per battery
clause, tagged `reversion` or `sensitivity`, each row's `target_test` named, and
`killed` attributed separately from `misdirected`. See C20 for the number.

One clause carries no row. D28's subject is the commit set
`git rev-list 6fb4d92..HEAD -- ...` returns, so every mutation this catalogue can
express edits the working tree alone and leaves that history byte-identical: the
clause is INSENSITIVE by construction, and a row for it would certify only that
it ignores the mutation. It was also red at baseline, so it already holds the
credential this instrument supplies to clauses that are green there. The
exclusion is grounded in `m3u6a1-mutants.json` and printed on every control line,
because a verdict set is not quotable without the clauses it omits.

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
- **S4** DONE — wave-2 STAGING. Both graders authored and graded both ways from
  committed state, the attack table seeded, and two diff-blind worktrees staged
  at `6fb4d92`. `main=` 85% 205K/240K, no teammate dispatched. Re-sized to SIX
  sessions here: MAIN reached 82% having read only this contract and authored the
  two graders, so a session that BUILDS the graders cannot also dispatch and
  harvest them. Entry cost, not the work, is the driver.
- **S5** DONE — wave-2 dispatch, harvest, the red-at-baseline / green-at-HEAD
  battery run, and section 12. `main=` 98% 236K/240K, `mate=` 73% 174K/240K.
  Section 13 stayed PENDING: ruling 36 attack rows is a session of MAIN-only
  judgment, so the plan's single wave-2 session was two.
- **S6** DONE — attack ruling (36 rows, 5 ACCEPTED) plus the three instrument
  repairs those rulings forced (C18, C19) and the V08 repair. `main=` 88%.
  The unit re-sized to SEVEN sessions here.
- **S7** DONE — gate 9's instrument: `m3u6a1-mutants.py` plus the 29-row seed,
  graded both ways with 12 controls firing, D28's exclusion grounded. `main=` 87%
  208K/240K, no teammate dispatched. Re-sized to EIGHT sessions on the same
  measurement S4 made and named: a session that BUILDS a grader cannot also
  dispatch and harvest it. Entry cost is the driver — MAIN read this contract and
  the battery's clause set and was at 66% before the first line of the harness.
- **S8** DONE — the catalogue filled to 92 rows, MAIN's decisive sweep, C22-C26,
  and closure. Section 14 is the sweep record. All nine gates green from
  committed state:

  | # | result |
  | --- | --- |
  | 1 | `Ran 979 tests in 352.354s`, `OK` — floor 949 met |
  | 2 | `SURVIVING-MIGRATE: 0`; `MEASURE-DRIFT`, `UNGROUNDED-OVERRIDE`, `BAD-VERDICT` all 0; 23 definitions / 45 sites / 23 RETAIN; `RESULT: PASS` |
  | 3 | `IN-SYNC` |
  | 4 | `RESULT: PASS` |
  | 5 | `RESULT: PASS`; P1's one differing cell is `events.rows:row1.payload_json`; P2 reproduces both halves |
  | 6 | `no-op` on both runs, tree clean afterwards |
  | 7 | rc 0, UNCHANGED — 28 leaves / 35 nodes, `parser_shape` 151 / `ebd2ac811bd9776d` |
  | 8 | rc 0, every check ok |
  | 9 | `CONTROL: GREEN`, 92 mutants, `KILLED: 92`, `MISDIRECTED: 0`, `SURVIVORS: 0`, `PATCH-NOOP: 0`, `RESULT: PASS` |

  Section 12's grader re-run after C22-C26: `OBLIGATIONS: 30`, `TESTS: 30`,
  `CORRECTION-UNCITED: 0`, `RESULT: PASS`, self-test all controls firing.
  The unit closes at EIGHT sessions against a plan of three.

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
  submission by raw `UPDATE` under `PRAGMA foreign_keys = OFF`. This binds D01
  and D15: completeness is not "no site still calls the old method", it is that
  every migrated site still forces what it forced before.
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
  M3.5b's D15b ("the twelve `examples/` files stay byte-identical to `36f7890`")
  and M3.5b's D22b ("every library-API locus is byte-identical, so this unit
  pre-empts no M3.6a doc work") are claims about M3.5b's OWN DIFF, by comparing the
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
- **C08 — M3.5b's D25 register gate is discharged by CLASSIFYING, never by
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
- **C10 — a CROSS-CONTRACT obligation citation collides with a live local id,
  and the collision is invisible to a reader who knows the local numbering.**
  C07 cited `D15b` and `D22b` and C08 cited `D25`, all three of them M3.5b's
  obligations. `D15b` and `D22b` name nothing here, so they read as foreign; this
  contract's own D25 is M3.3's P06 byte-span freeze, so C08 read as correcting a
  freeze it never mentions. Found by `m3u6a1-battery-validate.py`, which binds a
  correction to every obligation id its text names and therefore bound C08 to
  D25: a diff-blind author would then have encoded the register gate into the
  byte-span test and gone red against correct code. All three citations now carry
  their owning unit, and the parser treats a `M<n>.<n><x>` qualifier as marking
  the id foreign. STANDING RULE: cite another unit's obligation with its unit
  name attached, because the number alone is not a key. C10 was also the id this
  section skipped in drafting; assigning it here closes the gap rather than
  leaving an unassigned number that reads as a lost correction.
- **C11 — `SURVIVING-MIGRATE` counts DEFINITIONS; section 3's "26 sites" does
  not.** The gate-2 baseline of 26 is 25 test-tree definitions plus the demo,
  measured as STALE 25 + SURVIVING-MIGRATE 1 the moment the test tree landed.
  Those 25 definitions hold 28 `handle` CALL SITES, which is why `SITES` has 28
  rows. Post-migration the census reads 23 RETAIN definitions over 45 surviving
  lifecycle sites. Three different denominators, all live in this unit's prose:
  quote the unit with its noun. This binds D01, whose `SURVIVING-MIGRATE: 0` is a
  count of DEFINITIONS, and D05, whose "23 RETAIN definitions" is a third
  denominator again.

- **C12 — D10's and D14a's "41 call sites" is the BASELINE population, and one
  RETAIN consumer legitimately leaves it.** Measured by AST: `self.confirm(...)`
  is 41 at `6fb4d92` and 40 at the shipped tree, and the single departing owner
  is `test_operation_revision_invalidates_every_old_request_path` — C03's own
  third repair, which re-bases that test onto a direct `handle` + `review` plant
  because migrating `confirm` changed what it plants. So D10's real obligation is
  that no SURVIVING `self.confirm(...)` call passes a `request_id` argument, over
  all 40; the count 41 describes the population the migration started from. The
  battery pins WHICH owner left rather than the arithmetic alone, which is
  strictly stronger: an accidental deletion of any other call site fails it while
  the recorded repair passes. Same correction carries D14a's identical literal.
- **C13 — `self` and `cls` are outside D14's domain.** D14 reads "no migrated
  helper retains a parameter that no statement in its body reads", and
  `tests/test_resolve_battery.py::_confirm` is a method whose migrated body never
  touches `self`. Removing a bound receiver rewrites the call convention of every
  caller and is not a migration residue, so the literal reading over-quantifies.
  D14's domain is the parameters the migration itself could drop. Binds D13 and
  D14, whose shared helper made the same over-quantification twice.
- **C14 — section 1's "Call sites" column carries TWO measurement conventions and
  labels neither.** The three `tests/test_system.py` rows are AST-true (`confirm`
  41, `_confirm_scope` 65, `_promote_scope` 14). The other three are fixed-string
  counts that include the `def` line: `_promoted_conflict_fixture` reads 7 for 6
  calls, `_promoted_example_ledger` 4 for 3, `_confirm` 2 for 1. Same family as
  P06's slicing-convention table and the `parser_shape` digest-algorithm rule —
  state the algorithm beside every recorded number, because a consumer of the
  wrong convention reports correct code as stale. The AST counts are binding, and
  this correction binds D13, whose per-helper call expectations read that column.
- **C15 — section 7's preservation set is FIVE and the measured set is SIX.** The
  baseline run makes it D04, D22, D24, D25, D26 and D27 green at `6fb4d92`, 23
  red. D22 belongs there: the shipped transcript test asserts exactly one match
  per mask both before and after the act structure moves, so the obligation holds
  at baseline exactly as the four freeze pins do. Report the split, never force
  it — and derive the set from the run rather than from the contract's list.
- **C16 — P1's "exactly one differing cell" is FALSE without its projection.**
  Attack A14. `m3u6a1-premise.py` reports SIX differing columns and classifies
  five VOLATILE: `events.rows:row1.subject_id`, `row2.subject_id`,
  `row2.payload_json`, `examples.rows:row0.receipt_hash` and `receipt_json`. C02
  separately concedes `requests.id` is caller-chosen under `handle` and minted
  internally under `propose`, so the literal row state differs in primary keys,
  foreign keys, event subjects and receipts. P1 reads: after an identity
  isomorphism that drops minted identifiers and every column derived from them,
  EXACTLY ONE attributable difference survives, `events.rows:row1.payload_json`.
  The projection is the claim's premise and is stated with it, never assumed.
  Binds D07, which cites P1 for site-by-site row-state equivalence.
- **C17 — C11's third denominator moved for a reason C11 does not give.** Attack
  A18. The seed census at `8592c34` totals 23 RETAIN definitions over 44 sites;
  shipped totals 23 over 45. The entire increment is
  `tests/test_system.py::test_operation_revision_invalidates_every_old_request_path`,
  6 sites → 7, gaining `tests/test_system.py:880`. Cause: that test's subject IS
  the caller-chosen request-id route, and migrated `confirm` cannot carry a
  request id, so `self.confirm("old-confirmed")` was inlined into the direct
  `self.system.handle(..., request_id="old-confirmed")` plus `self.system.review(...)`
  pair it always was underneath. The call did not appear — it became VISIBLE.
  ONE event moves two denominators in opposite directions: `confirm`'s callers
  41 → 40 (C12, measured 40 today) and RETAIN sites 44 → 45. A denominator that
  moves without its cause recorded is a number no later reader can audit.
- **C18 — D09's "per-call positive control" was false, and gate 4 certified a
  taxonomy C01 calls false.** Attacks A19 and A16. `m3u6a1-fallback.py:130` gated
  the digest control on `isinstance(outcome, ReviewRequired)`, so every
  `Resolved`, `ReconciliationRequired`, `FallbackFailed`, `InProgress` and raising
  path skipped it — 24 checked over 17 site rows — and the one global counter
  named no site. Separately the shape rule keyed HIT on
  `outcomes != {ReviewRequired}`, collapsing "answered" with "refused to choose",
  and printed `HIT: 9` while C01 says seven. Both repaired: the control reads
  `requests.input_hash` for every returning call and attributes each verdict to
  its site (46 checked, 3 sites raise on every call and carry no request id), and
  `AMBIGUOUS` splits the `ReconciliationRequired`-only sites out of HIT, giving
  HIT 7 / AMBIGUOUS 2 at `tests/test_system.py:481` and `:582` — exactly C01's
  two. Credited by mutation: a site-selective wrong digest at
  `tests/test_system.py:277` now prints `CONTROL-SITE-FAILED` and `RESULT: FAIL`
  while the shape flips HIT 7 → 6 and FACTORY 28 → 29. Before the repair that
  same mutation left every counter clean.
  The committed `m3u6a1-fallback.json` is the FROZEN OPENING attribution, not a
  current-tree measurement: 72 targets against the migrated tree's 45, and the
  source of section 3's counts. Re-running `--emit` against the migrated tree
  destroys it. The corrected rule therefore reaches it through `--reclassify`,
  which replays `_shape()` over the table's OWN recorded fields and touches no
  measurement: 2 sites relabelled, `tests/test_system.py:485` and `:584` — again
  exactly C01's two — with ACTOR 2, MISS-GUARDED 4 and FACTORY 51 unmoved, and 0
  relabelled on a second run. A corrected rule replayed over frozen evidence is a
  repair; a fresh measurement written over frozen evidence is a loss.
- **C19 — gate 5 could not fail.** Attack Y05. `m3u6a1-premise.py` exited 0 while
  printing both final verdicts as `False`, and no obligation ran it, which is why
  the S5 gate list records gates 1-4 and 6-8 and skips it. Both `False` values
  were correct, which makes it worse: a reader is handed two negations beside a
  green rc and must already know the answer to read it. D29 now requires the probe
  to grade its expected findings and exit nonzero on divergence, and the verdict
  lines are restated positively so the printed value is the claim.
- **C20 — a GATE NUMBER is not a key across contracts either.** Section 7 called
  the reversion catalogue "gate 3 for this unit" while section 6's own table
  assigns gate 3 to the ruling-sync check. The 3 is M3.5b's, where gate 3 WAS the
  reinsertion sweep, and it collided with a live local number exactly as C10's
  cross-contract obligation citation did: a reader following section 7 would have
  graded closure on `m3u6a1-rule-census.py --check` and recorded a sweep that
  never ran. The catalogue is gate 9. Same standing rule, one namespace wider —
  cite another unit's gate with its unit name attached, because the number alone
  is not a key. This correction binds no obligation; its subject is section 7,
  and a correction may legitimately bind none.
- **C21 — the battery is THIRTY tests, and section 12 says 29.** The count was
  written in S5 and the thirtieth obligation landed in S6 under C19, so the
  number was stale one session after it was recorded. Measured from the shipped
  module by `m3u6a1-mutants.py --emit-stub`: `CLAUSES: 30`. The reversion
  catalogue covers 29 of them, the difference being section 7's one grounded
  exclusion. A count written before the last obligation lands is a denominator no
  later reader can audit — C17's defect arriving from the other direction, and
  the reason a closure session re-derives every number the contract asserts
  rather than quoting its own earlier text. Binds D29, whose late arrival is the
  cause.
- **C22 — section 7's "one row per battery clause" undercounts the instrument
  threefold.** Section 7 specifies "One row per battery clause, tagged
  `reversion` or `sensitivity`", and the S7 seed encoded exactly that at 29 rows.
  The sweep refuted it: a clause is a CONJUNCTION, so reverting one conjunct
  leaves the others asserting and a one-row-per-clause catalogue certifies only
  that each clause holds SOME live content. The delivered catalogue is 92 rows
  over 29 clauses — 53 `reversion`, 39 `sensitivity`, one row per SUBPROPERTY.
  The instrument was already subproperty-compatible: `CLAUSE-UNCOVERED` demands
  every clause be covered and nothing forbids a second row, so the prose was the
  only surface that disagreed. Read section 7's rule as ONE ROW PER SUBPROPERTY,
  with every clause covered at least once. Binds section 7's row rule.
- **C23 — the catalogue's own both-ways credential was row-count dependent, and
  12/12 was really 11/12.** `--self-test`'s `dropped row` control removed
  `rows[0]` and expected `CLAUSE-UNCOVERED`. That expectation holds only while
  rows are 1:1 with clauses. Once several rows covered one clause the drop left
  it covered, the control reported SILENT, and the instrument still printed a
  full 12/12 credential on the strength of the other eleven. Fixed at `0e91de9`:
  the control now drops the first row's WHOLE covering set, which is row-count
  independent; 12/12 fire at 92 rows. The generalisable rule — a control that
  mutates `rows[0]` is valid only where one row is the whole of the property it
  checks, and the scale-up that kills it is exactly what filling the catalogue
  does. Same family as V08: an instrument whose credential degrades as its own
  subject grows, read as evidence every run before it degraded.
- **C24 — three battery clauses assert subproperties they cannot observe.**
  Surfaced by the reversion sweep, then verified from committed artifacts rather
  than from the report that raised them. **This correction binds no obligation,
  and the omission is deliberate: all three obligations are unchanged, and what is
  defective is the METHOD ENCODING each of them.** The steering targets are
  therefore named as test methods with their line numbers, and the repairs are
  registered in `.agent/polish.md` rather than folded into obligation text:
  - **`test_d17_multi_line_anchors_...` (`tests/test_migration_battery.py:1036`)
    holds a migrated-definition loop that is vacuous BECAUSE gate 2 passes.** It walks
    `_census()["definitions"]` and `continue`s on every verdict outside
    `{MIGRATE, MIGRATE-RESOLVE}`; the committed `m3u6a1-census.json` holds 23
    rows, all `RETAIN`. The body never executes. Gate 2's acceptance IS
    `SURVIVING-MIGRATE: 0`, so the clause iterates precisely the set another gate
    certifies empty — dead at the moment that gate goes green. Standing rule: a
    battery clause must never draw its work list from a post-state census whose
    emptiness is another gate's acceptance criterion.
  - **`test_d20_act_5_keeps_export_and_identity_...`
    (`tests/test_migration_battery.py:1152`) asserts
    `assertNotIn("becomes one exportable function")`, which never had a
    subject.** The baseline heading at
    `6fb4d92:examples/hospital_ocr/run_demo.py:348` reads "both promoted layouts
    **become** one exportable function". The asserted string differs by one
    character and existed at neither end, so the conjunct held vacuously at
    baseline and holds vacuously at HEAD.
  - **`test_d15_the_migration_lands_through_one_idempotent_script_m3u6a1`
    (`tests/test_migration_battery.py:950`) reports on two different artifacts
    under one clause.** Its idempotence
    half runs `repaired / SURGERY.relative_to(ROOT)` — the script COMMITTED
    inside the detached worktree — while its cardinality half runs
    `_copy_surgery()`, which copies the WORKING-TREE script. An edit to the
    working-tree script moves the second half and cannot move the first.

  None of the three clauses is wholly dead; each retains live conjuncts, which is
  why M16, M21 and M66 were retargeted onto reachable failures and the catalogue
  still covers all 29 clauses. Section 7's acceptance bar is OBLIGATION-level —
  the battery "must fail when one obligation remains undone" — and that bar is
  met. These are CONJUNCT-level weaknesses: they are registered in
  `.agent/polish.md` with acceptance checks, they do not gate closure, and they
  must not be repaired silently, because every repair edits the battery and
  invalidates gate 9's committed-state binding.
- **C25 — section 7's coverage sentence and section 12's floor arithmetic both
  stop one obligation short.** Binds no obligation; its subjects are two prose
  surfaces. Section 7 describes the battery as one test per obligation over a
  range ending at the twenty-eighth, so the lettered obligation added in S2 and
  the thirtieth added in S6 under C19 both sit OUTSIDE the sentence that defines
  the battery's own coverage. Section 12's ruling on the whole-gate red then
  prints the suite floor as `978 - 29` where the shipped pair is `979 - 30`. The
  floor is 949 either way, which is exactly why the arithmetic survived three
  sessions unread: a stale term inside an expression whose VALUE is still right
  leaves no failing check anywhere. Measured at closure by
  `m3u6a1-battery-validate.py`: `OBLIGATIONS: 30`, `TESTS: 30`, `UNCOVERED: 0`,
  and gate 1 `Ran 979 tests in 352.354s, OK`. The battery covers everything; the
  prose describing it does not. C21 corrected the COUNT in section 12 and left
  the RANGE in section 7 and the arithmetic in section 12's own ruling standing —
  a correction repairs the sentence it was written against, never the family.
- **C26 — the correction-binder's fold stopped at the first NESTED sub-bullet, so
  a correction naming three clauses bound one.** Binds no obligation; its subject
  is `m3u6a1-battery-validate.py`. `BULLET_CONT` was `^  \S` — a continuation
  line indented EXACTLY two spaces. A nested sub-bullet indents its own
  continuation deeper, so folding C24 stopped 265 characters in, at the first
  four-space line, and the binder saw only the ids appearing before that point.
  It then reported `IN SYNC` on a binding it had silently truncated: the counter
  cannot see an id it never read, which is the fail-open shape this project
  already rules against for forbidden lists and closed allowlists, arriving in a
  text folder. Fixed to `^ {2,}\S`. Measured both ways before and after: under
  the widened rule every correction from C01 to C21 binds an IDENTICAL set, so
  the defect had never once bitten — C24 is the first correction in this contract
  written with nested sub-bullets, and it found the bug by being the first input
  of a shape the folder never had. An instrument that has only ever seen one
  input shape holds no credential for the next one.

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

## 12. Battery verdict table (S5)

Battery = `tests/test_migration_battery.py`, 29 tests, one per obligation
D01-D28 plus D14a, authored diff-blind by `test-m3u6a1-1` at
`wt/test-m3u6a1-1` based at `6fb4d92`, graded by
`m3u6a1-battery-validate.py` (`UNFILLED`, `UNCOVERED`, `ORPHAN`,
`ASSERTIONLESS`, `SKIPPED`, `CORRECTION-UNCITED` all 0, `RESULT: PASS`).

**Credential = red at baseline / green at HEAD, and the split is reported
rather than forced.** At `6fb4d92` with the CURRENT `.agent/decisions/`
overlaid: 23 red, 6 green (D04, D22, D24-D27), `Ran 29 in 64.365s`. At HEAD:
7 failures over 5 distinct tests, all ruled below, then 29/29 green.

Every red is classed SUITE (the battery is wrong), CONTRACT (MAIN's text is
wrong) or CODE (the shipped tree is wrong). A red is a specification question
first and a repair second.

| id | red | class | ruling |
| --- | --- | --- | --- |
| V01 | D10 `len(current_calls) != len(baseline_calls)`, 40 vs 41 | CONTRACT | C12. 41 is the baseline population; C03's third repair moves one RETAIN consumer off `confirm`. Battery re-anchored to 40 and now pins the departing owner by name. |
| V02 | D14a `len(_attribute_calls(tree, {"confirm"})) != 41` | CONTRACT | C12, same measurement. |
| V03 | D13 `_unused_parameters(helper) == {'self'}` | SUITE + CONTRACT | C13. `self`/`cls` are protocol-bound receivers, outside D14's domain; the helper excludes them. |
| V04 | D14 `_unused_parameters(helper) == {'self'}` | SUITE + CONTRACT | C13, same helper defect. |
| V05 | D13 baseline calls 6 vs 7 and 3 vs 4 | CONTRACT | C14. Section 1's counts for these three helpers are def-inclusive fixed-string counts; the AST counts are binding. |
| V06 | D21 `\b35\b` absent from the refusal test | **CODE** | The shipped `tests/test_hospital_ocr_example.py:909` still read "erase all 38 of them" while the migrated demo holds 35 `ast.Assert` nodes. S3 recorded "D21's verdict count re-derived 38 -> 35"; that re-derivation reached the roadmap and never reached the shipped surface. Fixed. |
| V08 | D28 `subprocess.TimeoutExpired` on a nested `unittest discover` — WHOLE-GATE red at `abb6b06` | INSTRUMENT-REPAIRED (S6) | D28 runs the FULL suite as a subprocess, and the battery is a MEMBER of that suite, so every battery-bearing revision re-entered D28 and the nesting alone exhausted the 600 s timeout. Cost grows with the count of battery-bearing revisions, so S5's reading that gate 1 "measured OK, the property holds" was an artefact of depth: at `f548f88` one of three revisions carried the battery; at `abb6b06` two of four did, and the whole gate went red — `Ran 978 tests in 997.691s`, `FAILED (errors=1)`. Repair = each checkout drops `tests/test_migration_battery.py` before the inner run, which is what the pre-existing floor of 949 (= 978 − 29) already assumed. D28 alone: `Ran 1 test in 338.592s`, `OK`, 4 revisions at ~85 s each. |
| V07 | D16 replay divergence on `tests/test_hospital_ocr_example.py` | INSTRUMENT-CORRECT | D16 fired because V06's fix was a HAND edit outside `m3u6a1-surgery.py`. Routed into `TEXT` with its expected-count assertion; gate 6 reports `no-op` on the second run and the replay reproduces the shipped tree. |

**V06 is the wave's whole return and the class the battery exists to reach.**
Six of seven reds were instrument or contract defects; one was a stale number in
shipped bytes that no gate could see, because nothing pinned a comment. The
battery's D21 clause now binds that prose to the module's own `ast.Assert`
count, so a later act-structure change fails loudly instead of leaving the number
behind. Eighth consecutive unit whose findings are dominated by claim defects in
MAIN's own text — and the first in this unit where one of them had reached code.

**V07 is D15/D16 working, not a defect.** A hand repair to a generated tree is
exactly what C05 forbids, and the replay obligation caught it within one gate
run. The generalisation is the project's own standing rule, now with a measured
instance: a repair to a script-generated artifact lands IN the script.

**V08 is the one finding a green gate concealed.** An instrument that includes
itself in its own subject does not fail at the boundary it crosses; it fails when
the population it measures grows one member past the timeout, and every earlier
run reads as evidence that the property holds. S5 had the whole diagnosis —
"a test inside gate 1 cannot verify gate 1 about itself" — and still deferred,
because the gate was green THAT run. The rule the deferral broke: a check whose
cost scales with the thing it checks is not stable, and a green reading from an
unstable check is not evidence. Ruling on the instrument's SHAPE never needs to
wait for it to go red.

## 13. Attack table — RULED (S6)

`.agent/decisions/m3u6a1-attack.json`, 36 rows (30 seeded A01-A18 + Y01-Y12, 6
extension A19-A21 + Y13-Y15), filled diff-blind by `rev-m3u6a1-1`. Every row is
disposed through `m3u6a1-rule-attack.py`, idempotent, `--check` asserting the id
set so a later row cannot go undisposed: `IN SYNC: 36 rows disposed`. Reviewer
severities: 12 blocking, 22 material, 2 cleared. MAIN's dispositions: **5
ACCEPTED, 27 SCOPED, 2 CLEARED, 2 DEFERRED**.

**The discriminator.** Nearly every row proves the same thing: a gate predicate
is NECESSARY and not SUFFICIENT. For a tripwire that is the normal condition, not
a defect — it becomes one exactly where the contract calls the tripwire a proof.
So the disposition splits on the ARTIFACT, not on the attack's strength. ACCEPTED
where something shipped is false today; SCOPED where the wording outran the
instrument, with the real domain named.

**Five ACCEPTED, each verified before ruling and each repaired in S6.**

| id | what was false | repair |
| --- | --- | --- |
| A16 | gate 4 printed `HIT: 9` and `RESULT: PASS` while C01 says seven | `AMBIGUOUS` split; frozen table reclassified; C18 |
| A19 | D09 called the digest control `per-call`; it ran on `ReviewRequired` alone, 24 of 46 | control on every returning call, site-attributed; C18 |
| Y05 | gate 5 exited 0 for every possible output and no obligation ran it | D29 + graded findings + `RESULT: PASS`/`FAIL`; C19 |
| A14 | P1 claimed `exactly one differing cell`; the probe reports six | C16 states the identity projection as the claim's premise |
| A18 | C11's `45` had no locus and the seed measures 44 | C17 names `tests/test_system.py:880` and its cause |

**A18 is the one that taught something new.** The 44 → 45 increment is entirely
`test_operation_revision_invalidates_every_old_request_path`, 6 sites → 7. That
test's subject IS the caller-chosen request-id route, and migrated `confirm`
cannot carry a request id, so `self.confirm("old-confirmed")` was inlined into
the direct `handle` + `review` pair it always was underneath. The call did not
appear — it became VISIBLE. ONE event moves two denominators in opposite
directions, `confirm`'s callers 41 → 40 and RETAIN sites 44 → 45, and the
contract recorded the second without its cause. A denominator that moves without
its cause recorded is a number no later reader can audit.

**The wave-2 design paid off where it was designed to.** Two teammates who never
saw each other's work: the attacker's evasions are answered by obligations the
diff-blind encoder wrote independently, and in four cases the encoder asserted
MORE than the contract sentence it was encoding.

| attack | answered by | how |
| --- | --- | --- |
| Y10, Y11, Y12 | D04 | `git diff --exit-code 6fb4d92 -- src`, the WHOLE tree, not D27's six-module allowlist |
| A03 | D05 | `_consumer_map(ROOT) == retained`, a qualified-name → count map, not a cardinality |
| A02 | D03 | each RETAIN definition's AST count against the COMMITTED census row |
| A09, Y06 | D16 | replay from an explicit detached baseline, not `git checkout --` against the index |
| A13 | D28 | the per-commit ledger the attack's own reproduction specifies |
| A06, Y04 | frozen `m3u6a1-fallback.json` | 72 opening targets read by `_shape_owners`, not a fresh run |

That last row corrects MAIN's own first reading of A06 and Y04, which said the
frozen opening set was missing. It is not: the committed attribution table IS
that set, which is why D07 resolves four MISS-GUARDED owners while the live gate
reports zero. What is genuinely absent is the REPLACEMENT-side half — nothing
asserts what stands at each frozen site today — and that belongs to M3.6a2.

**The one class no instrument in this unit can close.** The census and the shape
table are re-derived from the current tree, so a DELETED consumer and a MIGRATED
one leave identical evidence (A01, A06, Y02, Y03, Y04). No re-derived census will
ever close it. M3.6a2 does, structurally: once `handle` and `request_status` do
not exist, every evasion spelling in A01 raises `AttributeError` and absence
stops being measured. Section 7's language must read `no measured direct call
survives`, never `every consumer stopped`.

**Deferred, both to the polish register.** Y07 duplicates an OPEN M3.5b row
owning `parser_shape`'s field set; Y08 belongs to M3.5b's doc parser and its
corpus. Neither leaves this unit exposed: D04's whole-`src` byte pin is stricter
than gate 7 on the premise Y07 threatens, and this unit ships no new command
prose.

## 14. Reversion sweep — DECISIVE (S8)

Catalogue = `.agent/decisions/m3u6a1-mutants.json`, **92 rows over 29 clauses**
(53 `reversion`, 39 `sensitivity`, every row `expect: killed`). MAIN seeded 29
rows at S7; `gate-m3u6a1-1` filled them and extended to 92 at
`wt/gate-m3u6a1-1` @ `96d155d`, harvested into `0e91de9` by targeted checkout
proven sha256-identical. Structural grade `RESULT: PASS`; `--self-test`
`RESULT: PASS` with 12/12 controls firing after C23's repair.

**MAIN's decisive rerun, from committed state at `0340631`, on a box with no
other job running:**

    uv run python .agent/decisions/m3u6a1-mutants.py --json /tmp/m3u6a1-decisive.json

    VERDICT-MODULES: tests.test_migration_battery
    VERDICT-TARGETS: 29          D28 excluded, grounds printed on the control line
    CONTROL: GREEN
    MUTANTS: 92
    KILLED: 92
    MISDIRECTED: 0 []
    SURVIVORS: 0 []
    NAMED-SURVIVOR-SET: 0 []
    PATCH-NOOP: 0 []
    UNEXPECTED-SURVIVORS: 0 []
    RESULT: PASS

97 min 23 s wall over 93 battery runs (1 control + 92 mutants) = **62.8 s per
run against the 78.3 s S8 measured before dispatch**. The sizing miss is the ROW
COUNT, not the cost: S8 sized ~40 min for 30 runs, per-run cost came in 20 % under
forecast, and the catalogue tripled underneath it. A sweep is sized by the
catalogue the FILL produces, never by the one the seed ships (C22).

**The empty named-survivor set is the strongest form, not an unfilled field.**
The standing rule replaces a "zero survivors" predicate with a NAMED survivor set
so a later fifth survivor fails while the ruled four do not. Here the named set is
empty because no clause was granted equivalence: every row declares
`expect: killed` and every row killed, so `UNEXPECTED-SURVIVORS` and `SURVIVORS`
coincide and any future survivor fails the gate outright.

**Three rows were retargeted before the decisive run, and the retargets are this
campaign's whole return.** Each first verdict was a true finding about the SHIPPED
clause, ruled at C24 and registered for repair; each row was then aimed at a
reachable conjunct of the same obligation, so coverage of all 29 clauses survived.

| row | clause | first verdict | blind subproperty of the shipped clause | retargeted onto |
| --- | --- | --- | --- | --- |
| M16 | D15 | `misdirected` | idempotence half runs the script COMMITTED in a detached worktree, so a working-tree mutation cannot reach it; the duplicated `main` then aborts in `_qualified()` before TEXT cardinality runs | the exit contract — convert the surgery abort to rc 0 and D15's repeated-fragment probe goes silently green |
| M21 | D20 | `misdirected` | asserts `"becomes one exportable function"`; the baseline heading reads `become`, so the conjunct held at both ends | the ordered lifecycle spine — restore the pre-migration act flow and `propose`, checkpoint and `resolve` leave D20's ordering |
| M66 | D17 | `survived` | the "all migrated definitions" loop reads the POST-migration census, which gate 2 certifies holds zero `MIGRATE` rows, so deleting a `SITES` rule passes vacuously | the second-run no-op guarantee — an unchanged tree prints `applied:` instead of `no-op` |

Measured chain, restated here because its `/tmp` outputs are not tracked: base
29-row sweep **27 killed / 2 misdirected** (M16, M21); focused 92-row diagnostic
**91 killed / 1 survived** (M66); per-row repair runs then returned M21 killed on
9 witnesses, M16 and M62 killed on 1 each, M66 killed on 1. M21's nine witnesses
are worth naming: restoring a whole demo act flow reddens nine clauses at once, so
the row proves D20 is AMONG its killers rather than that D20 uniquely owns the
property. A blunt row still satisfies `killed`; it is weaker evidence than a
one-witness row and the catalogue does not currently distinguish them.

**Instruments and evidence this unit's closure rests on, all committed:**

| artifact | what it holds |
| --- | --- |
| `m3u6a1-census.json` + `m3u6a1-census.py` + `m3u6a1-rule-census.py` | gates 2-3; 23 definitions, 45 sites, `SURVIVING-MIGRATE: 0` |
| `m3u6a1-fallback.json` + `m3u6a1-fallback.py` | gate 4, the frozen 72-site shape attribution |
| `m3u6a1-premise.py` | gate 5, P1 and P2 graded rather than printed (C19) |
| `m3u6a1-surgery.py` | gate 6, the one idempotent migration script |
| `m3u6a1-mutants.json` + `m3u6a1-mutants.py` | gate 9, this section |
| `m3u6a1-verdicts.json` + `m3u6a1-battery-validate.py` | section 12's battery verdict table |
| `m3u6a1-attack.json` + `m3u6a1-rule-attack.py` | section 13's 36 ruled attack rows, `--check` in sync |

**Retained `wt/` branch tips — MILESTONE-REVIEW dispatches from these.** Their
worktrees are removed; the branches stay because they are the only refs keeping
these SHAs resolvable, and no ruling rests on them — every ground is restated
above as a measured fact.

| branch | tip | based at | what it carries |
| --- | --- | --- | --- |
| `wt/test-m3u6a1-1` | `5e604b7` | `6fb4d92` | the diff-blind battery as authored, before MAIN's V01-V08 reconciliation |
| `wt/rev-m3u6a1-1` | `82e1a2e` | `6fb4d92` | the 36-row attack table as filled, before MAIN's dispositions |
| `wt/gate-m3u6a1-1` | `96d155d` | `915c91e` | the 92-row catalogue as filled, plus its 22 fill commits |
| `wt/scout-m3u6a2` | `03b5da9` | `915c91e` | M3.6a2's re-measured deletion burden and the repaired `m3u6a-burden.py` |
