# Roadmap

## Milestone ledger

- M1 - Hospital OCR-to-JSON example (per-layout extraction plans) - IMPLEMENTED (units all DONE,
  unreviewed). M1.1-M1.4 DONE (detail below).

Earlier core work and deferred scope are preserved under "Core (completed)" and "Deferred" at the end.

## Active milestone - M1: Hospital OCR-to-JSON example (per-layout extraction plans)

Status: IMPLEMENTED (units all DONE, unreviewed). Scope-seed: session plan task - add an example where OCR'd hospital documents
(physician notes, patient information, lab slips) of varied layouts are processed into JSON, showing how
cement turns per-run bespoke LLM extraction into a single durable pipeline that "learns" over runs.

### Goal & thesis

Different document layouts normally mean a bespoke LLM extraction (a throwaway script) each run. With
cement, each distinct layout's extraction plan is proposed once by an adapter, confirmed by a
supervisor, and - after it recurs enough - promoted to a deterministic artifact. From then on, a known
layout resolves to its plan with no LLM call; the pipeline applies the plan to pull that patient's
fields. Genuinely-new layouts are handled uniformly as gated fallback "edge cases," then solidify the
same way. The "single program" is the pipeline; the reusable pattern lives in the promoted plans plus the
adapter and input canonicalization - never in cement's compiler.

### Honest boundary (do not violate)

cement compiles EXACT LOOKUPS ONLY: scope = (partition, operation, operation_revision, canonical_input).
It never generalizes across layouts; "recurrence alone never justifies generalization" (memory.md,
architecture.md). Therefore:

- cement's memoized scope is `layout_signature -> extraction_plan`, both patient-INDEPENDENT.
- cement guarantees the plan is RETURNED deterministically for a known layout. It does NOT guarantee the
  plan correctly extracts every future patient document of that layout - that rests on the reviewer and
  the adapter (architecture.md: "operational gates, not proof that supervisors were correct").
- A changed or new layout is simply a new canonical input = a new scope = a gated fallback. This maps
  cleanly onto the well-known "layout drift breaks rigid templates" problem: in cement a drifted layout is
  not a silent failure, it is an explicit new edge case awaiting supervision.
- The example must not claim or imply cross-layout generalization. Keep every guarantee statement matched
  to what cement actually proves.

### Design (decided this session)

Answered plan questions:

