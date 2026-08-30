"""Small immutable public values; all effectful behavior lives in ``System``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, TypeAlias, cast

from .errors import ValidationError
from .function import FunctionDocument, FunctionMatch
from .json_value import JSONValue


@dataclass(frozen=True, slots=True)
class CompilePolicy:
    min_confirmations: int = 3
    min_reviewers: int = 2
    min_span_seconds: int = 7 * 24 * 60 * 60

    def __post_init__(self) -> None:
        if any(
            type(value) is not int
            for value in (self.min_confirmations, self.min_reviewers, self.min_span_seconds)
        ):
            raise ValidationError("compile policy values must be integers")
        if not 2 <= self.min_confirmations <= 1_000_000:
            raise ValidationError("min_confirmations must be between 2 and 1,000,000")
        if not 1 <= self.min_reviewers <= self.min_confirmations:
            raise ValidationError("min_reviewers must be positive and no greater than confirmations")
        if not 0 <= self.min_span_seconds <= 10 * 365 * 24 * 60 * 60:
            raise ValidationError("min_span_seconds must be between zero and ten years")

    def as_json(self) -> dict[str, JSONValue]:
        return {
            "min_confirmations": self.min_confirmations,
            "min_reviewers": self.min_reviewers,
            "min_span_seconds": self.min_span_seconds,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, JSONValue]) -> "CompilePolicy":
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
    request_id: str
    input: JSONValue


@dataclass(frozen=True, slots=True)
class Resolved:
    request_id: str
    output: JSONValue
    source: Literal["artifact", "confirmed"]
    artifact_id: str | None = None
    example_id: str | None = None
    status: Literal["resolved"] = "resolved"


@dataclass(frozen=True, slots=True)
class ReviewRequired:
    request_id: str
    proposal_id: str
    status: Literal["review_required"] = "review_required"


@dataclass(frozen=True, slots=True)
class InProgress:
    request_id: str
    retry_after_seconds: int
    status: Literal["in_progress"] = "in_progress"


@dataclass(frozen=True, slots=True)
class FallbackFailed:
    request_id: str
    code: str
    status: Literal["fallback_failed"] = "fallback_failed"


@dataclass(frozen=True, slots=True)
class Rejected:
    request_id: str
    proposal_id: str
    status: Literal["rejected"] = "rejected"


@dataclass(frozen=True, slots=True)
class ReconciliationRequired:
    request_id: str
    reason: str
    artifact_id: str | None = None
    example_id: str | None = None
    status: Literal["reconciliation_required"] = "reconciliation_required"


Outcome: TypeAlias = (
    Resolved
    | ReviewRequired
    | InProgress
    | FallbackFailed
    | Rejected
    | ReconciliationRequired
)


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
class FunctionResolution:
    """One verification snapshot paired with the lookup taken inside it.

    For every verification the unmodified ``System.verify_function`` produces,
    ``match`` is ``None`` exactly when ``verification.passed`` is ``False``.
    That domain qualifier is load-bearing, and it names the implementation
    rather than the attribute: this class binds the two fields by no invariant,
    so an override or a hand-built ``FunctionVerification`` can carry
    ``passed=True`` with no document and still resolve to ``match`` ``None``.
    A failed verdict carries
    no answer at all. A verified ``matched=False`` is a proven absence inside a
    function that verified. Consumers must not collapse the two.
    """

    verification: FunctionVerification
    match: FunctionMatch | None


@dataclass(frozen=True, slots=True)
class Promotion:
    artifact_id: str
    replaced_artifact_ids: tuple[str, ...]
    promoted_at_us: int
