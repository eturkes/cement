#!/usr/bin/env python3
"""Drive the M3.2a read-capability corpus through ``Store.transaction``."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import gc
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time

from cement_runtime import CementError, IntegrityError, StateError
from cement_runtime.store import Store


PROBE_IDS = (
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "R7",
    "R8",
    "W1",
    "W2",
    "W3",
    "W4",
    "W5",
    "W6",
    "W7",
    "W8",
    "W9",
    "W10",
    "W11",
    "W12",
    "W13",
    "W14",
    "W15",
    "W16",
    "W17",
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
)


@dataclass(frozen=True)
class Result:
    outcome: str
    exc_type: str = ""
    message: str = ""
    notes: str = ""

    def as_json(self) -> dict[str, str]:
        return {
            "outcome": self.outcome,
            "exc_type": self.exc_type,
            "message": self.message,
            "notes": self.notes,
        }


def exception_type(exc: BaseException) -> str:
    cls = type(exc)
    return f"{cls.__module__}.{cls.__qualname__}"


def error_result(message: str, notes: str = "") -> Result:
    return Result("error", "builtins.AssertionError", message, notes)


def build_fixture(path: Path, marker: str) -> Store:
    store = Store(path)
    digest = hashlib.sha256(marker.encode("utf-8")).hexdigest()
    with store.transaction(write=True) as connection:
        connection.execute(
            """
            INSERT INTO operations(
                partition, name, revision, policy_json, policy_hash,
                created_at_us, updated_at_us
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("fixture", marker, 12, "{}", digest, 12, 13),
        )
        connection.execute(
            """
            INSERT INTO events(
                partition, kind, subject_type, subject_id, payload_json, created_at_us
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("fixture", "fixture-created", "operation", marker, "{}", 14),
        )
    return store


class Environment:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="cement-m3u2a-store-")
        self.root = Path(self._temporary.name)
        self.base = self.root / "base.sqlite"
        build_fixture(self.base, "base-marker")

    def copy(self, probe_id: str) -> Path:
        path = self.root / f"{probe_id}.sqlite"
        shutil.copy2(self.base, path)
        return path

    def close(self) -> None:
        self._temporary.cleanup()


def database_dump(path: Path) -> bytes:
    connection = sqlite3.connect(
        f"{path.absolute().as_uri()}?mode=ro",
        isolation_level=None,
        uri=True,
    )
    try:
        return ("\n".join(connection.iterdump()) + "\n").encode("utf-8")
    finally:
        connection.close()


def file_identity(path: Path) -> tuple[int, str]:
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest()


def run_read(action: Callable[[], str]) -> Result:
    try:
        notes = action()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "read probe raised")
    return Result("ok", notes=notes)


def is_read_only_denial(exc: BaseException) -> bool:
    return isinstance(exc, CementError) and not isinstance(
        exc, (StateError, IntegrityError)
    )


def run_denial(action: Callable[[], str]) -> Result:
    try:
        notes = action()
    except Exception as exc:
        if is_read_only_denial(exc):
            return Result("denied", exception_type(exc), str(exc), "write attempt raised")
        return Result(
            "error",
            exception_type(exc),
            str(exc),
            "write refusal used a raw, retryable, corrupt-ledger, or unrelated class",
        )
    return error_result("write unexpectedly succeeded", notes)


def probe_r1(environment: Environment) -> Result:
    path = environment.copy("R1")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            rows = connection.execute(
                "SELECT partition, name, revision FROM operations ORDER BY name"
            ).fetchall()
            actual = [tuple(row) for row in rows]
            expected = [("fixture", "base-marker", 12)]
            if actual != expected:
                raise AssertionError(f"rows={actual!r}; expected={expected!r}")
            return f"rows={actual!r}"

    return run_read(action)


def probe_r2(environment: Environment) -> Result:
    path = environment.copy("R2")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            value = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if value != 2:
                raise AssertionError(f"user_version={value}; expected=2")
            return f"user_version={value}"

    return run_read(action)


def probe_r3(environment: Environment) -> Result:
    path = environment.copy("R3")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            value = int(connection.execute("PRAGMA application_id").fetchone()[0])
            if value != 0:
                raise AssertionError(f"application_id={value}; expected=0")
            return f"application_id={value}"

    return run_read(action)


def probe_r4(environment: Environment) -> Result:
    path = environment.copy("R4")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            rows = connection.execute(
                "SELECT type, name FROM sqlite_schema ORDER BY type, name"
            ).fetchall()
            triggers = sum(str(row[0]) == "trigger" for row in rows)
            if not rows or triggers == 0:
                raise AssertionError("schema objects or triggers are missing")
            return f"schema_objects={len(rows)}; triggers={triggers}"

    return run_read(action)


def probe_r5(environment: Environment) -> Result:
    path = environment.copy("R5")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            integrity = [
                str(row[0])
                for row in connection.execute("PRAGMA integrity_check").fetchall()
            ]
            foreign_key_problem = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchone()
            metadata = connection.execute(
                "SELECT key, value FROM schema_metadata WHERE key = 'schema-v2'"
            ).fetchone()
            schema_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM sqlite_schema
                    WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL
                    """
                ).fetchone()[0]
            )
            if integrity != ["ok"]:
                raise AssertionError(f"integrity_check={integrity!r}")
            if foreign_key_problem is not None:
                raise AssertionError(f"foreign_key_check={tuple(foreign_key_problem)!r}")
            if metadata is None or len(str(metadata[1])) != 64:
                raise AssertionError(f"schema_metadata={metadata!r}")
            if schema_count == 0:
                raise AssertionError("runtime schema is empty")
            return (
                "validation SQL answered: integrity=ok; foreign_keys=ok; "
                f"metadata={metadata[0]!r}; schema_objects={schema_count}"
            )

    return run_read(action)


