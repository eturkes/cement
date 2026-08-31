# M3.5a acceptance contract — `resolve` and `proposal submit` CLI channels

Unit: M3.5a, tier `kernel`, tags `-`, depends M3.2b + M3.4. Base `4783eed`.
Sessions: S1 wave 1 (DONE, `773959f` + `07c295d`), **S2 fork rulings + this contract**,
S3 implementation, S4 battery + closure.

Sections 1-12 are binding on every downstream artifact. Sections 13-14 are PENDING and are
filled by S3's wave-2 tables under an idempotent patcher.

Inputs, all tracked and re-derivable from committed state:

- `m3u5a-map.json` — 55 rows (25 seeded + 30 extension), `UNKNOWN-CELLS 0`, `ANCHORS-BAD 0`.
  Graded by `m3u5a-wave1-validate.py`. **A grade proves each anchor resolves and each cell is
  filled; it never proves a finding true.** The six findings this contract asserts as fact were
  re-derived by MAIN in `m3u5a-s2-probe.py`; every other map row is attention-directing.
- `m3u5a-spike-envelope.json` (32 rows, `+97/-3`) + `m3u5a-alt-envelope.patch` +
  `m3u5a-envelope-probes.py`.
- `m3u5a-spike-flags.json` (24 rows, `+23/-1`) + `m3u5a-alt-flags.patch` +
  `m3u5a-flags-probes.py`.
- `m3u5a-s2-probe.py` — MAIN's own re-derivation, section 2.

## 1. Scope

Two channels are added. Nothing is removed: M3.5b owns `handle`/`request`/source grammar and
every legacy-prose deletion, so this unit's acceptance asserts **preservation plus no new source
reach**, never legacy-grammar failure (`X05`).

- Root leaf `resolve OPERATION --input VALUE [--expected-function-hash DIGEST]` → `System.resolve`.
- Leaf `proposal submit OPERATION --submission VALUE` → `System.submit_proposal`.

Out of scope, named so no downstream artifact reads them as gaps: schema stays v2 and `store.py`
stays byte-identical (M3.6b owns the cut); the private request row a submission still writes stays
(`X23`); `CommandCandidateSource` stays imported (`X23`, `M23`); root help keeps describing
supervised fallback (`X20`, `Y09`) because the lifecycle it describes is still shipped.

## 2. Ground facts — MAIN's own re-derivation

`uv run python .agent/decisions/m3u5a-s2-probe.py` answers six probes. Every number below is
its output at `4783eed`; a changed answer is a contract defect, not a test failure.

| Probe | Result | Consumed by |
| --- | --- | --- |
| `System(<absent path>)` | `exists_before=false` → `exists_after=true`, **208,896 bytes** | D13 |
| `resolve` after ledger deletion | `IntegrityError("ledger file is missing or unreadable")`, path stays absent | D13 |
| parser census | **28 leaves / 35 nodes** | D25 |
| abbreviation | root `--part`→`--partition` ACCEPTED; nested `function eval --bun`/`--in` ACCEPTED | D01, D14, section 11 |
| `_emit("prop_probe")` | `"prop_probe"\n` — a bare JSON string | D20 |
| provenance cap in `system.py` | **3 unexported `65_536` literals**, no named constant | D16 |

## 3. FORK 1 — the submission channel (RULED)

**RULING: the aggregate envelope, with `@PATH` removed and its cap derived rather than copied.
Neither spike as written.**

Ruled from the two tracked patches, per the M3.4 measured rule that a spike's shipped diff carries
defects its own table never measured. Both tables graded clean; the flags advocate additionally
ruled against its own alternative, which under the council rule closes the fork — but the grounds
below are the diffs and the probes, never the recommendation.

### 3.1 Grounds for the envelope core

**G1 — CAPACITY. The flags defect is unconditional and has no relief; the envelope's is
conditional on a form the operator chooses.** Both spikes measured the identical kernel wall:
real `execve` launches 131,071 argument bytes and refuses 131,072 with `E2BIG` (`Z17`, both
tables). Only ONE field can leave argv through stdin, because the second `_input("-")` reads a
drained stream and raises `invalid JSON: Expecting value: line 1 column 1 (char 0)` (`Z09`, `Y02`,
`X27`). So a flags submission can never carry more than one of three fields at the library's
1,048,576-byte contract, under any invocation. One `--submission -` frame carries all three at
their maxima, measured accepting exactly **2,162,722 bytes** and rejecting one byte more (`Z11`,
`Z12`). Standing rubric: prefer the alternative whose defect is CONDITIONAL on a regime the loser
cannot improve.

