---
paths:
  - "tests/test_read_capability_census.py"
  - ".agent/spec-lint"
  - ".agent/decisions/m3-deferred-validate.py"
  - "tests/test_migration_battery.py"
  - "tests/test_lifecycle_removal_battery.py"
---

# Gate-check firing records

Each purpose-built check below ships the seed that reds it; law → `.claude/rules/ops.md` Purpose-built gate checks. An edit to a check reruns its seeds before + after, and this record follows the after run. Seeds rerun by hand from these descriptions; their committed firing script = `.agent/deferred.md` p77.

- `tests/test_read_capability_census.py` (AST census: every `transaction(write=False)` block in `system.py` stays SELECT-only): insert `connection.execute("UPDATE operations SET revision = revision")` under the `SELECT revision FROM operations` read block → `test_every_read_transaction_block_is_select_only` = `['line 2206: UPDATE operations SET revision = revision']`, rc 1 (the locus = that block's `with` line, `src/cement_runtime/system.py:2206`, so an edit above it moves the number); `git checkout -- src/` → rc 0. Fire + revert run that module alone (`uv run python -m unittest tests.test_read_capability_census`, 0.2 s), never the full gate.
- `.agent/spec-lint`: `.agent/spec-lint <(git show b8a0703:.agent/spec.md)` → rc 1, `:116` 89 history lines; the shipped spec → rc 0. The upstream copy has no line-1 one-phrase check, so `:115` no longer fires.
- `.agent/decisions/m3-deferred-validate.py`, each seed run (counts at the agents@1622ede refresh): clean → rc 0, `COMMITTED-FLOOR: 77 over 9 revisions`; drop a born row → rc 1 `MISSING: 1 ['p62']`; the same drop COMMITTED on a throwaway branch → rc 1, `COMMITTED-FLOOR: 77 over 10 revisions` + `MISSING: 1 ['p62']` (the case a HEAD floor grades clean); `--emit-stub` over the live queue → rc 2 `REFUSING-OVERWRITE`, file byte-identical; `git` stubbed to exit 127 → rc 1 `git log over .agent/deferred.md failed; history floor ungraded`; a git stub failing the shallowness query ALONE → rc 1 `git rev-parse --is-shallow-repository failed`, `COMMITTED-FLOOR` unchanged, proving the stub selective (an inline `== "true\n"` swallowed it: `None` is not `"true\n"`, so an unanswerable question read as a proven full clone); one word of the header's floor description changed → rc 1 header drift (`--emit-stub` refuses a live queue, so it cannot resync the header); `Accept:` on an indented continuation line → rc 0; `unknown` on a continuation line → rc 1 `UNKNOWN-ROWS: 1`; `Accept:` removed → rc 1 ``has no `Accept:` clause``.
- D28 (`tests/test_migration_battery.py`): a seed costs one full suite per revision, so the shipped floor carries the anti-collapse half — `assertTrue(revisions)` + `Ran >= 949`; the census's own `>= 17/13/12` (the write floor moved 15 → 13 with the lifecycle removal).
- D28 pairing (`instrument_pruned()`, `tests/test_lifecycle_removal_battery.py` L23 ×2, L26, L29, L30), two seeds: `CEMENT_D28_INNER_REPLAY=1` in the primary tree → 5 frames `FAILED (failures=5)`, `set=True contradicts … present=True`; the instrument deleted from a checkout with the variable UNSET → the same 5, `set=False … present=False`. Announced + pruned → `OK (skipped=1)`; neither → `OK`, full strength.
- `SWAPPED_ROOTS` purge (`MigrationBatteryTests.setUpClass`): `uv run python -m unittest tests.test_hospital_ocr_example tests.test_migration_battery.MigrationBatteryTests.test_d19_...` → red before the purge (`FAILED (errors=1)`, 0.8 s), green after, each module still green alone.
