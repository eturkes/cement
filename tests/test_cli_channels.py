"""M3.5a phase-2 red suite: one test per ruled verdict row.

Seeded by `.agent/decisions/m3u5a-suite-validate.py --emit-stub` from the ruled
`m3u5a-verdicts.json`. Each docstring carries the row's ruled observable and its
battery action verbatim; the body is the work.

ENCODE        pin the ruled observable as written.
ENCODE-SCOPED pin the NARROWED form named in the verdict. The literal row goes red
              against correct code, so encoding it as written is a defect.

Replace each `self.fail` marker with real assertions. A body that asserts nothing
is graded ASSERTIONLESS and fails the validator.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import closing, redirect_stderr, redirect_stdout
from dataclasses import dataclass
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

import cement_runtime
from cement_runtime import Candidate, CompilePolicy, System
from cement_runtime import cli as cement_cli
from cement_runtime import system as system_module
from cement_runtime.errors import (
    CementError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    ValidationError,
)
from cement_runtime.function import FunctionMatch
from cement_runtime.json_value import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
    canonicalize,
)
from cement_runtime.models import FunctionCheck, FunctionResolution, FunctionVerification
from cement_runtime.store import SCHEMA_VERSION, Store


ROOT = Path(__file__).resolve().parents[1]
PARTITION = "tenant"
OPERATION = "op"
CHECK_KEYS = (
    "duplicate-input-digests",
    "abi-canonicalizer-uniform",
    "sealed-passing-reports",
    "current-promotion-receipts",
    "function-hash-matches-snapshot",
    "persisted-function-receipt",
)
RESOLVE_KEYS = {
    "artifact_hash",
    "checks",
    "entries",
    "function_hash",
    "matched",
    "output",
    "passed",
}
PROVENANCE_MAX_BYTES = getattr(system_module, "PROVENANCE_MAX_BYTES", 65_536)
SUBMISSION_FRAMING = len(b'{"input":,"output":,"provenance":}')
SUBMISSION_MAX_BYTES = 2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + SUBMISSION_FRAMING


@dataclass(frozen=True, slots=True)
class _Run:
    status: int
    stdout: str
    stderr: str

    @property
    def stdout_json(self) -> object | None:
        return json.loads(self.stdout) if self.stdout else None

    @property
    def stderr_json(self) -> object | None:
        return json.loads(self.stderr) if self.stderr else None


class _Source:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def propose(self, request: object) -> Candidate:
        self.calls.append(request)
        raise AssertionError("new CLI channels reached the configured source")


def _checks(*, passed: bool = True) -> tuple[FunctionCheck, ...]:
    return tuple(
        FunctionCheck(key=key, passed=passed, detail=f"{key} detail")
        for key in CHECK_KEYS
    )


def _resolution(state: str) -> FunctionResolution:
    if state == "hit":
        verification = FunctionVerification(
            passed=True,
            entries=1,
            document=mock.sentinel.document,
            function_hash="a" * 64,
            checks=_checks(),
        )
        match = FunctionMatch(
            matched=True,
            output={"answer": "projected"},
            artifact_hash="b" * 64,
        )
    elif state == "miss":
        verification = FunctionVerification(
            passed=True,
            entries=0,
            document=mock.sentinel.document,
            function_hash="c" * 64,
            checks=_checks(),
        )
        match = FunctionMatch(matched=False)
    elif state == "failed":
        verification = FunctionVerification(
            passed=False,
            entries=3,
            document=None,
            function_hash="d" * 64,
            checks=_checks(passed=False),
        )
        match = None
    else:  # pragma: no cover - test helper misuse
        raise AssertionError(f"unknown state: {state}")
    return FunctionResolution(verification=verification, match=match)


def _parser_nodes(
    parser: argparse.ArgumentParser,
) -> tuple[dict[tuple[str, ...], argparse.ArgumentParser], int]:
    leaves: dict[tuple[str, ...], argparse.ArgumentParser] = {}
    count = 0

    def walk(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        nonlocal count
        count += 1
        children = [
            action
            for action in node._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if not children:
            leaves[path] = node
            return
        for action in children:
            for name, child in action.choices.items():
                walk(child, (*path, name))

    walk(parser, ())
    return leaves, count


def _baseline_parser() -> argparse.ArgumentParser:
    source = subprocess.check_output(
        ("git", "-C", str(ROOT), "show", "c8b82cd:src/cement_runtime/cli.py"),
        text=True,
    )
    name = "cement_runtime._m3u5a_baseline_cli"
    module = types.ModuleType(name)
    module.__file__ = f"{name}.py"
    module.__package__ = "cement_runtime"
    sys.modules[name] = module
    try:
        exec(compile(source, module.__file__, "exec"), module.__dict__)
        return module._parser()
    finally:
        sys.modules.pop(name, None)


class CliChannelTests(unittest.TestCase):
    """Ruled M3.5a CLI-channel obligations, one test per verdict row."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "ledger.db"
        System(self.database)
        self.base = ["--db", str(self.database), "--partition", PARTITION]

    def run_argv(self, arguments: list[str]) -> _Run:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = cement_cli.main(arguments)
        return _Run(status, stdout.getvalue(), stderr.getvalue())

    def run_cli(self, *arguments: str) -> _Run:
        return self.run_argv([*self.base, *arguments])

    def error(self, run: _Run) -> dict[str, object]:
        self.assertIsInstance(run.stderr_json, dict)
        return dict(run.stderr_json)  # type: ignore[arg-type]

    def payload(self, run: _Run) -> dict[str, object]:
        self.assertIsInstance(run.stdout_json, dict)
        return dict(run.stdout_json)  # type: ignore[arg-type]

    def register(self, operation: str = OPERATION) -> System:
        system = System(self.database)
        system.register_operation(
            PARTITION,
            operation,
            policy=CompilePolicy(2, 1, 0),
        )
        return system

    def promoted_system(
        self,
        operation: str = OPERATION,
    ) -> tuple[System, dict[str, int]]:
        system = self.register(operation)
        input_value = {"query": 1}
        candidate = Candidate(output={"answer": 2}, provenance={"fixture": 1})
        for index in range(2):
            proposal_id = system.submit_proposal(
                PARTITION,
                operation,
                input_value,
                candidate=candidate,
            )
            system.review(
                PARTITION,
                proposal_id,
                reviewer=f"reviewer-{index}",
                decision="accept",
            )
        compiled = system.compile(PARTITION, operation)
        if len(compiled.created) != 1:
            raise AssertionError(f"fixture compiled {len(compiled.created)} artifacts")
        verified = system.verify_drafts(PARTITION, operation, verified_by="verifier")
        if not verified.passed:
            raise AssertionError("fixture draft verification failed")
        manifest = system.inspect_function_promotion(PARTITION, operation)
        system.promote_function(
            PARTITION,
            operation,
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        return system, input_value

    def parser_node(self, *path: str) -> argparse.ArgumentParser | None:
        return _parser_nodes(cement_cli._parser())[0].get(tuple(path))

    def table_counts(self, path: Path | None = None) -> dict[str, int]:
        database = self.database if path is None else path
        with closing(sqlite3.connect(database)) as connection:
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

    def test_v01_resolve_grammar_one_positional_plus_required_input_plus_op(self) -> None:
        """V01 [D01] resolve grammar: one positional plus required --input plus optional --expected-function-hash

        ACTION: ENCODE

        EXPECTED:
        The action destination set is exactly `{operation, input, expected_function_hash}`;
        `resolve op --input 0` parses with `expected_function_hash=None`, while a missing
        operation or input exits 2.

        RULING:
        CONFIRMED. Shipped grammar is exactly that: one positional `operation`, required
        `--input`, optional `--expected-function-hash` defaulting to None,
        `allow_abbrev=False`. Deriving the destination set from the node rather than
        transcribing it is what makes a fourth argument fail the test instead of passing
        unnoticed.
        """
        parser = cement_cli._parser()
        node = self.parser_node("resolve")
        self.assertIsNotNone(node)
        assert node is not None
        destinations = {action.dest for action in node._actions if action.dest != "help"}
        self.assertEqual(destinations, {"operation", "input", "expected_function_hash"})
        parsed = parser.parse_args(["resolve", OPERATION, "--input", "0"])
        self.assertEqual(parsed.operation, OPERATION)
        self.assertEqual(parsed.input, "0")
        self.assertIsNone(parsed.expected_function_hash)
        for arguments in (("resolve", "--input", "0"), ("resolve", OPERATION)):
            with self.subTest(arguments=arguments):
                with self.assertRaises(cement_cli._UsageError):
                    parser.parse_args(arguments)

    def test_v02_resolve_rejects_every_option_prefix_in_exp_inp_under_allow(self) -> None:
        """V02 [D01] resolve rejects every option prefix (--in, --exp, --inp) under allow_abbrev=False

        ACTION: ENCODE

        EXPECTED:
        Each of the 3 probes exits 2, writes no stdout, and includes the exact phrase
        `unrecognized arguments` plus the supplied prefix on stderr.

        RULING:
        CONFIRMED, and the probe's construction is why it survives amendment A1. It supplies a
        full `--input 0` alongside each prefix, which is exactly the condition under which
        argparse reaches its leftover check. Measured: `--in 1` and `--exp x` both yield
        `unrecognized arguments: <prefix> <value>` at exit 2 with empty stdout. A prefix-ALONE
        probe would instead report the missing required option; see A1 and the V18 ruling.
        """
        probes = (("--in", "1"), ("--inp", "1"), ("--exp", "00"))
        for prefix, value in probes:
            with self.subTest(prefix=prefix):
                run = self.run_cli(
                    "resolve", OPERATION, "--input", "0", prefix, value
                )
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout, "")
                self.assertEqual(
                    self.error(run),
                    {
                        "error": "invalid",
                        "message": f"unrecognized arguments: {prefix} {value}",
                    },
                )

    def test_v03_resolve_input_at_default_max_bytes_and_at_default_max_byte(self) -> None:
        """V03 [D02] resolve --input - at DEFAULT_MAX_BYTES and at DEFAULT_MAX_BYTES + 1

        ACTION: ENCODE

        EXPECTED:
        At 1048576 bytes `System.resolve` is called exactly 1 time; at 1048577 bytes status is
        2, call count is 0, and the message is `JSON stdin exceeds 1048576 bytes`.

        RULING:
        CONFIRMED. `--input` is the shipped `_input` verbatim; resolve adds no reader, so the
        1,048,576-byte bound and its message are inherited rather than restated. The adjacent
        accept/reject pair is the whole obligation - a constant-only pin would pass against a
        bound the code never applies.
        """
        sources = (
            b'"' + b"x" * (DEFAULT_MAX_BYTES - 2) + b'"',
            b'"' + b"x" * (DEFAULT_MAX_BYTES - 1) + b'"',
        )
        self.assertEqual(tuple(map(len, sources)), (DEFAULT_MAX_BYTES, DEFAULT_MAX_BYTES + 1))
        calls: list[int] = []
        for source in sources:
            with self.subTest(size=len(source)):
                stdin = types.SimpleNamespace(buffer=io.BytesIO(source))
                with mock.patch.object(sys, "stdin", stdin), mock.patch.object(
                    System, "resolve", autospec=True, return_value=_resolution("miss")
                ) as resolve:
                    run = self.run_cli("resolve", OPERATION, "--input", "-")
                calls.append(resolve.call_count)
                if len(source) == DEFAULT_MAX_BYTES:
                    self.assertEqual(resolve.call_count, 1)
                else:
                    self.assertEqual(run.status, 2)
                    self.assertEqual(resolve.call_count, 0)
                    self.assertEqual(
                        self.error(run)["message"],
                        f"JSON stdin exceeds {DEFAULT_MAX_BYTES} bytes",
                    )
        self.assertEqual(calls, [1, 0])

    def test_v04_resolve_input_malformed_json_which_of_input_s_three_famili(self) -> None:
        """V04 [D02] resolve --input malformed JSON: which of _input's three families answers

        ACTION: ENCODE

        EXPECTED:
        Status is 2, stdout is empty, `System.resolve` has 0 calls, and stderr message equals
        `invalid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char
        1)`.

        RULING:
        CONFIRMED. The invalid-JSON family answers, `System.resolve` is never called, and the
        message carries the parser's own position text. Pinning the full sentence including
        `line 1 column 2 (char 1)` is deliberate: it proves the CLI forwards the parser verdict
        rather than substituting a summary.
        """
        with mock.patch.object(
            System, "resolve", autospec=True, return_value=_resolution("miss")
        ) as resolve:
            run = self.run_cli("resolve", OPERATION, "--input", "{")
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout, "")
        self.assertEqual(resolve.call_count, 0)
        self.assertEqual(
            self.error(run),
            {
                "error": "invalid",
                "message": (
                    "invalid JSON: Expecting property name enclosed in double quotes: "
                    "line 1 column 2 (char 1)"
                ),
            },
        )

    def test_v05_a_configured_candidate_source_is_never_called_by_either_ne(self) -> None:
        """V05 [D03] a configured candidate source is never called by either new leaf

        ACTION: ENCODE

        EXPECTED:
        Both commands complete with counters exactly `{_source: 0, System.propose: 0,
        CandidateSource.propose: 0}`; resolve calls `System.resolve` once and submit calls
        `System.submit_proposal` once.

        RULING:
        CONFIRMED. This is D24's headline isolation predicate on the resolve side. A configured
        source must be present for the zero to mean anything, which the probe does, and the
        counter set covers the builder, the library route and the source object separately.
        """
        source = _Source()
        system = System(self.database, candidate_source=source)
        system.register_operation(PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0))
        envelope = json.dumps({"input": 0, "output": 1, "provenance": {}})
        with mock.patch.object(cement_cli, "System", return_value=system), mock.patch.object(
            cement_cli, "_source", wraps=cement_cli._source
        ) as source_builder, mock.patch.object(
            system, "resolve", wraps=system.resolve
        ) as resolve, mock.patch.object(
            system, "submit_proposal", wraps=system.submit_proposal
        ) as submit, mock.patch.object(
            system, "propose", wraps=system.propose
        ) as propose:
            resolved = self.run_cli("resolve", OPERATION, "--input", "0")
            submitted = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", envelope
            )
        self.assertIn(resolved.status, (0, 6))
        self.assertEqual(submitted.status, 0)
        self.assertEqual(
            {
                "_source": source_builder.call_count,
                "System.propose": propose.call_count,
                "CandidateSource.propose": len(source.calls),
            },
            {"_source": 0, "System.propose": 0, "CandidateSource.propose": 0},
        )
        self.assertEqual((resolve.call_count, submit.call_count), (1, 1))

    def test_v06_db_and_partition_gate_order_and_exact_text_on_the_resolve(self) -> None:
        """V06 [D04] --db and --partition gate order and exact text on the resolve path

        ACTION: ENCODE

        EXPECTED:
        The two resolve runs exit 2 with exact messages `--db or CEMENT_DB is required` and
        `--partition or CEMENT_PARTITION is required`; `_input` and `System` each have 0 calls.

        RULING:
        CONFIRMED. Both gates keep their shipped order and exact text, and both precede
        `_input` and `System`. Asserting zero `_input` calls is what distinguishes a gate that
        runs first from a gate that merely runs.
        """
        cases = (
            (
                ["resolve", OPERATION, "--input", "{"],
                "--db or CEMENT_DB is required",
            ),
            (
                ["--db", str(self.database), "resolve", OPERATION, "--input", "{"],
                "--partition or CEMENT_PARTITION is required",
            ),
        )
        with mock.patch.object(cement_cli, "_input", wraps=cement_cli._input) as input_, mock.patch.object(
            cement_cli, "System", autospec=True
        ) as system:
            observations = []
            for arguments, message in cases:
                run = self.run_argv(arguments)
                observations.append((run.status, self.error(run)["message"]))
                self.assertEqual(run.stdout, "")
                self.assertEqual(self.error(run)["message"], message)
        self.assertEqual(
            observations,
            [
                (2, "--db or CEMENT_DB is required"),
                (2, "--partition or CEMENT_PARTITION is required"),
            ],
        )
        self.assertEqual((input_.call_count, system.call_count), (0, 0))

    def test_v07_expected_function_hash_mismatch_and_malformed_digest_libra(self) -> None:
        """V07 [D05] --expected-function-hash mismatch and malformed digest: library-owned verdict and class

        ACTION: ENCODE

        EXPECTED:
        `bad` exits 2 with message `expected_function_hash must be a SHA-256 hex digest`; `0`
        repeated 64 exits 6 on stdout with `passed:false` and `matched:null`.

        RULING:
        CONFIRMED and it separates the two halves of D05 correctly. A malformed digest is a
        library ValidationError at exit 2; a well-formed digest that does not match the
        promoted set is a negative VERDICT at exit 6 with the full payload on stdout. The CLI
        grades neither - it forwards the value verbatim.
        """
        system = self.register()
        actual = system.resolve(PARTITION, OPERATION, 0).verification.function_hash
        self.assertIsNotNone(actual)
        malformed = self.run_cli(
            "resolve",
            OPERATION,
            "--input",
            "0",
            "--expected-function-hash",
            "bad",
        )
        self.assertEqual(malformed.status, 2)
        self.assertEqual(malformed.stdout, "")
        self.assertEqual(
            self.error(malformed)["message"],
            "expected_function_hash must be a SHA-256 hex digest",
        )
        wrong = "0" * 64 if actual != "0" * 64 else "1" * 64
        mismatch = self.run_cli(
            "resolve",
            OPERATION,
            "--input",
            "0",
            "--expected-function-hash",
            wrong,
        )
        payload = self.payload(mismatch)
        self.assertEqual(mismatch.status, 6)
        self.assertEqual(mismatch.stderr, "")
        self.assertIs(payload["passed"], False)
        self.assertIsNone(payload["matched"])

    def test_v08_resolve_writes_no_ledger_byte_no_event_no_clock_read_no_id(self) -> None:
        """V08 [D06] resolve writes no ledger byte, no event, no clock read, no id allocation

        ACTION: ENCODE

        EXPECTED:
        For all 3 states, ledger SHA-256 and dump remain equal, event delta is 0, clock-call
        delta is 0, and `_new_id` call count is 0.

        RULING:
        CONFIRMED. Four independent instruments - ledger digest, ledger dump, event delta and
        `_new_id` call count - over all three resolve states. The dump matters beyond the
        digest because a write that restores the previous bytes would defeat a hash alone.
        """
        system, hit_input = self.promoted_system()
        verification = system.resolve(PARTITION, OPERATION, hit_input).verification
        self.assertIsNotNone(verification.function_hash)
        wrong = (
            "0" * 64
            if verification.function_hash != "0" * 64
            else "1" * 64
        )

        def snapshot() -> tuple[str, tuple[str, ...], int]:
            digest = hashlib.sha256(self.database.read_bytes()).hexdigest()
            with closing(sqlite3.connect(self.database)) as connection:
                dump = tuple(connection.iterdump())
                events = int(
                    connection.execute("SELECT count(*) FROM events").fetchone()[0]
                )
            return digest, dump, events

        cases = (
            ("hit", json.dumps(hit_input), (), 0),
            ("miss", json.dumps({"query": 99}), (), 6),
            (
                "failed",
                json.dumps(hit_input),
                ("--expected-function-hash", wrong),
                6,
            ),
        )

        def now(instance: System) -> int:
            return instance._clock_us()

        observations: list[tuple[bool, int]] = []
        with mock.patch.object(
            system_module, "_new_id", wraps=system_module._new_id
        ) as new_id, mock.patch.object(
            System, "_now", autospec=True, side_effect=now
        ) as clock:
            for label, input_text, extra, expected_status in cases:
                with self.subTest(state=label):
                    before = snapshot()
                    run = self.run_cli(
                        "resolve", OPERATION, "--input", input_text, *extra
                    )
                    after = snapshot()
                    observations.append((before == after, run.status))
                    self.assertEqual(run.status, expected_status)
                    self.assertEqual(after, before)
        self.assertEqual(observations, [(True, 0), (True, 6), (True, 6)])
        self.assertEqual((clock.call_count, new_id.call_count), (0, 0))

    def test_v09_the_payload_key_set_is_exactly_seven_keys_and_identical_in(self) -> None:
        """V09 [D07] the payload key set is exactly seven keys and identical in all three states

        ACTION: ENCODE

        EXPECTED:
        Each object has exactly `{artifact_hash, checks, entries, function_hash, matched,
        output, passed}` and emits those 7 names in that sorted order.

        RULING:
        CONFIRMED. `_emit` sorts keys, so the closed set and the emitted order are one
        assertion. Requiring the SAME set in all three states is the structural half of D11: a
        payload that grows a key on a failed verdict would leak the verification shape.
        """
        observed: list[tuple[str, ...]] = []
        for state in ("hit", "miss", "failed"):
            with self.subTest(state=state), mock.patch.object(
                System, "resolve", autospec=True, return_value=_resolution(state)
            ):
                run = self.run_cli("resolve", OPERATION, "--input", "0")
                payload = self.payload(run)
                keys = tuple(payload)
                observed.append(keys)
                self.assertEqual(set(payload), RESOLVE_KEYS)
                self.assertEqual(keys, tuple(sorted(RESOLVE_KEYS)))
        self.assertEqual(len(set(observed)), 1)
        self.assertEqual(len(observed[0]), 7)

    def test_v10_checks_projects_the_ordered_key_passed_detail_vector_on_su(self) -> None:
        """V10 [D08] checks projects the ordered [{key, passed, detail}] vector on success too

        ACTION: ENCODE

        EXPECTED:
        `checks` has 6 objects, each with exactly `{key, passed, detail}`; keys begin
        `duplicate-input-digests` and end `persisted-function-receipt` in library order.

        RULING:
        CONFIRMED. `checks` is `[asdict(check) for check in verification.checks]`, so the
        vector is the library's own ordering. Pinning first and last key names plus the exact
        triple field set pins the projection without freezing the six check names as CLI
        vocabulary.
        """
        resolution = _resolution("hit")
        with mock.patch.object(
            System, "resolve", autospec=True, return_value=resolution
        ):
            payload = self.payload(
                self.run_cli("resolve", OPERATION, "--input", "0")
            )
        checks = payload["checks"]
        self.assertIsInstance(checks, list)
        assert isinstance(checks, list)
        self.assertEqual(len(checks), 6)
        self.assertEqual(
            [set(check) for check in checks],
            [{"key", "passed", "detail"}] * 6,
        )
        self.assertEqual(
            [check["key"] for check in checks],
            [check.key for check in resolution.verification.checks],
        )
        self.assertEqual(checks[0]["key"], "duplicate-input-digests")
        self.assertEqual(checks[-1]["key"], "persisted-function-receipt")

    def test_v11_verified_miss_is_matched_false_failed_verdict_is_matched_n(self) -> None:
        """V11 [D09] verified miss is matched false; failed verdict is matched null; the two never collapse

        ACTION: ENCODE

        EXPECTED:
        The miss emits `{passed:true, matched:false}` at exit 6; the failed verdict emits
        `{passed:false, matched:null}` at exit 6, and neither object equals the other.

        RULING:
        CONFIRMED. This is the property a shared exit 6 exists to preserve. Both objects carry
        the same seven keys, so `matched` alone separates a verified absence from a failed
        verdict, and asserting the two payloads are unequal blocks a regression that collapses
        them.
        """
        payloads: dict[str, dict[str, object]] = {}
        for state in ("miss", "failed"):
            with mock.patch.object(
                System, "resolve", autospec=True, return_value=_resolution(state)
            ):
                run = self.run_cli("resolve", OPERATION, "--input", "0")
            self.assertEqual(run.status, 6)
            self.assertEqual(run.stderr, "")
            payloads[state] = self.payload(run)
        self.assertEqual(
            (payloads["miss"]["passed"], payloads["miss"]["matched"]),
            (True, False),
        )
        self.assertEqual(
            (payloads["failed"]["passed"], payloads["failed"]["matched"]),
            (False, None),
        )
        self.assertNotEqual(payloads["miss"], payloads["failed"])
        self.assertEqual(set(payloads["miss"]), set(payloads["failed"]))

    def test_v12_output_and_artifact_hash_null_ness_tracks_match_is_none_ex(self) -> None:
        """V12 [D09] output and artifact_hash null-ness tracks match is None exactly

        ACTION: ENCODE

        EXPECTED:
        The 3 projected triples are exactly `(false,false,false)`, `(false,true,true)`, and
        `(true,true,true)`; the locus's claimed iff is false for the verified miss.

        RULING:
        CONFIRMED, and it forced amendment A4. The row is right that D09's locus sentence
        overstates: null-ness of `output` and `artifact_hash` tracks `match is None`, while
        `matched` is null only on a failed verdict. Measured triples of `(matched is None,
        output is None, artifact_hash is None)` are hit (F,F,F), miss (F,T,T), failed (T,T,T).
        A4 rules D09's biconditional to bind `matched` ALONE; the other two are null whenever
        no artifact is projected, which includes the verified miss.
        """
        triples: list[tuple[bool, bool, bool]] = []
        for state in ("hit", "miss", "failed"):
            with mock.patch.object(
                System, "resolve", autospec=True, return_value=_resolution(state)
            ):
                payload = self.payload(
                    self.run_cli("resolve", OPERATION, "--input", "0")
                )
            triples.append(
                (
                    payload["matched"] is None,
                    payload["output"] is None,
                    payload["artifact_hash"] is None,
                )
            )
        self.assertEqual(
            triples,
            [(False, False, False), (False, True, True), (True, True, True)],
        )

    def test_v13_status_0_iff_matched_is_true_else_6_with_both_negative_sta(self) -> None:
        """V13 [D10] status 0 iff matched is true else 6, with both negative states on stdout

        ACTION: ENCODE

        EXPECTED:
        Statuses are exactly `{hit:0, miss:6, failed:6}`; all 3 payloads are JSON on stdout and
        all 3 stderr streams are empty.

        RULING:
        CONFIRMED. `status=0 if matched is True else 6` is shipped, and the `is True` identity
        test is load-bearing: `matched` is a tri-state, so a truthiness test would map null to
        6 by accident rather than by rule. Both negative states use stdout, never `function
        export`'s exceptional stderr channel.
        """
        observations: dict[str, tuple[int, bool, bool]] = {}
        for state, expected_status in (("hit", 0), ("miss", 6), ("failed", 6)):
            with mock.patch.object(
                System, "resolve", autospec=True, return_value=_resolution(state)
            ):
                run = self.run_cli("resolve", OPERATION, "--input", "0")
            observations[state] = (
                run.status,
                isinstance(run.stdout_json, dict),
                run.stderr == "",
            )
            self.assertEqual(run.status, expected_status)
            self.assertIsInstance(run.stdout_json, dict)
            self.assertEqual(run.stderr, "")
        self.assertEqual(
            observations,
            {
                "hit": (0, True, True),
                "miss": (6, True, True),
                "failed": (6, True, True),
            },
        )

    def test_v14_no_functiondocument_field_reaches_stdout_on_any_resolve_br(self) -> None:
        """V14 [D11] no FunctionDocument field reaches stdout on any resolve branch

        ACTION: ENCODE

        EXPECTED:
        All payloads contain exactly 7 top-level keys, contain 0 keys named `document`, and
        contain 0 occurrences of the planted document-only string.

        RULING:
        CONFIRMED. The planted document-only string is what raises this above D07's structural
        pin: a closed key set proves no NEW key appeared, while the planted string proves no
        document byte reached an EXISTING key.
        """
        planted = "DOCUMENT_ONLY_SECRET_V14"
        passing = _resolution("hit")
        planted_verification = FunctionVerification(
            passed=True,
            entries=passing.verification.entries,
            document=types.SimpleNamespace(text=planted, planted=planted),
            function_hash=passing.verification.function_hash,
            checks=passing.verification.checks,
        )
        resolutions = {
            "hit": FunctionResolution(planted_verification, passing.match),
            "miss": FunctionResolution(
                FunctionVerification(
                    passed=True,
                    entries=0,
                    document=types.SimpleNamespace(text=planted, planted=planted),
                    function_hash="c" * 64,
                    checks=_checks(),
                ),
                FunctionMatch(matched=False),
            ),
            "failed": _resolution("failed"),
        }
        observations: list[tuple[int, int]] = []
        for state, resolution in resolutions.items():
            with mock.patch.object(
                System, "resolve", autospec=True, return_value=resolution
            ):
                run = self.run_cli("resolve", OPERATION, "--input", "0")
            payload = self.payload(run)
            encoded = json.dumps(payload, sort_keys=True)
            observations.append((len(payload), encoded.count(planted)))
            self.assertEqual(set(payload), RESOLVE_KEYS)
            self.assertNotIn("document", encoded)
            self.assertNotIn(planted, encoded)
        self.assertEqual(observations, [(7, 0), (7, 0), (7, 0)])

    def test_v15_unregistered_operation_is_3_empty_promoted_set_and_retired(self) -> None:
        """V15 [D12] unregistered operation is 3; empty promoted set and retired-artifact revision are 6

        ACTION: ENCODE

        EXPECTED:
        Unknown operation exits 3 with `operation is not registered in this partition`; empty
        and revised cases each exit 6 with `{entries:0, passed:true, matched:false}`.

        RULING:
        CONFIRMED, and the empty-set case is the discriminating one. An empty promoted set
        verifies successfully and reports a verified absence at exit 6, not an error -
        `build_function` yields an empty document rather than None, so `matched` is false and
        never null. A retired-artifact revision reads identically.
        """
        unknown = self.run_cli("resolve", "absent", "--input", "0")
        self.assertEqual(unknown.status, 3)
        self.assertEqual(unknown.stdout, "")
        self.assertEqual(
            self.error(unknown)["message"],
            "operation is not registered in this partition",
        )

        self.register("empty")
        empty = self.run_cli("resolve", "empty", "--input", "0")
        empty_payload = self.payload(empty)
        self.assertEqual(empty.status, 6)
        self.assertEqual(
            {
                "entries": empty_payload["entries"],
                "passed": empty_payload["passed"],
                "matched": empty_payload["matched"],
            },
            {"entries": 0, "passed": True, "matched": False},
        )

        system, _ = self.promoted_system("revised")
        system.revise_operation(
            PARTITION,
            "revised",
            policy=CompilePolicy(3, 2, 1),
            revised_by="owner",
        )
        revised = self.run_cli("resolve", "revised", "--input", "0")
        revised_payload = self.payload(revised)
        self.assertEqual(revised.status, 6)
        self.assertEqual(
            {
                "entries": revised_payload["entries"],
                "passed": revised_payload["passed"],
                "matched": revised_payload["matched"],
            },
            {"entries": 0, "passed": True, "matched": False},
        )

    def test_v16_an_absent_db_path_answers_integrity_at_5_and_leaves_the_pa(self) -> None:
        """V16 [D13] an absent --db path answers integrity at 5 and leaves the path absent

        ACTION: ENCODE

        EXPECTED:
        Status is 5, stdout is empty, stderr has exactly `{error, message}` with values
        'integrity' and 'ledger file is missing or unreadable', and path existence is false
        before and after.

        RULING:
        CONFIRMED. Exit 5, the exact two-key stderr object, and path absence BEFORE and AFTER.
        The after-check is the obligation: D13 exists because `Store` construction would
        otherwise create the file that resolve was asked to read.
        """
        absent = self.root / "absent.db"
        self.assertFalse(absent.exists())
        run = self.run_argv(
            [
                "--db",
                str(absent),
                "--partition",
                PARTITION,
                "resolve",
                OPERATION,
                "--input",
                "0",
            ]
        )
        self.assertEqual(run.status, 5)
        self.assertEqual(run.stdout, "")
        self.assertEqual(
            self.error(run),
            {
                "error": "integrity",
                "message": "ledger file is missing or unreadable",
            },
        )
        self.assertFalse(absent.exists())

    def test_v17_the_absent_ledger_check_precedes_input_parsing_so_a_malfor(self) -> None:
        """V17 [D13] the absent-ledger check precedes --input parsing, so a malformed input creates no ledger

        ACTION: ENCODE

        EXPECTED:
        The command exits 5 with message `ledger file is missing or unreadable`; `_input` and
        `System` have 0 calls and the absent path remains absent.

        RULING:
        CONFIRMED. Placing the precheck between the `--partition` gate and `System(...)` is
        what makes D04's ordering safe: with the ledger absent nothing is constructed, so a
        malformed `--input` rejected later can only ever touch a ledger that already existed.
        Zero `_input` calls is the ordering evidence.
        """
        absent = self.root / "absent-malformed.db"
        with mock.patch.object(
            cement_cli, "_input", wraps=cement_cli._input
        ) as input_, mock.patch.object(cement_cli, "System", autospec=True) as system:
            run = self.run_argv(
                [
                    "--db",
                    str(absent),
                    "--partition",
                    PARTITION,
                    "resolve",
                    OPERATION,
                    "--input",
                    "{",
                ]
            )
        self.assertEqual(run.status, 5)
        self.assertEqual(run.stdout, "")
        self.assertEqual(
            self.error(run)["message"], "ledger file is missing or unreadable"
        )
        self.assertEqual((input_.call_count, system.call_count), (0, 0))
        self.assertFalse(absent.exists())

    def test_v18_proposal_submit_grammar_sub_is_unrecognized_and_proposal_s(self) -> None:
        """V18 [D14] proposal submit grammar: --sub is unrecognized and `proposal sub` is an invalid choice

        ACTION: ENCODE

        EXPECTED:
        The action destinations are exactly `{operation, submission}`; full submission plus
        `--sub` yields `unrecognized arguments`, while `proposal sub` yields `argument
        proposal_command: invalid choice: 'sub' (choose from 'submit', 'show', 'list',
        'review')`.

        RULING:
        CONFIRMED as revised. The revision is correct and follows A1: `--sub` yields
        `unrecognized arguments` only when a full `--submission` is also supplied; `--sub`
        alone reports `the following arguments are required: --submission`. `proposal sub`
        yields `argument proposal_command: invalid choice: 'sub' (choose from 'submit', 'show',
        'list', 'review')`. Both are exit 2 with empty stdout.
        """
        node = self.parser_node("proposal", "submit")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(
            {action.dest for action in node._actions if action.dest != "help"},
            {"operation", "submission"},
        )
        probes = (
            (
                self.run_cli(
                    "proposal",
                    "submit",
                    OPERATION,
                    "--submission",
                    "{}",
                    "--sub",
                    "{}",
                ),
                "unrecognized arguments: --sub {}",
            ),
            (
                self.run_cli(
                    "proposal", "submit", OPERATION, "--sub", "{}"
                ),
                "the following arguments are required: --submission",
            ),
            (
                self.run_cli("proposal", "sub"),
                "argument proposal_command: invalid choice: 'sub' "
                "(choose from 'submit', 'show', 'list', 'review')",
            ),
        )
        for run, message in probes:
            with self.subTest(message=message):
                self.assertEqual(run.status, 2)
                self.assertEqual(run.stdout, "")
                self.assertEqual(self.error(run)["message"], message)

    def test_v19_submission_read_failure_oversize_and_invalid_utf_8_answer(self) -> None:
        """V19 [D15] --submission - read failure, oversize and invalid UTF-8 answer three distinct messages

        ACTION: ENCODE

        EXPECTED:
        One concrete reading is exit 2 with respectively `submission stdin could not be read`,
        `submission stdin exceeds 2162722 bytes`, and `submission stdin is not valid UTF-8`.

        RULING:
        CONFIRMED. The three shipped sentences are exactly `submission stdin could not be
        read`, `submission stdin exceeds 2162722 bytes` and `submission stdin is not valid
        UTF-8`. One warning for the battery: the TEXT-stream path says `exceeds 2162722
        characters`, so a probe that patches a text `sys.stdin` must expect the characters
        wording. Mirroring `_input`'s three families with submission-specific nouns is the
        whole of D15.
        """
        class FailingBytes(io.BytesIO):
            def read(self, size: int = -1) -> bytes:
                raise OSError("injected read failure")

        hosts = (
            (FailingBytes(), "submission stdin could not be read"),
            (
                io.BytesIO(b"x" * (SUBMISSION_MAX_BYTES + 1)),
                f"submission stdin exceeds {SUBMISSION_MAX_BYTES} bytes",
            ),
            (io.BytesIO(b"\xff"), "submission stdin is not valid UTF-8"),
        )
        observations: list[tuple[int, str, int]] = []
        for stream, expected in hosts:
            with self.subTest(message=expected), mock.patch.object(
                sys, "stdin", types.SimpleNamespace(buffer=stream)
            ), mock.patch.object(
                System, "submit_proposal", autospec=True
            ) as submit:
                run = self.run_cli(
                    "proposal", "submit", OPERATION, "--submission", "-"
                )
            observations.append(
                (run.status, str(self.error(run)["message"]), submit.call_count)
            )
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout, "")
            self.assertEqual(self.error(run)["message"], expected)
            self.assertEqual(submit.call_count, 0)
        self.assertEqual(
            observations,
            [
                (2, "submission stdin could not be read", 0),
                (2, f"submission stdin exceeds {SUBMISSION_MAX_BYTES} bytes", 0),
                (2, "submission stdin is not valid UTF-8", 0),
            ],
        )

    def test_v20_the_aggregate_cap_accepts_2162722_bytes_and_rejects_216272(self) -> None:
        """V20 [D16] the aggregate cap accepts 2162722 bytes and rejects 2162723

        ACTION: ENCODE

        EXPECTED:
        At 2162722 bytes `System.submit_proposal` is called exactly 1 time; at 2162723 bytes
        status is 2, call count is 0, and the message names `2162722 bytes`.

        RULING:
        CONFIRMED. The adjacent accept/reject pair at 2,162,722 and 2,162,723 is what proves
        the cap is APPLIED; X11 separately proves it is DERIVED. Neither claim implies the
        other.
        """
        input_json = '"' + "i" * (DEFAULT_MAX_BYTES - 2) + '"'
        provenance_json = (
            '{"p":"' + "p" * (PROVENANCE_MAX_BYTES - len(b'{"p":""}')) + '"}'
        )

        def frame(extra: int) -> bytes:
            output_json = '"' + "o" * (DEFAULT_MAX_BYTES - 2 + extra) + '"'
            return (
                '{"input":'
                + input_json
                + ',"output":'
                + output_json
                + ',"provenance":'
                + provenance_json
                + "}"
            ).encode("utf-8")

        sources = (frame(0), frame(1))
        self.assertEqual(
            tuple(map(len, sources)),
            (SUBMISSION_MAX_BYTES, SUBMISSION_MAX_BYTES + 1),
        )
        call_counts: list[int] = []
        for source in sources:
            with self.subTest(size=len(source)), mock.patch.object(
                sys,
                "stdin",
                types.SimpleNamespace(buffer=io.BytesIO(source)),
            ), mock.patch.object(
                System,
                "submit_proposal",
                autospec=True,
                return_value="prop_probe",
            ) as submit:
                run = self.run_cli(
                    "proposal", "submit", OPERATION, "--submission", "-"
                )
            call_counts.append(submit.call_count)
            if len(source) == SUBMISSION_MAX_BYTES:
                self.assertEqual(run.status, 0)
                self.assertEqual(submit.call_count, 1)
            else:
                self.assertEqual(run.status, 2)
                self.assertEqual(submit.call_count, 0)
                self.assertEqual(
                    self.error(run)["message"],
                    f"submission stdin exceeds {SUBMISSION_MAX_BYTES} bytes",
                )
        self.assertEqual(call_counts, [1, 0])

    def test_v21_a_duplicate_envelope_key_fails_inside_the_parser_before_an(self) -> None:
        """V21 [D17] a duplicate envelope key fails inside the parser, before any exact-key check

        ACTION: ENCODE

        EXPECTED:
        Status is 2 with exact message `duplicate JSON object key: 'input'`; post-parse
        key-check and `System.submit_proposal` call counts are both 0.

        RULING:
        CONFIRMED. `parse_json` is strict, so `{"input":1,"input":2}` fails inside the parser
        with `duplicate JSON object key: 'input'` before the exact-key check runs. That
        ordering is D17's reason for existing: a permissive parser would silently keep one of
        two values and the key check would see a well-formed envelope.
        """
        source = '{"input":1,"input":2,"output":3}'
        system = mock.Mock(spec=System)
        with mock.patch.object(
            cement_cli, "System", return_value=system
        ), mock.patch.object(
            cement_cli, "parse_json", wraps=cement_cli.parse_json
        ) as parser:
            run = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", source
            )
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout, "")
        self.assertEqual(
            self.error(run)["message"], "duplicate JSON object key: 'input'"
        )
        self.assertEqual(parser.call_count, 1)
        self.assertEqual(parser.call_args.args[0], source)
        self.assertEqual(system.submit_proposal.call_count, 0)

    def test_v22_unknown_keys_and_missing_keys_each_name_every_offending_ke(self) -> None:
        """V22 [D18] unknown keys and missing keys each name every offending key, sorted

        ACTION: ENCODE

        EXPECTED:
        The shipped wording exits 2 with `submission has unknown keys: a, z` and `submission is
        missing required keys: input, output`; `System.submit_proposal` call count is 0 for
        both.

        RULING:
        CONFIRMED as revised. The shipped sentences are `submission has unknown keys: a, z` and
        `submission is missing required keys: input, output` - the word `required` is present,
        and the pre-revision expectation would have gone red against correct code. Both lists
        are sorted and exhaustive, and `System.submit_proposal` is never called.
        """
        cases = (
            (
                json.dumps({"input": 1, "output": 2, "z": 3, "a": 4}),
                "submission has unknown keys: a, z",
            ),
            (
                json.dumps({"provenance": {}}),
                "submission is missing required keys: input, output",
            ),
        )
        system = mock.Mock(spec=System)
        observations: list[str] = []
        with mock.patch.object(cement_cli, "System", return_value=system):
            for source, expected in cases:
                with self.subTest(message=expected):
                    run = self.run_cli(
                        "proposal", "submit", OPERATION, "--submission", source
                    )
                    observations.append(str(self.error(run)["message"]))
                    self.assertEqual(run.status, 2)
                    self.assertEqual(run.stdout, "")
                    self.assertEqual(self.error(run)["message"], expected)
        self.assertEqual(
            observations,
            [
                "submission has unknown keys: a, z",
                "submission is missing required keys: input, output",
            ],
        )
        self.assertEqual(system.submit_proposal.call_count, 0)

    def test_v23_a_non_mapping_provenance_answers_the_library_s_own_message(self) -> None:
        """V23 [D19] a non-mapping provenance answers the library's own message at exit 2

        ACTION: ENCODE

        EXPECTED:
        The command exits 2 with exact message `candidate provenance must be a mapping`, writes
        no stdout, and leaves request, proposal, and event deltas all 0.

        RULING:
        CONFIRMED. Provenance shape stays library-graded: `candidate provenance must be a
        mapping` comes from `Candidate`, not the CLI, and the CLI adds no coercion. Zero
        request, proposal and event deltas prove the rejection precedes the write.
        """
        self.register()
        before = self.table_counts()
        source = json.dumps({"input": 1, "output": 2, "provenance": []})
        run = self.run_cli(
            "proposal", "submit", OPERATION, "--submission", source
        )
        after = self.table_counts()
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout, "")
        self.assertEqual(
            self.error(run)["message"], "candidate provenance must be a mapping"
        )
        self.assertEqual(
            {table: after[table] - before[table] for table in ("requests", "proposals", "events")},
            {"requests": 0, "proposals": 0, "events": 0},
        )

    def test_v24_success_emits_exactly_one_key_proposal_id_and_never_the_ba(self) -> None:
        """V24 [D20] success emits exactly one key, proposal_id, and never the bare returned string

        ACTION: ENCODE

        EXPECTED:
        Status is 0, stderr is empty, and decoded stdout equals exactly `{proposal_id:
        'prop_probe'}` with 1 key and no `status` key.

        RULING:
        CONFIRMED. Exactly one key. The bare string `submit_proposal` returns is not emitted
        directly because `_emit` would render it as a keyless JSON string, and the flags
        patch's `"status": "review_required"` stays REJECTED: every successful submission is
        pending by construction, so that key would advertise a variability the API does not
        have.
        """
        source = json.dumps({"input": 1, "output": 2, "provenance": {}})
        with mock.patch.object(
            System,
            "submit_proposal",
            autospec=True,
            return_value="prop_probe",
        ) as submit:
            run = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", source
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stderr, "")
        self.assertEqual(run.stdout_json, {"proposal_id": "prop_probe"})
        payload = self.payload(run)
        self.assertEqual(len(payload), 1)
        self.assertEqual(set(payload), {"proposal_id"})
        self.assertNotIn("status", payload)
        self.assertEqual(submit.call_count, 1)

    def test_v25_an_unregistered_operation_on_submit_is_3_and_writes_zero_r(self) -> None:
        """V25 [D22] an unregistered operation on submit is 3 and writes zero rows

        ACTION: ENCODE

        EXPECTED:
        Status is 3 with message `operation is not registered in this partition`; all 13
        application-table deltas, including requests, proposals, and events, are 0.

        RULING:
        CONFIRMED. Exit 3 with zero rows across all 13 application tables. Sweeping every table
        rather than the expected three is what turns this from a spot check into a footprint
        claim.
        """
        before = self.table_counts()
        self.assertEqual(len(before), 13)
        source = json.dumps({"input": 1, "output": 2, "provenance": {}})
        run = self.run_cli(
            "proposal", "submit", "absent", "--submission", source
        )
        after = self.table_counts()
        self.assertEqual(run.status, 3)
        self.assertEqual(run.stdout, "")
        self.assertEqual(
            self.error(run)["message"],
            "operation is not registered in this partition",
        )
        self.assertEqual(
            {table: after[table] - before[table] for table in before},
            {table: 0 for table in before},
        )

    def test_v26_two_byte_identical_submissions_return_two_ids_and_write_tw(self) -> None:
        """V26 [D23] two byte-identical submissions return two ids and write two of each row

        ACTION: ENCODE

        EXPECTED:
        The 2 stdout `proposal_id` values differ; cumulative deltas are exactly `{requests:2,
        proposals:2, events:2}` and 0 for every other application table.

        RULING:
        CONFIRMED. This is D23 stated as an observable rather than a warning: two
        byte-identical submissions, two distinct ids, exactly two of each of the three rows and
        zero elsewhere. There is no idempotency and the battery says so in deltas.
        """
        self.register()
        before = self.table_counts()
        source = json.dumps(
            {"input": {"same": 1}, "output": {"same": 2}, "provenance": {}}
        )
        runs = [
            self.run_cli(
                "proposal", "submit", OPERATION, "--submission", source
            )
            for _ in range(2)
        ]
        after = self.table_counts()
        identifiers = [str(self.payload(run)["proposal_id"]) for run in runs]
        self.assertEqual([run.status for run in runs], [0, 0])
        self.assertNotEqual(identifiers[0], identifiers[1])
        delta = {table: after[table] - before[table] for table in before}
        expected = {table: 0 for table in before}
        expected.update({"requests": 2, "proposals": 2, "events": 2})
        self.assertEqual(delta, expected)
        self.assertEqual(
            {table: change for table, change in delta.items() if change},
            {"requests": 2, "proposals": 2, "events": 2},
        )

    def test_v27_the_parser_census_moves_28_to_30_leaves_and_35_to_37_nodes(self) -> None:
        """V27 [D25] the parser census moves 28 to 30 leaves and 35 to 37 nodes, derived from _parser()

        ACTION: ENCODE

        EXPECTED:
        The derived census reports exactly 30 leaves and 37 nodes, and set subtraction against
        the 28-path baseline yields exactly `{'resolve', 'proposal submit'}`.

        RULING:
        CONFIRMED, re-derived by MAIN from `_parser()` at e6ba873: 30 leaves, 37 nodes, and the
        set difference against the 28-path baseline is exactly {'resolve', 'proposal submit'}.
        The census MOVING is the obligation landing, not a regression; deriving it inside the
        test rather than transcribing it is why the number can be trusted.
        """
        baseline_leaves, baseline_nodes = _parser_nodes(_baseline_parser())
        current_leaves, current_nodes = _parser_nodes(cement_cli._parser())
        baseline_paths = {" ".join(path) for path in baseline_leaves}
        current_paths = {" ".join(path) for path in current_leaves}
        self.assertEqual((len(baseline_paths), baseline_nodes), (28, 35))
        self.assertEqual((len(current_paths), current_nodes), (30, 37))
        self.assertEqual(
            current_paths - baseline_paths,
            {"resolve", "proposal submit"},
        )
        self.assertEqual(baseline_paths - current_paths, set())

    def test_v28_cross_leaf_option_isolation_holds_in_both_directions_for_b(self) -> None:
        """V28 [D26] cross-leaf option isolation holds in both directions for both new options

        ACTION: ENCODE

        EXPECTED:
        Both cross-new-leaf probes exit 2 with `unrecognized arguments`; across all 30 leaves
        `--submission` occurs 1 time and the expected-hash option occurs 4 times.

        RULING:
        CONFIRMED. Isolation in both directions is the point: `--submission` must not appear on
        any other leaf and `--expected-function-hash` must stay off `proposal submit`. The
        count of 4 for the expected-hash option covers its pre-existing homes plus resolve, so
        the battery derives it from the census rather than asserting a bare 1.
        """
        leaves, _ = _parser_nodes(cement_cli._parser())

        def owners(option: str) -> set[tuple[str, ...]]:
            return {
                path
                for path, parser in leaves.items()
                if any(option in action.option_strings for action in parser._actions)
            }

        submission_owners = owners("--submission")
        hash_owners = owners("--expected-function-hash")
        envelope = json.dumps({"input": 1, "output": 2})
        probes = (
            (
                self.run_cli(
                    "resolve",
                    OPERATION,
                    "--input",
                    "0",
                    "--submission",
                    envelope,
                ),
                "unrecognized arguments: --submission " + envelope,
            ),
            (
                self.run_cli(
                    "proposal",
                    "submit",
                    OPERATION,
                    "--submission",
                    envelope,
                    "--expected-function-hash",
                    "0" * 64,
                ),
                "unrecognized arguments: --expected-function-hash " + "0" * 64,
            ),
        )
        for run, message in probes:
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout, "")
            self.assertEqual(self.error(run)["message"], message)
        self.assertEqual(len(leaves), 30)
        self.assertEqual(submission_owners, {("proposal", "submit")})
        self.assertEqual(len(hash_owners), 4)
        self.assertIn(("resolve",), hash_owners)
        self.assertNotIn(("proposal", "submit"), hash_owners)

    def test_x01_cli_eager_json_parsing_cannot_preserve_the_library_owned_e(self) -> None:
        """X01 [D05] CLI eager JSON parsing cannot preserve the library-owned expected-hash-before-input precedence

        ACTION: ENCODE-SCOPED

        EXPECTED:
        Literal D05 requires exit 2 with `expected_function_hash must be a SHA-256 hex digest`;
        the straightforward `_input(args.input)` dispatch instead yields the invalid-JSON
        message first.

        RULING:
        CONFIRMED, and it forced amendment A2. Measured: `--input '{bad'
        --expected-function-hash bad` exits 2 with `invalid JSON: ...`, while `--input 1
        --expected-function-hash bad` exits 2 with `expected_function_hash must be a SHA-256
        hex digest`. A2 narrows D05 to the truth: the library owns precedence AMONG library
        validations, and CLI value-parsing necessarily precedes all of them because a value
        must exist before `System.resolve` can be called. Duplicating `_digest` in the CLI to
        restore the literal edge is REJECTED - it would put a second copy of a library
        validator on the surface D05 exists to keep thin.
        """
        self.register()
        malformed = self.run_cli(
            "resolve",
            OPERATION,
            "--input",
            "{bad",
            "--expected-function-hash",
            "bad",
        )
        valid_input = self.run_cli(
            "resolve",
            OPERATION,
            "--input",
            "1",
            "--expected-function-hash",
            "bad",
        )
        self.assertEqual((malformed.status, valid_input.status), (2, 2))
        self.assertEqual((malformed.stdout, valid_input.stdout), ("", ""))
        self.assertEqual(
            self.error(malformed)["message"],
            "invalid JSON: Expecting property name enclosed in double quotes: "
            "line 1 column 2 (char 1)",
        )
        self.assertEqual(
            self.error(valid_input)["message"],
            "expected_function_hash must be a SHA-256 hex digest",
        )

    def test_x02_the_stated_system_resolve_return_domain_does_not_close_the(self) -> None:
        """X02 [D09] the stated System.resolve return domain does not close the matched-null biconditional

        ACTION: ENCODE-SCOPED

        EXPECTED:
        Literal D09 forbids the pair `(true, true)` and requires `match is None` iff `passed is
        false`; baseline produces exactly the forbidden pair under a reachable override.

        RULING:
        SCOPED, and it forced the second half of amendment A4. The row is factually right:
        system.py:3835 returns `match=None` whenever `not verification.passed or document is
        None`, so a passing verification with no document yields payload `(passed:true,
        matched:null)`, which D09's literal biconditional forbids. A4 narrows D09's domain to
        values `System.resolve` computes THROUGH the shipped `verify_function`; the row's own
        route to the forbidden pair is an override of `verify_function`, which is not such a
        value. Normalizing it in the CLI is REJECTED on merits: mapping the pair to
        `matched:false` would launder an internal inconsistency into an ordinary miss, and
        `matched:null` at `passed:true` is precisely the signal that should stay visible.
        Encode the three reachable states as red; record the override behaviour as a probe.
        """
        system, hit_input = self.promoted_system()
        direct = system.resolve(PARTITION, OPERATION, hit_input)
        self.assertIsNotNone(direct.verification.function_hash)
        wrong = (
            "0" * 64
            if direct.verification.function_hash != "0" * 64
            else "1" * 64
        )
        cases = (
            (json.dumps(hit_input), (), (True, True)),
            (json.dumps({"query": 99}), (), (True, False)),
            (
                json.dumps(hit_input),
                ("--expected-function-hash", wrong),
                (False, None),
            ),
        )
        observations: list[tuple[object, object]] = []
        for input_text, extra, expected in cases:
            run = self.run_cli(
                "resolve", OPERATION, "--input", input_text, *extra
            )
            payload = self.payload(run)
            observation = (payload["passed"], payload["matched"])
            observations.append(observation)
            self.assertEqual(observation, expected)
        self.assertEqual(
            observations,
            [(True, True), (True, False), (False, None)],
        )

        passing_without_document = FunctionVerification(
            passed=True,
            entries=0,
            document=None,
            function_hash=None,
            checks=(),
        )
        with mock.patch.object(
            system,
            "verify_function",
            return_value=passing_without_document,
        ):
            override = system.resolve(PARTITION, OPERATION, 0)
        self.assertIs(override.verification, passing_without_document)
        self.assertTrue(override.verification.passed)
        self.assertIsNone(override.match)

    def test_x03_resolve_stdin_read_failure_and_invalid_utf_8_retain_the_tw(self) -> None:
        """X03 [D02] resolve stdin read failure and invalid UTF-8 retain the two non-size _input families

        ACTION: ENCODE

        EXPECTED:
        The 2 runs exit 2 with those exact messages, empty stdout, and `System.resolve` call
        count 0 in each run.

        RULING:
        CONFIRMED. `_input`'s two non-size families survive on the resolve path unchanged,
        which is D02's whole claim - resolve adds no reader, so it can add no failure family
        either.
        """
        class FailingBytes(io.BytesIO):
            def read(self, size: int = -1) -> bytes:
                raise OSError("injected read failure")

        cases = (
            (FailingBytes(), "JSON stdin could not be read"),
            (io.BytesIO(b"\xff"), "JSON stdin is not valid UTF-8"),
        )
        observations: list[tuple[int, str, int]] = []
        for stream, expected in cases:
            with self.subTest(message=expected), mock.patch.object(
                sys, "stdin", types.SimpleNamespace(buffer=stream)
            ), mock.patch.object(
                System, "resolve", autospec=True
            ) as resolve:
                run = self.run_cli("resolve", OPERATION, "--input", "-")
            observations.append(
                (run.status, str(self.error(run)["message"]), resolve.call_count)
            )
            self.assertEqual(run.status, 2)
            self.assertEqual(run.stdout, "")
            self.assertEqual(self.error(run)["message"], expected)
            self.assertEqual(resolve.call_count, 0)
        self.assertEqual(
            observations,
            [
                (2, "JSON stdin could not be read", 0),
                (2, "JSON stdin is not valid UTF-8", 0),
            ],
        )

    def test_x04_each_completed_resolve_dispatch_calls_system_resolve_once(self) -> None:
        """X04 [D03] each completed resolve dispatch calls System.resolve once and no neighboring library route

        ACTION: ENCODE

        EXPECTED:
        CLI counters are exactly `{System.resolve:1, System.propose:0,
        System.verify_function:0, _source:0}` for one completed invocation.

        RULING:
        CONFIRMED. Exactly one `System.resolve` call and zero on every neighbouring route.
        `verify_function` is in the counter set for a good reason: resolve calls it INTERNALLY,
        so a zero there proves the CLI reaches the library once at the composed entry point
        rather than assembling the operation itself.
        """
        system = mock.Mock(spec=System)
        system.resolve.return_value = _resolution("miss")
        with mock.patch.object(
            cement_cli, "System", return_value=system
        ), mock.patch.object(
            cement_cli, "_source", wraps=cement_cli._source
        ) as source:
            run = self.run_cli("resolve", OPERATION, "--input", "0")
        self.assertEqual(run.status, 6)
        self.assertEqual(
            {
                "System.resolve": system.resolve.call_count,
                "System.propose": system.propose.call_count,
                "System.verify_function": system.verify_function.call_count,
                "_source": source.call_count,
            },
            {
                "System.resolve": 1,
                "System.propose": 0,
                "System.verify_function": 0,
                "_source": 0,
            },
        )
        self.assertEqual(
            system.resolve.call_args,
            mock.call(PARTITION, OPERATION, 0, expected_function_hash=None),
        )

    def test_x05_an_absent_ledger_and_malformed_semantic_partition_expose_c(self) -> None:
        """X05 [D05, D13] an absent ledger and malformed semantic partition expose conflicting precedence obligations

        ACTION: ENCODE

        EXPECTED:
        D05 implies exit 2 with the quoted partition message, while D13 implies exit 5 with
        `ledger file is missing or unreadable`; the contract admits both first errors.

        RULING:
        CONFIRMED, and the two obligations do not actually conflict. Measured: absent ledger
        with partition `!` exits 5 with `ledger file is missing or unreadable` and creates no
        file; EXISTING ledger with partition `!` exits 2 with `partition must be 1-128 ASCII
        letters, digits, '.', '_', ':', '/', or '-'`. D13's precheck is upstream of
        construction and D05's shape check is downstream of it, so the first observable differs
        by ledger existence and neither reading needs `_name` duplicated in the CLI. Encode
        BOTH cells; the pair is the ruling.
        """
        absent = self.root / "absent-invalid-partition.db"
        absent_run = self.run_argv(
            [
                "--db",
                str(absent),
                "--partition",
                "!",
                "resolve",
                OPERATION,
                "--input",
                "0",
            ]
        )
        existing_run = self.run_argv(
            [
                "--db",
                str(self.database),
                "--partition",
                "!",
                "resolve",
                OPERATION,
                "--input",
                "0",
            ]
        )
        self.assertEqual((absent_run.status, existing_run.status), (5, 2))
        self.assertEqual(
            self.error(absent_run)["message"], "ledger file is missing or unreadable"
        )
        self.assertEqual(
            self.error(existing_run)["message"],
            "partition must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'",
        )
        self.assertFalse(absent.exists())

    def test_x06_one_read_transaction_per_invocation_is_unconditional_but_a(self) -> None:
        """X06 [D06] one read transaction per invocation is unconditional but argument rejection opens zero

        ACTION: ENCODE-SCOPED

        EXPECTED:
        The observable pair is `{valid:1, invalid:0}` under D05; literal D06 instead requires
        `{valid:1, invalid:1}`, so one reading must be narrowed.

        RULING:
        SCOPED, and it forced amendment A3. D06's `one transaction per invocation` was written
        without a reaching-ledger qualifier and is false for rejected invocations. A3 scopes it
        to invocations that reach the ledger. The ruled observable is the row's own `{valid:1,
        invalid:0}`, which is strictly more informative than the literal reading it replaces.
        """
        system = self.register()
        with mock.patch.object(
            cement_cli, "System", return_value=system
        ), mock.patch.object(
            system.store, "transaction", wraps=system.store.transaction
        ) as transaction:
            valid = self.run_cli("resolve", OPERATION, "--input", "0")
            valid_calls = transaction.call_count
            valid_arguments = list(transaction.call_args_list)
            transaction.reset_mock()
            invalid = self.run_argv(
                [
                    "--db",
                    str(self.database),
                    "--partition",
                    "!",
                    "resolve",
                    OPERATION,
                    "--input",
                    "0",
                ]
            )
            invalid_calls = transaction.call_count
        self.assertEqual((valid.status, invalid.status), (6, 2))
        self.assertEqual(
            {"valid": valid_calls, "invalid": invalid_calls},
            {"valid": 1, "invalid": 0},
        )
        self.assertEqual(valid_arguments, [mock.call(write=False)])

    def test_x07_entries_passed_and_diagnostic_function_hash_project_exactl(self) -> None:
        """X07 [D08] entries passed and diagnostic function_hash project exactly on a failed resolve verdict

        ACTION: ENCODE

        EXPECTED:
        The exit-6 payload has `passed:false`, `matched:null`, the direct integer `entries`,
        and the same 64-character `function_hash` as the direct verification.

        RULING:
        CONFIRMED. `function_hash` surviving a failed verdict as a diagnostic is the D08 clause
        most likely to be optimized away, because it is the one field a naive implementation
        would null out alongside the match. Comparing it to the direct verification's own
        digest is the right instrument.
        """
        system = self.register()
        actual = system.resolve(PARTITION, OPERATION, 0).verification.function_hash
        self.assertIsNotNone(actual)
        wrong = "0" * 64 if actual != "0" * 64 else "1" * 64
        direct = system.resolve(
            PARTITION,
            OPERATION,
            0,
            expected_function_hash=wrong,
        )
        run = self.run_cli(
            "resolve",
            OPERATION,
            "--input",
            "0",
            "--expected-function-hash",
            wrong,
        )
        payload = self.payload(run)
        self.assertEqual(run.status, 6)
        self.assertIs(payload["passed"], False)
        self.assertIsNone(payload["matched"])
        self.assertEqual(payload["entries"], direct.verification.entries)
        self.assertEqual(
            payload["function_hash"], direct.verification.function_hash
        )
        self.assertRegex(str(payload["function_hash"]), r"\A[0-9a-f]{64}\Z")

    def test_x08_resolve_retains_the_complete_shipped_exception_to_exit_map(self) -> None:
        """X08 [D12] resolve retains the complete shipped exception-to-exit map rather than only sampled states

        ACTION: ENCODE

        EXPECTED:
        The class-to-status map is exactly `{ValidationError:2, CementError:2, NotFoundError:3,
        ConflictError:4, StateError:4, IntegrityError:5}`.

        RULING:
        CONFIRMED, re-derived from `main`'s except ladder: `_UsageError` 2, `NotFoundError` 3,
        `(ConflictError, StateError)` 4, `IntegrityError` 5, `(ValidationError, CementError)`
        2, `_Unverified` 6. The map is correct BECAUSE of ladder order - the specific
        subclasses are caught ahead of the `CementError` base - so the battery must exercise
        real raises rather than reading a dict, which is what this row does.
        """
        cases = (
            (ValidationError("validation"), 2, "invalid"),
            (CementError("cement"), 2, "invalid"),
            (NotFoundError("not found"), 3, "not_found"),
            (ConflictError("conflict"), 4, "conflict"),
            (StateError("state"), 4, "conflict"),
            (IntegrityError("integrity"), 5, "integrity"),
        )
        observed: dict[str, int] = {}
        for error, status, error_key in cases:
            with self.subTest(error=type(error).__name__), mock.patch.object(
                System, "resolve", autospec=True, side_effect=error
            ) as resolve:
                run = self.run_cli("resolve", OPERATION, "--input", "0")
            observed[type(error).__name__] = run.status
            self.assertEqual(run.status, status)
            self.assertEqual(run.stdout, "")
            self.assertEqual(
                self.error(run),
                {"error": error_key, "message": str(error)},
            )
            self.assertEqual(resolve.call_count, 1)
        self.assertEqual(
            observed,
            {
                "ValidationError": 2,
                "CementError": 2,
                "NotFoundError": 3,
                "ConflictError": 4,
                "StateError": 4,
                "IntegrityError": 5,
            },
        )

    def test_x09_a_submission_value_beginning_with_at_sign_is_inline_json_a(self) -> None:
        """X09 [D-A, D15] a submission value beginning with at-sign is inline JSON and never a filesystem route

        ACTION: ENCODE

        EXPECTED:
        Status is 2 with that exact invalid-JSON message, `Path.open` call count is 0, and the
        named filesystem path remains untouched.

        RULING:
        CONFIRMED. Section 3.2 ruled D-A out, so an at-sign submission must be ordinary inline
        JSON that fails as invalid JSON. Zero `Path.open` calls plus an untouched named path is
        the evidence that no filesystem route was silently reintroduced; a message-only
        assertion would pass against a CLI that stats the path first.
        """
        missing = self.root / "submission-does-not-exist.json"
        source = "@" + str(missing)
        with mock.patch.object(
            Path, "open", autospec=True, side_effect=AssertionError("filesystem route used")
        ) as opened, mock.patch.object(
            System, "submit_proposal", autospec=True
        ) as submit:
            run = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", source
            )
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout, "")
        self.assertEqual(
            self.error(run)["message"],
            "invalid JSON: Expecting value: line 1 column 1 (char 0)",
        )
        self.assertEqual((opened.call_count, submit.call_count), (0, 0))
        self.assertFalse(missing.exists())

    def test_x10_aggregate_stdin_is_consumed_exactly_once_so_the_drained_se(self) -> None:
        """X10 [D15] aggregate stdin is consumed exactly once so the drained-second-read defect cannot recur

        ACTION: ENCODE

        EXPECTED:
        The command exits 0, returns exactly 1 `proposal_id`, and the stream records exactly 1
        call requesting at most 2162723 bytes.

        RULING:
        CONFIRMED, and it pins the defect that killed the per-field alternative. A second `-`
        read finds a drained stream, so any design needing two stdin reads truncates one field
        silently. Asserting exactly one read requesting at most `cap + 1` bytes proves both the
        single-read property and the bounded-read property in one instrument.
        """
        envelope = json.dumps({"input": 1, "output": 2, "provenance": {}}).encode()

        class ReadOnce(io.BytesIO):
            def __init__(self, payload: bytes) -> None:
                super().__init__(payload)
                self.requests: list[int] = []

            def read(self, size: int = -1) -> bytes:
                self.requests.append(size)
                if len(self.requests) > 1:
                    raise AssertionError("submission stdin was consumed twice")
                return super().read(size)

        stream = ReadOnce(envelope)
        with mock.patch.object(
            sys, "stdin", types.SimpleNamespace(buffer=stream)
        ), mock.patch.object(
            System,
            "submit_proposal",
            autospec=True,
            return_value="prop_probe",
        ) as submit:
            run = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", "-"
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(run.stdout_json, {"proposal_id": "prop_probe"})
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(len(stream.requests), 1)
        self.assertGreater(stream.requests[0], 0)
        self.assertLessEqual(stream.requests[0], SUBMISSION_MAX_BYTES + 1)

    def test_x11_the_aggregate_transport_cap_is_derived_from_one_exported_p(self) -> None:
        """X11 [D16] the aggregate transport cap is derived from one exported provenance constant with no copied limit

        ACTION: ENCODE-SCOPED

        EXPECTED:
        `PROVENANCE_MAX_BYTES == 65536`, framing is 34, and `2*1048576+65536+34 == 2162722`;
        CLI retains exactly 1 unrelated 65536 literal in `_source`, adds 0 provenance copies,
        and all 3 system sites reference the constant.

        RULING:
        CONFIRMED as revised, and the revision is one MAIN supplied after measuring. `cli.py`
        retains exactly one `65_536` literal, at line 370, bounding `--source-command`; it is
        unrelated to provenance and shares the value by coincidence. The pre-revision `0
        numeric 65536 literals` claim would have gone red against correct code. The ruled
        obligation is that the SUBMISSION path copies no limit: `SUBMISSION_MAX_BYTES` is `2 *
        DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + _SUBMISSION_FRAMING`, framing is computed
        from `_SUBMISSION_KEYS` at 34, and all three system.py provenance sites reference the
        exported constant. Retiring the coincidental literal is DEFERRED to polish.
        """
        self.assertTrue(hasattr(system_module, "PROVENANCE_MAX_BYTES"))
        self.assertTrue(hasattr(cement_cli, "SUBMISSION_MAX_BYTES"))
        self.assertTrue(hasattr(cement_cli, "_SUBMISSION_KEYS"))
        self.assertTrue(hasattr(cement_cli, "_SUBMISSION_FRAMING"))
        provenance_limit = system_module.PROVENANCE_MAX_BYTES
        keys = tuple(cement_cli._SUBMISSION_KEYS)
        framing = 2 + sum(len(json.dumps(key)) + 1 for key in keys) + len(keys) - 1
        self.assertEqual(provenance_limit, 65_536)
        self.assertEqual(framing, 34)
        self.assertEqual(cement_cli._SUBMISSION_FRAMING, framing)
        self.assertEqual(
            cement_cli.SUBMISSION_MAX_BYTES,
            2 * DEFAULT_MAX_BYTES + provenance_limit + framing,
        )
        self.assertEqual(cement_cli.SUBMISSION_MAX_BYTES, 2_162_722)

        cli_source = Path(inspect.getsourcefile(cement_cli) or "").read_text()
        system_source = Path(inspect.getsourcefile(System) or "").read_text()
        cli_tree = ast.parse(cli_source)
        system_tree = ast.parse(system_source)
        cli_literals = [
            node
            for node in ast.walk(cli_tree)
            if isinstance(node, ast.Constant)
            and type(node.value) is int
            and node.value == 65_536
        ]
        source_helper = next(
            node
            for node in ast.walk(cli_tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_source"
        )
        helper_literals = {
            node.lineno
            for node in ast.walk(source_helper)
            if isinstance(node, ast.Constant) and node.value == 65_536
        }
        self.assertEqual(len(cli_literals), 1)
        self.assertEqual({node.lineno for node in cli_literals}, helper_literals)

        cap_assignment = next(
            node
            for node in ast.walk(cli_tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            and any(
                isinstance(target, ast.Name) and target.id == "SUBMISSION_MAX_BYTES"
                for target in (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
            )
        )
        cap_names = {
            node.id for node in ast.walk(cap_assignment) if isinstance(node, ast.Name)
        }
        self.assertTrue(
            {"DEFAULT_MAX_BYTES", "PROVENANCE_MAX_BYTES", "_SUBMISSION_FRAMING"}
            <= cap_names
        )
        system_uses = sum(
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id == "PROVENANCE_MAX_BYTES"
            for node in ast.walk(system_tree)
        )
        self.assertEqual(system_uses, 3)

    def test_x12_top_level_non_object_submission_rejection_has_no_contract(self) -> None:
        """X12 [D17] top-level non-object submission rejection has no contract-selected exact sentence

        ACTION: ENCODE

        EXPECTED:
        One concrete reading makes all 4 cases exit 2 with `submission must be a JSON object`,
        zero key-check calls, and zero library calls.

        RULING:
        CONFIRMED. The shipped sentence is `submission must be a JSON object` for every
        non-object top level, verified by MAIN against `[]`. D17 quoted no wording, so this
        ruling supplies it; `type(parsed) is not dict` is the shipped test, which correctly
        rejects a list, a scalar and null alike.
        """
        system = mock.Mock(spec=System)
        observations: list[tuple[str, int, str]] = []
        with mock.patch.object(cement_cli, "System", return_value=system):
            for source in ("null", "[]", "0", '"text"'):
                with self.subTest(source=source):
                    run = self.run_cli(
                        "proposal", "submit", OPERATION, "--submission", source
                    )
                    message = str(self.error(run)["message"])
                    observations.append((source, run.status, message))
                    self.assertEqual(run.status, 2)
                    self.assertEqual(run.stdout, "")
                    self.assertEqual(message, "submission must be a JSON object")
        self.assertEqual(len(observations), 4)
        self.assertEqual(
            {message for _, _, message in observations},
            {"submission must be a JSON object"},
        )
        self.assertEqual(system.submit_proposal.call_count, 0)

    def test_x13_aggregate_depth_and_item_maxima_are_adjacent_accept_reject(self) -> None:
        """X13 [D17] aggregate depth and item maxima are adjacent accept-reject boundaries rather than named constants only

        ACTION: ENCODE

        EXPECTED:
        Depth 65 and 300003 items each reach dispatch once; depth 66 and 300004 items exit 2
        with respectively `JSON exceeds maximum depth 65` and `JSON exceeds maximum container
        item count`.

        RULING:
        CONFIRMED, re-derived from the shipped call: `max_depth=DEFAULT_MAX_DEPTH + 1` = 65 and
        `max_items=3 * DEFAULT_MAX_ITEMS + 3` = 300003, against library constants 64 and
        100000. The envelope nests each field one level deeper and adds three members, so those
        are the only values that let a submission the library accepts survive the transport.
        The adjacent reject at 66 and 300004 is what proves the derived maxima are applied
        rather than merely named.
        """
        max_depth = DEFAULT_MAX_DEPTH + 1
        max_items = 3 * DEFAULT_MAX_ITEMS + 3
        depth_at = (
            '{"input":'
            + "[" * DEFAULT_MAX_DEPTH
            + "0"
            + "]" * DEFAULT_MAX_DEPTH
            + ',"output":0}'
        )
        depth_over = (
            '{"input":'
            + "[" * (DEFAULT_MAX_DEPTH + 1)
            + "0"
            + "]" * (DEFAULT_MAX_DEPTH + 1)
            + ',"output":0}'
        )
        field_array = "[" + ",".join("0" for _ in range(DEFAULT_MAX_ITEMS)) + "]"

        def item_frame(provenance_items: int) -> str:
            provenance = "[" + ",".join("0" for _ in range(provenance_items)) + "]"
            return (
                '{"input":'
                + field_array
                + ',"output":'
                + field_array
                + ',"provenance":{"p":'
                + provenance
                + "}}"
            )

        item_at = item_frame(DEFAULT_MAX_ITEMS - 1)
        item_over = item_frame(DEFAULT_MAX_ITEMS)
        self.assertEqual((max_depth, max_items), (65, 300_003))
        cases = (
            ("depth-at", depth_at, 1, 0, None),
            (
                "depth-over",
                depth_over,
                0,
                2,
                f"JSON exceeds maximum depth {max_depth}",
            ),
            ("items-at", item_at, 1, 0, None),
            (
                "items-over",
                item_over,
                0,
                2,
                "JSON exceeds maximum container item count",
            ),
        )
        calls: list[int] = []
        for label, source, expected_calls, status, message in cases:
            with self.subTest(case=label), mock.patch.object(
                System,
                "submit_proposal",
                autospec=True,
                return_value="prop_probe",
            ) as submit:
                run = self.run_cli(
                    "proposal", "submit", OPERATION, "--submission", source
                )
            calls.append(submit.call_count)
            self.assertEqual(submit.call_count, expected_calls)
            self.assertEqual(run.status, status)
            if message is not None:
                self.assertEqual(self.error(run)["message"], message)
        self.assertEqual(calls, [1, 0, 1, 0])

    def test_x14_unknown_key_rejection_precedes_missing_key_rejection_when(self) -> None:
        """X14 [D17, D18] unknown-key rejection precedes missing-key rejection when one envelope violates both

        ACTION: ENCODE

        EXPECTED:
        Status is 2 with `submission has unknown keys: a, z`; the message contains neither
        `input` nor `output`, and `System.submit_proposal` has 0 calls.

        RULING:
        CONFIRMED. Unknown precedes missing in the shipped order, and asserting the message
        contains NEITHER required key name is the discriminating half - a validator that
        reported both violations together would pass a weaker containment test.
        """
        source = json.dumps({"z": 1, "a": 2})
        system = mock.Mock(spec=System)
        with mock.patch.object(cement_cli, "System", return_value=system):
            run = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", source
            )
        message = str(self.error(run)["message"])
        self.assertEqual(run.status, 2)
        self.assertEqual(run.stdout, "")
        self.assertEqual(message, "submission has unknown keys: a, z")
        self.assertNotIn("input", message)
        self.assertNotIn("output", message)
        self.assertEqual(system.submit_proposal.call_count, 0)

    def test_x15_omitted_provenance_creates_a_fresh_empty_mapping_and_persi(self) -> None:
        """X15 [D18] omitted provenance creates a fresh empty mapping and persists canonical empty-object bytes

        ACTION: ENCODE

        EXPECTED:
        Both candidates have provenance equal to `{}` but distinct object identities, and both
        stored `provenance_json` values equal the 2-byte string `{}`.

        RULING:
        CONFIRMED. Distinct object identity is the load-bearing clause: a module-level `{}`
        default shared across calls would satisfy an equality-only test and still let one
        submission mutate another's provenance. The 2-byte stored `{}` proves the default is
        durable rather than merely present in memory.
        """
        self.register()
        captured: list[Candidate] = []
        submit = System.submit_proposal

        def observe(
            instance: System,
            partition: str,
            operation: str,
            input_value: object,
            *,
            candidate: Candidate,
        ) -> str:
            captured.append(candidate)
            return submit(
                instance,
                partition,
                operation,
                input_value,
                candidate=candidate,
            )

        sources = (
            json.dumps({"input": {"n": 1}, "output": {"n": 2}}),
            json.dumps({"input": {"n": 3}, "output": {"n": 4}}),
        )
        with mock.patch.object(System, "submit_proposal", new=observe):
            runs = [
                self.run_cli(
                    "proposal", "submit", OPERATION, "--submission", source
                )
                for source in sources
            ]
        self.assertEqual([run.status for run in runs], [0, 0])
        self.assertEqual(len(captured), 2)
        self.assertEqual([candidate.provenance for candidate in captured], [{}, {}])
        self.assertIsNot(captured[0].provenance, captured[1].provenance)
        with closing(sqlite3.connect(self.database)) as connection:
            stored = [
                str(row[0])
                for row in connection.execute(
                    "SELECT provenance_json FROM proposals ORDER BY created_at_us, id"
                )
            ]
        self.assertEqual(stored, ["{}", "{}"])
        self.assertEqual([len(value.encode()) for value in stored], [2, 2])

    def test_x16_unknown_and_missing_envelope_failures_open_no_submission_t(self) -> None:
        """X16 [D18] unknown and missing envelope failures open no submission transaction after required System construction

        ACTION: ENCODE-SCOPED

        EXPECTED:
        Each invalid envelope exits 2 with `System.__init__` count 1, `sqlite3.connect` count
        at least 1, `Store.transaction` count 0, `System.submit_proposal` count 0, and the
        ledger path present afterward.

        RULING:
        CONFIRMED as revised, and the revision is the honest boundary that forced amendment A5.
        Measured on all four envelope failures: `System.__init__` 1, `sqlite3.connect` >= 1,
        `Store.transaction` 0, `System.submit_proposal` 0, ledger present afterwards at ~208
        KiB. D18's `before any transaction opens` is therefore TRUE as written at the
        `Store.transaction` seam and is retained; A5 adds the clause D18 was missing -
        construction precedes envelope validation, so a writing leaf creates its ledger before
        rejecting a malformed envelope. Giving submit a D13-style precheck is REJECTED:
        creating the ledger is a legitimate first use of a writing leaf. The residual - an
        invalid argument value creating the ledger on any writing leaf - is CLI-wide and
        pre-existing, and is DEFERRED to polish.
        """
        cases = (
            json.dumps({"input": 1, "output": 2, "z": 3}),
            json.dumps({"provenance": {}}),
        )
        observations: list[tuple[int, int, int, int, bool]] = []
        real_init = System.__init__
        real_transaction = Store.transaction
        real_connect = sqlite3.connect
        for index, source in enumerate(cases):
            path = self.root / f"invalid-envelope-{index}.db"
            init_calls = 0
            transaction_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

            def initialize(instance: System, *args: object, **kwargs: object) -> None:
                nonlocal init_calls
                init_calls += 1
                real_init(instance, *args, **kwargs)

            def transaction(
                instance: Store, *args: object, **kwargs: object
            ) -> object:
                transaction_calls.append((args, kwargs))
                return real_transaction(instance, *args, **kwargs)

            with mock.patch.object(
                System, "__init__", new=initialize
            ), mock.patch.object(
                Store, "transaction", new=transaction
            ), mock.patch.object(
                sqlite3, "connect", wraps=real_connect
            ) as connect, mock.patch.object(
                System, "submit_proposal", autospec=True
            ) as submit:
                run = self.run_argv(
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
            observations.append(
                (
                    init_calls,
                    connect.call_count,
                    len(transaction_calls),
                    submit.call_count,
                    path.exists(),
                )
            )
            self.assertEqual(run.status, 2)
            self.assertEqual(init_calls, 1)
            self.assertGreaterEqual(connect.call_count, 1)
            self.assertEqual(len(transaction_calls), 0)
            self.assertEqual(submit.call_count, 0)
            self.assertTrue(path.exists())
        self.assertEqual(len(observations), 2)
        self.assertTrue(
            all(
                init == 1 and connects >= 1 and transactions == 0 and submits == 0 and exists
                for init, connects, transactions, submits, exists in observations
            )
        )

    def test_x17_submission_envelope_fields_map_to_the_exact_submit_proposa(self) -> None:
        """X17 [D19] submission envelope fields map to the exact submit_proposal positional and Candidate channels

        ACTION: ENCODE

        EXPECTED:
        The call count is 1; positional args equal `('tenant','op',{'in':1})`, and candidate
        fields equal `output={'out':2}` plus `provenance={'prov':3}`.

        RULING:
        CONFIRMED. This is D19 as a wiring assertion: the envelope's `input` is the library's
        third POSITIONAL while `output` and `provenance` travel inside `Candidate`. Checking
        positional args and candidate fields separately is what would catch a transposition
        that a round-trip test would not.
        """
        source = json.dumps(
            {
                "input": {"in": 1},
                "output": {"out": 2},
                "provenance": {"prov": 3},
            }
        )
        system = mock.Mock(spec=System)
        system.submit_proposal.return_value = "prop_probe"
        with mock.patch.object(cement_cli, "System", return_value=system):
            run = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", source
            )
        self.assertEqual(run.status, 0)
        self.assertEqual(system.submit_proposal.call_count, 1)
        self.assertEqual(
            system.submit_proposal.call_args.args,
            (PARTITION, OPERATION, {"in": 1}),
        )
        candidate = system.submit_proposal.call_args.kwargs["candidate"]
        self.assertIs(type(candidate), Candidate)
        self.assertEqual(candidate.output, {"out": 2})
        self.assertEqual(candidate.provenance, {"prov": 3})

    def test_x18_submission_acknowledgement_and_proposal_created_event_disc(self) -> None:
        """X18 [D21] submission acknowledgement and proposal.created event disclose no candidate or request bytes

        ACTION: ENCODE

        EXPECTED:
        Stdout has exactly 1 key and 0 secret occurrences; the event has kind
        `proposal.created`, payload `{}`, and 0 occurrences of input, output, provenance, or
        request ID.

        RULING:
        CONFIRMED. The acknowledgement carries no request identity and `proposal.created` keeps
        payload `{}` on this route. Counting occurrences of the input, output and provenance
        bytes across BOTH surfaces is the disclosure claim; one key on stdout alone would not
        cover the event.
        """
        self.register()
        secrets = (
            "INPUT_SECRET_X18",
            "OUTPUT_SECRET_X18",
            "PROVENANCE_SECRET_X18",
        )
        source = json.dumps(
            {
                "input": {"value": secrets[0]},
                "output": {"value": secrets[1]},
                "provenance": {"value": secrets[2]},
            }
        )
        run = self.run_cli(
            "proposal", "submit", OPERATION, "--submission", source
        )
        payload = self.payload(run)
        self.assertEqual(run.status, 0)
        self.assertEqual(set(payload), {"proposal_id"})
        proposal_id = str(payload["proposal_id"])
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute(
                "SELECT e.kind, e.subject_id, e.payload_json, p.request_id "
                "FROM events AS e JOIN proposals AS p ON p.id = e.subject_id "
                "WHERE e.kind = 'proposal.created' ORDER BY e.sequence DESC LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        kind, subject_id, event_payload, request_id = map(str, row)
        self.assertEqual((kind, subject_id, event_payload), ("proposal.created", proposal_id, "{}"))
        combined = run.stdout + event_payload
        self.assertEqual([combined.count(secret) for secret in secrets], [0, 0, 0])
        self.assertNotIn(request_id, combined)
        self.assertEqual(json.loads(event_payload), {})

    def test_x19_proposal_submit_preserves_every_parser_library_conflict_an(self) -> None:
        """X19 [D22] proposal submit preserves every parser library conflict and integrity exit class

        ACTION: ENCODE

        EXPECTED:
        Observed statuses are exactly `{parser:2, field:2, not_found:3, conflict:4, state:4,
        integrity:5}`, each with empty stdout and one JSON stderr object.

        RULING:
        CONFIRMED. Six classes, each with empty stdout and exactly one JSON stderr object. The
        empty-stdout half matters as much as the status: a leaf that printed a partial payload
        before failing would still exit correctly. Encoding note: one object is NOT one line.
        cli.py emits every envelope as `json.dumps(value, ensure_ascii=False, sort_keys=True,
        indent=2) + "\n"`, unchanged since c8b82cd, so the stderr of a single-object failure
        holds 4 newlines. Assert the exact round-trip of that framing, never a newline count.
        """
        self.register()
        runs: dict[str, _Run] = {
            "parser": self.run_cli(
                "proposal", "submit", OPERATION, "--submission", "[]"
            ),
            "field": self.run_cli(
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                json.dumps({"input": 1, "output": 2, "provenance": []}),
            ),
        }
        envelope = json.dumps({"input": 1, "output": 2, "provenance": {}})
        injected = (
            ("not_found", NotFoundError("not found")),
            ("conflict", ConflictError("conflict")),
            ("state", StateError("state")),
            ("integrity", IntegrityError("integrity")),
        )
        for label, error in injected:
            with mock.patch.object(
                System, "submit_proposal", autospec=True, side_effect=error
            ):
                runs[label] = self.run_cli(
                    "proposal", "submit", OPERATION, "--submission", envelope
                )
        observed = {label: run.status for label, run in runs.items()}
        self.assertEqual(
            observed,
            {
                "parser": 2,
                "field": 2,
                "not_found": 3,
                "conflict": 4,
                "state": 4,
                "integrity": 5,
            },
        )
        for label, run in runs.items():
            with self.subTest(case=label):
                self.assertEqual(run.stdout, "")
                self.assertIsInstance(run.stderr_json, dict)
                # One object, not one line: the shipped envelope is indented, so
                # round-tripping the exact framing is what rejects a second object
                # or any trailing byte.
                self.assertEqual(
                    run.stderr,
                    json.dumps(
                        run.stderr_json,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                    + "\n",
                )

    def test_x20_new_command_help_and_publication_prohibit_retry_advice_and(self) -> None:
        """X20 [D23] new command help and publication prohibit retry advice and name pending enumeration recovery

        ACTION: ENCODE-SCOPED

        EXPECTED:
        Positive retry-advice matches total 0; at least 1 paragraph says submission is not
        idempotent, and at least 1 block contains `cement proposal list` as recovery.

        RULING:
        CONFIRMED with one scoping the battery must honour. The retry prohibition is D23's and
        it covers sentences about `resolve` and `proposal submit`; README's request-outcomes
        table legitimately advises `retry handle with --retry-failed` for the HANDLE route, so
        a document-wide `retry` count would go red against correct prose. Shipped text carries
        `Cement gives no idempotency here`, `Do not retry a failed submission` and a `proposal
        list --status pending` recovery block.
        """
        resolve = self.parser_node("resolve")
        submit = self.parser_node("proposal", "submit")
        self.assertIsNotNone(resolve)
        self.assertIsNotNone(submit)
        assert resolve is not None and submit is not None
        paths = (
            ROOT / "README.md",
            ROOT / "docs/architecture.md",
            ROOT / "docs/threat-model.md",
        )
        paragraphs: list[str] = []
        complete = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            complete.append(text)
            for paragraph in text.split("\n\n"):
                lowered = " ".join(paragraph.lower().split())
                if (
                    "proposal submit" in lowered
                    or "cement resolve" in lowered
                    or "`resolve`" in lowered
                    or "one resolve" in lowered
                ):
                    paragraphs.append(lowered)
        scoped = paragraphs + [resolve.format_help().lower(), submit.format_help().lower()]
        positive_retry: list[str] = []
        for surface in scoped:
            for sentence in re.split(r"(?<=[.!?])\s+", surface):
                if not re.search(r"\b(?:retry|rerun|repeat)\b", sentence):
                    continue
                if any(
                    phrase in sentence
                    for phrase in (
                        "do not retry",
                        "not retry",
                        "never retry",
                        "no retry",
                        "must not retry",
                        "cannot retry",
                    )
                ):
                    continue
                if re.search(
                    r"(?:\b(?:can|may|should|must)\s+retry\b|^retry\b|\btry again\b)",
                    sentence,
                ):
                    positive_retry.append(sentence)
        publication = "\n".join(complete).lower()
        self.assertEqual(positive_retry, [])
        self.assertTrue(
            any(
                "not idempotent" in paragraph or "no idempotency" in paragraph
                for paragraph in paragraphs
            )
        )
        self.assertRegex(
            publication,
            r"cement[^\n]*proposal list[^\n]*--status pending",
        )

    def test_x21_both_new_parser_nodes_omit_every_source_option_as_well_as(self) -> None:
        """X21 [D24] both new parser nodes omit every source option as well as avoiding source calls dynamically

        ACTION: ENCODE

        EXPECTED:
        New-node intersections with `{source_command, source_id, source_timeout}` are empty,
        and dynamic counters are exactly `{_source:0, System.propose:0, source.propose:0}`.

        RULING:
        CONFIRMED. Static and dynamic evidence for one claim: the new nodes carry no source
        OPTION, and the new dispatches make no source CALL. Either alone is defeatable - an
        option-free node could still reach a configured source, and a zero call count could
        reflect an unconfigured source - so D24 needs both.
        """
        source_options = {"source_command", "source_id", "source_timeout"}
        resolve_node = self.parser_node("resolve")
        submit_node = self.parser_node("proposal", "submit")
        self.assertIsNotNone(resolve_node)
        self.assertIsNotNone(submit_node)
        assert resolve_node is not None and submit_node is not None
        for node in (resolve_node, submit_node):
            self.assertEqual(
                {action.dest for action in node._actions} & source_options,
                set(),
            )

        source = _Source()
        system = System(self.database, candidate_source=source)
        system.register_operation(PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0))
        envelope = json.dumps({"input": 1, "output": 2, "provenance": {}})
        with mock.patch.object(
            cement_cli, "System", return_value=system
        ), mock.patch.object(
            cement_cli, "_source", wraps=cement_cli._source
        ) as source_builder, mock.patch.object(
            system, "propose", wraps=system.propose
        ) as propose:
            resolved = self.run_cli("resolve", OPERATION, "--input", "0")
            submitted = self.run_cli(
                "proposal", "submit", OPERATION, "--submission", envelope
            )
        self.assertIn(resolved.status, (0, 6))
        self.assertEqual(submitted.status, 0)
        self.assertEqual(
            {
                "_source": source_builder.call_count,
                "System.propose": propose.call_count,
                "source.propose": len(source.calls),
            },
            {"_source": 0, "System.propose": 0, "source.propose": 0},
        )

    def test_x22_all_twenty_eight_baseline_leaf_paths_survive_by_identity_r(self) -> None:
        """X22 [D25] all twenty-eight baseline leaf paths survive by identity rather than only by equal count

        ACTION: ENCODE

        EXPECTED:
        `baseline_paths - current_paths == set()` and `current_paths - baseline_paths ==
        {'resolve','proposal submit'}` with cardinalities 28 and 30.

        RULING:
        CONFIRMED. Identity, not cardinality, is the obligation: two set subtractions in both
        directions catch a rename that leaves the count at 30. This is the assertion V27's
        count cannot make.
        """
        baseline, _ = _parser_nodes(_baseline_parser())
        current, _ = _parser_nodes(cement_cli._parser())
        baseline_paths = {" ".join(path) for path in baseline}
        current_paths = {" ".join(path) for path in current}
        self.assertEqual(len(baseline_paths), 28)
        self.assertEqual(len(current_paths), 30)
        self.assertEqual(baseline_paths - current_paths, set())
        self.assertEqual(
            current_paths - baseline_paths,
            {"resolve", "proposal submit"},
        )

    def test_x23_root_and_nested_legacy_option_abbreviations_remain_accepte(self) -> None:
        """X23 [D25] root and nested legacy option abbreviations remain accepted while new-node abbreviations fail

        ACTION: ENCODE

        EXPECTED:
        The 3 legacy probes parse successfully with values `p`, `x`, and `0`; every resolve
        `--in/--inp/--exp` and submit `--sub` probe exits 2.

        RULING:
        CONFIRMED. The new nodes set `allow_abbrev=False` and no other node changed, so legacy
        abbreviation must still work while the new leaves reject it. Verified by MAIN that all
        four new-node prefix probes exit 2. Asserting only the new-node failures would let a
        global `allow_abbrev=False` regression pass.
        """
        parser = cement_cli._parser()
        root = parser.parse_args(["--part", "p", "operation", "list"])
        nested = parser.parse_args(
            ["function", "eval", "--bun", "x", "--in", "0"]
        )
        self.assertEqual(
            (root.partition, nested.bundle, nested.input),
            ("p", "x", "0"),
        )
        envelope = json.dumps({"input": 1, "output": 2})
        probes = (
            self.run_cli(
                "resolve", OPERATION, "--input", "0", "--in", "1"
            ),
            self.run_cli(
                "resolve", OPERATION, "--input", "0", "--inp", "1"
            ),
            self.run_cli(
                "resolve", OPERATION, "--input", "0", "--exp", "x"
            ),
            self.run_cli(
                "proposal",
                "submit",
                OPERATION,
                "--submission",
                envelope,
                "--sub",
                envelope,
            ),
        )
        self.assertEqual([run.status for run in probes], [2, 2, 2, 2])
        for run in probes:
            self.assertEqual(run.stdout, "")
            self.assertIn("unrecognized arguments", self.error(run)["message"])

    def test_x24_store_py_remains_byte_identical_to_the_unit_baseline_and_s(self) -> None:
        """X24 [D26] store.py remains byte-identical to the unit baseline and schema stays exactly version two

        ACTION: ENCODE

        EXPECTED:
        Byte comparison returns 0, length remains 27951, SHA-256 remains the quoted 64-hex
        digest, and `SCHEMA_VERSION` equals 2.

        RULING:
        CONFIRMED, re-derived by MAIN from the primary tree: `store.py` is 27,951 bytes, sha256
        2b2650144d4b384af4d8bfe67e1f9de0e186b609f3bb2632e2f81b53536770f7, `SCHEMA_VERSION` 2.
        Byte comparison plus length plus digest is deliberately redundant, because each one
        alone has a failure mode the others do not.
        """
        path = Path(inspect.getsourcefile(Store) or "")
        current = path.read_bytes()
        baseline = subprocess.check_output(
            (
                "git",
                "-C",
                str(ROOT),
                "show",
                "c8b82cd:src/cement_runtime/store.py",
            )
        )
        baseline_path = self.root / "store-baseline.py"
        baseline_path.write_bytes(baseline)
        compared = subprocess.run(
            ("cmp", "-s", str(path), str(baseline_path)),
            check=False,
        )
        self.assertEqual(compared.returncode, 0)
        self.assertEqual(current, baseline)
        self.assertEqual(len(current), 27_951)
        self.assertEqual(
            hashlib.sha256(current).hexdigest(),
            "2b2650144d4b384af4d8bfe67e1f9de0e186b609f3bb2632e2f81b53536770f7",
        )
        self.assertEqual(SCHEMA_VERSION, 2)

    def test_x25_one_successful_cli_submission_preserves_the_direct_library(self) -> None:
        """X25 [D26] one successful CLI submission preserves the direct library three-row footprint over all tables

        ACTION: ENCODE

        EXPECTED:
        The complete nonzero delta map is exactly `{requests:1, proposals:1, events:1}` across
        13 derived application tables.

        RULING:
        CONFIRMED, and the complete-map form is what makes it a footprint claim. 13 application
        tables derived from `store.SCHEMA`; the nonzero delta map is exactly `{requests:1,
        proposals:1, events:1}`. Deriving the table list rather than transcribing it means a
        future table joins the sweep automatically.
        """
        self.register()
        before = self.table_counts()
        self.assertEqual(len(before), 13)
        source = json.dumps(
            {"input": {"value": 1}, "output": {"value": 2}, "provenance": {}}
        )
        run = self.run_cli(
            "proposal", "submit", OPERATION, "--submission", source
        )
        after = self.table_counts()
        delta = {table: after[table] - before[table] for table in before}
        self.assertEqual(run.status, 0)
        self.assertEqual(
            {table: change for table, change in delta.items() if change},
            {"requests": 1, "proposals": 1, "events": 1},
        )
        expected = {table: 0 for table in before}
        expected.update({"requests": 1, "proposals": 1, "events": 1})
        self.assertEqual(delta, expected)

    def test_x26_commandcandidatesource_remains_imported_and_the_existing_h(self) -> None:
        """X26 [D26] CommandCandidateSource remains imported and the existing handle source seam remains intact

        ACTION: ENCODE

        EXPECTED:
        The import count is 1, `_source` still references `CommandCandidateSource` 1 or more
        times, and handle's source destination set remains exactly 3 names.

        RULING:
        CONFIRMED. `cli.py` holds three `CommandCandidateSource` references: the import and its
        uses inside `_source`. The seam must survive intact - D24 forbids the new leaves from
        REACHING a source, never the CLI from offering one to the routes that always had it.
        """
        source = Path(inspect.getsourcefile(cement_cli) or "").read_text()
        tree = ast.parse(source)
        imports = [
            alias
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "source"
            and node.level == 1
            for alias in node.names
            if alias.name == "CommandCandidateSource"
        ]
        helper = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_source"
        )
        references = sum(
            isinstance(node, ast.Name) and node.id == "CommandCandidateSource"
            for node in ast.walk(helper)
        )
        handle = self.parser_node("handle")
        self.assertIsNotNone(handle)
        assert handle is not None
        source_destinations = {
            action.dest for action in handle._actions if action.dest.startswith("source_")
        }
        configured = cement_cli._source(
            '["adapter"]', source_id="source-probe", timeout=1.0
        )
        self.assertEqual(len(imports), 1)
        self.assertGreaterEqual(references, 1)
        self.assertEqual(
            source_destinations,
            {"source_command", "source_id", "source_timeout"},
        )
        self.assertIsInstance(configured, cement_cli.CommandCandidateSource)

    def test_x27_b02_retires_only_the_cli_py_byte_pin_and_keeps_both_surviv(self) -> None:
        """X27 [D27] B02 retires only the cli.py byte pin and keeps both surviving runtime files frozen

        ACTION: ENCODE

        EXPECTED:
        B02's tuple equals exactly `{src/cement_runtime/_command_supervisor.py,
        src/cement_runtime/example_adapter.py}`, both comparisons return 0, and its docstring
        names D24, D25, and D26.

        RULING:
        CONFIRMED. `test_b02_cli_py_command_supervisor_py_and` in
        tests/test_submission_battery.py retires the `cli.py` member and keeps the other two
        frozen against git object f9b9755, with a docstring naming D24, D25 and D26. This is
        D27's substance: the property the pin carried for `cli.py` - M3.3 added no CLI channel
        and no CLI source reach - MIGRATED to three live obligations rather than being dropped.
        A byte pin over a file the unit is chartered to extend can only be retired, and
        retiring it silently is the failure D27 exists to prevent.
        """
        path = ROOT / "tests/test_submission_battery.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        test = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "test_b02_cli_py_command_supervisor_py_and"
        )
        assignment = next(
            node
            for node in test.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "paths" for target in node.targets)
        )
        paths = tuple(
            str(element.value)
            for element in assignment.value.elts  # type: ignore[union-attr]
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        )
        expected = (
            "src/cement_runtime/_command_supervisor.py",
            "src/cement_runtime/example_adapter.py",
        )
        self.assertEqual(paths, expected)
        docstring = (ast.get_docstring(test) or "").lower()
        self.assertTrue(all(name in docstring for name in ("d24", "d25", "d26")))
        comparisons: list[bool] = []
        for relative in paths:
            baseline = subprocess.check_output(
                ("git", "-C", str(ROOT), "show", f"f9b9755:{relative}")
            )
            equal = (ROOT / relative).read_bytes() == baseline
            comparisons.append(equal)
            self.assertTrue(equal, relative)
        self.assertEqual(comparisons, [True, True])

    def test_x28_operator_prose_teaches_both_complete_grammars_payloads_exi(self) -> None:
        """X28 [D28] operator prose teaches both complete grammars payloads exits purity and non-idempotency

        ACTION: ENCODE

        EXPECTED:
        Published text contains both full grammars, all 7 resolve keys, `proposal_id`, exit
        classes `{0,2,3,4,5,6}`, `not idempotent`, and an explicit statement that resolve
        writes nothing.

        RULING:
        CONFIRMED, verified against shipped prose. README ships both grammars in runnable
        blocks, the seven-key payload table, `proposal_id` at status 0, every exit class,
        `Cement gives no idempotency here` and the write-freedom sentence. Three spellings the
        battery must honour, each measured against the shipped bytes. First, the runnable
        blocks spell the invocation `uv run cement ... resolve` while prose says `cement
        resolve`, so a token search must accept both. Second, the exit classes ship as PROSE,
        not as table cells: `Exit 6 is the negative-verdict class`, then `Exit 2 covers usage
        and validation. Exit 3 means an absent object, exit 4 a state conflict, and exit 5 an
        integrity failure.`, with exit 0 named where root `verify` reports a failed
        verification. A markdown numeric-cell regex over the publication set matches ZERO rows,
        so scan `exit N`/`status N` tokens and require {0,2,3,4,5,6} while 1 stays absent.
        Third, README:186 ships the write-freedom sentence as ``resolve` writes nothing.` with
        the identifier backticked, seconded by `The leaf writes nothing` at architecture.md:78;
        an unbackticked literal search for `resolve writes nothing` matches nothing. Quote
        shipped prose byte-exact in a ruling or name the token search that must match it.
        """
        paths = (
            ROOT / "README.md",
            ROOT / "docs/architecture.md",
            ROOT / "docs/threat-model.md",
            ROOT / "docs/adapter-protocol.md",
        )
        publication = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        lowered = publication.lower()
        flattened = " ".join(publication.replace("\\\n", " ").split()).lower()
        self.assertRegex(
            flattened,
            r"\bcement\b.*?\bresolve\s+\S+.*?--input\s+\S+",
        )
        self.assertIn("--expected-function-hash", flattened)
        self.assertRegex(
            flattened,
            r"\bcement\b.*?\bproposal submit\s+\S+.*?--submission\s+\S+",
        )
        for key in RESOLVE_KEYS:
            with self.subTest(resolve_key=key):
                self.assertIn(key, lowered)
        self.assertIn("proposal_id", lowered)
        # The exit classes ship as prose, not as numeric table cells.
        published_exits = {
            int(value) for value in re.findall(r"(?:exit|status)\s+([0-6])\b", lowered)
        }
        self.assertTrue({0, 2, 3, 4, 5, 6} <= published_exits)
        self.assertNotIn(1, published_exits)
        self.assertTrue(
            "not idempotent" in lowered or "no idempotency" in lowered
        )
        # README:186 backticks the identifier; architecture.md:78 seconds it.
        self.assertIn("`resolve` writes nothing", lowered)
        self.assertIn("the leaf writes nothing", lowered)

    def test_x29_the_publication_grep_scope_is_ambiguous_between_a_document(self) -> None:
        """X29 [D28] the publication grep scope is ambiguous between a document union and every document individually

        ACTION: ENCODE-SCOPED

        EXPECTED:
        The minimum-count map is `{union_cells:2, per_file_cells:8}`: union needs each spelling
        somewhere, while per-file needs both spellings in all 4 files.

        RULING:
        CONFIRMED as a real ambiguity, resolved by amendment A6 in favour of the UNION.
        Measured cells for (`cement resolve`, `cement proposal submit`): README (1,1),
        architecture (1,1), threat-model (1,2), adapter-protocol (0,0). A6 rules the union over
        README, docs/architecture.md and docs/threat-model.md, with README additionally
        required to carry both; docs/adapter-protocol.md is OUTSIDE the union because it
        documents the adapter protocol and names no CLI leaf. The per-file reading is rejected
        on merits: it would force redundant grammar transcription into documents whose job is
        not teaching invocation, and duplicated grammar is exactly what goes stale.
        """
        scoped_paths = (
            ROOT / "README.md",
            ROOT / "docs/architecture.md",
            ROOT / "docs/threat-model.md",
        )
        excluded = ROOT / "docs/adapter-protocol.md"
        patterns = (
            re.compile(
                r"\bcement(?:\s+--(?:db|partition)\s+\S+)*\s+resolve\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bcement(?:\s+--(?:db|partition)\s+\S+)*\s+proposal\s+submit\b",
                re.IGNORECASE,
            ),
        )

        def cells(text: str) -> tuple[bool, bool]:
            return tuple(bool(pattern.search(text)) for pattern in patterns)  # type: ignore[return-value]

        by_path = {
            path: cells(path.read_text(encoding="utf-8")) for path in scoped_paths
        }
        union = "\n".join(path.read_text(encoding="utf-8") for path in scoped_paths)
        union_cells = sum(cells(union))
        readme_cells = sum(by_path[ROOT / "README.md"])
        self.assertEqual(union_cells, 2)
        self.assertEqual(readme_cells, 2)
        self.assertEqual(len(scoped_paths), 3)
        self.assertNotIn(excluded, scoped_paths)

    def test_x30_every_placeholder_in_each_shipped_shell_block_is_produced(self) -> None:
        """X30 [D29] every placeholder in each shipped shell block is produced earlier inside that same block

        ACTION: ENCODE

        EXPECTED:
        The derived orphan-placeholder set is exactly `{}` across all shipped command blocks,
        including every new resolve and proposal-submit example.

        RULING:
        CONFIRMED. The single placeholder in the new blocks is `HASH_FROM_VERIFY`, and its
        producer `function verify support.reply` is the FIRST line of the same block, with the
        prose above naming it. Two derivation warnings MAIN measured the hard way: a naive
        fence regex spans fence boundaries and reports prose words such as `LLM`, `OCR` and
        `README` as placeholders, and placeholders inside inline code in prose - `request
        REQUEST_ID`, `events --after SEQUENCE` - are outside D29's scope. The battery must walk
        fences line by line and consider shipped command blocks only.
        """
        markdown = (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")))
        shell_languages = {"bash", "sh", "shell", "console"}
        blocks: list[tuple[Path, int, list[str]]] = []
        for path in markdown:
            active = False
            shell = False
            marker = ""
            started = 0
            lines: list[str] = []
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                opening = re.match(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_-]*)\s*$", line)
                if not active and opening:
                    active = True
                    marker = opening.group(1)
                    shell = opening.group(2).lower() in shell_languages
                    started = number
                    lines = []
                    continue
                if active and re.match(rf"^\s*{re.escape(marker)}\s*$", line):
                    if shell:
                        blocks.append((path, started, list(lines)))
                    active = False
                    shell = False
                    marker = ""
                    lines = []
                    continue
                if active:
                    lines.append(line)

        placeholder = re.compile(
            r"\b(?:[A-Z][A-Z0-9_]*_FROM_[A-Z0-9_]+|[A-Za-z][A-Za-z0-9]*_REPLACE_ME)\b"
        )
        orphans: set[str] = set()
        command_counts = {"resolve": 0, "proposal submit": 0}
        for path, started, lines in blocks:
            produced: set[str] = set()
            for offset, line in enumerate(lines, 1):
                assigned = {
                    match.group(1)
                    for match in re.finditer(r"\b([A-Z][A-Z0-9_]*)=", line)
                }
                consumed = set(placeholder.findall(line)) - assigned
                for token in consumed - produced:
                    orphans.add(f"{path.relative_to(ROOT)}:{started + offset}:{token}")
                lowered = " ".join(line.lower().split())
                if "proposal list" in lowered or "proposal submit" in lowered:
                    produced.add("prop_REPLACE_ME")
                if "function inspect" in lowered:
                    produced.add("HASH_FROM_INSPECT")
                if "function verify" in lowered:
                    produced.add("HASH_FROM_VERIFY")
                produced.update(assigned)
                if re.search(r"\bproposal\s+submit\b", lowered):
                    command_counts["proposal submit"] += 1
                if re.search(r"(?:^|\s)resolve\s+\S+", lowered):
                    command_counts["resolve"] += 1
        self.assertEqual(orphans, set())
        self.assertGreaterEqual(command_counts["resolve"], 1)
        self.assertGreaterEqual(command_counts["proposal submit"], 1)

    def test_x31_published_resolve_cost_figures_are_mechanically_derived_fr(self) -> None:
        """X31 [D30] published resolve cost figures are mechanically derived from the committed benchmark artifact

        ACTION: ENCODE

        EXPECTED:
        Prose derives exactly `5.7 ms`, `613 ms`, `36,452 ms` or `~36.5 s`, and `985,696 KiB`
        or `~963 MiB` from those 3 artifact points.

        RULING:
        CONFIRMED. All four figures derive from `m3u2b-resolve-bench.json` at the precision
        each entry count states: 5.7 ms at one entry, 613 ms at 1,000, 36,452 ms and 985,696
        KiB at 50,000, matching the method docstring's ~36.5 s and ~963 MiB. Deriving rather
        than transcribing is D30's mechanism - a re-measurement then moves prose and artifact
        together or fails loudly.
        """
        artifact = json.loads(
            (ROOT / ".agent/decisions/m3u2b-resolve-bench.json").read_text(
                encoding="utf-8"
            )
        )
        points = artifact["points"]
        self.assertEqual(
            {point["entries"] for point in points.values()},
            {1, 1_000, 50_000},
        )
        one = points["n1"]
        thousand = points["n1000"]
        cap = points["n50000"]
        derived = {
            "one": f"{one['resolve_cold_hit_ms']:.1f} ms",
            "thousand": f"{thousand['resolve_cold_hit_ms']:.0f} ms",
            "cap_ms": f"{cap['resolve_cold_hit_ms']:,.0f} ms",
            "cap_seconds": f"~{cap['resolve_cold_hit_ms'] / 1000:.1f} s",
            "rss_kib": f"{cap['peak_rss_kib']:,} KiB",
            "rss_mib": f"~{cap['peak_rss_kib'] / 1024:.0f} MiB",
        }
        self.assertEqual(
            derived,
            {
                "one": "5.7 ms",
                "thousand": "613 ms",
                "cap_ms": "36,452 ms",
                "cap_seconds": "~36.5 s",
                "rss_kib": "985,696 KiB",
                "rss_mib": "~963 MiB",
            },
        )
        publication = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")))
        )
        self.assertIn(derived["one"], publication)
        self.assertIn(derived["thousand"], publication)
        self.assertTrue(
            derived["cap_ms"] in publication
            or derived["cap_seconds"] in publication
        )
        self.assertTrue(
            derived["rss_kib"] in publication or derived["rss_mib"] in publication
        )

    def test_x32_resolve_help_and_operator_prose_never_characterize_the_ful(self) -> None:
        """X32 [D30] resolve help and operator prose never characterize the full verification as fast cheap or cached

        ACTION: ENCODE

        EXPECTED:
        Counts of `fast`, `cheap`, and affirmative `cached` claims are all 0; at least 1 help
        or prose surface states `six` checks or `full verification` and `caches nothing`.

        RULING:
        CONFIRMED with the shipped sentence named. `fast` and `cheap` are absent; the two
        `cached` occurrences both describe WITHHOLDING cached output on the reconciliation path
        and are not affirmative claims about resolve. The positive half is shipped as `Cement
        caches no verification between calls.` in README alongside `One resolve runs the full
        six-check verification, so it costs what function verify costs.` The battery must match
        those meaning-bearing tokens, NOT the literal string `caches nothing`, which appears
        only in the method docstring. This row is D27's rule applied to cost: `resolve writes
        nothing` invites a cheapness inference that only the caching sentence closes.
        """
        node = self.parser_node("resolve")
        self.assertIsNotNone(node)
        assert node is not None
        paths = (
            ROOT / "README.md",
            ROOT / "docs/architecture.md",
            ROOT / "docs/threat-model.md",
        )
        surfaces = [node.format_help().lower()]
        for path in paths:
            for paragraph in path.read_text(encoding="utf-8").split("\n\n"):
                lowered = " ".join(paragraph.lower().split())
                if (
                    "cement resolve" in lowered
                    or "`resolve`" in lowered
                    or "one resolve" in lowered
                ):
                    surfaces.append(lowered)
        scoped = " ".join(surfaces)
        counts = {
            word: len(re.findall(rf"\b{word}\b", scoped))
            for word in ("fast", "cheap")
        }
        affirmative_cached: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", scoped):
            if not re.search(r"\bcached\b", sentence):
                continue
            if any(
                marker in sentence
                for marker in ("not", "no cached", "never", "without", "withhold")
            ):
                continue
            affirmative_cached.append(sentence)
        self.assertEqual(counts, {"fast": 0, "cheap": 0})
        self.assertEqual(affirmative_cached, [])
        self.assertTrue(
            "full six-check verification" in scoped
            or "full verification" in scoped
            or "six checks" in scoped
        )
        self.assertTrue(
            "caches no verification between calls" in scoped
            or "does not cache verification" in scoped
            or "caches nothing" in scoped
        )


if __name__ == "__main__":
    unittest.main()
