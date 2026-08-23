#!/usr/bin/env python3
"""Structural validator for M3.2a spike probe matrices.

Usage: uv run python .agent/decisions/m3u2a-matrix-validate.py <matrix.json>

Exit 0 = structurally valid AND no probe left `unknown`. Exit 1 = structural defect
or unfilled probe. Expectation MISMATCHES never fail the run: a mismatch is the
measurement this unit is buying, so it is reported and counted, never suppressed.

Two matrices that both exit 0 are mechanically comparable probe-by-probe, which is
what lets the two spike advocates serve as one differential instrument.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUTCOMES = {"ok", "denied", "error", "wrong_target", "unknown"}

# id -> (expected outcome, what `ok` means for this probe)
PROBES: dict[str, tuple[str, str]] = {
    # Read path: the enforced-read capability must still answer every one of these.
    "R1_select_user_table": ("ok", "SELECT over a populated user table returns its rows"),
    "R2_pragma_user_version_read": ("ok", "PRAGMA user_version reads back 2"),
    "R3_pragma_application_id_read": ("ok", "PRAGMA application_id reads back"),
    "R4_select_sqlite_schema": ("ok", "SELECT over sqlite_schema returns the schema objects"),
    "R5_validate_ledger_call": ("ok", "store._validate_ledger(connection) returns without raising"),
    "R6_connect_setup_pragmas": ("ok", "all five _connect pragmas execute; notes record each result"),
    "R7_setconfig_defensive": ("ok", "setconfig DEFENSIVE/TRUSTED_SCHEMA applies, or is absent on this build"),
    "R8_two_reads_one_snapshot": ("ok", "two SELECTs run with connection.in_transaction True throughout"),
    # Write denial: every one must be refused by the capability, not merely unused.
    "W1_insert": ("denied", ""),
    "W2_update": ("denied", ""),
    "W3_delete": ("denied", ""),
    "W4_create_table": ("denied", ""),
    "W5_drop_trigger": ("denied", ""),
    "W6_alter_table": ("denied", ""),
    "W7_pragma_user_version_write": ("denied", ""),
    "W8_pragma_journal_mode_wal": ("denied", ""),
    "W9_pragma_application_id_write": ("denied", ""),
    "W10_create_temp_table": ("denied", ""),
    "W11_attach_and_write": ("denied", ""),
    "W12_explicit_commit": ("denied", ""),
    "W13_vacuum": ("denied", ""),
    "W14_savepoint_insert": ("denied", ""),
    "W15_pragma_foreign_keys_off": ("denied", ""),
    "W16_writable_schema_update": ("denied", ""),
    "W17_reindex_analyze": ("denied", ""),
    # Structural properties.
    "S1_iterdump_identical": ("ok", "full iterdump() byte-identical before and after the read transaction"),
    "S2_file_bytes_identical": ("ok", "ledger file size and sha256 identical before and after"),
    "S3_missing_file_refused": ("denied", "opening a nonexistent path fails AND creates no file"),
    "S4_uri_hazard_paths": ("ok", "every hazardous path reads back its own marker row"),
    "S5_concurrent_writer_visibility": ("ok", "reader does not observe a mid-transaction commit; writer behavior in notes"),
    "S6_rollback_vs_commit": ("ok", "rollback leaves bytes identical; notes state how commit differs"),
    "S7_setup_cost_1000_opens": ("ok", "notes carry us/open for baseline _connect and for this alternative"),
}

REQUIRED_TOP = ("alternative", "mechanisms", "sqlite_version", "python_version", "probes")
REQUIRED_PROBE = ("id", "expected", "outcome", "exc_type", "message", "notes")


def fail(problems: list[str]) -> int:
    for problem in problems:
        print(f"INVALID: {problem}")
    print(f"STRUCTURE: FAIL ({len(problems)} problems)")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: m3u2a-matrix-validate.py <matrix.json>")
        return 2
    path = Path(argv[1])
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return fail([f"unreadable matrix: {exc}"])

    problems: list[str] = []
    if not isinstance(document, dict):
        return fail(["top level must be a JSON object"])
    for key in REQUIRED_TOP:
        if key not in document:
            problems.append(f"missing top-level key {key!r}")
    if not isinstance(document.get("mechanisms"), list) or not document.get("mechanisms"):
        problems.append("'mechanisms' must be a non-empty list of the enforcement mechanisms in force")
    probes = document.get("probes")
    if not isinstance(probes, dict):
        return fail(problems + ["'probes' must be a JSON object keyed by probe id"])

    missing = sorted(set(PROBES) - set(probes))
    extra = sorted(set(probes) - set(PROBES))
    problems.extend(f"missing probe {name!r}" for name in missing)
    problems.extend(f"unknown probe {name!r}" for name in extra)

    unknown: list[str] = []
    mismatches: list[tuple[str, str, str]] = []
    for name, expected_pair in PROBES.items():
        probe = probes.get(name)
        if probe is None:
            continue
        if not isinstance(probe, dict):
            problems.append(f"probe {name!r} must be an object")
            continue
        for key in REQUIRED_PROBE:
            if key not in probe:
                problems.append(f"probe {name!r} missing key {key!r}")
        if probe.get("id") != name:
            problems.append(f"probe {name!r} carries mismatched id {probe.get('id')!r}")
        expected = expected_pair[0]
        if probe.get("expected") != expected:
            problems.append(f"probe {name!r} expected must be {expected!r}, found {probe.get('expected')!r}")
        outcome = probe.get("outcome")
        if outcome not in OUTCOMES:
            problems.append(f"probe {name!r} outcome {outcome!r} not in {sorted(OUTCOMES)}")
            continue
        if outcome == "unknown":
            unknown.append(name)
        elif outcome != expected:
            mismatches.append((name, expected, str(outcome)))
        if outcome not in ("ok", "unknown") and not str(probe.get("message", "")).strip():
            problems.append(f"probe {name!r} is {outcome!r} and must carry a non-empty message")

    filled = len(PROBES) - len(unknown) - len(missing)
    print(f"FLUSHED: {filled}/{len(PROBES)}")
    for name, expected, outcome in mismatches:
        print(f"MISMATCH: {name} expected={expected} outcome={outcome}")
    print(f"MISMATCHES: {len(mismatches)}")
    if unknown:
        print(f"UNKNOWN: {len(unknown)} -> {', '.join(unknown)}")
    if problems:
        return fail(problems)
    if unknown:
        print("STRUCTURE: OK but probes remain unknown")
        return 1
    print("STRUCTURE: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
