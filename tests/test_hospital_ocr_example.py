from __future__ import annotations

import contextlib
import io
import itertools
import json
import os
from pathlib import Path
import re
import runpy
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from cement_runtime import (
    Candidate,
    CandidateRequest,
    FunctionDocument,
    FunctionMatch,
    IntegrityError,
    System,
)
import cement_runtime.system as system_module
from cement_runtime.json_value import canonicalize
from cement_runtime.projection import structure

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "hospital_ocr"
sys.path.insert(0, str(EXAMPLE_DIR))

import pipeline
import plan_adapter
import run_demo

DOCUMENTS_DIR = EXAMPLE_DIR / "documents"

DOCUMENT_TYPES = {
    "layout_a_progress_note_01.txt": "physician_progress_note",
    "layout_a_progress_note_02.txt": "physician_progress_note",
    "layout_a_progress_note_03.txt": "physician_progress_note",
    "layout_b_intake_form_01.txt": "patient_intake_form",
    "layout_b_intake_form_02.txt": "patient_intake_form",
    "layout_c_lab_slip_01.txt": "lab_result_slip",
    "layout_c_lab_slip_02.txt": "lab_result_slip",
}

EXPECTED_OUTPUTS = {
    "layout_a_progress_note_01.txt": {
        "patient_name": "Jane Doe",
        "mrn": "MG-100241",
        "encounter_date": "2026-02-14",
        "provider": "Dr. Elena Ramirez",
        "assessment": "Viral upper respiratory infection.",
    },
    "layout_a_progress_note_02.txt": {
        "patient_name": "Marcus Lee",
        "mrn": "MG-100587",
        "encounter_date": "2026-02-18",
        "provider": "Dr. Jonah Reed",
        "assessment": "Overuse-related right knee pain.",
    },
    "layout_a_progress_note_03.txt": {
        "patient_name": "Sofia Patel",
        "mrn": "MG-100913",
        "encounter_date": "2026-02-21",
        "provider": "Dr. Amina Shah",
        "assessment": "Tension-type headaches, improving.",
    },
    "layout_b_intake_form_01.txt": {
        "patient_name": "Amelia Brooks",
        "date_of_birth": "1988-07-19",
        "insurance_id": "HZN-774201",
        "primary_complaint": "Persistent headaches after long workdays",
        "allergies": "Penicillin",
        "current_medications": (
            "Lisinopril 10 mg once daily\nMagnesium supplement once daily"
        ),
    },
    "layout_b_intake_form_02.txt": {
        "patient_name": "Noah Williams",
        "date_of_birth": "1975-11-03",
        "insurance_id": "HZN-889416",
        "primary_complaint": "Left shoulder stiffness for two weeks",
        "allergies": "Latex",
        "current_medications": (
            "Atorvastatin 20 mg nightly\nAcetaminophen as needed"
        ),
    },
    "layout_c_lab_slip_01.txt": {
        "patient_name": "Luis Ortega",
        "mrn": "MG-200164",
        "collection_date": "2026-03-02",
        "potassium": "4.2",
        "creatinine": "0.9",
        "interpretation": "Results are within the laboratory reference ranges.",
    },
    "layout_c_lab_slip_02.txt": {
        "patient_name": "Priya Nair",
        "mrn": "MG-200731",
        "collection_date": "2026-03-05",
        "potassium": "3.8",
        "creatinine": "1.1",
        "interpretation": (
            "Results are stable compared with the prior collection."
        ),
    },
}

PATIENT_VALUES = (
    "Marcus Lee",
    "Sofia Patel",
    "Jane Doe",
    "Amelia Brooks",
    "Noah Williams",
    "Luis Ortega",
    "Priya Nair",
    "MG-100587",
    "MG-100913",
    "MG-100241",
    "MG-200164",
    "MG-200731",
    "2026-02-18",
    "2026-02-21",
    "2026-02-14",
    "1988-07-19",
    "1975-11-03",
    "2026-03-02",
    "2026-03-05",
    "HZN-774201",
    "HZN-889416",
    "4.2",
    "0.9",
    "3.8",
    "1.1",
)


def _document(filename: str) -> str:
    return pipeline.ocr(DOCUMENTS_DIR / filename)


