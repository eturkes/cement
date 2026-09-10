---
paths:
  - "CLAUDE.md"
---

# Upstream sync — `CLAUDE.md` template refresh

`CLAUDE.md` = a verbatim copy of `~/Projects/agents/claude/CLAUDE.project.md`, an upstream that knows nothing of this repo; a refresh overwrites it whole, so project law never lives there. Every refresh carries sound generic rules AND silently reverts repo-measured law → reconcile, never revert.

## Recipe

1. `cmp CLAUDE.md ~/Projects/agents/claude/CLAUDE.project.md` ⇒ the working tree is upstream verbatim.
2. `git -C ~/Projects/agents diff <last-sync> HEAD -- claude/CLAUDE.project.md claude/prompts/` = the genuine upstream delta; each upstream commit body carries its rationale. Its `prompts/` half reaches this repo only through a `/goal` body the owner pastes.
3. `git diff HEAD -- CLAUDE.md` = what the overwrite took away. Divergence is zero by design, so a hunk absent from the step-2 delta is reverted downstream law → `git checkout HEAD -- CLAUDE.md`, then fold the delta on hunk by hunk.
4. Sweep the invariants below, each retired form under a positive control naming its expected match count first.
5. Bind every new upstream clause to the `.claude/rules/` file carrying its downstream mechanics — the template states the law, `.claude/rules/` states how this repo satisfies it — and record the new `<last-sync>` here, all in one commit.

`last-sync = agents@539ca8b`.

## Invariants a refresh must keep, else restore

- Line 1 = the `@.agent/spec.md` import. A missing import is SILENT — the check is a fresh `claude -p` answering a spec-only question with zero tool calls.
- `Session flow` names `.agent/spec.md` (five sections: `Intent`, `Artifacts`, `Decisions`, `Deferred`, `Phase`) plus `.agent/review.md`, and binds spec size to LIVENESS — every line binds current or future work, superseded text dies in the commit that supersedes it, size emergent. A restored byte cap is a reverted upstream fix: it rewards compressing prose over deleting dead rows. `Deferred` = queue pointer + the unfinished units; the queue itself is `.agent/deferred.md`, where `Engineering` routes every off-path improvement and every scratch-validator port.
- The `.claude/rules/` two-tier bullet (bare | `paths:`) — the sole carrier of project law and of what a teammate inherits.
- No `## Claude Code` section and no retired-flow reference: session slash commands, the attached ledger trio, Serena, `read-guard`.

## Repo-measured law the template never carries

- ARTIFACTS: every dispatchable artifact = `.agent/decisions/m<m>u<u>-*`, never `.agent/contracts/`. Review rows land in `.agent/review.md`; where a validator grades them, they enter ONLY through an idempotent `--check` patcher asserting its id set (the `m3u5b-rule-attack.py` pattern), never by hand.
- `attack` and `mut` are WORK-UNIT instruments with `--check` patchers: each unit contract pins a NUMBERED gate list that every closure claim reruns, so moving either to the review pass unbuilds every closure claim. The review lens that matters for a removal is closure — an obligation whose pin was deleted with the behavior keeps the gate green.
- REPORTS ARE INLINE: the subagent harness forbids report/summary/findings `.md` files, so a brief naming a report PATH makes the teammate choose between policy and brief and withhold its marker. Teammate deltas for MAIN-retained files return inline too; MAIN materializes `.scratch/agents/<name>.md` itself where it needs the bytes addressable.
- `test` IS DIFF-BLIND ON TWO COUNTS audited separately: its OWN worktree baseline is REQUIRED reading (the contract's git-object pins), while the primary tree's `src/`/`tests/`/`docs/`, `git show main:` and `git diff main` stay unread — audit over the transcript under a positive control listing the worktree's own paths. MAIN owns the red-at-baseline / green-at-HEAD credential, REPORTED never forced.
- CONTRACTS are COPIED into each worktree at dispatch (`cp` + `cmp`); a gate added mid-unit invalidates that unit's pins instead of strengthening them.
- HARVEST reads `git diff --name-status main..wt/<name>` BEFORE choosing a merge verb, `prod` briefs order the validator LAST, `orc` is told NOT to match MAIN's rulings, every cited tip is tagged `archive/m<m>u<u>-<role>` before its branch goes, and a finding's anchor rematches against `git show wt/<name>:<path>` or that tag, never the moved tip. Mechanics live in `.claude/rules/ops.md`.
- THE DISPATCH RECORD is `git log --grep '^dispatch:'` ⇒ an ad-hoc commit carries its own `dispatch:` line, while the template makes the commit body the carrier a UNIT alone has. Downstream is deliberately the stronger rule: without it the record is holed at exactly the commits no unit owns. Mechanics in `.claude/rules/ops.md` Commits.
- THE QUEUE is `.agent/deferred.md`, seeded from the frozen `.agent/archive/polish.md` and graded by `.agent/decisions/m3-deferred-validate.py`, whose floor is archive ids UNION the last committed queue's ids, so rows can be born but never dropped. Layout + the archive-path citation rule live in `.claude/rules/ops.md`; the archive's headers are not uniform, so any parser over it pins itself against the loose `^- \`pNN\`` count.

## Superseded — do not restore

- `wt/` branch retention: tips archive as `archive/m<m>u<u>-<role>` tags before the Close order removes their branches (M3.4's five predate the convention and keep their `m3u4-*` names).
- The `N% NK/240K` gauge denominator: records read `N% NK/<window>` as `context-gauge` prints it, so compare pre-switch records by absolute K, never by percentage.
- Roadmap-flow machinery: the attached ledger trio, MODE dispatch, `est <raw> → <cal> sessions` calibration and the milestone/unit ledger. The archived records under `.agent/archive/` are history; the phase flow's live state is `.agent/spec.md`.
- A project-local copy of the shape→role map or the solo licences: both live in global `Subagents` b1, which the template cites, so a duplicate here drifts against the file every teammate already inherits. `Session flow` keeps the RECORDING rule (the `dispatch:` line, named by every unit, ITERATE turn AND ad-hoc request) plus the phase bindings, nothing more.
- Any reading of the phase bindings as a per-phase role WHITELIST: they WEIGHT b1's shape trigger, which is live in all four phases, and `rev` sits outside them — a closing diff draws one in every phase, unconditionally. A spine, contract or acceptance line that funds review once and late is that same misread one level down, so the sweep for it runs over `.agent/spec.md` `Phase` and the unit `Accept:` lines, not over `CLAUDE.md` alone.
- The byte cap on `.agent/spec.md` and an inline deferral queue: the queue is monotonic, so attached it is a permanent growth term, and the cap rewarded compressing prose over deleting dead rows.
