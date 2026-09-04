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
  - M3.5a DONE tier=kernel tags=- depends=M3.2b,M3.4 - add `resolve` and `proposal submit` CLI
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
    S2 DONE, fork-ruling + contract session, `main=` 79% 190K/240K. NO teammate dispatched: fork
    arbitration plus contract authoring is MAIN-retained work, the same shape as M3.4's S4.
    Shipped: `.agent/decisions/m3u5a-contract.md` (14 sections, 30 obligations D01-D30 gapless,
    sections 13-14 PENDING) + `m3u5a-s2-probe.py`, MAIN's own re-derivation of the six map findings
    the contract asserts as fact.
    BOTH FORKS RULED, each from the two TRACKED PATCHES rather than the tables or the reports.
    Fork 1 = ENVELOPE CORE, `@PATH` REMOVED, cap DERIVED - neither spike as written. The decisive
    ground is ASYMMETRY OF RELIEF, not the shared wall: both spikes measured the identical `execve`
    ceiling (131,071 bytes launch, 131,072 = `E2BIG`), but only ONE field can leave argv through
    stdin because the second `_input("-")` reads a drained stream, so a flags submission can NEVER
    carry more than one of three fields at the library's 1,048,576-byte contract, under any
    invocation, and at least two of three candidate fields are always world-readable in
    `/proc/<pid>/cmdline`. One `--submission -` frame carries all three at their maxima, measured at
    exactly 2,162,722 bytes accepted and one more rejected. Unconditional defect loses to a
    conditional one whose regime the operator chooses.
    A SPIKE'S SHIPPED DIFF CARRIES DEFECTS ITS OWN TABLE NEVER MEASURED, second consecutive unit.
    The envelope's `@PATH` reader opens `pathlib.Path(...)` directly and inherits NONE of
    `_read_function_bundle`'s descriptor hardening (`O_RDONLY|O_NONBLOCK`, `fstat` regular-file
    grading, bounded read, strict UTF-8), so a FIFO blocks and a directory answers through OS
    wording; its own `Y06` row measured the message taxonomy alone. `@PATH` is CUT and the channel
    loses nothing - `--submission - < file` is the file route. Its aggregate cap also wrote a FOURTH
    copy of the provenance limit; MAIN's probe measured 3 unexported `65_536` literals already in
    `system.py`, so the ruling exports `PROVENANCE_MAX_BYTES` and derives the cap. That constant is
    the whole production change outside the two new leaves.
    Fork 2 = ONE FIXED SEVEN-KEY PAYLOAD across all three resolve states, ruled against the shipped
    exit-6 stdout precedents, which are fixed-key on both branches without exception. `passed`, not
    the draft's `verified`, because it is `FunctionVerification`'s own field name and `function
    verify`'s own key. `matched` is three-valued - `true`/`false`/`null` - so a verified miss and a
    failed verdict stay distinguishable under their shared exit 6, with the biconditional scoped to
    values `System.resolve` actually returns. `--expected-function-hash` IS exposed, widening the
    draft grammar: it is the only single-snapshot route to a pinned resolution, and the workaround
    costs a second full verification plus a gap between two snapshots. `resolve` stays a ROOT leaf.
    THE B02 TRIPWIRE WAS FOUND IN AN UNTRACKED GATE LOG, not in any table, and the contract's first
    draft omitted it. S1 had already flagged it in this roadmap; MAIN still wrote 30 obligations
    without it and caught it only while reading the retiring worktree's leftover log. STANDING RULE:
    a tripwire named in the roadmap becomes a numbered contract OBLIGATION in the session that opens
    the unit, or it re-emerges in the next session disguised as a regression. Ruled at D27 - B02
    drops `cli.py` and keeps the other two files frozen, and the retired member's property MIGRATES
    to D24/D25/D26, which are strictly stronger because they constrain what the new bytes may be
    rather than that there are none. Re-pinning `cli.py` per unit is rejected: the plan already
    schedules M3.5b to break it again, and a pin the plan commits to breaking is noise.
    SIZING CORRECTION, binding on M3.5b..M3.9b: THE FOUR-SESSION SHAPE IS DRIVEN BY THE WAVE, NOT BY
    THE `oracle` TAG. M3.2b measured four for an oracle unit and the estimator was written as an
    oracle surcharge; M3.5a carries `tags=-` and is also taking four (wave 1, fork ruling + contract,
    implementation, battery + closure), because the cost sits in dispatching a wave, harvesting it,
    re-deriving its grades and arbitrating its forks. Budget FOUR sessions for any unit that opens a
    spike wave regardless of tag, and budget a unit with no fork to rule WITHOUT S1 and S2.
    WORKTREES RETIRED, branches deleted, NO TAGS. The two implementations, both probe drivers and
    both tables are tracked, so applying a patch and running its driver re-derives either table in
    any clone - M3.4's local-only-tag defect discharged in advance rather than repeated.
    MAIN re-derived 6 of `m3u5a-map.json`'s 55 rows; the other 49 stay attention-directing and are
    recorded as a polish row, because a grade proves each anchor resolves and each cell is filled and
    never that a finding is true.
    S3 IN PROGRESS, implementation session. Shipped at `c8b82cd` (wave-2 seed) + `e6ba873`
    (implementation + publication). Wave 2 = `test-m3u5a-1` (diff-blind verdict table, then the red
    suite) + `rev-m3u5a-1` (contract attack), both in worktrees based at `c8b82cd`, both seeded by a
    MAIN-committed validator (`m3u5a-wave2-validate.py`, kinds `verdicts`/`attack`, graded both ways
    with 12 negative controls) plus all-`unknown` skeletons of 28 verdict loci and 20 attack lenses.
    Contract sections 13-14 still PENDING; the wave fills them.
    SHIPPED: `resolve` as a ROOT leaf placed second in the command list; `proposal submit`;
    `system.PROVENANCE_MAX_BYTES` replacing three unexported literals; `SUBMISSION_MAX_BYTES`
    computed as `2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + framing` where framing is DERIVED
    from `_SUBMISSION_KEYS` (34) rather than copied. Publication landed in README,
    `architecture.md` and `threat-model.md`. Suite 811 -> 811.
    A TRIPWIRE NO OBLIGATION NAMED, and the second one this unit has hit. D16's constant reaches a
    site inside `System.handle`, whose byte span M3.3 froze on three tests, so a value-preserving
    identifier substitution broke the freeze by exactly 14 bytes (12,866 -> 12,880). Re-anchored and
    made STRICTLY STRONGER: each pin substitutes the identifier back and asserts M3.3's own three
    convention numbers reproduce, which proves the substitution is the WHOLE delta. B02 (D27) was
    named and cost nothing; P06 was not and cost a gate cycle. The S2 standing rule needs widening
    from `roadmap-flagged tripwire` to `every freeze pin over a file the unit's obligations touch` -
    B02 froze `cli.py` and was found; P06 froze a METHOD in a file the unit only meant to add a
    constant to.
    MAIN'S OWN SMOKE PROBE (`m3u5a-smoke.py`, tracked, 60 checks / 15 obligations, PASS) found one
    contract-claim defect before any test existed: D01 states an option prefix answers `unrecognized
    arguments`, but when the prefix IS the required option argparse reports the missing option first.
    Both are exit 2 and neither is a silent alias, so the property holds and the wording is wrong.
    Carried to the ruling pass.
    A TRANSPORT-BOUND PAIR MUST BE FIELD-LEGAL. The probe's first at-cap frame spent the whole
    2,162,722 bytes on ONE field, which the library's per-field limit rejects, so it pinned nothing
    about the transport. The real pair puts input, output and provenance each at their own maximum
    simultaneously - which is exactly the submission per-field flags can never carry, so the probe
    now exhibits the fork ruling's own ground.
    SEEDING, ninth datapoint, and the flush directive fired again: both teammates sat at 0 filled
    across three polls with live transcripts, took ONE directive re-ordering fill-before-execute, and
    moved within one poll (140 -> 125 and 60 -> 45 unknown cells, one commit). The directive is
    cheap and the gauge-plus-mtime rule still says read them together before ruling a stall.
    S3 CHECKPOINT 2, both wave-2 tables harvested and ruled. `main=` 95% 227K/240K at checkpoint;
    ran past one compaction boundary. Landed `9372664` verdict rulings, `8b96ab6` + `a0cbc94` +
    `7ad8c53` gate 4, `cc4bc9b` suite validator, `e9f73dd` phase-2 seed (on `wt/test-m3u5a-1`).
    Contract sections 13 and 14 are WRITTEN, no longer PENDING. Verdict table 60 rows ruled
    58 CONFIRMED + 2 SCOPED, 53 ENCODE + 7 ENCODE-SCOPED, by `m3u5a-rule-verdicts.py --check`.
    Attack table 50 rows, 11 blocking ALL RULED, section 14 written. EIGHT binding amendments
    A1-A8 supersede cited section text; A1-A6 in section 13, A7-A8 in section 14.
    Four two-lens confirmations (A01/X02, Y04/X01, Y05/X06, Y06/V02+V18) satisfied the council rule
    without MAIN adjudicating - the diff-blind author and the reviewer found them independently.
    Gate 4 was the session's biggest find and is REBUILT: `m3u5a-s2-probe.py` printed six probe
    results and returned 0 unconditionally, so it could never fail, and its implied pins were the S1
    pre-implementation values that D25 and D16 deliberately move. Now 7 probes, 19 pinned facts,
    15 negative controls, exit 1 on mismatch. Its new `parser_shape` digest (126 actions,
    `89dfa3d982d8c54b`) is what makes D27's migration claim true - it moves on the `events --limit`
    1000->7 mutation that leaves D24, D25, D26 and the census all green.
    Teammates: `test-m3u5a-1` STOPPED at 76% after delivering the 60-row table (report persisted by
    MAIN at `.scratch/agents/test-m3u5a-1.md` - the agent judged report files policy-forbidden).
    `rev-m3u5a-1` STOPPED at 88% after the 50-row attack table; report file likewise absent, its
    findings harvested from the committed table. Both worktrees clean; `wt/rev-m3u5a-1` is
    HARVESTED and removable, `wt/test-m3u5a-1` is IN USE by `test-m3u5a-2`.
    STANDING RULE, cost two harvests this session: the subagent harness FORBIDS report files -
    "Do NOT Write report/summary/findings/analysis .md files. Return findings directly as your
    final assistant message." A brief that names `.scratch/agents/<name>.md` as the report
    destination makes its agent choose between the policy and the brief, and both teammates
    withheld their DONE marker over the conflict. Always brief the report as INLINE final-message
    content with the marker as its last line, and always name the committed artifact - table,
    suite, script - as the real deliverable. Teammate-written `.md` files under `tests/` or
    `src/` are unaffected; the ban is on report/summary/findings prose.

    S3 DONE, implementation session, ran past two compaction boundaries. `main=` 52% 125K/240K at
    close; `mate=` 97% 232K/240K (`test-m3u5a-2`). Phase 2 landed: `tests/test_cli_channels.py`
    60/60 filled and GREEN against the shipped implementation, `m3u5a-suite-validate.py` PASS
    (unfilled/uncovered/orphan/assertionless all 0). Gate 1 = 871 tests OK in 183s (811 baseline
    + 60), gate 4 = rc 0 over 19 CHECK lines. Gates 2 and 3 remain S4's.
    Harvest was a TARGETED CHECKOUT, not `git merge --squash`: `wt/test-m3u5a-1` was based at
    `c8b82cd`, which PREDATES the implementation commit `e6ba873`, so a squash merge would have
    reverted `cli.py`, `system.py`, README, both docs and four `.agent/` files. `git diff
    --name-status main..wt/<name>` showed the branch's only new content was one file (3173
    insertions), harvested by `git checkout wt/test-m3u5a-1 -- tests/test_cli_channels.py` and
    proven byte-identical by sha256. Always read the branch's name-status before choosing a merge
    verb; a worktree older than the primary tree makes squash-merge a silent revert.
    FIRST CONTACT: 58/60 green with zero code changes. Both reds were INSTRUMENT defects, corrected
    verdict table -> red suite, code untouched.
    X19 asserted `stderr.count("\n") == 1` for "exactly one JSON stderr object". `cli.py:382` emits
    every envelope as `json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"`,
    byte-identical at `c8b82cd`, so a one-object failure carries 4 newlines. One object is not one
    line. Replaced by an exact round-trip assertion on that framing, which is strictly stronger:
    it also rejects a second object and any trailing byte. It was the only newline-count assertion
    in the file.
    X28's ruling said README ships "the exit-class table"; the classes ship as PROSE, so its
    markdown numeric-cell regex matched ZERO rows across the whole publication union. Behind that
    failure sat a second latent one: the ruling quoted `resolve writes nothing` unbackticked while
    README:186 ships ``resolve` writes nothing.` and architecture.md:78 seconds it with `The leaf
    writes nothing`. DURABLE RULE, cost both reds: a ruling that quotes shipped prose must quote it
    BYTE-EXACT or name the token search that must match it. Now encoded in X28's own ruling text.
    Negative controls on both corrections, every mutated file restored to a clean `git diff --stat`:
    `indent=2`->`indent=None` turns X19 red (6 subtests); deleting the backticked write-freedom
    sentence turns X28 red; erasing every `exit 5` witness across the union turns X28 red. Deleting
    README's `exit 3` alone SURVIVES, correctly - A6 rules the union and exit 3 has two witnesses
    there, so a per-file mutation cannot falsify a union-scoped obligation.
    `test-m3u5a-2` filled 60/60 across ten six-test checkpoints, reported inline, STOPPED at 97%.
    Its rate went 18 rows in its first 176K then 42 rows in the next 37K: the flush directive that
    named the exact stop condition and the exact report shape was worth more than any added
    context. DIFF-BLINDNESS AUDITED over its transcript - zero reads under the primary tree's
    `src/`, zero `git show main:`, zero `git diff main`; its two `e6ba873` mentions are MAIN's own
    ruling text quoted inside the verdict table it was entitled to read.
    Worktree and branch REMOVED; `git worktree list` is the primary tree alone and zero `wt/`
    branches remain.

    S4 ENTRY STATE: fill the attack table's per-row `disposition`/`main_note` columns through an
    idempotent `--check` patcher asserting the id set (pattern `m3u5a-rule-verdicts.py`; every
    blocking ruling is already binding in section 14, the patcher records rather than decides).
    Run the diff-blind obligation battery (`tests/test_cli_channels_battery.py` graded by
    `m3u5a-battery-validate.py`, one test per D01-D30) requiring `UNFILLED-TESTS 0`,
    `OBLIGATIONS-UNCOVERED 0`, `ASSERTIONLESS 0` and `SKIPPED 0`, and the mutation sweep with its
    verdict module list printed, its acceptance predicate written as a NAMED SURVIVOR SET, and its
    UNMUTATED control run reported GREEN on the same control line. This entry state also ruled the
    33 `material` attack rows "battery-design constraints, not S3 defects" IN ADVANCE OF READING
    THEM; checkpoint 1 falsified that whole-class ruling twice (`Y08`, `A10`).
    `m3u5a-battery-validate.py` is BUILT and graded both ways, so S4 opens on dispatch, not on
    tooling. It parses the contract itself - 30 `- **DNN**` bullets from sections 5-10, 8
    `- **A<k> (D..)**` amendments from sections 13-14 - so the seed cannot drift from the spec.
    Derived binding map: A1(D01,D14) A2(D05) A3(D06) A4(D09) A5(D18) A6(D28) A7(D13) A8(D27).
    Control lines: `UNFILLED-TESTS`, `OBLIGATIONS-UNCOVERED`, `ORPHAN-TESTS`, `ASSERTIONLESS`,
    `SKIPPED`, `AMENDMENT-UNCITED`; all zero for PASS. `AMENDMENT-UNCITED` fails a docstring that
    dropped its `AMENDED-BY A<k>` block, which is what keeps an amended obligation from being
    encoded in its superseded form. Graded both ways plus six controls, ALL FIRING: pass-bodies
    -> ASSERTIONLESS 30, `self.skipTest` -> SKIPPED 1, `@unittest.skip` -> SKIPPED 1, extra test
    -> ORPHAN 1, deleted test -> UNCOVERED 1, dropped `AMENDED-BY` -> UNCITED 1.
    The decorator control caught a real hole at seed: `ast.get_source_segment` starts at `def`, so
    `node.decorator_list` must be unparsed and prepended or a `@unittest.skip` reads as an
    ordinary filled body. Write the decorator control into every future AST-based gate.
    DISPATCH RECIPE, and the trap it avoids: the battery is diff-blind, so its worktree branches
    from `c8b82cd`, the last commit before `e6ba873`. Running the validator in a PLAIN `c8b82cd`
    tree ABORTS with `contract holds no amendments; A1-A8 are binding`, because sections 13 and 14
    landed later at `9372664` and `7ad8c53` - that tree has all 30 obligation bullets and zero
    amendment bullets. The abort is load-bearing: emitting there would seed nine obligations in
    their SUPERSEDED form. So build the branch at `c8b82cd`, commit the CURRENT `.agent/decisions/`
    onto it, emit the stub there, commit it, and only then dispatch. `src/`, README and docs stay at
    `c8b82cd`; the contract the teammate is entitled to read stays current. MAIN alone runs the
    battery against the implementation.
    Brief the report as inline final-message content. `tests/test_cli_channels.py` is already green
    in the primary tree and is NOT the battery: it encodes the 60 verdict rows, D01-D30 is a
    different axis, and the battery must be authored without reading it.

    S4 CHECKPOINT 1, `main=` 84% 201K/240K. Shipped at `75f0678` (gate-3 harness + 50-site seed) +
    `8f091fe` (Y08 code fix + A10 gate-4 extension). Gate 1 = 871 tests / 0 failures / OK /
    175.813 s; gate 4 = rc 0 over 19 CHECK lines.
    TWO TEAMMATES LIVE, both worktree-isolated, both seeded by a MAIN-committed both-ways-graded
    validator: `test-m3u5a-3` (`.scratch/worktrees/test-m3u5a-3`, branch at `c8b82cd` + current
    `.agent/decisions/`, marker `TEST-M3U5A-3-DONE-1`) filling the 30-test diff-blind obligation
    battery; `gate-m3u5a-1` (`.scratch/worktrees/gate-m3u5a-1`, branch at `75f0678`, marker
    `GATE-M3U5A-1-DONE-1`) filling the 50-row mutant catalogue and running the PRE-BATTERY baseline
    sweep against `tests.test_cli_channels` alone.
    THE ATTACK TABLE FOUND A REAL CODE DEFECT, which the roadmap's own S4 entry state had ruled out
    in advance: it recorded the 33 `material` rows as "battery-design constraints, not S3 defects",
    and `Y08` is a shipped defect. `os.path.exists` follows the link, so a dangling symlink, a
    missing parent and an embedded NUL all fired D13's precheck at exit 5 where the identical paths
    on a precheck-free leaf answer exit 2 with a precise diagnosis — D12 freezes that map and calls
    it untouched, so two obligations contradicted each other in shipped code. STANDING RULE: a
    severity label assigned by the reviewer is a sorting hint, never a disposition; MAIN re-derives
    every row before recording one, and a whole-severity-class ruling written before the rows are
    read is a claim, not a triage.
    A DIGEST OVER ACTIONS CANNOT SEE A PARSER-LEVEL FLAG. `A10` measured gate 4's `parser_shape`
    blind to `allow_abbrev`, which is exactly the property D25 claims to preserve. The fix is one
    `<node>` line per parser node; 126 -> 163 lines, and the negative control (disable it on
    `proposal review`) moves the digest while the 30/37 census stays put. Generalize: when a pin
    digests a collection, check which attributes live on the CONTAINER and are therefore invisible
    to it.
    S4 CHECKPOINT 2, `main=` 100% 240K/240K at the compaction boundary. Shipped `2b2753a` (contract
    section 15 = A9-A23, plus the validator's amendment-regex fix), `8006764` (`m3u5a-rule-attack.py`
    + all 50 dispositions), `29754f7` (`m3u5a-battery-reamend.py`).
    ALL 50 ATTACK ROWS RULED, census derived from the committed JSON: ACCEPTED-AMENDED 20
    (A01 A03 A04 A07 A08 A11 A12 A17 A20 Y04 Y05 Y06 Y10 Y15 Y16 Y17 Y19 Y20 Y24 Y25),
    ACCEPTED-FIXED 7 (A10 Y01 Y02 Y03 Y08 Y18 Y21), BATTERY-CONSTRAINT 8, DISCHARGED 6, SCOPED 4,
    CLEARED 4, REJECTED 1. `Y08` is the ONLY code defect the table found; the other six fixes
    repaired instruments (gate 4 pins, the `m3u5a-s2-probe.py` unconditional `return 0`) or docs.
    Contract amendments 8 -> 23, amended obligations 9 -> 18 (D01 D05 D06 D09 D12 D13 D14 D15 D16
    D18 D20 D21 D23 D25 D26 D27 D28 D30). `A21`/`A22` bind section 12 and section 3.1/G1 rather than
    a `DNN`, so `AMENDMENT-UNCITED` ignores them by construction.
    THE VALIDATOR'S AMENDMENT REGEX WAS `A\d`, dropping `A10` and every later id in silence — the
    fail-open shape of a forbidden-list grep. `A\d+` now parses all 23. Any gate matching an id
    class must be graded against an id that crosses the digit boundary.
    A DIFF-BLIND AUTHOR OUTLIVES ITS OWN CONTRACT: the battery is written against A1-A8 while the
    contract now carries A1-A23, so nine obligations arrive encoded in superseded form. That
    reconciliation is the designed WORK-UNIT flow, not a re-dispatch, and its MECHANICAL half is
    `m3u5a-battery-reamend.py` — it rebuilds each docstring from the validator's own emitter, edits
    BOTTOM-UP so earlier line numbers stay valid, and leaves every body byte-identical under AST
    comparison. A body that now contradicts its superseding amendment still goes red; that red is
    MAIN's specification question and the script must never be read as answering it.
    HARVEST IS A TARGETED CHECKOUT, NEVER `git merge --squash`. Both branches carry dispatch-time
    snapshots of files MAIN has since advanced: squashing `wt/test-m3u5a-3` (based at `c8b82cd`,
    which predates `e6ba873`) reverts `cli.py`, `system.py`, README, both docs, four `.agent/` files
    and deletes `tests/test_cli_channels.py` outright. Take
    `tests/test_cli_channels_battery.py` from `wt/test-m3u5a-3` and
    `.agent/decisions/m3u5a-mutants.json` from `wt/gate-m3u5a-1`, nothing else.
    S4 DONE, closure session, ran past one compaction boundary. `main=` 100% 240K/240K at the
    boundary and 44% 106K/240K in the post-compaction close window; `mate=` 89% 213K/240K
    (`test-m3u5a-3`; `gate-m3u5a-1` 63% 151K/240K). S4 range `22182e9..8b84ae5`, 10 commits;
    both worktrees removed and both `wt/` branches deleted at their harvested tips (`4005507`,
    `f36104b`).
    ALL FOUR GATES GREEN at `8b84ae5`: 901 tests / 0 failures / OK / 184.548 s; validator PASS with
    all six controls zero; 128 mutants / 127 killed / `SURVIVORS: 1 ['M41']` = the named survivor
    set, CONTROL GREEN, verdict modules `tests.test_cli_channels` +
    `tests.test_cli_channels_battery`; gate 4 rc 0 over 19 CHECK lines.
    THE BATTERY'S CREDENTIAL IS RED-AT-BASELINE / GREEN-AT-HEAD: 30/30 distinct tests red at
    `c8b82cd` in a detached worktree (`PYTHONPATH=<baseline>/src`, import path verified as the
    baseline's `__init__.py`, `resolve` leaf absent) and 30/30 green at HEAD. Five reds split three
    ways. TWO WERE THE REPO'S: `tests/test_submission_battery.py:181` still carried the `strictly
    stronger` claim A8 withdrew as false, and `docs/architecture.md` carried a 26-word and a 37-word
    sentence against the project's own <=25-word rule. Three were the suite's — D15's missing `-h`,
    D23's absence-grep matching `can repeat` because blank-line splitting makes a 33-line bullet
    list one paragraph, and D24's `assertRaisesRegex` around `handle`, structurally blind because
    `System` converts the raising source into a `candidate_source_error` envelope at status 0
    (measured `System.propose` call count 0). D27 also needed A23's `<node>` line mirrored into the
    battery's independent `parser_shape` oracle: 126 -> 163 rows, `89dfa3d982d8c54b` ->
    `8b58b465c08aa693`.
    GATE 3 FAILED ON ITS FIRST DECISIVE RUN, which is this session's most valuable result: 121
    killed / 7 survivors against a named set of 1. All six unexpected survivors were
    behaviour-changing, none equivalent, and all six were ONE blindness in three shapes — an
    assertion is bounded by the surface it RENDERS and by the discriminator it USES. D30 scanned
    the leaf parser, where an `add_parser(help=...)` string can never appear; D09 pinned null-ness,
    which cannot separate two non-null fields; D15 covered the binary branch of a two-branch reader
    and fixtured it entirely in ASCII. Fixes and per-mutant credit in `8b84ae5`, generalisation in
    `.agent/memory.md`.
    DIFF-BLINDNESS AUDIT of `test-m3u5a-3`: zero references to the primary tree's `src/`, `tests/`,
    `docs/`, `README` and zero `git show main:` / `git diff main`, under a positive control that
    lists its own worktree paths. It read that worktree's `c8b82cd` baseline 13 times, which the
    contract's git-object pins REQUIRE, so the role is diff-blind on two counts that must be audited
    separately; `/session-roadmap`'s `test` role now states the boundary and MAIN's baseline-run
    credential explicitly.
    M41 IS ALREADY A RULED SURVIVOR AND ITS RULING PRE-DATES THE SWEEP, which is `Y12`'s own demand:
    `FunctionMatch.matched` is `bool` and the CLI binds `None if match is None else match.matched`,
    so identity and truthiness agree over the whole `{True, False, None}` domain. `6` -> `7` on the
    same line is killed by six tests, which is the harness's positive control.
  - M3.5b DONE tier=kernel tags=- depends=M3.5a - remove `handle`/`request`/source grammar, imports, fixtures,
    help and operator prose. THREE sessions, not four: S1 contract, S2 implementation, S3 battery +
    closure.
    S1 DONE, contract session, `main=` 80% 191K/240K at close. NO teammate dispatched. Shipped
    `.agent/decisions/m3u5b-contract.md` (11 sections, 29 obligations D01-D29 gapless, sections 10-11
    PENDING), `m3u5b-burden.py` + `m3u5b-burden.json`.
    NO WAVE 1, and the grounds are the roadmap's own M3.5a sizing correction: budget FOUR sessions for a
    unit that OPENS a spike wave regardless of tag, and budget a unit with NO fork to rule WITHOUT S1 and
    S2. M3.5b has no material design fork - the pin shapes already ship, the removal mechanics are settled
    by prior units, and every open quantity was directly measurable. The prose corpus is 1,080 lines with
    56 vocabulary-hit lines, and the last two `map` dispatches returned rows MAIN had to re-derive before
    acting (6 of 55 on M3.5a). Teammate budget moves to wave 2. MAIN spent ~110K deriving ground state and
    reached a complete contract in one window against M3.5a's S1+S2 pair.
    BURDEN MEASURED, never counted: `m3u5b-burden.py` stages the source-only deletion in throwaway
    worktrees with per-edit occurrence assertions and groups every failure by its deepest `tests/` frame.
    Stage 1 (grammar) = 113 broken / 901, 11 frames. Stage 2 (+ `_source`, construction, both dispatch
    branches, the import) = 119 broken, 17 frames. 103 of stage 1's 113 stand behind ONE frame,
    `tests/test_cli.py:193 in payload`, fed by three fixture helpers - `confirm` (:217), `handle_once`
    (:247), `confirm_text` (:2954) - that seed state through the `handle` CLI route. The work list is 17
    frames. M3.4's 28x lesson reproduces exactly, and the plan draft's "three shared CLI fixture helpers
    shield 102 callers" is one of the few draft predicates that survives re-derivation at HEAD: measured 103.
    THE CENSUS COLLIDES AND THE DIGEST DISCRIMINATES, which is S1's sharpest find and it changes a gate
    design. Post-M3.5b is 28 leaves / 35 nodes - numerically EQUAL to pre-M3.5a `c8b82cd` over the exact
    INVERSE set. A leaf/node count pin cannot distinguish "M3.5a and M3.5b both landed" from "neither
    landed". `parser_shape` does separate them (154 `af19339c3995c97d` at `c8b82cd`, 151
    `ebd2ac811bd9776d` after), so census and digest are NOT redundant: the census names which leaf moved,
    the digest is the only one of the pair that notices the state at all. Every census obligation asserts
    the leaf-name SET.
    A ROADMAP NUMBER WAS CARRIED INTO THE CONTRACT AS A MEASUREMENT AND WAS WRONG. The recorded
    `126` / `89dfa3d982d8c54b` is the PRE-A23 algorithm over the POST-M3.5a parser; MAIN wrote it into the
    ground-state table as the pre-M3.5a baseline, then measured `c8b82cd` under the current probe and got
    154 / `af19339c3995c97d`. Two axes, not one. A digest is only comparable against its own algorithm -
    state the algorithm beside every recorded digest, exactly as P06's slicing-convention table does.
    GATE 4 RE-BASE MEASURED, five failing checks against the stage-2 tree: `parser_census.leaves` 30->28,
    `.nodes` 37->35, `parser_shape.actions` 163->151, `.digest` `8b58b465c08aa693`->`ebd2ac811bd9776d`,
    and `parser_census.lost_baseline_leaves` `[]`->`['handle','request']`. `BASELINE_LEAVES` KEEPS both
    members: the frozenset records `c8b82cd` history and does not move; the EXPECTATION moves from
    "nothing is lost" to "exactly these two are lost". Every tripwire this session predicted fired by
    name, which is what a measured burden buys over a map dispatch.
    TWO PINS INVERT RATHER THAN MOVE, the class M3.4 named. `x26` asserts `CommandCandidateSource` REMAINS
    imported; `d24` spies `cli._source` through `mock.patch.object`, which RAISES rather than fails once
    the symbol is deleted. A pin left asserting the pre-removal property tests nothing afterwards, and a
    spy on a deleted symbol is an error, not a verdict.
    ARGPARSE MEASURED, and flag removal has two distinct pin shapes. Subcommand names are EXACT-MATCH at
    both levels, so a removed LEAF raises `_UsageError` `invalid choice` whose message ENUMERATES the
    survivors - a complement assertion for free. A removed FLAG on a surviving leaf reports `unrecognized
    arguments`. Legacy leaves still abbreviate (`compile --act` -> `--actor`, and `handle --request` ->
    `--request-id` today), so removal is NOT pinnable as absence: D10 requires every removed spelling AND
    every proper prefix to be refused, derived over `_parser()`.
    THE PROSE SPLITS BY ROUTE AND BOTH ERROR DIRECTIONS ARE DEFECTS (D22). CLI-route prose names commands
    that cease to exist and must change; library-API prose names `System.handle`, which survives until
    M3.6a, and must NOT change here. `examples/hospital_ocr/run_demo.py` and its README drive the LIBRARY
    method, so the demo is untouched by this unit. Deleting library prose would pre-empt M3.6a's own doc
    pass and break the track order.
    S2 DONE, implementation + wave 2, `main=` 96% 231K/240K, `mate=` 86% 206K/240K (`test-m3u5b-1`).
    Commits `4e33cc6`..`4a01693`. Gates rerun from the committed tip `4a01693`, tree otherwise clean:
    suite 901 OK, gate 4 rc 0 (19 checks), gate 5 rc 0, `uv build` rc 0, both ruling patchers
    `--check` rc 0.
    THE REMOVAL WENT THROUGH THE ANCHORED TABLE, never by hand: `apply_stage(pathlib.Path('.'), 2)` over
    `m3u5b-burden.py`'s 7 occurrence-asserted `EDITS`, `cli.py` -44/+1. Census and digest hit S1's
    predictions exactly - 28 leaves / 35 nodes / 151 actions / `ebd2ac811bd9776d`, with 151 derived as
    116 action lines + 35 node lines rather than added. Gate 4's five predicted checks failed with the
    predicted values and no others.
    WAVE 2 CONFIRMED THE CENSUS COLLISION INDEPENDENTLY AND DIFF-BLIND: `c8b82cd` re-derives to 28/35
    with INVERSE two-leaf sets and `154`/`af19339c3995c97d`. S1's sharpest find survives an adversary.
    EIGHT CLAIM DEFECTS IN MAIN'S OWN CONTRACT, ninth consecutive unit on this pattern, all corrected in
    contract section 10: D17's 16-vs-19 checks; D03/D18's three cardinalities (prose 11, table 18 rows,
    measured 17) for one work list; D18's 103-vs-102 shielded assertions - re-basing the three helpers
    leaves ONE of the 103 still failing at `payload`, so 105 = 102 + 3; D22's `remove` on a table
    documenting live library methods; D14's false claim that the digest carries choices, types and help;
    D14's wrong cross-reference to D16; D28's false claim that M3.6a and M3.7 are scheduled to edit
    `cli.py`, which MAIN verified against THIS FILE; and S9's zero-fork claim against five real forks.
    THE FRAME CENSUS HAD A CATEGORY IT NEVER SCANNED. 17 code-coupled frames is right; an EIGHTEENTH,
    PROSE-coupled frame broke on the D22 edit alone (`test_cli_channels_battery.py` `test_d23_...`, whose
    final `assertIn` is A11's positive control). A burden staged over SOURCE deletions cannot see a frame
    that pins shipped prose. Binding on every later removal unit: stage the prose edit too, or scan for
    doc-string pins separately.
    POSITIVE CONTROLS RELOCATE, NEVER DELETE. Twice this session: `d24`'s CLI witness that a configured
    source IS reachable moved onto `System.handle`, and A11's README retry advice moved onto the library
    spelling. A control deleted rather than relocated turns an isolation pin into a tautology.
    GATE 3 AS SPECIFIED WAS VACUOUS - it mutates touched predicates read from the final tree, and the
    seven EDITS delete five predicates and add none, so the set is EMPTY. Contract section 11 redefines
    it as REINSERTION mutants. Binding on every later removal unit: a removal is bound by restoring what
    was removed, never by mutating what remains.
    GATE 5 IS NEW AND CREDITED BY MUTATION: `m3u5b-doc-parse.py` parses every `cement` invocation in
    fenced shell blocks of README, `docs/*.md` and `examples/*/README.md` under `_parser()` - 5 surfaces,
    18 invocations, 0 failures - behind an invocation floor, two must-fail removed-leaf controls and one
    must-parse surviving control. Injecting a stale `handle` line turns it red at the exact locus.
    ONE POLISH ROW DISCHARGED (`cli.py`'s bare `65_536` left with `_source`; measured 0 remaining), one
    ownership CORRECTED (global `allow_abbrev` DECLINED - a repo-wide grammar break needs its own
    mandate; D06/D10 close the removal half locally), two OPENED (the digest instruments no help,
    `choices` or `type`; no shipped prose names `example_adapter`).
    S3 ENTRY STATE: contract sections 1-9 bind EXCEPT where section 10 corrects them; section 11 is the
    gate specification and REPLACES section 8's. Build gate 2 (one test per D01-D28 plus one independent
    RED control per obligation, per-direction controls on compound D15/D18/D22, a runtime
    candidate-source assertion, a self-grading D20 narrative) and gate 3 (reinsertion mutants, NAMED
    survivor set). Every gate reruns from the committed tip with its SHA recorded. The verdict table's
    `action` column carries the encode instruction per row; `GATE-SPEC` rows bind construction, not
    assertions.
    S3 CHECKPOINT 1, `main=` 85% 204K/240K. Shipped `6598e54` (validator + harness + 48-row seed) +
    `69ce360` (witness fix). Gates rerun from tip `69ce360`, tree clean: gate 1 = 901 tests / OK /
    74.832 s · gate 4 = rc 0 over 19 CHECK · gate 5 = rc 0 over 6 CHECK.
    ONE CATALOGUE SERVES BOTH RESPECIFIED GATES. Section 11 demands a per-obligation RED control (gate 2)
    and a reinsertion sweep (gate 3); those are the same instrument read two ways, so
    `m3u5b-mutants.json` carries one row per battery clause tagged `reinsertion` or `sensitivity` and
    `m3u5b-mutants.py` runs both. It isolates in a `git worktree`, which closes the standing defect that
    a sweep contaminates `git status` for its whole run and strands a live mutant when killed.
    KILLED IS NOW ATTRIBUTED, NOT COUNTED. The harness separates `killed` (the row's OWN `target_test`
    went red) from `misdirected` (the run went red without it). A control that reddens some other test
    certifies nothing about the obligation it was aimed at, and a plain kill count cannot see the
    difference. `MISDIRECTED` and `PATCH-NOOP` both fail the gate.
    48 CLAUSES, NOT 28 OBLIGATIONS. X39 rules D15/D18/D22 compound, and the validator DERIVES their
    clause sets from the contract's own text rather than a hand list: D15 by the section 10 correction's
    6-runtime/12-example split, D18 one clause per row of its own table (18), D22 one per DIRECTION plus
    the protected ` ```text ` fence. `CORRECTION-UNCITED` is the `AMENDMENT-UNCITED` analog and guards
    the same defect - section 10 OVERRIDES the bullet above it, so a body encoding the literal bullet
    goes red against correct code. It fires on all eight corrected obligations (D03 D14 D15 D17 D18 D22
    D27 D28).
    THE SEED CREDENTIAL IS NOW MECHANICAL. `--self-test` grades both ways from committed state: filled
    pair PASS rc 0, and 11 negative controls ALL FIRING. M3.5a graded its validator by hand and recorded
    the result in prose, which cannot rerun from a clean checkout; this one can.
    D04'S PROCEDURAL CREDENTIAL IS DISCHARGED, and section 11 called it unverifiable. Replaying
    `apply_stage(pathlib.Path('.'), 2)` over the committed `EDITS` in a detached `36f7890` worktree
    reproduces the shipped `cli.py` to EXACTLY TWO diff hunks / 9 lines - the two help-string edits the
    section 10 "explicit capture help" fork ruled TAKEN and recorded as outside the seven `EDITS`. So the
    limit as written is too strong: the staged apply is not distinguishable from a direct edit, but the
    replay DOES bound the manual surface to the ruled exceptions, and a third unrecorded edit would show
    as a third hunk.
    Teammates: `test-m3u5b-2` (`.scratch/worktrees/test-m3u5b-2`, branch at `4e33cc6` + current
    `.agent/decisions/` + the seeded stub, marker `TEST-M3U5B-2-DONE-1`) filling the 48-clause diff-blind
    battery; `gate-m3u5b-1` (`.scratch/worktrees/gate-m3u5b-1`, branch at `69ce360`, marker
    `GATE-M3U5B-1-DONE-1`) filling the 48-row catalogue and running the PRE-BATTERY baseline sweep.
    THE BATTERY STUB STAYS OFF `main`. 48 `self.fail` bodies in `tests/` would turn gate 1 red, so the
    seed lives on the teammate's branch alone; only the catalogue seed, which is evidence rather than a
    test, is committed here.
    S3 CHECKPOINT 2, `main=` 92% 220K/240K at the compaction boundary. Battery HARVESTED by targeted
    checkout at `wt/test-m3u5b-2` tip `644962b`; `git diff --name-status main..wt/test-m3u5b-2` renders
    EIGHT of main's later files as modified (`cli.py`, README, four test files, roadmap, polish), so
    squash-merge would have reverted the whole removal - the standing rule reproduced exactly. One added
    file taken, nothing else.
    Battery grades CLEAN on all six of its own counters at 48 tests / 28 obligations: UNFILLED 0,
    UNCOVERED 0, ORPHAN 0, ASSERTIONLESS 0, SKIPPED 0, CORRECTION-UNCITED 0.
    FIRST CONTACT AT HEAD: 38/48 green, 10 red, 3.190 s. Every red is UNRULED and is checkpoint 3's entry
    work. FOUR (`D18f` x04, `D18h` x21, `D18k` v05, `D18m` d03) share one shape whose LIKELY reading is a
    SUITE defect: each asserts the token `_source` is ABSENT from a re-based frame, while D19 re-shaped
    those frames to assert the post-removal property DIRECTLY, which requires naming the deleted symbol
    to deny it. A token-absence check cannot separate an assertion that USES a symbol from one that
    FORBIDS it - the fail-open shape of a forbidden-list grep, arriving inside the instrument built to
    catch it. RULED, verified against the shipped frames: all four are SUITE DEFECTS and the frames are
    CORRECT. `test_cli_channels.py:447` and `:1651` carry `self.assertFalse(hasattr(cement_cli,
    "_source"))`, and the counter dicts bind `"_source": hasattr(cement_cli, "_source")` against an
    expected `False` - the token is present BECAUSE the frame denies the symbol, which is precisely D19's
    inversion. The battery must assert the RUNTIME absence the frame proves, never the absence of the
    token from its source text.
    The other six: `D18g` x11 expects a `node.name == '_source'` clause the frame does not use; `D18i`
    x22 expects the integer 26 where the frame carries 28 twice; `D18p` d25 expects the (28, 35) census
    pair at least twice; `D18q` d26 fails a compound predicate; `D22a` finds `provenance` in the
    CLI-route locus set it did not expect; `D25` is the register pass section 11 already records as
    having NO committed grader.
    `test-m3u5b-2` reached 48/48 and committed at 100% of its window after ONE flush directive naming the
    exact six remaining clauses and the exact report shape; it never emitted its marker, so its red/green
    split must be RE-DERIVED by MAIN rather than read. `gate-m3u5b-1` is LIVE at 64% with all 48 controls
    filled and its baseline sweep running; its last text reports M46 replaced after the survivor probe
    exposed it as invalid - it removed `capture` but left `submit`, so D26 still held. A teammate
    catching its own dead control is the catalogue working.
    S3 DONE, battery + closure session, ran past two compaction boundaries. `main=` 86% 206K/240K at
    close; `mate=` 100% 240K/240K (`test-m3u5b-2`, which reached its window filling 48/48).
    ALL FIVE GATES GREEN FROM COMMITTED TIP `5857d88`. Gate 1: 949 tests / OK / 80.422 s, rc 0 (901 at
    `69ce360` plus the battery's 48). Gate 2: validator rc 0 PASS, all NINE counters 0, self-test 11/11
    negative controls firing. Gate 3 + gate 2's red control, one sweep: 48 KILLED, 0 MISDIRECTED, 0
    SURVIVORS, 0 PATCH-NOOP, control GREEN, rc 0. Gate 4: rc 0 over 19 CHECK. Gate 5: rc 0 over 6 CHECK.
    ALL TEN REDS WERE SUITE DEFECTS; ZERO code defects, zero repo defects. The four `_source` reds ruled
    at checkpoint 2 plus six more, every one the same class: a diff-blind author pinning code it could
    not read. Four of the ten live frames express their property MORE strongly than the pin demanded - a
    set-difference census where the pin wanted a literal `(28, 35)` pair, one subTest loop where it
    wanted two unrolled copies, an `_ExplodingSource` where it wanted empty-kwargs equality, the one
    keyword the obligation names where it wanted `kwargs == {}`. D22a additionally demanded all three
    submission keys in the quick start, where `provenance` is optional; D25 counted a README table CELL
    as one sentence and reported a compliant 17+15-word pair as one 32-word violation.
    THE CATALOGUE ARRIVED MEASURED, NOT REPAIRED. Its own `note` fields recorded `baseline=misdirected`
    and `baseline=survived` on the three rows that were broken, and it still graded CLEAN on every
    structural counter, because notes are free text. Preview sweep at `88703e8`: 31 killed, 15
    misdirected, 2 survivors. 13 misdirected were one defect - a D18 clause test is a STATIC check on
    another frame's source, so a `cli.py` mutation cannot redden it; the target is the FRAME, which the
    contract's own D18 table names. Repairs land as `m3u5b-mutants-repair.py`, replayable: 19 changes,
    then `--check` CLEAN. M06 aimed at D06 and exercised D10 (a reinserted spelling satisfies the
    abbreviation property); M31 reinserted code guarded by `args.command == "handle"` after `handle`
    stopped parsing, so the branch was dead and D03 genuinely still held.
    BOTH SURVIVORS WERE REAL BATTERY GAPS, both closed. M04 weakened the burden script's `found !=
    expected` to `<`; D04 only drove the missing-anchor direction, where both forms abort, so D04 now
    also asserts a DUPLICATED anchor aborts with `found 2`. M45 seeded a 25-word four-clause instruction
    that survived on one missing word: D25's hand-written `imperatives` list omitted `generate`, so every
    unlisted verb fell through to the looser 25-word description bound. D25 is now FAIL-CLOSED on an
    unclassified opener, which immediately caught `supervised` (the parser root description, invisible to
    a paragraph scan) and forced the ruling that sentence-initial `Set` here is always the noun phrase.
    The validator resolved control coverage back THROUGH the target, inheriting the same blind spot and
    reporting the contract's own D18 frames as 14 orphans; a row now covers the clause it DECLARES once
    its target names a test in any verdict module.
    Teammates STOPPED, worktrees and `wt/` branches removed, both worktrees `status --porcelain` EMPTY at
    removal. `cbfaf17` on `wt/test-m3u5b-2` was unharvested Ruff work that main never carried (the battery
    came from `644962b`); replayed directly rather than merged, since that branch renders the battery
    DELETED. Ruff rc 0 over the battery and all three instruments.
    NOT EVERY OBLIGATION CAN BE RED AT BASELINE, and demanding it would corrupt the battery. M3.5a's
    30/30 red worked because every obligation described a NEW leaf; M3.5b's D12-D16, D21, D27 and D28 are
    PRESERVATION obligations that legitimately hold at `4e33cc6`. That is exactly why section 11 requires
    an independent red control per obligation: the catalogue generalises the baseline-red credential to
    obligations no baseline can redden. Report the split; never force it.
  - M3.6a SPLIT INTO M3.6a1 + M3.6a2 + M3.6a3 at its own pre-open measurement, which is the calibration
    ruling's standing instruction for this unit. `main=` 88% 212K/240K for the split session; NO teammate
    dispatched, since a pre-open split is measurement plus arbitration and both are MAIN-retained. The
    entry cost is the thing to cut: attached state plus the ground-state read spent ~150K before the
    first gate stage ran, so a session that must also write a contract needs the split ruled first.
    Burden measured, never counted: `m3u6a-burden.py` +
    `m3u6a-burden.json` stage the source-only deletion in throwaway worktrees with per-edit occurrence
    assertions and group every gate failure by its deepest `tests/` frame.
    STAGE 1, the method deletion alone = 296 broken / 943 ran / 46 frame keys. The deletion closure is
    exact: over `System`'s own call graph, `_request_revision_is_current` (11) is the ONLY private helper
    dead with the seed, so the span is `handle` 271 + `_outcome` 116 + `_fail_generation` 32 +
    `request_status` 14 + 11 = 444 lines. 251 of the 296 stand behind FOUR fixture helpers
    (`test_system.py` `_confirm_scope` 189 and `confirm` 28, `test_resolve_battery.py` `_confirm` 23,
    `test_proposal_binding_battery.py` `_promoted_conflict_fixture` 11) and 2 more behind
    `test_hospital_ocr_example.py` `_promoted_example_ledger`. M3.4's 28x lesson reproduces at 60x.
    STAGE 5 READS LOWER THAN STAGE 1 - 57 broken / 601 ran against 296 / 943 - and the drop is a
    MEASUREMENT ARTIFACT, not relief: deleting the five result models breaks three modules at IMPORT
    (`test_system`, `test_resolve_battery`, `test_hospital_ocr_example`), so 342 tests never run and their
    failures are hidden. Stage 6 repairs the two test-module import lists alone, leaving the demo broken
    because the demo is implementation work rather than an import repair, and measures 314 broken / 921
    ran / 52 frame keys. STANDING RULE: a cumulative removal stage that reports FEWER breaks than its own
    predecessor has hidden a module, so print `Ran N` beside every break count and diff the collection.
    LAYER ATTRIBUTION, by frame key across the two stages: the method deletion owns 46 frames; the lease
    knob, revision cancellation, result models and `CandidateRequest.request_id` own 10 between them.
    Against M3.5b's measured 17 frames for a three-session unit, an unsplit M3.6a is 3.2x - and it also
    carries a 7-site demo rewrite plus transcript regeneration and a five-document prose pass that M3.5b
    did not have, because M3.5b D22 deliberately left every `System.handle` sentence to this unit.
    THE SPLIT AXIS IS CONSUMER-MIGRATION-BEFORE-DELETION, and it works because both APIs exist TODAY.
    All four `handle`-driven fixture helpers share one shape - `handle` -> `assert isinstance(...,
    ReviewRequired)` -> `get_proposal` -> `review` - whose `propose` + `get_proposal` + `review`
    replacement reaches the identical final row state, so the re-base lands GREEN with `handle` still
    shipped and removes 253 of the deletion unit's breaks before it opens.
    ROADMAP CORRECTION: M3.7's `depends` gains M3.6a3, which deletes `CandidateRequest.request_id`. The
    prior line had M3.7 running alongside M3.6 on `depends=M3.3,M3.5b` while M3.7's own retained protocol
    names that field, which the M3 track order already flagged and no dependency edge recorded.
  - M3.6a1 tier=kernel tags=- depends=M3.5b - migrate every consumer off the lifecycle API while it still
    ships. Re-base the four `handle`-driven fixture helpers plus `test_hospital_ocr_example.py`
    `_promoted_example_ledger` onto `propose`/`get_proposal`/`review` through scripted, count-asserted,
    idempotent surgery; drop the now-dead `request_id` argument from ~217 helper call sites in the same
    script. Rewrite `examples/hospital_ocr/run_demo.py`'s seven `system.handle` sites onto `propose` and
    `resolve`, and regenerate the README transcript, whose lines 208 and 216 name the vanishing
    `request.resolved_by_artifact` event. Acceptance: gate green with `handle` and `request_status` still
    shipped, plus a census proving the only surviving consumers are the lifecycle-pinning tests M3.6a2
    deletes and the library itself.
    THREE sessions: S1 measurement + rulings, S2 contract + implementation, S3 battery + closure. NO
    wave 1 - the M3.5a sizing correction budgets a unit with no fork to rule WITHOUT S1's spike wave, and
    every open quantity here was directly measurable.
    S1 DONE, measurement + rulings session, `main=` 90% 216K/240K at close. NO teammate dispatched;
    measurement plus arbitration is MAIN-retained. Shipped `m3u6a1-premise.py`, `m3u6a1-census.py`,
    `m3u6a1-census.json`, `m3u6a1-rule-census.py`. No shipped code touched, so the gate is unmoved at
    `1146421`'s 949 tests and was not rerun.
    BOTH PLAN-LINE PREMISES FALSIFIED AS WRITTEN, each by its own probe rather than by reading.
    P1 - `propose` reaches the identical row state as `handle` across `requests`, `proposals`, `events`,
    `examples`, `artifacts` and `operations` EXCEPT ONE CELL: the `proposal.created` event's
    `payload_json`, where `handle` writes `{"request_id": "<caller id>"}` and `propose` writes `{}`. That
    single cell is the migration's whole behavioural signature, and two tests pin it (`test_d03...`,
    `test_b30...`), both consequently ruled RETAIN.
    P2 - `resolve` CANNOT replace `handle`'s artifact-hit branch at the demo's Act-2 ledger state: it
    fails check `persisted-function-receipt`, because the walkthrough promotes its function set only in
    Act 5. It matches once the set is promoted. OWNER RULED: checkpoint the set right after each artifact
    promotion so Acts 2 and 3 answer through `resolve`; Act 5 keeps export and identity but loses its
    "becomes one exportable function" framing. The demo then teaches M3's actual post-trim lifecycle -
    propose, review, compile, verify, promote artifact, promote set, resolve.
    THE SAME-ROUTE CONTROL IS WHAT MADE P1 HONEST, AND ITS FIRST FORM FAILED OPEN. Run without a control,
    P1 reported four differences, all of them fresh identifiers feeding persisted digests. Run with a
    control that aggregated volatility PER COLUMN across all rows, it reported zero - one event row's
    volatile subject id certified the whole `payload_json` column, masking the only real difference.
    Attribution had to go per ROW and per column. A control is an instrument and inherits the fail-open
    shapes of any other.
    THE SCOPE GAP IS THE SIZING FINDING. The plan line names five fixture helpers; the acceptance
    predicate quantifies over EVERY consumer, measured at 49 definitions / 79 sites. Ruled 27 MIGRATE +
    1 MIGRATE-RESOLVE + 21 RETAIN with 3 overrides, so the work list is 28 definitions, not 5 - against
    M3.5b's 17 frames for a three-session unit. Sizing holds at three sessions because 24 of the 28 are
    single-site fixture routes the surgery script rewrites uniformly.
    `request_id` CLASSIFIES NOTHING, which the first classifier learned the expensive way: every `handle`
    call passes it, so a rule keying on that token returned 78 RETAIN of 79 sites. The decidable
    discriminator is what the enclosing definition does with the call's RETURN VALUE - discarded, or read
    only as `isinstance(x, ReviewRequired)` plus `x.proposal_id`, is migratable because `propose` returns
    that identifier directly.
    TWO FAIL-OPEN CLASSIFIER DEFECTS FOUND AND FIXED, both the same family. `assertIs(type(x), T)` states
    the identical obligation as `assertIsInstance(x, T)` and was invisible to an `assertIsInstance`-only
    rule - it hid `test_b04`, which asserts `Resolved`. `typing.cast(T, x).attr` reads the result exactly
    as `x.attr` does and was invisible to a bare-Name attribute rule. Both ship in this repo.
    THE MECHANICAL RULE READS CONSUMPTION, NEVER INTENT, so three rows carry MAIN's override with its
    grounds in `m3u6a1-census.json`: the demo (RETAIN -> MIGRATE-RESOLVE, the second migration target the
    rule cannot name), `test_handle_still_answers_on_a_system_that_submitted_directly` (MIGRATE -> RETAIN,
    the method under test IS `handle`), and `test_b30...` (MIGRATE -> RETAIN, it pins the one payload P1
    measured as changing). `m3u6a1-rule-census.py --check` is the in-sync gate and asserts the override
    set exactly, so a later row addition fails loudly rather than going unruled.
    THE CENSUS IS RED AT BASELINE BY CONSTRUCTION: `SURVIVING-MIGRATE: 28`, with UNRULED, STALE,
    MEASURE-DRIFT, UNGROUNDED-OVERRIDE and BAD-VERDICT all 0. `--self-test` grades both ways from
    committed state with four controls, ALL FIRING. Its first control compared a ruled table against a
    bare measurement - two different shapes - and failed for a reason unrelated to the property; the
    property that matters is that emit is IDEMPOTENT over its own output, so a recorded ruling survives
    regeneration byte for byte.
    S2 DONE, shape-attribution + contract session, `main=` 91% 217K/240K at close. NO teammate
    dispatched; shape arbitration plus contract authoring is MAIN-retained work, the same shape as
    M3.4 S4 and M3.5a S2. Shipped `4db71a9` (`m3u6a1-fallback.py` + `m3u6a1-fallback.json` + two
    re-rulings) + `77a3da0` (`.agent/decisions/m3u6a1-contract.md`, 11 written sections, 29
    obligations D01-D28 plus D14a, sections 12-13 PENDING). No shipped code touched, so the gate is
    unmoved at `1146421`'s 949 tests and was not rerun.
    RE-SIZED TO FOUR SESSIONS, not the plan line's three, under the calibration ruling's route 2 -
    read the gauge at contract close and open implementation only if it fits. S3 = implementation,
    S4 = battery + closure. The plan budgeted three because it read the migration as mechanical; S2
    measured a semantic fork the census could not see.
    THE CENSUS RULE IS BLIND TO SIDE EFFECTS, which is the session's whole finding. It classifies a
    consumer by what the enclosing definition does with the call's RETURN VALUE, so it read one
    population where three exist. `m3u6a1-fallback.py` attributes all 72 test-tree sites by what the
    `handle` call actually CLAIMS: ACTOR 2, MISS-GUARDED 4, HIT 9, FACTORY 51, UNOBSERVED 6.
    TWO SITES ARE NOT MIGRATABLE AND WERE RE-RULED MIGRATE -> RETAIN with grounds
    (`test_system.py:1044`, `:2698`): the same-input artifact is `promoted` before the call and
    `suspended` after it, so the call PERFORMS the dispatch-time integrity quarantine the test
    asserts. `propose` never consults an artifact and `resolve` is read-only, reporting `passed=False`
    at both, so no post-trim method reproduces the transition. Census overrides 3 -> 5, ruled_migrate
    27 -> 25, SURVIVING-MIGRATE 28 -> 26.
    FOUR SITES CARRY A CLAIM `propose` CANNOT EXPRESS (`test_system.py` 541, 608, 827, 867): every
    execution sees a once-promoted artifact for that exact input which still declines to answer,
    `suspended` or `retired`. Migrating them to a bare `propose` would delete a preserved invariant
    while the gate stayed green - the exact failure this project's removal standard names. `resolve`
    measures `passed=True match=False` at all four, so D06-D08 pin the verified-miss assertion in the
    surviving vocabulary and D07 KEEPS the `propose` call even where its id is unused, because P1's
    equivalence is a claim about ROW STATE.
    BOTH SHAPE QUALIFIERS WERE DERIVED, NEVER ASSUMED, and each one moved the answer. `handle` looks
    up `status = 'promoted'` alone, so a `draft`/`verified` artifact is invisible to it; and a claim a
    SITE makes must hold at EVERY execution of that site, which drops the two shared fixture helpers
    (15 of 1273 and 2 of 78 once-promoted hits) back to FACTORY. Adding the outcome class then split
    HIT from MISS-GUARDED - without it, nine sites where `handle` ANSWERED from the artifact would
    have been prescribed a verified-miss assertion.
    THREE PROBE DEFECTS, EACH PRINTING LIKE A CLEAN RESULT. The digest was derived as
    `_digest_strings("cement-input-v1", ...)` instead of `canonicalize(v).digest`, so all 30 sites
    reported FACTORY - the grader now FAILS on a uniform verdict, and a per-call positive control
    re-derives the digest from the input the ledger stored for the proposal just created (1853
    checked, 0 failed, 0 unreadable). The record was appended AFTER `_real_handle`, so every
    deliberately-raising call lost its row: 4 sites observed of 30. And targeting MIGRATE alone would
    have erased the ACTOR rows the moment their ruling landed, taking the ruling's own evidence with
    it, so every test-tree consumer is a target whatever its verdict.
    TWO CONTRACT GROUND-STATE FACTS WERE WRONG IN THE FIRST DRAFT and were corrected by measuring
    rather than reading: `_promote_scope` has 14 call sites, not 15, and `confirm` is defined at :226.
    The second measurement found a hazard no map would have surfaced - `tests/test_system.py` holds
    TWO definitions named `confirm`, the method at :226 called as `self.confirm(...)` 41 times and a
    nested function at :14452 shadowing it with a different signature and its own lifecycle site at
    :14461. D14a forbids a bare `confirm(` anchor, which spans both.
    ALL THREE ROADMAP-FLAGGED TRIPWIRES ARE NUMBERED: the two `{"request_id": ...}` payload pins at
    D24, `_promote_scope`'s dead `prefix` RULED REMOVE at D12 + D14, the transcript mask counts at
    D22. Contract section 5 adds M3.3's P06 byte-span freeze with its three slicing conventions
    (D25), M3.5b's D01 still-ships pin (D26) and D15a's six-module freeze (D27). B02 and gate 4 are
    NOT tripwires here because the unit edits no production source - asserted by rerunning them.
    F1 CARRIED TO THE OWNER, contract section 8: M3 loses dispatch-time quarantine, not quarantine.
    `handle` owns two suspension writers (`system.py:1135` duplicate-promoted, `:1166` integrity
    failure) that M3.6a2 deletes; `verify`, `review`, `challenge`, `revoke_example` and
    `suspend_artifact` keep independent ones. Coherent with the trim - after it there is no dispatch
    and `resolve` is a pure read - and recorded so M3.6a2 states it deliberately.
    S3 ENTRY STATE: contract sections 1-11 are binding; open with the surgery script, not with hand
    edits. Land the migration through ONE idempotent, count-asserted `m3u6a1-surgery.py` (D15-D17),
    rewrite the demo's seven sites onto `propose`/`resolve` with the set checkpoint moved after each
    artifact promotion (D18-D21), regenerate the example README transcript (D22-D23), and take gates
    1-8 green from committed state. The census is the acceptance gate and must reach
    `SURVIVING-MIGRATE: 0`; it is RED at baseline by construction at 26.
    S3 DONE, implementation session, `main=` 83% 200K/240K at close. NO teammate dispatched. Shipped
    `8592c34` (surgery script) + `4e72692` (the whole migration). Every consumer is off
    `handle`/`request_status` while both still ship, so M3.6a2 opens against a consumer-free tree.
    GATES 1-8 GREEN FROM COMMITTED STATE at `4e72692`, tree clean: 1 = 949 tests / OK / 68.842 s ·
    2 = `SURVIVING-MIGRATE 0` with UNRULED/STALE/MEASURE-DRIFT/UNGROUNDED-OVERRIDE/BAD-VERDICT all 0,
    RESULT PASS, {definitions 23, overrides 4, ruled_retain 23, sites 45}, `--self-test` PASS with
    all four controls firing · 3 = `IN-SYNC` · 4 = RESULT PASS, control 24 checked / 0 failed,
    TARGETS 45, ACTOR 2, MISS-GUARDED 0, HIT 9, FACTORY 28, UNOBSERVED 6 · 5 = P1 and P2 both
    reproduce · 6 = run 2 `no-op` · 7 = 19 CHECK PASS, `parser_shape` 151 / `ebd2ac811bd9776d` ·
    8 = rc 0 over 6 CHECK. Ruff is NOT a gate here (memory: the suite is the sole configured one).
    MISS-GUARDED 4 -> 0 IS THE MIGRATION'S OWN CREDENTIAL: the four sites D06-D08 named are exactly
    the four that moved onto `resolve`, and no other shape moved. ACTOR 2 and HIT 9 are unchanged,
    which is what a correct migration of the FACTORY population looks like from the shape axis.
    THE FIVE REDS WERE ONE AXIS THE CENSUS CANNOT REACH, and the fix is per-consumer, not per-rule.
    D03 pins RETAIN on the definition's OWN lifecycle call and says nothing about its FIXTURES, so
    migrating `confirm` changed what it PLANTS and three RETAIN tests broke with their own calls
    untouched. Two recover the row through `(SELECT request_id FROM proposals WHERE id = ?)`; the
    third plants `old-confirmed` through `handle` + `review` directly, which it is entitled to do
    because it is RETAIN and already the file's heaviest `handle` consumer. RULE FOR A LATER UNIT: a
    fixture helper's ruling is not local to it -- migrating one obliges a re-read of every consumer,
    RETAIN included.
    ONE RED WOULD HAVE PASSED VACUOUSLY IN THE OTHER DIRECTION. A zero-row `UPDATE` raises nothing,
    so `test_unknown_resolved_source_kind_fails_closed_at_storage` -- whose whole subject is that a
    CHECK constraint fires -- was one edit away from green-and-empty rather than red. It now asserts
    `count(*) == 1` on the target row first. GENERALISATION: a test whose subject is a constraint
    needs a positive control that the constrained ROW exists.
    TWO M3.5b OBLIGATIONS INVERTED AND NEITHER WAS NUMBERED as a tripwire. D15b (the twelve
    `examples/` files byte-identical to `36f7890`) and D22b (every library-API locus byte-identical,
    "so this unit pre-empts no M3.6a doc work") are claims about M3.5b's OWN DIFF, asserted by
    comparing the WORKING TREE. That comparison over-claims and holds only until a later unit
    legitimately enters the scope; D18-D23 are that unit. Both re-scoped to `36f7890` -> `1146421`,
    M3.5b's own range. STANDING RULE: a scope pin read against the working tree expires, only a
    range-scoped assertion survives the next unit.
    THE EXAMPLE README IS THIS UNIT'S, NOT M3.6a2's: D22b's own table dispositions its
    `System.handle(...)` as KEEP *for M3.6a*, and M3.6a2's doc list (README 18 lines, architecture 7,
    adapter-protocol 8, threat-model 4) does not name it.
    D25's REGISTER GATE WAS DISCHARGED BY CLASSIFYING, NEVER BY DEFAULTING -- 5 imperative openers,
    23 descriptive. It diffs by PARAGRAPH, so rewriting one bullet drags every sibling bullet in.
    Gate working as designed.
    THE TRANSCRIPT IS GENERATED BY RUNNING THE DEMO, never edited: the two `request.resolved_by_artifact`
    rows sit inside the pinned block and a hand edit could not know what replaced them
    (`function.promoted`, twice). 20 event rows -> 19, both masks still exactly one match. The demo's
    `len(verifications) == 1` pin was a NAMING device for the document Act 6 carries; re-derived to 4
    plus the one-entry-versus-two-entry inequality that PROVES the checkpoint moved. D21's verdict
    count re-derived 38 -> 35, and the `-O`/`-OO` refusal is intact.
    THE WHOLE TREE RE-DERIVES FROM ONE SCRIPT: `git checkout -- tests/ examples/` then one run
    reproduces `4e72692` exactly, no D16 exception claimed. Contract section 10 carries C01-C09 and
    C11; the 26 baseline counts DEFINITIONS (25 test-tree + the demo) holding 28 CALL SITES, against
    23 RETAIN definitions over 45 sites at close -- three denominators, all live in this unit's prose.
    WAVE 2 MOVES TO S4, and the unit is FIVE sessions: MAIN entered S3 at 73% after attached state
    plus the ground-state read, and the implementation is 28 sites, 3 helpers, ~132 call sites, the
    demo and the transcript. Contract sections 12-13 stay PENDING. S4 = wave 2 + sections 12-13,
    S5 = reversion catalogue + closure.
    A FOURTH BLINDNESS AXIS, and it is the one that costs code. The census reads RETURN VALUES;
    `m3u6a1-fallback.py` reads ARTIFACT SIDE EFFECTS; neither sees that `request_id` is a
    caller-chosen PRIMARY KEY the consumer controls. Both `propose` and `submit_proposal` mint
    `_new_id("req")` internally and neither returns it, so no public route sets or reads it. Four
    MIGRATE sites depend on the value: three use it as a raw-SQL key (`test_system.py` 344 `UPDATE
    requests SET input_json`, 378 `DELETE FROM requests`, 1222 `UPDATE requests SET status`), each
    closed by recovering the row through `(SELECT request_id FROM proposals WHERE id = ?)`.
    THE FOURTH IS THE REAL ONE. `test_function_report_pending_request_join_is_like_and_case_exact`
    plants five request ids that are DELIBERATE COLLIDERS - `pending_join_1` against
    `pendingXjoinX1` under `LIKE`, `PendingCase` against `pendingcase` under case folding - against
    the `r.id = p.request_id` join at `system.py:534/547/574/591`. A minted `req_<32hex>` id is
    lowercase hex whose only `_` sits in the prefix, so migrating this site plainly would leave
    `=` -> `LIKE` and case-folding mutants ALIVE with every assertion still green: a preserved
    invariant deleted with its pin, which is the exact failure the removal standard names. The
    colliders are re-planted after submission by raw `UPDATE` under `PRAGMA foreign_keys = OFF`.
    FIVE REDS, ALL THE SAME AXIS ONE LEVEL UP, and this is S3's open work. `confirm` planted a
    caller-chosen request id that RETAIN tests then consume:
    `test_confirmed_request_cache_is_bound_to_immutable_example` (2 subtests, `request_status` on
    that id), `test_operation_revision_invalidates_every_old_request_path` (2, replays `handle` on
    `old-confirmed` expecting `ReconciliationRequired`) and
    `test_unknown_resolved_source_kind_fails_closed_at_storage`. Migrating a SHARED FIXTURE HELPER
    changes what it plants, so a RETAIN consumer of that helper breaks even though its own lifecycle
    call is untouched - D03 pins the RETAIN definition and says nothing about its fixtures. Fix
    shape: each RETAIN test plants its own request row through `handle` directly, which it is
    entitled to do because it is RETAIN.
    A CONTRACT CLAIM DEFECT, section 3: "HIT - 9 sites. `handle` answered from the artifact." FALSE
    for 2 of the 9. `tests/test_system.py:485` and `:584` carry `outcomes: ["ReconciliationRequired"]`
    in `m3u6a1-fallback.json`, which is the ambiguity branch, not an artifact answer; `:584` reads
    `before=['suspended']` with `resolve -> passed=True match=False`, the MISS-GUARDED signature.
    The shape rule keys HIT on `outcomes != {"ReviewRequired"}`, so it collapses "answered" with
    "refused to choose". Both are RETAIN, so no migration changes; section 10 correction only.
    A GROUND-STATE COUNT WRITTEN FROM TRUNCATED OUTPUT WAS WRONG: the bare `confirm(` call count is
    11, not the 21 first written into `PARAMS`. The count assertion caught it on the first dry run,
    which is the whole reason every rule carries one.
    SITES ARE KEYED BY QUALIFIED NAME AND ORDINAL, NEVER BY LINE. A line-keyed table cannot be
    idempotent: the first pass moves every line below its own first edit, so the second pass reads a
    stale address and D15's `no-op` is unreachable - measured as `ABORT: no enclosing function at
    line 608` on run 2. The dotted name also separates `SystemTests.confirm` from the nested
    `...reaches_every_compiler_block_reason_through_public_apis.confirm`, which is D14a discharged by
    construction rather than by a forbidden anchor.
    THE ANCHOR-INSIDE-REPLACEMENT DEFECT REPRODUCED AND IS NOW GATED. The `assertIsInstance(pending,
    str)` insertion re-applied on every run because its replacement contained its own anchor; the
    fix widens the anchor to the preceding line, and `run()` now REFUSES any `TEXT` rule with
    `old in new` at startup, so the rule set cannot regress into it again.
    S4 DONE, wave-2 STAGING session, `main=` 85% 205K/240K at close. NO teammate dispatched. Shipped
    `364d62b` (both graders + attack seed + contract C10) plus two staged worktrees. No shipped code
    touched, so gate 1 is unmoved at `4e72692`'s 949 tests and was not rerun.
    THE UNIT IS SIX SESSIONS, and the driver is the ENTRY COST, not the work. MAIN reached 82%
    197K/240K having read only the contract and authored two validators - no dispatch, no harvest, no
    ruling. M3.5a's correction already said to budget ~70K of MAIN on top of entry and to treat entry
    as the thing to cut; this session prices the next consequence: a session that BUILDS the graders
    cannot also dispatch and harvest them, because the graders alone are ~900 lines of MAIN-authored
    judgment-bearing code. S5 = dispatch + harvest + sections 12-13, S6 = reversion catalogue +
    closure. The S3 record's "FIVE sessions" line is superseded.
    BOTH GRADERS ARE BUILT AND GRADED BOTH WAYS FROM COMMITTED STATE, so S5 opens on dispatch, not on
    tooling - the M3.5a shape that made its own S4 dispatch-ready. `m3u6a1-battery-validate.py` parses
    the contract itself (29 obligations D01-D28 + D14a, 11 corrections C01-C11, 12 bound obligations)
    so the seed cannot drift from the spec; `--self-test` PASS with 10 controls firing.
    `m3u6a1-attack-validate.py` seeds 30 lens SUBJECTS (A01-A18 claim attack, Y01-Y12 evasion matrix
    over gates 1-8 plus the four preservation obligations); `--self-test` PASS with 12 controls firing.
    A CROSS-CONTRACT ID CITATION COLLIDED WITH A LIVE LOCAL ID, and only the grader saw it. C08 read
    "D25's register gate"; that is M3.5b's D25, while THIS contract's D25 is M3.3's `System.handle`
    byte-span freeze. The binder therefore bound C08 to D25, and a diff-blind author would have
    encoded the register gate into the byte-span test and gone red against correct code. C07's `D15b`
    and `D22b` are foreign too but name nothing local, so they read as foreign; the C08 collision does
    not. Fixed by qualifying all three with their owning unit and teaching the parser that an
    `M<n>.<n><x>` qualifier marks an id foreign. STANDING RULE: cite another unit's obligation with
    its unit name attached - the number alone is not a key.
    C10 ASSIGNED, closing section 10's own numbering gap. The gap was drafting residue (C01-C09 + C11
    = ten corrections), and an unassigned number reads as a lost correction; C10 now carries the
    citation-collision finding. C02 and C11 also gained the obligation citations they were already
    load-bearing for (C02 -> D01, D15; C11 -> D01, D05), because a correction that binds no obligation
    is invisible to the `CORRECTION-UNCITED` counter and therefore to the author it exists to steer.
    THREE GRADER DEFECTS CAUGHT BY THE BOTH-WAYS GRADING ITSELF, one of them AFTER the seed was
    already committed: adding C02's and C11's obligation citations gave D01 a SECOND correction, so
    the dropped-`CORRECTED-BY` control's hardcoded expectation of 1 became 2 and the control read as
    not firing. The count is now DERIVED from the victim obligation's own binding. This is the seed
    credential expiring with its contract, arriving one edit after the credential was earned - re-run
    `--self-test` after every contract edit, not only after a grader edit. The other two: `.upper()`
    mangles `D14a` into `D14A`,
    so the whole lettered-suffix obligation read as an ORPHAN over an UNCOVERED id - normalise through
    the contract's own spelling, never by case transform; and a bare `D\d+` token scan binds a foreign
    unit's obligation to a live local id. Neither is visible to a validator run once.
    S5 ENTRY STATE, dispatch-ready. Both worktrees are STAGED, clean, and based at `6fb4d92` - the
    last commit before the surgery script `8592c34` and the migration `4e72692`, so `m3u6a1-surgery.py`
    is ABSENT from both by construction and the `tests/`/`examples/` trees are pre-migration.
    Each carries the CURRENT contract (`364d62b`) overlaid on that baseline, which is required rather
    than optional: section 10's corrections ARE the spec, and a plain `6fb4d92` tree has none of them.
    · `test-m3u6a1-1` — `.scratch/worktrees/test-m3u6a1-1`, branch `wt/test-m3u6a1-1` at `0497d65`,
      marker `TEST-M3U6A1-1-DONE-1`. Fills `tests/test_migration_battery.py`, seeded RED at
      OBLIGATIONS 29 / TESTS 29 / UNFILLED 29 / BOUND-OBLIGATIONS 12, graded by
      `uv run python .agent/decisions/m3u6a1-battery-validate.py`.
    · `rev-m3u6a1-1` — `.scratch/worktrees/rev-m3u6a1-1`, branch `wt/rev-m3u6a1-1` at `23d3030`,
      marker `REV-M3U6A1-1-DONE-1`. Fills `.agent/decisions/m3u6a1-attack.json`, seeded RED at
      ROWS 30 / UNKNOWN-CELLS 150, graded by
      `uv run python .agent/decisions/m3u6a1-attack-validate.py`.
    THE DIFF-BLIND BOUNDARY HAS TWO COUNTS HERE AND BOTH MUST BE AUDITED SEPARATELY, per M3.5a: the
    worktree's own `6fb4d92` baseline is READ-PERMITTED and the contract's obligations require reading
    it; the primary tree's `src/`/`tests/`/`examples/`, `.agent/decisions/m3u6a1-surgery.py`,
    `git show main:` and `git diff main` are FORBIDDEN. Audit each count over the transcript under a
    positive control that lists the worktree's own paths.
    THE BRIEF MUST CARRY THE M3.5b PARAPHRASE RULE VERBATIM, because this unit's obligations are
    almost all of the form "frame F preserves property P" and that is exactly where a diff-blind
    author pins F's CODE - helper names, variable names, occurrence counts, assertion spellings - and
    goes red against correct code with zero code defects found. Write each clause against the
    PROPERTY, derived from the shipped tree by AST or by running the named gate; take a name only from
    the contract or from the worktree's own baseline definition.
    Report INLINE as the final assistant message with the marker as its last line; the committed
    artifact is the real deliverable. Batch the two spawns in one block.
    S5 also owes three MAIN-only items the wave cannot produce: run the battery against the `6fb4d92`
    baseline AND against HEAD (red-then-green is its credential, and D04/D24-D27 are PRESERVATION
    obligations that legitimately hold at baseline - report the split, never force it); rule every red
    as SUITE / CODE / CONTRACT defect into contract section 12; and rule every attack row into section
    13 through an idempotent `--check` patcher asserting the id set, pattern `m3u5b-rule-attack.py`.
    S5 DONE, wave-2 dispatch + harvest + battery ruling session, ran past one compaction
    boundary. `main=` 98% 236K/240K; `mate=` 73% 174K/240K (`test-m3u6a1-1`; `rev-m3u6a1-1`
    64% 154K/240K). Shipped `f548f88` plus this commit. Contract section 12 is WRITTEN;
    section 13 stays PENDING for S6.
    BOTH TEAMMATES DELIVERED, both graded PASS from committed state: `test-m3u6a1-1` filled
    all 29 obligation tests (`UNFILLED/UNCOVERED/ORPHAN/ASSERTIONLESS/SKIPPED/CORRECTION-UNCITED`
    all 0); `rev-m3u6a1-1` filled 36 attack rows (30 seeded + 6 extension, every graded counter 0).
    Extension rows outnumbered nothing this time but still arrived unprompted, and the reviewer
    caught its own dead control mid-flight (A19 re-bound after a survivor probe).
    THE CREDENTIAL IS RED-AT-BASELINE / GREEN-AT-HEAD, REPORTED NOT FORCED: 23 red / 6 green at
    `6fb4d92` in a detached worktree with the CURRENT `.agent/decisions/` overlaid (`Ran 29 in
    64.365s`), then 7 failures over 5 distinct tests at HEAD. Contract section 7 predicted FIVE
    preservation obligations (D04, D24-D27); the run measured SIX - D22 holds at baseline too,
    because the shipped transcript test asserts one match per mask on both sides of the act
    structure. Derive the split from the run, never from the contract's list (C15).
    ONE CODE DEFECT, and it is the wave's whole return. V06: `tests/test_hospital_ocr_example.py:909`
    still read "erase all 38 of them" while the migrated demo holds 35 `ast.Assert` nodes. S3's own
    record claims "D21's verdict count re-derived 38 -> 35" - that re-derivation reached THIS FILE and
    never reached shipped bytes, because nothing pinned a comment. A NUMBER IN A COMMENT IS CARRIED BY
    CONSTRUCTION: no gate can see it, so the re-derivation obligation is discharged only when an
    instrument binds the prose to the measurement. D21's clause now compares that comment against the
    module's own `ast.Assert` count.
    V07 IS D16 FIRING CORRECTLY, not a defect: the V06 repair was a HAND edit outside
    `m3u6a1-surgery.py`, so the replay diverged by exactly that line within one gate run. Routed into
    `TEXT` with its expected-count assertion; second run reports `no-op`. A repair to a script-generated
    tree lands IN the script - the project's own standing rule, now with a measured instance.
    THE OTHER SIX REDS WERE MAIN'S TEXT, ninth consecutive unit on that pattern, all corrected as
    C12-C15: D10/D14a's "41 call sites" is the BASELINE population that C03's own third repair reduces
    to 40 (the battery now pins WHICH owner left - `test_operation_revision_invalidates_every_old_
    request_path` - so an accidental deletion elsewhere still fails); `self`/`cls` are protocol-bound
    receivers outside D14's domain; and section 1's "Call sites" column carried TWO unlabeled
    conventions, three rows AST-true and three def-inclusive fixed-string counts (7 for 6, 4 for 3,
    2 for 1). Same family as P06's slicing table and the `parser_shape` digest rule.
    ADDING A CORRECTION MID-UNIT EXPIRES THE BATTERY'S SEED CREDENTIAL, measured one unit after M3.5a
    named it: writing C12-C15 turned `CORRECTION-UNCITED` from 0 to 9 against an unchanged, correct
    battery, because the grader binds each correction to the obligations its text names and the
    docstrings were authored against C01-C11. The MECHANICAL half is an amender that reads the
    grader's own output and edits BOTTOM-UP so earlier line numbers stay valid; it converged in one
    round to 0 over 10 docstrings. Two corrections also had to GAIN explicit obligation citations
    first (C13 -> D13, D14; C14 -> D13), because C10's own rule says a correction naming no obligation
    is invisible to the counter that exists to steer the author.
    V08 WAS AN INSTRUMENT SELF-REFERENCE AND IS REPAIRED IN S6: D28 runs the FULL suite as a
    subprocess, and the battery is a MEMBER of that suite, so every battery-bearing revision re-entered
    D28 and the nesting alone exhausted the 600 s timeout. S5 read gate 1 as OK at `f548f88` (978
    tests / 299.230 s) and concluded THE PROPERTY HOLDS, only the instrument needs re-scoping - that
    conclusion was an artefact of recursion DEPTH, not evidence. Cost scales with the count of
    battery-bearing revisions: one of three at `f548f88`, two of four at `abb6b06`, and the whole gate
    went red - `Ran 978 tests in 997.691s`, `FAILED (errors=1)`. Repair = each checkout drops
    `tests/test_migration_battery.py` before the inner run, which is what D28's pre-existing floor of
    949 (= 978 - 29) already assumed. A CHECK WHOSE COST SCALES WITH THE THING IT CHECKS IS UNSTABLE,
    AND A GREEN READING FROM AN UNSTABLE CHECK IS NOT EVIDENCE - ruling on an instrument's SHAPE never
    waits for it to go red.
    GATES 1-8 GREEN FROM COMMITTED STATE at `f548f88`: 1 = 978 tests / OK / 299.230 s · 2 =
    `SURVIVING-MIGRATE 0`, UNRULED/STALE/MEASURE-DRIFT/UNGROUNDED-OVERRIDE/BAD-VERDICT all 0, PASS ·
    3 = `IN-SYNC` · 4 = RESULT PASS, TARGETS 45 · 6 = `no-op` · 7 = rc 0 · 8 = rc 0. Both graders
    PASS and `--self-test` PASS with every control firing.
    SEEDING, tenth and eleventh datapoints, both confirming the standing rule. `rev-m3u6a1-1` flushed
    unprompted every batch and reached PASS at 60% of its window. `test-m3u6a1-1` sat at 0 of 29
    across four polls with a MOVING gauge (29 -> 32 -> 39 -> 44%), took ONE flush directive that
    re-ordered fill-before-refine and named a cheap-first obligation ordering, and committed five
    batches within two polls. A moving gauge is not progress on the graded artifact.
    S6 DONE, attack-ruling + instrument-repair session. Contract sections 1-13 bind; 30 obligations,
    19 corrections. All 36 attack rows disposed through `m3u6a1-rule-attack.py` (idempotent,
    `--check` = `IN SYNC: 36 rows disposed`): 5 ACCEPTED, 27 SCOPED, 2 CLEARED, 2 DEFERRED.
    THE DISCRIMINATOR THAT MADE 36 ROWS RULEABLE: nearly every row proves a gate predicate is
    NECESSARY AND NOT SUFFICIENT, which for a tripwire is the normal condition and not a defect - it
    becomes one exactly where the contract calls the tripwire a proof. So disposition splits on the
    ARTIFACT, not on the attack's strength: ACCEPTED where something shipped is FALSE TODAY, SCOPED
    where the wording outran the instrument. Without that rule the table reads as 34 defects.
    FIVE ACCEPTED, all repaired in-session, each credited by a mutation that must fail. A16: gate 4
    keyed HIT on `outcomes != {ReviewRequired}`, collapsing "answered" with "refused to choose", and
    printed `HIT: 9` while binding correction C01 says seven -> `AMBIGUOUS` split, HIT 7 / AMBIGUOUS 2
    at `tests/test_system.py:481` and `:582`. A19: `m3u6a1-fallback.py:130` gated the digest control
    on `isinstance(outcome, ReviewRequired)`, so 24 of 46 calls ran uncontrolled and one global
    counter named no site -> control reads `requests.input_hash` for every RETURNING call and
    attributes each verdict to its site. Credited by A19's own repro: a wrong digest at
    `tests/test_system.py:277` now prints `CONTROL-SITE-FAILED` + `RESULT: FAIL` rc 1 with the shape
    flipping HIT 7 -> 6 / FACTORY 28 -> 29; before the repair it left every counter clean. Y05: gate 5
    exited 0 while printing both verdicts `False` and NO obligation ran it - which is why the S5 gate
    list records 1-4 and 6-8 and silently skips 5 -> new obligation D29 requires it to grade its
    findings and exit nonzero, pinned by running a mutated copy and requiring rc 1. A14 -> C16 and
    A18 -> C17, below.
    A18 IS THE ROW THAT TAUGHT SOMETHING NEW. Seed census `8592c34` = 23 RETAIN / 44 sites, shipped =
    23 / 45, and the whole increment is
    `tests/test_system.py::test_operation_revision_invalidates_every_old_request_path`, 6 -> 7,
    gaining `tests/test_system.py:880`. `self.confirm("old-confirmed")` was inlined into the direct
    `handle` + `review` pair it always was underneath, because migrated `confirm` cannot carry a
    caller-chosen request id and that test's SUBJECT is that route. The call became VISIBLE, not new.
    ONE EVENT MOVES TWO DENOMINATORS IN OPPOSITE DIRECTIONS - `confirm` callers 41 -> 40, RETAIN sites
    44 -> 45 - and the contract recorded the second without its cause. A denominator that moves
    without its cause recorded is a number no later reader can audit.
    THE FROZEN-EVIDENCE RULE, learned by nearly destroying it. Committed `m3u6a1-fallback.json` is the
    OPENING attribution (72 targets vs the migrated tree's 45) and the source of section 3's counts; a
    casual `--emit` overwrote it with post-migration state and D07 went red at `_shape_owners
    ("MISS-GUARDED") == 0 != 4`, which is how the freeze was discovered to be load-bearing. Restored
    from git, then repaired the RIGHT way: `--reclassify` replays the extracted `_shape()` over the
    table's OWN records and touches no measurement - 2 sites relabelled, `:485` and `:584`, exactly
    C01's two, ACTOR 2 / MISS-GUARDED 4 / FACTORY 51 unmoved, 0 on a second run. A CORRECTED RULE
    REPLAYED OVER FROZEN EVIDENCE IS A REPAIR; A FRESH MEASUREMENT WRITTEN OVER IT IS A LOSS.
    WAVE-2 CROSS-CHECK, the design's own payoff: two teammates who never saw each other's work, and
    the attacker's evasions are answered by obligations the diff-blind encoder wrote INDEPENDENTLY,
    in four cases asserting more than the contract sentence it encoded. D04 pins the WHOLE `src` tree
    against `6fb4d92` (closes Y10/Y11/Y12 where D25/D26/D27 only claim it); D05 pins a qualified-name
    -> count map (A03); D03 pins each RETAIN definition's AST count against the COMMITTED census
    (A02); D16 replays from an explicit detached baseline (A09, Y06); D28 is the per-commit ledger
    A13 demands. MAIN's first reading of A06/Y04 said the frozen opening site set was missing; it is
    not - the committed attribution table IS that set, read by `_shape_owners`, which is why D07
    resolves four MISS-GUARDED owners while the live gate reports zero. Both rulings corrected.
    THE ONE CLASS NO INSTRUMENT IN THIS UNIT CAN CLOSE: the census and shape table are RE-DERIVED, so
    a DELETED consumer and a MIGRATED one leave identical evidence (A01, A06, Y02, Y03, Y04). No
    re-derived census will ever close it. M3.6a2 closes it STRUCTURALLY - once `handle` and
    `request_status` do not exist, every evasion spelling raises `AttributeError` and absence stops
    being measured. Section 7 must read `no measured direct call survives`, never `every consumer
    stopped`. M3.6a2 also inherits the REPLACEMENT-side half of Y04 (assert what stands at each frozen
    site today), Y11's reachability pin (it must flip from passing to failing at deletion), Y15's
    prose scan (the event kinds only vanish there), and Y03's independent ruling anchor. Y07 and Y08
    are DEFERRED to the polish register against existing M3.5b rows.
    Then the reversion catalogue and closure. THE UNIT IS SEVEN SESSIONS.
    GATES RE-MEASURED AT THE V08 REPAIR: 1 = 978 tests / OK / 613.518 s (`uv run python -m unittest
    discover -s tests -t .`; D28 alone = 338.592 s over 4 revisions at ~85 s each, so the honest cost
    of the per-commit axis is HALF the gate) · 6 = `no-op`, confirming the battery sits outside the
    surgery replay domain · battery grader RESULT PASS, all six counters 0.
    WAVE CLOSED IN S6. Both teammates STOPPED; post-stop `git status --porcelain` read per worktree in
    its OWN call, both EMPTY at `wt/test-m3u6a1-1` @ `5e604b7` and `wt/rev-m3u6a1-1` @ `82e1a2e`,
    nothing stranded mid-write, no watcher processes surviving. Artifacts were harvested earlier by
    TARGETED CHECKOUT - `git diff --name-status main..wt/<name>` renders `m3u6a1-surgery.py` as DELETED
    and the whole migration as reverted on both branches, so squash-merge was never available. All
    three worktrees removed (both teammates + the detached `m3u6a1-baseline`). THE `wt/` BRANCHES ARE
    KEPT DELIBERATELY, against the earlier plan to delete them: they are the only pointers that keep
    the recorded teammate SHAs resolvable for MILESTONE-REVIEW, and two refs cost nothing.
    ALSO RECLAIMED: 25 orphaned `/tmp/cement-m3u6a1-*/tree` worktree registrations, ~275 MB, leaked by
    `_detached_worktree` when D16/D28 runs died before their `finally`. `git worktree prune` does NOT
    reclaim them because the directories still exist - both halves need removing. Polish row filed with
    a `SIGKILL`-seeded acceptance check.
    GATE 1 DECISIVE, from committed state at `8bad017`: `Ran 979 tests in 458.691s`, `OK`, rc 0.
    979 = 978 + D29.
    S7 DONE, gate-9 instrument session, `main=` 87% 208K/240K. NO teammate dispatched: a session
    that BUILDS a grader cannot also dispatch and harvest it, which is S4's own measurement
    reproduced one wave later. Shipped `88e18c9`. Only a docstring changed under `tests/`, so
    gate 1 is unmoved at `8bad017`'s 979 and was not rerun; the battery grader, its `--self-test`
    and the D29 test were.
    THE UNIT IS EIGHT SESSIONS against the plan line's three - `est 3 -> 8`, ratio 2.67, the
    largest overrun on this project and the second unprecedented-shape unit to exceed 2.33. The
    driver is unchanged from S4 and S5: entry cost. MAIN read this contract plus the battery's
    clause set and was at 66% before the first line of the harness existed.
    GATE 9 IS BUILT AND GRADED BOTH WAYS FROM COMMITTED STATE, so S8 opens on dispatch rather
    than on tooling. `m3u6a1-mutants.py` derives its clause set from the shipped battery's own
    AST and the contract's own obligation spelling, so the seed cannot drift from either:
    `CLAUSES: 30`, 29 rows, 1 grounded exclusion. `--emit-stub` ADDS missing rows and never
    rewrites filled ones, `no-op` on run 2 - the frozen-evidence rule applied to the seeder.
    `--self-test` PASS with 12 controls ALL FIRING. The catalogue is RED at seed by construction
    at `UNFILLED: 29`, which is its own credential.
    D28 CARRIES NO ROW AND THE GROUNDS ARE STRUCTURAL, NEVER BUDGETARY. Its subject is the commit
    set `git rev-list 6fb4d92..HEAD -- ...` returns, and every mutation this catalogue can express
    edits the WORKING TREE alone, so no reversion or sensitivity row can turn it red and a row for
    it would certify only that the clause ignores the mutation. It was RED at the `6fb4d92`
    baseline, so it already holds the credential gate 9 exists to supply to the six clauses green
    there (D04, D22, D24-D27). Its ~340 s cost and its one nested worktree per revision are
    consequences of the exclusion, not its reason. `unittest` has no negative selector, so the
    exclusion is spelled as an explicit test-id selection and PRINTED on every control line.
    BASELINE-DEFECT IS THE COUNTER M3.5b PAID FOR: that unit's gate teammate filled 48/48 controls
    and honestly annotated three with their own failed verdicts, and the catalogue still graded
    CLEAN because notes are free text. `--validate` now reads each row's `note` for a recorded
    baseline verdict and fails on `baseline=survived`/`misdirected`/`noop`.
    TWO CLAIM DEFECTS IN MAIN'S OWN TEXT, tenth consecutive unit, both found by writing the
    instrument the text describes. C20 - section 7 called the catalogue "gate 3 for this unit"
    while section 6's own table assigns gate 3 to the ruling-sync check; the 3 is M3.5b's, where
    gate 3 WAS the reinsertion sweep, so a reader following section 7 would have graded closure on
    `m3u6a1-rule-census.py --check` and recorded a sweep that never ran. C10's rule one namespace
    wider: a GATE number is not a key across contracts either. C21 - section 12 calls the battery
    29 tests; D29 landed one session later under C19 and the shipped module holds 30.
    C20 AND C21 FIRST BOUND FOUR OBLIGATIONS THEY DO NOT CORRECT, which is C10's own defect
    reproduced by MAIN one correction after recording it. The binder scans bare `D\d+` tokens, so
    C20's illustrative `D25` and C21's `D01-D29 plus D14a` range each became a binding and
    `CORRECTION-UNCITED` went 0 -> 7 against a correct battery. Reworded until only the intended
    binding scans: C20 binds NO obligation (its subject is section 7, and a correction may
    legitimately bind none), C21 binds D29 alone. PROSE ILLUSTRATING A RULE MUST NOT SPELL AN ID
    THE RULE'S OWN PARSER READS.
    S8 ENTRY STATE, dispatch-ready. Contract sections 1-13 bind, 30 obligations, 21 corrections;
    gate 9 is section 6's ninth row and section 7's catalogue.
    · Dispatch `gate-m3u6a1-1` into `.scratch/worktrees/gate-m3u6a1-1` on a branch at the S7 tip.
      NOT diff-blind - a catalogue author must read the shipped tree to write anchors that resolve
      - which is why it is a `gate` role and not a second `test`. Marker `GATE-M3U6A1-1-DONE-1`,
      report INLINE as the final assistant message, the committed artifact
      `.agent/decisions/m3u6a1-mutants.json` being the real deliverable. Brief it to fill all 29
      rows and to run the PRE-BATTERY baseline sweep, graded by
      `uv run python .agent/decisions/m3u6a1-mutants.py --validate` (rc 0, every counter 0), with
      an explicit RETARGET clause: a compound clause earns extra rows, and extension rows have
      outnumbered seeds in every wave this project has run.
    · Each row is a REVERSION (restore the `handle` call, the `request_id` argument, the dead
      `prefix` parameter, a pre-migration demo act) or a SENSITIVITY control on one of the six
      preservation obligations. The M3.5b defect to name in the brief: a control must aim at the
      test that OWNS the property, and where a clause is a STATIC check on another frame's source
      the mutation target is that FRAME, not production code - 13 of M3.5b's 48 controls carried
      exactly that defect at once.
    · Then MAIN runs the decisive sweep itself (`--json`), rules every survivor by name, and
      closes: re-grade the contract's own gate text against what the campaign measured, name the
      ruled tables and the two `wt/` branch tips in the contract, set the unit DONE with
      `est 3 -> 8`, and set M3 IMPLEMENTED only when M3.6a2, M3.6a3, M3.6b and M3.7-M3.9b are also
      DONE - M3.6a1 alone does not close the milestone.
    S8 CHECKPOINT 1, wave dispatched, `main=` 84% 202K/240K at dispatch. Shipped `915c91e`.
    Two teammates LIVE, both worktree-isolated at `915c91e`, both seeded by a MAIN-committed
    both-ways-graded validator: `gate-m3u6a1-1` (`.scratch/worktrees/gate-m3u6a1-1`, marker
    `GATE-M3U6A1-1-DONE-1`) filling the 29-row reversion catalogue; `scout-m3u6a2`
    (`.scratch/worktrees/scout-m3u6a2`, marker `SCOUT-M3U6A2-DONE-1`) re-measuring M3.6a2's
    deletion burden at post-migration HEAD.
    ENTRY COST CONSUMED THE WINDOW BEFORE THE FIRST DISPATCH, fourth session on this measurement
    and the sharpest instance: attached state plus this unit's ground-state read spent ~150K, so
    MAIN reached 84% having read the contract, sized both sweeps and authored one 150-line
    validator. S4 and S7 each priced a session that BUILDS a grader; S8 prices the one that
    DISPATCHES. The term to cut is the attached set, not the work.
    BOTH SWEEP COSTS MEASURED BEFORE DISPATCH, which is what made the brief sizeable rather than
    hopeful: the battery minus D28 runs 29 tests in 78.3 s, and the four owning modules
    (`test_system`, `test_resolve_battery`, `test_proposal_binding_battery`,
    `test_hospital_ocr_example`) run 406 tests in 36.3 s. So the decisive sweep is ~40 min over 30
    runs and the pre-battery baseline ~18 min. D28's exclusion is what buys this - unexcluded it
    would add ~340 s per mutant, ~2.7 h to a single sweep.
    THE PRE-BATTERY SWEEP'S VERDICT VOCABULARY INVERTS, and a brief that omits this collects a
    table of misread rows. With the battery absent from the verdict modules no row's `target_test`
    can appear among the witnesses, so `killed` is unreachable BY CONSTRUCTION: `survived` means
    the pre-existing suite is BLIND to that reversion and the battery is its sole killer - the
    desired outcome and the battery's whole justification - while `misdirected` means the old
    suite already catches it. The brief also forbids that split from reaching the `note` field,
    because `--validate`'s `BASELINE-DEFECT` counter greps `note` for exactly
    `baseline=survived|misdirected|noop` and would fail the gate on an honest measurement.
    MAIN'S OWN CLAIM DEFECT, RAISED AND THEN WITHDRAWN INSIDE ONE SESSION, and the withdrawal is
    the finding. MAIN recorded at `915c91e` + `54b869f` that the M3.6a split record's 46 stage-1
    and 52 stage-6 frame keys were a claim defect against `m3u6a-burden.json`'s 48 and 54.
    `scout-m3u6a2` then normalised the frame keys and measured the pre triple as 46/33/52 - the
    roadmap's exact pair. So the roadmap was never wrong: it recorded NORMALISED keys (`file in
    name`) while the artifact records RAW ones (`file:line in name`). Two conventions, one word,
    and the same family as P06's byte-span slicing table and the `parser_shape` digest rule - a
    count is comparable only against its own convention. WITHDRAWN. The durable repair is not a
    number but a label: every frame count now travels with its convention, in both the artifact
    and this record. A defect found by comparing two numbers that were never comparable is the
    cheapest kind to manufacture, and MAIN manufactured one.
    THE SCOUT IS SPECULATIVE AND MUST NOT BLOCK CLOSE, per the roadmap's own speculation rule. Its
    question is decisive for M3.6a2's sizing and unmeasured by anyone: M3.6a's split ruled that
    migrating consumers first strips the deletion unit's shared-frame burden, M3.6a1 landed that
    migration, and no instrument has since rerun the burden harness. Its brief carries the
    frame-key normalisation trap (a key embeds a line number and the migration moved thousands of
    lines, so a raw set difference is noise) and the hidden-module trap (a cumulative stage
    reporting FEWER breaks than its predecessor has broken a module at import).
    S8 REMAINING WORK, in order: harvest by TARGETED CHECKOUT after reading
    `git diff --name-status main..wt/<name>`; MAIN reruns the decisive sweep itself and rules every
    survivor BY NAME; gates 1-8 from committed state, gate 1 LAST because it is load-sensitive and
    a concurrent sweep manufactures phantom failures; re-grade sections 6-7's gate text against
    what the campaign measured; name the ruled tables and the `wt/test-m3u6a1-1` @ `5e604b7` +
    `wt/rev-m3u6a1-1` @ `82e1a2e` tips in the contract; unit DONE at `est 3 -> 8`.
  - M3.6a2 tier=kernel tags=- depends=M3.6a1 - delete `handle`, `request_status`, `_outcome`,
    `_fail_generation` and `_request_revision_is_current`; delete the `generation_lease_seconds`
    constructor knob, `self._lease_us` and the clock bound named after it; delete request cancellation on
    operation revision together with the `operation.revised` payload's `invalidated_generators` key. Two
    event kinds vanish, `request.resolved_by_artifact` and `request.fallback_failed`. Rewrite the
    library-API prose M3.5b D22 deferred: README 18 hit lines including the whole poll-state table,
    `docs/architecture.md` 7, `docs/adapter-protocol.md` 8, `docs/threat-model.md` 4.
    TRIPWIRES, named now so they become numbered obligations rather than regressions. THREE INVERT rather
    than move: M3.3's P06 byte-span freeze on `System.handle` at `tests/test_submission.py:671` and
    `tests/test_submission_battery.py:289` + `:330` RAISES once the method is gone, and M3.5b's D01 at
    `tests/test_cli_removal_battery.py:617` asserts `System.handle` and `System.request_status` still ship
    as library methods. M3.5b D15a freezes six runtime modules byte-identical. B02 is NOT a tripwire here:
    its frozen tuple is `_command_supervisor.py` and `example_adapter.py` alone, `system.py` having never
    been a member.
  - M3.6a3 tier=kernel tags=- depends=M3.6a2 - delete `Resolved`, `InProgress`, `FallbackFailed`,
    `Rejected`, `ReconciliationRequired`, the `Outcome` alias and every import and `__all__` entry naming
    them; delete `CandidateRequest.request_id`, minting the private request-row id inside
    `_persist_proposal` so the id survives as plumbing and leaves the public protocol. `ReviewRequired`
    loses its last producer when M3.6a2 deletes `handle`, so its retention is this unit's first ruling
    rather than the plan draft's assumption. Measured burden: 10 frames, `test_source.py` `request` (9
    breaks) the only shared one.
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
