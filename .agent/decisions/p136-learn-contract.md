# p136-learn contract — the learning pass reads shadow disagreements (revision 1)

Owner rulings (`.agent/spec.md` `Decisions` Shadow sampling): T3 = a disagreement becomes a pending
proposal that the learning pass merges like any other answer; T1 = the learning pass writes the
comparator. Tier `docs` for the skill text, `data` for the read projection (the pass re-reads
every proposal before it writes). MAIN alone (shallow: no downstream effect without the pass's own
reviewed writes).

## Obligations

- E1 `System.learning_cases` lists, per case, `shadow_proposal_ids` = its pending proposals whose
  source id starts with `shadow:` (a subset of `pending_proposal_ids`, arrival order).
- E2 `skills/cement-learn/SKILL.md` step 3 + `references/workflow.md` `## Comparator`: the three
  decisions for a shadow proposal (keep = merge to the case's output; adopt = merge to the new
  output; reject), comparator authoring with its limits, `cement function drift` in the report.
- E3 README `### The learning pass` names the field and the decisions.

## Gates

1. `tests.test_shadow` `test_learn_a_case_names_its_shadow_proposals` red at `a1686ad`; the skill +
   learning batteries (`tests.test_phase_integration_battery`, `tests.test_learning_pass_battery`)
   green.
2. Full gate = CI gate (`.agent/ci-gate p136-learn`).
3. Register + article audits rc 0.

```claims
13	SKILL.md` step 3	unchecked	a step position in the skill, not a count	-
```
