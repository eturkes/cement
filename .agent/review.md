# Review ledger

Adjudicated `rev` findings, one section per review pass. A pass closes on a check set
fixed BEFORE the diff was read: every row adjudicated, the table shipped, an all-`pass`
table complete. An accepted ruling holds until new evidence reverses it. Rows are
adjudicated by MAIN — a teammate verdict is raw material and is re-derived here, never
credited (`.claude/rules/assurance.md`, `Instruments and validators`).

EVERY closing diff draws a pass: each unit's close, each ad-hoc request's close, and the
phase close alike — this ledger is not a phase-close step, and a unit that lands with no
section here closed unreviewed. A finding inside the artifact's acceptance contract is
fixed before the close it reviews; a finding outside it is born as a `.agent/deferred.md`
row with its acceptance check. The one open row this ledger holds = an IMPLEMENT mutation
survivor its unit left unruled, open until the closing-diff `reviewer` rules it against the
contract (`CLAUDE.md` `Engineering` Verification integrity). A fix earns ONE re-review round
against its acceptance check alone.

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
