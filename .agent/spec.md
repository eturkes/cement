# cement spec

## Intent

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior. In a chat-style deployment such as Open WebUI, one kind of task — an OCR extraction, say — is requested many times with slight variations (different documents, slightly different asks). Those requests and their supervised answers are retained in the background, and Cement is the process that realizes such a category can be routed to one deterministic function: a regular, if large, function that grows over time to cover the variations and edge cases as each is supervised, and that is deterministic once built and verified. When ready, an operator decides to route applicable requests to that function — or to sibling functions for other categories — so results depend less on probabilistic LLM processing. Aggregating repeated work this way would be hard to reach without LLMs; repetition alone never widens a rule beyond what was verified.

Production artifact = a library + CLI control plane that an interface like Open WebUI calls; not a web UI. Prototype artifact = a web UI demo that clarifies the purpose, the situations it serves, the output to expect, and how that output makes processes more efficient and predictable.

## Artifacts

Env + gate = `.claude/rules/ops.md`; stdlib-only Python ≥3.11 under `uv`.
- Prototype web UI demo — `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>; proof = `prototype/webui-demo/proof/` (9 PNGs + `transcript.txt`, all from ONE ledger via
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
  is the demonstration. A `held` answer renders as the typing indicator until its review lands,
  and a `miss` renders NOTHING: the user waits while the request returns to the model. Every
  detail stripped from a bubble moves to a per-message `what happened under this` disclosure.
  The right half runs the operator lifecycle as REAL `cement` subprocesses against the demo
  ledger (`_cli`), printing the command, its rc and a condensed reading of the bytes it
  returned, with verbatim stdout + exact argv one click away; an argument over 80 chars prints
  as its shell variable (`--output "$OUTPUT"`), which keeps a 64-char digest visible because
  repeating it IS `function promote`. Chat-side submit + resolve stay IN-PROCESS and say so:
  measured subprocess 106-109 ms vs `System.resolve` 0.9-3.5 ms, so routing the chat through a
  shell would report interpreter startup as the function's cost. Per-entry drill-down = the
  FOUR REAL HOPS p67 names (`function inspect` → `artifact show` → `events` → `proposal show`),
  each a recorded invocation, with `originals` derived from `proposal show`'s own
  `proposed_output`/`final_output` rather than from session memory; `events` carries no example
  filter, so the join is done by hand and shown. Metrics keep the numbers and lose the stat
  tiles. Free interaction stays.
- Human-facing prose (README, `docs/`, example README, CLI help) = ASD-STE100 register, graded by D25; everything else agent-optimized.
- Gate tooling (owner-ruled; lands at a unit boundary): mypy 2.3.1 `strict` over `src/cement_runtime` alone; ruff 0.16.6 format + check, `extend-exclude = ["tests", ".agent", "prototype"]`; scanners = `uv audit` (native, OSV/SARIF) + gitleaks Action + ruff `S`; `license = "Apache-2.0"`. Grounds, config + firing seeds → `.claude/rules/ops.md`; checker + CI measurements → `.agent/decisions/m3u10-*`. `github.com/eturkes/cement` is PUBLIC ⇒ `push`/`pull_request` carry the gate, a cron alone is disabled after 60 idle days.

## Deferred

Queue = `.agent/deferred.md` (`p<nn>`, one line + acceptance each, unattached; p01-p61 keep full text + evidence + grounds in `.agent/archive/polish.md`, a born row's line is its whole record; grader `uv run python .agent/decisions/m3-deferred-validate.py`). Below = the unfinished units, spine order in `Phase`; a bare `p<nn>` here means the unit owns that queue row.
- M3.6a3 delete the 7 dead outcome types (`Outcome` + its 6 members): `src/` holds zero constructors, only `models.py` defs, `__init__.py` import/`__all__`, one `system.py` docstring. `CandidateRequest.request_id` STAYS — live on the `cement-source-v1` envelope — and leaves with M3.6b's single schema/protocol cut. Accept: burden re-measured on its own deletion set; battery per contract.
- M3.6b schema cut v2→v3 (direct proposal columns, `requests` + index gone, refusal fixtures, 0.2.0); owns p50 p51 p04. Accept: fingerprint + `SCHEMA_VERSION` move together, suite green with the reset documented.
- M3.7 command-runtime relocation under byte equality + blocked reverse imports (wheel already carries no `examples/`/`tests/`); owns p54. M3.8 demo + transcript regeneration via idempotent updater (`data`). M3.9a/b docs claim ledger rewrite + independent replay (`docs`).
- M4 projection inside the boundary — plan, open design question + seeds in `.agent/archive/roadmap.md`. Accept: planned as a milestone.
- Gate tooling + CI + scanners = p01 p66 + the IMPLEMENT law gap (no CI, no scanners, no update automation), per the ruling above; GitHub Actions + Dependabot (`uv` + `github-actions`). Owner-approved to also carry p66's standing skip census, both being gate changes that one boundary covers. Accept: one gate command rc 0 clean-tree; `RUF100` zero; a seeded violation reds EACH of format, lint, type check, audit, secret scan, skip census — `uv audit` sees 0 third-party packages today, so its seed is a pinned vulnerable dev dep in a fixture lock, and the census seed is a fourth skip reddening it by test id.
- Committed dev tools p02 p05 p06 p19 (mutation replay, anchor validators, seam battery) + p12 p40 (human-facing register audit). Accept: each reruns from a clean checkout; the audit flags a seeded 30-word instruction + a seeded `simply`, zero over-cap sentences on the four surfaces.
- Scope expansion p34 p35 p36 p37; reviewer identities, encryption, retention, remote registry/signatures; shadow sampling + drift telemetry; TypedDict projections; absolute URLs before publication. Accept: planned as milestones.

## Phase

ITERATE. M3.6a2 closed and landed on main as `ffe9848`, green on the FULL gate with `test_d28`
included (`Ran 1031 tests in 1056.911s` `OK`, `uv build` rc 0; outer skipped + not-run = none,
nested D28 = L30 skipped in every inner replay by construction; missing = format, lint, type
check, dependency audit + secret scan, all five pending the gate-tooling unit). The `CLAUDE.md`
refresh landed as `a8109eb` + `81fad11` and reran that gate whole from EACH: `Ran 1031 tests` in
1113.706s and 1015.317s, `OK` rc 0, `uv build` rc 0, same exclusions both times. The IMPLEMENT
spine below is
SUSPENDED INTACT, not retired — `Decisions` and every unfinished unit stand as written, and the
ITERATE outcome amends them where it lands. Reason for the return, owner-ruled: prototype
feedback.

ITERATE opens by running the artifacts + refreshing proof, then works the owner's feedback into
`prototype/` + `Decisions`. `/goal` stays OFF here and these are interactive sessions until the
owner says go. Start with `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>.
A prototype-only turn owes no gate run (`.claude/rules/ops.md`, census bullet); it owes a
`capture-proof.sh` rerun, since every proof PNG that shows the Function pane goes stale with the
UI.

