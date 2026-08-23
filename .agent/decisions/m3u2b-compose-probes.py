#!/usr/bin/env python3
"""Real-ledger probes for the M3.2b thin resolver composition."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
from typing import Callable, Iterator
from unittest import mock

import cement_runtime.function as function_module
import cement_runtime.system as system_module
from cement_runtime import (
    Candidate,
    CompilePolicy,
    IntegrityError,
    NotFoundError,
    System,
    evaluate,
)
from cement_runtime.json_value import canonicalize


ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "019d040"
PARTITION = "probe"
OPERATION = "echo"
INPUT = {"z": 0, "outer": {"a": 1, "b": [2, 3]}}
OUTPUT = {"echo": INPUT}
ProbeResult = tuple[str, str]


class Source:
    def propose(self, request):
        return Candidate(
            output={"echo": request.input},
            provenance={"probe": "m3u2b-compose"},
        )


class Clock:
    def __init__(self) -> None:
        self.value = 1_000_000

    def __call__(self) -> int:
        self.value += 1
        return self.value


@dataclass
class Fixture:
    path: Path
    system: System
    artifact_id: str
    function_hash: str


@contextmanager
def promoted_fixture(*, input_value: object = INPUT) -> Iterator[Fixture]:
    with tempfile.TemporaryDirectory(prefix=".m3u2b-compose-", dir=ROOT) as temporary:
        path = Path(temporary) / "ledger.db"
        system = System(path, candidate_source=Source(), clock_us=Clock())
        system.register_operation(
            PARTITION,
            OPERATION,
            policy=CompilePolicy(2, 1, 0),
        )
        for index in (1, 2):
            review = system.handle(
                PARTITION,
                OPERATION,
                input_value,
                request_id=f"fixture-{index}",
            )
            system.review(
                PARTITION,
                review.proposal_id,
                reviewer="reviewer",
                decision="accept",
            )
        compiled = system.compile(PARTITION, OPERATION)
        if len(compiled.created) != 1:
            raise AssertionError(f"fixture compile created={compiled.created!r}")
        artifact_id = compiled.created[0]
        report = system.verify(PARTITION, artifact_id)
        if not report.passed:
            raise AssertionError(f"fixture report passed={report.passed!r}")
        system.promote(
            PARTITION,
            artifact_id,
            scope_hash=report.scope_hash,
            promoted_by="probe",
        )
        manifest = system.inspect_function_promotion(PARTITION, OPERATION)
        system.promote_function(
            PARTITION,
            OPERATION,
            expected_function_hash=manifest.function_hash,
            promoted_by="probe",
        )
        yield Fixture(path, system, artifact_id, manifest.function_hash)


def empty_fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, System]:
    temporary = tempfile.TemporaryDirectory(prefix=".m3u2b-compose-", dir=ROOT)
    path = Path(temporary.name) / "ledger.db"
    system = System(path, candidate_source=Source(), clock_us=Clock())
    system.register_operation(
        PARTITION,
        OPERATION,
        policy=CompilePolicy(2, 1, 0),
    )
    return temporary, path, system


def ledger_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ledger_dump(path: Path) -> tuple[str, ...]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return tuple(connection.iterdump())
    finally:
        connection.close()


def counters(path: Path) -> tuple[tuple[str, int], ...]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return tuple(
            (str(name), int(sequence))
            for name, sequence in connection.execute(
                "SELECT name, seq FROM sqlite_sequence ORDER BY name"
            )
        )
    finally:
        connection.close()


def probe_c1_hit() -> ProbeResult:
    with promoted_fixture() as fixture:
        result = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        match = result.match
        if not result.verification.passed or match is None or not match.matched:
            raise AssertionError(f"unexpected result={result!r}")
        if match.output != OUTPUT or match.artifact_hash is None:
            raise AssertionError(f"unexpected match={match!r}")
        return (
            "ok",
            "passed=True matched=True output="
            f"{json.dumps(match.output, sort_keys=True, separators=(',', ':'))} "
            f"artifact_hash={match.artifact_hash}",
        )


def probe_c2_miss() -> ProbeResult:
    with promoted_fixture() as fixture:
        result = fixture.system.resolve(PARTITION, OPERATION, {"missing": True})
        match = result.match
        if not result.verification.passed or match is None or match.matched:
            raise AssertionError(f"unexpected result={result!r}")
        if match.output is not None or match.artifact_hash is not None:
            raise AssertionError(f"unexpected match={match!r}")
        return (
            "ok",
            "passed=True matched=False output=None artifact_hash=None "
            f"function_hash={result.verification.function_hash}",
        )


def probe_c3_failed_verification() -> ProbeResult:
    with promoted_fixture() as fixture:
        fixture.system.suspend_artifact(
            PARTITION,
            fixture.artifact_id,
            suspended_by="probe",
            reason="C3",
        )
        result = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        if result.verification.passed or result.match is not None:
            raise AssertionError(f"unexpected result={result!r}")
        if result.verification.document is not None:
            raise AssertionError("failed verification returned a document")
        return (
            "ok",
            "passed=False match=None document=None "
            f"entries={result.verification.entries} checks="
            f"{[check.passed for check in result.verification.checks]}",
        )


def probe_c4_expected_hash_mismatch() -> ProbeResult:
    with promoted_fixture() as fixture:
        expected = "0" * 64
        result = fixture.system.resolve(
            PARTITION,
            OPERATION,
            INPUT,
            expected_function_hash=expected,
        )
        if result.verification.passed or result.match is not None:
            raise AssertionError(f"unexpected result={result!r}")
        return (
            "ok",
            f"expected={expected} actual={fixture.function_hash} "
            "passed=False match=None document=None",
        )


def probe_c5_empty_promoted_set() -> ProbeResult:
    temporary, _, system = empty_fixture()
    try:
        result = system.resolve(PARTITION, OPERATION, INPUT)
        match = result.match
        if not result.verification.passed or result.verification.entries != 0:
            raise AssertionError(f"unexpected verification={result.verification!r}")
        if match is None or match.matched:
            raise AssertionError(f"unexpected match={match!r}")
        return (
            "ok",
            "passed=True entries=0 matched=False output=None artifact_hash=None "
            f"checks={[check.passed for check in result.verification.checks]}",
        )
    finally:
        temporary.cleanup()


def probe_c6_one_snapshot() -> ProbeResult:
    with promoted_fixture() as fixture:
        original = fixture.system.store.transaction
        states: list[tuple[str, bool]] = []
        statements: list[str] = []

        @contextmanager
        def traced_transaction(*, write: bool = False):
            with original(write=write) as connection:
                states.append(("enter", connection.in_transaction))

                def trace(statement: str) -> None:
                    statements.append(statement)
                    states.append(("sql", connection.in_transaction))

                connection.set_trace_callback(trace)
                try:
                    yield connection
                finally:
                    states.append(("exit", connection.in_transaction))
                    connection.set_trace_callback(None)

        with mock.patch.object(
            fixture.system.store,
            "transaction",
            side_effect=traced_transaction,
        ) as transaction_spy:
            result = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        flags = [call.kwargs.get("write", False) for call in transaction_spy.call_args_list]
        if not result.verification.passed or result.match is None:
            raise AssertionError(f"unexpected result={result!r}")
        if transaction_spy.call_count != 1 or flags != [False]:
            raise AssertionError(
                f"transactions={transaction_spy.call_count} flags={flags!r}"
            )
        if not states or not all(in_transaction for _, in_transaction in states):
            raise AssertionError(f"transaction states={states!r}")
        return (
            "ok",
            f"transaction_calls=1 write_flags={flags} sql_statements={len(statements)} "
            f"state_samples={len(states)} in_transaction_all=True "
            f"enter={states[0][1]} exit={states[-1][1]}",
        )


def probe_c7_no_clock() -> ProbeResult:
    with promoted_fixture() as fixture:
        baseline = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        with mock.patch.object(
            System,
            "_now",
            side_effect=AssertionError("resolve called the clock"),
        ) as clock_spy:
            measured = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        if measured != baseline or clock_spy.call_count != 0:
            raise AssertionError(
                f"baseline={baseline!r} measured={measured!r} calls={clock_spy.call_count}"
            )
        match = measured.match
        if match is None:
            raise AssertionError("passing verification returned no match")
        return (
            "ok",
            f"clock_calls=0 answers_equal=True passed={measured.verification.passed} "
            f"matched={match.matched} artifact_hash={match.artifact_hash}",
        )


def probe_c8_no_write() -> ProbeResult:
    with promoted_fixture() as fixture:
        observations: list[str] = []

        def unchanged(label: str, call: Callable[[], object]) -> None:
            before_sha = ledger_sha256(fixture.path)
            before_dump = ledger_dump(fixture.path)
            call()
            after_sha = ledger_sha256(fixture.path)
            after_dump = ledger_dump(fixture.path)
            if before_sha != after_sha or before_dump != after_dump:
                raise AssertionError(
                    f"{label} sha={before_sha}->{after_sha} "
                    f"dump_equal={before_dump == after_dump}"
                )
            observations.append(
                f"{label}:sha256={before_sha},dump_statements={len(before_dump)}"
            )

        unchanged(
            "hit",
            lambda: fixture.system.resolve(PARTITION, OPERATION, INPUT),
        )
        unchanged(
            "miss",
            lambda: fixture.system.resolve(
                PARTITION,
                OPERATION,
                {"missing": True},
            ),
        )
        fixture.system.suspend_artifact(
            PARTITION,
            fixture.artifact_id,
            suspended_by="probe",
            reason="C8",
        )
        unchanged(
            "failed",
            lambda: fixture.system.resolve(PARTITION, OPERATION, INPUT),
        )
        return "ok", " | ".join(observations) + " | before_after_equal=True"


def probe_c9_no_event_no_id() -> ProbeResult:
    with promoted_fixture() as fixture:
        observations: list[str] = []

        def unchanged(label: str, call: Callable[[], object]) -> None:
            before_events = fixture.system.events(PARTITION)
            before_counters = counters(fixture.path)
            call()
            after_events = fixture.system.events(PARTITION)
            after_counters = counters(fixture.path)
            if before_events != after_events or before_counters != after_counters:
                raise AssertionError(
                    f"{label} events_equal={before_events == after_events} "
                    f"counters={before_counters!r}->{after_counters!r}"
                )
            observations.append(
                f"{label}:events={len(before_events)},counters={before_counters!r}"
            )

        unchanged(
            "hit",
            lambda: fixture.system.resolve(PARTITION, OPERATION, INPUT),
        )
        unchanged(
            "miss",
            lambda: fixture.system.resolve(
                PARTITION,
                OPERATION,
                {"missing": True},
            ),
        )
        fixture.system.suspend_artifact(
            PARTITION,
            fixture.artifact_id,
            suspended_by="probe",
            reason="C9",
        )
        unchanged(
            "failed",
            lambda: fixture.system.resolve(PARTITION, OPERATION, INPUT),
        )
        return "ok", " | ".join(observations) + " | before_after_equal=True"


def probe_c10_missing_ledger() -> ProbeResult:
    with promoted_fixture() as fixture:
        fixture.path.unlink()
        try:
            fixture.system.resolve(PARTITION, OPERATION, INPUT)
        except Exception as exc:
            if type(exc) is not IntegrityError:
                raise AssertionError(
                    f"expected IntegrityError, got {type(exc).__name__}: {exc}"
                ) from exc
            if fixture.path.exists():
                raise AssertionError("resolve recreated the deleted ledger")
            return (
                "error",
                f"{type(exc).__name__}: {exc}; ledger_exists_after=False",
            )
        raise AssertionError("resolve accepted a deleted ledger")


def probe_c11_unregistered_operation() -> ProbeResult:
    with promoted_fixture() as fixture:
        try:
            fixture.system.resolve(PARTITION, "missing", INPUT)
        except Exception as exc:
            if type(exc) is not NotFoundError:
                raise AssertionError(
                    f"expected NotFoundError, got {type(exc).__name__}: {exc}"
                ) from exc
            return "error", f"{type(exc).__name__}: {exc}"
        raise AssertionError("resolve accepted an unregistered operation")


def probe_c12_canonical_equivalent_input() -> ProbeResult:
    reordered = {"outer": {"b": [2, 3], "a": 1}, "z": 0}
    original_json = canonicalize(INPUT)
    reordered_json = canonicalize(reordered)
    with promoted_fixture() as fixture:
        original = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        equivalent = fixture.system.resolve(PARTITION, OPERATION, reordered)
        if original_json != reordered_json:
            raise AssertionError(
                f"canonical forms differ: {original_json!r} != {reordered_json!r}"
            )
        if original.match is None or equivalent.match is None:
            raise AssertionError("passing verification returned no match")
        if not original.match.matched or equivalent.match != original.match:
            raise AssertionError(
                f"original={original.match!r} equivalent={equivalent.match!r}"
            )
        return (
            "ok",
            f"canonical_digest={original_json.digest} matched=True "
            f"same_match=True artifact_hash={original.match.artifact_hash}",
        )


def probe_c13_evaluate_outside_snapshot() -> ProbeResult:
    with promoted_fixture() as fixture:
        original_transaction = fixture.system.store.transaction
        original_build = system_module.build_function
        input_json = canonicalize(INPUT)
        documents: list[object] = []
        captured: dict[str, object] = {}

        def capture_build(*args, **kwargs):
            document = original_build(*args, **kwargs)
            documents.append(document)
            return document

        @contextmanager
        def capture_transaction(*, write: bool = False):
            with original_transaction(write=write) as connection:
                try:
                    yield connection
                finally:
                    if not documents:
                        raise AssertionError("verification built no function document")
                    captured["inside_in_transaction"] = connection.in_transaction
                    captured["inside_match"] = evaluate(
                        documents[0],
                        input_json=input_json,
                    )
            try:
                captured["after_state"] = f"in_transaction={connection.in_transaction}"
            except Exception as exc:
                captured["after_state"] = f"{type(exc).__name__}: {exc}"

        with mock.patch.object(
            fixture.system.store,
            "transaction",
            side_effect=capture_transaction,
        ) as transaction_spy, mock.patch.object(
            system_module,
            "build_function",
            side_effect=capture_build,
        ):
            verification = fixture.system.verify_function(PARTITION, OPERATION)
        document = verification.document
        if document is None or document is not documents[0]:
            raise AssertionError(
                f"returned_document={document!r} built_documents={documents!r}"
            )
        outside = evaluate(document, input_json=input_json)
        inside = captured.get("inside_match")
        if captured.get("inside_in_transaction") is not True:
            raise AssertionError(f"inside state={captured!r}")
        if inside != outside:
            raise AssertionError(f"inside={inside!r} outside={outside!r}")
        after_state = str(captured.get("after_state"))
        if after_state == "in_transaction=True":
            raise AssertionError("verification transaction remained open")
        return (
            "ok",
            f"transaction_calls={transaction_spy.call_count} "
            f"inside_in_transaction=True after={after_state!r} "
            f"same_document=True inside_equals_outside=True matched={outside.matched} "
            f"artifact_hash={outside.artifact_hash} build_documents={len(documents)}",
        )


def probe_c14_document_none_gate() -> ProbeResult:
    with promoted_fixture() as fixture:
        fixture.system.suspend_artifact(
            PARTITION,
            fixture.artifact_id,
            suspended_by="probe",
            reason="C14",
        )
        with mock.patch.object(
            system_module,
            "evaluate",
            side_effect=AssertionError("failed verdict reached evaluate"),
        ) as evaluate_spy:
            result = fixture.system.resolve(PARTITION, OPERATION, INPUT)
        if result.verification.passed or result.verification.document is not None:
            raise AssertionError(f"unexpected verification={result.verification!r}")
        if result.match is not None or evaluate_spy.call_count != 0:
            raise AssertionError(
                f"match={result.match!r} evaluate_calls={evaluate_spy.call_count}"
            )
        return (
            "ok",
            "passed=False document=None match=None evaluate_calls=0",
        )


def probe_c15_concurrent_writer() -> ProbeResult:
    with promoted_fixture() as fixture:
        reader = fixture.system
        writer = System(fixture.path, clock_us=Clock())
        first = reader.resolve(PARTITION, OPERATION, INPUT)
        writer.suspend_artifact(
            PARTITION,
            fixture.artifact_id,
            suspended_by="separate-writer",
            reason="C15 committed between resolves",
        )
        writer_events = writer.events(PARTITION)
        second = reader.resolve(PARTITION, OPERATION, INPUT)
        if first.match is None or not first.verification.passed or not first.match.matched:
            raise AssertionError(f"unexpected first={first!r}")
        if second.verification.passed or second.match is not None:
            raise AssertionError(f"unexpected second={second!r}")
        committed = writer_events[-1]
        if committed["kind"] != "artifact.suspended":
            raise AssertionError(f"unexpected writer event={committed!r}")
        return (
            "ok",
            f"writer=separate_System event_sequence={committed['sequence']} "
            f"event_kind={committed['kind']} first_passed=True first_matched=True "
            f"first_artifact_hash={first.match.artifact_hash} "
            "second_passed=False second_match=None second_sees_commit=True",
        )


def probe_c16_factoring_forced() -> ProbeResult:
    def calls(function: Callable[..., object]) -> list[str]:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        found: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                found.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                found.append(node.func.attr)
        return found

    resolve_calls = calls(System.resolve)
    verify_calls = calls(System.verify_function)
    evaluate_tree = ast.parse(textwrap.dedent(inspect.getsource(evaluate)))
    evaluate_attributes = sorted(
        {
            node.attr
            for node in ast.walk(evaluate_tree)
            if isinstance(node, ast.Attribute)
        }
    )
    bundle_attributes = sorted(
        {
            node.attr
            for node in ast.walk(evaluate_tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "bundle"
        }
    )
    forbidden = sorted(
        {"connection", "store", "transaction", "sqlite3", "System"}
        & set(evaluate.__code__.co_names)
    )
    document_fields = tuple(function_module.FunctionDocument.__dataclass_fields__)
    behavioral = {
        "one_snapshot": probe_c6_one_snapshot()[0],
        "outside_snapshot": probe_c13_evaluate_outside_snapshot()[0],
        "concurrent_writer": probe_c15_concurrent_writer()[0],
    }
    if resolve_calls.count("verify_function") != 1 or resolve_calls.count("evaluate") != 1:
        raise AssertionError(f"resolve calls={resolve_calls!r}")
    if verify_calls.count("transaction") != 1:
        raise AssertionError(
            f"verify_function transaction calls={verify_calls.count('transaction')}"
        )
    if forbidden or bundle_attributes != ["entries", "input_hashes"]:
        raise AssertionError(
            f"evaluate forbidden={forbidden!r} bundle_attributes={bundle_attributes!r}"
        )
    if any(outcome != "ok" for outcome in behavioral.values()):
        raise AssertionError(f"behavioral ablation={behavioral!r}")
    return (
        "ok",
        "searched AST call graph + repeated C6/C13/C15 real-ledger ablations; "
        f"resolve_verify_calls=1 resolve_evaluate_calls=1 "
        f"verify_transaction_calls=1 evaluate_forbidden_names={forbidden} "
        f"evaluate_attributes={evaluate_attributes} bundle_attributes={bundle_attributes} "
        f"document_fields={document_fields} "
        f"behavioral={behavioral}; no behavior found that requires a supplied connection",
    )


def probe_c17_production_line_count() -> ProbeResult:
    command = [
        "git",
        "-C",
        str(ROOT),
        "diff",
        "--numstat",
        BASE_COMMIT,
        "--",
        "src/cement_runtime",
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    rows: list[tuple[int, int, str]] = []
    for line in completed.stdout.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-" or deleted == "-":
            raise AssertionError(f"binary production diff: {line}")
        rows.append((int(added), int(deleted), path))
    if not rows:
        raise AssertionError("production diff is empty")
    added = sum(row[0] for row in rows)
    deleted = sum(row[1] for row in rows)
    files = ",".join(f"{path}:+{a}/-{d}" for a, d, path in rows)
    return (
        "ok",
        f"base={BASE_COMMIT} files={len(rows)} added={added} deleted={deleted} "
        f"net={added - deleted} detail={files}",
    )


PROBES: dict[str, Callable[[], ProbeResult]] = {
    "C1_hit": probe_c1_hit,
    "C2_miss": probe_c2_miss,
    "C3_failed_verification": probe_c3_failed_verification,
    "C4_expected_hash_mismatch": probe_c4_expected_hash_mismatch,
    "C5_empty_promoted_set": probe_c5_empty_promoted_set,
    "C6_one_snapshot": probe_c6_one_snapshot,
    "C7_no_clock": probe_c7_no_clock,
    "C8_no_write": probe_c8_no_write,
    "C9_no_event_no_id": probe_c9_no_event_no_id,
    "C10_missing_ledger": probe_c10_missing_ledger,
    "C11_unregistered_operation": probe_c11_unregistered_operation,
    "C12_canonical_equivalent_input": probe_c12_canonical_equivalent_input,
    "C13_evaluate_outside_snapshot": probe_c13_evaluate_outside_snapshot,
    "C14_document_none_gate": probe_c14_document_none_gate,
    "C15_concurrent_writer": probe_c15_concurrent_writer,
    "C16_factoring_forced": probe_c16_factoring_forced,
    "C17_production_line_count": probe_c17_production_line_count,
}


def main(argv: list[str]) -> int:
    selected = argv[1:] or list(PROBES)
    unknown = [probe_id for probe_id in selected if probe_id not in PROBES]
    if unknown:
        print(f"unknown probe id(s): {', '.join(unknown)}", file=sys.stderr)
        return 1
    failed = False
    for probe_id in selected:
        try:
            outcome, note = PROBES[probe_id]()
        except Exception as exc:
            failed = True
            print(f"{probe_id} UNRUN {type(exc).__name__}: {exc}")
        else:
            print(f"{probe_id} {outcome}: {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