**G2 — DISCLOSURE.** Every flags field is visible in `/proc/<pid>/cmdline` (`Y01`). Combined with
G1's one-stdin-field limit, at least two of three candidate fields are ALWAYS world-readable in
process listings and shell history. The envelope exposes zero fields under `-` and the same
fields under inline text, so the exposure is again conditional where the rival's is structural.

**G3 — DUPLICATE REJECTION ON A WRITE.** Strict aggregate parsing raises
`duplicate JSON object key: 'input'` before object construction (`Y05`); repeated flags are
argparse last-wins, silently (`Z16`). Shipped precedent pins last-wins for `function eval`
(`X10`) — a read. A leaf that commits a candidate to the ledger earns the strict reading, because
last-wins records a candidate the operator did not name.

Counterweights, recorded rather than dismissed: the envelope is `+97/-3` against `+23/-1` and adds
a reader; flags map one-to-one onto `submit_proposal`'s three arguments (`Y04`) and inherit
`_input`'s three error families free (`Z04`); argparse supplies exact field-local omission text
(`Z03`) that the envelope must produce itself (`Y04` measures that it does).

### 3.2 Deltas from the shipped envelope patch

**D-A — `@PATH` IS REMOVED.** `Y06` measured it adding three failure modes, one coupled to
Python's OS-derived missing-path wording. `X26` measured the only shipped CLI file reader,
`_read_function_bundle`, as descriptor-hardened: `O_RDONLY|O_NONBLOCK`, `fstat` regular-file
grading, bounded `max+1` read, strict UTF-8. The patch instead opens `pathlib.Path(value[1:])`
directly and inherits none of it, so a FIFO blocks and a directory answers through OS wording.
The channel loses no capability: `--submission -` already carries the full cap, and
`cement proposal submit OP --submission - < file` is the file route.

**D-B — THE CAP IS DERIVED FROM A NAMED CONSTANT.** The patch writes a fourth copy of the
provenance limit into `cli.py`, against three unexported copies already in `system.py` (section 2)
— the cross-module invariant `Y10` names. `system.py` gains `PROVENANCE_MAX_BYTES = 65_536`, used
at all three existing sites; `cli.py` imports it and derives the aggregate cap. This is the whole
production change outside the two new leaves.

**D-C — `allow_abbrev=False` IS SCOPED TO THE TWO NEW NODES.** Abbreviation is live at the root
and on nested leaves (section 2), so `M16`'s bearing is measured true — but disabling it globally
changes shipped grammar (`--part` stops resolving) outside this unit's mandate, and the weakness
bites on REMOVAL predicates, which M3.5b owns. Both new leaves carry `allow_abbrev=False`; the
global decision is deferred with its evidence (section 11).

## 4. FORK 2 — the `resolve` payload (RULED)

**RULING: one fixed seven-key set across all three resolve states, with `null` carrying the
distinctions.**

Ruled against the shipped exit-6 stdout precedents rather than against the plan draft, whose
vocabulary `X30` measured as belonging to no model: `function eval` emits a fixed
`{artifact_hash, function_hash, matched, output}` on both branches, `function verify` a fixed
`{passed, entries, function_hash, checks}` on both, `verify-drafts` a fixed dataclass on both
(`M20`). A per-state key set would be this CLI's first varying payload.

Naming follows the sibling that projects the same object: the draft's `verified` is rejected for
**`passed`**, which is `FunctionVerification`'s own field name and `function verify`'s own key, so
one concept keeps one name across two leaves.

`checks` ships on success too. Resolve's cost IS a full verification, and the ordered check vector
is the evidence that the verification happened; `function verify` already ships it on both
branches.

`--expected-function-hash` IS exposed, widening the draft's stated grammar (`X15`). Grounds: it is
the only single-snapshot route to a pinned deterministic resolution, since the workaround —
`function verify --expected-function-hash` then `resolve` — costs a second full verification
(~36.5 s at the 50,000 cap) and opens a gap between two snapshots that `System.resolve`'s own
docstring names; the library already validates it in a pinned order (`X16`) so the CLI adds no
vocabulary; and three shipped leaves already carry that exact spelling, so terminology stays fixed.

`resolve` is a ROOT leaf, not `function resolve`. Considered and rejected: the `function` group
holds its two nearest siblings and the shared flag. Ruled root because the `function` group
administers the function object while `resolve` is the product's operating verb — README paragraph
1's deterministic answer path — and because the census delta both wave-1 artifacts predict is one
root choice plus one proposal child (`X20`, `M17`).

