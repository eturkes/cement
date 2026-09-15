# Cement web UI demo

This demo shows what Cement is for. A hospital intake desk sends scanned documents to a
chat assistant. The same document layout returns many times. A supervisor confirms the
answers. Cement collects that confirmed work into one deterministic function. An operator
then routes the category to that function, and the answers stop depending on the model.

This page is a demo, not a product. Cement ships as a library and a CLI. A production
deployment puts Cement behind a chat product such as Open WebUI, where none of this
reaches the person typing.

The screen has two halves. The left half is the whole surface a user gets. The right half
is everything that stays invisible in production.

## Run

```bash
uv run python prototype/webui-demo/app.py
```

Open <http://127.0.0.1:8765/>. Select **Run the story** for the full sequence. Stop the
server with Ctrl+C. The ledger is a temporary SQLite file, and it disappears with the
process.

## What to watch

1. **The chat stays plain.** The left half shows an attachment, a question and an answer.
   It shows no proposal ID, no model name, no digest and no timing. A held answer looks
   like a slow answer, because that is what a user sees.
2. **The supervised answer and the cemented answer are identical.** Document A02 is
   answered by the model and confirmed by a person. Document A03 is answered by the
   promoted function. The two bubbles render the same. That identity is the point.
3. **Each message opens.** Select **what happened under this** below any message. The
   machinery that the chat hides appears there: the signature Cement keys on, the plan
   the model wrote, what the supervisor changed, the digests, and the commands.
4. **The operator works in a terminal.** The right half runs the real `cement` binary
   against the demo ledger. Each row shows the command, a short reading of what it
   returned, and the exit code. Select the `stdout` line for the verbatim bytes and the
   exact argument list.
5. **Evidence accumulates.** Documents A01, A02 and A03 hold different patients, but they
   share one layout signature. That signature is the category. The patient values never
   enter it.
6. **The category becomes a function.** Select `compile`, `function verify-drafts` and
   `function promote`. Compile groups the confirmed examples. Verification replays them.
   Promotion makes the operator repeat the digest that `function inspect` reported.
7. **The operator routes the category.** Turn on operator routing. Document A03 then
   resolves from the promoted set in milliseconds, with no model call.
8. **The boundary holds.** Send document C01. Its layout is not in the promoted set. The
   user simply waits, and the request returns to the supervised path. The terminal shows
   `blocked  layout C - support 1 is below required 2`. Cement widens nothing on its own.
9. **The function travels.** Download the bundle, or answer A03 from the bundle bytes
   alone. The bundle carries no ledger.
10. **The function is readable.** Select **read the function**. The overlay shows the
    promoted set as one function: one guarded branch per entry, and a no-match tail. Each
    branch opens to the four commands that rebuild its lineage, and then to the requests
    themselves. Compare `proposed_output` against the entry that now answers.

## Real and simulated

The model is simulated. `StubProvider` in `demo.py` samples one plan variant and one
latency between 1.1 and 3.4 seconds. It calls no model and uses no network. The page
labels that number `simulated`.

Everything else is the shipped `cement_runtime`:

- The proposals, reviews, confirmed examples, drafts, verification reports, promotions and
  receipts are real ledger rows.
- The operator lifecycle runs as real `cement` subprocesses against the same ledger. The
  review, revoke, compile, verify-drafts, promote, inspect, verify and export commands all
  execute. The page prints what they printed.
- The artifact digests, the `function_hash` and the six set checks come from those
  commands.
- The exported bundle is the real `cement-function-v2` document.
- The function source overlay parses that bundle back and reads its entries. The `def`
  and `if` lines are a rendering for the reader. Cement seals exact entries, and it emits
  no code.

Two calls stay in process, and the page says so where it shows them. The chat submits a
proposal and resolves an input through the library, not through a subprocess. A `cement`
subprocess costs a flat 106 to 109 milliseconds of interpreter startup, and
`System.resolve` costs 0.9 to 3.5 milliseconds. A subprocess would therefore report
startup cost as the function's cost.

A long argument prints as its shell variable, such as `--output "$OUTPUT"`. The exact
argument list stays under the `stdout` disclosure. The bound is 80 characters, so a
64-character digest still prints in full. Repeating that digest is what `function promote`
requires.

Walking one entry back to its requests costs four commands, and the overlay runs all of
them: `function inspect` gives the artifact ID, `artifact show` gives the example IDs,
`events` gives the proposal IDs, and `proposal show` gives `proposed_output` beside
`final_output`. No command prints an entry beside its originals, and `events` accepts no
example filter, so the join is done by hand. `.agent/deferred.md` row `p67` records that
gap.

The demo reads the OCR corpus and the signature and extraction functions from
`examples/hospital_ocr/`. It enters the pipeline at `submit_proposal`.

## Proof

The `proof/` directory holds the evidence from one recorded run:

| File | What it shows |
|---|---|
| `01-desk.png` | The intake desk before the first document. |
| `02-held.png` | The user waiting, and the candidate on the review surface. |
| `03-evidence.png` | Two confirmations against one layout signature. |
| `04-cemented.png` | The promoted set, its hash and the six checks. |
| `05-routed.png` | A03 answered from the function, in a bubble that looks supervised. |
| `06-boundary.png` | The miss on layout C and the compile gate. |
| `07-bundle.png` | The answer from the exported bundle. |
| `08-source.png` | The function read as source, with the four hops behind one entry. |
| `story-full-page.png` | The whole page at the end of the story. |
| `transcript.txt` | The ledger events of the same run. |

The server also serves the live log at `/api/transcript.txt`.

## Scope

This is a prototype. It shows behavior, and it is not the production shape. The library
and the CLI are the shipped artifacts. Read the [repository overview](../../README.md) for
the guarantees, and [docs/architecture.md](../../docs/architecture.md) for the state model.

Query parameters help with capture. `?reset=1` starts a new ledger. `?scene=N` plays the
story to scene N. `?expand=1` removes the internal scrollbars for a full-page screenshot.
`?source=1` opens the function source overlay. `?open=1` opens every disclosure except
the raw `stdout` blocks. A screenshot cannot select a disclosure, and the raw bytes bury
the reading they belong to.

Regenerate the proof with `capture-proof.sh` against a running server. It drives the story
through the API, so all nine images and the transcript come from one ledger:

```bash
uv run python prototype/webui-demo/app.py &
prototype/webui-demo/capture-proof.sh
```
