# Cement web UI demo

This demo shows what Cement is for. Users at a hospital send scanned documents to a chat
assistant. They bring five different jobs, and they word each job differently every time.
The AI answers each request with a small script. From time to time, a learning pass reads
the retained chats, finds the requests that recur, and merges their scripts into one
deterministic function per job. A person reads a function and switches it on or off. While
a function is on, matching requests no longer depend on the AI.

This page is a demo, not a product. Cement ships as a library and a CLI. A production
deployment puts Cement behind a chat product such as Open WebUI, where none of this
reaches the person typing.

The page opens with one headline and three icons: **Ask**, **Learn** and **Switch on**.
The icons also show the step that the selected task has reached. A band under the icons
tells you what just happened, and it holds the next action.

The left half is the chat that users see. Until a function covers a request, each answer is
an ordinary chatbot answer. When a function answers, a tool-call line such as
`ƒ Used document.extraction_plan` shows above the reply.

The right half shows the latest request in three boxes: the form, the script used on it,
and the reply. An amber **AI script** chip marks a script that the AI wrote. A green
**Function** chip marks a learned function that ran without the AI. A function holds a
script for each kind of form, so plain code can read a new patient's form with it. Below the
boxes, **Functions** lists the functions of the selected task. Each function has a **Read**
button and its own switch.

**Show technical details** opens the per-message details, the scanned text and the
**Operator view**, which holds the commands, the evidence and the function source.

## Run

```bash
uv run python prototype/webui-demo/app.py
```

Open <http://127.0.0.1:8765/>. Select **Play the story** for a guided tour. Each step dims the page and lights up one
part of it, with a short note beside it. Select **Next** in the note to go on. Select the
**×** in the note or **Leave the story** to stop.
Stop the server with Ctrl+C. The ledger is a temporary SQLite file, and it disappears with the
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
the floor of two answers, and the learning pass turns them into functions.
`document.billing_codes` is decided by the words of one assessment. No second note repeats
those words. Every case therefore stays at one answer, the compiler blocks it, and the model
keeps answering.
That is the design, not a gap.

One function serves several tasks. **File it into the record** promotes
`document.extraction_plan`. Three later tasks then reach the same function for free.

## What to watch

1. Select a task, then send one of its requests. The chat answers at once, as an ordinary
   chatbot.
2. Send another form of the same kind. The AI writes a slightly different script.
3. Select **Learn from chats**. The learning pass merges the scripts into one function.
4. Select **Read** to see the function. It has one branch for each kind of form, and it
   asks the AI for anything else. A **shared** row came from every script. A **from A02**
   row came only from the requests that needed it. That union is how one function covers
   all of the requests.
5. Select **Switch on**. The next form of that kind gets its answer without an AI call. The
   reply is the same, and a tool-call line above it shows that the function answered.
6. Select **Code it for billing**. **Switch on** is struck through, because no two notes
   repeat the same words.
7. Select **Show technical details** for the commands, the evidence and the function source.

## Third-party code

The tour uses [driver.js](https://driverjs.com/) 1.10.2 under the MIT license. Its browser
build, its style sheet and its license are copied into `static/vendor/driver.js-1.10.2/`
from the npm package, which was checked against the registry integrity hash. The demo needs
no build step and no network access.

## Real and simulated

The model is simulated. `StubProvider` in `demo.py` returns a fixed script and samples one
latency between 1.1 and 3.4 seconds. The first script for a kind of form reads less than the
next one, for example no Provider row on the first progress note. The learning pass is simulated too: it merges the
scripts of each case into that case's reference answer, and it reviews each retained answer
as `learning-pass`. Compile, verification and promotion after it are real. It calls no model and uses no network. The page
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
story run. `System.resolve` costs 3.5 to 6.0 milliseconds in that same run. A subprocess
would therefore report startup cost as the function's cost. `capture.sh` prints both
costs for each run that it drives.

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

## Scope

This is a prototype. It shows behavior, and it is not the production shape. The library
and the CLI are the shipped artifacts. Read the [repository overview](../../README.md) for
the guarantees, and [docs/architecture.md](../../docs/architecture.md) for the state model.

Query parameters help with capture. `?reset=1` starts a new ledger. `?scene=N` plays the
story to step N + 1. `?expand=1` removes the internal scrollbars for a full-page screenshot.
`?source=<operation>` opens the source overlay for that promoted operation.
`?drawer=<operation>` opens the drawer for that operation. `?tech=1` shows the technical
details, and `?drawer`, `?source` and `?open` also show them. The source overlay opens the
lineage of its first entry, because a screenshot cannot select a disclosure.

## Visual check

`capture.sh` drives the story through the API against a running server. It captures
every frame from one ledger into `.scratch/webui-demo-capture/`, which git ignores. Set
`OUT` to write to a different directory.

The visual check needs two tools that this repository does not supply. `capture.sh` calls
`webcap`, a command that captures a page in headless Chromium. Put `webcap` on `PATH`, or
set `WEBCAP` to its path. `measure-height.mjs` and `density.mjs` load the `chromiumfish`
Node package. Set `CHROMIUMFISH_DIR` to the package directory, which holds `dist/index.js`.
The `.agent/deferred.md` row `p79` records the move to a browser that the demo installs.

```bash
export CHROMIUMFISH_DIR=/path/to/node_modules/chromiumfish
uv run python prototype/webui-demo/app.py &
prototype/webui-demo/capture.sh
```

Each numbered frame must show its claim:

| File | What it shows |
|---|---|
| `01-desk.png` | The headline, the three icons and five tasks before the first request. |
| `02-answered.png` | An ordinary chatbot answer, and **Learn from chats** in the band. |
| `03-evidence.png` | A second progress note, with a slightly different AI script. |
| `04-cemented.png` | A learned function that is off, with **Switch on** in the band. |
| `05-routed.png` | A03 answered without the AI: the same reply under a tool-call line. |
| `06-reuse.png` | One answer from a function and the AI together, under one tool-call line. |
| `07-blocked.png` | Billing stays with the AI because assessment words do not repeat. |
| `08-bundle.png` | The extraction plan drawer, with the answer from the exported bundle. |
| `09-source.png` | The function read as source, with the four hops behind one entry. |

The run also writes `story-full-page.png`, the whole page at the end of the story.
`transcript.txt` holds the ledger events of the run, and `timings.txt` holds its
subprocess and resolve costs. The script also prints the costs. The server serves the
live log at `/api/transcript.txt`.

The script measures every numbered frame with `measure-height.mjs`, immediately before
its own capture. The final full-page image needs no height. Both columns scroll inside
the page, so a block below the fold is absent from the file.
