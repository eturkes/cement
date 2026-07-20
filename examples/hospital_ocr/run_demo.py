"""Guided, deterministic lifecycle demo for the hospital OCR example.

The in-process plan proposer is deliberately not an LLM; it stands in for a
bespoke extraction-plan call while keeping this demo offline and repeatable.
Cement can return a reviewed plan deterministically for a known layout
signature, but the adapter and reviewer remain responsible for whether that
plan extracts future documents correctly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from cement_runtime import (
    Candidate,
    CandidateRequest,
    CompilePolicy,
    Resolved,
    ReviewRequired,
    System,
)

import pipeline
from plan_adapter import PlanProposer


PARTITION = "mercy-general"
OPERATION = "document.extraction_plan"
DOCUMENTS = Path(__file__).with_name("documents")
DEMO_POLICY = CompilePolicy(
    min_confirmations=2,
    min_reviewers=1,
    min_span_seconds=0,
)


class CountingSource:
    """Delegate candidate generation while counting adapter invocations."""

    def __init__(self, inner: PlanProposer) -> None:
        self._inner = inner
        self.calls = 0

    def propose(self, request: CandidateRequest) -> Candidate:
        self.calls += 1
        return self._inner.propose(request)


def _document(name: str) -> tuple[str, pipeline.JSONValue]:
    ocr_text = pipeline.ocr(DOCUMENTS / name)
    return ocr_text, pipeline.layout_signature(ocr_text)


def _signature_bytes(signature: pipeline.JSONValue) -> bytes:
    return json.dumps(
        signature,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _print_event_trace(system: System) -> None:
    print("\n=== Audit event trace ===")
    for index, event in enumerate(system.events(PARTITION), start=1):
        event_type = event.get("type")
        if type(event_type) is not str:
            event_type = event.get("kind")
        if type(event_type) is not str:
            event_type = "<missing type>"

        detail = ""
        for key in ("request_id", "proposal_id", "artifact_id"):
            value = event.get(key)
            if type(value) is str:
                detail = f"  {key}={value}"
                break
        print(f"{index:02d}. {event_type}{detail}")


def main() -> None:
    print("Hospital OCR layout-learning demo (offline; no LLM or network).")
    print(
        "Cement receives patient-independent layout signatures and returns "
        "reviewed extraction plans; the deterministic pipeline applies each "
        "plan to patient OCR."
    )
    print(
        "Demo policy: 2 confirmations, 1 reviewer, no minimum time span. "
        "Production defaults are stricter: 3 confirmations, 2 reviewers, "
        "and a 7-day span."
    )
    print(
        "Boundary: cement guarantees deterministic plan return for a known "
        "layout signature, not correct extraction from every future document; "
        "that remains the adapter/reviewer's responsibility."
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        database = os.path.join(temporary_directory, "cement.db")
        source = CountingSource(PlanProposer())
        system = System(database, candidate_source=source)
        system.register_operation(PARTITION, OPERATION, policy=DEMO_POLICY)

        print("\n=== Act 1: layout A recurs, is reviewed, and is promoted ===")
        _, a_signature_01 = _document("layout_a_progress_note_01.txt")
        _, a_signature_02 = _document("layout_a_progress_note_02.txt")
        a_text_03, a_signature_03 = _document("layout_a_progress_note_03.txt")
        assert _signature_bytes(a_signature_01) == _signature_bytes(a_signature_02)
        assert _signature_bytes(a_signature_02) == _signature_bytes(a_signature_03)
        print("Three patients share one byte-identical, patient-free layout signature.")

        outcome_a_01 = system.handle(
            PARTITION,
            OPERATION,
            a_signature_01,
            request_id="a-note-01",
        )
        assert isinstance(outcome_a_01, ReviewRequired)
        print("A01: adapter proposed a plan; records-supervisor review is required.")
        system.review(
            PARTITION,
            outcome_a_01.proposal_id,
            reviewer="records-supervisor",
            decision="accept",
        )
        print("A01: supervisor accepted the proposed layout-A plan.")

        outcome_a_02 = system.handle(
            PARTITION,
            OPERATION,
            a_signature_02,
            request_id="a-note-02",
        )
        assert isinstance(outcome_a_02, ReviewRequired)
        print("A02: the same layout recurred; its plan again requires supervision.")
        system.review(
            PARTITION,
            outcome_a_02.proposal_id,
            reviewer="records-supervisor",
            decision="accept",
        )
        print("A02: second confirmation reached the relaxed demo threshold.")

        build_a = system.compile(PARTITION, OPERATION)
        assert len(build_a.created) == 1
        artifact_a = build_a.created[0]
        report_a = system.verify(PARTITION, artifact_a)
        assert report_a.passed
        system.promote(
            PARTITION,
            artifact_a,
            scope_hash=report_a.scope_hash,
            promoted_by="informatics-lead",
        )
        print(
            f"Layout A: compiled, verified ({report_a.tests} tests), and promoted "
            f"as {artifact_a}."
        )

        print("\n=== Act 2: known layout A resolves without the adapter ===")
        calls_before = source.calls
        resolved_a = system.handle(
            PARTITION,
            OPERATION,
            a_signature_03,
            request_id="a-note-03",
        )
        assert isinstance(resolved_a, Resolved)
        assert resolved_a.source == "artifact"
        assert source.calls == calls_before
        extracted_a = pipeline.apply_plan(resolved_a.output, a_text_03)
        assert extracted_a["mrn"] == "MG-100913"
        print("A03: promoted artifact returned the confirmed plan; adapter calls stayed flat.")
        print(f"A03 patient JSON: {json.dumps(extracted_a, sort_keys=True)}")

        print("\n=== Act 3: genuinely new layout B follows the same lifecycle ===")
        b_text_01, b_signature_01 = _document("layout_b_intake_form_01.txt")
        _, b_signature_02 = _document("layout_b_intake_form_02.txt")
        assert _signature_bytes(b_signature_01) == _signature_bytes(b_signature_02)
        assert _signature_bytes(b_signature_01) != _signature_bytes(a_signature_01)

        outcome_b_01 = system.handle(
            PARTITION,
            OPERATION,
            b_signature_01,
            request_id="b-intake-01",
        )
        assert isinstance(outcome_b_01, ReviewRequired)
        system.review(
            PARTITION,
            outcome_b_01.proposal_id,
            reviewer="records-supervisor",
            decision="accept",
        )
        print("B01: unseen intake-form layout used the same supervised fallback.")

        outcome_b_02 = system.handle(
            PARTITION,
            OPERATION,
            b_signature_02,
            request_id="b-intake-02",
        )
        assert isinstance(outcome_b_02, ReviewRequired)
        system.review(
            PARTITION,
            outcome_b_02.proposal_id,
            reviewer="records-supervisor",
            decision="accept",
        )
        print("B02: second confirmation made layout B eligible to compile.")

        build_b = system.compile(PARTITION, OPERATION)
        assert len(build_b.created) == 1
        assert not build_b.blocked
        artifact_b = build_b.created[0]
        report_b = system.verify(PARTITION, artifact_b)
        assert report_b.passed
        system.promote(
            PARTITION,
            artifact_b,
            scope_hash=report_b.scope_hash,
            promoted_by="informatics-lead",
        )

        calls_before = source.calls
        resolved_b = system.handle(
            PARTITION,
            OPERATION,
            b_signature_01,
            request_id="b-intake-recur",
        )
        assert isinstance(resolved_b, Resolved)
        assert resolved_b.source == "artifact"
        assert source.calls == calls_before
        extracted_b = pipeline.apply_plan(resolved_b.output, b_text_01)
        assert extracted_b["insurance_id"] == "HZN-774201"
        print("Layout B: promoted and then resolved with no adapter invocation.")
        print(f"B01 patient JSON: {json.dumps(extracted_b, sort_keys=True)}")

        print("\n=== Act 4: layout C remains gated after one confirmation ===")
        _, c_signature_01 = _document("layout_c_lab_slip_01.txt")
        assert _signature_bytes(c_signature_01) != _signature_bytes(a_signature_01)
        assert _signature_bytes(c_signature_01) != _signature_bytes(b_signature_01)

        outcome_c_01 = system.handle(
            PARTITION,
            OPERATION,
            c_signature_01,
            request_id="c-lab-01",
        )
        assert isinstance(outcome_c_01, ReviewRequired)
        system.review(
            PARTITION,
            outcome_c_01.proposal_id,
            reviewer="records-supervisor",
            decision="accept",
        )

        build_c = system.compile(PARTITION, OPERATION)
        assert not build_c.created
        assert build_c.blocked
        gated = build_c.blocked[0]
        assert gated.get("support") == 1
        reasons = gated.get("reasons")
        assert type(reasons) is list
        assert any(
            type(reason) is str and "below required" in reason
            for reason in reasons
        )
        print("Layout C: reviewed once but not promoted; policy still gates it.")
        print("Gate reasons: " + "; ".join(str(reason) for reason in reasons))

        _print_event_trace(system)

    assert not os.path.exists(temporary_directory)
    print(
        "\nProduction policy defaults remain stricter; this demo relaxes them only "
        "for a fast, self-contained run."
    )
    print("All checks passed.")


if __name__ == "__main__":
    main()
