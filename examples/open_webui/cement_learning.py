"""
title: Cement learning pass
author: Cement
version: 0.2.0
license: Apache-2.0
description: Admin-only learning pass steps: merge retained answers by case, publish a new version.
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
    ValidationError,
)
from cement_runtime.json_value import canonicalize
from cement_runtime.projection import structure

REVIEWER = "learning-pass"
PAGE = 1_000
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


def _same(left: object, right: object) -> bool:
    return canonicalize(left).digest == canonicalize(right).digest


def _inputs(system: System, partition: str, operation: str, *, pending: bool) -> list[object]:
    """Raw inputs of the active examples, plus the current pending proposals when asked."""

    revision = system.learning_cases(partition, operation)["operation_revision"]
    found: list[object] = []
    after = 0
    while True:
        page = system.examples(partition, operation, after_sequence=after, limit=PAGE)
        found += [
            row["input"]
            for row in page
            if row["superseded_by"] is None and row["operation_revision"] == revision
        ]
        if len(page) < PAGE:
            break
        after = int(page[-1]["sequence"])
    after = 0
    while pending:
        rows = system.proposals(partition, status="pending", after_sequence=after, limit=PAGE)
        found += [
            row["input"]
            for row in rows
            if row["operation"] == operation and row["operation_revision"] == revision
        ]
        if len(rows) < PAGE:
            break
        after = int(rows[-1]["sequence"])
    return found


def draft_program(inputs: list[object]) -> dict[str, Any]:
    """One cement-projection-v1 layout per distinct title + structure of the raw inputs.

    The learning pass decides that an operation is projectable; the program itself is
    mechanical, so the tool derives it and the model never copies a label.
    """

    fields = {
        name
        for value in inputs
        if isinstance(value, dict)
        for name, text in value.items()
        if isinstance(text, str)
    }
    if (
        not inputs
        or len(fields) != 1
        or any(
            not isinstance(value, dict)
            or set(value) != fields
            or not all(isinstance(text, str) for text in value.values())
            for value in inputs
        )
    ):
        raise ValidationError("a projection needs inputs that hold exactly one text field")
    (field,) = fields
    layouts: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, Any]] = {}
    for value in inputs:
        parsed = structure(value[field])
        if parsed is None or parsed in layouts:
            continue
        title, pairs = parsed
        layouts[parsed] = {
            "name": title.lower(),
            "title": title,
            "entries": [{kind: key} for kind, key in pairs],
        }
    if not layouts:
        raise ValidationError("no input has a form layout that a projection can read")
    return {
        "abi": "cement-projection-v1",
        "text": field,
        "keep": [],
        "layouts": [layouts[key] for key in sorted(layouts)],
    }


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

    @staticmethod
    def _cases(system: System, partition: str, operation: str, projectable: bool) -> dict[str, Any]:
        if not projectable:
            return system.learning_cases(partition, operation)
        program = draft_program(_inputs(system, partition, operation, pending=True))
        return system.learning_cases(partition, operation, program=program) | {"program": program}

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
            lambda system, partition: self._cases(system, partition, operation, projectable),
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

        proposals = list(proposal_ids or [])
        examples = list(example_ids or [])

        def step(system: System, partition: str) -> object:
            if not proposals and not examples:
                raise ValidationError("name the proposal ids or example ids of one case")
            if len(set(proposals)) != len(proposals) or len(set(examples)) != len(examples):
                raise ValidationError("name each id once")
            cases = self._cases(system, partition, operation, projectable)["cases"]
            owner = [
                case
                for case in cases
                if set(proposals) <= set(case["pending_proposal_ids"])
                and set(examples) <= set(case["active_example_ids"])
            ]
            if len(owner) != 1:
                raise ValidationError("the ids are not the pending or active ids of one case")
            canonicalize(output)
            # The case already lists every output with its examples; a paged read could miss one.
            outputs = {
                example: entry["output"]
                for entry in owner[0]["outputs"]
                for example in entry["example_ids"]
            }
            text = self._note(note, __chat_id__, __model__)
            done: dict[str, Any] = {
                "key_hash": owner[0]["key_hash"],
                "reviewed": [],
                "superseded_example_ids": [],
                "new_example_ids": [],
            }
            try:
                for proposal_id in proposals:
                    proposed = system.proposal(partition, proposal_id)["proposed_output"]
                    extra = {} if _same(proposed, output) else {"corrected_output": output}
                    result = system.review(
                        partition,
                        proposal_id,
                        reviewer=REVIEWER,
                        decision="correct" if extra else "accept",
                        note=text,
                        **extra,
                    )
                    done["reviewed"].append({"proposal_id": proposal_id, "status": result.status})
                differing = [example for example in examples if not _same(outputs[example], output)]
                if differing:
                    created = system.supersede_examples(
                        partition,
                        operation,
                        example_ids=differing,
                        output=output,
                        reviewer=REVIEWER,
                        note=text,
                    )
                    done["superseded_example_ids"] = differing
                    done["new_example_ids"] = list(created)
            except CementError as exc:
                # Each write commits alone, so a later refusal must not hide the earlier ones.
                return _failure(exc) | {"completed": done}
            return done

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
            report: dict[str, Any] = {}
            if projectable:
                program = draft_program(_inputs(system, partition, operation, pending=False))
                report["projection"] = system.set_projection(
                    partition, operation, program, actor=REVIEWER
                )
                report["layouts"] = [layout["title"] for layout in program["layouts"]]
            compiled = system.compile(partition, operation, compiled_by=REVIEWER)
            drafts = system.verify_drafts(partition, operation, verified_by=REVIEWER)
            report |= {"compile": _plain(compiled), "verify_drafts": _plain(drafts)}
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