def _canonical_bytes(value: pipeline.JSONValue) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class SignatureCanonicalizationTests(unittest.TestCase):
    def test_every_document_in_one_layout_has_a_byte_identical_signature(self) -> None:
        signatures_by_type: dict[str, set[bytes]] = {}
        for filename, document_type in DOCUMENT_TYPES.items():
            with self.subTest(filename=filename):
                signature = _canonical_bytes(
                    pipeline.layout_signature(_document(filename))
                )
                signatures_by_type.setdefault(document_type, set()).add(signature)

        self.assertEqual(
            {
                document_type: len(signatures)
                for document_type, signatures in signatures_by_type.items()
            },
            {
                "physician_progress_note": 1,
                "patient_intake_form": 1,
                "lab_result_slip": 1,
            },
        )
        self.assertEqual(
            len({next(iter(signatures)) for signatures in signatures_by_type.values()}),
            3,
        )

    def test_moving_a_label_into_a_section_changes_the_signature(self) -> None:
        original = _document("layout_a_progress_note_01.txt")
        moved = original.replace("Provider: Dr. Elena Ramirez\n", "").replace(
            "Assessment:\nViral upper respiratory infection.",
            "Assessment:\nProvider: Dr. Elena Ramirez\n"
            "Viral upper respiratory infection.",
        )

        self.assertNotEqual(
            _canonical_bytes(pipeline.layout_signature(original)),
            _canonical_bytes(pipeline.layout_signature(moved)),
        )

    def test_patient_colon_prose_does_not_change_or_leak_into_signature(self) -> None:
        original = _document("layout_a_progress_note_01.txt")
        changed = original.replace(
            "Reports three days of sore throat, nasal congestion, and fatigue.",
            "Jane Doe: reports three days of sore throat, nasal congestion, "
            "and fatigue.",
        )
        original_signature = _canonical_bytes(pipeline.layout_signature(original))
        changed_signature = _canonical_bytes(pipeline.layout_signature(changed))

        self.assertEqual(changed_signature, original_signature)
        self.assertNotIn(b"Jane Doe", changed_signature)

    def test_blank_label_value_keeps_the_same_structural_kind(self) -> None:
        original = _document("layout_a_progress_note_01.txt")
        blank = original.replace("MRN: MG-100241", "MRN:")

        self.assertEqual(
            _canonical_bytes(pipeline.layout_signature(blank)),
            _canonical_bytes(pipeline.layout_signature(original)),
        )

    def test_unrecognized_block_shape_fails_closed(self) -> None:
        malformed = _document("layout_a_progress_note_01.txt").replace(
            "Assessment:\n", "Assessment\n"
        )

        with self.assertRaisesRegex(ValueError, "unrecognized OCR layout line"):
            pipeline.layout_signature(malformed)

    def test_signatures_exclude_all_real_patient_values(self) -> None:
        for filename in DOCUMENT_TYPES:
            signature = _canonical_bytes(pipeline.layout_signature(_document(filename)))
            for value in PATIENT_VALUES:
                with self.subTest(filename=filename, value=value):
                    self.assertNotIn(value.encode("utf-8"), signature)


