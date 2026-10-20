"""
title: Cement learning pass
author: Cement
version: 0.1.0
license: Apache-2.0
description: Admin-only learning pass steps: review retained answers, publish a new version.
"""

from __future__ import annotations

import asyncio
import dataclasses
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

REVIEWER = "learning-pass"
_KINDS = (
    (NotFoundError, "not_found"),
    (ConflictError, "conflict"),
    (StateError, "conflict"),
    (IntegrityError, "integrity"),
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


def _plain(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return value


def _failure(exc: CementError) -> dict[str, Any]:
    kind = next((name for cls, name in _KINDS if isinstance(exc, cls)), "invalid")
    return {"error": kind, "message": str(exc)}


class Tools:
    class Valves(BaseModel):
        ledger_path: str = Field(default="", description="Path of the existing Cement ledger file.")
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
        self, operation: str, program: dict | None = None, __user__: Any = None
    ) -> dict:
        """
        Read the work list of one operation: its pending proposals and active examples grouped by
        case key, the outputs of each case, and the unfinished steps. Pass a projection program to
        group the inputs by that program instead. Call this first, and again after each step.
        :param operation: The Cement operation.
        :param program: Optional cement-projection-v1 program to group the inputs by.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: system.learning_cases(partition, operation, program=program),
        )

    async def show_proposal(self, proposal_id: str, __user__: Any = None) -> dict:
        """
        Read one retained answer: its input, the output the chat model used, and its provenance
        (the chat model's full reply). Merge from what the reply shows.
        :param proposal_id: The proposal id from learn_cases.
        """

        return await self._run(
            __user__, None, lambda system, partition: system.proposal(partition, proposal_id)
        )

    async def review_proposal(
        self,
        proposal_id: str,
        decision: str,
        note: str,
        output: dict | None = None,
        __user__: Any = None,
        __chat_id__: Any = None,
        __model__: Any = None,
    ) -> dict:
        """
        Review one pending proposal as the learning pass. Use decision "accept" when the proposed
        output equals the merged output, "correct" with the merged output when it differs, and
        "reject" when the answer is not usable for this operation.
        :param proposal_id: The proposal id from learn_cases.
        :param decision: One of "accept", "correct" or "reject".
        :param note: Why: name this pass and what the merge kept.
        :param output: The merged output. Required for "correct", omitted otherwise.
        """

        def step(system: System, partition: str) -> object:
            extra = {} if output is None else {"corrected_output": output}
            return system.review(
                partition,
                proposal_id,
                reviewer=REVIEWER,
                decision=decision,
                note=self._note(note, __chat_id__, __model__),
                **extra,
            )

        return await self._run(__user__, None, step)

    async def supersede_examples(
        self,
        operation: str,
        example_ids: list[str],
        output: dict,
        note: str,
        __user__: Any = None,
        __chat_id__: Any = None,
        __model__: Any = None,
    ) -> dict:
        """
        Replace earlier confirmed examples of one case with a merged output that extends them.
        Each old example gets one new example with the same input. Use it when a merge adds rows
        that an earlier confirmation lacked.
        :param operation: The Cement operation.
        :param example_ids: The active example ids of the case that the merge extends.
        :param output: The merged output.
        :param note: Why: name this pass and what the merge added.
        """

        def step(system: System, partition: str) -> object:
            created = system.supersede_examples(
                partition,
                operation,
                example_ids=example_ids,
                output=output,
                reviewer=REVIEWER,
                note=self._note(note, __chat_id__, __model__),
            )
            return {"example_ids": list(created), "superseded_example_ids": example_ids}

        return await self._run(__user__, operation, step)

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

    async def test_projection(self, operation: str, program: dict, __user__: Any = None) -> dict:
        """
        Preview a projection program against the confirmed and pending inputs. Writes nothing.
        :param operation: The Cement operation.
        :param program: The cement-projection-v1 program.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: system.test_projection(partition, operation, program),
        )

    async def set_projection(self, operation: str, program: dict, __user__: Any = None) -> dict:
        """
        Store a projection program for the operation. Cement refuses a program that fails to
        parse, names a layout that no confirmed example shows, or merges different outputs.
        :param operation: The Cement operation.
        :param program: The cement-projection-v1 program that test_projection accepted.
        """

        return await self._run(
            __user__,
            operation,
            lambda system, partition: system.set_projection(
                partition, operation, program, actor=REVIEWER
            ),
        )

    async def publish_version(self, operation: str, __user__: Any = None) -> dict:
        """
        Compile the confirmed cases, verify the drafts and promote the verified set as a new
        function version. A version never answers until a person switches it on.
        :param operation: The Cement operation.
        """

        def step(system: System, partition: str) -> object:
            compiled = system.compile(partition, operation, compiled_by=REVIEWER)
            drafts = system.verify_drafts(partition, operation, verified_by=REVIEWER)
            report = {"compile": _plain(compiled), "verify_drafts": _plain(drafts)}
            if not drafts.passed:
                return report | {"published": False, "reason": "a draft failed verification"}
            manifest = system.inspect_function_promotion(partition, operation)
            newest = system.function_versions(partition, operation, limit=1).versions
            live = newest[0].receipt.function_hash if newest else None
            report["function_hash"] = manifest.function_hash
            report["cases"] = len(manifest.entries)
            if not manifest.entries:
                return report | {"published": False, "reason": "no case has enough confirmations"}
            if manifest.function_hash == live:
                return report | {
                    "published": False,
                    "reason": "the newest version already holds this set",
                }
            promotion = system.promote_function(
                partition,
                operation,
                expected_function_hash=manifest.function_hash,
                promoted_by=REVIEWER,
            )
            return report | {"published": True, "promotion": _plain(promotion)}

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
