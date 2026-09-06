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
    NO PRE-OPEN SPLIT, BUDGET 9 (owner ruling). S1 measurement, S2 contract, S3 wave-2 dispatch +
    phase-1 ruling, S4 red-suite harvest + implementation, S5 prose rewrite + pin repairs, S6
    battery verdicts + closure gate, S7 attack ruling, S8 mutation catalogue, S9 sweep + closure.
    Every candidate seam was measured and rejected:
    a deletion-layer split is the 46:10 imbalance M3.6a already rejected; consumer-migration relief
    is measured ABSENT (46 -> 47); the only clean seam (prose) ships a DONE state whose README
    documents a deleted method; two kernel units duplicate the ~6 machinery sessions that dominate
    the cost (2x6+3 = 15 > 9). Record the overrun against 9.
    S2 DONE - `.agent/decisions/m3u6a2-contract.md` at `ee731aa`, 26 KB, base `da70a56`, 29
    obligations `L01..L29` (a letter no other contract uses; `d`/`b`/`x`/`v`/`p` are all live in
    `tests/`) over 8 numbered gates. Deleted spans total 444 lines; three methods are EDITED, not
    deleted (`__init__` 680..702, `_now` 704..712, `revise_operation` 762..836). CLOSURE IS
    PROVABLE BY COUNTING - the five deleted methods form a closed call-graph component entered only
    through the two public methods being deleted, so `_lease_us`, `_outcome`, `_fail_generation` and
    `_request_revision_is_current` all reach zero occurrences with no dangling reference. The
    `requests` table has 20 lines over 7 methods; this unit removes 13 and leaves seven in M3.4's
    private plumbing. ONE RULED BEHAVIOUR CHANGE: dropping the lease term from `_now`'s bound widens
    the accepted clock range, so L06 probes both sides of the new boundary. TWO OBLIGATIONS EXIST
    BECAUSE THE GATE IS BLIND THERE: L08 pins the `operation.revised` payload's exact three-key set,
    L11 the exact thirteen surviving event kinds. SEVEN MODELS SURVIVE UNPRODUCED (L12) and belong
    to M3.6a3. Corrected in-session by C01: the first session table put implementation before the
    battery, which cannot be authored diff-blind once the diff exists.
    GATE 2 AND ITS SEED SHIPPED IN THE SAME SESSION, before dispatch, because the seed is the whole
    variable: `m3u6a2-seed-battery.py` derives `tests/test_lifecycle_removal_battery.py` from the
    contract's obligation list (30 stubs, names + docstrings DERIVED so a renamed obligation renames
    its stub, rerun prints NO-OP, and it REFUSES to overwrite authored tests), and
    `m3u6a2-battery-validate.py` grades it on five independent checks. Graded BOTH WAYS at seed:
    all-stub exits 1 on `STUB: 30`, filled exits 0; `--self-test` 5/5 firing. Gate 1 GREEN at 1009
    tests, 30 skipped, 343 s.
    A THIRD TRIPWIRE CLASS EXISTS AND NEITHER INSTRUMENT COULD SEE IT: what breaks when this unit
    ADDS a file. Committing the seed tripped M3.6a1's D16, which read `6fb4d92..HEAD` over `tests`
    and `examples` and so asserted that M3.6a1's surgery script reproduces every LATER unit's edits
    too - impossible for a script pinned to an earlier baseline, and it inverts on ANY added file,
    which makes it stricter than D15a. L30 closes both of its halves to `6fb4d92..dc4ab5e`
    (M3.6a1's baseline and DONE tip); its per-path half compared against the WORKING TREE and now
    compares against the tip's blobs. The seed's stub body SKIPS rather than fails, because M3.6a1's
    D28 asserts gate 1 green at EVERY commit in its range and history keeps a red revision after the
    unit that made it green closes. Contract corrections C01-C03 carry all three rulings.
    S3 - THE CONTRACT'S OWN NUMBERS WERE VERIFIED BEFORE DISPATCH AND THREE WERE WRONG, all three
    reachable only by running the count, and all three would have gone into a diff-blind battery as
    red-against-correct-code. Corrections C04-C06 carry the rulings.
    L13 read `exactly eleven` surviving `requests` sites while section 1 of the same contract
    inventoried SEVEN and named all seven lines. Measured: 20 lines total, 13 deleted, 7 surviving -
    and the three owners are module-level FUNCTIONS, so a class-body scan misattributes six of them.
    L11 READ THIRTEEN SURVIVING EVENT KINDS AND THE MEASURED ANSWER IS SIXTEEN, wrong three ways
    from ONE unrecorded fact: `artifact.ambiguity_quarantined` is emitted at `handle:1143` and
    nowhere else, so deleting `handle` DELETES AMBIGUITY QUARANTINE. L11 kept that kind, and missed
    four others because `kind=` has three spellings and a first-branch scan reads one -
    `artifact.challenged` + `artifact.verification_failed` hide in `IfExp` second branches,
    `proposal.accepted` + `proposal.corrected` hide in `kind=f"proposal.{proposal_status}"` whose
    interpolation is annotated `Literal["accepted", "corrected"]`. Section 2's deletion set now says
    THREE kinds lose their only producer, not two, and L11 states the derivation so the next reader
    does not re-derive it under whichever spelling it knows.
    GATE 3 WAS ALREADY RED AT HEAD AND NO S2 CLAIM SAW IT. `--check` reported DRIFT on `pins` and
    `freezes` from the S2 commits themselves: the battery seed quotes the contract's obligation text
    in its docstrings, so this unit's own battery entered its own census (PINS 15 -> 18, FREEZES
    4 -> 5), and L30's repair moved the D23 pin `:1269` -> `:1282` without the table absorbing it.
    Repair = exclude `tests/test_lifecycle_removal_battery.py` from both scanners, with a
    SELF-REFERENCE check + control so a future re-entry fails loudly. Census also gains `ambigu`,
    which is what reaches `README.md:49` and `docs/threat-model.md:61` - two lines promising the
    quarantine this unit removes, invisible to every other token in the convention. `idempot` was
    measured as a candidate and EXCLUDED with grounds: 9 of its 11 lines correctly describe the
    SURVIVING proposal API, and a token whose hits cannot reach zero makes L24 unsatisfiable.
    Post-repair census: PINS 16, PINS-WORKING-TREE 14, FREEZES 4, PROSE-HIT-LINES 50, self-test 7/7.
    NO GATE WAS ADDED - gate 3's instrument was repaired and its expectation re-emitted.
    WAVE 2 DISPATCHED with both graded artifacts committed BEFORE dispatch, since the seed is the
    whole variable: `m3u6a2-wave2-validate.py` (self-test 8/8 firing, stubs FAIL at 150 and 72
    unknown cells, MAIN-owned columns exempt and PRINTED) grades `m3u6a2-verdicts.json` (30 seeded
    loci over L01-L29) and `m3u6a2-attack.json` (24 seeded lenses over obligations, gates and
    sections). Row SUBJECTS are seeded, not just row ids - that is the difference measured at 0/96
    against 96/96 - and `X`/`Y` extension ids are declared a floor rather than a cap.
    S3 DONE - HARVEST 96 ROWS, EXTENSIONS OUTNUMBERING SEEDS 42:54 AND CARRYING THE SHARPEST
    FINDINGS, which is the seeded-floor rule paying out again. `m3u6a2-verdicts.json` 66 rows
    (30 seeded + 36 `X`) / 43 DIVERGENT; `m3u6a2-attack.json` 30 rows (24 seeded + 6 `Y`) /
    11 blocking + 15 material + 4 cleared, validator PASS. Tips `archive/m3u6a2-{test,attack}`,
    tables sha256-proven byte-identical to their worktree blobs before the branches went.
    THE ATTACK BROKE C05, THE CORRECTION MAIN HAD LANDED THAT SAME SESSION: Y01 measures 19 static
    `_event` calls where C05's text says 20. The event-kind SET is unaffected - it was derived per
    call site, not from the total - but a structural count inside a correction written to fix
    structural counts is exactly the shape that keeps closing units on MAIN's own claim defects.
    Other blocking rows to rule at S4: A13 (L15's `lineno..end_lineno` slice excludes decorators, so
    a decorator added to a frozen span is invisible), A15 (L18 is self-contradictory - surviving
    `revise_operation` calls `_now` and MUST change under L07), A17 + A18 (L23 is satisfiable by
    weakening the pins, L24 is unsatisfiable under its literal census reading), A22 + Y05 + Y06
    (gate 3 has no independent post-state oracle, never validates `totals`, never authenticates
    provenance - `--emit` blesses whatever the tree says), Y02 + Y03 (gate 2 detects only the
    literal `SEED STUB`, so `pass` bodies or a non-TestCase function grade clean), A06 (L08 pins the
    key set alone, so every value may be wrong), A23 (G8 names no fixed subproperty catalogue).
    A24 IS THE GOVERNANCE ROW AND MAIN RULES IT FIRST: did C06 change gate 3's ACCEPTANCE PREDICATE
    after S2 was DONE, which section 6 forbids, or repair its instrument, which it permits.
    S3 DID NOT BUY THE BATCH RULING the corrected session table assigned it. The window went to the
    pre-dispatch verification - which is what found C04-C06 and a red gate 3 no S2 claim had seen -
    plus the wave itself. `main=` 79% 215K/273K, `mate=` 78% 213K/273K (`test`, stopped saturated at
    66 rows after one bounding directive it did not take; `attack` finished clean at 71% 193K).
    S4 DONE - THE 96-ROW RULING, THE PHASE-2 WAVE AND THE WHOLE CODE IMPLEMENTATION, because a
    compaction handed the session a second full window and the work was already staged for it.
    `m3u6a2-rule-attack.py` rules BOTH tables (gate 6 names one command): attack 30 rows = 22
    accept / 4 accept-in-part / 4 cleared; verdicts 66 = 35 accept / 8 accept-amend / 23
    ratified-nondivergent. Idempotent - applied, `no-op`, `--check` in-sync. The 23 non-divergent
    rows are ruled as a CLASS with their ids in a frozenset, so a row changing class fails loudly;
    V04/V19/X07 were spot-checked first rather than asserting the class blind.
    A24 RULED FIRST AND THE ANSWER IS NO, WITH THE SUBSTANCE KEPT (C07). C06 added no numbered
    entry, so section 6's pins stand - and nothing could have been unbuilt anyway, since S2 claimed
    gate 1 alone while gate 3 was red. But a gate's identity is (COMMAND, ACCEPTED LANGUAGE), so an
    INSTRUMENT change is now a numbered correction voiding that gate's prior runs and forcing a
    full-list rerun at the next closure claim.
    FOUR MORE OF THE CONTRACT'S OWN NUMBERS WERE WRONG, each reachable only by running the count
    (C08-C11). C05's `20` `_event` calls is 19 static (16 Constant / 2 IfExp / 1 JoinedStr), 14
    post-state - the textual count matches the DEFINITION line; the 16-kind SET is unaffected,
    having been derived per call site. L09's `zero occurrences` for `request_status` is
    FALSE-BY-CONSTRUCTION against L15: 8 identifiers at base, SEVEN survive as proposal plumbing and
    one sits inside byte-frozen `get_proposal`. C04's own repair called all three surviving
    `requests` owners module-level FUNCTIONS - `_persist_proposal` is a `System` METHOD, so a
    class-body scan sees ONE site. Section 1's `seven exported models` is SIX: `Outcome` was never
    in `__all__`, and M3.6a3 inherits 7 definitions / 6 exports / 0 `system.py` imports.
    L24 WAS UNSATISFIABLE AND MAIN REPRODUCED WHY: M3.5b's D25 needs >=2 shipped paragraphs saying
    `request row stays internal`, measurement finds exactly 2 (README + architecture), and the
    census `\brequests?\b` matches both - a green D25 and a zero `requests` count cannot hold
    together. L24 now binds a NAMED token subset plus grounds per surviving generic hit, and that
    prose is also gate 3's independent oracle (A22), which `--emit` cannot rewrite. L18 was
    self-contradictory (`revise_operation` is both a surviving `_now` caller and an L07 edit target)
    and is replaced by the exact 12-method call-site set. NEW OBLIGATION L31: ambiguity quarantine
    is a removed BEHAVIOUR with its own pin, not merely a vocabulary spelling. L19-L22 split
    MECHANICAL / SEMANTIC (C12) because the committed vocabulary scores `vocab-hit False` on
    `Never call propose or review; use the legacy lifecycle dispatcher`. Section 7 gains gate 8's
    FIXED exclusion catalogue; D22c is MIXED and keeps live rows.
    THREE INSTRUMENTS WERE DEFECTIVE AND NONE OF THEM HAD BEEN RUN. The verdicts table had never
    passed its own validator: `CONCRETE` required a TWO-digit number, so 14 rows whose observable is
    a single-digit count, a boolean, `[]` or an exception class graded FAIL, and S3's `validator
    PASS` covered the attack table alone (C13; widened, re-graded both ways, 66/66 concrete PASS and
    a seeded vague row still rc 1). Gate 3's command named `--check`, which the instrument rejects -
    the bare invocation IS check mode, so the gate as written could never have run (C14). Gate 2's
    CORRECTION-BIND check had no form for a correction repairing an instrument OUTSIDE the numbered
    list, so C13 itself graded UNBOUND; the fourth accepted form requires the explicit none AND the
    repaired file's name, so the escape carries its own evidence (C15, self-test 6/6).
    THE ADDITION-TRIPWIRE CLASS FIRED A THIRD TIME, from the contract's own wording: L23 said
    section 8 `authorizes` a delta, the seed quotes obligation text into docstrings, and M3.1's
    residue classifier scans `tests/` for `authoriz*` - gate 1 red on
    `test_every_surviving_authorization_mention_is_classified`. Reworded to `permits`, which weakens
    no predicate, rather than editing a standing gate. Gate 1 then GREEN twice: 1010 tests, 31
    skipped, 498 s and 516 s.
    PHASE 2 DISPATCHED, HARVESTED AND CREDENTIALED IN THE SAME SESSION. `test-m3u6a2-2` ran from a
    worktree based at MAIN's own HEAD, not at `archive/m3u6a2-test`: the tag's base renders main's
    later commits as DELETIONS, and basing at HEAD leaks nothing because no implementation existed
    yet while `src/` was still byte-identical to `da70a56`. It delivered 59 tests over 31
    obligations in 11 batches, gate 2 PASS (STUB 31 -> 0), zero `self.fail()` and zero `skipTest()`.
    Harvest by file checkout, sha256-proven, tagged `archive/m3u6a2-test-2` before the branch went.
    MAIN's own credentials, both runs its own: 48 red methods at HEAD (55 failure records, rc 1,
    reproducing the author's figure exactly) and 50 red at `da70a56` in a detached worktree with the
    import path proven - four of those ERROR on a missing `m3u6a2-tripwires.py`, because the pinned
    baseline predates this unit's own instruments.
    THE AUTHOR GRADED FOUR OBLIGATIONS `contract-defect` AND THREE ARE REAL (C16-C18). Section 7's
    baseline-green list is per OBLIGATION where three members are MIXED, so a literal reading makes
    post-state predicates green at baseline - the classification is now SUBPROPERTY-level. L23's
    anti-weakening clause froze 14 pin bodies with section 8 enumerating NO permitted delta, which
    made L23 and L19-L22 jointly unsatisfiable; three inversions are measured and permitted (B27,
    D23's positive control re-based not deleted, D34), D22a stays unmeasured and unpermitted. L24's
    grounds catalogue omitted NEGATIVE request-identity claims, so satisfying the census would have
    deleted `four fields and no request identity` out from under a standing pin. L30's
    `green-at-baseline` is not a defect: it is red at `da70a56` and green at HEAD because `7cfc748`
    performed the repair inside this unit.
    THE CODE HALF IS IMPLEMENTED AND GREEN, staged exactly as `m3u6a-burden.py` measured it: five
    methods deleted (`handle` 271 lines, `_outcome` 116, `_fail_generation` 32, `request_status` 14,
    `_request_revision_is_current` 12) with the routing section header, 67 methods -> 62; `__init__`
    loses the lease parameter and `_lease_us`; `_now`'s bound becomes bare `_MAX_SQLITE_INTEGER`
    with the `lease-safe` wording gone; `revise_operation` loses the `UPDATE requests` write and the
    `invalidated_generators` key; the `.models` import goes 35 -> 28 names, each proven to hold
    exactly ONE NAME token first. Battery 48 red methods -> 19, every one of L01-L18 and L31's
    `src/` half GREEN.
    IT LIVES ON `impl/m3u6a2`, NOT ON MAIN, BECAUSE D28 REPLAYS GATE 1 AT EVERY REVISION TOUCHING
    `tests/` OR `examples/`. A red battery committed to main fails forever after this unit closes,
    so the branch carries the red-to-green work and squashes into main as ONE green commit at
    closure. `main` keeps the seed battery and stays green throughout.
    `main=` 83% 226K/273K to the compaction hook + 75% 205K/273K after it; `mate=` 89% 243K/273K
    (`test-m3u6a2-2`, which shipped its report under a flush directive at 236K and finished clean).
    S5 OPENS ON THE PROSE REWRITE against the 19 surviving red methods: L19-L22 over the four owned
    documents, L23's three permitted inversions plus any the rewrite measures, L24's grounded
    census, then the tripwire repairs L25-L29 and L31's test inversion. Work on `impl/m3u6a2`,
    rerun the battery to zero red, then the full numbered gate list, then squash to main.
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
