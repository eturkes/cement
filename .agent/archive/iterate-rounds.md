# ITERATE return — archived `Phase` narrative

`.agent/spec.md` `Phase` body at `b8a0703` (lines 115-215), moved verbatim when the agents@5e03db6
template refresh set `Phase` = state alone in the routed-state form (`CLAUDE.md` `Session flow`
`Routed state`). The route: owner request "I want to return to the ITERATE stage" (session
`08cfd0c7`, 2026-09-10T01:38:21Z); its `AskUserQuestion` rulings = why `Prototype feedback`,
`impl/m3u6a2b` `Finish, then switch`, spec `Suspend, keep intact`.

## `Phase` at `b8a0703`, verbatim

ITERATE — whole product. M3.6a2 closed and landed on main as `ffe9848`, green on the FULL gate with `test_d28`
included (`Ran 1031 tests in 1056.911s` `OK`, `uv build` rc 0; outer skipped + not-run = none,
nested D28 = L30 skipped in every inner replay by construction; missing = format, lint, type
check, dependency audit + secret scan, all five pending the gate-tooling unit). The `CLAUDE.md`
refresh landed as `a8109eb` + `81fad11` and reran that gate whole from EACH: `Ran 1031 tests` in
1113.706s and 1015.317s, `OK` rc 0, `uv build` rc 0, same exclusions both times. The IMPLEMENT
spine (`Tasks`) is
SUSPENDED INTACT, not retired — `Decisions` and every unfinished unit stand as written, and the
ITERATE outcome amends them where it lands. Reason for the return, owner-ruled: prototype
feedback.

Each ITERATE session runs one pasted `iterate.md` body: it opens by running the prototype
artifacts, then works the owner's feedback into `prototype/` + `Decisions` in rounds until the
owner's go, its `Met when`. Start with `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>.
A prototype-only round owes no gate run (`.claude/rules/ops.md`, census bullet); it owes a
`prototype/webui-demo/capture.sh` run read frame by frame, since every frame that shows the
Function pane changes with the UI. The close owes the full gate (`iterate.md` `Met when`).

Feedback landed so far, all worked into `prototype/` + `Decisions`:
1. The demo showed the CEREMONY around the function and never the function — the per-request plan
   was visible only while its proposal was pending, and the promoted set showed a count plus a
   hash. Answered by the function source view; owner picked source-style dispatch over an entry
   table, and entry-feeding requests only over every attempt.
2. The intake assistant was busier than a real chat, and the page as a whole read as a production
   control plane rather than an explanation. Answered by the two-halves framing, the plain chat,
   the per-message peel-back, and the real-CLI right half (`Decisions`, demo-framing bullet).
3. The page carried ONE task worded ONE way under a `send a scanned document` heading, so it read
   as a single-purpose OCR toy and no function ever served a second caller. Answered by five
   tasks with within-task rewordings, per-message ask → operation routing, an operation map
   beside the selected task, and function cards naming their callers (`Decisions`, tasks + reuse
   bullet).
4. The chat hung on `working…`: `send` ended a turn in a `held` state and only `review` released
   the answer, so the first request a visitor clicked waited on an operator click whose control
   sat below the fold. Answered by the ruling that the chat behaves like any LLM chat — the
   model answers in the same turn and supervision moves behind it (`Decisions`, demo-framing
   bullet). The hold also broke the identity claim it was framed by: the cemented path answered
   in ~4 ms unattended while the supervised path answered never.

Shipped for (2): `demo.py` `_cli`/`_display`/`_hops`, rewritten `index.html`/`app.js`/`app.css`
+ `prototype/webui-demo/README.md`. Verified by driving the story through the API on a live
server — real `cement` subprocesses, every rc 0; 5 hops per entry (4 distinct commands,
`proposal show` once per original); the block read off the real `compile`; offline bundle match
on A03; empty server log.

Shipped for (3): `demo.py` — `_bundle_target` + `bundle(operation)`, `_queue` (spelled `_hold` then) carrying
`scope_label`/`preview`, `_row_name` over `field`|`code`|`name` (a dict-shaped billing row
crashed the old `item["field"]`), `_promote_one` refusing to reseal an operation an earlier task
already promoted, `state().operations` feeding the coverage strip; `app.py` — `/api/bundle.json`
and `/api/offline` per `operation`, 409 where that operation is unpromoted; rewritten
`index.html`/`app.js`/`app.css`/`capture.sh`/`README.md`. Verified by driving the story
through the API on a live server: 75 real `cement` subprocesses — 50 operator rows + 25 lineage
hops over 5 sealed entries — every one rc 0; 9 provider calls, 4 cemented answers, 11 reviews,
`document.extraction_plan` sealed with 2 entries and
`phi_locators` + `required_fields` + `intake_queue` with 1 each, while
`document.billing_codes` blocked at `one note's assessment text
(A01) - support 1 is below required 2` — the boundary the fifth task exists to show. `06-boundary`
+ `07-bundle` + `08-source` retired for `06-reuse` + `07-blocked` + `08-bundle` + `09-source`. Webfonts load AFTER first paint and change line heights,
so `app.js` awaits `document.fonts.ready` before rendering — without it every auto-scroll landed
short and the chat cut its own last bubble.