## 5. D01-D06 — the `resolve` leaf

- **D01** Grammar is exactly one positional `operation`, one required `--input`, one optional
  `--expected-function-hash` defaulting to `None`. The node sets `allow_abbrev=False`, so `--in`,
  `--exp` and every other prefix is `unrecognized arguments` rather than a silent alias.
- **D02** `--input` accepts inline JSON text or `-` through the shipped `_input`, inheriting its
  1,048,576-byte bound and its three exact failure families (`M07`, `M24`). Resolve adds no reader.
- **D03** Dispatch calls `System.resolve` exactly once and reaches no candidate source: zero
  `_source` calls, zero `System.propose` calls, zero `CandidateSource` calls even when one is
  configured (`X19`, `X22`).
- **D04** The `--db` and `--partition` gates keep their shipped order and text and run before any
  resolve work (`X28`). `resolve` is ledger-backed, so it is never hoisted ahead of them the way
  `function eval` is.
- **D05** `--expected-function-hash` is forwarded verbatim to the library keyword. Its validation,
  and the whole `partition → operation → expected hash → input` precedence, stay library-owned
  (`M09`, `X16`); the CLI re-implements none of it.
- **D06** One `Store.transaction(write=False)` is opened per invocation and no ledger byte, event,
  clock read or ID allocation occurs (`X19`).

## 6. D07-D13 — the `resolve` payload and exit contract

- **D07** The payload key set is exactly, and identically in all three states,
  `{artifact_hash, checks, entries, function_hash, matched, output, passed}`. `_emit` sorts keys,
  so that list is also the emitted order.
- **D08** `passed` ← `verification.passed`; `entries` ← `verification.entries`;
  `function_hash` ← `verification.function_hash`, which survives a failed verdict as a diagnostic
  (`M14`); `checks` ← the ordered `[{key, passed, detail}]` projection `function verify` already
  ships.
- **D09** `matched`, `output` and `artifact_hash` project `FunctionMatch`, and are `null` when
  `match is None`. **Over every value `System.resolve` returns** — the domain is named because
  `FunctionResolution` enforces no invariant on a hand-built value (`M13`) — `matched is null` iff
  `passed is false`. A verified miss is therefore `matched: false`, never `null`, and a failed
  verdict is `matched: null`, never `false`. The three states stay distinguishable from the payload
  alone, which is what a shared exit 6 requires.
- **D10** Status is `0` iff `matched is true`, else `6`. Both negative states use one JSON
  `_Outcome` on **stdout**, following the three shipped stdout precedents and never `function
  export`'s exceptional `_Unverified` stderr channel (`M20`, `M04`).
- **D11** `verification.document` never reaches stdout. D07's closed key set is the structural pin;
  no `asdict` of a verification or resolution is emitted (`M02`, `M03`, `M14`).
- **D12** Raised classes keep their shipped map through `main`, unchanged and untouched by this
  unit: `ValidationError`/`CementError` → 2, `NotFoundError` → 3, `ConflictError`/`StateError` → 4,
  `IntegrityError` → 5 (`M04`). An unregistered operation is 3; an empty promoted set is NOT — it
  is the ordinary verified miss at 6 (`X14`), and so is a revised operation whose artifacts retired
  (`X18`).
- **D13** A `--db` path that does not exist answers `IntegrityError` →
  `{"error":"integrity","message":"ledger file is missing or unreadable"}` on stderr at **5**, and
  **creates no file**. This is a resolve-only pre-construction check placed between the
  `--partition` gate and `System(...)`, forwarding the library's own verdict for the same
  condition (section 2) rather than inventing vocabulary. Stated honestly and pinned as written:
  it is a check, not a read-only construction mode; the residual race is that a path deleted
  between check and construction is still recreated by `Store`, which is exactly the shipped
  behaviour, so the check strictly improves and never worsens. `X02`'s full answer — a public
  existing-only construction mode — is out of scope and deferred (section 11).
  This check is also what makes D04's ordering safe: on an absent ledger nothing is constructed, so
  a malformed `--input` rejected after construction can only ever touch a ledger that already
  existed.

## 7. D14-D19 — the `proposal submit` leaf

- **D14** Grammar is exactly one positional `operation` and one required `--submission`, with
  `allow_abbrev=False`, so `--sub` is `unrecognized arguments` and `proposal sub` is an invalid
  choice (`Y07`).
