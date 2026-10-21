# p98 — paste-in size: measured decision

Question: each of the four generated paste-ins embeds the whole library (`examples/open_webui/paste-in/*.py`, 369,921-379,772 B, 1,500,082 B total) because Open WebUI loads every tool and function module in isolation. Keep that, or ship one library-carrying function + thin files that bind its package?

Measurement: local Open WebUI 0.12.3 (`examples/open_webui/local.py serve`, Python 3.11.17, provisioned by REST) driven by `.agent/decisions/p98-editor.mjs` (Playwright Chromium of `prototype/webui-demo/browser.mjs`): open the edit page until CodeMirror shows the file (load), append one comment line, click Save until the `…/id/<id>/update` POST answers (save; the server re-imports the module there). Machine load 4-9 (gate runs beside it), warm SPA.

| paste-in | kind / id | bytes | runs | load ms | save ms | status |
|---|---|---|---|---|---|---|
| `cement_learning.py` (largest) | tool `cement_learning` | 379,772 | 5 | 509-641, median 573 | 549-917, median 690 | 200 ×5 |
| `cement_filter.py` | function `cement_filter` | 377,914 | 5 | 367-496, median 390 | 501-553, median 517 | 200 ×5 |
| `cement_admin.py` | function `cement_switch` | 372,475 | 3 | 485-626 | 484-1,035 | 200 ×3 |
| `cement_tools.py` | tool `cement` | 369,921 | 3 | 521-575 | 436-569 | 200 ×3 |

Decision: KEEP the self-contained paste-ins. Editing costs about one second at worst per file, while the split design adds two failure modes the current design cannot have — load order (a thin file imported before the library-carrying function) and version skew between files (each paste-in already pins `_CEMENT_DIGEST` over its own embedded sources). Reopen if a measured edit or save passes 5 s, or Open WebUI gains shared modules between tools and functions.