Feedback landed so far, both worked into `prototype/` + `Decisions`:
1. The demo showed the CEREMONY around the function and never the function — the per-request plan
   was visible only while its proposal was pending, and the promoted set showed a count plus a
   hash. Answered by the function source view; owner picked source-style dispatch over an entry
   table, and entry-feeding requests only over every attempt.
2. The intake assistant was busier than a real chat, and the page as a whole read as a production
   control plane rather than an explanation. Answered by the two-halves framing, the plain chat,
   the per-message peel-back, and the real-CLI right half (`Decisions`, demo-framing bullet).

Shipped for (2): `demo.py` `_cli`/`_display`/`_hops`, rewritten `index.html`/`app.js`/`app.css`
+ `prototype/webui-demo/README.md`. Verified by driving the story through the API on a live
server — 11 real `cement` subprocesses, every rc 0; 5 hops per entry (4 distinct commands,
`proposal show` once per original); `blocked: layout C - support 1 is below required 2` read off
the real `compile`; offline bundle match on A03; empty server log. `proof/` regenerated whole from
ONE ledger, and three capture heights in `capture-proof.sh` were stale against the new block
order: `08-source.png` → 1600x4480 (overlay card 4392 px + `.overlay` 24 px each edge; the card is
`position: fixed`, so `--full-page` reports viewport height and cannot size it), `04-cemented.png`
+ `07-bundle.png` → 1600x2000, the function block now sitting under the terminal + the categories
so a 1000 px fold cut the six set checks and the bundle answer — at 1000 px `06-boundary.png` and
`07-bundle.png` came out BYTE-IDENTICAL, the proof's own tell that a claim had lost its frame.

Resume IMPLEMENT at M3.6a3 when the owner says go.

Suspended IMPLEMENT order, resuming at its head: M3.6a3 → M3.6b → M3.7 → M3.8 → M3.9a/b → gate tooling + CI + scanners (p01 + the IMPLEMENT law-gap row) → README + `prototype/` retirement → phase-close `rev` over the whole phase diff → MAINTAIN. Every unit's closing diff draws its OWN `rev` first and every pass adjudicates into `.agent/review.md`, so the phase-close pass runs LAST with nothing mutating after it, and is never the only one.