- **D15** `--submission` accepts inline JSON text or `-` for one aggregate stdin frame. There is no
  `@PATH` (section 3.2 D-A) and no per-field flag; `-` reads at most `cap + 1` bytes and
  distinguishes read failure, oversize and invalid UTF-8, mirroring `_input`'s three families with
  submission-specific wording.
- **D16** The aggregate cap is `2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + framing` =
  **2,162,722 bytes**, where `PROVENANCE_MAX_BYTES` is newly exported from `system.py` and used at
  its three existing literal sites. No limit is copied. The cap is a TRANSPORT bound that must
  admit every submission the library accepts; it replaces no field validation (`Z13`, `X12`).
- **D17** Validation order is: strict `parse_json` under the aggregate byte, depth and item maxima
  (`X08` — depth `DEFAULT_MAX_DEPTH + 1`, items `3 * DEFAULT_MAX_ITEMS + 3`) → top-level object
  type → unknown keys → missing required keys → the library call. Duplicate members therefore fail
  inside the parser, before any exact-key check can collapse them (`X09`, `Y05`).
- **D18** `input` and `output` are required; `provenance` is optional and defaults to `{}`, which
  is a durable empty mapping (`Z06`). Unknown keys and missing keys each name every offending key,
  sorted. Every one of these is exit 2 on stderr before any transaction opens (`X11`).
- **D19** Dispatch builds `Candidate(output=..., provenance=...)` from the envelope and passes the
  envelope's `input` as the library's third positional (`M10`, `M12`, `X21`). Provenance shape stays
  library-graded: a non-mapping provenance is `candidate provenance must be a mapping` at exit 2
  (`Z07`), and no CLI-only coercion is added.

## 8. D20-D26 — the `proposal submit` payload, exit contract and invariants

- **D20** Success emits exactly `{"proposal_id": "<id>"}` at status 0 — one key. The bare string
  `submit_proposal` returns is NOT emitted directly, because `_emit` renders it as a bare JSON
  string with no key to bind (section 2). The flags patch's `"status": "review_required"` is
  REJECTED: it is a constant, not a measurement — every successful submission is pending by
  construction — so it advertises a variability the API does not have.
- **D21** No candidate byte is echoed. The acknowledgement carries no request identity, and the one
  `proposal.created` event's payload stays exactly `{}` (`Z18`, `M25`).
- **D22** Exit classes: parser, envelope and field-validation failures → 2; unregistered operation
  → 3 with zero rows written (`Z14`); `ConflictError`/`StateError` → 4; `IntegrityError` → 5.
- **D23** There is no idempotency. Two byte-identical submissions return two distinct ids and add
  two requests, two proposals and two events (`X13`). No help text, message or doc sentence may
  advise retry; the recovery route for the M3.3 commit window is pending-proposal ENUMERATION
  (`X24`).
- **D24** Zero `_source` calls, zero `System.propose` calls, and zero source calls even when a
  configured source would raise (`Y01` envelope, `X22`). This is the unit's headline isolation
  predicate: the core CLI gains a write channel and no candidate-source reach.
- **D25** The parser census moves **28 → 30 leaves and 35 → 37 nodes**, derived inside the test from
  `_parser()` and never transcribed (`M17`, section 2). All 28 existing leaf paths keep their
  names. Option abbreviation elsewhere is unchanged, which the same census-derived test asserts by
  leaving root and nested behaviour as section 2 measured it.
- **D26** Preserved and asserted independently: `store.py` byte-identical at `SCHEMA_VERSION` 2;
  a successful direct submission's three-row footprint (one request, one proposal, one event)
  (`X23`); `CommandCandidateSource` still imported (`M23`); cross-leaf option isolation in both
  directions for both new leaves, including that `--expected-function-hash` stays off
  `proposal submit` and `--submission` stays off every other leaf (`X15`, `X25`).

## 9. D27 — the B02 tripwire (RULED)

`tests/test_submission_battery.py:171` `test_b02_...` asserts byte equality against git object
`f9b9755` for three files, one of them `src/cement_runtime/cli.py`. Both S1 spike worktrees
therefore ran the gate at 810 passed / 1 failed, on exactly that pin and nothing else. **M3.5a
edits that file by definition**, so this unit dispositions the pin rather than discovering it.

- **D27** B02 drops `cli.py` from its frozen tuple and keeps `_command_supervisor.py` and
  `example_adapter.py` frozen at `f9b9755`, which stay correct until M3.7 relocates them. The
  retired member is not deleted silently: the property it carried — M3.3 added no CLI channel and
  no CLI source reach — is exactly what this unit retires, and it MIGRATES to D24 (zero `_source`,
  `System.propose` and source calls), D25 (the census-derived 28→30 / 35→37 delta with all 28
  existing leaf paths unchanged) and D26 (cross-leaf option isolation), which are strictly stronger
  because they constrain what the new bytes may be rather than that there are none. B02's docstring
  states where the property went, so a reader of the surviving pin can find it.

