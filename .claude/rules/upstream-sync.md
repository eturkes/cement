---
paths:
  - "CLAUDE.md"
---

# Upstream sync — `CLAUDE.md` template refresh

`CLAUDE.md` = a verbatim copy of `~/Projects/agents/claude/CLAUDE.project.md`, an upstream that knows nothing of this repo; a refresh overwrites it whole, so project law never lives there. Every refresh carries sound generic rules AND silently reverts repo-measured law → reconcile, never revert.

## Recipe

1. `cmp CLAUDE.md ~/Projects/agents/claude/CLAUDE.project.md` ⇒ the working tree is upstream verbatim.
2. `git -C ~/Projects/agents diff <last-sync> HEAD -- claude/CLAUDE.project.md claude/prompts/` = the genuine upstream delta; each upstream commit body carries its rationale.
3. `git checkout HEAD -- CLAUDE.md` restores downstream state → fold the delta on hunk by hunk, adapting each to the invariants.
4. Record the new `<last-sync>` here in the same commit.

`last-sync = agents@bc2c494`.

## Invariants a refresh must keep, else restore

- Line 1 = the `@.agent/spec.md` import. A missing import is SILENT — the check is a fresh `claude -p` answering a spec-only question with zero tool calls.
- `Session flow` names `.agent/spec.md` (≤ 8 KB, five sections: `Intent`, `Artifacts`, `Decisions`, `Deferred`, `Phase`) plus `.agent/review.md`; `Engineering` routes off-path improvements to `Deferred` rows.
- The `.claude/rules/` two-tier bullet (bare | `paths:`) — the sole carrier of project law and of what a teammate inherits.
- No `## Claude Code` section and no retired-flow reference: session slash commands, the attached ledger trio, Serena, `read-guard`.

## Repo-measured law the template never carries

- ARTIFACTS: every dispatchable artifact = `.agent/decisions/m<m>u<u>-*`, never `.agent/contracts/`. Review rows land in `.agent/review.md`; where a validator grades them, they enter ONLY through an idempotent `--check` patcher asserting its id set (the `m3u5b-rule-attack.py` pattern), never by hand.
- `attack` and `mut` are WORK-UNIT instruments with `--check` patchers: each unit contract pins a NUMBERED gate list that every closure claim reruns, so moving either to the review pass unbuilds every closure claim. The review lens that matters for a removal is closure — an obligation whose pin was deleted with the behavior keeps the gate green.
- REPORTS ARE INLINE: the subagent harness forbids report/summary/findings `.md` files, so a brief naming a report PATH makes the teammate choose between policy and brief and withhold its marker. Teammate deltas for MAIN-retained files return inline too; MAIN materializes `.scratch/agents/<name>.md` itself where it needs the bytes addressable.
- `test` IS DIFF-BLIND ON TWO COUNTS audited separately: its OWN worktree baseline is REQUIRED reading (the contract's git-object pins), while the primary tree's `src/`/`tests/`/`docs/`, `git show main:` and `git diff main` stay unread — audit over the transcript under a positive control listing the worktree's own paths. MAIN owns the red-at-baseline / green-at-HEAD credential, REPORTED never forced.
- CONTRACTS are COPIED into each worktree at dispatch (`cp` + `cmp`); a gate added mid-unit invalidates that unit's pins instead of strengthening them.
- HARVEST reads `git diff --name-status main..wt/<name>` BEFORE choosing a merge verb, `prod` briefs order the validator LAST, `orc` is told NOT to match MAIN's rulings, and every cited tip is tagged `archive/m<m>u<u>-<role>` before its branch goes. Mechanics live in `.claude/rules/ops.md`.

## Superseded — do not restore

- `wt/` branch retention: tips archive as `archive/m<m>u<u>-<role>` tags before the Close order removes their branches (M3.4's five predate the convention and keep their `m3u4-*` names).
- The `N% NK/240K` gauge denominator: records read `N% NK/<window>` as `context-gauge` prints it, so compare pre-switch records by absolute K, never by percentage.
- Roadmap-flow machinery: the attached ledger trio, MODE dispatch, `est <raw> → <cal> sessions` calibration and the milestone/unit ledger. The archived records under `.agent/archive/` are history; the phase flow's live state is `.agent/spec.md`.
