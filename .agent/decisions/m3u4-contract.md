# M3.4 acceptance contract — request-free public seams behind one internal binding adapter

Unit `M3.4`, tier `kernel`, tags `oracle`, depends `M3.3`. Schema stays `SCHEMA_VERSION` 2.
Session budget = the corrected oracle estimator's four: contract, implementation, battery, closure.

Every section is RULED and binding. Sections 12 and 13 carry their rulings in S2 RULING blocks;
sections 14 and 15 amend the numbered obligations and correct two grounds. Where a numbered
obligation and a later ruling disagree, the ruling governs.

## 1. Scope

M3.4 freezes the proposal, read, review, report and event PUBLIC seams request-free, while the
private `requests` row survives untouched as storage plumbing. Nothing is deleted from the schema
and no consumer of the ledger loses information; what changes is WHO may name the request row and
WHAT a public value is allowed to carry.

IN SCOPE — exactly eight `requests` sites in `src/cement_runtime/system.py`, MAIN-derived at
`da63741` by AST attribution over every `requests` token:

| site | line | owner method | role |
|---|---|---|---|
| Q01 | 1300 | `get_proposal` | JOIN feeding `ProposalView` |
| Q02 | 1340 | `proposal` | JOIN feeding the single-proposal record |
| Q03 | 1378 | `proposals` | JOIN feeding the list projection |
| Q04 | 1451 | `review` | JOIN read under the write lock |
| Q05 | 1487 | `review` | companion `UPDATE requests SET status = 'rejected'` |
| Q06 | 1616 | `review` | companion `UPDATE requests` on accept/correct |
| Q07 | 2920 | `function_report` | pending-proposal count and detail |
| Q08 | 2940 | `function_report` | pending-gap projection |

OUT OF SCOPE — the other fourteen `requests` sites, each with its owning unit: `_persist_proposal`
627 (M3.3, private plumbing, already shipped); `handle` 813/828/839/920/956/1001/1011/1020/1056 and
`_fail_generation` 1071/1080 (M3.5b removes the grammar, M3.6a deletes the methods);
`request_status` 1280 and `revise_operation` 548 (M3.6a). Map row A05 tests that last pair; if wave 1
shows either is unreachable without a public request seam, it stays out and the roadmap records why.

NOT IN SCOPE AT ALL: deleting the `requests` table, adding columns to `proposals`, adding a view,
bumping `SCHEMA_VERSION`, or changing any CLI grammar. Those belong to M3.5a/M3.5b/M3.6a/M3.6b.

## 2. Premise correction, binding on every downstream artifact

The M3 plan draft's `### M3.4` acceptance seed reads: *"an application-SQL trace/proxy rejects any
statement that names the `requests` table."* That predicate is FALSE-BY-CONSTRUCTION here and does
not ship.

Grounds. The draft was authored assuming M3.3 delivered a dual-compatible schema v3. The reviewed
plan (`m3-plan-review.md` F016, adopted into the roadmap) cuts schema ONCE, at M3.6b. So under M3.4
the `proposals` row still holds no scope, no input and no operation revision — `_persist_proposal`
(`system.py:599-672`) writes them onto a private `requests` row, and every read recovers them by
join. A proxy rejecting statements naming `requests` would reject the unit's own storage layer.

The predicate that replaces it is CONFINEMENT plus PUBLIC SHAPE, section 3 and section 4. This is the
standing rule that a prescription authored in an earlier unit expires when the unit it was written
against lands, and is re-derived at HEAD before implementation.

## 3. D01-D06 — the confinement obligation

D01. After M3.4 exactly ONE named private surface may reach the `requests` row on behalf of the eight
sites. Its identity is fork-dependent (section 12) but its existence is not.

D02. The pin is a COMPLEMENT assertion, never a forbidden-list grep. Derive from the shipped source:
walk `system.py` with `ast`, collect every string constant reachable inside each top-level function
and method, tokenize SQL identifiers, and assert that the SET of definitions whose SQL names
`requests` EQUALS an explicit permitted set. A forbidden list fails open on exactly the member nobody
thought of; a complement fails closed and auto-covers every definition added later.

D03. The permitted set immediately after M3.4 is exactly: `_persist_proposal`, `handle`,
`_fail_generation`, `request_status`, `revise_operation`, plus the adapter section 12 names. Every
one of `get_proposal`, `proposal`, `proposals`, `review`, `function_report`, `_proposal_record` and
`_proposal_content` MUST be absent from it.

D04. The instrument must see module-level constants too, not only function bodies. Under an
alternative that hoists SQL into a module constant the token moves out of every function, and an
instrument scoped to function bodies would report a clean set while the join is still composed into
seven consumers. Scope the walk to the whole module and attribute a module-level constant to its own
assigned name.

