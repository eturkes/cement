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

import sys

from wave_validate import SurfaceTables

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


ENGINE = SurfaceTables(
    ADDITIONS_FLOOR=ADDITIONS_FLOOR,
    DELTA_FLOOR=DELTA_FLOOR,
    EXEMPT=EXEMPT,
    MAP_FIELDS=MAP_FIELDS,
    MAP_SEED=MAP_SEED,
    PROSE_FLOOR=PROSE_FLOOR,
    SPIKE_FIELDS=SPIKE_FIELDS,
    SPIKE_HEADER=SPIKE_HEADER,
    SPIKE_SEED=SPIKE_SEED,
    UNKNOWN=UNKNOWN,
    VERDICTS=VERDICTS,
    documentation=__doc__,
    source_path=__file__
)
_root = ENGINE._root
_stub = ENGINE._stub
_load = ENGINE._load
_check_anchor = ENGINE._check_anchor
validate = ENGINE.validate
main = ENGINE.main

if __name__ == '__main__':
    sys.exit(main())
