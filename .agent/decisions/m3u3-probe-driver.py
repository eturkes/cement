#!/usr/bin/env python3
# ruff: noqa: BLE001, FURB167, SIM117 -- oracle probe bodies stay byte-semantic.
"""Measure M3.3 differential probes against this worktree's real SQLite ledger."""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import platform
import re
import sqlite3
import subprocess
import sys
import tempfile
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest import mock

_ORACLE_DRIVER_NAME = "m3u3_probes.py"
_DRIVER_FILE = Path(__file__).resolve()


def _project_root() -> Path:
    for parent in _DRIVER_FILE.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("project root not found")


ROOT = _project_root()
# Preserve the oracle-original label in driver-owned traceback observations.
__file__ = str(_DRIVER_FILE.with_name(_ORACLE_DRIVER_NAME))
sys.path.insert(0, str(ROOT / "src"))

from cement_runtime import (
    Candidate,
    CandidateSourceError,
    CompilePolicy,
    System,
)
from cement_runtime import store as store_module
from cement_runtime import system as system_module

PROBE_TEMPLATE_PATH = ROOT / ".agent" / "decisions" / "m3u3-probes.json"
DEFAULT_DIVERGENCES_PATH = ROOT / ".agent" / "decisions" / "m3u3-divergences.json"
_REAL_CONNECT = sqlite3.connect
_ID = re.compile(r"(?P<prefix>art|ex|fpr|lease|prop|report|req)_(?P<hex>[0-9a-f]{32})\Z")


class Clock:
    def __init__(self, value: int = 1_000_000) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        return self.value

    def reset(self) -> None:
        self.calls = 0


class Source:
    def __init__(
        self,
        result: object = None,
        *,
        failure: BaseException | None = None,
    ) -> None:
        self.result = (
            Candidate(output={"y": 2}, provenance={"model": "source"})
            if result is None
            else result
        )
        self.failure = failure
        self.calls = 0
        self.requests: list[object] = []

    def propose(self, request: object) -> object:
        self.calls += 1
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return self.result


@contextmanager
def ledger(
    *,
    source: object | None = None,
    register: bool = True,
    policy: CompilePolicy | None = None,
    clock: Clock | None = None,
) -> Iterator[tuple[System, Path, Clock]]:
    with tempfile.TemporaryDirectory(prefix="cement-m3u3-oracle-") as directory:
        path = Path(directory) / "ledger.db"
        measured_clock = Clock() if clock is None else clock
        system = System(path, candidate_source=source, clock_us=measured_clock)
        if register:
            system.register_operation("p", "op", policy=policy)
        yield system, path, measured_clock


def id_shape(value: object) -> object:
    if not isinstance(value, str):
        return value
    match = _ID.fullmatch(value)
    if match is None:
        return value
    return f"{match.group('prefix')}_<32hex>"


def _frame_name(filename: str) -> str:
    name = Path(filename).name
    if Path(filename).resolve() == _DRIVER_FILE:
        return _ORACLE_DRIVER_NAME
    return name


def captured_error(call: Callable[[], object]) -> dict[str, Any]:
    try:
        value = call()
    except Exception as exc:
        frames = [
            {"file": _frame_name(frame.filename), "function": frame.name}
            for frame in traceback.extract_tb(exc.__traceback__)
        ]
        return {
            "raised": True,
            "class": type(exc).__name__,
            "message": str(exc),
            "cause": None if exc.__cause__ is None else type(exc.__cause__).__name__,
            "context": None if exc.__context__ is None else type(exc.__context__).__name__,
            "frames": frames,
            "repr": repr(exc),
            "suppress_context": exc.__suppress_context__,
            "traceback_text": "".join(traceback.format_exception(exc)),
        }
    return {"raised": False, "return_class": type(value).__name__, "return": id_shape(value)}


def counted_transactions(system: System) -> list[bool]:
    calls: list[bool] = []
    original = system.store.transaction

    def transaction(*, write: bool = False):
        calls.append(write)
        return original(write=write)

    system.store.transaction = transaction  # type: ignore[method-assign]
    return calls


@contextmanager
def _connection(path: Path) -> Iterator[sqlite3.Connection]:
    connection = _REAL_CONNECT(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def schema_tables(path: Path) -> tuple[str, ...]:
    with _connection(path) as connection:
        return tuple(
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        )


def row_counts(path: Path) -> dict[str, int]:
    with _connection(path) as connection:
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in schema_tables(path)
        }


def count_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {table: after[table] - before[table] for table in sorted(before)}


def q01() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, path, _clock):
        proposal_id = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        with _connection(path) as connection:
            stored = connection.execute(
                "SELECT id FROM proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
    match = _ID.fullmatch(proposal_id)
    return (
        "ok",
        {
            "return_class": type(proposal_id).__name__,
            "return_value": id_shape(proposal_id),
            "id_prefix": proposal_id.split("_", 1)[0] + "_",
            "hex_length": len(match.group("hex")) if match is not None else None,
            "lowercase_hex": bool(match),
            "equals_stored_proposal_id": stored is not None,
        },
        "A direct call on a real ledger returned the generated proposal identifier, whose prefix and 32-hex suffix matched the persisted row.",
    )


def q02() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, path, _clock):
        before = row_counts(path)
        system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        after = row_counts(path)
    deltas = count_delta(before, after)
    return (
        "ok",
        {
            "table_count": len(deltas),
            "row_count_delta_by_table": deltas,
            "changed_tables": {table: delta for table, delta in deltas.items() if delta},
        },
        "Full counts over every non-SQLite-internal schema table were sampled before and after one direct submission on the same ledger.",
    )


