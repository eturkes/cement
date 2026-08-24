#!/usr/bin/env python
"""Re-derive M3.3's SQLite commit-uncertainty observations."""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import uuid
from unittest import mock

from cement_runtime import Candidate, CompilePolicy, System
from cement_runtime import store as store_module
from cement_runtime import system as system_module

_REAL_CONNECT = sqlite3.connect
_COMMIT_ERROR = "synthetic commit uncertainty"
_PARTITION = "tenant_a"
_OPERATION = "echo_1"


class _Source:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def propose(self, request: object) -> Candidate:
        self.calls.append(request)
        return Candidate(output={"v": 20}, provenance={"model": "source-window"})


@dataclass
class _CommitState:
    mode: str = "pass"
    fail_on_commit: int = 1
    commit_calls: int = 0
    durable_commit_calls: int = 0
    rollback_calls: int = 0
    positive_control_commit_calls: int = 0

    def arm(self, mode: str, *, fail_on_commit: int = 1) -> None:
        self.mode = mode
        self.fail_on_commit = fail_on_commit
        self.commit_calls = 0
        self.durable_commit_calls = 0
        self.rollback_calls = 0


def _spy_connect(state: _CommitState):
    class _InjectedConnection(sqlite3.Connection):
        def commit(self) -> None:
            state.commit_calls += 1
            if state.mode == "pass":
                super().commit()
                state.durable_commit_calls += 1
                return
            if state.mode not in {"after", "before"}:
                raise AssertionError(f"unknown commit mode: {state.mode}")
            if state.commit_calls != state.fail_on_commit:
                super().commit()
                state.durable_commit_calls += 1
                return
            if state.mode == "after":
                super().commit()
                state.durable_commit_calls += 1
            raise sqlite3.OperationalError(_COMMIT_ERROR)

        def rollback(self) -> None:
            state.rollback_calls += 1
            super().rollback()

    def connect(*args, **kwargs):
        kwargs["factory"] = _InjectedConnection
        return _REAL_CONNECT(*args, **kwargs)

    return connect


def _positive_control(system: System, state: _CommitState) -> None:
    state.arm("pass")
    with system.store.transaction(write=True) as connection:
        connection.execute("CREATE TEMP TABLE commit_spy_control(value INTEGER)")
        connection.execute("INSERT INTO commit_spy_control VALUES (1)")
    state.positive_control_commit_calls = state.commit_calls
    if state.positive_control_commit_calls != 1:
        raise AssertionError("commit spy positive control did not observe exactly one commit")


def _table_counts(database: Path) -> tuple[tuple[str, ...], dict[str, int]]:
    with closing(_REAL_CONNECT(database)) as connection:
        names = tuple(
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        )
        counts = {
            name: int(connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0])
            for name in names
        }
    return names, counts


def _stored_submission(database: Path) -> tuple[list[str], list[dict[str, str]]]:
    with closing(_REAL_CONNECT(database)) as connection:
        proposals = [
            str(row[0])
            for row in connection.execute("SELECT id FROM proposals ORDER BY id")
        ]
        requests = [
            {"request_id": str(row[0]), "proposal_id": str(row[1])}
            for row in connection.execute(
                "SELECT id, proposal_id FROM requests ORDER BY id"
            )
        ]
    return proposals, requests


