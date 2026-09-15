"""Session backend for the Cement web UI demo.

The session drives the shipped ``cement_runtime`` over one temporary SQLite ledger.
Only the provider is simulated: ``StubProvider`` samples a plan variant and a latency
instead of calling a model, so every artifact, digest, check, receipt and resolve
timing the page shows comes from the real system.

The demo enters the pipeline at ``submit_proposal``, the explicit-candidate seam.

Two seams, deliberately split. The operator's lifecycle runs as REAL ``cement``
subprocesses against this ledger, because the shipped control plane is a CLI and the
page must not read as a web console. Chat-side submit and resolve stay in-process:
a subprocess costs a flat ~105 ms of interpreter startup against a 0.9-4 ms resolve,
so routing the chat through it would report startup cost as the function's cost.
"""

from __future__ import annotations

from collections.abc import Callable
import copy
import hashlib
import json
from pathlib import Path
import random
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

from cement_runtime import (
    Candidate,
    CementError,
    CompilePolicy,
    System,
    evaluate,
    parse_function,
)
from cement_runtime.json_value import canonicalize


def _repo_root(start: Path) -> Path:
    """Find the checkout root by the marker file, not by a parent count."""

    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml above {start}")


ROOT = _repo_root(Path(__file__).resolve())
EXAMPLE_DIR = ROOT / "examples" / "hospital_ocr"
DOCUMENTS_DIR = EXAMPLE_DIR / "documents"

# The example owns the OCR corpus and the deterministic signature/extraction core.
# The prototype borrows both rather than forking a second copy that can drift.
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))
import pipeline  # noqa: E402

PARTITION = "example-hospital"
REVIEWER = "records-supervisor"
PROMOTER = "informatics-lead"
DEMO_POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
POLICY_VIEW = {
    "min_confirmations": 2,
    "min_reviewers": 1,
    "min_span_seconds": 0,
    "production_default": "3 confirmations, 2 reviewers, a 7-day span",
}
PROVIDER_NAME = "acme-health/clinical-llm-4"
LATENCY_RANGE = (1.1, 3.4)

def _display(arguments: tuple[str, ...]) -> str:
    """The short form the page prints, runnable as spelled after the preamble.

    A JSON payload passed to `--output` or `--input` runs to hundreds of characters
    and buries the command it belongs to, so it prints as the shell variable a person
    would use. The expansion beside it carries the exact argv that ran. The bound
    clears a 64-character digest, because repeating that digest IS the point of
    `function promote`.
    """

    parts: list[str] = []
    previous = ""
    for argument in arguments:
        if len(argument) > 80 and previous.startswith("--"):
            parts.append('"$' + previous.lstrip("-").upper().replace("-", "_") + '"')
        else:
            parts.append(shlex.quote(argument))
        previous = argument
    return "cement " + " ".join(parts)


def _cement_entry_point() -> Path:
    """The console script beside the running interpreter, so subprocesses run this
    checkout. ``sys.executable`` stays unresolved on purpose: `.venv/bin/python` is a
    symlink into the uv-managed toolchain, and resolving it leaves the venv."""

    beside = Path(sys.executable).parent / "cement"
    return beside if beside.is_file() else ROOT / ".venv" / "bin" / "cement"


CEMENT = _cement_entry_point()

JSONValue = Any


def _canonical_bytes(value: JSONValue) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: JSONValue) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


# --- tasks -------------------------------------------------------------------

# `keyed_on` is a reason, not a label: it names what the canonical input carries.
# Four operations are decided by the LAYOUT, so their scopes repeat and they cement.
# The fifth is decided by the note's own words, which no second visit repeats, so its
# scopes never reach a second confirmation and the compiler blocks it forever.
OPERATIONS: dict[str, dict[str, str]] = {
    "document.extraction_plan": {
        "label": "extraction plan",
        "decides": "where each record field sits in this layout",
        "keyed_on": "layout",
    },
    "document.phi_locators": {
        "label": "identifier map",
        "decides": "which of those fields carry patient identifiers",
        "keyed_on": "layout",
    },
    "document.required_fields": {
        "label": "required fields",
        "decides": "which fields this form must have filled in",
        "keyed_on": "layout",
    },
    "document.intake_queue": {
        "label": "intake queue",
        "decides": "which team owns this kind of document",
        "keyed_on": "layout",
    },
    "document.billing_codes": {
        "label": "billing codes",
        "decides": "which ICD-10 codes the assessment text supports",
        "keyed_on": "text",
    },
}

# One task the staff recognize, one or more operations under it. The extraction plan
# serves four of the five, which is why a function promoted for one task answers the
# next one for free.
SCENARIOS: list[dict[str, JSONValue]] = [
    {
        "id": "file",
        "title": "File it into the record",
        "intent": "extract the record fields",
        "operations": ["document.extraction_plan"],
    },
    {
        "id": "share",
        "title": "Send it to an outside specialist",
        "intent": "de-identify the document",
        "operations": ["document.extraction_plan", "document.phi_locators"],
    },
    {
        "id": "check",
        "title": "Check the form before I accept it",
        "intent": "find blank required fields",
        "operations": ["document.extraction_plan", "document.required_fields"],
    },
    {
        "id": "route",
        "title": "Where does this go?",
        "intent": "name the owning team",
        "operations": ["document.intake_queue"],
    },
    {
        "id": "bill",
        "title": "Code it for billing",
        "intent": "suggest billing codes",
        "operations": ["document.extraction_plan", "document.billing_codes"],
    },
]

# One row per tray card: the wording a person types, and the document it arrives with.
# Wordings inside a task vary on purpose. The model maps every one of them to the same
# task, and Cement never sees the wording at all.
REQUESTS: list[dict[str, str]] = [
    {"id": "q01", "scenario": "file", "document_id": "A01",
     "ask": "Extract the record fields as JSON."},
    {"id": "q02", "scenario": "file", "document_id": "A02",
     "ask": "Give me the JSON for the record fields."},
    {"id": "q03", "scenario": "file", "document_id": "A03",
     "ask": "Same as the others - pull the fields into JSON."},
    {"id": "q04", "scenario": "file", "document_id": "C01",
     "ask": "Can you get the fields out of this one as JSON?"},
    {"id": "q05", "scenario": "share", "document_id": "A01",
     "ask": "Remove the patient identifiers before I forward this."},
    {"id": "q06", "scenario": "share", "document_id": "A02",
     "ask": "De-identify this note for me."},
    {"id": "q07", "scenario": "share", "document_id": "B01",
     "ask": "Strip the PHI out of this one so I can share it."},
    {"id": "q08", "scenario": "check", "document_id": "B03",
     "ask": "Is anything missing from this form?"},
    {"id": "q09", "scenario": "check", "document_id": "B01",
     "ask": "Did they leave any blanks?"},
    {"id": "q10", "scenario": "route", "document_id": "C01",
     "ask": "Which team should pick this up?"},
    {"id": "q11", "scenario": "route", "document_id": "C02",
     "ask": "Who handles this one?"},
    {"id": "q12", "scenario": "bill", "document_id": "A01",
     "ask": "What should we bill for this visit?"},
    {"id": "q13", "scenario": "bill", "document_id": "A02",
     "ask": "What codes does this one support?"},
]

IDENTIFIERS: dict[str, list[dict[str, str]]] = {
    "physician_progress_note": [
        {"field": "patient_name", "category": "name"},
        {"field": "mrn", "category": "medical_record_number"},
        {"field": "encounter_date", "category": "date"},
    ],
    "patient_intake_form": [
        {"field": "patient_name", "category": "name"},
        {"field": "date_of_birth", "category": "date"},
        {"field": "insurance_id", "category": "member_id"},
    ],
    "lab_result_slip": [
        {"field": "patient_name", "category": "name"},
        {"field": "mrn", "category": "medical_record_number"},
        {"field": "collection_date", "category": "date"},
    ],
}

REQUIRED_FIELDS: dict[str, list[str]] = {
    "physician_progress_note": [
        "patient_name", "mrn", "encounter_date", "provider", "assessment",
    ],
    "patient_intake_form": [
        "patient_name", "date_of_birth", "insurance_id", "primary_complaint",
    ],
    "lab_result_slip": [
        "patient_name", "mrn", "collection_date", "potassium", "creatinine",
    ],
}

INTAKE_QUEUES: dict[str, dict[str, JSONValue]] = {
    "physician_progress_note": {
        "queue": "medical-records", "sla_hours": 24, "acknowledge": False,
    },
    "patient_intake_form": {
        "queue": "registration", "sla_hours": 4, "acknowledge": True,
    },
    "lab_result_slip": {
        "queue": "lab-results", "sla_hours": 2, "acknowledge": True,
    },
}

