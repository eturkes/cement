# Cement web UI demo

This demo shows what Cement is for. Hospital staff send scanned documents to a chat
assistant. They bring five different jobs, and they word each job differently every time.
A supervisor reviews those answers afterwards. Cement collects that confirmed work into
one deterministic function per operation. An operator then routes those operations to their
functions, and the answers stop depending on the model.

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

## Five tasks, four functions

The tray holds five tasks. Each task carries several requests that ask for one job in
different words.

| Task | Operations it calls |
|---|---|
| File it into the record | `document.extraction_plan` |
| Send it to an outside specialist | `document.extraction_plan` + `document.phi_locators` |
| Check the form before I accept it | `document.extraction_plan` + `document.required_fields` |
| Where does this go? | `document.intake_queue` |
| Code it for billing | `document.extraction_plan` + `document.billing_codes` |

The model absorbs the wording. It reads each request, names the operation, and hands
Cement one exact input. Cement never sees the words. Cement stays rigid on purpose. It
answers an operation and an exact input, and nothing else.

Four operations are decided by the document layout. Their inputs repeat, so they reach
the confirmation floor and they cement. `document.billing_codes` is decided by the words
of one assessment. No second note repeats those words. Every scope therefore stays at one
confirmation, the compiler blocks it, and the model keeps answering under supervision.
That is the design, not a gap.

One function serves several tasks. **File it into the record** promotes
`document.extraction_plan`. Three later tasks then reach the same function for free.

## What to watch

1. **The chat stays plain, and it never waits for a person.** The left half shows an
   attachment, a request and an answer. It shows no proposal ID, no model name, no
   digest and no timing. The model answers the user at once. The supervisor reads that
   candidate afterwards, which is where the review queue on the right comes from.
2. **The wording varies and the task does not.** `Extract the record fields as JSON.` and
   `Give me the JSON for the record fields.` reach the same operation. The right half
   names that operation under **one task at a time**.
3. **Each message opens.** Select **what happened under this** below any message. The
   machinery that the chat hides appears there: the exact input Cement keys on, the
   answer each operation returned, the digests, and the commands. A corrected answer
   also shows what the supervisor cemented instead. The user keeps the answer the model
   wrote, and that exposure is what cementing removes.
4. **The operator works in a terminal.** The right half runs the real `cement` binary
   against the demo ledger. Each row shows the command, a short reading of what it
   returned, and the exit code. Select the `stdout` line for the verbatim bytes and the
   exact argument list.
5. **Evidence accumulates.** Documents A01, A02 and A03 hold different patients, but they
   share one layout signature. That signature is the scope. The patient values never
   enter it.
6. **The scope becomes a function.** Select `compile`, `function verify-drafts` and
   `function promote`. Compile groups the confirmed examples. Verification replays them.
   Promotion makes the operator repeat the digest that `function inspect` reported.
7. **The operator routes the promoted operations.** Turn on operator routing. Document
   A03 then resolves from the promoted set in milliseconds, with no model call.
8. **The supervised answer and the cemented answer are identical.** A model answers A02,
   and a person confirms that candidate afterwards. The promoted function answers A03.
   The two bubbles render the same. That identity is the point.
9. **One function serves the next task.** Switch to **Send it to an outside specialist**.
   The extraction plan resolves from the function it already has, and only the identifier
   map reaches the model. One answer, two sources, no visible seam. The function card
   names every task that calls it.
10. **The boundary holds.** Run **Code it for billing**. The terminal shows
    `blocked  one note's assessment text (A01) - support 1 is below required 2`. Cement
    widens nothing on its own.
11. **The function travels.** Download the bundle, or answer A03 from the bundle bytes
    alone. The bundle carries no ledger.
12. **The function is readable.** Select **read the function**. The overlay shows the
    promoted set as one function: one guarded branch per entry, and a no-match tail. Each
    branch opens to the four commands that rebuild its lineage, and then to the requests
    themselves. Compare `proposed_output` against the entry that now answers.

## Real and simulated

The model is simulated. `StubProvider` in `demo.py` samples one answer variant and one
latency between 1.1 and 3.4 seconds. It calls no model and uses no network. The page
labels that number `simulated`. The mapping from a request to an operation is simulated
for the same reason. A deployment gives that reading to the model.

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
subprocess costs 92 to 128 milliseconds of interpreter startup, over the 50 calls of one
story run. `System.resolve` costs 3.5 to 6.0 milliseconds in that same run.
`proof/timings.txt` records both, from the run that produced `proof/`. A subprocess
would therefore report
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
`examples/hospital_ocr/`. Document B03 is derived in `demo.py` from an example file, with
one required line blanked. The blank leaves the layout signature unchanged, so B03 shares
a scope with B02 and still reads as incomplete. The demo enters the pipeline at
`submit_proposal`.

## Proof

The `proof/` directory holds the evidence from one recorded run:

| File | What it shows |
|---|---|
| `01-desk.png` | Five tasks, and every operation before the first request. |
| `02-answered.png` | The answer already with the user, and its candidate waiting for review. |
| `03-evidence.png` | Two confirmations against one layout signature. |
| `04-cemented.png` | The promoted set, its hash and the six checks. |
| `05-routed.png` | A03 answered from the function, in a bubble that looks supervised. |
| `06-reuse.png` | One answer from two sources, and a function with four callers. |
| `07-blocked.png` | Four operations sealed, and the fifth blocked by design. |
| `08-bundle.png` | The answer from the exported bundle. |
| `09-source.png` | The function read as source, with the four hops behind one entry. |
| `story-full-page.png` | The whole page at the end of the story. |
| `transcript.txt` | The ledger events of the same run. |
| `timings.txt` | The subprocess and resolve costs of the same run. |

The server also serves the live log at `/api/transcript.txt`.

## Scope

This is a prototype. It shows behavior, and it is not the production shape. The library
and the CLI are the shipped artifacts. Read the [repository overview](../../README.md) for
the guarantees, and [docs/architecture.md](../../docs/architecture.md) for the state model.

Query parameters help with capture. `?reset=1` starts a new ledger. `?scene=N` plays the
story to scene N. `?expand=1` removes the internal scrollbars for a full-page screenshot.
`?source=<operation>` opens the source overlay for that promoted operation. `?open=1`
opens every disclosure except the raw `stdout` blocks and the lineage of later entries. A
screenshot cannot select a disclosure. The raw bytes bury the reading they belong to, and
the later entries repeat a lineage the first entry already shows.

Regenerate the proof with `capture-proof.sh` against a running server. It drives the story
through the API, so all ten images and the transcript come from one ledger:

```bash
uv run python prototype/webui-demo/app.py &
prototype/webui-demo/capture-proof.sh
```

The script measures every numbered frame with `measure-height.mjs`, immediately before
its own capture. The final full-page image needs no height. Both columns scroll inside the page, so a block below the fold is simply
absent from the file.
