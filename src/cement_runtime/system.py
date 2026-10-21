"""Supervised fallback, evidence compilation, verification, and promotion."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
import unicodedata
import uuid
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
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
    FunctionAnchorReport,
    FunctionCheck,
    FunctionDiff,
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
    FunctionVersion,
    FunctionVersionPage,
    OperationArtifact,
    OperationArtifactStatus,
    OperationNowReport,
    PendingProposalGap,
    Promotion,
    ProposalView,
    ReviewResult,
    StaleRevisionAnomaly,
    SwitchState,
    VerificationReport,
)
from .projection import ProjectionProgram, parse_program, project
from .source import CandidateSource
from .store import Store

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_ENTITY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}\Z")
_UNSET = object()
_RECEIPT_MAX_BYTES = 3 * DEFAULT_MAX_BYTES
_CASE_KEY_MEMO_MAX = 65_536
_MAX_SQLITE_INTEGER = 2**63 - 1

PROVENANCE_MAX_BYTES = 65_536
"""Canonical byte bound on one candidate's provenance mapping.

Exported because a transport that must admit every submission the library
accepts has to derive its own bound from this one. A copy in another module is
a second source of truth that drifts silently.
"""
SOURCE_ID_MAX_BYTES = 512
"""UTF-8 byte bound on one proposal's source-observation id (one per partition + operation)."""


FUNCTION_PROMOTION_MANIFEST_ABI = "cement-function-promotion-manifest-v1"
FUNCTION_PROMOTION_RECEIPT_ABI = "cement-function-promotion-v2"
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
    dropped: tuple[str, ...] = ()


def _name(value: str, label: str) -> str:
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise ValidationError(
            f"{label} must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"
        )
    return value


def _entity_id(value: str, label: str) -> str:
    if type(value) is not str or _ENTITY_ID.fullmatch(value) is None:
        raise ValidationError(f"{label} must be a bounded ASCII identifier")
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


def _is_digest(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _digest(value: str, label: str) -> str:
    if not _is_digest(value):
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
            # `projection_hash` is NULL in exact mode; "" cannot collide with a 64-hex digest.
            str(row["projection_hash"] or ""),
        ),
    )


def _function_receipt_from_row(
    row: sqlite3.Row | Mapping[str, Any],
) -> FunctionReceipt:
    try:
        receipt_id = _entity_id(row["id"], "receipt_id")
        partition = _name(row["partition"], "stored function receipt partition")
        operation = _name(row["operation"], "stored function receipt operation")
        promoted_by = _text(
            row["promoted_by"],
            "stored function receipt promoted_by",
            maximum=256,
        )
        policy_hash = _digest(row["policy_hash"], "stored function receipt policy_hash")
        function_hash = _digest(row["function_hash"], "stored function receipt function_hash")
        membership_hash = _digest(row["membership_hash"], "stored function receipt membership_hash")
        candidate_artifact_ids_hash = _digest(
            row["candidate_artifact_ids_hash"],
            "stored function receipt candidate_artifact_ids_hash",
        )
        retired_artifact_ids_hash = _digest(
            row["retired_artifact_ids_hash"],
            "stored function receipt retired_artifact_ids_hash",
        )
        receipt_hash = _digest(row["receipt_hash"], "stored function receipt receipt_hash")
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
    if any(type(value) is not int for value in integers.values()):
        raise IntegrityError("stored function receipt has invalid scalar fields")
    sequence = integers["sequence"]
    operation_revision = integers["operation_revision"]
    member_count = integers["member_count"]
    candidate_count = integers["candidate_count"]
    retired_count = integers["retired_count"]
    promoted_at_us = integers["promoted_at_us"]
    if not 1 <= sequence <= _MAX_SQLITE_INTEGER:
        raise IntegrityError("stored function receipt sequence is invalid")
    if not 1 <= operation_revision <= _MAX_SQLITE_INTEGER:
        raise IntegrityError("stored function receipt operation revision is invalid")
    if not 1 <= member_count <= FUNCTION_MAX_ENTRIES:
        raise IntegrityError("stored function receipt member count is invalid")
    # A program change retires members that no candidate replaces (contract §5), so retirements
    # are bounded by the largest set that can have existed, not by this receipt's candidates.
    if not (0 <= candidate_count <= member_count and 0 <= retired_count <= FUNCTION_MAX_ENTRIES):
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


def _stored_program(row: sqlite3.Row) -> ProjectionProgram:
    """Parse a stored projection program and recompute its hash (contract §1 S7)."""

    try:
        program = parse_program(parse_json(str(row["program_json"])).value)
    except ValidationError as exc:
        raise IntegrityError("stored projection program is invalid") from exc
    if program.program_hash != row["program_hash"]:
        raise IntegrityError("stored projection program does not hash to its key")
    return program


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
# These functions are the ONLY definitions that read a proposal's scope (operation, operation
# revision, canonical input) on behalf of the proposal read, review and report paths. Consumers
# supply parameters through a named selection and never SQL; a consumer that composes its own
# query has inverted the confinement gate even though the complement assertion still passes.


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
    """One proposal row with its validated scope columns.

    ``row`` holds the raw columns the row-to-shape converters consume; every field beside it is
    the same row's scope, validated once here.
    """

    proposal_id: str
    partition: str
    operation: str
    operation_revision: int
    input_json: str
    input_hash: str
    row: sqlite3.Row


@dataclass(frozen=True, slots=True)
class _ProposalBindingSet:
    total: int
    rows: tuple[_ProposalBinding, ...]


def _proposal_binding_from_row(row: sqlite3.Row, *, partition: str) -> _ProposalBinding:
    try:
        proposal_id = _entity_id(row["id"], "proposal_id")
        operation = _name(row["operation"], "operation")
        operation_revision = _stored_int(
            row["operation_revision"],
            "proposal operation revision",
            minimum=1,
        )
        input_hash = _digest(row["input_hash"], "proposal input_hash")
        input_json = str(row["input_json"])
    except (IndexError, KeyError, TypeError, ValidationError) as exc:
        raise IntegrityError("proposal row has invalid scope fields") from exc
    if row["partition"] != partition:
        raise IntegrityError("proposal row belongs to another partition")
    return _ProposalBinding(
        proposal_id=proposal_id,
        partition=partition,
        operation=operation,
        operation_revision=operation_revision,
        input_json=input_json,
        input_hash=input_hash,
        row=row,
    )


