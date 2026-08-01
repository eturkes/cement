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
  - u2 OPEN - set-level verification in `System`: cross-entry properties per-artifact verification cannot
    see. Duplicate promoted input digest becomes a gate rather than lazy dispatch-time ambiguity
    quarantine; one ABI and one canonicalizer across the set; every entry carries a passing sealed report
    and a valid promotion receipt bound to the current operation revision and policy; recomputed function
    hash matches the stored set. Depends on u1. Mapped surface: add one set enumerator/verifier wired at
    2-3 sites (`_run_verification` has 2 callers, `_validate_promoted` 6, duplicate handling 2) rather
    than rewriting all six receipt callers; regression surface = 18 named `test_system.py` tests + 2 CLI
    tests with ~0 semantic edits expected (one literal, `report.tests == 9`, moves if set probes share
    per-artifact reports); ~6 new cases (duplicate digest, ABI/canonicalizer uniformity, tampered report,
    invalid receipt/policy, function-hash mismatch, atomic race); touches `system.py`, `function.py`,
    `tests/test_system.py`, likely `store.py`, `models.py`/`__init__.py`, `tests/test_cli.py`.
  - u3 OPEN - atomic batch verify and set promotion under one explicitly repeated function hash,
    retiring the O(N) per-entry `--scope-hash` path as the only way to grow a function. Verify every
    eligible draft for an operation in one action; promote the resulting set in one immediate
    transaction whose receipt binds the function hash, each entry's report digest, and the policy.
    Explicit-repeat safety is preserved: the operator types the set hash once. Depends on u2.
  - u4 OPEN - coverage and gap reporting plus the `function` CLI surface (`show`, `export`, `eval`,
    `verify`, `promote`). Honest measures only: promoted entry count, per-entry support and reviewer
    counts, compile-blocked scopes with reasons, pending proposals, and suspended/retired entries. No
    domain-coverage claim, since no domain schema exists. Depends on u1-u3.
  - u5 OPEN - surface realignment: `README.md` claim pass (guarantees, request outcomes, deployment
    boundary) against what the function object now proves, `docs/architecture.md` contract steps for the
    function layer, and the hospital example resolving from an exported bundle with no ledger, no adapter,
    and no LLM, covered by `tests/test_hospital_ocr_example.py`. Owns every documentation edit for M2 so
    u1-u4 stay code-and-test only. Depends on u1-u4.

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
