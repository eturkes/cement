"""Research sketch: fixed form grammar + full consumption, not production IR."""
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("hospital_pipeline", ROOT / "pipeline.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FORMS = {
    "PHYSICIAN PROGRESS NOTE": {
        "document_type": "physician_progress_note",
        "labels": ["Patient", "MRN", "Date", "Provider"],
        "sections": ["Subjective", "Objective", "Assessment", "Plan"],
    },
    "PATIENT INTAKE FORM": {
        "document_type": "patient_intake_form",
        "labels": ["Name", "Date of Birth", "Insurance ID", "Primary Complaint"],
        "sections": ["Allergies", "Current Medications"],
    },
    "LAB RESULT SLIP": {
        "document_type": "lab_result_slip",
        "labels": ["Patient", "MRN", "Collection Date", "Potassium", "Creatinine"],
        "sections": ["Interpretation"],
    },
}


def lines(text):
    if type(text) is not str:
        return None
    if any(
        (ord(c) < 32 and c not in "\t\r\n")
        or 0x7F <= ord(c) <= 0x9F
        or ord(c) in (0x2028, 0x2029)
        or 0xD800 <= ord(c) <= 0xDFFF
        for c in text
    ):
        return None
    result = []
    pending_blank = False
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.rstrip(" \t")
        if not line:
            pending_blank = bool(result)
        else:
            if pending_blank:
                result.append("")
                pending_blank = False
            result.append(line)
    return result


def field(line, expected, empty=False):
    key, sep, value = line.partition(":")
    return bool(sep) and key.strip(" \t") == expected and (
        not empty or not value.strip(" \t")
    )


def project(text):
    normalized = lines(text)
    if not normalized:
        return None
    form = FORMS.get(normalized[0])
    if form is None:
        return None
    cursor = 1
    structure = []
    for label in form["labels"]:
        if cursor >= len(normalized) or not field(normalized[cursor], label):
            return None
        structure.append({"kind": "label", "key": label})
        cursor += 1
    for heading in form["sections"]:
        if cursor >= len(normalized) or normalized[cursor] != "":
            return None
        cursor += 1
        if cursor >= len(normalized) or not field(normalized[cursor], heading, empty=True):
            return None
        structure.append({"kind": "section", "key": heading})
        cursor += 1
        start = cursor
        while cursor < len(normalized) and normalized[cursor]:
            # Conservative initial profile; colon-bearing body text falls back.
            if ":" in normalized[cursor]:
                return None
            cursor += 1
        if cursor == start:
            return None
    if cursor != len(normalized):
        return None
    return {"document_type": form["document_type"], "structure": structure}


def must(condition, label):
    if not condition:
        raise RuntimeError(label)


corpus = {}
for path in sorted((ROOT / "documents").glob("*.txt")):
    raw = path.read_bytes().decode("utf-8")
    actual = project(raw)
    expected = module.layout_signature(raw)
    must(actual == expected, path.name)
    corpus[path.name] = actual
base = (ROOT / "documents/layout_a_progress_note_01.txt").read_text(encoding="utf-8")
expected = module.layout_signature(base)
positives = {
    "CRLF": base.replace("\n", "\r\n"),
    "CR": base.replace("\n", "\r"),
    "blank_runs": "\n\n" + base.replace("\n\n", "\n\n\n") + "\n\n",
    "ASCII_trailing_space_tab": "\n".join(x + " \t" for x in base.split("\n")),
    "label_edge_space": base.replace("Patient:", " Patient \t:"),
    "patient_value": base.replace("Jane Doe", "Another Patient"),
    "value_colon": base.replace("Jane Doe", "Name: with colon"),
    "opaque_body_extension": base.replace("Viral upper respiratory infection.", "Viral upper respiratory infection.\nNew body line."),
}
negatives = {
    "empty": "",
    "wrong_type": {},
    "unrecognized_header_line": base.replace("MRN:", "broken header\nMRN:"),
    "unrecognized_block": base + "\n\nnot a heading\n",
    "extra_label": base.replace("MRN:", "Extra: value\nMRN:"),
    "duplicate_label": base.replace("MRN:", "Patient: second\nMRN:"),
    "missing_label": base.replace("Provider: Dr. Elena Ramirez\n", ""),
    "reordered_labels": base.replace("Patient: Jane Doe\nMRN: MG-100241", "MRN: MG-100241\nPatient: Jane Doe"),
    "new_title": base.replace("PHYSICIAN PROGRESS NOTE", "PHYSICIAN PROGRESS REPORT"),
    "title_case": base.replace("PHYSICIAN PROGRESS NOTE", "Physician Progress Note"),
    "title_NBSP": base.replace("PHYSICIAN PROGRESS NOTE", "PHYSICIAN PROGRESS NOTE"),
    "title_BOM": "﻿" + base,
    "label_zero_width": base.replace("Patient:", "Patient​:"),
    "label_full_width_colon": base.replace("Patient:", "Patient："),
    "line_separator": base.replace("\n", " "),
    "missing_body": base.replace("Viral upper respiratory infection.\n", ""),
    "structural_injection_in_body": base.replace("Viral upper respiratory infection.", "Viral upper respiratory infection.\nExtra: heading"),
}
for name, raw in positives.items():
    must(project(raw) == expected, "positive:" + name)
for name, raw in negatives.items():
    must(project(raw) is None, "negative:" + name)
legacy = {
    "extra_body_colon_same_key": module.layout_signature(negatives["structural_injection_in_body"]) == expected,
    "title_case_same_key": module.layout_signature(negatives["title_case"]) == expected,
}
print(json.dumps({
    "corpus_matched": len(corpus),
    "corpus": corpus,
    "positive_probes_passed": list(positives),
    "negative_probes_passed": list(negatives),
    "legacy_observations": legacy,
}, ensure_ascii=True, sort_keys=True))