def _stored_binding(database: Path, proposal_id: str) -> dict[str, str]:
    with closing(_REAL_CONNECT(database)) as connection:
        row = connection.execute(
            """
            SELECT p.id, p.request_id, r.id, r.proposal_id
            FROM proposals AS p
            JOIN requests AS r
              ON r.partition = p.partition AND r.id = p.request_id
            WHERE p.id = ?
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        raise AssertionError("stored proposal/request binding disappeared")
    return {
        "proposal_id": str(row[0]),
        "proposal_request_id": str(row[1]),
        "request_id": str(row[2]),
        "request_proposal_id": str(row[3]),
    }


def _ledger_snapshot(database: Path) -> dict[str, object]:
    names, counts = _table_counts(database)
    with closing(_REAL_CONNECT(database)) as connection:
        sequence = connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
        ).fetchone()
        dump = "\n".join(connection.iterdump())
    return {
        "application_tables": names,
        "counts": counts,
        "dump": dump,
        "event_sequence": 0 if sequence is None else int(sequence[0]),
        "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
    }


def _request_rows(database: Path) -> list[dict[str, object]]:
    with closing(_REAL_CONNECT(database)) as connection:
        rows = connection.execute(
            """
            SELECT id, status, proposal_id, lease_owner, attempts
            FROM requests ORDER BY id
            """
        ).fetchall()
    return [
        {
            "attempts": int(row[4]),
            "id": str(row[0]),
            "lease_owner_present": row[3] is not None,
            "proposal_id": None if row[2] is None else str(row[2]),
            "status": str(row[1]),
        }
        for row in rows
    ]


def _traceback_signature(error: BaseException | None) -> list[str] | None:
    if error is None:
        return None
    frames: list[str] = []
    traceback = error.__traceback__
    while traceback is not None:
        frames.append(
            f"{Path(traceback.tb_frame.f_code.co_filename).name}:"
            f"{traceback.tb_frame.f_code.co_name}"
        )
        traceback = traceback.tb_next
    return frames


def _exception_surface(error: BaseException) -> dict[str, object]:
    def summary(item: BaseException | None) -> dict[str, object] | None:
        if item is None:
            return None
        return {
            "args": list(item.args),
            "class": type(item).__name__,
            "message": str(item),
            "repr": repr(item),
            "traceback": _traceback_signature(item),
        }

    return {
        "args": list(error.args),
        "cause": summary(error.__cause__),
        "class": type(error).__name__,
        "context": summary(error.__context__),
        "message": str(error),
        "repr": repr(error),
        "suppress_context": error.__suppress_context__,
        "traceback": _traceback_signature(error),
    }


def _compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _measure_direct_after(root: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        database = Path(temporary) / "direct-after.db"
        system = System(database)
        system.register_operation(
            _PARTITION,
            _OPERATION,
            policy=CompilePolicy(2, 2, 0),
        )
        names, before = _table_counts(database)
        state = _CommitState()
        returned: str | None = None
        error: Exception | None = None
        with (
            mock.patch.object(store_module.sqlite3, "connect", _spy_connect(state)),
            mock.patch.object(
                system_module.uuid,
                "uuid4",
                side_effect=[uuid.UUID(int=1), uuid.UUID(int=2)],
            ),
        ):
            _positive_control(system, state)
            state.arm("after")
            try:
                returned = system.submit_proposal(
                    _PARTITION,
                    _OPERATION,
                    {"k": 1},
                    candidate=Candidate(
                        output={"v": 10},
                        provenance={"model": "window"},
                    ),
                )
            except Exception as caught:
                error = caught
        if error is None:
            raise AssertionError("commit-after-durability injection did not raise")
        after_names, after = _table_counts(database)
        if after_names != names:
            raise AssertionError("application table set changed during measurement")
        proposals, requests = _stored_submission(database)
        pending = system.proposals(_PARTITION, status="pending")
        if len(proposals) != 1:
            raise AssertionError("direct uncertainty measurement expected one proposal")
        view = system.get_proposal(_PARTITION, proposals[0])
        binding = _stored_binding(database, proposals[0])
        deltas = {name: after[name] - before[name] for name in names}
        changed = {name: delta for name, delta in deltas.items() if delta}
        return {
            "W01": _compact(
                {
                    "caller_error_class": type(error).__name__,
                    "caller_error_message": str(error),
                    "caller_proposal_id": returned,
                    "commit_calls": state.commit_calls,
                    "durable_commit_calls": state.durable_commit_calls,
                    "positive_control_commit_calls": state.positive_control_commit_calls,
                    "rollback_calls": state.rollback_calls,
                }
            ),
            "W02": _compact(
                {
                    "application_table_count": len(names),
                    "application_tables": list(names),
                    "changed_table_deltas": changed,
                    "table_deltas": deltas,
                }
            ),
            "W03": _compact(
                {
                    "call_raised": True,
                    "caller_proposal_id": returned,
                    "stored_proposal_ids": proposals,
                    "stored_request_bindings": requests,
                }
            ),
            "W05": _compact(
                {
                    "pending_count": len(pending),
                    "pending_ids": [str(row["id"]) for row in pending],
                    "pending_request_ids": [str(row["request_id"]) for row in pending],
                    "pending_statuses": [str(row["status"]) for row in pending],
                }
            ),
            "W06": _compact(
                {
                    "id": view.id,
                    "input": view.input,
                    "operation": view.operation,
                    "operation_revision": view.operation_revision,
                    "partition": view.partition,
                    "proposed_output": view.proposed_output,
                    "provenance": view.provenance,
                    "request_id": view.request_id,
                    "view_class": type(view).__name__,
                }
            ),
            "W07": _compact(
                {
                    "all_proposal_ids_equal": (
                        str(pending[0]["id"])
                        == view.id
                        == binding["proposal_id"]
                        == binding["request_proposal_id"]
                    ),
                    "all_request_ids_equal": (
                        str(pending[0]["request_id"])
                        == view.request_id
                        == binding["proposal_request_id"]
                        == binding["request_id"]
                    ),
                    "feed_proposal_id": str(pending[0]["id"]),
                    "feed_request_id": str(pending[0]["request_id"]),
                    "stored_binding": binding,
                    "view_request_id": view.request_id,
                }
            ),
        }


def _measure_source_after(root: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        database = Path(temporary) / "source-after.db"
        source = _Source()
        system = System(database, candidate_source=source)
        system.register_operation(
            _PARTITION,
            _OPERATION,
            policy=CompilePolicy(2, 2, 0),
        )
        names, before = _table_counts(database)
        state = _CommitState()
        returned: str | None = None
        error: Exception | None = None
        with (
            mock.patch.object(store_module.sqlite3, "connect", _spy_connect(state)),
            mock.patch.object(
                system_module.uuid,
                "uuid4",
                side_effect=[uuid.UUID(int=3), uuid.UUID(int=4)],
            ),
        ):
            _positive_control(system, state)
            state.arm("after")
            try:
                returned = system.propose(_PARTITION, _OPERATION, {"k": 2})
            except Exception as caught:
                error = caught
        if error is None:
            raise AssertionError("source commit-after-durability injection did not raise")
        after_names, after = _table_counts(database)
        if after_names != names:
            raise AssertionError("application table set changed during source measurement")
        proposals, requests = _stored_submission(database)
        deltas = {name: after[name] - before[name] for name in names}
        changed = {name: delta for name, delta in deltas.items() if delta}
        return {
            "W04": _compact(
                {
                    "application_table_count": len(names),
                    "caller_error_class": type(error).__name__,
                    "caller_error_message": str(error),
                    "caller_proposal_id": returned,
                    "changed_table_deltas": changed,
                    "commit_calls": state.commit_calls,
                    "durable_commit_calls": state.durable_commit_calls,
                    "positive_control_commit_calls": state.positive_control_commit_calls,
                    "read_snapshot_rollbacks": state.rollback_calls,
                    "source_calls": len(source.calls),
                    "stored_proposal_ids": proposals,
                    "stored_request_bindings": requests,
                    "table_deltas": deltas,
                }
            )
        }


def _measure_control(root: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        database = Path(temporary) / "control.db"
        system = System(database)
        system.register_operation(
            _PARTITION,
            _OPERATION,
            policy=CompilePolicy(2, 2, 0),
        )
        names, before = _table_counts(database)
        state = _CommitState()
        with (
            mock.patch.object(store_module.sqlite3, "connect", _spy_connect(state)),
            mock.patch.object(
                system_module.uuid,
                "uuid4",
                side_effect=[uuid.UUID(int=5), uuid.UUID(int=6)],
            ),
        ):
            _positive_control(system, state)
            state.arm("pass")
            returned = system.submit_proposal(
                _PARTITION,
                _OPERATION,
                {"k": 3},
                candidate=Candidate(
                    output={"v": 30},
                    provenance={"model": "control"},
                ),
            )
        after_names, after = _table_counts(database)
        if after_names != names:
            raise AssertionError("application table set changed during control")
        proposals, requests = _stored_submission(database)
        deltas = {name: after[name] - before[name] for name in names}
        changed = {name: delta for name, delta in deltas.items() if delta}
        return {
            "W08": _compact(
                {
                    "application_table_count": len(names),
                    "caller_error_class": None,
                    "caller_error_message": None,
                    "caller_proposal_id": returned,
                    "changed_table_deltas": changed,
                    "commit_calls": state.commit_calls,
                    "durable_commit_calls": state.durable_commit_calls,
                    "positive_control_commit_calls": state.positive_control_commit_calls,
                    "return_matches_stored": proposals == [returned],
                    "rollback_calls": state.rollback_calls,
                    "stored_proposal_ids": proposals,
                    "stored_request_bindings": requests,
                    "table_deltas": deltas,
                }
            )
        }


def _measure_interior_failures(root: Path) -> dict[str, str]:
    trials: list[dict[str, object]] = []
    for fail_after in (1, 2, 3):
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            database = Path(temporary) / f"interior-{fail_after}.db"
            system = System(database)
            system.register_operation(
                _PARTITION,
                _OPERATION,
                policy=CompilePolicy(2, 2, 0),
            )
            counters = {
                "commit_calls": 0,
                "connection_count": 0,
                "execute_calls": 0,
                "rollback_calls": 0,
                "successful_commit_calls": 0,
            }
            interior_writes: list[str] = []
            armed = False

            class _InteriorConnection(sqlite3.Connection):
                def execute(self, sql, parameters=()):
                    counters["execute_calls"] += 1
                    cursor = super().execute(sql, parameters)
                    normalized = " ".join(str(sql).lower().split())
                    table = next(
                        (
                            name
                            for name in ("requests", "events", "proposals")
                            if normalized.startswith(f"insert into {name}")
                        ),
                        None,
                    )
                    if armed and table is not None:
                        interior_writes.append(table)
                        if len(interior_writes) == fail_after:
                            raise sqlite3.IntegrityError(
                                f"injected after interior write {fail_after}"
                            )
                    return cursor

                def commit(self) -> None:
                    counters["commit_calls"] += 1
                    super().commit()
                    counters["successful_commit_calls"] += 1

                def rollback(self) -> None:
                    counters["rollback_calls"] += 1
                    super().rollback()

            def connect(*args, **kwargs):
                counters["connection_count"] += 1
                kwargs["factory"] = _InteriorConnection
                return _REAL_CONNECT(*args, **kwargs)

            with mock.patch.object(store_module.sqlite3, "connect", connect):
                before_commit = counters.copy()
                with system.store.transaction(write=True) as connection:
                    connection.execute("CREATE TEMP TABLE commit_control(value INTEGER)")
                    connection.execute("INSERT INTO commit_control VALUES (1)")
                positive_commit_calls = (
                    counters["commit_calls"] - before_commit["commit_calls"]
                )
                positive_commit_connections = (
                    counters["connection_count"] - before_commit["connection_count"]
                )
                positive_commit_execute_calls = (
                    counters["execute_calls"] - before_commit["execute_calls"]
                )
                if (
                    positive_commit_calls != 1
                    or positive_commit_connections != 1
                    or positive_commit_execute_calls <= 0
                ):
                    raise AssertionError("interior spy commit positive control failed")

                before_rollback = counters.copy()
                try:
                    with system.store.transaction(write=True) as connection:
                        connection.execute(
                            "CREATE TEMP TABLE rollback_control(value INTEGER)"
                        )
                        connection.execute("INSERT INTO rollback_control VALUES (1)")
                        raise RuntimeError("rollback positive control")
                except RuntimeError as error:
                    if str(error) != "rollback positive control":
                        raise
                positive_rollback_calls = (
                    counters["rollback_calls"] - before_rollback["rollback_calls"]
                )
                positive_rollback_connections = (
                    counters["connection_count"] - before_rollback["connection_count"]
                )
                positive_rollback_execute_calls = (
                    counters["execute_calls"] - before_rollback["execute_calls"]
                )
                if (
                    positive_rollback_calls != 1
                    or positive_rollback_connections != 1
                    or positive_rollback_execute_calls <= 0
                ):
                    raise AssertionError("interior spy rollback positive control failed")

                baseline = _ledger_snapshot(database)
                for key in counters:
                    counters[key] = 0
                armed = True
                caught: Exception | None = None
                try:
                    system.submit_proposal(
                        _PARTITION,
                        _OPERATION,
                        {"k": 4},
                        candidate=Candidate(
                            output={"v": 40},
                            provenance={"model": "interior"},
                        ),
                    )
                except Exception as error:
                    caught = error
            if caught is None:
                raise AssertionError(f"interior injection {fail_after} did not raise")
            after = _ledger_snapshot(database)
            before_names = baseline["application_tables"]
            after_names = after["application_tables"]
            before_counts = baseline["counts"]
            after_counts = after["counts"]
            if (
                not isinstance(before_names, tuple)
                or not isinstance(after_names, tuple)
                or not isinstance(before_counts, dict)
                or not isinstance(after_counts, dict)
                or before_names != after_names
            ):
                raise AssertionError("interior measurement schema changed")
            deltas = {
                name: int(after_counts[name]) - int(before_counts[name])
                for name in before_names
            }
            trials.append(
                {
                    "application_table_count": len(before_names),
                    "changed_table_deltas": {
                        name: delta for name, delta in deltas.items() if delta
                    },
                    "commit_calls": counters["commit_calls"],
                    "connection_count": counters["connection_count"],
                    "dump_equal": after["dump"] == baseline["dump"],
                    "error_class": type(caught).__name__,
                    "error_message": str(caught),
                    "event_sequence_delta": (
                        int(after["event_sequence"])
                        - int(baseline["event_sequence"])
                    ),
                    "fail_after": fail_after,
                    "interior_writes": list(interior_writes),
                    "positive_control_commit_calls": positive_commit_calls,
                    "positive_control_commit_connections": positive_commit_connections,
                    "positive_control_commit_execute_nonempty": (
                        positive_commit_execute_calls > 0
                    ),
                    "positive_control_rollback_calls": positive_rollback_calls,
                    "positive_control_rollback_connections": positive_rollback_connections,
                    "positive_control_rollback_execute_nonempty": (
                        positive_rollback_execute_calls > 0
                    ),
                    "rollback_calls": counters["rollback_calls"],
                    "sha256_equal": after["sha256"] == baseline["sha256"],
                    "successful_commit_calls": counters["successful_commit_calls"],
                    "table_deltas": deltas,
                }
            )
    return {"W09": _compact({"trials": trials})}


def _measure_handle_after(root: Path) -> dict[str, str]:
    trials: list[dict[str, object]] = []
    for target_commit in (1, 2):
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            database = Path(temporary) / f"handle-after-{target_commit}.db"
            source = _Source()
            system = System(database, candidate_source=source)
            system.register_operation(
                _PARTITION,
                _OPERATION,
                policy=CompilePolicy(2, 2, 0),
            )
            names, before = _table_counts(database)
            state = _CommitState()
            returned: object | None = None
            caught: Exception | None = None
            uuid_base = 20 if target_commit == 1 else 30
            with (
                mock.patch.object(store_module.sqlite3, "connect", _spy_connect(state)),
                mock.patch.object(
                    system_module.uuid,
                    "uuid4",
                    side_effect=[
                        uuid.UUID(int=uuid_base + offset) for offset in (1, 2, 3)
                    ],
                ),
            ):
                _positive_control(system, state)
                state.arm("after", fail_on_commit=target_commit)
                try:
                    returned = system.handle(_PARTITION, _OPERATION, {"k": 5})
                except Exception as error:
                    caught = error
            if caught is None:
                raise AssertionError(
                    f"handle commit-after injection {target_commit} did not raise"
                )
            after_names, after = _table_counts(database)
            if after_names != names:
                raise AssertionError("application table set changed during handle trial")
            proposals, _ = _stored_submission(database)
            deltas = {name: after[name] - before[name] for name in names}
            trials.append(
                {
                    "application_table_count": len(names),
                    "caller_error_class": type(caught).__name__,
                    "caller_error_message": str(caught),
                    "caller_outcome": returned,
                    "changed_table_deltas": {
                        name: delta for name, delta in deltas.items() if delta
                    },
                    "commit_calls": state.commit_calls,
                    "durable_commit_calls": state.durable_commit_calls,
                    "positive_control_commit_calls": state.positive_control_commit_calls,
                    "request_rows": _request_rows(database),
                    "rollback_calls": state.rollback_calls,
                    "source_calls": len(source.calls),
                    "stored_proposal_ids": proposals,
                    "table_deltas": deltas,
                    "target_commit": target_commit,
                }
            )
    return {"W10": _compact({"trials": trials})}


def _measure_non_submission_writer(root: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        database = Path(temporary) / "register-after.db"
        system = System(database)
        names, before = _table_counts(database)
        state = _CommitState()
        returned: int | None = None
        caught: Exception | None = None
        with mock.patch.object(store_module.sqlite3, "connect", _spy_connect(state)):
            _positive_control(system, state)
            state.arm("after")
            try:
                returned = system.register_operation(
                    "tenant_writer",
                    "write_1",
                    policy=CompilePolicy(2, 2, 0),
                )
            except Exception as error:
                caught = error
        if caught is None:
            raise AssertionError("register_operation commit-after injection did not raise")
        after_names, after = _table_counts(database)
        if after_names != names:
            raise AssertionError("application table set changed during writer trial")
        deltas = {name: after[name] - before[name] for name in names}
        public_operations = system.operations("tenant_writer")
        with closing(_REAL_CONNECT(database)) as connection:
            event_rows = [
                {"kind": str(row[0]), "subject_id": str(row[1])}
                for row in connection.execute(
                    "SELECT kind, subject_id FROM events ORDER BY sequence"
                )
            ]
        return {
            "W11": _compact(
                {
                    "application_table_count": len(names),
                    "caller_error_class": type(caught).__name__,
                    "caller_error_message": str(caught),
                    "caller_revision": returned,
                    "changed_table_deltas": {
                        name: delta for name, delta in deltas.items() if delta
                    },
                    "commit_calls": state.commit_calls,
                    "durable_commit_calls": state.durable_commit_calls,
                    "positive_control_commit_calls": state.positive_control_commit_calls,
                    "public_operation_count": len(public_operations),
                    "public_operation_names": [
                        str(operation["name"]) for operation in public_operations
                    ],
                    "public_operation_revisions": [
                        int(operation["revision"]) for operation in public_operations
                    ],
                    "rollback_calls": state.rollback_calls,
                    "stored_events": event_rows,
                    "table_deltas": deltas,
                }
            )
        }


def _direct_timing_trial(root: Path, mode: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        database = Path(temporary) / f"direct-{mode}.db"
        system = System(database, clock_us=lambda: 1_700_000_000_000_000)
        system.register_operation(
            _PARTITION,
            _OPERATION,
            policy=CompilePolicy(2, 2, 0),
        )
        names, before = _table_counts(database)
        state = _CommitState()
        returned: str | None = None
        caught: Exception | None = None
        with (
            mock.patch.object(store_module.sqlite3, "connect", _spy_connect(state)),
            mock.patch.object(
                system_module.uuid,
                "uuid4",
                side_effect=[uuid.UUID(int=41), uuid.UUID(int=42)],
            ),
        ):
            _positive_control(system, state)
            state.arm(mode)
            try:
                returned = system.submit_proposal(
                    _PARTITION,
                    _OPERATION,
                    {"k": 6},
                    candidate=Candidate(
                        output={"v": 60},
                        provenance={"model": "timing"},
                    ),
                )
            except Exception as error:
                caught = error
        if caught is None:
            raise AssertionError(f"commit-{mode}-durability injection did not raise")
        after_names, after = _table_counts(database)
        if after_names != names:
            raise AssertionError("application table set changed during timing trial")
        pending = system.proposals(_PARTITION, status="pending")
        proposals, requests = _stored_submission(database)
        deltas = {name: after[name] - before[name] for name in names}
        return {
            "application_table_count": len(names),
            "caller_proposal_id": returned,
            "caller_surface": _exception_surface(caught),
            "changed_table_deltas": {
                name: delta for name, delta in deltas.items() if delta
            },
            "commit_calls": state.commit_calls,
            "durable_commit_calls": state.durable_commit_calls,
            "pending_count": len(pending),
            "pending_ids": [str(row["id"]) for row in pending],
            "positive_control_commit_calls": state.positive_control_commit_calls,
            "rollback_calls": state.rollback_calls,
            "stored_proposal_ids": proposals,
            "stored_request_bindings": requests,
            "table_deltas": deltas,
        }


def _measure_timing_separation(root: Path) -> dict[str, str]:
    before = _direct_timing_trial(root, "before")
    after = _direct_timing_trial(root, "after")
    caller_surface = before.pop("caller_surface")
    after_surface = after.pop("caller_surface")
    return {
        "W12": _compact(
            {
                "after_durability": after,
                "before_durability": before,
                "caller_proposal_ids_equal": (
                    before["caller_proposal_id"] == after["caller_proposal_id"]
                ),
                "caller_surfaces_equal": caller_surface == after_surface,
                "post_failure_pending_counts": {
                    "after": after["pending_count"],
                    "before": before["pending_count"],
                },
                "post_failure_read_separates": (
                    before["pending_count"] != after["pending_count"]
                ),
                "shared_caller_surface": caller_surface,
            }
        )
    }


def observations() -> dict[str, str]:
    scratch = Path(".scratch")
    scratch.mkdir(exist_ok=True)
    measured = _measure_direct_after(scratch)
    measured.update(_measure_source_after(scratch))
    measured.update(_measure_control(scratch))
    measured.update(_measure_interior_failures(scratch))
    measured.update(_measure_handle_after(scratch))
    measured.update(_measure_non_submission_writer(scratch))
    measured.update(_measure_timing_separation(scratch))
    return measured


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row", choices=tuple(f"W{index:02d}" for index in range(1, 13)))
    arguments = parser.parse_args()
    measured = observations()
    selected = measured if arguments.row is None else {arguments.row: measured[arguments.row]}
    print(json.dumps(selected, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
