#!/usr/bin/env python
"""M3.6a1 migration surgery: move every consumer off `handle` onto `propose`.

Usage:
    uv run python .agent/decisions/m3u6a1-surgery.py            # apply
    uv run python .agent/decisions/m3u6a1-surgery.py --check    # report only

Exit 0 = applied or no-op. Exit 1 = an assertion about the tree failed.

D15 requires ONE idempotent script that asserts the expected occurrence count of
every anchor before applying it and prints `no-op` on a second run. D17 requires
multi-line anchors wherever a fragment repeats.

Four rule families, and the split is deliberate.

`SITES` drives the `handle` -> `propose` rewrite through the AST, never through
text: 28 call sites across the 25 test-tree definitions the census rules
MIGRATE. An AST rule addresses the call by NODE, so the occurrence-index trap
D17 guards against cannot arise: there is nothing to count because nothing is
matched by text. What replaces the count assertion is stronger -- each site
asserts that the enclosing function's remaining references to the bound name are
plain loads, so a site consuming anything beyond `.proposal_id` ABORTS instead of
migrating silently.

`PARAMS` drops a positional parameter from a fixture helper and the matching
argument from every call, also through the AST, with the call count asserted
against the contract's own table (section 1). `self.confirm(...)` and a bare
`confirm(...)` are two different functions in one file (D14a), so the rule
carries the qualifier and a bare anchor is never used.

`TEXT` carries every edit that is not a rename, each with an exact expected
occurrence count: the sites where the call's `request_id` ARGUMENT was a durable
ledger key the test controlled, the demo's act restructure (D18-D21), the
example README prose the reframed Act 5 falsifies, and the consequential repairs
in tests the migration reaches only through a shared fixture or a scope pin.
`run()` refuses any rule whose replacement contains its own anchor, because such
a rule re-applies on every run and reports `applied` where it owes `no-op`.

The README transcript is a family of its own, and it is GENERATED, not anchored:
D22 pins the block to the demo's own output, so the script RUNS the migrated
demo, asserts one match per dynamic mask, and rewrites the fenced block. It runs
last, and under `--check` only when no source file is still pending, because a
pending demo would pin the pre-migration output.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import io
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "examples" / "hospital_ocr"
TRANSCRIPT = "examples/hospital_ocr/README.md"

# D22's two dynamic values, with the occurrence count each must keep. The demo
# mints a fresh layout-A artifact id and a fresh function hash per run, and
# `DemoTranscriptTests` asserts exactly one match per mask, so an extra or
# missing dynamic token has to fail here rather than mask away silently.
MASKS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r"[0-9a-f]{64}"), "<function-hash>", 1),
    (re.compile(r"art_[0-9a-f]{32}"), "art_<hex>", 1),
)

# ---------------------------------------------------------------- rule tables

# (path, qualified function name, ordinal of the `handle` call inside it, prelude)
#
# Addressed by NAME and ordinal, never by line. A line-keyed table cannot be
# idempotent, because the first pass moves every line below its own first edit,
# so the second pass reads a stale address and D15's `no-op` is unreachable. The
# dotted name also separates `SystemTests.confirm` from the nested
# `...reaches_every_compiler_block_reason_through_public_apis.confirm` that
# shadows it, which D14a requires and a bare anchor cannot do.
#
# The four `resolve` sites are the MISS-GUARDED shapes of contract section 3:
# every execution sees a once-promoted artifact for this exact input that still
# declines to answer. `propose` cannot state that; `resolve` measures
# `passed=True match=False` at all four, so the assertion migrates into the
# surviving vocabulary (D06) and the `propose` call is retained beside it (D07).
SITES: tuple[tuple[str, str, int, bool], ...] = (
    ("tests/test_cli.py", "CLITests.test_function_inspect_emits_the_tail_beyond_one_hundred_entries", 0, False),
    ("tests/test_hospital_ocr_example.py", "_promoted_example_ledger", 0, False),
    ("tests/test_proposal_binding_battery.py", "ProposalBindingBatteryTests._promoted_conflict_fixture", 0, False),
    ("tests/test_resolve_battery.py", "ResolveBatteryTests._confirm", 0, False),
    ("tests/test_system.py", "SystemTests.confirm", 0, False),
    ("tests/test_system.py", "SystemTests.test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence", 0, False),
    ("tests/test_system.py", "SystemTests.test_proposal_content_hashes_fail_closed_on_storage_mutation", 0, False),
    ("tests/test_system.py", "SystemTests.test_proposal_paths_translate_malformed_persisted_json", 0, False),
    ("tests/test_system.py", "SystemTests.test_orphaned_binding_fails_closed_and_stays_distinct_from_an_absent_proposal", 0, False),
    ("tests/test_system.py", "SystemTests.test_counterexample_and_revocation_quarantine", 0, True),
    ("tests/test_system.py", "SystemTests.test_counterexample_and_revocation_quarantine", 1, False),
    ("tests/test_system.py", "SystemTests.test_late_review_counterexample_quarantines_promoted_scope", 0, False),
    ("tests/test_system.py", "SystemTests.test_late_review_counterexample_quarantines_promoted_scope", 1, True),
    ("tests/test_system.py", "SystemTests.test_monotonic_feeds_survive_transitions_and_clock_rollback", 0, False),
    ("tests/test_system.py", "SystemTests.test_monotonic_feeds_survive_transitions_and_clock_rollback", 1, False),
    ("tests/test_system.py", "SystemTests.test_receipt_can_bind_individually_valid_large_input_and_output", 0, False),
    ("tests/test_system.py", "SystemTests.test_runtime_integrity_failure_quarantines_then_falls_back", 0, True),
    ("tests/test_system.py", "SystemTests.test_operation_revision_retires_old_artifacts", 0, True),
    ("tests/test_system.py", "SystemTests.test_artifact_evidence_edges_are_database_immutable", 0, False),
    ("tests/test_system.py", "SystemTests.test_review_rejects_cross_table_state_corruption", 0, False),
    ("tests/test_system.py", "SystemTests._confirm_scope", 0, False),
    ("tests/test_system.py", "SystemTests.test_verify_drafts_requalifies_older_build_after_revocation", 0, False),
    ("tests/test_system.py", "SystemTests.test_function_report_projects_both_anchors_with_exact_counts_and_ordering", 0, False),
    ("tests/test_system.py", "SystemTests.test_function_report_reaches_every_compiler_block_reason_through_public_apis.confirm", 0, False),
    ("tests/test_system.py", "SystemTests.test_function_report_is_one_read_only_snapshot_with_exact_limit_materialization", 0, False),
    ("tests/test_system.py", "SystemTests.test_function_report_pending_projection_validates_middle_and_last_but_not_tail", 0, False),
    ("tests/test_system.py", "SystemTests.test_function_report_pending_rows_validate_middle_and_last_scalars_and_bindings", 0, False),
    ("tests/test_system.py", "SystemTests.test_function_report_pending_request_join_is_like_and_case_exact", 0, False),
)

# (path, function name, qualifier, parameter, expected call count)
#
# Qualifier `self` matches `self.<name>(...)`; `bare` matches `<name>(...)`.
# `_promote_scope` loses `prefix` under D12: it exists only to build the two
# request identifiers `_confirm_scope` no longer takes, so a retained `prefix`
# is exactly the dead-parameter residue D14 forbids.
PARAMS: tuple[tuple[str, str, str, str, int], ...] = (
    ("tests/test_system.py", "confirm", "self", "request_id", 41),
    ("tests/test_system.py", "confirm", "bare", "request_id", 11),
    ("tests/test_system.py", "_confirm_scope", "self", "request_id", 65),
    ("tests/test_system.py", "_promote_scope", "self", "prefix", 14),
    ("tests/test_resolve_battery.py", "_confirm", "self", "prefix", 1),
)

_ORPHAN_SQL = '''            connection.execute(
                "DELETE FROM requests WHERE id = "
                "(SELECT request_id FROM proposals WHERE id = ?)",
                (pending,),
            )
'''

_COLLIDER = '''            proposal_id = self.system.propose(
                "tenant_a", "echo_1", {"pending-join": index}
            )
            pending_by_request[request_id] = proposal_id

        # `propose` mints its own request-row id, so the collider set this test
        # exists to exercise has to be planted after submission. Every minted id
        # is lowercase hex whose only `_` sits in the `req_` prefix, so without
        # this a `=` -> `LIKE` or a case-folding mutation on the
        # `r.id = p.request_id` join survives with the assertions below intact.
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA foreign_keys = OFF")
            for request_id, proposal_id in pending_by_request.items():
                connection.execute(
                    "UPDATE requests SET id = ? WHERE id = "
                    "(SELECT request_id FROM proposals WHERE id = ?)",
                    (request_id, proposal_id),
                )
                connection.execute(
                    "UPDATE proposals SET request_id = ? WHERE id = ?",
                    (request_id, proposal_id),
                )
            connection.commit()
        finally:
            connection.close()
'''

# (path, old, new, expected count). Multi-line wherever the fragment repeats.
TEXT: tuple[tuple[str, str, str, int], ...] = (
    # --- the request_id ARGUMENT was a durable ledger key -------------------
    # The census reads return values and the shape table reads artifact side
    # effects; neither sees that `request_id` is a caller-chosen PRIMARY KEY.
    # `propose` mints `req_<hex>` internally and never returns it, so each of
    # these recovers the row through the proposal that binds it.
    (
        "tests/test_system.py",
        '                "UPDATE requests SET input_json = ? WHERE id = ?",\n'
        '                ("{", "malformed-proposal-input"),\n',
        '                "UPDATE requests SET input_json = ? WHERE id = "\n'
        '                "(SELECT request_id FROM proposals WHERE id = ?)",\n'
        '                ("{", pending),\n',
        1,
    ),
    (
        "tests/test_system.py",
        '            connection.execute("DELETE FROM requests WHERE id = ?", ("orphan-me",))\n',
        _ORPHAN_SQL,
        1,
    ),
    (
        "tests/test_system.py",
        '                "UPDATE requests SET status = \'rejected\' WHERE partition = ? AND id = ?",\n'
        '                ("tenant-a", "cross-state"),\n',
        '                "UPDATE requests SET status = \'rejected\' WHERE partition = ? AND id = "\n'
        '                "(SELECT request_id FROM proposals WHERE id = ?)",\n'
        '                ("tenant-a", pending),\n',
        1,
    ),
    # The collider set IS this test's fixture: `pending_join_1` against
    # `pendingXjoinX1` under LIKE, `PendingCase` against `pendingcase` under
    # case folding. Re-planted rather than dropped, because dropping it unpins
    # the `=` and case-exactness property the test is named for.
    (
        "tests/test_system.py",
        '            pending = self.system.propose("tenant_a", "echo_1", {"pending-join": index})\n'
        "            pending_by_request[request_id] = pending\n",
        _COLLIDER,
        1,
    ),
    (
        "tests/test_system.py",
        "        pending_by_request: dict[str, ReviewRequired] = {}\n",
        "        pending_by_request: dict[str, str] = {}\n",
        1,
    ),
    (
        "tests/test_system.py",
        "            {gap.proposal_id for gap in report.operation_now.pending_proposals},\n"
        "            {pending for pending in pending_by_request.values()},\n",
        "            {gap.proposal_id for gap in report.operation_now.pending_proposals},\n"
        "            set(pending_by_request.values()),\n",
        1,
    ),
    # --- loop variables that existed only to build a request id -------------
    (
        "tests/test_system.py",
        '        for request_id in ("a", "b"):\n',
        "        for _ in range(2):\n",
        1,
    ),
    (
        "tests/test_proposal_binding_battery.py",
        '        for request_id in ("early-1", "early-2"):\n',
        "        for _ in range(2):\n",
        1,
    ),
    (
        "tests/test_hospital_ocr_example.py",
        "    for index, filename in enumerate(SEED_DOCUMENTS, start=1):\n",
        "    for filename in SEED_DOCUMENTS:\n",
        1,
    ),
    (
        "tests/test_resolve_battery.py",
        '        for index, reviewer in enumerate(("alice", "bob"), start=1):\n',
        '        for reviewer in ("alice", "bob"):\n',
        1,
    ),
    # --- RETAIN consumers of a MIGRATED fixture -----------------------------
    # `confirm` used to plant a caller-chosen request id; it no longer does.
    # D03 pins RETAIN on the test's OWN lifecycle call and says nothing about
    # its fixtures, so these three break with their own calls untouched. Each
    # recovers the row it consumes instead of naming an id nothing mints.
    (
        "tests/test_system.py",
        '        for request_id, corrupted in (\n'
        '            ("confirmed-cache-invalid", "{"),\n'
        '            ("confirmed-cache-mismatch", \'"tampered"\'),\n'
        "        ):\n"
        "            with self.subTest(request_id=request_id):\n"
        "                self.confirm()\n"
        "                connection = sqlite3.connect(self.database)\n"
        "                try:\n"
        "                    connection.execute(\n",
        '        for label, corrupted in (\n'
        '            ("confirmed-cache-invalid", "{"),\n'
        '            ("confirmed-cache-mismatch", \'"tampered"\'),\n'
        "        ):\n"
        "            with self.subTest(request_id=label):\n"
        "                confirmed = self.confirm()\n"
        "                connection = sqlite3.connect(self.database)\n"
        "                try:\n"
        "                    (request_id,) = connection.execute(\n"
        '                        "SELECT request_id FROM proposals WHERE id = ?",\n'
        "                        (confirmed.proposal_id,),\n"
        "                    ).fetchone()\n"
        "                    connection.execute(\n",
        1,
    ),
    # A zero-row UPDATE raises nothing, so the CHECK this test is named for
    # would pass vacuously the moment its row stopped existing -- which is
    # exactly what the fixture migration did. The count assertion is the
    # positive control that makes the failure loud instead of silent.
    (
        "tests/test_system.py",
        "        self.confirm()\n"
        "        connection = sqlite3.connect(self.database)\n"
        "        try:\n"
        "            with self.assertRaises(sqlite3.IntegrityError):\n"
        "                connection.execute(\n"
        '                    """\n'
        "                    UPDATE requests SET source_kind = 'mystery', output_json = '\"tampered\"'\n"
        "                    WHERE partition = ? AND id = ?\n"
        '                    """,\n'
        '                    ("tenant-a", "source-kind"),\n'
        "                )\n",
        "        confirmed = self.confirm()\n"
        "        connection = sqlite3.connect(self.database)\n"
        "        try:\n"
        "            (planted,) = connection.execute(\n"
        '                "SELECT count(*) FROM requests WHERE partition = ? AND id = "\n'
        '                "(SELECT request_id FROM proposals WHERE id = ?)",\n'
        '                ("tenant-a", confirmed.proposal_id),\n'
        "            ).fetchone()\n"
        "            self.assertEqual(planted, 1)\n"
        "            with self.assertRaises(sqlite3.IntegrityError):\n"
        "                connection.execute(\n"
        '                    """\n'
        "                    UPDATE requests SET source_kind = 'mystery', output_json = '\"tampered\"'\n"
        "                    WHERE partition = ? AND id = (\n"
        "                        SELECT request_id FROM proposals WHERE id = ?\n"
        "                    )\n"
        '                    """,\n'
        '                    ("tenant-a", confirmed.proposal_id),\n'
        "                )\n",
        1,
    ),
    # This one replays `old-confirmed` through `handle` and counts source calls,
    # so a missing row is a silent extra candidate call rather than an error.
    # It is RETAIN and already the file's heaviest `handle` consumer, so it
    # plants its own confirmed request rather than borrowing the fixture's.
    (
        "tests/test_system.py",
        "    def test_operation_revision_invalidates_every_old_request_path(self) -> None:\n"
        "        self.register(confirmations=2, reviewers=1, span=0)\n"
        "        self.confirm()\n"
        "        pending = self.system.handle(\n",
        "    def test_operation_revision_invalidates_every_old_request_path(self) -> None:\n"
        "        self.register(confirmations=2, reviewers=1, span=0)\n"
        "        confirmed = self.system.handle(\n"
        '            "tenant-a", "echo", {"x": 1}, request_id="old-confirmed"\n'
        "        )\n"
        "        self.system.review(\n"
        '            "tenant-a", confirmed.proposal_id, reviewer="alice", decision="accept"\n'
        "        )\n"
        "        pending = self.system.handle(\n",
        1,
    ),
    # --- a claim the rename would have made vacuous -------------------------
    # `propose` returns a bare identifier, so `hasattr` on a `str` is trivially
    # false. The claim survives only if the returned TYPE is pinned beside it.
    (
        "tests/test_system.py",
        '        pending = self.system.propose("tenant-a", "echo", {"x": 1})\n'
        '        self.assertFalse(hasattr(pending, "proposed_output"))\n',
        '        pending = self.system.propose("tenant-a", "echo", {"x": 1})\n'
        "        self.assertIsInstance(pending, str)\n"
        '        self.assertFalse(hasattr(pending, "proposed_output"))\n',
        1,
    ),
    # --- the demo: five sites onto `propose`, two onto `resolve` (D18) -------
    # The checkpoint MOVES rather than the assertion weakening (D19): P2
    # measures `resolve` failing `persisted-function-receipt` at the Act-2
    # ledger state and matching once the set is promoted, so the walkthrough
    # promotes its set right after each artifact promotion. Act 5 keeps export
    # and identity and loses the "becomes one exportable function" framing,
    # because by then the set has already answered twice (D20).
    (
        "examples/hospital_ocr/run_demo.py",
        "The closing acts seal every promoted layout into one verified function and then\n"
        "resolve a document from those exported bytes after the ledger is deleted.\n",
        "Each artifact promotion is sealed into the verified function set immediately, so\n"
        "the next document of a known layout resolves from that set. The closing act\n"
        "answers one document from the exported bytes alone, after the ledger is deleted.\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "    FunctionMatch,\n    Resolved,\n    ReviewRequired,\n    System,\n",
        "    FunctionMatch,\n    System,\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        outcome_a_01 = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            a_signature_01,\n"
        '            request_id="a-note-01",\n'
        "        )\n"
        "        assert isinstance(outcome_a_01, ReviewRequired)\n"
        '        print("A01: adapter proposed a plan; records-supervisor review is required.")\n'
        "        system.review(\n"
        "            PARTITION,\n"
        "            outcome_a_01.proposal_id,\n",
        "        proposal_a_01 = system.propose(PARTITION, OPERATION, a_signature_01)\n"
        '        print("A01: adapter proposed a plan; records-supervisor review is required.")\n'
        "        system.review(\n"
        "            PARTITION,\n"
        "            proposal_a_01,\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        outcome_a_02 = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            a_signature_02,\n"
        '            request_id="a-note-02",\n'
        "        )\n"
        "        assert isinstance(outcome_a_02, ReviewRequired)\n"
        '        print("A02: the same layout recurred; its plan again requires supervision.")\n'
        "        system.review(\n"
        "            PARTITION,\n"
        "            outcome_a_02.proposal_id,\n",
        "        proposal_a_02 = system.propose(PARTITION, OPERATION, a_signature_02)\n"
        '        print("A02: the same layout recurred; its plan again requires supervision.")\n'
        "        system.review(\n"
        "            PARTITION,\n"
        "            proposal_a_02,\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        print(\n"
        '            f"Layout A: compiled, verified ({report_a.tests} tests), and promoted "\n'
        '            f"as {artifact_a}."\n'
        "        )\n"
        "\n"
        '        print("\\n=== Act 2: known layout A resolves without the adapter ===")\n'
        "        calls_before = source.calls\n"
        "        resolved_a = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            a_signature_03,\n"
        '            request_id="a-note-03",\n'
        "        )\n"
        "        assert isinstance(resolved_a, Resolved)\n"
        '        assert resolved_a.source == "artifact"\n'
        "        assert source.calls == calls_before\n"
        "        extracted_a = pipeline.apply_plan(resolved_a.output, a_text_03)\n",
        "        print(\n"
        '            f"Layout A: compiled, verified ({report_a.tests} tests), and promoted "\n'
        '            f"as {artifact_a}."\n'
        "        )\n"
        "        function = checkpoint_function(system)\n"
        "        print(\n"
        '            f"Function set: {len(function.input_hashes)} verified entry promoted; "\n'
        '            "layout A now answers from the set."\n'
        "        )\n"
        "\n"
        '        print("\\n=== Act 2: known layout A resolves without the adapter ===")\n'
        "        calls_before = source.calls\n"
        "        resolution_a = system.resolve(PARTITION, OPERATION, a_signature_03)\n"
        "        assert resolution_a.verification.passed\n"
        "        assert resolution_a.match is not None\n"
        "        assert resolution_a.match.matched\n"
        "        assert source.calls == calls_before\n"
        "        extracted_a = pipeline.apply_plan(resolution_a.match.output, a_text_03)\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        '        print("A03: promoted artifact returned the confirmed plan; adapter calls stayed flat.")\n',
        '        print("A03: the verified set returned the confirmed plan; adapter calls stayed flat.")\n',
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        outcome_b_01 = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            b_signature_01,\n"
        '            request_id="b-intake-01",\n'
        "        )\n"
        "        assert isinstance(outcome_b_01, ReviewRequired)\n"
        "        system.review(\n"
        "            PARTITION,\n"
        "            outcome_b_01.proposal_id,\n",
        "        proposal_b_01 = system.propose(PARTITION, OPERATION, b_signature_01)\n"
        "        system.review(\n"
        "            PARTITION,\n"
        "            proposal_b_01,\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        outcome_b_02 = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            b_signature_02,\n"
        '            request_id="b-intake-02",\n'
        "        )\n"
        "        assert isinstance(outcome_b_02, ReviewRequired)\n"
        "        system.review(\n"
        "            PARTITION,\n"
        "            outcome_b_02.proposal_id,\n",
        "        proposal_b_02 = system.propose(PARTITION, OPERATION, b_signature_02)\n"
        "        system.review(\n"
        "            PARTITION,\n"
        "            proposal_b_02,\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        system.promote(\n"
        "            PARTITION,\n"
        "            artifact_b,\n"
        "            scope_hash=report_b.scope_hash,\n"
        '            promoted_by="informatics-lead",\n'
        "        )\n"
        "\n"
        "        calls_before = source.calls\n"
        "        resolved_b = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            b_signature_01,\n"
        '            request_id="b-intake-recur",\n'
        "        )\n"
        "        assert isinstance(resolved_b, Resolved)\n"
        '        assert resolved_b.source == "artifact"\n'
        "        assert source.calls == calls_before\n"
        "        extracted_b = pipeline.apply_plan(resolved_b.output, b_text_01)\n",
        "        system.promote(\n"
        "            PARTITION,\n"
        "            artifact_b,\n"
        "            scope_hash=report_b.scope_hash,\n"
        '            promoted_by="informatics-lead",\n'
        "        )\n"
        "        function = checkpoint_function(system)\n"
        "        print(\n"
        '            f"Function set: {len(function.input_hashes)} verified entries, one per "\n'
        '            "promoted layout."\n'
        "        )\n"
        "\n"
        "        calls_before = source.calls\n"
        "        resolution_b = system.resolve(PARTITION, OPERATION, b_signature_01)\n"
        "        assert resolution_b.verification.passed\n"
        "        assert resolution_b.match is not None\n"
        "        assert resolution_b.match.matched\n"
        "        assert source.calls == calls_before\n"
        "        extracted_b = pipeline.apply_plan(resolution_b.match.output, b_text_01)\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        "        outcome_c_01 = system.handle(\n"
        "            PARTITION,\n"
        "            OPERATION,\n"
        "            c_signature_01,\n"
        '            request_id="c-lab-01",\n'
        "        )\n"
        "        assert isinstance(outcome_c_01, ReviewRequired)\n"
        "        system.review(\n"
        "            PARTITION,\n"
        "            outcome_c_01.proposal_id,\n",
        "        proposal_c_01 = system.propose(PARTITION, OPERATION, c_signature_01)\n"
        "        system.review(\n"
        "            PARTITION,\n"
        "            proposal_c_01,\n",
        1,
    ),
    (
        "examples/hospital_ocr/run_demo.py",
        '        print("\\n=== Act 5: both promoted layouts become one exportable function ===")\n'
        "        function = checkpoint_function(system)\n"
        "        bundle_text = function.text\n"
        "        print(\n"
        '            f"Function checkpoint: {len(function.input_hashes)} verified entries, "\n'
        '            "one per promoted layout."\n'
        "        )\n",
        '        print("\\n=== Act 5: the verified set exports as portable bytes ===")\n'
        "        bundle_text = function.text\n"
        "        print(\n"
        '            f"Exported set: {len(function.input_hashes)} verified entries, promoted "\n'
        '            "before Acts 2 and 3 resolved against them."\n'
        "        )\n",
        1,
    ),
    # --- example README prose the reframed Act 5 falsifies -------------------
    # The transcript block regenerates from the demo's own output; these are the
    # surrounding sentences no regeneration reaches.
    (
        TRANSCRIPT,
        "The demo finally seals every promoted layout into one portable function and "
        "answers a document after the ledger is gone.",
        "The demo seals each promoted layout into one portable function as it is "
        "promoted. It then answers a document after the ledger is gone.",
        1,
    ),
    (
        TRANSCRIPT,
        "ocr(path) -> layout_signature(ocr_text) -> System.handle(...)\n"
        "  promoted exact signature -> confirmed plan\n"
        "  miss -> PlanProposer.propose(...) -> supervisor review\n",
        "ocr(path) -> layout_signature(ocr_text) -> System.resolve(...)\n"
        "  promoted exact signature -> confirmed plan\n"
        "  miss -> System.propose(...) -> PlanProposer.propose(...) -> supervisor review\n",
        1,
    ),
    (
        TRANSCRIPT,
        "3. `System.handle(...)` either returns the promoted exact-scope plan or asks "
        "`PlanProposer.propose(...)` for a supervised candidate.",
        "3. `System.resolve(...)` returns the promoted exact-scope plan. On a miss, "
        "`System.propose(...)` asks `PlanProposer.propose(...)` for a supervised candidate.",
        1,
    ),
    (
        TRANSCRIPT,
        "function and returns the exportable bundle.\n6. `resolve_offline(",
        "function and returns the exportable bundle. The demo calls it after each "
        "artifact promotion, so the next document of a known layout resolves from the "
        "set.\n6. `resolve_offline(",
        1,
    ),
    (
        TRANSCRIPT,
        "`run_demo.py` drives review, compilation, verification, promotion, exact "
        "resolution, extraction, and audit output. It then checkpoints the promoted set, "
        "deletes the ledger, and answers one more document from the exported bytes.",
        "`run_demo.py` drives proposal, review, compilation, verification, artifact "
        "promotion, set promotion, exact resolution, extraction, and audit output. It "
        "then deletes the ledger and answers one more document from the exported bytes.",
        1,
    ),
    (
        TRANSCRIPT,
        "then deterministic compilation, verification, and explicit promotion. Act 2 sends",
        "then deterministic compilation, verification, and explicit promotion of the "
        "artifact and of the verified set. Act 2 sends",
        1,
    ),
    (
        TRANSCRIPT,
        "Act 5 seals both promoted layouts into one verified function and prints its "
        "hash and byte count.",
        "Act 5 exports the verified set and prints its hash and byte count.",
        1,
    ),
    (
        TRANSCRIPT,
        "Act 5 seals both promoted layouts into one self-verifying bundle.",
        "Act 5 exports the promoted set as one self-verifying bundle.",
        1,
    ),
    # --- consequences the contract did not number ---------------------------
    # The demo now verifies its set four times: the checkpoint after each
    # artifact promotion, plus the `resolve` in Acts 2 and 3, which verifies the
    # whole set per call. The count pinned the identity of "the document" Act 6
    # carries, so it is RE-DERIVED, and the one-entry-versus-two-entry
    # inequality is added because it is what proves the checkpoint moved.
    (
        "tests/test_hospital_ocr_example.py",
        "        self.assertEqual(len(verifications), 1)\n"
        "        document = verifications[0].document\n"
        "        self.assertIsNotNone(document)\n"
        "        self.assertEqual(\n"
        "            calls, [(document.text, False), (document.text, False)]\n"
        "        )\n",
        "        self.assertEqual(len(verifications), 4)\n"
        "        documents = [record.document for record in verifications]\n"
        "        self.assertNotIn(None, documents)\n"
        "        # Act 1 checkpoints a one-entry set and Act 3 a two-entry set, so the\n"
        "        # first document differs from the last. Act 4 promotes nothing, which\n"
        "        # is why every verification from the second promotion on sees one set.\n"
        "        self.assertNotEqual(documents[0].text, documents[-1].text)\n"
        "        self.assertEqual({record.text for record in documents[2:]}, {documents[-1].text})\n"
        "        document = documents[-1]\n"
        "        self.assertEqual(\n"
        "            calls, [(document.text, False), (document.text, False)]\n"
        "        )\n",
        1,
    ),
    # M3.5b's D15b and D22b pinned "this unit touched no file under `examples/`"
    # and "this unit pre-empted no M3.6a doc work" -- both claims about M3.5b's
    # OWN DIFF -- by comparing the WORKING TREE against the pre-unit baseline.
    # That reading is an over-claim that holds only until a later unit
    # legitimately enters the scope, and D18-D23 are that unit. Re-scoped to
    # M3.5b's own range, `36f7890` -> `1146421`, which is what each obligation
    # actually asserts and stays true for every unit after this one.
    (
        "tests/test_cli_removal_battery.py",
        '                ["git", "ls-files", "--", "examples"],\n',
        '                ["git", "ls-tree", "-r", "--name-only", "1146421", "--", "examples"],\n',
        1,
    ),
    (
        "tests/test_cli_removal_battery.py",
        "        self.assertEqual(tracked, baseline)\n"
        "        self.assertEqual(len(baseline), 12)\n"
        "        for relative in sorted(baseline):\n"
        "            with self.subTest(relative=relative):\n"
        '                self.assertEqual((ROOT / relative).read_bytes(), _git_bytes("36f7890", relative))\n',
        "        self.assertEqual(tracked, baseline)\n"
        "        self.assertEqual(len(baseline), 12)\n"
        "        for relative in sorted(baseline):\n"
        "            with self.subTest(relative=relative):\n"
        "                self.assertEqual(\n"
        '                    _git_bytes("1146421", relative), _git_bytes("36f7890", relative)\n'
        "                )\n",
        1,
    ),
    (
        "tests/test_cli_removal_battery.py",
        '        current_readme = (ROOT / "README.md").read_text()\n'
        '        baseline_readme = _git_bytes("36f7890", "README.md").decode()\n'
        '        current_architecture = (ROOT / "docs/architecture.md").read_text()\n'
        '        baseline_architecture = _git_bytes("36f7890", "docs/architecture.md").decode()\n'
        '        current_threat = (ROOT / "docs/threat-model.md").read_text()\n'
        '        baseline_threat = _git_bytes("36f7890", "docs/threat-model.md").decode()\n'
        '        current_hospital = (ROOT / "examples/hospital_ocr/README.md").read_text()\n'
        '        baseline_hospital = _git_bytes("36f7890", "examples/hospital_ocr/README.md").decode()\n',
        "        # `current_*` is M3.5b's CLOSING tree, never the working tree: the claim is\n"
        "        # that M3.5b's own diff left the library route alone, and M3.6a1's D18-D23\n"
        "        # rewrite the example walkthrough this unit was holding open for it.\n"
        '        current_readme = _git_bytes("1146421", "README.md").decode()\n'
        '        baseline_readme = _git_bytes("36f7890", "README.md").decode()\n'
        '        current_architecture = _git_bytes("1146421", "docs/architecture.md").decode()\n'
        '        baseline_architecture = _git_bytes("36f7890", "docs/architecture.md").decode()\n'
        '        current_threat = _git_bytes("1146421", "docs/threat-model.md").decode()\n'
        '        baseline_threat = _git_bytes("36f7890", "docs/threat-model.md").decode()\n'
        '        current_hospital = _git_bytes("1146421", "examples/hospital_ocr/README.md").decode()\n'
        '        baseline_hospital = _git_bytes("36f7890", "examples/hospital_ocr/README.md").decode()\n',
        1,
    ),
    (
        "tests/test_cli_removal_battery.py",
        "        self.assertEqual(\n"
        '            (ROOT / "docs/adapter-protocol.md").read_bytes(),\n'
        '            _git_bytes("36f7890", "docs/adapter-protocol.md"),\n'
        "        )\n",
        "        self.assertEqual(\n"
        '            _git_bytes("1146421", "docs/adapter-protocol.md"),\n'
        '            _git_bytes("36f7890", "docs/adapter-protocol.md"),\n'
        "        )\n",
        1,
    ),
    # D25 classifies the sentence opener of every CHANGED paragraph and treats an
    # unclassified opener as a failure, so rewriting one bullet of a list drags
    # its whole paragraph in. That is the obligation working as designed: the
    # openers below are classified rather than defaulted to the looser bound.
    (
        "tests/test_cli_removal_battery.py",
        "        imperatives = {\n"
        '            "call",\n'
        '            "capture",\n'
        '            "generate",\n'
        '            "inspect",\n',
        "        imperatives = {\n"
        '            "call",\n'
        '            "canonicalize",\n'
        '            "capture",\n'
        '            "export",\n'
        '            "generate",\n'
        '            "inspect",\n'
        '            "isolate",\n'
        '            "keep",\n',
        1,
    ),
    (
        "tests/test_cli_removal_battery.py",
        '            "submit",\n            "use",\n        }\n',
        '            "submit",\n            "treat",\n            "use",\n        }\n',
        1,
    ),
    (
        "tests/test_cli_removal_battery.py",
        "        descriptive = {\n"
        '            "a",\n'
        '            "caller",\n'
        '            "candidate",\n'
        '            "cement",\n'
        '            "compilation",\n'
        '            "confirmed",\n'
        '            "conflicts",\n'
        '            "counterexamples",\n'
        '            "current",\n'
        '            "every",\n'
        '            "fallbackfailed",\n'
        '            "for",\n'
        '            "if",\n'
        '            "inprogress",\n'
        '            "it",\n'
        '            "its",\n'
        '            "linux",\n'
        '            "llm",\n'
        '            "meaning",\n'
        '            "no",\n'
        '            "only",\n'
        '            "operation",\n'
        '            "promotion",\n',
        "        descriptive = {\n"
        '            "1",\n'
        '            "2",\n'
        '            "3",\n'
        '            "4",\n'
        '            "5",\n'
        '            "6",\n'
        '            "a",\n'
        '            "act",\n'
        '            "applyplan",\n'
        '            "caller",\n'
        '            "candidate",\n'
        '            "cement",\n'
        '            "cement-json-v1",\n'
        '            "checkpointfunction",\n'
        '            "compilation",\n'
        '            "confirmed",\n'
        '            "conflicts",\n'
        '            "counterexamples",\n'
        '            "current",\n'
        '            "distinct",\n'
        '            "every",\n'
        '            "fallbackfailed",\n'
        '            "for",\n'
        '            "hospital",\n'
        '            "if",\n'
        '            "inprogress",\n'
        '            "it",\n'
        '            "its",\n'
        '            "layout",\n'
        '            "layoutsignature",\n'
        '            "linux",\n'
        '            "llm",\n'
        '            "meaning",\n'
        '            "mercy-general",\n'
        '            "no",\n'
        '            "ocr",\n'
        '            "on",\n'
        '            "only",\n'
        '            "operation",\n'
        '            "patient",\n'
        '            "planadapter",\n'
        '            "production",\n'
        '            "promotion",\n'
        '            "resolveoffline",\n'
        '            "rundemo",\n',
        1,
    ),
    (
        "tests/test_cli_removal_battery.py",
        '            "status",\n'
        '            "supervised",\n'
        '            "system",\n'
        '            "that",\n',
        '            "status",\n'
        '            "structural",\n'
        '            "supervised",\n'
        '            "system",\n'
        '            "that",\n',
        1,
    ),
)


