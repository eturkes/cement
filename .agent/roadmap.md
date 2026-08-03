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

- M1 - Hospital OCR-to-JSON example (per-layout extraction plans) - REVIEWED. Ships
  `examples/hospital_ocr/` (7-document corpus across 3 layouts, `pipeline.py`, `plan_adapter.py`,
  `run_demo.py`, walkthrough README) plus `tests/test_hospital_ocr_example.py`. Teaching claim: one
  durable pipeline replaces per-run bespoke LLM extraction, because each layout's plan is proposed once,
  supervised, then promoted to a deterministic artifact. Review found and fixed three canonicalization
  defects in the example's `layout_signature` - lost label/section interleaving, colon-bearing patient
  prose entering the signature, and blank values flipping structural kind - so the signature now derives
  from an explicit block grammar by position, fails closed on unrecognized blocks, and carries one
  ordered `structure` list. Review also bound the adapter's reference plans to locator compatibility
  rather than `document_type` alone, made best-effort field names collision-free, and bound the demo's
  recurrence-gate check to layout C's own scope hash. Peak implementing-teammate context across units =
  33% (78K/240K), range 27-33%; window pressure sits on coordination - MAIN peaked 76-96% across M1
  sessions - so size units from `.agent/context-gauge.sh <teammate>` readings.

