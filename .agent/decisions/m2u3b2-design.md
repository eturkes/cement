# M2 u3b2 design record — MAIN arbitration

Inputs: `.scratch/agents/spike-m2u3b2-min.md`, `-record.md` (two independent full-design spikes, each with
a staging prototype + real-pipeline probes). Baseline HEAD `cf274a4`; gates green under MAIN's own run
(230 tests OK, `uv build` OK). Both staging trees independently reached 230 tests OK + `uv build` OK, so
both costed designs are buildable, not sketches. Peaks: min 59% (143K/240K), record 71% (170K/240K).

Binding prior art: `.agent/decisions/m2u3b-design.md` Decisions 7 (receipt/membership ABI) + 8 (P6
placement/semantics). Neither is reopened here.

## Council convergence (both spikes, independently)

Settled and not open to re-litigation in implementation:

- Public entry point name/signature `System.reconstruct_function_receipt(partition, receipt_id)`.
- **One shared private validating core** consumed by both `verify_function` P6 and the public method.
  Recorded cost, accepted: correlated implementation risk (both surfaces can agree on one bug), paid for
  by killing every core mutant from either surface and pinning P6-only logic separately.
- Reconstruction **validates content**, never plain-rebuilds: receipt 14-field ABI hash, membership count
  + contiguous ordinals + ascending `input_hash` + aggregate membership digest, joined artifact/report
  rows, `_artifact_from_row` projections, full report child-set digest + bindings, recomputed
  `entry_seal`, rebuilt `build_function` hash = receipt `function_hash`, final `validate_function`
  self-check. Plain rebuild is rejected: it would emit plausible bytes from diverged rows and reduce
  reference-only membership to an unchecked indirection.
- Reconstruction is **status-independent**: current status, current revision/policy, per-entry promotion
  receipt, and active-evidence checks are deliberately skipped, because those are exactly what a
  historical guarantee must survive. Probed by both: byte-identical rebuild after supersession, after
  operation-revision retirement, and after revoking every member's evidence.
- Failure taxonomy: caller-supplied structure → `ValidationError`; absent or cross-partition receipt →
  `NotFoundError`; any persisted divergence → `IntegrityError` (stored-content `ValidationError` is
  translated, preserving caller-vs-ledger attribution). No semantic `StateError` (no transition) and no
  `ConflictError` (no caller-held expected identity) enters this surface.
- Reconstructed bytes are identical to what `promote_function` sealed, not merely hash-equivalent:
  entries ascend by `input_hash`, and the embedded `function_hash` stays excluded from its own digest.
- P6 converts receipt absence/corruption into `FunctionCheck(passed=False)` rather than raising, matching
  `FunctionVerification`'s structured-check model.
- P6 compares the persisted document against P5's live snapshot document. A live set that drifted from
  the last receipt (legacy per-entry promotion, revocation, suspension) therefore fails P6 until the
  operator re-checkpoints with a zero-candidate `promote_function`. This is the intended demotion.

## Decision — scope from `min`, return shape from `record`

The single genuine fork was the operator-discovery surface, and `record` named it exactly: "the record
alternative wins only if operator discovery is accepted as u3b2 infrastructure rather than u4 policy."
That fork splits into two separable questions, decided oppositely.

**Discovery/enumeration stays out of u3b2** (`min`). `latest_function_receipt` and
`function_receipts(..., operation_revision, before_sequence, limit)` freeze ordering, filter, cursor, and
pagination vocabulary one unit ahead of their only consumer; u4 owns the `function` CLI and coverage
reporting and will design them against a known operator surface. Reconstruction is already usable without
them: `min` probed receipt discovery through `FunctionSetPromotion.receipt_id` and the `function.promoted`
event (`DISCOVERY_EVENT_RECEIPT_MATCH=True`), and P6's own current-revision latest-lookup helper stays
private, ready for u4 to promote. `record` itself lists this vocabulary freeze as its weakness #1.

**The return value binds receipt metadata** (`record`): `FunctionReconstruction(receipt, document)`, not a
bare `FunctionDocument`. Decisive asymmetry:

- The receipt's 16 fields are *already* recomputed and validated inside the accepted core, so returning
  them adds no validation logic and no new failure mode — only a frozen dataclass.
- Those fields mirror the `cement-function-promotion-v1` ABI already frozen by Decision 7, so they freeze
  no new vocabulary. Enumeration semantics, by contrast, would.
- Activation provenance (`promoted_by`, `promoted_at_us`, transition counts/digests) is the entire purpose
  of the set receipt. A reconstruction API that validates it and then discards it forces its only
  consumer to reach for private SQL.
- Rework cost is asymmetric: a bare document later needing metadata means a return-type change across
  u3b2's ~45 committed tests, or a second parallel method duplicating the validation. A bound record that
  u4 uses only for `.document` costs one attribute access.

Both halves are probe-backed: `record` prototyped this exact return shape to green gates, `min` prototyped
the accepted scope. Nothing in the synthesis is unprobed.

## Accepted API surface

```python
System.reconstruct_function_receipt(partition: str, receipt_id: str) -> FunctionReconstruction

@dataclass(frozen=True, slots=True)
class FunctionReceipt:            # mirrors the sealed row: 14 ABI fields + sequence + receipt_hash
    id; sequence; partition; operation; operation_revision; policy_hash; function_hash;
    membership_hash; member_count; candidate_artifact_ids_hash; candidate_count;
    retired_artifact_ids_hash; retired_count; promoted_by; promoted_at_us; receipt_hash

@dataclass(frozen=True, slots=True)
class FunctionReconstruction:
    receipt: FunctionReceipt
    document: FunctionDocument
    text -> document.text                    # derived, no duplicated stored truth
    function_hash -> document.function_hash
```

Both models are exported from `cement_runtime`. `verify_function`'s signature is unchanged; P6 is appended
to the ordered check vector in every path that emits one, including the aggregate-limit path.

**Out of u3b2.** Receipt enumeration/lookup APIs, CLI (u4), every documentation edit (u5), schema changes
of any kind — `function_receipts_scope (partition, operation, operation_revision, sequence)` and the
`(receipt_id, ordinal)` primary key already index both lookups, so `store.py` stays byte-identical.

## Consumers (recorded, for u4/u5 — not built here)

- u4 `function export` → `reconstruct_function_receipt(...).text.encode("utf-8")`.
- u4 `function show` → `.receipt` for actor/time/transition provenance + `.document.value`.
- u5 ledger-free path → `parse_function(text, expected_function_hash=...)` + `evaluate(...)`, with no
  `System`, ledger, adapter, or LLM in the resolution path.
- Receipt IDs reach callers through `FunctionSetPromotion.receipt_id` and the `function.promoted` event
  until u4 ships discovery.

## Required test construction

Binding rules from `.agent/memory.md`, each of which cost a prior unit a real defect:

- Set-level probes corrupt the **middle or last** of ≥3 entries; one probe per condition.
- Where an enclosing digest would otherwise be the rejecter, recompute it coherently so the inner check
  under test is the sole possible rejecter; where checks are entangled, assert the complete ordered
  six-check vector plus the detail of the check under test.
- Mutation criterion binds every added check: some committed test fails when that check's logic alone is
  deleted. P6's lookup/comparison logic must be killed by a P6 test even with reconstruction tests green.
- Read-only claims need a full `iterdump()` comparison or a write-denying SQLite authorizer; row counts
  are insufficient.
- Determinism: reconstruction bytes identical across independent `System` instances on one snapshot.
- Existing P1-P5 check-vector assertions are **retargeted to append P6, never weakened**.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root.
