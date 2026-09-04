#!/usr/bin/env python3
"""Grade `m3u6a2-burden.json`: M3.6a2's deletion burden RE-MEASURED at post-migration HEAD.

    uv run python .agent/decisions/m3u6a2-burden-validate.py
    uv run python .agent/decisions/m3u6a2-burden-validate.py --self-test

M3.6a's split ruled that migrating consumers first strips the deletion unit's shared-frame
burden. That ruling has never been measured against a migrated tree, and M3.6a2 sizes against
it, so the number it sizes against must come from a rerun rather than from the split's own
forecast.

THE PRE COLUMNS ARE FROZEN EVIDENCE. They are copied from the committed
`m3u6a-burden.json` and are re-derived here, so a row cannot quietly restate the baseline to
make its own delta look better. `PRE-DRIFT` is that check.

A FRAME KEY CARRIES A LINE NUMBER, and the migration moved thousands of lines, so a raw
key set difference is almost entirely noise. `frame_key_rule` must name the normalisation
actually applied, and both difference lists are graded as lists rather than as counts.
"""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ARTIFACT = HERE / "m3u6a2-burden.json"
BASELINE = HERE / "m3u6a-burden.json"

UNKNOWN = "unknown"
SCALAR_CELLS = ("post_broken", "post_ran", "post_frames", "note")
LIST_CELLS = ("frames_gone", "frames_new")
TOP_CELLS = ("head", "frame_key_rule", "reanchors", "verdict")
PRE_CELLS = (("pre_broken", "broken"), ("pre_ran", "tests_ran"), ("pre_frames", "distinct_frames"))


def validate(document: dict, baseline: dict) -> tuple[list[str], list[str]]:
    stages = {entry["stage"]: entry for entry in baseline.get("stages", [])}
    rows = document.get("rows", [])

    unfilled = [cell for cell in TOP_CELLS if str(document.get(cell, UNKNOWN)) == UNKNOWN]
    row_unfilled: list[str] = []
    bad_type: list[str] = []
    pre_drift: list[str] = []
    no_stage: list[str] = []
    empty_note: list[str] = []

    for row in rows:
        row_id = str(row.get("id", "?"))
        if any(str(row.get(cell, UNKNOWN)) == UNKNOWN for cell in SCALAR_CELLS + LIST_CELLS):
            row_unfilled.append(row_id)
            continue
        if not all(isinstance(row.get(cell), int) for cell in SCALAR_CELLS[:3]):
            bad_type.append(row_id)
        if not all(isinstance(row.get(cell), list) for cell in LIST_CELLS):
            bad_type.append(row_id)
        if len(str(row.get("note", "")).split()) < 8:
            empty_note.append(row_id)
        stage = stages.get(row.get("stage"))
        if stage is None:
            no_stage.append(row_id)
            continue
        if any(row.get(mine) != stage.get(theirs) for mine, theirs in PRE_CELLS):
            pre_drift.append(row_id)

    counters = [
        ("ROWS", len(rows), False),
        ("TOP-UNFILLED", unfilled, True),
        ("ROW-UNFILLED", row_unfilled, True),
        ("BAD-TYPE", sorted(set(bad_type)), True),
        ("PRE-DRIFT", pre_drift, True),
        ("STAGE-UNKNOWN", no_stage, True),
        ("NOTE-EMPTY", empty_note, True),
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


def _filled(document: dict, baseline: dict) -> dict:
    stages = {entry["stage"]: entry for entry in baseline.get("stages", [])}
    filled = copy.deepcopy(document)
    for cell in TOP_CELLS:
        filled[cell] = f"filled {cell}"
    for row in filled["rows"]:
        stage = stages[row["stage"]]
        row["post_broken"] = stage["broken"]
        row["post_ran"] = stage["tests_ran"]
        row["post_frames"] = stage["distinct_frames"]
        row["frames_gone"] = []
        row["frames_new"] = []
        row["note"] = "one two three four five six seven eight nine"
    return filled


def self_test(document: dict, baseline: dict) -> int:
    filled = _filled(document, baseline)
    _, failing = validate(filled, baseline)
    if failing:
        print(f"SELF-TEST  positive direction FAILED on {failing}")
        return 1
    print("SELF-TEST  positive: PASS")

    def control(name: str, expect: str, mutate) -> bool:
        candidate = copy.deepcopy(filled)
        mutate(candidate)
        _, fired = validate(candidate, baseline)
        ok = expect in fired
        print(f"SELF-TEST  {name:<24} {'FIRES' if ok else 'SILENT'} -> {sorted(fired)}")
        return ok

    controls = [
        ("top cell unfilled", "TOP-UNFILLED", lambda d: d.update({"verdict": UNKNOWN})),
        ("row cell unfilled", "ROW-UNFILLED", lambda d: d["rows"][0].update({"post_ran": UNKNOWN})),
        ("count as string", "BAD-TYPE", lambda d: d["rows"][0].update({"post_broken": "12"})),
        ("difference as count", "BAD-TYPE", lambda d: d["rows"][0].update({"frames_gone": 3})),
        ("restated baseline", "PRE-DRIFT", lambda d: d["rows"][0].update({"pre_broken": 12})),
        ("unknown stage", "STAGE-UNKNOWN", lambda d: d["rows"][0].update({"stage": 99})),
        ("note is a stub", "NOTE-EMPTY", lambda d: d["rows"][0].update({"note": "measured"})),
    ]
    fired = [control(name, expect, mutate) for name, expect, mutate in controls]
    print(f"SELF-TEST  controls {sum(fired)}/{len(fired)} firing")
    ok = all(fired)
    print("SELF-TEST RESULT: PASS" if ok else "SELF-TEST RESULT: FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv[1:])

    document = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    lines, failing = validate(document, baseline)
    for line in lines:
        print(line)
    print("RESULT: FAIL" if failing else "RESULT: PASS")
    if args.self_test:
        return self_test(document, baseline)
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
