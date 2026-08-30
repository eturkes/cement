"""Execute M3.4's differential corpus against MAIN and patch its observations.

Usage:
  uv run python .agent/decisions/m3u4-probe-main.py
  uv run python .agent/decisions/m3u4-probe-main.py --check

The table is rewritten only through its own two-space, Unicode-preserving JSON
serialization. Every populated observation comes from a fresh ledger execution.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import io
import json
import re
import sqlite3
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest import mock

import cement_runtime.system as system_module
from cement_runtime import (
    Candidate,
    CompilePolicy,
    PendingProposalGap,
    ProposalView,
    ReviewResult,
    System,
)
from cement_runtime.cli import main as cli_main
from cement_runtime.json_value import canonicalize
from cement_runtime.system import _ProposalIds, _proposal_bindings

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / ".agent" / "decisions" / "m3u4-probes.json"
SCRATCH = ROOT / ".scratch"
UNKNOWN = "unknown"


@dataclasses.dataclass(frozen=True, slots=True)
class _Observation:
    text: str
    agrees: bool


@dataclasses.dataclass(slots=True)
class _Clock:
    now_us: int = 1_000_000

    def __call__(self) -> int:
        return self.now_us

    def advance(self, seconds: int) -> None:
        self.now_us += seconds * 1_000_000


class _Source:
    def propose(self, request: object) -> Candidate:
        value = getattr(request, "input")
        return Candidate(output={"echo": value}, provenance={"model": "probe"})


@dataclasses.dataclass(slots=True)
class _Fixture:
    database: str
    system: System
    clock: _Clock

    def submit(
        self,
        value: object,
        *,
        partition: str = "tenant_a",
        operation: str = "echo_1",
        output: object | None = None,
    ) -> str:
        candidate_output = {"echo": value} if output is None else output
        return self.system.submit_proposal(
            partition,
            operation,
            value,
            candidate=Candidate(
                output=candidate_output,
                provenance={"model": "probe"},
            ),
        )


class _Ids:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self, prefix: str) -> str:
        self.value += 1
        return f"{prefix}_{self.value:032x}"


@contextlib.contextmanager
def _fixture(
    *,
    partitions: tuple[str, ...] = ("tenant_a",),
    operations: tuple[str, ...] = ("echo_1",),
    policy: CompilePolicy = CompilePolicy(2, 1, 0),
) -> Iterator[_Fixture]:
    SCRATCH.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
        database = str(Path(temporary) / "probe.db")
        clock = _Clock()
        identifiers = _Ids()
        with mock.patch.object(system_module, "_new_id", side_effect=identifiers):
            runtime = System(database, candidate_source=_Source(), clock_us=clock)
            for partition in partitions:
                for operation in operations:
                    runtime.register_operation(partition, operation, policy=policy)
            yield _Fixture(database=database, system=runtime, clock=clock)


def _capture(call: Callable[[], object]) -> tuple[BaseException | None, object | None]:
    try:
        return None, call()
    except BaseException as error:  # The measured exception class is part of each probe.
        return error, None


@dataclasses.dataclass(frozen=True, slots=True)
class _CLIRun:
    status: int
    stdout: str
    stderr: str
    payload: object | None


class _BinaryOutput:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()

    def write(self, value: str) -> int:
        return self.buffer.write(value.encode("utf-8"))

    def flush(self) -> None:
        pass


def _run_cli(database: str, *arguments: str) -> _CLIRun:
    stdout = _BinaryOutput()
    stderr = io.StringIO()
    argv = ["--db", database, "--partition", "tenant_a", *arguments]
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        status = cli_main(argv)
    stdout_text = stdout.buffer.getvalue().decode("utf-8")
    stderr_text = stderr.getvalue()
    try:
        payload = json.loads(stdout_text) if stdout_text else None
    except json.JSONDecodeError:
        payload = None
    return _CLIRun(
        status=status,
        stdout=stdout_text,
        stderr=stderr_text,
        payload=payload,
    )


def _raw(database: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    return connection


def _delete_request(database: str, proposal_id: str) -> None:
    connection = _raw(database)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "DELETE FROM requests WHERE proposal_id = ?",
            (proposal_id,),
        )
        connection.commit()
    finally:
        connection.close()


def _corrupt_request(
    database: str,
    proposal_id: str,
    *,
    bound_proposal_id: str | None = None,
    input_json: str | None = None,
) -> None:
    assignments: list[str] = []
    parameters: list[object] = []
    if bound_proposal_id is not None:
        assignments.append("proposal_id = ?")
        parameters.append(bound_proposal_id)
    if input_json is not None:
        assignments.append("input_json = ?")
        parameters.append(input_json)
    parameters.append(proposal_id)
    connection = _raw(database)
    try:
        connection.execute(
            f"UPDATE requests SET {', '.join(assignments)} WHERE proposal_id = ?",
            parameters,
        )
        connection.commit()
    finally:
        connection.close()


def _submit_three(fixture: _Fixture, prefix: str) -> tuple[str, str, str]:
    return tuple(
        fixture.submit({"case": f"{prefix}-{index}"}) for index in range(1, 4)
    )  # type: ignore[return-value]


def _insert_pending_rows(
    fixture: _Fixture,
    rows: list[tuple[str, object, int]],
) -> dict[str, str]:
    provenance = canonicalize({"source": "probe"})
    request_rows: list[tuple[object, ...]] = []
    proposal_rows: list[tuple[object, ...]] = []
    input_hashes: dict[str, str] = {}
    for proposal_id, value, sequence in rows:
        request_id = proposal_id.replace("prop_", "req_", 1)
        input_json = canonicalize(value)
        proposed = canonicalize({"output": value})
        input_hashes[proposal_id] = input_json.digest
        request_rows.append(
            (
                request_id,
                "tenant_a",
                "echo_1",
                1,
                input_json.text,
                input_json.digest,
                proposal_id,
                sequence + 10_000,
                sequence + 10_000,
            )
        )
        proposal_rows.append(
            (
                proposal_id,
                "tenant_a",
                request_id,
                proposed.text,
                proposed.digest,
                provenance.text,
                provenance.digest,
                sequence + 10_000,
                sequence,
            )
        )
    with fixture.system.store.transaction(write=True) as connection:
        connection.executemany(
            """
            INSERT INTO requests(
                id, partition, operation, operation_revision,
                input_json, input_hash, status, proposal_id,
                created_at_us, updated_at_us
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            request_rows,
        )
        connection.executemany(
            """
            INSERT INTO proposals(
                id, partition, request_id,
                proposed_output_json, proposed_output_hash,
                provenance_json, provenance_hash,
                status, created_at_us, status_sequence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            proposal_rows,
        )
    return input_hashes


def _exception_agrees(row: dict[str, object], error: BaseException | None) -> bool:
    observed = str(row["observed"])
    expected_class = observed.split(":", 1)[0]
    return error is not None and type(error).__name__ == expected_class


def _z01(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z01"})
        _corrupt_request(
            fixture.database,
            proposal_id,
            bound_proposal_id="prop_wrong",
            input_json="{",
        )
        error, _ = _capture(
            lambda: fixture.system.get_proposal("tenant_a", proposal_id)
        )
        mismatch_won = error is not None and "JSON" not in str(error)
        text = (
            f"{type(error).__name__}: {error}. The binding mismatch won before "
            f"malformed input JSON; proposal_id={proposal_id}."
        )
        return _Observation(text, _exception_agrees(row, error) and mismatch_won)


def _z02(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z02"})
        _corrupt_request(
            fixture.database,
            proposal_id,
            bound_proposal_id="prop_wrong",
        )
        error, value = _capture(
            lambda: fixture.system.proposals("tenant_a", status="pending")
        )
        escaped = 0 if value is None else len(value)  # type: ignore[arg-type]
        text = (
            f"{type(error).__name__}: {error}. The list feed returned {escaped} "
            f"partial elements; corrupt proposal={proposal_id}."
        )
        return _Observation(
            text,
            _exception_agrees(row, error) and value is None and escaped == 0,
        )


def _z03(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_ids = _submit_three(fixture, "Z03")
        corrupt = proposal_ids[-1]
        _corrupt_request(
            fixture.database,
            corrupt,
            bound_proposal_id="prop_wrong",
        )
        error, value = _capture(
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            )
        )
        if error is not None:
            text = (
                f"{type(error).__name__}: {error}. The third sorted binding was "
                f"examined beyond projection_limit=1; corrupt proposal={corrupt}."
            )
        else:
            report = value
            now = getattr(report, "operation_now")
            page = tuple(gap.proposal_id for gap in now.pending_proposals)
            text = (
                f"FunctionReport returned with pending_proposal_count="
                f"{now.pending_proposal_count} and page IDs={page!r}; corrupt tail "
                f"{corrupt} was not validated at projection_limit=1."
            )
        return _Observation(text, _exception_agrees(row, error))


def _z04(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z04"})
        _delete_request(fixture.database, proposal_id)
        error, _ = _capture(
            lambda: fixture.system.get_proposal("tenant_a", proposal_id)
        )
        text = (
            f"{type(error).__name__}: {error}. The orphan remained visible to the "
            f"singular adapter; proposal_id={proposal_id}."
        )
        return _Observation(text, _exception_agrees(row, error))


def _z05(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z05"})
        _delete_request(fixture.database, proposal_id)
        error, value = _capture(
            lambda: fixture.system.proposals("tenant_a", status="pending")
        )
        escaped = 0 if value is None else len(value)  # type: ignore[arg-type]
        text = (
            f"{type(error).__name__}: {error}. The orphan remained visible to the "
            f"feed adapter; escaped list elements={escaped}; proposal_id={proposal_id}."
        )
        agrees = _exception_agrees(row, error) and escaped == 0
        return _Observation(text, agrees)


def _z06(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z06"})
        _delete_request(fixture.database, proposal_id)
        error, _ = _capture(
            lambda: fixture.system.review(
                "tenant_a",
                proposal_id,
                reviewer="oracle",
                decision="accept",
            )
        )
        connection = _raw(fixture.database)
        try:
            proposal_status = connection.execute(
                "SELECT status FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()["status"]
            examples = connection.execute(
                "SELECT COUNT(*) AS n FROM examples WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()["n"]
        finally:
            connection.close()
        text = (
            f"{type(error).__name__}: {error}. The review transaction left "
            f"proposals.status={proposal_status!r} and created {examples} example rows "
            f"for {proposal_id}."
        )
        agrees = (
            _exception_agrees(row, error)
            and proposal_status == "pending"
            and examples == 0
        )
        return _Observation(text, agrees)


def _z07(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z07"})
        result = fixture.system.review(
            "tenant_a",
            proposal_id,
            reviewer="oracle",
            decision="accept",
        )
        payload = dataclasses.asdict(result)
        text = f"{result!r}."
        agrees = (
            type(result).__name__ == "ReviewResult"
            and tuple(payload) == ("proposal_id", "status", "example_id", "output")
            and text == str(row["observed"])
        )
        return _Observation(text, agrees)


def _z08(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z08"})
        result = fixture.system.review(
            "tenant_a",
            proposal_id,
            reviewer="oracle",
            decision="correct",
            corrected_output={"corrected": 8},
        )
        payload = dataclasses.asdict(result)
        text = f"{result!r}."
        agrees = (
            type(result).__name__ == "ReviewResult"
            and tuple(payload) == ("proposal_id", "status", "example_id", "output")
            and text == str(row["observed"])
        )
        return _Observation(text, agrees)


def _z09(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z09"})
        result = fixture.system.review(
            "tenant_a",
            proposal_id,
            reviewer="oracle",
            decision="reject",
        )
        payload = dataclasses.asdict(result)
        text = f"{result!r}. Both nullable fields exist and equal None."
        agrees = (
            tuple(payload) == ("proposal_id", "status", "example_id", "output")
            and payload["example_id"] is None
            and payload["output"] is None
            and text == str(row["observed"])
        )
        return _Observation(text, agrees)


def _cli_payload(run: _CLIRun) -> dict[str, object]:
    if not isinstance(run.payload, dict):
        raise RuntimeError(f"CLI stdout is not an object: {run.stdout!r}")
    return run.payload


def _z10(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z10"})
        run = _run_cli(
            fixture.database,
            "proposal",
            "review",
            proposal_id,
            "--reviewer",
            "oracle",
            "--decision",
            "accept",
        )
        payload = _cli_payload(run)
        keys = tuple(sorted(payload))
        values = tuple(payload[key] for key in keys)
        text = (
            f"Exit {run.status}; stderr={run.stderr!r}; sorted stdout keys="
            f"({', '.join(keys)}); values={values!r}."
        )
        return _Observation(text, text == str(row["observed"]))


def _z11(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z11"})
        run = _run_cli(
            fixture.database,
            "proposal",
            "review",
            proposal_id,
            "--reviewer",
            "oracle",
            "--decision",
            "correct",
            "--output",
            '{"corrected":11}',
        )
        payload = _cli_payload(run)
        keys = tuple(sorted(payload))
        values = tuple(payload[key] for key in keys)
        text = (
            f"Exit {run.status}; stderr={run.stderr!r}; sorted stdout keys="
            f"({', '.join(keys)}); values={values!r}."
        )
        return _Observation(text, text == str(row["observed"]))


def _z12(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z12"})
        run = _run_cli(
            fixture.database,
            "proposal",
            "review",
            proposal_id,
            "--reviewer",
            "oracle",
            "--decision",
            "reject",
        )
        payload = _cli_payload(run)
        keys = tuple(sorted(payload))
        example_text = (
            "null" if payload.get("example_id") is None else repr(payload["example_id"])
        )
        output_text = "null" if payload.get("output") is None else repr(payload["output"])
        text = (
            f"Exit {run.status}; stderr={run.stderr!r}; stdout JSON exactly has "
            f"example_id={example_text}, output={output_text}, "
            f"proposal_id={payload.get('proposal_id')!r}, status={payload.get('status')!r}; "
            f"sorted key count={len(keys)}."
        )
        return _Observation(text, text == str(row["observed"]))


def _trace(call: Callable[[], object]) -> tuple[object, tuple[str, ...]]:
    statements: list[str] = []
    original_connect = sqlite3.connect

    class _TracingConnection(sqlite3.Connection):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self.set_trace_callback(statements.append)

    def traced_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        kwargs["factory"] = _TracingConnection
        return original_connect(*args, **kwargs)

    with mock.patch.object(sqlite3, "connect", side_effect=traced_connect):
        value = call()
    return value, tuple(statements)


def _application_statements(statements: tuple[str, ...]) -> tuple[str, ...]:
    channel = tuple(
        statement
        for statement in statements
        if not statement.lstrip().upper().startswith(("COMMIT", "ROLLBACK"))
    )
    return tuple(
        statement
        for statement in channel
        if not statement.lstrip().upper().startswith(("PRAGMA", "BEGIN"))
    )


def _statement_counts(statements: tuple[str, ...]) -> tuple[int, int, int]:
    channel = tuple(
        statement
        for statement in statements
        if not statement.lstrip().upper().startswith(("COMMIT", "ROLLBACK"))
    )
    application = _application_statements(statements)
    request_statements = tuple(
        statement
        for statement in application
        if re.search(r"\brequests\b", statement, flags=re.IGNORECASE)
    )
    return len(channel), len(application), len(request_statements)


def _expected_statement_counts(row: dict[str, object]) -> tuple[int, int, int]:
    match = re.search(
        r"whole channel=(\d+) statements, application=(\d+), requests-naming=(\d+)",
        str(row["observed"]),
    )
    if match is None:
        raise RuntimeError(f"{row['id']} lacks the statement-count triple")
    return tuple(int(value) for value in match.groups())  # type: ignore[return-value]


def _z13(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z13"})
        result, statements = _trace(
            lambda: fixture.system.get_proposal("tenant_a", proposal_id)
        )
        counts = _statement_counts(statements)
        application = _application_statements(statements)
        complete = (
            len(application) == 1
            and "LEFT JOIN requests" in application[0]
            and "p.id IN" in application[0]
        )
        text = (
            f"{type(result).__name__} returned; whole channel={counts[0]} statements, "
            f"application={counts[1]}, requests-naming={counts[2]}. The sole application "
            f"statement is the complete _ProposalIds SELECT with LEFT JOIN requests."
        )
        return _Observation(
            text,
            counts == _expected_statement_counts(row) and complete,
        )


def _z14(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        fixture.submit({"case": "Z14-1"})
        fixture.submit({"case": "Z14-2"})
        result, statements = _trace(
            lambda: fixture.system.proposals(
                "tenant_a",
                status="pending",
                limit=2,
            )
        )
        counts = _statement_counts(statements)
        application = _application_statements(statements)
        complete = (
            len(application) == 1
            and "LEFT JOIN requests" in application[0]
            and "p.status_sequence >" in application[0]
            and "LIMIT" in application[0]
        )
        text = (
            f"{type(result).__name__} returned; whole channel={counts[0]} statements, "
            f"application={counts[1]}, requests-naming={counts[2]}. One complete "
            f"_ProposalFeed SELECT applies partition, status, sequence order and LIMIT."
        )
        return _Observation(
            text,
            counts == _expected_statement_counts(row) and complete,
        )


def _z15(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        fixture.submit({"case": "Z15"})
        report, statements = _trace(
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            )
        )
        counts = _statement_counts(statements)
        text = (
            f"{type(report).__name__} returned; whole channel={counts[0]} statements, "
            f"application={counts[1]}, requests-naming={counts[2]}. Pending count and "
            f"detail use {counts[2]} requests-naming statements."
        )
        return _Observation(text, counts == _expected_statement_counts(row))


def _z16(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z16"})
        result, statements = _trace(
            lambda: fixture.system.review(
                "tenant_a",
                proposal_id,
                reviewer="oracle",
                decision="accept",
            )
        )
        counts = _statement_counts(statements)
        application = _application_statements(statements)
        labels: list[str] = []
        for statement in application:
            normalized = " ".join(statement.split()).upper()
            if normalized.startswith("SELECT P.*"):
                labels.append("binding SELECT")
            elif normalized.startswith("SELECT REVISION FROM OPERATIONS"):
                labels.append("revision SELECT")
            elif normalized.startswith("UPDATE PROPOSALS SET STATUS ="):
                labels.append("proposal UPDATE")
            elif normalized.startswith("INSERT INTO EXAMPLES"):
                labels.append("example INSERT")
            elif normalized.startswith("SELECT ID FROM ARTIFACTS"):
                labels.append("artifact SELECT")
            elif normalized.startswith("UPDATE REQUESTS"):
                labels.append("request UPDATE")
            elif normalized.startswith("INSERT INTO EVENTS"):
                labels.append("event INSERT")
            elif normalized.startswith("UPDATE PROPOSALS SET STATUS_SEQUENCE"):
                labels.append("sequence UPDATE")
            else:
                labels.append(f"unclassified {normalized.split()[0]}")
        order = ", ".join(labels)
        text = (
            f"{type(result).__name__} returned; whole channel={counts[0]} statements, "
            f"application={counts[1]}, requests-naming={counts[2]}. Application order: "
            f"{order}."
        )
        return _Observation(
            text,
            counts == _expected_statement_counts(row)
            and text == str(row["observed"]),
        )


def _reverse_fixture(fixture: _Fixture) -> dict[str, str]:
    return _insert_pending_rows(
        fixture,
        [
            ("prop_c", {"reverse": "c"}, 101),
            ("prop_b", {"reverse": "b"}, 102),
            ("prop_a", {"reverse": "a"}, 103),
        ],
    )


def _z17(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        _reverse_fixture(fixture)
        report = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=2,
        )
        now = report.operation_now
        ids = tuple(gap.proposal_id for gap in now.pending_proposals)
        revisions = tuple(gap.operation_revision for gap in now.pending_proposals)
        hashes = tuple(gap.input_hash for gap in now.pending_proposals)
        text = (
            "Exact oracle reverse-page input documents are unspecified; ran "
            "System.function_report on its prop_c/prop_b/prop_a and 101/102/103 shape "
            f"with deterministic replacement inputs. count={now.pending_proposal_count}; "
            f"page IDs={ids!r}; revisions={revisions!r}; hashes={hashes!r}."
        )
        agrees = (
            now.pending_proposal_count == 3
            and ids == ("prop_a", "prop_b")
            and revisions == (1, 1)
        )
        return _Observation(text, agrees)


def _z18(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        _reverse_fixture(fixture)
        small = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=2,
        ).operation_now.pending_proposals
        report = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=3,
        )
        now = report.operation_now
        ids = tuple(gap.proposal_id for gap in now.pending_proposals)
        revisions = tuple(gap.operation_revision for gap in now.pending_proposals)
        hashes = tuple(gap.input_hash for gap in now.pending_proposals)
        small_ids = tuple(gap.proposal_id for gap in small)
        text = (
            "Exact oracle reverse-page input documents are unspecified; ran the closest "
            f"MAIN fixture. count={now.pending_proposal_count}; full IDs={ids!r}; "
            f"limit-2 prefix={small_ids!r}; revisions={revisions!r}; hashes={hashes!r}."
        )
        agrees = (
            now.pending_proposal_count == 3
            and ids == ("prop_a", "prop_b", "prop_c")
            and small_ids == ids[:2]
            and revisions == (1, 1, 1)
        )
        return _Observation(text, agrees)


def _z19(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        _insert_pending_rows(
            fixture,
            [
                (f"prop_tail_{index:05d}", {"tail": index}, index + 2)
                for index in range(10_001)
            ],
        )
        report = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        )
        now = report.operation_now
        gap = now.pending_proposals[0]
        text = (
            f"pending_proposal_count={now.pending_proposal_count} and detail_count="
            f"{len(now.pending_proposals)}. The sole gap is {gap!r}."
        )
        return _Observation(text, text == str(row["observed"]))


def _decision_state(fixture: _Fixture, proposal_id: str) -> tuple[str, str, int]:
    connection = _raw(fixture.database)
    try:
        state = connection.execute(
            """
            SELECT p.status AS proposal_status, r.status AS request_status
            FROM proposals AS p JOIN requests AS r ON r.id = p.request_id
            WHERE p.id = ?
            """,
            (proposal_id,),
        ).fetchone()
        examples = connection.execute(
            "SELECT COUNT(*) AS n FROM examples WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()["n"]
    finally:
        connection.close()
    return state["proposal_status"], state["request_status"], examples


def _make_stale(fixture: _Fixture, proposal_id: str) -> None:
    revision = fixture.system.revise_operation(
        "tenant_a",
        "echo_1",
        policy=CompilePolicy(2, 1, 0),
        revised_by=f"stale-{proposal_id}",
    )
    if revision != 2:
        raise RuntimeError(f"stale fixture revised to {revision}, not 2")


def _z22(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z22"})
        _make_stale(fixture, proposal_id)
        error, _ = _capture(
            lambda: fixture.system.review(
                "tenant_a",
                proposal_id,
                reviewer="oracle",
                decision="accept",
            )
        )
        proposal_status, request_status, examples = _decision_state(
            fixture,
            proposal_id,
        )
        text = (
            f"{type(error).__name__}: {error}. Proposal status={proposal_status}, "
            f"request status={request_status}, examples for proposal={examples}."
        )
        return _Observation(text, text == str(row["observed"]))


def _z23(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z23"})
        _make_stale(fixture, proposal_id)
        error, _ = _capture(
            lambda: fixture.system.review(
                "tenant_a",
                proposal_id,
                reviewer="oracle",
                decision="correct",
                corrected_output={"corrected": True},
            )
        )
        proposal_status, request_status, examples = _decision_state(
            fixture,
            proposal_id,
        )
        text = (
            f"{type(error).__name__}: {error}. Proposal status={proposal_status}, "
            f"request status={request_status}, examples for proposal={examples}."
        )
        return _Observation(text, text == str(row["observed"]))


def _z24(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z24"})
        _make_stale(fixture, proposal_id)
        result = fixture.system.review(
            "tenant_a",
            proposal_id,
            reviewer="oracle",
            decision="reject",
        )
        proposal_status, request_status, examples = _decision_state(
            fixture,
            proposal_id,
        )
        text = (
            f"{result!r}; proposal status={proposal_status}, request status="
            f"{request_status}, examples={examples}. Reject bypasses the stale-revision fence."
        )
        return _Observation(text, text == str(row["observed"]))


def _z25(row: dict[str, object]) -> _Observation:
    with _fixture(policy=CompilePolicy(2, 1, 0)) as fixture:
        value = {"scope": "Z25"}
        for reviewer in ("oracle-a", "oracle-b"):
            proposal_id = fixture.submit(value, output={"version": 1})
            fixture.system.review(
                "tenant_a",
                proposal_id,
                reviewer=reviewer,
                decision="accept",
            )
        artifact_id = fixture.system.compile("tenant_a", "echo_1").created[0]
        verification = fixture.system.verify("tenant_a", artifact_id)
        fixture.system.promote(
            "tenant_a",
            artifact_id,
            scope_hash=verification.scope_hash,
            promoted_by="oracle",
        )
        conflicting = fixture.submit(value, output={"version": 2})
        result = fixture.system.review(
            "tenant_a",
            conflicting,
            reviewer="oracle",
            decision="accept",
        )
        connection = _raw(fixture.database)
        try:
            example_count = connection.execute(
                "SELECT COUNT(*) AS n FROM examples WHERE proposal_id = ?",
                (conflicting,),
            ).fetchone()["n"]
            artifact_status = connection.execute(
                "SELECT status FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()["status"]
            event_count = connection.execute(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE kind = 'artifact.counterexample' AND subject_id = ?
                """,
                (artifact_id,),
            ).fetchone()["n"]
        finally:
            connection.close()
        text = (
            f"ReviewResult accepted {result.proposal_id} with example {result.example_id} "
            f"and output={result.output!r}. Exactly {example_count} example row exists; "
            f"{artifact_id} became {artifact_status}; artifact.counterexample event "
            f"count={event_count}."
        )
        agrees = (
            result.proposal_id == conflicting
            and result.status == "accepted"
            and result.output == {"version": 2}
            and example_count == 1
            and artifact_status == "suspended"
            and event_count == 1
            and str(row["observed"]).startswith(
                f"ReviewResult accepted {result.proposal_id} with example {result.example_id}"
            )
        )
        return _Observation(text, agrees)


