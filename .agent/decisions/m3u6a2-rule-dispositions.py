#!/usr/bin/env python3
"""MAIN's ruling over the 32 frames M3.6a2's deletion broke, as an idempotent patcher.

`m3u6a2-dispositions-validate.py` proves a `delete` row's test is GONE and a surviving row's span
CHANGED. Neither predicate can see the failure that matters: a rebase that keeps the frame and
drops the check. Assertion count is the cheapest signal for that, and it is a proxy — a drop is
legitimate exactly when the dropped call's subject left with the lifecycle. So MAIN reads every
drop and records the ruling here, and gate 9 then holds the census: a surviving row whose
assertions FELL must be ruled `affirmed-drop-ruled`, and a row NOT so ruled must not fall.

Baseline for every count below is `27658c4`, the seeded table's own commit.

    uv run python .agent/decisions/m3u6a2-rule-dispositions.py          # apply
    uv run python .agent/decisions/m3u6a2-rule-dispositions.py --check  # gate 9's ruling half
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TABLE = HERE / "m3u6a2-dispositions.json"

# Rows whose disposition follows from the frame's subject and whose assertion census shows NO net
# loss. Named rather than defaulted, so a row changing class fails loudly instead of inheriting a
# ruling it was never given.
AFFIRMED_CLASS = frozenset((
    "R01", "R03", "R05", "R07", "R13", "R14", "R19", "R20", "R21", "R22",
    "R23", "R24", "R25", "R26", "R27", "R28", "R29", "R30",
))
AFFIRMED_CLASS_RULING = (
    "affirmed",
    "Disposition matches the frame's subject and the assertion census shows no net loss against "
    "`27658c4`; six of these rows gained checks. Gate 9's structural half carries the rest.",
)

# id -> (main_verdict, main_note). Vocabulary:
#   affirmed                 - class ruling above.
#   affirmed-cover-verified  - a `delete` whose claimed surviving cover MAIN located BY NAME.
#   affirmed-drop-ruled      - a surviving frame whose assertion count FELL; MAIN read the diff.
ADJUDICATION: dict[str, tuple[str, str]] = {
    "R06": ("affirmed-cover-verified", (
        "Subject is interoperability from `submit_proposal` back into `System.handle`, and its only "
        "asserted outcome is `ReviewRequired` from the deleted dispatcher. The cover the grounds "
        "leave unnamed is real: `tests/test_submission.py` retains "
        "`test_a_submitted_proposal_flows_through_review` and "
        "`test_a_revised_operation_still_accepts_a_direct_submission`.")),
    "R08": ("affirmed", (
        "Request-ID artifact-dispatch cache bound to the producing execution. The cache row, the "
        "`handle` replay, `request_status` polling and the reconciliation outcome are each on the "
        "deletion set, so the frame has no residue to rehome.")),
    "R09": ("affirmed", (
        "Same family as R08 on the confirmed-output cache: both access paths run through "
        "`request_status` and a replayed `handle`, and the immutability property they exercised is "
        "pinned independently by the example-revocation tests that survive.")),
    "R10": ("affirmed", (
        "The frame pinned `handle` artifact dispatch trusting a sealed promotion receipt WITHOUT "
        "rehashing child tests. Artifact dispatch has no successor, and `resolve` pays full P1-P6 "
        "verification per call by ruling, so the fast path is deliberately absent rather than "
        "unpinned. Rehoming this assertion onto `resolve` would assert the opposite of the ruling.")),
    "R11": ("affirmed", (
        "Generation-lease expiry, `request_status` polling and `handle` reclamation under one "
        "request ID. Every assertion belongs to the lease/retry lifecycle; L04-L06 pin the knob's "
        "absence and gate 7's M15 kills its return.")),
    "R17": ("affirmed-cover-verified", (
        "Subject is replaying a pre-quarantine `handle` request ID after artifact suspension for a "
        "`ReconciliationRequired`. Ambiguity quarantine leaves with `handle` by ruling; the "
        "SURVIVING quarantine causes stay pinned by `tests/test_system.py`'s "
        "`test_counterexample_and_revocation_quarantine`, "
        "`test_late_review_counterexample_quarantines_promoted_scope` and "
        "`test_challenge_quarantines_corrupt_promoted_artifact`, plus battery L22 and L31.")),
    "R31": ("affirmed", (
        "Concurrent duplicate `handle` calls returning `InProgress` under a held lease. Request-ID "
        "idempotency, the lease and `InProgress` are all deleted; nothing in the frame outlives "
        "them.")),
    "R32": ("affirmed", (
        "Revision cancellation of an in-flight `handle` generation and its `ReconciliationRequired` "
        "outcome. The independent revision-bump and retirement-filter properties the frame might "
        "have carried are pinned by L17, which gate 7's M06, M07 and M08 each kill.")),
    "R02": ("affirmed-drop-ruled", (
        "5 -> 4. The dropped call is `assertIsInstance(outcome, ReviewRequired)`, type-narrowing "
        "scaffolding for the deleted dispatcher's return. The payload assertion STRENGTHENS: "
        "`{\"request_id\": request_id}` becomes the literal `{}`.")),
    "R04": ("affirmed-drop-ruled", (
        "5 -> 4. The dropped `assertEqual` compared each surviving route's payload to "
        "`handle_payload`, a value derived from the same run — it passes when both sides are wrong. "
        "It is replaced by the literal `{}`, so the census loses a call and gains a check.")),
    "R12": ("affirmed-drop-ruled", (
        "13 -> 8. Six of the seven dropped calls are three `assertIsInstance` plus three bare "
        "`assert isinstance` narrowing pairs for the deleted `ReviewRequired`. The rebase pins a "
        "deterministic request id through `_new_id` and ADDS a direct `requests` read asserting the "
        "cross-partition pair {(`tenant_a`, `shared_request`), (`tenantXa`, `shared_request`)} — the "
        "collision-pair shape scope-isolation fixtures are required to carry.")),
    "R15": ("affirmed-drop-ruled", (
        "9 -> 7. Three `assertIsInstance` calls on deleted outcome classes. The frame gains "
        "`self.source.calls[-1].operation_revision == 1` and binds `revise_operation`'s return, so "
        "the revision-invalidation subject it owns is pinned more directly than before.")),
    "R16": ("affirmed-drop-ruled", (
        "5 -> 4. The dropped `assertRaises(ValidationError)` guarded "
        "`System(db, generation_lease_seconds=1.0000001)`, a constructor keyword this unit deletes. "
        "L04's keyword-rejection half and gate 7's M15 own that ground now.")),
    "R18": ("affirmed-drop-ruled", (
        "6 -> 5. Drops request-ID idempotency (`assertEqual(first, second)`) and the `ConflictError` "
        "replay, both deleted. ADDS a second `assertRaises(NotFoundError)` so cross-partition "
        "isolation is asserted in BOTH directions where it was asserted in one.")),
}
for _row_id in AFFIRMED_CLASS:
    ADJUDICATION[_row_id] = AFFIRMED_CLASS_RULING

VERDICTS = {"affirmed", "affirmed-cover-verified", "affirmed-drop-ruled"}


def _load() -> dict[str, object]:
    return json.loads(TABLE.read_text(encoding="utf-8"))


def _serialize(table: dict[str, object]) -> str:
    """The table's own serialization, measured by round-trip: indent 2, ASCII-escaped, newline."""
    return json.dumps(table, indent=2) + "\n"


