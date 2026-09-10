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
row with its acceptance check, never as an open row here. A fix earns ONE re-review round
against its acceptance check alone.

## `CLAUDE.md` refresh (ITERATE, ad-hoc) — target = the single commit landing the refresh

The template was overwritten from `~/Projects/agents/claude/CLAUDE.project.md` at `c38a706`,
carrying one new `Engineering` bullet (`Verification integrity`); this pass reviews that fold plus
every downstream binding it drew. THE LENS SET BELOW WAS WRITTEN BEFORE THE REVIEWER WAS
DISPATCHED and ships in the same commit as the reviewed content, the diff being authored before
the pass rather than on a branch — that is the one departure from the M3.6a2 shape, and the
guarantee it preserves is the same: no lens was added, dropped or reworded after a finding
appeared. Verdicts land in the close commit.

| id | lens | verdict | basis (MAIN-verified) |
|---|---|---|---|
| L1 | upstream fidelity — the tracked template equals upstream byte for byte, the fold adds exactly upstream's delta and reverts no downstream law, and `last-sync` names a revision whose range holds every unfolded template/prompt commit | pending | |
| L2 | binding completeness — each clause of the new bullet reaches a `.claude/rules/` file with this repo's mechanics, or the record states why it needs none | pending | |
| L3 | claim soundness — every fact the new prose asserts is measured at this tree: the skip census is complete, the named missing checks are absent, and each cited symbol, path, line and environment variable is spelled as shipped | pending | |
| L4 | claim-vs-guarantee gap — no green claim, old or new, certifies more than was run, and the `Phase` record of the M3.6a2 close stays true of THAT run | pending | |
| L5 | law conflict — the new text contradicts no standing rule in the files it lands in, and duplicates none of them across scopes (the D28 `skipTest` seed, `REPORTED never forced`, the `CLAUDE.md`-versus-rules routing split) | pending | |
| L6 | repo-state integrity — the queue grades clean, no committed check reads an edited path in a way this diff reddens, and the retired-name sweep plus every tree census stay satisfied | pending | |
| L7 | register conformance — agent-optimized register on machine-read law, no human-facing surface touched, Marksman-clean markdown, no provenance | pending | |

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
