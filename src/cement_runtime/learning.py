"""The learning pass's bookkeeping: merge one case, publish one version.

The pass judges two things: whether an operation's answers depend on form structure alone
(``projectable``), and the merged output of each case. The rest is mechanical, so the CLI and both
chat examples run this one copy. It composes public ``System`` methods; each write commits alone,
and nothing here switches a function on.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, cast

from .errors import CementError, ValidationError
from .json_value import JSONValue, canonicalize
from .models import (
    CompileResult,
    DraftVerification,
    FunctionSetPromotion,
    LearningCasesRecord,
    ProjectionChange,
)
from .projection import draft_program
from .system import System

REVIEWER = "learning-pass"
_PAGE = 1_000


@dataclass(frozen=True, slots=True)
class ReviewedProposal:
    proposal_id: str
    status: str


@dataclass(frozen=True, slots=True)
class Merge:
    """The writes of one merge, in the order they committed."""

    key_hash: str
    reviewed: tuple[ReviewedProposal, ...] = ()
    superseded_example_ids: tuple[str, ...] = ()
    new_example_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Publication:
    """One publish step. ``reason`` says why nothing was promoted: a draft failed verification,
    no case has enough confirmations, or the newest version already holds the set."""

    published: bool
    reason: Literal["failed", "empty", "same"] | None
    layouts: tuple[str, ...] = ()
    projection: ProjectionChange | None = None
    compiled: CompileResult | None = None
    drafts: DraftVerification | None = None
    function_hash: str | None = None
    entries: int = 0
    promotion: FunctionSetPromotion | None = None


MergeRefusal = Literal["not_a_list", "no_ids", "repeated_ids", "not_one_case"]


class MergeRefusedError(ValidationError):
    """A merge refused before any write."""

    def __init__(self, reason: MergeRefusal) -> None:
        super().__init__(
            {
                "not_a_list": "pass the ids as a list, not as one string",
                "no_ids": "name the proposal ids or example ids of one case",
                "repeated_ids": "name each id once",
                "not_one_case": "the ids are not the pending or active ids of one case",
            }[reason]
        )
        self.reason = reason


class MergeInterruptedError(CementError):
    """A merge write raised ``cause``. ``completed`` holds the writes that returned before it; the
    raising write may have committed too (a write can commit and then fail), so read the ledger
    again (``cases``) before any retry."""

    def __init__(self, cause: CementError, completed: Merge) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.completed = completed


def raw_inputs(system: System, partition: str, operation: str, *, pending: bool) -> list[JSONValue]:
    """Inputs of the current revision's active examples, then of its pending proposals if asked."""

    revision = system.learning_cases(partition, operation)["operation_revision"]
    found: list[JSONValue] = []
    after = 0
    while True:
        page = system.examples(partition, operation, after_sequence=after, limit=_PAGE)
        found += [
            row["input"]
            for row in page
            if row["superseded_by"] is None and row["operation_revision"] == revision
        ]
        if len(page) < _PAGE:
            break
        after = page[-1]["sequence"]
    after = 0
    while pending:
        rows = system.proposals(partition, status="pending", after_sequence=after, limit=_PAGE)
        found += [
            row["input"]
            for row in rows
            if row["operation"] == operation and row["operation_revision"] == revision
        ]
        if len(rows) < _PAGE:
            break
        after = rows[-1]["sequence"]
    return found


def cases(
    system: System, partition: str, operation: str, *, projectable: bool = False
) -> LearningCasesRecord:
    """``System.learning_cases``; when projectable, grouped by a program derived from the raw
    inputs (one layout per form structure), which rides along as ``program``."""

    if not projectable:
        return system.learning_cases(partition, operation)
    program = draft_program(raw_inputs(system, partition, operation, pending=True))
    grouped = system.learning_cases(partition, operation, program=program)
    grouped["program"] = program
    return grouped


def _same(left: object, right: object) -> bool:
    return canonicalize(left).digest == canonicalize(right).digest


def check_merge_ids(
    proposal_ids: Sequence[str], example_ids: Sequence[str]
) -> tuple[list[str], list[str]]:
    """The id-list rules of ``merge_case``, which reads nothing: a caller that reads the merged
    output afterwards can refuse a bad id list first."""

    if isinstance(proposal_ids, str) or isinstance(example_ids, str):
        raise MergeRefusedError("not_a_list")
    proposals, examples = list(proposal_ids), list(example_ids)
    if not proposals and not examples:
        raise MergeRefusedError("no_ids")
    if len(set(proposals)) != len(proposals) or len(set(examples)) != len(examples):
        raise MergeRefusedError("repeated_ids")
    return proposals, examples