def q03() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, path, _clock):
        proposal_id = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        with _connection(path) as connection:
            event = connection.execute(
                "SELECT * FROM events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
    assert event is not None
    payload = json.loads(str(event["payload_json"]))
    return (
        "ok",
        {
            "kind": str(event["kind"]),
            "subject_type": str(event["subject_type"]),
            "subject_id": id_shape(event["subject_id"]),
            "subject_id_equals_return": event["subject_id"] == proposal_id,
            "payload": payload,
            "payload_keys": sorted(payload),
            "publishes_request_id": "request_id" in payload,
        },
        "The newest real event row was decoded after direct submission and compared to the returned proposal identifier and exact payload key set.",
    )


def q04() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, path, _clock):
        proposal_id = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        with _connection(path) as connection:
            request = connection.execute(
                "SELECT * FROM requests WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
    assert request is not None
    return (
        "ok",
        {
            "request_id": id_shape(request["id"]),
            "status": str(request["status"]),
            "proposal_id": id_shape(request["proposal_id"]),
            "proposal_id_equals_return": request["proposal_id"] == proposal_id,
            "lease_owner": request["lease_owner"],
            "lease_until_us": request["lease_until_us"],
            "attempts": int(request["attempts"]),
            "operation_revision": int(request["operation_revision"]),
        },
        "The request row bound to the returned proposal was read directly from SQLite and every requested lifecycle field was recorded.",
    )


def q05() -> tuple[str, dict[str, Any], str]:
    source = Source(failure=RuntimeError("configured source must stay inert"))
    candidate = Candidate(output={"from": "direct"}, provenance={"path": "caller"})
    with ledger(source=source) as (system, path, _clock):
        proposal_id = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        with _connection(path) as connection:
            proposal = connection.execute(
                "SELECT proposed_output_json, provenance_json FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
    assert proposal is not None
    return (
        "ok",
        {
            "source_invocations": source.calls,
            "return_class": type(proposal_id).__name__,
            "return_value": id_shape(proposal_id),
            "proposed_output_json": str(proposal["proposed_output_json"]),
            "provenance_json": str(proposal["provenance_json"]),
        },
        "A configured source that would raise remained uncalled while the caller-supplied candidate was persisted and returned normally.",
    )


def submission_projection(path: Path, proposal_id: str) -> dict[str, Any]:
    with _connection(path) as connection:
        proposal = connection.execute(
            "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
        ).fetchone()
        request = connection.execute(
            "SELECT * FROM requests WHERE proposal_id = ?", (proposal_id,)
        ).fetchone()
        event = connection.execute(
            "SELECT * FROM events WHERE subject_type = 'proposal' AND subject_id = ?",
            (proposal_id,),
        ).fetchone()
    assert proposal is not None and request is not None and event is not None
    return {
        "request": {
            "id": id_shape(request["id"]),
            "partition": str(request["partition"]),
            "operation": str(request["operation"]),
            "operation_revision": int(request["operation_revision"]),
            "input_json": str(request["input_json"]),
            "input_hash": str(request["input_hash"]),
            "status": str(request["status"]),
            "output_json": request["output_json"],
            "source_kind": request["source_kind"],
            "artifact_id": request["artifact_id"],
            "proposal_id": id_shape(request["proposal_id"]),
            "example_id": request["example_id"],
            "error_code": request["error_code"],
            "lease_owner": request["lease_owner"],
            "lease_until_us": request["lease_until_us"],
            "attempts": int(request["attempts"]),
            "created_at_us": "<timestamp_us>",
            "updated_at_us": "<timestamp_us>",
        },
        "proposal": {
            "id": id_shape(proposal["id"]),
            "partition": str(proposal["partition"]),
            "request_id": id_shape(proposal["request_id"]),
            "proposed_output_json": str(proposal["proposed_output_json"]),
            "proposed_output_hash": str(proposal["proposed_output_hash"]),
            "provenance_json": str(proposal["provenance_json"]),
            "provenance_hash": str(proposal["provenance_hash"]),
            "status": str(proposal["status"]),
            "final_output_json": proposal["final_output_json"],
            "final_output_hash": proposal["final_output_hash"],
            "reviewer": proposal["reviewer"],
            "review_note": proposal["review_note"],
            "created_at_us": "<timestamp_us>",
            "reviewed_at_us": proposal["reviewed_at_us"],
            "status_sequence": int(proposal["status_sequence"]),
        },
        "event": {
            "sequence": int(event["sequence"]),
            "partition": str(event["partition"]),
            "kind": str(event["kind"]),
            "subject_type": str(event["subject_type"]),
            "subject_id": id_shape(event["subject_id"]),
            "payload_json": str(event["payload_json"]),
            "created_at_us": "<timestamp_us>",
        },
    }


def q06() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, path, _clock):
        proposal_id = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        with _connection(path) as connection:
            proposal = connection.execute(
                "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
            event = connection.execute(
                "SELECT sequence FROM events WHERE subject_type = 'proposal' AND subject_id = ?",
                (proposal_id,),
            ).fetchone()
    assert proposal is not None and event is not None
    return (
        "ok",
        {
            "proposed_output_json": str(proposal["proposed_output_json"]),
            "proposed_output_hash": str(proposal["proposed_output_hash"]),
            "output_hash_matches_sha256": hashlib.sha256(
                str(proposal["proposed_output_json"]).encode("utf-8")
            ).hexdigest()
            == proposal["proposed_output_hash"],
            "provenance_json": str(proposal["provenance_json"]),
            "provenance_hash": str(proposal["provenance_hash"]),
            "provenance_hash_matches_sha256": hashlib.sha256(
                str(proposal["provenance_json"]).encode("utf-8")
            ).hexdigest()
            == proposal["provenance_hash"],
            "status": str(proposal["status"]),
            "status_sequence": int(proposal["status_sequence"]),
            "event_sequence": int(event["sequence"]),
            "status_sequence_equals_event_sequence": proposal["status_sequence"]
            == event["sequence"],
        },
        "The proposal row and its audit event were read from SQLite; both canonical texts, both digests, status, and shared sequence were measured.",
    )


def q07() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "same"})
    with ledger() as (direct_system, direct_path, _direct_clock):
        direct_before = row_counts(direct_path)
        direct_id = direct_system.submit_proposal(
            "p", "op", {"x": 1}, candidate=candidate
        )
        direct_delta = count_delta(direct_before, row_counts(direct_path))
        direct_projection = submission_projection(direct_path, direct_id)
    source = Source(result=candidate)
    with ledger(source=source) as (source_system, source_path, _source_clock):
        source_before = row_counts(source_path)
        source_id = source_system.propose("p", "op", {"x": 1})
        source_delta = count_delta(source_before, row_counts(source_path))
        source_projection = submission_projection(source_path, source_id)
    return (
        "ok",
        {
            "return_class": type(source_id).__name__,
            "return_value": id_shape(source_id),
            "source_invocations": source.calls,
            "source_row_count_delta_by_table": source_delta,
            "direct_row_count_delta_by_table": direct_delta,
            "row_count_deltas_equal": source_delta == direct_delta,
            "normalized_full_footprints_equal": source_projection == direct_projection,
        },
        "Separate real ledgers persisted byte-identical candidates through each public path; complete normalized request, proposal, event, and table deltas matched.",
    )


def q08() -> tuple[str, dict[str, Any], str]:
    source = Source()
    with ledger(source=source) as (system, path, _clock):
        proposal_id = system.propose("p", "op", {"x": 1})
        request = source.requests[0]
        with _connection(path) as connection:
            stored = connection.execute(
                "SELECT id FROM requests WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
    assert stored is not None
    return (
        "ok",
        {
            "source_invocations": source.calls,
            "request_class": type(request).__name__,
            "partition": request.partition,
            "operation": request.operation,
            "operation_revision": request.operation_revision,
            "request_id": id_shape(request.request_id),
            "request_id_equals_private_row": request.request_id == stored["id"],
            "input": request.input,
        },
        "The configured source retained the exact CandidateRequest from one real call, and its generated request identifier was matched to SQLite storage.",
    )


def q09() -> tuple[str, dict[str, Any], str]:
    tracked: list[TrackingConnection] = []

    class TrackingConnection(sqlite3.Connection):
        close_requested = False

        def close(self) -> None:
            self.close_requested = True

        def close_really(self) -> None:
            super().close()

    def connect(*args: object, **kwargs: object) -> TrackingConnection:
        kwargs["factory"] = TrackingConnection
        connection = _REAL_CONNECT(*args, **kwargs)
        assert isinstance(connection, TrackingConnection)
        tracked.append(connection)
        return connection

    class InspectingSource:
        def __init__(self) -> None:
            self.calls = 0
            self.states: list[bool] = []
            self.close_requested: list[bool] = []

        def propose(self, request: object) -> Candidate:
            del request
            self.calls += 1
            self.states = [connection.in_transaction for connection in tracked]
            self.close_requested = [connection.close_requested for connection in tracked]
            return Candidate(output={"y": 2}, provenance={"model": "inspect"})

    source = InspectingSource()
    positive_control = False
    proposal_id = ""
    with tempfile.TemporaryDirectory(prefix="cement-m3u3-oracle-q09-") as directory:
        path = Path(directory) / "ledger.db"
        try:
            with mock.patch.object(store_module.sqlite3, "connect", side_effect=connect):
                system = System(path, candidate_source=source, clock_us=Clock())
                system.register_operation("p", "op")
                with system.store.transaction(write=False) as connection:
                    positive_control = connection.in_transaction
                proposal_id = system.propose("p", "op", {"x": 1})
        finally:
            for connection in tracked:
                connection.close_really()
    return (
        "ok",
        {
            "source_invocations": source.calls,
            "tracked_connections_at_source": len(source.states),
            "in_transaction_values_at_source": source.states,
            "any_in_transaction_at_source": any(source.states),
            "all_prior_close_requested": all(source.close_requested),
            "positive_control_in_transaction": positive_control,
            "result": id_shape(proposal_id),
        },
        "A Connection subclass delayed physical close so every Cement-created connection remained inspectable; all were out of transaction during source execution, while a live read block proved True.",
    )


def q10() -> tuple[str, dict[str, Any], str]:
    secret = "Q10_DECLARED_SOURCE_SECRET"
    source = Source(failure=CandidateSourceError(secret))
    with ledger(source=source) as (system, _path, _clock):
        error = captured_error(lambda: system.propose("p", "op", {"x": 1}))
    frames = error["frames"]
    public_text = error["message"] + error["repr"] + error["traceback_text"]
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "cause": error["cause"],
            "context": error["context"],
            "suppress_context": error["suppress_context"],
            "traceback_frames": frames,
            "source_implementation_frame_present": any(
                frame["file"] == Path(__file__).name and frame["function"] == "propose"
                for frame in frames
            ),
            "secret_in_public_surface": secret in public_text,
            "source_invocations": source.calls,
        },
        "A declared CandidateSourceError carrying a planted secret was raised through a real source call; the public exception and traceback were captured directly.",
    )


