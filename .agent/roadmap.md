# Roadmap

## Scope source

README paragraph 1 is authoritative: aggregate repeated work into a regular, if large, function covering
many situations and edge cases; once built and verified, that function is deterministic. M2-M4 reconcile
the project to it. Paragraph 1 states the goal, so alignment work moves the system toward it and never
narrows the paragraph to fit the code.

Measured gaps driving the arc:

- `that function` has no referent. Verification is per artifact - own fixtures plus 4 negative probes
  (`system.py` `_run_verification`). No aggregate identity, coverage measure, cross-entry check, or export.
  An artifact is one input-output pair (`artifacts.py` `build_exact_lookup`). -> M2.
- `if large` is operationally blocked. `verify <artifact_id>` and `promote <artifact_id> --scope-hash`
  are per entry (`cli.py`), so N situations cost N human-typed hashes. -> M2.
- Post-promotion determinism is revocable: revocation, ambiguity, integrity failure, suspension, or a new
  operation revision move a resolved input to fallback. A sealed ledger-free bundle makes the paragraph's
  determinism claim literally true. -> M2.
- Coverage of many situations is produced outside the boundary. Cement supplies the middle lookup; the
  input projection and output interpretation are unverified caller code
  (`examples/hospital_ocr/pipeline.py` `layout_signature`, `apply_plan`), and M1 review found three real
  defects in that projection which no Cement gate reaches. -> M4.
- Beyond the paragraph: bundled LLM-invocation runtime (`source.py`, `_command_supervisor.py`,
  `example_adapter.py`, `docs/adapter-protocol.md`), inline-proxy machinery (leases, request-ID
  idempotency, `in_progress`/`retry_failed`/`fallback_failed`/`reconciliation_required`), and the
  `authority(partition, actor, action, subject)` callback in a system the README calls not an ACL system.
  -> M3 trims all three.

## Milestone ledger

- M1 - Hospital OCR-to-JSON example - REVIEWED (`9e50bed..6f4f260`). Ships `examples/hospital_ocr/`
  (7-document corpus over 3 layouts, `pipeline.py`, `plan_adapter.py`, `run_demo.py`, walkthrough README)
  plus `tests/test_hospital_ocr_example.py`. Teaching claim: one durable pipeline replaces per-run bespoke
  LLM extraction, because each layout's plan is proposed once, supervised, then promoted. Review fixed
  three `layout_signature` canonicalization defects and bound the adapter's reference plans to locator
  compatibility. Gauges: implementing teammates 27-33%, MAIN 76-96%. Detail: `.agent/archive/m1.md`.

- M2 - Function as object - REVIEWED (`71c5eab..83198e1`; review read `6f4f260..e5ff481`). Makes the
  aggregate deterministic function a first-class, verifiable, exportable artifact, so paragraph 1's
  `regular, if large, function` and `once built and verified, that function is deterministic` become
  checkable properties instead of per-entry claims. Trust boundary stays exact-lookup: a function is a set
  of exact entries, never a wider predicate. Shipped across 16 units (u1..u5b, all DONE): the
  `cement-function-v2` document, hash and pure evaluator; set-level `verify_function` checks P1-P6;
  pre-promotion `entry_seal` identity plus batch draft verification; persisted `function_receipts` +
  `function_memberships` at `SCHEMA_VERSION` 2 with one-hash set promotion; receipt discovery and
  historical reconstruction; `function_report` over a frozen build anchor and an operation-now anchor; the
  eight-leaf `function` CLI group (`show`, `receipts`, `verify-drafts`, `verify`, `inspect`, `promote`,
  `export`, `eval`) on one `_Outcome` seam with exit 6 as the negative-verdict class; the hospital example
  resolving a layout offline from an exported bundle; and a docs claim pass over `README.md` plus
  `docs/`. Suite 81 -> 548. Gauges: `main=` 62-100%, teammate `impl=`/`mate=` 44-92%. Detail - per-unit
  records, design forks, review findings, known limits: `.agent/archive/m2.md`.