Re-pinning `cli.py` to a fresh baseline is REJECTED: the roadmap schedules M3.5b to edit the same
file again, so a per-unit re-pin passes at the moment it is written and reports its next scheduled
break as a defect. A pin the plan already commits to breaking is noise, not a tripwire.

Every S3 brief names B02 as a TRIPWIRE the unit is expected to update deliberately. Standing rule:
a brief that forbids gate edits without naming its tripwires pushes the cost into production code.

## 10. D28-D30 — publication

- **D28** Both commands are named POSITIVELY in operator-facing prose. `X21`'s census found zero
  literal submit grammars, zero `System.resolve` mentions and zero root `resolve` commands across
  `README.md`, `docs/architecture.md`, `docs/adapter-protocol.md` and `docs/threat-model.md`, so
  there is no stale text to refresh and a "no sentence is falsified" test passes vacuously. A
  reader must learn from prose alone: that both commands exist, their grammar, their payload keys,
  their exit classes, that submission is not idempotent, and that resolve writes nothing.
  Mechanical test: grep both command spellings across README and every normative doc.
- **D29** Every placeholder in a shipped command block has a producing command earlier in the same
  block, and the human-facing register follows the project's ASD-STE100 rules.
- **D30** Resolve's cost is published where an operator meets it: one resolve runs the full
  six-check verification and costs what `verify_function` costs. Cite
  `m3u2b-resolve-bench.json`'s own `resolve_cold_hit_ms`, measured end to end through the shipped
  method — 36,452 ms and 985,696 KiB peak RSS at the 50,000-entry cap, 613 ms at 1,000, 5.7 ms at
  one — matching the method docstring's `~36.5 s` and `~963 MiB`. Any prose figure is DERIVED from
  that artifact at the precision it states, never transcribed, so a re-measurement moves prose and
  artifact together or fails loudly. No help or doc sentence may call resolve fast, cheap or cached
  on the grounds that it is read-only.

## 11. Gate identity

Closure is MECHANICAL, never a green suite (project rule; a removal-adjacent unit's gate stays
green when a behaviour and its pin vanish together).

1. `uv run python -m unittest discover -s tests -t .` — full suite, zero failures, zero errors.
   Baseline at `4783eed` is 811 tests, of which B02 is red for every tree that edits `cli.py` until
   D27 lands, so S3 opens by dispositioning it rather than by reading 810/1 as a regression.