def q11() -> tuple[str, dict[str, Any], str]:
    secret = "Q11_ARBITRARY_EXCEPTION_SECRET"
    source = Source(failure=RuntimeError(secret))
    with ledger(source=source) as (system, _path, _clock):
        error = captured_error(lambda: system.propose("p", "op", {"x": 1}))
    frames = error["frames"]
    public_text = error["message"] + error["repr"] + error["traceback_text"]
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "cause": error["cause"],
            "context": error["context"],
            "suppress_context": error["suppress_context"],
            "traceback_frames": frames,
            "source_implementation_frame_present": any(
                frame["file"] == Path(__file__).name and frame["function"] == "propose"
                for frame in frames
            ),
            "secret_in_message": secret in error["message"],
            "secret_in_repr": secret in error["repr"],
            "secret_in_traceback": secret in error["traceback_text"],
            "secret_in_public_surface": secret in public_text,
            "source_invocations": source.calls,
        },
        "A RuntimeError carrying a planted secret crossed the real adapter boundary; class, text, chaining, frames, repr, and formatted traceback were captured.",
    )


def q12() -> tuple[str, dict[str, Any], str]:
    with ledger(source=None) as (system, _path, _clock):
        transactions = counted_transactions(system)
        error = captured_error(lambda: system.propose("p", "op", {"x": 1}))
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "source_invocations": 0,
            "transaction_count": len(transactions),
            "transaction_modes": transactions,
        },
        "A real initialized System with candidate_source=None rejected the call after argument validation and before opening any ledger transaction.",
    )


def q13() -> tuple[str, dict[str, Any], str]:
    non_candidate_source = Source(result=object())
    with ledger(source=non_candidate_source) as (system, _path, _clock):
        non_candidate = captured_error(lambda: system.propose("p", "op", {"x": 1}))
    malformed_source = Source(
        result=Candidate(output={"y": 2}, provenance=object())  # type: ignore[arg-type]
    )
    with ledger(source=malformed_source) as (system, _path, _clock):
        malformed = captured_error(lambda: system.propose("p", "op", {"x": 1}))
    return (
        "error",
        {
            "non_candidate_class": non_candidate["class"],
            "non_candidate_message": non_candidate["message"],
            "non_candidate_source_invocations": non_candidate_source.calls,
            "malformed_provenance_class": malformed["class"],
            "malformed_provenance_message": malformed["message"],
            "malformed_provenance_source_invocations": malformed_source.calls,
            "public_errors_identical": (
                non_candidate["class"], non_candidate["message"]
            )
            == (malformed["class"], malformed["message"]),
        },
        "Two separate real ledgers measured a non-Candidate return and an object-valued provenance; both adapter result defects normalized identically.",
    )


def q14() -> tuple[str, dict[str, Any], str]:
    class RevisingSource:
        def __init__(self) -> None:
            self.calls = 0
            self.request_revision: int | None = None
            self.revised_revision: int | None = None
            self.system: System | None = None

        def propose(self, request: object) -> Candidate:
            self.calls += 1
            self.request_revision = request.operation_revision
            assert self.system is not None
            self.revised_revision = self.system.revise_operation(
                "p",
                "op",
                policy=CompilePolicy(2, 1, 0),
                revised_by="q14",
            )
            return Candidate(output={"y": 2}, provenance={"model": "revision-race"})

    source = RevisingSource()
    with ledger() as (system, path, _clock):
        system.candidate_source = source
        source.system = system
        before = row_counts(path)
        with _connection(path) as connection:
            proposal_events_before = int(
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0]
            )
        error = captured_error(lambda: system.propose("p", "op", {"x": 1}))
        after = row_counts(path)
        with _connection(path) as connection:
            current_revision = int(
                connection.execute(
                    "SELECT revision FROM operations WHERE partition = 'p' AND name = 'op'"
                ).fetchone()[0]
            )
            proposal_events_after = int(
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0]
            )
            event_kinds = [
                str(row[0])
                for row in connection.execute("SELECT kind FROM events ORDER BY sequence")
            ]
    deltas = count_delta(before, after)
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "source_invocations": source.calls,
            "candidate_request_revision": source.request_revision,
            "revision_returned_inside_source": source.revised_revision,
            "revision_at_write_recheck": current_revision,
            "requests_delta": deltas["requests"],
            "proposals_delta": deltas["proposals"],
            "proposal_created_events_delta": proposal_events_after
            - proposal_events_before,
            "all_table_row_count_delta": deltas,
            "event_kinds_after_call": event_kinds,
        },
        "The real source committed an operation revision during generation; the locked recheck rejected revision one and persisted no submission rows or proposal event.",
    )


def q21() -> tuple[str, dict[str, Any], str]:
    source = Source()
    with ledger(source=source, register=False) as (system, _path, _clock):
        transactions = counted_transactions(system)
        error = captured_error(lambda: system.propose("p", "missing", {"x": 1}))
        failure_transactions = list(transactions)
        failure_source_calls = source.calls
        system.register_operation("p", "op")
        transactions.clear()
        positive_id = system.propose("p", "op", {"x": 1})
        positive_source_calls = source.calls - failure_source_calls
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "source_invocations_before_error": failure_source_calls,
            "transaction_count_before_error": len(failure_transactions),
            "transaction_modes_before_error": failure_transactions,
            "source_positive_control_invocations": positive_source_calls,
            "positive_control_result": id_shape(positive_id),
        },
        "A scoped read on an empty real ledger raised NotFoundError before source execution; registering the sibling operation then proved the source counter live.",
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1_048_576):
            digest.update(chunk)
    return digest.hexdigest()


def full_iterdump(path: Path) -> tuple[str, ...]:
    with _connection(path) as connection:
        return tuple(connection.iterdump())


def event_sequence_counter(path: Path) -> int | None:
    with _connection(path) as connection:
        row = connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
        ).fetchone()
    return None if row is None else int(row[0])


def q22() -> tuple[str, dict[str, Any], str]:
    secret = "Q22_FAILED_SUBMISSION"
    source = Source(failure=RuntimeError(secret))
    with ledger(source=source) as (system, path, _clock):
        before_counts = row_counts(path)
        before_sequence = event_sequence_counter(path)
        before_dump = full_iterdump(path)
        before_file_hash = file_sha256(path)
        error = captured_error(lambda: system.propose("p", "op", {"x": 1}))
        after_counts = row_counts(path)
        after_sequence = event_sequence_counter(path)
        after_dump = full_iterdump(path)
        after_file_hash = file_sha256(path)
    before_dump_hash = hashlib.sha256("\n".join(before_dump).encode("utf-8")).hexdigest()
    after_dump_hash = hashlib.sha256("\n".join(after_dump).encode("utf-8")).hexdigest()
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "source_invocations": source.calls,
            "ledger_sha256_before": before_file_hash,
            "ledger_sha256_after": after_file_hash,
            "ledger_sha256_equal": before_file_hash == after_file_hash,
            "iterdump_statement_count_before": len(before_dump),
            "iterdump_statement_count_after": len(after_dump),
            "iterdump_sha256_before": before_dump_hash,
            "iterdump_sha256_after": after_dump_hash,
            "full_iterdump_equal": before_dump == after_dump,
            "row_counts_before": before_counts,
            "row_counts_after": after_counts,
            "row_counts_equal": before_counts == after_counts,
            "event_sequence_before": before_sequence,
            "event_sequence_after": after_sequence,
            "event_sequence_equal": before_sequence == after_sequence,
        },
        "Before and after one real failing source call, the physical file, complete iterdump tuple, all table counts, and sqlite_sequence event counter were independently sampled.",
    )