def probe_r6(environment: Environment) -> Result:
    path = environment.copy("R6")
    store = Store(path)
    expected = {
        "foreign_keys": 1,
        "busy_timeout": 10000,
        "synchronous": 3,
        "temp_store": 2,
        "trusted_schema": 0,
    }

    def action() -> str:
        with store.transaction(write=False) as connection:
            actual = {
                name: int(connection.execute(f"PRAGMA {name}").fetchone()[0])
                for name in expected
            }
            if actual != expected:
                raise AssertionError(f"setup={actual!r}; expected={expected!r}")
            return "; ".join(f"{name}={actual[name]}" for name in expected)

    return run_read(action)


def probe_r7(environment: Environment) -> Result:
    path = environment.copy("R7")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            if not hasattr(connection, "getconfig"):
                return "sqlite3.Connection.getconfig unavailable on this Python build"
            defensive = getattr(sqlite3, "SQLITE_DBCONFIG_DEFENSIVE", None)
            trusted = getattr(sqlite3, "SQLITE_DBCONFIG_TRUSTED_SCHEMA", None)
            if defensive is None or trusted is None:
                return "SQLite defensive configuration constants unavailable"
            actual = {
                "defensive": bool(connection.getconfig(defensive)),
                "trusted_schema": bool(connection.getconfig(trusted)),
            }
            expected = {"defensive": True, "trusted_schema": False}
            if actual != expected:
                raise AssertionError(f"setconfig={actual!r}; expected={expected!r}")
            return "SQLITE_DBCONFIG_DEFENSIVE=True; TRUSTED_SCHEMA=False"

    return run_read(action)


def probe_r8(environment: Environment) -> Result:
    path = environment.copy("R8")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            states = [connection.in_transaction]
            connection.execute("SELECT COUNT(*) FROM operations").fetchone()
            states.append(connection.in_transaction)
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
            states.append(connection.in_transaction)
            if states != [True, True, True]:
                raise AssertionError(f"in_transaction={states!r}")
            return f"in_transaction={states!r}"

    return run_read(action)


