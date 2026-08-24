#!/usr/bin/env python3
"""Grade seeded and discriminating M3.3 probes against the oracle."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / ".agent" / "decisions"
DEFAULT_MAIN = DECISIONS / "m3u3-main-probes.json"
DEFAULT_ORACLE = DECISIONS / "m3u3-probes.json"
DEFAULT_ARTIFACT = DECISIONS / "m3u3-divergences.json"
PROBE_IDS = tuple(f"Q{number:02d}" for number in range(1, 31))
EXTENSION_IDS = ("Z01", "Z02", "Z03", "Z04")
EXPECTED_DIVERGENCE_IDS = frozenset(EXTENSION_IDS)
COMPARED_FIELDS = ("probe", "outcome", "observation", "note")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: top level must be an object")
    return payload


def indexed_rows(payload: dict[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        raise TypeError(f"{path}: rows must be a list")
    rows: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise TypeError(f"{path}: every row needs a string id")
        identifier = row["id"]
        if identifier in rows:
            raise ValueError(f"{path}: duplicate row {identifier}")
        rows[identifier] = row
    return rows


def difference_paths(path: str, main: Any, oracle: Any) -> Iterator[str]:
    if isinstance(main, dict) and isinstance(oracle, dict):
        main_keys = set(main)
        oracle_keys = set(oracle)
        if main_keys != oracle_keys:
            yield f"{path}.__keys__"
        for key in sorted(main_keys & oracle_keys):
            yield from difference_paths(f"{path}.{key}", main[key], oracle[key])
        return
    if isinstance(main, list) and isinstance(oracle, list):
        if len(main) != len(oracle):
            yield f"{path}.__length__"
        for index, (main_item, oracle_item) in enumerate(zip(main, oracle)):
            yield from difference_paths(f"{path}[{index}]", main_item, oracle_item)
        return
    if type(main) is not type(oracle) or main != oracle:
        yield path


def row_differences(
    main_row: dict[str, Any], oracle_row: dict[str, Any]
) -> tuple[str, ...]:
    paths: list[str] = []
    for field in COMPARED_FIELDS:
        if field not in main_row or field not in oracle_row:
            paths.append(f"{field}.__presence__")
            continue
        paths.extend(difference_paths(field, main_row[field], oracle_row[field]))
    return tuple(paths)


def normalized_seed_row(identifier: str, row: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(row)
    if identifier != "Q30":
        return normalized
    methods = normalized["observation"]["write_transaction_site_methods"]
    normalized["observation"]["write_transaction_site_methods"] = [
        "_persist_submission" if method == "_persist_proposal" else method
        for method in methods
    ]
    return normalized


def main() -> int:
    arguments = parse_args()
    problems: list[str] = []
    try:
        main_payload = load_payload(arguments.main.resolve())
        oracle_payload = load_payload(arguments.oracle.resolve())
        artifact_payload = load_payload(arguments.artifact.resolve())
        main_rows = indexed_rows(main_payload, arguments.main)
        oracle_rows = indexed_rows(oracle_payload, arguments.oracle)
        artifact_rows = indexed_rows(artifact_payload, arguments.artifact)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"INVALID: {error}")
        return 2

    if tuple(main_rows) != PROBE_IDS or tuple(oracle_rows) != PROBE_IDS:
        problems.append("seeded probe ids/order differ from Q01-Q30")

    seeded_divergences: set[str] = set()
    for identifier in PROBE_IDS:
        main_row = normalized_seed_row(identifier, main_rows[identifier])
        oracle_row = oracle_rows[identifier]
        paths = row_differences(main_row, oracle_row)
        if paths:
            seeded_divergences.add(identifier)
            print(f"{identifier} DIFFERS fields={','.join(paths)}")
        elif identifier == "Q30":
            print(
                "Q30 IDENTICAL fields=probe,outcome,observation,note "
                "normalization=_persist_proposal→_persist_submission"
            )
        else:
            print(f"{identifier} IDENTICAL fields={','.join(COMPARED_FIELDS)}")

    extensions = main_payload.get("extensions")
    extension_pairs = (
        extensions.get("rows") if isinstance(extensions, dict) else None
    )
    if not isinstance(extension_pairs, list):
        print("INVALID: MAIN payload has no extensions.rows list")
        return 2
    paired = {row["id"]: row for row in extension_pairs}
    if tuple(paired) != EXTENSION_IDS:
        problems.append(f"extension ids/order differ: {tuple(paired)!r}")

    observed_extensions: set[str] = set()
    for identifier in EXTENSION_IDS:
        pair = paired[identifier]
        main_row = pair["main"]
        oracle_row = pair["oracle"]
        paths = row_differences(main_row, oracle_row)
        if paths:
            observed_extensions.add(identifier)
            print(f"{identifier} DIFFERS fields={','.join(paths)}")
        else:
            print(f"{identifier} IDENTICAL fields={','.join(COMPARED_FIELDS)}")
        artifact_row = artifact_rows.get(identifier, {})
        if artifact_row.get("main_observation") != main_row.get("observation"):
            problems.append(f"{identifier}: artifact MAIN observation is stale")
        if artifact_row.get("oracle_observation") != oracle_row.get("observation"):
            problems.append(f"{identifier}: artifact oracle observation is stale")
        if artifact_row.get("verdict") != "differs":
            problems.append(f"{identifier}: artifact verdict must be differs")

    q30_artifact = artifact_rows.get("Q30", {})
    if q30_artifact.get("verdict") != "identical":
        problems.append("Q30: adapted artifact verdict must be identical")
    if "_persist_proposal ↔ _persist_submission" not in str(
        q30_artifact.get("divergence", "")
    ):
        problems.append("Q30: artifact omits the explicit seam-label substitution")

    print(
        "SEEDED-DIVERGENCES: "
        + (",".join(sorted(seeded_divergences)) or "none")
    )
    print(
        "OBSERVED-EXTENSION-DIVERGENCES: "
        + (",".join(sorted(observed_extensions)) or "none")
    )
    print(
        "EXPECTED-EXTENSION-DIVERGENCES: "
        + ",".join(sorted(EXPECTED_DIVERGENCE_IDS))
    )
    for problem in problems:
        print(f"INVALID: {problem}")
    passed = (
        not seeded_divergences
        and observed_extensions == EXPECTED_DIVERGENCE_IDS
        and not problems
    )
    print("RESULT: PASS" if passed else "RESULT: FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
