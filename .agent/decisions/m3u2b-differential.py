#!/usr/bin/env python
"""Compare MAIN and independent-oracle M3.2b observations field by field.

Usage:

    uv run python .agent/decisions/m3u2b-differential.py MAIN.json ORACLE.json

Message wording is TEXT and does not fail the comparison. Every other value
change is BEHAVIORAL. A missing probe, outcome, observation, or observation key
fails the comparison independently.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


_MISSING = object()


@dataclass(frozen=True, slots=True)
class Difference:
    classification: str
    key: str
    main: object
    oracle: object


def _load(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    probes = payload.get("probes") if isinstance(payload, dict) else None
    if not isinstance(probes, dict):
        raise ValueError(f"{path}: 'probes' must be an object")
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in probes.items()):
        raise ValueError(f"{path}: every probe must have a string id and object value")
    return probes


def _render(value: object) -> str:
    if value is _MISSING:
        return "<missing>"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _difference(key: str, main: object, oracle: object) -> Difference:
    classification = (
        "TEXT"
        if key == "message" and isinstance(main, str) and isinstance(oracle, str)
        else "BEHAVIORAL"
    )
    return Difference(classification, key, main, oracle)


def _compare_probe(
    main: dict[str, Any],
    oracle: dict[str, Any],
) -> tuple[list[Difference], int, int]:
    differences: list[Difference] = []
    missing_main = 0
    missing_oracle = 0

    main_outcome = main.get("outcome", _MISSING)
    oracle_outcome = oracle.get("outcome", _MISSING)
    if main_outcome is _MISSING:
        missing_main += 1
        differences.append(Difference("MISSING", "outcome", _MISSING, oracle_outcome))
    elif oracle_outcome is _MISSING:
        missing_oracle += 1
        differences.append(Difference("MISSING", "outcome", main_outcome, _MISSING))
    elif main_outcome != oracle_outcome:
        differences.append(_difference("outcome", main_outcome, oracle_outcome))

    main_observation = main.get("observation", _MISSING)
    oracle_observation = oracle.get("observation", _MISSING)
    if main_observation is _MISSING:
        missing_main += 1
        differences.append(
            Difference("MISSING", "observation", _MISSING, oracle_observation)
        )
        return differences, missing_main, missing_oracle
    if oracle_observation is _MISSING:
        missing_oracle += 1
        differences.append(
            Difference("MISSING", "observation", main_observation, _MISSING)
        )
        return differences, missing_main, missing_oracle
    if not isinstance(main_observation, dict) or not isinstance(oracle_observation, dict):
        if main_observation != oracle_observation:
            differences.append(
                _difference("observation", main_observation, oracle_observation)
            )
        return differences, missing_main, missing_oracle

    for key in sorted(set(main_observation) | set(oracle_observation)):
        main_value = main_observation.get(key, _MISSING)
        oracle_value = oracle_observation.get(key, _MISSING)
        if main_value is _MISSING:
            missing_main += 1
            differences.append(Difference("MISSING", key, _MISSING, oracle_value))
        elif oracle_value is _MISSING:
            missing_oracle += 1
            differences.append(Difference("MISSING", key, main_value, _MISSING))
        elif main_value != oracle_value:
            differences.append(_difference(key, main_value, oracle_value))
    return differences, missing_main, missing_oracle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("main", type=Path, help="MAIN shipped-implementation observations")
    parser.add_argument("oracle", type=Path, help="independent-oracle observations")
    arguments = parser.parse_args(argv)

    try:
        main_probes = _load(arguments.main)
        oracle_probes = _load(arguments.oracle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    probe_ids = sorted(set(main_probes) | set(oracle_probes))
    probes_compared = len(set(main_probes) & set(oracle_probes))
    behavioral = 0
    textual = 0
    missing_main = 0
    missing_oracle = 0

    for identifier in probe_ids:
        main_probe = main_probes.get(identifier)
        oracle_probe = oracle_probes.get(identifier)
        if main_probe is None:
            missing_main += 1
            print(
                f"{identifier} MISSING: key=<probe> "
                "MAIN=<missing> ORACLE=<present>"
            )
            continue
        if oracle_probe is None:
            missing_oracle += 1
            print(
                f"{identifier} MISSING: key=<probe> "
                "MAIN=<present> ORACLE=<missing>"
            )
            continue

        differences, absent_main, absent_oracle = _compare_probe(
            main_probe,
            oracle_probe,
        )
        missing_main += absent_main
        missing_oracle += absent_oracle
        behavioral += sum(
            difference.classification == "BEHAVIORAL" for difference in differences
        )
        textual += sum(
            difference.classification == "TEXT" for difference in differences
        )
        if absent_main or absent_oracle:
            verdict = "MISSING"
        elif any(
            difference.classification == "BEHAVIORAL" for difference in differences
        ):
            verdict = "BEHAVIORAL"
        elif differences:
            verdict = "TEXT"
        else:
            verdict = "MATCH"

        details = "; ".join(
            f"{difference.classification} key={difference.key} "
            f"MAIN={_render(difference.main)} ORACLE={_render(difference.oracle)}"
            for difference in differences
        )
        print(f"{identifier} {verdict}" + (f": {details}" if details else ""))

    print(
        "COUNTS "
        f"probes_compared={probes_compared} "
        f"behavioral_divergences={behavioral} "
        f"text_differences={textual} "
        f"missing_keys_main={missing_main} "
        f"missing_keys_oracle={missing_oracle}"
    )
    return int(bool(behavioral or missing_main or missing_oracle))


if __name__ == "__main__":
    raise SystemExit(main())