- cement's role: per-layout extraction plan (input = layout signature, output = reusable plan).
- OCR/LLM realism: deterministic stubs (no external deps, no API keys, reproducible gates; matches
  cement's own "deliberately not an LLM" example adapter).
- Deliverable: guided end-to-end demo (multi-layout corpus + driver running the full lifecycle across
  runs + narrative walkthrough + self-checks).

Location: `examples/hospital_ocr/` (new; existing `examples/echo_adapter.py` untouched). Dependencies:
Python stdlib + `cement_runtime` only. Driver uses the in-process library API with a custom
`CandidateSource` (no subprocess needed).

Pipeline (the "single program"):

1. Corpus: simulated-OCR text files under `examples/hospital_ocr/documents/`, across a few hospital
   layouts - physician progress note (layout A, 3 patients), patient intake form (layout B, 2 patients),
   lab result slip (layout C, 2 patients; showcases decimals-as-strings). Each file is plain text with
   visible labels and sections; "OCR" is a deterministic read + whitespace normalization.
2. `layout_signature(ocr_text) -> JSONValue`: patient-INDEPENDENT canonical signature (document_type +
   ordered labels + section headings, with patient VALUES stripped). This is the cement input. Byte-equal
   across all patients of one layout; distinct across layouts.
3. Plan proposer adapter: `CandidateSource.propose(request) -> Candidate` returning an extraction plan +
   provenance for the layout signature in `request.input`. Deterministic stub, deliberately not an LLM.
4. `apply_plan(plan, ocr_text) -> dict`: deterministically extracts the patient JSON by following the
   plan's locators against the full OCR text (patient values included). Numeric lab values encoded as
   strings.

cement mapping:

- partition: `mercy-general` (a hospital; isolates cross-tenant/department learning).
- operation: `document.extraction_plan` (ONE operation; each distinct layout signature is its own scope,
  so the single pipeline handles all layouts and treats new ones as edge cases).
- demo policy: `CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)`; driver prints a
  note that production defaults are stricter (3 confirmations / 2 reviewers / 7-day span).
- reviewer id `records-supervisor`; promote actor `informatics-lead` (cosmetic).

Anchor JSON shapes (implementers may refine; keep every value cement-json-v1 valid):

layout signature (cement input):

```json
{"document_type": "physician_progress_note",
 "labels": ["Patient", "MRN", "Date", "Provider"],
 "sections": ["Subjective", "Objective", "Assessment", "Plan"]}
```

extraction plan (cement output; grounded in real layout-fingerprint schemas - document_type + fields):

```json
{"document_type": "physician_progress_note", "layout": "A",
 "fields": [
   {"name": "patient_name",   "locator": {"kind": "label",   "label": "Patient"},     "value_type": "string"},
   {"name": "mrn",            "locator": {"kind": "label",   "label": "MRN"},         "value_type": "string"},
   {"name": "encounter_date", "locator": {"kind": "label",   "label": "Date"},        "value_type": "string"},
   {"name": "assessment",     "locator": {"kind": "section", "heading": "Assessment"}, "value_type": "text"}
 ]}
```

`apply_plan` supports two locator kinds: `label` (value after `Label:`) and `section` (text under a
heading). Lab-slip fields (layout C) use string-encoded decimals (e.g. `value_type` = `decimal_string`).

### cement-json-v1 discipline (teaching points to bake in)

- Signature, plan, and output use only null / bool / string / signed-64-bit int / array / string-keyed
  object. NO decimal or exponent numbers - encode lab values and dosages as strings (README +
  adapter-protocol.md).
- The signature must include everything that changes the PLAN (document_type, labels, sections) and must
  EXCLUDE patient values, or recurrence breaks and every document becomes its own scope. This is the
  "hidden context cannot be compiled safely" rule applied to input canonicalization.

### Confirmed facts (smoke-tested this session; trust these)

- Full lifecycle runs end-to-end: after 2 confirmations of one input -> compile -> verify -> promote, a
  later `handle` of the SAME input returns `Resolved(source="artifact")` and the adapter is NOT invoked.
- `min_confirmations` must be >= 2 (`models.py` `CompilePolicy.__post_init__`); `min_reviewers` in
  `[1, min_confirmations]`.
- Confirmed-but-unpromoted examples do NOT resolve `handle` (a 2nd same-input handle still returns
  `ReviewRequired`). Only PROMOTED artifacts short-circuit the adapter.
- `System.verify(...)` returns the report inline (id, passed, tests, failures, scope_hash), so the driver
  never needs `report show`.
- `System.compile(...)` returns `CompileResult(created=(art_id, ...), existing, blocked)`; take the id
  from `.created[0]`. A scope with support below `min_confirmations` appears in `blocked` (use this to
  demonstrate the recurrence gate). `promote` requires the `scope_hash` from `verify`.
- `events(...)` yields the audit trail: `operation.registered`, `proposal.created`, `proposal.accepted`,
  `artifact.compiled`, `artifact.verified`, `artifact.promoted`, `request.resolved_by_artifact`.

### API anchors (`src/cement_runtime/`)

- Public types: `models.py` - `CompilePolicy` (defaults 3 / 2 / 7d), `Candidate(output, provenance)`,
  `CandidateRequest(partition, operation, operation_revision, request_id, input)`, `Resolved(source in
  {"artifact","confirmed"})`, `ReviewRequired(proposal_id)`, `CompileResult`, `VerificationReport`,
  `Promotion`.
- Adapter contract: `source.py:25` `CandidateSource` Protocol - `propose(self, request) -> Candidate`.
- `System` methods: `register_operation` @210, `handle` @336, `review` @965, `compile` @1199,
  `verify` @1610, `promote` @1936, `events` @2594. `__init__.py` re-exports all public names.
- References: `docs/adapter-protocol.md` (candidate contract), `docs/architecture.md` (lifecycle +
  boundary), `examples/echo_adapter.py` (existing example style).

### Units

- M1.1 DONE - Corpus + OCR/signature + plan applicator (deterministic pipeline core; no cement
  dependency). Build the `documents/` corpus (layout A: 3 patients, layout B: 2, layout C: 2) and
  `pipeline.py` with `ocr()`, `layout_signature()`, `apply_plan()`, plus the plan/signature shapes.
  Acceptance: `layout_signature` is byte-identical across patients of one layout and distinct across
  layouts; `apply_plan(plan, ocr)` yields the expected patient fields; every emitted value is
  cement-json-v1 valid (no floats; lab values as strings); the signature contains no patient values. A
  small `if __name__ == "__main__"` self-check (or asserts) demonstrates these.
  Delivered (banked API - reuse in M1.2/M1.3; verified this session): `examples/hospital_ocr/pipeline.py`
  exports `ocr(path)`, `layout_signature(ocr_text) -> JSONValue`, `apply_plan(plan, ocr_text) ->
  dict[str, JSONValue]`, `reference_plan(document_type) -> JSONValue | None`, and `REFERENCE_PLANS` (dict
  keyed by document_type); plus a local `JSONValue` alias - stdlib only, no `cement_runtime` import.
  document_types: `physician_progress_note` (layout A; includes a `section`-kind field `assessment`),
  `patient_intake_form` (layout B), `lab_result_slip` (layout C; decimal analytes `potassium`/
  `creatinine` carry `value_type` `decimal_string` and extract as strings). Locator kinds:
  `{"kind":"label","label":..}` and `{"kind":"section","heading":..}`. Signature shape matches the
  anchor above; byte-equal within a layout, distinct across. Corpus = 7 files under `documents/`
  (`layout_a_progress_note_0{1,2,3}.txt`, `layout_b_intake_form_0{1,2}.txt`,
  `layout_c_lab_slip_0{1,2}.txt`). Toolchain: run with `uv run python` (venv is 3.11.15); the only
  configured gate is `unittest` (no pytest/ruff/mypy). `main=36% (86K/240K)` `impl=28% (67K/240K)`.

- M1.2 DONE - Plan proposer adapter (`plan_adapter.py`, implements `CandidateSource`).
  `propose(request) -> Candidate` returns the extraction plan + provenance for the signature in
  `request.input`; deterministic, with a "deliberately not an LLM" docstring; returns a best-effort plan
  for an unknown signature so the edge-case path still yields a reviewable proposal.
  Acceptance: for each sample layout, `apply_plan(propose(CandidateRequest(input=sig)).output, ocr)`
  reproduces the expected patient JSON; the output is cement-json-v1 valid; provenance is a JSON object
  identifying the stub. Depends on M1.1.
  Delivered (banked API - reuse in M1.3; verified this session): `examples/hospital_ocr/plan_adapter.py`
  exports `PlanProposer` (in-process `CandidateSource`), constructed
  `PlanProposer(source_id="hospital-ocr-plan-stub")` with no required args. `propose(request) -> Candidate`
  reads the layout signature from `request.input`. Known `document_type`: `Candidate.output` is a deep copy
  of `pipeline.reference_plan(document_type)` via `json.loads(json.dumps(...))` (never aliases
  `REFERENCE_PLANS`), provenance strategy `reference_plan`. Unknown `document_type`: a best-effort plan
  (`layout="unknown"`) with one `label`-locator field per signature label then one `section`-locator field
  per heading; field name = `re.sub(r"[^a-z0-9]+","_", v.lower()).strip("_") or "field"`; provenance
  strategy `best_effort`. `Candidate.provenance` keys: `source_id`, `strategy`, `document_type`,
  `deliberately_not_an_llm` (cement-json-v1, no floats). `propose` rejects a non-dict signature, a
  missing/empty `document_type`, and (unknown path) non-string or empty labels/sections. Verified:
  `uv run python examples/hospital_ocr/plan_adapter.py` RC 0 (7 reference-plan + 1 best-effort proposals);
  root `unittest` 62 passed (no regression); stdlib + `cement_runtime` + sibling `pipeline` only; one new
  untracked file. `main=40% (96K/240K)` `impl=83% (199K/240K)`.

- M1.3 DONE - Lifecycle driver + narrative + self-checks (`run_demo.py`, library API).
  Register `document.extraction_plan` with the demo policy, then run the narrative across runs: layout A
  patient 1 -> miss -> review-accept; A patient 2 -> miss -> review-accept; compile -> verify -> promote;
  A patient 3 -> `Resolved(source="artifact")` + apply plan (assert the adapter did not run); then layout
  B recurs and promotes (the pipeline scales to a new layout); layout C confirmed only once and left
  uncompiled to show the recurrence gate (its scope appears in `compile` `blocked` with support below
  `min_confirmations`). Print a readable trace and the `events` feed. Use a throwaway temp db, cleaned up.
  Print a note that production policy defaults are stricter.
  Acceptance: `uv run python examples/hospital_ocr/run_demo.py` exits 0; all asserts pass (pre-promotion
  miss, post-promotion `Resolved(source="artifact")`, layout C stays gated); no stray db is left; stdlib +
  `cement_runtime` only. Depends on M1.1, M1.2.
  Delivered (banked for M1.4; verified this session): `examples/hospital_ocr/run_demo.py` - offline guided
  lifecycle demo; stdlib (`json`/`os`/`pathlib`/`tempfile`) + `cement_runtime` + sibling
  `pipeline`/`plan_adapter` only; flat imports (run-as-script puts the file dir on `sys.path`; not
  package-relative). `main()` drives register -> handle(signature) -> review-accept -> compile -> verify
  -> promote -> artifact-hit; helpers `CountingSource` (wraps `PlanProposer`, `.calls` proves the adapter
  is skipped on a hit), `_document`, `_signature_bytes` (byte-equal signature across a layout),
  `_print_event_trace`. Constants: `PARTITION="mercy-general"`, `OPERATION="document.extraction_plan"`,
  `DEMO_POLICY=CompilePolicy(2,1,0)` (min_confirmations/min_reviewers/min_span_seconds), reviewer
  `records-supervisor`, promoter `informatics-lead`. Real driver output M1.4's README must match (no
  drift): A -> verify(8 tests)/promote -> A03 artifact hit mrn `MG-100913` "Sofia Patel"; B -> same
  lifecycle -> recur hit insurance_id `HZN-774201` "Amelia Brooks"; C -> 1 confirm -> gated, reason
  `support 1 is below required 2`; then a 19-event audit trace. DURABLE cement API fact: `System.events()`
  dicts key the event name under `kind` (NOT `type`); ordered values `operation.registered`,
  `proposal.created`, `proposal.accepted`, `artifact.compiled`, `artifact.verified`, `artifact.promoted`,
  `request.resolved_by_artifact`. Gates: only configured project gate is `unittest` (ruff/mypy are NOT
  project-configured - a prior spec wrongly listed them; provisioned into gitignored `.venv` for a bonus
  clean pass, no tracked change). Verified: driver RC 0 "All checks passed."; root `unittest` 62 passed (no
  regression); no stray db (temp dir under system tmp, self-cleaned + asserted); one new untracked file;
  `pyproject.toml`/`uv.lock` unchanged. `main=63% (151K/240K)` `impl=26% (~63K/240K)`.