- M3 - Trim to paragraph scope - IN-PROGRESS (plan `bbac234..`). Removes behavior outside `turns
  repeatedly supervised LLM answers into narrowly scoped deterministic behavior`. Owner-approved seeds:
  (a) `CandidateSource` protocol stays in core while `CommandCandidateSource`, the subreaper/process-group
  supervisor, `example_adapter.py`, and `docs/adapter-protocol.md` relocate to an optional example
  surface; (b) the `authority()` callback goes, keeping reviewer and actor recording, which supervision
  genuinely requires; (c) the request lifecycle (leases, request-ID idempotency, `in_progress`,
  `retry_failed`, `fallback_failed`, `reconciliation_required`) is replaced by an explicit proposal
  submission plus a pure read-only `resolve`, leaving request lifecycle to the caller. Schema bumps once
  to 3; no migration path pre-1.0.

  Track order = (b) -> (c) -> (a): (b) is schema-neutral and independently landable, and landing it first
  stops (c) from building an authority gate on the new submission API only to delete it; (a) waits
  because its retained protocol names `CandidateRequest.request_id`, which (c) deletes, and because
  moving it earlier leaves the core CLI unable to turn a miss into a proposal.

  Correction to this roadmap's own prior wording: M2 did NOT reshape the dispatch path. All ten
  dispatch-path functions and the `requests` table are byte-identical across `3b7769b`, `6f4f260`,
  `71c5eab`, `83198e1` and HEAD (`handle` `cd60036faf5c`/12,867 B; `requests` `97190cf406eaa75e`/2,265 B).
  The scheduling conclusion survives for a different reason: M2 supplies the resolver target
  (`FunctionMatch`/`evaluate`) and adds request-bound report consumers that (c) must rewrite.

  Schema cuts ONCE, at M3.6b. M3.3-M3.6a keep `SCHEMA_VERSION` 2 and use private fresh request rows as
  internal storage plumbing that no public API exposes. The rejected expand-migrate-contract split
  (v3 compatibility columns, then v4 deletion) earns its second bump only where deployed operators cross
  it; under this milestone's own fail-closed no-migration contract nobody does, so it would uniquely pay
  two disposable transient test families plus two mid-milestone rewrites for zero operator value.

  Units - 15 after M3.6a's pre-open split, 7 DONE + 8 remaining. `depends` shows the DAG; same-wave units name the same
  predecessor. Tier default `kernel`; `oracle` is kept only where an independent implementation can
  actually diverge, so deletion, forwarding and byte-preserving relocation carry none.

  - M3.1 DONE tier=kernel tags=- depends=none - est calibration -> 1 session. Deleted the
    `authority()` callback and its scaffolds: `AuthorityCheck`, the constructor keyword,
    `_authorize` and all 11 call sites gone; both double-plan authorization windows collapsed to
    ONE locked plan; every actor/reviewer capture, validation, persistence and event survives;
    `store.py` byte-identical at `SCHEMA_VERSION` 2. Suite 548 -> 548 (11 deleted, 21 rewritten,
    11 added). `main=` 92% 220K/240K, `mate=` 54% 129K/240K.
    Contract `.agent/decisions/m3u1-contract.md` · detail `.agent/archive/m3-units.md#m31`.
  - M3.2a DONE tier=kernel tags=oracle depends=none - est 2 -> 3 sessions (1.50).
    Store-owned enforced-read capability behind an unchanged public seam: rolled-back
    transaction + deny-by-default authorizer allowlisting pragmas by NAME + percent-encoded
    existing-only `file:` URI `mode=ro`, classified by `sqlite_errorcode` alone. Both headline
    defects closed against a real ledger. Suite 551 -> 600; battery 49 tests / 22 obligations;
    19 mutants / 0 survivors. `main=` 93% 223K/240K (s1 75, s2 80), `mate=` 65% 155K/240K.
    Contract `.agent/decisions/m3u2a-contract.md` · detail `.agent/archive/m3-units.md#m32a`.
  - M3.2b DONE tier=kernel tags=oracle depends=M3.2a - est 3 -> 4 sessions (1.33).
    One-snapshot P1-P6 verification plus `evaluate` behind a pure `resolve`; failed
    verification, verified miss and verified hit stay distinct; 1/1,000/50,000 costs published
    with per-point provenance. +56/-1 production lines at `b5916a9`. Suite 600 -> 635; battery
    35 tests; 23 mutants / 1 ruled survivor closed by B34; differential 26 probes / 0
    divergences. `main=` 86/92/92/97%, `mate=` 68% 163K/240K.
    Contract `.agent/decisions/m3u2b-contract.md` · detail `.agent/archive/m3-units.md#m32b`.
  - M3.3 DONE tier=kernel tags=oracle depends=M3.1 - est 4 -> 4 sessions. Request-free
    direct and source-backed submission over unchanged schema v2: `submit_proposal(...,
    *, candidate)` and `propose(...)`, both returning the proposal id, so arity makes both
    illegal states unrepresentable; `CandidateSourceError` normalization leaks nothing. Also
    deleted `System.__init__`'s `callable(getattr(source, "propose", None))` pre-flight, a ruled
    public behaviour change. Suite 635 -> 744; battery 73 tests / 52 obligations; 48 mutants /
    0 survivors. `main=` 84/100/96/86%, `mate=` 99% 239K/240K.
    Contract `.agent/decisions/m3u3-contract.md` · detail `.agent/archive/m3-units.md#m33`.
  - M3.4 DONE tier=kernel tags=oracle depends=M3.3 - est 4 -> 4 sessions. Froze the
    request-free proposal/read/review/report/event seams behind one internal binding adapter at
    schema v2: fork 1 = COMPOSE (`_proposal_bindings` issues the complete statement per
    selection), fork 2 = R2+ four fields with `status` newly `accepted`/`corrected`/`rejected`.
    Owns exactly EIGHT `requests` sites in `system.py`. Suite 744 -> 811; battery 55 tests / 40
    obligations; 44 mutants / 4 NAMED ruled survivors; differential 42 probes / 2 rulings.
    `main=` 84/98/76/90%, `mate=` 100% 240K/240K.
    Contract `.agent/decisions/m3u4-contract.md` · chronology
    `.agent/archive/m3u4-chronology.md` · detail `.agent/archive/m3-units.md#m34`.
  - M3.5a DONE tier=kernel tags=- depends=M3.2b,M3.4 - est 4 -> 4 sessions. Added the
    `resolve` root leaf and `proposal submit` with exact exit and payload contracts: fork 1 =
    ENVELOPE CORE with `@PATH` cut and the cap DERIVED, fork 2 = one fixed seven-key payload
    across all three resolve states with three-valued `matched`. Exported
    `PROVENANCE_MAX_BYTES`. Suite 811 -> 901; battery 30 tests / 30 obligations, 30/30 red at
    `c8b82cd` and green at HEAD; 128 mutants / 1 NAMED ruled survivor (M41); 23 amendments over
    18 amended obligations. `main=` 85/79/95/100%, `mate=` 97% 232K/240K.
    Contract `.agent/decisions/m3u5a-contract.md` · detail `.agent/archive/m3-units.md#m35a`.
  - M3.5b DONE tier=kernel tags=- depends=M3.5a - est 3 -> 3 sessions. Removed the
    `handle`/`request`/source CLI grammar, imports, fixtures, help and CLI-route operator prose
    through `m3u5b-burden.py`'s 7 occurrence-asserted EDITS (`cli.py` -44/+1); library-API prose
    naming `System.handle` was deliberately DEFERRED to M3.6a. Census 28 leaves / 35 nodes,
    `parser_shape` 151 `ebd2ac811bd9776d`. Suite 901 -> 949; battery 48 clauses / 28
    obligations; sweep 48 killed / 0 misdirected / 0 survivors; gate 5 `m3u5b-doc-parse.py` new.
    `main=` 80/96/86%, `mate=` 100% 240K/240K.
    Contract `.agent/decisions/m3u5b-contract.md` · detail `.agent/archive/m3-units.md#m35b`.
  - M3.6a SPLIT INTO M3.6a1 + M3.6a2 + M3.6a3 at its own pre-open measurement. `main=` 88%
    212K/240K; no teammate dispatched. Unsplit it measured 3.2x M3.5b's frame count plus a
    7-site demo rewrite, a transcript regeneration and a five-document prose pass. Split axis =
    CONSUMER-MIGRATION-BEFORE-DELETION, available because both APIs shipped simultaneously.
    Detail `.agent/archive/m3-units.md#m36a`.
  - M3.6a1 DONE tier=kernel tags=- depends=M3.5b - est 3 -> 8 sessions (2.67, the project's
    largest overrun; driver measured four sessions running = ENTRY COST, not the work).
    Migrated every consumer off `handle`/`request_status` while both still shipped, through one
    idempotent count-asserted `m3u6a1-surgery.py`: 23 RETAIN definitions over 45 sites, the four
    `handle`-driven fixture helpers plus `_promoted_example_ledger` re-based onto
    `propose`/`get_proposal`/`review`, four MISS-GUARDED sites moved onto `resolve`, the demo's
    seven sites rewritten with the set checkpoint moved after each artifact promotion, and the
    README transcript regenerated. Suite 949 -> 979; 30 obligations / 19 corrections; battery 30
    tests, 23 red / 6 green at `6fb4d92`; 92 mutants / 92 killed / 0 survivors over 29 clauses;
    36 attack rows disposed. `main=` 82-98%, `mate=` 86% 206K/240K.
    Contract `.agent/decisions/m3u6a1-contract.md` · detail `.agent/archive/m3-units.md#m36a1`
    · tips `archive/m3u6a1-{test,rev,gate}`, `archive/m3u6a2-scout`.
  - M3.6a2 OPEN tier=kernel tags=- depends=M3.6a1 - est 9 -> ? sessions (1.00, repeat of M3.6a1's
    cadence). Delete `handle`, `request_status`, `_outcome`, `_fail_generation` and
    `_request_revision_is_current`; delete the `generation_lease_seconds` constructor knob,
    `self._lease_us` and the clock bound named after it; delete request cancellation on operation
    revision together with the `operation.revised` payload's `invalidated_generators` key. Two
    event kinds vanish, `request.resolved_by_artifact` and `request.fallback_failed`. Rewrite the
    library-API prose M3.5b D22 deferred, all four normative documents.
    S1 DONE - measurement + rulings, MAIN-retained, no teammate. No shipped code touched, so the
    gate stands unrerun at its `1146421`-era 979 tests. Instruments + data committed at `cb66217`
    (`m3u6a2-tripwires.py`, `m3u6a2-tripwires.json`, `m3u6a2-stages.json`). `main=` 85% 232K/273K
    at a compaction cut, closing the record post-compaction.
    GOVERNING BURDEN = 48 NORMALISED FRAMES. `m3u6a-burden.py` over throwaway worktrees at
    `da70a56`, this unit's three stages, broken/ran/raw (normalised): 1 methods 50/979/48 (47),
    2 lease 50/979/48 (48), 3 revise 50/979/48 (48). Stages 4-5 are M3.6a3's and were NOT
    measured. Stage 1's 47 reproduces `archive/m3u6a2-scout` independently, so M3.6a1 did not
    reduce this unit's burden: concentration collapsed (breaks fell ~6x once four fixture-helper
    cascades went - `_confirm_scope` 189, `_confirm` 23, `_promoted_conflict_fixture` 11,
    `_promoted_example_ledger` 2) while the work list did not (46 -> 47 frames).
    STAGE 3'S FAILURE SET IS BYTE-IDENTICAL TO STAGE 2'S: deleting request cancellation on
    operation revision plus the `invalidated_generators` key breaks nothing the methods deletion
    had not already broken. `invalidated_generators` has ZERO pins repo-wide - only `system.py:812`
    and `:832`, both inside the SURVIVING `revise_operation` (762..836) - so its deletion is
    unobservable to the current gate and THIS UNIT'S BATTERY MUST SUPPLY THE PIN.
    STAGES 1 AND 2 BOTH READ broken=50 AND THE EQUALITY IS A +1/-1 COINCIDENCE. Raw frames move
    +3/-3: `test_authority_removal.py:118 test_system_constructor_shape` is genuinely NEW once the
    lease kwarg leaves the constructor; `test_system.py test_expired_generation_poll_is_retryable_
    and_handle_reclaims` moves `:702` -> `:686`, one frame under the RAW key and none under the
    normalised one; and `test_system.py:732 test_public_scalar_validation_fails_with_domain_errors`
    replaces its own two `<lambda>` subtest rows at `:735` + `:736`, because it now fails before
    the subtest loop. Net breaks -2+1+1 = 0. Normalised 47 -> 48, since the two lambdas collapsed
    to one frame at stage 1 and there are none at stage 2. Compare the SET, size on normalised
    frames. Union over the three stages = 51 raw frames.
    Every `self._lease_us` read (1099, 1110, 1235) sits inside `handle` (1059..1329, 271 lines),
    so stage 2 leaves no dangling reference; the surviving clock bound is `_now` (704..712).
    TRIPWIRE + PROSE CENSUS by `m3u6a2-tripwires.py` at `da70a56` (`--self-test` PASS, 6/6 controls
    firing): PINS 15 (13 not GIT-RANGE-scoped) · FREEZES 4 · PROSE-HIT-LINES 48, of which 47 sit in
    the four OWNED documents (README 25, `docs/architecture.md` 13, `docs/adapter-protocol.md` 7,
    `docs/threat-model.md` 2) and the 48th is the hospital example README's, ruled M3.6a1's. These
    counts travel with the emitted vocabulary and are deliberately wider than M3.5b's D22 deferral
    table (18/7/8/4) - the two are incomparable and neither corrects the other.
    THE TWO INSTRUMENTS MEASURE DISJOINT SURFACES, which is why both exist and how each is read.
    The burden stages measure the CODE DELETION and already contain D15a plus all four P06 span
    freezes; NOT ONE of the census's 15 prose pins appears in any stage's frame set, because no
    burden stage rewrites a document. Burden = what the deletion breaks; census = what the prose
    rewrite breaks. Full pin inventory with scopes lives in `m3u6a2-contract.md` section 5.
    D15a IS THE SHARPEST TRIPWIRE (def `tests/test_cli_removal_battery.py:1131`, assertion `:1158`,
    scope MIXED, red in all three stages): it compares the WORKING TREE against `36f7890` for six
    runtime modules including `system.py`, so it inverts the instant this unit edits one. M3.6a1
    re-scoped siblings D15b (`:1160`) and D22b (`:2766`) to the closed range `36f7890..1146421`
    and never reached D15a; the repair is exact and precedented in the same file.
    FOUR P06 BYTE-SPAN FREEZES on `System.handle`, one more than the plan named, each RAISING once
    the method is gone and each already inside the burden: `tests/test_submission.py:670`
    (assertion `:692`), `tests/test_submission_battery.py:289` (`:307`) and `:329` (`:337`),
    `tests/test_migration_battery.py:1322` (`:1338`, M3.6a1's D25).
    THAT SET IS DISJOINT FROM THE CENSUS'S `FREEZES 4`, WHICH SHARES ONLY THE COUNT: the census
    freezes are D15a, D15b, D22b and D22c, all in `test_cli_removal_battery.py`. The census cannot
    see the P06 family at all - `_freezes()` requires the literal `cement_runtime/system.py` or
    `System.handle` AND one of `read_bytes()`/`getsource`/`_git_bytes(`, while the four P06 frames
    reach the same source through `cement_runtime.system.__file__`, `inspect.getsourcefile(System)`
    and a `_source(ROOT, path)` helper, and the 6/6 self-test covers none of that negative space.
    The measured burden is what makes them visible. S2 either widens the detector behind a control
    that fires on a P06 frame, or records the exclusion with grounds.
    M3.5b's D01 (def `:607`, assertion `:617`) asserts `System.handle` and `System.request_status`
    still ship as library methods. B02 is NOT a tripwire: its frozen tuple is
    `_command_supervisor.py` and `example_adapter.py` alone, `system.py` never a member.
    ALL FOUR NORMATIVE DOCUMENTS ARE THIS UNIT'S, `docs/adapter-protocol.md` INCLUDED: M3.7
    relocates it under BYTE EQUALITY and never rewrites a claim, so leaving false `handle` prose
    there would RELOCATE the defect rather than defer it.
    NO PRE-OPEN SPLIT, BUDGET 9 (owner ruling). S1 measurement, S2 contract, S3 implementation,
    S4 prose rewrite + pin repair, S5 graders, S6 dispatch + harvest + battery ruling, S7 attack
    ruling, S8 gate catalogue, S9 sweep + closure. Every candidate seam was measured and rejected:
    a deletion-layer split is the 46:10 imbalance M3.6a already rejected; consumer-migration relief
    is measured ABSENT (46 -> 47); the only clean seam (prose) ships a DONE state whose README
    documents a deleted method; two kernel units duplicate the ~6 machinery sessions that dominate
    the cost (2x6+3 = 15 > 9). Record the overrun against 9.
    S2 OPENS ON RULINGS, NOT MEASUREMENT: write `.agent/decisions/m3u6a2-contract.md` from the
    burden, tripwire and ownership rulings above.
    THE BURDEN HARNESS WAS DEFECTIVE AND IS REPAIRED AT `c3f6d83`, which M3.6a3's rerun inherits.
    `m3u6a-burden.py` sized each stage by grepping `Ran N` and `FAIL:`/`ERROR:` headers out of
    text, but D28, D15 and D16 replay whole suite runs as subprocess output, so nested summaries
    impersonated outer failures. Repair = structural collection through `traceback.extract_tb`,
    never string parsing, plus two hard aborts (`broken <= ran`; no duplicate test ids).
  - M3.6a3 tier=kernel tags=- depends=M3.6a2 - delete `Resolved`, `InProgress`, `FallbackFailed`,
    `Rejected`, `ReconciliationRequired`, the `Outcome` alias and every import and `__all__` entry naming
    them; delete `CandidateRequest.request_id`, minting the private request-row id inside
    `_persist_proposal` so the id survives as plumbing and leaves the public protocol. `ReviewRequired`
    loses its last producer when M3.6a2 deletes `handle`, so its retention is this unit's first ruling
    rather than the plan draft's assumption. Measured burden: 10 frames, `test_source.py` `request` (9
    breaks) the only shared one.
    THAT 10-FRAME FIGURE PREDATES M3.6a1 AND MUST BE RE-MEASURED BEFORE THIS UNIT OPENS, and it is
    NOT comparable to the burden harness's stage-5 numbers, whose stages are CUMULATIVE and carry
    stages 1-4's deletions inside them. What the post-migration re-measurement does establish is
    OWNERSHIP: the 34-break concentration surviving M3.6a1 - `PlanAdapterTests.request`
    (`tests/test_hospital_ocr_example.py:357`) and `CommandCandidateSourceTests.request`
    (`tests/test_source.py:17`) - is `CandidateRequest.request_id` burden and lands HERE, not in
    M3.6a2. Re-run `m3u6a-burden.py` scoped to this unit's own deletion set, state the convention
    beside the count, and size from that.
  - M3.6b tier=kernel tags=prod depends=M3.6a - the sole schema cut v2->v3: direct proposal columns,
    adapter swap, `requests` plus index deletion, refusal fixtures, package 0.2.0.
  - M3.7 tier=kernel tags=prod depends=M3.3,M3.5b,M3.6a3 - relocate the command runtime to an optional example
    surface with byte equality, archive membership and blocked reverse imports. Owns its destination paths
    explicitly (implementation, sibling supervisor, stub, README), rules whether the source-only example
    may depend on private JSON helpers, states that `py.typed` covers core only, and mocks the
    direct-process-only platform branch, which ships untested today. `uv build` measured: the wheel
    carries zero `examples/` and zero `tests/` members, so no `pyproject.toml` change is required. Runs
    alongside M3.6.
  - M3.8 tier=data tags=prod depends=M3.6b - regenerate the hospital demo and its pinned transcript
    through an idempotent updater. May run alongside M3.7.
  - M3.9a tier=docs tags=- depends=M3.6b,M3.7,M3.8 - rewrite the 145-row claim ledger, every core,
    example and optional-runner doc, plus the release and recovery record.
  - M3.9b tier=docs tags=- depends=M3.9a - independent final claim, command, help, archive, link and
    register replay; a code defect reopens the owning kernel unit.

  Acceptance is per-unit and quantified in `.agent/decisions/m3-plan-review.md` L5; a green suite plus a
  prose assertion is NEVER closure for a removal, because deleting a behavior together with its pin keeps
  the gate green. Every unit's battery must fail when one obligation remains undone or one preserved
  invariant disappears, and must rerun from that unit's committed checkpoint.

  SIZING LAW, measured across M3.1-M3.6a1 and binding on every remaining unit. The caveat this replaces
  said M3 opened with no validated estimator; eight closed units now supply one.
  - Multiply the bottom-up session count by the ratio measured on the nearest analog OF THE SAME SHAPE,
    never a milestone average: 1.00 for a repeat shape, up to 2.67 for an unprecedented one. Every 1.00
    is a unit sized against its own shape and all three overruns are the FIRST unit of theirs. Record
    `est <raw> -> <cal>` and split at a named seam rather than re-estimating the parts.
  - FOUR sessions for any unit that OPENS a spike wave, regardless of tag - the cost sits in dispatching,
    harvesting, re-deriving grades and arbitrating forks, not in the `oracle` tag. A unit with no fork to
    rule skips the wave-1 and fork-ruling sessions.
  - ENTRY COST IS THE TERM TO CUT BEFORE ADDING SESSIONS, priced by four consecutive M3.6a1 sessions and
    then by component: attached state measured 356 KB (~119K tokens) at M3.6a1 close, of which the
    roadmap was 163 KB and 88% of THAT was closed-unit detail. Unit detail now moves to
    `.agent/archive/m3-units.md` at unit close rather than at milestone close, which cut the roadmap to
    22 KB; MILESTONE-REVIEW dispatches from each unit's committed contract, so nothing it reads moved.
    Re-measure the attached set whenever a unit closes and archive on the same rule.
  - A pre-open size trigger must be a STATIC source-span budget or a MEASURED burden; a trigger needing
    the completed diff (byte equality, post-factoring line counts) is unmeasurable before the unit opens.
  - Size a removal by NORMALISED FRAME COUNT from a staged burden run, never by break count: a
    subtest-bearing test contributes a variable number of breaks, so the count is not even monotone
    under cumulative deletion. Compare the failure SET between stages, never the count. EVERY FRAME
    COUNT TRAVELS WITH ITS CONVENTION - RAW keys are `file:line in name`, NORMALISED keys are
    `file in name`, the two differ by roughly 5-10%, and comparing across them manufactures a defect
    out of nothing.

  Evidence, all tracked and re-runnable: `.agent/decisions/m3-map-a-llm-runtime.md` (229 anchors),
  `m3-map-b-authority.md` (212), `m3-map-c-lifecycle.md` (299), `m3-research.md` (Q1-Q4, executed probes),
  `m3-plan-draft.md`, `m3-plan-review.md` (54 findings, 8 lenses). Structural validator =
  `uv run python .agent/decisions/m3-report-validate.py <report.md>`; all six pass.

