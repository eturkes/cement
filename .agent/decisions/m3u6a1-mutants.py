#!/usr/bin/env python3
"""Gate 9 for M3.6a1: the REVERSION sweep, and the battery's independent red credential.

    uv run python .agent/decisions/m3u6a1-mutants.py
    uv run python .agent/decisions/m3u6a1-mutants.py --validate
    uv run python .agent/decisions/m3u6a1-mutants.py --self-test
    uv run python .agent/decisions/m3u6a1-mutants.py --emit-stub
    uv run python .agent/decisions/m3u6a1-mutants.py --id M07 --id M12
    uv run python .agent/decisions/m3u6a1-mutants.py --kind sensitivity

ONE CATALOGUE, READ TWO WAYS, exactly as M3.5b established. `m3u6a1-mutants.json` holds one row
per battery clause. Rows tagged `reversion` RESTORE what the migration moved away from -- the
`handle` call, the `request_id` argument, the dead `prefix` parameter, the pre-migration demo
act -- and are the sweep proper. Rows tagged `sensitivity` perturb a PRESERVED invariant and are
the independent red control that contract section 7 requires for the six obligations which
legitimately hold at the `6fb4d92` baseline (D04, D22, D24, D25, D26, D27).

WHY REVERSION. A migration is bound by restoring what was migrated away, never by mutating what
remains: this unit edits no production source, so a sweep over "touched predicates" reads an
empty set and passes without running anything. That is M3.5b's measured finding, applied to the
migration shape.

D28 CARRIES NO ROW, and the grounds are structural rather than budgetary. Its subject is the set
of commits `git rev-list 6fb4d92..HEAD -- ...` returns, so no working-tree mutation can reach it
-- every mutant this catalogue can express leaves the committed history byte-identical and D28
stays green by construction. It was also RED at the baseline, so it already holds the credential
this instrument exists to supply for clauses that are green there. It is excluded from every
verdict run because it is INSENSITIVE, and the exclusion is printed on the control line so no
verdict is quotable without it; the fact that it also costs ~340 s per run and spawns one nested
worktree per revision is a consequence, not the reason.

Mechanics, each one paid for by a defect in this project's history:

- AN ISOLATED WORKTREE, never the primary tree. A sweep patching tracked files in place
  contaminates `git status` for its whole run, and killing it strands a live mutant.
- A PREFLIGHT ANCHOR CENSUS reporting EVERY unusable row at once. A first-failure abort hides
  every later verdict and leaves a MIXED table nobody can quote.
- `PYTHONDONTWRITEBYTECODE=1` plus a `__pycache__` purge, because CPython invalidates bytecode
  on `(mtime, size)` and a length-preserving edit inside one mtime-second runs the ORIGINAL code.
- A POSITIVE CONTROL PER MUTANT: the anchor occurs exactly once and the patched bytes differ.
- THE UNMUTATED CONTROL RUNS FIRST. A red control makes every verdict below a false kill.
- WITNESSES from the summary header `FAIL: name (module.Class.name)`, never the verbose
  `... FAIL` line, which a docstring moves onto the next line.

VERDICTS. `killed` means the row's own `target_test` went red -- the credential the obligation
needs, because a control reddening some OTHER test proves nothing about the clause it was aimed
at. `misdirected` means the run went red WITHOUT the target: a real signal, and not a kill.
`survived` means the verdict targets stayed green.

ACCEPTANCE is the NAMED SURVIVOR SET, never `zero survivors`: rows carrying `expect:
equivalent` are that set and every other row must be `killed`.

MEASURING A DEFECT IS NOT REPAIRING IT. `--validate` reads each row's own `note` for a recorded
baseline verdict and FAILS on `baseline=survived` / `baseline=misdirected` / `baseline=noop`,
because M3.5b shipped three broken controls whose author had honestly written its own failed
verdicts into free text that no counter read.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CATALOGUE = HERE / "m3u6a1-mutants.json"
CONTRACT = HERE / "m3u6a1-contract.md"
BATTERY_RELPATH = pathlib.Path("tests") / "test_migration_battery.py"

BATTERY_MODULE = "tests.test_migration_battery"
CLASS_NAME = "MigrationBatteryTests"
DEFAULT_VERDICT = (BATTERY_MODULE,)

KINDS = ("reversion", "sensitivity")
EXPECTS = ("killed", "equivalent")

OBLIGATION = re.compile(r"^- \*\*(D\d+[a-z]?)\*\*")
TEST_OBLIGATION = re.compile(r"^test_(d\d+[a-z]?)_")
WITNESS = re.compile(r"^(?:FAIL|ERROR): \w+ \(([\w.]+)\)", re.MULTILINE)
# A row that RECORDS its own failed verdict in free text has handed MAIN a finding, not a
# working control; the counter is what turns that honesty into a gate.
BASELINE_DEFECT = re.compile(r"\bbaseline\s*=\s*(survived|misdirected|noop|patch-noop)\b")

UNKNOWN = "unknown"
FILLED_CELLS = ("kind", "path", "anchor", "replacement", "note")


def _contract_ids(contract: pathlib.Path) -> list[str]:
    """The contract's OWN spelling of every obligation id. `D14a` never becomes `D14A`."""
    return [
        match.group(1)
        for line in contract.read_text(encoding="utf-8").splitlines()
        if (match := OBLIGATION.match(line))
    ]


