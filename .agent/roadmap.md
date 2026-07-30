# Roadmap

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
  33% (78K/240K), range 27-33%; the per-unit `impl=83% (199K/240K)` recorded at M1.2 was that session's
  MAIN reading, not its teammate's (true value 31%, 76K). Window pressure sits on coordination - MAIN
  peaked 76-96% across M1 sessions - so size units from `.agent/context.sh <teammate>` readings.
- M2 - UNPLANNED. Scope to be selected from Deferred below.

## Core (completed)

- Supervised fallback, evidence ledger, compiler recurrence/stability gates, verification/promotion,
  runtime safeguards, and CLI/API/docs/tests/package verification.

## Deferred - contract/deployment expansion

- Typed schemas + verifier plugin ABI.
- Broader finite decision tables / constrained expression IR.
- Authenticated reviewer identities, encryption, retention, remote registry/signatures.
- Shadow sampling + production drift telemetry.
- TypedDict projections + dynamic inspection records.
- Owner-selected license + absolute repository/documentation URLs before public publication.
- Candidate contract enforcement: `Candidate` accepts any `provenance` value (`[]`, `'text'`, `5`, `None`
  stored as-is) despite the documented `Mapping` contract, and `System` coerces a non-`Mapping` to `{}`
  rather than failing the fallback. Found during M1 review; out of that milestone's scope.
