"""Capability-free artifact IR and its complete interpreter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import IntegrityError, ValidationError
from .json_value import (
    CANONICALIZER,
    DEFAULT_MAX_BYTES,
    CanonicalJSON,
    JSONValue,
    canonicalize,
    digest_parts,
)

ARTIFACT_ABI = "cement-exact-lookup-v1"
RUNTIME_ABI = "cement-runtime-v1"
ARTIFACT_MAX_BYTES = 3 * DEFAULT_MAX_BYTES


@dataclass(frozen=True, slots=True)
class ArtifactDocument:
    value: dict[str, JSONValue]
    text: str
    digest: str
    scope_digest: str
    input: CanonicalJSON
    output: CanonicalJSON


@dataclass(frozen=True, slots=True)
class Execution:
    matched: bool
    output: JSONValue = None


def build_exact_lookup(
    *,
    partition: str,
    operation: str,
    operation_revision: int,
    input_value: JSONValue,
    output_value: JSONValue,
) -> ArtifactDocument:
    document: dict[str, JSONValue] = {
        "abi": ARTIFACT_ABI,
        "behavior": {"op": "return", "value": output_value},
        "scope": {
            "canonicalizer": CANONICALIZER,
            "input": input_value,
            "op": "exact",
            "operation": operation,
            "operation_revision": operation_revision,
            "partition": partition,
        },
    }
    return validate_artifact(document)


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValidationError(f"invalid {label}: expected keys {sorted(expected)!r}")
    return value


def validate_artifact(value: Any) -> ArtifactDocument:
    root = _exact_keys(value, {"abi", "behavior", "scope"}, "artifact")
    if root["abi"] != ARTIFACT_ABI:
        raise ValidationError("unsupported artifact ABI")
    scope = _exact_keys(
        root["scope"],
        {
            "canonicalizer",
            "input",
            "op",
            "operation",
            "operation_revision",
            "partition",
        },
        "artifact scope",
    )
    if scope["canonicalizer"] != CANONICALIZER or scope["op"] != "exact":
        raise ValidationError("unsupported artifact scope")
    if type(scope["partition"]) is not str or type(scope["operation"]) is not str:
        raise ValidationError("artifact partition and operation must be strings")
    if type(scope["operation_revision"]) is not int or scope["operation_revision"] < 1:
        raise ValidationError("artifact operation revision must be a positive integer")
    behavior = _exact_keys(root["behavior"], {"op", "value"}, "artifact behavior")
    if behavior["op"] != "return":
        raise ValidationError("unsupported artifact behavior")
    input_json = canonicalize(scope["input"])
    output_json = canonicalize(behavior["value"])
    canonical = canonicalize(root, max_bytes=ARTIFACT_MAX_BYTES)
    scope_json = canonicalize(scope, max_bytes=2 * DEFAULT_MAX_BYTES)
    if type(canonical.value) is not dict:  # established by _exact_keys
        raise AssertionError("canonical artifact root changed type")
    return ArtifactDocument(
        value=canonical.value,
        text=canonical.text,
        digest=canonical.digest,
        scope_digest=scope_json.digest,
        input=input_json,
        output=output_json,
    )


def execute(
    artifact: ArtifactDocument,
    *,
    partition: str,
    operation: str,
    operation_revision: int,
    input_json: CanonicalJSON,
) -> Execution:
    scope = artifact.value["scope"]
    if type(scope) is not dict:
        raise IntegrityError("validated artifact scope changed type")
    if (
        scope["partition"] != partition
        or scope["operation"] != operation
        or scope["operation_revision"] != operation_revision
        or artifact.input.text != input_json.text
    ):
        return Execution(matched=False)
    return Execution(matched=True, output=artifact.output.value)


def build_digest(
    *,
    artifact_digest: str,
    policy_digest: str,
    evidence_snapshot_digest: str,
    support: int,
    reviewer_count: int,
    span_seconds: int,
) -> str:
    return digest_parts(
        "cement-build-v2",
        RUNTIME_ABI,
        CANONICALIZER,
        artifact_digest,
        policy_digest,
        evidence_snapshot_digest,
        str(support),
        str(reviewer_count),
        str(span_seconds),
    )
