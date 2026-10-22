# nucllei skill contract (MAINTAIN — Cement as a skill in LLENS)

Request (owner): get Cement working as a nucllei SKILL (not a tool) in prism-hu/llens, the Kimi
target, offline. Owner rulings at orientation → `.agent/spec.md` `Decisions` "nucllei skill
deployment". Tier `kernel` (a defect reaches hospital users unseen). Example surface: no
`src/` change; `examples/open_webui/generate.py` gains two keyword defaults that keep every
paste-in byte-identical.

## Target facts (llens master e6a1b6f, nucllei v20261020-01)

- nucllei = Open WebUI 0.6.5 fork; filter `outlet` removed (2026-10-05) ⇒ no post-reply writer.
- Skill = DB row {id, description, content}; empty description ⇒ invisible to the model, `/id`
  alone loads it (README_API §6.1); llens `nucllei/tests/test_sync_skills.py` requires a
  non-empty description for files in `nucllei/skills/`.
- Sandbox jail (nucllei-sandbox image): python 3.12 venv, SQLite 3.40.1 (bookworm), no network,
  read-only root, uid 65534 for every user, `/workspace` per user (persistent loopback ext4),
  `/ext/bin` read-only for all, `/ext/public` ro users / rw admin, `/ext/groups/<g>` rw members;
  JAIL_ENV carries no chat/message id; PATH lacks `/ext/bin`.
- llens policy: no patient data in `/ext/public` or `/ext/groups` ⇒ per-user ledger.

## Obligations

- N1 `use`: creates the ledger + registers the operation (`nucllei-chat`, default policy, switch
  off) on first use; hit ⇒ the function's output, version number, no ticket, no write; miss ⇒
  reason (`absent|off|failed|unrecognized`) + one ticket file `{operation, input, used_at_us}`;
  `--field NAME` = stdin text minus trailing newlines; ledger failure ⇒ exit class + "answer
  without Cement, record nothing"; bad operation/input ⇒ exit 2, no ticket.
- N2 `record <ticket>`: one proposal, `source_id = nucllei:<ticket>`, provenance `{ticket,
  used_at_us, request, request_truncated}` within `PROVENANCE_MAX_BYTES` (longest start); the
  ticket is consumed on success or on a duplicate source; a consumed/expired ticket ⇒ exit 3,
  no write; a bad ticket or output ⇒ exit 2, ticket kept; tickets older than 24 h pruned at
  `use`.
- N3 trigger: `record` asks for `cement-learn` before the reply iff the new proposal is no
  regeneration suspect AND the newest version does not map its input to the same output AND
  its case (default grouping, or a draft layout grouping unless the last pass ruled the
  operation not projectable) holds ≥ `min_confirmations` = active examples + non-suspect
  pending.
- N4 regeneration flag: a pending proposal is a suspect iff an earlier proposal of the same
  operation with the same input digest was created ≤ 10 min before it; `learn` lists suspects
  per case.
- N5 learning steps = the Open WebUI learning tool's semantics (`learn/show/merge/reject/revoke/
  publish`, reviewer `learning-pass`, merge = one case, repeated ids refused before any write,
  partial write reported, publish = derived projection → compile → verify → promote, refusal
  reasons `failed|empty|same`); nothing in it switches.
- N6 switch: `set_switch` reachable from `_switch` alone, actor `nucllei-user`, `pin N` over all
  receipts (version N = N-th promotion); `status/versions/read/diff` read only.
- N7 generated `ext/bin/cement` = generator output (`--check`), shebang `#!/usr/bin/env
  python3`, mode 0755 in the work tree and in git, runs under `python -I -S` (stdlib alone),
  refuses an edited embedded library.
- N8 skills: `cement`, `cement-learn`, `cement-switch` with llens front matter (title +
  description; switch description empty); every `/ext/bin/cement <sub>` they name exists;
  `switch` named by `cement-switch` alone.

## Gates (numbered; rerun from committed state)

1. `uv run python -m unittest tests.test_nucllei_example` (32 tests).
2. `uv run python examples/nucllei/generate.py --check` + `uv run python examples/open_webui/generate.py --check`.
3. Fast gate: `.agent/gate tests.test_nucllei_example tests.test_cli_removal_battery tests.test_open_webui_paste_in tests.test_open_webui_example tests.test_authority_removal tests.test_submission_battery tests.test_cli_channels tests.test_proposal_binding_battery tests.test_cli_channels_battery`.
4. Jail stand-in: `.agent/decisions/nucllei-jail-smoke.sh` in `python:3.12-slim-bookworm`
   (podman, `--network none --read-only --user 65534:65534`, tmpfs `/workspace`) → full cycle.
5. Full gate `.agent/gate`.
6. Live run on nucllei v20261020-01 + nucllei-sandbox → `.agent/decisions/nucllei-live-e2e.md`.

Red: gate 1 at `00dc010` with this battery alone → `FileNotFoundError` (no
`examples/nucllei/cement_nucllei.py`), every test unrun.
