"""p136-store battery — shadow observations (`.agent/decisions/p136-store-contract.md`)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from unittest import mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    ConflictError,
    IntegrityError,
    NotFoundError,
    System,
    ValidationError,
)
from cement_runtime import shadow as sh
from cement_runtime.cli import main

POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
P, OP = "tenant_a", "op"
IGNORE_NOTE = {"abi": "cement-comparator-v1", "rules": [{"path": ["note"], "rule": "ignore"}]}


def _confirm(system: System, value: int, output: dict, partition: str = P) -> None:
    for reviewer in ("r1", "r2"):
        proposal = system.submit_proposal(
            partition, OP, {"x": value}, candidate=Candidate(output=output, provenance={})
        )
        system.review(partition, proposal, reviewer=reviewer, decision="accept")


def _publish(system: System, partition: str = P) -> str:
    system.compile(partition, OP)
    system.verify_drafts(partition, OP, verified_by="lp")
    manifest = system.inspect_function_promotion(partition, OP)
    system.promote_function(partition, OP, expected_function_hash=manifest.function_hash, promoted_by="lp")
    return manifest.function_hash


def _ledger_counts(database: str) -> dict[str, int]:
    with closing(sqlite3.connect(database)) as connection:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in tables}


class _Case(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-shadow-")
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.db = str(self.root / "ledger.db")
        self.system = System(self.db)
        self.system.register_operation(P, OP, policy=POLICY)
        _confirm(self.system, 1, {"y": 1, "note": "n"})
        _confirm(self.system, 2, {"y": 2, "note": "m"})
        self.v1 = _publish(self.system)
        self.system.set_switch(P, OP, mode="follow", actor="person")
        self.store = sh.ShadowStore(sh.shadow_path(self.db))
        self.counter = 0

    def admit(self, value: int = 1, *, function_hash: str | None = None, observed_at_us: int = 10) -> sh.Admission:
        self.counter += 1
        return sh.admit(
            self.system, self.store, P, OP,
            observation_id=f"chat:{self.counter}:call",
            function_hash=function_hash or self.v1,
            input_value={"x": value},
            observed_at_us=observed_at_us,
        )

    def record(self, ident: str, output: object) -> sh.ObservationRecord:
        return sh.record_shadow(self.system, self.store, ident, llm_output=output, model="m", prompt_revision="p1", latency_ms=5)


class StoreIdentityTests(_Case):
    def test_s1_foreign_files_refuse_byte_identical(self) -> None:
        ledger_before = pathlib.Path(self.db).read_bytes()
        with self.assertRaisesRegex(IntegrityError, "not a Cement shadow store"):
            sh.ShadowStore(self.db)
        self.assertEqual(pathlib.Path(self.db).read_bytes(), ledger_before)
        foreign = self.root / "foreign.db"
        with closing(sqlite3.connect(foreign)) as connection:
            connection.execute("CREATE TABLE t(x)")
            connection.commit()
        before = foreign.read_bytes()
        with self.assertRaisesRegex(IntegrityError, "not a Cement shadow store"):
            sh.ShadowStore(foreign)
        self.assertEqual(foreign.read_bytes(), before)
        changed = self.root / "changed.shadow"
        sh.ShadowStore(changed)
        with closing(sqlite3.connect(changed)) as connection:
            connection.execute("CREATE TABLE extra(x)")
            connection.commit()
        with self.assertRaisesRegex(IntegrityError, "does not match the runtime schema"):
            sh.ShadowStore(changed)
        with closing(sqlite3.connect(changed)) as connection:
            connection.execute("DROP TABLE extra")
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
        with self.assertRaisesRegex(IntegrityError, "schema 2 is unsupported"):
            sh.ShadowStore(changed)

    def test_s1_mode_and_existing_only_open(self) -> None:
        previous = os.umask(0o022)
        try:
            path = self.root / "fresh.shadow"
            sh.ShadowStore(path)
        finally:
            os.umask(previous)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        missing = self.root / "missing.shadow"
        with self.assertRaises(NotFoundError):
            sh.ShadowStore(missing, create=False)
        self.assertFalse(missing.exists())

    def test_s1_transitions_and_capture_are_guarded(self) -> None:
        admitted = self.admit()
        agreed = self.record(self.admit().id, {"y": 1, "note": "n"})
        with closing(sqlite3.connect(self.store.path)) as connection:
            for statement, message in (
                (f"UPDATE observations SET state = 'disagreed' WHERE id = '{admitted.id}'", "invalid observation state transition"),
                (f"UPDATE observations SET state = 'admitted' WHERE id = '{agreed['id']}'", "invalid observation state transition"),
                (f"UPDATE observations SET function_output_json = '1' WHERE id = '{admitted.id}'", "keeps its identity and capture"),
                (f"UPDATE observations SET comparator_hash = 'x' WHERE id = '{admitted.id}'", "keeps its identity and capture"),
                (f"UPDATE observations SET state = 'agreed' WHERE id = '{admitted.id}'", "CHECK constraint"),
            ):
                with self.subTest(statement=statement), self.assertRaisesRegex(sqlite3.IntegrityError, message):
                    connection.execute(statement)


class AdmissionTests(_Case):
    def test_s2_the_captured_version_decides_in_both_directions(self) -> None:
        _confirm(self.system, 1, {"y": 10, "note": "n"})  # a contradicting pair, then a merge
        examples = [e["id"] for e in self.system.examples(P, OP) if e["output"] == {"y": 1, "note": "n"}]
        self.system.supersede_examples(P, OP, example_ids=examples, output={"y": 10, "note": "n"}, reviewer="lp")
        v2 = _publish(self.system)
        old, new = self.admit(1, function_hash=self.v1), self.admit(1, function_hash=v2)
        with mock.patch.object(System, "reconstruct_function_receipt", wraps=self.system.reconstruct_function_receipt) as rebuilt:
            third = self.admit(1, function_hash=v2)
        self.assertEqual(rebuilt.call_count, 0)  # the served version answers from serving
        with mock.patch.object(System, "reconstruct_function_receipt", wraps=self.system.reconstruct_function_receipt) as rebuilt:
            self.admit(1, function_hash=self.v1)
        self.assertEqual(rebuilt.call_count, 1)  # an older version is rebuilt from its receipt
        self.assertEqual(self.record(old.id, {"y": 1, "note": "n"})["state"], "agreed")
        self.assertEqual(self.record(new.id, {"y": 1, "note": "n"})["state"], "disagreed")
        self.assertEqual(self.record(third.id, {"y": 10, "note": "n"})["state"], "agreed")

    def test_s2_capture_works_with_the_switch_off(self) -> None:
        self.system.set_switch(P, OP, mode="off", actor="person")
        admission = self.admit(2)
        self.assertEqual(sh.observations(self.store, P, OP)[0]["function_output"], {"y": 2, "note": "m"})
        self.assertTrue(admission.admitted)

    def test_s2_refusals_write_nothing_in_either_file(self) -> None:
        self.system.register_operation("tenantXa", OP, policy=POLICY)
        _confirm(self.system, 1, {"y": 1, "note": "x"}, partition="tenantXa")
        foreign = _publish(self.system, partition="tenantXa")
        ledger, store = pathlib.Path(self.db).read_bytes(), self.store.path.read_bytes()
        for kwargs, error in (
            ({"function_hash": foreign}, NotFoundError),
            ({"function_hash": "0" * 64}, NotFoundError),
            ({"value": 99}, ValidationError),
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(error):
                self.admit(**kwargs)
        self.assertEqual((pathlib.Path(self.db).read_bytes(), self.store.path.read_bytes()), (ledger, store))
        with closing(sqlite3.connect(self.db)) as connection:
            trigger = connection.execute("SELECT sql FROM sqlite_master WHERE name = 'function_memberships_no_update'").fetchone()[0]
            connection.execute("DROP TRIGGER function_memberships_no_update")
            connection.execute("UPDATE function_memberships SET entry_seal = ? WHERE ordinal = 0", ("0" * 64,))
            connection.execute(trigger)
            connection.commit()
        store = self.store.path.read_bytes()
        with self.assertRaises(IntegrityError):
            self.admit(1)
        self.assertEqual(self.store.path.read_bytes(), store)

    def test_s2_a_repeated_identity_counts_and_returns_the_original(self) -> None:
        first = sh.admit(self.system, self.store, P, OP, observation_id="same", function_hash=self.v1, input_value={"x": 1}, observed_at_us=1)
        again = sh.admit(self.system, self.store, P, OP, observation_id="same", function_hash=self.v1, input_value={"x": 2}, observed_at_us=9)
        self.assertEqual((first.admitted, again.admitted, again.id), (True, False, first.id))
        self.assertEqual(sh.drift(self.store, P, OP)["duplicates"], 1)
        self.assertEqual(len(sh.observations(self.store, P, OP)), 1)
        self.assertEqual(sh.observations(self.store, P, OP)[0]["input"], {"x": 1})  # the original stays

    def test_s2_two_racing_admissions_write_one_row(self) -> None:
        barrier, results = threading.Barrier(4), []

        def race() -> None:
            barrier.wait()
            results.append(sh.admit(System(self.db), sh.ShadowStore(self.store.path), P, OP, observation_id="race", function_hash=self.v1, input_value={"x": 1}, observed_at_us=1))

        threads = [threading.Thread(target=race) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(result.admitted for result in results), [False, False, False, True])
        self.assertEqual(len({result.id for result in results}), 1)
        self.assertEqual(sh.drift(self.store, P, OP)["duplicates"], 3)

    def test_s2_the_observation_id_bound_is_an_adjacent_pair(self) -> None:
        sh.admit(self.system, self.store, P, OP, observation_id="o" * 505, function_hash=self.v1, input_value={"x": 1}, observed_at_us=1)
        for bad in ("o" * 506, "", "a\nb"):
            with self.subTest(length=len(bad)), self.assertRaises(ValidationError):
                sh.admit(self.system, self.store, P, OP, observation_id=bad, function_hash=self.v1, input_value={"x": 1}, observed_at_us=1)


class OutcomeTests(_Case):
    def test_s3_drop_cancel_and_fail_never_touch_the_ledger(self) -> None:
        before = _ledger_counts(self.db)
        dropped = sh.drop(self.store, P, OP, observation_id="full", function_hash=self.v1, input_value={"x": 1}, observed_at_us=1, reason="queue full")
        self.assertFalse(sh.drop(self.store, P, OP, observation_id="full", function_hash=self.v1, input_value={"x": 1}, observed_at_us=1, reason="again").admitted)
        cancelled, failed = self.admit(), self.admit()
        sh.cancel(self.store, cancelled.id, reason="shutdown")
        sh.fail(self.store, failed.id, reason="timeout", model="m", prompt_revision="p1", latency_ms=30_000)
        states = {row["id"]: (row["state"], row["note"]) for row in sh.observations(self.store, P, OP)}
        self.assertEqual(states, {dropped.id: ("dropped", "queue full"), cancelled.id: ("cancelled", "shutdown"), failed.id: ("failed", "timeout")})
        for call in (lambda: sh.cancel(self.store, failed.id, reason="x"), lambda: self.record(cancelled.id, {"y": 1})):
            with self.assertRaises(ConflictError):
                call()
        self.assertEqual(_ledger_counts(self.db), before)
        self.assertEqual(sh.drift(self.store, P, OP)["duplicates"], 1)


class RecordTests(_Case):
    def test_s4_an_agreement_writes_no_ledger_row_and_keeps_serving_warm(self) -> None:
        admission = self.admit()
        self.system.resolve(P, OP, {"x": 1})  # warm
        ledger = pathlib.Path(self.db).read_bytes()
        record = self.record(admission.id, {"note": "n", "y": 1})
        self.assertEqual((record["state"], record["differences"], record["source_id"]), ("agreed", [], None))
        self.assertEqual(pathlib.Path(self.db).read_bytes(), ledger)
        with mock.patch.object(System, "_verify_function_snapshot", wraps=self.system._verify_function_snapshot) as verified:
            self.system.resolve(P, OP, {"x": 1})
        self.assertEqual(verified.call_count, 0)

    def test_s4_a_disagreement_becomes_one_bounded_proposal(self) -> None:
        admission = self.admit()
        before = _ledger_counts(self.db)
        record = self.record(admission.id, {"y": 9, "note": "n"})
        after = _ledger_counts(self.db)
        self.assertEqual({k: after[k] - before[k] for k in after if after[k] != before[k]}, {"proposals": 1, "events": 1, "sqlite_sequence": 0} if False else {"proposals": 1, "events": 1})
        proposal = self.system.proposal(P, record["proposal_id"])
        self.assertEqual((proposal["status"], proposal["input"], proposal["proposed_output"]), ("pending", {"x": 1}, {"y": 9, "note": "n"}))
        self.assertEqual(
            proposal["provenance"],
            {"shadow": {"observation_id": "chat:1:call", "function_hash": self.v1, "receipt_id": record["receipt_id"],
                        "comparator_hash": None, "model": "m", "prompt_revision": "p1", "difference_count": 1,
                        "differences": ["$.y"]}},
        )
        self.assertEqual(record["source_id"], "shadow:chat:1:call")
        cases = self.system.learning_cases(P, OP)
        self.assertFalse(cases["nothing_to_learn"])
        self.assertIn(record["proposal_id"], [i for case in cases["cases"] for i in case["pending_proposal_ids"]])
        self.assertTrue(self.system.resolve(P, OP, {"x": 1}).match.matched)  # serving unchanged

    def test_s4_provenance_keeps_the_first_five_paths_and_the_count(self) -> None:
        answer = {"y": 1, "note": "n"} | {f"k{i}": i for i in range(7)}
        record = self.record(self.admit().id, answer)
        self.assertEqual(len(record["differences"]), 7)
        shadow = self.system.proposal(P, record["proposal_id"])["provenance"]["shadow"]
        self.assertEqual((shadow["difference_count"], shadow["differences"]), (7, record["differences"][:5]))

    def test_s4_bounds_are_adjacent_pairs(self) -> None:
        big = "a" * (1_048_576 - len('{"y":""}'))
        self.assertEqual(self.record(self.admit().id, {"y": big})["state"], "disagreed")
        with self.assertRaisesRegex(ValidationError, "1048576"):
            self.record(self.admit().id, {"y": big + "a"})
        sh.record_shadow(self.system, self.store, self.admit().id, llm_output={"y": 1, "note": "n"}, model="m" * 256, prompt_revision="p", latency_ms=0)
        with self.assertRaisesRegex(ValidationError, "model exceeds 256"):
            sh.record_shadow(self.system, self.store, self.admit().id, llm_output={"y": 1}, model="m" * 257, prompt_revision="p", latency_ms=0)


class FinishTests(_Case):
    def test_s5_a_crash_after_the_ledger_commit_recovers_one_proposal(self) -> None:
        admission = self.admit()
        with mock.patch.object(sh, "_record", side_effect=RuntimeError("planted")), self.assertRaisesRegex(RuntimeError, "planted"):
            self.record(admission.id, {"y": 9, "note": "n"})
        [row] = sh.pending(self.store, state="prepared")
        self.assertEqual(row["id"], admission.id)
        proposals = self.system.proposals(P, status="all")
        self.system.review(P, proposals[-1]["id"], reviewer="lp", decision="reject")  # reviewed before the retry
        finished = sh.finish_shadow(self.system, self.store, admission.id)
        self.assertEqual((finished["state"], finished["proposal_id"]), ("disagreed", proposals[-1]["id"]))
        self.assertEqual(len(self.system.proposals(P, status="all")), len(proposals))

    def test_s5_a_mismatching_proposal_under_the_source_id_conflicts(self) -> None:
        admission = self.admit()
        self.system.submit_proposal(P, OP, {"x": 1}, candidate=Candidate(output={"y": 7}, provenance={}), source_id="shadow:chat:1:call")
        with self.assertRaisesRegex(ConflictError, "does not match this observation"):
            self.record(admission.id, {"y": 9, "note": "n"})
        self.assertEqual(sh.observations(self.store, P, OP)[0]["state"], "prepared")

    def test_s5_a_revision_change_writes_no_proposal(self) -> None:
        admission = self.admit()
        self.system.revise_operation(P, OP, policy=POLICY, revised_by="ops")
        before = _ledger_counts(self.db)
        record = self.record(admission.id, {"y": 9, "note": "n"})
        self.assertEqual((record["state"], record["proposal_id"]), ("disagreed", None))
        self.assertEqual(record["note"], "no proposal: the operation moved from revision 1 to 2")
        self.assertEqual(_ledger_counts(self.db), before)

    def test_s5_the_comparator_captured_at_admission_decides(self) -> None:
        exact = self.admit()  # no comparator yet
        self.system.set_comparator(P, OP, IGNORE_NOTE, actor="lp")
        loose = self.admit()
        self.system.set_comparator(P, OP, {"abi": "cement-comparator-v1", "rules": [{"path": ["y"], "rule": "tolerance", "within": "0"}]}, actor="lp")
        self.assertEqual(self.record(exact.id, {"y": 1, "note": "other"})["state"], "disagreed")
        record = self.record(loose.id, {"y": 1, "note": "other"})
        self.assertEqual((record["state"], record["comparator_sequence"]), ("agreed", 1))


class ReadTests(_Case):
    def test_s6_drift_groups_hashes_cutoff_and_empty_window(self) -> None:
        _confirm(self.system, 3, {"y": 3, "note": "k"})
        v2 = _publish(self.system)
        for value, digest, answer, at in (
            (1, self.v1, {"y": 1, "note": "n"}, 100), (1, self.v1, {"y": 0, "note": "n"}, 200),
            (3, v2, {"y": 3, "note": "k"}, 300), (2, v2, {"y": 2, "note": "m"}, 400),
        ):
            self.record(self.admit(value, function_hash=digest, observed_at_us=at).id, answer)
        self.admit(2, function_hash=v2, observed_at_us=500)
        report = sh.drift(self.store, P, OP)
        self.assertEqual([g["function_hash"] for g in report["groups"]], [self.v1, v2])
        self.assertEqual([(g["counts"]["agreed"], g["counts"]["disagreed"], g["counts"]["admitted"]) for g in report["groups"]], [(1, 1, 0), (2, 0, 1)])
        self.assertEqual((report["disagreements"], report["totals"]["agreed"]), (1, 3))
        self.assertEqual(sh.drift(self.store, P, OP, since_us=200)["totals"]["disagreed"], 1)  # inclusive
        self.assertEqual(sh.drift(self.store, P, OP, since_us=201)["totals"]["disagreed"], 0)
        sh.admit(self.system, self.store, P, OP, observation_id="chat:1:call", function_hash=self.v1, input_value={"x": 1}, observed_at_us=1)
        empty = sh.drift(self.store, P, OP, since_us=10_000)
        self.assertEqual((empty["groups"], sum(empty["totals"].values()), empty["duplicates"]), ([], 0, 1))

    def test_s6_paging_filters_and_the_pending_cursor(self) -> None:
        ids = [self.admit().id for _ in range(5)]
        self.record(ids[1], {"y": 1, "note": "n"})
        first = sh.observations(self.store, P, OP, limit=2)
        rest = sh.observations(self.store, P, OP, after_sequence=first[-1]["sequence"], limit=1000)
        self.assertEqual([row["id"] for row in first + rest], ids)
        self.assertEqual([row["id"] for row in sh.observations(self.store, P, OP, state="agreed")], [ids[1]])
        page = sh.pending(self.store, limit=2)
        self.assertEqual([row["id"] for row in page], [ids[0], ids[2]])
        self.assertEqual([row["id"] for row in sh.pending(self.store, after_sequence=page[-1]["sequence"])], ids[3:])
        for bad in (0, 1001, True):
            with self.assertRaises(ValidationError):
                sh.observations(self.store, P, OP, limit=bad)


class RetentionTests(_Case):
    def test_s7_prune_is_an_adjacent_pair_and_erase_spares_neighbours(self) -> None:
        now = 10**15
        self.admit(observed_at_us=now - 86_400_000_000 - 1)
        kept = self.admit(observed_at_us=now - 86_400_000_000)
        self.system.register_operation("tenantXa", OP, policy=POLICY)
        with mock.patch.object(sh, "_now_us", return_value=now):
            self.assertEqual(self.store.prune(P, older_than_seconds=86_400), 1)
        self.assertEqual([row["id"] for row in sh.observations(self.store, P, OP)], [kept.id])
        self.assertEqual(self.store.erase("tenantXa"), {"observations": 0, "duplicates": 0})
        self.assertEqual(self.store.erase(P), {"observations": 1, "duplicates": 0})

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", self.db, "--partition", P, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_s7_the_cli_runs_both_files_and_creates_no_store(self) -> None:
        self.record(self.admit().id, {"y": 9, "note": "n"})
        code, out, _ = self.run_cli("partition", "erase", "--actor", "ops", "--confirm", P)
        result = json.loads(out)
        self.assertEqual((code, result["shadow"]), (0, {"observations": 1, "duplicates": 0}))
        self.assertEqual(result["counts"]["proposals"], 5)
        code, out, _ = self.run_cli("partition", "erase", "--actor", "ops", "--confirm", P)
        self.assertEqual(code, 3)
        other = self.root / "other.db"
        System(str(other)).register_operation(P, OP, policy=POLICY)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", str(other), "--partition", P, "retention", "prune", "--older-than", "0", "--actor", "ops"])
        self.assertEqual((code, json.loads(out.getvalue())["shadow"]), (0, None))
        self.assertFalse(sh.shadow_path(other).exists())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = main(["--db", str(other), "--partition", P, "--shadow", str(self.root / "nope"), "retention", "prune", "--older-than", "0", "--actor", "ops"])
        self.assertEqual(code, 3)

    def test_s9_drift_and_observations_read_the_store_alone(self) -> None:
        self.record(self.admit().id, {"y": 1, "note": "n"})
        code, out, _ = self.run_cli("function", "drift", OP)
        self.assertEqual((code, json.loads(out)["totals"]["agreed"]), (0, 1))
        code, out, _ = self.run_cli("function", "observations", OP, "--state", "agreed")
        self.assertEqual((code, len(json.loads(out))), (0, 1))
        ledger = pathlib.Path(self.db).read_bytes()
        self.assertEqual(self.run_cli("function", "drift", OP)[0], 0)
        self.assertEqual(pathlib.Path(self.db).read_bytes(), ledger)  # read alone
        missing = ["--shadow", str(self.root / "missing.shadow")]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", self.db, "--partition", P, *missing, "function", "drift", OP])
        self.assertEqual((code, out.getvalue()), (3, ""))
        self.assertFalse((self.root / "missing.shadow").exists())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = main(["--db", self.db, "--partition", P, "--shadow", self.db, "function", "drift", OP])
        self.assertEqual(code, 5)


if __name__ == "__main__":
    unittest.main()
