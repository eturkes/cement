# Python type-checker spike results

## ty

- M1 native install command: none; `uv check` resolves and runs ty itself. `uv check --isolated --verbose` logged `Resolved ty@>=0.0, <0.1 to ty==0.0.79`. The command is experimental and warns unless `--preview-features check-command` is set.
- M1 standalone install command: `uv add --dev ty`
- M1 resolved-version parity: **yes** — native `uv check` and `uv run ty --version` both resolved `ty 0.0.79`; native also accepts the gate pin `--ty-version 0.0.79`
- M2 warm-up command: `uv run ty check src/cement_runtime --output-format concise --no-progress --color never`
- M2 measured command: `/usr/bin/time -f '%e' uv run ty check src/cement_runtime --output-format concise --no-progress --color never`
- M2 best-of-3 wall time: **0.23 s** (`0.23`, `0.25`, `0.29` s after one warm-up)
- M2 total diagnostics: **3**
- M2 diagnostics by rule (top 10): `call-non-callable` 2; `redundant-cast` 1
- M2 native warm-up command: `uv check --isolated --color never --no-progress` (native has no positional source-path argument)
- M2 native measured command: `/usr/bin/time -f '%e' uv check --isolated --color never --no-progress`
- M2 native best-of-3 wall time: **0.91 s** (`0.93`, `0.91`, `0.92` s); stateful `uv check` best = **0.79 s** (`0.93`, `0.79`, `0.88` s)
- M2 native diagnostic count: **685** project-wide; filtering real GitLab JSON paths to `src/cement_runtime/` gives **1**, `redundant-cast` 1
- M2 path parity: **no** despite version parity — standalone explicit-source mode gives 3 source diagnostics, while native mode gives 1. Native omits the two `store.py:617,619` `call-non-callable` findings. A same-wave standalone rerun measured `0.14`, `0.14`, `0.15` s and reproduced all 3.
- M2 isolation effect: `--isolated` left `.venv` absent; stateful `uv check` created `.venv`. Both left `pyproject.toml` and `uv.lock` byte-identical. For a gate, isolation prevents environment mutation/coupling for a measured ~0.12 s best-run cost.
- M3 strictest preset source/name: no named strict preset; documented maximum = `--error all`, which enables every rule as an error ([Astral rules documentation](https://docs.astral.sh/ty/rules/))
- M3 warm-up command: `uv run ty check src/cement_runtime --error all --output-format concise --no-progress --color never`
- M3 measured command: `/usr/bin/time -f '%e' uv run ty check src/cement_runtime --error all --output-format concise --no-progress --color never`
- M3 best-of-3 wall time: **0.27 s** (`0.28`, `0.27`, `0.28` s)
- M3 total diagnostics: **13**
- M3 diagnostics by rule (top 10): `unsound-return-statement` 6; `redundant-condition-strict` 2; `call-non-callable` 2; `missing-override-decorator` 1; `redundant-cast` 1; `unsound-assignment` 1
- M4 warm-up command: `uv run ty check src tests examples --output-format concise --no-progress --color never`
- M4 measured command: `/usr/bin/time -f '%e' uv run ty check src tests examples --output-format concise --no-progress --color never`
- M4 best-of-3 wall time: **0.62 s** (`0.80`, `0.62`, `0.86` s)
- M4 total diagnostics: **313**
- M5 standalone diagnostic-tree exit code: **1** from the M2 `uv run ty check` command
- M5 native diagnostic-tree exit code: **1** from both `uv check --isolated --color never --no-progress` and stateful `uv check --color never --no-progress`
- M5 standalone clean subset/file: `src/cement_runtime/artifacts.py`; output = `All checks passed!`
- M5 standalone clean exit code: **0** from `uv run ty check src/cement_runtime/artifacts.py --output-format concise --no-progress --color never`
- M5 native clean subset/file: a temporary PEP 723 script containing one annotated `twice(int) -> int` function; output = `All checks passed!`
- M5 native clean exit code: **0** from `uv check --isolated --script .measure/uv-check/clean_script.py --color never --no-progress`
- M6 standalone machine-readable format/flag: GitLab Code Quality JSON via `--output-format gitlab` (JUnit XML is also available)
- M6 native CLI exposure: **none** — `uv check --isolated --output-format gitlab` and `uv check --isolated -- --output-format gitlab` both exit 2 with `unexpected argument '--output-format' found`
- M6 native environment fallback: `TY_OUTPUT_FORMAT=gitlab uv check --isolated --ty-version 0.0.79 --preview-features check-command --no-progress --color never` emits valid GitLab JSON on stdout (685 objects); isolated installation progress remains on stderr. This works by inherited ty environment, not a uv flag or pass-through.
- M6 real output excerpt: `[` / `  {` / `    "check_name": "invalid-argument-type",`
- M7 suppression edit: changed `from typing import Any` to `from typing import Any  # ty: ignore` in `src/cement_runtime/artifacts.py`
- M7 exact command/setting: `uv run ty check src/cement_runtime/artifacts.py --error all --output-format concise --no-progress --color never`
- M7 flagged?: **yes**
- M7 evidence: `error[blanket-ignore-comment] Use specific rule codes in ty: ignore`; `error[unused-ignore-comment] Unused blanket ty: ignore directive`; exit **1**
- M7 revert proof: `git checkout -- src/cement_runtime/artifacts.py` rc 0; targeted `git status --porcelain -- src/cement_runtime/artifacts.py` = empty, rc 0; positive control found the restored import exactly once
- M8 top-five M2 rules inspected: only two rules existed: `call-non-callable` (2) and `redundant-cast` (1); all 3 diagnostics inspected
- M8 top-20 genuine defects: **1/3** — the redundant `cast(...)` is removable type-checking debt, not a runtime defect
- M8 top-20 tool limitations: **2/3** — ty types the Python-version-conditional `sqlite3.Connection.setconfig` attribute as possibly `object` after the runtime `hasattr` guard
- M8 three representative diagnostics and source lines:
  1. ``src/cement_runtime/store.py:617:21: error[call-non-callable] Object of type `object` is not callable`` — `connection.setconfig(defensive, True)` (tool limitation)
  2. ``src/cement_runtime/store.py:619:21: error[call-non-callable] Object of type `object` is not callable`` — `connection.setconfig(trusted, False)` (tool limitation)
  3. ``src/cement_runtime/system.py:3236:32: warning[redundant-cast] Value is already of type `Literal["draft", "verified", "promoted", "suspended", "retired"]` `` — `status=cast(...)` (genuine redundant typing construct)
- M9 zero-diagnostic configuration/result: not run — M2 rank 3 (3 diagnostics), outside the two lowest-count tools

## pyrefly

- M1 install command: `uv add --dev pyrefly`
- M1 resolved version: `pyrefly 1.2.0`
- M2 warm-up command: `uv run pyrefly check src/cement_runtime --output-format min-text --summary=none --progress-bar no`
- M2 measured command: `/usr/bin/time -f '%e' uv run pyrefly check src/cement_runtime --output-format min-text --summary=none --progress-bar no`
- M2 best-of-3 wall time: **0.26 s** (`0.26`, `0.27`, `0.30` s after one warm-up)
- M2 total diagnostics: **0**; exit 0. A separate `--summary=full` positive control reported `13 modules` and `9,136 lines in your project`; an unconfigured invocation selects Pyrefly's `basic` preset.
- M2 diagnostics by rule (top 10): none
- M3 strictest preset source/name: `--preset all`; CLI help defines it as every error kind at `Error` severity
- M3 warm-up command: `uv run pyrefly check src/cement_runtime --preset all --output-format min-text --summary=none --progress-bar no`
- M3 measured command: `/usr/bin/time -f '%e' uv run pyrefly check src/cement_runtime --preset all --output-format min-text --summary=none --progress-bar no`
- M3 best-of-3 wall time: **0.23 s** (`0.24`, `0.25`, `0.23` s)
- M3 total diagnostics: **449**
- M3 diagnostics by rule (top 10): `unused-call-result` 186; `unknown-argument-type` 157; `implicit-bool` 44; `explicit-any` 31; `unknown-variable-type` 14; `unnecessary-type-conversion` 8; `deprecated` 2; `implicit-any-lambda` 2; `missing-override-decorator` 1; `no-any-return-implicit` 1
- M4 warm-up command: `uv run pyrefly check src tests examples --output-format min-text --summary=none --progress-bar no`
- M4 measured command: `/usr/bin/time -f '%e' uv run pyrefly check src tests examples --output-format min-text --summary=none --progress-bar no`
- M4 best-of-3 wall time: **0.50 s** (`0.51`, `0.51`, `0.50` s)
- M4 total diagnostics: **10**
- M5 diagnostic-tree exit code: **1** from the M4 default command (10 diagnostics)
- M5 clean subset/file: `src/cement_runtime/artifacts.py`; output was empty, while the positive control found its `ArtifactDocument` class once
- M5 clean exit code: **0** from `uv run pyrefly check src/cement_runtime/artifacts.py --output-format min-text --summary=none --progress-bar no`
- M6 machine-readable format/flag: JSON via `--output-format json` (JUnit XML and Code Climate JSON are also available)
- M6 real output excerpt: `{` / `  "errors": [` / `    {`
- M7 suppression edit: changed `from typing import Any` to `from typing import Any  # type: ignore` in `src/cement_runtime/artifacts.py`
- M7 exact command/setting: `uv run pyrefly check src/cement_runtime/artifacts.py --preset all --enabled-ignores type --output-format min-text --summary=none --progress-bar no`
- M7 flagged?: **yes**
- M7 evidence: `ERROR src/cement_runtime/artifacts.py:6:1-2: Unused # type: ignore comment [unused-type-ignore]`; exit **1**
- M7 revert proof: `git checkout -- src/cement_runtime/artifacts.py` rc 0; targeted `git status --porcelain -- src/cement_runtime/artifacts.py` = empty, rc 0; positive control found the restored import exactly once
- M8 top-five M2 rules inspected: none existed; all **0** M2 diagnostics were inspected
- M8 top-20 genuine defects: **0/0**
- M8 top-20 tool limitations: **0/0**
- M8 three representative diagnostics and source lines: not applicable — M2 emitted no diagnostics, so three real M2 diagnostics do not exist
- M9 zero-diagnostic configuration/result: **yes** with the smallest explicit stanza `[tool.pyrefly]` + `preset = "basic"`; `uv run pyrefly check src/cement_runtime --output-format min-text --summary=full --progress-bar no` returned exit 0, `0 errors`, and `13 modules`. No rule is manually suppressed: the stanza names Pyrefly's documented unconfigured-project preset. An empty `[tool.pyrefly]` table instead selects the configured-project default and leaves **1** `bad-assignment`: `src/cement_runtime/system.py:2089: list[str] is not assignable to dict value type bool | dict[str, JSONValue] | int | list[JSONValue] | str | None`.

## mypy

- M1 install command: `uv add --dev mypy`
- M1 resolved version: `mypy 2.3.1 (compiled: yes)`
- M2 warm-up command: `uv run mypy src/cement_runtime --show-error-codes --no-pretty --no-color-output`
- M2 measured command: `/usr/bin/time -f '%e' uv run mypy src/cement_runtime --show-error-codes --no-pretty --no-color-output`
- M2 best-of-3 wall time: **0.21 s** (`0.23`, `0.24`, `0.21` s after one warm-up)
- M2 total diagnostics: **4** (`checked 13 source files`)
- M2 diagnostics by rule (top 10): `assignment` 4
- M3 strictest preset source/name: `--strict`; CLI help documents the complete flag bundle that it enables
- M3 warm-up command: `uv run mypy src/cement_runtime --strict --show-error-codes --no-pretty --no-color-output`
- M3 measured command: `/usr/bin/time -f '%e' uv run mypy src/cement_runtime --strict --show-error-codes --no-pretty --no-color-output`
- M3 best-of-3 wall time: **0.24 s** (`0.24`, `0.26`, `0.26` s)
- M3 total diagnostics: **7**
- M3 diagnostics by rule (top 10): `assignment` 4; `no-any-return` 2; `redundant-cast` 1
- M4 warm-up command: `uv run mypy src tests examples --show-error-codes --no-pretty --no-color-output`
- M4 measured command: `/usr/bin/time -f '%e' uv run mypy src tests examples --show-error-codes --no-pretty --no-color-output`
- M4 best-of-3 wall time: **0.22 s** (`0.27`, `0.29`, `0.22` s)
- M4 total diagnostics: **311** (`checked 37 source files`)
- M5 diagnostic-tree exit code: **1** from the M2 command
- M5 clean subset/file: `src/cement_runtime/artifacts.py`; output = `Success: no issues found in 1 source file`
- M5 clean exit code: **0** from `uv run mypy src/cement_runtime/artifacts.py --show-error-codes --no-pretty --no-color-output`
- M6 machine-readable format/flag: newline-delimited JSON via `-O json`
- M6 real output excerpt: `{"file": "src/cement_runtime/system.py", "line": 3902, ... "code": "assignment", "severity": "error"}` / `{"file": "src/cement_runtime/system.py", "line": 4483, ...}` / `{"file": "src/cement_runtime/cli.py", "line": 606, ...}`
- M7 suppression edit: changed `from typing import Any` to `from typing import Any  # type: ignore` in `src/cement_runtime/artifacts.py`
- M7 exact command/setting: `uv run mypy src/cement_runtime/artifacts.py --warn-unused-ignores --show-error-codes --no-pretty --no-color-output`
- M7 flagged?: **yes**
- M7 evidence: `src/cement_runtime/artifacts.py:6: error: Unused "type: ignore" comment [unused-ignore]`; exit **1**
- M7 revert proof: `git checkout -- src/cement_runtime/artifacts.py` rc 0; targeted `git status --porcelain -- src/cement_runtime/artifacts.py` = empty, rc 0; positive control found the restored import exactly once
- M8 top-five M2 rules inspected: only `assignment` existed; all 4 diagnostics inspected
- M8 top-20 genuine defects: **4/4** — all correctly expose function-scope variable reuse across branches (`str`→`str | None`, `FunctionMatch`→`FunctionMatch | None`, `bool`→`tuple[str, ...]`); these are static typing defects, not observed runtime defects
- M8 top-20 tool limitations: **0/4**
- M8 three representative diagnostics and source lines:
  1. `src/cement_runtime/system.py:3902: error: Incompatible types in assignment (expression has type "str | None", variable has type "str") [assignment]` — `input_json = canonical_inputs.get(input_hash)`
  2. `src/cement_runtime/cli.py:606: error: Incompatible types in assignment (expression has type "FunctionMatch | None", variable has type "FunctionMatch") [assignment]` — `match = resolution.match`
  3. `src/cement_runtime/cli.py:692: error: Incompatible types in assignment (expression has type "tuple[str, ...]", variable has type "bool") [assignment]` — `suspended = system.revoke_example(...)`
- M9 zero-diagnostic configuration/result: not run — M2 rank 4 (4 diagnostics), outside the two lowest-count tools

## pyright

- M1 install command: `uv add --dev pyright`
- M1 resolved version: `pyright 1.1.411`
- M2 warm-up command: `uv run pyright src/cement_runtime --outputjson`
- M2 measured command: `/usr/bin/time -f '%e' uv run pyright src/cement_runtime --outputjson`
- M2 best-of-3 wall time: **2.22 s** (`2.27`, `2.22`, `2.31` s after one warm-up)
- M2 total diagnostics: **0**; exit 0 and JSON summary reported `filesAnalyzed: 13`
- M2 diagnostics by rule (top 10): none
- M3 strictest preset source/name: documented `typeCheckingMode = "strict"`; temporary project JSON contained only `{"typeCheckingMode": "strict"}`
- M3 warm-up command: `uv run pyright --project .measure/pyright/strict.json src/cement_runtime --outputjson`
- M3 measured command: `/usr/bin/time -f '%e' uv run pyright --project .measure/pyright/strict.json src/cement_runtime --outputjson`
- M3 best-of-3 wall time: **2.32 s** (`2.46`, `2.56`, `2.32` s)
- M3 total diagnostics: **24**
- M3 diagnostics by rule (top 10): `reportUnknownArgumentType` 9; `reportUnknownVariableType` 8; `reportDeprecated` 2; `reportUnnecessaryIsInstance` 2; `reportPrivateUsage` 1; `reportConstantRedefinition` 1; `reportUnnecessaryCast` 1
- M4 warm-up command: `uv run pyright src tests examples --outputjson`
- M4 measured command: `/usr/bin/time -f '%e' uv run pyright src tests examples --outputjson`
- M4 best-of-3 wall time: **7.98 s** (`7.98`, `8.04`, `8.07` s)
- M4 total diagnostics: **315** (`filesAnalyzed: 37`)
- M5 diagnostic-tree exit code: **1** from the M3 strict command (24 diagnostics)
- M5 clean subset/file: all of `src/cement_runtime` under default settings
- M5 clean exit code: **0** from the M2 command; its JSON summary is the positive control (`filesAnalyzed: 13`, zero diagnostics)
- M6 machine-readable format/flag: JSON via `--outputjson`
- M6 real output excerpt: `{` / `    "version": "1.1.411",` / `    "time": "1788929651084",`
- M7 suppression edit: changed `from typing import Any` to `from typing import Any  # type: ignore` in `src/cement_runtime/artifacts.py`
- M7 exact command/setting: temporary config `{"reportUnnecessaryTypeIgnoreComment": "error"}`; `uv run pyright --project .measure/pyright/unused.json src/cement_runtime/artifacts.py --outputjson`
- M7 flagged?: **yes**
- M7 evidence: `reportUnnecessaryTypeIgnoreComment Unnecessary "# type: ignore" comment` at line 6; exit **1**
- M7 revert proof: `git checkout -- src/cement_runtime/artifacts.py` rc 0; targeted `git status --porcelain -- src/cement_runtime/artifacts.py` = empty, rc 0; positive control found the restored import exactly once
- M8 top-five M2 rules inspected: none existed; all **0** M2 diagnostics were inspected
- M8 top-20 genuine defects: **0/0**
- M8 top-20 tool limitations: **0/0**
- M8 three representative diagnostics and source lines: not applicable — M2 emitted no diagnostics, so three real M2 diagnostics do not exist
- M9 zero-diagnostic configuration/result: **yes** with the non-suppressive stanza `[tool.pyright]` + `include = ["src/cement_runtime"]`; `uv run pyright --outputjson` returned exit 0 with `filesAnalyzed: 13` and zero diagnostics. This inherits the active Python 3.13 environment. Adding the project-minimum `pythonVersion = "3.11"` instead leaves **2** `reportAttributeAccessIssue` diagnostics at `store.py:617,619` because `sqlite3.Connection.setconfig` was added after 3.11 despite the runtime `hasattr` guard.

## basedpyright

- M1 install command: `uv add --dev basedpyright`
- M1 resolved version: `basedpyright 1.40.0` (`based on pyright 1.1.412`)
- M2 warm-up command: `uv run basedpyright src/cement_runtime --outputjson`
- M2 measured command: `/usr/bin/time -f '%e' uv run basedpyright src/cement_runtime --outputjson`
- M2 best-of-3 wall time: **2.66 s** (`2.66`, `2.91`, `3.83` s after one warm-up)
- M2 total diagnostics: **1,086** = 1 error + 1,085 warnings; default `recommended` mode and `failOnWarnings` produced exit 1; `filesAnalyzed: 13`
- M2 diagnostics by rule (top 10): `reportAny` 823; `reportUnusedCallResult` 186; `reportExplicitAny` 32; `reportUnannotatedClassAttribute` 11; `reportUnknownArgumentType` 9; `reportUnknownVariableType` 8; `reportUnreachable` 4; `reportImplicitStringConcatenation` 4; `reportDeprecated` 3; `reportUnnecessaryIsInstance` 2
- M3 strictest preset source/name: documented `typeCheckingMode = "all"`; temporary project JSON contained only `{"typeCheckingMode": "all"}`
- M3 warm-up command: `uv run basedpyright --project .measure/basedpyright/all.json src/cement_runtime --outputjson`
- M3 measured command: `/usr/bin/time -f '%e' uv run basedpyright --project .measure/basedpyright/all.json src/cement_runtime --outputjson`
- M3 best-of-3 wall time: **2.52 s** (`2.65`, `2.73`, `2.52` s)
- M3 total diagnostics: **1,086**, all errors
- M3 diagnostics by rule (top 10): `reportAny` 823; `reportUnusedCallResult` 186; `reportExplicitAny` 32; `reportUnannotatedClassAttribute` 11; `reportUnknownArgumentType` 9; `reportUnknownVariableType` 8; `reportUnreachable` 4; `reportImplicitStringConcatenation` 4; `reportDeprecated` 3; `reportUnnecessaryIsInstance` 2
- M4 warm-up command: `uv run basedpyright src tests examples --outputjson`
- M4 measured command: `/usr/bin/time -f '%e' uv run basedpyright src tests examples --outputjson`
- M4 best-of-3 wall time: **8.99 s** (`9.35`, `8.99`, `9.13` s)
- M4 total diagnostics: **6,509** = 472 errors + 6,037 warnings; `filesAnalyzed: 37`
- M5 diagnostic-tree exit code: **1** from the M2 command
- M5 clean subset/file: constructed root `checker_clean.py` containing one fully annotated `twice(int) -> int` function; JSON positive control reported `filesAnalyzed: 1`, zero diagnostics
- M5 clean exit code: **0** from `uv run basedpyright checker_clean.py --outputjson`
- M6 machine-readable format/flag: JSON via `--outputjson`
- M6 real output excerpt: `{` / `    "version": "1.40.0",` / `    "time": "1788930152890",`
- M7 suppression edit: changed `from typing import Any` to `from typing import Any  # type: ignore` in `src/cement_runtime/artifacts.py`
- M7 exact command/setting: temporary config `{"enableTypeIgnoreComments": true, "reportUnnecessaryTypeIgnoreComment": "error"}`; `uv run basedpyright --project .measure/basedpyright/unused.json src/cement_runtime/artifacts.py --outputjson`
- M7 flagged?: **yes**
- M7 evidence: line 6 `reportUnnecessaryTypeIgnoreComment Unnecessary "# type: ignore" comment` (error), plus `reportIgnoreCommentWithoutRule`; exit **1**
- M7 revert proof: `git checkout -- src/cement_runtime/artifacts.py` rc 0; targeted `git status --porcelain -- src/cement_runtime/artifacts.py` = empty, rc 0; positive control found the restored import exactly once
- M8 top-five M2 rules inspected: `reportAny`, `reportUnusedCallResult`, `reportExplicitAny`, `reportUnannotatedClassAttribute`, `reportUnknownArgumentType`; three source examples per rule inspected, plus the first 20 diagnostics in output order
- M8 top-20 genuine defects: **0/20** — no observed runtime or soundness defect; the findings demand explicit discard markers or reject deliberate dynamic-boundary `Any`
- M8 top-20 tool limitations: **20/20** — policy mismatch/noise: intentional ignored `write`/`wait`/`flush` returns and exact runtime validation of `json.loads`/public `Any` inputs
- M8 three representative diagnostics and source lines:
  1. `src/cement_runtime/_command_supervisor.py:110: warning[reportUnusedCallResult] Result of call expression is of type "int" and is not used; assign to variable "_" if this is intentional` — `stream.write(request)`
  2. `src/cement_runtime/_command_supervisor.py:119: warning[reportAny] Type of "value" is Any` — `value = json.loads(...)`
  3. ``src/cement_runtime/artifacts.py:62: warning[reportExplicitAny] Type `Any` is not allowed`` — `def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:`
- M9 zero-diagnostic configuration/result: not run — M2 rank 5 (1,086 diagnostics), outside the two lowest-count tools
