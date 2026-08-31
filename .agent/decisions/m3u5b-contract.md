# M3.5b acceptance contract — remove the `handle`/`request`/source CLI surface

Unit `M3.5b`, tier `kernel`, tags `-`, depends `M3.5a`. Entry HEAD `36f7890`, gate 901 tests OK.

Sections 1-9 are binding EXCEPT where section 10 corrects them; section 10 lists eight claim defects
and three scope corrections, and each overrides the section above it. Section 11 respecifies the
gates, because wave 2 found three of four could pass without binding.

No design fork exists in this unit, so no spike wave opens and no `orc` is dispatched. Grounds in
section 9.3.

---

## 1. Scope and boundary

M3.5b removes the OPERATOR-FACING route to the request lifecycle. It removes no library surface.

**Owned.** `src/cement_runtime/cli.py` grammar, import, helper and dispatch; the `tests/` fixtures
and instruments that name them; the CLI-route prose in `README.md`, `docs/architecture.md`,
`docs/threat-model.md`; gate 4 (`.agent/decisions/m3u5a-s2-probe.py`).

**Not owned, and an edit to any of these is a scope defect.**

| surface | owner | reason |
|---|---|---|
| `System.handle`, `System.request_status` | M3.6a | public lifecycle methods |
| `System.__init__(candidate_source=...)` | M3.6a | lifecycle constructor keyword |
| `models.py` request/result models, exports | M3.6a | lifecycle models |
| `store.py`, `requests` table, `SCHEMA_VERSION` | M3.6b | schema cuts ONCE at M3.6b |
| `source.py`, `_command_supervisor.py`, `example_adapter.py`, `docs/adapter-protocol.md` | M3.7 | relocation to the example surface |
| `examples/hospital_ocr/` code and README | M3.7, M3.8 | the demo drives the LIBRARY `System.handle`, which survives here |

**D01** M3.5b ships `System.handle` and `System.request_status` as public methods with NO operator
route. This is a ruled, temporary condition of the M3 track order, not a defect. State it once in
the contract; do not state it in shipped prose, which describes what exists rather than what is
scheduled.

---

## 2. Ground state, measured

### 2.1 Parser census

Derived from `_parser()` at `36f7890` and after the source-only deletion
(`.agent/decisions/m3u5b-burden.py`, stage 2).

| quantity | HEAD `36f7890` | after removal | pre-M3.5a `c8b82cd` |
|---|---|---|---|
| leaves | 30 | **28** | 28 |
| nodes | 37 | **35** | 35 |
| `parser_shape` actions | 163 | **151** | 154 |
| `parser_shape` digest | `8b58b465c08aa693` | **`ebd2ac811bd9776d`** | `af19339c3995c97d` |
| root commands | 14 | **12** | 14 |

The `c8b82cd` column is measured under the CURRENT digest algorithm, in a worktree carrying the
current probe. The roadmap's recorded `126` / `89dfa3d982d8c54b` is the pre-A23 algorithm over the
POST-M3.5a parser, which is a different pair of axes and is not comparable here.

**D02 — THE CENSUS COLLIDES AND THE DIGEST DISCRIMINATES.** The post-M3.5b census is **28 leaves /
35 nodes**, numerically EQUAL to the pre-M3.5a census over a DIFFERENT set: `c8b82cd` holds
`handle` and `request` and lacks `resolve` and `proposal submit`; the shipped state is the exact
inverse. A census pin on leaf and node COUNTS alone therefore cannot distinguish "M3.5a and M3.5b
both landed" from "neither landed". Every census obligation in this unit asserts the leaf-name SET,
and any count assertion travels with its set assertion in the same test.

`parser_shape` DOES separate the two states — 154 / `af19339c3995c97d` against 151 /
`ebd2ac811bd9776d` — which is measured evidence for keeping the digest beside the census rather than
a claim about it. The two instruments are not redundant: the census names WHICH leaf moved, and the
digest is the only one of the pair that notices the state at all.

### 2.2 Removal burden

`.agent/decisions/m3u5b-burden.py` against `36f7890`, gate run per stage, failures grouped by
deepest `tests/` frame. Committed measurement: `.agent/decisions/m3u5b-burden.json`.

