"""
title: Cement switch
author: Cement
version: 0.1.0
license: Apache-2.0
description: Admin-only button that sets up Cement operations and switches each learned function.
"""

from __future__ import annotations

import asyncio
import datetime
import os
from typing import Any

from pydantic import BaseModel, Field

from cement_runtime import CementError, NotFoundError, System

PAGE = 100


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


def _when(microseconds: int) -> str:
    moment = datetime.datetime.fromtimestamp(microseconds / 1_000_000, tz=datetime.UTC)
    return moment.strftime("%Y-%m-%d %H:%M UTC")


class Action:
    class Valves(BaseModel):
        ledger_path: str = Field(default="", description="Path of the Cement ledger file.")
        partition: str = Field(default="", description="Cement partition of this deployment.")
        operations: str = Field(
            default="",
            description="Operations to manage: one per line, `name` or `name: description`.",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _choices(self) -> tuple[list[str], list[dict[str, str]]]:
        """The status lines and the select options, from one read of the ledger."""

        lines: list[str] = []
        options: list[dict[str, str]] = []
        names = list(_operations(self.valves.operations))
        system = (
            System(self.valves.ledger_path, create=False)
            if os.path.isfile(self.valves.ledger_path)
            else None
        )
        for name in names:
            try:
                state = None if system is None else system.switch(self.valves.partition, name)
            except NotFoundError:
                state = None
            if system is None or state is None:
                lines.append(f"- {name}: not set up")
                options.append(
                    {"label": f"Set up {name} (its switch starts off)", "value": f"register|{name}"}
                )
                continue
            # Every receipt, so a person can pin any earlier version and the numbers hold.
            versions = []
            before = None
            while True:
                page = system.function_versions(
                    self.valves.partition, name, before_sequence=before, limit=PAGE, check=True
                )
                versions += page.versions
                if page.next_before_sequence is None:
                    break
                before = page.next_before_sequence
            numbered = {
                version.receipt.function_hash: len(versions) - index
                for index, version in enumerate(versions)
            }
            if state.mode == "off":
                status = "off"
            elif state.mode == "follow":
                status = "on, following the newest version"
            else:
                status = f"pinned to version {numbered.get(state.function_hash or '', '?')}"
            lines.append(f"- {name}: {status}; {len(versions)} version(s)")
            if state.mode != "off":
                options.append({"label": f"Switch {name} off", "value": f"off|{name}"})
            if versions and state.mode != "follow":
                newest = versions[0].receipt
                options.append(
                    {
                        "label": f"Switch {name} on: follow the newest version"
                        f" (version {len(versions)}, {newest.member_count} cases)",
                        "value": f"follow|{name}",
                    }
                )
            for version in versions:
                receipt = version.receipt
                if state.mode == "pinned" and state.function_hash == receipt.function_hash:
                    continue
                if version.servable is False:
                    continue
                options.append(
                    {
                        "label": f"Pin {name} to version {numbered[receipt.function_hash]}"
                        f" ({receipt.member_count} cases, {_when(receipt.promoted_at_us)},"
                        f" {receipt.function_hash[:12]})",
                        "value": f"pinned|{name}|{receipt.function_hash}",
                    }
                )
        return lines, options

    def _apply(self, choice: str, actor: str) -> str:
        mode, name, *rest = choice.split("|")
        if mode == "register":
            # The ledger lives in Open WebUI's data volume; its directory may not exist yet.
            os.makedirs(os.path.dirname(os.path.abspath(self.valves.ledger_path)), exist_ok=True)
            System(self.valves.ledger_path).register_operation(
                self.valves.partition, name, registered_by=actor
            )
            return f"{name} is set up. Its switch is off until you switch it on."
        state = System(self.valves.ledger_path, create=False).set_switch(
            self.valves.partition,
            name,
            mode=mode,
            actor=actor,
            function_hash=rest[0] if rest else None,
        )
        if state.mode == "off":
            return f"{name} is off. The chat model answers every request of this kind."
        if state.mode == "follow":
            return f"{name} is on and follows the newest version."
        return f"{name} is pinned to {state.function_hash}."

    async def action(
        self,
        body: dict,  # noqa: ARG002 — Open WebUI passes the message body by this keyword
        __user__: dict | None = None,
        __event_call__: Any = None,
        __event_emitter__: Any = None,
    ) -> None:
        async def notify(kind: str, content: str) -> None:
            if __event_emitter__ is not None:
                await __event_emitter__(
                    {"type": "notification", "data": {"type": kind, "content": content}}
                )

        user = __user__ or {}
        if user.get("role") != "admin":
            await notify("error", "Only an administrator can switch a Cement function.")
            return
        if __event_call__ is None:
            await notify("error", "This Open WebUI session cannot show a dialog.")
            return
        try:
            lines, options = await asyncio.to_thread(self._choices)
        except CementError as exc:
            await notify("error", f"Cement could not read its ledger: {exc}")
            return
        if not options:
            await notify("info", "No Cement operation is configured in this button's valves.")
            return
        choice = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": "Cement functions",
                    "message": "\n".join(["Current state:", *lines]),
                    "type": "select",
                    "options": options,
                    "placeholder": "Choose a change",
                },
            }
        )
        label = next((o["label"] for o in options if o["value"] == choice), None)
        if label is None:
            await notify("info", "Nothing changed.")
            return
        confirmed = await __event_call__(
            {"type": "confirmation", "data": {"title": "Confirm the change", "message": label}}
        )
        if confirmed is not True:
            await notify("info", "Nothing changed.")
            return
        actor = f"open-webui:{user.get('id')}"
        try:
            message = await asyncio.to_thread(self._apply, choice, actor)
        except CementError as exc:
            await notify("error", f"Cement refused the change: {exc}")
            return
        await notify("success", message)
