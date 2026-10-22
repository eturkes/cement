---
paths:
  - "examples/nucllei/**"
  - "tests/test_nucllei_example.py"
  - ".agent/decisions/nucllei-*"
  - "src/cement_runtime/**"
---

# nucllei skill example law (LLENS, skill-only)

Rulings = `.agent/spec.md` `Decisions` "nucllei skill deployment"; contract (obligations N1-N8, numbered gates) = `.agent/decisions/nucllei-contract.md`; live record = `.agent/decisions/nucllei-live-e2e.md`.

- Generated file: a change to `src/cement_runtime/**` or `examples/nucllei/cement_nucllei.py` → `uv run python examples/nucllei/generate.py` (and `examples/open_webui/generate.py` for the paste-ins); never hand-edit `ext/bin/cement` — N7 reds a stale file and a mode other than 0755 in the work tree or git (`100755`). The embedding is the Open WebUI generator's `render(…, generator=, refresh=)`; its keyword defaults keep every paste-in byte-identical.
- Jail facts the command rests on (nucllei-sandbox v20261020-01): Python 3.12, SQLite 3.40.1 (bookworm; Cement needs ≥ 3.37), no network, read-only root, uid 65534 for every user, per-user `/workspace`, `JAIL_ENV` without chat/message id, `PATH` without `/ext/bin` ⇒ skills spell `/ext/bin/cement` in full. A nucllei image bump re-runs `.agent/decisions/nucllei-jail-smoke.sh` (stand-in, rc 0 = PASS; positive control = alter one expectation → rc 1) and the live regimen.
- Model-facing text = Japanese, llens style: a refusal = `中止: <fact>`, last line `次の手: <next step>`; ASCII `( ) :` inside Japanese strings (ruff RUF001 flags full-width confusables).
- Writers: proposals ← `record` alone (consumes its ticket); reviews, supersessions, revocations, projection, promotion ← the learning commands (reviewer `learning-pass`); registration ← `use` (`nucllei-chat`); `set_switch` ← `_switch` alone (actor `nucllei-user`; N6 AST pin).
- Skills: `switch` is named by `cement-switch.md` alone (N8); its description stays EMPTY (model-invisible) ⇒ it installs through the nucllei admin UI, never `nucllei/skills/` (llens `test_every_skill_builds`). A command a skill names must exist in `_parser()` (N8).
- README census: `examples/nucllei/README.md` sits in the tripwire `DOCS` + D23 `added_surfaces`; a prose edit reruns `uv run python .agent/decisions/m3u6a2-tripwires.py` (`--emit` on DRIFT), `.agent/article-audit`, `.agent/register-audit`. Avoid `handle`, `*_FROM_*` placeholders and a bare `cement <sub>` token in shell blocks (D23 parses those under the core CLI; `/ext/bin/cement` is a different token).
- Untrusted documents never pass through the shell: the chat skill writes each one with `write_file` to `/workspace/.cement/in/` and runs `use --field document --input-file <path>` (a heredoc ends early at a document line equal to its delimiter and runs the rest as commands); `use` deletes a hand-over file inside `$CEMENT_HOME/in/`. Input + output parse through `cement_runtime.json_value.parse_json` (strict: repeated keys, depth). Filesystem failures after a durable write (`_discard`, `_remember`) return a line; `main` maps any other `OSError` to exit 5.
- `_inputs`, `_cases`, `_merge`, `_publish` copy `examples/open_webui/cement_learning.py` semantics; change both together until p118 moves them into the library.
