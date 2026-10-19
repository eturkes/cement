# cement spec

## Intent

Cement turns repeated LLM work into narrowly scoped deterministic functions. In a chat deployment such as Open WebUI, one kind of task — an OCR extraction, say — is requested many times with slight variations (different documents, slightly different asks). The LLM answers each request, often by writing a small script, and the requests and answers are retained in the background. Periodically, an LLM-driven learning pass reads those transcripts, finds the requests that recur, and combines their slightly different scripts into one deterministic function that covers every case it has seen: a regular, if large, function that grows as new variations appear, each case kept exact. A person can read the function and decides whether to switch it on or off in production. A switched-on function either follows each new version that learning produces or stays pinned to one version, and the person can roll back to any earlier version. While it is on, matching requests are answered by the function instead of the LLM, so results stop depending on probabilistic processing; anything it does not cover still goes to the LLM. A case is one exact key. Where requests differ in their values but share one structure (one form layout, say), a verified projection maps each new input to its key, and an input that the projection does not recognize goes to the LLM. Learning never widens a key beyond the inputs it has seen.

Production artifact = a library + CLI control plane that an interface like Open WebUI calls, plus the learning pass as a skill the operator runs; not a web UI. Prototype artifact = a web UI demo that clarifies the purpose, the situations it serves, the output to expect, and how that output makes processes more efficient and predictable.

## Artifacts

