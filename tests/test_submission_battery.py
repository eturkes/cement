"""Diff-blind obligation battery for M3.3 explicit proposal submission.

One test per numbered obligation of ``.agent/decisions/m3u3-contract.md``, named
``test_<id>_<slug>``. Coverage is graded by
``uv run python .agent/decisions/m3u3-battery-validate.py``.

Every test states its obligation in its own docstring, including how the
assertion reproduces it, because a finding is graded by whether its reproduction
is stated and never by whether its number differs.
"""

from __future__ import annotations

import asyncio
import ast
from collections.abc import Iterator, Mapping
from contextlib import closing
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest import mock

import cement_runtime
from cement_runtime import Candidate, CandidateRequest, CompilePolicy, System
from cement_runtime.json_value import canonicalize
from cement_runtime.store import SCHEMA, SCHEMA_FINGERPRINT, SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
PARTITION = "tenant_10"
OPERATION = "echo_10"
INPUT = {"value": 10, "nested": ["x", 11]}
CANDIDATE = Candidate(
    output={"answer": 12},
    provenance={"model": "adapter_10", "revision": 13},
)


class _ReturningSource:
    def __init__(self, candidate: Candidate = CANDIDATE) -> None:
        self.candidate = candidate
        self.calls: list[object] = []

    def propose(self, request: object) -> Candidate:
        self.calls.append(request)
        return self.candidate


class _RaisingSource:
    def __init__(self, exception: Exception) -> None:
        self.exception = exception
        self.calls = 0

    def propose(self, request: object) -> Candidate:
        del request
        self.calls += 1
        raise self.exception


class _DuckMapping:
    """Reads like a mapping to ``dict()`` and is not a ``Mapping`` instance."""

    def keys(self) -> tuple[str, ...]:
        return ("model",)

    def __getitem__(self, key: str) -> object:
        return "adapter_43"


class _CallbackSource:
    def __init__(self, callback: object) -> None:
        self.callback = callback
        self.calls: list[object] = []

    def propose(self, request: object) -> Candidate:
        self.calls.append(request)
        return self.callback(request)  # type: ignore[operator, no-any-return]