# Authored per DOCUMENT, because the codes follow the assessment sentence. Each wrong
# reading is one a coder meets in practice: the wrong side, the wrong class, the
# neighbouring code.
BILLING_CODES: dict[str, dict[str, JSONValue]] = {
    "A01": {
        "confirmed": [
            {"code": "J06.9",
             "description": "Acute upper respiratory infection, unspecified"},
        ],
        "proposed": [
            {"code": "J00", "description": "Acute nasopharyngitis (common cold)"},
        ],
        "note": "read the note as a common cold",
    },
    "A02": {
        "confirmed": [{"code": "M25.561", "description": "Pain in right knee"}],
        "proposed": [{"code": "M25.562", "description": "Pain in left knee"}],
        "note": "coded the left knee for a right-knee note",
    },
    "A03": {
        "confirmed": [
            {"code": "G44.209",
             "description": "Tension-type headache, unspecified, not intractable"},
        ],
        "proposed": [{"code": "G43.909", "description": "Migraine, unspecified"}],
        "note": "coded a migraine for a tension-type headache",
    },
}

_ASSESSMENT_PLAN: JSONValue = {
    "fields": [
        {
            "name": "assessment",
            "locator": {"kind": "section", "heading": "Assessment"},
            "value_type": "text",
        },
    ],
}


def scenario(scenario_id: str) -> dict[str, JSONValue]:
    for row in SCENARIOS:
        if row["id"] == scenario_id:
            return row
    raise KeyError(f"unknown scenario {scenario_id!r}")


def callers_of(operation: str) -> list[str]:
    """Every task that reaches this operation. Reuse, read from the other direction."""

    return [
        str(row["title"]) for row in SCENARIOS if operation in row["operations"]
    ]


def operation_input(operation: str, document: dict[str, JSONValue]) -> JSONValue:
    """The canonical input Cement keys this operation on for this document."""

    if OPERATIONS[operation]["keyed_on"] == "text":
        return {
            "document_type": document["document_type"],
            "assessment": pipeline.apply_plan(
                _ASSESSMENT_PLAN, str(document["text"])
            )["assessment"],
        }
    return document["signature"]


def reference_output(operation: str, document: dict[str, JSONValue]) -> JSONValue:
    """The output a supervisor confirms for one operation on one document."""

    document_type = str(document["document_type"])
    if operation == "document.extraction_plan":
        plan = pipeline.reference_plan(document_type)
        if plan is None:
            raise ValueError(f"no reference plan for {document_type!r}")
        return copy.deepcopy(plan)
    if operation == "document.phi_locators":
        return {
            "document_type": document_type,
            "layout": document["layout"],
            "identifiers": copy.deepcopy(IDENTIFIERS[document_type]),
        }
    if operation == "document.required_fields":
        plan = pipeline.reference_plan(document_type)
        names = [str(field["name"]) for field in plan["fields"]]
        required = REQUIRED_FIELDS[document_type]
        return {
            "document_type": document_type,
            "layout": document["layout"],
            "required": list(required),
            "optional": [name for name in names if name not in required],
        }
    if operation == "document.intake_queue":
        return {
            "document_type": document_type,
            "layout": document["layout"],
            **copy.deepcopy(INTAKE_QUEUES[document_type]),
        }
    if operation == "document.billing_codes":
        return {
            "codes": copy.deepcopy(BILLING_CODES[str(document["id"])]["confirmed"]),
            "basis": "assessment",
        }
    raise ValueError(f"unknown operation {operation!r}")


def _label_value(text: str, *labels: str) -> str:
    for line in text.split("\n"):
        key, separator, value = line.partition(":")
        if separator and key.strip() in labels:
            return value.strip()
    return ""


# A form that arrived with one required line blank. Derived here rather than added to
# `examples/`, which the gate censuses: the prototype borrows the corpus and never
# edits it. The blank leaves the layout signature byte-identical, so it lands in the
# SAME scope as B02 and proves the split the demo needs - the function is keyed on the
# structure, while the answer still follows the content.
INCOMPLETE_ID = "B03"
INCOMPLETE_SOURCE = "layout_b_intake_form_02.txt"
INCOMPLETE_EDITS = (
    ("Name: Noah Williams", "Name: Dana Whitfield"),
    ("Date of Birth: 1975-11-03", "Date of Birth: 1992-03-08"),
    ("Insurance ID: HZN-889416", "Insurance ID:"),
    (
        "Primary Complaint: Left shoulder stiffness for two weeks",
        "Primary Complaint: Recurring lower back pain",
    ),
)


def _document_entry(
    document_id: str, layout: str, origin: str, text: str
) -> dict[str, JSONValue]:
    signature = pipeline.layout_signature(text)
    return {
        "id": document_id,
        "layout": layout,
        "file": origin,
        "title": text.split("\n", 1)[0].title(),
        "patient": _label_value(text, "Patient", "Name"),
        "text": text,
        "signature": signature,
        "input_hash": _digest(signature),
        "document_type": signature["document_type"],
    }


def document_catalog() -> list[dict[str, JSONValue]]:
    """Read the corpus once: id, patient, OCR text and layout signature per file."""

    catalog: list[dict[str, JSONValue]] = []
    for path in sorted(DOCUMENTS_DIR.glob("layout_*.txt")):
        parts = path.stem.split("_")
        text = pipeline.ocr(path)
        catalog.append(
            _document_entry(
                parts[1].upper() + parts[-1], parts[1].upper(), path.name, text
            )
        )
        if path.name == INCOMPLETE_SOURCE:
            incomplete = text
            for before, after in INCOMPLETE_EDITS:
                incomplete = incomplete.replace(before, after)
            catalog.append(
                _document_entry(
                    INCOMPLETE_ID,
                    parts[1].upper(),
                    f"derived from {path.name}",
                    incomplete,
                )
            )
    return catalog


# --- simulated provider ------------------------------------------------------


def _without(plan: JSONValue, name: str) -> JSONValue:
    copied = copy.deepcopy(plan)
    copied["fields"] = [item for item in copied["fields"] if item["name"] != name]
    return copied


def _renamed(plan: JSONValue, name: str, new_name: str) -> JSONValue:
    copied = copy.deepcopy(plan)
    for item in copied["fields"]:
        if item["name"] == name:
            item["name"] = new_name
    return copied


def _retargeted(plan: JSONValue, name: str, locator: JSONValue) -> JSONValue:
    copied = copy.deepcopy(plan)
    for item in copied["fields"]:
        if item["name"] == name:
            item["locator"] = locator
    return copied


def _retyped(plan: JSONValue, names: tuple[str, ...], value_type: str) -> JSONValue:
    copied = copy.deepcopy(plan)
    for item in copied["fields"]:
        if item["name"] in names:
            item["value_type"] = value_type
    return copied


def _extraction_variants(document_type: str) -> list[dict[str, JSONValue]]:
    """Build the plan candidates this provider can return for one layout."""

    reference = pipeline.reference_plan(document_type)
    if reference is None:
        raise ValueError(f"no reference plan for {document_type!r}")
    pool: list[dict[str, JSONValue]] = [
        {
            "key": "complete",
            "note": "returned a complete plan for every field of this layout",
            "plan": copy.deepcopy(reference),
        }
    ]
    if document_type == "physician_progress_note":
        pool += [
            {
                "key": "dropped-provider",
                "note": "omitted the Provider field",
                "plan": _without(reference, "provider"),
            },
            {
                "key": "wrong-section",
                "note": "pointed assessment at the Plan section",
                "plan": _retargeted(
                    reference, "assessment", {"kind": "section", "heading": "Plan"}
                ),
            },
            {
                "key": "invented-label",
                "note": "invented a Physician label that this layout does not carry",
                "plan": _retargeted(
                    reference, "provider", {"kind": "label", "label": "Physician"}
                ),
            },
        ]
    elif document_type == "patient_intake_form":
        pool += [
            {
                "key": "dropped-allergies",
                "note": "omitted the Allergies section",
                "plan": _without(reference, "allergies"),
            },
            {
                "key": "renamed-field",
                "note": "returned complaint instead of primary_complaint",
                "plan": _renamed(reference, "primary_complaint", "complaint"),
            },
        ]
    else:
        pool += [
            {
                "key": "float-decimals",
                "note": "typed the decimal results as plain strings",
                "plan": _retyped(reference, ("potassium", "creatinine"), "string"),
            },
            {
                "key": "dropped-interpretation",
                "note": "omitted the Interpretation section",
                "plan": _without(reference, "interpretation"),
            },
        ]
    return pool


