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

import re
import sys
from pathlib import Path

from wave_validate import ObservationTables

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


ENGINE = ObservationTables(
    CLEARED=CLEARED,
    DIVERGENCE_FIELDS=DIVERGENCE_FIELDS,
    EXTENSION=EXTENSION,
    MAIN_OWNED=MAIN_OWNED,
    PROSE_MIN=PROSE_MIN,
    REVIEW_FIELDS=REVIEW_FIELDS,
    REVIEW_LENSES=REVIEW_LENSES,
    ROOT=ROOT,
    SEVERITIES=SEVERITIES,
    UNKNOWN=UNKNOWN,
    VERDICTS=VERDICTS,
    documentation=__doc__,
    source_path=__file__
)
VALIDATORS = ENGINE.VALIDATORS = {'divergences': ENGINE._validate_divergences, 'review': ENGINE._validate_review}
_load_probe_subjects = ENGINE._load_probe_subjects
_fail = ENGINE._fail
_rows = ENGINE._rows
_prose = ENGINE._prose
_count_unknown = ENGINE._count_unknown
_validate_divergences = ENGINE._validate_divergences
_validate_review = ENGINE._validate_review
_seed = ENGINE._seed
main = ENGINE.main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
