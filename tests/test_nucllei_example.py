"""nucllei skill battery: `/ext/bin/cement` in the llens sandbox jail + the three nucllei skills.

Contract: `.agent/decisions/nucllei-contract.md` (N1-N8). The jail command keeps one ledger per
user in `CEMENT_HOME`; the chat model runs it through `run_shell` and reads its Japanese lines.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from typing import Any
from unittest import mock

from cement_runtime import Candidate, StateError, System
from cement_runtime.json_value import canonicalize
from cement_runtime.system import PROVENANCE_MAX_BYTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "nucllei"
OP = "extraction_plan"
NOTE_A = "PHYSICIAN PROGRESS NOTE\nPatient: A\n"
NOTE_B = "PHYSICIAN PROGRESS NOTE\nPatient: B\n"
NOTE_C = "PHYSICIAN PROGRESS NOTE\nPatient: C\n"
LAB = "LAB RESULT SLIP\nPatient: A\nPotassium: 4.2\n"
PLAN = {"fields": [{"name": "patient", "label": "Patient"}]}
WIDER = {"fields": [{"name": "patient", "label": "Patient"}, {"name": "mrn", "label": "MRN"}]}
HOUR = 3600 * 1_000_000
MINUTE = 60 * 1_000_000
TICKET = re.compile(r"控え: (t_[0-9a-f]{16})")


def _load(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CEMENT = _load(EXAMPLE / "cement_nucllei.py", "nucllei_example_cement")
GENERATE = _load(EXAMPLE / "generate.py", "nucllei_example_generate")


class _Jail(unittest.TestCase):
    """One user's workspace: `CEMENT_HOME` in a temporary directory, a clock the test moves."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-nucllei-")
        self.addCleanup(directory.cleanup)
        self.home = pathlib.Path(directory.name) / ".cement"
        environment = mock.patch.dict(os.environ, {"CEMENT_HOME": str(self.home)})
        environment.start()
        self.addCleanup(environment.stop)
        self.now = 1_800_000_000_000_000
        clock = mock.patch.object(CEMENT, "_clock_us", lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def run_cement(self, *argv: str, stdin: str = "") -> tuple[int, str]:
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), contextlib.redirect_stdout(out):
            status = CEMENT.main(list(argv))
        return status, out.getvalue()

    @property
    def system(self) -> System:
        return System(self.home / "ledger.db", create=False, clock_us=lambda: self.now)

    def use(self, document: str = NOTE_A) -> tuple[int, str, str | None]:
        status, text = self.run_cement("use", OP, "--field", "document", stdin=document)
        found = TICKET.search(text)
        return status, text, None if found is None else found.group(1)

    def answer(self, document: str, output: object = PLAN, *, request: str = "plan this") -> str:
        """One miss turn: use, then record the model's output. Returns record's text."""

        status, _, ticket = self.use(document)
        self.assertEqual(status, 0)
        assert ticket is not None
        status, text = self.run_cement("record", ticket, "--request", request, stdin=json.dumps(output))
        self.assertEqual(status, 0, text)
        return text

    def tickets(self) -> list[str]:
        folder = self.home / "tickets"
        return sorted(p.stem for p in folder.glob("t_*.json")) if folder.is_dir() else []

    def counts(self) -> tuple[int, int]:
        with self.system.store.transaction() as connection:
            return (
                connection.execute("SELECT COUNT(*) FROM proposals").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            )

    def pending(self) -> list[dict[str, Any]]:
        return self.system.proposals(CEMENT.PARTITION, status="pending")

    def publish(self, *documents: str, output: object = PLAN) -> None:
        """Each document confirmed twice through the library, published as the newest version."""

        system = self.system
        for document in (d for d in documents for _ in range(2)):
            proposal = system.submit_proposal(
                CEMENT.PARTITION, OP, {"document": document.rstrip("\n")},
                candidate=Candidate(output=output, provenance={}),
            )
            system.review(CEMENT.PARTITION, proposal, reviewer="learning-pass", decision="accept")
        system.compile(CEMENT.PARTITION, OP)
        system.verify_drafts(CEMENT.PARTITION, OP, verified_by="learning-pass")
        manifest = system.inspect_function_promotion(CEMENT.PARTITION, OP)
        system.promote_function(
            CEMENT.PARTITION, OP, expected_function_hash=manifest.function_hash,
            promoted_by="learning-pass",
        )


