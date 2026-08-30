"""Idempotent, count-asserted test surgery for M3.4's public-shape freeze.

Rerunning on a repaired tree prints ``no-op`` for every edit. Each edit asserts the exact
occurrence count of its anchor BEFORE applying it, so a repeated fragment aborts loudly
instead of mutating the wrong span, and every anchor is multi-line wherever its first line
repeats. Run from the repository root:

    uv run python .agent/decisions/m3u4-test-surgery.py

Credit the script by replaying it onto a pristine checkout of the pre-surgery commit and
diffing the result against the shipped tree, which must be empty. `tests/` is untouched by
M3.4 at the contract commit 30195e7, apart from the new instrument file the surgery never
edits:

    git archive 30195e7 tests | tar -x -C <dir>
    uv run python .agent/decisions/m3u4-test-surgery.py --root <dir>
    diff -rq -x __pycache__ -x test_proposal_binding.py <dir>/tests tests
"""

from __future__ import annotations

import sys
from pathlib import Path

EDITS: list[tuple[str, str, str, int]] = [
    # (path, old, new, expected occurrences of old in the pristine file)
    (
        "tests/test_cli.py",
        '_PENDING_KEYS = {"input_hash", "operation_revision", "proposal_id", "request_id"}',
        '_PENDING_KEYS = {"input_hash", "operation_revision", "proposal_id"}',
        1,
    ),
    (
        "tests/test_cli.py",
        '            self.assertEqual(reviewed["source"], "confirmed")',
        '            self.assertEqual(reviewed["status"], "accepted")',
        1,
    ),
    (
        "tests/test_cli.py",
        """        self.assertEqual(
            sorted(
                proposal["request_id"]
                for proposal in whole["pending_proposals"]
            ),
            ["pending-0", "pending-1", "pending-2"],
        )""",
        """        pending_ids = sorted(
            str(proposal["proposal_id"]) for proposal in whole["pending_proposals"]
        )
        self.assertEqual(len(pending_ids), 3)
        self.assertEqual(len(set(pending_ids)), 3)
        for pending_id in pending_ids:
            self.assertTrue(pending_id.startswith("prop_"))""",
        1,
    ),
    (
        "tests/test_system.py",
        """                ("proposal_id", "request_id", "operation_revision", "input_hash"),
                {
                    "proposal_id": str,
                    "request_id": str,
                    "operation_revision": int,
                    "input_hash": str,""",
        """                ("proposal_id", "operation_revision", "input_hash"),
                {
                    "proposal_id": str,
                    "operation_revision": int,
                    "input_hash": str,""",
        1,
    ),
    (
        "tests/test_system.py",
        """        self.assertEqual(
            {item.proposal_id: item.request_id for item in gaps},
            {item.proposal_id: request_id for item, request_id in zip(
                target,
                ("shared_request", "target_middle", "target_last", "target_current"),
                strict=True,
            )},
        )""",
        """        # The gap no longer carries request identity, so the surviving projected
        # fields are what bind a gap to its proposal.
        for item in gaps:
            self.assertRegex(item.input_hash, r"\\A[0-9a-f]{64}\\Z")
            self.assertGreaterEqual(item.operation_revision, 1)""",
        1,
    ),
    (
        "tests/test_system.py",
        """        self.assertEqual(
            {
                gap.proposal_id: gap.request_id
                for gap in report.operation_now.pending_proposals
            },
            {
                pending.proposal_id: request_id
                for request_id, pending in pending_by_request.items()
            },
        )""",
        """        self.assertEqual(
            {gap.proposal_id for gap in report.operation_now.pending_proposals},
            {pending.proposal_id for pending in pending_by_request.values()},
        )
        for gap in report.operation_now.pending_proposals:
            self.assertRegex(gap.input_hash, r"\\A[0-9a-f]{64}\\Z")""",
        1,
    ),
    (
        "tests/test_submission_battery.py",
        """        self.assertTrue(view.request_id.startswith("req_"))
        self.assertNotEqual(proposal_id, domain_candidate.output["proposal_id"])
        self.assertNotEqual(view.request_id, domain_input["request_id"])""",
        """        self.assertNotIn("request_id", view.__dataclass_fields__)
        self.assertNotEqual(proposal_id, domain_candidate.output["proposal_id"])
        # The domain's own request_id key survives inside the stored input verbatim; only
        # Cement's request identity left the public shape.
        self.assertEqual(view.input["request_id"], domain_input["request_id"])""",
        1,
    ),
    (
        "tests/test_submission_battery.py",
        """        self.assertEqual(system.get_proposal(PARTITION, proposal_id).request_id, request.request_id)""",
        """        self.assertEqual(system.get_proposal(PARTITION, proposal_id).input, caller_input)""",
        1,
    ),
    (
        "tests/test_submission_battery.py",
        """        exposed = {
            "CandidateRequest": source_request.request_id,
            "handle": system.handle(
                PARTITION,
                OPERATION,
                INPUT,
                request_id=request_id,
            ).request_id,
            "request_status": system.request_status(PARTITION, request_id).request_id,
            "get_proposal": system.get_proposal(PARTITION, proposal_id).request_id,
            "proposal": system.proposal(PARTITION, proposal_id)["request_id"],
            "proposals": system.proposals(PARTITION)[0]["request_id"],
            "function_report": gap.request_id,
            "review": system.review(
                PARTITION,
                proposal_id,
                reviewer="reviewer_23",
                decision="reject",
                note="rejected_23",
            ).request_id,
        }

        self.assertEqual(len(exposed), 8)
        self.assertEqual(set(exposed.values()), {request_id})
        self.assertEqual(len(source.calls), 1)""",
        """        # M3.4 split this seam census in two. The handle lifecycle still carries the
        # caller's own request identity; the proposal, review and report seams no longer
        # expose any. Both halves are asserted, so readmitting one member to the wrong
        # half fails here.
        exposed = {
            "CandidateRequest": source_request.request_id,
            "handle": system.handle(
                PARTITION,
                OPERATION,
                INPUT,
                request_id=request_id,
            ).request_id,
            "request_status": system.request_status(PARTITION, request_id).request_id,
        }
        view = system.get_proposal(PARTITION, proposal_id)
        record = system.proposal(PARTITION, proposal_id)
        feed = system.proposals(PARTITION)[0]
        result = system.review(
            PARTITION,
            proposal_id,
            reviewer="reviewer_23",
            decision="reject",
            note="rejected_23",
        )

        self.assertEqual(len(exposed), 3)
        self.assertEqual(set(exposed.values()), {request_id})
        self.assertNotIn("request_id", view.__dataclass_fields__)
        self.assertNotIn("request_id", record)
        self.assertNotIn("request_id", feed)
        self.assertNotIn("request_id", gap.__dataclass_fields__)
        self.assertNotIn("request_id", result.__dataclass_fields__)
        self.assertEqual(result.proposal_id, proposal_id)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(len(source.calls), 1)""",
        1,
    ),
    # `review` now returns `ReviewResult`, whose `status` mirrors the reviewed proposal's
    # own status. The CLI serialises the dataclass, so its payload loses `source` and its
    # `status` reads "accepted" where the `Resolved` handle read "confirmed"/"resolved".
    (
        "tests/test_cli.py",
        """                )["source"],
                "confirmed",""",
        """                )["status"],
                "accepted",""",
        1,
    ),
    (
        "tests/test_cli.py",
        '            self.assertEqual(resolved["source"], "confirmed")',
        '            self.assertEqual(resolved["status"], "accepted")',
        1,
    ),
    # Documentation pins. The request row survives as storage, so every prose assertion
    # that promised a READER must now assert the storage wording instead.
    (
        "tests/test_submission_battery.py",
        '                self.assertIn("reader", paragraph)',
        '                self.assertIn("internal storage", paragraph)',
        1,
    ),
    (
        "tests/test_submission_battery.py",
        '        self.assertIn("existing request and proposal readers still show that identifier", readme)',
        """        self.assertIn(
            "no proposal, review, or report value shows it", readme
        )""",
        1,
    ),
    (
        "tests/test_submission_battery.py",
        '                "schema v2 keeps it for the existing readers",',
        '                "schema v2 keeps it as internal storage",',
        1,
    ),
    (
        "tests/test_submission_battery.py",
        '        self.assertIn("existing request and proposal readers still show that identifier", combined)',
        '        self.assertIn("no proposal, review, or report value shows it", combined)',
        1,
    ),
    # `PendingProposalGap` dropped `request_id`, so every literal comparison sheds it. The
    # two `prop_tail_00000` gaps differ only by nesting depth, so each anchor carries its
    # own indentation and both assert exactly one occurrence.
    (
        "tests/test_system.py",
        """                    proposal_id=pending.proposal_id,
                    request_id="function-report-pending",
                    operation_revision=1,""",
        """                    proposal_id=pending.proposal_id,
                    operation_revision=1,""",
        1,
    ),
    (
        "tests/test_system.py",
        """                    proposal_id="prop_tail_00000",
                    request_id="req_tail_00000",
                    operation_revision=1,""",
        """                    proposal_id="prop_tail_00000",
                    operation_revision=1,""",
        1,
    ),
    (
        "tests/test_system.py",
        """                proposal_id="prop_tail_00000",
                request_id="req_tail_00000",
                operation_revision=1,""",
        """                proposal_id="prop_tail_00000",
                operation_revision=1,""",
        1,
    ),
    (
        "tests/test_system.py",
        """                proposal_id="prop_tail_09999",
                request_id="req_tail_09999",
                operation_revision=1,""",
        """                proposal_id="prop_tail_09999",
                operation_revision=1,""",
        1,
    ),
    # Two tests whose subject is elsewhere still type-asserted `review`'s return.
    (
        "tests/test_system.py",
        """    ReviewRequired,
    StaleRevisionAnomaly,""",
        """    ReviewRequired,
    ReviewResult,
    StaleRevisionAnomaly,""",
        1,
    ),
    (
        "tests/test_system.py",
        """        self.assertIsInstance(resolved, Resolved)
        assert isinstance(resolved, Resolved)
        added = resolved.example_id""",
        """        self.assertIsInstance(resolved, ReviewResult)
        assert isinstance(resolved, ReviewResult)
        added = resolved.example_id""",
        1,
    ),
    (
        "tests/test_system.py",
        """            self.assertIsInstance(resolved, Resolved)
            assert isinstance(resolved, Resolved)
            self.assertIsNotNone(resolved.example_id)""",
        """            self.assertIsInstance(resolved, ReviewResult)
            assert isinstance(resolved, ReviewResult)
            self.assertIsNotNone(resolved.example_id)""",
        1,
    ),
]


def main(argv: list[str]) -> int:
    # ``--root`` replays the wave against a pristine checkout, so the script is credited by
    # reproducing the shipped tree byte-for-byte rather than by its own success message.
    root = Path(__file__).resolve().parents[2]
    if len(argv) == 3 and argv[1] == "--root":
        root = Path(argv[2]).resolve()
    elif len(argv) != 1:
        print(__doc__)
        return 2
    applied = 0
    for relative, old, new, expected in EDITS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if new in text and old not in text:
            print(f"no-op   {relative}: {old.strip().splitlines()[0][:60]}")
            continue
        count = text.count(old)
        if count != expected:
            print(
                f"ABORT   {relative}: anchor occurs {count} times, expected {expected}\n"
                f"        {old.strip().splitlines()[0][:100]}"
            )
            return 1
        path.write_text(text.replace(old, new), encoding="utf-8")
        applied += 1
        print(f"applied {relative}: {old.strip().splitlines()[0][:60]}")
    print(f"APPLIED: {applied} of {len(EDITS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