def probe_w1(environment: Environment) -> Result:
    path = environment.copy("W1")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute(
                """
                INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("fixture", "inserted", 13, "{}", "i" * 64, 15, 16),
            )
        return "INSERT completed"

    return run_denial(action)


def probe_w2(environment: Environment) -> Result:
    path = environment.copy("W2")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            cursor = connection.execute(
                "UPDATE operations SET updated_at_us = 22 WHERE name = 'base-marker'"
            )
            if cursor.rowcount != 1:
                raise AssertionError(f"rowcount={cursor.rowcount}; expected=1")
        return "UPDATE completed"

    return run_denial(action)


def probe_w3(environment: Environment) -> Result:
    path = environment.copy("W3")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            cursor = connection.execute(
                "DELETE FROM operations WHERE name = 'base-marker'"
            )
            if cursor.rowcount != 1:
                raise AssertionError(f"rowcount={cursor.rowcount}; expected=1")
        return "DELETE completed"

    return run_denial(action)


def probe_w4(environment: Environment) -> Result:
    path = environment.copy("W4")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("CREATE TABLE injected(value TEXT)")
        return "CREATE TABLE completed"

    return run_denial(action)


def probe_w5(environment: Environment) -> Result:
    path = environment.copy("W5")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            row = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'trigger' ORDER BY name LIMIT 1"
            ).fetchone()
            if row is None:
                raise AssertionError("fixture has no trigger")
            trigger = str(row[0])
            quoted = trigger.replace('"', '""')
            connection.execute(f'DROP TRIGGER "{quoted}"')
        return f"DROP TRIGGER completed; trigger={trigger}"

    return run_denial(action)


def probe_w6(environment: Environment) -> Result:
    path = environment.copy("W6")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute(
                "ALTER TABLE operations ADD COLUMN injected_value TEXT"
            )
        return "ALTER TABLE completed"

    return run_denial(action)


def probe_w7(environment: Environment) -> Result:
    path = environment.copy("W7")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("PRAGMA user_version = 3")
        return "PRAGMA user_version write completed"

    return run_denial(action)


def probe_w8(environment: Environment) -> Result:
    path = environment.copy("W8")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            row = connection.execute("PRAGMA journal_mode = WAL").fetchone()
        return f"PRAGMA journal_mode=WAL completed; result={None if row is None else row[0]!r}"

    return run_denial(action)


def probe_w9(environment: Environment) -> Result:
    path = environment.copy("W9")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("PRAGMA application_id = 123456")
        return "PRAGMA application_id write completed"

    return run_denial(action)


def probe_w10(environment: Environment) -> Result:
    path = environment.copy("W10")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("CREATE TEMP TABLE injected(value TEXT)")
        return "CREATE TEMP TABLE completed"

    return run_denial(action)


def probe_w11(environment: Environment) -> Result:
    path = environment.copy("W11")
    auxiliary = path.with_name("W11-attached.sqlite")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("ATTACH DATABASE ? AS aux", (str(auxiliary),))
            connection.execute("CREATE TABLE aux.injected(value TEXT)")
            connection.execute("INSERT INTO aux.injected VALUES ('written')")
        return f"ATTACH + write completed; auxiliary_exists={auxiliary.exists()}"

    return run_denial(action)


def probe_w12(environment: Environment) -> Result:
    path = environment.copy("W12")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.commit()
        return "explicit commit completed"

    return run_denial(action)


def probe_w13(environment: Environment) -> Result:
    path = environment.copy("W13")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("VACUUM")
        return "VACUUM completed"

    return run_denial(action)


def probe_w14(environment: Environment) -> Result:
    path = environment.copy("W14")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("SAVEPOINT nested")
            connection.execute(
                """
                INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("fixture", "savepoint-attempt", 15, "{}", "s" * 64, 19, 20),
            )
            connection.execute("RELEASE nested")
        return "SAVEPOINT + INSERT + RELEASE completed"

    return run_denial(action)