| stage | deletion | broken | distinct frames |
|---|---|---|---|
| 1 | the two `add_parser` blocks | 113 / 901 | 11 |
| 2 | and `_source`, its construction site, both dispatch branches, the import | 119 / 901 | 17 |

**D03** The work list is **17 frames**, never 119 tests. 103 of stage 1's 113 failures stand behind
ONE frame, `tests/test_cli.py:193 in payload`, which asserts `status == 0` for three fixture
helpers that seed state through the `handle` CLI route: `confirm` (`tests/test_cli.py:217`),
`handle_once` (`:247`), `confirm_text` (`:2954`). Repairing those three helpers to seed through
`proposal submit` is expected to clear the 103; the remaining 16 frames are named in section 5.

### 2.3 Source removal

Seven anchored, occurrence-asserted edits, already committed as the `EDITS` table in
`.agent/decisions/m3u5b-burden.py` and re-runnable: the `handle` `add_parser` block, the `request`
`add_parser` block, the `_source` helper, the `source = None` construction collapsing to
`System(args.db)`, the `handle` dispatch branch, the `request` dispatch branch, and
`from .source import CommandCandidateSource`.

**D04** The implementation reuses that anchored edit table rather than hand-editing, so the
deletion re-derives from committed state and a moved anchor aborts loudly.

### 2.4 argparse behaviour, measured at HEAD

| probe | result |
|---|---|
| `hand op --input {}` | `_UsageError` `argument command: invalid choice: 'hand'`, message enumerates every root command |
| `reque r1` | `_UsageError` invalid choice |
| `proposal sub ...` | `_UsageError` invalid choice, enumerates every `proposal` leaf |
| `handle op --input {} --request x` | **ACCEPTED** — abbreviates to `--request-id` |
| `handle op --input {} --source-c '["x"]'` | **ACCEPTED** — abbreviates to `--source-command` |
| `compile op --act me` | **ACCEPTED** — abbreviates to `--actor` |
| `resolve op --inp {}` | rejected; `resolve` carries `allow_abbrev=False` |
| `challenge ... --request-id x` | `_UsageError` `unrecognized arguments: --request-id x` |

**D05** Subcommand names are EXACT-MATCH at both levels. A removed LEAF is therefore pinnable as an
invalid-choice `_UsageError` whose message enumerates the survivors, which is a complement
assertion for free. A removed FLAG on a surviving leaf reports `unrecognized arguments`. The two
shapes are distinct and both are pinned.

**D06** Legacy leaves abbreviate (`--act` reaches `--actor`), so flag removal is NOT pinnable as
absence. Every removed flag spelling AND every proper prefix of it must be refused by every
surviving leaf, derived over `_parser()` rather than enumerated by hand.

---

## 3. Removal obligations

**D07** `_parser()` exposes no `handle` leaf and no `request` leaf. `cement handle ...` and
`cement request ...` exit 2 through the `_UsageError` channel.

**D08** `cli.py` defines no `_source` symbol and imports no name from `.source`. Asserted over the
shipped module's AST, not over a text grep, so a renamed helper cannot satisfy it.

**D09** `cli.py` contains no `args.command == "handle"` and no `args.command == "request"` dispatch
branch, and constructs `System` with no `candidate_source` argument on any path.

**D10** The removed flag spellings `--request-id`, `--retry-failed`, `--source-command`,
`--source-id`, `--source-timeout` are refused by every surviving leaf, together with every proper
prefix of each spelling that is not a prefix of a surviving flag on that leaf. Derived from
`_parser()` per D06.

**D11** No CLI help text at any parser node names `handle`, `request`, a request identifier, a
retry, or a candidate source. Walk EVERY node, root and intermediates included: an
`add_parser(help=...)` string renders in the PARENT's listing and never in the child's own
`format_help()`.

---

## 4. Preservation obligations

**D12** The surviving leaf-name SET equals exactly the 28 members of the HEAD set minus `handle`
and `request`. Asserted as SET EQUALITY (a complement), never as a forbidden list, and never as a
count alone (D02).

**D13** The 12 surviving root commands are `operation`, `resolve`, `proposal`, `compile`, `verify`,
`promote`, `challenge`, `example`, `artifact`, `report`, `function`, `events`.

