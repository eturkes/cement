# nucllei example

This example connects Cement to nucllei, the chat platform of the LLENS deployment. nucllei is a
fork of Open WebUI 0.6.5. Here Cement runs as a skill. The chat model loads a skill, and then it
runs one command in the sandbox of nucllei with `run_shell`. No Cement code runs inside nucllei.
The sandbox has no network access. The command therefore contains the whole Cement library, and
it needs only the Python standard library.

## The parts

| File | nucllei item | Who uses it |
|---|---|---|
| `ext/bin/cement` | The sandbox command `/ext/bin/cement` | The chat model, through `run_shell` |
| `skills/cement.md` | The skill `cement` | The chat model, for each request of a Cement operation |
| `skills/cement-learn.md` | The skill `cement-learn` | The chat model, when the command asks for a learning pass |
| `skills/cement-switch.md` | The skill `cement-switch` | The user, who sends `/cement-switch` |

The repository generates `ext/bin/cement` from `cement_nucllei.py` with `generate.py`. Do not
edit `ext/bin/cement`. The file checks its embedded library against a digest each time that
it runs, and it refuses to run after an accidental edit. The digest is not a signature.

The skills are in Japanese, as all LLENS skills are. The command writes Japanese lines for the
model. A refusal starts with `中止:`, and the last line after `次の手:` names the next step.

## How it works

Each user has a ledger of their own in `/workspace/.cement/`. LLENS keeps patient data only in
the workspace of each user, and the ledger holds the documents that the user pastes. Cement
therefore learns from the requests of one user, and each user switches their own functions on.

A chat turn goes like this:

1. The user pastes a form and asks which fields to extract. The model loads the `cement` skill.
2. The model writes the form to a file in `/workspace/.cement/in/` and runs `use` with that file.
   No line of the form goes into a shell command. When a switched-on function covers the form,
   the command prints the output of the function. The model uses that output in its reply.
3. When no function covers the form, the command prints a ticket. The model writes its own
   answer. Before it replies, it runs `record` with that ticket and its output.
4. When the ledger holds two answers for the same case, `record` asks for a learning pass. The
   model loads `cement-learn` and runs the pass before it replies. The user waits for the pass.
   The pass reviews each answer as `learning-pass` and publishes a new version. It never
   switches a function on.
5. The user sends `/cement-switch` to see each function and to switch it on or off.

## What the example guarantees

When a switched-on function covers a request, the output that the model receives is the output
of the function. That output does not depend on the model. The model still writes the reply
around that output, so the reply text is not deterministic.

A request that no function covers goes to the model, as before. Cement learns only from the
answers that the model recorded. A case needs two confirmations before a version holds it. The
switch of a new operation starts off. A version answers only while the switch selects it: with
`follow`, each new version answers at once, and with `pin`, one version answers.

## Limits

- The sandbox gives the command no chat ID or message ID. A regenerated reply therefore looks
  up the same input again. `record` accepts one record for each ticket. The learning work list
  marks an answer as a suspected regeneration when the same input came in 10 minutes or less
  earlier. The `cement-learn` skill rejects that answer, and the check that asks for a learning
  pass ignores it.
- The model runs the switch command when the user asks for it. The `cement-switch` skill has an
  empty description, so nucllei never lists it to the model, and only a message from the user
  loads it. The command itself cannot tell who asked. The `cement` skill tells the model never
  to switch. A switch can select only a version that the learning pass published and that
  Cement verifies.
- A recorded answer is untrusted evidence. Three gates stand between a recorded answer and
  production: the learning pass reviews every answer, a case needs two confirmations, and the
  user switches each function on.
- The sandbox deletes a workspace after a period without use (365 days in the LLENS
  configuration). The ledger goes with the workspace.

## Install into LLENS

Use the files from one commit together.

1. Copy `ext/bin/cement` to `ext/bin/cement` in the LLENS repository. Keep its mode `755`. The
   sandbox shows `ext/bin/` to every user as `/ext/bin`, read-only. You do not need to create a
   container again.
