# Open WebUI example

This example connects Cement to [Open WebUI](https://github.com/open-webui/open-webui) 0.12.3.
The chat model calls Cement as a tool. A filter retains each answer that the model gave for a
request that no learned function covered. The learning pass (`skills/cement-learn/`) then turns
recurring answers into a function, and a person switches the function on.

The example has two parts:

- `cement_tools.py` is an Open WebUI tool with two functions. `use_learned_function` answers a
  request from the operation's switched-on function. `record_answer` lets the model state the
  structured output that it used when no function covered the request. Neither function writes
  to the ledger.
- `cement_filter.py` is an Open WebUI filter. After a response completes, it pairs each
  uncovered `use_learned_function` call with the `record_answer` call for the same operation and
  input. It retains each pair as one pending proposal. It is the only part that writes.

## What the example guarantees

When a switched-on function covers a request, the tool result is the function's output. The
result does not depend on the model. The chat model still writes the reply around that result.
The example does not make the reply text deterministic.

A request that no function covers goes to the model, as before. The model's answer reaches the
user in the same turn. The learning pass decides later what Cement learns from it.

Each retained answer carries a source id: the deployment id, the chat id, the user message id
and the digest of the input. Cement refuses a second proposal with the same source id. A
repeated delivery or a regenerated reply to the same user message therefore adds no second
proposal. The filter retains nothing from a chat or a message that has no id.

Each retained answer also carries the final reply text as provenance. The filter keeps the whole
reply when it fits Cement's 64 KiB provenance bound. Otherwise it keeps the longest start of the
reply that fits, and it marks the reply as truncated.

A retained answer is untrusted evidence. The filter reads the chat that Open WebUI gives to it,
and a signed-in user can send a chat again through `/api/chat/completed` with tool calls that the
model never made. Three gates stand between a retained answer and production: the learning pass
reviews every answer, a case needs two confirmations, and a person switches each function on.

## Install

Open WebUI supports Python 3.11 and 3.12. Install Cement into the same environment as Open
WebUI, because Open WebUI runs tools and filters inside its own process:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv 'open-webui==0.12.3' /path/to/cement
```

Create the ledger and register each operation before the first chat. The tool and the filter
open an existing ledger only, so a wrong path creates no file:

```sh
cement --db /srv/cement/ledger.db --partition ward-7 operation register extraction_plan
```

## Configure

1. In Open WebUI, open **Workspace > Tools** and create a tool from `cement_tools.py`.
2. Open the tool's valves. Set `ledger_path`, `partition` and `operations` (a comma-separated
   list of the operations that the model can use).
3. Open **Admin Panel > Functions** and create a function from `cement_filter.py`.
4. Open the filter's valves. Set `ledger_path`, `partition`, `operations` and `deployment_id`.
5. Turn the filter on, and turn it on for the models that use the tool (or globally).
6. Attach the tool to the model, and use native function calling for that model.

## Run the learning pass

Run the skill in `skills/cement-learn/` when you want Cement to learn from the retained
answers. The skill reviews the answers, merges the scripts of each recurring case and publishes
a new function version. It never switches a function on.

## Switch a function on

Read the new version, then switch it on:

```sh
cement --db /srv/cement/ledger.db --partition ward-7 function versions extraction_plan
cement --db /srv/cement/ledger.db --partition ward-7 function switch extraction_plan --mode follow --actor ward-lead
```

Use `--mode pinned --function-hash <hash>` to keep one version, or `--mode off` to stop
answering from the function.

## Test

The example tests run without Open WebUI:

```sh
uv run python -m unittest tests.test_open_webui_example
```