Shipped for (4): `demo.py` — `send` finishing every turn itself, `_hold` → `_queue` setting the
part from the model's own candidate, `_finish` retaining the turn with its bubble, `_refuse`
replaced by `_record_review` (a ruling restates that message's peel-back in place and the bubble
is never rewritten), `REVIEW_READING` over `unreviewed|accepted|corrected|rejected`, and a
corrected part carrying a second block for what got cemented instead; `app.js` — the typing
indicator driven by `STATE.thinking` alone, the `held`/`refused` branches gone, `sent, unreviewed`
on the review card. Verified on a live server: one send answers in 1.68 s with the candidate
queued; `correct` afterwards leaves the answer bytes identical (`cmp` rc 0) while the peel-back
restates and gains the cemented plan; `reject` adds no bubble and the answer already sent
stands; a two-operation turn still
lands as ONE bubble. The full story = 10 turns, 10 `document` + 10 `answer` messages and NO other
kind, 9 provider calls, 4 cemented answers, 11 reviews (7 corrected, 4 accepted), 50 operator
rows, `System.resolve` 3.5-6.0 ms, 4 of 5 operations sealed, `billing_codes` blocked as designed,
empty server log. The capture = 10 PNGs + `transcript.txt` (127 lines) plus `timings.txt`, from ONE ledger in 88 s, `02-held` retired for `02-answered`, and
its `sha256sum *.png | awk '{print $1}' | sort | uniq -d` EMPTY — the filename must be
stripped, since whole-line `uniq -d` never fires — against a positive control reporting 1.

5. The page was incredibly dense and hard to understand: ten stacked right-half sections, 15
   prompt cards, a 64-char hash and six check rows on every function card. Answered by the
   board layout (`Decisions`), owner-picked from three variants (stepper, board, chat-twin).

Shipped for (5): rewritten `index.html`/`app.js`/`app.css`, `capture.sh` (`08-bundle` opens the
drawer via `?drawer=`), `README.md`, new `density.mjs`. `demo.py` = `operations[].support` (per-scope confirmations, unscoped by task, so an unselected row keeps its real count); `app.py` unchanged.
Verified by `capture.sh` rc 0, 10 PNGs read, duplicate-hash scan empty; density reset
259/282/17 + story end 311/338/18 against 545/774/24 + 571/3947/27.

Capture heights are no longer eyeballed: `prototype/webui-demo/measure-height.mjs` reports the
viewport the right column needs (or the fixed overlay card, whose body scrolls inside it), and
`capture.sh` measures immediately before each NUMBERED capture (the closing full-page image
needs no height), so a UI change cannot leave a stale number behind. It reproduced all eight previously eyeballed heights within 20 px and the overlay
card at 6095 against the recorded 6100.

6. The right half stayed too dense to understand: board grid, review inbox, routing switch +
   `What this buys`, and the drawer were all opaque. Answered by the story layout
   (`Decisions`), owner-picked from three variants (plain board, story, counter + rulebook);
   tips `archive/iter-r6-{plain,story,counter}`. Verified by `capture.sh` rc 0, frames read,
   duplicate-hash scan empty; 50 subprocesses 98-123 ms, `System.resolve` 3.4-5.5 ms.

Next ITERATE session = round 7 on the story layout. Resume IMPLEMENT at M3.6a3 when the owner says go.

Suspended IMPLEMENT order = `Tasks` top to bottom, resuming at its head; the phase-close review row hands over to MAINTAIN.

## Rounds r5-r17, closed on the owner's go (ITERATE → IMPLEMENT)

`Tasks` rows as they stood at the close, verbatim; later rounds r12-r17 = `b5ff826`, `fb1d7b7`, `314074f`, `215647c`, `33d6812`, `6f8c858`, `d34548c`, `6b90eb9`.

- [x] 2547505 ITERATE round 5: UI dense → `board` picked over `guided` + `mirror` (`Decisions` board-layout ruling); merged, retired.
- [x] d9fe5df ITERATE round 7: still dense + confusing → layperson framing (purpose sentence, four-step workflow, technical details behind one switch).
- [x] 46c95e8 ITERATE round 8: still unclear what happens → mechanism boxes, `What just happened` captions, narrated story, readable replies; ba5230d `staff` → `users`.
- [x] 8722f0b ITERATE round 9: too wordy → icon workflow as progress, one-line band + one action, chips/dots/marks in the boxes.
- [x] cbafe70 ITERATE round 10: audience needs gaze guidance → driver.js spotlight beats on the story; b7757b5 captions without file ids.
- [x] 002c68d ITERATE round 11: ordinary-chatbot captions + tool-call line; 548e00b mistake-stake captions.
- [ ] ITERATE round 12: human role corrected (Intent rewritten) → Ask → Learn → Switch on, learning pass = sole reviewer, per-function switch + `Read`; r13 generalization shown (`shared` / `from <request>` rows); owner's go at the close.
  - Rules upkeep ran at the close: `ops.md` compressed, D28/D19 law → `history-gates.md`, capture mechanics → `prototype.md`.
