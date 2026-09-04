#!/usr/bin/env python3
"""Fill the MAIN-owned `disposition` and `main_note` columns of m3u6a1-attack.json.

    uv run python .agent/decisions/m3u6a1-rule-attack.py [--check]

Idempotent, replayable from the teammate's committed table (wt/rev-m3u6a1-1 @ 82e1a2e,
36 rows: 30 seeded A01-A18 + Y01-Y12, 6 extension A19-A21 + Y13-Y15). `--check` exits 1
when the table is out of sync, so a later row addition fails loudly instead of going
undisposed.

Dispositions:
  ACCEPTED  the shipped artifact currently STATES or CERTIFIES something false
  SCOPED    the artifact is true but weaker than its wording implies; the ruling names
            the real domain and the obligation, if any, that already discharges it
  CLEARED   the reviewer found no defensible attack and MAIN concurs
  DEFERRED  real, but its owner is the polish register or another unit

Counts the reviewer reported: 12 blocking, 22 material, 2 cleared.
MAIN's dispositions: 5 ACCEPTED, 27 SCOPED, 2 CLEARED, 2 DEFERRED.

The discriminator, applied uniformly. Nearly every row proves the same thing: a gate
predicate is NECESSARY and not SUFFICIENT. For a tripwire that is the normal condition,
not a defect. It becomes a defect exactly where the contract calls the tripwire a proof.
So the disposition splits on the artifact, not on the attack's strength: ACCEPTED where
something shipped is false today, SCOPED where the wording outran the instrument.

Measurements this ruling rests on, derived by MAIN in the primary tree at 48649d8:
  seed census (8592c34) RETAIN = 23 definitions / 44 sites; shipped = 23 / 45. The whole
    increment is tests/test_system.py::test_operation_revision_invalidates_every_old_request_path,
    6 sites -> 7, gaining tests/test_system.py:880
  `self.confirm(` in tests/test_system.py = 40 occurrences, down from 41
  m3u6a1-fallback.py:130 gates the digest control on `isinstance(outcome, ReviewRequired)`;
    the run reports CONTROL-DIGESTS: 24 checked over 17 printed site rows
  gate 4 prints ACTOR 2 / MISS-GUARDED 0 / HIT 9 / FACTORY 28 and RESULT: PASS, with
    tests/test_system.py:481, :571 at `resolve -> passed=False failed=[persisted-function-receipt]`
    and :582 at `passed=True match=False`, the verified-miss signature
  m3u6a1-premise.py exits 0 while printing both final verdicts as False
  battery D04 runs `git diff --exit-code 6fb4d92 -- src`, a WHOLE-TREE pin, not the
    six-module allowlist D27 describes
  battery D05 asserts `_consumer_map(ROOT) == retained`, a qualified-name -> count map
  battery D06 orders resolve before propose by `call.lineno` alone
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u6a1-attack.json")
DUMP = dict(indent=2, ensure_ascii=False, sort_keys=False)

_CLEARED = (
    "CLEARED. The reviewer found no defensible attack and MAIN concurs: the obligation "
    "rests on a discriminating before/after state that the premise probe measures "
    "directly, and each named mutation fails closed rather than vacuously."
)

# The single structural finding behind A01, A06, Y02, Y03 and Y04. Named once so the
# rows that share it do not each restate it.
_REDERIVED = (
    "The census and the shape table are REGENERATED from the current tree, so a "
    "consumer that was DELETED and a consumer that was MIGRATED leave identical "
    "evidence, and a migrated definition leaves the attribution population at the "
    "moment its replacement most needs inspecting. "
)

# id -> (disposition, main_note)
RULINGS: dict[str, tuple[str, str]] = {
    "A01": (
        "SCOPED",
        _REDERIVED
        + "The attack is correct and the obligation is a TRIPWIRE, not a completeness "
        "proof: `SURVIVING-MIGRATE: 0` says no direct-attribute lifecycle call remains "
        "under `tests/` or `examples/`, which is the property a future edit is likely to "
        "break by accident. It cannot exclude a bound method, `getattr`, wrapper or "
        "descriptor, and no re-derived census ever will. The real closure is STRUCTURAL "
        "and belongs to M3.6a2: once `handle` and `request_status` do not exist, every "
        "spelling in this attack raises `AttributeError` and the absence stops being "
        "measured. Contract section 7 must read `no measured direct call survives`, not "
        "`every consumer stopped`.",
    ),
    "A02": (
        "SCOPED",
        "Lands against the contract's wording and is already discharged by the battery. "
        "D03's shipped test pins each RETAIN definition BOTH ways the attack asks for: "
        "`_lifecycle_count(definition) == row['sites']` compares the shipped AST against "
        "the COMMITTED census row, and every retained name is then re-run by "
        "`_run_test_methods`. Removing one `request_status` entry drops the AST count "
        "while the committed JSON still reads 2, so D03 goes red before any regeneration. "
        "The residual is the attack's real root and it is Y03's, not D03's: an author who "
        "also regenerates the table restores agreement. Rule at Y03.",
    ),
    "A03": (
        "SCOPED",
        "Lands against D05's WORDING and is discharged by D05's shipped test, which "
        "asserts more than the obligation says. `self.assertEqual(_consumer_map(ROOT), "
        "retained)` compares a qualified-name -> site-count map derived from source "
        "against the committed census, so the survivor-swap this attack describes fails "
        "on the name set, not on the cardinality. The contract sentence states a "
        "cardinality and should state the map; the instrument is already right.",
    ),
    "A04": (
        "SCOPED",
        "Correct that `passed is True` plus `matched is False` is weaker than the "
        "conclusion drawn from it, and the missing premise is the same one Y13 names. "
        "The pair proves resolution examined its state and selected nothing; it does not "
        "prove a same-input once-promoted artifact exists in the required status. The "
        "domain that makes it sound is the SITE, not the assertion: `m3u6a1-fallback.py` "
        "establishes `_ONCE_PROMOTED` membership per site before the shape is assigned, "
        "and only sites carrying that evidence were ruled MISS-GUARDED. The obligation "
        "should cite that precondition instead of re-deriving it from two booleans. "
        "Y13 owns the execution half.",
    ),
    "A05": (
        "SCOPED",
        "Correct: call presence is not ledger equivalence, and D07's own sentence claims "
        "the stronger property. The bounded reading is that D07 preserves the SHAPE of "
        "each MISS-GUARDED site - a proposal is still created there - while P1 supplies "
        "the row-state result for a matched pair of routes, measured once in "
        "`m3u6a1-premise.py`, not site by site. Arguments and multiplicity at each site "
        "are carried by that site's own assertions under gate 1, which is exactly the "
        "oracle Y01 shows is not independent. Y01 owns the general defect.",
    ),
    "A06": (
        "SCOPED",
        _REDERIVED
        + "D08 is a negative obligation whose LIVE population empties as the migration "
        "succeeds, and its real value was as a rule on MAIN's hand at authoring time - do "
        "not write a verified-miss assertion where no once-promoted artifact exists. It "
        "does not depend on the live gate, because the frozen opening set exists: the "
        "committed `m3u6a1-fallback.json` records all 72 opening targets and 51 FACTORY "
        "sites, and the battery's `_shape_owners` reads THAT table rather than a fresh "
        "run. The obligation is therefore checkable against the opening population "
        "permanently. Y04's ruling carries the same correction.",
    ),
    "A07": (
        "SCOPED",
        "Correct, and the same lexical-versus-semantic gap as A08; rule there. Specific to "
        "D12: `prefix` existed only to build two request identifiers, and the migrated "
        "helper cannot accept a caller-chosen request id at all, so the parameter is not "
        "merely unread, it is UNBUILDABLE - there is no expression the body could form "
        "from it. That is a stronger and checkable property than `no statement reads it`, "
        "and it is what D12 should say.",
    ),
    "A08": (
        "SCOPED",
        "Correct in full and the ceiling is real: no AST predicate decides reachability or "
        "observable effect, and `locals()[name]` reads without an `ast.Name` node. D14's "
        "defensible scope is the SHIPPED SIGNATURE SET, which is decidable: after "
        "migration no helper declares a parameter that no statement mentions. Every "
        "evasion in the attack requires ADDING a dead statement, which is a visible edit "
        "under review rather than a silent survival - that is the whole difference "
        "between this and the residue D14 exists to catch. A20 owns the variadic hole, "
        "which is the one evasion that adds nothing visible.",
    ),
    "A09": (
        "SCOPED",
        "Lands against D16 and C05 as WRITTEN and is discharged by the battery, which "
        "supplies every pin the attack asks for. `tests/test_migration_battery.py` sets "
        "`BASELINE = \"6fb4d92\"` and D16 replays into a detached worktree at that commit, "
        "not through `git checkout --` against the current index. The tautology the attack "
        "describes is exactly what C05's prose recipe would have produced, so the prose is "
        "the defect and the instrument is not. Correct C05 to name the detached-worktree "
        "recipe it should always have specified.",
    ),
    "A10": ("CLEARED", _CLEARED),
    "A11": (
        "SCOPED",
        "Correct that an aggregate `assert` count collides across opposite semantics, and "
        "this unit already paid for the weaker half: V06 shipped a stale `38` against a "
        "measured 35 because nothing bound the prose to the module. D21's count is a "
        "DRIFT DETECTOR for act-structure edits, which is the change this unit makes, and "
        "it now fails loudly on one. Assertion STRENGTH is a different property with a "
        "different instrument - a mutation campaign over the demo's verdicts - and it is "
        "Y01's, not D21's. Rule there; the demo mutant set is polish-register work.",
    ),
    "A12": (
        "SCOPED",
        "Correct: `[0-9a-f]{64}` proves a hex token occupies the position, not that it is "
        "the verified function hash, and the substitution in the reproduction would "
        "normalize identically. D22's domain is TRANSCRIPT REGENERATION - that the shipped "
        "block is the demo's own current output rather than a hand-edited relic - and for "
        "that the mask is correct and load-bearing. Binding a masked token to its producer "
        "value is a demo-assertion obligation: the demo already asserts the identity it "
        "prints, and Y01 owns whether that assertion is strong enough.",
    ),
    "A13": (
        "SCOPED",
        "Correct at the time it was written and now discharged by the battery, which built "
        "precisely the ledger the reproduction specifies: D28 enumerates `git rev-list "
        "--reverse 6fb4d92..HEAD` over the migration paths, checks each revision out "
        "detached, runs the full suite there, and requires rc 0 with `Ran N` >= 949. The "
        "endpoint-only record the attack indicts is gone. S6 also repaired D28's own "
        "self-reference (contract V08): the battery is the instrument, so every checkout "
        "drops it before the inner run.",
    ),
    "A14": (
        "ACCEPTED",
        "P1 as written is FALSE and the probe's own output says so. `m3u6a1-premise.py` "
        "prints six differing columns, classifies five VOLATILE and one ATTRIBUTABLE, and "
        "the volatile set includes `events.rows:row1.subject_id`, `row2.subject_id`, "
        "`row2.payload_json`, `examples.rows:row0.receipt_hash` and `receipt_json`. C02 "
        "separately concedes `requests.id` is caller-chosen under `handle` and internally "
        "minted under `propose`. So the literal row state differs in primary keys, foreign "
        "keys, event subjects and receipts. The defensible claim is the one the probe "
        "computes: after an identity-isomorphism projection that drops minted identifiers "
        "and their dependents, EXACTLY ONE attributable difference remains, "
        "`events.rows:row1.payload_json`. Correction C16 restates P1 in those terms; the "
        "projection is the claim's premise and must be stated with it, never assumed.",
    ),
    "A15": (
        "SCOPED",
        "Correct: `premise_2()` compares neither the post-promotion match output nor "
        "`artifact_hash` against the preceding `handle` result, so `after_hit` proves a "
        "match EXISTS. P2's role is a feasibility premise - after set promotion `resolve` "
        "can answer where `handle` answered from the artifact - and that is what the unit "
        "needed to justify migrating two demo sites. Output equivalence is asserted where "
        "it belongs, in the demo's own verdicts on the migrated acts. Narrow P2's sentence "
        "to match existence; the equivalence claim is D18's and Y14 owns its site mapping.",
    ),
    "A16": (
        "ACCEPTED",
        "Confirmed against the shipped gate. `m3u6a1-fallback.py` keys HIT on "
        "`outcomes != {ReviewRequired}`, which collapses `Resolved` with "
        "`ReconciliationRequired`, and it still prints `HIT: 9` and `RESULT: PASS`. "
        "Binding correction C01 already declares two of those nine not hits. An instrument "
        "that certifies a taxonomy its own contract calls FALSE is the V08 class exactly: "
        "the green reading is not evidence. C01 repaired the prose and left the gate, which "
        "is the half that outlives the session. Repair: split the ambiguity branch out of "
        "HIT so the printed partition matches C01. No migration ruling changes - both sites "
        "are RETAIN - so this is instrument truth, not a re-migration.",
    ),
    "A17": ("CLEARED", _CLEARED),
    "A18": (
        "ACCEPTED",
        "Confirmed and RESOLVED with the locus C11 failed to name. Seed census 8592c34 "
        "totals 23 RETAIN definitions over 44 sites; shipped totals 23 over 45. The entire "
        "increment is "
        "`tests/test_system.py::test_operation_revision_invalidates_every_old_request_path`, "
        "6 sites -> 7, gaining `tests/test_system.py:880`. Cause: that test's subject IS "
        "the caller-chosen request-id route, and migrated `confirm` can no longer carry a "
        "request id, so `self.confirm(\"old-confirmed\")` was inlined into the direct "
        "`self.system.handle(..., request_id=\"old-confirmed\")` plus `self.system.review(...)` "
        "pair it always was underneath. The call did not appear; it became VISIBLE. One "
        "event moves two denominators in opposite directions - `confirm`'s callers 41 -> 40, "
        "measured at 40 today, and RETAIN sites 44 -> 45 - and C11 recorded the second "
        "without its cause. Correction C17 names the locus and binds both movements to it.",
    ),
    "A19": (
        "ACCEPTED",
        "Confirmed at the source. `m3u6a1-fallback.py:130` reads "
        "`if isinstance(outcome, ReviewRequired): _control['checked'] += 1`, so every "
        "`Resolved`, `ReconciliationRequired`, `FallbackFailed`, `InProgress` and raising "
        "path skips the digest control entirely; the run reports 24 checked over 17 site "
        "rows. D09's battery docstring calls this a `per-call positive control` and that is "
        "FALSE as written. Worse for the taxonomy, the one global counter is not attributed "
        "to sites, so a site-selective wrong digest on an uncontrolled HIT flips its shape "
        "to FACTORY with every counter clean - which is the same blind spot A16 reaches "
        "from the other side. Repair: run the control on every observed call, attribute "
        "failures to their site, and correct D09's wording to whatever the instrument then "
        "does.",
    ),
    "A20": (
        "SCOPED",
        "Correct and it is the one D14 evasion that adds no visible dead statement: "
        "`*legacy_ids` accepts the old argument shape while the named parameter and the "
        "ordinary positional both vanish lexically. It does not land against SHIPPED state "
        "- migrated `confirm` and `_confirm_scope` declare no variadics, and all 40 and 65 "
        "callers pass fixed arity - so nothing is false today. It is a real gap in D10/D11 "
        "as PREDICATES, and the cheap closure is a signature allowlist rather than a "
        "parameter-absence check. Owner is the polish register: M3.6a2 rewrites these "
        "helpers again when the lifecycle API is deleted, and a signature pin written now "
        "would be rewritten there.",
    ),
    "A21": (
        "SCOPED",
        "Correct that D20 bans a MEANING with no oracle, and no gate can hold a semantic "
        "ban - the doc parser reads command syntax and the transcript test reads bytes. "
        "D20's real domain is a one-time authoring obligation on MAIN's hand, discharged "
        "and verifiable by reading Act 5: the retired framing is gone and no equivalent "
        "temporal claim replaced it. The durable half is not a gate but a fact - M3.6a2 "
        "rewrites the walkthrough again - so the honest record is that D20 was satisfied "
        "once, not that it is enforced.",
    ),
    "Y01": (
        "SCOPED",
        "The deepest row in the table and the one this unit already paid for. Correct that "
        "a green suite validates only surviving assertions, that expected and "
        "implementation code move together here, and that no independent assertion-strength "
        "oracle exists - V06 is the measured instance, a stale `38` that no gate could see. "
        "It does not land against shipped state: the wave-2 battery IS the independent "
        "oracle the attack says is missing, written diff-blind against the contract and the "
        "pre-implementation baseline, and it went red 23 of 29 at that baseline before "
        "going green at HEAD. That red-then-green transition is the assertion-strength "
        "credential a suite alone cannot produce. The residual - mutation testing over the "
        "migrated bodies - is polish-register work, and gate 1's own wording must stop "
        "implying the floor proves preservation.",
    ),
    "Y02": (
        "SCOPED",
        _REDERIVED
        + "This is A01 from the erasure side and it is the sharper telling: replacing a "
        "MIGRATE body with a tautology deletes its census row legitimately while gate 1's "
        "count floor holds. It does not land against shipped state, because the battery's "
        "D05 pins the qualified-name -> count map of every survivor and D03 re-runs each "
        "retained test by name. What neither pins is the frozen PRE-migration MIGRATE set "
        "with per-row dispositions, which is the artifact this attack correctly demands and "
        "which only Y03's ruling can supply.",
    ),
    "Y03": (
        "SCOPED",
        "Correct and it is the root A02 and Y02 both reduce to: `--check` compares "
        "hard-coded `RULINGS` against JSON regenerated FROM those rulings, so the pair is "
        "self-consistent by construction and synchronization is not integrity. The honest "
        "reading of `IN-SYNC` is that the committed table matches the committed rulings - a "
        "real property, since it fails when either moves alone - and nothing more. The "
        "independent anchor the attack wants exists but sits outside gate 3: the seed "
        "census at 8592c34 is committed and immutable, and A18's own resolution was derived "
        "by diffing shipped against it. Recording that seed as gate 3's reference is the "
        "closure; M3.6a2 must carry it, because that unit re-rules the whole population.",
    ),
    "Y04": (
        "SCOPED",
        _REDERIVED
        + "Correct that a successfully migrated definition has no `handle` call and so "
        "leaves the LIVE target set exactly when its replacement needs inspecting. The "
        "attack's remedy, a frozen opening site set, ALREADY EXISTS and MAIN's first "
        "reading missed it: committed `m3u6a1-fallback.json` is the opening attribution, "
        "72 targets against the migrated tree's 45, and `_shape_owners` in the battery "
        "reads that table, not a fresh run - which is why D07's four MISS-GUARDED owners "
        "resolve at all when the live gate reports MISS-GUARDED 0. What is genuinely "
        "missing is the REPLACEMENT-side half: nothing asserts what stands at each frozen "
        "site today. That is M3.6a2's, which must prove every deleted site's replacement. "
        "A19's repair landed here in S6 - the control now covers every returning call and "
        "names its site - and A16's split is replayed over the frozen table by "
        "`--reclassify`, so the opening evidence carries the corrected taxonomy without "
        "being re-measured.",
    ),
    "Y05": (
        "ACCEPTED",
        "Confirmed by running it: `m3u6a1-premise.py` exits 0 while printing "
        "`VERDICT P1 propose-equals-handle-row-state: False` and "
        "`VERDICT P2 resolve-replaces-artifact-hit: False`. Both False values are CORRECT - "
        "P1's projection leaves one attributable difference and P2 answers True only after "
        "set promotion - which makes the defect worse, not better: a reader is handed two "
        "`False` lines beside a green rc and must already know the answer to read it. A "
        "command that returns 0 for every possible output is not a gate; it cannot fail, so "
        "its rc carries no information and recording it as a passing gate asserts a check "
        "that never ran. Repair: assert the expected findings and exit nonzero on "
        "divergence, and rename the verdict lines so their polarity states the claim rather "
        "than negating it. The attack's second half - the probe is invariant under consumer "
        "edits - is correct and by design: it measures the API premises, and consumer "
        "obligations are the battery's.",
    ),
    "Y06": (
        "SCOPED",
        "Correct that second-run stability cannot constrain first-run correctness, and "
        "discharged by the battery: D16 replays from the explicit detached baseline and "
        "compares the produced tree against shipped bytes, which is exactly the "
        "distinguishing test the attack names. Gate 6's `no-op` keeps its own narrow job - "
        "the script is idempotent, so a rerun cannot double-apply - and V07 proved it live "
        "when a hand repair outside the script made the replay diverge within one gate run. "
        "Necessary and not sufficient, with the sufficient half already shipped elsewhere.",
    ),
    "Y07": (
        "DEFERRED",
        "Correct: `parser_shape` omits `type`, `choices`, `const`, `metavar` and `help`, so "
        "a behaviour-bearing change to any of them leaves every serialized line, count and "
        "digest identical. This is not a new finding - it duplicates an OPEN M3.5b polish "
        "row that already owns the serializer's field set - and opening a second record "
        "would split the fix across two registers. The unit-local premise it threatens, "
        "`no production source changes`, is independently pinned harder than gate 7 could: "
        "battery D04 runs `git diff --exit-code 6fb4d92 -- src`, which fails on any byte of "
        "`cli.py`. Route to the existing polish row; nothing is unprotected meanwhile.",
    ),
    "Y08": (
        "DEFERRED",
        "Correct: the extractor yields only fenced blocks whose bare info string is one of "
        "four shell labels, so inline code, indented code, `text` fences, HTML blocks and "
        "attributed fences are all outside the corpus, and a stale invocation on any of "
        "them leaves rc 0. The gate and its corpus are M3.5b's, not this unit's - "
        "`m3u5b-doc-parse.py` - and widening the corpus is a change to that unit's "
        "instrument with its own controls to re-derive. This unit ships no new command "
        "prose, so the exposure it adds is zero. Route to the polish register against the "
        "M3.5b doc-parser row; Y15 carries the adjacent prose-scanning gap.",
    ),
    "Y09": (
        "SCOPED",
        "Correct and it is Y01 instantiated on two specific tests: name, lifecycle call "
        "count and RETAIN classification all survive a weakening from exact payload "
        "equality to key presence. It does not land against shipped state - both "
        "assertions are the exact-equality form today - and the battery's D24 re-runs both "
        "tests by name rather than trusting the census row. D24's wording claims an `exact "
        "durable record`, which is the overreach; the record is durable against DELETION "
        "and not against WEAKENING. Mutation coverage is Y01's residual and belongs to the "
        "polish register.",
    ),
    "Y10": (
        "SCOPED",
        "Correct in principle - source bytes do not determine a runtime callable's "
        "defaults or binding, and the three P06 spans plus D26's `callable` check all pass "
        "under `__kwdefaults__` mutation - and DISCHARGED against shipped state by an "
        "obligation the attack did not see. The reproduction writes to "
        "`src/cement_runtime/__init__.py`, and battery D04 runs "
        "`git diff --exit-code 6fb4d92 -- src`: any byte in the whole tree, that file "
        "included, fails it. The gap is therefore real for D25's WORDING, which claims the "
        "spans prove the method unchanged, and closed in fact for this unit, which changes "
        "no production source at all. A runtime signature/identity pin is the right "
        "instrument for a unit that DOES edit `src`; that is M3.6a2, which deletes both "
        "methods and needs the inverse pin.",
    ),
    "Y11": (
        "SCOPED",
        "Correct: `callable(getattr(System, name, None))` accepts a variadic stub that "
        "always raises, an alias to an unrelated method, or a changed-default wrapper, so "
        "the pin admits a name-shaped tombstone. It does not land against shipped state for "
        "the same reason as Y10 - D04's whole-`src` byte diff forbids the rebinding the "
        "reproduction performs, and the repro's own monkeypatch lives inside one test "
        "process rather than in shipped bytes. D26's wording, `still ship and remain "
        "reachable`, outruns `callable`; reachability needs one executed success path. "
        "That obligation matters most at the moment the methods are DELETED, so M3.6a2 "
        "inherits it as the pin that must flip from passing to failing.",
    ),
    "Y12": (
        "SCOPED",
        "Correct that a six-file allowlist is not the complement of production source - it "
        "omits `__init__.py`, `cli.py`, `function.py` and `json_value.py`, each able to "
        "alter exports, parsing or match evaluation - and fully discharged here. D27 "
        "inherits M3.5b's six-module freeze and this unit does not rely on it: battery D04 "
        "pins the ENTIRE `src` tree byte-for-byte against 6fb4d92, so both reproduction "
        "edits fail immediately. The correct record is that D27 is a borrowed pin with a "
        "known-partial domain, retained for continuity, while D04 is the one this unit's "
        "no-production-source premise actually rests on.",
    ),
    "Y13": (
        "SCOPED",
        "Confirmed at the source and correct: battery D06 orders resolve before propose by "
        "`call.lineno` alone (`resolve_line < line < propose_line`), so wrapping the block "
        "in `if False:` preserves every line relation while nothing executes. It does not "
        "land against shipped state - the four sites run under gate 1 and their assertions "
        "would fail if the resolve never ran, since `resolution` would be unbound - which "
        "is the dominance evidence the lexical check omits but the suite supplies. The "
        "wording is the defect: D06 claims execution order and checks source order. A "
        "runtime execution count per site is the right instrument and it is the same spy "
        "gate 4 already implements, so A19's repair is where it should be built. Recorded "
        "against MISS-GUARDED 0 today: the population is empty post-migration, so the "
        "obligation is historical for this unit and live for M3.6a2.",
    ),
    "Y14": (
        "SCOPED",
        "Correct: five/two are ROUTE totals and cannot preserve a locus mapping, and the "
        "two byte-identical A signatures make the described collapse invisible in the final "
        "ledger. It does not land against shipped state - D18's five propose and two "
        "resolve calls sit at the seven original loci, and the demo's per-act assertions "
        "bind each to its own narrative step - but the obligation as written is an "
        "aggregate and would ratify the swap. The qualified original-locus -> replacement "
        "mapping the attack asks for is cheap and belongs with D18's own wording; owner is "
        "the polish register, since M3.6a2 rewrites the walkthrough and would inherit any "
        "mapping written now.",
    ),
    "Y15": (
        "SCOPED",
        "Correct: transcript regeneration removes the two known lines and nothing scans "
        "shipped prose for the retired event vocabulary, so the same sentence in another "
        "document leaves every gate green. It does not land against shipped state - the "
        "event still EXISTS in this unit, since production source is unchanged, so naming "
        "it elsewhere would be accurate rather than stale. The absence obligation only "
        "becomes true at M3.6a2, where `request.resolved_by_artifact` and "
        "`request.fallback_failed` are deleted; a complement-defined prose scan is that "
        "unit's gate and would be asserting a falsehood if written here. D23's scope is "
        "correctly the pinned transcript.",
    ),
}


def main(argv: list[str]) -> int:
    check = argv[1:] == ["--check"]
    raw = TABLE.read_bytes()
    payload = json.loads(raw)
    rows = payload["rows"]
    ids = [row["id"] for row in rows]

    if (json.dumps(payload, **DUMP) + "\n").encode() != raw:
        print("table is not in canonical dump form", file=sys.stderr)
        return 1

    if set(ids) != set(RULINGS):
        missing = sorted(set(ids) - set(RULINGS))
        extra = sorted(set(RULINGS) - set(ids))
        print(f"undisposed rows: {missing}\nunknown rulings: {extra}", file=sys.stderr)
        return 1

    stale = [
        row["id"]
        for row in rows
        if (row["disposition"], row["main_note"]) != RULINGS[row["id"]]
    ]
    if check:
        if stale:
            print(f"out of sync: {stale}", file=sys.stderr)
            return 1
        print(f"IN SYNC: {len(rows)} rows disposed")
        return 0

    for row in rows:
        row["disposition"], row["main_note"] = RULINGS[row["id"]]
    TABLE.write_text(json.dumps(payload, **DUMP) + "\n", encoding="utf-8")
    print(f"DISPOSED: {len(rows)} rows, {len(stale)} changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
