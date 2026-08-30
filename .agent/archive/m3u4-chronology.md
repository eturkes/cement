# M3.4 chronology — wave history, dispatch record, spike trees

Provenance moved out of `.agent/decisions/m3u4-contract.md` at M3.4 closure (review finding R15). The
contract keeps every ruled obligation, the grounds needed to read it, and every measured number. This
file keeps the history that produced them: how the waves ran, what each dispatch cost, and where the
spike trees live. Nothing here is binding. A later unit that needs a M3.4 ruling reads the contract;
a later unit that needs to know how a ruling was reached reads this.

POINTER LIFETIME. The two spike trees are LOCAL-ONLY annotated tags (`m3u4-alt-binding` = `aa77d9f`,
`m3u4-alt-projection` = `cb0ef3e`, plus `m3u4-map`, `m3u4-verdicts-wave2`, `m3u4-attack-wave2`).
`origin` carries no tags, and the commits are unreachable from `main`, so every clone resolves none of
them and a `git gc --prune` on this workstation can drop them. Each ruling's grounds are restated as
measured facts inside the contract for exactly that reason; treat the tags as evidence that expires,
never as the substance behind a claim.

## Sizing — how the one-unit ruling was measured

The M3 plan draft estimated `260 prod / 240 test` and set a pre-open split trigger at "a query diff
above 320 production lines". The plan review's own L7 rejects that trigger as not pre-open
measurable. MAIN therefore deleted the surface and let the gate produce the work list, which is the
standing rule after a token census mispredicted M3.1's break set.

Harness `.agent/decisions/m3u4-burden.py`, results `m3u4-burden.json`, three staged gate runs against
fresh worktrees at `da63741`. Per-stage failure attribution:

- stage 1, drop the two `request_id` fields only: 252 broken of 744, standing behind THREE frames —
  `system.py:1316` in `get_proposal` 227, `system.py:2676` in `_pending_proposal_gap_from_row` 24, and
  one shape test.
- stage 2, plus the three production sites repaired (the `ProposalView` keyword, the
  `_proposal_record` dict entry, the `PendingProposalGap` keyword): 9 broken across 9 frames. 243 of
  stage 1's failures were a production cascade from two constructors, never test burden.
- stage 3, plus `review` returning `ReviewResult`: 112 broken across 13 frames, 100 of them behind ONE
  shared fixture helper, `tests/test_cli.py:245` in `confirm`.

The 252-versus-9 gap is why the measurement exists: a break COUNT is not a work list until its shared
frames are factored out, and the two numbers differ by 28x. The draft's `260 prod / 240 test` stayed
labelled an ESTIMATE and never crossed into the contract as a measurement.

## Fork 1 — wave-1 outcome, and the dispatch defect that delayed it

