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

  Units - 13, 2 DONE + 11 OPEN, executing as 7 waves. `depends` shows the DAG; same-wave units name the same
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
    percentage surcharge: AN ORACLE UNIT DOES NOT FIT ONE WINDOW. It takes two sessions, split at the
    contract, which is exactly route 2. Budget M3.2b, M3.3 and M3.4 the same way and stop trying to
    close one in a single session.
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
    ORACLE CALIBRATION - MEASURED AND CLOSED, binding on M3.2b, M3.3 and M3.4. An oracle unit takes THREE
    MAIN sessions, split at the contract and again at the battery: s1 = wave 1 + acceptance contract
    (31 -> 75%), s2 = implementation (0 -> 80%), s3 = battery (0 -> 93%). The base implementation was
    46 production lines, so static span predicts none of it - the window goes to the BATTERY'S
    COORDINATION. Budget the three remaining oracle units the same way and stop trying to close one in
    fewer sessions.
    RELIABILITY, third datapoint, now with a control. Skeleton-first is the whole variable. The `test`
    re-dispatch carried a stub-commit mandate - every intended test name committed first with a failing
    body, then one commit per filled test - and delivered 52 commits, 48 tests, 22/22 obligations, zero
    unfilled report cells, at 65% of its window. The mutation-campaign teammate got the same mandate in
    prose but no stub artifact to seed, produced nothing across three polls and one explicit flush
    directive, and was stopped; MAIN then ran the 19-mutant sweep itself for a fraction of the
    coordination cost.

  - M3.2b OPEN tier=kernel tags=oracle depends=M3.2a - one-snapshot P1-P6 verification plus `evaluate`
    behind a pure `resolve`; failed verification, verified miss and verified hit stay distinct; publish
    durable 1/1,000/50,000 measurements.
    SESSION 1 CLOSED at the contract, per the M3.2a oracle protocol: wave 1 + acceptance contract
    (`.agent/decisions/m3u2b-contract.md`, sections 1-11 binding, 12-13 PENDING). Session 2 opens with
    that contract as its entry state and implements. MAIN 30% -> 86% (72K -> 205K).
    SESSION 2 CLOSED with the implementation landed and the contract corrected; the battery is
    session 3, exactly as the M3.2a protocol predicts. MAIN 5% -> 92%.
    Shipped at `b5916a9`: `System.resolve` + `FunctionResolution` + export, +56/-1 production lines
    across three files against the spike's +34/-1 estimate (delta = docstrings). Suite 600 -> 600.
    MAIN's own 38-check real-ledger smoke probe is green on shipped bytes and covers all three
    states, the biconditional both ways, `evaluate` call counts 1/1/0, ledger sha256 + full iterdump
    stability, event-digest stability, a raising `_now`, a raising `propose`, one
    `Store.transaction(write=False)`, `in_transaction` at the sixth check, six precedence messages,
    and both escaping error conditions.
    CONTRACT ATTACK, the session's yield: 12 findings, 12 accepted, 3 blocking, ZERO code defects and
    12 claim defects in MAIN's own contract - the FIFTH consecutive unit with that distribution, so
    the pre-implementation attack is settled as the default dispatch. Three reversed MAIN's own
    rulings: the `or document is None` mutation-criterion exception (A12, now a killable mutant plus
    a domain qualifier on section 3's biconditional), the precedence pair set MAIN had also shipped
    in its own smoke probe (A05, two pairs -> four adjacent-edge pairs), and the cost publication
    (A09, the harness never called `resolve`).
    COST REPUBLISHED end to end, the unit's durable obligation, now measuring the shipped method
    (`m3u2b-resolve-benchmark.py` + `m3u2b-resolve-bench.json`): one resolve at the 50,000 cap =
    37,228 ms cold hit / 40,170 ms warm miss / 985,568 KiB peak; 1,000 = 644 ms; 1 = 5.3 ms. The
    resolver adds 4.7% over its components at cap, 4.4% at 1,000, 30% at one entry. Time `N^1.037`.
    Two RSS exponents are now published because the old single figure was not re-derivable from its
    own artifact: raw `N^0.774`, incremental `N^1.000`. The no-hidden-cache inference is withdrawn -
    warm is SLOWER than cold at cap, which bounds a cache below noise rather than proving absence.
    ORACLE delivered 26/26 probes from the contract alone (`m3u2b-oracle.json`, branch
    `wt/orc-m3u2b`); the differential is session 3 and is now a field-by-field pass over two
    committed JSON files keyed by the same corpus ids.
    RELIABILITY, fourth datapoint, and the first FAILURE under seeding: 2 of 3 delivered. Both the
    reviewer and the oracle hit `UNKNOWN-CELLS: 0`. `test-m3u2b` filled ZERO of 96 cells across three
    polls, one flush directive and 58% of its window, and was stopped. Same seed, same validator,
    same brief shape as the two that delivered, so seeding is necessary and not sufficient; the
    variable this time was the task, not the scaffolding - enumerating divergences has no partial
    unit the way filling a probe row does. Section 12 stays PENDING and session 3 re-dispatches
    phase 1 against the unchanged seed.
    FORK RULED on measurement: the plan draft's prescribed "factor `verify_function` onto a supplied
    connection" is SUPERSEDED and does not ship. It was written before M3.2a landed, and there is no
    nesting to fix - none of the six helpers between `system.py:2952` and `system.py:3363` opens a
    second transaction. The thin composition (`verify_function` -> `evaluate` over the returned
    document) measures +34/-1 production lines against the draft's ~170-line estimate, and the spike's
    fork-deciding probe showed the document evaluates identically inside and after the snapshot.
    17/17 probes, suite 600 -> 600.
    COST PUBLISHED, the unit's durable obligation, measured at `019d040` and re-derivable
    (`m3u2b-benchmark.py` + `m3u2b-bench.json`, both validator-graded): one resolve at the
    50,000-entry cap = 35,550 ms cold / 36,461 ms warm / 985,864 KiB peak RSS; 1,000 entries = 616 ms;
    1 entry = 4.1 ms. Time `N^1.037`, memory `N^1.000`, evaluator 0.00028% of the total. Warm reuse
    buys nothing at cap scale, which independently proves no hidden cache. `FUNCTION_MAX_ENTRIES`
    50,000 is a reachable working maximum. MAIN re-derived n1 (4.159849 ms) from committed state.
    WAVE-1 RELIABILITY, the control for M3.2a's finding: 3 of 3 teammates delivered, against 1 of 3 on
    M3.2a. The variable is unchanged - every teammate got a MAIN-authored validator plus a seeded
    all-`unknown` skeleton committed BEFORE dispatch, so its first tool call filled cells instead of
    inventing a format, and UNKNOWN-CELLS was the poll metric. Cost to MAIN: one validator, ~90 lines.
  - M3.3 tier=kernel tags=oracle depends=M3.1 - request-free direct and source-backed submission over
    unchanged schema v2. Also owns `src/cement_runtime/errors.py`: `CandidateSourceError` stays public,
    its supervised-fallback docstring is rewritten, and both it and an arbitrary `Exception` normalize to
    exact public text with no durable row or event, so a broken source leaks nothing. Runs parallel with
    M3.2b.
  - M3.4 tier=kernel tags=oracle depends=M3.3 - freeze request-free proposal/read/review/report/event
    public seams behind one internal binding adapter, schema still v2.
  - M3.5a tier=kernel tags=- depends=M3.2b,M3.4 - add `resolve` and `proposal submit` CLI channels with
    exact exit and payload contracts. The submission channel shape is an open fork - one spike compares an
    aggregate JSON envelope against direct flags, stdin and file, including framing bound and exact error
    behavior - because the maps select explicit submission without measuring any channel.
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
