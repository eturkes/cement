#!/usr/bin/env python3
"""End-to-end cost of `System.resolve`, the shipped resolver entry point.

Usage:
  uv run python .agent/decisions/m3u2b-resolve-benchmark.py N REPEATS \
      [--out .agent/decisions/m3u2b-resolve-bench.json]

N is 1, 1000 or 50000. REPEATS must be odd so the median is an observed sample.

Why this file exists beside `m3u2b-benchmark.py`: that harness times
`verify_function` and standalone `evaluate` and never calls `resolve`, so it is a
COMPONENT baseline. It cannot see argument validation, the second dispatch, or
result construction. This harness calls the shipped public method and nothing
else, so its numbers are the ones a caller pays.

Method, identical to the component harness where it matters: the fixture is built
in a SEPARATE process, because a Linux child inherits the builder's `ru_maxrss`
high-water across exec and would report the builder's peak as the measurement's.
Each repetition is a fresh process and a fresh `System`, so cold means
process-cold, never disk-cold; the OS page cache is not dropped.

Each worker times three resolves in one process:
  hit    - process-cold, the first ledger touch of the process
  miss   - warm, an input absent from the promoted set
  failed - warm, a deliberately wrong `expected_function_hash`
`peak_rss_kib` is read immediately after the cold resolve, before the other two.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE / "m3u2b-benchmark.py"
DEFAULT_OUT = HERE / "m3u2b-resolve-bench.json"
POINTS = {1: "n1", 1_000: "n1000", 50_000: "n50000"}

_spec = importlib.util.spec_from_file_location("m3u2b_component", COMPONENT)
component = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(component)

PARTITION = component.PARTITION
OPERATION = component.OPERATION

sys.path.insert(0, str(HERE.parents[1] / "src"))

from cement_runtime import System  # noqa: E402


def _worker(database: str, entries: int) -> dict[str, int]:
    system = System(database)
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    started_ns = time.perf_counter_ns()
    hit = system.resolve(PARTITION, OPERATION, 0)
    hit_ns = time.perf_counter_ns() - started_ns
    peak_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if (
        not hit.verification.passed
        or hit.verification.entries != entries
        or hit.match is None
        or not hit.match.matched
        or hit.match.output != 0
        or hit.match.artifact_hash is None
    ):
        raise RuntimeError(f"cold resolve did not produce a verified hit: {hit!r}")

    started_ns = time.perf_counter_ns()
    miss = system.resolve(PARTITION, OPERATION, entries)
    miss_ns = time.perf_counter_ns() - started_ns
    if (
        not miss.verification.passed
        or miss.match is None
        or miss.match.matched
        or miss.match.output is not None
        or miss.match.artifact_hash is not None
    ):
        raise RuntimeError(f"warm resolve did not produce a verified miss: {miss!r}")

    started_ns = time.perf_counter_ns()
    failed = system.resolve(
        PARTITION, OPERATION, 0, expected_function_hash="0" * 64
    )
    failed_ns = time.perf_counter_ns() - started_ns
    if failed.verification.passed or failed.match is not None:
        raise RuntimeError(f"warm resolve did not produce a failed verdict: {failed!r}")

    if hit.verification.function_hash != miss.verification.function_hash:
        raise RuntimeError("two resolves reconstructed different function hashes")

    return {
        "hit_ns": hit_ns,
        "miss_ns": miss_ns,
        "failed_ns": failed_ns,
        "rss_before_kib": rss_before,
        "peak_rss_kib": peak_rss_kib,
        "document_bytes": len(hit.verification.document.text.encode("utf-8")),
    }


def _run_worker(database: Path, entries: int) -> dict[str, int]:
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", str(database), str(entries)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"resolve worker exited {completed.returncode}: {detail}")
    return json.loads(completed.stdout)


def _odd(text: str) -> int:
    value = int(text)
    if value < 1 or value % 2 == 0:
        raise argparse.ArgumentTypeError("REPEATS must be a positive odd integer")
    return value


def main(argv: list[str]) -> int:
    if argv[:1] == ["--worker"]:
        if not sys.platform.startswith("linux"):
            raise SystemExit("RUSAGE_SELF.ru_maxrss is specified as KiB only on Linux")
        sys.stdout.write(json.dumps(_worker(argv[1], int(argv[2]))) + "\n")
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("entries", type=int, choices=tuple(POINTS))
    parser.add_argument("repeats", type=_odd)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    point = POINTS[args.entries]

    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "resolve-bench.db"
        build_seconds = component._run_fixture_builder(database, args.entries)
        print(f"fixture built in {build_seconds:.6f}s", file=sys.stderr)
        runs = []
        for repeat in range(args.repeats):
            runs.append(_run_worker(database, args.entries))
            print(f"repetitions: {repeat + 1}/{args.repeats}", file=sys.stderr)

    if len({run["document_bytes"] for run in runs}) != 1:
        raise RuntimeError("repetitions reconstructed different document sizes")
    medians = {
        key: int(statistics.median([run[key] for run in runs]))
        for key in ("hit_ns", "miss_ns", "failed_ns", "rss_before_kib", "peak_rss_kib")
    }

    payload = {"kind": "resolve-bench", "points": {}}
    if args.out.exists():
        existing = json.loads(args.out.read_text(encoding="utf-8"))
        if existing.get("kind") == "resolve-bench":
            payload = existing
    payload["points"][point] = {
        "entries": args.entries,
        "repeats": args.repeats,
        "fixture_build_seconds": build_seconds,
        "document_bytes": runs[0]["document_bytes"],
        "resolve_cold_hit_ms": medians["hit_ns"] / 1_000_000,
        "resolve_warm_miss_ms": medians["miss_ns"] / 1_000_000,
        "resolve_warm_failed_ms": medians["failed_ns"] / 1_000_000,
        "rss_before_kib": medians["rss_before_kib"],
        "peak_rss_kib": medians["peak_rss_kib"],
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["points"][point], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
