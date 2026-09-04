"""Guided, deterministic lifecycle demo for the hospital OCR example.

The in-process plan proposer is deliberately not an LLM; it stands in for a
bespoke extraction-plan call while keeping this demo offline and repeatable.
Cement can return a reviewed plan deterministically for a known layout
signature, but the adapter and reviewer remain responsible for whether that
plan extracts future documents correctly.

Each artifact promotion is sealed into the verified function set immediately, so
the next document of a known layout resolves from that set. The closing act
answers one document from the exported bytes alone, after the ledger is deleted.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from cement_runtime import (
    Candidate,
    CandidateRequest,
    CompilePolicy,
    FunctionDocument,
    FunctionMatch,
    System,
    evaluate,
    parse_function,
)
from cement_runtime.json_value import canonicalize

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
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def checkpoint_function(system: System) -> FunctionDocument:
    """Seal every promoted entry of this operation as one verified function.

    Returns the portable document whose `.text` is the exportable bundle and
    whose `.function_hash` is the identity an operator carries away.
    """

    manifest = system.inspect_function_promotion(PARTITION, OPERATION)
    system.promote_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
        promoted_by="informatics-lead",
    )
    verification = system.verify_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
    )
    assert verification.passed
    assert verification.document is not None
    return verification.document


def resolve_offline(
    bundle_text: str,
    ocr_text: str,
    *,
    expected_function_hash: str,
) -> tuple[str, FunctionMatch]:
    """Answer one document from exported bytes alone, with no ledger reachable.

    `expected_function_hash` is the identity the operator carried away from the
    verified set. It is required, and `parse_function` raises `IntegrityError`
    when the bundle does not match it, so the binding survives `python -O` while
    a bare `assert` would not. The hash is returned beside the match for callers
    that report it.
    """

    function = parse_function(
        bundle_text,
        expected_function_hash=expected_function_hash,
    )
    signature = pipeline.layout_signature(ocr_text)
    match = evaluate(function, input_json=canonicalize(signature))
    return function.function_hash, match


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
    if not __debug__:
        raise SystemExit(
            "This demo verifies its results with assert statements. "
            "Python removes them under -O and -OO. Run this demo again without -O or -OO."
        )
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

        proposal_a_01 = system.propose(PARTITION, OPERATION, a_signature_01)
        print("A01: adapter proposed a plan; records-supervisor review is required.")
        system.review(
            PARTITION,
            proposal_a_01,
            reviewer="records-supervisor",
            decision="accept",
        )
        print("A01: supervisor accepted the proposed layout-A plan.")

        proposal_a_02 = system.propose(PARTITION, OPERATION, a_signature_02)
        print("A02: the same layout recurred; its plan again requires supervision.")
        system.review(
            PARTITION,
            proposal_a_02,
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
        function = checkpoint_function(system)
        print(
            f"Function set: {len(function.input_hashes)} verified entry promoted; "
            "layout A now answers from the set."
        )

        print("\n=== Act 2: known layout A resolves without the adapter ===")
        calls_before = source.calls
        resolution_a = system.resolve(PARTITION, OPERATION, a_signature_03)
        assert resolution_a.verification.passed
        assert resolution_a.match is not None
        assert resolution_a.match.matched
        assert source.calls == calls_before
        extracted_a = pipeline.apply_plan(resolution_a.match.output, a_text_03)
        assert extracted_a["mrn"] == "MG-100913"
        print("A03: the verified set returned the confirmed plan; adapter calls stayed flat.")
        print(f"A03 patient JSON: {json.dumps(extracted_a, sort_keys=True)}")

        print("\n=== Act 3: genuinely new layout B follows the same lifecycle ===")
        b_text_01, b_signature_01 = _document("layout_b_intake_form_01.txt")
        _, b_signature_02 = _document("layout_b_intake_form_02.txt")
        assert _signature_bytes(b_signature_01) == _signature_bytes(b_signature_02)
        assert _signature_bytes(b_signature_01) != _signature_bytes(a_signature_01)

        proposal_b_01 = system.propose(PARTITION, OPERATION, b_signature_01)
        system.review(
            PARTITION,
            proposal_b_01,
            reviewer="records-supervisor",
            decision="accept",
        )
        print("B01: unseen intake-form layout used the same supervised fallback.")

        proposal_b_02 = system.propose(PARTITION, OPERATION, b_signature_02)
        system.review(
            PARTITION,
            proposal_b_02,
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
        function = checkpoint_function(system)
        print(
            f"Function set: {len(function.input_hashes)} verified entries, one per "
            "promoted layout."
        )

        calls_before = source.calls
        resolution_b = system.resolve(PARTITION, OPERATION, b_signature_01)
        assert resolution_b.verification.passed
        assert resolution_b.match is not None
        assert resolution_b.match.matched
        assert source.calls == calls_before
        extracted_b = pipeline.apply_plan(resolution_b.match.output, b_text_01)
        assert extracted_b["insurance_id"] == "HZN-774201"
        print("Layout B: promoted and then resolved with no adapter invocation.")
        print(f"B01 patient JSON: {json.dumps(extracted_b, sort_keys=True)}")

        print("\n=== Act 4: layout C remains gated after one confirmation ===")
        c_text_01, c_signature_01 = _document("layout_c_lab_slip_01.txt")
        c_input_hash = hashlib.sha256(_signature_bytes(c_signature_01)).hexdigest()
        assert _signature_bytes(c_signature_01) != _signature_bytes(a_signature_01)
        assert _signature_bytes(c_signature_01) != _signature_bytes(b_signature_01)

        proposal_c_01 = system.propose(PARTITION, OPERATION, c_signature_01)
        system.review(
            PARTITION,
            proposal_c_01,
            reviewer="records-supervisor",
            decision="accept",
        )

        build_c = system.compile(PARTITION, OPERATION)
        assert not build_c.created
        assert build_c.blocked
        gated = next(
            (
                record
                for record in build_c.blocked
                if record.get("input_hash") == c_input_hash
            ),
            None,
        )
        assert gated is not None
        assert gated.get("support") == 1
        reasons = gated.get("reasons")
        assert type(reasons) is list
        assert any(
            type(reason) is str and "below required" in reason
            for reason in reasons
        )
        print("Layout C: reviewed once but not promoted; policy still gates it.")
        print("Gate reasons: " + "; ".join(str(reason) for reason in reasons))

        print("\n=== Act 5: the verified set exports as portable bytes ===")
        bundle_text = function.text
        print(
            f"Exported set: {len(function.input_hashes)} verified entries, promoted "
            "before Acts 2 and 3 resolved against them."
        )
        print(f"Verified function hash: {function.function_hash}")
        print(
            f"Exported bundle: {len(bundle_text.encode('utf-8'))} bytes carrying "
            "no ledger."
        )

        _print_event_trace(system)

    assert not os.path.exists(temporary_directory)

    print("\n=== Act 6: the exported function answers with no ledger ===")
    print("The temporary ledger and its audit trail are gone; only the bundle remains.")
    offline_hash, offline_a = resolve_offline(
        bundle_text, a_text_03, expected_function_hash=function.function_hash
    )
    assert offline_hash == function.function_hash
    assert offline_a.matched
    offline_extracted = pipeline.apply_plan(offline_a.output, a_text_03)
    assert offline_extracted == extracted_a
    print("A03 offline: the bundle returned the same plan under the same verified hash.")
    print(f"A03 offline patient JSON: {json.dumps(offline_extracted, sort_keys=True)}")
    _, offline_c = resolve_offline(
        bundle_text, c_text_01, expected_function_hash=function.function_hash
    )
    assert not offline_c.matched
    assert offline_c.output is None
    print("C01 offline: layout C never entered the function, so the bundle reports a miss.")

    print(
        "\nProduction policy defaults remain stricter; this demo relaxes them only "
        "for a fast, self-contained run."
    )
    print("All checks passed.")


if __name__ == "__main__":
    main()
