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
  33% (78K/240K), range 27-33%; window pressure sat on coordination - MAIN peaked 76-96% across M1
  sessions - and both loads now fall on MAIN, which carries implementation under the current authorship
  split.

- M2 - Function as object - IN-PROGRESS. Makes the aggregate deterministic function a first-class,
  verifiable, exportable artifact so paragraph 1's `regular, if large, function` and `once built and
  verified, that function is deterministic` become checkable properties instead of per-entry claims.
  Trust boundary stays exact-lookup: a function is a set of exact entries, never a wider predicate.
  Sizing under the current authorship split: one window buys MAIN's implementation plus its coordination,
  and M2's two recorded halves do not co-fit - `main=` ran 62-93% across u1-u4b while the delegated
  `impl=` on those same units ran 59-92%. u4c and u5 were scoped when a teammate absorbed the
  implementation half, so each opens with a size recheck against `main=` and splits if it does not fit;
  u4c took that recheck and split six ways, since its mandatory surface sizes at ~2.5x u4a.
  Gates for every unit: `uv run python -m unittest discover -s tests -t .` plus `uv build`.
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
    The mutation verdicts above are historical, not rerunnable from committed state: both the catalogue
    and the replay driver are gitignored scratch artifacts, so no clone reproduces them. The committed
    suite is what still holds. Both survive on the workstation that ran the wave, so the driver port
    tracked in `.agent/polish.md` is a copy there rather than a rebuild.
  - u4c split six ways per `.agent/decisions/m2u4c-design.md`, arbitrated from a CLI surface map plus a
    consumed-API map. Two findings drive the split. (1) `cli.py` carries zero references to any
    function-layer API, and the five names the earlier plan listed leave the milestone's own measured gap
    half open: they close the promotion half and leave verification per-entry, because nothing exposes
    `verify_drafts`. `inspect_function_promotion` is likewise the sole producer of the hash `promote_function`
    makes the operator repeat, and `function_receipts` the sole way to learn a receipt ID that
    `--receipt-id` accepts, so the mandatory surface is eight commands, not five. (2) That surface sizes at
    244-365 production + 3,070-4,540 test lines - ~2.5x u4a's production and ~2.6x its tests - while u4a's
    own halves already summed to 152% of one window, u4b's to 173%, u3b2's to 183%. Under the current
    authorship split those halves add rather than alternate, so one unit cannot hold it. The cut is cheap
    here because `cli.py` (360 lines) and `tests/test_cli.py` (121 lines) are small: re-reading them costs a
    few thousand tokens per sub-unit, unlike the u4a/u4b/u4c cut where `system.py` re-reads dominated.
    u4c1 freezes the cross-unit interfaces every later sub-unit inherits - the `_Outcome(payload, status,
    raw)` protocol carrying ordinary JSON, JSON with an explicit process status, and raw document bytes; the
    raw byte channel; nested-subparser and unclamped-limit conventions; and the replacement CLI test runner,
    since today's runner JSON-decodes any stdout and cannot express raw bytes or a nonzero status carrying
    stdout. Frozen rulings: `function verify` exits 6 when the set fails, payload on stdout, on the
    `git diff --exit-code` convention - measured precedent runs the other way, root `verify` returning a
    failing report with exit 0; the current committed snapshot, the prospective union and an immutable
    historical receipt never swap between commands; `eval` is special-cased ahead of the `--db`/`--partition`
    gate and constructs no `System`, though it cannot avoid importing one, since the package `__init__`
    eagerly imports `.system` -> `.store` -> `sqlite3`. Every sub-unit writes `cli.py` + `test_cli.py` only.
  - u4c1 DONE (main=72% 173K/240K, mate=57% 137K/240K) - shared scaffolding + `function show OPERATION
    [--projection-limit N]` over `function_report`'s current anchor; owns and freezes every interface in
    Decision 3 of the design record. `cli.py` +42/-4 (est. 46-69), `test_cli.py` 30 tests (est. 500-740
    lines). Contract `.agent/decisions/m2u4c1-contract.md`. `function show` emits the whole library model
    through `_emit`: a spike measured a hand-written projection at exactly zero byte saving (285,222 either
    way over a 300/100/100 ledger) for +108 production lines, and the model's transitive graph reaches no
    document, text or private cache, so Decision 3's ban holds structurally. Gate `Ran 378 tests / OK` +
    `uv build` rc=0. Evidence: MAIN's 9-mutant battery over the seam killed 9/9, each with a positive
    control proving the patch changed behavior; an independent 88-mutant campaign killed 84, proved 2
    equivalent and left 2 actionable (dispatch guard swallowing the `events` tail, exact-type check
    rejecting `_Outcome` subclasses), both now pinned and killed; a diff-blind suite written from the
    contract alone failed 29/30 at `a717544` and passed 30/30 against this implementation.
    Ruled during the unit: `stale_revision_anomalies` is reachable only from out-of-band ledger state,
    because `operation revise` retires every artifact it strands; `pending_proposals` and
    `stale_revision_anomalies` page in opaque id order, so a truncated page is arbitrary though
    per-ledger stable (both -> `.agent/polish.md`).
  - u4c2 DONE (main=87% 209K/240K, mate=44% 105K/240K) - receipt enumeration plus historical `show`.
    `cli.py` +15, `test_cli.py` +429/-12 (17 new tests); suite 380 -> 396. Contract
    `.agent/decisions/m2u4c2-contract.md`. Both leaves forward unclamped and return the bare library
    model, so `_emit` and the whole u4c1 seam stay byte-identical; production cost landed at the low end
    of the 34-52 estimate because the unit consumes two already-shipped APIs and adds no library delta.
    Ruled during the unit. No material design fork, so no spike wave: payload shape follows u4c1's
    emit-the-model ruling (`FunctionReceiptPage` = 16 scalar fields plus a cursor, reaching no document),
    `function receipts` keeps its roadmap name against the repo's `<group> list` convention because the
    `function` group's leaves are verbs over ONE set and a third nesting level costs more than the
    divergence, and `--receipt-id` stays a flag per u4c design Decision 1. Long-option abbreviation is
    deliberately unpinned: `allow_abbrev` is inherited default, so pinning it would turn a later
    sub-unit's legal flag addition into a red gate.
    Review. One correctness/spec reviewer produced six accepted findings, every one a claim-vs-code gap
    in MAIN's own contract rather than a code defect, and each was reproduced by MAIN before landing.
    The load-bearing one: Decision 9.2 asserted `len(receipts) < limit` ⟺ terminal page, but the library
    fetches `limit + 1` and sets the cursor only when the extra row exists, so a page of exactly `limit`
    rows with nothing behind it is full AND terminal (probed: 2 receipts, `limit=2` → len 2, cursor
    null). Terminality is now exactly `next_before_sequence is None`, with the exact-limit boundary
    pinned beside the short-page one. Also landed: Decision 6 restated as *no matching receipt row*
    rather than *no such operation*, since `function_receipts` has no FK to `operations`
    (`store.py:205-223`) and an out-of-band orphan receipt IS enumerated; the known-limit conversion set
    widened to `TypeError`/`ValueError`/`OverflowError` to match the tracked polish item; the exit-map
    anchor made symbol-qualified because this unit shifts `main`'s lines; adjacent accept/reject pairs
    added at every maximum, since a lone rejection pins nothing about where a boundary sits; and a
    cross-revision historical probe, because three same-revision receipts cannot kill a
    current-revision restriction on `--receipt-id` even though Decision 4 promises any revision.
    Verification. MAIN's own 10-mutant seam battery over the new dispatch and parser lines killed 10/10,
    each proved live by re-importing the mutated module in an isolated clone, preceded by a green
    pristine control and followed by byte-exact restore. Two anchors had to be widened to two lines
    first: `limit=args.limit,` occurs 4x in `cli.py`, so an occurrence-indexed patch would have mutated
    another leaf. A diff-blind suite written from the contract alone, never the diff, passed 35/35
    against this implementation.
    Known limits: pagination is NOT snapshot-consistent across pages - each call opens its own read
    transaction and the cursor is `sequence < boundary`, so a receipt promoted mid-traversal is never
    seen by the walk in progress; row-level receipt self-binding only, since
    `reconstruct_function_receipt` stays the sole reconstruction surface; `function receipts` cannot
    distinguish an unregistered operation from a registered one holding zero receipts. The diff-blind
    teammate's 13 tests are validated but NOT merged - its worktree died with the wave, so only the
    35/35 result survives, and the merge is tracked in `.agent/polish.md`. The mutation teammate's
    catalogue skeleton never reached an anchored campaign; MAIN's own battery is the mutation evidence
    for this unit, and it is scratch-local, so no durable claim rests on it alone.
  - u4c3 DONE (main=88% 211K/240K, mate=91% 219K/240K) - `function verify-drafts OPERATION --actor
    ACTOR` over `verify_drafts` and `function verify OPERATION [--expected-function-hash HEX]` over
    `verify_function`. `cli.py` +32, `test_cli.py` +580 (28 tests); suite 396 -> 424. Contract
    `.agent/decisions/m2u4c3-contract.md`. Production landed at the low end of the 44-66 estimate because
    both leaves forward to already-shipped APIs and add no library delta.
    Design fork, arbitrated from two prototyped spikes that BOTH self-rejected: `verify-drafts` exits 6
    when `not verification.passed`, `skipped` never affecting status. Both spikes independently measured
    that a false draft verdict is unreachable through any supported flow - ordinary evidence growth
    supersedes, suspends or retires rather than leaving a failing draft eligible - so the branch is
    corruption detection, not lifecycle gating, and both independently named the same dominant hazard:
    sibling verbs over one `passed` field mapping false to 6 in one leaf and 0 in the other silently drop
    the gate of any script moved between them. The ruling rests on the asymmetry between the two
    self-rejections rather than on either verdict token - PLAIN's defect is unconditional and sits on the
    contract (`$?` cannot separate all-pass from all-fail, so every caller reimplements the gate; its own
    stop-script needed 11 lines plus a structural JSON parser), STRICT's is conditional and pre-existing
    (rerun non-idempotence belongs to `verify_drafts`, not to the exit code, and fires only in the
    corruption-only branch). Cost over PLAIN, from PLAIN's own accounting: ~4-6 production, ~12-20 test
    lines. `function verify` emits the four-field projection Decision 4 named - `passed`, `entries`,
    `function_hash`, ordered `checks` - never the nested document; `verify-drafts` emits its whole model,
    which reaches no document.
    Verification. MAIN's own end-to-end smoke probe over eleven branches found the contract's own
    corruption recipe defective before any test was written: the committed library precedent leaves
    `artifacts_build_fields_immutable` dropped, which works there because one long-lived `System` checked
    its fingerprint at construction, while every CLI invocation builds a fresh one and exits 5 on the
    schema check without ever reading the corrupt row. The recipe now captures and recreates the trigger.
    A diff-blind suite written from the contract alone failed 25 of 28 at baseline; against the landed
    implementation two of its own predicates were wrong rather than the code - the corruption fixture had
    not adopted the amended recipe, and the exit-map test patched `cli._run` itself, replacing the status
    branch it meant to pin, so it now patches the library boundary and leaves `_run` under test.
    Review. One contract-attack reviewer dispatched BEFORE implementation, per the u4c2 lesson. Four
    accepted findings, every one a claim-soundness defect in MAIN's own contract and none in the code.
    The load-bearing one: the ruling defended its retry hazard as "already true of exit codes 2/3/4/5,
    which are equally non-retryable", which is false as a class claim - 2 and 3 fail before any write, 4
    is the one class where retry IS the intended recovery since the locked-recheck `StateError` rolls
    back, 5 reports uncleanable corruption, and only 6 guarantees a committed row and repeats the write.
    Also landed: the single-skip-reason claim scoped to `_draft_verification_plan` since promotion
    planning carries its own site; the absolute `1->2->3` rerun count replaced by the per-target `+1
    report / +1 failure event per invocation` invariant, since the absolute figure was fixture-dependent;
    and `OverflowError` restored to the known-limit exception set per the standing persisted-scalar rule.
    Known limits: the negative `verify-drafts` branch is unreachable through supported flows, so the
    suite proves the CLI's handling of an already-corrupt ledger, never that ordinary operation produces
    one. Rerun after exit 6 is not idempotent - each invocation commits a fresh report and event for the
    same unchanged bad draft - so exit 6 is a verdict class and a generic retry-on-nonzero wrapper
    amplifies exactly this code. Exit 6 now means two different objects across two leaves, distinguished
    only by payload. `$?` cannot separate authority denial from the locked-recheck `StateError` (both 4),
    nor an unregistered operation from a wrong partition (both 3). No `orc` was dispatched: a reference
    implementation of a leaf that forwards to a library method is the same forwarding code, so a
    differential oracle would add no independent judgment. The reviewer's lenses 3/5 and part of 4 closed
    at best-current-judgment rather than exhausted; the milestone review's per-unit reviewer inherits
    them. The surface map died at 91% with 12 of 25 anchors failing its own validator, so it is
    attention-directing only and no claim here rests on it.
  - u4c4 DONE (main=98% 235K/240K, mate=88% 212K/240K) - `function inspect OPERATION` over
    `inspect_function_promotion` and `function promote OPERATION --expected-function-hash HEX --actor
    ACTOR` over `promote_function`. `cli.py` +30, `test_cli.py` +1011/-7 (29 tests); suite 424 -> 453.
    Contract `.agent/decisions/m2u4c4-contract.md`. No library delta; `system.py`, `store.py`, `models.py`,
    `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/` byte-identical.
    Design fork, arbitrated from two prototyped spikes that BOTH self-rejected: `inspect` emits the
    manifest minus `text` and `document`, unsliced and uncounted. BOUNDED's defects are unconditional - a
    CLI-owned 10,000 maximum leaves prospective members 10,001-50,000 unreachable through any CLI route
    (the same reachability defect that killed u4b's `minimal`), the flag has no library owner to forward
    to against the frozen unclamped convention, and both spikes independently measured zero upstream
    benefit (N=1000 peak RSS 49,816 KiB bounded vs 49,752 unbounded) because `inspect_function_promotion`
    materializes the whole manifest before the CLI can slice. FULL's bite only at maximum cardinality,
    where the alternative provides no relief; its own third loss condition (cannot answer behavior) does
    not discriminate, since Decision 3 bans the document from both and u4c5/u4c6 own content. Counts
    follow: unsliced, `entry_count == len(entries)` identically, so the field advertises a truncation
    semantics the payload lacks.
    Verification. MAIN's own smoke probe over sixteen branches ran before any test existed and corrected
    the contract twice - `handle` resolves a promoted scope rather than proposing, so `challenge` agreeing
    with the active output is the only displacement-fixture route, and a PROMOTED predecessor yields
    `replaces_artifact_id` while a merely VERIFIED one yields `skipped: superseded-build`. The diff-blind
    suite, written from the contract alone, was red 29/29 at baseline; against the implementation four
    reds were the suite's own defects (an argparse paraphrase in five places, and an expectation that
    argparse reports an unrecognized flag before a missing required one), zero were code defects.
    Review. One contract-attack reviewer dispatched BEFORE implementation returned nine accepted findings,
    every one a claim defect in MAIN's contract and none in the code. Load-bearing: `entries == []` does
    not imply `skipped == []`, since rows are classified before the union is assembled (probed
    `entries=0, skipped=1`); a non-qualifying change holds the hash but promotion additionally needs a
    nonempty union, so the exit-0 checkpoint claim was conditional; the locked-recheck `StateError` is NOT
    injection-only but real concurrency behavior of the default-constructed `System`; 499 B/entry is a
    fixture result rather than a maximum, since a displacing candidate costs 533 B (25.416 MiB at 50,000);
    `promote`'s three tuples reach 6.295 MiB jointly against a claimed ~2 MB; and "the bound buys no
    resource benefit" was false as a class claim, since it cuts terminal bytes 99.799% while buying
    nothing upstream.
    Known limits: `inspect` has no cursor and no paging, so a maximum set emits tens of MiB in one write.
    Both exit-4 branches (stale hash, empty set) carry `error: "conflict"` and are separated only by
    message. Authority denial is genuinely CLI-unreachable (no `authority=` is ever passed), but the
    locked-recheck race is reachable and is pinned here only through `main`'s exit map by injection - the
    CLI-level concurrency probe is registered in `.agent/polish.md`. The corruption guarantee is scoped to
    the `artifact_json` recipe; report and artifact-build stored-scalar conversions on both planning paths
    can still leak raw conversion errors, widening the tracked audit. `stale_revision_anomalies` and
    actor-grammar bounds beyond the shipped pins stay as recorded polish.
  - u4c5 split two ways per `.agent/decisions/m2u4c5-design.md`, arbitrated from an anchored fact map plus
    two prototyped design spikes that BOTH self-rejected on disjoint evidence. The prescribed disposition
    is overruled: a failed live verification does NOT raise to exit 5. INTEGRITY measured `artifact
    suspend` alone driving a checkpointed set to `passed=False` through committed commands with vector
    `[T,T,T,T,T,F]`, so `{"error":"integrity"}` misnames ordinary drift, and the aggregate-limit vector
    misnames a capacity bound - reachable because `System.promote` carries no aggregate count guard, only
    `build_function` and set promotion do. VERDICT measured the opposing defect: `function export OP > f`
    at exit 6 leaves `f` holding 1,078 bytes of verdict JSON, because the redirect truncates the target
    before Cement runs, so stdout must never change media type by verdict. Ruling takes each spike's
    measured strength - no bundle bytes, empty stdout, the ordered check vector on stderr as
    `{error:"unverified", message, checks}`, exit 6 - keeping one exit-6 meaning across the `function`
    group and the token/exit bijection intact. Mechanics stay inside the write set: `_run` raises a
    private `_Unverified` and `main` gains one appended `except` branch, leaving `_Outcome`, `_emit` and
    every existing mapping byte-identical. The split follows: the arbitrated surface sizes at 80-100
    production + 800-1,070 test lines against u4c4's landed `+30 / +1,011` at `main=98%`, so it does not
    fit one window. The cut is by CHANNEL - source selection is one judgment surface whose branches decide
    each other, while the file channel is a self-contained writer plus a hostile-path matrix sharing no
    judgment with it. Decisions 1, 3 and 4 of the record bind both sub-units.
  - u4c5a DONE (main=100% 241K/240K then 44% 105K/240K across one compaction, mate=55% 132K/240K) -
    `function export OPERATION [--receipt-id ID]`: source selection, verification gate, raw byte channel.
    `cli.py` +54/-1, `test_cli.py` +486 (21 tests); suite 453 -> 474. Contract
    `.agent/decisions/m2u4c5a-contract.md`. No library delta; `system.py`, `store.py`, `models.py`,
    `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/` byte-identical.
    Shipped. Live source from `verify_function`, negative verdict at exit 6 on stderr as
    `{error:"unverified", message, checks}` through a private `_Unverified` that subclasses `Exception`
    directly, since a `CementError` subclass would be swallowed by `main`'s existing clause and exit 2;
    `--receipt-id` from `reconstruct_function_receipt`, cross-checked against the positional operation
    because the library's lookup keys on partition + id alone, reusing `function_report`'s exact
    `function receipt does not exist for this operation` at exit 3; historical failure staying exit 5,
    since a receipt is immutable and a receipt that will not reconstruct is corruption;
    `FunctionDocument.text` written as exact UTF-8 bytes with nothing appended, non-ASCII and no-`.buffer`
    hosts both pinned, round-tripping through `parse_function` + `evaluate`. An empty promoted set exports
    its real `"entries":[]` document at exit 0; its length is a fixture property, not the 304-byte constant
    the design record named, since the document embeds partition, operation and policy hash.
    Verification. MAIN's own smoke probe over both sources ran before any test existed and confirmed byte
    equality, no trailing newline, empty stderr on success, round-trip hash match and every exit code
    0/2/3/5/6 with exact strings. The diff-blind suite, written from the contract alone, was 36 failures +
    2 errors at baseline and 28/28 green against the implementation, finding no code defect. A 16-mutant
    seam battery over the parser slot, both dispatch branches and `main`'s new clause killed 16/16 under
    the shipped tests, positive control green and `cli.py` restored byte-identical.
    Review. One contract-attack reviewer dispatched BEFORE implementation returned 78 rows, 7 accepted -
    six claim defects in MAIN's contract and ONE behavioral defect in the code. Load-bearing: the
    historical branch passed the positional operation to no library call, so the same argument was graded
    by grammar on the live branch and by receipt membership on the other, and an unset `$OP` reported
    not_found (3) where `function show` reports invalid (2). Fixed by importing the library's own `_name`
    and grading before either call. The rest were record corrections: the reconstruction core raises 20
    `IntegrityError`s plus 7 in its scalar helper rather than 23, the repo has 13 top-level parser groups
    rather than 12, `IntegrityError`/`NotFoundError` are the first EXPLICIT raises here rather than the
    first raises at all, and prototype-measured byte counts (1,032/1,056, 1,078, 304) are fixture results
    demoted out of normative prose - what a committed test pins is the claim.
    Known limits: exit 6 now names three objects across three leaves, one meaning and three payload
    shapes, separated by command and channel rather than by `$?`. Exit 3 covers three conditions on this
    leaf, separated only by message. The aggregate-limit vector is reachable only through the legacy
    per-artifact `System.promote`, so the CLI's handling of it is pinned by injection while the library
    route into that state stays reasoned. Stored-scalar conversions reachable through the reconstruction
    path can still leak raw conversion errors past `main`, which remains the tracked audit.
  - u4c5b OPEN tier=kernel - `function export ... [--out PATH]`: same-directory temp, write, flush, fsync,
    `os.replace`, so the destination holds old bytes or new bytes and never a prefix - a direct writer was
    measured leaving a 17-byte partial. Existing symlink or non-regular target rejected before any write,
    missing parent reported separately, every other OS error translated, all at exit 2 mirroring
    `store.py`'s own messages, since `main` has no catch-all and a bare `OSError` was measured escaping it.
    Emits `{out, bytes, function_hash}` at exit 0, writes nothing on any failure path, and takes mode 0600
    from the replacing inode. Est. 35-45 / 320-450. Depends on u4c5a.
  - u4c6 OPEN tier=kernel - `function eval --bundle PATH --input JSON` over `parse_function` + `evaluate`:
    bundle read by a dedicated strict-UTF-8 reader bounded at `FUNCTION_MAX_BYTES` (67,108,864), evaluation
    input keeping the existing `DEFAULT_MAX_BYTES` channel including `-`, so a bundle can never travel
    through a reader 64x too small. Est. 48-70 / 560-820. Depends on u4c1 + u4c5a.
  - u5 OPEN tier=docs - surface realignment: `README.md` claim pass (guarantees, request outcomes,
    deployment boundary) against what the function object now proves, `docs/architecture.md` contract
    steps for the function layer, and the hospital example resolving from an exported bundle with no
    ledger, no adapter, and no LLM, covered by `tests/test_hospital_ocr_example.py`. Owns every
    documentation edit for M2 so u1-u4c6 stay code-and-test only. `docs` tier because the only code delta
    is example-side behind that committed test, while every claim it writes is re-derived by the M2
    review's `audit` replayer; a claim pass finding that the function object does not prove what the
    README asserts is spine work, not a wording fix. Depends on u1-u4c6.

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

Scope expansion, i.e. future-milestone material that planning promotes into units. Off-spine defects and
deferred perfection on shipped surfaces live in `.agent/polish.md` instead.

- Typed schemas + verifier plugin ABI (M4 seed).
- Broader finite decision tables / constrained expression IR (M4 seed).
- Authenticated reviewer identities, encryption, retention, remote registry/signatures.
- Shadow sampling + production drift telemetry.
- TypedDict projections + dynamic inspection records.
- Owner-selected license + absolute repository/documentation URLs before public publication.
