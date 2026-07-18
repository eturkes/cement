"""Conservative, versioned JSON boundary used by requests and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, TypeAlias

from .errors import ValidationError

JSONScalar: TypeAlias = None | bool | int | str
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

CANONICALIZER = "cement-json-v1"
DEFAULT_MAX_BYTES = 1_048_576
DEFAULT_MAX_DEPTH = 64
DEFAULT_MAX_ITEMS = 100_000
MIN_INTEGER = -(2**63)
MAX_INTEGER = 2**63 - 1


@dataclass(frozen=True, slots=True)
class CanonicalJSON:
    value: JSONValue
    text: str
    digest: str


def _validate(
    value: Any,
    *,
    depth: int,
    max_depth: int,
    remaining_items: list[int],
) -> None:
    if depth > max_depth:
        raise ValidationError(f"JSON exceeds maximum depth {max_depth}")
    if value is None or type(value) is bool or type(value) is str:
        return
    if type(value) is int:
        if not MIN_INTEGER <= value <= MAX_INTEGER:
            raise ValidationError("JSON integer is outside the signed 64-bit range")
        return
    if type(value) is float:
        raise ValidationError("cement-json-v1 supports integers; encode decimals as strings")
    if type(value) is list:
        remaining_items[0] -= len(value)
        if remaining_items[0] < 0:
            raise ValidationError("JSON exceeds maximum container item count")
        for item in value:
            _validate(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                remaining_items=remaining_items,
            )
        return
    if type(value) is dict:
        remaining_items[0] -= len(value)
        if remaining_items[0] < 0:
            raise ValidationError("JSON exceeds maximum container item count")
        for key, item in value.items():
            if type(key) is not str:
                raise ValidationError("JSON object keys must be strings")
            _validate(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                remaining_items=remaining_items,
            )
        return
    raise ValidationError(f"value of type {type(value).__name__!r} is not JSON")


def canonicalize(
    value: Any,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> CanonicalJSON:
    """Validate + serialize without lossy normalization.

    Object order is erased. Unicode is preserved byte-for-byte after UTF-8
    validation. Numeric scope is restricted to signed 64-bit integers; decimal
    quantities must use an application-defined string representation.
    """

    if (
        type(max_bytes) is not int
        or type(max_depth) is not int
        or type(max_items) is not int
        or max_bytes < 1
        or max_depth < 0
        or max_items < 0
    ):
        raise ValueError("JSON limits must be non-negative and max_bytes positive")
    _validate(
        value,
        depth=0,
        max_depth=max_depth,
        remaining_items=[max_items],
    )
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:  # defensive: _validate owns semantics
        raise ValidationError(f"invalid JSON value: {exc}") from exc
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError("JSON strings must contain valid Unicode scalar values") from exc
    if len(encoded) > max_bytes:
        raise ValidationError(f"canonical JSON exceeds {max_bytes} bytes")
    # Round-trip detaches caller-owned mutable containers.
    detached: JSONValue = json.loads(text)
    return CanonicalJSON(
        value=detached,
        text=text,
        digest=hashlib.sha256(encoded).hexdigest(),
    )


def parse_json(
    source: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> CanonicalJSON:
    """Parse strict JSON: duplicate keys and non-finite constants are errors."""

    if not isinstance(source, str):
        raise ValidationError("JSON source must be text")
    if (
        type(max_bytes) is not int
        or type(max_depth) is not int
        or type(max_items) is not int
        or max_bytes < 1
        or max_depth < 0
        or max_items < 0
    ):
        raise ValueError("JSON limits must be non-negative and max_bytes positive")
    try:
        encoded = source.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError("JSON source contains an unpaired Unicode surrogate") from exc
    if len(encoded) > max_bytes:
        raise ValidationError(f"JSON source exceeds {max_bytes} bytes")

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON object key: {key!r}")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise ValidationError(f"non-finite JSON number: {token}")

    def reject_float(token: str) -> None:
        raise ValidationError(
            f"cement-json-v1 rejects decimal/exponent number {token!r}; encode it as a string"
        )

    try:
        value = json.loads(
            source,
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
            parse_float=reject_float,
        )
    except ValidationError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValidationError(f"invalid JSON: {exc}") from exc
    return canonicalize(
        value,
        max_bytes=max_bytes,
        max_depth=max_depth,
        max_items=max_items,
    )


def digest_parts(label: str, *parts: str) -> str:
    """Length-delimited hash; safe against concatenation ambiguity."""

    digest = hashlib.sha256()
    for part in (label, *parts):
        data = part.encode("utf-8")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()
