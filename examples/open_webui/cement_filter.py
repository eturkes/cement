"""
title: Cement answer retention
author: Cement
version: 0.2.0
license: Apache-2.0
description: Retains recorded answers to uncovered requests for the Cement learning pass.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from cement_runtime import Candidate, CementError, ConflictError, System, ValidationError
from cement_runtime.json_value import canonicalize
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

    def __init__(self) -> None:
        self.valves = self.Valves()

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
    ) -> dict:
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
