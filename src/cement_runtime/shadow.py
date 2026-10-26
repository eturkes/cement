"""Shadow observations: an LLM's answer to an input a learned function also answered.

Contract: `.agent/decisions/p136-store-contract.md`. Observations live in their own SQLite file
beside the ledger, so an agreement never commits to the ledger and never makes the serving cache
cold. Admission captures what the comparison needs before any model call: the answer of the version
that served the hit and the comparator in force for its revision. A disagreement is first made
durable as `prepared`, then becomes one pending proposal (source id `shadow:<observation id>`); a
retry finds that proposal by its source id instead of writing a second one. Nothing here switches,
promotes, challenges or edits a function.
"""

from __future__ import annotations

import functools
import hashlib
import os
import sqlite3
import time
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from .comparator import Comparator, compare, parse_comparator
from .errors import ConflictError, IntegrityError, NotFoundError, StateError, ValidationError
from .json_value import JSONValue, canonicalize, parse_json
from .models import Candidate
from .store import _schema_objects
from .system import (
    _MAX_AGE_SECONDS,
    SOURCE_ID_MAX_BYTES,
    System,
    _digest,
    _entity_id,
    _name,
    _stored_int,
    _text,
)

__all__ = [
    "Admission",
    "DriftGroup",
    "DriftReport",
    "ObservationRecord",
    "ShadowErasure",
    "ShadowStore",
    "admit",
    "cancel",
    "drift",
    "drop",
    "fail",
    "finish_shadow",
    "observations",
    "pending",
    "record_shadow",
    "shadow_path",
]

SHADOW_SCHEMA_VERSION = 1
SOURCE_PREFIX = "shadow:"
# The observation id becomes the ledger source id.
OBSERVATION_ID_MAX_BYTES = SOURCE_ID_MAX_BYTES - len(SOURCE_PREFIX)
TEXT_MAX_BYTES = 256
ANSWER_MAX_BYTES = 1_048_576
PROVENANCE_PATHS = 5
_MAX_INT = 2**63 - 1
State = Literal["admitted", "prepared", "agreed", "disagreed", "failed", "cancelled", "dropped"]
STATES: tuple[State, ...] = (
    "admitted",
    "prepared",
    "agreed",
    "disagreed",
    "failed",
    "cancelled",
    "dropped",
)

SHADOW_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS shadow_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS observations (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    partition TEXT NOT NULL,
    operation TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    function_hash TEXT NOT NULL,
    input_json TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN ('admitted', 'prepared', 'agreed', 'disagreed', 'failed', 'cancelled', 'dropped')
    ),
    receipt_id TEXT,
    operation_revision INTEGER CHECK (operation_revision >= 1),
    function_output_json TEXT,
    artifact_hash TEXT,
    comparator_json TEXT,
    comparator_hash TEXT,
    comparator_sequence INTEGER,
    llm_output_json TEXT,
    differences_json TEXT,
    source_id TEXT,
    proposal_id TEXT,
    model TEXT,
    prompt_revision TEXT,
    note TEXT,
    observed_at_us INTEGER NOT NULL CHECK (observed_at_us >= 0),
    admitted_at_us INTEGER NOT NULL CHECK (admitted_at_us >= 0),
    recorded_at_us INTEGER,
    latency_ms INTEGER CHECK (latency_ms >= 0),
    UNIQUE (partition, operation, observation_id),
    CHECK ((state = 'dropped') = (receipt_id IS NULL)),
    CHECK ((receipt_id IS NULL) = (function_output_json IS NULL)),
    CHECK ((receipt_id IS NULL) = (operation_revision IS NULL)),
    CHECK ((comparator_json IS NULL) = (comparator_hash IS NULL)),
    CHECK ((comparator_json IS NULL) = (comparator_sequence IS NULL)),
    CHECK (state NOT IN ('agreed', 'prepared', 'disagreed') OR (
        llm_output_json IS NOT NULL AND differences_json IS NOT NULL AND model IS NOT NULL
        AND prompt_revision IS NOT NULL AND latency_ms IS NOT NULL AND recorded_at_us IS NOT NULL)),
    CHECK ((state IN ('prepared', 'disagreed')) = (source_id IS NOT NULL)),
    CHECK (state NOT IN ('failed', 'cancelled', 'dropped') OR note IS NOT NULL)
) STRICT;

