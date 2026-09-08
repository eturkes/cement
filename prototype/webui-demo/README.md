# Cement web UI demo

This demo shows what Cement is for. A hospital intake desk sends scanned documents to a
chat assistant. The same document layout returns many times. A supervisor confirms the
answers. Cement collects that confirmed work into one deterministic function. An operator
then routes the category to that function, and the answers stop depending on the model.

The screen has two halves. The left half is the chat deployment that staff use. The right
half is the control plane that runs in the background.

## Run

```bash
uv run python prototype/webui-demo/app.py
```

Open <http://127.0.0.1:8765/>. Select **Run the story** for the full sequence. Stop the
server with Ctrl+C. The ledger is a temporary SQLite file, and it disappears with the
process.

## What to watch

1. **The answer is held.** The provider answers document A01, but the chat shows no
   candidate. It shows a proposal ID. Only the review surface shows the candidate.
2. **The supervisor decides.** The review surface shows the extraction that the candidate
   produces. Select `correct` to record the supervisor's own plan. Select `accept` to take
   the candidate. Both create one confirmed example. `reject` creates none.
3. **Evidence accumulates.** Documents A01, A02 and A03 hold different patients, but they
   share one layout signature. That signature is the category. The patient values never
   enter it.
4. **The category becomes a function.** Select `compile`, `verify-drafts` and `promote`.
   Compile groups the confirmed examples. Verification replays them. Promotion is the
   operator's explicit act. The promoted set is one function with one hash.
5. **The operator routes the category.** Turn on operator routing. Document A03 then
   resolves from the promoted set in milliseconds, with no provider call.
6. **The boundary holds.** Send document C01. Its layout is not in the promoted set, so
   Cement reports a miss and returns the request to the supervised path. One confirmation
   is not enough to compile, and the lifecycle panel shows the gate.
7. **The function travels.** Download the bundle, or answer A03 from the bundle bytes
   alone. The bundle carries no ledger.

## Real and simulated

The provider is simulated. `StubProvider` in `demo.py` samples one plan variant and one
latency between 1.1 and 3.4 seconds. It calls no model and uses no network. The panel
labels that number `simulated`.

Everything else is the shipped `cement_runtime`:

- The proposals, reviews, confirmed examples, drafts, verification reports, promotions and
  receipts are real ledger rows.
- The artifact digests, the `function_hash` and the six set checks come from
  `System.verify_function`.
- The resolve time is measured around `System.resolve`. Each call runs the full six-check
  verification and caches nothing.
- The exported bundle is the real `cement-function-v2` document.

The demo reads the OCR corpus and the signature and extraction functions from
`examples/hospital_ocr/`. It enters the pipeline at `submit_proposal`. It never calls
`handle`.

## Proof

The `proof/` directory holds the evidence from one recorded run:

| File | What it shows |
|---|---|
| `01-desk.png` | The intake desk before the first document. |
| `02-held.png` | The held answer and the candidate on the review surface. |
| `03-evidence.png` | Two confirmations against one layout signature. |
| `04-cemented.png` | The promoted set, its hash and the six checks. |
| `05-routed.png` | A03 answered from the function with no provider call. |
| `06-boundary.png` | The miss on layout C and the compile gate. |
| `07-bundle.png` | The answer from the exported bundle. |
| `story-full-page.png` | The whole page at the end of the story. |
| `transcript.txt` | The control-plane log of the same run. |

The server also serves the live log at `/api/transcript.txt`.

## Scope

This is a prototype. It shows behavior, and it is not the production shape. The library
and the CLI are the shipped artifacts. Read the [repository overview](../../README.md) for
the guarantees, and [docs/architecture.md](../../docs/architecture.md) for the state model.

Query parameters help with capture. `?reset=1` starts a new ledger. `?scene=N` plays the
story to scene N. `?expand=1` removes the internal scrollbars for a full-page screenshot.
