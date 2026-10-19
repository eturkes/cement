"""M5.1 battery — the per-operation switch, versions, rollback and one-snapshot serving.

Contract: `.agent/decisions/m45-contract.md` §3 (W1-W11, P-a..P-d). The switch is the one human
gate (owner ruling O2/O3): `off` serves nothing, `follow` the newest version of the current
operation revision, `pinned` one version from any revision (O4).
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sqlite3
import tempfile
import unittest
import unittest.mock

from cement_runtime import Candidate, CompilePolicy, NotFoundError, StateError, System, ValidationError
from cement_runtime.cli import main
from cement_runtime.json_value import canonicalize
from cement_runtime.store import Store

P, OP = "tenant_a", "op"
POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)


class SwitchBattery(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-switch-")
        self.addCleanup(directory.cleanup)
        self.db = str(pathlib.Path(directory.name) / "ledger.db")
        self.system = System(self.db)
        self.system.register_operation(P, OP, policy=POLICY)

    def _learn(self, value: int, output: dict[str, int]) -> str:
        for _ in range(2):
            proposal = self.system.submit_proposal(
                P, OP, {"doc": value}, candidate=Candidate(output=output, provenance={})
            )
            self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        self.system.compile(P, OP)
        self.system.verify_drafts(P, OP, verified_by="learning-pass")
        manifest = self.system.inspect_function_promotion(P, OP)
        promotion = self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        return promotion.function_hash

    def _counts(self) -> tuple[int, int]:
        with self.system.store.transaction() as connection:
            settings = connection.execute("SELECT COUNT(*) FROM switch_settings").fetchone()[0]
            events = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return int(settings), int(events)

    def _cli(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            status = main(["--db", self.db, "--partition", P, *args])
        return status, out.getvalue()

    def test_w1_a_promoted_function_answers_nothing_until_switched_on(self) -> None:
        self._learn(1, {"f": 1})
        state = self.system.switch(P, OP)
        self.assertEqual((state.mode, state.function_hash, state.set_by), ("off", None, None))
        resolution = self.system.resolve(P, OP, {"doc": 1})
        self.assertEqual((resolution.verification, resolution.match), (None, None))
        status, out = self._cli("resolve", OP, "--input", '{"doc":1}')
        payload = json.loads(out)
        self.assertEqual(status, 6)
        self.assertEqual(
            payload,
            {
                "artifact_hash": None, "checks": [], "entries": None, "function_hash": None,
                "matched": None, "output": None, "passed": None, "switch": "off",
            },
        )

    def test_w2_follow_serves_each_new_version_without_another_switch_write(self) -> None:
        self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="follow", actor="person")
        self.assertTrue(self.system.resolve(P, OP, {"doc": 1}).match.matched)
        before = self._counts()[0]
        self._learn(2, {"f": 2})
        answer = self.system.resolve(P, OP, {"doc": 2}).match
        self.assertEqual((answer.matched, answer.output), (True, {"f": 2}))
        self.assertEqual(self._counts()[0], before)

    def test_w3_a_pin_keeps_serving_its_version_after_a_newer_promotion(self) -> None:
        v1 = self._learn(1, {"f": 1})
        self._learn(2, {"f": 2})
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.assertTrue(self.system.resolve(P, OP, {"doc": 1}).match.matched)
        absent = self.system.resolve(P, OP, {"doc": 2})
        self.assertEqual((absent.verification.passed, absent.match.matched), (True, False))

    def test_w4_a_pin_crosses_a_reset_until_its_evidence_is_revoked(self) -> None:
        v1 = self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.system.revise_operation(P, OP, policy=POLICY, revised_by="operator")
        self.assertTrue(self.system.resolve(P, OP, {"doc": 1}).match.matched)
        example = self.system.examples(P, OP)[0]["id"]
        self.system.revoke_example(P, example, revoked_by="person", reason="wrong")
        failed = self.system.resolve(P, OP, {"doc": 1})
        self.assertEqual((failed.verification.passed, failed.match), (False, None))
        self.assertIn(
            "pinned-evidence-unrevoked",
            [check.key for check in failed.verification.checks if not check.passed],
        )

    def test_w5_a_revision_never_unpins_but_a_suspension_does(self) -> None:
        v1 = self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        proposal = self.system.submit_proposal(
            P, OP, {"doc": 1}, candidate=Candidate(output={"f": 9}, provenance={})
        )
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        pinned = self.system.resolve(P, OP, {"doc": 1})
        self.assertEqual((pinned.verification.passed, pinned.match.output), (True, {"f": 1}))
        statuses = {row["status"] for row in self.system.artifacts(P, OP)}
        self.assertEqual(statuses, {"promoted"})
        self.system.set_switch(P, OP, mode="follow", actor="person")
        self.assertFalse(self.system.resolve(P, OP, {"doc": 1}).verification.passed)
        member = self.system.artifacts(P, OP)[0]["id"]
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.system.suspend_artifact(P, member, suspended_by="person", reason="wrong")
        suspended = self.system.resolve(P, OP, {"doc": 1})
        self.assertIn(
            "pinned-members-unsuspended",
            [check.key for check in suspended.verification.checks if not check.passed],
        )

    def test_w6_every_refusal_writes_nothing_and_every_success_writes_one_row_one_event(self) -> None:
        v1 = self._learn(1, {"f": 1})
        before = self._counts()
        for kwargs, error in (
            ({"mode": "pinned"}, ValidationError),
            ({"mode": "pinned", "function_hash": "0" * 64}, ValidationError),
            ({"mode": "follow", "function_hash": v1}, ValidationError),
            ({"mode": "on"}, ValidationError),
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(error):
                self.system.set_switch(P, OP, actor="person", **kwargs)
        with self.assertRaises(NotFoundError):
            self.system.set_switch(P, "unregistered", mode="follow", actor="person")
        self.assertEqual(self._counts(), before)
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.assertEqual(self._counts(), (before[0] + 1, before[1] + 1))
        self.assertEqual(self.system.switch(P, OP).function_hash, v1)

    def test_w7_exactly_one_version_is_selected_when_one_is_served(self) -> None:
        v1 = self._learn(1, {"f": 1})
        v2 = self._learn(2, {"f": 2})

        def selected() -> list[str]:
            page = self.system.function_versions(P, OP, limit=1)
            versions = list(page.versions)
            while page.next_before_sequence is not None:
                page = self.system.function_versions(
                    P, OP, limit=1, before_sequence=page.next_before_sequence
                )
                versions += page.versions
            self.assertEqual(len(versions), 2)
            return [version.receipt.function_hash for version in versions if version.selected]

        self.assertEqual(selected(), [])
        self.system.set_switch(P, OP, mode="follow", actor="person")
        self.assertEqual(selected(), [v2])
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.assertEqual(selected(), [v1])

    def test_w8_diff_names_the_case_keys_that_changed(self) -> None:
        v1 = self._learn(1, {"f": 1})
        v2 = self._learn(2, {"f": 2})
        forward = self.system.diff_versions(P, OP, from_hash=v1, to_hash=v2)
        backward = self.system.diff_versions(P, OP, from_hash=v2, to_hash=v1)
        same = self.system.diff_versions(P, OP, from_hash=v1, to_hash=v1)
        self.assertEqual((len(forward.added), forward.removed, forward.changed), (1, (), ()))
        self.assertEqual((backward.added, len(backward.removed)), ((), 1))
        self.assertEqual((same.added, same.removed, same.changed), ((), (), ()))
        receipts = {r.function_hash: r for r in self.system.function_receipts(P, OP).receipts}
        self.assertEqual(
            (forward.from_revision, forward.to_revision, forward.from_policy_hash, forward.to_policy_hash),
            (1, 1, receipts[v1].policy_hash, receipts[v2].policy_hash),
        )
        self.assertEqual(
            (forward.from_projection_hash, forward.to_projection_hash, forward.projection_changed,
             forward.from_program, forward.to_program),
            (None, None, False, None, None),
        )
        self.system.revise_operation(P, OP, policy=POLICY, revised_by="operator")
        v3 = self._learn(3, {"f": 3})
        across = self.system.diff_versions(P, OP, from_hash=v1, to_hash=v3)
        self.assertEqual((across.from_revision, across.to_revision), (1, 2))
        code, out = self._cli("function", "diff", OP, "--from", v1, "--to", v3)
        self.assertEqual((code, json.loads(out)["to_revision"]), (0, 2))
        v4 = self._learn(1, {"f": 9})
        rewritten = self.system.diff_versions(P, OP, from_hash=v1, to_hash=v4)
        self.assertEqual(rewritten.changed, (canonicalize({"doc": 1}).digest,))
        self.assertEqual(rewritten.added, (canonicalize({"doc": 3}).digest,))

    def test_w9_export_follows_the_switch_and_refuses_while_off(self) -> None:
        self._learn(1, {"f": 1})
        status, out = self._cli("function", "export", OP)
        self.assertEqual((status, out), (6, ""))
        self.system.set_switch(P, OP, mode="follow", actor="person")
        status, out = self._cli("function", "export", OP)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out)["abi"], "cement-function-v3")

    def test_w10_one_read_snapshot_serves_switch_version_and_checks(self) -> None:
        import cement_runtime.store as store

        v1 = self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        opened = []
        original = store.Store.transaction

        def counting(instance, *, write=False):  # type: ignore[no-untyped-def]
            opened.append(write)
            return original(instance, write=write)

        with unittest.mock.patch.object(store.Store, "transaction", counting):
            self.assertTrue(self.system.resolve(P, OP, {"doc": 1}).match.matched)
        self.assertEqual(opened, [False])

        held: list[object] = []
        seen: list[tuple[object, bool]] = []
        pin_checks = System._pin_checks
        enter = original

        @contextlib.contextmanager
        def recording(instance, *, write=False):  # type: ignore[no-untyped-def]
            with enter(instance, write=write) as connection:
                held.append(connection)
                yield connection

        def spy(instance, connection, **kwargs):  # type: ignore[no-untyped-def]
            seen.append((connection, connection.in_transaction))
            return pin_checks(instance, connection, **kwargs)

        with (
            unittest.mock.patch.object(store.Store, "transaction", recording),
            unittest.mock.patch.object(System, "_pin_checks", spy),
        ):
            self.assertTrue(self.system.resolve(P, OP, {"doc": 1}).match.matched)
        self.assertEqual(len(held), 1)
        self.assertEqual([(connection is held[0], live) for connection, live in seen], [(True, True)])


    def test_w12_contrary_evidence_is_a_ledger_state_never_corruption(self) -> None:
        v1 = self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="follow", actor="person")
        proposal = self.system.submit_proposal(
            P, OP, {"doc": 1}, candidate=Candidate(output={"f": 9}, provenance={})
        )
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        (member,) = [row["id"] for row in self.system.artifacts(P, OP)]
        self.assertEqual(self.system.artifact(P, member)["status"], "promoted")
        report = self.system.function_report(P, OP)
        assert report.function_anchor is not None
        self.assertEqual(report.function_anchor.receipt.function_hash, v1)
        live = {check.key: check.passed for check in self.system.verify_function(P, OP).checks}
        self.assertFalse(live["current-promotion-receipts"])
        with self.assertRaisesRegex(StateError, f"{member} conflicts with active evidence"):
            self.system.inspect_function_promotion(P, OP)
        self.assertEqual(self._cli("artifact", "show", member)[0], 0)
        conflicting = self.system.examples(P, OP)[-1]["id"]
        self.system.revoke_example(P, conflicting, revoked_by="learning-pass", reason="wrong")
        self.assertEqual(self.system.inspect_function_promotion(P, OP).function_hash, v1)
        self.assertTrue(self.system.verify_function(P, OP).passed)

    def test_w1_off_reads_the_switch_and_operation_rows_alone(self) -> None:
        self._learn(1, {"f": 1})
        statements: list[str] = []
        connect = Store._connect

        def traced(store: Store, *, read_only: bool = False) -> sqlite3.Connection:
            connection = connect(store, read_only=read_only)
            connection.set_trace_callback(statements.append)
            return connection

        with unittest.mock.patch.object(Store, "_connect", autospec=True, side_effect=traced):
            off = self.system.resolve(P, OP, {"doc": 1})
        self.assertEqual((off.switch.mode, off.verification, off.match), ("off", None, None))
        read = " ".join(statements).lower()
        self.assertIn("switch_settings", read)
        self.assertIn("operations", read)
        for table in ("artifacts", "function_receipts", "examples", "function_memberships"):
            self.assertNotIn(table, read)

    def test_w5_a_challenge_counterexample_on_a_member_key_fails_the_pin(self) -> None:
        v1 = self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.system.challenge(P, OP, {"doc": 1}, {"f": 7}, reviewer="person")
        failed = self.system.resolve(P, OP, {"doc": 1})
        self.assertEqual((failed.verification.passed, failed.match), (False, None))
        self.assertIn(
            "pinned-no-counterexample",
            [check.key for check in failed.verification.checks if not check.passed],
        )

    def test_w5c_after_a_reset_suspending_a_retired_member_fails_the_pin(self) -> None:
        v1 = self._learn(1, {"f": 1})
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.system.revise_operation(P, OP, policy=POLICY, revised_by="operator")
        self.assertTrue(self.system.resolve(P, OP, {"doc": 1}).match.matched)
        (member,) = [row["id"] for row in self.system.artifacts(P, OP)]
        self.assertEqual(self.system.artifact(P, member)["status"], "retired")
        self.system.suspend_artifact(P, member, suspended_by="person", reason="wrong")
        failed = self.system.resolve(P, OP, {"doc": 1})
        self.assertEqual(
            [check.key for check in failed.verification.checks if not check.passed],
            ["pinned-members-unsuspended"],
        )

    def test_w7_check_reports_whether_each_version_would_serve_now(self) -> None:
        v1 = self._learn(1, {"f": 1})
        v2 = self._learn(2, {"f": 2})
        plain = self.system.function_versions(P, OP).versions
        self.assertEqual({version.servable for version in plain}, {None})
        self.assertEqual({version.projection_hash for version in plain}, {None})
        member = next(
            row["id"] for row in self.system.artifacts(P, OP) if row["input_hash"] == canonicalize({"doc": 1}).digest
        )
        evidence = self.system.artifact(P, member)["evidence_ids"][0]
        self.system.revoke_example(P, evidence, revoked_by="person", reason="wrong")
        checked = {v.receipt.function_hash: v.servable for v in self.system.function_versions(P, OP, check=True).versions}
        self.assertEqual(checked, {v1: False, v2: False})
        code, out = self._cli("function", "versions", OP, "--check")
        self.assertEqual((code, sorted(v["servable"] for v in json.loads(out)["versions"])), (0, [False, False]))
        v3 = self._learn(3, {"f": 3})
        self.system.set_switch(P, OP, mode="follow", actor="person")
        served = {v.receipt.function_hash: (v.selected, v.servable) for v in self.system.function_versions(P, OP, check=True).versions}
        self.assertEqual(served[v3], (True, True))

    def test_w13_a_pin_verifies_past_the_sqlite_variable_limit(self) -> None:
        for value in range(7):
            self._learn(100 + value, {"f": value})
        pinned = self.system.function_receipts(P, OP).receipts[0]
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=pinned.function_hash)
        connect = Store._connect

        def tight(store: Store, *, read_only: bool = False) -> sqlite3.Connection:
            connection = connect(store, read_only=read_only)
            connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 5)
            return connection

        with unittest.mock.patch.object(Store, "_connect", autospec=True, side_effect=tight):
            served = self.system.resolve(P, OP, {"doc": 106})
        self.assertEqual((served.verification.passed, served.verification.entries), (True, 7))
        self.assertEqual(served.match.output, {"f": 6})

if __name__ == "__main__":
    unittest.main()
