# Memory

- Product boundary: local control plane/runtime; pure JSON in/out; caller owns authorization + effects.
- Generic compiler emits exact lookup artifacts only. Wider scopes require a future domain verifier; recurrence alone never justifies generalization.
- Evidence isolation key = explicit partition + operation revision + canonical input.
- Runtime dependencies = Python standard library only; SQLite must support STRICT tables.
- Promotion receipts bind sealed evidence + verification test sets; retired/suspended artifacts are terminal.
- Queue/history cursors use SQLite insertion/transition sequences, independent of caller clocks.
- Agent working headroom is far below the nominal 272K: an all-tools implementation Agent (full MCP tool schemas + CLAUDE.md, cached every turn) is baseline-dominated — M1.2 (one ~160-line file) still finished at impl=73% (199K/272K). SIZE-CHECK against real working headroom, not 272K; split larger units aggressively or dispatch Agents with a narrower toolset.