class ChatBattery(_Jail):
    def test_n1_the_first_use_creates_the_ledger_registers_off_and_mints_a_ticket(self) -> None:
        status, text, ticket = self.use()
        self.assertEqual(status, 0, text)
        self.assertIn("答えない (学習済みの版がまだ無い)", text)
        self.assertEqual(self.tickets(), [ticket])
        held = json.loads((self.home / "tickets" / f"{ticket}.json").read_text(encoding="utf-8"))
        self.assertEqual(held, {"operation": OP, "input": {"document": NOTE_A.rstrip("\n")}, "used_at_us": self.now})
        (operation,) = self.system.operations(CEMENT.PARTITION)
        self.assertEqual(operation["name"], OP)
        self.assertEqual(operation["policy"]["min_confirmations"], 2)
        self.assertEqual(self.system.switch(CEMENT.PARTITION, OP).mode, "off")
        registered = [e for e in self.system.events(CEMENT.PARTITION) if e["kind"] == "operation.registered"]
        self.assertEqual([e["payload"]["registered_by"] for e in registered], ["nucllei-chat"])
        self.assertEqual(self.counts()[0], 0)
        self.assertTrue(text.rstrip().endswith(f"{CEMENT.COMMAND} record {ticket} に渡して記録する。"))

    def test_n1_field_text_drops_trailing_newlines_and_json_input_reads_alike(self) -> None:
        self.use("PHYSICIAN PROGRESS NOTE\nPatient: A\n\n\n")
        status, _ = self.run_cement("use", OP, stdin=json.dumps({"document": NOTE_A.rstrip("\n")}))
        self.assertEqual(status, 0)
        inputs = {
            json.dumps(json.loads((self.home / "tickets" / f"{t}.json").read_text(encoding="utf-8"))["input"])
            for t in self.tickets()
        }
        self.assertEqual(inputs, {json.dumps({"document": NOTE_A.rstrip("\n")})})

    def test_n1_a_switched_on_function_answers_and_writes_nothing(self) -> None:
        self.use()
        self.publish(NOTE_A)
        self.system.set_switch(CEMENT.PARTITION, OP, mode="follow", actor="test")
        before, tickets = self.counts(), self.tickets()
        status, text, ticket = self.use(NOTE_A)
        self.assertEqual((status, ticket), (0, None), text)
        self.assertIn(f"学習済みの関数が答えた ({OP} の版 1)。", text)
        self.assertIn(json.dumps(PLAN, ensure_ascii=False, indent=2, sort_keys=True), text)
        self.assertIn("record は流さない", text)
        self.assertEqual((self.counts(), self.tickets()), (before, tickets))

    def test_n1_each_miss_names_its_reason(self) -> None:
        self.assertIn("(学習済みの版がまだ無い)", self.use()[1])
        self.publish(NOTE_A)
        self.assertIn("(関数がオフ)", self.use()[1])
        self.system.set_switch(CEMENT.PARTITION, OP, mode="follow", actor="test")
        self.assertIn("(関数にこの入力の場合が無い)", self.use(LAB)[1])
        real = System.resolve

        def failing(system: System, *args: Any, **kwargs: Any) -> Any:
            resolution = real(system, *args, **kwargs)
            verification = resolution.verification
            import dataclasses

            return dataclasses.replace(resolution, verification=dataclasses.replace(verification, passed=False))

        with mock.patch.object(System, "resolve", failing):
            self.assertIn("(関数の検証が通らなかった)", self.use()[1])

    def test_n1_a_broken_ledger_tells_the_model_to_answer_without_recording(self) -> None:
        self.home.mkdir(parents=True)
        (self.home / "ledger.db").write_bytes(b"not a ledger at all" * 100)
        status, text, ticket = self.use()
        self.assertEqual((status, ticket), (5, None), text)
        self.assertTrue(text.rstrip().endswith("次の手: Cement を使わずに自分で答える。record は流さない。"))
        self.assertEqual(self.tickets(), [])

    def test_n1_a_bad_operation_or_input_is_a_usage_refusal(self) -> None:
        status, text = self.run_cement("use", "bad name!", "--field", "document", stdin=NOTE_A)
        self.assertEqual(status, 2, text)
        status, text = self.run_cement("use", OP, stdin="{not json")
        self.assertEqual(status, 2, text)
        self.assertIn("入力が JSON として読めない", text)
        self.assertEqual(self.tickets(), [])

    def test_n2_record_consumes_its_ticket_once_with_source_and_provenance(self) -> None:
        _, _, ticket = self.use()
        status, text = self.run_cement("record", ticket, "--request", "どの項目?", stdin=json.dumps(PLAN))
        self.assertEqual(status, 0, text)
        (proposal,) = self.pending()
        self.assertEqual((proposal["input"], proposal["proposed_output"]), ({"document": NOTE_A.rstrip("\n")}, PLAN))
        self.assertEqual(
            proposal["provenance"],
            {"ticket": ticket, "used_at_us": self.now, "request": "どの項目?", "request_truncated": False},
        )
        with self.system.store.transaction() as connection:
            source = connection.execute("SELECT source_id FROM proposals").fetchone()[0]
        self.assertEqual(source, f"nucllei:{ticket}")
        self.assertEqual(self.tickets(), [])
        self.assertIn(f"記録した ({OP} の提案 {proposal['id']})。", text)
        self.assertTrue(text.rstrip().endswith("次の手: 返答を書く。"))
        before = self.counts()
        status, text = self.run_cement("record", ticket, stdin=json.dumps(PLAN))
        self.assertEqual(status, 3, text)
        self.assertIn("記録済みか", text)
        self.assertEqual(self.counts(), before)

    def test_n2_a_bad_ticket_or_output_writes_nothing_and_keeps_the_ticket(self) -> None:
        _, _, ticket = self.use()
        for argv, stdin in (
            (("record", "../tickets/x"), json.dumps(PLAN)),
            (("record", ticket), "not json"),
            (("record", ticket), "1.5"),
        ):
            with self.subTest(argv=argv, stdin=stdin):
                status, text = self.run_cement(*argv, stdin=stdin)
                self.assertEqual(status, 2, text)
        self.assertEqual((self.counts()[0], self.tickets()), (0, [ticket]))

    def test_n2_a_ticket_whose_source_is_retained_writes_no_second_proposal(self) -> None:
        _, _, ticket = self.use()
        path = self.home / "tickets" / f"{ticket}.json"
        kept = path.read_bytes()
        self.run_cement("record", ticket, stdin=json.dumps(PLAN))
        path.write_bytes(kept)
        status, text = self.run_cement("record", ticket, stdin=json.dumps(PLAN))
        self.assertEqual(status, 0, text)
        self.assertIn("記録済み", text)
        self.assertEqual((len(self.pending()), self.tickets()), (1, []))

    def test_n2_a_long_request_keeps_its_longest_start_within_the_bound(self) -> None:
        _, _, ticket = self.use()
        request = "頼" * 40_000
        status, text = self.run_cement("record", ticket, "--request", request, stdin=json.dumps(PLAN))
        self.assertEqual(status, 0, text)
        provenance = self.pending()[0]["provenance"]
        self.assertIs(provenance["request_truncated"], True)
        self.assertTrue(request.startswith(provenance["request"]))
        canonicalize(provenance, max_bytes=PROVENANCE_MAX_BYTES)
        longer = provenance | {"request": request[: len(provenance["request"]) + 1]}
        with self.assertRaises(ValueError):
            canonicalize(longer, max_bytes=PROVENANCE_MAX_BYTES)

    def test_n2_tickets_older_than_a_day_are_pruned_at_the_next_use(self) -> None:
        _, _, old = self.use()
        self.now += 24 * HOUR + 1
        _, _, new = self.use(NOTE_B)
        self.assertEqual(self.tickets(), [new])
        self.assertNotEqual(old, new)


