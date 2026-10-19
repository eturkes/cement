# M5.3 Open WebUI smoke (contract §7)

Open WebUI 0.12.3 in an isolated Python 3.12 venv + this repo installed editable; stub model =
`.agent/decisions/m5u3-stub-model.py` (deterministic, native tool calls, OpenAI-compatible);
driver = `.agent/decisions/m5u3-smoke.py <examples/open_webui>`. Server env: fresh `DATA_DIR`,
`WEBUI_AUTH=False`, `OFFLINE_MODE=True`, `BYPASS_EMBEDDING_AND_RETRIEVAL=True`,
`ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS=false`, `OPENAI_API_BASE_URL` = the stub; port 18765.

| case | function calls in the saved assistant message | proposals written | expected |
|---|---|---|---|
| hit | use_learned_function | 0 | 0 |
| miss_record | use_learned_function, record_answer | 1 | 1 |
| duplicate_delivery | — (`/api/chat/completed` re-delivery) | 0 | 0 |
| regeneration | use_learned_function, record_answer | 0 | 0 |
| two_calls | use_learned_function, use_learned_function, record_answer, record_answer | 2 | 2 |
| off | use_learned_function, record_answer | 1 | 1 |

Source id shape (miss_record): `<deployment>:<chat id>:<user message id>:<input sha256>` —
first run derived the user message id from `__metadata__`, which `/api/chat/completed` omits, so the
re-delivery wrote a second proposal; the filter now reads it from the body's preceding user message.
Provenance keys: assistant_message_id, chat_id, model, record_call_id, reply, reply_truncated, use_call_id, user_message_id.
