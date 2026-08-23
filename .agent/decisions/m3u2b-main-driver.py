"""Run MAIN shipped resolver over the fixed M3.2b R01-R26 corpus."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import Any
from unittest import mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    Resolved,
    ReviewRequired,
    System,
)
from cement_runtime import function as runtime_function
from cement_runtime import json_value as runtime_json
from cement_runtime import system as runtime_system


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".agent" / "decisions" / "m3u2b-main.json"
BASE_COMMIT = "e381ce3"
PARTITION = "tenant_a"
OPERATION = "echo_1"
EMPTY_OPERATION = "empty_1"
FIXED_TIME_US = 1_700_000_000_000_000
INPUTS: tuple[dict[str, object], ...] = (
    {"n": 1, "tag": "first"},
    {"n": 12, "tag": "middle"},
    {"n": 3, "tag": "last"},
)
MISS_INPUT = {"n": 404, "tag": "absent"}


def _resolve(system: System, *args: Any, **kwargs: Any) -> Any:
    return system.resolve(*args, **kwargs)


class ExactSource:
    def __init__(self) -> None:
        self.calls = 0

    def propose(self, request: Any) -> Candidate:
        self.calls += 1
        return Candidate(output=request.input, provenance={"kind": "oracle-exact"})


class BombSource:
    def __init__(self) -> None:
        self.calls = 0

    def propose(self, request: Any) -> Candidate:
        self.calls += 1
        raise AssertionError("candidate source was invoked")


class BombClock:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        raise AssertionError("clock was read")


@dataclass(frozen=True, slots=True)
class Fixture:
    database: Path
    function_hash: str
    artifact_by_input_hash: dict[str, str]
    example_ids_by_input_hash: dict[str, tuple[str, ...]]
    middle_artifact_id: str
    middle_example_id: str


@dataclass(frozen=True, slots=True)
class Context:
    root: Path
    fixture: Fixture
    system: System


@dataclass(frozen=True, slots=True)
class ProbeResult:
    observation: dict[str, Any]
    agrees: bool


@dataclass(frozen=True, slots=True)
class Probe:
    identifier: str
    note: str
    run: Callable[[Context], ProbeResult]


def _policy() -> CompilePolicy:
    return CompilePolicy(2, 1, 0)


def _confirm_pair(
    system: System,
    partition: str,
    operation: str,
    input_value: object,
    prefix: str,
) -> tuple[str, ...]:
    example_ids: list[str] = []
    for index in range(2):
        outcome = system.handle(
            partition,
            operation,
            input_value,
            request_id=f"{prefix}-{index}",
        )
        if not isinstance(outcome, ReviewRequired):
            raise RuntimeError(
                f"{prefix}-{index}: expected ReviewRequired, got {type(outcome).__name__}"
            )
        reviewed = system.review(
            partition,
            outcome.proposal_id,
            reviewer="oracle-reviewer",
            decision="accept",
        )
        if not isinstance(reviewed, Resolved):
            raise RuntimeError(
                f"{prefix}-{index}: expected Resolved, got {type(reviewed).__name__}"
            )
        example_ids.append(reviewed.example_id)
    return tuple(example_ids)


def _build_status_decoy(
    system: System,
    partition: str,
    operation: str,
    input_value: object,
    prefix: str,
    status: str,
) -> None:
    _confirm_pair(system, partition, operation, input_value, prefix)
    compiled = system.compile(partition, operation, compiled_by="oracle-compiler")
    if len(compiled.created) != 1 or compiled.existing or compiled.blocked:
        raise RuntimeError(f"{prefix}: decoy compile did not create exactly one draft")
    artifact_id = compiled.created[0]
    if status == "draft":
        return
    verified = system.verify_drafts(
        partition,
        operation,
        verified_by="oracle-verifier",
    )
    if not verified.passed or len(verified.entries) != 1 or verified.skipped:
        raise RuntimeError(f"{prefix}: decoy verification did not pass exactly once")
    if status == "verified":
        return
    if status != "suspended":
        raise RuntimeError(f"{prefix}: unsupported decoy status {status!r}")
    system.suspend_artifact(
        partition,
        artifact_id,
        suspended_by="oracle-operator",
        reason="oracle status-dimension fixture",
    )


def _build_fixture(database: Path) -> Fixture:
    source = ExactSource()
    system = System(database, candidate_source=source, clock_us=lambda: FIXED_TIME_US)
    policy = _policy()
    system.register_operation(
        PARTITION,
        OPERATION,
        policy=policy,
        registered_by="oracle-builder",
    )
    for revision in range(2, 13):
        actual = system.revise_operation(
            PARTITION,
            OPERATION,
            policy=policy,
            revised_by="oracle-builder",
        )
        if actual != revision:
            raise RuntimeError(f"main operation revision {actual}, expected {revision}")

    registrations = (
        (PARTITION, EMPTY_OPERATION),
        ("tenantXa", OPERATION),
        ("Tenant_a", OPERATION),
        (PARTITION, "echoX1"),
        (PARTITION, "Echo_1"),
    )
    for partition, operation in registrations:
        system.register_operation(
            partition,
            operation,
            policy=_policy(),
            registered_by="oracle-builder",
        )

    examples_by_hash: dict[str, tuple[str, ...]] = {}
    for index, input_value in enumerate(INPUTS):
        digest = runtime_json.canonicalize(input_value).digest
        examples_by_hash[digest] = _confirm_pair(
            system,
            PARTITION,
            OPERATION,
            input_value,
            f"oracle-main-{index}",
        )
    compiled = system.compile(PARTITION, OPERATION, compiled_by="oracle-compiler")
    if len(compiled.created) != len(INPUTS) or compiled.existing or compiled.blocked:
        raise RuntimeError("main compile did not create the three expected drafts")
    verified = system.verify_drafts(
        PARTITION,
        OPERATION,
        verified_by="oracle-verifier",
    )
    if not verified.passed or len(verified.entries) != len(INPUTS) or verified.skipped:
        raise RuntimeError("main draft verification did not pass all three entries")
    artifact_by_hash = {
        entry.input_hash: entry.artifact_id for entry in verified.entries
    }
    if set(artifact_by_hash) != set(examples_by_hash):
        raise RuntimeError("verified artifact inputs differ from confirmed fixture inputs")
    manifest = system.inspect_function_promotion(PARTITION, OPERATION)
    promotion = system.promote_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
        promoted_by="oracle-release-manager",
    )
    if len(promotion.member_artifact_ids) != len(INPUTS):
        raise RuntimeError("main function promotion did not retain three members")

    _build_status_decoy(
        system,
        "tenantXa",
        OPERATION,
        {"n": 21, "tag": "partition-collider"},
        "oracle-decoy-draft",
        "draft",
    )
    _build_status_decoy(
        system,
        PARTITION,
        "echoX1",
        {"n": 22, "tag": "operation-collider"},
        "oracle-decoy-verified",
        "verified",
    )
    _build_status_decoy(
        system,
        PARTITION,
        "Echo_1",
        {"n": 23, "tag": "operation-case"},
        "oracle-decoy-suspended",
        "suspended",
    )

    ordered_hashes = sorted(artifact_by_hash)
    middle_hash = ordered_hashes[1]
    return Fixture(
        database=database,
        function_hash=promotion.function_hash,
        artifact_by_input_hash=artifact_by_hash,
        example_ids_by_input_hash=examples_by_hash,
        middle_artifact_id=artifact_by_hash[middle_hash],
        middle_example_id=examples_by_hash[middle_hash][0],
    )


def _clone(
    context: Context,
    name: str,
    *,
    source: object | None = None,
    clock: Callable[[], int] | None = None,
) -> tuple[Path, System]:
    destination = context.root / f"{name}.db"
    shutil.copy2(context.fixture.database, destination)
    return destination, System(destination, candidate_source=source, clock_us=clock)


def _suspended_clone(context: Context, name: str) -> tuple[Path, System]:
    path, system = _clone(context, name, clock=lambda: FIXED_TIME_US)
    system.suspend_artifact(
        PARTITION,
        context.fixture.middle_artifact_id,
        suspended_by="oracle-operator",
        reason="oracle failed-verdict fixture",
    )
    return path, system


def _revoked_clone(context: Context, name: str) -> tuple[Path, System, int]:
    path, system = _clone(context, name, clock=lambda: FIXED_TIME_US)
    suspended = system.revoke_example(
        PARTITION,
        context.fixture.middle_example_id,
        revoked_by="oracle-operator",
        reason="oracle revoked-member fixture",
    )
    return path, system, len(suspended)


def _wrong_hash(value: str) -> str:
    replacement = "0" if value[0] != "0" else "1"
    return replacement + value[1:]


def _capture_exception(call: Callable[[], object]) -> dict[str, Any]:
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - exception class + text are probe data
        return {"class": type(exc).__name__, "message": str(exc)}
    return {"class": "None", "message": "call returned without raising"}


def _ledger_state(path: Path) -> tuple[str, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    connection = sqlite3.connect(path)
    try:
        dump = "\n".join(connection.iterdump())
    finally:
        connection.close()
    return digest, dump


def _event_sequence(path: Path) -> int:
    connection = sqlite3.connect(path)
    try:
        row = connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
        ).fetchone()
    finally:
        connection.close()
    return 0 if row is None else int(row[0])


def _event_bytes(system: System) -> bytes:
    return json.dumps(
        system.events(PARTITION, limit=1_000),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _ledger_stability(
    system: System,
    path: Path,
    input_value: object,
) -> dict[str, bool]:
    before_hash, before_dump = _ledger_state(path)
    _resolve(system, PARTITION, OPERATION, input_value)
    after_hash, after_dump = _ledger_state(path)
    return {
        "iterdump_equal": before_dump == after_dump,
        "sha256_equal": before_hash == after_hash,
    }


def _event_stability(
    system: System,
    path: Path,
    input_value: object,
) -> dict[str, bool]:
    before_events = _event_bytes(system)
    before_sequence = _event_sequence(path)
    _resolve(system, PARTITION, OPERATION, input_value)
    after_events = _event_bytes(system)
    after_sequence = _event_sequence(path)
    return {
        "events_bytes_equal": before_events == after_events,
        "sequence_equal": before_sequence == after_sequence,
    }


def _clock_comparison(path: Path, input_value: object) -> dict[str, Any]:
    expected = _resolve(System(path), PARTITION, OPERATION, input_value)
    clock = BombClock()
    actual = _resolve(
        System(path, clock_us=clock),
        PARTITION,
        OPERATION,
        input_value,
    )
    return {"clock_calls": clock.calls, "same_resolution": actual == expected}


def _probe_r01(context: Context) -> ProbeResult:
    resolution = _resolve(context.system, PARTITION, OPERATION, INPUTS[1])
    match = resolution.match
    document = resolution.verification.document
    artifact_hash = None if match is None else match.artifact_hash
    observation = {
        "artifact_hash_equals_promoted_member": (
            document is not None
            and artifact_hash in {entry.artifact_hash for entry in document.entries}
        ),
        "artifact_hash_is_64hex": (
            type(artifact_hash) is str
            and re.fullmatch(r"[0-9a-f]{64}", artifact_hash) is not None
        ),
        "document_present": document is not None,
        "entries": resolution.verification.entries,
        "matched": None if match is None else match.matched,
        "output": None if match is None else match.output,
        "passed": resolution.verification.passed,
    }
    agrees = observation == {
        "artifact_hash_equals_promoted_member": True,
        "artifact_hash_is_64hex": True,
        "document_present": True,
        "entries": 3,
        "matched": True,
        "output": INPUTS[1],
        "passed": True,
    }
    return ProbeResult(observation, agrees)


def _probe_r02(context: Context) -> ProbeResult:
    resolution = _resolve(context.system, PARTITION, OPERATION, MISS_INPUT)
    match = resolution.match
    observation = {
        "artifact_hash_is_none": match is not None and match.artifact_hash is None,
        "document_present": resolution.verification.document is not None,
        "entries": resolution.verification.entries,
        "matched": None if match is None else match.matched,
        "output_is_none": match is not None and match.output is None,
        "passed": resolution.verification.passed,
    }
    agrees = observation == {
        "artifact_hash_is_none": True,
        "document_present": True,
        "entries": 3,
        "matched": False,
        "output_is_none": True,
        "passed": True,
    }
    return ProbeResult(observation, agrees)


def _probe_r03(context: Context) -> ProbeResult:
    _, system = _suspended_clone(context, "r03-suspended")
    resolution = _resolve(system, PARTITION, OPERATION, INPUTS[0])
    observation = {
        "document_is_none": resolution.verification.document is None,
        "entries": resolution.verification.entries,
        "match_is_none": resolution.match is None,
        "passed": resolution.verification.passed,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "document_is_none": True,
            "entries": 2,
            "match_is_none": True,
            "passed": False,
        },
    )


def _probe_r04(context: Context) -> ProbeResult:
    resolution = _resolve(
        context.system,
        PARTITION,
        OPERATION,
        INPUTS[0],
        expected_function_hash=_wrong_hash(context.fixture.function_hash),
    )
    hash_check = next(
        check
        for check in resolution.verification.checks
        if check.key == "function-hash-matches-snapshot"
    )
    observation = {
        "document_is_none": resolution.verification.document is None,
        "hash_check_passed": hash_check.passed,
        "match_is_none": resolution.match is None,
        "passed": resolution.verification.passed,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "document_is_none": True,
            "hash_check_passed": False,
            "match_is_none": True,
            "passed": False,
        },
    )


def _probe_r05(context: Context) -> ProbeResult:
    resolution = _resolve(
        context.system,
        PARTITION,
        EMPTY_OPERATION,
        INPUTS[0],
    )
    match = resolution.match
    observation = {
        "artifact_hash_is_none": match is not None and match.artifact_hash is None,
        "document_present": resolution.verification.document is not None,
        "entries": resolution.verification.entries,
        "matched": None if match is None else match.matched,
        "output_is_none": match is not None and match.output is None,
        "passed": resolution.verification.passed,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "artifact_hash_is_none": True,
            "document_present": True,
            "entries": 0,
            "matched": False,
            "output_is_none": True,
            "passed": True,
        },
    )


def _probe_r06(context: Context) -> ProbeResult:
    capacity = len(context.fixture.artifact_by_input_hash) - 1
    with (
        mock.patch.object(runtime_system, "FUNCTION_MAX_ENTRIES", capacity),
        mock.patch.object(
            context.system,
            "_promoted_function_rows",
            wraps=context.system._promoted_function_rows,
        ) as enumeration,
    ):
        resolution = _resolve(
            context.system,
            PARTITION,
            OPERATION,
            INPUTS[0],
        )
    observation = {
        "all_checks_failed": all(
            not check.passed for check in resolution.verification.checks
        ),
        "document_is_none": resolution.verification.document is None,
        "entries": resolution.verification.entries,
        "enumeration_calls": enumeration.call_count,
        "match_is_none": resolution.match is None,
        "passed": resolution.verification.passed,
        "patched_capacity": capacity,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "all_checks_failed": True,
            "document_is_none": True,
            "entries": 3,
            "enumeration_calls": 0,
            "match_is_none": True,
            "passed": False,
            "patched_capacity": 2,
        },
    )


def _probe_r07(context: Context) -> ProbeResult:
    hit = _resolve(context.system, PARTITION, OPERATION, INPUTS[0])
    miss = _resolve(context.system, PARTITION, OPERATION, MISS_INPUT)
    _, failed_system = _suspended_clone(context, "r07-failed")
    failed = _resolve(failed_system, PARTITION, OPERATION, INPUTS[0])
    resolutions = (hit, miss, failed)
    observation = {
        "failed_implies_match_none": all(
            resolution.verification.passed or resolution.match is None
            for resolution in resolutions
        ),
        "match_none_implies_failed": all(
            resolution.match is not None or not resolution.verification.passed
            for resolution in resolutions
        ),
        "state_count": len(resolutions),
    }
    return ProbeResult(
        observation,
        observation
        == {
            "failed_implies_match_none": True,
            "match_none_implies_failed": True,
            "state_count": 3,
        },
    )


def _name_message(label: str) -> str:
    return (
        f"{label} must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"
    )


def _exception_probe(
    call: Callable[[], object],
    expected_class: str,
    expected_message: str,
) -> ProbeResult:
    observation = _capture_exception(call)
    return ProbeResult(
        observation,
        observation == {"class": expected_class, "message": expected_message},
    )


def _probe_r08(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(context.system, "", OPERATION, INPUTS[0]),
        "ValidationError",
        _name_message("partition"),
    )


def _probe_r09(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(context.system, PARTITION, "", INPUTS[0]),
        "ValidationError",
        _name_message("operation"),
    )


def _probe_r10(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(
            context.system,
            PARTITION,
            OPERATION,
            INPUTS[0],
            expected_function_hash="not-a-digest",
        ),
        "ValidationError",
        "expected_function_hash must be a SHA-256 hex digest",
    )


def _probe_r11(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(context.system, PARTITION, OPERATION, object()),
        "ValidationError",
        "value of type 'object' is not JSON",
    )


def _probe_r12(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(context.system, "", OPERATION, object()),
        "ValidationError",
        _name_message("partition"),
    )


def _probe_r13(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(
            context.system,
            PARTITION,
            "",
            INPUTS[0],
            expected_function_hash="not-a-digest",
        ),
        "ValidationError",
        _name_message("operation"),
    )


def _probe_r14(context: Context) -> ProbeResult:
    return _exception_probe(
        lambda: _resolve(context.system, PARTITION, "absent_1", INPUTS[0]),
        "NotFoundError",
        "operation is not registered in this partition",
    )


def _probe_r15(context: Context) -> ProbeResult:
    with (
        mock.patch.object(
            context.system.store,
            "transaction",
            wraps=context.system.store.transaction,
        ) as transaction,
        mock.patch.object(
            context.system,
            "verify_function",
            wraps=context.system.verify_function,
        ) as verify,
    ):
        observation = _capture_exception(
            lambda: _resolve(
                context.system,
                PARTITION,
                OPERATION,
                "x" * runtime_json.DEFAULT_MAX_BYTES,
            )
        )
    observation.update(
        {"transaction_calls": transaction.call_count, "verify_calls": verify.call_count}
    )
    expected = {
        "class": "ValidationError",
        "message": (
            f"canonical JSON exceeds {runtime_json.DEFAULT_MAX_BYTES} bytes"
        ),
        "transaction_calls": 0,
        "verify_calls": 0,
    }
    return ProbeResult(observation, observation == expected)


def _probe_r16(context: Context) -> ProbeResult:
    path, system = _clone(context, "r16-missing")
    path.unlink()
    absent_before = not path.exists()
    observation = _capture_exception(
        lambda: _resolve(system, PARTITION, OPERATION, INPUTS[0])
    )
    observation.update(
        {
            "path_absent_after": not path.exists(),
            "path_absent_before": absent_before,
        }
    )
    expected = {
        "class": "IntegrityError",
        "message": "ledger file is missing or unreadable",
        "path_absent_after": True,
        "path_absent_before": True,
    }
    return ProbeResult(observation, observation == expected)


def _corrupt_operation_revision(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("ALTER TABLE operations RENAME TO operations_strict")
        connection.execute(
            """
            CREATE TABLE operations (
                partition TEXT NOT NULL,
                name TEXT NOT NULL,
                revision TEXT NOT NULL,
                policy_json TEXT NOT NULL,
                policy_hash TEXT NOT NULL,
                created_at_us INTEGER NOT NULL,
                updated_at_us INTEGER NOT NULL,
                PRIMARY KEY (partition, name)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO operations(
                partition, name, revision, policy_json, policy_hash,
                created_at_us, updated_at_us
            )
            SELECT partition, name,
                   CASE WHEN partition = ? AND name = ?
                        THEN 'not-an-int' ELSE CAST(revision AS TEXT) END,
                   policy_json, policy_hash, created_at_us, updated_at_us
            FROM operations_strict
            """,
            (PARTITION, OPERATION),
        )
        connection.execute("DROP TABLE operations_strict")
        connection.commit()
    finally:
        connection.close()


def _probe_r17(context: Context) -> ProbeResult:
    path, system = _clone(context, "r17-malformed-revision")
    _corrupt_operation_revision(path)
    return _exception_probe(
        lambda: _resolve(system, PARTITION, OPERATION, INPUTS[0]),
        "IntegrityError",
        "stored operation revision is invalid",
    )


def _probe_r18(context: Context) -> ProbeResult:
    _, system, suspended_count = _revoked_clone(context, "r18-revoked")
    resolution = _resolve(system, PARTITION, OPERATION, INPUTS[0])
    observation = {
        "document_is_none": resolution.verification.document is None,
        "match_is_none": resolution.match is None,
        "passed": resolution.verification.passed,
        "suspended_dependents": suspended_count,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "document_is_none": True,
            "match_is_none": True,
            "passed": False,
            "suspended_dependents": 1,
        },
    )


def _probe_r19(context: Context) -> ProbeResult:
    _, failed_system = _suspended_clone(context, "r19-failed")
    failed_path = Path(failed_system.store.path)
    observation = {
        "failed": _ledger_stability(failed_system, failed_path, INPUTS[0]),
        "hit": _ledger_stability(
            context.system,
            context.fixture.database,
            INPUTS[0],
        ),
        "miss": _ledger_stability(
            context.system,
            context.fixture.database,
            MISS_INPUT,
        ),
    }
    agrees = all(
        state == {"iterdump_equal": True, "sha256_equal": True}
        for state in observation.values()
    )
    return ProbeResult(observation, agrees)


def _probe_r20(context: Context) -> ProbeResult:
    failed_path, _ = _suspended_clone(context, "r20-failed")
    observation = {
        "failed": _clock_comparison(failed_path, INPUTS[0]),
        "hit": _clock_comparison(context.fixture.database, INPUTS[0]),
        "miss": _clock_comparison(context.fixture.database, MISS_INPUT),
    }
    agrees = all(
        state == {"clock_calls": 0, "same_resolution": True}
        for state in observation.values()
    )
    return ProbeResult(observation, agrees)


def _probe_r21(context: Context) -> ProbeResult:
    failed_path, failed_system = _suspended_clone(context, "r21-failed")
    observation = {
        "failed": _event_stability(failed_system, failed_path, INPUTS[0]),
        "hit": _event_stability(
            context.system,
            context.fixture.database,
            INPUTS[0],
        ),
        "miss": _event_stability(
            context.system,
            context.fixture.database,
            MISS_INPUT,
        ),
    }
    agrees = all(
        state == {"events_bytes_equal": True, "sequence_equal": True}
        for state in observation.values()
    )
    return ProbeResult(observation, agrees)


def _probe_r22(context: Context) -> ProbeResult:
    source = BombSource()
    system = System(context.fixture.database, candidate_source=source)
    resolution = _resolve(system, PARTITION, OPERATION, MISS_INPUT)
    observation = {
        "matched": None if resolution.match is None else resolution.match.matched,
        "output_is_none": (
            resolution.match is not None and resolution.match.output is None
        ),
        "passed": resolution.verification.passed,
        "source_calls": source.calls,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "matched": False,
            "output_is_none": True,
            "passed": True,
            "source_calls": 0,
        },
    )


class _ConnectionProbe:
    def __init__(self, connection: sqlite3.Connection, samples: list[bool]) -> None:
        self._connection = connection
        self._samples = samples

    def _sample(self) -> None:
        self._samples.append(self._connection.in_transaction)

    def execute(self, sql: str, parameters: object = ()) -> sqlite3.Cursor:
        self._sample()
        cursor = self._connection.execute(sql, parameters)
        self._sample()
        return cursor

    def executemany(self, sql: str, parameters: object) -> sqlite3.Cursor:
        self._sample()
        cursor = self._connection.executemany(sql, parameters)
        self._sample()
        return cursor

    @property
    def in_transaction(self) -> bool:
        return self._connection.in_transaction

    def __getattr__(self, name: str) -> object:
        return getattr(self._connection, name)


def _probe_r23(context: Context) -> ProbeResult:
    samples: list[bool] = []
    original = context.system.store.transaction

    @contextmanager
    def tracked_transaction(*, write: bool = False) -> Iterator[_ConnectionProbe]:
        with original(write=write) as connection:
            samples.append(connection.in_transaction)
            yield _ConnectionProbe(connection, samples)
            samples.append(connection.in_transaction)

    with mock.patch.object(
        context.system.store,
        "transaction",
        wraps=tracked_transaction,
    ) as transaction:
        _resolve(context.system, PARTITION, OPERATION, INPUTS[0])
    call = transaction.call_args
    observation = {
        "all_in_transaction": bool(samples) and all(samples),
        "transaction_calls": transaction.call_count,
        "write_false": call is not None and call.kwargs == {"write": False},
    }
    return ProbeResult(
        observation,
        observation
        == {
            "all_in_transaction": True,
            "transaction_calls": 1,
            "write_false": True,
        },
    )


def _probe_r24(context: Context) -> ProbeResult:
    _, failed_system = _suspended_clone(context, "r24-failed")
    counts: dict[str, int] = {}
    with mock.patch.object(
        runtime_system,
        "evaluate",
        wraps=runtime_system.evaluate,
    ) as evaluate:
        _resolve(failed_system, PARTITION, OPERATION, INPUTS[0])
        counts["failed"] = evaluate.call_count
        evaluate.reset_mock()
        _resolve(context.system, PARTITION, OPERATION, INPUTS[0])
        counts["hit"] = evaluate.call_count
        evaluate.reset_mock()
        _resolve(context.system, PARTITION, OPERATION, MISS_INPUT)
        counts["miss"] = evaluate.call_count
    return ProbeResult(counts, counts == {"failed": 0, "hit": 1, "miss": 1})


def _probe_r25(context: Context) -> ProbeResult:
    input_json = runtime_json.canonicalize(INPUTS[0])
    inside: dict[str, object] = {}
    original = context.system._persisted_function_receipt_check

    def capture_inside(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        operation_revision: int,
        entry_count: int,
        document: object,
    ) -> object:
        if document is not None:
            inside["document"] = document
            inside["in_transaction"] = connection.in_transaction
            inside["match"] = runtime_function.evaluate(
                document,
                input_json=input_json,
            )
        return original(
            connection,
            partition=partition,
            operation=operation,
            operation_revision=operation_revision,
            entry_count=entry_count,
            document=document,
        )

    with mock.patch.object(
        context.system,
        "_persisted_function_receipt_check",
        side_effect=capture_inside,
    ):
        resolution = _resolve(context.system, PARTITION, OPERATION, INPUTS[0])
    observation = {
        "document_identity_preserved": (
            inside.get("document") is resolution.verification.document
        ),
        "inside_equals_outside": inside.get("match") == resolution.match,
        "inside_in_transaction": inside.get("in_transaction") is True,
    }
    return ProbeResult(
        observation,
        observation
        == {
            "document_identity_preserved": True,
            "inside_equals_outside": True,
            "inside_in_transaction": True,
        },
    )


def _probe_r26(context: Context) -> ProbeResult:
    original_input = INPUTS[1]
    reordered_input = {"tag": original_input["tag"], "n": original_input["n"]}
    original = _resolve(
        context.system,
        PARTITION,
        OPERATION,
        original_input,
    )
    reordered = _resolve(
        context.system,
        PARTITION,
        OPERATION,
        reordered_input,
    )
    observation = {
        "artifact_hash_equal": (
            original.match is not None
            and reordered.match is not None
            and original.match.artifact_hash == reordered.match.artifact_hash
        ),
        "canonical_digest_equal": (
            runtime_json.canonicalize(original_input).digest
            == runtime_json.canonicalize(reordered_input).digest
        ),
        "matched_both": (
            original.match is not None
            and reordered.match is not None
            and original.match.matched
            and reordered.match.matched
        ),
        "output_equal": (
            original.match is not None
            and reordered.match is not None
            and original.match.output == reordered.match.output
        ),
    }
    return ProbeResult(
        observation,
        observation
        == {
            "artifact_hash_equal": True,
            "canonical_digest_equal": True,
            "matched_both": True,
            "output_equal": True,
        },
    )


PROBES: tuple[Probe, ...] = (
    Probe("R01_hit", "Resolved one promoted input and recorded the complete verified-hit shape.", _probe_r01),
    Probe("R02_miss", "Resolved one absent input and recorded the complete verified-miss shape.", _probe_r02),
    Probe("R03_failed_suspended", "Suspended the hash-ordered middle member, then resolved a failed verdict.", _probe_r03),
    Probe("R04_expected_hash_mismatch", "Passed a distinct valid digest and recorded identity-pinning failure.", _probe_r04),
    Probe("R05_no_promoted_set", "Resolved a registered zero-member operation and recorded its vacuous function.", _probe_r05),
    Probe("R06_over_capacity", "FABRICATED: patched FUNCTION_MAX_ENTRIES to two over a real three-member set.", _probe_r06),
    Probe("R07_biconditional", "Checked both implications across one hit, one miss, and one failed verdict.", _probe_r07),
    Probe("R08_invalid_partition", "Submitted an empty partition and captured the exact validation exception.", _probe_r08),
    Probe("R09_invalid_operation", "Submitted an empty operation and captured the exact validation exception.", _probe_r09),
    Probe("R10_invalid_expected_hash", "Submitted a non-digest expected hash and captured the exact exception.", _probe_r10),
    Probe("R11_uncanonicalizable_input", "Submitted an object instance that cement-json-v1 cannot canonicalize.", _probe_r11),
    Probe("R12_precedence_partition_before_input", "Submitted an empty partition with an uncanonicalizable input to pin precedence.", _probe_r12),
    Probe("R13_precedence_operation_before_expected_hash", "Submitted an empty operation with a malformed digest to pin precedence.", _probe_r13),
    Probe("R14_unregistered_operation", "Resolved a valid absent operation and captured the exact not-found exception.", _probe_r14),
    Probe("R15_oversize_input", "Submitted canonical JSON above DEFAULT_MAX_BYTES while spying on every ledger entry point.", _probe_r15),
    Probe("R16_missing_ledger", "Deleted an initialized clone before resolve and checked that no file reappeared.", _probe_r16),
    Probe("R17_malformed_stored_revision", "Rebuilt the operations table with one non-integer revision, then resolved it.", _probe_r17),
    Probe("R18_revoked_member", "Revoked evidence for the hash-ordered middle member through the public API.", _probe_r18),
    Probe("R19_ledger_bytes_stable", "Compared ledger SHA-256 and full SQLite iterdump around all three states.", _probe_r19),
    Probe("R20_clock_never_read", "Compared all three states against Systems whose clock raises on every call.", _probe_r20),
    Probe("R21_events_unchanged", "Compared serialized events and sqlite_sequence around all three resolve states.", _probe_r21),
    Probe("R22_source_never_invoked", "Resolved a miss with a CandidateSource that raises if propose is called.", _probe_r22),
    Probe("R23_one_snapshot", "Wrapped Store.transaction and sampled in_transaction around every verification query.", _probe_r23),
    Probe("R24_evaluate_call_counts", "Spied on function.evaluate separately for failed, hit, and miss states.", _probe_r24),
    Probe("R25_document_outside_snapshot", "Evaluated the reconstructed document inside verification and after snapshot exit.", _probe_r25),
    Probe("R26_canonical_equivalent_input", "Resolved one promoted object with reversed key insertion order and compared hits.", _probe_r26),
)


def _implementation_commit() -> str:
    output = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "rev-list",
            "--reverse",
            f"{BASE_COMMIT}..HEAD",
        ],
        text=True,
    )
    commits = output.splitlines()
    return commits[0] if commits else BASE_COMMIT


def _payload(context: Context, through: int) -> dict[str, Any]:
    probes: dict[str, dict[str, Any]] = {}
    for index, probe in enumerate(PROBES, start=1):
        if index > through:
            probes[probe.identifier] = {
                "outcome": "unknown",
                "observation": "unknown",
                "note": probe.note,
            }
            continue
        try:
            result = probe.run(context)
        except Exception as exc:  # noqa: BLE001 - harness failures remain gradeable
            probes[probe.identifier] = {
                "outcome": "error",
                "observation": {
                    "class": type(exc).__name__,
                    "message": str(exc),
                },
                "note": probe.note,
            }
        else:
            probes[probe.identifier] = {
                "outcome": "ok" if result.agrees else "differs",
                "observation": result.observation,
                "note": probe.note,
            }
    complete = through == len(PROBES)
    return {
        "kind": "oracle",
        "unit": "M3.2b",
        "author": "diff-m3u2b",
        "implementation": "MAIN shipped System.resolve",
        "impl_path": "src/cement_runtime/system.py" if complete else "unknown",
        "driver_path": ".agent/decisions/m3u2b-main-driver.py" if complete else "unknown",
        "commit": _implementation_commit() if complete else "unknown",
        "probes": probes,
    }


def _write_payload(payload: dict[str, Any]) -> None:
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--through",
        type=int,
        default=len(PROBES),
        choices=range(1, len(PROBES) + 1),
        metavar="N",
        help="fill probes R01 through RN; default: all",
    )
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="m3u2b-oracle-", dir=ROOT) as raw:
        temporary = Path(raw)
        fixture = _build_fixture(temporary / "fixture.db")
        context = Context(
            root=temporary,
            fixture=fixture,
            system=System(fixture.database),
        )
        payload = _payload(context, arguments.through)
    _write_payload(payload)
    print(f"WROTE: {OUTPUT.relative_to(ROOT)}")
    print(f"FILLED-PROBES: {arguments.through}")
    print(f"UNKNOWN-PROBES: {len(PROBES) - arguments.through}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