D05. Token matching is on SQL IDENTIFIERS, not substrings, and it is case-folded. `FROM ARTIFACTS`
escaped a prior instrument on case alone, and `requests` appears inside `requests_scope`. Tokenize,
case-fold, compare whole identifiers.

D06. D02's instrument is a TRIPWIRE the unit is expected to update deliberately, not a gate to route
around. A later unit that legitimately adds or removes a permitted member edits the permitted set in
the same commit. Satisfying it by HIDING an access — composing the table name at runtime, reaching
the row through a helper that builds SQL from fragments, or projecting it through a wider query —
inverts the gate and is a defect even though the test passes.

## 4. D07-D14 — public shape freeze

D07. `ProposalView` field tuple is exactly
`(id, partition, operation, operation_revision, input, proposed_output, provenance, created_at_us)`.
`request_id` is gone.

D08. `PendingProposalGap` field tuple is exactly `(proposal_id, operation_revision, input_hash)`.
`request_id` is gone. A gap is identified by its proposal, not by its request.

D09. `review` returns a new frozen `ReviewResult`. Its exact field set is section 13.

D10. No public dataclass, return value, CLI payload, event payload or `__init__` export reachable
from a proposal, read, review or report path carries request identity. `Resolved`, `Rejected`,
`ReviewRequired`, `InProgress`, `FallbackFailed`, `ReconciliationRequired` and `CandidateRequest`
keep their `request_id` fields because they are `handle`-lifecycle values owned by M3.6a — they are
simply no longer REACHABLE from `review`.

D11. Frozen shape is invisible to behavioural tests: removing a keyword-only marker, adding a
defaulted field and changing a return annotation all pass a full suite. Pin every shape in this unit
with one `inspect.signature` plus `typing.get_type_hints` test, and record in that test's docstring
that it carries every shape pin at once.

D12. The stored value keeps its full fidelity. Dropping `request_id` from a public shape must not
drop any other projected column, and the remaining fields must carry byte-identical values to the
pre-change projection for the same ledger.

D13. `_proposal_record` and `_proposal_content` are pure row-to-shape converters — neither names
`requests` today — so they change only by losing the `request_id` entry and by taking their input
from the adapter. Any growth in either is a design smell to report, not to absorb.

D14. Adding `ReviewResult` disturbs `models.py` ordering and the `__init__.py` export list plus
`__all__`. Both are part of the diff and both are pinned by the export census.

## 5. D15-D24 — preserved invariants

A green suite is NEVER closure here: deleting a behaviour together with its pin leaves the gate green
and the coverage number unchanged. Every item below is pinned INDEPENDENTLY, and the battery must
fail if any one of them disappears.

D15. Proposal status transitions `pending -> accepted | corrected | rejected` keep their exact row
writes and their order.

D16. Reviewer, note and `reviewed_at_us` provenance capture and validation bounds are unchanged.

D17. Accept and correct each create exactly one immutable example and return its id; reject creates
none. This is the single most valuable field in `ReviewResult` and section 13 may not drop it.

D18. `review`'s conflict-quarantine path and every condition reaching it are unchanged.

D19. Event sequencing and the `proposals.status_sequence` binding are unchanged. Event payloads carry
no request identity (D10).

D20. Cross-partition and cross-operation proposals stay invisible in every read path.

D21. `=` versus `LIKE` isolation survives on partition and operation. The fixture MUST carry `_`
colliders (`tenant_a` beside `tenantXa`, `echo_1` beside `echoX1`) and case variants, because `_` is
legal in a name AND a `LIKE` single-character wildcard, and ASCII case-folds by default. Four
independently live `=`->`LIKE` mutants once passed 307 tests on hyphen-only fixtures.

D22. `function_report` pending counts stay exact, detail stays bounded, and the tail beyond 10,000
rows stays reachable. Enumeration completeness needs a sentinel beyond any plausible `LIMIT`.

D23. Pending-row ORDER is PRESERVED, not fixed. `pending_proposals` orders by opaque `p.id`, so the
page is arbitrary though stable per ledger. Pin set membership plus per-ledger byte stability, or the
projected page as a prefix of the same ledger's unbounded page — never insertion order, which passes
twice and fails on the third run. Fixing the ordering to a meaningful key is OFF-SPINE for this unit
and belongs in `.agent/polish.md`.

D24. Every persisted scalar these paths convert stays fail-closed. All 13 user tables are `STRICT`
and the columns on this path are `NOT NULL`, so a raw `TypeError`/`ValueError`/`OverflowError` is
unreachable from a real ledger — keep the guards for defence in depth, and label any probe reaching
one as fabricated rather than citing it as a real-ledger repro.

## 6. D25-D27 — publication

D25. Docstrings are NOT publication. A reader must learn from PROSE ALONE that `review` returns
`ReviewResult`, what its fields mean, and that proposal reads no longer expose request identity.

