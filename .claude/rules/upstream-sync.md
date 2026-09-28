---
paths:
  - "CLAUDE.md"
---

# Upstream sync — `CLAUDE.md` template refresh

`CLAUDE.md` = a verbatim copy of `~/.local/app/agents/claude/CLAUDE.project.md`, an upstream that knows nothing of this repo; a refresh overwrites it whole, so project law never lives there. The flow around it = global `~/.claude/CLAUDE.md` + `~/.claude/agents/`, deployed from the same upstream. Every refresh carries sound generic rules AND silently reverts repo-measured law → reconcile, never revert.

## Recipe

1. `cmp CLAUDE.md ~/.local/app/agents/claude/CLAUDE.project.md` ⇒ the working tree is upstream verbatim; else `cp` the template over it.
2. `<last-sync>` = the upstream commit whose template equals `git show HEAD:CLAUDE.md`: `git -C ~/.local/app/agents log --format=%h -- claude/CLAUDE.project.md | while read -r c; do git -C ~/.local/app/agents show "$c:claude/CLAUDE.project.md" | cmp -s - <(git show HEAD:CLAUDE.md) && { echo "$c"; break; }; done`. The loop outranks the value recorded below.
3. `git -C ~/.local/app/agents diff <last-sync> HEAD -- claude/CLAUDE.project.md` = the genuine upstream delta; the commit bodies of `git -C ~/.local/app/agents log <last-sync>..HEAD -- claude/` carry its rationale. Upstream `claude/prompts/` reaches this repo only through a body the owner pastes.
4. `git diff HEAD -- CLAUDE.md` = what the overwrite took away. Divergence is zero by design, so a line it removes outside the step-3 delta is reverted repo law → fold it into its owning `.claude/rules/` file; `CLAUDE.md` stays the template byte for byte.
5. Sweep the invariants below, each retired form under a positive control naming its expected match count first.
6. Bind every new upstream clause to the `.claude/rules/` file carrying its downstream mechanics — the template states the law, `.claude/rules/` states how this repo satisfies it — and record `last-sync = agents@$(git -C ~/.local/app/agents rev-parse --short HEAD)` here, all in one commit.

`last-sync = agents@8fc2e19`.

## Invariants a refresh must keep, else restore

- Line 1 = the `@.agent/spec.md` import. A missing import is SILENT — the check is a fresh `claude -p` answering a spec-only question with zero tool calls.
- `Session flow` names `.agent/spec.md` (five sections: `Intent`, `Artifacts`, `Decisions`, `Tasks`, `Phase`) plus `.agent/review.md`, and binds spec size to LIVENESS — every line binds current or future work, superseded text dies in the commit that supersedes it, size emergent. A restored byte cap is a reverted upstream fix: it rewards compressing prose over deleting dead rows. `Tasks` = the phase checklist: `- [ ]` open units in spine order with acceptance + binding notes as indented sub-bullets, `- [x] <sha>` once committed, on-path finds appended, ticked rows cleared at phase close, last line = the pointer to `.agent/deferred.md`, where `Engineering` routes every off-path improvement and every scratch-validator port.
- The `.claude/rules/` two-tier bullet (bare | `paths:`) — the sole carrier of project law and of what a teammate inherits.
- `Execution` Git: the commit body names each teammate the work used (name, role, verdict). `.claude/rules/ops.md` Commits holds this repo's stronger form.
- `Session flow` Teammates: triggers + mechanics = global `CLAUDE.md` `Subagents`, role rules = `~/.claude/agents/<role>.md`; `consultant` on each phase plan, `reviewer` on every closing diff (one per lens in IMPLEMENT). A `Tasks` row, contract or `Accept:` line that funds review once and late contradicts it ⇒ the sweep runs over `.agent/spec.md` `Tasks` + unit `Accept:` lines, not over `CLAUDE.md` alone.
- Thinking depth = the session's `--effort`, set at launch ⇒ no project `.claude/settings*.json` env pin and no `.claude/agents/` definition overrides the user-level models, effort or roles.
- No `## Claude Code` section and no retired-flow reference: session slash commands, the attached ledger trio, Serena, `read-guard`, per-unit `dispatch:` lines, solo licences.
- `Engineering` carries the `Verification integrity` bullet — red-first witness, contract-owned output tables, skip/xfail approval, `green` = run + passed. `.claude/rules/assurance.md` `## Verification integrity` and `.claude/rules/ops.md` (green reporting, Commits witness) hold this repo's mechanics for it, so dropping the bullet orphans live law downstream.

