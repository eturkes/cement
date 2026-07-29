"""Deterministic in-process plan proposer for the hospital OCR example.

This stub is deliberately not an LLM. It proposes reviewable extraction plans;
cement can return a confirmed plan exactly for a known layout, but it does not
guarantee that the plan extracts every future document correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

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
        if type(document_type) is not str or not document_type.strip():
            raise ValueError("layout signature document_type must be a non-empty string")

        structure = signature.get("structure")
        if type(structure) is not list:
            raise ValueError("layout signature structure must be a JSON array")

        fields: list[pipeline.JSONValue] = []
        locator_counts: dict[tuple[str, str], int] = {}
        used_field_names: set[str] = set()
        for entry in structure:
            if type(entry) is not dict or any(
                type(entry_key) is not str for entry_key in entry
            ):
                raise ValueError(
                    "layout signature structure entries must be string-keyed objects"
                )
            kind = entry.get("kind")
            if type(kind) is not str or not kind.strip():
                raise ValueError(
                    "layout signature structure entry kind must be a non-empty string"
                )
            key = entry.get("key")
            if type(key) is not str or not key.strip():
                raise ValueError(
                    "layout signature structure entry key must be a non-empty string"
                )

            locator: pipeline.JSONValue
            if kind == "label":
                locator = {"kind": "label", "label": key}
                value_type = "string"
            elif kind == "section":
                locator = {"kind": "section", "heading": key}
                value_type = "text"
            else:
                raise ValueError(
                    f"layout signature structure entry has unsupported kind {kind!r}"
                )

            locator_key = (kind, key)
            locator_counts[locator_key] = locator_counts.get(locator_key, 0) + 1
            base_name = _field_name(key)
            field_name = base_name
            suffix = 2
            while field_name in used_field_names:
                field_name = f"{base_name}_{suffix}"
                suffix += 1
            used_field_names.add(field_name)
            field: pipeline.JSONValue = {
                "name": field_name,
                "locator": locator,
                "value_type": value_type,
            }
            fields.append(field)

        reference = pipeline.reference_plan(document_type)
        if reference is not None and _reference_plan_resolves_structure(
            reference, locator_counts
        ):
            output = json.loads(json.dumps(reference))
            strategy = "reference_plan"
        else:
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


def _reference_plan_resolves_structure(
    plan: pipeline.JSONValue,
    locator_counts: dict[tuple[str, str], int],
) -> bool:
    """Return whether every reference locator resolves exactly once."""

    if type(plan) is not dict:
        return False
    fields = plan.get("fields")
    if type(fields) is not list:
        return False
    for field in fields:
        if type(field) is not dict:
            return False
        locator = field.get("locator")
        if type(locator) is not dict:
            return False
        kind = locator.get("kind")
        if type(kind) is not str:
            return False
        if kind == "label":
            key = locator.get("label")
        elif kind == "section":
            key = locator.get("heading")
        else:
            return False
        if type(key) is not str:
            return False
        if locator_counts.get((kind, key), 0) != 1:
            return False
    return True

def _field_name(value: str) -> str:
    """Return a stable snake_case field name for a visible OCR key."""

    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "field"


def _self_check() -> None:
    proposer = PlanProposer()
    document = Path(__file__).with_name("documents") / "layout_a_progress_note_01.txt"
    signature = pipeline.layout_signature(pipeline.ocr(document))
    known = proposer.propose(
        CandidateRequest(
            partition="mercy-general",
            operation="document.extraction_plan",
            operation_revision=1,
            request_id="self-check-known-layout",
            input=signature,
        )
    )
    reference = pipeline.reference_plan("physician_progress_note")
    assert reference is not None
    assert known.output == reference
    assert known.output is not reference

    unknown = proposer.propose(
        CandidateRequest(
            partition="mercy-general",
            operation="document.extraction_plan",
            operation_revision=1,
            request_id="self-check-unknown-layout",
            input={
                "document_type": "unknown_note",
                "structure": [
                    {"kind": "section", "key": "Summary"},
                    {"kind": "label", "key": "Signer"},
                ],
            },
        )
    )
    assert unknown.output == {
        "document_type": "unknown_note",
        "layout": "unknown",
        "fields": [
            {
                "name": "summary",
                "locator": {"kind": "section", "heading": "Summary"},
                "value_type": "text",
            },
            {
                "name": "signer",
                "locator": {"kind": "label", "label": "Signer"},
                "value_type": "string",
            },
        ],
    }
    assert unknown.provenance["strategy"] == "best_effort"
    print("Hospital OCR plan adapter smoke check passed.")


if __name__ == "__main__":
    _self_check()