D26. State the obligation positively and test it mechanically: grep `ReviewResult` across `README.md`
and every `docs/*.md`, and grep the removed `request_id` claims in a proposal/review/report context
across the same files. Current mentions to reconcile: `README.md` 6, `docs/threat-model.md` 1,
`docs/adapter-protocol.md` 3, `docs/architecture.md` 1.

D27. Qualifying a claim in the contract does not qualify it in the prose. The moment a scoping
qualifier is introduced anywhere, grep every public surface for the unqualified form. A shared
qualifier that reached the contract but not the README was the last unit's only real uncaught gap.

## 7. Sizing ruling — no pre-open split, and the measurement behind it

RULED: M3.4 ships as ONE unit. It does NOT get the pre-open split that M3.5b, M3.6a, M3.6b, M3.7 and
M3.9a need.

The plan draft estimated `260 prod / 240 test` and set a trigger at "a query diff above 320
production lines". The plan review's own L7 rejects that trigger as not pre-open measurable. So MAIN
measured the burden directly instead of forecasting it, by DELETING the surface and letting the gate
produce the work list — the standing rule after a token census mispredicted M3.1's break set.

Harness = `.agent/decisions/m3u4-burden.py`, results = `m3u4-burden.json`, three staged gate runs
against fresh worktrees at `da63741`:

- stage 1, drop the two `request_id` fields only: 252 broken of 744, standing behind just THREE
  frames — `system.py:1316` in `get_proposal` 227, `system.py:2676` in
  `_pending_proposal_gap_from_row` 24, and one shape test.
- stage 2, stage 1 plus the three production sites repaired (the `ProposalView` keyword, the
  `_proposal_record` dict entry, the `PendingProposalGap` keyword): 9 broken across 9 frames. So 243
  of stage 1's failures were a production cascade from two constructors, not test burden.
- stage 3, stage 2 plus `review` returning `ReviewResult`: 112 broken across 13 frames, of which 100
  stand behind ONE shared fixture helper, `tests/test_cli.py:245` in `confirm`.

The gap between 252 and 9 is the whole reason this section exists. A break COUNT is not a work list
until its shared frames are factored out, and the two numbers differ here by a factor of 28.

Read as a work list rather than a failure count: roughly 21 distinct test methods plus one fixture
helper, against about 20 production lines outside the adapter plus the adapter itself. That is an
order of magnitude under the draft's estimate, and it comfortably fits one implementation session.

This is also the standing caution about forecasts crossing a document boundary: the draft's
`260 prod / 240 test` is an ESTIMATE and is labelled as one here, never carried forward as a
measurement.

## 8. Instruments

Four, each with a distinct job, and closure is mechanical rather than a green suite:

1. CONFINEMENT instrument — section 3's AST complement assertion over the shipped module.
2. SHAPE instrument — one `inspect.signature` + `typing.get_type_hints` test per frozen shape (D11).
3. DIFF-BLIND BATTERY — one test per numbered obligation in this contract, authored against the
   contract and normative docs alone, never against MAIN's diff.
4. MUTATION SWEEP — mutants over every predicate this unit adds or edits, run against a green
   control. A survivor count is meaningless without its VERDICT MODULE LIST, so the harness prints
   the modules it graded with on the control line and every reported count quotes them.

Statement-count measurement, wherever it appears, must be TOTAL over the channel: overriding
`sqlite3.Connection.execute` alone misses `executemany`, `executescript` and `cursor().execute`.

## 9. Probe corpus seed

All three review decisions; corrected-output required and forbidden pairs; a stale-revision review;
proposals created through `submit_proposal` and through `propose`; scalar corruption of the MIDDLE
and the LAST of at least three proposals; pending rows past the 10,000 boundary; reverse insertion
order; partition/operation/revision colliders per D21; an orphaned proposal whose private request row
is absent or mismatched; and the adapter used inside `review`'s existing write transaction with
`connection.in_transaction` observed.

Corpus classes are budgeted separately: probes that demonstrate conformance are a CONTROL and cannot
discriminate two implementations. Only probes aimed at RULED disagreements are evidentiary.

## 10. Gate identity

Sole configured gate: `uv run python -m unittest discover -s tests -t .`, 744 tests at `da63741`,
about 175 s. Acceptance requires it green from committed state, plus every instrument in section 8
reporting mechanically: confinement set equal, shape pins present, battery grader `UNFILLED 0`, and
the mutation sweep at zero survivors against a green control with its verdict modules printed.

## 11. Deferred to `.agent/polish.md`

Pending-proposal ordering by a meaningful documented key (D23). Any adapter generalization beyond the
eight sites. Any `requests` site owned by a later unit.

## 12. FORK 1 — the binding adapter's shape (RULED, see also section 15)

