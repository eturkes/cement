from __future__ import annotations

from copy import deepcopy
import gc
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
from unittest import mock
from typing import Any

import cement_runtime.function as function_module
from cement_runtime import (
    FUNCTION_ABI,
    FUNCTION_ENTRY_SEAL_ABI,
    FUNCTION_MAX_BYTES,
    FUNCTION_MAX_DEPTH,
    FUNCTION_MAX_ENTRIES,
    FUNCTION_MAX_ITEMS,
    FunctionEntry,
    IntegrityError,
    ValidationError,
    build_function,
    evaluate,
    parse_function,
    validate_function,
)
from cement_runtime.artifacts import build_exact_lookup
from cement_runtime.json_value import (
    CANONICALIZER,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
    CanonicalJSON,
    MAX_INTEGER,
    canonicalize,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _flip_digest(value: str) -> str:
    return ("1" if value[0] != "1" else "2") + value[1:]


def _entry(input_value: Any, output_value: Any, *, label: str) -> FunctionEntry:
    return FunctionEntry(
        input=input_value,
        output=output_value,
        artifact_hash=_digest(f"{label}:artifact"),
        evidence_snapshot_hash=_digest(f"{label}:evidence"),
        entry_seal=_digest(f"{label}:entry-seal"),
        report_details_hash=_digest(f"{label}:report-details"),
        report_test_set_hash=_digest(f"{label}:report-tests"),
    )


def _build(entries: Any, *, operation_revision: int = 3):
    return build_function(
        partition="tenant-a",
        operation="echo",
        operation_revision=operation_revision,
        policy_hash=_digest("policy"),
        entries=entries,
    )


def _container_items(value: Any) -> int:
    if type(value) is list:
        return len(value) + sum(_container_items(item) for item in value)
    if type(value) is dict:
        return len(value) + sum(_container_items(item) for item in value.values())
    return 0


def _rehash(document: dict[str, Any]) -> None:
    document.pop("function_hash")
    document["function_hash"] = canonicalize(
        document,
        max_bytes=FUNCTION_MAX_BYTES,
        max_depth=FUNCTION_MAX_DEPTH,
        max_items=FUNCTION_MAX_ITEMS,
    ).digest


class FunctionTests(unittest.TestCase):
    def test_repeat_evaluation_is_byte_identical_and_mutation_isolated(self) -> None:
        bundle = _build(
            (
                _entry(
                    {"x": 1},
                    {"answer": [1, {"stable": True}]},
                    label="repeat",
                ),
            )
        )
        input_json = canonicalize({"x": 1})
        first = evaluate(bundle, input_json=input_json)
        second = evaluate(bundle, input_json=input_json)
        self.assertTrue(first.matched and second.matched)
        self.assertEqual(first.artifact_hash, _digest("repeat:artifact"))
        expected_bytes = canonicalize(second.output).text.encode("utf-8")
        self.assertEqual(canonicalize(first.output).text.encode("utf-8"), expected_bytes)

        first_output = first.output
        if type(first_output) is not dict:
            raise AssertionError("matched output changed type")
        answer = first_output["answer"]
        if type(answer) is not list:
            raise AssertionError("matched answer changed type")
        nested = answer[1]
        if type(nested) is not dict:
            raise AssertionError("nested answer changed type")
        nested["stable"] = False

        third = evaluate(bundle, input_json=input_json)
        self.assertEqual(canonicalize(third.output).text.encode("utf-8"), expected_bytes)
        self.assertEqual(parse_function(bundle.text).text, bundle.text)

    def test_unknown_input_returns_no_match(self) -> None:
        bundle = _build((_entry({"x": 1}, "known", label="known"),))
        result = evaluate(bundle, input_json=canonicalize({"x": 2}))
        self.assertFalse(result.matched)
        self.assertIsNone(result.output)
        self.assertIsNone(result.artifact_hash)

    def test_entry_reordering_keeps_one_hash_and_canonical_document(self) -> None:
        first = _entry({"case": 1}, {"answer": 1}, label="first")
        second = _entry({"case": 2}, {"answer": 2}, label="second")
        forward = _build((first, second))
        reverse = _build((second, first))
        self.assertEqual(forward.function_hash, reverse.function_hash)
        self.assertEqual(forward.text, reverse.text)

        reordered = deepcopy(forward.value)
        reordered_entries = reordered["entries"]
        if type(reordered_entries) is not list:
            raise AssertionError("function entries changed type")
        reordered_entries.reverse()
        validated = validate_function(reordered)
        self.assertEqual(validated.function_hash, forward.function_hash)
        self.assertEqual(validated.text, forward.text)


    def test_function_v1_document_is_explicitly_rejected(self) -> None:
        document = deepcopy(
            _build((_entry({"x": 1}, 1, label="legacy-abi"),)).value
        )
        document["abi"] = "cement-function-v1"
        _rehash(document)
        with self.assertRaisesRegex(ValidationError, "unsupported function ABI"):
            validate_function(document)

    def test_every_document_field_fails_closed_with_typed_errors(self) -> None:
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="fields"),))
        mutations = (
            (
                "root.abi",
                ValidationError,
                lambda doc: doc.__setitem__("abi", "cement-function-v1"),
            ),
            (
                "root.canonicalizer",
                ValidationError,
                lambda doc: doc.__setitem__("canonicalizer", "cement-json-v2"),
            ),
            (
                "root.entries",
                IntegrityError,
                lambda doc: doc.__setitem__("entries", []),
            ),
            (
                "root.function_hash",
                IntegrityError,
                lambda doc: doc.__setitem__(
                    "function_hash", _flip_digest(doc["function_hash"])
                ),
            ),
            (
                "root.scope",
                ValidationError,
                lambda doc: doc.__setitem__("scope", None),
            ),
            (
                "scope.operation",
                IntegrityError,
                lambda doc: doc["scope"].__setitem__("operation", "other"),
            ),
            (
                "scope.operation_revision",
                IntegrityError,
                lambda doc: doc["scope"].__setitem__("operation_revision", 4),
            ),
            (
                "scope.partition",
                IntegrityError,
                lambda doc: doc["scope"].__setitem__("partition", "tenant-b"),
            ),
            (
                "scope.policy_hash",
                IntegrityError,
                lambda doc: doc["scope"].__setitem__(
                    "policy_hash", _flip_digest(doc["scope"]["policy_hash"])
                ),
            ),
            (
                "entry.artifact_hash",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__(
                    "artifact_hash",
                    _flip_digest(doc["entries"][0]["artifact_hash"]),
                ),
            ),
            (
                "entry.evidence_snapshot_hash",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__(
                    "evidence_snapshot_hash",
                    _flip_digest(doc["entries"][0]["evidence_snapshot_hash"]),
                ),
            ),
            (
                "entry.input",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__("input", {"x": 99}),
            ),
            (
                "entry.input_hash",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__(
                    "input_hash", _flip_digest(doc["entries"][0]["input_hash"])
                ),
            ),
            (
                "entry.output",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__(
                    "output", {"answer": 99}
                ),
            ),
            (
                "entry.output_hash",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__(
                    "output_hash", _flip_digest(doc["entries"][0]["output_hash"])
                ),
            ),
            (
                "entry.entry_seal",
                IntegrityError,
                lambda doc: doc["entries"][0].__setitem__(
                    "entry_seal",
                    _flip_digest(doc["entries"][0]["entry_seal"]),
                ),
            ),
            (
                "entry.report",
                ValidationError,
                lambda doc: doc["entries"][0].__setitem__("report", None),
            ),
            (
                "report.details_hash",
                IntegrityError,
                lambda doc: doc["entries"][0]["report"].__setitem__(
                    "details_hash",
                    _flip_digest(doc["entries"][0]["report"]["details_hash"]),
                ),
            ),
            (
                "report.test_set_hash",
                IntegrityError,
                lambda doc: doc["entries"][0]["report"].__setitem__(
                    "test_set_hash",
                    _flip_digest(doc["entries"][0]["report"]["test_set_hash"]),
                ),
            ),
        )
        for label, error, mutate in mutations:
            document = deepcopy(bundle.value)
            mutate(document)
            with self.subTest(field=label), self.assertRaises(error):
                validate_function(document)

    def test_exact_keys_types_bounds_and_digest_syntax_fail_validation(self) -> None:
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="shape"),))
        extra_key_mutations = (
            lambda doc: doc.__setitem__("extra", None),
            lambda doc: doc["scope"].__setitem__("extra", None),
            lambda doc: doc["entries"][0].__setitem__("extra", None),
            lambda doc: doc["entries"][0]["report"].__setitem__("extra", None),
        )
        for index, mutate in enumerate(extra_key_mutations):
            document = deepcopy(bundle.value)
            mutate(document)
            with self.subTest(extra_key_level=index), self.assertRaises(ValidationError):
                validate_function(document)

        invalid_mutations = (
            lambda doc: doc.__setitem__("function_hash", "F" * 64),
            lambda doc: doc["scope"].__setitem__("partition", ""),
            lambda doc: doc["scope"].__setitem__("operation", 1),
            lambda doc: doc["scope"].__setitem__("operation_revision", True),
            lambda doc: doc["scope"].__setitem__("policy_hash", "f" * 63),
            lambda doc: doc["entries"][0].__setitem__("artifact_hash", "bad"),
            lambda doc: doc["entries"][0].__setitem__("input_hash", False),
            lambda doc: doc["entries"][0]["report"].__setitem__(
                "details_hash", "g" * 64
            ),
        )
        for index, mutate in enumerate(invalid_mutations):
            document = deepcopy(bundle.value)
            mutate(document)
            with self.subTest(invalid_value=index), self.assertRaises(ValidationError):
                validate_function(document)

        with self.assertRaises(ValidationError):
            validate_function(bundle.value, expected_function_hash="bad")
        with self.assertRaises(IntegrityError):
            validate_function(bundle.value, expected_function_hash=_digest("different"))
        with self.assertRaises(ValidationError):
            _build(({},))
        with self.assertRaises(ValidationError):
            _build(None)

    def test_duplicate_input_hash_rejects_before_evaluation(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate input_hash"):
            _build(
                (
                    _entry({"same": True}, 1, label="duplicate-a"),
                    _entry({"same": True}, 2, label="duplicate-b"),
                )
            )

    def test_digest_collision_path_requires_canonical_input_text(self) -> None:
        input_json = canonicalize({"x": 1})
        bundle = _build((_entry(input_json.value, "matched", label="collision"),))
        different = canonicalize({"x": 2})
        collision = CanonicalJSON(
            value=different.value,
            text=different.text,
            digest=input_json.digest,
        )
        result = evaluate(bundle, input_json=collision)
        self.assertFalse(result.matched)
        self.assertIsNone(result.output)

        neighbouring = CanonicalJSON(
            value=input_json.value,
            text=input_json.text,
            digest="0" * 64,
        )
        self.assertLess(neighbouring.digest, input_json.digest)
        neighbour_result = evaluate(bundle, input_json=neighbouring)
        self.assertFalse(neighbour_result.matched)
        self.assertIsNone(neighbour_result.output)

    def test_entry_digest_mismatches_reject_after_outer_rehash(self) -> None:
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="entry-binding"),))
        mutations = (
            ("input", {"x": 99}, "input digest mismatch"),
            ("output", {"answer": 99}, "output digest mismatch"),
        )
        for field, changed, message in mutations:
            document: Any = deepcopy(bundle.value)
            entry = document["entries"][0]
            entry[field] = changed
            _rehash(document)
            with self.subTest(field=field), self.assertRaisesRegex(
                IntegrityError, message
            ):
                validate_function(document)

    def test_revision_signed_64_boundaries_and_scope_precedence(self) -> None:
        minimum = _build((_entry(1, 1, label="revision-min"),), operation_revision=1)
        self.assertEqual(validate_function(minimum.value).function_hash, minimum.function_hash)
        with self.assertRaisesRegex(ValidationError, "operation revision"):
            _build((_entry(0, 0, label="revision-zero"),), operation_revision=0)

        maximum = _build(
            (_entry(MAX_INTEGER, MAX_INTEGER, label="revision-max"),),
            operation_revision=MAX_INTEGER,
        )
        self.assertEqual(validate_function(maximum.value).function_hash, maximum.function_hash)

        overflow: Any = deepcopy(minimum.value)
        overflow["scope"]["operation_revision"] = MAX_INTEGER + 1
        overflow["entries"][0]["artifact_hash"] = "bad"
        with self.assertRaisesRegex(ValidationError, "operation revision"):
            validate_function(overflow)

    def test_validator_entries_type_and_count_taxonomy(self) -> None:
        singleton = _build((_entry(1, 1, label="validator-type"),))
        wrong_type: Any = deepcopy(singleton.value)
        wrong_type["entries"] = tuple(wrong_type["entries"])
        with self.assertRaisesRegex(ValidationError, "entries must be an array"):
            validate_function(wrong_type)

        pair = _build(
            (
                _entry(1, 1, label="validator-count-a"),
                _entry(2, 2, label="validator-count-b"),
            )
        )
        with mock.patch.object(function_module, "FUNCTION_MAX_ENTRIES", 1):
            with self.assertRaisesRegex(ValidationError, "function exceeds 1 entries"):
                validate_function(pair.value)

    def test_builder_limit_stops_at_first_excess_item(self) -> None:
        entry = _entry(1, 1, label="builder-count")
        requested = 0

        def entries():
            nonlocal requested
            while True:
                requested += 1
                yield entry

        with mock.patch.object(function_module, "FUNCTION_MAX_ENTRIES", 1):
            with self.assertRaisesRegex(ValidationError, "function exceeds 1 entries"):
                _build(entries())
        self.assertEqual(requested, 2)

    def test_builder_rejects_function_entry_subclasses(self) -> None:
        class FunctionEntrySubclass(FunctionEntry):
            pass

        base = _entry(1, 1, label="entry-subclass")
        subclass = FunctionEntrySubclass(
            input=base.input,
            output=base.output,
            artifact_hash=base.artifact_hash,
            evidence_snapshot_hash=base.evidence_snapshot_hash,
            entry_seal=base.entry_seal,
            report_details_hash=base.report_details_hash,
            report_test_set_hash=base.report_test_set_hash,
        )
        with self.assertRaisesRegex(
            ValidationError, "function entries must be FunctionEntry values"
        ):
            _build((subclass,))

    def test_digest_and_scope_name_boundaries(self) -> None:
        digest_64 = "a" * 64
        valid_entry = FunctionEntry(
            input=1,
            output=1,
            artifact_hash=digest_64,
            evidence_snapshot_hash=digest_64,
            entry_seal=digest_64,
            report_details_hash=digest_64,
            report_test_set_hash=digest_64,
        )
        bounded = build_function(
            partition="p" * 128,
            operation="o" * 128,
            operation_revision=1,
            policy_hash=digest_64,
            entries=(valid_entry,),
        )
        bounded_scope = bounded.value["scope"]
        if type(bounded_scope) is not dict or type(bounded_scope["partition"]) is not str:
            raise AssertionError("function scope changed type")
        self.assertEqual(len(bounded_scope["partition"]), 128)

        overlong_digest = FunctionEntry(
            input=1,
            output=1,
            artifact_hash="a" * 65,
            evidence_snapshot_hash=digest_64,
            entry_seal=digest_64,
            report_details_hash=digest_64,
            report_test_set_hash=digest_64,
        )
        with self.assertRaises(ValidationError):
            build_function(
                partition="tenant",
                operation="echo",
                operation_revision=1,
                policy_hash=digest_64,
                entries=(overlong_digest,),
            )
        for partition in ("p" * 129, "-tenant"):
            with self.subTest(partition=partition), self.assertRaises(ValidationError):
                build_function(
                    partition=partition,
                    operation="echo",
                    operation_revision=1,
                    policy_hash=digest_64,
                    entries=(valid_entry,),
                )

    def test_entries_are_sorted_by_ascending_input_hash(self) -> None:
        values = (0, 1, 2, 3, 10, 11)
        canonical = {value: canonicalize(value) for value in values}
        hash_order = sorted(item.digest for item in canonical.values())
        text_order = [
            canonical[value].digest
            for value in sorted(values, key=lambda value: canonical[value].text)
        ]
        self.assertNotEqual(text_order, hash_order)

        bundle = _build(
            tuple(
                _entry(value, value, label=f"sort-{value}")
                for value in reversed(values)
            )
        )
        entries = bundle.value["entries"]
        if type(entries) is not list:
            raise AssertionError("function entries changed type")
        actual: list[str] = []
        for entry in entries:
            if type(entry) is not dict or type(entry["input_hash"]) is not str:
                raise AssertionError("function entry hash changed type")
            actual.append(entry["input_hash"])
        self.assertEqual(actual, hash_order)

    def test_mutable_value_cannot_redefine_validated_text_or_cases(self) -> None:
        bundle = _build(
            (
                _entry(
                    {"x": 1},
                    {"answer": {"stable": True}},
                    label="mutable-value",
                ),
            )
        )
        original_text = bundle.text
        original_hash = bundle.function_hash
        input_json = canonicalize({"x": 1})

        value_entry = bundle.value["entries"]
        if type(value_entry) is not list or type(value_entry[0]) is not dict:
            raise AssertionError("function entry changed type")
        output = value_entry[0]["output"]
        if type(output) is not dict or type(output["answer"]) is not dict:
            raise AssertionError("function output changed type")
        output["answer"]["stable"] = False

        result = evaluate(bundle, input_json=input_json)
        self.assertEqual(result.output, {"answer": {"stable": True}})
        self.assertEqual(bundle.text, original_text)
        self.assertEqual(bundle.function_hash, original_hash)
        self.assertEqual(
            parse_function(bundle.text, expected_function_hash=original_hash).function_hash,
            original_hash,
        )
        with self.assertRaises(IntegrityError):
            validate_function(bundle.value)

    def test_cross_process_build_is_byte_identical(self) -> None:
        entry = _entry(
            {"x": [1, 2, 3]},
            {"answer": {"ok": True}},
            label="process",
        )
        bundle = _build((entry,))
        source = """
import hashlib
import json
from cement_runtime import FunctionEntry, build_function

def digest(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()

entry = FunctionEntry(
    input={"x": [1, 2, 3]},
    output={"answer": {"ok": True}},
    artifact_hash=digest("process:artifact"),
    evidence_snapshot_hash=digest("process:evidence"),
    entry_seal=digest("process:entry-seal"),
    report_details_hash=digest("process:report-details"),
    report_test_set_hash=digest("process:report-tests"),
)
bundle = build_function(
    partition="tenant-a",
    operation="echo",
    operation_revision=3,
    policy_hash=digest("policy"),
    entries=(entry,),
)
print(json.dumps({"function_hash": bundle.function_hash, "text": bundle.text}, sort_keys=True))
"""
        completed = subprocess.run(
            [sys.executable, "-c", source],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
        )
        observed = json.loads(completed.stdout)
        self.assertEqual(observed["function_hash"], bundle.function_hash)
        self.assertEqual(observed["text"], bundle.text)

    def test_declared_limits_and_inclusive_document_boundaries(self) -> None:
        self.assertEqual(FUNCTION_ABI, "cement-function-v2")
        self.assertEqual(
            FUNCTION_ENTRY_SEAL_ABI,
            "cement-function-entry-seal-v1",
        )
        self.assertEqual(FUNCTION_MAX_BYTES, 64 * DEFAULT_MAX_BYTES)
        self.assertEqual(FUNCTION_MAX_ENTRIES, 50_000)
        self.assertEqual(FUNCTION_MAX_ITEMS, 10 * DEFAULT_MAX_ITEMS)
        self.assertEqual(FUNCTION_MAX_DEPTH, DEFAULT_MAX_DEPTH + 3)

        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="limits"),))
        byte_count = len(bundle.text.encode("utf-8"))
        with mock.patch.object(function_module, "FUNCTION_MAX_BYTES", byte_count):
            self.assertEqual(validate_function(bundle.value).text, bundle.text)
        with mock.patch.object(function_module, "FUNCTION_MAX_BYTES", byte_count - 1):
            with self.assertRaises(ValidationError):
                validate_function(bundle.value)

        item_count = _container_items(bundle.value)
        with mock.patch.object(function_module, "FUNCTION_MAX_ITEMS", item_count):
            self.assertEqual(validate_function(bundle.value).text, bundle.text)
        with mock.patch.object(function_module, "FUNCTION_MAX_ITEMS", item_count - 1):
            with self.assertRaises(ValidationError):
                validate_function(bundle.value)

    def test_per_value_boundaries_and_depth_67_embedding(self) -> None:
        exact_bytes = "x" * (DEFAULT_MAX_BYTES - 2)
        accepted_bytes = _build((_entry(exact_bytes, None, label="bytes"),))
        self.assertTrue(evaluate(accepted_bytes, input_json=canonicalize(exact_bytes)).matched)
        with self.assertRaises(ValidationError):
            _build((_entry(exact_bytes + "x", None, label="bytes-over"),))
        del accepted_bytes, exact_bytes
        gc.collect()

        exact_items = [0] * DEFAULT_MAX_ITEMS
        accepted_items = _build((_entry(exact_items, None, label="items"),))
        self.assertTrue(evaluate(accepted_items, input_json=canonicalize(exact_items)).matched)
        with self.assertRaises(ValidationError):
            _build((_entry(exact_items + [0], None, label="items-over"),))
        del accepted_items, exact_items
        gc.collect()

        depth_64: Any = 0
        for _ in range(DEFAULT_MAX_DEPTH):
            depth_64 = [depth_64]
        deep_bundle = _build((_entry(depth_64, None, label="depth"),))
        self.assertEqual(parse_function(deep_bundle.text).function_hash, deep_bundle.function_hash)
        with self.assertRaises(ValidationError):
            canonicalize(
                deep_bundle.value,
                max_bytes=FUNCTION_MAX_BYTES,
                max_depth=FUNCTION_MAX_DEPTH - 1,
                max_items=FUNCTION_MAX_ITEMS,
            )
        with self.assertRaises(ValidationError):
            _build((_entry([depth_64], None, label="depth-over"),))

    def test_entry_count_accepts_maximum_and_rejects_one_past(self) -> None:
        provenance_hash = _digest("entry-limit")

        def entries(count: int):
            for index in range(count):
                yield FunctionEntry(
                    input=index,
                    output=index,
                    artifact_hash=provenance_hash,
                    evidence_snapshot_hash=provenance_hash,
                    entry_seal=provenance_hash,
                    report_details_hash=provenance_hash,
                    report_test_set_hash=provenance_hash,
                )

        bundle = _build(entries(FUNCTION_MAX_ENTRIES))
        self.assertEqual(len(bundle.entries), FUNCTION_MAX_ENTRIES)
        self.assertTrue(
            evaluate(
                bundle,
                input_json=canonicalize(FUNCTION_MAX_ENTRIES - 1),
            ).matched
        )
        del bundle
        gc.collect()

        repeated = FunctionEntry(
            input=0,
            output=0,
            artifact_hash=provenance_hash,
            evidence_snapshot_hash=provenance_hash,
            entry_seal=provenance_hash,
            report_details_hash=provenance_hash,
            report_test_set_hash=provenance_hash,
        )
        with self.assertRaises(ValidationError):
            _build(repeated for _ in range(FUNCTION_MAX_ENTRIES + 1))

    def test_real_artifact_round_trip_preserves_output_and_provenance(self) -> None:
        artifact = build_exact_lookup(
            partition="tenant-a",
            operation="extract",
            operation_revision=7,
            input_value={"document": ["a", "b"]},
            output_value={"fields": {"a": 1, "b": 2}},
        )
        entry = FunctionEntry(
            input=artifact.input.value,
            output=artifact.output.value,
            artifact_hash=artifact.digest,
            evidence_snapshot_hash=_digest("artifact:evidence"),
            entry_seal=_digest("artifact:entry-seal"),
            report_details_hash=_digest("artifact:report-details"),
            report_test_set_hash=_digest("artifact:report-tests"),
        )
        bundle = build_function(
            partition="tenant-a",
            operation="extract",
            operation_revision=7,
            policy_hash=_digest("artifact:policy"),
            entries=(entry,),
        )
        parsed = parse_function(
            bundle.text,
            expected_function_hash=bundle.function_hash,
        )
        result = evaluate(parsed, input_json=artifact.input)
        self.assertTrue(result.matched)
        self.assertEqual(result.output, artifact.output.value)
        self.assertEqual(result.artifact_hash, artifact.digest)

    def test_parse_rejects_duplicate_source_object_keys(self) -> None:
        bundle = _build((_entry(1, 2, label="duplicate-key"),))
        source = bundle.text.replace(
            f'"abi":"{FUNCTION_ABI}"',
            f'"abi":"{FUNCTION_ABI}","abi":"{FUNCTION_ABI}"',
            1,
        )
        with self.assertRaisesRegex(ValidationError, "duplicate JSON object key"):
            parse_function(source)

    def test_rewritten_content_with_recomputed_hash_is_a_new_function(self) -> None:
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="rewrite"),))
        rewritten = deepcopy(bundle.value)
        rewritten.pop("function_hash")
        rewritten_scope = rewritten["scope"]
        if type(rewritten_scope) is not dict:
            raise AssertionError("function scope changed type")
        rewritten_scope["partition"] = "tenant-b"
        new_hash = canonicalize(
            rewritten,
            max_bytes=FUNCTION_MAX_BYTES,
            max_depth=FUNCTION_MAX_DEPTH,
            max_items=FUNCTION_MAX_ITEMS,
        ).digest
        rewritten["function_hash"] = new_hash

        validated = validate_function(rewritten)
        self.assertEqual(validated.function_hash, new_hash)
        self.assertNotEqual(validated.function_hash, bundle.function_hash)
        with self.assertRaises(IntegrityError):
            validate_function(
                rewritten,
                expected_function_hash=bundle.function_hash,
            )


if __name__ == "__main__":
    unittest.main()
