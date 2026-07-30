# Memory

- Compiler emits exact-lookup artifacts only; scope = partition + operation revision + canonical input. Wider scopes require a future domain verifier — recurrence alone never justifies generalization.
- Sole configured gate = `uv run python -m unittest discover -s tests -t .`; ruff/mypy stay unconfigured. Example self-checks run only when invoked by hand, so behavior worth protecting belongs in `tests/` (pattern: `tests/test_hospital_ocr_example.py` puts the example dir on `sys.path`, then imports the modules).
- `System.events()` dicts key the event name under `kind`; there is no `type` field.
- `examples/hospital_ocr/run_demo.py` prints exactly ONE per-run random `art_<32hex>`; every other line is deterministic → mask `art_[0-9a-f]{32}` before diffing its output.
- Implementing-teammate headroom = 27-33% (66-78K/240K) across M1's four units, on a ~27K baseline (tool schemas + CLAUDE.md re-cache every turn) → units that size leave ~3x room, and the ~200K aim binds MAIN instead (76-96% peaks in M1 sessions). `impl=` always comes from the teammate's own transcript: `.agent/context.sh <teammate>` = high-water turn, since `TaskStop`ped/dead teammates trail stripped zero-usage turns that a final-turn read reports as 0%.
- Serena `language_servers:` here = python, markdown, toml, yaml (python first = default/fallback). Markdown gate = pull-based `get_diagnostics_for_file` → Marksman (project mode via `.git`): flags links to non-existent or non-`.md` targets, silent when clean → inject a broken link as a positive control to prove liveness.