Two spikes, identical 14-probe corpus plus the `Z50` swap probe, each DEFENDING one alternative:

- ALT-BINDING (`spike-m3u4-binding`): a row-level private resolver returning a frozen binding record;
  consumers stop writing joins entirely. Exposure: N+1 statements on the two list projections.
- ALT-PROJECTION (`spike-m3u4-projection`): one canonical private SQL constant plus one row-to-record
  validator, composed into consumer queries; list projections stay single-statement. Exposure:
  confinement is textual, and the guarantee is weaker than one function owning every access.

DECIDING CRITERION, added by MAIN after the spikes opened and sent to both as probe `Z50`: M3.6b is
defined as "the sole schema cut v2->v3: direct proposal columns, BINDING-ADAPTER SWAP, request table
and index deletion" (`m3-plan-review.md:243`). The adapter M3.4 ships EXISTS IN ORDER TO BE REPLACED
two units later. So the dominant question is not elegance or statement count but how much consumer
code the M3.6b swap touches. An adapter whose consumers survive the swap untouched earns real cost
now; one that forces every consumer to be re-edited at M3.6b has bought a rename.

Both spikes were told to MEASURE the swap by performing it, not to argue it.

WAVE-1 OUTCOME: THE FORK IS NOT RULED, and the reason is a defect in MAIN's dispatch rather than in
either teammate. Both spikes filled all 14 probe rows and both reported `adapter_present=False` on
every one: they answered the whole corpus against BASELINE, which is exactly what the brief ordered
("fill the graded artifact first, implementation second"). Thirteen of the fourteen probes I wrote
were answerable without an implementation, so the graded metric reached zero while measuring only the
status quo. Neither `Z50` row was ever added.

What survives is real and is not thrown away:

- `m3u4-spike-binding.json` and `m3u4-spike-projection.json` are a thorough BASELINE census — exact
  SQL statement counts per read path (`get_proposal` 7/1, `proposals` 7/1, `function_report` 19/13
  with 2 request statements, `review` accept 14/8 correct 14/8 reject 12/6), the collider matrix,
  middle-and-last corruption classes, the `.review(` call-site census (30 total: 24 tests, 5
  examples, 1 production), the `PendingProposalGap` dependent-site split, and the verbatim CLI JSON
  for all three decisions. Section 9's corpus and the battery both consume this directly.
- `wt/spike-m3u4-binding` DOES carry a real ALT-BINDING implementation: +433/-147 across
  `system.py`, `models.py` and `__init__.py`, adding `_ProposalBinding`, `_ProposalBindingSet`,
  `_proposal_binding`, a BATCH `_proposal_bindings` answering the N+1 exposure, and
  `_write_proposal_request_status`. Its own table never measured it, but the diff is evidence.
- `wt/spike-m3u4-projection` ALSO carries a real ALT-PROJECTION implementation: +181/-117, adding
  `_PROPOSAL_BINDING_SQL`, a `_ProposalBinding` record and a `_proposal_binding(row)` validator. It
  was uncommitted when `TaskStop` landed and was preserved by the close order's per-worktree status
  read, at `cb0ef3e`. Both spikes therefore built their alternative AFTER the flush directive
  re-ordered their work — the corpus defect delayed the implementations, it did not prevent them.

FIRST COMPARABLE NUMBER, and it favours ALT-PROJECTION: +181/-117 against ALT-BINDING's +433/-147,
for the same eight sites. It is a size measurement only, taken from two trees of unequal maturity,
and it settles nothing on its own — the deciding criterion remains `Z50`.

S2 ENTRY STATE for this fork: both worktrees are RETAINED and both hold a shipped alternative. Rule
by running the DIFFERENTIAL rows against the two committed diffs and by answering `Z50` on each,
which is now cheap because neither side has to be built from nothing.

DISPATCH CORRECTION, binding on every future spike: a probe corpus answerable against baseline does
not force an implementation. Either write each probe as a DELTA that requires both sides, or make the
implementation a separately graded deliverable the validator can see.

### RULING (S2) — COMPOSE. Adapter owns the whole statement; neither alternative ships as written.

Each spike's shipped diff carries a defect the other lacks, so the disposition is the composition,
not either token. Measured from the two committed trees at `aa77d9f` and `cb0ef3e`:

- ALT-PROJECTION's consumers survive `Z50` — every embedded `WHERE` names `p.` columns or the
  constant's own `binding_*` aliases, never `r.`, so rewriting `_PROPOSAL_BINDING_SQL` at M3.6b
  touches no consumer. That was the open question and the answer is favourable.
- ALT-PROJECTION fails D03 as shipped: `review` still issues two raw `UPDATE requests` statements
  (`system.py:1546`, `:1679` in its tree). A read-only SQL constant cannot confine a write, and the
  spike never built the missing writer.
