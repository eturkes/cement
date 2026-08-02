"""Portable, capability-free exact-function document and evaluator."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass
import re
from typing import Any

from .errors import IntegrityError, ValidationError
from .json_value import (
    CANONICALIZER,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
    CanonicalJSON,
    JSONValue,
    MAX_INTEGER,
    canonicalize,
    parse_json,
)

FUNCTION_ABI = "cement-function-v2"
FUNCTION_ENTRY_SEAL_ABI = "cement-function-entry-seal-v1"
FUNCTION_MAX_BYTES = 64 * DEFAULT_MAX_BYTES
FUNCTION_MAX_ENTRIES = 50_000
FUNCTION_MAX_ITEMS = 10 * DEFAULT_MAX_ITEMS
FUNCTION_MAX_DEPTH = DEFAULT_MAX_DEPTH + 3

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
# Mirrors system.py:57; importing it would pull in store capabilities.
# Keep the grammar synchronized until a pure shared validator is justified.
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionEntry:
    """Exact case plus opaque governance digests verified outside this module."""

    input: JSONValue
    output: JSONValue
    artifact_hash: str
    evidence_snapshot_hash: str
    entry_seal: str
    report_details_hash: str
    report_test_set_hash: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _FunctionCase:
    input: CanonicalJSON
    output: CanonicalJSON
    artifact_hash: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionDocument:
    """Trusted validated state with authoritative portable export in `.text`.

    Produce instances through `build_function`, `validate_function`, or
    `parse_function`. Direct construction or `dataclasses.replace` is trusted-caller
    behavior outside the integrity boundary. `.value` is caller-mutable and cannot
    redefine the validated cases, text, or hash. The unkeyed hash binds normalized
    content, not origin.
    """

    value: dict[str, JSONValue]
    text: str
    function_hash: str
    entries: tuple[_FunctionCase, ...]
    input_hashes: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionMatch:
    """Lookup result; artifact_hash is carried provenance, not verification proof."""

    matched: bool
    output: JSONValue = None
    artifact_hash: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class _NormalizedFunction:
    content: CanonicalJSON
    entries: tuple[_FunctionCase, ...]
    input_hashes: tuple[str, ...]


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValidationError(f"invalid {label}: expected keys {sorted(expected)!r}")
    return value


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValidationError(f"{label} must be a SHA-256 hex digest")
    return value


def _name(value: Any, label: str) -> str:
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise ValidationError(
            f"{label} must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"
        )
    return value


def _normalize(value: Any) -> _NormalizedFunction:
    root = _exact_keys(
        value,
        {"abi", "canonicalizer", "entries", "function_hash", "scope"},
        "function",
    )
    if root["abi"] != FUNCTION_ABI:
        raise ValidationError("unsupported function ABI")
    if root["canonicalizer"] != CANONICALIZER:
        raise ValidationError("unsupported function canonicalizer")

    scope = _exact_keys(
        root["scope"],
        {"operation", "operation_revision", "partition", "policy_hash"},
        "function scope",
    )
    partition = _name(scope["partition"], "function partition")
    operation = _name(scope["operation"], "function operation")
    operation_revision = scope["operation_revision"]
    if (
        type(operation_revision) is not int
        or not 1 <= operation_revision <= MAX_INTEGER
    ):
        raise ValidationError(
            "function operation revision must be a positive signed 64-bit integer"
        )
    policy_hash = _digest(scope["policy_hash"], "function policy_hash")

    raw_entries = root["entries"]
    if type(raw_entries) is not list:
        raise ValidationError("function entries must be an array")
    if len(raw_entries) > FUNCTION_MAX_ENTRIES:
        raise ValidationError(f"function exceeds {FUNCTION_MAX_ENTRIES} entries")

    normalized: list[tuple[str, dict[str, JSONValue], _FunctionCase]] = []
    for index, raw_entry in enumerate(raw_entries):
        entry = _exact_keys(
            raw_entry,
            {
                "artifact_hash",
                "evidence_snapshot_hash",
                "input",
                "input_hash",
                "output",
                "output_hash",
                "entry_seal",
                "report",
            },
            f"function entry {index}",
        )
        artifact_hash = _digest(
            entry["artifact_hash"], f"function entry {index} artifact_hash"
        )
        evidence_snapshot_hash = _digest(
            entry["evidence_snapshot_hash"],
            f"function entry {index} evidence_snapshot_hash",
        )
        input_hash = _digest(
            entry["input_hash"], f"function entry {index} input_hash"
        )
        output_hash = _digest(
            entry["output_hash"], f"function entry {index} output_hash"
        )
        entry_seal = _digest(
            entry["entry_seal"], f"function entry {index} entry_seal"
        )
        report = _exact_keys(
            entry["report"],
            {"details_hash", "test_set_hash"},
            f"function entry {index} report",
        )
        report_details_hash = _digest(
            report["details_hash"],
            f"function entry {index} report details_hash",
        )
        report_test_set_hash = _digest(
            report["test_set_hash"],
            f"function entry {index} report test_set_hash",
        )

        input_json = canonicalize(entry["input"])
        output_json = canonicalize(entry["output"])
        if input_json.digest != input_hash:
            raise IntegrityError(f"function entry {index} input digest mismatch")
        if output_json.digest != output_hash:
            raise IntegrityError(f"function entry {index} output digest mismatch")

        normalized_entry: dict[str, JSONValue] = {
            "artifact_hash": artifact_hash,
            "evidence_snapshot_hash": evidence_snapshot_hash,
            "input": input_json.value,
            "input_hash": input_hash,
            "output": output_json.value,
            "output_hash": output_hash,
            "entry_seal": entry_seal,
            "report": {
                "details_hash": report_details_hash,
                "test_set_hash": report_test_set_hash,
            },
        }
        normalized.append(
            (
                input_hash,
                normalized_entry,
                _FunctionCase(
                    input=input_json,
                    output=output_json,
                    artifact_hash=artifact_hash,
                ),
            )
        )

    input_hashes = [item[0] for item in normalized]
    if len(set(input_hashes)) != len(input_hashes):
        raise ValidationError("function contains duplicate input_hash")
    normalized.sort(key=lambda item: item[0])

    content: dict[str, JSONValue] = {
        "abi": FUNCTION_ABI,
        "canonicalizer": CANONICALIZER,
        "entries": [item[1] for item in normalized],
        "scope": {
            "operation": operation,
            "operation_revision": operation_revision,
            "partition": partition,
            "policy_hash": policy_hash,
        },
    }
    canonical = canonicalize(
        content,
        max_bytes=FUNCTION_MAX_BYTES,
        max_depth=FUNCTION_MAX_DEPTH,
        max_items=FUNCTION_MAX_ITEMS,
    )
    return _NormalizedFunction(
        content=canonical,
        entries=tuple(item[2] for item in normalized),
        input_hashes=tuple(item[0] for item in normalized),
    )


def _document(normalized: _NormalizedFunction) -> FunctionDocument:
    if type(normalized.content.value) is not dict:
        raise AssertionError("canonical function content root changed type")
    value: dict[str, JSONValue] = dict(normalized.content.value)
    value["function_hash"] = normalized.content.digest
    # Content passed this depth ceiling; a root hash sibling cannot deepen it.
    canonical = canonicalize(
        value,
        max_bytes=FUNCTION_MAX_BYTES,
        max_depth=FUNCTION_MAX_DEPTH,
        max_items=FUNCTION_MAX_ITEMS,
    )
    if type(canonical.value) is not dict:
        raise AssertionError("canonical function root changed type")
    return FunctionDocument(
        value=canonical.value,
        text=canonical.text,
        function_hash=normalized.content.digest,
        entries=normalized.entries,
        input_hashes=normalized.input_hashes,
    )


def build_function(
    *,
    partition: str,
    operation: str,
    operation_revision: int,
    policy_hash: str,
    entries: Iterable[FunctionEntry],
) -> FunctionDocument:
    """Build one normalized exact function from caller-supplied cases."""

    try:
        iterator = iter(entries)
    except TypeError as exc:
        raise ValidationError("function entries must be iterable") from exc
    supplied: list[FunctionEntry] = []
    for entry in iterator:
        supplied.append(entry)
        if len(supplied) > FUNCTION_MAX_ENTRIES:
            raise ValidationError(f"function exceeds {FUNCTION_MAX_ENTRIES} entries")

    document_entries: list[JSONValue] = []
    for entry in supplied:
        if type(entry) is not FunctionEntry:
            raise ValidationError("function entries must be FunctionEntry values")
        input_json = canonicalize(entry.input)
        output_json = canonicalize(entry.output)
        document_entries.append(
            {
                "artifact_hash": entry.artifact_hash,
                "evidence_snapshot_hash": entry.evidence_snapshot_hash,
                "input": input_json.value,
                "input_hash": input_json.digest,
                "output": output_json.value,
                "output_hash": output_json.digest,
                "entry_seal": entry.entry_seal,
                "report": {
                    "details_hash": entry.report_details_hash,
                    "test_set_hash": entry.report_test_set_hash,
                },
            }
        )

    raw: dict[str, JSONValue] = {
        "abi": FUNCTION_ABI,
        "canonicalizer": CANONICALIZER,
        "entries": document_entries,
        "function_hash": "0" * 64,
        "scope": {
            "operation": operation,
            "operation_revision": operation_revision,
            "partition": partition,
            "policy_hash": policy_hash,
        },
    }
    return _document(_normalize(raw))


def validate_function(
    value: Any,
    *,
    expected_function_hash: str | None = None,
) -> FunctionDocument:
    """Validate normalized content and hash bindings without proving origin.

    The embedded hash binds the document only to its own normalized content. An
    `expected_function_hash` obtained independently also binds it to the identity
    held by the caller; copying that hash from the same untrusted source adds no
    trust. Neither mode is a signature or establishes origin.
    """

    normalized = _normalize(value)
    root = value  # exact dict established by _normalize
    embedded_hash = _digest(root["function_hash"], "function_hash")
    if embedded_hash != normalized.content.digest:
        raise IntegrityError("function hash mismatch")
    if expected_function_hash is not None:
        expected = _digest(expected_function_hash, "expected_function_hash")
        if expected != normalized.content.digest:
            raise IntegrityError("function does not match expected_function_hash")
    return _document(normalized)


def parse_function(
    source: str,
    *,
    expected_function_hash: str | None = None,
) -> FunctionDocument:
    """Parse untrusted text and apply both validation hash modes.

    Only `parse_json` can reject duplicate source keys. The embedded hash proves
    normalized self-consistency; an independently obtained `expected_function_hash`
    additionally pins caller-held identity. Neither mode proves origin.
    """

    parsed = parse_json(
        source,
        max_bytes=FUNCTION_MAX_BYTES,
        max_depth=FUNCTION_MAX_DEPTH,
        max_items=FUNCTION_MAX_ITEMS,
    )
    return validate_function(
        parsed.value,
        expected_function_hash=expected_function_hash,
    )


def evaluate(
    bundle: FunctionDocument,
    *,
    input_json: CanonicalJSON,
) -> FunctionMatch:
    """Return the exact canonical-input match or an inert miss."""

    index = bisect_left(bundle.input_hashes, input_json.digest)
    if index == len(bundle.input_hashes) or bundle.input_hashes[index] != input_json.digest:
        return FunctionMatch(matched=False)
    entry = bundle.entries[index]
    if entry.input.text != input_json.text:
        return FunctionMatch(matched=False)
    return FunctionMatch(
        matched=True,
        output=parse_json(entry.output.text).value,
        artifact_hash=entry.artifact_hash,
    )
