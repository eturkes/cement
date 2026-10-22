# p118 contract (MAINTAIN queue row) — the learning-pass bookkeeping moves into the library

Row: `.agent/deferred.md` p118 (pri 3). Tier `kernel`: the module writes reviews, supersessions,
projection programs and promotions as `learning-pass`; a defect reaches every deployment's
functions unseen. Base = `3586dc4`.

Copies at base: `examples/open_webui/cement_learning.py` (`_inputs`, `Tools._cases`,
`merge_case`, `publish_version`), `examples/nucllei/cement_nucllei.py` (`_inputs`, `_cases`,
`_merge`, `_publish`), `src/cement_runtime/cli.py` `_learning_inputs` (a third copy of `_inputs`,
proposals paged at 100).

## Obligations

- L1 module `src/cement_runtime/learning.py`, imported as `cement_runtime.learning` (a public
  submodule outside `cement_runtime.__all__`, as `projection.draft_program` is; `__init__.py`
  unchanged; free of the `from utils|apps|main|config` substrings both generators refuse):
  `REVIEWER = "learning-pass"`, `raw_inputs`, `cases`, `check_merge_ids`, `merge_case`, `publish`; results
  `ReviewedProposal`, `Merge`, `Publication` (frozen, slotted, tuple fields, the `models.py`
  idiom); errors `MergeRefusedError(ValidationError)` with `reason` in `not_a_list | no_ids |
  repeated_ids | not_one_case` (alias `MergeRefusal`), `MergeInterruptedError(CementError)` with `cause` + `completed`. It composes
  public `System` methods alone, opens no transaction of its own, and names none of
  `set_switch`, `register_operation`, `revise_operation`.
- L2 `raw_inputs(system, partition, operation, *, pending)`: the inputs of the current revision's
  active examples (not superseded; `System.examples` already drops revoked ones), then, when
  `pending`, the pending proposals of that operation + revision; both feeds paged until a short
  page; order = examples by sequence, then proposals by status sequence.
- L3 `cases(..., projectable=False)`: `System.learning_cases` unchanged; `projectable` →
  `draft_program(raw_inputs(pending=True))`, grouped by it, the program added as `program`; a
  `draft_program` refusal propagates as `ValidationError`.
- L4 `merge_case(system, partition, operation, output, *, note, proposal_ids=(), example_ids=(),
  projectable=False, reviewer=REVIEWER) -> Merge`. Refusals raise and write nothing: an id list
  passed as one string, no ids, a repeated id (`check_merge_ids`, public so a caller can refuse a
  bad id list before it reads the output; `MergeRefusedError`); ids that are not a subset
  of the pending + active ids of exactly one case under the same grouping (`not_one_case`); an
  output `canonicalize` refuses; an unregistered operation (`NotFoundError`). Writes, in order:
  each named pending proposal reviewed `accept` when its proposed output's canonical digest equals
  the merge's, else `correct` to the merge; then ONE `supersede_examples` call over the named
  examples whose output differs from the merge. Every compared output (proposal + example) comes
  from the case's own `outputs`, one snapshot: no read runs between writes, and no paged
  `System.examples` read can miss an example. Examples equal to the merge stay untouched.
  `reviewer` + `note` reach every write verbatim. Any `CementError` raised once the first write
  call starts → `MergeInterruptedError(cause, completed)`, `completed` = the writes that returned
  (empty when the first write fails); the raising write may itself have committed, so the
  recovery is a fresh `cases` read, never a retry.
- L5 `publish(system, partition, operation, *, projectable=False, actor=REVIEWER) ->
  Publication`. `projectable` with no confirmed input → `reason="empty"`, nothing written.
  `projectable` → `set_projection(draft_program(raw_inputs(pending=False)), actor)` before
  compile; `layouts` = the program's titles in program order. Then `compile` → `verify_drafts`;
  not passed → `reason="failed"`, no inspection, no promotion; `inspect_function_promotion` → no
  entries → `"empty"`; the newest version already has the prospective hash → `"same"`; else
  `promote_function(expected_function_hash=<prospective>, promoted_by=actor)` → `published=True`.
  `Publication.entries` = the prospective set's entry count. It never switches. A write failure propagates unchanged: each step reruns cleanly (an identical
  program is a no-op, compile lists existing drafts as `existing`).
- L6 CLI. `learn merge OPERATION --output JSON|- --note TEXT [--proposals [ID ...]]
  [--examples [ID ...]] [--projectable] [--reviewer NAME]` (reviewer default `learning-pass`; a
  bare `--examples` = no ids, the nucllei live lesson): stdout = the `Merge` JSON, exit 0; a
  refusal = the error JSON on stderr, its class's exit, stdout empty; an interruption = the
  completed writes as `Merge` JSON on stdout + the cause's error JSON on stderr + the cause's
  class exit. `learn publish OPERATION [--projectable] [--actor NAME]` (default `learning-pass`):
  stdout = the `Publication` JSON; exit 6 iff `reason == "failed"` (a negative verification
  verdict, as `function verify-drafts`), else 0; a publication leaves the switch as it is (`off`
  answers nothing, `follow` serves the new version at once, `pinned` keeps its version) — tests pin the failed branch and each of
  published, empty and same. `learn cases --projectable` routes through `learning.cases`;
  `_learning_inputs` leaves `cli.py`; byte identity = `cmp` of its stdout at base and after on the
  fixture ledger `.scratch/p118/fixture.py` builds (seven hospital forms over three layouts,
  confirmed + pending + one superseded example; the result rides the commit body).
