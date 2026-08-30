"""Fill MAIN's exempt `main_verdict` column on `m3u4-map.json`, idempotently.

Usage:
  uv run python .agent/decisions/m3u4-rule-map.py           # write the rulings
  uv run python .agent/decisions/m3u4-rule-map.py --check   # in-sync gate, rc 1 when stale

`m3u4-map.json` is ATTENTION-DIRECTING: its wave-1 author graded `UNKNOWN-CELLS: 0`
over the columns the wave-1 validator scored, while `main_verdict` stayed `unknown` on
all 42 rows. A table can grade clean with every MAIN-owned verdict still empty, so the
ruling is a separate deliverable and this is it.

Structural credit, re-derived at `da63741`: 39 of 39 line anchors resolve in range with
0 bad; the three remaining anchors are commit SHAs on the archaeology rows.

Three verdicts, and the distinction is what MAIN actually did with the row:

`credited-by-rederivation`  MAIN established the same fact independently, so the row is
                            evidence. The contract cites the re-derivation.
`credited-structurally`     the anchor resolves and the row directed attention that a
                            downstream artifact consumed, with no independent
                            re-derivation. Browse context, never evidence.
`superseded`                a later ruling overtook the row's finding.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / ".agent" / "decisions" / "m3u4-map.json"

REDERIVED = "credited-by-rederivation"
STRUCTURAL = "credited-structurally"
SUPERSEDED = "superseded"

RULINGS: dict[str, tuple[str, str]] = {
    "Q01": (REDERIVED, "contract section 1 attributes all eight owned sites by AST at da63741, independently of this map"),
    "Q02": (REDERIVED, "same AST attribution; the site table names the method and the role, not this row"),
    "Q03": (REDERIVED, "same AST attribution"),
    "Q04": (REDERIVED, "same AST attribution"),
    "Q05": (REDERIVED, "same AST attribution; section 12's ruling re-read the write from ALT-PROJECTION's own diff"),
    "Q06": (REDERIVED, "same AST attribution; same second reading"),
    "Q07": (REDERIVED, "same AST attribution"),
    "Q08": (REDERIVED, "same AST attribution"),
    "Q09": (REDERIVED, "section 15 re-derived the converter census and CORRECTED D13 against it"),
    "Q10": (REDERIVED, "section 15 established that _proposal_content never carried a request_id, which this row's census asked for"),
    "S01": (STRUCTURAL, "consumed by the burden harness, which measured the field's removal at 252 broken tests over three frames"),
    "S02": (STRUCTURAL, "consumed by the same harness; the gap's identity is ruled in D08"),
    "S03": (STRUCTURAL, "consumed by fork 2; the field-by-field grounds were taken from the spikes' P08 payloads"),
    "S04": (STRUCTURAL, "the verbatim CLI JSON reached section 13 through the spikes' P08 rows, not through this map"),
    "S05": (STRUCTURAL, "superseded in substance by section 14's measured payload census, which found the handle-route leak this row's question could not"),
    "S06": (STRUCTURAL, "consumed by D14 and by the export census"),
    "S07": (REDERIVED, "D26 publishes its own mention counts: README 6, threat-model 1, adapter-protocol 3, architecture 1"),
    "P01": (STRUCTURAL, "became D15; the S3 battery owns its re-derivation under lens A08"),
    "P02": (STRUCTURAL, "became D16, whose bounds section 15 then published as numbers"),
    "P03": (STRUCTURAL, "became D17; the S3 battery owns its re-derivation under lens A09"),
    "P04": (STRUCTURAL, "became D18; lens Y7 found the row's condition inventory missing and the battery owns it"),
    "P05": (STRUCTURAL, "became D19; the S3 battery owns its re-derivation under lens A10"),
    "P06": (STRUCTURAL, "became D20, which section 14 then narrowed to scope-relative"),
    "P07": (STRUCTURAL, "became D21; the collider requirement is this project's standing rule, not this row's finding"),
    "P08": (STRUCTURAL, "became D22 and D23; section 15 corrected the tail to counted-not-reachable"),
    "P09": (STRUCTURAL, "became D24, whose fabricated-only premise section 15 then falsified"),
    "P10": (STRUCTURAL, "accepted as scoping; the out-of-scope site list in contract section 1 carries it"),
    "A01": (STRUCTURAL, "the column union reached the shipped _ProposalBinding through the two spike diffs"),
    "A02": (REDERIVED, "section 12's ruling measured the N+1 exposure directly from ALT-BINDING's committed diff"),
    "A03": (SUPERSEDED, "where the adapter may live was overtaken by the COMPOSE ruling, which sites it by statement ownership"),
    "A04": (STRUCTURAL, "schema facts consumed by D24; the STRICT and NOT NULL properties are re-derived in memory, not here"),
    "A05": (STRUCTURAL, "MAIN accepted the row's out-of-scope conclusion for revise_operation without an independent probe; it sits in D03's permitted set"),
    "G01": (STRUCTURAL, "precedent only; M3.3's plumbing rule reached this unit through the roadmap"),
    "G02": (STRUCTURAL, "the confinement instrument reuses the AST closure shape, extended to a complement assertion"),
    "G03": (SUPERSEDED, "section 7 replaced forecast-by-analog with the measured burden harness"),
    "G04": (SUPERSEDED, "same replacement; the analog churn number never entered the sizing ruling"),
    "G05": (STRUCTURAL, "the 24 .review( call sites were re-counted by the spikes' own census at 30 total"),
    "X01": (STRUCTURAL, "became D10; lens Y20 found the compound obligation satisfiable on dataclasses alone and the battery owns the path matrix"),
    "X02": (REDERIVED, "MAIN measured the freeze this session: SCHEMA_VERSION 2, 14,580 B, sha256 5be3d79f..., equal to SCHEMA_FINGERPRINT"),
    "X03": (REDERIVED, "section 2 re-derived the expired predicate at HEAD and replaced it with confinement plus public shape"),
    "X04": (STRUCTURAL, "became lens Y16 rather than a numbered obligation, which is the gap the lens reported; the battery owns it"),
    "X05": (REDERIVED, "the attack table re-derived the JOIN behaviour with EXPLAIN QUERY PLAN, sharpening it into section 15's LEFT JOIN ground"),
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when the table is out of sync")
    args = parser.parse_args(argv)

    document = json.loads(TABLE.read_text(encoding="utf-8"))
    rows = document["rows"]
    identifiers = [row["id"] for row in rows]
    if sorted(identifiers) != sorted(RULINGS):
        missing = sorted(set(identifiers) - set(RULINGS))
        extra = sorted(set(RULINGS) - set(identifiers))
        print(f"INVALID: id set differs. unruled rows {missing}; rulings with no row {extra}")
        return 2

    changed = 0
    for row in rows:
        verdict, grounds = RULINGS[row["id"]]
        value = f"{verdict}: {grounds}"
        if row.get("main_verdict") != value:
            changed += 1
            row["main_verdict"] = value

    counts: dict[str, int] = {}
    for verdict, _ in RULINGS.values():
        counts[verdict] = counts.get(verdict, 0) + 1

    if args.check:
        print(f"ROWS: {len(rows)}  STALE: {changed}")
        print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        print("RESULT: IN-SYNC" if changed == 0 else "RESULT: STALE")
        return 0 if changed == 0 else 1

    TABLE.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"WROTE: {TABLE.relative_to(ROOT)}  rows {len(rows)}  updated {changed}")
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
