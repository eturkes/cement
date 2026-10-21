"""`cement-projection-v1`: a closed, line-oriented recognizer from raw input to an exact case key.

Contract: `.agent/decisions/m45-contract.md` §4. The text rules are explicit ASCII on purpose:
Python 3.11-3.14 ship four Unicode databases (UCD 14.0.0 -> 16.0.0), so `str.isspace`, `lower`
or NFKC would make one key depend on the interpreter. No regex runs on input, nothing is
evaluated, and `work` counts the characters, lines and entries the recognizer touches.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Literal, cast

from .errors import ValidationError
from .json_value import CanonicalJSON, JSONValue, canonicalize

__all__ = [
    "PROJECTION_ABI",
    "Layout",
    "Projection",
    "ProjectionProgram",
    "parse_program",
    "project",
    "structure",
]

PROJECTION_ABI = "cement-projection-v1"
PROGRAM_MAX_BYTES = 64 * 1024
MAX_LAYOUTS = 1_000
MAX_ENTRIES = 256
MAX_KEEP = 32
MAX_FIELD = 128
MAX_LITERAL = 256

Reason = Literal["input", "text", "layout", "key"]

_FIELD_CHARS = frozenset(string.ascii_letters + string.digits + "_.-")
_LITERAL_FORBIDDEN = frozenset(
    [chr(code) for code in (*range(0x20), *range(0x7F, 0xA0))] + ["\u2028", "\u2029"]
)
# Input lines keep TAB: it is the one control character the grammar trims and partitions around.
_TEXT_FORBIDDEN = _LITERAL_FORBIDDEN - {"\t"}
_EDGE = " \t"


@dataclass(frozen=True, slots=True)
class Layout:
    name: str
    title: str
    entries: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ProjectionProgram:
    text: str
    keep: tuple[str, ...]
    layouts: tuple[Layout, ...]
    canonical: CanonicalJSON
    program_hash: str


@dataclass(frozen=True, slots=True)
class Projection:
    matched: bool
    key: CanonicalJSON | None
    reason: Reason | None
    work: int


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        raise ValidationError(f"{label} must be an object with keys {sorted(expected)!r}")
    return value


def _field(value: object, label: str) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= MAX_FIELD
        or any(char not in _FIELD_CHARS for char in value)
    ):
        raise ValidationError(f"{label} must be 1-{MAX_FIELD} ASCII letters, digits, '_', '.', '-'")
    return value


def _literal(value: object, label: str, *, colon_free: bool) -> str:
    if type(value) is not str or not 1 <= len(value) <= MAX_LITERAL:
        raise ValidationError(f"{label} must be a string of 1-{MAX_LITERAL} characters")
    if any(char in _LITERAL_FORBIDDEN or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValidationError(f"{label} holds a control character or a lone surrogate")
    if value[0] in _EDGE or value[-1] in _EDGE:
        raise ValidationError(f"{label} must not start or end with an ASCII space or tab")
    if colon_free and ":" in value:
        raise ValidationError(f"{label} must not contain ':'")
    return value


def _entry(value: object, label: str) -> tuple[str, str]:
    if type(value) is not dict or len(value) != 1 or next(iter(value)) not in {"label", "section"}:
        raise ValidationError(f"{label} must be exactly {{'label': K}} or {{'section': H}}")
    kind = next(iter(value))
    return kind, _literal(value[kind], f"{label} {kind}", colon_free=True)


def parse_program(value: object) -> ProjectionProgram:
    """Validate one program object; every rule violation raises `ValidationError` naming it."""

    root = _exact_keys(value, {"abi", "text", "keep", "layouts"}, "projection program")
    if root["abi"] != PROJECTION_ABI:
        raise ValidationError(f"projection abi must be {PROJECTION_ABI!r}")
    text = _field(root["text"], "projection text")
    raw_keep = root["keep"]
    if type(raw_keep) is not list or len(raw_keep) > MAX_KEEP:
        raise ValidationError(f"projection keep must be an array of at most {MAX_KEEP} fields")
    keep = tuple(_field(item, "projection keep field") for item in raw_keep)
    if list(keep) != sorted(set(keep)):
        raise ValidationError("projection keep fields must be sorted and unique")
    if text in keep:
        raise ValidationError("projection text field must not also be kept")
    raw_layouts = root["layouts"]
    if type(raw_layouts) is not list or not 1 <= len(raw_layouts) <= MAX_LAYOUTS:
        raise ValidationError(f"projection layouts must be an array of 1-{MAX_LAYOUTS}")
    layouts: list[Layout] = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for index, raw_layout in enumerate(raw_layouts):
        layout = _exact_keys(raw_layout, {"name", "title", "entries"}, f"projection layout {index}")
        name = _literal(layout["name"], f"layout {index} name", colon_free=False)
        title = _literal(layout["title"], f"layout {index} title", colon_free=False)
        raw_entries = layout["entries"]
        if type(raw_entries) is not list or not 1 <= len(raw_entries) <= MAX_ENTRIES:
            raise ValidationError(f"layout {index} entries must be an array of 1-{MAX_ENTRIES}")
        entries = tuple(
            _entry(item, f"layout {index} entry {position}")
            for position, item in enumerate(raw_entries)
        )
        identity = (title, entries)
        if identity in seen:
            raise ValidationError(f"layout {index} repeats an earlier layout's title + entries")
        seen.add(identity)
        layouts.append(Layout(name=name, title=title, entries=entries))
    canonical = canonicalize(value, max_bytes=PROGRAM_MAX_BYTES)
    return ProjectionProgram(
        text=text,
        keep=keep,
        layouts=tuple(layouts),
        canonical=canonical,
        program_hash=canonical.digest,
    )


def _label(line: str) -> tuple[str, str] | None:
    key, separator, remainder = line.partition(":")
    key = key.strip(_EDGE)
    if not separator or not key:
        return None
    return key, remainder


def _structure(text: str) -> tuple[tuple[str, tuple[tuple[str, str], ...]] | None, int]:
    work = len(text)
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.rstrip(_EDGE)
        work += len(raw) + 1
        if any(char in _TEXT_FORBIDDEN for char in line):
            return None, work
        lines.append(line)
    blocks: list[list[str]] = [[]]
    for line in lines:
        work += 1
        if line:
            blocks[-1].append(line)
        elif blocks[-1]:
            blocks.append([])
    if not blocks[-1]:
        blocks.pop()
    if not blocks:
        return None, work
    title, *header = blocks[0]
    pairs: list[tuple[str, str]] = []
    for line in header:
        work += len(line)
        label = _label(line)
        if label is None:
            return None, work
        pairs.append(("label", label[0]))
    for block in blocks[1:]:
        work += len(block[0])
        leader = _label(block[0])
        if leader is None:
            return None, work
        if not leader[1].strip(_EDGE):
            if len(block) < 2:
                return None, work
            for body in block[1:]:
                work += len(body)
                if ":" in body:
                    return None, work
            pairs.append(("section", leader[0]))
            continue
        pairs.append(("label", leader[0]))
        for line in block[1:]:
            work += len(line)
            label = _label(line)
            if label is None:
                return None, work
            pairs.append(("label", label[0]))
    return (title, tuple(pairs)), work


def structure(text: str) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    """Steps 2-4 alone: the title and its structure pairs, or `None` where the grammar refuses."""

    return _structure(text)[0]


def project(program: ProjectionProgram, value: JSONValue) -> Projection:
    """Map one canonical-JSON input to its case key, or name why it has none. Total."""

    if (
        type(value) is not dict
        or set(value) != {program.text, *program.keep}
        or type(value[program.text]) is not str
    ):
        return Projection(matched=False, key=None, reason="input", work=0)
    text = value[program.text]
    assert type(text) is str  # noqa: S101 — narrowing only: checked on the line above
    parsed, work = _structure(text)
    if parsed is None:
        return Projection(matched=False, key=None, reason="text", work=work)
    title, pairs = parsed
    matched = False
    for layout in program.layouts:
        if layout.title != title:
            continue
        work += min(len(layout.entries), len(pairs))
        if layout.entries == pairs:
            matched = True
            break
    if not matched:
        return Projection(matched=False, key=None, reason="layout", work=work)
    key_value: dict[str, JSONValue] = {
        "form": {"title": title, "structure": [[kind, key] for kind, key in pairs]},
        "keep": {field: value[field] for field in program.keep},
    }
    try:
        key = canonicalize(key_value)
    except ValidationError:
        return Projection(matched=False, key=None, reason="key", work=work)
    return Projection(matched=True, key=key, reason=None, work=work)


# Outside `__all__` on purpose: the two learning surfaces (CLI `learn cases --projectable`, the Open
# WebUI learning tool) share it, while the projection contract API stays the seven pinned names.
def draft_program(inputs: list[JSONValue]) -> dict[str, JSONValue]:
    """One `cement-projection-v1` layout per distinct title + structure of the raw inputs.

    The learning pass decides that an operation is projectable; the program itself is mechanical,
    so it is derived here and nobody copies a label by hand.
    """

    fields = {
        name
        for value in inputs
        if isinstance(value, dict)
        for name, text in value.items()
        if isinstance(text, str)
    }
    if (
        not inputs
        or len(fields) != 1
        or any(
            not isinstance(value, dict)
            or set(value) != fields
            or not all(isinstance(text, str) for text in value.values())
            for value in inputs
        )
    ):
        raise ValidationError("a projection needs inputs that hold exactly one text field")
    (field,) = fields
    layouts: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, JSONValue]] = {}
    for value in inputs:
        parsed = structure(str(cast(dict[str, JSONValue], value)[field]))
        if parsed is None or parsed in layouts:
            continue
        title, pairs = parsed
        layouts[parsed] = {
            "name": title.lower(),
            "title": title,
            "entries": [{kind: key} for kind, key in pairs],
        }
    if not layouts:
        raise ValidationError("no input has a form layout that a projection can read")
    return {
        "abi": PROJECTION_ABI,
        "text": field,
        "keep": [],
        "layouts": [layouts[key] for key in sorted(layouts)],
    }
