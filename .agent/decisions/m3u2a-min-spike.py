#!/usr/bin/env python3
"""Measure incremental enforcement sets for the M3.2a ALT-MIN spike."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time
from typing import Any

from cement_runtime import store as store_module
from cement_runtime.store import Store


PROBE_IDS = (
    "R1_select_user_table",
    "R2_pragma_user_version_read",
    "R3_pragma_application_id_read",
    "R4_select_sqlite_schema",
    "R5_validate_ledger_call",
    "R6_connect_setup_pragmas",
    "R7_setconfig_defensive",
    "R8_two_reads_one_snapshot",
    "W1_insert",
    "W2_update",
    "W3_delete",
    "W4_create_table",
    "W5_drop_trigger",
    "W6_alter_table",
    "W7_pragma_user_version_write",
    "W8_pragma_journal_mode_wal",
    "W9_pragma_application_id_write",
    "W10_create_temp_table",
    "W11_attach_and_write",
    "W12_explicit_commit",
    "W13_vacuum",
    "W14_savepoint_insert",
    "W15_pragma_foreign_keys_off",
    "W16_writable_schema_update",
    "W17_reindex_analyze",
    "S1_iterdump_identical",
    "S2_file_bytes_identical",
    "S3_missing_file_refused",
    "S4_uri_hazard_paths",
    "S5_concurrent_writer_visibility",
    "S6_rollback_vs_commit",
    "S7_setup_cost_1000_opens",
)

EXPECTED = {
    **{name: "ok" for name in PROBE_IDS[:8]},
    **{name: "denied" for name in PROBE_IDS[8:25]},
    "S1_iterdump_identical": "ok",
    "S2_file_bytes_identical": "ok",
    "S3_missing_file_refused": "denied",
    "S4_uri_hazard_paths": "ok",
    "S5_concurrent_writer_visibility": "ok",
    "S6_rollback_vs_commit": "ok",
    "S7_setup_cost_1000_opens": "ok",
}


@dataclass(frozen=True)
class Configuration:
    stage: str
    mechanisms: tuple[str, ...]
    authorizer: bool
    readonly_uri: bool
    transaction: bool = True


STAGES = {
    "transaction": Configuration(
        stage="transaction",
        mechanisms=("one explicit transaction with owner rollback",),
        authorizer=False,
        readonly_uri=False,
    ),
    "authorizer": Configuration(
        stage="authorizer",
        mechanisms=(
            "one explicit transaction with owner rollback",
            "read-allowlisted SQLite authorizer",
        ),
        authorizer=True,
        readonly_uri=False,
    ),
    "readonly": Configuration(
        stage="readonly",
        mechanisms=(
            "one explicit transaction with owner rollback",
            "read-allowlisted SQLite authorizer",
            "percent-encoded existing-only file URI with mode=ro",
        ),
        authorizer=True,
        readonly_uri=True,
    ),
    "control-no-authorizer": Configuration(
        stage="control-no-authorizer",
        mechanisms=(
            "one explicit transaction with owner rollback",
            "percent-encoded existing-only file URI with mode=ro",
        ),
        authorizer=False,
        readonly_uri=True,
    ),
    "control-no-transaction": Configuration(
        stage="control-no-transaction",
        mechanisms=(
            "read-allowlisted SQLite authorizer",
            "percent-encoded existing-only file URI with mode=ro",
        ),
        authorizer=True,
        readonly_uri=True,
        transaction=False,
    ),
}


@dataclass(frozen=True)
class Result:
    outcome: str
    exc_type: str = ""
    message: str = ""
    notes: str = ""

    def as_probe(self, probe_id: str) -> dict[str, str]:
        return {
            "id": probe_id,
            "expected": EXPECTED[probe_id],
            "outcome": self.outcome,
            "exc_type": self.exc_type,
            "message": self.message,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class Environment:
    root: Path
    base: Path
    configuration: Configuration

    def copy(self, probe_id: str) -> Path:
        target = self.root / f"{probe_id}.sqlite"
        shutil.copy2(self.base, target)
        return target


def exception_type(exc: BaseException) -> str:
    return f"{type(exc).__module__}.{type(exc).__qualname__}"


def unknown_probe(probe_id: str) -> dict[str, str]:
    return {
        "id": probe_id,
        "expected": EXPECTED[probe_id],
        "outcome": "unknown",
        "exc_type": "",
        "message": "",
        "notes": "",
    }


def matrix(configuration: Configuration) -> dict[str, Any]:
    return {
        "alternative": (
            "ALT-MIN incremental set; final candidate omits PRAGMA query_only"
        ),
        "mechanisms": list(configuration.mechanisms),
        "sqlite_version": sqlite3.sqlite_version,
        "python_version": ".".join(str(part) for part in os.sys.version_info[:3]),
        "probes": {probe_id: unknown_probe(probe_id) for probe_id in PROBE_IDS},
    }


def write_matrix(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def build_fixture(path: Path, marker: str) -> Store:
    store = Store(path)
    policy_json = json.dumps({"minimum_support": 12}, separators=(",", ":"))
    policy_hash = hashlib.sha256(policy_json.encode()).hexdigest()
    with store.transaction(write=True) as connection:
        connection.execute(
            """
            INSERT INTO operations(
                partition, name, revision, policy_json, policy_hash,
                created_at_us, updated_at_us
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("fixture", marker, 12, policy_json, policy_hash, 12, 13),
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


def encoded_readonly_uri(path: Path) -> str:
    return f"{path.absolute().as_uri()}?mode=ro"


def setup_connection(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    pragmas = (
        ("foreign_keys=ON", "PRAGMA foreign_keys = ON", "PRAGMA foreign_keys"),
        ("busy_timeout=10000", "PRAGMA busy_timeout = 10000", "PRAGMA busy_timeout"),
        ("synchronous=EXTRA", "PRAGMA synchronous = EXTRA", "PRAGMA synchronous"),
        ("temp_store=MEMORY", "PRAGMA temp_store = MEMORY", "PRAGMA temp_store"),
        ("trusted_schema=OFF", "PRAGMA trusted_schema = OFF", "PRAGMA trusted_schema"),
    )
    results: dict[str, Any] = {}
    for name, statement, readback in pragmas:
        connection.execute(statement)
        results[name] = connection.execute(readback).fetchone()[0]

    setconfig: dict[str, Any] = {"available": hasattr(connection, "setconfig")}
    if setconfig["available"]:
        defensive = getattr(sqlite3, "SQLITE_DBCONFIG_DEFENSIVE", None)
        trusted = getattr(sqlite3, "SQLITE_DBCONFIG_TRUSTED_SCHEMA", None)
        setconfig["defensive_constant"] = defensive is not None
        setconfig["trusted_schema_constant"] = trusted is not None
        if defensive is not None:
            connection.setconfig(defensive, True)
            setconfig["defensive"] = connection.getconfig(defensive)
        if trusted is not None:
            connection.setconfig(trusted, False)
            setconfig["trusted_schema"] = connection.getconfig(trusted)
    results["setconfig"] = setconfig
    return results


_READ_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}


def read_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    database: str | None,
    trigger: str | None,
) -> int:
    del database, trigger
    if action in _READ_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and arg2 is None:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_TRANSACTION and (arg1 or "").upper() in {
        "BEGIN",
        "ROLLBACK",
    }:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_SAVEPOINT:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def open_connection(
    path: Path, configuration: Configuration
) -> tuple[sqlite3.Connection, dict[str, Any]]:
    if configuration.readonly_uri:
        connection = sqlite3.connect(
            encoded_readonly_uri(path),
            timeout=10.0,
            isolation_level=None,
            uri=True,
        )
    else:
        connection = sqlite3.connect(
            path,
            timeout=10.0,
            isolation_level=None,
        )
    try:
        setup = setup_connection(connection)
        if configuration.authorizer:
            connection.set_authorizer(read_authorizer)
    except Exception:
        connection.close()
        raise
    return connection, setup