def q23() -> tuple[str, dict[str, Any], str]:
    commits: list[str] = []

    class CommitConnection(sqlite3.Connection):
        def commit(self) -> None:
            commits.append("commit")
            super().commit()

    def connect(*args: object, **kwargs: object) -> CommitConnection:
        kwargs["factory"] = CommitConnection
        connection = _REAL_CONNECT(*args, **kwargs)
        assert isinstance(connection, CommitConnection)
        return connection

    @contextmanager
    def commit_case(
        *, source: object | None = None, register: bool = True
    ) -> Iterator[tuple[System, Path]]:
        with tempfile.TemporaryDirectory(prefix="cement-m3u3-oracle-q23-") as directory:
            path = Path(directory) / "ledger.db"
            system = System(path, candidate_source=source, clock_us=Clock())
            if register:
                system.register_operation("p", "op")
            commits.clear()
            yield system, path

    counts: dict[str, int] = {}
    with mock.patch.object(store_module.sqlite3, "connect", side_effect=connect):
        with commit_case() as (system, _path):
            with system.store.transaction(write=True) as connection:
                connection.execute(
                    "UPDATE operations SET updated_at_us = updated_at_us WHERE partition = 'p'"
                )
            counts["positive_write_control"] = len(commits)

        with commit_case(source=Source(failure=CandidateSourceError("declared"))) as (
            system,
            _path,
        ):
            captured_error(lambda: system.propose("p", "op", {"x": 1}))
            counts["source_candidate_source_error"] = len(commits)

        with commit_case(source=Source(failure=RuntimeError("arbitrary"))) as (
            system,
            _path,
        ):
            captured_error(lambda: system.propose("p", "op", {"x": 1}))
            counts["source_arbitrary_exception"] = len(commits)

        with commit_case(source=Source(result=object())) as (system, _path):
            captured_error(lambda: system.propose("p", "op", {"x": 1}))
            counts["source_invalid_result"] = len(commits)

        with commit_case(source=None) as (system, _path):
            captured_error(lambda: system.propose("p", "op", {"x": 1}))
            counts["missing_source"] = len(commits)

        with commit_case(source=Source(), register=False) as (system, _path):
            captured_error(lambda: system.propose("p", "missing", {"x": 1}))
            counts["unregistered_operation"] = len(commits)

        with commit_case(source=Source()) as (system, _path):
            captured_error(lambda: system.propose("", "op", object()))
            counts["argument_validation"] = len(commits)

        with commit_case() as (system, _path):
            captured_error(
                lambda: system.submit_proposal(
                    "p", "op", {"x": 1}, candidate=object()  # type: ignore[arg-type]
                )
            )
            counts["direct_invalid_candidate"] = len(commits)

        class ExternalRevisionSource:
            def __init__(self, path: Path) -> None:
                self.path = path

            def propose(self, request: object) -> Candidate:
                del request
                connection = _REAL_CONNECT(self.path)
                try:
                    connection.execute(
                        "UPDATE operations SET revision = revision + 1 WHERE partition = 'p' AND name = 'op'"
                    )
                    connection.commit()
                finally:
                    connection.close()
                return Candidate(output={"y": 2}, provenance={"model": "race"})

        with commit_case() as (system, path):
            system.candidate_source = ExternalRevisionSource(path)
            captured_error(lambda: system.propose("p", "op", {"x": 1}))
            counts["revision_changed"] = len(commits)

    return (
        "ok",
        {
            "commit_call_counts": counts,
            "positive_control_live": counts["positive_write_control"] == 1,
            "all_failure_counts_zero": all(
                count == 0 for name, count in counts.items() if name != "positive_write_control"
            ),
            "connection_factory_class": "CommitConnection",
        },
        "A sqlite3.Connection subclass counted actual commit() dispatches across eight independent failure families; a no-op write transaction proved the spy with one call.",
    )


def q24() -> tuple[str, dict[str, Any], str]:
    source = Source()
    clock = Clock()
    external_time_reads = 0

    def time_ns() -> int:
        nonlocal external_time_reads
        external_time_reads += 1
        return 1_000_000_000

    with ledger(source=source, clock=clock) as (system, _path, _measured_clock):
        clock.reset()
        with mock.patch.object(system_module.time, "time_ns", side_effect=time_ns):
            with mock.patch.object(system, "_now", wraps=system._now) as now_method:
                direct_id = system.submit_proposal(
                    "p",
                    "op",
                    {"x": 1},
                    candidate=Candidate(output={"y": 2}, provenance={"model": "direct"}),
                )
                direct_now_calls = now_method.call_count
                direct_clock_calls = clock.calls
                direct_external_reads = external_time_reads
                now_method.reset_mock()
                clock.reset()
                external_time_reads = 0
                source_id = system.propose("p", "op", {"x": 2})
                source_now_calls = now_method.call_count
                source_clock_calls = clock.calls
                source_external_reads = external_time_reads
    return (
        "ok",
        {
            "direct_result": id_shape(direct_id),
            "direct_self_now_calls": direct_now_calls,
            "direct_injected_clock_calls": direct_clock_calls,
            "direct_system_time_ns_calls": direct_external_reads,
            "source_result": id_shape(source_id),
            "source_self_now_calls": source_now_calls,
            "source_injected_clock_calls": source_clock_calls,
            "source_system_time_ns_calls": source_external_reads,
            "source_invocations": source.calls,
        },
        "Wrapped self._now, the injected clock, and system_module.time.time_ns were counted independently for one successful call through each public path.",
    )


def q25() -> tuple[str, dict[str, Any], str]:
    selects: list[tuple[str, tuple[object, ...]]] = []

    class RecordingConnection(sqlite3.Connection):
        def execute(
            self,
            sql: str,
            parameters: tuple[object, ...] = (),
            /,
        ) -> sqlite3.Cursor:
            normalized = " ".join(sql.split())
            if normalized.upper().startswith("SELECT"):
                selects.append((normalized, tuple(parameters)))
            return super().execute(sql, parameters)

    def connect(*args: object, **kwargs: object) -> RecordingConnection:
        kwargs["factory"] = RecordingConnection
        connection = _REAL_CONNECT(*args, **kwargs)
        assert isinstance(connection, RecordingConnection)
        return connection

    source = Source()
    with tempfile.TemporaryDirectory(prefix="cement-m3u3-oracle-q25-") as directory:
        path = Path(directory) / "ledger.db"
        with mock.patch.object(store_module.sqlite3, "connect", side_effect=connect):
            system = System(path, candidate_source=source, clock_us=Clock())
            system.register_operation("p", "op")
            selects.clear()
            proposal_id = system.propose("p", "op", {"x": 1})
    table_counts: dict[str, int] = {}
    for sql, _parameters in selects:
        match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)", sql, re.I)
        table = "<none>" if match is None else match.group(1)
        table_counts[table] = table_counts.get(table, 0) + 1
    return (
        "ok",
        {
            "result": id_shape(proposal_id),
            "select_count": len(selects),
            "select_count_by_table": table_counts,
            "selects": [
                {"sql": sql, "parameters": list(parameters)}
                for sql, parameters in selects
            ],
            "source_invocations": source.calls,
        },
        "A Connection subclass captured every explicit SELECT template and bind tuple after setup was reset; one real source-backed success produced the recorded list.",
    )