- M4 - Projection inside the boundary - UNPLANNED. Brings the step that actually produces coverage of many
  situations under supervision and verification: a projection artifact kind mapping raw input to canonical
  key, replayed against every confirmed raw input plus boundary probes, with counterexample gates and
  fail-closed behavior on unrecognized input. Open design question for planning: how a projection is
  verified without a domain oracle. Deferred entries `Typed schemas + verifier plugin ABI` and
  `Broader finite decision tables / constrained expression IR` seed this milestone. Output interpretation
  (`apply_plan`-class execution) inside the boundary is a separate later decision.

## Core (completed)

- Supervised fallback, evidence ledger, compiler recurrence/stability gates, verification/promotion,
  runtime safeguards, and CLI/API/docs/tests/package verification.

## Deferred - contract/deployment expansion

Scope expansion, i.e. future-milestone material that planning promotes into units. Off-spine defects and
deferred perfection on shipped surfaces live in `.agent/polish.md` instead.

- Typed schemas + verifier plugin ABI (M4 seed).
- Broader finite decision tables / constrained expression IR (M4 seed).
- Authenticated reviewer identities, encryption, retention, remote registry/signatures.
- Shadow sampling + production drift telemetry.
- TypedDict projections + dynamic inspection records.
- Owner-selected license + absolute repository/documentation URLs before public publication.
