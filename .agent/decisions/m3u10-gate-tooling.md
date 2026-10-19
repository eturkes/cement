# Gate tooling unit — measurements + seeds (M3.10)

Owner rulings: `.agent/spec.md` Decisions gate tooling (versions = latest at IMPLEMENT
orientation). Grounds behind the checker pick: `m3u10-checker-spike.md`; CI + update automation:
`m3u10-ci-research.md` (R1-R9; R10's workflow superseded by `.github/workflows/gate.yml`, whose
action SHAs were re-fetched from each repo's `releases/latest` → `commits/<tag>`).

## Versions pinned

| tool | pin | where |
|---|---|---|
| ruff | 0.17.1 | `[dependency-groups] dev`, `uv.lock` |
| mypy | 2.4.0 | same |
| cosmic-ray | 8.7.0 | same |
| gitleaks | 8.30.1, sha256 per platform | `.agent/gitleaks` (downloads into gitignored `.tools/`) |
| uv | 0.13.1 (`uv audit` native, preview) | CI `setup-uv` `version:`; `uv_build>=0.13.1,<0.14` |
| actions/checkout | v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1` | `gate.yml` |
| astral-sh/setup-uv | v10.3.0 `1c37ad07a6a961277cf70c0d37d6f313000f5884` | `gate.yml` |
| actions/cache | v6.1.0 `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` | `gate.yml` (restore + save) |

## Baseline findings → disposition

- `ruff format` (line length 100): 5 `src` files + 3 example files + 1 README Python block (ruff
  0.17 formats fenced Python in Markdown; 2 PEP 8 blank lines).
- `ruff check`, selection in `pyproject.toml`: 48 findings over `src` before fixes; after
  `--fix` + hand fixes, 0. Reasoned inline `noqa` (p01: inline + reasoned): S603 ×2 + S101 ×4 +
  BLE001 ×4 in the command runtime (M3.7 relocates it); S608 ×4 (only code-chosen SQL
  fragments interpolate, every value binds as `?`); N818 ×2 (private signals); PLW0603 ×1 (lazy
  schema constant); SIM118 ×1 — a ruff FALSE POSITIVE here: `in` on a `sqlite3.Row` tests values,
  only `keys()` tests column names. Global ignore: SIM105 (explicit `try/except: pass` names the
  swallowed class). Examples: per-file S101 + T201 (the demo's asserts sit behind its `-O`
  refusal; its transcript is stdout). `RUF100` (unused noqa) = 0, enforced by the `RUF` selection.
- `mypy --strict` + `warn_unreachable` + `ignore-without-code`/`redundant-expr`/`truthy-bool`:
  10 errors → 0 — function-scope variable reuse across branches (`cli._run` `match`/`suspended`,
  `system` `input_json` ×2), an `Any` stdin read, an `Any` `fetchone`, one redundant cast.
- `uv audit`: 34 packages (dev tools), 0 vulnerabilities.
- gitleaks over 280 commits: 6 `generic-api-key` hits, all false positives, ignored by exact
  fingerprint in `.gitleaksignore` (5 prose lines about duplicate object keys and decimal
  exponents; 1 probe-driver test sentinel). The scan covers HEAD's history = what ships, the same
  in a clean CI clone; local unpublished branches and archive tags are out of scope.
- skip census: 3 sites = the 3 allowed (2 `platform`, 1 `replay-pruned`).
- register audit: 5 surfaces, 0 filler; longest sentence 37 words (`docs/architecture.md`),
  printed for the judgment pass, never graded.

## Seeds (each run by MAIN, rc recorded)

| check | seed | rc |
|---|---|---|
| format | `x  =  1` appended to `src/cement_runtime/errors.py` | 1 |
| lint | `import os` appended (F401) | 1 |
| lint RUF100 | `ok = 1  # noqa: F401` appended (unused noqa) | 1 |
| types | `def _seed() -> int: return "x"` appended | 1 |
| audit | scratch project, dev dep `jinja2==2.10`, `uv lock` + `uv audit --locked` | 1 (12 vulns) |
| secrets | scratch repo committing a random `ghp_…` token; `.agent/gitleaks git … <repo>` | 1 |
| skips | copy of `tests/` + a fourth `self.skipTest("seed")` | 1, names `SeededSkip.test_seeded_fourth_skip` |
| register | `Run the command simply …` | 1 (`FILLER … simply`) |
| register | one 30-word sentence + a punctuation-free bullet + `Cement's` | 0, prints `[30]`, contraction 0 |

Every seed restores byte-identical (`git diff --quiet` rc 0 on the seeded file).

## p74 — mutation credit tool trial

Command: `uv run python .agent/mutate <test id> --rev <rev> --workers 1` (cosmic-ray 8.7.0, default
operators, scope = the `src/cement_runtime` lines the pin executes in a traced baseline run).
Pin = `tests.test_json_value.CanonicalJSONTests.test_parser_rejects_ambiguous_or_unbounded_values`
(scope `src/cement_runtime/json_value.py`, 90 executed lines, 258 in-scope mutants).

| revision | what it holds | killed | survived | invalid |
|---|---|---|---|---|
| `593df5a` (tag `archive/m3u10-trial`) | the pin as shipped | 131 | 126 | 1 |
| `97d5d01` (tag `archive/m3u10-p74-seed`) | the pin with its `parse_json` assertion deleted | 124 | 133 | 1 |

Deleting the pin's assertion raises the survivor count on the same run (126 → 133): p74's acceptance.
`invalid` = a mutant cosmic-ray cannot build (its exception replacer raises on a parso `PythonNode`)
or one that does not compile; tallied, never run, never a kill. The first trial (`03caa6f`) counted
every mutant `error` (258/258) and a later one crashed on that replacer — both driver defects, fixed
in `cb20e55` + `593df5a`.
