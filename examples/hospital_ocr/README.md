# Hospital OCR layout learning

Hospital workers often ask an LLM to extract fields from forms. The model writes a plan for each document, even when it has seen the same layout before. Cement retains these answers. A learning pass merges the plans for recurring layouts into a deterministic function. A person decides whether to switch that function on.

This offline example follows seven synthetic documents across three layouts. The plan adapter and the learning pass are scripted stand-ins for LLM calls. The Cement library performs the real projection checks, compilation, verification, promotion, switching and resolution. The demo uses no network.

## Run

Use Python 3.12 or later, SQLite 3.37 or later, and `uv`. From the repository root, run:

```bash
uv sync
uv run python examples/hospital_ocr/run_demo.py
```

The demo creates a temporary ledger and deletes it before the last act. It exits with `All checks passed.` when its checks pass. Run it without `-O` or `-OO`; those Python options remove the checks.

## Six acts

1. **Retain answers.** The adapter receives raw documents as `{"document": text}`. It proposes plans for A01, A02, B01, B02 and C01. These answers remain pending proposals. The model has already answered; no person reviews individual answers.
2. **Learn.** The scripted pass reads `learning_cases`. It decides that these outputs are plans that read document values, not answers that depend on those values. It builds a projection from the observed layouts, groups the proposals by case, and merges each case's plans. It reviews as `learning-pass`, sets the projection, compiles, verifies and promotes version 1. Layouts A and B each have two confirmations. Layout C has only one and stays with the model.
3. **Switch on.** The switch is off by default, including after promotion. A person sets it to `follow`. A03 has new patient values, but the projection recognizes its layout. Cement returns the plan without another adapter call. The pipeline applies that plan to A03.
4. **Add a case.** C02 misses version 1, so the model answers. The next learning pass confirms its plan and publishes version 2. The version difference reports one added case, with no removed or changed cases. The switch follows version 2.
5. **Roll back.** A person pins version 1. A layout-C document misses again, so the model answers. The person returns to `follow`, and version 2 answers layout C without an adapter call.
6. **Use the bundle alone.** The demo exports the version that the switch selects. After it deletes the ledger, the bundle answers a raw document. An unknown layout returns a miss.

## How the parts fit

```
raw document -> System.resolve
  hit  -> extraction plan -> apply_plan -> patient fields
  miss -> model's plan -> answer now + retain a pending proposal

retained proposals -> learning_cases -> grouped plans + projection
  -> review -> set_projection -> compile -> verify_drafts
  -> inspect_function_promotion -> promote_function -> new version

person -> off | follow | pinned
selected version -> bundle + raw document -> resolve_offline -> plan or miss
```

- `pipeline.py` reads simulated OCR text and applies label and section locators. Its `layout_signature` helper serves the adapter only. The caller passes raw documents to Cement, not signatures.
- `plan_adapter.py` supplies `PlanProposer`, a deterministic stand-in for the model. Its reference plans extract values as strings. Decimal quantities, such as potassium, stay strings because `cement-json-v1` excludes decimal numbers.
- `run_demo.py` supplies the scripted learning pass and the six acts. The pass unions compatible plan rows. It corrects proposals and supersedes earlier examples when a merge extends their plan. A disagreement between rows stops this scripted pass; a real pass needs model judgment.
- `checkpoint_function` promotes the verified set as one version without changing the switch. `function_versions` lists the versions. `diff_versions` compares their cases.
- `resolve_offline` calls the shipped `parse_function` and `evaluate` APIs. It requires the function hash that the caller kept from export.

The operation is `document.extraction_plan` in partition `example-hospital`. The compile policy uses the production defaults: two confirmations, one reviewer and no minimum observation span. The only reviewer and promoter in this demo is `learning-pass`. The person's only control is the per-operation switch.

The corpus contains three progress notes (layout A), two intake forms (layout B) and two lab slips (layout C). A03 stays out of learning, so its hit demonstrates reuse across patient values rather than a replay of retained input.

## Boundary

The projection is a `cement-projection-v1` program. It names the document field and lists each observed title and ordered sequence of labels and sections. Patient values do not enter its key. A case stays exact on that key. The projection recognizes the same layout with new values; it does not infer an unseen layout.

