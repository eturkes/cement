from collections.abc import Iterator
import ast
import contextlib
import hashlib
import inspect
import io
import json
import pathlib
import sqlite3
import tempfile
import typing
import unittest
from unittest import mock

from cement_runtime import System
from cement_runtime import cli as cement_cli
from cement_runtime import store as store_module
from cement_runtime.errors import IntegrityError, StateError


class ReadCapabilityBatteryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(self.temporary.cleanup)
        self.path = pathlib.Path(self.temporary.name) / "ledger.db"
        self.store = store_module.Store(self.path)

    def test_b01_transaction_remains_active_across_three_reads(self):
        """B1: One snapshot remains active across three reads."""
        with self.store.transaction() as connection:
            for value in (11, 12, 13):
                self.assertTrue(connection.in_transaction)
                self.assertEqual(connection.execute("SELECT ?", (value,)).fetchone()[0], value)
                self.assertTrue(connection.in_transaction)

    def test_b01_concurrent_commit_remains_invisible(self):
        """B1: A concurrent committed row stays invisible."""
        policy = sqlite3.connect(self.path, isolation_level=None)
        try:
            self.assertEqual(policy.execute("PRAGMA journal_mode = WAL").fetchone()[0], "wal")
        finally:
            policy.close()

        marker = "snapshot-marker-11"
        with self.store.transaction() as reader:
            self.assertIsNone(
                reader.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                ).fetchone()
            )
            with self.store.transaction(write=True) as writer:
                writer.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    (marker, "committed"),
                )
            for _ in range(3):
                self.assertTrue(reader.in_transaction)
                self.assertIsNone(
                    reader.execute(
                        "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                    ).fetchone()
                )
        with self.store.transaction() as reader:
            self.assertEqual(
                reader.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                ).fetchone()[0],
                "committed",
            )

    def test_b01_caller_commit_is_denied(self):
        """B1: A caller commit is denied."""
        try:
            with self.store.transaction() as connection:
                connection.commit()
        except Exception as exc:
            violation = getattr(store_module, "_ReadOnlyViolation")
            self.assertIs(type(exc), violation)
            self.assertEqual(str(exc), "read-only ledger transaction refused a write")
        else:
            self.fail("caller commit unexpectedly succeeded")

    def _assert_inner_sql_denied(
        self, statement: str, parameters: tuple[object, ...] = ()
    ) -> None:
        with self.store.transaction() as connection:
            try:
                connection.execute(statement, parameters)
            except sqlite3.DatabaseError as exc:
                self.assertEqual(type(exc), sqlite3.DatabaseError)
                self.assertEqual(str(exc), "not authorized")
                self.assertEqual(exc.sqlite_errorcode, sqlite3.SQLITE_AUTH)
            else:
                self.fail(f"statement unexpectedly succeeded: {statement}")

    def test_b02_temp_table_write_is_denied(self):
        """B2: A TEMP-table write is denied."""
        self._assert_inner_sql_denied("CREATE TEMP TABLE b02_temp(value INTEGER)")

    def test_b02_attached_database_write_is_denied(self):
        """B2: An ATTACH-then-write is denied."""
        attached = self.path.with_name("attached-11.db")
        self._assert_inner_sql_denied(
            "ATTACH DATABASE ? AS b02_auxiliary", (str(attached),)
        )
        self.assertFalse(attached.exists())

    def test_b02_foreign_keys_assignment_is_denied(self):
        """B2: PRAGMA foreign_keys = OFF is denied."""
        self._assert_inner_sql_denied("PRAGMA foreign_keys = OFF")

    def test_b03_existing_ledger_opens(self):
        """B3: An existing ledger opens read-only."""
        self.assertTrue(self.path.is_file())
        with self.store.transaction() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?",
                    (f"schema-v{store_module.SCHEMA_VERSION}",),
                ).fetchone()[0],
                store_module.SCHEMA_FINGERPRINT,
            )
        self.assertTrue(self.path.is_file())

    def test_b03_missing_ledger_is_refused_without_creation(self):
        """B3: A missing ledger is refused and remains absent."""
        self.path.unlink()
        self.assertFalse(self.path.exists())
        caught: Exception | None = None
        try:
            with self.store.transaction() as connection:
                connection.execute("SELECT value FROM schema_metadata").fetchone()
        except Exception as exc:
            caught = exc
        self.assertFalse(self.path.exists(), "missing read created the ledger file")
        self.assertIsNotNone(caught)
        self.assertIs(type(caught), IntegrityError)
        self.assertEqual(str(caught), "ledger file is missing or unreadable")

    def test_b04_encoded_uri_reads_real_ledger_not_raw_decoy(self):
        """B4: An encoded hazardous path reads the real ledger marker."""
        real_path = pathlib.Path(self.temporary.name) / "hazard?query#fragment%percent.db"
        raw_decoy_path = pathlib.Path(self.temporary.name) / "hazard"
        real_store = store_module.Store(real_path)
        decoy_store = store_module.Store(raw_decoy_path)
        for store, marker in (
            (real_store, "real-marker-11"),
            (decoy_store, "raw-decoy-marker-12"),
        ):
            with store.transaction(write=True) as connection:
                connection.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    ("b04-marker", marker),
                )

        raw = sqlite3.connect(f"file:{real_path.absolute()}?mode=ro", uri=True)
        try:
            self.assertEqual(
                raw.execute(
                    "SELECT value FROM schema_metadata WHERE key = 'b04-marker'"
                ).fetchone()[0],
                "raw-decoy-marker-12",
            )
        finally:
            raw.close()

        with real_store.transaction() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT value FROM schema_metadata WHERE key = 'b04-marker'"
                ).fetchone()[0],
                "real-marker-11",
            )

    def _pragma_value(self, name: str) -> object:
        with self.store.transaction() as connection:
            row = connection.execute(f"PRAGMA {name}").fetchone()
        self.assertIsNotNone(row)
        return row[0]

    def test_b05_foreign_keys_readback_is_one(self):
        """B5: PRAGMA foreign_keys reads back as 1."""
        self.assertEqual(self._pragma_value("foreign_keys"), 1)

    def test_b05_busy_timeout_readback_is_ten_thousand(self):
        """B5: PRAGMA busy_timeout reads back as 10000."""
        self.assertEqual(self._pragma_value("busy_timeout"), 10_000)

    def test_b05_synchronous_readback_is_three(self):
        """B5: PRAGMA synchronous reads back as 3."""
        self.assertEqual(self._pragma_value("synchronous"), 3)

    def test_b05_temp_store_readback_is_two(self):
        """B5: PRAGMA temp_store reads back as 2."""
        self.assertEqual(self._pragma_value("temp_store"), 2)

    def test_b05_trusted_schema_readback_is_zero(self):
        """B5: PRAGMA trusted_schema reads back as 0."""
        self.assertEqual(self._pragma_value("trusted_schema"), 0)

    def _record_read_setup(
        self,
    ) -> tuple[
        list[tuple[object, tuple[object, ...], dict[str, object]]],
        list[tuple[object, ...]],
    ]:
        real_connect = sqlite3.connect
        connect_calls: list[
            tuple[object, tuple[object, ...], dict[str, object]]
        ] = []
        events: list[tuple[object, ...]] = []

        class RecordingConnection(sqlite3.Connection):
            def execute(self, sql: str, parameters=(), /):
                events.append(("execute", sql, parameters))
                return super().execute(sql, parameters)

            def setconfig(self, operation: int, enable: bool = True, /) -> None:
                events.append(("setconfig", operation, enable))
                return super().setconfig(operation, enable)

            def set_authorizer(self, callback, /) -> None:
                events.append(("set_authorizer", callback))
                return super().set_authorizer(callback)

        def recording_connect(database, *args, **kwargs):
            connect_calls.append((database, args, dict(kwargs)))
            self.assertNotIn("factory", kwargs)
            return real_connect(database, *args, factory=RecordingConnection, **kwargs)

        with mock.patch.object(store_module.sqlite3, "connect", recording_connect):
            with self.store.transaction() as connection:
                self.assertIsInstance(connection, RecordingConnection)
        return connect_calls, events

    def test_b06_read_connect_arguments_are_exact(self):
        """B6: Connect arguments are exact on both capability paths."""
        read_calls, _ = self._record_read_setup()
        write_calls, _, write_error = self._record_write_transaction(lambda _: None)
        self.assertIsNone(write_error)
        self.assertEqual(
            read_calls,
            [
                (
                    f"{self.path.absolute().as_uri()}?mode=ro",
                    (),
                    {"timeout": 10.0, "isolation_level": None, "uri": True},
                )
            ],
        )
        self.assertEqual(
            write_calls,
            [
                (
                    self.path,
                    (),
                    {"timeout": 10.0, "isolation_level": None},
                )
            ],
        )

    def test_b06_five_pragmas_run_in_exact_order(self):
        """B6: The five setup pragmas run in exact order."""
        _, events = self._record_read_setup()
        self.assertEqual(
            [event[1] for event in events if event[:1] == ("execute",) and str(event[1]).startswith("PRAGMA ")],
            [
                "PRAGMA foreign_keys = ON",
                "PRAGMA busy_timeout = 10000",
                "PRAGMA synchronous = EXTRA",
                "PRAGMA temp_store = MEMORY",
                "PRAGMA trusted_schema = OFF",
            ],
        )

    def test_b06_setconfig_calls_are_exact(self):
        """B6: Both setconfig calls carry their exact arguments."""
        _, events = self._record_read_setup()
        self.assertEqual(
            [event[1:] for event in events if event[:1] == ("setconfig",)],
            [
                (sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
                (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
            ],
        )

    def test_b06_authorizer_is_last_then_begin_runs(self):
        """B6: The authorizer is installed last before BEGIN."""
        _, events = self._record_read_setup()
        begin_index = events.index(("execute", "BEGIN", ()))
        self.assertEqual(events[begin_index - 1][0], "set_authorizer")
        self.assertTrue(callable(events[begin_index - 1][1]))
        self.assertEqual(
            [event[0] for event in events[: begin_index + 1]],
            [
                "execute",
                "execute",
                "execute",
                "execute",
                "execute",
                "setconfig",
                "setconfig",
                "set_authorizer",
                "execute",
            ],
        )

    def test_b07_allowed_bare_foreign_keys_read(self):
        """B7: The allowed bare foreign_keys pragma succeeds."""
        with self.store.transaction() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_b07_foreign_keys_assignment_denied_by_name(self):
        """B7: An assignment on foreign_keys is denied."""
        self._assert_inner_sql_denied("PRAGMA foreign_keys = OFF")

    def test_b07_argumented_table_info_read_is_allowed(self):
        """B7: An argumented table_info introspection pragma succeeds."""
        with self.store.transaction() as connection:
            rows = connection.execute("PRAGMA table_info(schema_metadata)").fetchall()
        self.assertEqual([row["name"] for row in rows], ["key", "value"])

    def test_b07_unlisted_bare_optimize_is_denied(self):
        """B7: The unlisted bare optimize pragma is denied."""
        self._assert_inner_sql_denied("PRAGMA optimize")

    def _assert_translated_and_inner_raw_denial(
        self, statement: str, parameters: tuple[object, ...] = ()
    ) -> None:
        outer: Exception | None = None
        try:
            with self.store.transaction() as connection:
                connection.execute(statement, parameters)
        except Exception as exc:
            outer = exc
        if outer is None:
            self.fail(f"statement unexpectedly succeeded: {statement}")

        violation = getattr(store_module, "_ReadOnlyViolation")
        self.assertIs(type(outer), violation)
        self.assertEqual(str(outer), "read-only ledger transaction refused a write")
        cause = outer.__cause__
        self.assertIsNotNone(cause)
        self.assertIs(type(cause), sqlite3.DatabaseError)
        self.assertEqual(str(cause), "not authorized")
        self.assertEqual(cause.sqlite_errorcode, sqlite3.SQLITE_AUTH)

        with self.store.transaction() as connection:
            try:
                connection.execute(statement, parameters)
            except Exception as raw:
                self.assertIs(type(raw), sqlite3.DatabaseError)
                self.assertEqual(str(raw), "not authorized")
                self.assertEqual(raw.sqlite_errorcode, sqlite3.SQLITE_AUTH)
            else:
                self.fail(f"inner-caught statement unexpectedly succeeded: {statement}")

    def test_b08_dml_denial_translation_and_inner_raw_error(self):
        """B8: DML denial has the exact outer and inner error surfaces."""
        self._assert_translated_and_inner_raw_denial(
            "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
            ("b08-dml", "11"),
        )

    def test_b08_ddl_denial_translation_and_inner_raw_error(self):
        """B8: DDL denial has the exact outer and inner error surfaces."""
        self._assert_translated_and_inner_raw_denial(
            "CREATE TABLE b08_ddl(value INTEGER)"
        )

    def test_b08_attach_denial_translation_and_inner_raw_error(self):
        """B8: ATTACH denial has the exact outer and inner error surfaces."""
        self._assert_translated_and_inner_raw_denial(
            "ATTACH DATABASE ? AS b08_attached",
            (str(self.path.with_name("b08-attached-12.db")),),
        )

    def test_b08_temp_denial_translation_and_inner_raw_error(self):
        """B8: TEMP-write denial has the exact outer and inner error surfaces."""
        self._assert_translated_and_inner_raw_denial(
            "CREATE TEMP TABLE b08_temp(value INTEGER)"
        )

    def test_b08_pragma_denial_translation_and_inner_raw_error(self):
        """B8: Pragma-write denial has the exact outer and inner error surfaces."""
        self._assert_translated_and_inner_raw_denial("PRAGMA foreign_keys = OFF")

    def test_b09_denial_class_is_not_state_or_integrity_error(self):
        """B9: The denial class stays distinct from state and integrity errors."""
        caught: Exception | None = None
        try:
            with self.store.transaction() as connection:
                connection.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    ("b09-denial", "13"),
                )
        except Exception as exc:
            caught = exc
        if caught is None:
            self.fail("read-path DML unexpectedly succeeded")
        violation = getattr(store_module, "_ReadOnlyViolation")
        self.assertIs(type(caught), violation)
        self.assertNotIsInstance(caught, (StateError, IntegrityError))

    def test_b10_missing_ledger_api_error_is_exact_and_noncreating(self):
        """B10: The API reports the exact missing-ledger integrity error."""
        self.path.unlink()
        caught: Exception | None = None
        try:
            with self.store.transaction() as connection:
                connection.execute("SELECT value FROM schema_metadata").fetchone()
        except Exception as exc:
            caught = exc
        self.assertFalse(self.path.exists(), "missing API read created the ledger file")
        self.assertIs(type(caught), IntegrityError)
        self.assertEqual(str(caught), "ledger file is missing or unreadable")

    def test_b10_missing_ledger_cli_exit_is_five(self):
        """B10: The CLI reports a missing ledger with exit 5."""
        system = System(self.path)
        self.path.unlink()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(cement_cli, "System", return_value=system),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = cement_cli.main(
                ["--db", str(self.path), "--partition", "tenant", "events"]
            )
        self.assertEqual(status, 5)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            json.loads(stderr.getvalue()),
            {
                "error": "integrity",
                "message": "ledger file is missing or unreadable",
            },
        )
        self.assertFalse(self.path.exists())

    def test_b11_vacuum_has_read_write_parity(self):
        """B11: VACUUM has identical class and message on both paths."""
        outcomes: list[tuple[type[Exception], str]] = []
        for write in (False, True):
            try:
                with self.store.transaction(write=write) as connection:
                    connection.execute("VACUUM")
            except Exception as exc:
                outcomes.append((type(exc), str(exc)))
            else:
                self.fail(f"VACUUM unexpectedly succeeded with write={write}")
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[0], (StateError, "database is busy or unavailable"))

    def test_b12_caller_rollback_is_denied_without_splitting_snapshot(self):
        """B12: Caller rollback is denied and preserves the snapshot."""
        policy = sqlite3.connect(self.path, isolation_level=None)
        try:
            self.assertEqual(policy.execute("PRAGMA journal_mode = WAL").fetchone()[0], "wal")
        finally:
            policy.close()

        marker = "b12-snapshot-14"
        with self.store.transaction() as reader:
            self.assertIsNone(
                reader.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                ).fetchone()
            )
            try:
                reader.rollback()
            except sqlite3.DatabaseError as exc:
                self.assertIs(type(exc), sqlite3.DatabaseError)
                self.assertEqual(str(exc), "not authorized")
                self.assertEqual(exc.sqlite_errorcode, sqlite3.SQLITE_AUTH)
            else:
                self.fail("caller rollback unexpectedly succeeded")
            self.assertTrue(reader.in_transaction)
            with self.store.transaction(write=True) as writer:
                writer.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    (marker, "committed"),
                )
            self.assertTrue(reader.in_transaction)
            self.assertIsNone(
                reader.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                ).fetchone()
            )

    def test_b13_executescript_is_denied_without_splitting_snapshot(self):
        """B13: executescript implicit COMMIT is denied and preserves the snapshot."""
        with self.store.transaction() as connection:
            self.assertTrue(connection.in_transaction)
            try:
                connection.executescript("SELECT 1;")
            except sqlite3.DatabaseError as exc:
                self.assertIs(type(exc), sqlite3.DatabaseError)
                self.assertEqual(str(exc), "not authorized")
                self.assertEqual(exc.sqlite_errorcode, sqlite3.SQLITE_AUTH)
            else:
                self.fail("executescript implicit COMMIT unexpectedly succeeded")
            self.assertTrue(connection.in_transaction)
            self.assertEqual(connection.execute("SELECT 13").fetchone()[0], 13)

    def test_b14_malformed_read_keeps_state_error(self):
        """B14: A malformed read keeps its StateError mapping."""
        with self.assertRaises(StateError) as raised:
            with self.store.transaction() as connection:
                connection.execute("SELECT FROM schema_metadata")
        self.assertEqual(str(raised.exception), "database is busy or unavailable")
        self.assertIs(type(raised.exception.__cause__), sqlite3.OperationalError)

    def test_b14_non_denial_database_error_keeps_integrity_error(self):
        """B14: A non-denial DatabaseError keeps its exact IntegrityError mapping."""
        original = sqlite3.DatabaseError("b14 injected non-denial")
        with self.assertRaises(IntegrityError) as raised:
            with self.store.transaction():
                raise original
        self.assertEqual(
            str(raised.exception),
            "database operation failed an integrity check",
        )
        self.assertIs(raised.exception.__cause__, original)

    def _record_write_transaction(self, callback, *, fail_setup: bool = False):
        real_connect = sqlite3.connect
        connect_calls: list[
            tuple[object, tuple[object, ...], dict[str, object]]
        ] = []
        events: list[tuple[object, ...]] = []

        class RecordingConnection(sqlite3.Connection):
            def execute(self, sql: str, parameters=(), /):
                events.append(("execute", sql, parameters))
                if fail_setup and sql == "PRAGMA foreign_keys = ON":
                    raise sqlite3.OperationalError("b15 injected setup failure")
                return super().execute(sql, parameters)

            def set_authorizer(self, authorizer_callback, /) -> None:
                events.append(("set_authorizer", authorizer_callback))
                return super().set_authorizer(authorizer_callback)

            def commit(self) -> None:
                events.append(("commit",))
                return super().commit()

            def rollback(self) -> None:
                events.append(("rollback",))
                return super().rollback()

            def close(self) -> None:
                events.append(("close",))
                return super().close()

        def recording_connect(database, *args, **kwargs):
            connect_calls.append((database, args, dict(kwargs)))
            self.assertNotIn("factory", kwargs)
            return real_connect(database, *args, factory=RecordingConnection, **kwargs)

        caught: Exception | None = None
        with mock.patch.object(store_module.sqlite3, "connect", recording_connect):
            try:
                with self.store.transaction(write=True) as connection:
                    callback(connection)
            except Exception as exc:
                caught = exc
        return connect_calls, events, caught

    def test_b15_write_connect_and_begin_are_exact(self):
        """B15: The write path uses exact plain-connect and BEGIN IMMEDIATE calls."""
        connect_calls, events, caught = self._record_write_transaction(lambda _: None)
        self.assertIsNone(caught)
        self.assertEqual(
            connect_calls,
            [
                (
                    self.path,
                    (),
                    {"timeout": 10.0, "isolation_level": None},
                )
            ],
        )
        self.assertEqual(
            [event for event in events if event[:1] == ("set_authorizer",)], []
        )
        self.assertEqual(
            [event for event in events if event[:2] == ("execute", "BEGIN IMMEDIATE")],
            [("execute", "BEGIN IMMEDIATE", ())],
        )

    def test_b15_write_clean_exit_commits(self):
        """B15: A clean write exit commits."""
        marker = "b15-clean-15"

        def insert(connection) -> None:
            connection.execute(
                "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                (marker, "committed"),
            )

        _, events, caught = self._record_write_transaction(insert)
        self.assertIsNone(caught)
        self.assertEqual([event for event in events if event == ("commit",)], [("commit",)])
        self.assertEqual([event for event in events if event == ("rollback",)], [])
        check = sqlite3.connect(self.path)
        try:
            self.assertEqual(
                check.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                ).fetchone()[0],
                "committed",
            )
        finally:
            check.close()

    def test_b15_write_exception_rolls_back(self):
        """B15: An exceptional write exit rolls back."""
        marker = "b15-rollback-16"
        injected = RuntimeError("b15 injected body failure")

        def insert_then_fail(connection) -> None:
            connection.execute(
                "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                (marker, "must-roll-back"),
            )
            raise injected

        _, events, caught = self._record_write_transaction(insert_then_fail)
        self.assertIs(caught, injected)
        self.assertEqual(
            [event for event in events if event == ("rollback",)], [("rollback",)]
        )
        self.assertEqual([event for event in events if event == ("commit",)], [])
        check = sqlite3.connect(self.path)
        try:
            self.assertIsNone(
                check.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", (marker,)
                ).fetchone()
            )
        finally:
            check.close()

    def test_b15_write_connection_always_closes(self):
        """B15: The write connection always closes."""
        def fail(_connection) -> None:
            raise RuntimeError("b15 close-path failure")

        cases = (
            ("clean", lambda _: None, False),
            ("body-exception", fail, False),
            ("setup-exception", lambda _: self.fail("body reached"), True),
        )
        for name, callback, fail_setup in cases:
            with self.subTest(path=name):
                _, events, caught = self._record_write_transaction(
                    callback, fail_setup=fail_setup
                )
                self.assertEqual(
                    [event for event in events if event == ("close",)], [("close",)]
                )
                self.assertEqual(events[-1], ("close",))
                if fail_setup:
                    self.assertIs(type(caught), StateError)

    def test_b16_transaction_public_shape_is_frozen(self):
        """B16: The transaction signature and type hints stay exact."""
        method = store_module.Store.transaction
        signature = inspect.signature(method)
        parameters = signature.parameters
        self.assertEqual(list(parameters), ["self", "write"])
        self.assertIs(parameters["self"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertIs(parameters["write"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(parameters["write"].default, False)
        hints = typing.get_type_hints(method)
        self.assertIs(hints["write"], bool)
        self.assertEqual(hints["return"], Iterator[sqlite3.Connection])
        self.assertTrue(hasattr(method, "__wrapped__"))
        self.assertTrue(inspect.isgeneratorfunction(method.__wrapped__))

    def test_b17_recursive_cte_read_succeeds(self):
        """B17: A recursive CTE read succeeds."""
        with self.store.transaction() as connection:
            rows = connection.execute(
                """
                WITH RECURSIVE numbers(value) AS (
                    VALUES (11)
                    UNION ALL
                    SELECT value + 1 FROM numbers WHERE value < 13
                )
                SELECT value FROM numbers ORDER BY value
                """
            ).fetchall()
        self.assertEqual([row[0] for row in rows], [11, 12, 13])

    def test_b18_savepoint_is_denied(self):
        """B18: SAVEPOINT is denied inside a read block."""
        self._assert_inner_sql_denied("SAVEPOINT b18_snapshot")

    def test_b19_layered_guarantee_survives_authorizer_removal(self):
        """B19: Authorizer removal leaves the ledger protected but not ATTACH."""
        before = hashlib.sha256(self.path.read_bytes()).digest()
        attached = self.path.with_name("b19-attached-17.db")
        ledger_refusal: sqlite3.OperationalError | None = None
        with self.store.transaction() as connection:
            connection.set_authorizer(None)
            try:
                connection.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    ("b19-ledger", "must-not-land"),
                )
            except sqlite3.OperationalError as exc:
                ledger_refusal = exc
            connection.execute("ATTACH DATABASE ? AS b19_auxiliary", (str(attached),))
            connection.execute("CREATE TABLE b19_auxiliary.probe(value INTEGER)")
            connection.execute("INSERT INTO b19_auxiliary.probe VALUES (17)")
            connection.commit()

        self.assertIsNotNone(ledger_refusal)
        self.assertIs(type(ledger_refusal), sqlite3.OperationalError)
        self.assertEqual(ledger_refusal.sqlite_errorcode, sqlite3.SQLITE_READONLY)
        self.assertEqual(
            str(ledger_refusal), "attempt to write a readonly database"
        )
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(), before)
        check = sqlite3.connect(attached)
        try:
            self.assertEqual(check.execute("SELECT value FROM probe").fetchone()[0], 17)
        finally:
            check.close()

    def test_b19_escaping_readonly_refusal_is_translated(self):
        """B19: A mode=ro refusal escaping the block becomes the read-only violation."""
        violation = getattr(store_module, "_ReadOnlyViolation")
        with self.assertRaises(violation) as caught:
            with self.store.transaction() as connection:
                connection.set_authorizer(None)
                connection.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                    ("b19-escape", "must-not-land"),
                )
        self.assertEqual(
            str(caught.exception), "read-only ledger transaction refused a write"
        )
        self.assertEqual(
            caught.exception.__cause__.sqlite_errorcode, sqlite3.SQLITE_READONLY
        )

    def test_b20_read_site_census_has_no_mutations(self):
        """B20: The reachability census finds zero mutating read sites."""
        source_path = pathlib.Path(__file__).resolve().parents[1] / "src/cement_runtime/system.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        system_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "System"
        )
        methods = {
            node.name: node
            for node in system_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        violations: list[str] = []
        reached_helpers: set[str] = set()

        def sql_text(node: ast.expr) -> str | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.JoinedStr):
                return "".join(
                    value.value if isinstance(value, ast.Constant) else "{expression}"
                    for value in node.values
                )
            return None

        def scan(
            body: list[ast.stmt],
            connection_names: set[str],
            trail: tuple[str, ...],
        ) -> None:
            for statement in body:
                for node in ast.walk(statement):
                    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                        continue
                    receiver = node.func.value
                    if isinstance(receiver, ast.Name) and receiver.id in connection_names:
                        if node.func.attr in {"commit", "rollback"}:
                            violations.append(
                                f"{' -> '.join(trail)}:{node.lineno} calls {node.func.attr}()"
                            )
                        if node.func.attr in {"execute", "executemany", "executescript"}:
                            text = sql_text(node.args[0]) if node.args else None
                            if text is None:
                                violations.append(
                                    f"{' -> '.join(trail)}:{node.lineno} uses dynamic SQL"
                                )
                            else:
                                verb = text.lstrip().split(None, 1)[0].upper()
                                if verb != "SELECT":
                                    violations.append(
                                        f"{' -> '.join(trail)}:{node.lineno} executes {verb}"
                                    )
                    if not (
                        isinstance(receiver, ast.Name)
                        and receiver.id == "self"
                        and node.func.attr in methods
                    ):
                        continue
                    target = methods[node.func.attr]
                    positional = [*target.args.posonlyargs, *target.args.args]
                    forwarded: set[str] = set()
                    for index, argument in enumerate(node.args, start=1):
                        if (
                            isinstance(argument, ast.Name)
                            and argument.id in connection_names
                            and index < len(positional)
                        ):
                            forwarded.add(positional[index].arg)
                    for keyword in node.keywords:
                        if (
                            keyword.arg is not None
                            and isinstance(keyword.value, ast.Name)
                            and keyword.value.id in connection_names
                        ):
                            forwarded.add(keyword.arg)
                    if forwarded and node.func.attr not in trail:
                        reached_helpers.add(node.func.attr)
                        scan(target.body, forwarded, (*trail, node.func.attr))

        read_sites: list[tuple[str, int]] = []
        write_sites: list[tuple[str, int]] = []
        for method_name, method in methods.items():
            for node in ast.walk(method):
                if not isinstance(node, ast.With):
                    continue
                for item in node.items:
                    call = item.context_expr
                    if not (
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "transaction"
                        and isinstance(call.func.value, ast.Attribute)
                        and call.func.value.attr == "store"
                        and isinstance(call.func.value.value, ast.Name)
                        and call.func.value.value.id == "self"
                    ):
                        continue
                    write_argument = next(
                        (keyword.value for keyword in call.keywords if keyword.arg == "write"),
                        ast.Constant(False),
                    )
                    if not (
                        isinstance(write_argument, ast.Constant)
                        and isinstance(write_argument.value, bool)
                    ):
                        violations.append(
                            f"{method_name}:{node.lineno} has a nonliteral write capability"
                        )
                        continue
                    site = (method_name, node.lineno)
                    if write_argument.value:
                        write_sites.append(site)
                        continue
                    read_sites.append(site)
                    if not isinstance(item.optional_vars, ast.Name):
                        violations.append(
                            f"{method_name}:{node.lineno} has no simple connection binding"
                        )
                        continue
                    scan(node.body, {item.optional_vars.id}, (method_name,))

        self.assertEqual(len(read_sites), 17)
        self.assertEqual(len(write_sites), 15)
        self.assertEqual(len(reached_helpers), 12)
        self.assertEqual(violations, [])

    def test_b21_validate_ledger_succeeds_inside_enforced_block(self):
        """B21: Explicit ledger validation succeeds inside an enforced block."""
        with mock.patch.object(
            store_module,
            "_validate_ledger",
            wraps=store_module._validate_ledger,
        ) as validate:
            with self.store.transaction() as connection:
                store_module._validate_ledger(connection)
                self.assertTrue(connection.in_transaction)
            validate.assert_called_once_with(connection)

    def test_b21_transaction_never_calls_validate_ledger(self):
        """B21: A transaction makes zero ledger-validation calls."""
        with mock.patch.object(
            store_module,
            "_validate_ledger",
            wraps=store_module._validate_ledger,
        ) as validate:
            with self.store.transaction() as connection:
                self.assertEqual(connection.execute("SELECT 21").fetchone()[0], 21)
            validate.assert_not_called()

    def test_b22_schema_version_is_two(self):
        """B22: SCHEMA_VERSION stays 2."""
        self.assertEqual(store_module.SCHEMA_VERSION, 2)

    def test_b22_schema_ddl_matches_entry_digest(self):
        """B22: Store schema DDL stays byte-identical to unit entry."""
        payload = store_module.SCHEMA.encode("utf-8")
        expected = "5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77"
        self.assertEqual(len(payload), 14_580)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), expected)
        self.assertEqual(store_module.SCHEMA_FINGERPRINT, expected)
