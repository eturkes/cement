"""Raw documents → scripted learning pass → versioned, switched extraction plans.

The provider and learning pass are offline stand-ins for LLM calls. The ledger,
projection checks, compilation, verification, promotion and switch are real.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pipeline
from plan_adapter import PlanProposer

from cement_runtime import (
    Candidate,
    CandidateRequest,
    CompilePolicy,
    CompileResult,
    FunctionDocument,
    FunctionMatch,
    System,
    evaluate,
    parse_function,
)
from cement_runtime.json_value import canonicalize
from cement_runtime.projection import structure

PARTITION = "example-hospital"
OPERATION = "document.extraction_plan"
DOCUMENTS = Path(__file__).with_name("documents")
DEMO_POLICY = CompilePolicy()


class CountingSource:
    """Delegate candidate generation while counting adapter invocations."""

    def __init__(self, inner: PlanProposer) -> None:
        self._inner = inner
        self.calls = 0

    def propose(self, request: CandidateRequest) -> Candidate:
        self.calls += 1
        return self._inner.propose(request)


def _document(name: str) -> dict[str, str]:
    return {"document": pipeline.ocr(DOCUMENTS / name)}


def _program(inputs: list[pipeline.JSONValue]) -> pipeline.JSONValue:
    layouts = {}
    for raw in inputs:
        parsed = structure(raw["document"])
        if parsed is None:
            raise ValueError("the scripted pass requires the demo's document grammar")
        title, pairs = parsed
        layouts[(title, pairs)] = {
            "name": title.lower(),
            "title": title,
            "entries": [{kind: key} for kind, key in pairs],
        }
    return {
        "abi": "cement-projection-v1",
        "text": "document",
        "keep": [],
        "layouts": [layouts[key] for key in sorted(layouts)],
    }


def _merge_plans(outputs: list[pipeline.JSONValue]) -> pipeline.JSONValue:
    """Union compatible plan rows; a disagreement needs real LLM judgment."""

    merged = json.loads(canonicalize(outputs[0]).text)
    fields = {field["name"]: field for field in merged["fields"]}
    for output in outputs[1:]:
        if (output["document_type"], output["layout"]) != (
            merged["document_type"],
            merged["layout"],
        ):
            raise ValueError("the scripted pass cannot merge different plan kinds")
        for field in output["fields"]:
            name = field["name"]
            if name in fields and fields[name] != field:
                raise ValueError("the scripted pass cannot resolve conflicting plan rows")
            fields[name] = field
    merged["fields"] = list(fields.values())
    return merged


def checkpoint_function(system: System) -> FunctionDocument:
    """Publish the verified cases as one version without changing the switch."""

    manifest = system.inspect_function_promotion(PARTITION, OPERATION)
    system.promote_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
        promoted_by="learning-pass",
    )
    verification = system.verify_function(
        PARTITION,
        OPERATION,
        expected_function_hash=manifest.function_hash,
    )
    assert verification.passed
    assert verification.document is not None
    return verification.document


def learning_pass(system: System, *, run: int) -> tuple[FunctionDocument, CompileResult]:
    """Imitate cement-learn on this bounded corpus, never on arbitrary model output.

    The scripted semantic decision is specific to these plans: each output reads
    values from a document. The runtime checks the projection, not that decision.
    """

    work = system.learning_cases(PARTITION, OPERATION)
    examples = {row["id"]: row for row in system.examples(PARTITION, OPERATION)}
    proposal_ids = list(work["unprojected"]["proposal_ids"])
    example_ids = list(work["unprojected"]["example_ids"])
    for case in work["cases"]:
        proposal_ids.extend(case["pending_proposal_ids"])
        example_ids.extend(case["active_example_ids"])
    inputs = [system.proposal(PARTITION, ident)["input"] for ident in proposal_ids]
    inputs.extend(examples[ident]["input"] for ident in example_ids)
    program = _program(inputs)
    grouped = system.learning_cases(PARTITION, OPERATION, program=program)
    assert not any(grouped["unprojected"].values())
    note = f"demo run {run}; scripted stand-in, no LLM"
    for case in grouped["cases"]:
        merged = _merge_plans([row["output"] for row in case["outputs"]])
        for row in case["outputs"]:
            changed = row["output"] != merged
            for ident in row["proposal_ids"]:
                correction = {"corrected_output": merged} if changed else {}
                system.review(
                    PARTITION,
                    ident,
                    reviewer="learning-pass",
                    decision="correct" if changed else "accept",
                    note=note,
                    **correction,
                )
            if changed and row["example_ids"]:
                system.supersede_examples(
                    PARTITION,
                    OPERATION,
                    example_ids=row["example_ids"],
                    output=merged,
                    reviewer="learning-pass",
                    note=note,
                )
    preview = system.test_projection(PARTITION, OPERATION, program)
    assert preview["projected"] > 0
    assert not any(preview[key] for key in ("unprojected", "unwitnessed_layouts", "merged_outputs"))
    system.set_projection(PARTITION, OPERATION, program, actor="learning-pass")
    build = system.compile(PARTITION, OPERATION, compiled_by="learning-pass")
    verified = system.verify_drafts(PARTITION, OPERATION, verified_by="learning-pass")
    assert verified.passed
    return checkpoint_function(system), build


def resolve_offline(
    bundle_text: str,
    ocr_text: str,
    *,
    expected_function_hash: str,
) -> tuple[str, FunctionMatch]:
    """Use the shipped parser and evaluator on raw input, with the held hash required."""

    function = parse_function(bundle_text, expected_function_hash=expected_function_hash)
    match = evaluate(function, input_json=canonicalize({"document": ocr_text}))
    return function.function_hash, match


def _print_event_trace(system: System) -> None:
    print("\n=== Audit event trace ===")
    for index, event in enumerate(system.events(PARTITION), start=1):
        print(f"{index:02d}. {event['kind']}")


def main() -> None:
    if not __debug__:
        raise SystemExit(
            "This demo verifies its results with assert statements. "
            "Python removes them under -O and -OO. Run this demo again without -O or -OO."
        )
    print("Hospital OCR learning demo (offline; no LLM or network).")
    print("The plan adapter and learning pass are scripted stand-ins for LLM calls.")
    print("Cement receives raw documents. The projection maps each recognized layout to one case.")
    print("Default policy: 2 confirmations, 1 reviewer, no minimum time span.")
    print("Assumption: documents with one layout need one extraction plan.")
    print(
        "Cement checks structure and consistency, not whether that assumption or plan is correct."
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        database = os.path.join(temporary_directory, "cement.db")
        source = CountingSource(PlanProposer())
        system = System(database, candidate_source=source)
        system.register_operation(PARTITION, OPERATION, policy=DEMO_POLICY)

        print("\n=== Act 1: retain the model's answers to raw documents ===")
        names = (
            "layout_a_progress_note_01.txt",
            "layout_a_progress_note_02.txt",
            "layout_b_intake_form_01.txt",
            "layout_b_intake_form_02.txt",
            "layout_c_lab_slip_01.txt",
        )
        proposals = [system.propose(PARTITION, OPERATION, _document(name)) for name in names]
        assert source.calls == 5
        assert all(system.proposal(PARTITION, ident)["status"] == "pending" for ident in proposals)
        assert not system.examples(PARTITION, OPERATION)
        print("A01, A02, B01, B02 and C01: the model answered; five proposals remain pending.")
        print("No person reviews individual answers. Cement has no learned function yet.")

        print("\n=== Act 2: learn the recurring cases and publish version 1 ===")
        first, build = learning_pass(system, run=1)
        assert len(first.input_hashes) == 2
        assert len(build.created) == 2
        assert len(build.blocked) == 1
        assert build.blocked[0]["support"] == 1
        print(
            "The scripted pass reads retained answers, groups their layouts and merges their plans."
        )
        print(
            "Reviewer: learning-pass. The pass sets the projection, "
            "compiles, verifies and promotes."
        )
        print(f"One compiled case: {build.created[0]}.")
        print("Version 1: two cases, for layouts A and B. Layout C has only one confirmation.")
        print("Gate reasons: " + "; ".join(build.blocked[0]["reasons"]))

        print("\n=== Act 3: a person switches the function on ===")
        fresh = _document("layout_a_progress_note_03.txt")
        assert fresh not in [_document(name) for name in names]
        off = system.resolve(PARTITION, OPERATION, fresh)
        assert system.switch(PARTITION, OPERATION).mode == "off"
        assert off.match is None or not off.match.matched
        print("The switch is still off. Even a learned layout goes to the model.")
        system.set_switch(PARTITION, OPERATION, mode="follow", actor="person")
        before = source.calls
        resolution = system.resolve(PARTITION, OPERATION, fresh)
        assert resolution.verification.passed
        assert resolution.match is not None and resolution.match.matched
        assert source.calls == before
        extracted = pipeline.apply_plan(resolution.match.output, fresh["document"])
        assert extracted["mrn"] == "MG-100913"
        print("Switch: follow. A03 has new patient values; the projection selects layout A's plan.")
        print("A03: adapter calls stayed flat.")
        print(f"A03 patient JSON: {json.dumps(extracted, sort_keys=True)}")

        print("\n=== Act 4: another lab slip lets the next pass add a case ===")
        c_second = _document("layout_c_lab_slip_02.txt")
        c_miss = system.resolve(PARTITION, OPERATION, c_second)
        assert c_miss.match is not None and not c_miss.match.matched
        c_proposal = system.propose(PARTITION, OPERATION, c_second)
        c_answer = system.proposal(PARTITION, c_proposal)["proposed_output"]
        assert pipeline.apply_plan(c_answer, c_second["document"])["mrn"] == "MG-200731"
        print("C02 misses version 1. The model answers and its plan joins the retained proposals.")
        second, build = learning_pass(system, run=2)
        assert len(second.input_hashes) == 3
        assert len(build.created) == 1 and not build.blocked
        diff = system.diff_versions(
            PARTITION, OPERATION, from_hash=first.function_hash, to_hash=second.function_hash
        )
        assert len(diff.added) == 1 and not diff.removed and not diff.changed
        assert not diff.projection_changed
        versions = system.function_versions(PARTITION, OPERATION)
        assert len(versions.versions) == 2
        assert versions.versions[0].selected
        print("Version 2: three cases. Difference from version 1: 1 added, 0 removed, 0 changed.")
        print("The switch follows version 2 without another person reviewing the answers.")

        print("\n=== Act 5: a person rolls back, then follows the newest version ===")
        system.set_switch(
            PARTITION, OPERATION, mode="pinned", function_hash=first.function_hash, actor="person"
        )
        c_first = _document("layout_c_lab_slip_01.txt")
        rollback = system.resolve(PARTITION, OPERATION, c_first)
        assert rollback.match is not None and not rollback.match.matched
        fallback = system.propose(PARTITION, OPERATION, c_first)
        fallback_plan = system.proposal(PARTITION, fallback)["proposed_output"]
        assert pipeline.apply_plan(fallback_plan, c_first["document"])["mrn"] == "MG-200164"
        print("Switch: pinned to version 1. Layout C misses; the model answers.")
        system.set_switch(PARTITION, OPERATION, mode="follow", actor="person")
        before = source.calls
        restored = system.resolve(PARTITION, OPERATION, c_first)
        assert restored.match is not None and restored.match.matched
        assert source.calls == before
        assert pipeline.apply_plan(restored.match.output, c_first["document"])["mrn"] == "MG-200164"
        print("Switch: follow. Version 2 answers layout C; adapter calls stay flat.")

        state, served = system.serving(
            PARTITION, OPERATION, expected_function_hash=second.function_hash
        )
        assert state.mode == "follow"
        assert served is not None and served.passed and served.document is not None
        function = served.document
        bundle_text = function.text
        print("\nExport the version that the switch selects before deleting the ledger.")
        print(f"Verified function hash: {function.function_hash}")
        print(
            f"Exported bundle: {len(bundle_text.encode('utf-8'))} bytes, including the projection."
        )
        _print_event_trace(system)

    assert not os.path.exists(temporary_directory)
    print("\n=== Act 6: version 2 answers raw input without a ledger ===")
    print("The temporary ledger and its audit trail are gone; only the bundle remains.")
    offline_hash, offline = resolve_offline(
        bundle_text, fresh["document"], expected_function_hash=function.function_hash
    )
    assert offline_hash == function.function_hash and offline.matched
    assert pipeline.apply_plan(offline.output, fresh["document"]) == extracted
    print("A03 offline: the bundle returns the same plan and patient JSON.")
    unknown = fresh["document"].replace("PHYSICIAN PROGRESS NOTE", "UNSEEN FOLLOW-UP NOTE")
    _, miss = resolve_offline(bundle_text, unknown, expected_function_hash=function.function_hash)
    assert not miss.matched and miss.output is None
    print("Unknown layout offline: the projection reports a miss, not a guessed plan.")
    print("All checks passed.")


if __name__ == "__main__":
    main()
