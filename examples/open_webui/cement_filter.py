"""
title: Cement answer retention
author: Cement
version: 0.2.0
license: Apache-2.0
description: Retains recorded answers to uncovered requests for the Cement learning pass.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from cement_runtime import Candidate, CementError, ConflictError, System, ValidationError
from cement_runtime.json_value import canonicalize
from cement_runtime.shadow import ShadowStore, admit, drop, fail, record_shadow, shadow_path
from cement_runtime.system import PROVENANCE_MAX_BYTES

log = logging.getLogger(__name__)

USE = "use_learned_function"
RECORD = "record_answer"
NOTE_HEAD = "Cement learned functions are available for these operations:"
NOTE_TAIL = (
    "For a request that one of these operations covers, first call use_learned_function with"
    " the operation and the exact input object that its description names. If the result says"
    " covered, answer from its output. If it says not covered, answer the request yourself, then"
    " call record_answer with the same operation and input and the structured output that your"
    " answer used. Answer every other request as usual."
)


SHADOW_SYSTEM = (
    "You answer one operation of a deployment. Read the operation, its description and its input."
    " Return only the JSON output that the operation produces for that input: one JSON value, with"
    " no prose and no code fence."
)


def _shadow_prompt(operation: str, description: str, value: Any) -> tuple[list[dict], str]:
    """The shadow call's messages and their revision: the operation's description + the input
    alone, never the function's answer, the chat or the reply (T8)."""

    user = (
        f"Operation: {operation}\nDescription: {description or '(none)'}\n"
        f"Input (JSON):\n{canonicalize(value).text}"
    )
    digest = hashlib.sha256(f"{SHADOW_SYSTEM}\n{description}".encode()).hexdigest()
    messages = [{"role": "system", "content": SHADOW_SYSTEM}, {"role": "user", "content": user}]
    return messages, f"sha256:{digest[:16]}"


def _answer(text: str) -> Any:
    """The JSON value of a model reply; a reply wrapped in one code fence is unwrapped."""

    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped[3:-3].strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    return json.loads(stripped)


def _names(text: str) -> set[str]:
    return {name.strip() for name in text.replace("\n", ",").split(",") if name.strip()}


def _operations(text: str) -> dict[str, str]:
    """Valve text → operation name → description: `name: description` lines, or names alone."""

    operations: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            name, description = line.split(":", 1)
            if name.strip():
                operations[name.strip()] = description.strip()
        else:
            operations.update((name.strip(), "") for name in line.split(",") if name.strip())
    return operations


def _note(operations: dict[str, str]) -> str:
    lines = [f"- {name}: {text}" if text else f"- {name}" for name, text in operations.items()]
    return "\n".join([NOTE_HEAD, *lines, NOTE_TAIL])


