# Learning pass workflow

This reference expands the steps in `SKILL.md`. Read it when a field or an exit code is unclear.

## What the ledger holds

- A **proposal** is one retained model answer: the operation, the exact input, the output that
  the model used, and its provenance (for a chat deployment, the reply text, the model and the
  chat and message ids). A new proposal is `pending`.
- A review turns a proposal into a confirmed **example** (`accept` or `correct`) or closes it
  (`reject`). Only examples count toward a case.
- A **case** is one key. Without a projection, the key is the exact input. With a projection,
  the key is the layout of the input (see `projection.md`), so documents with different values
  and one layout share a case.
- An example is **active** until it is revoked or superseded. Compile reads active examples of
  the current operation revision only.
- A **function version** is a promotion receipt. `function promote` publishes the set of
  verified cases as a new version. The person's switch decides whether chats use it.

## Reading `learn cases`

`cement learn cases "$OP"` writes nothing. Its JSON object holds:

| Field | Meaning |
| --- | --- |
| `grouped_by` | `exact`, `build-current` (the projection set for this revision) or `candidate` (the `--program` you passed, or the one `--projectable` derived) |
| `program` | only with `--projectable`: the program derived from the raw inputs, one layout per form structure; save it as `program.json` |
| `cases[]` | one entry per key: `key`, `key_hash`, `pending_proposal_ids`, `active_example_ids`, `outputs` (each distinct output with the proposal ids and example ids that carry it), `support` (active examples), `ready`, `blocked_reasons`, `artifact` (the build that already carries this case, with its status) |
| `unprojected` | proposal ids and example ids that the grouping program does not recognize |
| `stale_pending_proposal_ids` | pending proposals of an earlier operation revision; reject them, since they cannot be confirmed |
| `unsourced_pending` | pending proposals without a source id, with their provenance; check them for duplicates of one chat message by hand |
| `work` | unfinished steps under the build-current grouping: `merge_key_hashes` (cases whose confirmed outputs differ, so the merge step is unfinished), `compile_key_hashes`, `verify_artifact_ids`, `promote_artifact_ids`, `promote_blocked`, `prospective_function_hash`, `live_function_hash` |
| `nothing_to_learn` | `true` when there is nothing pending and no unfinished step |

Read a proposal's provenance with `cement proposal show prop_1`. The provenance holds the
model's script or reply, which is what you merge.

## Merging a case

1. Collect every output of the case: the pending proposals and the active examples.
2. Write one output that covers what every request needed. Keep the union of the rows. Keep a
   difference when a request asked for it (for example, a request that asked for the provider).
3. For a projectable operation, put no input value into the output. The output must read values
   from the input when it runs.
4. Review every pending proposal of the case against the merge:
   - equal to the merge → `--decision accept`;
   - different from the merge → `--decision correct --output -` with the merge on stdin;
   - unusable (not an answer for this operation) → `--decision reject`.
5. Compare each active example with the merge:
   - the merge extends the example (it is narrower) → supersede it, with the merge on stdin.
     Supersession replaces the judgment and adds no support: one observation counts once.
   - the merge contradicts the example (it is wrong) → revoke it and give the reason. A
     revocation also stops every version built on that example from answering.

   ```sh
   cement example supersede "$OP" ex_1 --output - --reviewer learning-pass --note "run 7, model X" < merged.json
   cement example revoke ex_2 --actor learning-pass --reason "run 7: contradicts the merged plan"
   ```

A case with two different active outputs is blocked (`confirmed outputs conflict`). Compile
builds nothing for it until you supersede or revoke the examples that differ from the merge.

## Publishing

Run the publication steps in one pass, because the live function fails verification between a
supersession and the next promotion, and chats then go to the model:

```sh
cement compile "$OP" --actor learning-pass
cement function verify-drafts "$OP" --actor learning-pass
cement function inspect "$OP"
cement function promote "$OP" --expected-function-hash "$NEW_HASH" --actor learning-pass
```

`function inspect` prints the prospective `function_hash`. Pass that value to `function promote`.
If promotion refuses because a promoted case conflicts with active evidence, go back to the merge
step for that case: the conflicting examples need a supersession or a revocation.

## Resuming

A pass can stop at any point. If `program.json` from the stopped pass exists and `cement
projection show "$OP"` does not show that program, the pass stopped before `projection set`:
group by the saved program (`cement learn cases "$OP" --program - < program.json`) and continue
from step 3. Under the saved program, a case with more than one active output stopped during the
merge step even when `work` is empty: `work` describes the stored program alone. Otherwise run `cement learn cases "$OP"` again. Proposals that you reviewed
are no longer pending, so the rerun shows only what remains. A case in `work.merge_key_hashes`
stopped during the merge step: supersede or revoke its examples that differ from the merge.
Then continue from the first step that `work` lists. A rerun after a complete pass
reports `nothing_to_learn`.

## Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | success | continue |
| 2 | invalid input or usage | fix the command or the JSON, then continue |
| 3 | not found | check the id or the operation name |
| 4 | conflict or state | read `learn cases` again; the ledger changed or the step does not apply |
| 5 | integrity failure | stop and report: the ledger needs the operator |
| 6 | negative verdict | stop and report the verdict |

## Report

End the pass with a short report to the operator:

- the new function hash and `function diff` against the previous version (on a first promotion,
  every case is new);
- for each case: what the merge added or changed, and which examples you superseded or revoked;
- for a projectable operation: the layouts the projection recognizes, and the assumption that
  documents with one layout need one procedure;
- any refusal, with its exit code and message.

Do not switch the function on. Tell the operator that the new version is ready to read and
switch on.