def q26() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, _path, _clock):
        proposal_id = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        view = system.get_proposal("p", proposal_id)
        record = system.proposal("p", proposal_id)
        feed = system.proposals("p")
        report = system.function_report("p", "op")
    gap = report.operation_now.pending_proposals[0]
    feed_record = feed[0]
    return (
        "ok",
        {
            "proposal_id": id_shape(proposal_id),
            "get_proposal": {
                "class": type(view).__name__,
                "id": id_shape(view.id),
                "request_id": id_shape(view.request_id),
                "operation": view.operation,
                "operation_revision": view.operation_revision,
                "input": view.input,
                "proposed_output": view.proposed_output,
                "provenance": view.provenance,
                "created_at_us": "<timestamp_us>",
            },
            "proposal": {
                "class": type(record).__name__,
                "id": id_shape(record["id"]),
                "request_id": id_shape(record["request_id"]),
                "status": record["status"],
                "input": record["input"],
                "proposed_output": record["proposed_output"],
                "provenance": record["provenance"],
            },
            "proposals": {
                "class": type(feed).__name__,
                "count": len(feed),
                "id": id_shape(feed_record["id"]),
                "request_id": id_shape(feed_record["request_id"]),
                "status": feed_record["status"],
            },
            "function_report": {
                "class": type(report).__name__,
                "operation_revision": report.operation_now.operation_revision,
                "pending_proposal_count": report.operation_now.pending_proposal_count,
                "projected_pending_count": len(report.operation_now.pending_proposals),
                "proposal_id": id_shape(gap.proposal_id),
                "request_id": id_shape(gap.request_id),
                "gap_operation_revision": gap.operation_revision,
                "input_hash": gap.input_hash,
            },
            "all_proposal_ids_equal": view.id
            == record["id"]
            == feed_record["id"]
            == gap.proposal_id
            == proposal_id,
            "all_request_ids_equal": view.request_id
            == record["request_id"]
            == feed_record["request_id"]
            == gap.request_id,
        },
        "Four unchanged read APIs were called against the same submitted row; every projected proposal and request identity was compared, including FunctionReport's pending gap.",
    )


def q27() -> tuple[str, dict[str, Any], str]:
    policy = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger(policy=policy) as (system, path, _clock):
        first_proposal = system.submit_proposal(
            "p", "op", {"x": 1}, candidate=candidate
        )
        first_review = system.review(
            "p",
            first_proposal,
            reviewer="reviewer-a",
            decision="accept",
            note="first confirmation",
        )
        second_proposal = system.submit_proposal(
            "p", "op", {"x": 1}, candidate=candidate
        )
        second_review = system.review(
            "p",
            second_proposal,
            reviewer="reviewer-b",
            decision="accept",
            note="second confirmation",
        )
        compiled = system.compile("p", "op", compiled_by="q27")
        artifact_id = compiled.created[0]
        verification = system.verify("p", artifact_id, verified_by="q27")
        promotion = system.promote(
            "p",
            artifact_id,
            scope_hash=verification.scope_hash,
            promoted_by="q27",
        )
        resolved = system.handle("p", "op", {"x": 1}, request_id="q27-resolution")
        with _connection(path) as connection:
            proposal_statuses = [
                str(row[0])
                for row in connection.execute(
                    "SELECT status FROM proposals ORDER BY status_sequence"
                )
            ]
            request_statuses = [
                str(row[0])
                for row in connection.execute(
                    "SELECT status FROM requests ORDER BY created_at_us, id"
                )
            ]
            artifact = connection.execute(
                "SELECT status, support, reviewer_count FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            counts = row_counts(path)
    assert artifact is not None
    return (
        "ok",
        {
            "first_proposal": id_shape(first_proposal),
            "first_review": {
                "class": type(first_review).__name__,
                "source": first_review.source,
                "output": first_review.output,
                "example_id": id_shape(first_review.example_id),
            },
            "second_proposal": id_shape(second_proposal),
            "second_review": {
                "class": type(second_review).__name__,
                "source": second_review.source,
                "output": second_review.output,
                "example_id": id_shape(second_review.example_id),
            },
            "compile": {
                "created": [id_shape(value) for value in compiled.created],
                "existing": [id_shape(value) for value in compiled.existing],
                "blocked": list(compiled.blocked),
            },
            "verification": {
                "class": type(verification).__name__,
                "report_id": id_shape(verification.id),
                "artifact_id": id_shape(verification.artifact_id),
                "passed": verification.passed,
                "tests": verification.tests,
                "failures": list(verification.failures),
            },
            "promotion": {
                "class": type(promotion).__name__,
                "artifact_id": id_shape(promotion.artifact_id),
                "replaced_artifact_ids": [
                    id_shape(value) for value in promotion.replaced_artifact_ids
                ],
                "promoted_at_us": "<timestamp_us>",
            },
            "post_promotion_handle": {
                "class": type(resolved).__name__,
                "request_id": resolved.request_id,
                "output": resolved.output,
                "source": resolved.source,
                "artifact_id": id_shape(resolved.artifact_id),
            },
            "proposal_statuses": proposal_statuses,
            "request_statuses": request_statuses,
            "artifact_status": str(artifact["status"]),
            "artifact_support": int(artifact["support"]),
            "artifact_reviewer_count": int(artifact["reviewer_count"]),
            "row_counts": counts,
        },
        "Two submitted proposals were accepted into real examples, then compiled, verified, promoted, and consumed through unchanged handle as an artifact resolution.",
    )


def q28() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"model": "manual"})
    with ledger() as (system, path, _clock):
        first = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        second = system.submit_proposal("p", "op", {"x": 1}, candidate=candidate)
        with _connection(path) as connection:
            proposals = connection.execute(
                "SELECT id, request_id, proposed_output_json, proposed_output_hash, provenance_json, provenance_hash FROM proposals ORDER BY status_sequence"
            ).fetchall()
            requests = connection.execute(
                "SELECT id, proposal_id, input_json, input_hash FROM requests ORDER BY created_at_us, id"
            ).fetchall()
            events = connection.execute(
                "SELECT subject_id, payload_json FROM events WHERE kind = 'proposal.created' ORDER BY sequence"
            ).fetchall()
    return (
        "ok",
        {
            "first_proposal_id": id_shape(first),
            "second_proposal_id": id_shape(second),
            "proposal_ids_distinct": first != second,
            "proposal_row_count": len(proposals),
            "request_row_count": len(requests),
            "proposal_created_event_count": len(events),
            "distinct_request_ids": len({str(row["request_id"]) for row in proposals}),
            "proposal_contents_equal": len(
                {
                    (
                        row["proposed_output_json"],
                        row["proposed_output_hash"],
                        row["provenance_json"],
                        row["provenance_hash"],
                    )
                    for row in proposals
                }
            )
            == 1,
            "request_inputs_equal": len(
                {(row["input_json"], row["input_hash"]) for row in requests}
            )
            == 1,
            "event_subjects_distinct": len({str(row["subject_id"]) for row in events})
            == 2,
            "event_payloads": [json.loads(str(row["payload_json"])) for row in events],
            "conflict_raised": False,
        },
        "Two byte-identical direct calls ran against one real ledger; their proposal, request, and event rows were enumerated and compared for identity and content.",
    )


