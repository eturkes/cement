#!/usr/bin/env python3
"""Grade M3.6a1's contract-attack table, `m3u6a1-attack.json`.

Two lens families, one table:

* `A<nn>` — CLAIM ATTACK. The contract asserts something; the lens tries to
  falsify it against the shipped repo. Nine consecutive units have closed on
  claim defects in MAIN's own text, so this is the high-yield family.
* `Y<nn>` — EVASION MATRIX. For each acceptance predicate and each gate, the
  lens asks how an artifact could satisfy the predicate's LETTER while leaving
  the obligation unforced. Diff-blind: it needs the acceptance checks, never the
  diff.

`--emit-seed` is the seed's SINGLE SOURCE OF TRUTH and carries the row SUBJECTS,
because seeding a deliverable does not make it resumable unless each row already
names what it is about. The seed is a FLOOR: adding rows is the format working,
so every extension row keeps its family prefix and is graded identically.

MAIN owns `disposition` and `main_note`; both are exempt from unknown-cell
grading and are filled by an idempotent patcher, never by the teammate.

Usage:
    m3u6a1-attack-validate.py --emit-seed [> .agent/decisions/m3u6a1-attack.json]
    m3u6a1-attack-validate.py [--table PATH] [--root DIR]
    m3u6a1-attack-validate.py --self-test
"""

from __future__ import annotations

import pathlib
import re
import sys

from wave_validate import AttackTable

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT_NAME = "m3u6a1-contract.md"
TABLE_RELPATH = pathlib.Path(".agent") / "decisions" / "m3u6a1-attack.json"

UNKNOWN = "unknown"
TEAMMATE_FIELDS = ("section", "locus", "claim", "attack", "reproduction", "severity", "verdict")
MAIN_FIELDS = ("disposition", "main_note")
SEVERITIES = ("blocking", "material", "minor", "cleared")
MIN_ATTACK_CHARS = 120
MIN_REPRO_CHARS = 40

OBLIGATION = re.compile(r"^- \*\*(D\d+[a-z]?)\*\*")
CORRECTION = re.compile(r"^- \*\*(C\d+)\b")
EXTRA_ANCHORS = ("P1", "P2", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "S3", "S5", "S7", "S8", "S11")

# Row subjects. Each names a LOCUS the lens must attack; the lens supplies the
# claim, the attack and the reproduction. Extension rows are expected.
SEED: tuple[tuple[str, str, str], ...] = (
    ("A01", "D01", "gate 2's `SURVIVING-MIGRATE: 0` as a completeness predicate"),
    ("A02", "D03", "the RETAIN set pinned `by name and by call count`"),
    ("A03", "D05", "the enumerated surviving-consumer set"),
    ("A04", "D06", "`resolve` asserting `passed` true and `matched` false as the verified-miss spelling"),
    ("A05", "D07", "keeping `propose` at a MISS-GUARDED site to preserve row state"),
    ("A06", "D08", "`no FACTORY site gains a resolve call` as a negative obligation"),
    ("A07", "D12", "removing `_promote_scope`'s `prefix` as observable through D14"),
    ("A08", "D14", "`no migrated helper retains an unread parameter`, checked by AST"),
    ("A09", "D16", "the replay credential: script plus clean base reproduces the shipped tree"),
    ("A10", "D19", "moving the function-set checkpoint so Acts 2 and 3 answer through `resolve`"),
    ("A11", "D21", "the demo's re-derived `assert` verdict count"),
    ("A12", "D22", "the regenerated transcript and its two mask-count assertions"),
    ("A13", "D28", "`gate 1 stays green at every commit, never only at the last one`"),
    ("A14", "P1", "row-state equivalence with EXACTLY ONE differing cell"),
    ("A15", "P2", "`resolve` matching once the function set is promoted"),
    ("A16", "S3", "the four shape classes and their site counts"),
    ("A17", "C02", "recovering the request row through `(SELECT request_id FROM proposals WHERE id = ?)`"),
    ("A18", "C11", "three denominators: 26 definitions, 28 call sites, 45 surviving sites"),
    ("Y01", "G1", "a suite that stays green because a re-based test asserts less"),
    ("Y02", "G2", "a census reporting zero because its target population shrank"),
    ("Y03", "G3", "`IN-SYNC` as a ruling-integrity claim"),
    ("Y04", "G4", "shape attribution `RESULT: PASS` after the population it attributes has moved"),
    ("Y05", "G5", "the premise probe reproducing P1 and P2 against a tree they no longer describe"),
    ("Y06", "G6", "`no-op` on a second surgery run as an idempotence credential"),
    ("Y07", "G7", "the parser census and `parser_shape` digest asserted unchanged"),
    ("Y08", "G8", "doc-parse rc 0 over the shipped command blocks"),
    ("Y09", "D24", "the two `{\"request_id\": ...}` payload pins as the record of P1's sole difference"),
    ("Y10", "D25", "the `System.handle` byte-span freeze and its three slicing conventions"),
    ("Y11", "D26", "the still-ships pin on `System.handle` and `System.request_status`"),
    ("Y12", "D27", "the six-module byte-identity freeze"),
)


ENGINE = AttackTable(
    CONTRACT_NAME=CONTRACT_NAME,
    CORRECTION=CORRECTION,
    EXTRA_ANCHORS=EXTRA_ANCHORS,
    HERE=HERE,
    MIN_ATTACK_CHARS=MIN_ATTACK_CHARS,
    MIN_REPRO_CHARS=MIN_REPRO_CHARS,
    OBLIGATION=OBLIGATION,
    ROOT=ROOT,
    SEED=SEED,
    SEVERITIES=SEVERITIES,
    TABLE_RELPATH=TABLE_RELPATH,
    TEAMMATE_FIELDS=TEAMMATE_FIELDS,
    UNKNOWN=UNKNOWN,
    documentation=__doc__,
    source_path=__file__
)
_contract_ids = ENGINE._contract_ids
emit_seed = ENGINE.emit_seed
grade = ENGINE.grade
_fill = ENGINE._fill
_run = ENGINE._run
self_test = ENGINE.self_test
main = ENGINE.main

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