def _proposal_bindings(
    connection: sqlite3.Connection,
    *,
    partition: str,
    selection: _ProposalIds | _ProposalFeed | _PendingProposals,
) -> _ProposalBindingSet:
    """Resolve proposals by id set, by status feed, or as one operation's pending page.

    `_PendingProposals` issues an unbounded count and a bounded detail: the count is the total the
    report publishes, and the detail materializes only the rows the caller reads.
    """

    if type(selection) is _ProposalIds:
        if not selection.values:
            return _ProposalBindingSet(total=0, rows=())
        if len(set(selection.values)) != len(selection.values):
            raise IntegrityError("proposal binding selection contains duplicate identifiers")
        placeholders = ", ".join("?" for _ in selection.values)
        rows = connection.execute(
            f"""
            SELECT * FROM proposals
            WHERE partition = ? AND id IN ({placeholders})
            """,  # noqa: S608 — only code-chosen fragments; every value binds as `?`
            (partition, *selection.values),
        ).fetchall()
    elif type(selection) is _ProposalFeed:
        rows = connection.execute(
            """
            SELECT * FROM proposals
            WHERE partition = ? AND (? IS NULL OR status = ?) AND status_sequence > ?
            ORDER BY status_sequence LIMIT ?
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
        count_row = connection.execute(
            """
            SELECT COUNT(*) AS item_count FROM proposals
            WHERE partition = ? AND operation = ? AND status = 'pending'
            """,
            (partition, selection.operation),
        ).fetchone()
        if count_row is None:
            raise IntegrityError("pending proposal count is missing")
        total = _stored_int(count_row["item_count"], "pending proposal count")
        rows = connection.execute(
            """
            SELECT * FROM proposals
            WHERE partition = ? AND operation = ? AND status = 'pending'
            ORDER BY status_sequence LIMIT ?
            """,
            (partition, selection.operation, selection.limit),
        ).fetchall()
        return _ProposalBindingSet(
            total=total,
            rows=tuple(_proposal_binding_from_row(row, partition=partition) for row in rows),
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


class System:
    """Local learning loop.

    All returned values are pure data. A caller applies a resolved plan only
    after its own live authorization/policy gate. Cement makes no principal or
    permission decision. Every control-plane mutation and every read relies on the
    embedding application's access control, and database access is the trust
    boundary. Actor and reviewer arguments are recorded assertions only.
    """

    def __init__(
        self,
        database: str | os.PathLike[str],
        *,
        create: bool = True,
        candidate_source: CandidateSource | None = None,
        clock_us: Callable[[], int] | None = None,
    ) -> None:
        # A source is classified where it is invoked, never here: reading
        # ``propose`` off a descriptor already executes caller-supplied code, so a
        # constructor pre-flight is the very hazard it looks like a guard against.
        if clock_us is not None and not callable(clock_us):
            raise ValidationError("clock_us must be callable")
        self.store = Store(database, create=create)
        self.candidate_source = candidate_source
        self._clock_us = clock_us if clock_us is not None else (lambda: time.time_ns() // 1_000)

    def _now(self) -> int:
        now = self._clock_us()
        if type(now) is not int or now < 0 or now > _MAX_SQLITE_INTEGER:
            raise StateError("clock must return a signed 64-bit microsecond timestamp")
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
                    return _stored_int(existing["revision"], "stored operation revision", minimum=1)
                raise ConflictError(
                    "operation exists with a different policy; revise it explicitly"
                )
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
            previous = _stored_int(current["revision"], "stored operation revision", minimum=1)
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
        provenance = canonicalize(dict(candidate.provenance), max_bytes=PROVENANCE_MAX_BYTES)
        return proposed, provenance

    def _submission_revision(self, partition: str, operation: str) -> int:
        with self.store.transaction() as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
        if registered is None:
            raise NotFoundError("operation is not registered in this partition")
        return _stored_int(registered["revision"], "stored operation revision", minimum=1)

    def _persist_proposal(
        self,
        *,
        partition: str,
        operation: str,
        expected_revision: int | None,
        source_id: str | None,
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
            revision = _stored_int(registered["revision"], "stored operation revision", minimum=1)
            if expected_revision is not None and revision != expected_revision:
                raise StateError("operation revision changed before proposal submission")
            if source_id is not None:
                existing = connection.execute(
                    """
                    SELECT id FROM proposals
                    WHERE partition = ? AND operation = ? AND source_id = ?
                    """,
                    (partition, operation, source_id),
                ).fetchone()
                if existing is not None:
                    raise ConflictError(
                        f"source observation already recorded as proposal {existing['id']}"
                    )
            proposal_id = _new_id("prop")
            created = self._now()
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
                    id, partition, operation, operation_revision, input_json, input_hash,
                    source_id, proposed_output_json, proposed_output_hash, provenance_json,
                    provenance_hash, status, created_at_us, status_sequence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    proposal_id,
                    partition,
                    operation,
                    revision,
                    input_json.text,
                    input_json.digest,
                    source_id,
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
        source_id: str | None = None,
    ) -> str:
        """Submit a candidate that the caller generated, as a pending proposal.

        The call writes one proposal row and one ``proposal.created`` event. It
        never invokes the configured candidate source.

        ``source_id`` names the source observation (for example deployment, chat,
        user message and input digest). A second proposal with the same
        ``source_id`` for the same partition and operation raises
        ``ConflictError`` naming the first, so one observation counts once.
        Without a ``source_id``, Cement gives no idempotency: two calls with
        identical content write two proposals and return two identifiers.

        Return the identifier of the new proposal.

        The call opens one transaction and binds whatever operation revision is
        current under that write lock. It captures no earlier revision, so a
        concurrent revision change cannot make it fail.

        Raise ``ValidationError`` for a rejected partition, operation, input
        value, candidate, or ``source_id``. Raise ``NotFoundError`` when the
        partition holds no such operation.

        A failure before the commit writes nothing. If the commit itself
        succeeds and then fails, the call raises and returns no identifier while
        the two rows stay durable. Recover by listing the partition's pending
        proposals. A retry with the same ``source_id`` raises ``ConflictError``
        naming the stored proposal; a retry without one writes a second proposal.
        """
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if source_id is not None:
            source_id = _text(source_id, "source_id", maximum=SOURCE_ID_MAX_BYTES)
        input_json = canonicalize(input_value)
        proposed, provenance = self._canonical_candidate(candidate)
        return self._persist_proposal(
            partition=partition,
            operation=operation,
            expected_revision=None,
            source_id=source_id,
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

        Cement writes one proposal row, one ``proposal.created`` event, and no
        other row. That count covers Cement's
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
        the two rows stay durable. Recover by listing the partition's pending
        proposals; never retry, because a retry writes a second proposal.
        """
        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        input_json = canonicalize(input_value)
        source = self.candidate_source
        if source is None:
            raise StateError("candidate source is not configured")
        revision = self._submission_revision(partition, operation)
        try:
            candidate = source.propose(
                CandidateRequest(
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                    input=input_json.value,
                )
            )
            generated = self._canonical_candidate(candidate)
        except Exception:  # noqa: BLE001 — adapter boundary: every adapter failure is contained totally (runtime.md)
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
            source_id=None,
            input_json=input_json,
            proposed=proposed,
            provenance=provenance,
        )

    @staticmethod
    def _proposal_content(
        binding: _ProposalBinding,
    ) -> tuple[CanonicalJSON, CanonicalJSON, CanonicalJSON]:
        # A stored value that will not parse is ledger corruption, so it reports as
        # IntegrityError rather than escaping as the ValidationError that parse_json
        # raises for caller input.
        row = binding.row
        try:
            input_json = parse_json(binding.input_json)
            proposed = parse_json(str(row["proposed_output_json"]))
            provenance = parse_json(str(row["provenance_json"]), max_bytes=PROVENANCE_MAX_BYTES)
        except ValidationError as exc:
            raise IntegrityError("stored proposal content is not valid JSON") from exc
        if input_json.digest != binding.input_hash:
            raise IntegrityError("proposal input digest mismatch")
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
        # Each review field is checked on its own: an all-or-nothing test lets a PARTIAL review
        # (one field set) pass as pending, where `review` would then overwrite it.
        review = [row[field] is not None for field in ("reviewer", "review_note", "reviewed_at_us")]
        if status == "pending":
            valid = not final_present and not final_hash_present and not any(review)
        elif status == "rejected":
            valid = not final_present and not final_hash_present and all(review)
        elif status in {"accepted", "corrected"}:
            valid = final_present and final_hash_present and all(review)
        else:
            raise IntegrityError("proposal has an unknown status")
        if not valid:
            raise IntegrityError("proposal fields do not match its status")

    # -- supervision ---------------------------------------------------------

    def get_proposal(self, partition: str, proposal_id: str) -> ProposalView:
        partition = _name(partition, "partition")
        proposal_id = _entity_id(proposal_id, "proposal_id")
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
            input_json, proposed, provenance = self._proposal_content(binding)
            return ProposalView(
                id=proposal_id,
                partition=partition,
                operation=binding.operation,
                operation_revision=binding.operation_revision,
                input=input_json.value,
                proposed_output=proposed.value,
                provenance=provenance.value,
                created_at_us=_stored_int(row["created_at_us"], "stored proposal created_at_us"),
            )

    def proposal(self, partition: str, proposal_id: str) -> dict[str, JSONValue]:
        """Inspect pending or historical proposal state and bound provenance."""

        partition = _name(partition, "partition")
        proposal_id = _entity_id(proposal_id, "proposal_id")
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
            "created_at_us": _stored_int(row["created_at_us"], "stored proposal created_at_us"),
            "final_output": final_output.value if final_output is not None else None,
            "id": str(row["id"]),
            "input": input_json.value,
            "operation": binding.operation,
            "operation_revision": binding.operation_revision,
            "proposed_output": proposed.value,
            "provenance": provenance.value,
            "review_note": str(row["review_note"]) if row["review_note"] is not None else None,
            "reviewed_at_us": (
                _stored_int(row["reviewed_at_us"], "stored proposal reviewed_at_us")
                if row["reviewed_at_us"] is not None
                else None
            ),
            "reviewer": str(row["reviewer"]) if row["reviewer"] is not None else None,
            "sequence": _stored_int(
                row["status_sequence"], "stored proposal status_sequence", minimum=1
            ),
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
        proposal_id = _entity_id(proposal_id, "proposal_id")
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
            # The status alone guards the transition, so a pending row carrying review fields is
            # corruption the UPDATE below would launder; grade the whole shape first.
            self._validate_proposal_shape(row)
            current = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, binding.operation),
            ).fetchone()
            if decision != "reject" and (
                current is None
                or _stored_int(current["revision"], "stored operation revision", minimum=1)
                != binding.operation_revision
            ):
                raise StateError(
                    "proposal belongs to an obsolete operation revision; "
                    "reject it or use a new request"
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
                if proposal_update.rowcount != 1:
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

            final = canonicalize(corrected_output) if decision == "correct" else proposed
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
                "operation_revision": _stored_int(
                    row["operation_revision"], "stored proposal operation_revision", minimum=1
                ),
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
                    output_json, output_hash, reviewer, origin, proposal_id, source_id,
                    receipt_json, receipt_hash, confirmed_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    binding.row["source_id"],
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
                  AND status = 'promoted' AND projection_hash IS NULL
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
            # A newer different confirmation is a REVISION, never a contradiction (contract §3):
            # it leaves every artifact's status alone, so a pinned version survives it, while the
            # live set now fails verification on the contrary evidence and follow answers nothing.
            contradicted_ids = [str(item["id"]) for item in conflicting_artifacts]
            # X7: a projected artifact matches the new confirmation through its program's key.
            for artifact in connection.execute(
                """
                SELECT id, input_json, output_json, projection_hash FROM artifacts
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND status = 'promoted' AND projection_hash IS NOT NULL
                """,
                (partition, binding.operation, binding.operation_revision),
            ):
                program = self._program_by_hash(connection, str(artifact["projection_hash"]))
                if (
                    program is not None
                    and self._case_key_text(program, input_json.text, input_json.digest)
                    == artifact["input_json"]
                    and artifact["output_json"] != final.text
                ):
                    contradicted_ids.append(str(artifact["id"]))
            contradicted = tuple(contradicted_ids)
            if contradicted:
                for artifact_id in contradicted:
                    _event(
                        connection,
                        partition=partition,
                        kind="artifact.contradicted",
                        subject_type="artifact",
                        subject_id=artifact_id,
                        payload={"example_id": example_id, "proposal_id": proposal_id},
                        now_us=now,
                    )
            if proposal_update.rowcount != 1:
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
                    "contradicted_artifact_ids": list(contradicted),
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
        program: ProjectionProgram | None = None,
    ) -> _CurrentBuild | _BlockedBuild:
        partition = str(operation_row["partition"])
        operation = str(operation_row["name"])
        revision = _stored_int(operation_row["revision"], "stored operation revision", minimum=1)
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
            program=program,
        )
        assessment = self._assess_examples(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=input_hash,
                input_text=input_json,
                program=program,
            ),
            policy,
            reviewer_count=reviewer_count,
            projected=program is not None,
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
                program=program,
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
                projection_digest=None if program is None else program.program_hash,
            ),
        )

    def _current_build_projections(
        self,
        connection: sqlite3.Connection,
        operation_row: sqlite3.Row,
    ) -> Iterator[tuple[str, str, _CurrentBuild | _BlockedBuild]]:
        """Enumerate compile's current case keys without writing.

        Exact mode: one case per canonical input. Under the build-current projection program:
        one case per projected key; examples the program refuses form one blocked
        ``unprojected`` entry (input hash ``""``), so they never silently vanish.
        """

        partition = str(operation_row["partition"])
        operation = str(operation_row["name"])
        revision = _stored_int(operation_row["revision"], "stored operation revision", minimum=1)
        program = self._build_program(
            connection, partition=partition, operation=operation, revision=revision
        )
        active = """
            SELECT e.input_hash, e.input_json
            FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND x.example_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
            {group}
            ORDER BY e.input_hash, e.input_json
        """
        canonical_inputs: dict[str, str] = {}

        def checked(input_hash: str, input_text: str) -> None:
            previous = canonical_inputs.get(input_hash)
            if previous is not None and previous != input_text:
                raise IntegrityError("one input digest maps to multiple canonical inputs")
            canonical_inputs[input_hash] = input_text

        if program is None:
            # Exact mode streams one case per canonical input, checked and built as it arrives:
            # no example rows materialize; the duplicate check keeps one text per distinct input.
            for row in connection.execute(
                active.format(group="GROUP BY e.input_hash, e.input_json"),
                (partition, operation, revision),
            ):
                input_hash, input_text = str(row["input_hash"]), str(row["input_json"])
                checked(input_hash, input_text)
                yield (
                    input_hash,
                    input_text,
                    self._project_current_build(connection, operation_row, input_hash, input_text),
                )
            return
        # Under a program every example counts (an unprojected entry reports examples, not
        # distinct inputs), and keys exist only after every raw input is projected.
        rows = connection.execute(
            active.format(group=""), (partition, operation, revision)
        ).fetchall()
        for row in rows:
            checked(str(row["input_hash"]), str(row["input_json"]))
        keys: dict[str, str] = {}
        unprojected = 0
        for row in rows:
            key_text = self._case_key_text(program, str(row["input_json"]), str(row["input_hash"]))
            if key_text is None:
                unprojected += 1
                continue
            keys[parse_json(key_text).digest] = key_text
        if unprojected:
            yield (
                "",
                "",
                _BlockedBuild(
                    reasons=(f"unprojected: {unprojected} example(s) the projection refuses",),
                    support=unprojected,
                    reviewer_count=0,
                    span_seconds=0,
                ),
            )
        for key_hash, key_text in sorted(keys.items()):
            yield (
                key_hash,
                key_text,
                self._project_current_build(
                    connection, operation_row, key_hash, key_text, program=program
                ),
            )

    @staticmethod
    def _live_build(connection: sqlite3.Connection, build_hash: str) -> sqlite3.Row | None:
        """The artifact that already carries this build, so compile creates no second one."""

        row: sqlite3.Row | None = connection.execute(
            """
            SELECT id, status FROM artifacts
            WHERE build_hash = ? AND status IN ('building', 'draft', 'verified', 'promoted')
            ORDER BY id LIMIT 1
            """,
            (build_hash,),
        ).fetchone()
        return row

    def _build_projections(
        self, connection: sqlite3.Connection, registered: sqlite3.Row
    ) -> dict[str, _CurrentBuild | _BlockedBuild]:
        """Build-current case key hash → its build (blocked or current); unprojected excluded."""

        return {
            key_hash: build
            for key_hash, _, build in self._current_build_projections(connection, registered)
            if key_hash
        }

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
            revision = _stored_int(registered["revision"], "stored operation revision", minimum=1)
            program = self._build_program(
                connection, partition=partition, operation=operation, revision=revision
            )
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
                found = self._live_build(connection, projection.build_hash)
                if found is not None:
                    existing.append(str(found["id"]))
                    continue
                artifact_id = _new_id("art")
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, partition, operation, operation_revision, input_json, input_hash,
                        output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                        build_hash, policy_json, policy_hash, evidence_snapshot_hash,
                        projection_hash, status, support, reviewer_count, span_seconds,
                        created_at_us
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'building', ?, ?, ?, ?
                    )
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
                        None if program is None else program.program_hash,
                        projection.support,
                        projection.reviewer_count,
                        projection.span_seconds,
                        now,
                    ),
                )
                if program is None:
                    inserted_count = connection.execute(
                        """
                    INSERT INTO artifact_evidence(artifact_id, example_id)
                    SELECT ?, e.id FROM examples AS e
                    LEFT JOIN example_revocations AS x ON x.example_id = e.id
                    WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
                      AND e.input_hash = ? AND e.input_json = ? AND x.example_id IS NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id
                      )
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
                    ).rowcount
                else:
                    # A projected case is not expressible as SQL over input_hash: its evidence
                    # edges are the active examples whose projection equals the key.
                    evidence_ids = [
                        (artifact_id, str(row["id"]))
                        for row in self._active_evidence(
                            connection,
                            partition=partition,
                            operation=operation,
                            revision=revision,
                            input_hash=input_hash,
                            input_text=input_text,
                            order_by_id=True,
                            program=program,
                        )
                    ]
                    connection.executemany(
                        "INSERT INTO artifact_evidence(artifact_id, example_id) VALUES (?, ?)",
                        evidence_ids,
                    )
                    inserted_count = len(evidence_ids)
                if inserted_count != projection.support:
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
        projected: bool = False,
    ) -> dict[str, Any]:
        # `projected`: the case is a projection key, so its raw inputs differ by design and only
        # their shared key (checked by the caller) binds them.
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
                receipt = parse_json(str(row["receipt_json"]), max_bytes=_RECEIPT_MAX_BYTES)
            except ValidationError as exc:
                integrity_failure(f"example {row['id']} contains invalid canonical JSON: {exc}")
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
            timestamp = _stored_int(row["confirmed_at_us"], "stored example confirmed_at_us")
            earliest = timestamp if earliest is None else min(earliest, timestamp)
            latest = timestamp if latest is None else max(latest, timestamp)

        span_seconds = (
            (latest - earliest) // 1_000_000
            if earliest is not None and latest is not None and support >= 2
            else 0
        )
        policy_failures: list[str] = []
        if input_conflict and not projected:
            integrity_failure("evidence hash collision bound multiple canonical inputs")
        if output_conflict:
            policy_failures.append("confirmed outputs conflict")
        if support < policy.min_confirmations:
            policy_failures.append(
                f"support {support} is below required {policy.min_confirmations}"
            )
        effective_reviewer_count = len(reviewers) if reviewer_count is None else reviewer_count
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

    def _active_evidence(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        revision: int,
        input_hash: str,
        input_text: str,
        order_by_id: bool = False,
        program: ProjectionProgram | None = None,
    ) -> list[sqlite3.Row]:
        """Active examples (confirmed, unrevoked, unsuperseded) of one case.

        Exact mode keys the case on the canonical input itself; under ``program`` the case is
        every active example of the revision whose ``project(program, input)`` equals the key.
        """

        order = "e.id" if order_by_id else "e.confirmed_at_us, e.id"
        active = """
            FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND x.example_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
        """
        if program is None:
            return connection.execute(
                f"SELECT e.* {active} AND e.input_hash = ? AND e.input_json = ? ORDER BY {order}",
                (partition, operation, revision, input_hash, input_text),
            ).fetchall()
        return [
            row
            for row in connection.execute(
                f"SELECT e.* {active} ORDER BY {order}",
                (partition, operation, revision),
            )
            if self._case_key_text(program, str(row["input_json"]), str(row["input_hash"]))
            == input_text
        ]

    def _active_reviewer_count(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        revision: int,
        input_hash: str,
        input_text: str,
        program: ProjectionProgram | None = None,
    ) -> int:
        if program is None:
            # Exact mode counts in SQL; only a projected case needs its rows in Python.
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT e.reviewer) FROM examples AS e
                LEFT JOIN example_revocations AS x ON x.example_id = e.id
                WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
                  AND e.input_hash = ? AND e.input_json = ? AND x.example_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
                """,
                (partition, operation, revision, input_hash, input_text),
            ).fetchone()
            return _stored_int(row[0], "active reviewer count")
        rows = self._active_evidence(
            connection,
            partition=partition,
            operation=operation,
            revision=revision,
            input_hash=input_hash,
            input_text=input_text,
            program=program,
        )
        return len({str(row["reviewer"]) for row in rows})

    def _case_key_text(
        self, program: ProjectionProgram, input_text: str, input_hash: str
    ) -> str | None:
        """`project(program, input)`'s key text, or ``None`` for input the program refuses.

        Content-addressed (program hash + input digest), so the memo can never go stale; it
        evicts least-recently-used keys past `_CASE_KEY_MEMO_MAX`, so a long-lived ``System``
        holds a bounded number while one pass over fewer inputs never projects one twice.
        """

        memo = self.__dict__.setdefault("_case_keys", {})
        slot = (program.program_hash, input_hash)
        if slot in memo:
            memo[slot] = memo.pop(slot)  # dicts keep insertion order: move to the newest end
        else:
            if len(memo) >= _CASE_KEY_MEMO_MAX:
                del memo[next(iter(memo))]
            projected = project(program, parse_json(input_text).value)
            memo[slot] = projected.key.text if projected.matched and projected.key else None
        cached: str | None = memo[slot]
        return cached

    @staticmethod
    def _build_program(
        connection: sqlite3.Connection, *, partition: str, operation: str, revision: int
    ) -> ProjectionProgram | None:
        """The program NEW builds of this revision use: the newest setting, else exact mode."""

        row = connection.execute(
            """
            SELECT g.program_json, g.program_hash FROM projection_settings AS s
            JOIN projection_programs AS g ON g.program_hash = s.program_hash
            WHERE s.partition = ? AND s.operation = ? AND s.operation_revision = ?
            ORDER BY s.sequence DESC LIMIT 1
            """,
            (partition, operation, revision),
        ).fetchone()
        return None if row is None else _stored_program(row)

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
                "1" if _stored_int(row["passed"], "stored test passed", maximum=1) else "0",
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
        return _stored_int(row["entry_count"], "promoted entry count")

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
        row: sqlite3.Row | None = connection.execute(
            """
            SELECT * FROM function_receipts
            WHERE partition = ? AND operation = ? AND operation_revision = ?
            ORDER BY sequence DESC LIMIT 1
            """,
            (partition, operation, operation_revision),
        ).fetchone()
        return row

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
                _entity_id(membership["artifact_id"], "artifact_id")
                _entity_id(membership["report_id"], "report_id")
                membership_function_hash = _digest(
                    membership["function_hash"],
                    "stored membership function_hash",
                )
                input_hash = _digest(membership["input_hash"], "stored membership input_hash")
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
            raise IntegrityError("function receipt references a missing or foreign report")

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
                raise IntegrityError(f"function receipt member {ordinal} scope binding mismatch")
            if artifact_row["projection_hash"] != receipt_row["projection_hash"]:
                # One program per set (contract §5): the receipt's program alone serves it.
                raise IntegrityError(f"function receipt member {ordinal} program binding mismatch")
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
                details_value = details.value
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
                raise IntegrityError(f"function receipt member {ordinal} input digest mismatch")
            entry_seal = _function_entry_seal(artifact_row, report_row)
            if membership["entry_seal"] != entry_seal:
                raise IntegrityError(f"function receipt member {ordinal} entry seal mismatch")
            entries.append(
                FunctionEntry(
                    input=artifact.input.value,
                    output=artifact.output.value,
                    artifact_hash=str(artifact_row["artifact_hash"]),
                    evidence_snapshot_hash=str(artifact_row["evidence_snapshot_hash"]),
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
                projection=self._program_by_hash(connection, receipt_row["projection_hash"]),
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
            if type(stored_revision) is not int or not 1 <= stored_revision <= _MAX_SQLITE_INTEGER:
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

        with self.store.transaction(write=False) as connection:
            page_rows, cursor = self._receipt_rows(
                connection,
                partition=partition,
                operation=operation,
                operation_revision=operation_revision,
                before_sequence=before_sequence,
                limit=limit,
            )
            return FunctionReceiptPage(
                receipts=tuple(_function_receipt_from_row(row) for row in page_rows),
                next_before_sequence=cursor,
            )

    @staticmethod
    def _receipt_rows(
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        operation_revision: int | None,
        before_sequence: int | None,
        limit: int,
    ) -> tuple[list[sqlite3.Row], int | None]:
        """One page of receipt rows, newest first, and the cursor of the next page (if any)."""

        predicates = ["partition = ?", "operation = ?"]
        parameters: list[object] = [partition, operation]
        if operation_revision is not None:
            predicates.append("operation_revision = ?")
            parameters.append(operation_revision)
        if before_sequence is not None:
            predicates.append("sequence < ?")
            parameters.append(before_sequence)
        parameters.append(limit + 1)
        rows = connection.execute(
            f"""
            SELECT * FROM function_receipts
            WHERE {" AND ".join(predicates)}
            ORDER BY sequence DESC LIMIT ?
            """,  # noqa: S608 — only code-chosen fragments; every value binds as `?`
            parameters,
        ).fetchall()
        page = rows[:limit]
        return page, (
            _stored_int(page[-1]["sequence"], "receipt sequence", minimum=1)
            if len(rows) > limit
            else None
        )

    @staticmethod
    def _receipt_by_hash(
        connection: sqlite3.Connection, *, partition: str, operation: str, function_hash: str
    ) -> sqlite3.Row | None:
        """The newest receipt of this operation that bound ``function_hash``."""

        row: sqlite3.Row | None = connection.execute(
            """
            SELECT * FROM function_receipts
            WHERE partition = ? AND operation = ? AND function_hash = ?
            ORDER BY sequence DESC LIMIT 1
            """,
            (partition, operation, function_hash),
        ).fetchone()
        return row

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
            artifact_id = _entity_id(row["membership_artifact_id"], "artifact_id")
            report_id = _entity_id(row["membership_report_id"], "report_id")
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
            "evidence_snapshot_hash": row["bound_report_evidence_snapshot_hash"],
            "passed": row["bound_report_passed"],
            "details_json": row["bound_report_details_json"],
            "details_hash": row["bound_report_details_hash"],
            "test_count": row["bound_report_test_count"],
            "test_set_hash": row["bound_report_test_set_hash"],
        }
        try:
            if _entity_id(report_row["id"], "report_id") != report_id:
                raise IntegrityError("bound report identity mismatch")
            if _entity_id(report_row["artifact_id"], "artifact_id") != artifact_id:
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
            raise IntegrityError(f"function report member {expected_ordinal} entry seal mismatch")
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
        if (
            row["partition"] != partition
            or row["operation"] != operation
            or row["status"] != "pending"
        ):
            raise IntegrityError("pending proposal scope mismatch")
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
            artifact_id = _entity_id(row["id"], "artifact_id")
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
        """Report immutable function membership beside current operation state.

        Every detail list keeps one fixed order, so the page at a smaller `projection_limit` is a
        prefix of the page at a larger one: members by membership ordinal; ready and blocked
        compile scopes by input hash; pending proposals in arrival order (`status_sequence`,
        oldest first); each artifact status list and the stale-revision anomalies newest first
        (`sequence` descending).
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if receipt_id is not None:
            receipt_id = _entity_id(receipt_id, "receipt_id")
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
            if operation_row["partition"] != partition or operation_row["name"] != operation:
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
                    raise NotFoundError("function receipt does not exist for this operation")

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
                    raise IntegrityError("function receipt projected membership count mismatch")
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
                    raise IntegrityError("function report member order is not canonical")
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
                            projection.reasons if isinstance(projection, _BlockedBuild) else ()
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
            artifact_counts = dict.fromkeys(artifact_status_order, 0)
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
                    raise IntegrityError("operation contains a persisted building artifact")
                if type(status) is not str or status not in artifact_counts:
                    raise IntegrityError("operation contains an unknown artifact status")
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
                    raise IntegrityError(f"{status} artifact projection count mismatch")
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
                ORDER BY sequence DESC LIMIT ?
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
        receipt_id = _entity_id(receipt_id, "receipt_id")
        with self.store.transaction(write=False) as connection:
            receipt_row = connection.execute(
                """
                SELECT * FROM function_receipts
                WHERE partition = ? AND id = ?
                """,
                (partition, receipt_id),
            ).fetchone()
            if receipt_row is None:
                raise NotFoundError("function receipt does not exist in this partition")
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
        if expected_function_hash is not None and not _is_digest(expected_function_hash):
            raise ValidationError("expected_function_hash must be a SHA-256 hex digest")

        with self.store.transaction(write=False) as connection:
            return self._verify_function_snapshot(
                connection,
                partition=partition,
                operation=operation,
                expected_function_hash=expected_function_hash,
            )

    def _verify_function_snapshot(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        expected_function_hash: str | None,
    ) -> FunctionVerification:
        """`verify_function`'s checks inside a caller-held read snapshot (one-snapshot serving)."""

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
                detail=(f"{len(failures)} failure(s): " + "; ".join(failures[:3])),
            )

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
            operation_policy_failures.append(f"operation policy is invalid: {exc}")
        else:
            if canonical_policy.text != policy_json:
                operation_policy_failures.append("operation policy JSON is not canonical")
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
                receipt_detail = "; ".join(operation_policy_failures) + "; " + skipped
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
                FunctionCheck(key="projection-uniform", passed=False, detail=skipped),
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
            sources = duplicate_sources.setdefault(digest, [first_digest_source[digest]])
            if len(sources) < 3:
                sources.append(artifact_id)
        duplicates = sorted(duplicate_sources.items())
        if duplicates:
            preview = "; ".join(
                f"{digest}:{','.join(source_ids)}" for digest, source_ids in duplicates[:3]
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
        projection_failures = [f"operation: {failure}" for failure in operation_policy_failures]
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
                canonicalizer = raw_scope.get("canonicalizer") if type(raw_scope) is dict else None
                if artifact_abi != ARTIFACT_ABI or canonicalizer != CANONICALIZER:
                    abi_failures.append(
                        f"{artifact_id}: abi={artifact_abi!r}, canonicalizer={canonicalizer!r}"
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
                details = self._validate_report(connection, report, verify_test_set=True)
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
                scope_failures.append("policy hash does not match current operation")
            if row["policy_json"] != policy_json:
                scope_failures.append("policy JSON does not match current operation")
            try:
                if artifact is None:
                    raise IntegrityError(artifact_error or "artifact is invalid")
                if scope_failures:
                    raise IntegrityError("; ".join(scope_failures))
                self._validate_live_promoted(connection, row)
            except (IntegrityError, ValidationError) as exc:
                receipt_failures.append(f"{artifact_id}: {exc}")

            if artifact is None:
                projection_failures.append(
                    f"{artifact_id}: {artifact_error or 'artifact is invalid'}"
                )
            elif report is None:
                projection_failures.append(f"{artifact_id}: bound report is missing")
            elif scope_failures:
                projection_failures.append(f"{artifact_id}: {'; '.join(scope_failures)}")
            else:
                entry = FunctionEntry(
                    input=artifact.input.value,
                    output=artifact.output.value,
                    artifact_hash=str(row["artifact_hash"]),
                    evidence_snapshot_hash=str(row["evidence_snapshot_hash"]),
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
        member_programs = {row["projection_hash"] for row in rows}
        del rows
        program: ProjectionProgram | None = None
        projection_detail = "exact mode: no member carries a projection"
        projection_ok = len(member_programs) <= 1
        if not projection_ok:
            projection_detail = f"{len(member_programs)} programs across one set"
        elif member_programs and next(iter(member_programs)) is not None:
            try:
                program = self._program_by_hash(connection, next(iter(member_programs)))
                projection_detail = (
                    f"every member projects with {program.program_hash if program else ''}"
                )
            except IntegrityError as exc:
                projection_ok = False
                projection_detail = str(exc)
        projection_check = FunctionCheck(
            key="projection-uniform", passed=projection_ok, detail=projection_detail
        )

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
                    projection=program,
                )
                function_hash = document.function_hash
                if document.value.get("abi") != FUNCTION_ABI:
                    raise IntegrityError("function ABI changed during projection")
                if document.value.get("canonicalizer") != CANONICALIZER:
                    raise IntegrityError("function canonicalizer changed during projection")
                if document.value.get("function_hash") != document.function_hash:
                    raise IntegrityError("function hash changed during projection")
                expected_scope: dict[str, JSONValue] = {
                    "operation": operation,
                    "operation_revision": revision,
                    "partition": partition,
                    "policy_hash": policy_hash,
                }
                if document.value.get("scope") != expected_scope:
                    raise IntegrityError("function scope does not equal the promoted snapshot")
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
                    raise IntegrityError("function normalization changed during self-check")
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
                    detail=(f"{document.function_hash} binds {entry_count} snapshot entry/entries"),
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
            projection_check,
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
        """Serve the version the operation's switch selects, then look the input up in it.

        One read snapshot holds the switch, the served version and its checks, so a writer
        committing in between changes the next call, never this one. ``off`` runs no
        verification and answers nothing. ``follow`` runs the full set verification over the
        live promoted set (it costs what ``verify_function`` costs: ~36.5 s and ~963 MiB at
        50,000 entries, ``.agent/decisions/m3u2b-resolve-bench.json``). ``pinned`` rebuilds the
        pinned receipt and checks that no explicit negative judgment (revoked evidence, a
        suspended member, a counterexample) has reached it since. Arguments are validated
        first, so a rejected call reads no ledger. This call writes nothing and caches no
        verification result (projection keys are memoized by content, never by verdict). A
        failed verdict returns ``match`` ``None`` and is never a miss.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if expected_function_hash is not None:
            _digest(expected_function_hash, "expected_function_hash")
        input_json = canonicalize(input_value)
        state, verification = self.serving(
            partition, operation, expected_function_hash=expected_function_hash
        )
        if verification is None:
            return FunctionResolution(verification=None, match=None, switch=state)
        document = verification.document
        if not verification.passed or document is None:
            return FunctionResolution(verification=verification, match=None, switch=state)
        return FunctionResolution(
            verification=verification,
            match=evaluate(document, input_json=input_json),
            switch=state,
        )

    def serving(
        self,
        partition: str,
        operation: str,
        *,
        expected_function_hash: str | None = None,
    ) -> tuple[SwitchState, FunctionVerification | None]:
        """The switch and the verification of the version it serves, in one read snapshot.

        ``off`` returns ``None`` and runs no check; ``follow`` = the live set's verification;
        ``pinned`` = the pin checks. ``resolve`` and the CLI export both serve through this.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if expected_function_hash is not None:
            _digest(expected_function_hash, "expected_function_hash")
        with self.store.transaction(write=False) as connection:
            state = self._switch_state(connection, partition=partition, operation=operation)
            if state.mode == "off":
                return state, None
            if state.mode == "follow":
                return state, self._verify_function_snapshot(
                    connection,
                    partition=partition,
                    operation=operation,
                    expected_function_hash=expected_function_hash,
                )
            return state, self._verify_pinned_snapshot(
                connection,
                partition=partition,
                state=state,
                expected_function_hash=expected_function_hash,
            )

    # -- projection settings (M4.2) --------------------------------------------

    def _projection_report(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        revision: int,
        program: ProjectionProgram,
    ) -> dict[str, JSONValue]:
        """V2-V4 evidence for one program over the revision's active examples (read-only)."""

        rows = connection.execute(
            """
            SELECT e.id, e.input_json, e.input_hash, e.output_hash FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND x.example_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
            ORDER BY e.id
            """,
            (partition, operation, revision),
        ).fetchall()
        outputs: dict[str, set[str]] = {}
        support: dict[str, int] = {}
        unprojected: list[JSONValue] = []
        witnessed: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
        for row in rows:
            key_text = self._case_key_text(program, str(row["input_json"]), str(row["input_hash"]))
            if key_text is None:
                unprojected.append(str(row["id"]))
                continue
            key = parse_json(key_text)
            form = cast(dict[str, JSONValue], cast(dict[str, JSONValue], key.value)["form"])
            witnessed.add(
                (
                    str(form["title"]),
                    tuple(
                        (str(kind), str(name))
                        for kind, name in cast(list[list[str]], form["structure"])
                    ),
                )
            )
            outputs.setdefault(key.digest, set()).add(str(row["output_hash"]))
            support[key.digest] = support.get(key.digest, 0) + 1
        unwitnessed: list[JSONValue] = [
            layout.name
            for layout in program.layouts
            if (layout.title, layout.entries) not in witnessed
        ]
        return {
            "program_hash": program.program_hash,
            "projected": sum(support.values()),
            "unprojected": unprojected,
            "keys": [
                {"key_hash": digest, "support": support[digest], "outputs": len(outputs[digest])}
                for digest in sorted(support)
            ],
            "merged_outputs": cast(
                list[JSONValue], sorted(d for d, o in outputs.items() if len(o) > 1)
            ),
            "unwitnessed_layouts": unwitnessed,
        }

    def test_projection(
        self, partition: str, operation: str, program: object
    ) -> dict[str, JSONValue]:
        """Preview a program over the current revision; writes nothing.

        Besides the V2-V4 evidence ``set_projection`` grades (active examples alone), the preview
        lists each active example and pending proposal with its key or the reason it has none,
        and per key its pending proposals and readiness under the operation's policy.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        parsed = parse_program(program)
        with self.store.transaction(write=False) as connection:
            registered = connection.execute(
                "SELECT * FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = _stored_int(registered["revision"], "operation revision", minimum=1)
            policy = _policy_from_text(str(registered["policy_json"]))
            report = self._projection_report(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                program=parsed,
            )
            items: list[JSONValue] = []
            pending: dict[str, int] = {}
            key_texts: dict[str, str] = {}
            sources = (
                (
                    "example",
                    """
                    SELECT e.id, e.input_json FROM examples AS e
                    LEFT JOIN example_revocations AS x ON x.example_id = e.id
                    WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
                      AND x.example_id IS NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id
                      )
                    ORDER BY e.sequence
                    """,
                ),
                (
                    "proposal",
                    """
                    SELECT id, input_json FROM proposals
                    WHERE partition = ? AND operation = ? AND operation_revision = ?
                      AND status = 'pending'
                    ORDER BY status_sequence
                    """,
                ),
            )
            for kind, sql in sources:
                for row in connection.execute(sql, (partition, operation, revision)):
                    projected = project(parsed, parse_json(str(row["input_json"])).value)
                    key_hash = projected.key.digest if projected.key is not None else None
                    items.append(
                        {
                            "kind": kind,
                            "id": str(row["id"]),
                            "key_hash": key_hash,
                            "reason": projected.reason,
                        }
                    )
                    if kind == "proposal" and key_hash is not None:
                        pending[key_hash] = pending.get(key_hash, 0) + 1
                    elif projected.key is not None:
                        key_texts[projected.key.digest] = projected.key.text
            keys = cast(list[dict[str, JSONValue]], report["keys"])
            for entry in keys:
                digest = str(entry["key_hash"])
                entry["pending"] = pending.pop(digest, 0)
                # Ready = compile's own per-key gates (support, outputs, reviewers, span) pass.
                assessment = self._assess_examples(
                    self._active_evidence(
                        connection,
                        partition=partition,
                        operation=operation,
                        revision=revision,
                        input_hash=digest,
                        input_text=key_texts[digest],
                        program=parsed,
                    ),
                    policy,
                    projected=True,
                )
                entry["ready"] = not (
                    assessment["policy_failures"] or assessment["integrity_failures"]
                )
            keys.extend(
                {"key_hash": digest, "support": 0, "outputs": 0, "pending": count, "ready": False}
                for digest, count in sorted(pending.items())
            )
            report["items"] = items
            return report

    @staticmethod
    def _submission_revision_in(
        connection: sqlite3.Connection, partition: str, operation: str
    ) -> int:
        row = connection.execute(
            "SELECT revision FROM operations WHERE partition = ? AND name = ?",
            (partition, operation),
        ).fetchone()
        if row is None:
            raise NotFoundError("operation is not registered in this partition")
        return _stored_int(row["revision"], "operation revision", minimum=1)

    def projection(self, partition: str, operation: str) -> dict[str, JSONValue] | None:
        """The program new builds of the current revision use, or ``None`` (exact mode)."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        with self.store.transaction(write=False) as connection:
            revision = self._submission_revision_in(connection, partition, operation)
            program = self._build_program(
                connection, partition=partition, operation=operation, revision=revision
            )
            if program is None:
                return None
            return {
                "operation_revision": revision,
                "program": program.canonical.value,
                "program_hash": program.program_hash,
            }

    def set_projection(
        self, partition: str, operation: str, program: object, *, actor: str
    ) -> dict[str, JSONValue]:
        """Set the projection program new builds use; verify it in the same write transaction.

        Refused (nothing written) unless: the program validates (V1); every layout is witnessed
        by an active example (V2); no key merges examples with different outputs (V3); at least
        one example projects (V4). A program identical to the current one is a no-op. On success
        every draft or verified artifact of the revision built under another program retires
        (reason ``projection superseded``); promoted artifacts stay, they belong to versions.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        actor = _text(actor, "actor", maximum=256)
        parsed = parse_program(program)
        now = self._now()
        with self.store.transaction(write=True) as connection:
            revision = self._submission_revision_in(connection, partition, operation)
            current = self._build_program(
                connection, partition=partition, operation=operation, revision=revision
            )
            if current is not None and current.program_hash == parsed.program_hash:
                return {"changed": False, "program_hash": parsed.program_hash, "retired": []}
            report = self._projection_report(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                program=parsed,
            )
            if report["unwitnessed_layouts"]:
                raise ValidationError(
                    "projection layouts no confirmed example shows: "
                    f"{report['unwitnessed_layouts']}"
                )
            if report["merged_outputs"]:
                raise ValidationError("projection merges confirmed examples with different outputs")
            if not report["projected"]:
                raise ValidationError("no confirmed example of this revision projects")
            connection.execute(
                """
                INSERT OR IGNORE INTO projection_programs(program_hash, abi, program_json)
                VALUES (?, ?, ?)
                """,
                (parsed.program_hash, "cement-projection-v1", parsed.canonical.text),
            )
            connection.execute(
                """
                INSERT INTO projection_settings(
                    id, partition, operation, operation_revision, program_hash, set_by, set_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (_new_id("proj"), partition, operation, revision, parsed.program_hash, actor, now),
            )
            stale: list[JSONValue] = [
                str(row["id"])
                for row in connection.execute(
                    """
                    SELECT id FROM artifacts
                    WHERE partition = ? AND operation = ? AND operation_revision = ?
                      AND status IN ('draft', 'verified')
                      AND (projection_hash IS NULL OR projection_hash <> ?)
                    """,
                    (partition, operation, revision, parsed.program_hash),
                )
            ]
            connection.executemany(
                """
                UPDATE artifacts SET status = 'retired', status_reason = 'projection superseded'
                WHERE id = ?
                """,
                [(artifact_id,) for artifact_id in stale],
            )
            _event(
                connection,
                partition=partition,
                kind="projection.set",
                subject_type="operation",
                subject_id=f"{partition}/{operation}@{revision}",
                payload={
                    "previous_program_hash": None if current is None else current.program_hash,
                    "program_hash": parsed.program_hash,
                    "retired_artifact_ids": stale,
                    "set_by": actor,
                },
                now_us=now,
            )
            return {"changed": True, "program_hash": parsed.program_hash, "retired": stale}

    # -- switch + versions ----------------------------------------------------

    @staticmethod
    def _switch_state(
        connection: sqlite3.Connection, *, partition: str, operation: str
    ) -> SwitchState:
        if (
            connection.execute(
                "SELECT 1 FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            is None
        ):
            raise NotFoundError("operation is not registered in this partition")
        row = connection.execute(
            """
            SELECT * FROM switch_settings WHERE partition = ? AND operation = ?
            ORDER BY sequence DESC LIMIT 1
            """,
            (partition, operation),
        ).fetchone()
        if row is None:
            return SwitchState(
                partition=partition,
                operation=operation,
                mode="off",
                function_hash=None,
                receipt_id=None,
                set_by=None,
                set_at_us=None,
                sequence=None,
            )
        mode = row["mode"]
        if mode not in {"off", "follow", "pinned"}:
            raise IntegrityError("stored switch mode is invalid")
        return SwitchState(
            partition=partition,
            operation=operation,
            mode=mode,
            function_hash=None if row["function_hash"] is None else str(row["function_hash"]),
            receipt_id=None if row["receipt_id"] is None else str(row["receipt_id"]),
            set_by=str(row["set_by"]),
            set_at_us=_stored_int(row["set_at_us"], "switch set_at_us"),
            sequence=_stored_int(row["sequence"], "switch sequence", minimum=1),
        )

    def switch(self, partition: str, operation: str) -> SwitchState:
        """Read the operation's current switch (``off`` until a person sets one)."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        with self.store.transaction(write=False) as connection:
            return self._switch_state(connection, partition=partition, operation=operation)

    def set_switch(
        self,
        partition: str,
        operation: str,
        *,
        mode: str,
        actor: str,
        function_hash: str | None = None,
    ) -> SwitchState:
        """Switch an operation's function off, to follow its newest version, or onto one pin.

        ``pinned`` names any version of this operation by ``function_hash``, from any operation
        revision (a rollback across a reset is allowed); the newest receipt bearing that hash is
        bound. One write: one setting row and one ``function.switched`` event. A refusal
        writes nothing.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        actor = _text(actor, "actor", maximum=256)
        if type(mode) is not str or mode not in {"off", "follow", "pinned"}:
            raise ValidationError("switch mode must be off, follow, or pinned")
        if mode == "pinned":
            if function_hash is None:
                raise ValidationError("a pinned switch names its function_hash")
            _digest(function_hash, "function_hash")
        elif function_hash is not None:
            raise ValidationError(f"switch mode {mode} takes no function_hash")
        now = self._now()
        with self.store.transaction(write=True) as connection:
            previous = self._switch_state(connection, partition=partition, operation=operation)
            receipt_id: str | None = None
            if mode == "pinned":
                receipt = self._receipt_by_hash(
                    connection,
                    partition=partition,
                    operation=operation,
                    function_hash=cast(str, function_hash),
                )
                if receipt is None:
                    raise ValidationError("function_hash names no version of this operation")
                receipt_id = str(receipt["id"])
            setting_id = _new_id("sw")
            connection.execute(
                """
                INSERT INTO switch_settings(
                    id, partition, operation, mode, receipt_id, function_hash, set_by, set_at_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (setting_id, partition, operation, mode, receipt_id, function_hash, actor, now),
            )
            _event(
                connection,
                partition=partition,
                kind="function.switched",
                subject_type="operation",
                subject_id=f"{partition}/{operation}",
                payload={
                    "function_hash": function_hash,
                    "mode": mode,
                    "previous_function_hash": previous.function_hash,
                    "previous_mode": previous.mode,
                    "receipt_id": receipt_id,
                    "set_by": actor,
                },
                now_us=now,
            )
            return self._switch_state(connection, partition=partition, operation=operation)

    def _verify_pinned_snapshot(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        state: SwitchState,
        expected_function_hash: str | None,
    ) -> FunctionVerification:
        """Pin checks P-a..P-d (`.agent/decisions/m45-contract.md` §3) in a held snapshot."""

        receipt_row = connection.execute(
            "SELECT * FROM function_receipts WHERE partition = ? AND id = ?",
            (partition, state.receipt_id),
        ).fetchone()
        return self._pin_checks(
            connection,
            receipt_row=receipt_row,
            function_hash=cast(str, state.function_hash),
            expected_function_hash=expected_function_hash,
        )

    def _pin_checks(
        self,
        connection: sqlite3.Connection,
        *,
        receipt_row: sqlite3.Row | None,
        function_hash: str,
        expected_function_hash: str | None = None,
    ) -> FunctionVerification:
        # Every member check joins through the receipt's memberships: a member list bound as
        # SQL parameters would exceed SQLITE_LIMIT_VARIABLE_NUMBER (32,766 here) long before
        # FUNCTION_MAX_ENTRIES (50,000).
        checks: list[FunctionCheck] = []
        document: FunctionDocument | None = None
        receipt_id = None if receipt_row is None else str(receipt_row["id"])
        try:
            if receipt_row is None:
                raise IntegrityError("pinned receipt is missing")
            reconstruction = self._reconstruct_function_receipt(connection, receipt_row)
            if reconstruction.function_hash != function_hash:
                raise IntegrityError("pinned receipt rebuilds a different function")
            document = reconstruction.document
            checks.append(FunctionCheck(key="pinned-receipt-rebuilds", passed=True, detail="ok"))
        except IntegrityError as exc:
            checks.append(
                FunctionCheck(key="pinned-receipt-rebuilds", passed=False, detail=str(exc)[:200])
            )

        def count(sql: str) -> int:
            if receipt_id is None:
                return 0
            return _stored_int(
                connection.execute(sql, (receipt_id,)).fetchone()[0], "pinned receipt count"
            )

        revoked = count(
            """
            SELECT COUNT(*) FROM function_memberships AS m
            JOIN artifact_evidence AS ev ON ev.artifact_id = m.artifact_id
            JOIN example_revocations AS x ON x.example_id = ev.example_id
            WHERE m.receipt_id = ?
            """
        )
        checks.append(
            FunctionCheck(
                key="pinned-evidence-unrevoked",
                passed=revoked == 0,
                detail="ok" if revoked == 0 else f"{revoked} member evidence example(s) revoked",
            )
        )
        suspended = count(
            """
            SELECT COUNT(*) FROM function_memberships AS m
            JOIN artifacts AS a ON a.id = m.artifact_id
            WHERE m.receipt_id = ? AND a.status = 'suspended'
            """
        )
        checks.append(
            FunctionCheck(
                key="pinned-members-unsuspended",
                passed=suspended == 0,
                detail="ok" if suspended == 0 else f"{suspended} member artifact(s) suspended",
            )
        )
        counter = count(
            """
            SELECT COUNT(*) FROM function_memberships AS m
            JOIN artifacts AS a ON a.id = m.artifact_id
            JOIN examples AS c ON a.partition = c.partition AND a.operation = c.operation
                AND a.operation_revision = c.operation_revision
                AND a.input_hash = c.input_hash AND a.output_hash <> c.output_hash
            LEFT JOIN example_revocations AS x ON x.example_id = c.id
            WHERE m.receipt_id = ? AND c.origin = 'challenge' AND x.example_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = c.id)
              AND a.projection_hash IS NULL
            """
        )
        if receipt_row is not None and receipt_row["projection_hash"] is not None:
            # P-d under the RECEIPT's own program: a counterexample reaches a member's key
            # through projection, never through the raw input digest.
            program = self._program_by_hash(connection, str(receipt_row["projection_hash"]))
            members = {
                str(row["input_json"]): str(row["output_json"])
                for row in connection.execute(
                    """
                    SELECT a.input_json, a.output_json FROM function_memberships AS m
                    JOIN artifacts AS a ON a.id = m.artifact_id
                    WHERE m.receipt_id = ?
                    """,
                    (receipt_id,),
                )
            }
            for example in connection.execute(
                """
                SELECT c.input_json, c.input_hash, c.output_json FROM examples AS c
                LEFT JOIN example_revocations AS x ON x.example_id = c.id
                WHERE c.partition = ? AND c.operation = ? AND c.operation_revision = ?
                  AND c.origin = 'challenge' AND x.example_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = c.id)
                """,
                (
                    receipt_row["partition"],
                    receipt_row["operation"],
                    receipt_row["operation_revision"],
                ),
            ):
                key = (
                    None
                    if program is None
                    else self._case_key_text(
                        program, str(example["input_json"]), str(example["input_hash"])
                    )
                )
                if key in members and members[key] != example["output_json"]:
                    counter += 1
        checks.append(
            FunctionCheck(
                key="pinned-no-counterexample",
                passed=counter == 0,
                detail="ok" if counter == 0 else f"{counter} counterexample(s) on member keys",
            )
        )
        if expected_function_hash is not None:
            matches = expected_function_hash == function_hash
            checks.append(
                FunctionCheck(
                    key="expected-function-hash",
                    passed=matches,
                    detail="ok" if matches else "the pin serves a different function",
                )
            )
        passed = all(check.passed for check in checks)
        return FunctionVerification(
            passed=passed,
            entries=count("SELECT COUNT(*) FROM function_memberships WHERE receipt_id = ?"),
            document=document if passed else None,
            function_hash=function_hash,
            checks=tuple(checks),
        )

    def function_versions(
        self,
        partition: str,
        operation: str,
        *,
        before_sequence: int | None = None,
        limit: int = 100,
        check: bool = False,
    ) -> FunctionVersionPage:
        """Page the operation's versions (promotion receipts), newest first, marking the served.

        ``check=True`` computes ``servable`` per version, which costs a verification each: for the
        version ``follow`` serves, the live set verification; for any other, the pin checks it
        would face if a person pinned it now.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        if before_sequence is not None:
            _bounded_int(before_sequence, "before_sequence", minimum=0, maximum=2**63 - 1)
        _bounded_int(limit, "limit", minimum=1, maximum=10_000)
        if type(check) is not bool:
            raise ValidationError("check must be a boolean")
        with self.store.transaction(write=False) as connection:
            state = self._switch_state(connection, partition=partition, operation=operation)
            revision_row = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            revision = _stored_int(revision_row["revision"], "operation revision", minimum=1)
            newest = self._latest_function_receipt_row(
                connection, partition=partition, operation=operation, operation_revision=revision
            )
            selected = (
                state.receipt_id
                if state.mode == "pinned"
                else (str(newest["id"]) if state.mode == "follow" and newest else None)
            )
            page, cursor = self._receipt_rows(
                connection,
                partition=partition,
                operation=operation,
                operation_revision=None,
                before_sequence=before_sequence,
                limit=limit,
            )
            versions = []
            for row in page:
                receipt = _function_receipt_from_row(row)
                servable: bool | None = None
                if check:
                    if receipt.id == selected and state.mode == "follow":
                        servable = self._verify_function_snapshot(
                            connection,
                            partition=partition,
                            operation=operation,
                            expected_function_hash=None,
                        ).passed
                    else:
                        servable = self._pin_checks(
                            connection, receipt_row=row, function_hash=receipt.function_hash
                        ).passed
                versions.append(
                    FunctionVersion(
                        receipt=receipt,
                        projection_hash=(
                            None if row["projection_hash"] is None else str(row["projection_hash"])
                        ),
                        revision_current=receipt.operation_revision == revision,
                        selected=receipt.id == selected,
                        servable=servable,
                    )
                )
            return FunctionVersionPage(versions=tuple(versions), next_before_sequence=cursor)

    def diff_versions(
        self,
        partition: str,
        operation: str,
        *,
        from_hash: str,
        to_hash: str,
    ) -> FunctionDiff:
        """Compare two versions: their scope, their projection and their cases by key."""

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        _digest(from_hash, "from_hash")
        _digest(to_hash, "to_hash")
        with self.store.transaction(write=False) as connection:
            rows = []
            for function_hash in (from_hash, to_hash):
                row = self._receipt_by_hash(
                    connection,
                    partition=partition,
                    operation=operation,
                    function_hash=function_hash,
                )
                if row is None:
                    raise NotFoundError(f"no version {function_hash} for this operation")
                rows.append(row)
            documents = [
                self._reconstruct_function_receipt(connection, row).document for row in rows
            ]
            # Reconstruction already loaded, validated and embedded each version's program.
            programs: list[JSONValue] = [
                None if doc.projection is None else doc.projection.canonical.value
                for doc in documents
            ]
        before, after = (
            {
                str(entry["input_hash"]): str(entry["output_hash"])
                for entry in cast(list[dict[str, JSONValue]], doc.value["entries"])
            }
            for doc in documents
        )
        projections = [
            None if row["projection_hash"] is None else str(row["projection_hash"]) for row in rows
        ]
        return FunctionDiff(
            from_function_hash=from_hash,
            to_function_hash=to_hash,
            from_revision=_stored_int(rows[0]["operation_revision"], "revision", minimum=1),
            to_revision=_stored_int(rows[1]["operation_revision"], "revision", minimum=1),
            from_policy_hash=str(rows[0]["policy_hash"]),
            to_policy_hash=str(rows[1]["policy_hash"]),
            from_projection_hash=projections[0],
            to_projection_hash=projections[1],
            projection_changed=projections[0] != projections[1],
            from_program=programs[0],
            to_program=programs[1],
            added=tuple(sorted(set(after) - set(before))),
            removed=tuple(sorted(set(before) - set(after))),
            changed=tuple(
                sorted(key for key in set(before) & set(after) if before[key] != after[key])
            ),
        )

    def _draft_verification_plan(
        self,
        connection: sqlite3.Connection,
        *,
        partition: str,
        operation: str,
        projections: dict[str, _CurrentBuild | _BlockedBuild] | None = None,
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

        # The same enumerator compile uses, so eligibility is reconstruction in both modes (exact
        # input, or projection key under the build-current program).
        if projections is None:
            projections = self._build_projections(connection, registered)
        selected: list[sqlite3.Row] = []
        skipped: list[dict[str, JSONValue]] = []
        selected_hashes: set[str] = set()
        for row in rows:
            input_hash = str(row["input_hash"])
            projection = projections.get(input_hash)
            if projection is None:
                raise IntegrityError(f"current-revision draft {row['id']} has no canonical input")
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
                self._validate_live_promoted(connection, row)
            failures, test_count, artifact = self._run_verification(
                connection, row, record_test=record_test
            )
            flush_tests()
        # `ValidationError` is deliberate breadth (p24): the callees normalize every reachable
        # failure to `IntegrityError` today, but a value-shape failure in replayed evidence must
        # still end as a failed report, never as an exception escaping the locked batch.
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
        scope_hash = artifact.scope_digest if artifact is not None else str(row["scope_hash"])
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
        artifact_id = _entity_id(artifact_id, "artifact_id")
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

    @staticmethod
    def _program_by_hash(
        connection: sqlite3.Connection, program_hash: str | None
    ) -> ProjectionProgram | None:
        if program_hash is None:
            return None
        stored = connection.execute(
            "SELECT program_json, program_hash FROM projection_programs WHERE program_hash = ?",
            (program_hash,),
        ).fetchone()
        if stored is None:
            raise IntegrityError("projection program is missing")
        return _stored_program(stored)

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
        revision = _stored_int(
            row["operation_revision"], "stored artifact operation_revision", minimum=1
        )
        registered = connection.execute(
            "SELECT * FROM operations WHERE partition = ? AND name = ?",
            (partition, operation),
        ).fetchone()
        current_ok = (
            registered is not None
            and _stored_int(registered["revision"], "stored operation revision", minimum=1)
            == revision
            and registered["policy_hash"] == row["policy_hash"]
            and registered["policy_json"] == row["policy_json"]
        )
        test("operation-current", None, current_ok, "operation revision + policy binding")
        if not current_ok:
            failures.append("operation revision or policy is stale")
        policy = _policy_from_text(str(row["policy_json"]))
        program = self._program_by_hash(
            connection, None if row["projection_hash"] is None else str(row["projection_hash"])
        )
        assessment = self._assess_examples(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=str(row["input_hash"]),
                input_text=str(row["input_json"]),
                program=program,
            ),
            policy,
            projected=program is not None,
            reviewer_count=self._active_reviewer_count(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=str(row["input_hash"]),
                input_text=str(row["input_json"]),
                program=program,
            ),
        )
        if assessment["integrity_failures"]:
            raise IntegrityError(str(assessment["integrity_failures"][0]))
        failures.extend(str(failure) for failure in assessment["policy_failures"])
        snapshot = self._evidence_snapshot(
            self._active_evidence(
                connection,
                partition=partition,
                operation=operation,
                revision=revision,
                input_hash=str(row["input_hash"]),
                input_text=str(row["input_json"]),
                order_by_id=True,
                program=program,
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
                if _stored_int(row[field], f"stored artifact {field}") != int(assessment[field]):
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
            program=program,
        ):
            key_ok = True
            if program is not None:
                # The example reaches this case only through its projection; replay that hop,
                # then probe that deleting its LAST structural line (contract §5) leaves it. Body
                # lines hold no `:` (the grammar), so that line is the last one carrying one.
                key_ok = (
                    self._case_key_text(
                        program, str(example["input_json"]), str(example["input_hash"])
                    )
                    == input_json.text
                )
                raw = parse_json(str(example["input_json"])).value
                probe_ok = False
                if type(raw) is dict and type(raw.get(program.text)) is str:
                    lines = str(raw[program.text]).replace("\r\n", "\n").split("\n")
                    last = max(i for i, line in enumerate(lines) if ":" in line)
                    probed = {**raw, program.text: "\n".join(lines[:last] + lines[last + 1 :])}
                    projected = project(program, probed)
                    probe_ok = not projected.matched or (
                        projected.key is not None and projected.key.text != input_json.text
                    )
                test(
                    f"structure:{example['id']}",
                    str(example["id"]),
                    probe_ok,
                    "a structural edit leaves the case",
                )
                if not probe_ok:
                    failures.append("a structural edit kept the projected key")
            execution = execute(
                artifact,
                partition=partition,
                operation=operation,
                operation_revision=revision,
                input_json=input_json,
            )
            ok = (
                key_ok
                and execution.matched
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
                    partition="cement-boundary"
                    if partition != "cement-boundary"
                    else "cement-boundary-2",
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
                    operation="cement-boundary"
                    if operation != "cement-boundary"
                    else "cement-boundary-2",
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
        if type(details.value) is not dict or details.value.get("scope_hash") != row["scope_hash"]:
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
        projections: dict[str, _CurrentBuild | _BlockedBuild] | None = None,
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
        build_program = self._build_program(
            connection, partition=partition, operation=operation, revision=revision
        )
        build_program_hash = None if build_program is None else build_program.program_hash
        # Members built under another program leave the set (contract §5: replaced, never
        # mixed); a candidate on the same key replaces one, the rest retire as superseded.
        superseded: dict[str, sqlite3.Row] = {}
        for row in promoted_rows:
            artifact_id = str(row["id"])
            if row["operation_revision"] != revision:
                raise IntegrityError(
                    f"promoted artifact {artifact_id} has stale operation revision"
                )
            if row["policy_json"] != policy_json or row["policy_hash"] != policy_hash:
                raise IntegrityError(f"promoted artifact {artifact_id} has stale operation policy")
            input_hash = str(row["input_hash"])
            if input_hash in retained or input_hash in superseded:
                raise IntegrityError(f"multiple promoted artifacts claim input {input_hash}")
            if row["projection_hash"] != build_program_hash:
                superseded[input_hash] = row
                continue
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
        # The same enumerator compile uses: eligibility is reconstruction under the
        # build-current program, so a set never mixes programs (contract §5).
        if projections is None:
            projections = self._build_projections(connection, registered)
        candidates: dict[
            str,
            tuple[sqlite3.Row, sqlite3.Row, FunctionEntry],
        ] = {}
        skipped: list[dict[str, JSONValue]] = []
        for row in verified_rows:
            artifact_id = str(row["id"])
            input_hash = str(row["input_hash"])
            projection = projections.get(input_hash)
            if projection is None:
                raise IntegrityError(
                    f"current-revision verified artifact {artifact_id} has no canonical input"
                )
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
            if predecessor is not None and row["input_json"] != predecessor[0]["input_json"]:
                raise IntegrityError("equal input digest maps to unequal canonical inputs")
            report, function_entry = self._function_promotion_entry(
                connection,
                row,
                promoted=False,
            )
            candidates[input_hash] = (row, report, function_entry)

        dropped: list[str] = []
        for input_hash, row in sorted(superseded.items()):
            if input_hash not in candidates:
                dropped.append(str(row["id"]))
                skipped.append(
                    {
                        "artifact_id": str(row["id"]),
                        "input_hash": input_hash,
                        "reason": "projection-superseded",
                    }
                )
        for input_hash, (row, _, _) in sorted(retained.items()):
            if input_hash not in candidates and self._contradicted(connection, row):
                raise StateError(
                    f"promoted artifact {row['id']} conflicts with active evidence and no verified"
                    " build replaces it; supersede or revoke the conflicting examples, or suspend"
                    " the artifact"
                )
        final = dict(retained)
        final.update(candidates)
        planned: list[_FunctionPromotionPlanEntry] = []
        for input_hash in sorted(final):
            row, report, function_entry = final[input_hash]
            candidate = input_hash in candidates
            predecessor = retained.get(input_hash)
            replaced = (
                str(predecessor[0]["id"])
                if predecessor is not None
                else (str(superseded[input_hash]["id"]) if input_hash in superseded else None)
            )
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
                        replaces_artifact_id=replaced if candidate else None,
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
            projection=build_program,
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
            dropped=tuple(dropped),
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
                entry for entry in locked.entries if entry.public.disposition == "candidate"
            )
            retired_ids = tuple(
                sorted(
                    {
                        entry.public.replaces_artifact_id
                        for entry in locked.entries
                        if entry.public.replaces_artifact_id is not None
                    }
                    | set(locked.dropped)
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
                    raise StateError("function predecessor changed before locked retirement")

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
                    raise StateError("function candidate changed before locked activation")

            member_ids = tuple(sorted(entry.public.artifact_id for entry in locked.entries))
            candidate_ids = tuple(sorted(entry.public.artifact_id for entry in candidates))
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
                "projection_hash": locked.manifest.document.projection_hash,
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
                    promoted_at_us, receipt_hash, projection_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    locked.manifest.document.projection_hash,
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
        artifact_id = _entity_id(artifact_id, "artifact_id")
        promoted_by = _text(promoted_by, "promoted_by", maximum=256)
        if not _is_digest(scope_hash):
            raise ValidationError("scope_hash must be a SHA-256 hex digest")
        now = self._now()
        with self.store.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ? AND partition = ?",
                (artifact_id, partition),
            ).fetchone()
            if row is None:
                raise NotFoundError("artifact does not exist in this partition")
            if row["projection_hash"] is not None:
                # A projected entry joins a function only through set promotion, which keeps one
                # program per set (contract §5); a lone entry has no program to carry.
                raise StateError("a projected artifact is promoted with function promote")
            if row["status"] != "verified" or not row["verified_report_id"]:
                raise StateError("artifact must have a current passing verification report")
            if row["scope_hash"] != scope_hash:
                raise ConflictError("requested promotion scope does not equal the tested scope")
            report = connection.execute(
                "SELECT * FROM test_reports WHERE id = ? AND artifact_id = ?",
                (row["verified_report_id"], artifact_id),
            ).fetchone()
            if report is None or not _stored_int(
                report["passed"], "stored report passed", maximum=1
            ):
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
                raise StateError(
                    "artifact changed or became stale after verification: " + failures[0]
                )
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

    def _promoted_for_input(
        self,
        connection: sqlite3.Connection,
        partition: str,
        operation: str,
        revision: int,
        input_json: CanonicalJSON,
    ) -> list[tuple[sqlite3.Row, CanonicalJSON]]:
        """Promoted artifacts of the revision whose case this raw input reaches, with its key.

        Exact artifacts match the input itself; a projected artifact matches the key its OWN
        program maps the input to (X7), so a challenge on a raw form reaches the case it hits.
        """

        found = [
            (row, input_json)
            for row in connection.execute(
                """
                SELECT * FROM artifacts
                WHERE partition = ? AND operation = ? AND operation_revision = ?
                  AND input_hash = ? AND status = 'promoted' AND projection_hash IS NULL
                """,
                (partition, operation, revision, input_json.digest),
            )
        ]
        for (program_hash,) in connection.execute(
            """
            SELECT DISTINCT projection_hash FROM artifacts
            WHERE partition = ? AND operation = ? AND operation_revision = ?
              AND status = 'promoted' AND projection_hash IS NOT NULL
            ORDER BY projection_hash
            """,
            (partition, operation, revision),
        ).fetchall():
            program = self._program_by_hash(connection, str(program_hash))
            projected = None if program is None else project(program, input_json.value)
            if projected is None or not projected.matched or projected.key is None:
                continue
            key = projected.key
            found.extend(
                (row, key)
                for row in connection.execute(
                    """
                    SELECT * FROM artifacts
                    WHERE partition = ? AND operation = ? AND operation_revision = ?
                      AND input_hash = ? AND status = 'promoted' AND projection_hash = ?
                    """,
                    (partition, operation, revision, key.digest, program_hash),
                )
            )
        return found

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
            revision = _stored_int(registered["revision"], "stored operation revision", minimum=1)
            rows = [
                row
                for row, _ in self._promoted_for_input(
                    connection, partition, operation, revision, input_json
                )
            ]
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
            raise StateError(
                "challenge quarantined an integrity-invalid artifact; retry after review"
            )

        with self.store.transaction(write=True) as connection:
            registered = connection.execute(
                "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = _stored_int(registered["revision"], "stored operation revision", minimum=1)
            keyed = self._promoted_for_input(connection, partition, operation, revision, input_json)
            matches: list[tuple[sqlite3.Row, CanonicalJSON]] = []
            for row, key in keyed:
                artifact = self._artifact_from_row(row)
                self._validate_promoted(connection, row)
                execution = execute(
                    artifact,
                    partition=partition,
                    operation=operation,
                    operation_revision=revision,
                    input_json=key,
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

    # -- learning pass (M5.2) ----------------------------------------------------

    def learning_cases(
        self, partition: str, operation: str, *, program: object = None
    ) -> dict[str, JSONValue]:
        """What the learning pass has to do for one operation; writes nothing.

        Groups the current revision's pending proposals and active examples by case key: under
        ``program`` (a candidate the pass is drafting), else the build-current program, else the
        exact canonical input. ``work`` names the unfinished publication steps under the
        build-current program, so an interrupted pass resumes there without adding support.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        candidate = None if program is None else parse_program(program)
        with self.store.transaction(write=False) as connection:
            registered = connection.execute(
                "SELECT * FROM operations WHERE partition = ? AND name = ?",
                (partition, operation),
            ).fetchone()
            if registered is None:
                raise NotFoundError("operation is not registered in this partition")
            revision = _stored_int(registered["revision"], "operation revision", minimum=1)
            build_program = self._build_program(
                connection, partition=partition, operation=operation, revision=revision
            )
            grouping = candidate if candidate is not None else build_program
            cases: dict[str, dict[str, Any]] = {}
            unprojected: dict[str, list[JSONValue]] = {"example_ids": [], "proposal_ids": []}
            stale: list[JSONValue] = []
            unsourced: list[JSONValue] = []

            def carry(
                input_text: str, input_hash: str, output_text: str, kind: str, ident: str
            ) -> None:
                key_text = (
                    input_text
                    if grouping is None
                    else self._case_key_text(grouping, input_text, input_hash)
                )
                if key_text is None:
                    unprojected[f"{kind}_ids"].append(ident)
                    return
                entry = cases.setdefault(key_text, {"example": [], "proposal": [], "outputs": {}})
                entry[kind].append(ident)
                slot = entry["outputs"].setdefault(
                    output_text, {"example_ids": [], "proposal_ids": []}
                )
                slot[f"{kind}_ids"].append(ident)

            for row in connection.execute(
                """
                SELECT id, operation_revision, input_json, input_hash, proposed_output_json,
                    source_id, provenance_json
                FROM proposals
                WHERE partition = ? AND operation = ? AND status = 'pending'
                ORDER BY status_sequence
                """,
                (partition, operation),
            ):
                proposal_id = str(row["id"])
                if row["operation_revision"] != revision:
                    stale.append(proposal_id)
                    continue
                if row["source_id"] is None:
                    unsourced.append(
                        {
                            "proposal_id": proposal_id,
                            "provenance": parse_json(
                                str(row["provenance_json"]), max_bytes=PROVENANCE_MAX_BYTES
                            ).value,
                        }
                    )
                carry(
                    str(row["input_json"]),
                    str(row["input_hash"]),
                    str(row["proposed_output_json"]),
                    "proposal",
                    proposal_id,
                )
            for row in connection.execute(
                """
                SELECT e.id, e.input_json, e.input_hash, e.output_json FROM examples AS e
                LEFT JOIN example_revocations AS x ON x.example_id = e.id
                WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
                  AND x.example_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
                ORDER BY e.sequence
                """,
                (partition, operation, revision),
            ):
                carry(
                    str(row["input_json"]),
                    str(row["input_hash"]),
                    str(row["output_json"]),
                    "example",
                    str(row["id"]),
                )

            # One reconstruction per case per snapshot: the build-current builds feed the case
            # list (when they group it), the work queues and both publication plans.
            current = self._build_projections(connection, registered)
            listed: list[JSONValue] = []
            for key_text, entry in cases.items():
                key = parse_json(key_text)
                known = current.get(key.digest) if candidate is None else None
                build = known or self._project_current_build(
                    connection, registered, key.digest, key.text, program=grouping
                )
                built = (
                    self._live_build(connection, build.build_hash)
                    if isinstance(build, _CurrentBuild)
                    else None
                )
                listed.append(
                    {
                        "key": key.value,
                        "key_hash": key.digest,
                        "pending_proposal_ids": entry["proposal"],
                        "active_example_ids": entry["example"],
                        "outputs": [
                            {"output": parse_json(text).value, **ids}
                            for text, ids in sorted(entry["outputs"].items())
                        ],
                        "support": build.support,
                        "ready": isinstance(build, _CurrentBuild),
                        "blocked_reasons": (
                            [] if isinstance(build, _CurrentBuild) else list(build.reasons)
                        ),
                        "artifact": (
                            None
                            if built is None
                            else {"id": str(built["id"]), "status": str(built["status"])}
                        ),
                    }
                )
            listed.sort(key=lambda item: str(cast(dict[str, JSONValue], item)["key_hash"]))

            compile_work: list[JSONValue] = []
            merge_work: list[JSONValue] = []
            for key_hash, build in current.items():
                if isinstance(build, _CurrentBuild):
                    if self._live_build(connection, build.build_hash) is None:
                        compile_work.append(key_hash)
                elif "confirmed outputs conflict" in build.reasons:
                    # An interrupted merge leaves no pending proposal and nothing to compile; the
                    # case's differing confirmations are the only sign the pass must resume.
                    merge_work.append(key_hash)
            _, drafts, _ = self._draft_verification_plan(
                connection, partition=partition, operation=operation, projections=current
            )
            promote_work: list[JSONValue] = []
            promote_blocked: str | None = None
            prospective: str | None = None
            try:
                plan = self._function_promotion_plan(
                    connection, partition=partition, operation=operation, projections=current
                )
            except StateError as exc:
                promote_blocked = str(exc)
            else:
                prospective = plan.manifest.function_hash
                promote_work = [
                    entry.artifact_id
                    for entry in plan.manifest.entries
                    if entry.disposition == "candidate"
                ]
            live = self._latest_function_receipt_row(
                connection, partition=partition, operation=operation, operation_revision=revision
            )
            work: dict[str, JSONValue] = {
                "merge_key_hashes": merge_work,
                "compile_key_hashes": compile_work,
                "verify_artifact_ids": [str(row["id"]) for row in drafts],
                "promote_artifact_ids": promote_work,
                "promote_blocked": promote_blocked,
                "prospective_function_hash": prospective,
                "live_function_hash": None if live is None else str(live["function_hash"]),
            }
            pending = sum(len(entry["proposal"]) for entry in cases.values()) + len(
                unprojected["proposal_ids"]
            )
            return {
                "partition": partition,
                "operation": operation,
                "operation_revision": revision,
                "grouped_by": (
                    "candidate"
                    if candidate is not None
                    else "exact"
                    if build_program is None
                    else "build-current"
                ),
                "program_hash": None if grouping is None else grouping.program_hash,
                "cases": listed,
                "unprojected": cast(dict[str, JSONValue], unprojected),
                "stale_pending_proposal_ids": stale,
                "unsourced_pending": unsourced,
                "work": work,
                "nothing_to_learn": not (
                    pending
                    or stale
                    or merge_work
                    or compile_work
                    or drafts
                    or promote_work
                    or promote_blocked is not None
                ),
            }

    def supersede_examples(
        self,
        partition: str,
        operation: str,
        *,
        example_ids: Sequence[str],
        output: object,
        reviewer: str,
        note: str = "",
    ) -> tuple[str, ...]:
        """Replace earlier confirmations with a re-merged output, one new example per old one.

        Each new example keeps its old example's input, revision and source observation and
        names it in ``supersedes_example_id``; the old example stays valid for the versions
        built on it but no longer counts for new builds, so one observation earns one support
        credit however often the learning pass re-merges it. Refused, with nothing written,
        for an empty or repeated id, an unknown, revoked or already-superseded example, one of
        another operation, or an output equal to the old one.
        """

        partition = _name(partition, "partition")
        operation = _name(operation, "operation")
        reviewer = _text(reviewer, "reviewer", maximum=256)
        note = _text(note, "note", maximum=2_048, allow_empty=True)
        ids = tuple(_entity_id(value, "example_id") for value in example_ids)
        if not ids or len(set(ids)) != len(ids):
            raise ValidationError("example_ids must be a non-empty list of distinct ids")
        final = canonicalize(output)
        now = self._now()
        created: list[str] = []
        with self.store.transaction(write=True) as connection:
            for old_id in ids:
                old = connection.execute(
                    "SELECT * FROM examples WHERE id = ? AND partition = ?", (old_id, partition)
                ).fetchone()
                if old is None:
                    raise NotFoundError(f"example {old_id} does not exist in this partition")
                if old["operation"] != operation:
                    raise ValidationError(f"example {old_id} belongs to another operation")
                if connection.execute(
                    "SELECT 1 FROM example_revocations WHERE example_id = ?", (old_id,)
                ).fetchone():
                    raise StateError(f"example {old_id} is revoked")
                if connection.execute(
                    "SELECT 1 FROM examples WHERE supersedes_example_id = ?", (old_id,)
                ).fetchone():
                    raise StateError(f"example {old_id} is already superseded")
                if old["output_json"] == final.text:
                    raise ValidationError(f"example {old_id} already confirms this output")
                example_id = _new_id("ex")
                receipt = canonicalize(
                    {
                        "confirmed_at_us": now,
                        "example_id": example_id,
                        "format": "cement-supersession-v1",
                        "input": parse_json(str(old["input_json"])).value,
                        "note": note,
                        "operation": operation,
                        "operation_revision": _stored_int(
                            old["operation_revision"],
                            "stored example operation_revision",
                            minimum=1,
                        ),
                        "output": final.value,
                        "partition": partition,
                        "reviewer": reviewer,
                        "supersedes_example_id": old_id,
                    },
                    max_bytes=_RECEIPT_MAX_BYTES,
                )
                connection.execute(
                    """
                    INSERT INTO examples(
                        id, partition, operation, operation_revision, input_json, input_hash,
                        output_json, output_hash, reviewer, origin, supersedes_example_id,
                        source_id, receipt_json, receipt_hash, confirmed_at_us
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'superseded', ?, ?, ?, ?, ?)
                    """,
                    (
                        example_id,
                        partition,
                        operation,
                        _stored_int(
                            old["operation_revision"],
                            "stored example operation_revision",
                            minimum=1,
                        ),
                        str(old["input_json"]),
                        str(old["input_hash"]),
                        final.text,
                        final.digest,
                        reviewer,
                        old_id,
                        old["source_id"],
                        receipt.text,
                        receipt.digest,
                        now,
                    ),
                )
                _event(
                    connection,
                    partition=partition,
                    kind="example.superseded",
                    subject_type="example",
                    subject_id=old_id,
                    payload={"example_id": example_id, "reviewer": reviewer},
                    now_us=now,
                )
                created.append(example_id)
        return tuple(created)

    def revoke_example(
        self,
        partition: str,
        example_id: str,
        *,
        revoked_by: str,
        reason: str,
    ) -> tuple[str, ...]:
        partition = _name(partition, "partition")
        example_id = _entity_id(example_id, "example_id")
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
        artifact_id = _entity_id(artifact_id, "artifact_id")
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
            # A retired member can still be suspended: that is how a person invalidates a
            # historical version a pin could otherwise keep serving (contract §3, C3).
            if row["status"] == "suspended":
                raise StateError("artifact is already suspended")
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
                    "created_at_us": _stored_int(
                        row["created_at_us"], "stored operation created_at_us"
                    ),
                    "name": str(row["name"]),
                    "policy": parse_json(str(row["policy_json"]), max_bytes=16_384).value,
                    "policy_hash": str(row["policy_hash"]),
                    "revision": _stored_int(
                        row["revision"], "stored operation revision", minimum=1
                    ),
                    "updated_at_us": _stored_int(
                        row["updated_at_us"], "stored operation updated_at_us"
                    ),
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
                SELECT e.*, x.revoked_by, x.reason AS revocation_reason, x.revoked_at_us,
                    (SELECT s.id FROM examples AS s WHERE s.supersedes_example_id = e.id)
                        AS superseded_by
                FROM examples AS e
                LEFT JOIN example_revocations AS x ON x.example_id = e.id
                WHERE e.partition = ? AND e.operation = ? AND e.sequence > ? {clause}
                ORDER BY e.sequence LIMIT ?
                """,  # noqa: S608 — only code-chosen fragments; every value binds as `?`
                (partition, operation, after_sequence, limit),
            ).fetchall()
            return [
                {
                    "confirmed_at_us": _stored_int(
                        row["confirmed_at_us"], "stored example confirmed_at_us"
                    ),
                    "id": str(row["id"]),
                    "input": parse_json(str(row["input_json"])).value,
                    "input_hash": str(row["input_hash"]),
                    "operation_revision": _stored_int(
                        row["operation_revision"], "stored example operation_revision", minimum=1
                    ),
                    "origin": str(row["origin"]),
                    "output": parse_json(str(row["output_json"])).value,
                    "output_hash": str(row["output_hash"]),
                    "receipt_hash": str(row["receipt_hash"]),
                    "reviewer": str(row["reviewer"]),
                    "sequence": _stored_int(row["sequence"], "stored example sequence", minimum=1),
                    "source_id": None if row["source_id"] is None else str(row["source_id"]),
                    "superseded_by": (
                        None if row["superseded_by"] is None else str(row["superseded_by"])
                    ),
                    "supersedes_example_id": (
                        None
                        if row["supersedes_example_id"] is None
                        else str(row["supersedes_example_id"])
                    ),
                    "revocation": (
                        {
                            "at_us": _stored_int(
                                row["revoked_at_us"], "stored example revoked_at_us"
                            ),
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
        artifact_id = _entity_id(artifact_id, "artifact_id")
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
        report_id = _entity_id(report_id, "report_id")
        after_test_key = _text(after_test_key, "after_test_key", maximum=256, allow_empty=True)
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
                "created_at_us": _stored_int(row["created_at_us"], "stored report created_at_us"),
                "details": details.value,
                "evidence_snapshot_hash": str(row["evidence_snapshot_hash"]),
                "id": report_id,
                "passed": bool(_stored_int(row["passed"], "stored report passed", maximum=1)),
                "policy_hash": str(row["policy_hash"]),
                "sequence": _stored_int(row["sequence"], "stored report sequence", minimum=1),
                "scope_hash": str(row["scope_hash"]),
                "test_count": _stored_int(row["test_count"], "stored report test_count", minimum=1),
                "test_set_hash": str(row["test_set_hash"]),
                "tests": [
                    {
                        "detail": str(test["detail"]),
                        "example_id": (
                            str(test["example_id"]) if test["example_id"] is not None else None
                        ),
                        "key": str(test["test_key"]),
                        "passed": bool(
                            _stored_int(test["passed"], "stored test passed", maximum=1)
                        ),
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
            artifact_id = _entity_id(artifact_id, "artifact_id")
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
                        "created_at_us": _stored_int(
                            row["created_at_us"], "stored report created_at_us"
                        ),
                        "id": str(row["id"]),
                        "passed": bool(
                            _stored_int(row["passed"], "stored report passed", maximum=1)
                        ),
                        "sequence": _stored_int(
                            row["sequence"], "stored report sequence", minimum=1
                        ),
                        "scope_hash": str(row["scope_hash"]),
                        "test_count": _stored_int(
                            row["test_count"], "stored report test_count", minimum=1
                        ),
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
                    "created_at_us": _stored_int(
                        row["created_at_us"], "stored event created_at_us"
                    ),
                    "kind": str(row["kind"]),
                    "payload": parse_json(str(row["payload_json"]), max_bytes=262_144).value,
                    "sequence": _stored_int(row["sequence"], "stored event sequence", minimum=1),
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
            "created_at_us": _stored_int(row["created_at_us"], "stored artifact created_at_us"),
            "evidence_snapshot_hash": str(row["evidence_snapshot_hash"]),
            "id": str(row["id"]),
            "input_hash": str(row["input_hash"]),
            "operation_revision": _stored_int(
                row["operation_revision"], "stored artifact operation_revision", minimum=1
            ),
            "promoted_at_us": (
                _stored_int(row["promoted_at_us"], "stored artifact promoted_at_us")
                if row["promoted_at_us"] is not None
                else None
            ),
            "promotion_hash": str(row["promotion_hash"]) if row["promotion_hash"] else None,
            "reviewer_count": _stored_int(
                row["reviewer_count"], "stored artifact reviewer_count", minimum=1
            ),
            "sequence": _stored_int(row["sequence"], "stored artifact sequence", minimum=1),
            "scope_hash": str(row["scope_hash"]),
            "span_seconds": _stored_int(row["span_seconds"], "stored artifact span_seconds"),
            "status": str(row["status"]),
            "status_reason": str(row["status_reason"]) if row["status_reason"] else None,
            "support": _stored_int(row["support"], "stored artifact support", minimum=2),
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
        test_count = _stored_int(row["test_count"], "stored report test_count", minimum=1)
        if verify_test_set:
            stored_count, test_set_hash = System._test_snapshot(connection, str(row["id"]))
            if stored_count != test_count or test_set_hash != row["test_set_hash"]:
                raise IntegrityError("verification report test set mismatch")
        elif not _is_digest(str(row["test_set_hash"])):
            raise IntegrityError("verification report test set digest is invalid")
        failures = details.value.get("failures")
        if (
            details.value.get("tests") != test_count
            or type(failures) is not list
            or bool(_stored_int(row["passed"], "stored report passed", maximum=1)) == bool(failures)
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
        if report is None or not _stored_int(report["passed"], "stored report passed", maximum=1):
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

    def _contradicted(self, connection: sqlite3.Connection, row: sqlite3.Row) -> bool:
        """Whether an active example of the artifact's case confirms a different output.

        A legitimate ledger state since review stopped auto-suspending (contract §3): the live set
        fails verification until the next promotion replaces the artifact, so read surfaces and
        challenges grade integrity alone and never report it as corruption.
        """

        if row["projection_hash"] is None:
            counterexample = connection.execute(
                """
                SELECT e.id FROM examples AS e
                LEFT JOIN example_revocations AS x ON x.example_id = e.id
                WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
                  AND e.input_hash = ? AND e.input_json = ?
                  AND e.output_json <> ? AND x.example_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
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
            return counterexample is not None
        # X7: under a program, contrary evidence is any active example of the revision whose
        # PROJECTED key is this artifact's key with a different output; a raw input equal to the
        # key text is NoMatch under its program, so raw equality alone never contradicts.
        program = System._program_by_hash(connection, str(row["projection_hash"]))
        assert program is not None  # noqa: S101 — narrowing only: the hash is non-null
        for example in connection.execute(
            """
            SELECT e.input_json, e.input_hash, e.output_json FROM examples AS e
            LEFT JOIN example_revocations AS x ON x.example_id = e.id
            WHERE e.partition = ? AND e.operation = ? AND e.operation_revision = ?
              AND e.output_json <> ? AND x.example_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM examples AS s WHERE s.supersedes_example_id = e.id)
            """,
            (row["partition"], row["operation"], row["operation_revision"], row["output_json"]),
        ):
            key = self._case_key_text(
                program, str(example["input_json"]), str(example["input_hash"])
            )
            if key == row["input_json"]:
                return True
        return False

    def _validate_live_promoted(self, connection: sqlite3.Connection, row: sqlite3.Row) -> None:
        System._validate_promoted(connection, row)
        if self._contradicted(connection, row):
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
            support=_stored_int(row["support"], "stored artifact support", minimum=2),
            reviewer_count=_stored_int(
                row["reviewer_count"], "stored artifact reviewer_count", minimum=1
            ),
            span_seconds=_stored_int(row["span_seconds"], "stored artifact span_seconds"),
            projection_digest=(
                None if row["projection_hash"] is None else str(row["projection_hash"])
            ),
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