def _dropped(value: JSONValue, key: str, name: str) -> JSONValue:
    copied = copy.deepcopy(value)
    copied[key] = [item for item in copied[key] if _row_name(item) != name]
    return copied


def _moved(value: JSONValue, source: str, target: str, name: str) -> JSONValue:
    copied = copy.deepcopy(value)
    copied[source] = [item for item in copied[source] if item != name]
    copied[target] = sorted([*copied[target], name])
    return copied


def _row_name(item: JSONValue) -> str:
    """Name one list row for the diff, by whichever identifying key it carries."""

    if not isinstance(item, dict):
        return str(item)
    for key in ("field", "code", "name"):
        if key in item:
            return str(item[key])
    return json.dumps(item, sort_keys=True)


def variants(operation: str, document: dict[str, JSONValue]) -> list[dict[str, JSONValue]]:
    """The candidate pool for one operation on one document, reference first."""

    document_type = str(document["document_type"])
    if operation == "document.extraction_plan":
        return _extraction_variants(document_type)

    reference = reference_output(operation, document)
    pool: list[dict[str, JSONValue]] = [
        {
            "key": "complete",
            "note": "returned the full answer for this layout",
            "plan": copy.deepcopy(reference),
        },
    ]
    if operation == "document.phi_locators":
        date_field = IDENTIFIERS[document_type][2]["field"]
        pool += [
            {
                "key": "missed-date",
                "note": f"left {date_field} out of the identifier map",
                "plan": _dropped(reference, "identifiers", date_field),
            },
            {
                "key": "over-redacts",
                "note": "marked a clinical field as an identifier",
                "plan": {
                    **copy.deepcopy(reference),
                    "identifiers": [
                        *copy.deepcopy(reference["identifiers"]),
                        {"field": _clinical_field(document_type), "category": "name"},
                    ],
                },
            },
        ]
    elif operation == "document.required_fields":
        pool += [
            {
                "key": "over-strict",
                "note": f"required {reference['optional'][0]}, which is optional",
                "plan": _moved(
                    reference, "optional", "required", str(reference["optional"][0])
                ),
            },
            {
                "key": "under-strict",
                "note": f"treated {reference['required'][-1]} as optional",
                "plan": _moved(
                    reference, "required", "optional", str(reference["required"][-1])
                ),
            },
        ]
    elif operation == "document.intake_queue":
        pool += [
            {
                "key": "wrong-queue",
                "note": "sent it to the general intake queue",
                "plan": {**copy.deepcopy(reference), "queue": "general-intake"},
            },
            {
                "key": "wrong-sla",
                "note": "doubled the turnaround this queue works to",
                "plan": {
                    **copy.deepcopy(reference),
                    "sla_hours": int(reference["sla_hours"]) * 2,
                },
            },
        ]
    elif operation == "document.billing_codes":
        row = BILLING_CODES[str(document["id"])]
        pool += [
            {
                "key": "misread-assessment",
                "note": str(row["note"]),
                "plan": {"codes": copy.deepcopy(row["proposed"]), "basis": "assessment"},
            },
        ]
    return pool


def _clinical_field(document_type: str) -> str:
    """A field that is clinical, not identifying - the one an over-redaction eats."""

    return {
        "physician_progress_note": "assessment",
        "patient_intake_form": "primary_complaint",
        "lab_result_slip": "interpretation",
    }[document_type]


