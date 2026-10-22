#!/usr/bin/env python
"""Structural grader for M3.3 S4's two teammate deliverables.

    uv run python .agent/decisions/m3u3-s4-validate.py --kind window .agent/decisions/m3u3-window.json
    uv run python .agent/decisions/m3u3-s4-validate.py --kind attack .agent/decisions/m3u3-s4-attack.json

Grades BOTH ways at seed: the all-`unknown` skeleton exits nonzero, a filled artifact exits 0. The
seeded row ids are a FLOOR, never a cap - an extension row takes an id prefixed `X` and is graded
exactly like a seeded one.

Exempt columns are MAIN's own to fill and are PRINTED on every run, because a teammate's
completeness and MAIN's ruling are two different deliverables and only one of them is graded here.
"""

from __future__ import annotations

from wave_validate import FieldTables


UNFILLED = ("unknown", "", None, [], {})

WINDOW_SEED = {
    "W01": "direct submit_proposal, commit durably succeeds then raises: caller-visible class + exact message",
    "W02": "direct: requests/proposals/events row deltas measured AFTER the raising commit returns",
    "W03": "direct: does the caller receive any proposal id, and is the minted id discoverable at all",
    "W04": "source propose, same injected commit: class, message and the same three row deltas",
    "W05": "recovery route: does system.proposals(partition, status='pending') surface the orphan row",
    "W06": "recovery route: does get_proposal(partition, id) resolve the orphan once its id is known",
    "W07": "recovery route: can an operator bind the orphan proposal back to its requests row",
    "W08": "CONTROL, commit that does not raise: the same observables on an ordinary success",
    "W09": "pre-commit interior write failure: row deltas, commit count, rollback count (re-derive D15's matrix)",
    "W10": "is the window submission-specific, or does System.handle exhibit it identically",
    "W11": "does a non-submission writer (register_operation or review) exhibit it identically",
    "W12": "any observable separating commit-raised-after-durability from commit-raised-before-durability",
}
WINDOW_FIELDS = ("id", "subject", "method", "observed", "verdict", "reproduction")
WINDOW_EXEMPT = ("main_ruling",)

ATTACK_SEED = {
    "A01": "R06/R07 scoping: an evasion where 'submission-attributable' is stated but the prose still overclaims",
    "A02": "R06/R07 window: a commit-uncertainty publication a reader cannot act on (no recovery route reachable)",
    "A03": "R06/R07 probe: a committed probe that passes whether or not the window exists",
    "A04": "Z02 AST probe: a split writer that keeps all three writes textually inside _persist_proposal yet is not the sole owner",
    "A05": "Z02 AST probe: a probe keyed on helper NAME that a rename defeats while ownership is unchanged",
    "A06": "Z02 mutant: a one-transaction two-helper split the prescribed AST probe would still pass",
    "A07": "Z03 ABI: an annotation weakening that typing.get_type_hints reports identically",
    "A08": "Z03 ABI: a signature change the prescribed test does not read (order, default, kind, or *args)",
    "A09": "Z03 mutant: an ABI mutant that a string-compare-only annotation test lets survive",
    "A10": "Z05 footprint: a live-schema derivation that still omits a table SQLite reports differently",
    "A11": "Z05 footprint: an exclusion rule that drops an application table along with the SQLite-owned ones",
    "A12": "Z05 mutant: a write the derived footprint still cannot see",
    "A13": "Z06 SQL spy: a normalization that misses a forbidden table (quoting, schema prefix, whitespace, comment)",
    "A14": "Z06 SQL spy: a substring match that FALSELY fires on a permitted statement (false positive cost)",
    "A15": "Z06 spy installation: a read path the Connection.execute override never records (executemany, cursor, executescript)",
    "A16": "Z06 mutant: a forbidden read the prescribed instrument still admits",
    "A17": "cross-check: any S4 pin whose deletion the S4 mutant corpus would not detect",
    "A18": "cross-check: any S4 pin that forces PRODUCTION code to change to satisfy an exact-count gate",
}
ATTACK_FIELDS = ("id", "subject", "evasion", "concrete_mutant", "severity", "reproduction")
ATTACK_EXEMPT = ("main_ruling",)

KINDS = {
    "window": (WINDOW_SEED, WINDOW_FIELDS, WINDOW_EXEMPT),
    "attack": (ATTACK_SEED, ATTACK_FIELDS, ATTACK_EXEMPT),
}


ENGINE = FieldTables(
    KINDS=KINDS,
    UNFILLED=UNFILLED,
    documentation=__doc__,
    source_path=__file__
)
grade = ENGINE.grade
main = ENGINE.main

if __name__ == '__main__':
    raise SystemExit(main())
