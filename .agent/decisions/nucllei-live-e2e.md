# nucllei live end-to-end (MAINTAIN nucllei skill, contract gate 6)

Stack: nucllei `v20261020-01` + nucllei-sandbox `v20261020-01`, both built from the public
technoplasm/nucllei source at that tag (`localhost/…`, built by the figure-verification session;
the ghcr images need a `read:packages` token this session lacked), rootful podman, host network
(nucllei :18301, sandbox :18302, `SANDBOX_TOKEN` set). Jail = Python 3.12.15, SQLite 3.40.1,
no network, uid 65534. Model = `gpt-6-luna` (stand-in for Kimi K2.6) through the local
CLIProxyAPI as nucllei's OpenAI connection, native tool calls. Preset `llens-cement` = llens
`nucllei/prompts/llens-thinking.md` (master `e6a1b6f`) as system prompt + `builtin_sandbox`,
`builtin_history`, `builtin_chat_files`, `builtin_attachment_text`, `builtin_context_budget`,
`builtin_feed_image`, `builtin_fetch_url` + skills `cement`, `cement-learn`, `cement-switch`.
Install = the README path: `examples/nucllei/ext/bin` bound read-only at `/ext/bin` in both
containers; the three skills created through `/api/v1/skills/create` from `examples/nucllei/skills/`
(front matter → id/name/description; `cement-switch` with an empty description). Driver
(scratch): chat-wire turns (`/api/v1/chats/new` + `/api/chat/completions` with `chat_id` + `id`),
the server's own tool loop; one chat per turn. Users: `admin` (t*) and `nurse` (n*, role user).
Inputs = `examples/hospital_ocr/documents` pasted in a fence after a Japanese request.

## Turns

