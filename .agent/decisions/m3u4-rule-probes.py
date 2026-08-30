"""Rule every row of the M3.4 differential table.

Usage:
  uv run python .agent/decisions/m3u4-rule-probes.py           # write
  uv run python .agent/decisions/m3u4-rule-probes.py --check   # gate, rc 1 when stale

`m3u4-probes.json` carries the oracle's expectation, MAIN's measured observation and a
`differs` verdict per probe. `main_ruling` is MAIN's alone: the differential names a
divergence, never who is right. Forty rows agree and take the uniform ruling. The two
divergences take a ruling that cites the obligation it turns on.

Serialization is pinned by round-trip before writing, so a second run rewrites the same
bytes and `--check` is a true in-sync gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / ".agent" / "decisions" / "m3u4-probes.json"

AGREES = (
    "AGREES: the independent implementation reproduced MAIN's observation, so this row "
    "carries no obligation."
)

RULINGS: dict[str, str] = {
    "Z03": (
        "MAIN CONFORMS; the oracle read a rationale that over-claimed. X32's obligation "
        "is a MISSING binding beyond the detail cap, which MAIN raises on: the pending "
        "count statement proves binding EXISTENCE over the unbounded partition. Its "
        "rationale sentence 'the cap bounds returned detail, never validation' is "
        "WITHDRAWN, because cross-field consistency and JSON content hold for RETURNED "
        "DETAIL alone. This probe corrupts requests.proposal_id, which leaves the row "
        "present and the join satisfied, so it is a cross-field defect and the report "
        "returns. Hoisting that check into the adapter would pre-empt "
        "_validate_proposal_shape and rewrite the class, message and precedence every "
        "corrupt ledger reports, and the same corruption still fails closed on the "
        "singular read, the feed, review and reconstruct_function_receipt. "
        "docs/architecture.md already publishes the bound: the report validates only "
        "the members it returns."
    ),
    "Z15": (
        "MAIN CONFORMS against corrected text. Section 12's 'one complete statement per "
        "selection' was WITHDRAWN for the pending selection and replaced by measured "
        "counts: requests-naming statements per selection are ids 1, feed 1, pending 2. "
        "The pair is what X32 and section 15 require together - an unbounded count that "
        "proves every pending binding exists, plus a bounded detail that materializes "
        "only the returned page. One unbounded statement cannot hold both, because "
        "serving a one-item page would then materialize the whole partition, which is "
        "the cost the report exists to bound. Y11's baseline-or-better rule is met: the "
        "baseline report issued two requests-naming statements on this path."
    ),
}


def rule(rows: list[dict[str, object]]) -> int:
    changed = 0
    for row in rows:
        wanted = RULINGS.get(str(row["id"]), AGREES)
        if row["differs"] == "yes" and str(row["id"]) not in RULINGS:
            raise SystemExit(f"INVALID: divergence {row['id']} has no ruling")
        if row.get("main_ruling") != wanted:
            row["main_ruling"] = wanted
            changed += 1
    return changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when a ruling is stale")
    args = parser.parse_args(argv)

    document = json.loads(TABLE.read_text(encoding="utf-8"))
    rows = document["rows"]
    unknown = sorted(set(RULINGS) - {str(row["id"]) for row in rows})
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
