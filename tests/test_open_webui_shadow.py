"""p136-owui battery — shadow sampling in the Open WebUI filter (S5 = the frozen-completion probe).

Contract: `.agent/decisions/p136-owui-contract.md`. Open WebUI stays stubbed as in
`tests/test_open_webui_example.py`; the model boundary is the filter's own `_ask`, replaced per test,
except one test that drives it against stub `open_webui.utils.chat` + `open_webui.models.users` modules.
"""

from __future__ import annotations

import asyncio
import copy
import json
import sys
import types
import unittest
from typing import Any
from unittest import mock

from cement_runtime import shadow as sh
from tests.test_open_webui_example import DOC, OP, P, PLAN, _call, _Example

OUTPUT = {"fields": ["MARKER-OUT"]}


def _doc(index: int) -> dict[str, str]:
    return {"document": f"PHYSICIAN PROGRESS NOTE\nPatient: P{index}\n"}


class ShadowSamplingTests(_Example):
    def setUp(self) -> None:
        super().setUp()
        self.filter.valves.shadow_model = "shadow-model"
        self.asked: list[list[dict]] = []

    def publish(self, *documents: dict[str, str]) -> None:
        for document in documents:
            self._publish(document, OUTPUT)
        self.system.set_switch(P, OP, mode="follow", actor="person")

    def body(self, index: int, value: dict[str, str], *, chat: str = "chat-1") -> dict[str, Any]:
        result = self._use(value)
        assert result["covered"] is True, result
        return {
            "model": "stub-model",
            "chat_id": chat,
            "id": f"msg-{index}",
            "messages": [
                {"id": f"user-{index}", "role": "user", "content": "plan this"},
                {"id": f"msg-{index}", "role": "assistant", "content": "Done.",
                 "output": _call(f"call-{index}", "use_learned_function", {"operation": OP, "input": value}, result)},
            ],
        }

    def answering(self, replies: dict[str, Any]):
        async def ask(request: Any, user: Any, messages: list[dict]) -> str:
            self.asked.append(messages)
            reply = next((answer for marker, answer in replies.items() if marker in messages[1]["content"]), OUTPUT)
            if isinstance(reply, BaseException):
                raise reply
            return reply if isinstance(reply, str) else json.dumps(reply)

        return ask

    async def drive(self, bodies: list[dict[str, Any]], ask) -> list[dict[str, Any]]:
        self.filter._ask = ask
        returned = [await self.filter.outlet(body) for body in bodies]
        if self.filter._queue is not None:
            await self.filter._queue.join()
        return returned

    def rows(self) -> list[sh.ObservationRecord]:
        return sh.observations(sh.ShadowStore(sh.shadow_path(self.db)), P, OP, limit=1000)

    def test_s5_the_frozen_completion_is_returned_unchanged_on_and_off(self) -> None:
        self.publish(DOC)
        body = self.body(1, DOC)
        frozen = json.dumps(body, sort_keys=True)
        for model in ("", "shadow-model"):
            self.filter.valves.shadow_model = model
            with self.subTest(model=model):
                [returned] = asyncio.run(self.drive([body], self.answering({})))
                self.assertIs(returned, body)
                self.assertEqual(json.dumps(returned, sort_keys=True), frozen)
        self.assertEqual(len(self.asked), 1)  # off: no call; on: one

    def test_s5_n_hits_with_mixed_agreement_and_both_controls(self) -> None:
        documents = [_doc(i) for i in range(5)]
        self.publish(*documents)
        disagree = {"P1\\n": {"fields": ["other"]}, "P3\\n": {"fields": ["x"]}}
        for name, replies, expected in (
            ("mixed", disagree, 2),
            ("all agree", {}, 0),
            ("all disagree", {f"P{i}\\n": {"fields": [str(i)]} for i in range(5)}, 5),
        ):
            with self.subTest(case=name):
                self.setUp()
                self.publish(*documents)
                bodies = [self.body(i, document, chat=f"{name}-{i}") for i, document in enumerate(documents)]
                digest = json.loads(bodies[0]["messages"][1]["output"][1]["output"][0]["text"])["function_hash"]
                asyncio.run(self.drive(bodies, self.answering(replies)))
                report = sh.drift(sh.ShadowStore(sh.shadow_path(self.db)), P, OP)
                self.assertEqual(len(self.asked), 5)
                self.assertEqual(sum(report["totals"].values()), 5)
                self.assertEqual(report["disagreements"], expected)
                self.assertEqual(report["totals"]["agreed"], 5 - expected)
                self.assertEqual([group["function_hash"] for group in report["groups"]], [digest])
        self.assertEqual(sh.drift(sh.ShadowStore(sh.shadow_path(self.db)), P, "other_op")["groups"], [])

    def test_s5_off_and_excluded_operations_make_no_call_and_no_write(self) -> None:
        self.publish(DOC)
        for valves in ({"shadow_model": ""}, {"shadow_exclude": f"other, {OP}"}):
            with self.subTest(valves=valves):
                for name, value in valves.items():
                    setattr(self.filter.valves, name, value)
                asyncio.run(self.drive([self.body(1, DOC)], self.answering({})))
                self.assertEqual(self.asked, [])
                self.assertFalse(sh.shadow_path(self.db).exists())
                self.filter.valves.shadow_model, self.filter.valves.shadow_exclude = "shadow-model", ""

    def test_s5_a_repeated_completed_run_is_one_observation(self) -> None:
        self.publish(DOC)
        body = self.body(1, DOC)
        asyncio.run(self.drive([body, copy.deepcopy(body)], self.answering({})))
        self.assertEqual((len(self.asked), len(self.rows())), (1, 1))
        self.assertEqual(sh.drift(sh.ShadowStore(sh.shadow_path(self.db)), P, OP)["duplicates"], 1)
        self.assertEqual(self.rows()[0]["observation_id"], "ward-7:chat-1:msg-1:call-1")

    def test_s5_a_blocked_shadow_call_never_holds_the_reply(self) -> None:
        self.publish(DOC)
        body = self.body(1, DOC)
        order: list[str] = []

        async def scenario() -> None:
            gate = asyncio.Event()

            async def ask(request: Any, user: Any, messages: list[dict]) -> str:
                order.append("asked")
                await gate.wait()
                order.append("answered")
                return json.dumps(OUTPUT)

            self.filter._ask = ask
            await self.filter.outlet(body)
            order.append("reply returned")
            await asyncio.sleep(0.2)
            self.assertNotIn("answered", order)
            gate.set()
            await self.filter._queue.join()

        asyncio.run(scenario())
        self.assertEqual(order[0], "reply returned")
        self.assertEqual(order[-1], "answered")
        self.assertEqual(self.rows()[0]["state"], "agreed")

    def test_s5_failed_unparsable_and_slow_calls_are_counted_failures(self) -> None:
        self.publish(_doc(1), _doc(2), _doc(3))
        self.filter.valves.shadow_timeout = 1

        async def ask(request: Any, user: Any, messages: list[dict]) -> str:
            content = messages[1]["content"]
            if "P1\\n" in content:
                raise ConnectionError("model down")
            if "P2\\n" in content:
                return "here is the plan: none"
            await asyncio.sleep(3)
            return json.dumps(OUTPUT)

        before = self._counts()
        asyncio.run(self.drive([self.body(i, _doc(i), chat=f"c{i}") for i in (1, 2, 3)], ask))
        self.assertEqual(
            sorted((row["state"], row["note"]) for row in self.rows()),
            [("failed", "the shadow call failed: ConnectionError"),
             ("failed", "the shadow call failed: JSONDecodeError"),
             ("failed", "the shadow model timed out")],
        )
        self.assertEqual(self._counts(), before)  # no proposal, no event

    def test_s5_the_version_that_served_the_hit_decides(self) -> None:
        self.publish(DOC)
        body = self.body(1, DOC)  # the tool answered from version 1
        examples = [e["id"] for e in self.system.examples(P, OP)]
        self.system.supersede_examples(P, OP, example_ids=examples, output={"fields": ["NEW"]}, reviewer="lp")
        self._publish(_doc(9), OUTPUT)  # version 2 answers DOC with NEW
        self.assertEqual(self._use(DOC)["output"], {"fields": ["NEW"]})
        asyncio.run(self.drive([body], self.answering({})))  # the LLM answers like version 1
        [row] = self.rows()
        self.assertEqual((row["state"], row["function_output"]), ("agreed", OUTPUT))

    def test_s5_a_full_queue_drops_without_blocking(self) -> None:
        documents = [_doc(i) for i in range(3)]
        self.publish(*documents)
        self.filter.valves.shadow_queue = 1
        bodies = [self.body(i, document, chat=f"q{i}") for i, document in enumerate(documents)]

        async def scenario() -> None:
            self.filter._ask = self.answering({})
            for body in bodies:
                await self.filter.outlet(body)
            await self.filter._queue.join()
            for _ in range(200):
                if sum(row["state"] == "dropped" for row in self.rows()) == 2:
                    break
                await asyncio.sleep(0.05)

        asyncio.run(scenario())
        self.assertEqual(sorted(row["state"] for row in self.rows()), ["agreed", "dropped", "dropped"])
        self.assertEqual(self.filter.shadow_counts.get("dropped"), 2)

    def test_s5_the_real_shadow_call_awaits_the_account_and_sends_no_tools(self) -> None:
        # Open WebUI 0.12.3: `Users.get_user_by_id` is a coroutine function (live run, p136 gate 3).
        self.publish(DOC)
        body = self.body(1, DOC)
        account, request = object(), object()
        calls: list[tuple[Any, ...]] = []

        async def get_user_by_id(user_id: str) -> object:
            calls.append(("account", user_id))
            return account

        async def generate_chat_completion(request: Any, form: dict, *, user: Any, bypass_filter: bool = False) -> Any:
            calls.append(("model", request, form, user, bypass_filter))
            reply = {"choices": [{"message": {"content": json.dumps(OUTPUT)}}]}
            return types.SimpleNamespace(body=json.dumps(reply).encode())

        modules = {
            "open_webui.utils.chat": types.SimpleNamespace(generate_chat_completion=generate_chat_completion),
            "open_webui.models.users": types.SimpleNamespace(Users=types.SimpleNamespace(get_user_by_id=get_user_by_id)),
        }

        async def scenario() -> None:
            await self.filter.outlet(body, __request__=request, __user__={"id": "u-1", "role": "user"})
            await self.filter._queue.join()

        with mock.patch.dict(sys.modules, modules):
            asyncio.run(scenario())
        [looked_up, (_, seen_request, form, user, bypass)] = calls
        self.assertEqual(looked_up, ("account", "u-1"))
        self.assertIs(seen_request, request)
        self.assertIs(user, account)
        self.assertIs(bypass, True)
        self.assertEqual(sorted(form), ["messages", "model", "stream"])
        self.assertEqual((form["model"], form["stream"]), ("shadow-model", False))
        self.assertEqual(self.rows()[0]["state"], "agreed")

    def test_s5_the_prompt_never_holds_the_function_answer(self) -> None:
        self.publish(DOC)
        asyncio.run(self.drive([self.body(1, DOC)], self.answering({})))
        [messages] = self.asked
        text = json.dumps(messages)
        self.assertNotIn("MARKER-OUT", text)
        self.assertIn(json.dumps(DOC["document"])[1:-1].split("\\n")[0], text)
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertTrue(self.rows()[0]["prompt_revision"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