class TriggerBattery(_Jail):
    def test_n3_the_second_answer_of_one_layout_asks_for_learning_before_the_reply(self) -> None:
        self.assertTrue(self.answer(NOTE_A).rstrip().endswith("次の手: 返答を書く。"))
        self.now += HOUR
        text = self.answer(NOTE_B, WIDER)
        self.assertIn("同じ場合の答えが 2 件そろった", text)
        self.assertTrue(
            text.rstrip().endswith(f"次の手: 返答を書く前に load_skill で cement-learn を読み込み、{OP} の学習を済ませる。")
        )

    def test_n3_an_exact_repeat_counts_once_within_ten_minutes_and_twice_hours_apart(self) -> None:
        self.answer(NOTE_A)
        self.now += 5 * MINUTE
        self.assertNotIn("cement-learn", self.answer(NOTE_A))
        self.run_cement("learn", OP, "--projectable", "no")
        self.now += 2 * HOUR
        self.assertIn("同じ場合の答えが 2 件そろった", self.answer(NOTE_A))

    def test_n3_no_learning_when_the_newest_version_already_gives_this_output(self) -> None:
        self.use()
        self.publish(NOTE_A)
        self.now += HOUR
        same = self.answer(NOTE_A)
        self.assertNotIn("cement-learn", same)
        self.now += HOUR
        self.assertIn("cement-learn", self.answer(NOTE_A, WIDER))

    def test_n3_a_pass_that_ruled_the_operation_not_projectable_groups_exactly(self) -> None:
        self.answer(NOTE_A)
        (proposal,) = self.pending()
        status, text = self.run_cement(
            "merge", OP, "--projectable", "no", "--proposals", proposal["id"], "--note", "values", stdin=json.dumps(PLAN)
        )
        self.assertEqual(status, 0, text)
        self.now += HOUR
        self.assertNotIn("cement-learn", self.answer(NOTE_B))
        self.assertEqual(json.loads((self.home / "state.json").read_text(encoding="utf-8")), {"projectable": {OP: False}})

    def test_n3_a_refused_merge_or_an_empty_publish_rules_nothing(self) -> None:
        """Live turns t2 + t4: a confused pass ran a refused `merge --projectable no` and an empty
        `publish --projectable no`; storing that choice silenced every later layout trigger."""

        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(NOTE_B)
        ids = ",".join(p["id"] for p in self.pending())
        status, _ = self.run_cement("merge", OP, "--projectable", "no", "--proposals", ids, "--note", "n", stdin=json.dumps(PLAN))
        self.assertEqual(status, 2)
        status, text = self.run_cement("publish", OP, "--projectable", "no")
        self.assertIn("版を作らなかった", text)
        self.assertFalse((self.home / "state.json").exists())
        self.now += HOUR
        self.assertIn("同じ場合の答えが 3 件そろった", self.answer(NOTE_C))

    def test_n3_a_damaged_state_file_reads_as_no_ruling(self) -> None:
        self.answer(NOTE_A)
        for damaged in ('{"projectable": ["x"]}', "[1]", "not json"):
            with self.subTest(damaged=damaged):
                (self.home / "state.json").write_text(damaged, encoding="utf-8")
                self.assertIsNone(CEMENT._projectable_state(OP))
        self.now += HOUR
        self.assertIn("同じ場合の答えが 2 件そろった", self.answer(NOTE_B))

    def test_n4_the_work_list_flags_a_regenerated_reply(self) -> None:
        self.answer(NOTE_A)
        first = self.pending()[0]["id"]
        self.now += 2 * MINUTE
        self.answer(NOTE_A)
        second = next(p["id"] for p in self.pending() if p["id"] != first)
        status, text = self.run_cement("learn", OP, "--projectable", "no")
        self.assertEqual(status, 0, text)
        work = json.loads(text.split("\n", 1)[1])
        (case,) = work["cases"]
        self.assertEqual(case["regeneration_suspects"], [second])
        self.assertEqual(sorted(case["pending_proposal_ids"]), sorted([first, second]))


