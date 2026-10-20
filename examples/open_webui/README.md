# Open WebUI example

This example connects Cement to [Open WebUI](https://github.com/open-webui/open-webui) 0.12.3.
The chat model calls Cement as a tool. A filter retains each answer that the model gave for a
request that no learned function covered. A learning pass runs inside Open WebUI and turns
recurring answers into a function. An administrator then switches the function on with a button.

Everything installs by paste. Each file in `paste-in/` contains the whole Cement library, so the
Open WebUI image needs no package installation and no rebuild. The files need only the Python
standard library and the `pydantic` package that Open WebUI already contains.

## The parts

| File | Open WebUI item | ID | Who uses it |
|---|---|---|---|
| `paste-in/cement_tools.py` | Tool | `cement` | The users' chat model |
| `paste-in/cement_filter.py` | Function (filter) | `cement_filter` | The users' chat model |
| `paste-in/cement_learning.py` | Tool | `cement_learning` | The administrator's learning model |
| `paste-in/cement_admin.py` | Function (action) | `cement_switch` | The administrator's learning model |
| `cement-learn/SKILL.md` | Skill | `cement-learn` | The administrator's learning model |

- The `cement` tool has two functions. `use_learned_function` answers a request from the
  operation's switched-on function. `record_answer` lets the model state the structured output
  that it used when no function covered the request. Neither function writes to the ledger.
- The `cement_filter` filter does two things. Before the model answers, it adds a note to the
  last user message. The note names each enabled operation and its exact input. After a response
  completes, it pairs each uncovered `use_learned_function` call with the `record_answer` call for
  the same operation and input. It retains each pair as one pending proposal. It is the only part
  that writes a proposal.
- The `cement_learning` tool runs the steps of the learning pass. The model reads the retained
  answers, decides whether the operation is projectable, and writes one merged output for each
  case. The tool then reviews the answers as `learning-pass`, derives the projection program from
  the documents, and publishes a new function version. It refuses every user who is not an
  administrator. It cannot switch a function on.
- The `cement_switch` action is a button under each reply of the learning model. It sets up an
  operation, and it switches a function off, on, or to one version. The administrator chooses the
  change in a list and confirms it. No model takes part in this step.
- The `cement-learn` skill tells the learning model how to run the learning pass with the
  `cement_learning` tool.

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
reviews every answer, a case needs two confirmations, and an administrator switches each function
on.

## Install on an existing instance

Use the files from one commit together. Do not edit them. The repository generates them. Each
file checks its embedded library against a digest when Open WebUI loads it, and it refuses to load
after an accidental edit. The digest is not a signature: a person who can edit the file can also
change the digest. Paste only files that you took from the repository.

1. Open **Workspace**, then **Tools**. Create a tool with the ID `cement` from
   `paste-in/cement_tools.py`. Create a second tool with the ID `cement_learning` from
   `paste-in/cement_learning.py`.
2. Open **Admin Panel**, then **Functions**. Create a function with the ID `cement_filter` from
   `paste-in/cement_filter.py`. Create a function with the ID `cement_switch` from
   `paste-in/cement_admin.py`. Turn on both functions. Do not make them global.
3. Open **Workspace**, then **Skills**. Create a skill with the ID `cement-learn` from
   `cement-learn/SKILL.md`.
4. Set the valves of all four items to the same values (see [Valves](#valves)).
5. Open **Workspace**, then **Models**. Create the users' chat model on top of your model. Attach
   the `cement` tool and the `cement_filter` filter, and set function calling to native. Give your
   users read access to this model and to the `cement` tool. Without read access to the tool,
   Open WebUI drops the tool from their chats.
6. Create the administrator's learning model on top of the same model. Attach the
   `cement_learning` tool, the `cement-learn` skill and the `cement_switch` action, and set
   function calling to native. Under **Builtin Tools**, turn off **Skills**. Open WebUI then puts
   the whole skill text into each chat with this model. With **Skills** on, it only lists the skill,
   and the model can skip it. Keep this model, the `cement_learning` tool and the skill private to
   administrators.
7. Open a chat with the learning model and send any message. Under the reply, click the
   `cement_switch` button. Choose `Set up <operation>` for each operation. The button creates the
   ledger file. The switch of a new operation is off.

You do not change the system prompt of a model. The filter note carries every model-facing
instruction about the operations.

## Valves

All four items have the same three valves:

- `ledger_path`: the ledger file. Put it in the Open WebUI data volume, for example
  `/app/backend/data/cement/ledger.db`, so that it survives a container restart.
- `partition`: the Cement partition of this instance, for example `ward_7`.
- `operations`: one operation on each line, written as `name: description`. The description
  tells the chat model which requests the operation covers and the exact input object. Write the
  input with one fixed shape, because Cement compares inputs exactly. For example:

  ```text
  extraction_plan: The user pastes one form and asks which fields to extract. input = {"document": "<the whole form text, exactly as pasted>"}. output = the extraction plan, never the patient's values: {"fields": [{"name": "<name>", "label": "<the text before the colon>"}]}.
  ```

The filter also has `deployment_id`, which names this instance in each source id.

## Run the learning pass

Open a chat with the learning model and send, for example, `Run a Cement learning pass for
extraction_plan.` The model loads the `cement-learn` skill and calls the `cement_learning` tool.
At the end, it reports the new version and what changed. It never switches a function on.

To run the pass on a schedule, create an Open WebUI automation with the learning model and the
same message.

## Switch a function on

Under a reply of the learning model, click the `cement_switch` button. The list shows the state
of each operation and the changes that you can make:

- `Switch <operation> on: follow the newest version` serves each new version as the learning pass
  publishes it.
- `Pin <operation> to version N` serves one version, and a later version does not change it. To
  roll back, pin an earlier version.
- `Switch <operation> off` sends every request of that kind to the model again.

Choose a change and confirm it. The ledger records your Open WebUI user id as the actor.

## Try it locally

`local.py` starts Open WebUI 0.12.3 on Python 3.11, the Python of the official image. It installs
no Cement package beside Open WebUI, and it pastes in every part through the Open WebUI API. Use
any OpenAI-compatible endpoint for the model. The instance has no login and listens on
`127.0.0.1` only. Use it for tests on your own computer, not as a shared server.

1. Install Open WebUI into `.open-webui/` once:

   ```sh
   uv run python examples/open_webui/local.py setup
   ```

2. Start the instance. Put the key of your model endpoint in `OPENAI_API_KEY`:

   ```sh
   OPENAI_API_KEY=<key> uv run python examples/open_webui/local.py serve \
     --base-url <endpoint>/v1 --model <model id>
   ```

   The command prints the address and the steps of the walkthrough. It creates the users' chat
   model `Cement chat` and the learning model `Cement learning`. Add `--fresh` to start again
   with an empty instance and ledger. Press `Ctrl-C` to stop.

3. Follow the printed steps. Set up `extraction_plan` with the button. Paste two forms of one
   layout from `examples/hospital_ocr/documents/` into new chats with `Cement chat`, and ask which
   fields to extract. Run the learning pass. Switch the function on. Then paste a third form of
   the same layout. Open the `use_learned_function` tool call in the reply: its result says
   `"covered": true`, and the model answers from the learned plan.

The ledger is in `.open-webui/data/cement/ledger.db`. Read it with the Cement CLI, for example:

```sh
uv run cement --db .open-webui/data/cement/ledger.db --partition local learn cases extraction_plan
```

## Regenerate the paste-in files

Change the sources in this directory or in `src/cement_runtime/`. Then regenerate:

```sh
uv run python examples/open_webui/generate.py
```

The test suite fails when a paste-in file differs from the generator output.

## Test

The example tests run without Open WebUI:

```sh
uv run python -m unittest tests.test_open_webui_example tests.test_open_webui_paste_in tests.test_open_webui_local
```
