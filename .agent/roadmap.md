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

  Units - 13, 1 DONE + 12 OPEN, executing as 7 waves. `depends` shows the DAG; same-wave units name the same
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
    itself, which cost less than a successor would have. Two lessons bind the next wave: a teammate
    whose deliverable count is flat across two polls is already failing, and a mechanically-derivable
    fact (an AST census, a count, a span) is cheaper for MAIN to compute than to delegate and verify.
  - M3.2a OPEN tier=kernel tags=oracle depends=none - Store-owned enforced-read capability: existing-only
    `file:` URI with `mode=ro`, `PRAGMA query_only`, write-denying authorizer, one rolled-back
    transaction. Oracle-calibration unit per the ruling above. Measured static span = 46 production
    lines, both methods in `store.py`: `_connect` L488-511 and `transaction` L550-571. Blast radius =
    32 `.transaction(` call sites in `system.py` (57 `write=True` / 90 other, repo-wide), 113 in
    `test_system.py`. Base span sits far under M3.1's, which is what leaves room for the battery.
    WAVE 1 + CONTRACT DONE; implementation is the next session's entry state. Acceptance contract =
    `.agent/decisions/m3u2a-contract.md`. Evidence, all tracked and rerunnable: `m3u2a-min-matrix.json`
    (32/32, 0 mismatches), `m3u2a-min-spike.md`, `m3u2a-min-spike.py` (1,141-line harness,
    `--stage readonly --matrix <path>`), `m3u2a-matrix-validate.py`. MAIN reran the decisive stage from
    committed state: 32/32, 0 outcome disagreements against the spike's matrix.
    Rulings: three mechanisms (Store-owned rolled-back transaction + deny-by-default read-allowlisted
    authorizer + percent-encoded existing-only `file:` URI `mode=ro`), each with a distinct forcing
    probe and a distinct leave-one-out failure. `PRAGMA query_only` REJECTED - no probe forces it, so no
    test could pin it, so it would ship as an undetectably-deletable line. Raw path-to-URI concatenation
    FORBIDDEN: planted decoys proved `?`, `#` and `%` names open a DIFFERENT ledger, while space,
    newline and non-ASCII happened to resolve correctly, so a single happy-path test certifies nothing.
    Two measured defects justify the unit: a write inside a `write=False` block currently COMMITS and
    persists (ledger sha256 moved), and a read against a deleted ledger CREATES a 0-byte file that a
    later `Store()` initializes as a fresh empty ledger, laundering deletion into first-run init.
    Reachability census (MAIN-derived, `ast` over `system.py`): all 17 read sites and all 12 helpers
    they hand the connection to are SELECT-only, zero commits, and no non-literal SQL exists in the
    file - so enforcement breaks no shipped call site and the violation is developer-only, which is what
    licenses the private non-retryable `_ReadOnlyViolation(CementError)` at CLI exit 2.
    Open at implementation: re-measure setup cost interleaved (spike artifact and report disagree,
    1.361x vs 1.024x, neither quotable); map Sections B/C (existing read-only test pins, `sqlite3.connect`
    sites outside `_connect`) were never delivered and are cheap to derive during implementation.

    SESSION 2 LANDED THE IMPLEMENTATION - `d4a3158`, gate 549 -> 551 green. Three mechanisms shipped in
    `store.py` behind an unchanged public seam; classification is by `sqlite_errorcode`, never message
    text (`SQLITE_AUTH`/`SQLITE_READONLY` -> private `_ReadOnlyViolation` -> exit 2; `SQLITE_CANTOPEN` ->
    `IntegrityError("ledger file is missing or unreadable")` -> exit 5; every other failure keeps its
    baseline mapping, so `write=True` is unchanged). Both section-1a defects are closed against a real
    ledger. Section 3a is now IN THE GATE as `tests/test_read_capability_census.py`, MAIN-derived and
    reproducing the contract's numbers exactly: 17 read sites, 15 write, 12 helpers, 0 mutating.
    Two production holes came from `test-m3u2a`'s phase-1 table BEFORE any test existed, both real:
    the allowlist admitted ROLLBACK, letting a caller end the Store's snapshot and defeat the section 5
    lifetime guarantee; and `arg2 is None` graded pragmas by SHAPE, which fails BOTH ways - it admits
    bare writers (`PRAGMA optimize` writes `sqlite_stat1`) and denies argument-carrying reads
    (`PRAGMA table_info(...)`, which broke a committed test). Pragmas now allowlist by NAME across a
    readable-bare set and an introspection set.
    Rulings issued against that table, each on measurement: missing AND unreadable ledgers share one
    class, because both raise `SQLITE_CANTOPEN` with identical text and splitting them needs a
    TOCTOU-shaped pre-connect stat that would assign exit 4 "retry" to a condition retry cannot fix;
    W13 `VACUUM` keeps `StateError` because `write=True` raises the IDENTICAL class and message, so it is
    refused by the open TRANSACTION both paths hold rather than by the capability - translating it would
    need a blanket `SQLITE_ERROR` catch that relabels malformed reads and real corruption as caller
    writes.

    ENTRY STATE FOR SESSION 3, which closes the unit. Implementation is committed and green; what remains
    is the BATTERY, and contract section 7 is explicit that a green pre-existing suite is never closure
    here. In order: (1) merge the diff-blind red suite from `wt/test-m3u2a` (`git merge --squash`), whose
    baseline reds are its credential, and re-verify every exact-string pin against a live run before it
    drives anything; (2) harvest `wt/orc-m3u2a` - its `store.py` is committed at `70c6378` and its
    `.agent/decisions/m3u2a-store-probes.py` driver is written to be COPIED INTO THE PRIMARY TREE AND
    RERUN against MAIN's implementation, which is the `diff` cross-check; (3) harvest
    `.scratch/agents/rev-m3u2a.md`; (4) amend the contract - section 7's 548 is stale (551 now), section 5's
    "`_validate_ledger` still runs on the read path" is false as written (it runs once in `_initialize`
    at `store.py:540`, never per transaction; the true property is that it stays authorizer-compatible),
    section 3 carries a DUPLICATED "Forbidden resolutions" paragraph, and section 3's classification claim
    needs scoping to writes the capability itself refuses.

    ORACLE CALIBRATION, MEASURED - this is the number M3.2b, M3.3 and M3.4 are sized against, and it
    supersedes the two-session estimate above. AN ORACLE UNIT TAKES THREE SESSIONS, split at the contract
    and again at the battery. Session 1 = wave 1 + acceptance contract, MAIN 31% -> 75% (~105K), zero
    implementation. Session 2 = implementation, MAIN 0 -> 80% (192K) buying: surface read, a 3-teammate
    wave-2 dispatch, MAIN's own design probes settling three contract-undetermined points, the
    implementation itself, two rounds of test repair over six sites, three full gate runs at ~170s each,
    the phase-1 harvest plus twelve batch rulings, the census promotion, and the commit. Session 3 = the
    battery. The base implementation was only 46 production lines, so span never predicted this: what
    consumed the window was the BATTERY'S COORDINATION, not the code. Budget M3.2b, M3.3 and M3.4 as
    three sessions each and stop trying to close one in two.
    Reliability, second datapoint and much better than the first: 3 of 3 wave-2 teammates produced, at
    35-43% each after the implementation landed. The change that bought it was a brief naming the
    deliverable total, the batch size, a skeleton-first write, and the validator command - and measuring
    progress by UNFILLED CELL COUNT rather than report line count, since a teammate filling a seeded
    skeleton in place holds its line count flat while working normally. Line count read as a stall twice
    and was wrong both times.
  - M3.2b tier=kernel tags=oracle depends=M3.2a - one-snapshot P1-P6 verification plus `evaluate` behind
    a pure `resolve`; failed verification, verified miss and verified hit stay distinct; publish durable
    1/1,000/50,000 measurements.
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
