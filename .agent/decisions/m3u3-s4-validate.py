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

import argparse
import json
from pathlib import Path
import sys

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


def grade(kind: str, path: Path) -> int:
    seed, fields, exempt = KINDS[kind]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"UNREADABLE {path}: {error}", file=sys.stderr)
        return 1

    problems: list[str] = []
    if document.get("kind") != kind:
        problems.append(f"kind must be {kind!r}, found {document.get('kind')!r}")
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        print(f"NO ROWS in {path}", file=sys.stderr)
        return 1

    identifiers = [row.get("id") for row in rows]
    if len(set(identifiers)) != len(identifiers):
        problems.append("duplicate row ids")
    missing = sorted(set(seed) - set(identifiers))
    if missing:
        problems.append(f"seeded rows absent (the seed is a floor): {missing}")
    for identifier in identifiers:
        if identifier not in seed and not str(identifier).startswith("X"):
            problems.append(f"unseeded row {identifier!r} must take an X-prefixed id")

    unknown = 0
    for row in rows:
        for field in fields:
            if field not in row:
                problems.append(f"{row.get('id')}: field {field!r} absent")
                unknown += 1
            elif row[field] in UNFILLED:
                unknown += 1
        for field in row:
            if field not in fields and field not in exempt:
                problems.append(f"{row.get('id')}: unexpected field {field!r}")

    print(f"kind={kind} rows={len(rows)} seeded={len(seed)} extensions={len(rows) - len(seed)}")
    print(f"EXEMPT-COLUMNS (MAIN fills, not graded here): {list(exempt)}")
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(f"UNKNOWN-CELLS: {unknown}")
    print("PASS" if unknown == 0 and not problems else "FAIL")
    return 0 if unknown == 0 and not problems else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=sorted(KINDS))
    parser.add_argument("--emit-stub", action="store_true", help="print the all-unknown skeleton")
    parser.add_argument("path", nargs="?")
    arguments = parser.parse_args(argv)

    seed, fields, _ = KINDS[arguments.kind]
    if arguments.emit_stub:
        rows = [
            {field: (identifier if field == "id" else subject if field == "subject" else "unknown")
             for field in fields}
            for identifier, subject in seed.items()
        ]
        print(json.dumps({"kind": arguments.kind, "rows": rows}, indent=2))
        return 0
    if not arguments.path:
        parser.error("a path is required unless --emit-stub is given")
    return grade(arguments.kind, Path(arguments.path))


if __name__ == "__main__":
    raise SystemExit(main())