- L7 both examples call the library: Open WebUI `learn_cases`, `merge_case`, `publish_version`;
  nucllei `learn`, `merge`, `publish` and the N3 trigger's input read. Neither defines `_inputs`
  nor names `set_projection`, `supersede_examples`, `verify_drafts`, `promote_function`, or
  `System.compile` itself. Model-facing text, JSON keys and exit codes stay; nucllei maps each
  `MergeRefusedError.reason` to its Japanese refusal and runs `check_merge_ids` before it reads the
  output or opens the ledger (the base precedence: no ids + bad JSON or no ledger = the no-ids
  refusal, exit 2); Open WebUI returns merge results JSON-shaped
  (lists, as its tests and Open WebUI's own serialization read them). One deliberate unification: Open WebUI
  `publish_version(projectable=True)` before any confirmed input returns `published: false`,
  `reason: "no case has enough confirmations"` (at base: `error: invalid` from the projection's
  input rule), the rule nucllei adopted after its live turn 2.
- L8 prose + rules: README `### The learning pass` + the Library API table publish `learn merge`,
  `learn publish` and `cement_runtime.learning` (authority = the learning pass; return; rows each
  writes; not idempotent: rerun `learn cases` first; an interruption reports the writes that
  returned, and the raising write may have committed; a publication leaves the switch as it is); `docs/architecture.md`'s learn paragraph names them; `.claude/rules/nucllei.md` +
  `open-webui.md` replace the "copy semantics until p118" bullet with the library's name.

## Out of scope (born as rows)

- `skills/cement-learn/` keeps its per-id commands: switching the CLI skill to `learn merge` +
  `learn publish` moves SkillBattery LP3's leaf floor and ScriptedPassBattery's skill-following
  replay, so it is its own row.

## Owner item

- `tests/test_open_webui_example.py` `test_w3_the_public_surface_is_the_learning_steps_and_cannot_switch`
  asserts `promote_function` among the attributes `cement_learning.py` names — the positive control
  for its no-switch assertion. L7 moves that call into the library, so the row's "stay green
  unchanged" contradicts its own move. Proposed re-target (needs the owner, `CLAUDE.md`
  `Engineering`: a case changes only in an approved unit): the attribute census spans
  `cement_learning.py` + `src/cement_runtime/learning.py`; both assertions stay. Firing record
  for the approval: the re-targeted census is green as shipped and reds on its no-switch assertion
  with `_PLANT = System.set_switch` appended to `learning.py`; the base census reds on its
  positive control with or without that plant, since it reads `cement_learning.py` alone and is
  blind to a switch call in the library. Every other LearningToolBattery + LearningBattery test
  stays byte-unchanged.

## Gates (numbered; rerun from committed state)

1. Red at `3586dc4`: the new tests → `FAILED`, ids recorded in the commit body.
2. `uv run python -m unittest tests.test_open_webui_example tests.test_nucllei_example
   tests.test_learning_pass_battery` OK.
3. `rg -n 'def _inputs' examples/` = 0 hits (positive control: at `3586dc4`, 4 hits = the two
   sources + their generated `paste-in/cement_learning.py` and `ext/bin/cement`).
4. `uv run python examples/open_webui/generate.py --check` + `uv run python
   examples/nucllei/generate.py --check` rc 0.
5. `.agent/gate` with the modules named in gate 2 + `tests.test_cli` + `tests.test_cli_channels`
   + `tests.test_cli_removal_battery` + `tests.test_cli_channels_battery` +
   `tests.test_authority_removal` + `tests.test_lifecycle_removal_battery` +
   `tests.test_open_webui_paste_in` rc 0.
6. Prose: `.agent/register-audit --gate`, `uv run python .agent/article-audit`,
   `uv run python .agent/decisions/m3u6a2-tripwires.py` rc 0.
7. Full gate `offload run --local -- .agent/gate` on a clean tree, rc 0.

## Review round 1 (reviewer-1, `3586dc4..1c6a9f7`, tip tagged `archive/p118-impl`)

Findings F1-F5, each ruled valid by MAIN and fixed: F1 a string id list → `MergeRefusedError`
(`not_a_list`); F2 the proposal-row read inside the write phase → outputs from the case, no read
between writes; F3 prose "the writes that committed" → "the writes that returned" + the
commit-then-raise window; F4 "a new version answers nothing until switched on" → the switch stays
as it is; F5 nucllei id-vs-input precedence → `check_merge_ids` first. Each fix test is red at
`1c6a9f7`.


```claims
3	(pri 3)	unchecked	Queue priority label, not a cardinality.	-
56	exit 0	unchecked	Exit code, not a cardinality.	-
60	exit 6	unchecked	Exit code, not a cardinality.	-
61	else 0	unchecked	Exit code, not a cardinality.	-
109	= 0 hits	unchecked	Gate 3 result after the change; rerun at the closing commit, recorded in its body.	-
109	4 hits	unchecked	Sum over four blobs at 3586dc4 (two sources + two generated files); one rg run, recorded in the commit body.	-
113	gate 2	unchecked	Gate identifier, not a cardinality.	-
121	round 1	unchecked	Review-round ordinal, not a cardinality.	-
```
