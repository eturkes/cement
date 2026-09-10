#!/usr/bin/env python3
"""Grade `m3u6a2-dispositions.json` — one ruled disposition per frame the removal broke.

A removal's failure list is its work list, and a green suite is not closure for it: deleting a
test together with the behaviour it pinned leaves the gate green and coverage silently smaller.
Every row therefore states WHERE the subject is checked after the repair, and this validator
proves that answer against the tree rather than accepting the word.

    uv run python .agent/decisions/m3u6a2-dispositions-validate.py
    uv run python .agent/decisions/m3u6a2-dispositions-validate.py --self-test
"""

from __future__ import annotations

import argparse
import ast
import functools
import io
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TABLE = ROOT / ".agent/decisions/m3u6a2-dispositions.json"
BASELINE = "27658c4"
DELETED_SUBJECT = "NONE - the subject is on the unit's deletion set"
DISPOSITIONS = {"delete", "rebase", "remeasure"}
MIN_GROUNDS = 60

# MAIN's ruling half, written by `m3u6a2-rule-dispositions.py` (C24). The disposition checks above
# see a rebase that kept the frame and dropped the check as clean, because the span DID differ.
MAIN_VERDICTS = {"affirmed", "affirmed-cover-verified", "affirmed-drop-ruled"}
DROP_RULED = "affirmed-drop-ruled"
COVER_VERIFIED = "affirmed-cover-verified"
TEST_NAME = re.compile(r"\btest_[a-z0-9_]+")