class LearningBattery(_Jail):
    def work(self, projectable: str) -> dict[str, Any]:
        status, text = self.run_cement("learn", OP, "--projectable", projectable)
        self.assertEqual(status, 0, text)
        return json.loads(text.split("\n", 1)[1])

    def test_n5_a_projectable_pass_merges_publishes_and_never_switches_on(self) -> None:
        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(NOTE_B, WIDER)
        self.assertEqual(len(self.work("no")["cases"]), 2)
        grouped = self.work("yes")
        self.assertEqual(grouped["layouts"], ["PHYSICIAN PROGRESS NOTE"])
        (case,) = grouped["cases"]
        ids = ",".join(case["pending_proposal_ids"])
        status, text = self.run_cement(
            "merge", OP, "--projectable", "yes", "--proposals", ids, "--note", "kept mrn", stdin=json.dumps(WIDER)
        )
        self.assertEqual(status, 0, text)
        merged = json.loads(text.split("\n", 1)[1])
        self.assertEqual(sorted(r["status"] for r in merged["reviewed"]), ["accepted", "corrected"])
        status, text = self.run_cement("publish", OP, "--projectable", "yes")
        self.assertEqual(status, 0, text)
        self.assertIn(f"新しい版を作った: {OP} の版 1 (場合 1 件、", text)
        self.assertIn("用紙の形: PHYSICIAN PROGRESS NOTE", text)
        self.assertIn("/cement-switch でオンにするまで答えない", text)
        self.assertEqual(self.system.switch(CEMENT.PARTITION, OP).mode, "off")
        self.system.set_switch(CEMENT.PARTITION, OP, mode="follow", actor="test")
        self.assertEqual(self.system.resolve(CEMENT.PARTITION, OP, {"document": NOTE_C.rstrip("\n")}).match.output, WIDER)
        status, text = self.run_cement("publish", OP, "--projectable", "yes")
        self.assertIn("版を作らなかった (最新の版が既に同じ中身を持つ)", text)
        reviewers = {p["reviewer"] for p in self.system.proposals(CEMENT.PARTITION, status="all")}
        self.assertEqual(reviewers, {"learning-pass"})

    def test_n5_an_empty_examples_or_proposals_value_reads_as_no_ids(self) -> None:
        """Live turn 2: the model passed `--examples` with no value for a case without examples."""

        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(NOTE_B, WIDER)
        (case,) = self.work("yes")["cases"]
        ids = ",".join(case["pending_proposal_ids"])
        status, text = self.run_cement(
            "merge", OP, "--projectable", "yes", "--proposals", ids, "--examples", "--note", "n", stdin=json.dumps(WIDER)
        )
        self.assertEqual(status, 0, text)
        (case,) = self.work("yes")["cases"]
        examples = ",".join(case["active_example_ids"])
        status, text = self.run_cement(
            "merge", OP, "--projectable", "yes", "--proposals", "", "--examples", examples, "--note", "n",
            stdin=json.dumps(WIDER),
        )
        self.assertEqual(status, 0, text)
        status, text = self.run_cement("merge", OP, "--projectable", "yes", "--proposals", "--note", "n", stdin=json.dumps(WIDER))
        self.assertEqual(status, 2, text)
        self.assertIn("1 つの場合の id を渡していない", text)

    def test_n5_a_projectable_publish_without_confirmed_examples_reports_empty(self) -> None:
        """Live turn 2: `publish --projectable yes` before any merge named the projection's input rule."""

        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(NOTE_B)
        status, text = self.run_cement("publish", OP, "--projectable", "yes")
        self.assertEqual(status, 0, text)
        self.assertIn("版を作らなかった (確認が 2 件そろった場合がまだ無い)", text)
        self.assertIsNone(self.system.projection(CEMENT.PARTITION, OP))

    def test_n5_a_pass_without_two_confirmations_publishes_nothing(self) -> None:
        self.answer(NOTE_A)
        status, text = self.run_cement("publish", OP, "--projectable", "no")
        self.assertEqual(status, 0, text)
        self.assertIn("版を作らなかった (確認が 2 件そろった場合がまだ無い)", text)

    def test_n5_merge_refuses_two_cases_repeated_ids_and_no_ids_before_any_write(self) -> None:
        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(LAB)
        note, lab = (p["id"] for p in self.pending())
        before = self.counts()
        for ids in (f"{note},{lab}", f"{note},{note}"):
            with self.subTest(ids=ids):
                status, text = self.run_cement(
                    "merge", OP, "--projectable", "yes", "--proposals", ids, "--note", "n", stdin=json.dumps(PLAN)
                )
                self.assertEqual(status, 2, text)
        status, text = self.run_cement("merge", OP, "--projectable", "yes", "--note", "n", stdin=json.dumps(PLAN))
        self.assertEqual(status, 2, text)
        self.assertEqual(self.counts(), before)

    def test_n5_a_failure_after_a_write_reports_the_writes(self) -> None:
        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(NOTE_B)
        ids = [p["id"] for p in self.pending()]
        real = System.review
        calls: list[str] = []

        def review(system: System, *args: Any, **kwargs: Any) -> Any:
            calls.append(args[1])
            if len(calls) == 2:
                raise StateError("ledger busy")
            return real(system, *args, **kwargs)

        with mock.patch.object(System, "review", review):
            status, text = self.run_cement(
                "merge", OP, "--projectable", "yes", "--proposals", ",".join(ids), "--note", "n", stdin=json.dumps(PLAN)
            )
        self.assertEqual(status, 4, text)
        self.assertIn("中止: 途中で止まった (ledger busy)", text)
        self.assertIn(f'"proposal_id": "{calls[0]}"', text)
        self.assertEqual(self.system.proposal(CEMENT.PARTITION, calls[0])["status"], "accepted")

    def test_n5_reject_revoke_and_show_act_as_the_learning_pass(self) -> None:
        self.answer(NOTE_A)
        self.now += HOUR
        self.answer(NOTE_B, {"x": 1})
        kept, dropped = (p["id"] for p in self.pending())
        status, text = self.run_cement("show", dropped)
        self.assertEqual(status, 0, text)
        self.assertEqual(json.loads(text.split("\n", 1)[1])["proposed_output"], {"x": 1})
        status, text = self.run_cement("reject", dropped, "--note", "not a plan")
        self.assertEqual(status, 0, text)
        record = self.system.proposal(CEMENT.PARTITION, dropped)
        self.assertEqual((record["status"], record["reviewer"], record["review_note"]), ("rejected", "learning-pass", "not a plan (nucllei)"))
        self.run_cement("merge", OP, "--projectable", "no", "--proposals", kept, "--note", "ok", stdin=json.dumps(PLAN))
        (example,) = [e["id"] for e in self.system.examples(CEMENT.PARTITION, OP)]
        status, text = self.run_cement("revoke", example, "--reason", "wrong label")
        self.assertEqual(status, 0, text)
        revoked = [e for e in self.system.events(CEMENT.PARTITION) if e["kind"] == "example.revoked"]
        self.assertEqual(len(revoked), 1)

    def test_n5_learning_steps_without_a_ledger_are_absent_and_create_nothing(self) -> None:
        for argv in (("learn", OP, "--projectable", "no"), ("status",), ("publish", OP, "--projectable", "no")):
            with self.subTest(argv=argv):
                status, text = self.run_cement(*argv)
                self.assertEqual(status, 3, text)
                self.assertIn("Cement の台帳がまだ無い", text)
        self.assertFalse((self.home / "ledger.db").exists())


