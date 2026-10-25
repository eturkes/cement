"""`cement-comparator-v1`: when an LLM's shadow answer agrees with a function's answer.

Contract: `.agent/decisions/p136-cmp-contract.md`. A comparator is a closed list of rules the
learning pass writes; Cement interprets it, evaluates nothing, and walks each value once. Every
field no rule names compares exactly, and no comparator at all means canonical JSON equality.
Decimal quantities compare as scaled integers, so no rounding context enters a verdict. Text rules
are explicit tables, never the interpreter's Unicode data: Python 3.12-3.15 ship different Unicode
databases, and `str.casefold` agrees on U+A7CB / U+0264 under 3.15 but not 3.12, so a host-dependent
fold would flip a verdict (and a proposal) with no change to the comparator's hash.
"""

from __future__ import annotations

import hashlib
import re
import string
from dataclasses import dataclass, field
from typing import Literal, NotRequired, TypedDict, cast

from .errors import ValidationError
from .json_value import JSONValue, canonicalize

__all__ = [
    "COMPARATOR_ABI",
    "Comparator",
    "ComparatorDocument",
    "Comparison",
    "Rule",
    "compare",
    "parse_comparator",
]

COMPARATOR_ABI = "cement-comparator-v1"
MAX_RULES = 256
MAX_SEGMENTS = 32
MAX_SEGMENT = 256
MAX_WITHIN = 32
MAX_PATHS = 20
MAX_BYTES = 65_536  # the canonical document; projection programs share the bound
MAX_PATH_TEXT = 256  # a rendered path; longer ones end in an ellipsis
# A decimal quantity a `tolerance` rule reads; the bound keeps scaled integers small.
MAX_DECIMAL = 64

RuleKind = Literal["ignore", "text", "unordered", "tolerance"]
_KINDS: frozenset[str] = frozenset({"ignore", "text", "unordered", "tolerance"})
_WITHIN = re.compile(r"(0|[1-9][0-9]*)(\.[0-9]+)?")
_DECIMAL = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")
_SIMPLE_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# `text`: these characters collapse to one space; the 26 ASCII capitals fold to lower case.
_SPACES = {ord(character): " " for character in "\t\n\v\f\r\u00a0\u3000"}
_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


class RuleDocument(TypedDict):
    path: list[str]
    rule: str
    within: NotRequired[str]


class ComparatorDocument(TypedDict):
    """The canonical comparator document (rules sorted by path)."""

    abi: str
    rules: list[RuleDocument]


@dataclass(frozen=True, slots=True)
class Rule:
    path: tuple[str, ...]
    rule: RuleKind
    within: str | None = None


@dataclass(frozen=True, slots=True)
class Comparator:
    rules: tuple[Rule, ...]
    comparator_hash: str

    def document(self) -> ComparatorDocument:
        """The canonical form: rules sorted by path."""

        return _document(self.rules)


def _document(rules: tuple[Rule, ...]) -> ComparatorDocument:
    listed: list[RuleDocument] = []
    for rule in rules:
        item: RuleDocument = {"path": list(rule.path), "rule": rule.rule}
        if rule.within is not None:
            item["within"] = rule.within
        listed.append(item)
    return {"abi": COMPARATOR_ABI, "rules": listed}


@dataclass(frozen=True, slots=True)
class Comparison:
    """``agreed`` and, when not, the first ``MAX_PATHS`` disagreeing paths in walk order."""

    agreed: bool
    paths: tuple[str, ...] = ()


class _Any:
    """The array edge `*`; an object member literally named `*` stays an ordinary key."""


_ANY = _Any()


@dataclass(slots=True)
class _Node:
    rule: Rule | None = None
    children: dict[str | _Any, _Node] = field(default_factory=dict)


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"{label} must hold exactly {', '.join(sorted(expected))}")
    return cast(dict[str, object], value)