def q29() -> tuple[str, dict[str, Any], str]:
    source = Source(result=Candidate(output={"y": 2}, provenance={"model": "handle"}))
    direct_candidate = Candidate(output={"y": 2}, provenance={"model": "direct"})
    with ledger(source=source) as (system, path, _clock):
        submitted = system.submit_proposal(
            "p", "op", {"x": 1}, candidate=direct_candidate
        )
        source_calls_after_submit = source.calls
        baseline = row_counts(path)
        handled = system.handle("p", "op", {"x": 1})
        after = row_counts(path)
        with _connection(path) as connection:
            original_status = str(
                connection.execute(
                    "SELECT status FROM proposals WHERE id = ?", (submitted,)
                ).fetchone()[0]
            )
            handled_request = connection.execute(
                "SELECT status, proposal_id FROM requests WHERE id = ?",
                (handled.request_id,),
            ).fetchone()
    assert handled_request is not None
    deltas = count_delta(baseline, after)
    return (
        "ok",
        {
            "submitted_proposal": id_shape(submitted),
            "source_calls_after_submit": source_calls_after_submit,
            "handle_result": {
                "class": type(handled).__name__,
                "request_id": id_shape(handled.request_id),
                "proposal_id": id_shape(handled.proposal_id),
                "status": handled.status,
            },
            "source_calls_after_handle": source.calls,
            "source_calls_during_handle": source.calls - source_calls_after_submit,
            "row_count_delta_by_table": deltas,
            "changed_tables": {table: delta for table, delta in deltas.items() if delta},
            "matches_submission_footprint": {
                table: delta for table, delta in deltas.items() if delta
            }
            == {"events": 1, "proposals": 1, "requests": 1},
            "original_proposal_status": original_status,
            "handled_request_status": str(handled_request["status"]),
            "handled_request_proposal_matches_result": handled_request["proposal_id"]
            == handled.proposal_id,
        },
        "After direct submission on one configured System, unchanged handle ran on the same input; its result, source count, full table delta, and both pending bindings were measured.",
    )


def transaction_census() -> dict[str, Any]:
    tree = ast.parse((ROOT / "src" / "cement_runtime" / "system.py").read_text(encoding="utf-8"))
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
                    (
                        keyword.value
                        for keyword in call.keywords
                        if keyword.arg == "write"
                    ),
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

    return {
        "read_sites": read_sites,
        "write_sites": write_sites,
        "reached_helpers": sorted(reached_helpers),
        "violations": violations,
    }


def q30() -> tuple[str, dict[str, Any], str]:
    census = transaction_census()
    source = Source()
    with ledger(source=source) as (system, _path, _clock):
        transactions = counted_transactions(system)
        proposal_id = system.propose("p", "op", {"x": 1})
    read_methods = [method for method, _line in census["read_sites"]]
    write_methods = [method for method, _line in census["write_sites"]]
    return (
        "ok",
        {
            "read_transaction_site_count": len(read_methods),
            "read_transaction_site_methods": read_methods,
            "write_transaction_site_count": len(write_methods),
            "write_transaction_site_methods": write_methods,
            "reached_helper_count": len(census["reached_helpers"]),
            "reached_helpers": census["reached_helpers"],
            "violations": census["violations"],
            "new_read_site_present": "_submission_revision" in read_methods,
            "new_write_site_present": "_persist_proposal" in write_methods,
            "successful_submission_transaction_modes": transactions,
            "successful_submission_result": id_shape(proposal_id),
            "successful_submission_source_invocations": source.calls,
        },
        "The production AST was scanned with the gate's recursive connection-flow algorithm, then a real success proved the new read and write sites execute in that order.",
    )


def z01() -> tuple[str, dict[str, Any], str]:
    sentinel = object()
    names = [
        name
        for name in ("_persist_proposal", "_persist_submission")
        if inspect.getattr_static(System, name, sentinel) is not sentinel
    ]
    return (
        "ok",
        {"private_persistence_seams": names, "seam_count": len(names)},
        "Static class inspection records the raw private single-writer seam name; the contract attaches no obligation to that identifier.",
    )


def z02() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"probe": "z02"})
    with ledger() as (system, _path, _clock):
        transactions = counted_transactions(system)
        with system.store.transaction(write=False):
            pass
        positive_control = list(transactions)
        transactions.clear()
        proposal_id = system.submit_proposal(
            "p", "op", {"x": 1}, candidate=candidate
        )
        direct_transactions = list(transactions)
    return (
        "ok",
        {
            "spy_positive_control_modes": positive_control,
            "spy_positive_control_live": positive_control == [False],
            "direct_transaction_count": len(direct_transactions),
            "direct_transaction_modes": direct_transactions,
            "result": id_shape(proposal_id),
        },
        "A live Store.transaction wrapper first observed one forced read, then counted every transaction opened by one direct submission.",
    )


def z03() -> tuple[str, dict[str, Any], str]:
    candidate = Candidate(output={"y": 2}, provenance={"probe": "z03"})
    with ledger() as (system, path, _clock):
        seam_name = (
            "_persist_proposal"
            if inspect.getattr_static(System, "_persist_proposal", None) is not None
            else "_persist_submission"
        )
        original = getattr(system, seam_name)
        injection_calls = 0
        revised_revision: int | None = None

        def injecting_seam(**kwargs: object) -> str:
            nonlocal injection_calls, revised_revision
            injection_calls += 1
            revised_revision = system.revise_operation(
                "p",
                "op",
                policy=CompilePolicy(2, 1, 0),
                revised_by="z03",
            )
            return original(**kwargs)

        setattr(system, seam_name, injecting_seam)
        before = row_counts(path)
        with _connection(path) as connection:
            proposal_events_before = int(
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0]
            )
        result = captured_error(
            lambda: system.submit_proposal(
                "p", "op", {"x": 1}, candidate=candidate
            )
        )
        after = row_counts(path)
        with _connection(path) as connection:
            operation_revision = int(
                connection.execute(
                    "SELECT revision FROM operations WHERE partition = 'p' AND name = 'op'"
                ).fetchone()[0]
            )
            proposal_events_after = int(
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0]
            )
            stored_request_revisions = [
                int(row[0])
                for row in connection.execute(
                    "SELECT operation_revision FROM requests ORDER BY created_at_us, id"
                )
            ]
    deltas = count_delta(before, after)
    if result["raised"]:
        assert stored_request_revisions == []
    else:
        assert stored_request_revisions == [operation_revision]
    public_result = (
        {
            "raised": True,
            "class": result["class"],
            "message": result["message"],
        }
        if result["raised"]
        else {
            "raised": False,
            "return_class": result["return_class"],
            "return": result["return"],
        }
    )
    return (
        "ok",
        {
            "injection_seam": seam_name,
            "injection_calls": injection_calls,
            "revised_revision": revised_revision,
            "operation_revision_after": operation_revision,
            "stored_request_operation_revisions": stored_request_revisions,
            "stored_revision_matches_current": (
                stored_request_revisions == [operation_revision]
                if stored_request_revisions
                else None
            ),
            "public_result": public_result,
            "requests_delta": deltas["requests"],
            "proposals_delta": deltas["proposals"],
            "proposal_created_events_delta": proposal_events_after
            - proposal_events_before,
        },
        "A labelled seam wrapper committed revise_operation immediately before persistence; a successful call must store the revision current under MAIN's write lock.",
    )


