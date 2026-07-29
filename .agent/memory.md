# Memory

- Compiler emits exact-lookup artifacts only; scope = partition + operation revision + canonical input. Wider scopes require a future domain verifier — recurrence alone never justifies generalization.
- Sole configured gate = `uv run python -m unittest discover -s tests -t .`; ruff/mypy stay unconfigured. Example self-checks run only when invoked by hand, so behavior worth protecting belongs in `tests/` (pattern: `tests/test_hospital_ocr_example.py` puts the example dir on `sys.path`, then imports the modules).
- `System.events()` dicts key the event name under `kind`; there is no `type` field.
- `examples/hospital_ocr/run_demo.py` prints exactly ONE per-run random `art_<32hex>`; every other line is deterministic → mask `art_[0-9a-f]{32}` before diffing its output.
- Implementing-agent headroom is baseline-dominated (tool schemas + CLAUDE.md re-cache every turn), so even a one-file unit can approach the ~200K aim. Size units against measured baseline-inclusive usage; split aggressively.
- Serena `language_servers:` here = python, markdown, toml, yaml (python first = default/fallback). Markdown gate = pull-based `get_diagnostics_for_file` → Marksman (project mode via `.git`): flags links to non-existent or non-`.md` targets, silent when clean → inject a broken link as a positive control to prove liveness.