# ------------------------------------------------------------------ machinery


class Abort(Exception):
    """A stated fact about the tree is false. Never repair; report and stop."""


def _offsets(source: str) -> list[int]:
    starts, index = [0], 0
    for line in source.splitlines(keepends=True):
        index += len(line)
        starts.append(index)
    return starts


def _at(starts: list[int], line: int, column: int) -> int:
    return starts[line - 1] + column


def _span(starts: list[int], node: ast.AST) -> tuple[int, int]:
    assert node.end_lineno is not None and node.end_col_offset is not None
    return (
        _at(starts, node.lineno, node.col_offset),
        _at(starts, node.end_lineno, node.end_col_offset),
    )


def _statement_span(source: str, starts: list[int], node: ast.stmt) -> tuple[int, int]:
    """Whole physical lines, including indentation and the trailing newline."""
    start = starts[node.lineno - 1]
    assert node.end_lineno is not None
    end = starts[node.end_lineno]
    return start, end


def _qualified(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Dotted name -> definition, so a shadowing nested function is addressable."""
    found: dict[str, ast.FunctionDef] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                if isinstance(child, ast.FunctionDef):
                    if name in found:
                        raise Abort(f"two definitions share the qualified name `{name}`")
                    found[name] = child
                walk(child, name)
            else:
                walk(child, prefix)

    walk(tree, "")
    return found


def _is_guard(node: ast.stmt, target: str) -> bool:
    """`assertIsInstance(T, ReviewRequired)`, `assertIs(type(T), ...)`, `assert isinstance(T, ...)`."""
    if isinstance(node, ast.Assert):
        test = node.test
        return (
            isinstance(test, ast.Call)
            and isinstance(test.func, ast.Name)
            and test.func.id == "isinstance"
            and bool(test.args)
            and isinstance(test.args[0], ast.Name)
            and test.args[0].id == target
            and "ReviewRequired" in ast.unparse(test)
        )
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return False
    call = node.value
    if not (isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)):
        return False
    if call.func.value.id != "self" or "ReviewRequired" not in ast.unparse(call):
        return False
    if call.func.attr == "assertIsInstance":
        return bool(call.args) and isinstance(call.args[0], ast.Name) and call.args[0].id == target
    if call.func.attr == "assertIs":
        first = call.args[0] if call.args else None
        return (
            isinstance(first, ast.Call)
            and isinstance(first.func, ast.Name)
            and first.func.id == "type"
            and bool(first.args)
            and isinstance(first.args[0], ast.Name)
            and first.args[0].id == target
        )
    return False


def _proposal_id_base(node: ast.Attribute) -> str | None:
    """The name `X` in `X.proposal_id` or `typing.cast(T, X).proposal_id`."""
    if node.attr != "proposal_id":
        return None
    value = node.value
    if isinstance(value, ast.Name):
        return value.id
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "cast"
        and len(value.args) == 2
        and isinstance(value.args[1], ast.Name)
    ):
        return value.args[1].id
    return None


def _migrate_site(
    source: str,
    starts: list[int],
    functions: dict[str, ast.FunctionDef],
    qualname: str,
    ordinal: int,
    guarded: bool,
    expected: int,
) -> list[tuple[int, int, str]]:
    """Return edits turning one `handle` site into `propose`, or [] if already done."""
    owner = functions.get(qualname)
    if owner is None:
        raise Abort(f"no function named `{qualname}`")
    line = owner.lineno
    calls = sorted(
        (
            node
            for node in ast.walk(owner)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "handle"
        ),
        key=lambda node: (node.lineno, node.col_offset),
    )
    # Every listed function migrates ALL of its `handle` calls, so the count is
    # the count assertion D15 asks for and it doubles as the idempotence test:
    # zero left means this pass already ran.
    if not calls:
        return []
    if len(calls) != expected:
        raise Abort(f"{qualname}: {len(calls)} `handle` calls, table states {expected}")
    call = calls[ordinal]
    line = call.lineno

    assign = None
    for node in ast.walk(owner):
        if isinstance(node, ast.Assign) and node.value is call:
            assign = node
    if assign is None or len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
        raise Abort(f"{line}: `handle` result is not bound to one plain name")
    target = assign.targets[0].id

    if len(call.args) != 3:
        raise Abort(f"{line}: expected three positional arguments, found {len(call.args)}")
    receiver = ast.get_source_segment(source, call.func.value)
    arguments = [ast.get_source_segment(source, argument) for argument in call.args]
    if receiver is None or any(argument is None for argument in arguments):
        raise Abort(f"{line}: could not slice the call")

    indent = " " * (assign.col_offset)
    joined = ", ".join(str(argument) for argument in arguments)
    body = f"{indent}{target} = {receiver}.propose({joined})\n"
    if len(body) > 89:
        inner = indent + "    "
        body = (
            f"{indent}{target} = {receiver}.propose(\n"
            + "".join(f"{inner}{argument},\n" for argument in arguments)
            + f"{indent})\n"
        )
    if guarded:
        if any(
            isinstance(node, ast.Name) and node.id == "resolution" for node in ast.walk(owner)
        ):
            raise Abort(f"{line}: the name `resolution` is already bound in this function")
        prelude = (
            f"{indent}resolution = {receiver}.resolve({joined})\n"
            f"{indent}self.assertTrue(resolution.verification.passed)\n"
            f"{indent}self.assertIsNotNone(resolution.match)\n"
            f"{indent}assert resolution.match is not None\n"
            f"{indent}self.assertFalse(resolution.match.matched)\n"
        )
        if len(prelude.splitlines()[0]) > 89:
            inner = indent + "    "
            prelude = (
                f"{indent}resolution = {receiver}.resolve(\n"
                + "".join(f"{inner}{argument},\n" for argument in arguments)
                + f"{indent})\n"
                + prelude.split("\n", 1)[1]
            )
        body = prelude + body

    edits: list[tuple[int, int, str]] = []
    dead: list[tuple[int, int]] = []
    for node in ast.walk(owner):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt) and child is not assign and _is_guard(child, target):
                span = _statement_span(source, starts, child)
                edits.append((*span, ""))
                dead.append(span)

    for node in ast.walk(owner):
        if isinstance(node, ast.Attribute) and _proposal_id_base(node) == target:
            edits.append((*_span(starts, node), target))

    # A site whose binding survives only inside the deleted guard reads nothing.
    # Retaining the call is D07; retaining a name no statement reads would be
    # exactly the dead residue D14 forbids, so it lands as a bare call instead.
    surviving = 0
    for node in ast.walk(owner):
        if isinstance(node, ast.Name) and node.id == target and isinstance(node.ctx, ast.Load):
            position = _span(starts, node)[0]
            if not any(start <= position < end for start, end in dead):
                surviving += 1
    if surviving == 0:
        body = body.replace(f"{target} = ", "", 1)

    edits.append((*_statement_span(source, starts, assign), body))

    # Fail closed on a site that claims more than the migration expresses.
    for node in ast.walk(owner):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == target
            and node.attr != "proposal_id"
        ):
            raise Abort(f"{line}: `{target}.{node.attr}` survives the migration")
    return edits


def _drop_parameter(
    source: str,
    starts: list[int],
    tree: ast.Module,
    name: str,
    qualifier: str,
    parameter: str,
    expected: int,
) -> list[tuple[int, int, str]]:
    definitions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == name
        and any(argument.arg == parameter for argument in node.args.args)
        and (node.args.args[0].arg == "self") == (qualifier == "self")
    ]
    if not definitions:
        return []
    if len(definitions) != 1:
        raise Abort(f"{name}/{qualifier}: {len(definitions)} definitions carry `{parameter}`")
    definition = definitions[0]
    arguments = definition.args.args
    index = next(i for i, argument in enumerate(arguments) if argument.arg == parameter)

    edits: list[tuple[int, int, str]] = []
    if index + 1 < len(arguments):
        edits.append((_span(starts, arguments[index])[0], _span(starts, arguments[index + 1])[0], ""))
    elif index > 0:
        edits.append((_span(starts, arguments[index - 1])[1], _span(starts, arguments[index])[1], ""))
    else:
        edits.append((*_span(starts, arguments[index]), ""))

    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if qualifier == "self":
            matched = (
                isinstance(function, ast.Attribute)
                and function.attr == name
                and isinstance(function.value, ast.Name)
                and function.value.id == "self"
            )
        else:
            matched = isinstance(function, ast.Name) and function.id == name
        if matched:
            calls.append(node)
    if len(calls) != expected:
        raise Abort(f"{name}/{qualifier}: {len(calls)} call sites, contract states {expected}")

    position = index - 1 if qualifier == "self" else index
    for node in calls:
        if len(node.args) <= position:
            raise Abort(f"{name} at line {node.lineno}: no positional argument {position}")
        victim = node.args[position]
        following: ast.expr | ast.keyword | None = None
        if position + 1 < len(node.args):
            following = node.args[position + 1]
        elif node.keywords:
            following = node.keywords[0]
        if following is not None:
            start = _span(starts, victim)[0]
            if isinstance(following, ast.keyword):
                assert following.value.end_lineno is not None
                end = starts[following.lineno - 1] + following.col_offset
            else:
                end = _span(starts, following)[0]
            edits.append((start, end, ""))
        elif position > 0:
            edits.append((_span(starts, node.args[position - 1])[1], _span(starts, victim)[1], ""))
        else:
            edits.append((*_span(starts, victim), ""))
    return edits


def _prune_import(source: str) -> str:
    """Drop `ReviewRequired` from an import once no statement reads it."""
    tree = ast.parse(source)
    reads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "ReviewRequired"
    ]
    if reads:
        return source
    lines = source.splitlines(keepends=True)
    kept = [line for line in lines if line.strip() not in {"ReviewRequired,", "ReviewRequired"}]
    return "".join(kept)


def _demo_transcript() -> str:
    """Run the migrated demo and mask its per-run values, D22's own recipe.

    Regenerated from the demo's OWN output rather than edited, because the two
    `request.resolved_by_artifact` rows the migration removes sit inside the
    pinned block and a hand edit could not know what replaced them.
    """

    sys.path.insert(0, str(DEMO_DIR))
    try:
        demo = importlib.import_module("run_demo")
    finally:
        sys.path.remove(str(DEMO_DIR))
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        demo.main()
    output = stream.getvalue()
    for pattern, replacement, expected in MASKS:
        found = len(pattern.findall(output))
        if found != expected:
            raise Abort(f"mask /{pattern.pattern}/ matched {found} times, expected {expected}")
        output = pattern.sub(replacement, output)
    return output


def _replace_transcript(source: str, transcript: str) -> str:
    """Swap the README's single fenced `text` block for the demo's output."""

    opening = "```text\n"
    if source.count(opening) != 1:
        raise Abort(f"{TRANSCRIPT}: {source.count(opening)} ```text blocks, expected 1")
    start = source.index(opening) + len(opening)
    closing = source.find("\n```\n", start)
    if closing < 0:
        raise Abort(f"{TRANSCRIPT}: unterminated ```text block")
    return source[:start] + transcript + source[closing + 1 :]


def _apply(source: str, edits: list[tuple[int, int, str]]) -> str:
    ordered = sorted(edits, key=lambda edit: (-edit[0], -edit[1]))
    previous = len(source) + 1
    for start, end, _ in ordered:
        if end > previous:
            raise Abort(f"overlapping edits at {start}..{end}")
        previous = start
    for start, end, replacement in ordered:
        source = source[:start] + replacement + source[end:]
    return source


def run(check: bool) -> int:
    # An edit whose REPLACEMENT still contains its own anchor reapplies on every
    # run and reports `applied` where it owes `no-op`. Checked here rather than
    # discovered by the idempotence rerun, so the rule set cannot regress.
    for text_path, old, new, _expected in TEXT:
        if old in new:
            raise Abort(f"{text_path}: replacement contains its own anchor\n{old[:120]}")

    files = sorted({path for path, *_ in SITES} | {path for path, *_ in PARAMS} | {path for path, *_ in TEXT})
    changed: list[str] = []
    for name in files:
        path = ROOT / name
        original = path.read_text()

        source = original
        # `TEXT` also carries prose, and the two AST families are Python-only.
        if name.endswith(".py"):
            starts, tree = _offsets(source), ast.parse(source)
            functions = _qualified(tree)
            totals: dict[str, int] = {}
            for site_path, qualname, _ordinal, _guarded in SITES:
                if site_path == name:
                    totals[qualname] = totals.get(qualname, 0) + 1
            edits: list[tuple[int, int, str]] = []
            for site_path, qualname, ordinal, guarded in SITES:
                if site_path == name:
                    edits.extend(
                        _migrate_site(
                            source, starts, functions, qualname, ordinal, guarded, totals[qualname]
                        )
                    )
            source = _apply(source, edits)

            starts, tree = _offsets(source), ast.parse(source)
            edits = []
            for param_path, function, qualifier, parameter, expected in PARAMS:
                if param_path == name:
                    edits.extend(
                        _drop_parameter(source, starts, tree, function, qualifier, parameter, expected)
                    )
            source = _apply(source, edits)

        for text_path, old, new, expected in TEXT:
            if text_path != name:
                continue
            found = source.count(old)
            if found == expected:
                source = source.replace(old, new)
            elif source.count(new) >= expected and found == 0:
                continue
            else:
                raise Abort(f"{name}: anchor found {found} times, expected {expected}\n{old[:120]}")

        if name.endswith(".py"):
            source = _prune_import(source)
            ast.parse(source)
        if source != original:
            changed.append(name)
            if not check:
                path.write_text(source)

    # Last, and only once the demo on disk is the migrated one: the transcript
    # is generated by RUNNING that demo, so a pending source would pin the old
    # output. Under `--check` with pending files the answer is already known.
    if not (check and changed):
        readme = ROOT / TRANSCRIPT
        original = readme.read_text()
        source = _replace_transcript(original, _demo_transcript())
        if source != original:
            if TRANSCRIPT not in changed:
                changed.append(TRANSCRIPT)
            if not check:
                readme.write_text(source)

    if not changed:
        print("no-op")
    else:
        print(("pending: " if check else "applied: ") + ", ".join(changed))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report without writing")
    arguments = parser.parse_args()
    try:
        return run(arguments.check)
    except Abort as error:
        print(f"ABORT: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