def probe_w15(environment: Environment) -> Result:
    path = environment.copy("W15")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            value = int(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        return f"PRAGMA foreign_keys=OFF completed; readback={value}"

    return run_denial(action)


def probe_w16(environment: Environment) -> Result:
    path = environment.copy("W16")
    store = Store(path)

    def action() -> str:
        with store.transaction(write=False) as connection:
            connection.execute("PRAGMA writable_schema = ON")
            cursor = connection.execute(
                "UPDATE sqlite_schema SET sql = sql WHERE name = 'operations'"
            )
        return f"writable_schema update completed; rowcount={cursor.rowcount}"

    return run_denial(action)


def probe_w17(environment: Environment) -> Result:
    path = environment.copy("W17")
    store = Store(path)
    failures: list[tuple[str, BaseException]] = []
    completed: list[str] = []
    for label, statement in (("REINDEX", "REINDEX"), ("ANALYZE", "ANALYZE")):
        try:
            with store.transaction(write=False) as connection:
                connection.execute(statement)
        except Exception as exc:
            failures.append((label, exc))
        else:
            completed.append(label)
    if len(failures) == 2:
        exc_type = "; ".join(
            f"{label}: {exception_type(exc)}" for label, exc in failures
        )
        message = "; ".join(f"{label}: {exc}" for label, exc in failures)
        if not all(is_read_only_denial(exc) for _, exc in failures):
            return Result(
                "error",
                exc_type,
                message,
                "REINDEX or ANALYZE used a forbidden denial class",
            )
        return Result(
            "denied",
            exc_type,
            message,
            "REINDEX and ANALYZE both denied through separate public contexts",
        )
    if not failures:
        return error_result("REINDEX and ANALYZE unexpectedly succeeded")
    return error_result(
        "REINDEX/ANALYZE denial was partial",
        f"completed={completed!r}; denied={[label for label, _ in failures]!r}",
    )


def probe_s1(environment: Environment) -> Result:
    path = environment.copy("S1")
    store = Store(path)
    before = database_dump(path)
    try:
        with store.transaction(write=False) as connection:
            connection.execute("SELECT COUNT(*) FROM operations").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "read transaction raised")
    after = database_dump(path)
    if before != after:
        return error_result(
            "iterdump changed",
            f"before_sha256={hashlib.sha256(before).hexdigest()}; "
            f"after_sha256={hashlib.sha256(after).hexdigest()}",
        )
    return Result(
        "ok",
        notes=f"bytes={len(before)}; sha256={hashlib.sha256(before).hexdigest()}",
    )


def probe_s2(environment: Environment) -> Result:
    path = environment.copy("S2")
    store = Store(path)
    before = file_identity(path)
    try:
        with store.transaction(write=False) as connection:
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "read transaction raised")
    after = file_identity(path)
    if before != after:
        return error_result(
            "ledger bytes changed",
            f"before={before!r}; after={after!r}",
        )
    return Result("ok", notes=f"size={before[0]}; sha256={before[1]}; identical=True")


def probe_s3(environment: Environment) -> Result:
    path = environment.copy("S3")
    store = Store(path)
    path.unlink()
    try:
        with store.transaction(write=False):
            pass
    except Exception as exc:
        absent = not path.exists()
        return Result(
            "denied" if absent else "error",
            exception_type(exc),
            str(exc),
            f"path_absent_after={absent}",
        )
    return error_result(
        "missing ledger unexpectedly opened",
        f"path_absent_after={not path.exists()}",
    )


def fixture_marker(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT name FROM operations WHERE partition = 'fixture'"
    ).fetchone()
    if row is None:
        raise AssertionError("fixture marker is missing")
    return str(row[0])


def raw_uri_marker(path: Path) -> str:
    connection = sqlite3.connect(
        f"file:{path}?mode=ro",
        isolation_level=None,
        uri=True,
    )
    try:
        return fixture_marker(connection)
    finally:
        connection.close()


def probe_s4(environment: Environment) -> Result:
    del environment
    temporary = tempfile.TemporaryDirectory(prefix="cement-m3u2a-uri-")
    root = Path(temporary.name)
    hazards = {
        "question": ("target?query.sqlite", "target"),
        "fragment": ("target#fragment.sqlite", "target"),
        "percent": ("target%25.sqlite", "target%.sqlite"),
        "space": ("space target.sqlite", "space%20target.sqlite"),
        "newline": ("newline\ntarget.sqlite", "newline%0Atarget.sqlite"),
        "non_ascii": ("café.sqlite", "caf%C3%A9.sqlite"),
    }
    details: list[str] = []
    try:
        for name, (target_name, decoy_name) in hazards.items():
            directory = root / name
            directory.mkdir()
            target = directory / target_name
            decoy = directory / decoy_name
            expected = f"intended-{name}"
            decoy_marker = f"decoy-{name}"
            build_fixture(target, expected)
            build_fixture(decoy, decoy_marker)

            store = Store(target)
            with store.transaction(write=False) as connection:
                actual = fixture_marker(connection)
            try:
                raw_actual = raw_uri_marker(target)
            except Exception as exc:
                raw_note = f"{exception_type(exc)}: {exc}"
            else:
                raw_note = repr(raw_actual)
            details.append(
                f"{name}: expected={expected!r}; active={actual!r}; "
                f"planted_decoy={decoy_marker!r}; raw={raw_note}"
            )
            if actual != expected:
                return error_result(
                    f"hazard {name} opened the wrong ledger",
                    " | ".join(details),
                )
        return Result("ok", notes=" | ".join(details))
    finally:
        temporary.cleanup()


