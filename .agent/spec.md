# cement spec

## Intent

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior. In a chat-style deployment such as Open WebUI, one kind of task — an OCR extraction, say — is requested many times with slight variations (different documents, slightly different asks). Those requests and their supervised answers are retained in the background, and Cement is the process that realizes such a category can be routed to one deterministic function: a regular, if large, function that grows over time to cover the variations and edge cases as each is supervised, and that is deterministic once built and verified. When ready, an operator decides to route applicable requests to that function — or to sibling functions for other categories — so results depend less on probabilistic LLM processing. Aggregating repeated work this way would be hard to reach without LLMs; repetition alone never widens a rule beyond what was verified.

Production artifact = a library + CLI control plane that an interface like Open WebUI calls; not a web UI. Prototype artifact = a web UI demo that clarifies the purpose, the situations it serves, the output to expect, and how that output makes processes more efficient and predictable.

## Artifacts

Env + gate = `.claude/rules/ops.md`; stdlib-only Python ≥3.11 under `uv`.
- Prototype web UI demo `prototype/webui-demo/` — `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>.
  - Density grade: `node prototype/webui-demo/density.mjs '<url>'` at `?reset=1` + after `capture.sh` (both need `CHROMIUMFISH_DIR`, prototype README).
- Library `src/cement_runtime/` (`from cement_runtime import System`) + CLI `uv run cement --help` (README quick start = the lifecycle: `operation register` → `proposal submit/review` → `compile` → `function verify-drafts/inspect/promote/verify/export/eval`, `resolve`).
- Hospital OCR example — `uv run python examples/hospital_ocr/run_demo.py` (`All checks passed.`; README transcript pinned).
- Gate — `.agent/gate` = `uv run python -m unittest discover -s tests -t .` (1031 tests; wall time splits by `test_d28`'s replay range) + `uv build` + `.agent/spec-lint`, per-step wall-clock printed; fast gate = `.agent/gate <tests.module …>` (→ `.claude/rules/ops.md`). Instruments = `.agent/decisions/m<m>u<u>-*`.

## Decisions

- README paragraph 1 = authoritative scope; alignment moves the system toward it and never narrows it. Arc: M2 function-as-object (REVIEWED) → M3 trim to paragraph scope (IN-PROGRESS) → M4 projection inside the boundary (UNPLANNED).
- Trust boundary = exact lookup: scope = partition + operation revision + canonical JSON input; a function = a set of exact entries (`cement-function-v2`), never a wider predicate; only M4's verified projection artifact widens what one entry covers. Function identity = verified-content identity (`entry_seal` excludes promoter + time; activation provenance stays in the receipt).
- M3 seeds, owner-approved: (a) `CandidateSource` stays core while `CommandCandidateSource`, the subreaper supervisor, `example_adapter.py`, `docs/adapter-protocol.md` relocate to an optional example surface (M3.7); (c) request lifecycle (`handle`, leases, request-ID idempotency, `in_progress`/`retry_failed`/`fallback_failed`/`reconciliation_required`) replaced by `submit_proposal`/`propose` + pure read-only `resolve` (M3.3–M3.6a). Order c → a. Schema cuts ONCE, v2 → v3 at M3.6b, no migration pre-1.0; `SCHEMA_VERSION` 2 until then, private request rows = internal plumbing.
- `resolve` pays full P1-P6 verification per call, no cache; prose cites the measured numbers (`.claude/rules/runtime.md`), never "fast". Ambiguity quarantine leaves with `handle`.
- Exit classes 2/3/4/5/6, the per-leaf stdout channel + `allow_abbrev` scope → `.claude/rules/runtime.md`; root `verify` exit 0 = frozen precedent, never a model.
- Assurance: tier default `kernel`; `oracle` only where an independent implementation can diverge. A removal closes on a battery that fails when one obligation is undone or one preserved invariant disappears — never on a green suite. Each contract pins a NUMBERED gate list rerun from committed state; a gate added mid-unit voids the pins ⇒ linters/type checkers land at a unit boundary. Rulings enter tables through idempotent `--check` patchers; dispatch tips tagged `archive/m<m>u<u>-<role>`.
- Prototype (user): `prototype/webui-demo` = the prototype `Session flow` names, KEPT past IMPLEMENT as an explanatory aid, never production-robust (ruling → `.claude/rules/ops.md` Template rulings). Light theme, accents ≥4.5:1 on white; the provider is simulated + labelled, any other value MAY be hardcoded to visualize the concept, each labelled simulated; every unlabelled value — lifecycle, digests, timings — is the runtime's.
  Function source view (owner-ruled): the promoted set renders as a SOURCE-STYLE DISPATCH — one
  guarded branch per entry, provenance in a comment, an explicit no-match tail, excluded scopes as
  trailing comments — parsed back out of the exported bundle and labelled a rendering, since Cement
  seals exact entries and emits no code. Per-request history retains ONLY proposals that became
  confirmed examples; each entry drills down to the requests behind it, showing the plan the
  provider wrote and what the supervisor changed.
  Demo framing (owner-ruled): the prototype explains a concept and must never read as a
  production control plane. Layout = TWO HALVES, `What staff see` | `Behind the scenes`. The chat is a PLAIN chat — no badge, id, model name, digest or
  timing — so the supervised answer and the cemented answer render IDENTICALLY; that identity
  is the demonstration. A TURN is one question however many operations answer it: it renders as
  the typing indicator while the model writes, then answers in ONE bubble; a part that misses
  the promoted set returns to the model, and the user waits for the MODEL alone. The chat NEVER
  waits on a person: the model's answer goes out in that same turn and its candidate enters the
  review queue behind it, so a later accept/correct/reject decides what Cement may seal and
  never what the user already read. A correction therefore shows both — the reply the user got
  and the answer cemented instead — inside that message's disclosure, and a rejection retracts
  nothing. Chat kinds = `document | answer`. Every detail stripped from a bubble moves to a
  per-message `what happened under this` disclosure, shown only under technical details.
  Layperson framing (owner-ruled r7, Swamp's homepage as the clarity reference, not its look):
  the page leads with ONE purpose sentence + a four-step workflow strip `Ask` → `Check` →
  `Save` → `Switch on`, plain words, no Cement term; the right half restates those four steps
  for the selected task — current step = its sentence + the ONE next action (`Check the
  answer`, `Save as a fixed answer`, `Use fixed answers`), done steps = a short result, later
  steps = name only — and the header strip marks the same step. `Save` names what is saved:
  how to handle a KIND of form, never one patient's details. Billing = the amber `Save` step
  (no two notes repeat), `Switch on` marked not for this task. A tally line counts AI answers
  vs fixed answers. Requests show directly under the five task pills. ONE `Show technical
  details` switch (off by default; `?tech`, `?drawer`, `?source`, `?open` turn it on) holds
  every per-message disclosure, the scanned text + the `Operator view` (board, routing switch,
  inbox, drawer, commands). Mistakes in the check panel read as plain sentences (`The AI left
  out provider`). Density (words on the first 1600×1000 screen / rendered / buttons): reset
  260/260/12, story end 330/334/13 — the purpose + strip add words that the layperson reading
  needs, so word count is no longer the grade.
  Mechanism + narration (owner-ruled r8; unclear = what clicks did, the auto story, JSON
  replies): the right half opens with `What happened to the latest request` = three boxes,
  the document (id, kind, first scanned lines) → the METHOD used per part, in plain rows
  (`Patient name ← the "Patient:" line`), badged `Written by the AI · not checked yet / a person
  fixed it / confirmed` or `Fixed answer · no AI` with its check count, a correction marking
  each added/fixed/removed row → the reply staff got. This makes the saved thing visible: a
  method for a KIND of form, which plain code applies to a new patient's form. A `What just
  happened` band under the strip captions every action in plain words (send, check, save,
  switch on, task change). `Play the story` = 11 narrated steps, one per `Next`, captions read
  live state (the AI's actual mistake, the patient's name); any manual click leaves the story.
  Chat + reply render as labelled fields, never JSON. Density at story end 381/430/13 —
  the mechanism's words are the explanation.
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
  same card. A turn's parts may split across a promoted function and the model, and the bubble
  hides that seam. `document.billing_codes` is keyed on one note's ASSESSMENT TEXT, not the
  layout, so no second note repeats the input, every scope stays at support 1, `compile` blocks
  it, and it stays supervised BY DESIGN — the boundary is the claim, not a gap. The story cements
  every cementable task.
- Human-facing prose (README, `docs/`, example README, CLI help, this spec's `Intent`) = ASD-STE100 register, graded by D25 except `Intent` (ungraded, p75); everything else agent-optimized.
- Gate tooling (owner-ruled; lands at a unit boundary): mypy 2.3.1 `strict` over `src/cement_runtime` alone; ruff 0.16.6 format + check, `extend-exclude = ["tests", ".agent", "prototype"]`; scanners = `uv audit` (native, OSV/SARIF) + gitleaks Action + ruff `S`; `license = "Apache-2.0"`; CI = GitHub Actions + Dependabot (`uv` + `github-actions`). The gate-tooling unit also carries p66's standing skip census, owner-approved: both are gate changes that one boundary covers. Grounds + config → `.claude/rules/ops.md`; firing seeds + records → `.claude/rules/gate-checks.md`, its `paths:` extended to the new check files; checker + CI measurements → `.agent/decisions/m3u10-*`. `github.com/eturkes/cement` is PUBLIC ⇒ `push`/`pull_request` carry the gate, a cron alone is disabled after 60 idle days.

## Tasks

- [x] 2547505 ITERATE round 5: UI dense → `board` picked over `guided` + `mirror` (`Decisions` board-layout ruling); merged, retired.
- [x] d9fe5df ITERATE round 7: still dense + confusing → layperson framing (purpose sentence, four-step workflow, technical details behind one switch).
- [ ] ITERATE round 8: still unclear what happens → mechanism boxes (document → method → reply), `What just happened` captions, narrated step-through story, readable replies; owner reviews it.
  - Close (the owner's go) runs `Rules upkeep`; known backlog: origin stories + measured results in bare `ops.md` + `assurance.md`; area-bound law in bare `ops.md` (D28, D19, capture mechanics) → `paths:`.
- [ ] M3.6a3 delete the 7 dead outcome types (`Outcome` + its 6 members).
  - Resume point: the suspended IMPLEMENT scope rejoins here once ITERATE closes on the owner's go.
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
  - Accept: each reruns from a clean checkout; the audit flags a seeded `simply` and passes a seeded 30-word sentence (length judged, never capped), zero filler hits on the four surfaces.
- [ ] Scope expansion p34 p35 p36 p37; reviewer identities, encryption, retention, remote registry/signatures; shadow sampling + drift telemetry; TypedDict projections; absolute URLs before publication.
  - Accept: planned as milestones.
- [ ] README + prototype disposition: `prototype/webui-demo` stays KEPT (`.claude/rules/ops.md` Template rulings); decide its home — `prototype/` or `tools/` — and record it in `Artifacts`.
- [ ] Phase-close review over the whole phase diff: every lens, one `reviewer` per lens.
  - Runs LAST, after the close's rules upkeep (`CLAUDE.md` `Rules upkeep`), nothing mutating after it; each unit's closing diff draws its OWN pass first (`reviewer` count per `Session flow` Teammates where MAIN dispatches), every pass adjudicated into `.agent/review.md` ⇒ never the only pass.
- Queue = `.agent/deferred.md` (`p<nn>`, one entry + acceptance each, unattached; p01-p61 keep full text + evidence + grounds in `.agent/archive/polish.md`, a born row's entry is its whole record; grader `uv run python .agent/decisions/m3-deferred-validate.py`); a bare `p<nn>` in a row = that unit owns the queue row.

## Phase

ITERATE — whole product

> I want to return to the ITERATE stage

Suspended: IMPLEMENT — whole product