**D14** Every surviving leaf keeps its options, defaults, choices, types and help byte-identical.
Carried by the re-derived `parser_shape` digest (D16), which moves on any such change.

**D15** `src/cement_runtime/system.py`, `store.py`, `models.py`, `source.py`,
`_command_supervisor.py`, `example_adapter.py` and every file under `examples/` stay byte-identical
to `36f7890`. Asserted against git objects, so a scope breach fails rather than passes silently.

**D16** `proposal submit`, `proposal show`, `proposal list`, `proposal review` and `resolve` keep
their exit classes and payload key sets from M3.5a's contract unchanged.

---

## 5. Instrument re-base obligations

Every pin below records a value that this unit is CHARTERED to move. Each is a deliberate re-base,
not a regression, and each is named here per the standing rule that a freeze pin over a file the
unit's obligations touch becomes a numbered obligation in the session that opens the unit. A pin
NOT in this list that goes red is a real finding.

**D17 — gate 4** (`.agent/decisions/m3u5a-s2-probe.py`), five failing checks, measured:

| check | want at HEAD | want after |
|---|---|---|
| `parser_census.leaves` | 30 | 28 |
| `parser_census.nodes` | 37 | 35 |
| `parser_shape.actions` | 163 | 151 |
| `parser_shape.digest` | `8b58b465c08aa693` | `ebd2ac811bd9776d` |
| `parser_census.lost_baseline_leaves` | `[]` | `['handle', 'request']` |

`BASELINE_LEAVES` keeps `handle` and `request` as members: the frozenset records the `c8b82cd`
baseline, which is history and does not move. The EXPECTATION moves instead, from "nothing is lost"
to "exactly these two are lost". Gate 4 must exit 0 over all 16 checks after the re-base.

**D18** The eleven remaining stage-1 and stage-2 frames, each re-based in place with its property
preserved:

| frame | property to preserve |
|---|---|
| `test_cli.py:193 in payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal submit`; the 103 assertions they shield stay unchanged |
| `test_cli.py:480 test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay machine-readable |
| `test_cli.py:4754 in options` | leaf-option census |
| `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion |
| `test_cli_channels.py:1458 v28` | cross-leaf option isolation |
| `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once |
| `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported constant |
| `test_cli_channels.py:2605 x21` | both new leaves omit every source option |
| `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the surviving set |
| `test_cli_channels.py:2801/2811 x26` | **inverted**: `CommandCandidateSource` is no longer imported |
| `test_cli_channels.py:445 v05` | a configured candidate source is never called |
| `test_cli_channels_battery.py:139 _leaf_parser` | battery leaf-parser helper |
| `test_cli_channels_battery.py:571 d03` | dispatch reaches no source |
| `test_cli_channels_battery.py:1799 d16` | aggregate cap derivation |
| `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the `_source` spy targets a deleted symbol |
| `test_cli_channels_battery.py:2733 d25` | census, re-based per D02 |
| `test_cli_channels_battery.py:2861 d26` | preserved-neighbour assertions |
| `test_cli_channels_battery.py:3059 d27` | B02 frozen tuple |

**D19** `x26` and `d24` INVERT rather than move. `x26` asserts `CommandCandidateSource` remains
imported; `d24` spies on `cli._source`, which ceases to exist, so `mock.patch.object` raises rather
than fails. A pin left asserting the pre-removal property tests nothing after the removal, and a
spy on a deleted symbol is an error rather than a verdict. Both are rewritten to assert the
post-removal property directly.

**D20** `tests/test_submission_battery.py` B02's docstring narrates D25's "28 to 30 leaves and 35 to
37 nodes" migration. That prose goes stale WITHOUT failing, because B02 asserts only
`_command_supervisor.py` and `example_adapter.py` byte equality. Silent staleness is the defect
class that has closed seven consecutive units; the docstring is corrected in this unit.

**D21** The battery's independent `parser_shape` oracle is DELIBERATE duplication — importing the
graded function would make the check circular — and it carries a standing re-derivation cost. It is
re-derived to 151 actions and `ebd2ac811bd9776d`, and the duplication stays.

---

## 6. Documentation obligations