def probe_s5(environment: Environment) -> Result:
    path = environment.copy("S5")
    reader = Store(path)
    writer = Store(path)
    inserted = threading.Event()
    writer_errors: list[BaseException] = []
    writer_duration_ms: list[float] = []

    def write() -> None:
        started = time.perf_counter_ns()
        try:
            with writer.transaction(write=True) as connection:
                connection.execute(
                    """
                    INSERT INTO events(
                        partition, kind, subject_type, subject_id,
                        payload_json, created_at_us
                    ) VALUES ('fixture', 'concurrent', 'operation', 'writer', '{}', 21)
                    """
                )
                inserted.set()
        except BaseException as exc:
            writer_errors.append(exc)
            inserted.set()
        finally:
            writer_duration_ms.append(
                (time.perf_counter_ns() - started) / 1_000_000
            )

    thread = threading.Thread(target=write, name="m3u2a-store-writer")
    before = -1
    inside_after_writer = -1
    blocked_at_sample = False
    read_error: BaseException | None = None
    try:
        with reader.transaction(write=False) as connection:
            before = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            thread.start()
            if not inserted.wait(timeout=3.0):
                raise TimeoutError("writer did not reach its commit attempt within 3 seconds")
            time.sleep(0.15)
            blocked_at_sample = thread.is_alive()
            inside_after_writer = int(
                connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            )
    except BaseException as exc:
        read_error = exc
    finally:
        if thread.ident is not None:
            thread.join(timeout=12.0)

    if read_error is not None:
        return Result("error", exception_type(read_error), str(read_error), "reader raised")
    if thread.is_alive():
        return error_result("writer remained blocked after reader rollback")
    if writer_errors:
        exc = writer_errors[0]
        return Result("error", exception_type(exc), str(exc), "writer raised")
    with reader.transaction(write=False) as connection:
        after = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
    if inside_after_writer != before or after != before + 1:
        return error_result(
            "snapshot or post-rollback visibility mismatch",
            f"before={before}; inside_after_writer={inside_after_writer}; after={after}",
        )
    return Result(
        "ok",
        notes=(
            f"before={before}; inside_after_writer={inside_after_writer}; after={after}; "
            f"writer_blocked_at_150ms={blocked_at_sample}; "
            f"writer_duration_ms={writer_duration_ms[0]:.3f}"
        ),
    )


def probe_s6(environment: Environment) -> Result:
    path = environment.copy("S6")
    store = Store(path)
    before = file_identity(path)
    rollback_trace: list[str] = []
    try:
        with store.transaction(write=False) as connection:
            connection.set_trace_callback(rollback_trace.append)
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "rollback arm raised")
    after = file_identity(path)
    rollback_seen = any(
        statement.strip().upper() == "ROLLBACK" for statement in rollback_trace
    )
    commit_seen = any(
        statement.strip().upper() == "COMMIT" for statement in rollback_trace
    )
    if before != after or not rollback_seen or commit_seen:
        return error_result(
            "owner rollback contract failed",
            f"before={before!r}; after={after!r}; trace={rollback_trace!r}",
        )

    commit_path = environment.copy("S6-commit")
    commit_store = Store(commit_path)
    states: list[bool] = []
    commit_error: BaseException | None = None
    commit_trace: list[str] = []
    try:
        with commit_store.transaction(write=False) as connection:
            connection.set_trace_callback(commit_trace.append)
            states.append(connection.in_transaction)
            try:
                connection.commit()
            except BaseException as exc:
                commit_error = exc
            states.append(connection.in_transaction)
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "commit arm context raised")
    if commit_error is None:
        return error_result(
            "explicit commit unexpectedly succeeded",
            f"states={states!r}; trace={commit_trace!r}",
        )
    if states != [True, True]:
        return error_result(
            "denied commit ended the snapshot",
            f"states={states!r}; trace={commit_trace!r}",
        )
    return Result(
        "ok",
        exception_type(commit_error),
        str(commit_error),
        (
            f"rollback_bytes_identical=True; rollback_trace={rollback_trace!r}; "
            f"commit_states={states!r}; commit_trace={commit_trace!r}"
        ),
    )


