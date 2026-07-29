# Memory

- Product boundary: local control plane/runtime; pure JSON in/out; caller owns authorization + effects.
- Generic compiler emits exact lookup artifacts only. Wider scopes require a future domain verifier; recurrence alone falls short of justifying generalization.
- Evidence isolation key = explicit partition + operation revision + canonical input.
- Runtime dependencies = Python standard library only; SQLite must support STRICT tables.
- Promotion receipts bind sealed evidence + verification test sets; retired/suspended artifacts are terminal.
- Queue/history cursors use SQLite insertion/transition sequences, independent of caller clocks.
- Implementing-agent headroom is baseline-dominated: full MCP tool schemas + CLAUDE.md re-cache every turn, so even a tiny unit lands near the one-window aim — M1.2 (one ~160-line file) finished at impl=83% (199K/240K), consuming essentially the whole ~200K aim. Size units against measured baseline-inclusive usage; split aggressively or dispatch agents with a narrower toolset.
- Hospital OCR demo (`examples/hospital_ocr/run_demo.py`) prints exactly ONE per-run random 32-hex artifact id (`art_<32hex>`, on the promote line); every other output line is deterministic. Compare/diff its output after masking `art_[0-9a-f]{32}`.
- Serena `language_servers:` here = python, markdown, toml, yaml (python first = default/fallback LS). Markdown gate = pull-based `get_diagnostics_for_file` on the `.md` → Marksman (project-mode via `.git` present): flags links to non-existent OR non-`.md` targets, silent when clean → inject a broken link as a positive control to prove liveness.
