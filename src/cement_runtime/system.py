"""Supervised fallback, evidence compilation, verification, and promotion."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import os
import re
import sqlite3
import time
import unicodedata
import uuid
from typing import Any, Literal, cast

from .artifacts import (
    ARTIFACT_ABI,
    ARTIFACT_MAX_BYTES,
    ArtifactDocument,
    build_digest,
    build_exact_lookup,
    execute,
    validate_artifact,
)
from .errors import (
    CandidateSourceError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    ValidationError,
)
from .function import (
    FUNCTION_ABI,
    FUNCTION_ENTRY_SEAL_ABI,
    FUNCTION_MAX_BYTES,
    FUNCTION_MAX_DEPTH,
    FUNCTION_MAX_ENTRIES,
    FUNCTION_MAX_ITEMS,
    FunctionDocument,
    FunctionEntry,
    build_function,
    evaluate,
    validate_function,
)
from .json_value import (
    CANONICALIZER,
    DEFAULT_MAX_BYTES,
    CanonicalJSON,
    JSONValue,
    canonicalize,
    parse_json,
)
from .models import (
    Candidate,
    CandidateRequest,
    CompilePolicy,
    CompileResult,
    CompileScope,
    DraftEntry,
    DraftVerification,
    FallbackFailed,
    FunctionAnchorReport,
    FunctionCheck,
    FunctionMember,
    FunctionPromotionEntry,
    FunctionPromotionManifest,
    FunctionReceipt,
    FunctionReceiptPage,
    FunctionReconstruction,
    FunctionReport,
    FunctionResolution,
    FunctionSetPromotion,
    FunctionVerification,
    InProgress,
    OperationArtifact,
    OperationArtifactStatus,
    OperationNowReport,
    Outcome,
    PendingProposalGap,
    Promotion,
    ProposalView,
    ReconciliationRequired,
    Rejected,
    Resolved,
    ReviewRequired,
    ReviewResult,
    StaleRevisionAnomaly,
    VerificationReport,
)
from .source import CandidateSource
from .store import Store

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}\Z")
_UNSET = object()
_RECEIPT_MAX_BYTES = 3 * DEFAULT_MAX_BYTES
_MAX_SQLITE_INTEGER = 2**63 - 1

FUNCTION_PROMOTION_MANIFEST_ABI = "cement-function-promotion-manifest-v1"
FUNCTION_PROMOTION_RECEIPT_ABI = "cement-function-promotion-v1"
FUNCTION_MEMBERSHIP_ABI = "cement-function-membership-v1"
_FUNCTION_MANIFEST_MAX_BYTES = 2 * FUNCTION_MAX_BYTES
_FUNCTION_MANIFEST_MAX_DEPTH = FUNCTION_MAX_DEPTH + 2
_FUNCTION_MANIFEST_MAX_ITEMS = 2 * FUNCTION_MAX_ITEMS
_ID_LIST_ABI = "cement-id-list-v1"



@dataclass(frozen=True, slots=True)
class _BlockedBuild:
    reasons: tuple[str, ...]
    support: int
    reviewer_count: int
    span_seconds: int


@dataclass(frozen=True, slots=True)
class _CurrentBuild:
    input_json: CanonicalJSON
    output_json: CanonicalJSON
    artifact: ArtifactDocument
    policy_json: str
    policy_hash: str
    evidence_snapshot_hash: str
    support: int
    reviewer_count: int
    span_seconds: int
    build_hash: str


@dataclass(frozen=True, slots=True)
class _FunctionPromotionPlanEntry:
    row: sqlite3.Row
    report: sqlite3.Row
    function_entry: FunctionEntry
    public: FunctionPromotionEntry


@dataclass(frozen=True, slots=True)
class _FunctionPromotionPlan:
    manifest: FunctionPromotionManifest
    policy_hash: str
    entries: tuple[_FunctionPromotionPlanEntry, ...]


def _name(value: str, label: str) -> str:
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise ValidationError(
            f"{label} must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"
        )
    return value


def _request_id(value: str) -> str:
    if type(value) is not str or _REQUEST_ID.fullmatch(value) is None:
        raise ValidationError("request_id must be a bounded ASCII identifier")
    return value


def _text(value: str, label: str, *, maximum: int = 512, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise ValidationError(f"{label} must be {'text' if allow_empty else 'non-empty text'}")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError(f"{label} must contain valid Unicode scalar values") from exc
    if len(encoded) > maximum or any(
        unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value
    ):
        raise ValidationError(f"{label} must be control-free and at most {maximum} UTF-8 bytes")
    return value


def _bounded_int(value: int, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValidationError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _digest_strings(label: str, values: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for value in (label,):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _function_entry_seal(
    artifact: sqlite3.Row | Mapping[str, Any],
    report: sqlite3.Row | Mapping[str, Any],
) -> str:
    """Hash the promotion-v2 field list minus promoter and timestamp."""

    return _digest_strings(
        FUNCTION_ENTRY_SEAL_ABI,
        (
            str(artifact["id"]),
            str(artifact["artifact_hash"]),
            str(artifact["build_hash"]),
            str(artifact["policy_hash"]),
            str(artifact["evidence_snapshot_hash"]),
            str(artifact["support"]),
            str(artifact["reviewer_count"]),
            str(artifact["span_seconds"]),
            str(artifact["scope_hash"]),
            str(report["id"]),
            str(report["details_hash"]),
            str(report["test_set_hash"]),
            str(report["test_count"]),
            str(report["passed"]),
        ),
    )


def _digest(value: str, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValidationError(f"{label} must be a SHA-256 hex digest")
    return value


def _id_list_hash(values: Sequence[str]) -> str:
    return _digest_strings(_ID_LIST_ABI, tuple(sorted(values)))


def _id_list_projection(
    values: Sequence[str],
) -> tuple[int, list[str], str]:
    ordered = tuple(sorted(values))
    return len(ordered), list(ordered[:100]), _id_list_hash(ordered)


def _membership_hash(rows: Sequence[sqlite3.Row | Mapping[str, Any]]) -> str:
    fields: list[str] = []
    for row in rows:
        fields.extend(
            (
                str(row["ordinal"]),
                str(row["artifact_id"]),
                str(row["report_id"]),
                str(row["input_hash"]),
                str(row["entry_seal"]),
            )
        )
    return _digest_strings(FUNCTION_MEMBERSHIP_ABI, tuple(fields))


def _function_receipt_hash(row: sqlite3.Row | Mapping[str, Any]) -> str:
    return _digest_strings(
        FUNCTION_PROMOTION_RECEIPT_ABI,
        (
            str(row["id"]),
            str(row["partition"]),
            str(row["operation"]),
            str(row["operation_revision"]),
            str(row["policy_hash"]),
            str(row["function_hash"]),
            str(row["membership_hash"]),
            str(row["member_count"]),
            str(row["candidate_artifact_ids_hash"]),
            str(row["candidate_count"]),
            str(row["retired_artifact_ids_hash"]),
            str(row["retired_count"]),
            str(row["promoted_by"]),
            str(row["promoted_at_us"]),
        ),
    )


def _function_receipt_from_row(
    row: sqlite3.Row | Mapping[str, Any],
) -> FunctionReceipt:
    try:
        receipt_id = _request_id(row["id"])
        partition = _name(row["partition"], "stored function receipt partition")
        operation = _name(row["operation"], "stored function receipt operation")
        promoted_by = _text(
            row["promoted_by"],
            "stored function receipt promoted_by",
            maximum=256,
        )
        policy_hash = _digest(
            row["policy_hash"], "stored function receipt policy_hash"
        )
        function_hash = _digest(
            row["function_hash"], "stored function receipt function_hash"
        )
        membership_hash = _digest(
            row["membership_hash"], "stored function receipt membership_hash"
        )
        candidate_artifact_ids_hash = _digest(
            row["candidate_artifact_ids_hash"],
            "stored function receipt candidate_artifact_ids_hash",
        )
        retired_artifact_ids_hash = _digest(
            row["retired_artifact_ids_hash"],
            "stored function receipt retired_artifact_ids_hash",
        )
        receipt_hash = _digest(
            row["receipt_hash"], "stored function receipt receipt_hash"
        )
    except (IndexError, KeyError, TypeError, ValidationError) as exc:
        raise IntegrityError("stored function receipt has invalid scalar fields") from exc

    integers = {
        "sequence": row["sequence"],
        "operation_revision": row["operation_revision"],
        "member_count": row["member_count"],
        "candidate_count": row["candidate_count"],
        "retired_count": row["retired_count"],
        "promoted_at_us": row["promoted_at_us"],
    }
    sequence = int(integers["sequence"])
    operation_revision = int(integers["operation_revision"])
    member_count = int(integers["member_count"])
    candidate_count = int(integers["candidate_count"])
    retired_count = int(integers["retired_count"])
    promoted_at_us = int(integers["promoted_at_us"])
    if not 1 <= sequence <= _MAX_SQLITE_INTEGER:
        raise IntegrityError("stored function receipt sequence is invalid")
    if not 1 <= operation_revision <= _MAX_SQLITE_INTEGER:
        raise IntegrityError("stored function receipt operation revision is invalid")
    if not 1 <= member_count <= FUNCTION_MAX_ENTRIES:
        raise IntegrityError("stored function receipt member count is invalid")
    if not 0 <= retired_count <= candidate_count <= member_count:
        raise IntegrityError("stored function receipt transition counts are invalid")
    if not 0 <= promoted_at_us <= _MAX_SQLITE_INTEGER:
        raise IntegrityError("stored function receipt timestamp is invalid")
    if _function_receipt_hash(row) != receipt_hash:
        raise IntegrityError("function receipt hash mismatch")
    return FunctionReceipt(
        id=receipt_id,
        sequence=sequence,
        partition=partition,
        operation=operation,
        operation_revision=operation_revision,
        policy_hash=policy_hash,
        function_hash=function_hash,
        membership_hash=membership_hash,
        member_count=member_count,
        candidate_artifact_ids_hash=candidate_artifact_ids_hash,
        candidate_count=candidate_count,
        retired_artifact_ids_hash=retired_artifact_ids_hash,
        retired_count=retired_count,
        promoted_by=promoted_by,
        promoted_at_us=promoted_at_us,
        receipt_hash=receipt_hash,
    )


def _stored_int(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = _MAX_SQLITE_INTEGER,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise IntegrityError(f"{label} is invalid")
    return value


def _event(
    connection: sqlite3.Connection,
    *,
    partition: str,
    kind: str,
    subject_type: str,
    subject_id: str,
    payload: Mapping[str, Any],
    now_us: int,
) -> int:
    payload_json = canonicalize(dict(payload), max_bytes=262_144).text
    cursor = connection.execute(
        """
        INSERT INTO events(partition, kind, subject_type, subject_id, payload_json, created_at_us)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (partition, kind, subject_type, subject_id, payload_json, now_us),
    )
    if cursor.lastrowid is None:
        raise IntegrityError("audit event did not receive a sequence")
    return int(cursor.lastrowid)


def _policy_from_text(text: str) -> CompilePolicy:
    value = parse_json(text, max_bytes=16_384).value
    if type(value) is not dict:
        raise IntegrityError("stored policy is not an object")
    try:
        return CompilePolicy.from_json(value)
    except ValidationError as exc:
        raise IntegrityError("stored policy is invalid") from exc


# -- private proposal binding adapter ---------------------------------------
#
# A proposal row carries no scope of its own at SCHEMA_VERSION 2: its operation, operation
# revision and canonical input live on a private request row that no public value names.
# These three functions are the ONLY definitions allowed to reach that row on behalf of the
# proposal read, review and report paths, so M3.6b's schema cut rewrites their statements and
# leaves every consumer untouched. Consumers supply parameters through a named selection and
# never SQL; a consumer that composes its own join has inverted the confinement gate even
# though the complement assertion still passes.


@dataclass(frozen=True, slots=True)
class _ProposalIds:
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ProposalFeed:
    status: str | None
    after_sequence: int
    limit: int


@dataclass(frozen=True, slots=True)
class _PendingProposals:
    operation: str
    limit: int


@dataclass(frozen=True, slots=True)
class _ProposalBinding:
    """One proposal joined to the private request row that carries its scope.

    ``row`` holds the proposal's own columns and is what the row-to-shape converters
    consume; every field beside it was recovered from the request row and is the only
    supported way for a consumer to read a request-derived value.
    """

    proposal_id: str
    partition: str
    operation: str
    operation_revision: int
    input_json: str
    input_hash: str
    request_id: str
    request_status: str
    row: sqlite3.Row


@dataclass(frozen=True, slots=True)
class _ProposalBindingSet:
    total: int
    rows: tuple[_ProposalBinding, ...]


def _proposal_binding_from_row(row: sqlite3.Row, *, partition: str) -> _ProposalBinding:
    # The complete statements LEFT JOIN so an EXISTING proposal whose private request row
    # is absent stays VISIBLE here and fails closed. An inner join deletes that proposal
    # from the result set instead, which makes an orphan indistinguishable from an absent
    # proposal on the singular paths and silently drops it from the feed. What the fork
    # ruling rejects is a LEFT JOIN that PUBLISHES the NULL binding columns; a LEFT JOIN
    # whose validator refuses them is how absent and orphaned stay distinguishable in one
    # statement.
    if row["bound_request_id"] is None:
        raise IntegrityError("proposal has no private request binding")
    try:
        proposal_id = _request_id(row["id"])
        request_id = _request_id(row["bound_request_id"])
        operation = _name(row["operation"], "operation")
        operation_revision = _stored_int(
            row["operation_revision"],
            "proposal operation revision",
            minimum=1,
        )
        input_hash = _digest(row["input_hash"], "proposal input_hash")
        input_json = str(row["bound_input_json"])
    except (IndexError, KeyError, TypeError, ValidationError) as exc:
        raise IntegrityError("proposal binding row has invalid scalar fields") from exc
    # Cross-field binding consistency deliberately stays with each consumer, at the exact
    # position it held before this adapter existed. Hoisting it here would pre-empt
    # _validate_proposal_shape and rewrite the class, message and precedence every corrupt
    # ledger reports, which is a behaviour change no consumer asked for.
    return _ProposalBinding(
        proposal_id=proposal_id,
        partition=partition,
        operation=operation,
        operation_revision=operation_revision,
        input_json=input_json,
        input_hash=input_hash,
        request_id=request_id,
        request_status=str(row["bound_request_status"]),
        row=row,
    )


def _proposal_bindings(
    connection: sqlite3.Connection,
    *,
    partition: str,
    selection: _ProposalIds | _ProposalFeed | _PendingProposals,
) -> _ProposalBindingSet:
    """Resolve proposals with their private request binding, one statement per selection."""

    if type(selection) is _ProposalIds:
        if not selection.values:
            return _ProposalBindingSet(total=0, rows=())
        if len(set(selection.values)) != len(selection.values):
            raise IntegrityError("proposal binding selection contains duplicate identifiers")
        placeholders = ", ".join("?" for _ in selection.values)
        rows = connection.execute(
            f"""
            SELECT p.*, r.partition AS bound_request_partition, r.operation,
                   r.operation_revision, r.input_json AS bound_input_json, r.input_hash,
                   r.id AS bound_request_id, r.status AS bound_request_status,
                   r.proposal_id AS bound_proposal_id
            FROM proposals AS p
            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id
            WHERE p.partition = ? AND p.id IN ({placeholders})
            """,
            (partition, *selection.values),
        ).fetchall()
    elif type(selection) is _ProposalFeed:
        rows = connection.execute(
            """
            SELECT p.*, r.partition AS bound_request_partition, r.operation,
                   r.operation_revision, r.input_json AS bound_input_json, r.input_hash,
                   r.id AS bound_request_id, r.status AS bound_request_status,
                   r.proposal_id AS bound_proposal_id
            FROM proposals AS p
            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id
            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)
              AND p.status_sequence > ?
            ORDER BY p.status_sequence LIMIT ?
            """,
            (
                partition,
                selection.status,
                selection.status,
                selection.after_sequence,
                selection.limit,
            ),
        ).fetchall()
    elif type(selection) is _PendingProposals:
        # One statement carries both numbers, so the pending selection keeps the two
        # request statements baseline issued. `item_count` is the operation-scoped
        # count the report publishes. `orphan_count` covers every pending proposal in
        # the partition whose private request row is absent: the detail cap bounds
        # RETURNED ROWS and never validation, so an orphan past the cap must fail
        # closed instead of silently lowering the count an inner join would compute.
        # An orphan has no recoverable operation, so it cannot be excluded by scope.
        count_row = connection.execute(
            """
            SELECT COUNT(*) FILTER (WHERE r.id IS NOT NULL AND r.operation = ?)
                       AS item_count,
                   COUNT(*) FILTER (WHERE r.id IS NULL) AS orphan_count
            FROM proposals AS p
            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id
            WHERE p.partition = ? AND p.status = 'pending'
            """,
            (selection.operation, partition),
        ).fetchone()
        if count_row is None:
            raise IntegrityError("pending proposal count is missing")
        if _stored_int(count_row["orphan_count"], "pending proposal orphan count"):
            raise IntegrityError("pending proposal has no private request binding")
        total = _stored_int(count_row["item_count"], "pending proposal count")
        rows = connection.execute(
            """
            SELECT p.*, r.partition AS bound_request_partition, r.operation,
                   r.operation_revision, r.input_json AS bound_input_json, r.input_hash,
                   r.id AS bound_request_id, r.status AS bound_request_status,
                   r.proposal_id AS bound_proposal_id
            FROM proposals AS p
            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id
            WHERE p.partition = ? AND r.operation = ? AND p.status = 'pending'
            ORDER BY p.id LIMIT ?
            """,
            (partition, selection.operation, selection.limit),
        ).fetchall()
        return _ProposalBindingSet(
            total=total,
            rows=tuple(
                _proposal_binding_from_row(row, partition=partition) for row in rows
            ),
        )
    else:
        raise IntegrityError("proposal binding selection is invalid")
    bindings = tuple(_proposal_binding_from_row(row, partition=partition) for row in rows)
    return _ProposalBindingSet(total=len(bindings), rows=bindings)


def _proposal_binding(
    connection: sqlite3.Connection,
    *,
    partition: str,
    proposal_id: str,
) -> _ProposalBinding | None:
    """Resolve one proposal, or ``None`` when the partition holds no bound row for it."""

    result = _proposal_bindings(
        connection,
        partition=partition,
        selection=_ProposalIds((proposal_id,)),
    )
    if not result.rows:
        return None
    if result.total != 1:
        raise IntegrityError("proposal binding lookup returned the wrong cardinality")
    return result.rows[0]


def _write_proposal_request_status(
    connection: sqlite3.Connection,
    *,
    binding: _ProposalBinding,
    status: Literal["rejected", "resolved"],
    final: CanonicalJSON | None,
    example_id: str | None,
    now_us: int,
) -> int:
    """Carry a review decision onto the private request row. Returns the rowcount."""

    if status == "rejected":
        return connection.execute(
            """
            UPDATE requests SET status = 'rejected', updated_at_us = ?
            WHERE partition = ? AND id = ? AND status = 'pending'
              AND proposal_id = ?
            """,
            (now_us, binding.partition, binding.request_id, binding.proposal_id),
        ).rowcount
    if final is None or example_id is None:
        raise IntegrityError("a resolved request needs its confirmed output and example")
    return connection.execute(
        """
        UPDATE requests
        SET status = 'resolved', output_json = ?, source_kind = 'confirmed',
            example_id = ?, updated_at_us = ?
        WHERE partition = ? AND id = ? AND status = 'pending'
          AND proposal_id = ?
        """,
        (
            final.text,
            example_id,
            now_us,
            binding.partition,
            binding.request_id,
            binding.proposal_id,
        ),
    ).rowcount