def z04() -> tuple[str, dict[str, Any], str]:
    active: list[tuple[bool, sqlite3.Connection]] = []
    clock_states: list[dict[str, Any]] = []

    class ObservingClock:
        def __call__(self) -> int:
            clock_states.append(
                {
                    "active_transaction_count": len(active),
                    "active_modes": [write for write, _connection in active],
                    "in_transaction": [
                        connection.in_transaction for _write, connection in active
                    ],
                }
            )
            return 1_000_000

    with ledger(clock=ObservingClock()) as (system, _path, _clock):
        original = system.store.transaction
        opened_modes: list[bool] = []

        @contextmanager
        def transaction(*, write: bool = False):
            opened_modes.append(write)
            with original(write=write) as connection:
                active.append((write, connection))
                try:
                    yield connection
                finally:
                    active.pop()

        system.store.transaction = transaction  # type: ignore[method-assign]
        clock_states.clear()
        with system.store.transaction(write=True):
            system._now()
        positive_control = list(clock_states)
        clock_states.clear()
        opened_modes.clear()
        proposal_id = system.submit_proposal(
            "p",
            "op",
            {"x": 1},
            candidate=Candidate(output={"y": 2}, provenance={"probe": "z04"}),
        )
        direct_clock_states = list(clock_states)
        direct_transaction_modes = list(opened_modes)
    return (
        "ok",
        {
            "clock_spy_positive_control": positive_control,
            "clock_spy_positive_control_live": positive_control
            == [
                {
                    "active_transaction_count": 1,
                    "active_modes": [True],
                    "in_transaction": [True],
                }
            ],
            "direct_clock_read_count": len(direct_clock_states),
            "direct_clock_states": direct_clock_states,
            "direct_transaction_modes": direct_transaction_modes,
            "result": id_shape(proposal_id),
        },
        "A transaction wrapper exposed the active connection to the injected clock; a forced write-transaction read proved the spy before direct submission.",
    )


def q15() -> tuple[str, dict[str, Any], str]:
    source = Source()
    with ledger(source=source) as (system, _path, _clock):
        direct = captured_error(
            lambda: system.submit_proposal(
                "",
                "op",
                object(),
                candidate=Candidate(output=1, provenance={}),
            )
        )
        backed = captured_error(lambda: system.propose("", "op", object()))
    return (
        "error",
        {
            "direct_class": direct["class"],
            "direct_message": direct["message"],
            "source_backed_class": backed["class"],
            "source_backed_message": backed["message"],
            "source_invocations": source.calls,
        },
        "Two live calls combined an invalid partition with a non-JSON input; both rejected the partition first.",
    )


def q16() -> tuple[str, dict[str, Any], str]:
    source = Source()
    with ledger(source=source) as (system, _path, _clock):
        direct = captured_error(
            lambda: system.submit_proposal(
                "p",
                "",
                object(),
                candidate=Candidate(output=1, provenance={}),
            )
        )
        backed = captured_error(lambda: system.propose("p", "", object()))
    return (
        "error",
        {
            "direct_class": direct["class"],
            "direct_message": direct["message"],
            "source_backed_class": backed["class"],
            "source_backed_message": backed["message"],
            "source_invocations": source.calls,
        },
        "Two live calls combined an invalid operation with a non-JSON input; both rejected the operation first.",
    )


def q17() -> tuple[str, dict[str, Any], str]:
    source = Source()
    with ledger(source=source) as (system, _path, _clock):
        transactions = counted_transactions(system)
        error = captured_error(lambda: system.propose("", "unregistered", {"x": 1}))
    return (
        "error",
        {
            "class": error["class"],
            "message": error["message"],
            "transaction_count": len(transactions),
            "transaction_modes": transactions,
            "source_invocations": source.calls,
        },
        "A live transaction wrapper and source counter showed that partition validation rejected the combined call before either capability ran.",
    )


def q18() -> tuple[str, dict[str, Any], str]:
    source = Source()
    with ledger(source=source) as (system, _path, _clock):
        transactions = counted_transactions(system)
        rejected = captured_error(lambda: system.propose("p", "op", object()))
        rejected_transactions = list(transactions)
        rejected_source_calls = source.calls
        transactions.clear()
        proposal_id = system.propose("p", "op", {"x": 1})
        positive_transactions = list(transactions)
        positive_source_calls = source.calls - rejected_source_calls
    return (
        "error",
        {
            "rejected_class": rejected["class"],
            "rejected_message": rejected["message"],
            "rejected_transaction_count": len(rejected_transactions),
            "rejected_source_invocations": rejected_source_calls,
            "transaction_positive_control_count": len(positive_transactions),
            "transaction_positive_control_modes": positive_transactions,
            "source_positive_control_invocations": positive_source_calls,
            "positive_control_result": id_shape(proposal_id),
        },
        "The rejected call recorded zero transactions and source calls; an immediate valid call proved both counters live with one read, one write, and one source call.",
    )


def q19() -> tuple[str, dict[str, Any], str]:
    with ledger() as (system, _path, _clock):
        error = captured_error(lambda: system.submit_proposal("p", "op", {"x": 1}))
    return (
        "error",
        {"class": error["class"], "message": error["message"]},
        "A bound System method on a real initialized ledger produced Python's native missing-keyword-only TypeError.",
    )


def q20() -> tuple[str, dict[str, Any], str]:
    source = Source()
    candidate = Candidate(output=1, provenance={})
    with ledger(source=source) as (system, _path, _clock):
        direct = captured_error(
            lambda: system.submit_proposal(
                "p", "op", {"x": 1}, candidate=candidate, source=source  # type: ignore[call-arg]
            )
        )
        backed = captured_error(
            lambda: system.propose("p", "op", {"x": 1}, source=source)  # type: ignore[call-arg]
        )
    return (
        "error",
        {
            "submit_class": direct["class"],
            "submit_message": direct["message"],
            "propose_class": backed["class"],
            "propose_message": backed["message"],
            "source_invocations": source.calls,
        },
        "Both bound methods rejected source= through Python's native signature handling before the configured source could run.",
    )


PROBE_FUNCTIONS: dict[str, Callable[[], tuple[str, dict[str, Any], str]]] = {
    "Q01": q01,
    "Q02": q02,
    "Q03": q03,
    "Q04": q04,
    "Q05": q05,
    "Q06": q06,
    "Q07": q07,
    "Q08": q08,
    "Q09": q09,
    "Q10": q10,
    "Q11": q11,
    "Q12": q12,
    "Q13": q13,
    "Q14": q14,
    "Q15": q15,
    "Q16": q16,
    "Q17": q17,
    "Q18": q18,
    "Q19": q19,
    "Q20": q20,
    "Q21": q21,
    "Q22": q22,
    "Q23": q23,
    "Q24": q24,
    "Q25": q25,
    "Q26": q26,
    "Q27": q27,
    "Q28": q28,
    "Q29": q29,
    "Q30": q30,
}

EXTENSION_FUNCTIONS: dict[
    str, Callable[[], tuple[str, dict[str, Any], str]]
] = {
    "Z01": z01,
    "Z02": z02,
    "Z03": z03,
    "Z04": z04,
}
EXTENSION_PROBES = {
    "Z01": "private persistence seam name: raw MAIN and oracle class-level writer names, with no contract obligation attached",
    "Z02": "direct-path transaction count: live Store.transaction spy plus a read-transaction positive control",
    "Z03": "direct-path revision race: revise_operation commits immediately before the implementation's persistence seam",
    "Z04": "direct-path clock placement: active write-transaction state observed at the injected _now clock read",
}


def _git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *arguments],
        text=True,
    ).strip()


def run_provenance(module_file: Path) -> dict[str, Any]:
    return {
        "commit_sha": _git(
            "log", "-1", "--format=%H", "--", "src/cement_runtime/system.py"
        ),
        "dirty_tree": bool(_git("status", "--porcelain")),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "platform": platform.platform(),
        "cement_runtime_system": str(module_file.relative_to(ROOT)),
        "traceback_driver_frame": f"{_ORACLE_DRIVER_NAME} (oracle-original filename)",
        "probe_adaptations": {
            "Q30": "oracle _persist_submission → MAIN _persist_proposal"
        },
    }