class SubmissionBatteryTests(unittest.TestCase):
    """Contract-derived pins. The author reads the contract, never the diff."""

    def new_system(
        self,
        *,
        source: object | None = None,
        partition: str = PARTITION,
        operation: str = OPERATION,
    ) -> tuple[System, Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "ledger.db"
        system = System(path, candidate_source=source, clock_us=lambda: 1_700_000_000_010_000)
        system.register_operation(partition, operation)
        return system, path

    def table_counts(self, path: Path) -> dict[str, int]:
        with closing(sqlite3.connect(path)) as connection:
            tables = tuple(
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_schema "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            )
            return {
                table: int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
                for table in tables
            }

    def ledger_snapshot(self, path: Path) -> dict[str, object]:
        with closing(sqlite3.connect(path)) as connection:
            counts = {
                table: int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
                for table in ("requests", "proposals", "events")
            }
            sequence_row = connection.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
            ).fetchone()
            dump = tuple(connection.iterdump())
        return {
            "counts": counts,
            "event_sequence": 0 if sequence_row is None else int(sequence_row[0]),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "dump": dump,
        }

    def revision_race(self) -> tuple[System, Path, dict[str, object], _CallbackSource]:
        source_snapshot: dict[str, object] = {}
        system: System
        path: Path

        def revise_during_generation(request: object) -> Candidate:
            del request
            system.revise_operation(
                PARTITION,
                OPERATION,
                policy=CompilePolicy(
                    min_confirmations=10,
                    min_reviewers=2,
                    min_span_seconds=11,
                ),
                revised_by="racer_12",
            )
            source_snapshot.update(self.ledger_snapshot(path))
            return CANDIDATE

        source = _CallbackSource(revise_during_generation)
        system, path = self.new_system(source=source)
        return system, path, source_snapshot, source

    def test_b01_schema_version_is_2_and_schema(self) -> None:
        """B01. Hashing the encoded DDL pins version 2, 14,580 bytes, and its published fingerprint."""
        encoded = SCHEMA.encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()

        self.assertEqual(SCHEMA_VERSION, 2)
        self.assertEqual(len(encoded), 14_580)
        self.assertEqual(
            digest,
            "5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77",
        )
        self.assertEqual(SCHEMA_FINGERPRINT, digest)

    def test_b02_cli_py_command_supervisor_py_and(self) -> None:
        """B02. Comparing each current byte stream to git object f9b9755 pins both frozen runtime files.

        `src/cement_runtime/cli.py` was a third member, retired by M3.5a
        contract D27 because that unit added two CLI leaves to the file by
        definition. The property this pin carried for it - M3.3 added no CLI
        channel and no CLI candidate-source reach - migrated to M3.5a's D24
        (zero `_source`, `System.propose` and source calls from either new
        leaf), D25 (the `_parser()`-derived census) and D26 (cross-leaf option
        isolation). M3.5b D27 supersedes the first two. `_source` no longer
        exists, so D24's zero-call clause is an absence assertion (M3.5b D08),
        and the census migration reverses, because M3.5b removes the `handle`
        and `request` leaves - 30 to 28 leaves and 37 to 35 nodes, pinned as a
        set difference in both directions (M3.5b D02, D12, D17). Those three
        cover source reach, leaf names and option isolation alone, and none of
        them notices an old leaf's changed default, help string, payload or
        dispatch. Gate 4's `parser_shape` digest carries that remainder:
        mutating `events --limit` from 1000 to 7 moves the digest while the
        28/35 census and every D24, D25 and D26 assertion stay green.

        Re-pinning `cli.py` to a fresh baseline stays rejected (M3.5b D28). The
        roadmap schedules M3.6a and M3.7 to edit the same file again, so a
        per-unit re-pin passes at the moment it is written and reports its next
        scheduled break as a defect.
        """
        paths = (
            "src/cement_runtime/_command_supervisor.py",
            "src/cement_runtime/example_adapter.py",
        )
        for relative_path in paths:
            with self.subTest(path=relative_path):
                baseline = subprocess.check_output(
                    ("git", "-C", str(ROOT), "show", f"f9b9755:{relative_path}")
                )
                self.assertEqual((ROOT / relative_path).read_bytes(), baseline)

    def test_p01_two_methods_candidate_is_keyword_only(self) -> None:
        """P01. Inspecting both public signatures pins a required keyword-only candidate on only the direct path."""
        submit = inspect.signature(System.submit_proposal)
        propose = inspect.signature(System.propose)

        self.assertEqual(
            tuple(submit.parameters),
            ("self", "partition", "operation", "input_value", "candidate"),
        )
        self.assertIs(submit.parameters["candidate"].default, inspect.Parameter.empty)
        self.assertIs(
            submit.parameters["candidate"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        self.assertEqual(
            tuple(propose.parameters),
            ("self", "partition", "operation", "input_value"),
        )

    def test_p02_both_return_the_proposal_id_as(self) -> None:
        """P02. Successful direct and source calls each return an exact str proposal identifier, never a model."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)

        direct = system.submit_proposal(PARTITION, OPERATION, INPUT, candidate=CANDIDATE)
        generated = system.propose(PARTITION, OPERATION, INPUT)

        self.assertIs(type(direct), str)
        self.assertIs(type(generated), str)
        self.assertTrue(direct.startswith("prop_"))
        self.assertTrue(generated.startswith("prop_"))

    def test_p03_submit_proposal_never_invokes_a_configured(self) -> None:
        """P03. A configured source that would raise stays at zero calls while direct submission succeeds."""
        source = _RaisingSource(RuntimeError("direct path must not invoke this source"))
        system, _ = self.new_system(source=source)

        proposal_id = system.submit_proposal(
            PARTITION,
            OPERATION,
            INPUT,
            candidate=CANDIDATE,
        )

        self.assertIs(type(proposal_id), str)
        self.assertEqual(source.calls, 0)

    def test_p04_self_candidate_source_is_propose_s(self) -> None:
        """P04. A wrapped configured source alone supplies the generated output that get_proposal returns."""
        generated = Candidate(
            output={"authority": "configured", "edge": 14},
            provenance={"source": "configured", "edge": 15},
        )
        source = _ReturningSource(generated)
        system, _ = self.new_system(source=source)

        proposal_id = system.propose(PARTITION, OPERATION, INPUT)
        proposal = system.get_proposal(PARTITION, proposal_id)

        self.assertEqual(len(source.calls), 1)
        self.assertEqual(proposal.proposed_output, generated.output)
        self.assertEqual(proposal.provenance, generated.provenance)
        self.assertNotIn("source", inspect.signature(System.propose).parameters)

    def test_p05_neither_name_is_in_all_nor(self) -> None:
        """P05. Module export and attribute checks leave both callables reachable exclusively on System."""
        for name in ("submit_proposal", "propose"):
            with self.subTest(name=name):
                self.assertNotIn(name, cement_runtime.__all__)
                self.assertFalse(hasattr(cement_runtime, name))
                self.assertTrue(callable(getattr(System, name)))

    def test_p06_handle_is_12_866_b_1182130a2b3a(self) -> None:
        """P06. The whole-line lineno..end_lineno span with trailing newlines stripped reproduces the byte pin.

        The name still states the pin this test proves. M3.5a's D16 routes every
        provenance limit through the exported `PROVENANCE_MAX_BYTES`, and one of
        the three literal sites sits inside `handle`, so the raw span now
        measures 12,880 bytes. Substituting that one identifier back to its
        literal reproduces 12,866 and `1182130a2b3a` exactly, which is a
        STRONGER claim than either anchor alone: it proves the substitution is
        the whole delta and every other byte of `handle` is the byte it carried
        at `3b7769b`.
        """
        source_path = Path(inspect.getsourcefile(System) or "")
        source = source_path.read_text(encoding="utf-8")
        module = ast.parse(source)
        system_node = next(
            node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "System"
        )
        handle_node = next(
            node
            for node in system_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "handle"
        )
        whole_line_span_trailing_newlines_stripped = "".join(
            source.splitlines(keepends=True)[handle_node.lineno - 1 : handle_node.end_lineno]
        ).rstrip("\r\n")
        encoded = whole_line_span_trailing_newlines_stripped.encode("utf-8")

        self.assertEqual(len(encoded), 12_880)
        self.assertTrue(hashlib.sha256(encoded).hexdigest().startswith("eec7cb7c85f8"))

        self.assertEqual(
            whole_line_span_trailing_newlines_stripped.count("PROVENANCE_MAX_BYTES"), 1
        )
        restored = whole_line_span_trailing_newlines_stripped.replace(
            "PROVENANCE_MAX_BYTES", "65_536"
        ).encode("utf-8")
        self.assertEqual(len(restored), 12_866)
        self.assertTrue(hashlib.sha256(restored).hexdigest().startswith("1182130a2b3a"))

    def test_p06_three_slicing_conventions_are_distinct(self) -> None:
        """P06. Recomputing all three AST conventions proves only newline-stripped whole lines select the normative pin."""
        source_path = Path(inspect.getsourcefile(System) or "")
        source = source_path.read_text(encoding="utf-8")
        module = ast.parse(source)
        system_node = next(
            node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "System"
        )
        handle_node = next(
            node
            for node in system_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "handle"
        )
        kept = "".join(
            source.splitlines(keepends=True)[handle_node.lineno - 1 : handle_node.end_lineno]
        )
        stripped = kept.rstrip("\r\n")
        source_segment = ast.get_source_segment(source, handle_node) or ""
        measured = tuple(
            (len(value.encode("utf-8")), hashlib.sha256(value.encode("utf-8")).hexdigest()[:12])
            for value in (stripped, kept, source_segment)
        )

        self.assertEqual(
            measured,
            (
                (12_880, "eec7cb7c85f8"),
                (12_881, "da24241f4628"),
                (12_876, "8ce3957fc619"),
            ),
        )
        # Substituting the one constant M3.5a exported back to its literal
        # reproduces M3.3's table exactly, on all three conventions at once. The
        # substitution is therefore the WHOLE delta, and the three conventions
        # stay distinct across it.
        restored = tuple(
            (len(value.encode("utf-8")), hashlib.sha256(value.encode("utf-8")).hexdigest()[:12])
            for value in (
                text.replace("PROVENANCE_MAX_BYTES", "65_536")
                for text in (stripped, kept, source_segment)
            )
        )
        self.assertEqual(
            restored,
            (
                (12_866, "1182130a2b3a"),
                (12_867, "cd60036faf5c"),
                (12_862, "c27e71b0b4c7"),
            ),
        )

    def test_d01_success_footprint_over_declared_schema_tables(self) -> None:
        """D01. Per-table before/after counts pin exactly one request, proposal, and event on both routes."""
        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                before = self.table_counts(path)

                if route == "direct":
                    system.submit_proposal(PARTITION, OPERATION, INPUT, candidate=CANDIDATE)
                else:
                    system.propose(PARTITION, OPERATION, INPUT)

                after = self.table_counts(path)
                delta = {table: after[table] - before[table] for table in before}
                expected = {table: 0 for table in before}
                expected.update({"requests": 1, "proposals": 1, "events": 1})
                self.assertEqual(delta, expected)

    def test_d01_sqlite_sequence_is_outside_declared_schema_footprint(self) -> None:
        """D01. A success increments events and sqlite_sequence together while the declared-table census excludes SQLite internals."""
        system, path = self.new_system()
        before_tables = self.table_counts(path)
        with closing(sqlite3.connect(path)) as connection:
            before_sequence = int(
                connection.execute(
                    "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
                ).fetchone()[0]
            )

        system.submit_proposal(PARTITION, OPERATION, INPUT, candidate=CANDIDATE)

        after_tables = self.table_counts(path)
        with closing(sqlite3.connect(path)) as connection:
            after_sequence = int(
                connection.execute(
                    "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
                ).fetchone()[0]
            )
        self.assertNotIn("sqlite_sequence", before_tables)
        self.assertEqual(after_tables["events"] - before_tables["events"], 1)
        self.assertEqual(after_sequence - before_sequence, 1)

    def test_d02_the_request_row_is_pending_with(self) -> None:
        """D02. Reading each route's sole request row pins pending status, proposal binding, null lease, and attempt one."""
        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                if route == "direct":
                    proposal_id = system.submit_proposal(
                        PARTITION,
                        OPERATION,
                        INPUT,
                        candidate=CANDIDATE,
                    )
                else:
                    proposal_id = system.propose(PARTITION, OPERATION, INPUT)

                with closing(sqlite3.connect(path)) as connection:
                    row = connection.execute(
                        "SELECT status, proposal_id, lease_owner, lease_until_us, attempts "
                        "FROM requests"
                    ).fetchone()

                self.assertEqual(row, ("pending", proposal_id, None, None, 1))

    def test_d03_the_event_is_proposal_created_with(self) -> None:
        """D03. Normalizing handle's request_id leaves the exact empty payload and proposal subject on both new routes."""
        source = _ReturningSource()
        system, path = self.new_system(source=source)
        handled = system.handle(PARTITION, OPERATION, INPUT, request_id="request_public_10")
        direct_id = system.submit_proposal(PARTITION, OPERATION, INPUT, candidate=CANDIDATE)
        source_id = system.propose(PARTITION, OPERATION, INPUT)

        with closing(sqlite3.connect(path)) as connection:
            rows = connection.execute(
                "SELECT kind, subject_type, subject_id, payload_json FROM events "
                "WHERE kind = 'proposal.created' ORDER BY sequence"
            ).fetchall()

        self.assertEqual(len(rows), 3)
        handle_payload = json.loads(rows[0][3])
        self.assertEqual(handle_payload.pop("request_id"), handled.request_id)
        for row, proposal_id in zip(rows[1:], (direct_id, source_id), strict=True):
            self.assertEqual(row[:3], ("proposal.created", "proposal", proposal_id))
            self.assertEqual(json.loads(row[3]), handle_payload)
            self.assertNotIn("request", row[3].lower())

    def test_d04_no_idempotency_byte_identical_content_submitted(self) -> None:
        """D04. Repeating byte-identical content on each route yields distinct IDs and two rows in every footprint table."""
        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                before = self.table_counts(path)
                if route == "direct":
                    first = system.submit_proposal(
                        PARTITION, OPERATION, INPUT, candidate=CANDIDATE
                    )
                    second = system.submit_proposal(
                        PARTITION, OPERATION, INPUT, candidate=CANDIDATE
                    )
                else:
                    first = system.propose(PARTITION, OPERATION, INPUT)
                    second = system.propose(PARTITION, OPERATION, INPUT)

                after = self.table_counts(path)
                self.assertNotEqual(first, second)
                self.assertEqual(
                    {table: after[table] - before[table] for table in ("requests", "proposals", "events")},
                    {"requests": 2, "proposals": 2, "events": 2},
                )

    def test_d04_domain_identifiers_remain_stored_verbatim(self) -> None:
        """D04. Domain request/proposal/idempotency labels inside JSON remain verbatim while Cement alone mints ledger row identities."""
        domain_input = {
            "request_id": "domain_request_10",
            "idempotency_key": "domain_key_11",
        }
        domain_candidate = Candidate(
            output={"proposal_id": "domain_proposal_12"},
            provenance={"request_id": "provider_request_13"},
        )
        system, _ = self.new_system()

        proposal_id = system.submit_proposal(
            PARTITION,
            OPERATION,
            domain_input,
            candidate=domain_candidate,
        )
        view = system.get_proposal(PARTITION, proposal_id)

        self.assertTrue(proposal_id.startswith("prop_"))
        self.assertNotIn("request_id", view.__dataclass_fields__)
        self.assertNotEqual(proposal_id, domain_candidate.output["proposal_id"])
        # The domain's own request_id key survives inside the stored input verbatim; only
        # Cement's request identity left the public shape.
        self.assertEqual(view.input["request_id"], domain_input["request_id"])
        self.assertEqual(view.input, domain_input)
        self.assertEqual(view.proposed_output, domain_candidate.output)
        self.assertEqual(view.provenance, domain_candidate.provenance)

    def test_d05_propose_invokes_the_source_exactly_once(self) -> None:
        """D05. Live call counts stay zero across four pre-invocation errors, then rise once on one success."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        rejected = (
            (("", OPERATION, INPUT), cement_runtime.ValidationError),
            ((PARTITION, "", INPUT), cement_runtime.ValidationError),
            ((PARTITION, OPERATION, 1.5), cement_runtime.ValidationError),
            ((PARTITION, "absent_10", INPUT), cement_runtime.NotFoundError),
        )
        for arguments, error_type in rejected:
            with self.subTest(arguments=arguments):
                with self.assertRaises(error_type):
                    system.propose(*arguments)
                self.assertEqual(len(source.calls), 0)

        proposal_id = system.propose(PARTITION, OPERATION, INPUT)
        self.assertTrue(proposal_id.startswith("prop_"))
        self.assertEqual(len(source.calls), 1)

    def test_d06_one_private_persistence_seam_writes_all(self) -> None:
        """D06. Wrapping the named System seam records one call and its three-row footprint from each public route."""
        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                before = self.table_counts(path)
                with mock.patch.object(
                    system,
                    "_persist_proposal",
                    wraps=system._persist_proposal,
                ) as persistence:
                    if route == "direct":
                        system.submit_proposal(
                            PARTITION,
                            OPERATION,
                            INPUT,
                            candidate=CANDIDATE,
                        )
                    else:
                        system.propose(PARTITION, OPERATION, INPUT)

                persistence.assert_called_once()
                self.assertEqual(
                    persistence.call_args.kwargs["partition"],
                    PARTITION,
                )
                after = self.table_counts(path)
                self.assertEqual(
                    {table: after[table] - before[table] for table in ("requests", "proposals", "events")},
                    {"requests": 1, "proposals": 1, "events": 1},
                )

    def test_d07_validation_order_partition_operation_input_canonicalization_1(self) -> None:
        """D07. Making partition and operation adjacent-invalid returns the partition text, pinning edge one."""
        system, _ = self.new_system()

        with self.assertRaisesRegex(
            cement_runtime.ValidationError,
            r"^partition must be 1-128 ASCII letters, digits, '\.', '_', ':', '/', or '-'$",
        ):
            system.submit_proposal("", "", INPUT, candidate=CANDIDATE)

    def test_d07_validation_order_partition_operation_input_canonicalization_2(self) -> None:
        """D07. Making operation and input adjacent-invalid returns the operation text, pinning edge two."""
        system, _ = self.new_system()

        with self.assertRaisesRegex(
            cement_runtime.ValidationError,
            r"^operation must be 1-128 ASCII letters, digits, '\.', '_', ':', '/', or '-'$",
        ):
            system.submit_proposal(PARTITION, "", 1.5, candidate=CANDIDATE)

    def test_d07_validation_order_partition_operation_input_canonicalization_3(self) -> None:
        """D07. Making input and candidate adjacent-invalid returns the JSON text, pinning edge three."""
        system, _ = self.new_system()

        with self.assertRaisesRegex(
            cement_runtime.ValidationError,
            r"^cement-json-v1 supports integers; encode decimals as strings$",
        ):
            system.submit_proposal(
                PARTITION,
                OPERATION,
                1.5,
                candidate=object(),  # type: ignore[arg-type]
            )

    def test_d07_propose_partition_precedes_operation(self) -> None:
        """D07. On the source route, adjacent-invalid partition and operation return partition before any transaction or invocation."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transactions:
            with self.assertRaisesRegex(
                cement_runtime.ValidationError,
                r"^partition must be 1-128 ASCII letters, digits, '\.', '_', ':', '/', or '-'$",
            ):
                system.propose("", "", INPUT)
        transactions.assert_not_called()
        self.assertEqual(len(source.calls), 0)

    def test_d07_propose_operation_precedes_input(self) -> None:
        """D07. On the source route, adjacent-invalid operation and input return operation before any transaction or invocation."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transactions:
            with self.assertRaisesRegex(
                cement_runtime.ValidationError,
                r"^operation must be 1-128 ASCII letters, digits, '\.', '_', ':', '/', or '-'$",
            ):
                system.propose(PARTITION, "", 1.5)
        transactions.assert_not_called()
        self.assertEqual(len(source.calls), 0)

    def test_d08_a_bad_partition_together_with_a(self) -> None:
        """D08. Pairing an invalid partition with invalid JSON returns the partition error on both public methods."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        calls = (
            lambda: system.submit_proposal("", OPERATION, 1.5, candidate=CANDIDATE),
            lambda: system.propose("", OPERATION, 1.5),
        )
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    cement_runtime.ValidationError,
                    r"^partition must be 1-128 ASCII letters, digits, '\.', '_', ':', '/', or '-'$",
                ):
                    call()
        self.assertEqual(len(source.calls), 0)

    def test_d09_an_argument_rejected_call_opens_zero(self) -> None:
        """D09. A successful positive control moves both live spies; four argument failures then move neither."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        rejected_calls = (
            lambda: system.propose("", OPERATION, INPUT),
            lambda: system.propose(PARTITION, "", INPUT),
            lambda: system.propose(PARTITION, OPERATION, 1.5),
            lambda: system.submit_proposal(
                PARTITION,
                OPERATION,
                INPUT,
                candidate=object(),  # type: ignore[arg-type]
            ),
        )

        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transactions:
            system.propose(PARTITION, OPERATION, INPUT)
            self.assertGreater(transactions.call_count, 0, "transaction spy positive control")
            self.assertEqual(len(source.calls), 1, "source spy positive control")

            for call in rejected_calls:
                with self.subTest(call=call):
                    transactions.reset_mock()
                    calls_before = len(source.calls)
                    with self.assertRaises(cement_runtime.ValidationError):
                        call()
                    self.assertEqual(transactions.call_count, 0)
                    self.assertEqual(len(source.calls), calls_before)

    def test_d10_omitted_candidate_and_source_both_raise(self) -> None:
        """D10. Bound-method calls reproduce Python's missing-keyword and unexpected-keyword TypeError texts."""
        system, _ = self.new_system()
        cases = (
            (
                lambda: system.submit_proposal(PARTITION, OPERATION, INPUT),
                "System.submit_proposal() missing 1 required keyword-only argument: 'candidate'",
            ),
            (
                lambda: system.submit_proposal(
                    PARTITION,
                    OPERATION,
                    INPUT,
                    candidate=CANDIDATE,
                    source=object(),  # type: ignore[call-arg]
                ),
                "System.submit_proposal() got an unexpected keyword argument 'source'",
            ),
            (
                lambda: system.propose(
                    PARTITION,
                    OPERATION,
                    INPUT,
                    source=object(),  # type: ignore[call-arg]
                ),
                "System.propose() got an unexpected keyword argument 'source'",
            ),
        )
        for call, message in cases:
            with self.subTest(message=message):
                with self.assertRaises(TypeError) as raised:
                    call()
                self.assertEqual(str(raised.exception), message)

    def test_d11_no_connection_the_call_holds_is(self) -> None:
        """D11. Held-open factory connections report a live True control, then all report False inside the source."""
        real_connect = sqlite3.connect
        created: list[sqlite3.Connection] = []
        observed_during_source: list[bool] = []

        class HoldingConnection(sqlite3.Connection):
            def close(self) -> None:
                return None

        def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
            kwargs["factory"] = HoldingConnection
            connection = real_connect(*args, **kwargs)  # type: ignore[arg-type]
            created.append(connection)
            return connection

        def observe(request: object) -> Candidate:
            del request
            observed_during_source.extend(connection.in_transaction for connection in created)
            return CANDIDATE

        source = _CallbackSource(observe)
        system, _ = self.new_system(source=source)
        try:
            with mock.patch.object(sqlite3, "connect", side_effect=connect):
                control = sqlite3.connect(":memory:")
                control.execute("BEGIN")
                self.assertTrue(control.in_transaction, "connection observer positive control")
                control.rollback()
                sqlite3.Connection.close(control)
                created.clear()

                system.propose(PARTITION, OPERATION, INPUT)
        finally:
            for connection in created:
                sqlite3.Connection.close(connection)

        self.assertTrue(observed_during_source, "the call opened an observed connection")
        self.assertEqual(observed_during_source, [False] * len(observed_during_source))

    def test_d12_propose_re_reads_the_revision_under(self) -> None:
        """D12. A source-committed revision rejects propose, while the next direct call binds revision two."""
        system, path, _, source = self.revision_race()

        with self.assertRaisesRegex(
            cement_runtime.StateError,
            r"^operation revision changed before proposal submission$",
        ):
            system.propose(PARTITION, OPERATION, INPUT)

        self.assertEqual(len(source.calls), 1)
        self.assertEqual(
            {key: self.table_counts(path)[key] for key in ("requests", "proposals")},
            {"requests": 0, "proposals": 0},
        )
        proposal_id = system.submit_proposal(
            PARTITION,
            OPERATION,
            INPUT,
            candidate=CANDIDATE,
        )
        with closing(sqlite3.connect(path)) as connection:
            revision = connection.execute(
                "SELECT operation_revision FROM requests WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()[0]
        self.assertEqual(revision, 2)

    def test_d12_direct_opens_one_transaction_and_source_opens_two(self) -> None:
        """D12. Live transaction calls pin one write on direct submission versus one revision read plus one write on source submission."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transactions:
            system.submit_proposal(PARTITION, OPERATION, INPUT, candidate=CANDIDATE)
            self.assertEqual(transactions.call_args_list, [mock.call(write=True)])

            transactions.reset_mock()
            system.propose(PARTITION, OPERATION, INPUT)
            self.assertEqual(
                transactions.call_args_list,
                [mock.call(), mock.call(write=True)],
            )

    def test_d13_the_revision_read_is_scoped_to(self) -> None:
        """D13. Recorded SQL uses equality for tenant_a/echo_1 twice and never calls broad operations()."""
        real_connect = sqlite3.connect
        statements: list[tuple[str, tuple[object, ...]]] = []

        class RecordingConnection(sqlite3.Connection):
            def execute(
                self,
                sql: str,
                parameters: object = (),
            ) -> sqlite3.Cursor:
                parameter_tuple = tuple(parameters)  # type: ignore[arg-type]
                statements.append((sql, parameter_tuple))
                return super().execute(sql, parameters)  # type: ignore[arg-type]

        def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
            kwargs["factory"] = RecordingConnection
            return real_connect(*args, **kwargs)  # type: ignore[arg-type]

        source = _ReturningSource()
        system, _ = self.new_system(source=source, partition="tenant_a", operation="echo_1")
        for partition, operation in (
            ("tenantXa", "echo_1"),
            ("tenant_a", "echoX1"),
            ("TENANT_A", "ECHO_1"),
        ):
            system.register_operation(partition, operation)
            system.revise_operation(
                partition,
                operation,
                policy=CompilePolicy(
                    min_confirmations=10,
                    min_reviewers=2,
                    min_span_seconds=11,
                ),
                revised_by="scope_13",
            )

        with mock.patch.object(sqlite3, "connect", side_effect=connect), mock.patch.object(
            system,
            "operations",
            side_effect=AssertionError("propose must not materialize operations()"),
        ) as broad_read:
            system.propose("tenant_a", "echo_1", INPUT)

        self.assertTrue(statements, "statement recorder positive control")
        operation_reads = [
            (" ".join(sql.lower().split()), parameters)
            for sql, parameters in statements
            if sql.lstrip().lower().startswith("select") and " operations " in f" {sql.lower()} "
        ]
        self.assertEqual(len(operation_reads), 2)
        for sql, parameters in operation_reads:
            self.assertIn("where partition = ? and name = ?", sql)
            self.assertNotIn(" like ", f" {sql} ")
            self.assertEqual(parameters, ("tenant_a", "echo_1"))
        broad_read.assert_not_called()
        request = source.calls[0]
        self.assertEqual(
            (request.partition, request.operation, request.operation_revision),
            ("tenant_a", "echo_1", 1),
        )

    def test_d14_propose_hands_the_source_a_candidaterequest(self) -> None:
        """D14. Capturing the sole adapter argument pins CandidateRequest fields and its generated req_ identity."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        caller_input = {"outer": {"value": 10}, "items": [11, 12]}

        proposal_id = system.propose(PARTITION, OPERATION, caller_input)

        self.assertEqual(len(source.calls), 1)
        request = source.calls[0]
        self.assertIs(type(request), CandidateRequest)
        self.assertEqual(
            (request.partition, request.operation, request.operation_revision),
            (PARTITION, OPERATION, 1),
        )
        self.assertTrue(request.request_id.startswith("req_"))
        self.assertEqual(request.input, caller_input)
        self.assertIsNot(request.input, caller_input)
        self.assertEqual(system.get_proposal(PARTITION, proposal_id).input, caller_input)

    def test_d15_a_failed_submission_mutates_nothing_of_1(self) -> None:
        """D15. Request and proposal counts after the source's committed revision equal counts after rejection returns."""
        system, path, source_snapshot, _ = self.revision_race()

        with self.assertRaisesRegex(
            cement_runtime.StateError,
            r"^operation revision changed before proposal submission$",
        ):
            system.propose(PARTITION, OPERATION, INPUT)

        after = self.ledger_snapshot(path)
        baseline_counts = source_snapshot["counts"]
        after_counts = after["counts"]
        self.assertIsInstance(baseline_counts, dict)
        self.assertIsInstance(after_counts, dict)
        self.assertEqual(baseline_counts["requests"], after_counts["requests"])
        self.assertEqual(baseline_counts["proposals"], after_counts["proposals"])

    def test_d15_a_failed_submission_mutates_nothing_of_2(self) -> None:
        """D15. Event count and sqlite_sequence after the source's commit remain exact after revision rejection."""
        system, path, source_snapshot, _ = self.revision_race()

        with self.assertRaises(cement_runtime.StateError):
            system.propose(PARTITION, OPERATION, INPUT)

        after = self.ledger_snapshot(path)
        baseline_counts = source_snapshot["counts"]
        after_counts = after["counts"]
        self.assertIsInstance(baseline_counts, dict)
        self.assertIsInstance(after_counts, dict)
        self.assertEqual(baseline_counts["events"], after_counts["events"])
        self.assertEqual(source_snapshot["event_sequence"], after["event_sequence"])

    def test_d15_a_failed_submission_mutates_nothing_of_3(self) -> None:
        """D15. Ledger sha256 captured after the source's revision commit is byte-identical after rejection."""
        system, path, source_snapshot, _ = self.revision_race()

        with self.assertRaises(cement_runtime.StateError):
            system.propose(PARTITION, OPERATION, INPUT)

        self.assertEqual(source_snapshot["sha256"], self.ledger_snapshot(path)["sha256"])

    def test_d15_a_failed_submission_mutates_nothing_of_4(self) -> None:
        """D15. Full iterdump captured after the source's revision commit is text-identical after rejection."""
        system, path, source_snapshot, _ = self.revision_race()

        with self.assertRaises(cement_runtime.StateError):
            system.propose(PARTITION, OPERATION, INPUT)

        self.assertEqual(source_snapshot["dump"], self.ledger_snapshot(path)["dump"])

    def test_d15_a_failed_submission_mutates_nothing_of_5(self) -> None:
        """D15. Injecting after writes one, two, and three rolls back every purity pin with no successful commit."""
        real_connect = sqlite3.connect

        for fail_after in (1, 2, 3):
            with self.subTest(fail_after=fail_after):
                system, path = self.new_system()
                baseline = self.ledger_snapshot(path)
                interior_writes: list[str] = []
                connection_count = 0
                commit_calls = 0
                successful_commits = 0

                class InjectingConnection(sqlite3.Connection):
                    def execute(
                        self,
                        sql: str,
                        parameters: object = (),
                    ) -> sqlite3.Cursor:
                        cursor = super().execute(sql, parameters)  # type: ignore[arg-type]
                        normalized = " ".join(sql.lower().split())
                        table = next(
                            (
                                name
                                for name in ("requests", "proposals", "events")
                                if normalized.startswith(f"insert into {name}")
                            ),
                            None,
                        )
                        if table is not None:
                            interior_writes.append(table)
                            if len(interior_writes) == fail_after:
                                raise sqlite3.IntegrityError(
                                    f"injected after interior write {fail_after}"
                                )
                        return cursor

                    def commit(self) -> None:
                        nonlocal commit_calls, successful_commits
                        commit_calls += 1
                        super().commit()
                        successful_commits += 1

                def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
                    nonlocal connection_count
                    kwargs["factory"] = InjectingConnection
                    connection_count += 1
                    return real_connect(*args, **kwargs)  # type: ignore[arg-type]

                with mock.patch.object(sqlite3, "connect", side_effect=connect):
                    with self.assertRaises(cement_runtime.IntegrityError) as raised:
                        system.submit_proposal(
                            PARTITION,
                            OPERATION,
                            INPUT,
                            candidate=CANDIDATE,
                        )

                self.assertEqual(
                    str(raised.exception),
                    "database operation failed an integrity check",
                )
                self.assertGreater(connection_count, 0, "factory injection positive control")
                self.assertEqual(len(interior_writes), fail_after)
                self.assertEqual(commit_calls, 0)
                self.assertEqual(successful_commits, 0)
                after = self.ledger_snapshot(path)
                baseline_counts = baseline["counts"]
                after_counts = after["counts"]
                self.assertIsInstance(baseline_counts, dict)
                self.assertIsInstance(after_counts, dict)
                self.assertEqual(baseline_counts["requests"], after_counts["requests"])
                self.assertEqual(baseline_counts["proposals"], after_counts["proposals"])
                self.assertEqual(baseline_counts["events"], after_counts["events"])
                self.assertEqual(baseline["event_sequence"], after["event_sequence"])
                self.assertEqual(baseline["sha256"], after["sha256"])
                self.assertEqual(baseline["dump"], after["dump"])

    def test_d16_zero_commit_calls_on_failures_before_1(self) -> None:
        """D16. The factory spy counts a committed write control, resets, then counts zero on source failure."""
        real_connect = sqlite3.connect
        commit_calls = 0
        factory_connections = 0

        class CommitCountingConnection(sqlite3.Connection):
            def commit(self) -> None:
                nonlocal commit_calls
                commit_calls += 1
                super().commit()

        def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
            nonlocal factory_connections
            kwargs["factory"] = CommitCountingConnection
            factory_connections += 1
            return real_connect(*args, **kwargs)  # type: ignore[arg-type]

        source = _RaisingSource(RuntimeError("adapter failure 16"))
        system, _ = self.new_system(source=source)
        with mock.patch.object(sqlite3, "connect", side_effect=connect):
            with system.store.transaction(write=True) as connection:
                cursor = connection.execute(
                    "UPDATE operations SET updated_at_us = updated_at_us "
                    "WHERE partition = ? AND name = ?",
                    (PARTITION, OPERATION),
                )
                self.assertEqual(cursor.rowcount, 1)
            self.assertEqual(commit_calls, 1, "commit spy positive control")
            self.assertGreater(factory_connections, 0, "factory positive control")

            commit_calls = 0
            with self.assertRaisesRegex(
                cement_runtime.CandidateSourceError,
                r"^candidate source failed$",
            ):
                system.propose(PARTITION, OPERATION, INPUT)

        self.assertEqual(source.calls, 1)
        self.assertEqual(commit_calls, 0)

    def test_d16_zero_commit_calls_on_failures_before_2(self) -> None:
        """D16. A committed write proves the factory spy; argument, lookup, and missing-source failures stay zero."""
        real_connect = sqlite3.connect
        commit_calls = 0

        class CommitCountingConnection(sqlite3.Connection):
            def commit(self) -> None:
                nonlocal commit_calls
                commit_calls += 1
                super().commit()

        def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
            kwargs["factory"] = CommitCountingConnection
            return real_connect(*args, **kwargs)  # type: ignore[arg-type]

        system, _ = self.new_system()
        failures = (
            (
                cement_runtime.ValidationError,
                lambda: system.submit_proposal(
                    PARTITION,
                    OPERATION,
                    INPUT,
                    candidate=object(),  # type: ignore[arg-type]
                ),
            ),
            (
                cement_runtime.NotFoundError,
                lambda: system.submit_proposal(
                    PARTITION,
                    "absent_16",
                    INPUT,
                    candidate=CANDIDATE,
                ),
            ),
            (
                cement_runtime.StateError,
                lambda: system.propose(PARTITION, OPERATION, INPUT),
            ),
        )

        with mock.patch.object(sqlite3, "connect", side_effect=connect):
            with system.store.transaction(write=True) as connection:
                cursor = connection.execute(
                    "UPDATE operations SET updated_at_us = updated_at_us "
                    "WHERE partition = ? AND name = ?",
                    (PARTITION, OPERATION),
                )
                self.assertEqual(cursor.rowcount, 1)
            self.assertEqual(commit_calls, 1, "commit spy positive control")

            for error_type, call in failures:
                with self.subTest(error_type=error_type.__name__):
                    commit_calls = 0
                    with self.assertRaises(error_type):
                        call()
                    self.assertEqual(commit_calls, 0)

    def test_d16_a_commit_failure_is_one_invocation_not_zero(self) -> None:
        """D16. Injecting failure from commit() proves the pre-commit zero rule stops at the commit boundary and rollback stays pure."""
        real_connect = sqlite3.connect
        commit_calls = 0
        successful_commits = 0

        class CommitFailingConnection(sqlite3.Connection):
            def commit(self) -> None:
                nonlocal commit_calls
                commit_calls += 1
                raise sqlite3.OperationalError("injected commit failure 16")

        def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
            kwargs["factory"] = CommitFailingConnection
            return real_connect(*args, **kwargs)  # type: ignore[arg-type]

        system, path = self.new_system()
        before = self.ledger_snapshot(path)
        with mock.patch.object(sqlite3, "connect", side_effect=connect):
            with self.assertRaisesRegex(
                cement_runtime.StateError,
                r"^database is busy or unavailable$",
            ):
                system.submit_proposal(
                    PARTITION,
                    OPERATION,
                    INPUT,
                    candidate=CANDIDATE,
                )

        self.assertEqual(commit_calls, 1)
        self.assertEqual(successful_commits, 0)
        self.assertEqual(self.ledger_snapshot(path), before)

    def test_d17_no_clock_except_self_now_and(self) -> None:
        """D17. A nonempty statement recorder excludes eight resolve tables while one _now call sees the write transaction."""
        real_connect = sqlite3.connect
        forbidden_tables = {
            "examples",
            "example_revocations",
            "artifacts",
            "artifact_evidence",
            "test_reports",
            "artifact_tests",
            "function_receipts",
            "function_memberships",
        }

        for route in ("direct", "source"):
            with self.subTest(route=route):
                statements: list[str] = []
                active_connections: list[sqlite3.Connection] = []
                states_at_now: list[tuple[bool, ...]] = []

                class RecordingConnection(sqlite3.Connection):
                    def execute(
                        self,
                        sql: str,
                        parameters: object = (),
                    ) -> sqlite3.Cursor:
                        statements.append(sql)
                        return super().execute(sql, parameters)  # type: ignore[arg-type]

                    def close(self) -> None:
                        if self in active_connections:
                            active_connections.remove(self)
                        super().close()

                def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
                    kwargs["factory"] = RecordingConnection
                    connection = real_connect(*args, **kwargs)  # type: ignore[arg-type]
                    active_connections.append(connection)
                    return connection

                source = _ReturningSource() if route == "source" else None
                system, _ = self.new_system(source=source)
                original_now = system._now

                def observe_now() -> int:
                    states_at_now.append(
                        tuple(connection.in_transaction for connection in active_connections)
                    )
                    return original_now()

                with mock.patch.object(sqlite3, "connect", side_effect=connect), mock.patch.object(
                    system,
                    "_now",
                    side_effect=observe_now,
                ) as now_spy:
                    if route == "direct":
                        system.submit_proposal(
                            PARTITION,
                            OPERATION,
                            INPUT,
                            candidate=CANDIDATE,
                        )
                    else:
                        system.propose(PARTITION, OPERATION, INPUT)

                self.assertTrue(statements, "statement recorder positive control")
                normalized = [" ".join(statement.lower().split()) for statement in statements]
                statement_words = {
                    word.strip("(),")
                    for statement in normalized
                    for word in statement.split()
                }
                self.assertTrue(forbidden_tables.isdisjoint(statement_words))
                now_spy.assert_called_once_with()
                self.assertEqual(states_at_now, [(True,)])

    def test_d18_source_failure_raises_with_cause_context(self) -> None:
        """D18. Declared and arbitrary secret failures lose cause, context, adapter frames, renderings, and event payload traces."""
        secret = "PLANTED_ADAPTER_SECRET_18"

        class ArbitrarySecretSource:
            def adapter_secret_frame_18(self) -> Candidate:
                try:
                    raise KeyError(secret)
                except KeyError as cause:
                    raise RuntimeError(secret) from cause

            def propose(self, request: object) -> Candidate:
                del request
                return self.adapter_secret_frame_18()

        sources = (
            _RaisingSource(cement_runtime.CandidateSourceError(secret)),
            ArbitrarySecretSource(),
        )
        for source in sources:
            with self.subTest(source=type(source).__name__):
                system, path = self.new_system(source=source)
                with self.assertRaises(cement_runtime.CandidateSourceError) as raised:
                    system.propose(PARTITION, OPERATION, INPUT)

                error = raised.exception
                self.assertIs(type(error), cement_runtime.CandidateSourceError)
                self.assertEqual(str(error), "candidate source failed")
                self.assertIsNone(error.__cause__)
                self.assertIsNone(error.__context__)
                self.assertNotIn(secret, str(error))
                self.assertNotIn(secret, repr(error))
                traceback_frames: list[tuple[str, str]] = []
                traceback = error.__traceback__
                while traceback is not None:
                    traceback_frames.append(
                        (traceback.tb_frame.f_code.co_filename, traceback.tb_frame.f_code.co_name)
                    )
                    traceback = traceback.tb_next
                self.assertFalse(
                    any(
                        Path(filename) == Path(__file__)
                        and name in {"propose", "adapter_secret_frame_18"}
                        for filename, name in traceback_frames
                    ),
                    traceback_frames,
                )
                with closing(sqlite3.connect(path)) as connection:
                    payloads = [str(row[0]) for row in connection.execute("SELECT payload_json FROM events")]
                self.assertTrue(payloads, "event-payload scan positive control")
                for payload in payloads:
                    self.assertNotIn(secret, payload)

    def test_d18_descriptor_failure_is_fully_sanitized(self) -> None:
        """D18. A reassigned propose descriptor with a planted cause loses both exception links, its frame, secret text, events, and writes."""
        secret = "DESCRIPTOR_CONTAINMENT_SECRET_18"

        class RaisingDescriptor:
            def __init__(self) -> None:
                self.accesses = 0

            def __get__(self, instance: object, owner: object) -> object:
                del instance, owner
                self.accesses += 1
                try:
                    raise KeyError(secret)
                except KeyError as cause:
                    raise RuntimeError(secret) from cause

        descriptor = RaisingDescriptor()

        class DescriptorSource:
            propose = descriptor

        system, path = self.new_system(source=_ReturningSource())
        system.candidate_source = DescriptorSource()
        before = self.ledger_snapshot(path)
        with self.assertRaises(cement_runtime.CandidateSourceError) as raised:
            system.propose(PARTITION, OPERATION, INPUT)
        error = raised.exception

        self.assertEqual(descriptor.accesses, 1)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(secret, str(error))
        self.assertNotIn(secret, repr(error))
        traceback = error.__traceback__
        frames: list[tuple[str, str]] = []
        while traceback is not None:
            frames.append(
                (traceback.tb_frame.f_code.co_filename, traceback.tb_frame.f_code.co_name)
            )
            traceback = traceback.tb_next
        self.assertFalse(
            any(Path(filename) == Path(__file__) and name == "__get__" for filename, name in frames),
            frames,
        )
        self.assertEqual(self.ledger_snapshot(path), before)
        with closing(sqlite3.connect(path)) as connection:
            payloads = tuple(str(row[0]) for row in connection.execute("SELECT payload_json FROM events"))
        self.assertTrue(payloads)
        self.assertTrue(all(secret not in payload for payload in payloads))

    def test_d19_the_declared_and_the_arbitrary_source(self) -> None:
        """D19. Equal class, args, text, repr, links, and normalized frames make declared and arbitrary failures indistinguishable."""
        def observe(source_exception: Exception) -> tuple[object, ...]:
            system, _ = self.new_system(source=_RaisingSource(source_exception))
            with self.assertRaises(cement_runtime.CandidateSourceError) as raised:
                system.propose(PARTITION, OPERATION, INPUT)
            error = raised.exception
            frames: list[tuple[str, str]] = []
            traceback = error.__traceback__
            while traceback is not None:
                frames.append(
                    (
                        Path(traceback.tb_frame.f_code.co_filename).name,
                        traceback.tb_frame.f_code.co_name,
                    )
                )
                traceback = traceback.tb_next
            return (
                type(error),
                error.args,
                str(error),
                repr(error),
                error.__cause__,
                error.__context__,
                tuple(frames),
            )

        declared = observe(cement_runtime.CandidateSourceError("declared secret 19"))
        arbitrary = observe(RuntimeError("arbitrary secret 19"))
        self.assertEqual(declared, arbitrary)

    def test_d20_failure_raises_it_never_returns_and(self) -> None:
        """D20. A source exception exits only by CandidateSourceError and leaves no failed request or fallback event."""
        source = _RaisingSource(RuntimeError("failure 20"))
        system, path = self.new_system(source=source)

        with self.assertRaisesRegex(
            cement_runtime.CandidateSourceError,
            r"^candidate source failed$",
        ):
            system.propose(PARTITION, OPERATION, INPUT)

        with closing(sqlite3.connect(path)) as connection:
            request_rows = int(connection.execute("SELECT count(*) FROM requests").fetchone()[0])
            failed_rows = int(
                connection.execute("SELECT count(*) FROM requests WHERE status = 'failed'").fetchone()[0]
            )
            proposal_rows = int(connection.execute("SELECT count(*) FROM proposals").fetchone()[0])
            fallback_events = int(
                connection.execute(
                    "SELECT count(*) FROM events WHERE kind = 'request.fallback_failed'"
                ).fetchone()[0]
            )

        self.assertEqual((request_rows, failed_rows, proposal_rows, fallback_events), (0, 0, 0, 0))

    def test_d21_notfounderror_precedes_source_invocation_but_never(self) -> None:
        """D21. A live source proves zero calls on absent lookup; absent source plus absent operation reports configuration first."""
        source = _ReturningSource()
        configured, _ = self.new_system(source=source)

        with self.assertRaisesRegex(
            cement_runtime.NotFoundError,
            r"^operation is not registered in this partition$",
        ):
            configured.propose(PARTITION, "absent_21", INPUT)
        self.assertEqual(len(source.calls), 0)
        configured.propose(PARTITION, OPERATION, INPUT)
        self.assertEqual(len(source.calls), 1, "source counter positive control")

        unconfigured, _ = self.new_system()
        with mock.patch.object(
            unconfigured.store,
            "transaction",
            wraps=unconfigured.store.transaction,
        ) as transactions:
            with self.assertRaisesRegex(
                cement_runtime.StateError,
                r"^candidate source is not configured$",
            ):
                unconfigured.propose(PARTITION, "absent_21", INPUT)
        transactions.assert_not_called()

    def test_d22_neither_the_return_value_nor_the(self) -> None:
        """D22. Looking up the stored request ID proves it appears in neither returned proposal ID nor created-event payload."""
        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                if route == "direct":
                    proposal_id = system.submit_proposal(
                        PARTITION,
                        OPERATION,
                        INPUT,
                        candidate=CANDIDATE,
                    )
                else:
                    proposal_id = system.propose(PARTITION, OPERATION, INPUT)

                with closing(sqlite3.connect(path)) as connection:
                    request_id = str(
                        connection.execute(
                            "SELECT request_id FROM proposals WHERE id = ?",
                            (proposal_id,),
                        ).fetchone()[0]
                    )
                    event = connection.execute(
                        "SELECT subject_type, subject_id, payload_json FROM events "
                        "WHERE kind = 'proposal.created' AND subject_id = ?",
                        (proposal_id,),
                    ).fetchone()

                self.assertIs(type(proposal_id), str)
                self.assertNotEqual(proposal_id, request_id)
                self.assertNotIn(request_id, proposal_id)
                self.assertEqual(event, ("proposal", proposal_id, "{}"))
                self.assertNotIn(request_id, event[2])

    def test_d23_the_eight_named_seams_still_expose(self) -> None:
        """D23. One proposal ID reaches the same request ID through all eight named live high-level seams."""
        source = _ReturningSource()
        system, _ = self.new_system(source=source)
        proposal_id = system.propose(PARTITION, OPERATION, INPUT)
        source_request = source.calls[0]
        request_id = source_request.request_id

        report = system.function_report(PARTITION, OPERATION)
        gap = next(
            gap
            for gap in report.operation_now.pending_proposals
            if gap.proposal_id == proposal_id
        )
        # M3.4 split this seam census in two. The handle lifecycle still carries the
        # caller's own request identity; the proposal, review and report seams no longer
        # expose any. Both halves are asserted, so readmitting one member to the wrong
        # half fails here.
        exposed = {
            "CandidateRequest": source_request.request_id,
            "handle": system.handle(
                PARTITION,
                OPERATION,
                INPUT,
                request_id=request_id,
            ).request_id,
            "request_status": system.request_status(PARTITION, request_id).request_id,
        }
        view = system.get_proposal(PARTITION, proposal_id)
        record = system.proposal(PARTITION, proposal_id)
        feed = system.proposals(PARTITION)[0]
        result = system.review(
            PARTITION,
            proposal_id,
            reviewer="reviewer_23",
            decision="reject",
            note="rejected_23",
        )

        self.assertEqual(len(exposed), 3)
        self.assertEqual(set(exposed.values()), {request_id})
        self.assertNotIn("request_id", view.__dataclass_fields__)
        self.assertNotIn("request_id", record)
        self.assertNotIn("request_id", feed)
        self.assertNotIn("request_id", gap.__dataclass_fields__)
        self.assertNotIn("request_id", result.__dataclass_fields__)
        self.assertEqual(result.proposal_id, proposal_id)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(len(source.calls), 1)

    def test_d24_private_means_a_storage_role_the(self) -> None:
        """D24. Signature inspection plus ledger lookup pins a retained request row that neither method accepts nor returns."""
        for method in (System.submit_proposal, System.propose):
            with self.subTest(method=method.__name__):
                parameters = inspect.signature(method).parameters
                self.assertNotIn("request_id", parameters)
                self.assertNotIn("idempotency_key", parameters)

        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                if route == "direct":
                    returned = system.submit_proposal(
                        PARTITION,
                        OPERATION,
                        INPUT,
                        candidate=CANDIDATE,
                    )
                else:
                    returned = system.propose(PARTITION, OPERATION, INPUT)
                with closing(sqlite3.connect(path)) as connection:
                    stored_request_id = str(
                        connection.execute(
                            "SELECT id FROM requests WHERE proposal_id = ?",
                            (returned,),
                        ).fetchone()[0]
                    )
                self.assertTrue(stored_request_id.startswith("req_"))
                self.assertNotEqual(returned, stored_request_id)

    def test_d25_shipped_prose_says_schema_v2_retains(self) -> None:
        """D25. Every public paragraph calling the row internal also states schema-v2 retention and reader visibility."""
        surfaces = (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")))
        identity_paragraphs: list[tuple[Path, str]] = []
        for path in surfaces:
            for paragraph in path.read_text(encoding="utf-8").split("\n\n"):
                lowered = " ".join(paragraph.lower().split())
                if "request row stays internal" in lowered:
                    identity_paragraphs.append((path, lowered))

        self.assertGreaterEqual(len(identity_paragraphs), 2)
        for path, paragraph in identity_paragraphs:
            with self.subTest(path=path):
                self.assertIn("schema v2", paragraph)
                self.assertTrue("keeps" in paragraph or "retains" in paragraph)
                self.assertIn("internal storage", paragraph)
        readme = " ".join(
            (ROOT / "README.md").read_text(encoding="utf-8").lower().split()
        )
        self.assertIn(
            "no proposal, review, or report value shows it", readme
        )

    def test_d26_the_battery_module_declares_no_skips(self) -> None:
        """D26. AST inspection finds zero skip decorators here, while the contract carries its measured close totals."""
        battery_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        skip_decorators = [
            (node.name, ast.dump(decorator))
            for node in ast.walk(battery_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for decorator in node.decorator_list
            if "skip" in ast.dump(decorator).lower()
        ]
        self.assertEqual(skip_decorators, [])

        contract = " ".join(
            (ROOT / ".agent/decisions/m3u3-contract.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        self.assertIn(
            "668 tests (n = 33), 0 failures, 0 errors, 206.045 s",
            contract,
        )
        self.assertIn("zero skips among the tests m3.3 adds", contract)

    def test_d27_the_census_test_is_cited_by(self) -> None:
        """D27. Contract citation plus AST shape pins three positive integer counts and an explicit violations-equals-empty assertion."""
        test_name = "test_b20_read_site_census_has_no_mutations"
        contract = (ROOT / ".agent/decisions/m3u3-contract.md").read_text(encoding="utf-8")
        self.assertIn(test_name, contract)

        census_path = ROOT / "tests/test_read_capability_battery.py"
        census_tree = ast.parse(census_path.read_text(encoding="utf-8"))
        census_test = next(
            node
            for node in ast.walk(census_tree)
            if isinstance(node, ast.FunctionDef) and node.name == test_name
        )
        assertions = [
            node
            for node in ast.walk(census_test)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assertEqual"
        ]
        exact_positive_counts = {
            argument.value
            for assertion in assertions
            for argument in assertion.args[:2]
            if isinstance(argument, ast.Constant)
            and type(argument.value) is int
            and argument.value > 0
        }
        pins_empty_violations = any(
            any(isinstance(argument, ast.Name) and argument.id == "violations" for argument in call.args)
            and any(isinstance(argument, ast.List) and not argument.elts for argument in call.args)
            for call in assertions
        )

        self.assertGreaterEqual(len(exact_positive_counts), 3)
        self.assertTrue(pins_empty_violations)

    def test_d28_the_census_counts_match_the_sites(self) -> None:
        """D28. Executing the named census proves its exact totals, while its AST names both added transaction methods."""
        module_name = "tests.test_read_capability_battery"
        test_name = "test_b20_read_site_census_has_no_mutations"
        module = importlib.import_module(module_name)
        discovered = unittest.TestLoader().loadTestsFromModule(module)

        def flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
            tests: list[unittest.TestCase] = []
            for item in suite:
                if isinstance(item, unittest.TestSuite):
                    tests.extend(flatten(item))
                else:
                    tests.append(item)
            return tests

        matches = [
            test
            for test in flatten(discovered)
            if getattr(test, "_testMethodName", "") == test_name
        ]
        self.assertEqual(len(matches), 1)
        result = unittest.TestResult()
        unittest.TestSuite(matches).run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])

        census_path = ROOT / "tests/test_read_capability_battery.py"
        source = census_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        node = next(
            candidate
            for candidate in ast.walk(tree)
            if isinstance(candidate, ast.FunctionDef) and candidate.name == test_name
        )
        census_source = ast.get_source_segment(source, node) or ""
        self.assertIn("_submission_revision", census_source)
        self.assertIn("_persist_proposal", census_source)

    def test_d29_every_census_site_binds_a_simple(self) -> None:
        """D29. The census AST accumulates binding defects into violations and its live execution leaves that list empty."""
        test_name = "test_b20_read_site_census_has_no_mutations"
        module = importlib.import_module("tests.test_read_capability_battery")
        discovered = unittest.TestLoader().loadTestsFromModule(module)
        stack: list[unittest.TestSuite | unittest.TestCase] = [discovered]
        matches: list[unittest.TestCase] = []
        while stack:
            item = stack.pop()
            if isinstance(item, unittest.TestSuite):
                stack.extend(item)
            elif getattr(item, "_testMethodName", "") == test_name:
                matches.append(item)
        self.assertEqual(len(matches), 1)
        result = unittest.TestResult()
        unittest.TestSuite(matches).run(result)
        self.assertEqual((result.failures, result.errors, result.skipped), ([], [], []))

        tree = ast.parse(
            (ROOT / "tests/test_read_capability_battery.py").read_text(encoding="utf-8")
        )
        node = next(
            candidate
            for candidate in ast.walk(tree)
            if isinstance(candidate, ast.FunctionDef) and candidate.name == test_name
        )
        records_violations = any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "append"
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "violations"
            for call in ast.walk(node)
        )
        pins_empty = any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "assertEqual"
            and any(isinstance(arg, ast.Name) and arg.id == "violations" for arg in call.args)
            and any(isinstance(arg, ast.List) and not arg.elts for arg in call.args)
            for call in ast.walk(node)
        )
        self.assertTrue(records_violations)
        self.assertTrue(pins_empty)

    def test_d30_closure_instruments_exist_and_the_contract(self) -> None:
        """D30. Git-tracked battery and grader files plus exact contract command and enumerated mutation corpus make closure mechanical."""
        instruments = (
            "tests/test_submission_battery.py",
            ".agent/decisions/m3u3-battery-validate.py",
        )
        for relative_path in instruments:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())
                subprocess.run(
                    ("git", "-C", str(ROOT), "ls-files", "--error-unmatch", relative_path),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        contract = (ROOT / ".agent/decisions/m3u3-contract.md").read_text(encoding="utf-8")
        missing: list[str] = []
        grader_command = "uv run python .agent/decisions/m3u3-battery-validate.py"
        if grader_command not in contract:
            missing.append(f"verbatim grader command: {grader_command}")
        lowered = " ".join(contract.lower().split())
        if "mutation corpus" not in lowered or "mutation corpus is unenumerated" in lowered:
            missing.append("enumerated mutation corpus")
        self.assertEqual(missing, [])

    def test_d31_candidatesourceerror_s_docstring_names_explicit_submission(self) -> None:
        """D31. Runtime docstring inspection ties the error to System.propose and contains no fallback vocabulary."""
        docstring = inspect.getdoc(cement_runtime.CandidateSourceError) or ""
        lowered = docstring.lower()

        self.assertIn("system.propose", lowered)
        self.assertIn("candidate source", lowered)
        self.assertIn("usable candidate", lowered)
        self.assertNotIn("fallback", lowered)

    def test_d32_both_docstrings_state_persistence_no_idempotency(self) -> None:
        """D32. Normalized method docs publish three-row cost, idempotency, authority, and route-specific error classes without stale revision text."""
        submit = " ".join((inspect.getdoc(System.submit_proposal) or "").lower().split())
        propose = " ".join((inspect.getdoc(System.propose) or "").lower().split())

        for method, docstring in (("submit_proposal", submit), ("propose", propose)):
            with self.subTest(method=method):
                self.assertIn("one request row", docstring)
                self.assertIn("one proposal row", docstring)
                self.assertIn("proposal.created", docstring)
                self.assertIn("no idempotency", docstring)
                self.assertIn("return the identifier", docstring)
                self.assertIn("validationerror", docstring)
                self.assertIn("notfounderror", docstring)

        # V-D12 leaves the direct path no revision guard, so naming StateError on
        # submit_proposal would publish an error that route cannot raise.
        self.assertIn("stateerror", propose)
        self.assertNotIn("stateerror", submit)
        self.assertIn("binds whatever operation revision is current", submit)
        self.assertIn("never invokes the configured candidate source", submit)
        self.assertNotIn("operation revision changes", submit)
        self.assertIn("source runs outside every transaction", propose)
        self.assertIn("adapter code that the caller supplies", propose)
        self.assertIn("candidatesourceerror", propose)

    def test_d33_no_shipped_surface_calls_submission_cheap(self) -> None:
        """D33. Scanning README, docs, and runtime prose rejects four banned claims and finds all three published price terms."""
        paths = (
            ROOT / "README.md",
            *sorted((ROOT / "docs").glob("*.md")),
            *sorted((ROOT / "src").rglob("*.py")),
        )
        shipped_prose = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
        for banned in ("cheap", "safe-to-retry", "deduplicated", "request-free"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, shipped_prose)

        readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("one request row, one proposal row, and one `proposal.created` event", readme)
        self.assertIn("no idempotency", readme)
        self.assertIn("`propose` invokes the configured source one time", readme)

    def test_d34_readme_and_the_three_normative_docs(self) -> None:
        """D34. Route-qualified sentences in all four normative files distinguish direct, source, and handle behavior."""
        required = {
            ROOT / "README.md": (
                "`submit_proposal` takes the candidate from the caller",
                "it never invokes the configured candidate source",
                "`propose` invokes the configured source one time",
            ),
            ROOT / "docs/architecture.md": (
                "steps 1 to 3 describe `handle`, the request lifecycle",
                "two methods enter the same pipeline at step 3 alone",
                "schema v2 keeps it as internal storage",
            ),
            ROOT / "docs/threat-model.md": (
                "`submit_proposal` and `propose` give no idempotency",
                "each call writes a new proposal",
                "do not repeat those calls to recover",
            ),
            ROOT / "docs/adapter-protocol.md": (
                "through `handle`",
                "through `system.propose`, the same failures raise `candidatesourceerror`",
                "`system.propose` invokes the adapter at most one time for each call",
                "invokes the adapter zero times",
            ),
        }
        for path, fragments in required.items():
            normalized = " ".join(path.read_text(encoding="utf-8").lower().split())
            for fragment in fragments:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, normalized)

    def test_d35_propose_precedence_arguments_then_source_is_1(self) -> None:
        """D35. Invalid input beside a None source returns JSON validation before configuration and opens no transaction."""
        system, _ = self.new_system()
        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transactions:
            with self.assertRaisesRegex(
                cement_runtime.ValidationError,
                r"^cement-json-v1 supports integers; encode decimals as strings$",
            ):
                system.propose(PARTITION, OPERATION, 1.5)
        transactions.assert_not_called()

    def test_d35_propose_precedence_arguments_then_source_is_2(self) -> None:
        """D35. A None source beside an absent operation returns configuration first and performs zero ledger transactions."""
        system, _ = self.new_system()
        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transactions:
            with self.assertRaisesRegex(
                cement_runtime.StateError,
                r"^candidate source is not configured$",
            ):
                system.propose(PARTITION, "absent_35", INPUT)
        transactions.assert_not_called()

    def test_d35_propose_precedence_arguments_then_source_is_3(self) -> None:
        """D35. An absent operation beside a raising source returns NotFound with zero calls, then a valid lookup proves the counter live."""
        source = _RaisingSource(RuntimeError("invocation_35"))
        system, _ = self.new_system(source=source)

        with self.assertRaisesRegex(
            cement_runtime.NotFoundError,
            r"^operation is not registered in this partition$",
        ):
            system.propose(PARTITION, "absent_35", INPUT)
        self.assertEqual(source.calls, 0)

        with self.assertRaises(cement_runtime.CandidateSourceError):
            system.propose(PARTITION, OPERATION, INPUT)
        self.assertEqual(source.calls, 1, "source counter positive control")

    def test_d36_propose_snapshots_candidate_source_once_so(self) -> None:
        """D36. A getter swaps sources after its first read; one read invokes the returned source and never the replacement."""
        first_candidate = Candidate(
            output={"authority": "first", "value": 36},
            provenance={"source": "first_36"},
        )
        first = _ReturningSource(first_candidate)
        replacement = _RaisingSource(RuntimeError("replacement must stay unused"))

        class ReassigningSystem(System):
            def __init__(self, path: Path) -> None:
                self.source_reads = 0
                self.armed = False
                self.replacement = replacement
                self._candidate_source_value: object | None = first
                super().__init__(
                    path,
                    candidate_source=first,
                    clock_us=lambda: 1_700_000_000_036_000,
                )

            @property
            def candidate_source(self) -> object | None:
                self.source_reads += 1
                value = self._candidate_source_value
                if self.armed:
                    self._candidate_source_value = self.replacement
                return value

            @candidate_source.setter
            def candidate_source(self, value: object | None) -> None:
                self._candidate_source_value = value

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        system = ReassigningSystem(Path(directory.name) / "ledger.db")
        system.register_operation(PARTITION, OPERATION)
        system.source_reads = 0
        system._candidate_source_value = first
        system.armed = True

        proposal_id = system.propose(PARTITION, OPERATION, INPUT)

        self.assertEqual(system.source_reads, 1)
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(replacement.calls, 0)
        self.assertEqual(
            system.get_proposal(PARTITION, proposal_id).proposed_output,
            first_candidate.output,
        )

    def test_d37_unusable_non_none_configuration_is_contained(self) -> None:
        """D37. Missing, non-callable, and secret-raising propose attributes all normalize to one contained error and zero footprint."""
        secret = "DESCRIPTOR_SECRET_37"

        class NonCallableSource:
            propose = 37

        class RaisingPropose:
            def __init__(self) -> None:
                self.accesses = 0

            def __get__(self, instance: object, owner: object) -> object:
                del instance, owner
                self.accesses += 1
                raise RuntimeError(secret)

        descriptor = RaisingPropose()

        class DescriptorSource:
            propose = descriptor

        cases = (
            ("missing", object()),
            ("noncallable", NonCallableSource()),
            ("descriptor", DescriptorSource()),
        )
        for label, source in cases:
            with self.subTest(label=label):
                system, path = self.new_system(source=_ReturningSource())
                system.candidate_source = source  # Exercise mutable live configuration, not constructor policy.
                before = self.table_counts(path)
                with self.assertRaises(cement_runtime.CandidateSourceError) as raised:
                    system.propose(PARTITION, OPERATION, INPUT)
                error = raised.exception
                self.assertEqual(str(error), "candidate source failed")
                self.assertIsNone(error.__cause__)
                self.assertIsNone(error.__context__)
                self.assertNotIn(secret, str(error))
                self.assertNotIn(secret, repr(error))
                self.assertEqual(self.table_counts(path), before)

        self.assertEqual(descriptor.accesses, 1)

    def test_d37_constructor_does_not_preflight_unusable_sources(self) -> None:
        """D37. Constructing with each unusable non-None source must defer its classification to contained propose execution."""
        secret = "CONSTRUCTOR_DESCRIPTOR_SECRET_37"

        class NonCallableSource:
            propose = 37

        class RaisingPropose:
            def __get__(self, instance: object, owner: object) -> object:
                del instance, owner
                raise RuntimeError(secret)

        class DescriptorSource:
            propose = RaisingPropose()

        defects: list[str] = []
        for label, source in (
            ("missing", object()),
            ("noncallable", NonCallableSource()),
            ("descriptor", DescriptorSource()),
        ):
            directory = tempfile.TemporaryDirectory()
            self.addCleanup(directory.cleanup)
            try:
                system = System(
                    Path(directory.name) / "ledger.db",
                    candidate_source=source,  # type: ignore[arg-type]
                    clock_us=lambda: 1_700_000_000_037_000,
                )
            except BaseException as error:
                defects.append(
                    f"{label}: constructor raised {type(error).__name__}: {error}"
                )
                continue
            system.register_operation(PARTITION, OPERATION)
            try:
                system.propose(PARTITION, OPERATION, INPUT)
            except cement_runtime.CandidateSourceError:
                continue
            except BaseException as error:
                defects.append(f"{label}: propose leaked {type(error).__name__}: {error}")
            else:
                defects.append(f"{label}: propose returned instead of containing failure")

        self.assertEqual(defects, [])

    def test_d38_a_malformed_source_return_is_contained(self) -> None:
        """D38. Five malformed returns match a raised adapter error's public observation, erase a mapping secret, and write nothing."""
        secret = "MAPPING_ACCESS_SECRET_38"

        class ExplodingAccess(Mapping[str, object]):
            """D38's settling case, placed on the path ``dict(Mapping)`` reads."""

            def __getitem__(self, key: str) -> object:
                raise RuntimeError(secret)

            def __iter__(self) -> Iterator[str]:
                raise RuntimeError(secret)

            def __len__(self) -> int:
                return 1

        def observe(source: object) -> tuple[tuple[object, ...] | None, list[str]]:
            system, path = self.new_system(source=source)
            before = self.table_counts(path)
            error: cement_runtime.CandidateSourceError | None = None
            returned: object | None = None
            try:
                returned = system.propose(PARTITION, OPERATION, INPUT)
            except cement_runtime.CandidateSourceError as caught:
                error = caught
            after = self.table_counts(path)
            defects: list[str] = []
            if error is None:
                defects.append(f"returned {returned!r} instead of raising CandidateSourceError")
            if after != before:
                defects.append(
                    "footprint changed: "
                    + repr({table: after[table] - before[table] for table in before})
                )
            if error is None:
                return None, defects
            observation = (
                type(error),
                error.args,
                str(error),
                repr(error),
                error.__cause__,
                error.__context__,
            )
            return observation, defects

        raised_observation, raised_defects = observe(
            _RaisingSource(RuntimeError("raised_38"))
        )
        self.assertEqual(raised_defects, [])
        self.assertIsNotNone(raised_observation)
        malformed = (
            ("non-candidate", object()),
            ("bad-output", Candidate(output=1.5, provenance={})),
            (
                "non-mapping",
                Candidate(output={}, provenance=object()),  # type: ignore[arg-type]
            ),
            (
                "non-json-object",
                Candidate(output={}, provenance={38: "bad"}),  # type: ignore[dict-item]
            ),
            ("access-raises", Candidate(output={}, provenance=ExplodingAccess())),
        )
        for label, returned in malformed:
            with self.subTest(label=label):
                source = _CallbackSource(lambda request, value=returned: value)  # type: ignore[return-value]
                observation, defects = observe(source)
                self.assertEqual(defects, [])
                self.assertEqual(observation, raised_observation)
                self.assertEqual(len(source.calls), 1)
                self.assertIsNotNone(observation)
                self.assertNotIn(secret, observation[2])
                self.assertNotIn(secret, observation[3])

    def test_d38_direct_malformed_candidates_keep_validation_taxonomy(self) -> None:
        """D38. The same malformed shapes owned by a direct caller raise their exact ValidationError texts before any transaction."""
        cases = (
            (
                "non-candidate",
                object(),
                "candidate must be a Candidate",
            ),
            (
                "non-mapping",
                Candidate(output={}, provenance=object()),  # type: ignore[arg-type]
                "candidate provenance must be a mapping",
            ),
            (
                "non-json-object",
                Candidate(output={}, provenance={38: "bad"}),  # type: ignore[dict-item]
                "JSON object keys must be strings",
            ),
            (
                "bad-output",
                Candidate(output=1.5, provenance={}),
                "cement-json-v1 supports integers; encode decimals as strings",
            ),
            (
                "bad-provenance-value",
                Candidate(output={}, provenance={"value": 1.5}),
                "cement-json-v1 supports integers; encode decimals as strings",
            ),
        )
        for label, candidate, message in cases:
            with self.subTest(label=label):
                system, _ = self.new_system()
                with mock.patch.object(
                    system.store,
                    "transaction",
                    wraps=system.store.transaction,
                ) as transactions:
                    with self.assertRaises(cement_runtime.ValidationError) as raised:
                        system.submit_proposal(
                            PARTITION,
                            OPERATION,
                            INPUT,
                            candidate=candidate,  # type: ignore[arg-type]
                        )
                self.assertEqual(str(raised.exception), message)
                transactions.assert_not_called()

    def test_d39_the_catch_is_exactly_exception_baseexception(self) -> None:
        """D39. Four process-control BaseExceptions propagate by identity while counts, sequence, bytes, and dump stay unchanged."""
        class BaseRaisingSource:
            def __init__(self, error: BaseException) -> None:
                self.error = error
                self.calls = 0

            def propose(self, request: object) -> Candidate:
                del request
                self.calls += 1
                raise self.error

        errors: tuple[BaseException, ...] = (
            KeyboardInterrupt("keyboard_39"),
            SystemExit(39),
            GeneratorExit("generator_39"),
            asyncio.CancelledError("cancelled_39"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                source = BaseRaisingSource(error)
                system, path = self.new_system(source=source)
                before = self.ledger_snapshot(path)

                with self.assertRaises(type(error)) as raised:
                    system.propose(PARTITION, OPERATION, INPUT)

                self.assertIs(raised.exception, error)
                self.assertEqual(source.calls, 1)
                self.assertEqual(self.ledger_snapshot(path), before)

    def test_d40_one_canonical_snapshot_serves_the_call(self) -> None:
        """D40. Adapter mutation of detached CandidateRequest.input changes neither caller containers nor stored canonical text and hash."""
        caller_input = {
            "nested": {"value": 40},
            "items": [10, 11, 12],
        }
        original = json.loads(json.dumps(caller_input))
        expected = canonicalize(original)
        seen_before_mutation: list[object] = []
        captured_requests: list[CandidateRequest] = []

        def mutate(request: object) -> Candidate:
            self.assertIs(type(request), CandidateRequest)
            typed_request = request
            captured_requests.append(typed_request)
            seen_before_mutation.append(json.loads(json.dumps(typed_request.input)))
            typed_request.input["nested"]["value"] = 400  # type: ignore[index]
            typed_request.input["items"].append(13)  # type: ignore[index, union-attr]
            return CANDIDATE

        source = _CallbackSource(mutate)
        system, path = self.new_system(source=source)
        proposal_id = system.propose(PARTITION, OPERATION, caller_input)

        with closing(sqlite3.connect(path)) as connection:
            row = connection.execute(
                "SELECT id, partition, operation, operation_revision, input_json, input_hash "
                "FROM requests WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()

        self.assertEqual(caller_input, original)
        self.assertEqual(seen_before_mutation, [original])
        self.assertIsNot(captured_requests[0].input, caller_input)
        self.assertNotEqual(captured_requests[0].input, original)
        self.assertEqual(row[1:], (PARTITION, OPERATION, 1, expected.text, expected.digest))
        self.assertEqual(system.get_proposal(PARTITION, proposal_id).input, original)

    def test_d40_unusable_adapter_mutation_is_never_recanonicalized(self) -> None:
        """D40. Mutating detached source input to a forbidden float still succeeds from the pre-invocation canonical snapshot."""
        caller_input = {"value": 40, "nested": {"stable": 41}}
        expected = canonicalize(caller_input)

        def poison(request: object) -> Candidate:
            self.assertIs(type(request), CandidateRequest)
            request.input["value"] = 4.5  # type: ignore[index]
            request.input["nested"]["stable"] = 4.6  # type: ignore[index]
            return CANDIDATE

        source = _CallbackSource(poison)
        system, path = self.new_system(source=source)
        proposal_id = system.propose(PARTITION, OPERATION, caller_input)

        with closing(sqlite3.connect(path)) as connection:
            stored = connection.execute(
                "SELECT input_json, input_hash FROM requests WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        self.assertEqual(stored, (expected.text, expected.digest))
        self.assertEqual(caller_input, {"value": 40, "nested": {"stable": 41}})
        self.assertEqual(system.get_proposal(PARTITION, proposal_id).input, caller_input)

    def test_d41_readme_and_the_normative_docs_name(self) -> None:
        """D41. Public prose names both methods and states authority, string return, three-row cost, no idempotency, containment, and retained row."""
        paths = (
            ROOT / "README.md",
            ROOT / "docs/architecture.md",
            ROOT / "docs/threat-model.md",
            ROOT / "docs/adapter-protocol.md",
        )
        normalized_by_path = {
            path: " ".join(path.read_text(encoding="utf-8").lower().split())
            for path in paths
        }
        combined = " ".join(normalized_by_path.values())

        for method in ("submit_proposal", "propose"):
            with self.subTest(method=method):
                self.assertIn(method, combined)
        self.assertIn("`submit_proposal` takes the candidate from the caller", combined)
        self.assertIn("`propose` invokes the configured source one time", combined)
        self.assertIn("both methods return the new proposal identifier as a string", combined)
        self.assertIn(
            "each call writes one request row, one proposal row, and one `proposal.created` event",
            combined,
        )
        self.assertIn("cement gives no idempotency here", combined)
        self.assertIn("that error carries no detail from the source", combined)
        self.assertIn("schema v2 keeps the row", combined)
        self.assertIn("no proposal, review, or report value shows it", combined)

    def test_d42_the_proposal_row_shape_including_status(self) -> None:
        """D42. Full-row comparison on both routes pins canonical content, pending defaults, shared time, request FK, and event sequence."""
        expected_output = canonicalize(CANDIDATE.output)
        expected_provenance = canonicalize(dict(CANDIDATE.provenance))
        expected_columns = {
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
        }

        for route in ("direct", "source"):
            with self.subTest(route=route):
                source = _ReturningSource() if route == "source" else None
                system, path = self.new_system(source=source)
                if route == "direct":
                    proposal_id = system.submit_proposal(
                        PARTITION,
                        OPERATION,
                        INPUT,
                        candidate=CANDIDATE,
                    )
                else:
                    proposal_id = system.propose(PARTITION, OPERATION, INPUT)

                with closing(sqlite3.connect(path)) as connection:
                    connection.row_factory = sqlite3.Row
                    proposal = dict(
                        connection.execute(
                            "SELECT * FROM proposals WHERE id = ?",
                            (proposal_id,),
                        ).fetchone()
                    )
                    request = connection.execute(
                        "SELECT id, partition, proposal_id, created_at_us FROM requests "
                        "WHERE id = ?",
                        (proposal["request_id"],),
                    ).fetchone()
                    event = connection.execute(
                        "SELECT sequence, subject_id, created_at_us FROM events "
                        "WHERE kind = 'proposal.created' AND subject_id = ?",
                        (proposal_id,),
                    ).fetchone()

                self.assertEqual(set(proposal), expected_columns)
                self.assertEqual(proposal["id"], proposal_id)
                self.assertTrue(proposal_id.startswith("prop_"))
                self.assertEqual(proposal["partition"], PARTITION)
                self.assertTrue(str(proposal["request_id"]).startswith("req_"))
                self.assertEqual(proposal["proposed_output_json"], expected_output.text)
                self.assertEqual(proposal["proposed_output_hash"], expected_output.digest)
                self.assertEqual(proposal["provenance_json"], expected_provenance.text)
                self.assertEqual(proposal["provenance_hash"], expected_provenance.digest)
                self.assertEqual(proposal["status"], "pending")
                self.assertEqual(
                    tuple(
                        proposal[name]
                        for name in (
                            "final_output_json",
                            "final_output_hash",
                            "reviewer",
                            "review_note",
                            "reviewed_at_us",
                        )
                    ),
                    (None, None, None, None, None),
                )
                self.assertEqual(
                    tuple(request),
                    (
                        proposal["request_id"],
                        PARTITION,
                        proposal_id,
                        proposal["created_at_us"],
                    ),
                )
                self.assertEqual(event[1], proposal_id)
                self.assertEqual(event[2], proposal["created_at_us"])
                self.assertEqual(proposal["status_sequence"], event[0])

    def test_d43_candidate_is_exactly_candidate_and_provenance(self) -> None:
        """D43. A Candidate subclass and four pair-iterable provenances are rejected on the direct path with the published texts."""

        class SubclassedCandidate(Candidate):
            """A subclass may reimplement output or provenance as a descriptor."""

        system, path = self.new_system()
        before = self.ledger_snapshot(path)
        pairs = (("model", "adapter_43"),)
        rejected = (
            (
                "candidate-subclass",
                SubclassedCandidate(output={"answer": 43}, provenance={}),
                "candidate must be a Candidate",
            ),
            (
                "list-of-pairs",
                Candidate(output={}, provenance=list(pairs)),  # type: ignore[arg-type]
                "candidate provenance must be a mapping",
            ),
            (
                "tuple-of-pairs",
                Candidate(output={}, provenance=pairs),  # type: ignore[arg-type]
                "candidate provenance must be a mapping",
            ),
            (
                "generator-of-pairs",
                Candidate(output={}, provenance=(pair for pair in pairs)),  # type: ignore[arg-type]
                "candidate provenance must be a mapping",
            ),
            (
                "keys-only-duck-type",
                Candidate(output={}, provenance=_DuckMapping()),  # type: ignore[arg-type]
                "candidate provenance must be a mapping",
            ),
        )
        for label, candidate, message in rejected:
            with self.subTest(label=label):
                with self.assertRaises(cement_runtime.ValidationError) as raised:
                    system.submit_proposal(PARTITION, OPERATION, INPUT, candidate=candidate)
                self.assertEqual(str(raised.exception), message)

        self.assertEqual(self.ledger_snapshot(path), before)

    def test_d43_source_returned_pair_iterables_are_contained(self) -> None:
        """D43. The same pair iterables returned by a source raise the contained error, never ValidationError, and drain no iterator."""
        drained: list[str] = []

        def counting_pairs() -> Iterator[tuple[str, str]]:
            drained.append("entered")
            yield ("model", "adapter_43")

        returned = (
            ("list-of-pairs", [("model", "adapter_43")]),
            ("generator-of-pairs", counting_pairs()),
            ("keys-only-duck-type", _DuckMapping()),
        )
        for label, provenance in returned:
            with self.subTest(label=label):
                source = _ReturningSource(
                    Candidate(output={}, provenance=provenance)  # type: ignore[arg-type]
                )
                system, path = self.new_system(source=source)
                before = self.ledger_snapshot(path)

                with self.assertRaisesRegex(
                    cement_runtime.CandidateSourceError, r"^candidate source failed$"
                ):
                    system.propose(PARTITION, OPERATION, INPUT)

                self.assertEqual(len(source.calls), 1)
                self.assertEqual(self.ledger_snapshot(path), before)

        self.assertEqual(drained, [])

    def test_d44_provenance_canonicalizes_under_65_536_bytes(self) -> None:
        """D44. Provenance one byte over 65,536 raises the exact bound text while the same payload passes as output."""
        filler = "x" * 65_536
        oversized = {"model": filler}
        self.assertGreater(len(canonicalize(oversized).text.encode("utf-8")), 65_536)

        system, path = self.new_system(source=_ReturningSource(Candidate(output={}, provenance=oversized)))
        before = self.ledger_snapshot(path)

        with self.assertRaises(cement_runtime.ValidationError) as raised:
            system.submit_proposal(
                PARTITION,
                OPERATION,
                INPUT,
                candidate=Candidate(output={}, provenance=oversized),
            )
        self.assertEqual(str(raised.exception), "canonical JSON exceeds 65536 bytes")

        with self.assertRaisesRegex(
            cement_runtime.CandidateSourceError, r"^candidate source failed$"
        ):
            system.propose(PARTITION, OPERATION, INPUT)
        self.assertEqual(self.ledger_snapshot(path), before)

        # The same payload as OUTPUT clears the module default, so the failure
        # above measures the provenance bound and not the payload's size.
        accepted = system.submit_proposal(
            PARTITION,
            OPERATION,
            INPUT,
            candidate=Candidate(output=oversized, provenance={"model": "adapter_44"}),
        )
        self.assertTrue(accepted.startswith("prop_"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
