"""M5.3 battery — the Open WebUI example: a read-only tool + the filter as the single writer.

Contract: `.agent/decisions/m45-contract.md` §7 (E1-E4). Open WebUI is not a dependency: the
modules import `pydantic` for their valves alone, so a minimal stub stands in for it here and the
real 0.12.3 loop is the unit's recorded smoke.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import pathlib
import sys
import tempfile
import types
import unittest
from typing import Any
from unittest import mock

from cement_runtime import Candidate, CompilePolicy, StateError, System
from cement_runtime.json_value import canonicalize
from cement_runtime.system import PROVENANCE_MAX_BYTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, OP = "tenant_a", "extraction_plan"
POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
DOC = {"document": "PHYSICIAN PROGRESS NOTE\nPatient: A\n"}
PLAN = {"fields": ["patient"]}


def _pydantic() -> types.ModuleType:
    module = types.ModuleType("pydantic")

    class FieldInfo:
        def __init__(self, default: object = None, description: str = "") -> None:
            self.default = default

    class BaseModel:
        def __init__(self, **values: object) -> None:
            for name in type(self).__annotations__:
                default = getattr(type(self), name, None)
                if isinstance(default, FieldInfo):
                    default = default.default
                setattr(self, name, values.get(name, default))

    module.BaseModel = BaseModel  # type: ignore[attr-defined]
    module.Field = FieldInfo  # type: ignore[attr-defined]
    return module


def _load(name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"open_webui_example_{name}", ROOT / "examples/open_webui" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"pydantic": _pydantic()}):
        spec.loader.exec_module(module)
    return module


TOOLS = _load("cement_tools")
FILTER = _load("cement_filter")


def _call(call_id: str, name: str, arguments: dict[str, Any], result: object) -> list[dict[str, Any]]:
    return [
        {"type": "function_call", "id": call_id, "call_id": call_id, "name": name,
         "arguments": json.dumps(arguments), "status": "completed"},
        {"type": "function_call_output", "id": f"fco_{call_id}", "call_id": call_id,
         "output": [{"type": "input_text", "text": json.dumps(result)}], "status": "completed"},
    ]


class _Example(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-owui-")
        self.addCleanup(directory.cleanup)
        self.db = str(pathlib.Path(directory.name) / "ledger.db")
        self.system = System(self.db)
        self.system.register_operation(P, OP, policy=POLICY)
        self.tools = TOOLS.Tools()
        self.tools.valves = TOOLS.Tools.Valves(ledger_path=self.db, partition=P, operations=OP)
        self.filter = FILTER.Filter()
        self.filter.valves = FILTER.Filter.Valves(
            ledger_path=self.db, partition=P, deployment_id="ward-7", operations=OP
        )
        self.notes: list[dict[str, Any]] = []

    def _publish(self, value: object = DOC, output: object = PLAN) -> None:
        for _ in range(2):
            proposal = self.system.submit_proposal(
                P, OP, value, candidate=Candidate(output=output, provenance={})
            )
            self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        self.system.compile(P, OP)
        self.system.verify_drafts(P, OP, verified_by="learning-pass")
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )

    def _use(self, value: object = DOC) -> dict[str, Any]:
        return asyncio.run(self.tools.use_learned_function(OP, value))

    def _counts(self) -> tuple[int, int]:
        with self.system.store.transaction() as connection:
            return (
                connection.execute("SELECT COUNT(*) FROM proposals").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            )

    def _outlet(self, output: list[dict[str, Any]], *, history: list[dict[str, Any]] | None = None,
                message_id: str = "msg-a", user_message_id: str = "msg-u",
                metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {
            "model": "stub-model",
            "chat_id": "chat-1",
            "id": message_id,
            "messages": [
                *(history or []),
                {"id": user_message_id, "role": "user", "content": "plan this note"},
                {"id": message_id, "role": "assistant", "content": "Here is the plan.", "output": output},
            ],
        }

        async def emit(event: dict[str, Any]) -> None:
            self.notes.append(event)

        returned = asyncio.run(
            self.filter.outlet(
                body,
                __event_emitter__=emit,
                __metadata__={"user_message_id": user_message_id} if metadata is None else metadata,
            )
        )
        self.assertIs(returned, body)
        return body


class ToolBattery(_Example):
    def test_e1_a_covered_request_returns_the_function_output(self) -> None:
        self._publish()
        self.system.set_switch(P, OP, mode="follow", actor="person")
        answer = self._use()
        self.assertEqual((answer["covered"], answer["output"]), (True, PLAN))
        self.assertEqual(answer["function_hash"], self.system.resolve(P, OP, DOC).verification.function_hash)

    def test_e1_each_uncovered_state_names_its_reason(self) -> None:
        self.assertEqual(self._use()["reason"], "off")
        self.system.set_switch(P, OP, mode="follow", actor="person")
        self.assertEqual(self._use()["reason"], "absent")
        self._publish()
        self.assertEqual(self._use({"document": "LAB RESULT SLIP\n"})["reason"], "unrecognized")
        proposal = self.system.submit_proposal(
            P, OP, DOC, candidate=Candidate(output={"fields": []}, provenance={})
        )
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        failed = self._use()
        self.assertEqual((failed["covered"], failed["reason"]), (False, "failed"))
        self.assertIn("record_answer", failed["instruction"])

    def test_e1_a_missing_ledger_or_a_disabled_operation_answers_nothing(self) -> None:
        self.tools.valves.ledger_path = self.db + ".absent"
        self.assertEqual(self._use()["reason"], "failed")
        self.assertFalse(pathlib.Path(self.db + ".absent").exists())
        self.tools.valves.ledger_path = self.db
        disabled = asyncio.run(self.tools.use_learned_function("billing_codes", DOC))
        self.assertEqual((disabled["covered"], disabled["reason"]), (False, "invalid"))

    def test_e2_record_answer_validates_and_writes_nothing(self) -> None:
        before = self._counts()
        accepted = asyncio.run(self.tools.record_answer(OP, DOC, PLAN))
        self.assertEqual(accepted, {"accepted": True})
        for operation, value, output in (("billing_codes", DOC, PLAN), (OP, DOC, {"x": float("nan")})):
            self.assertFalse(asyncio.run(self.tools.record_answer(operation, value, output))["accepted"])
        self.assertEqual(self._counts(), before)


class FilterBattery(_Example):
    def _miss(self) -> dict[str, Any]:
        return {"covered": False, "reason": "off", "instruction": "..."}

    def test_e2_one_valid_pair_writes_one_proposal_and_a_repeat_delivery_writes_none(self) -> None:
        output = _call("c1", "use_learned_function", {"operation": OP, "input": DOC}, self._miss())
        output += _call("c2", "record_answer", {"operation": OP, "input": DOC, "output": PLAN}, {"accepted": True})
        before = self._counts()
        self._outlet(output)
        self.assertEqual(self._counts(), (before[0] + 1, before[1] + 1))
        (row,) = self.system.proposals(P)
        self.assertEqual((row["input"], row["proposed_output"]), (DOC, PLAN))
        self.assertEqual(row["provenance"]["reply"], "Here is the plan.")
        self.assertEqual(
            (row["provenance"]["use_call_id"], row["provenance"]["record_call_id"]), ("c1", "c2")
        )
        self._outlet(output)
        self._outlet(output, message_id="msg-regenerated")
        # `/api/chat/completed` re-runs the outlet without `user_message_id` in its metadata: the
        # source id must come from the body's own user message, or the repeat counts twice.
        self._outlet(output, metadata={})
        self.assertEqual(self._counts(), (before[0] + 1, before[1] + 1))
        self.assertEqual(self.notes, [])

    def test_e3_a_covered_record_an_unpaired_record_and_a_malformed_one_write_nothing(self) -> None:
        covered = _call("c1", "use_learned_function", {"operation": OP, "input": DOC},
                        {"covered": True, "output": PLAN, "function_hash": "0" * 64})
        record = _call("c2", "record_answer", {"operation": OP, "input": DOC, "output": PLAN}, {"accepted": True})
        malformed = [{"type": "function_call", "call_id": "c3", "name": "record_answer", "arguments": "{"}]
        before = self._counts()
        for output in (covered + record, record, malformed):
            with self.subTest(calls=[item.get("call_id") for item in output]):
                self.notes.clear()
                self._outlet(output)
                self.assertEqual(self._counts(), before)
                self.assertEqual(len(self.notes), 1)
                self.assertEqual(self.notes[0]["type"], "notification")

    def test_e4_only_the_current_message_counts_and_a_lone_miss_is_flagged(self) -> None:
        old = _call("h1", "use_learned_function", {"operation": OP, "input": DOC}, self._miss())
        old += _call("h2", "record_answer", {"operation": OP, "input": DOC, "output": PLAN}, {"accepted": True})
        history = [{"id": "msg-old", "role": "assistant", "content": "earlier", "output": old}]
        before = self._counts()
        self._outlet(_call("c1", "use_learned_function", {"operation": OP, "input": DOC}, self._miss()),
                     history=history)
        self.assertEqual(self._counts(), before)
        self.assertEqual(len(self.notes), 1)
        self.assertIn("without record_answer", self.notes[0]["data"]["content"])

    def test_e4_the_outlet_never_raises(self) -> None:
        output = _call("c1", "use_learned_function", {"operation": OP, "input": DOC}, self._miss())
        output += _call("c2", "record_answer", {"operation": OP, "input": DOC, "output": PLAN}, {"accepted": True})
        self.filter.valves.ledger_path = self.db + ".absent"
        self._outlet(output)
        self.assertFalse(pathlib.Path(self.db + ".absent").exists())
        self.assertEqual(len(self.notes), 1)
        for body in ({}, {"messages": "not a list", "id": 1}, {"messages": [None, 5], "id": "x"}):
            with self.subTest(body=body):
                self.assertIs(asyncio.run(self.filter.outlet(body)), body)



class CaptureBindingBattery(FilterBattery):
    """§7 capture binding (X6) + E3/E4 boundaries: what one outlet run may and may not retain."""

    def _pair(self, use_id: str, record_id: str, value: object, output: object = PLAN) -> list[dict[str, Any]]:
        calls = _call(use_id, "use_learned_function", {"operation": OP, "input": value}, self._miss())
        return calls + _call(
            record_id, "record_answer", {"operation": OP, "input": value, "output": output}, {"accepted": True}
        )

    def _retained(self) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
        with self.system.store.transaction() as connection:
            rows = connection.execute("SELECT id, source_id FROM proposals ORDER BY status_sequence, id").fetchall()
        records = {record["id"]: record for record in self.system.proposals(P)}
        return [(str(row[1]), records[str(row[0])]["input"], records[str(row[0])]["provenance"]) for row in rows]

    def test_x6_each_pair_binds_its_own_source_id_and_provenance(self) -> None:
        other = {"document": "PATIENT INTAKE FORM\nName: B\n"}
        self._outlet(self._pair("c1", "c2", DOC) + self._pair("c3", "c4", other, {"fields": ["name"]}))
        self.assertEqual(self.notes, [])
        retained = self._retained()
        self.assertEqual(len(retained), 2)
        for (source_id, value, provenance), (use_id, record_id) in zip(retained, (("c1", "c2"), ("c3", "c4"))):
            with self.subTest(source_id=source_id):
                digest = canonicalize(value).digest
                self.assertEqual(source_id, f"ward-7:chat-1:msg-u:{digest}")
                self.assertEqual(
                    provenance,
                    {
                        "chat_id": "chat-1",
                        "assistant_message_id": "msg-a",
                        "user_message_id": "msg-u",
                        "model": "stub-model",
                        "use_call_id": use_id,
                        "record_call_id": record_id,
                        "reply": "Here is the plan.",
                        "reply_truncated": False,
                    },
                )

    def test_e3_a_malformed_peer_never_drops_a_valid_pair(self) -> None:
        peers = _call("c9", "record_answer", {"operation": [], "input": DOC, "output": PLAN}, {"accepted": True})
        self._outlet(self._pair("c1", "c2", DOC) + peers)
        self.assertEqual([value for _, value, _ in self._retained()], [DOC])
        self.assertEqual(len(self.notes), 1)
        self.assertIn("c9", self.notes[0]["data"]["content"])

    def test_e3_a_record_without_its_output_writes_nothing(self) -> None:
        record = _call("c2", "record_answer", {"operation": OP, "input": DOC}, {"accepted": True})
        before = self._counts()
        self._outlet(_call("c1", "use_learned_function", {"operation": OP, "input": DOC}, self._miss()) + record)
        self.assertEqual(self._counts(), before)
        self.assertTrue(any("c2" in note["data"]["content"] for note in self.notes))

    def test_e4_without_a_current_message_id_nothing_is_retained(self) -> None:
        history = [{"role": "assistant", "content": "earlier", "output": self._pair("h1", "h2", DOC)}]
        before = self._counts()
        for missing in ("id", "chat_id"):
            with self.subTest(missing=missing):
                body = {
                    "model": "stub-model", "chat_id": "chat-1", "id": "msg-a",
                    "messages": [*history, {"id": "msg-u", "role": "user", "content": "plan this"},
                                 {"role": "assistant", "content": "plan", "output": self._pair("c1", "c2", DOC)}],
                }
                del body[missing]
                self.assertIs(asyncio.run(self.filter.outlet(body)), body)
                self.assertEqual(self._counts(), before)

    def test_x6_the_full_reply_is_retained_whenever_the_provenance_fits(self) -> None:
        for label, reply, whole in (
            ("ascii", "a" * 20_000, True),
            ("astral", "\U0001d4b3" * 16_384, False),
            ("oversize", "b" * 70_000, False),
        ):
            with self.subTest(reply=label):
                self.system = System(self.db)
                body = {
                    "model": "stub-model", "chat_id": f"chat-{label}", "id": "msg-a",
                    "messages": [{"id": "msg-u", "role": "user", "content": "plan this"},
                                 {"id": "msg-a", "role": "assistant", "content": reply,
                                  "output": self._pair("c1", "c2", DOC)}],
                }
                asyncio.run(self.filter.outlet(body))
                (_, _, provenance) = [row for row in self._retained() if f"chat-{label}" in row[0]][0]
                self.assertEqual(provenance["reply"] == reply, whole)
                self.assertEqual(provenance["reply_truncated"], not whole)
                self.assertTrue(reply.startswith(provenance["reply"]))
                self.assertLessEqual(len(canonicalize(provenance).text.encode()), PROVENANCE_MAX_BYTES)

    def test_e4_a_retention_or_notification_failure_never_reaches_open_webui(self) -> None:
        output = self._pair("c1", "c2", DOC)
        with mock.patch.object(System, "submit_proposal", side_effect=RuntimeError("disk gone")):
            self._outlet(output)
        self.assertEqual(len(self.notes), 1)

        async def broken(event: dict[str, Any]) -> None:
            raise RuntimeError("socket closed")

        body = {"model": "m", "chat_id": "chat-2", "id": "msg-a",
                "messages": [{"id": "msg-u", "role": "user", "content": "x"},
                             {"id": "msg-a", "role": "assistant", "content": "y",
                              "output": _call("c1", "use_learned_function", {"operation": OP, "input": DOC}, self._miss())}]}
        self.assertIs(asyncio.run(self.filter.outlet(body, __event_emitter__=broken)), body)



GUIDE = (
    "extraction_plan: The user pastes one form and asks what to extract."
    ' input = {"document": the whole form text}\n'
    "billing_codes: The user asks for billing codes of one note."
)


class ChatNoteBattery(_Example):
    """MAINTAIN W2: the operations reach the model through the filter inlet (fixed system prompt)."""

    def _inlet(self, body: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self.filter.inlet(body))

    def test_w2_the_inlet_note_names_each_operation_on_the_last_user_message(self) -> None:
        self.filter.valves.operations = GUIDE
        body = {
            "model": "m",
            "messages": [
                {"role": "system", "content": "Deployer prompt."},
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
                {"role": "user", "content": "Plan this form:\nPATIENT INTAKE FORM\nName: Bo"},
            ],
        }
        before = json.loads(json.dumps(body))
        returned = self._inlet(body)
        self.assertEqual(body, before)
        self.assertEqual(returned["messages"][:3], before["messages"][:3])
        content = returned["messages"][3]["content"]
        self.assertTrue(content.startswith(before["messages"][3]["content"] + "\n\n"))
        note = content[len(before["messages"][3]["content"]) :]
        for line in GUIDE.splitlines():
            self.assertIn(f"- {line}", note)
        for word in ("use_learned_function", "covered", "record_answer"):
            self.assertIn(word, note)
        self.assertEqual(returned["model"], "m")

    def test_w2_the_inlet_leaves_what_it_cannot_annotate_unchanged(self) -> None:
        self.filter.valves.operations = ""
        empty = {"messages": [{"role": "user", "content": "x"}]}
        self.assertEqual(self._inlet(empty), {"messages": [{"role": "user", "content": "x"}]})
        self.filter.valves.operations = GUIDE
        parts = {"messages": [{"role": "user", "content": [{"type": "text", "text": "x"}]}]}
        annotated = self._inlet(parts)["messages"][0]["content"]
        self.assertEqual(annotated[0], {"type": "text", "text": "x"})
        self.assertEqual(annotated[1]["type"], "text")
        self.assertIn("- billing_codes:", annotated[1]["text"])
        self.assertEqual(len(parts["messages"][0]["content"]), 1)
        for body in ({"messages": "x"}, {"messages": [{"role": "assistant", "content": "y"}]}, {}):
            with self.subTest(body=body):
                self.assertEqual(self._inlet(body), body)

    def test_w2_a_described_operation_is_enabled_and_retained(self) -> None:
        self.tools.valves.operations = GUIDE
        self.filter.valves.operations = GUIDE
        self.assertEqual(self._use()["reason"], "off")
        miss = {"covered": False, "reason": "off", "instruction": "..."}
        self._outlet(
            _call("c1", "use_learned_function", {"operation": OP, "input": DOC}, miss)
            + _call("c2", "record_answer", {"operation": OP, "input": DOC, "output": PLAN}, {"accepted": True})
        )
        self.assertEqual(len(self.system.proposals(P)), 1)

    def test_w2_a_refusal_names_the_enabled_operations(self) -> None:
        self.tools.valves.operations = GUIDE
        refused = asyncio.run(self.tools.use_learned_function("extract_plan", DOC))
        self.assertEqual((refused["covered"], refused["reason"]), (False, "invalid"))
        self.assertEqual(refused["enabled_operations"], ["extraction_plan", "billing_codes"])
        self.assertIn("extraction_plan", refused["error"])
        record = asyncio.run(self.tools.record_answer("extract_plan", DOC, PLAN))
        self.assertEqual(record["enabled_operations"], ["extraction_plan", "billing_codes"])

    def test_w2_every_source_reads_the_operations_valve_alike(self) -> None:
        import ast

        bodies = {}
        for path in sorted((ROOT / "examples/open_webui").glob("cement_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_operations"]
            self.assertEqual(len(found), 1, path.name)
            bodies[path.name] = ast.dump(found[0])
        self.assertGreaterEqual(len(bodies), 2)
        self.assertEqual(len(set(bodies.values())), 1, sorted(bodies))

    def test_w2_a_covered_result_tells_the_model_to_answer_from_it(self) -> None:
        self._publish()
        self.system.set_switch(P, OP, mode="follow", actor="person")
        answer = self._use()
        self.assertIs(answer["covered"], True)
        self.assertIn("output", answer["instruction"])
        self.assertIn("record_answer", answer["instruction"])



ADMIN = {"id": "u-admin", "role": "admin", "name": "Ward lead"}
NOTE_A = {"document": "PHYSICIAN PROGRESS NOTE\nPatient: A\n"}
NOTE_B = {"document": "PHYSICIAN PROGRESS NOTE\nPatient: B\n"}
NOTE_C = {"document": "PHYSICIAN PROGRESS NOTE\nPatient: C\n"}
LEARNING_FUNCTIONS = {
    "learn_cases", "show_proposal", "merge_case", "reject_proposal", "revoke_example",
    "publish_version", "function_versions", "diff_versions",
}
LAB = {"document": "LAB RESULT SLIP\nPatient: A\nPotassium: 4.2\n"}
LAYOUT = {"name": "physician progress note", "title": "PHYSICIAN PROGRESS NOTE", "entries": [{"label": "Patient"}]}
MERGED = {"fields": ["patient", "mrn"]}


class LearningToolBattery(_Example):
    """MAINTAIN W3 + W5: the admin-only learning tool runs the pass inside Open WebUI and never
    switches; the model judges projectability + each case's merge, the tool does the rest."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load("cement_learning")

    def setUp(self) -> None:
        super().setUp()
        self.learning = self.module.Tools()
        self.learning.valves = self.module.Tools.Valves(
            ledger_path=self.db, partition=P, operations=GUIDE
        )

    def _run(self, name: str, *args: Any, user: object = ADMIN, **kwargs: Any) -> dict[str, Any]:
        extra = {"__user__": user, "__chat_id__": "chat-9", "__model__": {"id": "cement-learning"}}
        function = getattr(self.learning, name)
        accepted = inspect.signature(function).parameters
        return asyncio.run(function(*args, **kwargs, **{k: v for k, v in extra.items() if k in accepted}))

    def _retain(self, *pairs: tuple[object, object]) -> list[str]:
        return [
            self.system.submit_proposal(P, OP, value, candidate=Candidate(output=output, provenance={}))
            for value, output in pairs
        ]

    def test_w3_the_public_surface_is_the_learning_steps_and_cannot_switch(self) -> None:
        public = {name for name in dir(self.module.Tools) if not name.startswith("_")} - {"Valves"}
        self.assertEqual(public, LEARNING_FUNCTIONS)
        import ast

        tree = ast.parse((ROOT / "examples/open_webui/cement_learning.py").read_text(encoding="utf-8"))
        called = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertTrue({"set_switch", "register_operation", "revise_operation"}.isdisjoint(called))
        self.assertIn("promote_function", called)

    def test_w3_a_non_admin_is_refused_and_nothing_is_written(self) -> None:
        (proposal,) = self._retain((NOTE_A, PLAN))
        before = self._counts()
        for user in ({"id": "u-1", "role": "user"}, None, "admin"):
            with self.subTest(user=user):
                refused = self._run("merge_case", OP, False, PLAN, "n", [proposal], user=user)
                self.assertEqual(refused["error"], "forbidden")
                self.assertEqual(self._run("publish_version", OP, False, user=user)["error"], "forbidden")
        self.assertEqual(self._counts(), before)

    def test_w3_an_operation_outside_the_valve_is_refused(self) -> None:
        refused = self._run("learn_cases", "triage_queue")
        self.assertEqual(refused["error"], "invalid")
        self.assertEqual(refused["enabled_operations"], ["extraction_plan", "billing_codes"])

    def test_w5_a_projectable_pass_derives_the_program_and_publishes_a_version_it_never_switches_on(self) -> None:
        first, second = self._retain((NOTE_A, PLAN), (NOTE_B, MERGED))
        self.assertEqual(len(self._run("learn_cases", OP)["cases"]), 2)
        grouped = self._run("learn_cases", OP, True)
        self.assertEqual(grouped["program"]["layouts"], [LAYOUT])
        (case,) = grouped["cases"]
        self.assertEqual(sorted(case["pending_proposal_ids"]), sorted([first, second]))
        merged = self._run("merge_case", OP, True, MERGED, "kept mrn", [first, second])
        self.assertEqual(
            [r["status"] for r in merged["reviewed"]], ["corrected", "accepted"], merged
        )
        published = self._run("publish_version", OP, True)
        self.assertIs(published["published"], True, published)
        self.assertEqual((published["cases"], published["layouts"]), (1, ["PHYSICIAN PROGRESS NOTE"]))
        self.assertEqual(self.system.switch(P, OP).mode, "off")
        self.system.set_switch(P, OP, mode="follow", actor="ward-lead")
        self.assertEqual(self.system.resolve(P, OP, NOTE_C).match.output, MERGED)
        again = self._run("publish_version", OP, True)
        self.assertEqual((again["published"], again["reason"]), (False, "the newest version already holds this set"))
        versions = self._run("function_versions", OP)["versions"]
        self.assertEqual([v["receipt"]["function_hash"] for v in versions], [published["function_hash"]])

    def test_w5_a_pass_recovers_exact_confirmations_by_superseding_them(self) -> None:
        for value, output in ((NOTE_A, PLAN), (NOTE_B, {"fields": ["mrn"]})):
            (proposal,) = self._retain((value, output))
            self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        exact = self._run("learn_cases", OP)
        self.assertEqual((exact["nothing_to_learn"], exact["grouped_by"]), (True, "exact"))
        (case,) = self._run("learn_cases", OP, True)["cases"]
        self.assertEqual((case["support"], len(case["outputs"])), (2, 2))
        merged = self._run("merge_case", OP, True, MERGED, "union", None, case["active_example_ids"])
        self.assertEqual(sorted(merged["superseded_example_ids"]), sorted(case["active_example_ids"]))
        self.assertEqual(len(merged["new_example_ids"]), 2)
        self.assertIs(self._run("publish_version", OP, True)["published"], True)
        self.system.set_switch(P, OP, mode="follow", actor="ward-lead")
        self.assertEqual(self.system.resolve(P, OP, NOTE_C).match.output, MERGED)

    def test_w5_merge_case_refuses_ids_of_two_cases_and_writes_nothing(self) -> None:
        note, lab = self._retain((NOTE_A, PLAN), (LAB, PLAN))
        self.assertEqual(len(self._run("learn_cases", OP, True)["cases"]), 2)
        before = self._counts()
        for ids in ([note, lab], []):
            with self.subTest(ids=ids):
                refused = self._run("merge_case", OP, True, PLAN, "n", ids)
                self.assertEqual(refused["error"], "invalid")
        self.assertEqual(self._counts(), before)

    def test_w5_the_program_needs_one_text_field(self) -> None:
        self._retain((NOTE_A, PLAN), ({"text": "PHYSICIAN PROGRESS NOTE\nPatient: Z\n"}, PLAN))
        refused = self._run("learn_cases", OP, True)
        self.assertEqual(refused["error"], "invalid")
        self.assertIn("one text field", refused["message"])

    def test_w3_reviews_are_the_learning_pass_with_chat_and_model_provenance(self) -> None:
        kept, dropped = self._retain((NOTE_A, PLAN), (NOTE_B, {"x": 1}))
        self.assertEqual(self._run("reject_proposal", dropped, "not a plan")["status"], "rejected")
        self._run("merge_case", OP, True, PLAN, "kept the plan", [kept])
        record = self.system.proposal(P, kept)
        self.assertEqual((record["status"], record["reviewer"]), ("accepted", "learning-pass"))
        self.assertEqual(record["review_note"], "kept the plan (Open WebUI chat chat-9, model cement-learning)")
        (example,) = [e["id"] for e in self.system.examples(P, OP)]
        revoked = self._run("revoke_example", example, "the plan read the wrong label")
        self.assertEqual(revoked["example_id"], example)
        events = [e for e in self.system.events(P) if e["kind"] == "example.revoked"]
        self.assertEqual(len(events), 1)

    def test_w3_the_skill_names_every_learning_function_and_no_command_line(self) -> None:
        import re

        text = (ROOT / "examples/open_webui/cement-learn/SKILL.md").read_text(encoding="utf-8")
        front = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
        assert front is not None
        fields = dict(line.split(": ", 1) for line in front.group(1).splitlines())
        self.assertEqual(fields["name"], "cement-learn")
        self.assertIn("never switches", fields["description"])
        named = set(re.findall(r"`([a-z_]+)`", text))
        self.assertEqual(LEARNING_FUNCTIONS - named, set())
        self.assertNotIn("set_switch", named)
        self.assertIsNone(re.search(r"`cement [a-z]", text))

    def test_w6_a_non_text_input_is_refused_not_raised(self) -> None:
        self._retain((NOTE_A, PLAN), ({"document": 42}, PLAN))
        refused = self._run("learn_cases", OP, True)
        self.assertEqual(refused["error"], "invalid")

    def test_w6_examples_of_an_older_revision_stay_out_of_the_program(self) -> None:
        (old,) = self._retain(({"old_document": "x"}, PLAN))
        self.system.review(P, old, reviewer="learning-pass", decision="accept")
        self.system.revise_operation(P, OP, policy=POLICY, revised_by="ward-lead")
        self._retain((NOTE_A, PLAN))
        grouped = self._run("learn_cases", OP, True)
        self.assertNotIn("error", grouped, grouped)
        self.assertEqual(grouped["program"]["layouts"], [LAYOUT])

    def test_w6_merge_case_reads_its_case_not_a_page_of_examples(self) -> None:
        (proposal,) = self._retain((NOTE_A, PLAN))
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        (example,) = [e["id"] for e in self.system.examples(P, OP)]
        with mock.patch.object(System, "examples", side_effect=AssertionError("paged read")):
            merged = self._run("merge_case", OP, False, MERGED, "n", None, [example])
        self.assertEqual(merged["superseded_example_ids"], [example], merged)

    def test_w6_repeated_ids_are_refused_before_any_write(self) -> None:
        (proposal,) = self._retain((NOTE_A, PLAN))
        before = self._counts()
        refused = self._run("merge_case", OP, False, PLAN, "n", [proposal, proposal])
        self.assertEqual(refused["error"], "invalid")
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.system.proposal(P, proposal)["status"], "pending")

    def test_w6_a_failure_after_a_write_reports_the_writes(self) -> None:
        first, second = self._retain((NOTE_A, PLAN), (NOTE_B, PLAN))
        real = System.review
        calls = []

        def review(system: System, *args: Any, **kwargs: Any) -> Any:
            calls.append(args[1])
            if len(calls) == 2:
                raise StateError("ledger busy")
            return real(system, *args, **kwargs)

        with mock.patch.object(System, "review", review):
            result = self._run("merge_case", OP, True, PLAN, "n", [first, second])
        self.assertEqual(result["error"], "conflict")
        self.assertEqual(result["completed"]["reviewed"], [{"proposal_id": calls[0], "status": "accepted"}])
        self.assertEqual(self.system.proposal(P, calls[0])["status"], "accepted")

    def test_w3_refusals_carry_the_cli_error_kinds(self) -> None:
        self.assertEqual(self._run("show_proposal", "prop_" + "0" * 32)["error"], "not_found")
        nothing = self._run("publish_version", OP, False)
        self.assertEqual((nothing["published"], nothing["reason"]), (False, "no case has enough confirmations"))
        self.learning.valves.ledger_path = self.db + ".absent"
        self.assertEqual(self._run("learn_cases", OP)["error"], "integrity")
        self.assertFalse(pathlib.Path(self.db + ".absent").exists())