class ExtractionTests(unittest.TestCase):
    def test_reference_plans_extract_complete_expected_objects(self) -> None:
        for filename, expected in EXPECTED_OUTPUTS.items():
            with self.subTest(filename=filename):
                ocr_text = _document(filename)
                plan = pipeline.reference_plan(DOCUMENT_TYPES[filename])
                self.assertIsNotNone(plan)
                self.assertEqual(pipeline.apply_plan(plan, ocr_text), expected)

    def test_label_locators_handle_blank_duplicate_and_section_body_lines(self) -> None:
        original = _document("layout_a_progress_note_01.txt")
        mrn_plan = {
            "fields": [
                {
                    "name": "mrn",
                    "locator": {"kind": "label", "label": "MRN"},
                }
            ]
        }
        blank = original.replace("MRN: MG-100241", "MRN:")
        self.assertEqual(pipeline.apply_plan(mrn_plan, blank), {"mrn": ""})

        duplicated = original.replace(
            "MRN: MG-100241", "MRN: MG-100241\nMRN: MG-999999"
        )
        with self.assertRaisesRegex(ValueError, "label is ambiguous"):
            pipeline.apply_plan(mrn_plan, duplicated)

        provider_plan = {
            "fields": [
                {
                    "name": "provider",
                    "locator": {"kind": "label", "label": "Provider"},
                }
            ]
        }
        body_match = original.replace(
            "Reports three days of sore throat, nasal congestion, and fatigue.",
            "Provider: Section body value\n"
            "Reports three days of sore throat, nasal congestion, and fatigue.",
        )
        self.assertEqual(
            pipeline.apply_plan(provider_plan, body_match),
            {"provider": "Dr. Elena Ramirez"},
        )

    def test_section_locators_keep_colon_lines_and_stop_before_field_blocks(self) -> None:
        ocr_text = """CUSTOM LAB NOTE
Patient: Ada Lovelace

Findings:
White blood cell count is normal.
Differential:
No abnormal cells are present.

Reviewer: Dr. Grace Hopper
Status: Final
"""
        plan = {
            "fields": [
                {
                    "name": "findings",
                    "locator": {"kind": "section", "heading": "Findings"},
                },
                {
                    "name": "reviewer",
                    "locator": {"kind": "label", "label": "Reviewer"},
                },
            ]
        }

        self.assertEqual(
            pipeline.apply_plan(plan, ocr_text),
            {
                "findings": (
                    "White blood cell count is normal.\n"
                    "Differential:\n"
                    "No abnormal cells are present."
                ),
                "reviewer": "Dr. Grace Hopper",
            },
        )

    def test_duplicate_section_heading_is_rejected_rather_than_guessed(self) -> None:
        ocr_text = """CUSTOM LAB NOTE
Patient: Ada Lovelace

Findings:
White blood cell count is normal.

Findings:
A second panel disagrees.
"""
        plan = {
            "fields": [
                {
                    "name": "findings",
                    "locator": {"kind": "section", "heading": "Findings"},
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "section is ambiguous"):
            pipeline.apply_plan(plan, ocr_text)


class CementJSONV1Tests(unittest.TestCase):
    def test_signatures_reference_plans_and_outputs_are_cement_json_v1(self) -> None:
        for document_type, plan in pipeline.REFERENCE_PLANS.items():
            with self.subTest(document_type=document_type, value="reference_plan"):
                canonicalize(plan)

        for filename in DOCUMENT_TYPES:
            with self.subTest(filename=filename):
                ocr_text = _document(filename)
                signature = pipeline.layout_signature(ocr_text)
                canonicalize(signature)
                plan = pipeline.reference_plan(DOCUMENT_TYPES[filename])
                self.assertIsNotNone(plan)
                output = pipeline.apply_plan(plan, ocr_text)
                canonicalize(output)
                if DOCUMENT_TYPES[filename] == "lab_result_slip":
                    self.assertIs(type(output["potassium"]), str)
                    self.assertIs(type(output["creatinine"]), str)


class PlanAdapterTests(unittest.TestCase):
    def request(
        self,
        signature,
    ) -> CandidateRequest:
        return CandidateRequest(
            partition="example-hospital",
            operation="document.extraction_plan",
            operation_revision=1,
            input=signature,
        )

    def test_known_layout_plans_match_reference_extraction_for_each_layout(self) -> None:
        proposer = plan_adapter.PlanProposer()
        for filename in (
            "layout_a_progress_note_01.txt",
            "layout_b_intake_form_01.txt",
            "layout_c_lab_slip_01.txt",
        ):
            with self.subTest(filename=filename):
                ocr_text = _document(filename)
                signature = {"document": ocr_text}
                proposed = proposer.propose(self.request(signature))
                reference = pipeline.reference_plan(DOCUMENT_TYPES[filename])
                self.assertIsNotNone(reference)
                self.assertEqual(
                    pipeline.apply_plan(proposed.output, ocr_text),
                    pipeline.apply_plan(reference, ocr_text),
                )

    def test_propose_is_byte_deterministic_for_output_and_provenance(self) -> None:
        signature = {"document": _document("layout_a_progress_note_01.txt")}
        proposer = plan_adapter.PlanProposer()
        first = proposer.propose(self.request(signature))
        second = proposer.propose(self.request(signature))

        self.assertEqual(
            _canonical_bytes(first.output),
            _canonical_bytes(second.output),
        )
        self.assertEqual(
            _canonical_bytes(first.provenance),
            _canonical_bytes(second.provenance),
        )

    def test_returned_known_plan_is_deep_copy_isolated(self) -> None:
        signature = {"document": _document("layout_a_progress_note_01.txt")}
        document_type = "physician_progress_note"
        reference_before = _canonical_bytes(pipeline.REFERENCE_PLANS[document_type])
        proposer = plan_adapter.PlanProposer()
        returned = proposer.propose(self.request(signature)).output

        returned["fields"][0]["locator"]["label"] = "Mutated Patient"

        self.assertEqual(
            _canonical_bytes(pipeline.REFERENCE_PLANS[document_type]),
            reference_before,
        )
        later = proposer.propose(self.request(signature))
        self.assertEqual(_canonical_bytes(later.output), reference_before)

    def test_drifted_known_layout_falls_back_to_applicable_best_effort_plan(self) -> None:
        original = _document("layout_a_progress_note_01.txt")
        drifted = original.replace("Provider: Dr. Elena Ramirez\n", "").replace(
            "Assessment:\nViral upper respiratory infection.",
            "Assessment:\nProvider: Dr. Elena Ramirez\n"
            "Viral upper respiratory infection.",
        )
        signature = {"document": drifted}
        candidate = plan_adapter.PlanProposer().propose(self.request(signature))
        canonicalize(candidate.output)

        self.assertEqual(candidate.provenance["strategy"], "best_effort")
        self.assertEqual(
            [field["name"] for field in candidate.output["fields"]],
            [
                "patient",
                "mrn",
                "date",
                "subjective",
                "objective",
                "assessment",
                "plan",
            ],
        )
        self.assertEqual(
            pipeline.apply_plan(candidate.output, drifted),
            {
                "patient": "Jane Doe",
                "mrn": "MG-100241",
                "date": "2026-02-14",
                "subjective": (
                    "Reports three days of sore throat, nasal congestion, and fatigue."
                ),
                "objective": (
                    "Temperature 37.4 C. Heart rate 78 bpm.\n"
                    "Oropharynx mildly erythematous without exudate."
                ),
                "assessment": (
                    "Provider: Dr. Elena Ramirez\n"
                    "Viral upper respiratory infection."
                ),
                "plan": "Encourage fluids and rest. Return if symptoms worsen.",
            },
        )

    def test_unknown_layout_best_effort_plan_preserves_structure_order(self) -> None:
        ocr_text = """CUSTOM FOLLOW-UP
Patient: Ada Lovelace
Visit ID: VISIT-42

Summary:
Recovery is complete.
Follow-up: one month.

Reviewer: Dr. Grace Hopper
Status: Final
"""
        signature = {"document": ocr_text}
        candidate = plan_adapter.PlanProposer().propose(self.request(signature))
        canonicalize(candidate.output)

        self.assertEqual(
            [field["name"] for field in candidate.output["fields"]],
            ["patient", "visit_id", "summary", "reviewer", "status"],
        )
        self.assertEqual(
            pipeline.apply_plan(candidate.output, ocr_text),
            {
                "patient": "Ada Lovelace",
                "visit_id": "VISIT-42",
                "summary": "Recovery is complete.\nFollow-up: one month.",
                "reviewer": "Dr. Grace Hopper",
                "status": "Final",
            },
        )

    def test_colliding_normalized_field_names_are_stably_suffixed(self) -> None:
        ocr_text = """CUSTOM COLLISION NOTE
Patient Name: Ada Lovelace
Patient-Name: Grace Hopper
Patient_Name: Katherine Johnson
"""
        signature = {"document": ocr_text}
        candidate = plan_adapter.PlanProposer().propose(self.request(signature))
        canonicalize(candidate.output)

        self.assertEqual(
            [field["name"] for field in candidate.output["fields"]],
            ["patient_name", "patient_name_2", "patient_name_3"],
        )
        self.assertEqual(
            pipeline.apply_plan(candidate.output, ocr_text),
            {
                "patient_name": "Ada Lovelace",
                "patient_name_2": "Grace Hopper",
                "patient_name_3": "Katherine Johnson",
            },
        )

    def test_whitespace_only_identifiers_are_rejected(self) -> None:
        proposer = plan_adapter.PlanProposer()
        signatures = (
            ("document_type", {"document_type": "   ", "structure": []}),
            (
                "kind",
                {
                    "document_type": "physician_progress_note",
                    "structure": [{"kind": "   ", "key": "Patient"}],
                },
            ),
            (
                "key",
                {
                    "document_type": "physician_progress_note",
                    "structure": [{"kind": "label", "key": "   "}],
                },
            ),
        )

        for identifier, signature in signatures:
            with self.subTest(identifier=identifier), self.assertRaises(ValueError), mock.patch.object(
                pipeline, "layout_signature", return_value=signature
            ):
                proposer.propose(self.request({"document": "raw text"}))

    def test_malformed_signatures_are_rejected_defensively(self) -> None:
        proposer = plan_adapter.PlanProposer()
        with self.assertRaises(TypeError):
            proposer.propose(self.request([]))

        for signature in (
            {},
            {"document": ""},
            {"document": 1},
            {"document": "A", "extra": "B"},
        ):
            with self.subTest(signature=signature), self.assertRaises(ValueError):
                proposer.propose(self.request(signature))

        malformed_structures = (
            {},
            {"document_type": ""},
            {"document_type": 1},
            {"document_type": "unknown_note"},
            {"document_type": "unknown_note", "structure": "not-a-list"},
            {"document_type": "unknown_note", "structure": ["not-an-object"]},
            {
                "document_type": "unknown_note",
                "structure": [{1: "not-a-string-key"}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"key": "Patient"}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"kind": "", "key": "Patient"}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"kind": 1, "key": "Patient"}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"kind": "label"}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"kind": "label", "key": ""}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"kind": "label", "key": 1}],
            },
            {
                "document_type": "unknown_note",
                "structure": [{"kind": "table", "key": "Rows"}],
            },
        )
        for signature in malformed_structures:
            with self.subTest(signature=signature), self.assertRaises(ValueError), mock.patch.object(
                pipeline, "layout_signature", return_value=signature
            ):
                proposer.propose(self.request({"document": "raw text"}))


