#!/usr/bin/env python3
"""p136-store gate 3: the cost of `admit → record_shadow → resolve` for an agreeing and a
disagreeing record, at 1 and 1,000 promoted entries.

Each point = a fresh ledger with N promoted exact entries under `follow` and a warm serving cache,
then per repeat: admit (captures the served version's answer), record (agree: shadow file alone;
disagree: prepared + one ledger proposal), resolve. A disagreement commits to the ledger, so the
resolve after it pays a cold verification (p35). Prints one JSON document with per-point provenance
(commit, interpreter, SQLite, host load before + after, repeats).
Usage: uv run python .agent/decisions/p136-shadow-bench.py [--sizes 1,1000] [--repeats 5]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time


def _root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve().parent
    while not (here / "pyproject.toml").exists():
        here = here.parent
    return here


ROOT = _root()
sys.path.insert(0, str(ROOT / "src"))

from cement_runtime import Candidate, CompilePolicy, System  # noqa: E402
from cement_runtime import shadow  # noqa: E402

P, OP = "bench", "op"


def _ledger(directory: pathlib.Path, entries: int) -> tuple[System, str]:
    system = System(str(directory / "ledger.db"))
    system.register_operation(P, OP, policy=CompilePolicy(2, 1, 0))
    for value in range(entries):
        for reviewer in ("a", "b"):
            proposal = system.submit_proposal(
                P, OP, {"x": value}, candidate=Candidate(output={"y": value}, provenance={})
            )
            system.review(P, proposal, reviewer=reviewer, decision="accept")
    system.compile(P, OP)
    system.verify_drafts(P, OP, verified_by="bench")
    manifest = system.inspect_function_promotion(P, OP)
    system.promote_function(P, OP, expected_function_hash=manifest.function_hash, promoted_by="bench")
    system.set_switch(P, OP, mode="follow", actor="bench")
    system.resolve(P, OP, {"x": 0})
    return system, manifest.function_hash


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)


def _point(entries: int, repeats: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="cement-shadow-bench-") as name:
        directory = pathlib.Path(name)
        system, digest = _ledger(directory, entries)
        store = shadow.ShadowStore(directory / "ledger.db.shadow")
        samples: dict[str, list[float]] = {key: [] for key in (
            "agree_admit", "agree_record", "agree_resolve",
            "disagree_admit", "disagree_record", "disagree_resolve",
        )}
        for repeat in range(repeats):
            for kind, answer in (("agree", {"y": 0}), ("disagree", {"y": -1})):
                start = time.perf_counter()
                admission = shadow.admit(
                    system, store, P, OP, observation_id=f"{kind}-{repeat}",
                    function_hash=digest, input_value={"x": 0}, observed_at_us=repeat,
                )
                samples[f"{kind}_admit"].append(_ms(start))
                start = time.perf_counter()
                record = shadow.record_shadow(
                    system, store, admission.id, llm_output=answer, model="bench",
                    prompt_revision="bench", latency_ms=0,
                )
                samples[f"{kind}_record"].append(_ms(start))
                assert record["state"] == ("agreed" if kind == "agree" else "disagreed"), record
                start = time.perf_counter()
                assert system.resolve(P, OP, {"x": 0}).match.matched
                samples[f"{kind}_resolve"].append(_ms(start))
        return {
            "entries": entries,
            "repeats": repeats,
            "median_ms": {key: statistics.median(values) for key, values in samples.items()},
            "samples_ms": samples,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--sizes", default="1,1000")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    load_before = os.getloadavg()
    points = [_point(int(size), args.repeats) for size in args.sizes.split(",")]
    print(json.dumps({
        "provenance": {
            "commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
            "dirty": bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no", "src"], capture_output=True, text=True).stdout.strip()),
            "python": sys.version,
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "cpus": os.cpu_count(),
            "load_before": load_before,
            "load_after": os.getloadavg(),
        },
        "points": points,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
