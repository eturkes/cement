"""Diff-blind obligation battery for M3.4 request-free proposal seams.

One test per numbered obligation of ``.agent/decisions/m3u4-contract.md``, named
``test_<id>_<slug>``. Coverage is graded by
``uv run python .agent/decisions/m3u4-battery-validate.py``.

Sections 14 and 15 of that contract AMEND the numbered obligations and govern where
they disagree, so every test encodes the ruled form. Each test states its obligation
in its own docstring, including how the assertion reproduces it, because a finding is
graded by whether its reproduction is stated and never by whether its number differs.
"""

from __future__ import annotations

import ast
from contextlib import closing, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import typing
import unittest
from unittest import mock

import cement_runtime
from cement_runtime import (
    Candidate,
    CompilePolicy,
    IntegrityError,
    NotFoundError,
    PendingProposalGap,
    ProposalView,
    ReviewRequired,
    ReviewResult,
    StateError,
    System,
    ValidationError,
)
import cement_runtime.models as models_module
import cement_runtime.store as store_module
import cement_runtime.system as system_module


class _Clock:
    def __init__(self, now_us: int = 1_000_000) -> None:
        self.now_us = now_us

    def __call__(self) -> int:
        return self.now_us


class _Source:
    def propose(self, request: object) -> Candidate:
        input_value = typing.cast(typing.Any, request).input
        return Candidate(
            output={"echo": input_value},
            provenance={"model": "battery", "rank": 13},
        )


class _BinaryOutput:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()

    def write(self, value: str) -> int:
        return self.buffer.write(value.encode("utf-8"))

    def flush(self) -> None:
        pass


@contextmanager
def _record_sql() -> typing.Iterator[
    tuple[list[tuple[int, bool, str, str, tuple[object, ...]]], list[int]]
]:
    records: list[tuple[int, bool, str, str, tuple[object, ...]]] = []
    connection_ids: list[int] = []
    real_connect = store_module.sqlite3.connect

    class RecordingCursor:
        def __init__(self, inner: sqlite3.Cursor, owner: sqlite3.Connection) -> None:
            self._inner = inner
            self._owner = owner

        def __getattr__(self, name: str) -> object:
            return getattr(self._inner, name)

        def __iter__(self) -> typing.Iterator[sqlite3.Row]:
            return iter(self._inner)

        def _record(self, channel: str, sql: str, args: tuple[object, ...]) -> None:
            records.append(
                (id(self._owner), self._owner.in_transaction, channel, sql, args)
            )

        def execute(self, sql: str, *args: object, **kwargs: object) -> sqlite3.Cursor:
            self._record("cursor.execute", sql, args)
            return self._inner.execute(sql, *args, **kwargs)

        def executemany(
            self, sql: str, *args: object, **kwargs: object
        ) -> sqlite3.Cursor:
            self._record("cursor.executemany", sql, args)
            return self._inner.executemany(sql, *args, **kwargs)

        def executescript(
            self, sql: str, *args: object, **kwargs: object
        ) -> sqlite3.Cursor:
            self._record("cursor.executescript", sql, args)
            return self._inner.executescript(sql, *args, **kwargs)

    class RecordingConnection(sqlite3.Connection):
        def _record(self, channel: str, sql: str, args: tuple[object, ...]) -> None:
            records.append((id(self), self.in_transaction, channel, sql, args))

        def execute(self, sql: str, *args: object, **kwargs: object) -> sqlite3.Cursor:
            self._record("execute", sql, args)
            return super().execute(sql, *args, **kwargs)

        def executemany(
            self, sql: str, *args: object, **kwargs: object
        ) -> sqlite3.Cursor:
            self._record("executemany", sql, args)
            return super().executemany(sql, *args, **kwargs)

        def executescript(
            self, sql: str, *args: object, **kwargs: object
        ) -> sqlite3.Cursor:
            self._record("executescript", sql, args)
            return super().executescript(sql, *args, **kwargs)

        def cursor(self, *args: object, **kwargs: object) -> RecordingCursor:
            return RecordingCursor(super().cursor(*args, **kwargs), self)

    def recording_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        kwargs["factory"] = RecordingConnection
        connection = real_connect(*args, **kwargs)
        connection_ids.append(id(connection))
        return connection

    with mock.patch.object(store_module.sqlite3, "connect", recording_connect):
        yield records, connection_ids


def _prose_without_fences(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _canonical_json(value: object) -> tuple[str, str]:
    text = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_sql(sql: str) -> str:
    return " ".join(sql.casefold().split())


def _application_statements(
    records: list[tuple[int, bool, str, str, tuple[object, ...]]],
) -> list[str]:
    statements = []
    for _, _, _, sql, _ in records:
        normalized = _normalized_sql(sql)
        if not normalized.startswith(("select", "insert", "update", "delete")):
            continue
        if "sqlite_" in normalized or normalized.startswith("select 1"):
            continue
        statements.append(normalized)
    return statements


def _request_statements(
    records: list[tuple[int, bool, str, str, tuple[object, ...]]],
) -> list[str]:
    return [
        sql
        for sql in _application_statements(records)
        if "requests"
        in {
            token.casefold()
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sql)
        }
    ]


def _flatten_values(value: object) -> typing.Iterator[object]:
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _flatten_values(child)
        return
    yield value


def _review_write_labels(
    records: list[tuple[int, bool, str, str, tuple[object, ...]]],
) -> list[str]:
    labels: list[str] = []
    for _, _, _, sql, arguments in records:
        normalized = _normalized_sql(sql)
        if normalized.startswith("update proposals set status_sequence"):
            labels.append("proposal.status_sequence")
        elif normalized.startswith("update proposals set"):
            labels.append("proposal.state")
        elif normalized.startswith("insert into examples"):
            labels.append("example.insert")
        elif normalized.startswith("update artifacts set"):
            labels.append("artifact.quarantine")
        elif normalized.startswith("update requests set"):
            labels.append("request.state")
        elif normalized.startswith("insert into events"):
            event_kind = next(
                (
                    value
                    for value in _flatten_values(arguments)
                    if isinstance(value, str)
                    and value
                    in {
                        "proposal.rejected",
                        "proposal.accepted",
                        "proposal.corrected",
                        "artifact.counterexample",
                    }
                ),
                None,
            )
            labels.append(f"event:{event_kind}")
    return labels