## Repo-measured law the template never carries

- ARTIFACTS: every dispatchable artifact = `.agent/decisions/m<m>u<u>-*`, never `.agent/contracts/`. Review rows land in `.agent/review.md`; where a validator grades them, they enter ONLY through an idempotent `--check` patcher asserting its id set (the `m3u5b-rule-attack.py` pattern), never by hand.
- `attack` and `mut` are WORK-UNIT instruments with `--check` patchers: each unit contract pins a NUMBERED gate list that every closure claim reruns, so moving either to the review pass unbuilds every closure claim. The review lens that matters for a removal is closure — an obligation whose pin was deleted with the behavior keeps the gate green.
- `tester` IS DIFF-BLIND ON TWO COUNTS audited separately: its OWN worktree baseline is REQUIRED reading (the contract's git-object pins), while the primary tree's `src/`/`tests/`/`docs/`, `git show main:` and `git diff main` stay unread — audit over the transcript under a positive control listing the worktree's own paths. MAIN owns the red-at-baseline / green-at-HEAD credential, REPORTED never forced.
- CONTRACTS are COPIED into each worktree at dispatch (`cp` + `cmp`); a gate added mid-unit invalidates that unit's pins instead of strengthening them.
- HARVEST reads `git diff --name-status main..wt/<name>` BEFORE choosing a merge verb, `general-purpose` briefs order the validator LAST, a `tester` oracle is told NOT to match MAIN's rulings, every cited tip is tagged `archive/m<m>u<u>-<role>` before its branch goes, and a finding's anchor rematches against `git show wt/<name>:<path>` or that tag, never the moved tip. Mechanics live in `.claude/rules/ops.md`.
- THE TEAMMATE RECORD is `git log --grep '^Teammates:'` ⇒ every commit carries its own `Teammates:` line, an ad-hoc one included and `none` when MAIN worked alone, while the template names only the unit commit. Downstream is deliberately the stronger rule: without it the record is holed at exactly the commits no unit owns. Mechanics in `.claude/rules/ops.md` Commits.
- THE QUEUE is `.agent/deferred.md`, seeded from the frozen `.agent/archive/polish.md` and graded by `.agent/decisions/m3-deferred-validate.py`, whose floor is archive ids UNION the last committed queue's ids, so rows can be born but never dropped. Layout + the archive-path citation rule live in `.claude/rules/ops.md`; the archive's headers are not uniform, so any parser over it pins itself against the loose `^- \`pNN\`` count.

## Superseded — do not restore

- `wt/` branch retention: tips archive as `archive/m<m>u<u>-<role>` tags before the Close order removes their branches (M3.4's five predate the convention and keep their `m3u4-*` names).
- The `N% NK/240K` gauge denominator: records read `N% NK/<window>` as `context-gauge` prints it, so compare pre-switch records by absolute K, never by percentage.
- Roadmap-flow machinery: the attached ledger trio, MODE dispatch, `est <raw> → <cal> sessions` calibration and the milestone/unit ledger. The archived records under `.agent/archive/` are history; the phase flow's live state is `.agent/spec.md`.
- A project-local copy of the teammate triggers or role rules: both live upstream (global `Subagents`, `~/.claude/agents/`), which every teammate already inherits, so a duplicate here drifts.
- The phase-flow dispatch vocabulary — the `dispatch:` commit line, solo licences, the shape→role map and its role tags — retired upstream for `Teammates:` lines + the global triggers + named roles. Commits, `.agent/archive/`, decision records and `.agent/review.md` rows keep the old spellings as history.
- The byte cap on `.agent/spec.md` and an inline deferral queue: the queue is monotonic, so attached it is a permanent growth term, and the cap rewarded compressing prose over deleting dead rows.
- `Deferred` as the spec's unit section: the open units live in `Tasks`, the queue in `.agent/deferred.md`.
