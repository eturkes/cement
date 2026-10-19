---
paths:
  - "README.md"
  - "docs/**"
  - "examples/**/README.md"
---

# Human-facing prose law

Surfaces = `README.md`, `docs/*.md`, `examples/*/README.md`, CLI `--help`. Register = ASD-STE100 per `CLAUDE.md` `Authoring` `Human-facing`. Sentence length is judged, never capped (owner ruling: `CLAUDE.md` `Authoring` keeps text caps out of checks). The filler ban is graded today by D25 (`tests/test_cli_removal_battery.py`: paragraphs changed since `36f7890` + the root help description), D29 (`tests/test_cli_channels_battery.py`: paragraphs naming `cement resolve` or `cement proposal submit`) and the `function eval` help test (`tests/test_cli.py`), and over every Markdown surface (`README.md`, `docs/*.md`, `examples/*/README.md`) by the gate's `register` step (`.agent/register-audit --gate`: a filler hit → rc 1); CLI help reaches the filler ban through D25's root description + the `function eval` help test alone.

- Re-derive every claim against SHIPPED CODE, never against the inventory that scoped the work: an accurate inventory of WHAT to fix still carries role errors that flow straight into new prose. An inventory is attention-directing; the source is authoritative.
- State publication POSITIVELY: a reader must learn from prose alone that a surface exists, plus its authority, return, row cost, idempotency and failure containment. Docstrings are not publication — a unit can ship a fully documented public API that no human-facing surface names. The mechanical test is grepping each new name across README and every normative document.
- Every placeholder in a shipped command block needs a producing command earlier in the SAME block, and a numbered lifecycle is ordered by EXECUTION, not by API surface — each step's precondition must be produced by an earlier one.
- A trust-model "Trusted" list must never name an artifact the code parses as untrusted input. What is trusted on a ledger-free path is the host runtime and the channel delivering the independently held expected hash, never the bytes being validated. Check every Trusted entry against the validator that actually reads it.
- Qualify a claim in one place and it stays false everywhere else: grep every public surface for the unqualified form the moment a qualifier lands.
- Never imply speed or caching for `resolve`; cite the measured cost. Keep `ledger-free`, `import-free` and `capability-free` distinct — collapsing them misleads least-authority and sandbox design.
- Register audit = `.agent/register-audit` (p12 + p40); plain mode prints every sentence with its word count for the judgment pass. Spec: drop fenced code, skip headings and table rules, split table cells, join wrapped bullet and paragraph lines, blank inline code and link targets, sentence-split on `.?!` with abbreviation and ordinal guards, print each sentence's word count for the judgment pass (never a cap), regex-count filler, passive, modal, contraction and em-dash. Contractions match by form (`'s` only after a pronoun), so a possessive never counts; a blank line, heading or bullet ends a block, so a block without terminal punctuation never joins its neighbour.
- Split bullets and table rows into their own units before any paragraph-level check: a 33-line markdown bullet list is ONE paragraph, so one bullet's vocabulary contaminates its siblings.
