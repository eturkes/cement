"""Deterministic OCR-to-JSON core for the synthetic hospital corpus.

The pipeline builds patient-independent signatures for exact document layouts and
applies reviewed reference plans to full OCR text. In the complete example, cement
can return a plan deterministically for a known signature, but it does not generalize
across layouts or guarantee that a plan extracts every future document correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import TypeAlias

JSONValue: TypeAlias = None | bool | int | str | list["JSONValue"] | dict[str, "JSONValue"]

MIN_INTEGER = -(2**63)
MAX_INTEGER = 2**63 - 1

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

_EXPECTED_FIELDS = {
    "layout_a_progress_note_01.txt": {
        "patient_name": "Jane Doe",
        "mrn": "MG-100241",
        "assessment": "Viral upper respiratory infection.",
    },
    "layout_a_progress_note_02.txt": {
        "patient_name": "Marcus Lee",
        "mrn": "MG-100587",
        "assessment": "Overuse-related right knee pain.",
    },
    "layout_a_progress_note_03.txt": {
        "patient_name": "Sofia Patel",
        "mrn": "MG-100913",
        "assessment": "Tension-type headaches, improving.",
    },
    "layout_b_intake_form_01.txt": {
        "patient_name": "Amelia Brooks",
        "insurance_id": "HZN-774201",
        "allergies": "Penicillin",
    },
    "layout_b_intake_form_02.txt": {
        "patient_name": "Noah Williams",
        "insurance_id": "HZN-889416",
        "allergies": "Latex",
    },
    "layout_c_lab_slip_01.txt": {
        "patient_name": "Luis Ortega",
        "potassium": "4.2",
        "creatinine": "0.9",
    },
    "layout_c_lab_slip_02.txt": {
        "patient_name": "Priya Nair",
        "potassium": "3.8",
        "creatinine": "1.1",
    },
}

_PATIENT_VALUE_SENTINELS = {
    "layout_a_progress_note_01.txt": ("Jane Doe", "MG-100241"),
    "layout_a_progress_note_02.txt": ("Marcus Lee", "MG-100587"),
    "layout_a_progress_note_03.txt": ("Sofia Patel", "MG-100913"),
    "layout_b_intake_form_01.txt": ("Amelia Brooks", "HZN-774201"),
    "layout_b_intake_form_02.txt": ("Noah Williams", "HZN-889416"),
    "layout_c_lab_slip_01.txt": ("Luis Ortega", "4.2", "0.9"),
    "layout_c_lab_slip_02.txt": ("Priya Nair", "3.8", "1.1"),
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


def layout_signature(ocr_text: str) -> JSONValue:
    """Return the exact layout structure while excluding all patient values."""

    normalized = _normalize_ocr_text(ocr_text)
    if not normalized:
        raise ValueError("OCR text is empty")

    lines = normalized.split("\n")
    labels: list[JSONValue] = []
    sections: list[JSONValue] = []
    for line in lines[1:]:
        keyed = _keyed_line(line)
        if keyed is None:
            continue
        key, value = keyed
        if value:
            labels.append(key)
        else:
            sections.append(key)

    return {
        "document_type": _document_type(lines[0]),
        "labels": labels,
        "sections": sections,
    }


def reference_plan(document_type: str) -> JSONValue | None:
    """Return the reviewed reference plan for an exact known document type."""

    return REFERENCE_PLANS.get(document_type)


def _label_value(lines: list[str], label: str) -> str:
    for line in lines:
        keyed = _keyed_line(line)
        if keyed is not None and keyed[0] == label and keyed[1]:
            return keyed[1]
    raise ValueError(f"label not found in OCR text: {label!r}")


def _section_value(lines: list[str], heading: str) -> str:
    for index, line in enumerate(lines):
        keyed = _keyed_line(line)
        if keyed != (heading, ""):
            continue

        body: list[str] = []
        for candidate in lines[index + 1 :]:
            candidate_keyed = _keyed_line(candidate)
            if candidate_keyed is not None and not candidate_keyed[1]:
                break
            body.append(candidate)
        return "\n".join(body).strip()
    raise ValueError(f"section not found in OCR text: {heading!r}")


def apply_plan(plan: JSONValue, ocr_text: str) -> dict[str, JSONValue]:
    """Apply label and section locators, returning raw extracted strings."""

    if type(plan) is not dict:
        raise TypeError("extraction plan must be a JSON object")
    fields = plan.get("fields")
    if type(fields) is not list:
        raise ValueError("extraction plan fields must be a JSON array")

    lines = _normalize_ocr_text(ocr_text).split("\n")
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
            result[name] = _label_value(lines, label)
        elif kind == "section":
            heading = locator.get("heading")
            if type(heading) is not str or not heading:
                raise ValueError(f"field {name!r} has an invalid section locator")
            result[name] = _section_value(lines, heading)
        else:
            raise ValueError(f"field {name!r} has unsupported locator kind {kind!r}")
    return result


def _is_cement_json_value(value: object) -> bool:
    """Check the local cement-json-v1 value boundary recursively."""

    if value is None or type(value) is bool or type(value) is str:
        return True
    if type(value) is int:
        return MIN_INTEGER <= value <= MAX_INTEGER
    if type(value) is list:
        return all(_is_cement_json_value(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _is_cement_json_value(item)
            for key, item in value.items()
        )
    return False


def _self_check() -> None:
    documents = Path(__file__).with_name("documents")
    groups = {
        "A": sorted(documents.glob("layout_a_*.txt")),
        "B": sorted(documents.glob("layout_b_*.txt")),
        "C": sorted(documents.glob("layout_c_*.txt")),
    }
    assert {layout: len(paths) for layout, paths in groups.items()} == {
        "A": 3,
        "B": 2,
        "C": 2,
    }
    assert all(_is_cement_json_value(plan) for plan in REFERENCE_PLANS.values())

    signatures_by_layout: dict[str, bytes] = {}
    checked_documents = 0
    for layout, paths in groups.items():
        serialized_signatures: set[bytes] = set()
        for path in paths:
            ocr_text = ocr(path)
            assert _normalize_ocr_text(ocr_text) == ocr_text

            signature = layout_signature(ocr_text)
            assert _is_cement_json_value(signature)
            serialized = json.dumps(signature, sort_keys=True).encode("utf-8")
            serialized_signatures.add(serialized)
            for patient_value in _PATIENT_VALUE_SENTINELS[path.name]:
                assert patient_value.encode("utf-8") not in serialized

            assert type(signature) is dict
            document_type = signature.get("document_type")
            assert type(document_type) is str
            plan = reference_plan(document_type)
            assert plan is not None
            extracted = apply_plan(plan, ocr_text)
            assert _is_cement_json_value(extracted)
            assert all(type(value) is str for value in extracted.values())
            assert all(not isinstance(value, float) for value in extracted.values())
            for field_name, expected in _EXPECTED_FIELDS[path.name].items():
                assert extracted[field_name] == expected
            checked_documents += 1

        assert len(serialized_signatures) == 1
        signatures_by_layout[layout] = next(iter(serialized_signatures))

    assert len(set(signatures_by_layout.values())) == 3
    assert not _is_cement_json_value({"nested": [float("4.2")]})
    print(
        "Hospital OCR self-check passed: "
        f"{checked_documents} documents, 3 stable distinct layout signatures, "
        "string-only plan outputs, cement-json-v1 valid."
    )


if __name__ == "__main__":
    _self_check()