@functools.cache
def _tree_source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@functools.cache
def _function_names(relative: str) -> frozenset[str]:
    """Every function name one tracked file defines.

    Cached because `--self-test` grades 11 mutated tables and each one resolves a covering test
    per row: uncached, the grader reparses 47k lines of `tests/` thousands of times and takes
    minutes, which is not a gate anyone reruns.
    """
    path = ROOT / relative
    if not path.is_file():
        return frozenset()
    return frozenset(
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _defined(relative: str, name: str) -> bool:
    return name in _function_names(relative)


@functools.cache
def _baseline_source(relative: str) -> str:
    return subprocess.run(
        ["git", "show", f"{BASELINE}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@functools.cache
def _span(source: str, name: str) -> str | None:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
            return "\n".join(source.splitlines()[start - 1 : node.end_lineno])
    return None


@functools.cache
def _assert_count(source: str, name: str) -> int | None:
    """Assertion calls plus bare `assert` statements inside one named frame.

    A proxy for strength, and deliberately a coarse one: it cannot tell a real check from
    narrowing scaffolding, which is why a fall must be RULED rather than merely reported.
    """
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            total = 0
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    total += child.func.attr.startswith("assert")
                elif isinstance(child, ast.Assert):
                    total += 1
            return total
    return None


@functools.cache
def _find_test(name: str) -> str | None:
    """Locate a named test anywhere under `tests/`, so a rehomed subject still resolves."""
    for path in sorted((ROOT / "tests").glob("*.py")):
        if _defined(f"tests/{path.name}", name):
            return f"tests/{path.name}"
    return None


def _unrepaired_frame() -> tuple[str, str]:
    """A frame byte-identical between BASELINE and the tree, derived rather than named.

    Once every row is genuinely repaired, a control that only relabels rows can no longer
    produce an UNCHANGED finding and then reports exactly like a control that fired. So the
    control borrows a frame this unit never touched, and a tree with no such frame left is a
    hard error rather than a quiet pass.
    """
    for path in sorted((ROOT / "tests").glob("*.py")):
        relative = f"tests/{path.name}"
        try:
            if _baseline_source(relative) != _tree_source(relative):
                continue
        except subprocess.CalledProcessError:
            continue
        for name in sorted(_function_names(relative)):
            if name.startswith("test_"):
                return relative, name
    raise SystemExit("SELF-TEST: no frame survived the unit unchanged, so UNCHANGED is unreachable")


def validate(table: dict[str, object]) -> int:
    rows = table["rows"]
    failures: list[str] = []

    expected = {row["id"] for row in json.loads(_baseline_source(
        ".agent/decisions/m3u6a2-dispositions.json"
    ))["rows"]}
    present = {row["id"] for row in rows}
    if present != expected:
        failures.append(
            f"ROW-SET: dropped={sorted(expected - present)} added={sorted(present - expected)}"
        )

    for row in rows:
        rid, module, test = row["id"], row["module"], row["test"]
        disposition, grounds = row["disposition"], str(row["grounds"]).strip()
        covering = str(row["covering_test"]).strip()
        if disposition not in DISPOSITIONS:
            failures.append(f"{rid} UNRULED: disposition={disposition!r}")
            continue
        if len(grounds) < MIN_GROUNDS:
            failures.append(f"{rid} THIN-GROUNDS: {len(grounds)} chars, want >= {MIN_GROUNDS}")
        still_here = _defined(module, test)
        if disposition == "delete":
            if still_here:
                failures.append(f"{rid} NOT-DELETED: {module} still defines {test}")
            if covering == DELETED_SUBJECT:
                continue
            home = _find_test(covering) if covering else None
            if home is None:
                failures.append(
                    f"{rid} UNCOVERED: covering_test={covering!r} names no test under tests/"
                )
            continue
        if not still_here:
            failures.append(f"{rid} MISSING: {module} no longer defines {test}")
            continue
        before = _span(_baseline_source(module), test)
        after = _span(_tree_source(module), test)
        if before == after:
            failures.append(f"{rid} UNCHANGED: the frame is byte-identical to {BASELINE}")

    for row in rows:
        rid = row["id"]
        verdict = str(row.get("main_verdict", "")).strip()
        note = str(row.get("main_note", "")).strip()
        if verdict not in MAIN_VERDICTS:
            failures.append(f"{rid} UNADJUDICATED: main_verdict={verdict!r}")
            continue
        if len(note) < MIN_GROUNDS:
            failures.append(f"{rid} THIN-NOTE: {len(note)} chars, want >= {MIN_GROUNDS}")
        if verdict == COVER_VERIFIED and not any(
            _find_test(name) for name in TEST_NAME.findall(note)
        ):
            failures.append(f"{rid} COVER-UNRESOLVED: the note names no test that exists")
        if row["disposition"] == "delete":
            if verdict == DROP_RULED:
                failures.append(f"{rid} DROP-ON-DELETE: a deleted frame has no assertion census")
            continue
        before = _assert_count(_baseline_source(row["module"]), row["test"])
        after = _assert_count(_tree_source(str(row["module"])), str(row["test"]))
        if before is None or after is None:
            continue
        if after < before and verdict != DROP_RULED:
            failures.append(f"{rid} UNRULED-DROP: assertions {before} -> {after}, rule it")
        if after >= before and verdict == DROP_RULED:
            failures.append(f"{rid} PHANTOM-DROP: assertions {before} -> {after}, nothing fell")

    ruled = sum(1 for row in rows if row["disposition"] in DISPOSITIONS)
    for line in failures:
        print(line)
    print(f"ROWS: {len(rows)} RULED: {ruled} UNRULED: {len(rows) - ruled}")
    print(f"DELETED: {sum(1 for r in rows if r['disposition'] == 'delete')}")
    print(f"REBASED: {sum(1 for r in rows if r['disposition'] == 'rebase')}")
    print(f"REMEASURED: {sum(1 for r in rows if r['disposition'] == 'remeasure')}")
    for verdict in sorted(MAIN_VERDICTS):
        print(f"{verdict.upper()}: {sum(1 for r in rows if r.get('main_verdict') == verdict)}")
    print(f"RESULT: {'PASS' if not failures else 'FAIL'} ({len(failures)} findings)")
    return 1 if failures else 0


def self_test() -> int:
    """Grade the grader both ways against the committed table."""
    base = json.loads(TABLE.read_text(encoding="utf-8"))
    controls: list[tuple[str, dict[str, object], str]] = []

    unruled = json.loads(json.dumps(base))
    unruled["rows"][0]["disposition"] = "unknown"
    controls.append(("an unruled row", unruled, "UNRULED"))

    thin = json.loads(json.dumps(base))
    thin["rows"][0]["disposition"] = "rebase"
    thin["rows"][0]["grounds"] = "because"
    controls.append(("grounds too thin to audit", thin, "THIN-GROUNDS"))

    dropped = json.loads(json.dumps(base))
    dropped["rows"] = dropped["rows"][1:]
    controls.append(("a dropped row", dropped, "ROW-SET"))

    uncovered = json.loads(json.dumps(base))
    for row in uncovered["rows"]:
        row["disposition"] = "delete"
        row["grounds"] = "g" * MIN_GROUNDS
        row["covering_test"] = "test_no_such_test_anywhere_in_the_tree"
    controls.append(("a deletion whose cover does not exist", uncovered, "UNCOVERED"))

    surviving = json.loads(json.dumps(base))
    for row in surviving["rows"]:
        row["disposition"] = "delete"
        row["grounds"] = "g" * MIN_GROUNDS
        row["covering_test"] = DELETED_SUBJECT
    controls.append(("a deletion the tree did not perform", surviving, "NOT-DELETED"))

    untouched = json.loads(json.dumps(base))
    frozen_module, frozen_test = _unrepaired_frame()
    for row in untouched["rows"]:
        row["disposition"] = "rebase"
        row["grounds"] = "g" * MIN_GROUNDS
        row["module"], row["test"] = frozen_module, frozen_test
    controls.append((f"a rebase that edited nothing ({frozen_test})", untouched, "UNCHANGED"))

    unadjudicated = json.loads(json.dumps(base))
    for row in unadjudicated["rows"]:
        row.pop("main_verdict", None)
    controls.append(("MAIN's ruling absent", unadjudicated, "UNADJUDICATED"))

    thin_note = json.loads(json.dumps(base))
    for row in thin_note["rows"]:
        row["main_note"] = "affirmed"
    controls.append(("a ruling too thin to audit", thin_note, "THIN-NOTE"))

    phantom_cover = json.loads(json.dumps(base))
    for row in phantom_cover["rows"]:
        row["main_verdict"] = COVER_VERIFIED
        row["main_note"] = "cover = test_no_such_test_anywhere_in_this_tree " + "g" * MIN_GROUNDS
    controls.append(("a cover the tree does not hold", phantom_cover, "COVER-UNRESOLVED"))

    unruled_drop = json.loads(json.dumps(base))
    for row in unruled_drop["rows"]:
        if row.get("main_verdict") == DROP_RULED:
            row["main_verdict"] = "affirmed"
    controls.append(("a weakened frame left unruled", unruled_drop, "UNRULED-DROP"))

    phantom_drop = json.loads(json.dumps(base))
    for row in phantom_drop["rows"]:
        if row["disposition"] != "delete" and row.get("main_verdict") != DROP_RULED:
            row["main_verdict"] = DROP_RULED
    controls.append(("a drop ruling with nothing to rule", phantom_drop, "PHANTOM-DROP"))

    silent: list[str] = []
    for label, mutated, expected in controls:
        buffer = io.StringIO()
        stdout, sys.stdout = sys.stdout, buffer
        try:
            validate(mutated)
        finally:
            sys.stdout = stdout
        if expected not in buffer.getvalue():
            silent.append(f"{label} -> expected {expected}")

    buffer = io.StringIO()
    stdout, sys.stdout = sys.stdout, buffer
    try:
        filled = validate(base)
    finally:
        sys.stdout = stdout
    unruled_rows = sum(1 for row in base["rows"] if row["disposition"] not in DISPOSITIONS)
    if unruled_rows == len(base["rows"]) and filled == 0:
        silent.append("the all-`unknown` seed graded PASS")

    for line in silent:
        print(f"SILENT: {line}")
    print(f"CONTROLS: {len(controls) - len(silent)}/{len(controls)} firing")
    print(f"SEED-GRADE: {'nonzero' if filled else 'zero'} with {unruled_rows} unruled rows")
    print(f"RESULT: {'FAIL' if silent else 'PASS'}")
    return 1 if silent else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grade M3.6a2's frame dispositions.")
    parser.add_argument("--self-test", action="store_true", help="grade the grader both ways")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    return validate(json.loads(TABLE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    raise SystemExit(main())
