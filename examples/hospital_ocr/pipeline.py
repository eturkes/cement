"""Deterministic OCR-to-JSON core for the synthetic hospital corpus.

The pipeline builds patient-independent signatures for exact document layouts and
applies reviewed reference plans to full OCR text. In the complete example, cement
can return a plan deterministically for a known signature, but it does not generalize
across layouts or guarantee that a plan extracts every future document correctly.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import TypeAlias

JSONValue: TypeAlias = None | bool | int | str | list["JSONValue"] | dict[str, "JSONValue"]
_ParsedEntry: TypeAlias = tuple[str, str, str]

REFERENCE_PLANS: dict[str, JSONValue] = {
    "physician_progress_note": {
        "document_type": "physician_progress_note",
        "layout": "A",
        "fields": [
            {
                "name": "patient_name",
                "locator": {"kind": "label", "label": "Patient"},
                "value_type": "string",
            },
            {
                "name": "mrn",
                "locator": {"kind": "label", "label": "MRN"},
                "value_type": "string",
            },
            {
                "name": "encounter_date",
                "locator": {"kind": "label", "label": "Date"},
                "value_type": "string",
            },
            {
                "name": "provider",
                "locator": {"kind": "label", "label": "Provider"},
                "value_type": "string",
            },
            {
                "name": "assessment",
                "locator": {"kind": "section", "heading": "Assessment"},
                "value_type": "text",
            },
        ],
    },
    "patient_intake_form": {
        "document_type": "patient_intake_form",
        "layout": "B",
        "fields": [
            {
                "name": "patient_name",
                "locator": {"kind": "label", "label": "Name"},
                "value_type": "string",
            },
            {
                "name": "date_of_birth",
                "locator": {"kind": "label", "label": "Date of Birth"},
                "value_type": "string",
            },
            {
                "name": "insurance_id",
                "locator": {"kind": "label", "label": "Insurance ID"},
                "value_type": "string",
            },
            {
                "name": "primary_complaint",
                "locator": {"kind": "label", "label": "Primary Complaint"},
                "value_type": "string",
            },
            {
                "name": "allergies",
                "locator": {"kind": "section", "heading": "Allergies"},
                "value_type": "text",
            },
            {
                "name": "current_medications",
                "locator": {"kind": "section", "heading": "Current Medications"},
                "value_type": "text",
            },
        ],
    },
    "lab_result_slip": {
        "document_type": "lab_result_slip",
        "layout": "C",
        "fields": [
            {
                "name": "patient_name",
                "locator": {"kind": "label", "label": "Patient"},
                "value_type": "string",
            },
            {
                "name": "mrn",
                "locator": {"kind": "label", "label": "MRN"},
                "value_type": "string",
            },
            {
                "name": "collection_date",
                "locator": {"kind": "label", "label": "Collection Date"},
                "value_type": "string",
            },
            {
                "name": "potassium",
                "locator": {"kind": "label", "label": "Potassium"},
                "value_type": "decimal_string",
            },
            {
                "name": "creatinine",
                "locator": {"kind": "label", "label": "Creatinine"},
                "value_type": "decimal_string",
            },
            {
                "name": "interpretation",
                "locator": {"kind": "section", "heading": "Interpretation"},
                "value_type": "text",
            },
        ],
    },
}

def _normalize_ocr_text(text: str) -> str:
    """Normalize line endings and blank lines without changing internal spaces."""

    if type(text) is not str:
        raise TypeError("OCR input must be text")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized: list[str] = []
    pending_blank = False
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            if normalized:
                pending_blank = True
            continue
        if pending_blank:
            normalized.append("")
            pending_blank = False
        normalized.append(line)
    return "\n".join(normalized)


def ocr(path: str | Path) -> str:
    """Read a simulated OCR document and apply idempotent whitespace cleanup."""

    source = Path(path).read_bytes().decode("utf-8")
    return _normalize_ocr_text(source)


def _keyed_line(line: str) -> tuple[str, str] | None:
    """Return a stripped key and value for a colon-delimited structural line."""

    key, separator, value = line.partition(":")
    key = key.strip()
    if not separator or not key:
        return None
    return key, value.strip()


def _document_type(title: str) -> str:
    """Map a constant document title to a stable snake_case identifier."""

    result = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    if not result:
        raise ValueError("document title does not contain an identifier")
    return result


def _parse_layout(ocr_text: str) -> tuple[str, list[_ParsedEntry]]:
    """Parse one recognized OCR layout into ordered extraction entries."""

    normalized = _normalize_ocr_text(ocr_text)
    if not normalized:
        raise ValueError("OCR text is empty")

    blocks = normalized.split("\n\n")
    title_and_header = blocks[0].split("\n")
    entries: list[_ParsedEntry] = []
    for line in title_and_header[1:]:
        keyed = _keyed_line(line)
        if keyed is None:
            raise ValueError(f"unrecognized OCR layout line: {line!r}")
        key, value = keyed
        entries.append(("label", key, value))

    for block in blocks[1:]:
        lines = block.split("\n")
        leader = _keyed_line(lines[0])
        if leader is None:
            raise ValueError(f"unrecognized OCR layout line: {lines[0]!r}")
        key, value = leader
        if not value:
            entries.append(("section", key, "\n".join(lines[1:])))
            continue

        for line in lines:
            keyed = _keyed_line(line)
            if keyed is None:
                raise ValueError(f"unrecognized OCR layout line: {line!r}")
            key, value = keyed
            entries.append(("label", key, value))

    return _document_type(title_and_header[0]), entries


def layout_signature(ocr_text: str) -> JSONValue:
    """Return the exact layout structure while excluding all patient values."""

    document_type, entries = _parse_layout(ocr_text)
    return {
        "document_type": document_type,
        "structure": [
            {"kind": kind, "key": key}
            for kind, key, _ in entries
        ],
    }


def reference_plan(document_type: str) -> JSONValue | None:
    """Return the reviewed reference plan for an exact known document type."""

    return REFERENCE_PLANS.get(document_type)


def _label_value(entries: list[_ParsedEntry], label: str) -> str:
    matches = [
        value
        for kind, key, value in entries
        if kind == "label" and key == label
    ]
    if not matches:
        raise ValueError(f"label not found in OCR text: {label!r}")
    if len(matches) > 1:
        raise ValueError(f"label is ambiguous in OCR text: {label!r}")
    return matches[0]


def _section_value(entries: list[_ParsedEntry], heading: str) -> str:
    matches = [
        value
        for kind, key, value in entries
        if kind == "section" and key == heading
    ]
    if not matches:
        raise ValueError(f"section not found in OCR text: {heading!r}")
    if len(matches) > 1:
        raise ValueError(f"section is ambiguous in OCR text: {heading!r}")
    return matches[0]


def apply_plan(plan: JSONValue, ocr_text: str) -> dict[str, JSONValue]:
    """Apply label and section locators, returning raw extracted strings."""

    if type(plan) is not dict:
        raise TypeError("extraction plan must be a JSON object")
    fields = plan.get("fields")
    if type(fields) is not list:
        raise ValueError("extraction plan fields must be a JSON array")

    _, entries = _parse_layout(ocr_text)
    result: dict[str, JSONValue] = {}
    for field in fields:
        if type(field) is not dict:
            raise ValueError("each extraction field must be a JSON object")
        name = field.get("name")
        locator = field.get("locator")
        if type(name) is not str or not name:
            raise ValueError("extraction field name must be a non-empty string")
        if name in result:
            raise ValueError(f"duplicate extraction field name: {name!r}")
        if type(locator) is not dict:
            raise ValueError(f"field {name!r} must have a locator object")

        kind = locator.get("kind")
        if kind == "label":
            label = locator.get("label")
            if type(label) is not str or not label:
                raise ValueError(f"field {name!r} has an invalid label locator")
            result[name] = _label_value(entries, label)
        elif kind == "section":
            heading = locator.get("heading")
            if type(heading) is not str or not heading:
                raise ValueError(f"field {name!r} has an invalid section locator")
            result[name] = _section_value(entries, heading)
        else:
            raise ValueError(f"field {name!r} has unsupported locator kind {kind!r}")
    return result



def _self_check() -> None:
    document = Path(__file__).with_name("documents") / "layout_a_progress_note_01.txt"
    ocr_text = ocr(document)
    signature = layout_signature(ocr_text)
    assert signature == {
        "document_type": "physician_progress_note",
        "structure": [
            {"kind": "label", "key": "Patient"},
            {"kind": "label", "key": "MRN"},
            {"kind": "label", "key": "Date"},
            {"kind": "label", "key": "Provider"},
            {"kind": "section", "key": "Subjective"},
            {"kind": "section", "key": "Objective"},
            {"kind": "section", "key": "Assessment"},
            {"kind": "section", "key": "Plan"},
        ],
    }
    plan = reference_plan("physician_progress_note")
    assert plan is not None
    extracted = apply_plan(plan, ocr_text)
    assert extracted["mrn"] == "MG-100241"
    assert extracted["assessment"] == "Viral upper respiratory infection."
    print("Hospital OCR pipeline smoke check passed.")


if __name__ == "__main__":
    _self_check()