WAVE 1 DID NOT RULE THE FORK, and the cause was MAIN's dispatch rather than either teammate. Both
spikes filled all 14 probe rows and both reported `adapter_present=False` on every one: they answered
the whole corpus against BASELINE, exactly as the brief ordered ("fill the graded artifact first,
implementation second"). Thirteen of the fourteen probes MAIN wrote were answerable without an
implementation, so the graded metric reached zero while measuring only the status quo. Neither `Z50`
row was ever added.

DISPATCH CORRECTION, binding on every future spike: a probe corpus answerable against baseline does
not force an implementation. Write each probe as a DELTA requiring both sides, or make the
implementation a separately graded deliverable the validator can see. Both spikes built their
alternative AFTER one flush directive re-ordered their work, so the defect delayed the implementations
rather than preventing them.

WHAT WAVE 1 STILL BOUGHT:

- `m3u4-spike-binding.json` and `m3u4-spike-projection.json` are a thorough BASELINE census. Section 9
  of the contract and the battery consume it: exact SQL statement counts per read path, the collider
  matrix, middle-and-last corruption classes, the `.review(` call-site census (30 total: 24 tests, 5
  examples, 1 production), the `PendingProposalGap` dependent-site split, and the verbatim CLI JSON for
  all three decisions.
- `m3u4-alt-binding` (`aa77d9f`) carries a real ALT-BINDING implementation, +433/-147 across
  `system.py`, `models.py` and `__init__.py`, adding `_ProposalBinding`, `_ProposalBindingSet`,
  `_proposal_binding`, a BATCH `_proposal_bindings` answering the N+1 exposure, and
  `_write_proposal_request_status`. Its own table never measured it; the diff is the evidence.
- `m3u4-alt-projection` (`cb0ef3e`) carries a real ALT-PROJECTION implementation, +181/-117, adding
  `_PROPOSAL_BINDING_SQL`, a `_ProposalBinding` record and a `_proposal_binding(row)` validator. It was
  uncommitted when `TaskStop` landed and was preserved by the close order's per-worktree status read.

FIRST COMPARABLE NUMBER, +181/-117 against +433/-147 for the same eight sites, favoured
ALT-PROJECTION. It is a size measurement from two trees of unequal maturity and it settled nothing;
`Z50` remained the deciding criterion, and the S2 ruling then went against the smaller diff.

TAG ANNOTATION CORRECTED AT CLOSURE. `m3u4-alt-projection` was annotated with the `function_report`
materialization ground, which contract section 15 WITHDRAWS after `EXPLAIN QUERY PLAN` on SQLite
3.53.1 returned identical plans for both shapes. The tag was rewritten (old object `c9e31e9`) to state
the two surviving grounds and to name the withdrawal, because a corrected claim that survives in an
un-grepped surface is exactly the defect this project keeps paying for.

## Fork 2 — wave-1 outcome

NOT RULED at wave 1, same cause as fork 1. The baseline evidence needed to rule it did land: both
spike artifacts record under `P08` the verbatim CLI JSON emitted for accept, correct and reject, plus
the return classes and exit codes. `m3u4-alt-binding` had already committed a concrete `ReviewResult`,
and MAIN ruled the field set at S2 against that payload rather than against the draft's prescription.
Both spikes shipped R1; R1 was rejected on D12.

## Wave 2 — the two tables and the validator that expired mid-wave

`m3u4-verdicts.json` = 57 rows, 22 seeded + 35 extension. `m3u4-attack.json` = 39 lenses, 18 seeded +
21 extension. Extensions outnumbered seeds in both, which is the seeding format working rather than
scope drift.

The wave-2 validator's `SECTION` regex accepted `D<nn>` ids only. MAIN then appended contract sections
12 and 13, so both teammates hit `INVALID` on legitimate citations and neither could reach a clean
grade. Two grammar widenings failed before the right move: pull the CENSUS of all 77 distinct values
and check the two things a pointer can be checked for — it resolves somewhere, and it stays under 60
characters. A validator seeded before its contract grew expires; re-grade both ways after any
validator edit, because the seed credential dies with it.

## S3 — the battery wave

Instruments: 42 probes, 44 mutants, 18 review lenses, all grading PASS with zero unknown cells.

THE DIFFERENTIAL FOUND THE UNIT'S FOURTH CODE DEFECT. An existing proposal whose private request row
was deleted hid behind the inner join, so all four read paths reported `NotFoundError`. No reviewer
lens caught it because the four paths AGREED WITH EACH OTHER; agreement among sibling paths is not
evidence, and only an implementation built to the contract rather than to MAIN's code disagreed.

TWO MUTATION-HARNESS DEFECTS, both aborting rather than reporting. Stale anchors: two fixes rewrote
the statements six mutants target, and the first `ANCHOR-MISS` aborted the campaign, hiding 35 later
verdicts. A naive whole-string census said 10 stale and was wrong — multi-patch mutants join sections
with `---`, and loading the harness's own `MUTANTS` gave 6 mutants over 12 patches. Two of the six
INVERT rather than move, because the shipped code is now what they used to mutate INTO. Second defect:
`first_failure` matched only the docstring-free one-line verbose record, so a mutant whose only
witnesses were battery tests raised `VERDICT-FAIL-WITHOUT-TEST` and aborted. The summary header
`FAIL: name (tests.M.C.name)` is authoritative instead, surviving both a docstring and a subtest.

VERDICT MODULES DECIDE A SURVIVOR COUNT. The 3-module campaign reported 35 killed / 9 survivors; the
decisive 4-module campaign reports 40 killed / 4 survivors over the same corpus. A prescribed killer
is a PRESCRIPTION and only the module-set verdict is a measurement.

## Session record

| session | scope | `main=` | peak `mate=` |
|---|---|---|---|
| S1 | wave 1 + acceptance contract | 84% 203K/240K | 70% 168K/240K (`spike-m3u4-binding`) |
| S2 | fork rulings + implementation + wave 2 | 98% 236K/240K | 85% 205K/240K (`rev-m3u4-1`) |
| S3 | battery, differential, mutation campaign, review | 76% 183K/240K | 100% 240K/240K (`test-m3u4-2`) |
| S4 | R15 archive split, gate reruns, closure | recorded in the roadmap | — |

GATE MOVEMENT across the unit: 744 tests in about 175 s at `da63741`, 753 after the implementation,
755 and 756 across the S3 fixes, 811 in about 181 s at closure. The contract carries the opening and
closing figures; the interior readings are here.

ONE BASH WORKING DIRECTORY IS SHARED BY MAIN AND EVERY TEAMMATE. MAIN `cd`-ed into its own measurement
worktree during S1 and silently moved all three teammates' shells; one spike caught it and invalidated
a batch of measurements. Anchors and line numbers taken that way look valid and resolve to the wrong
bytes. Every located command runs as `(cd <path> && ...)` in a subshell or through `git -C`, and every
brief carries a mandatory per-call `cd <worktree> &&` prefix.