CREATE TABLE IF NOT EXISTS duplicates (
    partition TEXT NOT NULL,
    operation TEXT NOT NULL,
    count INTEGER NOT NULL CHECK (count >= 1),
    last_at_us INTEGER NOT NULL,
    PRIMARY KEY (partition, operation)
) STRICT;

CREATE INDEX IF NOT EXISTS observations_scope
    ON observations(partition, operation, sequence);
CREATE INDEX IF NOT EXISTS observations_state
    ON observations(state, sequence);

CREATE TRIGGER IF NOT EXISTS observations_state_lifecycle
BEFORE UPDATE OF state ON observations
WHEN NOT (
    NEW.state = OLD.state
    OR (OLD.state = 'admitted' AND NEW.state IN ('agreed', 'prepared', 'failed', 'cancelled'))
    OR (OLD.state = 'prepared' AND NEW.state = 'disagreed')
)
BEGIN
    SELECT RAISE(ABORT, 'invalid observation state transition');
END;
CREATE TRIGGER IF NOT EXISTS observations_capture_immutable
BEFORE UPDATE OF
    sequence, id, partition, operation, observation_id, function_hash, input_json, input_hash,
    receipt_id, operation_revision, function_output_json, artifact_hash, comparator_json,
    comparator_hash, comparator_sequence, observed_at_us, admitted_at_us
ON observations BEGIN
    SELECT RAISE(ABORT, 'an observation keeps its identity and capture');
END;
CREATE TRIGGER IF NOT EXISTS shadow_metadata_no_update
BEFORE UPDATE ON shadow_metadata BEGIN
    SELECT RAISE(ABORT, 'shadow metadata is immutable');
END;
CREATE TRIGGER IF NOT EXISTS shadow_metadata_no_delete
BEFORE DELETE ON shadow_metadata BEGIN
    SELECT RAISE(ABORT, 'shadow metadata is immutable');
