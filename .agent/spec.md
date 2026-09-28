# cement spec

## Intent

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior. In a chat-style deployment such as Open WebUI, one kind of task — an OCR extraction, say — is requested many times with slight variations (different documents, slightly different asks). Those requests and their supervised answers are retained in the background, and Cement is the process that realizes such a category can be routed to one deterministic function: a regular, if large, function that grows over time to cover the variations and edge cases as each is supervised, and that is deterministic once built and verified. When ready, an operator decides to route applicable requests to that function — or to sibling functions for other categories — so results depend less on probabilistic LLM processing. Aggregating repeated work this way would be hard to reach without LLMs; repetition alone never widens a rule beyond what was verified.

Production artifact = a library + CLI control plane that an interface like Open WebUI calls; not a web UI. Prototype artifact = a web UI demo that clarifies the purpose, the situations it serves, the output to expect, and how that output makes processes more efficient and predictable.

## Artifacts

Env + gate = `.claude/rules/ops.md`; stdlib-only Python ≥3.11 under `uv`.
- Prototype web UI demo — `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>; proof = `prototype/webui-demo/proof/` (10 PNGs + `transcript.txt`, all from ONE ledger via
  `prototype/webui-demo/capture-proof.sh`, which drives the story through the API because a
  `?scene=N` replay always restarts at scene 0).
- Library `src/cement_runtime/` (`from cement_runtime import System`) + CLI `uv run cement --help` (README quick start = the lifecycle: `operation register` → `proposal submit/review` → `compile` → `function verify-drafts/inspect/promote/verify/export/eval`, `resolve`).
- Hospital OCR example — `uv run python examples/hospital_ocr/run_demo.py` (`All checks passed.`; README transcript pinned).
- Gate — `uv run python -m unittest discover -s tests -t .` (1031 tests; wall time splits by `test_d28`'s replay range → `.claude/rules/ops.md`) + `uv build`. Instruments = `.agent/decisions/m<m>u<u>-*`.

## Decisions

- README paragraph 1 = authoritative scope; alignment moves the system toward it and never narrows it. Arc: M2 function-as-object (REVIEWED) → M3 trim to paragraph scope (IN-PROGRESS) → M4 projection inside the boundary (UNPLANNED).
- Trust boundary = exact lookup: scope = partition + operation revision + canonical JSON input; a function = a set of exact entries (`cement-function-v2`), never a wider predicate; only M4's verified projection artifact widens what one entry covers. Function identity = verified-content identity (`entry_seal` excludes promoter + time; activation provenance stays in the receipt).
- M3 seeds, owner-approved: (a) `CandidateSource` stays core while `CommandCandidateSource`, the subreaper supervisor, `example_adapter.py`, `docs/adapter-protocol.md` relocate to an optional example surface (M3.7); (c) request lifecycle (`handle`, leases, request-ID idempotency, `in_progress`/`retry_failed`/`fallback_failed`/`reconciliation_required`) replaced by `submit_proposal`/`propose` + pure read-only `resolve` (M3.3–M3.6a). Order c → a. Schema cuts ONCE, v2 → v3 at M3.6b, no migration pre-1.0; `SCHEMA_VERSION` 2 until then, private request rows = internal plumbing.
- `resolve` pays full P1-P6 verification per call, no cache; prose cites the measured numbers (`.claude/rules/runtime.md`), never "fast". Ambiguity quarantine leaves with `handle`.
- Exit classes 2/3/4/5/6, the per-leaf stdout channel + `allow_abbrev` scope → `.claude/rules/runtime.md`; root `verify` exit 0 = frozen precedent, never a model.
- Assurance: tier default `kernel`; `oracle` only where an independent implementation can diverge. A removal closes on a battery that fails when one obligation is undone or one preserved invariant disappears — never on a green suite. Each contract pins a NUMBERED gate list rerun from committed state; a gate added mid-unit voids the pins ⇒ linters/type checkers land at a unit boundary. Rulings enter tables through idempotent `--check` patchers; dispatch tips tagged `archive/m<m>u<u>-<role>`.
- Prototype (user): `prototype/webui-demo` = behavioral reference (UX, outputs, aesthetics), never IMPLEMENT's code base; retires at phase close. Light theme, accents ≥4.5:1 on white; the provider alone is simulated + labelled, lifecycle/digests/timings are the runtime's.
  Function source view (owner-ruled): the promoted set renders as a SOURCE-STYLE DISPATCH — one
  guarded branch per entry, provenance in a comment, an explicit no-match tail, excluded scopes as
  trailing comments — parsed back out of the exported bundle and labelled a rendering, since Cement
  seals exact entries and emits no code. Per-request history retains ONLY proposals that became
  confirmed examples; each entry drills down to the requests behind it, showing the plan the
  provider wrote and what the supervisor changed.
  Demo framing (owner-ruled): the prototype explains a concept and must never read as a
  production control plane. Layout = TWO HALVES, `what the user sees` | `none of this is
  visible in production`. The chat is a PLAIN chat — no badge, id, model name, digest or
  timing — so the supervised answer and the cemented answer render IDENTICALLY; that identity
  is the demonstration. A TURN is one question however many operations answer it: it renders as
  the typing indicator while the model writes, then answers in ONE bubble; a part that misses
  the promoted set returns to the model, and the user waits for the MODEL alone. The chat NEVER
  waits on a person: the model's answer goes out in that same turn and its candidate enters the
  review queue behind it, so a later accept/correct/reject decides what Cement may seal and
  never what the user already read. A correction therefore shows both — the reply the user got
  and the answer cemented instead — inside that message's disclosure, and a rejection retracts
  nothing. Chat kinds = `document | answer`. Every detail stripped from a bubble moves to a
  per-message `what happened under this` disclosure.
  The right half runs the operator lifecycle as REAL `cement` subprocesses against the demo
  ledger (`_cli`), printing the command, its rc and a condensed reading of the bytes it
  returned, with verbatim stdout + exact argv one click away; an argument over 80 chars prints
  as its shell variable (`--output "$OUTPUT"`), which keeps a 64-char digest visible because
  repeating it IS `function promote`. Chat-side submit + resolve stay IN-PROCESS and say so:
  measured subprocess 92-128 ms over one story's 50 calls vs `System.resolve` 3.5-6.0 ms in that
  same run (`prototype/webui-demo/proof/timings.txt`, rewritten by every capture run), so routing the chat through a shell would report interpreter startup as the
  function's cost. Per-entry drill-down = the FOUR REAL HOPS p67 names
  (`function inspect` → `artifact show` → `events` → `proposal show`),
  each a recorded invocation, with `originals` derived from `proposal show`'s own
  `proposed_output`/`final_output` rather than from session memory; `events` carries no example
  filter, so the join is done by hand and shown. Metrics keep the numbers and lose the stat
  tiles. Free interaction stays.
  Tasks + reuse (owner-ruled): the tray holds FIVE tasks a hospital worker brings to an in-house
  LLM, each carrying several rewordings of its own job — wording variation is WITHIN-task, never
  a route to another task. The LLM upstream absorbs the words and NAMES the operation; Cement
  stays rigid, keyed on operation + exact input, and never sees the request text ⇒ the
  ask → operation routing renders per message, labelled simulated. Five tasks resolve to FOUR
  cementable operations: `file` → `extraction_plan`, `share` → `+ phi_locators`, `check` →
  `+ required_fields`, `route` → `intake_queue`, `bill` → `+ billing_codes`.
  The right half is SCOPED to the selected task while the operation map shows all five, so reuse
  is portrayed BOTH ways: the function card names its callers, and switching tasks lands on the
  same card. A turn's parts may split across a promoted function and the model, and the bubble
  hides that seam. `document.billing_codes` is keyed on one note's ASSESSMENT TEXT, not the
  layout, so no second note repeats the input, every scope stays at support 1, `compile` blocks
  it, and it stays supervised BY DESIGN — the boundary is the claim, not a gap. The story cements
  every cementable task.
- Human-facing prose (README, `docs/`, example README, CLI help) = ASD-STE100 register, graded by D25; everything else agent-optimized.
- Gate tooling (owner-ruled; lands at a unit boundary): mypy 2.3.1 `strict` over `src/cement_runtime` alone; ruff 0.16.6 format + check, `extend-exclude = ["tests", ".agent", "prototype"]`; scanners = `uv audit` (native, OSV/SARIF) + gitleaks Action + ruff `S`; `license = "Apache-2.0"`; CI = GitHub Actions + Dependabot (`uv` + `github-actions`). The gate-tooling unit also carries p66's standing skip census, owner-approved: both are gate changes that one boundary covers. Grounds, config + firing seeds → `.claude/rules/ops.md`; checker + CI measurements → `.agent/decisions/m3u10-*`. `github.com/eturkes/cement` is PUBLIC ⇒ `push`/`pull_request` carry the gate, a cron alone is disabled after 60 idle days.

## Tasks

- [ ] M3.6a3 delete the 7 dead outcome types (`Outcome` + its 6 members).
  - `src/` holds zero constructors, only `models.py` defs, `__init__.py` import/`__all__`, one `system.py` docstring. `CandidateRequest.request_id` STAYS — live on the `cement-source-v1` envelope — and leaves with M3.6b's single schema/protocol cut.
  - Accept: burden re-measured on its own deletion set; battery per contract.
- [ ] M3.6b schema cut v2→v3 (direct proposal columns, `requests` + index gone, refusal fixtures, 0.2.0); owns p50 p51 p04.
  - Accept: fingerprint + `SCHEMA_VERSION` move together, suite green with the reset documented.
- [ ] M3.7 command-runtime relocation under byte equality + blocked reverse imports; owns p54.
  - The wheel already carries no `examples/`/`tests/`.
- [ ] M3.8 demo + transcript regeneration via idempotent updater (`data`).
- [ ] M3.9a docs claim ledger rewrite (`docs`).
- [ ] M3.9b independent replay of the M3.9a rewrite (`docs`).
- [ ] M4 projection inside the boundary — plan, open design question + seeds in `.agent/archive/roadmap.md`.
  - Accept: planned as a milestone.
- [ ] Gate tooling + CI + scanners = p01 p66 + the IMPLEMENT law gap (no CI, no scanners, no update automation), per the `Decisions` gate-tooling ruling.
  - Accept: one gate command rc 0 clean-tree; `RUF100` zero; a seeded violation reds EACH of format, lint, type check, audit, secret scan, skip census — `uv audit` sees 0 third-party packages today, so its seed is a pinned vulnerable dev dep in a fixture lock, and the census seed is a fourth skip reddening it by test id.
- [ ] Committed dev tools p02 p05 p06 p19 (mutation replay, anchor validators, seam battery) + p12 p40 (human-facing register audit).
  - Accept: each reruns from a clean checkout; the audit flags a seeded 30-word instruction + a seeded `simply`, zero over-cap sentences on the four surfaces.
- [ ] Scope expansion p34 p35 p36 p37; reviewer identities, encryption, retention, remote registry/signatures; shadow sampling + drift telemetry; TypedDict projections; absolute URLs before publication.
  - Accept: planned as milestones.
- [ ] README + `prototype/` retirement.
- [ ] Phase-close `reviewer` over the whole phase diff.
  - Runs LAST, nothing mutating after it; each unit's closing diff draws its OWN `reviewer` first and every pass adjudicates into `.agent/review.md` ⇒ never the only pass.
- Queue = `.agent/deferred.md` (`p<nn>`, one line + acceptance each, unattached; p01-p61 keep full text + evidence + grounds in `.agent/archive/polish.md`, a born row's line is its whole record; grader `uv run python .agent/decisions/m3-deferred-validate.py`); a bare `p<nn>` in a row = that unit owns the queue row.

## Phase

ITERATE. M3.6a2 closed and landed on main as `ffe9848`, green on the FULL gate with `test_d28`
included (`Ran 1031 tests in 1056.911s` `OK`, `uv build` rc 0; outer skipped + not-run = none,
nested D28 = L30 skipped in every inner replay by construction; missing = format, lint, type
check, dependency audit + secret scan, all five pending the gate-tooling unit). The `CLAUDE.md`
refresh landed as `a8109eb` + `81fad11` and reran that gate whole from EACH: `Ran 1031 tests` in
1113.706s and 1015.317s, `OK` rc 0, `uv build` rc 0, same exclusions both times. The IMPLEMENT
spine (`Tasks`) is
SUSPENDED INTACT, not retired — `Decisions` and every unfinished unit stand as written, and the
ITERATE outcome amends them where it lands. Reason for the return, owner-ruled: prototype
feedback.

ITERATE opens by running the artifacts + refreshing proof, then works the owner's feedback into
`prototype/` + `Decisions`. These are interactive sessions until the owner says go. Start with `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>.
A prototype-only turn owes no gate run (`.claude/rules/ops.md`, census bullet); it owes a
`capture-proof.sh` rerun, since every proof PNG that shows the Function pane goes stale with the
UI.

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
`index.html`/`app.js`/`app.css`/`capture-proof.sh`/`README.md`. Verified by driving the story
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
empty server log. `proof/` = 10 PNGs + `transcript.txt` (127 lines) plus `timings.txt`, from ONE ledger in 88 s, `02-held` retired for `02-answered`, and
`sha256sum proof/*.png | awk '{print $1}' | sort | uniq -d` EMPTY — the filename must be
stripped, since whole-line `uniq -d` never fires — against a positive control reporting 1.

Capture heights are no longer eyeballed: `prototype/webui-demo/measure-height.mjs` reports the
viewport the right column needs (or the fixed overlay card, whose body scrolls inside it), and
`capture-proof.sh` measures immediately before each NUMBERED capture (the closing full-page image
needs no height), so a UI change cannot leave a stale number behind. It reproduced all eight previously eyeballed heights within 20 px and the overlay
card at 6095 against the recorded 6100.

Resume IMPLEMENT at M3.6a3 when the owner says go.

Suspended IMPLEMENT order = `Tasks` top to bottom, resuming at its head; the phase-close `reviewer` row hands over to MAINTAIN.