def _z26(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        decisions = (
            ("accept", None),
            ("correct", {"corrected": 26}),
            ("reject", None),
        )
        proposal_ids: list[str] = []
        for decision, corrected in decisions:
            proposal_id = fixture.submit({"case": f"Z26-{decision}"})
            proposal_ids.append(proposal_id)
            arguments: dict[str, object] = {
                "reviewer": "oracle",
                "decision": decision,
            }
            if corrected is not None:
                arguments["corrected_output"] = corrected
            fixture.system.review(
                "tenant_a",
                proposal_id,
                **arguments,  # type: ignore[arg-type]
            )
        connection = _raw(fixture.database)
        try:
            pairs: list[tuple[int, int]] = []
            for (decision, _), proposal_id in zip(
                decisions,
                proposal_ids,
                strict=True,
            ):
                proposal_sequence = connection.execute(
                    "SELECT status_sequence FROM proposals WHERE id = ?",
                    (proposal_id,),
                ).fetchone()["status_sequence"]
                event_sequence = connection.execute(
                    """
                    SELECT sequence FROM events
                    WHERE kind = ? AND subject_id = ?
                    """,
                    (f"proposal.{('corrected' if decision == 'correct' else decision + 'ed')}", proposal_id),
                ).fetchone()["sequence"]
                pairs.append((proposal_sequence, event_sequence))
        finally:
            connection.close()
        rendered_pairs = tuple(f"({left},{right})" for left, right in pairs)
        text = (
            f"Exact pairs are accept={rendered_pairs[0]} for {proposal_ids[0]}, "
            f"correct={rendered_pairs[1]} for {proposal_ids[1]}, reject="
            f"{rendered_pairs[2]} for {proposal_ids[2]}, where each tuple is "
            f"(proposal.status_sequence, decision event.sequence)."
        )
        oracle = str(row["observed"])
        expected_pairs = tuple(
            (int(left), int(right))
            for left, right in re.findall(r"=\((\d+),(\d+)\)", oracle)
        )
        expected_suffixes = tuple(re.findall(r"prop_\.\.\.([0-9a-z]+)", oracle))
        ids_agree = len(expected_suffixes) == len(proposal_ids) and all(
            proposal_id.endswith(suffix)
            for proposal_id, suffix in zip(
                proposal_ids,
                expected_suffixes,
                strict=True,
            )
        )
        return _Observation(text, tuple(pairs) == expected_pairs and ids_agree)


def _z27(row: dict[str, object]) -> _Observation:
    partitions = ("tenant_a", "tenantXa", "TENANT_A")
    with _fixture(partitions=partitions) as fixture:
        proposal_ids = tuple(
            fixture.submit(
                {"partition": partition},
                partition=partition,
            )
            for partition in partitions
        )
        feed = fixture.system.proposals("tenant_a", status="pending")
        report = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=10,
        )
        feed_ids = tuple(str(item["id"]) for item in feed)
        report_ids = tuple(
            gap.proposal_id for gap in report.operation_now.pending_proposals
        )
        errors = tuple(
            _capture(
                lambda partition=partition: fixture.system.get_proposal(
                    partition,
                    proposal_ids[0],
                )
            )[0]
            for partition in partitions[1:]
        )
        text = (
            f"tenant_a feed IDs and report IDs both equal only ({proposal_ids[0]}); "
            f"report count={report.operation_now.pending_proposal_count}. Collider IDs "
            f"{proposal_ids[1]} and {proposal_ids[2]} are absent. get_proposal from "
            f"tenantXa and TENANT_A each raises {type(errors[0]).__name__}: {errors[0]}."
        )
        agrees = (
            feed_ids == report_ids == (proposal_ids[0],)
            and report.operation_now.pending_proposal_count == 1
            and all(type(error).__name__ == "NotFoundError" for error in errors)
            and len({str(error) for error in errors}) == 1
        )
        return _Observation(text, agrees)


