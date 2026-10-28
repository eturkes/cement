# Review ledger

Adjudicated `rev` findings, one section per review pass. A pass closes on a check set
fixed BEFORE the diff was read: every row adjudicated, the table shipped, an all-`pass`
table complete. An accepted ruling holds until new evidence reverses it. Rows are
adjudicated by MAIN — a teammate verdict is raw material and is re-derived here, never
credited (`.claude/rules/assurance.md`, `Instruments and validators`).

EVERY closing diff draws a pass: each unit's close, each ad-hoc request's close, and the
phase close alike — this ledger is not a phase-close step, and a unit that lands with no
section here closed unreviewed. Scope (owner-ruled, p73): the ledger holds the closes its sections
name (added by the close itself, or naming its SHA); every other commit keeps its record in its
own body's `Teammates:` / `dispatch:` line — the 17 closes of `a8109eb..1623535` among them — and
`uv run python .agent/decisions/p73-review-coverage.py` prints any commit since `a8109eb` with
neither (six listed there with their reasons). A finding inside the artifact's acceptance contract is
fixed before the close it reviews; a finding outside it is born as a `.agent/deferred.md`
row with its acceptance check. The one open row this ledger holds = an IMPLEMENT mutation
survivor its unit left unruled, open until a `consultant` rules it against the contract before
the phase closes (`CLAUDE.md` `Engineering` Verification integrity). A fix earns ONE re-review round
against its acceptance check alone. A pass here is a reviewer's opinion about the repository: neither a
replay verdict nor a promotion receipt (`docs/architecture.md` `## Stability and verification claims`
names all three).

## Template refresh → agents@e29f63a (MAINTAIN, request) — target = the diff this commit lands, base `03b6139`

Template delta = agents@a08b211..e29f63a (a6c54c0, 9ca5f35, 5e742cc, e29f63a): first failed attempt escalates (`consultant`, deep work, advisor fit); `Code review` = `kernel` slices → two `reviewer`s + a MAINTAIN request's closing diff → one all-lens `reviewer` (`where needed` out); PROTOTYPE + ITERATE `researcher` per product-domain question + `operator` per variant batch; ≥5 `consultant`s on a costly-to-reverse ruling; acceptance-suite parenthetical out; unit fits → IMPLEMENT + MAINTAIN; advisor = IMPLEMENT + MAINTAIN low bar + wider fits; portability line positive; `Read` cap out; `navigator` + `tester` wording. Owner ruling: ops.md Template rulings (3) loses its dispatch sub-clause ("Follow the template"). Check set L1-L10 seeded before reviewer-1 (`reviewer`, every lens) read the diff; MAIN re-derived each row; R11 + R12 = MAIN's.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | template fidelity | pass | `cmp` rc 0 vs agents@e29f63a: `CLAUDE.md` (`claude/CLAUDE.project.md`), 8 roles, `.agent/spec-lint` (blob `e3f11e9`, 100755); HEAD's copies `cmp`-equal agents@a08b211 ⇒ delta = upstream `a08b211..e29f63a` alone; role sets 8 = 8. |
| R2 | obligation coverage | pass | reviewer-1's own enumeration E01-E24 (written before it read MAIN's record) maps onto O1-O13 + steps 3-4; its E08 (`substantial` qualified the unit fit too) entered O5. |
| R3 | dispositions | pass | O1-O13 vs rules + spec: O8 = owner ruling + this pass's `reviewer`; O7, O9, O10, O11 bind at their next code-review request / PROTOTYPE-ITERATE session / IMPLEMENT orientation; O5 overclaimed a files-before-commit call before it ran → corrected to the one call so far (transcript `server_tool_use` advisor line 197, result 198, `AskUserQuestion` 201), reviewer-1 rematched. |
| R4 | old forms | pass | 18 forms, `rg --hidden -g '!.git' -n -F` → 0 live hits; history hits = `.agent/review.md` alone (this section's R4 + R5 rows quoting the forms, `:183` `IMPLEMENT unit fits`, `:1280` `nothing machine-specific`); `git grep -F … HEAD` controls ≥ 1 each. |
| R5 | ruling (3) edit | pass | `git diff --word-diff` = one deletion, ``[-`reviewer` dispatch per close = MAIN's call where `Code review` names a fit;-]``, 1 hunk; the every-close adaptation + both carriers stay. |
| R6 | spec preservation | pass | `.agent/spec.md`, `.agent/spec-lint`, `.agent/deferred.md` diff 0 bytes (`git diff --quiet` rc 0) ⇒ layout + unit ids unchanged. |
| R7 | check strength | pass | no check edited; template readers = `law` (`@` imports, frontmatter, `portable`), S24 (`@.agent/spec.md` line 1, unchanged), `shell` (`.agent/spec-lint` unchanged), `p10-scratch-census.py` (operational `CLAUDE.md` = worktree convention, unchanged); test hits = comments + one docstring. |
| R8 | rules upkeep | pass | 11 rule files read whole; none only restates the template or retired mechanics; no rule restates removed text; `upstream-sync.md` absent since `9194f41`. Rules upkeep (MAINTAIN request close): the rules tree is byte-identical to queue run 4's upkeep at `03b6139` apart from ruling (3)'s struck sub-clause, and this re-read found no dead law, misplaced area law or origin story. |
| R9 | portability + settings | pass | `law` `portable` 0; sweep → README `:230`/`:232`/`:259` `~/.ssh/id_ed25519` (owner-kept reader key) + public upstream names (own GitHub URL, Open WebUI, `prism-hu/llens`); no project `.claude/settings*.json`. |
| R10 | queue | pass | no finding outside the contract ⇒ no row born; reviewer-1 register empty. |
| R11 | load probe | pass | fresh `claude -p --output-format stream-json --verbose` (spec-only: the `route` task's operation) → `intake_queue`, 1 turn, 0 `tool_use`; `intake_queue` occurs in `.agent/spec.md` alone among session-start files. |
| R12 | full gate | see the commit body | the CI gate runs on the commit (a commit cannot carry its own gate result). |

## MAINTAIN queue run 4 close — target = the commit landing this section

Check set (the body's `Met when`), fixed before the run's record was reread: R1 every row present at the run's base `e8c1fa5` + every row born after it closed by its acceptance in its own commit, blocked on the owner with what it owes, waiting on its trigger, or routed; R2 the queue + ledger grader; R3 the standing censuses + audits; R4 the full gate on a clean tree at the closing commit. Teammates: operator-1 + operator-2 (p147 live runs, harvested; both stopped after their DONE markers).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 10 rows open at `e8c1fa5`, 3 born (p150-p152). Closed, each in its own commit with its `Closed:` line: p143, p148, p149, p147, p152 (born p149), p145 + p151 (born p143; owner-approved gate changes, seeds fired through CI). Agent parts, row open: p137 ×2 (pillow re-key + PYSEC-2026-4327; authlib CVE-2026-96760 — both target-pinned, held), p150 (owner ruling → cooldown census; the bumps wait). Waiting on a trigger: p52 (a map row about to become a durable claim), p137 (the Open WebUI release production moves to), p140 (a llens backend signer, or the owner reopens), p142 (the owner reopens with a route), p144 (production moves past 0.12.3), p150 (2026-11-03, or an advisory against a current version). Blocked on the owner: none (the run's one question answered p145, p151, p150). Routed: none. |
| R2 | acceptance | pass | `uv run python .agent/decisions/m3-deferred-validate.py` → `VERDICT: PASS`. |
| R3 | integrity | pass | rc 0 each: `p03-stored-int-census.py` (UNGUARDED 0), `p10-scratch-census.py` (unmarked 0; now gate step `scratch`), `p76-anchor-census.py --quiet` (failures 0), `p94-sha-census.py` (unreachable 0), `p73-review-coverage.py`, tripwires PASS, `m3-report-validate.py --all` (5 graded, 0 failed), `.agent/owui-audit` (129 findings in 16 packages held on p137), `.agent/pins` (28 pins: 3 rows + the Open WebUI lock cooling down, open-webui target held p144), `.agent/seeds --only S23 S26 S27` 10 + 3 + 3 MATCH. |
| R4 | acceptance | see the commit body | the closing gate runs on the closing commit (a commit cannot carry its own gate result). |

Rules upkeep (each `.claude/rules/` file re-read against `Authoring`): `ops.md` (Gate list + the census bullet), `gate-checks.md` (S26, S27, S23), `pins.md` (cooldown law), `assurance.md` (closed-unit graders) carry this run's law; no dead law, misplaced area law or origin story found in the other seven.

Cleanup: the cited seed commits ae9c2a1 (p145) + 9d2f1d6 (p151) are kept by local tags `archive/p145-seed` + `archive/p151-seed` (unpublished, `ops.md` Tags); the three prepared worktrees + `wip/*` branches removed; the operators' evidence stays gitignored scratch (no tracked file cites it).

## p150 agent part (MAINTAIN queue run 4, owner ruling: "honor the cooldown except for security releases"; tier `data`: a pin census) — target = the commit landing this section

Check set fixed before the diff was reread: R1 the ruling's two halves (cooldown, security at once); R2 the census both ways; R3 every row kind graded; R4 records; C1 classic pitfalls. The row stays open on its trigger (the bumps after 2026-11-03). MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | cooldown + security exception | pass | `classify`: every stable release between current and latest younger than 7 days → `cooldown until <oldest + 7 d>` (rc 0); an older release in between, an undated source, an unorderable version → BEHIND; any OSV advisory against the CURRENT version → `BEHIND (security: <ids>)` before any date is read. |
| R2 | both ways | pass | `--self-test` 11/11 (synthetic releases, advisories, GitHub Actions tag ranges); its security branch disabled → `FAIL security`, rc 1 (seed S23 `security-off`); live `zizmor 1.0.0` still BEHIND (aged releases between); S23 10/10 MATCH. |
| R3 | every row kind | pass | PyPI (dev deps, uv_build, uv, hatchling, pip-audit, open-webui) + npm (playwright, driver.js, fonts) → release dates + OSV by version; GitHub releases (tools, actions) → `gh` release dates, OSV: zizmor → PyPI, gitleaks → Go module, shellcheck none, actions → a package query + tag-range evaluation (OSV orders no GitHub Actions versions: `tj-actions/changed-files` 45.0.7 by version → 0 hits, its advisory carries ECOSYSTEM ranges); lock rows → per drifted entry (PyPI dates + OSV); Python lines, runner, nucllei tag → undated → BEHIND. OSV positive controls: jinja2 2.10 → 12, pillow 12.3.0 → 44, golang.org/x/net 0.0.1 → 34, playwright 1.0.0 → 1. |
| R4 | records | pass | `pins.md` law (owner ruling quoted) + rc table; `gate-checks.md` S23 bullet (10 cases); `spec.md` Decisions Gate tooling; p150 row re-scoped (trigger 2026-11-03 or an advisory). Live: rc 0, ruff / uv_build / setup-uv uv `cooldown until 2026-11-03`, Open WebUI lock `cooldown until 2026-11-02`. |
| C1 | pitfalls | pass | lock drift is structured (`Drift` keeps the old display, so the census output and S23's regexes are unchanged); a dropped entry (`gone`) or a newly required package (`None`) → BEHIND; per-row network errors stay rc 2; pre-releases never start a cooldown (`version_key` → None). |

## p151 close (MAINTAIN queue run 4, born at p143; owner-approved gate change; tier `data`: a citation census) — target = the commit landing this section

Check set = the row's acceptance A1-A4 + C1 (the census's own records), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | step `scratch` in both branches of `.agent/gate` | pass | after `revisions` in the full + `--omit-d28` branches; shipped → rc 0 `unmarked 0`. |
| A2 | a planted unmarked citation reds the step; the shipped tree passes | pass | seed 9d2f1d6 → CI run 40530418078: both legs `scratch 1`, every other step 0; the closing CI gate = this commit's body. |
| A3 | `.agent/seeds` group + `gate-checks.md` bullet + `paths:` | pass | S27 3/3 MATCH (shipped, docs citation, marker removed); bullet + `paths:` entry; S01-S27 header (p145 took S26, so the prepared group moved to S27 at landing). |
| A4 | `ops.md` Gate list + `spec.md` Artifacts | pass | both name the step; the on-demand bullet became the census bullet. |
| C1 | the census's own records | pass | its first run on the prepared branch reddened its own new `gate-checks.md` bullet (`.scratch/` in the seed text) → `OPERATIONAL` gains `gate-checks.md` (firing record) + `.agent/seeds` (seed group; it had passed only because it quotes the `MARKER` sentence), each with its reason. |

## p137 agent part 2 (MAINTAIN queue run 4, tier `data`: audit holds; the row stays open on its trigger) — target = the commit landing this section

Same check set as `## p137 agent part` (A1 holds = findings, A2 row text, A3 p144 facts, C1 no hold widened), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | holds = findings | pass | `.agent/owui-audit` rc 1 `UNHELD authlib CVE-2026-96760 1.7.2` (first seen at the p145 close); `--emit-holds p137` → 129 holds; rc 0 `PASS`. |
| A2 | row text | pass | OSV `v1/query` authlib 1.7.2 → GHSA-6v38-4h7w-rj9h (alias CVE-2026-96760, fixed 1.9.0; summary: a signature-verification bypass); PyPI `requires_dist`: open-webui 0.12.3 AND 0.12.4 both `authlib==1.7.2` ⇒ target-pinned (the owner's track-only ruling), no lock bump fixes it. Row = 129 findings in 16 packages, authlib named. |
| A3 | p144 facts | pass | fresh 0.12.4 compile → `--lock`: 31 findings in 10 packages, 98 STALE + 3 MOVED; the authlib hold stays. |
| C1 | no hold widened | pass | holds diff = one key added (`authlib CVE-2026-96760`, 1.7.2, p137); `gate-checks.md` S23 shipped case 128/15 → 129/16. |

## p145 close (MAINTAIN queue run 4, owner-approved gate change; tier `data`: a dependency scanner) — target = the commit landing this section

Check set = the row's acceptance A1-A3 + C1 (the tool's other modes) + C2 (prose readers), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | the full gate audits `build-constraints.txt` (OSV, hashes required, no holds, rc 1 on a finding) | pass | step `constraints` after `audit` in both `.agent/gate` branches = `.agent/owui-audit --lock examples/command_source/build-constraints.txt --no-holds` (pip-audit `--require-hashes --disable-pip`); shipped → `PASS (0 findings)`. |
| A2 | a seed pinning `jinja2==2.10` + hashes reds that step | pass | seed ae9c2a1 → CI run 40527846144: both legs `constraints 1`, every other step 0 (`ci/p145-seed` deleted); `.agent/seeds` S26: hashed → rc 1 (6 findings), unhashed → rc 2, shipped → rc 0, 3/3 MATCH. |
| A3 | step + seed recorded; owner approval first | pass | owner: "Approve" (the run's question); `gate-checks.md` S26 bullet + `paths:`, `ops.md` Gate list + Static checks, `pins.md`, `spec.md` Artifacts + Decisions (Gate tooling), README `## Development`. |
| C1 | the tool's other modes | pass | default (Open WebUI lock + holds) unchanged — it reads its default absolute path (a new authlib advisory reds it, held by the p137 commit after this one); `--no-holds` + `--emit-holds` → argparse refuses (mutually exclusive); a relative `--lock` resolved before pip-audit's temporary working directory (the first relative run read no report, rc 2). |
| C2 | prose readers | pass | register-audit `--gate` rc 0, article-audit 0 ungrounded, tripwires PASS; fast gate over the 12 modules reading README or the constraints → Ran 414, OK. |

## p152 close (MAINTAIN queue run 4, born at p149; tier `data`: closed-unit graders) — target = the commit landing this section

Check set = the row's acceptance A1-A3 + C1 (callers + self-tests) + K1 (cleanup: one helper), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | the three named default to close objects, live behind a flag | pass | m3u4 `7864274`, reamend `--check` via the validator's `36f7890`, m3u5b `1146421` (all reads staged, self-test included); `--worktree` reds m3u4 + reamend (the drift the row measured); m3u5b stays green both ways (latent). |
| A2 | rc 0 on a clean clone; m3u5b self-test reds its plants | pass | fresh clone + the 10 files, `python3 -I`: rc 0 × 9 (+ crosswalk); m3u5b `--self-test` 11/11 controls fired before and after. |
| A3 | the rest of the census classified | pass | three more graders/censuses of closed units converted (m3u3 `32c2d11`, m3u6a1-census `dc4ab5e` — red at HEAD, self-test 2/4 controls dead at HEAD → 4/4, m3u2b crosswalk `02dd892`); the remaining 12 = sweeps, burden runs, probes, a corpus: live-range by design, recorded in `assurance.md` Tripwires. |
| C1 | callers + self-tests | pass | `cr1-read-cache.py` GREEN; reamend apply mode refuses an unnamed target (rc 2) instead of rewriting the live battery from a close read; `--emit-stub` / `--emit` keep writing the live files (each unit's own seed step), stdout stubs carry no `SOURCE` line. |
| K1 | cleanup | pass | one helper replaces p149's two `_read` copies + m3u6a1's `_git_object`; `p94-sha-census.py` rc 0 (four new constants in HEAD's history). |

## p147 close (MAINTAIN queue run 4, live regimen; tier `docs`: skill text proven by a sampled run) — target = the commit landing this section

Check set = the row's acceptance A1 (Open WebUI pass), A2 (nucllei pass), A3 (records) + C1 (the evidence is the run's, not the teammate's summary), fixed before the records were reread. Teammates: operator-1 (Open WebUI), operator-2 (nucllei); each verdict below = MAIN's read of the raw files they saved.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | Open WebUI: reply support = listing after `publish` | pass | `learn-reply.txt` (737 bytes): "support is now **2**"; `cases-after.json`: support 2, 2 active, 0 pending; the turn's calls end `publish_version` → `function_versions` → `learn_cases`; pre-merge listing support 0, so the reply did not repeat the stale count. |
| A2 | nucllei: reply support = listing after `publish` | pass | `learn-reply.txt`: "確認済みの例は 2 件です。"; `listing-before.txt` support 0 / 2 pending, `listing-after.txt` support 2 / 2 active / 0 pending; `learn-calls.json` ends `publish` → `learn --projectable yes` (the step-6 re-run). |
| A3 | recorded | pass | `owui-live-e2e.md` + `nucllei-live-e2e.md` `## Support after publish`; `nucllei-contract.md` gate 6 points at it (the row named the contract; the rule's live record is the e2e file). |
| C1 | evidence integrity | pass | both deliverables' `unknown` census → 0; replies quoted from the saved raw bytes, not the reports; operator-1 registered the operation through the CLI stand-in (setup only; the admin Action stays proven by the W6 + B8 runs); operator-2 seeded the second user through `/exec` because the chat route auto-learns (stated in the record). Credential scans 0 hits with positive controls (both). |
| O1 | observation | recorded | nucllei's automatic in-turn pass chose `--projectable no` and merged A02 alone (no version, A01 left pending) against step 4's merge-every-case rule — one gpt-6-luna sample; recorded under the record's pass, no row (model judgment the owner assigned to the learning pass). |

## p149 close (MAINTAIN queue run 4, tier `data`: closed-unit shape graders; the units' claims re-check from git) — target = the commit landing this section

Check set = the row's acceptance A1-A3 + C1 (callers) + C2 (one source per clause) + Q1 (the class), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | default input = close objects; live tree behind a named flag | pass | `CLOSE` + `git show` (m3u5a pair: module `REV`, `--worktree` sets `None`; m3u6a1: `_stage_close` into a temporary root, `--worktree` / `--root` mutually exclusive); `SOURCE:` line printed per grade (never into `--emit-stub` output). |
| A2 | rc 0 by default on a clean checkout | pass | primary tree: rc 0 × 3; fresh `git clone` + the three files, `python3 -I` → rc 0 × 3 with `SOURCE: 36f7890` / `dc4ab5e`; `--worktree` → rc 1 × 3 (the row's drift). |
| A3 | each `--self-test` still reds its planted defect | pass | m3u6a1 (the only one with `--self-test`): 10/10 controls `OK`, `SELF-TEST: PASS`; the m3u5a pair fired by planted inputs: stub → `UNFILLED-TESTS` 30 / 60, close suite minus X01 → `ROWS-UNCOVERED: 1 ['X01']`. |
| C1 | callers fit | pass | `cr1-read-cache.py` runpy's `emit_stub` + `grade(path)`: `grade` keeps its path signature (one read, then `grade_source`), GREEN; `m3u5a-battery-reamend.py` imports `_obligations` / `_amendments` / `_wrap`: `--check` output `cmp`-identical before/after (the contract is unchanged since `36f7890`). |
| C2 | one source per clause | pass | contract/table AND battery/suite come from the same `CLOSE` (m3u6a1-contract.md moved 3× after `dc4ab5e`); an explicit BATTERY path pairs with the selected contract source. |
| Q1 | the class | row born | `rg -l '"tests"' .agent/decisions/*.py` minus git-object readers → 18 tree readers; graded by default: `m3u4-battery-validate.py` rc 1, `m3u5a-battery-reamend.py --check` rc 1, `m3u5b-battery-validate.py` rc 0 (latent), `m3u3-battery-validate.py` rc 0 → p152 (the three named; the rest classified there). |

## p148 close (MAINTAIN queue run 4, tier `docs`: historical records) — target = the commit landing this section

Check set = the row's acceptance A1-A2 + C1 (record readers still pass) + C2 (verbatim evidence stays honest), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | each citation repo-relative or marked | pass | 12 lines in 4 files before (`rg -n "/home/[A-Za-z0-9_.-]+" .agent/decisions`); after: 2 lines, `m45-consultant-1.md:86` + `:88`, both marked. |
| A2 | substance restated beside marked citations | pass | `:86` quotes the v0.12.3 `utils/middleware.py` lines (3805-3819, 3823, 3752-3753) with their pinned GitHub URL; `:88` quotes the Filter documentation's two sentences with their URL; the marker names both. |
| C1 | readers still pass | pass | `m3u6a2-dispositions-validate.py` PASS (0 findings); `m3u6a2-rule-dispositions.py --check` rc 0, apply twice → `cmp`-identical (serialization round-trips; the patcher never reads `symptom`); `m3-report-validate.py --all` 5 graded, 0 failed; `m3u10-gate-tooling.md`'s pointer to `m3u10-ci-research.md` resolves. |
| C2 | verbatim evidence | pass | commands + the quoted error keep their text with `<repo>` standing for the checkout path, and each `.md` says so; prose headings + citations in `m3u10-ci-research.md` became plain repo paths. No count, verdict or excerpt changed. |

## p143 close (MAINTAIN queue run 4, tier `docs`: record markers + a census entry) — target = the commit landing this section

Check set = the row's acceptance A1-A3 + C1 (the census edit still fires) + Q1 (new finds), fixed before the diff was reread. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | census rc 0, `unmarked 0` | pass | `uv run python .agent/decisions/p10-scratch-census.py` → rc 0, `CITATIONS: 199 {'operational': 11, 'history': 51, 'marked': 125, 'json': 12} unmarked 0`. |
| A2 | the four modules green | pass | `.agent/gate tests.test_shadow tests.test_signature tests.test_comparator tests.test_retention_battery` → Ran 93, OK; format, lint, types, spec-lint rc 0. They cite the contracts in docstrings alone (`rg` over `tests/`), so no byte pin moved. |
| A3 | substance restated or marked | pass | each contract's appended marker names where its cited substance lives: consultant verdicts = `.agent/review.md` p135-e3 K1-K8, p136-cmp L1-L6, p136-store N1-N8 (rows read: each carries the verdict + MAIN's re-derivation); the byte probe = p135-e3 R6 (16 copies vs 0); the spike = p135-e5 F3 (210 Wycheproof tests, 0 mismatches) + `test_wycheproof_under_the_strict_policy` at the pinned sha256. `.agent/contract-claims` on each contract → rc 0 (the marker lines carry no count). |
| C1 | census edit fires | pass | p136-store marker removed → rc 1 `UNMARKED …p136-store-contract.md:10`; the census at `HEAD` (without the janitor entry) → rc 1 `UNMARKED .claude/agents/janitor.md:11`; restored → rc 0. The janitor citation = a template copy's ignore-entry list (`.claude/agents/` overwritten whole at each refresh, `ops.md` Template rulings), so `OPERATIONAL` classifies it beside `CLAUDE.md`. |
| Q1 | finds | rows born | p150 (pins drift, `.agent/pins` rc 1 at the run's base), p151 (wire the census as a gate step: a gate change, owner approval first); `ops.md`'s on-demand bullet names p151. |

## p137 agent part (MAINTAIN queue run 4, tier `data`: audit holds; the row stays open on its trigger) — target = the commit landing this section

Check set fixed before the diff was reread: A1 holds = the audit's current findings; A2 the row restates the count + names the new advisory; A3 p144's measured facts re-derived; C1 no hold widened. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | holds = findings | pass | before: `.agent/owui-audit` rc 1 (`UNHELD pillow PYSEC-2026-4326/4327/4328`, `STALE pillow CVE-2026-112392/112396`); `--emit-holds p137` → 128 holds; after: rc 0 `128 findings in 15 packages`, `PASS (0 problems)`. |
| A2 | row text | pass | OSV `api.osv.dev/v1/vulns/<id>`: PYSEC-2026-4326 aliases CVE-2026-112392, PYSEC-2026-4328 aliases CVE-2026-112396 (re-keyed), PYSEC-2026-4327 aliases CVE-2026-112394 (new: P;2L/P;4L raw decoders read past the buffer end), each `fixed` 13.0.0; row = 128 findings, the new id named, the re-key mechanism stated. |
| A3 | p144 facts | pass | `echo open-webui==0.12.4 \| uv pip compile --python-version 3.12 --universal --generate-hashes` → `.agent/owui-audit --lock` = 30 findings in 9 packages, 98 STALE + 3 MOVED (row: from 128, 98 stale, 3 move). |
| C1 | no hold widened | pass | holds diff = 2 pillow keys removed, 3 pillow keys added, each `version` 12.3.0, `row` p137; `gate-checks.md` S23 shipped case 127 → 128. |

## Template refresh → agents@a08b211 (MAINTAIN, request) — target = the diff this commit lands, base `123f08d`

Template delta = agents@7e8ad36..a08b211: `Engineering` IMPLEMENT survivor ruler (`consultant` before close), `Teammates` fit reasons (+ `navigator`, `janitor`) + split stop, `Session flow` `Code review` (replacing `Closing-diff reviewer`), PROTOTYPE + ITERATE rewrite (builds, `janitor`, `navigator`, variant floor), IMPLEMENT orientation steps + unit fits, debugging fan-out, advisor on costly decisions; roles `reviewer` + `tester` changed, `janitor` + `navigator` new; `.agent/spec-lint` unchanged. MAIN alone; 11 lenses fixed before the diff was read.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | template fidelity | pass | `cmp` rc 0 vs agents@a08b211: `CLAUDE.md` (`claude/CLAUDE.project.md`), 8 roles, `.agent/spec-lint` (0 bytes changed, 100755 kept); `copy-template --check` → `The template files are current.`; HEAD's copies `cmp`-equal agents@7e8ad36 ⇒ delta = upstream `7e8ad36..a08b211` alone. |
| R2 | obligation coverage (each delta clause → practice or a named ruling) | pass | O1 survivor ruler → preamble follows; O2 + `navigator`/`janitor` = template roles, their phase-timed fits bind at their next occurrence, `.gitignore` already holds janitor's repo entries; O3 split stop → ruling (3)'s `the template's count` → ``where `Code review` names a fit`` (upstream 81a609b retired counts); O4 `Closing-diff reviewer` → `Code review`: ruling (3) re-keyed; O5 PROTOTYPE + ITERATE rewrite → binds from the next PROTOTYPE/ITERATE session; ruling (1)'s `PROTOTYPE law` = the template's Verification-integrity term (outside every gate) ⇒ MAINTAIN prototype edits keep unit depth (6 latest prototype commits: MAIN alone or `operator`/`reviewer`); O6 deep `tester` suites + debugging fan-out → `assurance.md` Diff-blind authorship + `ops.md` Worktrees hold; O7 IMPLEMENT orientation steps → next IMPLEMENT orientation (Phase = MAINTAIN), spec layout unchanged; O8 `IMPLEMENT unit fits` → next IMPLEMENT unit; O9 advisor on costly decisions → practice holds; O10 `tester` sources + characterization green ↔ `assurance.md` preservation credential (`.agent/mutate`), `reviewer` fit ↔ ruling (3). |
| R3 | old forms | pass | 15 old forms, `rg --hidden -g '!.git' -n -F` → 0 live hits; 1 history hit (`IMPLEMENT phase fits` = `.agent/review.md:265`, code-review check-set row L.cl.66); `git grep -F … HEAD` controls ≥ 1 each. |
| R4 | spec preservation | pass | `.agent/spec.md` diff 0 bytes (layout clauses + `.agent/spec-lint` unchanged); `.agent/spec-lint` rc 0. |
| R5 | check strength (every check reading an edited file) | pass | no check edited. Readers: `law` frontmatter (tracked files ⇒ graded `janitor.md` + `navigator.md` once staged → 0 violations), `imports` (`CLAUDE.md:1` `@.agent/spec.md`), `portable`; `shell` (`.agent/spec-lint` unchanged); `p73-review-coverage.py` (ledger headings, one added). No test reads the preamble (`rg -F '.agent/review.md' tests/` = 1 docstring). |
| R6 | law consistency (edited lines vs template, `assurance.md`, each other) | pass | ruling (3) key = the live `Code review` clause; its fit wording matches `reviewer.md`; every-close pass agrees with the template's IMPLEMENT `per unit + at close`. Preamble ``a `consultant` … before the phase closes`` = template ``a `consultant` rules it before close`` for a row its unit left unruled + upstream `implement.md` Met when (`.agent/review.md` holds no open row); `assurance.md` Survivor scope (non-author ruling) holds. |
| R7 | nothing lost (ruling (3) adaptation, preamble, ledger headings) | pass | ruling (3) keeps the every-close pass, MAIN's dispatch call + both carriers; preamble diff = 2 lines; ledger headings 159 → 160, set diff = this section alone (`## Code review`, `## Security review 2` intact). |
| R8 | portability + settings | pass | `law` `portable` 0; sweep (home paths, `.local/app`, owner login, scheduler + browser tools) → README `~/.ssh/id_ed25519` (`:230`, `:232`, `:259`, owner-kept reader key) + the repo's own public GitHub URL; no project `.claude/settings*.json`. |
| R9 | rules upkeep (restated template, retired mechanics, `upstream-sync.md`) | pass | 11 rule files read whole; none only restates the template or retired mechanics (ruling (4) = a live portability fact holding the numbering `(5)` citations use); `upstream-sync.md` deleted by `9194f41`. |
| R10 | load probe | pass | fresh `claude -p --output-format stream-json --verbose` (spec-only question: the `route` task's operation) → `intake_queue`, 1 turn, 0 `tool_use`; `intake_queue` occurs in `.agent/spec.md` alone among session-start files. |
| R11 | queue | pass | no finding outside the contract ⇒ no row born; on-demand `p10-scratch-census.py` rc 1 (`unmarked 5`) reproduces at `123f08d` = open p143; grader PASS (`COMMITTED-FLOOR: 149`). |

## Code review (MAINTAIN, request) — target = the implementation at `686e86e`, fixes = the commits after it that name this section

Owner body: code, tests, gates, config + docs; check set fixed + committed here before the first read; rows = lens × module, `CLAUDE.md` conformance = lens × clause; finding = severity (`blocker` | `major` | `minor` | `info`) + `file:line` + proof (behavior → a red test; text → anchor bytes `rg -Fn` matches); fix at the root cause, sweep the defect class, one scoped commit per class, gate green at each; law vs code → fix the stale side; a fix changing `Intent`, `Decisions` or a grading check → owner ruling first; security defects met here → MAIN alone. Pre-check-set reads (orientation, disclosed): this ledger (its `## Security review 2` heading lost to `686e86e`'s splice; restored = F-ledger-1), `.claude/rules/*`, `.agent/deferred.md`, `.agent/gate:1-40`, `.agent/ci-gate`, `.claude/agents/reviewer.md`, file lists + def names. Verdicts: `pass` | `finding <F-id>` | `excluded (<reason>)` — `excluded` = a clause that binds no tracked file (process, history, conversation) or a lens the target's law places outside (PROTOTYPE law, Template ruling (1)). Teammate verdicts = leads; every row's verdict here = MAIN's own check.

Lenses: B baseline (the full gate + each runnable `Artifacts` entry by its run command; a red step or failed run = a finding) · C correctness · K cleanup · A altitude (`CLAUDE.md` `Engineering` code diff lenses, one pass each, every function read with its callers + callees) · S claim soundness + guarantee-vs-claim gaps (docstrings, comments, error text, `--help`, README, docs, `Artifacts` vs behavior) · V verification integrity (`Engineering`: tests that cannot fail, retyped expected values, fixture values returned, test/gate detection in shipped code, the skip set, checks that never fire) · F spec fit (behavior vs `Intent` + `Decisions`) · L conformance (each bullet of `CLAUDE.md` + `.claude/rules/*.md`: tool-decidable → its check runs + fires on a planted bad input, none → finding fixed by wiring a check; judgment → judged on the lens rows it names). Grain: one `L` row per bullet; a rules file's indented sub-bullets (`pins.md` `Where each lives`) fold into their parent row, whose basis enumerates them.

Modules (paths fixed here; `system.py` areas by method name, each with the module helpers it calls):
- `sys-intake` = `System.register_operation`, `revise_operation`, `submit_proposal`, `propose`, `get_proposal`, `proposal`, `proposals`, `proposal_by_source`, `review`, `challenge` · `sys-build` = `compile`, `verify_drafts`, `verify`, `inspect_function_promotion`, `promote_function`, `promote`, `learning_cases`, `supersede_examples`, `revoke_example`, `suspend_artifact`, `quarantine_plan`, `quarantine` · `sys-serve` = `latest_function_receipt`, `function_receipts`, `function_report`, `reconstruct_function_receipt`, `verify_function`, `resolve`, `serving`, `switch`, `set_switch`, `function_versions`, `diff_versions`, `shadow_capture` · `sys-config` = `System.__init__` + private infrastructure, `test_projection`, `projection`, `set_projection`, `comparator`, `set_comparator`, `operations`, `examples`, `artifacts`, `artifact`, `report`, `reports`, `prune_proposals`, `erase_partition`, `events`
- `src/cement_runtime/`: `store` `models` `function` `artifacts` `json_value` `pkg` (= `errors.py` + `__init__.py` + `__main__.py` + `py.typed`) `source` `projection` `comparator` `learning` `shadow` `signature` `cli`
- examples: `owui-src` (`examples/open_webui/cement_{tools,filter,learning,admin}.py` + `cement-learn/SKILL.md`) · `owui-gen` (`generate.py`, `paste-in/`, `local.py`, `local-requirements.txt`) · `nucllei` (`examples/nucllei/**`) · `ocr` (`examples/hospital_ocr/**`) · `outbox` (`examples/outbox/**`) · `cmdsrc` (`examples/command_source/**`)
- `skill` = `skills/cement-learn/**`
- tests: `t-system` (`test_system.py`) · `t-cli` (`test_cli*.py`) · `t-battery` (every other `test_*battery*.py` + `test_authority_removal`, `test_read_capability_census`, `test_survivor_pins`, `test_assertion_strength`, `test_expected_revision`) · `t-module` (`test_{function,json_value,comparator,projection_ir,shadow,signature,source,submission,proposal_binding,typed_records,publication_metadata,command_source_distribution}.py` + `typed_records_caller.py`, `ed25519_signer.py`, `projection_oracle.py`, `tests/fixtures/**`) · `t-example` (`test_{hospital_ocr_example,nucllei_example,open_webui_*,outbox_example}.py`)
- gates + config: `g-chain` (`.agent/gate`, `.agent/suite`, `.agent/ci-gate`, `.github/**`) · `g-steps` (`.agent/{skip-census,register-audit,article-audit,article-glossary.txt,fetch-tool,gitleaks,zizmor,shellcheck,spec-lint}`, `.agent/decisions/m3-report-validate.py`, `.agent/decisions/p34-two-wheel-smoke.sh`) · `g-instr` (`.agent/{seeds,pins,owui-audit,mutate,replay-mutants,survivor-triage,kill-check,validate-anchors,contract-claims}`, `.agent/decisions/m3-deferred-validate.py` + the on-demand censuses `ops.md` names + every `.agent/decisions/` file the suite reads or runs, census `rg -o '\.agent/[A-Za-z0-9_./-]+' tests/`) · `config` (`pyproject.toml`, `uv.lock`, `.gitignore`, `.gitleaksignore`, `LICENSE`)
- docs: `readme` (`README.md`) · `docs` (`docs/*.md`) · `ex-readme` (`examples/*/README.md`) · `artifacts-spec` (`.agent/spec.md` `Artifacts`) · `help` (every `cement … --help` page) · `ledger` (`.agent/review.md`, `.agent/deferred.md`)
- `proto` = `prototype/webui-demo/**` (PROTOTYPE law: B + F only)

| id | lens | target | verdict | basis |
|---|---|---|---|---|
| B1 | B | full gate `.agent/gate` at HEAD (CI gate: both legs, D28 included) | pass | CI run 40276994772 on `686e86e`: both legs, every step rc 0, Ran 1621 (3.15) / 1620 (3.12), D28 39 revisions / 3 replayed; the closing commit's full gate = section close line |
| B2 | B | library smoke `from cement_runtime import System` at the package boundary | pass | import-and-call smoke at the package boundary: register → propose → review → compile → verify_drafts → inspect + promote → set_switch → resolve hit, rc 0 |
| B3 | B | CLI `uv run cement --help` + the README quick start end to end | pass | `uv run cement --help` + README quick start end to end in a temp dir (signed `function eval` included), every leaf rc as documented |
| B4 | B | CLI leaves `Artifacts` names: projection test/set/show, learn cases/merge/publish, function versions/diff/export/eval (+ `--signature`), retention prune, partition erase, comparator set/show, function drift/observations | pass | every `Artifacts`-named leaf driven in a temp dir; `function drift`/`observations` without a shadow file → exit 3 as documented |
| B5 | B | learning pass skill `skills/cement-learn/` run per its SKILL.md by an Agent Skills runtime | pass | fresh `claude -p` + the skill alone: 1 version `promoted_by learning-pass`, 0 `function.switched`, injected proposal rejected, support-1 case kept |
| B6 | B | hospital OCR `uv run python examples/hospital_ocr/run_demo.py` → `All checks passed.` + `.agent/decisions/m3u8-transcript.py` | pass | `All checks passed.`; `m3u8-transcript.py --check` rc 0 |
| B7 | B | Open WebUI `examples/open_webui/generate.py` (paste-ins fresh) | pass | `generate.py --check` rc 0 (paste-ins fresh) |
| B8 | B | Open WebUI local instance `local.py setup | serve | provision` + a live chat turn | finding operator-1-F1 | operator-1: setup (0.12.3 / CPython 3.12.15) → serve → provision → 2 retained notes → learning pass promotes (support 2) → admin action `follow` → covered note answered by the function, no proposal; the learning reply misstated support |
| B9 | B | `.agent/owui-audit` (lock OSV audit) | pass | `.agent/owui-audit` rc 0: 127 findings held on p137 |
| B10 | B | stub smoke `.agent/decisions/m5u3-smoke.py` | pass | operator-1: `m5u3-smoke.py` 6/6 cases |
| B11 | B | nucllei `generate.py` + jail stand-in `.agent/decisions/nucllei-jail-smoke.sh` | pass | nucllei `generate.py --check` rc 0 + mode 755; `nucllei-jail-smoke.sh` PASS (Python 3.12.15, SQLite 3.40.1) |
| B12 | B | outbox `examples/outbox/outbox.py` | pass | `tests.test_outbox_example` 5 OK + `outbox.py` run |
| B13 | B | command source wheel `.agent/decisions/p34-two-wheel-smoke.sh` | pass | gate step `wheels` rc 0 on both CI legs (B1) |
| B14 | B | prototype `uv run python prototype/webui-demo/app.py` + `capture.sh` + `density.mjs` + `quality.mjs` | finding operator-2-F1 operator-2-F2 operator-2-F3 | operator-2: capture rc 0 (10 distinct frames), density story 245/16 + reset 156/13, quality floor rc 0 both states, Japanese census pass |
| C1 | C | `sys-intake` | finding reviewer-1-F1 reviewer-1-F3 | MAIN: report read, its leads rerun |
| C2 | C | `sys-build` | finding reviewer-2-F1 reviewer-2-F2 | MAIN: report read, its leads rerun |
| C3 | C | `sys-serve` | finding reviewer-3-F1 | MAIN: report read, its leads rerun; MAIN's own read of `_pin_checks` confirmed |
| C4 | C | `sys-config` | finding reviewer-4-F1 | MAIN: report read, its leads rerun |
| C5 | C | `store` | finding reviewer-4-F2 SEC-1 | MAIN: report read, its leads rerun; reviewer-4-F3 retired against D13 |
| C6 | C | `models` | pass | reviewer-4 pass (models); MAIN: report read, its leads rerun |
| C7 | C | `function` | pass | reviewer-5 pass (function); MAIN: report read, its leads rerun |
| C8 | C | `artifacts` | pass | reviewer-5 pass (artifacts); MAIN: report read, its leads rerun |
| C9 | C | `json_value` | pass | reviewer-5 pass (json_value); MAIN: report read, its leads rerun |
| C10 | C | `pkg` | pass | reviewer-5 pass (pkg); MAIN: report read, its leads rerun |
| C11 | C | `source` | pass | reviewer-5 pass (source); MAIN: report read, its leads rerun |
| C12 | C | `projection` | finding reviewer-5-F1 | MAIN: report read, its leads rerun |
| C13 | C | `comparator` | pass | reviewer-6 pass (comparator); MAIN: report read, its leads rerun |
| C14 | C | `learning` | pass | reviewer-6 pass (learning); MAIN: report read, its leads rerun |
| C15 | C | `shadow` | finding reviewer-6-F1 | MAIN: report read, its leads rerun |
| C16 | C | `signature` | finding reviewer-6-F2 | MAIN: report read, its leads rerun |
| C17 | C | `cli` | finding reviewer-7-F1 reviewer-7-F2 | MAIN: report read, its leads rerun |
| C18 | C | `owui-src` | finding reviewer-8-F1 | MAIN: report read, its leads rerun |
| C19 | C | `owui-gen` | finding reviewer-8-F2 | MAIN: report read, its leads rerun |
| C20 | C | `nucllei` | finding reviewer-9-F1 SEC-5 | MAIN: report read, its leads rerun; SEC-5 = MAIN (security, worked alone) |
| C21 | C | `ocr` | pass | reviewer-9 pass (ocr); MAIN: report read, its leads rerun |
| C22 | C | `outbox` | pass | reviewer-9 pass (outbox); MAIN: report read, its leads rerun |
| C23 | C | `cmdsrc` | finding reviewer-9-F2 | MAIN: report read, its leads rerun |
| C24 | C | `g-chain` | pass | reviewer-10 pass (g-chain); MAIN: report read, its leads rerun |
| C25 | C | `g-steps` | finding reviewer-10-F1 | MAIN: report read, its leads rerun |
| C26 | C | `g-instr` | finding reviewer-10-F2 reviewer-10-F3 reviewer-10-F4 reviewer-10-F5 reviewer-10-F6 reviewer-10-F7 | MAIN: report read, its leads rerun |
| C27 | C | `config` | finding SEC-4 | reviewer-10 lead (pass with a `.gitignore` note); MAIN: `git check-ignore x.db.shadow` rc 1 |
| K1 | K | `sys-intake` | finding reviewer-1-F2 | MAIN: report read, its leads rerun |
| K2 | K | `sys-build` | pass | reviewer-2 pass (sys-build); MAIN: report read, its leads rerun |
| K3 | K | `sys-serve` | pass | reviewer-3 pass (sys-serve); MAIN: report read, its leads rerun |
| K4 | K | `sys-config` | pass | reviewer-4 pass (sys-config); MAIN: report read, its leads rerun |
| K5 | K | `store` | pass | reviewer-4 pass (store); MAIN: report read, its leads rerun |
| K6 | K | `models` | pass | reviewer-4 pass (models); MAIN: report read, its leads rerun |
| K7 | K | `function` | pass | reviewer-5 pass (function); MAIN: report read, its leads rerun |
| K8 | K | `artifacts` | pass | reviewer-5 pass (artifacts); MAIN: report read, its leads rerun |
| K9 | K | `json_value` | pass | reviewer-5 pass (json_value); MAIN: report read, its leads rerun |
| K10 | K | `pkg` | pass | reviewer-5 pass (pkg); MAIN: report read, its leads rerun |
| K11 | K | `source` | pass | reviewer-5 pass (source); MAIN: report read, its leads rerun |
| K12 | K | `projection` | pass | reviewer-5 pass (projection); MAIN: report read, its leads rerun |
| K13 | K | `comparator` | pass | reviewer-6 pass (comparator); MAIN: report read, its leads rerun |
| K14 | K | `learning` | pass | reviewer-6 pass (learning); MAIN: report read, its leads rerun |
| K15 | K | `shadow` | pass | reviewer-6 pass (shadow); MAIN: report read, its leads rerun |
| K16 | K | `signature` | pass | reviewer-6 pass (signature); MAIN: report read, its leads rerun |
| K17 | K | `cli` | pass | reviewer-7 pass (cli); MAIN: report read, its leads rerun |
| K18 | K | `owui-src` | pass | reviewer-8 pass (owui-src); MAIN: report read, its leads rerun |
| K19 | K | `owui-gen` | pass | reviewer-8 pass (owui-gen); MAIN: report read, its leads rerun |
| K20 | K | `nucllei` | pass | reviewer-9 pass (nucllei); MAIN: report read, its leads rerun |
| K21 | K | `ocr` | pass | reviewer-9 pass (ocr); MAIN: report read, its leads rerun |
| K22 | K | `outbox` | pass | reviewer-9 pass (outbox); MAIN: report read, its leads rerun |
| K23 | K | `cmdsrc` | pass | reviewer-9 pass (cmdsrc); MAIN: report read, its leads rerun |
| K24 | K | `g-chain` | pass | reviewer-10 pass (g-chain); MAIN: report read, its leads rerun |
| K25 | K | `g-steps` | pass | reviewer-10 pass (g-steps); MAIN: report read, its leads rerun |
| K26 | K | `g-instr` | finding reviewer-10-F8 | MAIN: report read, its leads rerun |
| K27 | K | `config` | pass | reviewer-10 pass (config); MAIN: report read, its leads rerun |
| A1 | A | `sys-intake` | finding reviewer-1-F1 reviewer-1-F2 | MAIN: report read, its leads rerun |
| A2 | A | `sys-build` | finding reviewer-2-F1 reviewer-2-F2 | MAIN: report read, its leads rerun |
| A3 | A | `sys-serve` | pass | reviewer-3 pass (sys-serve); MAIN: report read, its leads rerun |
| A4 | A | `sys-config` | finding reviewer-4-F1 | MAIN: report read, its leads rerun |
| A5 | A | `store` | pass | reviewer-4 pass (store); MAIN: report read, its leads rerun |
| A6 | A | `models` | pass | reviewer-4 pass (models); MAIN: report read, its leads rerun |
| A7 | A | `function` | pass | reviewer-5 pass (function); MAIN: report read, its leads rerun |
| A8 | A | `artifacts` | pass | reviewer-5 pass (artifacts); MAIN: report read, its leads rerun |
| A9 | A | `json_value` | pass | reviewer-5 pass (json_value); MAIN: report read, its leads rerun |
| A10 | A | `pkg` | pass | reviewer-5 pass (pkg); MAIN: report read, its leads rerun |
| A11 | A | `source` | pass | reviewer-5 pass (source); MAIN: report read, its leads rerun |
| A12 | A | `projection` | pass | reviewer-5 pass (projection); MAIN: report read, its leads rerun |
| A13 | A | `comparator` | pass | reviewer-6 pass (comparator); MAIN: report read, its leads rerun |
| A14 | A | `learning` | pass | reviewer-6 pass (learning); MAIN: report read, its leads rerun |
| A15 | A | `shadow` | pass | reviewer-6 pass (shadow); MAIN: report read, its leads rerun |
| A16 | A | `signature` | pass | reviewer-6 pass (signature); MAIN: report read, its leads rerun |
| A17 | A | `cli` | finding reviewer-7-F1 | MAIN: report read, its leads rerun |
| A18 | A | `owui-src` | pass | reviewer-8 pass (owui-src); MAIN: report read, its leads rerun |
| A19 | A | `owui-gen` | pass | reviewer-8 pass (owui-gen); MAIN: report read, its leads rerun |
| A20 | A | `nucllei` | pass | reviewer-9 pass (nucllei); MAIN: report read, its leads rerun |
| A21 | A | `ocr` | pass | reviewer-9 pass (ocr); MAIN: report read, its leads rerun |
| A22 | A | `outbox` | pass | reviewer-9 pass (outbox); MAIN: report read, its leads rerun |
| A23 | A | `cmdsrc` | finding reviewer-9-F2 | MAIN: report read, its leads rerun |
| A24 | A | `g-chain` | pass | reviewer-10 pass (g-chain); MAIN: report read, its leads rerun |
| A25 | A | `g-steps` | pass | reviewer-10 pass (g-steps); MAIN: report read, its leads rerun |
| A26 | A | `g-instr` | finding reviewer-10-F3 reviewer-10-F5 reviewer-10-F6 | MAIN: report read, its leads rerun |
| S1 | S | `sys-intake` | pass | reviewer-1 pass (sys-intake docstrings + error text); MAIN: report read, its leads rerun |
| S2 | S | `sys-build` | finding reviewer-2-F1 reviewer-2-F2 | MAIN: report read, its leads rerun |
| S3 | S | `sys-serve` | finding reviewer-3-F2 | MAIN: report read, its leads rerun |
| S4 | S | `sys-config` | finding reviewer-4-F4 | MAIN: report read, its leads rerun |
| S5 | S | `store` | finding reviewer-4-F5 | MAIN: report read, its leads rerun; reviewer-4-F3 retired against D13 |
| S6 | S | `models` | finding reviewer-4-F6 | MAIN: report read, its leads rerun |
| S7 | S | `function` | pass | reviewer-5 pass (function); MAIN: report read, its leads rerun |
| S8 | S | `artifacts` | pass | reviewer-5 pass (artifacts); MAIN: report read, its leads rerun |
| S9 | S | `json_value` | pass | reviewer-5 pass (json_value); MAIN: report read, its leads rerun |
| S10 | S | `pkg` | finding reviewer-5-F2 | MAIN: report read, its leads rerun |
| S11 | S | `source` | pass | reviewer-5 pass (source); MAIN: report read, its leads rerun |
| S12 | S | `projection` | finding reviewer-5-F1 | MAIN: report read, its leads rerun |
| S13 | S | `comparator` | finding reviewer-6-F3 | MAIN: report read, its leads rerun |
| S14 | S | `learning` | finding reviewer-6-F4 | MAIN: report read, its leads rerun |
| S15 | S | `shadow` | finding reviewer-6-F5 | MAIN: report read, its leads rerun |
| S16 | S | `signature` | finding reviewer-6-F2 SEC-2 | MAIN: report read, its leads rerun |
| S17 | S | `cli` | finding reviewer-7-F1 reviewer-7-F2 reviewer-7-F3 | MAIN: report read, its leads rerun |
| S18 | S | `owui-src` | finding reviewer-8-F3 reviewer-8-F4 | MAIN: report read, its leads rerun |
| S19 | S | `owui-gen` | pass | reviewer-8 pass (owui-gen); MAIN: report read, its leads rerun |
| S20 | S | `nucllei` | finding reviewer-9-F3 reviewer-15-F5 | MAIN: report read, its leads rerun (reviewer-9-F4 = reviewer-15-F5) |
| S21 | S | `ocr` | pass | reviewer-9 pass (ocr); MAIN: report read, its leads rerun |
| S22 | S | `outbox` | pass | reviewer-9 pass (outbox); MAIN: report read, its leads rerun |
| S23 | S | `cmdsrc` | pass | reviewer-9 pass (cmdsrc); MAIN: report read, its leads rerun |
| S24 | S | `g-chain` | pass | reviewer-10 pass (g-chain); MAIN: report read, its leads rerun |
| S25 | S | `g-steps` | finding reviewer-10-F1 | MAIN: report read, its leads rerun |
| S26 | S | `g-instr` | finding reviewer-10-F2 reviewer-10-F4 reviewer-10-F5 reviewer-10-F6 reviewer-10-F7 reviewer-10-F9 | MAIN: report read, its leads rerun |
| S27 | S | `config` | pass | reviewer-10 pass (config); MAIN: report read, its leads rerun |
| S28 | S | `skill` | finding reviewer-11-F1 | MAIN: report read, its leads rerun |
| S29 | S | `readme` | finding reviewer-11-F2 reviewer-11-F3 reviewer-11-F8 reviewer-1-R1 | MAIN: report read, its leads rerun |
| S30 | S | `docs` | finding reviewer-11-F2 | MAIN: report read, its leads rerun |
| S31 | S | `ex-readme` | finding reviewer-11-F4 reviewer-11-F5 | MAIN: report read, its leads rerun |
| S32 | S | `artifacts-spec` | pass | reviewer-11 pass (artifacts-spec); MAIN: report read, its leads rerun |
| S33 | S | `help` | pass | reviewer-7 pass (59 help pages, 76 CLI calls); MAIN: report read, its leads rerun; MAIN B3/B4 drove the leaves |
| S34 | S | `ledger` | finding reviewer-11-F6 reviewer-11-F7 F-ledger-1 | MAIN: report read, its leads rerun |
| V1 | V | `t-system` | finding reviewer-12-F1 reviewer-12-F2 | MAIN: report read, its leads rerun |
| V2 | V | `t-cli` | finding reviewer-13-F1 | MAIN: report read, its leads rerun |
| V3 | V | `t-battery` | finding reviewer-13-F2 reviewer-13-F3 reviewer-13-F4 | MAIN: report read, its leads rerun; class sweep adds D13 + D17 recorders |
| V4 | V | `t-module` | finding reviewer-14-F1 | MAIN: report read, its leads rerun |
| V5 | V | `t-example` | pass | reviewer-14 pass (every example test module); MAIN: report read, its leads rerun |
| V6 | V | `src/cement_runtime (shipped code: no test/gate detection, no fixture value returned, no branch keyed to a test input)` | pass | reviewer-14 pass (16 modules, AST census); MAIN: report read, its leads rerun; MAIN census: no unittest/pytest/sys.modules/env branch in src |
| V7 | V | `examples (same, shipped example code)` | pass | reviewer-14 pass (15 example modules); MAIN: report read, its leads rerun; MAIN census over examples |
| V8 | V | `g-steps + g-instr (each check fires on its planted input)` | finding reviewer-10-F5 reviewer-10-F6 reviewer-10-F7 L.nucllei.7 L.open-webui.2 | MAIN: `.agent/seeds` S02-S23 at `6992036` 124/125 MATCH (S23 `shipped` = F-pins-1; 8/8 at the stack tip), S01 fast cases MATCH + full table = B1; checks that did not fire = the listed findings |
| F1 | F | `sys-intake` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F2 | F | `sys-build` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F3 | F | `sys-serve` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F4 | F | `sys-config` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F5 | F | `store` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F6 | F | `projection` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F7 | F | `comparator` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F8 | F | `learning` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F9 | F | `shadow` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F10 | F | `signature` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F11 | F | `cli` | finding reviewer-15-F1 | MAIN: report read, its leads rerun |
| F12 | F | `owui-src` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F13 | F | `owui-gen` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F14 | F | `nucllei` | finding reviewer-15-F2 | MAIN: report read, its leads rerun |
| F15 | F | `ocr` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F16 | F | `outbox` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F17 | F | `cmdsrc` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F18 | F | `skill` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F19 | F | `readme` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F20 | F | `docs` | pass | reviewer-15 pass (its Intent + Decisions obligation map for this module); MAIN: report read, its leads rerun |
| F21 | F | `ex-readme` | finding reviewer-15-F5 | MAIN: report read, its leads rerun |
| F22 | F | `proto` | finding reviewer-15-F3 operator-2-F2 operator-2-F3 | MAIN: report read, its leads rerun |
| L.cl.1 | L | `CLAUDE.md:7` Uncertain / needs a decision / benefits from my | excluded (conversation/collaboration: binds no tracked file) | — |
| L.cl.2 | L | `CLAUDE.md:8` When discussion may improve the work, open one proactively: | excluded (conversation/collaboration: binds no tracked file) | — |
| L.cl.3 | L | `CLAUDE.md:9` Stay objective; push back on my ideas when warranted | excluded (conversation/collaboration: binds no tracked file) | — |
| L.cl.4 | L | `CLAUDE.md:10` A failed attempt is a valid result: report it | excluded (conversation/collaboration: binds no tracked file) | — |
| L.cl.5 | L | `CLAUDE.md:14` Install/configure project-local; work within the launch dir + children; | pass | J: installs project-local — gate tools in gitignored `.tools/` (`.agent/fetch-tool`), `.venv`, `.open-webui/`; judged on C27/K27 |
| L.cl.6 | L | `CLAUDE.md:15` Long horizon → orient, then execute: one session carries | excluded (session process: binds no tracked file) | — |
| L.cl.7 | L | `CLAUDE.md:16` Finish line = a pasted body's Met when, else | excluded (session process: binds no tracked file) | — |
| L.cl.8 | L | `CLAUDE.md:17` Research, whenever a tooling, method or design choice is | excluded (session process: binds no tracked file) | — |
| L.cl.9 | L | `CLAUDE.md:18` Git: creds in the global gitconfig; standing permission for | finding SEC-4 L-census | commit law = history; `.gitignore` current = T: `git check-ignore x.db.shadow` rc 1 (SEC-4) + no proof a gate run leaves the tree clean → CI clean-tree step after each leg |
| L.cl.10 | L | `CLAUDE.md:19` Gate command = the full check chain .claude/rules/ records; | pass | T: `.agent/gate` prints rc + seconds + `Slowest test durations` — seeds S01 (`missing-module` rc 1, `durations`) + CI step tables |
| L.cl.11 | L | `CLAUDE.md:20` CI gate: a public GitHub repo whose main CI | pass | T: `.agent/ci-gate` wrong arg count / dirty tree → rc 2; green run deleted `ci/cr`, red run 40280902361 kept it (rc 1) |
| L.cl.12 | L | `CLAUDE.md:21` Evidence: capture rc on the spot (cmd; rc=$?); an | excluded (session process: binds no tracked file) | — |
| L.cl.13 | L | `CLAUDE.md:22` Command output rides the context → the quietest useful | excluded (session process: binds no tracked file) | — |
| L.cl.14 | L | `CLAUDE.md:23` Task close → remove the temporary + stale artifacts | pass | process part excluded; T: tracked dangling links = law-census `symlinks` (0; self-test plant fires) |
| L.cl.15 | L | `CLAUDE.md:24` UI design (artifact, variant or unit): the subject's domain, | pass | prototype UI under PROTOTYPE law (Template ruling (1)); quality floor `quality.mjs` rc 0 at reset + story (B14) |
| L.cl.16 | L | `CLAUDE.md:25` Charts + figures: the data's job picks the form, | pass | T: no chart or figure tracked (`git ls-files` image census 0) ⇒ palette gate vacuous |
| L.cl.17 | L | `CLAUDE.md:29` AI agents = the sole developers ⇒ agent-optimized = | pass | J: agent-optimized text — judged on the K/S rows + rules upkeep |
| L.cl.18 | L | `CLAUDE.md:30` State rules, facts + warnings plainly; omit provenance — | pass | J: rules upkeep pass at this close (no dates, provenance or origin story added) |
| L.cl.19 | L | `CLAUDE.md:31` Future-facing text, esp. prompts → state the desired action | pass | J: rules + skills state actions positively (rules upkeep pass) |
| L.cl.20 | L | `CLAUDE.md:32` Prompts + instruction files state task, finish line + | pass | J: `.claude/agents/` = template copies (fixes upstream); briefs = process |
| L.cl.21 | L | `CLAUDE.md:33` Guidance + checks on text = goals + reasons, | pass | T: register-audit prints sentence length, never grades it (seeds S13) |
| L.cl.22 | L | `CLAUDE.md:34` Instruction files = yours to maintain → update any | finding L-census | T: law-census (gate step `law`, seeds S24) — no check existed (`portable`: home-directory paths in live law, config, code + docs) |
| L.cl.23 | L | `CLAUDE.md:35` .claude/rules/ reaches MAIN + every teammate of an interactive | finding L-census | T: law-census (gate step `law`, seeds S24) — no check existed (`frontmatter`: quoting + every glob matches a tracked file) |
| L.cl.24 | L | `CLAUDE.md:36` @path imports (instruction files) + attaches (my messages) a | finding L-census | T: law-census (gate step `law`, seeds S24) — no check existed (`imports`: each `@` line names a tracked file) |
| L.cl.25 | L | `CLAUDE.md:37` Human-facing = strictly user-facing surfaces a person reads at | pass | T: filler ban = seeds S13 + S19 (register) + S17 (articles); register = J on S29-S31 |
| L.cl.26 | L | `CLAUDE.md:41` Elegant, tightly-scoped modular components; deduplicate; KISS + UNIX where | pass | J: code diff lenses — judged on the C/K/A rows |
| L.cl.27 | L | `CLAUDE.md:42` Code = agent-read artifact → concise within three bounds: | pass | J: code diff lenses — judged on the C/K/A rows |
| L.cl.28 | L | `CLAUDE.md:43` Comments cost tokens → spend them on the why | pass | J: code diff lenses — judged on the C/K/A rows |
| L.cl.29 | L | `CLAUDE.md:44` Target sufficient scope, evidence-backed claims + real success criteria. | pass | J: code diff lenses — judged on the C/K/A rows |
| L.cl.30 | L | `CLAUDE.md:45` Established methods (TDD red-green-refactor, differential oracles, adversarial review) + | pass | J: code diff lenses — judged on the C/K/A rows |
| L.cl.31 | L | `CLAUDE.md:46` Open tooling decisions (language/library/package…) → research (Execution) + select | pass | J: code diff lenses — judged on the C/K/A rows |
| L.cl.32 | L | `CLAUDE.md:47` Deterministic checks own every rule a tool can decide: | pass | T: `.agent/seeds` refuses a bullet count ≠ group count; S01-S23 fired |
| L.cl.33 | L | `CLAUDE.md:48` Tests/verification: derive scope from requested outcome + regression risk | pass | J: test scope — judged on the V rows |
| L.cl.34 | L | `CLAUDE.md:49` Runnable change → run the real app by its | excluded (session process: binds no tracked file) | the B rows drove each runnable artifact |
| L.cl.35 | L | `CLAUDE.md:50` Verification integrity binds every check on the implementation; a | pass | T: skip set = seeds S12; J rest on V1-V8 |
| L.cl.36 | L | `CLAUDE.md:51` Assurance tier, declared per unit with its contract: kernel | excluded (session process: binds no tracked file) | — |
| L.cl.37 | L | `CLAUDE.md:52` Units = the shortest path to the consumable artifact, | excluded (session process: binds no tracked file) | — |
| L.cl.38 | L | `CLAUDE.md:53` A gate backing a durable claim must rerun from | finding p143 | T: `p10-scratch-census.py` rc 1 (5 unmarked = open p143); stays on demand until p143 closes (owner) |
| L.cl.39 | L | `CLAUDE.md:54` Repairs to a generated artifact land as one idempotent | pass | T: W1 + N7 + `generate.py --check` rc 0 (B7, B11); catalogue L.nucllei.1 + L.open-webui.1 killed |
| L.cl.40 | L | `CLAUDE.md:55` Adversarial review (code or session) → scrutinize correctness + | excluded (session process: binds no tracked file) | — |
| L.cl.41 | L | `CLAUDE.md:56` Code diff lenses = the author's self-review before each | excluded (session process: binds no tracked file) | — |
| L.cl.42 | L | `CLAUDE.md:57` Split assurance by what it costs the decider: mechanical | excluded (session process: binds no tracked file) | — |
| L.cl.43 | L | `CLAUDE.md:58` Review terminates on a check set fixed before the | excluded (session process: binds no tracked file) | — |
| L.cl.44 | L | `CLAUDE.md:59` Delegated reports are two-tier: a verdict table the decider | excluded (session process: binds no tracked file) | — |
| L.cl.45 | L | `CLAUDE.md:60` Remotely-exploitable code → highest security standard: periodically audit, update | excluded (security: owner body `Security review`; security defects met here worked by MAIN) | — |
| L.cl.46 | L | `CLAUDE.md:64` MAIN does the work: a planned unit's code, docs | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.47 | L | `CLAUDE.md:65` Offload economics: fresh-context + blindness fits pay at any | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.48 | L | `CLAUDE.md:66` Briefs + prompts (teammates, SendMessage, claude -p) = broader | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.49 | L | `CLAUDE.md:67` Names = role + gapless ordinal (reviewer-2), so SendMessage | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.50 | L | `CLAUDE.md:68` Harvest: marker + turn end → read the deliverable | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.51 | L | `CLAUDE.md:69` A code-writing teammate works in git worktree add -b | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.52 | L | `CLAUDE.md:70` Shared mutable resources (build stores, DBs, ports, work tree, | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.53 | L | `CLAUDE.md:71` Advisor, where present = MAIN's call per case at | excluded (teammate mechanics: binds no tracked file) | — |
| L.cl.54 | L | `CLAUDE.md:75` Phases, Phase: in .agent/spec.md = the phase + its | pass | T: `.agent/spec-lint` (seeds S03); `Phase` = `MAINTAIN — whole product` |
| L.cl.55 | L | `CLAUDE.md:76` .agent/spec.md = the sole attached state, imported by the | pass | T: spec-lint gate step + seeds S03 |
| L.cl.56 | L | `CLAUDE.md:77` PROTOTYPE = the fastest path to an artifact I | pass | J: `Artifacts` records `prototype/webui-demo/` (S32) |
| L.cl.57 | L | `CLAUDE.md:78` IMPLEMENT = the best version of the intended software, | excluded (session process: binds no tracked file) | — |
| L.cl.58 | L | `CLAUDE.md:79` Routing: phase per kind of work — an open | excluded (session process: binds no tracked file) | — |
| L.cl.59 | L | `CLAUDE.md:80` Routed state: Phase line 1 = <PHASE> — <scope>; | pass | T: spec-lint (seeds S03); no routed state open |
| L.cl.60 | L | `CLAUDE.md:81` This file + .claude/agents/ = copies of a shared | pass | T: template fidelity = `copy-template --check` in the agents repo (template-refresh section R1); no portable in-repo gate (another repo) |
| L.cl.61 | L | `CLAUDE.md:82` Rules upkeep rides the Tasks clearing: each phase close | pass | J: rules upkeep at this close |
| L.cl.62 | L | `CLAUDE.md:83` Checkpointing: a phase session compacts many times ⇒ state | excluded (session process: binds no tracked file) | — |
| L.cl.63 | L | `CLAUDE.md:84` Teammates: fits, reasons + mechanics = Teammates; the phase | excluded (session process: binds no tracked file) | — |
| L.cl.64 | L | `CLAUDE.md:85` PROTOTYPE + ITERATE: teammates = cheap + shallow, artifacts | excluded (session process: binds no tracked file) | — |
| L.cl.65 | L | `CLAUDE.md:86` IMPLEMENT + MAINTAIN: teammates = deep; each unit's depth | excluded (session process: binds no tracked file) | — |
| L.cl.66 | L | `CLAUDE.md:87` IMPLEMENT phase fits, any depth: researcher = SOTA survey | excluded (session process: binds no tracked file) | — |
| L.cl.67 | L | `CLAUDE.md:88` Advisor (fits + rulings = Teammates; its bar follows | excluded (session process: binds no tracked file) | — |
| L.cl.68 | L | `CLAUDE.md:89` Read cost control = .gitignore kept current — content | finding SEC-4 L-census | = L.cl.9 `.gitignore` half |
| L.assurance.1 | L | `.claude/rules/assurance.md:11` Mutation criterion, binding: for every check, some committed test | pass | J: judged on the V rows (V1-V8) |
| L.assurance.2 | L | `.claude/rules/assurance.md:12` A green suite is NEVER closure for a removal: | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.3 | L | `.claude/rules/assurance.md:13` Token-absence cannot prove structural deletion — a rename satisfies | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.4 | L | `.claude/rules/assurance.md:14` A residue classifier needs a stable domain, an exact | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.5 | L | `.claude/rules/assurance.md:15` One row per clause certifies only that the clause | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.6 | L | `.claude/rules/assurance.md:16` Three blind-conjunct shapes: VACUOUS BY A SIBLING GATE (a | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.7 | L | `.claude/rules/assurance.md:17` A clause whose subject is committed history is insensitive | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.8 | L | `.claude/rules/assurance.md:18` attack + mut = WORK-UNIT instruments with --check patchers: | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.9 | L | `.claude/rules/assurance.md:22` A prototype runs under PROTOTYPE law. This repo's = | pass | T: no `tests/` module names `prototype/`; wheel = `cement_runtime` alone, sdist excludes prototype (`uv build` in B1; `test_publication_metadata`) |
| L.assurance.10 | L | `.claude/rules/assurance.md:23` An expected-output table the contract does not own is | pass | J: judged on the V rows (V1-V8) |
| L.assurance.11 | L | `.claude/rules/assurance.md:24` Red-first and preservation are two credentials, not one. A | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.12 | L | `.claude/rules/assurance.md:25` Survivor scope (owner-ruled at the MAINTAIN queue run's close): | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.13 | L | `.claude/rules/assurance.md:26` The shipped suite's skip set is CLOSED at three, | pass | T: gate step `skips` rc 0 (B1); seeds S12 5/5 (planted shapes); its loop defect = reviewer-10-F1 |
| L.assurance.14 | L | `.claude/rules/assurance.md:27` The grading check is fixed when the contract is: | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.15 | L | `.claude/rules/assurance.md:31` An instrument that cannot fire reports exactly like an | pass | J: judged on the V rows (V1-V8) |
| L.assurance.16 | L | `.claude/rules/assurance.md:32` A mutation control aims at the test that OWNS | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.17 | L | `.claude/rules/assurance.md:33` A test whose subject is a CONSTRAINT needs a | pass | J: judged on the V rows (V1-V8) |
| L.assurance.18 | L | `.claude/rules/assurance.md:34` A self-test control that mutates rows[0] dies at scale | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.19 | L | `.claude/rules/assurance.md:35` Recording instruments must be TOTAL over their channel: override | pass | J: judged on the V rows (V1-V8) |
| L.assurance.20 | L | `.claude/rules/assurance.md:36` A probe that records AFTER the call loses every | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.21 | L | `.claude/rules/assurance.md:40` Purge __pycache__ and set PYTHONDONTWRITEBYTECODE=1: CPython invalidates bytecode on | pass | T: replay-mutants / mutate / survivor-triage / kill-check set PYTHONDONTWRITEBYTECODE + purge; this review's 40 replays restored every clone |
| L.assurance.22 | L | `.claude/rules/assurance.md:41` Address every mutant by line plus an asserted anchor | pass | T: seeds S14 `anchor-miss` rc 2 |
| L.assurance.23 | L | `.claude/rules/assurance.md:42` Run a pristine CONTROL sweep at full worker count | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.24 | L | `.claude/rules/assurance.md:43` A survivor count is meaningless without its VERDICT MODULE | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.25 | L | `.claude/rules/assurance.md:44` An author-run sweep certifies only the families its author | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.26 | L | `.claude/rules/assurance.md:45` The sweep patches src/ in place ⇒ git status | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.27 | L | `.claude/rules/assurance.md:46` A replay that mutates an embedded source (src/cement_runtime minus | pass | T: seeds S14 embed seed; this review's replays regenerated the copies (L.nucllei.7 survived honestly, no phantom W1/N7 kill) |
| L.assurance.28 | L | `.claude/rules/assurance.md:50` Vary every fixture across the boundary its check depends | pass | J: judged on the V rows (V1-V8) |
| L.assurance.29 | L | `.claude/rules/assurance.md:51` Enumeration completeness needs a tail sentinel beyond any plausible | pass | J: judged on the V rows (V1-V8) |
| L.assurance.30 | L | `.claude/rules/assurance.md:52` Pin every bound as an adjacent accept/reject PAIR (max | pass | J: judged on the V rows (V1-V8) |
| L.assurance.31 | L | `.claude/rules/assurance.md:53` Frozen public shape is invisible to behavioral tests: one | pass | J: judged on the V rows (V1-V8) |
| L.assurance.32 | L | `.claude/rules/assurance.md:54` Behavioral tests cannot see resource contracts: slicing after the | pass | J: judged on the V rows (V1-V8) |
| L.assurance.33 | L | `.claude/rules/assurance.md:55` Mock the LIBRARY boundary, never the module's own dispatch | pass | J: judged on the V rows (V1-V8) |
| L.assurance.34 | L | `.claude/rules/assurance.md:59` A diff-blind author pins what it can see, so | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.35 | L | `.claude/rules/assurance.md:60` Red-at-baseline / green-at-HEAD is MAIN's credential, run in a | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.36 | L | `.claude/rules/assurance.md:61` tester is diff-blind on TWO counts, audited separately: its | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.37 | L | `.claude/rules/assurance.md:62` Dispatch the phase-1 table BEFORE implementing; its divergences are | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.38 | L | `.claude/rules/assurance.md:66` DERIVE the instrument, never hand-list it, and assert the | pass | J: judged on the V rows (V1-V8) |
| L.assurance.39 | L | `.claude/rules/assurance.md:67` Grade by whole-token set membership, never containment (24 sits | pass | J: judged on the V rows (V1-V8) |
| L.assurance.40 | L | `.claude/rules/assurance.md:68` A validator that passes on its first run has | pass | J: judged on the V rows (V1-V8) |
| L.assurance.41 | L | `.claude/rules/assurance.md:69` A grader's strict branch guarded by a surface heuristic | pass | J: judged on the V rows (V1-V8) |
| L.assurance.42 | L | `.claude/rules/assurance.md:70` A validator's clean grade says nothing about columns it | pass | J: judged on the V rows (V1-V8) |
| L.assurance.43 | L | `.claude/rules/assurance.md:71` Run every idempotent patcher twice before trusting it once: | pass | J: judged on the V rows (V1-V8) |
| L.assurance.44 | L | `.claude/rules/assurance.md:75` Every number a contract states must be RUN in | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.45 | L | `.claude/rules/assurance.md:76` Nothing grades the contract against its own instruments' results, | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.46 | L | `.claude/rules/assurance.md:77` A set obligation states its DERIVATION, and the spellings | pass | J: judged on the V rows (V1-V8) |
| L.assurance.47 | L | `.claude/rules/assurance.md:78` Obligation and gate numbers are NOT keys across contracts: | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.48 | L | `.claude/rules/assurance.md:79` A prescription authored in an earlier unit is a | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.49 | L | `.claude/rules/assurance.md:83` Three tripwire classes: what the DELETION breaks (staged burden | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.50 | L | `.claude/rules/assurance.md:84` Every instrument reading tests/ sees the unit's own battery, | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.51 | L | `.claude/rules/assurance.md:85` A scope pin read against the WORKING TREE expires: | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.52 | L | `.claude/rules/assurance.md:86` A whole battery grading a CLOSED transition takes both | pass | J: judged on the V rows (V1-V8) |
| L.assurance.53 | L | `.claude/rules/assurance.md:87` Before adding a file to a frozen tree, read | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.54 | L | `.claude/rules/assurance.md:88` Measure a removal by deleting it and running the | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.55 | L | `.claude/rules/assurance.md:89` Compare the failure SET between stages, never the count: | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.56 | L | `.claude/rules/assurance.md:90` Scripted, count-asserted, idempotent surgery beats hand editing past ~30 | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.57 | L | `.claude/rules/assurance.md:94` Seed the deliverable, and seed its row SUBJECTS: filling | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.58 | L | `.claude/rules/assurance.md:95` Order the graded artifact FIRST in the brief; a | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.59 | L | `.claude/rules/assurance.md:96` Instruct the oracle NOT to match MAIN's rulings: a | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.60 | L | `.claude/rules/assurance.md:97` A mid-wave contract edit expires every seeded predicate at | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.61 | L | `.claude/rules/assurance.md:98` MAIN's fill of an exempt column belongs in an | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.assurance.62 | L | `.claude/rules/assurance.md:99` Re-derive a teammate artifact before crediting it; a PASS | excluded (unit-closure / campaign method: binds the work, not a tracked file) | — |
| L.example-demo.1 | L | `.claude/rules/example-demo.md:8` run_demo.py prints exactly TWO per-run dynamic values, one art_<32hex> | pass | T: catalogue mutant L.example-demo.1 killed |
| L.example-demo.2 | L | `.claude/rules/example-demo.md:9` The example README's text transcript block is that output | pass | T: catalogue mutant L.example-demo.2 killed |
| L.example-demo.3 | L | `.claude/rules/example-demo.md:10` The demo refuses to run under -O/-OO, where Python | pass | T: catalogue mutant L.example-demo.3 killed |
| L.example-demo.4 | L | `.claude/rules/example-demo.md:11` The demo deletes its temporary ledger, so every producing | pass | J: demo teardown order — B6 `All checks passed.` |
| L.example-demo.5 | L | `.claude/rules/example-demo.md:12` Two clean runs export different bundle bytes at a | pass | J: self-consistent bundle loop (`OfflineBundleTests`) |
| L.example-demo.6 | L | `.claude/rules/example-demo.md:13` A test that grades a helper's RESULT does not | pass | T: catalogue mutant L.example-demo.6 killed |
| L.example-demo.7 | L | `.claude/rules/example-demo.md:14` An end-to-end script needs its own integration pin, or | pass | T: catalogue mutant L.example-demo.7 killed |
| L.example-demo.8 | L | `.claude/rules/example-demo.md:15` Example self-checks run only by hand ⇒ behavior worth | pass | T: `tests/test_hospital_ocr_example.py` holds the demo pins (suite) |
| L.example-demo.9 | L | `.claude/rules/example-demo.md:16` A probe copied into a worktree relocates its __file__, | excluded (session process: binds no tracked file) | probe-authoring method |
| L.gate-checks.1 | L | `.claude/rules/gate-checks.md:39` .agent/gate (the gate command, .claude/rules/ops.md Env + Fast gate): | pass | T: seeds S01 `missing-module` + `durations` MATCH; full table = CI B1 |
| L.gate-checks.2 | L | `.claude/rules/gate-checks.md:40` tests/test_read_capability_census.py (AST census: every transaction(write=False) block in system.py stays | pass | T: seeds group S02 MATCH at `6992036` |
| L.gate-checks.3 | L | `.claude/rules/gate-checks.md:41` .agent/spec-lint: .agent/spec-lint <(git show b8a0703:.agent/spec.md) → rc 1, :116 | pass | T: seeds group S03 MATCH at `6992036` |
| L.gate-checks.4 | L | `.claude/rules/gate-checks.md:42` .agent/decisions/m3-deferred-validate.py, each seed run in a disposable worktree at | pass | T: seeds group S04 MATCH at `6992036` |
| L.gate-checks.5 | L | `.claude/rules/gate-checks.md:43` D28 verdict cache (p78): planted red revision = a | pass | T: seeds group S05 MATCH at `6992036` |
| L.gate-checks.6 | L | `.claude/rules/gate-checks.md:44` D28 (tests/test_migration_battery.py): a seed costs one full suite per | pass | T: seeds group S06 MATCH at `6992036` |
| L.gate-checks.7 | L | `.claude/rules/gate-checks.md:45` D28 pairing (instrument_pruned(), tests/test_lifecycle_removal_battery.py L23 ×2, L26, L29, L30), | pass | T: seeds group S07 MATCH at `6992036` |
| L.gate-checks.8 | L | `.claude/rules/gate-checks.md:46` SWAPPED_ROOTS purge (MigrationBatteryTests.setUpClass): uv run python -m unittest tests.test_hospital_ocr_example | pass | T: seeds group S08 MATCH at `6992036` |
| L.gate-checks.9 | L | `.claude/rules/gate-checks.md:47` Static checks (pyproject.toml [tool.ruff] + [tool.mypy], gate steps format/lint/types): | pass | T: seeds group S09 MATCH at `6992036` |
| L.gate-checks.10 | L | `.claude/rules/gate-checks.md:48` uv audit (gate step audit): a scratch project with | pass | T: seeds group S10 MATCH at `6992036` |
| L.gate-checks.11 | L | `.claude/rules/gate-checks.md:49` .agent/gitleaks (gate step secrets, pinned binary by sha256 into | pass | T: seeds group S11 MATCH at `6992036` |
| L.gate-checks.12 | L | `.claude/rules/gate-checks.md:50` .agent/skip-census (gate step skips, p66 + p85): a copy | pass | T: seeds group S12 MATCH at `6992036` |
| L.gate-checks.13 | L | `.claude/rules/gate-checks.md:51` .agent/register-audit --gate (gate step register, p12 + p40): Run | pass | T: seeds group S13 MATCH at `6992036` |
| L.gate-checks.14 | L | `.claude/rules/gate-checks.md:52` .agent/replay-mutants (p02, closure tool, not a gate step): .agent/decisions/replay-mutants-seeds.jsonl | pass | T: seeds group S14 MATCH at `6992036` |
| L.gate-checks.15 | L | `.claude/rules/gate-checks.md:53` .agent/validate-anchors (p19, report validator, not a gate step): fixtures | pass | T: seeds group S15 MATCH at `6992036` |
| L.gate-checks.16 | L | `.claude/rules/gate-checks.md:54` .agent/contract-claims (p60, contract checker, not a gate step): fixtures | pass | T: seeds group S16 MATCH at `6992036` |
| L.gate-checks.17 | L | `.claude/rules/gate-checks.md:55` .agent/article-audit (p64; gate step articles, p130): .agent/gate with the | pass | T: seeds group S17 MATCH at `6992036` |
| L.gate-checks.18 | L | `.claude/rules/gate-checks.md:56` .agent/mutate (p74, credit tool, not a gate step): see | pass | T: seeds group S18 MATCH at `6992036` |
| L.gate-checks.19 | L | `.claude/rules/gate-checks.md:57` .agent/register-audit --gate CLI help (p92): simply inserted at the | pass | T: seeds group S19 MATCH at `6992036` |
| L.gate-checks.20 | L | `.claude/rules/gate-checks.md:58` .agent/decisions/m3-report-validate.py --all (gate step reports, p05): fixtures .agent/fixtures/report-anchors/ — | pass | T: seeds group S20 MATCH at `6992036` |
| L.gate-checks.21 | L | `.claude/rules/gate-checks.md:59` .agent/zizmor (gate step actions, zizmor 1.31.1 --offline over .github/, | pass | T: seeds group S21 MATCH at `6992036` |
| L.gate-checks.22 | L | `.claude/rules/gate-checks.md:60` .agent/shellcheck (gate step shell, ShellCheck 0.11.0, every severity, -x, | pass | T: seeds group S22 MATCH at `6992036` |
| L.gate-checks.23 | L | `.claude/rules/gate-checks.md:61` .agent/pins (p125, pin census, not a gate step; network | pass | T: seeds S23 firing cases 7/7 MATCH at `6992036`; `shipped` DIFF = F-pins-1 (8/8 at the stack tip) |
| L.history-gates.1 | L | `.claude/rules/history-gates.md:10` D28 (tests/test_migration_battery.py) replays the full suite at EVERY revision | pass | T: D28 in CI's full leg (`D28: 51 revisions, 1 replayed`); every stack commit's suite replayed by D28 |
| L.history-gates.2 | L | `.claude/rules/history-gates.md:11` Verdict cache (p78, equal-strength speed-up): D28 serves a revision | pass | T: seeds S05 6/6 (a planted red never recorded) + `D28VerdictCacheTests` |
| L.history-gates.3 | L | `.claude/rules/history-gates.md:12` Launch the gate with SIGINT at SIG_DFL: a non-interactive | pass | J/T: ci-gate + offload launch under SIG_DFL (seeds S05/S07 ran) |
| L.history-gates.4 | L | `.claude/rules/history-gates.md:13` On a red branch each ADDITIONAL commit touching those | excluded (session process: binds no tracked file) | — |
| L.history-gates.5 | L | `.claude/rules/history-gates.md:14` D28 is the ONLY gate grading history, and splitting | pass | T: CI full leg = one `discover` with D28; split leg named (`suite: SPLIT RUN — omits …`) |
| L.history-gates.6 | L | `.claude/rules/history-gates.md:15` D28 unlinks tests/test_migration_battery.py from each checkout before the inner | pass | T: seeds S07 4/4 pairing |
| L.history-gates.7 | L | `.claude/rules/history-gates.md:16` _detached_worktree (every migration-battery checkout) lives in a run-scoped directory | pass | T: `WorktreeOrphanTests` (suite) |
| L.history-gates.8 | L | `.claude/rules/history-gates.md:17` m3u6a2-tripwires.json keys each pin + freeze on <file>:<test name> | pass | T: `m3u6a2-tripwires.py` PASS after each prose fix |
| L.history-gates.9 | L | `.claude/rules/history-gates.md:18` Composition is the unit of gate truth. MigrationBatteryTests swaps | pass | T: seeds S08 4/4 `SWAPPED_ROOTS` purge |
| L.human-facing.1 | L | `.claude/rules/human-facing.md:12` Re-derive every claim against SHIPPED CODE, never against the | pass | J: claims re-derived against shipped code on S29-S31 (findings there) |
| L.human-facing.2 | L | `.claude/rules/human-facing.md:13` State publication POSITIVELY: a reader must learn from prose | pass | J: publication claims on S29 (absent shadow file → exit 3 documented, B4) |
| L.human-facing.3 | L | `.claude/rules/human-facing.md:14` Every placeholder in a shipped command block needs a | pass | J/T: D23 parses shell blocks for placeholders (suite); quick start placeholders produced earlier in each block (B3) |
| L.human-facing.4 | L | `.claude/rules/human-facing.md:15` A trust-model "Trusted" list must never name an artifact | pass | J: threat-model Trusted list read (S30) |
| L.human-facing.5 | L | `.claude/rules/human-facing.md:16` Qualify a claim in one place and it stays | pass | J: unqualified-form sweep with each S fix |
| L.human-facing.6 | L | `.claude/rules/human-facing.md:17` Never imply speed for resolve; cite the measured cold | finding reviewer-3-F2 | J: `resolve` docstring cited the pre-cache cost as current; README qualified it |
| L.human-facing.7 | L | `.claude/rules/human-facing.md:18` Register audit = .agent/register-audit (p12 + p40); plain mode | pass | T: gate step `register` + seeds S13/S19 |
| L.human-facing.8 | L | `.claude/rules/human-facing.md:19` Definite references = uv run python .agent/article-audit (p64; gate | pass | T: gate step `articles` + seeds S17 |
| L.human-facing.9 | L | `.claude/rules/human-facing.md:20` Split bullets and table rows into their own units | pass | T: register-audit splits bullets + table cells (seeds S13) |
| L.nucllei.1 | L | `.claude/rules/nucllei.md:13` Generated file: a change to src/cement_runtime/** or examples/nucllei/cement_nucllei.py → | pass | T: catalogue L.nucllei.1 killed (N7 freshness + mode) |
| L.nucllei.2 | L | `.claude/rules/nucllei.md:14` Jail facts the command rests on (nucllei-sandbox v20261020-01): Python | pass | T: `nucllei-jail-smoke.sh` PASS (B11) |
| L.nucllei.3 | L | `.claude/rules/nucllei.md:15` Model-facing text = Japanese, llens style: a refusal = | finding reviewer-15-F2 | T/J: llens-style Japanese — argparse help + usage errors were English |
| L.nucllei.4 | L | `.claude/rules/nucllei.md:16` Writers: proposals ← record alone (consumes its ticket); reviews, | pass | T: catalogue L.nucllei.4 killed (N6 AST pin) |
| L.nucllei.5 | L | `.claude/rules/nucllei.md:17` Skills: switch is named by cement-switch.md alone (N8); its | pass | T: catalogue L.nucllei.5 killed (N8) |
| L.nucllei.6 | L | `.claude/rules/nucllei.md:18` README census: examples/nucllei/README.md sits in the tripwire DOCS + | pass | T: tripwires `DOCS` + D23 `added_surfaces` (suite) |
| L.nucllei.7 | L | `.claude/rules/nucllei.md:19` Untrusted documents never pass through the shell: the chat | finding L.nucllei.7 SEC-3 | T: catalogue mutant L.nucllei.7 survived; the skills' heredoc hand-over = SEC-3 |
| L.nucllei.8 | L | `.claude/rules/nucllei.md:20` Shadow sampling = deferred (p142, owner): each /workspace is | pass | owner-deferred (p142); no tracked nucllei shadow code |
| L.nucllei.9 | L | `.claude/rules/nucllei.md:21` Learning bookkeeping (raw inputs, grouping, merge, publish) = cement_runtime.learning, | pass | J: bookkeeping in `cement_runtime.learning` (C14); reviewer-9-F1 = the command's own state file |
| L.open-webui.1 | L | `.claude/rules/open-webui.md:11` Sources examples/open_webui/cement_*.py (importable with an installed cement_runtime + a | pass | T: catalogue L.open-webui.1 killed (W1 refusals) |
| L.open-webui.2 | L | `.claude/rules/open-webui.md:12` LOADER imports importlib.machinery before installing its finder: find_spec imports | finding L.open-webui.2 | T: catalogue mutant L.open-webui.2 survived W1 + N7 |
| L.open-webui.3 | L | `.claude/rules/open-webui.md:13` Item ids: chat tool cement, learning tool cement_learning, filter | pass | T: item ids pinned by `tests.test_open_webui_local` plan tests + live provision (B8) |
| L.open-webui.4 | L | `.claude/rules/open-webui.md:14` Valve operations = one line per operation, name: description | pass | T: catalogue L.open-webui.4 killed (W2) |
| L.open-webui.5 | L | `.claude/rules/open-webui.md:15` Writers: proposals ← the filter alone; reviews / supersessions | pass | T: catalogue L.open-webui.5 killed (W3 AST pin) |
| L.open-webui.6 | L | `.claude/rules/open-webui.md:16` Shadow sampling (filter, p136): outlet only queues — _hits | pass | T: catalogue L.open-webui.6 killed (`_loggable`); the recovery defect = reviewer-8-F1 |
| L.open-webui.7 | L | `.claude/rules/open-webui.md:17` Learning tool division (live-run finding, record § Learning passes): | pass | J: learning tool division held in the live pass (B8) |
| L.open-webui.8 | L | `.claude/rules/open-webui.md:18` Open WebUI 0.12.3, measured live: built-in search_tools (the model | pass | J: measured-live facts reproduced in B8 (`search_tools`, action dialog) |
| L.open-webui.9 | L | `.claude/rules/open-webui.md:19` Local regimen: uv run python examples/open_webui/local.py setup (installs examples/open_webui/local-requirements.txt | pass | T: catalogue L.open-webui.9 killed (`test_s1_*`); the valve overwrite = reviewer-8-F2 |
| L.open-webui.10 | L | `.claude/rules/open-webui.md:20` Guard firing records: freshness (test_w1_every_paste_in_equals_the_generator_output) fired unseeded in W5 | pass | T: W1/W2/W3 firing re-proven by catalogue kills (L.open-webui.1/.4/.5) |
| L.ops.1 | L | `.claude/rules/ops.md:3` Env: stdlib-only Python ≥3.12 (the latest line + the | pass | T: no runtime dependency (`test_publication_metadata`) + `ext/bin/cement` under `python -I -S` (N7); `uv run` everywhere = J |
| L.ops.2 | L | `.claude/rules/ops.md:4` Gate = .agent/gate, one command, steps in order: format | pass | T: seeds S01 (missing-module rc 1, durations, full table) + CI step tables |
| L.ops.3 | L | `.claude/rules/ops.md:5` Fast gate (adapts CLAUDE.md Execution Gate command parallel + | pass | T: seeds S01 fast form `.agent/gate tests.<module>` |
| L.ops.4 | L | `.claude/rules/ops.md:6` Static checks + scanners (owner-ruled; config = pyproject.toml, versions | finding L-census | T: seeds S09 format/lint/types (+RUF100), S10 audit, S11 gitleaks, S21 zizmor, S22 shellcheck fire; a suppression's REASON had no check → law-census `reasons` (85 in scope, 0 violations) |
| L.ops.5 | L | `.claude/rules/ops.md:7` Green report (Verification integrity): OUTER skipped = none on | pass | T: seeds S12; CI outer skipped none |
| L.ops.6 | L | `.claude/rules/ops.md:8` Purpose-built gate checks ship the seed that reds them; | pass | T: seeds bullet-count guard + S01-S23 |
| L.ops.7 | L | `.claude/rules/ops.md:9` Tree censuses an ADDITION enters — check a new | pass | T: L24 / authority / submission censuses green with this review's new tests (suite) |
| L.ops.8 | L | `.claude/rules/ops.md:10` Layout: .agent/spec.md = live state, each Tasks row carrying | finding L-ondemand | T: `m3-deferred-validate.py` fires (seeds S04 23/23) yet ran on demand only → owner-approved: gate step `queue`; retired-name sweep = D25 battery |
| L.ops.9 | L | `.claude/rules/ops.md:11` Template rulings: CLAUDE.md, .claude/agents/ + .agent/spec-lint = template copies, | pass | T: (1) prototype outside gates (L.assurance.9); (2) scanners in the gate (B1 steps); (5) ci-gate firing (L.cl.11); (3) = this ledger |
| L.ops.10 | L | `.claude/rules/ops.md:12` Tags (adapts CLAUDE.md Teammates close remove worktrees + branches): | excluded (history/commit-message law: binds no tracked file) | — |
| L.ops.11 | L | `.claude/rules/ops.md:13` Worktrees: .scratch/worktrees/<name> on wt/<name>; MAIN alone writes the primary | excluded (session process: binds no tracked file) | — |
| L.ops.12 | L | `.claude/rules/ops.md:14` On-demand censuses (not gate steps; rerun after editing what | finding L-ondemand | T: each fires on a planted input — p03 `int(row[...])` rc 1, p94 revision outside HEAD's history rc 1, p76 organically (M87 at the stack tip), p10 rc 1 (p143), p46 `--self-test`; none ran in the gate → owner-approved: gate steps `stored-ints`, `anchors`, `revisions` + seeds S25; p10 waits on p143 |
| L.ops.13 | L | `.claude/rules/ops.md:15` Shared mutable resources = one named holder per wave: | excluded (session process: binds no tracked file) | — |
| L.ops.14 | L | `.claude/rules/ops.md:16` Settings: .claude/settings.local.json machine-local; no project .claude/settings.json with a path-keyed | finding L-census | T: law-census (gate step `law`, seeds S24) — no check existed (`settings`: no tracked project `.claude/settings.json`) |
| L.ops.15 | L | `.claude/rules/ops.md:17` Commits (adapts CLAUDE.md Execution Git): <scope> (<trace>): <cause> → | excluded (history/commit-message law: binds no tracked file) | — |
| L.ops.16 | L | `.claude/rules/ops.md:18` Read-and-conform-to set for every brief: the gate above · | excluded (session process: binds no tracked file) | — |
| L.pins.1 | L | `.claude/rules/pins.md:20` Law (owner): every pin at its latest release; a | finding F-pins-1 | T: `.agent/pins` rc 1 — 3 lock transitives BEHIND, no queue row |
| L.pins.2 | L | `.claude/rules/pins.md:21` Where each lives: | pass | J: each pin's home read against its file |
| L.pins.3 | L | `.claude/rules/pins.md:28` Hash-pinned locks (build-constraints.txt, local-requirements.txt) regenerate by the header command | pass | T: `test_p128_the_lock_pins_the_target_and_hashes_every_package` (suite) |
| L.pins.4 | L | `.claude/rules/pins.md:29` Python lines (owner-ruled) = the latest CPython line (CI | pass | T: `.agent/pins` grades each Python line (3.15 full, 3.12 split, Open WebUI 3.12, jail 3.12) |
| L.pins.5 | L | `.claude/rules/pins.md:30` A uv.lock change re-keys every D28 verdict (the content | excluded (session process: binds no tracked file) | a fact about D28 keys; `uv.lock` untouched by this review |
| L.prototype.1 | L | `.claude/rules/prototype.md:8` PROTOTYPE law for good (ops.md Template rulings (1)), outside | pass | T: no `tests/` module names the prototype; prototype-only revisions owe no gate |
| L.prototype.2 | L | `.claude/rules/prototype.md:9` Server = uv run python prototype/webui-demo/app.py (port 8765). Static | pass | T: server readiness via `until curl -sf` (B14) |
| L.prototype.3 | L | `.claude/rules/prototype.md:10` capture.sh drives the story through the API (send → | pass | T: `capture.sh` rc 0, 10 PNGs, duplicate-hash count 0 (positive control 1) |
| L.prototype.4 | L | `.claude/rules/prototype.md:11` Every shot height is MEASURED: both columns scroll internally, | pass | T: measured-height frames complete (B14) |
| L.prototype.5 | L | `.claude/rules/prototype.md:12` Quality floor (p80) = quality.mjs <base> <report.json> (STATE = | pass | T: `quality.mjs` rc 0 at reset + story (B14) |
| L.prototype.6 | L | `.claude/rules/prototype.md:13` density.mjs <url> = words on the first 1600×1000 screen | pass | T: `density.mjs` story 245/16, reset 156/13 (B14) |
| L.prototype.7 | L | `.claude/rules/prototype.md:14` Story Back (p86, owner-ruled): each finished story step checkpoints | pass | J: Back checkpoints exercised along the story only (operator-2 coverage note) |
| L.prototype.8 | L | `.claude/rules/prototype.md:15` Browser = the prototype's own pinned Playwright Chromium (package.json | pass | T: the pinned headless shell via `browser.mjs` (B14) |
| L.prototype.9 | L | `.claude/rules/prototype.md:16` States capture.sh cannot reach (tour beats, Back, free clicks, | excluded (session process: binds no tracked file) | — |
| L.prototype.10 | L | `.claude/rules/prototype.md:17` Japanese UI = static/i18n.js, loaded before app.js: under ?lang=ja | pass | T: `?lang=ja` Latin-node census pass (B14) |
| L.runtime.1 | L | `.claude/rules/runtime.md:10` All 18 user tables are STRICT (sqlite_sequence excepted) ⇒ | pass | T: catalogue mutant L.runtime.1 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.2 | L | `.claude/rules/runtime.md:11` Every stored INTEGER read = _stored_int(value, label, minimum=…, maximum=…) | pass | T: `p03-stored-int-census.py` rc 0 + fires on a planted `int(row[...])` (on demand; L.ops.12) |
| L.runtime.3 | L | `.claude/rules/runtime.md:12` A fresh System — which every CLI invocation constructs | pass | T: catalogue mutant L.runtime.3 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.4 | L | `.claude/rules/runtime.md:13` A validator whose RESULT is discarded is not a | pass | J: judged on the C/S rows of `src/` |
| L.runtime.5 | L | `.claude/rules/runtime.md:14` verify_drafts + promote_function read the caller's clock_us INSIDE BEGIN | pass | T: catalogue mutant L.runtime.5 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.6 | L | `.claude/rules/runtime.md:15` Public writes carry a commit-then-raise window: a durable commit | pass | J: judged on the C/S rows of `src/` |
| L.runtime.7 | L | `.claude/rules/runtime.md:16` Authorization or validation written as a loop over members | pass | J: judged on the C/S rows of `src/` |
| L.runtime.8 | L | `.claude/rules/runtime.md:17` A second SQLite store (shadow.py ShadowStore) carries every Store | pass | T: catalogue mutant L.runtime.8 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.9 | L | `.claude/rules/runtime.md:21` mode=ro protects ONLY the main database file — TEMP | pass | T: catalogue mutant L.runtime.9 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.10 | L | `.claude/rules/runtime.md:22` Deny-by-default authorizer allowlists by NAME, split into a readable-bare | pass | T: catalogue mutant L.runtime.10 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.11 | L | `.claude/rules/runtime.md:23` Classify on sqlite_errorcode alone: SQLITE_AUTH(23) is reachable only from | finding reviewer-4-R1 | T: catalogue mutant L.runtime.11 killed; the clause's denial path was stale (`_ReadOnlyViolation`, not IntegrityError) |
| L.runtime.12 | L | `.claude/rules/runtime.md:24` VACUUM inside a read block is refused by the | pass | T: read-capability battery VACUUM parity test (suite) |
| L.runtime.13 | L | `.claude/rules/runtime.md:25` Convert a path to a file: URI with Path.absolute().as_uri(); | pass | T: catalogue mutant L.runtime.13 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.14 | L | `.claude/rules/runtime.md:26` Test-only pragma injection (reverse_unordered_selects) uses a named helper that | pass | J: judged on the C/S rows of `src/` |
| L.runtime.15 | L | `.claude/rules/runtime.md:27` Read-only proof and single-snapshot lifetime are separate guarantees: a | pass | T: catalogue mutant L.runtime.15 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.16 | L | `.claude/rules/runtime.md:31` verify_function raises for EXACTLY five conditions (unregistered operation; malformed | pass | T: catalogue mutant L.runtime.16 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.17 | L | `.claude/rules/runtime.md:32` Function identity = verified-content identity: entry_seal is cement-promotion-v2 minus | pass | T: catalogue mutant L.runtime.17 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.18 | L | `.claude/rules/runtime.md:33` Draft eligibility is RECONSTRUCTION, not status filtering: current revision, | pass | T: catalogue mutant L.runtime.18 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.19 | L | `.claude/rules/runtime.md:34` resolve pays full verification of the selected version on | pass | T: catalogue mutant L.runtime.19 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.20 | L | `.claude/rules/runtime.md:35` serving(expected_function_hash=H) keys its own cache entry per H (_SERVING_CACHE_MAX | pass | T: catalogue mutant L.runtime.20 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.21 | L | `.claude/rules/runtime.md:36` function_report's six detail lists each keep one documented order | pass | T: catalogue mutant L.runtime.21 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.22 | L | `.claude/rules/runtime.md:37` Cursor pagination over per-call transactions is not a snapshot; | pass | J: judged on the C/S rows of `src/` |
| L.runtime.23 | L | `.claude/rules/runtime.md:38` An exported bundle is NOT byte-reproducible across clean runs: | pass | J: judged on the C/S rows of `src/` |
| L.runtime.24 | L | `.claude/rules/runtime.md:39` No cement_runtime submodule import is store-free — the package | pass | T: catalogue mutant L.runtime.24 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.25 | L | `.claude/rules/runtime.md:43` ValidationError subclasses ValueError, so a helper raising its own | pass | J: judged on the C/S rows of `src/` |
| L.runtime.26 | L | `.claude/rules/runtime.md:44` raise X from None INSIDE an except block leaves | pass | T: catalogue mutant L.runtime.26 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.27 | L | `.claude/rules/runtime.md:45` Ownership, not exception class, decides translation: a caller's own | pass | J: judged on the C/S rows of `src/` |
| L.runtime.28 | L | `.claude/rules/runtime.md:46` A guard protecting a window is meaningless for a | pass | J: judged on the C/S rows of `src/` |
| L.runtime.29 | L | `.claude/rules/runtime.md:47` Filesystem writers: one os.lstat + stat.S_ISREG beats chained pathlib | pass | J: judged on the C/S rows of `src/` |
| L.runtime.30 | L | `.claude/rules/runtime.md:51` Exit classes: 2 usage/validation, 3 absent, 4 conflict (the | pass | T: catalogue mutant L.runtime.30 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.31 | L | `.claude/rules/runtime.md:52` argparse option abbreviation is OFF on every node (p49, | pass | T: catalogue mutant L.runtime.31 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.32 | L | `.claude/rules/runtime.md:53` Derive the leaf census from _parser() inside the test, | pass | T: X23 + parser-shape digest census (`tests/test_cli_channels.py`); the clause prescribes test design (catalogue note) |
| L.runtime.33 | L | `.claude/rules/runtime.md:54` Where one leaf routes the same argument to two | pass | J: judged on the C/S rows of `src/` |
| L.runtime.34 | L | `.claude/rules/runtime.md:55` A CLI-owned bound over an unclamped library projection makes | pass | J: judged on the C/S rows of `src/` |
| L.runtime.35 | L | `.claude/rules/runtime.md:56` Linux refuses an exec argument well below 1 MiB | pass | J: judged on the C/S rows of `src/` |
| L.runtime.36 | L | `.claude/rules/runtime.md:57` Ledger creation: operation register alone constructs System(create=True), after grading | pass | T: catalogue mutant L.runtime.36 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.37 | L | `.claude/rules/runtime.md:58` Interrupt (p25): the process entry entry (cement script + | pass | T: catalogue mutant L.runtime.37 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.38 | L | `.claude/rules/runtime.md:59` stdout is never flushed by main (documented limit, README | pass | J: judged on the C/S rows of `src/` |
| L.runtime.39 | L | `.claude/rules/runtime.md:60` Human-read renderings of stored values (function read text) pass | pass | T: catalogue mutant L.runtime.39 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.40 | L | `.claude/rules/runtime.md:61` Entity ids: one grammar owner _entity_id(value, label) (_ENTITY_ID, bounded | pass | T: catalogue mutant L.runtime.40 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.41 | L | `.claude/rules/runtime.md:65` System.events() dicts key the event name under kind; there | pass | T: catalogue mutant L.runtime.41 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |
| L.runtime.42 | L | `.claude/rules/runtime.md:66` Every event producer and branch pins its own payload | pass | T: catalogue mutant L.runtime.42 killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0) |

### Findings (code review)

Close: 430/430 rows adjudicated (pass 277, finding 72, excluded 81); 75 findings (fixed 74, retired 1); full gate = CI run 40333517498 on the commit landing this table (both legs, every step rc 0; Ran 1651 / 1650).

| id | sev | anchor | proof | status |
|---|---|---|---|---|
| SEC-1 | minor | `src/cement_runtime/store.py:557` | out-of-band trigger `sqliteXhidden` passed the live-schema census (`LIKE 'sqlite_%'`: `_` = any char) | fixed `7ce5447` |
| reviewer-3-F1 | major | `src/cement_runtime/system.py:4906` | pinned-version program load outside `_pin_checks`' containment: `resolve` + `function versions` raised IntegrityError | fixed `98ea105` |
| reviewer-2-F1 | major | `src/cement_runtime/system.py:650` | `_structural_edit_leaves` on a full-width-only v2 layout → `max()` of an empty sequence | fixed `a7f9bc4` |
| reviewer-5-F1 | major | `src/cement_runtime/projection.py:327` | `draft_program` emitted layouts its own parser refuses (single-line input; U+0130 title) | fixed `a7f9bc4` |
| reviewer-4-F1 | major | `src/cement_runtime/system.py:520` | stored malformed JSON surfaced as ValidationError / exit 2, not IntegrityError / exit 5 (20 stored-row sites) | fixed `11f657b` |
| reviewer-4-F3 | major | `src/cement_runtime/store.py:734` | existing-only open under a missing parent → exit 2 | retired: D13 pins exit 2 for that open (contract) |
| reviewer-4-F2 | major | `src/cement_runtime/store.py:718` | relative ledger path re-resolved per open → one System read + wrote a second ledger after `chdir` (+ `shadow.py:232`) | fixed `d42467e` |
| reviewer-6-F1 | minor | `src/cement_runtime/shadow.py:246` | new shadow file + ledger created `0600 & ~umask`, no `fchmod` (+ `store.py:742`) | fixed `117e90a` |
| reviewer-1-F1 | major | `src/cement_runtime/system.py:2067` | receipt envelope consumed the depth/item budget: legal boundary values refused at review (+ challenge, supersession, reader) | fixed `37a1a62` |
| reviewer-7-F2 | minor | `src/cement_runtime/cli.py:656` | export temporary name passed NAME_MAX for a legal 244-byte basename | fixed `37a1a62` |
| reviewer-9-F2 | major | `examples/command_source/command_source.py:138` | protocol wrapper consumed the input's depth/item budget (= reviewer-1-F1 class) | fixed `37a1a62` |
| reviewer-1-F3 | minor | `src/cement_runtime/system.py:1533` | `revise_operation` at the maximum revision → OverflowError | fixed `78362fa` |
| reviewer-7-F1 | major | `src/cement_runtime/cli.py:897` | `function read` said a suspended selected version answers (resolve exits 6) | fixed `82d31a4`; its test repair owner-approved |
| reviewer-15-F1 | major | `src/cement_runtime/cli.py:989` | projected `function read` omitted the program + the structure-only assumption (Decision M4) | fixed `d14ad45` |
| reviewer-2-F2 | major | `src/cement_runtime/system.py:6645` | `learning_cases` reported `nothing_to_learn` while a republish would restore `follow` | fixed `dc55023` |
| reviewer-1-F2 | minor | `src/cement_runtime/system.py:2141` | `review` re-loaded + re-parsed the projection program per member (12 loads vs 1) | fixed `d47fd36` |
| reviewer-6-F2 | minor | `src/cement_runtime/signature.py:357` | a non-ASCII namespace raised UnicodeEncodeError, not ValidationError | fixed `93bdd75` |
| reviewer-8-F1 | major | `examples/open_webui/cement_filter.py:366` | a duplicate admit returned before finishing a `prepared` disagreement | fixed `110aa60` |
| reviewer-8-F2 | major | `examples/open_webui/local.py:235` | `provision` overwrote saved shadow valves on each `serve` | fixed `1eb7570` |
| reviewer-9-F1 | major | `examples/nucllei/cement_nucllei.py:161` | concurrent passes lost one operation's projectability ruling (state-file read-modify-write) | fixed `8959e51` |
| reviewer-15-F2 | minor | `examples/nucllei/cement_nucllei.py:756` | argparse help + usage errors English (Decision: model-facing output Japanese) | fixed `c77a051` |
| reviewer-9-F3 | minor | `examples/nucllei/cement_nucllei.py:747` | `follow` with no published version said `版 0 が答える` | fixed `c77a051` |
| SEC-3 | major | `examples/nucllei/skills/cement.md:36` | model answers passed through heredocs: an answer line equal to the delimiter ends it and runs the rest in the user's jail (+ `cement-learn.md:43`) | fixed `5e7d596` |
| L.nucllei.7 | minor | `examples/nucllei/cement_nucllei.py:334` | catalogue mutant L.nucllei.7 (`use` keeps its hand-over file) survived all 47 `tests.test_nucllei_example` tests | fixed `5e7d596` |
| L.open-webui.2 | minor | `examples/open_webui/generate.py:27` | catalogue mutant L.open-webui.2 (no `import importlib.machinery`) survived W1 + N7 | fixed `1f3b491` |
| SEC-2 | info | `src/cement_runtime/signature.py:107` | comment misstated which keys satisfy the cofactorless equation (code refuses them correctly) | fixed `b7b27ec` |
| reviewer-3-F2 | minor | `src/cement_runtime/system.py:4088` | `resolve` docstring cited the pre-cache cost as current | fixed `b7b27ec` |
| reviewer-4-F4 | minor | `src/cement_runtime/system.py:7496` | stale comment `other records are joined.` | fixed `b7b27ec` |
| reviewer-4-F5 | minor | `src/cement_runtime/store.py:576` | `never raised to callers` vs `_ReadOnlyViolation` escaping `Store.transaction` | fixed `b7b27ec` |
| reviewer-4-F6 | minor | `src/cement_runtime/models.py:1` | `Small immutable public values` vs plain dict records | fixed `b7b27ec` |
| reviewer-5-F2 | minor | `src/cement_runtime/errors.py:16` | ConflictError doc omitted the identical source-id repeat | fixed `b7b27ec` |
| reviewer-6-F3 | minor | `src/cement_runtime/comparator.py:4` | `single walk` vs nested `unordered` revisits | fixed `b7b27ec` |
| reviewer-6-F4 | minor | `src/cement_runtime/learning.py:245` | publish `rerun … without new rows` vs a failed rerun adding a report + event | fixed `b7b27ec` |
| reviewer-6-F5 | minor | `src/cement_runtime/shadow.py:915` | `every stored field` omitted `artifact_hash` + `comparator_json` | fixed `b7b27ec` |
| reviewer-7-F3 | minor | `src/cement_runtime/cli.py:939` | comparator readout `letter case ignored` without the ASCII-only qualifier | fixed `b7b27ec` |
| reviewer-11-F1 | major | `skills/cement-learn/SKILL.md:27` | exit 2/3 `wrote nothing` vs `learn merge` exit 3 after a committed review | fixed `dbae3cc` |
| reviewer-11-F2 | major | `README.md:543` | retention + erase `one transaction` vs two files (+ `docs/threat-model.md:88`) | fixed `dbae3cc` |
| reviewer-11-F3 | minor | `README.md:606` | every write `one event` + every refusal `writes nothing` vs compile + commit-then-raise | fixed `dbae3cc` |
| reviewer-11-F4 | major | `examples/open_webui/README.md:8` | paste-in path omitted Python ≥3.12 (paste-ins SyntaxError on 0.12.3's stock 3.11) | fixed `dbae3cc` |
| reviewer-11-F5 | minor | `examples/open_webui/README.md:11` | `about 370 KB` vs 504-526 kB (= reviewer-8 register) | fixed `dbae3cc` |
| reviewer-11-F8 | minor | `README.md:349` | `an argument list above 131,071 bytes` = the per-argument bound | fixed `dbae3cc` |
| reviewer-1-R1 | minor | `README.md:678` | `cannot make it fail` unqualified vs `expected_revision` | fixed `dbae3cc` |
| reviewer-8-F3 | major | `examples/open_webui/cement-learn/SKILL.md:16` | `a refusal wrote nothing` vs publish committing before refusing | fixed `dbae3cc` |
| reviewer-8-F4 | minor | `examples/open_webui/cement_learning.py:245` | `never answers until a person switches it on` vs `follow` (= reviewer-2 register) | fixed `dbae3cc` |
| reviewer-15-F5 | minor | `examples/nucllei/README.md:60` | `less than 10 minutes` vs the inclusive bound (= reviewer-9-F4) | fixed `dbae3cc` |
| SEC-4 | minor | `.gitignore:11` | `<ledger>.shadow` + `-journal` (plaintext inputs + answers) not ignored | fixed `b0418f8` |
| reviewer-4-R1 | minor | `.claude/rules/runtime.md:23` | law said an authorizer denial lands as IntegrityError / exit 5; code raises `_ReadOnlyViolation` | fixed `b0418f8` |
| SEC-5 | minor | `examples/nucllei/cement_nucllei.py:706` | pre-switch `read` listing printed C1/bidi/zero-width characters raw | fixed `dd853b9` |
| operator-2-F1 | minor | `prototype/webui-demo/static/app.js:817` | reload reset the band narration despite a populated session | fixed `0699e05` |
| operator-2-F3 | minor | `prototype/webui-demo/static/app.js:845` | default band named Cement beyond the p95 ruling (= reviewer-15-F4) | fixed `0699e05` |
| reviewer-15-F3 | minor | `prototype/webui-demo/static/app.js:795` | `six-check verification and caches nothing` = an unlabelled false runtime claim (+ `demo.py:1437`) | fixed `0699e05` |
| operator-2-F2 | major | `prototype/webui-demo/demo.py:1256` | billing q12 resent → support 2 → promoted, vs the Decision `every scope stays at support 1` + UI `never repeats` | fixed `8669977` (owner-ruled: the Decision + UI wording moves, the runtime stays) |
| F-pins-1 | minor | `examples/open_webui/local-requirements.txt` | `.agent/pins` rc 1: 3 lock transitives BEHIND with no queue row | fixed `d551bff` |
| reviewer-10-F1 | major | `.agent/skip-census:69` | `_aliases` oscillated forever on a cross-module alias collision (gate step never ends) | fixed `afa2298` |
| reviewer-10-F4 | major | `.agent/decisions/m3-deferred-validate.py:124` | an unfinished acceptance on a continuation line passed | fixed `3a717f3` |
| reviewer-10-F2 | major | `.agent/survivor-triage:239` | kills credited without a pristine control run (+ `.agent/kill-check:73`) | fixed `4bb5304` |
| reviewer-10-F3 | major | `.agent/survivor-triage:66` | class subjects dropped decorator + field lines from scope | fixed `7ce9c0f` |
| reviewer-10-F5 | major | `.agent/decisions/m3u5a-battery-validate.py:199` | 4 battery graders accepted comment-only assertions (+ `m3u5a-suite-validate.py:131`, `m3u5b-battery-validate.py:397`, `m3u6a1-battery-validate.py:273`) | fixed `51683f7` |
| reviewer-10-F6 | major | `.agent/decisions/wave_validate.py:656` | `ColumnTables` never enforced its seed floor | fixed `41fd3e5` |
| reviewer-10-F7 | major | `.agent/decisions/m3u6a2-battery-validate.py:144` | self-test credited a zero counter | fixed `5e2db62` |
| reviewer-10-F8 | minor | `.agent/validate-anchors:55` | files reread per row (+ `m3u5a-suite-validate.py:127`) | fixed `2cefd87` |
| reviewer-10-F9 | minor | `.agent/seeds:7` | `every recorded recipe` vs the groups' actual coverage | fixed `bd203c8` |
| reviewer-12-F1 | minor | `tests/test_system.py:4877` | lock-order test sampled `time.monotonic()` after each call returned: a permitted schedule failed it | fixed `0db6dcf` (owner-approved) |
| reviewer-12-F2 | minor | `tests/test_system.py:15630` | one-snapshot report test delegated commit/cursor/batch calls + allowed transaction control: a mid-report commit passed | fixed `9d50ba2` (owner-approved) |
| reviewer-13-F1 | minor | `tests/test_cli.py:3541` | export exit-map token assertion compared the actual value with itself for exits 2-5 | fixed `f1a9470` (owner-approved) |
| reviewer-13-F2 | major | `tests/test_read_capability_census.py:173` | read censuses classified SQL by its first token: a write behind a SELECT, comment or CTE passed (+ `:209`, `test_read_capability_battery.py:792`) | fixed `9d50ba2` (owner-approved) |
| reviewer-13-F3 | minor | `tests/test_retention_battery.py:406` | `if False` disabled the expected prune digest | fixed `f1a9470` (owner-approved) |
| reviewer-13-F4 | major | `tests/test_proposal_binding_battery.py:154` | SQL recorder returned raw cursors: a chained query ran unrecorded (class sweep: D13 + D17 recorders) | fixed `9d50ba2` (owner-approved) |
| reviewer-14-F1 | minor | `tests/test_function.py:741` | entry-cap pin repeated ONE entry: a cap loosened by one still raised as a duplicate | fixed `dcbda01` (owner-approved) |
| L-ondemand | minor | `.claude/rules/ops.md:14` | p03, p76, p94, p10 + `m3-deferred-validate.py` fire on planted input yet no gate step runs them (an unkeyed departure from `CLAUDE.md` `Engineering`: a purpose-built check is wired into the gate); p76 went red at this review's stack tip (M87) with the gate green | fixed `ad0b5b2` (owner-approved; p10 waits on p143) |
| L-census | minor | `CLAUDE.md + .claude/rules (6 clauses)` | frontmatter quoting + live globs, `@` imports, project settings, dangling links, machine paths, suppression reasons: tool-decidable, no check; no proof a gate run leaves the tree clean | fixed `374750b` |
| operator-1-F1 | minor | `examples/open_webui/cement-learn/SKILL.md:79` | live pass reported `support 1` for a case at 2: the skill's support came from the pre-merge listing (+ nucllei skill) | fixed `6a70852`; live rerun = deferred row |
| F-ledger-1 | minor | `.agent/review.md:489` | `## Security review 2 (MAINTAIN, request)` heading lost in `686e86e`'s splice | fixed in the commit landing this table |
| reviewer-11-F6 | minor | `.agent/deferred.md:27` | p137 `0.12.3 is both the latest release` vs p144 (0.12.4 released) | fixed in the commit landing this table |
| reviewer-11-F7 | minor | `.agent/deferred.md:29` | p142 `cold resolve plus the capture's cold verification` vs capture reusing resolve's entry | fixed in the commit landing this table |

## Template refresh → agents@7e8ad36 (MAINTAIN, request) — target = the diff this commit lands, base `e7336bd`

Template delta = `Authoring` `@path` bullet (NEW), MAINTAIN request kinds `+ a code review`, `.agent/spec-lint` SC2016 directive. The first copy dropped that directive (a local line since `95fb113`) → gate step `shell` rc 1; owner ruling at the session's question = fix upstream: agents@7e8ad36 carries it inline, recopied by `copy-template`. Owner ruling: README `~/.ssh/id_ed25519` (`:226`, `:228`, `:255`) = the reader's own key in a signing example, kept. MAIN alone; 10 lenses fixed before the diff was read.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | template fidelity | pass | `cmp` rc 0 vs agents@7e8ad36: `CLAUDE.md` (`claude/CLAUDE.project.md`), 6 roles, `.agent/spec-lint` (100755); `copy-template --check` → `The template files are current.` |
| R2 | obligation coverage | pass | `@path` → practice holds: live law's one `@` import = `CLAUDE.md:1` `@.agent/spec.md` (other `@` hits = npm scopes, decorators, prose), rules + roles named by plain path; `a code review` → Template rulings (3) already gives every request close its pass here; SC2016 → upstream + `ops.md` Template rulings (template copies incl. `.agent/spec-lint`, fixes land upstream). |
| R3 | old forms | pass | `queued rows, a security review` + `the single quotes hold the awk program` → `rg --hidden -g '!.git' -F` rc 1 each; HEAD controls 1 + 2 hits. |
| R4 | spec preservation | pass | `.agent/spec.md` diff 0 bytes (layout clause unchanged); `.agent/spec-lint` rc 0. |
| R5 | check strength: `shell` | pass | `.agent/shellcheck` rc 0, 11 scripts; suppression scope = the old one (one inline directive on the awk call). |
| R6 | check strength: S22 | pass | literal anchor → `substitute(r"(?m)^# shellcheck disable=SC2016\b.*\n")`, count-1 guard kept, same planted input + expectation; 3/3 MATCH at `e7336bd` (old seed) and on tree `10f118c` (new seed). |
| R7 | check strength: S03 | pass | `.agent/spec-lint` = a comment line changed; S03 2/2 MATCH before (`e7336bd`) + after (tree `85e47f5`); agents@7e8ad36 `check-spec-lint` 18/18 under gawk, busybox awk, Debian mawk. |
| R8 | law consistency | pass | `ops.md` Static checks (inline directive per false positive) holds; `gate-checks.md` S22 record (`without its SC2016 directive`) unchanged + true. |
| R9 | portability + settings | pass | live-law sweep (home paths, other repos, machine tools) → README `~/.ssh` alone (ruled); no project `.claude/settings*.json`; `upstream-sync.md` absent since `9194f41`. |
| R10 | queue | pass | no new finding outside the contract ⇒ no row born; on-demand `p10-scratch-census.py` rc 1 (5 unmarked, p135/p136 contracts) reproduces at `e7336bd` = open p143; grader PASS. |
## Security review 2 (MAINTAIN, request) — target = the implementation at `5ae4d9f`, fixes `92f62da` (F1-F5), `2fc7e8b` (F6, this section) and the `filter (MAINTAIN):` commit after it (F8)

Owner body: threat surface from `Intent` + `Artifacts`; the committed scanners run (a stack with none = a finding), then a manual pass over remotely reachable code on a check set fixed before any code was read: each untrusted input traced to every sink it reaches; trust model: env vars + CLI flags trusted, the server = the enforcement boundary, framework auto-escaping holds outside raw-HTML sinks; each finding = severity + `file:line` + a red test or repro; every finding above informational fixed, the rest → `.agent/deferred.md`. MAIN alone (security vocabulary stays off the teammate route); advisor read the fix plan before the owner questions. Surfaces: L library + CLI; O Open WebUI paste-ins (every signed-in chat user through the tools and the `/api/chat/completed` body; admins through the learning tool + action) + `local.py`; N nucllei `ext/bin/cement` (the chat model's `run_shell`); K skills; P prototype server (loopback); X other examples; G CI + gate tooling. Scope note: 66 commits since review 1 (`99f260a`) added signatures, retention/erase, comparators and shadow sampling; those got the deepest reading. Owner rulings (AskUserQuestion): F1 "Keep + document" (one model per deployment); F2 "Skip, record dropped".

| id | row | verdict | basis (MAIN-verified) |
|---|---|---|---|
| SC1 | `uv audit --locked` | pass | rc 0, 34 packages, 0 vulnerabilities; control: a throwaway project locking `jinja2==2.10` → rc 1, 22 advisory ids. |
| SC2 | gitleaks, whole HEAD history | pass | `.agent/gitleaks` rc 0; control: a planted AWS key pair + `ghp_` token (`gitleaks dir` on a scratch dir) → rc 1. |
| SC3 | ruff `S` + its suppressions | pass | `ruff check --select S` rc 0 over `src/` + `examples/` (paste-ins included); control: a `shell=True` + `pickle.loads` file → 2 hits, rc 1. Every `S` noqa re-read true: S608 ×5 (system.py ×3 code-chosen fragments; shadow.py `_INSERT` = a fixed column list, `_leave_admitted` = column names from `cancel`/`fail` literals), S603 ×5 argv lists without a shell, S101 ×7 narrowing, S105 Open WebUI's public no-login default, S310 ×2 loopback, S102 the digest-checked embedded library. |
| SC4 | zizmor `.github/` | pass | rc 0 over `gate.yml` + `dependabot.yml`; control: a scratch workflow (`pull_request_target`, `${{ }}` in `run:`, unpinned checkout) → rc 14, 5 findings. |
| SC5 | ShellCheck, every tracked script | pass | 11 scripts, rc 0; control: `rm -rf $1/*` → rc 1. |
| SC6 | `.agent/owui-audit` | pass (held) | rc 0: 127 findings in 15 packages, each held on open p137; the nonzero count is the scanner's own positive signal. |
| SC7 | a scanner per stack | finding F7 (informational) → p145 | Python `src/` + `examples/` (paste-ins included): ruff `S` (+ mypy over `src/`); `ext/bin/cement` = scanned sources + the generator's `LOADER` string; Actions + Dependabot: zizmor; shell: ShellCheck; `uv.lock`: `uv audit`; Open WebUI lock: owui-audit (on demand); `build-constraints.txt`: none → F7; prototype Python + JS + `pnpm-lock.yaml`: outside every gate (Template ruling (1)), by hand ruff `S` 1 (S311, the seeded latency RNG, `demo.py:674`), `pnpm audit` 0; `.agent/` tools run on this repository's own inputs alone. |
| M1 | SQL injection | pass | every dynamic statement = code-chosen fragments (placeholder lists, `{order}`, `{clause}`, `{group}`, a predicate list, fixed column lists), values bound `?`; `PRAGMA user_version` f-strings = module constants; examples + prototype issue no SQL of their own except `outbox.py` (static). |
| M2 | shell / process injection | pass | `src/` spawns nothing; `command_source` = `Popen` over the operator's argv flags, the request on stdin, no shell; `local.py` fixed argv; prototype `_cli` argv lists; nucllei documents by `write_file` + `--input-file`; no `${{ }}` in a `run:` (zizmor). |
| M3 | template + XML entities | pass | no template engine or XML parser; `_shadow_prompt` builds a model prompt by f-string, nothing evaluates it. |
| M4 | file paths | pass | CLI paths = flags; `_read_regular` = `O_NONBLOCK` + `fstat` regular + bounded read, and `function eval` verifies and parses the same bytes from one read; export temp `O_EXCL` 0600 + `lstat` guard before `os.replace`; `ShadowStore` refuses symlinks + non-regular files, creates `O_EXCL` 0600, opens existing-only where asked; valves admin-set; nucllei `_discard` only under the resolved `$CEMENT_HOME/in/`; prototype static = `resolve()` + parent check. |
| M5 | authn/authz + escalation | findings F1, F3 | pass elsewhere: learning tool role `admin` per call (`_run`); action role `admin` + an offered value + confirmation `True`; chat tool read-only, `record_answer` writes nothing; filter = the one proposal writer; actors from server-side `__user__`; no model-callable path to `set_switch` (AST pins green); library partition-scoped (each statement binds `partition` or follows a partitioned lookup; `shadow_capture` finds receipts by partition + operation); nucllei = the jail (README limit). |
| M6 | session + token handling | pass | nucllei ticket `t_` + `secrets.token_hex(8)`, consumed by `record`, 24 h; observation id = deployment + chat + message + call, and 0.12.3 `/api/chat/completed` runs `verify_chat_ownership`, so a user cannot pre-claim another user's ids; `local.py` secret + password 64 hex, 0600; the prototype has no session. |
| M7 | secrets + crypto | pass | gitleaks clean; `signature.py` re-read against RFC 8032 §5.1.7 under its strict policy: canonical A + R (`y < p`; `x = 0` with sign 1 refused), `S < L`, `[8]A ≠ O` + `[L]A = O`, cofactorless equation, the complete a = −1 unified addition, `k = SHA-512(R‖A‖M) mod L`; SSHSIG wire strict (magic, version 1, exact key blob, exact namespace, hash ∈ {sha256, sha512}, trailing bytes refused); allowed signers refuse patterns, unknown options, certificate authorities + FIDO keys; ids `uuid4` / `os.urandom` / `secrets`; no TLS client past loopback; `function_hash` unkeyed + documented as integrity, not origin. |
| M8 | unsafe deserialization + eval | pass | no pickle, marshal or YAML; `exec` = the loader over digest-checked embedded sources in admin-pasted code; projection + comparator = closed interpreters (no eval; the comparator's regexes run on ≤ 64-char strings); strict `parse_json` on every untrusted parse (CLI stdin, bundles, nucllei input/output, shadow answers after `json.loads`). |
| M9 | raw-HTML + rendering sinks | finding F6 | prototype `app.js`, `i18n.js`, `demo.py` unchanged since review 1's M9 pass (`git diff --quiet 99f260a` rc 0); Open WebUI tools return JSON; notifications reach the sender's session alone (R7); `function read` = a terminal rendering of untrusted values → F6. |
| M10 | SSRF | pass | outbound = `_ask` through Open WebUI's own router to the admin-set model (F3 closes the client-routed case), `local.py` to its own loopback instance, `fetch-tool` to fixed GitHub URLs behind a sha256 refusal; no tool or filter fetches a URL. |
| M11 | data exposure | pass + finding F8 (low), fixed | no secret in a log (gitleaks; the model key by environment alone); errors carry `CementError` text (paths admin-set, review 1 M5.3 S6); the ledger + shadow file are plaintext = the deployment's volume encryption (threat model); F8 log injection. |
| M12 | dependencies + supply chain | pass + F7 | `uv.lock` hashed; actions SHA-pinned, `contents: read`, `persist-credentials: false`, `pull_request` (never `_target`), and a fork PR's `actions/cache` save stays scoped to that PR, so it cannot plant D28 verdicts on `main`; gitleaks/zizmor/ShellCheck sha256-pinned; the Open WebUI lock hash-pinned (p128); driver.js + fonts byte-checked; Dependabot cooldown 7 days; owui-audit's `uvx pip-audit` install is unhashed (on demand) → register. |
| M13 | resource exhaustion | findings F2, F5 | bounds hold elsewhere: JSON 1 MiB / depth 64 / 100,000 items, bundles 64 MiB, signatures 64 KiB, allowed signers 1 MiB; projection linear; the comparator walks each value once; the filter caps 256 hits per reply, 1,024 queued drops, 64 queued samples, one worker. Register R-b, R4. |
| M14 | prompt injection through retained data | pass | the CLI, Open WebUI and nucllei learning skills each treat proposal input, output and provenance as chat-user data, never instructions (review 1 F2 pins green); shadow proposals fall under "each proposal"; the learning model holds no switch tool (AST pin); F3 closed the route that labelled client text as the shadow model's. |

Findings (each red at its tag first, fixed, green in the gate):
- F1 (medium as found → documentation by owner ruling) `examples/open_webui/cement_filter.py:384` `bypass_filter=True`: Open WebUI 0.12.3 `check_model_access` returns at once on it (`utils/access_control/__init__.py:359-380`, "skip all access checks"; `routers/openai.py:1426-1460`), and `generate_chat_completion` runs no filter either way, so p136-owui W3/O3's reason was false. Fix `92f62da`: example README `## Shadow answers` names the skip, contract erratum, rule; pin `test_s5_the_readme_states_that_sampling_skips_model_permissions` (red at `archive/secrev2-shadow-red` = `52e3cc9`).
- F2 (medium) `src/cement_runtime/system.py:4686` `shadow_capture` verified through `serving(expected_function_hash=H)` = one cache key per named hash; a forged covered result names any hash a user has seen. Repro at `5ae4d9f` (300 entries, 10 versions): 9 old-hash admissions turned a 13 ms warm `resolve` into a 535 ms cold one, and each old-hash admission rebuilt its receipt uncached (~120 ms). Fix `92f62da`: the plain entry + a local hash compare (p141 closed by its bench), and the filter samples a hit only while `_serves` (owner), else `dropped`. Pins `CaptureCostTests` ×2 + `test_s5_a_hit_whose_version_no_longer_serves_is_dropped` (owner-approved replacement of `test_s5_the_version_that_served_the_hit_decides`; the original fires on the fix).
- F3 (low; outlet half driven live: on 0.12.3 a forged `/api/chat/completed` body's `model_item.direct` set `request.state.direct` on the outlet's request; the routing to the client's socket read from source) `_ask` reused the outlet's request: `main.py:1199-1201` + `2142-2143` set `request.state.direct` from the client's `model_item` with no enablement check, `utils/filter.py:59-62` takes `filterIds` from that item, and `utils/chat.py:186-192` answers a matching model id from the client's own socket, so a client could write answers recorded under the admin's shadow model. Fix `92f62da`: the worker fails the sample before `_ask`; pin `test_s5_a_direct_connection_never_answers_a_sample`. Live after the fix (Open WebUI 0.12.3, paste-ins, stub model): a real covered hit sampled, a forged older-hash body → `dropped` and a forged direct body → `failed`, 0 model calls for either, 0 tracebacks.
- F4 (low) `src/cement_runtime/shadow.py` `admit`/`drop` graded observation ids for Cc alone, while `finish_shadow`'s source id (`_text`) refuses Cf/Zl/Zp: a U+200B id → `record_shadow` and every finish retry raised `ValidationError`, the row `prepared` for good. Fix `92f62da`: `_observation_id` = the `_text` grammar; pin `test_s2_an_observation_id_takes_the_source_id_grammar`.
- F5 (low) `examples/open_webui/cement_filter.py` `_drop` built `System(...)` (a full `PRAGMA integrity_check`: 18 ms at 25 MB, 74 ms at 201 MB) for each of up to 1,024 drops one forged body queues. Fix `92f62da`: the shadow file alone; pin `test_s5_a_dropped_hit_never_opens_the_ledger`.
- F6 (low) `src/cement_runtime/cli.py` `_render_listing` printed C1 controls, bidi controls, zero-width, tag + separator characters from retained answers raw, so the version a person reads before switching it on could display other text than the bytes that answer. Fix `2fc7e8b`: `_visible` = each such character as its JSON escape, lossless; `--json` raw; README sentence; pin `test_function_read_escapes_characters_a_terminal_hides` (red at `archive/secrev2-read-red` = `9039521`).
- F7 (informational) → p145.
- F8 (low; born informational as p146 from a source read, re-rated on its repro) `examples/open_webui/cement_filter.py` `outlet` logged `cement: %s` notes that embed client call ids from the `/api/chat/completed` body: repro at `2fc7e8b` = one malformed `record_answer` call whose id holds `\n2026-10-25 22:30:00,000 | INFO | admin password reset by support` → one WARNING record printed as two log lines, the second a forged INFO record (CWE-117). Fix (the `filter (MAINTAIN):` commit after `2fc7e8b`): `_loggable` writes Cc/Cf/Zl/Zp characters as `unicode_escape` text; the sender's own notification keeps the text (R7); p146 closed; pin `test_e4_a_client_call_id_never_forges_a_log_line` (red at `archive/secrev2-log-red` = `f6e7e4f`).

Register (by design or documented; no change):
- R-a `local.py` leaves Open WebUI's own files (`webui.db`, `data/`) to the user's umask; Cement's ledger, shadow file, secret + password are 0600; the regimen runs on a single-user host.
- R-b every `System(...)` (each CLI call, each chat tool call) runs a full `PRAGMA integrity_check`, ~0.35 ms/MB (74 ms at 201 MB); ledger growth by fabricated proposals (R4) raises it for every user (quota class, threat model `Deliberately absent`).
- R-c a sample now pays two warm serving reads (the `_serves` gate + the capture), a deep copy each (52-60 ms at 1,000 entries).
- R-d owui-audit installs pip-audit through `uvx` without hashes; on demand, outside the gate.
- Carried from review 1: R1 (fabricated `record_answer` pairs, still), R2, R4, R5, R6, R7, R8, R9; R3 superseded by p35 (a cold `resolve` after each ledger commit, 35.5 s at the 50,000-entry cap, still reachable by any chat user); R10 retired (`.open-webui/admin-password` exists, 0600).

## Dependency + toolchain upgrade (MAINTAIN, request; tiers `data` for the locks, `kernel` for the census) — target = the commit landing this section

Check set (fixed before the diff was read): U1 every pin listed current vs latest, census + an independent listing; U2 each lock diff = the upgrade alone; U3 the census reads every lock entry, both sides; U4 S23 fires every recorded case; U5 major bumps vs our call sites; U6 each pin below latest held (a row or a ruling); U7 every runnable `Artifacts` entry driven; U8 the instrument repair is lock-independent; U9 correctness lens over the code hunks; U10 rules upkeep; U11 full gate (CI gate, run in the commit body). MAIN alone; advisor consulted on U6.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| U1 | completeness | pass | `.agent/pins` 28 rows (before rc 1: `uv.lock` multidict + 5 Open WebUI-lock transitives; after rc 0); rerun after the CI gate: rc 0 with one hold (U6); independent PyPI listing per entry: `uv.lock` 34/34 at latest after, `build-constraints.txt` 6/6, Open WebUI lock 182/266 (U6 holds the rest); action SHAs = `gh api repos/<r>/commits/<tag>`; uv 0.13.5 ships CPython 3.15.1 + 3.12.15 = python.org's newest; jail image digest unchanged by `podman pull`. |
| U2 | lock diffs | pass | `uv.lock`: name/version lines = multidict 7.1.0 → 7.2.1 alone; Open WebUI lock: 5 pins + their hashes, header `cmp`-equal to HEAD's (regenerated with `--custom-compile-command`: a plain rerun dropped the `echo open-webui==0.12.3 |` that `test_p128_the_lock_pins_the_target_and_hashes_every_package` reads); `.agent/owui-audit` PASS, 127 findings all on p137. |
| U3 | census reach | find → fixed | `compile_drift` matched `name==v \` alone: 30 marker-bearing pins unread on either side. Fix keys name + marker, rc 2 on an empty parse; seed `pywin32==1 ;` → pre-fix census silent, fixed census `pywin32 ; sys_platform == 'win32' 1 -> 312`. |
| U4 | seed group | find → fixed | S23 before 1/3 (`hold-gone` deleted an already-closed p126 row; `shipped` red on live drift) and short of its record's cases → 8 cases incl. the marker seed, 8/8 MATCH; anchors count-asserted (`substitute`). |
| U5 | majors | pass | none: multidict minor (cosmic-ray → aiohttp), the 5 lock moves minor/patch inside Open WebUI; Cement imports none of them. |
| U6 | held pins | pass (owner-ruled) | 84 lock entries below PyPI latest, each pinned or capped by a locked parent's requirement back to open-webui 0.12.3 (kubernetes by conflict: pydantic>=2.13.5 vs the target's 2.13.4) → owner: the target holds them; `pins.md` Law clause. open-webui 0.12.4 released during the CI gate (census: `open-webui target 0.12.3 0.12.4 BEHIND`) → owner: hold 0.12.3 while production runs it → born row p144 (the measured 0.12.4 lock + audit facts) + `HELD` entry; census rc 0, `held p144`. |
| U7 | runnable artifacts | pass | README quick start end to end (signed `eval`, `resolve` hit rc 0 / miss rc 6); hospital OCR `All checks passed.`; both generators byte-identical; Open WebUI regimen on the new lock (setup → serve gpt-6-luna → provision → covered turn, missed turn retained, shadow observation `agreed`, 0 tracebacks); stub smoke 6/6 = `m5u3-smoke.md`; nucllei jail stand-in PASS; prototype capture 10 distinct frames + density + quality floor rc 0; `.agent/mutate` 49 mutants on the bumped cosmic-ray stack. |
| U8 | instrument repair | pass | `m5u3-stub-model.py` parsed the whole user message; the inlet note (990ec8d, MAINTAIN W2) broke every turn before this change; `raw_decode` of the leading object restores the M5.3 table; no test reads either file. |
| U9 | correctness | pass | `entries()` read inside `compile_drift`: `(\S+)` stops at the marker's space, the lazy marker group ends at the line's tail; display keys carry the marker, so a fork prints twice; `substitute` mirrors `replace`'s count guard; `raw_decode(None)` = the caught `TypeError`. |
| U10 | rules upkeep | pass | `pins.md` (Law clause, one Hash-pinned locks definition replacing two partial recipes), `open-webui.md` (points there), `gate-checks.md` (`.agent/pins` record = the after run, landing-commit citation) re-read against `Authoring`. |
| U11 | full gate | see the commit body | CI gate on this tree: run id, legs + D28 line in the landing commit's body. |

## Phase close, version cut (IMPLEMENT p135 + p136) — target = the commit landing this section

Check set: the `Decisions` Pin repairs rule (each repaired test id named in the body + here), the new freeze pin, the shipped filter live.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| PR1 | pin repair | pass | `tests.test_schema_v3_battery.SchemaIdentityBattery.test_s1_the_package_version_is_the_cut` read the working tree's `pyproject.toml` = a frame freezing the CLOSED v3 cut → re-scoped to git object `93007ac:pyproject.toml` (M3.6b's squash), assertion unchanged (`0.2.0`); nothing deleted, skipped or weakened. |
| V1 | freeze pin | pass | `test_v1_v4_and_shadow_v1_are_frozen_by_the_0_3_0_release`: version half red at the fixes commit (0.2.0); digest halves fired by a one-character seed in each schema (`.scratch/close/freeze_seed.py`, control OK). Mutation credit (`.agent/mutate`) not run: seeds are closure, the version half carries the red-first credential. |
| L1 | live, shipped filter | pass | the regenerated paste-ins on the regimen instance (`.agent/decisions/owui-live-e2e.md` last line): one covered hit → observation 4 `agreed`, model `gpt-6-luna`, the shadow call without tools, zero warnings. |

## Phase close review, ffe130f..eb5cc4d (IMPLEMENT p135 + p136) — fixes = the commit landing this section

Check set fixed before any reading: one `reviewer` per lens over `src/` + the two Open WebUI example sources (+ skills + changed tests for correctness), each a seeded table graded both ways (`| unknown |` 56 / 54 / 9 at seed, 0 filled; `.agent/validate-anchors` rc 0); MAIN alone = the security lens S1-S10. Tables: `.scratch/close/reviewer-{1,2,3}/verdicts.md`, `.scratch/close/security.md`. Every finding below MAIN-reproduced at eb5cc4d before its ruling; each fixed one pinned by a test red there (commit body).

| id | lens | verdict | ruling + pin |
|---|---|---|---|
| C-F1 / A-F1 | correctness + altitude: `unordered` dropped an `ignore` at `*` (`_normal` handled ignored keys only) | fixed | `_normal` maps an ignored node to one constant (the rule covers every element on both sides); `test_m2_unordered_applies_an_ignore_at_its_elements`. |
| C-F2 | correctness: valid JSON outside cement-json-v1 (a decimal) left the observation `admitted` for good | fixed | `_answer` grades with `parse_json` at `ANSWER_MAX_BYTES` after `json.loads`; `test_s5_an_answer_outside_cement_json_is_a_failure` (also a repeated key, which `json.loads` collapsed into an agreement). |
| C-F3 | correctness: `finish_shadow` recovery matched only the observation id inside the provenance | fixed | whole-provenance digest against `_provenance(row, differences)` (S5); `test_s5_recovery_binds_the_whole_shadow_provenance`. |
| C-F4 / C-F5 | correctness: `comparator(operation_revision=2**63)` leaked `OverflowError`; a stored comparator the grammar refuses read as usage (exit 2) | fixed | bound 1..2⁶³−1; `ValidationError` on a stored row → `IntegrityError` (`comparator` + the captured reader); `test_m4_reads_bound_…`, `test_m5_show_exits_by_class_…`. |
| C-F6 | correctness: observation reads trusted a captured comparator hash (S6) | fixed | `_captured_comparator` re-checks JSON + hash in `_record` and `record_shadow`; `test_s6_a_read_rechecks_the_captured_comparator_hash`. |
| C-F7 | correctness: the filter recorded the valve's model read after the call | fixed | `_sample` reads the model once and passes it to `_ask`; `test_s5_the_record_names_the_model_that_was_asked`. |
| C-F8 | correctness: skill line "The case stops answering until step 4 publishes it again" | fixed | probe (`.scratch/close/f8_probe.py`): under `follow` the whole function answers nothing, a pinned version keeps its old answer; `skills/cement-learn/SKILL.md` says so. |
| C-F9 / A-F2 | correctness + altitude: `ShadowStore` forked the ledger opener without its guards | fixed | only a creating open initializes, only a pristine file (`application_id` 0, no schema); `journal_mode = DELETE` after identity; `test_s1_only_a_creating_open_initializes_a_pristine_file`, `test_s1_a_reopen_restores_the_rollback_journal`. |
| K-F1 | cleanup: shadow schema helpers duplicate `store.py` + rebuilt per open | fixed (partly) | `_schema_objects` reused, `_expected_objects` cached (`functools.cache`); `_statements` kept (the ledger's executor is bound to its own DDL + a pinned call). |
| K-F2 | cleanup: `OBSERVATION_ID_MAX_BYTES` from a copied 512 | fixed | `SOURCE_ID_MAX_BYTES - len(SOURCE_PREFIX)` (505 unchanged; the adjacent pair still pins it). |
| K-F3 | cleanup: sampling + retention each decode the reply's tool items | declined | the outlet keeps them in two failure-isolated blocks; one shared decode would couple them for one JSON parse. |
| S-F1 | security S6: one forged `/api/chat/completed` body queued one executor job per drop (2,000 forged hits held an unrelated `to_thread` call 4,825 ms) | fixed | one drain task records drops one at a time from a 1,024 backlog; a reply's hits past 256 counted, never canonicalized; example README states both; `test_s5_drops_are_written_one_at_a_time` (eb5cc4d: 12 in flight), `test_s5_a_reply_past_the_hit_cap_is_counted_not_recorded`. |
| S1-S5, S7-S10 | security | pass | `.scratch/close/security.md` rows. |
| R1 | register: p136-store S9 "without constructing a System" vs p51 | ruled | p51 precedes (`## p136-store` A9/C1); erratum appended to the contract. |
| R3 | register: README `Python 3.11+`, `cement function` "eleven leaves" | fixed | 3.12+ (`requires-python`); sixteen leaves, the table gains `quarantine-plan`, `quarantine`, `drift`, `observations`. |
| R4 | register: p136-cmp M4 names `ComparatorRecord` as `set_comparator`'s return | ruled | `ComparatorChange` is the shipped + documented return; erratum appended. |

## p135-docs close (IMPLEMENT, unit; tier `docs`) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p135-docs-contract.md` + p87 gate 3: G1-G4 = its obligations; P = p87's E3 + E5 doc bullets (landed by those units); C1 claims re-derived against code. MAIN alone (consistency pass).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| G1 | README encryption | pass | `## Deployment boundary`: Cement does not encrypt + holds no key; volume encryption + swap; the ledger + `-journal` (`-wal`/`-shm` after a switch), `<ledger>.shadow` + journal, each export temporary file, each bundle + backup; volume-key erasure; Open WebUI's data volume. |
| G2 | threat model | pass | Evidence bullet names the same files + "Cement does not encrypt"; `## Deliberately absent`: field-level encryption + the volume-key sentence, registry line added. |
| G3 | registry recipe | pass | README `### Storing bundles in a registry`: export → `ssh-keygen -Y sign` → `oras push`; `oras pull` → `function eval --signature --allowed-signers`; the allowed signers file + a pinned hash travel another channel. Placeholder-free blocks; the README command parsers (D23, X-placeholder census) green. |
| G4 | untouched claims | pass | `CLI actor names are recorded assertions, not authentication` kept (E1 → p140). |
| P | plan bullets | pass | E5: threat model lines 63-67 (unkeyed hash, then the signature check), `External signatures` gone; E3: line 79 `database-immutable outside a partition erasure`, the evidence bullet names `retention prune` + `partition erase`. |
| C1 | claims | pass | `journal_mode = DELETE` (`store.py` `_initialize`), `temp_store = MEMORY` on every store + shadow connection (`_connect`, read and write), export temporary `.<name>.<12 hex>` mode 0600 beside the destination (`cli.py` `_export_temporary`), `oras push <ref> <file> <file>` / `oras pull <ref>` (ORAS command reference). Register + article audits rc 0, tripwires PASS. |

## p136 gate 3 records (IMPLEMENT, store + owui gate 3; tier `kernel` for the `_ask` fix, `data` for records) — target = the commit landing this section

Check set, fixed from p136-store gate 3 + p136-owui gate 3 + the diff lenses: G1 cost measured, G2 live regimen, F1 the live finding's fix (one re-review against its acceptance: a red test + seeds), C1 claims. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| G1 | store gate 3 cost | pass | `.agent/decisions/p136-shadow-bench.json`: committed `220fb55`, clean `src`, load 2.8 on 8 CPUs, 5 repeats at 1 + 1,000 entries; the separate expected-hash cache key (`_serving_key` member `expected_function_hash`) makes a disagreement's commit cost two verifications (769 + 776 ms at 1,000) → README sentence + p141. |
| G2 | owui gate 3 live | pass | `.agent/decisions/owui-live-e2e.md` `## Shadow sampling`: covered hit → one observation `agreed`; the forwarder shows the shadow call without `tools`; `/api/chat/completed` replay → one duplicate, zero model calls; the learning model called `shadow_drift` + `show_comparator`. |
| F1 | `_ask` user | fixed | Reverses the `_ask` half of p136-owui C1: 0.12.3's `Users.get_user_by_id` is a coroutine function, so the user passed was a coroutine (live `RuntimeWarning`). Fix = `await`; `test_s5_the_real_shadow_call_awaits_the_account_and_sends_no_tools` red at `220fb55` (`ValueError: not enough values to unpack`, lookup never awaited); seeds `.scratch/p136/ask_seeds.py` (control OK): lookup not awaited, filters not bypassed, tools sent, request dropped → each reds it. Re-provisioned live hit → `agreed`, zero warnings. |
| C1 | claims | pass | Contract W3's "live-verified that no tool or filter reaches the shadow call" is now backed by G2; README cites medians + the record path; register + article audits rc 0, tripwires PASS. |

## p136-owui close (IMPLEMENT, unit; tier `kernel` for selection, identity + isolation) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p136-owui-contract.md` + the diff lenses: A1-A7 = O1-O7; S = seeds; C1 correctness. MAIN alone (the store's consultants already ruled the semantics it calls).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | O1 hits | pass | Only covered `use_learned_function` calls of the current message with a listed, not excluded operation and a hash; identity `ward-7:chat-1:msg-1:call-1` pinned. |
| A2 | O2 isolation | pass | The returned body is the same object and serializes byte-identically with sampling off and on; a blocked shadow call → the reply returns first; a full queue (1) → two `dropped` rows, no wait. |
| A3 | O3 worker | pass | N = 5 hits → 5 calls + 5 rows; mixed (2 disagree), all-agree (0), all-disagree (5) → `drift` exact on the one hash; a repeated completed run → one row + one duplicate; ConnectionError, non-JSON, timeout (1 s valve) → `failed` with their notes, no proposal or event; the version that served the hit decides after a newer promotion. |
| A4 | O4 prompt | pass | Two messages (system + user), the function's answer marker absent, `prompt_revision` = `sha256:` + 16 hex. |
| A5 | O5 valves | pass | `shadow_model` empty = off (no call, no file), `shadow_exclude`, `shadow_queue`, `shadow_timeout`, `shadow_path`. |
| A6 | O6 learning tool | pass | `set_comparator`, `show_comparator`, `shadow_drift`, `shadow_observations` (admin-checked `_run`); W3 surface pin + the skill names each; the no-switch AST pin holds. |
| A7 | O7 paste-ins + README | pass | Regenerated (freshness green); example README `## Shadow answers`; register + article audits rc 0; tripwires PASS. |
| S | seeds | pass | `.scratch/p136/owui_seeds.py`, control OK, source restored: outlet awaits the worker, exclusion ignored, call id dropped from the identity, prompt carries the answer, off switch ignored, timeout not failed → each reds its owner. |
| C1 | correctness | pass | The worker task is held on the instance (the loop keeps a weak reference); `_ask` imports Open WebUI by full module name (the generator's `replace_imports` rule); every worker failure is counted + logged, never raised into a chat. Gate 3's live run is owed (records commit). |

## p136-learn close (IMPLEMENT, unit; tiers `data` + `docs`) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p136-learn-contract.md` + the diff lenses: A1-A3 = E1-E3; C1 correctness; C2 claims. MAIN alone (shallow).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | E1 projection | pass | `test_learn_a_case_names_its_shadow_proposals`: a shadow and an ordinary pending proposal on one case → `pending_proposal_ids` holds both, `shadow_proposal_ids` the shadow one alone; red at a1686ad (`KeyError: 'shadow_proposal_ids'`), the other 23 tests green there. |
| A2 | E2 skill | pass | Step 3 names keep / adopt / reject with each one's effect (a correction adds a confirmation; an adoption stops the case answering until publication); `## Comparator` with the four rules, the never-loosen rule, the checks Cement runs and their limit; step 5 reports `function drift`. The skill + learning batteries green (54). The skill's compatibility floor 3.11 → 3.12 (`requires-python`). |
| A3 | E3 README | pass | `### The learning pass` names the field and the decisions; register + article audits rc 0; tripwires PASS. |
| C1 | correctness | pass | The flag comes from `source_id` in the same query, so it costs no extra read and cannot disagree with `pending_proposal_ids` (same rows). |
| C2 | claims | pass | The skill says Cement cannot tell whether a rule is right (matches `set_comparator`'s applicability-only checks). |

## p136-store close (IMPLEMENT, unit; tier `kernel` + `data` payloads) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p136-store-contract.md` revision 2 + the `CLAUDE.md` diff lenses before the diff was reread: A1-A10 = S1-S10; N = consultant-2's eight rows, each re-derived; P = repaired pins; C1-C3 lenses. consultant-2 (`consultant`) attacked revision 1 before code; its N3 + consultant-1's L4 reshaped the design (capture at admission, a durable `prepared` row, recovery by an exact source lookup).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | S1 store | pass | `tests.test_shadow.StoreIdentityTests`: a ledger file, a foreign DB, an extra table, a wrong version → `IntegrityError` with byte-identical files; mode 0600 under umask 022; `create=False` on a missing file → `NotFoundError`, nothing created; illegal transitions, capture edits and a CHECK-violating shape refused by SQLite. |
| A2 | S2 admission | pass | The captured version decides in both directions (v1 vs v2 for one input), the served version answers without a rebuild and an older one rebuilds (spy 0 / 1); switch off still captures; foreign scope, an absent hash, a miss and a corrupt membership refuse with both files byte-identical; a repeated id returns the original id, counts, keeps the original input; four threads racing one id → one row + three duplicates; 505 / 506-byte id, empty, control character. |
| A3 | S3 outcomes | pass | drop (new identity, repeat counted), cancel, fail → their states + notes; a second transition → `ConflictError`; ledger table counts unchanged. |
| A4 | S4 record | pass | An agreement leaves the ledger file byte-identical and the serving cache warm (0 verifications on the next resolve); a disagreement → exactly proposals + 1 and events + 1, pending, exact bounded provenance, joins `learning_cases`, serving unchanged; >5 paths keep the first five + the count; 1 MiB / + 1 output, 256 / 257-byte model. |
| A5 | S5 finish | pass | A failure planted after the ledger commit leaves `prepared`; the proposal is then rejected (reviewed before the retry); `finish_shadow` records that same proposal and no second one; a mismatching proposal under the source id → `ConflictError`, still `prepared`; a revision change → no proposal + the exact note; the comparator captured at admission decides after two later settings. |
| A6 | S6 reads | pass | Drift across two hashes ordered by first sequence, `disagreements`, the inclusive `since_us` edge (200 keeps, 201 drops), an empty window with a lifetime duplicate; paging, the state filter, the pending cursor, limit bounds. |
| A7 | S7 retention | pass | Prune as an adjacent pair (clock patched), a neighbour partition untouched; CLI erase runs the shadow file then the ledger, a rerun exits 3; an absent default store is skipped and never created; a named missing store exits 3. |
| A8 | S8 never act | pass | Ledger deltas: agree 0, drop / cancel / fail 0, disagree = one proposal + one event; no path calls `challenge`, `set_switch`, `set_projection`, `set_comparator` (source read). |
| A9 | S9 CLI | pass | `function drift` / `function observations` read the shadow file (ledger bytes unchanged), a missing store exits 3 uncreated, a ledger passed as `--shadow` exits 5; p51 holds (the ledger opens existing-only first). |
| A10 | S10 docs | pass | README `### Shadow answers` + library row + erase wording; architecture `### Shadow observations`; threat model: the shadow answer as untrusted evidence, `Active shadow sampling` removed from `## Deliberately absent` (the Open WebUI half lands with p136-owui), monitor + minimize obligations. No cost claim yet: gate 3's measurement lands in the records commit that follows. Register + article audits rc 0; tripwires PASS (the retired token `request` avoided). |
| N1 | store shape | accept | State CHECKs, immutable capture, live-schema comparison, existing-only open. |
| N2 | identity | accept | Caller-derived source id with the 505-byte bound; cancellation is its own transition; one consumer per store (documented; the nucllei job holds a lock). |
| N3 | recovery | accept | Durable `prepared`, exact all-status lookup + binding check, revision checked before submission (the ledger's own check stays a backstop), bounded provenance. |
| N4 | learning effects | accept (sound) | Pinned: pending, joins `learning_cases`, serving unchanged. |
| N5 | reads | accept | Filtered drift, lifetime duplicates apart, SQL `LIMIT`, a cursor for pending. |
| N6 | retention + never act | accept | `proposal.created` named as the second ledger write; two-file erase reports per store, a rerun completes; quiescence documented. |
| N7 | collateral | accept | typed records (runtime `System` import; `ShadowErasure`), B20 read sites, SHAPE, p51, both embeddings. |
| N8 | seeds | accept | Fired (`.scratch/p136/store_seeds.py`, control OK first, source restored): conflict taken as success, pending-only lookup, captured comparator ignored, duplicate counter frozen, exclusive cutoff, revision check off, agreement written as prepared, provenance paths uncapped, cancel from any state → each reds its owner. Survivor: "served hash not checked" = equivalent (`serving`'s expected-hash check already fails a different version) → the redundant clause deleted, its reason in a comment. |
| P | repaired pins | pass | Live re-pins: B20 + `shadow_capture` / `proposal_by_source`; `ParserShapeTests` SHAPE (287, 1a14d23d9e0d17ec) → (301, c8c163d165b7e6ce); the E3 battery's erase key set + `shadow`. |
| C1 | correctness | pass, fixes | The ledger passed as a shadow store reported "schema 4 is unsupported" → names the foreign file; the shadow leaves skipped the ledger open and broke p51 → they open it existing-only first. |
| C2 | cleanup | pass | One insert path (`_insert`) for admit + drop; one transition helper for cancel + fail. |
| C3 | altitude | pass | Two small `System` reads carry the ledger knowledge; the store never writes the ledger except through `submit_proposal`. |

## p136-cmp close (IMPLEMENT, unit; tier `kernel`) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p136-cmp-contract.md` revision 2 + the `CLAUDE.md` diff lenses before the diff was reread: A1-A6 = M1-M6; L = consultant-1's six rows, each re-derived; P = repaired pins; C1-C3 lenses. consultant-1 (`consultant`, reused from E3) attacked revision 1 before code; consultant-2's store review (N3) independently found the comparator-time flip.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | M1 grammar | pass | `tests.test_comparator.GrammarTests`: a valid comparator round-trips and hashes order-free; 14 refusals each name their rule index (repeated path, root ignore, under ignore / text / tolerance, an unordered child not through `*`, tolerance under unordered, kind, keys, abi, segment); 256 / 257 rules, 32 / 33 segments, 256 / 257 characters, `within` forms, and the 65,536 / 65,537-byte document as exact adjacent pairs. |
| A2 | M2 compare | pass | `CompareTests`: each rule's adjacent pair; tolerance over integers + decimal strings by scaled integers (32-digit edge, 65-character operand exact); the text rule folds A-Z + the fixed whitespace set and leaves `ß`, `É`, U+A7CB, combining marks and EM SPACE exact (identical on 3.12 and 3.15 by construction); multiplicity; nested rules below `unordered`; a literal `*` key stays exact; paths sorted, capped at 20 + 256 characters; `None` walks like an empty list. |
| A3 | M3 storage | pass | `comparator_settings` + scope index + two triggers (delete opens only under an erase grant); `partition erase` counts it (retention battery fixture now holds a row, so its every-table control covers it). |
| A4 | M4 set + read | pass | Equal hash → no write before revalidation; typed witnesses (text vs list, tolerance vs string refused); a wholly ignored answer refused; revision scoping; stored JSON re-hashed on read; one `comparator.set` event with the previous hash. |
| A5 | M5 CLI + Read | pass | `comparator set/show`, exit 2 / 3; `function read` header names revision + hash + setting sequence and says a later setting replaces it; the no-match tail stays last (pinned test unchanged). |
| A6 | M6 docs | pass | README `### Comparing answers` (exact text table, the `*` limitation, set-time applicability, a tolerance that covers every dose as the named limit, mutable policy); architecture `### Comparators`; threat model: comparators are the learning pass's judgment. Register + article audits rc 0. |
| L1 | grammar | accept | Budget 64 KiB (projection's), typed `*` edge, descent through `*`, original indices; the `within` spelling (`1.0` vs `1.00`) keeps distinct hashes by design. |
| L2 | determinism | accept, remedy chosen | Measured interpreter split → explicit tables. MAIN chose A-Z + a fixed whitespace set (the projection precedent) over a packaged Unicode-15 fold table: deterministic, no generated data module; the narrowing is in the docs. |
| L3 | the floor | accept as documentation | No owner-ratified semantic criterion exists; M4 = applicability + non-erasure, stated as such; typed witnesses + empty-container leaves close the `[{}]` loophole. |
| L4 | capture | accept | Revision-scoped mutable policy; p136-store captures comparator JSON + hash + sequence at admission (contract amended there). |
| L5 | collateral | accept | Table count 17 → 18 (4 pins), `runtime.md`, the retention census + fixture, B20 write + read sites + helper, identity + event censuses, typed-record fixture, SHAPE. |
| L6 | gates | accept | Seeds fired (`.scratch/p136/cmp_seeds.py` + `cmp_seeds2.py`, control OK first, source restored byte-for-byte): A-Z fold dropped, host `casefold`, multiset as a set (both sides), `<=` → `<`, ignored-key presence counted, `*` conflated with a literal key, descent check off, witness type ignored, path cap off, whole-answer check off, unwitnessed check off, idempotence off, tolerance under unordered → each reds its owner. |
| P | repaired pins | pass | Live re-pins for the deliberate change: `test_submission` + D22 + V25 + X25 table counts 17 → 18; B20 + `set_comparator` / `comparator` / `_comparator_row`; identity census + writer; `EVENT_PAYLOAD_KEYS` + `comparator.set`; typed-record caller fixture + 9 fields; `ParserShapeTests` SHAPE (272, 3003b326d5555606) → (287, 1a14d23d9e0d17ec). |
| C1 | correctness | pass, fixes | Revision 1's text rule read the host's Unicode tables (L2); the walk conflated a literal `*` key with the array edge (L1); a huge key overflowed provenance downstream (consultant-2 N3) → all fixed + pinned. |
| C2 | cleanup | pass | `_document` is the one canonical builder for parse + `document()`. |
| C3 | altitude | pass | Grammar + compare in a pure module; storage follows `projection_settings`. |

## p135-e3 close (IMPLEMENT, unit; tier `kernel`) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p135-e3-contract.md` revision 2 + the `CLAUDE.md` diff lenses before the diff was reread: A1-A7 = V1, V2, V2a, V3, V4, V5, V6; K = consultant-1's eight rows, each re-derived; P = every repaired pin; C1-C3 lenses; S1 security. consultant-1 (`consultant`) attacked revision 1 before code (`.scratch/p135/consultant-1/verdicts.md`, probes at `3333d7c`).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | V1 schema v4 | pass | `tests.test_retention_battery.SchemaV4Tests`: version 4, fingerprint = sha256(SCHEMA), `schema-v4`, every table classified (direct 8 + child 5 + shared 1 + meta 4 = `sqlite_master`); 10 guards carry the grant clause, `schema_metadata_no_delete` + `erasures_no_delete` carry none, the program guard carries its three reference clauses; a real v3 ledger (package from `331a3b4`) refuses on both opens and through the CLI (exit 5), bytes unchanged. |
| A2 | V2 prune | pass | `PruneTests`: cutoff = t0 + 1 keeps the t0 + 1 proposal and deletes the t0 ones (adjacent pair), accepted + corrected kept, `tenantXa` / `Tenant_a` untouched, event payload exact; 108 deleted → count 108, first 100 sorted, hash of the full set; nothing to prune → identical bytes; a pruned pending proposal leaves `learning_cases` and frees its source id (the next repeat conflicts again); argument + actor bounds as adjacent pairs. |
| A3 | V2a `secure_delete` | pass, scope changed | MAIN measured the stale-copy defect before consultant-1 reported it (K6): switched on at erase time alone, 16 copies of the erased marker survived (earlier page moves + updates); on for every write connection, 0 (`.scratch/p135/probe_erase_bytes.py`). Shipped: `Store._connect` write branch; `test_v2a_the_control_without_secure_delete_keeps_the_bytes` forces OFF and keeps the marker, so the absence test cannot pass on a build default. The claim excludes backups, the journal's disk blocks and an operator-switched WAL file (README, threat model, architecture). |
| A4 | V3 erase | pass | `EraseTests`: every rowid of the partition (snapshotted before, per table) absent after, `foreign_key_check` empty, neighbours' rows identical, counts = per-table lengths + 1 program, tombstone exact, grants empty; the shared program stays, the unshared one goes, an unrelated orphan stays; an events-only partition erases; a warm serve then the erase → `NotFoundError`, the neighbour still answers; an empty partition and a planted foreign-key break write nothing; a failure injected at the tombstone leaves identical bytes and a valid reopen. |
| A5 | V4 guards | pass | `GuardTests`: each of the 10 guards refuses with no grant, with a grant for `tenantXa` and for `Tenant_a`, and opens for its own partition (control); `schema_metadata` + `projection_programs` refuse under a grant; each program-reference family alone blocks the program delete, none left → it opens (control); the tombstone refuses update + delete under a grant. |
| A6 | V5 CLI | pass | `RetentionCLITests` + the real CLI (`.scratch/p135/e3`): prune 0 / 1 day, max days accepted, −1 and max + 1 exit 2; `--confirm` mismatch exit 2 with identical bytes; a missing `--db` exits 5 and stays missing (p51); erase JSON keys; a second erase exit 3. |
| A7 | V6 docs | pass | README `### Retention and erasure` + the library row + the receipt bullet's qualifier; architecture: the two immutability claims qualified, the v4 paragraph; threat model: the immutability bullet qualified, a new enforced-controls bullet with the byte boundary, the minimize obligation names both commands + backup retention. Register + article audits rc 0, tripwires PASS. |
| K1 | consultant premises | accept | R4 wording amended (review events keep ids, never bodies). |
| K2 | trigger order | accept | Children go while their parent exists (contract V3 order; `_ERASE_STEPS`). |
| K3 | program guard | accept | Orphan-kept case added. |
| K4 | erase order | accept | The shipped order is one of the valid topological orders; examples go in one statement. |
| K5 | prune | accept in part | Actor wording = `_text` (≤ 256 UTF-8 bytes). Rejected: unbounded age; the shipped bound (`_MAX_AGE_SECONDS`, the largest age whose cutoff fits int64) is explicit, pinned as a pair, and refuses rather than silently matching nothing. |
| K6 | byte claim | accept, remedy differs | The defect is real; the remedy is always-on `secure_delete` (A3) rather than a narrowed claim; the WAL + journal boundary is stated. |
| K7 | collateral | accept | `runtime.md` 15 → 17 STRICT tables; embeddings regenerated; read setup's pragma pin untouched (write branch alone). |
| K8 | acceptance + seeds | accept | Every listed case is in the battery; the named seeds were fired: `<`→`<=`, `=`→`LIKE`, `secure_delete` OFF, grant cleanup removed, one child delete omitted, the artifacts reference clause removed, the event kind renamed → each reds its owner (`.scratch/p135/e3_seeds.py`, source restored byte-for-byte). |
| P | repaired pins (standing approval) | pass | Re-scoped to `331a3b4` (the last v3 revision): `test_schema_v3_battery.SchemaIdentityBattery.test_s1_version_three_and_the_fingerprint_bind_the_schema_text`, `test_proposal_binding_battery.ProposalBindingBatteryTests.test_b32_the_schema_freeze_schema_version_2`, `test_read_capability_battery.ReadCapabilityBatteryTests.test_b22_schema_version_is_two`, `test_cli_channels.CliChannelTests.test_x24_store_py_remains_byte_identical_to_the_unit_baseline_and_s`, `test_system.SystemTests.test_function_promotion_schema_v2_is_reference_only_and_immutable`, `test_system.PreservedInvariantCensusTests.test_the_live_schema_is_frozen_at_v3`, `test_cli_channels_battery.ObligationBatteryTests.test_d26_preserved_and_asserted_independently_store_py_byte_identic`, `test_submission_battery.SubmissionBatteryTests.test_b01_schema_version_is_2_and_schema`; message derived from `SCHEMA_VERSION`: `test_s1_a_real_v2_ledger_refuses_to_open_naming_the_reset`, `test_function_promotion_schema_one_fails_closed_with_version_diagnostic`, `test_l07_fabricated_legacy_generating_row_survives_revision`. Live re-pins for the deliberate change: `test_submission` 15 → 17 tables, D22 15 → 17, B35 +1 setup record, B20 + two write sites, the identity + event censuses, `ParserShapeTests` SHAPE 254 → 272. None deleted, skipped or weakened. |
| C1 | correctness | pass, one fix | The CLI checked `--confirm` + `--older-than` before the ledger opened, which broke p51 (every leaf but `register` exits 5 on an absent ledger) → both now run after the existing-only open, before any write. |
| C2 | cleanup | pass | `_PARTITION_PRESENT` is one static query (ruff S608 refused the joined form); no duplicated helper. |
| C3 | altitude | pass | Grants live in the schema's own triggers, not in a code path that drops and recreates them; prune + erase share the write-connection pragma rather than special-casing it. |
| S1 | security | pass | Inputs: partition (`_name`), actor (`_text`), age (int + bound), `--confirm`; SQL is static with bound parameters; the grant row exists only inside the erase transaction (empty after success, rollback and a planted failure); a raw-SQL party that can write the file could always delete rows, so the grant adds no new power; the tombstone's digest is unkeyed and documented as not secret. |
| G | gates | see the commit body | gate 1 = the battery (red at `cd0d2cf`) + the seeds; gate 2 = the CI gate; gate 3 = audits + the pin list above. |

## p135-e5 close (IMPLEMENT, unit; tier `kernel`) — target = the commit landing this section

Check set, fixed from `.agent/decisions/p135-e5-contract.md` revision 2 + the `CLAUDE.md` diff lenses before the diff was reread: A1-A8 = obligations G1-G8; C1 correctness (each hunk with its enclosing function, callers + callees), C2 cleanup, C3 altitude; S1 security (each untrusted input to every sink). MAIN alone: the unit is signature verification, so security vocabulary keeps teammates off it (user `CLAUDE.md` `Subagents`); the advisor read the contract (revision 1 → 2).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | G1 Ed25519 | pass | `tests.test_signature.Ed25519Tests`: RFC 8032 TEST 1/2/3/1024/SHA(abc) verify, one flipped bit in R, S, key or message refuses; Wycheproof (sha256 pinned) tallies exactly 117 valid accepted / 64 invalid rejected / 29 acceptable rejected; y ≥ p, x = 0 with the sign bit, S = L, wrong lengths and 200 noise inputs → `False`, never a raise. |
| A2 | G2 SSHSIG reader | pass | `EnvelopeTests`: both `ssh-keygen` hash algorithms verify; one flipped byte at the end of each field (key, namespace, reserved, hash algorithm, signature) refuses with its own class + message; armor cases (no header, no footer, text after the footer, a non-base64 character, a form feed inside a line, bad magic, version 2, trailing bytes, truncation, empty namespace, a differing signature type, a 63-byte value) refuse; trailing blank lines + CRLF accepted. |
| A3 | G3 allowed signers | pass | `AllowedSignersTests`: 18 malformed or unsupported third lines each refuse with `allowed signers line 3: `; ECDSA, FIDO and certificate key lines, an options-then-other-type line, indented comments + blank lines are skipped; keywords case-insensitive; lines union their principals. |
| A4 | G4 public verifier | pass | Type checks first (4 cases); namespace → signer listing → signer → Ed25519 in that order (`verify_signature`); the fingerprint equals `ssh-keygen -l` (fixtures `alice.pub`, `bob.pub`, and the live smoke key). |
| A5 | G5 CLI | pass | `EvalSignatureTests`: a verified eval adds exactly `signers` + `signing_key`; no flags → the four keys; a tampered bundle exits 5 with stdout empty and `parse_function` never called (spy + control); pairing → exit 2; six refusals keep stdout empty with their class; both bounds pass as adjacent pairs (65,536 / 65,537 and 1,048,576 / 1,048,577); a wrong expected hash after a good signature exits 5. The real CLI drove export → `ssh-keygen -Y sign` → eval: hit 0, miss 6, wrong signer 5, one appended byte 5. |
| A6 | G6 process-free | pass | `EvalProcessFreeTests`: the child's audit hook records exactly the bundle, the signature and the allowed-signers file inside the directory, and no `sqlite3.connect` or process event; control = the same hook records `subprocess.Popen`. |
| A7 | G7 docs | pass | README eval recipe + library paragraph + `Deployment boundary`; `docs/architecture.md` two paragraphs; threat model `## Trusted` (allowed signers file), `## Untrusted` (signature files), `## Enforced controls` (a signature proves origin), `## Deployment obligations` (sign each exported bundle; D6), `External signatures` removed from `## Deliberately absent`. Register + article audits rc 0 (glossary + `allowed`, `publisher`, `signing`). |
| A8 | G8 instruments | pass | `tests/ed25519_signer.py` reproduces every RFC 8032 signature + public key byte for byte; `.agent/decisions/p135-e5-fixtures.sh` commits public keys, the message, signatures and the allowed-signers file alone (each signature verified by `ssh-keygen -Y verify` before it is kept); gate 3's `.agent/decisions/p135-e5-differential.py`: 144 rows, 0 disagreements; seeded with an always-accepting verifier → 48 disagreements, rc 1. |
| C1 | correctness | pass, one fix | Help, README and threat model said the signature is checked before the bundle is READ; the bytes are read first (they are what is signed) → reworded to "before the bundle parses". `_read_regular` keeps the old bundle messages byte-identical (label = `function bundle`; `tests.test_cli` pins pass). `checked` renamed from `verification`, which `_run` binds later to a `FunctionVerification`. |
| C2 | cleanup | pass | The bundle reader became `_read_regular` + `_utf8`, shared by the three files; no new helper duplicates an existing one. |
| C3 | altitude | pass | The verifier lives in `cement_runtime.signature`, outside `__all__` (frozen pins), beside `cement_runtime.learning`; the CLI adds no special case beyond the flag pairing. |
| S1 | security | pass, one fix | Inputs: bundle bytes (≤ 64 MiB), signature text (≤ 64 KiB), allowed-signers text (≤ 1 MiB), `--signer`. Sinks: `binascii.a2b_base64(strict_mode=True)`; `_Wire` bounds every length against the buffer; `hashlib.new` takes only a name in `{sha256, sha512}`; error text echoes ≤ 64 replaced-ASCII characters into JSON (escaped by `json.dumps`); no file is opened by name from inside an envelope. Verification touches public data alone, so timing leaks nothing secret. Fix: `_split` concatenated characters (a quadratic risk at 1 MiB) → index slicing; worst cases at the 1 MiB bound measured 0.14-0.63 s. Policy: patterns, certificate authorities, validity windows and FIDO keys are refused rather than ignored, so no restriction is silently widened. |
| G | gates | see the commit body | gate 1 = the new tests (red at `331a3b4`); gate 2 = the CI gate; gate 3 = `p32-differential.py` + the two-way differential. |

## MAINTAIN queue run 3 close — target = the commit landing this section

Check set (the body's `Met when`), fixed before the run's record was reread: R1 every queue row closed by its acceptance in its own commit, blocked on the owner with what it owes, waiting on its trigger, or routed; R2 the queue + ledger grader; R3 the standing censuses + audits; R4 the full gate on a clean tree at the closing commit. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 37 rows open at the run's base `dbe9db0`; closed this run, each in its own commit with its `Closed:` line (43): p32 p33 p34 p35 p36 p37 p87 p88 p89 p90 p93 p99-p102 p104-p116 p122-p134 p138 p139 (born + closed: p130-p134, p138, p139); waiting on a trigger: p52 (a map row about to become a durable claim), p137 (an Open WebUI release that moves its exact pins); routed to IMPLEMENT (owner, the route commit after this one): p135, p136; owed by the owner: none. |
| R2 | acceptance | pass | `uv run python .agent/decisions/m3-deferred-validate.py` → `VERDICT: PASS`. |
| R3 | integrity | pass | `p03-stored-int-census.py` (UNGUARDED 0), `p10-scratch-census.py` (unmarked 0), `p76-anchor-census.py` (failures 0), `p94-sha-census.py` (unreachable 0), `p73-review-coverage.py` rc 0; tripwires `RESULT: PASS`; `m3-report-validate.py --all` 5 graded, 0 failed; `.agent/pins` rc 0 (28 pins); `.agent/owui-audit` rc 1 → two pillow 12.3.0 advisories published after p131 (CVE-2026-112398, CVE-2026-114501; pillow is one of the 15 packages `open-webui==0.12.3` pins exactly) held on p137 under the owner's track-only ruling → rc 0, 127 findings. |
| R4 | acceptance | see the final message | the closing gate runs on the closing commit (a commit cannot carry its own gate result). |

p138 pass (tier `kernel`: a ledger event's shape; owner-approved re-pin) — target = `24e1e07` (`runtime+tests+queue (MAINTAIN p138)`); check set = the row's acceptance A1-A4 + correctness lenses C1-C3, fixed before the diff was reread:

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | the payload projects the list | pass | `retired_artifact_count` + `retired_artifact_ids` (first 100 sorted) + `retired_artifact_ids_hash` via `_id_list_projection`, the names `function.promoted` uses (the row wrote `retired_count`). |
| A2 | 10,000 stale artifacts | pass | `test_p138_set_projection_retires_ten_thousand_stale_artifacts` red at the parent (`canonical JSON exceeds 262144 bytes`), green at the commit. |
| A3 | census + docs follow | pass | `EVENT_PAYLOAD_KEYS["projection.set"]` (static + runtime halves); no shipped doc names payload keys. |
| A4 | other list payloads checked | pass | `replaced_artifact_ids` ≤ 1 (`one_promoted_exact_scope`); `contradicted_artifact_ids` ≤ 1 exact + one per distinct promoted projected key; `failures`: one structural-probe message per example → one counted message (pinned, red at the parent), the rest fixed-size. |
| C1 | each hunk with its enclosing function | pass | `stale` became `list[str]`: `executemany`, `_id_list_projection` (sorts a copy) and the return read it, none mutates it; `structure_failures` counts inside the evidence loop, its message precedes the replay message as the per-example ones did. |
| C2 | callers + consumers | pass | no reader of `projection.set`'s payload outside the census (`rg retired_artifact_ids`: `function.promoted` + receipt fields alone); `ProjectionChange.retired` still lists every id; the embedded copies regenerated. |
| C3 | classic pitfalls | pass | the event write stays inside the write transaction, so a refusal still rolls everything back; L18 still fails the defective interpreter (`passed` False). |

## p133 close (MAINTAIN queue run 3, owner-approved gate change; tier `data`) — target = the commit landing this section

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | the smoke runs inside the gate | pass | step `wheels` after `build` in the full + `--omit-d28` branches; the smoke's default = the working tree's tracked + untracked-unignored files (a tree-ish argument keeps the committed form), so a local gate tests what it sees. |
| A2 | firing recorded | pass | hash seed e6083cb → CI run 40040610060: both legs `wheels 2` (`Hash mismatch`), every other step 0; prefix seed 98384a8 → run 40040543110: `wheels 1` + `unittest 1`; both seed branches deleted. Recorded in `gate-checks.md` (the `.agent/gate` bullet). |
| A3 | records | pass | `ops.md` Gate list, `spec.md` Artifacts, README `## Development` (the install check named). |

## p134 close (MAINTAIN queue run 3, tier `kernel`: a public write's contract; owner-approved re-pins) — target = the commit landing this section

Check set = the row's acceptance clauses A1-A4 + lenses C1-C3, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | `submit_proposal(…, expected_revision=)` refuses another revision with zero writes (adjacent pair) | pass | `_bounded_int(1, 2**63 - 1)` before any I/O, then `_persist_proposal(expected_revision=…)` compares under the write lock (`StateError`, the propose path's message); `tests/test_expected_revision.py`: equal → written, after a revise → refused with 1 proposal still, the new revision → written; 0, -1, `True`, 1.0, "1", 2**63 → `ValidationError` + 2**63 - 1 passes validation. |
| A2 | CLI envelope `operation_revision` routed | pass | `_SUBMISSION_KEYS` gains it, `_REVISION_WIRE_BYTES` (19) enters the derived cap, `max_items` = fields + one per key; equal → exit 0, revised → exit 4 `conflict`, `true` → exit 2; help names it. |
| A3 | the relay passes it; the README window sentence goes | pass | `Outbox.relay` → `expected_revision=intent["operation_revision"]`, a `StateError` with the refusal text → `stale` (any other `StateError` re-raised); the pre-check and its window paragraph removed. |
| A4 | tests red at the parent | pass | the commit body's red-first run. |
| C1 | re-pins keep their strength (owner-approved) | pass | D16 (five-key framing 69, cap formula + AST names, exact-cap success with the revision padded to its 19-byte width, cap + 1 refused), D17 + X13 (+5 members, at-bound + over-bound pairs), D19 (kwargs set + `expected_revision` None), D32 (StateError named beside `expected_revision`, the revision prose re-targeted), P01 + the ABI pin (signature + hints), V20 (maximal frame with a 19-digit revision), X11 (framing, keys, cap), X15 (the spy forwards the keyword), the grammar SHAPE digest (help text). |
| C2 | behavior elsewhere | pass | `p32-differential.py --base 811f583` → SAME 2712; paste-ins + `ext/bin/cement` regenerated. |
| C3 | prose | pass | README (five keys, the table row, the source-id paragraph), `docs/architecture.md`, the outbox README; register + article audits rc 0. |

## p126 close (MAINTAIN queue run 3, owner-approved re-scope; tier `data`) — target = the commit landing this section

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | re-scoped acceptance: each mirror graded against its target | pass | `.agent/pins`: `open-webui mirror python` = `PYTHON` vs the Kimi target line (the jail stand-in; `Decisions`: the Open WebUI target runs Cement's supported Python, not the stock image's 3.11), `nucllei jail stand-in python` = the stand-in vs `FROM python:3.N` in nucllei's `sandbox/Dockerfile` at `v20261020-01` (`dockerfile_python`, `gh api`); both 3.12 = 3.12, `HELD` empty, 28 pins rc 0. |
| A2 | the rows fire | pass | `PYTHON = "3.13"` → rc 1 `3.13 3.12 BEHIND`; the stand-in image at `python:3.13-slim` → rc 1 on the split leg, the floor and the jail row; files restored (`cmp`). |
| A3 | records | pass | `pins.md` (mirrors graded against their targets), `gate-checks.md` `.agent/pins` bullet (new seeds; the HOLD-GONE seed left with the hold). |

## p132 close (MAINTAIN queue run 3, owner ruling: "Choose the more correct one, even if it takes more work now") — target = the commit landing this section

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| O1 | the more correct form | pass | PEP 695 `type` statements (the typing docs deprecate `TypeAlias` since 3.12; every supported target runs 3.12+, `Decisions`): `json_value.py` `JSONScalar` + `JSONValue`, the hospital example's own aliases; `UP040` no longer ignored, so ruff enforces the form. |
| O2 | public surface | pass | no runtime `isinstance` use in `src/` or `examples/`; README `## Library API` states that the aliases serve annotations and `isinstance` refuses them; `test_the_json_aliases_are_type_statements` pins the shape (red at HEAD: `bool | int | str | None is not an instance of TypeAliasType`). |
| O3 | regressions | pass | mypy + ruff clean; paste-ins + `ext/bin/cement` regenerated; fast gate over every module but D28 + `test_source` → 1425 tests OK; the p89 census drops its `JSONValue`-union exemption (a `type` alias stays whole in hints). |

## p132 agent part (MAINTAIN queue run 3, tier `kernel`: connection setup; the row stays open for the owner's `JSONValue` ruling) — target = the commit landing this section

Check set = the row's acceptance clauses A1-A4, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | each accommodation removed or its reason restated | pass (one owed) | `store.py`: `setconfig(SQLITE_DBCONFIG_DEFENSIVE, True)` unconditional (both `setconfig` + the constant exist on 3.12-3.15, measured), the `trusted_schema` PRAGMA kept as p44's one setter with that reason; `.agent/gate`'s `--durations` probe removed (+ `.agent/seeds` S01's old-Python cases, `ops.md`, `gate-checks.md`); the battery's `SETCONFIG_PYTHON` branch removed; `cli.py` + `projection.py` comments restated (UCD 15.0.0 / 15.1.0 / 16.0.0 / 17.0.0 on 3.12 / 3.13 / 3.14 / 3.15, measured). Owed: `UP040` — keeping `JSONValue` + `JSONScalar` as `TypeAlias` unions is an owner ruling (a `type` statement makes `isinstance(x, JSONScalar)` raise `TypeError`, measured on 3.12). |
| A2 | removed branch's invariant pinned where it moved | pass | B23 `test_b23_both_connection_settings_read_back_on_both_paths`: `getconfig` DEFENSIVE `True` + TRUSTED_SCHEMA `False` on the read and the write path; deleting either setter → `FAILED (failures=2)`. B6's event lists drop the 3.11 alternative. |
| A3 | generated copies | pass | paste-ins + `ext/bin/cement` regenerated (W1/N7 green). |
| A4 | full gate green | pass | the CI gate in this commit's body; fast gate 8 modules / 206 tests rc 0, the slowest-tests list printed. |

## p131 close (MAINTAIN queue run 3, tier `data`: dependency instruments; the vulnerability triage = MAIN) — target = the commit landing this section

Check set = the row's acceptance clauses A1-A4 + a security lens S1, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | `.agent/pins` lock row | pass | `open-webui lock transitive` = a fresh compile of the lock's header requirement (`open-webui==0.12.3`, Python 3.12) vs the lock's pins (`compile_drift`, shared with p34's constraints row); it found `jiter 0.17.0 -> 0.18.0` → the lock refreshed by its header command + `--upgrade` (an existing output file otherwise keeps its pins); fired by lowering `jiter` again → rc 1; shipped → 28 pins, rc 0. |
| A2 | committed OSV audit | pass | `.agent/owui-audit` = `pip-audit==2.10.1` (latest; its own `.agent/pins` row) `--require-hashes --disable-pip` over the lock; findings keyed `<package> <id>` (one advisory can name two packages; pip-audit repeats 30 of its 155 entries) against `owui-audit-holds.json`; rc 1 on `jinja2==2.10` (6 UNHELD) and on the holding row dropped (125 HOLD-GONE); rc 0 on the shipped lock with every finding held. |
| A3 | seeds recorded | pass | `.claude/rules/gate-checks.md` `.agent/pins` bullet (lock row + audit seeds). |
| A4 | `pins.md` names both | pass | the Open WebUI target bullet: refresh command, audit command, holds, `--emit-holds`. |
| S1 | the findings themselves | find → row `p137` (held) | 125 advisories in 15 packages, every one an EXACT pin in `open-webui==0.12.3`'s own `requires_dist` (checked against PyPI metadata), and 0.12.3 = the latest release + the owner-ruled target mirroring production ⇒ no in-repo fix; the production instance carries the same set — reported to the owner at the run's close. |

## p130 close (MAINTAIN queue run 3, tier `docs`: a gate step wrapping an existing audit; owner-approved gate change) — target = the commit landing this section

Check set = the row's acceptance clauses A1-A4, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | step `articles` after `register` | pass | `.agent/gate` full + `--omit-d28` branches; the fast gate stays static checks + modules + spec-lint. |
| A2 | firing | pass | seed commit 4fddc2d (this tree + S17's `cached` sentence in `docs/architecture.md`), CI run 40028039097: both legs `articles 1` (`docs/architecture.md:345 the cached`), every other step 0 (full leg unittest 0 in 1488.1 s, D28 included), gate rc 1; branch `ci/p130-seed` deleted. |
| A3 | `ops.md` Gate + `spec.md` Artifacts list the step | pass | both lists; `human-facing.md` + the `gate-checks.md` S17 bullet name it. |
| A4 | full gate green | pass | the CI gate in this commit's body. |
| P1 | the step's first catch | pass | it flagged this unit's own README rewrite (`the workflow`, `the definite-reference`), reworded before the seed; the README step list also gained the three steps it omitted (`zizmor`, ShellCheck, the report anchor check). |

## p88 close (MAINTAIN queue run 3, tier `docs`: a milestone plan; the build = row p136) — target = the commit landing this section

Check set W1-W8 fixed before the review; consultant-1 reviewed revision 1 (`93ff847`, Open WebUI 0.12.3 from the installed wheel); MAIN re-derived the decisive claims and ruled each row; revision 2 = the plan this commit lands.

| id | lens | consultant-1 | MAIN ruling + basis |
|---|---|---|---|
| W1 | premises | defect | accepted: Q2 rewritten (the outlet runs before delivery; `_pairs` returns miss/record pairs, hits need `_tool_calls`); Q5 rewritten (`--receipt-id`; reconstruction uncached; p35's cache keys the whole ledger). |
| W2 | S1 outlet timing | defect | accepted after MAIN read `open_webui/utils/middleware.py`: the non-streaming handler awaits `outlet_filter_handler(ctx)` before `return response` → S1 = enqueue a descriptor, a bounded worker does the model + Cement work; duplicate `/api/chat/completed` admission named. |
| W3 | S2 cost + captured version | defect | accepted: a ledger commit invalidates p35's cache by design (its contract C2/C4), so telemetry goes to a separate store (T6); `agreed` from the captured hash; no cost claim before `resolve → record → resolve` is measured. |
| W4 | S3 counts + inspection | gap | accepted: retained original input + `observations`; group by distinct hash; cutoff, empty window, order, dropped/failed counts; learning-tool reads. |
| W5 | S5 discrimination | gap | accepted: one frozen primary completion replayed at rate 0/1 (two fresh chats differ); mixed + all-agree + all-disagree controls; call counts; duplicate delivery, blocked, failed and version-move cases. |
| W6 | docs map | gap | accepted: supported scope instead of blanket absence; oracle + proof-of-request caveats; telemetry-store classification; p87 E3 named as a future integration. |
| W7 | Intent + Decisions | gap | accepted: S4 states that drift never gates, switches or challenges; prototype + nucllei waiting rulings stay scoped as written. |
| W8 | owner decisions | gap | accepted: T6-T9 added; tier `kernel` for selection, identity, isolation + verdict. |

## p89 close (MAINTAIN queue run 3, tier `kernel`: public API typing; the runtime dicts unchanged, re-checked by the p32 differential) — target = the commit landing this section

Check set = the row's three acceptance clauses A1-A3 + the code diff lenses C1-C3, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | each dict-returning public method returns a TypedDict or a dataclass | pass | 16 functions retyped (13 `System` methods, `learning.cases`, `projection.draft_program`, `CompilePolicy.as_json`); `test_no_public_function_returns_an_untyped_dict` walks every public function of every `src/cement_runtime` module (`JSONValue` unions exempt: a JSON document, not a record) — red at the parent with 16 offenders. |
| A2 | mypy `--strict` over a committed caller fixture: zero Any-typed field reads | pass | `tests/typed_records_caller.py` binds all 175 field reads to their declared types under `--strict --disallow-any-expr` → `Success`; at the parent the same fixture → 172 errors; `MYPYPATH` = the tree's own `src` (D28 replays check their own revision). |
| A3 | the CLI's JSON byte-identical | pass | `p32-differential.py --base ebbfe76`: every behavior + CLI probe identical; the one differing record = `S01.29.public-signatures` (the two return annotations this row changes). Runtime values stay plain dicts. |
| C1 | correctness of reshaped builders | pass | `artifact` builds its summary before parsing the document (stored-field errors keep their order); `test_projection` keeps the key insertion order (`{**entry, "pending", "ready"}`, `items` last); `set_projection` returns `str` ids (stored ids already strings). |
| C2 | public surface | pass | `Publication.projection` → `ProjectionChange | None`; record names importable from `cement_runtime.models` / `.projection`, none added to `__all__` (R3 freezes it); README `## Library API` names them; casts the typing made redundant removed (`cli.py`, `learning.py`). |
| C3 | generated copies + censuses | pass | paste-ins + `ext/bin/cement` regenerated; fast gate over every module but D28 + `test_source` → 1421 tests OK; article audit 437 grounded words (the S17 record updated). |

## p90 close (MAINTAIN queue run 3, tier `docs`: metadata + links; PyPI's own renderer = the live spot-check) — target = the commit landing this section

Check set = the row's three acceptance clauses A1-A3 + a prose lens P1, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | `[project.urls]` names repository + docs | pass | root: `Repository` + `Documentation` (`tree/main/docs`); the p34 provider wheel too (`tree/main/examples/command_source`); `tests/test_publication_metadata.py` pins both + the docs directory exists. |
| A2 | every README link resolves on PyPI's renderer | pass | 10 links → absolute repository URLs (9 relative paths + the bare `#the-learning-pass`, which `readme-renderer` 46.0 would render beside its own `user-content-` heading ids); `readme-renderer[md]==46.0` (PyPI's renderer, latest) → 10 repository hrefs + 15 generated heading self-links, every self-link matching an emitted id; curl on remote `main` (dbe9db0): 7 of 8 targets 200, `examples/outbox/README.md` 404 until the owner pushes 5660494 (the test binds each `blob/main/<path>` to a tracked file). |
| A3 | no trusted-publishing workflow without approval | pass | none added; publishing stays outside this phase. |
| P1 | prose pins | pass | link targets only (register + article audits blank them): register gate rc 0, article audit 0 ungrounded, tripwires PASS, fast gate 9 modules / 313 tests rc 0. |

## p87 close (MAINTAIN queue run 3, tier `docs`: a milestone plan; the build = row p135, tier `kernel`) — target = the commit landing this section

Check set V1-V10 fixed before MAIN's review pass (seeded for consultant-1, who declined it: trust-gate reviews route to MAIN under the user's global instructions, so MAIN ran it).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| V1 | premises hold at HEAD | pass after edits | 15 actor-bearing writes (`_text(…, maximum=256)` sites in `system.py`); triggers + FKs read from `store.py` → P8 added (`examples.proposal_id` FK; `projection_programs` shared across partitions; five child tables reach their partition through a parent). |
| V2 | E1 unforgeable by the chat model | defect → fixed | write-time checks alone are bypassable where the model can write the ledger (nucllei `/workspace/.cement`) → P7 + the stored attestation re-verified on serving, `allowed-signers` on a read-only mount; HMAC dropped (the verifier would hold the minting key inside the jail); `previous` binds the prior switch row, and the rollback left when rows can be deleted is published. |
| V3 | authorization stays outside Cement | pass | the minting side decides who gets a signature; `allowed-signers` = deployment configuration; Cement applies no role logic (M3.1 kept). |
| V4 | E2 names every plaintext copy | pass after edits | file list = ledger, `-journal` (+ `-wal`/`-shm`), the export's temporary file, bundles, backups, swap; SQLite temp files stay in memory (`temp_store = MEMORY`). |
| V5 | E3 rows exact | defect → fixed | a shared `projection_programs` row goes only when no other partition names it; child tables reach the grant through their parent; prune age vs learning cadence stated; backups named. |
| V6 | E4 + E5 key, verifier, process-free | pass | signer = the publisher's SSH key (D6); verifier = in-process SSHSIG + RFC 8032 Ed25519 (stdlib `hashlib` SHA-512 + integers; feasibility from RFC 8032 §6's reference code, not probed here), so the eval audit-hook claim holds; a library verifier added. |
| V7 | threat-model + README bullets complete | pass after edits | added `## Untrusted` reviewer-label bullet, `## Enforced controls` switch bullet, three README `Deployment boundary` sentences. |
| V8 | Intent + Decisions conflicts | pass | the switch stays the one human gate (E1 strengthens it); stdlib-only + embeddings kept (E2 declines a cipher dependency, D4); schema v4 = D5. |
| V9 | missing property or risk | pass after edits | key removal = fail-closed, clock skew (nonce stops replay), rollback residual, backups. |
| V10 | gates fail on the unbuilt tree + catch the classic defect | pass after edits | raw-SQL switch row + copied older row → `off`; shared program kept on erase; collision-pair partition. |

## p37 close (MAINTAIN queue run 3, tier `data`: `System.submit_proposal` re-grades every field the relay sends; the example is caller code) — target = the commit landing this section

Check set = the row's acceptance clauses A1-A4 + the code diff lenses C1-C3, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | id bound to partition + revision + canonical input + candidate + source revision | pass | digest over the canonical envelope; `test_the_id_binds_the_content` varies each of the 7 fields → `IntentConflictError`, same content → no-op, zero proposals. |
| A2 | same id / different content rejected | pass | A1's subtests; the refusal rolls the `BEGIN IMMEDIATE` back, the table keeps one pending row. |
| A3 | acknowledgement-crash probe shows duplicates | pass | a real relay process exits 70 between Cement's commit and the acknowledgement: unkeyed → 2 proposals, identical input/output/provenance/revision; keyed (`source_id = outbox:<id>`) → 1 proposal, `replayed`, attempts 2. The row predates core `source_id` uniqueness, so the probe shows both. |
| A4 | docs = lost-intent protection only | pass | README opening + `## Delivery is at least once`; no exactly-once claim; the revision window published (find p134). |
| C1 | correctness | pass | acknowledgement guarded by `state = 'pending'`; a revised operation → `stale`, no proposal; the conflict branch accepts only `submit_proposal`'s repeated-`source_id` text and re-raises anything else. |
| C2 | censuses an addition enters | pass | D23 `added_surfaces` + tripwire `DOCS`/`OWNERS` admit the README (table re-emitted: 1 `request` hit, PASS); L24 green; glossary +4 taught referents (intent, outbox, probe, relay). |
| C3 | altitude | find → row `p134` | the window is a core gap (`submit_proposal` has no expected revision), so the fix belongs in the core, not the example. |

## p34 close (MAINTAIN queue run 3, tier `data`: `System.propose` + `parse_json` re-grade every byte the runner passes; the smoke + metadata pins = structural validator + live spot-check) — target = the commit landing this section

Check set = `CLAUDE.md` `Engineering` code diff lenses (correctness, cleanup, altitude) + the row's five acceptance clauses A1-A5, fixed before the diff was reread.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | second wheel beside a wheel-only core | pass | `.agent/decisions/p34-two-wheel-smoke.sh <tree>`: the core wheel alone installs no `cement-command-source`; both install offline; wheel members = `cement_command_source/{_command_supervisor,command_source}.py` + dist-info, license bytes = `LICENSE`. |
| A2 | core loads no optional module | pass | smoke: `cement_runtime.cli.main(["--help"])` in the installed venv leaves no `*command_source*` in `sys.modules`; R4 (`tests/test_relocation_battery.py`) unchanged. |
| A3 | one documented runner command | pass | `cement-command-source` = `command_source.main`; README block run literally in a scratch copy (`pip install dist/*.whl` → `{"proposal_id": …}`); D23/D24 + R5 green (one Python block kept). |
| A4 | root gate + clean smoke | pass | fast gate over the 9 touched modules (309 tests, rc 0) + the CI gate in the commit body; smoke fires both ways (wrong `sources` prefix → rc 1, every hatchling hash wrong → `Hash mismatch`). |
| A5 | release/version ownership | pass | README paragraph; `test_the_core_range_admits_this_core_and_stops_at_its_next_minor` binds the range to the core's own version. |
| C1 | correctness: exit map, input, abbreviation | pass | the core's class table copied in order (CandidateSourceError ⊂ CementError → 2); `allow_abbrev=False` (`--inp` refused); stdin bounded on byte + text streams, the unit named as measured (finding during review: a text stream reported `bytes` → `characters`, tested). |
| C2 | cleanup: duplication vs coupling | pass | `_emit`/`_input`/the exit table restate ~30 lines of `cement_runtime.cli` privates; importing those privates would bind a separately versioned wheel to unpublished names. |
| C3 | altitude | pass | no core change; hatchling only because `uv_build` packages a module directory and R1/R2/R5 pin the flat files in place. |
| C4 | pins law | pass | hatchling + 5 build dependencies hash-pinned; `.agent/pins` rows `command-source hatchling` + `command-source build constraints` fire (seeds in `gate-checks.md`), shipped rc 0 (26 pins). |
| F1 | smoke runs by hand alone | find → row `p133` | a gate change, so it is put to the owner at the run's close. |

## p35 close (MAINTAIN queue run 3, tier `kernel`) — target = `d155dca` (implementation) + the commit landing this section (bench)

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| C1 | observation soundness | redesigned before code | consultant-1 (paired controls, SQLite 3.53.1 + 3.40.1): closing a second raw descriptor dropped this process's locks (a cross-process COMMIT landed under a held snapshot) → token = observer `PRAGMA data_version`; scope ruled by the owner (writes through SQLite). |
| C2 | implementation | finding → fixed | consultant-1's audit: the observer read `journal_mode` before `data_version` refreshed its pager → one-call WAL miss; order swapped, one-call regression pinned (old order → `database is locked`); re-audit accepted. |
| C3 | isolation | pass | deep copy per hit; caller mutation never reaches a later call (test). |
| C4 | C8 bench | pass | `.agent/decisions/p35-resolve-bench.json` at `d155dca` (nixbox, load 8-10): warm/cold 0.032 at 1,000 and 0.034 at 50,000 (≤ 0.10). |

## p36 close (MAINTAIN queue run 3, tier `kernel`) — target = the commit landing this section

Check set = consultant-1's contract rows K1-K6 (before code) + MAIN's implementation lenses M1-M3.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| K1-K2 | affected set, digest preimage | pass after edits | member-local findings from `_snapshot_member` + ambiguity derived from rows (all claimants; a UNIQUE index confines claimants to distinct revisions); P3 refusal; digest = `_digest_strings` length-prefixed, no size ceiling, binds the display. |
| K3-K4 | one-lock recompute, race, rerun | pass after edits | Q3 rewritten: the immutable event is the receipt and the tagged set must match its full count + id hash (a forged `suspend_artifact` tag and a partial tagged set → conflict, both tested); displayed-plan change → conflict with zero writes; an unrelated commit still applies. |
| K5 | bounded event | pass | `_id_list_projection` over the complete sorted set; payload keys pinned in `EVENT_PAYLOAD_KEYS`. |
| K6 | serving after containment | pass | P4 states containment publishes no replacement; test: `follow` stays failed after a quarantine. |
| M1 | atomicity | pass | a planted event failure rolls every suspension back (`test_a_failing_event_rolls_every_suspension_back`). |
| M2 | censuses | pass | B20 + `quarantine_plan` read site, `quarantine` write site, `_quarantine_plan` helper (derived); identity + event censuses gain the writer; grammar SHAPE re-pinned (251 rows). |
| M3 | prose | pass | L24 refused `ambiguous` in a new README line (deleted-surface vocabulary) → reworded; article + register audits rc 0. |

## p32 close (MAINTAIN queue run 3, tier `kernel`) — target = the commit landing this section, base `1b5b7d7`

Check set fixed before the diff was read: reviewer-1's R1-R11 (frozen refactor `archive/p32-wip`) + MAIN's M1-M4. Blind equivalence corpus = tester-1 (`archive/p32-tester`), written against the baseline alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1-R8 | correctness: stage order, SQL order, the seven-check vector + previews, exception classes + messages, operators + operand order per family site | pass | reviewer-1: source audit + a same-ledger trace differential (six calls; payloads + ordered SQL, executions, callbacks; 94,379 bytes each side, `cmp` rc 0; controls: swapped SQL and a changed `FunctionCheck.detail` both caught). MAIN reran tester-1's blind corpus on the final tree: `uv run python .agent/decisions/p32-differential.py --base 1b5b7d7` → `SAME 2712`, `RESULT: PASS` (13 families); its `--self-test` mutants (a detail literal, two swapped checks) → `DIFF`. |
| R9 | test edits keep strength | pass | B20 expected set + exactly the 11 connection-taking helpers the census itself derives (owner-approved extension); X11 + D16 name `_learning_case_groups` where they named `learning_cases` (the provenance parse moved unchanged; set size 3 either way) → put to the owner at the run's close. Register RG1 (census blind spellings): reversed scope operands + inline sealed-field compares now caught, each control reds its own test; a policy re-encoded through a temporary variable stays a disclosed limit. |
| R10 | generated copies | finding F1 → fixed | a late `system.py` edit left the paste-ins + the nucllei command stale (W1/N7 red); regenerated; W1 + N7 green. |
| R11 | dead code, misleading text | pass | removed inline stages each have a called replacement; the binding-family comment matches the sites. |
| M1 | no E/F System method | pass | `uvx radon cc -s -n E src/cement_runtime/system.py` → none (was F 70 + E 37/35/34/31); `cli._run` F 77 sits outside `System`. |
| M2 | public facade | pass | 41 public `System` methods, signatures + `__init__` exports identical (`1b5b7d7` vs this commit); control `6e9e715~1` → `6e9e715` reports 39 vs 41. |
| M3 | operators under the suite's fakes | finding → fixed before review | a first draft spelled member scope as `==`; `_LeftMismatchText` overrides `__ne__` alone → 8 subtests of `test_function_report_member_rows_validate_middle_and_last_scalars_and_bindings` red; every predicate now keeps the original `!=` with the stored value on the left. |
| M4 | stored-int census | finding → fixed | three `bool(...)` wrappers added for mypy read as unguarded coercions (`p03-stored-int-census.py` rc 1); replaced by annotated locals + `any(...)`; census 91 sites, 0 unguarded. |

## Security review (MAINTAIN, ad-hoc) — target = the implementation at `99f260a`, fixes `4eaf102` `5c81bde` `95fb113`

Owner body: threat surface from `Intent` + `Artifacts`; committed scanners run (a stack with none = a finding); a manual pass over remotely reachable code on a check set fixed before any code was read; trust model: env vars + CLI flags trusted, the server = the enforcement boundary, auto-escaping holds outside raw-HTML sinks; every finding above informational fixed, the rest → `.agent/deferred.md`. MAIN alone (security vocabulary stays off the teammate route). Surfaces: L library + CLI; O Open WebUI paste-ins (remote via Open WebUI) + `local.py`; N nucllei jail command (via the chat model's `run_shell`); P prototype server (loopback); X other examples; K skills; G CI + gate tooling. Every scanner verdict carries a positive control run beside it.

| id | row | verdict | basis (MAIN-verified) |
|---|---|---|---|
| SC1 | `uv audit --locked` | pass | rc 0, 34 packages, 0 vulnerabilities; control = S10 record (`jinja2==2.10` → rc 1), not rerun. |
| SC2 | gitleaks, whole history | pass | rc 0; control: planted AWS + `ghp_` keys in a scratch dir → rc 1. |
| SC3 | ruff `S` + its suppressions | pass | rc 0 over `src/` + `examples/`; control: `shell=True` + `pickle.loads` file → 2 hits. Every `S` noqa reason re-read true: S603 ×4 argv lists, no shell; S608 ×3 code-chosen fragments, values bound `?`; S101 ×5 narrowing only (`system.py:6471`: `_contradicted` returns first on a NULL hash, `_program_by_hash` raises on a missing row); S310 loopback; S102 = the digest-sealed embedded library; S105 (new, F1) = Open WebUI's public no-login password, read only to replace it. |
| SC4 | scanner per stack | finding F4 (low), fixed | Python src + examples: SC1-SC3. Actions + Dependabot YAML: none → zizmor by hand 2 medium (F3). Shell (6 tracked scripts): none → ShellCheck by hand 1 info (SC2016, false positive). Prototype Python + JS: none, informational, no row — Template ruling (1) keeps the prototype outside every gate; by hand: ruff `S` 1 hit (S311 `demo.py:674`, the seeded latency RNG, non-crypto), `pnpm audit` 0 (Playwright 1.64.1). |
| M1 | SQL injection | pass | 3 f-string statements + 1 `.format` in `system.py`: code-chosen fragments, values bound; `store.py:716` constant PRAGMA; examples + prototype run no SQL of their own (System API only). |
| M2 | shell/process injection | pass | process sinks: `src/`, `hospital_ocr`, nucllei generator 0 (control `local.py` 6); `command_source` argv list, `shell=False`, request on stdin; `local.py` fixed argv; prototype `_cli` argv list (request-chosen elements via F5 stay argv); nucllei documents via `write_file` + `--input-file`, the CLI skill's JSON via stdin files, nucllei `--request '…'` quoting = the user's own jail; `gate.yml` has no `${{ }}` in `run:` (zizmor clean). |
| M3 | template + XML entities | pass | no template engine, no XML parser in src/examples/prototype Python; `.format` only over code constants (`system.py:1499`, `generate.py` `LOADER`). |
| M4 | file paths | pass | CLI paths = flags (trusted); bundle reader `O_NONBLOCK` + `fstat` regular + bounded; export atomic 0600; nucllei `--input-file` = a read in the user's jail (its model holds `run_shell` already), `_discard` only under the resolved `$CEMENT_HOME/in/`; prototype static = `resolve()` + parent check; action `makedirs` on the admin-set valve. |
| M5 | authn/authz + escalation | finding F1 (high), fixed | `local.py` Open WebUI: any web page → admin token → `tools/create` exec (repro below). Pass elsewhere: learning tool `_run` role admin per call; action role admin + offered value + confirmation `True`; chat tool read-only, `record_answer` writes nothing; filter = the single proposal writer by design; `__user__` server-side; nucllei jail = the boundary (switch reachable by the model, README limit); prototype = F5. |
| M6 | session + token handling | pass | nucllei ticket `t_` + `secrets.token_hex(8)` per lookup, consumed by `record`, 24 h TTL, per-user workspace; Open WebUI actor from server-side `__user__`; F1 fix: `WEBUI_SECRET_KEY` + admin password 64 hex, 0600 (`_kept_token`); prototype has no session or cookie. |
| M7 | secrets + crypto | pass | gitleaks clean; sha256 throughout, no md5/sha1; ids `uuid4`, temp names `os.urandom`/`secrets`; unkeyed `function_hash` = documented integrity, not a signature; no TLS client (loopback `urllib` only); model key by env alone (W6 pin). |
| M8 | deserialization + eval | pass | no pickle/marshal/yaml; `exec` = the paste-in loader over the embedded library (digest-checked, admin-pasted code); projection = closed interpreter, no eval, no regex on input; strict `parse_json` on CLI stdin, bundles, nucllei input/output; filter `json.loads` of tool arguments → `canonicalize` (R8). |
| M9 | raw-HTML sinks | pass + register | prototype: 22 `innerHTML` sinks; every value a cross-origin request can write into state (terminal `display`/`argv`/`stdout`/`reading`) renders through `esc` in a text context; `esc` omits quotes, and attribute interpolations carry fixture values alone. Open WebUI: tools return JSON; notifications reach the requesting user's own session. R5. |
| M10 | SSRF | pass | outbound = `local.py` to its own loopback instance; `--base-url` = a CLI flag; no tool or filter makes a request; gate tools fetch fixed GitHub URLs behind a sha256 refusal. |
| M11 | data exposure | pass + register | no secret in logs (W6, gitleaks); F1 also exposed the model key through admin config routes (closed with F1); error + notification text = `CementError` text (M5.3 S6); R2, R6. |
| M12 | dependencies + supply chain | findings F3 (low), F6 (informational) | F3 Dependabot cooldown = GitHub's implicit 3 days (zizmor floor 7) → fixed. F6 `local.py setup` installs `open-webui==0.12.3` unhashed → p128. Pass: `uv.lock` hashed; actions SHA-pinned, `contents: read`, `persist-credentials: false`, `pull_request` only; gitleaks/zizmor/ShellCheck sha256-pinned; driver.js + fonts byte-checked (`pins.md`); paste-in digest = edit check, documented. |
| M13 | resource exhaustion | pass + register | 1 MiB / depth 64 / 100,000 items on every untrusted parse; projection linear (`work`); bundle 64 MiB before read; R3, R4; prototype `_body` unbounded on loopback (p127). |

Findings:
- F1 (high) `examples/open_webui/local.py:_environment` set `WEBUI_AUTH=False` and left `CORS_ALLOW_ORIGIN` at Open WebUI's `*` (0.12.3 `open_webui/config.py:2179`, `main.py:866` `allow_credentials=True`). Repro at `99f260a`: preflight from `https://attacker.example` → 200 + origin echoed; signin with a wrong password → 200 admin token; that token → `tools/create` → the pasted source wrote a marker file as the user. Fix `4eaf102` (owner pick: login + CORS): `WEBUI_AUTH` on, `ENABLE_SIGNUP` off, admin password kept 0600, a no-login `admin`/`admin` replaced; CORS = the instance's own two origins. Acceptance: `tests/test_open_webui_local.py` `test_s1_*` + W5 (red at `archive/sec1-red` = `1ea5ae1`), live: foreign preflight 400, wrong + `admin` signins 400, kept 200, second signup 403, Socket.IO foreign origin refused, browser sign-in OK.
- F2 (low) the threat model's "a retained answer is evidence … never an instruction" reached no learning skill. Fix `5c81bde`: the CLI, Open WebUI and nucllei learning skills treat proposal text as chat-user data (CLI: never in a command line; Open WebUI: no link or image from it in the report). Acceptance: the three `test_s2_*` (red at `archive/sec2-red` = `0387990`).
- F3 (low) see M12. F4 (low) see SC4. Fix `95fb113`: gate steps `actions` (zizmor `--offline`) + `shell` (ShellCheck), cooldown 7 days. Acceptance: seeds S21 + S22 (10/10 with S03 + S11), the full gate.
- F5 (informational) the prototype server accepts any `Host` and a `text/plain` POST → p127. F6 (informational) → p128.

Register (by design or documented; no change):
- R1 one chat user's fabricated `record_answer` pairs in two chats (`/api/chat/completed`) meet the 2-confirmation floor; under `follow` the learning pass alone stands between them and production (`examples/open_webui/README.md` `## What the example guarantees`, threat model `## Untrusted`, owner `CompilePolicy` defaults).
- R2 a wrong projectability call serves one user's output for another user's form of the same layout (Cement verifies grammar + consistency, never semantics; `Read` before the switch).
- R3 `resolve` pays full verification per call (35.5 s at 50,000 entries), reachable by any chat user (p35; quotas are deployment work). R4 no per-user cap on retained proposals (threat model `Deliberately absent`: quotas).
- R5 Open WebUI renders the learning model's Markdown: an injected image URL can carry ledger text out; F2 is a soft control, CSP is the deployment's.
- R6 retained provenance holds chat replies + request text (PHI in llens) in a plaintext ledger = deployment obligation (threat model: minimize, redact, encrypt).
- R7 filter notifications echo client-supplied call ids to the same user's own session only.
- R8 the filter's `json.loads` keeps the last of repeated keys, the same parse Open WebUI's tool call used, so both read one value; `canonicalize` grades it after.
- R9 pinned tool binaries in `.tools/` are not re-hashed on reuse (local only; CI starts clean).
- R10 the owner's `.open-webui/data` keeps `admin@localhost`/`admin` until its next `local.py serve`, which replaces it and prints the password file.

## Dependency + toolchain upgrade (MAINTAIN, ad-hoc) — target = the diff this commit lands, base `e7137f3`

Owner request = every dependency + toolchain pin at its latest release or a `.agent/deferred.md` row naming the blocker; owner pick at this request's question = repair D05's message parser (3.12.8+ bare choices). `reviewer-1`, 7 lenses fixed before it read `e7137f3..d27b462`; MAIN re-derived every row, then re-reviewed the later `_check_value` + D05 changes itself against the same lenses.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | pin completeness | finding F3 (minor), fixed | reviewer's independent inventory (34 locked packages, tools, 4 action SHAs, gitleaks checksums, Playwright, driver.js + 5 fonts byte-equal, Open WebUI 0.12.3, nucllei v20261020-01) = MAIN's; mirrors' Python + SQLite unqueued → p126. |
| L2 | CLI invalid-choice wording | pass | `_parser()` 48 nodes, all `_JSONArgumentParser` (reviewer probe, 3.11.17-3.15.1); `_check_value` final form: 4 CLI modules `Ran 349` OK on each of 3.11.17 / 3.12.15 / 3.13.17 / 3.14.9 / 3.15.1. |
| L3 | `gate.yml` | pass | setup-uv v10.3.2 exports `UV_PYTHON`, installs under `RUNNER_TEMP`, `cache-python` false ⇒ `only-managed` = newest patch per leg (CI run 39909959977: 3.12 leg `Using CPython 3.12.15`); `ubuntu-26.04` GA (runner-images README + announcement); actionlint 1.7.12's label table predates it. |
| L4 | live-law consistency | findings F1 F2 (minor), fixed | no version number left in `ops.md` / `spec.md` / `gate-checks.md`; `CLAUDE.local.md` build string = `uv run python -c 'import sys;print(sys.version)'`. |
| L5 | queue rows | finding F2 (minor), fixed | p123 blocker: V18 since `9a48c85`, D14 since `861c069`, both in D28's first replayed revision; grader PASS. |
| L6 | `pins.md` claims | findings F1 F2 (minor), fixed | GitHub cache docs: a run restores current- or default-branch caches, never a sibling's. |
| L7 | no check weakened | pass | D05 repair = owner-approved; assertions unchanged (exact set equality); seed: one survivor dropped → `failures 1` quoted + bare on 3.12.15 + 3.13.17, control OK. |

- F1 `pins.md` said a runner image re-keys D28 verdicts, while the key holds `sys.platform` (`tests/test_migration_battery.py:1862`) → interpreter build + SQLite re-key, an image alone keeps the key.
- F2 `pins.md` + p125 said Dependabot bumps `uv.lock` + action SHAs alone, while its `uv` updater rewrites `pyproject.toml` too (dependabot-core `d261cc7` `uv/lib/dependabot/uv/file_updater/lock_file_updater.rb`) → manifests + lock + action refs automated, range floors + the rest by hand.
- F3 the deployment mirrors (`local.py` `PYTHON = "3.11"`, stand-in `python:3.12-slim-bookworm`, SQLite 3.40.1) sit below latest without a row → p126, blocker = the owner-ruled targets (Open WebUI v0.12.3 `Dockerfile:59`, nucllei sandbox `Dockerfile:22`, both re-fetched by MAIN).
- Register adopted: p124 `beside` → `with each redistributed copy` (OFL also permits embedded metadata).
- Re-review (MAIN, each fix against its acceptance): `rg -Fc 'or runner image (' .claude/rules/pins.md` → 0; `rg -Fc 'action SHAs alone' .claude/rules/pins.md .agent/deferred.md` → 0 + 0; grader PASS with p126.

## `CLAUDE.md` refresh agents@897faa7 → agents@b78f436 + offload move + CI gate + 3.11 leg (MAINTAIN, ad-hoc) — target = the diff this commit lands, base `a1a08de`

Template delta = Git `ci/*` pushes, NEW `CI gate`, `CLAUDE.local.md` tier. Owner request = offload/nixbox law out of `.claude/rules/` into `CLAUDE.local.md`; owner picks at the session's question = CI gate installed + the 3.11 leg fixed now, p119 superseded by the CI gate. `reviewer-1`, 10 lenses fixed before it read the diff, primary tree read-only (target sha256 `4990af7f…` over its run; MAIN's fixes after it). Teammate verdicts re-derived here.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | template fidelity | pass | `cmp` rc 0 vs agents@b78f436: `CLAUDE.md`, 6 roles, `.agent/spec-lint` (100755); HEAD's copy = agents@897faa7 ⇒ no local law in the replaced lines. |
| L2 | obligation coverage | pass | Git `ci/*` → `ops.md` Commits; `CI gate` → Template rulings (5) + `gate.yml` `ci/**` + `.agent/ci-gate` + the 3.11 repair (green-`main` precondition); `CLAUDE.local.md` tier → `.gitignore:21` + the move. |
| L3 | owner request | pass | `rg -n 'offload\|nixbox' .claude/` rc 1 (HEAD: 3 lines); every moved fact in `CLAUDE.local.md`, the portable remainder in `ops.md` / `history-gates.md` / `gate-checks.md`; nixbox's 3.13 build re-measured (`main, Jun 11 2026, 04:03:13`). |
| L4 | old forms | pass | `I handle remote`, `nothing machine-specific.` → 0 live hits (HEAD controls 1 each); `drives remote` → the new Commits clause; `offload` / `nixbox` → `.agent/decisions/*` + `.agent/archive/` alone. |
| L5 | spec preservation | pass | `Artifacts` Gate line alone; unit/`p<nn>` token stream sha256 equal, headers equal; spec-lint rc 0. |
| L6 | check strength | pass | 3.12+ assertions unchanged, b02 adds field `kw_only` + `__slots__` pins; both modules OK on 3.11.17 / 3.12.14 / 3.13.14 / 3.14.8; 3.11 credit + survivor rulings `.agent/decisions/py311-mutate.txt`; skip census 3 members; `seeds --list` 20 groups. |
| L7 | `.agent/ci-gate` | pass | `bash -n` + `shellcheck` rc 0; no arg / tracked change outside HEAD → rc 2; verdict source `gh run watch 39801982661 --exit-status` → rc 1; reviewer's remote-free harness: green → rc 0 + delete, red → rc 1 kept, no run → rc 2. |
| L8 | queue soundness | finding F1 (minor), fixed | p119 row + status byte-verbatim; grader PASS. |
| L9 | law consistency | finding F2 (minor), fixed | `sys.platform` + `sys.version` key; no host or clone component (`tests/test_migration_battery.py` `_d28_content_key`). |
| L10 | claim soundness | findings F1-F3 (minor), fixed | run 39801982661 = `a1a08de`, 3.11 leg red alone; mutation tallies match the log. |

- F1 p119's `Closed:` asserted four green legs before the first CI run existed → it names the closing commit's body as the carrier of the observed run.
- F2 `history-gates.md` + `ops.md` said another host or clone replays cold, while the key holds neither (a copied store hits — the CI cache relies on it) → a clone without the store, or a different interpreter build.
- F3 `CLAUDE.local.md` stated this controller's uv as 0.13.1 (now 0.13.5) → the `sys.version` strings D28 keys on, both re-measured.
- Re-review (MAIN, each fix against its own acceptance): each of the four finding anchors `rg -Fc` → 0 in its file (positive control: the new `Closed:` line = 1); grader PASS, spec-lint rc 0, acceptance rc 1.
- Survivor rulings (3.11 credit, subject `Store._connect`): reviewer-1 = 10 contract-open + 2 equivalent; MAIN reran S2 (siblings b05 + b06 read arguments `FAILED (failures=2)`) and S6 (3.11 module OK; neither `Connection.setconfig` nor `SQLITE_DBCONFIG_DEFENSIVE` exists).

## p120 close (MAINTAIN queue row, tier `docs`: skill text + its replay) — target = the commit that lands this section

MAIN alone; check set = the row's acceptance + the standing pin-repair approval.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| P1 | pin repair (standing approval: prose pin re-targeted at the new claim) | re-targeted | `tests.test_learning_pass_battery.ProjectableResumeBattery.test_lp0d_the_skill_keeps_the_candidate_until_projection_set`: superseded claims (keep `program.json` until step 4; check `projection show`) → the step-1 recovery rule + `cement learn cases "$OP" --projectable` + "a pass that stops resumes from step 1 with no saved copy" + workflow.md's manual-route "Keep `program.json` until `projection set` succeeds"; red at `a8daf43`, green here; nothing deleted, skipped or weakened |
| P2 | skill commands parse; LP3 leaf floor | pass | `SkillBattery` green, its ten-leaf floor unchanged (per-id leaves live in workflow.md `Manual route`) |
| P3 | replay of the skill's own commands | pass | `SkillReplayBattery` red at `a8daf43` (skill commands differ), green here: L1 → 1 version, 2 members, switch off |
| P4 | pin repair (standing approval) | re-targeted | `tests.test_phase_integration_battery.SkillResumeBattery.test_x3_the_saved_program_resume_covers_cases_with_differing_active_outputs` errored in this unit's first full gate (its anchor `If program.json exists` left with the saved-program rule); the property (a resumed pass finishes step 3 for cases with pending proposals or more than one active output) is restated in SKILL.md step 2 and the anchor re-targeted to `a pass that stops resumes from step 1`; the workflow half unchanged |

## p118 close (MAINTAIN queue row, tier `kernel`) — target = `3586dc4..30062c8` (`archive/p118-impl`), squashed in the commit that lands this section

Check set = reviewer-1's 9 rows, seeded before it read `3586dc4..1c6a9f7`; round 2 = F1-F5 against their own acceptances on `1c6a9f7..a8daf43`, + R2-F1 fixed in `30062c8`. Contract = `.agent/decisions/p118-contract.md` L1-L8. Teammate verdicts re-derived here.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | `learning.py` vs L1-L5 | fixed F1 F2 | F1: a string id list raised plain `ValidationError` → `MergeRefusedError("not_a_list")` via public `check_merge_ids`; F2: a `System.proposal` read sat inside the write phase → every compared output comes from the case snapshot. Both red at `1c6a9f7` (`test_merge_refuses_before_any_write`, `test_merge_reads_each_output_from_its_case_and_wraps_a_failing_first_write`, `test_learn_merge_reads_no_proposal_row_so_no_read_fails_between_writes`) |
| R2 | example parity (L7) | fixed F5 | nucllei graded the output before the id lists → `check_merge_ids` first; `LibraryOrderBattery` (2 tests) red at `1c6a9f7`; the base precedence also restores no ids + no ledger = exit 2 |
| R3 | CLI leaves (L6) | fixed F2 | interrupted stdout now lists returned writes only; `learn cases --projectable` stdout `cmp`-identical on the fixture ledger (MAIN + reviewer, independently) |
| R4 | classic pitfalls | fixed F1 F2 | as R1 |
| R5 | new tests | pass | 18 tests red at `3586dc4` (16 errors `No module named 'cement_runtime.learning'`, 3 failures) |
| R6 | prose claims (L8) | fixed F3 F4 R2-F1 | "the writes that committed" → the writes that returned + the commit-then-raise window (README, architecture, docstrings, CLI comment, open-webui rule); "answers nothing until switched on" → the switch stays as it is |
| R7 | generated files | pass | both generators `--check` rc 0; `tests.test_open_webui_paste_in` OK |
| R8 | owner item | pass → owner-approved | the re-targeted census is strictly stronger (a planted library `set_switch` reds it; the base census is blind); owner approved the re-target at the queue run's question |
| R9 | scope | fixed F5 | no change outside the contract besides p120's birth row |

## nucllei skill request close (MAINTAIN, tier `kernel`) — target = `e325bdc` + the commit landing this section

Check set = reviewer-1's 12 rows, seeded before it read `00dc010..e325bdc` (`.scratch/nucllei/review/verdicts.md`), + R13 live re-check + R14 full gate at the closing commit. Contract = `.agent/decisions/nucllei-contract.md` N1-N8. Teammate verdicts re-derived here.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness vs N1-N6 | fixed F1-F4 | each finding red at `e325bdc` as `ReviewBattery` (failures=4, errors=3), green after the fix |
| R2 | no write on refusal paths | fixed F1-F3 | expired ticket: exit 3, deleted, no proposal; duplicate-key output: exit 2, ticket kept |
| R3 | robustness after durable writes | fixed F2 | `_discard` / `_remember` return a line; a ticket write failure = exit 5 + answer without recording; `main` maps `OSError` → exit 5 |
| R4 | classic pitfalls | fixed F3 F4 | `parse_json` (repeated key, 100,000-deep nest → exit 2); `read OP 0` → exit 3 |
| R5 | generator | pass | both `generate.py --check` rc 0; paste-ins change only by the loader fix below |
| R6 | learning parity with the OWUI tool | fixed F2 | state store after the writes; parity otherwise held, deviations named in the contract |
| R7 | skills ↔ command | pass | N8 census green after the G3 skill change (`use --input-file` exists in `_parser()`) |
| R8 | trust | pass + G3 fixed | N6 AST pin, N8 census; G3 (heredoc delimiter in a document runs the rest as commands) → `write_file` + `--input-file`, live d5 kept an injected `switch … off` line as data; `docs/threat-model.md` states the model-executed switch |
| R9 | llens conventions | pass | reviewer ran llens `parse_md_frontmatter`/`build_payload` over the 3 files; `cement-switch` alone has an empty description |
| R10 | README claims | fixed F5 | per-operation switch wording (`off` start, `follow`, `pin`) in README + `cement-learn.md`; `--input-file` documented |
| R11 | spec/contract/rule vs behavior | fixed | contract N1/N2/N5 + counts (G1), rule bullets, spec live-test line (source-built images, owner picked ghcr) |
| R12 | tests bind behavior | fixed | +8 `ReviewBattery` tests (incl. the 24 h / 24 h + 1 µs pair); battery 44 |
| R13 | live re-check | pass | `.agent/decisions/nucllei-live-e2e.md` § Re-check: d1-d6 with the file hand-over, in-turn learning, switch, hits, injected document inert, `in/` + `tickets/` empty after |
| R14 | full gate at the closing commit | see the closing commit body | — |

Rulings:
- reviewer-1's probe `test_merge_reports_durable_reviews_when_state_write_fails` expects a nonzero exit; ruled: exit 0 — the merge's writes succeeded, the output names them plus a line that the projectability ruling was not stored (contract N5).
- G2 (`_plain` + `dataclasses` unused) removed; removing `dataclasses` exposed a latent shared-`LOADER` recursion (`find_spec` lazily imports `importlib.machinery`, never preloaded under `python -I -S`) → N7 `test_n7_the_command_runs_on_the_standard_library_alone` fired with `RecursionError`; fixed in `examples/open_webui/generate.py` (preload before the finder), paste-ins regenerated (+3 lines each).
- Owner-ruled limits stay limits: per-user ledgers, the model-executed switch (empty-description skill), in-turn learning wait.

## MAINTAIN queue run close — target = the commit landing this section

Check set (the body's Met when): R1 every queue row closed by its acceptance in its own commit, owed with what it owes, routed, or waiting on its trigger; R2 the queue + ledger grader; R3 the standing censuses; R4 the full gate on a clean tree at this commit. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 29 open rows, each with a Status line: routed 20 (survivor backlog p93 + p99-p102 + p104-p116, and the p32 + p33 refactor; owner-ruled), owed-go 6 (p34 p37 p87-p90, offered and not selected), queued 2 (p35 p36, owner-ruled for a later session), trigger 1 (p52); every other row closed in its own commit (p05 + p92 share one gate-boundary commit, stated there). |
| R2 | acceptance | pass | `m3-deferred-validate.py` VERDICT: PASS. |
| R3 | integrity | pass | p03 / p10 / p76 / p94 censuses + p73 coverage rc 0; tripwires PASS; `m3-report-validate.py --all` 5 graded, 0 failed. |
| R4 | acceptance | see final message | the closing gate runs on this commit after it lands (a commit cannot carry its own gate result). |

## p77 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 one committed command fires every listed seed from a clean checkout in a disposable worktree; R2 byte-identical restoration; R3 per-seed rc + record line printed; R4 the rule names the command; R5 neutralizing one check flips exactly its seed; R6 harvest integrity. general-purpose-3 built; MAIN reran.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 20 groups for 20 bullets (coverage check refuses drift); MAIN added S19 + S20 for the p92 + p05 records written after the teammate base. |
| R2 | acceptance | pass | every tree reports `sha256-equal git-diff=0` on restore (MAIN runs). |
| R3 | acceptance | pass | each case line names `gate-checks.md:<line>`, expected vs observed rc + tokens. |
| R4 | acceptance | pass | intro paragraph of `gate-checks.md` (prose, so the bullet count stays the group count). |
| R5 | acceptance | pass | `--self-test`: only S12's four cases flip (teammate over all 18 groups; MAIN over S12 S13 S19 S20). |
| R6 | integrity | pass | `.agent/seeds` taken from `wt/general-purpose-3` @ `98ce02e` sha256-equal, then extended; S18 rerun on main's `.agent/mutate` 5/5. |

## p97 close (MAINTAIN queue run, owner ruling, tier `kernel`) — target = the commit landing this section

Check set: R1 the ruled ABI (v2 with `:` + `：`, v1 unchanged); R2 Japanese fixture: one layout, shared key; R3 threat-model claims re-checked; R4 pins moved + oracle; R5 run the real path. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | v1 programs parse + project exactly as before (ASCII-only separator); v2 adds `：`; ASCII drafts stay v1 byte for byte (draft test). |
| R2 | acceptance | pass | runtime + oracle: one layout, equal keys for two value sets; v1 refuses (`text`). |
| R3 | acceptance | pass | separator set fixed per ABI, no regex, linear `bound()` held on every v2 projection; threat model + architecture state it. |
| R4 | correctness | pass | `test_v1_exact_types_at_every_node`: `cement-projection-v2` moved from rejected to accepted, `cement-projection-v3` added as the unknown-version probe (strength kept); oracle extended in its own code path; red at `d75f22f` (3 runtime-side tests). |
| R5 | acceptance | pass | CLI `learn cases --projectable` → v2 draft; `projection test` → one key hash for both examples. |

## p86 close (MAINTAIN queue run, owner ruling, tier `docs` — PROTOTYPE law) — target = the commit landing this section

Check set: R1 Back restores a per-step snapshot of ledger + session; R2 Back across the third learn step < 500 ms; R3 state string after Back + forward equals the forward pass. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | checkpoint = `Session.clone()` per finished step (SQLite backup + deep copy); restore swaps in a copy; reset clears; replay remains the fallback. |
| R2 | acceptance | pass | 7 → 6 (third learn step) 50 ms; 8 → 7 51 ms. |
| R3 | acceptance | pass | both crossings: state after Back = forward state of the target step; after Back + forward = forward state again (fields STORY_AT, AI count, function count, switched-on count, chat length). |

## p30 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the wrap asserts the transaction state before delegation; R2 one successful result; R3 credential. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `observed == [True]`, recorded before the real call. |
| R2 | acceptance | pass | `result.passed` + `function_hash` equals the promotion. |
| R3 | integrity | pass | `.agent/mutate` at `impl/p30` (tag `archive/p30-credit`): killed 1702 / survived 1218 / invalid 50 of 2970; survivors → p116 (routed with the survivor backlog). |

## p49 close (MAINTAIN queue run, owner ruling, tier `kernel`) — target = the commit landing this section

Check set: R1 no node abbreviates; R2 the three examples exit 2 `unrecognized arguments`; R3 README states the break; R4 every moved pin named + re-targeted, none weakened. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | one walk at the end of `_parser()`; X23 censuses every node (red at `2b35f42`: all nodes listed). |
| R2 | acceptance | pass | `--part=p`, `--bun x`, `--in 0` → `unrecognized arguments` (single-token `--part=p`: a split `--part p` lets argparse report `p` as an invalid command first, also exit 2). |
| R3 | acceptance | pass | README Quick start sentence; register-audit rc 0, article-audit 0 ungrounded. |
| R4 | correctness | pass | X23 inverted (M3.5a kept abbreviation on purpose; owner overruled), D06 asserts the refusal, D10 asserts no claimed prefix (stricter), grammar digest re-pinned (allow_abbrev facet only, same 225 rows); D06/D10 keep their names (m3u5b catalogue targets). |

## p05 + p92 close (MAINTAIN queue run, owner-approved gate changes, one boundary) — target = the commit landing this section

Check set: R1 the gate runs each check; R2 each check fires on its seed; R3 the shipped tree passes; R4 the pinned `register` gate line is intact. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/gate` gains `step reports …m3-report-validate.py --all` in both full branches; `register-audit` grades every CLI `--help` page inside its existing step. |
| R2 | acceptance | pass | p05: `one-stale.md` rc 1, misdirected exemption rc 1 (`STALE-EXEMPT` + the record red); p92: seeded `simply` rc 1 naming `cement function switch --help`. |
| R3 | acceptance | pass | `--all` rc 0 (5 graded, 1 exempt); `register-audit --gate` rc 0 (46 help pages, filler 0). |
| R4 | correctness | pass | `tests.test_cli_removal_battery` (pins `step register uv run python .agent/register-audit --gate`) green. |

## p83 close (MAINTAIN queue run, owner ruling, tier `docs`) — target = the commit landing this section

Check set: R1 the ruled surface; R2 a fresh agent answers the near-match question from it alone; R3 each stated fact matches shipped code. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | one architecture section, no new CLI surface. |
| R2 | acceptance | pass | the near-match paragraph states both modes and the adapter action (exit 6 → send to the LLM). |
| R3 | correctness | pass | outcome rows = `cli.py` resolve branch (fixed key set, exit 0 iff matched); key rule = `### Projection` + `## Isolation and revisioning`; `operation list` leaf exists. |

## p73 close (MAINTAIN queue run, owner ruling) — target = the commit landing this section

Check set: R1 the ruled branch (b); R2 the script prints nothing over `a8109eb..HEAD`; R3 it can fire. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | preamble scopes the ledger and names the commit-body record for the rest. |
| R2 | acceptance | pass | `p73-review-coverage.py` rc 0 (this commit adds its own section, so it is covered too). |
| R3 | integrity | pass | dropping `a97bbc3` from its list → rc 1 `NO-RECORD a97bbc3`. |

## p75 close (MAINTAIN queue run, owner approval) — target = the commit landing this section

Check set: R1 owner approval of the exact text; R2 meaning kept; R3 measured shape. MAIN alone (advisor shaped the question).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | the committed text = the preview the owner approved, byte for byte (one 29-word sentence of the earlier draft split before asking). |
| R2 | correctness | pass | every claim of the old Intent survives: recurrence, learning pass, exact cases, read + switch, follow / pinned / rollback, LLM fallback, projection fail-closed, no key widening, library + CLI + skill, web UI demo. |
| R3 | acceptance | pass | 24 sentences, max 24 words, 0 ` = ` (counts in the ledger entry). |

## p22 close (MAINTAIN queue run, owner approval) — target = the commit landing this section

Check set: R1 owner approval for the deletion; R2 the survivor carries the claim. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | owner approved deleting the observational test (closing question); deletion = one test function, no skip added. |
| R2 | acceptance | pass | the mechanism test pins byte equality + the hash move at equal length and names the README sentence it backs; module OK. |

## Owner rulings recorded (MAINTAIN queue run, closing question) — target = the commit landing this section

Check set: R1 each ruled row carries its new status; R2 the approved survivor-scope rule is written where credit law lives. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | routed: p93 + p99-p115 (survivors, own MAINTAIN request), p32 + p33 (refactor request); queued: p35 p36 (later MAINTAIN session), p34 p37 p87-p90 (no selection); deferred grader PASS. |
| R2 | acceptance | pass | `.claude/rules/assurance.md` `## Verification integrity` gains the survivor-scope rule (subject = diff lines / named subject function; outside = contract-open by construction). |

## p95 close (MAINTAIN queue run, owner ruling) — target = the commit landing this section

Check set: R1 the owner ruling; R2 Decisions match the shipped header. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | owner: amend Decisions (the shipped state wins). |
| R2 | acceptance | pass | the two Presentation clauses now describe `index.html:12` (brand + Concept demo) and the tool-call caption at `app.js:840`; spec-lint rc 0. |

## p43 close (MAINTAIN queue run, owner ruling) — target = the commit landing this section

Check set: R1 the owner ruling; R2 the pins it keeps. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | owner: keep current behavior; close as ruled. |
| R2 | acceptance | pass | B11 (`VACUUM` parity) + B14 (`test_b14_malformed_read_keeps_state_error`) unchanged and green in the suite. |

## p06 close (MAINTAIN queue run, owner ruling) — target = the commit landing this section

Check set: R1 the owner ruling; R2 the replayable catalogues. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | owner: accept expired-source for u4c1; close on u4c5a + u4c5b. |
| R2 | acceptance | pass | both catalogues replay rc 0 (16/16; 12 + 1 ruled equivalent), recorded in the ledger entry. |

## p48 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 two-id order pinned; R2 duplicate → IntegrityError; R3 empty → zero SQL; R4 half-missing inputs; R5 M02/M03/M15/M26 rerun + killed; R6 credentials. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | fixed | documented order = arrival (`status_sequence`), like the feed + pending selections; red at `397a43a`, green after a Python-side sort (B34 freezes the SQL text, so `ORDER BY` stays out). |
| R2 | acceptance | pass | duplicate selection raises `IntegrityError`. |
| R3 | acceptance | pass | empty selection returns `total=0, rows=()` with no statement traced. |
| R4 | acceptance | superseded | the half-missing resolved-request writer left with `93007ac` (M3.6b); no production writer takes a half-missing input today. |
| R5 | acceptance | pass | M02/M03/M15 killed at HEAD (control 572 green); M26 = superseded (anchor count 0, removed in `93007ac`). |
| R6 | integrity | pass | 3 preservation pins credited (`.agent/decisions/p48-mutate.txt`, survivors → p115); paste-ins regenerated; p03 census rc 0. |

## p42 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 SCHEMA_VERSION + SCHEMA digest frozen; R2 identities read per writer; R3 every event branch's payload keys + the 1,001 sentinels; R4 invalid identities make 0 clock / id calls; R5 credentials; R6 harvest. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | digest + length + fingerprint equality; one-space SCHEMA edit → FAILED (module constant: 0 in-scope mutants, so the planted edit is its check). |
| R2 | acceptance | pass | identity-writer census green on today's tree (p38's `_entity_id` rename leaves it intact). |
| R3 | acceptance | pass | 20 event kinds' payload keys pinned; 1,001-member retained + candidate page tails already pinned by the two `…page_tail` tests. |
| R4 | acceptance | pass | invalid-identity probe: 0 clock reads, 0 `_new_id` calls. |
| R5 | integrity | pass | `.agent/mutate` ×3 at `impl/p42` (tag `archive/p42-credit`): killed 1767 / 1427 / 1809; survivors → p114. |
| R6 | integrity | pass | cherry-pick of `059dab8` conflicted only where both sides appended to `SystemTests`'s end (base empty) → both kept, mine first; class runs 4 OK. |

## p91 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 an ABI pin reports ≥ 1 in-scope `models.py` mutant; R2 its survivors named; R3 the p74 trial pin keeps 131 / 126 / 1. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | scope adds read definition spans (test-caller frames only): `models.py: 0 executed lines + 64 read definition lines` → 27 mutants, 27 killed (per-module tally line added so the count is printed, not inferred). O5 reads git objects, so the live ABI pin carries the check — re-derivation stated in the ledger. |
| R2 | acceptance | pass | 84 survivors listed in `.agent/decisions/p91-mutate.txt` (store 67, system 17); rulings owed → p113. |
| R3 | acceptance | pass | p74 trial pin at `impl/p91`: killed 131, survived 126, invalid 1 of 258. |

## p56 close (MAINTAIN queue run, unit, tier `kernel`, two commits: `35411af` + this) — target = the commit landing this section

Check set: R1 a committed campaign over the migrated assertions + demo verdicts; R2 every named-obligation mutant killed; R3 the three named survive-then-die cases; R4 premise re-derived at HEAD; R5 the oracle can fire and cannot pass vacuously. MAIN alone (advisor consulted on the design).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `p56-strength.py` + `.json` (7 rows) + outputs `p56-strength-{survive,die}.txt` committed. |
| R2 | acceptance | pass | die half at `35411af`: 7/7 killed, each by its named oracle id (`named-oracle=yes` ×7). |
| R3 | acceptance | pass | survive half at `35411af~1`: 7/7 survived the full suite minus D28 (CONTROL OK ran 1314) → die at `35411af`. |
| R4 | correctness | pass | request-id payload pin gone at HEAD → family moved to the empty-payload equality pins (B30, submission D03); battery frozen to `dc4ab5e` → named obligation = the oracle test id; both stated in `35411af`'s body. |
| R5 | integrity | pass | targets pass bare (asserted per row); kills come through the witness (a missing statement leaves no line, so the witness decides); wrong-oracle seed → rc 1. |

## p46 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 one shared engine, each existing validator a schema; R2 old/new identical rc + unfilled count on every artifact; R3 blank seed rc 1, filled control rc 0; R4 harvest integrity. general-purpose-4 built; MAIN reran.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 13 schema modules over `wave_validate.py`; 16 validators out of scope with a stated shape each (`.scratch` deliverable table, restated in the ledger entry). |
| R2 | acceptance | pass | MAIN's rerun of `p46-differential.py --base 02440b8`: 3,274 cases over 34 artifacts, 0 differences (four inherited reds stay red, identical output). |
| R3 | acceptance | pass | 29 blank → filled pairs inside the same run; `--self-test` detects a planted counter deletion (31 differences in the teammate's run). |
| R4 | integrity | pass | 15 files taken from `wt/general-purpose-4` @ `9248747` (no base drift since `02440b8`), sha256-equal to the branch; no test names a touched file; p94 census still rc 0. |

## p98 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 a measured decision (keep → the editor's load + save times on 0.12.3 recorded for the largest file); R2 the published claim matches the measurement. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | keep; largest file 573 / 690 ms medians (5 runs), all four files measured (max save 1,035 ms under gate load 4-9); record + rerunnable driver committed. The "thin files" branch needs no tests since it was not taken. |
| R2 | correctness | fixed | the first README draft said "less than one second"; one save measured 1,035 ms → "about one second". |

## p80 close (MAINTAIN queue run, unit, tier `docs` — PROTOTYPE law) — target = the commit landing this section

Check set (the row's acceptance): R1 reduced motion; R2 390×844 reach; R3 Tab focus ring; R4 contrast ≥ 4.5:1; R5 UI copy ruled against `Decisions`; R6 fixes captured. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | fixed | `.dots span` `pulse` → `none` under `prefers-reduced-motion: reduce` (positive control: `pulse` without it); driver.js already ran `animate: false` there. |
| R2 | acceptance | fixed | story state: a function row's switch sat at 380-423 px (clipped) → `.fn-row` wraps; now 0 off-screen controls, `scrollWidth` 390, both states; frame inspected. |
| R3 | acceptance | pass | Tab stops 13/13 (reset) and 17/17 (story end), each with an outline ring (`:focus-visible` rule already present). |
| R4 | acceptance | pass | 73 (reset) / 360 (`?tech=1` story end) text nodes, 0 pairs below 4.5:1 (blended backgrounds). |
| R5 | acceptance | fixed | errors must state the fix: client fallback `request failed`, `/api/bundle.json` `no verified function to export`, offline `… for this task` → each names the next action (`Reset`, `Learn from chats`); controls, empty states and the technical-details toggle match `Decisions` wording; the `cement · Concept demo` header = p95's open owner question, untouched. |
| R6 | acceptance | pass | `capture.sh` rc 0, 10 frames, duplicate check empty; density 155/155/12 at `?reset=1` (unchanged), 244/244/15 at story end; `quality.mjs` committed so the floor reruns. |

## p79 close (MAINTAIN queue run, unit, tier `docs` — PROTOTYPE law) — target = the commit landing this section

Check set: R1 the three tools drive a browser the prototype installs (one command, `node_modules/` gitignored); R2 the machine-bound grep is rc 1; R3 fresh clone → 10 PNGs + transcript + timings, no duplicate frame; R4 density grade at `?reset=1`; R5 Template rulings (4) retires. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | Playwright 1.64.1 pinned in `package.json` + `pnpm-lock.yaml`; Chromium headless shell lands in `node_modules/.pnpm/…/.local-browsers` (`PLAYWRIGHT_BROWSERS_PATH=0`); the home Playwright cache untouched. |
| R2 | acceptance | pass | rg rc 1 over `prototype/ .claude/rules/ .agent/spec.md`. |
| R3 | acceptance | pass | clone of `f489412`: install, server, `capture.sh` rc 0; 01-09 + story-full-page PNGs, `sha256sum … | uniq -d` empty; frames 01 + 06 inspected. Heights equal the last `webcap` run except 09 (5460 vs 5150 px, each measured by `measure-height.mjs`). |
| R4 | acceptance | pass | 155 / 155 / 12 under both ChromiumFish and the new browser at `?reset=1` (twice each) — no recorded grade existed, so the old toolchain on the same state is the reference. |
| R5 | acceptance | pass | `ops.md` ruling (4) → retired (p79); `prototype.md` names the browser + `browser.mjs`; README `Visual check` rewritten. |

## p11 close (MAINTAIN queue run, row closure at `02440b8`, tier `docs`) — target = the commit landing this section

Check set: R1 zero `reportAttributeAccessIssue` under `uvx pyright tests/test_system.py`; R2 suite green. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | pyright 1.1.414 at `02440b8`: 0 of that rule (44 other-rule diagnostics, listed in the ledger, outside the metric). No narrowing edit was needed: the region the row measured was rewritten by M3. |
| R2 | acceptance | pass | the closing commit's full gate (`tests/test_system.py` unchanged since `af22d57`). |

## p76 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 the census prints every row's working-tree anchor count; R2 count-0 rows carry a verified retired mark (or re-anchor); R3 seeding a fresh count-0 row reds it. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 268 rows over the three catalogues carrying `anchor` + `path`/`file`; one line each. |
| R2 | acceptance | pass | 118 count-0 at HEAD (the row's 26 was measured at the refresh tree); every mark lives in `p76-retired.json` (catalogue schemas and their validators untouched) and is re-verified on each run against `<commit>^` / `<commit>`. Re-anchoring onto surviving loci was not chosen: those units are closed and their harnesses grade the trees they were written for. |
| R3 | integrity | pass | appended seed row → `UNMARKED … P76SEED`, rc 1; wrong-commit mark → `UNVERIFIED`, rc 1; restored → rc 0. |

## p94 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 every instrument's named revisions on `main` or recorded with a restore command; R2 the census exits 1 on an unreachable unrecorded SHA; R3 instruments unchanged in behavior. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 9 recorded `Tag dependency:` lines over 8 instruments: 6 with their tag + fetch command, 3 expired (no ref keeps `3f9a053`, `f87c8a2`, `1880241`; `git for-each-ref --contains` empty) — a restore command cannot exist for those, so the line says so. |
| R2 | integrity | pass | census before the docstring lines: rc 1 (9 `UNREACHABLE`); after: rc 0 (63 on main + 9 recorded). Digest hex (e.g. `m3u5a-s2-probe.py`'s parser-shape digest) is excluded by resolution, a stated limit. |
| R3 | correctness | pass | the 7 patchers' `--check` rc identical before/after; `m3u6a2-dispositions-validate.py` output byte-equal (RESULT: PASS, 0 findings); no test reads these files. |

## p47 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 the branch taken (publish vs expire); R2 every citation marked; R3 both `m3u4-alt-*` diffs tracked + reproducible from the tags here; R4 instruments still pass. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | publishing pushes tags to the remote, which the owner drives → expire + archive. |
| R2 | acceptance | pass | `git grep` over the five tag names (minus `m3u4-map.json` file names): 5 citing files outside the row texts, each with the `Expired (p47)` sentence or the corrected reason. |
| R3 | acceptance | pass | diffs = `git diff <parent> <tag>` here (stats equal the contract's +433/-147, +181/-117); bases are spike-branch commits, so each diff is self-contained; gitleaks dir clean. |
| R4 | correctness | pass | `m3u4-archive-validate.py` RESULT: PASS; markers appended at file ends (no line-anchored content moves); deferred grader PASS. |

## p38 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 one `_entity_id(value, label)` owner; R2 every caller supplies its entity; R3 CLI + library messages update together; R4 request-lifecycle vocabulary absent; R5 pins the rename moves. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `_request_id` + `_REQUEST_ID` → `_entity_id` + `_ENTITY_ID`; grammar unchanged (bounded ASCII, 192 chars). |
| R2 | acceptance | pass | 22 call sites, labels per parameter/stored column; stored-row reads keep their `IntegrityError` translation (the label only reaches `__cause__`). |
| R3 | acceptance | pass | the CLI has no copy of the grammar; `function export --receipt-id` bad values now print `receipt_id must be a bounded ASCII identifier` (test red at the unfixed source). |
| R4 | acceptance | pass | `rg request_id src/` rc 1; the requests-residue battery's survivor set drops the retired message, so a reappearance reds it. |
| R5 | correctness | pass | pin edits named: `test_function_export_bounds_the_receipt_id_grammar` message (re-targeted), `RequestsResidueBattery.test_s4_no_requests_table_and_no_query_names_one` survivors (one entry fewer = stricter), a `test_cli.py` comment. |

## p10 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 each of the 14 cited inputs inlined or marked expired, the 3 deleted included; R2 no tracked file presents a `.scratch/` path as retrievable; R3 the check fires. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | seven records' inputs: 11 present on this machine only → marked machine-local (each record already states the arbitration it drew from them); `m2u3b1.patch` + `main-verify/{tree,f1probe.py}` → `deleted` in place. Rescue by archiving the raw spike reports was weighed and declined: ≈ 0.5 MB of superseded agent drafts would enter every repo search, while the records hold the decisions. |
| R2 | acceptance | pass | census over `git grep -F .scratch/` at this commit: 167 citations = 10 operational (conventions + capture output, reasons in the script) + 47 history/queue + 12 JSON (marked in the census) + 98 in marked files; 0 unmarked. |
| R3 | integrity | pass | before the markers: rc 1, 84 `UNMARKED` lines over 13 files; after: rc 0. |

## p23 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 a child-process audit hook proves `function eval` opens no database file and no connection; R2 the probe can fire (control); R3 every offline claim states any `python -S` audit-hook gap; R4 preservation credit. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | probe runs `function eval` (A03 hit rc 0, C01 miss rc 6) through `python -c` with the hook installed before `cement_runtime` loads: 0 `sqlite3.connect`, no file open in the ledger directory other than the bundle. |
| R2 | integrity | pass | control: the same probe over `function export` records `sqlite3.connect` on the ledger's `file:` URI; positive control: the bundle `open` is recorded for each eval. |
| R3 | acceptance | pass | the hook is the child's own program, not `sitecustomize`, so `python -S` leaves no gap; residual coverage (startup before the hook, access outside Python audit events) stated once at the precise ledger-free claim (README `Deployment boundary`) and referenced from `docs/threat-model.md`'s offline bullet; the other offline sentences (README quick start + API table, architecture, example README) carry no gap to state. register-audit rc 0, article-audit 0 ungrounded. |
| R4 | integrity | pass | `.agent/mutate` at `impl/p23` (tag `archive/p23-credit`): killed 2182 / survived 1483 / invalid 92 of 3757; survivors unruled → p112. |

## p78 close (MAINTAIN queue run, row closure at `1935f68`, tier `kernel`) — target = the commit landing this section

Check set: R1 the acceptance met at `1935f68` holds on recheck; R2 planted red reds twice, store unchanged; R3 the kept assertions. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `1935f68` + records `2d84f3b`: cold 2274.1 s / 12 replays → warm 306.1 s / 1 replay on one tree; this session's warm D28 = 143.1 s and 340.9 s at 1 replay. Cold not re-measured (≈ 61 replays now). |
| R2 | acceptance | pass | throwaway `099c9a7` on `c323edd` (one failing test in `tests/`): run 1 + run 2 both rc 1, `1 replayed, 60 from green verdicts`, failing revision = `099c9a7`; store listing 87 entries, digest `911f79d12d20836b` before = after. |
| R3 | acceptance | pass | `tests/test_migration_battery.py`: `assertTrue(revisions, …)` + `assertGreaterEqual(ran, 949)` on a replay + `assertGreaterEqual(verdict[0], 949)` on a served verdict. |

## p03 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 §G audits every site + nullability; R2 public paths reject non-int stored integers; R3 numeric-text receipt probe expects `IntegrityError`; R4 fabricated / schema-rewrite probes labelled non-real-ledger; R5 existing pins the change moves; R6 paste-ins regenerated. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | census script → §G table: 91 sites (79 exact, 4 pre-checked, 7 in-memory, 1 driver, 0 UNGUARDED); graded both ways: pre-fix source 62 UNGUARDED rc 1, fixed rc 0. Nullability from `store.SCHEMA`; surfaces from the AST call graph. |
| R2 | acceptance | pass | 57 conversions → `_stored_int` (56 UNGUARDED + 1 pre-checked) with schema CHECK minima (revision/sequence 1, support 2, reviewer_count 1, test_count 1, passed ≤ 1, timestamps 0 — clock values are validated ≥ 0 at write); receipts: exact-type check before the existing range messages. |
| R3 | acceptance | pass | probe covers `function_receipts` sequence / operation_revision / member_count / promoted_at_us beside 10 other public paths; red at the unfixed source (36 of 37 subtests; `artifact`/`operation_revision` already raised). |
| R4 | acceptance | pass | probe comment: FABRICATED (STRICT tables cannot hold numeric text); the NULL probe rewrites the schema and stays so labelled. |
| R5 | correctness | fixed | `test_function_report_translates_null_persisted_projection_scalars`: its two message pins (`^operation artifact row is invalid:`, `^current build projection is invalid:`) wrapped a raw `TypeError`; `_stored_int` now raises the field's own `IntegrityError` → re-targeted to `^stored report passed is invalid$` + `^stored example confirmed_at_us is invalid$` (class kept, anchored + exact; standing pin-repair approval); the prefixes stay live for other `TypeError`/`ValueError`. |
| R6 | acceptance | pass | `examples/open_webui/generate.py` rerun; paste-in battery green. |

## p15 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 each of the 28 probes mapped to a subsuming shipped test or merged; R2 merged count recorded; R3 scratch suite removed; R4 the merged probes earn preservation credit; R5 the map's anchors resolve in the landed tree. MAIN + general-purpose-1 (map author).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/decisions/p15-map.md`: 17 subsumed (shipped ids per row), 8 gap (ported), 3 obsolete (retired grammar: export leaf order, `--out` now the atomic-file channel); verdict counts recounted from the table (17/8/3 of 28). |
| R2 | acceptance | pass | merged = 8 `tests.test_cli.CLITests.test_function_export_*` tests (cherry-picked from `48fe736`, conflict-free); fast gate test_cli + lifecycle_removal + authority_removal Ran 284 OK. |
| R3 | acceptance | pass | `.scratch/agents/test-m2u4c5a-suite.py` deleted (machine-local, untracked). |
| R4 | integrity | pass | 8 `.agent/mutate` runs at `impl/p15` (tag `archive/p15-credit`), all rc 0: killed 9716 / survived 7594 / invalid 410 summed; survivors unruled → p111. |
| R5 | correctness | fixed | the map's anchors were written against `809e779` (52/52 resolve there; 8/52 at `48fe736`) → re-anchored by exact-line difflib map to the landed tree, 0 misses; `.agent/validate-anchors` rc 0. |

## p61 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 runner + output committed; R2 each pre-battery verdict in a dedicated field, never `note`; R3 the contract states how many rows the pre-existing suite already catches; R4 the output cannot drift from its transcript unseen. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/decisions/p61-prebattery.py` + `.txt` transcript + `.json`; the transcript = the pool run of the identical argv at `dc4ab5e` (`uv run python -u .agent/decisions/m3u6a1-mutants.py --verdict ×4`, rc 1 by construction: every row expects `killed`); the runner's fresh-sweep path was not executed end to end here (hours serially) — `--from-log` + `--check` were. |
| R2 | acceptance | pass | field `pre_battery` ∈ {`battery_sole_killer`, `old_suite_kills`} + `old_suite_killers`; catalogue `note` untouched; ids/obligation/kind cross-checked against `dc4ab5e:.agent/decisions/m3u6a1-mutants.json`. |
| R3 | acceptance | pass | contract §16: 50/92 already killed by the old suite (33 reversion, 17 sensitivity); battery sole killer of 42 (20 + 22); seven `contract-claims` rows graded against the committed JSON. |
| R4 | correctness | pass | `--check` PASS; drift seed (pre_battery rewritten) rc 1; red-control seed (`CONTROL: RED`) aborts before writing. |

## p25 probe repair (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 root cause of the gate red at `5b4e947` (`test_an_interrupt_exits_130_with_a_json_error_and_no_traceback`: `4 != 130`, 10.135 s) proven by experiment; R2 the probe holds in every launch mode; R3 README `## Outcomes` states the inherited-ignore case. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | fixed | not a race: an inherited SIG_IGN (`trap '' INT`, or an `&` job of `bash -c`) keeps SIGINT ignored in the child (Python installs `default_int_handler` only over SIG_DFL) ⇒ the lock wait times out → StateError → exit 4; unmodified probe at `929c7e3`: default OK, `trap '' INT` FAIL `4 != 130` (10.126 s), `&` FAIL (10.139 s). |
| R2 | acceptance | pass | probe installs `signal.default_int_handler` first; default / `trap '' INT` / `&` = OK 10.175 / 10.171 / 10.176 s. |
| R3 | acceptance | pass | README sentence: a process started with SIGINT ignored ignores the interrupt, the lock wait ends with exit 4 after 10 s; register-audit rc 0, article-audit 0 ungrounded. Law → `.claude/rules/runtime.md` (behavior) + `history-gates.md` (launch the gate at SIG_DFL: revisions `21b7463`.. keep the old probe for cold D28 replays). |

## p44 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 one setter per pair, pinned by readback; R2 the `hasattr(setconfig)` guard reassessed against `requires-python`; R3 B6 updated. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | busy timeout = `connect(timeout=10.0)`; trusted_schema = the PRAGMA; B5 readbacks 10000 / 0 green. |
| R2 | acceptance | pass | kept: Python 3.11 lacks `Connection.setconfig`; DEFENSIVE applies on 3.12+. |
| R3 | acceptance | pass | B6 pragma list (4), setconfig list (DEFENSIVE), authorizer-last sequence updated; `tests.test_read_capability_battery` 49 + paste-in OK. |
| R4 | correctness | fixed | full gate at the first p44 tree red on B35 (`test_b35_y11_statement_cardinality_one_statement_per_1` ×4 paths, `_per_2` ×3 decisions): its TOTAL statement counts included the removed `PRAGMA busy_timeout`; application + request counts unchanged ⇒ each total −1 (B35 not named by the row; a direct consequence of its removal); `tests.test_proposal_binding_battery` 55 OK. |

## p84 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 `docs/architecture.md` names, per proof, what it binds, what makes it stale and whether it gates promotion; R2 `.agent/review.md`'s preamble uses the same three names. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `## Stability and verification claims`: reviewer's opinion (example + receipt hash; stale on revoke/supersede; one confirmation, gates nothing alone), replay verdict (artifact/build/policy hash + evidence snapshot; stale on evidence or revision change; promotion requires a passing one), promotion receipt (function hash + entry seals; a true record; gates nothing, each call re-checks the selected version). Claims checked against `_validate_report` bindings + promote's passing-report rule. |
| R2 | acceptance | pass | review preamble: a pass here is a reviewer's opinion, neither a replay verdict nor a promotion receipt. |

## p45 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 one 64-hex predicate in `system.py`; R2 each replaced site keeps its message + raise/verdict behavior; R3 suite green (gate). MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `command grep -c '\[0-9a-f\]{64}' src/cement_runtime/system.py` → 1 (`_is_digest`). |
| R2 | acceptance | pass | `_digest` (ValidationError `{label} must be …`), `verify_function` precheck (`expected_function_hash must be …`), `promote` (`scope_hash must be …`), `_validate_report` (IntegrityError `… test set digest is invalid`): each keeps its class, message and its type check (`_is_digest` includes `type(value) is str`; the report site still stringifies first). |
| R3 | regression | pass | full gate at the landing commit. |

## p82 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 the README names the Ctrl+C-only cleanup (the row's documented option). MAIN alone; prototype law (no suite owed).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `prototype/webui-demo/README.md`: Ctrl+C removes the temporary ledger; a `SIGTERM`-stopped server leaves its `cement-demo-*` directory, to remove by hand. |

## p24 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 the arm is documented as deliberate breadth over schema-fixed inputs, with no claim of a real-ledger repro. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | comment at `_verify_row`'s `except (IntegrityError, ValidationError)`: callees normalize reachable failures to `IntegrityError`; the `ValidationError` breadth keeps a value-shape failure a failed report. No test added (the documented option). |

## pri-4 owner-gated rows (MAINTAIN queue run, owed / waiting) — target = the commit landing this section

Check set: R1 each row names what it owes or the trigger it waits on. MAIN alone; no code.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| p34 p37 p87 p88 p89 p90 | scope | owed | owner's scope-expansion disposition (`Decisions` `Dispositions`). |
| p73 p75 p83 p86 | scope | owed | each acceptance opens on an owner ruling. |
| p92 | gate | owed | widening the `register` step = a gate change (owner approval). |
| p52 | trigger | waiting | binds only when a map row is about to become a durable claim. |
| p99-p102 p104-p110 | verification integrity | owed | per-survivor non-author rulings at 77-1,689 survivors a row = the open survivor-scale question. |

## p93 + p95 (MAINTAIN queue run, owed) — target = the commit landing this section

Check set: R1 each row's remaining part needs the owner, named on the row. MAIN alone; no code.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| p93 | scope | owed | per-survivor non-author rulings at 160-1,700 survivors a pin = the open survivor-scale question (p99-p110). |
| p95 | scope | owed | the acceptance is an owner ruling on the prototype header vs the `Decisions` presentation rule. |

## p60 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 a committed checker reads every count-bearing contract line and resolves it against the named committed artifact, nonzero on divergence; R2 seeded both ways; R3 the shipped contract exits 0; R4 teammate output re-derived. MAIN + general-purpose-2.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/contract-claims`: coverage = every prose line holding a backticked token + an integer; each needs a fenced `claims` row (`count` / `lines` / `json` over `<rev>:<path>`, or `unchecked` + reason), anchored by line + fragment. |
| R2 | acceptance | pass | fixtures: good rc 0; wrong count → `MISMATCH`; unclaimed → `UNCLAIMED`; moved fragment → `STALE`. |
| R3 | acceptance | pass | `m3u6a1-contract.md` §15 (append-only, +7,702 bytes): 44 lines, 50 graded rows all matching at their historical revisions, 20 `unchecked` (context-gauge figures, identifiers, historical runs) → rc 0. |
| R4 | verification integrity | pass | MAIN reran the validator (rc 0), proved the edit byte-append-only, read every `unchecked` reason; finding recorded: the contract cites `m3u6a1-verdicts.json`, absent at `dc4ab5e` (L557, L761 stay `unchecked`). |

## p96 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the CLI skill's step 1 carries the recovery rule (exact + support 1 → the projection decision); R2 a CLI read surface derives a candidate program (one layout per distinct `projection.structure`), with a test that two notes of one layout group into one case; R3 the skill + workflow text pins move with it (X3, LP0d hold); R4 replaying the L1 state through the CLI skill reaches a published version; R5 one owner for the derivation. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `skills/cement-learn/SKILL.md` step 1: `nothing_to_learn` + `grouped_by` `exact` + a support-1 case → step 2. |
| R2 | acceptance | pass | `cement learn cases OPERATION --projectable` (exclusive with `--program`) → `program` + grouping; `test_two_notes_of_one_layout_group_into_one_case`: exact = 2 cases at support 1, derived = 1 case at support 2, program = one layout. |
| R3 | acceptance | pass | step 2 + `references/projection.md` + `references/workflow.md` derive instead of hand-writing; X3 + LP0d phrases kept (both green). |
| R4 | acceptance | pass | `test_the_l1_state_replays_through_the_cli_skill_to_a_published_version`: 5 exact support-1 answers → recovery → derive → merge (supersede the extended example) → projection test/set → compile/verify/inspect/promote → 1 version, 2 members, lab at support 1, switch off. Red at `e2082d7`. |
| R5 | cleanup | pass | `draft_program` moved from the Open WebUI tool into `cement_runtime.projection` (outside `__all__`: the contract API pin keeps its seven names); the tool imports it; paste-ins regenerated. |

## p41 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 a blocking clock vs a second default writer, outcome asserted; R2 a re-entrant clock through another `System`, outcome asserted; R3 measured lock duration recorded beside the ruling; R4 credit recorded. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_verify_drafts_holds_the_write_lock_while_a_blocking_clock_runs`: the second writer is still waiting after 0.5 s, finishes after the verify commits, both succeed. |
| R2 | acceptance | pass | `test_promote_function_rolls_back_when_its_clock_reenters_the_ledger`: `StateError("database is busy or unavailable")`, one clock call, ledger dump unchanged. |
| R3 | acceptance | pass | `.claude/rules/runtime.md`: a 1.0 s hold → the second writer waited 1.050 s; re-entry → StateError after 10.07 s (busy timeout). |
| R4 | verification integrity | open → p110 | 963/1251 killed (`.agent/decisions/p41-mutate.txt`). |

## p67 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 one read-only leaf prints the promoted set as a guarded-branch listing with, per case, the confirmed proposals behind it (original `proposed_output` beside the change); R2 case values come from the rebuilt bundle, not a second ledger projection; R3 `--json` keeps the machine surface, both branches pinned; R4 two originals print both, none prints the case and names the absence, an empty set exits 3; R5 no grading check moves except the documented digest re-pin; R6 surface wording (advisor). MAIN + advisor.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `cement function read OPERATION`: one `if case == …:` / `answer …` branch per case, each proposal as `# proposal <id>: proposed <out>, accepted | corrected to <out>`, supersession walked back to the original proposal, `otherwise: ask the LLM` tail. |
| R2 | acceptance | pass | values from `reconstruct_function_receipt`'s document; originals via `function_report` members → artifact `evidence_ids` → review events → `proposal`, all public reads (B20's read-site set unchanged). |
| R3 | acceptance | pass | `test_function_read_lists_each_case_with_the_proposals_behind_it` pins the JSON fields + order and the text lines. |
| R4 | acceptance | pass | x1: 2 proposals in arrival order; x3 (rebuilt from 2 challenges): `from a challenge, no proposal` ×2; `test_function_read_exits_3_without_a_promoted_version` rc 3 both branches; overflow past the member projection named (`_LISTING_MEMBERS` test). |
| R5 | gate safety | pass | `ParserShapeTests.SHAPE` (218 → 224 rows) re-pinned as its docstring prescribes for a deliberate grammar change; census batteries + `test_cli` 487 OK; tripwires PASS; register + article audits rc 0. |
| R6 | surface | finding, fixed | advisor: proposal order was evidence order (nondeterministic) → arrival order; header + tail wording aligned with the ruled `Read` view (`seals … runs no code`, `ask the LLM`); over-limit branch tested. |

## p71 + p72 close (MAINTAIN queue run, closures, tier `docs`) — target = the commit landing this section

Check set: each row's acceptance rerun at HEAD. MAIN alone; no change.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| p71 | acceptance | pass | `rg -F 'a8109eb' .agent/spec.md` → rc 1; `Phase` = `MAINTAIN — whole product`, naming no gate baseline. Met at `e4e7016`. |
| p72 | acceptance | pass | `rg -F -e 'Shipped for (' -e 'no longer eyeballed' .agent/spec.md` → rc 1; each paragraph of `e4e7016^:.agent/spec.md` (`Shipped for (2)`-(5) + `Capture heights are no longer eyeballed`) occurs byte-verbatim in `.agent/archive/iterate-rounds.md`. Met at `e4e7016`. |

## p54 + p85 close (MAINTAIN queue run, closures, tier `docs` / `kernel`) — target = the commit landing this section

Check set: each row's acceptance rerun at HEAD with its seed. MAIN alone; no change.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| p54 | acceptance (relocated doc) | pass | `docs/adapter-protocol.md` relocated to `examples/command_source/README.md` (M3.7); R5 (`tests.test_relocation_battery`) runs its one Python block (the bundled `example_adapter.py` through `source.propose`), asserts the stated echo and requires every operator-facing module named; seed `example_adapter` → `stub_adapter` in that README → R5 fails naming `example_adapter.py`. Met at `635a473`. |
| p85 | acceptance | pass | `.agent/skip-census`: each allowlist member carries a reason class (`platform` ×2, `replay-pruned` ×1), printed per hit; a seeded skip outside the allowlist prints `UNLISTED` and fails rc 1. Met at `629577d`. |

## p28 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section (pins landed in `286b014`)

Check set: R1 outer-rehashed malformed values make all four `function.py` digest fields raise `ValidationError`; R2 altered `build_function` results fail `function-hash-matches-snapshot` with field-specific detail (complete vector asserted); R3 all nine deletion mutants die, by a committed catalogue rerun from a clean checkout; R4 the M2 premise re-derived at HEAD; R5 credit recorded. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_entry_digest_syntax_rejects_after_outer_rehash`: uppercased digest + rehash → `^function entry 0 <field> must be a SHA-256 hex digest$` for each of the four. |
| R2 | acceptance (re-derived) | pass | `test_function_verification_pins_each_projected_document_field`: vector (T,T,T,T,F,F,T) + per-field hash detail + the receipt check's derivative detail (the receipt rebuild calls the same patched constructor; the row's "only" predates that check). |
| R3 | acceptance | pass | `.agent/decisions/p28-mutants.jsonl` (base `286b014`, generator `p28-catalogue.py`) → `replay-mutants`: CONTROL green, 9/9 killed, all restored, rc 0. |
| R4 | claim soundness | recorded | at `b937a3b` (pins absent) the whole suite minus D28 already killed 9/9: the M2 premise expired; the pins still owe the acceptance's specific assertions. |
| R5 | verification integrity | open → p109 | 263/1678 killed, 161/1185 survived (`.agent/decisions/p28-mutate.txt`). |

## p29 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the shipped `FUNCTION_MAX_ITEMS` is driven at exactly 1,000,000 (accepted) and 1,000,001 (rejected), build + parse; R2 the patched-limit fixtures stay; R3 "marked-slow" re-derived; R4 credit recorded. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_the_real_item_bound_accepts_one_million_and_rejects_one_more`: an 11-entry bundle at exactly `FUNCTION_MAX_ITEMS` validates + parses byte-identical; one more item rejected at build and at parse (`JSON exceeds maximum container item count`). |
| R2 | acceptance | pass | the patched-limit fixtures in `FunctionTests` are unchanged. |
| R3 | acceptance (re-derived) | pass | this unittest suite has no slow marker; a marker = a conditional skip, and the skip set is closed at three (owner approval) ⇒ the pin runs in the default suite (≈ 3-6 s measured). |
| R4 | verification integrity | open → p108 | killed 323 / survived 170 of 493 (`.agent/decisions/p29-mutate.txt`). |

## p26 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 adjacent 256/257-byte + printable/control `--actor` pairs pin exit 0 vs invalid/2 with rejected stdout empty; R2 the accepted boundary value persists in the verification report; R3 credit recorded, survivors routed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_function_verify_drafts_actor_bounds_are_adjacent_pairs`: `é`×128+`a` (257 B) + BEL → rc 2, stdout empty, `verified_by must be control-free and at most 256 UTF-8 bytes`; `é`×128 (256 B) + `verifier` → rc 0. |
| R2 | acceptance | pass | the accepted 256-byte value = the `artifact.verified` event's `verified_by` and the report's `details.verified_by`. |
| R3 | verification integrity | open → p107 | killed 1307 / survived 1026 / invalid 70 of 2403 (`.agent/decisions/p26-mutate.txt`). |

## p59 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 both D15 halves name ONE source; R2 the chosen branch is reddened by its own seed; R3 the unchanged half stays green. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance (re-derived) | pass | since `ffe9848` (M3.6a2) `MigrationBatteryTests.setUpClass` binds `cls.root` to a detached worktree at `M3U6A1_TIP`, so `repaired / SURGERY` and `_copy_surgery(self.root, …)` both read the script committed at `dc4ab5e`; the docstring now states that one source. |
| R2 | acceptance | pass | throwaway commit `337506d` (= `dc4ab5e` + the script printing `applied: seed` where it owes `no-op`) with `M3U6A1_TIP` pointed at it → D15 red: `'no-op' not found in 'applied: seed\n'`. A working-tree seed leaves D15 green by design (closed-transition frame). |
| R3 | regression | pass | unpatched → D15 green. |

## p49 (MAINTAIN queue run, owed) — target = the commit landing this section

Check set: R1 the acceptance's grammar change is compatible with the standing pins. MAIN alone; no code.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | gate safety | owed | X23 (`tests/test_cli_channels.py`) + the channel battery's shared-path abbreviation map deliberately pin legacy abbreviation as accepted (M3.5a); a global `allow_abbrev=False` breaks the public CLI and inverts both ⇒ owner ruling. |

## p43 (MAINTAIN queue run, owed) — target = the commit landing this section

Check set: R1 the acceptance's classification inputs (error code + Store-owned provenance) can separate `VACUUM` from every other statement whose mapping a standing pin fixes. MAIN alone; no code.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | feasibility | owed | `VACUUM` in a transaction and `SELECT FROM schema_metadata` both raise `sqlite_errorcode` 1 (`SQLITE_ERROR`); B14 pins the malformed read to `StateError` ⇒ a code-based remap moves both B11 and B14 = a grading-check change for the owner. |

## p35 + p36 (MAINTAIN queue run, owed) — target = the commit landing this section

Check set: R1 each row's funding is blocked by a binding ruling, named on the row. MAIN alone; no code.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| p35 | scope | owed | `Decisions`: `resolve` pays full verification per call, no cache; `Dispositions`: p34-p37 = scope expansion queued with reasons. |
| p36 | scope | owed | `Dispositions` (p34-p37 scope expansion) + `Decisions`: ambiguity quarantine left with `handle`. |

## p18 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 one CLI probe per shape (empty, boundary accepted, boundary+1 rejected, illegal character) with exit + mapped message; R2 the accepted boundary value is read back from the promotion receipt; R3 credit recorded, survivors routed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_function_promote_actor_bounds_are_adjacent_byte_pairs`: `""` → `promoted_by must be non-empty text`; `é`×128+`a` (257 bytes), BEL, U+200B → `promoted_by must be control-free and at most 256 UTF-8 bytes`; each rc 2, stdout empty, no receipt written. |
| R2 | acceptance | pass | `é`×128 (256 bytes) → rc 0; `function receipts` → `promoted_by` = that value. |
| R3 | verification integrity | open → p106 | killed 1662 / survived 1260 / invalid 70 of 2992 (`.agent/decisions/p18-mutate.txt`). |

## p32 + p33 plan review (MAINTAIN queue run, partial, tier `kernel`) — target = the commit landing this section

Check set (the plan's own): A policy family, B bound-report family, C FunctionEntry construction, D decomposition, V verification, Q1-Q3. Reviewer = `consultant-1` (consultant), table `.agent/decisions/p32-plan-review.md`; MAIN re-verified each decisive anchor.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| D | gate safety | finding, owed | B20 `tests/test_read_capability_battery.py:883` `self.assertEqual(reached_helpers, expected_helpers)` over an exact 24-name set ⇒ any read-reachable extracted helper reds it; extending the set = a grading-check change ⇒ owner ruling, recorded on p32. |
| B | completeness | finding, recorded | six bound-report owners, not four (+ `promote` `:5222`, `_validate_promoted` `:6321`); member-binding family missing — recorded on p32 as design input. |
| V | verification | finding, recorded | literal census ≠ equivalence; behavioral differential over compound defects recorded on p32. |
| R | rules accuracy | finding, fixed | `.claude/rules/runtime.md` said over-capacity returns "all six checks FALSE"; `system.py:3076-3082` returns seven ⇒ fixed to seven. |
| Q1-Q3, A, C | design | pass / recorded | per-caller message maps = one owner per predicate; p33 closes `closed=<p32 sha>` after its own census; C sound. |

## p39 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 each S3 KEEP row + source-docstring row carries a disposition + falsifier at HEAD; R2 a deterministic check rejects callback/runtime ACCESS-CONTROL ATTRIBUTION (not merely unclassified tokens); R3 each check is seen firing on planted text; R4 credit status stated. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/decisions/p39-dispositions.md`: S3-001 DELETE (superseded by the M3.9a README rewrite), S3-004/005 KEEP, S1-009/010/138 REWRITE→KEEP, each with falsifier + pin. |
| R2 | acceptance | pass | `test_no_surface_attributes_access_control_to_cement`: sentence-level subject × access-verb × no-negation over README, `docs/*.md`, `examples/*/README.md` + every `src` docstring; in-test seeds both ways (2 flagged, 2 clean); 0 hits at HEAD. |
| R3 | verification integrity | pass | planted `The runtime authorizes every reviewer before it records a review.` in `docs/architecture.md` → that test fails naming it; `recorded assertions` → `kept` in README → the presence test fails naming the S3-005 claim. |
| R4 | verification integrity | pass (limit recorded) | both pins read prose (README + docstrings) and execute no `src` line ⇒ `.agent/mutate` scope = 0 mutants (p91's class); credit = the planted-text controls above. |

## p70 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 `.claude/rules/ops.md` names D28's per-revision 600 s limit as load-sensitive with both measurements; R2 a change to the limit is bound to an owner-approved unit recording this firing. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | ops.md Env/gate bullet: `timeout=600` at `tests/test_migration_battery.py:1639` (the D28 inner replay), `ffe9848` TimeoutExpired at load 8.7-11 vs 379.1 s alone at load 4.8-6.0 (63%; recurrences to 88%). |
| R2 | acceptance | pass | same sentence: a TimeoutExpired is load until a quiet rerun reproduces it; a limit change = an owner-approved gate change recording this firing. |

## p66 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 a committed census enumerates every `skipTest` call + `skip*` decorator under `tests/` and EQUALS a three-member allowlist with each condition; R2 it excludes itself + prints every unmatched hit; R3 a seeded fourth skip reds it naming the test id; the shipped tree exits 0. MAIN alone; no change (acceptance met at `629577d`).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/skip-census` (gate step `skips` since `629577d`): `32 modules, 3 skip sites, 3 allowed`, each printed with its condition + reason class. |
| R2 | acceptance | pass | the census lives in `.agent/`, outside its `tests/` domain; every hit printed, an unlisted one tagged `UNLISTED`. |
| R3 | acceptance | pass | seeded `SeededSkip.test_seed` (`self.skipTest("seed")`) in a disposable worktree → `UNLISTED tests/test_json_value.py::SeededSkip.test_seed`, `FAIL (unlisted 1, missing 0)`, rc 1. |

## p40 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 the tracked register tool runs from the configured gate over every human-facing surface; R2 zero filler hits, sentence length reported and never capped; R3 a filler seed reds it. MAIN alone; no change (acceptance met at `629577d`).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `.agent/gate` step `register` = `.agent/register-audit --gate` over `README.md` + `docs/*.md` + `examples/*/README.md` (`git ls-files`); present since `629577d`. |
| R2 | acceptance | pass | rerun at `ee7ce62`: rc 0, `filler 0` per file, longest sentence printed (30 words, open_webui README), never graded. |
| R3 | acceptance | pass | seed `Run the command simply to start.` appended to `docs/architecture.md` in a disposable worktree → rc 1 `FILLER docs/architecture.md:281: simply`. |

## p65 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the unfilled test matches the stub's SHAPE (a cell that IS the placeholder), not a substring; R2 a row quoting the token in backticks grades clean (was red); R3 `--emit-stub` output still grades nonzero through the unfilled check; R4 every other seed fires as before; R5 the seed record names both new seeds. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `unfilled(parts)`: head before `Accept:`, the acceptance text, or a whole continuation line (`- ` stripped) equal to `unknown`/`unknown.` (case-folded). |
| R2 | acceptance | pass | seed `quoted-token-in-backticks` at `21b7463`: pre-p65 grader rc 1 `UNKNOWN-ROWS: 1` (p62), this grader rc 0. |
| R3 | acceptance | pass | seed `emit-stub-grades-nonzero`: rc 1 `UNKNOWN-ROWS: 61` (+ `MISSING: 44`) before and after. |
| R4 | regression | pass | the other 18 seeds: identical rc + decisive line before/after (the foreign-commit SHA alone varies). |
| R5 | acceptance | pass | `.claude/rules/gate-checks.md` grader bullet re-recorded at `21b7463` with both seeds; the stale `p99` never-queued seed moved to `p990` (p99 is a live born row). |

## p62 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 `examples()` rows carry `input_hash` + `output_hash` equal to the compiler's stored values; R2 each consumer that recomputed them stops; R3 the paste-ins embed the changed library (generator freshness); R4 the prototype's evidence view is unchanged. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_example_rows_carry_the_compiler_s_input_and_output_digests`: each row's pair = `canonicalize(...)` digests = the compiled artifact's stored pair; red at `972ba2e` (`KeyError: 'input_hash'`). |
| R2 | acceptance (re-derived) | pass | `run_demo.py` held no such helper at HEAD; `prototype/webui-demo/demo.py`'s `examples()` consumer uses the stored digests, while `_digest` stays for values not yet in the ledger (`:421`, `:1005`, `:1238`). |
| R3 | correctness | pass | `tests.test_open_webui_paste_in` W1 (paste-ins = generator output) green with the regenerated files. |
| R4 | correctness | pass | Prototype driven headless (every request twice, `fast=True`, then `learn`): `_evidence()` before vs after = equal after masking per-run example ids (9 groups, 40 entries). |

## p31 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 every repo-local `TemporaryDirectory` fixture under `tests/` allocates in the system temp dir; R2 a deliberately interrupted run leaves `git status` clean (measured at the landing tree); R3 no frame depended on a repo-local temp path (full gate). MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | finding, fixed | The prepared tip converted the 8 `dir="."` sites but missed 10 `dir=ROOT` sites in `tests/test_lifecycle_removal_battery.py` (same leftover class); all converted. `rg 'TemporaryDirectory\(dir' tests/ examples/` → none. |
| R2 | acceptance | pass | SIGKILL 6 s into `tests.test_cli` + `tests.test_lifecycle_removal_battery`: base `main` → plain `git status` shows `?? tmpk5camqhd/` (+ ignored `cli.db`); this tree → 0 `tmp*` entries in `git status --porcelain --ignored`. |
| R3 | correctness | pass | Full gate at the landing commit (suite incl. L29 tripwire self-test + D28). |

## p27 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the export path fsyncs the destination's directory after `os.replace`, and one probe pins the call order; R2 the durability claim is stated once where export durability is claimed; R3 the new failure window (flush failure after the rename) is published + pinned (runtime.md commit-then-raise law). MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_function_export_out_flushes_the_directory_after_the_rename`: events = `[replace(target), fsync(directory)]`; red at `286b014` (no directory fsync). |
| R2 | acceptance | pass | `docs/threat-model.md` export bullet: a completed export survives a power loss; README claims atomicity only. |
| R3 | claim soundness | finding, fixed | The prepared change left a directory-flush failure unpublished: exit 2 `export output could not be written safely` while the destination already holds the new bundle. Threat model states it; `test_function_export_out_reports_a_failed_directory_flush_after_the_rename` pins rc 2 + stdout empty + the destination's bytes = the bundle; red at `286b014` (`0 != 2`). |

## p25 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 a committed blocked-database SIGINT probe pins the chosen status + no traceback; R2 the probe's write is real (no-commit claim non-vacuous); R3 README states the interrupt contract once, incl. the lock-wait latency; R4 `main` stays embeddable (host keeps `KeyboardInterrupt`); R5 runtime.md residue retired + law added. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `test_an_interrupt_exits_130_with_a_json_error_and_no_traceback`: rc 130, stdout empty, stderr = the exact JSON, no `Traceback`; red at `286b014` (`-2 != 130`). |
| R2 | correctness | finding, fixed | Prepared probe revised an UNREGISTERED operation, so `operations == []` held with or without the interrupt; now `echo` is registered, revision stays 1 after the interrupt and becomes 2 under the same command uninterrupted (control). |
| R3 | acceptance + claim soundness | finding, fixed | SIGINT during the lock wait lands only when SQLite's busy wait returns (measured 9.86 s); README now says so beside exit 130. |
| R4 | correctness | pass | `entry` wraps `main`; `__main__` + `[project.scripts]` route through it; a host calling `main` receives the exception. |
| R5 | portability | finding, fixed | Readiness via a `/proc/<pid>/fd` poll errored (not skipped) on `/proc`-less hosts; now an audit hook in the child's `-c` program marks `sqlite3.connect`. |

## p20 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 the model stated once in normative prose; R2 the existing pin asserts exactly +1 report / +1 event per failed run and cites the doc. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `docs/architecture.md` item 8; register + article audits rc 0. |
| R2 | acceptance | pass | `second_counts == (first[0] + 1, first[1] + 1)` in the cited test. |

## p14 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the chosen option (documented limit) is stated once in human-facing prose; R2 a custom buffered stream pins the no-flush behavior; R3 the closed-pipe claim measured (exit 120 + notice); R4 credit recorded, survivors routed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | README `## Outcomes` paragraph; register audit rc 0. |
| R2 | acceptance | pass | raw stream empty after `main` returns; JSON after the host's flush. |
| R3 | acceptance | pass | read end closed before spawn → rc 120 + `BrokenPipeError` (manual probe and the pin). |
| R4 | verification integrity | open → p105 | 217 / 89 killed (`.agent/decisions/p14-mutate.txt`). |

## p16 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 README names the four meanings + the disambiguation; R2 each leaf's exit-6 test pins its channel. MAIN alone; no change.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | README `## Outcomes` table + the leaf/payload sentence. |
| R2 | acceptance | pass | verify-drafts, verify, export, eval exit-6 tests each assert stdout/stderr per the table. |

## p09 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 re-derivation grounded (`handle` gone; successor paths share `_canonical_candidate`); R2 both ownership classes pinned (caller → validation text; source → contained, no context); R3 no write on refusal + `{}` control; R4 credit recorded, survivors routed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | claim soundness | pass | `rg 'def handle' src` → none; `_canonical_candidate` guards `Mapping` before `dict()`. |
| R2 | acceptance | pass | 4 shapes × 2 paths, exact classes + messages, `__context__ is None`. |
| R3 | correctness | pass | `_counts(database)` equal before/after per shape; `{}` accepted. |
| R4 | verification integrity | open → p104 | 321 / 281 / 40 (`.agent/decisions/p09-mutate.txt`). |

## p74 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 the command runs from clean clones with default operators; R2 the seed raises the survivor count on the same scope; R3 records + the p02 ruling. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | 258 in-scope mutants, both runs; worktrees removed after each. |
| R2 | acceptance | pass | 126 → 133 survivors with the assertion swallowed (`38387c8`). |
| R3 | records | pass | `ops.md` Static checks names the command; p02 closed with its tool. |

## p12 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 acceptance rerun (register step over the four surfaces; filler red; long sentence, punctuation-free bullet, possessive, link target green); R2 the D25 pin repair re-targets the superseded claim without weakening it; R3 the repair fires. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | gate step `register` rc 0 at every gate this session; seeds as recorded in `gate-checks.md`. |
| R2 | verification integrity | pass | repaired test id `tests.test_cli_removal_battery.RemovalObligationBatteryTests.test_d25_rewritten_human_facing_prose_holds_the_project_registe` (standing pin-repair approval): it read the p12 row from the live queue as "port deferred"; it now reads the same row bytes from the closed ledger (same 4 anchor assertions) and asserts the gate runs `.agent/register-audit --gate`. L23 compares this body at git objects `BASE_SHA` vs `adb0ab9`, so the working-tree edit leaves it unchanged; the frame is outside the tripwire pin census (`m3u6a2-tripwires.py` PASS). |
| R3 | correctness | pass | seeds: register step deleted from `.agent/gate` → D25 FAILED; p12 row renamed in the ledger → D25 FAILED; restored → OK. |

## p08 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 the corruption-only claim re-derived from behavior; R2 the probe cites the contract; R3 register. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | claim soundness | pass | library probe across a revision: every active build retired, stale count 0, pinned version answering. |
| R2 | acceptance | pass | the CLI probe's comment names `docs/architecture.md` and its fabrication. |
| R3 | records | pass | register audit + article audit rc 0 on the new sentences. |

## p05 partial (MAINTAIN queue run, unit, tier `data`; owed: owner approval to wire `--all` into the gate) — target = the commit landing this section

Check set: R1 `--rev` reads git objects for every anchor and `owns` path; R2 `--all` grades each record at its adding commit; R3 the fixture fires both ways; R4 the unwired half is recorded as owed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `_lines` / `_exists` route through `git show` / `git cat-file -e` when `rev` is set. |
| R2 | correctness | pass | the M3 maps: 207 / 212 / 294 bad at HEAD → 0 at `3a53389`. |
| R3 | acceptance (partial) | pass | `one-stale.md` rc 1 naming the stale anchor; `resolving.md` rc 0. |
| R4 | claim soundness | pass + register | gate wiring owed; `m3-plan-review.md` fails at its base on scratch-only anchors (p10). |

## p97 partial (MAINTAIN queue run, unit, tier `kernel`; owed: owner ruling on the separator set + ABI) — target = the commit landing this section

Check set: R1 the defect reproduced at HEAD; R2 the design input states what each option changes for already-promoted versions; R3 nothing implemented ahead of the ruling. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `structure()` on a full-width-colon form → `None`; same form with `:` → a 3-label layout. |
| R2 | claim soundness | pass | in-place widening changes `structure()` for every stored v1 program, so promoted versions would start recognizing inputs no confirmed example showed; a v2 ABI leaves v1 programs unchanged. |
| R3 | scope | pass | no source change; the row stays open. |

## p103 close (MAINTAIN queue run, born row pulled forward as an enabler, tier `data`) — target = the commit landing this section

Check set: R1 equal strength (identical emitted table, all self-test controls fire); R2 the speed-up measured; R3 scope (only the segment source changed). MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | pre/post `--emit` → `cmp` identical; `--self-test` 8/8. |
| R2 | acceptance | pass | emit 59.2 → 2.0 s, self-test ~200 → 13.4 s, L29 16 s. |
| R3 | correctness | pass | one helper + two call sites; scans, regexes and table shape untouched. |

## p64 close (MAINTAIN queue run, unit, tier `docs`) — target = the commit landing this section

Check set: R1 each repaired sentence re-derived from behavior, not retyped; R2 the checker grounds against published names only and fires both ways; R3 records. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | claim soundness | pass | library probe across a revision: `follow` → miss with verification passing; pinned `v1` → still answers; the threat-model sentence names `resolve` + the caller. |
| R2 | correctness | pass | grounding walks module + class bodies only (a function-local `cached` grounded the seed until scoped out); seed + pre-p64 text rc 1, shipped rc 0. |
| R3 | records | pass + register | `human-facing.md` + `gate-checks.md` record the tool and seeds; register audit rc 0. Register: the glossary snapshots today's 199 ungrounded words, so it catches NEW definite references only. |

## p53 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the re-derivation is grounded (Gate 4 grades a git object); R2 every facet the row names is in the live digest and moves it; R3 the frozen D02 digest + census stay untouched; R4 credit recorded, its first run's survivors acted on, the rest routed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | claim soundness | pass | D02 + the channels oracle call `_module_from_git("1146421")._parser()`. |
| R2 | acceptance | pass | 5 in-test seeds, each `assertNotEqual(digest)` at equal count; pinned `(218, "9efacf438f50f647")`. |
| R3 | correctness | pass | `tests/test_cli_removal_battery.py` + `tests/test_cli_channels_battery.py` unchanged by this commit. |
| R4 | verification integrity | open → p102 | first run 114/86: 9 survivors = subcommand-group `required` → facet added; second run 123/77 (`.agent/decisions/p53-mutate.txt`). |

## p22 partial (MAINTAIN queue run, unit, tier `kernel`; row stays open, owed: owner approval to retire the observational test) — target = the commit landing this section

Check set: R1 the mechanism test fixes every entropy source the bundle depends on; R2 exactly one id moves in the varied run; R3 length equality is derived, never retyped; R4 credit recorded, survivors routed; R5 the deletion half is recorded as owed, not performed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `_new_id` → counter ids, `time.time_ns` → fixed stream; two runs byte-equal (text + hash). |
| R2 | correctness | pass | only the first `ex` id differs (`ex_ffff…`); the counter advances identically in both runs. |
| R3 | correctness | pass | `assertEqual(len(moved…), len(first…))`; 3,830 bytes measured today. |
| R4 | verification integrity | open → p101 | killed 2108 / survived 1513 / invalid 92 (`.agent/decisions/p22-mutate.txt`). |
| R5 | claim soundness | pass | the observational test stays; its retirement waits on the owner. |

## p63 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 no row carries a line number; R2 every consumer of the table still parses it (L23 splits `locus` on `:`, `instrument_pruned()` matches `<file>:`); R3 the three seeds fire as the row specifies; R4 the re-emit changes nothing but keys + the measured prose delta. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `rg -n 'lineno|"line"|total_lines' .agent/decisions/m3u6a2-tripwires.py` → no hit. |
| R2 | correctness | pass | lifecycle removal battery 59 OK against the new table. |
| R3 | acceptance | pass | blank line above → PASS; rename → DRIFT; span +1 → DRIFT; self-test 8/8. |
| R4 | claim soundness | pass + register | pins/freezes: 15 + 4, same tests + spans; prose: +3 generic `request` lines in the Open WebUI README, grounded by L24's live scan. Register: the emit + self-test take ~1 + ~3 min under load (`ast.get_source_segment` per function over 15k-line modules). |

## p21 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 each acceptance class pinned with an exact expectation; R2 pins mock the library boundary, never the CLI's own dispatch; R3 no existing test touched; R4 preservation credit recorded, survivors routed. MAIN alone (CLI grammar pins).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | last-wins in both orders per flag; three Unicode digit spellings per integer flag; 5 cross-leaf flags with the exact `unrecognized arguments` message; surplus positional on both leaves. |
| R2 | correctness | pass | spies = `mock.patch.object(System, "function_receipts" / "function_report", autospec=True)`, asserting `call_args.kwargs` exactly. |
| R3 | correctness | pass | `git diff` adds lines only. |
| R4 | verification integrity | open → p100 | killed 268 / 266 / 147 / 147; survivors in `.agent/decisions/p21-mutate.txt` → born row p100. |

## p58 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the literal is derived from the baseline blob, never retyped, and its existence asserted; R2 the seed reds the new frame and leaves the old one green. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | one heading found in `6fb4d92`'s `run_demo.py`, asserted to name `exportable function`; read through `_run` from `self.root`. |
| R2 | acceptance | pass | baseline heading restored in the closed tree → new D20 RED, old D20 GREEN. |

## p57 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the work list is drawn from a frozen, main-reachable source and asserted non-empty; R2 the seed reds the new frame and leaves the old one green; R3 D30 holds (the frame reads git objects, never the working tree). MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `4db71a9` is an ancestor of main; 26 rows asserted; read through `_run(["git", "show", …], cwd=self.root, root=self.root)`. |
| R2 | acceptance | pass | seed: one `SITES` rule deleted → new D17 RED naming the missed site; old D17 GREEN on that seed. |
| R3 | correctness | pass | migration battery minus D28 green at the commit's full gate; D30 unchanged. |

## p55 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section, base `546f6e7`

Check set: R1 the cleanup touches only dead-PID run directories; R2 D30 structure holds (helpers take `root`, git via `_run`); R3 no census locus above the L23 pin moved; R4 red-first; R5 records. MAIN alone (test infrastructure; the killed-child tests are the seeds).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `_clean_stale_worktrees` skips a live PID (`os.kill(pid, 0)`), skips non-numeric names + `PermissionError`; a reused PID only delays cleanup. |
| R2 | correctness | pass | new helpers take `root` with no default and call `_run`; `test_lifecycle_removal_battery` (59 OK) + migration battery minus D28 (37 OK). |
| R3 | correctness | pass | `_detached_worktree` keeps its line count (one `with` line swapped); helpers + tests sit after line 1426; `m3u6a2-tripwires.py` output identical to HEAD's. |
| R4 | acceptance | pass | 3 tests red over base's helper (`546f6e7`, detached worktree), green here. |
| R5 | records | pass | `history-gates.md` names the directory, the cleanup and `--clean`. |

## p51 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 acceptance rerun at HEAD (one ruling for every write leaf; per-leaf typo-path + malformed-value probes create nothing and name the cause). MAIN alone; no code changed.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `ExistingOnlyBattery` p51 ×2 OK; the leaf census is derived from `_parser()` at run time, so a new leaf enters it. |

## p17 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 the re-derivation is grounded (the quoted message + pre-call probe left with the authority callback); R2 the successor acceptance holds on a real ledger through supported calls; R3 the no-write assertion is non-vacuous; R4 preservation credit recorded, survivors routed. MAIN alone (a test-only change to an existing CLI race test).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | claim soundness | pass | `tests/test_authority_removal.py` R8 pins the quoted message absent from src + docs + tests; `promote_function` holds one locked comparison (`system.py` `expected_function_hash does not match the locked prospective function`); `LockedGuardTests` keeps it. |
| R2 | acceptance | pass | the CLI test passes at this commit: rc 4 + exact conflict payload after inspect → confirm + compile + verify-drafts. |
| R3 | correctness | pass | the before-dump holds artifact rows (asserted); after = before; receipts `[]`. |
| R4 | verification integrity | open → p99 | credit run killed 1562 / survived 1170 / invalid 70 of 2802; survivors listed in `.agent/decisions/p17-mutate.txt`, unruled here → born row p99 (non-author rulings, suite-replay triage first). |

## p50 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 acceptance rerun at HEAD (absent paths + read-only directories create nothing, exit 5; no `System` built before the assertion). MAIN alone; no code changed.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | `ExistingOnlyBattery` p50 ×3 OK; live CLI probe on an absent path in a `0o555` directory → rc 5, nothing created. |

## p19 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 acceptance from a clean checkout (good rc 0; bad anchor + `TODO-FILL` rc 1, each printing its line); R2 fixtures cannot drift with source edits; R3 records. MAIN alone (a dev validator with mechanical fixtures).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | three fixtures rerun from the gate worktree checkout at this commit, outputs as in the closed row. |
| R2 | correctness | pass | every fixture row anchors `.agent/fixtures/anchors/target.txt`, a committed 3-line file no unit edits. |
| R3 | records | pass | `ops.md` names the command; `gate-checks.md` records the fixtures, `paths:` covers the tool + fixtures. |

## p13 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section

Check set: R1 acceptance rerun (both hosts, exit 2 + `invalid`, messages unchanged); R2 the tests fire when the translation is undone; R3 law current. MAIN alone; no code changed.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | the two named tests OK; three `_input` messages unchanged in `src/cement_runtime/cli.py`. |
| R2 | correctness | pass | translation removed → 4 errors (both hosts on `function eval`, the buffer host + the observation tuple on `resolve`). |
| R3 | law | pass + register | `runtime.md` Known residue listed `_input` as untranslated after the fix landed → clause removed. |

## p07 close (MAINTAIN queue run, unit, tier `kernel`) — target = the commit landing this section, base `99b3734`

Check set fixed before re-reading the diff: R1 each changed query keeps its WHERE + LIMIT + count check; R2 every pin the order change touched is re-targeted at the new key, none weakened; R3 red-first over the unfixed src; R4 publication (docstring + human-facing doc + law); R5 generated paste-ins regenerated. MAIN alone: two `ORDER BY` clauses, every consumer of both lists found by the split suite (7 tests red before re-targeting), each re-target an exact-equality pin.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | `_proposal_bindings` `_PendingProposals` branch + the stale block in `function_report`: only `ORDER BY` changed; counts + `min(count, limit)` checks unchanged; one caller of `_PendingProposals`. |
| R2 | correctness | pass | re-targeted: `test_b23_a13_order_preserved_not_fixed_the` (expected = arrival order, plus an anti-vacuity `assertNotEqual(arrival, sorted(arrival))`; was the baseline lexicographic page M3.4 kept "not fixed" for this row), `test_function_report_stale_anomalies_cover_three_active_statuses_at_revision_ten` (projected ids = the two newest by `sequence`), `test_function_report_pending_proposals_bind_partition_operation_request_and_revision` (`tuple(target)` = arrival), and the SQL-text matchers of `test_function_report_is_one_read_only_snapshot_with_exact_limit_materialization`, `test_function_report_pending_projection_validates_middle_and_last_but_not_tail`, `test_function_report_pending_rows_validate_middle_and_last_scalars_and_bindings`, `test_function_report_stale_validation_reaches_middle_and_last_rows` (the stale matcher now precedes the status-list matcher, both naming `ORDER BY sequence DESC`). |
| R3 | acceptance | pass | the two new probes + re-targeted B23 red over src at `99b3734` (failures=4 with B23's two subtests), green at this commit. |
| R4 | law + docs | pass | docstring lists all six families; `docs/architecture.md` sentence; `runtime.md` ordering bullet rewritten; register audit rc 0. |
| R5 | correctness | pass | `generate.py` rerun → 4 paste-ins; `test_w1_every_paste_in_equals_the_generator_output` OK. |

## p06 partial (MAINTAIN queue run, unit, tier `data`; row stays open, owed: owner ruling on u4c1) — target = the commit landing this section

Check set: R1 each ported row reproduces its driver's mutated bytes at the catalogue base; R2 each replay reproduces its recorded closure set; R3 the unported part is recorded as owed, unclaimed. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | builder asserts, per row, that `old → new` at `line` over `git show <base>:src/cement_runtime/cli.py` equals the driver's `str.replace` result (u4c5b's `gate-first-ordering` with its second edit); u4c5a's base `291e0e9` = the commit whose cli.py sha256 equals the driver's recorded baseline `aa5503faa223…`. |
| R2 | acceptance (partial) | pass | u4c5a 16/16 killed rc 0; u4c5b 12 killed + `installed-file-unlinked` = ruled equivalent rc 0; CONTROL green ×8 each; all restored. |
| R3 | claim soundness | pass | u4c1's catalogue has no surviving source; the row keeps `reproduces 9/9` open and names the ruling it needs. |

## p04 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 acceptance rerun at HEAD (plans, page cost, control, version + fingerprint, reset doc). MAIN alone; no code changed.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass | battery OK; dropping the index → 2 failures naming the temp sort; `SCHEMA_FINGERPRINT` derives from `SCHEMA`; `docs/architecture.md` names the v2 reset. |

## p01 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section

Check set: R1 each acceptance conjunct rerun at HEAD (selections, clean-checkout gate, inline + reasoned suppressions, RUF100 = 0, one seed per tool); R2 the fix changes no behavior; R3 no frozen file touched. MAIN alone.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | acceptance | pass after fix | 26 suppressions censused; 2 in `examples/open_webui/local.py` lacked their own reason → comment lines added; format/lint/RUF100/types seeds each rc 1; configured `ruff check` rc 0. |
| R2 | correctness | pass | comment lines only; `tests.test_open_webui_local` OK. |
| R3 | correctness | pass + register | a reason appended to `_command_supervisor.py:157` redded `test_r1_moved_modules_are_byte_identical_and_leave_the_package` (M3.7 freezes the relocated bytes) → reverted; that assert shares the comment above line 156. |

## p02 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section, base `784350c`

Check set fixed before re-reading the diff: R1 the mechanics `.claude/rules/assurance.md` Mutation campaigns names (isolated clones, bytecode off + purge, loaded-module proof, byte-exact restore, control first at full worker count); R2 classification — superseded (`old` absent) vs anchor-miss (present off `line`) vs applied; R3 every rc branch fires; R4 p02's acceptance; R5 law + records. MAIN alone (a dev tool whose seeds are mechanical).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | clones = `git worktree add --detach <base>` in a temp dir, removed in `finally`; `_suite` purges every `__pycache__` with `PYTHONDONTWRITEBYTECODE=1`; the probe imports the module and requires its file = the clone's path holding the edit + 80 chars of context (deletions included); `finally` restores and compares sha256; each clone ends `git diff --quiet`; CONTROL runs in every clone before any mutant. |
| R2 | correctness | pass | `_locate`: no occurrence → superseded; >1 occurrence with none starting on `line` → anchor-miss (rc 2, seeded); u4b's 8 rows the scratch run called ambiguous carry the line its re-anchored pass applied (`final-reanchored.jsonl`) and replay killed. |
| R3 | correctness | pass | seeds: equal expect rc 0; expect mismatch rc 1; `ran` 5 → CONTROL red rc 2; anchor-miss rc 2; non-importing mutant → not-loaded rc 2. |
| R4 | acceptance | pass | u4b at `62e6d09`: CONTROL ran 353 × 8 green; 58 killed, superseded [XMEM-001], survived [STALE-013, STALE-014] = the catalogue's `equivalent` (reviewer rulings carried verbatim); rc 0. |
| R5 | law + records | pass | `ops.md` Static checks names the command + rc classes; `gate-checks.md` records the seeds, `paths:` covers the tool + catalogues. |

## p81 close (MAINTAIN queue run, unit, tier `data`) — target = the commit landing this section, base `d4746ef`

Check set fixed before re-reading the diff: R1 no row can leave the queue unclosed (floor over both files' histories); R2 a closure SHA is admitted only when it resolves to an ancestor of HEAD; R3 `HEADER`, the queue header, `CLOSED_HEADER`, the ledger header + `--emit-stub` agree; R4 every pre-edit seed still fires; R5 p81 + p68 + p69 acceptance rerun; R6 law + records current. MAIN alone (a dev-tool grader whose seeds are mechanical; a teammate adds no assurance they miss).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | correctness | pass | seeds: drop a born row → `MISSING ['p62']`, the same drop committed → `MISSING ['p62']`, a closed row dropped from the ledger → `MISSING ['p68']`, a closed row back in the queue → `open AND closed`, a closed `p99` never queued → red. |
| R2 | correctness | pass | `closed=0000000`, `closed=HEAD`, a commit off HEAD's history → rc 1 each (`closure_sha_errors`: hex shape, `cat-file -e`, `merge-base --is-ancestor`). |
| R3 | correctness | pass | header drift seeds red for both files; `--emit-stub` refuses the live queue byte-identically and writes `HEADER` alone. |
| R4 | correctness | pass | `d4746ef` grader seeds vs the new grader's: same verdicts for drop, committed drop, header, `Accept:` on a continuation line, `unknown`, `Accept:` removed, git 127, shallowness stub. |
| R5 | acceptance | pass | p81: the seeds above; p68: `rg -F 'last committed queue' .claude/rules/` rc 1 beside 3 hits in the ledger (positive control); p69: `claude -p` context-only question → 0 `tool_use` + the spec's answer from the root, 0 `tool_use` + `NOT LOADED` with `CLAUDE.md` line 1 deleted outside the repo. |
| R6 | law + records | pass + register | `ops.md` Layout names the closure form + floor; `gate-checks.md` re-records the grader seeds; the queue header's stale gate line (`unittest discover` + `uv build` + `spec-lint`) → `.agent/gate`. Register: `ops.md` said `.agent/**` revisions owe no suite run, while D25 reads `.agent/deferred.md`'s p12 row and the batteries read or run `.agent/decisions/` files — fixed in place (census command named). |

## MAINTAIN Open WebUI live testing (ad-hoc request close) — target `3188ba3..c832287`, fixes in `6fdbb26`

Check set fixed before the diff was read: correctness C1-C8 + cleanup K1 (reviewer-35, raw table `.scratch/review/owui/reviewer-35.md`), security S1-S6 (MAIN). Every finding was reproduced red by MAIN at `88ab4c2` (tag `archive/owui-w6-red`) before its fix.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| C1 (F1, F2) | correctness | minor → fixed | the generator rebound `import cement_runtime.x` (no `as`) and mixed import statements wrongly and dropped statements between library imports; all three shapes are now refused (`test_w6_the_generator_refuses_import_shapes_it_cannot_rebind`). The shipped sources use none of them. |
| C2 | correctness | pass | the importer serves its digest package alone, repeat loads are idempotent, and the digest is checked before the first exec. |
| C3 (F1, F2) | correctness | major → fixed | a non-text field value raised `TypeError` out of the tool, and examples of an older revision entered the derived program. Each input's value is now checked as text, and examples are taken from the current revision only (`test_w6_a_non_text_input_is_refused_not_raised`, `test_w6_examples_of_an_older_revision_stay_out_of_the_program`). |
| C4 (F1, F2) | correctness | major → fixed | `merge_case` read outputs from a 1000-row page, repeated ids passed, and a later refusal hid committed writes. Outputs now come from the case, repeated ids are refused before any write, and a refusal after a write carries `completed` (skill sentence qualified; `test_w6_merge_case_reads_its_case_not_a_page_of_examples`, `test_w6_repeated_ids_are_refused_before_any_write`, `test_w6_a_failure_after_a_write_reports_the_writes`). |
| C5, C6 | correctness | pass | projection is stored only when projectable, and the skip rules hold across revisions; the inlet copies on write, touches the last user message alone and never raises. |
| C7 (F1) | correctness | minor → fixed | a server that outlived the 30 s grace period was orphaned; `_stop` now SIGKILLs it and reaps (`test_w6_a_server_that_outlives_its_grace_period_is_killed`). |
| C8 (F1) | correctness | minor → fixed | the argv frame never ran `serve`; `test_w6_serve_starts_the_server_with_the_key_in_its_environment_alone` drives it with a fake `Popen` (seed: key appended to argv → red). Other frame families killed their sampled breaks. |
| K1 | cleanup | minor → fixed | the unused `PROGRAM` fixture is removed. |
| R1 | register → fixed | — | an edited copy loaded after a clean one reused the clean package, so the README's per-file refusal claim overreached. Every load now verifies its own sources (`test_w6_an_edited_copy_refuses_after_a_clean_copy_loaded`). |
| R2 | register → fixed | — | the switch read one 100-receipt page, so older versions were unpinnable and misnumbered (Decision: rollback to any earlier version). It now pages every receipt (`test_w6_every_version_is_offered_past_one_page`). |
| S1 | security | pass | all 8 learning functions route through `_run` (role `admin`); the action checks the role inline; the chat tool has none, by design (AST census). |
| S2 | security | pass | `set_switch` / `register_operation` are reached only by `cement_admin.py` (AST pin over the learning tool; the chat tool names neither); Open WebUI actions are UI buttons, never model tools. |
| S3 | security | pass | the action writes only a value its select offered, after a confirmation of exactly `True` (W4 battery). |
| S4 | security | pass | the actor comes from Open WebUI's server-side `__user__` (`utils/actions.py` `user.model_dump()`), never the request body. |
| S5 | security | pass | the model key travels by environment alone; a search over HEAD, all history and the run's scratch logs gives 0 hits, against a positive control of 1. |
| S6 | security | minor → fixed | the README did not state that the local instance has no login and binds 127.0.0.1; it now does. |

Findings: 4 major + 6 minor fixed, plus 2 register items fixed; 0 open. Live re-check after the fixes: the re-pasted files loaded, an unseen intake form returned `covered: true`, and an idle pass reported nothing to learn (`.agent/decisions/owui-live-e2e.md` § After review).

## IMPLEMENT phase close (phase) — target `2af499f..8be6d83`, fixes in `35ed37a`

Check set fixed before the diff was read, one `reviewer` per lens over the units TOGETHER (each unit's own section stands): correctness X1-X7 (reviewer-32), cleanup K1-K4 (reviewer-33), altitude A1-A4 (reviewer-34), security P1-P6 (MAIN). Raw tables: `.scratch/review/phase/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| X2 (F1) | correctness | major → fixed | a challenge that a later supersession replaced still failed a historical pin's P-d (exact + projected); P-d now grades active challenges alone (`tests/test_phase_integration_battery.py` X2 ×2 red at 941d711, archive/phase-red). |
| X4 (F2) | correctness | major → fixed | the skill's saved-program resume missed a merge stopped before its supersession (no pending proposal, two active outputs, empty build-current `work`); the rule now covers it (X3 pins the skill + workflow text). |
| X1, X3, X5-X7 | correctness | pass | pinned version answers through its own program on resolve, export and eval (X1 battery test); 23 writer branches + 23 rollback injections + 10 refusals write all-or-nothing; skill CLI calls exist; examples use public API; no test names a SHA outside main; skip set = 3. |
| K1 (F1) | cleanup | minor → fixed | `diff_versions` re-read programs that reconstruction already embedded (4 → 2 queries). |
| K2-K4 | cleanup | pass + register | register: `SKILL.md` "No write is idempotent" reads broad beside `source_id` (the skill's own writes are not idempotent) — ruled no change. |
| A2 / A4 (F1-F5) | altitude | minor → fixed | README publishes the `System` methods by purpose; supersede refusals by exit class; source-id idempotency; architecture keeps pins across a revision; spec Decisions + `runtime.md` + `assurance.md` state v3, case keys and verification per switch mode. |
| A1, A3 | altitude | pass | — |
| P1-P6 | security | pass + register | interpreter on raw text linear + refusal-total; LLM-only review gated by support + set verification + the switch, stated as untrusted; bundles re-validated; integrations open existing-only; zero runtime deps, scanners green; no process control in the core. Register: Open WebUI notifications can name the ledger path (M5.3 S6). |

Findings: 2 major + 6 minor fixed in `35ed37a`; 0 open. This ledger holds no open row.

## M3.9b replay (IMPLEMENT, unit, tier `docs`) — target `92a162e`, fixes in `baf2743`

Independent replay of the M3.9a claim ledger (reviewer-31): C01-C21 + D1 (README blocks run as printed) + D2 (no superseded model stated) + D3 (publication stated positively). 16 hold, 8 fail; raw table `.scratch/review/m3u9b/table.md`. Every ruling below = MAIN's, on the reviewer's code probes (pinned resolve → 4 checks; a reviewed proposal changes status; revoking the contradicting example restores the old receipt; follow serves v2 with no switch write; `source_id` accepted as a fourth key; distinct reviewer names gate compile).

| id | verdict | ruling (MAIN-verified) |
|---|---|---|
| F1 (D1) | major → fixed | `candidate.json` + `program.json` had no producer in their blocks: each block now writes its file (heredoc); the projection block names its `form.plan` operation and the set precondition (a confirmed example per layout). The candidate block driven: submit rc 0, a repeat with the same `source_id` exit 4. |
| F2 | major → fixed | README promised seven checks in every resolve: `checks` = seven under `follow`, four pinned checks under `pinned`, none under `off`; the cost line + the threat model's export line say the same. |
| F3 | minor → fixed | architecture called proposals append-only; only projection programs/settings + switch settings are. |
| F4 | minor → fixed | contradiction also clears when the contradicting example is revoked or superseded (README ×2, architecture, threat model). |
| F5 | major → fixed | the threat model said a person stands between every learned version and production; `follow` is a standing choice, `pinned` keeps one version, `off` is the default. |
| F6 | minor → fixed | `example supersede` now states its refusals (exit 2, nothing written). |
| F7 | major → fixed | the submission object takes four keys; `source_id` and its exit-4 refusal are named. |
| F8 | minor → fixed | Cement authenticates no reviewer name and counts distinct names toward the reviewer gate. |
| other rows | holds | 184 cited tests + the hospital demo + 45 CLI help nodes green. |

Checks after the fixes: register audit rc 0; `tests.test_cli`, `test_cli_channels`, `test_cli_channels_battery`, `test_cli_removal_battery`, `test_submission_battery`, `test_proposal_binding_battery`, `test_authority_removal`, `test_lifecycle_removal_battery` → Ran 523 OK (586.3 s).

## M3.9a close (IMPLEMENT, unit, tier `docs`) — target `92a162e` (squash of `archive/m3u9a-land`), records in the next commit

Tier `docs` = consistency pass: MAIN's register audit (rc 0, filler 0 on every Markdown surface) + the README quick start driven end to end through the CLI (every command rc 0) + the claim ledger `.agent/decisions/m3u9a-claims.md` (C01-C21), which M3.9b replays independently (its own section). Prose-pin repair (general-purpose-6, `.scratch/m3u9a-repair/table.md`, 7 rows): D22c D23 D26 L22 L23 D34 re-targeted at the rewritten claims (strings derived from the shipped files; D23's frozen baseline stays at 635a473, its new count derives from the live docs — a pre-squash SHA dependency was refused); B26, x28 and L24 were satisfied by prose (event-payload claim restored, one-line leaf sentence, inputs not requests). AST census: no id lost, `assert*` calls never fewer.

Gate at the squash: `.agent/gate` on `92a162e` rc 0 (clean tree, `heavy`): unittest 625.5 s, Ran 1233, outer skipped none, nested D28 = L30, D28 25 revisions / 1 replayed.

## M3.8 close (IMPLEMENT, unit, tier `data`) — target `ef06a25` (squash of `archive/m3u8-land`; review read `7b71982`), records in the next commit

Check set fixed before the diff was read, all lenses in one `reviewer` (data unit): D1 structural validator (the transcript updater), D2 live spot-check (the demo), D3 the lifecycle told, D4 masks, D5 test repairs, C1-C3 code lenses (reviewer-28). Raw table: `.scratch/review/m3u8/table.md`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| D1 | validator | pass | `.agent/decisions/m3u8-transcript.py` twice → byte-identical README; a planted drift → `--check` rc 1, no write. |
| D2 | spot-check | pass | `uv run python examples/hospital_ocr/run_demo.py` ×2 → `All checks passed.`; printed acts match the transcript after masking. |
| D3 | lifecycle | pass | raw requests → pending proposals → scripted learning pass (projection, compile, verify, promote) → switch off → follow → v2 → pin v1 → export + offline eval. |
| D4 | masks | pass | every per-run value masked with a count pin. |
| D5 | repairs | pass | 29 original ids kept + 6 new (35); 10 body repairs + 7 retargets keep their obligations; the six new pins red at 04646cb (failures=1 errors=5). |
| C1-C3 | code lenses | pass + register | R1: the root README + architecture still told the old lifecycle → owned by M3.9a. |

Red-first: `uv run python -m unittest tests.test_hospital_ocr_example.LearningWalkthroughTests tests.test_hospital_ocr_example.TranscriptUpdaterTests` at 04646cb (tag archive/m3u8-general-purpose-4) → 6 tests, errors=5 failures=1.

Gate at the squash: `.agent/gate` on `ef06a25` rc 0 (clean tree, `heavy`): unittest 619.7 s, Ran 1233, outer skipped none, nested D28 = L30, D28 24 revisions / 1 replayed.

## M5.3 close (IMPLEMENT, unit) — target `097de5b` (squash of `archive/m5u3-land`; review read `c22ef68`, re-review `74a19df`), records in the next commit

Check set fixed before the diff was read: correctness (reviewer-25: contract §7 E1-E4, X6 capture binding, the smoke record), cleanup (reviewer-26), altitude (reviewer-27), security S1-S6 (MAIN). One re-review round (reviewer-29, 6 rows). Raw tables: `.scratch/review/m5u3/`, `.scratch/review/m5u3-r2/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| F1 / S4 | capture | finding (major) → fixed | a malformed peer record (`operation: []`, unhashable) raised inside `_pairs` and dropped an unrelated valid pair; each call is validated alone. |
| F2 / S4 | capture | finding (major) → fixed | absent ids compared equal (`None == None`) and selected a history message; the filter now requires the current message id, and a chat or question without an id retains nothing. |
| F3 / S2 | capture | finding (major) → fixed | the reply was cut at 16,384 characters: a 20,000-character ASCII reply that fits lost its tail, and 16,384 astral characters (65,536 B) exceeded the 64 KiB provenance bound and lost the answer. The whole reply is kept when the provenance fits, else the longest fitting prefix, marked; the README states it. |
| F4 | capture | finding (major) → fixed | an accepted record without `output` was retained as null; required keys are checked before pairing. |
| F5 | battery | finding (major) → fixed | nine E4/X6 obligations survived the battery; `CaptureBindingBattery` pins source id + provenance per pair + failure containment; `.agent/decisions/m5u3-capture-mutants.py` 9/9 killed (exits 1 on a survivor). |
| S5 | security | finding → fixed | the README never said retained answers are untrusted: `/api/chat/completed` lets a signed-in user resubmit fabricated tool calls; the README now names the three gates (learning pass, support floor, switch). |
| AL4 (F1) | altitude | finding (major) → fixed | `examples/open_webui/README.md` missing from the L24 Markdown census `DOCS`; the tripwire pair regenerated (stack repair). |
| S6 | security | register | notifications carry `CementError` text, which can name the admin-configured ledger path; deployment-local exposure, ruled no change. |
| other rows | all lenses | pass | 8/8 + 4/4 cleanup pass; wheel excludes the example, sdist carries it. |

Red-first: b4dd7b4 (branch fix/m5u3) at c22ef68's code → `uv run python -m unittest tests.test_open_webui_example` failures=5 errors=1 (F1-F4 tests); the binding + containment pins pass there (preservation; closure = the 9-mutant probe). Kernel capture smoke: real Open WebUI 0.12.3, 6/6 (`.agent/decisions/m5u3-smoke.md`).

Gate at the squash: `.agent/gate` on `097de5b` rc 0 (clean tree, `heavy`): unittest 592.2 s, Ran 1227, outer skipped none, nested D28 = L30, D28 23 revisions / 1 replayed.

## M5.2 close (IMPLEMENT, unit) — target `6e9e715` (squash of `archive/m5u2-land`; review read `d4ed851`), records in the next commit

Check set fixed before the diff was read: correctness (reviewer-4: contract §6 LP0-LP4, learning-cases fields + code lenses), cleanup (reviewer-5), altitude (reviewer-6). Raw tables: `.scratch/review/m5u2/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| F1 / ALT-1 | resume | finding (major) → fixed | an unfinished merge (two active outputs on one case, no pending proposal) reported `nothing_to_learn`; the work classifier now reads active case outputs (LP2f red at 123f360). |
| F2 | resume | finding (major) → fixed | an interruption before `projection set` lost a ready projected case: the skill's resume rule reads `program.json` against `projection show` (LP0d skill pin red at feebf9f); the read surface is contract amendment A7. |
| CL1 | cleanup | finding (minor) → fixed | `learning_cases` reuses the same-snapshot build projection (LP2g red at 3c60f8f: 3 != 1). |
| CL2 | cleanup | finding (minor) → fixed | one executable workflow in `SKILL.md`, references for detail. |
| R1 | altitude | finding (minor) → fixed | the projection reference confused schema field names with their values; reworded. |
| other rows | all lenses | pass | — |

Red-first (tag archive/m5u2-impl = 55c83fb, base 72e15b0): SupersessionBattery + ContradictedPromotionBattery at ddcd7d7; LearningCasesBattery LP2a-e + ScriptedPassBattery LP0/LP1 at d4a52c0 (no `learn` leaf); SkillBattery LP3 + PolicyDefaultsBattery LP4 at 287aa4f / 72e15b0 (defaults 3/2/7d). Command: detached worktree + battery copy, `PYTHONPATH=src uv run --no-project --python 3.13 python -m unittest tests.test_learning_pass_battery.<class>`.

Gate at the squash: `.agent/gate` on `6e9e715` rc 0 (clean tree, `heavy`): unittest 639.9 s, Ran 1209, outer skipped none, nested D28 = L30, D28 22 revisions / 1 replayed.

## M4.2 close (IMPLEMENT, unit) — target `87d011f` (squash of `archive/m4u2-land`; round 1 read `93904e3`, re-review `e5b7f26`), records in the next commit

Check set fixed before the diff was read: correctness (reviewer-10: contract §5 L1-L9, X7, C4, S7 + code lenses, 33 rows), cleanup (reviewer-11), altitude (reviewer-12); one re-review round (reviewer-21, 14 rows, acceptance checks alone). Raw tables: `.scratch/review/m4u2/`, `.scratch/review/m4u2-r2/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| F1 / ALT1 | promotion | finding (major) → fixed | members built under a previous program stayed in a new-program set (and a zero-candidate promotion sealed them under the new program). Promotion now retires them (`projection-superseded`); reconstruction binds each member's program to its receipt's (L11 red at 93904e3; L17 red at 4b99157 via a build_function-swap probe). |
| F2 | contrary evidence | finding (major) → fixed | raw-key equality contradicted a projected member on review, live verification and P-d; the exact-SQL branches now cover exact-mode artifacts alone (L15 L16 red at 7a65c03). |
| F3 | verification | finding (major) → fixed | the structural probe deleted the title, not the last structural line (§5); L18 runs a lenient interpreter that verification must fail. |
| F4 / ALT2 | preview | finding (major) → fixed | `test_projection` omitted pending proposals + per-key readiness (L13); re-review R2-F4: readiness ignored reviewers + span → readiness = compile's own gates via `_assess_examples` (L19 red at 376d520). |
| F5 | battery | finding (major) → fixed | L2 full-ledger purity per refusal, L3 real stale builds, L5 ledger-free under patched System/sqlite3, L7 ordered vector, L8 real A→B→A + historical pin, V1 invalid program; `.agent/decisions/m4u2-mutants.py` 15 killed + V4 ruled EQUIVALENT (V1 ≥ 1 layout ∧ V2 every layout witnessed ⇒ V4). |
| F6 / R2-F6 | battery | finding (minor) → fixed | expected outputs derived from the confirmed example or fixture bytes, none retyped. |
| C1-C4 | cleanup | finding → fixed | one program loader; one verification projects each raw input once (L14); exact-mode counts in SQL; memo bounded — re-review R2-C2: a full memo cleared mid-verification → least-recently-used eviction (L20 red at b1b865b). |
| ALT3 | altitude | finding (minor) → fixed | exact-mode reviewer count back in SQL. |
| ALT4 | altitude | ruled KEEP | `System.projection` + `projection show` = contract amendment A7 (the skill's resume rule reads them). |
| stack burden | correctness | src defect → fixed | the stack repair found exact-mode compile enumeration materialized every row (rows 39/41); exact mode streams again, a projection alone materializes (cf42b7c). |

Red-first: `tests/test_projection_lifecycle_battery.py` red at 64ffac0 (archive/m4u2-red-base: no `cement_runtime.projection`); L10 at 2acd1a7 (archive/m4u2-impl).
| comment | cleanup | finding (minor) → fixed | the streaming comment claimed memory bounded by one row; the duplicate check keeps one text per distinct input (general-purpose-5). Comment corrected in the records commit. |

Preservation credit: closure probe `.agent/decisions/m4u2-mutants.py` (15 killed, V4 equivalent); default-operator credit over `system.py` = p93 (cost).

Gate at the squash: `.agent/gate` on `87d011f` rc 0 (clean tree, `heavy`): unittest 909.4 s, Ran 1182, outer skipped none, nested D28 = L30, D28 21 revisions / 2 replayed.

## M4.1 close (IMPLEMENT, unit) — target `535a0a9` (squash of `archive/m4u1-land`; review read `e448ad2`), records in the next commit

Check set fixed before the diff was read: correctness (reviewer-13: contract §4 + AM1-AM6, 24 rows), cleanup (reviewer-14, 8 rows), altitude (one unnamed reviewer). The `tester` (tester-1) wrote the diff-blind suite + the differential oracle `tests/projection_oracle.py` before MAIN's interpreter was read. Raw tables: `.scratch/review/m4u1/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| C1 (AM3) | correctness | finding (minor) → fixed | TAB around a label/heading key is equivalent to its trimmed key (AM3), yet `strip(" ")` in place of `strip(_EDGE)` left all 72 tests green; label + heading TAB pins added (ab67311); the mutant now reds 2 tests in RuntimeGrammarTests. |
| F1 | altitude | finding (minor) → fixed | the module exported 22 names, §4 names seven; `__all__` = the seven (e5b7f26), pinned by `test_exports_exactly_the_contract_api` (red at ab67311: AttributeError). |
| other correctness rows | correctness | pass | 21,278 adversarial texts + 2,091 derived-layout matches + 242 program mutations: zero runtime/oracle divergences, exceptions or bound violations. 3.12/3.14 execution rides CI (AM6). |
| L1-L8 | cleanup | pass | — |

Red-first: the tester's suite (archive/m4u1-test = 54ede5d) is absence-red at 3817417 (no `cement_runtime.projection`); MAIN's interpreter landed green against it with the AM2 TAB patch the contract amended.

Mutation credit + survivor ruling: `uv run python .agent/mutate tests.test_projection_ir --rev bdb5205 --workers 3` → killed 569, survived 103 (65 in projection.py, 38 in json_value.py outside this diff), invalid 10 of 682. reviewer-30 ruled the 65 independently: 4 equivalent, 50 contract-open (work-counter formula edits that keep the I7 bound, AM4 "any honest counter"), 11 missing-test in four families → pinned by `RuntimeMutantRulingTests` (the commit after the squash): a value whose type compares equal to everything is refused as `ValidationError` at 7 sites (§4 `parse_program(value: object)`), U+D7FF/U+E000 are legal literals beside the surrogate range, a repeated `keep` field that sorts low is refused, a lower title is no match. One mutant per family (lines 72, 90, 117, 235) now reds the new tests (`.scratch` kill check). 0 survivors unruled.

Gate at the squash: `.agent/gate` on `535a0a9` rc 0 (clean tree, `heavy`): unittest 628.9 s, Ran 1156, outer skipped none, nested D28 = L30, D28 19 revisions / 1 replayed.

## M5.1 close (IMPLEMENT, unit) — target `1289797` (squash of `archive/m5u1-land`) (review read `5f4c2b4` on the pre-stack lineage), records in the next commit

Check set fixed before the diff was read, one `reviewer` per lens: correctness (reviewer-7: m45-contract §3 switch + versions + pinned checks P-a..P-d + the read census), cleanup (reviewer-8), altitude (reviewer-9). Raw tables: `.scratch/review/m5u1/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| C1 | correctness | finding (major) → fixed | a pin over more than 32,766 members exceeded SQLite's bound-parameter ceiling; pinned checks now join `function_memberships` (W13 pins 32,767 members). |
| C2 / R1 | versions | finding (major) → fixed | `function versions` lacked the projection hash and an eligibility answer; `--check` adds `servable` (whether each version would serve now) beside `selected` (W7 ×2; R3's selected/servable split). |
| C3 / R2 | diff | finding (major) → fixed | `function diff` named fields, not the changed case keys + values; it now names keys, outputs and projection changes (W8). |
| C4 | battery | finding (major) → fixed | rejection + snapshot branches unpinned: W1 off reads two rows alone, W5 revision never unpins, W5c a retired suspended member fails the pin, W10b one snapshot; closure probe `.agent/decisions/m5u1-mutants.py` 5/5 killed. |
| cleanup C1, C2 | cleanup | finding (minor) → fixed | receipt readers shared (`_function_receipt_from_row` path), pinned serving reads members through SQL joins, not a Python round-trip. |
| other rows | all lenses | pass | — |

Red-first: `tests/test_switch_battery.py` at 0d62318 (tag archive/m5u1-red = d63aa2c + the battery) → Ran 16, failures=1 errors=19, every test red (W1-W13); review-fix pins W7 W8 W10 W13 red at 5f4c2b4 (archive/m5u1-impl lineage, errors=4). Stack burden (general-purpose-5, 21 ids across 6 modules + the tripwire datum): AST census over `3dccdc6..12905d6` = 14 changed test bodies, `assert*` calls never fewer, none deleted; the read-capability census now resolves a literal SQL forwarded through a helper parameter (a non-literal still fails it).

Gate at the squash: `.agent/gate` on `1289797` rc 0 (clean tree, `heavy`): unittest 607.6 s, Ran 1083, outer skipped none, nested D28 = L30, D28 18 revisions / 1 replayed.

## M3.7 close (IMPLEMENT, unit) — target `635a473` (squash of `archive/m3u7-land`; review read `985e071`), records in the next commit

Check set fixed before the diff was read, one `reviewer` per lens: correctness C1-C5 + battery R1-R5 (reviewer-22), cleanup L1-L4 (reviewer-23), altitude AL1-AL4 (reviewer-24). Raw tables: `.scratch/review/m3u7/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| R5 / AL3 register | p54 | finding F1 (major) → fixed | the README's one block built a `CommandCandidateSource` + `System` and never ran the stub (audit hook: 0 adapter launches); R5 asserted class names only (reviewer-22 F1, reviewer-24 R1). The block now calls `source.propose(...)` and the README states the printed echo; R5 runs the block and asserts the stated output. New R5 against the `985e071` README → `ValueError` (no stated output). |
| R3 | core keeps the protocol alone | finding F2 (major) → fixed | R3 rejected the literal name only: the base `source.py` restored with its class renamed `LegacyCommandSource` left all five tests green. R3 now pins the module's structure (docstring + 3 imports + the one `CandidateSource` class) and a second R3 frame pins `subprocess`/`signal` absent from every core module; the renamed restore → 2 failures. |
| R1, R2, R4 | relocation | pass | 8 isolated undo controls (reviewer-22) each red: supervisor + stub bytes, class span, protocol span, export list, static + fresh-process reverse import. |
| C1-C5 | correctness | pass | relocated class span byte-identical; supervisor launched by file name beside it; burden repairs (test_source, test_cli_channels, test_cli_channels_battery, test_cli_removal_battery, test_submission_battery, test_lifecycle_removal_battery, test_outcome_removal_battery) keep their obligations. Register G1: tripwire-locus drift predates M3.7 (p63). |
| L1-L4 | cleanup | pass + register | Q1: `example_adapter.py:1` says "Installed protocol stub"; byte equality (R1) freezes it → ruled no change this unit. |
| AL1, AL2, AL4 | altitude | pass | no shim or re-export; `__all__` 51 → 50 (exactly `CommandCandidateSource`); 35 CLI nodes / 28 leaves byte-identical; wheel = `cement_runtime` alone, sdist carries `examples/command_source/`. |

Red-first: `tests/test_relocation_battery.py` at fa5ac87 (tag archive/m3u7-red = 93007ac + the battery) → R1 ×2, R2, R5 errors + R3 failure; R4 holds at base by construction (preservation: injecting `import command_source` into a core module reds it; `.agent/mutate` cannot reach import statements → uncredited, closure control recorded).

Gate at the squash: `.agent/gate` on `635a473` rc 0 (clean tree, `heavy`): unittest 818.2 s, Ran 1067, outer skipped none, nested D28 = L30, D28 17 revisions / 2 replayed.

## M3.6b close (IMPLEMENT, unit) — target `93007ac` (squash; review read `fc752eb`, the same unit on the pre-squash M3.6a3 lineage), records in the next commit

Check set fixed before the diff was read: the three code lenses of `CLAUDE.md` `Engineering`
(correctness L1-L10 + the unit's predicates S1-S4, S6, supersession schema, p50, p51,
pin-repair non-weakening; cleanup L1-L8; altitude L1-L5) + MAIN's security lens. Raw tables:
`reviewer-1` (correctness, stopped after its 3 last rows waited on a held CPU slot; those rows
adjudicated below from MAIN's probe), `reviewer-2` (cleanup), `reviewer-3` (altitude). Every
verdict below = MAIN's, on the reviewers' anchors rematched against `fc752eb` bytes.

| row | verdict | evidence |
|---|---|---|
| correctness L1/L5 (F1) + altitude L4 (L4-F1) | fixed | `parse_function` set-membership on a JSON `abi` raised `TypeError` for `[]`/`{}` (CLI exit 1 + traceback). Fix = exact-type check before membership; pins `test_s1_an_unhashable_bundle_abi_refuses_as_validation` red at `fc752eb` (errors=3) |
| correctness L3 (F2) | fixed | `tests/test_source.py` fixture still passed the removed `CandidateRequest.request_id`; the module was outside the unit's burden runs (timing-sensitive). Fix = the fixture keyword dropped, every test + assertion kept; `test_source` green alone (10 tests) |
| correctness L2, L4, L6-L10 | pass | deleted invariants re-homed (`store.py` direct proposal scope, `review` transition guard); 122 modified + 14 added + 0 deleted test methods; expectations derive from live rows |
| S1 | pass + extended | real v2 ledger from `1935f68` refused both modes + CLI exit 5; package version pin `test_s1_the_package_version_is_the_cut` red at `fc752eb` (0.1.0) → 0.2.0 |
| S2, S3, supersession schema | pass | `.agent/decisions/m3u6b-constraint-probe.py`: deleting each of 8 constraints alone (3 append-only triggers, pin-scope trigger, switch CHECK, composite FK, superseded CHECK, supersedes UNIQUE) reds its owning test, survivors none. The supersession pin `test_s2_supersession_columns_bind_origin_and_supersede_each_example_once` was missing (reviewer-1 X-schema) and added |
| S4, S6, p50, p51 | pass | residue census with survivor equality; source-id refusal before ID/clock/event work; every non-register CLI leaf exits 5 creating nothing; register grades values first |
| pin repairs | pass | full tests sweep: no equality loosened, no count relaxed; the one assertion-count decrease merges two exclusive branches into one stricter `assertRaisesRegex` |
| cleanup L4-a, L4-b | fixed | binding-adapter comment kept the v2 request-row design; `submit_proposal` docstring kept the unconditional retry claim → both state v3 |
| cleanup L1-L3, L5-L8 | pass | shared `_unsupported_schema` + `_validate_ledger`; derived transport bound; no new closure |
| cleanup register R1 | fixed | `.claude/rules/runtime.md` census 13 tables / 3 nullable INTEGER → measured 15 / 2 |
| altitude L1-L3 | pass | `create` on Store + System (A3), register-only creation, `source_id` as a `--submission` key keep every invariant in its owning layer |
| altitude L5 (L5-F1) | fixed | same docstring as cleanup L4-b |
| altitude handoffs | fixed | `--submission` help names `source_id?`; pyproject 0.2.0 |
| MAIN security lens | pass | existing-only open creates nothing (missing check precedes any connection; `mode=ro` refuses a missing file; symlinks refuse first); `source_id` ≤ 512 UTF-8 bytes, control-free, bound as a parameter; transport caps derive from library limits |

MAIN-found while fixing (same close): README + `docs/adapter-protocol.md` still stated the
request row, three records, unconditional no-idempotency and `request_id` on the source
envelope → rewritten to v3 (two records, source id, no per-call identifier); the envelope's
protocol moved `cement-candidate-v1` → `cement-candidate-v2` (a removed field = a new protocol);
10 prose/census pins re-targeted under the pin-repair approval. Partial review fields passed
`_validate_proposal_shape` as pending (general-purpose-1 report) → each field graded on its own.

Round-4 pin repairs after the review (general-purpose-1 Part A, owner pin-repair approval; each re-targets a prose/census pin at MAIN's v3 prose or reads a closed transition from git): test_cli_channels_battery d23; test_cli_removal_battery d22a, d14; test_lifecycle_removal_battery l21, l23 ×2, l24, l29; test_submission_battery d25, d41, d34; test_outcome_removal_battery o4, o5 (preservation at CLOSE = `17896eb`). MAIN's AST census over the Part A range (`283552f..2b57a3a`): 11 changed test bodies, `assert*` calls never fewer (d23 11 → 12, d25 5 → 6), no test deleted; o4/o5 keep exact equality on the closed package.

p04's acceptance (feed plan without a temp sort, page visits near its size) had no committed pin at the squash → `ReceiptFeedPlanBattery` lands with these records; its control drops `function_receipts_feed` → `USE TEMP B-TREE FOR ORDER BY`, 2 failures.

Findings: 8 raised (2 major), all fixed in the squash; 0 open.

Rulings that bind beyond this pass:

- A module a burden run excludes (timing-sensitive `tests/test_source.py`, D28) still carries the
  unit's burden: run it alone before the squash, or the squash lands red on it.
- A wire envelope that loses a field gets a new protocol name, even pre-1.0.

Gate at the squash: `.agent/gate` on `93007ac` rc 0 (clean tree, `heavy`): unittest 2241.3 s, Ran 1060, outer skipped none, nested D28 = L30, D28 15 revisions / 15 replayed (the 0.2.0 `uv.lock` re-keyed every verdict); slowest D28 1920.7 s, L29 183.9 s.

## M3.6a3 close (IMPLEMENT, unit) — target `17896eb` (squash of `archive/m3u6a3-impl`), records in the next commit

Check set fixed before the diff was read, one `reviewer` per lens: correctness C1-C6 + contract O1-O6 (reviewer-18), cleanup L1-L5 (reviewer-19), altitude AL1-AL4 (reviewer-20); target `55588a8` = the branch before its review fixes. Raw tables: `.scratch/review/m3u6a3/` (scratch; rulings restated here).

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| C1-C3, C5, C6 | correctness | pass | deletion = §1 set exactly; `resolve` docstring keeps its rule; 7 battery + 9 repaired tests OK at `55588a8`. |
| C4, O6 | repairs | pass | burden re-measured MAIN-side (contract §4: stage 1 Ran 635 failures=3 errors=18, stage 2 failures=1 errors=7); every reddened id = import repair, inversion (D10) or git-object re-scope; none deleted/skipped. |
| O1 | absence | finding F1 → fixed | `(Outcome,) = (int,)` passed O1's AST collector (O3 caught the token). `_bound_names` walks destructured targets; `def` names count. |
| O4 | structure | finding F2 → fixed | `_top_definitions` skipped `FunctionDef`/`AsyncFunctionDef`: an added top-level function passed. Now enumerated. |
| O5 | preserved ABI | finding F3 → fixed | `default_factory` kept `default` MISSING: `Candidate(output=17)` constructible while O5 stayed green. Requiredness vector added. |
| O2, O3 | exports, residue | pass | 14 in-memory undo controls red (`.agent/decisions/m3u6a3-controls.py <root> controls`). |
| L4 | dead code | finding F4 → fixed | unused `models_module` import (`tests/test_proposal_binding_battery.py:43`, ruff F401 in isolation) + a dead `namespace` in O5. |
| L1-L3, L5 | cleanup | pass | — |
| AL1-AL4 | altitude | pass | `__all__` 57 → 51 (exactly six); root `cement --help` byte-identical (1,443 B, `cmp` rc 0); no human-facing surface names the seven. |

Fix credit: `m3u6a3-controls.py <root> red` (reviewer-18's three gap probes) → failures=3 at `55588a8`, OK at `899d84e`. O5 = preservation pin, UNCREDITED: `.agent/mutate` finds 0 in-scope mutants (post-import trace) → p91. Register: contract §4 placeholder (reviewer-19/-20 R1) → filled before the squash.

Gate at the squash: `.agent/gate` on `17896eb` rc 0 (clean tree, `heavy`): unittest 1149.9 s, Ran 1043, outer skipped none, nested D28 = L30, D28 14 revisions / 1 replayed / 13 from green verdicts; slowest L29 474.4 s, D28 392.0 s (slot-1 load).

## M3.10 gate tooling close (IMPLEMENT, unit) — target `629577d`, review fixes in the commit that lands this section

Check set fixed before the diff was read: correctness C1-C8 + acceptance A1-A6 (reviewer-15), cleanup L1-L8 (reviewer-16), altitude AL1-AL6 (reviewer-17), security S1-S7 (MAIN: scanner config is security vocabulary, kept off the teammate route). Raw tables: `.scratch/review/m3u10/`.

| id | lens | verdict | ruling (MAIN-verified) |
|---|---|---|---|
| C1-C4, C6-C8 | correctness | pass | src edits = typing/lint shape only; `compile`/`resolve`/`verify_function` AST-identical to `e22282f` (reviewer-16); 116 + 8 re-scoped tests OK. |
| A2, C5 | skip census | finding F1 (major) → fixed | `from unittest import skip as not_ready` + `@not_ready` skipped a real test with census rc 0 (reviewer-15); a fourth skip in a nested `tests/nested/` package, which discovery runs, also rc 0 (reviewer-17 F1). Census now `rglob`s and follows rebinding (import-as, assignment, cross-module re-import). Old census rc 0 / new rc 1 on all three seeds; shipped tree rc 0. |
| A3 | register audit | finding F2 (minor) → fixed | a link TARGET holding `simply` tripped the filler count (`[guide](https://example.com/simply-start)` rc 1); filler + counts now read `prose()` (link text kept, target + inline code blanked). Old rc 1 / new rc 0; `simply` in prose still rc 1. |
| AL5 | rules | finding F3 (minor) → fixed | `human-facing.md` claimed the `register` step covers CLI help; it reads Markdown only. Rule corrected; the CLI help gap → p92. |
| A1, A4-A6 | gate, mutate, CI, re-scopes | pass | one command, per-step rc + time, rc 0 only all-green; mutate tally excludes invalid/incompetent from kills; CI push + pull_request + schedule, Dependabot `uv` + `github-actions`. |
| L1-L8 | cleanup | pass + register | R1 full/split dispatch repeats three step lines → ruled no change (explicit step lists read clearer than a selector; CI calls the gate, never restates it). R2 eager `read_text` inside `setdefault` → fixed (miss-only read). R3 mutate docstring named a `skipped` tally it never prints → fixed. |
| AL1-AL4, AL6 | altitude | pass | public library + CLI surface byte-identical after sentinel normalization (57 exports, 35 help nodes, 7 invalid CLI cases); versions single-sourced in `pyproject.toml` + `uv.lock`. |
| S1-S7 | security | pass + register | pinned binary sha256-refused on mismatch; `--log-opts=HEAD` + `fetch-depth: 0`; exact-fingerprint ignores; `uv audit` offline → rc 2 (fail closed); CI `contents: read`, SHA-pinned actions, `persist-credentials: false`, `pull_request` only; every `S` noqa reason true (S608 fragments = code-chosen literals). R1: a cached `.tools/` binary is not re-hashed on reuse (local-only exposure). |

## M4/M5 contract (IMPLEMENT, unit contract before code) — target `.agent/decisions/m45-contract.md` revision 3

Check set fixed before the draft was read: the draft's own §8 questions C1-C8, plus the reviewer's
open rows (X1-X7, capped at 12). `consultant-1` (raw table + re-review = `.agent/decisions/
m45-consultant-1.md`); the advisor read revision 2 before the re-review. Every ruling below = MAIN's,
on the reviewer's evidence re-derived (C3 + X1 repros: MAIN reran the reconstruction-after-revise
probe, rc 0, hash equal; the other repros are cited verbatim in the raw table).

| id | reviewer verdict | ruling + where it lands (revision 3 §) |
|---|---|---|
| C1 | sound-with-change | accepted: recognition = grammatical (G1); exact mode for every other operation; v1 = line-oriented forms (§0, §4). |
| C2 | unsound | accepted as a claim correction: G2 consistency vs G3 no semantic guarantee, the lab counterexample published; owner O6 = the learning pass decides projectability, Read states the assumption (§0, §6 step 2). |
| C3 | unsound | accepted with a MAIN departure (advisor-backed): a newer different output = a revision, never an unpin; contradiction = revocation (P-b), suspension (P-c, now allowed on retired members), `challenge` (P-d); review no longer auto-suspends. Owner O4: pins cross resets (§3, W4, W5, W5b, W5c). |
| C4 | sound | seventh check `projection-uniform`, complete ordered vector pinned (§5). |
| C5 | sound-with-change | accepted: three identities, one read snapshot for switch + receipt + program + evidence, one write transaction for `set_projection` (§3, §5, W10, L9). |
| C6 | sound | accepted: off = every answer field null, syntax-only expected hash, exit 6, switch + operation reads alone (§3, W1). |
| C7 | unsound | owner O7: Cement `source_id` unique per (partition, operation), repeat = exit 4; revision 3: the filter is the single writer after completion, `record_answer` writes nothing (§1 S6, §7, E2-E4). |
| C8 | sound-with-change | accepted: source id, supersession lineage, two-branch switch CHECK, composite receipt FK, program table hash-checked; function ABI v3 lands WITH the cut so no v3-ledger receipt binds a v2 hash (§1). |
| X1 | unsound | accepted: `supersede_examples` (one credit per observation), candidate-program grouping before confirmation, revoke-vs-supersede rule, resumable unfinished work (§2, §6 steps 1-3, X1a-d, LP0). |
| X2 | unsound | owner O8: structured `record_answer` output = the candidate; the final reply = provenance (§7). |
| X3 | unsound | accepted: content identity (`program_hash`) everywhere; identical setting = no-op; compile never revives retired rows (§5, L8). |
| X4 | sound-with-change | accepted: diff covers scope, policy + program; `selected` over full history, `servable` separate (§3, W7, W8). |
| X5 | unsound | accepted: exact program schema, normalized pairs, Unicode scalars, key caps → `NoMatch("key")`, I2/I3 restricted to the grammar's equivalences, work counter in place of two timings (§4). |
| X6 | sound-with-change | accepted: capture binding = `kernel`; real Open WebUI 0.12.3 smoke over hit / miss / off / duplicate / regeneration / two calls (§7, §9). |
| X7 | unsound (added by the reviewer) | accepted: every contrary-evidence path evaluates raw examples under the artifact's own program (§5, X7a). |

Re-review of revision 2 (one round): 9 closed (C1 C2 C4 C5 C6 X2 X4 X6 X7); 6 open (C3 C7 C8 X1 X3
X5) → ruled into revision 3 as listed above; their acceptance = the named predicates, graded when
each unit's battery runs. Register: Open WebUI live delivery, cancellation + metadata keys stay
UNCONFIRMED until M5.3's smoke; P-d cost is measured in M5.1, never assumed.

## p78 close (IMPLEMENT, unit) — target `1935f68` (squash of `archive/p78-impl`), records in the next commit

Check set fixed before re-reading the diff: R1 every input the inner verdict depends on is keyed or
excluded with grounds; R2 red is never recorded; R3 a damaged or foreign record replays; R4 D30's
structure holds (helpers take `root`, one `subprocess.run` site); R5 tripwire census loci unchanged;
R6 p78's acceptance measured; R7 law + records current. MAIN alone (a test-infrastructure cache with
a mechanical seed; a teammate adds no assurance the seed + `D28VerdictCacheTests` miss).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | key completeness | pass + register | key = tree id + `D28_INNER` + `sys.version` + implementation + platform + `sqlite3.sqlite_version` + primary `uv.lock` sha256 (`_d28_content_key`). Excluded with grounds: git version, kernel, locale — environment, not repository content; HEAD's outer suite grades it every run. |
| R2 | red never recorded | pass | `_d28_record` sits after both replay assertions (structural pin `test_d28_records_only_after_both_of_its_assertions`); planted red: 2 runs rc 1, store 12 → 12. |
| R3 | damaged record | pass | `test_a_damaged_or_foreign_record_replays_instead_of_passing`: corrupt, foreign format, foreign key, non-int `ran` → `None`. |
| R4 | D30 structure | pass | `test_d30_every_obligation_reads_the_closed_transition` OK beside the new class; helpers name no `ROOT`/`__file__`; git via `_run`. |
| R5 | census loci | pass | `m3u6a2-tripwires.py --emit` diff = the provenance-only `head` line; not committed. |
| R6 | acceptance | pass | cold 2274.1 s / 12 replays vs warm 306.1 s / 1 replay on `1935f68`; `Ran >= 949` re-asserted on a served verdict; red firing above. |
| R7 | law + records | pass | `history-gates.md` verdict-cache bullet, `ops.md` wall-time + 1036 tests, `gate-checks.md` seed record, p78 status, `Tasks` ticked. |

Red-first credit: `D28VerdictCacheTests` red at `b5257fa` (`archive/p78-impl`, ancestor proven rc 0) by
`uv run python -m unittest tests.test_migration_battery.D28VerdictCacheTests` → `FAILED (failures=1,
errors=4)`. Preservation pins: none cited. Register: the first cold run hit p70's 600 s inner
timeout at `9194f41` under load 13-20; the warm rerun replayed it green.

## ITERATE close (phase, owner's go) — target `d3635b5..6b90eb9`, fixes land in the close commit

Check set fixed before reading: (a) every `Artifacts` entry runs by its recorded command; (b) `Decisions` hold
every owner ruling, each readable without the prototype; (c) every stub, shortcut + hard-coded value reads as
one wherever the owner could take it as real; (d) `spec.md` matches what shipped + passes `.agent/spec-lint`.
(a) = MAIN alone (it holds port 8765); (b)-(d) = `reviewer-1`, 23 seeded rows (validator graded both ways:
seed 23, filled 0), owner rulings O1-O18 handed verbatim; every row below = MAIN's rematch of the bytes at HEAD.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| A1 | artifacts run | pass | `app.py` serving 8765; `capture.sh` rc 0, 10 frames, duplicate check empty; `density.mjs` reset 150/150/12; `run_demo.py` rc 0 `All checks passed.`; `uv run cement --help` rc 0; full gate run 1 at load 9-15 = `FAILED (errors=2)`, both D28 `TimeoutExpired` (`ffe9848`, `adb0ab9`), each green replayed alone (p70 recurrence); rerun `Ran 1031 tests in 2655.256s` `OK`, gate rc 0 (outer skipped none, nested D28 = L30). |
| D1-D9 | rulings held | pass | O1-O11 + O17 each named in `Decisions` / `Intent` (Intent paragraph = the approved text, em dashes kept). |
| D10-D11 | rulings readable | finding F1, fixed | O14 (first caption silent on Provider) + O16 (owner's title) were in code only; the spec's `2-3 word title` contradicted O16 → story bullet rewritten. |
| D12, P2 | no superseded text | finding F3, fixed | ticked rounds r5-r17 + the stale "owner reviews it" → `.agent/archive/iterate-rounds.md`; `Phase` = IMPLEMENT. |
| S1, S3, S4, S6 | stubs labelled | pass | `AI simulated` on the chat half; ask→operation reading labelled in the request disclosure; fixed stand-in scripts in `Decisions` + README; tally / tool ms / cases / switch = runtime values. |
| S2 | learning pass labelled | finding F2, fixed | Default page labelled the chat AI alone → right-half tag `learning simulated` + the Learn beat `(simulated here)`. |
| S5 | renderings labelled | finding F5, fixed | Default `Read` lacked the rendering qualifier the source-view ruling requires → `readable rendering ·` heads it. |
| P3 | Decisions = shipped | findings F1 F2 F4 F5, fixed | Story order now orientation + learn/`Read` in one step (F4); operator view read-only (R1). |
| P4, P5 | README + spec-lint | pass | README walkthrough, frame table, params, third-party match the code; `spec-lint` rc 0. |
| R1 | per-answer controls | finding, fixed | Reviewer lead, rematched: the operator view still offered accept/correct/reject (`renderReview`), manual compile/verify/promote and revoke × — contrary to r12 (a person's ONE act = switching) → removed, the view read-only apart from switches; stale `checked` board wording → `function learned`. |

Register: Back's replay speed (9.3 s across a learn at load ~18) = an owner option, born as `p86`. Library-side
consequences of r12 (learning-pass skill, reviewer identity, per-operation switch, README paragraph 1, docs, CLI
help) = the open `Tasks` library row. Rules upkeep at this close: `ops.md` 22.6 → 12.1 KB, D28/D19 law →
`history-gates.md` (`paths:` tests/examples/m3u6a*), capture + server mechanics → `prototype.md` (`paths:`
prototype/**), two moved-law pointers repointed (`assurance.md`, `p79`).

## `CLAUDE.md` refresh agents@1622ede → agents@4a758e0 (ITERATE, ad-hoc) — target = the diff this commit lands, base `bd78d4e`

Template delta = Alignment law (Collaboration, Execution, Authoring, Engineering, Teammates) moved in
from the user-level file, roles project-local (`.claude/agents/`), `upstream-sync.md` retired, + NEW
gate command, UI design, charts, run-the-real-app, code diff lenses, survivor rulings, UI copy.
`reviewer-1`, 11 lenses fixed before dispatch, primary tree read-only (`git diff HEAD` sha256
`19dc81ce…` unchanged over its run), its own clause map C01-C28 built before MAIN's O-map.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | template fidelity | pass | `cmp` rc 0: `CLAUDE.md`, `.agent/spec-lint` (mode 755), 6 roles vs agents@4a758e0. |
| L2 | obligation coverage | finding F2 (minor), fixed | C01-C28 ⊆ MAIN's map; read cost control = moved (old global `Reading`), not new. |
| L3 | old-form completeness | pass | 30 forms, each with a `git grep HEAD` or old-global control; live = p68/p69 (subject = the retired file, status lines) + p73 (historical section titles). |
| L4 | `upstream-sync.md` migration | finding F1 (minor), fixed | per-close review → `ops.md` (3); `attack`/`mut` + `tester` two counts → `assurance.md`; upkeep backlog → spec; F1's two clauses → `ops.md` Layout + `assurance.md` Waves. |
| L5 | spec preservation | pass | 14 `Tasks` rows + ordered unit/`p<nn>` tokens `cmp` rc 0; `Intent`/`Decisions`/`Phase` byte-equal; spec-lint rc 0. |
| L6 | check strength | pass | D25, D29, L23 clean OK + red on seeds before = after; grader 10 seeds same verdicts; `.agent/gate` clean 0, missing module 1, below-3.12 shim 0 + notice. |
| L7 | portability | pass | remaining machine names = owner-ruled prototype QA (`ops.md` Template rulings (4), p79); project `CLAUDE.md` section pointers = local law. |
| L8 | queue soundness | findings F3 + F4 (minor), fixed | grader PASS, 81 rows; p78-p81 anchors re-derived. |
| L9 | law consistency | finding F4, fixed | survivor open row matches `CLAUDE.md` `Engineering`; p80 had contradicted `ops.md` Layout's absence rule. |
| L10 | code diff lenses | finding F2, fixed | gate keeps the 3-step chain + rc fold; prototype tools change dependency selection + preflight alone. |
| L11 | claim soundness | findings F2 + F4, fixed | numbers re-derived; F2's unconditional timing claim + F4's absence claim corrected. |

- F1 `upstream-sync.md` held two repo-only clauses: `Tasks` rows carry acceptance + binding notes as
  indented sub-bullets; `general-purpose` briefs order the validator LAST → `ops.md` Layout +
  `assurance.md` Waves (`rg -Fn` 1 hit each).
- F2 `.agent/gate` printed no slowest tests on Python 3.11 (admitted by `pyproject.toml`) while
  `ops.md` promised them unconditionally → notice line + `ops.md` qualifier + Fast gate key; `uv`
  shim proof rc 0 + notice.
- F3 p79's `sha256sum … | uniq -d` passes identical frames (paths differ per line) → the standing
  hash-only sorted pipeline.
- F4 p80 asserted the absence of gitignored captures → `no committed phone-width check (capture.sh
  captures at --width 1600 alone)`.
- Post-review, MAIN: p82 born (the demo leaks its temporary ledger on SIGTERM, found while driving
  it) + p70 recurrence evidence (full-gate run 1); grader PASS, 82 rows.

## `CLAUDE.md` refresh agents@5e03db6 → agents@1622ede, second pass (ITERATE, ad-hoc) — target = `adb0ab9` (`e4e7016..adb0ab9` + its commit message)

Owner request (resumed session): rerun this session's teammate work on the new teammate model ⇒ the first pass below (`reviewer-1`, gpt-6.1-sol, 10 lenses, pre-commit diff) re-ran as `reviewer-2` on gpt-6-astra in a fresh context over the committed refresh: L1-L10 as before + L11 record soundness (the commit body, the first-pass section, `gate-checks.md`), fixed before dispatch; primary tree read-only, its firing in two disposable detached worktrees (`adb0ab9`, `e4e7016`), both removed. MAIN found F2 before dispatch and withheld it from the brief as a calibration probe; reviewer-2 found it independently. Each row's basis = MAIN's own rerun, MAIN's first-pass firing (recorded in `adb0ab9`'s body) or an anchor rematch at `adb0ab9`; a measurement only reviewer-2 ran is labelled `reviewer-2`.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | template fidelity + `last-sync` | pass | `cmp` of `adb0ab9:CLAUDE.md` + `adb0ab9:.agent/spec-lint` vs upstream rc 0 each, mode 100755; `last-sync = agents@1622ede` 1 occurrence; upstream `1622ede..HEAD -- claude/` = 0 commits. |
| L2 | obligation coverage | finding F1 (minor), fixed | `.agent/spec.md:84` (`Decisions` gate-tooling ruling) still routed future `firing seeds → .claude/rules/ops.md`, the carrier O3 retired (global `Engineering` 7d76c2c, `ops.md` Purpose-built); present before the refresh (`git show e4e7016:.agent/spec.md` rc 0, 1 hit) and missed by it → `firing seeds + records → .claude/rules/gate-checks.md, its paths: extended to the new check files`; grounds + config stay in `ops.md`; the owner-ruled tooling choices are unchanged. |
| L3 | old-form completeness | finding F1, fixed | reviewer-2's 33-form sweep, each control count named first: 8 live lines = F1, D25's verbatim M3.5b CONTRACT quote (`tests/test_cli_removal_battery.py:3078-3079`, superseded by its RULED-BY paragraph), 4× `over-capacity` (the 50,000-entry bound), `upstream-sync.md:80` (Superseded record). MAIN's sweep missed F1's form + the quote's spelling. |
| L4 | spec preservation | pass | `e4e7016 → adb0ab9`: 5 sections, 14 `Tasks` rows, 39 unit-id occurrences (30 distinct), `Intent`/`Artifacts`/`Decisions`/`Phase` byte-identical, 3 lines changed; the F1 fix vs `adb0ab9`: `Decisions` alone changes, `Tasks` sha256 `d222e36d…` + the unit-id sequence identical (MAIN; reviewer-2's `Tasks` hash agrees). |
| L5 | check strength | pass | reviewer-2's 91-observation matrix at `e4e7016` vs `adb0ab9` (text 22, pins + pairing 27, queue 26, gate records 16), every outcome as ruled + equal to MAIN's first-pass firing; M45 killed in both catalogue versions (MAIN first pass + reviewer-2). Beyond the first pass, rerun by MAIN: a second sentence on `Phase` line 1 → `e4e7016`'s spec-lint rc 1 (`one phrase`), the upstream copy rc 0; D19 composition seed on `adb0ab9` (`SWAPPED_ROOTS` → `("cement_runtime",)`) with `tests.test_hospital_ocr_example` composed → `FAILED (errors=1)`, `CandidateSourceError: candidate source failed`, D19 alone under that purge rc 0, pristine rc 0 (reviewer-2: rc 1 at `e4e7016` too). |
| L6 | deferral queue | pass | grader rc 0 at `adb0ab9`: 61/61, `COMMITTED-FLOOR: 77 over 9 revisions`, 77 rows, 0 missing/unparsed/unknown/bad; p76's 26/268 reproduced; p66 = the skip at `:1951`; p68 rc 1, control rc 0. |
| L7 | rules shape | pass | 7 frontmatters parse; `gate-checks.md` `paths:` = its 5 check files; invariants 9 → 10, index 14 → 16, repo-measured 7, Superseded 16 → 20. |
| L8 | consistency + register | finding F1, fixed | `spec.md:84` disagreed with `ops.md:5` + `upstream-sync.md:40` on the seed carrier; the F1 fix aligns them; one H1 per changed Markdown file. |
| L9 | step 6 settings | pass | `settings.local.json` env = 2 keys, hook = Headroom selfheal; no `settings.json`, no `.claude/agents/`. |
| L10 | composition | pass | MAIN: the full gate's D28 replayed `1764c66` (tree `e7709e2b` = `adb0ab9`'s) green (`adb0ab9` body); reviewer-2's inner replay of `adb0ab9`'s exact tree (instrument unlinked, `CEMENT_D28_INNER_REPLAY=1`): `Ran 1000 tests in 317.728s` `OK (skipped=1)`, load 1.96 → 4.14; AST census: 1031 ids + the same 3 conditional skip sites at both revisions (L30 `:1948` → `:1951`). |
| L11 | record soundness | findings F2 + F3 (minor), fixed | F2: the first-pass L10 row + `adb0ab9`'s body call the replayed tree `ac5ddfeb` this commit minus its review section; `git diff --stat ac5ddfeb adb0ab9` = 4 files → corrected below. F3: `gate-checks.md`'s read-census record named `line 2684`, carried from `ops.md` and stale on both sides; MAIN rerun on `adb0ab9` = `['line 2206: UPDATE operations SET revision = revision']` rc 1, file restored sha256-equal, pristine rc 0 → record = 2206 + its locus rule. M3 (MAIN, from reviewer-2's N11): the body + first-pass L5 say 163 catalogue anchors in edited files; recount = 6 in edited files (`tests/test_cli.py` 4, `tests/test_cli_channels_battery.py` 2) + 157 in the seed-planted `README.md` 6 + `src/cement_runtime/cli.py` 151; reviewer-2: all 268 anchored rows keep their counts `e4e7016 → adb0ab9`. |

Corrections to the first-pass section + `adb0ab9`'s body, both kept as written: `ac5ddfeb` = `adb0ab9` minus p77 (`.agent/deferred.md`), the review section, `gate-checks.md`'s p77 sentence + 76 → 77 floors and `upstream-sync.md`'s p77 clause; no test reads `.agent/review.md`, `gate-checks.md` or `upstream-sync.md` (`rg` rc 1 each); D25 reads the whole `.agent/deferred.md` but asserts on p12's entry alone (reviewer-2's qualification), byte-identical in both trees (awk-extracted entry sha256 `55d9ba90…` both) ⇒ the replay evidence holds, and L10 replays the exact tree. The 163 = the M3 split above.

Re-review round 1 (`reviewer-2`, rows F1 F2 F3 M3 T1, each against its acceptance check alone): 5/5 resolved, none regressed; reviewed working diff sha256 `786cfc90…` = MAIN's tree at harvest. After the round MAIN edited this section alone: this line, reviewer-2's F2 qualification adopted, MAIN reruns added to L4 L5 L10 + the basis sentence; `.agent/spec.md` + `gate-checks.md` stay as reviewed.

## `CLAUDE.md` refresh agents@5e03db6 → agents@1622ede (ITERATE, ad-hoc) — target = the diff this commit lands, base `e4e7016`

Template delta = deferral queue `one entry + acceptance check each` (b6a6cf3) + `Rules upkeep` (7d76c2c); global delta = check firing + scratch-validator regeneration → `paths:` rules, rule = law + why, strict text caps out of guidance + checks, `Human-facing` `short sentences`, brief parts `one entry` (7d76c2c, b6a6cf3); `claude/spec-lint` one-phrase check dropped (b6a6cf3). Owner rulings this pass carries: R1 word caps dropped now, full cascade (D25, D29 + the `function eval` help test keep the filler ban; L23 ×2 + L29 census 16 → 15, pruned 15 → 14; `m3u6a2-tripwires.json` re-emitted; M3.5b's M45 re-aimed at a filler seed); R2 queue grader byte floors dropped; R3 grader parses entries (row line + indented lines). Reviewer = `reviewer-1`, 10 lenses fixed before dispatch, primary tree read-only (its binding = tracked diff sha256 `73f6f54c…` + `gate-checks.md` `897daff2…` = MAIN's tree at harvest); every row below = MAIN's own rerun. MAIN-found after the pass, M1: global `Authoring` `a multi-step recipe → a committed script` had no carrier for the firing recipes moved into `gate-checks.md` (fired this session by gitignored scratch harnesses) → p77 born, named by `gate-checks.md` + the upkeep index row; MAIN re-check = grader rc 0 (77 rows) + both anchors present.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | template fidelity + `last-sync` | pass | `cmp` `CLAUDE.md` + `.agent/spec-lint` vs upstream rc 0 each, mode 755; `last-sync = agents@1622ede` = `upstream-sync.md:14`, 1 occurrence; upstream `1622ede..HEAD -- claude/` = 0 commits. |
| L2 | obligation coverage | pass | `one entry` → queue header + grader `HEADER` + entry parse, `ops.md` Layout, spec `Tasks` pointer, `upstream-sync.md` spec invariant + index; `Rules upkeep` → invariant + index mechanics row (first due at the ITERATE close, backlog named) + the phase-close row runs after it; firing records → new `gate-checks.md` (`paths:` = the 5 check files), scratch-validator regeneration → `human-facing.md` (`paths:` on its surfaces), `assurance.md` restatement deleted; text caps → R1 + R2; brief parts, consultant cap, `implement.md` step 2, ScheduleWakeup, marketplace stamps → no repo carrier (step 2's results-out-of-rules = the upkeep backlog). |
| L3 | old-form completeness | pass | `rg --hidden -g '!.git' -g '!.scratch' -n -F` over 32 forms from the root, `.agent/decisions/*.py` classed live (reviewer's L3 point, adopted) → 8 live hits, each justified: `last-sync` line, Superseded record, 4× `over-capacity` (the 50,000-entry function bound), p40's past-tense M3.1 measurement, p68's defect evidence; every form has a nonzero control (history, pre-refresh `git grep HEAD`, or upstream `5e03db6`); retired-flow invariant names = HEAD's counts. |
| L4 | spec preservation | pass | `preserve.py HEAD` rc 0: 5 sections, 14 `Tasks` checkbox rows + 39 unit ids (30 distinct) identical, `Intent`/`Artifacts`/`Decisions`/`Phase` byte-identical, 3 permitted lines changed; seeds (row drop, `Decisions` word, unit rename) rc 1 each. |
| L5 | check strength | pass | Seeds at `e4e7016` vs the refresh tree (`ee01a93`; later edits = p66 re-anchor + M45 note, neither read by a fired check): filler seeds red both sides (D25, D29, help); cap seeds red → green (R1); root-description filler green → red (D25 now bans filler there); p12 anchor red both; p12 entry split red → green (R3); L23 freeze token + foreign pin red both, ruling token red after; L23-all pin drop red both (16 / 15); L29 + tripwires seeded pin red both; pairing P1/P2 = 5 failures both, P3 `OK (skipped=1)` both; queue grader 12/12 as ruled (G7/G8/G9 flip); M45 killed both sides (`m3u5b-mutants.py --id M45`, control GREEN); spec-lint seed `:116` both, `:115` before only; m3u5a/m3u5b/m3u6a2 shape validators PASS; 163 catalogue anchors in edited files at HEAD counts. |
| L6 | deferral queue | pass | grader rc 0: `ARCHIVE-ROWS: 61 of 61`, `COMMITTED-FLOOR: 75 over 8 revisions`, `QUEUE-ROWS: 77`, 0 missing/unparsed/unknown/bad; p12 / p40 / p75 keep their obligations, length reported never capped; p76 born (26 of 268 catalogue anchors at count 0); p77 born after the pass (MAIN-found M1, below); p66 anchor `:1948` → `:1951` (the L23/L29 lines moved L30's skip); p68's acceptance now holds (`rg -F 'last committed queue' .claude/rules/` rc 1). |
| L7 | rules shape | pass | 7 rule files, frontmatter parses (PyYAML); `gate-checks.md` `paths:` = the 5 files its records name; moved = `ops.md` Purpose-built seeds, grader seeds, D28 pairing + D19 seeds (`ops.md` 22369 → 20497 B), counts refreshed to the after run; `upstream-sync.md` invariants 9 → 10, index 14 → 16, repo-measured 7, Superseded 16 → 20. |
| L8 | consistency + register | pass | entry definition + every-revision floor + R2 grading read alike in grader docstring, `HEADER` = queue header (grader prefix check), `ops.md` Layout, `upstream-sync.md` THE QUEUE + index, spec pointer; census 15/14 alike in L23, L29, `ops.md` D28 bullet, `upstream-sync.md`; one H1 per Markdown file; `git diff --check HEAD` rc 0. |
| L9 | step 6 settings | pass | `.claude/settings.local.json` env = `ANTHROPIC_BASE_URL` + `ENABLE_TOOL_SEARCH`, hook = Headroom selfheal; no `.claude/settings.json`, no `.claude/agents/` ⇒ nothing removed. |
| L10 | composition | note N10, resolved | Reviewer: full D28 replay of this revision unconfirmed (outside its brief). MAIN: D28-style inner replay of the refresh tree `ac5ddfeb` (= this commit minus this section; instrument unlinked, `CEMENT_D28_INNER_REPLAY=1`, `PYTHONPATH` = tree + `src`) = `Ran 1000 tests in 539.842s` `OK (skipped=1)` rc 0 (skip = L30: the two `/proc` frames run on this host; 539.8 s under a competing Verus/z3 load ≈ 10 on 8 cores, D28's per-revision limit = 600 s); the full gate with D28 replaying this commit = the commit body. |

## `CLAUDE.md` refresh agents@eac5295 → agents@5e03db6 (ITERATE, ad-hoc) — target = the diff this commit lands, base `b8a0703`

Template delta = `# Alignment` → `# Phase flow` (Collaboration, Authoring, Engineering, research,
briefs, Git, read cost → global `CLAUDE.md`), `Routing` + `Routed state`, spec bullet (`Intent`
human-facing, `Phase` = state alone, `.agent/spec-lint`), PROTOTYPE + ITERATE quick loop, IMPLEMENT
greenfield, per-depth Teammates + Advisor; 15 `claude/` bodies. Reviewer = `reviewer-1`, 10 lenses
fixed before dispatch, primary tree read-only for both rounds (first pass tree `49d8d92`, re-review
`ebc17e3`; its tracked-diff + new-file hashes equal before = after each round); every row below =
MAIN's own rerun. Owner ruling this pass carries: 614a667 mutation-tool credit = adopted, tool
queued (p74).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | template fidelity + `last-sync` | pass | `cmp` `CLAUDE.md` + `.agent/spec-lint` vs upstream rc 0 each, mode 755; `last-sync = agents@5e03db6` = `upstream-sync.md:14`, 1 occurrence; upstream `5e03db6..HEAD -- claude/` = 0 commits. |
| L2 | obligation coverage | finding, fixed | Reviewer's independent D01-D22 = MAIN's map except D16: `fdf950f`'s steered finish-line migration unmapped (F1) → O22: carrier = upstream `prompts/steered/`, no repo copy; live law follows (`upstream-sync.md` phases invariant, ITERATE index row, Superseded ITERATE line; `ops.md` census: a round's revision editing `.agent/spec.md` owes `.agent/spec-lint`). MAIN-found F2: the `Intent` (human-facing) register half was unmet, `Decisions` classing it agent-optimized → that line names `Intent` human-facing + ungraded, p75 queues the existing text (4 of 7 sentences over 25 words, 2 with ` = `). Re-review round 1: F1 + F2 resolved. |
| L3 | old-form completeness | pass | `rg --hidden -g '!.git' -n -F` over 38 forms + `last-sync = agents@` from the root → live = `upstream-sync.md:14` (last-sync) + `:73` (Superseded `SUSPENDED INTACT`); history = `review.md:26` + `:45`, `archive/iterate-rounds.md:18`, `archive/memory.md:3`; controls: 36 forms in pre-refresh `git grep HEAD`, 2 in history. Reviewer's 23 extra forms → rc 1. |
| L4 | spec preservation | note, fixed | Archive = `Phase` verbatim (`cmp` vs `b8a0703` lines 115-215 rc 0); spec above `Phase` vs `b8a0703` = 3 hunks (`16c16` Gate, `83c83` `Intent` human-facing, `90a91` M3.6a3 resume note); 14 `Tasks` checkbox rows identical; 30 unit ids, 0 lost. N1: the first helper counted the permitted Gate edit as lost history (false rc 1) → containment scoped to `Phase`, Gate + `Decisions` edits asserted exactly; archive-drop / Artifacts-drift / Decisions-drift seeds rc 1 each, clean rc 0. |
| L5 | check strength | pass | `.agent/spec-lint <(git show b8a0703:.agent/spec.md)` rc 1 (`:115`, `:116`), working spec rc 0; queue grader header pin before = clean 0 / one-word drift 1, after = clean 0 / drift 1 / OLD header vs new pin 1; `tests/ src/ examples/ prototype/` diff empty (control `.agent .claude CLAUDE.md` = 8); gate run 1 on `49d8d92` `Ran 1031 tests in 1847.267s` `OK`, `uv build` rc 0, `.agent/spec-lint` rc 0. |
| L6 | deferred rows | pass | grader rc 0 `VERDICT: PASS`, 75 rows; p74 (mutation tool, `pri=2`) + p75 (`Intent` register, `pri=4`) born ascending; p67 `behavioral reference` → `owner-ruled view`; p72 accept follows `Phase` = state alone; p71 + p72 accept commands hold (rc 1 each). |
| L7 | `upstream-sync.md` shape | pass | frontmatter = HEAD's (`cmp` rc 0); invariants 9 → 9, each tracing to a current `CLAUDE.md` clause; index 13 → 14 (5 verbatim, 7 re-keyed to global or current template clauses, the `State` row → the spec's routed state, + mutation-tool + spec-lint rows); Superseded 14 → 16. |
| L8 | law conflict + register | pass | mutation credit reads the same in `assurance.md`, `ops.md` Commits, `upstream-sync.md` index + Superseded, p74; gate = unittest + `uv build` + `.agent/spec-lint` in `ops.md` Env, spec `Artifacts`, queue header + grader `HEADER`; `git diff --check HEAD` rc 0; one H1 per edited or new Markdown file. |
| L9 | step 6 settings | pass | `.claude/settings.local.json` env = `ANTHROPIC_BASE_URL` + `ENABLE_TOOL_SEARCH`, hook = Headroom selfheal; `.claude/agents/` absent ⇒ nothing removed. |
| L10 | routed state | pass | `Phase` = `ITERATE — whole product` / `> I want to return to the ITERATE stage` (the owner's message, session `08cfd0c7`, 2026-09-10T01:38:21Z) / `Suspended: IMPLEMENT — whole product`; resume note on M3.6a3; `.agent/spec-lint` rc 0; fresh `claude -p` context-only probe: 0 tool calls, answer = IMPLEMENT + M3.6a3. |

## `CLAUDE.md` refresh agents@4d22203 → agents@eac5295 (ITERATE, ad-hoc) — target = the diff this commit lands, base `604bf9b`

Template delta = 4 hunks (`Execution` research, `Authoring` pasted-prompt flaw, `Engineering`
`data` tier, `Session flow` Teammates + Advisor) + 6 `claude/` bodies. Reviewer = `reviewer-1`, 9
lenses fixed before dispatch, tree frozen for the run (`git diff HEAD` sha256 `8a60225b…` before =
after); every row below = MAIN's own rerun. Owner ruling this pass carries: unit-close review =
fit form (`upstream-sync.md` index row, `spec.md` `Tasks` phase-close sub-bullet).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | template fidelity + `last-sync` | pass | `cmp CLAUDE.md ~/.local/app/agents/claude/CLAUDE.project.md` rc 0; upstream HEAD `eac5295`, `eac5295..HEAD -- claude/` = 0 commits; `last-sync = agents@eac5295` = `upstream-sync.md:14`, 1 occurrence. |
| L2 | obligation coverage | pass | Reviewer's independent map = MAIN's O1-O7 + migrations (9baf749 `Trigger =` → `Fit =` → rules `teammate fits` / `global fits`; e285415 steps 8-9 leave the cited steps 1 + 7 intact); each lands as practice, the Teammates invariant, a Superseded line or the owner-ruled index row (commit body lists each). |
| L3 | old-form completeness | pass | `rg --hidden -g '!.git' -n -F -f forms.txt .` (23 forms) → `upstream-sync.md:62` + `:71`, both Superseded; reviewer's 11 extra forms → rc 1; 20/23 forms hit pre-refresh `git grep HEAD`, the 3 global-only forms hit `agents@4d22203` `claude/` 3/2/2. |
| L4 | spec preservation | pass | id census before = after (`cmp` rc 0: 5 headers, 12 checkbox rows, M-ids, p-ids); `Intent`/`Artifacts`/`Decisions`/`Phase` byte-identical; one sub-bullet reworded to the owner ruling. |
| L5 | check strength | pass | No gate, test or validator edited (`diff --name-status HEAD` = 3 instruction files); no `tests/`/`src/`/`examples/`/`prototype/` module reads them (`rg` rc 1, control `hospital_ocr` rc 0); gate run 1 `Ran 1031 tests in 1746.607s` `OK`, `uv build` rc 0. |
| L6 | deferred rows added | pass | `.agent/deferred.md` `cmp` HEAD rc 0 ⇒ none; queue grader rc 0 `VERDICT: PASS`. |
| L7 | `upstream-sync.md` shape | pass | frontmatter lines 1-4 = HEAD (`paths: ["CLAUDE.md"]`); one `last-sync` line; index rows 12 → 13, every prior row byte-preserved (`comm -23` = 0); both `prompts/{auto,steered}/refresh.md` exist. |
| L8 | law conflict + register | pass | Every close keeps its own pass ⇒ the preamble above holds unchanged; dispatch per case at the template count; `git diff --check HEAD` rc 0; one H1 per edited file. |
| L9 | step 6 settings | pass | `.claude/settings.local.json` env = `ANTHROPIC_BASE_URL` + `ENABLE_TOOL_SEARCH`, hook = Headroom selfheal; `.claude/agents/` absent ⇒ nothing removed. |

## `CLAUDE.md` refresh agents@2cedb4f → agents@4d22203 (ITERATE, ad-hoc) — target = the diff this commit lands, base `1623535`

Template delta = 4 hunks (`Execution` research, `Engineering` tier, `Session flow` ITERATE +
phase-keyed teammates + advisor) + 12 `claude/` bodies. Reviewer = `reviewer-1`, 10 lenses fixed
before dispatch, tree held frozen for the run (4 modified files, unchanged across it); every row
below = MAIN's own rerun. Gate result → this commit's body (message-only amend, tree unchanged).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| R1 | template fidelity + `last-sync` | pass | `cmp CLAUDE.md ~/.local/app/agents/claude/CLAUDE.project.md` rc 0; upstream HEAD `4d22203`, `4d22203..HEAD -- claude/` = 0 commits; `last-sync = agents@4d22203` = `upstream-sync.md:14`. |
| R2 | obligation coverage | pass | Reviewer's independent U1-U9 map ⊆ MAIN's C1-C8 + migrations; each lands as practice or an `upstream-sync.md` invariant/index/Superseded line (commit body lists each). |
| R3 | old-form completeness | pass | MAIN's 15 forms + control `agents@c38a706` → 2 hits (`upstream-sync.md:14`, history `review.md`); reviewer's 25 extra forms rematched by MAIN → 8 hits = `upstream-sync.md:68-69` (Superseded / substring of the new form) + 6 history paths under `.agent/archive/` + `.agent/decisions/`. |
| R4 | spec preservation | pass | id census before = after (`cmp` rc 0), 12 checkbox rows, `Intent`/`Artifacts`/`Decisions`/`Tasks` byte-identical; `Phase` keeps the start command, prototype-only carve-out + capture obligation, adds the `iterate.md` body + close gate. |
| R5 | check strength | pass | No gate, test or validator edited; no `tests/`/`src/`/`examples/` module reads `CLAUDE.md`, `spec.md`, `review.md` or `.claude/rules/` (`rg` rc 1), the one `deferred.md` reader selects `p12` alone (`tests/test_cli_removal_battery.py:3300`); queue grader rc 0 PASS 73 rows. |
| R6 | claim soundness | pass | `p73`: `git log a8109eb..1623535` = 17 commits, none named by a section; `Teammates:`/`dispatch:`/neither split rematched per SHA; `capture.sh:14-15` defines `BASE` + `OUT`. |
| R7 | law conflict | pass | New text = repo mechanics + refresh invariants; the prototype-only no-gate carve-out holds per round, the close gate comes from `iterate.md` `Met when`; screenshot stays gitignored QA. |
| R8 | `upstream-sync.md` shape | pass | `paths: ["CLAUDE.md"]` kept, one `last-sync` line, Recipe → `~/.local/app/agents/claude/prompts/{auto,steered}/refresh.md` (both exist). |
| R9 | step 6 settings | pass | `.claude/settings.local.json` env = `ANTHROPIC_BASE_URL` + `ENABLE_TOOL_SEARCH`, hook = Headroom selfheal; `.claude/agents/` absent ⇒ nothing removed. |
| R10 | register | pass | `git diff --check HEAD` rc 0; one H1 per edited file; no provenance in added law. |

## `CLAUDE.md` refresh (ITERATE, ad-hoc) — target = the single commit landing the refresh

Target = `a8109eb`, upstream `agents@c38a706`, scope = the fold of the new `Engineering` bullet
(`Verification integrity`) plus every downstream binding it drew. The lens set was fixed in the
target before dispatch and no lens was added, dropped or reworded after a finding appeared.
Reviewer = `rev-sync-1`, read-only, its verdicts raw material; every anchor below is MAIN's own
rematch against `a8109eb`. Gate at the target, rerun whole by MAIN: `Ran 1031 tests in 1113.706s`
`OK` rc 0 + `uv build` rc 0, outer skipped none, nested D28 = L30, missing = the five unconfigured
checks.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | upstream fidelity — the tracked template equals upstream byte for byte, the fold adds exactly upstream's delta and reverts no downstream law, and `last-sync` names a revision whose range holds every unfolded template/prompt commit | pass | MAIN's own: `git -C ~/Projects/agents show c38a706:claude/CLAUDE.project.md \| cmp - CLAUDE.md` rc 0, upstream tree clean and its file equal to its own HEAD blob; `539ca8b..c38a706 -- claude/CLAUDE.project.md claude/prompts/` = `da7c64d` alone; the fold is 1 added line, 0 removed, `cmp`-identical to `da7c64d`'s own added line ⇒ nothing downstream was reverted, and the earlier extraction that reported both sides empty was a pattern defect (`^[+-][^+-]` rejects `+-`), rerun with `^\+` minus `+++`. |
| L2 | binding completeness — each clause of the new bullet reaches a `.claude/rules/` file with this repo's mechanics, or the record states why it needs none | finding, fixed | CONFIRMED, reached independently by MAIN and the reviewer: clauses (b)-(f) had mechanics, clause (a) — implementation scope with `prototype/` under PROTOTYPE law — had none. Fixed with the MEASURED exclusion rather than a restatement: no module under `tests/` names `prototype`, the wheel carries `cement_runtime` + dist-info alone, the sdist carries `docs`, `examples`, `src`, `tests` and no `prototype/` ⇒ it is outside every check, and the ruled boundary inside the demo (provider simulated + labelled, lifecycle/digests/timings from the real runtime) is what keeps a permitted shortcut from becoming a false claim. Clause (c) was half-bound too and MAIN closed it in the same edit: the domain OUTSIDE the entry set is contracted as an inert miss, M4's projection the only widener. |
| L3 | claim soundness — every fact the new prose asserts is measured at this tree: the skip census is complete, the named missing checks are absent, and each cited symbol, path, line and environment variable is spelled as shipped | finding, fixed | THREE defects, all rematched by MAIN. (i) `function verify` was named as the sealer; it is read-only (`src/cement_runtime/system.py:2878` `Verify one committed promoted-set snapshot without mutation`) — `_function_entry_seal` (`:199`) derives the seal from artifact + report, `_function_report_member` (`:2287`) recomputes it and raises `IntegrityError`, `function_hash` binds the whole normalized table (`function.py:256`). (ii) The witness rule spelled the tag `archive/<unit>-impl`, a FAMILY not a tag: `git merge-base --is-ancestor 05f7ce4 archive/m3u6a2-impl` rc 1 while `archive/m3u6a2-impl-3` rc 0, so the generic form walks a successor into unrelated history — now the exact tag plus an ancestry proof, and the pre-existing same-shape error at the branch rule (`ops.md` History-walking gates) fixed with it. (iii) `skip off-Linux` dropped half the guard: both decorators require `sys.platform.startswith("linux") and pathlib.Path("/proc").is_dir()`, so a Linux container without `/proc` skips them, and `subreaper frames` misnamed `test_outer_watchdog_kills_adapter_if_supervisor_dies`. The census itself held: widened sweep for `SkipTest\|load_tests\|expectedFailure\|@skip` over `tests/ src/ examples/ prototype/` adds nothing, and `tests/test_lifecycle_removal_battery.py:1397` asserts `expectedFailures == []`. The five missing checks are real (`pyproject.toml` has no `[tool.ruff]`/`[tool.mypy]`, `.github` absent). |
| L4 | claim-vs-guarantee gap — no green claim, old or new, certifies more than was run, and the `Phase` record of the M3.6a2 close stays true of THAT run | finding, fixed | CONFIRMED and the sharpest row. `skipped = none` read the OUTER runner as the whole gate: D28 exports `CEMENT_D28_INNER_REPLAY=1` around its loop (`tests/test_migration_battery.py:1600`), unlinks its own module from each checkout, and L30 therefore skips in EVERY inner replay by construction — recorded as `announced + pruned -> OK (skipped=1)` at `.agent/decisions/m3u6a2-closure-gates.log:141` — while D28 asserts inner rc plus `Ran >= 949` (`:1627`) and propagates no skip count. The outer `OK` is true of the outer runner and silent about the nested one, which is the same composition blindness that hid D28 and D19. Both the `Phase` record and the standing values now read `outer skipped none, nested D28 = L30`. |
| L5 | law conflict — the new text contradicts no standing rule in the files it lands in, and duplicates none of them across scopes (the D28 `skipTest` seed, `REPORTED never forced`, the `CLAUDE.md`-versus-rules routing split) | finding, fixed | TWO valid halves, one pass. (i) Duplication: the bindings opened by restating the generic mandate that `CLAUDE.md` already carries in every context, which the file's own recipe forbids — upstream advances, the local copy stays authoritative and stale. Both restatements now cite the clause and keep only the measured half. (ii) The `skipTest` seed carve-out claimed transience `by construction`, which the squash does not deliver: a squash takes the branch TIP's tree, so a seed still present at the tip lands on `main` as an ordinary fourth member. Rewritten to make removal part of the unit that added it. The preservation collision is a PASS — `REPORTED never forced` survives intact, the mutation criterion carrying the preservation credential instead of a forced baseline red. |
| L6 | repo-state integrity — the queue grades clean, no committed check reads an edited path in a way this diff reddens, and the retired-name sweep plus every tree census stay satisfied | pass | MAIN's own: queue grader rc 0 `VERDICT: PASS`, QUEUE-ROWS 65 → 66, UNKNOWN-ROWS 0, THIN-CELLS 0; seven modified paths and zero additions, so no tree census gains a member; the one test reading `.agent/deferred.md` selects the `p12` row alone (`tests/test_cli_removal_battery.py:3299`); retired-name sweep outside archive + decisions = the single permitted full-path spelling, under a positive control hitting the archive 2/1/2. Full gate rerun whole at the target: `Ran 1031 tests` `OK` rc 0, `uv build` rc 0. |
| L7 | register conformance — agent-optimized register on machine-read law, no human-facing surface touched, Marksman-clean markdown, no provenance | finding, fixed | Reviewer's Marksman run over the changed documents returned zero diagnostics under a positive control that produced `Link to non-existent document`, and no human-facing surface changed (`README.md`, `docs/`, example README, CLI help all untouched). Its register objection is upheld: this section's preamble narrated the overwrite and compared itself to the previous pass — provenance the `Authoring` law excludes. Compressed to target, upstream revision, scope, fixation and the gate result. |

## M3.6a2 close (IMPLEMENT, unit) — target = the `main..impl/m3u6a2b` squash content

Delete the lifecycle API (`handle`, `request_status` and the closed call-graph component
serving them), rewrite the four normative documents describing it, and refreeze the
migration battery onto the closed transition (C26/D30). Reviewers = `rev-m3u6a2-1` (rows
L4 L5 L6, then dead of hard context overflow — `Prompt is too long · automatic compaction
failed` — after reading the 6973/1670 diff whole) and `rev-m3u6a2-2`, a narrow successor
carrying L1 L2 L3 L7 with a per-lens read target instead of the range. Both read `968ce79`,
preserved as tag `archive/m3u6a2-rev`; every anchor below was rematched against it.

THE LENS SET BELOW WAS FIXED AND COMMITTED BEFORE ANY REVIEWER READ THE DIFF (`5f712ea`) —
that is what makes this pass terminate. Rows are adjudicated by MAIN; a reviewer verdict is
raw material, re-derived here, never credited. A finding inside the unit's acceptance
contract is fixed before this close; anything outside it is born as a `.agent/deferred.md`
row.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | deletion completeness — every deleted symbol has zero live producers, and each residue predicate is paired with a STRUCTURAL pin, since a rename satisfies every residue grep while the code stays | pass | Five raw-source residue predicates (`_lease_us`, `generation_lease_seconds`, `lease-safe`, `invalidated_generators`, `ambiguous active scope` at `tests/test_lifecycle_removal_battery.py:348,406,437,540,2008`) — all five anchors rematched by MAIN. Each carries a structural companion, re-read line by line: method-set subtraction `:284`, AST comparator identity on `_MAX_SQLITE_INTEGER` `:363`, derived-attribute set `:403`, accepted-max write `:428`, no-`requests`-write regex over the SQL string set `:453`, before/after row equality `:501`, literal-only dynamic dispatch `:583`, parsed model-import set `:610`, event kinds `:637`, deleted-name intersection `:666`. No predicate stands on token absence alone. |
| L2 | preserved-invariant integrity — the neighbours the contract promised to preserve are unchanged, and no behaviour change rode along uncontracted | pass | `git diff --numstat 04e83b3..968ce79 -- src/cement_runtime/system.py` = `2 480`, and `src/` holds no other changed file. MAIN read both added lines: `or now > _MAX_SQLITE_INTEGER` (`system.py:694`) and `raise StateError("clock must return a signed 64-bit microsecond timestamp")` (`:696`). They are not a stowaway — the lease removal deleted the path that previously bounded `now`, so the pair PRESERVES the signed-64-bit clock invariant, and the battery pins it structurally at `tests/test_lifecycle_removal_battery.py:363`. Every deletion is lifecycle imports, lease state, request invalidation, `handle`/helpers or `request_status`. |
| L3 | coverage loss — no suite frame among the 32 repaired lost a check while the gate stayed green, independent of gate 9's own census | pass | Raised as a finding and overturned on re-derivation. D25 did drop `assertEqual(measured, baseline_measured)` (`04e83b3:tests/test_migration_battery.py:1396`) and its peer-frame replay, and now reads the single object `3b7769b` (`:264`). Both halves are CONTRACTED by L26, this unit's own retirement obligation: it requires the figures be DERIVED from `3b7769b` on every run rather than transcribed, and MAIN read its tail — L26 loads all four target ids into a `unittest.TestSuite`, runs it, and asserts `testsRun == 4` with `failures`, `errors` and `skipped` all empty (`tests/test_lifecycle_removal_battery.py:1743-1752`). The replay moved from D25 to L26; it was not lost. The endpoint-vs-baseline comparison is retired by design, because `System.handle` no longer exists to compare. |
| L4 | claim-vs-guarantee gap — every number in the contract, the records and the commit bodies re-derives from committed state, and no claim exceeds what its gate proves | finding, fixed | CONFIRMED and wider than reported. Discovery measures 1031, not 1010; MAIN re-derived it (`unittest.defaultTestLoader.discover` = 1031, migration module 31) and it reconciles exactly with the closure log's own split — gate 1a `Ran 1000` + gate 1b `Ran 30` + `test_d28` = 1031. The stale count lived in TWO live files, `.agent/spec.md:15` and `.claude/rules/ops.md:3`; the archive copy is history and stays. The `~500 s` beside it was also false: 1030 tests measure ~333 s (270.4 + 62.6 at `05f7ce4`) while `test_d28` replays the suite once per revision in its range, so no single figure describes the command. Both files now carry the decomposition and `ops.md` forbids quoting one number. |
| L5 | prose truth — the four rewritten normative documents describe only surfaces that exist, with no stale lifecycle claim surviving and no new false claim introduced | finding, fixed + 1 deferred | CONFIRMED for the claim this unit AUTHORED. `README.md` gained `No public surface names it, and no caller supplies it.` (present in the diff as an added line), which is false: `CandidateRequest` is exported in `__init__.py:68` `__all__`, README's own quick start imports it and types an adapter against it (`:253,:256`), the dataclass field is literally `request_id` (`models.py:64`), the envelope carries it (`source.py:127`), and `docs/adapter-protocol.md:59-61` documents it AND requires an adapter idempotency namespace keyed on `(partition, request_id)`. It also contradicts `.agent/spec.md`'s own ruling that `request_id` STAYS on the `cement-source-v1` envelope. Scoped to its route and the adapter seam named, keeping the committed regex pin (`tests/test_cli_removal_battery.py:2783`) matching — `test_d22a` green after the edit. The reporter's other two anchors are NOT defects of this unit: `docs/threat-model.md:28` and `docs/architecture.md:96` lost their subject when `handle` left but state nothing false, are invisible to gate 3 and L24 alike, and belong to M3.9a/b ⇒ born as `p64`. |
| L6 | refreeze soundness — the migration battery asserts the SAME properties after C26/D30, with no assertion weakened to pass against `dc4ab5e` and the allowlist not used as a bypass | finding, fixed | CONFIRMED. D30 claimed `naming ROOT is the whole predicate` while censusing only the token `ROOT`, so a frame reaching the live tree through `__file__` evaded all four checks — and the idiom was already in the module (`ROOT` itself is built from it at `:38`). No live frame exploited it and no assertion was weakened, so the defect was the overstated guarantee plus a census that fails open on the handle nobody named. MAIN enumerated the reachable handles instead: `ROOT`, `__file__` (now censused at module and frame level against a second allowlist `SELF_READERS`, checked in REVERSE like the first), and an inherited cwd — closed structurally, since `subprocess.run` has ONE call site, inside `_run`, whose `cwd`/`root` carry no defaults, all three now asserted. Five seeds fire, each on its own assertion: `__file__` off-allowlist → `['test_d29_...']`; module-level helper → `['_seed_helper']`; second `subprocess.run` → `2 != 1`; `_run` cwd default → `is not None`; absent allowlist name → `not found in`. Tree restored `cmp`-identical after every seed; D30 green either side. |
| L7 | gate credibility — each of gates 1-10 can actually fail, and every firing seed recorded beside it is real | pass | Reporter judged the recorded seeds without rerunning; MAIN reran the cheap half independently at this tree — gate 2 `GATE 2: PASS` `CORRECTION-BIND: 0 unbound`, gate 4 `PASS (0/5 checks failed)`, gate 5 six checks including both removed-parser controls, gate 6 both tables `in-sync`, all rc 0. Gate 3's credibility is measured, not asserted: `--self-test` reports `CONTROLS: 8/8 firing`, matching the reporter's count from the detector source. Gate 2's `6/6` is C27's repair from this session, gate 9's `11/11` and gates 7/8's `MUTANTS: 15 SURVIVORS: 0` / `ROWS: 30 SURVIVORS: 0` rematched against the closure log. No gate rests on a seed that cannot fire. |

L7 REVERSED by new evidence — gate 10b, the run its own row deferred to `main`. Gate 1 as run
throughout this unit is `discover` MINUS `tests/test_migration_battery.py`, and gate 10a is that
module minus `test_d28`: 1000 + 30 of 1031, with the ONLY gate that grades history excluded from
every numbered rerun, including the "all ten green" one. Run whole from the squash it is
RED — `Ran 1031 tests`, `FAILED (failures=1, errors=1)`, rc 1 — because D28 unlinks the migration
battery from each checkout it grades while four frames of the lifecycle battery read exactly that
file (L23 imports it to execute the pin at `tests/test_migration_battery.py:1426`, L23's body
freeze and L26 read its bytes, L29 counts a working-tree pin scan). MAIN reproduced it at the
branch's own newest in-range revision `05f7ce4` — same 4 errors, same `15 != 16` — so the defect is
STRUCTURAL and pre-existing, not an artifact of the squash. L7's basis was sound for the nine gates
it reran; what it could not see is that gate 1 was never the whole of gate 1. Fixed here: D28
announces its inner replay and the four frames narrow to what the checkout holds, the pairing
checked both ways so a real deletion still reddens (seeds + counts → `.claude/rules/ops.md`). The
repair lands by AMENDING that squash, since D28 grades committed trees and a fix on top would
leave the red revision inside the range forever.

The same split hid a SECOND composition failure, found by the same run: D19 errors
`CandidateSourceError: candidate source failed` when `tests/test_hospital_ocr_example` precedes
it, and passes in 0.169 s alone — gate 1 dropped the whole migration module and gate 10a ran it
alone, so that pairing never existed. `MigrationBatteryTests` swaps `sys.modules` to the
`dc4ab5e` worktree but purged only `cement_runtime`, while the example module imports `pipeline`,
`plan_adapter` and `run_demo` at module scope from the primary tree; those bind runtime classes at
their own import time, the worktree's `run_demo` reuses them, and the resulting candidate is not
an instance of the class the worktree's `System.propose` accepts. `propose` catches `Exception`
and re-raises `from None` by design, so the true cause never reaches the report — the generic
message is what made this look like a load flake, and MAIN first misread it as one on the evidence
of a concurrent job on the same box. Fixed by naming all four roots in `SWAPPED_ROOTS`; seeded
red-before/green-after on the two-module command.

Findings: 4 raised across the two reviewers, 3 confirmed and fixed in this close (L4, L5, L6),
1 overturned on MAIN's re-derivation (L3 — the change it names is contracted by L26, and L26
executes the coverage it reported lost). One reported anchor pair fell outside the unit's
acceptance contract and is born as `p64`; `p65` records a queue-grader defect found while
filing it. Zero findings open.

Rulings that bind beyond this pass:

- A token census forbids a SPELLING, not a capability. `ROOT` was the handle everyone named,
  `__file__` was the handle the module already used, and the census saw only the first — so
  enumerate the handles that REACH the resource and pin each one, or the instrument fails
  open on exactly the member nobody thought of. Where a handle is not decidable by census,
  close it structurally and assert the structure (one `subprocess.run` call site, no `cwd`
  default) rather than widening the docstring's promise.
- A guarantee sentence in a docstring is an artifact under review. D30 asserted four correct
  things and CLAIMED a fifth; the claim, not the code, was the defect, and it would have
  survived any green suite.
- A gate list that SPLITS the suite to bound wall time must name what each split omits and run
  the omitted part at least once before the close. Two splits here were individually reasonable
  and together removed the only gate that grades history from every rerun of the unit, while
  each split reported `OK`. A subset that reports like the whole is the same failure shape as a
  control that cannot fire.
- Two instruments can be mutually exclusive by construction and each stay correct alone. D28
  deletes the file four frames of another battery read. Nothing was weakened and no assertion
  was wrong; the pair simply cannot both hold in one process, and only a run of the real
  composition finds it — which is why the composed gate is the one that must actually run.
- A wall-time figure for a command containing a history-walking test is a claim with an
  expiry — its cost tracks a commit RANGE that grows with each commit and collapses at each
  squash. State the decomposition, never one number.
- An absolute sentence inside a scoped paragraph generalizes silently. `No public surface
  names it` was true of the route the paragraph describes and false of the library; scope the
  sentence to its route, because the reader takes the widest reading the words allow.
- A reviewer that dies of context overflow is a dispatch defect, not a reviewer defect. The
  fix that worked: give each lens its OWN read target in the seeded table, and hand the
  successor the closed rows so it cannot re-spend the budget that killed its predecessor.

## upstream-sync 2 (IMPLEMENT, ad-hoc) — target = the diff this commit lands, base `a98945f`

`CLAUDE.md` refresh `agents@a9cddf5` -> `539ca8b` (one changed line, the `Session flow`
dispatch bullet) and its downstream bindings. Reviewer = `rev-1`, 5 lenses fixed at
dispatch, table issued against a tree MAIN held frozen for the run (4 modified files,
unchanged across it).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | merge fidelity | pass | `CLAUDE.md` = upstream `539ca8b` byte-for-byte, sha256 `04e89e18b8db56a142451687f557fa5116c871f91597e3c569d83e4f9a55d25b` both sides; `HEAD:CLAUDE.md` = upstream `a9cddf5` ⇒ the sole hunk IS the upstream delta, zero downstream law reverted. |
| L2 | binding completeness | pass | Recording clause → `.claude/rules/ops.md` Commits (already stronger, now recorded as such); the `rev` clause → `.agent/review.md` header + `.agent/spec.md` `Phase`. The `prompts/prototype.md` half is a repo no-op: prompts enter only through an owner-pasted `/goal` body and this repo is past PROTOTYPE. |
| L3 | misread closure | pass | Retired-form sweep (`fund the map/res/spike end\|MAINTAIN add`) rc 1 over `--hidden --glob '!.git/'`; positive control `PROTOTYPE + ITERATE run heaviest` rc 0 on the one expected file, `CLAUDE.md:60`. No surviving whitelist reading in tracked law. |
| L4 | internal consistency + staleness | finding, fixed | The spine ordered `phase-close rev → README + prototype/ retirement → MAINTAIN` while calling that pass the LAST one over the WHOLE phase diff — two diffs would have landed after it. Reordered so the phase-close pass runs last with nothing mutating after it. |
| L5 | overreach + gate safety | pass | The M3.6a2 `Accept:` addition is a judgment pass, not a numbered mechanical gate ⇒ gates 1–10 pins intact (`CLAUDE.md` `Engineering` splits the two). The 4 changed paths have zero readers in `tests/` (rc 1; control = `pyproject.toml` → `tests/test_authority_removal.py:21`, rc 0), enter no tree census, and miss D28's `tests/`/`examples/`/`m3u6a1-surgery.py` pathspec. |

Findings: 1 raised, confirmed by MAIN's own anchor rematch (`.agent/spec.md:43`, rc 0), fixed
in this commit. Zero findings open.

Rulings that bind beyond this pass:

- A review step placed at an ORDERED position in the spine is only a whole-diff pass if
  nothing in the order mutates after it. Naming a pass "last" does not make it last —
  read the tail of the order, not the label. This is the per-phase-whitelist misread one
  level down: the template stopped funding review once and late, and the spine did it
  anyway.
- A closing `rev` is judgment adjudication, so adding one to a unit's `Accept:` line
  mid-unit does NOT void that unit's numbered gate pins; only a mechanical gate does.

## upstream-sync (IMPLEMENT, ad-hoc) — target `d8994bb`

`CLAUDE.md` refresh from `~/Projects/agents/` (`agents@7d72589` -> `a9cddf5`), the queue
split to `.agent/deferred.md`, and its grader. Reviewer = `rev-1`, 5 lenses fixed at
dispatch, table issued against a frozen tree (`git status --porcelain` empty at
`d8994bb`).

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | merge fidelity | pass | Tree copy byte-identical to upstream (`cmp` rc 0); the 10 changed body lines of `git diff -- CLAUDE.md` equal the upstream delta's 10 ⇒ zero downstream law reverted. |
| L2 | binding completeness | pass | Each of the 5 changed clauses bound to the rule file carrying its mechanics; the `prompts/` half reaches this repo only through owner-pasted `/goal` bodies and is correctly a repo no-op. |
| L3 | queue soundness | pass | 62 rows, grader rc 0; six seeds fire (`.claude/rules/ops.md` Layout) plus the p100 ordinal control. |
| L4 | stale references | pass | `p01`-`p61` cite `.agent/archive/polish.md` for full text; `p62` states its line is its whole record; retired-name sweep matches are qualified historical citations. |
| L5 | overreach | pass | Every obligation removed from the attached state survives as a queue row; two overstated grader claims corrected in later commit bodies on the same unmerged branch. |

Findings: 11 raised in the first round, all confirmed and fixed (`eb669fd`); 1 raised
after it (`d8994bb`); 1 self-found by MAIN while fixing the 12th (`d8994bb`). Zero
findings open.

Rulings that bind beyond this pass:

- L5, ruled: a false claim in a commit body is repaired by an explicit correction in a
  LATER body, not by rewriting the original, while both sit on an unmerged branch that
  `.agent/spec.md` books as squashing into main as ONE commit — the false body never
  reaches main. History rewriting is NOT required to close L5.
- A grader's fail-closed property is a claim about EVERY external read, so it is graded
  per read. `eb669fd`'s body claimed it and one read falsified it: an inline
  `_git(...) == "true\n"` compares a failure sentinel against a string, so `None`
  silently reads as a proven full clone. Seed = a `git` stub failing that ONE query
  while `exec`ing the real git otherwise; the unchanged `COMMITTED-FLOOR` line is the
  control proving the stub selective.
- A generated artifact's header states the rule its generator implements, and a
  generator that refuses to overwrite cannot resync it ⇒ pin the header as a prefix or
  it drifts unnoticed by hand-edit alone.

Machine-local: each `.scratch/` path in this file names a gitignored input or output of the session that wrote it; no clone retrieves it, and the file states the substance it relied on (p10).
