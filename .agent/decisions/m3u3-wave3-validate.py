#!/usr/bin/env python3
"""Structural validator for M3.3 wave-3 artifacts.

Usage:
  uv run python .agent/decisions/m3u3-wave3-validate.py <artifact.json>
  uv run python .agent/decisions/m3u3-wave3-validate.py --emit-seed divergences|review

The artifact's top-level ``kind`` selects the schema:

  "divergences"  the oracle differential, one row per probe of m3u3-probes.json
  "review"       post-implementation adversarial review, one row per seeded lens

Exit 0 = structurally valid AND nothing left ``unknown`` outside a MAIN-owned
field. Exit 1 = structural defect or an unfilled cell. Exit 2 = unreadable input.

Seeding contract: ``--emit-seed`` writes every required id with every value
``unknown``. That file is STRUCTURALLY valid and still exits 1, so UNKNOWN-CELLS
is the flush metric and each filled cell lowers it by one.

``probe`` and ``lens`` are MAIN-owned row identity: the validator rejects any
value other than the seeded text, so a row keeps its assigned subject. Report a
wrong subject to MAIN instead of rewriting it. ``main_ruling`` is MAIN-owned in
the other direction: MAIN fills it, the teammate leaves it ``unknown``, and it
never counts as unfilled. Print the exempt columns before crediting any table as
closed - a teammate's completeness and MAIN's ruling are two deliverables and
only one of them is graded here.

Retarget clause: seeding must never cap discovery. Both kinds accept EXTRA rows
whose id matches ``Z<nn>``; an extra row is graded exactly like a seeded one
except that the teammate owns its subject text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "unknown"
MAIN_OWNED = {"main_ruling"}
PROSE_MIN = 20
EXTENSION = re.compile(r"^Z\d{2}$")
CLEARED = re.compile(r"^(no divergence|no defect|not reachable): .{20,}$", re.S)

VERDICTS = {"identical", "differs", "unreachable", UNKNOWN}
SEVERITIES = {"blocking", "material", "minor", "cleared", UNKNOWN}

DIVERGENCE_FIELDS = ("probe", "verdict", "main_observation", "oracle_observation", "divergence", "main_ruling")
REVIEW_FIELDS = ("lens", "finding", "evidence", "severity", "acceptance_check", "main_ruling")

# ---------------------------------------------------------------------------
# Row identity. MAIN owns every string below.
# ---------------------------------------------------------------------------

# One row per oracle probe. Subjects are the probe texts the oracle recorded in
# m3u3-probes.json, so the two tables join on id and the differential compares
# observation field by observation field.
DIVERGENCE_PROBES: dict[str, str] = {}


def _load_probe_subjects() -> dict[str, str]:
    path = ROOT / ".agent" / "decisions" / "m3u3-probes.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row["probe"] for row in payload["rows"]}


# One row per review lens. Z-rows extend. The lenses split into three declared
# groups so two reviewers can take complementary halves without overlap.
REVIEW_LENSES: dict[str, str] = {
    "R01": "correctness of _canonical_candidate: does every rejected candidate shape reach its contracted text, and is any accepted shape unreachable?",
    "R02": "correctness of _submission_revision and the seam's re-read: can the pair report a stale revision the caller never captured?",
    "R03": "correctness of _persist_proposal: does every column of all three rows match D42, D02 and D03 including the shared timestamp?",
    "R04": "containment: can any adapter-controlled byte reach the caller's exception, the event payload, or a stored column?",
    "R05": "the except Exception boundary: which BaseException members reach the caller, and does any leave a partial footprint?",
    "R06": "purity under injected failure: is there a failure point after the first INSERT that commits, and does the ledger survive it byte-identical?",
    "R07": "claim soundness of contract sections 3-8 against the landed code: name every sentence the code falsifies or under-determines",
    "R08": "claim soundness of the roadmap M3.3 entry and .agent/memory.md additions against the landed code and the committed instruments",
    "R09": "guarantee-vs-claim gaps in the two new docstrings and errors.py: does a reader learn a guarantee the code does not give?",
    "R10": "guarantee-vs-claim gaps in README, architecture.md, threat-model.md and adapter-protocol.md for the new surface",
    "R11": "the read-site census update: is every new site recorded by method name, and does any count hide a site?",
    "R12": "mutation reachability: name every added predicate whose deletion the committed suite cannot detect",
    "R13": "fixture adequacy: does any pin rest on a value whose boundary the running system does not actually have?",
    "R14": "project CLAUDE.md Authoring conformance on every durable file M3.3 touched, including this unit's records",
    "R15": "project CLAUDE.md Engineering conformance on the landed code: scope, deduplication, evidence-backed claims",
    "R16": "scope discipline: did M3.3 touch anything section 1 places out of scope, or leave any B01/B02 freeze pin broken?",
}


def _fail(message: str) -> None:
    print(f"INVALID: {message}")


def _rows(payload: dict, required: dict[str, str], fields: tuple[str, ...]) -> tuple[dict[str, dict], int]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        _fail("payload has no 'rows' list")
        return {}, 1
    problems = 0
    seen: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            _fail(f"row is not an object with an id: {row!r:.80}")
            problems += 1
            continue
        identifier = row["id"]
        if identifier in seen:
            _fail(f"duplicate row id {identifier}")
            problems += 1
            continue
        if identifier not in required and not EXTENSION.match(str(identifier)):
            _fail(f"row id {identifier} is neither seeded nor an extension row Z<nn>")
            problems += 1
            continue
        subject = fields[0]
        if identifier in required and row.get(subject) != required[identifier]:
            _fail(f"{identifier}: '{subject}' is MAIN-owned row identity and was rewritten")
            problems += 1
        missing = [field for field in fields if field not in row]
        if missing:
            _fail(f"{identifier}: missing field(s) {missing}")
            problems += 1
        seen[identifier] = row
    for identifier in required:
        if identifier not in seen:
            _fail(f"seeded row {identifier} is absent")
            problems += 1
    return seen, problems


def _prose(identifier: str, field: str, value: object) -> int:
    if value == UNKNOWN:
        return 0
    if not isinstance(value, str) or len(value.strip()) < PROSE_MIN:
        _fail(f"{identifier}: '{field}' must be at least {PROSE_MIN} characters of prose")
        return 1
    return 0


def _count_unknown(row: dict, fields: tuple[str, ...]) -> int:
    return sum(1 for field in fields if field not in MAIN_OWNED and row.get(field) == UNKNOWN)


def _validate_divergences(payload: dict) -> tuple[int, int]:
    required = _load_probe_subjects()
    rows, problems = _rows(payload, required, DIVERGENCE_FIELDS)
    unknown = 0
    for identifier, row in sorted(rows.items()):
        verdict = row.get("verdict")
        if verdict not in VERDICTS:
            _fail(f"{identifier}: 'verdict' must be one of {sorted(VERDICTS)}")
            problems += 1
        for field in ("main_observation", "oracle_observation"):
            value = row.get(field)
            if value != UNKNOWN and not isinstance(value, (dict, str)):
                _fail(f"{identifier}: '{field}' must be the recorded observation object or prose")
                problems += 1
        divergence = row.get("divergence")
        if verdict == "identical" and divergence not in (UNKNOWN, None) and not CLEARED.match(str(divergence)):
            _fail(f"{identifier}: an identical verdict states 'no divergence: <why the join is exact>'")
            problems += 1
        if verdict == "differs":
            problems += _prose(identifier, "divergence", divergence)
        unknown += _count_unknown(row, DIVERGENCE_FIELDS)
    return unknown, problems


def _validate_review(payload: dict) -> tuple[int, int]:
    rows, problems = _rows(payload, REVIEW_LENSES, REVIEW_FIELDS)
    unknown = 0
    for identifier, row in sorted(rows.items()):
        severity = row.get("severity")
        if severity not in SEVERITIES:
            _fail(f"{identifier}: 'severity' must be one of {sorted(SEVERITIES)}")
            problems += 1
        finding = row.get("finding")
        if severity == "cleared" and finding != UNKNOWN and not CLEARED.match(str(finding)):
            _fail(f"{identifier}: a cleared lens states 'no defect: <what was checked and why it holds>'")
            problems += 1
        for field in ("finding", "evidence", "acceptance_check"):
            problems += _prose(identifier, field, row.get(field))
        unknown += _count_unknown(row, REVIEW_FIELDS)
    return unknown, problems


def _seed(kind: str) -> dict:
    if kind == "divergences":
        subjects, fields = _load_probe_subjects(), DIVERGENCE_FIELDS
    else:
        subjects, fields = REVIEW_LENSES, REVIEW_FIELDS
    rows = []
    for identifier, subject in subjects.items():
        row = {"id": identifier, fields[0]: subject}
        row.update({field: UNKNOWN for field in fields[1:]})
        rows.append(row)
    return {"kind": kind, "implementation": UNKNOWN, "rows": rows}


VALIDATORS = {"divergences": _validate_divergences, "review": _validate_review}


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--emit-seed":
        kind = argv[1]
        if kind not in VALIDATORS:
            _fail(f"unknown kind {kind}; expected one of {sorted(VALIDATORS)}")
            return 2
        print(json.dumps(_seed(kind), indent=2))
        return 0
    if len(argv) != 1:
        _fail(__doc__.splitlines()[2].strip())
        return 2
    path = Path(argv[0])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _fail(f"cannot read {path}: {error}")
        return 2
    kind = payload.get("kind")
    if kind not in VALIDATORS:
        _fail(f"top-level 'kind' must be one of {sorted(VALIDATORS)}, got {kind!r}")
        return 2
    unknown, problems = VALIDATORS[kind](payload)
    if payload.get("implementation") == UNKNOWN:
        unknown += 1
    print(f"KIND: {kind}")
    print(f"MAIN-OWNED-COLUMNS: {sorted(MAIN_OWNED)} (exempt from UNKNOWN-CELLS)")
    print(f"UNKNOWN-CELLS: {unknown}")
    print(f"STRUCTURAL-PROBLEMS: {problems}")
    ok = not unknown and not problems
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