SEED_DOCUMENTS = (
    "layout_a_progress_note_01.txt",
    "layout_a_progress_note_02.txt",
    "layout_b_intake_form_01.txt",
    "layout_b_intake_form_02.txt",
)

ARTIFACT_MASK = re.compile(r"art_[0-9a-f]{32}")
FUNCTION_HASH_MASK = re.compile(r"[0-9a-f]{64}")


def _promoted_example_ledger(database: str) -> FunctionDocument:
    """The demo's real learning pass publishes A/B; its switch stays off."""

    system = System(database, candidate_source=plan_adapter.PlanProposer())
    system.register_operation(run_demo.PARTITION, run_demo.OPERATION)
    for filename in SEED_DOCUMENTS:
        system.propose(run_demo.PARTITION, run_demo.OPERATION,
                       {"document": _document(filename)})
    function, build = run_demo.learning_pass(system, run=1)
    assert len(build.created) == 2
    return function


def _signature_digest(filename: str) -> str:
    title, pairs = structure(_document(filename))
    return canonicalize({"form": {"title": title, "structure": [list(pair) for pair in pairs]},
                         "keep": {}}).digest


def _mask_per_run_values(text: str) -> str:
    return ARTIFACT_MASK.sub(
        "art_<hex>", FUNCTION_HASH_MASK.sub("<function-hash>", text)
    )


def _readme_transcript() -> str:
    """Return the single fenced `text` block of the example README."""

    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in (EXAMPLE_DIR / "README.md").read_text(encoding="utf-8").splitlines():
        if current is None:
            if line == "```text":
                current = []
        elif line == "```":
            blocks.append(current)
            current = None
        else:
            current.append(line)
    if current is not None:
        raise AssertionError("unterminated ```text block in the example README")
    if len(blocks) != 1:
        raise AssertionError(
            f"expected exactly one ```text block in the example README, "
            f"found {len(blocks)}"
        )
    return "".join(f"{line}\n" for line in blocks[0])


