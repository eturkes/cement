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
