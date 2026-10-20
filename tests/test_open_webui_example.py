"""M5.3 battery — the Open WebUI example: a read-only tool + the filter as the single writer.

Contract: `.agent/decisions/m45-contract.md` §7 (E1-E4). Open WebUI is not a dependency: the
modules import `pydantic` for their valves alone, so a minimal stub stands in for it here and the
real 0.12.3 loop is the unit's recorded smoke.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest
from typing import Any
from unittest import mock

from cement_runtime import Candidate, CompilePolicy, System
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


if __name__ == "__main__":
    unittest.main()