2. Copy `skills/cement.md` and `skills/cement-learn.md` to `nucllei/skills/`. Then run
   `make nuc-sync`.
3. Open **Workspace**, then **Skills**, and create the skill `cement-switch`. Leave its
   description empty. For its content, use `skills/cement-switch.md` without its front matter.
   Do not put this file in `nucllei/skills/`: the LLENS skill test refuses a skill with an empty
   description.
4. For each model preset that users chat with, add `cement`, `cement-learn` and `cement-switch`
   to the skills of the preset. The preset must also have the sandbox tool `builtin_sandbox`.
5. Give the users read access to the three skills.

You do not change a system prompt. The `cement` skill carries every model-facing instruction for
the chat, and its description tells the model when to load it.

## Add an operation

Section `操作` of `skills/cement.md` lists the operations. For a new operation, write its
name, the requests that it covers and the exact shape of its input and output. Then add those
requests to the description of the skill, so that the model loads the skill for them. Cement
compares inputs exactly. A form layout can join documents with different values only when the
input holds one text field.

## Use it

1. Paste a progress note and ask which fields to extract. The model answers and records the
   answer.
2. Paste a second progress note with the same layout. The model records the answer, runs a
   learning pass and replies. The reply ends with a line about the new version.
3. Send `/cement-switch extraction_plan をオンにして`. The model shows the state and switches the
   function on.
4. Paste a third progress note. The function answers it.

## Test it without nucllei

Run the tests of this example:

```sh
uv run python -m unittest tests.test_nucllei_example
```

After a change to `cement_nucllei.py` or to `src/cement_runtime`, generate the command again:

```sh
uv run python examples/nucllei/generate.py
```

To run the command in a container that resembles the sandbox jail, use Podman. The container has
no network, a read-only root and a temporary workspace:

```sh
podman run --rm -i --network none --read-only --user 65534:65534 --tmpfs /workspace:rw,mode=1777 --tmpfs /tmp:rw,mode=1777 -e HOME=/workspace -v "$PWD/examples/nucllei/ext/bin:/ext/bin:ro" docker.io/library/python:3.12-slim-bookworm /ext/bin/cement status
```

## Command reference

| Command | What it does | Used by |
|---|---|---|
| `use <operation> [--field <name>] [--input-file <path>]` | Looks up one input. Prints the output of the function, or a ticket. | `cement` |
| `record <ticket> [--request <text>]` | Retains the output for the input of the ticket. | `cement` |
| `learn <operation> --projectable yes\|no` | Lists the cases, their answers and suspected regenerations. | `cement-learn` |
| `show <proposal>` | Shows one recorded answer. | `cement-learn` |
| `merge <operation> --projectable yes\|no ...` | Confirms a merged output for one case. | `cement-learn` |
| `reject <proposal> --note <text>` | Rejects one recorded answer. | `cement-learn` |
| `revoke <example> --reason <text>` | Withdraws one wrong confirmed answer. | `cement-learn` |
| `publish <operation> --projectable yes\|no` | Compiles, verifies and promotes a new version. | `cement-learn` |
| `versions <operation>` | Lists the versions and the switch. | All |
| `read <operation> [<version>]` | Shows the cases of one version. | `cement-learn`, `cement-switch` |
| `diff <operation> <old> <new>` | Counts the cases that a later version adds, removes or changes. | `cement-learn`, `cement-switch` |
| `status` | Shows the versions and the switch of each operation. | `cement-switch` |
| `switch <operation> off\|follow\|pin [<version>]` | Switches a function off, on, or to one version. | `cement-switch` |

Each input and output on standard input is JSON. With `--field <name>`, `use` reads the whole
standard input as the text of that one field and removes line breaks at its end. With
`--input-file <path>`, `use` reads that file instead of standard input. When the file is in
`/workspace/.cement/in/`, `use` deletes it after it reads it.
