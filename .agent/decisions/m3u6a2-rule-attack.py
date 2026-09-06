#!/usr/bin/env python3
"""MAIN's S4 batch ruling over M3.6a2's two wave-2 tables, as an idempotent patcher.

Rules BOTH committed tables through one script because section 6's gate 6 names one command:
`m3u6a2-attack.json` (30 rows, MAIN owns `disposition` + `main_note`) and
`m3u6a2-verdicts.json` (66 rows, MAIN owns `main_verdict` + `action`). The wave validator
EXEMPTS those four columns, so a clean teammate grade says nothing about them — the ruling is a
separate deliverable and this file is it.

Contract: assert the id set matches each table EXACTLY, rewrite under the table's own
serialization (`indent=2, ensure_ascii=False`, trailing newline, both measured), derive every
counter from FINAL state, and report `no-op` on rerun. `--check` is gate 6. Run it twice before
trusting it once: an emitter that computes totals before overlaying rulings is non-idempotent.

The 23 rows the teammate graded `divergent=no` are ruled as a CLASS, not row by row: a
non-divergent row is one whose reading matched the contract, so ratifying the class is the
ruling the split already encodes. They stay named in NONDIVERGENT so a row changing class fails
loudly rather than inheriting a verdict it was never given.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --- attack table: id -> (disposition, main_note) -------------------------------------------
# disposition vocabulary: accept | accept-in-part | cleared. `cleared` mirrors the teammate's own
# self-clearing rows, which are evidence, not omissions.
ATTACK: dict[str, tuple[str, str]] = {
    "A24": ("accept-in-part", (
        "RULED FIRST because it decides whether gate 3's expectation stands. NOT an added gate: "
        "section 6's pin is the numbered LIST and C06 added no entry, so no closure claim is "
        "unbuilt — and none existed, since S2 claimed gate 1 alone while gate 3 was in fact RED. "
        "The substance holds: a gate's identity is (command, accepted language), so C07 records "
        "that an INSTRUMENT change voids prior runs of THAT gate and requires the full numbered "
        "list to rerun at the next closure claim. Gate 3's post-C06 expectation stands.")),
    "A01": ("accept", (
        "L01 amended: post-state `System` method-name set == the `da70a56` set minus exactly the "
        "five deleted names. A text predicate grades spelling; the set subtraction grades "
        "subtraction. Same family as the project's token-absence rule.")),
    "A02": ("cleared", "L04's two halves already reject a `**kwargs` tail; no amendment."),
    "A03": ("accept", (
        "L05 amended with an AST SHAPE pin, which is what a rename cannot satisfy: `_now`'s "
        "comparator is exactly `now > _MAX_SQLITE_INTEGER` with no BinOp, and `__init__` binds no "
        "attribute derived from a lease parameter. Measured baseline: "
        "`now > _MAX_SQLITE_INTEGER - self._lease_us`.")),
    "A04": ("cleared", "Audit confirms no surviving `_now` consumer derives a deadline; 2.1 stands."),
    "A05": ("accept", (
        "L07 amended: the `generating` row is FABRICATED legacy state, labelled as such, and the "
        "probe asserts it exists at `status='generating'` BEFORE `revise_operation`. A zero-row "
        "UPDATE raises nothing, so an unguarded preservation probe is green-and-empty.")),
    "A06": ("accept", (
        "L08 amended to bind VALUES read from persisted `events.payload_json`: `previous_revision` "
        "== the pre-revision integer, `policy_hash` == the canonical policy digest, `revised_by` "
        "== the supplied actor. A key-set assertion passes with all three values wrong.")),
    "A07": ("accept-in-part", (
        "The general dynamic-reach problem is undecidable; the bounded pin is exact and MAIN "
        "measured it: `src/` contains ZERO getattr/setattr/hasattr/delattr calls whose name "
        "argument is not a string Constant. Gate 4 pins that count at 0, which rejects "
        "`getattr(self, '_out' + 'come')` by construction. L09 amended.")),
    "A08": ("accept", (
        "L12 amended: each package export resolves in `cement_runtime` to the SAME object as in "
        "`cement_runtime.models` (identity, not `__all__` text), which an aliasing re-export "
        "breaks. See also X06/X34 — the export count is SIX, not seven.")),
    "A09": ("accept", (
        "L11 amended to TOTAL accounting: every `_event` call's `kind` must be one of the three "
        "ruled AST forms and must expand non-empty; an unsupported form FAILS rather than being "
        "skipped. Set equality alone stays green while a fourth form ships a new kind.")),
    "A10": ("accept", (
        "New obligation L31. C05 made ambiguity quarantine a REMOVED BEHAVIOUR and section 2.1 "
        "gave the clock widening its own obligation; the behaviour removal must have one too, or "
        "the only pin is a vocabulary spelling. L31 pins the artifact-state non-mutation.")),
    "A11": ("cleared", "L12 is a unit-boundary pin protecting M3.6a3's measured start; grounds stated."),
    "A12": ("accept", (
        "L13 amended: ownership binds to the NEAREST lexical FunctionDef and the pin compares the "
        "exact multiset {owner: count} plus owner KIND. Carries V17's repair of C04's own error.")),
    "A13": ("accept", (
        "L15 amended: the span is `min(decorator lineno, def lineno)..end_lineno` and the baseline "
        "decorator vector (empty for all five) is asserted. `FunctionDef.lineno` points at `def`, "
        "so `@staticmethod` changes runtime binding while every compared byte is identical.")),
    "A14": ("accept", (
        "L16 amended with the reject round trip. `_write_proposal_request_status` has a dedicated "
        "rejection branch that the accept-only probe never executes, so the contract's sentence "
        "`this is the probe that proves it` was false for half the helper.")),
    "A15": ("accept", (
        "L18 was self-contradictory: `revise_operation` is both a surviving `_now` caller and an "
        "L07 edit target. Replaced by an exact CALL-SITE predicate — 12 surviving caller methods, "
        "each with exactly one `self._now()` call. MAIN measured 15 callers at base, minus "
        "`handle`, `_fail_generation`, `request_status`.")),
    "A16": ("accept-in-part", (
        "L19-L22 gain an explicit MECHANICAL/RULED split: the mechanical half is asserted by the "
        "battery, the semantic half is MAIN's recorded ruling at closure. A token predicate "
        "accepts `Never call propose or review; use the legacy lifecycle dispatcher`, so claiming "
        "a test decides replacement prose would be a guarantee-vs-claim gap.")),
    "A17": ("accept", (
        "L23 amended: each of the 14 working-tree pins keeps its assertion body byte-identical to "
        "its `da70a56` blob unless section 8 authorizes the delta, and every authorized delta is "
        "enumerated. Otherwise 'all pins green' is satisfiable by weakening the pins.")),
    "A18": ("accept", (
        "L24 was UNSATISFIABLE under its literal reading and MAIN reproduced the collision: D25 "
        "requires >=2 shipped paragraphs containing `request row stays internal` and measurement "
        "finds exactly 2 (README + architecture), both matched by the census `\\brequests?\\b`. "
        "L24 now binds a NAMED token subset and requires grounds per surviving generic hit.")),
    "A19": ("accept", (
        "L26 amended: the three figures are DERIVED from git object `3b7769b` every run, not "
        "recorded as prose. A retirement that turns a computation into a transcribed literal "
        "leaves the claim gate-unchecked, and the only recomputers are the frames being retired.")),
    "A20": ("cleared", "Inverted D01 keeps two non-overlapping CLI subproperties; retention justified."),
    "A21": ("accept", (
        "L29 amended (merges X14): the control needs an IMMUTABLE synthetic P06 source fixture as "
        "the positive plus a same-origin preserved-method near-miss as the negative, because L26 "
        "empties the live positive set in the same unit. A detector returning no P06 rows and a "
        "working one are otherwise indistinguishable post-retirement.")),
    "A22": ("accept-in-part", (
        "Gate 3's COMMAND is unchanged — amending it would invalidate section 6's pins. The "
        "independent oracle moves into the CONTRACT instead: L24 states the owned-hit expectation "
        "in prose MAIN authored, so `--emit` can no longer bless a bad post-state without "
        "contradicting a number the contract carries. `--emit` is additionally forbidden after "
        "S3's re-emission except through a numbered correction (C07). Y05 and Y06 harden the "
        "validator's own totals and provenance.")),
    "A23": ("accept", (
        "Section 7 gains the fixed grounded-exclusion catalogue: L23's D22b (git-only), L25's "
        "post-repair D15a, L26's three historical figures, and BOTH halves of L30's D16. D22c is "
        "MIXED and gets live rows despite the census label. Every exclusion prints on the control "
        "line; cost never grounds one, insensitivity does.")),
    "Y01": ("accept", (
        "MAIN re-measured: 19 static `_event` calls (16 Constant, 2 IfExp, 1 JoinedStr); the "
        "textual `_event(` count is 20 because the DEFINITION line matches. Post-state static "
        "count is 14. C05 was a correction written to fix structural counts and carried one — "
        "corrected by C08. The 16-kind SET is unaffected: it was derived per call site.")),
    "Y02": ("accept", (
        "Gate 2's instrument is repaired (command unchanged): coverage binds to test ids "
        "DISCOVERED by `unittest.defaultTestLoader`, skip decorators/calls must be zero at "
        "closure, and each obligation needs >=1 non-tautological assertion or expected exception. "
        "The literal `SEED STUB` predicate graded 30 `pass` bodies clean.")),
    "Y03": ("accept", (
        "Same repair as Y02: a nested `test_l01_ghost` unittest never discovers cannot count as "
        "coverage. Bind coverage to discovered ids, then map back to AST bodies.")),
    "Y04": ("accept", (
        "`CORRECTION-BIND` requires explicit `binds L<nn>` / `binds GATE <n>` / `binds SECTION "
        "<n>` grammar validated against the contract's real id sets. M3.6a1 already paid for the "
        "opposite failure — illustrative ids parsed as bindings.")),
    "Y05": ("accept", (
        "Gate 3's validator derives every `totals` field from the validated row arrays instead of "
        "printing the committed numbers. Four false totals printed beside `RESULT: PASS`.")),
    "Y06": ("accept", (
        "Gate 3's validator authenticates `unit`, `head`, `excluded` and the counting convention "
        "against fresh emission. A credential not bound to unit and state is not a credential.")),
}

# --- verdicts table -------------------------------------------------------------------------
# main_verdict vocabulary: accept | accept-amend | ratified-nondivergent.
NONDIVERGENT = frozenset((
    "V04", "V06", "V08", "V11", "V13", "V18", "V19", "V20", "V21", "V28",
    "X07", "X10", "X11", "X13", "X15", "X17", "X19", "X22", "X23", "X27", "X28", "X29", "X32",
))
NONDIVERGENT_RULING = (
    "ratified-nondivergent",
    "Reading matches the contract; row becomes conformance corpus for the phase-2 suite.",
)

VERDICTS: dict[str, tuple[str, str]] = {
    "V01": ("accept", "Strongest public-surface reading adopted; L01 also gains A01's set subtraction."),
    "V02": ("accept-amend", "L03 binds ATTRIBUTES and DEFINITIONS: zero FunctionDef named any of the three at any scope. Binding counts follow from L09."),
    "V03": ("accept", "L04 binds the class only. CPython's message is recorded diagnostically, never pinned — a paraphrased interpreter string is the project's recorded defect shape."),
    "V05": ("accept", "Raw bytes over git-tracked `src/`; git-tracked scope excludes `__pycache__`."),
    "V07": ("accept-amend", "L06 additionally pins the POSITIVE replacement text `clock must return a signed 64-bit microsecond timestamp`. MAIN authors it, so it is not a diff-blind paraphrase, and a forbidden-substring predicate alone cannot see a silent re-wording."),
    "V09": ("accept", "Fabricated legacy row through `Store.transaction`, labelled, with A05's precondition control."),
    "V10": ("accept", "Semantic multi-spelling static-SQL scan; runtime-composed SQL stays a stated blind spot closed by X19's authorizer observation."),
    "V12": ("accept", "Word occurrences over tracked textual `src/`; `handler`/`unhandled` excluded. MAIN measured baseline 1."),
    "V14": ("accept-amend", "The 16-kind SET stands. The CALL count is 19 at base and 14 post-state, reported separately and never as a completeness control at 20 (Y01/C08)."),
    "V15": ("accept", "Invert the `test_system.py` tail: both artifacts stay `promoted`, ambiguity event count 0. Feeds new L31."),
    "V16": ("accept", "Base object `da70a56`; `__all__` compared as the parsed ordered list. Note `Outcome` is absent from it (X06)."),
    "V17": ("accept", "CORRECTS C04's own text. Measured: `_proposal_bindings` and `_write_proposal_request_status` are module-level, `_persist_proposal` is a `System` method. A class-body-only scan sees ONE surviving site, not zero."),
    "V22": ("accept-amend", "Same positive text pin as V07; the non-callable path keeps `ValidationError('clock_us must be callable')`."),
    "V23": ("accept", "Poll-state table defined semantically (Status-headed table carrying >=1 frozen lifecycle state). Token bans cover code fences: all of it is shipped human-facing prose."),
    "V24": ("accept-amend", "MAIN rules the implicit question YES: items 1-3 must contain `propose` >=1 AND `review` >=1. Steps identified structurally under the Contract H2."),
    "V25": ("accept-amend", "Token set adopted with one carve-out: `request_id` SURVIVES (X16). `\\brequests?\\b` already excludes it, since `_` is a word character."),
    "V26": ("accept", "The three-part replacement is adopted: application-owned idempotency key, at-most-once source invocation per call, enumerate-pending recovery rather than retry."),
    "V27": ("accept", "Contextual-zero adopted; L24 now names the token subset and requires grounds per surviving generic hit (A18)."),
    "V29": ("accept", "Retire = stop reading the deleted working-tree span, keep a LIVE historical check against `3b7769b` (A19). D01 inversion pairs absence with identity/positive controls."),
    "V30": ("accept-amend", "Adopt the `_is_freeze(segment)` seam; the fixture is the immutable synthetic P06 source of A21/X14, not a live frame. Live `_freezes()` stays 4; self-test goes 8/8."),
    "X01": ("accept", "L02 binds the `System` attribute; `_ProposalBinding.request_status` is a different subject and survives under L15."),
    "X02": ("accept", "L09's literal `zero occurrences` for `request_status` is FALSE-BY-CONSTRUCTION against L15. MAIN measured 8 NAME tokens at base; deleting the method removes line 1546 alone, leaving SEVEN proposal-plumbing identifiers. L09 corrected by C09."),
    "X03": ("accept", "Raw closure on `generation_lease_seconds` = 0 across tracked `src/`; `inspect.signature` cannot see a dead literal."),
    "X04": ("accept", "Raw closure on `invalidated_generators` = 0. MAIN measured raw 3 against 2 NAME tokens — the contract's `2` was the token count, and the third occurrence is the payload key STRING."),
    "X05": ("accept", "Fail closed on any unsupported `kind` form (A09), so an unrecognized call cannot be silently skipped into a correct-looking set."),
    "X06": ("accept", "Section 1 corrected by C10: SIX package exports, SEVEN definitions. `Outcome` is a models-only alias and was never in `__all__`."),
    "X08": ("accept", "See A15; L18 replaced by the exact surviving call-site set."),
    "X09": ("accept", "L19 is conjunctive: the Library API region must still teach both proposal routes, review and `proposal_id`. Deleting the lifecycle section is necessary, never sufficient."),
    "X12": ("accept", "D01 inversion pairs with `System.__module__` and callable `propose`, and retains its parser leaf-set complement, so an empty dummy class cannot satisfy the negatives."),
    "X14": ("accept", "Merged into L29 as the negative half of A21's control: a same-origin preserved-method near-miss must stay OUT, or over-reporting satisfies the positive."),
    "X16": ("accept", "L21 gains a RETENTION clause: the `\"request_id\"` JSON wire key stays, described as an opaque per-call tracing identifier. `CandidateRequest.request_id` is M3.6a3's, and byte-frozen `propose` still constructs it."),
    "X18": ("accept", "L24's scanner coverage is itself pinned: the `DOCS` tuple must equal the tracked human-facing Markdown set (README + docs/ + examples/), so a new document cannot become an unscanned home for a deleted claim."),
    "X20": ("accept", "L13 pins word occurrences beside hit lines with per-line multiplicity 1; line equality alone permits packing a second reference onto an existing line."),
    "X21": ("accept", "All four P06 test identities stay DISCOVERABLE post-retirement; one aggregate replacement erases three independent tripwire records."),
    "X24": ("accept", "Tokenize NAME equality, expected vector {handle:0, request_status:7, _outcome:0, _fail_generation:0, _request_revision_is_current:0, _lease_us:0}. MAIN re-measured every base count."),
    "X25": ("accept", "L19's lease ban is context-classed: generation/request lease claims go, and the two truthful `snapshot is not a lease` statements stay. A global word ban would delete correct prose to reach zero."),
    "X26": ("accept", "L21 preserves `System.propose`'s failure contract (`CandidateSourceError` + a concrete no-write observable) while `fallback_failed` reaches 0."),
    "X30": ("accept", "SQL-constant derivation joins line and word counts as L13's third instrument: verbs plus owners, excluding comments and docstrings."),
    "X31": ("accept", "`_bounded_int` survives with 15 calls and 1 definition — MAIN measured 16 calls at base, exactly one of them the lease validation. Inlining the helper would widen the unit past its deletion set."),
    "X33": ("accept-amend", "Contract wording corrected by C11, history NOT rewritten: `before every other edit` becomes `no later than the first commit that adds a file under tests/ or examples/`. Git has no intra-commit ordering, and `7cfc748` satisfies the practical reading."),
    "X34": ("accept", "Seven definitions survive in `models.py`; six are package exports; all seven leave `system.py`. This is the executable state M3.6a3 inherits."),
    "X35": ("accept", "L16 binds the CONFIRMED variant: `source_kind='confirmed'`, `artifact_id` NULL, `proposal_id` bound to the reviewed proposal, `example_id` bound to the ReviewResult."),
    "X36": ("accept", "L15 asserts definition CARDINALITY 1 per preserved name BEFORE hashing; a name-keyed span map silently drops a duplicate definition and compares the wrong one."),
}


def _load(name: str) -> tuple[Path, dict]:
    path = HERE / name
    return path, json.loads(path.read_text())


def _dump(path: Path, doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode()


def _rule(doc: dict, kind: str) -> None:
    """Overlay rulings, then derive totals FROM FINAL STATE (a pre-overlay total is non-idempotent)."""
    if kind == "attack":
        ids = {r["id"] for r in doc["rows"]}
        if ids != set(ATTACK):
            raise SystemExit(f"attack id set drift: table-only={sorted(ids - set(ATTACK))} ruling-only={sorted(set(ATTACK) - ids)}")
        for row in doc["rows"]:
            row["disposition"], row["main_note"] = ATTACK[row["id"]]
        doc["ruling"] = {
            "session": "S4",
            "rows": len(doc["rows"]),
            "by_disposition": _tally(doc["rows"], "disposition"),
            "by_severity": _tally(doc["rows"], "severity"),
        }
        return

    ids = {r["id"] for r in doc["rows"]}
    expected = set(VERDICTS) | set(NONDIVERGENT)
    if ids != expected:
        raise SystemExit(f"verdicts id set drift: table-only={sorted(ids - expected)} ruling-only={sorted(expected - ids)}")
    overlap = set(VERDICTS) & set(NONDIVERGENT)
    if overlap:
        raise SystemExit(f"a row cannot be both individually ruled and class-ruled: {sorted(overlap)}")
    for row in doc["rows"]:
        declared = row["id"] in NONDIVERGENT
        if declared != (row["divergent"] == "no"):
            raise SystemExit(f"{row['id']}: divergent={row['divergent']} contradicts its ruling class")
        row["main_verdict"], row["action"] = NONDIVERGENT_RULING if declared else VERDICTS[row["id"]]
    doc["ruling"] = {
        "session": "S4",
        "rows": len(doc["rows"]),
        "by_verdict": _tally(doc["rows"], "main_verdict"),
        "divergent": sum(1 for r in doc["rows"] if r["divergent"] == "yes"),
    }


def _tally(rows: list[dict], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[row[field]] = out.get(row[field], 0) + 1
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="gate 6: fail when any table is unruled or drifted")
    args = parser.parse_args(argv)

    status = 0
    for name, kind in (("m3u6a2-attack.json", "attack"), ("m3u6a2-verdicts.json", "verdicts")):
        path, doc = _load(name)
        before = path.read_bytes()
        _rule(doc, kind)
        after = _dump(path, doc)
        if args.check:
            state = "in-sync" if after == before else "OUT-OF-SYNC"
            print(f"{name}: {state} {doc['ruling']}")
            status |= 0 if after == before else 1
        else:
            print(f"{name}: {'no-op' if after == before else 'applied'} {doc['ruling']}")
            if after != before:
                path.write_bytes(after)
    return status


if __name__ == "__main__":
    sys.exit(main())
