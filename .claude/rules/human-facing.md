---
paths:
  - "README.md"
  - "docs/**"
  - "examples/**/README.md"
---

# Human-facing prose law

Surfaces = `README.md`, `docs/*.md`, `examples/*/README.md`, CLI `--help`. Register = ASD-STE100 per project `CLAUDE.md`; graded today by `test_d25_*` in `tests/test_cli_removal_battery.py` over paragraphs the diff changed.

- Re-derive every claim against SHIPPED CODE, never against the inventory that scoped the work: an accurate inventory of WHAT to fix still carries role errors that flow straight into new prose. An inventory is attention-directing; the source is authoritative.
- State publication POSITIVELY: a reader must learn from prose alone that a surface exists, plus its authority, return, row cost, idempotency and failure containment. Docstrings are not publication — a unit can ship a fully documented public API that no human-facing surface names. The mechanical test is grepping each new name across README and every normative document.
- Every placeholder in a shipped command block needs a producing command earlier in the SAME block, and a numbered lifecycle is ordered by EXECUTION, not by API surface — each step's precondition must be produced by an earlier one.
- A trust-model "Trusted" list must never name an artifact the code parses as untrusted input. What is trusted on a ledger-free path is the host runtime and the channel delivering the independently held expected hash, never the bytes being validated. Check every Trusted entry against the validator that actually reads it.
- Qualify a claim in one place and it stays false everywhere else: grep every public surface for the unqualified form the moment a qualifier lands.
- Never imply speed or caching for `resolve`; cite the measured cost. Keep `ledger-free`, `import-free` and `capability-free` distinct — collapsing them misleads least-authority and sandbox design.
- Register-audit spec (scratch-local today, `Deferred` p12/p40 ports it): drop fenced code, skip headings and table rules, split table cells, join wrapped bullet and paragraph lines, blank inline code and link targets, sentence-split on `.?!` with abbreviation and ordinal guards, flag >25 words (descriptions) and >20 (instructions), regex-count filler, passive, modal, contraction and em-dash. Two known false positives: a possessive `'s` reads as a contraction, and a block without terminal punctuation joins the next one.
- A grader whose strict branch is guarded by a recognized-opener list fails OPEN: every unlisted verb falls through to the looser description bound. Make the unclassified case fail and name the token; `Set` here is always the noun phrase (`Set promotion`), never the imperative.
- Split bullets and table rows into their own units before any paragraph-level check: a 33-line markdown bullet list is ONE paragraph, so one bullet's vocabulary contaminates its siblings.