**D22 — THE PROSE SPLITS BY ROUTE, AND BOTH DIRECTIONS OF ERROR ARE DEFECTS.** CLI-route prose
describes commands that cease to exist and MUST change. Library-API prose describes
`System.handle`, which survives until M3.6a, and MUST NOT change here: deleting it breaks the track
order and pre-empts M3.6a's own doc pass.

| locus | route | disposition |
|---|---|---|
| `README.md` quick start, `uv run cement ... handle support.reply --request-id ...` | CLI | rewrite onto `proposal submit` |
| `README.md` "Repeat with a distinct request ID until the confirmations satisfy the policy" | CLI | rewrite |
| `README.md` `handle`/`request` return-state table (`in_progress`, `fallback_failed`, `rejected`, `reconciliation_required`) with `Poll request REQUEST_ID` advice | CLI | remove; no command reaches these states |
| `README.md` "The ordinary `handle` result exposes a proposal ID" | CLI | rewrite |
| `README.md` `System.handle(...)` API example and its `request_id=` argument | library | KEEP |
| `README.md` "Only the `handle` and `request` route still carries a request identifier" | mixed | re-scope to the library route |
| `docs/architecture.md` steps 1-3, "Steps 1 to 3 describe `handle`, the request lifecycle" | library | KEEP |
| `docs/threat-model.md:78` "`handle` request ID as an idempotency key" | library | KEEP |
| `examples/hospital_ocr/README.md` `System.handle(...)` | library | KEEP |
| `docs/adapter-protocol.md` | M3.7 | untouched |

**D23** No shipped human-facing surface instructs an operator to run a command that does not exist.
Mechanical test: extract every `cement <command>` invocation from README, `docs/*.md` and
`examples/*/README.md`, and require each to parse under `_parser()`.

**D24** Every placeholder a shipped command block consumes has a producing command earlier in the
same block. The quick-start rewrite changes which command produces the proposal ID, so this is
re-checked rather than assumed.

**D25** Rewritten human-facing prose holds the project register: instructions ≤20 words per
sentence, descriptions ≤25, imperative steps, active voice, condition before command.

**D26** Root help describes deterministic resolution plus explicit supervised proposal capture, and
names no request lifecycle.

---

## 7. Supersession

**D27** This unit supersedes three M3.5a obligations. M3.5a is DONE and its contract is history;
the supersession is recorded HERE and the affected tests are re-based in place, so no M3.5a record
is rewritten.

| M3.5a obligation | superseded clause | replacement |
|---|---|---|
| D24 | zero `_source` calls from either new leaf | `_source` does not exist (D08) |
| D25 | census 28 → 30 leaves, 35 → 37 nodes; all 28 baseline leaf paths survive | census 30 → 28 / 37 → 35 as a SET (D02, D12); exactly `handle` and `request` are lost (D17) |
| D27 | B02 narrates the 28 → 30 migration | B02's docstring records the 30 → 28 removal (D20) |

**D28** B02 keeps `cli.py` OUT of its frozen tuple. Re-pinning `cli.py` to a fresh baseline stays
rejected on M3.5a's own grounds: M3.6a and M3.7 are scheduled to edit it again, and a pin the plan
commits to breaking reports its next scheduled break as a defect.

---

## 8. Acceptance gates

A green suite is NEVER closure for a removal, because deleting a behaviour together with its pin
leaves the gate green and the coverage number unchanged. All four gates are required.

- **Gate 1** — `uv run python -m unittest discover -s tests -t .`, 0 failures, 0 errors, 0 skips.
- **Gate 2** — the diff-blind obligation battery, one test per D01-D28, graded by
  `m3u5b-battery-validate.py` with `UNFILLED-TESTS`, `OBLIGATIONS-UNCOVERED`, `ORPHAN-TESTS`,
  `ASSERTIONLESS`, `SKIPPED` and `AMENDMENT-UNCITED` all zero. Credential = red at the
  pre-implementation baseline, green at HEAD, audited as two separate counts.
- **Gate 3** — the mutation sweep over every touched predicate, its verdict module list PRINTED on
  the control line, its acceptance predicate written as a NAMED SURVIVOR SET, and its unmutated
  control reported GREEN on that same line.
- **Gate 4** — `.agent/decisions/m3u5a-s2-probe.py` exit 0 over all 16 checks after the D17 re-base.