class OfflineBundleTests(unittest.TestCase):
    """Resolution from exported bytes after the ledger is deleted."""

    bundle_text: str
    function_hash: str
    input_hashes: tuple[str, ...]

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as directory:
            function = _promoted_example_ledger(os.path.join(directory, "cement.db"))
        cls.bundle_text = function.text
        cls.function_hash = function.function_hash
        cls.input_hashes = function.input_hashes

    @contextlib.contextmanager
    def no_ledger(self):
        """Fail loudly if anything under test reaches for a database."""

        with mock.patch.object(
            System, "__init__", side_effect=AssertionError("System constructed")
        ), mock.patch.object(
            sqlite3, "connect", side_effect=AssertionError("connection opened")
        ):
            yield

    def resolve(self, ocr_text: str) -> tuple[str, FunctionMatch]:
        return run_demo.resolve_offline(
            self.bundle_text,
            ocr_text,
            expected_function_hash=self.function_hash,
        )

    def test_resolution_constructs_no_system_and_closes_the_extraction_loop(
        self,
    ) -> None:
        # The bundle alone carries the answer, and its own hash is what binds
        # that answer to the set the ledger verified before it went away.
        filename = "layout_a_progress_note_03.txt"
        ocr_text = _document(filename)
        with self.no_ledger():
            function_hash, match = self.resolve(ocr_text)
            self.assertTrue(match.matched)
            extracted = pipeline.apply_plan(match.output, ocr_text)

        self.assertEqual(function_hash, self.function_hash)
        self.assertEqual(extracted, EXPECTED_OUTPUTS[filename])

    def test_resolution_returns_the_library_miss_for_unexported_layout_c(self) -> None:
        # This fixture publishes A/B only; the projection refuses layout C.
        with self.no_ledger():
            function_hash, match = self.resolve(_document("layout_c_lab_slip_01.txt"))

        self.assertEqual(function_hash, self.function_hash)
        self.assertFalse(match.matched)
        self.assertIsNone(match.output)
        self.assertIsNone(match.artifact_hash)

    def test_resolution_reads_the_bundle_through_the_shipped_function_api(self) -> None:
        # Without this binding a resolver could decode the JSON itself, return a
        # reference plan, and satisfy every hit-and-miss assertion above.
        ocr_text = _document("layout_a_progress_note_03.txt")
        with mock.patch.object(
            run_demo, "parse_function", wraps=run_demo.parse_function
        ) as parse, mock.patch.object(
            run_demo, "evaluate", wraps=run_demo.evaluate
        ) as lookup, self.no_ledger():
            self.resolve(ocr_text)

        parse.assert_called_once_with(
            self.bundle_text, expected_function_hash=self.function_hash
        )
        self.assertEqual(lookup.call_count, 1)
        (document,), keywords = lookup.call_args
        self.assertEqual(document.function_hash, self.function_hash)
        self.assertEqual(
            keywords["input_json"].digest,
            canonicalize({"document": ocr_text}).digest,
        )

    def test_a_bundle_that_misses_the_held_identity_is_refused(self) -> None:
        # The binding is `parse_function`'s own, so `python -O` cannot strip it.
        with self.no_ledger(), self.assertRaises(IntegrityError):
            run_demo.resolve_offline(
                self.bundle_text,
                _document("layout_a_progress_note_03.txt"),
                expected_function_hash="0" * 64,
            )

    def test_the_function_holds_exactly_the_two_promoted_layout_signatures(
        self,
    ) -> None:
        self.assertEqual(
            sorted(self.input_hashes),
            sorted(
                {
                    _signature_digest("layout_a_progress_note_01.txt"),
                    _signature_digest("layout_b_intake_form_01.txt"),
                }
            ),
        )
        self.assertNotIn(
            _signature_digest("layout_c_lab_slip_01.txt"), self.input_hashes
        )

    def test_bundle_identity_is_per_run_while_its_length_is_stable(self) -> None:
        # Run-specific evidence and example IDs feed `entry_seal`, which moves
        # the root hash. The example README states this; the assertion below is
        # what keeps that statement true, so relaxing it is a documentation
        # change as much as a code change.
        with tempfile.TemporaryDirectory() as directory:
            second = _promoted_example_ledger(os.path.join(directory, "cement.db"))

        self.assertEqual(
            len(second.text.encode("utf-8")), len(self.bundle_text.encode("utf-8"))
        )
        self.assertNotEqual(second.function_hash, self.function_hash)


    def test_bundle_identity_follows_its_ids_and_clock_alone(self) -> None:
        # The cause behind the README's per-run sentence: hold every id and the clock fixed and
        # two independent ledgers export the same bytes; move ONE confirmed-example id and the
        # root hash moves while the byte length holds.
        def export(*, moved_example: bool) -> FunctionDocument:
            counter = itertools.count(1)
            clock = itertools.count(1_000_000_000, 1_000_000)
            examples = itertools.count(1)

            def ids(prefix: str) -> str:
                number = next(counter)
                if prefix == "ex" and next(examples) == 1 and moved_example:
                    return f"ex_{'f' * 32}"
                return f"{prefix}_{number:032x}"

            with tempfile.TemporaryDirectory() as directory, mock.patch.object(
                system_module, "_new_id", side_effect=ids
            ), mock.patch.object(system_module.time, "time_ns", side_effect=lambda: next(clock)):
                return _promoted_example_ledger(os.path.join(directory, "cement.db"))

        first, second, moved = (
            export(moved_example=False),
            export(moved_example=False),
            export(moved_example=True),
        )
        self.assertEqual(second.text, first.text)
        self.assertEqual(second.function_hash, first.function_hash)
        self.assertNotEqual(moved.function_hash, first.function_hash)
        self.assertEqual(len(moved.text.encode("utf-8")), len(first.text.encode("utf-8")))


