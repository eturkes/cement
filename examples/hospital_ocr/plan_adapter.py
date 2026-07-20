"""Deterministic in-process plan proposer for the hospital OCR example.

This stub is deliberately not an LLM. It proposes reviewable extraction plans;
cement can return a confirmed plan exactly for a known layout, but it does not
guarantee that the plan extracts every future document correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import cast

from cement_runtime import Candidate, CandidateRequest

import pipeline


class PlanProposer:
    """Propose a deterministic extraction plan for a layout signature."""

    def __init__(self, source_id: str = "hospital-ocr-plan-stub") -> None:
        self._source_id = source_id

    def propose(self, request: CandidateRequest) -> Candidate:
        signature = request.input
        if type(signature) is not dict:
            raise TypeError("layout signature must be a JSON object")

        document_type = signature.get("document_type")
        if type(document_type) is not str or not document_type:
            raise ValueError("layout signature document_type must be a non-empty string")

        reference = pipeline.reference_plan(document_type)
        if reference is not None:
            output = json.loads(json.dumps(reference))
            strategy = "reference_plan"
        else:
            raw_labels = signature.get("labels")
            raw_sections = signature.get("sections")
            if type(raw_labels) is not list or any(
                type(label) is not str or not label for label in raw_labels
            ):
                raise ValueError("layout signature labels must be non-empty strings")
            if type(raw_sections) is not list or any(
                type(heading) is not str or not heading for heading in raw_sections
            ):
                raise ValueError("layout signature sections must be non-empty strings")

            labels = cast(list[str], raw_labels)
            sections = cast(list[str], raw_sections)
            fields: list[pipeline.JSONValue] = []
            for label in labels:
                fields.append(
                    {
                        "name": _field_name(label),
                        "locator": {"kind": "label", "label": label},
                        "value_type": "string",
                    }
                )
            for heading in sections:
                fields.append(
                    {
                        "name": _field_name(heading),
                        "locator": {"kind": "section", "heading": heading},
                        "value_type": "text",
                    }
                )
            output = {
                "document_type": document_type,
                "layout": "unknown",
                "fields": fields,
            }
            strategy = "best_effort"

        return Candidate(
            output=output,
            provenance={
                "source_id": self._source_id,
                "strategy": strategy,
                "document_type": document_type,
                "deliberately_not_an_llm": True,
            },
        )


def _field_name(value: str) -> str:
    """Return a stable snake_case field name for a visible OCR key."""

    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "field"


def _self_check() -> None:
    documents = Path(__file__).with_name("documents")
    proposer = PlanProposer()
    checked_documents = 0

    for path in sorted(documents.glob("*.txt")):
        ocr_text = pipeline.ocr(path)
        signature = pipeline.layout_signature(ocr_text)
        assert type(signature) is dict
        document_type = signature["document_type"]
        assert type(document_type) is str

        request = CandidateRequest(
            partition="mercy-general",
            operation="document.extraction_plan",
            operation_revision=1,
            request_id=f"self-check-{path.stem}",
            input=signature,
        )
        candidate = proposer.propose(request)
        reference = pipeline.reference_plan(document_type)
        assert reference is not None
        assert candidate.output == reference
        assert candidate.output is not reference
        assert pipeline._is_cement_json_value(candidate.output)
        assert pipeline._is_cement_json_value(candidate.provenance)
        assert candidate.provenance == {
            "source_id": "hospital-ocr-plan-stub",
            "strategy": "reference_plan",
            "document_type": document_type,
            "deliberately_not_an_llm": True,
        }

        candidate_plan = cast(pipeline.JSONValue, candidate.output)
        extracted = pipeline.apply_plan(candidate_plan, ocr_text)
        for name, expected in pipeline._EXPECTED_FIELDS[path.name].items():
            assert extracted[name] == expected
        checked_documents += 1

    unknown_path = documents / "layout_a_progress_note_01.txt"
    unknown_ocr = pipeline.ocr(unknown_path)
    unknown_signature = pipeline.layout_signature(unknown_ocr)
    assert type(unknown_signature) is dict
    unknown_signature["document_type"] = "unknown_progress_note"
    unknown_candidate = proposer.propose(
        CandidateRequest(
            partition="mercy-general",
            operation="document.extraction_plan",
            operation_revision=1,
            request_id="self-check-unknown-layout",
            input=unknown_signature,
        )
    )
    assert pipeline._is_cement_json_value(unknown_candidate.output)
    assert pipeline._is_cement_json_value(unknown_candidate.provenance)
    assert unknown_candidate.provenance["strategy"] == "best_effort"
    unknown_plan = cast(pipeline.JSONValue, unknown_candidate.output)
    unknown_extracted = pipeline.apply_plan(unknown_plan, unknown_ocr)
    assert unknown_extracted
    assert "Jane Doe" in unknown_extracted.values()

    print(
        "Hospital OCR plan adapter self-check passed: "
        f"{checked_documents} reference-plan proposals, 1 best-effort proposal."
    )


if __name__ == "__main__":
    _self_check()
