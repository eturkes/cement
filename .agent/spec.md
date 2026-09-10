# cement spec

## Intent

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior. In a chat-style deployment such as Open WebUI, one kind of task — an OCR extraction, say — is requested many times with slight variations (different documents, slightly different asks). Those requests and their supervised answers are retained in the background, and Cement is the process that realizes such a category can be routed to one deterministic function: a regular, if large, function that grows over time to cover the variations and edge cases as each is supervised, and that is deterministic once built and verified. When ready, an operator decides to route applicable requests to that function — or to sibling functions for other categories — so results depend less on probabilistic LLM processing. Aggregating repeated work this way would be hard to reach without LLMs; repetition alone never widens a rule beyond what was verified.

Production artifact = a library + CLI control plane that an interface like Open WebUI calls; not a web UI. Prototype artifact = a web UI demo that clarifies the purpose, the situations it serves, the output to expect, and how that output makes processes more efficient and predictable.

## Artifacts

Env + gate = `.claude/rules/ops.md`; stdlib-only Python ≥3.11 under `uv`.
- Prototype web UI demo — `uv run python prototype/webui-demo/app.py` → <http://127.0.0.1:8765/>; proof = `prototype/webui-demo/proof/` (8 PNGs + `transcript.txt`).
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
- Human-facing prose (README, `docs/`, example README, CLI help) = ASD-STE100 register, graded by D25; everything else agent-optimized.
- Gate tooling (owner-ruled; lands at a unit boundary): mypy 2.3.1 `strict` over `src/cement_runtime` alone; ruff 0.16.6 format + check, `extend-exclude = ["tests", ".agent", "prototype"]`; scanners = `uv audit` (native, OSV/SARIF) + gitleaks Action + ruff `S`; `license = "Apache-2.0"`. Grounds, config + firing seeds → `.claude/rules/ops.md`; checker + CI measurements → `.agent/decisions/m3u10-*`. `github.com/eturkes/cement` is PUBLIC ⇒ `push`/`pull_request` carry the gate, a cron alone is disabled after 60 idle days.

## Deferred

Queue = `.agent/deferred.md` (`p<nn>`, one line + acceptance each, unattached; p01-p61 keep full text + evidence + grounds in `.agent/archive/polish.md`, a born row's line is its whole record; grader `uv run python .agent/decisions/m3-deferred-validate.py`). Below = the unfinished units, spine order in `Phase`; a bare `p<nn>` here means the unit owns that queue row.
- M3.6a3 delete the 7 dead outcome types (`Outcome` + its 6 members): `src/` holds zero constructors, only `models.py` defs, `__init__.py` import/`__all__`, one `system.py` docstring. `CandidateRequest.request_id` STAYS — live on the `cement-source-v1` envelope — and leaves with M3.6b's single schema/protocol cut. Accept: burden re-measured on its own deletion set; battery per contract.
- M3.6b schema cut v2→v3 (direct proposal columns, `requests` + index gone, refusal fixtures, 0.2.0); owns p50 p51 p04. Accept: fingerprint + `SCHEMA_VERSION` move together, suite green with the reset documented.
- M3.7 command-runtime relocation under byte equality + blocked reverse imports (wheel already carries no `examples/`/`tests/`); owns p54. M3.8 demo + transcript regeneration via idempotent updater (`data`). M3.9a/b docs claim ledger rewrite + independent replay (`docs`).
- M4 projection inside the boundary — plan, open design question + seeds in `.agent/archive/roadmap.md`. Accept: planned as a milestone.
- Gate tooling + CI + scanners = p01 + the IMPLEMENT law gap (no CI, no scanners, no update automation), per the ruling above; GitHub Actions + Dependabot (`uv` + `github-actions`). Accept: one gate command rc 0 clean-tree; `RUF100` zero; a seeded violation reds EACH of format, lint, type check, audit, secret scan — `uv audit` sees 0 third-party packages today, so its seed is a pinned vulnerable dev dep in a fixture lock.
- Committed dev tools p02 p05 p06 p19 (mutation replay, anchor validators, seam battery) + p12 p40 (human-facing register audit). Accept: each reruns from a clean checkout; the audit flags a seeded 30-word instruction + a seeded `simply`, zero over-cap sentences on the four surfaces.
- Scope expansion p34 p35 p36 p37; reviewer identities, encryption, retention, remote registry/signatures; shadow sampling + drift telemetry; TypedDict projections; absolute URLs before publication. Accept: planned as milestones.

## Phase

IMPLEMENT, returning to ITERATE at M3.6a2's close. OWNER RULED (this session): finish M3.6a2 S9 to
green and squash it onto main FIRST, then flip `Phase:` to ITERATE; the IMPLEMENT spine below is
SUSPENDED INTACT, not retired — `Decisions` and every unfinished unit stand as written, and the
ITERATE outcome amends them where it lands. Reason for the return = prototype feedback: the owner
has UX/output changes for `prototype/webui-demo`. That prototype still runs — its only drift is two
prose hits (`prototype/webui-demo/README.md:60`, `prototype/webui-demo/demo.py:9`) saying the demo
never calls the now-deleted `handle`; the `released` matches in `static/app.js` are the demo's OWN
message vocabulary, not the runtime's. ITERATE opens by running the artifacts + refreshing proof,
then works the owner's feedback into `prototype/` + `Decisions`; `/goal` stays OFF for ITERATE.
Resume IMPLEMENT at M3.6a3 when the owner says go.

Suspended IMPLEMENT order, resuming at its head: M3.6a3 → M3.6b → M3.7 → M3.8 → M3.9a/b → gate tooling + CI + scanners (p01 + the IMPLEMENT law-gap row) → README + `prototype/` retirement → phase-close `rev` over the whole phase diff → MAINTAIN. Every unit's closing diff draws its OWN `rev` first and every pass adjudicates into `.agent/review.md`, so the phase-close pass runs LAST with nothing mutating after it, and is never the only one.