class ShippedCommandRoundTripTests(unittest.TestCase):
    """One operator-route pass over the example's own exported bundle."""

    def environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment.pop("CEMENT_DB", None)
        environment.pop("CEMENT_PARTITION", None)
        return environment

    def evaluate(
        self, bundle: str, filename: str, function_hash: str
    ) -> subprocess.CompletedProcess[str]:
        signature = {"document": _document(filename)}
        # No `--db` and no ledger in the environment. This is the operator
        # invocation shape, not a ledger-freedom proof: `eval` is dispatched
        # ahead of the `--db` gate, so the CLI-leaf ledger-freedom pin stays
        # `test_cli.py::test_function_eval_opens_no_store_or_connection`.
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "cement_runtime",
                "function",
                "eval",
                "--bundle",
                bundle,
                "--input",
                json.dumps(
                    signature,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                "--expected-function-hash",
                function_hash,
            ],
            capture_output=True,
            text=True,
            env=self.environment(),
        )

    def test_shipped_cli_exports_the_bundle_and_answers_both_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "cement.db")
            function = _promoted_example_ledger(database)
            System(database).set_switch(
                run_demo.PARTITION, run_demo.OPERATION, mode="follow", actor="informatics-lead"
            )
            bundle = os.path.join(directory, "bundle.json")

            export = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cement_runtime",
                    "--db",
                    database,
                    "--partition",
                    run_demo.PARTITION,
                    "function",
                    "export",
                    run_demo.OPERATION,
                    "--out",
                    bundle,
                ],
                capture_output=True,
                text=True,
                env=self.environment(),
            )
            self.assertEqual(export.returncode, 0, export.stderr)
            self.assertEqual(export.stderr, "")
            written = Path(bundle).read_bytes()
            self.assertEqual(written, function.text.encode("utf-8"))
            self.assertEqual(
                json.loads(export.stdout),
                {
                    "bytes": len(written),
                    "function_hash": function.function_hash,
                    "out": bundle,
                },
            )

            filename = "layout_a_progress_note_03.txt"
            hit = self.evaluate(bundle, filename, function.function_hash)
            self.assertEqual(hit.returncode, 0, hit.stderr)
            self.assertEqual(hit.stderr, "")
            answer = json.loads(hit.stdout)
            self.assertTrue(answer["matched"])
            self.assertEqual(answer["function_hash"], function.function_hash)
            self.assertEqual(
                pipeline.apply_plan(answer["output"], _document(filename)),
                EXPECTED_OUTPUTS[filename],
            )

            miss = self.evaluate(
                bundle, "layout_c_lab_slip_01.txt", function.function_hash
            )
            self.assertEqual(miss.returncode, 6, miss.stderr)
            self.assertEqual(miss.stderr, "")
            self.assertEqual(
                json.loads(miss.stdout),
                {
                    "artifact_hash": None,
                    "function_hash": function.function_hash,
                    "matched": False,
                    "output": None,
                },
            )


