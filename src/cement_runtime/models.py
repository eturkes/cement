"""Public value types — frozen dataclasses, and the plain-dict records (``TypedDict``) that
inspection methods return; all effectful behavior lives in ``System``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict, cast

from .errors import ValidationError
from .function import FunctionDocument, FunctionMatch
from .json_value import JSONValue
from .projection import ProgramDocument


@dataclass(frozen=True, slots=True)
class CompilePolicy:
    # Owner ruling (IMPLEMENT orientation): the learning pass is the only reviewer and the
    # person's switch the only human gate, so the floor is recurrence alone: seen twice.
    min_confirmations: int = 2
    min_reviewers: int = 1
    min_span_seconds: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int
            for value in (self.min_confirmations, self.min_reviewers, self.min_span_seconds)
        ):
            raise ValidationError("compile policy values must be integers")
        if not 2 <= self.min_confirmations <= 1_000_000:
            raise ValidationError("min_confirmations must be between 2 and 1,000,000")
        if not 1 <= self.min_reviewers <= self.min_confirmations:
            raise ValidationError(
                "min_reviewers must be positive and no greater than confirmations"
            )
        if not 0 <= self.min_span_seconds <= 10 * 365 * 24 * 60 * 60:
            raise ValidationError("min_span_seconds must be between zero and ten years")

    def as_json(self) -> PolicyRecord:
        return {
            "min_confirmations": self.min_confirmations,
            "min_reviewers": self.min_reviewers,
            "min_span_seconds": self.min_span_seconds,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, JSONValue]) -> CompilePolicy:
        expected = {"min_confirmations", "min_reviewers", "min_span_seconds"}
        if set(value) != expected or any(type(value[key]) is not int for key in expected):
            raise ValidationError("invalid compile policy document")
        return cls(
            min_confirmations=cast(int, value["min_confirmations"]),
            min_reviewers=cast(int, value["min_reviewers"]),
            min_span_seconds=cast(int, value["min_span_seconds"]),
        )


@dataclass(frozen=True, slots=True)
class Candidate:
    # Runtime canonicalization owns JSON validation; ``object`` avoids mutable
    # container invariance rejecting ordinary ``dict[str, int]`` adapter output.
    output: object
    provenance: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CandidateRequest:
    partition: str
    operation: str
    operation_revision: int
    input: JSONValue


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """The outcome of reviewing one proposal, identified by the proposal alone.

    ``status`` mirrors the reviewed proposal's own status, so accept and correct are
    distinguishable without comparing outputs. ``example_id`` and ``output`` are the
    confirmed example and its output on accept and correct, and are ``None`` on reject,
    where no example is created.
    """

    proposal_id: str
    status: Literal["accepted", "corrected", "rejected"]
    example_id: str | None
    output: JSONValue | None


@dataclass(frozen=True, slots=True)
class ProposalView:
    id: str
    partition: str
    operation: str
    operation_revision: int
    input: JSONValue
    proposed_output: JSONValue
    provenance: JSONValue
    created_at_us: int


@dataclass(frozen=True, slots=True)
class CompileResult:
    created: tuple[str, ...]
    existing: tuple[str, ...]
    blocked: tuple[dict[str, JSONValue], ...]


@dataclass(frozen=True, slots=True)
class VerificationReport:
    id: str
    artifact_id: str
    scope_hash: str
    passed: bool
    tests: int
    failures: tuple[str, ...]
    created_at_us: int


@dataclass(frozen=True, slots=True)
class DraftEntry:
    artifact_id: str
    input_hash: str
    report: VerificationReport
    entry_seal: str | None


@dataclass(frozen=True, slots=True)
class DraftVerification:
    passed: bool
    operation_revision: int
    entries: tuple[DraftEntry, ...]
    skipped: tuple[dict[str, JSONValue], ...]


@dataclass(frozen=True, slots=True)
class FunctionPromotionEntry:
    artifact_id: str
    input_hash: str
    artifact_hash: str
    output_hash: str
    entry_seal: str
    disposition: Literal["retained", "candidate"]
    replaces_artifact_id: str | None


@dataclass(frozen=True, slots=True)
class FunctionPromotionManifest:
    operation_revision: int
    function_hash: str
    text: str
    document: FunctionDocument
    entries: tuple[FunctionPromotionEntry, ...]
    skipped: tuple[dict[str, JSONValue], ...]


@dataclass(frozen=True, slots=True)
class FunctionReceipt:
    id: str
    sequence: int
    partition: str
    operation: str
    operation_revision: int
    policy_hash: str
    function_hash: str
    membership_hash: str
    member_count: int
    candidate_artifact_ids_hash: str
    candidate_count: int
    retired_artifact_ids_hash: str
    retired_count: int
    promoted_by: str
    promoted_at_us: int
    receipt_hash: str


@dataclass(frozen=True, slots=True)
class FunctionReceiptPage:
    receipts: tuple[FunctionReceipt, ...]
    next_before_sequence: int | None


@dataclass(frozen=True, slots=True)
class FunctionMember:
    ordinal: int
    artifact_id: str
    input_hash: str
    build_support: int
    build_reviewer_count: int


@dataclass(frozen=True, slots=True)
class FunctionAnchorReport:
    receipt: FunctionReceipt
    member_count: int
    members: tuple[FunctionMember, ...]


@dataclass(frozen=True, slots=True)
class CompileScope:
    input_hash: str
    active_support: int
    active_reviewer_count: int
    active_span_seconds: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuarantineMember:
    """One live promoted member and its findings, each tagged with its check channel."""

    artifact_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuarantinePlan:
    """The live promoted members a quarantine would suspend, and the digest that names them.

    Members carry member-local findings only (ABI, report, receipt, projection, ambiguity), so an
    empty plan means nothing to contain, never a passing verification. ``plan_digest`` binds this
    display, not every ledger byte.
    """

    partition: str
    operation: str
    operation_revision: int
    members: tuple[QuarantineMember, ...]
    plan_digest: str


@dataclass(frozen=True, slots=True)
class QuarantineResult:
    """What one ``quarantine`` call suspended, or the earlier application it found."""

    plan_digest: str
    quarantined: tuple[str, ...]
    already_applied: bool


@dataclass(frozen=True, slots=True)
class ShadowCapture:
    """What a shadow observation compares against: the version that served the hit (its receipt,
    revision and answer) and the comparator in force for that revision when it was captured."""

    receipt_id: str
    operation_revision: int
    function_hash: str
    output: JSONValue
    artifact_hash: str
    comparator: ComparatorRecord | None


@dataclass(frozen=True, slots=True)
class PruneResult:
    """What one ``prune_proposals`` call deleted: proposals created before ``cutoff_us`` that no
    example referenced. ``proposal_ids`` holds the first 100 sorted ids; the hash binds them all."""

    cutoff_us: int
    count: int
    proposal_ids: tuple[str, ...]
    proposal_ids_hash: str


@dataclass(frozen=True, slots=True)
class ErasureResult:
    """One ``erase_partition``: its tombstone id, the partition digest it records, and the rows it
    deleted per table."""

    erasure_id: str
    partition_hash: str
    counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class PendingProposalGap:
    proposal_id: str
    operation_revision: int
    input_hash: str


@dataclass(frozen=True, slots=True)
class OperationArtifact:
    sequence: int
    artifact_id: str
    operation_revision: int
    input_hash: str
    status_reason: str | None


@dataclass(frozen=True, slots=True)
class OperationArtifactStatus:
    status: Literal["draft", "verified", "promoted", "suspended", "retired"]
    count: int
    artifacts: tuple[OperationArtifact, ...]


@dataclass(frozen=True, slots=True)
class StaleRevisionAnomaly:
    artifact_id: str
    status: Literal["draft", "verified", "promoted"]
    artifact_revision: int
    current_revision: int
    reason: str


@dataclass(frozen=True, slots=True)
class OperationNowReport:
    operation_revision: int
    policy_hash: str
    projection_limit: int
    promoted_entry_count: int
    compile_ready_scope_count: int
    compile_ready_scopes: tuple[CompileScope, ...]
    compile_blocked_scope_count: int
    compile_blocked_scopes: tuple[CompileScope, ...]
    pending_proposal_count: int
    pending_proposals: tuple[PendingProposalGap, ...]
    artifact_statuses: tuple[OperationArtifactStatus, ...]
    stale_revision_anomaly_count: int
    stale_revision_anomalies: tuple[StaleRevisionAnomaly, ...]


@dataclass(frozen=True, slots=True)
class FunctionReport:
    partition: str
    operation: str
    function_anchor: FunctionAnchorReport | None
    operation_now: OperationNowReport


@dataclass(frozen=True, slots=True)
class FunctionReconstruction:
    receipt: FunctionReceipt
    document: FunctionDocument

    @property
    def text(self) -> str:
        return self.document.text

    @property
    def function_hash(self) -> str:
        return self.document.function_hash


@dataclass(frozen=True, slots=True)
class FunctionSetPromotion:
    receipt_id: str
    receipt_hash: str
    function_hash: str
    operation_revision: int
    member_artifact_ids: tuple[str, ...]
    candidate_artifact_ids: tuple[str, ...]
    retired_artifact_ids: tuple[str, ...]
    promoted_at_us: int


@dataclass(frozen=True, slots=True)
class FunctionCheck:
    """One stable named decision in promoted-set verification."""

    key: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class FunctionVerification:
    """Read-only verification result over one committed promoted-set snapshot.

    A diagnostic hash may survive a failed ledger check; consumers must gate on
    ``passed``. The result is not a lease, signature, persisted report, semantic
    replay, or proof of input-domain coverage.
    """

    passed: bool
    entries: int
    document: FunctionDocument | None
    function_hash: str | None
    checks: tuple[FunctionCheck, ...]


@dataclass(frozen=True, slots=True)
class SwitchState:
    """The per-operation switch a person sets: the ONE human gate on serving.

    ``off`` serves nothing; ``follow`` serves the newest promoted version of the current
    operation revision; ``pinned`` serves exactly ``function_hash`` (receipt ``receipt_id``),
    from any operation revision. With no setting ever written, the state is ``off`` and every
    provenance field is ``None``.
    """

    partition: str
    operation: str
    mode: Literal["off", "follow", "pinned"]
    function_hash: str | None
    receipt_id: str | None
    set_by: str | None
    set_at_us: int | None
    sequence: int | None


@dataclass(frozen=True, slots=True)
class FunctionResolution:
    """One switch reading plus, when the switch serves a version, its verification + lookup.

    ``switch.mode == "off"`` runs no verification: ``verification`` and ``match`` are both
    ``None``. Otherwise ``match`` is ``None`` exactly when ``verification.passed`` is ``False``
    for every verification the unmodified ``System`` produces; that qualifier names the
    implementation, not an invariant the class enforces. A failed verdict carries no answer.
    A verified ``matched=False`` is a proven absence inside the served version. Consumers must
    not collapse the three states.
    """

    verification: FunctionVerification | None
    match: FunctionMatch | None
    switch: SwitchState


@dataclass(frozen=True, slots=True)
class FunctionVersion:
    """One promotion receipt seen as a version a person can serve, pin or roll back to."""

    receipt: FunctionReceipt
    projection_hash: str | None
    revision_current: bool
    selected: bool
    servable: bool | None = None


@dataclass(frozen=True, slots=True)
class FunctionVersionPage:
    versions: tuple[FunctionVersion, ...]
    next_before_sequence: int | None


@dataclass(frozen=True, slots=True)
class FunctionDiff:
    """What changes between two versions, by case key (read-only)."""

    from_function_hash: str
    to_function_hash: str
    from_revision: int
    to_revision: int
    from_policy_hash: str
    to_policy_hash: str
    from_projection_hash: str | None
    to_projection_hash: str | None
    projection_changed: bool
    from_program: JSONValue
    to_program: JSONValue
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Promotion:
    artifact_id: str
    replaced_artifact_ids: tuple[str, ...]
    promoted_at_us: int


# Inspection records (p89): the dicts the read and write methods return, typed per field. Runtime
# values stay plain dicts, so their JSON is unchanged; a stored JSON document stays `JSONValue`.


class PolicyRecord(TypedDict):
    min_confirmations: int
    min_reviewers: int
    min_span_seconds: int


class OperationRecord(TypedDict):
    created_at_us: int
    name: str
    policy: JSONValue
    policy_hash: str
    revision: int
    updated_at_us: int


class ProposalRecord(TypedDict):
    created_at_us: int
    final_output: JSONValue
    id: str
    input: JSONValue
    operation: str
    operation_revision: int
    proposed_output: JSONValue
    provenance: JSONValue
    review_note: str | None
    reviewed_at_us: int | None
    reviewer: str | None
    sequence: int
    status: str


class RevocationRecord(TypedDict):
    at_us: int
    by: str
    reason: str


class ExampleRecord(TypedDict):
    confirmed_at_us: int
    id: str
    input: JSONValue
    input_hash: str
    operation_revision: int
    origin: str
    output: JSONValue
    output_hash: str
    receipt_hash: str
    reviewer: str
    sequence: int
    source_id: str | None
    superseded_by: str | None
    supersedes_example_id: str | None
    revocation: RevocationRecord | None


class ArtifactSummaryRecord(TypedDict):
    artifact_hash: str
    build_hash: str
    created_at_us: int
    evidence_snapshot_hash: str
    id: str
    input_hash: str
    operation_revision: int
    promoted_at_us: int | None
    promotion_hash: str | None
    reviewer_count: int
    sequence: int
    scope_hash: str
    span_seconds: int
    status: str
    status_reason: str | None
    support: int
    verified_report_id: str | None


class ArtifactRecord(ArtifactSummaryRecord):
    document: JSONValue
    evidence_ids: list[str]


class ReportTestRecord(TypedDict):
    detail: str
    example_id: str | None
    key: str
    passed: bool


class ReportSummaryRecord(TypedDict):
    artifact_id: str
    build_hash: str
    created_at_us: int
    id: str
    passed: bool
    sequence: int
    scope_hash: str
    test_count: int
    test_set_hash: str


class ReportRecord(ReportSummaryRecord):
    artifact_hash: str
    details: JSONValue
    evidence_snapshot_hash: str
    policy_hash: str
    tests: list[ReportTestRecord]


class EventRecord(TypedDict):
    created_at_us: int
    kind: str
    payload: JSONValue
    sequence: int
    subject_id: str
    subject_type: str


class ProjectionRecord(TypedDict):
    operation_revision: int
    program: JSONValue
    program_hash: str


class ComparatorRecord(TypedDict):
    operation_revision: int
    comparator: JSONValue
    comparator_hash: str
    set_by: str
    set_at_us: int
    sequence: int


class ComparatorChange(TypedDict):
    changed: bool
    comparator_hash: str
    operation_revision: int


class ProjectionChange(TypedDict):
    changed: bool
    program_hash: str
    retired: list[str]


class ProjectionKeyRecord(TypedDict):
    key_hash: str
    support: int
    outputs: int


class ProjectionReportRecord(TypedDict):
    program_hash: str
    projected: int
    unprojected: list[str]
    keys: list[ProjectionKeyRecord]
    merged_outputs: list[str]
    unwitnessed_layouts: list[str]


class ProjectionPreviewKey(ProjectionKeyRecord):
    pending: int
    ready: bool


class ProjectionPreviewItem(TypedDict):
    kind: Literal["example", "proposal"]
    id: str
    key_hash: str | None
    reason: str | None


class ProjectionPreview(TypedDict):
    program_hash: str
    projected: int
    unprojected: list[str]
    keys: list[ProjectionPreviewKey]
    merged_outputs: list[str]
    unwitnessed_layouts: list[str]
    items: list[ProjectionPreviewItem]


class LearningCasesRecord(TypedDict):
    partition: str
    operation: str
    operation_revision: int
    grouped_by: Literal["candidate", "exact", "build-current"]
    program_hash: str | None
    cases: list[JSONValue]
    unprojected: dict[str, JSONValue]
    stale_pending_proposal_ids: list[JSONValue]
    unsourced_pending: list[JSONValue]
    work: dict[str, JSONValue]
    nothing_to_learn: bool
    program: NotRequired[ProgramDocument]
