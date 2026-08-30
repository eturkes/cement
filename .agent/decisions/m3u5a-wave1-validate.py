#!/usr/bin/env python
"""Structural validator for M3.5a wave-1 artifacts. Sole source of truth for their seeds.

Kinds:
  map    -> .agent/decisions/m3u5a-map.json          (surface map, anchored)
  spike  -> .agent/decisions/m3u5a-spike-<alt>.json  (channel alternative, delta probes)

Usage:
  uv run python .agent/decisions/m3u5a-wave1-validate.py --emit-stub map > <path>
  uv run python .agent/decisions/m3u5a-wave1-validate.py <path> [--root DIR]

rc 0 = PASS. rc 1 = any unfilled cell or any failed check.

Design rules this file encodes, each paid for by a recorded defect:
  - Row SUBJECTS are seeded (`locus`), not just the row count: a generative
    deliverable is resumable only when its subjects are named.
  - Seeded ids are a FLOOR. Extension ids (`X..` map, `Y..` spike) are accepted
    so seeding cannot cap discovery.
  - MAIN-owned fields are EXEMPT from the unknown census and PRINTED, so a
    teammate's completeness is never read as MAIN's ruling.
  - A spike table answerable against baseline alone measures the status quo. Every
    spike row carries BOTH observations and the file must show real deltas.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

UNKNOWN = "unknown"
EXEMPT = ("main_verdict",)
PROSE_FLOOR = 24
DELTA_FLOOR = 15
ADDITIONS_FLOOR = 20

MAP_FIELDS = ("anchor", "symbol", "finding", "bearing")
SPIKE_FIELDS = ("command", "baseline", "alt", "delta", "verdict")
SPIKE_HEADER = ("alternative", "head_sha", "diff_stat", "driver")
VERDICTS = ("ok", "defect", "unreachable")

MAP_SEED: tuple[tuple[str, str], ...] = (
    ("M01", "cli.py `_run` function-eval branch: payload keys, status 0/6, ledger-free dispatch"),
    ("M02", "cli.py `_run` function-verify branch: projection that keeps FunctionDocument off stdout"),
    ("M03", "cli.py `_run` function-inspect branch: manifest projection and dropped `text`/`document`"),
    ("M04", "cli.py `main`: ordered except clauses, exception class -> exit code, stream per class"),
    ("M05", "cli.py `_Outcome`: exactly-one-channel invariant and exact-int status assertion"),
    ("M06", "cli.py `_emit`: asdict expansion, sort_keys, indent, ensure_ascii, trailing newline"),
    ("M07", "cli.py `_input`: stdin bound, buffer-vs-text branch, its three exact messages"),
    ("M08", "cli.py `challenge` leaf: the shipped precedent for two JSON-bearing flags on one leaf"),
    ("M09", "system.py `System.resolve`: exact signature, argument validation order, raised classes"),
    ("M10", "system.py `System.submit_proposal`: exact signature, return type, absent revision arg"),
    ("M11", "system.py `System.propose`: signature and why the core CLI must reach no source"),
    ("M12", "models.py `Candidate`: field set, provenance mapping contract, canonicalization site"),
    ("M13", "models.py `FunctionResolution`: field set and the `match is None` domain qualifier"),
    ("M14", "function.py `FunctionVerification`: field set incl. the document that must not ship"),
    ("M15", "function.py `FunctionMatch` and `FunctionCheck`: field sets reaching a resolve payload"),
    ("M16", "argparse abbreviation on `_parser()`: whether a prefix of a flag or leaf still parses"),
    ("M17", "tests/test_cli.py: how the leaf census is derived from `_parser()` and what it asserts"),
    ("M18", "System construction against an absent ledger path: does it create the file, and when"),
    ("M19", "tests/test_cli.py shared fixture helpers: names, line anchors, caller counts"),
    ("M20", "exit-6 census across shipped leaves: which object, which channel, which payload shape"),
    ("M21", "README.md + docs/: every sentence naming CLI submission or resolution grammar"),
    ("M22", "cli.py `proposal review` leaf: `--output` JSON handling and its stdin interaction"),
    ("M23", "cli.py `_source` + `CommandCandidateSource` import: the reach M3.5a must not extend"),
    ("M24", "json_value `DEFAULT_MAX_BYTES` / `parse_json`: bytes-vs-chars bound and its messages"),
    ("M25", "System.events + proposal.created event payload produced by a direct submission"),
)

SPIKE_SEED: tuple[tuple[str, str], ...] = (
    ("Z01", "valid submission, happy path: exit, stdout payload keys, rows and events written"),
    ("Z02", "the identical submission repeated: proposal count, ids, whether anything dedupes"),
    ("Z03", "required channel argument omitted entirely: exit, channel, exact message"),
    ("Z04", "syntactically malformed JSON on the channel: exit, channel, exact message"),
    ("Z05", "an unknown/surplus key or flag supplied beside a valid submission: accept or reject"),
    ("Z06", "provenance omitted: defaulted to empty mapping, or rejected"),
    ("Z07", "provenance present but not a JSON object (`[]`, `5`, `\"t\"`): exact class and message"),
    ("Z08", "output is JSON `null`, and separately `[]`: accepted as a legal JSON value or not"),
    ("Z09", "`-` on the channel: exact stdin bytes consumed, and what a second `-` flag would do"),
    ("Z10", "a file-borne submission (`--...-file` or `@path`): supported, absent, or emulated"),
    ("Z11", "framing bound: the exact total cap this channel imposes and where it is enforced"),
    ("Z12", "framing bound adjacent pair: max accepted and max+1 rejected, with the exact message"),
    ("Z13", "composition with the library's per-field DEFAULT_MAX_BYTES: which bound bites first"),
    ("Z14", "unknown operation name: exit, channel, message, and whether any row is written"),
    ("Z15", "absent ledger file: exit, message, and whether the invocation CREATES the database"),
    ("Z16", "repeated channel flag: last-wins, error, or accumulate"),
    ("Z17", "argv size: the largest submission this channel can launch as a real process"),
    ("Z18", "acknowledgement content: whether candidate output bytes are echoed back to stdout"),
    ("Z19", "cross-leaf flag isolation: the new flag(s) rejected on every other leaf, both ways"),
    ("Z20", "`proposal submit --help` and root `--help`: exact new lines and their register"),
)


def _root(override: str | None) -> pathlib.Path:
    if override:
        return pathlib.Path(override).resolve()
    here = pathlib.Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise SystemExit("cannot locate repository root by upward pyproject.toml search")


def _stub(kind: str) -> dict[str, Any]:
    if kind == "map":
        rows = [
            {"id": rid, "locus": locus, **{f: UNKNOWN for f in MAP_FIELDS}, "main_verdict": UNKNOWN}
            for rid, locus in MAP_SEED
        ]
        return {"kind": "map", "rows": rows}
    rows = [
        {"id": rid, "locus": locus, **{f: UNKNOWN for f in SPIKE_FIELDS}, "main_verdict": UNKNOWN}
        for rid, locus in SPIKE_SEED
    ]
    return {"kind": "spike", **{f: UNKNOWN for f in SPIKE_HEADER}, "rows": rows}


def _load(path: pathlib.Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"unreadable artifact: {exc}")
    if type(document) is not dict:
        raise SystemExit("artifact must be a JSON object")
    return document


def _check_anchor(root: pathlib.Path, anchor: str, symbol: str) -> str | None:
    match = re.fullmatch(r"([^:]+):(\d+)", anchor.strip())
    if match is None:
        return f"anchor {anchor!r} is not path:line"
    target = root / match.group(1)
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return f"anchor path {match.group(1)!r} does not resolve"
    index = int(match.group(2))
    if not 1 <= index <= len(lines):
        return f"anchor {anchor!r} is past end of file ({len(lines)} lines)"
    token = symbol.strip().strip("`")
    if token and token not in lines[index - 1]:
        return f"symbol {token!r} is absent from {anchor}"
    return None


def validate(path: pathlib.Path, root: pathlib.Path) -> int:
    document = _load(path)
    kind = document.get("kind")
    if kind not in ("map", "spike"):
        raise SystemExit("kind must be 'map' or 'spike'")
    seed = MAP_SEED if kind == "map" else SPIKE_SEED
    fields = MAP_FIELDS if kind == "map" else SPIKE_FIELDS
    extension = "X" if kind == "map" else "Y"

    rows = document.get("rows")
    if type(rows) is not list or not rows:
        raise SystemExit("rows must be a non-empty array")

    problems: list[str] = []
    unknown = 0
    anchors_bad = 0
    deltas = 0

    if kind == "spike":
        for name in SPIKE_HEADER:
            value = document.get(name, UNKNOWN)
            if type(value) is not str or value.strip() in ("", UNKNOWN):
                unknown += 1
                continue
            if name == "head_sha" and re.fullmatch(r"[0-9a-f]{7,40}", value.strip()) is None:
                problems.append(f"head_sha {value!r} is not a git object name")
            if name == "diff_stat":
                stat = re.fullmatch(r"\+(\d+)/-(\d+)", value.strip())
                if stat is None:
                    problems.append(f"diff_stat {value!r} must read +N/-M")
                elif int(stat.group(1)) < ADDITIONS_FLOOR:
                    problems.append(
                        f"diff_stat additions {stat.group(1)} < {ADDITIONS_FLOOR}:"
                        " this alternative was never implemented"
                    )
            if name == "driver" and not (root / value.strip()).is_file():
                problems.append(f"driver {value!r} does not resolve under the root")

    seen: list[str] = []
    for row in rows:
        if type(row) is not dict:
            problems.append("every row must be an object")
            continue
        rid = str(row.get("id", "")).strip()
        seen.append(rid)
        if not re.fullmatch(rf"(?:M|Z|{extension})\d{{2,3}}", rid):
            problems.append(f"row id {rid!r} is not a seeded or extension id")
        if "locus" not in row or not str(row.get("locus", "")).strip():
            problems.append(f"{rid}: locus must name the row's subject")
        for name in fields:
            value = row.get(name, UNKNOWN)
            if type(value) is not str or value.strip() in ("", UNKNOWN):
                unknown += 1
                continue
            text = value.strip()
            if name in ("finding", "bearing", "delta") and len(text) < PROSE_FLOOR:
                problems.append(f"{rid}.{name}: {len(text)} chars < {PROSE_FLOOR}")
            if name == "verdict" and text.split(":")[0].strip() not in VERDICTS:
                problems.append(f"{rid}.verdict must open with one of {VERDICTS}")
        if kind == "map":
            anchor = str(row.get("anchor", UNKNOWN)).strip()
            symbol = str(row.get("symbol", UNKNOWN)).strip()
            if UNKNOWN not in (anchor, symbol) and anchor and symbol:
                reason = _check_anchor(root, anchor, symbol)
                if reason is not None:
                    anchors_bad += 1
                    problems.append(f"{rid}: {reason}")
        else:
            baseline = str(row.get("baseline", UNKNOWN)).strip()
            alt = str(row.get("alt", UNKNOWN)).strip()
            if UNKNOWN not in (baseline, alt) and baseline != alt:
                deltas += 1

    missing = [rid for rid, _ in seed if rid not in seen]
    if missing:
        problems.append(f"seeded ids absent: {', '.join(missing)}")
    duplicates = sorted({rid for rid in seen if seen.count(rid) > 1})
    if duplicates:
        problems.append(f"duplicate ids: {', '.join(duplicates)}")
    if kind == "spike" and unknown == 0 and deltas < DELTA_FLOOR:
        problems.append(
            f"only {deltas} rows separate baseline from alt (floor {DELTA_FLOOR}):"
            " a corpus answerable against baseline alone forces no implementation"
        )

    print(f"KIND: {kind}")
    print(f"ROWS: {len(rows)} ({len(seed)} seeded, {len(rows) - len(seed)} extension)")
    print(f"UNKNOWN-CELLS: {unknown}")
    print(f"EXEMPT-FIELDS: {', '.join(EXEMPT)} (MAIN-owned; never graded here)")
    if kind == "map":
        print(f"ANCHORS-BAD: {anchors_bad}")
    else:
        print(f"DELTA-ROWS: {deltas}")
    for problem in problems:
        print(f"PROBLEM: {problem}")
    if unknown or problems:
        print("FAIL")
        return 1
    print("PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", nargs="?")
    parser.add_argument("--emit-stub", choices=("map", "spike"))
    parser.add_argument("--root")
    args = parser.parse_args()
    if args.emit_stub:
        print(json.dumps(_stub(args.emit_stub), ensure_ascii=False, indent=2))
        return 0
    if not args.artifact:
        parser.error("give an artifact path or --emit-stub")
    return validate(pathlib.Path(args.artifact), _root(args.root))


if __name__ == "__main__":
    sys.exit(main())