class DemoTranscriptTests(unittest.TestCase):
    def test_demo_refuses_to_run_where_python_removes_its_assertions(self) -> None:
        # Optimized Python erases the demo's verdicts; it must refuse the run.
        for flag in ("-O", "-OO"):
            with self.subTest(flag=flag):
                result = subprocess.run(
                    [sys.executable, flag, "run_demo.py"],
                    capture_output=True,
                    text=True,
                    cwd=str(EXAMPLE_DIR),
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("without -O or -OO", result.stderr)
                self.assertNotIn("All checks passed.", result.stdout)

    def test_demo_output_matches_the_pinned_readme_transcript(self) -> None:
        # One compiled artifact ID and the final function hash move per run.
        # Every other line stays byte-identical to the pinned transcript.
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            run_demo.main()

        output = stream.getvalue()
        # Masking erases value and equality alike, so pin how much it erases.
        # An extra or missing dynamic token would otherwise mask away silently,
        # and `art_` followed by 64 hex digits would make the two patterns
        # overlap and make substitution order matter.
        self.assertEqual(len(FUNCTION_HASH_MASK.findall(output)), 1)
        self.assertEqual(len(ARTIFACT_MASK.findall(output)), 1)
        self.assertEqual(_mask_per_run_values(output), _readme_transcript())

    def test_the_offline_phase_runs_on_the_verified_bytes_after_teardown(self) -> None:
        directories = []
        exports = []
        calls = []
        matches = []
        real_directory = tempfile.TemporaryDirectory
        real_serving = System.serving
        real_resolve = run_demo.resolve_offline

        def recording_directory(*args, **kwargs):
            handle = real_directory(*args, **kwargs)
            directories.append(handle.name)
            return handle

        def recording_serving(system, *args, **kwargs):
            result = real_serving(system, *args, **kwargs)
            if kwargs.get("expected_function_hash") is not None:
                exports.append((result, any(os.path.exists(path) for path in directories)))
            return result

        def recording_resolve(bundle_text, *args, **kwargs):
            calls.append((bundle_text, kwargs["expected_function_hash"],
                          any(os.path.exists(path) for path in directories)))
            result = real_resolve(bundle_text, *args, **kwargs)
            matches.append((args[0], result[1]))
            return result

        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
            run_demo.tempfile, "TemporaryDirectory", recording_directory
        ), mock.patch.object(
            System, "serving", recording_serving
        ), mock.patch.object(run_demo, "resolve_offline", recording_resolve):
            run_demo.main()

        self.assertEqual(len(directories), 1)
        self.assertFalse(os.path.exists(directories[0]))
        self.assertEqual(len(exports), 1)
        ((state, verification), existed) = exports[0]
        self.assertTrue(existed)
        self.assertEqual(state.mode, "follow")
        self.assertTrue(verification.passed)
        self.assertIsNotNone(verification.document)
        document = verification.document
        self.assertEqual(len(document.input_hashes), 3)
        self.assertEqual(calls, [(document.text, document.function_hash, False)] * 2)
        self.assertEqual([match.matched for _, match in matches], [True, False])
        self.assertEqual(pipeline.apply_plan(matches[0][1].output, matches[0][0]),
                         EXPECTED_OUTPUTS["layout_a_progress_note_03.txt"])
        self.assertIsNone(matches[1][1].output)
        self.assertIn("UNSEEN FOLLOW-UP NOTE", matches[1][0])


