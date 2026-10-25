# p136-owui contract — shadow sampling in the Open WebUI example (revision 1)

Plan: `.agent/decisions/p88-milestone.md` S1 + S5, amended by the owner's T rulings (`.agent/spec.md`
`Decisions` Shadow sampling): T5 = EVERY hit of every listed operation, an admin valve excludes
operations; T6 = the filter outlet enqueues and returns, a bounded background worker asks the model;
T7 = observation id = chat message + tool-call id; T8 = a fixed admin-chosen model + a versioned
prompt from the operation's description + the input alone, never the function's answer, the chat or
Cement's tools; reads in the learning tool + its skill. Tier `kernel` for hit selection, identity and
response isolation (the chat must never change or wait); `data` for the model's answer (Cement's
`record_shadow` re-validates it). Store semantics = `.agent/decisions/p136-store-contract.md`.

## Premises (measured at the p136-learn commit, Open WebUI 0.12.3 from `.open-webui/venv`)

- W1 A hit = a `use_learned_function` call whose result is `{"covered": true, "output", "function_hash",
  …}` (`cement_tools.py` `_resolve`); `cement_filter.py` `_tool_calls` maps the current message's
  `function_call` items to their `function_call_output` results by `call_id`.
- W2 The outlet receives `__request__`, `__user__` (a dict), `__metadata__`, `__event_emitter__`
  (`utils/middleware.py` `outlet_filter_handler`), and `/api/chat/completed` can run it again for one
  message. The Filter instance persists across requests in one process.
- W3 `open_webui.utils.chat.generate_chat_completion(request, form_data, user, bypass_filter=True)` calls
  the model router directly; it merges `request.state.metadata` into the form (live-verified that no
  tool or filter reaches the shadow call).

## Obligations

- O1 Hit extraction (`cement_filter.py` `_hits`): every current-message `use_learned_function` call
  with valid arguments (a listed, not excluded operation; canonical input) whose result says
  `covered: true` with a 64-hex `function_hash` → one descriptor `(observation_id =
  "<deployment_id>:<chat_id>:<assistant message id>:<call_id>", operation, input, function_hash,
  observed_at_us)`; a message without its own id yields none (as `_pairs`).
- O2 Isolation: the outlet returns `body` unchanged (the same object), awaits no model and no Cement
  write for sampling, and never raises because of sampling; descriptors go to a bounded
  `asyncio.Queue` (`shadow_queue` valve, default 64); a full queue → `drop` (reason `queue full`) in a
  thread the outlet does not await.
- O3 Worker (one per Filter instance, started lazily on the running loop): per descriptor `admit`
  (a duplicate → done), then the shadow call with `shadow_timeout` (default 60 s), then
  `record_shadow`, or `fail` on an error, a timeout, or an answer that is no JSON value. Its own
  failures are logged and counted, never raised into a chat. The shadow call reaches neither Cement's
  tools nor this filter (`bypass_filter=True`, no `tools`, no `tool_ids`, the fixed `shadow_model`).
- O4 Prompt (`_shadow_prompt(operation, description, input)` → messages + `prompt_revision` =
  `sha256:` + the first 16 hex of SHA-256 over the template + the description): a system message
  stating the task and "return only the JSON output", a user message with the operation, its
  description and the canonical input. Never the function's answer, the chat or the reply.
- O5 Valves: `shadow_model` (empty = sampling off), `shadow_exclude` (operations, comma or line
  separated), `shadow_queue`, `shadow_timeout`, `shadow_path` (empty = the ledger path + `.shadow`).
- O6 Learning tool (`cement_learning.py`) + its skill: `set_comparator`, `show_comparator`, `drift`,
  `observations` (the shadow file beside the ledger); the AST pin (no model-callable path reaches
  `set_switch`) still holds; the skill names each function (W3).
- O7 Paste-ins regenerated; README (example): the valves, every-hit sampling, the queue + drop, the
  observation id + replay rule, the learning tool's reads.

## Gates (numbered; rerun from committed state)

1. New tests red at the p136-learn commit, with Open WebUI stubbed as `tests/test_open_webui_example.py`
   does (S5 = the frozen-completion probe): one frozen outlet body replayed with sampling off and on →
   the returned body is the same object and serializes byte-identically; N distinct hits with mixed
   agreement + all-agree + all-disagree controls → model calls = N, rows = N, `drift` = N − k
   disagreements on that hash, 0 elsewhere; sampling off (no `shadow_model`) and an excluded operation →
   no call, no write; the same body twice (`/api/chat/completed`) → one observation + one duplicate; a
   blocked shadow call → the outlet returns first; a failed / non-JSON / timed-out call → `failed`, no
   proposal; a version change between hit and record → the captured hash decides; a full queue →
   `dropped`. The prompt holds no function answer (the captured output's values absent from it).
2. Full gate = CI gate (`.agent/ci-gate p136-owui`).
3. Live regimen: `examples/open_webui/local.py` with `gpt-6-luna` — a hit in chat produces one admitted
   then recorded observation; the shadow call shows no tool use; record in
   `.agent/decisions/owui-live-e2e.md`. Register + article audits rc 0.