- M2 - Function as object - IN-PROGRESS. Makes the aggregate deterministic function a first-class,
  verifiable, exportable artifact so paragraph 1's `regular, if large, function` and `once built and
  verified, that function is deterministic` become checkable properties instead of per-entry claims.
  Trust boundary stays exact-lookup: a function is a set of exact entries, never a wider predicate.
  Size every unit against M1 actuals (implementing teammate 27-33%, 66-78K/240K). Gates for every unit:
  `uv run python -m unittest discover -s tests -t .` plus `uv build`.
  - u1 DONE (main=62% 148K/240K, impl=67% 160K/240K) - `src/cement_runtime/function.py` (397 lines) +
    `tests/test_function.py` (749 lines, 22 tests; suite 81 -> 103). `cement-function-v1` document with
    one document-level scope (partition, operation, operation revision, policy hash) and entries carrying
    full input/output values plus their digests and the ledger's own governance digests (artifact,
    evidence snapshot, promotion, and both report digests, since no single whole-report digest exists).
    Function hash = canonical-JSON digest of the whole content object with entries normalized ascending by
    `input_hash`; the portable document embeds that hash as its sole excluded field, so reordering keeps
    one hash and a bundle self-checks with no sidecar. Optional `expected_function_hash` adds
    caller-held-identity binding. Evaluation is digest lookup decided by canonical input text, returning
    detached output. `ValidationError` = structure/bounds; `IntegrityError` = digest mismatch. Limits:
    64 MiB, 50_000 entries, 1M items, depth 67 (default canonicalizer walls admit only ~1_600 entries).
  - u2 DONE (main=84% 202K/240K, impl=80% 191K/240K) - `System.verify_function` in `system.py` (+485)
    plus `FunctionCheck`/`FunctionVerification` in `models.py` (+26) and 31 tests in `test_system.py`
    (+2041; suite 103 -> 134). Read-only verifier: one `Store.transaction(write=False)`, no schema, no
    authority call, no event, no persisted identity - u3 owns the receipt that binds a function hash.
    Five ordered checks (`duplicate-input-digests`, `abi-canonicalizer-uniform`, `sealed-passing-reports`,
    `current-promotion-receipts`, `function-hash-matches-snapshot`) over all promoted rows for
    `(partition, operation)`, so a stale-revision row is a reported failure rather than a silent omission.
    P3 rehashes the full sealed child set at the gate while dispatch keeps its receipt fast path. P5
    reconstructs the expected document field by field and re-canonicalizes against stored row digests;
    `expected_function_hash` is optional and is u3's explicit-repeat seam. Empty set passes vacuously with
    `entries=0`. `function.py`, `store.py`, `cli.py`, `test_cli.py` stay byte-identical; `report.tests == 9`
    unmoved. Duplicate detection is an explicit gate; `handle`'s lazy quarantine and `challenge`'s
    cardinality guard stay as post-gate corruption defenses, since the partial unique index plus
    predecessor retirement make duplicates unreachable through the ordinary API. Known limits: sets within
    the 50,000-entry count guard are still materialized before the 64 MiB/item bounds apply (streaming
    deferred); the result binds one committed snapshot and is never a lease.
  - u3a DONE (main=91% 218K/240K, impl=72% 173K/240K) - pre-promotion entry identity, draft
    eligibility, and batch verification. `function.py` (+8/-7), `system.py` (+513/-223), `models.py`,
    `__init__.py`, `test_function.py`, `test_system.py`; suite 134 -> 162. Scope source: u3 was split
    here into u3a and u3b per the scout's sizing verdict, and both u3 blockers were settled by a
    four-way spike wave arbitrated in `.agent/decisions/m2u3a-design.md`.
    Identity. The blocker was circular: u1's function hash embeds each entry's `promotion_hash`, which
    `promote` creates only at commit time while binding promoter and clock. Resolution = raise the
    document to `cement-function-v2` and replace the entry's `promotion_hash` with `entry_seal`, a
    `cement-function-entry-seal-v1` digest over 14 ordered fields - exactly `cement-promotion-v2` minus
    `promoted_by` and `promoted_at_us`. The seal is recomputed on demand, never stored, so u3a carries no
    schema delta, and `cement-promotion-v2` stays byte-identical with its dispatch fast path untouched.
    Consequence, accepted: function identity is now verified-content identity, so re-promoting identical
    content yields one hash, and activation provenance stays in the ledger receipt.
    Rejected with probe evidence: making the ledger receipt itself pre-promotion computable (dropping
    promoter/time to `cement-promotion-v3`) - its own probe recorded a successful undetected actor/time
    substitution on an active row, since `_validate_promoted` recomputes from `row["promoted_by"]` and
    `row["promoted_at_us"]` (`system.py:3198-3215`); and a distinct candidate-set hash - conceded by its
    own author to be strictly weaker, because one candidate digest can lead to multiple valid function
    hashes, so the operator can never pre-authorize the final identity.
    Eligibility. A literal `status='draft'` filter stays permanently poisoned, so selection now
    reconstructs the expected current build: `_project_current_build` is shared by `compile` and the
    batch enumerator, and an eligible row must match current revision, `draft`, exact canonical input,
    and the projected `build_hash`. Duplicate qualifying rows, duplicate canonical inputs, and missing
    canonical input each fail closed; non-qualifying current drafts are returned as `superseded-build`
    rather than silently omitted. Compile-side supersession was rejected on a probed liveness failure: a
    stale verified row demoted back to `draft` re-poisons the literal batch. Selection-side additionally
    lets revocation requalify an older correct build with no recompilation.
    Batch verification. `System.verify_drafts(partition, operation, *, verified_by)` returns
    `DraftVerification`/`DraftEntry`, sequenced as read preflight, per-artifact authority under the
    existing `artifact.verify` subject, then one `BEGIN IMMEDIATE` whose locked recheck raises
    `StateError` if eligibility moved, then one savepoint, report, and event per row. `verify` and
    `verify_drafts` share `_verify_row`, so per-row semantics stay identical. Savepoint containment
    covers only artifact-local `IntegrityError`/`ValidationError`; authority denial, duplicate rows, and
    any unexpected failure abort the whole batch with no partial writes.
    Verification. Two diff-blind reviewers plus MAIN. Every landed check is pinned by the mutation
    criterion: MAIN replayed all 25 independent-sweep survivors against the fixed tree and killed 22,
    leaving exactly 3 mutants with accepted equivalence proofs (two orderings on a query whose rows only
    key a map, and the private 512-row flush threshold). Review found no defect in the landed code -
    all ten findings were committed-test gaps where a mutant broke a required guarantee while the suite
    stayed green, closed across two fix passes. Known limits: u3a is deliberately not operator-complete,
    since the operator-visible set hash needs u3b's union; the pre-existing `store.py` `ResourceWarning`
    remains, as `store.py` is outside u3a's write set.
  - u3b1 DONE (main=92% 222K/240K then 71% 170K/240K across two sessions, impl=78% 186K/240K) -
    persisted set promotion core. Assemble the final set as retained current promoted rows
    plus passing verified candidates, each candidate replacing the retained row of its own input digest,
    so growth never silently drops established entries; a promoted row on a stale revision is corruption
    and fails closed rather than being omitted. Compute the prospective `cement-function-v2` hash from
    that union - now possible before promotion because every entry seal is - show it with an inspectable
    deterministic manifest (`inspect_function_promotion`), and require the operator to repeat it once as
    `expected_function_hash` (`promote_function`). Promote in one `BEGIN IMMEDIATE` that revalidates
    under its own write lock, rechecks plan identity against what was authorized, bulk-retires
    predecessors before bulk-activating candidates (the partial unique index forbids two promoted rows
    for one scope even transiently), then writes immutable membership rows and the set receipt that
    seals them. Carries the schema delta u3a avoided: `function_receipts` + `function_memberships`,
    `SCHEMA_VERSION` 1 -> 2, and a pre-1.0 ledger reset with no migration runner. Membership is
    reference-only - `artifact_id` + `report_id` + `input_hash` + `entry_seal` - so entry content keeps
    exactly one authoritative home and foreign keys under `PRAGMA foreign_keys = ON` make retention
    structural. Audit payloads project rather than enumerate: the event cap is 262,144 bytes against
    50,000 admissible entries, so mirror the revocation projection of count plus bounded IDs plus a
    digest, and let the membership table stay authoritative. Keep the per-entry path byte-identical -
    its demotion is semantic and lands with u3b2's receipt check, u4 owns the final CLI surface.
    Depends on u3a. Design record: `.agent/decisions/m2u3b-design.md`.
    Landed across one implementation pass plus three fix passes; suite 162 -> 230. Files: `store.py`
    +81/-14, `system.py` +655/-10, `models.py` +33, `__init__.py` +6, `test_system.py` +4462/-51.
    Review. Two diff-blind reviewers - correctness/spec plus an independent 146-mutant catalogue -
    produced findings arbitrated in `.agent/decisions/m2u3b1-findings.md`. Two were production defects in
    `promote_function`, both reproduced by MAIN before dispatch. An empty prospective union performed
    zero authority calls yet still allocated a receipt ID, read the clock, and wrote a durable receipt
    plus event, because authorization was a loop over prospective members; it now raises `StateError`
    ahead of any clock read, ID allocation, or write, and a zero-candidate checkpoint over a nonempty
    retained set stays legal and still authorizes every retained member. The authorized-vs-locked plan
    identity omitted the retirement set, so suspending a displayed predecessor inside the authority
    callback left revision, candidate IDs, member IDs, and the function hash all unchanged while
    committing a different retirement plan than was inspected; the identity tuple now carries the sorted
    non-null `replaces_artifact_id` set, which is also the sole source of the executed `retired_ids`.
    Pins. The other thirteen batches were committed pins over already-correct code: enumeration
    quantification against the 50,000-entry contract (`LIMIT 1000` on either query had left all 208 tests
    green), partition/operation/revision isolation, the expected-hash gate, retained-member
    authorization, bound-report ownership, the surviving semantic scope digest, event transition sets,
    skipped ordering under reverse scans, retire-all-before-activate-any, schema-v2 structure, receipt
    ABI integer framing, manifest byte/item caps, and active-only canonical inputs. MAIN replayed 37
    mutants itself across the three passes, all killed, and audited the widened retirement derivation as
    set-identical (`system.py:3011-3014` sets `replaces_artifact_id` non-null only for candidates).
    Known limit: `verify_function` still exposes P1-P5 only, so a promoted set carries no receipt check
    until u3b2 appends P6.
  - u3b2 DONE (main=93% 222K/240K, impl=90% 216K/240K) - function-receipt verification and historical
    reconstruction. `system.py` +377/-2, `models.py` +34, `__init__.py` +5/-1, `test_system.py` +3225/-65;
    suite 230 -> 293. Design record `.agent/decisions/m2u3b2-design.md`, findings
    `.agent/decisions/m2u3b2-findings.md`.
    Surface. `verify_function` gains ordered check P6 `persisted-function-receipt` after an unchanged
    P1-P5, emitted in every vector including the aggregate-limit path: a nonempty promoted set with no
    current-revision receipt fails, an empty set with no receipt keeps u2's vacuous pass, and the latest
    receipt for the current revision is selected by descending `sequence`. Because P6 compares the
    persisted document against P5's live snapshot, a set that drifted from its last receipt through
    legacy per-entry promotion, revocation, or suspension fails until the operator re-checkpoints with a
    zero-candidate `promote_function` - the legacy path's demotion is now enforced, not just described.
    `System.reconstruct_function_receipt(partition, receipt_id) -> FunctionReconstruction(receipt,
    document)` rebuilds a past `cement-function-v2` from `(receipt, memberships)` joined to the artifact
    and report rows they pin, status-independently: probed byte-identical after supersession, after
    operation-revision retirement, and after revoking every member's evidence. One shared private
    validating core serves both surfaces; it revalidates the 14-field receipt ABI, membership count,
    ordinal contiguity, ascending `input_hash`, the membership digest, the joined rows, scope binding,
    full report child sets, recomputed entry seals, the rebuilt hash, and the normalized self-check.
    Design fork, arbitrated from two staged spikes: scope from `min` (receipt enumeration/discovery stays
    out, since u4 owns the CLI and would freeze ordering/cursor/filter vocabulary a unit early), return
    shape from `record` (the receipt's 16 fields are already recomputed inside the core and mirror an ABI
    Decision 7 already froze, so binding them costs one frozen dataclass while a bare document would cost
    a return-type change across ~45 committed tests). No schema delta: `store.py` stays byte-identical
    because `function_receipts_scope` and the `(receipt_id, ordinal)` primary key already index both
    lookups.
    Review. Two diff-blind reviewers plus a fresh successor sweep, arbitrated in the findings record.
    No production defect in the unmutated landed code. One production resource regression: the aggregate
    fast-fail path reconstructed and fully validated the latest receipt before testing `document is None`,
    so an oversized invalid set still materialized up to 50,000 memberships and their test rows; it now
    emits the failed P6 directly. Everything else - 34 findings across three fix batches - was a committed
    test gap where a live mutant broke a required guarantee while the suite stayed green: enumeration
    tails beyond `LIMIT 1000` on three separate queries plus authorization quantification, read-only proof
    breadth across the failure branches, entry-seal integer framing above nine, inclusive maxima, revision
    and status predicates, schema-index/FK/fingerprint pins, and one dominant family - set checks pinned
    only in the middle of three members, leaving every last-row quantifier alive. MAIN replayed 17 mutants
    itself across batches 1-2 (all killed) and then re-ran the reviewer's entire 108-mutant catalogue
    against the fixed tree: 83 killed, 25 survivors, and every one of those 25 lies inside the reviewer's
    own 26 explicitly-proved-equivalent set.
    Known limits: the >1000-member tail sentinel is one shared fixture carrying four distinct enumeration
    pins, so weakening that single test would unpin all four; reconstruction stays O(members + joined
    reports/tests) and depends on u3b's structural retention invariant; the receipt's candidate and
    retired ID sets are recoverable only as counts plus digests, so u4's previews need the projected
    event.
  - u4 split three ways per `.agent/decisions/m2u4-design.md`, arbitrated from a surface map plus three
    prototyped design spikes. Scope as actually inherited exceeds one window: u3b2's design record
    deferred receipt discovery/enumeration to u4, and u4 also owns an offline ledger-free `eval`, so the
    map sized the whole at 560-770 production + 4,600-6,400 test lines against u3b2's landed 411 + 3,225
    at impl=90%. The `anchored` spike reached the same verdict independently from its own 881-line
    prototype. Two framing decisions bind all three sub-units. (1) A library-level read-only report method
    is required, because the CLI-only baseline self-rejected on measurement: compile-blocked state is
    persisted nowhere and public `compile()` is a write, and a two-ledger probe showed all 13 existing
    read methods returning byte-identical projections while the compiler diverged healthy-vs-`IntegrityError`
    on hidden `receipt_json`. (2) Coverage splits into two separately-anchored surfaces that never share a
    number space - function-anchored identity (membership, frozen build-time support/reviewer counts,
    receipt provenance) and operation-centric now (blocked/ready scopes, pending proposals, artifact
    statuses, stale-revision anomalies) - because both surviving spikes self-rejected as the sole model on
    the same defect: a receipt's membership is immutable while its "complement" moves, so a three-promotion
    probe held `member_count=2` fixed while the same report's promoted count went to 4.
  - u4a DONE (main=93% 223K/240K, impl=59% 142K/240K) - receipt discovery/enumeration.
    `system.py` +91, `models.py` +6, `__init__.py` +2, `test_system.py` +1163/-1; suite 293 -> 314
    across one implementation pass plus one fix pass. `store.py`, `cli.py`, `function.py`, `README.md`,
    `docs/` byte-identical, verified by MAIN at every gate rerun.
    Review. Two diff-blind reviewers, one correctness/spec/claim-soundness and one independent
    138-mutant catalogue plus determinism probes. The mutation sweep killed 126 and left 12 survivors
    with an EMPTY proved-equivalent set, so every survivor became a finding. Cross-lens result: three
    findings confirmed by both, six unique but probe-proved, one rejected. The lenses again found
    disjoint defects - the mutation catalogue never reached the `=` -> `LIKE` family, and the
    correctness reviewer never reached snapshot lifetime.
    One production defect, found only because the reviewer probed past the intact-schema boundary:
    `int(registered["revision"])` had no stored-scalar guard, so a live ledger whose operations schema
    was altered after `System` construction leaked a raw `ValueError` instead of `IntegrityError`. The
    revision is now type- and range-checked before conversion and before the helper call. Everything
    else - the 10,001-row continuation boundary, exact `=` scoping against `_`/case `LIKE` collisions,
    one-snapshot lifetime of the latest lookup, exact bounded `limit + 1` materialization,
    validate-only-returned-rows placement, `before_sequence=False`, inclusive `limit=1`, and the frozen
    public signature/model shape - was a committed-test gap on already-correct code.
    Rejected with reasoning recorded in the design record: a finding wanting the
    current-revision-without-receipt branch to reuse the shared unknown-operation message. The two
    conditions differ and merging the strings would discard diagnostic information and make a
    wrong-scope lookup fail indistinguishably from an unregistered one; the ambiguity was MAIN's
    reviewer brief, not the implementation.
    MAIN replayed all 12 survivors itself against the fixed tree: 12 killed, 0 surviving.
    Known limits: discovery proves row-level receipt self-binding only, never that a listed receipt's
    memberships/artifacts/reports/tests reconstruct - `reconstruct_function_receipt` stays the sole
    reconstruction surface. The 10,001-receipt census is one expensive fixture carrying four pins
    (inclusive `limit=10_000`, maximum-page ordering, the `limit + 1` continuation fetch, and tail
    traversal), so weakening that single test unpins all four; the exact bounded-materialization pin
    deliberately sits on a separate five-row proxy fixture so it does not depend on that census. The
    public-surface introspection test likewise carries all seven exact-shape pins as one frozen ABI.
    Original scope line: `latest_function_receipt(partition, operation) ->
    FunctionReceipt` (resolves the current revision, promotes the private `_latest_function_receipt_row`)
    plus `function_receipts(partition, operation, *, operation_revision=None, before_sequence=None,
    limit=100) -> FunctionReceiptPage(receipts, next_before_sequence)`: `sequence DESC`, exclusive cursor,
    `limit + 1` fetch to decide continuation, every row validated through `_function_receipt_from_row`, a
    malformed row in the page raising `IntegrityError` rather than being skipped. Row-level self-binding
    only - membership reconstruction stays `reconstruct_function_receipt`. Convention corrections against
    both spikes: `limit` bound is the repository-wide `1..10_000`, and enumeration returns an empty page
    for an unknown operation while only the current-revision lookup raises `NotFoundError`. No schema
    delta - `function_receipts_scope` already covers a backward range scan. Write set `system.py`,
    `models.py`, `__init__.py`, `test_system.py`. Depends on u1-u3b2.
  - u4b DONE (main=81% 194K/240K, impl=92% 220K/240K) - coverage + gap report core, both anchors, one
    read transaction. `system.py` +675/-33, `models.py` +83, `__init__.py` +18, `test_system.py` +3725;
    suite 314 -> 353 across one implementation pass plus two fix batches. `store.py`, `cli.py`,
    `function.py`, `README.md`, `docs/`, `examples/` byte-identical, verified by MAIN at every gate rerun.
    Design record `.agent/decisions/m2u4b-design.md`, arbitrated from three prototyped full-design spikes
    that each reached green gates in their own staging tree, so all three costed shapes were buildable.
    `split` (two per-anchor methods plus a shared-snapshot lease) self-rejected on its own measurements:
    atomicity degrades to caller discipline, and its deliberately unclosed public snapshot blocked a
    writer 10,017.791 ms before failing it with `StateError`, because `journal_mode=DELETE` lets a writer
    stage but not commit behind a live reader. `minimal` self-rejected on reachability - its hard-coded
    limit of 100 left 9,900 of 10,000 pending IDs and 49,900 of 50,000 member annotations unreachable
    through any public read. `composite` named its own strongest counterargument: calling full receipt
    reconstruction from the report makes the healthy operation-now anchor unavailable whenever the
    selected receipt is corrupt or 50,000 members wide.
    Accepted shape: one composite read-only call
    `function_report(partition, operation, *, receipt_id=None, projection_limit=100) -> FunctionReport`
    over 9 frozen/slotted models, every field required. The function anchor does NOT reconstruct - it
    validates the receipt row plus only the member rows it returns, keeping
    `reconstruct_function_receipt` the sole reconstruction surface (u3b2's freeze) and matching u4a's
    validate-only-returned-rows convention. Exact `COUNT(*)` everywhere plus `LIMIT ?` detail projections;
    truncation is visible as `count > len(items)` with no redundant `has_more`. Rejected with reasons
    recorded: per-category digests (the u3b1 pattern exists because that projection is sealed into an
    immutable event; this report is ephemeral, and the honest full digest is unavoidably O(n)), an event
    watermark (a snapshot-identity reading it cannot support), and typed reason codes (the compiler's
    ordered strings are the authoritative vocabulary). Naming is structurally separated - frozen fields
    are `build_*`, current fields `active_*` - and no field subtracts, ratios or complements one anchor
    against the other. `projection_limit` is the repository-wide validated `1..10_000`, never clamped.
    Compiler factoring: `_current_build_projections` is a lazy read-callable generator shared with
    `compile()`, raising `IntegrityError` when one input digest carries two canonical texts; `_BlockedBuild`
    gains `reviewer_count`/`span_seconds` while `compile()`'s serialized blocked shape stays frozen at
    exactly `{input_hash, reasons, support}` - now a committed pin, not just scratch before/after evidence.
    All five block reasons are reached through real public-API probes, the fifth via a depth-63 input that
    `handle`/`review` accept while the artifact wrapper crosses canonical depth 64.
    Review. Two diff-blind reviewers: correctness/spec/claim-soundness, and an independent 254-mutant
    catalogue plus determinism/snapshot probes. The mutation reviewer died at 77% (184K) with an
    all-`planned` catalogue and was replaced by a successor seeded from its on-disk catalogue and runner.
    Two production defects, both from the correctness lens, both reproduced by MAIN before dispatch.
    (1) Returned membership rows were syntax-checked only: `_function_report_member` passed
    `membership_report_id` through `_request_id` and `membership_entry_seal` through `_digest` and
    discarded both results, so retargeting a selected member's `entry_seal` to another valid 64-hex digest
    let the report succeed while `reconstruct_function_receipt` rejected the same ledger. The bounded
    member query now joins `test_reports` on both report and artifact identity, checks passing/scope and
    the four hash bindings, and recomputes `_function_entry_seal`; validation stays bounded to each
    returned member's own artifact row plus its single bound report row, with
    `_validate_report(verify_test_set=False)` issuing no query at all. The new inner join can only drop a
    member row, and the pre-existing projected-count check turns any drop into `IntegrityError`.
    (2) Persisted corruption escaped as a raw `TypeError` - selected active evidence with
    `confirmed_at_us=NULL` and a selected promoted report with `passed=NULL` both leaked
    `int() argument ... NoneType` past catches written for `(ValidationError, ValueError)`. Both sites now
    translate `TypeError`/`ValueError`/`OverflowError`. Same defect class u4a already paid for once.
    Everything else - 5 correctness-lens test gaps and 59 mutation findings - was a committed-test gap on
    already-correct code: the two anchors were never behaviorally distinguished (every asserted member had
    `build_support == build_reviewer_count == 2` and every revision reused one policy, so both a
    build-field swap and sourcing `operation_now.policy_hash` from the historical receipt passed all 337
    tests); public field mappings were unpinned against authoritative rows; blocked and stale counts were
    unpinned under truncation; the 10,000 bound was proved only on an empty ledger, leaving a 1,000 clamp
    alive; and nine separate queries had `=` -> `LIKE` mutants alive for want of `_`/case colliders
    reaching each one.
    MAIN's own verification, driven from the reviewer's catalogue rather than any fixer's account, with a
    purpose-built replay driver (`.scratch/main-replay/replay.py`): 8 isolated clones,
    `PYTHONDONTWRITEBYTECODE=1`, a per-mutant proof that the interpreter loaded the mutated module, and
    byte-exact restore, preceded by a pristine control run in all 8 clones under full parallel load so no
    kill could be a flaky-timing artifact. Pre-fix: all 61 catalogue survivors reproduced as survivors.
    Post-batch-1: 10 closed. Final: 58 killed, 1 superseded (the mutated code no longer exists after the
    A1 fix), and exactly the 2 mutants carrying the reviewer's own equivalence proofs still alive. Line
    shifts from the production fix were re-anchored exactly by a `difflib` line map from the catalogue's
    own baseline copy, never by guessing.
    Accepted invariant rather than code change: both pending queries inner-join `requests`, so a pending
    proposal whose request was deleted through a connection with foreign keys disabled undercounts instead
    of failing closed. `PRAGMA foreign_keys = ON` makes that state unreachable through any ordinary API -
    the same posture u3b1 took for membership retention.
    Known limits: the function anchor proves row-level receipt self-binding plus the validity of the
    members it returns, never that the whole membership reconstructs. Unselected rows beyond
    `projection_limit` are counted but not validated, so the report never claims validated history.
    Compile-ready and compile-blocked are the only categories whose counts cost a full pass, since
    ready-vs-blocked is not readable from stored status. The 166 Pyright `reportAttributeAccessIssue`
    errors in `tests/test_system.py` lines 221-1192 are pre-existing at `d0b7e93` - unnarrowed union
    member access in baseline outcome assertions, in a region this unit left byte-identical.
  - u4c OPEN - the five `function` CLI commands (`show`, `export`, `eval`, `verify`, `promote`), owning
    `cli.py` + `test_cli.py` only. Offline `eval --bundle` special-cased ahead of the `--db`/`--partition`
    gate so `System` is never constructed; `export` writing `FunctionDocument.text` bytes exactly rather
    than through `_emit`; `verify` making an explicit exit-code choice, since generic `main` returns 0 for
    any returned dataclass. Depends on u4a + u4b.
  - u5 OPEN - surface realignment: `README.md` claim pass (guarantees, request outcomes, deployment
    boundary) against what the function object now proves, `docs/architecture.md` contract steps for the
    function layer, and the hospital example resolving from an exported bundle with no ledger, no adapter,
    and no LLM, covered by `tests/test_hospital_ocr_example.py`. Owns every documentation edit for M2 so
    u1-u4c stay code-and-test only. Depends on u1-u4c.

- M3 - Trim to paragraph scope - UNPLANNED. Removes behavior outside `turns repeatedly supervised LLM
  answers into narrowly scoped deterministic behavior`, sequenced after M2 so the pure resolver is
  written once against M2's evaluator. Seeds: (a) `CandidateSource` protocol stays in core while
  `CommandCandidateSource`, the subreaper/process-group supervisor, `example_adapter.py`, and
  `docs/adapter-protocol.md` relocate to an optional example surface; (b) the `authority()` callback goes,
  keeping reviewer and actor recording, which supervision genuinely requires; (c) the request lifecycle
  (leases, request-ID idempotency, `in_progress`, `retry_failed`, `fallback_failed`,
  `reconciliation_required`) is replaced by an explicit proposal submission plus a pure read-only
  `resolve`, leaving request lifecycle to the caller. Schema fingerprint bumps; no migration path
  pre-1.0. Plan the split from the M2 close, since M2 reshapes the dispatch path u3 (c) rewrites.

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

- Typed schemas + verifier plugin ABI (M4 seed).
- Broader finite decision tables / constrained expression IR (M4 seed).
- Authenticated reviewer identities, encryption, retention, remote registry/signatures.
- Shadow sampling + production drift telemetry.
- TypedDict projections + dynamic inspection records.
- Owner-selected license + absolute repository/documentation URLs before public publication.
- Candidate contract enforcement: `Candidate` accepts any `provenance` value (`[]`, `'text'`, `5`, `None`
  stored as-is) despite the documented `Mapping` contract, and `System` coerces a non-`Mapping` to `{}`
  rather than failing the fallback.