def _z28(row: dict[str, object]) -> _Observation:
    operations = ("echo_1", "echoX1", "ECHO_1")
    with _fixture(operations=operations) as fixture:
        proposal_ids = tuple(
            fixture.submit(
                {"operation": operation},
                operation=operation,
            )
            for operation in operations
        )
        report = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=10,
        )
        report_ids = tuple(
            gap.proposal_id for gap in report.operation_now.pending_proposals
        )
        projected_operations = tuple(
            fixture.system.get_proposal("tenant_a", proposal_id).operation
            for proposal_id in proposal_ids
        )
        text = (
            f"echo_1 report count={report.operation_now.pending_proposal_count} and "
            f"IDs=({proposal_ids[0]}), excluding echoX1 {proposal_ids[1]} and ECHO_1 "
            f"{proposal_ids[2]}. Singular reads report operations exactly "
            f"({', '.join(projected_operations)}), preserving underscore and case isolation."
        )
        agrees = (
            report.operation_now.pending_proposal_count == 1
            and report_ids == (proposal_ids[0],)
            and projected_operations == operations
        )
        return _Observation(text, agrees)


def _z29(row: dict[str, object]) -> _Observation:
    observations: list[tuple[str, str, str]] = []
    for path in (
        "get_proposal",
        "proposal",
        "proposals",
        "review",
        "function_report",
    ):
        with _fixture() as fixture:
            proposal_id = fixture.submit({"case": f"Z29-{path}"})
            _corrupt_request(fixture.database, proposal_id, input_json="{")
            invocations: dict[str, Callable[[], object]] = {
                "get_proposal": lambda: fixture.system.get_proposal(
                    "tenant_a",
                    proposal_id,
                ),
                "proposal": lambda: fixture.system.proposal("tenant_a", proposal_id),
                "proposals": lambda: fixture.system.proposals("tenant_a"),
                "review": lambda: fixture.system.review(
                    "tenant_a",
                    proposal_id,
                    reviewer="oracle",
                    decision="accept",
                ),
                "function_report": lambda: fixture.system.function_report(
                    "tenant_a",
                    "echo_1",
                ),
            }
            error, value = _capture(invocations[path])
            observations.append(
                (
                    path,
                    type(error).__name__,
                    str(error),
                )
            )
            if value is not None:
                raise RuntimeError(f"Z29 {path} returned {value!r}")
    text = "Fresh-ledger malformed input results: " + "; ".join(
        f"{path}={error_class}: {message}"
        for path, error_class, message in observations
    ) + "."
    agrees = all(error_class == "IntegrityError" for _, error_class, _ in observations)
    return _Observation(text, agrees)


