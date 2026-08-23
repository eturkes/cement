#!/usr/bin/env python3
"""Structural validator for M3.2b wave-1 artifacts.

Usage: uv run python .agent/decisions/m3u2b-validate.py <artifact.json>

The artifact's top-level ``kind`` selects the schema:

  "compose-matrix"  the composition spike's probe matrix
  "bench"           the component-cost baseline measurements
  "resolve-bench"   the end-to-end `System.resolve` measurements
  "smoke-crosswalk" each check of MAIN's machine-local smoke probe -> the committed test
                    that now carries it

A "resolve-bench" artifact must also carry one `provenance` block PER POINT and every
point's block must be identical, because the published exponents are a fit across the
three points. The grader prints the derived exponents and overheads, so section 8 of
`.agent/decisions/m3u2b-contract.md` re-derives from committed state with one command
instead of resting on arithmetic no reader can replay.

Exit 0 = structurally valid AND nothing left ``unknown``. Exit 1 = structural
defect or an unfilled cell. An expectation MISMATCH never fails the run: the
mismatch is the measurement this unit buys, so it is reported and counted.

The schemas below are the seedable skeleton. A first tool call that writes every
required id with every value ``unknown`` produces a valid file whose UNKNOWN-CELLS
count is the flush metric, and each filled cell lowers it.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

UNKNOWN = "unknown"
OUTCOMES = {"ok", "denied", "error", "differs", UNKNOWN}

# id -> (expected outcome, what a filled `ok` must demonstrate)
COMPOSE_PROBES: dict[str, tuple[str, str]] = {
    # Three-state contract. These are the unit's headline predicates.
    "C1_hit": ("ok", "promoted input returns passed=True, matched=True, exact promoted output + artifact_hash"),
    "C2_miss": ("ok", "absent input returns passed=True, matched=False, output None, artifact_hash None"),
    "C3_failed_verification": ("ok", "a suspended member returns passed=False, match is None, document None"),
    "C4_expected_hash_mismatch": ("ok", "a wrong expected_function_hash returns passed=False and match None"),
    "C5_empty_promoted_set": ("ok", "a scope with no promoted set reports its verdict; note records passed + entries"),
    # Purity. Every one of these is a claim the unit must be able to make.
    "C6_one_snapshot": ("ok", "exactly one read transaction opens per call; in_transaction holds across verification"),
    "C7_no_clock": ("ok", "a raising System._now leaves every resolve answer unchanged"),
    "C8_no_write": ("ok", "ledger sha256 + full iterdump are byte-identical across hit, miss and failed calls"),
    "C9_no_event_no_id": ("ok", "events() and every id-allocating counter are unchanged across all three states"),
    "C10_missing_ledger": ("error", "resolve against a deleted ledger raises and creates no file"),
    "C11_unregistered_operation": ("error", "note records the exact class + message for an unknown operation"),
    # Composition soundness. C12/C13 decide whether factoring is forced.
    "C12_canonical_equivalent_input": ("ok", "key-reordered and equal-value inputs resolve to the same hit"),
    "C13_evaluate_outside_snapshot": ("ok", "evaluating the returned document after rollback equals evaluating inside"),
    "C14_document_none_gate": ("ok", "a failed verdict never reaches evaluate; the spy records zero calls"),
    "C15_concurrent_writer": ("ok", "a writer committing between two resolves changes only the second answer"),
    # The ablation. `differs` here is the only outcome that forces the factored design.
    "C16_factoring_forced": (
        UNKNOWN,
        "any behaviour the thin composition cannot produce that a supplied-connection core can; "
        "outcome `ok` = none found, `differs` = one found and the note names it",
    ),
    "C17_production_line_count": ("ok", "measured non-test lines the thin composition adds, counted from the diff"),
}

BENCH_POINTS: dict[str, int] = {
    "n1": 1,
    "n1000": 1_000,
    "n50000": 50_000,
}
BENCH_CELLS = (
    "entries",
    "document_bytes",
    "document_items",
    "fixture_build_seconds",
    "verify_cold_ms",
    "verify_warm_ms",
    "evaluate_hit_ms",
    "evaluate_miss_ms",
    "peak_rss_kib",
    "note",
)
BENCH_ENV = ("python_version", "sqlite_version", "host_cpu", "repeats", "commit")
RESOLVE_CELLS = (
    "entries",
    "document_bytes",
    "fixture_build_seconds",
    "resolve_cold_hit_ms",
    "resolve_warm_miss_ms",
    "resolve_warm_failed_ms",
    "rss_before_kib",
    "peak_rss_kib",
)
RESOLVE_PROVENANCE = (
    "unit",
    "commit",
    "source_dirty",
    "python_version",
    "sqlite_version",
    "host_cpu",
    "platform",
    "repeats",
)


def fail(message: str) -> None:
    print(f"INVALID: {message}")
    raise SystemExit(1)


def load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"{path} is unreadable or is not JSON: {exc}")
    if not isinstance(payload, dict):
        fail(f"{path} must hold a JSON object")
    return payload


def check_compose(payload: dict) -> tuple[int, int]:
    probes = payload.get("probes")
    if not isinstance(probes, dict):
        fail("compose-matrix requires a `probes` object")
    missing = sorted(set(COMPOSE_PROBES) - set(probes))
    if missing:
        fail(f"missing probe id(s): {', '.join(missing)}")
    extra = sorted(set(probes) - set(COMPOSE_PROBES))
    if extra:
        fail(f"unknown probe id(s): {', '.join(extra)}")
    unknown = 0
    mismatches = 0
    for probe_id, expected in COMPOSE_PROBES.items():
        entry = probes[probe_id]
        if not isinstance(entry, dict):
            fail(f"{probe_id} must hold an object")
        outcome = entry.get("outcome")
        if outcome not in OUTCOMES:
            fail(f"{probe_id} outcome {outcome!r} is not one of {sorted(OUTCOMES)}")
        note = entry.get("note")
        evidence = entry.get("evidence")
        if not isinstance(note, str) or not isinstance(evidence, str):
            fail(f"{probe_id} requires text `note` and `evidence`")
        if outcome == UNKNOWN or note.strip() in ("", UNKNOWN) or evidence.strip() in ("", UNKNOWN):
            unknown += 1
            continue
        if expected[0] != UNKNOWN and outcome != expected[0]:
            mismatches += 1
            print(f"MISMATCH {probe_id}: expected {expected[0]}, measured {outcome} -- {note}")
    return unknown, mismatches


def check_bench(payload: dict) -> tuple[int, int]:
    unknown = 0
    for key in BENCH_ENV:
        value = payload.get(key)
        if not isinstance(value, (str, int)):
            fail(f"bench requires top-level `{key}`")
        if value == UNKNOWN:
            unknown += 1
    points = payload.get("points")
    if not isinstance(points, dict):
        fail("bench requires a `points` object")
    missing = sorted(set(BENCH_POINTS) - set(points))
    if missing:
        fail(f"missing measurement point(s): {', '.join(missing)}")
    mismatches = 0
    for point_id, expected_entries in BENCH_POINTS.items():
        entry = points[point_id]
        if not isinstance(entry, dict):
            fail(f"{point_id} must hold an object")
        for cell in BENCH_CELLS:
            if cell not in entry:
                fail(f"{point_id} is missing cell `{cell}`")
            value = entry[cell]
            if value == UNKNOWN:
                unknown += 1
                continue
            if cell == "note":
                if not isinstance(value, str) or not value.strip():
                    fail(f"{point_id}.note must be non-empty text")
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                fail(f"{point_id}.{cell} must be a number or `unknown`, not {value!r}")
            if value < 0:
                fail(f"{point_id}.{cell} must not be negative")
        measured = entry["entries"]
        if measured != UNKNOWN and measured != expected_entries:
            mismatches += 1
            print(f"MISMATCH {point_id}: expected {expected_entries} entries, measured {measured}")
    return unknown, mismatches


def check_resolve_bench(payload: dict) -> tuple[int, int]:
    points = payload.get("points")
    if not isinstance(points, dict):
        fail("resolve-bench requires a `points` object")
    missing = sorted(set(BENCH_POINTS) - set(points))
    if missing:
        fail(f"missing measurement point(s): {', '.join(missing)}")
    unknown = 0
    mismatches = 0
    provenances: dict[str, dict] = {}
    for point_id, expected_entries in BENCH_POINTS.items():
        entry = points[point_id]
        if not isinstance(entry, dict):
            fail(f"{point_id} must hold an object")
        for cell in RESOLVE_CELLS:
            if cell not in entry:
                fail(f"{point_id} is missing cell `{cell}`")
            value = entry[cell]
            if value == UNKNOWN:
                unknown += 1
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                fail(f"{point_id}.{cell} must be a number or `unknown`, not {value!r}")
            if value < 0:
                fail(f"{point_id}.{cell} must not be negative")
        provenance = entry.get("provenance")
        if not isinstance(provenance, dict):
            fail(f"{point_id} requires its own `provenance` object")
        for key in RESOLVE_PROVENANCE:
            if key not in provenance:
                fail(f"{point_id}.provenance is missing `{key}`")
            if provenance[key] == UNKNOWN:
                unknown += 1
        if provenance.get("source_dirty"):
            fail(f"{point_id} was measured against a dirty source tree; re-measure from a clean checkout")
        provenances[point_id] = provenance
        measured = entry["entries"]
        if measured != UNKNOWN and measured != expected_entries:
            mismatches += 1
            print(f"MISMATCH {point_id}: expected {expected_entries} entries, measured {measured}")
    distinct = {json.dumps(value, sort_keys=True) for value in provenances.values()}
    if len(distinct) != 1:
        fail(
            "points do not share one provenance, so they cannot form one scaling curve: "
            + "; ".join(f"{point_id}={json.dumps(value, sort_keys=True)}" for point_id, value in provenances.items())
        )
    if unknown == 0:
        _report_scaling(points)
    return unknown, mismatches


UNCOVERED = "UNCOVERED"


def _tracked_test_ids(root: Path) -> set[str]:
    """Every `tests.<module>.<Class>.<method>` id, read from source without importing."""

    ids: set[str] = set()
    for path in sorted((root / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test"):
                    ids.add(f"tests.{path.stem}.{node.name}.{item.name}")
    return ids


def check_crosswalk(payload: dict) -> tuple[int, int]:
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        fail("smoke-crosswalk requires a non-empty `rows` list")
    known = _tracked_test_ids(Path(__file__).resolve().parents[2])
    if not known:
        fail("no committed test ids were found; the crosswalk cannot be graded")
    unknown = 0
    uncovered = 0
    for row in rows:
        if not isinstance(row, dict):
            fail("every row must hold an object")
        identifier = row.get("id")
        for key in ("id", "label", "source_line", "asserts", "covered_by", "evidence"):
            if key not in row:
                fail(f"{identifier} is missing `{key}`")
        evidence = row["evidence"]
        covered = row["covered_by"]
        if covered == UNKNOWN or not isinstance(evidence, str) or evidence.strip() in ("", UNKNOWN):
            unknown += 1
            continue
        if covered == UNCOVERED:
            uncovered += 1
            print(f"UNCOVERED {identifier}: {row['label']} -- {evidence}")
            continue
        if not isinstance(covered, list) or not covered:
            fail(f"{identifier}.covered_by must be a non-empty list of test ids, `{UNCOVERED}`, or `{UNKNOWN}`")
        absent = [item for item in covered if item not in known]
        if absent:
            fail(f"{identifier} names test id(s) that no committed test file defines: {absent}")
    return unknown, uncovered


def _report_scaling(points: dict) -> None:
    """Print section 8's published derivations so a reader replays them, never retypes them."""

    low, high = points["n1000"], points["n50000"]
    ratio = math.log(high["entries"] / low["entries"])
    print(
        "DERIVED time-exponent(1,000->50,000): "
        f"{math.log(high['resolve_cold_hit_ms'] / low['resolve_cold_hit_ms']) / ratio:.6f}"
    )
    print(
        "DERIVED raw-rss-exponent(1,000->50,000): "
        f"{math.log(high['peak_rss_kib'] / low['peak_rss_kib']) / ratio:.6f}"
    )
    incremental = [point["peak_rss_kib"] - point["rss_before_kib"] for point in (low, high)]
    print(
        "DERIVED incremental-rss-exponent(1,000->50,000): "
        f"{math.log(incremental[1] / incremental[0]) / ratio:.6f}"
    )
    for point_id in BENCH_POINTS:
        point = points[point_id]
        print(
            f"DERIVED {point_id}: cold_hit_ms={point['resolve_cold_hit_ms']:.6f} "
            f"warm_miss_ms={point['resolve_warm_miss_ms']:.6f} "
            f"incremental_rss_kib={point['peak_rss_kib'] - point['rss_before_kib']}"
        )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    path = Path(argv[1])
    payload = load(path)
    kind = payload.get("kind")
    if kind == "compose-matrix":
        unknown, mismatches = check_compose(payload)
        total = len(COMPOSE_PROBES)
    elif kind == "bench":
        unknown, mismatches = check_bench(payload)
        total = len(BENCH_POINTS) * len(BENCH_CELLS) + len(BENCH_ENV)
    elif kind == "resolve-bench":
        unknown, mismatches = check_resolve_bench(payload)
        total = len(BENCH_POINTS) * (len(RESOLVE_CELLS) + len(RESOLVE_PROVENANCE))
    elif kind == "smoke-crosswalk":
        unknown, mismatches = check_crosswalk(payload)
        total = len(payload["rows"])
    else:
        fail(f"kind {kind!r} must be 'compose-matrix', 'bench', 'resolve-bench' or 'smoke-crosswalk'")
    print(f"KIND: {kind}")
    print(f"CELLS: {total}")
    print(f"UNKNOWN-CELLS: {unknown}")
    print(f"{'UNCOVERED' if kind == 'smoke-crosswalk' else 'MISMATCHES'}: {mismatches}")
    return 0 if unknown == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
