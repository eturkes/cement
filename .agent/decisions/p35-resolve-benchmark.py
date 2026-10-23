#!/usr/bin/env python3
"""Cold vs warm `System.resolve` under the p35 serving cache (`.agent/decisions/p35-contract.md` C8).

Usage:
  uv run python .agent/decisions/p35-resolve-benchmark.py N REPEATS [--out FILE] [--reset]

N = 1, 1000 or 50000; REPEATS odd (the median is an observed sample). The fixture is built once
per N in a separate process through today's public lifecycle (`submit_proposal` → `review` ×2 →
`compile` → `verify_drafts` → `promote_function` → `set_switch follow`). Each repetition is a
fresh process that times, on one ledger and one key:
  cold  - the first `resolve` of the process (full verification, then stored)
  warm  - a second `resolve` of the same input (served: re-parse + lookup)
  other - a warm `resolve` of another input (served: re-parse + lookup)
Every point carries its own provenance (commit, source cleanliness over `src/` + this file,
interpreter, SQLite, CPU, platform, repeats, 1-minute load before + after) and the file refuses
to merge a point whose provenance differs from the others (`--reset` starts a new curve).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_OUT = HERE / "p35-resolve-bench.json"
POINTS = {1: "n1", 1_000: "n1000", 50_000: "n50000"}
SOURCE_PATHS = ("src", ".agent/decisions/p35-resolve-benchmark.py")
PARTITION = "bench"
OPERATION = "echo"


def _build(database: str, entries: int) -> None:
    from cement_runtime import Candidate, CompilePolicy, System

    system = System(database)
    system.register_operation(PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0))
    for index in range(entries):
        for reviewer in ("alice", "bob"):
            proposal = system.submit_proposal(
                PARTITION,
                OPERATION,
                {"x": index},
                candidate=Candidate(output={"y": index}, provenance={}),
                source_id=f"{index}-{reviewer}",
            )
            system.review(PARTITION, proposal, reviewer=reviewer, decision="accept")
    compiled = system.compile(PARTITION, OPERATION)
    if len(compiled.created) != entries:
        raise SystemExit(f"compile created {len(compiled.created)}, want {entries}")
    verified = system.verify_drafts(PARTITION, OPERATION, verified_by="bench")
    if not verified.passed or len(verified.entries) != entries:
        raise SystemExit("draft verification failed")
    manifest = system.inspect_function_promotion(PARTITION, OPERATION)
    system.promote_function(
        PARTITION, OPERATION, expected_function_hash=manifest.function_hash, promoted_by="bench"
    )
    system.set_switch(PARTITION, OPERATION, mode="follow", actor="bench")


def _measure(database: str, entries: int) -> dict[str, object]:
    from cement_runtime import System

    system = System(database, create=False)
    timings: dict[str, object] = {}
    for label, value in (("cold", 0), ("warm", 0), ("other", entries - 1)):
        started = time.perf_counter_ns()
        resolution = system.resolve(PARTITION, OPERATION, {"x": value})
        timings[f"{label}_ms"] = (time.perf_counter_ns() - started) / 1_000_000
        if resolution.match is None or not resolution.match.matched:
            raise SystemExit(f"{label} resolve did not match")
        if label == "cold":
            timings["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return timings


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _provenance(repeats: int) -> dict[str, object]:
    cpu = "unknown"
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            cpu = line.split(":", 1)[1].strip()
            break
    return {
        "commit": _git("rev-parse", "HEAD"),
        "source_dirty": bool(_git("status", "--porcelain", "--", *SOURCE_PATHS)),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "host_cpu": cpu,
        "platform": platform.platform(),
        "repeats": repeats,
    }


def _child(mode: str, database: str, entries: int) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, __file__, f"--{mode}", database, str(entries)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    if completed.returncode != 0:
        raise SystemExit(f"{mode} child failed: {completed.stderr[-2000:]}")
    return json.loads(completed.stdout or "{}")


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] in ("--build", "--measure"):
        database, entries = sys.argv[2], int(sys.argv[3])
        if sys.argv[1] == "--build":
            _build(database, entries)
            print("{}")
        else:
            print(json.dumps(_measure(database, entries)))
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("entries", type=int, choices=sorted(POINTS))
    parser.add_argument("repeats", type=int)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reset", action="store_true")
    arguments = parser.parse_args()
    if arguments.repeats < 1 or arguments.repeats % 2 == 0:
        parser.error("REPEATS must be a positive odd number")
    payload: dict[str, object] = {"kind": "p35-resolve-bench", "points": {}}
    if arguments.out.exists() and not arguments.reset:
        payload = json.loads(arguments.out.read_text(encoding="utf-8"))
    provenance = _provenance(arguments.repeats)
    points = payload["points"]
    assert isinstance(points, dict)
    for key, point in points.items():
        if key != POINTS[arguments.entries] and point["provenance"] != provenance:
            raise SystemExit(f"refusing to merge: {key} was measured under other provenance")
    with tempfile.TemporaryDirectory(prefix="cement-p35-bench-") as directory:
        database = str(Path(directory) / "ledger.db")
        load_before = os.getloadavg()[0]
        started = time.perf_counter()
        _child("build", database, arguments.entries)
        build_seconds = time.perf_counter() - started
        samples = [_child("measure", database, arguments.entries) for _ in range(arguments.repeats)]
        load_after = os.getloadavg()[0]
    point: dict[str, object] = {
        "entries": arguments.entries,
        "fixture_build_seconds": round(build_seconds, 3),
        "load_1min_before": load_before,
        "load_1min_after": load_after,
        "provenance": provenance,
        "samples": samples,
    }
    for name in ("cold_ms", "warm_ms", "other_ms", "peak_rss_kib"):
        point[f"median_{name}"] = statistics.median(float(sample[name]) for sample in samples)
    point["warm_over_cold"] = round(
        float(point["median_warm_ms"]) / float(point["median_cold_ms"]), 6
    )
    points[POINTS[arguments.entries]] = point
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in point.items() if key != "samples"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