def _battery_tests(battery: pathlib.Path) -> list[str]:
    tree = ast.parse(battery.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == CLASS_NAME:
            return [
                child.name
                for child in node.body
                if isinstance(child, ast.FunctionDef) and child.name.startswith("test_")
            ]
    raise SystemExit(f"ABORT   {battery} holds no class {CLASS_NAME}")


def _clauses(battery: pathlib.Path, contract: pathlib.Path) -> dict[str, str]:
    """test name -> obligation id, in the CONTRACT's spelling. Order follows the battery."""
    spelling = {name.lower(): name for name in _contract_ids(contract)}
    clauses: dict[str, str] = {}
    for test in _battery_tests(battery):
        match = TEST_OBLIGATION.match(test)
        if match is None:
            raise SystemExit(f"ABORT   {test} names no obligation")
        key = match.group(1)
        if key not in spelling:
            raise SystemExit(f"ABORT   {test} names {key}, absent from the contract")
        clauses[test] = spelling[key]
    return clauses


def _load(path: pathlib.Path = CATALOGUE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(document: dict, path: pathlib.Path = CATALOGUE) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- seed


def emit_stub(document: dict, clauses: dict[str, str]) -> tuple[dict, int]:
    """ADD missing rows, never rewrite filled ones.

    The frozen-evidence rule: a fresh emit written over recorded work is a loss, so the seeder is
    idempotent over its own output and reports how many rows it added.
    """
    excluded = {entry["test"] for entry in document.get("excluded", [])}
    rows = list(document.get("rows", []))
    covered = {row["target_test"] for row in rows}
    added = 0
    for test, obligation in clauses.items():
        if test in excluded or test in covered:
            continue
        added += 1
        rows.append(
            {
                "id": f"M{len(rows) + 1:02d}",
                "obligation": obligation,
                "kind": UNKNOWN,
                "target_test": test,
                "path": UNKNOWN,
                "anchor": UNKNOWN,
                "replacement": UNKNOWN,
                "expect": "killed",
                "note": UNKNOWN,
            }
        )
    document["rows"] = rows
    return document, added


# --------------------------------------------------------------------------- grade


def validate(document: dict, clauses: dict[str, str]) -> tuple[list[str], list[str]]:
    """Structural grade. Returns (counter lines, failing counter names)."""
    rows = document.get("rows", [])
    excluded = document.get("excluded", [])
    excluded_tests = {entry["test"] for entry in excluded}

    ungrounded = [
        entry["test"] for entry in excluded if not str(entry.get("grounds", "")).strip()
    ]
    unknown_exclusion = sorted(excluded_tests - set(clauses))
    covered: dict[str, int] = {}
    orphan: list[str] = []
    duplicate: list[str] = []
    unfilled: list[str] = []
    bad_kind: list[str] = []
    bad_expect: list[str] = []
    identity: list[str] = []
    baseline_defect: list[str] = []
    drift: list[str] = []

    seen: set[str] = set()
    for row in rows:
        row_id = str(row.get("id", "?"))
        if row_id in seen:
            duplicate.append(row_id)
        seen.add(row_id)
        target = row.get("target_test", "")
        if target not in clauses:
            orphan.append(row_id)
        else:
            covered[target] = covered.get(target, 0) + 1
            if row.get("obligation") != clauses[target]:
                drift.append(row_id)
        if any(str(row.get(cell, UNKNOWN)) == UNKNOWN for cell in FILLED_CELLS):
            unfilled.append(row_id)
            continue
        if row.get("kind") not in KINDS:
            bad_kind.append(row_id)
        if row.get("expect", "killed") not in EXPECTS:
            bad_expect.append(row_id)
        if row.get("anchor") == row.get("replacement"):
            identity.append(row_id)
        if BASELINE_DEFECT.search(str(row.get("note", ""))):
            baseline_defect.append(row_id)

    uncovered = sorted(set(clauses) - excluded_tests - set(covered))
    excluded_covered = sorted(excluded_tests & set(covered))

    counters = [
        ("ROWS", len(rows), False),
        ("CLAUSES", len(clauses), False),
        ("EXCLUDED", len(excluded_tests), False),
        ("CLAUSE-UNCOVERED", uncovered, True),
        ("EXCLUDED-COVERED", excluded_covered, True),
        ("EXCLUSION-UNGROUNDED", ungrounded, True),
        ("EXCLUSION-UNKNOWN", unknown_exclusion, True),
        ("ORPHAN", orphan, True),
        ("DUPLICATE-ID", duplicate, True),
        ("OBLIGATION-DRIFT", drift, True),
        ("UNFILLED", unfilled, True),
        ("BAD-KIND", bad_kind, True),
        ("BAD-EXPECT", bad_expect, True),
        ("IDENTITY", identity, True),
        ("BASELINE-DEFECT", baseline_defect, True),
    ]
    lines: list[str] = []
    failing: list[str] = []
    for name, value, gating in counters:
        if isinstance(value, int):
            lines.append(f"{name}: {value}")
            continue
        lines.append(f"{name}: {len(value)} {sorted(value)}" if value else f"{name}: 0")
        if gating and value:
            failing.append(name)
    return lines, failing


# --------------------------------------------------------------------------- sweep


def _purge_pycache(root: pathlib.Path) -> None:
    for cache in root.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def _verdict_targets(tree: pathlib.Path, modules: list[str], excluded: set[str]) -> list[str]:
    """Expand the battery module into explicit test ids MINUS the excluded clauses.

    `unittest` has no negative selector, so the exclusion has to be spelled as a selection.
    """
    targets: list[str] = []
    for module in modules:
        if module != BATTERY_MODULE:
            targets.append(module)
            continue
        for test in _battery_tests(tree / BATTERY_RELPATH):
            if test not in excluded:
                targets.append(f"{module}.{CLASS_NAME}.{test}")
    return targets


def _run(tree: pathlib.Path, targets: list[str]) -> tuple[bool, str]:
    _purge_pycache(tree)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    argv = ["uv", "run", "--quiet", "python", "-m", "unittest", "-v", *targets]
    proc = subprocess.run(
        argv, cwd=tree, capture_output=True, text=True, env=env, check=False
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def _witnesses(output: str) -> list[str]:
    return sorted(set(WITNESS.findall(output)))


def preflight(tree: pathlib.Path, rows: list[dict]) -> list[str]:
    """Report EVERY unusable row at once; a first-failure abort hides later verdicts."""
    problems: list[str] = []
    for row in rows:
        target = tree / row["path"]
        if not target.is_file():
            problems.append(f"{row['id']}   NO-FILE      {row['path']}")
            continue
        count = target.read_text(encoding="utf-8").count(row["anchor"])
        if count != 1:
            problems.append(
                f"{row['id']}   ANCHOR-{'MISS' if count == 0 else 'AMBIGUOUS'}  "
                f"{row['path']} count={count}"
            )
            continue
        if row["anchor"] == row["replacement"]:
            problems.append(f"{row['id']}   IDENTITY     replacement equals anchor")
    return problems


def apply_one(tree: pathlib.Path, row: dict, targets: list[str]) -> dict:
    target = tree / row["path"]
    before = target.read_text(encoding="utf-8")
    after = before.replace(row["anchor"], row["replacement"], 1)
    summary = {
        "id": row["id"],
        "obligation": row["obligation"],
        "kind": row.get("kind", ""),
        "target_test": row["target_test"],
        "expect": row.get("expect", "killed"),
    }
    if after == before:
        return {**summary, "verdict": "patch-noop", "witnesses": []}
    target.write_text(after, encoding="utf-8")
    try:
        green, output = _run(tree, targets)
        witnesses = _witnesses(output)
        wanted = row["target_test"]
        if green:
            verdict = "survived"
        elif any(witness.endswith(f".{wanted}") for witness in witnesses):
            verdict = "killed"
        else:
            verdict = "misdirected"
    finally:
        target.write_text(before, encoding="utf-8")
        if target.read_text(encoding="utf-8") != before:
            raise SystemExit(f"ABORT   {row['id']} left {row['path']} unrestored")
    return {**summary, "verdict": verdict, "witnesses": witnesses}


def sweep(rows: list[dict], modules: list[str], excluded: dict[str, str]) -> tuple[int, list[dict]]:
    declared = sorted(row["id"] for row in rows if row.get("expect") == "equivalent")
    with tempfile.TemporaryDirectory(prefix="m3u6a1-sweep-") as room:
        tree = pathlib.Path(room) / "tree"
        subprocess.run(
            ["git", "-C", str(ROOT), "worktree", "add", "--detach", str(tree), "HEAD"],
            check=True,
            capture_output=True,
        )
        try:
            stale = preflight(tree, rows)
            for line in stale:
                print(line)
            if stale:
                print(f"ABORT   {len(stale)} unusable rows; re-anchor before quoting a verdict")
                return 1, []

            targets = _verdict_targets(tree, modules, set(excluded))
            control_green, control_output = _run(tree, targets)
            print(f"VERDICT-MODULES: {' '.join(modules)}")
            print(f"VERDICT-TARGETS: {len(targets)}")
            for test, grounds in excluded.items():
                print(f"VERDICT-EXCLUDED: {test} -- {grounds}")
            print(f"CONTROL: {'GREEN' if control_green else 'RED'}")
            if not control_green:
                print(f"  {' '.join(_witnesses(control_output)) or 'no witness parsed'}")
                print("ABORT   the unmutated control is red; every verdict would be a false kill")
                return 1, []
            results = [apply_one(tree, row, targets) for row in rows]
        finally:
            subprocess.run(
                ["git", "-C", str(ROOT), "worktree", "remove", "--force", str(tree)],
                check=False,
                capture_output=True,
            )

    print(f"MUTANTS: {len(results)}")
    for result in results:
        marks = ",".join(str(w) for w in result["witnesses"][:2]) or "-"
        print(
            f"{result['id']:<5} {result['verdict']!s:<12} {result['obligation']!s:<6} "
            f"{result['kind']!s:<12} {marks}"
        )
    killed = [r for r in results if r["verdict"] == "killed"]
    misdirected = sorted(str(r["id"]) for r in results if r["verdict"] == "misdirected")
    survived = sorted(str(r["id"]) for r in results if r["verdict"] == "survived")
    noop = sorted(str(r["id"]) for r in results if r["verdict"] == "patch-noop")
    unexpected = sorted(set(survived) - set(declared))
    print(f"KILLED: {len(killed)}")
    print(f"MISDIRECTED: {len(misdirected)} {misdirected}")
    print(f"SURVIVORS: {len(survived)} {survived}")
    print(f"NAMED-SURVIVOR-SET: {len(declared)} {declared}")
    print(f"PATCH-NOOP: {len(noop)} {noop}")
    print(f"UNEXPECTED-SURVIVORS: {len(unexpected)} {unexpected}")
    failed = bool(unexpected or misdirected or noop)
    print("RESULT: FAIL" if failed else "RESULT: PASS")
    return (1 if failed else 0), results


# --------------------------------------------------------------------------- self-test


def _synthetic(document: dict, clauses: dict[str, str]) -> dict:
    """A FILLED copy of the catalogue, so the positive direction is gradeable at seed time."""
    filled = copy.deepcopy(document)
    for row in filled["rows"]:
        row["kind"] = "reversion"
        row["path"] = "tests/test_system.py"
        row["anchor"] = f"anchor-{row['id']}"
        row["replacement"] = f"replacement-{row['id']}"
        row["note"] = f"reverts the migration at {row['target_test']}"
    return filled


def self_test(document: dict, clauses: dict[str, str]) -> int:
    """Grade both ways from committed state: a filled pair PASSES, every control FIRES."""
    filled = _synthetic(document, clauses)
    _, failing = validate(filled, clauses)
    if failing:
        print(f"SELF-TEST  positive direction FAILED on {failing}")
        return 1
    print("SELF-TEST  positive: PASS")

    def control(name: str, expect: str, mutate) -> bool:
        candidate = copy.deepcopy(filled)
        mutate(candidate)
        _, fired = validate(candidate, clauses)
        ok = expect in fired
        print(f"SELF-TEST  {name:<24} {'FIRES' if ok else 'SILENT'} -> {sorted(fired)}")
        return ok

    def _drop_row(doc: dict) -> None:
        doc["rows"] = doc["rows"][1:]

    def _unfill(doc: dict) -> None:
        doc["rows"][0]["anchor"] = UNKNOWN

    def _bad_kind(doc: dict) -> None:
        doc["rows"][0]["kind"] = "mutation"

    def _bad_expect(doc: dict) -> None:
        doc["rows"][0]["expect"] = "maybe"

    def _orphan(doc: dict) -> None:
        doc["rows"][0]["target_test"] = "test_d99_absent"

    def _duplicate(doc: dict) -> None:
        doc["rows"].append(copy.deepcopy(doc["rows"][0]))

    def _identity(doc: dict) -> None:
        doc["rows"][0]["replacement"] = doc["rows"][0]["anchor"]

    def _baseline(doc: dict) -> None:
        doc["rows"][0]["note"] = "restores the call; baseline=survived, needs a wider anchor"

    def _drift(doc: dict) -> None:
        doc["rows"][0]["obligation"] = "D99"

    def _excluded_covered(doc: dict) -> None:
        doc["rows"][0]["target_test"] = doc["excluded"][0]["test"]

    def _ungrounded(doc: dict) -> None:
        doc["excluded"][0]["grounds"] = ""

    def _unknown_exclusion(doc: dict) -> None:
        doc["excluded"][0]["test"] = "test_d99_absent"

    controls = [
        ("dropped row", "CLAUSE-UNCOVERED", _drop_row),
        ("unfilled cell", "UNFILLED", _unfill),
        ("bad kind", "BAD-KIND", _bad_kind),
        ("bad expect", "BAD-EXPECT", _bad_expect),
        ("orphan target", "ORPHAN", _orphan),
        ("duplicate id", "DUPLICATE-ID", _duplicate),
        ("identity patch", "IDENTITY", _identity),
        ("recorded baseline fail", "BASELINE-DEFECT", _baseline),
        ("obligation drift", "OBLIGATION-DRIFT", _drift),
        ("excluded clause covered", "EXCLUDED-COVERED", _excluded_covered),
        ("ungrounded exclusion", "EXCLUSION-UNGROUNDED", _ungrounded),
        ("exclusion names no clause", "EXCLUSION-UNKNOWN", _unknown_exclusion),
    ]
    fired = [control(name, expect, mutate) for name, expect, mutate in controls]
    print(f"SELF-TEST  controls {sum(fired)}/{len(fired)} firing")
    ok = all(fired)
    print("SELF-TEST RESULT: PASS" if ok else "SELF-TEST RESULT: FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- entry


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", default=[])
    parser.add_argument("--kind", action="append", default=[])
    parser.add_argument("--verdict", action="append", default=[])
    parser.add_argument("--json", default="")
    parser.add_argument("--emit-stub", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv[1:])

    clauses = _clauses(ROOT / BATTERY_RELPATH, CONTRACT)
    document = _load()

    if args.emit_stub:
        document, added = emit_stub(document, clauses)
        _dump(document)
        print(f"CLAUSES: {len(clauses)}")
        print(f"ROWS: {len(document['rows'])}")
        print("EMIT: no-op" if added == 0 else f"EMIT: {added} row(s) added")
        return 0

    if args.validate or args.self_test:
        lines, failing = validate(document, clauses)
        for line in lines:
            print(line)
        print("RESULT: FAIL" if failing else "RESULT: PASS")
        if args.self_test:
            return self_test(document, clauses)
        return 1 if failing else 0

    lines, failing = validate(document, clauses)
    if failing:
        for line in lines:
            print(line)
        print("ABORT   the catalogue is structurally invalid; grade it before sweeping")
        return 1

    rows = document["rows"]
    if args.id:
        rows = [row for row in rows if row["id"] in set(args.id)]
    if args.kind:
        rows = [row for row in rows if row.get("kind") in set(args.kind)]
    if not rows:
        raise SystemExit("ABORT   selection matched no mutant")

    excluded = {entry["test"]: entry["grounds"] for entry in document.get("excluded", [])}
    status, results = sweep(rows, args.verdict or list(DEFAULT_VERDICT), excluded)
    if args.json and results:
        pathlib.Path(args.json).write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