def merge_case(
    system: System,
    partition: str,
    operation: str,
    output: object,
    *,
    note: str,
    proposal_ids: Sequence[str] = (),
    example_ids: Sequence[str] = (),
    projectable: bool = False,
    reviewer: str = REVIEWER,
) -> Merge:
    """Confirm ``output`` as the merge of one case.

    Each named pending proposal is accepted when it equals the merge and corrected to it otherwise;
    the named active examples whose output differs are superseded by it in one call. The ids must
    belong to exactly one case under the grouping ``projectable`` selects. Refusals write nothing.
    Each write commits alone, so a failure once the writes begin raises ``MergeInterruptedError``
    naming the writes that returned: a blind retry would refuse them.
    """

    proposals, examples = check_merge_ids(proposal_ids, example_ids)
    listed = cast(
        list[dict[str, Any]], cases(system, partition, operation, projectable=projectable)["cases"]
    )
    owner = [
        case
        for case in listed
        if set(proposals) <= set(case["pending_proposal_ids"])
        and set(examples) <= set(case["active_example_ids"])
    ]
    if len(owner) != 1:
        raise MergeRefusedError("not_one_case")
    canonicalize(output)
    (case,) = owner
    # The case lists every output with its proposals + examples, read in one snapshot: no read
    # runs between writes, and a paged `System.examples` read could miss an example.
    outputs = {
        ident: entry["output"]
        for entry in case["outputs"]
        for ident in (*entry["proposal_ids"], *entry["example_ids"])
    }
    key_hash = str(case["key_hash"])
    reviewed: list[ReviewedProposal] = []
    try:
        for proposal_id in proposals:
            if _same(outputs[proposal_id], output):
                result = system.review(
                    partition, proposal_id, reviewer=reviewer, decision="accept", note=note
                )
            else:
                result = system.review(
                    partition,
                    proposal_id,
                    reviewer=reviewer,
                    decision="correct",
                    corrected_output=output,
                    note=note,
                )
            reviewed.append(ReviewedProposal(proposal_id, result.status))
        differing = [example for example in examples if not _same(outputs[example], output)]
        created: tuple[str, ...] = ()
        if differing:
            created = tuple(
                system.supersede_examples(
                    partition,
                    operation,
                    example_ids=differing,
                    output=output,
                    reviewer=reviewer,
                    note=note,
                )
            )
    except CementError as exc:
        raise MergeInterruptedError(exc, Merge(key_hash, tuple(reviewed))) from exc
    return Merge(key_hash, tuple(reviewed), tuple(differing), created)


def publish(
    system: System,
    partition: str,
    operation: str,
    *,
    projectable: bool = False,
    actor: str = REVIEWER,
) -> Publication:
    """Publish a new version: set the derived projection program (when projectable), compile,
    verify the drafts and promote the verified set. The switch stays as it is: ``off`` answers
    nothing, ``follow`` serves the new version at once, ``pinned`` keeps its version. A failing
    step raises; a rerun repeats the earlier steps without new rows
    (an identical program is a no-op, compile lists existing drafts as ``existing``)."""

    layouts: tuple[str, ...] = ()
    projection = None
    if projectable:
        confirmed = raw_inputs(system, partition, operation, pending=False)
        if not confirmed:
            # No merge confirmed anything yet: a program over no documents would only be refused.
            return Publication(published=False, reason="empty")
        program = draft_program(confirmed)
        projection = system.set_projection(partition, operation, program, actor=actor)
        layouts = tuple(
            str(layout["title"]) for layout in cast(list[dict[str, Any]], program["layouts"])
        )
    compiled = system.compile(partition, operation, compiled_by=actor)
    drafts = system.verify_drafts(partition, operation, verified_by=actor)
    report = Publication(
        published=False,
        reason="failed",
        layouts=layouts,
        projection=projection,
        compiled=compiled,
        drafts=drafts,
    )
    if not drafts.passed:
        return report
    manifest = system.inspect_function_promotion(partition, operation)
    report = replace(
        report, reason="empty", function_hash=manifest.function_hash, entries=len(manifest.entries)
    )
    if not manifest.entries:
        return report
    newest = system.function_versions(partition, operation, limit=1).versions
    if newest and newest[0].receipt.function_hash == manifest.function_hash:
        return replace(report, reason="same")
    promotion = system.promote_function(
        partition,
        operation,
        expected_function_hash=manifest.function_hash,
        promoted_by=actor,
    )
    return replace(report, published=True, reason=None, promotion=promotion)
