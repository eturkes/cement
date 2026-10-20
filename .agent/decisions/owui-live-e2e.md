# Open WebUI live end-to-end (MAINTAIN W5/W6)

Stand-in for the Kimi K2.6 target: Open WebUI 0.12.3 on CPython 3.11.15 (uv), SQLite 3.53.1, NO
`cement_runtime` installed in its venv (`find_spec` None); chat + learning model = `gpt-6-luna`
through an OpenAI-compatible endpoint (`OPENAI_API_BASE_URL`), native tool calls. Instance =
`uv run python examples/open_webui/local.py serve --base-url <endpoint>/v1 --model gpt-6-luna`,
every part pasted from `examples/open_webui/paste-in/` + `cement-learn/SKILL.md` through the REST
API. Drivers (scratch, gitignored): REST chat turns through `/api/chat/completions` (the server's
own tool loop + filters), browser steps through ChromiumFish (playwright API). Load 3-15 (other
jobs) — wall times below are indicative only.

## Turns (one chat each; "covered" = the `use_learned_function` result)

| # | model | input | s | calls | covered |
|---|---|---|---|---|---|
| 1 | cement-chat | progress note A01 | 21.0 | search_tools, use_learned_function, search_tools, record_answer | false (off) |
| 2 | cement-chat | progress note A02 | 20.2 | same | false (off) |
| 3 | cement-chat | intake form B01 | 18.8 | same | false (off) |
| 4 | cement-chat | intake form B02 | 17.9 | same | false (off) |
| 5 | cement-chat | lab slip C01 | 15.6 | same | false (off) |
| L1 | cement-learning | "Run a Cement learning pass for extraction_plan." | 38.2 | learn_cases, 5× show_proposal, 5× review_proposal (accept), publish_version | — |
| L2 | cement-learning | same | 28.8 | learn_cases, test_projection (3 layouts) | — |
| L3 | cement-learning | same | 16.7 | learn_cases, publish_version | — |
| L4 | cement-learning | same | 38.4 | learn_cases, learn_cases(projectable), 3× merge_case, publish_version | — |
| 6 | cement-chat | progress note A03 (unseen patient) | 11.3 | search_tools, use_learned_function | **true** |
| 7 | cement-chat | lab slip C02 | 15.5 | search_tools, use_learned_function, search_tools, record_answer | false (unrecognized) |
| L5 | cement-learning | same | 49.2 | learn_cases ×2, show_proposal, 3× merge_case, publish_version, diff_versions | — |
| 8 | cement-chat (typed in the browser composer) | synthetic progress note A04 (Hana Sato) | — | search_tools, use_learned_function | **true** |

`search_tools` = Open WebUI 0.12.3's built-in deferred tool search: the model finds each tool by
query before its first call. Every miss turn ended in an accepted `record_answer` and one pending
proposal (5 after turn 5); covered turns retained nothing (pending 0 → 0 at turn 6). Replies were
plain prose or a table, except turn 1 (the bare JSON plan).

## Learning passes

- L1 (tool = the W3 fine-grained surface, skill attached by `meta.skillIds` with built-in skill
  tools ON): the model never called `view_skill` — Open WebUI 0.12.3 lists such a skill in
  `<available_skills>` and injects it only when activated or when `builtinTools.skills` is off
  (`utils/middleware.py`). It accepted all 5 answers as 5 exact cases at support 1, wrote no
  program, published nothing; afterwards `learn cases` reported `nothing_to_learn: true`.
- L2 (skill injected: `builtinTools.skills` off): wrote a correct 3-layout program, ran
  `test_projection` (intake support 2 / 1 output; progress note support 2 / 2 outputs =
  `merged_outputs`; lab support 1), then stopped, reading the two progress-note outputs as "not
  one procedure"; its report also misstated the intake support.
- L3: skipped projection, published nothing.
- L4 (tool = 8 functions, program derived by the tool, skill = merge is the pass's work): regrouped
  by layout, merged each case (progress note = union: `objective` + `temperature` + `heart_rate`
  + `oropharynx_exam`; both earlier examples superseded), published v1 `61f21149…` = 2 cases
  (intake, progress note), lab slip left at support 1. Report accurate.
- L5: merged C02 into the lab case (support 2), published v2 `4dd8063b…` = 3 cases; under
  `follow` v2 was `selected` with no switch write.

## Switch (browser, the `cement_switch` button under a learning-model reply)

- Set up: select options `["Set up extraction_plan (its switch starts off)"]` → confirm → toast
  "extraction_plan is set up. Its switch is off until you switch it on." Ledger:
  `operation.registered` `registered_by = open-webui:<user id>`.
- On: options `Switch extraction_plan on: follow the newest version (version 1, 2 cases)` +
  `Pin extraction_plan to version 1 (2 cases, …, 61f211491218)` → follow + confirm → toast
  "extraction_plan is on and follows the newest version."; `function versions --check`: v1
  `selected: true`, `servable: true`.
- The button sits in the reply's action bar, OUTSIDE the `.chat-assistant` element
  (`button[aria-label='Cement switch']`); a fresh browser profile first shows a release-notes modal
  ("Okay, Let's Go!").

## Hits

- Turn 6: `use_learned_function` → `"covered": true`, `output` = the v1 merged progress-note plan,
  `function_hash` `61f21149…`; the model applied the plan to the new note and answered; no
  `record_answer`. Screenshot: "View Result from use_learned_function" shows INPUT (operation,
  the unseen document) and OUTPUT `{"covered": true, "output": {"fields": [...]}}`.
- Turn 8 (the UI's own tool selection, no driver `tool_ids`): `covered: true` again; the model
  relabelled one row ("Lung exam") — the tool result is deterministic, the reply is not.

## After review (fixes `6fdbb26`, re-pasted with `local.py provision`)

| # | model | input | s | calls | covered |
|---|---|---|---|---|---|
| 9 | cement-chat | synthetic intake form B03 (Ravi Menon) | 14.7 | search_tools, use_learned_function | **true** |
| L6 | cement-learning | "Run a Cement learning pass for extraction_plan." | 9.5 | learn_cases | — "Nothing to learn": 3 cases at support 2, nothing pending |
