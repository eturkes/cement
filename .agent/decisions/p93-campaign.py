#!/usr/bin/env python3
"""p93 campaign — subject-scoped default-operator credit for the pins IMPLEMENT strengthened.

Usage: uv run python .agent/decisions/p93-campaign.py [--rev REV] [--workers N] [--only SUBSTRING]
Runs `.agent/mutate <pin> --subject …` per pin below (subjects = `.agent/decisions/survivor-subjects.json`,
a `module.py` key = `src/cement_runtime/module.py`, a key holding `/` = that repo path) and appends
each run's output to `.agent/decisions/p93-mutate.txt`, the record `.agent/survivor-triage` reads.
rc 0 = every run completed; 1 = a run failed (its output still appended).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SUBJECTS = ROOT / ".agent/decisions/survivor-subjects.json"
RECORD = ROOT / ".agent/decisions/p93-mutate.txt"
SW = "tests.test_switch_battery.SwitchBattery."
P1 = "tests.test_projection_lifecycle_battery.ProjectionLifecycleBattery."
P2 = "tests.test_projection_lifecycle_battery.ProjectionLifecycleBatteryII."
OW = "tests.test_open_webui_example.CaptureBindingBattery."
PINS = (
    SW + "test_w1_off_reads_the_switch_and_operation_rows_alone",
    SW + "test_w5_a_revision_never_unpins_but_a_suspension_does",
    SW + "test_w5c_after_a_reset_suspending_a_retired_member_fails_the_pin",
    SW + "test_w10_one_read_snapshot_serves_switch_version_and_checks",
    P1 + "test_l2_each_refusal_writes_nothing",
    P1 + "test_l2_a_program_no_example_satisfies_is_refused",
    P1 + "test_l3_a_program_change_retires_stale_builds_and_keeps_promoted_ones",
    P1 + "test_l5_the_bundle_answers_raw_input_ledger_free_like_resolve",
    P1 + "test_l8_an_identical_program_is_a_no_op_and_a_b_a_rebuilds",
    P1 + "test_v1_an_invalid_program_is_refused_before_any_write",
    P1 + "test_l18_verification_fails_an_interpreter_that_ignores_a_missing_last_structural_line",
    P2 + "test_l7_a_fabricated_mixed_set_fails_projection_uniform_alone_of_its_cause",
    P2 + "test_l20_a_full_memo_never_repeats_a_projection_inside_one_verification",
    OW + "test_x6_each_pair_binds_its_own_source_id_and_provenance",
    OW + "test_x6_the_full_reply_is_retained_whenever_the_provenance_fits",
    OW + "test_e3_a_malformed_peer_never_drops_a_valid_pair",
    OW + "test_e3_a_record_without_its_output_writes_nothing",
    OW + "test_e4_without_a_current_message_id_nothing_is_retained",
    OW + "test_e4_a_retention_or_notification_failure_never_reaches_open_webui",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rev", default="HEAD")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    subjects = json.loads(SUBJECTS.read_text(encoding="utf-8"))
    rc = 0
    for pin in (pin for pin in PINS if args.only in pin):
        flags = []
        for subject in subjects[pin]:
            key, _, name = subject.partition(":")
            path = key if "/" in key else f"src/cement_runtime/{key}"
            flags += ["--subject", f"{path}:{name}"]
        run = subprocess.run([sys.executable, str(ROOT / ".agent/mutate"), pin, "--rev", args.rev,
                              "--workers", str(args.workers), *flags],
                             cwd=ROOT, capture_output=True, text=True, check=False)
        with RECORD.open("a", encoding="utf-8") as record:
            record.write(run.stdout + (run.stderr if run.returncode else ""))
        print(f"{pin}: rc {run.returncode}", flush=True)
        rc = rc or (run.returncode != 0)
    return int(rc)


if __name__ == "__main__":
    sys.exit(main())