def apply(check_only: bool) -> int:
    table = _load()
    rows: list[dict[str, object]] = table["rows"]  # type: ignore[assignment]
    present = {str(row["id"]) for row in rows}
    if present != set(ADJUDICATION):
        print(
            f"ID-SET: unruled={sorted(present - set(ADJUDICATION))} "
            f"unknown={sorted(set(ADJUDICATION) - present)}"
        )
        return 1

    for row in rows:
        verdict, note = ADJUDICATION[str(row["id"])]
        row["main_verdict"] = verdict
        row["main_note"] = note

    rendered = _serialize(table)
    if check_only:
        if rendered != TABLE.read_text(encoding="utf-8"):
            print("CHECK: the committed table does not carry this ruling; rerun without --check")
            return 1
        print("CHECK: ruling applied and byte-identical")
    else:
        changed = rendered != TABLE.read_text(encoding="utf-8")
        TABLE.write_text(rendered, encoding="utf-8")
        print("APPLIED" if changed else "no-op")

    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["main_verdict"])] = counts.get(str(row["main_verdict"]), 0) + 1
    for verdict in sorted(counts):
        print(f"{verdict}: {counts[verdict]}")
    print(f"ROWS: {len(rows)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rule M3.6a2's 32 broken frames.")
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    return apply(parser.parse_args(argv).check)


if __name__ == "__main__":
    sys.exit(main())
