# cement spec

## Intent

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior. In a chat-style deployment such as Open WebUI, one kind of task — an OCR extraction, say — is requested many times with slight variations (different documents, slightly different asks). Those requests and their supervised answers are retained in the background, and Cement is the process that realizes such a category can be routed to one deterministic function: a regular, if large, function that grows over time to cover the variations and edge cases as each is supervised, and that is deterministic once built and verified. When ready, an operator decides to route applicable requests to that function — or to sibling functions for other categories — so results depend less on probabilistic LLM processing. Aggregating repeated work this way would be hard to reach without LLMs; repetition alone never widens a rule beyond what was verified.

Production artifact = a library + CLI control plane that an interface like Open WebUI calls; not a web UI. Prototype artifact = a web UI demo that clarifies the purpose, the situations it serves, the output to expect, and how that output makes processes more efficient and predictable.

## Artifacts

Env + gate = `.claude/rules/ops.md`; stdlib-only Python ≥3.11 under `uv`.
- Prototype web UI demo — `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>; proof = `prototype/webui-demo/proof/` (7 scene PNGs + `story-full-page.png` + `transcript.txt`).
- Library `src/cement_runtime/` (`from cement_runtime import System`) + CLI `uv run cement --help` (README quick start = the lifecycle: `operation register` → `proposal submit/review` → `compile` → `function verify-drafts/inspect/promote/verify/export/eval`, `resolve`).
- Hospital OCR example — `uv run python examples/hospital_ocr/run_demo.py` (`All checks passed.`; README transcript pinned).
- Gate — `uv run python -m unittest discover -s tests -t .` (1010 tests, ~500 s) + `uv build`. Instruments per unit = `.agent/decisions/m<m>u<u>-*`.

## Decisions

- README paragraph 1 = authoritative scope; alignment moves the system toward it and never narrows it. Arc: M2 function-as-object (REVIEWED) → M3 trim to paragraph scope (IN-PROGRESS) → M4 projection inside the boundary (UNPLANNED).
- Trust boundary = exact lookup: scope = partition + operation revision + canonical JSON input; a function = a set of exact entries (`cement-function-v2`), never a wider predicate; only M4's verified projection artifact widens what one entry covers. Function identity = verified-content identity (`entry_seal` excludes promoter + time; activation provenance stays in the receipt).
- M3 seeds, owner-approved: (a) `CandidateSource` stays core while `CommandCandidateSource`, the subreaper supervisor, `example_adapter.py`, `docs/adapter-protocol.md` relocate to an optional example surface (M3.7); (b) `authority()` deleted, reviewer/actor recording kept (DONE M3.1); (c) request lifecycle (`handle`, leases, request-ID idempotency, `in_progress`/`retry_failed`/`fallback_failed`/`reconciliation_required`) replaced by `submit_proposal`/`propose` + pure read-only `resolve` (M3.3–M3.6a). Order b → c → a. Schema cuts ONCE, v2 → v3 at M3.6b, no migration pre-1.0; `SCHEMA_VERSION` 2 until then, private request rows = internal plumbing.
- `resolve` pays full P1-P6 verification per call (35.5 s / 986 MiB at the 50,000-entry cap; 616 ms at 1,000; 4 ms at 1), no cache; prose cites the numbers, never "fast". Ambiguity quarantine leaves with `handle`.
- Exit classes: 2 usage/validation, 3 absent, 4 conflict (the one class where retry is the recovery), 5 integrity, 6 negative verdict with the channel chosen per leaf; root `verify` exit 0 = frozen precedent, not a model. `allow_abbrev=False` only on `resolve` + `proposal submit`.
- Assurance: tier default `kernel`; `oracle` only where an independent implementation can diverge. A removal closes on a battery that fails when one obligation is undone or one preserved invariant disappears — never on a green suite. Each contract pins a NUMBERED gate list rerun from committed state; a gate added mid-unit voids the pins ⇒ linters/type checkers land at a unit boundary. Rulings enter tables through idempotent `--check` patchers; dispatch tips tagged `archive/m<m>u<u>-<role>`.
- Prototype (user): `prototype/webui-demo` = behavioral reference (UX, outputs, aesthetics) for IMPLEMENT, never its code base; retires at phase close. Chat + control-plane split, light theme (user ruling), accents ≥4.5:1 on white, `?scene=N` autoplay; the provider alone is simulated and labelled on screen, while lifecycle, digests + resolve timings are the runtime's.
- Human-facing prose (README, `docs/`, example README, CLI help) = ASD-STE100 register, graded by D25; everything else agent-optimized.

## Deferred

`p<nn>` = the archived polish register under `.agent/archive/` (full text, evidence, `pri`, acceptance).
- M3.6a2 S6–S9: code half = `archive/m3u6a2-impl` (`63444f7`, only `system.py` + the battery; main touched neither since `683be58`) cherry-picked onto `impl/m3u6a2b` off main; 19 red battery methods = L19–L24 prose rewrite of the four owned docs, L25–L29 tripwire repairs, L31 quarantine pin. Accept: `tests/test_lifecycle_removal_battery.py` 0 red; contract §6 gates 1–8 green; ONE green squash commit onto main.
- M3.6a3 delete `Resolved`/`InProgress`/`FallbackFailed`/`Rejected`/`ReconciliationRequired`/`Outcome` + `CandidateRequest.request_id`; rule `ReviewRequired` first. Accept: burden re-measured on its own deletion set; battery per contract.
- M3.6b schema cut v2→v3 (direct proposal columns, `requests` + index gone, refusal fixtures, 0.2.0); owns p50 p51 p04. Accept: fingerprint + `SCHEMA_VERSION` move together, suite green with the reset documented.
- M3.7 command-runtime relocation under byte equality + blocked reverse imports (wheel already carries no `examples/`/`tests/`); owns p54. M3.8 demo + transcript regeneration via idempotent updater (`data`). M3.9a/b docs claim ledger rewrite + independent replay (`docs`).
- M4 projection inside the boundary: projection artifact kind replayed against confirmed raw inputs + boundary probes, fail-closed on unrecognized input; open: verification without a domain oracle. Seeds: typed schemas + verifier plugin ABI; decision tables / constrained expression IR.
- `System.examples()` returns values, no digests ⇒ every scope-grouping consumer recomputes the canonical sha256 (`run_demo.py`, prototype `demo.py`). Accept: rows carry `input_hash` + `output_hash`, a test pins them to the compiler's values, both consumers drop the local helper.
- Tooling p01: ruff + a type checker with explicit rule selection; one gate command rc 0; `RUF100` zero; a seeded violation reds it.
- Committed dev tools for scratch instruments p02 p05 p06 p19 (mutation replay, anchor validators, seam battery) + p12 p40 port the human-facing register audit to committed state. Accept: each reruns from a clean checkout; the audit flags a seeded 30-word instruction and a seeded `simply`, zero over-cap sentences on the four surfaces.
- CLI p13 p14 p16 p18 p25 p26 p27 p49 p53 · library p03 p09 p24 p38 p43 p44 p45 p48 · test depth p07 p08 p15 p17 p20 p21 p22 p23 p28 p29 p30 p31 p39 p41 p42 p52 p56 p57 p58 p59 p60 p61 · refactors p32 p33 p46 · records p10 p11 p47 p55. Accept: per row.
- Scope expansion p34 p35 p36 p37; reviewer identities, encryption, retention, remote registry/signatures; shadow sampling + drift telemetry; TypedDict projections; license + absolute URLs before publication. Accept: planned as milestones.
- IMPLEMENT law gap: no CI, scanners, update automation. Accept: dep audit + secret scan + static analysis in gate + CI + Dependabot.

## Phase

IMPLEMENT. Owner said go. Order: M3.6a2 S6–S9 → M3.6a3 → M3.6b → M3.7 → M3.8 → M3.9a/b → gate tooling + CI + scanners (p01 + the IMPLEMENT law-gap row) → `rev` lenses adjudicated in `.agent/review.md` → README + `prototype/` retirement → MAINTAIN.
