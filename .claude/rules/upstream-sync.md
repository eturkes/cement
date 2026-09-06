# Upstream sync

`CLAUDE.md` + `.claude/commands/*.md` = refresh copies of
`~/Projects/agents/claude/{CLAUDE.project.md,slash-commands/*}`, an upstream that knows nothing of this
repo. Every refresh carries sound generic rules AND silently reverts repo-measured law → reconcile,
never revert, and re-check every invariant below. This file is the checklist because it loads in every
session and reaches teammates; the command files themselves are overwritten.

## Recipe

1. `cmp` each refreshed file against its upstream twin ⇒ the working tree is upstream verbatim.
2. `git -C ~/Projects/agents diff <last-sync> HEAD -- claude/CLAUDE.project.md claude/slash-commands/`
   = the genuine upstream delta; each upstream commit body carries its rationale.
3. `git checkout HEAD -- <clobbered file>` restores downstream law → fold the delta onto it hunk by
   hunk, adapting each to the invariants.
4. Record the new `<last-sync>` here in the same commit.

`last-sync = agents@7e872af`.

## Invariants

- ARTIFACTS: every dispatchable artifact = `.agent/decisions/m<m>u<u>-*`, never `.agent/contracts/`.
  MILESTONE-REVIEW's ledger = `.agent/decisions/m<m>-review.json`, written ONLY through an idempotent
  `--check` patcher asserting its id set (`m<m>-rule-review.py`, the `m3u5b-rule-attack.py` pattern),
  never upstream's unpatched `.agent/review-m<m>.md`.
- REPORTS ARE INLINE: the subagent harness forbids report/summary/findings `.md` files, so a brief
  naming a report PATH makes the teammate choose between policy and brief and withhold its marker.
  Teammate deltas for MAIN-retained files return inline as well; MAIN materializes
  `.scratch/agents/<name>.md` itself where it needs the bytes addressable.
- UNITS ARE SIZED IN MAIN SESSIONS: `est <raw> → <cal> sessions` with the multiplier selected by analog
  SHAPE (1.00 repeat, up to 2.33 first-of-shape), never a milestone average and never upstream's
  `est <raw>K → <cal>K`. A `kernel` unit spans S1..S<k>, each session closing on its own checkpoint or
  DONE commit; entry cost — attached state + the ground-state read ≈ 150K — is why.
- `attack` + `mut` ARE WORK-UNIT INSTRUMENTS with `--check` patchers: each unit contract pins a NUMBERED
  gate list where mutation is a gate every closure claim reruns, so moving either to MILESTONE-REVIEW
  unbuilds every closure claim. `rev2`'s lens is removal closure — an obligation whose pin was deleted
  with the behavior keeps the gate green.
- `test` IS DIFF-BLIND ON TWO COUNTS audited separately: its OWN worktree baseline is REQUIRED reading
  (the contract's git-object pins), while the primary tree's `src/`/`tests/`/`docs/`, `git show main:`
  and `git diff main` stay unread — audit over the transcript under a positive control listing the
  worktree's own paths. MAIN owns the red-at-baseline / green-at-HEAD credential, REPORTED never forced.
- HARVEST READS `git diff --name-status main..wt/<name>` BEFORE choosing a merge verb: a worktree based
  at a pre-implementation SHA renders main's later commits as deletions, so `git merge --squash` there
  is a silent revert → take the file (`git checkout wt/<name> -- <path>`, sha256-proven).
- CONTRACTS are COPIED into each worktree at dispatch (`cp` + `cmp`) and pin a NUMBERED gate list; a
  gate added mid-unit invalidates those pins instead of strengthening them.
- `prod` briefs order the validator LAST; `orc` is told NOT to match MAIN's rulings.
- `pri` is a polish-row PREREQUISITE written beside the acceptance check at deferral, not a preference.

## Superseded — do not restore

- `wt/` branch retention. Tips now archive as `archive/m<m>u<u>-<role>` tags before the Close order
  removes their branches, and MILESTONE-REVIEW dispatches from the tags. Every tip the tracked record
  cites carries one: a record naming `wt/<role>-m<m>u<u>` resolves through `archive/m<m>u<u>-<role>`,
  with the roster's instance suffix kept where a unit ran several (`archive/m3u5b-test-2`). M3.4's tips
  predate the convention and keep their `m3u4-*` names.
- The `N% NK/240K` gauge denominator. Records read `N% NK/<window>` as `context-gauge` prints it
  (`/273K`) → compare pre-switch records by absolute K, never by percentage.
