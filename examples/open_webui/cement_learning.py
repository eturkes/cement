"""
title: Cement learning pass
author: Cement
version: 0.3.0
license: Apache-2.0
description: Admin-only learning pass steps: merge retained answers by case, publish a new version.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
from typing import Any

from pydantic import BaseModel, Field

from cement_runtime import (
    CementError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    System,
)
from cement_runtime.learning import REVIEWER, MergeInterruptedError, cases, merge_case, publish
from cement_runtime.shadow import ShadowStore, drift, observations, shadow_path

_KINDS = (
    (NotFoundError, "not_found"),
    (ConflictError, "conflict"),
    (StateError, "conflict"),
    (IntegrityError, "integrity"),
)
_NOT_PUBLISHED = {
    "failed": "a draft failed verification",
    "empty": "no case has enough confirmations",
    "same": "the newest version already holds this set",
}


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


def _plain(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return value


def _failure(exc: CementError) -> dict[str, Any]:
    kind = next((name for cls, name in _KINDS if isinstance(exc, cls)), "invalid")
    return {"error": kind, "message": str(exc)}


def _json_shaped(value: object) -> Any:
    """Tuples become lists, as Open WebUI's own serialization reads them."""

    return json.loads(json.dumps(_plain(value)))


class Tools:
    class Valves(BaseModel):
        ledger_path: str = Field(default="", description="Path of the existing Cement ledger file.")
        shadow_path: str = Field(
            default="", description="Shadow observation file; empty = the ledger path + .shadow."
        )
        partition: str = Field(default="", description="Cement partition of this deployment.")
        operations: str = Field(
            default="",
            description="Operations the learning pass may work on: one per line, `name` or"
            " `name: description`.",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    async def _run(self, user: Any, operation: str | None, step: Any) -> dict[str, Any]:
        if not isinstance(user, dict) or user.get("role") != "admin":
            return {
                "error": "forbidden",
                "message": "Only an administrator can run the learning pass.",
            }
        if operation is not None and operation not in _operations(self.valves.operations):
            return {
                "error": "invalid",
                "message": f"operation {operation!r} is not enabled for the learning pass",
                "enabled_operations": list(_operations(self.valves.operations)),
            }

        def call() -> dict[str, Any]:
            try:
                system = System(self.valves.ledger_path, create=False)
                result = _plain(step(system, self.valves.partition))
            except CementError as exc:
                return _failure(exc)
            return result if isinstance(result, dict) else {"result": result}

        return await asyncio.to_thread(call)

    @staticmethod
    def _note(note: str, chat_id: Any, model: Any) -> str:
        model_id = model.get("id") if isinstance(model, dict) else None
        return f"{note} (Open WebUI chat {chat_id}, model {model_id})"

    async def learn_cases(
        self, operation: str, projectable: bool = False, __user__: Any = None
    ) -> dict:
        """
        Read the work list of one operation: its pending proposals and confirmed examples grouped
        into cases, the distinct outputs of each case, and its support. With projectable true,
        the cases group documents by form layout, and the result shows the derived program.
        :param operation: The Cement operation.
        :param projectable: True when every output is a procedure that reads values from the input.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: cases(system, partition, operation, projectable=projectable),
        )

    async def show_proposal(self, proposal_id: str, __user__: Any = None) -> dict:
        """
        Read one retained answer: its input, the output the chat model used, and its provenance
        (the chat model's full reply).
        :param proposal_id: The proposal id from learn_cases.
        """

        return await self._run(
            __user__, None, lambda system, partition: system.proposal(partition, proposal_id)
        )

    async def merge_case(
        self,
        operation: str,
        projectable: bool,
        output: dict,
        note: str,
        proposal_ids: list[str] | None = None,
        example_ids: list[str] | None = None,
        __user__: Any = None,
        __chat_id__: Any = None,
        __model__: Any = None,
    ) -> dict:
        """
        Confirm the merged output of one case. Each pending proposal of the case is accepted when
        it equals the merge and corrected to the merge otherwise. Each confirmed example whose
        output differs is superseded by the merge. Pass the ids of ONE case from learn_cases,
        with the same projectable value.
        :param operation: The Cement operation.
        :param projectable: The value that you passed to learn_cases.
        :param output: The merged output that covers what every request of the case needed.
        :param note: What the merge kept or added.
        :param proposal_ids: The case's pending proposal ids.
        :param example_ids: The case's active example ids.
        """

        def step(system: System, partition: str) -> object:
            try:
                merged = merge_case(
                    system,
                    partition,
                    operation,
                    output,
                    note=self._note(note, __chat_id__, __model__),
                    proposal_ids=proposal_ids or [],
                    example_ids=example_ids or [],
                    projectable=projectable,
                )
            except MergeInterruptedError as exc:
                # Each write commits alone, so a later refusal must not hide the earlier ones.
                return _failure(exc.cause) | {"completed": _json_shaped(exc.completed)}
            return _json_shaped(merged)

        return await self._run(__user__, operation, step)

    async def reject_proposal(
        self,
        proposal_id: str,
        note: str,
        __user__: Any = None,
        __chat_id__: Any = None,
        __model__: Any = None,
    ) -> dict:
        """
        Reject one pending proposal that is not a usable answer for its operation.
        :param proposal_id: The proposal id from learn_cases.
        :param note: Why the answer is not usable.
        """

        return await self._run(
            __user__,
            None,
            lambda system, partition: system.review(
                partition,
                proposal_id,
                reviewer=REVIEWER,
                decision="reject",
                note=self._note(note, __chat_id__, __model__),
            ),
        )

    async def revoke_example(
        self,
        example_id: str,
        reason: str,
        __user__: Any = None,
        __chat_id__: Any = None,
        __model__: Any = None,
    ) -> dict:
        """
        Withdraw a confirmed example that is wrong. Every version built on it stops answering.
        :param example_id: The active example id.
        :param reason: Why the example is wrong.
        """

        def step(system: System, partition: str) -> object:
            suspended = system.revoke_example(
                partition,
                example_id,
                revoked_by=REVIEWER,
                reason=self._note(reason, __chat_id__, __model__),
            )
            return {"example_id": example_id, "suspended_artifact_ids": list(suspended)}

        return await self._run(__user__, None, step)

    async def publish_version(
        self, operation: str, projectable: bool, __user__: Any = None
    ) -> dict:
        """
        Publish a new function version: store the derived projection program (when projectable),
        compile the confirmed cases, verify them and promote the verified set. A version never
        answers until a person switches it on.
        :param operation: The Cement operation.
        :param projectable: The value that you passed to learn_cases.
        """

        def step(system: System, partition: str) -> object:
            result = publish(system, partition, operation, projectable=projectable)
            report: dict[str, Any] = {"published": result.published}
            if result.projection is not None:
                report |= {"projection": result.projection, "layouts": list(result.layouts)}
            if result.compiled is not None:
                report |= {
                    "compile": _plain(result.compiled),
                    "verify_drafts": _plain(result.drafts),
                }
            if result.function_hash is not None:
                report |= {"function_hash": result.function_hash, "cases": result.entries}
            if result.reason is not None:
                report["reason"] = _NOT_PUBLISHED[result.reason]
            if result.promotion is not None:
                report["promotion"] = _plain(result.promotion)
            return report

        return await self._run(__user__, operation, step)

    async def function_versions(self, operation: str, __user__: Any = None) -> dict:
        """
        List the operation's versions, newest first, with whether each one can serve now.
        :param operation: The Cement operation.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: system.function_versions(partition, operation, check=True),
        )

    def _shadow(self) -> ShadowStore:
        return ShadowStore(
            self.valves.shadow_path or shadow_path(self.valves.ledger_path), create=False
        )

    async def set_comparator(self, operation: str, comparator: dict, __user__: Any = None) -> dict:
        """
        Set the rule that decides when a shadow answer agrees with the function's answer.
        :param operation: The Cement operation.
        :param comparator: {"abi": "cement-comparator-v1", "rules": [{"path": [...], "rule": ...}]}.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: system.set_comparator(
                partition, operation, comparator, actor=REVIEWER
            ),
        )

    async def show_comparator(self, operation: str, __user__: Any = None) -> dict:
        """
        Show the comparator in force for the operation's current revision, or null.
        :param operation: The Cement operation.
        """

        return await self._run(
            __user__, operation, lambda system, partition: system.comparator(partition, operation)
        )

    async def shadow_drift(self, operation: str, __user__: Any = None) -> dict:
        """
        Count the shadow answers of each version that agreed or disagreed with the function.
        :param operation: The Cement operation.
        """

        return await self._run(
            __user__,
            operation,
            lambda _system, partition: drift(self._shadow(), partition, operation),
        )

    async def shadow_observations(
        self, operation: str, state: str = "disagreed", __user__: Any = None
    ) -> dict:
        """
        List up to 100 shadow observations in one state, with both answers.
        :param operation: The Cement operation.
        :param state: admitted, prepared, agreed, disagreed, failed, cancelled or dropped.
        """

        return await self._run(
            __user__,
            operation,
            lambda _system, partition: observations(
                self._shadow(), partition, operation, state=state
            ),
        )

    async def diff_versions(
        self, operation: str, from_hash: str, to_hash: str, __user__: Any = None
    ) -> dict:
        """
        Compare two versions: the cases the second one adds, removes or changes.
        :param operation: The Cement operation.
        :param from_hash: The function hash of the earlier version.
        :param to_hash: The function hash of the later version.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: system.diff_versions(
                partition, operation, from_hash=from_hash, to_hash=to_hash
            ),
        )