END;
"""

SHADOW_FINGERPRINT = hashlib.sha256(SHADOW_SCHEMA.encode("utf-8")).hexdigest()
_METADATA_KEY = f"cement-shadow-v{SHADOW_SCHEMA_VERSION}"


def shadow_path(ledger: str | os.PathLike[str]) -> Path:
    """The shadow store that belongs beside a ledger file."""

    return Path(f"{os.fspath(ledger)}.shadow")


def _statements(script: str) -> Iterator[str]:
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            yield statement
            statement = ""


@functools.cache
def _expected_objects() -> dict[tuple[str, str], str]:
    # Built once: the filter opens the store once per sampled hit.
    connection = sqlite3.connect(":memory:")
    try:
        for statement in _statements(SHADOW_SCHEMA):
            connection.execute(statement)
        return _schema_objects(connection)
    finally:
        connection.close()


def _bounded_text(value: object, label: str, maximum: int) -> str:
    if type(value) is not str or not value:
        raise ValidationError(f"{label} must be non-empty text")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValidationError(f"{label} must contain valid Unicode scalar values") from None
    if size > maximum:
        raise ValidationError(f"{label} exceeds {maximum} UTF-8 bytes")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValidationError(f"{label} must not contain control characters")
    return value


def _bounded_int(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_INT:
        raise ValidationError(f"{label} must be an integer from 0 to {_MAX_INT}")
    return value


def _now_us() -> int:
    return time.time_ns() // 1_000


class ShadowStore:
    """The shadow observation file. Connections are short-lived, as in the ledger's store."""

    def __init__(self, path: str | os.PathLike[str], *, create: bool = True) -> None:
        if type(create) is not bool:
            raise ValidationError("create must be a boolean")
        try:
            self.path = Path(path)
        except (TypeError, ValueError) as exc:
            raise ValidationError("shadow store path must be text or a path-like value") from exc
        text = str(self.path)
        if "\0" in text or text == ":memory:":
            raise ValidationError("shadow store path must name a file")
        try:
            self.path = self.path.absolute()  # as `Store`: a later `chdir` keeps this file
        except OSError as exc:
            raise ValidationError("shadow store path is relative to a missing directory") from exc
        if self.path.is_symlink():
            raise ValidationError("shadow store path must not be a symbolic link")
        if self.path.exists() and not self.path.is_file():
            raise ValidationError("shadow store path must identify a regular file")
        if not self.path.exists():
            if not create:
                raise NotFoundError("shadow store file is missing")
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            except OSError as exc:
                raise ValidationError("shadow store path could not be created safely") from exc
            else:
                try:
                    os.fchmod(descriptor, 0o600)  # as `Store`: the umask masks `os.open`'s mode
                finally:
                    os.close(descriptor)
        self._open(initialize=create)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA synchronous = EXTRA")
            connection.execute("PRAGMA temp_store = MEMORY")
            connection.execute("PRAGMA trusted_schema = OFF")
            # A pruned or erased observation leaves no copy in the file (as in the ledger).
            connection.execute("PRAGMA secure_delete = ON")
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
        except Exception:
            connection.close()
            raise
        return connection

    def _open(self, *, initialize: bool) -> None:
        try:
            with self.transaction() as connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version == 0:
                    # As the ledger: only a creating open initializes, and only a pristine file.
                    if (
                        not initialize
                        or connection.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
                        or int(connection.execute("PRAGMA application_id").fetchone()[0]) != 0
                    ):
                        raise IntegrityError("the file is not a Cement shadow store")
                    for statement in _statements(SHADOW_SCHEMA):
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO shadow_metadata(key, value) VALUES (?, ?)",
                        (_METADATA_KEY, SHADOW_FINGERPRINT),
                    )
                    connection.execute(f"PRAGMA user_version = {SHADOW_SCHEMA_VERSION}")
                elif (
                    connection.execute(
                        "SELECT 1 FROM sqlite_master WHERE type = 'table'"
                        " AND name = 'shadow_metadata'"
                    ).fetchone()
                    is None
                ):
                    raise IntegrityError("the file is not a Cement shadow store")
                elif version != SHADOW_SCHEMA_VERSION:
                    raise IntegrityError(f"shadow store schema {version} is unsupported")
                try:
                    stored = connection.execute(
                        "SELECT value FROM shadow_metadata WHERE key = ?", (_METADATA_KEY,)
                    ).fetchone()
                except sqlite3.DatabaseError:
                    raise IntegrityError("the file is not a Cement shadow store") from None
                if stored is None or stored[0] != SHADOW_FINGERPRINT:
                    raise IntegrityError("shadow store schema fingerprint mismatch")
                if _schema_objects(connection) != _expected_objects():
                    raise IntegrityError("shadow store schema does not match the runtime schema")
            # Journal policy changes only after identity is established (as the ledger): a file an
            # operator switched to WAL returns to a rollback journal.
            connection = self._connect()
            try:
                connection.execute("PRAGMA journal_mode = DELETE")
            finally:
                connection.close()
        except StateError:
            raise
        except sqlite3.OperationalError as exc:
            raise StateError("shadow store is busy or unavailable") from exc
        except sqlite3.DatabaseError as exc:
            raise IntegrityError("the file is not a Cement shadow store") from exc

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """One write-locked transaction; a raised exception rolls it back."""

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            connection.commit()
        except sqlite3.OperationalError as exc:
            raise StateError("shadow store is busy or unavailable") from exc
        finally:
            connection.close()

    def prune(self, partition: str, *, older_than_seconds: int) -> int:
        """Delete the partition's observations observed before now minus the age, every state;
        returns the count. A pruned identity can be admitted again."""

        partition = _name(partition, "partition")
        if type(older_than_seconds) is not int or not 0 <= older_than_seconds <= _MAX_AGE_SECONDS:
            raise ValidationError(
                f"older_than_seconds must be an integer from 0 to {_MAX_AGE_SECONDS}"
            )
        with self.transaction() as connection:
            cutoff = _now_us() - older_than_seconds * 1_000_000
            return int(
                connection.execute(
                    "DELETE FROM observations WHERE partition = ? AND observed_at_us < ?",
                    (partition, cutoff),
                ).rowcount
            )

    def erase(self, partition: str) -> ShadowErasure:
        """Delete every observation and the duplicate counters of the partition."""

        partition = _name(partition, "partition")
        with self.transaction() as connection:
            return {
                "observations": int(
                    connection.execute(
                        "DELETE FROM observations WHERE partition = ?", (partition,)
                    ).rowcount
                ),
                "duplicates": int(
                    connection.execute(
                        "DELETE FROM duplicates WHERE partition = ?", (partition,)
                    ).rowcount
                ),
            }