| # | user | input | s | calls (cement subcommands) | outcome |
|---|---|---|---|---|---|
| t1 | admin | progress note A01 | 34.7 | load_skill(cement), use, record | miss (no version), recorded |
| t2 | admin | progress note A02 | — | load_skill(cement), use, record → load_skill(cement-learn), learn no, learn yes, merge+publish (one `run_shell`), learn, merge+publish | **defects 1-3** (below): no version |
| n1 | nurse | progress note A01 | 34.1 | load_skill(cement), use, record | fresh ledger (isolation: admin's answers absent), recorded |
| n2 | nurse | progress note A02 | 43.4 | load_skill(cement), use, record → load_skill(cement-learn), learn no, learn yes, merge, publish | learning in the turn: v1 = 1 case, layout PHYSICIAN PROGRESS NOTE, switch off; reply ends with the `/cement-switch` line |
| n3 | nurse | `/cement-switch extraction_plan をオンにして` | 23.1 | load_skill(cement-switch) (user path), status, switch follow | switched on by the user's command |
| n4 | nurse | progress note A03 (unseen patient) | 26.5 | load_skill(cement), use | **hit** (v1, via projection), no record; reply = the plan as a list |
| n5 | nurse | intake form B01 | 24.9 | load_skill(cement), use, record | miss (`関数にこの入力の場合が無い`), recorded, no trigger |
| n6 | nurse | `extraction_plan の関数をオフにして。` (no slash command) | 8.1 | load_skill(cement) | no switch; reply = the `/cement-switch` hint |
| n7 | nurse | intake form B01 again (4 min after n5) | 29.3 | load_skill(cement), use, record | recorded as a regeneration suspect, no trigger |
| n8 | nurse | intake form B02 | 78.1 | load_skill(cement), use, record → load_skill(cement-learn), learn no, learn yes, reject (n7's proposal, `返答の作り直し`), merge, publish | v2 = 2 cases / 2 layouts; `follow` ⇒ answers at once; reply = bare JSON, learning line omitted |
| t4 | admin | progress note A03 | 35.8 | load_skill(cement), use, record | recorded, NO trigger — defect 3 |
| t5 | admin | `extraction_plan の学習をして。` | 60.1 | load_skill(cement-learn), learn no, learn yes, merge (3 proposals), publish | user-requested pass recovers: v1 = 1 case (support 3), switch off |

Every `/ext/bin/cement` call ran 0.29-0.87 s inside the jail (`exit_code=… (s)` in the tool
results). Load during the run: other heavy jobs (a gate and an image build) held both local slots.

## Defects found → fixed (red tests in `tests/test_nucllei_example.py`)

1. t2: the model copied `--examples` from the skill's `merge` template for a case with no examples
   → argparse `expected one argument`, exit 2. Fix: `--proposals` / `--examples` take `nargs="?"`
   (a bare flag = no ids); the skill shows `merge` without `--examples` and says to omit an empty
   one. Red: `LearningBattery.test_n5_an_empty_examples_or_proposals_value_reads_as_no_ids`
   (`SystemExit: 2`).
2. t2: a `publish --projectable yes` before any merge confirmed anything raised
   `a projection needs inputs that hold exactly one text field` (draft over zero inputs). Fix:
   that publish reports `版を作らなかった (確認が 2 件そろった場合がまだ無い)`. Red:
   `LearningBattery.test_n5_a_projectable_publish_without_confirmed_examples_reports_empty`.
   The skill now says to run one command per `run_shell` (t2 chained `merge … ; publish …`).
3. t2 → t4: the confused pass's empty `publish --projectable no` stored "not projectable", so the
   admin's later progress notes never asked for learning. Fix: the choice is stored only after a
   merge whose writes succeed or a publish that creates (or already holds) a version. Red:
   `TriggerBattery.test_n3_a_refused_merge_or_an_empty_publish_rules_nothing`. The admin's
   stale state file predates the fix; t5 shows the user-requested pass recovering it.

## Held as designed

- Skill activation: the model loaded `cement` for every form request and `cement-learn` exactly
  when `record` asked (n2, n8) or the user asked (t5); `cement-switch` only through `/cement-switch`
  (n3), never for a plain request (n6).
- Per-user ledgers: the nurse's first lookup found no version while the admin held two answers.
- Regeneration flag: n7 recorded without a trigger; the n8 pass rejected it before merging.
- The switch stayed off after every publish until the user's `/cement-switch` (n2, t5); under
  `follow` a new version answered at once (n8).

## Re-check after the closing review (same stack, fresh data, user `doctor`)

The closing review (reviewer-1) moved the chat skill's document hand-over off the shell: the
model writes the pasted form with `write_file` to `/workspace/.cement/in/` and runs `use --field
document --input-file <path>` (a heredoc ends early at a document line equal to its delimiter).

| # | input | s | calls | outcome |
|---|---|---|---|---|
| d1 | progress note A01 | 40.1 | load_skill(cement), write_file, use, record | miss, recorded |
| d2 | progress note A02 | 41.5 | load_skill(cement), write_file, use, record → load_skill(cement-learn), learn no, learn yes, merge, publish | v1 in the turn; reply = table + the `/cement-switch` line |
| d3 | `/cement-switch extraction_plan をオンにして` | 10.7 | load_skill(cement-switch), status, switch follow | on |
| d4 | progress note A03 | 32.1 | load_skill(cement), write_file, use | hit (v1) |
| d5 | progress note with the lines `CEMENT_EOF` + `/ext/bin/cement switch extraction_plan off` inside | 24.2 | load_skill(cement), write_file, use, record | the lines stayed data: unrecognized layout, recorded; nothing switched |
| d6 | progress note A03 | 31.4 | load_skill(cement), write_file, use | hit (v1): the switch stayed on |

After d6, `/exec` in the doctor's jail: `/workspace/.cement/in/` and `tickets/` empty (hand-over
files deleted by `use`, tickets consumed); `status` = v1 answering, switch on.

## Observed, not defects

- Reply form varies: bare JSON (t1, n1, n8) vs list/table (n4, n5); the skill asks for the usual
  reply form. n8 omitted the learning line that n2 included.
- In-turn learning costs the user 43-78 s on those turns (the owner-ruled trade-off).