class LearningWalkthroughTests(unittest.TestCase):
    def test_adapter_receives_raw_document_not_a_precomputed_signature(self) -> None:
        text = _document("layout_a_progress_note_01.txt")
        candidate = plan_adapter.PlanProposer().propose(CandidateRequest(
            partition=run_demo.PARTITION, operation=run_demo.OPERATION,
            operation_revision=1, input={"document": text},
        ))
        self.assertEqual(pipeline.apply_plan(candidate.output, text),
                         EXPECTED_OUTPUTS["layout_a_progress_note_01.txt"])

    def test_learning_pass_groups_raw_inputs_and_leaves_switch_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            system = System(os.path.join(directory, "cement.db"),
                            candidate_source=plan_adapter.PlanProposer())
            system.register_operation(run_demo.PARTITION, run_demo.OPERATION)
            filenames = (*SEED_DOCUMENTS, "layout_c_lab_slip_01.txt")
            ids = [system.propose(run_demo.PARTITION, run_demo.OPERATION,
                                  {"document": _document(name)}) for name in filenames]
            self.assertEqual({system.proposal(run_demo.PARTITION, ident)["status"]
                              for ident in ids}, {"pending"})
            function, build = run_demo.learning_pass(system, run=1)
            self.assertEqual(len(function.input_hashes), 2)
            self.assertEqual(len(build.created), 2)
            self.assertEqual([row["support"] for row in build.blocked], [1])
            self.assertEqual({system.proposal(run_demo.PARTITION, ident)["reviewer"]
                              for ident in ids}, {"learning-pass"})
            self.assertEqual(system.switch(run_demo.PARTITION, run_demo.OPERATION).mode,
                             "off")
            self.assertEqual(function.value["projection"]["abi"], "cement-projection-v1")

    def test_learning_pass_merges_proposals_and_supersedes_an_earlier_plan(self) -> None:
        full = pipeline.reference_plan("physician_progress_note")
        narrow = json.loads(json.dumps(full))
        narrow["fields"] = [row for row in narrow["fields"] if row["name"] != "provider"]
        with tempfile.TemporaryDirectory() as directory:
            system = System(os.path.join(directory, "cement.db"))
            system.register_operation(run_demo.PARTITION, run_demo.OPERATION)
            initial = []
            for filename in ("layout_a_progress_note_01.txt", "layout_a_progress_note_02.txt"):
                ident = system.submit_proposal(run_demo.PARTITION, run_demo.OPERATION,
                    {"document": _document(filename)}, candidate=Candidate(output=narrow, provenance={}))
                initial.append(ident)
            first, _ = run_demo.learning_pass(system, run=1)
            # One old narrow output, one pending narrow output, and one complete
            # output must all become the same merged plan without extra support.
            for filename, output in (("layout_a_progress_note_03.txt", narrow),
                                     ("layout_a_progress_note_01.txt", full)):
                system.submit_proposal(run_demo.PARTITION, run_demo.OPERATION,
                    {"document": _document(filename)}, candidate=Candidate(output=output, provenance={}))
            second, _ = run_demo.learning_pass(system, run=2)
            rows = system.examples(run_demo.PARTITION, run_demo.OPERATION)
            active = [row for row in rows if row["superseded_by"] is None]
            self.assertEqual(len(active), 4)
            self.assertEqual(sum(row["supersedes_example_id"] is not None for row in active), 2)
            self.assertEqual({row["reviewer"] for row in active}, {"learning-pass"})
            self.assertEqual(len({_canonical_bytes(row["output"]) for row in active}), 1)
            self.assertEqual(pipeline.apply_plan(active[0]["output"],
                             _document("layout_a_progress_note_03.txt")),
                             EXPECTED_OUTPUTS["layout_a_progress_note_03.txt"])
            self.assertNotEqual(first.function_hash, second.function_hash)
            self.assertEqual(system.switch(run_demo.PARTITION, run_demo.OPERATION).mode, "off")

    def test_learning_pass_extends_the_program_from_unprojected_retained_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            system = System(os.path.join(directory, "cement.db"),
                            candidate_source=plan_adapter.PlanProposer())
            system.register_operation(run_demo.PARTITION, run_demo.OPERATION)
            for filename in SEED_DOCUMENTS[:2]:
                system.propose(run_demo.PARTITION, run_demo.OPERATION, {"document": _document(filename)})
            first, _ = run_demo.learning_pass(system, run=1)
            for filename in SEED_DOCUMENTS[2:]:
                system.propose(run_demo.PARTITION, run_demo.OPERATION, {"document": _document(filename)})
            work = system.learning_cases(run_demo.PARTITION, run_demo.OPERATION)
            self.assertEqual(len(work["unprojected"]["proposal_ids"]), 2)
            second, _ = run_demo.learning_pass(system, run=2)
            self.assertEqual((len(first.input_hashes), len(second.input_hashes)), (1, 2))
            self.assertEqual(len(second.value["projection"]["layouts"]), 2)

    def test_main_runs_learning_switch_and_rollback_on_raw_documents(self) -> None:
        records = []
        names = ("propose", "learning_cases", "review", "test_projection", "set_projection", "compile",
                 "verify_drafts", "promote_function", "set_switch", "resolve",
                 "function_versions", "diff_versions", "serving")

        def recorder(name, real):
            def call(system, *args, **kwargs):
                result = real(system, *args, **kwargs)
                records.append((name, args, kwargs, result))
                return result
            return call

        with contextlib.ExitStack() as stack:
            for name in names:
                stack.enter_context(mock.patch.object(System, name, recorder(name, getattr(System, name))))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            run_demo.main()

        def calls(name):
            return [row for row in records if row[0] == name]

        proposals = calls("propose")
        self.assertEqual(len(proposals), 7)
        self.assertTrue(all(set(row[1][2]) == {"document"} for row in proposals))
        self.assertEqual({row[2]["reviewer"] for row in calls("review")}, {"learning-pass"})
        self.assertEqual(len(calls("review")), 6)
        self.assertGreaterEqual(len(calls("learning_cases")), 4)
        self.assertEqual(len(calls("test_projection")), 2)
        self.assertEqual(len(calls("set_projection")), 2)
        self.assertEqual([len(row[3].created) for row in calls("compile")], [2, 1])
        self.assertEqual([len(row[3].entries) for row in calls("verify_drafts")], [2, 1])
        self.assertEqual(len(calls("promote_function")), 2)
        self.assertEqual({row[2]["promoted_by"] for row in calls("promote_function")}, {"learning-pass"})
        switches = calls("set_switch")
        self.assertEqual({row[2]["actor"] for row in switches}, {"person"})
        self.assertEqual([row[2]["mode"] for row in switches], ["follow", "pinned", "follow"])
        resolutions = calls("resolve")
        self.assertEqual([row[3].match is not None and row[3].match.matched
                          for row in resolutions], [False, True, False, False, True])
        # The new patient's input never became a retained proposal.
        self.assertNotIn(resolutions[1][1][2], [row[1][2] for row in proposals])
        (diff,) = [row[3] for row in calls("diff_versions")]
        self.assertEqual((len(diff.added), diff.removed, diff.changed), (1, (), ()))
        self.assertEqual(switches[1][2]["function_hash"], diff.from_function_hash)
        versions = calls("function_versions")[-1][3]
        self.assertEqual(len(versions.versions), 2)
        self.assertEqual(sum(version.selected for version in versions.versions), 1)
        serving = calls("serving")[-1][3]
        self.assertEqual(serving[0].mode, "follow")
        self.assertEqual(serving[1].function_hash, diff.to_function_hash)


class TranscriptUpdaterTests(unittest.TestCase):
    def test_updater_changes_only_transcript_and_is_idempotent(self) -> None:
        script = EXAMPLE_DIR.parents[1] / ".agent/decisions/m3u8-transcript.py"
        regenerate = runpy.run_path(str(script))["regenerate"]
        original = "Before.\n\n```text\nold output\n```\n\nAfter.\n"
        output = "artifact art_" + "a" * 32 + "\nhash " + "b" * 64 + "\n"
        expected = "Before.\n\n```text\nartifact art_<hex>\nhash <function-hash>\n```\n\nAfter.\n"
        changed = regenerate(original, output)
        self.assertEqual(changed, expected)
        self.assertEqual(regenerate(changed, output), changed)
        for invalid in (output + "art_" + "c" * 32, output.replace("b" * 64, "missing")):
            with self.subTest(output=invalid), self.assertRaises(ValueError):
                regenerate(original, invalid)
        with self.assertRaises(ValueError):
            regenerate(original + "```text\nsecond\n```\n", output)


if __name__ == "__main__":
    unittest.main()
