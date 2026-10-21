---
name: cement-learn
description: Run one Cement learning pass for one operation. Use this skill only when the operator asks for a learning pass. The pass reads the chat answers that a deployment retained, merges the scripts of each recurring case into one output, reviews them as the learning-pass reviewer, and then compiles, verifies and promotes a new function version through the cement CLI. The pass never switches a function on or off.
license: Apache-2.0
compatibility: Requires the cement CLI (Python 3.11 or later) and write access to the Cement ledger.
---

# Cement learning pass

Cement turns repeated LLM work into deterministic functions. A chat deployment retains each
answer that the model gave for an operation as a pending proposal. This skill is the learning
pass: it reads those proposals, decides what the answer for each case is, and publishes a new
version of the operation's function. A person then decides whether to switch the function on.

Run this skill only when the operator asks for it. Do not start a learning pass on your own.

## Before you start

The operator gives you the ledger path, the partition and the operation name. Set them once
(the commands below use these names):

```sh
export CEMENT_DB=/path/to/ledger.db CEMENT_PARTITION=tenant_a OP=extraction_plan
```

Every command prints JSON. Exit code 0 means success. Any other exit code is a refusal. A
refusal with exit 2 or 3 wrote nothing: fix the command or the id, then run it again. A refusal
with exit 4 means that the ledger state does not allow the step: run `cement learn cases` again
and continue from what it shows. Stop and report any other code. The workflow reference
(`references/workflow.md`) explains each code.

## Steps

1. Read the work list.

   ```sh
   cement learn cases "$OP"
   ```

   If `program.json` exists from an earlier pass and `cement projection show "$OP"` does not
   show that program, the earlier pass stopped before step 4. Run `cement learn cases "$OP"
   --program - < program.json` instead, finish step 3 for any case that still lists pending
   proposals or more than one active output (a merge stopped before its supersession), and
   continue with step 4.

   Otherwise, if `nothing_to_learn` is `true`, check `grouped_by` first. If it is `exact` and a
   case has support 1, an earlier pass confirmed answers without projection: go on to step 2,
   because projection can join those cases. Otherwise report "nothing to learn" and stop. If no
   proposal is pending but `work` lists unfinished steps, an earlier pass was interrupted.
   Finish step 3 for each case in `work.merge_key_hashes` (its confirmed outputs differ), then
   continue with step 4 or step 5.

2. Decide whether the operation is projectable. It is projectable only when every output is a
   procedure over the input (a plan or a script that reads values from the input) and no output
   contains a value copied from an input. Answers that interpret values are never projectable.
   If it is projectable, derive the program from the raw inputs. The command groups the cases by
   it and prints it as `program`:

   ```sh
   cement learn cases "$OP" --projectable
   ```

   Save that `program` object as `program.json` and keep that file until step 4 finishes: the
   ledger holds no record of a program before `projection set`. From now on, group the cases by
   the saved program (`references/projection.md`):

   ```sh
   cement learn cases "$OP" --program - < program.json
   ```

3. For each case, merge the scripts into one output that covers what every request in the case
   needed. Keep the union of the rows. Keep a difference when a request asked for it. Put no
   input value into a projectable output. Then review each pending proposal of the case with
   reviewer `learning-pass` and a note that names this run and your model:

   ```sh
   cement proposal review prop_1 --reviewer learning-pass --decision accept --note "run 7, model X"
   cement proposal review prop_2 --reviewer learning-pass --decision correct --output - --note "run 7, model X" < merged.json
   cement proposal review prop_3 --reviewer learning-pass --decision reject --note "run 7, model X: not a plan"
   ```

   Use `accept` when the proposal equals the merge, `correct` when it differs, and `reject` when
   it is unusable. Then compare the case's earlier active examples with the merge. If the merge
   extends an example, supersede the example to the merge. If the merge contradicts an example,
   revoke the example and give the reason:

   ```sh
   cement example supersede "$OP" ex_1 ex_2 --output - --reviewer learning-pass --note "run 7, model X" < merged.json
   cement example revoke ex_3 --actor learning-pass --reason "run 7: contradicts the merged plan"
   ```

4. If the operation is projectable, test the program and then set it:

   ```sh
   cement projection test "$OP" --program - < program.json
   cement projection set "$OP" --program - --actor learning-pass < program.json
   ```

5. Publish the new version:

   ```sh
   cement compile "$OP" --actor learning-pass
   cement function verify-drafts "$OP" --actor learning-pass
   cement function inspect "$OP"
   cement function promote "$OP" --expected-function-hash "$NEW_HASH" --actor learning-pass
   ```

6. Report the new function hash, the difference from the previous version, what the pass
   learned, and, for a projectable operation, the assumption that the projection makes:

   ```sh
   cement function versions "$OP"
   cement function diff "$OP" --from "$PREVIOUS_HASH" --to "$NEW_HASH"
   ```

## Rules

- Never run `cement function switch`. Switching a function on or off is the person's decision.
- Always review as `learning-pass`, and always name the run and the model in the note.
- Never repeat a write that may have succeeded. No write is idempotent, so a blind retry writes
  a second row. Run `cement learn cases` again to see what the ledger holds, and continue from
  there.
- A case seen once stays with the model. The operation's policy decides how many confirmations
  a case needs.

The full procedure, with each field of `learn cases` and each exit code, is in
[the workflow reference](references/workflow.md). The projection program format is in
[the projection reference](references/projection.md).
