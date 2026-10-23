"""Caller-side outbox: keep a submission intent durable until Cement records it (p37).

Lost-intent protection only. The relay delivers each intent at least once: a crash after Cement
commits and before the outbox acknowledges repeats the delivery. A keyed relay passes the intent
id as `source_id`, so Cement refuses the repeat with `ConflictError` naming the first proposal; an
unkeyed relay writes a second proposal. Neither makes submission exactly-once.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Callable, Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from cement_runtime import Candidate, ConflictError, System
from cement_runtime.json_value import JSONValue, canonicalize

SCHEMA = """
CREATE TABLE IF NOT EXISTS intents (
    id TEXT PRIMARY KEY,
    digest TEXT NOT NULL,
    envelope TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'delivered', 'stale')),
    proposal_id TEXT,
    attempts INTEGER NOT NULL DEFAULT 0
) STRICT
"""
# `System.submit_proposal`'s refusal of a repeated `source_id`; the stored id travels in the text.
RECORDED = re.compile(r"source observation already recorded as proposal (prop_[0-9a-f]{32})")


class IntentConflictError(Exception):
    """An intent id was reused for different content."""


@dataclass(frozen=True)
class Delivery:
    intent_id: str
    state: str  # `delivered` | `stale`
    proposal_id: str | None
    replayed: bool  # Cement already held the intent's `source_id`: an earlier attempt landed


class Outbox:
    """A SQLite intent table. In a real caller it lives in the caller's own database, written in
    the same transaction as the state that creates the intent."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._write() as connection:
            connection.execute(SCHEMA)

    @contextmanager
    def _write(self) -> Generator[sqlite3.Connection, None, None]:
        with closing(sqlite3.connect(self._path, isolation_level=None)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")

    def record(
        self,
        intent_id: str,
        *,
        partition: str,
        operation: str,
        operation_revision: int,
        input_value: JSONValue,
        output: JSONValue,
        provenance: dict[str, JSONValue],
        source_revision: str,
    ) -> str:
        """Bind `intent_id` to its content; return the content digest.

        The same id with the same content is a no-op; the same id with other content raises
        `IntentConflictError` and writes nothing.
        """
        envelope = canonicalize(
            {
                "candidate": {"output": output, "provenance": provenance},
                "input": input_value,
                "operation": operation,
                "operation_revision": operation_revision,
                "partition": partition,
                "source_revision": source_revision,
            }
        ).text
        digest = hashlib.sha256(envelope.encode("utf-8")).hexdigest()
        with self._write() as connection:
            row = connection.execute(
                "SELECT digest FROM intents WHERE id = ?", (intent_id,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO intents(id, digest, envelope, state) VALUES (?, ?, ?, 'pending')",
                    (intent_id, digest, envelope),
                )
            elif row["digest"] != digest:
                raise IntentConflictError(f"intent {intent_id} is recorded with other content")
        return digest

    def intents(self) -> list[dict[str, object]]:
        with closing(sqlite3.connect(self._path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, state, proposal_id, attempts FROM intents ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def relay(
        self,
        system: System,
        *,
        keyed: bool = True,
        submitted: Callable[[str, str], None] | None = None,
    ) -> list[Delivery]:
        """Deliver every pending intent in id order; `submitted` runs between Cement's commit
        and the acknowledgement (a crash there = the acknowledgement crash)."""

        with closing(sqlite3.connect(self._path)) as connection:
            pending = connection.execute(
                "SELECT id, envelope FROM intents WHERE state = 'pending' ORDER BY id"
            ).fetchall()
        deliveries = []
        for intent_id, envelope in pending:
            intent = json.loads(envelope)
            with self._write() as connection:
                connection.execute(
                    "UPDATE intents SET attempts = attempts + 1 WHERE id = ?", (intent_id,)
                )
            current = next(
                (
                    row["revision"]
                    for row in system.operations(intent["partition"])
                    if row["name"] == intent["operation"]
                ),
                None,
            )
            # `submit_proposal` binds whatever revision is current under Cement's write lock and
            # takes no expected revision, so a revise between this check and the submission
            # still binds the intent to the new revision.
            if current is not None and current != intent["operation_revision"]:
                self._acknowledge(intent_id, "stale", None)
                deliveries.append(Delivery(intent_id, "stale", None, replayed=False))
                continue
            candidate = Candidate(
                output=intent["candidate"]["output"],
                provenance={
                    "intent": intent_id,
                    "reported": intent["candidate"]["provenance"],
                    "source_revision": intent["source_revision"],
                },
            )
            replayed = False
            try:
                proposal_id = system.submit_proposal(
                    intent["partition"],
                    intent["operation"],
                    intent["input"],
                    candidate=candidate,
                    source_id=f"outbox:{intent_id}" if keyed else None,
                )
            except ConflictError as error:
                match = RECORDED.fullmatch(str(error))
                if match is None:
                    raise
                proposal_id, replayed = match.group(1), True
            if submitted is not None:
                submitted(intent_id, proposal_id)
            self._acknowledge(intent_id, "delivered", proposal_id)
            deliveries.append(Delivery(intent_id, "delivered", proposal_id, replayed))
        return deliveries

    def _acknowledge(self, intent_id: str, state: str, proposal_id: str | None) -> None:
        with self._write() as connection:
            connection.execute(
                "UPDATE intents SET state = ?, proposal_id = ? WHERE id = ? AND state = 'pending'",
                (state, proposal_id, intent_id),
            )
