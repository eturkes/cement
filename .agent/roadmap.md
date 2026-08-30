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

  Units - 13, 5 DONE + 8 remaining, executing as 7 waves. `depends` shows the DAG; same-wave units name the same
  predecessor. Tier default `kernel`; `oracle` is kept only where an independent implementation can
  actually diverge, so deletion, forwarding and byte-preserving relocation carry none.

  - M3.1 DONE tier=kernel tags=- depends=none - deleted the `authority()` callback and its scaffolds.
    `main=` 92% 220K/240K, `mate=` 54% 129K/240K. Contract + attack record:
    `.agent/decisions/m3u1-contract.md`. Shipped: `AuthorityCheck`, the `System.__init__` `authority`
    keyword, `self._authority`, `_authorize` and all 11 call sites gone; both double-plan
    authorization-window scaffolds collapsed to ONE locked plan; the empty-union gate and every
    actor/reviewer capture, validation, persistence and event survive; `store.py` byte-identical to
    `3a53389` at `SCHEMA_VERSION` 2. Suite 548 -> 548 (11 authorization-only tests deleted, 21 rewritten,
    11 added as `tests/test_authority_removal.py`).

    CALIBRATION RESULT, binding on M3.2a..M3.9b. One single-author kernel unit consumed 92% of MAIN.
    Cost split, measured: ~25K wave-1 surface reading (the 61 KB track map alone), ~40K implementation,
    ~35K a single unplanned context dump, the rest coordination and closure. So a unit of this shape
    fits one window with NO margin, and M3.1 was the SMALLEST unit in the milestone. Every later unit
    must therefore either shrink below M3.1's static source span or split before it opens; M3.5b, M3.6a,
    M3.6b, M3.7 and M3.9a all exceed it as written and need a pre-open split. Two mechanics earned their
    cost and should repeat: scripted, count-asserted, idempotent test surgery instead of per-test hand
    edits, and a pre-implementation contract attack that ran concurrently with implementation.
    ORACLE SURCHARGE, SETTLED. M3.1 carried `tags=-`, so its 92% bought NO `orc`, NO `diff` and no
    divergence rulings, and the split list above ranks static source span alone -- which is why it flags
    five `-`/`prod` units and not one of the four `oracle` units (M3.2a, M3.2b, M3.3, M3.4), each of
    which pays a battery the calibration never measured. Pricing route 1 (measure against M2's oracle
    units) is UNAVAILABLE: project history holds ZERO `orc` and ZERO `diff` dispatches across 269
    `.scratch/agents/` artifacts, and M2's single oracle mention is a rejection
    (`.agent/archive/m2.md:454` - a forwarding leaf's reference implementation is the same forwarding
    code). Archaeology over non-oracle analogs would manufacture a forecast and carry it across a
    document boundary as a measurement, a defect this project has already paid for. RULING: M3.2a is the
    ORACLE-CALIBRATION unit, run under route 2's protective split - wave 1 plus acceptance contract
    first, MAIN gauge read at contract close, implementation opening only if projected cost fits the
    one-window aim, else the contract becomes the next session's entry state. Record M3.2a's
    `orc`/`diff` MAIN cost separately from its base at close; that measurement, never an estimate, sizes
    M3.2b, M3.3 and M3.4. Tags stay as reviewed - seven campaigns were already cut to three and
    justified per unit (`.agent/decisions/m3-plan-review.md` L86-88), so cost was the only open question.

    FIRST MEASUREMENT, from M3.2a's own wave 1. MAIN went 31% -> 75% (74K -> 179K, ~105K) to buy:
    validator authoring, a 3-teammate wave-1 dispatch, four rounds of steering, one spike-report
    harvest, MAIN's own reachability census, MAIN's rerun of the decisive harness stage, and the
    acceptance contract. Implementation had not started. So the priced answer is structural, not a
    percentage surcharge: AN ORACLE UNIT DOES NOT FIT ONE WINDOW, and the split belongs at the contract,
    which is exactly route 2. This wave-1 reading put the total at two sessions; the binding figure is
    M3.2b's measured FOUR below.
    Reliability datapoint, priced the hard way: 1 of 3 wave-1 teammates delivered. `spike-m3u2a-full`
    died twice and produced 0/32 probes; `map-m3u2a` climbed to 91% (218K) while its report never grew
    past its skeleton across four flush directives. MAIN absorbed both losses by deriving the census
    itself, which cost less than a successor would have.
  - M3.2a DONE tier=kernel tags=oracle depends=none - Store-owned enforced-read capability.
    `main=` 93% 223K/240K (session 3; sessions 1-2 closed at 75% and 80%),
    `mate=` 65% 155K/240K. Contract, MAIN-final verdict table, review dispositions and the differential:
    `.agent/decisions/m3u2a-contract.md`.
    Shipped in `store.py` behind an unchanged public seam: three mechanisms (Store-owned rolled-back
    transaction; deny-by-default authorizer allowlisting pragmas by NAME in a readable-bare set and an
    introspection set; percent-encoded existing-only `file:` URI `mode=ro`), and classification by
    `sqlite_errorcode` alone - `SQLITE_AUTH`/`SQLITE_READONLY` -> private `_ReadOnlyViolation` -> exit 2,
    `SQLITE_CANTOPEN` -> `IntegrityError("ledger file is missing or unreadable")` -> exit 5, every other
    failure keeping its baseline mapping with `write=True` unchanged. `PRAGMA query_only` and the
    `SQLITE_SAVEPOINT` grant are both REJECTED on the mutation criterion: no probe forces either, so
    neither could ship with a test able to detect its deletion. Both headline defects are closed against
    a real ledger - a `write=False` INSERT no longer commits (ledger sha `090d735f101f17f4` unchanged)
    and a read against a deleted ledger no longer creates a 0-byte file. Suite 551 -> 600.
    CLOSURE IS MECHANICAL, never a green suite. Battery = 49 diff-blind tests over 22 numbered
    obligations (`tests/test_read_capability_battery.py`, coverage graded by `m3u2a-battery-validate.py`)
    plus the census test; `m3u2a-mutants.py` runs 19 mutants over every enforcement predicate and reports
    19 killed / 0 survivors against a green control. Cost re-measured and the old discrepancy withdrawn:
    the enforced open costs no more than the plain open (four runs 0.961-0.980x, two probe harnesses
    0.995x/1.002x, `m3u2a-connect-benchmark.py`).
    Two defects in MAIN's landed code that the 32-probe corpus could not reach, both found in the battery
    wave: `_transaction_error` read `exc.sqlite_errorcode` unguarded, so a `DatabaseError` constructed in
    Python escaped as `AttributeError` instead of the contracted `IntegrityError` (the oracle's
    independent implementation had used `getattr` - the differential paying for itself); and no test
    forced the `SQLITE_READONLY` denial member, because the layered-guarantee probe asserts the RAW error
    inside the block and never the translation. Differential over the oracle's own 32-seam driver:
    1 behavioral divergence (W13 `VACUUM`, ruled MAIN's way on parity measurement - both capabilities
    raise the identical class and message, so the open transaction refuses it before the authorizer is
    consulted), 17 message-text differences, graded by `m3u2a-differential.py`.
    ORACLE CALIBRATION, this unit's measurement, SUPERSEDED by M3.2b's four-session correction below -
    read that one. Three MAIN sessions here: s1 = wave 1 + acceptance contract (31 -> 75%), s2 =
    implementation (0 -> 80%), s3 = battery (0 -> 93%). Three only because this unit's review landed
    inside s3. The base implementation was 46 production lines, so static span predicts none of it -
    the window goes to the BATTERY'S COORDINATION.
    RELIABILITY, third datapoint, now with a control. Skeleton-first is the whole variable. The `test`
    re-dispatch carried a stub-commit mandate - every intended test name committed first with a failing
    body, then one commit per filled test - and delivered 52 commits, 48 tests, 22/22 obligations, zero
    unfilled report cells, at 65% of its window. The mutation-campaign teammate got the same mandate in
    prose but no stub artifact to seed, produced nothing across three polls and one explicit flush
    directive, and was stopped; MAIN then ran the 19-mutant sweep itself for a fraction of the
    coordination cost.

  - M3.2b DONE tier=kernel tags=oracle depends=M3.2a - one-snapshot P1-P6 verification plus
    `evaluate` behind a pure `resolve`; failed verification, verified miss and verified hit stay
    distinct; durable 1/1,000/50,000 measurements published. Contract, MAIN-final verdict table,
    review dispositions, differential and the history correction: `.agent/decisions/m3u2b-contract.md`.
    Shipped at `b5916a9`: `System.resolve` + `FunctionResolution` + export, +56/-1 production lines
    across three files against the spike's +34/-1 estimate (delta = docstrings). Suite 600 -> 635.
    ORACLE CALIBRATION, CORRECTED AND BINDING ON M3.3 + M3.4. An oracle unit takes FOUR MAIN
    sessions, not M3.2a's measured three: s1 contract 30 -> 86%, s2 implementation 5 -> 92%,
    s3 battery + differential + review 38 -> 92%, s4 finding closure + verdict table 33 -> 97%.
    `mate=` 68% 163K/240K (`test-m3u2b-2`). The fourth session is not overrun - it is the
    REVIEW-CLOSURE session, and M3.2a never paid it because its review landed inside s3. Budget
    every remaining oracle unit at four and split at contract, implementation, battery, closure.
    FORK RULED on measurement: the plan draft's prescribed "factor `verify_function` onto a supplied
    connection" is SUPERSEDED and does not ship. M3.2a had already landed the enforced read inside
    `Store.transaction(write=False)`, leaving no nesting to fix; none of the six helpers between
    `system.py:2952` and `system.py:3363` opens a second transaction, and the spike measured the
    document evaluating identically inside and after the snapshot. 17/17 probes.
    INSTRUMENTS, four, three distributions. Battery = 35 diff-blind tests, one per obligation
    B01-B35, graded by `m3u2b-battery-validate.py` (`--emit-stub` = the seed's single source of
    truth); it returned 2 reds, both claim defects. Mutation sweep = `m3u2b-mutants.py`, 23 mutants
    over three files, 22 killed by the battery alone, `battery_gaps=0`, ONE SURVIVOR: deleting
    `not verification.passed or` passed all 633 tests, because `verify_function` binds both gate
    terms in every real output. Closed by B34, the mirror of B14's fabricated probe. Differential =
    26 probes, 0 behavioral divergences, 0 text differences, exit 0, credited by MAIN's
    re-derivation. Review = 12 findings, 4 cleared, 8 upheld, all disposed. ZERO code defects across
    every instrument; sixth consecutive unit whose findings are claim defects in MAIN's own text.
    CLOSURE IS MECHANICAL, never a green suite: the sweep plus the battery grader's UNFILLED 0.
    COST PUBLISHED, the unit's durable obligation, measured end to end through the shipped method
    and re-derivable from committed state (`m3u2b-resolve-benchmark.py` + `m3u2b-resolve-bench.json`, contract section 8). The harness now records PROVENANCE PER POINT
    and REFUSES to merge points measured under different provenance, so the scaling fit cannot be
    assembled from incomparable builds; `m3u2b-validate.py` grades that identity and prints the
    exponents, and it refuses a dirty-tree measurement outright.
    SEEDING, four datapoints and the variable now isolated. MAIN-committed validator + all-`unknown`
    skeleton gave 3/3 on wave 1 and 3/3 on the battery wave, against M3.2a's 1/3 under a prose
    mandate. It then gave 2/3: the teammate asked to ENUMERATE divergences filled 0 of 96 across
    three polls and 58% of its window, while its successor - identical validator, identical brief,
    plus a `section` anchor and an ungraded `locus` naming each row's SUBJECT - filled 16 of 16.
    Seeding the deliverable is necessary; seeding the row SUBJECTS is what makes a generative
    deliverable resumable. `prod-m3u2b-1` then filled 43 crosswalk rows at 33% of its window and
    self-reported its own boundary slip, which MAIN confirmed reversed before harvest.
  - M3.3 DONE tier=kernel tags=oracle depends=M3.1 - request-free direct and source-backed submission
    over unchanged schema v2. Also owns `src/cement_runtime/errors.py`: `CandidateSourceError` stays
    public, its supervised-fallback docstring is rewritten, and both it and an arbitrary `Exception`
    normalize to exact public text with no durable row or event, so a broken source leaks nothing.
    Budget FOUR MAIN sessions per the corrected oracle estimator: contract, implementation, battery,
    closure.
    S1 DONE, contract session, `main=` 84% 201K/240K against the estimator's 86%, `mate=` 68%
    164K/240K (`spike-m3u3-split`). Wave 1 = `map-m3u3` + two spikes, all three seeded by a
    MAIN-committed validator and all three delivering `UNKNOWN-CELLS: 0`: 35 map rows, 14 probes each.
    Acceptance contract `.agent/decisions/m3u3-contract.md`, 13 sections, 34 obligations, sections 12
    and 13 PENDING.
    FORK RULED, two methods: `submit_proposal(..., *, candidate) -> str` and `propose(...) -> str`,
    both returning the proposal ID. Arity makes both illegal states unrepresentable. BOTH spikes
    recommended it, including the one built to defend the XOR signature, so the council rule accepted
    it without a third spike - the first time an alternative's own advocate ruled against it.
    S2 DONE, implementation session, ran past one compaction boundary. `main=` 100% 239K/240K at the
    boundary, 65% 156K/240K in the post-compaction close window; `mate=` 78% 187K/240K
    (`orc-m3u3-1`). Shipped at `4b96e4d` + `719b48a` + `57a4571`. Suite 635 -> 668, gate green
    203.921 s.
    `wt/spike-m3u3-split` is RETIRED as a design input: it collapsed `handle` onto the shared seam,
    which P06 forbids, and its `operations()` reuse is rejected at D13. Both avoided.
    SHIPPED: `submit_proposal` + `propose` + `_persist_proposal` + `_submission_revision` +
    `_canonical_candidate` in `system.py`; `CandidateSourceError`'s docstring; census 17 -> 18 read
    sites, 16 write sites, each new site asserted BY METHOD NAME; `tests/test_submission.py` (33);
    `.agent/decisions/m3u3-smoke.py`, tracked, 40/40 against a real ledger.
    ONE DIVERGENCE INDICTED MAIN'S OWN CODE before commit, found independently by the diff-blind
    verdict table (D12) and the contract attack (A05): MAIN had given both paths a revision pre-read
    plus a seam re-read, so a concurrent `revise_operation` raised "operation revision changed before
    proposal submission" for a DIRECT submission that captured no revision and had no generation
    window to protect. The seam now takes `expected_revision: int | None`; `submit_proposal` passes
    None and opens exactly ONE transaction, `propose` keeps the two-read guard. That pair is the
    whole return on dispatching the verdict table BEFORE implementing.
    WAVE 2 HARVESTED + CLOSED, all three seeded by a MAIN-committed validator + all-`unknown`
    skeleton (`m3u3-wave2-validate.py`, kinds `verdicts`/`attack`/`probes`, graded both ways at
    seed). Every teammate ADDED rows beyond its seed, which is the seeding format working:
    `test-m3u3-1` 46 -> 58 loci (12 `X` extension rows), 48 divergent; `rev-m3u3-1` 18 -> 24 lenses
    (6 `Y` rows), blocking=6 material=14 cleared=3 minor=1; `orc-m3u3-1` 30/30 probes + a full
    independent implementation. All 58 verdicts and all 24 dispositions are ruled in contract
    sections 12-13, filled by the idempotent patchers `m3u3-rule-verdicts.py` +
    `m3u3-rule-attack.py` (`--check` = in-sync gate), so the wave re-derives from the teammate
    tables. Worktrees + branches for `test`/`rev` retired; `wt/orc-m3u3-1` RETAINED for S3.
    THE EXTENSION ROWS OUTWEIGHED THE SEED: 8 new contract obligations came from them (B01/B02
    freeze pins with a NAMED baseline, D35-D37 precedence/snapshot/containment, D38/D39
    malformed-return + `BaseException`, D40 canonical snapshot, D41 positive publication), plus D42
    (proposal row shape) and 5 overreach scopings (P04, D04, D11, D23/D25/D33 negative->positive)
    from the attack's own `Y` rows. Seed the skeleton; let the lens grow it.
    X11 WAS A REAL SHIP GAP no other lens caught: `submit_proposal`/`propose` existed in code and
    docstrings while README, `architecture.md` and `threat-model.md` named NEITHER. Docstrings are
    not publication. FIXED at S2 close; D41 now states the obligation positively.
    ORACLE DIVERGENCE PAID: told not to match MAIN, `orc-m3u3-1` BUILT the two-transaction direct
    path that verdict D12 + attack A05 had only warned about, exhibiting the `StateError` MAIN
    removed. Its second divergence (clock read before the write transaction, to shorten lock hold)
    is a sound trade that M3.1's ruling already decides against.
    P06 HAS THREE SLICING CONVENTIONS, not two, and the pin now ships the table: 12,866 B
    `1182130a2b3a` (whole-line span, trailing newlines stripped - THE PIN), 12,867 B `cd60036faf5c`
    (newline kept), 12,862 B `c27e71b0b4c7` (`ast.get_source_segment`, drops the indent). Same
    unchanged source. A lens on the wrong row reports correct code as stale, so grade a finding by
    whether its reproduction is stated, never by whether its number differs.
    SUBAGENT HARNESS FORBIDS `.md` REPORT CREATION. Two of three teammates reported inline and named
    the blocker; MAIN materialized `.scratch/agents/<name>.md` from their transcripts. Brief the
    report destination as a transcript-final-response format, not a file, until this changes.
    SEEDING, fifth datapoint, and a NEW failure mode with its fix measured: `orc-m3u3-1` sat at
    UNKNOWN-CELLS 32 across four polls while it built its implementation first, exactly as its brief
    ordered. One flush directive re-ordering the work - answer probes against whatever is green,
    `unreachable` + a note is a FILLED cell - moved it to 19 within one poll. Seeding the deliverable
    does not help when the BRIEF sequences the ungraded half first; order the graded artifact first
    and let the implementation catch up.
    S3 DONE, battery session, ran past one compaction boundary. `main=` 92% 222K/240K at the
    boundary and 96% 230K/240K in the post-compaction close window; `mate=` 99% 239K/240K
    (`rev-m3u3-2`; `test-m3u3-2` 78% 187K, `diff-m3u3-1` 72% 173K). A REPORT EMITTED AT 99% IS
    CONTEXT-STARVED: `rev-m3u3-2` delivered 22 complete rows and could not have answered a
    follow-up, so every one of its findings had to be re-derived by MAIN before action - which is
    what caught that two of its six blocking-or-material instrument findings were already satisfied
    by the battery it never read.
    Gate reruns from committed state: 741 tests, 0 failures, OK, 173.967 s.
    D30 AND X12 ARE BOTH DISCHARGED, which was S3's whole job. D30 publishes three verbatim commands
    and enumerates all 42 mutants by site; X12 ships as D15's fifth pin, the rollback matrix
    injecting after each interior write. MEASURED at close: gate 741 / 0 failures / 0 errors /
    0 skips / 205.725 s · grader 52 obligations / 73 tests / UNFILLED 0 / PASS · sweep 42 mutants /
    0 survivors / 0 battery gaps against a green control.
    A MUTATION NUMBER IS MEANINGLESS WITHOUT ITS VERDICT MODULE LIST. The pre-battery baseline read
    13 survivors of 41 against `tests.test_submission` alone; the same corpus against that module
    plus `tests.test_submission_battery` kills all 42. Print the verdict modules with every sweep.
    DIFFERENTIAL RUN AND CREDITED BY MAIN'S OWN RE-DERIVATION, not merely ruled: 30/30 seeded probes
    identical, all four Z extensions byte-identical to their recorded MAIN observations, re-derived
    against the shipped post-fix `system.py`. THE EMPTY SEEDED DIVERGENCE SET IS THE FINDING - the
    oracle wrote its probes to demonstrate its own conformance, so they cannot discriminate two
    designs. Only MAIN's four added Z probes, aimed at the RULED divergences, made the instrument
    evidentiary; Z03 exhibits the oracle raising `StateError` and storing nothing where MAIN
    succeeds, which is the defect V-D12 removed from MAIN's code.
    TWO CODE DEFECTS FOUND AND FIXED, each confirmed by two independent lenses: `dict(provenance)`
    accepted pair iterables as a mapping (now `isinstance(..., Mapping)`, D43), and
    `System.__init__` pre-flighted `callable(getattr(source, "propose", None))`, which executes a
    raising descriptor at construction and leaked its planted secret. The pre-flight is DELETED -
    a RULED public behaviour change on a surface stable since `3b7769b`, recorded in D37 with its
    grounds and its `tests/test_system.py` landing site.
    A DEAD BRANCH AND A SURVIVING MUTANT ARE ONE FACT SEEN TWICE: `provenance-object-check-deleted`
    survived because `canonicalize(dict).value` is always `dict`, which the review reached
    independently as a KISS defect. Deleting the branch removed the mutant and a section 7 row.
    S4 DONE, closure session, ALL SIX CARRIED ROWS DISCHARGED. `main=` 86% 207K/240K at the
    roadmap-close point; `mate=` 58% 138K/240K (`prod-m3u3-2`; `rev-m3u3-3` 40% 96K). Shipped at
    `543d2af` + `e3e8351`. Gate reruns from committed state: 744 tests / 0 failures / OK /
    175.071 s · smoke 40/40 · sweep 48 mutants / 0 survivors / 0 battery gaps against a green
    control, verdict modules `tests.test_submission` + `tests.test_submission_battery`.
    Z05/Z06/Z02/Z03 all closed the same way: the instrument was DERIVED instead of named. Z05 -
    both `tests/test_submission.py` and `m3u3-smoke.py` now read the table set from `sqlite_schema`
    under ONE exclusion rule (the `sqlite_` prefix) and assert 13. Z06 - D17's spy became a
    COMPLEMENT, asserting the application tables named EQUAL the permitted four, over tokenized
    case-folded identifiers, with the recorder total over `execute`/`executemany`/`executescript`/
    `cursor()`. Z02 - an AST probe over each public method's `self`-call closure requires exactly
    ONE writer in it and that it is `_persist_proposal`; closure scoping keeps `handle`'s own writes
    out. Z03 - one `inspect.signature` + `typing.get_type_hints` test. Corpus 42 -> 48; all six new
    mutants killed.
    R06 + R07 CLOSED BY PUBLICATION, NOT BY REPAIR. D45 states SUBMISSION-ATTRIBUTABLE once and
    scopes D01/D07/D09/D15/D16 to it: BOTH paths execute caller code (the source adapter; the
    provenance mapping's `keys()`/`__getitem__`), either may reenter and commit, so all five are
    false read unscoped. D46 publishes the window - `StateError` `database is busy or unavailable`,
    no proposal id, `{requests:1, proposals:1, events:1}` durable - with enumeration as the recovery
    route and never retry, since D04 gives no idempotency. D15 now says before-commit; D16 withdraws
    "no failure reaches commit" as an overclaim.
    THE WINDOW IS A `Store` PROPERTY, MEASURED: `handle` and `register_operation` exhibit it with
    the identical class and message (W10, W11), so scoping it inside M3.3's candidate boundary would
    have misattributed it. Evidence = `.agent/decisions/m3u3-window.json` (12 rows, validator PASS)
    + `m3u3-window.py`, re-derived by MAIN's own run.
    TWO CLAIMS THAT MUST NOT MERGE, and the teammate harness caught MAIN merging them: the caller's
    EXCEPTION SURFACE is identical whether the commit failed before or after durability, but a
    subsequent READ separates the two (pending count 0 vs 1) - which is exactly why the recovery
    route works. MAIN's own control had compared durable-raise against success, a different pair,
    and the first D46 wording read as "unknowable". W12 pins both halves.
    A DIFF-BLIND EVASION MATRIX IS WORTH ITS DISPATCH: `rev-m3u3-3` filled 18 rows (11 blocking)
    knowing only the six acceptance checks, never MAIN's diff. Sixteen confirmed MAIN's pins already
    defeat the evasion - A13's `main."ARTIFACTS"` quoting, A15's `cursor().execute` channel, A12's
    projection back to nine names, A17's deleted positive control. A01 was a REAL uncaught gap:
    D45 scoped the contract while `propose`'s docstring and README still claimed the whole call
    writes three rows, which a reentrant source falsifies. Fixed at `e3e8351`+. Matrix committed as
    `.agent/decisions/m3u3-s4-attack.json`.
    SEEDING, sixth and seventh datapoints, both confirming the standing rule and adding one:
    `prod-m3u3-2` filled 9 of 12 rows in three committed batches unprompted. `rev-m3u3-3` sat at 0
    of 72 cells across four polls, took ONE flush directive re-ordering fill-before-execute, and
    delivered all 18 rows at `UNKNOWN-CELLS: 0`. NEW: its report said the directive arrived AFTER it
    had finished, so a flat poll can mean a long tool call rather than a stall - the directive still
    cost nothing, but read a frozen gauge plus a frozen transcript mtime together before ruling a
    teammate stalled.
  - M3.4 DONE tier=kernel tags=oracle depends=M3.3 - freeze request-free proposal/read/review/report/event
    public seams behind one internal binding adapter, schema still v2. Budget FOUR MAIN sessions per
    the oracle estimator: contract, implementation, battery, closure.
    S1 DONE, contract session, `main=` 84% 203K/240K against the estimator's 84-86%; `mate=` 70%
    168K/240K (`spike-m3u4-binding`; `map-m3u4` 61% 146K, `spike-m3u4-projection` 60% 143K).
    Shipped at `da63741` + `6ea4c9c`: `.agent/decisions/m3u4-contract.md`, 13 sections, 27
    obligations, sections 12-13 PENDING.
    SURFACE FIXED BY MEASUREMENT, not by the draft: M3.4 owns exactly EIGHT `requests` sites in
    `system.py` (1300, 1340, 1378, 1451, 1487, 1616, 2920, 2940), AST-attributed at `da63741`. The
    other 14 carry their owning unit in contract section 1.
    THE PLAN DRAFT'S CENTRAL PREDICATE IS EXPIRED AND DOES NOT SHIP. Its seed - "an application-SQL
    proxy rejects any statement naming `requests`" - was written assuming M3.3 delivered schema v3.
    Schema cuts ONCE at M3.6b, so `_persist_proposal` still writes the proposal's scope, input and
    revision onto a private request row and every read joins to recover them; that proxy would
    reject the unit's own storage layer. Replacement = CONFINEMENT (D01-D06) + PUBLIC SHAPE
    (D07-D14), where confinement is a COMPLEMENT assertion over the shipped module (the set of
    definitions whose SQL names `requests` must EQUAL a permitted set), because a forbidden-list
    grep fails open on exactly the member nobody thought of.
    SIZING RULED, NO PRE-OPEN SPLIT, and measured rather than forecast. The draft estimated
    260 prod / 240 test behind a trigger the plan review itself rejected as not pre-open measurable,
    so MAIN deleted the surface and let the gate produce the work list (`m3u4-burden.py` +
    `m3u4-burden.json`, three staged gate runs against fresh worktrees at `da63741`): stage 1 drop
    the two `request_id` fields = 252 broken / 3 frames; stage 2 + repair the production
    constructors = 9 broken / 9 frames; stage 3 + `review` returns `ReviewResult` = 112 broken / 13
    frames. 243 of stage 1's failures are a production cascade from TWO constructors
    (`get_proposal` 227, `_pending_proposal_gap_from_row` 24) and 100 of stage 3's stand behind ONE
    fixture helper (`tests/test_cli.py:245` in `confirm`). Work list = ~21 distinct test methods
    plus one helper against ~20 production lines outside the adapter. A BREAK COUNT IS NOT A WORK
    LIST until its shared frames are factored out - here they differ by 28x.
    BOTH FORKS UNRULED, and the cause is MAIN's dispatch, not either teammate. Wave 1 = `map-m3u4` +
    two spikes, all three seeded by a MAIN-committed validator. `map-m3u4` delivered
    `UNKNOWN-CELLS: 0` at 42 rows (37 seeded + 5 extension). Both spikes also filled all 14 probe
    rows - and both reported `adapter_present=False` on EVERY one, because they answered the whole
    corpus against BASELINE exactly as the brief ordered ("fill the graded artifact first,
    implementation second"). Thirteen of fourteen probes were answerable WITHOUT an implementation,
    so the graded metric reached zero while measuring only the status quo, and neither added the
    `Z50` swap row MAIN sent mid-flight.
    A PROBE CORPUS ANSWERABLE AGAINST BASELINE DOES NOT FORCE AN IMPLEMENTATION. This is the
    seeding rule's next failure mode after "order the graded artifact first": ordering it first
    works, and it silently substitutes for the ungraded half whenever the graded rows can be
    answered without it. Fix, binding on every future spike - write each probe as a DELTA requiring
    both sides, or make the implementation a separately graded deliverable the validator can see.
    WAVE 1 STILL PAID. The two spike artifacts are a thorough baseline census the contract's corpus
    and the battery consume directly: exact SQL statement counts per read path (`get_proposal` 7/1,
    `proposals` 7/1, `function_report` 19/13 with 2 request statements, `review` accept 14/8 correct
    14/8 reject 12/6), the collider matrix, middle-and-last corruption classes, the `.review(`
    census (30 = 24 tests + 5 examples + 1 production), and the verbatim CLI JSON for all three
    decisions. And `wt/spike-m3u4-binding` DOES carry a real ALT-BINDING implementation, +433/-147,
    adding `_ProposalBinding`, `_ProposalBindingSet`, `_proposal_binding`, a BATCH
    `_proposal_bindings` answering the N+1 exposure, and `_write_proposal_request_status`. Its own
    table never measured it; the diff is the evidence.
    THE CLOSE ORDER'S PER-WORKTREE STATUS READ PAID FOR ITSELF. `spike-m3u4-projection` looked
    implementation-free until `TaskStop` cut it mid-write: its uncommitted tree held a full
    ALT-PROJECTION (+181/-117 - `_PROPOSAL_BINDING_SQL`, a `_ProposalBinding` record, a
    `_proposal_binding(row)` validator), preserved at `cb0ef3e`. Both spikes built their alternative
    AFTER the flush directive re-ordered their work, so the corpus defect DELAYED the
    implementations rather than preventing them. Reading status per worktree in its own call, at
    the last point the content exists, is what kept a whole design alternative.
    FIRST COMPARABLE NUMBER favours ALT-PROJECTION: +181/-117 against ALT-BINDING's +433/-147 over
    the same eight sites. Size only, from two trees of unequal maturity - it settles nothing alone
    and `Z50` remains the deciding criterion.
    S2 ENTRY STATE: contract sections 1-11 are binding; open with the fork rulings, not with code.
    All three worktrees are RETAINED and BOTH spikes hold a shipped alternative, so ruling fork 1
    is now a differential over two committed diffs plus `Z50` on each, with neither side built from
    nothing. Rule fork 2 against the P08 baseline CLI payloads. MAIN must also validate
    `m3u4-map.json` before crediting it; it is attention-directing, harvested but not re-derived.
    ONE BASH WORKING DIRECTORY IS SHARED BY MAIN AND EVERY TEAMMATE. MAIN `cd`-ed into its own
    measurement worktree and silently moved all three teammates' shells; one spike caught it and
    invalidated a batch of measurements. Anchors and line numbers taken this way look valid and
    resolve to the wrong bytes. MAIN now runs every located command as `(cd <path> && ...)` in a
    subshell or `git -C`, and every brief carries a mandatory per-call `cd <worktree> &&` prefix.
    S2 DONE, implementation session, `main=` 98% 236K/240K, over the estimator band; `mate=` 85%
    205K/240K (`rev-m3u4-1`; `test-m3u4-1` 52% 125K). Shipped at `bdbe94a` (system), `0e9130c` +
    `d8ab9fc` (validator), `c603b07` (sections 14 + 57 verdicts), `d1621ab` (section 15 + 39
    lenses). Gate 744 -> 753 tests, OK, 173.8s; failures ran 121 -> 15 -> 3 -> 0.
    BOTH FORKS RULED. Fork 1 = COMPOSE, neither spike as written: `_proposal_bindings(connection, *,
    partition, selection)` issues the COMPLETE statement per selection over `_ProposalIds` /
    `_ProposalFeed` / `_PendingProposals`, `_write_proposal_request_status` is the sole review-path
    writer, `_proposal_binding` is a SQL-free singular wrapper, and the inner JOIN is preserved
    everywhere. Fork 2 = R2+, four fields, with `status` newly `accepted`/`corrected`/`rejected` -
    a ruled public behaviour change, because baseline said `resolved` for BOTH confirming decisions.
    A SPIKE'S SHIPPED DIFF CARRIES DEFECTS ITS OWN TABLE NEVER MEASURED. Both spikes graded
    UNKNOWN-CELLS: 0; the ruling came from reading the two diffs. ALT-PROJECTION left two raw
    `UPDATE requests` in `review` (a read-only SQL constant cannot confine a write, and it built no
    writer). ALT-BINDING confined in full but was a SIDE lookup that M3.6b's direct columns are
    PREDICTED to delete. Choose the alternative predicted to survive the NEXT unit, not the smaller
    diff: +181/-117 lost to +433/-147 here. That prediction rests on Z50's COUPLING CENSUS, and a
    census measures coupling, never survival - M3.6b is what tests it.
    THE ATTACK TABLE FALSIFIED A COMMITTED GROUND, which is the highest-value thing wave 2 produced.
    Y9 ran both shapes through `EXPLAIN QUERY PLAN` (SQLite 3.53.1) and got IDENTICAL plans, so the
    "ALT-PROJECTION materializes the partition before filtering by operation" ground is WITHDRAWN -
    SQLite flattens the wrapper and pushes the predicate down. The ruling stands on its other two
    grounds and the LEFT JOIN ground got sharper. Standing rule: a subquery is not a materialization,
    so never assert a query plan without running the planner.
    FOUR MORE CLAIM CORRECTIONS, all against text MAIN had already committed: Z50 is a COUPLING
    CENSUS, not a performed swap (A18); section 1's "no consumer loses information" was false for
    public consumers (Y18); D12's byte-identity rule had to exempt `status` explicitly (Y4); D24's
    "fabricated only" premise was false on two real-ledger paths - malformed JSON in a schema-valid
    TEXT column, and five legitimately-nullable columns (A14, Y17).
    A VALIDATOR SEEDED BEFORE ITS CONTRACT GREW BLOCKS EVERY TEAMMATE AT ONCE. The `SECTION` regex
    accepted `D<nn>` only; MAIN then appended sections 12-13, so both teammates hit INVALID on
    legitimate citations and neither could reach a clean grade. Two grammar widenings failed before
    the right move: pull the CENSUS of all 77 distinct values and check the two things a pointer can
    be checked for - it resolves somewhere, and it stays under 60 chars. Re-grade both ways after
    any validator edit; the seed credential dies with it.
    WAVE 2 CLOSED BOTH TABLES: 57 verdicts (22 seeded + 35 extension) and 39 lenses (18 + 21), each
    ruled through an idempotent `--check` patcher that pins serialization by round-trip before
    writing and asserts the id set. Extensions outnumbered seeds in both.
    S3 ENTRY STATE, battery session. Sections 1-15 are binding; 15 lenses carry a `DEFERRED-S3`
    disposition (A02, A07, A08, A09, A10, A13, A15, Y7, Y8, Y11, Y12, Y14, Y16, Y20, Y21) with the
    battery obligation named per lens in `m3u4-attack.json`; two further rows name S3 in prose
    (A04 corrected, Y15 scheduling the section 12-13 archive move) - the sharpest are A13 (both assertions
    D23 permits survive an ORDER BY change, so self-consistency is not a pin), A02 (Literal is not
    runtime-enforced, so both confirming paths can still return `resolved`), Y11 (a validation SELECT
    inside the adapter recreates the per-consumer cost that ruled ALT-BINDING out), and Y8 (a
    survivor count needs its catalogue). `orc` was deliberately deferred to S3: an oracle corpus
    written to demonstrate its own conformance is a control, and the evidentiary probes are the ones
    MAIN aims at the ruled disagreements, which exist only now that the implementation has landed.
    Section 15 schedules the contract's wave chronology for `.agent/archive/` at milestone close;
    its grounds are still load-bearing for the battery.
    S3 DONE, battery session, ran past one compaction boundary. `main=` 76% 183K/240K; `mate=` 100%
    240K/240K (`test-m3u4-2`; `diff-m3u4-1` 68% 163K, `orc-m3u4-1` 63% 151K, `gate-m3u4-1` 62% 149K,
    `rev-m3u4-2` 53% 126K). Shipped at `841e710` + `6e9ac37` + `1143332` (system + contract) and this
    commit. Gate 753 -> 755 -> 756 -> 811 tests, OK, 180.5s.
    THE DIFFERENTIAL FIRED AND FOUND A FOURTH CODE DEFECT, which is the whole reason `orc` exists.
    An EXISTING proposal whose private request row was deleted hid behind the inner join: all four
    read paths reported `NotFoundError`, which section 14 rejects, and `841e710` had closed the
    report count alone. `6e9ac37` LEFT JOINs the ids and feed statements and refuses a NULL
    `bound_request_id` in `_proposal_binding_from_row`. NO REVIEWER LENS CAUGHT IT because the four
    paths AGREED WITH EACH OTHER; agreement among sibling paths is not evidence, and only an
    implementation built to a contract rather than to MAIN's code disagreed. `test-m3u4-2` found it
    independently, so two lenses confirmed before the fix.
    A MUTATION HARNESS HIDES VERDICTS TWICE OVER, and both failures abort rather than report. Stale
    anchors: `841e710` and `6e9ac37` rewrote the statements six mutants target, and the first
    `ANCHOR-MISS` aborted the campaign, hiding 35 later verdicts. The naive whole-string census said
    10 stale and was WRONG - multi-patch mutants join sections with `---`; loading the harness's own
    `MUTANTS` gave 6 mutants over 12 patches. Fixed by an idempotent re-anchor script plus an anchor
    PRE-FLIGHT census that prints every stale anchor at once. Two of the six INVERT rather than move,
    and that is the substance: M18 becomes outer-to-INNER and M34 becomes `binding`-to-`binding.row`,
    because the shipped code is now what they used to mutate INTO. A mutant left pointing at its own
    fix tests nothing.
    THE SECOND HARNESS DEFECT IS THE SUBTLER ONE. `first_failure` matched only the docstring-free
    one-line verbose record (`test_x (tests.M.C.test_x) ... FAIL`); a docstring moves `... FAIL` onto
    the next line, so a mutant whose only witnesses were battery tests raised
    `VERDICT-FAIL-WITHOUT-TEST` and aborted at M33. The summary header `FAIL: name (tests.M.C.name)`
    is authoritative instead, because it survives both a docstring and a subtest. STANDING RULE: the
    catalogue is written PER MUTANT, so an aborted campaign leaves a MIXED table - classify every row
    by its own recorded verdict-module list before quoting a survivor count.
    DECISIVE MUTATION CAMPAIGN: 44 mutants over FOUR verdict modules (`test_proposal_binding`,
    `test_proposal_binding_battery`, `test_system`, `test_cli`), control green at 538, 40 KILLED, 0
    equivalent, 4 SURVIVED - `M02`, `M03`, `M15`, `M26`, every one an unforced guard the polish row
    owns. The 3-module campaign had said 35/9. Its named killers cite classes that were never
    written, so a prescribed killer is a PRESCRIPTION and only the module-set verdict is a
    measurement.
    TWO SURVIVORS WERE REAL GATE GAPS AND BECAME OBLIGATIONS. B39 pins the feed's ascending
    `status_sequence` and its LIMIT, which one row per call cannot observe. B40 pins
    `binding.request_status` against the REQUEST row on a ledger whose two status columns differ -
    every fixture that transitions a proposal moves both rows together, so reading the proposal's own
    column stayed correct everywhere the suite looked. Battery 53 -> 55 tests, 40 obligations, PASS.
    BOTH DIVERGENCES RULED MAIN-CONFORMING AGAINST TEXT THAT OVER-CLAIMED. 42 probes, 40 agree. Z03:
    X32's obligation is a MISSING binding beyond the cap, which the unbounded pending count proves;
    its rationale "the cap bounds returned detail, never validation" is WITHDRAWN, because
    cross-field consistency and JSON content hold for RETURNED DETAIL alone and the same corruption
    still fails closed on every other path. Z15: section 12's "one complete statement per selection"
    was already withdrawn for the pending selection, whose pair is exactly what X32 and section 15
    require together. Both rulings are now in the contract, in `_proposal_bindings`' docstring, and
    in `docs/architecture.md`.
    S4 DONE, closure session, R15 DISCHARGED and the unit CLOSED. `main=` 90% 217K/240K; no teammate
    dispatched - the whole session is contract judgment, which is MAIN-retained work. Shipped at
    `cd172b5`. Gate reruns from committed state: 811 tests / 0 failures / OK / 180.703 s · battery
    grader 40 obligations / 55 tests / UNFILLED-TESTS 0 / OBLIGATIONS-UNCOVERED 0 / PASS ·
    `m3u4-archive-validate.py` PASS.
    Sections 7 and 12-15's wave chronology, dispatch history and worktree state moved to
    `.agent/archive/m3u4-chronology.md`; every ruling, interpretive ground and measured number stayed
    in the contract.
    FOUR CLAIM DEFECTS SURFACED BY THE MOVE ITSELF, none caused by it. (1) Section 10 required "the
    mutation sweep at zero survivors" while the decisive campaign leaves four RULED survivors - the
    contract's own acceptance predicate contradicted its own recorded outcome, so it is WITHDRAWN for
    the named survivor SET, under which a fifth survivor fails and these four do not. (2) Section 15
    cited the attack table as 24 lenses; the committed table holds 39. (3) Battery obligation B32
    grades against `SCHEMA_VERSION` 2, 14580 bytes and sha256 `5be3d79f...`, and the contract stated
    none of them - section 1 now carries the freeze, re-derived from `store.SCHEMA`. (4) Tag
    `m3u4-alt-projection` still asserted the materialization ground section 15 measured FALSE;
    retagged with the two surviving grounds.
    A CLOSURE SESSION MUST RE-GRADE THE CONTRACT'S OWN GATE TEXT against what the campaign actually
    measured. Every one of the four is a claim MAIN wrote and no instrument was pointed at, because
    each instrument grades the code against the contract and none grades the contract against the
    instruments' results. Seventh consecutive unit whose closing findings are claim defects in MAIN's
    own text.
    THE MOVE IS GATED, not asserted: `m3u4-archive-validate.py`, six checks over DERIVED domains -
    SECTIONS 15/15, OBLIGATIONS D01-D27, CITATIONS 332 resolved across six artifact tables, NUMBERS
    70, IDENTIFIERS 164, BATTERY-NUMBERS 5. Its first draft graded by CONTAINMENT and passed
    immediately; tightening to whole-token membership exposed two real losses it had certified as
    fine, since `24` sits inside `243` and `_proposal_binding` inside `_proposal_bindings`. Graded
    both ways on staged copies via `--root`, one seed per check.
    Polish gains one row: all five M3.4 evidence tags are local-only and `origin` carries no tags, so
    every clone resolves none of them. No claim depends on them - each ruling's grounds are restated
    as measured facts - but publishing is the owner's call.
  - M3.5a IN-PROGRESS tier=kernel tags=- depends=M3.2b,M3.4 - add `resolve` and `proposal submit` CLI
    channels with exact exit and payload contracts. Sessions: S1 wave 1, S2 fork ruling + contract,
    S3 implementation, S4 battery + closure.
    S1 DONE, wave-1 session, `main=` 85% 204K/240K; `mate=` 67% 161K/240K (`map-m3u5a`;
    `spike-m3u5a-flags` 65% 157K, `spike-m3u5a-envelope` 57% 138K). Shipped at `773959f` (validator +
    seeds) + `07c295d` (evidence). No contract line written - see the measurement below.
    SEEDING, eighth datapoint, 3/3 AGAIN, and the M3.4 failure mode is CLOSED BY CONSTRUCTION. Every
    artifact reached `UNKNOWN-CELLS: 0` and every one re-derives to PASS under MAIN's own run from the
    primary tree. The fix for "a probe corpus answerable against baseline forces no implementation" is
    mechanical, not exhortative: each spike row carries BOTH a `baseline` and an `alt` observation, the
    validator requires >= 15 rows separating them, plus a resolvable probe driver and a `+N/-M` header
    with >= 20 additions. Result 32 and 24 real deltas and TWO SHIPPED ALTERNATIVES, against M3.4's two
    baseline censuses. Graded both ways at seed with 8 negative controls (stale anchor, absent symbol,
    short prose, dropped seed row, unimplemented alternative, alt==baseline everywhere, bad verdict
    token, absent driver); all 8 fire.
    EXTENSIONS OUTNUMBERED SEEDS AGAIN: map 55 rows on a 25-row seed, envelope 32 on 20, flags 24 on 20.
    EVIDENCE IS TRACKED, not a `wt/` branch or a local tag: `.agent/decisions/m3u5a-alt-envelope.patch`
    and `m3u5a-alt-flags.patch` carry the two implementations, beside their tracked probe drivers, so
    apply-plus-run re-derives either table in any clone. This is M3.4's polish row discharged in advance
    for this unit rather than deferred.
    THE FLAGS ADVOCATE RULED AGAINST ITS OWN ALTERNATIVE, second occurrence on this project, so the
    council rule can close fork 1 without a third spike - but the ruling still gets made from the two
    diffs, per M3.4's measured rule that a spike's shipped diff carries defects its own table never
    measured. Its grounds, measured: real `execve` accepts 131,071 bytes and refuses 131,072 with
    `E2BIG` against a 1,048,576-byte per-field contract, and only ONE field can leave argv through
    stdin; every literal flag value is world-readable in `/proc/<pid>/cmdline`; repeated flags are
    silently last-wins. Its counterweight is real: +23/-1 against the envelope's +97/-3, direct mapping
    onto the landed API, and no candidate-source reach. Envelope measured a 2,162,722-byte aggregate
    bound with an adjacent pair, exact-key rejection, and a provenance 65,536/65,537 pair.
    B02 IS A FROZEN-FILE TRIPWIRE THIS UNIT MUST DISPOSITION, found independently by both spikes:
    `tests.test_submission_battery` B02 asserts `cli.py` byte equality to `f9b9755`, so every gate run
    in both worktrees was 810 passed / 1 failed on exactly that pin and nothing else. M3.5a edits that
    file by definition. The contract states the new pin; a brief forbidding gate edits without naming
    its tripwires would otherwise push the cost into production code.
    ARGPARSE PREFIX LEAKAGE IS REAL HERE: the shipped `--out` abbreviates a new `--output`, and `--sub`
    resolved to a new `--submission`. Both spikes hardened their own leaf. This bears directly on
    M3.5b's removed-flag pins, which cannot be written as absence alone.
    MEASUREMENT, binding on M3.5b..M3.9b. A `-`-tagged kernel unit with a 3-teammate wave 1 does NOT
    reach its contract in S1: MAIN went 57% -> 85% (137K -> 204K, ~67K) buying validator authoring plus
    both-ways grading, a 3-teammate dispatch, seven polls, worktree harvest, MAIN's own re-derivation of
    all three grades and reruns of both drivers - with zero contract lines written. M3.2a's oracle wave 1
    cost ~105K and DID include the contract, so the difference is not the oracle tag: it is that MAIN
    entered at 57% against M3.2a's 31%, because M3 attached state plus this unit's ground-state read now
    costs a third of the window before any dispatch. Two consequences: budget a wave-1 session at ~70K
    of MAIN ON TOP of the entry cost, and treat the entry cost itself as the thing to cut.
    S2 ENTRY STATE: rule fork 1 from the two TRACKED PATCHES plus the two tables, never from the reports
    - `spike-m3u5a-envelope`'s report was cut mid-write, so its verdict exists only as its table. Rule
    the `resolve` payload shape against the shipped `function eval` and `function verify` precedents
    that map rows M01/M02 anchor. Then write the acceptance contract. All three worktrees are RETAINED
    at `.scratch/worktrees/`; `map-m3u5a` holds no implementation, both spikes do. MAIN must validate
    `m3u5a-map.json`'s 55 rows before crediting them: the grade proves each anchor resolves and each
    cell is filled, never that a finding is true.
  - M3.5b tier=kernel tags=- depends=M3.5a - remove `handle`/`request`/source grammar, imports, fixtures,
    help and operator prose.
  - M3.6a tier=kernel tags=- depends=M3.5b - delete public lifecycle methods, leases, result models and
    exports; retain only the private v2 binding plumbing.
  - M3.6b tier=kernel tags=prod depends=M3.6a - the sole schema cut v2->v3: direct proposal columns,
    adapter swap, `requests` plus index deletion, refusal fixtures, package 0.2.0.
  - M3.7 tier=kernel tags=prod depends=M3.3,M3.5b - relocate the command runtime to an optional example
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

  SIZING CAVEAT - M3 opens with NO validated one-window estimator. Every M2 gauge was recorded under split
  authorship, MAIN paying coordination while a teammate paid implementation; MAIN now pays both from one
  window, so no M2 half predicts an M3 unit. M3.1 is therefore the calibration unit: record its actual
  `main=` at close and resize every later unit against that measurement before opening it. Undershooting
  is cheap here because the three surface maps carry 740 resolving `file:line` anchors, which replaces
  whole-file rereads with targeted reads and makes fine cuts cheaper than the giant-file heuristic
  assumes. A pre-open size trigger must be a STATIC source-span budget; a trigger that needs the
  completed diff (byte equality, post-factoring line counts) is unmeasurable before the unit opens.

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
