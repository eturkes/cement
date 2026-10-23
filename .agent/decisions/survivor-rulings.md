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

Subjects: `system.py` `System._canonical_candidate` (the provenance type check) + `System.submit_proposal`. Tally: 281 survivors — 280 out of scope → `contract-open` by construction (`store.py` 79, `models.py` 76 = `CompilePolicy.__post_init__`, `json_value.py` 74, `system.py` 51 outside the subjects: the fixture's ledger, policy and candidate canonicalization); 1 in scope, `system.py:739` `System._canonical_candidate` `ReplaceComparisonOperator_IsNot_NotEq #10` → killed by the 16 modules naming a subject (D28 excluded). No ruling owed.