class SwitchActionBattery(_Example):
    """MAINTAIN W4: the switch = an admin's click through a select + a confirmation, no model."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load("cement_admin")

    def setUp(self) -> None:
        super().setUp()
        self.action = self.module.Action()
        self.action.valves = self.module.Action.Valves(ledger_path=self.db, partition=P, operations=GUIDE)
        self.calls: list[dict[str, Any]] = []
        self.answers: list[object] = []

    async def _event_call(self, event: dict[str, Any]) -> object:
        self.calls.append(event)
        return self.answers.pop(0)

    def _click(self, *answers: object, user: object = ADMIN) -> list[dict[str, Any]]:
        self.answers = list(answers)
        self.calls = []
        self.notes = []

        async def emit(event: dict[str, Any]) -> None:
            self.notes.append(event)

        asyncio.run(
            self.action.action({"model": "cement-learning"}, __user__=user, __event_call__=self._event_call,
                               __event_emitter__=emit)
        )
        return [call["data"]["options"] for call in self.calls if call["data"].get("type") == "select"]

    def _values(self, options: list[dict[str, str]]) -> list[str]:
        return [option["value"] for option in options]

    def _version(self, value: object, output: object) -> str:
        for _ in range(2):
            proposal = self.system.submit_proposal(P, OP, value, candidate=Candidate(output=output, provenance={}))
            self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        self.system.compile(P, OP)
        self.system.verify_drafts(P, OP, verified_by="learning-pass")
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass")
        return manifest.function_hash

    def test_w4_a_non_admin_gets_no_dialog_and_nothing_changes(self) -> None:
        before = self._counts()
        for user in ({"id": "u-1", "role": "user"}, None):
            with self.subTest(user=user):
                self._click("follow|extraction_plan", True, user=user)
                self.assertEqual(self.calls, [])
                self.assertEqual(self.notes[-1]["data"]["type"], "error")
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.system.switch(P, OP).mode, "off")

    def test_w4_set_up_creates_the_ledger_and_registers_with_the_switch_off(self) -> None:
        ledger = pathlib.Path(self.db).parent / "cement" / "ledger.db"
        self.action.valves.ledger_path = str(ledger)
        (options,) = self._click("register|extraction_plan", True)
        self.assertEqual(self._values(options), ["register|extraction_plan", "register|billing_codes"])
        self.assertTrue(ledger.is_file())
        system = System(str(ledger), create=False)
        self.assertEqual([op["name"] for op in system.operations(P)], ["extraction_plan"])
        self.assertEqual((system.switch(P, OP).mode, system.events(P)[0]["payload"]["registered_by"]),
                         ("off", "open-webui:u-admin"))
        self.assertEqual(self.notes[-1]["data"]["type"], "success")

    def test_w4_declining_either_dialog_writes_nothing(self) -> None:
        self._version(NOTE_A, PLAN)
        before = self._counts()
        for answers in ((False,), (None,), ("follow|extraction_plan", False), ("follow|extraction_plan", None)):
            with self.subTest(answers=answers):
                self._click(*answers)
                self.assertEqual(self.notes[-1]["data"]["content"], "Nothing changed.")
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.system.switch(P, OP).mode, "off")

    def test_w4_a_version_is_switched_on_pinned_and_off_by_the_admin(self) -> None:
        first = self._version(NOTE_A, PLAN)
        (options,) = self._click("follow|extraction_plan", True)
        self.assertEqual(
            self._values(options),
            ["follow|extraction_plan", f"pinned|extraction_plan|{first}", "register|billing_codes"],
        )
        state = self.system.switch(P, OP)
        self.assertEqual((state.mode, state.set_by), ("follow", "open-webui:u-admin"))
        second = self._version(NOTE_B, {"fields": ["patient", "mrn"]})
        self.assertNotEqual(first, second)
        (options,) = self._click(f"pinned|extraction_plan|{first}", True)
        self.assertEqual(
            self._values(options),
            ["off|extraction_plan", f"pinned|extraction_plan|{second}", f"pinned|extraction_plan|{first}",
             "register|billing_codes"],
        )
        self.assertEqual((self.system.switch(P, OP).mode, self.system.switch(P, OP).function_hash), ("pinned", first))
        self.assertEqual(self.system.resolve(P, OP, NOTE_A).match.output, PLAN)
        (options,) = self._click("off|extraction_plan", True)
        self.assertIn("follow|extraction_plan", self._values(options))
        self.assertEqual(self.system.switch(P, OP).mode, "off")

    def test_w4_the_dialog_is_a_select_then_a_confirmation_naming_the_choice(self) -> None:
        self._version(NOTE_A, PLAN)
        self._click("follow|extraction_plan", True)
        select, confirm = self.calls
        self.assertEqual((select["type"], select["data"]["type"]), ("input", "select"))
        self.assertIn("extraction_plan: off", select["data"]["message"])
        self.assertIn("billing_codes: not set up", select["data"]["message"])
        chosen = next(o["label"] for o in select["data"]["options"] if o["value"] == "follow|extraction_plan")
        self.assertEqual((confirm["type"], confirm["data"]["message"]), ("confirmation", chosen))

    def test_w6_every_version_is_offered_past_one_page(self) -> None:
        hashes = [self._version(value, {"fields": [name]}) for value, name in
                  ((NOTE_A, "a"), (NOTE_B, "b"), (NOTE_C, "c"))]
        with mock.patch.object(self.module, "PAGE", 2):
            (options,) = self._click(False)
        pins = {o["value"].rsplit("|", 1)[1]: o["label"] for o in options if o["value"].startswith("pinned|")}
        self.assertEqual(set(pins), set(hashes))
        for number, function_hash in enumerate(hashes, start=1):
            self.assertIn(f"version {number} ", pins[function_hash])

    def test_w4_a_value_the_dialog_did_not_offer_changes_nothing(self) -> None:
        before = self._counts()
        for forged in ("follow|extraction_plan", "register|triage_queue", "off|extraction_plan|x", "x"):
            with self.subTest(forged=forged):
                self._click(forged, True)
                self.assertEqual(self.notes[-1]["data"]["content"], "Nothing changed.")
        self.assertEqual(self._counts(), before)


if __name__ == "__main__":
    unittest.main()