**D29** Gate 2's battery must fail when ONE obligation remains undone OR ONE preserved invariant
disappears, and must rerun from this unit's committed checkpoint.

---

## 9. Method

### 9.1 Probe corpus seed

Removed-leaf invalid choice; removed-flag `unrecognized arguments` on a surviving leaf; every
proper prefix of every removed flag; help-text scan over every parser node; leaf-set equality;
`parser_shape` digest; byte equality of the six preserved modules; each shipped `cement` invocation
in prose parsed under `_parser()`; the three re-based fixture helpers seeding through
`proposal submit`.

### 9.2 Session split

Three sessions: S1 contract, S2 implementation, S3 battery plus closure.

### 9.3 No fork, and therefore no spike wave

The roadmap's M3.5a sizing correction binds: budget FOUR sessions for any unit that OPENS a spike
wave regardless of tag, and budget a unit with NO fork to rule WITHOUT S1 and S2. M3.5b has no
material design fork. The removal mechanics are settled by prior units (complement assertions over
`_parser()`, derived instruments, named survivor sets); the pin shapes already ship; the doc split
is a scoping ruling, not an alternative; and the only quantities in question were measurable
directly. MAIN measured them in this session rather than dispatching a `map`, because the prose
corpus is 1,080 lines with 56 vocabulary-hit lines and the last two map dispatches returned rows
MAIN had to re-derive before acting (6 of 55 re-derived on M3.5a). Teammate budget moves to wave 2,
where the measured yield is: the diff-blind verdict table, the contract attack, and the obligation
battery.

### 9.4 Wave 2

`test-m3u5b-1` diff-blind verdict table then the red suite; `rev-m3u5b-1` contract attack. Both
seeded by a MAIN-committed validator plus an all-`unknown` skeleton naming each row's SUBJECT, both
in worktrees based at the pre-implementation commit, both reporting INLINE with the marker as the
final line.

---

## 10. Verdict table rulings and contract corrections

`.agent/decisions/m3u5b-verdicts.json`, 70 rows (30 seeded V01-V30, 40 extension X01-X40), harvested
from `wt/test-m3u5b-1` @ `1f0ce30` by targeted checkout. Every row's `main_verdict` and `action` is
filled by `.agent/decisions/m3u5b-rule-verdicts.py`, which replays to byte-identical output and whose
`--check` fails when a later row goes unruled. 53 CONFIRMED, 17 divergent readings picked. Action
verbs: `ENCODE`, `ENCODE-SCOPED`, `GATE-SPEC`, `PROBE`, `DEFER`.

`.agent/decisions/m3u5b-attack.json`, 41 rows (23 seeded A01-A23, 18 extension Y01-Y18), harvested
from `wt/rev-m3u5b-1` @ `23935a2`. `disposition` and `main_note` are filled by
`.agent/decisions/m3u5b-rule-attack.py` under the same replay contract. 24 ACCEPTED, 2 SCOPED, 15
CLEARED.

**SECTIONS 1-9 CARRY EIGHT CLAIM DEFECTS. Each correction below OVERRIDES the section above it.**

| # | section | wrong as written | correct |
|---|---|---|---|
| 1 | D17 | "all 16 checks" | gate 4 grades **19** checks; the roadmap already recorded 19 (A09, V19) |
| 2 | D03/D18 | three cardinalities for one work list: prose 11, table 18 rows, measurement 17 | **17** code-coupled frames, plus **1** prose-coupled frame the census never scanned; the surplus table row `test_cli_channels_battery.py:139 _leaf_parser` is not a distinct frame (A18, X02) |
| 3 | D18 | "103 shielded assertions" | `test_cli` showed **105** failures; the three re-based helpers cleared **102**; **3** were re-based in place (A10) |
| 4 | D22 | the `handle`/`request` return-state table dispositioned `remove` | **KEEP.** No command reaches those states, but `System.handle` and `System.request_status` both survive and both return all six, so the table is live library-API documentation. Removing it does what D22's own header forbids. Its CLI-shaped caller actions are re-scoped instead (X27, Y18) |
| 5 | D14 | the `parser_shape` digest carries choices, types and help | it carries **none** of the three. It digests dest, option strings, default, required, nargs, class and `allow_abbrev`. Two D26 help rewrites left `151`/`ebd2ac811bd9776d` unmoved (A07, Y07, V15, X26) |
| 6 | D14 | cites D16 as the parser-shape carrier | **D17** defines the digest re-base; D16 specifies exit classes and payload key sets (Y01) |
| 7 | D28 | "M3.6a and M3.7 are scheduled to edit `cli.py` again" | **neither roadmap unit names `cli.py`**, and post-removal `cli.py` holds no lifecycle or source residue for either. The conclusion survives on the file's rate of change: two commits each from M3.5a and M3.5b, with M3.6b's refusal fixtures and M3.9a's documentation rewrite the plausible next editors (Y06) |
| 8 | S9 | "no design fork" | **five** material forks existed: global abbreviation, capture help, status-table scope, invocation extraction, digest sufficiency. All five are ruled below (X40) |