def _named(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _with_reply(provenance: dict[str, Any], reply: object) -> dict[str, Any]:
    """The provenance with the whole reply, or its longest prefix that fits the library bound."""

    if not isinstance(reply, str):
        return provenance | {"reply": None, "reply_truncated": False}

    def fits(length: int) -> bool:
        candidate = provenance | {"reply": reply[:length], "reply_truncated": length < len(reply)}
        try:
            canonicalize(candidate, max_bytes=PROVENANCE_MAX_BYTES)
        except ValidationError:
            return False
        return True

    if fits(len(reply)):
        return provenance | {"reply": reply, "reply_truncated": False}
    low, high = 0, len(reply)  # fits(low) holds; fits(high) does not
    while high - low > 1:
        middle = (low + high) // 2
        low, high = (middle, high) if fits(middle) else (low, middle)
    return provenance | {"reply": reply[:low], "reply_truncated": True}


def _tool_calls(message: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """`call_id` → {name, arguments} and `call_id` → parsed result, from native tool items."""

    calls: dict[str, dict[str, Any]] = {}
    results: dict[str, Any] = {}
    for item in message.get("output") or []:
        if not isinstance(item, dict) or not isinstance(item.get("call_id"), str):
            continue
        if item.get("type") == "function_call":
            try:
                arguments = json.loads(item.get("arguments") or "{}")
            except (TypeError, ValueError):
                arguments = None
            calls[item["call_id"]] = {"name": item.get("name"), "arguments": arguments}
        elif item.get("type") == "function_call_output":
            text = "".join(
                part.get("text", "")
                for part in item.get("output") or []
                if isinstance(part, dict) and part.get("type") == "input_text"
            )
            try:
                results[item["call_id"]] = json.loads(text)
            except ValueError:
                results[item["call_id"]] = None
    return calls, results


class Filter:
    class Valves(BaseModel):
        ledger_path: str = Field(default="", description="Path of the existing Cement ledger file.")
        partition: str = Field(default="", description="Cement partition of this deployment.")
        deployment_id: str = Field(
            default="open-webui", description="Names this deployment in each source id."
        )
        operations: str = Field(
            default="",
            description="Operations whose answers are retained, one per line: `name: description`."
            " The description tells the chat model the request and its exact input.",
        )
        shadow_model: str = Field(
            default="",
            description="Model that answers each covered request again in the background, so"
            " Cement can compare answers. Empty turns shadow answers off.",
        )
        shadow_exclude: str = Field(
            default="", description="Operations that never get a shadow answer, comma separated."
        )
        shadow_queue: int = Field(
            default=64, description="Shadow answers that wait at most; more are dropped."
        )
        shadow_timeout: int = Field(
            default=60, description="Seconds one shadow answer may take before it fails."
        )
        shadow_path: str = Field(
            default="", description="Shadow observation file; empty = the ledger path + .shadow."
        )

    def __init__(self) -> None:
        self.valves = self.Valves()
        self._queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._worker: asyncio.Task | None = None
        self.shadow_counts: dict[str, int] = {}

    def _hits(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        """Covered `use_learned_function` calls of the CURRENT assistant message (O1)."""

        if not self.valves.shadow_model:
            return []
        raw = body.get("messages")
        messages = [m for m in raw if isinstance(m, dict)] if isinstance(raw, list) else []
        message_id, chat_id = _named(body.get("id")), _named(body.get("chat_id"))
        message = next(
            (m for m in messages if m.get("role") == "assistant" and m.get("id") == message_id),
            None,
        )
        if message is None or message_id is None or chat_id is None:
            return []
        listed = _operations(self.valves.operations)
        excluded = _names(self.valves.shadow_exclude)
        calls, results = _tool_calls(message)
        hits = []
        for call_id, call in calls.items():
            arguments, result = call["arguments"], results.get(call_id)
            if (
                call["name"] != USE
                or not isinstance(arguments, dict)
                or not isinstance(result, dict)
                or result.get("covered") is not True
                or not isinstance(result.get("function_hash"), str)
                or arguments.get("operation") not in listed
                or arguments.get("operation") in excluded
                or "input" not in arguments
            ):
                continue
            try:
                canonicalize(arguments["input"])
            except ValidationError:
                continue
            hits.append(
                {
                    "observation_id": (
                        f"{self.valves.deployment_id}:{chat_id}:{message_id}:{call_id}"
                    ),
                    "operation": arguments["operation"],
                    "input": arguments["input"],
                    "function_hash": result["function_hash"],
                    "observed_at_us": time.time_ns() // 1_000,
                }
            )
        return hits

    def _count(self, outcome: str) -> None:
        self.shadow_counts[outcome] = self.shadow_counts.get(outcome, 0) + 1

    def _store(self) -> tuple[System, ShadowStore]:
        system = System(self.valves.ledger_path, create=False)
        return system, ShadowStore(self.valves.shadow_path or shadow_path(self.valves.ledger_path))

    def _enqueue(self, hits: list[dict[str, Any]], request: Any, user: Any) -> None:
        """Queue each hit for the worker and return at once; a full queue drops the hit (O2)."""

        loop = asyncio.get_running_loop()
        if self._queue is None or self._loop is not loop:
            self._queue = asyncio.Queue(maxsize=max(1, self.valves.shadow_queue))
            self._loop = loop
            # The task is held on the instance: the loop keeps only a weak reference to it.
            self._worker = loop.create_task(self._work(self._queue))
        for hit in hits:
            try:
                self._queue.put_nowait((hit, request, user))
            except asyncio.QueueFull:
                self._count("dropped")
                loop.run_in_executor(None, self._drop, hit)

    def _drop(self, hit: dict[str, Any]) -> None:
        try:
            _, store = self._store()
            drop(
                store,
                self.valves.partition,
                hit["operation"],
                observation_id=hit["observation_id"],
                function_hash=hit["function_hash"],
                input_value=hit["input"],
                observed_at_us=hit["observed_at_us"],
                reason="queue full",
            )
        except Exception:
            log.exception("cement: a dropped shadow sample was not recorded")

    async def _work(self, queue: asyncio.Queue) -> None:
        while True:
            hit, request, user = await queue.get()
            try:
                await self._sample(hit, request, user)
            except Exception:
                self._count("error")
                log.exception("cement: a shadow sample failed")
            finally:
                queue.task_done()

    async def _sample(self, hit: dict[str, Any], request: Any, user: Any) -> None:
        """Admit, ask the shadow model, record (O3); every failure stays out of the chat."""

        system, store = await asyncio.to_thread(self._store)
        admission = await asyncio.to_thread(
            admit,
            system,
            store,
            self.valves.partition,
            hit["operation"],
            observation_id=hit["observation_id"],
            function_hash=hit["function_hash"],
            input_value=hit["input"],
            observed_at_us=hit["observed_at_us"],
        )
        if not admission.admitted:
            self._count("duplicate")
            return
        description = _operations(self.valves.operations).get(hit["operation"], "")
        messages, revision = _shadow_prompt(hit["operation"], description, hit["input"])
        started = time.monotonic()
        try:
            reply = await asyncio.wait_for(
                self._ask(request, user, messages), timeout=max(1, self.valves.shadow_timeout)
            )
            answer = _answer(reply)
        except TimeoutError:
            reason = "the shadow model timed out"
        except Exception as exc:  # noqa: BLE001 — any model or parse failure is one counted outcome
            reason = f"the shadow call failed: {type(exc).__name__}"
        else:
            await asyncio.to_thread(
                record_shadow,
                system,
                store,
                admission.id,
                llm_output=answer,
                model=self.valves.shadow_model,
                prompt_revision=revision,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            self._count("recorded")
            return
        self._count("failed")
        await asyncio.to_thread(
            fail,
            store,
            admission.id,
            reason=reason,
            model=self.valves.shadow_model,
            prompt_revision=revision,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def _ask(self, request: Any, user: Any, messages: list[dict]) -> str:
        """One plain model call: no tools, no filters, the fixed shadow model (O3)."""

        chat = importlib.import_module("open_webui.utils.chat")
        users = importlib.import_module("open_webui.models.users")
        account = users.Users.get_user_by_id(user["id"])
        response = await chat.generate_chat_completion(
            request,
            {"model": self.valves.shadow_model, "messages": messages, "stream": False},
            user=account,
            bypass_filter=True,
        )
        if hasattr(response, "body"):
            response = json.loads(response.body)
        return str(response["choices"][0]["message"]["content"])

    def _pairs(
        self, body: dict[str, Any], metadata: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Valid (miss, record) pairs of the CURRENT assistant message + one note per defect."""

        raw = body.get("messages")
        messages = [m for m in raw if isinstance(m, dict)] if isinstance(raw, list) else []
        # Without its own id the current message is unknowable: retain nothing, never history.
        message_id = _named(body.get("id"))
        current = next(
            (
                index
                for index, m in enumerate(messages)
                if message_id is not None
                and m.get("role") == "assistant"
                and m.get("id") == message_id
            ),
            None,
        )
        if current is None:
            return [], []
        message = messages[current]
        # The asking user message comes from the body: `/api/chat/completed` re-runs the outlet
        # without `user_message_id` in its metadata, and the source id must not change with it.
        user_message_id = _named(
            next(
                (m.get("id") for m in reversed(messages[:current]) if m.get("role") == "user"),
                None,
            )
        ) or _named(metadata.get("user_message_id"))
        chat_id = _named(body.get("chat_id"))
        calls, results = _tool_calls(message)
        if (chat_id is None or user_message_id is None) and any(
            call["name"] == RECORD for call in calls.values()
        ):
            return [], ["the chat or its question has no id, so no answer was retained"]
        allowed = set(_operations(self.valves.operations))
        misses: dict[tuple[str, str], str] = {}
        covered: set[tuple[str, str]] = set()
        records: list[tuple[str, dict[str, Any]]] = []
        notes: list[str] = []
        for call_id, call in calls.items():
            arguments = call["arguments"]
            name = call["name"]
            if name not in (USE, RECORD):
                continue
            required = {"operation", "input"} | ({"output"} if name == RECORD else set())
            if (
                not isinstance(arguments, dict)
                or not required <= arguments.keys()
                or not isinstance(arguments["operation"], str)
                or arguments["operation"] not in allowed
            ):
                notes.append(f"{name} call {call_id} is malformed or names a disabled operation")
                continue
            try:
                key = (arguments["operation"], canonicalize(arguments["input"]).digest)
            except ValidationError:
                notes.append(f"{name} call {call_id} has an input that is not canonical JSON")
                continue
            result = results.get(call_id)
            if name == USE:
                if isinstance(result, dict) and result.get("covered") is True:
                    covered.add(key)
                elif isinstance(result, dict) and result.get("covered") is False:
                    misses.setdefault(key, call_id)
            elif isinstance(result, dict) and result.get("accepted") is True:
                records.append((call_id, arguments | {"_key": key}))
            else:
                notes.append(f"record_answer call {call_id} was not accepted")
        pairs: list[dict[str, Any]] = []
        paired: set[tuple[str, str]] = set()
        for call_id, record in records:
            key = record.pop("_key")
            if key in covered:
                notes.append(f"record_answer call {call_id} answers a covered request")
            elif key not in misses:
                notes.append(f"record_answer call {call_id} has no matching uncovered call")
            elif key in paired:
                notes.append(f"record_answer call {call_id} repeats a recorded request")
            else:
                paired.add(key)
                pairs.append(
                    {
                        "operation": record["operation"],
                        "input": record["input"],
                        "output": record["output"],
                        "input_hash": key[1],
                        "use_call_id": misses[key],
                        "record_call_id": call_id,
                    }
                )
        notes.extend(
            f"use_learned_function call {call_id} missed without record_answer"
            for key, call_id in misses.items()
            if key not in paired
        )
        for pair in pairs:
            pair["provenance"] = _with_reply(
                {
                    "chat_id": chat_id,
                    "assistant_message_id": message_id,
                    "user_message_id": user_message_id,
                    "model": body.get("model"),
                    "use_call_id": pair["use_call_id"],
                    "record_call_id": pair["record_call_id"],
                },
                message.get("content"),
            )
            pair["source_id"] = ":".join(
                str(part)
                for part in (
                    self.valves.deployment_id,
                    chat_id,
                    user_message_id,
                    pair["input_hash"],
                )
            )
        return pairs, notes

    def _retain(self, pairs: list[dict[str, Any]]) -> list[str]:
        notes: list[str] = []
        try:
            system = System(self.valves.ledger_path, create=False)
        except CementError as exc:
            return [f"Cement could not open its ledger, so no answer was retained: {exc}"]
        for pair in pairs:
            try:
                system.submit_proposal(
                    self.valves.partition,
                    pair["operation"],
                    pair["input"],
                    candidate=Candidate(output=pair["output"], provenance=pair["provenance"]),
                    source_id=pair["source_id"],
                )
            except ConflictError:
                # A repeated delivery of one observation (a retry or a regenerated reply).
                log.info("cement: source %s is already retained", pair["source_id"])
            except CementError as exc:
                notes.append(f"record_answer call {pair['record_call_id']} was not retained: {exc}")
        return notes

    async def inlet(self, body: dict) -> dict:
        """The deployer's system prompt stays fixed: the operations ride the last user message."""

        try:
            operations = _operations(self.valves.operations)
            messages = body.get("messages")
            if not operations or not isinstance(messages, list):
                return body
            index = next(
                (
                    i
                    for i in range(len(messages) - 1, -1, -1)
                    if isinstance(messages[i], dict) and messages[i].get("role") == "user"
                ),
                None,
            )
            if index is None:
                return body
            message = messages[index]
            content = message.get("content")
            note = _note(operations)
            if isinstance(content, str):
                content = f"{content}\n\n{note}"
            elif isinstance(content, list):
                content = [*content, {"type": "text", "text": note}]
            else:
                return body
            annotated = [*messages[:index], {**message, "content": content}, *messages[index + 1 :]]
            return {**body, "messages": annotated}
        except Exception:  # the chat must never fail because the note did
            log.exception("cement: the operations note failed")
            return body

    async def outlet(
        self,
        body: dict,
        __event_emitter__: Any = None,
        __metadata__: dict | None = None,
        __request__: Any = None,
        __user__: Any = None,
    ) -> dict:
        try:
            # Shadow answers: queued here, answered by the worker; nothing here waits for them.
            hits = self._hits(body)
            if hits:
                self._enqueue(hits, __request__, __user__)
        except Exception:  # the chat must never fail because sampling did
            log.exception("cement: shadow sampling could not queue")
        try:
            pairs, notes = self._pairs(body, __metadata__ or {})
            if pairs:
                notes += await asyncio.to_thread(self._retain, pairs)
        except Exception:  # the chat must never fail because retention did
            log.exception("cement: retention failed")
            notes = ["Cement could not retain this answer; see the server log."]
        for note in notes:
            log.warning("cement: %s", note)
            if __event_emitter__ is not None:
                try:
                    await __event_emitter__(
                        {"type": "notification", "data": {"type": "warning", "content": note}}
                    )
                except Exception:  # a closed socket must not fail the outlet
                    log.exception("cement: notification failed")
        return body
