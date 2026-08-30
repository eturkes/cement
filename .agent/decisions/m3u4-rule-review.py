"""Rule every finding of the M3.4 S3 adversarial review table.

Usage:
  uv run python .agent/decisions/m3u4-rule-review.py           # write
  uv run python .agent/decisions/m3u4-rule-review.py --check   # gate, rc 1 when stale

`m3u4-review.json` carries the reviewer's finding, severity, reproduction and acceptance
check. `disposition` is MAIN's alone. Every row is ruled: the eight `cleared` rows record
that the reviewer found no defensible alternative, and each confirmed row names the commit
or the instrument that closes it.

Serialization is pinned by round-trip before writing, so a second run rewrites the same
bytes and `--check` is a true in-sync gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / ".agent" / "decisions" / "m3u4-review.json"

CLEARED = (
    "CLEARED. The lens ran and found no defensible alternative to the shipped design, so "
    "the row is evidence of coverage rather than a defect."
)

DISPOSITIONS: dict[str, str] = {
    "R01": (
        "CONFIRMED and FIXED at 6e9ac37. The inner join deleted an orphaned proposal from "
        "the result set, which made it indistinguishable from a proposal that was never "
        "stored. The ids and feed statements now LEFT JOIN and "
        "_proposal_binding_from_row refuses a NULL bound_request_id, so absent and "
        "orphaned stay distinguishable inside one statement. Pinned by "
        "test_orphaned_binding_fails_closed_and_stays_distinct_from_an_absent_proposal "
        "and by B34's two tests; mutants M18 and M31 die on them."
    ),
    "R02": (
        "CONFIRMED as a text defect and CORRECTED at 1143332; the shipped code already "
        "held the boundary. Section 12 named the field `input`, which no shape carries, "
        "and now names `input_json`. bound_input_json is read at exactly one site, inside "
        "_proposal_binding_from_row, and _proposal_content consumes binding.input_json "
        "with binding.input_hash. The AST assertion the acceptance check asks for is "
        "carried mechanically by mutant M34, which rewrites _proposal_content(binding) to "
        "_proposal_content(binding.row) and is killed."
    ),
    "R08": (
        "CONFIRMED and FIXED with R01. The pending count statement proves that every "
        "pending binding in the partition EXISTS, unbounded by the detail cap, so a "
        "hidden tail raises instead of shrinking the count. B28's two tests split the "
        "cases: a binding missing inside the page and a binding missing beyond it. "
        "Section 14 X32 now also states the bound this does NOT give - cross-field "
        "consistency and JSON content hold for returned detail alone."
    ),
    "R09": (
        "CONFIRMED and CORRECTED at 1143332. Z50 measured lexical coupling; survival "
        "through M3.6b is a PREDICTION resting on that census, and both the roadmap and "
        "tests/test_proposal_binding.py now say so. A census measures coupling, never "
        "survival."
    ),
    "R10": (
        "CONFIRMED and CORRECTED at 1143332. Section 12 item 1 WITHDRAWS 'one statement "
        "per call' and publishes measured counts: requests-naming statements per "
        "selection are ids 1, feed 1, pending 2; whole-channel counts are get_proposal 8, "
        "proposals 8, function_report 20, review-accept 15. Item 4 corrects `input` to "
        "`input_json` and states that `partition` is the caller's scope echoed, never "
        "recovered. _proposal_bindings' own docstring now carries the same pair."
    ),
    "R11": (
        "CONFIRMED and FIXED at 841e710. Malformed stored input_json reached callers as "
        "ValidationError from four of the five paths; _proposal_content now translates "
        "every stored-JSON failure to IntegrityError, and the five-path fixture uses one "
        "real SQLite TEXT mutation with no proxy storage class. The independent oracle "
        "agrees on all five paths (Z28)."
    ),
    "R12": (
        "CONFIRMED and CORRECTED at 1143332. The confinement instrument proves a LEXICAL "
        "literal-string census: runtime-composed SQL, cross-module SQL and views stay "
        "invisible to it. The docstrings now state that limit and B06 owns the tripwire "
        "boundary, which accepts a literal hidden namer and rejects runtime composition."
    ),
    "R13": (
        "CONFIRMED and FIXED at 1143332. ProposalView and PendingProposalGap gained "
        "annotation-text pins, resolved-hint spot checks and no-default checks. Proved by "
        "mutation: retyping ProposalView.input to str turns the shape test red, and "
        "models.py restores byte-clean."
    ),
    "R15": (
        "CONFIRMED and SCHEDULED for S4. Contract sections 7 and 12-15 retain wave "
        "chronology, dispatch history and worktree state, which the durable-authoring "
        "rule prunes. The grounds stayed load-bearing while the battery was written, so "
        "the move waits for the closure session: chronology to .agent/archive/, rulings "
        "and measured numbers stay in the contract."
    ),
    "R17": (
        "KEEP, with the pin DEFERRED to .agent/polish.md (pri=3 size=S). M3.6b's "
        "direct-column swap is expected to want the plural form, so deleting it now to "
        "re-add it there is churn. The decisive mutation campaign measures the exposure "
        "exactly: M02 empty selection, M03 duplicate rejection, M15 invalid-selection "
        "fallback and M26 the resolved writer's output guard survive all four verdict "
        "modules, and the polish row carries their acceptance check. Ordering is the open "
        "question a pin must answer first, because no obligation grants selection order."
    ),
    "R18": (
        "CONFIRMED as a gate gap, and its SUBJECT INVERTED. The inner join was the defect "
        "rather than the behaviour to pin, so B34's two tests now assert the LEFT JOIN, "
        "IntegrityError on all five paths, and a NotFoundError control before and after "
        "corruption. Mutant M18 was inverted to outer-to-INNER and is killed, which is "
        "the independent pin the finding asked for."
    ),
}


def rule(rows: list[dict[str, object]]) -> int:
    changed = 0
    for row in rows:
        identifier = str(row["id"])
        wanted = DISPOSITIONS.get(identifier)
        if wanted is None:
            if row["severity"] != "cleared":
                raise SystemExit(f"INVALID: finding {identifier} has no disposition")
            wanted = CLEARED
        if row.get("disposition") != wanted:
            row["disposition"] = wanted
            changed += 1
    return changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when a disposition is stale")
    args = parser.parse_args(argv)

    document = json.loads(TABLE.read_text(encoding="utf-8"))
    rows = document["rows"]
    unknown = sorted(set(DISPOSITIONS) - {str(row["id"]) for row in rows})
    if unknown:
        print(f"INVALID: the table has no row for {unknown}")
        return 2

    changed = rule(rows)
    serialized = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if json.loads(serialized) != document:
        print("INVALID: the table does not round-trip")
        return 2

    if args.check:
        print(f"RULED: {len(rows)}  STALE: {changed}")
        print("RESULT: IN-SYNC" if changed == 0 else "RESULT: STALE")
        return 0 if changed == 0 else 1

    TABLE.write_text(serialized, encoding="utf-8")
    print(f"WROTE: {TABLE.relative_to(ROOT)}  ruled {changed} of {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
