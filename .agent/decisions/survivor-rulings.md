# Survivor rulings (p93, p99-p116)

Rule (owner-ruled, `.claude/rules/assurance.md` Survivor scope): a credit run's survivor needs a ruling
only inside the pin's named subject; every survivor outside it is `contract-open` by construction.
Mechanics: `uv run python .agent/survivor-triage .agent/decisions/<record>-mutate.txt` with subjects
from `.agent/decisions/survivor-subjects.json` (rerunnable from committed state: the record names its
revision, the tool rebuilds each in-scope mutant there with cosmic-ray and replays it against every test
module that names a subject, D28 excluded). Rulings below are MAIN's (owner: the backlog is MAIN alone).

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