class ShadowErasure(TypedDict):
    observations: int
    duplicates: int


@dataclass(frozen=True, slots=True)
class Admission:
    """``admitted`` False = the observation id was already admitted; ``id`` names that row."""

    admitted: bool
    id: str


class ObservationRecord(TypedDict):
    sequence: int
    id: str
    partition: str
    operation: str
    observation_id: str
    function_hash: str
    input: JSONValue
    state: State
    receipt_id: str | None
    operation_revision: int | None
    function_output: JSONValue
    comparator_hash: str | None
    comparator_sequence: int | None
    llm_output: JSONValue
    differences: list[str]
    source_id: str | None
    proposal_id: str | None
    model: str | None
    prompt_revision: str | None
    note: str | None
    observed_at_us: int
    admitted_at_us: int
    recorded_at_us: int | None
    latency_ms: int | None


class DriftGroup(TypedDict):
    function_hash: str
    first_sequence: int
    counts: dict[str, int]


class DriftReport(TypedDict):
    partition: str
    operation: str
    since_us: int | None
    groups: list[DriftGroup]
    totals: dict[str, int]
    disagreements: int
    duplicates: int


def _scope(partition: str, operation: str) -> tuple[str, str]:
    return _name(partition, "partition"), _name(operation, "operation")


def _observation_id(value: str) -> str:
    # The source id grammar: a disagreement's proposal carries `shadow:<observation id>`, and an id
    # graded for Cc alone (a U+200B) left its observation `prepared` for good.
    return _text(value, "observation_id", maximum=OBSERVATION_ID_MAX_BYTES)


def _row_id(value: str) -> str:
    return _entity_id(value, "observation")


_INSERT_COLUMNS = (
    "id",
    "partition",
    "operation",
    "observation_id",
    "function_hash",
    "input_json",
    "input_hash",
    "state",
    "receipt_id",
    "operation_revision",
    "function_output_json",
    "artifact_hash",
    "comparator_json",
    "comparator_hash",
    "comparator_sequence",
    "note",
    "observed_at_us",
    "admitted_at_us",
)
_INSERT = (
    f"INSERT INTO observations({', '.join(_INSERT_COLUMNS)})"  # noqa: S608 — a fixed column list
    f" VALUES ({', '.join('?' for _ in _INSERT_COLUMNS)})"
)


def _insert(store: ShadowStore, values: dict[str, object]) -> Admission:
    """One new row, or — for a repeated identity — the duplicate counter + 1 and the original id."""

    now = cast(int, values["admitted_at_us"])
    with store.transaction() as connection:
        existing = connection.execute(
            "SELECT id FROM observations"
            " WHERE partition = ? AND operation = ? AND observation_id = ?",
            (values["partition"], values["operation"], values["observation_id"]),
        ).fetchone()
        if existing is not None:
            connection.execute(
                """
                INSERT INTO duplicates(partition, operation, count, last_at_us)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(partition, operation)
                DO UPDATE SET count = count + 1, last_at_us = excluded.last_at_us
                """,
                (values["partition"], values["operation"], now),
            )
            return Admission(admitted=False, id=str(existing["id"]))
        connection.execute(_INSERT, tuple(values.get(column) for column in _INSERT_COLUMNS))
    return Admission(admitted=True, id=cast(str, values["id"]))