Env + gate = `.claude/rules/ops.md`; stdlib-only Python ≥3.11 under `uv`.
- Prototype web UI demo `prototype/webui-demo/` — `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>.
  - Density grade: `node prototype/webui-demo/density.mjs '<url>'` at `?reset=1` + after `capture.sh` (both need `CHROMIUMFISH_DIR`, prototype README).
- Library `src/cement_runtime/` (`from cement_runtime import System`) + CLI `uv run cement --help` (README quick start = the lifecycle: `operation register` → `proposal submit/review` → `compile` → `function verify-drafts/inspect/promote/verify/export/eval`, `resolve`).
- Hospital OCR example — `uv run python examples/hospital_ocr/run_demo.py` (`All checks passed.`; README transcript pinned).
- Gate — `.agent/gate` = `uv run python -m unittest discover -s tests -t .` (1036 tests; wall time = non-D28 tests + one replay per range revision without a green verdict, p78) + `uv build` + `.agent/spec-lint`, per-step wall-clock printed; fast gate = `.agent/gate <tests.module …>` (→ `.claude/rules/ops.md`). Instruments = `.agent/decisions/m<m>u<u>-*`.

## Decisions

- README paragraph 1 = the human-facing statement of `Intent`, rewritten to it in M3.9a; alignment moves the system toward it and never narrows it. Arc: M2 function-as-object (REVIEWED) → M3 trim (IN-PROGRESS) → M5 learning pass + switch/versions and M4 projection inside the boundary, both built this phase (owner-ruled at IMPLEMENT orientation).
- Learning + switching, production (owner-ruled at IMPLEMENT orientation; Intent): the learning pass ships as a skill the operator runs and is the only reviewer (`learning-pass`); it reviews, compiles, verifies AND promotes, so the ONE human gate = the per-operation switch. `CompilePolicy` defaults = 2 confirmations / 1 reviewer / 0 s span (owner: "the only gate is a human switching the function on"). Switch states per operation: `off` | `follow` (answers from the newest promoted version) | `pinned` (one version, named by function hash). Versions = the promotion receipts; rollback = pin an earlier version, so a later learning pass cannot override it — ANY earlier version, across operation revisions too (owner, after `operation revise` was defined as the operator's start-over point), subject to the contract's contrary-evidence checks; `resolve` + `function export` serve the version the switch selects; `function versions` lists receipts and Read diffs two versions. Duplicate retention: Cement enforces a source-observation id unique per (partition, operation), a repeat = conflict exit 4 (owner). Open WebUI example (owner-picked): Cement functions as a tool the chat model calls; on a miss the model also calls `record_answer` with its structured output, and a filter, the single writer, retains it after the response completes with the final reply as provenance (owner); Tool path only — a Pipe mode is out of scope (owner). Contract = `.agent/decisions/m45-contract.md`.
- M4 projection (owner-ruled at IMPLEMENT orientation): case = the projected key — the case stays exact on its key, the projection alone generalizes, verified against EVERY confirmed raw input and fail-closed on input it does not recognize (the LLM answers those); the switch covers function + projection. Form = a constrained JSON IR (`cement-projection-v1`) of total, terminating steps that Cement interprets itself — no eval, no backtracking regex — sealed into the bundle so `function eval` runs it ledger-free; the Read view shows it as code. Author = the learning pass, which proposes the projection while merging scripts AND decides whether the operation's answers depend on structure alone (owner: no operator flag; the Read view states the assumption); Cement verifies grammar + consistency, never semantic correctness.
- Trust boundary = exact lookup: scope = partition + operation revision + canonical JSON input; a function = a set of exact entries (`cement-function-v2`), never a wider predicate; only M4's verified projection artifact widens what one entry covers. Function identity = verified-content identity (`entry_seal` excludes promoter + time; activation provenance stays in the receipt).
- M3 seeds, owner-approved: (a) `CandidateSource` stays core while `CommandCandidateSource`, the subreaper supervisor, `example_adapter.py`, `docs/adapter-protocol.md` relocate to an optional example surface (M3.7); (c) request lifecycle (`handle`, leases, request-ID idempotency, `in_progress`/`retry_failed`/`fallback_failed`/`reconciliation_required`) replaced by `submit_proposal`/`propose` + pure read-only `resolve` (M3.3–M3.6a). Order c → a. Schema cuts ONCE, v2 → v3 at M3.6b, no migration pre-1.0; `SCHEMA_VERSION` 2 until then, private request rows = internal plumbing. v3 carries the switch + projection state the M4/M5 contract names; v3 stays unreleased until the phase close, so a later unit of this phase that needs a v3 column amends v3 in place (fingerprint moves, `SCHEMA_VERSION` stays 3) — no v3 ledger exists outside the suite (MAIN's reading of "cuts ONCE", reported to the owner).
- `resolve` pays full P1-P6 verification per call, no cache; prose cites the measured numbers (`.claude/rules/runtime.md`), never "fast". Ambiguity quarantine leaves with `handle`.
- Exit classes 2/3/4/5/6, the per-leaf stdout channel + `allow_abbrev` scope → `.claude/rules/runtime.md`; root `verify` exit 0 = frozen precedent, never a model.
- Assurance: tier default `kernel`; `oracle` only where an independent implementation can diverge. A removal closes on a battery that fails when one obligation is undone or one preserved invariant disappears — never on a green suite. Each contract pins a NUMBERED gate list rerun from committed state; a gate added mid-unit voids the pins ⇒ linters/type checkers land at a unit boundary. Rulings enter tables through idempotent `--check` patchers; dispatch tips tagged `archive/m<m>u<u>-<role>`.
- Prototype (user): `prototype/webui-demo` = the prototype `Session flow` names, KEPT past IMPLEMENT as an explanatory aid, never production-robust (ruling → `.claude/rules/ops.md` Template rulings); home = `prototype/webui-demo` (owner-ruled at IMPLEMENT orientation), wired to the real switch + versions once they ship. Light theme, accents ≥4.5:1 on white; the provider is simulated + labelled, any other value MAY be hardcoded to visualize the concept, each labelled simulated; every unlabelled value — lifecycle, digests, timings — is the runtime's.
  Function source view (owner-ruled): the promoted set renders as a SOURCE-STYLE DISPATCH — one
  guarded branch per entry, provenance in a comment, an explicit no-match tail, excluded scopes as
  trailing comments — parsed back out of the exported bundle and labelled a rendering, since Cement
  seals exact entries and emits no code. Per-request history retains ONLY proposals that became
  confirmed examples; each entry drills down to the requests behind it, showing the plan the
  provider wrote and what the learning pass merged it into.
  Demo framing (owner-ruled): the prototype explains a concept and must never read as a
  production control plane. Layout = TWO HALVES, `What users see` | `Behind the scenes` (owner-ruled: `users`, never `staff`). The chat = an ordinary chatbot: no badge, id, model name or digest; an AI answer = a
  plain reply, captioned `No change from an ordinary chatbot answer` while Cement has nothing
  reusable for it. A promoted-function part adds ONE tool-call line above the reply (`ƒ Used
  <operation> · <ms>`, expanding to one sentence), as chat products show tool use; the reply
  body is identical either way (owner-ruled r11; supersedes identical rendering). A TURN is one question however many operations answer it: it renders as
  the typing indicator while the model writes, then answers in ONE bubble; a part that misses
  the promoted set returns to the model, and the user waits for the MODEL alone. The chat NEVER
  waits on anyone: the model's answer goes out in that same turn and is retained for the next
  learning pass, which decides what Cement may seal and never what the user already read. Chat kinds = `document | answer`. Every detail stripped from a bubble moves to a
  per-message `what happened under this` disclosure, shown only under technical details.
  Learning + switching (owner-ruled r12; Intent): no person rules on single answers. `Learn from
  chats` = the learning pass, an LLM run periodically (production: a skill the operator runs;
  demo: simulated + labelled, merged script = the case's reference answer) and the ONLY reviewer
  (`learning-pass`): it reads every retained answer, merges each exact case's scripts, then the
  real lifecycle compiles (the floor of 2 = recurrence; a case seen once stays with the AI),
  verifies + promotes. A person's ONE act = switching each learned function on or off (per
  operation, `route(enabled, operation)`), optionally after `Read`ing the function alone.
  Presentation (owner-ruled r7-r12: dense, unclear, wordy, then the human role corrected; Swamp's
  homepage = the clarity reference, not its look): words stripped, the workflow shown, no Cement
  term on the default page.
  - Header = headline alone. Strip = three icons `Ask` → `Learn` → `Switch on`, one word + a
    2-3 word sub each, doubling as the selected task's progress (done / now; billing strikes
    `Switch on`).
  - Band under the strip = one short line on what just happened + the next action: `Learn from
    chats` while answers are retained, `Switch on` for a learned function that is off; in the
    story `Leave the story`.
  - Story = 10 steps: orientation (`What users see`, `Behind the scenes`), first send, second
    send, learn + `Read` (two beats), switch on, tool call, reuse, more jobs, billing, done. Each
    runs, then shows 1-3 spotlight beats (owner-ruled r10, driverjs.com as the reference):
    vendored driver.js `highlight()` on ONE element, never the header strip (r15), with a short
    title + one line read from live state; Next + Back in the popover (Back across a step = reset
    + fast replay to the previous step — no model sleep, same seeded state — then its last beat),
    × or `Leave the story` exits; animation off under reduced motion; a manual click leaves it.
    Owner wording kept: the first script's caption says nothing about Provider (r14); the second
    script's beat = `A slight change from the last script` (r16). driver.js 1.10.2 MIT,
    `static/vendor/driver.js-1.10.2/` (iife build + css + license, registry-integrity checked).
  - Right half = the latest request as three boxes `Form` (first scanned lines) → script →
    `Reply`. The script = a way to handle a KIND of form in plain rows (`Patient name | "Patient:"
    line`), never a patient's values; chip amber `AI script` vs green `Function`. Below it
    `Functions` = one row per operation of the selected task: `ƒ <operation>`, `n kinds of form`,
    `Read`, its own switch; `not learned yet` / billing `never repeats`. `Read` = the function
    alone as code (`if form is a <kind>:` rows … `otherwise: ask the AI`), each row tagged
    `shared` (in every merged script) or `from <request>` (only the scripts that needed it),
    computed from the entry's lineage — the union is how one function generalizes over
    requests (owner-ruled r13). The stand-in AI is fixed, not sampled: a case's first script
    reads less (progress note: no Provider row), every later one is complete; the second
    progress-note request asks for the provider, so the difference reads as request-driven (r14). Tally = chips `AI n`
    `Function m`.
  - Chat + reply = labelled fields, never JSON. Users = `users`, never `staff`. Requests show under
    the five task pills. ONE `Show technical details` switch (off by default; `?tech`,
    `?drawer`, `?source`, `?open` turn it on) holds every per-message disclosure, the scanned text
    + the `Operator view`, READ-ONLY apart from switches (board, one switch for all functions,
    answers retained for the next learning pass, drawer, commands): no accept/correct/reject,
    no manual compile/verify/promote, no revoke (r12 + close review R1).
  - The learning pass reads `learning simulated` on the right half's tag + its story beat;
    `Read` heads `readable rendering`, since Cement seals exact entries and emits no code.
  The right half runs the operator lifecycle as REAL `cement` subprocesses against the demo
  ledger (`_cli`), printing the command, its rc and a condensed reading of the bytes it
  returned, with verbatim stdout + exact argv one click away; an argument over 80 chars prints
  as its shell variable (`--output "$OUTPUT"`), which keeps a 64-char digest visible because
  repeating it IS `function promote`. Chat-side submit + resolve stay IN-PROCESS and say so:
  measured subprocess 92-128 ms over one story's 50 calls vs `System.resolve` 3.5-6.0 ms in that
  same run (`prototype/webui-demo/capture.sh` prints both per run), so routing the chat through a shell would report interpreter startup as the
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
  same card. A turn's parts may split across a promoted function and the model; the bubble shows
  the function part's tool call and nothing for the model part. `document.billing_codes` is keyed on one note's ASSESSMENT TEXT, not the
  layout, so no second note repeats the input, every scope stays at support 1, `compile` blocks
  it, and it stays with the model BY DESIGN — the boundary is the claim, not a gap. The story cements
  every cementable task.
- Human-facing prose (README, `docs/`, example README, CLI help, this spec's `Intent`) = ASD-STE100 register, graded by D25 except `Intent` (ungraded, p75); everything else agent-optimized.
- Gate tooling (owner-ruled; lands at a unit boundary; versions re-ruled at IMPLEMENT orientation = latest): mypy 2.4.0 `strict` over `src/cement_runtime` alone; ruff 0.17.1 format + check, `extend-exclude = ["tests", ".agent", "prototype"]`; scanners = `uv audit` (native, OSV/SARIF) + gitleaks v8.30.1 as ONE sha256-pinned binary the gate downloads into a gitignored tools dir, CI running that same gate command (owner: supersedes the gitleaks Action) + ruff `S`; mutation tool = cosmic-ray 8.7.0 behind one committed command (p74; mutmut 3 = pytest-only + source trampolines this suite's source pins would see); `license = "Apache-2.0"`; CI = GitHub Actions + Dependabot (`uv` + `github-actions`), the full gate on Python 3.13 + the suite minus D28 on 3.11/3.12/3.14, named as a split run; D28 = p78's verdict cache (green only, keyed on replayed tree id + interpreter + `uv.lock` digest; CI restores it through `actions/cache`). The gate-tooling unit also carries p66's standing skip census + p85's reason classes and p12/p40's register audit, owner-approved: all are gate changes that one boundary covers. Grounds + config → `.claude/rules/ops.md`; firing seeds + records → `.claude/rules/gate-checks.md`, its `paths:` extended to the new check files; checker + CI measurements → `.agent/decisions/m3u10-*`. `github.com/eturkes/cement` is PUBLIC ⇒ `push`/`pull_request` carry the gate, a cron alone is disabled after 60 idle days.
- Pin repairs (owner standing approval at IMPLEMENT orientation): a battery frame freezing a CLOSED transition against the working tree is re-scoped to git objects at that unit's close SHA; a prose pin freezing superseded wording is re-targeted at the new claim; none is deleted, skipped or weakened, and every repaired test id is named in its commit body + a `.agent/review.md` row.
- Dispositions (owner-ruled at IMPLEMENT orientation): dev tools p02 p05 p06 p19 stay queued (p02 + p06 ruled against p74 when it lands); scope expansion → queue with reasons (p34-p37, p87-p90): none is needed by the learning pass, the switch or M4.

## Tasks

- [x] 1935f68 p78 D28 verdict cache (`kernel`, gate instrument): equal-strength speed-up of the dominating step.
  - Accept: p78's acceptance — D28's `--durations` line before + after on one tree; a green verdict per content key (replayed tree id + interpreter + `uv.lock` digest), red never cached; a planted red revision reds D28 on its first run and on a rerun; `assertTrue(revisions)` + `Ran >= 949` kept.
- [x] 629577d Gate tooling + CI + scanners = p01 p66 p85 p12 p40 p74 + the IMPLEMENT law gap, per the `Decisions` gate-tooling ruling, at this unit boundary.
  - Format + lint + type check over `src/`; `uv audit`; gitleaks pinned binary; skip census; register audit; `.agent/mutate` (cosmic-ray); `.github/workflows/` + `.github/dependabot.yml`. L12 + L15 (`tests/test_lifecycle_removal_battery.py`) re-scope to git objects at M3.6a2's close (pin-repair approval): the probe measured those 3 failures of 1000 under `ruff format`.
  - Accept: one gate command rc 0 clean-tree; `RUF100` zero; a seeded violation reds EACH of format, lint, type check, audit (a pinned vulnerable dev dep in a fixture lock), secret scan, skip census (a fourth skip, named by test id), register audit (a seeded `simply`; a seeded 30-word sentence stays green); `.agent/mutate` meets p74's acceptance; CI + Dependabot committed.
- [x] 17896eb M3.6a3 delete the 7 dead outcome types (`Outcome` + its 6 members).
  - `src/` holds zero constructors, only `models.py` defs, `__init__.py` import/`__all__`, one `system.py` docstring. `CandidateRequest.request_id` STAYS — live on the `cement-source-v1` envelope — and leaves with M3.6b's single schema/protocol cut.
  - Accept: burden re-measured on its own deletion set; battery per contract.
- [x] 9c2d0ff M4/M5 contract (`kernel`): switch + versions, learning pass + skill, projection IR + its verification, v3 tables, Open WebUI example; `researcher` on the Open WebUI tool/filter API + the Agent Skills format; `consultant` on the contract before code.
  - Accept: `.agent/decisions/m45-contract.md` committed — testable predicates + tier + numbered gate list per unit; consultant verdict adjudicated in `.agent/review.md`.
- [x] 93007ac M3.6b schema cut v2→v3 (direct proposal columns, `requests` + index gone, receipts index, switch + projection tables per the M4/M5 contract, refusal fixtures, 0.2.0); owns p50 p51 p04.
  - Accept: fingerprint + `SCHEMA_VERSION` move together, suite green with the reset documented.
- [x] 635a473 M3.7 command-runtime relocation under byte equality + blocked reverse imports; owns p54.
  - The wheel already carries no `examples/`/`tests/`.
- [x] 1289797 M5.1 switch + versions: per operation `off` | `follow` | `pinned`; rollback = pin; `resolve` + `function export` serve the selected version; `function versions` + Read diff.
- [x] 535a0a9 M4.1 projection IR `cement-projection-v1`: a pure, total, terminating interpreter; `tester` differential oracle.
- [x] 87d011f M4.2 projection lifecycle: raw input → projected key; verification against every confirmed raw input + boundary probes, fail-closed; compile by key; the bundle carries the projection; `resolve` + `function eval` on raw input.
- [x] 6e9e715 M5.2 learning pass: defaults 2/1/0, `learning-pass` reviewer, a CLI read surface over retained answers by case, the skill (merge scripts, write the projection, compile, verify, promote).
- [x] 097de5b M5.3 Open WebUI example: Cement functions as a tool the chat model calls + a filter that retains answers.
- [x] ef06a25 M3.8 demo + transcript regeneration via idempotent updater (`data`): the hospital example on projection + learning pass + switch.
- [ ] Prototype on the real switch + versions (PROTOTYPE law).
  - Resume point: IMPLEMENT resumes here — the prototype commits sit on `impl/m3u9a` (machine-local) below M3.9a's rewrite; cherry-pick them onto `main` (PROTOTYPE law, no suite owed), then land M3.9a once its prose-pin repair (`wt/gp6`) is green.
- [ ] M3.9a docs claim ledger rewrite (`docs`): README paragraph 1 + `docs/` + CLI help follow `Intent`; README install/run/configure current for everything shipped.
- [ ] M3.9b independent replay of the M3.9a rewrite (`docs`).
- [ ] README + prototype disposition: `prototype/webui-demo` stays at `prototype/` (owner-ruled) → `Artifacts`.
- [ ] Phase-close review over the whole phase diff: every lens, one `reviewer` per lens + MAIN's security lens.
  - Runs LAST, after the close's rules upkeep (`CLAUDE.md` `Rules upkeep`), nothing mutating after it; each unit's closing diff draws its OWN pass first (`reviewer` count per `Session flow` Teammates where MAIN dispatches), every pass adjudicated into `.agent/review.md` ⇒ never the only pass.
- Queue = `.agent/deferred.md` (`p<nn>`, one entry + acceptance each, unattached; p01-p61 keep full text + evidence + grounds in `.agent/archive/polish.md`, a born row's entry is its whole record; grader `uv run python .agent/decisions/m3-deferred-validate.py`); a bare `p<nn>` in a row = that unit owns the queue row.

## Phase

IMPLEMENT — whole product
