---
name: cement-learn
description: Run one Cement learning pass for one operation inside Open WebUI. Use this skill only when the administrator asks for a learning pass. The pass reads the chat answers that Cement retained, merges the answers of each recurring case into one output, and publishes a new function version with the Cement learning tool. It never switches a function on or off.
---

# Cement learning pass (Open WebUI)

Cement turns repeated chat work into deterministic functions. When the chat model answers a
request that no learned function covers, Cement retains the answer as a pending proposal. This
skill is the learning pass: it decides the answer for each case, and the Cement learning tool
records that decision and publishes a new version of the operation's function. A person then
decides whether to switch the function on.

Run this skill only when the administrator asks for it. The administrator names the operation.
Every tool returns JSON. A result with an `error` key is a refusal; read its `message`. A refusal
wrote nothing, except a `merge_case` result that also has `completed`: it lists the writes made
before the refusal. After `conflict`, call `learn_cases` again and continue from what it shows.
After `integrity`, stop and report: the ledger needs the operator.

## Words

- A **proposal** is one retained answer: the operation, the exact input, the output that the chat
  model used, and its provenance (the chat model's full reply). A new proposal is pending.
- An **example** is a confirmed answer. Only examples count toward a case.
- A **case** is one key. Without projection the key is the exact input. With projection the key is
  the form layout of the input, so documents with different values and one layout share a case.
- A **version** is one published set of verified cases. It answers nothing until a person switches
  it on.
- The outputs of one case usually differ a little, because each user asked in their own words: one
  plan splits a section into several fields, another keeps it whole. That difference is the work
  of this pass. Merge it. It is never a reason to stop.

## Steps

1. Call `learn_cases` with the operation. `cases` lists each key with its `pending_proposal_ids`,
   its `active_example_ids`, its distinct `outputs` and its `support`. If `nothing_to_learn` is
   `true`, check `grouped_by` first. If it is `exact` and a case has support 1, an earlier pass
   confirmed answers without projection: go on to step 2, because projection can join those
   cases. Otherwise report "nothing to learn" and stop. Reject each id in
   `stale_pending_proposal_ids` with `reject_proposal`.

2. Decide whether the operation is projectable. It is projectable when every output is a
   procedure over the input (a plan that says where to find each value) and no output contains a
   value copied from an input, such as a patient's name. Outputs that list different rows are
   still procedures. Answers that interpret values are never projectable. When an output is
   unclear, read the chat model's reply with `show_proposal` (`provenance.reply`).

3. If the operation is projectable, call `learn_cases` again with `projectable` set to `true`. The
   tool derives the projection program from the documents, so you never write one. The cases now
   group documents by form layout. Pass the same `projectable` value to every later call.

4. For each case, write one merged output that covers what every request of the case needed.
   Start from the output with the most rows, and add each row that another output of the case has
   and it lacks. When two outputs split one part differently, keep the rows of both. Keep a
   difference when a request asked for it. Put no input value into a projectable output.

   Then call `merge_case` once for the case, with its `pending_proposal_ids`, its
   `active_example_ids` and the merged output. The tool accepts or corrects each proposal and
   supersedes each example whose output differs. Give a short `note` that says what the merge
   kept or added. Merge every case, also a case with support 1: its confirmation counts when the
   same layout comes back.

   Before you merge, call `reject_proposal` for a proposal that is not an answer for this
   operation, and leave its id out of `merge_case`. Call `revoke_example` for a confirmed example
   that is wrong.

5. Call `publish_version` with the same `projectable` value. It stores the projection program,
   compiles the cases, verifies them and promotes the verified set as a new version. A case needs
   two confirmations; a case seen once stays with the chat model. If `published` is `false`,
   report its `reason`.

6. Call `function_versions`, and `diff_versions` from the previous version to the new one when
   one exists. Report to the administrator:
   - the new function hash and what changed (on a first version, every case is new);
   - for each case: its support, and what the merge added or changed;
   - for a projectable operation: the layouts in `layouts`, and the assumption that documents with
     one layout need one procedure;
   - every refusal, with its message.

   If `function_versions` marks the new version `selected`, the switch follows the newest version:
   end with "The new version answers now, because the switch follows the newest version."
   Otherwise end with: "The new version is ready. Read it, then use the Cement switch button to
   switch it on." Never claim more than `selected` shows.