def _z30(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z30"})
        proposal = fixture.system.proposal("tenant_a", proposal_id)
        text = (
            f"proposal() returns status={proposal['status']!r}, final_output="
            f"{proposal['final_output']!r}, reviewer={proposal['reviewer']!r}, "
            f"review_note={proposal['review_note']!r} and reviewed_at_us="
            f"{proposal['reviewed_at_us']!r} for {proposal_id}; no raw TypeError reaches "
            f"the caller."
        )
        return _Observation(text, text == str(row["observed"]))


def _z31(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        outcome = fixture.system.handle(
            "tenant_a",
            "echo_1",
            {"case": "Z31"},
            request_id="handle_z31",
        )
        connection = _raw(fixture.database)
        try:
            payload_text = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE kind = 'proposal.created' AND subject_id = ?
                """,
                (outcome.proposal_id,),
            ).fetchone()["payload_json"]
        finally:
            connection.close()
        payload = json.loads(payload_text)
        text = (
            f"Outcome class={type(outcome).__name__}; proposal_id={outcome.proposal_id}; "
            f"proposal.created payload is exactly {payload!r}. The handle-lifecycle "
            f"exception remains intact."
        )
        agrees = (
            type(outcome).__name__ == "ReviewRequired"
            and payload == {"request_id": "handle_z31"}
            and str(row["observed"]).endswith(
                "The handle-lifecycle exception remains intact."
            )
        )
        return _Observation(text, agrees)


def _z32(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        submitted = fixture.submit({"case": "Z32-submit"})
        proposed = fixture.system.propose(
            "tenant_a",
            "echo_1",
            {"case": "Z32-propose"},
        )
        connection = _raw(fixture.database)
        try:
            payloads = {
                subject_id: json.loads(payload_text)
                for subject_id, payload_text in connection.execute(
                    """
                    SELECT subject_id, payload_json FROM events
                    WHERE kind = 'proposal.created' AND subject_id IN (?, ?)
                    """,
                    (submitted, proposed),
                ).fetchall()
            }
        finally:
            connection.close()
        text = (
            f"submit_proposal created {submitted} with payload={payloads[submitted]!r}; "
            f"propose created {proposed} with payload={payloads[proposed]!r}. Both direct "
            f"routes emit an empty object and expose no request identity."
        )
        oracle = str(row["observed"])
        expected_suffixes = tuple(re.findall(r"prop_\.\.\.([0-9a-z]+)", oracle))
        ids_agree = len(expected_suffixes) == 2 and all(
            proposal_id.endswith(suffix)
            for proposal_id, suffix in zip(
                (submitted, proposed),
                expected_suffixes,
                strict=True,
            )
        )
        return _Observation(
            text,
            ids_agree and payloads == {submitted: {}, proposed: {}},
        )


def _z34(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z34"})
        transactions: list[tuple[sqlite3.Connection, bool]] = []
        adapters: list[tuple[sqlite3.Connection, bool]] = []
        writers: list[tuple[sqlite3.Connection, bool]] = []
        original_transaction = fixture.system.store.transaction
        original_adapter = system_module._proposal_bindings
        original_writer = system_module._write_proposal_request_status

        @contextlib.contextmanager
        def tracked_transaction(*, write: bool = False) -> Iterator[sqlite3.Connection]:
            with original_transaction(write=write) as connection:
                transactions.append((connection, write))
                yield connection

        def tracked_adapter(
            connection: sqlite3.Connection,
            *,
            partition: str,
            selection: object,
        ) -> object:
            adapters.append((connection, connection.in_transaction))
            return original_adapter(
                connection,
                partition=partition,
                selection=selection,
            )

        def tracked_writer(
            connection: sqlite3.Connection,
            **arguments: object,
        ) -> int:
            writers.append((connection, connection.in_transaction))
            return original_writer(connection, **arguments)  # type: ignore[arg-type]

        with mock.patch.object(
            fixture.system.store,
            "transaction",
            new=tracked_transaction,
        ), mock.patch.object(
            system_module,
            "_proposal_bindings",
            new=tracked_adapter,
        ), mock.patch.object(
            system_module,
            "_write_proposal_request_status",
            new=tracked_writer,
        ):
            result = fixture.system.review(
                "tenant_a",
                proposal_id,
                reviewer="oracle",
                decision="accept",
            )
        same = (
            len(transactions) == len(adapters) == len(writers) == 1
            and transactions[0][0] is adapters[0][0] is writers[0][0]
        )
        agrees = (
            same
            and transactions[0][1]
            and adapters[0][1]
            and writers[0][1]
            and result.status == "accepted"
        )
        text = (
            f"One write={transactions[0][1]} transaction spans {len(adapters)} adapter "
            f"call and {len(writers)} writer call. Both receive the same connection "
            f"object={same}; in_transaction={adapters[0][1] and writers[0][1]} at both "
            f"entries. Review returns {result.status} ReviewResult for {result.proposal_id} "
            f"with example {result.example_id}."
        )
        return _Observation(text, agrees)


def _z35(row: dict[str, object]) -> _Observation:
    with _fixture(partitions=("tenant_a", "tenantXa")) as fixture:
        target = fixture.submit({"case": "Z35-target"}, partition="tenant_a")
        collider = fixture.submit({"case": "Z35-collider"}, partition="tenantXa")
        invocations = (
            lambda: fixture.system.get_proposal("tenantXa", target),
            lambda: fixture.system.proposal("tenantXa", target),
            lambda: fixture.system.review(
                "tenantXa",
                target,
                reviewer="oracle",
                decision="accept",
            ),
        )
        errors = tuple(_capture(invoke)[0] for invoke in invocations)
        feed_ids = tuple(
            str(proposal["id"])
            for proposal in fixture.system.proposals("tenantXa", status="pending")
        )
        report = fixture.system.function_report(
            "tenantXa",
            "echo_1",
            projection_limit=10,
        )
        report_ids = tuple(
            gap.proposal_id for gap in report.operation_now.pending_proposals
        )
        target_status = fixture.system.proposal("tenant_a", target)["status"]
        text = (
            f"get_proposal, proposal and review each raise {type(errors[0]).__name__}: "
            f"{errors[0]}. tenantXa feed/report IDs=({collider}), report count="
            f"{report.operation_now.pending_proposal_count}, and tenant_a target {target} "
            f"remains {target_status}."
        )
        agrees = (
            all(type(error).__name__ == "NotFoundError" for error in errors)
            and len({str(error) for error in errors}) == 1
            and feed_ids == report_ids == (collider,)
            and report.operation_now.pending_proposal_count == 1
            and target_status == "pending"
        )
        return _Observation(text, agrees)


def _z36(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z36"})
        report = fixture.system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        )
        gap = report.operation_now.pending_proposals[0]
        payload = dataclasses.asdict(gap)
        field_names = tuple(payload)
        slots = tuple(gap.__slots__)
        connection = _raw(fixture.database)
        try:
            request_id = connection.execute(
                "SELECT request_id FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()["request_id"]
        finally:
            connection.close()
        text = (
            f"Fields and slots are exactly ({', '.join(field_names)}); values="
            f"{tuple(payload.values())!r}. hasattr(request_id)="
            f"{hasattr(gap, 'request_id')} although storage has {request_id}."
        )
        oracle = str(row["observed"])
        request_suffixes = tuple(re.findall(r"req_\.\.\.([0-9a-z]+)", oracle))
        return _Observation(
            text,
            field_names == slots
            and not hasattr(gap, "request_id")
            and repr(tuple(payload.values())) in oracle
            and len(request_suffixes) == 1
            and request_id.endswith(request_suffixes[0]),
        )


def _z42(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z42"})
        connection = _raw(fixture.database)
        try:
            request_id = connection.execute(
                "SELECT request_id FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()["request_id"]
        finally:
            connection.close()
        reviewed = fixture.system.review(
            "tenant_a",
            proposal_id,
            reviewer="oracle",
            decision="accept",
        )
        lifecycle = fixture.system.request_status("tenant_a", request_id)
        text = (
            f"review returns {type(reviewed).__name__} status={reviewed.status!r} with "
            f"no request_id attribute; request_status returns {type(lifecycle).__name__} "
            f"status={lifecycle.status!r} with request_id={lifecycle.request_id!r}. Cement "
            f"translates neither vocabulary into the other."
        )
        return _Observation(
            text,
            not hasattr(reviewed, "request_id")
            and lifecycle.request_id == request_id
            and text == str(row["observed"]),
        )


def _z20(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z20"})

        def invoke() -> object:
            with fixture.system.store.transaction(write=False) as connection:
                return _proposal_bindings(
                    connection,
                    partition="tenant_a",
                    selection=_ProposalIds((proposal_id, proposal_id)),
                )

        error, value = _capture(invoke)
        text = (
            f"{type(error).__name__}: {error}. No binding batch was returned for the "
            f"duplicated {proposal_id} selection."
        )
        return _Observation(
            text,
            _exception_agrees(row, error) and value is None,
        )


def _z21(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:

        def invoke() -> object:
            with fixture.system.store.transaction(write=False) as connection:
                return _proposal_bindings(
                    connection,
                    partition="tenant_a",
                    selection=_ProposalIds(()),
                )

        result, statements = _trace(invoke)
        application_count = len(_application_statements(statements))
        text = (
            f"{type(result).__name__}(total={result.total}, rows={result.rows!r}) returned. "
            f"Application statement count={application_count}; the empty selection "
            f"short-circuits before SQL."
        )
        agrees = result.total == 0 and result.rows == () and application_count == 0
        return _Observation(text, agrees)


def _z33(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z33"})
        invocations = (
            lambda: fixture.system.get_proposal("tenant_a", proposal_id),
            lambda: fixture.system.proposals("tenant_a", status="pending"),
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            ),
        )
        results: list[tuple[int, int, bool, bool, str]] = []
        for invoke in invocations:
            transactions: list[sqlite3.Connection] = []
            adapters: list[tuple[sqlite3.Connection, bool]] = []
            original_transaction = fixture.system.store.transaction
            original_adapter = system_module._proposal_bindings

            @contextlib.contextmanager
            def tracked_transaction(*, write: bool = False) -> Iterator[sqlite3.Connection]:
                with original_transaction(write=write) as connection:
                    transactions.append(connection)
                    yield connection

            def tracked_adapter(
                connection: sqlite3.Connection,
                *,
                partition: str,
                selection: object,
            ) -> object:
                adapters.append((connection, connection.in_transaction))
                return original_adapter(
                    connection,
                    partition=partition,
                    selection=selection,
                )

            with mock.patch.object(
                fixture.system.store,
                "transaction",
                new=tracked_transaction,
            ), mock.patch.object(
                system_module,
                "_proposal_bindings",
                new=tracked_adapter,
            ):
                value = invoke()
            same = (
                len(transactions) == 1
                and len(adapters) == 1
                and transactions[0] is adapters[0][0]
            )
            in_transaction = len(adapters) == 1 and adapters[0][1]
            results.append(
                (
                    len(transactions),
                    len(adapters),
                    same,
                    in_transaction,
                    type(value).__name__,
                )
            )

        agrees = all(
            transaction_count == adapter_count == 1 and same and in_transaction
            for transaction_count, adapter_count, same, in_transaction, _ in results
        ) and tuple(result[-1] for result in results) == (
            "ProposalView",
            "list",
            "FunctionReport",
        )
        if agrees:
            text = (
                "Singular, feed and report each opened 1 transaction and made 1 adapter "
                "call. For all three, adapter connection is the exact yielded object and "
                "in_transaction=True; return classes are ProposalView, list and FunctionReport."
            )
        else:
            text = f"Per-path transaction/adapter/identity/in-transaction/class results={results!r}."
        return _Observation(text, agrees and text == str(row["observed"]))


def _z37(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_id = fixture.submit({"case": "Z37"})
        _delete_request(fixture.database, proposal_id)
        error, value = _capture(
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            )
        )
        text = (
            f"{type(error).__name__}: {error}. The in-page orphan was rejected before "
            f"a {type(value).__name__ if value is not None else 'FunctionReport'} escaped; "
            f"proposal_id={proposal_id}."
        )
        return _Observation(text, _exception_agrees(row, error) and value is None)


def _z38(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_ids = _submit_three(fixture, "Z38")
        orphan = proposal_ids[-1]
        _delete_request(fixture.database, orphan)
        error, value = _capture(
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            )
        )
        text = (
            f"{type(error).__name__}: {error}. The count-side orphan check reached "
            f"{orphan} beyond projection_limit=1; FunctionReport returned={value is not None}."
        )
        return _Observation(text, _exception_agrees(row, error) and value is None)


def _z39(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        proposal_ids = _submit_three(fixture, "Z39")
        corrupt = proposal_ids[-1]
        _corrupt_request(fixture.database, corrupt, input_json="{")
        low_error, low_value = _capture(
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            )
        )
        high_error, high_value = _capture(
            lambda: fixture.system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=3,
            )
        )
        low_now = getattr(low_value, "operation_now", None)
        low_page = (
            tuple(gap.proposal_id for gap in low_now.pending_proposals)
            if low_now is not None
            else ()
        )
        text = (
            f"At limit=1, error={type(low_error).__name__ if low_error else None}; "
            f"count={getattr(low_now, 'pending_proposal_count', None)}; page IDs={low_page!r}. "
            f"At limit=3, {type(high_error).__name__ if high_error else type(high_value).__name__}: "
            f"{high_error if high_error else 'returned'}."
        )
        oracle = str(row["observed"])
        agrees = (
            "At limit=1 the report returns count=3" in oracle
            and "At limit=3 it raises IntegrityError" in oracle
            and low_error is None
            and low_now is not None
            and low_now.pending_proposal_count == 3
            and low_page == (proposal_ids[0],)
            and type(high_error).__name__ == "IntegrityError"
            and high_value is None
        )
        return _Observation(text, agrees)


def _z40(row: dict[str, object]) -> _Observation:
    with _fixture() as fixture:
        first = fixture.submit({"case": "Z40-1"})
        second = fixture.submit({"case": "Z40-2"})
        selection = (second, first)
        with fixture.system.store.transaction(write=False) as connection:
            result = _proposal_bindings(
                connection,
                partition="tenant_a",
                selection=_ProposalIds(selection),
            )
        returned = tuple(binding.proposal_id for binding in result.rows)
        expected_match = re.search(
            r"returned order=\(([^)]*)\)",
            str(row["observed"]),
        )
        if expected_match is None:
            raise RuntimeError("Z40 lacks the oracle returned order")
        expected_suffixes = tuple(
            re.findall(r"prop_\.\.\.([0-9a-z]+)", expected_match.group(1))
        )
        suffixes_agree = len(returned) == len(expected_suffixes) and all(
            identifier.endswith(suffix)
            for identifier, suffix in zip(returned, expected_suffixes, strict=True)
        )
        text = (
            f"Selection order={selection!r}; returned order={returned!r}; total="
            f"{result.total}. MAIN's closest result type is {type(result).__name__}."
        )
        return _Observation(text, suffixes_agree and result.total == 2)


def _shape_names(shape: type[object]) -> tuple[str, ...]:
    return tuple(field.name for field in dataclasses.fields(shape))


def _z41(row: dict[str, object]) -> _Observation:
    shapes = (ProposalView, ReviewResult, PendingProposalGap)
    field_sets = {shape.__name__: _shape_names(shape) for shape in shapes}
    slots = {shape.__name__: tuple(shape.__slots__) for shape in shapes}
    frozen = all(shape.__dataclass_params__.frozen for shape in shapes)
    slotted = all(slots[shape.__name__] == field_sets[shape.__name__] for shape in shapes)
    dict_slot = any("__dict__" in slots[shape.__name__] for shape in shapes)
    rendered = ", ".join(
        f"{shape.__name__}=({','.join(field_sets[shape.__name__])})"
        for shape in shapes
    )
    text = (
        f"All three report frozen={frozen} and slots={slotted} with "
        f"{'a' if dict_slot else 'no'} __dict__ slot. Field/slot tuples are {rendered}."
    )
    return _Observation(text, text == str(row["observed"]))


Probe = Callable[[dict[str, object]], _Observation]
PROBES: dict[str, Probe] = {
    "Z01": _z01,
    "Z02": _z02,
    "Z03": _z03,
    "Z04": _z04,
    "Z05": _z05,
    "Z06": _z06,
    "Z07": _z07,
    "Z08": _z08,
    "Z09": _z09,
    "Z10": _z10,
    "Z11": _z11,
    "Z12": _z12,
    "Z13": _z13,
    "Z14": _z14,
    "Z15": _z15,
    "Z16": _z16,
    "Z17": _z17,
    "Z18": _z18,
    "Z19": _z19,
    "Z20": _z20,
    "Z21": _z21,
    "Z22": _z22,
    "Z23": _z23,
    "Z24": _z24,
    "Z25": _z25,
    "Z26": _z26,
    "Z27": _z27,
    "Z28": _z28,
    "Z29": _z29,
    "Z30": _z30,
    "Z31": _z31,
    "Z32": _z32,
    "Z33": _z33,
    "Z34": _z34,
    "Z35": _z35,
    "Z36": _z36,
    "Z37": _z37,
    "Z38": _z38,
    "Z39": _z39,
    "Z40": _z40,
    "Z41": _z41,
    "Z42": _z42,
}


def _load() -> tuple[str, dict[str, object]]:
    raw = TABLE.read_text(encoding="utf-8")
    document = json.loads(raw)
    round_trip = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if raw != round_trip:
        raise RuntimeError(
            "probe table serialization is not indent=2, ensure_ascii=False, trailing newline"
        )
    return raw, document


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when the table is stale")
    args = parser.parse_args(argv)

    try:
        raw, document = _load()
        rows = document["rows"]
        identifiers = [row["id"] for row in rows]
        if sorted(identifiers) != sorted(PROBES):
            missing = sorted(set(identifiers) - set(PROBES))
            extra = sorted(set(PROBES) - set(identifiers))
            print(f"INVALID: id set differs. unmeasured rows {missing}; extra probes {extra}")
            return 2

        measured = 0
        for row in rows:
            observation = PROBES[row["id"]](row)
            measured += 1
            row["main_observed"] = observation.text
            row["differs"] = "no" if observation.agrees else "yes"
    except Exception as error:
        print(f"PROBE-ERROR: {type(error).__name__}: {error}")
        return 2

    rendered = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    stale = rendered != raw
    agreements = sum(row.get("differs") == "no" for row in rows)
    divergences = sum(row.get("differs") == "yes" for row in rows)
    unknown = sum(
        row.get(column) == UNKNOWN for row in rows for column in ("main_observed", "differs")
    )

    if args.check:
        print(f"ROWS: {len(rows)}  MEASURED: {measured}  STALE: {int(stale)}")
        print(
            f"AGREEMENTS: {agreements}  DIVERGENCES: {divergences}  UNKNOWN-CELLS: {unknown}"
        )
        print("RESULT: IN-SYNC" if not stale else "RESULT: STALE")
        return 0 if not stale else 1

    TABLE.write_text(rendered, encoding="utf-8")
    print(f"WROTE: {TABLE.relative_to(ROOT)}  rows {len(rows)}  measured {measured}")
    print(
        f"AGREEMENTS: {agreements}  DIVERGENCES: {divergences}  UNKNOWN-CELLS: {unknown}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
