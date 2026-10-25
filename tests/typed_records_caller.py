"""p89 caller fixture: every field of every record the dict-returning API gives a caller.

Type-checked by `tests/test_typed_records.py` (mypy `--strict --disallow-any-expr`), never
imported or run. Each read is bound to its field type, so a record typed `dict[str, JSONValue]`
reds every non-JSON binding, and an `Any` anywhere reds the expression check.
"""

from __future__ import annotations

from typing import Literal

from cement_runtime import CompilePolicy, System, learning, projection
from cement_runtime.json_value import JSONValue
from cement_runtime.models import (
    ProjectionPreviewItem,
    ProjectionPreviewKey,
    ReportTestRecord,
    RevocationRecord,
)
from cement_runtime.projection import LayoutDocument, ProgramDocument


def read_every_field(  # noqa: PLR0915 — one binding per field, by design
    system: System,
    partition: str,
    operation: str,
    ids: tuple[str, str, str],
    program: object,
    inputs: list[JSONValue],
) -> None:
    proposal_id, artifact_id, report_id = ids
    r0 = system.proposal(partition, proposal_id)
    r0_created_at_us: int = r0["created_at_us"]
    r0_final_output: JSONValue = r0["final_output"]
    r0_id: str = r0["id"]
    r0_input: JSONValue = r0["input"]
    r0_operation: str = r0["operation"]
    r0_operation_revision: int = r0["operation_revision"]
    r0_proposed_output: JSONValue = r0["proposed_output"]
    r0_provenance: JSONValue = r0["provenance"]
    r0_review_note: str | None = r0["review_note"]
    r0_reviewed_at_us: int | None = r0["reviewed_at_us"]
    r0_reviewer: str | None = r0["reviewer"]
    r0_sequence: int = r0["sequence"]
    r0_status: str = r0["status"]
    r1 = system.proposals(partition)[0]
    r1_created_at_us: int = r1["created_at_us"]
    r1_final_output: JSONValue = r1["final_output"]
    r1_id: str = r1["id"]
    r1_input: JSONValue = r1["input"]
    r1_operation: str = r1["operation"]
    r1_operation_revision: int = r1["operation_revision"]
    r1_proposed_output: JSONValue = r1["proposed_output"]
    r1_provenance: JSONValue = r1["provenance"]
    r1_review_note: str | None = r1["review_note"]
    r1_reviewed_at_us: int | None = r1["reviewed_at_us"]
    r1_reviewer: str | None = r1["reviewer"]
    r1_sequence: int = r1["sequence"]
    r1_status: str = r1["status"]
    r2 = system.operations(partition)[0]
    r2_created_at_us: int = r2["created_at_us"]
    r2_name: str = r2["name"]
    r2_policy: JSONValue = r2["policy"]
    r2_policy_hash: str = r2["policy_hash"]
    r2_revision: int = r2["revision"]
    r2_updated_at_us: int = r2["updated_at_us"]
    r3 = system.examples(partition, operation)[0]
    r3_confirmed_at_us: int = r3["confirmed_at_us"]
    r3_id: str = r3["id"]
    r3_input: JSONValue = r3["input"]
    r3_input_hash: str = r3["input_hash"]
    r3_operation_revision: int = r3["operation_revision"]
    r3_origin: str = r3["origin"]
    r3_output: JSONValue = r3["output"]
    r3_output_hash: str = r3["output_hash"]
    r3_receipt_hash: str = r3["receipt_hash"]
    r3_reviewer: str = r3["reviewer"]
    r3_sequence: int = r3["sequence"]
    r3_source_id: str | None = r3["source_id"]
    r3_superseded_by: str | None = r3["superseded_by"]
    r3_supersedes_example_id: str | None = r3["supersedes_example_id"]
    r3_revocation: RevocationRecord | None = r3["revocation"]
    if r3_revocation is not None:
        r3_revocation_at_us: int = r3_revocation["at_us"]
        r3_revocation_by: str = r3_revocation["by"]
        r3_revocation_reason: str = r3_revocation["reason"]
    r4 = system.artifacts(partition, operation)[0]
    r4_artifact_hash: str = r4["artifact_hash"]
    r4_build_hash: str = r4["build_hash"]
    r4_created_at_us: int = r4["created_at_us"]
    r4_evidence_snapshot_hash: str = r4["evidence_snapshot_hash"]
    r4_id: str = r4["id"]
    r4_input_hash: str = r4["input_hash"]
    r4_operation_revision: int = r4["operation_revision"]
    r4_promoted_at_us: int | None = r4["promoted_at_us"]
    r4_promotion_hash: str | None = r4["promotion_hash"]
    r4_reviewer_count: int = r4["reviewer_count"]
    r4_sequence: int = r4["sequence"]
    r4_scope_hash: str = r4["scope_hash"]
    r4_span_seconds: int = r4["span_seconds"]
    r4_status: str = r4["status"]
    r4_status_reason: str | None = r4["status_reason"]
    r4_support: int = r4["support"]
    r4_verified_report_id: str | None = r4["verified_report_id"]
    r5 = system.artifact(partition, artifact_id)
    r5_artifact_hash: str = r5["artifact_hash"]
    r5_build_hash: str = r5["build_hash"]
    r5_created_at_us: int = r5["created_at_us"]
    r5_evidence_snapshot_hash: str = r5["evidence_snapshot_hash"]
    r5_id: str = r5["id"]
    r5_input_hash: str = r5["input_hash"]
    r5_operation_revision: int = r5["operation_revision"]
    r5_promoted_at_us: int | None = r5["promoted_at_us"]
    r5_promotion_hash: str | None = r5["promotion_hash"]
    r5_reviewer_count: int = r5["reviewer_count"]
    r5_sequence: int = r5["sequence"]
    r5_scope_hash: str = r5["scope_hash"]
    r5_span_seconds: int = r5["span_seconds"]
    r5_status: str = r5["status"]
    r5_status_reason: str | None = r5["status_reason"]
    r5_support: int = r5["support"]
    r5_verified_report_id: str | None = r5["verified_report_id"]
    r5_document: JSONValue = r5["document"]
    r5_evidence_ids: list[str] = r5["evidence_ids"]
    r6 = system.report(partition, report_id)
    r6_artifact_id: str = r6["artifact_id"]
    r6_build_hash: str = r6["build_hash"]
    r6_created_at_us: int = r6["created_at_us"]
    r6_id: str = r6["id"]
    r6_passed: bool = r6["passed"]
    r6_sequence: int = r6["sequence"]
    r6_scope_hash: str = r6["scope_hash"]
    r6_test_count: int = r6["test_count"]
    r6_test_set_hash: str = r6["test_set_hash"]
    r6_artifact_hash: str = r6["artifact_hash"]
    r6_details: JSONValue = r6["details"]
    r6_evidence_snapshot_hash: str = r6["evidence_snapshot_hash"]
    r6_policy_hash: str = r6["policy_hash"]
    r6_tests: list[ReportTestRecord] = r6["tests"]
    r6_tests_0 = r6_tests[0]
    r6_tests_0_detail: str = r6_tests_0["detail"]
    r6_tests_0_example_id: str | None = r6_tests_0["example_id"]
    r6_tests_0_key: str = r6_tests_0["key"]
    r6_tests_0_passed: bool = r6_tests_0["passed"]
    r7 = system.reports(partition, artifact_id=artifact_id)[0]
    r7_artifact_id: str = r7["artifact_id"]
    r7_build_hash: str = r7["build_hash"]
    r7_created_at_us: int = r7["created_at_us"]
    r7_id: str = r7["id"]
    r7_passed: bool = r7["passed"]
    r7_sequence: int = r7["sequence"]
    r7_scope_hash: str = r7["scope_hash"]
    r7_test_count: int = r7["test_count"]
    r7_test_set_hash: str = r7["test_set_hash"]
    r8 = system.events(partition)[0]
    r8_created_at_us: int = r8["created_at_us"]
    r8_kind: str = r8["kind"]
    r8_payload: JSONValue = r8["payload"]
    r8_sequence: int = r8["sequence"]
    r8_subject_id: str = r8["subject_id"]
    r8_subject_type: str = r8["subject_type"]
    maybe_r9 = system.projection(partition, operation)
    assert maybe_r9 is not None
    r9 = maybe_r9
    r9_operation_revision: int = r9["operation_revision"]
    r9_program: JSONValue = r9["program"]
    r9_program_hash: str = r9["program_hash"]
    r10 = system.test_projection(partition, operation, program)
    r10_program_hash: str = r10["program_hash"]
    r10_projected: int = r10["projected"]
    r10_unprojected: list[str] = r10["unprojected"]
    r10_keys: list[ProjectionPreviewKey] = r10["keys"]
    r10_keys_0 = r10_keys[0]
    r10_keys_0_key_hash: str = r10_keys_0["key_hash"]
    r10_keys_0_support: int = r10_keys_0["support"]
    r10_keys_0_outputs: int = r10_keys_0["outputs"]
    r10_keys_0_pending: int = r10_keys_0["pending"]
    r10_keys_0_ready: bool = r10_keys_0["ready"]
    r10_merged_outputs: list[str] = r10["merged_outputs"]
    r10_unwitnessed_layouts: list[str] = r10["unwitnessed_layouts"]
    r10_items: list[ProjectionPreviewItem] = r10["items"]
    r10_items_0 = r10_items[0]
    r10_items_0_kind: Literal["example", "proposal"] = r10_items_0["kind"]
    r10_items_0_id: str = r10_items_0["id"]
    r10_items_0_key_hash: str | None = r10_items_0["key_hash"]
    r10_items_0_reason: str | None = r10_items_0["reason"]
    r11 = system.set_projection(partition, operation, program, actor="caller")
    r11_changed: bool = r11["changed"]
    r11_program_hash: str = r11["program_hash"]
    r11_retired: list[str] = r11["retired"]
    r12 = system.learning_cases(partition, operation)
    r12_partition: str = r12["partition"]
    r12_operation: str = r12["operation"]
    r12_operation_revision: int = r12["operation_revision"]
    r12_grouped_by: Literal["candidate", "exact", "build-current"] = r12["grouped_by"]
    r12_program_hash: str | None = r12["program_hash"]
    r12_cases: list[JSONValue] = r12["cases"]
    r12_unprojected: dict[str, JSONValue] = r12["unprojected"]
    r12_stale_pending_proposal_ids: list[JSONValue] = r12["stale_pending_proposal_ids"]
    r12_unsourced_pending: list[JSONValue] = r12["unsourced_pending"]
    r12_work: dict[str, JSONValue] = r12["work"]
    r12_nothing_to_learn: bool = r12["nothing_to_learn"]
    r12_program: ProgramDocument = r12["program"]
    r13 = learning.cases(system, partition, operation, projectable=True)
    r13_partition: str = r13["partition"]
    r13_operation: str = r13["operation"]
    r13_operation_revision: int = r13["operation_revision"]
    r13_grouped_by: Literal["candidate", "exact", "build-current"] = r13["grouped_by"]
    r13_program_hash: str | None = r13["program_hash"]
    r13_cases: list[JSONValue] = r13["cases"]
    r13_unprojected: dict[str, JSONValue] = r13["unprojected"]
    r13_stale_pending_proposal_ids: list[JSONValue] = r13["stale_pending_proposal_ids"]
    r13_unsourced_pending: list[JSONValue] = r13["unsourced_pending"]
    r13_work: dict[str, JSONValue] = r13["work"]
    r13_nothing_to_learn: bool = r13["nothing_to_learn"]
    r13_program: ProgramDocument = r13["program"]
    r14 = projection.draft_program(inputs)
    r14_abi: str = r14["abi"]
    r14_text: str = r14["text"]
    r14_keep: list[str] = r14["keep"]
    r14_layouts: list[LayoutDocument] = r14["layouts"]
    r14_layouts_0 = r14_layouts[0]
    r14_layouts_0_name: str = r14_layouts_0["name"]
    r14_layouts_0_title: str = r14_layouts_0["title"]
    r14_layouts_0_entries: list[dict[str, str]] = r14_layouts_0["entries"]
    r15 = CompilePolicy().as_json()
    r15_min_confirmations: int = r15["min_confirmations"]
    r15_min_reviewers: int = r15["min_reviewers"]
    r15_min_span_seconds: int = r15["min_span_seconds"]
    r16 = system.set_comparator(partition, operation, program, actor="caller")
    r16_changed: bool = r16["changed"]
    r16_comparator_hash: str = r16["comparator_hash"]
    r16_operation_revision: int = r16["operation_revision"]
    maybe_r17 = system.comparator(partition, operation)
    assert maybe_r17 is not None
    r17 = maybe_r17
    r17_operation_revision: int = r17["operation_revision"]
    r17_comparator: JSONValue = r17["comparator"]
    r17_comparator_hash: str = r17["comparator_hash"]
    r17_set_by: str = r17["set_by"]
    r17_set_at_us: int = r17["set_at_us"]
    r17_sequence: int = r17["sequence"]