class StubProvider:
    """Stand in for one in-house LLM: a sampled candidate and a sampled latency.

    The first candidate for a scope always diverges from the reference, so the
    supervisor's correction is visible. Later candidates favour the complete answer.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._pools: dict[str, list[dict[str, JSONValue]]] = {}
        self._served: dict[str, int] = {}

    def latency_seconds(self) -> float:
        return self._rng.uniform(*LATENCY_RANGE)

    def candidate(
        self, operation: str, document: dict[str, JSONValue]
    ) -> dict[str, JSONValue]:
        # Keyed by the SCOPE the candidate answers, not by the document: two documents
        # of one layout share a pool, and that sharing is what builds a category.
        key = f"{operation}|{document['input_hash']}"
        if OPERATIONS[operation]["keyed_on"] == "text":
            key = f"{operation}|{document['id']}"
        pool = self._pools.setdefault(key, variants(operation, document))
        served = self._served.get(key, 0)
        self._served[key] = served + 1
        if served == 0:
            return copy.deepcopy(self._rng.choice(pool[1:]))
        if self._rng.random() < 0.6:
            return copy.deepcopy(pool[0])
        return copy.deepcopy(self._rng.choice(pool[1:]))


def plan_diff(proposed: JSONValue, reference: JSONValue) -> list[dict[str, str]]:
    """Compare two operation outputs for the review surface.

    An extraction plan compares field by field, because that is what a reviewer reads.
    Every other output is a small object, so it compares key by key, and a list value
    compares by membership.
    """

    if isinstance(proposed, dict) and "fields" in proposed:
        def index(plan: JSONValue) -> dict[str, JSONValue]:
            return {item["name"]: item for item in plan.get("fields", [])}

        left, right = index(proposed), index(reference)
        rows: list[dict[str, str]] = []
        for name in right:
            if name not in left:
                rows.append(
                    {"kind": "missing", "field": name, "detail": "not in the candidate"}
                )
            elif left[name] != right[name]:
                rows.append(
                    {
                        "kind": "changed",
                        "field": name,
                        "detail": json.dumps(left[name]["locator"], sort_keys=True),
                    }
                )
        for name in left:
            if name not in right:
                rows.append(
                    {
                        "kind": "extra",
                        "field": name,
                        "detail": "not in the confirmed plan",
                    }
                )
        return rows

    if not isinstance(proposed, dict) or not isinstance(reference, dict):
        return []
    rows = []
    for key in sorted(set(proposed) | set(reference)):
        left_value, right_value = proposed.get(key), reference.get(key)
        if left_value == right_value:
            continue
        if isinstance(left_value, list) and isinstance(right_value, list):
            left_names = {_row_name(item) for item in left_value}
            right_names = {_row_name(item) for item in right_value}
            for name in sorted(right_names - left_names):
                rows.append(
                    {"kind": "missing", "field": f"{key}.{name}",
                     "detail": "not in the candidate"}
                )
            for name in sorted(left_names - right_names):
                rows.append(
                    {"kind": "extra", "field": f"{key}.{name}",
                     "detail": "not in the confirmed answer"}
                )
            if left_names == right_names:
                rows.append(
                    {"kind": "changed", "field": key,
                     "detail": json.dumps(left_value, sort_keys=True)}
                )
            continue
        rows.append(
            {"kind": "changed", "field": key, "detail": json.dumps(left_value)}
        )
    return rows


def _completeness_sentence(blank: list[str]) -> str:
    names = ", ".join(name.replace("_", " ") for name in blank)
    if not blank:
        return "This form is complete. Every required field has a value."
    if len(blank) == 1:
        return f"One required field is blank: {names}. Return the form before you accept it."
    return (
        f"{len(blank)} required fields are blank: {names}. "
        "Return the form before you accept it."
    )


def _queue_sentence(queue: JSONValue) -> str:
    sentence = (
        f"Send this one to the {queue['queue']} queue. "
        f"That team works to a {queue['sla_hours']}-hour turnaround."
    )
    if queue["acknowledge"]:
        sentence += " They confirm receipt."
    return sentence


def compose_answer(
    scenario_id: str, document: dict[str, JSONValue], outputs: dict[str, JSONValue]
) -> dict[str, JSONValue]:
    """Build the one answer the chat shows out of the outputs the operations returned.

    Every branch is deterministic given its outputs, so a cemented turn and a
    supervised turn produce the same bytes for the same document.
    """

    def fields() -> dict[str, JSONValue]:
        return pipeline.apply_plan(
            outputs["document.extraction_plan"], str(document["text"])
        )

    try:
        if scenario_id == "file":
            return {"kind": "json", "body": fields(), "error": ""}
        if scenario_id == "share":
            shared = fields()
            for row in outputs["document.phi_locators"]["identifiers"]:
                name = str(row["field"])
                if name in shared:
                    shared[name] = f"[redacted: {row['category']}]"
            return {"kind": "json", "body": shared, "error": ""}
        if scenario_id == "check":
            found = fields()
            required = [
                str(name) for name in outputs["document.required_fields"]["required"]
            ]
            blank = [
                name for name in required if not str(found.get(name, "")).strip()
            ]
            return {
                "kind": "text",
                "body": _completeness_sentence(blank),
                "error": "",
            }
        if scenario_id == "route":
            return {
                "kind": "text",
                "body": _queue_sentence(outputs["document.intake_queue"]),
                "error": "",
            }
        if scenario_id == "bill":
            return {
                "kind": "json",
                "body": {
                    "suggested_codes": outputs["document.billing_codes"]["codes"],
                    "read_from": "the assessment text",
                },
                "error": "",
            }
    except (ValueError, TypeError, KeyError) as error:
        return {"kind": "text", "body": None, "error": str(error)}
    raise ValueError(f"unknown scenario {scenario_id!r}")


# --- session -----------------------------------------------------------------


class Session:
    """One demo run: one ledger, one chat, one control plane."""

    def __init__(self, seed: int = 20260908) -> None:
        self.seed = seed
        self._lock = threading.RLock()
        self._temporary = tempfile.TemporaryDirectory(prefix="cement-demo-")
        self.database = str(Path(self._temporary.name) / "cement.db")
        self.system = System(self.database)
        for operation in OPERATIONS:
            self.system.register_operation(PARTITION, operation, policy=DEMO_POLICY)
        self.documents = document_catalog()
        self.provider = StubProvider(seed)
        self.chat: list[dict[str, JSONValue]] = []
        self.log: list[dict[str, JSONValue]] = []
        # Every real `cement` invocation, in order, with its exact argv and stdout.
        self.terminal: list[dict[str, JSONValue]] = []
        self.categories: dict[str, dict[str, JSONValue]] = {}
        self.pending: dict[str, dict[str, JSONValue]] = {}
        # Keyed by scope. An entry's value is unreadable without the per-request plans
        # that produced it, and `pending` drops a proposal the moment it is reviewed.
        self.lineage: dict[str, list[dict[str, JSONValue]]] = {}
        self.drafts: dict[str, dict[str, JSONValue]] = {}
        # One promoted function per operation, and the bytes each one exports.
        self.functions: dict[str, dict[str, JSONValue]] = {}
        self.bundles: dict[str, str] = {}
        self.blocked: dict[str, list[dict[str, JSONValue]]] = {}
        # Turns still waiting on a supervisor, keyed by turn id.
        self.inflight: dict[str, dict[str, JSONValue]] = {}
        self.selected = str(SCENARIOS[0]["id"])
        self.offline: dict[str, JSONValue] | None = None
        self.routed = False
        self.thinking: dict[str, JSONValue] | None = None
        self.started = time.time()
        self._sequence = 0
        self.stats = {
            "provider_calls": 0,
            "provider_seconds": 0.0,
            "reviews": 0,
            "cement_answers": 0,
            "provider_calls_avoided": 0,
            "resolve_ms": [],
        }
        self._note(
            "ledger",
            f"temporary ledger created; {len(OPERATIONS)} operations registered "
            f"in partition {PARTITION}",
            ", ".join(OPERATIONS)
            + f" · policy: {POLICY_VIEW['min_confirmations']} confirmations, "
            f"{POLICY_VIEW['min_reviewers']} reviewer, no minimum span",
        )

    # -- plumbing --

    def close(self) -> None:
        self._temporary.cleanup()

    def _next(self) -> int:
        self._sequence += 1
        return self._sequence

    def _note(self, kind: str, text: str, detail: str = "") -> None:
        self.log.append(
            {
                "seq": self._next(),
                "at": round(time.time() - self.started, 2),
                "kind": kind,
                "text": text,
                "detail": detail,
            }
        )

    def _say(self, role: str, kind: str, **fields: JSONValue) -> dict[str, JSONValue]:
        message = {"seq": self._next(), "role": role, "kind": kind, **fields}
        self.chat.append(message)
        return message

    def _cli(
        self,
        *arguments: str,
        stdin: str | None = None,
        reading: Callable[[JSONValue], list[list[str]]] | None = None,
        check: bool = True,
        sink: list[dict[str, JSONValue]] | None = None,
    ) -> JSONValue:
        """Run one real ``cement`` command against this ledger and record it.

        The page shows the command, its exit code and a short reading of the bytes
        this call actually returned; the verbatim stdout stays attached for the
        reader who opens it. Nothing here is rendered from anywhere else.
        """

        argv = [str(CEMENT), "--db", self.database, "--partition", PARTITION]
        argv.extend(arguments)
        started = time.perf_counter()
        completed = subprocess.run(  # noqa: S603
            argv, input=stdin, capture_output=True, text=True
        )
        elapsed = round((time.perf_counter() - started) * 1000)
        stdout = completed.stdout or completed.stderr
        value: JSONValue = None
        if stdout.strip():
            try:
                value = json.loads(stdout)
            except json.JSONDecodeError:
                value = None
        rows: list[list[str]] = []
        if reading is not None and completed.returncode == 0:
            rows = reading(value)
        elif completed.returncode != 0:
            message = value.get("message") if isinstance(value, dict) else None
            rows = [["error", str(message or f"exit {completed.returncode}")]]
        rows_sink = self.terminal if sink is None else sink
        rows_sink.append(
            {
                "seq": self._next(),
                "at": round(time.time() - self.started, 2),
                "display": _display(arguments),
                "argv": argv,
                "rc": completed.returncode,
                "ms": elapsed,
                "stdout": stdout,
                "bytes": len(stdout.encode("utf-8")),
                "reading": rows,
            }
        )
        if check and completed.returncode != 0:
            # Recorded first: a failing command belongs on the terminal the page reads.
            raise RuntimeError(rows[0][1] if rows else f"exit {completed.returncode}")
        return value

    def _ledger_preamble(self) -> list[str]:
        """The two lines that make every printed command runnable as spelled."""

        return [
            f"export CEMENT_DB={shlex.quote(self.database)}",
            "alias cement='cement --db \"$CEMENT_DB\" "
            f"--partition {shlex.quote(PARTITION)}'",
        ]

    def _document(self, document_id: str) -> dict[str, JSONValue]:
        for document in self.documents:
            if document["id"] == document_id:
                return document
        raise KeyError(f"unknown document {document_id!r}")

    def _request(self, request_id: str) -> dict[str, str]:
        for row in REQUESTS:
            if row["id"] == request_id:
                return row
        raise KeyError(f"unknown request {request_id!r}")

    @staticmethod
    def _scope_key(operation: str, document: dict[str, JSONValue]) -> str:
        return f"{operation}|{_digest(operation_input(operation, document))}"

    def _category(
        self, operation: str, document: dict[str, JSONValue]
    ) -> dict[str, JSONValue]:
        key = self._scope_key(operation, document)
        category = self.categories.get(key)
        if category is None:
            keyed_on = OPERATIONS[operation]["keyed_on"]
            category = {
                "key": key,
                "operation": operation,
                "operation_label": OPERATIONS[operation]["label"],
                "keyed_on": keyed_on,
                "input_hash": key.split("|", 1)[1],
                "layout": document["layout"],
                "document_type": document["document_type"],
                "document_id": document["id"],
                "callers": callers_of(operation),
                "candidates": [],
                "promoted": False,
                "artifact_id": None,
            }
            self.categories[key] = category
            self._note(
                "category",
                f"{operation}: a new exact scope, first seen on layout "
                f"{document['layout']}",
                f"input_hash {str(category['input_hash'])[:12]}… · keyed on "
                + (
                    f"{len(document['signature']['structure'])} structural keys, "
                    "no patient values"
                    if keyed_on == "layout"
                    else "the note's own assessment text, which no second visit repeats"
                ),
            )
        return category

    # -- chat --

    def send(self, request_id: str) -> None:
        """Send one request from the intake desk into the assistant.

        One turn can need several operations. Each part is tried against the promoted
        function first, and only the parts that miss reach the model. The chat shows
        nothing until every part settles, because a person asked one question.
        """

        with self._lock:
            request = self._request(request_id)
            document = self._document(str(request["document_id"]))
            task = scenario(str(request["scenario"]))
            self.selected = str(task["id"])
            turn = f"turn-{self._next()}"
            self._say(
                "clerk",
                "document",
                turn=turn,
                request_id=request_id,
                scenario=task["id"],
                scenario_title=task["title"],
                document_id=document["id"],
                title=document["title"],
                patient=document["patient"],
                layout=document["layout"],
                text=document["text"],
                ask=request["ask"],
                under=self._intent_under(task, document, str(request["ask"])),
            )
            parts = [
                self._resolve_part(str(operation), document)
                for operation in task["operations"]
            ]
            self.inflight[turn] = {
                "turn": turn,
                "request_id": request_id,
                "scenario": task["id"],
                "scenario_title": task["title"],
                "document_id": document["id"],
                "parts": parts,
            }
            unanswered = [part for part in parts if not part["settled"]]
            if not unanswered:
                self._finish(turn)
                return
            self.thinking = {
                "turn": turn,
                "document_id": document["id"],
                "provider": PROVIDER_NAME,
                "started": time.time(),
            }
            # One latency for the turn, not one per operation: a deployment asks the
            # model once and reads every part out of the same answer.
            delay = self.provider.latency_seconds()
            candidates = [
                (part, self.provider.candidate(str(part["operation"]), document))
                for part in unanswered
            ]

        time.sleep(delay)

        with self._lock:
            self.thinking = None
            self.stats["provider_calls"] += 1
            self.stats["provider_seconds"] = round(
                float(self.stats["provider_seconds"]) + delay, 2
            )
            for part, candidate in candidates:
                self._hold(turn, part, candidate, document, round(delay * 1000))
            self._say(
                "assistant",
                "held",
                turn=turn,
                document_id=document["id"],
                provider=PROVIDER_NAME,
                provider_ms=round(delay * 1000),
            )

    def _intent_under(
        self, task: dict[str, JSONValue], document: dict[str, JSONValue], ask: str
    ) -> dict[str, JSONValue]:
        """The peel-back on the request: how a sentence became an operation."""

        operations = [str(name) for name in task["operations"]]
        return {
            "summary": "how this turn became an operation",
            "rows": [
                ["the words you typed", ask],
                ["read as", str(task["intent"])],
                ["which calls", ", ".join(operations)],
                [
                    "attached",
                    f"{document['id']} · layout {document['layout']} · "
                    f"{str(document['document_type']).replace('_', ' ')}",
                ],
            ],
            "blocks": [
                {
                    "label": "the exact input, holding no patient values",
                    "json": document["signature"],
                },
            ],
            "note": "Two people word this task two ways. The model reads the intent "
            "and names the operation, and that reading is the simulated part. Cement "
            "never sees the wording. It answers an operation and one exact input.",
        }

    def _resolve_part(
        self, operation: str, document: dict[str, JSONValue]
    ) -> dict[str, JSONValue]:
        """Try the promoted function for one operation. A miss returns to the model."""

        part: dict[str, JSONValue] = {
            "operation": operation,
            "label": OPERATIONS[operation]["label"],
            "decides": OPERATIONS[operation]["decides"],
            "settled": False,
            "source": "model",
            "output": None,
            "proposal_id": None,
        }
        if not self.routed or self.functions.get(operation) is None:
            return part
        start = time.perf_counter()
        resolution = self.system.resolve(
            PARTITION, operation, operation_input(operation, document)
        )
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        self.stats["resolve_ms"].append(elapsed)
        verification = resolution.verification
        match = resolution.match
        if verification.passed and match is not None and match.matched:
            part.update(
                {
                    "settled": True,
                    "source": "function",
                    "output": match.output,
                    "resolve_ms": elapsed,
                    "artifact_hash": match.artifact_hash,
                    "function_hash": verification.function_hash,
                    "entries": verification.entries,
                    "checks": [check.key for check in verification.checks],
                }
            )
            self.stats["cement_answers"] += 1
            self.stats["provider_calls_avoided"] += 1
            self._note(
                "resolve",
                f"{document['id']} · {operation}: answered from the promoted set "
                f"in {elapsed} ms",
                f"{len(verification.checks)} checks passed over "
                f"{verification.entries} entry(ies) · no provider call",
            )
            return part
        part["fallback"] = f"no promoted entry for this input ({elapsed} ms)"
        self._note(
            "resolve",
            f"{document['id']} · {operation}: no promoted entry for this input "
            f"({elapsed} ms)",
            "this part of the request returns to the supervised path",
        )
        return part

    def _hold(
        self,
        turn: str,
        part: dict[str, JSONValue],
        candidate: dict[str, JSONValue],
        document: dict[str, JSONValue],
        provider_ms: int,
    ) -> None:
        """Submit one part's candidate and hold it for a supervisor."""

        operation = str(part["operation"])
        category = self._category(operation, document)
        proposal_id = self.system.submit_proposal(
            PARTITION,
            operation,
            operation_input(operation, document),
            candidate=Candidate(
                output=candidate["plan"],
                provenance={
                    "model": PROVIDER_NAME,
                    "variant": candidate["key"],
                    "simulated": "true",
                },
            ),
        )
        digest = _digest(candidate["plan"])
        if digest not in category["candidates"]:
            category["candidates"].append(digest)
        reference = reference_output(operation, document)
        part["proposal_id"] = proposal_id
        # An extraction plan is a rule ABOUT the document, so the reviewer reads what it
        # pulls out. Every other output already is the answer and needs no preview.
        preview, preview_error = (
            self._preview(candidate["plan"], str(document["text"]))
            if operation == "document.extraction_plan"
            else (None, "")
        )
        self.pending[proposal_id] = {
            "proposal_id": proposal_id,
            "turn": turn,
            "operation": operation,
            "operation_label": OPERATIONS[operation]["label"],
            "decides": OPERATIONS[operation]["decides"],
            "scenario": self.inflight[turn]["scenario"],
            "scenario_title": self.inflight[turn]["scenario_title"],
            "document_id": document["id"],
            "input_hash": category["input_hash"],
            "scope_label": self._scope_label(operation, str(category["input_hash"])),
            "layout": document["layout"],
            "variant": candidate["key"],
            "note": candidate["note"],
            "plan": candidate["plan"],
            "preview": preview,
            "preview_error": preview_error,
            "correction": reference,
            "diff": plan_diff(candidate["plan"], reference),
            "provider_ms": provider_ms,
        }
        self._note(
            "proposal",
            f"{document['id']} · {operation}: candidate stored as {proposal_id}",
            f"{PROVIDER_NAME} {provider_ms} ms simulated · the candidate stays hidden "
            "until review",
        )

    def _finish(self, turn: str) -> None:
        """Every part of one turn has settled, so the assistant answers once."""

        unit = self.inflight.pop(turn, None)
        if unit is None:
            return
        parts = list(unit["parts"])
        document = self._document(str(unit["document_id"]))
        outputs = {str(part["operation"]): part["output"] for part in parts}
        answer = compose_answer(str(unit["scenario"]), document, outputs)
        self._say(
            "assistant",
            "answer",
            turn=turn,
            document_id=document["id"],
            scenario=unit["scenario"],
            render=answer["kind"],
            body=answer["body"],
            error=answer["error"],
            under=self._answer_under(unit, parts, document),
        )

    def _refuse(self, turn: str, proposal_id: str) -> None:
        """One part was rejected, so the whole turn returns nothing to the user."""

        unit = self.inflight.pop(turn, None)
        if unit is None:
            return
        self._say(
            "assistant",
            "refused",
            turn=turn,
            document_id=unit["document_id"],
            under={
                "summary": "a person refused the model's answer",
                "rows": [
                    ["task", str(unit["scenario_title"])],
                    ["answered by", f"{PROVIDER_NAME} (simulated)"],
                    ["held as", proposal_id],
                    ["reviewer", f"{REVIEWER} rejected it"],
                    ["confirmed example", "none created"],
                ],
                "commands": [str(self.terminal[-1]["display"])],
                "commands_label": "the command the review surface ran",
                "note": "A rejection is audit evidence. It creates no example, so it "
                "widens no function.",
            },
        )

    def _answer_under(
        self,
        unit: dict[str, JSONValue],
        parts: list[dict[str, JSONValue]],
        document: dict[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """The peel-back on the answer: one section per operation behind it."""

        rows: list[list[str]] = [["task", str(unit["scenario_title"])]]
        blocks: list[dict[str, JSONValue]] = []
        commands: list[str] = []
        for part in parts:
            operation = str(part["operation"])
            if part["source"] == "function":
                rows.append(
                    [operation, f"the promoted function answered in "
                     f"{part['resolve_ms']} ms, with no model call"]
                )
                rows.append(
                    ["   checks", f"{len(list(part['checks']))} passed over "
                     f"{part['entries']} entry(ies), on this call"]
                )
                rows.append(["   entry", str(part["artifact_hash"])])
                commands.append(
                    f"cement resolve {operation} --input "
                    + shlex.quote(
                        json.dumps(operation_input(operation, document))
                    )
                )
            else:
                rows.append(
                    [operation, f"a model answered, and {REVIEWER} "
                     f"{part.get('status', 'confirmed')} it"]
                )
                rows.append(["   model took", f"{part.get('provider_ms')} ms (simulated)"])
                rows.append(["   held as", str(part["proposal_id"])])
                rows.append(["   confirmed example", str(part.get("example_id"))])
                if part.get("command"):
                    commands.append(str(part["command"]))
            blocks.append(
                {
                    "label": f"{OPERATIONS[operation]['label']} — "
                    f"{OPERATIONS[operation]['decides']}",
                    "json": part["output"],
                }
            )
        cemented = [part for part in parts if part["source"] == "function"]
        if cemented and len(cemented) != len(parts):
            note = (
                "This one answer has two sources. Cement returned the part it has "
                "verified, and the model kept the part nobody has confirmed twice. "
                "The bubble shows no seam, and that is the point."
            )
        elif cemented:
            note = (
                "No model ran. Every resolve runs the full six-check verification "
                "and caches nothing. A shell adds about 105 ms of interpreter "
                "startup, which is why the page calls the library here."
            )
        else:
            note = (
                "A model wrote this, and a person confirmed it. The bubble looks "
                "exactly like the cemented one above, because a user must not have "
                "to care which path answered."
            )
        detail: dict[str, JSONValue] = {
            "summary": "what happened under this answer",
            "rows": rows,
            "blocks": blocks,
            "note": note,
        }
        if commands:
            detail["commands"] = commands
            detail["commands_label"] = (
                "the commands behind this answer"
                if any(part["source"] != "function" for part in parts)
                else "the deployment calls System.resolve in process, and this "
                "command makes the same call from a shell"
            )
            detail["commands_ran"] = any(
                part["source"] != "function" for part in parts
            )
        return detail

    @staticmethod
    def _preview(plan: JSONValue, text: str) -> tuple[JSONValue, str]:
        try:
            return pipeline.apply_plan(plan, text), ""
        except (ValueError, TypeError) as error:
            return None, str(error)

    # -- review surface --

    def review(self, proposal_id: str, decision: str) -> None:
        with self._lock:
            record = self.pending.get(proposal_id)
            if record is None:
                raise KeyError(f"no pending proposal {proposal_id!r}")
            document = self._document(str(record["document_id"]))
            operation = str(record["operation"])
            turn = str(record["turn"])
            arguments = [
                "proposal",
                "review",
                proposal_id,
                "--reviewer",
                REVIEWER,
                "--decision",
                decision,
            ]
            if decision == "correct":
                arguments += [
                    "--output",
                    json.dumps(record["correction"], separators=(",", ":")),
                    "--note",
                    "corrected to the confirmed answer for this scope",
                ]
            result = self._cli(
                *arguments,
                reading=lambda value: [
                    ["status", str(value["status"])],
                    ["example", str(value["example_id"] or "none created")],
                ],
            )
            del self.pending[proposal_id]
            self.stats["reviews"] += 1
            command = str(self.terminal[-1]["display"])

            if result["status"] == "rejected":
                self._note(
                    "review",
                    f"{document['id']} · {operation}: {REVIEWER} rejected "
                    f"{proposal_id}",
                    "audit evidence only; the rejection creates no example",
                )
                self._refuse(turn, proposal_id)
                return

            diff = plan_diff(record["plan"], result["output"])
            self.lineage.setdefault(
                self._scope_key(operation, document), []
            ).append(
                {
                    "document_id": document["id"],
                    "proposal_id": proposal_id,
                    "operation": operation,
                    "layout": record["layout"],
                    "provider": PROVIDER_NAME,
                    "provider_ms": record["provider_ms"],
                    "variant": record["variant"],
                    "note": record["note"],
                    "provider_plan": record["plan"],
                    "confirmed_plan": result["output"],
                    "diff": diff,
                    "status": result["status"],
                    "reviewer": REVIEWER,
                    "example_id": result["example_id"],
                }
            )
            self._note(
                "review",
                f"{document['id']} · {operation}: {REVIEWER} {result['status']} "
                f"{proposal_id}",
                f"confirmed example {result['example_id']} binds this exact input "
                "to this exact answer",
            )
            unit = self.inflight.get(turn)
            if unit is None:
                return
            for part in unit["parts"]:
                if part.get("proposal_id") != proposal_id:
                    continue
                part.update(
                    {
                        "settled": True,
                        "output": result["output"],
                        "status": result["status"],
                        "example_id": result["example_id"],
                        "provider_ms": record["provider_ms"],
                        "diff": diff,
                        "command": command,
                    }
                )
            if all(part["settled"] for part in unit["parts"]):
                self._finish(turn)

    def revoke(self, example_id: str) -> None:
        with self._lock:
            self._cli(
                "example",
                "revoke",
                example_id,
                "--actor",
                REVIEWER,
                "--reason",
                "withdrawn in the demo",
                reading=lambda value: [
                    ["revoked", str(value["example_id"])],
                    [
                        "suspended artifacts",
                        str(len(value["suspended_artifact_ids"])),
                    ],
                ],
            )
            self._note(
                "evidence",
                f"{REVIEWER} revoked example {example_id}",
                "the example leaves the active evidence set for the next compile",
            )

    # -- lifecycle --

    def operations_for(self, scenario_id: str | None = None) -> list[str]:
        """The operations one task reaches. The lifecycle buttons act on exactly these."""

        return [
            str(name)
            for name in scenario(scenario_id or self.selected)["operations"]
        ]

    def select(self, scenario_id: str) -> None:
        with self._lock:
            scenario(scenario_id)
            self.selected = scenario_id

    def compile(self, scenario_id: str | None = None) -> None:
        with self._lock:
            for operation in self.operations_for(scenario_id):
                self._compile_one(operation)

    def _compile_one(self, operation: str) -> None:
        result = self._cli(
            "compile",
            operation,
            reading=lambda value: [
                ["created", str(len(value["created"])) + " draft(s)"],
            ]
            + [
                [
                    "blocked",
                    f"{self._scope_label(operation, str(row['input_hash']))} - "
                    + "; ".join(str(reason) for reason in row["reasons"]),
                ]
                for row in value["blocked"]
            ],
        )
        for artifact_id in result["created"]:
            summary = self.system.artifact(PARTITION, artifact_id)
            self.drafts[artifact_id] = {
                "artifact_id": artifact_id,
                "operation": operation,
                "input_hash": summary["input_hash"],
                "layout": self._layout_of(operation, str(summary["input_hash"])),
                "status": "draft",
                "support": summary["support"],
                "tests": None,
                "scope_hash": summary["scope_hash"],
            }
        blocked = [
            {
                "input_hash": row.get("input_hash"),
                "operation": operation,
                "layout": self._layout_of(operation, str(row.get("input_hash"))),
                "label": self._scope_label(operation, str(row.get("input_hash"))),
                "support": row.get("support"),
                "reasons": row.get("reasons"),
            }
            for row in result["blocked"]
        ]
        self.blocked[operation] = blocked
        self._note(
            "compile",
            f"{operation}: compile created {len(result['created'])} draft(s), "
            f"{len(result['blocked'])} scope(s) blocked",
            "; ".join(
                f"{row['label']}: "
                + ", ".join(str(reason) for reason in (row["reasons"] or []))
                for row in blocked
            )
            or "grouped active examples by exact scope; no model runs here",
        )

    def verify(self, scenario_id: str | None = None) -> None:
        with self._lock:
            for operation in self.operations_for(scenario_id):
                self._verify_one(operation)

    def _verify_one(self, operation: str) -> None:
        verification = self._cli(
            "function",
            "verify-drafts",
            operation,
            "--actor",
            PROMOTER,
            reading=lambda value: [
                ["verdict", "passed" if value["passed"] else "failed"],
                [
                    "replayed",
                    f"{sum(row['report']['tests'] for row in value['entries'])} "
                    f"sealed test(s) over {len(value['entries'])} draft(s)",
                ],
            ],
        )
        for entry in verification["entries"]:
            draft = self.drafts.get(entry["artifact_id"])
            if draft is None:
                continue
            report = entry["report"]
            draft["status"] = "verified" if report["passed"] else "failed"
            draft["tests"] = report["tests"]
            draft["scope_hash"] = report["scope_hash"]
        tests = sum(row["report"]["tests"] for row in verification["entries"])
        self._note(
            "verify",
            f"{operation}: verify-drafts replayed {tests} sealed test(s) "
            f"over {len(verification['entries'])} draft(s)",
            "every active example in the exact scope, plus partition, operation, "
            "revision and input boundary probes",
        )

    def promote(self, scenario_id: str | None = None) -> None:
        with self._lock:
            for operation in self.operations_for(scenario_id):
                self._promote_one(operation)

    def _promote_one(self, operation: str) -> None:
        promoted: list[str] = []
        for draft in self.drafts.values():
            if draft["status"] != "verified" or draft["operation"] != operation:
                continue
            self._cli(
                "promote",
                str(draft["artifact_id"]),
                "--scope-hash",
                str(draft["scope_hash"]),
                "--actor",
                PROMOTER,
                reading=lambda value: [
                    ["promoted", str(value["artifact_id"])],
                    ["replaced", str(len(value["replaced_artifact_ids"]))],
                ],
            )
            draft["status"] = "promoted"
            promoted.append(str(draft["artifact_id"]))
            category = self.categories.get(f"{operation}|{draft['input_hash']}")
            if category is not None:
                category["promoted"] = True
                category["artifact_id"] = draft["artifact_id"]
        if promoted:
            self._note(
                "promote",
                f"{operation}: {PROMOTER} promoted {len(promoted)} artifact(s) "
                "against the verified scope hash",
                ", ".join(promoted),
            )
        # A task that reaches an already-sealed operation adds nothing to it, and a
        # second checkpoint would reseal the same entries under a fresh receipt.
        if promoted or operation not in self.functions:
            self._checkpoint(operation)

    def _checkpoint(self, operation: str) -> None:
        manifest = self._cli(
            "function",
            "inspect",
            operation,
            reading=lambda value: [
                ["verified entries", str(len(value["entries"]))],
                ["prospective hash", str(value["function_hash"])],
            ],
        )
        if not manifest["entries"]:
            self._note(
                "function",
                f"{operation}: no verified entries to seal into a function",
                "",
            )
            return
        function_hash = str(manifest["function_hash"])
        # `function promote` refuses unless the operator repeats the digest `inspect`
        # reported, so the demo passes the value it just read rather than a flag.
        promotion = self._cli(
            "function",
            "promote",
            operation,
            "--expected-function-hash",
            function_hash,
            "--actor",
            PROMOTER,
            reading=lambda value: [
                ["receipt", str(value["receipt_id"])],
                ["members", f"{len(value['member_artifact_ids'])} artifact(s)"],
            ],
        )
        verification = self._cli(
            "function",
            "verify",
            operation,
            "--expected-function-hash",
            function_hash,
            reading=lambda value: [
                ["verdict", "passed" if value["passed"] else "failed"],
                [
                    "checks",
                    f"{sum(1 for check in value['checks'] if check['passed'])}/"
                    f"{len(value['checks'])} over {value['entries']} entry(ies)",
                ],
            ],
        )
        self._cli(
            "function",
            "export",
            operation,
            reading=lambda value: [
                ["abi", str(value["abi"])],
                ["sealed entries", str(len(value["entries"]))],
            ],
        )
        self.bundles[operation] = str(self.terminal[-1]["stdout"])
        self.functions[operation] = {
            "operation": operation,
            "label": OPERATIONS[operation]["label"],
            "decides": OPERATIONS[operation]["decides"],
            "callers": callers_of(operation),
            "function_hash": verification["function_hash"],
            "entries": verification["entries"],
            "passed": verification["passed"],
            "checks": verification["checks"],
            "receipt_id": promotion["receipt_id"],
            "members": list(promotion["member_artifact_ids"]),
            "bundle_bytes": len(self.bundles[operation].encode("utf-8")),
            "source": self._source_view(operation, function_hash),
        }
        self.offline = None
        self._note(
            "function",
            f"{operation}: set promotion sealed {verification['entries']} entry(ies) "
            f"under receipt {promotion['receipt_id']}",
            f"function_hash {function_hash[:16]}… · "
            f"{len(verification['checks'])} ordered checks passed",
        )

    def _hops(
        self, artifact_id: str, shared: list[dict[str, JSONValue]]
    ) -> tuple[list[dict[str, JSONValue]], list[dict[str, JSONValue]]]:
        """Walk one promoted entry back to the requests behind it, through the CLI.

        Four leaves and a join the caller performs by hand: no command prints an
        entry beside its originals, and `events` carries no example filter, so this
        scans the whole stream and matches `payload.example_id` itself. The cost is
        the point, and every row here is a command that ran.
        """

        rows = list(shared)
        artifact = self._cli(
            "artifact",
            "show",
            artifact_id,
            reading=lambda value: [
                ["evidence", ", ".join(value["evidence_ids"])],
                [
                    "support",
                    f"{value['support']} example(s), "
                    f"{value['reviewer_count']} reviewer(s)",
                ],
            ],
            sink=rows,
        )
        wanted = set(artifact["evidence_ids"])

        def matched(stream: JSONValue) -> list[tuple[str, str]]:
            return [
                (str(row["subject_id"]), str(row["payload"]["example_id"]))
                for row in stream
                if row["subject_type"] == "proposal"
                and isinstance(row.get("payload"), dict)
                and row["payload"].get("example_id") in wanted
            ]

        events = self._cli(
            "events",
            "--limit",
            "400",
            reading=lambda value: [
                ["scanned", f"{len(value)} event(s); no example filter exists"],
                [
                    "matched",
                    ", ".join(pair[0] for pair in matched(value)) or "none",
                ],
            ],
            sink=rows,
        )
        by_proposal = {
            str(row["proposal_id"]): row
            for group in self.lineage.values()
            for row in group
        }
        originals: list[dict[str, JSONValue]] = []
        for proposal_id, example_id in matched(events):
            shown = self._cli(
                "proposal",
                "show",
                proposal_id,
                reading=lambda value: [
                    ["status", f"{value['status']} by {value['reviewer']}"],
                    ["proposed_output", "what the model wrote"],
                    ["final_output", "what the supervisor kept"],
                ],
                sink=rows,
            )
            session_row = by_proposal.get(proposal_id, {})
            provenance = shown.get("provenance") or {}
            originals.append(
                {
                    "proposal_id": proposal_id,
                    "example_id": example_id,
                    "document_id": session_row.get("document_id", "-"),
                    "provider": provenance.get("model", PROVIDER_NAME),
                    "provider_ms": session_row.get("provider_ms"),
                    "variant": provenance.get("variant", "-"),
                    "note": session_row.get("note", ""),
                    "provider_plan": shown["proposed_output"],
                    "confirmed_plan": shown["final_output"],
                    "diff": plan_diff(shown["proposed_output"], shown["final_output"]),
                    "status": shown["status"],
                    "reviewer": shown["reviewer"],
                }
            )
        return rows, originals

    def _source_view(self, operation: str, function_hash: str) -> dict[str, JSONValue]:
        """Project the exported bundle into the entries a reader can read.

        Parsed back out of the bundle rather than rebuilt from the ledger: the reader
        must see the artifact that travels, not a second rendering of the same rows.
        """

        document = parse_function(
            self.bundles[operation], expected_function_hash=function_hash
        )
        scope: JSONValue = document.value["scope"]
        sealed: JSONValue = document.value["entries"]
        # Hop 1 answers every entry at once, so it runs here and prefixes each walk.
        shared: list[dict[str, JSONValue]] = []
        manifest = self._cli(
            "function",
            "inspect",
            operation,
            reading=lambda value: [
                [
                    "entries",
                    ", ".join(str(row["artifact_id"]) for row in value["entries"]),
                ],
            ],
            sink=shared,
        )
        by_artifact_hash = {
            str(row["artifact_hash"]): str(row["artifact_id"])
            for row in manifest["entries"]
        }
        entries: list[dict[str, JSONValue]] = []
        for index, entry in enumerate(sealed, start=1):
            input_hash = str(entry["input_hash"])
            artifact_id = by_artifact_hash.get(str(entry["artifact_hash"]), "")
            hops, originals = (
                self._hops(artifact_id, shared) if artifact_id else ([], [])
            )
            entries.append(
                {
                    "index": index,
                    "layout": self._layout_of(operation, input_hash),
                    "label": self._scope_label(operation, input_hash),
                    "input": entry["input"],
                    "output": entry["output"],
                    "input_hash": input_hash,
                    "artifact_hash": entry["artifact_hash"],
                    "artifact_id": artifact_id,
                    "entry_seal": entry["entry_seal"],
                    "confirmations": len(originals),
                    "reviewers": sorted({str(row["reviewer"]) for row in originals}),
                    "originals": originals,
                    "hops": hops,
                }
            )
        return {
            "partition": scope["partition"],
            "operation": scope["operation"],
            "label": OPERATIONS[operation]["label"],
            "revision": scope["operation_revision"],
            "entries": entries,
        }

    def route(self, enabled: bool) -> None:
        with self._lock:
            self.routed = bool(enabled)
            promoted = sorted(self.functions)
            self._note(
                "routing",
                f"operator routing {'enabled' if self.routed else 'disabled'}",
                f"{len(promoted)} promoted function(s): " + ", ".join(promoted)
                + " · a matching input resolves from the promoted set, and every "
                "other input keeps the supervised path"
                if self.routed
                else "every request returns to the supervised provider path",
            )

    def _bundle_target(self, operation: str | None) -> str:
        """Name the operation a bundle request means, defaulting to the task's own."""

        return operation or next(
            (name for name in self.operations_for() if name in self.functions), ""
        )

    def bundle(self, operation: str | None = None) -> str | None:
        with self._lock:
            return self.bundles.get(self._bundle_target(operation))

    def evaluate_offline(
        self, document_id: str, operation: str | None = None
    ) -> None:
        """Answer one document from the exported bytes, with no ledger read."""

        with self._lock:
            target = self._bundle_target(operation)
            if target not in self.functions:
                raise RuntimeError("no verified function to export for this task")
            document = self._document(document_id)
            expected = str(self.functions[target]["function_hash"])
            bundle = self.bundles[target]
            function = parse_function(bundle, expected_function_hash=expected)
            match = evaluate(
                function,
                input_json=canonicalize(operation_input(target, document)),
            )
            self.offline = {
                "document_id": document["id"],
                "operation": target,
                "label": OPERATIONS[target]["label"],
                "layout": document["layout"],
                "matched": match.matched,
                "output": match.output if match.matched else None,
                "artifact_hash": match.artifact_hash,
                "function_hash": function.function_hash,
            }
            self._note(
                "bundle",
                f"{document['id']} · {target}: the exported bundle "
                f"{'returned the confirmed answer' if match.matched else 'reported a miss'}",
                f"{len(bundle.encode('utf-8'))} bytes parsed against the "
                "operator's own hash; no ledger read",
            )

    # -- read model --

    def _layout_of(self, operation: str, input_hash: str) -> str:
        category = self.categories.get(f"{operation}|{input_hash}")
        if category is not None:
            return str(category["layout"])
        for document in self.documents:
            if document["input_hash"] == input_hash:
                return str(document["layout"])
        return "?"

    def _scope_label(self, operation: str, input_hash: str) -> str:
        """Name one scope the way the page names it, layout or note."""

        if OPERATIONS[operation]["keyed_on"] == "text":
            category = self.categories.get(f"{operation}|{input_hash}")
            document = category.get("document_id") if category else None
            return f"one note's assessment text{f' ({document})' if document else ''}"
        return f"layout {self._layout_of(operation, input_hash)}"

    def _evidence(self) -> dict[str, list[dict[str, JSONValue]]]:
        grouped: dict[str, list[dict[str, JSONValue]]] = {}
        for operation in OPERATIONS:
            for row in self.system.examples(PARTITION, operation):
                # `examples` returns the values, not their digests; the ledger groups
                # by the same canonical-JSON digest the compiler uses for a scope.
                key = f"{operation}|{_digest(row['input'])}"
                grouped.setdefault(key, []).append(
                    {
                        "example_id": row["id"],
                        "reviewer": row["reviewer"],
                        "origin": row["origin"],
                        "output_hash": _digest(row["output"])[:12],
                    }
                )
        return grouped

    def state(self) -> dict[str, JSONValue]:
        with self._lock:
            evidence = self._evidence()
            categories = []
            for key, category in self.categories.items():
                rows = evidence.get(key, [])
                categories.append(
                    {
                        **{
                            name: value
                            for name, value in category.items()
                            if name != "candidates"
                        },
                        "examples": rows,
                        "confirmations": len(rows),
                        "reviewers": sorted({str(row["reviewer"]) for row in rows}),
                        "distinct_candidates": len(category["candidates"]),
                        "required": POLICY_VIEW["min_confirmations"],
                    }
                )
            resolve_ms = list(self.stats["resolve_ms"])
            selected = self.operations_for()
            functions = []
            for operation in selected:
                function = self.functions.get(operation)
                if function is None:
                    functions.append(
                        {
                            "operation": operation,
                            "label": OPERATIONS[operation]["label"],
                            "decides": OPERATIONS[operation]["decides"],
                            "keyed_on": OPERATIONS[operation]["keyed_on"],
                            "callers": callers_of(operation),
                            "promoted": False,
                            "blocked": self.blocked.get(operation, []),
                        }
                    )
                    continue
                functions.append(
                    {
                        **function,
                        "keyed_on": OPERATIONS[operation]["keyed_on"],
                        "promoted": True,
                        "blocked": self.blocked.get(operation, []),
                        # Read time, not promotion time: a scope can miss the floor
                        # after the promotion that sealed the function.
                        "excluded": [
                            {
                                "label": self._scope_label(
                                    operation, str(category["input_hash"])
                                ),
                                "confirmations": len(evidence.get(key, [])),
                                "required": POLICY_VIEW["min_confirmations"],
                            }
                            for key, category in self.categories.items()
                            if category["operation"] == operation
                            and not category["promoted"]
                        ],
                    }
                )
            return {
                "partition": PARTITION,
                "reviewer": REVIEWER,
                "promoter": PROMOTER,
                "provider": PROVIDER_NAME,
                "policy": POLICY_VIEW,
                # Every operation, selected or not: the coverage strip is the one place
                # the page shows that one function serves several tasks.
                "operations": [
                    {
                        "name": name,
                        **detail,
                        "callers": callers_of(name),
                        "promoted": name in self.functions,
                        "entries": self.functions.get(name, {}).get("entries", 0),
                        "blocked": len(self.blocked.get(name, [])),
                        "selected": name in selected,
                    }
                    for name, detail in OPERATIONS.items()
                ],
                "scenarios": [
                    {
                        **row,
                        "requests": [
                            request
                            for request in REQUESTS
                            if request["scenario"] == row["id"]
                        ],
                    }
                    for row in SCENARIOS
                ],
                "selected": self.selected,
                "selected_operations": selected,
                "documents": [
                    {
                        name: value
                        for name, value in document.items()
                        if name != "signature"
                    }
                    for document in self.documents
                ],
                "chat": self.chat,
                "log": self.log,
                "terminal": self.terminal,
                "ledger": {
                    "path": self.database,
                    "preamble": self._ledger_preamble(),
                },
                "categories": sorted(
                    (row for row in categories if row["operation"] in selected),
                    key=lambda row: (str(row["operation"]), str(row["layout"])),
                ),
                "pending": [
                    row
                    for row in self.pending.values()
                    if row["operation"] in selected
                ],
                "drafts": [
                    row
                    for row in self.drafts.values()
                    if row["operation"] in selected
                ],
                "functions": functions,
                "promoted_operations": sorted(self.functions),
                "offline": self.offline,
                "routed": self.routed,
                "thinking": self.thinking,
                "stats": {
                    **{
                        name: value
                        for name, value in self.stats.items()
                        if name != "resolve_ms"
                    },
                    "resolve_ms_last": resolve_ms[-1] if resolve_ms else None,
                    "resolve_ms_median": _median(resolve_ms),
                    "provider_ms_mean": round(
                        float(self.stats["provider_seconds"])
                        * 1000
                        / max(1, int(self.stats["provider_calls"]))
                    )
                    if self.stats["provider_calls"]
                    else None,
                },
            }

    def transcript(self) -> str:
        """Render the control-plane log as plain text for the proof directory."""

        with self._lock:
            lines = [
                "Cement web UI demo - control-plane transcript",
                f"partition {PARTITION} · {len(OPERATIONS)} operations · "
                f"seed {self.seed}",
                ", ".join(OPERATIONS),
                f"policy {POLICY_VIEW['min_confirmations']} confirmations, "
                f"{POLICY_VIEW['min_reviewers']} reviewer, no minimum span "
                f"(production default: {POLICY_VIEW['production_default']})",
                "",
            ]
            for row in self.log:
                lines.append(f"[{row['at']:>7.2f}s] {row['kind']:<9} {row['text']}")
                if row["detail"]:
                    lines.append(f"{'':>10}  {'':<9} {row['detail']}")
            return "\n".join(lines) + "\n"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 1)
    return round((ordered[middle - 1] + ordered[middle]) / 2, 1)


__all__ = ["CementError", "Session", "document_catalog"]