class ProposalBindingBatteryTests(unittest.TestCase):
    """Contract-derived pins. The author reads the contract, never the diff."""

    def _make_system(
        self,
        *,
        partition: str = "tenant_a",
        operation: str = "echo_1",
        clock: _Clock | None = None,
    ) -> tuple[System, Path, _Clock]:
        temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(temporary.cleanup)
        database = Path(temporary.name) / "cement.db"
        clock = _Clock() if clock is None else clock
        system = System(database, candidate_source=_Source(), clock_us=clock)
        system.register_operation(
            partition,
            operation,
            policy=CompilePolicy(2, 1, 0),
        )
        return system, database, clock

    def _promoted_conflict_fixture(
        self,
    ) -> tuple[System, Path, str, str]:
        system, database, _ = self._make_system()
        late_proposal_id = self._submit(
            system,
            input_value={"index": 11},
            output={"different": True},
        )
        for _ in range(2):
            pending = system.propose("tenant_a", "echo_1", {"index": 11})
            system.review(
                "tenant_a",
                pending,
                reviewer="operator",
                decision="accept",
            )
        artifact_id = system.compile("tenant_a", "echo_1").created[0]
        report = system.verify("tenant_a", artifact_id)
        system.promote(
            "tenant_a",
            artifact_id,
            scope_hash=report.scope_hash,
            promoted_by="operator",
        )
        return (
            system,
            database,
            late_proposal_id,
            artifact_id,
        )

    def _assert_quarantine_nonmatch(
        self,
        *,
        assignment: str,
        values: tuple[object, ...],
        expected_status: str = "promoted",
    ) -> None:
        system, database, proposal_id, artifact_id = self._promoted_conflict_fixture()
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("DROP TRIGGER artifacts_build_fields_immutable")
            connection.execute("DROP TRIGGER artifacts_status_lifecycle")
            connection.execute(
                f"UPDATE artifacts SET {assignment} WHERE id = ?",
                (*values, artifact_id),
            )
            connection.commit()
        result = system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="accept",
        )
        artifact = self._rows(
            database,
            "SELECT status FROM artifacts WHERE id = ?",
            (artifact_id,),
        )[0]
        counterexamples = self._rows(
            database,
            """
            SELECT sequence FROM events
            WHERE kind = 'artifact.counterexample' AND subject_id = ?
            """,
            (artifact_id,),
        )
        decision_event = self._rows(
            database,
            """
            SELECT payload_json FROM events
            WHERE kind = 'proposal.accepted' AND subject_id = ?
            """,
            (proposal_id,),
        )[0]
        self.assertEqual(result.status, "accepted")
        self.assertEqual(artifact["status"], expected_status)
        self.assertEqual(counterexamples, [])
        self.assertEqual(
            json.loads(decision_event["payload_json"])["suspended_artifact_ids"],
            [],
        )

    def _insert_pending_rows(
        self,
        system: System,
        *,
        count: int,
        prefix: str = "tail",
    ) -> list[str]:
        provenance_json, provenance_hash = _canonical_json({"source": prefix})
        request_rows: list[tuple[object, ...]] = []
        proposal_rows: list[tuple[object, ...]] = []
        input_hashes: list[str] = []
        for index in range(count):
            request_id = f"req_{prefix}_{index:05d}"
            proposal_id = f"prop_{prefix}_{index:05d}"
            input_json, input_hash = _canonical_json({prefix: index})
            output_json, output_hash = _canonical_json({"output": index})
            input_hashes.append(input_hash)
            request_rows.append(
                (
                    request_id,
                    "tenant_a",
                    "echo_1",
                    1,
                    input_json,
                    input_hash,
                    proposal_id,
                    20_000 + index,
                    20_000 + index,
                )
            )
            proposal_rows.append(
                (
                    proposal_id,
                    "tenant_a",
                    request_id,
                    output_json,
                    output_hash,
                    provenance_json,
                    provenance_hash,
                    20_000 + index,
                    index + 2,
                )
            )
        with system.store.transaction(write=True) as connection:
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

    def _submit(
        self,
        system: System,
        *,
        partition: str = "tenant_a",
        operation: str = "echo_1",
        input_value: object | None = None,
        output: object | None = None,
        provenance: object | None = None,
    ) -> str:
        return system.submit_proposal(
            partition,
            operation,
            {"index": 11} if input_value is None else input_value,
            candidate=Candidate(
                output={"answer": 22} if output is None else output,
                provenance=(
                    {"model": "battery", "rank": 13}
                    if provenance is None
                    else provenance
                ),
            ),
        )

    def _rows(self, database: Path, sql: str, parameters: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(database)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(sql, parameters).fetchall()

    def _run_cli(
        self,
        database: Path,
        *arguments: str,
        partition: str = "tenant_a",
    ) -> tuple[int, object | None, object | None, bytes]:
        from cement_runtime.cli import main

        stdout = _BinaryOutput()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(
                [
                    "--db",
                    str(database),
                    "--partition",
                    partition,
                    *arguments,
                ]
            )
        stdout_bytes = stdout.buffer.getvalue()
        stdout_value = json.loads(stdout_bytes) if stdout_bytes else None
        stderr_text = stderr.getvalue()
        stderr_value = json.loads(stderr_text) if stderr_text else None
        return status, stdout_value, stderr_value, stdout_bytes

    def _assert_request_identity_absent(self, value: object) -> None:
        if hasattr(value, "__dataclass_fields__"):
            mapping = {
                field.name: getattr(value, field.name)
                for field in fields(value)
            }
            self._assert_request_identity_absent(mapping)
            return
        if isinstance(value, dict):
            self.assertNotIn("request_id", value)
            for child in value.values():
                self._assert_request_identity_absent(child)
            return
        if isinstance(value, (list, tuple)):
            for child in value:
                self._assert_request_identity_absent(child)

    def test_b01_one_named_private_reader_and_at(self) -> None:
        """B01. one named private reader and at most one named private writer reach the request row

        Reproduction: lexically classify shipped request-table SQL owners and pin the
        sole read adapter plus the zero-or-one write-adapter boundary.
        """
        import ast
        import re
        from pathlib import Path

        import cement_runtime.system as system_module

        tree = ast.parse(Path(system_module.__file__).read_text(encoding="utf-8"))
        definitions: list[tuple[str, ast.AST]] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append((node.name, node))
            elif isinstance(node, ast.ClassDef):
                definitions.extend(
                    (child.name, child)
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
        owner_tokens = {
            name: {
                token.casefold()
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", item.value)
            }
            for name, node in definitions
        }
        adapters = {
            name: tokens
            for name, tokens in owner_tokens.items()
            if name in {"_proposal_bindings", "_write_proposal_request_status"}
            and "requests" in tokens
        }
        readers = {name for name, tokens in adapters.items() if "select" in tokens}
        writers = {
            name
            for name, tokens in adapters.items()
            if {"insert", "update", "delete"} & tokens
        }

        self.assertEqual({"_proposal_bindings"}, readers)
        self.assertLessEqual(len(writers), 1)
        self.assertEqual({"_write_proposal_request_status"}, writers)

    def test_b02_confinement_is_a_complement_assertion_over(self) -> None:
        """B02. confinement is a complement assertion over the shipped module, never a forbidden list

        Reproduction: derive every lexical owner of a literal ``requests`` SQL
        identifier from the shipped module and require set equality with the permit set.
        """
        import ast
        import re
        from pathlib import Path

        import cement_runtime.system as system_module

        tree = ast.parse(Path(system_module.__file__).read_text(encoding="utf-8"))
        definitions: list[tuple[str, ast.AST]] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append((node.name, node))
            elif isinstance(node, ast.ClassDef):
                definitions.extend(
                    (child.name, child)
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                definitions.extend(
                    (target.id, node.value)
                    for target in targets
                    if isinstance(target, ast.Name) and node.value is not None
                )
        owners = {
            name
            for name, node in definitions
            if "requests"
            in {
                token.casefold()
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", item.value)
            }
        }
        permitted = {
            "_persist_proposal",
            "handle",
            "_fail_generation",
            "request_status",
            "revise_operation",
            "_proposal_bindings",
            "_write_proposal_request_status",
        }

        self.assertSetEqual(permitted, owners)

    def test_b03_the_permitted_owner_set_is_exactly(self) -> None:
        """B03. the permitted owner set is exactly seven names and every freed path is absent from it

        Reproduction: census literal request-table owners, pin all seven permitted
        names, and separately reject every public or converter owner freed by M3.4.
        """
        import ast
        import re
        from pathlib import Path

        import cement_runtime.system as system_module

        tree = ast.parse(Path(system_module.__file__).read_text(encoding="utf-8"))
        definitions: list[tuple[str, ast.AST]] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append((node.name, node))
            elif isinstance(node, ast.ClassDef):
                definitions.extend(
                    (child.name, child)
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
        owners = {
            name
            for name, node in definitions
            if "requests"
            in {
                token.casefold()
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", item.value)
            }
        }
        permitted = {
            "_persist_proposal",
            "handle",
            "_fail_generation",
            "request_status",
            "revise_operation",
            "_proposal_bindings",
            "_write_proposal_request_status",
        }
        freed = {
            "get_proposal",
            "proposal",
            "proposals",
            "review",
            "function_report",
            "_proposal_record",
            "_proposal_content",
            "_proposal_binding",
        }

        self.assertEqual(7, len(permitted))
        self.assertTrue(permitted <= owners, permitted - owners)
        self.assertTrue(freed.isdisjoint(owners), freed & owners)

    def test_b04_the_walk_covers_module_level_constants(self) -> None:
        """B04. the walk covers module level constants, so hoisted SQL cannot leave the owner set

        Reproduction: run the lexical owner rule over a synthetic hoisted request SQL
        constant and require attribution to the assigned module-level name.
        """
        import ast
        import re

        tree = ast.parse(
            "REQUEST_ROWS = 'SELECT * FROM requests WHERE partition = ?'\n"
            "def clean():\n    return 'SELECT * FROM proposals'\n"
        )
        definitions: list[tuple[str, ast.AST]] = []
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                definitions.extend(
                    (target.id, node.value)
                    for target in targets
                    if isinstance(target, ast.Name) and node.value is not None
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append((node.name, node))
        owners = {
            name
            for name, node in definitions
            if "requests"
            in {
                token.casefold()
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", item.value)
            }
        }

        self.assertSetEqual({"REQUEST_ROWS"}, owners)

    def test_b05_matching_is_on_case_folded_whole(self) -> None:
        """B05. matching is on case folded whole SQL identifiers, so requests_scope is not a match

        Reproduction: feed uppercase ``REQUESTS`` and lowercase ``requests_scope``
        through the identifier tokenizer; only the whole uppercase identifier owns SQL.
        """
        import ast
        import re

        tree = ast.parse(
            "def upper():\n    return 'SELECT * FROM REQUESTS'\n"
            "def substring():\n    return 'SELECT * FROM requests_scope'\n"
        )
        owners = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if "requests"
            in {
                token.casefold()
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", item.value)
            }
        }

        self.assertSetEqual({"upper"}, owners)

    def test_b06_a04_tripwire_boundary_a_literal_hidden_1(self) -> None:
        """B06. A04 tripwire boundary: a literal hidden namer is rejected and runtime composition is not

        Reproduction: adjacent literal fragments become one AST constant, so the
        confinement census catches a deliberately hidden ``requests`` identifier.
        """
        from tests.test_proposal_binding import _definitions_naming_table

        literal_hidden = (
            "def leaked():\n"
            "    return 'SELECT id FROM ' 'reque' 'sts'\n"
        )

        self.assertSetEqual(
            {"leaked"},
            _definitions_naming_table(literal_hidden, "requests"),
        )

    def test_b06_a04_tripwire_boundary_a_literal_hidden_2(self) -> None:
        """B06. A04 tripwire boundary: a literal hidden namer is rejected and runtime composition is not

        Reproduction: split the table name across runtime ``+`` operands and prove
        the lexical census does not claim enforcement beyond literal constants.
        """
        from tests.test_proposal_binding import _definitions_naming_table

        runtime_composed = (
            "def leaked():\n"
            "    return 'SELECT id FROM ' + 'reque' + 'sts'\n"
        )

        self.assertSetEqual(
            set(),
            _definitions_naming_table(runtime_composed, "requests"),
        )

    def test_b07_proposalview_fields_are_exactly_id_partition(self) -> None:
        """B07. ProposalView fields are exactly id partition operation operation_revision input proposed_output provenance created_at_us

        Reproduction: compare the dataclass field tuple by equality, which pins order,
        membership, and the absence of the former request identity.
        """
        self.assertEqual(
            tuple(ProposalView.__dataclass_fields__),
            (
                "id",
                "partition",
                "operation",
                "operation_revision",
                "input",
                "proposed_output",
                "provenance",
                "created_at_us",
            ),
        )

    def test_b08_pendingproposalgap_fields_are_exactly_proposal_id(self) -> None:
        """B08. PendingProposalGap fields are exactly proposal_id operation_revision input_hash

        Reproduction: compare the report-gap dataclass field tuple exactly, so a
        retained request identifier or any reordered/defaulted projection fails.
        """
        self.assertEqual(
            tuple(PendingProposalGap.__dataclass_fields__),
            ("proposal_id", "operation_revision", "input_hash"),
        )

    def test_b09_review_returns_a_frozen_reviewresult_carrying(self) -> None:
        """B09. review returns a frozen ReviewResult carrying proposal_id status example_id output

        Reproduction: accept one real proposal, assert all four returned values and
        prove runtime field assignment raises ``FrozenInstanceError``.
        """
        system, _, _ = self._make_system()
        proposal_id = self._submit(system)

        result = system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="accept",
        )

        self.assertIs(type(result), ReviewResult)
        self.assertEqual(result.proposal_id, proposal_id)
        self.assertEqual(result.status, "accepted")
        self.assertIsInstance(result.example_id, str)
        self.assertEqual(result.output, {"answer": 22})
        with self.assertRaises(FrozenInstanceError):
            setattr(result, "status", "rejected")

    def test_b10_y20_path_matrix_request_identity_is_1(self) -> None:
        """B10. Y20 path matrix: request identity is absent from every read review report event CLI payload and export

        Reproduction: exercise every library proposal/read/review/report projection on
        one ledger and recursively reject a ``request_id`` key or dataclass field.
        """
        system, _, _ = self._make_system()
        first = self._submit(system, input_value={"index": 11})
        second = self._submit(system, input_value={"index": 12})

        values = (
            system.get_proposal("tenant_a", first),
            system.proposal("tenant_a", first),
            system.proposals("tenant_a", status="pending", limit=10),
            system.function_report("tenant_a", "echo_1", projection_limit=10),
            system.review(
                "tenant_a",
                first,
                reviewer="operator",
                decision="accept",
            ),
        )

        self.assertIn(second, [row["id"] for row in typing.cast(list[dict[str, object]], values[2])])
        for value in values:
            with self.subTest(surface=type(value).__name__):
                self._assert_request_identity_absent(value)

    def test_b10_y20_path_matrix_request_identity_is_2(self) -> None:
        """B10. Y20 path matrix: request identity is absent from every read review report event CLI payload and export

        Reproduction: assert CLI show/list/review and owned proposal events are
        request-free, then pin the request-free classes exported by the package.
        """
        system, database, _ = self._make_system()
        first = self._submit(system, input_value={"index": 11})
        second = self._submit(system, input_value={"index": 12})

        show_status, shown, _, _ = self._run_cli(
            database, "proposal", "show", first
        )
        list_status, listed, _, _ = self._run_cli(database, "proposal", "list")
        review_status, reviewed, _, _ = self._run_cli(
            database,
            "proposal",
            "review",
            first,
            "--reviewer",
            "operator",
            "--decision",
            "accept",
        )

        self.assertEqual((show_status, list_status, review_status), (0, 0, 0))
        self.assertIn(
            second,
            {
                row["id"]
                for row in typing.cast(list[dict[str, object]], listed)
            },
        )
        for label, payload in (
            ("show", shown),
            ("list", listed),
            ("review", reviewed),
            ("events", system.events("tenant_a")),
        ):
            with self.subTest(surface=label):
                self._assert_request_identity_absent(payload)

        exported = set(cement_runtime.__all__)
        self.assertTrue(
            {"ProposalView", "PendingProposalGap", "ReviewResult"} <= exported
        )
        self.assertNotIn(ReviewResult, typing.get_args(models_module.Outcome))
        for shape in (ProposalView, PendingProposalGap, ReviewResult):
            self.assertNotIn("request_id", shape.__dataclass_fields__)

    def test_b11_signature_and_resolved_hints_plus_slots(self) -> None:
        """B11. signature and resolved hints plus slots present and dict absent pin all three shapes at once

        Reproduction: constructor and review signatures, resolved hints, and slot-only
        runtime layout are asserted together so weakening any one shape fails this test.
        """
        expected_fields = {
            ProposalView: (
                "id",
                "partition",
                "operation",
                "operation_revision",
                "input",
                "proposed_output",
                "provenance",
                "created_at_us",
            ),
            PendingProposalGap: (
                "proposal_id",
                "operation_revision",
                "input_hash",
            ),
            ReviewResult: (
                "proposal_id",
                "status",
                "example_id",
                "output",
            ),
        }
        for shape, names in expected_fields.items():
            with self.subTest(shape=shape.__name__):
                signature = inspect.signature(shape)
                self.assertEqual(tuple(signature.parameters), names)
                self.assertTrue(
                    all(
                        parameter.default is inspect.Parameter.empty
                        for parameter in signature.parameters.values()
                    )
                )
                self.assertEqual(set(typing.get_type_hints(shape)), set(names))
                self.assertTrue(hasattr(shape, "__slots__"))
                self.assertNotIn("__dict__", dir(shape))

        review_signature = inspect.signature(System.review)
        self.assertEqual(
            {
                name: parameter.kind
                for name, parameter in review_signature.parameters.items()
            },
            {
                "self": inspect.Parameter.POSITIONAL_OR_KEYWORD,
                "partition": inspect.Parameter.POSITIONAL_OR_KEYWORD,
                "proposal_id": inspect.Parameter.POSITIONAL_OR_KEYWORD,
                "reviewer": inspect.Parameter.KEYWORD_ONLY,
                "decision": inspect.Parameter.KEYWORD_ONLY,
                "corrected_output": inspect.Parameter.KEYWORD_ONLY,
                "note": inspect.Parameter.KEYWORD_ONLY,
            },
        )
        self.assertIs(
            typing.get_type_hints(System.review)["return"],
            ReviewResult,
        )
        self.assertEqual(
            typing.get_type_hints(ReviewResult)["status"],
            typing.Literal["accepted", "corrected", "rejected"],
        )

    def test_b12_every_kept_projected_value_stays_byte(self) -> None:
        """B12. every kept projected value stays byte identical to baseline, with status the one named exemption

        Reproduction: compare every request/proposal JSON projection to its canonical
        stored bytes, then assert only status changes vocabulary on confirmation.
        """
        clock = _Clock(1_234_567)
        system, database, _ = self._make_system(clock=clock)
        input_value = {"text": "π", "n": 11}
        proposed_output = {"answer": "é"}
        provenance = {"model": "m", "rank": 13}
        proposal_id = self._submit(
            system,
            input_value=input_value,
            output=proposed_output,
            provenance=provenance,
        )
        view = system.get_proposal("tenant_a", proposal_id)
        record = system.proposal("tenant_a", proposal_id)
        stored = self._rows(
            database,
            """
            SELECT r.input_json, r.status AS request_status,
                   p.proposed_output_json, p.provenance_json, p.created_at_us
            FROM requests AS r
            JOIN proposals AS p ON p.request_id = r.id
            WHERE p.id = ?
            """,
            (proposal_id,),
        )[0]

        self.assertEqual(
            (
                view.id,
                view.partition,
                view.operation,
                view.operation_revision,
                view.created_at_us,
            ),
            (proposal_id, "tenant_a", "echo_1", 1, 1_234_567),
        )
        for public, raw in (
            (view.input, stored["input_json"]),
            (view.proposed_output, stored["proposed_output_json"]),
            (view.provenance, stored["provenance_json"]),
        ):
            self.assertEqual(
                json.dumps(
                    public,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                raw,
            )
        self.assertEqual(record["input"], input_value)
        self.assertEqual(record["proposed_output"], proposed_output)
        self.assertEqual(record["provenance"], provenance)
        self.assertEqual(record["status"], "pending")

        result = system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="accept",
        )
        confirmed = self._rows(
            database,
            """
            SELECT p.status, p.final_output_json, r.status AS request_status,
                   e.id AS example_id, e.output_json AS example_output_json
            FROM proposals AS p
            JOIN requests AS r ON r.id = p.request_id
            JOIN examples AS e ON e.proposal_id = p.id
            WHERE p.id = ?
            """,
            (proposal_id,),
        )[0]
        self.assertEqual(result.status, confirmed["status"])
        self.assertEqual(result.status, "accepted")
        self.assertEqual(confirmed["request_status"], "resolved")
        self.assertEqual(result.example_id, confirmed["example_id"])
        self.assertEqual(
            json.dumps(
                result.output,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            confirmed["final_output_json"],
        )
        self.assertEqual(
            confirmed["final_output_json"],
            confirmed["example_output_json"],
        )

    def test_b13_a07_no_growth_the_converters_lose(self) -> None:
        """B13. A07 no growth: the converters lose the request_id entry and gain no statement or span

        Reproduction: measure each shipped converter's AST body and source span
        against the budget below; any added responsibility fails.

        BUDGET RE-BASELINED, deliberately, and this is a TRIPWIRE the unit updates in the
        same commit that grows a converter. A07's no-growth reading was written against
        D24's fabricated-only premise, which section 15 then FALSIFIED: malformed JSON
        reaches these two converters on a real ledger, so both must translate it, and the
        translation is code. `_proposal_content` also took the binding parameter when the
        request row left the consumer-visible row. Budget moves 13/7 to 21/6 for
        `_proposal_content` and 28/5 to 31/6 for `_proposal_record`, which are the exact
        shipped measurements — an equality, not a ceiling, so growth AND shrinkage both
        fail and neither can pass unnoticed. The obligation A07 still enforces is that
        these converters gained no RESPONSIBILITY beyond the two named: no statement, no
        request access, no new call. B01 and B35 pin those directly.
        """
        source = Path(system_module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        converters = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in {"_proposal_record", "_proposal_content"}
        }
        self.assertSetEqual(
            {"_proposal_record", "_proposal_content"},
            set(converters),
        )
        baselines = {
            "_proposal_record": (31, 6),
            "_proposal_content": (21, 6),
        }
        for name, (span, statements) in baselines.items():
            node = converters[name]
            actual = (node.end_lineno - node.lineno + 1, len(node.body))
            with self.subTest(converter=name, metric="source span"):
                self.assertEqual(actual[0], span)
            with self.subTest(converter=name, metric="AST statements"):
                self.assertEqual(actual[1], statements)
        # The responsibility half of A07, which the size numbers only proxy: neither
        # converter names the request row and neither issues SQL. A converter that grew
        # by absorbing an access would pass a size ceiling and fail here.
        for name, node in converters.items():
            body = ast.get_source_segment(source, node) or ""
            with self.subTest(converter=name, metric="no request access"):
                self.assertNotIn("requests", body.casefold())
            with self.subTest(converter=name, metric="no SQL"):
                self.assertNotIn("select ", body.casefold())

    def test_b14_y12_export_census_alphabetical_all_position(self) -> None:
        """B14. Y12 export census: alphabetical __all__ position for ReviewResult and unchanged Outcome members

        Reproduction: pin ReviewResult's exact neighboring exports and the complete
        request-lifecycle Outcome union, with ReviewResult excluded from that union.
        """
        exports = list(cement_runtime.__all__)
        review_index = exports.index("ReviewResult")
        self.assertEqual(
            exports[review_index - 1 : review_index + 2],
            ["ReviewRequired", "ReviewResult", "StaleRevisionAnomaly"],
        )
        outcome_members = typing.get_args(models_module.Outcome)
        self.assertEqual(
            tuple(member.__name__ for member in outcome_members),
            (
                "Resolved",
                "ReviewRequired",
                "InProgress",
                "FallbackFailed",
                "Rejected",
                "ReconciliationRequired",
            ),
        )
        self.assertNotIn(ReviewResult, outcome_members)
        self.assertIs(cement_runtime.ReviewResult, ReviewResult)

    def test_b15_a08_write_order_the_exact_ordered_1(self) -> None:
        """B15. A08 write order: the exact ordered write subsequence per decision, including quarantine

        Reproduction: trace every SQLite execution channel and pin the complete
        reject, accept, and correct write subsequences rather than final state alone.
        """
        expected = {
            "reject": [
                "proposal.state",
                "request.state",
                "event:proposal.rejected",
                "proposal.status_sequence",
            ],
            "accept": [
                "proposal.state",
                "example.insert",
                "request.state",
                "event:proposal.accepted",
                "proposal.status_sequence",
            ],
            "correct": [
                "proposal.state",
                "example.insert",
                "request.state",
                "event:proposal.corrected",
                "proposal.status_sequence",
            ],
        }
        for decision, ordered_writes in expected.items():
            with self.subTest(decision=decision):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                with _record_sql() as (records, _):
                    system.review(
                        "tenant_a",
                        proposal_id,
                        reviewer="operator",
                        decision=decision,
                        **arguments,
                    )
                self.assertEqual(_review_write_labels(records), ordered_writes)
                self.assertTrue(
                    all(
                        in_transaction
                        for _, in_transaction, _, sql, _ in records
                        if _normalized_sql(sql).startswith(
                            ("insert", "update", "delete")
                        )
                    )
                )

    def test_b15_a08_write_order_the_exact_ordered_2(self) -> None:
        """B15. A08 write order: the exact ordered write subsequence per decision, including quarantine

        Reproduction: accept a conflicting late proposal against a promoted artifact
        and pin quarantine before the private write and final proposal event.
        """
        system, _, proposal_id, artifact_id = self._promoted_conflict_fixture()

        with _record_sql() as (records, _):
            result = system.review(
                "tenant_a",
                proposal_id,
                reviewer="operator",
                decision="accept",
            )

        self.assertEqual(result.status, "accepted")
        self.assertEqual(
            _review_write_labels(records),
            [
                "proposal.state",
                "example.insert",
                "artifact.quarantine",
                "event:artifact.counterexample",
                "request.state",
                "event:proposal.accepted",
                "proposal.status_sequence",
            ],
        )
        event_arguments = [
            tuple(_flatten_values(arguments))
            for _, _, _, sql, arguments in records
            if _normalized_sql(sql).startswith("insert into events")
        ]
        self.assertTrue(any(artifact_id in arguments for arguments in event_arguments))
        self.assertTrue(
            all(
                in_transaction
                for _, in_transaction, _, sql, _ in records
                if _normalized_sql(sql).startswith(
                    ("insert", "update", "delete")
                )
            )
        )

    def test_b16_reviewer_nonempty_control_free_256_bytes_1(self) -> None:
        """B16. reviewer nonempty control free 256 bytes, note empty allowed control free 2048 bytes, one shared now

        Reproduction: exercise adjacent accept/reject pairs for empty, control-byte,
        and UTF-8 byte-length reviewer boundaries against fresh pending proposals.
        """
        cases = (
            ("minimum accepted", "a", True),
            ("empty rejected", "", False),
            ("control-free accepted", "operator", True),
            ("control rejected", "operator\x00", False),
            ("256 bytes accepted", "é" * 128, True),
            ("257 bytes rejected", "é" * 128 + "a", False),
        )
        for label, reviewer, accepted in cases:
            with self.subTest(boundary=label):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                if accepted:
                    result = system.review(
                        "tenant_a",
                        proposal_id,
                        reviewer=reviewer,
                        decision="reject",
                    )
                    self.assertEqual(result.status, "rejected")
                else:
                    with self.assertRaises(ValidationError):
                        system.review(
                            "tenant_a",
                            proposal_id,
                            reviewer=reviewer,
                            decision="reject",
                        )
                    self.assertEqual(
                        system.proposal("tenant_a", proposal_id)["status"],
                        "pending",
                    )

    def test_b16_reviewer_nonempty_control_free_256_bytes_2(self) -> None:
        """B16. reviewer nonempty control free 256 bytes, note empty allowed control free 2048 bytes, one shared now

        Reproduction: exercise adjacent note boundaries, then compare every review
        provenance timestamp and receipt timestamp to one injected clock reading.
        """
        cases = (
            ("empty accepted", "", True),
            ("control-free accepted", "note", True),
            ("control rejected", "note\x00", False),
            ("2048 bytes accepted", "é" * 1024, True),
            ("2049 bytes rejected", "é" * 1024 + "a", False),
        )
        for label, note, accepted in cases:
            with self.subTest(boundary=label):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                if accepted:
                    result = system.review(
                        "tenant_a",
                        proposal_id,
                        reviewer="operator",
                        decision="reject",
                        note=note,
                    )
                    self.assertEqual(result.status, "rejected")
                else:
                    with self.assertRaises(ValidationError):
                        system.review(
                            "tenant_a",
                            proposal_id,
                            reviewer="operator",
                            decision="reject",
                            note=note,
                        )
                    self.assertEqual(
                        system.proposal("tenant_a", proposal_id)["status"],
                        "pending",
                    )

        clock = _Clock(1_000_000)
        system, database, _ = self._make_system(clock=clock)
        proposal_id = self._submit(system)
        clock.now_us = 9_876_543
        system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="accept",
            note="shared-now",
        )
        provenance = self._rows(
            database,
            """
            SELECT p.reviewed_at_us, r.updated_at_us, e.confirmed_at_us,
                   e.receipt_json, ev.created_at_us AS event_created_at_us
            FROM proposals AS p
            JOIN requests AS r ON r.id = p.request_id
            JOIN examples AS e ON e.proposal_id = p.id
            JOIN events AS ev
              ON ev.subject_id = p.id AND ev.kind = 'proposal.accepted'
            WHERE p.id = ?
            """,
            (proposal_id,),
        )[0]
        self.assertEqual(
            (
                provenance["reviewed_at_us"],
                provenance["updated_at_us"],
                provenance["confirmed_at_us"],
                provenance["event_created_at_us"],
                json.loads(provenance["receipt_json"])["confirmed_at_us"],
            ),
            (9_876_543,) * 5,
        )

    def test_b17_a09_exactly_one_example_on_accept(self) -> None:
        """B17. A09 exactly one example on accept and correct, none on reject, id equal to ReviewResult.example_id

        Reproduction: count proposal-owned examples before and after every decision,
        then repeat accept on the quarantine path and equate its sole id to the result.
        """
        for decision in ("accept", "correct", "reject"):
            with self.subTest(decision=decision, path="normal"):
                system, database, _ = self._make_system()
                proposal_id = self._submit(system)
                before = self._rows(
                    database,
                    "SELECT id FROM examples WHERE proposal_id = ?",
                    (proposal_id,),
                )
                arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                result = system.review(
                    "tenant_a",
                    proposal_id,
                    reviewer="operator",
                    decision=decision,
                    **arguments,
                )
                after = self._rows(
                    database,
                    "SELECT id FROM examples WHERE proposal_id = ?",
                    (proposal_id,),
                )
                expected_delta = 0 if decision == "reject" else 1
                self.assertEqual(len(after) - len(before), expected_delta)
                self.assertEqual(
                    result.example_id,
                    None if decision == "reject" else after[0]["id"],
                )

        system, database, proposal_id, artifact_id = self._promoted_conflict_fixture()
        before = self._rows(
            database,
            "SELECT id FROM examples WHERE proposal_id = ?",
            (proposal_id,),
        )
        result = system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="accept",
        )
        after = self._rows(
            database,
            "SELECT id FROM examples WHERE proposal_id = ?",
            (proposal_id,),
        )
        self.assertEqual((len(before), len(after)), (0, 1))
        self.assertEqual(result.example_id, after[0]["id"])
        self.assertEqual(
            self._rows(
                database,
                "SELECT status FROM artifacts WHERE id = ?",
                (artifact_id,),
            )[0]["status"],
            "suspended",
        )

    def test_b18_y7_quarantine_predicate_inventory_partition_operation_1(self) -> None:
        """B18. Y7 quarantine predicate inventory: partition operation revision input_hash input_json output promoted

        Reproduction: alter only partition, operation, or revision on an otherwise
        matching promoted artifact; each independent nonmatch must prevent quarantine.
        """
        cases = (
            ("partition", "partition = ?", ("tenantXa",)),
            ("operation", "operation = ?", ("echoX1",)),
            ("revision", "operation_revision = ?", (2,)),
        )
        for predicate, assignment, values in cases:
            with self.subTest(predicate=predicate):
                self._assert_quarantine_nonmatch(
                    assignment=assignment,
                    values=values,
                )

    def test_b18_y7_quarantine_predicate_inventory_partition_operation_2(self) -> None:
        """B18. Y7 quarantine predicate inventory: partition operation revision input_hash input_json output promoted

        Reproduction: independently break input hash, input canonical text, and
        unequal-output matching while every other quarantine predicate still matches.
        """
        equal_output = '{"different":true}'
        equal_output_hash = hashlib.sha256(equal_output.encode("utf-8")).hexdigest()
        cases = (
            ("input hash", "input_hash = ?", ("0" * 64,)),
            ("input JSON", "input_json = ?", ('{"index":12}',)),
            (
                "output unequal",
                "output_json = ?, output_hash = ?",
                (equal_output, equal_output_hash),
            ),
        )
        for predicate, assignment, values in cases:
            with self.subTest(predicate=predicate):
                self._assert_quarantine_nonmatch(
                    assignment=assignment,
                    values=values,
                )

    def test_b18_y7_quarantine_predicate_inventory_partition_operation_3(self) -> None:
        """B18. Y7 quarantine predicate inventory: partition operation revision input_hash input_json output promoted

        Reproduction: a verified-status nonmatch prevents quarantine, while reject on
        a fully matching promoted conflict performs zero example or quarantine work.
        """
        self._assert_quarantine_nonmatch(
            assignment="status = ?, promotion_hash = NULL",
            values=("verified",),
            expected_status="verified",
        )

        system, database, proposal_id, artifact_id = self._promoted_conflict_fixture()
        with _record_sql() as (records, _):
            result = system.review(
                "tenant_a",
                proposal_id,
                reviewer="operator",
                decision="reject",
            )
        self.assertEqual(result.status, "rejected")
        self.assertIsNone(result.example_id)
        self.assertEqual(
            self._rows(
                database,
                "SELECT status FROM artifacts WHERE id = ?",
                (artifact_id,),
            )[0]["status"],
            "promoted",
        )
        self.assertEqual(
            self._rows(
                database,
                "SELECT id FROM examples WHERE proposal_id = ?",
                (proposal_id,),
            ),
            [],
        )
        self.assertNotIn("artifact.quarantine", _review_write_labels(records))
        self.assertNotIn(
            "event:artifact.counterexample",
            _review_write_labels(records),
        )

    def test_b19_a10_status_sequence_equals_the_matching(self) -> None:
        """B19. A10 status_sequence equals the matching decision event sequence and rejects every intervening one

        Reproduction: bind all three normal decisions to their own event, then
        fabricate two live conflicts and reject both counterexample sequences.
        """
        for decision in ("reject", "accept", "correct"):
            with self.subTest(decision=decision, path="normal"):
                system, database, _ = self._make_system()
                proposal_id = self._submit(system)
                arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                result = system.review(
                    "tenant_a",
                    proposal_id,
                    reviewer="operator",
                    decision=decision,
                    **arguments,
                )
                proposal = self._rows(
                    database,
                    "SELECT status_sequence FROM proposals WHERE id = ?",
                    (proposal_id,),
                )[0]
                event = self._rows(
                    database,
                    """
                    SELECT sequence FROM events
                    WHERE subject_id = ? AND kind = ?
                    """,
                    (proposal_id, f"proposal.{result.status}"),
                )
                self.assertEqual(len(event), 1)
                self.assertEqual(proposal["status_sequence"], event[0]["sequence"])

        system, database, proposal_id, artifact_id = self._promoted_conflict_fixture()
        clone_id = "art_" + "f" * 32
        with closing(sqlite3.connect(database)) as connection:
            connection.row_factory = sqlite3.Row
            source = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            self.assertIsNotNone(source)
            connection.execute("DROP INDEX one_promoted_exact_scope")
            columns = [name for name in source.keys() if name != "sequence"]
            values = [source[name] for name in columns]
            values[columns.index("id")] = clone_id
            connection.execute(
                f"INSERT INTO artifacts({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                values,
            )
            connection.commit()

        result = system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="accept",
        )
        proposal = self._rows(
            database,
            "SELECT status_sequence FROM proposals WHERE id = ?",
            (proposal_id,),
        )[0]
        counterevents = self._rows(
            database,
            """
            SELECT sequence, subject_id FROM events
            WHERE kind = 'artifact.counterexample'
              AND json_extract(payload_json, '$.proposal_id') = ?
            ORDER BY sequence
            """,
            (proposal_id,),
        )
        decision_event = self._rows(
            database,
            """
            SELECT sequence, payload_json FROM events
            WHERE kind = 'proposal.accepted' AND subject_id = ?
            """,
            (proposal_id,),
        )[0]
        self.assertEqual(result.status, "accepted")
        self.assertEqual(
            {row["subject_id"] for row in counterevents},
            {artifact_id, clone_id},
        )
        self.assertEqual(proposal["status_sequence"], decision_event["sequence"])
        self.assertTrue(
            all(
                sequence < decision_event["sequence"]
                and sequence != proposal["status_sequence"]
                for sequence in (row["sequence"] for row in counterevents)
            )
        )
        self.assertEqual(
            set(json.loads(decision_event["payload_json"])["suspended_artifact_ids"]),
            {artifact_id, clone_id},
        )

    def test_b20_each_read_path_hides_everything_outside(self) -> None:
        """B20. each read path hides everything outside the scope it names, and proposals names no operation

        Reproduction: cross two partitions and two operations, reject foreign IDs,
        keep reports operation-scoped, and require the partition feed to include both operations.
        """
        system, _, _ = self._make_system()
        system.register_operation(
            "tenant_a", "other_2", policy=CompilePolicy(2, 1, 0)
        )
        system.register_operation(
            "tenant_b", "echo_1", policy=CompilePolicy(2, 1, 0)
        )
        primary = self._submit(system)
        other_operation = self._submit(system, operation="other_2")
        other_partition = self._submit(system, partition="tenant_b")

        tenant_feed = system.proposals("tenant_a", status="pending", limit=10)
        self.assertEqual(
            {row["id"] for row in tenant_feed},
            {primary, other_operation},
        )
        self.assertEqual(
            {row["operation"] for row in tenant_feed},
            {"echo_1", "other_2"},
        )
        self.assertNotIn(other_partition, {row["id"] for row in tenant_feed})

        for path in ("get_proposal", "proposal"):
            with self.subTest(path=path):
                with self.assertRaises(NotFoundError):
                    getattr(system, path)("tenant_b", primary)
        with self.assertRaises(NotFoundError):
            system.review(
                "tenant_b",
                primary,
                reviewer="operator",
                decision="reject",
            )

        reports = {
            (partition, operation): {
                gap.proposal_id
                for gap in system.function_report(
                    partition,
                    operation,
                    projection_limit=10,
                ).operation_now.pending_proposals
            }
            for partition, operation in (
                ("tenant_a", "echo_1"),
                ("tenant_a", "other_2"),
                ("tenant_b", "echo_1"),
            )
        }
        self.assertEqual(reports[("tenant_a", "echo_1")], {primary})
        self.assertEqual(reports[("tenant_a", "other_2")], {other_operation})
        self.assertEqual(reports[("tenant_b", "echo_1")], {other_partition})

    def test_b21_underscore_colliders_and_case_variants_keep_1(self) -> None:
        """B21. underscore colliders and case variants keep equals from weakening to LIKE on partition and operation

        Reproduction: place ``tenant_a`` beside wildcard collider ``tenantXa`` and
        ASCII case variant ``TENANT_A``; every partition-scoped path must stay exact.
        """
        system, _, _ = self._make_system()
        for partition in ("tenantXa", "TENANT_A"):
            system.register_operation(
                partition,
                "echo_1",
                policy=CompilePolicy(2, 1, 0),
            )
        proposals = {
            partition: self._submit(system, partition=partition)
            for partition in ("tenant_a", "tenantXa", "TENANT_A")
        }

        for partition, expected_id in proposals.items():
            with self.subTest(partition=partition):
                feed = system.proposals(partition, status="pending", limit=10)
                self.assertEqual([row["id"] for row in feed], [expected_id])
                gaps = system.function_report(
                    partition,
                    "echo_1",
                    projection_limit=10,
                ).operation_now.pending_proposals
                self.assertEqual([gap.proposal_id for gap in gaps], [expected_id])
                self.assertEqual(
                    system.get_proposal(partition, expected_id).partition,
                    partition,
                )

        for foreign_partition in ("tenantXa", "TENANT_A"):
            with self.subTest(foreign_partition=foreign_partition):
                with self.assertRaises(NotFoundError):
                    system.get_proposal(
                        foreign_partition,
                        proposals["tenant_a"],
                    )
                with self.assertRaises(NotFoundError):
                    system.proposal(
                        foreign_partition,
                        proposals["tenant_a"],
                    )

    def test_b21_underscore_colliders_and_case_variants_keep_2(self) -> None:
        """B21. underscore colliders and case variants keep equals from weakening to LIKE on partition and operation

        Reproduction: place ``echo_1`` beside wildcard collider ``echoX1`` and
        ASCII case variant ``ECHO_1``; operation reports must select exactly one.
        """
        system, _, _ = self._make_system()
        for operation in ("echoX1", "ECHO_1"):
            system.register_operation(
                "tenant_a",
                operation,
                policy=CompilePolicy(2, 1, 0),
            )
        proposals = {
            operation: self._submit(system, operation=operation)
            for operation in ("echo_1", "echoX1", "ECHO_1")
        }

        feed = system.proposals("tenant_a", status="pending", limit=10)
        self.assertEqual({row["id"] for row in feed}, set(proposals.values()))
        self.assertEqual({row["operation"] for row in feed}, set(proposals))
        for operation, expected_id in proposals.items():
            with self.subTest(operation=operation):
                self.assertEqual(
                    system.get_proposal("tenant_a", expected_id).operation,
                    operation,
                )
                gaps = system.function_report(
                    "tenant_a",
                    operation,
                    projection_limit=10,
                ).operation_now.pending_proposals
                self.assertEqual([gap.proposal_id for gap in gaps], [expected_id])

    def test_b22_exact_pending_counts_bounded_detail_and_1(self) -> None:
        """B22. exact pending counts, bounded detail, and a tail past 10000 that is counted and validated

        Reproduction: insert 10,001 pending bindings, then pin the exact count and
        the independently bounded first and maximum detail projections.
        """
        system, _, _ = self._make_system()
        input_hashes = self._insert_pending_rows(system, count=10_001)

        first = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        ).operation_now
        self.assertEqual(first.pending_proposal_count, 10_001)
        self.assertEqual(
            first.pending_proposals,
            (
                PendingProposalGap(
                    proposal_id="prop_tail_00000",
                    operation_revision=1,
                    input_hash=input_hashes[0],
                ),
            ),
        )

        maximum = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=10_000,
        ).operation_now
        self.assertEqual(maximum.pending_proposal_count, 10_001)
        self.assertEqual(len(maximum.pending_proposals), 10_000)
        self.assertEqual(
            maximum.pending_proposals[0].proposal_id,
            "prop_tail_00000",
        )
        self.assertEqual(
            maximum.pending_proposals[-1].proposal_id,
            "prop_tail_09999",
        )
        self.assertGreater(
            maximum.pending_proposal_count,
            len(maximum.pending_proposals),
        )

    def test_b22_exact_pending_counts_bounded_detail_and_2(self) -> None:
        """B22. exact pending counts, bounded detail, and a tail past 10000 that is counted and validated

        Reproduction: prove row 10,001 contributes to the count, corrupt only that
        schema-valid TEXT binding, and require the count to survive while the content
        stays unreachable.

        MAIN RULED THE UNDERDETERMINATION section 15 left open. "Counted and validated"
        governs BINDING EXISTENCE, which the pending count statement proves over every
        matching row with no cap. JSON CONTENT validation is scoped to RETURNED DETAIL.
        Full-tail content validation, a capped detail projection and bounded
        materialization cannot all hold at once, and 10,001 JSON parses to serve a
        one-item page is the cost the report exists to bound. `projection_limit` is
        capped at 10,000 (`system.py`, `_bounded_int(..., maximum=10_000)`), so row
        10,001's CONTENT is unreachable at every legal limit — that is a stated bound,
        not an accident, and B28 owns the split it implies.
        """
        system, database, _ = self._make_system()
        self._insert_pending_rows(system, count=10_001)
        before = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        ).operation_now
        self.assertEqual(before.pending_proposal_count, 10_001)
        self.assertEqual(len(before.pending_proposals), 1)

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "UPDATE requests SET input_json = ? WHERE id = ?",
                ("{", "req_tail_10000"),
            )
            connection.commit()

        after = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        ).operation_now
        self.assertEqual(after.pending_proposal_count, 10_001)
        self.assertEqual(len(after.pending_proposals), 1)
        # The corrupt row is still COUNTED, so the report does not silently shrink, and
        # its binding is still proved to exist. Raising the limit to its ceiling cannot
        # reach the row, so no legal call parses that content.
        maximum = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=10_000,
        ).operation_now
        self.assertEqual(maximum.pending_proposal_count, 10_001)
        self.assertEqual(len(maximum.pending_proposals), 10_000)
        with self.assertRaises(ValidationError):
            system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=10_001,
            )

    def test_b23_a13_order_preserved_not_fixed_the(self) -> None:
        """B23. A13 order preserved not fixed: the exact lexicographic p.id page at two projection limits

        Reproduction: insert twelve proposals in reverse creation order and require
        the baseline lexicographic id prefix at limits three and eleven.
        """
        system, _, _ = self._make_system()
        provenance_json, provenance_hash = _canonical_json({"source": "order"})
        request_rows: list[tuple[object, ...]] = []
        proposal_rows: list[tuple[object, ...]] = []
        for insertion, index in enumerate(range(11, -1, -1)):
            request_id = f"req_order_{index:02d}"
            proposal_id = f"prop_order_{index:02d}"
            input_json, input_hash = _canonical_json({"index": index})
            output_json, output_hash = _canonical_json({"output": index})
            request_rows.append(
                (
                    request_id,
                    "tenant_a",
                    "echo_1",
                    1,
                    input_json,
                    input_hash,
                    proposal_id,
                    30_000 + insertion,
                    30_000 + insertion,
                )
            )
            proposal_rows.append(
                (
                    proposal_id,
                    "tenant_a",
                    request_id,
                    output_json,
                    output_hash,
                    provenance_json,
                    provenance_hash,
                    30_000 + insertion,
                    insertion + 2,
                )
            )
        with system.store.transaction(write=True) as connection:
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

        lexicographic = [f"prop_order_{index:02d}" for index in range(12)]
        for limit in (3, 11):
            with self.subTest(projection_limit=limit):
                projected = system.function_report(
                    "tenant_a",
                    "echo_1",
                    projection_limit=limit,
                ).operation_now.pending_proposals
                self.assertEqual(
                    [gap.proposal_id for gap in projected],
                    lexicographic[:limit],
                )

    def test_b24_y14_scalar_inventory_nullable_versus_non_1(self) -> None:
        """B24. Y14 scalar inventory: nullable versus non null fields, real ledger malformed JSON, middle and last

        Reproduction: derive nullability for every converted proposal/request/operation
        scalar, exercise all five real NULL guards, and send malformed input JSON through all five paths.
        """
        system, database, _ = self._make_system()
        proposal_id = self._submit(system)
        converted = {
            "proposals": {
                "id",
                "partition",
                "request_id",
                "proposed_output_json",
                "proposed_output_hash",
                "provenance_json",
                "provenance_hash",
                "status",
                "final_output_json",
                "final_output_hash",
                "reviewer",
                "review_note",
                "created_at_us",
                "reviewed_at_us",
                "status_sequence",
            },
            "requests": {
                "id",
                "partition",
                "operation",
                "operation_revision",
                "input_json",
                "input_hash",
                "status",
                "proposal_id",
            },
            "operations": {"revision"},
            "aggregate": {"pending_count"},
        }
        nullable = {
            "final_output_json",
            "final_output_hash",
            "reviewer",
            "review_note",
            "reviewed_at_us",
        }
        proposal_info = {
            row["name"]: bool(row["notnull"])
            for row in self._rows(database, "PRAGMA table_info(proposals)")
        }
        request_info = {
            row["name"]: bool(row["notnull"])
            for row in self._rows(database, "PRAGMA table_info(requests)")
        }
        operation_info = {
            row["name"]: bool(row["notnull"])
            for row in self._rows(database, "PRAGMA table_info(operations)")
        }
        self.assertSetEqual(set(proposal_info), converted["proposals"])
        self.assertSetEqual(
            {name for name in converted["proposals"] if not proposal_info[name]},
            nullable,
        )
        self.assertTrue(
            all(
                request_info[name]
                for name in converted["requests"] - {"proposal_id"}
            )
        )
        self.assertFalse(request_info["proposal_id"])
        self.assertTrue(operation_info["revision"])

        pending = system.proposal("tenant_a", proposal_id)
        self.assertEqual(
            {
                "final_output_json": pending["final_output"],
                "final_output_hash": self._rows(
                    database,
                    "SELECT final_output_hash FROM proposals WHERE id = ?",
                    (proposal_id,),
                )[0]["final_output_hash"],
                "reviewer": pending["reviewer"],
                "review_note": pending["review_note"],
                "reviewed_at_us": pending["reviewed_at_us"],
            },
            {name: None for name in nullable},
        )
        self.assertEqual(
            system.proposals("tenant_a", status="pending", limit=10)[0][
                "review_note"
            ],
            None,
        )

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "UPDATE requests SET input_json = ? WHERE proposal_id = ?",
                ("{", proposal_id),
            )
            connection.commit()
        paths: tuple[tuple[str, typing.Callable[[], object]], ...] = (
            ("get_proposal", lambda: system.get_proposal("tenant_a", proposal_id)),
            ("proposal", lambda: system.proposal("tenant_a", proposal_id)),
            (
                "proposals",
                lambda: system.proposals("tenant_a", status="pending", limit=10),
            ),
            (
                "function_report",
                lambda: system.function_report(
                    "tenant_a", "echo_1", projection_limit=10
                ),
            ),
            (
                "review",
                lambda: system.review(
                    "tenant_a",
                    proposal_id,
                    reviewer="operator",
                    decision="accept",
                ),
            ),
        )
        for path, call in paths:
            with self.subTest(path=path):
                with self.assertRaises(Exception) as raised:
                    call()
                self.assertIs(type(raised.exception), IntegrityError)

    def test_b24_y14_scalar_inventory_nullable_versus_non_2(self) -> None:
        """B24. Y14 scalar inventory: nullable versus non null fields, real ledger malformed JSON, middle and last

        Reproduction: corrupt schema-valid TEXT in the middle and last of three
        bindings independently for both loop-owned converters and require IntegrityError.
        """
        for reader in ("proposals", "function_report"):
            for position in (1, 2):
                with self.subTest(reader=reader, position=position):
                    system, database, _ = self._make_system()
                    for index in (11, 12, 13):
                        self._submit(system, input_value={"index": index})
                    ordered = self._rows(
                        database,
                        """
                        SELECT p.id AS proposal_id, r.id AS request_id
                        FROM proposals AS p
                        JOIN requests AS r ON r.id = p.request_id
                        ORDER BY p.id
                        """,
                    )
                    self.assertEqual(len(ordered), 3)
                    with closing(sqlite3.connect(database)) as connection:
                        connection.execute(
                            "UPDATE requests SET input_json = ? WHERE id = ?",
                            ("{", ordered[position]["request_id"]),
                        )
                        connection.commit()
                    if reader == "proposals":
                        call = lambda: system.proposals(
                            "tenant_a",
                            status="pending",
                            limit=10,
                        )
                    else:
                        call = lambda: system.function_report(
                            "tenant_a",
                            "echo_1",
                            projection_limit=10,
                        )
                    with self.assertRaises(Exception) as raised:
                        call()
                    self.assertIs(type(raised.exception), IntegrityError)

    def test_b25_prose_alone_teaches_reviewresult_and_the(self) -> None:
        """B25. prose alone teaches ReviewResult and the removal of request identity from proposal reads

        Reproduction: strip every fenced block, isolate the README review section,
        and require the return type, field meanings, and request-free read methods in prose.
        """
        root = Path(__file__).resolve().parents[1]
        prose = _prose_without_fences(
            (root / "README.md").read_text(encoding="utf-8")
        )
        review_section = prose.split("### Reviewing a proposal", 1)[1].split(
            "## Request outcomes", 1
        )[0]
        normalized = " ".join(review_section.split())

        self.assertIn("`System.review` returns a `ReviewResult`", normalized)
        self.assertIn("four fields and no request identity", normalized)
        for field, meaning in (
            ("`proposal_id`", "reviewed proposal"),
            ("`status`", "proposal's own status"),
            ("`example_id`", "confirmed example"),
            ("`output`", "confirmed output"),
        ):
            with self.subTest(field=field):
                self.assertIn(field, normalized)
                self.assertIn(meaning, normalized)
        for method in (
            "`System.get_proposal`",
            "`System.proposal`",
            "`System.proposals`",
            "`function_report`",
        ):
            self.assertIn(method, normalized)
        self.assertIn("expose no request identifier", normalized)

    def test_b26_a15_prose_outside_code_fences_names(self) -> None:
        """B26. A15 prose outside code fences names four fields, three statuses, reject nulls, request free scope

        Reproduction: strip all public Markdown fences, census the ruled payload
        vocabulary, and require positive request-free claims for reads, review, reports, and events.
        """
        root = Path(__file__).resolve().parents[1]
        surfaces = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
        prose = "\n".join(
            _prose_without_fences(path.read_text(encoding="utf-8"))
            for path in surfaces
        )
        folded = " ".join(prose.casefold().split())

        for token in (
            "proposal_id",
            "status",
            "example_id",
            "output",
            "accepted",
            "corrected",
            "rejected",
        ):
            with self.subTest(token=token):
                self.assertIn(token, folded)
        self.assertRegex(
            folded,
            r"example_id.{0,180}(?:null|none).{0,8}after a rejection",
        )
        self.assertRegex(
            folded,
            r"output.{0,220}(?:null|none).{0,8}after a rejection",
        )
        self.assertRegex(
            folded,
            r"reviewresult.{0,120}no request identity",
        )
        self.assertIn(
            "no request identifier, and neither does any proposal read or report value",
            folded,
        )
        event_claims = [
            sentence
            for sentence in re.split(r"(?<=[.!?])\s+", folded)
            if "event payload" in sentence
            and "request" in sentence
            and any(word in sentence for word in ("no ", "omit", "request-free"))
        ]
        self.assertTrue(
            event_claims,
            "public prose has no positive request-free event-payload claim",
        )

    def test_b27_no_public_surface_retains_the_unqualified(self) -> None:
        """B27. no public surface retains the unqualified form of a claim the contract qualified

        Reproduction: census public prose for the withdrawn materialization, performed-swap,
        information-preservation, event, and system-wide status formulations, then pin the status qualifier.
        """
        root = Path(__file__).resolve().parents[1]
        prose = "\n".join(
            _prose_without_fences(path.read_text(encoding="utf-8"))
            for path in [root / "README.md", *sorted((root / "docs").glob("*.md"))]
        ).casefold()
        forbidden = (
            r"no consumer (?:of the ledger )?loses information",
            r"adapter survives the (?:schema )?swap untouched",
            r"subquery materializes (?:the )?(?:whole|entire) partition",
            r"all proposal event payloads (?:omit|contain no|carry no) request",
            r"review changed (?:the )?(?:system|request) status to accepted",
        )
        for pattern in forbidden:
            with self.subTest(unqualified=pattern):
                self.assertNotRegex(prose, pattern)

        readme = _prose_without_fences(
            (root / "README.md").read_text(encoding="utf-8")
        )
        normalized = " ".join(readme.split())
        self.assertIn(
            "The older `System.request_status` and `System.handle` lifecycle values still report `resolved`",
            normalized,
        )
        self.assertIn("Cement does not translate one vocabulary into the other", normalized)

    def test_b28_x32_a_binding_missing_beyond_the(self) -> None:
        """B28. X32 a binding missing beyond the 10000 row detail cap still raises IntegrityError

        Reproduction: prove 10,001 pending proposals, orphan only row 10,001,
        request one detail row, and require fail-closed validation beyond the cap.
        """
        system, database, _ = self._make_system()
        self._insert_pending_rows(system, count=10_001)
        before = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        ).operation_now
        self.assertEqual(before.pending_proposal_count, 10_001)
        self.assertEqual(len(before.pending_proposals), 1)

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "DELETE FROM requests WHERE id = ?",
                ("req_tail_10000",),
            )
            connection.commit()

        with self.assertRaises(IntegrityError):
            system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=1,
            )

    def test_b28_x32_a_binding_missing_beyond_the_2(self) -> None:
        """B28. X32 past the 10000 row detail cap a MISSING BINDING raises at any limit, while malformed JSON raises only once the cap reaches it

        Reproduction: the other half of the split. Corrupt one row's stored JSON and
        show the report succeeds while that row sits outside the projection, then
        raises once the projection includes it.

        The two halves are governed by DIFFERENT statements and that is the whole
        ruling. Binding EXISTENCE is proved by the pending count statement, which
        carries no cap, so a missing binding fails closed at any limit — the sibling
        test pins that at row 10,001. Stored CONTENT is parsed only for rows the
        detail statement returns, so a malformed row is inert until the cap reaches
        it. Both behaviours are conforming; reading section 15's "counted and
        validated" as one undifferentiated obligation is what makes them look
        contradictory.
        """
        system, database, _ = self._make_system()
        self._insert_pending_rows(system, count=3, prefix="split")

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "UPDATE requests SET input_json = ? WHERE id = ?",
                ("{", "req_split_00002"),
            )
            connection.commit()

        outside = system.function_report(
            "tenant_a",
            "echo_1",
            projection_limit=1,
        ).operation_now
        self.assertEqual(outside.pending_proposal_count, 3)
        self.assertEqual(len(outside.pending_proposals), 1)

        with self.assertRaises(IntegrityError):
            system.function_report(
                "tenant_a",
                "echo_1",
                projection_limit=3,
            )

    def test_b29_an_absent_proposal_is_notfounderror_and_1(self) -> None:
        """B29. an absent proposal is NotFoundError and an absent or mismatched binding is IntegrityError

        Reproduction: call every singular public path with one valid but absent
        proposal id and assert the exact NotFoundError class rather than a binding fault.
        """
        system, _, _ = self._make_system()
        missing = "prop_" + "0" * 32
        paths: tuple[tuple[str, typing.Callable[[], object]], ...] = (
            ("get_proposal", lambda: system.get_proposal("tenant_a", missing)),
            ("proposal", lambda: system.proposal("tenant_a", missing)),
            (
                "review",
                lambda: system.review(
                    "tenant_a",
                    missing,
                    reviewer="operator",
                    decision="reject",
                ),
            ),
        )
        for path, call in paths:
            with self.subTest(path=path):
                with self.assertRaises(Exception) as raised:
                    call()
                self.assertIs(type(raised.exception), NotFoundError)

    def test_b29_an_absent_proposal_is_notfounderror_and_2(self) -> None:
        """B29. an absent proposal is NotFoundError and an absent or mismatched binding is IntegrityError

        Reproduction: retain a real proposal while deleting or rebinding only its
        private request row; every singular and bulk path must raise exact IntegrityError.
        """
        for corruption in ("absent", "mismatched"):
            with self.subTest(corruption=corruption):
                system, database, _ = self._make_system()
                proposal_id = self._submit(system)
                with closing(sqlite3.connect(database)) as connection:
                    if corruption == "absent":
                        connection.execute(
                            "DELETE FROM requests WHERE proposal_id = ?",
                            (proposal_id,),
                        )
                    else:
                        connection.execute(
                            "UPDATE requests SET proposal_id = ? WHERE proposal_id = ?",
                            ("prop_" + "f" * 32, proposal_id),
                        )
                    connection.commit()
                paths: tuple[tuple[str, typing.Callable[[], object]], ...] = (
                    (
                        "get_proposal",
                        lambda: system.get_proposal("tenant_a", proposal_id),
                    ),
                    ("proposal", lambda: system.proposal("tenant_a", proposal_id)),
                    (
                        "proposals",
                        lambda: system.proposals(
                            "tenant_a", status="pending", limit=10
                        ),
                    ),
                    (
                        "review",
                        lambda: system.review(
                            "tenant_a",
                            proposal_id,
                            reviewer="operator",
                            decision="reject",
                        ),
                    ),
                    (
                        "function_report",
                        lambda: system.function_report(
                            "tenant_a", "echo_1", projection_limit=10
                        ),
                    ),
                )
                for path, call in paths:
                    with self.subTest(corruption=corruption, path=path):
                        with self.assertRaises(Exception) as raised:
                            call()
                        self.assertIs(type(raised.exception), IntegrityError)

    def test_b30_the_six_owned_event_payloads_are_1(self) -> None:
        """B30. the six owned event payloads are request free and the handle route payload is unchanged

        Reproduction: emit both direct creations, all three review decisions, and
        one counterexample; pin every exact owned payload and recursively reject request identity.
        """
        system, database, _ = self._make_system()
        submitted = self._submit(system, input_value={"index": 11})
        proposed = system.propose("tenant_a", "echo_1", {"index": 12})
        rejected = self._submit(system, input_value={"index": 13})
        accepted = self._submit(system, input_value={"index": 14})
        corrected = self._submit(system, input_value={"index": 15})
        reject_result = system.review(
            "tenant_a", rejected, reviewer="operator", decision="reject"
        )
        accept_result = system.review(
            "tenant_a", accepted, reviewer="operator", decision="accept"
        )
        correct_result = system.review(
            "tenant_a",
            corrected,
            reviewer="operator",
            decision="correct",
            corrected_output={"answer": 99},
        )
        rows = self._rows(
            database,
            "SELECT kind, subject_id, payload_json FROM events ORDER BY sequence",
        )
        selected = [
            row
            for row in rows
            if (row["kind"] == "proposal.created" and row["subject_id"] in {submitted, proposed})
            or row["subject_id"] in {rejected, accepted, corrected}
            and row["kind"] != "proposal.created"
        ]

        quarantine_system, quarantine_database, quarantine_proposal, artifact_id = (
            self._promoted_conflict_fixture()
        )
        quarantine_result = quarantine_system.review(
            "tenant_a",
            quarantine_proposal,
            reviewer="operator",
            decision="accept",
        )
        counterexample = self._rows(
            quarantine_database,
            """
            SELECT kind, subject_id, payload_json FROM events
            WHERE kind = 'artifact.counterexample' AND subject_id = ?
            """,
            (artifact_id,),
        )[0]
        selected.append(counterexample)
        self.assertEqual(len(selected), 6)

        payloads = {
            (row["kind"], row["subject_id"]): json.loads(row["payload_json"])
            for row in selected
        }
        self.assertEqual(payloads[("proposal.created", submitted)], {})
        self.assertEqual(payloads[("proposal.created", proposed)], {})
        self.assertEqual(
            payloads[("proposal.rejected", rejected)],
            {"reviewer": "operator"},
        )
        self.assertIsNone(reject_result.example_id)
        for kind, proposal_id, result in (
            ("proposal.accepted", accepted, accept_result),
            ("proposal.corrected", corrected, correct_result),
        ):
            payload = payloads[(kind, proposal_id)]
            self.assertEqual(
                set(payload),
                {
                    "example_id",
                    "receipt_hash",
                    "reviewer",
                    "suspended_artifact_ids",
                },
            )
            self.assertEqual(payload["example_id"], result.example_id)
            self.assertEqual(payload["reviewer"], "operator")
            self.assertEqual(payload["suspended_artifact_ids"], [])
        self.assertEqual(
            payloads[("artifact.counterexample", artifact_id)],
            {
                "example_id": quarantine_result.example_id,
                "proposal_id": quarantine_proposal,
            },
        )
        for payload in payloads.values():
            self._assert_request_identity_absent(payload)

    def test_b30_the_six_owned_event_payloads_are_2(self) -> None:
        """B30. the six owned event payloads are request free and the handle route payload is unchanged

        Reproduction: drive the exempt handle creation route and pin its exact
        request-id payload, proposal subject, and status_sequence binding unchanged.
        """
        system, database, _ = self._make_system()
        request_id = "handle-route-11"
        outcome = system.handle(
            "tenant_a",
            "echo_1",
            {"index": 11},
            request_id=request_id,
        )
        self.assertIsInstance(outcome, ReviewRequired)
        proposal_id = typing.cast(ReviewRequired, outcome).proposal_id
        event = self._rows(
            database,
            """
            SELECT sequence, subject_type, subject_id, payload_json
            FROM events
            WHERE kind = 'proposal.created' AND subject_id = ?
            """,
            (proposal_id,),
        )[0]
        proposal = self._rows(
            database,
            "SELECT status_sequence FROM proposals WHERE id = ?",
            (proposal_id,),
        )[0]

        self.assertEqual(event["subject_type"], "proposal")
        self.assertEqual(event["subject_id"], proposal_id)
        self.assertEqual(json.loads(event["payload_json"]), {"request_id": request_id})
        self.assertEqual(proposal["status_sequence"], event["sequence"])

    def test_b31_the_exact_cli_triples_exit_0(self) -> None:
        """B31. the exact CLI triples: exit 0 and the exact sorted key set and values for all three decisions

        Reproduction: review three real proposals through the CLI and compare exit,
        parsed values, key order, nulls, and pretty-printed bytes for each decision.
        """
        system, database, _ = self._make_system()
        proposal_ids = {
            decision: self._submit(system, input_value={"decision": decision})
            for decision in ("accept", "correct", "reject")
        }
        for decision, expected_status, expected_output in (
            ("accept", "accepted", {"answer": 22}),
            ("correct", "corrected", {"answer": 99}),
            ("reject", "rejected", None),
        ):
            with self.subTest(decision=decision):
                arguments = [
                    "proposal",
                    "review",
                    proposal_ids[decision],
                    "--reviewer",
                    "operator",
                    "--decision",
                    decision,
                ]
                if decision == "correct":
                    arguments.extend(("--output", '{"answer":99}'))
                status, value, error, stdout_bytes = self._run_cli(
                    database,
                    *arguments,
                )
                self.assertEqual(status, 0)
                self.assertIsNone(error)
                self.assertIsInstance(value, dict)
                payload = typing.cast(dict[str, object], value)
                self.assertEqual(
                    list(payload),
                    ["example_id", "output", "proposal_id", "status"],
                )
                self.assertEqual(payload["proposal_id"], proposal_ids[decision])
                self.assertEqual(payload["status"], expected_status)
                self.assertEqual(payload["output"], expected_output)
                if decision == "reject":
                    self.assertIsNone(payload["example_id"])
                else:
                    self.assertIsInstance(payload["example_id"], str)
                expected = {
                    "example_id": payload["example_id"],
                    "output": expected_output,
                    "proposal_id": proposal_ids[decision],
                    "status": expected_status,
                }
                self.assertEqual(
                    stdout_bytes,
                    (json.dumps(expected, indent=2, sort_keys=True) + "\n").encode(
                        "utf-8"
                    ),
                )

    def test_b32_the_schema_freeze_schema_version_2(self) -> None:
        """B32. the schema freeze: SCHEMA_VERSION 2, 14580 bytes, sha256 5be3d79f, equal to SCHEMA_FINGERPRINT

        Reproduction: hash the exact UTF-8 DDL payload and compare version, byte
        length, full baseline digest, and exported fingerprint by equality.
        """
        expected = "5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77"
        schema_bytes = store_module.SCHEMA.encode("utf-8")

        self.assertEqual(store_module.SCHEMA_VERSION, 2)
        self.assertEqual(len(schema_bytes), 14_580)
        self.assertEqual(hashlib.sha256(schema_bytes).hexdigest(), expected)
        self.assertEqual(store_module.SCHEMA_FINGERPRINT, expected)

    def test_b33_a02_literal_is_not_runtime_enforced(self) -> None:
        """B33. A02 Literal is not runtime enforced, so accept correct and reject are called and their values asserted

        Reproduction: keep the Literal annotation as context, then independently call
        all decisions through Python and CLI and reject the legacy resolved runtime value.
        """
        self.assertEqual(
            typing.get_type_hints(ReviewResult)["status"],
            typing.Literal["accepted", "corrected", "rejected"],
        )
        system, database, _ = self._make_system()
        for decision, expected in (
            ("accept", "accepted"),
            ("correct", "corrected"),
            ("reject", "rejected"),
        ):
            with self.subTest(decision=decision):
                api_proposal = self._submit(
                    system,
                    input_value={"api": decision},
                )
                api_arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                result = system.review(
                    "tenant_a",
                    api_proposal,
                    reviewer="operator",
                    decision=decision,
                    **api_arguments,
                )
                self.assertEqual(result.status, expected)
                self.assertNotEqual(result.status, "resolved")

                cli_proposal = self._submit(
                    system,
                    input_value={"cli": decision},
                )
                cli_arguments = [
                    "proposal",
                    "review",
                    cli_proposal,
                    "--reviewer",
                    "operator",
                    "--decision",
                    decision,
                ]
                if decision == "correct":
                    cli_arguments.extend(("--output", '{"answer":99}'))
                status, payload, _, serialized = self._run_cli(
                    database,
                    *cli_arguments,
                )
                self.assertEqual(status, 0)
                self.assertEqual(
                    typing.cast(dict[str, object], payload)["status"],
                    expected,
                )
                self.assertIn(
                    f'"status": "{expected}"'.encode("utf-8"),
                    serialized,
                )
                self.assertNotIn(b'"status": "resolved"', serialized)

    def test_b34_the_complete_statements_left_join_1(self) -> None:
        """B34. the complete statements LEFT JOIN and the row validator refuses the NULL binding, so an orphan fails closed on all five paths and an absent proposal still answers NotFoundError

        Reproduction: trace the singular adapter statement to pin its LEFT request
        join, then orphan the existing proposal and require exact IntegrityError.

        THE JOIN KIND IS LOAD-BEARING AND ITS FIRST READING WAS BACKWARDS. An inner
        join deletes an orphaned proposal from the result set, so the singular paths
        report NotFoundError and the feed silently omits it — indistinguishable from
        a proposal that was never stored, which is the fail-open behaviour section 14
        rejects. What section 15 condemns is a LEFT JOIN that PUBLISHES the NULL
        binding columns. A LEFT JOIN whose row validator REFUSES them keeps absent and
        orphaned distinguishable inside ONE statement, so the cardinality obligation
        and the fail-closed obligation hold together.
        """
        system, database, _ = self._make_system()
        proposal_id = self._submit(system)
        with _record_sql() as (records, _):
            view = system.get_proposal("tenant_a", proposal_id)
        self.assertEqual(view.id, proposal_id)
        request_sql = [
            _normalized_sql(sql)
            for _, _, _, sql, _ in records
            if "requests"
            in {
                token.casefold()
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sql)
            }
        ]
        self.assertEqual(len(request_sql), 1)
        self.assertIn(" left join requests ", f" {request_sql[0]} ")

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "DELETE FROM requests WHERE proposal_id = ?",
                (proposal_id,),
            )
            connection.commit()
        with self.assertRaises(Exception) as raised:
            system.get_proposal("tenant_a", proposal_id)
        self.assertIs(type(raised.exception), IntegrityError)

    def test_b34_the_complete_statements_left_join_2(self) -> None:
        """B34. the complete statements LEFT JOIN and the row validator refuses the NULL binding, so an orphan fails closed on all five paths and an absent proposal still answers NotFoundError

        Reproduction: orphan one proposal, drive all five public paths, and require
        IntegrityError from each while an absent id keeps answering NotFoundError
        both before and after the corruption.

        The control is the point. Without it these assertions pass just as well
        against an implementation that answers IntegrityError for every unknown id,
        which would destroy the distinction rather than establish it.
        """
        system, database, _ = self._make_system()
        proposal_id = self._submit(system)

        with self.assertRaises(NotFoundError):
            system.get_proposal("tenant_a", "prop_absent_00000")

        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "DELETE FROM requests WHERE proposal_id = ?",
                (proposal_id,),
            )
            connection.commit()

        paths: dict[str, typing.Callable[[], object]] = {
            "get_proposal": lambda: system.get_proposal("tenant_a", proposal_id),
            "proposal": lambda: system.proposal("tenant_a", proposal_id),
            "proposals": lambda: system.proposals("tenant_a"),
            "review": lambda: system.review(
                "tenant_a", proposal_id, reviewer="alice", decision="accept"
            ),
            "function_report": lambda: system.function_report("tenant_a", "echo_1"),
        }
        for path, invoke in paths.items():
            with self.subTest(path=path), self.assertRaises(Exception) as raised:
                invoke()
            with self.subTest(path=path, check="class"):
                self.assertIs(type(raised.exception), IntegrityError)

        with self.assertRaises(NotFoundError):
            system.get_proposal("tenant_a", "prop_absent_00000")

    def test_b35_y11_statement_cardinality_one_statement_per_1(self) -> None:
        """B35. Y11 statement cardinality: one statement per adapter call over the whole channel, per path

        Reproduction: record execute, executemany, executescript, and cursor calls;
        pin total/application/request counts plus the ruled adapter-call count for
        every read path.

        "ONE STATEMENT PER CALL" IS WITHDRAWN, and the numbers below are what replaced
        it. Measured request statements per SELECTION are `_ProposalIds` 1,
        `_ProposalFeed` 1, `_PendingProposals` 2 — the pending selection issues an
        uncapped count statement beside its bounded detail statement. X32 forces
        exactly that: a binding missing past the detail cap must still fail closed, so
        the count cannot be derived from the capped rows. Two request statements inside
        ONE adapter call is also exactly the pair baseline issued for the report, so
        the cardinality obligation is met and only the wording was wrong. The last
        element is the adapter call count, and pinning it at 1 for every path is the
        stronger claim: it says no consumer reaches the request row twice.
        """
        expected = {
            "get_proposal": (7, 1, 1, 1),
            "proposal": (7, 1, 1, 1),
            "proposals": (7, 1, 1, 1),
            "function_report": (19, 13, 2, 1),
        }
        request_statements_per_path = {
            "get_proposal": 1,
            "proposal": 1,
            "proposals": 1,
            "function_report": 2,
        }
        real_adapter = system_module._proposal_bindings
        for path, counts in expected.items():
            with self.subTest(path=path):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                calls: dict[str, typing.Callable[[], object]] = {
                    "get_proposal": lambda: system.get_proposal(
                        "tenant_a", proposal_id
                    ),
                    "proposal": lambda: system.proposal(
                        "tenant_a", proposal_id
                    ),
                    "proposals": lambda: system.proposals(
                        "tenant_a", status="pending", limit=10
                    ),
                    "function_report": lambda: system.function_report(
                        "tenant_a", "echo_1", projection_limit=10
                    ),
                }
                with mock.patch.object(
                    system_module,
                    "_proposal_bindings",
                    wraps=real_adapter,
                ) as adapter_spy:
                    with _record_sql() as (records, _):
                        calls[path]()
                actual = (
                    len(records),
                    len(_application_statements(records)),
                    len(_request_statements(records)),
                    adapter_spy.call_count,
                )
                self.assertEqual(actual, counts)
                self.assertEqual(adapter_spy.call_count, 1)
                self.assertEqual(
                    len(_request_statements(records)),
                    request_statements_per_path[path],
                )

    def test_b35_y11_statement_cardinality_one_statement_per_2(self) -> None:
        """B35. Y11 statement cardinality: one statement per adapter call over the whole channel, per path

        Reproduction: trace all three review decisions and require baseline total and
        application counts, with one request statement for each read and write adapter call.
        """
        expected = {
            "accept": (14, 8, 2),
            "correct": (14, 8, 2),
            "reject": (12, 6, 2),
        }
        real_reader = system_module._proposal_bindings
        real_writer = system_module._write_proposal_request_status
        for decision, counts in expected.items():
            with self.subTest(decision=decision):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                with mock.patch.object(
                    system_module,
                    "_proposal_bindings",
                    wraps=real_reader,
                ) as reader_spy, mock.patch.object(
                    system_module,
                    "_write_proposal_request_status",
                    wraps=real_writer,
                ) as writer_spy:
                    with _record_sql() as (records, _):
                        system.review(
                            "tenant_a",
                            proposal_id,
                            reviewer="operator",
                            decision=decision,
                            **arguments,
                        )
                self.assertEqual(
                    (
                        len(records),
                        len(_application_statements(records)),
                        len(_request_statements(records)),
                    ),
                    counts,
                )
                self.assertEqual(reader_spy.call_count, 1)
                self.assertEqual(writer_spy.call_count, 1)
                self.assertEqual(
                    len(_request_statements(records)),
                    reader_spy.call_count + writer_spy.call_count,
                )

    def test_b36_y16_one_transaction_and_adapter_connection_1(self) -> None:
        """B36. Y16 one transaction and adapter connection identity per path, with review sharing one write lock

        Reproduction: capture the actual adapter connection object on every read,
        then require one opened connection, one BEGIN, identity equality, and active transaction state.
        """
        expected_calls = {
            "get_proposal": 1,
            "proposal": 1,
            "proposals": 1,
            "function_report": 1,
        }
        real_adapter = system_module._proposal_bindings
        for path, call_count in expected_calls.items():
            with self.subTest(path=path):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                observed: list[tuple[int, bool]] = []

                def spy(connection: sqlite3.Connection, **kwargs: object) -> object:
                    observed.append((id(connection), connection.in_transaction))
                    return real_adapter(connection, **kwargs)

                calls: dict[str, typing.Callable[[], object]] = {
                    "get_proposal": lambda: system.get_proposal(
                        "tenant_a", proposal_id
                    ),
                    "proposal": lambda: system.proposal(
                        "tenant_a", proposal_id
                    ),
                    "proposals": lambda: system.proposals(
                        "tenant_a", status="pending", limit=10
                    ),
                    "function_report": lambda: system.function_report(
                        "tenant_a", "echo_1", projection_limit=10
                    ),
                }
                with mock.patch.object(
                    system_module,
                    "_proposal_bindings",
                    spy,
                ):
                    with _record_sql() as (records, connection_ids):
                        calls[path]()
                begins = [
                    sql
                    for _, _, _, sql, _ in records
                    if _normalized_sql(sql).startswith("begin")
                ]
                self.assertEqual(len(connection_ids), 1)
                self.assertEqual(len(begins), 1)
                self.assertEqual(len(observed), call_count)
                self.assertTrue(
                    all(
                        connection_id == connection_ids[0] and in_transaction
                        for connection_id, in_transaction in observed
                    )
                )

    def test_b36_y16_one_transaction_and_adapter_connection_2(self) -> None:
        """B36. Y16 one transaction and adapter connection identity per path, with review sharing one write lock

        Reproduction: capture both adapters for accept, correct, and reject; each
        pair must receive the sole connection while its one BEGIN IMMEDIATE lock is active.
        """
        real_reader = system_module._proposal_bindings
        real_writer = system_module._write_proposal_request_status
        for decision in ("accept", "correct", "reject"):
            with self.subTest(decision=decision):
                system, _, _ = self._make_system()
                proposal_id = self._submit(system)
                observed: list[tuple[str, int, bool]] = []

                def reader(connection: sqlite3.Connection, **kwargs: object) -> object:
                    observed.append(("read", id(connection), connection.in_transaction))
                    return real_reader(connection, **kwargs)

                def writer(connection: sqlite3.Connection, **kwargs: object) -> object:
                    observed.append(("write", id(connection), connection.in_transaction))
                    return real_writer(connection, **kwargs)

                arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                with mock.patch.object(
                    system_module,
                    "_proposal_bindings",
                    reader,
                ), mock.patch.object(
                    system_module,
                    "_write_proposal_request_status",
                    writer,
                ):
                    with _record_sql() as (records, connection_ids):
                        system.review(
                            "tenant_a",
                            proposal_id,
                            reviewer="operator",
                            decision=decision,
                            **arguments,
                        )
                begins = [
                    _normalized_sql(sql)
                    for _, _, _, sql, _ in records
                    if _normalized_sql(sql).startswith("begin")
                ]
                self.assertEqual(len(connection_ids), 1)
                self.assertEqual(begins, ["begin immediate"])
                self.assertEqual([kind for kind, _, _ in observed], ["read", "write"])
                self.assertTrue(
                    all(
                        connection_id == connection_ids[0] and in_transaction
                        for _, connection_id, in_transaction in observed
                    )
                )

    def test_b37_y21_one_stale_fixture_crossed_with(self) -> None:
        """B37. Y21 one stale fixture crossed with all three decisions: accept and correct raise, reject completes

        Reproduction: revise after one pending proposal, compare byte-complete dumps
        across failed accept/correct, then require one rejection and zero examples on that same fixture.
        """
        system, database, _ = self._make_system()
        proposal_id = self._submit(system)
        revision = system.revise_operation(
            "tenant_a",
            "echo_1",
            policy=CompilePolicy(2, 1, 0),
            revised_by="operator",
        )
        self.assertEqual(revision, 2)

        def snapshot() -> tuple[str, ...]:
            with closing(sqlite3.connect(database)) as connection:
                return tuple(connection.iterdump())

        for decision in ("accept", "correct"):
            with self.subTest(decision=decision):
                before = snapshot()
                arguments = (
                    {"corrected_output": {"answer": 99}}
                    if decision == "correct"
                    else {}
                )
                with self.assertRaises(Exception) as raised:
                    system.review(
                        "tenant_a",
                        proposal_id,
                        reviewer="operator",
                        decision=decision,
                        **arguments,
                    )
                self.assertIs(type(raised.exception), StateError)
                self.assertEqual(snapshot(), before)

        result = system.review(
            "tenant_a",
            proposal_id,
            reviewer="operator",
            decision="reject",
        )
        statuses = self._rows(
            database,
            """
            SELECT p.status AS proposal_status, r.status AS request_status
            FROM proposals AS p
            JOIN requests AS r ON r.id = p.request_id
            WHERE p.id = ?
            """,
            (proposal_id,),
        )[0]
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.proposal_id, proposal_id)
        self.assertIsNone(result.example_id)
        self.assertIsNone(result.output)
        self.assertEqual(
            (statuses["proposal_status"], statuses["request_status"]),
            ("rejected", "rejected"),
        )
        self.assertEqual(
            self._rows(
                database,
                "SELECT id FROM examples WHERE proposal_id = ?",
                (proposal_id,),
            ),
            [],
        )
        self.assertEqual(
            len(
                self._rows(
                    database,
                    """
                    SELECT sequence FROM events
                    WHERE kind = 'proposal.rejected' AND subject_id = ?
                    """,
                    (proposal_id,),
                )
            ),
            1,
        )

    def test_b38_y8_the_committed_mutation_catalogue_its(self) -> None:
        """B38. Y8 the committed mutation catalogue, its liveness proofs, its control and its verdict modules

        Reproduction: validate all 44 seeded predicate and nonpredicate rows, then
        require a committed harness that proves unique changed/loaded bytes and prints complete control/verdict summaries.
        """
        root = Path(__file__).resolve().parents[1]
        decisions = root / ".agent" / "decisions"
        catalogue_path = decisions / "m3u4-mutants.json"
        catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
        rows = catalogue["rows"]
        expected_ids = {f"M{index:02d}" for index in range(1, 45)}
        ids = {row["id"] for row in rows}
        graded = ("anchor", "mutation", "expected_killer", "result")
        unknown = [
            f"{row['id']}.{field}"
            for row in rows
            for field in graded
            if row.get(field) in (None, "unknown", "")
        ]

        self.assertEqual(catalogue["kind"], "mutants")
        self.assertTrue(expected_ids <= ids)
        self.assertTrue(
            {
                "adapter",
                "row record",
                "singular",
                "writer",
                "consumer",
                "shape",
                "export",
            }
            <= {row["section"] for row in rows}
        )
        with self.subTest(artifact="catalogue completion"):
            self.assertEqual(len(unknown), 0, unknown[:8])
        completed_results = {
            row["result"] for row in rows if row.get("result") != "unknown"
        }
        self.assertTrue(
            completed_results
            <= {"killed", "survived", "equivalent", "unreachable"}
        )

        harness_path = decisions / "m3u4-mutants.py"
        with self.subTest(artifact="committed harness"):
            self.assertTrue(harness_path.is_file(), str(harness_path))
        if not harness_path.is_file():
            return
        harness = harness_path.read_text(encoding="utf-8")
        required_evidence = {
            "unique anchor proof": ("ANCHOR-MISS", "count != 1"),
            "changed bytes proof": ("IDENTITY", "changed nothing"),
            "loaded code proof": ("LOADED", "loaded"),
            "pristine control": ("control: pristine", "CONTROL FAILED"),
            "verdict modules": ("verdict_modules", "--verdict"),
            "total summary": ("mutants=", "total="),
            "killed summary": ("killed=",),
            "equivalent summary": ("equivalent=",),
            "survivor ids": ("SURVIVOR", "survivor_ids", "survivors="),
        }
        for evidence, alternatives in required_evidence.items():
            with self.subTest(evidence=evidence):
                self.assertTrue(
                    any(alternative in harness for alternative in alternatives),
                    alternatives,
                )

    def test_b39_the_feed_order_and_limit_are_exact(self) -> None:
        """B39. the feed orders by ascending status_sequence and its LIMIT truncates, so a reversed or unbounded feed is red

        Reproduction: submit three proposals, read the feed at limit 2 and at the
        default limit, and require both exact ascending identifier tuples.

        One row per call hides both halves of this statement. Every order and every
        limit agree on a single element, so a reversed ORDER BY and a dropped LIMIT
        both survive a feed test that never observes two rows at once.
        """
        system, _, _ = self._make_system()
        first = self._submit(system, input_value={"index": 1})
        second = self._submit(system, input_value={"index": 2})
        third = self._submit(system, input_value={"index": 3})

        page = system.proposals("tenant_a", limit=2)
        self.assertEqual(tuple(record["id"] for record in page), (first, second))

        whole = system.proposals("tenant_a")
        self.assertEqual(
            tuple(record["id"] for record in whole),
            (first, second, third),
        )

    def test_b40_the_binding_request_status_comes_from_the_request_row(self) -> None:
        """B40. binding.request_status is read from the request row, proved on a ledger whose two status columns differ

        Reproduction: store one pending proposal, drive the two status columns apart
        in the ledger, and read the binding through the adapter.

        Equal columns prove nothing here. Every fixture that transitions a proposal
        moves the proposal row and the request row together, so reading the
        proposal's own status column returns the right answer until one ledger holds
        two different values.
        """
        system, database, _ = self._make_system()
        proposal_id = self._submit(system)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                """
                UPDATE proposals
                   SET status = 'rejected', reviewer = 'battery',
                       review_note = 'divergent status columns', reviewed_at_us = 2000000
                 WHERE id = ?
                """,
                (proposal_id,),
            )
            connection.commit()

        with system.store.transaction() as connection:
            bindings = system_module._proposal_bindings(
                connection,
                partition="tenant_a",
                selection=system_module._ProposalIds((proposal_id,)),
            )
        (binding,) = bindings.rows
        self.assertEqual(binding.request_status, "pending")
        self.assertEqual(binding.row["status"], "rejected")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
