---
name: cement-learn
description: Run one Cement learning pass for one operation inside Open WebUI. Use this skill only when the administrator asks for a learning pass. The pass reads the chat answers that Cement retained, merges the answers of each recurring case into one output, reviews them as the learning pass, and publishes a new function version with the Cement learning tool. It never switches a function on or off.
---

# Cement learning pass (Open WebUI)

Cement turns repeated chat work into deterministic functions. When the chat model answers a
request that no learned function covers, Cement retains the answer as a pending proposal. This
skill is the learning pass: it reads those proposals, decides the answer for each case, and
publishes a new version of the operation's function with the tools of the Cement learning tool.
A person then decides whether to switch the function on.

Run this skill only when the administrator asks for it. The administrator names the operation.
Every tool returns JSON. A result with an `error` key is a refusal that wrote nothing; read its
`message`. After `conflict`, call `learn_cases` again and continue from what it shows. After
`integrity`, stop and report: the ledger needs the operator.

## Words

- A **proposal** is one retained answer: the operation, the exact input, the output that the chat
  model used, and its provenance (the chat model's full reply). A new proposal is pending.
- A review turns a proposal into a confirmed **example** (`accept` or `correct`) or closes it
  (`reject`). Only examples count toward a case.
- A **case** is one key. Without a projection program the key is the exact input. With a program
  the key is the layout of the input, so documents with different values and one layout share a
  case.
- A **version** is one published set of verified cases. It answers nothing until a person switches
  it on.

## Steps

1. Call `learn_cases` with the operation. If `nothing_to_learn` is `true`, report "nothing to
   learn" and stop. `cases` lists each key with its pending proposal ids, its active example ids,
   its distinct outputs and its support. `work` lists unfinished steps of an earlier pass.
   `unsourced_pending` lists proposals without a source id; check them for duplicates of one
   chat message. Reject each id in `stale_pending_proposal_ids`.

2. Read each pending proposal with `show_proposal`. Its `provenance.reply` is the chat model's
   full reply: the script or plan that the answer used. Merge from it.

3. Decide whether the operation is projectable. It is projectable only when every output is a
   procedure over the input (a plan that reads values from the input) and no output contains a
   value copied from an input. Answers that interpret values are never projectable. If it is
   projectable and no program is stored yet (`grouped_by` is `exact`), write a projection program
   (format below) from the layouts of the raw inputs. Then call `learn_cases` again with
   `program` set to it, and keep using that grouping until step 5.

4. For each case, merge the outputs into one output that covers what every request needed. Keep
   the union of the rows. Keep a difference when a request asked for it. Put no input value into
   a projectable output. Then review each pending proposal of the case with `review_proposal`:
   `accept` when it equals the merge, `correct` with the merge as `output` when it differs,
   `reject` when it is not an answer for this operation. Give a short `note` that says what the
   merge kept.

   Then compare the case's earlier active examples with the merge. If the merge extends an
   example, call `supersede_examples` with those example ids and the merge. If the merge
   contradicts an example, call `revoke_example` with the reason. A case with two different
   active outputs builds nothing until you finish this step.

5. If you wrote a program, call `test_projection`, then `set_projection` with the same program.
   `set_projection` refuses a layout that no confirmed example shows, so it comes after the
   reviews.

6. Call `publish_version`. It compiles the confirmed cases, verifies them and promotes the
   verified set as a new version. A case seen once stays with the chat model: the operation needs
   two confirmations of a case. If `published` is `false`, report its `reason`.

7. Call `function_versions`, and `diff_versions` from the previous version to the new one when
   one exists. Report to the administrator:
   - the new function hash and what changed (on a first version, every case is new);
   - for each case: what the merge added or changed, and the examples you superseded or revoked;
   - for a projectable operation: the layouts that the program recognizes, and its assumption that
     documents with one layout need one procedure;
   - every refusal, with its message.

   End with: "The new version is ready. Read it, then use the Cement switch button to switch it
   on." Never claim that the function is on.

## Projection program

A program maps a raw input to its case key. Cement checks it against every confirmed input.

```json
{"abi": "cement-projection-v1",
 "text": "document",
 "keep": [],
 "layouts": [
   {"name": "progress note",
    "title": "PHYSICIAN PROGRESS NOTE",
    "entries": [{"label": "Patient"}, {"label": "MRN"}, {"label": "Date"},
                {"section": "Assessment"}, {"section": "Plan"}]}]}
```

- `text` names the input field that holds the document text. The input object must hold exactly
  that field plus the fields that `keep` lists.
- `title` is the document's first line. `entries` is the ordered structure: `{"label": "K"}` for
  a line `K: value`, `{"section": "H"}` for a heading line `H:` followed by body lines.
- Cement removes trailing spaces, removes leading and trailing blank lines, and joins runs of
  blank lines before it reads a document. A label line splits at its first `:`. The value never
  enters the key.
- The structure must equal one layout exactly. An extra label, a missing line or a different title
  is a miss, and the chat model answers that document.
- Write one layout for each distinct title and structure that the inputs show. Copy titles and
  labels exactly, including case. Literals hold no `:` and no leading or trailing space.