@contextmanager
def read_transaction(
    path: Path, configuration: Configuration
) -> Iterator[tuple[sqlite3.Connection, dict[str, Any]]]:
    connection, setup = open_connection(path, configuration)
    try:
        if configuration.transaction:
            connection.execute("BEGIN")
        try:
            yield connection, setup
        finally:
            if connection.in_transaction:
                connection.rollback()
    finally:
        connection.close()


def read_probe(action: Callable[[], str]) -> Result:
    try:
        notes = action()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "read path raised")
    return Result("ok", notes=notes)


def write_probe(action: Callable[[], str]) -> Result:
    try:
        notes = action()
    except sqlite3.Error as exc:
        return Result("denied", exception_type(exc), str(exc), "write statement raised")
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "probe defect or non-SQL failure")
    return Result("ok", notes=notes)


def r1(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            rows = connection.execute(
                "SELECT partition, name, revision FROM operations ORDER BY name"
            ).fetchall()
            if len(rows) != 1 or tuple(rows[0]) != ("fixture", "base-marker", 12):
                raise RuntimeError(f"unexpected rows: {[tuple(row) for row in rows]!r}")
            return f"rows={[tuple(row) for row in rows]!r}"

    return read_probe(action)


def r2(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            value = connection.execute("PRAGMA user_version").fetchone()[0]
            if value != 2:
                raise RuntimeError(f"user_version={value!r}")
            return f"user_version={value}"

    return read_probe(action)


def r3(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            value = connection.execute("PRAGMA application_id").fetchone()[0]
            return f"application_id={value}"

    return read_probe(action)


def r4(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            rows = connection.execute(
                "SELECT type, name FROM sqlite_schema ORDER BY type, name"
            ).fetchall()
            if not rows or not any(row[0] == "trigger" for row in rows):
                raise RuntimeError("schema objects or triggers missing")
            return f"schema_objects={len(rows)}; triggers={sum(row[0] == 'trigger' for row in rows)}"

    return read_probe(action)


def r5(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            store_module._validate_ledger(connection)
            return "_validate_ledger returned"

    return read_probe(action)


def r6(path: Path, configuration: Configuration) -> Result:
    expected = {
        "foreign_keys=ON": 1,
        "busy_timeout=10000": 10000,
        "synchronous=EXTRA": 3,
        "temp_store=MEMORY": 2,
        "trusted_schema=OFF": 0,
    }

    def action() -> str:
        with read_transaction(path, configuration) as (_, setup):
            actual = {name: setup[name] for name in expected}
            if actual != expected:
                raise RuntimeError(f"setup readback={actual!r}; expected={expected!r}")
            return "; ".join(f"{name} -> {actual[name]}" for name in expected)

    return read_probe(action)


def r7(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (_, setup):
            values = setup["setconfig"]
            if not values["available"]:
                return "connection.setconfig absent on this build"
            expected = {
                "defensive_constant": True,
                "trusted_schema_constant": True,
                "defensive": True,
                "trusted_schema": False,
            }
            actual = {name: values.get(name) for name in expected}
            if actual != expected:
                raise RuntimeError(f"setconfig state={actual!r}; expected={expected!r}")
            return "setconfig present; DEFENSIVE=True; TRUSTED_SCHEMA=False"

    return read_probe(action)


def r8(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            states = [connection.in_transaction]
            connection.execute("SELECT COUNT(*) FROM operations").fetchone()
            states.append(connection.in_transaction)
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
            states.append(connection.in_transaction)
            if states != [True, True, True]:
                raise RuntimeError(f"in_transaction states={states!r}")
            return f"in_transaction states={states!r}"

    return read_probe(action)


def w1(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute(
                """
                INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("fixture", "inserted", 13, "{}", "i" * 64, 15, 16),
            )
            return "INSERT completed"

    return write_probe(action)


def w2(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            cursor = connection.execute(
                "UPDATE operations SET updated_at_us = 22 WHERE name = 'base-marker'"
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"rowcount={cursor.rowcount}")
            return "UPDATE completed; rowcount=1"

    return write_probe(action)


def w3(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            cursor = connection.execute(
                "DELETE FROM operations WHERE name = 'base-marker'"
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"rowcount={cursor.rowcount}")
            return "DELETE completed; rowcount=1"

    return write_probe(action)


def w4(path: Path, configuration: Configuration) -> Result:
    return write_probe(
        lambda: _execute_in_read(path, configuration, "CREATE TABLE injected(value TEXT)")
    )


def w5(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            row = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'trigger' ORDER BY name LIMIT 1"
            ).fetchone()
            if row is None:
                raise RuntimeError("fixture has no trigger")
            trigger = str(row[0])
            quoted = trigger.replace('"', '""')
            connection.execute(f'DROP TRIGGER "{quoted}"')
            return f"DROP TRIGGER completed; trigger={trigger}"

    return write_probe(action)


def w6(path: Path, configuration: Configuration) -> Result:
    return write_probe(
        lambda: _execute_in_read(
            path,
            configuration,
            "ALTER TABLE operations ADD COLUMN spike_added TEXT",
        )
    )


def w7(path: Path, configuration: Configuration) -> Result:
    return write_probe(
        lambda: _execute_in_read(path, configuration, "PRAGMA user_version = 3")
    )


def w8(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            row = connection.execute("PRAGMA journal_mode = WAL").fetchone()
            return f"PRAGMA journal_mode=WAL completed; result={None if row is None else row[0]!r}"

    return write_probe(action)


def w9(path: Path, configuration: Configuration) -> Result:
    return write_probe(
        lambda: _execute_in_read(path, configuration, "PRAGMA application_id = 123456")
    )


def w10(path: Path, configuration: Configuration) -> Result:
    return write_probe(
        lambda: _execute_in_read(
            path, configuration, "CREATE TEMP TABLE temp_injected(value TEXT)"
        )
    )


def w11(path: Path, configuration: Configuration) -> Result:
    auxiliary = path.with_name(f"{path.stem}-attached.sqlite")

    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("ATTACH DATABASE ? AS aux", (str(auxiliary),))
            connection.execute("CREATE TABLE aux.injected(value TEXT)")
            connection.execute("INSERT INTO aux.injected VALUES ('written')")
            return f"ATTACH + CREATE + INSERT completed; auxiliary_exists={auxiliary.exists()}"

    return write_probe(action)


def w12(path: Path, configuration: Configuration) -> Result:
    failures: list[tuple[str, BaseException]] = []
    with read_transaction(path, configuration) as (connection, _):
        try:
            connection.execute(
                """
                INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("fixture", "commit-attempt", 14, "{}", "c" * 64, 17, 18),
            )
        except sqlite3.Error as exc:
            failures.append(("INSERT", exc))
        try:
            connection.commit()
        except sqlite3.Error as exc:
            failures.append(("COMMIT", exc))
    if not failures:
        return Result("ok", notes="INSERT completed; explicit commit completed")
    labels = "; ".join(f"{label}: {str(exc)}" for label, exc in failures)
    types = "; ".join(
        f"{label}: {exception_type(exc)}" for label, exc in failures
    )
    return Result(
        "denied",
        types,
        labels,
        f"denied steps={','.join(label for label, _ in failures)}",
    )


def w13(path: Path, configuration: Configuration) -> Result:
    return write_probe(lambda: _execute_in_read(path, configuration, "VACUUM"))


def w14(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("SAVEPOINT nested")
            connection.execute(
                """
                INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("fixture", "savepoint-attempt", 15, "{}", "s" * 64, 19, 20),
            )
            connection.execute("RELEASE nested")
            return "SAVEPOINT + INSERT + RELEASE completed"

    return write_probe(action)


def w15(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("PRAGMA foreign_keys = OFF")
            readback = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            return f"PRAGMA foreign_keys=OFF completed; readback={readback}"

    return write_probe(action)


def w16(path: Path, configuration: Configuration) -> Result:
    def action() -> str:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("PRAGMA writable_schema = ON")
            cursor = connection.execute(
                "UPDATE sqlite_schema SET sql = sql WHERE name = 'operations'"
            )
            return f"writable_schema enabled; sqlite_schema UPDATE rowcount={cursor.rowcount}"

    return write_probe(action)


def w17(path: Path, configuration: Configuration) -> Result:
    failures: list[tuple[str, BaseException]] = []
    completed: list[str] = []
    with read_transaction(path, configuration) as (connection, _):
        for label, statement in (("REINDEX", "REINDEX"), ("ANALYZE", "ANALYZE")):
            try:
                connection.execute(statement)
            except sqlite3.Error as exc:
                failures.append((label, exc))
            else:
                completed.append(label)
    if len(failures) == 2:
        return Result(
            "denied",
            "; ".join(
                f"{label}: {exception_type(exc)}" for label, exc in failures
            ),
            "; ".join(f"{label}: {str(exc)}" for label, exc in failures),
            "REINDEX and ANALYZE both denied",
        )
    if not failures:
        return Result("ok", notes="REINDEX and ANALYZE both completed")
    return Result(
        "error",
        "; ".join(f"{label}: {exception_type(exc)}" for label, exc in failures),
        "; ".join(f"{label}: {str(exc)}" for label, exc in failures),
        f"partial denial; completed={completed!r}",
    )


def _execute_in_read(
    path: Path, configuration: Configuration, statement: str
) -> str:
    with read_transaction(path, configuration) as (connection, _):
        connection.execute(statement)
        return f"completed: {statement}"


def database_dump(path: Path) -> bytes:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        return ("\n".join(connection.iterdump()) + "\n").encode()
    finally:
        connection.close()


def file_identity(path: Path) -> tuple[int, str]:
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest()


def s1(path: Path, configuration: Configuration) -> Result:
    before = database_dump(path)
    try:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("SELECT COUNT(*) FROM operations").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "read transaction raised")
    after = database_dump(path)
    if before != after:
        return Result("error", "builtins.AssertionError", "iterdump changed", "before != after")
    return Result(
        "ok",
        notes=f"iterdump bytes={len(before)}; sha256={hashlib.sha256(before).hexdigest()}",
    )


def s2(path: Path, configuration: Configuration) -> Result:
    before = file_identity(path)
    try:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "read transaction raised")
    after = file_identity(path)
    if before != after:
        return Result(
            "error",
            "builtins.AssertionError",
            f"file identity changed: before={before!r}; after={after!r}",
            "ledger bytes changed",
        )
    return Result("ok", notes=f"size={before[0]}; sha256={before[1]}; identical=True")


def s3(path: Path, configuration: Configuration) -> Result:
    path.unlink(missing_ok=True)
    try:
        with read_transaction(path, configuration):
            pass
    except sqlite3.Error as exc:
        absent = not path.exists()
        outcome = "denied" if absent else "error"
        return Result(
            outcome,
            exception_type(exc),
            str(exc),
            f"path_absent_after={absent}",
        )
    except Exception as exc:
        return Result(
            "error",
            exception_type(exc),
            str(exc),
            f"path_absent_after={not path.exists()}",
        )
    return Result(
        "ok",
        notes=f"open succeeded; path_created={path.exists()}",
    )


def marker_from_connection(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT name FROM operations WHERE partition = 'fixture'"
    ).fetchone()
    if row is None:
        raise RuntimeError("marker row missing")
    return str(row[0])


def raw_uri_marker(path: Path) -> tuple[str, str]:
    uri = f"file:{path}?mode=ro"
    try:
        connection = sqlite3.connect(uri, isolation_level=None, uri=True)
    except Exception as exc:
        return "error", f"{exception_type(exc)}: {exc}"
    try:
        return "opened", marker_from_connection(connection)
    except Exception as exc:
        return "error", f"{exception_type(exc)}: {exc}"
    finally:
        connection.close()


def s4(path: Path, configuration: Configuration) -> Result:
    del path
    root = Path(tempfile.mkdtemp(prefix="cement-m3u2a-uri-"))
    try:
        hazards = {
            "question": root / "question-target?query.sqlite",
            "fragment": root / "fragment-target#fragment.sqlite",
            "percent": root / "percent%25.sqlite",
            "space": root / "space target.sqlite",
            "newline": root / "newline\ntarget.sqlite",
            "non_ascii": root / "café.sqlite",
        }
        expected = {name: f"marker-{name}" for name in hazards}
        for name, target in hazards.items():
            build_fixture(target, expected[name])

        decoys = {
            "question": root / "question-target",
            "fragment": root / "fragment-target",
            "percent": root / "percent%.sqlite",
        }
        for name, target in decoys.items():
            build_fixture(target, f"raw-decoy-{name}")

        active_details: list[str] = []
        wrong = False
        for name, target in hazards.items():
            try:
                with read_transaction(target, configuration) as (connection, _):
                    actual = marker_from_connection(connection)
            except Exception as exc:
                return Result(
                    "error",
                    exception_type(exc),
                    str(exc),
                    f"active path={name}; details={' | '.join(active_details)}",
                )
            matches = actual == expected[name]
            wrong |= not matches
            active_details.append(
                f"{name}: expected={expected[name]!r}, actual={actual!r}, ok={matches}"
            )

        raw_details: list[str] = []
        if configuration.readonly_uri:
            for name, target in hazards.items():
                status, detail = raw_uri_marker(target)
                raw_details.append(f"{name}: {status} -> {detail!r}")
        else:
            raw_details.append("not applicable: active mechanism uses a non-URI path")

        notes = (
            "active=" + " | ".join(active_details) + "; raw_uri=" + " | ".join(raw_details)
        )
        if wrong:
            return Result(
                "wrong_target",
                "builtins.AssertionError",
                "at least one hazardous path opened the wrong ledger",
                notes,
            )
        return Result("ok", notes=notes)
    finally:
        shutil.rmtree(root)


def s5(path: Path, configuration: Configuration) -> Result:
    writer_store = Store(path)
    inserted = threading.Event()
    writer_errors: list[BaseException] = []
    writer_duration_ms: list[float] = []

    def writer() -> None:
        started = time.perf_counter_ns()
        try:
            with writer_store.transaction(write=True) as connection:
                connection.execute(
                    """
                    INSERT INTO events(
                        partition, kind, subject_type, subject_id, payload_json, created_at_us
                    ) VALUES ('fixture', 'concurrent', 'operation', 'writer', '{}', 21)
                    """
                )
                inserted.set()
        except BaseException as exc:
            writer_errors.append(exc)
            inserted.set()
        finally:
            writer_duration_ms.append((time.perf_counter_ns() - started) / 1_000_000)

    thread = threading.Thread(target=writer, name="m3u2a-writer")
    before = second = -1
    blocked_at_sample = False
    try:
        with read_transaction(path, configuration) as (connection, _):
            before = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            thread.start()
            if not inserted.wait(timeout=3.0):
                return Result(
                    "error",
                    "builtins.TimeoutError",
                    "writer did not reach its commit attempt within 3 seconds",
                    "reader transaction remained open",
                )
            time.sleep(0.15)
            blocked_at_sample = thread.is_alive()
            second = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "reader path raised")
    finally:
        if thread.ident is not None:
            thread.join(timeout=12.0)

    if thread.is_alive():
        return Result(
            "error",
            "builtins.TimeoutError",
            "writer remained blocked after reader rollback",
            "join timeout=12 seconds",
        )
    if writer_errors:
        exc = writer_errors[0]
        return Result(
            "error",
            exception_type(exc),
            str(exc),
            f"writer duration_ms={writer_duration_ms[0]:.3f}",
        )
    after_connection = sqlite3.connect(path, isolation_level=None)
    try:
        after = after_connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        after_connection.close()
    if second != before or after != before + 1:
        return Result(
            "error",
            "builtins.AssertionError",
            f"counts before={before}, inside_after_writer={second}, after={after}",
            "snapshot or writer visibility mismatch",
        )
    return Result(
        "ok",
        notes=(
            f"counts before={before}, inside_after_writer={second}, after={after}; "
            f"writer_blocked_at_150ms={blocked_at_sample}; "
            f"writer_duration_ms={writer_duration_ms[0]:.3f}; journal_mode=DELETE"
        ),
    )


def s6(path: Path, configuration: Configuration, base: Path) -> Result:
    before = file_identity(path)
    try:
        with read_transaction(path, configuration) as (connection, _):
            connection.execute("SELECT COUNT(*) FROM events").fetchone()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "rollback path raised")
    after = file_identity(path)
    if before != after:
        return Result(
            "error",
            "builtins.AssertionError",
            f"rollback changed bytes: before={before!r}; after={after!r}",
            "rollback byte comparison failed",
        )

    commit_path = path.with_name("S6_commit.sqlite")
    shutil.copy2(base, commit_path)
    commit_error: BaseException | None = None
    split = False
    states: list[bool] = []
    with read_transaction(commit_path, configuration) as (connection, _):
        initial = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        states.append(connection.in_transaction)
        try:
            connection.commit()
        except sqlite3.Error as exc:
            commit_error = exc
        states.append(connection.in_transaction)
        if commit_error is None:
            writer_store = Store(commit_path)
            with writer_store.transaction(write=True) as writer_connection:
                writer_connection.execute(
                    """
                    INSERT INTO events(
                        partition, kind, subject_type, subject_id, payload_json, created_at_us
                    ) VALUES ('fixture', 'after-commit', 'operation', 'split', '{}', 23)
                    """
                )
            observed = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            split = observed == initial + 1

    if commit_error is None:
        commit_note = "commit succeeded; ended transaction; split_snapshot=True"
        exc_type = ""
    else:
        commit_note = (
            f"commit denied: {exception_type(commit_error)}: {commit_error}; "
            "transaction remained active; split_snapshot=False"
        )
        exc_type = exception_type(commit_error)
    notes = (
        f"rollback size={before[0]}, sha256={before[1]}, identical=True; "
        f"commit_states={states!r}; {commit_note}; observed_split={split}"
    )
    if not configuration.transaction:
        return Result(
            "error",
            "builtins.AssertionError",
            "no read transaction existed; commit split the snapshot",
            notes,
        )
    return Result("ok", exc_type=exc_type, notes=notes)


def s7(path: Path, configuration: Configuration) -> Result:
    baseline_store = Store(path)

    def baseline_open() -> None:
        connection = baseline_store._connect()
        connection.close()

    def alternative_open() -> None:
        connection, _ = open_connection(path, configuration)
        connection.close()

    try:
        for _ in range(20):
            baseline_open()
            alternative_open()
        was_enabled = gc.isenabled()
        gc.disable()
        try:
            baseline_ns = 0
            alternative_ns = 0
            round_samples: list[tuple[float, float]] = []
            for round_index in range(5):
                round_baseline_ns = 0
                round_alternative_ns = 0
                for pair_index in range(200):
                    calls = (
                        ((baseline_open, "baseline"), (alternative_open, "alternative"))
                        if (round_index + pair_index) % 2 == 0
                        else ((alternative_open, "alternative"), (baseline_open, "baseline"))
                    )
                    for call, label in calls:
                        started = time.perf_counter_ns()
                        call()
                        elapsed = time.perf_counter_ns() - started
                        if label == "baseline":
                            round_baseline_ns += elapsed
                        else:
                            round_alternative_ns += elapsed
                baseline_ns += round_baseline_ns
                alternative_ns += round_alternative_ns
                round_samples.append(
                    (round_baseline_ns / 200_000, round_alternative_ns / 200_000)
                )
        finally:
            if was_enabled:
                gc.enable()
    except Exception as exc:
        return Result("error", exception_type(exc), str(exc), "1000-open benchmark raised")

    baseline_us = baseline_ns / 1_000_000
    alternative_us = alternative_ns / 1_000_000
    delta_us = alternative_us - baseline_us
    ratio = alternative_us / baseline_us
    baseline_rounds = [sample[0] for sample in round_samples]
    alternative_rounds = [sample[1] for sample in round_samples]
    return Result(
        "ok",
        notes=(
            f"measured 1000 interleaved opens each after 20 warmups; "
            f"current _connect={baseline_us:.3f} us/open "
            f"(200-open round range={min(baseline_rounds):.3f}..{max(baseline_rounds):.3f}); "
            f"alternative={alternative_us:.3f} us/open "
            f"(range={min(alternative_rounds):.3f}..{max(alternative_rounds):.3f}); "
            f"delta={delta_us:+.3f} us/open; ratio={ratio:.3f}x"
        ),
    )


def run_probe(probe_id: str, environment: Environment) -> Result:
    path = environment.copy(probe_id)
    configuration = environment.configuration
    functions: dict[str, Callable[[Path, Configuration], Result]] = {
        "R1_select_user_table": r1,
        "R2_pragma_user_version_read": r2,
        "R3_pragma_application_id_read": r3,
        "R4_select_sqlite_schema": r4,
        "R5_validate_ledger_call": r5,
        "R6_connect_setup_pragmas": r6,
        "R7_setconfig_defensive": r7,
        "R8_two_reads_one_snapshot": r8,
        "W1_insert": w1,
        "W2_update": w2,
        "W3_delete": w3,
        "W4_create_table": w4,
        "W5_drop_trigger": w5,
        "W6_alter_table": w6,
        "W7_pragma_user_version_write": w7,
        "W8_pragma_journal_mode_wal": w8,
        "W9_pragma_application_id_write": w9,
        "W10_create_temp_table": w10,
        "W11_attach_and_write": w11,
        "W12_explicit_commit": w12,
        "W13_vacuum": w13,
        "W14_savepoint_insert": w14,
        "W15_pragma_foreign_keys_off": w15,
        "W16_writable_schema_update": w16,
        "W17_reindex_analyze": w17,
        "S1_iterdump_identical": s1,
        "S2_file_bytes_identical": s2,
        "S3_missing_file_refused": s3,
        "S4_uri_hazard_paths": s4,
        "S5_concurrent_writer_visibility": s5,
        "S7_setup_cost_1000_opens": s7,
    }
    try:
        if probe_id == "S6_rollback_vs_commit":
            return s6(path, configuration, environment.base)
        return functions[probe_id](path, configuration)
    except BaseException as exc:
        return Result(
            "error",
            exception_type(exc),
            str(exc) or repr(exc),
            "uncaught probe failure",
        )


def run(configuration: Configuration, output: Path) -> dict[str, Any]:
    document = matrix(configuration)
    write_matrix(output, document)
    with tempfile.TemporaryDirectory(prefix=f"cement-m3u2a-{configuration.stage}-") as raw:
        root = Path(raw)
        base = root / "base.sqlite"
        build_fixture(base, "base-marker")
        environment = Environment(root, base, configuration)
        for index, probe_id in enumerate(PROBE_IDS, start=1):
            result = run_probe(probe_id, environment)
            document["probes"][probe_id] = result.as_probe(probe_id)
            if index % 6 == 0 or index == len(PROBE_IDS):
                write_matrix(output, document)
                print(f"FLUSH {index}/{len(PROBE_IDS)} -> {output}")
    mismatches = [
        probe_id
        for probe_id, probe in document["probes"].items()
        if probe["outcome"] != probe["expected"]
    ]
    print(
        f"COMPLETE stage={configuration.stage} mismatches={len(mismatches)} "
        f"ids={','.join(mismatches) or '-'}"
    )
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    args = parser.parse_args()
    run(STAGES[args.stage], args.matrix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