class StateFileBattery(_Jail):
    def test_two_concurrent_passes_keep_both_projectability_rulings(self) -> None:
        # Each worker reads the state file, then waits until the other has read too (a barrier
        # with a timeout, so a serialized read-modify-write still finishes): without the lock the
        # later write drops the earlier ruling.
        import multiprocessing
        import threading

        self.home.mkdir(parents=True)
        context = multiprocessing.get_context("fork")
        barrier = context.Barrier(2)
        read_state = CEMENT._state

        def read_then_wait() -> dict[str, Any]:
            state = read_state()
            with contextlib.suppress(threading.BrokenBarrierError):
                barrier.wait(timeout=1)
            return state

        def remember(operation: str, value: bool) -> None:
            with mock.patch.object(CEMENT, "_state", read_then_wait):
                os._exit(0 if CEMENT._remember(operation, value) == [] else 1)

        workers = [
            context.Process(target=remember, args=(operation, value))
            for operation, value in (("operation_a", False), ("operation_b", True))
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(
            json.loads((self.home / "state.json").read_text(encoding="utf-8"))["projectable"],
            {"operation_a": False, "operation_b": True},
        )


class JapaneseOutputBattery(_Jail):
    """The model reads every line the command prints, argparse's own refusals + help included."""

    def test_a_malformed_command_line_refuses_in_llens_style(self) -> None:
        for argv in (["use"], ["switch", OP, "sideways"], ["no-such-command"]):
            with self.subTest(argv=argv):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    with self.assertRaises(SystemExit) as stop:
                        CEMENT.main(argv)
                self.assertEqual(stop.exception.code, 2)
                lines = out.getvalue().splitlines()
                self.assertTrue(lines[0].startswith("中止: コマンドの書き方が違う ("), lines)
                self.assertEqual(lines[-1], CEMENT.NEXT[2])
                self.assertEqual(err.getvalue(), "")

    def test_every_help_text_is_japanese(self) -> None:
        parser = CEMENT._parser()
        subparsers = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        texts = [parser.description] + [
            text
            for name, sub in subparsers.choices.items()
            for text in [sub.description, *(a.help for a in sub._actions if a.help and a.dest != "help")]
        ]
        for text in texts:
            with self.subTest(text=text):
                self.assertRegex(str(text), "[\u3040-\u30ff\u4e00-\u9fff]")

    def test_follow_before_any_version_says_the_model_answers(self) -> None:
        self.run_cement("use", OP, "--field", "document", stdin=NOTE_A)
        status, text = self.run_cement("switch", OP, "follow")
        self.assertEqual(status, 0, text)
        self.assertIn("まだ版が無いので、版が公開されるまでモデルが答える。", text)
        self.assertNotIn("版 0", text)


class HandOverBattery(_Jail):
    """Documents and model answers reach the command as files under `$CEMENT_HOME/in/`, never as
    shell text (a heredoc ends at a line equal to its delimiter and runs the rest); each command
    deletes its hand-over file once the ledger or the ticket holds the content."""

    def handed(self, name: str, text: str) -> pathlib.Path:
        (self.home / "in").mkdir(parents=True, exist_ok=True)
        path = self.home / "in" / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_use_deletes_its_hand_over_file_and_keeps_any_other(self) -> None:
        inside = self.handed("plan-1.txt", NOTE_A)
        status, text = self.run_cement("use", OP, "--field", "document", "--input-file", str(inside))
        self.assertEqual(status, 0, text)
        self.assertFalse(inside.exists())
        outside = self.home.parent / "plan-2.txt"
        outside.write_text(NOTE_B, encoding="utf-8")
        self.run_cement("use", OP, "--field", "document", "--input-file", str(outside))
        self.assertTrue(outside.exists())

    def test_record_and_merge_read_an_answer_file_and_delete_it_after_the_write(self) -> None:
        tickets = []
        for document in (NOTE_A, NOTE_B):
            _, _, ticket = self.use(document)
            tickets.append(ticket)
        for index, ticket in enumerate(tickets):
            answer = self.handed(f"answer-{index}.json", json.dumps(PLAN))
            status, text = self.run_cement(
                "record", str(ticket), "--request", "plan", "--output-file", str(answer)
            )
            self.assertEqual(status, 0, text)
            self.assertFalse(answer.exists())
        work = json.loads(self.run_cement("learn", OP, "--projectable", "yes")[1].split("\n", 1)[1])
        (case,) = work["cases"]
        merged = self.handed("merge-1.json", json.dumps(PLAN))
        status, text = self.run_cement(
            "merge", OP, "--projectable", "yes", "--proposals", ",".join(case["pending_proposal_ids"]),
            "--note", "n", "--output-file", str(merged),
        )
        self.assertEqual(status, 0, text)
        self.assertFalse(merged.exists())

    def test_a_refused_record_keeps_its_answer_file_for_the_retry(self) -> None:
        _, _, ticket = self.use(NOTE_A)
        answer = self.handed("answer-1.json", json.dumps(PLAN))
        with mock.patch.object(System, "submit_proposal", side_effect=StateError("busy")):
            status, _ = self.run_cement("record", str(ticket), "--request", "p", "--output-file", str(answer))
        self.assertEqual(status, 4)
        self.assertTrue(answer.exists())

    def test_the_skills_hand_every_document_and_answer_over_as_a_file(self) -> None:
        for name, command in (("cement", "record"), ("cement-learn", "merge")):
            with self.subTest(skill=name):
                _, text = _front(name)
                self.assertNotIn("<<", text)
                self.assertRegex(text, rf"/ext/bin/cement {command} .*--output-file /workspace/\.cement/in/")


class SwitchBattery(_Jail):
    def two_versions(self) -> None:
        self.use()
        self.publish(NOTE_A)
        self.now += HOUR
        self.publish(NOTE_A, LAB)

    def test_n6_the_person_switches_on_pins_and_switches_off(self) -> None:
        self.two_versions()
        status, text = self.run_cement("status")
        self.assertEqual(status, 0, text)
        self.assertIn("- 版 2: 場合 2 件", text)
        self.assertIn("- 版 1: 場合 1 件", text)
        self.assertIn("スイッチ: オフ", text)
        status, text = self.run_cement("switch", OP, "follow")
        self.assertEqual(status, 0, text)
        self.assertIn("最新の版 (いまは版 2) が答える", text)
        self.assertIn(f"({OP} の版 2)", self.use(LAB)[1])
        status, text = self.run_cement("switch", OP, "pin", "1")
        self.assertEqual(status, 0, text)
        self.assertIn("(関数にこの入力の場合が無い)", self.use(LAB)[1])
        self.assertIn(f"({OP} の版 1)", self.use(NOTE_A)[1])
        self.assertIn("スイッチ: 版 1 に固定", self.run_cement("versions", OP)[1])
        self.run_cement("switch", OP, "off")
        self.assertIn("(関数がオフ)", self.use(NOTE_A)[1])
        actors = [
            e["payload"]["set_by"] for e in self.system.events(CEMENT.PARTITION)
            if e["kind"] == "function.switched"
        ]
        self.assertEqual(actors, ["nucllei-user"] * 3)

    def test_n6_a_pin_needs_one_existing_version_number(self) -> None:
        self.two_versions()
        for argv, code in ((("switch", OP, "pin"), 2), (("switch", OP, "pin", "9"), 3), (("switch", OP, "follow", "1"), 2)):
            with self.subTest(argv=argv):
                status, text = self.run_cement(*argv)
                self.assertEqual(status, code, text)
        self.assertEqual(self.system.switch(CEMENT.PARTITION, OP).mode, "off")

    def test_n6_read_and_diff_show_one_version_and_what_changed(self) -> None:
        self.two_versions()
        status, text = self.run_cement("read", OP)
        self.assertEqual(status, 0, text)
        self.assertIn(f"{OP} の版 2 の中身 (場合 2 件、", text)
        self.assertIn('"Patient: A\\nPotassium: 4.2"', text.replace("LAB RESULT SLIP\\n", ""))
        self.assertIn("コードではない", text)
        status, text = self.run_cement("diff", OP, "1", "2")
        self.assertEqual(status, 0, text)
        self.assertIn("足した場合 1 件、消えた場合 0 件、出力が変わった場合 0 件", text)

    def test_n6_only_the_switch_command_sets_the_switch(self) -> None:
        tree = ast.parse((EXAMPLE / "cement_nucllei.py").read_text(encoding="utf-8"))
        owners: dict[str, set[str]] = {}
        for function in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
            for node in ast.walk(function):
                if isinstance(node, ast.Attribute):
                    owners.setdefault(node.attr, set()).add(function.name)
        self.assertEqual(owners["set_switch"], {"_switch"})
        self.assertEqual(owners["register_operation"], {"_registered"})
        self.assertNotIn("revise_operation", owners)


class ReviewBattery(_Jail):
    """reviewer-1 findings on e325bdc (F1-F4) + MAIN's G3 ruling, each red on that revision."""

    def test_f1_an_expired_ticket_is_refused_without_a_write(self) -> None:
        _, _, ticket = self.use()
        self.now += CEMENT.TICKET_TTL_US + 1
        before = self.counts()
        status, text = self.run_cement("record", ticket, stdin=json.dumps(PLAN))
        self.assertEqual(status, 3, text)
        self.assertIn("24 時間", text)
        self.assertEqual((self.counts(), self.tickets()), (before, []))

    def test_f1_a_ticket_exactly_one_day_old_still_records(self) -> None:
        _, _, ticket = self.use()
        self.now += CEMENT.TICKET_TTL_US
        status, text = self.run_cement("record", ticket, stdin=json.dumps(PLAN))
        self.assertEqual(status, 0, text)
        self.assertEqual(len(self.pending()), 1)

    def test_f2_a_merge_whose_state_write_fails_reports_its_reviews(self) -> None:
        self.answer(NOTE_A)
        (proposal,) = self.pending()
        (self.home / "state.json").mkdir()
        status, text = self.run_cement(
            "merge", OP, "--projectable", "no", "--proposals", proposal["id"], "--note", "n", stdin=json.dumps(PLAN)
        )
        self.assertEqual(status, 0, text)
        self.assertIn(proposal["id"], text)
        self.assertIn("場合をまとめた。", text)
        self.assertEqual(self.system.proposal(CEMENT.PARTITION, proposal["id"])["status"], "accepted")

    def test_f2_a_record_whose_ticket_cleanup_fails_reports_the_proposal(self) -> None:
        _, _, ticket = self.use()
        real = pathlib.Path.unlink

        def denied(path: pathlib.Path, *args: Any, **kwargs: Any) -> None:
            if path.name == f"{ticket}.json":
                raise PermissionError("ticket directory became unwritable")
            real(path, *args, **kwargs)

        with mock.patch.object(pathlib.Path, "unlink", denied):
            status, text = self.run_cement("record", ticket, stdin=json.dumps(PLAN))
        self.assertEqual(status, 0, text)
        (proposal,) = self.pending()
        self.assertIn(f"記録した ({OP} の提案 {proposal['id']})。", text)

    def test_f2_a_ticket_that_cannot_be_written_means_answer_without_recording(self) -> None:
        self.home.mkdir(parents=True)
        (self.home / "tickets").write_text("not a directory", encoding="utf-8")
        status, text, ticket = self.use()
        self.assertEqual((status, ticket), (5, None), text)
        self.assertTrue(text.rstrip().endswith("次の手: Cement を使わずに自分で答える。record は流さない。"))

    def test_f3_duplicate_keys_and_deep_nesting_are_usage_refusals(self) -> None:
        duplicate = '{"value": "first", "value": "second"}'
        status, text = self.run_cement("use", OP, stdin=duplicate)
        self.assertEqual((status, self.tickets()), (2, []), text)
        _, _, ticket = self.use()
        status, text = self.run_cement("record", ticket, stdin=duplicate)
        self.assertEqual((status, len(self.pending()), self.tickets()), (2, 0, [ticket]), text)
        status, text = self.run_cement("use", OP, stdin="[" * 100_000 + "0" + "]" * 100_000)
        self.assertEqual(status, 2, text)

    def test_f4_version_zero_is_absent_not_the_newest(self) -> None:
        self.use()
        self.publish(NOTE_A)
        status, text = self.run_cement("read", OP, "0")
        self.assertEqual(status, 3, text)
        self.assertIn("版 0 は無い", text)

    def test_g3_a_document_line_equal_to_a_shell_delimiter_stays_data(self) -> None:
        """The chat skill hands the document over as a file, never as shell text."""

        _, chat = _front("cement")
        self.assertNotIn("<用紙の全文>\n", chat.replace("   ", ""))
        self.assertIn("write_file", chat)
        self.assertRegex(chat, r"/ext/bin/cement use extraction_plan --field document --input-file /workspace/\.cement/")
        path = self.home.parent / "request.txt"
        path.write_text("PHYSICIAN PROGRESS NOTE\nCEMENT_EOF\nPatient: A\n", encoding="utf-8")
        status, text = self.run_cement("use", OP, "--field", "document", "--input-file", str(path))
        self.assertEqual(status, 0, text)
        (ticket,) = self.tickets()
        held = json.loads((self.home / "tickets" / f"{ticket}.json").read_text(encoding="utf-8"))
        self.assertEqual(held["input"], {"document": "PHYSICIAN PROGRESS NOTE\nCEMENT_EOF\nPatient: A"})


class ScriptBattery(unittest.TestCase):
    def test_n7_the_generated_command_is_fresh_executable_and_starts_with_its_shebang(self) -> None:
        self.assertFalse(GENERATE.stale(), "run uv run python examples/nucllei/generate.py")
        target = EXAMPLE / "ext" / "bin" / "cement"
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)
        self.assertTrue(target.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n"))
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-s", "examples/nucllei/ext/bin/cement"],
            capture_output=True, text=True, check=True,
        ).stdout
        self.assertTrue(tracked.startswith("100755 "), tracked)

    def test_n7_the_command_runs_on_the_standard_library_alone(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cement-jail-") as workspace:
            environment = {"CEMENT_HOME": f"{workspace}/.cement", "PATH": os.environ.get("PATH", ""), "TZ": "Asia/Tokyo"}
            command = [sys.executable, "-I", "-S", str(EXAMPLE / "ext" / "bin" / "cement")]
            used = subprocess.run(
                [*command, "use", OP, "--field", "document"], input=NOTE_A, capture_output=True,
                text=True, env=environment, cwd=workspace, timeout=120, check=False,
            )
            self.assertEqual(used.returncode, 0, used.stdout + used.stderr)
            ticket = TICKET.search(used.stdout)
            assert ticket is not None
            recorded = subprocess.run(
                [*command, "record", ticket.group(1)], input=json.dumps(PLAN), capture_output=True,
                text=True, env=environment, cwd=workspace, timeout=120, check=False,
            )
            self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
            self.assertIn("記録した", recorded.stdout)
            self.assertEqual(recorded.stderr, "")

    def test_n7_an_edited_embedded_library_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cement-jail-") as workspace:
            copy = pathlib.Path(workspace) / "cement"
            text = (EXAMPLE / "ext" / "bin" / "cement").read_text(encoding="utf-8")
            marker = 'MIN_SQLITE = (3, 37, 0)'
            self.assertEqual(text.count(marker), 1)
            copy.write_text(text.replace(marker, 'MIN_SQLITE = (3, 36, 0)'), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, "-I", "-S", str(copy), "status"], capture_output=True, text=True,
                env={"CEMENT_HOME": f"{workspace}/.cement"}, cwd=workspace, timeout=120, check=False,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("the embedded cement_runtime was edited; copy ext/bin/cement from the repository again", run.stderr)


def _front(name: str) -> tuple[dict[str, str], str]:
    text = (EXAMPLE / "skills" / f"{name}.md").read_text(encoding="utf-8")
    found = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert found is not None, name
    fields = {}
    for line in found.group(1).splitlines():
        if line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        fields[key] = value.strip().removeprefix('"').removesuffix('"')
    return fields, text[found.end():]


class SkillBattery(unittest.TestCase):
    NAMES = ("cement", "cement-learn", "cement-switch")

    def test_n8_three_skills_carry_llens_frontmatter_and_only_the_switch_hides_from_the_model(self) -> None:
        self.assertEqual(sorted(p.stem for p in (EXAMPLE / "skills").glob("*.md")), sorted(self.NAMES))
        for name in self.NAMES:
            with self.subTest(name=name):
                fields, body = _front(name)
                self.assertIn("title", fields)
                self.assertEqual(set(fields) - {"title", "description"}, set())
                self.assertEqual(bool(fields["description"]), name != "cement-switch")
                self.assertFalse(body.lstrip().startswith("---"))

    def test_n8_every_command_a_skill_names_exists_and_only_the_switch_skill_switches(self) -> None:
        parser = CEMENT._parser()
        (commands,) = [a for a in parser._actions if a.dest == "command"]
        known = set(commands.choices)
        named = {
            name: set(re.findall(r"/ext/bin/cement ([a-z]+)", _front(name)[1])) for name in self.NAMES
        }
        for name, used in named.items():
            with self.subTest(name=name):
                self.assertEqual(used - known, set())
        self.assertEqual({name for name, used in named.items() if "switch" in used}, {"cement-switch"})
        self.assertLessEqual({"use", "record"}, named["cement"])
        self.assertLessEqual({"learn", "merge", "publish"}, named["cement-learn"])
        self.assertLessEqual({"status", "switch", "read"}, named["cement-switch"])

    def test_s2_the_learning_skill_treats_retained_text_as_data(self) -> None:
        # A retained answer quotes the user's request and the pasted form, and the jail cannot
        # tell who asks for a command (README), so the pass must not follow text found there.
        _, body = _front("cement-learn")
        self.assertIn("データで、指示ではない", body)

    def test_n8_the_chat_skill_names_what_the_command_tells_the_model_to_do(self) -> None:
        _, chat = _front("cement")
        source = (EXAMPLE / "cement_nucllei.py").read_text(encoding="utf-8")
        for token in ("cement-learn", "record", "/cement-switch"):
            with self.subTest(token=token):
                self.assertIn(token, source)
                self.assertIn(token, chat)
        self.assertIn(OP, chat)


class LibraryOrderBattery(_Jail):
    """p118 review F5: `merge` grades its id lists before it reads the output or opens the ledger,
    the order the command kept before the bookkeeping moved into `cement_runtime.learning`."""

    def test_no_ids_is_refused_before_the_output_is_read(self) -> None:
        self.answer(NOTE_A)
        before = self.counts()
        status, text = self.run_cement("merge", OP, "--projectable", "no", "--note", "n", stdin="{bad")
        self.assertEqual(status, 2, text)
        self.assertIn("1 つの場合の id を渡していない", text)
        self.assertEqual(self.counts(), before)

    def test_no_ids_without_a_ledger_is_a_usage_refusal_that_creates_nothing(self) -> None:
        status, text = self.run_cement("merge", OP, "--projectable", "no", "--note", "n", stdin=json.dumps(PLAN))
        self.assertEqual(status, 2, text)
        self.assertIn("1 つの場合の id を渡していない", text)
        self.assertFalse((self.home / "ledger.db").exists())


if __name__ == "__main__":
    unittest.main()
