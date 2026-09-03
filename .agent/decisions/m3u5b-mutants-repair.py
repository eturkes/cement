#!/usr/bin/env python3
"""Idempotent repair of `m3u5b-mutants.json`, replayable from the harvested catalogue.

    uv run python .agent/decisions/m3u5b-mutants-repair.py          # apply, report
    uv run python .agent/decisions/m3u5b-mutants-repair.py --check  # verify, never write

The catalogue arrived from `wt/gate-m3u5b-1` with 48 filled rows and three defects its own
`note` fields already recorded as `baseline=misdirected` / `baseline=survived`. The teammate
measured them and did not repair them. Each repair below is derived from the CONTRACT, never
from the sweep output, so re-deriving it does not require rerunning the sweep.

1. THIRTEEN D18 ROWS NAMED THE WRONG TARGET. A D18 clause obligation reads "frame F, re-based
   in place, preserves property P". The battery's `test_d18x` is a STATIC check on frame F's own
   source text, so a mutation of `src/cement_runtime/cli.py` cannot redden it -- the frame's
   bytes never move. The test that protects P is frame F ITSELF, which is what the contract's
   D18 table names in its `| frame |` column. Every retarget below is read off that column.

2. M06 AIMED AT D06 AND EXERCISED D10. Reinserting `--request-id` on a surviving leaf restores
   a removed SPELLING, which is D10's obligation. D06 is the ABBREVIATION property, pinned by
   `parse_args(["compile", "operation", "--act", "actor"])`. Making `--act` ambiguous is what
   violates it, so the mutation adds a colliding `--action` instead. That perturbs a preserved
   invariant rather than restoring removed content, so `kind` becomes `sensitivity`.

3. M31 REINSERTED DEAD CODE. Its source construction was guarded by `args.command == "handle"`,
   and `handle` no longer exists, so the branch is unreachable and D03's property -- dispatch
   reaches no source -- still held. Only the text-level D09 saw it. The mutation now hands the
   constructor a real object on every route, which is the violation D03 is built to catch.

Rows are matched by `id`; every write is a whole-field replacement, so a second run is a no-op.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

CATALOGUE = pathlib.Path(__file__).resolve().parent / "m3u5b-mutants.json"

# Read off the contract's D18 `| frame |` column: clause -> the frame that carries the property.
RETARGET = {
    "M22": "test_v27_the_parser_census_moves_28_to_30_leaves_and_35_to_37_nodes",
    "M23": "test_v28_cross_leaf_option_isolation_holds_in_both_directions_for_b",
    "M24": "test_x04_each_completed_resolve_dispatch_calls_system_resolve_once",
    "M25": "test_x11_the_aggregate_transport_cap_is_derived_from_one_exported_p",
    "M26": "test_x21_both_new_parser_nodes_omit_every_source_option_as_well_as",
    "M27": "test_x22_all_twenty_eight_baseline_leaf_paths_survive_by_identity_r",
    "M28": "test_x26_commandcandidatesource_remains_imported_and_the_existing_h",
    "M29": "test_v05_a_configured_candidate_source_is_never_called_by_either_ne",
    "M31": "test_d03_dispatch_calls_system_resolve_exactly_once_and_reaches_no",
    "M32": "test_d16_the_aggregate_cap_is_2_default_max_bytes_provenance_max_by",
    "M33": "test_d24_zero_source_calls_zero_system_propose_calls_and_zero_sourc",
    "M34": "test_d25_the_parser_census_moves_28_30_leaves_and_35_37_nodes_deriv",
    "M35": "test_d26_preserved_and_asserted_independently_store_py_byte_identic",
    "M36": "test_d27_b02_drops_cli_py_from_its_frozen_tuple_and_keeps_command_s",
}

REMUTATE = {
    "M06": {
        "kind": "sensitivity",
        "replacement": (
            '    compile_command.add_argument("--actor", default="local-system")\n'
            '    compile_command.add_argument("--action", default="none")\n'
        ),
        "note": (
            "aims at D06's ABBREVIATION property: a colliding `--action` makes `--act` "
            "ambiguous, so `parse_args([\"compile\", \"operation\", \"--act\", \"actor\"])` "
            "raises instead of resolving. Reinserting `--request-id` restored a removed "
            "SPELLING and exercised D10 instead."
        ),
    },
    "M31": {
        "replacement": "    system = System(args.db, candidate_source=object())\n",
        "note": (
            "hands the constructor a real candidate source on EVERY route. The previous "
            "form guarded construction on `args.command == \"handle\"`, which no longer "
            "parses, so the branch was unreachable and D03's property still held."
        ),
    },
}


def repair(rows: list[dict[str, object]]) -> list[str]:
    changes: list[str] = []
    index = {str(row["id"]): row for row in rows}
    for identifier, target in RETARGET.items():
        row = index[identifier]
        if row["target_test"] != target:
            changes.append(f"{identifier} target_test -> {target}")
            row["target_test"] = target
    for identifier, fields in REMUTATE.items():
        row = index[identifier]
        for field, value in fields.items():
            if row.get(field) != value:
                changes.append(f"{identifier} {field} rewritten")
                row[field] = value
    return changes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv[1:])

    document = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    changes = repair(document["rows"])
    for line in changes:
        print(line)
    print(f"CHANGES: {len(changes)}")
    if args.check:
        print("CLEAN" if not changes else "DIRTY")
        return 1 if changes else 0
    if changes:
        CATALOGUE.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE {CATALOGUE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
