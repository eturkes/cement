#!/usr/bin/env python3
"""Measure the uncached M3.2b ``verify_function`` + ``evaluate`` baseline.

Usage:
  uv run python .agent/decisions/m3u2b-benchmark.py N REPEATS \
    [--output .agent/decisions/m3u2b-bench.json] [--commit SHA]

The fixture is built only through public ``System`` methods. Each repetition runs
in a fresh child process: its first verification is cold at process/System scope,
and its second verification is warm on the same ``System``. The OS page cache is
not dropped. Progress goes to stderr; stdout is one validator-shaped JSON object.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any

from cement_runtime import (
    Candidate,
    CompilePolicy,
    ReviewRequired,
    System,
    evaluate,
)
from cement_runtime.json_value import canonicalize

PARTITION = "m3u2b-benchmark"
OPERATION = "exact"
POINTS = {1: "n1", 1_000: "n1000", 50_000: "n50000"}
POINT_CELLS = (
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
ENV_CELLS = ("python_version", "sqlite_version", "host_cpu", "repeats", "commit")


class _ExactSource:
    def propose(self, request: Any) -> Candidate:
        return Candidate(output=request.input, provenance={})


def _json_items(value: Any) -> int:
    if type(value) is list:
        return len(value) + sum(_json_items(item) for item in value)
    if type(value) is dict:
        return len(value) + sum(_json_items(item) for item in value.values())
    return 0


def _host_cpu() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                return line.partition(":")[2].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _skeleton() -> dict[str, Any]:
    return {
        "kind": "bench",
        "unit": "M3.2b",
        **{cell: "unknown" for cell in ENV_CELLS},
        "points": {
            point: {cell: "unknown" for cell in POINT_CELLS}
            for point in POINTS.values()
        },
    }


def _load_output(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return _skeleton()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if type(payload) is not dict or payload.get("kind") != "bench":
        raise ValueError("output must contain a bench JSON object")
    expected = _skeleton()
    if set(payload) != set(expected):
        raise ValueError("output top-level keys do not match the benchmark schema")
    if type(payload.get("points")) is not dict or set(payload["points"]) != set(POINTS.values()):
        raise ValueError("output point keys do not match the benchmark schema")
    for point in POINTS.values():
        if type(payload["points"][point]) is not dict or set(payload["points"][point]) != set(POINT_CELLS):
            raise ValueError(f"output cells for {point} do not match the benchmark schema")
    return payload


def _set_environment(
    payload: dict[str, Any],
    *,
    repeats: int,
    commit: str,
) -> None:
    measured: dict[str, str | int] = {
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "host_cpu": _host_cpu(),
        "repeats": repeats,
        "commit": commit,
    }
    for key, value in measured.items():
        existing = payload[key]
        if existing != "unknown" and existing != value:
            raise ValueError(
                f"output {key}={existing!r} conflicts with measured {value!r}"
            )
        payload[key] = value


def _build_fixture(database: Path, entries: int) -> float:
    started_ns = time.perf_counter_ns()
    system = System(str(database), candidate_source=_ExactSource())
    system.register_operation(
        PARTITION,
        OPERATION,
        policy=CompilePolicy(2, 1, 0),
        registered_by="m3u2b-benchmark",
    )
    stride = max(1, min(1_000, entries // 20 or 1))
    for index in range(entries):
        for confirmation in range(2):
            outcome = system.handle(
                PARTITION,
                OPERATION,
                index,
                request_id=f"bench-{index}-{confirmation}",
            )
            if not isinstance(outcome, ReviewRequired):
                raise RuntimeError(
                    f"entry {index} confirmation {confirmation} expected "
                    f"ReviewRequired, got {type(outcome).__name__}"
                )
            system.review(
                PARTITION,
                outcome.proposal_id,
                reviewer="m3u2b-reviewer",
                decision="accept",
            )
        completed = index + 1
        if completed == entries or completed % stride == 0:
            print(f"fixture confirmations: {completed}/{entries}", file=sys.stderr)

    compiled = system.compile(
        PARTITION,
        OPERATION,
        compiled_by="m3u2b-benchmark",
    )
    if len(compiled.created) != entries or compiled.existing or compiled.blocked:
        raise RuntimeError(
            "compile result mismatch: "
            f"created={len(compiled.created)} existing={len(compiled.existing)} "
            f"blocked={len(compiled.blocked)}"
        )
    verified = system.verify_drafts(
        PARTITION,
        OPERATION,
        verified_by="m3u2b-verifier",
    )
    if not verified.passed or len(verified.entries) != entries or verified.skipped:
        raise RuntimeError(
            "draft verification mismatch: "
            f"passed={verified.passed} entries={len(verified.entries)} "
            f"skipped={len(verified.skipped)}"
        )
    manifest = system.inspect_function_promotion(PARTITION, OPERATION)
    if len(manifest.entries) != entries or manifest.skipped:
        raise RuntimeError(
            "promotion manifest mismatch: "
            f"entries={len(manifest.entries)} skipped={len(manifest.skipped)}"
        )
    promotion = system.promote_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
        promoted_by="m3u2b-release-manager",
    )
    if len(promotion.member_artifact_ids) != entries:
        raise RuntimeError(
            "function promotion mismatch: "
            f"members={len(promotion.member_artifact_ids)} expected={entries}"
        )
    elapsed_ns = time.perf_counter_ns() - started_ns
    return elapsed_ns / 1_000_000_000


def _run_fixture_builder(database: Path, entries: int) -> float:
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--build-fixture",
            str(database),
            str(entries),
        ],
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"fixture builder exited {completed.returncode}")
    payload = json.loads(completed.stdout)
    if type(payload) is not dict or type(payload.get("fixture_build_seconds")) is not float:
        raise RuntimeError("fixture builder did not return its measured wall time")
    return payload["fixture_build_seconds"]


def _worker(database: str, entries: int) -> dict[str, int]:
    system = System(database)
    hit_input = canonicalize(0)
    miss_input = canonicalize(entries)
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    started_ns = time.perf_counter_ns()
    cold = system.verify_function(PARTITION, OPERATION)
    cold_ns = time.perf_counter_ns() - started_ns
    rss_after_cold = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if not cold.passed or cold.document is None or cold.entries != entries:
        raise RuntimeError(
            "cold verification mismatch: "
            f"passed={cold.passed} document={cold.document is not None} "
            f"entries={cold.entries} expected={entries}"
        )

    started_ns = time.perf_counter_ns()
    warm = system.verify_function(PARTITION, OPERATION)
    warm_ns = time.perf_counter_ns() - started_ns
    if not warm.passed or warm.document is None:
        raise RuntimeError("warm verification did not return a passing document")
    if warm.function_hash != cold.function_hash or warm.document.text != cold.document.text:
        raise RuntimeError("warm verification reconstructed different function bytes")

    started_ns = time.perf_counter_ns()
    hit = evaluate(warm.document, input_json=hit_input)
    hit_ns = time.perf_counter_ns() - started_ns
    if not hit.matched or hit.output != 0 or hit.artifact_hash is None:
        raise RuntimeError(f"evaluate hit mismatch: {hit!r}")

    started_ns = time.perf_counter_ns()
    miss = evaluate(warm.document, input_json=miss_input)
    miss_ns = time.perf_counter_ns() - started_ns
    if miss.matched or miss.output is not None or miss.artifact_hash is not None:
        raise RuntimeError(f"evaluate miss mismatch: {miss!r}")

    return {
        "cold_ns": cold_ns,
        "warm_ns": warm_ns,
        "hit_ns": hit_ns,
        "miss_ns": miss_ns,
        "rss_before_kib": rss_before,
        "peak_rss_kib": rss_after_cold,
        "document_bytes": len(warm.document.text.encode("utf-8")),
        "document_items": _json_items(warm.document.value),
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
        raise RuntimeError(
            f"benchmark worker exited {completed.returncode}: {detail}"
        )
    payload = json.loads(completed.stdout)
    if type(payload) is not dict:
        raise RuntimeError("benchmark worker did not return a JSON object")
    return payload


def _median(values: list[int]) -> int:
    result = statistics.median(values)
    if type(result) is not int:
        raise AssertionError("odd repeat count must produce an observed median")
    return result


def _measure(database: Path, entries: int, repeats: int) -> tuple[dict[str, int], int]:
    runs: list[dict[str, int]] = []
    for repeat in range(repeats):
        runs.append(_run_worker(database, entries))
        print(f"measurement repetitions: {repeat + 1}/{repeats}", file=sys.stderr)
    document_bytes = {run["document_bytes"] for run in runs}
    document_items = {run["document_items"] for run in runs}
    if len(document_bytes) != 1 or len(document_items) != 1:
        raise RuntimeError("repetitions reconstructed different document sizes")
    medians = {
        key: _median([run[key] for run in runs])
        for key in (
            "cold_ns",
            "warm_ns",
            "hit_ns",
            "miss_ns",
            "rss_before_kib",
            "peak_rss_kib",
        )
    }
    medians["document_bytes"] = document_bytes.pop()
    medians["document_items"] = document_items.pop()
    return medians, medians["rss_before_kib"]


def _milliseconds(nanoseconds: int) -> float:
    return round(nanoseconds / 1_000_000, 6)


def _write_output(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _odd_repeats(value: str) -> int:
    parsed = _positive_integer(value)
    if parsed % 2 == 0:
        raise argparse.ArgumentTypeError("REPEATS must be odd so the median is observed")
    return parsed


def _benchmark_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entries", type=_positive_integer, choices=tuple(POINTS))
    parser.add_argument("repeats", type=_odd_repeats)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--commit", help="source checkout SHA measured by every point")
    args = parser.parse_args(argv)

    payload = _load_output(args.output)
    commit = args.commit or _git_head()
    _set_environment(payload, repeats=args.repeats, commit=commit)
    point = POINTS[args.entries]

    with tempfile.TemporaryDirectory(prefix=f"cement-{point}-") as temporary:
        database = Path(temporary) / "cement.db"
        fixture_seconds = _run_fixture_builder(database, args.entries)
        measured, rss_before_kib = _measure(database, args.entries, args.repeats)

    payload["points"][point] = {
        "entries": args.entries,
        "document_bytes": measured["document_bytes"],
        "document_items": measured["document_items"],
        "fixture_build_seconds": round(fixture_seconds, 9),
        "verify_cold_ms": _milliseconds(measured["cold_ns"]),
        "verify_warm_ms": _milliseconds(measured["warm_ns"]),
        "evaluate_hit_ms": _milliseconds(measured["hit_ns"]),
        "evaluate_miss_ms": _milliseconds(measured["miss_ns"]),
        "peak_rss_kib": measured["peak_rss_kib"],
        "note": (
            "ok; cold=first verify_function in a fresh process on a fresh System; "
            "warm=second verify_function on that System; OS page cache not controlled "
            "and fixture construction/prior repeats may warm it; peak RSS=median absolute "
            "RUSAGE_SELF.ru_maxrss after cold verification on Linux (KiB), with fixture "
            f"construction isolated in a separate process; median pre-verify RSS={rss_before_kib} KiB; "
            f"all timings are observed medians of {args.repeats} fresh-process runs"
        ),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        _write_output(args.output, text)
    sys.stdout.write(text)
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--build-fixture"]:
        if len(argv) != 3:
            raise SystemExit("fixture usage: --build-fixture DATABASE ENTRIES")
        seconds = _build_fixture(Path(argv[1]), int(argv[2]))
        sys.stdout.write(json.dumps({"fixture_build_seconds": seconds}) + "\n")
        return 0
    if argv[:1] == ["--worker"]:
        if len(argv) != 3:
            raise SystemExit("worker usage: --worker DATABASE ENTRIES")
        if not sys.platform.startswith("linux"):
            raise SystemExit("RUSAGE_SELF.ru_maxrss is specified as KiB only on Linux")
        sys.stdout.write(json.dumps(_worker(argv[1], int(argv[2]))) + "\n")
        return 0
    return _benchmark_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
