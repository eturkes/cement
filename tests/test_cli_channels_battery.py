"""M3.5a obligation battery: one test per contract obligation D01-D30.

Seeded by `.agent/decisions/m3u5a-battery-validate.py --emit-stub` from the
obligation bullets in `m3u5a-contract.md`. Each docstring carries its obligation
verbatim, followed by every amendment that binds it; the body is the work.

An AMENDED obligation is encoded in its AMENDED form. The amendment supersedes the
bullet text above it, so encoding the literal bullet is a defect that goes red
against correct code.

Replace each `self.fail` marker with real assertions. A body that asserts nothing is
graded ASSERTIONLESS, and a body that skips is graded SKIPPED. Both fail the
validator.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import dataclasses
import hashlib
import inspect
import io
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from contextlib import closing
from unittest import mock

from cement_runtime import (
    Candidate,
    CementError,
    CommandCandidateSource,
    CompilePolicy,
    ConflictError,
    FunctionCheck,
    FunctionDocument,
    FunctionMatch,
    FunctionResolution,
    FunctionVerification,
    IntegrityError,
    NotFoundError,
    StateError,
    System,
    ValidationError,
)
from cement_runtime import cli as cement_cli
from cement_runtime import store as store_module
from cement_runtime import system as system_module
from cement_runtime.json_value import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
)
from cement_runtime.store import SCHEMA_VERSION, Store

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARTITION = "tenant_a"
OPERATION = "echo_1"


class _BinaryStdin(io.StringIO):
    def __init__(self, raw: bytes) -> None:
        super().__init__("")
        self.buffer = io.BytesIO(raw)


class _FailingBuffer:
    def read(self, size: int = -1) -> bytes:
        del size
        raise OSError("planted stdin failure")


class _FailingBinaryStdin(io.StringIO):
    def __init__(self) -> None:
        super().__init__("")
        self.buffer = _FailingBuffer()


class _FailingTextStdin(io.StringIO):
    """Text-only host whose read fails; `StringIO` exposes no `.buffer` (A18)."""

    def read(self, size: int | None = -1) -> str:
        del size
        raise OSError("planted stdin failure")


class _ExplodingSource:
    def __getattribute__(self, name: str) -> object:
        if name.startswith("__"):
            return object.__getattribute__(self, name)
        raise AssertionError(f"candidate source reached through {name}")


def _invoke(
    argv: list[str],
    *,
    stdin: io.TextIOBase | None = None,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    saved_stdin = sys.stdin
    if stdin is not None:
        sys.stdin = stdin
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cement_cli.main(argv)
    finally:
        sys.stdin = saved_stdin
    return status, stdout.getvalue(), stderr.getvalue()


def _payload(text: str) -> object:
    return json.loads(text)


def _leaf_parser(
    case: unittest.TestCase,
    parser: argparse.ArgumentParser,
    path: tuple[str, ...],
) -> argparse.ArgumentParser:
    current = parser
    for name in path:
        actions = [
            action
            for action in current._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        case.assertEqual(len(actions), 1)
        case.assertIn(name, actions[0].choices)
        current = actions[0].choices[name]
    return current


def _leaf_parsers(
    parser: argparse.ArgumentParser,
) -> dict[str, argparse.ArgumentParser]:
    leaves: dict[str, argparse.ArgumentParser] = {}

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        actions = [
            action
            for action in node._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if not actions:
            leaves[" ".join(path)] = node
            return
        for action in actions:
            for name, child in action.choices.items():
                visit(child, (*path, name))

    visit(parser, ())
    return leaves


def _help_surfaces(parser: argparse.ArgumentParser) -> str:
    """Every help screen an operator can render, root and intermediates included.

    A subcommand's `help=` string renders in its PARENT's listing and nowhere in
    its own `format_help()`, so a leaf-only scan sees no `add_parser` help text.
    """

    screens: list[str] = []

    def visit(node: argparse.ArgumentParser) -> None:
        screens.append(node.format_help())
        for action in node._actions:
            if isinstance(action, argparse._SubParsersAction):
                for child in action.choices.values():
                    visit(child)

    visit(parser)
    return "\n".join(screens)


def _parser_census(parser: argparse.ArgumentParser) -> tuple[set[str], int]:
    leaves: set[str] = set()
    nodes = 0

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        nonlocal nodes
        nodes += 1
        actions = [
            action
            for action in node._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if not actions:
            leaves.add(" ".join(path))
            return
        for action in actions:
            for name, child in action.choices.items():
                visit(child, (*path, name))

    visit(parser, ())
    return leaves, nodes


def _resolution(state: str) -> FunctionResolution:
    checks = (
        FunctionCheck("duplicate-input-digests", True, "no duplicates"),
        FunctionCheck("function-abi", True, "ABI matches"),
        FunctionCheck("artifact-reports", True, "reports pass"),
        FunctionCheck("promotion-receipt", True, "receipt matches"),
        FunctionCheck("function-hash", state != "failed", "hash verdict"),
        FunctionCheck("persisted-function-receipt", True, "receipt persisted"),
    )
    verification = FunctionVerification(
        passed=state != "failed",
        entries=12,
        document=None,
        function_hash=("f" if state != "failed" else "e") * 64,
        checks=checks,
    )
    if state == "hit":
        match = FunctionMatch(
            matched=True, output={"answer": 12}, artifact_hash="a" * 64
        )
    elif state == "miss":
        match = FunctionMatch(matched=False)
    elif state == "failed":
        match = None
    else:
        raise AssertionError(f"unknown resolution state {state!r}")
    return FunctionResolution(verification=verification, match=match)


def _temporary_path(case: unittest.TestCase, name: str = "ledger.db") -> pathlib.Path:
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    return pathlib.Path(directory.name) / name


def _new_system(
    case: unittest.TestCase,
    *,
    source: object | None = None,
    register: bool = True,
) -> tuple[System, pathlib.Path]:
    path = _temporary_path(case)
    system = System(
        path, candidate_source=source, clock_us=lambda: 1_700_000_000_010_000
    )
    if register:
        system.register_operation(PARTITION, OPERATION, policy=CompilePolicy(2, 2, 0))
    return system, path


def _promote_values(
    case: unittest.TestCase,
    system: System,
    values: tuple[object, ...],
) -> tuple[str, ...]:
    for index, value in enumerate(values):
        for reviewer in ("alice", "bob"):
            proposal_id = system.submit_proposal(
                PARTITION,
                OPERATION,
                value,
                candidate=Candidate(
                    output={"echo": value},
                    provenance={"fixture": f"value-{index}"},
                ),
            )
            system.review(
                PARTITION,
                proposal_id,
                reviewer=reviewer,
                decision="accept",
            )
    compiled = system.compile(PARTITION, OPERATION)
    case.assertEqual(len(compiled.created), len(values))
    for artifact_id in compiled.created:
        report = system.verify(PARTITION, artifact_id)
        case.assertTrue(report.passed)
        system.promote(
            PARTITION,
            artifact_id,
            scope_hash=report.scope_hash,
            promoted_by="release-manager",
        )
    manifest = system.inspect_function_promotion(PARTITION, OPERATION)
    system.promote_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
        promoted_by="release-manager",
    )
    return compiled.created


def _ledger_snapshot(
    path: pathlib.Path,
) -> tuple[str, tuple[str, ...], int, dict[str, bytes]]:
    with closing(sqlite3.connect(path)) as connection:
        dump = tuple(connection.iterdump())
        events = int(connection.execute("SELECT count(*) FROM events").fetchone()[0])
    sidecars = {
        sibling.name: sibling.read_bytes()
        for sibling in path.parent.glob(f"{path.name}-*")
        if sibling.is_file()
    }
    return hashlib.sha256(path.read_bytes()).hexdigest(), dump, events, sidecars


def _recording_transaction(calls: list[bool]) -> object:
    original = Store.transaction

    def recording(store: Store, *, write: bool = False) -> object:
        calls.append(write)
        return original(store, write=write)

    return recording


def _table_counts(path: pathlib.Path) -> dict[str, int]:
    with closing(sqlite3.connect(path)) as connection:
        tables = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        )
        return {
            table: int(
                connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            )
            for table in tables
        }


class ObligationBatteryTests(unittest.TestCase):
    """One test per M3.5a contract obligation, encoded in its amended form."""

    def test_d01_grammar_is_exactly_one_positional_operation_one_required_i(
        self,
    ) -> None:
        """D01 obligation

        CONTRACT:
        Grammar is exactly one positional `operation`, one required `--input`, one optional
        `--expected-function-hash` defaulting to `None`. The node sets `allow_abbrev=False`, so
        `--in`, `--exp` and every other prefix is `unrecognized arguments` rather than a silent
        alias.

        AMENDED-BY A1, superseding the text above:
        The guarantee is that no option prefix ever BINDS: every prefix invocation exits 2 with
        empty stdout. The message is `unrecognized arguments: <prefix> <value>` only when the
        required option is separately supplied. A prefix standing IN PLACE of the required
        option answers `the following arguments are required: --input` (or `--submission`),
        because argparse runs its required check inside `parse_known_args`, ahead of the
        leftover check in `parse_args`. D01's "every other prefix is `unrecognized arguments`"
        named one of the two messages as if it were the property.

        AMENDED-BY A17, superseding the text above:
        The prefix rejection is scoped to prefixes of the LEAF'S OWN options. Root options are
        parsed by the root parser before the child is reached, so `--d` and `--part` keep
        resolving under a hardened child — which is what D25 preserves. Measured: `--d x.sqlite
        --part p resolve op --input 1` retains `db=x.sqlite partition=p`. Unscoped, D01 and D25
        demand opposite results for one invocation (`Y24`).
        """
        # BASELINE c8b82cd: red — the root resolve leaf is absent.
        parser = cement_cli._parser()
        resolve = _leaf_parser(self, parser, ("resolve",))
        destinations = {
            action.dest for action in resolve._actions if action.dest != "help"
        }
        self.assertEqual(destinations, {"operation", "input", "expected_function_hash"})
        self.assertFalse(resolve.allow_abbrev)

        parsed = parser.parse_args(
            [
                "--db",
                "ledger.db",
                "--partition",
                PARTITION,
                "resolve",
                OPERATION,
                "--input",
                "0",
            ]
        )
        self.assertEqual(parsed.operation, OPERATION)
        self.assertEqual(parsed.input, "0")
        self.assertIsNone(parsed.expected_function_hash)
        for argv, required in (
            (["resolve", "--input", "0"], "operation"),
            (["resolve", OPERATION], "--input"),
        ):
            with (
                self.subTest(required=required),
                self.assertRaises(cement_cli._UsageError) as caught,
            ):
                parser.parse_args(argv)
            self.assertIn(
                f"the following arguments are required: {required}",
                str(caught.exception),
            )

        prefixes = sorted(
            {
                option[:end]
                for option in ("--input", "--expected-function-hash")
                for end in range(3, len(option))
            }
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                status, stdout, stderr = _invoke(
                    [
                        "--db",
                        "unused.db",
                        "--partition",
                        PARTITION,
                        "resolve",
                        OPERATION,
                        "--input",
                        "0",
                        prefix,
                        "sentinel",
                    ]
                )
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertEqual(
                    _payload(stderr)["message"],
                    f"unrecognized arguments: {prefix} sentinel",
                )

        status, stdout, stderr = _invoke(
            [
                "--db",
                "unused.db",
                "--partition",
                PARTITION,
                "resolve",
                OPERATION,
                "--in",
                "0",
            ]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "the following arguments are required: --input",
        )

        repeated = parser.parse_args(
            [
                "resolve",
                OPERATION,
                "--input",
                "1",
                "--input",
                "12",
                "--expected-function-hash",
                "a" * 64,
                "--expected-function-hash",
                "b" * 64,
            ]
        )
        self.assertEqual(
            (repeated.input, repeated.expected_function_hash), ("12", "b" * 64)
        )

    def test_d02_input_accepts_inline_json_text_or_through_the_shipped_inpu(
        self,
    ) -> None:
        """D02 obligation

        CONTRACT:
        `--input` accepts inline JSON text or `-` through the shipped `_input`, inheriting its
        1,048,576-byte bound and its three exact failure families (`M07`, `M24`). Resolve adds
        no reader.
        """
        # BASELINE c8b82cd: red — no CLI route can carry _input into System.resolve.
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.resolve.return_value = _resolution("hit")
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "resolve",
            OPERATION,
            "--input",
        ]

        with (
            mock.patch.object(cement_cli, "System", return_value=fake),
            mock.patch.object(cement_cli, "_input", wraps=cement_cli._input) as reader,
        ):
            status, stdout, stderr = _invoke([*base, '{"n":12}'])
        self.assertEqual((status, stderr), (0, ""))
        self.assertTrue(_payload(stdout)["matched"])
        reader.assert_called_once_with('{"n":12}')
        fake.resolve.assert_called_once_with(
            PARTITION,
            OPERATION,
            {"n": 12},
            expected_function_hash=None,
        )

        maximal = b'"' + b"x" * (DEFAULT_MAX_BYTES - 2) + b'"'
        self.assertEqual(len(maximal), DEFAULT_MAX_BYTES)
        fake.reset_mock()
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, _, stderr = _invoke([*base, "-"], stdin=_BinaryStdin(maximal))
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(len(fake.resolve.call_args.args[2]), DEFAULT_MAX_BYTES - 2)

        over = b'"' + b"x" * (DEFAULT_MAX_BYTES - 1) + b'"'
        self.assertEqual(len(over), DEFAULT_MAX_BYTES + 1)
        failures = (
            (_BinaryStdin(over), f"JSON stdin exceeds {DEFAULT_MAX_BYTES} bytes"),
            (_FailingBinaryStdin(), "JSON stdin could not be read"),
            (_BinaryStdin(b"\xff"), "JSON stdin is not valid UTF-8"),
        )
        for stdin, message in failures:
            with self.subTest(message=message):
                fake.reset_mock()
                with mock.patch.object(cement_cli, "System", return_value=fake):
                    status, stdout, stderr = _invoke([*base, "-"], stdin=stdin)
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(_payload(stderr)["message"], message)
                fake.resolve.assert_not_called()

        fake.reset_mock()
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke([*base, "{"])
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "invalid JSON: Expecting property name enclosed in double quotes: "
            "line 1 column 2 (char 1)",
        )
        fake.resolve.assert_not_called()

    def test_d03_dispatch_calls_system_resolve_exactly_once_and_reaches_no(
        self,
    ) -> None:
        """D03 obligation

        CONTRACT:
        Dispatch calls `System.resolve` exactly once and reaches no candidate source: zero
        `_source` calls, zero `System.propose` calls, zero `CandidateSource` calls even when
        one is configured (`X19`, `X22`).
        """
        # BASELINE c8b82cd: red — argparse rejects resolve before dispatch.
        path = _temporary_path(self)
        path.touch()
        source = _ExplodingSource()
        fake = mock.create_autospec(System, instance=True)
        fake.candidate_source = source
        fake.resolve.return_value = _resolution("hit")
        # M3.5b D19: the exploding `_source` double targets a deleted symbol, so
        # `mock.patch.object` raises rather than returning a verdict. Absence is
        # the successor and it is stronger: the builder cannot be reached.
        self.assertFalse(hasattr(cement_cli, "_source"))
        with mock.patch.object(cement_cli, "System", return_value=fake) as constructor:
            status, stdout, stderr = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "resolve",
                    OPERATION,
                    "--input",
                    '{"n":12}',
                ]
            )
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(_payload(stdout)["output"], {"answer": 12})
        constructor.assert_called_once()
        self.assertEqual(constructor.call_args.args, (str(path),))
        self.assertIsNone(constructor.call_args.kwargs.get("candidate_source"))
        fake.resolve.assert_called_once_with(
            PARTITION,
            OPERATION,
            {"n": 12},
            expected_function_hash=None,
        )
        fake.verify_function.assert_not_called()
        fake.propose.assert_not_called()
        self.assertIs(fake.candidate_source, source)
        with self.assertRaisesRegex(AssertionError, "candidate source reached"):
            _ = source.propose

    def test_d04_the_db_and_partition_gates_keep_their_shipped_order_and_te(
        self,
    ) -> None:
        """D04 obligation

        CONTRACT:
        The `--db` and `--partition` gates keep their shipped order and text and run before any
        resolve work (`X28`). `resolve` is ledger-backed, so it is never hoisted ahead of them
        the way `function eval` is.
        """
        # BASELINE c8b82cd: red — the gates exist, but no resolve grammar reaches them.
        probes = (
            (["resolve", OPERATION, "--input", "{"], "--db or CEMENT_DB is required"),
            (
                ["--db", "unused.db", "resolve", OPERATION, "--input", "{"],
                "--partition or CEMENT_PARTITION is required",
            ),
        )
        with (
            mock.patch.dict(
                os.environ,
                {"CEMENT_DB": "", "CEMENT_PARTITION": ""},
                clear=False,
            ),
            mock.patch.object(
                cement_cli,
                "_input",
                side_effect=AssertionError("input parsed before global gates"),
            ) as input_reader,
            mock.patch.object(
                cement_cli,
                "System",
                side_effect=AssertionError("System built before global gates"),
            ) as constructor,
        ):
            for argv, message in probes:
                with self.subTest(message=message):
                    status, stdout, stderr = _invoke(argv)
                    self.assertEqual((status, stdout), (2, ""))
                    self.assertEqual(
                        _payload(stderr), {"error": "invalid", "message": message}
                    )
        input_reader.assert_not_called()
        constructor.assert_not_called()

    def test_d05_expected_function_hash_is_forwarded_verbatim_to_the_librar(
        self,
    ) -> None:
        """D05 obligation

        CONTRACT:
        `--expected-function-hash` is forwarded verbatim to the library keyword. Its
        validation, and the whole `partition → operation → expected hash → input` precedence,
        stay library-owned (`M09`, `X16`); the CLI re-implements none of it.

        AMENDED-BY A2, superseding the text above:
        The library owns precedence AMONG library validations — `partition → operation →
        expected hash → input` holds for every value that reaches `System.resolve`. CLI
        value-parsing necessarily precedes all of it, because `--input` must become a value
        before the call exists: `--input '{bad' --expected-function-hash bad` is exit 2
        `invalid JSON: …`, while `--input 1 --expected-function-hash bad` is the library's
        `expected_function_hash must be a SHA-256 hex digest`. Duplicating `_digest` in the CLI
        to restore the literal edge is REJECTED — it puts a second copy of a library validator
        on the surface D05 exists to keep thin.
        """
        # BASELINE c8b82cd: red — no CLI branch forwards the expected hash.
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.resolve.return_value = _resolution("hit")
        sentinel = "Bad-Hash-Forwarded-Verbatim"
        argv = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "resolve",
            OPERATION,
            "--input",
            "12",
            "--expected-function-hash",
            sentinel,
        ]
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, _, stderr = _invoke(argv)
        self.assertEqual((status, stderr), (0, ""))
        fake.resolve.assert_called_once_with(
            PARTITION,
            OPERATION,
            12,
            expected_function_hash=sentinel,
        )

        fake.reset_mock()
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "resolve",
                    OPERATION,
                    "--input",
                    "{bad",
                    "--expected-function-hash",
                    "bad",
                ]
            )
        self.assertEqual((status, stdout), (2, ""))
        self.assertTrue(_payload(stderr)["message"].startswith("invalid JSON:"))
        fake.resolve.assert_not_called()

        _, ledger = _new_system(self)
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                "!",
                "resolve",
                OPERATION,
                "--input",
                "12",
                "--expected-function-hash",
                "bad",
            ]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "partition must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'",
        )

        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "resolve",
                "!",
                "--input",
                "12",
                "--expected-function-hash",
                "bad",
            ]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "operation must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'",
        )

        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "resolve",
                OPERATION,
                "--input",
                "12",
                "--expected-function-hash",
                "bad",
            ]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "expected_function_hash must be a SHA-256 hex digest",
        )
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "resolve",
                OPERATION,
                "--input",
                "12",
                "--expected-function-hash",
                "0" * 64,
            ]
        )
        self.assertEqual((status, stderr), (6, ""))
        self.assertEqual(
            (_payload(stdout)["passed"], _payload(stdout)["matched"]),
            (False, None),
        )

        run_tree = ast.parse(textwrap.dedent(inspect.getsource(cement_cli._run)))
        called_names = {
            node.func.id
            for node in ast.walk(run_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("_digest", called_names)

    def test_d06_one_store_transaction_write_false_is_opened_per_invocation(
        self,
    ) -> None:
        """D06 obligation

        CONTRACT:
        One `Store.transaction(write=False)` is opened per invocation and no ledger byte,
        event, clock read or ID allocation occurs (`X19`).

        AMENDED-BY A3, superseding the text above:
        One `Store.transaction(write=False)` per invocation that REACHES THE LEDGER. A rejected
        invocation opens zero. Observable: `{valid: 1, invalid: 0}`.
        """
        # BASELINE c8b82cd: red — resolve has no full-CLI read-only path.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        system, path = _new_system(self)
        artifact_ids = _promote_values(self, system, ({"n": 12},))
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "resolve",
            OPERATION,
            "--input",
        ]

        states = (("hit", '{"n":12}', 0), ("miss", '{"n":99}', 6))
        for label, input_text, expected_status in states:
            before = _ledger_snapshot(path)
            transaction_calls: list[bool] = []

            with (
                mock.patch.object(
                    Store,
                    "transaction",
                    _recording_transaction(transaction_calls),
                ),
                mock.patch.object(
                    system_module.time,
                    "time_ns",
                    side_effect=AssertionError("resolve read the clock"),
                ) as clock,
                mock.patch.object(
                    system_module,
                    "_new_id",
                    side_effect=AssertionError("resolve allocated an id"),
                ) as identifier,
            ):
                status, _, stderr = _invoke([*base, input_text])
            with self.subTest(state=label):
                self.assertEqual((status, stderr), (expected_status, ""))
                self.assertEqual(transaction_calls, [False])
                self.assertEqual(_ledger_snapshot(path), before)
                clock.assert_not_called()
                identifier.assert_not_called()

        system.suspend_artifact(
            PARTITION,
            artifact_ids[0],
            suspended_by="auditor",
            reason="force a failed verification",
        )
        before = _ledger_snapshot(path)
        transaction_calls = []

        with (
            mock.patch.object(
                Store,
                "transaction",
                _recording_transaction(transaction_calls),
            ),
            mock.patch.object(
                system_module.time,
                "time_ns",
                side_effect=AssertionError("resolve read the clock"),
            ) as failed_clock,
            mock.patch.object(
                system_module,
                "_new_id",
                side_effect=AssertionError("resolve allocated an id"),
            ) as failed_identifier,
        ):
            status, _, stderr = _invoke([*base, '{"n":12}'])
        self.assertEqual((status, stderr), (6, ""))
        self.assertEqual(transaction_calls, [False])
        self.assertEqual(_ledger_snapshot(path), before)
        failed_clock.assert_not_called()
        failed_identifier.assert_not_called()

        transaction_calls = []

        with mock.patch.object(
            Store,
            "transaction",
            _recording_transaction(transaction_calls),
        ):
            status, stdout, _ = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    "!",
                    "resolve",
                    OPERATION,
                    "--input",
                    "12",
                ]
            )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(transaction_calls, [])

    def test_d07_the_payload_key_set_is_exactly_and_identically_in_all_thre(
        self,
    ) -> None:
        """D07 obligation

        CONTRACT:
        The payload key set is exactly, and identically in all three states, `{artifact_hash,
        checks, entries, function_hash, matched, output, passed}`. `_emit` sorts keys, so that
        list is also the emitted order.
        """
        # BASELINE c8b82cd: red — no resolve payload exists.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        expected_order = [
            "artifact_hash",
            "checks",
            "entries",
            "function_hash",
            "matched",
            "output",
            "passed",
        ]
        observed_sets: list[set[str]] = []
        for state, expected_status in (("hit", 0), ("miss", 6), ("failed", 6)):
            fake.resolve.return_value = _resolution(state)
            with mock.patch.object(cement_cli, "System", return_value=fake):
                status, stdout, stderr = _invoke(
                    [
                        "--db",
                        str(path),
                        "--partition",
                        PARTITION,
                        "resolve",
                        OPERATION,
                        "--input",
                        "12",
                    ]
                )
            payload = _payload(stdout)
            self.assertIs(type(payload), dict)
            assert isinstance(payload, dict)
            with self.subTest(state=state):
                self.assertEqual((status, stderr), (expected_status, ""))
                self.assertEqual(set(payload), set(expected_order))
                self.assertEqual(list(payload), expected_order)
            observed_sets.append(set(payload))
        self.assertEqual(observed_sets, [set(expected_order)] * 3)

    def test_d08_passed_verification_passed_entries_verification_entries_fu(
        self,
    ) -> None:
        """D08 obligation

        CONTRACT:
        `passed` ← `verification.passed`; `entries` ← `verification.entries`; `function_hash` ←
        `verification.function_hash`, which survives a failed verdict as a diagnostic (`M14`);
        `checks` ← the ordered `[{key, passed, detail}]` projection `function verify` already
        ships.
        """
        # BASELINE c8b82cd: red — the verification projection has no CLI owner.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        for state in ("hit", "failed"):
            resolution = _resolution(state)
            fake.resolve.return_value = resolution
            with mock.patch.object(cement_cli, "System", return_value=fake):
                _, stdout, _ = _invoke(
                    [
                        "--db",
                        str(path),
                        "--partition",
                        PARTITION,
                        "resolve",
                        OPERATION,
                        "--input",
                        "12",
                    ]
                )
            payload = _payload(stdout)
            assert isinstance(payload, dict)
            verification = resolution.verification
            expected_checks = [
                dataclasses.asdict(check) for check in verification.checks
            ]
            with self.subTest(state=state):
                self.assertEqual(payload["passed"], verification.passed)
                self.assertEqual(payload["entries"], verification.entries)
                self.assertEqual(payload["function_hash"], verification.function_hash)
                self.assertEqual(payload["checks"], expected_checks)
                self.assertEqual(
                    [set(check) for check in payload["checks"]],
                    [{"key", "passed", "detail"}] * len(expected_checks),
                )
                self.assertEqual(
                    payload["checks"][0]["key"], verification.checks[0].key
                )
                self.assertEqual(
                    payload["checks"][-1]["key"], verification.checks[-1].key
                )
        self.assertEqual(len(_resolution("hit").verification.checks), 6)
        self.assertIsNotNone(_payload(stdout)["function_hash"])

    def test_d09_matched_output_and_artifact_hash_project_functionmatch_and(
        self,
    ) -> None:
        """D09 obligation

        CONTRACT:
        `matched`, `output` and `artifact_hash` project `FunctionMatch`, and are `null` when
        `match is None`. **Over every value `System.resolve` returns** — the domain is named
        because `FunctionResolution` enforces no invariant on a hand-built value (`M13`) —
        `matched is null` iff `passed is false`. A verified miss is therefore `matched: false`,
        never `null`, and a failed verdict is `matched: null`, never `false`. The three states
        stay distinguishable from the payload alone, which is what a shared exit 6 requires.

        AMENDED-BY A4, superseding the text above:
        The biconditional binds `matched` ALONE. `output` and `artifact_hash` are null whenever
        no artifact is projected, which includes the verified miss where `matched` is `false`.
        Measured `(matched is None, output is None, artifact_hash is None)`: hit `(F,F,F)`,
        miss `(F,T,T)`, failed `(T,T,T)`. The domain narrows to values `System.resolve`
        computes through the SHIPPED `verify_function`. The defensive guard at `system.py:3835`
        returns `match=None` whenever `not verification.passed or document is None`, so an
        overridden `verify_function` yielding a passing verification with no document produces
        `(passed: true, matched: null)`. The CLI does not normalize that pair, and normalizing
        it is REJECTED: mapping it to `matched: false` would launder an internal inconsistency
        into an ordinary miss, and the null is exactly the signal that should stay visible.
        """
        # BASELINE c8b82cd: red — the three CLI projections do not exist.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        system, path = _new_system(self)
        artifact_ids = _promote_values(self, system, ({"n": 12},))
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "resolve",
            OPERATION,
            "--input",
        ]

        _, hit_stdout, _ = _invoke([*base, '{"n":12}'])
        _, miss_stdout, _ = _invoke([*base, '{"n":99}'])
        # Null-ness alone cannot tell the two non-null projections apart, so the
        # hit is also pinned value-wise against the library's own `FunctionMatch`.
        hit_match = system.resolve(PARTITION, OPERATION, {"n": 12}).match
        system.suspend_artifact(
            PARTITION,
            artifact_ids[0],
            suspended_by="auditor",
            reason="force a failed verification",
        )
        _, failed_stdout, _ = _invoke([*base, '{"n":12}'])
        payloads = {
            "hit": _payload(hit_stdout),
            "miss": _payload(miss_stdout),
            "failed": _payload(failed_stdout),
        }
        triples = {
            label: (
                body["matched"] is None,
                body["output"] is None,
                body["artifact_hash"] is None,
            )
            for label, body in payloads.items()
        }
        self.assertEqual(
            triples,
            {
                "hit": (False, False, False),
                "miss": (False, True, True),
                "failed": (True, True, True),
            },
        )
        self.assertEqual(
            {
                label: (body["passed"], body["matched"])
                for label, body in payloads.items()
            },
            {
                "hit": (True, True),
                "miss": (True, False),
                "failed": (False, None),
            },
        )
        self.assertEqual(
            len({json.dumps(body, sort_keys=True) for body in payloads.values()}), 3
        )
        self.assertNotEqual(hit_match.output, hit_match.artifact_hash)
        self.assertEqual(
            (payloads["hit"]["output"], payloads["hit"]["artifact_hash"]),
            (hit_match.output, hit_match.artifact_hash),
        )

        inconsistent = FunctionResolution(
            verification=FunctionVerification(True, 0, None, None, ()),
            match=None,
        )
        fake = mock.create_autospec(System, instance=True)
        fake.resolve.return_value = inconsistent
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke([*base, "12"])
        body = _payload(stdout)
        self.assertEqual((status, stderr), (6, ""))
        self.assertEqual((body["passed"], body["matched"]), (True, None))

    def test_d10_status_is_0_iff_matched_is_true_else_6_both_negative_state(
        self,
    ) -> None:
        """D10 obligation

        CONTRACT:
        Status is `0` iff `matched is true`, else `6`. Both negative states use one JSON
        `_Outcome` on **stdout**, following the three shipped stdout precedents and never
        `function export`'s exceptional `_Unverified` stderr channel (`M20`, `M04`).
        """
        # BASELINE c8b82cd: red — no resolve outcome selects status 0 or 6.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        observed: dict[str, tuple[int, bool, bool]] = {}
        for state, expected_status in (("hit", 0), ("miss", 6), ("failed", 6)):
            fake.resolve.return_value = _resolution(state)
            with mock.patch.object(cement_cli, "System", return_value=fake):
                status, stdout, stderr = _invoke(
                    [
                        "--db",
                        str(path),
                        "--partition",
                        PARTITION,
                        "resolve",
                        OPERATION,
                        "--input",
                        "12",
                    ]
                )
            with self.subTest(state=state):
                self.assertEqual(status, expected_status)
                self.assertEqual(stderr, "")
                self.assertTrue(stdout.endswith("\n"))
                self.assertIs(type(_payload(stdout)), dict)
            observed[state] = (status, bool(stdout), bool(stderr))
        self.assertEqual(
            observed,
            {
                "hit": (0, True, False),
                "miss": (6, True, False),
                "failed": (6, True, False),
            },
        )

    def test_d11_verification_document_never_reaches_stdout_d07_s_closed_ke(
        self,
    ) -> None:
        """D11 obligation

        CONTRACT:
        `verification.document` never reaches stdout. D07's closed key set is the structural
        pin; no `asdict` of a verification or resolution is emitted (`M02`, `M03`, `M14`).
        """
        # BASELINE c8b82cd: red — no resolve stdout exists to close over seven keys.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        secret = "DOCUMENT_ONLY_6f2ad6b71e"
        document = FunctionDocument(
            value={"planted": secret},
            text=secret,
            function_hash="d" * 64,
            entries=(),
            input_hashes=(),
        )
        ordinary = _resolution("hit")
        planted = FunctionResolution(
            verification=dataclasses.replace(ordinary.verification, document=document),
            match=ordinary.match,
        )
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.resolve.return_value = planted
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "resolve",
                    OPERATION,
                    "--input",
                    "12",
                ]
            )
        payload = _payload(stdout)
        assert isinstance(payload, dict)
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(
            set(payload),
            {
                "artifact_hash",
                "checks",
                "entries",
                "function_hash",
                "matched",
                "output",
                "passed",
            },
        )
        self.assertNotIn("document", payload)
        self.assertNotIn(secret, json.dumps(payload, sort_keys=True))

        run_tree = ast.parse(textwrap.dedent(inspect.getsource(cement_cli._run)))
        asdict_arguments = [
            ast.unparse(node.args[0])
            for node in ast.walk(run_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "asdict"
            and node.args
        ]
        self.assertIn("check", asdict_arguments)
        self.assertFalse(
            any(
                argument == name or argument.startswith(f"{name}.")
                for argument in asdict_arguments
                for name in ("verification", "resolution")
            ),
            asdict_arguments,
        )

    def test_d12_raised_classes_keep_their_shipped_map_through_main_unchang(
        self,
    ) -> None:
        """D12 obligation

        CONTRACT:
        Raised classes keep their shipped map through `main`, unchanged and untouched by this
        unit: `ValidationError`/`CementError` → 2, `NotFoundError` → 3,
        `ConflictError`/`StateError` → 4, `IntegrityError` → 5 (`M04`). An unregistered
        operation is 3; an empty promoted set is NOT — it is the ordinary verified miss at 6
        (`X14`), and so is a revised operation whose artifacts retired (`X18`).

        AMENDED-BY A13, superseding the text above:
        `unchanged and untouched` names its object and its SLICING CONVENTION: `main`'s
        whole-line AST span (`lineno`..`end_lineno`, trailing newlines stripped), 1,306 bytes,
        sha256 `973b7ee6605f93641a87051626fce53856d219d6763c069b7242da545f406ee1`, equal at
        `4783eed` and at HEAD. Same discipline as P06's three-convention table: a lens on the
        wrong convention reports correct code as stale (`A17`). One planted exception per
        mapped class is driven through `main` beside the span pin, because a span is not a
        behaviour.
        """
        # BASELINE c8b82cd: red — the preserved map has no resolve caller.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))

        current_source = (ROOT / "src/cement_runtime/cli.py").read_text(
            encoding="utf-8"
        )
        base_source = subprocess.run(
            ["git", "show", "4783eed:src/cement_runtime/cli.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

        def function_span(source: str, name: str) -> str:
            tree = ast.parse(source)
            node = next(
                item
                for item in tree.body
                if isinstance(item, ast.FunctionDef) and item.name == name
            )
            return "".join(
                source.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno]
            )

        self.assertEqual(
            function_span(current_source, "main"), function_span(base_source, "main")
        )

        system, path = _new_system(self)
        base = ["--db", str(path), "--partition", PARTITION, "resolve"]
        status, stdout, stderr = _invoke([*base, "missing", "--input", "12"])
        self.assertEqual((status, stdout), (3, ""))
        self.assertEqual(
            _payload(stderr),
            {
                "error": "not_found",
                "message": "operation is not registered in this partition",
            },
        )

        status, stdout, stderr = _invoke([*base, OPERATION, "--input", "12"])
        empty = _payload(stdout)
        self.assertEqual((status, stderr), (6, ""))
        self.assertEqual(
            (empty["entries"], empty["passed"], empty["matched"]),
            (0, True, False),
        )

        _promote_values(self, system, ({"n": 12},))
        system.revise_operation(
            PARTITION,
            OPERATION,
            policy=CompilePolicy(3, 2, 0),
            revised_by="release-manager",
        )
        status, stdout, stderr = _invoke([*base, OPERATION, "--input", "12"])
        revised = _payload(stdout)
        self.assertEqual((status, stderr), (6, ""))
        self.assertEqual(
            (revised["entries"], revised["passed"], revised["matched"]),
            (0, True, False),
        )

        fake = mock.create_autospec(System, instance=True)
        mappings = (
            (ValidationError("validation"), 2, "invalid"),
            (CementError("cement"), 2, "invalid"),
            (NotFoundError("missing"), 3, "not_found"),
            (ConflictError("conflict"), 4, "conflict"),
            (StateError("state"), 4, "conflict"),
            (IntegrityError("integrity"), 5, "integrity"),
        )
        for exception, expected_status, error_key in mappings:
            fake.resolve.side_effect = exception
            with mock.patch.object(cement_cli, "System", return_value=fake):
                status, stdout, stderr = _invoke([*base, OPERATION, "--input", "12"])
            with self.subTest(exception=type(exception).__name__):
                self.assertEqual((status, stdout), (expected_status, ""))
                self.assertEqual(
                    _payload(stderr),
                    {"error": error_key, "message": str(exception)},
                )

    def test_d13_a_db_path_that_does_not_exist_answers_integrityerror_error(
        self,
    ) -> None:
        """D13 obligation

        CONTRACT:
        A `--db` path that does not exist answers `IntegrityError` →
        `{"error":"integrity","message":"ledger file is missing or unreadable"}` on stderr at
        **5**, and **creates no file**. This is a resolve-only pre-construction check placed
        between the `--partition` gate and `System(...)`, forwarding the library's own verdict
        for the same condition (section 2) rather than inventing vocabulary. Stated honestly
        and pinned as written: it is a check, not a read-only construction mode; the residual
        race is that a path deleted between check and construction is still recreated by
        `Store`, which is exactly the shipped behaviour, so the check strictly improves and
        never worsens. `X02`'s full answer — a public existing-only construction mode — is out
        of scope and deferred (section 11). This check is also what makes D04's ordering safe:
        on an absent ledger nothing is constructed, so a malformed `--input` rejected after
        construction can only ever touch a ledger that already existed.

        AMENDED-BY A7, superseding the text above:
        The pre-construction check strictly improves for a path that is STABLY ABSENT. The
        claim `never worsens` is withdrawn as unconditional: in the inverse race a valid ledger
        appearing between the check and construction turns a would-be success into exit 5. The
        mechanism is decomposed rather than raced: `System` builds a valid ledger at a staging
        path, the target tests absent, `os.replace` moves it in, and ordinary construction on
        the now-present target succeeds — so the precheck's exit 5 would have been computed
        from a state construction no longer sees. The window is the same microseconds D13
        already discloses in the forward direction, and no code change is warranted; the
        unconditional sentence is the defect.

        AMENDED-BY A14, superseding the text above:
        The precheck fires ONLY for a path `Store` would create — absent target under an
        existing directory — and is implemented by `_absent_ledger`, not `os.path.exists`.
        `exists` follows the link, so a DANGLING SYMLINK, a MISSING PARENT and an EMBEDDED NUL
        all read as absent and all answered exit 5 `ledger file is missing or unreadable`,
        where the identical paths on a precheck-free leaf answer exit 2 with a precise
        diagnosis (`database path must not be a symbolic link`, `database parent directory does
        not exist`, `database path must not contain NUL`). D12 freezes `ValidationError` → 2,
        so two obligations contradicted each other in shipped code. Every path shape `System`
        already diagnoses stays `System`'s, including a denied ancestor and a non-regular file
        (`Y08`).
        """
        # BASELINE c8b82cd: red — no resolve-only missing-ledger precheck exists.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        target = _temporary_path(self, "absent.db")
        argv = [
            "--db",
            str(target),
            "--partition",
            PARTITION,
            "resolve",
            OPERATION,
            "--input",
            "12",
        ]
        self.assertFalse(target.exists())
        status, stdout, stderr = _invoke(argv)
        self.assertEqual((status, stdout), (5, ""))
        self.assertEqual(
            _payload(stderr),
            {"error": "integrity", "message": "ledger file is missing or unreadable"},
        )
        self.assertFalse(target.exists())

        invalid_partition_argv = argv.copy()
        invalid_partition_argv[3] = "!"
        status, stdout, stderr = _invoke(invalid_partition_argv)
        self.assertEqual((status, stdout), (5, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "ledger file is missing or unreadable",
        )
        self.assertFalse(target.exists())

        with (
            mock.patch.object(
                cement_cli,
                "_input",
                side_effect=AssertionError(
                    "input parsed before missing-ledger verdict"
                ),
            ) as reader,
            mock.patch.object(
                cement_cli,
                "System",
                side_effect=AssertionError("System built for stable absent ledger"),
            ) as constructor,
        ):
            status, stdout, stderr = _invoke([*argv[:-1], "{"])
        self.assertEqual((status, stdout), (5, ""))
        self.assertEqual(
            _payload(stderr)["message"], "ledger file is missing or unreadable"
        )
        self.assertFalse(target.exists())
        reader.assert_not_called()
        constructor.assert_not_called()

        directory_path = target.parent / "directory"
        directory_path.mkdir()
        dangling = target.parent / "dangling.db"
        dangling.symlink_to(target.parent / "missing-target.db")
        invalid_paths = (
            (str(directory_path), "database path must identify a regular file"),
            (str(dangling), "database path must not be a symbolic link"),
            (
                str(target.parent / "nul") + "\0suffix",
                "database path must not contain NUL",
            ),
            (
                str(target.parent / "missing-parent" / "ledger.db"),
                "database parent directory does not exist",
            ),
        )
        for database, message in invalid_paths:
            with self.subTest(database=repr(database)):
                status, stdout, stderr = _invoke(
                    [
                        "--db",
                        database,
                        "--partition",
                        PARTITION,
                        "resolve",
                        OPERATION,
                        "--input",
                        "12",
                    ]
                )
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(_payload(stderr)["message"], message)

        staging = target.parent / "staging.db"
        System(staging)
        raced_target = target.parent / "appeared.db"
        self.assertFalse(raced_target.exists())
        os.replace(staging, raced_target)
        constructed = System(raced_target)
        self.assertEqual(constructed.store.path, raced_target)
        self.assertTrue(raced_target.is_file())

    def test_d14_grammar_is_exactly_one_positional_operation_and_one_requir(
        self,
    ) -> None:
        """D14 obligation

        CONTRACT:
        Grammar is exactly one positional `operation` and one required `--submission`, with
        `allow_abbrev=False`, so `--sub` is `unrecognized arguments` and `proposal sub` is an
        invalid choice (`Y07`).

        AMENDED-BY A1, superseding the text above:
        The guarantee is that no option prefix ever BINDS: every prefix invocation exits 2 with
        empty stdout. The message is `unrecognized arguments: <prefix> <value>` only when the
        required option is separately supplied. A prefix standing IN PLACE of the required
        option answers `the following arguments are required: --input` (or `--submission`),
        because argparse runs its required check inside `parse_known_args`, ahead of the
        leftover check in `parse_args`. D01's "every other prefix is `unrecognized arguments`"
        named one of the two messages as if it were the property.

        AMENDED-BY A17, superseding the text above:
        The prefix rejection is scoped to prefixes of the LEAF'S OWN options. Root options are
        parsed by the root parser before the child is reached, so `--d` and `--part` keep
        resolving under a hardened child — which is what D25 preserves. Measured: `--d x.sqlite
        --part p resolve op --input 1` retains `db=x.sqlite partition=p`. Unscoped, D01 and D25
        demand opposite results for one invocation (`Y24`).
        """
        # BASELINE c8b82cd: red — proposal has no submit child.
        parser = cement_cli._parser()
        submit = _leaf_parser(self, parser, ("proposal", "submit"))
        destinations = {
            action.dest for action in submit._actions if action.dest != "help"
        }
        self.assertEqual(destinations, {"operation", "submission"})
        self.assertFalse(submit.allow_abbrev)
        parsed = parser.parse_args(
            ["proposal", "submit", OPERATION, "--submission", "{}"]
        )
        self.assertEqual((parsed.operation, parsed.submission), (OPERATION, "{}"))

        for argv, required in (
            (["proposal", "submit", "--submission", "{}"], "operation"),
            (["proposal", "submit", OPERATION], "--submission"),
        ):
            with (
                self.subTest(required=required),
                self.assertRaises(cement_cli._UsageError) as caught,
            ):
                parser.parse_args(argv)
            self.assertIn(
                f"the following arguments are required: {required}",
                str(caught.exception),
            )

        prefixes = ["--submission"[:end] for end in range(3, len("--submission"))]
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                status, stdout, stderr = _invoke(
                    [
                        "proposal",
                        "submit",
                        OPERATION,
                        "--submission",
                        "{}",
                        prefix,
                        "{}",
                    ]
                )
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(
                    _payload(stderr)["message"],
                    f"unrecognized arguments: {prefix} {{}}",
                )

        status, stdout, stderr = _invoke(
            ["proposal", "submit", OPERATION, "--sub", "{}"]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "the following arguments are required: --submission",
        )
        status, stdout, stderr = _invoke(
            ["proposal", "sub", OPERATION, "--submission", "{}"]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "argument proposal_command: invalid choice: 'sub' "
            "(choose from 'submit', 'show', 'list', 'review')",
        )

        repeated = parser.parse_args(
            [
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                '{"input":1,"output":1}',
                "--submission",
                '{"input":12,"output":12}',
            ]
        )
        self.assertEqual(repeated.submission, '{"input":12,"output":12}')

    def test_d15_submission_accepts_inline_json_text_or_for_one_aggregate_s(
        self,
    ) -> None:
        """D15 obligation

        CONTRACT:
        `--submission` accepts inline JSON text or `-` for one aggregate stdin frame. There is
        no `@PATH` (section 3.2 D-A) and no per-field flag; `-` reads at most `cap + 1` bytes
        and distinguishes read failure, oversize and invalid UTF-8, mirroring `_input`'s three
        families with submission-specific wording.

        AMENDED-BY A18, superseding the text above:
        The byte wording is scoped to BINARY stdin. A text-only host (`StringIO`, an embedding
        runtime) exposes no `.buffer`; that branch reads at most `cap + 1` CHARACTERS, reports
        `characters` in its oversize message, and has no invalid-UTF-8 family of its own
        because the parser's own encoded-byte check stays authoritative after it (`Y19`).
        """
        # BASELINE c8b82cd: red — no aggregate submission reader exists.
        submit = _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        option_strings = {
            option for action in submit._actions for option in action.option_strings
        }
        self.assertEqual(option_strings, {"-h", "--help", "--submission"})
        cap = cement_cli.SUBMISSION_MAX_BYTES
        path = _temporary_path(self)
        path.touch()
        envelope = '{"input":{"n":12},"output":{"answer":12}}'
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
            "--submission",
        ]
        fake = mock.create_autospec(System, instance=True)
        fake.submit_proposal.return_value = "prop_probe"

        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke([*base, envelope])
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(_payload(stdout), {"proposal_id": "prop_probe"})
        fake.submit_proposal.assert_called_once()

        class RecordingBuffer:
            def __init__(self, raw: bytes) -> None:
                self.raw = raw
                self.calls: list[int] = []

            def read(self, size: int = -1) -> bytes:
                self.calls.append(size)
                if len(self.calls) > 1:
                    raise AssertionError("submission stdin was read twice")
                return self.raw

        class RecordingStdin(io.StringIO):
            def __init__(self, raw: bytes) -> None:
                super().__init__("")
                self.buffer = RecordingBuffer(raw)

        stdin = RecordingStdin(envelope.encode("utf-8"))
        fake.reset_mock()
        fake.submit_proposal.return_value = "prop_stdin"
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke([*base, "-"], stdin=stdin)
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(_payload(stdout), {"proposal_id": "prop_stdin"})
        self.assertEqual(stdin.buffer.calls, [cap + 1])
        fake.submit_proposal.assert_called_once()

        submission_file = path.parent / "submission.json"
        submission_file.write_text(envelope, encoding="utf-8")
        fake.reset_mock()
        with (
            mock.patch.object(cement_cli, "System", return_value=fake),
            mock.patch.object(
                pathlib.Path,
                "open",
                side_effect=AssertionError("@PATH file route reached"),
            ) as path_open,
        ):
            status, stdout, stderr = _invoke([*base, f"@{submission_file}"])
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "invalid JSON: Expecting value: line 1 column 1 (char 0)",
        )
        path_open.assert_not_called()
        fake.submit_proposal.assert_not_called()
        self.assertEqual(submission_file.read_text(encoding="utf-8"), envelope)

        failures = (
            (_FailingBinaryStdin(), "submission stdin could not be read"),
            (_BinaryStdin(b"x" * (cap + 1)), f"submission stdin exceeds {cap} bytes"),
            (_BinaryStdin(b"\xff"), "submission stdin is not valid UTF-8"),
            (
                io.StringIO("x" * (cap + 1)),
                f"submission stdin exceeds {cap} characters",
            ),
            (_FailingTextStdin(), "submission stdin could not be read"),
        )
        for stdin_value, message in failures:
            with self.subTest(message=message):
                fake.reset_mock()
                with mock.patch.object(cement_cli, "System", return_value=fake):
                    status, stdout, stderr = _invoke([*base, "-"], stdin=stdin_value)
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(_payload(stderr)["message"], message)
                fake.submit_proposal.assert_not_called()

        # `cap` itself is admitted on both branches; only `cap + 1` is oversize.
        # At the boundary the frame reaches the parser, whose failure is what
        # surfaces, which is how an accepting reader stays distinguishable from
        # one that rejects its own limit.
        fake.reset_mock()
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke(
                [*base, "-"], stdin=io.StringIO("x" * cap)
            )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "invalid JSON: Expecting value: line 1 column 1 (char 0)",
        )
        fake.submit_proposal.assert_not_called()

        # The binary branch decodes UTF-8, so every non-ASCII frame the library
        # accepts survives transport.
        unicode_envelope = '{"input":{"n":12},"output":{"answer":"é"}}'
        fake.reset_mock()
        fake.submit_proposal.return_value = "prop_unicode"
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke(
                [*base, "-"], stdin=_BinaryStdin(unicode_envelope.encode("utf-8"))
            )
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(_payload(stdout), {"proposal_id": "prop_unicode"})
        fake.submit_proposal.assert_called_once()

        for option in ("--input", "--output", "--provenance"):
            with self.subTest(option=option):
                status, stdout, stderr = _invoke([*base, envelope, option, "12"])
                self.assertEqual((status, stdout), (2, ""))
                self.assertIn(
                    f"unrecognized arguments: {option} 12", _payload(stderr)["message"]
                )

    def test_d16_the_aggregate_cap_is_2_default_max_bytes_provenance_max_by(
        self,
    ) -> None:
        """D16 obligation

        CONTRACT:
        The aggregate cap is `2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + framing` =
        **2,162,722 bytes**, where `PROVENANCE_MAX_BYTES` is newly exported from `system.py`
        and used at its three existing literal sites. No limit is copied. The cap is a
        TRANSPORT bound that must admit every submission the library accepts; it replaces no
        field validation (`Z13`, `X12`).

        AMENDED-BY A9, superseding the text above:
        The framing term is **34 bytes**, DERIVED and never written down: two braces, one comma
        between each adjacent pair, and `"<key>":` per key, over `_SUBMISSION_KEYS`. It equals
        `len('{"input":,"output":,"provenance":}')`. D16 gave the total `2,162,722` while
        naming no byte template, so a copied total satisfied the numeric pin with nothing
        deriving it (`A04`).

        AMENDED-BY A20, superseding the text above:
        `must admit every submission the library accepts` is WITHDRAWN as unconditional and
        replaced by the value-level guarantee: for every field triple the library accepts, its
        COMPACT CANONICAL envelope fits under the cap. Insignificant whitespace and escapes are
        unbounded, so no transport bound can admit every serialization — measured, a
        2,162,723-byte whitespace-padded envelope semantically equal to `{input:0, output:0,
        provenance:{}}` is rejected by the cap while `submit_proposal` accepts the same values
        directly (`Y25`).
        """
        # BASELINE c8b82cd: red — the aggregate cap and exported provenance constant are absent.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        cap = cement_cli.SUBMISSION_MAX_BYTES
        provenance_max = system_module.PROVENANCE_MAX_BYTES
        framing_bytes = b'{"input":,"output":,"provenance":}'
        framing = len(framing_bytes)
        self.assertEqual(framing, 34)
        self.assertEqual(cement_cli._SUBMISSION_FRAMING, framing)
        self.assertEqual(
            cap,
            2 * DEFAULT_MAX_BYTES + provenance_max + framing,
        )
        self.assertEqual(cap, 2_162_722)

        cli_tree = ast.parse(
            (ROOT / "src/cement_runtime/cli.py").read_text(encoding="utf-8")
        )
        system_tree = ast.parse(
            (ROOT / "src/cement_runtime/system.py").read_text(encoding="utf-8")
        )
        # M3.5b: the last bare copy lived in `_source`, deleted with the helper,
        # so "exactly one, and it is the source-command bound" strengthens to
        # "no bare copy of the number survives in cli.py".
        self.assertEqual(
            sum(
                isinstance(node, ast.Constant) and node.value == 65_536
                for node in ast.walk(cli_tree)
            ),
            0,
        )
        self.assertEqual(
            sum(
                isinstance(node, ast.Constant) and node.value == 65_536
                for node in ast.walk(system_tree)
            ),
            1,
        )
        self.assertEqual(
            sum(
                isinstance(node, ast.Name) and node.id == "PROVENANCE_MAX_BYTES"
                for node in ast.walk(system_tree)
            ),
            4,
        )
        cap_assignment = next(
            node
            for node in cli_tree.body
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "SUBMISSION_MAX_BYTES"
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "SUBMISSION_MAX_BYTES"
            )
        )
        assert cap_assignment.value is not None
        cap_names = {
            node.id
            for node in ast.walk(cap_assignment.value)
            if isinstance(node, ast.Name)
        }
        self.assertEqual(
            cap_names,
            {"DEFAULT_MAX_BYTES", "PROVENANCE_MAX_BYTES", "_SUBMISSION_FRAMING"},
        )
        self.assertFalse(
            any(
                isinstance(node, ast.Constant) and node.value == 65_536
                for node in ast.walk(cap_assignment.value)
            )
        )
        imports = {
            alias.name
            for node in cli_tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "system"
            for alias in node.names
        }
        self.assertIn("PROVENANCE_MAX_BYTES", imports)

        system, path = _new_system(self)
        del system
        maximal_field = '"' + "x" * (DEFAULT_MAX_BYTES - 2) + '"'
        maximal_provenance = '{"k":"' + "x" * (provenance_max - 8) + '"}'
        self.assertEqual(len(maximal_field.encode("utf-8")), DEFAULT_MAX_BYTES)
        self.assertEqual(len(maximal_provenance.encode("utf-8")), provenance_max)
        at_cap = (
            '{"input":'
            + maximal_field
            + ',"output":'
            + maximal_field
            + ',"provenance":'
            + maximal_provenance
            + "}"
        )
        self.assertEqual(len(at_cap.encode("utf-8")), cap)
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
            "--submission",
            "-",
        ]
        status, stdout, stderr = _invoke(
            base, stdin=_BinaryStdin(at_cap.encode("utf-8"))
        )
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(set(_payload(stdout)), {"proposal_id"})

        over = at_cap[:-2] + 'x"}'
        self.assertEqual(len(over.encode("utf-8")), cap + 1)
        counts = _table_counts(path)
        status, stdout, stderr = _invoke(base, stdin=_BinaryStdin(over.encode("utf-8")))
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"], f"submission stdin exceeds {cap} bytes"
        )
        self.assertEqual(_table_counts(path), counts)
        status, stdout, stderr = _invoke(base, stdin=io.StringIO(over))
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            f"submission stdin exceeds {cap} characters",
        )
        self.assertEqual(_table_counts(path), counts)
        status, stdout, stderr = _invoke([*base[:-1], over])
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"], f"JSON source exceeds {cap} bytes"
        )
        self.assertEqual(_table_counts(path), counts)

    def test_d17_validation_order_is_strict_parse_json_under_the_aggregate(
        self,
    ) -> None:
        """D17 obligation

        CONTRACT:
        Validation order is: strict `parse_json` under the aggregate byte, depth and item
        maxima (`X08` — depth `DEFAULT_MAX_DEPTH + 1`, items `3 * DEFAULT_MAX_ITEMS + 3`) →
        top-level object type → unknown keys → missing required keys → the library call.
        Duplicate members therefore fail inside the parser, before any exact-key check can
        collapse them (`X09`, `Y05`).
        """
        # BASELINE c8b82cd: red — no strict envelope pipeline exists.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.submit_proposal.return_value = "prop_probe"
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
            "--submission",
        ]
        valid = '{"input":12,"output":34}'
        with (
            mock.patch.object(cement_cli, "System", return_value=fake),
            mock.patch.object(
                cement_cli, "parse_json", wraps=cement_cli.parse_json
            ) as parser_spy,
        ):
            status, _, stderr = _invoke([*base, valid])
        self.assertEqual((status, stderr), (0, ""))
        parser_spy.assert_called_once()
        self.assertEqual(
            parser_spy.call_args.kwargs,
            {
                "max_bytes": cement_cli.SUBMISSION_MAX_BYTES,
                "max_depth": DEFAULT_MAX_DEPTH + 1,
                "max_items": 3 * DEFAULT_MAX_ITEMS + 3,
            },
        )

        rejected = (
            ('{"input":1,"input":2,"output":3}', "duplicate JSON object key: 'input'"),
            ("null", "submission must be a JSON object"),
            ("[]", "submission must be a JSON object"),
            ("0", "submission must be a JSON object"),
            ('"text"', "submission must be a JSON object"),
            ('{"z":0,"a":0}', "submission has unknown keys: a, z"),
        )
        for source, message in rejected:
            with self.subTest(source=source):
                fake.reset_mock()
                with mock.patch.object(cement_cli, "System", return_value=fake):
                    status, stdout, stderr = _invoke([*base, source])
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(_payload(stderr)["message"], message)
                if source == '{"z":0,"a":0}':
                    self.assertNotIn("input", _payload(stderr)["message"])
                    self.assertNotIn("output", _payload(stderr)["message"])
                fake.submit_proposal.assert_not_called()

        at_depth = "0"
        for _ in range(DEFAULT_MAX_DEPTH):
            at_depth = f"[{at_depth}]"
        at_depth = '{"input":' + at_depth + ',"output":0}'
        over_depth = at_depth.replace('"input":', '"input":[', 1).replace(
            ',"output":', '],"output":', 1
        )
        fake.reset_mock()
        fake.submit_proposal.return_value = "prop_depth"
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, _, stderr = _invoke([*base, at_depth])
        self.assertEqual((status, stderr), (0, ""))
        fake.submit_proposal.assert_called_once()
        fake.reset_mock()
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke([*base, over_depth])
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            f"JSON exceeds maximum depth {DEFAULT_MAX_DEPTH + 1}",
        )
        fake.submit_proposal.assert_not_called()

        hundred_thousand = "[" + ",".join("0" for _ in range(DEFAULT_MAX_ITEMS)) + "]"
        at_items = (
            '{"input":'
            + hundred_thousand
            + ',"output":'
            + hundred_thousand
            + ',"provenance":'
            + hundred_thousand
            + "}"
        )
        over_items = at_items.replace('"input":[', '"input":[0,', 1)
        fake.reset_mock()
        fake.submit_proposal.return_value = "prop_items"
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, _, stderr = _invoke([*base, at_items])
        self.assertEqual((status, stderr), (0, ""))
        fake.submit_proposal.assert_called_once()
        fake.reset_mock()
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke([*base, over_items])
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"], "JSON exceeds maximum container item count"
        )
        fake.submit_proposal.assert_not_called()

    def test_d18_input_and_output_are_required_provenance_is_optional_and_d(
        self,
    ) -> None:
        """D18 obligation

        CONTRACT:
        `input` and `output` are required; `provenance` is optional and defaults to `{}`, which
        is a durable empty mapping (`Z06`). Unknown keys and missing keys each name every
        offending key, sorted. Every one of these is exit 2 on stderr before any transaction
        opens (`X11`).

        AMENDED-BY A5, superseding the text above:
        `before any transaction opens` is TRUE as written at the `Store.transaction` seam and
        is retained. Added, because D18 omitted it: envelope validation runs in the dispatch
        branch, AFTER `System(...)`, so a writing leaf creates its ledger and initialises the
        schema before rejecting a malformed envelope. Measured on all four envelope failures:
        `System.__init__` 1, `sqlite3.connect` ≥ 1, `Store.transaction` 0,
        `System.submit_proposal` 0, ledger present afterwards at ~208 KiB. Giving `proposal
        submit` a D13-style precheck is REJECTED: creating the ledger is a legitimate first use
        of a writing leaf. The residual — an invalid argument value creating the ledger on ANY
        writing leaf — is CLI-wide, pre-existing, and deferred (section 12).
        """
        # BASELINE c8b82cd: red — no envelope validation or durable default exists.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        invalid = (
            ("[]", "submission must be a JSON object"),
            ('{"input":1,"output":2,"z":0,"a":0}', "submission has unknown keys: a, z"),
            ('{"provenance":{}}', "submission is missing required keys: input, output"),
            ('{"input":1,"input":2,"output":3}', "duplicate JSON object key: 'input'"),
        )
        for index, (source, message) in enumerate(invalid):
            path = _temporary_path(self, f"invalid-{index}.db")
            transaction_calls: list[bool] = []
            original_connect = sqlite3.connect

            with (
                mock.patch.object(cement_cli, "System", wraps=System) as constructor,
                mock.patch.object(
                    store_module.sqlite3,
                    "connect",
                    wraps=original_connect,
                ) as connections,
                mock.patch.object(
                    Store,
                    "transaction",
                    _recording_transaction(transaction_calls),
                ),
                mock.patch.object(
                    System,
                    "submit_proposal",
                    side_effect=AssertionError("invalid envelope reached the library"),
                ) as submit,
            ):
                status, stdout, stderr = _invoke(
                    [
                        "--db",
                        str(path),
                        "--partition",
                        PARTITION,
                        "proposal",
                        "submit",
                        OPERATION,
                        "--submission",
                        source,
                    ]
                )
            with self.subTest(source=source):
                self.assertEqual((status, stdout), (2, ""))
                self.assertEqual(_payload(stderr)["message"], message)
                constructor.assert_called_once()
                self.assertEqual(constructor.call_args.args, (str(path),))
                self.assertIsNone(constructor.call_args.kwargs.get("candidate_source"))
                self.assertGreaterEqual(connections.call_count, 1)
                self.assertEqual(transaction_calls, [])
                submit.assert_not_called()
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)

        path = _temporary_path(self, "identity.db")
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.submit_proposal.side_effect = ("prop_one", "prop_two")
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
            "--submission",
        ]
        with mock.patch.object(cement_cli, "System", return_value=fake):
            first = _invoke([*base, '{"input":12,"output":34}'])
            second = _invoke([*base, '{"input":56,"output":78}'])
        self.assertEqual((first[0], second[0]), (0, 0))
        candidates = [
            call.kwargs["candidate"] for call in fake.submit_proposal.call_args_list
        ]
        self.assertEqual([candidate.provenance for candidate in candidates], [{}, {}])
        self.assertIsNot(candidates[0].provenance, candidates[1].provenance)

        _, ledger = _new_system(self)
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                '{"input":12,"output":34}',
            ]
        )
        proposal_id = _payload(stdout)["proposal_id"]
        self.assertEqual((status, stderr), (0, ""))
        with closing(sqlite3.connect(ledger)) as connection:
            stored = connection.execute(
                "SELECT provenance_json FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
        self.assertIsNotNone(stored)
        self.assertEqual(stored[0], "{}")

    def test_d19_dispatch_builds_candidate_output_provenance_from_the_envel(
        self,
    ) -> None:
        """D19 obligation

        CONTRACT:
        Dispatch builds `Candidate(output=..., provenance=...)` from the envelope and passes
        the envelope's `input` as the library's third positional (`M10`, `M12`, `X21`).
        Provenance shape stays library-graded: a non-mapping provenance is `candidate
        provenance must be a mapping` at exit 2 (`Z07`), and no CLI-only coercion is added.
        """
        # BASELINE c8b82cd: red — no envelope-to-Candidate wiring reaches submit_proposal.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.submit_proposal.return_value = "prop_wired"
        envelope = json.dumps(
            {
                "input": {"input": 12},
                "output": {"output": 34},
                "provenance": {"source": "p56"},
            },
            separators=(",", ":"),
        )
        argv = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
            "--submission",
            envelope,
        ]
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke(argv)
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(_payload(stdout), {"proposal_id": "prop_wired"})
        fake.submit_proposal.assert_called_once()
        call = fake.submit_proposal.call_args
        self.assertEqual(call.args, (PARTITION, OPERATION, {"input": 12}))
        self.assertEqual(set(call.kwargs), {"candidate"})
        candidate = call.kwargs["candidate"]
        self.assertIs(type(candidate), Candidate)
        self.assertEqual(candidate.output, {"output": 34})
        self.assertEqual(candidate.provenance, {"source": "p56"})

        fake.reset_mock()
        fake.submit_proposal.return_value = "prop_ungraded"
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, _, stderr = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "proposal",
                    "submit",
                    OPERATION,
                    "--submission",
                    '{"input":12,"output":34,"provenance":[56]}',
                ]
            )
        self.assertEqual((status, stderr), (0, ""))
        forwarded = fake.submit_proposal.call_args.kwargs["candidate"]
        self.assertEqual(forwarded.provenance, [56])

        _, ledger = _new_system(self)
        before = _table_counts(ledger)
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                '{"input":12,"output":34,"provenance":[56]}',
            ]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(
            _payload(stderr)["message"],
            "candidate provenance must be a mapping",
        )
        self.assertEqual(_table_counts(ledger), before)
        self.assertNotIn(
            "candidate provenance must be a mapping",
            (ROOT / "src/cement_runtime/cli.py").read_text(encoding="utf-8"),
        )

    def test_d20_success_emits_exactly_proposal_id_id_at_status_0_one_key_t(
        self,
    ) -> None:
        """D20 obligation

        CONTRACT:
        Success emits exactly `{"proposal_id": "<id>"}` at status 0 — one key. The bare string
        `submit_proposal` returns is NOT emitted directly, because `_emit` renders it as a bare
        JSON string with no key to bind (section 2). The flags patch's `"status":
        "review_required"` is REJECTED: it is a constant, not a measurement — every successful
        submission is pending by construction — so it advertises a variability the API does not
        have.

        AMENDED-BY A10, superseding the text above:
        D20's premise `every successful submission is pending by construction` is FALSE and is
        replaced by **every proposal is INSERTED pending**. Measured: a reviewer transitioning
        the committed row inside the post-commit, pre-return window yields `returned_id=True
        status_at_return=rejected` (`A07`). The `"status": "review_required"` key stays
        REJECTED, on the corrected ground — the constant can already be stale when it is
        emitted, not that status cannot vary.
        """
        # BASELINE c8b82cd: red — the submit acknowledgement is absent.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        path = _temporary_path(self)
        path.touch()
        fake = mock.create_autospec(System, instance=True)
        fake.submit_proposal.return_value = "prop_probe"
        with mock.patch.object(cement_cli, "System", return_value=fake):
            status, stdout, stderr = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "proposal",
                    "submit",
                    OPERATION,
                    "--submission",
                    '{"input":12,"output":34}',
                ]
            )
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(_payload(stdout), {"proposal_id": "prop_probe"})
        self.assertEqual(
            stdout,
            '{\n  "proposal_id": "prop_probe"\n}\n',
        )
        self.assertEqual(len(_payload(stdout)), 1)
        self.assertNotIn("status", _payload(stdout))
        fake.submit_proposal.assert_called_once()

        bare = io.StringIO()
        cement_cli._emit("prop_probe", stream=bare)
        self.assertEqual(bare.getvalue(), '"prop_probe"\n')
        self.assertNotEqual(stdout, bare.getvalue())

    def test_d21_no_candidate_byte_is_echoed_the_acknowledgement_carries_no(
        self,
    ) -> None:
        """D21 obligation

        CONTRACT:
        No candidate byte is echoed. The acknowledgement carries no request identity, and the
        one `proposal.created` event's payload stays exactly `{}` (`Z18`, `M25`).

        AMENDED-BY A15, superseding the text above:
        `No candidate byte is echoed` is scoped to the **status-0 acknowledgement**. Read
        across the whole leaf it is false: strict parsing quotes the offending token, measured
        as `cement-json-v1 rejects decimal/exponent number '12345.678901'` at exit 2. No
        error-redaction boundary is added — the echo is the diagnosis (`Y10`).
        """
        # BASELINE c8b82cd: red — no successful submission acknowledgement exists.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        _, path = _new_system(self)
        secrets = (
            "INPUT_SECRET_12",
            "OUTPUT_SECRET_34",
            "PROVENANCE_SECRET_56",
        )
        envelope = json.dumps(
            {
                "input": secrets[0],
                "output": secrets[1],
                "provenance": {"model": secrets[2]},
            },
            separators=(",", ":"),
        )
        before = _table_counts(path)
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(path),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                envelope,
            ]
        )
        body = _payload(stdout)
        proposal_id = body["proposal_id"]
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(set(body), {"proposal_id"})
        self.assertFalse(any(secret in stdout for secret in secrets))

        after = _table_counts(path)
        self.assertEqual(after["events"] - before["events"], 1)
        with closing(sqlite3.connect(path)) as connection:
            proposal = connection.execute(
                "SELECT request_id FROM proposals WHERE id = ? AND partition = ?",
                (proposal_id, PARTITION),
            ).fetchone()
            events = connection.execute(
                "SELECT kind, subject_type, subject_id, payload_json FROM events "
                "WHERE partition = ? AND subject_id = ? ORDER BY sequence",
                (PARTITION, proposal_id),
            ).fetchall()
        self.assertIsNotNone(proposal)
        request_id = str(proposal[0])
        self.assertNotIn(request_id, stdout)
        self.assertEqual(
            events,
            [("proposal.created", "proposal", proposal_id, "{}")],
        )
        event_text = "".join(str(cell) for row in events for cell in row)
        self.assertFalse(any(secret in event_text for secret in secrets))
        self.assertNotIn(request_id, event_text)

        decimal = "12345.678901"
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(path),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                f'{{"input":12,"output":{decimal}}}',
            ]
        )
        self.assertEqual((status, stdout), (2, ""))
        self.assertIn(decimal, _payload(stderr)["message"])

    def test_d22_exit_classes_parser_envelope_and_field_validation_failures(
        self,
    ) -> None:
        """D22 obligation

        CONTRACT:
        Exit classes: parser, envelope and field-validation failures → 2; unregistered
        operation → 3 with zero rows written (`Z14`); `ConflictError`/`StateError` → 4;
        `IntegrityError` → 5.
        """
        # BASELINE c8b82cd: red — submit has no exit-class surface.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        _, path = _new_system(self)
        base = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
        ]
        validation_cases = (
            ([*base], "parser"),
            ([*base, "--submission", "[]"], "envelope"),
            (
                [*base, "--submission", '{"input":12,"output":34,"provenance":[]}'],
                "field",
            ),
        )
        for argv, label in validation_cases:
            with self.subTest(label=label):
                status, stdout, stderr = _invoke(argv)
                self.assertEqual((status, stdout), (2, ""))
                payload = _payload(stderr)
                self.assertEqual(payload["error"], "invalid")
                self.assertEqual(
                    stderr,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
                    + "\n",
                )

        before = _table_counts(path)
        self.assertEqual(len(before), 13)
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(path),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                "missing",
                "--submission",
                '{"input":12,"output":34}',
            ]
        )
        self.assertEqual((status, stdout), (3, ""))
        self.assertEqual(
            _payload(stderr),
            {
                "error": "not_found",
                "message": "operation is not registered in this partition",
            },
        )
        self.assertEqual(_table_counts(path), before)

        fake = mock.create_autospec(System, instance=True)
        failures = (
            (ConflictError("conflict probe"), 4, "conflict"),
            (StateError("state probe"), 4, "conflict"),
            (IntegrityError("integrity probe"), 5, "integrity"),
        )
        for exception, expected_status, error_key in failures:
            fake.submit_proposal.side_effect = exception
            with mock.patch.object(cement_cli, "System", return_value=fake):
                status, stdout, stderr = _invoke(
                    [*base, "--submission", '{"input":12,"output":34}']
                )
            payload = {"error": error_key, "message": str(exception)}
            with self.subTest(exception=type(exception).__name__):
                self.assertEqual((status, stdout), (expected_status, ""))
                self.assertEqual(_payload(stderr), payload)
                self.assertEqual(
                    stderr,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
                    + "\n",
                )

    def test_d23_there_is_no_idempotency_two_byte_identical_submissions_ret(
        self,
    ) -> None:
        """D23 obligation

        CONTRACT:
        There is no idempotency. Two byte-identical submissions return two distinct ids and add
        two requests, two proposals and two events (`X13`). No help text, message or doc
        sentence may advise retry; the recovery route for the M3.3 commit window is
        pending-proposal ENUMERATION (`X24`).

        AMENDED-BY A11, superseding the text above:
        The no-retry-advice predicate is scoped to a SUBMISSION-OWNED corpus: the `proposal
        submit` help and docstrings, and the submission sections of README and the normative
        docs. A repository-wide `retry` grep is invalid in both directions — legacy `handle`
        legitimately advises retry at `README.md:277`, and an absence grep passes when the
        recovery prose is deleted (`A08`). The predicate is positive: the corpus must state
        pending-proposal ENUMERATION as the recovery route, and must contain no
        `retry|resubmit|run again|repeat` advice.

        M3.5b D22 re-scopes A11's positive control. The CLI `handle` leaf is gone, so README's
        retry advice moved onto the surviving library route and now reads `call `System.handle`
        again with `retry_failed=True``. The control asserts that NEW spelling. Its role is
        unchanged: it proves the README still carries retry advice OUTSIDE the submission
        corpus, which is what keeps the scoped absence assertion above non-vacuous. Deleting
        the control instead of moving it would leave that assertion passing on a README with no
        retry prose at all, which is exactly the A08 failure A11 was written to prevent.
        """
        # BASELINE c8b82cd: red — no CLI submission can demonstrate non-idempotency.
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        _, path = _new_system(self)
        envelope = '{"input":{"n":12},"output":{"answer":34}}'
        argv = [
            "--db",
            str(path),
            "--partition",
            PARTITION,
            "proposal",
            "submit",
            OPERATION,
            "--submission",
            envelope,
        ]
        before = _table_counts(path)
        first = _invoke(argv)
        second = _invoke(argv)
        self.assertEqual((first[0], second[0]), (0, 0))
        first_id = _payload(first[1])["proposal_id"]
        second_id = _payload(second[1])["proposal_id"]
        self.assertNotEqual(first_id, second_id)
        after = _table_counts(path)
        delta = {table: after[table] - before[table] for table in before}
        self.assertEqual(
            {table: count for table, count in delta.items() if count},
            {"events": 2, "proposals": 2, "requests": 2},
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        documents = "\n\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in (
                "README.md",
                "docs/architecture.md",
                "docs/threat-model.md",
            )
        )
        submit_help = _leaf_parser(
            self,
            cement_cli._parser(),
            ("proposal", "submit"),
        ).format_help()
        self.assertIn("Cement gives no idempotency here", readme)
        self.assertIn("Do not retry a failed submission", readme)
        self.assertRegex(readme, r"proposal list[^\n]*--status pending")
        self.assertNotRegex(
            submit_help.lower(), r"\b(?:retry|resubmit|run again|repeat)\b"
        )

        units: list[str] = []
        for paragraph in re.split(r"\n\s*\n", documents):
            units.extend(
                re.split(r"\n(?=\s*[-*|] )", paragraph)
                if re.search(r"^\s*[-*|] ", paragraph, re.MULTILINE)
                else [paragraph]
            )
        submission_paragraphs = "\n".join(
            unit
            for unit in units
            if re.search(r"\bsubmission\b|proposal submit", unit, re.IGNORECASE)
        ).lower()
        scrubbed = re.sub(
            r"\b(?:do not|never|must not)\s+(?:retry|resubmit|run again|repeat)\b",
            "",
            submission_paragraphs,
        )
        self.assertNotRegex(
            scrubbed,
            r"\b(?:should|must|can|may|please)\s+(?:retry|resubmit|run again|repeat)\b"
            r"|(?:^|[.!?:;]\s+)(?:retry|resubmit|run again|repeat)\b",
        )
        self.assertIn("call `System.handle` again with `retry_failed=True`", readme)

    def test_d24_zero_source_calls_zero_system_propose_calls_and_zero_sourc(
        self,
    ) -> None:
        """D24 obligation

        CONTRACT:
        Zero `_source` calls, zero `System.propose` calls, and zero source calls even when a
        configured source would raise (`Y01` envelope, `X22`). This is the unit's headline
        isolation predicate: the core CLI gains a write channel and no candidate-source reach.
        """
        # BASELINE c8b82cd: red — neither isolated CLI leaf exists.
        parser = cement_cli._parser()
        resolve_parser = _leaf_parser(self, parser, ("resolve",))
        submit_parser = _leaf_parser(self, parser, ("proposal", "submit"))
        source_destinations = {"source_command", "source_id", "source_timeout"}
        for node in (resolve_parser, submit_parser):
            destinations = {action.dest for action in node._actions}
            self.assertEqual(destinations & source_destinations, set())

        source = _ExplodingSource()
        system, path = _new_system(self, source=source)
        before = _table_counts(path)
        # M3.5b D19: `_source` is deleted, so the spy raises rather than
        # verdicting. Absence replaces its zero count.
        self.assertFalse(hasattr(cement_cli, "_source"))
        with (
            mock.patch.object(cement_cli, "System", return_value=system) as constructor,
            mock.patch.object(
                system,
                "propose",
                side_effect=AssertionError("System.propose reached"),
            ) as propose,
            mock.patch.object(system, "resolve", wraps=system.resolve) as resolve,
            mock.patch.object(
                system,
                "submit_proposal",
                wraps=system.submit_proposal,
            ) as submit,
        ):
            resolve_result = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "resolve",
                    OPERATION,
                    "--input",
                    "12",
                ]
            )
            submit_result = _invoke(
                [
                    "--db",
                    str(path),
                    "--partition",
                    PARTITION,
                    "proposal",
                    "submit",
                    OPERATION,
                    "--submission",
                    '{"input":12,"output":34}',
                ]
            )
            self.assertEqual((resolve_result[0], submit_result[0]), (6, 0))
            self.assertEqual(resolve.call_count, 1)
            self.assertEqual(submit.call_count, 1)
            propose.assert_not_called()
            self.assertIs(system.candidate_source, source)
            leaves = _table_counts(path)

            # POSITIVE CONTROL. `handle` was the CLI witness that a configured
            # source IS reachable, which is what stops the two zeros above from
            # being vacuous. M3.5b removes that CLI route and keeps the LIBRARY
            # method, so the control moves onto `System.handle` itself. A control
            # deleted rather than relocated turns an isolation pin into a
            # tautology.
            handled = system.handle(PARTITION, OPERATION, 12)
        self.assertEqual(handled.status, "fallback_failed")
        self.assertEqual(handled.code, "candidate_source_error")
        self.assertEqual(constructor.call_count, 2)

        after = _table_counts(path)
        leaf_delta = {table: leaves[table] - before[table] for table in before}
        handle_delta = {table: after[table] - leaves[table] for table in before}
        self.assertEqual(
            {table: count for table, count in leaf_delta.items() if count},
            {"events": 1, "proposals": 1, "requests": 1},
        )
        self.assertEqual(
            {table: count for table, count in handle_delta.items() if count},
            {"events": 1, "requests": 1},
        )

    def test_d25_the_parser_census_moves_28_30_leaves_and_35_37_nodes_deriv(
        self,
    ) -> None:
        """D25 obligation

        CONTRACT:
        The parser census moves **28 → 30 leaves and 35 → 37 nodes**, derived inside the test
        from `_parser()` and never transcribed (`M17`, section 2). All 28 existing leaf paths
        keep their names. Option abbreviation elsewhere is unchanged, which the same
        census-derived test asserts by leaving root and nested behaviour as section 2 measured
        it.

        AMENDED-BY A23, superseding the text above:
        `Option abbreviation elsewhere is unchanged` names its instrument, because the census
        cannot carry it. Disabling `allow_abbrev` on an existing leaf leaves every action
        attribute, the 30/37 census and all three section-2 abbreviation probes unchanged. Gate
        4's `parser_shape` digest now emits one `<node>` line per parser node carrying
        `allow_abbrev`: 163 lines = 126 actions + 37 nodes, digest `8b58b465c08aa693`, and the
        control mutation on `proposal review` moves it to `515b30796c61d189` while the census
        holds at 30/37 (`A10`, `A16`).
        """
        # BASELINE c8b82cd: red — the two named leaves are absent.
        current_parser = cement_cli._parser()
        _leaf_parser(self, current_parser, ("resolve",))
        _leaf_parser(self, current_parser, ("proposal", "submit"))

        base_source = subprocess.run(
            ["git", "show", "c8b82cd:src/cement_runtime/cli.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        module_name = "cement_runtime._m3u5a_base_cli"
        base_module = types.ModuleType(module_name)
        base_module.__file__ = "<git:c8b82cd:src/cement_runtime/cli.py>"
        base_module.__package__ = "cement_runtime"
        sys.modules[module_name] = base_module
        self.addCleanup(sys.modules.pop, module_name, None)
        exec(  # noqa: S102 - committed Git source is the oracle.
            compile(base_source, base_module.__file__, "exec"),
            base_module.__dict__,
        )
        base_parser = base_module._parser()

        base_leaves, base_nodes = _parser_census(base_parser)
        current_leaves, current_nodes = _parser_census(current_parser)
        # M3.5b D02/D12: the counts return to the base's own 28/35 over the
        # INVERSE set, so both set differences carry the claim and the equal
        # cardinality is asserted as a CONSEQUENCE of the two named swaps.
        self.assertEqual(base_leaves - current_leaves, {"handle", "request"})
        self.assertEqual(current_leaves - base_leaves, {"proposal submit", "resolve"})
        self.assertEqual(len(current_leaves), len(base_leaves))
        self.assertEqual(current_nodes, base_nodes)

        def abbreviation_map(parser: argparse.ArgumentParser) -> dict[str, bool]:
            values: dict[str, bool] = {}

            def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
                values[" ".join(path)] = node.allow_abbrev
                for action in node._actions:
                    if isinstance(action, argparse._SubParsersAction):
                        for name, child in action.choices.items():
                            visit(child, (*path, name))

            visit(parser, ())
            return values

        base_abbreviation = abbreviation_map(base_parser)
        current_abbreviation = abbreviation_map(current_parser)
        # M3.5b: `handle` and `request` leave the base map, so the preservation
        # claim runs over the SHARED paths and the two removals are asserted
        # separately. Comparing over the base's own key set would raise a
        # KeyError and report a removal as an instrument error.
        shared = set(base_abbreviation) & set(current_abbreviation)
        self.assertEqual(
            {path: current_abbreviation[path] for path in shared},
            {path: base_abbreviation[path] for path in shared},
        )
        self.assertEqual(set(base_abbreviation) - shared, {"handle", "request"})
        self.assertEqual(
            set(current_abbreviation) - shared, {"resolve", "proposal submit"}
        )
        self.assertFalse(current_abbreviation["resolve"])
        self.assertFalse(current_abbreviation["proposal submit"])

        legacy_argv = (
            ["--part", PARTITION, "--db", "ledger.db", "events"],
            ["function", "eval", "--bun", "bundle.json", "--in", "12"],
        )
        for argv in legacy_argv:
            with self.subTest(argv=argv):
                base_args = base_parser.parse_args(argv)
                current_args = current_parser.parse_args(argv)
                self.assertEqual(
                    (
                        getattr(current_args, "partition", None),
                        getattr(current_args, "bundle", None),
                        getattr(current_args, "input", None),
                    ),
                    (
                        getattr(base_args, "partition", None),
                        getattr(base_args, "bundle", None),
                        getattr(base_args, "input", None),
                    ),
                )
        parsed_root = current_parser.parse_args(legacy_argv[0])
        parsed_nested = current_parser.parse_args(legacy_argv[1])
        self.assertEqual(parsed_root.partition, PARTITION)
        self.assertEqual(
            (parsed_nested.bundle, parsed_nested.input), ("bundle.json", "12")
        )

    def test_d26_preserved_and_asserted_independently_store_py_byte_identic(
        self,
    ) -> None:
        """D26 obligation

        CONTRACT:
        Preserved and asserted independently: `store.py` byte-identical at `SCHEMA_VERSION` 2;
        a successful direct submission's three-row footprint (one request, one proposal, one
        event) (`X23`); `CommandCandidateSource` still imported (`M23`); cross-leaf option
        isolation in both directions for both new leaves, including that
        `--expected-function-hash` stays off `proposal submit` and `--submission` stays off
        every other leaf (`X15`, `X25`).

        AMENDED-BY A12, superseding the text above:
        `store.py` byte-identity names its ORACLE: git object
        `4783eed:src/cement_runtime/store.py`, blob `b870dacbaf2718b7cba3567b59d69a994ca4ca42`,
        27,951 bytes, sha256
        `2b2650144d4b384af4d8bfe67e1f9de0e186b609f3bb2632e2f81b53536770f7`. A test-local digest
        or a self-comparison pins nothing, because it divorces the claim from its referent
        (`A11`).
        """
        # BASELINE c8b82cd: red — preservation holds, but both new option owners are absent.
        parser = cement_cli._parser()
        _leaf_parser(self, parser, ("resolve",))
        _leaf_parser(self, parser, ("proposal", "submit"))

        store_path = ROOT / "src/cement_runtime/store.py"
        baseline_store = subprocess.run(
            ["git", "show", "4783eed:src/cement_runtime/store.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        current_store = store_path.read_bytes()
        self.assertEqual(current_store, baseline_store)
        self.assertEqual(
            hashlib.sha256(current_store).digest(),
            hashlib.sha256(baseline_store).digest(),
        )
        self.assertEqual(SCHEMA_VERSION, 2)

        _, ledger = _new_system(self)
        before = _table_counts(ledger)
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                '{"input":12,"output":34}',
            ]
        )
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(set(_payload(stdout)), {"proposal_id"})
        after = _table_counts(ledger)
        delta = {table: after[table] - before[table] for table in before}
        self.assertEqual(
            {table: count for table, count in delta.items() if count},
            {"events": 1, "proposals": 1, "requests": 1},
        )

        cli_source = (ROOT / "src/cement_runtime/cli.py").read_text(encoding="utf-8")
        cli_tree = ast.parse(cli_source)
        # M3.5b D08/D19 INVERT this block. The pre-removal reading pinned the
        # import, the helper and `handle`'s three source destinations as
        # SURVIVORS; the unit is chartered to delete all five, so the assertion
        # is restated over the post-removal property. `source.py` itself is
        # untouched here and belongs to M3.7.
        imports = [
            alias.name
            for node in cli_tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "source"
            for alias in node.names
        ]
        self.assertEqual(imports, [])
        self.assertEqual(
            [
                node
                for node in cli_tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "_source"
            ],
            [],
        )
        self.assertEqual(
            sum(
                isinstance(node, ast.Name) and node.id == "CommandCandidateSource"
                for node in ast.walk(cli_tree)
            ),
            0,
        )
        self.assertFalse(hasattr(cement_cli, "CommandCandidateSource"))
        self.assertIsNotNone(CommandCandidateSource)
        # D05: subcommand names are exact-match, so the removed leaf raises an
        # invalid-choice error whose message ENUMERATES the survivors. That makes
        # the refusal a complement assertion for free.
        for removed in ("handle", "request"):
            with self.assertRaises(cement_cli._UsageError) as raised:
                parser.parse_args([removed, OPERATION])
            message = str(raised.exception)
            self.assertIn(f"invalid choice: '{removed}'", message)
            for survivor in ("operation", "resolve", "proposal", "function", "events"):
                self.assertIn(f"'{survivor}'", message)

        base_source = subprocess.run(
            ["git", "show", "c8b82cd:src/cement_runtime/cli.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        module_name = "cement_runtime._m3u5a_d26_base_cli"
        base_module = types.ModuleType(module_name)
        base_module.__file__ = "<git:c8b82cd:src/cement_runtime/cli.py>"
        base_module.__package__ = "cement_runtime"
        sys.modules[module_name] = base_module
        self.addCleanup(sys.modules.pop, module_name, None)
        exec(  # noqa: S102 - committed Git source is the oracle.
            compile(base_source, base_module.__file__, "exec"),
            base_module.__dict__,
        )

        def owners(node: argparse.ArgumentParser, option: str) -> set[str]:
            return {
                path
                for path, leaf in _leaf_parsers(node).items()
                if any(option in action.option_strings for action in leaf._actions)
            }

        self.assertEqual(owners(parser, "--submission"), {"proposal submit"})
        self.assertEqual(
            owners(parser, "--expected-function-hash"),
            owners(base_module._parser(), "--expected-function-hash") | {"resolve"},
        )
        self.assertNotIn("proposal submit", owners(parser, "--expected-function-hash"))

        cross_probes = (
            (
                ["resolve", OPERATION, "--input", "12", "--submission", "{}"],
                "--submission",
            ),
            (
                [
                    "proposal",
                    "submit",
                    OPERATION,
                    "--submission",
                    '{"input":12,"output":34}',
                    "--expected-function-hash",
                    "0" * 64,
                ],
                "--expected-function-hash",
            ),
        )
        for argv, option in cross_probes:
            with self.subTest(option=option):
                status, stdout, stderr = _invoke(argv)
                self.assertEqual((status, stdout), (2, ""))
                self.assertIn(
                    f"unrecognized arguments: {option}", _payload(stderr)["message"]
                )

    def test_d27_b02_drops_cli_py_from_its_frozen_tuple_and_keeps_command_s(
        self,
    ) -> None:
        """D27 obligation

        CONTRACT:
        B02 drops `cli.py` from its frozen tuple and keeps `_command_supervisor.py` and
        `example_adapter.py` frozen at `f9b9755`, which stay correct until M3.7 relocates them.
        The retired member is not deleted silently: the property it carried — M3.3 added no CLI
        channel and no CLI source reach — is exactly what this unit retires, and it MIGRATES to
        D24 (zero `_source`, `System.propose` and source calls), D25 (the census-derived 28→30
        / 35→37 delta with all 28 existing leaf paths unchanged) and D26 (cross-leaf option
        isolation), which are strictly stronger because they constrain what the new bytes may
        be rather than that there are none. B02's docstring states where the property went, so
        a reader of the surviving pin can find it.

        AMENDED-BY A8, superseding the text above:
        D27's claim that D24, D25 and D26 are `strictly stronger` than B02's retired `cli.py`
        byte pin is FALSE and withdrawn. The three cover source reach, leaf names and option
        isolation; none notices an old leaf's changed default, help string, payload or
        dispatch. Demonstrated by mutating `events --limit` from 1000 to 7: census stays 30/37
        and every D24/D25/D26 assertion stays green. The replacement is gate 4's `parser_shape`
        digest, which moves on that exact mutation. D27 now claims what is true — the migration
        preserves B02's CLI-preservation property through a behavioural digest rather than a
        byte pin over a file this unit is chartered to extend.
        """
        # BASELINE c8b82cd: red — B02 still freezes cli.py and has no migrated-property note.
        battery_path = ROOT / "tests/test_submission_battery.py"
        battery_tree = ast.parse(battery_path.read_text(encoding="utf-8"))
        battery_class = next(
            node
            for node in battery_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "SubmissionBatteryTests"
        )
        b02 = next(
            node
            for node in battery_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "test_b02_cli_py_command_supervisor_py_and"
        )
        paths_assignment = next(
            node
            for node in b02.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "paths"
                for target in node.targets
            )
        )
        paths = ast.literal_eval(paths_assignment.value)
        self.assertEqual(
            paths,
            (
                "src/cement_runtime/_command_supervisor.py",
                "src/cement_runtime/example_adapter.py",
            ),
        )
        docstring = ast.get_docstring(b02) or ""
        for obligation in ("D24", "D25", "D26"):
            self.assertIn(obligation, docstring)
        self.assertNotIn("strictly stronger", docstring.lower())
        for relative_path in paths:
            baseline = subprocess.run(
                ["git", "show", f"f9b9755:{relative_path}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual((ROOT / relative_path).read_bytes(), baseline)

        def parser_shape(parser: argparse.ArgumentParser) -> tuple[int, str]:
            rows: list[str] = []

            def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
                rows.append(
                    "|".join(
                        (" ".join(path), "<node>", repr(bool(node.allow_abbrev)))
                    )
                )
                children = [
                    action
                    for action in node._actions
                    if isinstance(action, argparse._SubParsersAction)
                ]
                for action in sorted(node._actions, key=lambda item: item.dest):
                    if isinstance(action, argparse._SubParsersAction):
                        continue
                    rows.append(
                        "|".join(
                            (
                                " ".join(path),
                                action.dest,
                                ",".join(sorted(action.option_strings)),
                                repr(action.default),
                                repr(bool(action.required)),
                                repr(action.nargs),
                                type(action).__name__,
                            )
                        )
                    )
                for action in children:
                    for name, child in sorted(action.choices.items()):
                        visit(child, (*path, name))

            visit(parser, ())
            digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()[:16]
            return len(rows), digest

        probe_path = ROOT / ".agent/decisions/m3u5a-s2-probe.py"
        probe_tree = ast.parse(probe_path.read_text(encoding="utf-8"))
        expected_assignment = next(
            node
            for node in probe_tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "EXPECTED"
        )
        expected = ast.literal_eval(expected_assignment.value)
        parser = cement_cli._parser()
        self.assertEqual(
            parser_shape(parser),
            (expected["parser_shape"]["actions"], expected["parser_shape"]["digest"]),
        )
        before = parser_shape(parser)
        events = _leaf_parser(self, parser, ("events",))
        limit = next(action for action in events._actions if action.dest == "limit")
        original_default = limit.default
        limit.default = 7
        try:
            mutated = parser_shape(parser)
        finally:
            limit.default = original_default
        self.assertNotEqual(mutated, before)

    def test_d28_both_commands_are_named_positively_in_operator_facing_pros(
        self,
    ) -> None:
        """D28 obligation

        CONTRACT:
        Both commands are named POSITIVELY in operator-facing prose. `X21`'s census found zero
        literal submit grammars, zero `System.resolve` mentions and zero root `resolve`
        commands across `README.md`, `docs/architecture.md`, `docs/adapter-protocol.md` and
        `docs/threat-model.md`, so there is no stale text to refresh and a "no sentence is
        falsified" test passes vacuously. A reader must learn from prose alone: that both
        commands exist, their grammar, their payload keys, their exit classes, that submission
        is not idempotent, and that resolve writes nothing. Mechanical test: grep both command
        spellings across README and every normative doc.

        AMENDED-BY A6, superseding the text above:
        The mechanical grep is a UNION over `README.md`, `docs/architecture.md` and
        `docs/threat-model.md`: each spelling appears at least once in that union, and README
        carries both. `docs/adapter-protocol.md` is OUTSIDE the union — it documents the
        adapter protocol and names no CLI leaf. Measured cells for (`cement resolve`, `cement
        proposal submit`): README `(1,1)`, architecture `(1,1)`, threat-model `(1,2)`,
        adapter-protocol `(0,0)`. The per-file reading is rejected on merits: it forces
        redundant grammar transcription into documents whose job is not teaching invocation,
        and duplicated grammar is what goes stale. Shipped blocks spell the invocation `uv run
        cement … resolve`, so a token search must accept both spellings.

        AMENDED-BY A19, superseding the text above:
        Publication enumerates BOTH schemas, which D28 collapsed into one phrase: the
        SUBMISSION ENVELOPE's required `input` and `output` plus optional `provenance`, and the
        ACKNOWLEDGEMENT's single `proposal_id`. A reader who learns every output key and no
        input key cannot construct `--submission` (`Y20`).
        """
        # BASELINE c8b82cd: red — neither command is published because neither parser leaf exists.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        texts = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "docs/architecture.md": (ROOT / "docs/architecture.md").read_text(
                encoding="utf-8"
            ),
            "docs/threat-model.md": (ROOT / "docs/threat-model.md").read_text(
                encoding="utf-8"
            ),
        }
        resolve_pattern = re.compile(r"\bcement\b[^\n]*\bresolve\b", re.IGNORECASE)
        submit_pattern = re.compile(
            r"\bcement\b[^\n]*\bproposal\s+submit\b",
            re.IGNORECASE,
        )
        cells = {
            name: (
                bool(resolve_pattern.search(text)),
                bool(submit_pattern.search(text)),
            )
            for name, text in texts.items()
        }
        self.assertTrue(any(resolve for resolve, _ in cells.values()))
        self.assertTrue(any(submit for _, submit in cells.values()))
        self.assertEqual(cells["README.md"], (True, True))

        def markdown_sections(text: str) -> list[str]:
            headings = list(re.finditer(r"^(#{1,6})\s+.+$", text, re.MULTILINE))
            sections: list[str] = []
            for index, heading in enumerate(headings):
                level = len(heading.group(1))
                end = len(text)
                for later in headings[index + 1 :]:
                    if len(later.group(1)) <= level:
                        end = later.start()
                        break
                sections.append(text[heading.start() : end])
            return sections

        readme_sections = markdown_sections(texts["README.md"])
        resolve_sections = "\n".join(
            section for section in readme_sections if resolve_pattern.search(section)
        )
        submit_sections = "\n".join(
            section for section in readme_sections if submit_pattern.search(section)
        )
        self.assertTrue(resolve_sections)
        self.assertTrue(submit_sections)
        self.assertRegex(
            resolve_sections,
            r"(?s)\bresolve\s+\S+.*?--input(?:\s|`)",
        )
        self.assertIn("--expected-function-hash", resolve_sections)
        self.assertRegex(
            submit_sections,
            r"(?s)\bproposal\s+submit\s+\S+.*?--submission(?:\s|`)",
        )
        for key in (
            "artifact_hash",
            "checks",
            "entries",
            "function_hash",
            "matched",
            "output",
            "passed",
        ):
            self.assertIn(key, resolve_sections)
        for key in ("input", "output", "provenance", "proposal_id"):
            self.assertIn(key, submit_sections)
        self.assertRegex(submit_sections.lower(), r"\brequired\b")
        self.assertRegex(submit_sections.lower(), r"\boptional\b")
        self.assertRegex(
            submit_sections.lower(), r"\b(?:not idempotent|no idempotency)\b"
        )
        self.assertRegex(
            resolve_sections.lower(),
            r"(?:`resolve`|\bresolve\b).{0,80}\bwrites nothing\b|\bthe leaf writes nothing\b",
        )

        publication = "\n".join(texts.values())
        exit_classes = {
            int(value)
            for value in re.findall(
                r"\b(?:exit|status)\s+([0-9]+)\b", publication, re.IGNORECASE
            )
        }
        self.assertTrue({0, 2, 3, 4, 5, 6}.issubset(exit_classes))
        self.assertNotIn(1, exit_classes)

    def test_d29_every_placeholder_in_a_shipped_command_block_has_a_produci(
        self,
    ) -> None:
        """D29 obligation

        CONTRACT:
        Every placeholder in a shipped command block has a producing command earlier in the
        same block, and the human-facing register follows the project's ASD-STE100 rules.
        """
        # BASELINE c8b82cd: red — the new runnable command blocks are not published.
        _leaf_parser(self, cement_cli._parser(), ("resolve",))
        _leaf_parser(self, cement_cli._parser(), ("proposal", "submit"))
        documents = {
            path: (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "README.md",
                "docs/architecture.md",
                "docs/adapter-protocol.md",
                "docs/threat-model.md",
            )
        }
        fence_pattern = re.compile(
            r"^```([^\n]*)\n(.*?)^```[ \t]*$",
            re.MULTILINE | re.DOTALL,
        )
        placeholder_pattern = re.compile(
            r"\b(?:prop_REPLACE_ME|[A-Z][A-Z0-9_]*_FROM_[A-Z][A-Z0-9_]*|"
            r"[A-Z][A-Z0-9_]*_REPLACE_ME)\b"
        )
        found: set[str] = set()
        orphans: list[str] = []
        for path, text in documents.items():
            for fence_index, match in enumerate(fence_pattern.finditer(text), start=1):
                language = match.group(1).strip().lower()
                if language not in {"bash", "sh", "shell", "console"}:
                    continue
                lines = match.group(2).splitlines()
                for line_index, line in enumerate(lines):
                    for placeholder in placeholder_pattern.findall(line):
                        found.add(placeholder)
                        prior = "\n".join(lines[:line_index])
                        if placeholder.startswith("prop_"):
                            produced = (
                                re.search(r"\bproposal\s+list\b", prior) is not None
                            )
                        elif "_FROM_" in placeholder:
                            producer = (
                                placeholder.rsplit("_FROM_", 1)[1]
                                .lower()
                                .replace("_", " ")
                            )
                            produced = (
                                re.search(
                                    rf"\bfunction\s+{re.escape(producer)}\b",
                                    prior,
                                )
                                is not None
                            )
                        else:
                            produced = False
                        if not produced:
                            orphans.append(
                                f"{path}:fence-{fence_index}:line-{line_index + 1}:{placeholder}"
                            )
        self.assertEqual(orphans, [])
        self.assertTrue(
            {"prop_REPLACE_ME", "HASH_FROM_INSPECT", "HASH_FROM_VERIFY"}.issubset(found)
        )

        touched_prose: list[str] = []
        for text in (
            documents["README.md"],
            documents["docs/architecture.md"],
            documents["docs/threat-model.md"],
        ):
            prose = fence_pattern.sub("", text)
            touched_prose.extend(
                paragraph
                for paragraph in re.split(r"\n\s*\n", prose)
                if re.search(
                    r"cement resolve|cement proposal submit", paragraph, re.IGNORECASE
                )
            )
        self.assertTrue(touched_prose)
        register = "\n".join(touched_prose)
        self.assertNotRegex(
            register.lower(), r"\b(?:simply|robust|seamlessly|leverage)\b"
        )
        sentence_violations: list[tuple[int, str]] = []
        instruction_violations: list[tuple[int, str]] = []
        imperatives = {
            "run",
            "use",
            "pass",
            "read",
            "list",
            "keep",
            "do",
            "set",
            "give",
        }
        for sentence in re.split(r"(?<=[.!?])\s+", register):
            plain = re.sub(r"[`*_#|]", "", sentence).strip()
            words = re.findall(r"\b[\w-]+\b", plain)
            if words and len(words) > 25:
                sentence_violations.append((len(words), plain))
            if words and words[0].lower() in imperatives and len(words) > 20:
                instruction_violations.append((len(words), plain))
        self.assertEqual(sentence_violations, [])
        self.assertEqual(instruction_violations, [])

    def test_d30_resolve_s_cost_is_published_where_an_operator_meets_it_one(
        self,
    ) -> None:
        """D30 obligation

        CONTRACT:
        Resolve's cost is published where an operator meets it: one resolve runs the full
        six-check verification and costs what `verify_function` costs. Cite
        `m3u2b-resolve-bench.json`'s own `resolve_cold_hit_ms`, measured end to end through the
        shipped method — 36,452 ms and 985,696 KiB peak RSS at the 50,000-entry cap, 613 ms at
        1,000, 5.7 ms at one — matching the method docstring's `~36.5 s` and `~963 MiB`. Any
        prose figure is DERIVED from that artifact at the precision it states, never
        transcribed, so a re-measurement moves prose and artifact together or fails loudly. No
        help or doc sentence may call resolve fast, cheap or cached on the grounds that it is
        read-only.

        AMENDED-BY A16, superseding the text above:
        Two corrections. The published figures are **`System.resolve` METHOD latency**: the
        harness constructs `System` before starting its timer, so interpreter startup,
        argparse, the ledger precheck, schema initialisation and CLI JSON projection are all
        outside them, and at the one-entry `5.7 ms` point that overhead is not negligible
        (`Y15`). And `costs what verify_function costs` is WITHDRAWN as an equality claim: the
        two artifacts were measured at different commits (`23ec5717…` vs `019d0409…`), which
        the project's own per-point provenance rule makes non-evidentiary, and the cold ratios
        span 1.393 / 0.995 / 1.025 (`Y16`). What ships is the true and cheaper statement — one
        resolve performs one full six-check verification — beside resolve's OWN measured cost.
        """
        # BASELINE c8b82cd: red — operators have no resolve command or cost warning.
        resolve_parser = _leaf_parser(self, cement_cli._parser(), ("resolve",))
        artifact_path = ROOT / ".agent/decisions/m3u2b-resolve-bench.json"
        benchmark = json.loads(artifact_path.read_text(encoding="utf-8"))
        points = benchmark["points"]
        n1_ms = points["n1"]["resolve_cold_hit_ms"]
        n1000_ms = points["n1000"]["resolve_cold_hit_ms"]
        n50000_ms = points["n50000"]["resolve_cold_hit_ms"]
        n50000_rss = points["n50000"]["peak_rss_kib"]
        derived = {
            "n1": f"{n1_ms:.1f} ms",
            "n1000": f"{n1000_ms:,.0f} ms",
            "n50000_ms": f"{n50000_ms:,.0f} ms",
            "n50000_s": f"{n50000_ms / 1_000:.1f} s",
            "n50000_kib": f"{n50000_rss:,.0f} KiB",
            "n50000_mib": f"{n50000_rss / 1_024:,.0f} MiB",
        }

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        architecture = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        threat_model = (ROOT / "docs/threat-model.md").read_text(encoding="utf-8")
        operator_prose = (
            f"{readme}\n{architecture}\n{threat_model}\n{resolve_parser.format_help()}"
        )
        self.assertIn("m3u2b-resolve-bench.json", operator_prose)
        self.assertIn(derived["n1"], operator_prose)
        self.assertIn(derived["n1000"], operator_prose)
        self.assertTrue(
            derived["n50000_ms"] in operator_prose
            or derived["n50000_s"] in operator_prose
        )
        self.assertTrue(
            derived["n50000_kib"] in operator_prose
            or derived["n50000_mib"] in operator_prose
        )

        system, _ = _new_system(self)
        check_count = len(system.verify_function(PARTITION, OPERATION).checks)
        number_words = (
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
        )
        self.assertLess(check_count, len(number_words))
        self.assertRegex(
            operator_prose.lower(),
            rf"full\s+{number_words[check_count]}-check\s+verification",
        )
        self.assertIn("Cement caches no verification between calls", operator_prose)
        self.assertNotRegex(operator_prose.lower(), r"\b(?:fast|cheap)\b")
        # Docs may write `cached output` and `Quick start` about other subjects;
        # a help screen has no such room, so the whole cost vocabulary is banned
        # across every parser rather than only the two words the prose can spare.
        self.assertNotRegex(
            _help_surfaces(cement_cli._parser()).lower(),
            r"\b(?:cached|cheap|cheaply|fast|instant|instantly|quick|quickly)\b",
        )
        self.assertNotRegex(
            operator_prose.lower(),
            r"\bresolve\b[^.]{0,100}\b(?:is|stays|uses|returns)\s+cached\b",
        )


if __name__ == "__main__":
    unittest.main()