def admit(
    system: System,
    store: ShadowStore,
    partition: str,
    operation: str,
    *,
    observation_id: str,
    function_hash: str,
    input_value: object,
    observed_at_us: int,
) -> Admission:
    """Admit one hit before any model work, capturing the answer of the version that served it
    and the comparator in force for its revision. A repeated observation id writes no row, counts
    one duplicate and returns the original row's id."""

    partition, operation = _scope(partition, operation)
    observation_id = _observation_id(observation_id)
    observed_at_us = _bounded_int(observed_at_us, "observed_at_us")
    canonical = canonicalize(input_value)
    capture = system.shadow_capture(
        partition, operation, function_hash=function_hash, input_value=input_value
    )
    comparator = capture.comparator
    return _insert(
        store,
        {
            "id": "ob_" + os.urandom(16).hex(),
            "partition": partition,
            "operation": operation,
            "observation_id": observation_id,
            "function_hash": capture.function_hash,
            "input_json": canonical.text,
            "input_hash": canonical.digest,
            "state": "admitted",
            "receipt_id": capture.receipt_id,
            "operation_revision": capture.operation_revision,
            "function_output_json": canonicalize(capture.output).text,
            "artifact_hash": capture.artifact_hash,
            "comparator_json": None
            if comparator is None
            else canonicalize(comparator["comparator"]).text,
            "comparator_hash": None if comparator is None else comparator["comparator_hash"],
            "comparator_sequence": None if comparator is None else comparator["sequence"],
            "observed_at_us": observed_at_us,
            "admitted_at_us": _now_us(),
        },
    )


def drop(
    store: ShadowStore,
    partition: str,
    operation: str,
    *,
    observation_id: str,
    function_hash: str,
    input_value: object,
    observed_at_us: int,
    reason: str,
) -> Admission:
    """Record a hit that never reached the model (a full queue) as ``dropped``, without capture."""

    partition, operation = _scope(partition, operation)
    observation_id = _observation_id(observation_id)
    canonical = canonicalize(input_value)
    return _insert(
        store,
        {
            "id": "ob_" + os.urandom(16).hex(),
            "partition": partition,
            "operation": operation,
            "observation_id": observation_id,
            "function_hash": _digest(function_hash, "function_hash"),
            "input_json": canonical.text,
            "input_hash": canonical.digest,
            "state": "dropped",
            "note": _bounded_text(reason, "reason", TEXT_MAX_BYTES),
            "observed_at_us": _bounded_int(observed_at_us, "observed_at_us"),
            "admitted_at_us": _now_us(),
        },
    )


def _leave_admitted(
    store: ShadowStore, ident: str, state: State, fields: dict[str, object]
) -> None:
    assignments = ", ".join(f"{column} = ?" for column in fields)
    statement = (
        f"UPDATE observations SET state = ?, {assignments} WHERE id = ? AND state = 'admitted'"  # noqa: S608 — fixed column names
    )
    with store.transaction() as connection:
        if connection.execute(statement, (state, *fields.values(), ident)).rowcount != 1:
            raise ConflictError("the observation is not admitted")


def cancel(store: ShadowStore, ident: str, *, reason: str) -> None:
    """``admitted`` → ``cancelled``: admitted work that will not reach the model (a shutdown)."""

    ident = _row_id(ident)
    note = _bounded_text(reason, "reason", TEXT_MAX_BYTES)
    _leave_admitted(store, ident, "cancelled", {"note": note, "recorded_at_us": _now_us()})


def fail(
    store: ShadowStore,
    ident: str,
    *,
    reason: str,
    model: str,
    prompt_revision: str,
    latency_ms: int,
) -> None:
    """``admitted`` → ``failed``: the model call failed, timed out or gave no usable answer."""

    ident = _row_id(ident)
    fields: dict[str, object] = {
        "note": _bounded_text(reason, "reason", TEXT_MAX_BYTES),
        "model": _bounded_text(model, "model", TEXT_MAX_BYTES),
        "prompt_revision": _bounded_text(prompt_revision, "prompt_revision", TEXT_MAX_BYTES),
        "latency_ms": _bounded_int(latency_ms, "latency_ms"),
        "recorded_at_us": _now_us(),
    }
    _leave_admitted(store, ident, "failed", fields)