def _path(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > MAX_SEGMENTS:
        raise ValidationError(f"{label} path must be a list of at most {MAX_SEGMENTS} segments")
    for segment in value:
        if type(segment) is not str or not 1 <= len(segment) <= MAX_SEGMENT:
            raise ValidationError(
                f"{label} path segments must be text of 1 to {MAX_SEGMENT} characters"
            )
    return tuple(cast(list[str], value))


def _rule(value: object, label: str) -> Rule:
    if not isinstance(value, dict) or type(value.get("rule")) is not str:
        raise ValidationError(f"{label} must be an object with a rule")
    kind = cast(str, value["rule"])
    if kind not in _KINDS:
        raise ValidationError(f"{label} rule must be ignore, text, unordered, or tolerance")
    if kind == "tolerance":
        fields = _exact_keys(value, {"path", "rule", "within"}, label)
        within = fields["within"]
        if type(within) is not str or len(within) > MAX_WITHIN or _WITHIN.fullmatch(within) is None:
            raise ValidationError(f"{label} within must be a non-negative decimal string")
        return Rule(_path(fields["path"], label), "tolerance", within)
    fields = _exact_keys(value, {"path", "rule"}, label)
    return Rule(_path(fields["path"], label), cast(RuleKind, kind))


def parse_comparator(value: object) -> Comparator:
    """Validate an untrusted comparator document (grammar only; ``System.set_comparator`` adds the
    checks against an operation's examples)."""

    root = _exact_keys(value, {"abi", "rules"}, "comparator")
    if root["abi"] != COMPARATOR_ABI:
        raise ValidationError(f"comparator abi must be {COMPARATOR_ABI}")
    raw = root["rules"]
    if not isinstance(raw, list) or len(raw) > MAX_RULES:
        raise ValidationError(f"comparator rules must be a list of at most {MAX_RULES} rules")
    rules = [_rule(item, f"comparator rule {index}") for index, item in enumerate(raw)]
    seen: dict[tuple[str, ...], int] = {}
    for index, rule in enumerate(rules):
        label = f"comparator rule {index}"
        if rule.path in seen:
            raise ValidationError(f"{label} repeats the path of rule {seen[rule.path]}")
        seen[rule.path] = index
        if rule.rule == "ignore" and not rule.path:
            raise ValidationError(f"{label} ignores the whole answer")
    for index, rule in enumerate(rules):
        for depth in range(len(rule.path)):
            above = seen.get(rule.path[:depth])
            if above is None:
                continue
            kind = rules[above].rule
            if kind in ("ignore", "text", "tolerance"):
                raise ValidationError(
                    f"comparator rule {index} sits under a {kind} rule (rule {above})"
                )
            if kind == "unordered" and rule.rule == "tolerance":
                raise ValidationError(
                    f"comparator rule {index}: tolerance cannot sit under an unordered rule"
                )
            if kind == "unordered" and rule.path[depth] != "*":
                raise ValidationError(
                    f"comparator rule {index} must pass through * below its unordered rule"
                    f" (rule {above})"
                )
    ordered = tuple(sorted(rules, key=lambda rule: rule.path))
    text = canonicalize(cast(JSONValue, _document(ordered)), max_bytes=MAX_BYTES).text
    digest = hashlib.sha256(text.encode()).hexdigest()
    return Comparator(rules=ordered, comparator_hash=digest)


def _tree(comparator: Comparator) -> _Node:
    root = _Node()
    for rule in comparator.rules:
        node = root
        for segment in rule.path:
            node = node.children.setdefault(_ANY if segment == "*" else segment, _Node())
        node.rule = rule
    return root


_EMPTY = _Node()


def _text(value: str) -> str:
    return " ".join(part for part in value.translate(_SPACES).split(" ") if part).translate(_LOWER)


def _scaled(value: object) -> tuple[int, int] | None:
    """An integer or a decimal string as (digits, scale), or ``None``."""

    if isinstance(value, int) and not isinstance(value, bool):
        return value, 0
    if type(value) is not str or len(value) > MAX_DECIMAL or _DECIMAL.fullmatch(value) is None:
        return None
    whole, _, fraction = value.partition(".")
    return int(whole + fraction), len(fraction)


def _within(left: tuple[int, int], right: tuple[int, int], limit: tuple[int, int]) -> bool:
    scale = max(left[1], right[1], limit[1])
    # `int ** int` types as Any (a negative exponent yields a float); every exponent here is >= 0.
    a, b, c = (number * int(10 ** (scale - places)) for number, places in (left, right, limit))
    return abs(a - b) <= c


def _show(path: str, key: str) -> str:
    return f"{path}.{key}" if _SIMPLE_KEY.fullmatch(key) else f"{path}[{canonicalize(key).text}]"


def _note(out: list[str], path: str) -> None:
    out.append(path if len(path) <= MAX_PATH_TEXT else path[: MAX_PATH_TEXT - 1] + "\u2026")


def _same(left: JSONValue, right: JSONValue) -> bool:
    return canonicalize(left).text == canonicalize(right).text


def _normal(value: JSONValue, node: _Node) -> JSONValue:
    """``value`` with the rules below ``node`` applied (`unordered` arrays sorted); no tolerance
    exists under an unordered rule, so a normal form decides agreement there."""

    rule = node.rule.rule if node.rule is not None else None
    if rule == "ignore":
        # Every element under this path is ignored on both sides, so one constant cannot collide.
        return None
    if rule == "text" and isinstance(value, str):
        return _text(value)
    if isinstance(value, dict):
        return {
            key: _normal(item, node.children.get(key, _EMPTY))
            for key, item in value.items()
            if not _ignored(node, key)
        }
    if isinstance(value, list):
        child = node.children.get(_ANY, _EMPTY)
        items = [_normal(item, child) for item in value]
        if rule == "unordered":
            items.sort(key=lambda item: canonicalize(item).text)
        return items
    return value


def _ignored(node: _Node, key: str) -> bool:
    child = node.children.get(key)
    return child is not None and child.rule is not None and child.rule.rule == "ignore"


def _walk(node: _Node, left: JSONValue, right: JSONValue, path: str, out: list[str]) -> None:
    if len(out) >= MAX_PATHS:
        return
    rule = node.rule
    if rule is not None and rule.rule == "ignore":
        return
    if rule is not None and rule.rule == "text":
        if isinstance(left, str) and isinstance(right, str):
            if _text(left) != _text(right):
                _note(out, path)
        elif not _same(left, right):
            _note(out, path)
        return
    if rule is not None and rule.rule == "tolerance":
        low, high = _scaled(left), _scaled(right)
        limit = _scaled(rule.within)
        if low is not None and high is not None and limit is not None:
            if not _within(low, high, limit):
                _note(out, path)
        elif not _same(left, right):
            _note(out, path)
        return
    if rule is not None and rule.rule == "unordered":
        if isinstance(left, list) and isinstance(right, list):
            child = node.children.get(_ANY, _EMPTY)
            if sorted(canonicalize(_normal(item, child)).text for item in left) != sorted(
                canonicalize(_normal(item, child)).text for item in right
            ):
                _note(out, path)
        elif not _same(left, right):
            _note(out, path)
        return
    if isinstance(left, dict) and isinstance(right, dict):
        keys = sorted(key for key in {*left, *right} if not _ignored(node, key))
        for key in keys:
            if key not in left or key not in right:
                _note(out, _show(path, key))
            else:
                _walk(node.children.get(key, _EMPTY), left[key], right[key], _show(path, key), out)
            if len(out) >= MAX_PATHS:
                return
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            _note(out, path)
            return
        child = node.children.get(_ANY, _EMPTY)
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _walk(child, a, b, f"{path}[{index}]", out)
            if len(out) >= MAX_PATHS:
                return
        return
    if not _same(left, right):
        _note(out, path)


def compare(comparator: Comparator | None, expected: JSONValue, actual: JSONValue) -> Comparison:
    """Whether ``actual`` agrees with ``expected`` under ``comparator`` (``None``: byte-equal
    canonical JSON)."""

    out: list[str] = []
    _walk(_EMPTY if comparator is None else _tree(comparator), expected, actual, "$", out)
    return Comparison(agreed=not out, paths=tuple(out))


def witnesses(value: JSONValue, rule: Rule) -> bool:
    """Whether ``value`` holds a value at ``rule.path`` that the rule applies to: a string for
    `text`, an array for `unordered`, an integer or decimal string for `tolerance`, anything for
    `ignore`."""

    def at(item: JSONValue, path: tuple[str, ...]) -> bool:
        if not path:
            if rule.rule == "text":
                return isinstance(item, str)
            if rule.rule == "unordered":
                return isinstance(item, list)
            if rule.rule == "tolerance":
                return _scaled(item) is not None
            return True
        head, rest = path[0], path[1:]
        if head == "*":
            return isinstance(item, list) and any(at(element, rest) for element in item)
        return isinstance(item, dict) and head in item and at(item[head], rest)

    return at(value, rule.path)


def compared_leaves(comparator: Comparator, value: JSONValue) -> tuple[int, int]:
    """(leaves, leaves outside every ignore rule); a leaf = a scalar or an empty container."""

    def count(node: _Node, item: JSONValue) -> tuple[int, int]:
        if node.rule is not None and node.rule.rule == "ignore":
            total = count(_EMPTY, item)[0]
            return total, 0
        if isinstance(item, dict) and item:
            pairs = [count(node.children.get(key, _EMPTY), child) for key, child in item.items()]
        elif isinstance(item, list) and item:
            child = node.children.get(_ANY, _EMPTY)
            pairs = [count(child, element) for element in item]
        else:
            return 1, 1
        return sum(pair[0] for pair in pairs), sum(pair[1] for pair in pairs)

    return count(_tree(comparator), value)
