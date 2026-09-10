---
paths:
  - "tests/**"
  - ".agent/decisions/**"
---

# Assurance law — batteries, instruments, waves

## What closes a claim

- Mutation criterion, binding: for every check, some committed test fails when that check's logic alone is deleted. Logically entangled checks (a duplicate `input_hash` also breaks `build_function`) satisfy it by asserting the COMPLETE ordered check vector plus the detail of the check under test; never report a derivative check as passing to manufacture isolation.
- A green suite is NEVER closure for a removal: deleting a behavior together with its pin leaves the gate green and coverage unchanged. Enumerate the residue (symbol, grammar token, table, index, help line, doc row) as absence assertions, pin every preserved neighbour independently, and rerun both from the unit's committed checkpoint.
- Token-absence cannot prove structural deletion — a rename satisfies every residue grep while the code stays. Pair each residue predicate with a STRUCTURAL pin over the shipped source: helper call count per method, transaction count and kind, ordinal position of clock/ID acquisition (`inspect.getsource(...).count(...)` + index comparison, no production hook needed).
- A residue classifier needs a stable domain, an exact regex, an explicit survivor allowlist, and it must PRINT every unmatched hit — and exclude ITSELF from its own scan.
- One row per clause certifies only that the clause has SOME live content; a clause is a conjunction. Seed one row per clause, require the FILL to enumerate subproperties, and make coverage a floor rather than an identity. Acceptance is obligation-level, defects are conjunct-level.
- Three blind-conjunct shapes: VACUOUS BY A SIBLING GATE (a work list drawn from a post-state census whose emptiness is another gate's acceptance) — draw it from the BASELINE census or the frozen opening set; A LITERAL THAT NEVER EXISTED — re-derive every asserted string from the baseline blob rather than retyping it; TWO ARTIFACTS UNDER ONE CLAUSE (committed copy vs working tree) — name ONE source per clause.
- A clause whose subject is committed history is insensitive to every working-tree mutation ⇒ it takes a GROUNDED EXCLUSION printed on every control line, never a row.

## Verification integrity

- `prototype/` is outside every check, measured: no module under `tests/` names it, the wheel carries `cement_runtime` alone, and the sdist carries `docs`, `examples`, `src`, `tests` without it ⇒ PROTOTYPE law governs it and its shortcuts stay. What keeps a shortcut from becoming a false claim is the ruled boundary INSIDE the demo — the provider alone is simulated + labelled, while lifecycle, digests and timings come from the real runtime (`.agent/spec.md` `Decisions`).
- An expected-output table the contract does not own is the defect; this repo's contract OWNS one. A function IS a set of exact entries (`cement-function-v2`) over partition + operation revision + canonical JSON input, specified by README paragraph 1 plus the trust-boundary ruling ⇒ `resolve` returning a stored output on an exact match is the SPECIFIED behavior, never a fixture shortcut, and the domain outside the entry set is contracted too: an inert miss, never a widened predicate, with M4's verified projection the only artifact that widens what one entry covers. Each entry carries an `entry_seal` derived from its artifact plus its verification report (`_function_entry_seal`, `src/cement_runtime/system.py:199`) and recomputed on read (`_function_report_member`, `:2287`, `IntegrityError` on mismatch), while `function_hash` binds the whole normalized table (`src/cement_runtime/function.py:256`); `verify_function` RECHECKS those bindings without mutation (`system.py:2878`) rather than creating them. The defect shape that stays live here is narrower: a `src/` branch keyed to a test's input or expected value, an entry no verification report seals, and an expected value RETYPED into a test rather than derived from the artifact under test.
- Red-first and preservation are two credentials, not one. A test pinning NEW or CHANGED behavior earns red on the unfixed revision, its SHA + command recorded in the commit body (`.claude/rules/ops.md` Commits). A preservation pin legitimately holds at baseline, so its credential is the mutation criterion above: some committed test fails when that check's logic alone is deleted, named survivor set attached. Forcing the second shape red by mutating the pin destroys the property it guards.
- The shipped suite's skip set is CLOSED at three, each conditional and each structural: `tests/test_source.py:107` + `:125` guard the two supervisor frames (`test_detached_descendants_are_killed_and_reaped`, `test_outer_watchdog_kills_adapter_if_supervisor_dies`) behind `sys.platform.startswith("linux") and pathlib.Path("/proc").is_dir()` — BOTH conditions, so a Linux container without `/proc` mounted skips them too — and `tests/test_lifecycle_removal_battery.py` L30 skips under `instrument_pruned()`, that frame and D28's own instrument being mutually exclusive by construction (`.claude/rules/ops.md`). A fourth enters green, so a new skip, xfail, deletion or tier demotion takes its `.agent/deferred.md` row plus approval BEFORE the case moves; the standing census that would decide this mechanically is queued as p66, being itself a gate change. A `skipTest` code seed on a red-to-green `impl/<unit>` revision is exempt ONLY while it stays off the squash: the squash carries the branch TIP's tree, not a merge of its history, so a seed still present at the tip lands on `main` as an ordinary fourth member — removing it is part of the unit that added it.
- The grading check is fixed when the contract is: the NUMBERED gate list reruns unchanged from committed state, which is why tooling lands at a unit BOUNDARY — a gate added mid-unit voids the pins it was meant to strengthen. The owner-approval half is `CLAUDE.md` `Engineering`, unrestated here.

## Controls

- An instrument that cannot fire reports exactly like an instrument that passed. Every control must be REACHABLE and must violate the obligation it names — read the target test's own assertion and confirm the mutation drives THAT assertion false.
- A mutation control aims at the test that OWNS the property. Where an obligation reads "frame F preserves property P", the clause is a static check on F's text, so a production mutation cannot redden it; the target is F.
- A test whose subject is a CONSTRAINT needs a positive control that the constrained ROW exists: a zero-row `UPDATE` raises nothing, so `assertRaises` over a no-op is green-and-empty.
- A self-test control that mutates `rows[0]` dies at scale once several rows cover one clause: drop the whole COVERING SET, and re-run `--self-test` after every scale-up — a both-ways credential earned at seed size is not one at fill size.
- Recording instruments must be TOTAL over their channel: override `execute`, `executemany`, `executescript` AND wrap `cursor()`, else a base-cursor read bypasses the instrument while the test reports clean.
- A probe that records AFTER the call loses every deliberately-raising case: append the record BEFORE the call, mutate it after. Pair with a per-call positive control that round-trips through the system under measurement, and make the grader FAIL on uniformity over a heterogeneous population.

## Mutation campaigns

- Purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`: CPython invalidates bytecode on `(mtime, size)`, so a length-preserving edit inside one mtime-second runs the ORIGINAL code and reports a live mutant as surviving.
- Address every mutant by line plus an asserted anchor string with `count == 1` (multi-line anchors where a fragment repeats); assert `text != before`, then assert the observable actually moved. A bare `python` is absent from PATH and exits 127 without editing anything, printing exactly like a survivor.
- Run a pristine CONTROL sweep at full worker count first; load-sensitive tests turn contention into phantom kills, and a phantom kill silently retires a real finding.
- A survivor count is meaningless without its VERDICT MODULE LIST — print the modules on the control line and quote them beside every count. A dead branch and a surviving mutant are one fact seen twice: an unforced enforcement line gets deleted, an unforced GRANT splits by reachability.
- An author-run sweep certifies only the families its author had in mind; treat it as a floor and give the campaign its own catalogue. Re-anchor after a fix through a `difflib` line MAP over a byte-exact pre-fix copy; three outcomes are distinct — killed, survived, superseded (`old` absent ⇒ the fix deleted that code).
- The sweep patches `src/` in place ⇒ `git status` is contaminated for its whole run; commit by explicit pathspec, and after a kill run `git status --porcelain src/` + `git checkout -- src/`.

## Fixtures and bounds

- Vary every fixture across the boundary its check depends on: drive at least one integer >9 (below 10 decimal and hex agree), give scope-isolation fixtures collision pairs (`tenant_a` vs `tenantXa`) plus case variants because `=` weakens to `LIKE` undetected, make member and candidate ID sets differ, and break insertion order away from query order.
- Enumeration completeness needs a tail sentinel beyond any plausible `LIMIT`. Set-level gates need multi-entry negative probes: corrupt the MIDDLE and the LAST of ≥3 entries, and split compound conditions into one probe each.
- Pin every bound as an adjacent accept/reject PAIR (`max` accepted beside `max + 1` rejected). Derive the constant from the running system (`os.pathconf(parent, "PC_NAME_MAX")`), never from prose.
- Frozen public shape is invisible to behavioral tests: one `inspect.signature` + `typing.get_type_hints` test per ABI. A recursive type alias is not equal to itself under `|` — pin the ANNOTATION TEXT (PEP 563 stringifies from the AST and normalizes quotes); compare `dataclasses.MISSING` by IDENTITY, and check `default_factory` beside `default`.
- Behavioral tests cannot see resource contracts: slicing after the fetch makes `LIMIT ?` bound to `limit + 2` byte-identical. Pin materialization with a connection/cursor proxy asserting the final bind and the rows fetched.
- Mock the LIBRARY boundary, never the module's own dispatch function — patching `_run` to pin `main`'s exit map replaces the branch under test. Tell: a mock whose return value is the input to the logic under test.

## Diff-blind authorship

- A diff-blind author pins what it can see, so it paraphrases library and stdlib text and guesses the baseline's code shape (helper names, occurrence counts, assertion spellings) — both redden correct code. Write each clause against the PROPERTY, derived by AST or by running the named gate, and MAIN-verify every exact-string pin against a live run before it drives an implementation.
- Red-at-baseline / green-at-HEAD is MAIN's credential, run in a detached worktree with the import path proven, REPORTED never forced: preservation obligations legitimately hold at baseline.
- Dispatch the phase-1 table BEFORE implementing; its divergences are the contract's real defect list, and full convergence is the maturity signal. Where the contract already names every string and corpus, budget the suite as redundancy insurance and spend the freed capacity on the contract attack.

## Instruments and validators

- DERIVE the instrument, never hand-list it, and assert the COMPLEMENT (the set a path names must EQUAL the permitted set). A forbidden-list instrument fails open on exactly the members nobody thought of.
- Grade by whole-token set membership, never containment (`24` sits inside `243`); normalize presentation first (digit grouping, abbreviated digests). Match the seed to the check's QUANTIFIER: a check grading a pair of files is untouched by a seed that edits one.
- A validator that passes on its first run has not been graded. Grade BOTH ways at seed (all-`unknown` nonzero, filled 0), re-grade both ways after any widening, and grade each artifact BY NAME with its own rc — one PASS line reads as covering every table.
- A grader's strict branch guarded by a surface heuristic fails closed on legitimate rows (a `\d{2,}` concreteness test rejects single-digit counts, booleans, `[]`); make the unclassified case FAIL and name the token, and let a widening carry its own evidence rather than becoming a bypass.
- A validator's clean grade says nothing about columns it EXEMPTS — print the exempt columns; teammate completeness and MAIN's ruling are two deliverables and only one is graded.
- Run every idempotent patcher twice before trusting it once: derive aggregates from FINAL state, guard idempotence on post-state CONTENT (a marker-presence guard re-emits an archive from its own summaries), and give each edit a distinct sentinel — an anchor re-emitted by its own replacement reapplies forever.
- A scratch-local validator is a temporary encoding: record its regeneration path beside the gate invocation here and open a `.agent/deferred.md` row for the port, acceptance check written while the evidence is fresh.

## Contract text is an artifact

- Every number a contract states must be RUN in the session that writes it, corrections included — a correction is where unrun numbers concentrate. A gate's command is an unverified claim until executed once.
- Nothing grades the contract against its own instruments' results, so a closure session re-reads the gate text against what the campaign measured. Replace a "zero survivors" predicate with the NAMED survivor set, and state every number a gate depends on IN the contract.
- A set obligation states its DERIVATION, and the spellings are enumerated from the corpus: `assertIs(type(x), T)` states what `assertIsInstance` states, `typing.cast(T, x).attr` reads what `x.attr` reads, and `kind=` reaches an `IfExp` second branch and a `JoinedStr` no first-branch scan sees.
- Obligation and gate numbers are NOT keys across contracts: cite a foreign id with its unit name, keep illustrative ids out of any text a binder parses, normalise through the contract's own spelling (never `.upper()`), and bound a parsed list at the next structural token — a `\Z` bound makes the last entry unauditable until a successor lands behind it.
- A prescription authored in an earlier unit is a claim with an expiry: re-derive its PREMISE at HEAD before implementing it, and re-derive every scheduling premise by hashing the named symbol's body at each SHA in the range.

## Tripwires and burden

- Three tripwire classes: what the DELETION breaks (staged burden run), what a PROSE REWRITE breaks (vocabulary census), and what an ADDITION breaks — invisible to both, because no burden stage adds a file and no census reads one. Before adding a file to a frozen tree, grep the batteries for clauses whose path set is computed against `HEAD` rather than a closed range, and close both halves.
- Every instrument reading `tests/` sees the unit's own battery, and obligation PROSE is an input to all of them (a seed quotes contract text into docstrings). Exclude the battery BY NAME with a checked `SELF-REFERENCE` property plus a control, print the exclusion, and repair the CONTRACT's vocabulary rather than a standing gate.
- A scope pin read against the WORKING TREE expires: write "unit X touched nothing under Y" as `_git_bytes(<close SHA>, p) == _git_bytes(<baseline SHA>, p)`. Enumerate a pin family by its assertion SHAPE, not by the ids the current task touched, and re-run that census after the repair.
- A whole battery grading a CLOSED transition takes both endpoints from git, never the tree: the question is settled and permanently answerable, so a tree-relative frame reddens correct work at the next unit and the tax repeats per unit. Tell that the class is present rather than one frame: the battery goes green at the predecessor's close SHA and red at HEAD. Freeze it behind ONE class-level detached worktree; give every tree-reading helper a `root` with NO default so a frame cannot reach the tree without naming it; pin that structural half FIRST, because while a helper carries the tree implicitly the frame census reports exactly like a converted battery. Keep only frames whose subject IS the live range, each in an allowlist checked in REVERSE so a converted frame cannot be parked there.
- Before adding a file to a frozen tree, read every tree census in the suite, not only the burden runs: `git ls-files -- '<glob>'`, `rglob`/`glob` over repo directories, dot-entry scans, and whatever reads the manifest. Record which censuses the new path ENTERS and which it misses — an addition is invisible to a deletion burden and to a vocabulary sweep alike.
- Measure a removal by deleting it and running the gate; the failure list is the work list, and the map serves as the per-test disposition ruling. Group failures by deepest `tests/` frame and size on NORMALISED frames (`file in name`); RAW keys (`file:line in name`) differ 5–10% and mixing conventions manufactures a defect.
- Compare the failure SET between stages, never the count: a subtest-bearing test contributes a variable number of breaks, and a cumulative stage reporting FEWER breaks has broken collection (print `Ran N`, diff the collection, add a stage repairing import lists alone).
- Scripted, count-asserted, idempotent surgery beats hand editing past ~30 tests; grep the DEFINITION vocabulary as well as the call vocabulary first, since two definitions sharing a name make a bare anchor span both.

## Waves

- Seed the deliverable, and seed its row SUBJECTS: filling a named locus is resumable after any death, discovering which rows exist is not. Extensions are a floor — name the row count at which extension stops, since an uncapped invitation runs unbounded (findings rising with row count is the tell, and the artifact is committed per batch, so stopping the agent costs nothing).
- Order the graded artifact FIRST in the brief; a probe corpus answerable against baseline silently substitutes for the ungraded half, so every spike row carries BOTH a `baseline` and an `alt` observation plus a minimum addition count.
- Instruct the oracle NOT to match MAIN's rulings: a divergent oracle BUILDS the branch other lenses only warn about. An oracle corpus written to demonstrate the oracle's own conformance discriminates nothing — budget conformance probes as a control and aim the rest at ruled disagreements.
- A mid-wave contract edit expires every seeded predicate at once: re-derive them against the NEW contract and re-grade the validator both ways.
- MAIN's fill of an exempt column belongs in an idempotent `--check` patcher carrying an `id -> (verdict, action)` map that asserts the id set and rewrites under the artifact's own serialization (determine it empirically by round-trip).
- Re-derive a teammate artifact before crediting it; a PASS from a pre-repair copy certifies the OLD state. Teammates can report completed work they did not do, and a stated validator RESULT can contradict its own artifact — rerun the validator yourself.
