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
button and its own switch. The switch writes the runtime's real setting: **on** selects
`follow`, and **off** selects `off`. A function in `follow` uses each new version that the
learning pass publishes. Learning never changes the switch.

**Show technical details** opens the per-message details, the scanned text and the
**Operator view**, which holds the commands, the evidence and the function source. In that
view, **Read the function** also shows the versions and the change from the previous version.
These are the results of `function versions` and `function diff`, with their commands and
verbatim output. The version history is read-only. The library supports pins and rollback;
this demo exposes only the on/off switch.

## Run

```bash
uv run python prototype/webui-demo/app.py
```

Open <http://127.0.0.1:8765/>. Select **Play the story** for a guided tour. Each step dims the page and lights up one
part of it, with a short note beside it. Select **Next** in the note to go on, or **Back**
to go to the previous note. Going back to an earlier step restores the state that the demo
saved when that step ended, so the page shows the same state as before. If no saved state
exists for that step, the demo runs the story again up to that step, without the simulated
wait. Select the **×** in the note or **Leave the story** to stop.
Stop the server with Ctrl+C. The ledger is a temporary SQLite file, and Ctrl+C removes it with
the process. A server that a signal such as `SIGTERM` stops leaves its `cement-demo-*` directory
in the system temporary directory. Remove that directory by hand.

## Japanese

Select **日本語** in the header to show the page in Japanese. Select **English** to go back.
The language switch keeps the state of the demo. You can also open
<http://127.0.0.1:8765/?lang=ja> directly.

The Japanese page translates the headings, the buttons, the labels, the band and the story
notes. The forms, the requests, the replies and the scripts stay in English, because they are
the contents of the chat. The technical details and the code in the **Read** view also stay in
English. The page uses the Japanese font of your operating system. No native speaker has
reviewed the Japanese text.

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
`document.billing_codes` is decided by the words of one assessment. Two different notes do
not share those words. Each case therefore stays at one answer, the compiler blocks it, and the
model keeps answering.
That is the design, not a gap. If you send the same note again, that is an exact repeat, and the
learning pass turns it into a function like any other case.

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
6. Select **Code it for billing**. **Switch on** is struck through, because two different
   notes do not repeat the same words.
7. Select **Show technical details** for the commands, the evidence and the function source.

## Third-party code

The tour uses [driver.js](https://driverjs.com/) 1.10.2 under the MIT license. Its browser
build, its style sheet and its license are copied into `static/vendor/driver.js-1.10.2/`
from the npm package, which was checked against the registry integrity hash. The demo needs
no build step and no network access.

The page uses the Space Grotesk and JetBrains Mono fonts under the SIL Open Font License 1.1.
The latin font files come from the npm packages `@fontsource/space-grotesk` 5.3.0 and
`@fontsource/jetbrains-mono` 5.3.0, which were checked against the registry integrity hash.
The license of each family is copied from its package into `static/fonts/` as
`LICENSE-space-grotesk` and `LICENSE-jetbrains-mono`.

## Real and simulated

The model is simulated. `StubProvider` in `demo.py` returns a fixed script and samples one
latency between 1.1 and 3.4 seconds. The first script for a kind of form reads less than the
next one, for example no Provider row on the first progress note. The learning pass is
simulated too. It reads `learn cases` and reviews the retained answers as `learning-pass`.
When a later script extends an extraction plan or identifier map, `example supersede`
replaces the earlier confirmation with the merged plan. The earlier example stays with its
version. Only the replacement counts for the next build, so each request counts once.
Other stand-in answers contain fixed mistakes that the pass corrects to the reference answer.
Compile, verification, version publication and switching are real. The demo calls no model
and uses no network. The page labels the model latency and learning pass as simulated.
The mapping from a request to an operation is simulated for the same reason. A deployment
gives that reading to the model.

Everything else is the shipped `cement_runtime`:

- The proposals, reviews, confirmed examples, drafts, verification reports, promotions and
  receipts are real ledger rows.
- The lifecycle runs as real `cement` subprocesses against the same ledger. Only
  `operation register` creates the ledger. The pass reads, reviews, supersedes, compiles,
  verifies drafts, inspects the prospective function, and promotes that function by hash.
  Each promotion creates a version receipt. The page prints what each command returned.
- Each function starts off. The switch calls `function switch` with the person's actor.
  Chat calls `System.resolve` even while the switch is off; the runtime decides whether
  to return a function answer or a miss. The operator view is read-only apart from these
  switches: no person rules on a single answer.
- The policy uses the runtime defaults: two confirmations, one reviewer and no minimum span.
- The artifact digests, the `function_hash` and the seven set checks come from those
  commands.
- The exported bundle is the real `cement-function-v3` document. The demo exports the
  latest published receipt with `--receipt-id`, so you can read it before switching it on.
  This read does not enable the function. Without that option, the CLI exports the version
  that the switch selects, and it refuses while the switch is off.
- The function source overlay parses that bundle back and reads its entries. The `def`
  and `if` lines are a rendering for the reader. Cement seals exact entries, and it emits
  no code.

Two calls stay in process, and the page says so where it shows them. The chat submits a
proposal and resolves an input through the library, not through a subprocess. A subprocess
adds interpreter startup to the work. `capture.sh` prints both costs for each run that it
drives. Its resolve sample includes switched-off calls, which perform no verification,
and enabled calls, which verify the selected function.

A long argument prints as its shell variable, such as `--output "$OUTPUT"`. The exact
argument list stays under the `stdout` disclosure. The bound is 80 characters, so a
64-character digest still prints in full. Repeating that digest is what `function promote`
requires.

Walking one entry back to its requests costs four commands, and the overlay runs all of
them: `function inspect` gives the artifact ID, `artifact show` gives the example IDs,
`events` gives the proposal IDs, and `proposal show` gives `proposed_output` beside
`final_output`. The event join follows each supersession back to the original review.
The overlay keeps that earlier confirmation and shows the merged answer from `artifact show`.
No command prints an entry beside its originals, and `events` accepts no example filter,
so the join is done by hand. The demo reads every event page. `.agent/deferred.md` row `p67`
records that gap.

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
details, and `?drawer`, `?source` and `?open` also show them. `?lang=ja` shows the page in
Japanese. The source overlay opens the
lineage of its first entry, because a screenshot cannot select a disclosure.

## Visual check

`capture.sh` drives the story through the API against a running server. It captures
every frame from one ledger into `.scratch/webui-demo-capture/`, which git ignores. Set
`OUT` to write to a different directory.

The visual check uses its own browser: a pinned Playwright and its headless Chromium.
Install them once with the first command below. The command needs Node.js and pnpm. It
writes only to `prototype/webui-demo/node_modules/`, which git ignores. `capture.sh`,
`measure-height.mjs`, `density.mjs` and `quality.mjs` all use that browser through `browser.mjs`.
`quality.mjs` checks reduced motion, a 390 px viewport, keyboard focus and text contrast.

```bash
pnpm --dir prototype/webui-demo install
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
| `07-blocked.png` | Billing stays with the AI because each note has its own assessment words. |
| `08-bundle.png` | The extraction plan drawer, with the answer from the exported bundle. |
| `09-source.png` | The function read as source, with the four hops behind one entry. |

The run also writes `story-full-page.png`, the whole page at the end of the story.
`transcript.txt` holds the ledger events of the run, and `timings.txt` holds its
subprocess and resolve costs. The script also prints the costs. The server serves the
live log at `/api/transcript.txt`.

The script measures every numbered frame with `measure-height.mjs`, immediately before
its own capture. The final full-page image needs no height. Both columns scroll inside
the page, so a block below the fold is absent from the file.
