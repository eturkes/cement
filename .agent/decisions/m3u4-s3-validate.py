"""Grade the M3.4 S3 wave tables for completeness.

Usage:
  uv run python .agent/decisions/m3u4-s3-validate.py --emit-seed <kind>
  uv run python .agent/decisions/m3u4-s3-validate.py <path-to-table.json>

Kinds and their deliverables:
  probes   .agent/decisions/m3u4-probes.json   the oracle's independent observations
  review   .agent/decisions/m3u4-review.json   the adversarial review of the landed diff
  mutants  .agent/decisions/m3u4-mutants.json  the mutation catalogue and its verdicts

Each seed carries every row's SUBJECT already named, because a teammate can work a
named locus after any death while discovering which rows exist is not resumable. Rows
may be ADDED beyond the seed and the seed is a floor, never a cap: extension ids use
the kind's letter with a number above the seeded range.

MAIN-owned columns are EXEMPT from grading and are printed on every run, because a
teammate's completeness and MAIN's ruling are two different deliverables and only one
of them is graded here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / ".agent" / "decisions"

UNKNOWN = "unknown"
PROSE_MIN = 24

SPEC: dict[str, dict[str, object]] = {
    "probes": {
        "path": DECISIONS / "m3u4-probes.json",
        "graded": ("probe", "observed"),
        "exempt": ("main_observed", "differs", "main_ruling"),
        "prose": ("probe", "observed"),
    },
    "review": {
        "path": DECISIONS / "m3u4-review.json",
        "graded": ("finding", "severity", "reproduction", "acceptance_check"),
        "exempt": ("disposition",),
        "prose": ("finding", "reproduction", "acceptance_check"),
    },
    "mutants": {
        "path": DECISIONS / "m3u4-mutants.json",
        "graded": ("anchor", "mutation", "expected_killer", "result"),
        "exempt": ("main_ruling",),
        "prose": ("anchor", "mutation", "expected_killer"),
    },
}

SEVERITY = ("blocking", "material", "minor", "cleared")
RESULT = ("killed", "survived", "equivalent", "unreachable", UNKNOWN)

# ---------------------------------------------------------------------------
# Seeded row subjects. Every locus names what the row is ABOUT; the teammate
# supplies the evidence. Loci are drawn from the ruled disagreements in contract
# sections 12-15, which are the only probes that can discriminate two designs.
# ---------------------------------------------------------------------------
PROBE_SUBJECTS: list[tuple[str, str, str]] = [
    ("Z01", "§14 D24, §15", "mismatched binding through the singular read: class, message and precedence"),
    ("Z02", "§14 D24, §15", "mismatched binding through the list feed"),
    ("Z03", "§14 X32, §D22", "mismatched binding through the report, including past the detail cap"),
    ("Z04", "§15 LEFT JOIN", "orphan proposal whose request row is absent: singular read"),
    ("Z05", "§15 LEFT JOIN", "orphan proposal: list feed visibility"),
    ("Z06", "§15 LEFT JOIN", "orphan proposal: review"),
    ("Z07", "§13 RULING", "ReviewResult returned by accept: every field value"),
    ("Z08", "§13 RULING", "ReviewResult returned by correct: every field value"),
    ("Z09", "§13 RULING", "ReviewResult returned by reject: the two null-valued fields"),
    ("Z10", "§13 CLI triples", "CLI JSON for accept: exact sorted key set, values and exit code"),
    ("Z11", "§13 CLI triples", "CLI JSON for correct"),
    ("Z12", "§13 CLI triples", "CLI JSON for reject, including both explicit nulls"),
    ("Z13", "§12 RULING, Y11", "statements issued by the singular read over the whole channel"),
    ("Z14", "§12 RULING, Y11", "statements issued by the list feed"),
    ("Z15", "§12 RULING, Y11", "statements issued by the report's pending count and detail"),
    ("Z16", "§12 RULING, Y11", "statements issued by review on accept"),
    ("Z17", "§D23, A13", "pending page order on a reverse-created fixture at a small projection limit"),
    ("Z18", "§D23, A13", "pending page order at the full projection limit"),
    ("Z19", "§D22, §15 tail", "pending count with rows past the detail cap"),
    ("Z20", "§12 RULING", "a selection carrying duplicate proposal identifiers"),
    ("Z21", "§12 RULING", "an empty selection"),
    ("Z22", "§D15, Y21", "stale operation revision crossed with accept"),
    ("Z23", "§D15, Y21", "stale operation revision crossed with correct"),
    ("Z24", "§D15, Y21", "stale operation revision crossed with reject"),
    ("Z25", "§D17, A09", "conflict quarantine: example rows created for the reviewed proposal"),
    ("Z26", "§D19, A10", "proposals.status_sequence against the decision event sequence"),
    ("Z27", "§D21", "partition isolation against an underscore collider and a case variant"),
    ("Z28", "§D21", "operation isolation against an underscore collider and a case variant"),
    ("Z29", "§15 D24", "malformed input_json on a real ledger through each read path"),
    ("Z30", "§15 D24", "a legitimately NULL column reaching a scalar conversion"),
    ("Z31", "§14 D10", "the handle route's proposal.created payload"),
    ("Z32", "§14 D10", "the direct route's proposal.created payload"),
    ("Z33", "§Y16", "the connection the adapter reads on, against the one the caller opened"),
    ("Z34", "§Y16", "review's binding lookup and request status write, and whether one lock spans both"),
    ("Z35", "§D20", "cross-partition invisibility on each read path that names a partition"),
    ("Z36", "§D08", "PendingProposalGap values projected by the report"),
]

REVIEW_SUBJECTS: list[tuple[str, str, str]] = [
    ("R01", "correctness", "_proposal_bindings: the three selection branches and their parameter binding"),
    ("R02", "correctness", "_proposal_binding_from_row: which fields it validates and which it passes through raw"),
    ("R03", "correctness", "_proposal_binding: the cardinality check and the None contract"),
    ("R04", "correctness", "_write_proposal_request_status: the two UPDATE statements and their rowcount use"),
    ("R05", "correctness", "get_proposal and proposal: what changed beside the dropped field"),
    ("R06", "correctness", "proposals: the feed selection, its status filter and its limit"),
    ("R07", "correctness", "review: decision routing, the writer call site and the returned value"),
    ("R08", "correctness", "function_report: the pending count, the detail cap and the gap projection"),
    ("R09", "claim soundness", "the S2 commit message and roadmap record against what the diff actually does"),
    ("R10", "claim soundness", "contract section 12's RULING text against the shipped adapter"),
    ("R11", "claim soundness", "contract section 15's corrections: whether each replacement ground holds"),
    ("R12", "guarantee gap", "what the confinement instrument proves and what its prose claims"),
    ("R13", "guarantee gap", "what the shape instrument proves and what D11 claims it carries"),
    ("R14", "guarantee gap", "the ruled public behaviour change: every surface that still reports the old value"),
    ("R15", "CLAUDE.md authoring", "the durable files this unit touched, against the Authoring rules"),
    ("R16", "CLAUDE.md engineering", "the shipped code against KISS, deduplication and scoped-module rules"),
    ("R17", "KISS", "any branch, guard or field the shipped design carries that nothing can reach"),
    ("R18", "regression risk", "behaviour the eight owned sites had at 30195e7 that no test now pins"),
]

MUTANT_SUBJECTS: list[tuple[str, str, str]] = [
    ("M01", "adapter", "the _ProposalIds branch selector"),
    ("M02", "adapter", "the empty-selection early return"),
    ("M03", "adapter", "the duplicate-identifier guard"),
    ("M04", "adapter", "the _ProposalIds WHERE partition predicate"),
    ("M05", "adapter", "the _ProposalIds id-list predicate"),
    ("M06", "adapter", "the _ProposalFeed status filter"),
    ("M07", "adapter", "the _ProposalFeed after_sequence predicate"),
    ("M08", "adapter", "the _ProposalFeed ORDER BY and LIMIT"),
    ("M09", "adapter", "the _PendingProposals count statement's predicates"),
    ("M10", "adapter", "the missing-count guard"),
    ("M11", "adapter", "the _PendingProposals detail predicates"),
    ("M12", "adapter", "the _PendingProposals ORDER BY p.id"),
    ("M13", "adapter", "the _PendingProposals LIMIT"),
    ("M14", "adapter", "the pending selection's unbounded total"),
    ("M15", "adapter", "the invalid-selection fallback"),
    ("M16", "adapter", "the JOIN's partition equality"),
    ("M17", "adapter", "the JOIN's request-id equality"),
    ("M18", "adapter", "the JOIN kind itself, inner against outer"),
    ("M19", "row record", "each scalar validator call in _proposal_binding_from_row"),
    ("M20", "row record", "the exception tuple that maps a bad scalar to IntegrityError"),
    ("M21", "row record", "the raw pass-through of request_status"),
    ("M22", "singular", "the cardinality check in _proposal_binding"),
    ("M23", "singular", "the empty-result None return"),
    ("M24", "writer", "the rejected UPDATE's status and pending predicates"),
    ("M25", "writer", "the rejected UPDATE's proposal_id predicate"),
    ("M26", "writer", "the resolved branch's output and example guard"),
    ("M27", "writer", "the resolved UPDATE's column assignments"),
    ("M28", "writer", "the resolved UPDATE's predicates"),
    ("M29", "writer", "the returned rowcount"),
    ("M30", "consumer", "get_proposal's binding lookup and its NotFoundError"),
    ("M31", "consumer", "proposal's binding lookup"),
    ("M32", "consumer", "proposals' feed parameters"),
    ("M33", "consumer", "_proposal_record's field set"),
    ("M34", "consumer", "_proposal_content's argument source"),
    ("M35", "consumer", "review's binding lookup and revision fence"),
    ("M36", "consumer", "review's writer call arguments per decision"),
    ("M37", "consumer", "the ReviewResult constructed per decision"),
    ("M38", "consumer", "function_report's pending count source"),
    ("M39", "consumer", "function_report's detail cap"),
    ("M40", "consumer", "_pending_proposal_gap_from_row's field set"),
    ("M41", "shape", "ReviewResult's frozen and slots flags"),
    ("M42", "shape", "the removed request_id on ProposalView"),
    ("M43", "shape", "the removed request_id on PendingProposalGap"),
    ("M44", "export", "the __init__ export and __all__ entry"),
]


def _fail(message: str) -> None:
    print(f"INVALID: {message}")


def emit_seed(kind: str) -> int:
    spec = SPEC[kind]
    subjects = {"probes": PROBE_SUBJECTS, "review": REVIEW_SUBJECTS, "mutants": MUTANT_SUBJECTS}[kind]
    columns = tuple(spec["graded"]) + tuple(spec["exempt"])
    rows = []
    for identifier, section, locus in subjects:
        row: dict[str, object] = {"id": identifier, "section": section, "locus": locus}
        for column in columns:
            row[column] = None if column in spec["exempt"] else UNKNOWN
        rows.append(row)
    path = Path(str(spec["path"]))
    path.write_text(
        json.dumps({"kind": kind, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {path.relative_to(ROOT)} ({len(rows)} rows)")
    return 0


def grade(path: Path) -> int:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"{path} is unreadable: {error}")
        return 2
    kind = document.get("kind")
    if kind not in SPEC:
        _fail(f"kind must be one of {sorted(SPEC)}, got {kind!r}")
        return 2
    spec = SPEC[kind]
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        _fail("rows must be a nonempty list")
        return 2

    graded = tuple(spec["graded"])
    prose = set(spec["prose"])
    unknown_cells = 0
    problems: list[str] = []
    seen: set[str] = set()

    for index, row in enumerate(rows):
        identifier = row.get("id") or f"row[{index}]"
        if identifier in seen:
            problems.append(f"{identifier}: duplicate id")
        seen.add(identifier)
        for column in ("id", "section", "locus", *graded):
            if column not in row:
                problems.append(f"{identifier}: missing column {column}")
        for column in graded:
            value = row.get(column)
            if value is None or (isinstance(value, str) and value.strip().lower() == UNKNOWN):
                unknown_cells += 1
                continue
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{identifier}.{column}: must be a nonempty string")
                continue
            if column in prose and len(value.strip()) < PROSE_MIN:
                problems.append(
                    f"{identifier}.{column}: {len(value.strip())} chars, needs {PROSE_MIN}"
                )
        if kind == "review":
            severity = row.get("severity")
            if isinstance(severity, str) and severity not in SEVERITY and severity != UNKNOWN:
                problems.append(f"{identifier}.severity: must be one of {SEVERITY}")
        if kind == "mutants":
            result = row.get("result")
            if isinstance(result, str) and result not in RESULT:
                problems.append(f"{identifier}.result: must be one of {RESULT}")

    seeded = {
        "probes": len(PROBE_SUBJECTS),
        "review": len(REVIEW_SUBJECTS),
        "mutants": len(MUTANT_SUBJECTS),
    }[kind]
    for problem in problems:
        _fail(problem)
    print(f"KIND: {kind}")
    print(f"ROWS: {len(rows)} (seeded {seeded}, extension {max(0, len(rows) - seeded)})")
    print(f"GRADED-COLUMNS: {', '.join(graded)}")
    print(f"EXEMPT-COLUMNS: {', '.join(spec['exempt'])} (MAIN-owned, never graded here)")
    print(f"UNKNOWN-CELLS: {unknown_cells}")
    ok = not problems and unknown_cells == 0
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-seed", choices=sorted(SPEC), help="write the all-unknown seed")
    parser.add_argument("table", nargs="?", help="the table to grade")
    args = parser.parse_args(argv)
    if args.emit_seed:
        return emit_seed(args.emit_seed)
    if not args.table:
        parser.error("give a table to grade or --emit-seed <kind>")
    return grade(Path(args.table))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
