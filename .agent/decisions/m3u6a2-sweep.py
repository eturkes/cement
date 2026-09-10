#!/usr/bin/env python3
"""M3.6a2 gate 8 — the reversion sweep: every clause dies when its own subject comes back.

One row per SUBPROPERTY, never one per clause. A clause is a conjunction, so a single row per
obligation certifies only that the obligation has SOME live content; the rows below undo one
obligation at a time and name the battery tests that must go red.

Gate 8's exclusion catalogue is FIXED in contract section 7, not chosen here, because an
open-ended exclusion list hides omissions behind the same word that legitimises them. Every
exclusion prints on the control line with its grounds and an explicit test-id selection, since
`unittest` has no negative selector. Cost never grounds an exclusion; insensitivity does.

    uv run python .agent/decisions/m3u6a2-sweep.py --sweep
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE_SHA = "da70a56"
SYSTEM = "src/cement_runtime/system.py"
BATTERY_MODULE = "tests.test_lifecycle_removal_battery"
BATTERY = f"{BATTERY_MODULE}.LifecycleRemovalBattery"

L01 = [
    f"{BATTERY}.test_l01_system_has_no_handle_attribute_under_every_access_route",
    f"{BATTERY}.test_l01_no_functiondef_named_handle_at_any_scope",
    f"{BATTERY}.test_l01_system_method_set_is_exact_baseline_subtraction",
]
L02 = [
    f"{BATTERY}.test_l02_system_has_no_request_status_attribute_under_the_same_four",
    f"{BATTERY}.test_l02_no_functiondef_named_request_status_at_any_scope",
]
L03 = [
    f"{BATTERY}.test_l03_system_has_no__outcome__fail_generation_or",
    f"{BATTERY}.test_l03_no_private_lifecycle_functiondefs_at_any_scope",
]
L04 = [
    f"{BATTERY}.test_l04_system___init___s_signature_is_exactly_self_database",
    f"{BATTERY}.test_l04_generation_lease_keyword_is_rejected",
]
L05_RAW = f"{BATTERY}.test_l05__lease_us_has_zero_raw_byte_occurrences_across_the_git"
L05_SHAPE = f"{BATTERY}.test_l05_now_upper_bound_is_bare_sqlite_maximum"
L05_KNOB = f"{BATTERY}.test_l05_generation_lease_seconds_has_zero_raw_src_occurrences"
L06_LITERAL = f"{BATTERY}.test_l06_lease_safe_literal_has_zero_raw_src_occurrences"
L08_RAW = f"{BATTERY}.test_l08_invalidated_generators_has_zero_raw_src_occurrences"
L09 = f"{BATTERY}.test_l09_zero_dangling_references_counted_as_tokenize_name_equality"
L10 = f"{BATTERY}.test_l10_system_py_s_from_models_import_list_loses_exactly"
L11_SET = f"{BATTERY}.test_l11_the_emitted_event_kind_vocabulary_is_exactly_the_sixteen"
L11_PRODUCER = f"{BATTERY}.test_l11_each_unique_deleted_event_producer_is_absent"
L19 = [
    f"{BATTERY}.test_l19_mechanical_readme_md_contains_zero_standalone_handle_words",
    f"{BATTERY}.test_l19_no_markdown_poll_state_table_survives",
    f"{BATTERY}.test_l19_generation_lease_claims_leave_snapshot_controls_intact",
]
L20 = [
    f"{BATTERY}.test_l20_mechanical_docs_architecture_md_s_contract_h2_ordered_list",
    f"{BATTERY}.test_l20_no_candidate_generation_lease_paragraph_survives",
]
L21 = [
    f"{BATTERY}.test_l21_mechanical_docs_adapter_protocol_md_matches_zero_deleted",
    f"{BATTERY}.test_l21_propose_failure_contract_survives_without_fallback_state",
]
L22 = [
    f"{BATTERY}.test_l22_mechanical_docs_threat_model_md_matches_zero_standalone",
    f"{BATTERY}.test_l22_ambiguity_leaves_the_three_surviving_quarantine_causes",
]
L23_PINS = f"{BATTERY}.test_l23_all_16_census_pins_in_section_5_are_green_after_the"
L23_FREEZE = f"{BATTERY}.test_l23_pin_bodies_freeze_unless_the_deleted_claim_forces_inversion"
L24 = [
    f"{BATTERY}.test_l24_no_human_facing_surface_gains_a_new_claim_about_a_deleted",
    f"{BATTERY}.test_l24_scanner_covers_all_human_markdown_and_grounds_generic_hits",
]
L25 = [
    f"{BATTERY}.test_l25_m3_5b_s_d15a_tests_test_cli_removal_battery_py_1131",
    f"{BATTERY}.test_l25_entire_d15_d22_freeze_family_is_git_range_scoped",
]
L26 = f"{BATTERY}.test_l26_the_four_p06_span_freezes_are_retired_with_their_history"
L27 = f"{BATTERY}.test_l27_m3_5b_s_d01_tests_test_cli_removal_battery_py_608"
L28 = f"{BATTERY}.test_l28_tests_test_authority_removal_py_118"
L29 = f"{BATTERY}.test_l29_m3u6a2_tripwires_py_s__freezes_detector_is_widened_to_see"
L31 = f"{BATTERY}.test_l31_existing_duplicate_regression_is_inverted_not_deleted"
D22C = (
    "tests.test_cli_removal_battery.RemovalObligationBatteryTests"
    ".test_d22c_the_opening_text_handle_request_fence_is_protected_and"
)

CLI_REMOVAL = "tests/test_cli_removal_battery.py"
TRIPWIRES = ".agent/decisions/m3u6a2-tripwires.py"

# `patch` restores one deleted subproperty by anchored edit; `revert_file` and `revert_frame`
# restore the pre-unit bytes of a whole document or of one named test function.
ROWS: tuple[dict[str, object], ...] = (
    {
        "id": "S01",
        "obligation": "L01",
        "subject": "`System.handle` exists again",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "    def _now(self) -> int:\n",
        "replacement": "    def handle(self, *args, **kwargs):\n        return None\n\n    def _now(self) -> int:\n",
        "killers": [*L01, L09],
    },
    {
        "id": "S02",
        "obligation": "L02",
        "subject": "`System.request_status` exists again",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "    def _now(self) -> int:\n",
        "replacement": "    def request_status(self, *args, **kwargs):\n        return None\n\n    def _now(self) -> int:\n",
        "killers": [*L02, L09],
    },
    {
        "id": "S03",
        "obligation": "L03",
        "subject": "`System._outcome` exists again",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "    def _now(self) -> int:\n",
        "replacement": "    def _outcome(self, *args, **kwargs):\n        return None\n\n    def _now(self) -> int:\n",
        "killers": [*L03, L09],
    },
    {
        "id": "S04",
        "obligation": "L03",
        "subject": "`System._fail_generation` exists again",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "    def _now(self) -> int:\n",
        "replacement": "    def _fail_generation(self, *args, **kwargs):\n        return None\n\n    def _now(self) -> int:\n",
        "killers": [*L03, L09],
    },
    {
        "id": "S05",
        "obligation": "L03",
        "subject": "`System._request_revision_is_current` exists again",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "    def _now(self) -> int:\n",
        "replacement": "    def _request_revision_is_current(self, *a, **k):\n        return None\n\n    def _now(self) -> int:\n",
        "killers": [*L03, L09],
    },
    {
        "id": "S06",
        "obligation": "L04",
        "subject": "the `generation_lease_seconds` constructor knob returns",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "        clock_us: Callable[[], int] | None = None,\n    ) -> None:\n",
        "replacement": (
            "        clock_us: Callable[[], int] | None = None,\n"
            "        generation_lease_seconds: int = 60,\n    ) -> None:\n"
        ),
        "killers": [*L04, L05_KNOB],
    },
    {
        "id": "S07",
        "obligation": "L05",
        "subject": "a raw `_lease_us` byte returns to tracked `src/`",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "_MAX_SQLITE_INTEGER = 2**63 - 1\n",
        "replacement": "_MAX_SQLITE_INTEGER = 2**63 - 1\n_lease_us = 0\n",
        "killers": [L05_RAW, L09],
    },
    {
        "id": "S08",
        "obligation": "L05",
        "subject": "`_now`'s upper bound stops being a bare `Name`",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "            or now > _MAX_SQLITE_INTEGER\n",
        "replacement": "            or now > _MAX_SQLITE_INTEGER - 0\n",
        "killers": [L05_SHAPE],
    },
    {
        "id": "S09",
        "obligation": "L06",
        "subject": "the dead `lease-safe` literal returns",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "_MAX_SQLITE_INTEGER = 2**63 - 1\n",
        "replacement": '_MAX_SQLITE_INTEGER = 2**63 - 1\n_NOTE = "lease-safe"\n',
        "killers": [L06_LITERAL],
    },
    {
        "id": "S10",
        "obligation": "L08",
        "subject": "a raw `invalidated_generators` byte returns",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "_MAX_SQLITE_INTEGER = 2**63 - 1\n",
        "replacement": "_MAX_SQLITE_INTEGER = 2**63 - 1\ninvalidated_generators = 0\n",
        "killers": [L08_RAW],
    },
    {
        "id": "S11",
        "obligation": "L10",
        "subject": "the seven dropped `.models` imports return",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": "from .models import (\n",
        "replacement": (
            "from .models import (\n    FallbackFailed,\n    InProgress,\n    Outcome,\n"
            "    ReconciliationRequired,\n    Rejected,\n    Resolved,\n    ReviewRequired,\n"
        ),
        "killers": [L10],
    },
    {
        "id": "S12",
        "obligation": "L11",
        "subject": "a deleted `request.` event kind gains a producer again",
        "kind": "patch",
        "path": SYSTEM,
        "anchor": 'kind="operation.registered",\n',
        "replacement": 'kind="request.resolved_by_artifact",\n',
        "killers": [L11_SET, L11_PRODUCER],
    },
    {
        "id": "S13",
        "obligation": "L19/L24",
        "subject": "`README.md` reverts to its pre-unit bytes",
        "kind": "revert_file",
        "path": "README.md",
        "killers": [*L19, *L24, D22C],
    },
    {
        "id": "S14",
        "obligation": "L20",
        "subject": "`docs/architecture.md` reverts to its pre-unit bytes",
        "kind": "revert_file",
        "path": "docs/architecture.md",
        "killers": L20,
    },
    {
        "id": "S15",
        "obligation": "L21",
        "subject": "`docs/adapter-protocol.md` reverts to its pre-unit bytes",
        "kind": "revert_file",
        "path": "docs/adapter-protocol.md",
        "killers": L21,
    },
    {
        "id": "S16",
        "obligation": "L22",
        "subject": "`docs/threat-model.md` reverts to its pre-unit bytes",
        "kind": "revert_file",
        "path": "docs/threat-model.md",
        "killers": L22,
    },
    {
        "id": "S17",
        "obligation": "L23",
        "subject": "D23's inverted retry-advice control reverts",
        "kind": "revert_frame",
        "path": "tests/test_cli_channels_battery.py",
        "name": "test_d23_there_is_no_idempotency_two_byte_identical_submissions_ret",
        "killers": [L23_FREEZE, L23_PINS],
    },
    {
        "id": "S18",
        "obligation": "L23",
        "subject": "D22a's inverted library-route pin reverts",
        "kind": "revert_frame",
        "path": CLI_REMOVAL,
        "name": "test_d22a_direction_cli_route_every_cli_route_locus_was_rewritte",
        "killers": [L23_FREEZE, L23_PINS],
    },
    {
        "id": "S19",
        "obligation": "L23",
        "subject": "B27's inverted lifecycle-value pin reverts",
        "kind": "revert_frame",
        "path": "tests/test_proposal_binding_battery.py",
        "name": "test_b27_no_public_surface_retains_the_unqualified",
        "killers": [L23_FREEZE, L23_PINS],
    },
    {
        "id": "S20",
        "obligation": "L23",
        "subject": "D34's inverted normative-doc pin reverts",
        "kind": "revert_frame",
        "path": "tests/test_submission_battery.py",
        "name": "test_d34_readme_and_the_three_normative_docs",
        "killers": [L23_FREEZE, L23_PINS],
    },
    {
        "id": "S21",
        "obligation": "L23",
        "subject": "D25's permitted register delta reverts",
        "kind": "revert_frame",
        "path": CLI_REMOVAL,
        "name": "test_d25_rewritten_human_facing_prose_holds_the_project_registe",
        "killers": [L23_FREEZE],
    },
    {
        "id": "S22",
        "obligation": "L25",
        "subject": "D15a's live-tree read returns",
        "kind": "revert_frame",
        "path": CLI_REMOVAL,
        "name": "test_d15a_the_six_runtime_modules_stay_byte_identical_to_their_3",
        "killers": L25,
    },
    {
        "id": "S23",
        "obligation": "L26",
        "subject": "the P06 size freeze reads live source again",
        "kind": "revert_frame",
        "path": "tests/test_submission_battery.py",
        "name": "test_p06_handle_is_12_866_b_1182130a2b3a",
        "killers": [L26],
    },
    {
        "id": "S24",
        "obligation": "L26",
        "subject": "the P06 convention freeze reads live source again",
        "kind": "revert_frame",
        "path": "tests/test_submission_battery.py",
        "name": "test_p06_three_slicing_conventions_are_distinct",
        "killers": [L26],
    },
    {
        "id": "S25",
        "obligation": "L26",
        "subject": "the unit-baseline P06 freeze reads live source again",
        "kind": "revert_frame",
        "path": "tests/test_submission.py",
        "name": "test_handle_is_byte_identical_to_the_unit_baseline",
        "killers": [L26],
    },
    {
        "id": "S26",
        "obligation": "L26",
        "subject": "the migration battery's P06 freeze reads live source again",
        "kind": "revert_frame",
        "path": "tests/test_migration_battery.py",
        "name": "test_d25_m3_3_s_p06_byte_span_freeze_on_system_handle_stays_green",
        "killers": [L26],
    },
    {
        "id": "S27",
        "obligation": "L27",
        "subject": "D01's inverted ships-both-methods pin reverts",
        "kind": "revert_frame",
        "path": CLI_REMOVAL,
        "name": "test_d01_m3_5b_ships_system_handle_and_system_request_status_as",
        "killers": [L27],
    },
    {
        "id": "S28",
        "obligation": "L28",
        "subject": "the frozen constructor shape reverts to four parameters",
        "kind": "revert_frame",
        "path": "tests/test_authority_removal.py",
        "name": "test_system_constructor_shape",
        "killers": [L28],
    },
    {
        "id": "S29",
        "obligation": "L29",
        "subject": "the freeze detector loses the SPAN shape",
        "kind": "patch",
        "path": TRIPWIRES,
        "anchor": "    return module_shape or span_shape\n",
        "replacement": "    return module_shape\n",
        "killers": [L29],
    },
    {
        "id": "S30",
        "obligation": "L31",
        "subject": "the duplicate-gate regression reverts to its lifecycle spelling",
        "kind": "revert_frame",
        "path": "tests/test_system.py",
        "name": "test_function_verification_duplicate_gate_and_runtime_defenses",
        "killers": [L31],
    },
)

# FIXED by contract section 7. Each names an insensitive subject and the test-id selection a
# reader reruns to see it pass regardless of any working-tree edit.
EXCLUSIONS: tuple[tuple[str, str], ...] = (
    (
        f"{CLI_REMOVAL}::test_d22b_direction_library_route_every_library_api_locus_is_byt",
        "git-only endpoints; no working-tree mutation can redden it",
    ),
    (
        f"{CLI_REMOVAL}::test_d15a AFTER the repair",
        "its six per-module comparisons became the closed range 36f7890..1146421",
    ),
    (
        f"{BATTERY_MODULE}::test_l26 three historical span figures",
        "derived from 3b7769b; immutable under any tree edit",
    ),
    (
        f"{BATTERY_MODULE}::test_l30 D16, BOTH halves",
        "expected path set and per-path blob comparison both read 6fb4d92..dc4ab5e",
    ),
)


def _git_text(relative: str) -> str:
    return subprocess.run(
        ["git", "show", f"{BASE_SHA}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _purge_pycache() -> None:
    for directory in ROOT.rglob("__pycache__"):
        shutil.rmtree(directory, ignore_errors=True)


def _run_tests(ids: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "unittest", *ids],
        cwd=ROOT,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _frame_span(source: str, name: str) -> tuple[int, int] | None:
    import ast

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
            return start, node.end_lineno or start
    return None


def _apply(row: dict[str, object]) -> str | None:
    """Return an error string, or None once the reversion is on disk."""
    relative = str(row["path"])
    target = ROOT / relative
    current = target.read_text(encoding="utf-8")
    kind = row["kind"]
    if kind == "patch":
        anchor, replacement = str(row["anchor"]), str(row["replacement"])
        occurrences = current.count(anchor)
        if occurrences != 1:
            return f"anchor occurs {occurrences} times, not once"
        target.write_text(current.replace(anchor, replacement, 1), encoding="utf-8")
        return None
    if kind == "revert_file":
        baseline = _git_text(relative)
        if baseline == current:
            return "the file is already at its pre-unit bytes"
        target.write_text(baseline, encoding="utf-8")
        return None
    if kind == "revert_frame":
        name = str(row["name"])
        here, there = _frame_span(current, name), _frame_span(_git_text(relative), name)
        if here is None or there is None:
            return f"{name} is missing from the working tree or from {BASE_SHA}"
        baseline_lines = _git_text(relative).splitlines(keepends=True)
        lines = current.splitlines(keepends=True)
        replacement = baseline_lines[there[0] - 1 : there[1]]
        rewritten = lines[: here[0] - 1] + replacement + lines[here[1] :]
        if rewritten == lines:
            return f"{name} is already byte-identical to {BASE_SHA}"
        target.write_text("".join(rewritten), encoding="utf-8")
        return None
    return f"unknown kind {kind!r}"


def sweep() -> int:
    paths = sorted({str(row["path"]) for row in ROWS})
    dirty = subprocess.run(
        ["git", "status", "--porcelain", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        print(f"ABORT: the sweep rewrites these paths in place and they are not clean\n{dirty}")
        return 1

    for subject, grounds in EXCLUSIONS:
        print(f"EXCLUDED {subject} :: {grounds}")

    every_killer = sorted({killer for row in ROWS for killer in row["killers"]})
    _purge_pycache()
    control = _run_tests(every_killer)
    if control.returncode != 0:
        print("PRISTINE CONTROL FAILED; every survivor below would be a phantom")
        print(control.stdout[-3000:])
        print(control.stderr[-3000:])
        return 1
    print(f"CONTROL: {len(every_killer)} killer tests green on the unreverted tree")

    survivors: list[str] = []
    for row in ROWS:
        relative = str(row["path"])
        error = _apply(row)
        if error:
            survivors.append(f"{row['id']} {error}")
            print(f"{row['id']} {row['obligation']} UNAPPLIED {row['subject']} :: {error}")
            subprocess.run(["git", "checkout", "--", relative], cwd=ROOT, check=True)
            continue
        try:
            _purge_pycache()
            result = _run_tests(list(row["killers"]))
        finally:
            subprocess.run(["git", "checkout", "--", relative], cwd=ROOT, check=True)
            _purge_pycache()
        died = result.returncode != 0
        if not died:
            survivors.append(f"{row['id']} ({row['obligation']}) {row['subject']}")
        print(
            f"{row['id']} {row['obligation']} {'died' if died else 'SURVIVED'} {row['subject']} "
            f":: {' '.join(name.rsplit('.', 1)[1] for name in row['killers'])}"
        )

    residue = subprocess.run(
        ["git", "status", "--porcelain", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if residue:
        survivors.append(f"the sweep left the tree dirty: {residue}")
    print(f"ROWS: {len(ROWS)} SURVIVORS: {len(survivors)}")
    for line in survivors:
        print(f"SURVIVOR: {line}")
    print(f"RESULT: {'PASS' if not survivors else 'FAIL'}")
    return 1 if survivors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M3.6a2 gate 8 reversion sweep.")
    parser.add_argument("--sweep", action="store_true", help="run the catalogue")
    args = parser.parse_args(argv)
    if not args.sweep:
        parser.error("pass --sweep")
    return sweep()


if __name__ == "__main__":
    raise SystemExit(main())
