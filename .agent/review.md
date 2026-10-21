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