- M1.4 DONE - Example walkthrough README + root docs link.
  `examples/hospital_ocr/README.md`: thesis, honest boundary (deterministic plan return, NOT extraction
  correctness), how to run, annotated expected output (captured by actually running the driver), teaching
  points (canonicalize input so recurrence is exact; encode decimals as strings; new layouts are gated
  edge cases; partition isolation; production policy is stricter). Add a short pointer from the root
  `README.md`. Keep markdown lint-clean (backtick-wrap any `<token>` and any adjacent `][` groups).
  Acceptance: the README's expected output matches the driver's real output (no drift); markdown
  diagnostics are clean; the root README links to the example. Depends on M1.1-M1.3.
  Delivered (verified this session): `examples/hospital_ocr/README.md` (new) + root `README.md` `##
  Examples` pointer to it. README: title/thesis, Boundary (honest - guarantees deterministic plan return
  in the exact `(partition, operation, operation_revision, canonical_input)` scope, NOT extraction
  correctness; states plainly "no cross-layout generalization"), How-it-maps (pipeline `ocr` ->
  `layout_signature` -> `System.handle` / `PlanProposer.propose` -> `apply_plan`; scope + policy
  constants; a real layout signature and `reference_plan("physician_progress_note")` plan JSON generated
  from the live helpers), Run, Expected output (the full driver transcript in a fenced text block),
  Teaching points, Pointers (`../../README.md`, `../../docs/architecture.md`,
  `../../docs/adapter-protocol.md`). MAIN independent verification: (1) NO-DRIFT - the driver transcript
  is deterministic modulo ONE per-run random 32-hex artifact id; the fenced block equals live
  `run_demo.py` stdout after masking `art_[0-9a-f]{32}` to `art_<hex>` (byte-equal across 3 runs).
  (2) MARKDOWN clean - markdown is NOT a Serena language here, so the lint used a standalone Marksman LSP
  client (bundled `marksman server`); an in-repo positive control confirmed it validates links in project
  mode (.git), then it reported NO diagnostics on both READMEs; plus one H1, no adjacent bracket groups,
  no unbackticked angle tokens, all three links resolve, and the B01 medications backslash-n stays
  literal. (3) the root README `## Examples` section links the example. Only project gate is `unittest`
  (untouched - no Python changed). `main=69% (165K/240K)` `impl=31% (74K/240K)`.

## Core (completed) - safe learning loop

- [x] Supervised fallback: deterministic miss -> hidden LLM proposal -> explicit review.
- [x] Evidence ledger: immutable canonical fixtures + receipts + revocation edges.
- [x] Compiler: recurrence/stability gates -> capability-free exact lookup build.
- [x] Verification/promotion: full-scope replay + immutable snapshot + atomic activation.
- [x] Runtime safeguards: idempotency, partition isolation, integrity checks, quarantine.
- [x] CLI/API/docs/tests/package verification.

## Deferred - contract/deployment expansion

- Typed schemas + verifier plugin ABI.
- Broader finite decision tables / constrained expression IR.
- Authenticated reviewer identities, encryption, retention, remote registry/signatures.
- Shadow sampling + production drift telemetry.
- TypedDict projections for dynamic inspection records.
- Owner-selected license + absolute repository/documentation URLs before public publication.