def _json(text: object, label: str) -> JSONValue:
    if text is None:
        return None
    try:
        return parse_json(str(text), max_bytes=ANSWER_MAX_BYTES).value
    except ValidationError as exc:
        raise IntegrityError(f"stored {label} is invalid") from exc


def _captured_comparator(row: sqlite3.Row) -> Comparator | None:
    """The comparator an observation captured, re-checked against its stored hash."""

    if row["comparator_json"] is None:
        return None
    try:
        comparator = parse_comparator(_json(row["comparator_json"], "comparator"))
    except ValidationError:
        raise IntegrityError("stored comparator is invalid") from None
    if comparator.comparator_hash != row["comparator_hash"]:
        raise IntegrityError("stored comparator does not match its hash")
    return comparator


def _record(row: sqlite3.Row) -> ObservationRecord:
    input_value = _json(row["input_json"], "input")
    if canonicalize(input_value).digest != row["input_hash"]:
        raise IntegrityError("stored observation input does not match its hash")
    _captured_comparator(row)
    state = str(row["state"])
    if state not in STATES:
        raise IntegrityError("stored observation state is invalid")
    differences = _json(row["differences_json"], "differences")
    if differences is not None and not (
        isinstance(differences, list) and all(isinstance(path, str) for path in differences)
    ):
        raise IntegrityError("stored observation differences are invalid")

    def number(name: str, minimum: int = 0) -> int | None:
        value = row[name]
        return None if value is None else _stored_int(value, f"observation {name}", minimum=minimum)

    def text(name: str) -> str | None:
        value = row[name]
        return None if value is None else str(value)

    return {
        "sequence": _stored_int(row["sequence"], "observation sequence", minimum=1),
        "id": str(row["id"]),
        "partition": str(row["partition"]),
        "operation": str(row["operation"]),
        "observation_id": str(row["observation_id"]),
        "function_hash": str(row["function_hash"]),
        "input": input_value,
        "state": state,
        "receipt_id": text("receipt_id"),
        "operation_revision": number("operation_revision", 1),
        "function_output": _json(row["function_output_json"], "function output"),
        "comparator_hash": text("comparator_hash"),
        "comparator_sequence": number("comparator_sequence", 1),
        "llm_output": _json(row["llm_output_json"], "LLM output"),
        "differences": [] if differences is None else cast(list[str], differences),
        "source_id": text("source_id"),
        "proposal_id": text("proposal_id"),
        "model": text("model"),
        "prompt_revision": text("prompt_revision"),
        "note": text("note"),
        "observed_at_us": _stored_int(row["observed_at_us"], "observation observed_at_us"),
        "admitted_at_us": _stored_int(row["admitted_at_us"], "observation admitted_at_us"),
        "recorded_at_us": number("recorded_at_us"),
        "latency_ms": number("latency_ms"),
    }


