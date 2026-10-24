# Survivor rulings (p93, p99-p116)

Rule (owner-ruled, `.claude/rules/assurance.md` Survivor scope): a credit run's survivor needs a ruling
only inside the pin's named subject; every survivor outside it is `contract-open` by construction.
Mechanics: `uv run python .agent/survivor-triage .agent/decisions/<record>-mutate.txt` with subjects
from `.agent/decisions/survivor-subjects.json` (rerunnable from committed state: the record names its
revision, the tool rebuilds each in-scope mutant there with cosmic-ray and replays it against every test
module that names a subject, D28 excluded). A `missing-test` pin proves red on its mutants with `uv run python .agent/kill-check RECORD ROWS <test id>` (ROWS = triage's `--at HEAD` output).
Rulings below are MAIN's (owner: the backlog is MAIN alone).

## p102 — `p53-mutate.txt` (`ParserShapeTests.test_the_live_grammar_digest_covers_help_choices_and_type` @ a5b0163)

Subject `cli.py:_parser`. Tally: 77 survivors = 75 out-of-scope (`contract-open`: `models.py`
`CompilePolicy.__post_init__`, which `_parser()` runs for its defaults) + 2 in scope, both survived triage
(9 killer modules).

| survivor | ruling | basis |
|---|---|---|
| `cli.py:102` `ReplaceComparisonOperator_Eq_GtE` #1 | equivalent | `for name in ("register", "revise")`: `"register" >= "revise"` is False and `"revise" >= "revise"` True, the same truth table as `==` over the only two values. |
| `cli.py:102` `ReplaceComparisonOperator_Eq_Is` #1 | equivalent | both operands are the same interned literal `"revise"` in CPython, so `is` agrees with `==` over the loop's two values. |

## p113 — `p91-mutate.txt` (ABI pin `test_function_report_public_shape_is_exact_frozen_slotted_and_exported` @ 3ef05d3 + `test_parser_rejects_ambiguous_or_unbounded_values` @ 8bef2a0)

Subjects: the report dataclasses (`models.py` `FunctionReport`, `OperationNowReport`, `FunctionAnchorReport`) and `json_value.py` `parse_json`. Tally: 84 survivors, all out of scope → `contract-open` by construction: `store.py` `Store.__init__` 35, `_validate_ledger` 10, `Store._connect` 10, `Store._initialize` 7, `_schema_objects` 5 and `system.py` `System.__init__` 17 — the ledger the pin's fixture opens. The subject module `models.py` holds no survivor (the record: 27 killed of 27); the parser pin's section holds none.

## p112 — `p23-mutate.txt` (`ShippedCommandRoundTripTests.test_the_eval_child_opens_no_database_file` @ e3665b5)

Subjects: the eval path the pin's audited child runs — `cli.py` `_read_function_bundle` and `_run` (its eval branch precedes the ledger gate). Tally: 1483 survivors, all out of scope → `contract-open` by construction: the credit run traces the parent process alone, and the parent builds the promoted ledger the children read (`system.py` 946 — `System._verify_function_snapshot` 92, `System._assess_examples` 83, `System._run_verification` 73 —, `projection.py` 163, `json_value.py` 118, `models.py` 76, `store.py` 76, `function.py` 66, `artifacts.py` 38); no `cli.py` line holds a survivor, because the eval path runs only in the audited child processes.

## p104 — `p09-mutate.txt` (`SubmissionTests.test_a_non_mapping_provenance_is_refused_never_normalized` @ 06ab393)

Subjects: `system.py` `System._canonical_candidate` (the provenance type check) + `System.submit_proposal`. Tally: 281 survivors — 280 out of scope → `contract-open` by construction (`store.py` 79, `models.py` 76 = `CompilePolicy.__post_init__`, `json_value.py` 74, `system.py` 51 outside the subjects: the fixture's ledger, policy and candidate canonicalization); 1 in scope, `system.py:739` `System._canonical_candidate` `ReplaceComparisonOperator_IsNot_NotEq #10`. The first triage reported it killed, a phantom: its 16 killer modules included `tests/test_open_webui_paste_in.py`, whose freshness test (W1) reds every `system.py` mutant left un-regenerated; the corrected tool (regenerated embeds) → `out-of-scope 280, survived 1`, ruled:

| survivor (`06ab393`) | ruling | basis |
|---|---|---|
| `system.py:739` `_canonical_candidate` `ReplaceComparisonOperator_IsNot_NotEq #10` (`type(candidate) is not Candidate` → `!=`) | missing-test → added | the contract refuses anything but a `Candidate` (`candidate must be a Candidate`); equality on a class can be forged through its metaclass, identity cannot. `tests/test_survivor_pins.py` `test_p104_a_class_forging_equality_is_no_candidate` is green on the tree and red on the mutant (`ValidationError not raised`). |

## p105 — `p14-mutate.txt` (`test_main_returns_with_stdout_still_buffered` + `test_a_closed_stdout_exits_120_with_python_s_notice` @ 5a44733)

Subjects: `cli.py` `_emit` + `main` (the stdout channel both pins name). Tally: 389 survivors — 372 out of scope → `contract-open` by construction (`store.py` 153, `cli.py` 110 outside `_emit` + `main`, `models.py` 75, `system.py` 34: the ledger, parser and policy code the pins' commands run); 17 in scope (the first pin; the second holds none): 15 killed by the 29 modules naming a subject, 2 survived and ruled:

| survivor (`5a44733`) | ruling | basis |
|---|---|---|
| `cli.py:409` `_emit` `ReplaceBinaryOperator_Mul_Div #3` | equivalent | cosmic-ray rewrites the keyword-only `*` of `def _emit(value, *, stream=None)` into `/`: `stream` becomes positional-or-keyword, and every call site passes `stream=` by keyword, so no call behaves differently. |
| `cli.py:414` `_emit` `ReplaceFalseWithTrue #10` (`ensure_ascii=False` → `True`) | missing-test → added | the CLI prints non-ASCII JSON as raw UTF-8 (the implementation and every byte-comparing CLI test use `ensure_ascii=False`), but each such test prints ASCII alone; `tests/test_survivor_pins.py` `test_p105_the_cli_prints_non_ascii_json_as_raw_utf8` (a `proposal show` of a Japanese input + output) is green on the tree and red on the mutant (`'"患者": "山田"' not found`). |

## p116 — `p30-mutate.txt` (`test_function_verification_enumerates_members_inside_its_read_transaction` @ 90b405a)

Subjects: `system.py` `System.verify_function` + `System._promoted_function_rows`. Tally (`.agent/survivor-triage`, regenerated embeds): 1218 survivors — 1216 out of scope → `contract-open` by construction (`system.py` 830 outside the subjects, `json_value.py` 118, `models.py` 80, `store.py` 79, `function.py` 73: the promotion fixture the pin builds); 2 in scope, both killed by the modules naming a subject (`verify_function:2972` `ReplaceUnaryOperator_Delete_Not #22`, `:2975` `ReplaceFalseWithTrue #14`). No ruling owed.

## p110 — `p41-mutate.txt` (`test_verify_drafts_holds_the_write_lock_while_a_blocking_clock_runs` + `test_promote_function_rolls_back_when_its_clock_reenters_the_ledger` @ ab478e4)

Subjects: `system.py` `System.verify_drafts` (first pin) + `System.promote_function` (second). Tally: 1689 survivors — 1681 out of scope → `contract-open` by construction (`system.py` 990 outside the subjects, `json_value.py` 224, `models.py` 160, `store.py` 159, `function.py` 76); 8 in scope: 4 killed at the record's revision (`promote_function:4994` `ReplaceTrueWithFalse #49`, `:5002` `NotEq_Gt #121`, `NotEq_Is #112`, `NotEq_Lt #121`), 4 survived there (`verify_drafts:4411` `NumberReplacer #326`/`#327`, `promote_function:4993` `NumberReplacer #354`/`#355`) and are killed at HEAD f368cc1 by the suite's later tests (`survivor-triage --at HEAD --from …p41.jsonl` → `4 distinct replays; killed-at 4`). No ruling owed.

## p115 — `p48-mutate.txt` (the three `ProposalBindingAdapterTests` selection pins @ 9af7827)

Subjects: `system.py` `_proposal_bindings`. Tally: 888 survivors — 877 out of scope → `contract-open` by construction (the ledger + proposal fixture); 11 in scope: 2 killed by the modules naming the subject, 9 rows = 5 distinct mutants surviving at the record's revision and at HEAD f368cc1 (`survivor-triage --at HEAD` → `survived-at 9`), ruled:

| survivor (`9af7827`) | ruling | basis |
|---|---|---|
| `:512` `type(selection) is _ProposalIds` → `==` (`Is_Eq #0`) | equivalent | the selection classes are private dataclasses with no custom metaclass, built only inside `system.py`; class equality = identity for them. |
| `:527` `is _ProposalFeed` → `==` (`Is_Eq #1`) | equivalent | as above. |
| `:542` `is _PendingProposals` → `==` (`Is_Eq #2`) | equivalent | as above. |
| `:515` `len(set(v)) != len(v)` → `<` (`NotEq_Lt #3`) | equivalent | a set never holds more members than the sequence it came from, so `!=` and `<` agree. |
| `:515` `len(set(v)) != len(v)` → `is not` (`NotEq_IsNot #3`) | missing-test → added | CPython caches small ints only (to 256), so the identity form refuses every distinct selection longer than that; the helper's contract (an id set, duplicates refused) admits it. `tests/test_survivor_pins.py` `test_p115_a_long_distinct_id_selection_is_no_duplicate` (300 distinct ids) is green on the tree and red on the mutant (`IntegrityError: … duplicate identifiers`). |

## p114 — `p42-mutate.txt` (the three `PreservedInvariantCensusTests` pins @ 059dab8)

Subjects: `system.py` `_text` (invalid-identity pin), `_event` (payload-keys pin), both (identity-writer census). Tally: 3950 survivors — 3928 out of scope → `contract-open` by construction (the writers' bodies + fixtures the censuses drive); 22 in scope: 10 killed by the modules naming a subject, 12 rows = 6 distinct mutants surviving at the record's revision and at HEAD f368cc1 (`--at HEAD` → `survived-at 12`), ruled:

| survivor (`059dab8`) | ruling | basis |
|---|---|---|
| `:171` `_text` `maximum: int = 512` → 511 / 513 (`NumberReplacer #20`, `#21`) | equivalent | every `_text` call passes `maximum` explicitly (AST census: 23 calls at the record's revision, 25 at HEAD, none reads the default). |
| `:171` `_text` keyword-only `*` → `/` (`Mul_Div #3`) | equivalent | every call passes `maximum` + `allow_empty` by keyword. |
| `:172` `type(value) is not str` → `!=` (`IsNot_NotEq #2`) | missing-test → added | equality with `str` can be forged through a metaclass, identity cannot; `tests/test_survivor_pins.py` `test_p114_text_refuses_a_class_forging_equality_with_str` red on the mutant. |
| `:388` `_event` `max_bytes=262_144` → 262,143 / 262,145 (`NumberReplacer #44`, `#45`) | missing-test → added | the cap is reachable (`set_projection` writes an unbounded id list, row p138); `test_p114_the_event_payload_cap_is_an_adjacent_pair` (262,144 accepted, 262,145 refused) red on both mutants. |

## p100 — `p21-mutate.txt` (the four `function show` / `receipts` parser pins @ 55d6942)

Subjects: `cli.py` `_parser`. Tally: 1188 survivors — 858 out of scope → `contract-open` by construction; 330 in scope (84 distinct): 122 killed by the modules naming the subject at the record's revision; the 208 survivors replayed against HEAD (`--at HEAD`, re-anchored by line text) → 172 rows killed by later tests (the grammar SHAPE digest, p53, covers each node's `required`, `default`, `nargs`, `allow_abbrev`, help, choices and type), 36 rows = 9 distinct surviving the full suite minus D28 too (`--at HEAD --full` → `survived-at 36`), ruled:

| survivor (`55d6942`) | ruling | basis |
|---|---|---|
| `:182` `:252` `:257` `:264` `:279` `:282` `:286` `:291` `add_parser(…, allow_abbrev=False)` → `True` (`ReplaceFalseWithTrue #2`-`#9`) | equivalent | `_parser()` ends with `_no_abbreviation`, which sets `allow_abbrev = False` on every node (p49); a per-node argument is overridden by that walk, so neither value reaches a parse. |
| `:102` `if name == "revise"` → `>=` (`Eq_GtE #1`) | equivalent | `name` ranges over the literal pair `("register", "revise")`, and `"register" < "revise"`, so `==` and `>=` agree on both. |

## p101 — `p22-mutate.txt` (`OfflineBundleTests.test_bundle_identity_follows_its_ids_and_clock_alone` @ bad1d30)

Subjects: `function.py` `build_function` + `_normalize`, `system.py` `_function_entry_seal`. Tally: 1513 survivors — 1462 out of scope → `contract-open` by construction (the promoted-ledger fixture); 51 in scope: 33 killed by the modules naming a subject at the record's revision; the 18 survivors replayed against HEAD → 1 killed by later tests (`--at HEAD`), then 2 more by the full suite minus D28 (`--at HEAD --full`: the input + output digest-mismatch `!=` → `<`/`>` mutants), 15 distinct left, ruled:

| survivor (`bad1d30`) | ruling | basis |
|---|---|---|
| `:123` `v2_keys | {"projection", "projection_hash"}` → `^` (`BitOr_BitXor #0`) | equivalent | the two key sets are disjoint, so union = symmetric difference. |
| `:131` + `:249` `root["abi"] == FUNCTION_ABI` → `>=` (`Eq_GtE #1`, `#2`) | equivalent | `:127` admits only `cement-function-v3` + `-v2`, and `-v2 < -v3`, so `==` and `>=` agree. |
| `:234` `len(set(h)) != len(h)` → `<` (`NotEq_Lt #5`) | equivalent | a set never outgrows its sequence. |
| `:339` `"function_hash": "0" * 64` → 63 / 65 (`NumberReplacer #20`, `#21`) | equivalent | a placeholder: `_document` overwrites `function_hash` with the normalized content digest. |
| `:119` `type(value) is dict` → `==`; `:127` `type(root["abi"]) is not str` → `!=`; `:151` `type(operation_revision) is not int` → `!=`; `:158` `type(raw_entries) is not list` → `!=`; `:315` `type(entry) is not FunctionEntry` → `!=` (`#0`, `#3`, `#4`, `#5`, `#8`) | missing-test → added | `validate_function` + `build_function` are public and take caller objects; equality can be forged through a metaclass, identity cannot. `tests/test_survivor_pins.py` `test_p101_bundle_type_checks_refuse_classes_forging_equality` is red on each of the five mutants. |
| `:132` `projection is not None or projection_hash is not None` → `and` (`ReplaceOrWithAnd #4`) | missing-test → added | a bundle with one half set must still enter the projected branch and refuse the missing half; `test_p101_a_half_set_projection_is_refused_as_invalid` (hash alone, program alone) red on the mutant. |
| `:138` `program.program_hash != projection_hash` → `>`, `<`, `is` (`#1` ×3) | missing-test → added | a mismatch below and above the program's hash must both refuse; `test_p101_a_projection_hash_mismatch_is_refused_in_both_orders` (`0…0`, `f…f`) red on all three. |

## p111 — `p15-mutate.txt` (the eight `function export` CLI pins @ 48fe736)

Subjects: `cli.py` `_run` (the export branch + the ledger gate the pins run). Tally: 7594 survivors — 6967 out of scope → `contract-open` by construction (the ledger, promotion and parser code the pins' commands run); 627 in scope (109 distinct, one replay each through the run memo): 322 killed by the modules naming the subject at the record's revision; the 305 survivors replayed against HEAD → 192 killed by later tests (`--at HEAD`), 35 more by the full suite minus D28 (`--at HEAD --full`), 78 rows = 14 distinct left, ruled:

| survivor (`48fe736`) | ruling | basis |
|---|---|---|
| `:610` `:613` `:655` `:674` `:676` `:696` `:741` `:758` `:821` `:853` `:860` dispatch `args.<group> == "<name>"` → `<=` / `>=` (`Eq_LtE` / `Eq_GtE` #9-#38) | equivalent | each mutated comparison admits, among the names its argparse group allows at HEAD, only its own name or names whose branches return earlier in `_run` (HEAD dispatch order: operation `list` → `register`; proposal `submit` → `show` → `list`; command `… verify … artifact → report`, with `resolve` + `verify` before `report`; function `… quarantine-plan → quarantine → promote → export`, every name ≥ `promote` / `export` dispatched earlier), so dispatch is unchanged. |
| `:691` `corrected is not _MISSING` → `!=` (`IsNot_NotEq #2`) | equivalent | `_MISSING` is a fresh `object()` sentinel; the JSON value it is compared with never defines equality with it. |
| `:603` `_text(args.actor, "registered_by", maximum=256)` → 255 / 257 (`NumberReplacer #74`, `#75`) | missing-test → added | the CLI grades the actor before `System(create=True)` makes the ledger (p51): at 257 a 257-byte actor passes the pre-check and leaves a ledger file behind; at 255 a valid 256-byte actor is refused. `tests/test_survivor_pins.py` `test_p111_register_grades_its_actor_before_creating_a_ledger` (256 → exit 0 + file; 257 → exit 2, no file) red on both. |

## p107 — `p26-mutate.txt` (`test_function_verify_drafts_actor_bounds_are_adjacent_pairs` @ 9bd3e7a)

Subjects: `system.py` `System.verify_drafts` + `_text`. Tally: 1026 survivors — 1020 out of scope → `contract-open` by construction (`system.py` 511 outside the subjects, `cli.py` 203, `json_value.py` 106: the ledger + CLI the pin drives); 6 in scope: 2 killed by the modules naming a subject, 4 survived; replayed against HEAD with the full suite minus D28 (`--at HEAD --full`) → 1 killed, 3 left, ruled: `_text` `maximum: int = 512` → 511 / 513 (`NumberReplacer #20`, `#21`) and its keyword-only `*` → `/` (`Mul_Div #3`) = equivalent, as in `## p114` (no call reads the default; every call passes keywords).

## p106 — `p18-mutate.txt` (`test_function_promote_actor_bounds_are_adjacent_byte_pairs` @ 9d6cdf3)

Subjects: `system.py` `System.promote_function` + `_text`. Tally: 1260 survivors — 1224 out of scope → `contract-open` by construction (`system.py` 620 outside the subjects, `cli.py` 210, `json_value.py` 118); 36 in scope: 29 killed, 7 survived; replayed against HEAD with the full suite minus D28 → 1 killed, 6 left (one `ambiguous`: its text repeats inside `promote_function`, mapped by hand below), ruled:

| survivor (`9d6cdf3`) | ruling | basis |
|---|---|---|
| `_text` `:171` `NumberReplacer #20`, `#21`, `Mul_Div #3` | equivalent | as in `## p114`. |
| `:5010` `entry.public.disposition == "candidate"` → `<=` (`Eq_LtE #48`) | equivalent | `disposition` is `Literal["retained", "candidate"]` and `"retained" > "candidate"`, so `==` and `<=` agree. |
| `:5019` `{replaced ids} | set(locked.dropped)` → `^` (`BitOr_BitXor #57`) | equivalent | the two sets are disjoint by the plan's construction: a member a candidate replaces keeps its case key in the new set, so it is never `dropped`; union = symmetric difference. |
| `:5068` `if changed != 1` → `<` (`NotEq_Lt #123`; `ambiguous` at HEAD) | equivalent | `changed` = the `rowcount` of an `UPDATE … WHERE id = ?` on the primary key, so 0 or 1, where `!= 1` and `< 1` agree. |

## p93 — `p93-mutate.txt` (19 subject-scoped credit runs over the pins IMPLEMENT strengthened @ 630f3a9 / ebbfe76 / 313ff6a / b665da1 / 811f583)

Campaign: `uv run python .agent/decisions/p93-campaign.py` = `.agent/mutate <pin> --subject PATH:QUALNAME …` per pin (row p93: L2 ×2, L3, L5, L7, L8, V1, L18, L20, W1, W5, W5c, W10 + the six `CaptureBindingBattery` binding + containment pins; subjects = `survivor-subjects.json`, W5 + W5c naming `System._pin_checks` beside `serving` because they assert the pin checks, the capture pins naming `examples/open_webui/cement_filter.py` `Filter._pairs` / `_retain` / `outlet`). Tally: 531 survivors; triage → 273 killed by the modules naming a subject, 256 survived, 2 rows marked out of scope by the exact-name matcher though they sit in `count`, nested inside `_pin_checks` (ruled below; the matcher now counts a nested definition as its subject's); replayed against HEAD with the full suite minus D28 (`--at HEAD --full`) → 6 killed, 250 rows = 93 distinct mutants left (2 rows `ambiguous`: one `continue` text repeats inside `_pairs`, applied by hand), + the nested one = 94 ruled: 58 missing-test → 14 pins in `tests/test_survivor_pins.py` (`PinCheckPins` 2, `FilterCapturePins` 7, `ProjectionPins` 4, `EvaluatePins` 1), each red on its mutants (`uv run python .agent/kill-check .agent/decisions/p93-mutate.txt <the --at HEAD --full rows> tests.test_survivor_pins` → 82 of 122 section rows killed; the 40 left = the equivalent + contract-open rows below and the hand-applied `continue`, red on `test_p93_extra_arguments_and_an_earlier_malformed_call_keep_the_pair`); 18 equivalent; 18 contract-open.

| survivor (HEAD text) | ruling | basis |
|---|---|---|
| `_pin_checks` `reconstruction.function_hash != function_hash` → `<`, `>`, `is` | missing-test → added | a long-lived `System` reads a pin row forged after it opened (its foreign-key check runs at open): `test_p93_a_pin_naming_another_hash_fails_in_both_orders` (a lower and a higher hash). |
| `_pin_checks` revoked / suspended / counterexample `detail` + `passed` (21: AddNot, `0` → ±1, comparisons other than `<=`) | missing-test → added | no test read a pin check's detail: `test_p93_each_pinned_check_names_its_count`. |
| `_pin_checks` `passed=x == 0` → `<=` ×3, `detail … if x == 0` → `<=` ×3 | equivalent | each `x` = a `COUNT(*)` read through `_stored_int`, never negative. |
| `_pin_checks.count` `fetchone()[0]` → `[-1]` (`NumberReplacer #311`, the nested 2 rows) | equivalent | every `count` query selects `COUNT(*)` alone: a one-column row, so `[0]` and `[-1]` read the same value. |
| `_pairs` `role == "assistant"` → `>=` / `<=` / `is`; `id == message_id` → `<=` / `is`; `role == "user"` → `>=` / `<=` / `is`; `name == USE` → `is` | missing-test → added | the battery's bodies are Python literals, whose interned strings let `is` pass; Open WebUI delivers JSON. `test_p93_only_the_current_answer_counts_bound_to_its_question`: a JSON round-tripped multi-turn body (an earlier turn with its own pair and a lower id, a system message and a role-less message between question and answer, a role-less first message) keeps exactly the current pairs bound to the asking user message. |
| `_pairs` covered-branch AddNot; `name == RECORD` → `is` | missing-test → added | the battery counted one note per defect without reading it: `test_p93_each_defect_note_names_its_call` (a covered record's note; a JSON record without `output` = malformed, never a `KeyError`). |
| `_pairs` `covered is True` → `==` / `>` / `>=`; `isinstance(result, dict) and covered is False` → `or`, `is False` → `==` / `>=` / `<=`; `… and accepted is True` → `or`, `is True` → `==` / `>=` / `<=` | missing-test → added | the outlet body of `/api/chat/completed` is the client's, so only JSON booleans may decide: `test_p93_only_json_booleans_decide_covered_and_accepted` (`covered` 1, 2, 0 and a missing result; `accepted` 1, 2, false, 0 → exact notes, no pair). |
| `_pairs` `chat_id is None or user_message_id is None` → `and` | missing-test → added | the battery's no-id body also lacked the current message id: `test_p93_a_chat_or_a_question_without_an_id_retains_nothing` (each id missing alone). |
| `_pairs` `required <= arguments.keys()` → `==`; the malformed call's `continue` → `break` (hand-applied: the text repeats) | missing-test → added | `<=` is a subset test, so a call carrying more than the required keys is well formed; a malformed call before a valid pair must not end the scan: `test_p93_extra_arguments_and_an_earlier_malformed_call_keep_the_pair`. |
| `_retain` `except CementError` → another class (`ExceptionReplacer #7`) | missing-test → added | the battery raised a `RuntimeError`: `test_p93_a_retention_error_names_its_call` (an enabled but unregistered operation → the note names the call + the library's message). |
| `outlet` `__metadata__ or {}` → `and` | missing-test → added | every battery body carried its user message: `test_p93_the_metadata_names_the_question_the_body_lacks`. |
| `_pairs` `{"operation", "input"} \| …` → `^` | equivalent | the right operand is `{"output"}` or `set()`, disjoint from the left: union = symmetric difference. |
| `_pairs` `name == RECORD` → `<=`; `name == USE` → `>=` | equivalent | the loop `continue`s every name but `use_learned_function` + `record_answer`, and over those two (`"use_learned_function" > "record_answer"`) each ordering has the truth table of `==`. |
| `parse_program` `type(root["abi"]) is not str` → `!=` | missing-test → added | `parse_program(value: object)` grades any object and names the rule it breaks (contract §4); equality can be forged through the metaclass: `test_p93_a_forged_abi_string_is_refused_by_its_rule`. |
| `_structure` `work += len(raw) + 1` (12: `+ 2`, `+ 0`, `& \| ^ // << % * ** >> -` 1), `work += 1` → 2 / 0, `work += len(block[0])` → `[-1]`; `project` the matched layout's `break` → `continue` | contract-open | each changes `work` alone (`break` → `continue` only adds the compares of later same-title layouts, each counted once; the matched layout stays the only one, since title + entries are unique); contract §4 AM4: `work` = any honest counter within the bound, never one algorithm's exact count. I7's bound (`4·len + 2·lines + entries`) and the matched floor (`work ≥ len(text)`) hold for every mutant: the counter starts at `len(text)`, each mutated increment stays within −1 and twice the original per line, and a scratch replay over 3 programs × 4,042 texts (the fixtures, their CRLF forms, edge texts, 4,000 random texts over a structural alphabet, a 5,000-line text) found 0 violations. |
| `project` `type(value) is not dict` → `!=`; `type(value[program.text]) is not str` → `!=` | contract-open | `project`'s domain = the values `canonicalize` accepts (§4: total, never raises for one), and every Cement caller passes one (`evaluate` takes a `CanonicalJSON`; `System` parses stored JSON); the mutants differ only on a class forging type equality, outside that domain. |
| `project` `assert type(text) is str` → `==` | equivalent | the guard above has already established `type(text) is str`. |
| `evaluate` `index == len(bundle.input_hashes)` → `is` | missing-test → added | `is` agrees with `==` only inside CPython's small-int cache: past 256 entries a digest after the last one indexes past the end (`IndexError`, not the inert miss): `test_p93_a_miss_past_every_entry_of_a_large_bundle_is_inert` (257 entries). |
| `evaluate` `index == len(…)` → `>=`; `input_hashes[index] != key.digest` → `>` | equivalent | `bisect_left` returns at most `len` and an index whose hash is ≥ the digest. |
| `evaluate` `entry.input.text != key.text` → `<` | equivalent | the entry sits at the key's digest and validation binds each entry's `input_hash` to its input text (`function.py` `input_json.digest != input_hash` refuses), so the texts differ only under a SHA-256 collision. |
| `evaluate` `not projected.matched or projected.key is None` → `and` | equivalent | `project` sets `key` iff `matched` at every return, so both operands agree. |
| `_case_key_text` `len(memo) >= _CASE_KEY_MEMO_MAX` → `>`, `is` | missing-test → added | `>` holds one key past the bound; `is` never evicts once the bound leaves the small-int cache (the real bound = 65,536), and L20's small capacity hid both: `test_p93_the_case_key_memo_evicts_its_oldest_key_at_its_bound` (bound 300). |
| `_case_key_text` `>=` → `==` | equivalent | each insertion evicts first at the bound, so `len(memo) ≤ _CASE_KEY_MEMO_MAX` holds and `>=` meets only equality. |
| `_case_key_text` `projected.matched and projected.key` → `or` | equivalent | `key` set iff `matched`, and a `CanonicalJSON` (slotted dataclass, no `__bool__` / `__len__`) is always truthy. |
| `set_projection` `_text(actor, "actor", maximum=256)` → 255 / 257 | missing-test → added | the actor byte bound had no adjacent pair here: `test_p93_set_projection_bounds_its_actor_at_256_utf8_bytes` (two-byte characters, as p18). |
| `serving` `state.mode == "follow"` → `<=` | equivalent | `off` returns above; over `follow` and `pinned`, `"pinned" > "follow"`. |
| `_projection_uniform_check` AddNot on `program.program_hash if program else ''` | missing-test → added | no test read the passing detail: `test_p93_the_uniform_check_names_the_program_every_member_projects_with`. |

## p99 — `p17-mutate.txt` (`test_function_promote_rejects_stale_hash_after_qualifying_change` @ 4d9ff42)

Subject: `system.py` `System.promote_function`. Tally: 1170 survivors — 1164 out of scope → `contract-open` by construction (`system.py` outside `promote_function`, `cli.py`, `json_value.py`, `artifacts.py`: the compile + verify + inspect path the pin's fixture runs); 6 in scope: 4 killed by the modules naming the subject, 2 survived (`promoted_by = _text(…, maximum=256)` → 257 / 255, `NumberReplacer #354`, `#355`); replayed against HEAD with the full suite minus D28 → both killed (p18's `test_function_promote_actor_bounds_are_adjacent_byte_pairs`, the adjacent byte pair). No residue.

## p108 — `p29-mutate.txt` (`test_the_real_item_bound_accepts_one_million_and_rejects_one_more` @ d52bbe3)

Subjects: `json_value.py` `_validate`, `canonicalize`, `parse_json`. Tally: 170 survivors — 69 out of scope → `contract-open` by construction (`function.py`, the bundle path the pin drives); 101 in scope: 51 killed by the modules naming a subject, 50 survived; replayed against HEAD with the full suite minus D28 → none killed (46 distinct replays: 46 `survived-at`, 4 `ambiguous` — `remaining_items[0]` repeats in the list and dict branches), ruled: 45 missing-test → three pins in `tests/test_survivor_pins.py` `JSONBoundaryPins`, red on each (`uv run python .agent/kill-check .agent/decisions/p29-mutate.txt <the --at HEAD --full rows> tests.test_survivor_pins.JSONBoundaryPins` → 45/50 killed, the 5 left = the equivalent rows below); 5 equivalent.

| survivor (`d52bbe3`) | ruling | basis |
|---|---|---|
| `_validate` `:39` `type(value) is bool` / `is str` → `==`, `:41` `is int`, `:45` `is float`, `:47` `is list`, `:59` `is dict` → `==`, `:64` `type(key) is not str` → `!=` | missing-test → added | `canonicalize(value: Any)` grades any caller object and `_validate` owns the messages (`json.dumps` = the defensive second line); equality can be forged through the metaclass, which sends the object to `json.dumps` or a comparison instead: `test_p108_canonicalize_refuses_classes_forging_equality_by_its_own_rules`. |
| `_validate` `:42` `MIN_INTEGER <= value` → `MIN_INTEGER is not value` (`LtE_IsNot #0`) | missing-test → added | the mutant admits every integer below the range; only the upper end had an adjacent pair: `test_p108_the_integer_range_is_an_adjacent_pair_at_both_ends`. |
| `canonicalize` `:91`-`:96` + `parse_json` `:142`-`:147` limit guard (37: `type(limit) is not int` → `!=` ×6; `max_bytes < 1` → `< 2` / `< 0` / `== 1` / `<= 1`, `max_depth` + `max_items` `< 0` → `< 1` / `< -1` / `== 0` / `<= 0`, each guard's `or` → `and`) | missing-test → added | no test graded the guard: `test_p108_json_limits_are_adjacent_pairs_of_exact_ints` (each limit's floor accepted, floor − 1, a float and a forged class refused, beside an invalid input: `parse_json` ends in `canonicalize`, whose same guard otherwise masks a weakened `parse_json` guard for `max_depth` + `max_items`). |
| `_validate` `:48` `:49` `:60` `:61` `remaining_items[0]` → `[-1]` | equivalent | `remaining_items` is always the one-element list `[max_items]` (`canonicalize` builds it; every recursion passes the same list). |
| `canonicalize` `:108` `allow_nan=False` → `True` | equivalent | `_validate` refuses every float first (`type(value) is float`; a float subclass reaches the final "not JSON" raise), so `json.dumps` never meets one. |

## p109 — `p28-mutate.txt` (`test_entry_digest_syntax_rejects_after_outer_rehash` + `test_function_verification_pins_each_projected_document_field` @ e546edd)

Subjects: `function.py` `_digest` + `validate_function`; `system.py` `System._verify_function_snapshot`. Tally: 1346 survivors — 1268 out of scope → `contract-open` by construction; 78 in scope: 8 killed by the modules naming a subject, 70 survived; replayed against HEAD (`--at HEAD`) → 9 killed, 12 survived, 49 `superseded` (the p32 refactor split `_verify_function_snapshot` into `System._snapshot_member` + module helpers); the 12 against the full suite minus D28 → 4 killed, 8 left; the 49 again with moved-code placement (stripped text, re-indented) + the full suite → 15 killed, 11 left, 23 still unplaced (their text was rewritten, not just moved). The 23 were mapped by hand onto the snapshot path's own check at HEAD (`_snapshot_policy_failures`, `_duplicate_digest_check`, `System._snapshot_member`'s report block, its scope + field calls inlined with the mutated comparison): 5 ruled equivalent without a replay (below), 18 replayed through `uv run python .agent/replay-mutants .agent/decisions/p109-mapped-mutants.jsonl` (base ee9bead, the full suite minus D28 + `test_source`, `ran` 1454) → 17 killed, `PASSED-LT` survived. Residue = 8 + 11 + 23 = 42: 17 killed at HEAD (mapped), 4 missing-test → three pins (`tests/test_survivor_pins.py` `test_p109_a_digest_field_refuses_a_class_forging_equality`, `SnapshotScopePins` 2), each red on its mutants, 21 equivalent (`PASSED-LT` included).

| survivor (`e546edd`, HEAD place) | ruling | basis |
|---|---|---|
| `function.py:105` `_digest` `type(value) is not str` → `!=` | missing-test → added | `validate_function` reads every entry digest from a caller document; equality can be forged through the metaclass: `test_p109_a_digest_field_refuses_a_class_forging_equality`. |
| `:3011` `:3016` `:3018` `type(registered[…]) is not int` / `str` → `!=` | equivalent | values the SQLite driver returns (`int`, `str`, `bytes`, `float`, `None`), whose classes never forge equality. |
| `:3161` `type(details.value) is not dict` → `!=` | equivalent | `details` = `parse_json` output: JSON types alone. |
| `:3097` `len(rows) != entry_count` → `>` / `<` | equivalent | dead defensive check: the count and the rows come from one read snapshot under one predicate; reaching it needs a mock of the module's own enumeration, which would grade the mock. |
| `:3248` `entry_count == 0` → `<=` | equivalent | a `COUNT(*)`, never negative. |
| `_snapshot_abi_failure` (`:3139`, `:3143`) `type(raw_artifact) is not dict` → `!=`, `type(raw_scope) is dict` → `==` | equivalent | `parse_json` output. |
| `_snapshot_scope_failures` (`:3185`) `type(stored_revision) is not int` → `!=` | equivalent | a SQLite driver value. |
| `_snapshot_scope_failures` (`:3187`) `stored_revision != revision` → `is not` | missing-test → added | two reads of one revision agree by identity only inside CPython's small-int cache; past revision 256 the set fails: `test_p109_a_set_past_revision_256_verifies` (revision 257). |
| `_snapshot_scope_failures` (`:3191`, `:3193`) `row["policy_hash"] != policy_hash`, `row["policy_json"] != policy_json` → `>` | missing-test → added | the battery forged one order each (a lower operation hash, a higher member JSON): `test_p109_a_member_policy_mismatch_fails_in_both_orders` (hash `0…` + `f…`; JSON of `CompilePolicy(3, 1, 0)` + `(10, 1, 0)`). |
| `_snapshot_projection` (`:3224`) `input_json.digest != row["input_hash"]` → `>`; (`:3228`) `output_json.digest != row["output_hash"]` → `>`, `is`, `<` (unplaced) | equivalent | dead defensive checks: `_artifact_from_row` refuses the row first unless its `input_hash` / `output_hash` equal the artifact's digests, and the entry carries the artifact's own values, so the re-canonicalized digests equal the row's. |
| `_snapshot_hash_check` (`:3305`, `:3307`, `:3309`) `abi` / `canonicalizer` / `function_hash` `!=` → `<`; (`:3320`) `type(actual_entries) is not list` → `!=` | equivalent | self-checks of the document `build_function` has just built from the projected entries: its ABI, canonicalizer and hash are its own constants and its entries a `list`, so neither operand differs. |
| `:3024` `canonicalize(policy.as_json(), max_bytes=16_384)` → 16385 / 16383 (unplaced; HEAD `_policy_binding`) | equivalent | a `CompilePolicy`'s canonical JSON = three bounded integers, under 100 bytes, far inside either bound. |
| `PASSED-LT`: `:3158` `report["passed"] != 1` → `< 1` (mapped onto `System._snapshot_member`) | equivalent | `test_reports.passed` carries `CHECK (passed IN (0, 1))`. |
| the other 17 mapped (`:3028` / `:3030` policy text + digest `>` / `is` / `<`, `:3107` `continue` → `break`, `:3158` `> 1` + `or` → `and`, `:3160` `verify_test_set=False`, `:3163` scope `>` / `is` / `<`, `:3165` the field loop emptied, `:3171` field `>` / `is` / `<`) | killed at HEAD | `.agent/decisions/p109-mapped-mutants.jsonl`, each id = its mapped row. |
