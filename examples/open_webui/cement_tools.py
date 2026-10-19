"""
title: Cement learned functions
author: Cement
version: 0.2.0
license: Apache-2.0
description: Answers a request from a switched-on learned function, or asks the model to record it.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from cement_runtime import CementError, System, ValidationError
from cement_runtime.json_value import canonicalize

MISS_INSTRUCTION = (
    "No learned function covers this request. Answer it yourself. Then call record_answer with"
    " the same operation and input and the structured output that your answer used."
)


def _allowed(operations: str) -> set[str]:
    return {name.strip() for name in operations.split(",") if name.strip()}


class Tools:
    class Valves(BaseModel):
        ledger_path: str = Field(default="", description="Path of the existing Cement ledger file.")
        partition: str = Field(default="", description="Cement partition of this deployment.")
        operations: str = Field(
            default="", description="Comma-separated operations that the model can use."
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _check(self, operation: str, input: Any) -> str | None:
        if operation not in _allowed(self.valves.operations):
            return f"operation {operation!r} is not enabled for this deployment"
        try:
            canonicalize(input)
        except ValidationError as exc:
            return f"input is not canonical JSON: {exc}"
        return None

    def _resolve(self, operation: str, input: Any) -> dict[str, Any]:
        resolution = System(self.valves.ledger_path, create=False).resolve(
            self.valves.partition, operation, input
        )
        verification = resolution.verification
        if resolution.switch.mode == "off" or verification is None:
            reason = "off"
        elif not verification.passed:
            reason = "failed"
        elif verification.entries == 0:
            reason = "absent"
        elif resolution.match is not None and resolution.match.matched:
            return {
                "covered": True,
                "output": resolution.match.output,
                "function_hash": verification.function_hash,
            }
        else:
            reason = "unrecognized"
        return {"covered": False, "reason": reason, "instruction": MISS_INSTRUCTION}

    async def use_learned_function(self, operation: str, input: dict) -> dict:
        """
        Answer a request from a learned Cement function. Call this first for every request of an
        enabled operation. When the result says covered, use its output as the answer. When it
        says not covered, answer yourself and then call record_answer.
        :param operation: The Cement operation that names the kind of request.
        :param input: The exact structured input of the request, as a JSON object.
        """

        problem = self._check(operation, input)
        if problem is not None:
            return {"covered": False, "reason": "invalid", "error": problem}
        try:
            return await asyncio.to_thread(self._resolve, operation, input)
        except CementError as exc:
            # A ledger the deployment cannot read answers nothing; the model answers instead.
            return {
                "covered": False,
                "reason": "failed",
                "error": str(exc),
                "instruction": MISS_INSTRUCTION,
            }

    async def record_answer(self, operation: str, input: dict, output: dict) -> dict:
        """
        Record the structured output that you used to answer a request that no learned function
        covered. Call this once, after use_learned_function said not covered, with the same
        operation and input.
        :param operation: The Cement operation of the request.
        :param input: The same input that you passed to use_learned_function.
        :param output: The structured output that your answer used, as a JSON object.
        """

        # Writes nothing: the filter retains the pair once the response completes (contract §7).
        problem = self._check(operation, input)
        if problem is None:
            try:
                canonicalize(output)
            except ValidationError as exc:
                problem = f"output is not canonical JSON: {exc}"
        if problem is not None:
            return {"accepted": False, "error": problem}
        return {"accepted": True}