def _row(connection: sqlite3.Connection, ident: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM observations WHERE id = ?", (ident,)).fetchone()
    if row is None:
        raise NotFoundError("the observation does not exist")
    return cast(sqlite3.Row, row)


def record_shadow(
    system: System,
    store: ShadowStore,
    ident: str,
    *,
    llm_output: object,
    model: str,
    prompt_revision: str,
    latency_ms: int,
) -> ObservationRecord:
    """Record the LLM's answer for an admitted observation and decide agreement against the
    CAPTURED answer + comparator. An agreement writes the shadow store alone; a disagreement is
    made durable as ``prepared`` and then finished into one pending proposal (``finish_shadow``)."""

    ident = _row_id(ident)
    answer = canonicalize(llm_output, max_bytes=ANSWER_MAX_BYTES)
    model = _bounded_text(model, "model", TEXT_MAX_BYTES)
    prompt_revision = _bounded_text(prompt_revision, "prompt_revision", TEXT_MAX_BYTES)
    latency_ms = _bounded_int(latency_ms, "latency_ms")
    with store.transaction() as connection:
        row = _row(connection, ident)
        if row["state"] != "admitted":
            raise ConflictError(f"the observation is {row['state']}, not admitted")
        verdict = compare(
            _captured_comparator(row),
            _json(row["function_output_json"], "function output"),
            answer.value,
        )
        connection.execute(
            """
            UPDATE observations SET state = ?, llm_output_json = ?, differences_json = ?,
                source_id = ?, model = ?, prompt_revision = ?, latency_ms = ?, recorded_at_us = ?
            WHERE id = ? AND state = 'admitted'
            """,
            (
                "agreed" if verdict.agreed else "prepared",
                answer.text,
                canonicalize(list[JSONValue](verdict.paths)).text,
                None if verdict.agreed else SOURCE_PREFIX + str(row["observation_id"]),
                model,
                prompt_revision,
                latency_ms,
                _now_us(),
                ident,
            ),
        )
        if verdict.agreed:
            return _record(_row(connection, ident))
    return finish_shadow(system, store, ident)


def _provenance(row: sqlite3.Row, differences: list[str]) -> dict[str, JSONValue]:
    shadow: dict[str, JSONValue] = {
        "observation_id": str(row["observation_id"]),
        "function_hash": str(row["function_hash"]),
        "receipt_id": str(row["receipt_id"]),
        "comparator_hash": None if row["comparator_hash"] is None else str(row["comparator_hash"]),
        "model": str(row["model"]),
        "prompt_revision": str(row["prompt_revision"]),
        "difference_count": len(differences),
        "differences": list[JSONValue](differences[:PROVENANCE_PATHS]),
    }
    return {"shadow": shadow}


def _matches(
    existing: Any,
    row: sqlite3.Row,
    answer_digest: str,
    revision: int,
    provenance: dict[str, JSONValue],
) -> bool:
    # An earlier attempt wrote exactly this provenance from the same prepared row.
    return bool(
        canonicalize(existing["input"]).digest == row["input_hash"]
        and canonicalize(existing["proposed_output"]).digest == answer_digest
        and existing["operation_revision"] == revision
        and canonicalize(existing["provenance"]).digest == canonicalize(provenance).digest
    )


def finish_shadow(system: System, store: ShadowStore, ident: str) -> ObservationRecord:
    """Turn a ``prepared`` disagreement into one pending proposal and mark it ``disagreed``.

    Lock order: the shadow store, then the ledger. An earlier attempt's proposal is found by its
    source id in any status and must match the prepared payload (``ConflictError`` otherwise; the
    row stays ``prepared``). A captured revision that is no longer current writes no proposal.
    """

    ident = _row_id(ident)
    with store.transaction() as connection:
        row = _row(connection, ident)
        if row["state"] != "prepared":
            raise ConflictError(f"the observation is {row['state']}, not prepared")
        partition, operation = str(row["partition"]), str(row["operation"])
        source_id = str(row["source_id"])
        answer = canonicalize(_json(row["llm_output_json"], "LLM output"))
        revision = int(row["operation_revision"])
        paths = _json(row["differences_json"], "differences")
        differences = [str(path) for path in paths] if isinstance(paths, list) else []
        proposal_id: str | None = None
        note: str | None = None
        existing = system.proposal_by_source(partition, operation, source_id)
        if existing is not None:
            if not _matches(existing, row, answer.digest, revision, _provenance(row, differences)):
                raise ConflictError(
                    f"source id {source_id} names a proposal that does not match this observation"
                )
            proposal_id = existing["id"]
        else:
            current = next(
                (
                    record["revision"]
                    for record in system.operations(partition)
                    if record["name"] == operation
                ),
                None,
            )
            if current != revision:
                note = f"no proposal: the operation moved from revision {revision} to {current}"
            else:
                try:
                    proposal_id = system.submit_proposal(
                        partition,
                        operation,
                        _json(row["input_json"], "input"),
                        candidate=Candidate(
                            output=answer.value, provenance=_provenance(row, differences)
                        ),
                        source_id=source_id,
                        expected_revision=revision,
                    )
                except StateError as exc:
                    if "revision" not in str(exc):
                        raise
                    note = f"no proposal: {exc}"
        connection.execute(
            """
            UPDATE observations SET state = 'disagreed', proposal_id = ?, note = ?
            WHERE id = ? AND state = 'prepared'
            """,
            (proposal_id, note, ident),
        )
        return _record(_row(connection, ident))


def _limit(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 1_000:
        raise ValidationError("limit must be an integer from 1 to 1000")
    return value


def drift(
    store: ShadowStore, partition: str, operation: str, *, since_us: int | None = None
) -> DriftReport:
    """Per-version counts of the observations at or after ``since_us`` (all when ``None``);
    ``disagreements`` = prepared + disagreed; ``duplicates`` = the lifetime repeat counter."""

    partition, operation = _scope(partition, operation)
    floor = 0 if since_us is None else _bounded_int(since_us, "since_us")
    groups: dict[str, DriftGroup] = {}
    totals: dict[str, int] = dict.fromkeys(STATES, 0)
    with store.transaction() as connection:
        for row in connection.execute(
            """
            SELECT function_hash, state, MIN(sequence) AS first, COUNT(*) AS n
            FROM observations
            WHERE partition = ? AND operation = ? AND observed_at_us >= ?
            GROUP BY function_hash, state
            """,
            (partition, operation, floor),
        ):
            state = str(row["state"])
            if state not in STATES:
                raise IntegrityError("stored observation state is invalid")
            digest, first, count = str(row["function_hash"]), int(row["first"]), int(row["n"])
            group = groups.setdefault(
                digest,
                {
                    "function_hash": digest,
                    "first_sequence": first,
                    "counts": dict.fromkeys(STATES, 0),
                },
            )
            group["first_sequence"] = min(group["first_sequence"], first)
            group["counts"][state] = count
            totals[state] += count
        repeated = connection.execute(
            "SELECT count FROM duplicates WHERE partition = ? AND operation = ?",
            (partition, operation),
        ).fetchone()
    return {
        "partition": partition,
        "operation": operation,
        "since_us": since_us,
        "groups": sorted(groups.values(), key=lambda group: group["first_sequence"]),
        "totals": totals,
        "disagreements": totals["prepared"] + totals["disagreed"],
        "duplicates": 0 if repeated is None else int(repeated["count"]),
    }


def observations(
    store: ShadowStore,
    partition: str,
    operation: str,
    *,
    state: str | None = None,
    function_hash: str | None = None,
    after_sequence: int = 0,
    limit: int = 100,
) -> list[ObservationRecord]:
    """One page of observations in sequence order, every stored field included."""

    partition, operation = _scope(partition, operation)
    if state is not None and state not in STATES:
        raise ValidationError(f"state must be one of {', '.join(STATES)}")
    if function_hash is not None:
        function_hash = _digest(function_hash, "function_hash")
    after_sequence = _bounded_int(after_sequence, "after_sequence")
    limit = _limit(limit)
    with store.transaction() as connection:
        rows = connection.execute(
            """
            SELECT * FROM observations
            WHERE partition = ? AND operation = ? AND sequence > ?
              AND (? IS NULL OR state = ?) AND (? IS NULL OR function_hash = ?)
            ORDER BY sequence LIMIT ?
            """,
            (
                partition,
                operation,
                after_sequence,
                state,
                state,
                function_hash,
                function_hash,
                limit,
            ),
        ).fetchall()
        return [_record(row) for row in rows]


def pending(
    store: ShadowStore,
    *,
    state: Literal["admitted", "prepared"] = "admitted",
    after_sequence: int = 0,
    limit: int = 100,
) -> list[ObservationRecord]:
    """Observations awaiting a model answer (``admitted``) or a finish (``prepared``), oldest
    first, across every scope: a cursor for ONE batch consumer, never a lease."""

    if state not in ("admitted", "prepared"):
        raise ValidationError("state must be admitted or prepared")
    after_sequence = _bounded_int(after_sequence, "after_sequence")
    limit = _limit(limit)
    with store.transaction() as connection:
        rows = connection.execute(
            "SELECT * FROM observations WHERE state = ? AND sequence > ? ORDER BY sequence LIMIT ?",
            (state, after_sequence, limit),
        ).fetchall()
        return [_record(row) for row in rows]