- ALT-PROJECTION's `function_report` pays for textual confinement with a wrapping subquery
  (`SELECT ... FROM ( {SQL} WHERE p.partition = ? ) WHERE binding_operation = ?`), which
  materialises the partition's proposals before filtering by operation. Baseline filters
  `r.operation = ?` inside the join. That is a D22 regression bought for grammar.
- ALT-BINDING satisfies D03 in full — `_write_proposal_request_status` owns both `review` writes and
  no consumer names `requests`.
- ALT-BINDING pays a redundant statement: `_proposal_binding` is a SIDE lookup, so `get_proposal`,
  `proposal` and `review` each keep their own row query and add a second one, and `proposals` reads
  its feed then re-reads the same proposals by id list. Its adapter is a lookup beside the query
  rather than the query.
- ALT-BINDING at M3.6b degrades badly for the same reason: once `proposals` carries direct columns a
  side lookup has nothing left to look up, so the honest swap DELETES the adapter and rewrites all
  six call sites. ALT-PROJECTION's constant degrades into the canonical proposal projection and
  keeps its consumers. Z50 therefore splits ALT-BINDING's ownership from its survival.

SHIPPED SHAPE, taking each alternative's winning property:

1. ONE private read adapter `_proposal_bindings(connection, *, partition, selection)` issuing the
   COMPLETE statement per named selection — `_ProposalIds`, `_ProposalFeed(status, after_sequence,
   limit)`, `_PendingProposals(operation, limit)` — so a consumer supplies parameters and never SQL.
   Baseline cardinality (ALT-PROJECTION's property) with the adapter owning every access
   (ALT-BINDING's property). MEASURED statements naming `requests`, per selection, by
   `sqlite3` trace over the whole channel: `_ProposalIds` 1, `_ProposalFeed` 1,
   `_PendingProposals` 2. "One statement per call" is therefore FALSE as an unqualified
   claim and is withdrawn. `_PendingProposals` issues a count statement and a bounded
   detail statement, which is exactly the two request statements baseline issued for the
   report, so the cardinality obligation is MET while the one-statement wording is not.
   Whole-channel totals at the same measurement, for scale: `get_proposal` 8, `proposals`
   8, `function_report` 20, `review` on accept 15 — the last carrying 2 request statements
   because the adapter read is joined by `_write_proposal_request_status`'s write.
2. `_proposal_binding(...)` = the singular wrapper over `_ProposalIds`, cardinality-checked.
3. `_write_proposal_request_status(...)` taken from ALT-BINDING, unchanged in role: the sole writer
   of the private request row on the review path.
4. `_ProposalBinding` = a frozen record carrying every value recovered from the request row
   (`operation`, `operation_revision`, `input_json`, `input_hash`, `request_id`, `request_status`)
   plus the proposal row itself for `p.*` fields. Consumers read request-derived values ONLY through
   the record. The field is `input_json`, not `input`: it holds the stored TEXT and sits beside
   `input_hash`, so this sentence is corrected against the shipped code rather than the code against
   it. `partition` is also a field of the record, and it is the CALLER'S scope echoed back — the
   adapter takes it as an argument and never reads `r.partition` into it, so it is not a recovered
   value and the consumer gains no authority by reading it.

D06 grounds for rejecting bare textual confinement: composing a join fragment into six consumers is
the "builds SQL from fragments" case D06 names, and it passes the D02 instrument while the join is
still spread across seven definitions. Statement ownership is what makes the complement assertion
mean what it says.

Permitted-set delta for D03: add `_proposal_bindings`, `_proposal_binding` and
`_write_proposal_request_status`. `_ProposalBinding`, `_ProposalIds`, `_ProposalFeed` and
`_PendingProposals` hold no SQL and stay out.

## 13. FORK 2 — the `ReviewResult` payload (RULED)

`review` currently returns `Resolved(request_id, output, source="confirmed", example_id)` on
accept/correct and `Rejected(request_id, proposal_id)` on reject, and `cli.py:520` returns that value
straight to the operator channel.

- R1, the plan draft's prescription: `ReviewResult(proposal_id, status, example_id)`. Minimal, but it
  drops `output` from the operator's accept payload.
- R2: the same plus the confirmed `output`, dropping request identity ALONE.

Evidence already in hand: dropping `output` is what makes 100 CLI tests fail through one helper
(section 7 stage 3), which measures the payload's reach rather than settling it. The draft is a
prescription with an expiry date and R1 carries no independent grounds beyond minimality.

WAVE-1 OUTCOME: NOT RULED, same cause as section 12. But the baseline evidence needed to rule it is
now in hand and is recorded in both spike artifacts under `P08` — the verbatim CLI JSON emitted today
for accept, correct and reject, plus the return classes and exit codes. `wt/spike-m3u4-binding` has
already committed a concrete `ReviewResult`; MAIN rules its field set at S2 against that payload
rather than against the draft's prescription.

### RULING (S2) — R2+, four fields. `ReviewResult(proposal_id, status, example_id, output)`

```python
@dataclass(frozen=True, slots=True)
class ReviewResult:
    proposal_id: str
    status: Literal["accepted", "corrected", "rejected"]
    example_id: str | None
    output: JSONValue | None
```

Both spikes shipped R1, and R1 is REJECTED on D12. D12 forbids dropping any other PROJECTED value
while dropping `request_id`, and `output` is projected today on both confirming decisions
(P08 baseline accept/correct JSON). R1 drops it, so R1 trades one removal for two.

Field-by-field grounds against the P08 baseline:

| baseline key | disposition | grounds |
|---|---|---|
| `request_id` | REMOVED | the unit's purpose (D10). |
| `proposal_id` | KEPT, now on all three | already the reject identity; becomes the single identity for every decision, and it is the key every read path already accepts. |
| `status` | KEPT, REDEFINED | see the ruled change below. |
| `example_id` | KEPT | D17; `None` on reject, where no example is created. |
| `output` | KEPT | D12. `None` on reject. |
| `source` | REMOVED | constant `"confirmed"` on this path, and `status` now carries the same fact with more resolution. Not a projected value, so D12 does not reach it. |
| `artifact_id` | REMOVED | structurally `None` from every `review` return — it is `Resolved`'s handle-path field, and D10 keeps `Resolved` intact for M3.6a. Not a projected value. |

RULED PUBLIC BEHAVIOUR CHANGE, recorded with its grounds rather than absorbed silently: `status` was
`"resolved"` for BOTH accept and correct and is now `"accepted"` / `"corrected"`. Grounds — the
payload's status now equals `proposals.status`, so `proposal confirm` and `proposal show` agree on
one vocabulary; accept and correct become distinguishable without comparing outputs, which the
baseline payload could not do; and M3 is pre-1.0 under a fail-closed no-migration contract. Landing
site for the pin: the shape test carrying D11.

Exact CLI JSON under the ruled shape, keys sorted as `cli.py` emits them:

```
accept:  {"example_id": "ex_...", "output": {...}, "proposal_id": "prop_...", "status": "accepted"}
correct: {"example_id": "ex_...", "output": {...}, "proposal_id": "prop_...", "status": "corrected"}
reject:  {"example_id": null, "output": null, "proposal_id": "prop_...", "status": "rejected"}
```

Reject emits both null-valued keys rather than omitting them: one frozen shape means one key set, and
a scripted operator testing `example_id is None` beats one testing for a missing key. Exit code stays
0 on all three; no exit-class change is in this unit's scope.

## 14. S2 RULINGS — the five conflicts the diff-blind verdict table surfaced

`m3u4-verdicts.json` (57 rows, 22 seeded + 35 extension) reports five places where the shipped
implementation and the contract's own text cannot both be read literally. Every one is a defect in the
contract text, not in the shipped shape, because each obligation was written before the fork it
constrains was ruled. The rulings below AMEND sections 3, 4 and 5 and bind the S3 battery.

D01 IS AMENDED: exactly one named private READER and at most one named private WRITER, not one
surface. D01's "exactly ONE" was written while both spike alternatives were read-only, and section
12's ruling proved a read-only surface cannot confine a write - that is precisely why ALT-PROJECTION
failed D03 with two raw `UPDATE requests` left in `review`. The shipped set is `_proposal_bindings`
(reader) and `_write_proposal_request_status` (writer). Two members is a consequence of the row having
both a read and a write side; it is not a weakening. D03's "plus the adapter section 12 names" already
admits the plural and needs no change.

D02 ATTRIBUTION IS LEXICAL, and `_proposal_binding` is deliberately OUTSIDE the permitted set. D02
already describes a lexical AST walk; the word was never written down, so the table could read D02 and
D03 as call-closure attribution, under which the singular wrapper reaches `requests` and belongs in
the set. Lexical is the ruling, and it is SOUND rather than convenient: a delegating wrapper that
carries its own SQL naming `requests` lands in the set and fails the complement, and one that carries
no SQL cannot reach the row except through a permitted member. Confinement is a property of WHO
WRITES THE SQL, not of who calls it. Call-closure attribution would additionally drag every public
consumer back into the set and make the obligation unsatisfiable by construction.

D12 GAINS ITS MISSING DEFINITION. A PROJECTED VALUE is a value READ FROM THE LEDGER for that decision.
It is not a constant of the model being replaced. Measured on the pre-M3.4 return
`Resolved(request_id=..., output=final.value, source="confirmed", example_id=example_id)`:
`output` and `example_id` are ledger-derived and are KEPT - that is what rejects R1 - while
`request_id` is the value this unit exists to drop, `source` is the literal `"confirmed"` on this path
and `artifact_id` defaults to `None` because review creates an example and never an artifact. Removing
two path-constants drops no projected value, so section 13 does not conflict with D12.

D20 IS SCOPE-RELATIVE, per V20. Each read path hides everything outside the scope IT NAMES. A path
that names no operation carries no cross-operation obligation, and its partition obligation is total.
`proposals(partition, *, status, after_sequence, limit)` takes no operation and lists a partition-wide
feed, so a literal cross-operation reading of D20 makes the shipped signature non-conforming while
describing no reachable leak. `get_proposal`, `proposal` and `review` name a proposal id inside a
partition; `function_report` names both partition and operation and keeps the full obligation.

D24 IS UNCHANGED and V17 is correct as written. D24 fixes the exception CLASS for a missing binding and
says nothing about message text, so V17 asserting `IntegrityError` plus path coverage is the whole
obligation. New message text is free.

X32 IS ACCEPTED as an obligation and BOUNDED: a binding MISSING beyond `function_report`'s
10,000-row detail cap must still raise `IntegrityError`, because the pending count statement proves
binding EXISTENCE over the unbounded partition and D22's exact counts are computed there. "The cap
bounds RETURNED DETAIL, never validation" is WITHDRAWN as written; validation splits three ways.
EXISTENCE is unbounded. CROSS-FIELD consistency (`requests.proposal_id` against the proposal id, and
every other request-to-proposal scalar) and JSON CONTENT hold for RETURNED DETAIL alone, at each
consumer's own position - hoisting either into the adapter would pre-empt `_validate_proposal_shape`
and rewrite the class, message and precedence every corrupt ledger reports. A present-but-mismatched
binding in the unreturned tail therefore returns a report; `docs/architecture.md` publishes that
bound, and the singular reads, the feed, review and `reconstruct_function_receipt` each validate the
row they materialize. The battery owns both fixtures.

X26 IS ANSWERED BY THE D01 AND D02 AMENDMENTS TOGETHER: D02's SQL-owner equality is measured
lexically, so section 12's SQL-free singular wrapper is not an owner and the two do not conflict.

D10 IS SCOPED TO THE EVENTS THE OWNED SITES EMIT, and X15 IS FALSIFIED BY THE SHIPPED CODE. X15 claims
`proposal.created` carries `payload={}` on all three creation routes; measured in `system.py`, the two
direct routes emit `payload={}` (line 880) and the `handle` route emits
`payload={"request_id": request_id}` (line 1262). V22's "no proposal or review event payload contains
a request_id key" is therefore over-broad, and a battery encoding it literally goes RED against
correct code.

RULING: M3.4's event obligation covers the events its EIGHT OWNED SITES emit - the review-path
transitions and the direct-route `proposal.created`. Measured and request-free:
`proposal.rejected` `{reviewer}`, `proposal.accepted` / `proposal.corrected`
`{example_id, receipt_hash, reviewer, suspended_artifact_ids}`, `artifact.counterexample`
`{example_id, proposal_id}`, direct `proposal.created` `{}`. The `handle` route's `proposal.created`
KEEPS its `request_id` under the same handle-lifecycle exception D10 already grants the lifecycle
models: `handle` is not an owned site, M3.5b removes its grammar and M3.6a deletes the method.
Stripping it here edits a method this unit does not own and destroys the only audit link between a
request and its proposal while the request lifecycle is still public. The battery asserts the six
payloads above and asserts the `handle` payload UNCHANGED, so the exception is pinned rather than
merely tolerated.

## 15. S2 CORRECTIONS — grounds the contract attack falsified, and the claims that narrow

`m3u4-attack.json` (24 lenses, 18 seeded + 6 extension) attacked the S2 rulings themselves. Section
14 answered the obligations that could not be read literally; this section corrects claims that were
WRONG. A ruling can survive while one of its stated grounds does not, and a reader who inherits the
false ground reasons from it later.

THE D22 MATERIALIZATION GROUND IS WITHDRAWN. Section 12 said ALT-PROJECTION's `function_report` wraps
the constant in a subquery and materializes the whole partition before filtering by operation.
MEASURED, THAT IS FALSE. Both shapes were run through `EXPLAIN QUERY PLAN` on the shipped schema
under SQLite 3.53.1, and the plans are IDENTICAL:

```
SEARCH r USING INDEX requests_scope (partition=? AND operation=?)
SEARCH p USING INDEX sqlite_autoindex_proposals_3 (partition=? AND request_id=?)
USE TEMP B-TREE FOR ORDER BY
```

SQLite flattens the wrapper and pushes the operation predicate down into `requests_scope`. The outer
`WHERE binding_operation = ?` additionally strength-reduces the spike's LEFT JOIN to an inner join on
this path. FORK 1'S RULING IS UNCHANGED, because it never depended on this ground: ALT-PROJECTION
fails D03 with two raw `UPDATE requests` left in `review`, which a read-only SQL constant cannot
confine, and its LEFT JOIN changes orphan visibility under D12. That third ground is now SHARPER, not
weaker - strength reduction applies only where the outer query constrains the right table, so the
singular read path keeps the LEFT JOIN and returns an orphan proposal with NULL binding columns
instead of failing closed. NEVER ASSERT A QUERY PLAN WITHOUT RUNNING `EXPLAIN QUERY PLAN`; a subquery
is not a materialization.

Z50 IS A COUPLING CENSUS, NOT A PERFORMED SWAP. Z50 established that all six consumer `WHERE` clauses
name `p.` columns or the constant's own `binding_*` aliases and never `r.`, so an M3.6b rewrite of the
join touches no consumer. It did NOT perform a v3 schema swap, and no artifact contains one. The
ruling's claim is exactly the census: consumers are not coupled to the join's shape. "The adapter
survives the swap untouched" is a PREDICTION this unit does not verify, and M3.6b owns its proof.

SECTION 1'S "NO CONSUMER LOSES INFORMATION" IS NARROWED. Public consumers plainly do lose access:
accept and correct results lose `request_id`, `source` and `artifact_id`, proposal readers lose
`request_id`, and `status` changes value. The true claim is that NO STORED SCHEMA OR ROW INFORMATION
IS DELETED - schema v2 keeps every byte, and the cut happens once at M3.6b. The public losses are
intentional and enumerated here.

D12'S BYTE-IDENTITY RULE EXEMPTS `status`, EXPLICITLY. D12 requires every remaining projected value to
keep its baseline value; section 13 keeps `status` while CHANGING it from `resolved` to
`accepted`/`corrected`. Both cannot hold silently. The exemption is named and bounded: `status` alone
is transformed, with grounds in section 13, and every other kept value stays byte-identical.

D24'S "FABRICATED ONLY" PREMISE IS FALSE, and two real-ledger paths disprove it. (1) Malformed JSON:
a supported pending proposal whose TEXT `input_json` is rewritten to malformed JSON is a schema-valid
STRICT row, and `parse_json` raises `ValidationError`, which subclasses `ValueError`, straight out of
a real ledger. (2) Legitimately NULL columns: `final_output_json`, `final_output_hash`, `reviewer`,
`review_note` and `reviewed_at_us` are nullable by schema, so a mutant dropping a `None` guard yields
a raw `TypeError` from a real ledger. D24 must therefore ENUMERATE nullable versus non-null converted
fields, translate real-ledger malformed JSON to `IntegrityError` on all five paths, and reserve the
word "fabricated" for proxy-injected storage classes alone.

D22'S TAIL IS COUNTED, NOT REACHABLE, AND ITS VALIDATION IS EXISTENCE ALONE. The API exposes no cursor
past `projection_limit`, which is itself capped at 10,000, so row 10,001 is observable only through
`pending_proposal_count`. The obligation is that the tail CONTRIBUTES TO THE EXACT COUNT and that every
tail binding EXISTS (section 14, X32), never that a caller can read the row or that its content and
cross-field consistency are checked.

TWO FINDINGS CLOSED IN CODE THIS SESSION. `slots=True` was unpinned - turning it off keeps the
constructor signature and resolved hints identical and only adds `__dict__` - so the shape test now
asserts `__slots__` presence and `__dict__` absence on all three shapes. README published the new
`accepted`/`corrected` vocabulary without saying the handle lifecycle still reports `resolved`, which
made the prose read as a system-wide rename; README now contrasts the two vocabularies and states
that Cement translates neither into the other.

FIVE TEXT DEFECTS STAND CORRECTED. D03's permitted delta must EXCLUDE `_proposal_binding` (section 14
rules attribution lexical, and the wrapper owns no SQL). D13 assigns the `request_id` deletion to
`_proposal_record` ALONE, because `_proposal_content` never carried one and its only permitted change
is its argument source. D16's "unchanged bounds" publishes its numbers: reviewer nonempty,
control-free, at most 256 UTF-8 bytes; note empty-allowed, control-free, at most 2048 bytes; one
shared `now` across every provenance edge. The exact CLI triples in section 13 and the schema freeze
in section 1 are OBLIGATIONS, not commentary, and the S3 battery owns one test each - an unnumbered
contract paragraph is invisible to a one-test-per-obligation battery.

THE CONTRACT CARRIES PROVENANCE IT SHOULD NOT. Sections 12 and 13 retain wave chronology, dispatch
history and worktree state, which the project's authoring rule excludes from durable artifacts and
which competes with the binding obligations for a reader's attention. The narrative moves to
`.agent/archive/` at milestone close; the obligations stay.