The learning pass assumes that documents with one layout need one plan. Cement checks the program's grammar and consistency against confirmed inputs. It does not establish that the assumption is sound or that a plan extracts every future document correctly. A changed title, missing label or extra label returns a miss. The model handles inputs that the function does not cover.

Raw documents and model answers enter the ledger. This example uses synthetic patient data. Removing values from a projection key does not remove them from the retained observations.

The exported bundle includes the projection and the exact cases. It needs no ledger to answer. Its function hash binds the bytes to the version that the caller selected. Keep that hash through a separate, reliable channel when you move a bundle between systems.

## Expected output

Exactly two printed values change per run: one artifact id and the final function hash. The transcript masks them as `art_<hex>` and `<function-hash>`. Evidence ids change the bundle's hash between clean runs, but its byte length stays the same. Every other output line is deterministic.

Regenerate this block from the real demo with:

```bash
uv run python .agent/decisions/m3u8-transcript.py
uv run python .agent/decisions/m3u8-transcript.py --check
```

The updater changes only this transcript block. The tests pin the output, each mask's occurrence count, the shipped API calls and the ledger teardown order.

```text
Hospital OCR learning demo (offline; no LLM or network).
The plan adapter and learning pass are scripted stand-ins for LLM calls.
Cement receives raw documents. The projection maps each recognized layout to one case.
Default policy: 2 confirmations, 1 reviewer, no minimum time span.
Assumption: documents with one layout need one extraction plan.
Cement checks structure and consistency, not whether that assumption or plan is correct.

=== Act 1: retain the model's answers to raw documents ===
A01, A02, B01, B02 and C01: the model answered; five proposals remain pending.
No person reviews individual answers. Cement has no learned function yet.

=== Act 2: learn the recurring cases and publish version 1 ===
The scripted pass reads retained answers, groups their layouts and merges their plans.
Reviewer: learning-pass. The pass sets the projection, compiles, verifies and promotes.
One compiled case: art_<hex>.
Version 1: two cases, for layouts A and B. Layout C has only one confirmation.
Gate reasons: support 1 is below required 2

=== Act 3: a person switches the function on ===
The switch is still off. Even a learned layout goes to the model.
Switch: follow. A03 has new patient values; the projection selects layout A's plan.
A03: adapter calls stayed flat.
A03 patient JSON: {"assessment": "Tension-type headaches, improving.", "encounter_date": "2026-02-21", "mrn": "MG-100913", "patient_name": "Sofia Patel", "provider": "Dr. Amina Shah"}

=== Act 4: another lab slip lets the next pass add a case ===
C02 misses version 1. The model answers and its plan joins the retained proposals.
Version 2: three cases. Difference from version 1: 1 added, 0 removed, 0 changed.
The switch follows version 2 without another person reviewing the answers.

=== Act 5: a person rolls back, then follows the newest version ===
Switch: pinned to version 1. Layout C misses; the model answers.
Switch: follow. Version 2 answers layout C; adapter calls stay flat.

Export the version that the switch selects before deleting the ledger.
Verified function hash: <function-hash>
Exported bundle: 5474 bytes, including the projection.

=== Audit event trace ===
01. operation.registered
02. proposal.created
03. proposal.created
04. proposal.created
05. proposal.created
06. proposal.created
07. proposal.accepted
08. proposal.accepted
09. proposal.accepted
10. proposal.accepted
11. proposal.accepted
12. projection.set
13. artifact.compiled
14. artifact.compiled
15. artifact.verified
16. artifact.verified
17. function.promoted
18. function.switched
19. proposal.created
20. proposal.accepted
21. artifact.compiled
22. artifact.verified
23. function.promoted
24. function.switched
25. proposal.created
26. function.switched

=== Act 6: version 2 answers raw input without a ledger ===
The temporary ledger and its audit trail are gone; only the bundle remains.
A03 offline: the bundle returns the same plan and patient JSON.
Unknown layout offline: the projection reports a miss, not a guessed plan.
All checks passed.
```

## Pointers

- [Learning pass skill](../../skills/cement-learn/SKILL.md)
- [Repository overview](../../README.md)
- [Architecture](../../docs/architecture.md)
- [Command candidate source](../command_source/README.md)