class System:
    """Local learning loop.

    All returned values are pure data. A caller may apply a ``Resolved`` plan only
    after its own live authorization/policy gate. Cement makes no principal or
    permission decision. Every control-plane mutation and every read relies on the
    embedding application's access control, and database access is the trust
    boundary. Actor and reviewer arguments are recorded assertions only.
    """

    def __init__(
        self,
        database: str | os.PathLike[str],
        *,
        candidate_source: CandidateSource | None = None,
        clock_us: Callable[[], int] | None = None,
        generation_lease_seconds: int = 120,
    ) -> None:
        generation_lease_seconds = _bounded_int(
            generation_lease_seconds,
            "generation_lease_seconds",
            minimum=1,
            maximum=3_600,
        )
        # A source is classified where it is invoked, never here: reading
        # ``propose`` off a descriptor already executes caller-supplied code, so a
        # constructor pre-flight is the very hazard it looks like a guard against.
        if clock_us is not None and not callable(clock_us):
            raise ValidationError("clock_us must be callable")
        self.store = Store(database)
        self.candidate_source = candidate_source
        self._clock_us = clock_us if clock_us is not None else (lambda: time.time_ns() // 1_000)
        self._lease_us = generation_lease_seconds * 1_000_000

    def _now(self) -> int:
        now = self._clock_us()
        if (
            type(now) is not int
            or now < 0
            or now > _MAX_SQLITE_INTEGER - self._lease_us
        ):
            raise StateError("clock must return a lease-safe signed 64-bit microsecond timestamp")
        return now

    # -- operation revisions -------------------------------------------------

    def register_operation(
        self,
        partition: str,
        operation: str,
        *,
        policy: CompilePolicy | None = None,
        registered_by: str = "local-system",
    ) -> int:
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        registered_by = _text(registered_by, "registered_by", maximum=256)
        if policy is None:
            policy = CompilePolicy()
        elif type(policy) is not CompilePolicy:
            raise ValidationError("policy must be a CompilePolicy")
        policy_json = canonicalize(policy.as_json(), max_bytes=16_384)
        now = self._now()
        with self.store.transaction(write=True) as connection:
            existing = connection.execute(
                "SELECT revision, policy_hash FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if existing is not None:
                if existing["policy_hash"] == policy_json.digest:
                    return int(existing["revision"])
                raise ConflictError("operation exists with a different policy; revise it explicitly")
            connection.execute(
                """
                INSERT INTO operations(
                    partition, name, revision, policy_json, policy_hash,
                    created_at_us, updated_at_us
                ) VALUES (?, ?, 1, ?, ?, ?, ?)
                """,
                (partition, operation, policy_json.text, policy_json.digest, now, now),
            )
            _event(
                connection,
                partition=partition,
                kind="operation.registered",
                subject_type="operation",
                subject_id=f"{partition}/{operation}@1",
                payload={"policy_hash": policy_json.digest, "registered_by": registered_by},
                now_us=now,
            )
        return 1

    def revise_operation(
        self,
        partition: str,
        operation: str,
        *,
        policy: CompilePolicy,
        revised_by: str,
    ) -> int:
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        revised_by = _text(revised_by, "revised_by", maximum=256)
        if type(policy) is not CompilePolicy:
            raise ValidationError("policy must be a CompilePolicy")
        policy_json = canonicalize(policy.as_json(), max_bytes=16_384)
        now = self._now()
        with self.store.transaction(write=True) as connection:
            current = connection.execute(
                "SELECT revision, policy_hash FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if current is None:
                raise NotFoundError("operation is not registered in this partition")
            previous = int(current["revision"])
            revision = previous + 1
            connection.execute(
                """
                UPDATE operations
                SET revision = ?, policy_json = ?, policy_hash = ?, updated_at_us = ?
                WHERE partition = ? AND name = ? AND revision = ?
                """,
                (
                    revision,
                    policy_json.text,
                    policy_json.digest,
                    now,
                    partition,
                    operation,
                    previous,
                ),
            )
            connection.execute(
                """
                UPDATE artifacts
                SET status = 'retired', promotion_hash = NULL,
                    status_reason = 'operation revised'
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND status IN ('draft', 'verified', 'promoted')
                """,
                (partition, operation, previous),
            )
            invalidated_generators = connection.execute(
                """
                UPDATE requests
                SET status = 'failed', error_code = 'operation_revised',
                    lease_owner = NULL, lease_until_us = NULL, updated_at_us = ?
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND status = 'generating'
                """,
                (now, partition, operation, previous),
            ).rowcount
            _event(
                connection,
                partition=partition,
                kind="operation.revised",
                subject_type="operation",
                subject_id=f"{partition}/{operation}@{revision}",
                payload={
                    "previous_revision": previous,
                    "policy_hash": policy_json.digest,
                    "revised_by": revised_by,
                    "invalidated_generators": invalidated_generators,
                },
                now_us=now,
            )
        return revision

    # -- explicit proposal submission ---------------------------------------

    @staticmethod
    def _canonical_candidate(candidate: Candidate) -> tuple[CanonicalJSON, CanonicalJSON]:
        if type(candidate) is not Candidate:
            raise ValidationError("candidate must be a Candidate")
        proposed = canonicalize(candidate.output)
        # ``dict()`` alone accepts any iterable of pairs, which admits a list or a
        # generator as provenance and silently drains a one-shot iterator.
        if not isinstance(candidate.provenance, Mapping):
            raise ValidationError("candidate provenance must be a mapping")
        # ``dict(Mapping)`` reads through ``keys()`` and ``__getitem__``. A direct
        # caller owns that object, so its own exception reaches it unchanged; the
        # source path contains the same failure with every other adapter defect.
        provenance = canonicalize(dict(candidate.provenance), max_bytes=65_536)
        return proposed, provenance

    def _submission_revision(self, partition: str, operation: str) -> int:
        with self.store.transaction() as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
        if registered is None:
            raise NotFoundError("operation is not registered in this partition")
        return int(registered["revision"])

    def _persist_proposal(
        self,
        *,
        partition: str,
        operation: str,
        expected_revision: int | None,
        request_id: str,
        input_json: CanonicalJSON,
        proposed: CanonicalJSON,
        provenance: CanonicalJSON,
    ) -> str:
        # The proposal binds to the revision current under the write lock. Only a
        # caller that captured a revision earlier — the source path, across
        # generation — holds an expectation the seam can find stale.
        with self.store.transaction(write=True) as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = int(registered["revision"])
            if expected_revision is not None and revision != expected_revision:
                raise StateError("operation revision changed before proposal submission")
            proposal_id = _new_id("prop")
            created = self._now()
            connection.execute(
                """
                INSERT INTO requests(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    status, proposal_id, created_at_us, updated_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (
                    request_id,
                    partition,
                    operation,
                    revision,
                    input_json.text,
                    input_json.digest,
                    proposal_id,
                    created,
                    created,
                ),
            )
            status_sequence = _event(
                connection,
                partition=partition,
                kind="proposal.created",
                subject_type="proposal",
                subject_id=proposal_id,
                payload={},
                now_us=created,
            )
            connection.execute(
                """
                INSERT INTO proposals(
                    id, partition, request_id, proposed_output_json, proposed_output_hash,
                    provenance_json, provenance_hash, status, created_at_us, status_sequence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    proposal_id,
                    partition,
                    request_id,
                    proposed.text,
                    proposed.digest,
                    provenance.text,
                    provenance.digest,
                    created,
                    status_sequence,
                ),
            )
        return proposal_id

    def submit_proposal(
        self,
        partition: str,
        operation: str,
        input_value: object,
        *,
        candidate: Candidate,
    ) -> str:
        """Submit a candidate that the caller generated, as a pending proposal.

        The call writes one request row, one proposal row, and one
        ``proposal.created`` event. It never invokes the configured candidate
        source.

        Cement gives no idempotency. Each call writes a new proposal. Two calls
        with identical content write two proposals and return two different
        identifiers.

        Return the identifier of the new proposal.

        The call opens one transaction and binds whatever operation revision is
        current under that write lock. It captures no earlier revision, so a
        concurrent revision change cannot make it fail.

        Raise ``ValidationError`` for a rejected partition, operation, input
        value, or candidate. Raise ``NotFoundError`` when the partition holds no
        such operation.

        A failure before the commit writes nothing. If the commit itself
        succeeds and then fails, the call raises and returns no identifier while
        the three rows stay durable. Recover by listing the partition's pending
        proposals; never retry, because a retry writes a second proposal.
        """
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        input_json = canonicalize(input_value)
        proposed, provenance = self._canonical_candidate(candidate)
        return self._persist_proposal(
            partition=partition,
            operation=operation,
            expected_revision=None,
            request_id=_new_id("req"),
            input_json=input_json,
            proposed=proposed,
            provenance=provenance,
        )

    def propose(
        self,
        partition: str,
        operation: str,
        input_value: object,
    ) -> str:
        """Ask the configured candidate source for a candidate, then submit it.

        Cement writes one request row, one proposal row, one
        ``proposal.created`` event, and no other row. That count covers Cement's
        own transaction only; a source that reenters the same ``System`` writes
        on its own. The source runs outside every transaction
        this call holds, because the source executes adapter code that the caller
        supplies. A source that reenters the same ``System`` opens its own
        transaction, which no library can prevent.

        Cement gives no idempotency. Each call writes a new proposal. Two calls
        with identical content write two proposals and return two different
        identifiers.

        Return the identifier of the new proposal.

        Raise ``ValidationError`` for a rejected partition, operation, or input
        value. Raise ``StateError`` when no candidate source is configured. Raise
        ``NotFoundError`` when the partition holds no such operation. Raise
        ``CandidateSourceError`` when the source fails; that error carries no
        detail from the source. Raise ``StateError`` when the operation revision
        changes during generation.

        A failure before the commit writes nothing. If the commit itself
        succeeds and then fails, the call raises and returns no identifier while
        the three rows stay durable. Recover by listing the partition's pending
        proposals; never retry, because a retry writes a second proposal.
        """
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        input_json = canonicalize(input_value)
        source = self.candidate_source
        if source is None:
            raise StateError("candidate source is not configured")
        revision = self._submission_revision(partition, operation)
        request_id = _new_id("req")
        try:
            candidate = source.propose(
                CandidateRequest(
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                    request_id=request_id,
                    input=input_json.value,
                )
            )
            generated = self._canonical_candidate(candidate)
        except Exception:
            generated = None
        # Raising outside the handler leaves __context__ itself empty, so no
        # adapter frame, class, or message survives into the caller's traceback.
        if generated is None:
            raise CandidateSourceError("candidate source failed") from None
        proposed, provenance = generated
        return self._persist_proposal(
            partition=partition,
            operation=operation,
            expected_revision=revision,
            request_id=request_id,
            input_json=input_json,
            proposed=proposed,
            provenance=provenance,
        )

    # -- routing + supervised fallback --------------------------------------

    def handle(
        self,
        partition: str,
        operation: str,
        input_value: object,
        *,
        request_id: str | None = None,
        retry_failed: bool = False,
    ) -> Outcome:
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if type(retry_failed) is not bool:
            raise ValidationError("retry_failed must be a boolean")
        request_id = _request_id(_new_id("req") if request_id is None else request_id)
        input_json = canonicalize(input_value)
        now = self._now()
        owner = _new_id("lease")

        with self.store.transaction(write=True) as connection:
            request = connection.execute(
                "SELECT * FROM requests WHERE partition = ? AND id = ?",
                (partition, request_id),
            ).fetchone()
            if request is not None:
                if (
                    request["partition"] != partition
                    or request["operation"] != operation
                    or request["input_json"] != input_json.text
                ):
                    raise ConflictError("request_id is already bound to different immutable content")
                if not self._request_revision_is_current(request, connection):
                    return self._outcome(request, now, connection)
                if request["status"] == "generating" and int(request["lease_until_us"] or 0) <= now:
                    connection.execute(
                        """
                        UPDATE requests
                        SET lease_owner = ?, lease_until_us = ?, attempts = attempts + 1,
                            updated_at_us = ?
                        WHERE partition = ? AND id = ? AND status = 'generating'
                        """,
                        (owner, now + self._lease_us, now, partition, request_id),
                    )
                    revision = int(request["operation_revision"])
                elif request["status"] == "failed" and retry_failed:
                    connection.execute(
                        """
                        UPDATE requests
                        SET status = 'generating', error_code = NULL, lease_owner = ?,
                            lease_until_us = ?, attempts = attempts + 1, updated_at_us = ?
                        WHERE partition = ? AND id = ? AND status = 'failed'
                        """,
                        (owner, now + self._lease_us, now, partition, request_id),
                    )
                    revision = int(request["operation_revision"])
                else:
                    return self._outcome(request, now, connection)
            else:
                registered = connection.execute(
                    "SELECT * FROM operations WHERE partition = ? AND name = ?",
                    (partition, operation),
                ).fetchone()
                if registered is None:
                    raise NotFoundError("operation is not registered in this partition")
                revision = int(registered["revision"])
                artifacts = connection.execute(
                    """
                    SELECT * FROM artifacts
                    WHERE partition = ? AND operation = ? AND operation_revision = ?
                      AND input_hash = ? AND status = 'promoted'
                    """,
                    (partition, operation, revision, input_json.digest),
                ).fetchall()
                if len(artifacts) > 1:
                    ids = [str(row["id"]) for row in artifacts]
                    connection.executemany(
                        """
                        UPDATE artifacts SET status = 'suspended', promotion_hash = NULL,
                            status_reason = ? WHERE id = ?
                        """,
                        [("ambiguous active scope", artifact_id) for artifact_id in ids],
                    )
                    _event(
                        connection,
                        partition=partition,
                        kind="artifact.ambiguity_quarantined",
                        subject_type="operation",
                        subject_id=f"{partition}/{operation}@{revision}",
                        payload={"artifact_ids": ids},
                        now_us=now,
                    )
                    artifacts = []
                if artifacts:
                    artifact_row = artifacts[0]
                    try:
                        artifact = self._artifact_from_row(artifact_row)
                        self._validate_promoted(connection, artifact_row)
                        execution = execute(
                            artifact,
                            partition=partition,
                            operation=operation,
                            operation_revision=revision,
                            input_json=input_json,
                        )
                    except (IntegrityError, ValidationError):
                        connection.execute(
                            """
                            UPDATE artifacts
                            SET status = 'suspended', promotion_hash = NULL,
                                status_reason = 'runtime integrity failure'
                            WHERE id = ? AND status = 'promoted'
                            """,
                            (artifact_row["id"],),
                        )
                        _event(
                            connection,
                            partition=partition,
                            kind="artifact.integrity_quarantined",
                            subject_type="artifact",
                            subject_id=str(artifact_row["id"]),
                            payload={},
                            now_us=now,
                        )
                    else:
                        if execution.matched:
                            output_json = canonicalize(execution.output)
                            connection.execute(
                                """
                                INSERT INTO requests(
                                    id, partition, operation, operation_revision, input_json,
                                    input_hash, status, output_json, source_kind, artifact_id,
                                    created_at_us, updated_at_us
                                ) VALUES (?, ?, ?, ?, ?, ?, 'resolved', ?, 'artifact', ?, ?, ?)
                                """,
                                (
                                    request_id,
                                    partition,
                                    operation,
                                    revision,
                                    input_json.text,
                                    input_json.digest,
                                    output_json.text,
                                    artifact_row["id"],
                                    now,
                                    now,
                                ),
                            )
                            _event(
                                connection,
                                partition=partition,
                                kind="request.resolved_by_artifact",
                                subject_type="request",
                                subject_id=request_id,
                                payload={"artifact_id": str(artifact_row["id"])},
                                now_us=now,
                            )
                            return Resolved(
                                request_id=request_id,
                                output=output_json.value,
                                source="artifact",
                                artifact_id=str(artifact_row["id"]),
                            )
                connection.execute(
                    """
                    INSERT INTO requests(
                        id, partition, operation, operation_revision, input_json, input_hash,
                        status, lease_owner, lease_until_us, created_at_us, updated_at_us
                    ) VALUES (?, ?, ?, ?, ?, ?, 'generating', ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        partition,
                        operation,
                        revision,
                        input_json.text,
                        input_json.digest,
                        owner,
                        now + self._lease_us,
                        now,
                        now,
                    ),
                )

        if self.candidate_source is None:
            return self._fail_generation(partition, request_id, owner, "candidate_source_unavailable")
        try:
            candidate = self.candidate_source.propose(
                CandidateRequest(
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                    request_id=request_id,
                    input=input_json.value,
                )
            )
            proposed = canonicalize(candidate.output)
            provenance = canonicalize(dict(candidate.provenance), max_bytes=65_536)
            if type(provenance.value) is not dict:
                raise ValidationError("candidate provenance must be a JSON object")
        except CandidateSourceError:
            return self._fail_generation(partition, request_id, owner, "candidate_source_error")
        except Exception:
            # Custom adapter failures remain inert and do not leak details into audit data.
            return self._fail_generation(partition, request_id, owner, "candidate_source_error")

        proposal_id = _new_id("prop")
        completed = self._now()
        with self.store.transaction(write=True) as connection:
            request = connection.execute(
                "SELECT * FROM requests WHERE partition = ? AND id = ?",
                (partition, request_id),
            ).fetchone()
            if request is None:
                raise IntegrityError("reserved request disappeared")
            if request["status"] != "generating" or request["lease_owner"] != owner:
                return self._outcome(request, completed, connection)
            if not self._request_revision_is_current(request, connection):
                connection.execute(
                    """
                    UPDATE requests
                    SET status = 'failed', error_code = 'operation_revised',
                        lease_owner = NULL, lease_until_us = NULL, updated_at_us = ?
                    WHERE partition = ? AND id = ? AND status = 'generating'
                      AND lease_owner = ?
                    """,
                    (completed, partition, request_id, owner),
                )
                refreshed = connection.execute(
                    "SELECT * FROM requests WHERE partition = ? AND id = ?",
                    (partition, request_id),
                ).fetchone()
                if refreshed is None:
                    raise IntegrityError("invalidated request disappeared")
                return self._outcome(refreshed, completed, connection)
            status_sequence = _event(
                connection,
                partition=partition,
                kind="proposal.created",
                subject_type="proposal",
                subject_id=proposal_id,
                payload={"request_id": request_id},
                now_us=completed,
            )
            connection.execute(
                """
                INSERT INTO proposals(
                    id, partition, request_id, proposed_output_json, proposed_output_hash,
                    provenance_json, provenance_hash, status, created_at_us, status_sequence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    proposal_id,
                    partition,
                    request_id,
                    proposed.text,
                    proposed.digest,
                    provenance.text,
                    provenance.digest,
                    completed,
                    status_sequence,
                ),
            )
            connection.execute(
                """
                UPDATE requests
                SET status = 'pending', proposal_id = ?, lease_owner = NULL,
                    lease_until_us = NULL, updated_at_us = ?
                WHERE partition = ? AND id = ?
                """,
                (proposal_id, completed, partition, request_id),
            )
        return ReviewRequired(request_id=request_id, proposal_id=proposal_id)

    def _fail_generation(
        self, partition: str, request_id: str, owner: str, code: str
    ) -> Outcome:
        now = self._now()
        with self.store.transaction(write=True) as connection:
            request = connection.execute(
                "SELECT * FROM requests WHERE partition = ? AND id = ?",
                (partition, request_id),
            ).fetchone()
            if request is None:
                raise IntegrityError("reserved request disappeared")
            if request["status"] != "generating" or request["lease_owner"] != owner:
                return self._outcome(request, now, connection)
            connection.execute(
                """
                UPDATE requests
                SET status = 'failed', error_code = ?, lease_owner = NULL,
                    lease_until_us = NULL, updated_at_us = ?
                WHERE partition = ? AND id = ?
                """,
                (code, now, partition, request_id),
            )
            _event(
                connection,
                partition=str(request["partition"]),
                kind="request.fallback_failed",
                subject_type="request",
                subject_id=request_id,
                payload={"code": code},
                now_us=now,
            )
        return FallbackFailed(request_id=request_id, code=code)

    def _outcome(
        self,
        request: sqlite3.Row,
        now_us: int,
        connection: sqlite3.Connection,
    ) -> Outcome:
        status = str(request["status"])
        request_id = str(request["id"])
        if status != "rejected" and not self._request_revision_is_current(request, connection):
            return ReconciliationRequired(
                request_id=request_id,
                reason="operation revision changed; submit a new request ID",
                artifact_id=str(request["artifact_id"]) if request["artifact_id"] else None,
                example_id=str(request["example_id"]) if request["example_id"] else None,
            )
        if status == "resolved":
            if request["output_json"] is None or request["source_kind"] is None:
                raise IntegrityError("resolved request is incomplete")
            stored_output = str(request["output_json"])
            output: JSONValue = None
            if request["source_kind"] == "artifact":
                source_kind: Literal["artifact", "confirmed"] = "artifact"
                artifact_id = str(request["artifact_id"] or "")
                artifact_row = connection.execute(
                    "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
                ).fetchone()
                valid = False
                if artifact_row is not None and artifact_row["status"] == "promoted":
                    try:
                        artifact = self._artifact_from_row(artifact_row)
                        self._validate_promoted(connection, artifact_row)
                        input_json = parse_json(str(request["input_json"]))
                        execution = execute(
                            artifact,
                            partition=str(request["partition"]),
                            operation=str(request["operation"]),
                            operation_revision=int(request["operation_revision"]),
                            input_json=input_json,
                        )
                        valid = (
                            execution.matched
                            and canonicalize(execution.output).text == stored_output
                        )
                        if valid:
                            output = execution.output
                    except (IntegrityError, ValidationError):
                        valid = False
                if not valid:
                    return ReconciliationRequired(
                        request_id=request_id,
                        reason="artifact is no longer active and integrity-valid",
                        artifact_id=artifact_id or None,
                    )
            elif request["source_kind"] == "confirmed":
                source_kind = "confirmed"
                example_id = str(request["example_id"] or "")
                example = connection.execute(
                    """
                    SELECT e.*, x.example_id AS revoked
                    FROM examples AS e
                    LEFT JOIN example_revocations AS x ON x.example_id = e.id
                    WHERE e.id = ?
                    """,
                    (example_id,),
                ).fetchone()
                valid = False
                if example is not None and example["revoked"] is None:
                    assessment = self._assess_examples(
                        [example], CompilePolicy(2, 1, 0)
                    )
                    valid = not assessment["integrity_failures"] and (
                        example["partition"] == request["partition"]
                        and example["operation"] == request["operation"]
                        and example["operation_revision"] == request["operation_revision"]
                        and example["input_json"] == request["input_json"]
                        and example["output_json"] == stored_output
                    )
                    if valid:
                        output = parse_json(str(example["output_json"])).value
                if not valid:
                    return ReconciliationRequired(
                        request_id=request_id,
                        reason="confirmed example is missing, revoked, or inconsistent",
                        example_id=example_id or None,
                    )
            else:
                raise IntegrityError("resolved request has an unknown source kind")
            return Resolved(
                request_id=request_id,
                output=output,
                source=source_kind,
                artifact_id=str(request["artifact_id"]) if request["artifact_id"] else None,
                example_id=str(request["example_id"]) if request["example_id"] else None,
            )
        if status == "pending":
            if not request["proposal_id"]:
                raise IntegrityError("pending request has no proposal")
            return ReviewRequired(request_id=request_id, proposal_id=str(request["proposal_id"]))
        if status == "generating":
            remaining = max(0, int(request["lease_until_us"] or now_us) - now_us)
            if remaining == 0:
                return FallbackFailed(
                    request_id=request_id,
                    code="generation_lease_expired",
                )
            return InProgress(
                request_id=request_id,
                retry_after_seconds=max(1, (remaining + 999_999) // 1_000_000),
            )
        if status == "failed":
            return FallbackFailed(request_id=request_id, code=str(request["error_code"] or "unknown"))
        if status == "rejected":
            if not request["proposal_id"]:
                raise IntegrityError("rejected request has no proposal")
            return Rejected(request_id=request_id, proposal_id=str(request["proposal_id"]))
        raise IntegrityError(f"unknown request status: {status}")

    @staticmethod
    def _request_revision_is_current(
        request: sqlite3.Row,
        connection: sqlite3.Connection,
    ) -> bool:
        operation = connection.execute(
            "SELECT revision FROM operations WHERE partition = ? AND name = ?",
            (request["partition"], request["operation"]),
        ).fetchone()
        return operation is not None and int(operation["revision"]) == int(
            request["operation_revision"]
        )

    @staticmethod
    def _proposal_content(
        binding: _ProposalBinding,
    ) -> tuple[CanonicalJSON, CanonicalJSON, CanonicalJSON]:
        # The request-derived input arrives through the binding record; every other
        # column is the proposal's own. A stored value that will not parse is ledger
        # corruption, so it reports as IntegrityError rather than escaping as the
        # ValidationError that parse_json raises for caller input.
        row = binding.row
        try:
            input_json = parse_json(binding.input_json)
            proposed = parse_json(str(row["proposed_output_json"]))
            provenance = parse_json(str(row["provenance_json"]), max_bytes=65_536)
        except ValidationError as exc:
            raise IntegrityError("stored proposal content is not valid JSON") from exc
        if input_json.digest != binding.input_hash:
            raise IntegrityError("proposal request input digest mismatch")
        if proposed.digest != row["proposed_output_hash"]:
            raise IntegrityError("proposal output digest mismatch")
        if provenance.digest != row["provenance_hash"]:
            raise IntegrityError("proposal provenance digest mismatch")
        return input_json, proposed, provenance

    @staticmethod
    def _validate_proposal_shape(row: sqlite3.Row) -> None:
        status = str(row["status"])
        final_present = row["final_output_json"] is not None
        final_hash_present = row["final_output_hash"] is not None
        review_present = (
            row["reviewer"] is not None
            and row["review_note"] is not None
            and row["reviewed_at_us"] is not None
        )
        if status == "pending":
            valid = not final_present and not final_hash_present and not review_present
            request_status = "pending"
        elif status == "rejected":
            valid = not final_present and not final_hash_present and review_present
            request_status = "rejected"
        elif status in {"accepted", "corrected"}:
            valid = final_present and final_hash_present and review_present
            request_status = "resolved"
        else:
            raise IntegrityError("proposal has an unknown status")
        if not valid:
            raise IntegrityError("proposal fields do not match its status")
        if "bound_proposal_id" in row.keys() and (
            row["bound_proposal_id"] != row["id"]
            or row["bound_request_status"] != request_status
        ):
            raise IntegrityError("proposal and request states are inconsistent")

    def request_status(self, partition: str, request_id: str) -> Outcome:
        """Poll an existing request without resupplying its immutable input."""

        partition = _name(partition, "partition")
        request_id = _request_id(request_id)
        now = self._now()
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM requests WHERE partition = ? AND id = ?",
                (partition, request_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("request does not exist in this partition")
            return self._outcome(row, now, connection)

    # -- supervision ---------------------------------------------------------

    def get_proposal(self, partition: str, proposal_id: str) -> ProposalView:
        partition = _name(partition, "partition")
        proposal_id = _request_id(proposal_id)
        with self.store.transaction() as connection:
            binding = _proposal_binding(
                connection,
                partition=partition,
                proposal_id=proposal_id,
            )
            if binding is None:
                raise NotFoundError("proposal does not exist in this partition")
            row = binding.row
            self._validate_proposal_shape(row)
            if row["status"] != "pending":
                raise StateError(f"proposal is already {row['status']}")
            if (
                binding.request_status != "pending"
                or row["bound_proposal_id"] != proposal_id
            ):
                raise IntegrityError("pending proposal is not bound to a pending request")
            input_json, proposed, provenance = self._proposal_content(binding)
            return ProposalView(
                id=proposal_id,
                partition=partition,
                operation=binding.operation,
                operation_revision=binding.operation_revision,
                input=input_json.value,
                proposed_output=proposed.value,
                provenance=provenance.value,
                created_at_us=int(row["created_at_us"]),
            )

    def proposal(self, partition: str, proposal_id: str) -> dict[str, JSONValue]:
        """Inspect pending or historical proposal state and bound provenance."""

        partition = _name(partition, "partition")
        proposal_id = _request_id(proposal_id)
        with self.store.transaction() as connection:
            binding = _proposal_binding(
                connection,
                partition=partition,
                proposal_id=proposal_id,
            )
            if binding is None:
                raise NotFoundError("proposal does not exist in this partition")
            return self._proposal_record(binding)

    def proposals(
        self,
        partition: str,
        *,
        status: str = "pending",
        after_sequence: int = 0,
        limit: int = 100,
    ) -> list[dict[str, JSONValue]]:
        """Monotonic proposal-state feed ordered by audit transition sequence."""

        partition = _name(partition, "partition")
        allowed = {"all", "pending", "accepted", "corrected", "rejected"}
        if type(status) is not str or status not in allowed:
            raise ValidationError(f"proposal status must be one of {sorted(allowed)!r}")
        _bounded_int(
            after_sequence,
            "after_sequence",
            minimum=0,
            maximum=2**63 - 1,
        )
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)
        selected_status = None if status == "all" else status
        with self.store.transaction() as connection:
            bindings = _proposal_bindings(
                connection,
                partition=partition,
                selection=_ProposalFeed(
                    status=selected_status,
                    after_sequence=after_sequence,
                    limit=limit,
                ),
            )
            return [self._proposal_record(binding) for binding in bindings.rows]

    def _proposal_record(self, binding: _ProposalBinding) -> dict[str, JSONValue]:
        row = binding.row
        self._validate_proposal_shape(row)
        input_json, proposed, provenance = self._proposal_content(binding)
        try:
            final_output = (
                parse_json(str(row["final_output_json"]))
                if row["final_output_json"] is not None
                else None
            )
        except ValidationError as exc:
            raise IntegrityError("stored proposal content is not valid JSON") from exc
        if final_output is not None and final_output.digest != row["final_output_hash"]:
            raise IntegrityError("proposal final output digest mismatch")
        return {
            "created_at_us": int(row["created_at_us"]),
            "final_output": final_output.value if final_output is not None else None,
            "id": str(row["id"]),
            "input": input_json.value,
            "operation": binding.operation,
            "operation_revision": binding.operation_revision,
            "proposed_output": proposed.value,
            "provenance": provenance.value,
            "review_note": str(row["review_note"]) if row["review_note"] is not None else None,
            "reviewed_at_us": (
                int(row["reviewed_at_us"]) if row["reviewed_at_us"] is not None else None
            ),
            "reviewer": str(row["reviewer"]) if row["reviewer"] is not None else None,
            "sequence": int(row["status_sequence"]),
            "status": str(row["status"]),
        }

    def review(
        self,
        partition: str,
        proposal_id: str,
        *,
        reviewer: str,
        decision: str,
        corrected_output: object = _UNSET,
        note: str = "",
    ) -> ReviewResult:
        partition = _name(partition, "partition")
        proposal_id = _request_id(proposal_id)
        reviewer = _text(reviewer, "reviewer", maximum=256)
        note = _text(note, "note", maximum=2_048, allow_empty=True)
        if type(decision) is not str or decision not in {"accept", "correct", "reject"}:
            raise ValidationError("decision must be accept, correct, or reject")
        if decision == "correct" and corrected_output is _UNSET:
            raise ValidationError("correct requires corrected_output")
        if decision != "correct" and corrected_output is not _UNSET:
            raise ValidationError("corrected_output is valid only with decision='correct'")
        now = self._now()
        with self.store.transaction(write=True) as connection:
            binding = _proposal_binding(
                connection,
                partition=partition,
                proposal_id=proposal_id,
            )
            if binding is None:
                raise NotFoundError("proposal does not exist in this partition")
            row = binding.row
            if row["status"] != "pending":
                raise StateError(f"proposal is already {row['status']}")
            current = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, binding.operation),
            ).fetchone()
            if (
                decision != "reject"
                and (
                    current is None
                    or int(current["revision"]) != binding.operation_revision
                )
            ):
                raise StateError(
                    "proposal belongs to an obsolete operation revision; reject it or use a new request"
                )
            input_json, proposed, _ = self._proposal_content(binding)
            if decision == "reject":
                proposal_update = connection.execute(
                    """
                    UPDATE proposals
                    SET status = 'rejected', reviewer = ?, review_note = ?, reviewed_at_us = ?
                    WHERE id = ? AND status = 'pending'
                    """,
                    (reviewer, note, now, proposal_id),
                )
                request_update_count = _write_proposal_request_status(
                    connection,
                    binding=binding,
                    status="rejected",
                    final=None,
                    example_id=None,
                    now_us=now,
                )
                if proposal_update.rowcount != 1 or request_update_count != 1:
                    raise IntegrityError("proposal rejection transition lost its state binding")
                status_sequence = _event(
                    connection,
                    partition=partition,
                    kind="proposal.rejected",
                    subject_type="proposal",
                    subject_id=proposal_id,
                    payload={"reviewer": reviewer},
                    now_us=now,
                )
                sequence_update = connection.execute(
                    "UPDATE proposals SET status_sequence = ? WHERE id = ? AND status = 'rejected'",
                    (status_sequence, proposal_id),
                )
                if sequence_update.rowcount != 1:
                    raise IntegrityError("proposal rejection sequence was not bound")
                return ReviewResult(
                    proposal_id=proposal_id,
                    status="rejected",
                    example_id=None,
                    output=None,
                )

            final = (
                canonicalize(corrected_output)
                if decision == "correct"
                else proposed
            )
            example_id = _new_id("ex")
            proposal_status: Literal["accepted", "corrected"] = (
                "corrected" if decision == "correct" else "accepted"
            )
            receipt_value: dict[str, JSONValue] = {
                "confirmed_at_us": now,
                "example_id": example_id,
                "format": "cement-confirmation-v1",
                "input": input_json.value,
                "note": note,
                "operation": str(row["operation"]),
                "operation_revision": int(row["operation_revision"]),
                "output": final.value,
                "partition": partition,
                "proposal_id": proposal_id,
                "resolution": proposal_status,
                "reviewer": reviewer,
            }
            receipt = canonicalize(receipt_value, max_bytes=_RECEIPT_MAX_BYTES)
            proposal_update = connection.execute(
                """
                UPDATE proposals
                SET status = ?, final_output_json = ?, final_output_hash = ?,
                    reviewer = ?, review_note = ?, reviewed_at_us = ?
                WHERE partition = ? AND id = ? AND status = 'pending'
                """,
                (
                    proposal_status,
                    final.text,
                    final.digest,
                    reviewer,
                    note,
                    now,
                    partition,
                    proposal_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO examples(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, reviewer, origin, proposal_id,
                    receipt_json, receipt_hash, confirmed_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    example_id,
                    partition,
                    binding.operation,
                    binding.operation_revision,
                    input_json.text,
                    input_json.digest,
                    final.text,
                    final.digest,
                    reviewer,
                    proposal_status,
                    proposal_id,
                    receipt.text,
                    receipt.digest,
                    now,
                ),
            )
            conflicting_artifacts = connection.execute(
                """
                SELECT id FROM artifacts
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND input_hash = ? AND input_json = ? AND output_json <> ?
                  AND status = 'promoted'
                """,
                (
                    partition,
                    binding.operation,
                    binding.operation_revision,
                    input_json.digest,
                    input_json.text,
                    final.text,
                ),
            ).fetchall()
            quarantined = tuple(str(item["id"]) for item in conflicting_artifacts)
            if quarantined:
                connection.executemany(
                    """
                    UPDATE artifacts
                    SET status = 'suspended', promotion_hash = NULL,
                        status_reason = 'new confirmed counterexample'
                    WHERE id = ? AND status = 'promoted'
                    """,
                    [(artifact_id,) for artifact_id in quarantined],
                )
                for artifact_id in quarantined:
                    _event(
                        connection,
                        partition=partition,
                        kind="artifact.counterexample",
                        subject_type="artifact",
                        subject_id=artifact_id,
                        payload={"example_id": example_id, "proposal_id": proposal_id},
                        now_us=now,
                    )
            request_update_count = _write_proposal_request_status(
                connection,
                binding=binding,
                status="resolved",
                final=final,
                example_id=example_id,
                now_us=now,
            )
            if proposal_update.rowcount != 1 or request_update_count != 1:
                raise IntegrityError("proposal confirmation transition lost its state binding")
            status_sequence = _event(
                connection,
                partition=partition,
                kind=f"proposal.{proposal_status}",
                subject_type="proposal",
                subject_id=proposal_id,
                payload={
                    "example_id": example_id,
                    "receipt_hash": receipt.digest,
                    "reviewer": reviewer,
                    "suspended_artifact_ids": list(quarantined),
                },
                now_us=now,
            )
            sequence_update = connection.execute(
                "UPDATE proposals SET status_sequence = ? WHERE id = ? AND status = ?",
                (status_sequence, proposal_id, proposal_status),
            )
            if sequence_update.rowcount != 1:
                raise IntegrityError("proposal confirmation sequence was not bound")
        return ReviewResult(
            proposal_id=proposal_id,
            status=proposal_status,
            example_id=example_id,
            output=final.value,
        )

    # -- deterministic compiler ---------------------------------------------

    def _project_current_build(
        self,
        connection: sqlite3.Connection,
        operation_row: sqlite3.Row,
        input_hash: str,
        input_json: str,
    ) -> _CurrentBuild | _BlockedBuild:
        partition = str(operation_row["partition"])
        operation = str(operation_row["name"])
        revision = int(operation_row["revision"])
        policy_json = str(operation_row["policy_json"])
        policy_hash = str(operation_row["policy_hash"])
        policy = _policy_from_text(policy_json)
        if canonicalize(policy.as_json(), max_bytes=16_384).digest != policy_hash:
            raise IntegrityError("operation policy digest mismatch")

        canonical_input = parse_json(input_json)
        if canonical_input.text != input_json or canonical_input.digest != input_hash:
            raise IntegrityError("canonical input does not match its stored digest")
        reviewer_count = self._active_reviewer_count(
            connection,
            partition=partition,
            operation=operation,
            revision=revision,
            input_hash=input_hash,
            input_text=input_json,
        )
        assessment = self._assess_examples(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=input_hash,
                input_text=input_json,
            ),
            policy,
            reviewer_count=reviewer_count,
        )
        if assessment["integrity_failures"]:
            raise IntegrityError(str(assessment["integrity_failures"][0]))
        reasons = tuple(str(reason) for reason in assessment["policy_failures"])
        support = int(assessment["support"])
        reviewer_count = int(assessment["reviewer_count"])
        span_seconds = int(assessment["span_seconds"])
        if reasons:
            return _BlockedBuild(
                reasons=reasons,
                support=support,
                reviewer_count=reviewer_count,
                span_seconds=span_seconds,
            )

        output_json = parse_json(str(assessment["output_text"]))
        try:
            artifact = build_exact_lookup(
                partition=partition,
                operation=operation,
                operation_revision=revision,
                input_value=canonical_input.value,
                output_value=output_json.value,
            )
        except ValidationError as exc:
            return _BlockedBuild(
                reasons=(f"artifact constraint: {exc}",),
                support=support,
                reviewer_count=reviewer_count,
                span_seconds=span_seconds,
            )
        snapshot = self._evidence_snapshot(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=input_hash,
                input_text=input_json,
                order_by_id=True,
            ),
            partition=partition,
            operation=operation,
            revision=revision,
            input_text=input_json,
        )
        return _CurrentBuild(
            input_json=canonical_input,
            output_json=output_json,
            artifact=artifact,
            policy_json=policy_json,
            policy_hash=policy_hash,
            evidence_snapshot_hash=snapshot,
            support=support,
            reviewer_count=reviewer_count,
            span_seconds=span_seconds,
            build_hash=build_digest(
                artifact_digest=artifact.digest,
                policy_digest=policy_hash,
                evidence_snapshot_digest=snapshot,
                support=support,
                reviewer_count=reviewer_count,
                span_seconds=span_seconds,
            ),
        )

    def _current_build_projections(
        self,
        connection: sqlite3.Connection,
        operation_row: sqlite3.Row,
    ) -> Iterator[tuple[str, str, _CurrentBuild | _BlockedBuild]]:
        """Enumerate compile's exact current scopes without writing."""

        partition = str(operation_row["partition"])
        operation = str(operation_row["name"])
        revision = int(operation_row["revision"])
        groups = connection.execute(
            """
            SELECT e.input_hash, e.input_json
            FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND x.example_id IS NULL
            GROUP BY e.input_hash, e.input_json
            ORDER BY e.input_hash, e.input_json
            """,
            (partition, operation, revision),
        )
        canonical_inputs: dict[str, str] = {}
        for group in groups:
            input_hash = str(group["input_hash"])
            input_text = str(group["input_json"])
            previous = canonical_inputs.get(input_hash)
            if previous is not None and previous != input_text:
                raise IntegrityError("one input digest maps to multiple canonical inputs")
            canonical_inputs[input_hash] = input_text
            yield (
                input_hash,
                input_text,
                self._project_current_build(
                    connection,
                    operation_row,
                    input_hash,
                    input_text,
                ),
            )

    def compile(
        self,
        partition: str,
        operation: str,
        *,
        compiled_by: str = "local-system",
    ) -> CompileResult:
        """Snapshot eligible examples into draft exact-lookup builds.

        The compiler performs no model call and no generalization. Repetition
        chooses whether an already-confirmed exact behavior is mature enough to
        become a build; it never invents a wider predicate.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        compiled_by = _text(compiled_by, "compiled_by", maximum=256)
        now = self._now()
        created: list[str] = []
        existing: list[str] = []
        blocked: list[dict[str, JSONValue]] = []
        with self.store.transaction(write=True) as connection:
            registered = connection.execute(
                "SELECT * FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = int(registered["revision"])
            for input_hash, input_text, projection in self._current_build_projections(
                connection,
                registered,
            ):
                if isinstance(projection, _BlockedBuild):
                    blocked.append(
                        {
                            "input_hash": input_hash,
                            "reasons": list(projection.reasons),
                            "support": projection.support,
                        }
                    )
                    continue
                found = connection.execute(
                    """
                    SELECT id FROM artifacts
                    WHERE build_hash = ? AND status IN ('building', 'draft', 'verified', 'promoted')
                    ORDER BY id LIMIT 1
                    """,
                    (projection.build_hash,),
                ).fetchone()
                if found is not None:
                    existing.append(str(found["id"]))
                    continue
                artifact_id = _new_id("art")
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, partition, operation, operation_revision, input_json, input_hash,
                        output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                        build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                        support, reviewer_count, span_seconds, created_at_us
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'building', ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        partition,
                        operation,
                        revision,
                        projection.input_json.text,
                        projection.input_json.digest,
                        projection.output_json.text,
                        projection.output_json.digest,
                        projection.artifact.text,
                        projection.artifact.digest,
                        projection.artifact.scope_digest,
                        projection.build_hash,
                        projection.policy_json,
                        projection.policy_hash,
                        projection.evidence_snapshot_hash,
                        projection.support,
                        projection.reviewer_count,
                        projection.span_seconds,
                        now,
                    ),
                )
                inserted = connection.execute(
                    """
                    INSERT INTO artifact_evidence(artifact_id, example_id)
                    SELECT ?, e.id FROM examples AS e
                    LEFT JOIN example_revocations AS x ON x.example_id = e.id
                    WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
                      AND e.input_hash = ? AND e.input_json = ? AND x.example_id IS NULL
                    ORDER BY e.id
                    """,
                    (
                        artifact_id,
                        partition,
                        operation,
                        revision,
                        input_hash,
                        input_text,
                    ),
                )
                if inserted.rowcount != projection.support:
                    raise IntegrityError(
                        "artifact evidence insertion count changed during compilation"
                    )
                connection.execute(
                    "UPDATE artifacts SET status = 'draft' WHERE id = ? AND status = 'building'",
                    (artifact_id,),
                )
                _event(
                    connection,
                    partition=partition,
                    kind="artifact.compiled",
                    subject_type="artifact",
                    subject_id=artifact_id,
                    payload={
                        "artifact_hash": projection.artifact.digest,
                        "build_hash": projection.build_hash,
                        "evidence_snapshot_hash": projection.evidence_snapshot_hash,
                        "scope_hash": projection.artifact.scope_digest,
                        "support": projection.support,
                        "compiled_by": compiled_by,
                    },
                    now_us=now,
                )
                created.append(artifact_id)
        return CompileResult(
            created=tuple(created),
            existing=tuple(existing),
            blocked=tuple(blocked),
        )

    def _assess_examples(
        self,
        evidence: Iterable[sqlite3.Row],
        policy: CompilePolicy,
        *,
        reviewer_count: int | None = None,
    ) -> dict[str, Any]:
        integrity: list[str] = []
        reviewers: set[str] = set()
        support = 0
        first_input: str | None = None
        first_output: str | None = None
        input_conflict = False
        output_conflict = False
        earliest: int | None = None
        latest: int | None = None

        def integrity_failure(message: str) -> None:
            if len(integrity) < 16:
                integrity.append(message)

        for row in evidence:
            support += 1
            try:
                input_json = parse_json(str(row["input_json"]))
                output_json = parse_json(str(row["output_json"]))
                receipt = parse_json(
                    str(row["receipt_json"]), max_bytes=_RECEIPT_MAX_BYTES
                )
            except ValidationError as exc:
                integrity_failure(
                    f"example {row['id']} contains invalid canonical JSON: {exc}"
                )
                continue
            if input_json.digest != row["input_hash"] or output_json.digest != row["output_hash"]:
                integrity_failure(f"example {row['id']} content digest mismatch")
            if receipt.digest != row["receipt_hash"]:
                integrity_failure(f"example {row['id']} receipt digest mismatch")
            receipt_value = receipt.value
            if type(receipt_value) is not dict:
                integrity_failure(f"example {row['id']} receipt is not an object")
            else:
                bound = {
                    "example_id": row["id"],
                    "partition": row["partition"],
                    "operation": row["operation"],
                    "operation_revision": row["operation_revision"],
                    "reviewer": row["reviewer"],
                    "confirmed_at_us": row["confirmed_at_us"],
                }
                if any(receipt_value.get(key) != value for key, value in bound.items()):
                    integrity_failure(f"example {row['id']} receipt binding mismatch")
                try:
                    if canonicalize(receipt_value.get("input")).text != input_json.text:
                        integrity_failure(f"example {row['id']} receipt input mismatch")
                    if canonicalize(receipt_value.get("output")).text != output_json.text:
                        integrity_failure(f"example {row['id']} receipt output mismatch")
                except ValidationError:
                    integrity_failure(f"example {row['id']} receipt payload is invalid")
            if first_input is None:
                first_input = input_json.text
            elif first_input != input_json.text:
                input_conflict = True
            if first_output is None:
                first_output = output_json.text
            elif first_output != output_json.text:
                output_conflict = True
            if reviewer_count is None and len(reviewers) < policy.min_reviewers:
                reviewers.add(str(row["reviewer"]))
            timestamp = int(row["confirmed_at_us"])
            earliest = timestamp if earliest is None else min(earliest, timestamp)
            latest = timestamp if latest is None else max(latest, timestamp)

        span_seconds = (
            (latest - earliest) // 1_000_000
            if earliest is not None and latest is not None and support >= 2
            else 0
        )
        policy_failures: list[str] = []
        if input_conflict:
            integrity_failure("evidence hash collision bound multiple canonical inputs")
        if output_conflict:
            policy_failures.append("confirmed outputs conflict")
        if support < policy.min_confirmations:
            policy_failures.append(
                f"support {support} is below required {policy.min_confirmations}"
            )
        effective_reviewer_count = (
            len(reviewers) if reviewer_count is None else reviewer_count
        )
        if effective_reviewer_count < policy.min_reviewers:
            policy_failures.append(
                f"reviewers {effective_reviewer_count} is below required {policy.min_reviewers}"
            )
        if span_seconds < policy.min_span_seconds:
            policy_failures.append(
                f"span {span_seconds}s is below required {policy.min_span_seconds}s"
            )
        return {
            "integrity_failures": integrity,
            "policy_failures": policy_failures,
            "reviewer_count": effective_reviewer_count,
            "span_seconds": span_seconds,
            "support": support,
            "output_text": first_output,
        }

    @staticmethod
    def _active_evidence(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        revision: int,
        input_hash: str,
        input_text: str,
        order_by_id: bool = False,
    ) -> sqlite3.Cursor:
        order = "e.id" if order_by_id else "e.confirmed_at_us, e.id"
        return connection.execute(
            f"""
            SELECT e.* FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND e.input_hash = ? AND e.input_json = ? AND x.example_id IS NULL
            ORDER BY {order}
            """,
            (partition, operation, revision, input_hash, input_text),
        )

    @staticmethod
    def _active_reviewer_count(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        revision: int,
        input_hash: str,
        input_text: str,
    ) -> int:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT e.reviewer) FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND e.input_hash = ? AND e.input_json = ? AND x.example_id IS NULL
            """,
            (partition, operation, revision, input_hash, input_text),
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _evidence_snapshot(
        evidence: Iterable[sqlite3.Row],
        *,
        partition: str,
        operation: str,
        revision: int,
        input_text: str,
    ) -> str:
        digest = hashlib.sha256()
        for part in (
            "cement-evidence-snapshot-v1",
            CANONICALIZER,
            partition,
            operation,
            str(revision),
            input_text,
        ):
            encoded = part.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
        for row in evidence:
            for part in (str(row["id"]), str(row["receipt_hash"])):
                encoded = part.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
        return digest.hexdigest()

    @staticmethod
    def _test_snapshot(
        connection: sqlite3.Connection,
        report_id: str,
    ) -> tuple[int, str]:
        digest = hashlib.sha256()
        label = b"cement-verification-tests-v1"
        digest.update(len(label).to_bytes(8, "big"))
        digest.update(label)
        count = 0
        for row in connection.execute(
            """
            SELECT test_key, example_id, passed, detail FROM artifact_tests
            WHERE report_id = ? ORDER BY test_key
            """,
            (report_id,),
        ):
            count += 1
            parts = (
                str(row["test_key"]),
                "none" if row["example_id"] is None else "example",
                "" if row["example_id"] is None else str(row["example_id"]),
                "1" if int(row["passed"]) else "0",
                str(row["detail"]),
            )
            for part in parts:
                encoded = part.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
        return count, digest.hexdigest()

    # -- promoted-set verification -----------------------------------------

    @staticmethod
    def _promoted_function_count(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
    ) -> int:
        row = connection.execute(
            """
            SELECT COUNT(*) AS entry_count FROM artifacts
            WHERE partition = ? AND operation = ? AND status = 'promoted'
            """,
            (partition, operation),
        ).fetchone()
        if row is None or type(row["entry_count"]) is not int:
            raise IntegrityError("promoted-set count is invalid")
        return int(row["entry_count"])

    @staticmethod
    def _promoted_function_rows(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
    ) -> list[sqlite3.Row]:
        return connection.execute(
            """
            SELECT * FROM artifacts
            WHERE partition = ? AND operation = ? AND status = 'promoted'
            ORDER BY operation_revision, input_hash, id
            """,
            (partition, operation),
        ).fetchall()

    @staticmethod
    def _latest_function_receipt_row(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        operation_revision: int,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT * FROM function_receipts
            WHERE partition = ? AND operation = ? AND operation_revision = ?
            ORDER BY sequence DESC LIMIT 1
            """,
            (partition, operation, operation_revision),
        ).fetchone()

    def _reconstruct_function_receipt(
        self,
        connection: sqlite3.Connection,
        receipt_row: sqlite3.Row,
    ) -> FunctionReconstruction:
        """Validate and rebuild one status-independent historical receipt."""

        receipt = _function_receipt_from_row(receipt_row)
        memberships = tuple(
            connection.execute(
                """
                SELECT * FROM function_memberships
                WHERE receipt_id = ? ORDER BY ordinal
                """,
                (receipt.id,),
            )
        )
        if len(memberships) != receipt.member_count:
            raise IntegrityError("function receipt membership count mismatch")

        input_hashes: list[str] = []
        for ordinal, membership in enumerate(memberships):
            if membership["ordinal"] != ordinal:
                raise IntegrityError("function receipt membership ordinals are not contiguous")
            try:
                _request_id(membership["artifact_id"])
                _request_id(membership["report_id"])
                membership_function_hash = _digest(
                    membership["function_hash"],
                    "stored membership function_hash",
                )
                input_hash = _digest(
                    membership["input_hash"], "stored membership input_hash"
                )
                _digest(membership["entry_seal"], "stored membership entry_seal")
            except (TypeError, ValidationError) as exc:
                raise IntegrityError(
                    f"function receipt membership {ordinal} has invalid scalar fields"
                ) from exc
            if membership_function_hash != receipt.function_hash:
                raise IntegrityError("function receipt membership function hash mismatch")
            input_hashes.append(input_hash)
        if input_hashes != sorted(input_hashes):
            raise IntegrityError("function receipt membership order is not canonical")
        if _membership_hash(memberships) != receipt.membership_hash:
            raise IntegrityError("function receipt membership digest mismatch")

        artifacts = tuple(
            connection.execute(
                """
                SELECT a.* FROM function_memberships AS m
                JOIN artifacts AS a ON a.id = m.artifact_id
                WHERE m.receipt_id = ? ORDER BY m.ordinal
                """,
                (receipt.id,),
            )
        )
        reports = tuple(
            connection.execute(
                """
                SELECT r.* FROM function_memberships AS m
                JOIN test_reports AS r
                  ON r.id = m.report_id AND r.artifact_id = m.artifact_id
                WHERE m.receipt_id = ? ORDER BY m.ordinal
                """,
                (receipt.id,),
            )
        )
        if len(artifacts) != receipt.member_count:
            raise IntegrityError("function receipt references a missing artifact")
        if len(reports) != receipt.member_count:
            raise IntegrityError(
                "function receipt references a missing or foreign report"
            )

        artifacts_by_id = {str(row["id"]): row for row in artifacts}
        reports_by_id = {str(row["id"]): row for row in reports}
        entries: list[FunctionEntry] = []
        for ordinal, membership in enumerate(memberships):
            artifact_id = str(membership["artifact_id"])
            report_id = str(membership["report_id"])
            artifact_row = artifacts_by_id[artifact_id]
            report_row = reports_by_id[report_id]
            if (
                artifact_row["partition"] != receipt.partition
                or artifact_row["operation"] != receipt.operation
                or artifact_row["operation_revision"] != receipt.operation_revision
                or artifact_row["policy_hash"] != receipt.policy_hash
            ):
                raise IntegrityError(
                    f"function receipt member {ordinal} scope binding mismatch"
                )
            try:
                artifact = self._artifact_from_row(artifact_row)
            except (IntegrityError, ValidationError) as exc:
                raise IntegrityError(
                    f"function receipt member {ordinal} artifact is invalid: {exc}"
                ) from exc
            try:
                if report_row["passed"] != 1:
                    raise IntegrityError("bound report is not passing")
                details = self._validate_report(
                    connection,
                    report_row,
                    verify_test_set=True,
                )
                if type(details.value) is not dict:
                    raise IntegrityError("bound report details are not an object")
                details_value = cast(dict[str, JSONValue], details.value)
                if details_value.get("scope_hash") != artifact_row["scope_hash"]:
                    raise IntegrityError("bound report scope mismatch")
                for field in (
                    "artifact_hash",
                    "build_hash",
                    "policy_hash",
                    "evidence_snapshot_hash",
                ):
                    if report_row[field] != artifact_row[field]:
                        raise IntegrityError(f"bound report {field} mismatch")
            except (IntegrityError, ValidationError) as exc:
                raise IntegrityError(
                    f"function receipt member {ordinal} report is invalid: {exc}"
                ) from exc
            if membership["input_hash"] != artifact_row["input_hash"]:
                raise IntegrityError(
                    f"function receipt member {ordinal} input digest mismatch"
                )
            entry_seal = _function_entry_seal(artifact_row, report_row)
            if membership["entry_seal"] != entry_seal:
                raise IntegrityError(
                    f"function receipt member {ordinal} entry seal mismatch"
                )
            entries.append(
                FunctionEntry(
                    input=artifact.input.value,
                    output=artifact.output.value,
                    artifact_hash=str(artifact_row["artifact_hash"]),
                    evidence_snapshot_hash=str(
                        artifact_row["evidence_snapshot_hash"]
                    ),
                    entry_seal=entry_seal,
                    report_details_hash=str(report_row["details_hash"]),
                    report_test_set_hash=str(report_row["test_set_hash"]),
                )
            )

        try:
            document = build_function(
                partition=receipt.partition,
                operation=receipt.operation,
                operation_revision=receipt.operation_revision,
                policy_hash=receipt.policy_hash,
                entries=entries,
            )
            if document.function_hash != receipt.function_hash:
                raise IntegrityError("rebuilt function hash does not match receipt")
            validated = validate_function(
                document.value,
                expected_function_hash=receipt.function_hash,
            )
            if validated.text != document.text:
                raise IntegrityError("rebuilt function normalization changed")
        except ValidationError as exc:
            raise IntegrityError("function receipt rebuilt an invalid document") from exc
        return FunctionReconstruction(receipt=receipt, document=document)

    def _persisted_function_receipt_check(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        operation_revision: int,
        entry_count: int,
        document: FunctionDocument | None,
    ) -> FunctionCheck:
        receipt_row = self._latest_function_receipt_row(
            connection,
            partition=partition,
            operation=operation,
            operation_revision=operation_revision,
        )
        if receipt_row is None:
            if entry_count == 0:
                return FunctionCheck(
                    key="persisted-function-receipt",
                    passed=True,
                    detail="empty promoted set vacuously requires no persisted receipt",
                )
            return FunctionCheck(
                key="persisted-function-receipt",
                passed=False,
                detail="nonempty promoted set has no current-revision function receipt",
            )
        try:
            reconstructed = self._reconstruct_function_receipt(
                connection,
                receipt_row,
            )
        except IntegrityError as exc:
            return FunctionCheck(
                key="persisted-function-receipt",
                passed=False,
                detail=f"latest current-revision receipt is invalid: {exc}",
            )
        if document is None:
            return FunctionCheck(
                key="persisted-function-receipt",
                passed=False,
                detail="latest receipt reconstructs but the promoted snapshot does not",
            )
        if reconstructed.text != document.text:
            return FunctionCheck(
                key="persisted-function-receipt",
                passed=False,
                detail="latest receipt does not bind the promoted snapshot",
            )
        return FunctionCheck(
            key="persisted-function-receipt",
            passed=True,
            detail=(
                f"receipt {reconstructed.receipt.id} at sequence "
                f"{reconstructed.receipt.sequence} binds the promoted snapshot"
            ),
        )

    def latest_function_receipt(
        self,
        partition: str,
        operation: str,
    ) -> FunctionReceipt:
        """Return the newest self-bound receipt for the current revision."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        with self.store.transaction(write=False) as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            stored_revision = registered["revision"]
            if (
                type(stored_revision) is not int
                or not 1 <= stored_revision <= _MAX_SQLITE_INTEGER
            ):
                raise IntegrityError("stored operation revision is invalid")
            revision = int(stored_revision)
            receipt_row = self._latest_function_receipt_row(
                connection,
                partition=partition,
                operation=operation,
                operation_revision=revision,
            )
            if receipt_row is None:
                raise NotFoundError("current operation revision has no function receipt")
            return _function_receipt_from_row(receipt_row)

    def function_receipts(
        self,
        partition: str,
        operation: str,
        *,
        operation_revision: int | None = None,
        before_sequence: int | None = None,
        limit: int = 100,
    ) -> FunctionReceiptPage:
        """Enumerate self-bound receipt rows without reconstructing memberships."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if operation_revision is not None:
            _bounded_int(
                operation_revision,
                "operation_revision",
                minimum=1,
                maximum=2**63 - 1,
            )
        if before_sequence is not None:
            _bounded_int(
                before_sequence,
                "before_sequence",
                minimum=0,
                maximum=2**63 - 1,
            )
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)

        predicates = ["partition = ?", "operation = ?"]
        parameters: list[object] = [partition, operation]
        if operation_revision is not None:
            predicates.append("operation_revision = ?")
            parameters.append(operation_revision)
        if before_sequence is not None:
            predicates.append("sequence < ?")
            parameters.append(before_sequence)
        parameters.append(limit + 1)

        with self.store.transaction(write=False) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM function_receipts
                WHERE {' AND '.join(predicates)}
                ORDER BY sequence DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
            page_rows = rows[:limit]
            receipts = tuple(_function_receipt_from_row(row) for row in page_rows)
            return FunctionReceiptPage(
                receipts=receipts,
                next_before_sequence=(
                    receipts[-1].sequence if len(rows) > limit else None
                ),
            )

    def _function_report_member(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        receipt: FunctionReceipt,
        expected_ordinal: int,
    ) -> FunctionMember:
        try:
            ordinal = _stored_int(
                row["membership_ordinal"],
                "function report member ordinal",
                maximum=receipt.member_count - 1,
            )
            artifact_id = _request_id(row["membership_artifact_id"])
            report_id = _request_id(row["membership_report_id"])
            function_hash = _digest(
                row["membership_function_hash"],
                "function report member function_hash",
            )
            input_hash = _digest(
                row["membership_input_hash"],
                "function report member input_hash",
            )
            entry_seal = _digest(
                row["membership_entry_seal"],
                "function report member entry_seal",
            )
            support = _stored_int(
                row["support"],
                "function report member support",
                minimum=2,
            )
            reviewer_count = _stored_int(
                row["reviewer_count"],
                "function report member reviewer count",
                minimum=1,
                maximum=support,
            )
        except (IndexError, KeyError, TypeError, ValidationError) as exc:
            raise IntegrityError(
                f"function report member {expected_ordinal} has invalid scalar fields"
            ) from exc
        if ordinal != expected_ordinal:
            raise IntegrityError("function report member ordinals are not contiguous")
        if function_hash != receipt.function_hash:
            raise IntegrityError("function report member function hash mismatch")
        if row["id"] != artifact_id:
            raise IntegrityError("function report member artifact binding mismatch")
        if (
            row["partition"] != receipt.partition
            or row["operation"] != receipt.operation
            or row["operation_revision"] != receipt.operation_revision
            or row["policy_hash"] != receipt.policy_hash
        ):
            raise IntegrityError("function report member scope binding mismatch")
        if row["input_hash"] != input_hash:
            raise IntegrityError("function report member input digest mismatch")
        try:
            self._artifact_from_row(row)
        except ValidationError as exc:
            raise IntegrityError(
                f"function report member {expected_ordinal} artifact is invalid: {exc}"
            ) from exc

        report_row: dict[str, Any] = {
            "id": row["bound_report_id"],
            "artifact_id": row["bound_report_artifact_id"],
            "artifact_hash": row["bound_report_artifact_hash"],
            "build_hash": row["bound_report_build_hash"],
            "policy_hash": row["bound_report_policy_hash"],
            "evidence_snapshot_hash": row[
                "bound_report_evidence_snapshot_hash"
            ],
            "passed": row["bound_report_passed"],
            "details_json": row["bound_report_details_json"],
            "details_hash": row["bound_report_details_hash"],
            "test_count": row["bound_report_test_count"],
            "test_set_hash": row["bound_report_test_set_hash"],
        }
        try:
            if _request_id(report_row["id"]) != report_id:
                raise IntegrityError("bound report identity mismatch")
            if _request_id(report_row["artifact_id"]) != artifact_id:
                raise IntegrityError("bound report artifact mismatch")
            if report_row["passed"] != 1:
                raise IntegrityError("bound report is not passing")
            details = self._validate_report(
                connection,
                report_row,
                verify_test_set=False,
            )
            details_value = cast(dict[str, JSONValue], details.value)
            if details_value.get("scope_hash") != row["scope_hash"]:
                raise IntegrityError("bound report scope mismatch")
            for field in (
                "artifact_hash",
                "build_hash",
                "policy_hash",
                "evidence_snapshot_hash",
            ):
                if report_row[field] != row[field]:
                    raise IntegrityError(f"bound report {field} mismatch")
        except (
            IndexError,
            KeyError,
            TypeError,
            ValidationError,
            ValueError,
            OverflowError,
            IntegrityError,
        ) as exc:
            raise IntegrityError(
                f"function report member {expected_ordinal} report is invalid: {exc}"
            ) from exc
        if _function_entry_seal(row, report_row) != entry_seal:
            raise IntegrityError(
                f"function report member {expected_ordinal} entry seal mismatch"
            )
        return FunctionMember(
            ordinal=ordinal,
            artifact_id=artifact_id,
            input_hash=input_hash,
            build_support=support,
            build_reviewer_count=reviewer_count,
        )

    def _pending_proposal_gap_from_row(
        self,
        binding: _ProposalBinding,
        *,
        partition: str,
        operation: str,
    ) -> PendingProposalGap:
        row = binding.row
        # Every term reads the row rather than the binding record, so this check keeps the
        # exact fields, order, class and message it had before the adapter existed.
        if (
            row["partition"] != partition
            or row["bound_request_partition"] != partition
            or row["operation"] != operation
            or row["request_id"] != binding.request_id
            or row["status"] != "pending"
            or row["bound_request_status"] != "pending"
            or row["bound_proposal_id"] != binding.proposal_id
        ):
            raise IntegrityError("pending proposal scope or request binding mismatch")
        try:
            self._validate_proposal_shape(row)
            self._proposal_content(binding)
        except ValidationError as exc:
            raise IntegrityError(f"pending proposal row is invalid: {exc}") from exc
        return PendingProposalGap(
            proposal_id=binding.proposal_id,
            operation_revision=binding.operation_revision,
            input_hash=binding.input_hash,
        )

    def _operation_report_artifact(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        partition: str,
        operation: str,
        expected_status: str,
    ) -> OperationArtifact:
        try:
            sequence = _stored_int(
                row["sequence"],
                "operation artifact sequence",
                minimum=1,
            )
            artifact_id = _request_id(row["id"])
            operation_revision = _stored_int(
                row["operation_revision"],
                "operation artifact revision",
                minimum=1,
            )
            input_hash = _digest(row["input_hash"], "operation artifact input_hash")
            support = _stored_int(
                row["support"],
                "operation artifact support",
                minimum=2,
            )
            _stored_int(
                row["reviewer_count"],
                "operation artifact reviewer count",
                minimum=1,
                maximum=support,
            )
            _stored_int(
                row["span_seconds"],
                "operation artifact span",
            )
            status_reason = (
                _text(
                    row["status_reason"],
                    "operation artifact status_reason",
                    maximum=2_048,
                )
                if row["status_reason"] is not None
                else None
            )
        except (IndexError, KeyError, TypeError, ValidationError) as exc:
            raise IntegrityError("operation artifact row has invalid scalar fields") from exc
        if (
            row["partition"] != partition
            or row["operation"] != operation
            or row["status"] != expected_status
        ):
            raise IntegrityError("operation artifact scope or status binding mismatch")
        try:
            self._artifact_from_row(row)
            if expected_status == "promoted":
                self._validate_promoted(connection, row)
        except (TypeError, ValidationError, ValueError, OverflowError) as exc:
            raise IntegrityError(f"operation artifact row is invalid: {exc}") from exc
        return OperationArtifact(
            sequence=sequence,
            artifact_id=artifact_id,
            operation_revision=operation_revision,
            input_hash=input_hash,
            status_reason=status_reason,
        )

    def function_report(
        self,
        partition: str,
        operation: str,
        *,
        receipt_id: str | None = None,
        projection_limit: int = 100,
    ) -> FunctionReport:
        """Report immutable function membership beside current operation state."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if receipt_id is not None:
            receipt_id = _request_id(receipt_id)
        _bounded_int(
            projection_limit,
            "projection_limit",
            minimum=1,
            maximum=10_000,
        )

        with self.store.transaction(write=False) as connection:
            operation_row = connection.execute(
                "SELECT * FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if operation_row is None:
                raise NotFoundError("operation is not registered in this partition")
            if (
                operation_row["partition"] != partition
                or operation_row["name"] != operation
            ):
                raise IntegrityError("stored operation scope is invalid")
            revision = _stored_int(
                operation_row["revision"],
                "stored operation revision",
                minimum=1,
            )
            policy_json = operation_row["policy_json"]
            try:
                if type(policy_json) is not str:
                    raise TypeError("policy text is not a string")
                policy_hash = _digest(
                    operation_row["policy_hash"],
                    "stored operation policy_hash",
                )
                policy = _policy_from_text(policy_json)
                normalized_policy = canonicalize(policy.as_json(), max_bytes=16_384)
            except (TypeError, ValidationError) as exc:
                raise IntegrityError("stored operation policy is invalid") from exc
            if normalized_policy.text != policy_json:
                raise IntegrityError("stored operation policy is not canonical")
            if normalized_policy.digest != policy_hash:
                raise IntegrityError("operation policy digest mismatch")

            if receipt_id is None:
                receipt_row = self._latest_function_receipt_row(
                    connection,
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                )
            else:
                receipt_row = connection.execute(
                    """
                    SELECT * FROM function_receipts
                    WHERE partition = ? AND operation = ? AND id = ?
                    """,
                    (partition, operation, receipt_id),
                ).fetchone()
                if receipt_row is None:
                    raise NotFoundError(
                        "function receipt does not exist for this operation"
                    )

            function_anchor: FunctionAnchorReport | None = None
            if receipt_row is not None:
                receipt = _function_receipt_from_row(receipt_row)
                member_rows = connection.execute(
                    """
                    SELECT a.*,
                           m.ordinal AS membership_ordinal,
                           m.function_hash AS membership_function_hash,
                           m.artifact_id AS membership_artifact_id,
                           m.report_id AS membership_report_id,
                           m.input_hash AS membership_input_hash,
                           m.entry_seal AS membership_entry_seal,
                           r.id AS bound_report_id,
                           r.artifact_id AS bound_report_artifact_id,
                           r.artifact_hash AS bound_report_artifact_hash,
                           r.build_hash AS bound_report_build_hash,
                           r.policy_hash AS bound_report_policy_hash,
                           r.evidence_snapshot_hash
                               AS bound_report_evidence_snapshot_hash,
                           r.passed AS bound_report_passed,
                           r.details_json AS bound_report_details_json,
                           r.details_hash AS bound_report_details_hash,
                           r.test_count AS bound_report_test_count,
                           r.test_set_hash AS bound_report_test_set_hash
                    FROM function_memberships AS m
                    JOIN artifacts AS a ON a.id = m.artifact_id
                    JOIN test_reports AS r
                      ON r.id = m.report_id AND r.artifact_id = m.artifact_id
                    WHERE m.receipt_id = ?
                    ORDER BY m.ordinal LIMIT ?
                    """,
                    (receipt.id, projection_limit),
                ).fetchall()
                expected_members = min(receipt.member_count, projection_limit)
                if len(member_rows) != expected_members:
                    raise IntegrityError(
                        "function receipt projected membership count mismatch"
                    )
                members = tuple(
                    self._function_report_member(
                        connection,
                        row,
                        receipt=receipt,
                        expected_ordinal=ordinal,
                    )
                    for ordinal, row in enumerate(member_rows)
                )
                member_input_hashes = [member.input_hash for member in members]
                if member_input_hashes != sorted(member_input_hashes):
                    raise IntegrityError(
                        "function report member order is not canonical"
                    )
                function_anchor = FunctionAnchorReport(
                    receipt=receipt,
                    member_count=receipt.member_count,
                    members=members,
                )

            ready_scopes: list[CompileScope] = []
            blocked_scopes: list[CompileScope] = []
            ready_count = 0
            blocked_count = 0
            try:
                projections = self._current_build_projections(
                    connection,
                    operation_row,
                )
                for input_hash, _input_text, projection in projections:
                    scope = CompileScope(
                        input_hash=input_hash,
                        active_support=projection.support,
                        active_reviewer_count=projection.reviewer_count,
                        active_span_seconds=projection.span_seconds,
                        reasons=(
                            projection.reasons
                            if isinstance(projection, _BlockedBuild)
                            else ()
                        ),
                    )
                    if isinstance(projection, _BlockedBuild):
                        blocked_count += 1
                        if len(blocked_scopes) < projection_limit:
                            blocked_scopes.append(scope)
                    else:
                        ready_count += 1
                        if len(ready_scopes) < projection_limit:
                            ready_scopes.append(scope)
            except (TypeError, ValidationError, ValueError, OverflowError) as exc:
                raise IntegrityError(f"current build projection is invalid: {exc}") from exc

            pending_bindings = _proposal_bindings(
                connection,
                partition=partition,
                selection=_PendingProposals(
                    operation=operation,
                    limit=projection_limit,
                ),
            )
            pending_count = pending_bindings.total
            if len(pending_bindings.rows) != min(pending_count, projection_limit):
                raise IntegrityError("pending proposal projection count mismatch")
            pending_proposals = tuple(
                self._pending_proposal_gap_from_row(
                    binding,
                    partition=partition,
                    operation=operation,
                )
                for binding in pending_bindings.rows
            )

            artifact_status_order = (
                "draft",
                "verified",
                "promoted",
                "suspended",
                "retired",
            )
            artifact_counts = {status: 0 for status in artifact_status_order}
            for count_row in connection.execute(
                """
                SELECT status, COUNT(*) AS item_count
                FROM artifacts
                WHERE partition = ? AND operation = ?
                GROUP BY status
                """,
                (partition, operation),
            ).fetchall():
                status = count_row["status"]
                if status == "building":
                    raise IntegrityError(
                        "operation contains a persisted building artifact"
                    )
                if type(status) is not str or status not in artifact_counts:
                    raise IntegrityError(
                        "operation contains an unknown artifact status"
                    )
                artifact_counts[status] = _stored_int(
                    count_row["item_count"],
                    f"{status} artifact count",
                )

            artifact_statuses: list[OperationArtifactStatus] = []
            for status in artifact_status_order:
                artifact_rows = connection.execute(
                    """
                    SELECT * FROM artifacts
                    WHERE partition = ? AND operation = ? AND status = ?
                    ORDER BY sequence DESC LIMIT ?
                    """,
                    (partition, operation, status, projection_limit),
                ).fetchall()
                if len(artifact_rows) != min(
                    artifact_counts[status],
                    projection_limit,
                ):
                    raise IntegrityError(
                        f"{status} artifact projection count mismatch"
                    )
                artifacts = tuple(
                    self._operation_report_artifact(
                        connection,
                        row,
                        partition=partition,
                        operation=operation,
                        expected_status=status,
                    )
                    for row in artifact_rows
                )
                artifact_statuses.append(
                    OperationArtifactStatus(
                        status=cast(
                            Literal[
                                "draft",
                                "verified",
                                "promoted",
                                "suspended",
                                "retired",
                            ],
                            status,
                        ),
                        count=artifact_counts[status],
                        artifacts=artifacts,
                    )
                )

            stale_count_row = connection.execute(
                """
                SELECT COUNT(*) AS item_count FROM artifacts
                WHERE partition = ? AND operation = ?
                  AND status IN ('draft', 'verified', 'promoted')
                  AND operation_revision <> ?
                """,
                (partition, operation, revision),
            ).fetchone()
            if stale_count_row is None:
                raise IntegrityError("stale revision anomaly count is missing")
            stale_count = _stored_int(
                stale_count_row["item_count"],
                "stale revision anomaly count",
            )
            stale_rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = ? AND operation = ?
                  AND status IN ('draft', 'verified', 'promoted')
                  AND operation_revision <> ?
                ORDER BY id LIMIT ?
                """,
                (partition, operation, revision, projection_limit),
            ).fetchall()
            if len(stale_rows) != min(stale_count, projection_limit):
                raise IntegrityError("stale revision anomaly projection count mismatch")
            stale_anomalies: list[StaleRevisionAnomaly] = []
            for row in stale_rows:
                status = str(row["status"])
                artifact = self._operation_report_artifact(
                    connection,
                    row,
                    partition=partition,
                    operation=operation,
                    expected_status=status,
                )
                artifact_revision = artifact.operation_revision
                stale_anomalies.append(
                    StaleRevisionAnomaly(
                        artifact_id=artifact.artifact_id,
                        status=cast(
                            Literal["draft", "verified", "promoted"],
                            status,
                        ),
                        artifact_revision=artifact_revision,
                        current_revision=revision,
                        reason=(
                            f"{status} artifact belongs to stale operation revision "
                            f"{artifact_revision}; current revision is {revision}"
                        ),
                    )
                )

            return FunctionReport(
                partition=partition,
                operation=operation,
                function_anchor=function_anchor,
                operation_now=OperationNowReport(
                    operation_revision=revision,
                    policy_hash=policy_hash,
                    projection_limit=projection_limit,
                    promoted_entry_count=artifact_counts["promoted"],
                    compile_ready_scope_count=ready_count,
                    compile_ready_scopes=tuple(ready_scopes),
                    compile_blocked_scope_count=blocked_count,
                    compile_blocked_scopes=tuple(blocked_scopes),
                    pending_proposal_count=pending_count,
                    pending_proposals=pending_proposals,
                    artifact_statuses=tuple(artifact_statuses),
                    stale_revision_anomaly_count=stale_count,
                    stale_revision_anomalies=tuple(stale_anomalies),
                ),
            )

    def reconstruct_function_receipt(
        self,
        partition: str,
        receipt_id: str,
    ) -> FunctionReconstruction:
        """Validate and rebuild one historical function by immutable receipt ID."""

        partition = _name(partition, "partition")
        receipt_id = _request_id(receipt_id)
        with self.store.transaction(write=False) as connection:
            receipt_row = connection.execute(
                """
                SELECT * FROM function_receipts
                WHERE partition = ? AND id = ?
                """,
                (partition, receipt_id),
            ).fetchone()
            if receipt_row is None:
                raise NotFoundError(
                    "function receipt does not exist in this partition"
                )
            return self._reconstruct_function_receipt(connection, receipt_row)

    def verify_function(
        self,
        partition: str,
        operation: str,
        *,
        expected_function_hash: str | None = None,
    ) -> FunctionVerification:
        """Verify one committed promoted-set snapshot without mutation.

        A passing result proves exact projection and current ledger bindings only for
        the read transaction's snapshot. Each accepted entry is compatible with
        the current artifact ABI and canonicalizer; this is per-entry current
        compatibility, not a separate relational metadata proof. Consumers must
        gate on ``passed``: a diagnostic hash may accompany a failed result. This
        is not a lease, signature, persisted report, semantic replay, or
        domain-coverage proof.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if expected_function_hash is not None and (
            type(expected_function_hash) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_function_hash) is None
        ):
            raise ValidationError("expected_function_hash must be a SHA-256 hex digest")

        def summarized(
            key: str,
            failures: list[str],
            passed_detail: str,
        ) -> FunctionCheck:
            if not failures:
                return FunctionCheck(key=key, passed=True, detail=passed_detail)
            return FunctionCheck(
                key=key,
                passed=False,
                detail=(
                    f"{len(failures)} failure(s): "
                    + "; ".join(failures[:3])
                ),
            )

        with self.store.transaction(write=False) as connection:
            registered = connection.execute(
                "SELECT * FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            if type(registered["revision"]) is not int:
                raise IntegrityError("stored operation revision is invalid")
            revision = int(registered["revision"])
            policy_hash = registered["policy_hash"]
            policy_json = registered["policy_json"]
            if type(policy_hash) is not str:
                raise IntegrityError("stored operation policy hash is invalid")
            if type(policy_json) is not str:
                raise IntegrityError("stored operation policy JSON is invalid")

            operation_policy_failures: list[str] = []
            try:
                policy = _policy_from_text(policy_json)
                canonical_policy = canonicalize(policy.as_json(), max_bytes=16_384)
            except (IntegrityError, ValidationError) as exc:
                operation_policy_failures.append(
                    f"operation policy is invalid: {exc}"
                )
            else:
                if canonical_policy.text != policy_json:
                    operation_policy_failures.append(
                        "operation policy JSON is not canonical"
                    )
                if canonical_policy.digest != policy_hash:
                    operation_policy_failures.append(
                        "operation policy digest does not match policy_hash"
                    )

            entry_count = self._promoted_function_count(
                connection,
                partition=partition,
                operation=operation,
            )
            if entry_count > FUNCTION_MAX_ENTRIES:
                skipped = (
                    f"not evaluated because {entry_count} promoted entries exceed "
                    f"FUNCTION_MAX_ENTRIES={FUNCTION_MAX_ENTRIES}"
                )
                receipt_detail = skipped
                if operation_policy_failures:
                    receipt_detail = (
                        "; ".join(operation_policy_failures) + "; " + skipped
                    )
                checks = (
                    FunctionCheck(
                        key="duplicate-input-digests",
                        passed=False,
                        detail=skipped,
                    ),
                    FunctionCheck(
                        key="abi-canonicalizer-uniform",
                        passed=False,
                        detail=skipped,
                    ),
                    FunctionCheck(
                        key="sealed-passing-reports",
                        passed=False,
                        detail=skipped,
                    ),
                    FunctionCheck(
                        key="current-promotion-receipts",
                        passed=False,
                        detail=receipt_detail,
                    ),
                    FunctionCheck(
                        key="function-hash-matches-snapshot",
                        passed=False,
                        detail=(
                            f"promoted set has {entry_count} entries and exceeds "
                            f"FUNCTION_MAX_ENTRIES={FUNCTION_MAX_ENTRIES}"
                        ),
                    ),
                    FunctionCheck(
                        key="persisted-function-receipt",
                        passed=False,
                        detail=skipped,
                    ),
                )
                return FunctionVerification(
                    passed=False,
                    entries=entry_count,
                    document=None,
                    function_hash=None,
                    checks=checks,
                )

            rows = self._promoted_function_rows(
                connection,
                partition=partition,
                operation=operation,
            )
            if len(rows) != entry_count:
                raise IntegrityError("promoted-set count changed during enumeration")

            first_digest_source: dict[str, str] = {}
            duplicate_sources: dict[str, list[str]] = {}
            for row in rows:
                digest = str(row["input_hash"])
                artifact_id = str(row["id"])
                if digest not in first_digest_source:
                    first_digest_source[digest] = artifact_id
                    continue
                sources = duplicate_sources.setdefault(
                    digest, [first_digest_source[digest]]
                )
                if len(sources) < 3:
                    sources.append(artifact_id)
            duplicates = sorted(duplicate_sources.items())
            if duplicates:
                preview = "; ".join(
                    f"{digest}:{','.join(source_ids)}"
                    for digest, source_ids in duplicates[:3]
                )
                duplicate_check = FunctionCheck(
                    key="duplicate-input-digests",
                    passed=False,
                    detail=f"{len(duplicates)} duplicate digest(s): {preview}",
                )
            else:
                duplicate_check = FunctionCheck(
                    key="duplicate-input-digests",
                    passed=True,
                    detail=f"{entry_count} entries have unique input digests",
                )

            abi_failures: list[str] = []
            report_failures: list[str] = []
            receipt_failures = list(operation_policy_failures)
            projection_failures = [
                f"operation: {failure}" for failure in operation_policy_failures
            ]
            projected: list[tuple[str, str, str, FunctionEntry]] = []
            for row in rows:
                artifact_id = str(row["id"])
                try:
                    raw_artifact = parse_json(
                        str(row["artifact_json"]), max_bytes=ARTIFACT_MAX_BYTES
                    ).value
                    if type(raw_artifact) is not dict:
                        raise IntegrityError("artifact document is not an object")
                    raw_scope = raw_artifact.get("scope")
                    artifact_abi = raw_artifact.get("abi")
                    canonicalizer = (
                        raw_scope.get("canonicalizer")
                        if type(raw_scope) is dict
                        else None
                    )
                    if artifact_abi != ARTIFACT_ABI or canonicalizer != CANONICALIZER:
                        abi_failures.append(
                            f"{artifact_id}: abi={artifact_abi!r}, "
                            f"canonicalizer={canonicalizer!r}"
                        )
                except (IntegrityError, ValidationError) as exc:
                    abi_failures.append(f"{artifact_id}: {exc}")

                report: sqlite3.Row | None = None
                if row["verified_report_id"] is not None:
                    report = connection.execute(
                        "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                        (row["verified_report_id"], artifact_id),
                    ).fetchone()
                try:
                    if report is None or report["passed"] != 1:
                        raise IntegrityError("missing passing bound report")
                    details = self._validate_report(
                        connection, report, verify_test_set=True
                    )
                    if type(details.value) is not dict:
                        raise IntegrityError("report details are not an object")
                    if details.value.get("scope_hash") != row["scope_hash"]:
                        raise IntegrityError("report scope binding mismatch")
                    for field in (
                        "artifact_hash",
                        "build_hash",
                        "policy_hash",
                        "evidence_snapshot_hash",
                    ):
                        if report[field] != row[field]:
                            raise IntegrityError(f"report {field} binding mismatch")
                except (IntegrityError, ValidationError) as exc:
                    report_failures.append(f"{artifact_id}: {exc}")

                artifact: ArtifactDocument | None = None
                artifact_error: str | None = None
                try:
                    artifact = self._artifact_from_row(row)
                except (IntegrityError, ValidationError) as exc:
                    artifact_error = str(exc)

                scope_failures: list[str] = []
                stored_revision = row["operation_revision"]
                if type(stored_revision) is not int:
                    scope_failures.append("stored operation revision is not an integer")
                elif stored_revision != revision:
                    scope_failures.append(
                        f"operation revision {stored_revision} does not match current {revision}"
                    )
                if row["policy_hash"] != policy_hash:
                    scope_failures.append(
                        "policy hash does not match current operation"
                    )
                if row["policy_json"] != policy_json:
                    scope_failures.append(
                        "policy JSON does not match current operation"
                    )
                try:
                    if artifact is None:
                        raise IntegrityError(artifact_error or "artifact is invalid")
                    if scope_failures:
                        raise IntegrityError("; ".join(scope_failures))
                    self._validate_promoted(connection, row)
                except (IntegrityError, ValidationError) as exc:
                    receipt_failures.append(f"{artifact_id}: {exc}")

                if artifact is None:
                    projection_failures.append(
                        f"{artifact_id}: {artifact_error or 'artifact is invalid'}"
                    )
                elif report is None:
                    projection_failures.append(f"{artifact_id}: bound report is missing")
                elif scope_failures:
                    projection_failures.append(
                        f"{artifact_id}: {'; '.join(scope_failures)}"
                    )
                else:
                    entry = FunctionEntry(
                        input=artifact.input.value,
                        output=artifact.output.value,
                        artifact_hash=str(row["artifact_hash"]),
                        evidence_snapshot_hash=str(
                            row["evidence_snapshot_hash"]
                        ),
                        entry_seal=_function_entry_seal(row, report),
                        report_details_hash=str(report["details_hash"]),
                        report_test_set_hash=str(report["test_set_hash"]),
                    )
                    input_json = canonicalize(entry.input)
                    output_json = canonicalize(entry.output)
                    if input_json.digest != row["input_hash"]:
                        projection_failures.append(
                            f"{artifact_id}: input digest changed during projection"
                        )
                    elif output_json.digest != row["output_hash"]:
                        projection_failures.append(
                            f"{artifact_id}: output digest changed during projection"
                        )
                    else:
                        projected.append(
                            (
                                artifact_id,
                                input_json.digest,
                                output_json.digest,
                                entry,
                            )
                        )

            abi_check = summarized(
                "abi-canonicalizer-uniform",
                abi_failures,
                (
                    f"{entry_count} entries are vacuously compatible with current "
                    f"{ARTIFACT_ABI} + {CANONICALIZER}"
                    if entry_count == 0
                    else f"{entry_count} entries are compatible with current "
                    f"{ARTIFACT_ABI} + {CANONICALIZER}"
                ),
            )
            report_check = summarized(
                "sealed-passing-reports",
                report_failures,
                f"{entry_count} entries carry passing full-seal reports",
            )
            receipt_check = summarized(
                "current-promotion-receipts",
                receipt_failures,
                f"{entry_count} entries carry current valid promotion receipts",
            )
            del rows

            document = None
            function_hash: str | None = None
            if projection_failures:
                hash_check = FunctionCheck(
                    key="function-hash-matches-snapshot",
                    passed=False,
                    detail=(
                        f"{len(projection_failures)} unprojectable entry/entries: "
                        + "; ".join(projection_failures[:3])
                    ),
                )
            else:
                try:
                    document = build_function(
                        partition=partition,
                        operation=operation,
                        operation_revision=revision,
                        policy_hash=policy_hash,
                        entries=(item[3] for item in projected),
                    )
                    function_hash = document.function_hash
                    if document.value.get("abi") != FUNCTION_ABI:
                        raise IntegrityError("function ABI changed during projection")
                    if document.value.get("canonicalizer") != CANONICALIZER:
                        raise IntegrityError(
                            "function canonicalizer changed during projection"
                        )
                    if document.value.get("function_hash") != document.function_hash:
                        raise IntegrityError(
                            "function hash changed during projection"
                        )
                    expected_scope: dict[str, JSONValue] = {
                        "operation": operation,
                        "operation_revision": revision,
                        "partition": partition,
                        "policy_hash": policy_hash,
                    }
                    if document.value.get("scope") != expected_scope:
                        raise IntegrityError(
                            "function scope does not equal the promoted snapshot"
                        )
                    actual_entries = document.value.get("entries")
                    if type(actual_entries) is not list:
                        raise IntegrityError("function entries are not an array")
                    if len(actual_entries) != len(projected):
                        raise IntegrityError(
                            "function entry count does not equal the promoted snapshot"
                        )
                    projected.sort(key=lambda item: item[1])
                    for actual, (
                        artifact_id,
                        input_hash,
                        output_hash,
                        entry,
                    ) in zip(actual_entries, projected, strict=True):
                        expected_entry: dict[str, JSONValue] = {
                            "artifact_hash": entry.artifact_hash,
                            "evidence_snapshot_hash": entry.evidence_snapshot_hash,
                            "input": entry.input,
                            "input_hash": input_hash,
                            "output": entry.output,
                            "output_hash": output_hash,
                            "entry_seal": entry.entry_seal,
                            "report": {
                                "details_hash": entry.report_details_hash,
                                "test_set_hash": entry.report_test_set_hash,
                            },
                        }
                        if actual != expected_entry:
                            raise IntegrityError(
                                f"{artifact_id} function entry changed during projection"
                            )
                    validated = validate_function(
                        document.value,
                        expected_function_hash=(
                            document.function_hash
                            if expected_function_hash is None
                            else expected_function_hash
                        ),
                    )
                    if validated.text != document.text:
                        raise IntegrityError(
                            "function normalization changed during self-check"
                        )
                except (IntegrityError, ValidationError) as exc:
                    hash_check = FunctionCheck(
                        key="function-hash-matches-snapshot",
                        passed=False,
                        detail=str(exc),
                    )
                else:
                    hash_check = FunctionCheck(
                        key="function-hash-matches-snapshot",
                        passed=True,
                        detail=(
                            f"{document.function_hash} binds "
                            f"{entry_count} snapshot entry/entries"
                        ),
                    )

            persisted_receipt_check = self._persisted_function_receipt_check(
                connection,
                partition=partition,
                operation=operation,
                operation_revision=revision,
                entry_count=entry_count,
                document=document,
            )
            checks = (
                duplicate_check,
                abi_check,
                report_check,
                receipt_check,
                hash_check,
                persisted_receipt_check,
            )
            passed = all(check.passed for check in checks)
            return FunctionVerification(
                passed=passed,
                entries=entry_count,
                document=document if passed else None,
                function_hash=function_hash,
                checks=checks,
            )

    def resolve(
        self,
        partition: str,
        operation: str,
        input_value: object,
        *,
        expected_function_hash: str | None = None,
    ) -> FunctionResolution:
        """Verify one promoted-set snapshot, then look the input up inside it.

        Arguments are validated first, so a call this method rejects runs no
        check and reads no ledger. Every call that reaches the ledger runs the
        full six-check verification, so a resolve costs what ``verify_function``
        costs. One resolve over a 50,000-entry set costs ~36.5 s and ~963 MiB,
        measured end to end through this method
        (``.agent/decisions/m3u2b-resolve-bench.json``). This call writes
        nothing and caches nothing. Two calls take two snapshots, so a writer
        committing between them changes the second answer. A failed verdict
        returns ``match`` ``None`` and is never a miss.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if expected_function_hash is not None:
            _digest(expected_function_hash, "expected_function_hash")
        input_json = canonicalize(input_value)

        verification = self.verify_function(
            partition,
            operation,
            expected_function_hash=expected_function_hash,
        )
        document = verification.document
        if not verification.passed or document is None:
            return FunctionResolution(verification=verification, match=None)
        return FunctionResolution(
            verification=verification,
            match=evaluate(document, input_json=input_json),
        )

    # -- replay verification + atomic promotion ----------------------------

    def _draft_verification_plan(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
    ) -> tuple[
        int,
        tuple[sqlite3.Row, ...],
        tuple[dict[str, JSONValue], ...],
    ]:
        registered = connection.execute(
            "SELECT * FROM operations WHERE partition = ? AND name = ?",
            (partition, operation),
        ).fetchone()
        if registered is None:
            raise NotFoundError("operation is not registered in this partition")
        if type(registered["revision"]) is not int:
            raise IntegrityError("stored operation revision is invalid")
        revision = int(registered["revision"])
        rows = connection.execute(
            """
            SELECT * FROM artifacts
            WHERE partition = ? AND operation = ? AND operation_revision = ?
              AND status = 'draft'
            ORDER BY input_hash, sequence, id
            """,
            (partition, operation, revision),
        ).fetchall()

        canonical_inputs: dict[str, str] = {}
        for group in connection.execute(
            """
            SELECT e.input_hash, e.input_json
            FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND x.example_id IS NULL
            GROUP BY e.input_hash, e.input_json
            ORDER BY e.input_hash, e.input_json
            """,
            (partition, operation, revision),
        ):
            input_hash = str(group["input_hash"])
            input_json = str(group["input_json"])
            previous = canonical_inputs.get(input_hash)
            if previous is not None and previous != input_json:
                raise IntegrityError(
                    "one input digest maps to multiple canonical inputs"
                )
            canonical_inputs[input_hash] = input_json

        projections: dict[str, _CurrentBuild | _BlockedBuild] = {}
        selected: list[sqlite3.Row] = []
        skipped: list[dict[str, JSONValue]] = []
        selected_hashes: set[str] = set()
        for row in rows:
            input_hash = str(row["input_hash"])
            input_json = canonical_inputs.get(input_hash)
            if input_json is None:
                raise IntegrityError(
                    f"current-revision draft {row['id']} has no canonical input"
                )
            projection = projections.get(input_hash)
            if projection is None:
                projection = self._project_current_build(
                    connection,
                    registered,
                    input_hash,
                    input_json,
                )
                projections[input_hash] = projection
            eligible = (
                type(projection) is _CurrentBuild
                and row["input_json"] == projection.input_json.text
                and row["build_hash"] == projection.build_hash
            )
            if eligible:
                if input_hash in selected_hashes:
                    raise IntegrityError(
                        f"multiple drafts claim the current build for input {input_hash}"
                    )
                selected_hashes.add(input_hash)
                selected.append(row)
            else:
                skipped.append(
                    {
                        "artifact_id": str(row["id"]),
                        "input_hash": input_hash,
                        "reason": "superseded-build",
                    }
                )
        return revision, tuple(selected), tuple(skipped)

    def _verify_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        verified_by: str,
        now_us: int,
    ) -> tuple[VerificationReport, str | None]:
        artifact_id = str(row["id"])
        partition = str(row["partition"])
        report_id = _new_id("report")
        artifact: ArtifactDocument | None
        pending_tests: list[tuple[str, str, str | None, int, str]] = []

        def flush_tests() -> None:
            if pending_tests:
                connection.executemany(
                    """
                    INSERT INTO artifact_tests(
                        report_id, test_key, example_id, passed, detail
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    pending_tests,
                )
                pending_tests.clear()

        def record_test(
            key: str,
            example_id: str | None,
            passed: bool,
            detail: str,
        ) -> None:
            pending_tests.append((report_id, key, example_id, int(passed), detail))
            if len(pending_tests) >= 512:
                flush_tests()

        connection.execute("SAVEPOINT verification_run")
        try:
            if row["status"] == "promoted":
                self._validate_promoted(connection, row)
            failures, test_count, artifact = self._run_verification(
                connection, row, record_test=record_test
            )
            flush_tests()
        except (IntegrityError, ValidationError) as exc:
            pending_tests.clear()
            connection.execute("ROLLBACK TO verification_run")
            connection.execute("RELEASE verification_run")
            failures = [f"artifact integrity failure: {exc}"]
            record_test("artifact-integrity", None, False, failures[0])
            flush_tests()
            test_count = 1
            artifact = None
        else:
            connection.execute("RELEASE verification_run")
        passed = not failures
        scope_hash = (
            artifact.scope_digest if artifact is not None else str(row["scope_hash"])
        )
        stored_test_count, test_set_hash = self._test_snapshot(connection, report_id)
        if stored_test_count != test_count:
            raise IntegrityError("verification test count changed while recording")
        details = canonicalize(
            {
                "failures": failures,
                "scope_hash": scope_hash,
                "tests": test_count,
                "verified_by": verified_by,
            },
            max_bytes=262_144,
        )
        connection.execute(
            """
            INSERT INTO test_reports(
                id, artifact_id, artifact_hash, build_hash, policy_hash,
                evidence_snapshot_hash, passed, details_json, details_hash,
                test_count, test_set_hash, created_at_us
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                artifact_id,
                row["artifact_hash"],
                row["build_hash"],
                row["policy_hash"],
                row["evidence_snapshot_hash"],
                int(passed),
                details.text,
                details.digest,
                test_count,
                test_set_hash,
                now_us,
            ),
        )
        status = str(row["status"])
        if passed and status in {"draft", "verified"}:
            connection.execute(
                """
                UPDATE artifacts
                SET status = 'verified', verified_report_id = ?, status_reason = NULL
                WHERE id = ?
                """,
                (report_id, artifact_id),
            )
        elif not passed and status == "promoted":
            connection.execute(
                """
                UPDATE artifacts
                SET status = 'suspended', promotion_hash = NULL,
                    status_reason = 'verification failed'
                WHERE id = ?
                """,
                (artifact_id,),
            )
        elif not passed and status == "verified":
            connection.execute(
                """
                UPDATE artifacts
                SET status = 'draft', verified_report_id = NULL,
                    status_reason = 'verification failed'
                WHERE id = ?
                """,
                (artifact_id,),
            )
        _event(
            connection,
            partition=partition,
            kind="artifact.verified" if passed else "artifact.verification_failed",
            subject_type="artifact",
            subject_id=artifact_id,
            payload={
                "failures": failures,
                "report_id": report_id,
                "scope_hash": scope_hash,
                "tests": test_count,
                "verified_by": verified_by,
            },
            now_us=now_us,
        )
        report = VerificationReport(
            id=report_id,
            artifact_id=artifact_id,
            scope_hash=scope_hash,
            passed=passed,
            tests=test_count,
            failures=tuple(failures),
            created_at_us=now_us,
        )
        if not passed:
            return report, None
        sealed = connection.execute(
            "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
            (report_id, artifact_id),
        ).fetchone()
        if sealed is None:
            raise IntegrityError("verification report disappeared before sealing")
        return report, _function_entry_seal(row, sealed)

    def verify_drafts(
        self,
        partition: str,
        operation: str,
        *,
        verified_by: str,
    ) -> DraftVerification:
        """Verify every current-build draft in one immediate transaction."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        verified_by = _text(verified_by, "verified_by", maximum=256)
        with self.store.transaction(write=True) as connection:
            revision, rows, skipped = self._draft_verification_plan(
                connection,
                partition=partition,
                operation=operation,
            )
            now = self._now()
            entries: list[DraftEntry] = []
            for row in rows:
                report, entry_seal = self._verify_row(
                    connection,
                    row,
                    verified_by=verified_by,
                    now_us=now,
                )
                entries.append(
                    DraftEntry(
                        artifact_id=str(row["id"]),
                        input_hash=str(row["input_hash"]),
                        report=report,
                        entry_seal=entry_seal,
                    )
                )
        result_entries = tuple(entries)
        return DraftVerification(
            passed=all(entry.report.passed for entry in result_entries),
            operation_revision=revision,
            entries=result_entries,
            skipped=skipped,
        )

    def verify(
        self,
        partition: str,
        artifact_id: str,
        *,
        verified_by: str = "local-system",
    ) -> VerificationReport:
        partition = _name(partition, "partition")
        artifact_id = _request_id(artifact_id)
        verified_by = _text(verified_by, "verified_by", maximum=256)
        now = self._now()
        with self.store.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ? AND partition = ?",
                (artifact_id, partition),
            ).fetchone()
            if row is None:
                raise NotFoundError("artifact does not exist in this partition")
            report, _ = self._verify_row(
                connection,
                row,
                verified_by=verified_by,
                now_us=now,
            )
        return report

    def _run_verification(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        record_test: Callable[[str, str | None, bool, str], None] | None = None,
    ) -> tuple[list[str], int, ArtifactDocument]:
        failures: list[str] = []
        test_count = 0

        def test(key: str, example_id: str | None, passed: bool, detail: str) -> None:
            nonlocal test_count
            test_count += 1
            if record_test is not None:
                record_test(key, example_id, passed, detail)
        try:
            artifact = self._artifact_from_row(row)
        except (IntegrityError, ValidationError) as exc:
            # A placeholder is needed only for the return type; reparse cannot be trusted.
            raise IntegrityError(f"artifact integrity failure: {exc}") from exc
        partition = str(row["partition"])
        operation = str(row["operation"])
        revision = int(row["operation_revision"])
        registered = connection.execute(
            "SELECT * FROM operations WHERE partition = ? AND name = ?",
            (partition, operation),
        ).fetchone()
        current_ok = (
            registered is not None
            and int(registered["revision"]) == revision
            and registered["policy_hash"] == row["policy_hash"]
            and registered["policy_json"] == row["policy_json"]
        )
        test("operation-current", None, current_ok, "operation revision + policy binding")
        if not current_ok:
            failures.append("operation revision or policy is stale")
        policy = _policy_from_text(str(row["policy_json"]))
        assessment = self._assess_examples(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=str(row["input_hash"]),
                input_text=str(row["input_json"]),
            ),
            policy,
            reviewer_count=self._active_reviewer_count(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=str(row["input_hash"]),
                input_text=str(row["input_json"]),
            ),
        )
        if assessment["integrity_failures"]:
            raise IntegrityError(str(assessment["integrity_failures"][0]))
        for failure in assessment["policy_failures"]:
            failures.append(str(failure))
        snapshot = self._evidence_snapshot(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=str(row["input_hash"]),
                input_text=str(row["input_json"]),
                order_by_id=True,
            ),
            partition=partition,
            operation=operation,
            revision=revision,
            input_text=str(row["input_json"]),
        )
        snapshot_ok = snapshot == row["evidence_snapshot_hash"]
        test("evidence-snapshot", None, snapshot_ok, "immutable evidence snapshot")
        if not snapshot_ok:
            failures.append("evidence snapshot changed")
        else:
            for field in ("support", "reviewer_count", "span_seconds"):
                if int(row[field]) != int(assessment[field]):
                    raise IntegrityError(f"artifact {field} does not match active evidence")
        input_json = parse_json(str(row["input_json"]))
        expected_output = str(row["output_json"])
        replay_failures = 0
        for example in self._active_evidence(
            connection,
            partition=partition,
            operation=operation,
            revision=revision,
            input_hash=str(row["input_hash"]),
            input_text=str(row["input_json"]),
            order_by_id=True,
        ):
            execution = execute(
                artifact,
                partition=partition,
                operation=operation,
                operation_revision=revision,
                input_json=input_json,
            )
            ok = (
                execution.matched
                and canonicalize(execution.output).text == str(example["output_json"])
                and str(example["output_json"]) == expected_output
            )
            test(
                f"example:{example['id']}",
                str(example["id"]),
                ok,
                "exact fixture replay",
            )
            if not ok:
                replay_failures += 1
        if replay_failures:
            failures.append(f"{replay_failures} exact fixture replay tests failed")

        different_input = canonicalize({"$cement_boundary_probe": artifact.digest})
        if different_input.text == input_json.text:
            different_input = canonicalize(["$cement_boundary_probe", artifact.digest])
        boundary_cases = (
            (
                "boundary:partition",
                execute(
                    artifact,
                    partition="cement-boundary" if partition != "cement-boundary" else "cement-boundary-2",
                    operation=operation,
                    operation_revision=revision,
                    input_json=input_json,
                ),
            ),
            (
                "boundary:operation",
                execute(
                    artifact,
                    partition=partition,
                    operation="cement-boundary" if operation != "cement-boundary" else "cement-boundary-2",
                    operation_revision=revision,
                    input_json=input_json,
                ),
            ),
            (
                "boundary:revision",
                execute(
                    artifact,
                    partition=partition,
                    operation=operation,
                    operation_revision=revision + 1,
                    input_json=input_json,
                ),
            ),
            (
                "boundary:input",
                execute(
                    artifact,
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                    input_json=different_input,
                ),
            ),
        )
        for key, execution in boundary_cases:
            ok = not execution.matched
            test(key, None, ok, "out-of-scope request must not match")
            if not ok:
                failures.append(f"{key} widened scope")
        return failures, test_count, artifact

    def _function_promotion_entry(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        promoted: bool,
    ) -> tuple[sqlite3.Row, FunctionEntry]:
        artifact_id = str(row["id"])
        report = connection.execute(
            "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
            (row["verified_report_id"], artifact_id),
        ).fetchone()
        if report is None or report["passed"] != 1:
            raise IntegrityError(f"{artifact_id} has no passing bound report")
        details = self._validate_report(connection, report, verify_test_set=True)
        if (
            type(details.value) is not dict
            or details.value.get("scope_hash") != row["scope_hash"]
        ):
            raise IntegrityError(f"{artifact_id} report scope binding mismatch")
        for field in (
            "artifact_hash",
            "build_hash",
            "policy_hash",
            "evidence_snapshot_hash",
        ):
            if report[field] != row[field]:
                raise IntegrityError(f"{artifact_id} report {field} binding mismatch")
        if promoted:
            artifact = self._artifact_from_row(row)
            self._validate_promoted(connection, row)
        else:
            failures, _, artifact = self._run_verification(connection, row)
            if failures:
                raise StateError(
                    f"function candidate {artifact_id} stopped qualifying: {failures[0]}"
                )
        return report, FunctionEntry(
            input=artifact.input.value,
            output=artifact.output.value,
            artifact_hash=str(row["artifact_hash"]),
            evidence_snapshot_hash=str(row["evidence_snapshot_hash"]),
            entry_seal=_function_entry_seal(row, report),
            report_details_hash=str(report["details_hash"]),
            report_test_set_hash=str(report["test_set_hash"]),
        )

    def _function_promotion_plan(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
    ) -> _FunctionPromotionPlan:
        registered = connection.execute(
            "SELECT * FROM operations WHERE partition = ? AND name = ?",
            (partition, operation),
        ).fetchone()
        if registered is None:
            raise NotFoundError("operation is not registered in this partition")
        if type(registered["revision"]) is not int:
            raise IntegrityError("stored operation revision is invalid")
        if type(registered["policy_json"]) is not str:
            raise IntegrityError("stored operation policy JSON is invalid")
        if type(registered["policy_hash"]) is not str:
            raise IntegrityError("stored operation policy hash is invalid")
        revision = int(registered["revision"])
        policy_json = str(registered["policy_json"])
        policy_hash = str(registered["policy_hash"])
        policy = _policy_from_text(policy_json)
        canonical_policy = canonicalize(policy.as_json(), max_bytes=16_384)
        if canonical_policy.text != policy_json or canonical_policy.digest != policy_hash:
            raise IntegrityError("operation policy binding mismatch")

        promoted_rows = connection.execute(
            """
            SELECT * FROM artifacts
            WHERE partition = ? AND operation = ? AND status = 'promoted'
            ORDER BY operation_revision, input_hash, sequence, id
            """,
            (partition, operation),
        ).fetchall()
        retained: dict[
            str,
            tuple[sqlite3.Row, sqlite3.Row, FunctionEntry],
        ] = {}
        for row in promoted_rows:
            artifact_id = str(row["id"])
            if row["operation_revision"] != revision:
                raise IntegrityError(
                    f"promoted artifact {artifact_id} has stale operation revision"
                )
            if row["policy_json"] != policy_json or row["policy_hash"] != policy_hash:
                raise IntegrityError(
                    f"promoted artifact {artifact_id} has stale operation policy"
                )
            input_hash = str(row["input_hash"])
            if input_hash in retained:
                raise IntegrityError(
                    f"multiple promoted artifacts claim input {input_hash}"
                )
            report, function_entry = self._function_promotion_entry(
                connection,
                row,
                promoted=True,
            )
            retained[input_hash] = (row, report, function_entry)

        verified_rows = connection.execute(
            """
            SELECT * FROM artifacts
            WHERE partition = ? AND operation = ? AND operation_revision = ?
              AND status = 'verified'
            ORDER BY operation_revision, input_hash, sequence, id
            """,
            (partition, operation, revision),
        ).fetchall()
        canonical_inputs: dict[str, str] = {}
        for group in connection.execute(
            """
            SELECT e.input_hash, e.input_json
            FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND x.example_id IS NULL
            GROUP BY e.input_hash, e.input_json
            ORDER BY e.input_hash, e.input_json
            """,
            (partition, operation, revision),
        ):
            input_hash = str(group["input_hash"])
            input_json = str(group["input_json"])
            previous = canonical_inputs.get(input_hash)
            if previous is not None and previous != input_json:
                raise IntegrityError(
                    "one input digest maps to multiple canonical inputs"
                )
            canonical_inputs[input_hash] = input_json

        candidates: dict[
            str,
            tuple[sqlite3.Row, sqlite3.Row, FunctionEntry],
        ] = {}
        skipped: list[dict[str, JSONValue]] = []
        projections: dict[str, _CurrentBuild | _BlockedBuild] = {}
        for row in verified_rows:
            artifact_id = str(row["id"])
            input_hash = str(row["input_hash"])
            input_json = canonical_inputs.get(input_hash)
            if input_json is None:
                raise IntegrityError(
                    f"current-revision verified artifact {artifact_id} "
                    "has no canonical input"
                )
            projection = projections.get(input_hash)
            if projection is None:
                projection = self._project_current_build(
                    connection,
                    registered,
                    input_hash,
                    input_json,
                )
                projections[input_hash] = projection
            eligible = (
                type(projection) is _CurrentBuild
                and row["input_json"] == projection.input_json.text
                and row["build_hash"] == projection.build_hash
            )
            if not eligible:
                skipped.append(
                    {
                        "artifact_id": artifact_id,
                        "input_hash": input_hash,
                        "reason": "superseded-build",
                    }
                )
                continue
            if input_hash in candidates:
                raise IntegrityError(
                    f"multiple verified candidates claim current input {input_hash}"
                )
            predecessor = retained.get(input_hash)
            if (
                predecessor is not None
                and row["input_json"] != predecessor[0]["input_json"]
            ):
                raise IntegrityError(
                    "equal input digest maps to unequal canonical inputs"
                )
            report, function_entry = self._function_promotion_entry(
                connection,
                row,
                promoted=False,
            )
            candidates[input_hash] = (row, report, function_entry)

        final = dict(retained)
        final.update(candidates)
        planned: list[_FunctionPromotionPlanEntry] = []
        for input_hash in sorted(final):
            row, report, function_entry = final[input_hash]
            candidate = input_hash in candidates
            predecessor = retained.get(input_hash)
            planned.append(
                _FunctionPromotionPlanEntry(
                    row=row,
                    report=report,
                    function_entry=function_entry,
                    public=FunctionPromotionEntry(
                        artifact_id=str(row["id"]),
                        input_hash=input_hash,
                        artifact_hash=str(row["artifact_hash"]),
                        output_hash=str(row["output_hash"]),
                        entry_seal=function_entry.entry_seal,
                        disposition="candidate" if candidate else "retained",
                        replaces_artifact_id=(
                            str(predecessor[0]["id"])
                            if candidate and predecessor is not None
                            else None
                        ),
                    ),
                )
            )
        planned_entries = tuple(planned)
        document = build_function(
            partition=partition,
            operation=operation,
            operation_revision=revision,
            policy_hash=policy_hash,
            entries=(entry.function_entry for entry in planned_entries),
        )
        public_entries = tuple(entry.public for entry in planned_entries)
        skipped_entries = tuple(skipped)
        encoded = canonicalize(
            {
                "abi": FUNCTION_PROMOTION_MANIFEST_ABI,
                "entries": [
                    {
                        "artifact_hash": entry.artifact_hash,
                        "artifact_id": entry.artifact_id,
                        "disposition": entry.disposition,
                        "entry_seal": entry.entry_seal,
                        "input_hash": entry.input_hash,
                        "output_hash": entry.output_hash,
                        "replaces_artifact_id": entry.replaces_artifact_id,
                    }
                    for entry in public_entries
                ],
                "function": document.value,
                "function_hash": document.function_hash,
                "scope": {
                    "operation": operation,
                    "operation_revision": revision,
                    "partition": partition,
                    "policy_hash": policy_hash,
                },
                "skipped": list(skipped_entries),
            },
            max_bytes=_FUNCTION_MANIFEST_MAX_BYTES,
            max_depth=_FUNCTION_MANIFEST_MAX_DEPTH,
            max_items=_FUNCTION_MANIFEST_MAX_ITEMS,
        )
        return _FunctionPromotionPlan(
            manifest=FunctionPromotionManifest(
                operation_revision=revision,
                function_hash=document.function_hash,
                text=encoded.text,
                document=document,
                entries=public_entries,
                skipped=skipped_entries,
            ),
            policy_hash=policy_hash,
            entries=planned_entries,
        )

    def inspect_function_promotion(
        self,
        partition: str,
        operation: str,
    ) -> FunctionPromotionManifest:
        """Build the deterministic prospective function without mutation."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        with self.store.transaction(write=False) as connection:
            return self._function_promotion_plan(
                connection,
                partition=partition,
                operation=operation,
            ).manifest

    def promote_function(
        self,
        partition: str,
        operation: str,
        *,
        expected_function_hash: str,
        promoted_by: str,
    ) -> FunctionSetPromotion:
        """Promote the locked prospective union in one immediate transaction."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        expected_function_hash = _digest(
            expected_function_hash,
            "expected_function_hash",
        )
        promoted_by = _text(promoted_by, "promoted_by", maximum=256)
        with self.store.transaction(write=True) as connection:
            locked = self._function_promotion_plan(
                connection,
                partition=partition,
                operation=operation,
            )
            if not locked.entries:
                raise StateError("function promotion requires at least one member")
            if locked.manifest.function_hash != expected_function_hash:
                raise ConflictError(
                    "expected_function_hash does not match the locked prospective function"
                )
            now = self._now()
            receipt_id = _new_id("fpr")

            candidates = tuple(
                entry
                for entry in locked.entries
                if entry.public.disposition == "candidate"
            )
            retired_ids = tuple(
                sorted(
                    {
                        entry.public.replaces_artifact_id
                        for entry in locked.entries
                        if entry.public.replaces_artifact_id is not None
                    }
                )
            )
            for artifact_id in retired_ids:
                changed = connection.execute(
                    """
                    UPDATE artifacts
                    SET status = 'retired', promotion_hash = NULL,
                        status_reason = 'replaced by function promotion'
                    WHERE id = ? AND status = 'promoted'
                    """,
                    (artifact_id,),
                ).rowcount
                if changed != 1:
                    raise StateError(
                        "function predecessor changed before locked retirement"
                    )

            for entry in candidates:
                row = entry.row
                report = entry.report
                promotion_hash = _digest_strings(
                    "cement-promotion-v2",
                    (
                        str(row["id"]),
                        str(row["artifact_hash"]),
                        str(row["build_hash"]),
                        str(row["policy_hash"]),
                        str(row["evidence_snapshot_hash"]),
                        str(row["support"]),
                        str(row["reviewer_count"]),
                        str(row["span_seconds"]),
                        str(row["scope_hash"]),
                        str(report["id"]),
                        str(report["details_hash"]),
                        str(report["test_set_hash"]),
                        str(report["test_count"]),
                        str(report["passed"]),
                        promoted_by,
                        str(now),
                    ),
                )
                changed = connection.execute(
                    """
                    UPDATE artifacts
                    SET status = 'promoted', promoted_by = ?, promoted_at_us = ?,
                        promotion_hash = ?, status_reason = NULL
                    WHERE id = ? AND status = 'verified'
                    """,
                    (promoted_by, now, promotion_hash, row["id"]),
                ).rowcount
                if changed != 1:
                    raise StateError(
                        "function candidate changed before locked activation"
                    )

            member_ids = tuple(
                sorted(entry.public.artifact_id for entry in locked.entries)
            )
            candidate_ids = tuple(
                sorted(entry.public.artifact_id for entry in candidates)
            )
            membership_rows = tuple(
                {
                    "receipt_id": receipt_id,
                    "ordinal": ordinal,
                    "function_hash": locked.manifest.function_hash,
                    "artifact_id": entry.public.artifact_id,
                    "report_id": str(entry.report["id"]),
                    "input_hash": entry.public.input_hash,
                    "entry_seal": entry.public.entry_seal,
                }
                for ordinal, entry in enumerate(locked.entries)
            )
            membership_hash = _membership_hash(membership_rows)
            candidate_ids_hash = _id_list_hash(candidate_ids)
            retired_ids_hash = _id_list_hash(retired_ids)
            receipt_fields: dict[str, object] = {
                "id": receipt_id,
                "partition": partition,
                "operation": operation,
                "operation_revision": locked.manifest.operation_revision,
                "policy_hash": locked.policy_hash,
                "function_hash": locked.manifest.function_hash,
                "membership_hash": membership_hash,
                "member_count": len(membership_rows),
                "candidate_artifact_ids_hash": candidate_ids_hash,
                "candidate_count": len(candidate_ids),
                "retired_artifact_ids_hash": retired_ids_hash,
                "retired_count": len(retired_ids),
                "promoted_by": promoted_by,
                "promoted_at_us": now,
            }
            receipt_hash = _function_receipt_hash(receipt_fields)
            connection.executemany(
                """
                INSERT INTO function_memberships(
                    receipt_id, ordinal, function_hash, artifact_id, report_id,
                    input_hash, entry_seal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["receipt_id"],
                        row["ordinal"],
                        row["function_hash"],
                        row["artifact_id"],
                        row["report_id"],
                        row["input_hash"],
                        row["entry_seal"],
                    )
                    for row in membership_rows
                ],
            )
            connection.execute(
                """
                INSERT INTO function_receipts(
                    id, partition, operation, operation_revision, policy_hash,
                    function_hash, membership_hash, member_count,
                    candidate_artifact_ids_hash, candidate_count,
                    retired_artifact_ids_hash, retired_count, promoted_by,
                    promoted_at_us, receipt_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    partition,
                    operation,
                    receipt_fields["operation_revision"],
                    receipt_fields["policy_hash"],
                    locked.manifest.function_hash,
                    membership_hash,
                    len(membership_rows),
                    candidate_ids_hash,
                    len(candidate_ids),
                    retired_ids_hash,
                    len(retired_ids),
                    promoted_by,
                    now,
                    receipt_hash,
                ),
            )
            member_projection = _id_list_projection(member_ids)
            candidate_projection = _id_list_projection(candidate_ids)
            retired_projection = _id_list_projection(retired_ids)
            _event(
                connection,
                partition=partition,
                kind="function.promoted",
                subject_type="function",
                subject_id=receipt_id,
                payload={
                    "candidate_artifact_count": candidate_projection[0],
                    "candidate_artifact_ids": candidate_projection[1],
                    "candidate_artifact_ids_hash": candidate_projection[2],
                    "function_hash": locked.manifest.function_hash,
                    "member_artifact_count": member_projection[0],
                    "member_artifact_ids": member_projection[1],
                    "member_artifact_ids_hash": member_projection[2],
                    "promoted_by": promoted_by,
                    "receipt_hash": receipt_hash,
                    "receipt_id": receipt_id,
                    "retired_artifact_count": retired_projection[0],
                    "retired_artifact_ids": retired_projection[1],
                    "retired_artifact_ids_hash": retired_projection[2],
                },
                now_us=now,
            )

        return FunctionSetPromotion(
            receipt_id=receipt_id,
            receipt_hash=receipt_hash,
            function_hash=locked.manifest.function_hash,
            operation_revision=locked.manifest.operation_revision,
            member_artifact_ids=member_ids,
            candidate_artifact_ids=candidate_ids,
            retired_artifact_ids=retired_ids,
            promoted_at_us=now,
        )

    def promote(
        self,
        partition: str,
        artifact_id: str,
        *,
        scope_hash: str,
        promoted_by: str,
    ) -> Promotion:
        partition = _name(partition, "partition")
        artifact_id = _request_id(artifact_id)
        promoted_by = _text(promoted_by, "promoted_by", maximum=256)
        if type(scope_hash) is not str or not re.fullmatch(r"[0-9a-f]{64}", scope_hash):
            raise ValidationError("scope_hash must be a SHA-256 hex digest")
        now = self._now()
        with self.store.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ? AND partition = ?",
                (artifact_id, partition),
            ).fetchone()
            if row is None:
                raise NotFoundError("artifact does not exist in this partition")
            if row["status"] != "verified" or not row["verified_report_id"]:
                raise StateError("artifact must have a current passing verification report")
            if row["scope_hash"] != scope_hash:
                raise ConflictError("requested promotion scope does not equal the tested scope")
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                (row["verified_report_id"], artifact_id),
            ).fetchone()
            if report is None or not int(report["passed"]):
                raise StateError("artifact's bound verification report is missing or failed")
            report_details = self._validate_report(connection, report)
            if (
                type(report_details.value) is not dict
                or report_details.value.get("scope_hash") != row["scope_hash"]
            ):
                raise IntegrityError("verification report scope binding mismatch")
            for field in (
                "artifact_hash",
                "build_hash",
                "policy_hash",
                "evidence_snapshot_hash",
            ):
                if report[field] != row[field]:
                    raise IntegrityError(f"verification report {field} binding mismatch")
            failures, _, artifact = self._run_verification(connection, row)
            if failures:
                raise StateError("artifact changed or became stale after verification: " + failures[0])
            if artifact.scope_digest != scope_hash:
                raise IntegrityError("artifact scope digest mismatch")
            previous = connection.execute(
                """
                SELECT id FROM artifacts
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND input_hash = ? AND status = 'promoted' AND id <> ?
                """,
                (
                    partition,
                    row["operation"],
                    row["operation_revision"],
                    row["input_hash"],
                    artifact_id,
                ),
            ).fetchall()
            replaced = tuple(str(item["id"]) for item in previous)
            if previous:
                connection.executemany(
                    """
                    UPDATE artifacts
                    SET status = 'retired', promotion_hash = NULL,
                        status_reason = 'replaced by verified build'
                    WHERE id = ? AND status = 'promoted'
                    """,
                    [(item,) for item in replaced],
                )
            promotion_hash = _digest_strings(
                "cement-promotion-v2",
                (
                    artifact_id,
                    str(row["artifact_hash"]),
                    str(row["build_hash"]),
                    str(row["policy_hash"]),
                    str(row["evidence_snapshot_hash"]),
                    str(row["support"]),
                    str(row["reviewer_count"]),
                    str(row["span_seconds"]),
                    str(row["scope_hash"]),
                    str(report["id"]),
                    str(report["details_hash"]),
                    str(report["test_set_hash"]),
                    str(report["test_count"]),
                    str(report["passed"]),
                    promoted_by,
                    str(now),
                ),
            )
            connection.execute(
                """
                UPDATE artifacts SET status = 'promoted', promoted_by = ?, promoted_at_us = ?,
                    promotion_hash = ?, status_reason = NULL
                WHERE id = ? AND status = 'verified'
                """,
                (promoted_by, now, promotion_hash, artifact_id),
            )
            _event(
                connection,
                partition=partition,
                kind="artifact.promoted",
                subject_type="artifact",
                subject_id=artifact_id,
                payload={
                    "promoted_by": promoted_by,
                    "replaced_artifact_ids": list(replaced),
                    "scope_hash": scope_hash,
                },
                now_us=now,
            )
        return Promotion(
            artifact_id=artifact_id,
            replaced_artifact_ids=replaced,
            promoted_at_us=now,
        )

    # -- drift, revocation, inspection --------------------------------------

    def challenge(
        self,
        partition: str,
        operation: str,
        input_value: object,
        expected_output: object,
        *,
        reviewer: str,
        note: str = "",
    ) -> tuple[str, bool]:
        """Confirm an active scope; quarantine immediately on disagreement.

        Returns ``(example_id, suspended)``.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        reviewer = _text(reviewer, "reviewer", maximum=256)
        note = _text(note, "note", maximum=2_048, allow_empty=True)
        input_json = canonicalize(input_value)
        expected = canonicalize(expected_output)
        now = self._now()
        example_id = _new_id("ex")

        quarantined: list[str] = []
        with self.store.transaction(write=True) as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = int(registered["revision"])
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND input_hash = ? AND status = 'promoted'
                """,
                (partition, operation, revision, input_json.digest),
            ).fetchall()
            for row in rows:
                try:
                    self._artifact_from_row(row)
                    self._validate_promoted(connection, row)
                except (IntegrityError, ValidationError):
                    artifact_id = str(row["id"])
                    connection.execute(
                        """
                        UPDATE artifacts
                        SET status = 'suspended', promotion_hash = NULL,
                            status_reason = 'challenge integrity failure'
                        WHERE id = ? AND status = 'promoted'
                        """,
                        (artifact_id,),
                    )
                    _event(
                        connection,
                        partition=partition,
                        kind="artifact.integrity_quarantined",
                        subject_type="artifact",
                        subject_id=artifact_id,
                        payload={"source": "challenge"},
                        now_us=now,
                    )
                    quarantined.append(artifact_id)
        if quarantined:
            raise StateError("challenge quarantined an integrity-invalid artifact; retry after review")

        with self.store.transaction(write=True) as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = int(registered["revision"])
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND input_hash = ? AND status = 'promoted'
                """,
                (partition, operation, revision, input_json.digest),
            ).fetchall()
            matches: list[tuple[sqlite3.Row, CanonicalJSON]] = []
            for row in rows:
                artifact = self._artifact_from_row(row)
                self._validate_promoted(connection, row)
                execution = execute(
                    artifact,
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                    input_json=input_json,
                )
                if execution.matched:
                    matches.append((row, canonicalize(execution.output)))
            if len(matches) != 1:
                raise StateError("challenge requires exactly one active artifact match")
            artifact_row, observed = matches[0]
            suspended = observed.text != expected.text
            receipt = canonicalize(
                {
                    "artifact_id": str(artifact_row["id"]),
                    "confirmed_at_us": now,
                    "example_id": example_id,
                    "format": "cement-confirmation-v1",
                    "input": input_json.value,
                    "note": note,
                    "operation": operation,
                    "operation_revision": revision,
                    "output": expected.value,
                    "partition": partition,
                    "resolution": "challenge",
                    "reviewer": reviewer,
                },
                max_bytes=_RECEIPT_MAX_BYTES,
            )
            connection.execute(
                """
                INSERT INTO examples(
                    id, partition, operation, operation_revision, input_json, input_hash,
                    output_json, output_hash, reviewer, origin, receipt_json, receipt_hash,
                    confirmed_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'challenge', ?, ?, ?)
                """,
                (
                    example_id,
                    partition,
                    operation,
                    revision,
                    input_json.text,
                    input_json.digest,
                    expected.text,
                    expected.digest,
                    reviewer,
                    receipt.text,
                    receipt.digest,
                    now,
                ),
            )
            if suspended:
                connection.execute(
                    """
                    UPDATE artifacts
                    SET status = 'suspended', promotion_hash = NULL,
                        status_reason = 'confirmed counterexample'
                    WHERE id = ? AND status = 'promoted'
                    """,
                    (artifact_row["id"],),
                )
            _event(
                connection,
                partition=partition,
                kind="artifact.counterexample" if suspended else "artifact.challenged",
                subject_type="artifact",
                subject_id=str(artifact_row["id"]),
                payload={
                    "example_id": example_id,
                    "receipt_hash": receipt.digest,
                    "reviewer": reviewer,
                    "suspended": suspended,
                },
                now_us=now,
            )
        return example_id, suspended

    def revoke_example(
        self,
        partition: str,
        example_id: str,
        *,
        revoked_by: str,
        reason: str,
    ) -> tuple[str, ...]:
        partition = _name(partition, "partition")
        example_id = _request_id(example_id)
        revoked_by = _text(revoked_by, "revoked_by", maximum=256)
        reason = _text(reason, "reason", maximum=2_048)
        now = self._now()
        with self.store.transaction(write=True) as connection:
            example = connection.execute(
                "SELECT id FROM examples WHERE id = ? AND partition = ?",
                (example_id, partition),
            ).fetchone()
            if example is None:
                raise NotFoundError("example does not exist in this partition")
            try:
                connection.execute(
                    """
                    INSERT INTO example_revocations(example_id, revoked_by, reason, revoked_at_us)
                    VALUES (?, ?, ?, ?)
                    """,
                    (example_id, revoked_by, reason, now),
                )
            except sqlite3.IntegrityError as exc:
                raise StateError("example is already revoked") from exc
            dependents = connection.execute(
                """
                SELECT a.id FROM artifacts AS a
                JOIN artifact_evidence AS e ON e.artifact_id = a.id
                WHERE e.example_id = ? AND a.status IN ('draft', 'verified', 'promoted')
                ORDER BY a.id
                """,
                (example_id,),
            ).fetchall()
            suspended = tuple(str(row["id"]) for row in dependents)
            if suspended:
                connection.executemany(
                    """
                    UPDATE artifacts
                    SET status = 'suspended', promotion_hash = NULL,
                        status_reason = 'evidence revoked'
                    WHERE id = ?
                    """,
                    [(artifact_id,) for artifact_id in suspended],
                )
            _event(
                connection,
                partition=partition,
                kind="example.revoked",
                subject_type="example",
                subject_id=example_id,
                payload={
                    "reason": reason,
                    "revoked_by": revoked_by,
                    "suspended_artifact_count": len(suspended),
                    "suspended_artifact_ids": list(suspended[:100]),
                    "suspended_artifact_ids_hash": _id_list_hash(suspended),
                },
                now_us=now,
            )
        return suspended

    def suspend_artifact(
        self,
        partition: str,
        artifact_id: str,
        *,
        suspended_by: str,
        reason: str,
    ) -> None:
        partition = _name(partition, "partition")
        artifact_id = _request_id(artifact_id)
        suspended_by = _text(suspended_by, "suspended_by", maximum=256)
        reason = _text(reason, "reason", maximum=2_048)
        now = self._now()
        with self.store.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT status FROM artifacts WHERE id = ? AND partition = ?",
                (artifact_id, partition),
            ).fetchone()
            if row is None:
                raise NotFoundError("artifact does not exist in this partition")
            if row["status"] in {"retired", "suspended"}:
                raise StateError(f"artifact is already {row['status']}")
            connection.execute(
                """
                UPDATE artifacts SET status = 'suspended', promotion_hash = NULL,
                    status_reason = ? WHERE id = ?
                """,
                (reason, artifact_id),
            )
            _event(
                connection,
                partition=partition,
                kind="artifact.suspended",
                subject_type="artifact",
                subject_id=artifact_id,
                payload={"reason": reason, "suspended_by": suspended_by},
                now_us=now,
            )

    def operations(self, partition: str) -> list[dict[str, JSONValue]]:
        partition = _name(partition, "partition")
        with self.store.transaction() as connection:
            rows = connection.execute(
                """
                SELECT name, revision, policy_json, policy_hash, created_at_us, updated_at_us
                FROM operations WHERE partition = ? ORDER BY name
                """,
                (partition,),
            ).fetchall()
            return [
                {
                    "created_at_us": int(row["created_at_us"]),
                    "name": str(row["name"]),
                    "policy": parse_json(str(row["policy_json"]), max_bytes=16_384).value,
                    "policy_hash": str(row["policy_hash"]),
                    "revision": int(row["revision"]),
                    "updated_at_us": int(row["updated_at_us"]),
                }
                for row in rows
            ]

    def examples(
        self,
        partition: str,
        operation: str,
        *,
        include_revoked: bool = False,
        after_sequence: int = 0,
        limit: int = 1_000,
    ) -> list[dict[str, JSONValue]]:
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if type(include_revoked) is not bool:
            raise ValidationError("include_revoked must be a boolean")
        _bounded_int(
            after_sequence,
            "after_sequence",
            minimum=0,
            maximum=2**63 - 1,
        )
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)
        clause = "" if include_revoked else "AND x.example_id IS NULL"
        with self.store.transaction() as connection:
            rows = connection.execute(
                f"""
                SELECT e.*, x.revoked_by, x.reason AS revocation_reason, x.revoked_at_us
                FROM examples AS e
                LEFT JOIN example_revocations AS x ON x.example_id = e.id
                WHERE e.partition = ? AND e.operation = ? AND e.sequence > ? {clause}
                ORDER BY e.sequence LIMIT ?
                """,
                (partition, operation, after_sequence, limit),
            ).fetchall()
            return [
                {
                    "confirmed_at_us": int(row["confirmed_at_us"]),
                    "id": str(row["id"]),
                    "input": parse_json(str(row["input_json"])).value,
                    "operation_revision": int(row["operation_revision"]),
                    "origin": str(row["origin"]),
                    "output": parse_json(str(row["output_json"])).value,
                    "receipt_hash": str(row["receipt_hash"]),
                    "reviewer": str(row["reviewer"]),
                    "sequence": int(row["sequence"]),
                    "revocation": (
                        {
                            "at_us": int(row["revoked_at_us"]),
                            "by": str(row["revoked_by"]),
                            "reason": str(row["revocation_reason"]),
                        }
                        if row["revoked_at_us"] is not None
                        else None
                    ),
                }
                for row in rows
            ]

    def artifacts(
        self,
        partition: str,
        operation: str,
        *,
        after_sequence: int = 0,
        limit: int = 1_000,
    ) -> list[dict[str, JSONValue]]:
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        _bounded_int(
            after_sequence,
            "after_sequence",
            minimum=0,
            maximum=2**63 - 1,
        )
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)
        with self.store.transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = ? AND operation = ? AND sequence > ?
                ORDER BY sequence LIMIT ?
                """,
                (partition, operation, after_sequence, limit),
            ).fetchall()
            return [self._artifact_summary(row) for row in rows]

    def artifact(self, partition: str, artifact_id: str) -> dict[str, JSONValue]:
        partition = _name(partition, "partition")
        artifact_id = _request_id(artifact_id)
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ? AND partition = ?",
                (artifact_id, partition),
            ).fetchone()
            if row is None:
                raise NotFoundError("artifact does not exist in this partition")
            self._artifact_from_row(row)
            if row["status"] == "promoted":
                self._validate_promoted(connection, row)
            summary = self._artifact_summary(row)
            summary["document"] = parse_json(
                str(row["artifact_json"]), max_bytes=ARTIFACT_MAX_BYTES
            ).value
            summary["evidence_ids"] = [
                str(item["example_id"])
                for item in connection.execute(
                    """
                    SELECT example_id FROM artifact_evidence
                    WHERE artifact_id = ? ORDER BY example_id
                    """,
                    (artifact_id,),
                ).fetchall()
            ]
            return summary

    def report(
        self,
        partition: str,
        report_id: str,
        *,
        after_test_key: str = "",
        test_limit: int = 1_000,
    ) -> dict[str, JSONValue]:
        """Inspect immutable verification bindings and a stable test page."""

        partition = _name(partition, "partition")
        report_id = _request_id(report_id)
        after_test_key = _text(
            after_test_key, "after_test_key", maximum=256, allow_empty=True
        )
        _bounded_int(test_limit, "test_limit", minimum=1, maximum=10_000)
        with self.store.transaction() as connection:
            row = connection.execute(
                """
                SELECT r.*, a.partition, a.scope_hash
                FROM test_reports AS r JOIN artifacts AS a ON a.id = r.artifact_id
                WHERE r.id = ? AND a.partition = ?
                """,
                (report_id, partition),
            ).fetchone()
            if row is None:
                raise NotFoundError("verification report does not exist in this partition")
            details = self._validate_report(connection, row)
            tests = connection.execute(
                """
                SELECT test_key, example_id, passed, detail FROM artifact_tests
                WHERE report_id = ? AND test_key > ?
                ORDER BY test_key LIMIT ?
                """,
                (report_id, after_test_key, test_limit),
            ).fetchall()
            return {
                "artifact_hash": str(row["artifact_hash"]),
                "artifact_id": str(row["artifact_id"]),
                "build_hash": str(row["build_hash"]),
                "created_at_us": int(row["created_at_us"]),
                "details": details.value,
                "evidence_snapshot_hash": str(row["evidence_snapshot_hash"]),
                "id": report_id,
                "passed": bool(row["passed"]),
                "policy_hash": str(row["policy_hash"]),
                "sequence": int(row["sequence"]),
                "scope_hash": str(row["scope_hash"]),
                "test_count": int(row["test_count"]),
                "test_set_hash": str(row["test_set_hash"]),
                "tests": [
                    {
                        "detail": str(test["detail"]),
                        "example_id": (
                            str(test["example_id"]) if test["example_id"] is not None else None
                        ),
                        "key": str(test["test_key"]),
                        "passed": bool(test["passed"]),
                    }
                    for test in tests
                ],
            }

    def reports(
        self,
        partition: str,
        *,
        artifact_id: str | None = None,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> list[dict[str, JSONValue]]:
        """Monotonic immutable verification-report feed."""

        partition = _name(partition, "partition")
        if artifact_id is not None:
            artifact_id = _request_id(artifact_id)
        _bounded_int(
            after_sequence,
            "after_sequence",
            minimum=0,
            maximum=2**63 - 1,
        )
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)
        with self.store.transaction() as connection:
            rows = connection.execute(
                """
                SELECT r.*, a.scope_hash FROM test_reports AS r
                JOIN artifacts AS a ON a.id = r.artifact_id
                WHERE a.partition = ? AND (? IS NULL OR r.artifact_id = ?)
                  AND r.sequence > ?
                ORDER BY r.sequence LIMIT ?
                """,
                (
                    partition,
                    artifact_id,
                    artifact_id,
                    after_sequence,
                    limit,
                ),
            ).fetchall()
            result: list[dict[str, JSONValue]] = []
            for row in rows:
                self._validate_report(connection, row)
                result.append(
                    {
                        "artifact_id": str(row["artifact_id"]),
                        "build_hash": str(row["build_hash"]),
                        "created_at_us": int(row["created_at_us"]),
                        "id": str(row["id"]),
                        "passed": bool(row["passed"]),
                        "sequence": int(row["sequence"]),
                        "scope_hash": str(row["scope_hash"]),
                        "test_count": int(row["test_count"]),
                        "test_set_hash": str(row["test_set_hash"]),
                    }
                )
            return result

    def events(
        self,
        partition: str,
        *,
        after: int = 0,
        limit: int = 1_000,
    ) -> list[dict[str, JSONValue]]:
        """Read events carrying an exact partition binding."""

        partition = _name(partition, "partition")
        _bounded_int(after, "after", minimum=0, maximum=2**63 - 1)
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)
        with self.store.transaction() as connection:
            # Events deliberately avoid indexing private inputs. Subjects for
            # operations carry a partition prefix; other records are joined.
            rows = connection.execute(
                """
                SELECT * FROM events
                WHERE partition = ? AND sequence > ?
                ORDER BY sequence LIMIT ?
                """,
                (partition, after, limit),
            ).fetchall()
            return [
                {
                    "created_at_us": int(row["created_at_us"]),
                    "kind": str(row["kind"]),
                    "payload": parse_json(str(row["payload_json"]), max_bytes=262_144).value,
                    "sequence": int(row["sequence"]),
                    "subject_id": str(row["subject_id"]),
                    "subject_type": str(row["subject_type"]),
                }
                for row in rows
            ]

    @staticmethod
    def _artifact_summary(row: sqlite3.Row) -> dict[str, JSONValue]:
        return {
            "artifact_hash": str(row["artifact_hash"]),
            "build_hash": str(row["build_hash"]),
            "created_at_us": int(row["created_at_us"]),
            "evidence_snapshot_hash": str(row["evidence_snapshot_hash"]),
            "id": str(row["id"]),
            "input_hash": str(row["input_hash"]),
            "operation_revision": int(row["operation_revision"]),
            "promoted_at_us": (
                int(row["promoted_at_us"]) if row["promoted_at_us"] is not None else None
            ),
            "promotion_hash": str(row["promotion_hash"]) if row["promotion_hash"] else None,
            "reviewer_count": int(row["reviewer_count"]),
            "sequence": int(row["sequence"]),
            "scope_hash": str(row["scope_hash"]),
            "span_seconds": int(row["span_seconds"]),
            "status": str(row["status"]),
            "status_reason": str(row["status_reason"]) if row["status_reason"] else None,
            "support": int(row["support"]),
            "verified_report_id": (
                str(row["verified_report_id"]) if row["verified_report_id"] else None
            ),
        }

    @staticmethod
    def _validate_report(
        connection: sqlite3.Connection,
        row: sqlite3.Row | Mapping[str, Any],
        *,
        verify_test_set: bool = True,
    ) -> CanonicalJSON:
        details = parse_json(str(row["details_json"]), max_bytes=262_144)
        if details.digest != row["details_hash"] or type(details.value) is not dict:
            raise IntegrityError("verification report details digest mismatch")
        test_count = int(row["test_count"])
        if verify_test_set:
            stored_count, test_set_hash = System._test_snapshot(connection, str(row["id"]))
            if stored_count != test_count or test_set_hash != row["test_set_hash"]:
                raise IntegrityError("verification report test set mismatch")
        elif re.fullmatch(r"[0-9a-f]{64}", str(row["test_set_hash"])) is None:
            raise IntegrityError("verification report test set digest is invalid")
        failures = details.value.get("failures")
        if (
            details.value.get("tests") != test_count
            or type(failures) is not list
            or bool(row["passed"]) == bool(failures)
        ):
            raise IntegrityError("verification report outcome binding mismatch")
        return details

    @staticmethod
    def _validate_promoted(connection: sqlite3.Connection, row: sqlite3.Row) -> None:
        if row["status"] != "promoted":
            raise IntegrityError("artifact is not promoted")
        if (
            row["verified_report_id"] is None
            or row["promoted_by"] is None
            or row["promoted_at_us"] is None
            or row["promotion_hash"] is None
        ):
            raise IntegrityError("promoted artifact is missing activation bindings")
        report = connection.execute(
            "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
            (row["verified_report_id"], row["id"]),
        ).fetchone()
        if report is None or not int(report["passed"]):
            raise IntegrityError("promoted artifact has no passing bound report")
        for field in (
            "artifact_hash",
            "build_hash",
            "policy_hash",
            "evidence_snapshot_hash",
        ):
            if report[field] != row[field]:
                raise IntegrityError(f"promoted artifact report {field} binding mismatch")
        # Artifact tests and reports are sealed by schema triggers. Promotion
        # performed the full child-set replay/hash; dispatch verifies its bound
        # receipt without re-hashing up to one million immutable test rows.
        details = System._validate_report(connection, report, verify_test_set=False)
        if type(details.value) is not dict or details.value.get("scope_hash") != row["scope_hash"]:
            raise IntegrityError("promoted artifact report scope mismatch")
        expected = _digest_strings(
            "cement-promotion-v2",
            (
                str(row["id"]),
                str(row["artifact_hash"]),
                str(row["build_hash"]),
                str(row["policy_hash"]),
                str(row["evidence_snapshot_hash"]),
                str(row["support"]),
                str(row["reviewer_count"]),
                str(row["span_seconds"]),
                str(row["scope_hash"]),
                str(report["id"]),
                str(report["details_hash"]),
                str(report["test_set_hash"]),
                str(report["test_count"]),
                str(report["passed"]),
                str(row["promoted_by"]),
                str(row["promoted_at_us"]),
            ),
        )
        if expected != row["promotion_hash"]:
            raise IntegrityError("artifact promotion receipt mismatch")
        revoked = connection.execute(
            """
            SELECT 1 FROM artifact_evidence AS e
            JOIN example_revocations AS x ON x.example_id = e.example_id
            WHERE e.artifact_id = ? LIMIT 1
            """,
            (row["id"],),
        ).fetchone()
        if revoked is not None:
            raise IntegrityError("promoted artifact depends on revoked evidence")
        counterexample = connection.execute(
            """
            SELECT e.id FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND e.input_hash = ? AND e.input_json = ?
              AND e.output_json <> ? AND x.example_id IS NULL
            LIMIT 1
            """,
            (
                row["partition"],
                row["operation"],
                row["operation_revision"],
                row["input_hash"],
                row["input_json"],
                row["output_json"],
            ),
        ).fetchone()
        if counterexample is not None:
            raise IntegrityError("promoted artifact conflicts with active evidence")

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> ArtifactDocument:
        parsed = parse_json(str(row["artifact_json"]), max_bytes=ARTIFACT_MAX_BYTES)
        if parsed.digest != row["artifact_hash"]:
            raise IntegrityError("artifact document digest mismatch")
        artifact = validate_artifact(parsed.value)
        if artifact.digest != row["artifact_hash"] or artifact.scope_digest != row["scope_hash"]:
            raise IntegrityError("artifact semantic digest mismatch")
        if (
            artifact.input.text != row["input_json"]
            or artifact.input.digest != row["input_hash"]
            or artifact.output.text != row["output_json"]
            or artifact.output.digest != row["output_hash"]
        ):
            raise IntegrityError("artifact projection mismatch")
        policy = parse_json(str(row["policy_json"]), max_bytes=16_384)
        if policy.digest != row["policy_hash"]:
            raise IntegrityError("artifact policy digest mismatch")
        expected_build = build_digest(
            artifact_digest=artifact.digest,
            policy_digest=policy.digest,
            evidence_snapshot_digest=str(row["evidence_snapshot_hash"]),
            support=int(row["support"]),
            reviewer_count=int(row["reviewer_count"]),
            span_seconds=int(row["span_seconds"]),
        )
        if expected_build != row["build_hash"]:
            raise IntegrityError("artifact build digest mismatch")
        scope = artifact.value["scope"]
        if type(scope) is not dict:
            raise IntegrityError("artifact scope is malformed")
        if (
            scope["partition"] != row["partition"]
            or scope["operation"] != row["operation"]
            or scope["operation_revision"] != row["operation_revision"]
        ):
            raise IntegrityError("artifact scope projection mismatch")
        return artifact
