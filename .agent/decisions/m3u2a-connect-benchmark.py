#!/usr/bin/env python
"""Measure the read capability's per-open cost against the landed production path.

Interleaved alternating-pair method: each round opens both paths the same number of
times, swapping which path goes first, so phase drift hits both arms equally. The
sequential form is rejected - it attributes drift to whichever arm ran second.

    uv run python .agent/decisions/m3u2a-connect-benchmark.py [--opens N] [--rounds N]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve()
while not (ROOT / "pyproject.toml").exists():
    if ROOT == ROOT.parent:
        raise SystemExit("pyproject.toml not found above this script")
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from cement_runtime.store import Store  # noqa: E402


def time_opens(store: Store, *, read_only: bool, opens: int) -> float:
    started = time.perf_counter()
    for _ in range(opens):
        connection = store._connect(read_only=read_only)
        connection.close()
    return (time.perf_counter() - started) / opens * 1_000_000.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opens", type=int, default=200)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=20)
    arguments = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "ledger.db")
        for _ in range(arguments.warmups):
            store._connect(read_only=False).close()
            store._connect(read_only=True).close()

        plain: list[float] = []
        enforced: list[float] = []
        for round_index in range(arguments.rounds):
            if round_index % 2 == 0:
                plain.append(time_opens(store, read_only=False, opens=arguments.opens))
                enforced.append(time_opens(store, read_only=True, opens=arguments.opens))
            else:
                enforced.append(time_opens(store, read_only=True, opens=arguments.opens))
                plain.append(time_opens(store, read_only=False, opens=arguments.opens))

    plain_us = statistics.median(plain)
    enforced_us = statistics.median(enforced)
    result = {
        "method": "interleaved alternating pairs",
        "opens_per_round": arguments.opens,
        "rounds": arguments.rounds,
        "warmups": arguments.warmups,
        "plain_us_per_open": round(plain_us, 3),
        "enforced_us_per_open": round(enforced_us, 3),
        "delta_us": round(enforced_us - plain_us, 3),
        "ratio": round(enforced_us / plain_us, 3),
        "plain_range_us": [round(min(plain), 3), round(max(plain), 3)],
        "enforced_range_us": [round(min(enforced), 3), round(max(enforced), 3)],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
