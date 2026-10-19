"""Independent §4 reference; deliberately separate from the runtime interpreter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cement_runtime.errors import ValidationError
from cement_runtime.json_value import CanonicalJSON, JSONValue, canonicalize

PROJECTION_ABI = "cement-projection-v1"
_FIELD_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")


@dataclass(frozen=True)
class Layout:
    name: str
    title: str
    entries: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ProjectionProgram:
    text: str
    keep: tuple[str, ...]
    layouts: tuple[Layout, ...]
    canonical: CanonicalJSON
    program_hash: str


@dataclass(frozen=True)
class Projection:
    matched: bool
    key: CanonicalJSON | None
    reason: Literal["input", "text", "layout", "key"] | None
    work: int


def _forbidden(char: str) -> bool:
    n = ord(char)
    return n <= 0x1F or 0x7F <= n <= 0x9F or n in (0x2028, 0x2029) or 0xD800 <= n <= 0xDFFF


def _object(value: object, keys: set[str], rule: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ValidationError(f"{rule}: exact object keys required")
    return value


def _field(value: object, rule: str) -> str:
    if type(value) is not str or not 1 <= len(value) <= 128 or any(c not in _FIELD_CHARS for c in value):
        raise ValidationError(f"{rule}: field name must contain 1-128 ASCII name characters")
    return value


def _literal(value: object, rule: str, *, colon: bool = True) -> str:
    if type(value) is not str or not 1 <= len(value) <= 256:
        raise ValidationError(f"{rule}: literal must contain 1-256 Unicode scalars")
    if any(_forbidden(c) for c in value):
        raise ValidationError(f"{rule}: forbidden character in literal")
    if value != value.strip(" \t"):
        raise ValidationError(f"{rule}: literal has edge ASCII whitespace")
    if not colon and ":" in value:
        raise ValidationError(f"{rule}: colon in label or section literal")
    return value


def parse_program(value: object) -> ProjectionProgram:
    obj = _object(value, {"abi", "text", "keep", "layouts"}, "program")
    if type(obj["abi"]) is not str or obj["abi"] != PROJECTION_ABI:
        raise ValidationError("abi: expected cement-projection-v1")
    text = _field(obj["text"], "text")
    keep = obj["keep"]
    if type(keep) is not list or len(keep) > 32:
        raise ValidationError("keep: array of at most 32 field names required")
    for field in keep:
        _field(field, "keep")
    if keep != sorted(set(keep)):
        raise ValidationError("keep: sorted unique field names required")
    if text in keep:
        raise ValidationError("keep: text field must not occur in keep")
    layouts = obj["layouts"]
    if type(layouts) is not list or not 1 <= len(layouts) <= 1000:
        raise ValidationError("layouts: array of 1-1000 layouts required")
    parsed = []
    identities = set()
    for raw in layouts:
        layout = _object(raw, {"name", "title", "entries"}, "layout")
        name = _literal(layout["name"], "name")
        title = _literal(layout["title"], "title")
        raw_entries = layout["entries"]
        if type(raw_entries) is not list or not 1 <= len(raw_entries) <= 256:
            raise ValidationError("entries: array of 1-256 entries required")
        entries = []
        for entry in raw_entries:
            if type(entry) is not dict or len(entry) != 1 or next(iter(entry)) not in {"label", "section"}:
                raise ValidationError("entry: exactly one label or section key required")
            kind, literal = next(iter(entry.items()))
            entries.append((kind, _literal(literal, kind, colon=False)))
        identity = (title, tuple(entries))
        if identity in identities:
            raise ValidationError("layout identity: duplicate title and normalized entries")
        identities.add(identity)
        parsed.append(Layout(name, title, tuple(entries)))
    canonical = canonicalize(obj, max_bytes=65_536)
    return ProjectionProgram(text, tuple(keep), tuple(parsed), canonical, canonical.digest)


def _analyze(text: str) -> tuple[tuple[str, tuple[tuple[str, str], ...]] | None, int]:
    if type(text) is not str:
        return None, 0
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    work = len(text) + len(raw_lines)
    lines = []
    for raw_line in raw_lines:
        line = raw_line.rstrip(" \t")
        for char in line:
            work += 1
            # MAIN ruling AM2: TAB is ordinary text in input lines (literals still refuse it).
            if _forbidden(char) and char != "\t":
                return None, work
        if line or (lines and lines[-1]):
            lines.append(line)
    if lines and not lines[-1]:
        lines.pop()
    if not lines:
        return None, work
    blocks = [[]]
    for line in lines:
        if line:
            blocks[-1].append(line)
        else:
            blocks.append([])
    title = blocks[0][0]
    entries = []

    def label(line: str) -> tuple[str, str] | None:
        nonlocal work
        work += len(line)
        key, delimiter, value = line.partition(":")
        key = key.strip(" \t")
        if not delimiter or not key:
            return None
        return key, value

    for line in blocks[0][1:]:
        item = label(line)
        if item is None:
            return None, work
        entries.append(("label", item[0]))
    for block in blocks[1:]:
        first = label(block[0])
        if first is None:
            return None, work
        if not first[1].strip(" \t"):
            if len(block) < 2:
                return None, work
            for body in block[1:]:
                work += len(body)
                if ":" in body:
                    return None, work
            entries.append(("section", first[0]))
        else:
            entries.append(("label", first[0]))
            for line in block[1:]:
                item = label(line)
                if item is None:
                    return None, work
                entries.append(("label", item[0]))
    return (title, tuple(entries)), work


def structure(text: str) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    return _analyze(text)[0]


def project(program: ProjectionProgram, value: JSONValue) -> Projection:
    if type(value) is not dict or set(value) != {program.text, *program.keep} or type(value[program.text]) is not str:
        return Projection(False, None, "input", 0)
    parsed, work = _analyze(value[program.text])
    if parsed is None:
        return Projection(False, None, "text", work)
    title, entries = parsed
    matched = False
    for layout in program.layouts:
        if title != layout.title or len(entries) != len(layout.entries):
            continue
        same = True
        for expected, actual in zip(layout.entries, entries):
            work += 1
            if expected != actual:
                same = False
                break
        if same:
            matched = True
            break
    if not matched:
        return Projection(False, None, "layout", work)
    key = {
        "form": {"title": title, "structure": [list(pair) for pair in entries]},
        "keep": {field: value[field] for field in program.keep},
    }
    try:
        canonical = canonicalize(key)
    except ValidationError:
        return Projection(False, None, "key", work)
    return Projection(True, canonical, None, work)