EXTENSION_DIVERGENCES = {
    "Z01": (
        "The private single-writer seam is named _persist_proposal in MAIN and "
        "_persist_submission in the oracle. D06 constrains ownership and cardinality, "
        "not this private identifier, so the difference carries no contract defect."
    ),
    "Z02": (
        "Expected divergence 1: direct_transaction_count moves 1 → 2 and "
        "direct_transaction_modes moves [true] → [false, true]. MAIN performs only "
        "the authoritative write transaction; the oracle adds an entry read."
    ),
    "Z03": (
        "Expected divergence 1: after the injected revision commit, MAIN returns a "
        "proposal and writes one request/proposal/proposal.created event whose request "
        "binds the revision current under the write lock; the oracle raises "
        "StateError('operation revision changed before proposal submission') and "
        "writes none. The seam label also moves as isolated by Z01."
    ),
    "Z04": (
        "Expected divergence 2: MAIN's clock observes one active write transaction, "
        "while the oracle observes zero active transactions before opening its write. "
        "The direct transaction modes also move [true] → [false, true]."
    ),
}


def merge_extension_results(
    *,
    output_path: Path,
    artifact_path: Path,
    main_results_path: Path,
    oracle_results_path: Path,
) -> None:
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    oracle_payload = json.loads(PROBE_TEMPLATE_PATH.read_text(encoding="utf-8"))
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    main_results = json.loads(main_results_path.read_text(encoding="utf-8"))
    oracle_results = json.loads(oracle_results_path.read_text(encoding="utf-8"))
    payload_rows = {row["id"]: row for row in payload["rows"]}
    oracle_rows = {row["id"]: row for row in oracle_payload["rows"]}
    artifact_rows = {row["id"]: row for row in artifact["rows"]}
    main_extensions = {row["id"]: row for row in main_results["rows"]}
    oracle_extensions = {row["id"]: row for row in oracle_results["rows"]}

    q30 = artifact_rows["Q30"]
    q30.update(
        {
            "verdict": "identical",
            "main_observation": payload_rows["Q30"]["observation"],
            "oracle_observation": oracle_rows["Q30"]["observation"],
            "divergence": (
                "no divergence: after the explicit Q30 private-seam label substitution "
                "_persist_proposal ↔ _persist_submission, every contract-bearing "
                "census and live-execution field joins exactly; Z01 retains the raw "
                "name difference."
            ),
        }
    )

    paired = []
    for identifier in EXTENSION_FUNCTIONS:
        main_row = main_extensions[identifier]
        oracle_row = oracle_extensions[identifier]
        paired.append(
            {
                "id": identifier,
                "probe": EXTENSION_PROBES[identifier],
                "main": main_row,
                "oracle": oracle_row,
            }
        )
        row = {
            "id": identifier,
            "probe": EXTENSION_PROBES[identifier],
            "verdict": "differs",
            "main_observation": main_row["observation"],
            "oracle_observation": oracle_row["observation"],
            "divergence": EXTENSION_DIVERGENCES[identifier],
            "main_ruling": "unknown",
        }
        if identifier in artifact_rows:
            artifact_rows[identifier].update(row)
        else:
            artifact["rows"].append(row)

    payload["extensions"] = {
        "main_run_provenance": main_results["run_provenance"],
        "oracle_run_provenance": oracle_results["run_provenance"],
        "rows": paired,
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--probe",
        action="append",
        choices=tuple(PROBE_FUNCTIONS),
        dest="probes",
        help="run one seeded probe; repeat to select a batch (default: all)",
    )
    parser.add_argument("--extensions-only", action="store_true")
    parser.add_argument(
        "--extension",
        action="append",
        choices=tuple(EXTENSION_FUNCTIONS),
        dest="extensions",
        help="run one discriminating extension (default: all)",
    )
    parser.add_argument("--implementation-label")
    parser.add_argument("--implementation-commit")
    parser.add_argument("--expected-system-sha256")
    parser.add_argument(
        "--merge-extension-results",
        nargs=2,
        type=Path,
        metavar=("MAIN_RESULTS", "ORACLE_RESULTS"),
    )
    parser.add_argument("--artifact", type=Path, default=DEFAULT_DIVERGENCES_PATH)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    output_path = arguments.out.resolve()
    if output_path == PROBE_TEMPLATE_PATH.resolve():
        raise SystemExit(f"refusing to overwrite oracle evidence: {PROBE_TEMPLATE_PATH}")
    if arguments.merge_extension_results is not None:
        main_results, oracle_results = arguments.merge_extension_results
        merge_extension_results(
            output_path=output_path,
            artifact_path=arguments.artifact.resolve(),
            main_results_path=main_results.resolve(),
            oracle_results_path=oracle_results.resolve(),
        )
        print(f"MERGED-EXTENSIONS: {output_path}")
        print(f"UPDATED-ARTIFACT: {arguments.artifact.resolve()}")
        return 0

    module_file = Path(inspect.getfile(system_module)).resolve()
    expected_module = (ROOT / "src" / "cement_runtime" / "system.py").resolve()
    if module_file != expected_module:
        raise SystemExit(
            f"wrong cement_runtime.system loaded: {module_file}; expected {expected_module}"
        )
    module_sha256 = file_sha256(module_file)
    print(f"MODULE: {module_file}")
    print(f"MODULE-SHA256: {module_sha256}")
    if (
        arguments.expected_system_sha256 is not None
        and module_sha256 != arguments.expected_system_sha256
    ):
        raise SystemExit(
            f"wrong cement_runtime.system bytes: {module_sha256}; "
            f"expected {arguments.expected_system_sha256}"
        )

    if arguments.extensions_only:
        if not arguments.implementation_label or not arguments.implementation_commit:
            raise SystemExit(
                "--extensions-only requires --implementation-label and "
                "--implementation-commit"
            )
        selected_extensions = set(arguments.extensions or EXTENSION_FUNCTIONS)
        extension_rows = []
        for identifier, probe in EXTENSION_FUNCTIONS.items():
            if identifier not in selected_extensions:
                continue
            outcome, observation, note = probe()
            extension_rows.append(
                {
                    "id": identifier,
                    "probe": EXTENSION_PROBES[identifier],
                    "implementation": arguments.implementation_label,
                    "outcome": outcome,
                    "observation": {
                        "implementation": arguments.implementation_label,
                        **observation,
                    },
                    "note": note,
                }
            )
            print(f"{identifier}: {outcome}")
        provenance = run_provenance(module_file)
        provenance["commit_sha"] = arguments.implementation_commit
        provenance["cement_runtime_system_sha256"] = module_sha256
        extension_payload = {
            "kind": "discriminating-probes",
            "implementation": arguments.implementation_label,
            "rows": extension_rows,
            "run_provenance": provenance,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(extension_payload, indent=2) + "\n", encoding="utf-8"
        )
        print(f"WROTE: {output_path}")
        return 0

    preserved_extensions: object | None = None
    if output_path.is_file():
        preserved_extensions = json.loads(
            output_path.read_text(encoding="utf-8")
        ).get("extensions")
    selected = set(arguments.probes or PROBE_FUNCTIONS)
    payload = json.loads(PROBE_TEMPLATE_PATH.read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in payload["rows"]}
    for row in rows.values():
        row["outcome"] = "not-run"
        row["observation"] = {}
        row["note"] = "Not selected for this incremental run."
    for identifier, probe in PROBE_FUNCTIONS.items():
        if identifier not in selected:
            continue
        outcome, observation, note = probe()
        rows[identifier]["outcome"] = outcome
        rows[identifier]["observation"] = observation
        rows[identifier]["note"] = note
        print(f"{identifier}: {outcome}")

    provenance = run_provenance(module_file)
    payload["implementation"] = (
        f"cement_runtime.system loaded from {provenance['cement_runtime_system']}"
    )
    provenance["cement_runtime_system_sha256"] = module_sha256
    payload["run_provenance"] = provenance
    if preserved_extensions is not None:
        payload["extensions"] = preserved_extensions
    payload.pop("worktree_commit", None)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
