#!/usr/bin/env python3
"""M3.6a2 gate 7 — mutation catalogue over the logic this unit LEAVES BEHIND.

A removal unit's risk is not the deleted span; it is the surviving code the deletion touched. Every
mutant here edits code an obligation claims to pin (L04-L08, L16-L18) and names the battery test
that must die. A survivor means the obligation's test grades a spelling rather than the behaviour.

Each mutant addresses its target by a UNIQUE anchor (`count == 1`, asserted), proves liveness by
showing its killers green in the pristine control and red under the edit, and restores the tree in a
`finally` block. `PYTHONDONTWRITEBYTECODE=1` plus a `__pycache__` purge is mandatory: CPython
invalidates bytecode on `(mtime, size)`, so a length-preserving edit inside one mtime-second runs
the ORIGINAL code and reports a live mutant as surviving.

    uv run python .agent/decisions/m3u6a2-mutants.py --replay
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SYSTEM = "src/cement_runtime/system.py"
BATTERY = "tests.test_lifecycle_removal_battery.LifecycleRemovalBattery"

L04_SIGNATURE = f"{BATTERY}.test_l04_system___init___s_signature_is_exactly_self_database"
L04_KEYWORD = f"{BATTERY}.test_l04_generation_lease_keyword_is_rejected"
L05_RAW = f"{BATTERY}.test_l05_generation_lease_seconds_has_zero_raw_src_occurrences"
L05_BOUND = f"{BATTERY}.test_l05_now_upper_bound_is_bare_sqlite_maximum"
L06_BOUNDARY = f"{BATTERY}.test_l06__now_s_upper_bound_carries_no_lease_term_a_clock_returning"
L07_SOURCE = f"{BATTERY}.test_l07_revise_operation_performs_no_requests_write_the_source"
L08_PAYLOAD = f"{BATTERY}.test_l08_the_operation_revised_event_payload_read_back_from_the"
L16_ACCEPT = f"{BATTERY}.test_l16_the_proposal_round_trip_still_ends_with_the_private"
L16_REJECT = f"{BATTERY}.test_l16_rejected_proposal_writes_the_private_rejected_variant"
L17_REVISION = f"{BATTERY}.test_l17_revise_operation_still_bumps_the_revision_by_one_and_still"
L18_NOW = f"{BATTERY}.test_l18__now_still_rejects_a_non_int_a_bool_a_negative_value_all"
L18_CLOCK = f"{BATTERY}.test_l18_non_callable_clock_keeps_exact_validation_error"

CATALOGUE: tuple[dict[str, object], ...] = (
    {
        "id": "M01",
        "obligation": "L06",
        "note": "the accepted boundary value becomes a rejection",
        "anchor": "            or now > _MAX_SQLITE_INTEGER\n",
        "replacement": "            or now >= _MAX_SQLITE_INTEGER\n",
        "killers": [L06_BOUNDARY],
    },
    {
        "id": "M02",
        "obligation": "L06",
        "note": "a silent re-wording of the StateError text",
        "anchor": '"clock must return a signed 64-bit microsecond timestamp"',
        "replacement": '"clock must return a valid timestamp"',
        "killers": [L06_BOUNDARY, L18_NOW],
    },
    {
        "id": "M03",
        "obligation": "L18",
        "note": "the non-int and bool rejection loses its guard",
        "anchor": "            type(now) is not int\n",
        "replacement": "            not isinstance(now, int)\n",
        "killers": [L18_NOW],
    },
    {
        "id": "M04",
        "obligation": "L18",
        "note": "the negative-timestamp rejection disappears",
        "anchor": "            or now < 0\n",
        "replacement": "",
        "killers": [L18_NOW],
    },
    {
        "id": "M05",
        "obligation": "L18",
        "note": "the constructor stops rejecting a non-callable clock",
        "anchor": "        if clock_us is not None and not callable(clock_us):\n",
        "replacement": "        if False:\n",
        "killers": [L18_CLOCK],
    },
    {
        "id": "M06",
        "obligation": "L17",
        "note": "the revision bump is no longer by one",
        "anchor": "            revision = previous + 1\n",
        "replacement": "            revision = previous + 2\n",
        "killers": [L17_REVISION],
    },
    {
        "id": "M07",
        "obligation": "L17",
        "note": "the retirement reason is re-worded",
        "anchor": "                    status_reason = 'operation revised'\n",
        "replacement": "                    status_reason = 'revised'\n",
        "killers": [L17_REVISION],
    },
    {
        "id": "M08",
        "obligation": "L17",
        "note": "one retired status drops out of the filter",
        "anchor": (
            "                WHERE partition = ? AND operation = ? AND operation_revision = ?\n"
            "                  AND status IN ('draft', 'verified', 'promoted')\n"
        ),
        "replacement": (
            "                WHERE partition = ? AND operation = ? AND operation_revision = ?\n"
            "                  AND status IN ('draft', 'verified')\n"
        ),
        "killers": [L17_REVISION],
    },
    {
        "id": "M09",
        "obligation": "L08",
        "note": "the payload loses a key",
        "anchor": '                    "policy_hash": policy_json.digest,\n',
        "replacement": "",
        "killers": [L08_PAYLOAD],
    },
    {
        "id": "M10",
        "obligation": "L08",
        "note": "a payload key keeps its name and loses its binding",
        "anchor": '                    "previous_revision": previous,\n',
        "replacement": '                    "previous_revision": revision,\n',
        "killers": [L08_PAYLOAD],
    },
    {
        "id": "M11",
        "obligation": "L08",
        "note": "the recorded actor is hard-coded instead of supplied",
        "anchor": '                    "revised_by": revised_by,\n',
        "replacement": '                    "revised_by": "system",\n',
        "killers": [L08_PAYLOAD],
    },
    {
        "id": "M12",
        "obligation": "L07",
        "note": "revise_operation regains a `requests` write that executes zero rows",
        "anchor": "                (partition, operation, previous),\n            )\n            _event(\n",
        "replacement": (
            "                (partition, operation, previous),\n            )\n"
            "            connection.execute(\n"
            "                \"UPDATE requests SET status = 'stale' WHERE 0\"\n"
            "            )\n"
            "            _event(\n"
        ),
        "killers": [L07_SOURCE],
    },
    {
        "id": "M13",
        "obligation": "L16",
        "note": "the resolved request row stops being the confirmed variant",
        "anchor": "SET status = 'resolved', output_json = ?, source_kind = 'confirmed',\n",
        "replacement": "SET status = 'resolved', output_json = ?, source_kind = 'artifact',\n",
        "killers": [L16_ACCEPT],
    },
    {
        "id": "M14",
        "obligation": "L16",
        "note": "the rejection branch writes the accept status",
        "anchor": "            UPDATE requests SET status = 'rejected', updated_at_us = ?\n",
        "replacement": "            UPDATE requests SET status = 'resolved', updated_at_us = ?\n",
        "killers": [L16_REJECT],
    },
    {
        "id": "M15",
        "obligation": "L04/L05",
        "note": "the deleted lease knob returns to the constructor",
        "anchor": "        clock_us: Callable[[], int] | None = None,\n    ) -> None:\n",
        "replacement": (
            "        clock_us: Callable[[], int] | None = None,\n"
            "        generation_lease_seconds: int = 60,\n    ) -> None:\n"
        ),
        "killers": [L04_SIGNATURE, L04_KEYWORD, L05_RAW],
    },
)


def _purge_pycache() -> None:
    for directory in ROOT.rglob("__pycache__"):
        shutil.rmtree(directory, ignore_errors=True)


def _run_tests(ids: list[str]) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-m", "unittest", *ids],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
    )


def _restore(relative: str) -> None:
    subprocess.run(["git", "checkout", "--", relative], cwd=ROOT, check=True)


def replay() -> int:
    target = ROOT / SYSTEM
    dirty = subprocess.run(
        ["git", "status", "--porcelain", SYSTEM],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        print(f"ABORT: `{SYSTEM}` is not clean; a sweep patches it in place\n{dirty}")
        return 1

    every_killer = sorted({killer for row in CATALOGUE for killer in row["killers"]})
    _purge_pycache()
    control = _run_tests(every_killer)
    if control.returncode != 0:
        print("PRISTINE CONTROL FAILED; every survivor below would be a phantom")
        print(control.stderr[-4000:])
        return 1
    print(f"CONTROL: {len(every_killer)} killer tests green on the unmutated tree")

    survivors: list[str] = []
    pristine = target.read_text(encoding="utf-8")
    for row in CATALOGUE:
        anchor, replacement = str(row["anchor"]), str(row["replacement"])
        occurrences = pristine.count(anchor)
        if occurrences != 1:
            survivors.append(f"{row['id']} anchor occurs {occurrences} times, not once")
            print(f"{row['id']} {row['obligation']} ANCHOR-{occurrences} {row['note']}")
            continue
        mutated = pristine.replace(anchor, replacement, 1)
        assert mutated != pristine, row["id"]
        try:
            target.write_text(mutated, encoding="utf-8")
            _purge_pycache()
            result = _run_tests(list(row["killers"]))
        finally:
            _restore(SYSTEM)
            _purge_pycache()
        killed = result.returncode != 0
        if not killed:
            survivors.append(f"{row['id']} ({row['obligation']}) {row['note']}")
        print(
            f"{row['id']} {row['obligation']} {'killed' if killed else 'SURVIVED'} "
            f"{row['note']} :: {' '.join(name.rsplit('.', 1)[1] for name in row['killers'])}"
        )

    residue = subprocess.run(
        ["git", "status", "--porcelain", SYSTEM],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if residue:
        survivors.append(f"the sweep left `{SYSTEM}` dirty: {residue}")
    print(f"MUTANTS: {len(CATALOGUE)} SURVIVORS: {len(survivors)}")
    for line in survivors:
        print(f"SURVIVOR: {line}")
    print(f"RESULT: {'PASS' if not survivors else 'FAIL'}")
    return 1 if survivors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M3.6a2 gate 7 mutation replay.")
    parser.add_argument("--replay", action="store_true", help="run the catalogue")
    args = parser.parse_args(argv)
    if not args.replay:
        parser.error("pass --replay")
    return replay()


if __name__ == "__main__":
    raise SystemExit(main())