def configure_baseline(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA synchronous = EXTRA")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA trusted_schema = OFF")
    if hasattr(connection, "setconfig"):
        defensive = getattr(sqlite3, "SQLITE_DBCONFIG_DEFENSIVE", None)
        trusted = getattr(sqlite3, "SQLITE_DBCONFIG_TRUSTED_SCHEMA", None)
        if defensive is not None:
            connection.setconfig(defensive, True)
        if trusted is not None:
            connection.setconfig(trusted, False)


def probe_s7(environment: Environment) -> Result:
    path = environment.copy("S7")
    store = Store(path)

    def baseline_open() -> None:
        connection = sqlite3.connect(path, timeout=10.0, isolation_level=None)
        try:
            configure_baseline(connection)
            connection.execute("BEGIN")
            connection.commit()
        finally:
            connection.close()

    def enforced_open() -> None:
        with store.transaction(write=False):
            pass

    try:
        for _ in range(20):
            baseline_open()
            enforced_open()
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            baseline_ns = 0
            enforced_ns = 0
            baseline_rounds: list[float] = []
            enforced_rounds: list[float] = []
            for round_index in range(5):
                round_baseline_ns = 0
                round_enforced_ns = 0
                for pair_index in range(200):
                    calls = (
                        ((baseline_open, "baseline"), (enforced_open, "enforced"))
                        if (round_index + pair_index) % 2 == 0
                        else ((enforced_open, "enforced"), (baseline_open, "baseline"))
                    )
                    for call, label in calls:
                        started = time.perf_counter_ns()
                        call()
                        elapsed = time.perf_counter_ns() - started
                        if label == "baseline":
                            round_baseline_ns += elapsed
                        else:
                            round_enforced_ns += elapsed
                baseline_ns += round_baseline_ns
                enforced_ns += round_enforced_ns
                baseline_rounds.append(round_baseline_ns / 200_000)
                enforced_rounds.append(round_enforced_ns / 200_000)
        finally:
            if gc_was_enabled:
                gc.enable()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "interleaved benchmark raised")

    baseline_us = baseline_ns / 1_000_000
    enforced_us = enforced_ns / 1_000_000
    ratio = enforced_us / baseline_us
    return Result(
        "ok",
        notes=(
            "method=1000 opens per arm, interleaved in one loop as 5x200 pairs, "
            "alternating first arm, after 20 warmup pairs; "
            f"baseline={baseline_us:.3f} us/open "
            f"(rounds={min(baseline_rounds):.3f}..{max(baseline_rounds):.3f}); "
            f"enforced={enforced_us:.3f} us/open "
            f"(rounds={min(enforced_rounds):.3f}..{max(enforced_rounds):.3f}); "
            f"delta={enforced_us - baseline_us:+.3f} us/open; ratio={ratio:.3f}x"
        ),
    )


# All probe functions are implemented.


PROBES: dict[str, Callable[[Environment], Result] | None] = {
    "R1": probe_r1,
    "R2": probe_r2,
    "R3": probe_r3,
    "R4": probe_r4,
    "R5": probe_r5,
    "R6": probe_r6,
    "R7": probe_r7,
    "R8": probe_r8,
    "W1": probe_w1,
    "W2": probe_w2,
    "W3": probe_w3,
    "W4": probe_w4,
    "W5": probe_w5,
    "W6": probe_w6,
    "W7": probe_w7,
    "W8": probe_w8,
    "W9": probe_w9,
    "W10": probe_w10,
    "W11": probe_w11,
    "W12": probe_w12,
    "W13": probe_w13,
    "W14": probe_w14,
    "W15": probe_w15,
    "W16": probe_w16,
    "W17": probe_w17,
    "S1": probe_s1,
    "S2": probe_s2,
    "S3": probe_s3,
    "S4": probe_s4,
    "S5": probe_s5,
    "S6": probe_s6,
    "S7": probe_s7,
}


def write_results(path: Path, results: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"probes": results}, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def run(output: Path) -> int:
    results: dict[str, dict[str, str]] = {}
    environment = Environment()
    try:
        for probe_id in PROBE_IDS:
            probe = PROBES[probe_id]
            if probe is None:
                raise RuntimeError(f"probe {probe_id} is not implemented")
            try:
                result = probe(environment)
            except Exception as exc:
                result = Result(
                    "error",
                    exception_type(exc),
                    str(exc),
                    "uncaught probe failure",
                )
            results[probe_id] = result.as_json()
            write_results(output, results)
    finally:
        environment.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.json)
    except Exception as exc:
        print(f"probe harness failed: {exception_type(exc)}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