**Scope corrections that widen a binding obligation.**

- **D15's scope pin is short.** Section 9.1's six-module blob omits the examples tree and six runtime
  modules, so an example-scope breach or an `errors.py` change passes it silently. The pin widens to
  the **18** protected paths actually verified: 6 runtime modules and 12 example files, asserted
  against the named git object rather than a second copy of the bytes (A08, Y08).
- **D22's locus table is a FLOOR, never a census.** It omitted two CLI-route sentences in the
  proposal-submit section and the opening `handle(request)` fence. The two sentences were rewritten;
  the fence is PROTECTED on the same grounds as every other `System.handle` locus, and gate 5 cannot
  reach it because it is a ` ```text ` fence, so the battery asserts its byte equality directly
  (A13, X28).
- **D27's supersession table is short by one row.** M3.5a **D26** is superseded too: its
  source-import clause is inverted by M3.5b D19. The battery already inverted it; only the record was
  missing (A16).

| M3.5a obligation | superseded clause | replacement |
|---|---|---|
| D26 | `cli.py` imports `CommandCandidateSource` | `cli.py` imports no name from `.source` (D08), and `d26` pins the removed leaf's refusal enumerating the survivors |

**The five design forks, ruled.**

| fork | ruling |
|---|---|
| global `allow_abbrev=False` | **DECLINED.** A repo-wide grammar break needs its own mandate. The removal half is closed locally: D06 refuses every proper prefix of a removed flag over all 112 removed-flag/leaf combinations, D10 exempts prefixes a surviving flag legitimately claims. The public-grammar residue stays in the polish register, owned by no unit (X06, X07, X24) |
| explicit capture help | **TAKEN.** Root help named no lifecycle but its description still sold one. Two help-string edits outside the seven `EDITS`, neither of which moves the digest (X09, V29, A15) |
| status-table scope | **KEEP and re-scope**, per correction 4 |
| invocation extraction | **fenced shell blocks only.** Inline prose references legitimately omit required positionals and can never parse, so "every `cement <command>` invocation" is undefined without the corpus (X37, V27, A14) |
| digest sufficiency | **GAP NAMED, not closed.** Per correction 5; help, `choices` and `type` have no instrument anywhere in the repo, and that is a polish row with its acceptance check written (X26, A07) |

**Divergent readings picked.** V10 reading A (the exemption is what the LIVE parser resolves, not the
removed flag's original arity). V15 reading A (direct full-facet comparison, `shared=28`, `equal=28`,
`different=[]`; reading B is unsound because it rests on correction 5). V18 reading B (the M3.5a
SHIPPED git object is the preservation oracle; reading A leaves `proposal show`, `list` and `review`
with no oracle at all). V19, V27, V29, X02, X06-X09, X24, X26-X28, X31, X40 as ruled in the patcher.

**Two attacks SCOPED rather than accepted.** Y04: `candidate.json` is a caller-supplied input file,
not a value an earlier command produces, so D24's placeholder grammar (`*_FROM_*`, `*_REPLACE_ME`)
does not reach it. A23: a test docstring is an agent-consumed surface taking the dense project
register, while D25's ASD-STE100 caps bind human-facing prose alone — two registers, not a conflict.

---

## 11. Gate specification for S3, and stated limits

Wave 2 found that three of the four gates could pass without binding. S3 builds them as specified
here, not as sections 8-9 describe them.

**Gate 1 — full suite.** The complete committed suite, zero failures, zero errors, zero skips. Not a
targeted green subset (X36).

**Gate 2 — diff-blind obligation battery.** One test per D01-D28, and **one independent RED control
per obligation**. Inferring sensitivity from coverage is how a diff-blind battery ships assertions
that cannot fail, so the validator result and the red/green credential are separate artifacts from
the battery's ordinary pass (X33, X34). Compound obligations D15, D18 and D22 cannot be certified by
one asserted clause plus an obligation citation; each clause needs its own assertion and its own red
control, and D22 needs one per DIRECTION because a single-clause test can satisfy the CLI-route half
while violating the library-route half (X39). Three specific strengthenings:

- **D08/D09 need a runtime assertion, not an AST pin alone.** The literal conditions are satisfiable
  by an inline source class under a different name, or by a kwargs dictionary that leaves no named
  keyword node. Gate 2 asserts on every reachable CLI path that the constructed system's candidate
  source is None (A04, A11, Y02).
- **D20 must grade its own narrative.** B02's docstring can carry any census numbers and stay green,
  which is this unit's own defect class turned recursive. Gate 2 derives the census from `_parser()`
  and asserts the docstring contains it (A12).
- **D26 asserts a capture VERB, not the noun.** Keyword presence satisfies a naive reading while root
  help omits every verb telling a reader how to capture a proposal (A15).

**Gate 3 — mutation sweep. THE SPECIFICATION IN SECTION 8 IS VACUOUS.** It mutates touched predicates
read from the final tree; the seven `EDITS` delete five predicates and add none, so that set is
EMPTY and the gate passes without running anything. The catalogue is redefined as **REINSERTION
mutants**: re-add the removed leaf, each removed flag, the `.source` import, each dispatch branch and
the `candidate_source=` construction, and require a NAMED red per mutant. Only a mutation that
restores what was removed can bind a removal (A22). The control line binds the verdict modules, the
NAMED SURVIVOR SET and a green unmutated run together; a survivor count without names is not
checkable at the next unit (X35).

**Gate 4 — the executable probe.** `.agent/decisions/m3u5a-s2-probe.py`, **19** checks, rc 0.

**Gate 5 — shipped-prose parse, new in this unit.** `.agent/decisions/m3u5b-doc-parse.py`. Every
`cement` invocation inside a fenced shell block of `README.md`, `docs/*.md` and
`examples/*/README.md` parses under `_parser()`. Three control classes keep a green run from being
vacuous: an invocation floor, two synthetic REMOVED-leaf invocations that must fail, and one
SURVIVING-leaf invocation that must parse. Credited by mutation, not by its green result.

**EVERY GATE RERUNS FROM THE COMMITTED TIP.** Section 8 bound only gate 2 to a committed checkpoint,
so gates 1, 3 and 4 could support closure from uncommitted bytes — and did during S2, where gate 1
ran repeatedly from the working tree before the frame re-bases were committed. The closure credential
records the tip SHA beside each gate result (Y09).

**Stated limits.** These are recorded rather than repaired, because repairing them moves the
unverifiable step instead of removing it.

- **D04's procedure is not verifiable from the final state.** A direct edit producing identical bytes
  is indistinguishable from the staged apply; no diff-blind battery can separate them. The procedural
  credential is the commit record plus a rerun of `apply_stage(pathlib.Path('.'), 2)` over the
  committed `EDITS`, which aborts on a moved anchor rather than applying (A17).
- **D25 has no committed grader.** The register pass is by hand and cannot rerun from a clean
  checkout. Owner is the polish register's existing register-audit port row, which now has a third
  consumer; no duplicate row is opened (A21, X31).
- **Section 9's 56-hit figure is withdrawn.** It names no vocabulary matcher, and three reasonable
  route vocabularies over the stated corpus give 53, 60 and 68. An unreproducible count in a binding
  section is worse than no count, because it reads as measured (Y05).
- **Help, `choices` and `type` have no instrument.** Per correction 5. A mutant that rewrites a
  leaf's help into a lie, narrows `choices`, or swaps `type=int` for `type=str` survives gates 1, 4
  and 5 together.