2. A diff-blind obligation battery, one test per obligation D01-D30, in
   `tests/test_cli_channels_battery.py`, graded by `m3u5a-battery-validate.py`
   (`--emit-stub` = the seed's single source of truth). `UNFILLED-TESTS 0` and
   `OBLIGATIONS-UNCOVERED 0` are both required, and so are `ASSERTIONLESS 0` and `SKIPPED 0`:
   a covered-but-empty body and a `skipTest` body both satisfy a coverage count while asserting
   nothing, which is the cheapest way to turn this gate vacuous. The phase-2 suite validator
   `m3u5a-suite-validate.py` already carries the `ASSERTIONLESS` half and is the pattern to copy.
3. A mutation sweep over every predicate the two leaves add — the payload projections, the status
   selectors, the envelope validators, the ledger precheck — reporting **its verdict module list on
   the control line**, with the acceptance predicate written as the NAMED SURVIVOR SET rather than
   "zero survivors", so a survivor outside that set fails while ruled ones do not. The UNMUTATED
   control run must be reported GREEN on the same control line: without it a sweep whose harness is
   broken reports every mutant killed and passes, which is the same vacuity gate 4 was carrying.
4. `uv run python .agent/decisions/m3u5a-s2-probe.py` — section 2's **seven** ground probes, graded
   against **19 pinned facts**, exit 1 on any mismatch. Re-anchored at S3: the probe previously
   printed its findings and returned 0 unconditionally, so it could not fail, and its pins as
   written contradicted this unit's own obligations. Two pins now carry POST-implementation
   values — `parser_census` at 30 leaves / 37 nodes and `provenance_literal` at one declaration
   site with `exported_constant` true — because D25 and D16 move them by design. `parser_census`
   is additionally graded by NAME: all 28 `c8b82cd` leaf paths survive and the added set is exactly
   `{proposal submit, resolve}`, which the count alone cannot assert. Legacy option abbreviation
   stays pinned ACCEPTED, so the M3.5b deferral closing is visible rather than silent. The
   fresh-ledger BYTE SIZE is reported but not graded: it is a function of the host SQLite build's
   page size and layout, and D13 needs creation versus non-creation. What the gate grades instead
   is `bytes_positive` and `bytes_deterministic` — two independently constructed fresh ledgers must
   have the same non-zero size — which is falsifiable without being host-fragile. A seventh probe,
   `parser_shape`, digests every leaf's option strings, destinations, defaults, required flags and
   nargs (126 actions, sha256-16 `89dfa3d982d8c54b`); it is what makes D27's migration claim true,
   because mutating `events --limit` from 1000 to 7 leaves D24, D25, D26 and the census all green
   while the digest moves. `provenance_literal` counts literals over the AST and reads the exported
   symbol from the imported module, since a substring census also counts comments and prose.
   Verified at seed with **15 negative controls**, all firing.
5. Re-derivation of both spike tables from their tracked patches and drivers is NOT a gate; it is
   the fork ruling's evidence and was run at S1.

Every gate reruns from this unit's committed checkpoint.

## 12. Deferred to `.agent/polish.md`

Each entry carries its acceptance check, written now while the evidence is fresh.

- **Global `allow_abbrev=False`.** Abbreviation is live at the root and on nested leaves
  (section 2). Check: every parser node sets it, and a census-derived test asserts `--part`,
  `--bun` and `--in` are all `unrecognized arguments`. Owner: M3.5b, which owns removal predicates
  and is where the weakness bites.
- **A public existing-only construction mode.** D13 is a pre-construction check, not a read-only
  constructor; `X02` measured that `Store.__init__` uses `O_CREAT|O_EXCL` and `_initialize` opens a
  writable connection even for an existing ledger. Check: an unpatched `main` on an absent path,
  and on a read-only directory, creates nothing and answers 5. Owner: M3.6b, which reworks
  construction.
- **The write leaves still create a ledger on a typo'd `--db`.** `Z15` measured it for submission
  under both alternatives; D13 fixes the read verb only, because changing every write leaf is a
  cross-cutting behaviour change this unit does not own. Check: one ruling covering all write
  leaves, applied uniformly.
- **`m3u5a-map.json` rows not re-derived by MAIN.** Section 2 credits six findings. The remaining
  49 rows are attention-directing and were consumed as pointers only. Check: any row promoted to a
  durable claim is re-derived first.
- **`cli.py:370`'s coincidental `65_536`.** It bounds `--source-command` and is unrelated to
  provenance, but it is now the only bare copy of that number in the runtime and forced `X11` to be
  narrowed. Check: it becomes a named constant documented as provenance-unrelated, and one test
  asserts `cli.py` holds zero bare `65_536` literals.

## 13. Verdict table — MAIN-final

Table = `.agent/decisions/m3u5a-verdicts.json`, 60 rows (28 seeded, 32 extension), produced
diff-blind at `wt/test-m3u5a-1` and graded `PASS` with `UNKNOWN-CELLS 0` and
`CONCRETE-EXPECTATIONS 60` by `uv run python .agent/decisions/m3u5a-wave2-validate.py
.agent/decisions/m3u5a-verdicts.json`.

MAIN's `main_verdict` and `action` columns are written by
`uv run python .agent/decisions/m3u5a-rule-verdicts.py [--check]`, idempotent and asserting the id
set, so a later row addition fails loudly rather than going unruled. Ruled distribution:
**58 CONFIRMED, 2 SCOPED; 53 ENCODE, 7 ENCODE-SCOPED**. `ENCODE-SCOPED` rows are
`X01, X02, X06, X11, X16, X20, X29` — each carries a narrowing the battery must apply, because the
literal row would go red against correct code.

Ten rows are `divergent: yes`: `V12, V19, V22, X01, X02, X05, X06, X12, X16, X29`. Six forced the
amendments below; `V19`, `V22` and `X12` were wording forks the contract left open and the ruling
now closes on the shipped sentences; `X05` proved a suspected conflict is not one.

Five expectations were corrected against MAIN's live measurement before ruling — `V18`, `V22`,
`X11`, `X16` and `X16`'s divergence flag. Each would have gone red against correct code.

### Amendments — binding, superseding the cited section text

A1-A6 come from the verdict table below; **A7 (D13)** and **A8 (D27)** come from the attack table
and are written in section 14. All eight are one set.

- **A1 (D01, D14)** The guarantee is that no option prefix ever BINDS: every prefix invocation
  exits 2 with empty stdout. The message is `unrecognized arguments: <prefix> <value>` only when
  the required option is separately supplied. A prefix standing IN PLACE of the required option
  answers `the following arguments are required: --input` (or `--submission`), because argparse
  runs its required check inside `parse_known_args`, ahead of the leftover check in `parse_args`.
  D01's "every other prefix is `unrecognized arguments`" named one of the two messages as if it
  were the property.
- **A2 (D05)** The library owns precedence AMONG library validations —
  `partition → operation → expected hash → input` holds for every value that reaches
  `System.resolve`. CLI value-parsing necessarily precedes all of it, because `--input` must become
  a value before the call exists: `--input '{bad' --expected-function-hash bad` is exit 2
  `invalid JSON: …`, while `--input 1 --expected-function-hash bad` is the library's
  `expected_function_hash must be a SHA-256 hex digest`. Duplicating `_digest` in the CLI to
  restore the literal edge is REJECTED — it puts a second copy of a library validator on the
  surface D05 exists to keep thin.
- **A3 (D06)** One `Store.transaction(write=False)` per invocation that REACHES THE LEDGER. A
  rejected invocation opens zero. Observable: `{valid: 1, invalid: 0}`.
- **A4 (D09)** The biconditional binds `matched` ALONE. `output` and `artifact_hash` are null
  whenever no artifact is projected, which includes the verified miss where `matched` is `false`.
  Measured `(matched is None, output is None, artifact_hash is None)`: hit `(F,F,F)`, miss
  `(F,T,T)`, failed `(T,T,T)`. The domain narrows to values `System.resolve` computes through the
  SHIPPED `verify_function`. The defensive guard at `system.py:3835` returns `match=None` whenever
  `not verification.passed or document is None`, so an overridden `verify_function` yielding a
  passing verification with no document produces `(passed: true, matched: null)`. The CLI does not
  normalize that pair, and normalizing it is REJECTED: mapping it to `matched: false` would launder
  an internal inconsistency into an ordinary miss, and the null is exactly the signal that should
  stay visible.
- **A5 (D18)** `before any transaction opens` is TRUE as written at the `Store.transaction` seam
  and is retained. Added, because D18 omitted it: envelope validation runs in the dispatch branch,
  AFTER `System(...)`, so a writing leaf creates its ledger and initialises the schema before
  rejecting a malformed envelope. Measured on all four envelope failures: `System.__init__` 1,
  `sqlite3.connect` ≥ 1, `Store.transaction` 0, `System.submit_proposal` 0, ledger present
  afterwards at ~208 KiB. Giving `proposal submit` a D13-style precheck is REJECTED: creating the
  ledger is a legitimate first use of a writing leaf. The residual — an invalid argument value
  creating the ledger on ANY writing leaf — is CLI-wide, pre-existing, and deferred (section 12).
- **A6 (D28)** The mechanical grep is a UNION over `README.md`, `docs/architecture.md` and
  `docs/threat-model.md`: each spelling appears at least once in that union, and README carries
  both. `docs/adapter-protocol.md` is OUTSIDE the union — it documents the adapter protocol and
  names no CLI leaf. Measured cells for (`cement resolve`, `cement proposal submit`): README
  `(1,1)`, architecture `(1,1)`, threat-model `(1,2)`, adapter-protocol `(0,0)`. The per-file
  reading is rejected on merits: it forces redundant grammar transcription into documents whose job
  is not teaching invocation, and duplicated grammar is what goes stale. Shipped blocks spell the
  invocation `uv run cement … resolve`, so a token search must accept both spellings.

## 14. Review dispositions, differential and attack results

Attack table = `.agent/decisions/m3u5a-attack.json`, **50 rows** (20 seeded, 30 extension) from
`wt/rev-m3u5a-1` @ `c462286`, graded `PASS` with `UNKNOWN-CELLS 0` by
`m3u5a-wave2-validate.py`, re-run by MAIN. Severity split as the reviewer filed it:
**11 blocking, 33 material, 4 cleared, 2 minor**.

### Blocking — all 11 ruled, none open

| id | ruling | landed |
| --- | --- | --- |
| `A01` | ACCEPTED. Same finding as verdict `X02`; D09's domain narrowed. | amendment A4 |
| `A03` | ACCEPTED. D13's `never worsens` was unconditional and false. | amendment A7 |
| `A12` | ACCEPTED. D27's `strictly stronger` was false; a parser-shape digest now carries what B02 lost. | amendment A8 + gate 4 |
| `Y01` | ACCEPTED. The fresh-ledger byte size is a host SQLite property, not a Cement invariant. | gate 4 re-grade |
| `Y02` | ACCEPTED. Gate 4 was unsatisfiable — it required the two facts D25 and D16 move. | gate 4 re-anchor |
| `Y03` | ACCEPTED. `m3u5a-s2-probe.py` returned 0 unconditionally and could not fail. | gate 4 grading |
| `Y04` | ACCEPTED. Same finding as verdict `X01`. | amendment A2 |
| `Y05` | ACCEPTED. Same finding as verdict `X06`. | amendment A3 |
| `Y06` | ACCEPTED. Same finding as verdict rows `V02`/`V18`. | amendment A1 |
| `Y18` | ACCEPTED. The argv disclosure claim was platform- and policy-unconditional. | `docs/threat-model.md`, `README.md` |
| `Y21` | ACCEPTED. The stdin-capacity claim rested on `@PATH` probes the fork ruling removed. | re-cited below |

`A01`, `Y04`, `Y05` and `Y06` were each raised INDEPENDENTLY by the diff-blind `test` teammate and
by this reviewer, on different lenses and from different evidence. Four two-lens confirmations
satisfy the council rule without MAIN adjudicating.

### Two further amendments

- **A7 (D13)** The pre-construction check strictly improves for a path that is STABLY ABSENT. The
  claim `never worsens` is withdrawn as unconditional: in the inverse race a valid ledger appearing
  between the check and construction turns a would-be success into exit 5. The mechanism is
  decomposed rather than raced: `System` builds a valid ledger at a staging path, the target tests
  absent, `os.replace` moves it in, and ordinary construction on the now-present target succeeds —
  so the precheck's exit 5 would have been computed from a state construction no longer sees. The
  window is the same microseconds D13 already discloses in the forward direction, and no code
  change is warranted; the unconditional sentence is the defect.
- **A8 (D27)** D27's claim that D24, D25 and D26 are `strictly stronger` than B02's retired `cli.py`
  byte pin is FALSE and withdrawn. The three cover source reach, leaf names and option isolation;
  none notices an old leaf's changed default, help string, payload or dispatch. Demonstrated by
  mutating `events --limit` from 1000 to 7: census stays 30/37 and every D24/D25/D26 assertion stays
  green. The replacement is gate 4's `parser_shape` digest, which moves on that exact mutation. D27
  now claims what is true — the migration preserves B02's CLI-preservation property through a
  behavioural digest rather than a byte pin over a file this unit is chartered to extend.

### Y21 — the stdin-capacity citation

The fork ruling's sentence credited a measured 2,162,722-byte stdin acceptance to spike probes
`Z11`/`Z12`, which carry the cap pair through the `@PATH` route section 3.2 REMOVED; `Z09` measures
41 stdin bytes. The claim is now carried by `m3u5a-smoke.py` instead, which drives the shipped
`main`: a frame at exactly the cap is accepted on the byte stream, and `cap + 1` is rejected on the
byte stream, on a text stream, and inline. The at-cap frame spends its bytes across `input`,
`output` and `provenance` at their several maxima simultaneously, which is the submission per-field
flags can never carry, so the probe exhibits the fork ruling's own ground.

### Material, cleared and minor — 39 rows

The 33 `material` rows are almost entirely BATTERY-DESIGN constraints: how a pin must be written so
it cannot pass vacuously. They are S4 input, not S3 defects, and none indicts shipped behaviour.
Four are already discharged inside gate 4 — `Y22` (AST literal census and imported-symbol check
replace substring counting), `Y23` (the probe count in the docstring), `Y26` and `Y27` (gate 2's
`ASSERTIONLESS`/`SKIPPED` and gate 3's green control run). `Y28` is ruled NOT a defect: repeated
options are argparse last-win uniformly across all 30 leaves — measured, `--input 1 --input 2`
resolves against `2` — and D01/D14 fix the option SET rather than repetition arity, so making two
leaves differ would be the asymmetry.

The 4 `cleared` rows (`A05`, `A06`, `A14`, `A15`) record probes with no defensible alternative and
are kept as written. The 2 `minor` rows are absorbed: `Y23` above, and `Y30`'s rationale correction
to D27, which A8 supersedes.

The per-row `disposition` and `main_note` columns are filled at S4 by an idempotent `--check`
patcher asserting the id set, following `m3u5a-rule-verdicts.py`. Every blocking row's ruling is
already binding here; the patcher records it per row rather than deciding it.
