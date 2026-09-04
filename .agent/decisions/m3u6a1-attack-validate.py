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

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

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


def _contract_ids(root: pathlib.Path) -> set[str]:
    lines = (root / ".agent" / "decisions" / CONTRACT_NAME).read_text(encoding="utf-8").splitlines()
    found = {match.group(1) for line in lines if (match := OBLIGATION.match(line))}
    found |= {match.group(1) for line in lines if (match := CORRECTION.match(line))}
    return found | set(EXTRA_ANCHORS)


def emit_seed(root: pathlib.Path) -> str:
    rows = [
        {
            "id": row_id,
            "section": section,
            "locus": locus,
            "claim": UNKNOWN,
            "attack": UNKNOWN,
            "reproduction": UNKNOWN,
            "severity": UNKNOWN,
            "verdict": UNKNOWN,
            "disposition": UNKNOWN,
            "main_note": UNKNOWN,
        }
        for row_id, section, locus in SEED
    ]
    document = {
        "unit": "M3.6a1",
        "artifact": "contract attack + evasion matrix",
        "seeded_rows": len(rows),
        "rows": rows,
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def grade(table: pathlib.Path, root: pathlib.Path) -> int:
    if not table.exists():
        print(f"ABSENT: {table}")
        print("RESULT: FAIL")
        return 1
    try:
        document = json.loads(table.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"MALFORMED: {error}")
        print("RESULT: FAIL")
        return 1
    rows = document.get("rows", [])
    anchors = _contract_ids(root)

    unknown_cells: list[str] = []
    unresolved: list[str] = []
    bad_severity: list[str] = []
    short_attack: list[str] = []
    unreproduced: list[str] = []
    duplicates: list[str] = []
    bad_id: list[str] = []

    seen: set[str] = set()
    for row in rows:
        row_id = str(row.get("id", "?"))
        if row_id in seen:
            duplicates.append(row_id)
        seen.add(row_id)
        if not re.fullmatch(r"[AY]\d{2,}", row_id):
            bad_id.append(row_id)
        for field in TEAMMATE_FIELDS:
            value = str(row.get(field, "")).strip()
            if not value or value == UNKNOWN:
                unknown_cells.append(f"{row_id}.{field}")
        if str(row.get("section", "")) not in anchors:
            unresolved.append(f"{row_id}:{row.get('section')}")
        if str(row.get("severity", "")) not in SEVERITIES:
            bad_severity.append(f"{row_id}:{row.get('severity')}")
        attack = str(row.get("attack", ""))
        if attack != UNKNOWN and len(attack) < MIN_ATTACK_CHARS:
            short_attack.append(row_id)
        repro = str(row.get("reproduction", ""))
        if repro != UNKNOWN and len(repro) < MIN_REPRO_CHARS:
            unreproduced.append(row_id)

    seeded = {row_id for row_id, _, _ in SEED}
    dropped = sorted(seeded - seen)

    print(f"ROWS: {len(rows)} (seed {len(SEED)}, extension {max(0, len(rows) - len(SEED))})")
    print(f"UNKNOWN-CELLS: {len(unknown_cells)} {sorted(unknown_cells)[:8]}")
    print(f"SEED-DROPPED: {len(dropped)} {dropped}")
    print(f"UNRESOLVED-SECTION: {len(unresolved)} {sorted(unresolved)}")
    print(f"BAD-SEVERITY: {len(bad_severity)} {sorted(bad_severity)}")
    print(f"BAD-ID: {len(bad_id)} {sorted(bad_id)}")
    print(f"DUPLICATE-ID: {len(duplicates)} {sorted(duplicates)}")
    print(f"SHORT-ATTACK: {len(short_attack)} {sorted(short_attack)}")
    print(f"UNREPRODUCED: {len(unreproduced)} {sorted(unreproduced)}")

    failures = (
        len(unknown_cells)
        + len(dropped)
        + len(unresolved)
        + len(bad_severity)
        + len(bad_id)
        + len(duplicates)
        + len(short_attack)
        + len(unreproduced)
    )
    print(f"RESULT: {'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


def _fill(seed: str) -> str:
    document = json.loads(seed)
    for row in document["rows"]:
        row["claim"] = "the contract asserts X at this locus"
        row["attack"] = "a" * (MIN_ATTACK_CHARS + 10)
        row["reproduction"] = "b" * (MIN_REPRO_CHARS + 10)
        row["severity"] = "cleared"
        row["verdict"] = "holds"
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _run(root: pathlib.Path, table: pathlib.Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HERE / pathlib.Path(__file__).name), "--table", str(table), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def self_test() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as raw:
        stage = pathlib.Path(raw)
        decisions = stage / ".agent" / "decisions"
        decisions.mkdir(parents=True)
        shutil.copy2(ROOT / ".agent" / "decisions" / CONTRACT_NAME, decisions / CONTRACT_NAME)
        table = stage / TABLE_RELPATH

        seed = emit_seed(stage)
        filled = _fill(seed)

        def check(label: str, text: str, expect_rc: int, expect: list[str]) -> None:
            nonlocal failures
            table.write_text(text, encoding="utf-8")
            code, out = _run(stage, table)
            ok = code == expect_rc and all(line in out for line in expect)
            print(f"{'OK  ' if ok else 'FAIL'} {label}: rc={code} expect={expect_rc}")
            if not ok:
                failures += 1
                print(out)

        check("seed graded red", seed, 1, [f"UNKNOWN-CELLS: {len(SEED) * len(TEAMMATE_FIELDS) - 2 * len(SEED)}"])
        check("filled graded green", filled, 0, ["RESULT: PASS", f"SEED-DROPPED: 0"])

        def mutate(fn) -> str:
            document = json.loads(filled)
            fn(document)
            return json.dumps(document, indent=2, ensure_ascii=False) + "\n"

        check(
            "control dropped seed row -> SEED-DROPPED",
            mutate(lambda d: d["rows"].pop(0)),
            1,
            ["SEED-DROPPED: 1"],
        )
        check(
            "control unresolvable section -> UNRESOLVED-SECTION",
            mutate(lambda d: d["rows"][0].__setitem__("section", "D99")),
            1,
            ["UNRESOLVED-SECTION: 1"],
        )
        check(
            "control bad severity -> BAD-SEVERITY",
            mutate(lambda d: d["rows"][0].__setitem__("severity", "critical")),
            1,
            ["BAD-SEVERITY: 1"],
        )
        check(
            "control short attack -> SHORT-ATTACK",
            mutate(lambda d: d["rows"][0].__setitem__("attack", "too short")),
            1,
            ["SHORT-ATTACK: 1"],
        )
        check(
            "control empty reproduction -> UNREPRODUCED",
            mutate(lambda d: d["rows"][0].__setitem__("reproduction", "ran it")),
            1,
            ["UNREPRODUCED: 1"],
        )
        check(
            "control blanked cell -> UNKNOWN-CELLS",
            mutate(lambda d: d["rows"][0].__setitem__("verdict", "")),
            1,
            ["UNKNOWN-CELLS: 1"],
        )
        check(
            "control duplicate id -> DUPLICATE-ID",
            mutate(lambda d: d["rows"].append(dict(d["rows"][0]))),
            1,
            ["DUPLICATE-ID: 1"],
        )
        check(
            "control bad extension id -> BAD-ID",
            mutate(
                lambda d: d["rows"].append({**d["rows"][0], "id": "Z1"}),
            ),
            1,
            ["BAD-ID: 1"],
        )
        check("control malformed table -> FAIL", "{not json", 1, ["MALFORMED", "RESULT: FAIL"])
        table.unlink()
        code, out = _run(stage, table)
        ok = code == 1 and "ABSENT" in out
        print(f"{'OK  ' if ok else 'FAIL'} control absent table -> ABSENT: rc={code}")
        if not ok:
            failures += 1

    print(f"SELF-TEST: {'PASS' if failures == 0 else 'FAIL'} ({failures} control(s) not firing)")
    return 0 if failures == 0 else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-seed", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--table", type=pathlib.Path, default=None)
    parser.add_argument("--root", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    root = (args.root or ROOT).resolve()
    if args.self_test:
        return self_test()
    if args.emit_seed:
        sys.stdout.write(emit_seed(root))
        return 0
    table = args.table or (root / TABLE_RELPATH)
    return grade(table.resolve(), root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
