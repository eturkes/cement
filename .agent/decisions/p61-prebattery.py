#!/usr/bin/env python3
"""p61-prebattery — M3.6a1's pre-battery sweep: which catalogue rows the PRE-EXISTING suite already kills.

Runs `.agent/decisions/m3u6a1-mutants.py` at the unit tip `dc4ab5e` (a detached temporary worktree)
with `--verdict` = the four modules owning the mutated files, so the migration battery that each row
targets is absent. The instrument's vocabulary then inverts: `survived` = no pre-existing test kills
the row, so the battery is its sole killer (the desired blindness); `misdirected` = the old suite
already kills it. The instrument exits 1 here by construction (every row expects `killed`); the run
counts only with `CONTROL: GREEN`, all 92 rows parsed, `KILLED: 0` and `PATCH-NOOP: 0`.

Outputs (each pre-battery verdict in its own field `pre_battery`, never `note`):
  .agent/decisions/p61-prebattery.txt   instrument stdout, `VERDICT-MODULES:` through `RESULT:`
  .agent/decisions/p61-prebattery.json  one row per catalogue id + counts

Usage: uv run python .agent/decisions/p61-prebattery.py [--from-log <transcript> | --check]
  (none)       sweep at dc4ab5e (hours serially), then write both outputs
  --from-log   take the transcript from an earlier run's log (runner noise before
               `VERDICT-MODULES:` is dropped), then write both outputs
  --check      rebuild the JSON from the committed transcript; rc 1 if it differs from the file
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
REV = "dc4ab5e"
CATALOGUE = ".agent/decisions/m3u6a1-mutants.json"
MODULES = (
    "tests.test_system",
    "tests.test_resolve_battery",
    "tests.test_proposal_binding_battery",
    "tests.test_hospital_ocr_example",
)
TRANSCRIPT = ROOT / ".agent/decisions/p61-prebattery.txt"
OUTPUT = ROOT / ".agent/decisions/p61-prebattery.json"
ROW = re.compile(r"^(M\d+)\s+(survived|misdirected|killed)\s+(D\d+[a-z]?)\s+(reversion|sensitivity)\s+(\S+)$")
VERDICT = {"survived": "battery_sole_killer", "misdirected": "old_suite_kills"}


def _sweep() -> str:
    with tempfile.TemporaryDirectory() as parent:
        checkout = pathlib.Path(parent) / "m3u6a1"
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "-q", "--detach", str(checkout), REV], check=True)
        try:
            argv = ["uv", "run", "python", "-u", CATALOGUE.replace(".json", ".py")]
            for module in MODULES:
                argv += ["--verdict", module]
            result = subprocess.run(argv, cwd=checkout, capture_output=True, text=True)
            return result.stdout
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(checkout)], check=True)


def _transcript(text: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("VERDICT-MODULES: "))
    end = next(i for i, line in enumerate(lines) if line.startswith("RESULT: "))
    return "\n".join(lines[start : end + 1]) + "\n"


def _derive(transcript: str) -> dict:
    lines = transcript.splitlines()
    header = {line.split(": ", 1)[0]: line.split(": ", 1)[1] for line in lines if re.match(r"^[A-Z-]+: ", line)}
    if header.get("VERDICT-MODULES", "").split() != list(MODULES):
        raise SystemExit(f"ABORT   verdict modules {header.get('VERDICT-MODULES')!r} != {' '.join(MODULES)}")
    for key, want in (("CONTROL", "GREEN"), ("KILLED", "0"), ("PATCH-NOOP", "0 []")):
        if header.get(key) != want:
            raise SystemExit(f"ABORT   {key}: {header.get(key)!r}, want {want!r}")
    catalogue = json.loads(
        subprocess.run(["git", "-C", str(ROOT), "show", f"{REV}:{CATALOGUE}"], capture_output=True, text=True, check=True).stdout
    )
    expected = {row["id"]: (row["obligation"], row["kind"]) for row in catalogue["rows"]}
    rows = []
    for line in lines:
        match = ROW.match(line)
        if match:
            mutant, verdict, obligation, kind, killers = match.groups()
            if expected.get(mutant) != (obligation, kind):
                raise SystemExit(f"ABORT   {mutant} {obligation} {kind} disagrees with {REV}:{CATALOGUE}")
            rows.append({
                "id": mutant,
                "obligation": obligation,
                "kind": kind,
                "pre_battery": VERDICT[verdict],
                "old_suite_killers": [] if killers == "-" else killers.split(","),
            })
    if [row["id"] for row in rows] != list(expected) or int(header["MUTANTS"]) != len(rows):
        raise SystemExit(f"ABORT   parsed {len(rows)} rows; catalogue has {len(expected)}, MUTANTS: {header.get('MUTANTS')}")
    counts = {"rows": len(rows)}
    for value in VERDICT.values():
        counts[value] = sum(row["pre_battery"] == value for row in rows)
    for value in VERDICT.values():
        for kind in ("reversion", "sensitivity"):
            counts[f"{value}.{kind}"] = sum(row["pre_battery"] == value and row["kind"] == kind for row in rows)
    return {
        "unit": "M3.6a1",
        "rev": REV,
        "instrument": CATALOGUE.replace(".json", ".py"),
        "verdict_modules": list(MODULES),
        "pre_battery": {
            "battery_sole_killer": "instrument `survived`: no pre-existing test kills the row",
            "old_suite_kills": "instrument `misdirected`: `old_suite_killers` kill it without the battery",
        },
        "counts": counts,
        "rows": rows,
    }


def _render(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    if argv[1:] == ["--check"]:
        rebuilt = _render(_derive(TRANSCRIPT.read_text(encoding="utf-8")))
        if rebuilt != OUTPUT.read_text(encoding="utf-8"):
            print(f"DRIFT   {OUTPUT.relative_to(ROOT)} != rebuild from {TRANSCRIPT.relative_to(ROOT)}")
            return 1
        print(f"CHECK: PASS {json.loads(rebuilt)['counts']}")
        return 0
    if argv[1:2] == ["--from-log"] and len(argv) == 3:
        transcript = _transcript(pathlib.Path(argv[2]).read_text(encoding="utf-8"))
    elif len(argv) == 1:
        transcript = _transcript(_sweep())
    else:
        print(__doc__, file=sys.stderr)
        return 2
    document = _derive(transcript)
    TRANSCRIPT.write_text(transcript, encoding="utf-8")
    OUTPUT.write_text(_render(document), encoding="utf-8")
    print(f"WROTE: {document['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
