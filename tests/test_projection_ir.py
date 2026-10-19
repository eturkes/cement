"""Contract §4 conformance, generated properties, and independent differential."""

from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import importlib
import inspect
from pathlib import Path
import random
import unittest
from unittest.mock import patch
from typing import Literal, get_type_hints

from cement_runtime.errors import ValidationError
from cement_runtime.json_value import CanonicalJSON, canonicalize
from examples.hospital_ocr.pipeline import layout_signature
from tests import projection_oracle


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "hospital_ocr" / "documents"
TITLES = {
    "layout_a": "PHYSICIAN PROGRESS NOTE",
    "layout_b": "PATIENT INTAKE FORM",
    "layout_c": "LAB RESULT SLIP",
}


def minimal(*, keep=(), entries=None, title="T"):
    return {
        "abi": "cement-projection-v1", "text": "document", "keep": list(keep),
        "layouts": [{"name": "n", "title": title, "entries": entries or [{"label": "A"}]}],
    }


def corpus():
    documents = [(p.name, p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.txt"))]
    layouts = {}
    for name, text in documents:
        title = TITLES[name[:8]]
        pairs = layout_signature(text)["structure"]
        layouts[title] = {
            "name": name, "title": title,
            "entries": [{item["kind"]: item["key"]} for item in pairs],
        }
    spec = minimal(keep=("fields",))
    spec["layouts"] = list(layouts.values())
    return spec, documents


def expected_key(title, pairs, keep=None):
    return canonicalize({"form": {"title": title, "structure": [list(p) for p in pairs]}, "keep": keep or {}})


def nested(depth):
    value = 0
    for _ in range(depth):
        value = [value]
    return value


def replace_path(value, path, replacement):
    value = deepcopy(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    return value


def generated_documents(text, seed):
    """Bounded grammar generator: every label/body position, then structural edits."""
    rng = random.Random(seed)
    blocks = text.rstrip("\n").split("\n\n")
    payloads = ["", " ", "v:with:colons", "é文🙂", "\u00a0", "\u2003", "e\u0301"]
    payloads += ["".join(rng.choice("aZ09 é文:.-") for _ in range(rng.randrange(1, 60))) for _ in range(16)]
    for b, block in enumerate(blocks):
        lines = block.split("\n")
        is_section = b > 0 and not lines[0].partition(":")[2].strip(" \t")
        for i, line in enumerate(lines):
            if b == 0 and i == 0:
                continue
            if is_section and i == 0:
                continue
            for payload in payloads:
                if is_section:
                    payload = payload.replace(":", "x")
                    if not payload.rstrip(" \t"):
                        continue
                    replacement = payload
                else:
                    if b > 0 and not payload.strip(" \t"):
                        continue
                    replacement = line.partition(":")[0] + ":" + payload
                changed = lines.copy()
                changed[i] = replacement
                new_blocks = blocks.copy()
                new_blocks[b] = "\n".join(changed)
                yield "value", "\n\n".join(new_blocks)
    lines = text.rstrip("\n").split("\n")
    positions = [i for i, line in enumerate(lines) if i == 0 or ":" in line]
    for i in positions:
        yield "structural", "\n".join(lines[:i] + lines[i + 1:])
        yield "structural", "\n".join(lines[:i] + [lines[i]] + lines[i:])
        changed = lines.copy()
        changed[i] = "x" + changed[i]
        yield "structural", "\n".join(changed)
    for left, right in zip(positions, positions[1:]):
        changed = lines.copy()
        changed[left], changed[right] = changed[right], changed[left]
        yield "structural", "\n".join(changed)
    yield "structural", text + "\nUnseen: x\n"
    for ending in ("\n", "\r\n", "\r"):
        yield "equivalent", ending * 3 + ending.join(line + " \t" for line in lines) + ending * 4
    for char in ("\x00", "\x1f", "\x7f", "\x85", "\x9f", "\u2028", "\u2029", "\x0b"):
        yield "invalid", text.replace(":", ":v" + char + "v", 1)
    yield "value", text.replace(":", ":v\tv", 1)  # MAIN ruling AM2: TAB is value text


class BoundMixin:
    module_name = ""

    def setUp(self):
        self.impl = importlib.import_module(self.module_name)

    def matched(self, program, value):
        canonicalize(value)
        result = self.impl.project(program, value)
        self.assertIs(type(result.matched), bool)
        self.assertTrue(result.matched, result.reason)
        self.assertIsNone(result.reason)
        self.assertIsInstance(result.key, CanonicalJSON)
        self.assertIs(type(result.work), int)
        self.assertGreaterEqual(result.work, 0)
        self.assertEqual(result.key, canonicalize(result.key.value))
        self.bound(program, value[program.text], result)
        return result

    def refused(self, program, value, reason):
        canonicalize(value)
        result = self.impl.project(program, value)
        self.assertIs(result.matched, False)
        self.assertIsNone(result.key)
        self.assertEqual(result.reason, reason)
        self.assertIs(type(result.work), int)
        self.assertGreaterEqual(result.work, 0)
        if type(value) is dict and type(value.get(program.text)) is str:
            self.bound(program, value[program.text], result)
        return result

    def invalid(self, value, *rule_words):
        with self.assertRaises(ValidationError) as raised:
            self.impl.parse_program(value)
        message = str(raised.exception).lower()
        self.assertTrue(message)
        if rule_words:
            self.assertTrue(any(word in message for word in rule_words), message)

    def bound(self, program, text, result):
        lines = len(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
        limit = 4 * len(text) + 2 * lines + sum(len(layout.entries) for layout in program.layouts)
        self.assertIs(type(result.work), int)
        self.assertGreaterEqual(result.work, 0)
        self.assertLessEqual(result.work, limit)
        if result.matched:
            self.assertGreaterEqual(result.work, len(text))


class ApiMixin(BoundMixin):
    def test_a1_api_signatures_and_annotations(self):
        self.assertEqual(self.impl.PROJECTION_ABI, "cement-projection-v1")
        shapes = {"parse_program": ("value",), "project": ("program", "value"), "structure": ("text",)}
        for name, params in shapes.items():
            with self.subTest(name=name):
                function = getattr(self.impl, name)
                signature = inspect.signature(function)
                self.assertEqual(tuple(signature.parameters), params)
                for parameter in signature.parameters.values():
                    self.assertIs(parameter.kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    self.assertIsNot(parameter.annotation, inspect.Parameter.empty)
                self.assertIsNot(signature.return_annotation, inspect.Signature.empty)
        self.assertIs(get_type_hints(self.impl.parse_program)["return"], self.impl.ProjectionProgram)
        self.assertIs(get_type_hints(self.impl.parse_program)["value"], object)
        self.assertIs(get_type_hints(self.impl.project)["program"], self.impl.ProjectionProgram)
        self.assertIs(get_type_hints(self.impl.project)["return"], self.impl.Projection)
        self.assertEqual(get_type_hints(self.impl.structure), {
            "text": str, "return": tuple[str, tuple[tuple[str, str], ...]] | None,
        })

    def test_a1_frozen_dataclasses_and_exact_fields(self):
        specs = {
            "Layout": {"name": str, "title": str, "entries": tuple[tuple[str, str], ...]},
            "ProjectionProgram": {"text": str, "keep": tuple[str, ...], "layouts": tuple[self.impl.Layout, ...],
                                  "canonical": CanonicalJSON, "program_hash": str},
            "Projection": {"matched": bool, "key": CanonicalJSON | None,
                           "reason": Literal["input", "text", "layout", "key"] | None, "work": int},
        }
        program = self.impl.parse_program(minimal())
        instances = {"ProjectionProgram": program, "Layout": program.layouts[0],
                     "Projection": self.matched(program, {"document": "T\nA:v"})}
        for name, expected in specs.items():
            with self.subTest(name=name):
                cls = getattr(self.impl, name)
                self.assertTrue(is_dataclass(cls))
                self.assertEqual([f.name for f in fields(cls)], list(expected))
                self.assertEqual(get_type_hints(cls), expected)
                self.assertIs(cls.__dataclass_params__.frozen, True)
                instance = instances[name]
                self.assertIs(type(instance), cls)
                for field in expected:
                    with self.assertRaises(FrozenInstanceError):
                        setattr(instance, field, getattr(instance, field))

    def test_a1_program_canonical_digest_and_detachment(self):
        raw = minimal(keep=("a", "z"), entries=[{"section": "H"}, {"label": "A"}])
        want = canonicalize(raw)
        parsed = self.impl.parse_program(raw)
        self.assertEqual(parsed.canonical, want)
        self.assertEqual(parsed.program_hash, want.digest)
        self.assertEqual(parsed.text, "document")
        self.assertEqual(parsed.keep, ("a", "z"))
        self.assertEqual(parsed.layouts[0].entries, (("section", "H"), ("label", "A")))
        raw["layouts"][0]["title"] = "changed"
        raw["keep"].append("zz")
        self.assertEqual(parsed.canonical, want)
        self.assertEqual(parsed.layouts[0].title, "T")
        reversed_keys = dict(reversed(list(want.value.items())))
        self.assertEqual(self.impl.parse_program(reversed_keys).program_hash, parsed.program_hash)


class ValidationMixin(BoundMixin):
    def test_v1_exact_keys_at_every_object_node(self):
        base = minimal()
        self.impl.parse_program(base)
        for path in ((), ("layouts", 0), ("layouts", 0, "entries", 0)):
            node = base
            for part in path:
                node = node[part]
            for key in node:
                replacement = {k: v for k, v in node.items() if k != key}
                with self.subTest(path=path, removed=key):
                    self.invalid(replace_path(base, path, replacement) if path else replacement)
            for extra in ("extra", 1):
                replacement = dict(node)
                replacement[extra] = "x"
                with self.subTest(path=path, extra=extra):
                    self.invalid(replace_path(base, path, replacement) if path else replacement)
        for entry in ({}, {"kind": "A"}, {"label": "A", "section": "H"}):
            self.invalid(replace_path(base, ("layouts", 0, "entries", 0), entry))

    def test_v1_exact_types_at_every_node(self):
        base = minimal(keep=("k",))
        paths = [(), ("abi",), ("text",), ("keep",), ("keep", 0), ("layouts",),
                 ("layouts", 0), ("layouts", 0, "name"), ("layouts", 0, "title"),
                 ("layouts", 0, "entries"), ("layouts", 0, "entries", 0),
                 ("layouts", 0, "entries", 0, "label")]
        wrong = (None, True, 0, 1.5, "x", [], {}, (), b"x")
        for path in paths:
            original = base
            for key in path:
                original = original[key]
            for value in wrong:
                if type(value) is type(original):
                    continue
                with self.subTest(path=path, type=type(value).__name__):
                    self.invalid(replace_path(base, path, value) if path else value)
        section = replace_path(base, ("layouts", 0, "entries", 0), {"section": "H"})
        for value in wrong:
            if type(value) is not str:
                self.invalid(replace_path(section, ("layouts", 0, "entries", 0, "section"), value))
        for value in ("cement-projection-v2", "CEMENT-PROJECTION-V1", ""):
            self.invalid(replace_path(base, ("abi",), value), "abi", "version")
        for path, value in [(("text",), type("Text", (str,), {})("document")),
                            (("keep",), type("Array", (list,), {})(["k"])),
                            (("layouts", 0), type("Object", (dict,), {})(base["layouts"][0]))]:
            self.invalid(replace_path(base, path, value))

    def test_v2_field_name_domain_and_length_pairs(self):
        for path in (("text",), ("keep", 0)):
            for good in ("x", "A._-09z", "a" * 128):
                self.impl.parse_program(replace_path(minimal(keep=("k",)), path, good))
            for bad in ("", "a" * 129, "a b", "a/b", "a:b", "a\n", "é", "Ａ", "a\x00", "a\t"):
                with self.subTest(path=path, bad=repr(bad)):
                    self.invalid(replace_path(minimal(keep=("k",)), path, bad), "field", "text", "keep", "128")

    def test_v2_keep_sorted_unique_disjoint_and_count_pairs(self):
        for fields_value in ([], [f"k{i:02}" for i in range(32)], ["A", "a"]):
            self.impl.parse_program(minimal(keep=fields_value))
        for fields_value in ([f"k{i:02}" for i in range(33)], ["b", "a"], ["a", "a"], ["document"]):
            with self.subTest(keep=fields_value):
                self.invalid(minimal(keep=fields_value), "keep", "field", "32", "sorted", "unique")

    def test_v3_layout_and_entry_count_pairs(self):
        for count in (1, 1000):
            spec = minimal()
            spec["layouts"] = [{"name": "n", "title": str(i), "entries": [{"label": "A"}]} for i in range(count)]
            self.assertLessEqual(len(canonicalize(spec).text.encode()), 65_536)
            self.assertEqual(len(self.impl.parse_program(spec).layouts), count)
        for count in (0, 1001):
            spec["layouts"] = [{"name": "n", "title": str(i), "entries": [{"label": "A"}]} for i in range(count)]
            self.invalid(spec, "layout", "1000", "1,000")
        for count in (1, 256):
            spec = minimal(entries=[{"label": "A"}] * count)
            self.assertEqual(len(self.impl.parse_program(spec).layouts[0].entries), count)
        for count in (0, 257):
            self.invalid(replace_path(minimal(), ("layouts", 0, "entries"), [{"label": "A"}] * count), "entr", "256")

    def test_v3_layout_identity_ignores_names_preserves_order_and_kind(self):
        base = minimal(entries=[{"label": "A"}, {"section": "H"}])
        duplicate = deepcopy(base["layouts"][0])
        duplicate["name"] = "different display name"
        base["layouts"].append(duplicate)
        self.invalid(base, "duplicate", "identity", "layout")
        for change in ("title", "kind", "order", "literal"):
            spec = deepcopy(base)
            if change == "title":
                spec["layouts"][1]["title"] = "t"
            elif change == "kind":
                spec["layouts"][1]["entries"][0] = {"section": "A"}
            elif change == "order":
                spec["layouts"][1]["entries"].reverse()
            else:
                spec["layouts"][1]["entries"][0] = {"label": "a"}
            self.assertEqual(len(self.impl.parse_program(spec).layouts), 2)
        same_names = minimal()
        same_names["layouts"].append({"name": "n", "title": "U", "entries": [{"label": "A"}]})
        self.impl.parse_program(same_names)

    def test_v4_literal_length_scalar_and_edge_pairs(self):
        for field in ("name", "title", "label", "section"):
            path = ("layouts", 0, field) if field in {"name", "title"} else ("layouts", 0, "entries", 0, field)
            base = minimal(entries=[{field: "A"}]) if field in {"label", "section"} else minimal()
            for value in ("x", "🙂" * 256, "é文", "A B", "\u00a0A\u00a0", "\u2003A\u2003", "\ufeff"):
                self.impl.parse_program(replace_path(base, path, value))
            for value in ("", "🙂" * 257, " A", "A ", "\tA", "A\t", "\ud800", "\udfff"):
                with self.subTest(field=field, bad=repr(value)):
                    self.invalid(replace_path(base, path, value))
            if field in {"label", "section"}:
                self.invalid(replace_path(base, path, "A:B"), "colon", ":", field)
            else:
                self.impl.parse_program(replace_path(base, path, "A:B"))

    def test_v4_every_forbidden_codepoint_at_every_literal_site(self):
        forbidden = [*range(0x20), *range(0x7F, 0xA0), 0x2028, 0x2029]
        for field in ("name", "title", "label", "section"):
            base = minimal(entries=[{field: "A"}]) if field in {"label", "section"} else minimal()
            path = ("layouts", 0, field) if field in {"name", "title"} else ("layouts", 0, "entries", 0, field)
            for codepoint in forbidden:
                with self.subTest(field=field, codepoint=hex(codepoint)):
                    self.invalid(replace_path(base, path, "A" + chr(codepoint) + "B"))
            for codepoint in (0x20, 0x7E, 0xA0, 0x2027, 0x202A, 0x10FFFF):
                self.impl.parse_program(replace_path(base, path, "A" + chr(codepoint) + "B"))

    def test_v5_program_byte_cap_adjacent_pair(self):
        spec = minimal(entries=[{"label": f"L{i:03}" + "x" * 235} for i in range(256)])
        deficit = 65_536 - len(canonicalize(spec).text.encode("utf-8"))
        self.assertGreater(deficit, 0)
        for entry in spec["layouts"][0]["entries"]:
            add = min(deficit, 256 - len(entry["label"]))
            entry["label"] += "x" * add
            deficit -= add
        self.assertEqual(deficit, 0)
        self.assertEqual(len(canonicalize(spec).text.encode()), 65_536)
        self.assertEqual(len(self.impl.parse_program(spec).canonical.text.encode()), 65_536)
        spec["layouts"][0]["name"] += "x"
        self.assertEqual(len(canonicalize(spec).text.encode()), 65_537)
        self.invalid(spec, "byte", "size", "65536", "65,536", "64")


class GrammarMixin(BoundMixin):
    def test_n2_ascii_normalization_equivalences(self):
        text = "T\nA:v\n\nH:\nbody\nsecond"
        want = ("T", (("label", "A"), ("section", "H")))
        self.assertEqual(self.impl.structure(text), want)
        for ending in ("\n", "\r", "\r\n"):
            varied = ending * 3 + ending.join(line + " \t\t " for line in text.split("\n")) + ending * 4
            with self.subTest(ending=repr(ending)):
                self.assertEqual(self.impl.structure(varied), want)
        self.assertEqual(self.impl.structure("T\r\nA:v\r\rH:\nbody\nsecond"), want)
        self.assertEqual(self.impl.structure(text.replace("\n\n", "\n \t\n\n\n")), want)

    def test_n2_forbidden_chars_and_unicode_non_equivalences(self):
        # MAIN ruling AM2: TAB (0x09) is ordinary text inside input lines; its accept half follows.
        for cp in [*range(0x20), *range(0x7F, 0xA0), 0x2028, 0x2029]:
            if cp in (9, 10, 13):
                continue
            char = chr(cp)
            for text in ("T" + char + "X\nA:v", "T\nA:v" + char + "x", "T\n\nH:\na" + char + "b"):
                with self.subTest(codepoint=hex(cp), text=repr(text)):
                    self.assertIsNone(self.impl.structure(text))
        for text in ("", "\n\r\n", " \t\n\t ", "T\nA:v\n\u2028", "T\nA:v\x00 "):
            self.assertIsNone(self.impl.structure(text))
        self.assertEqual(self.impl.structure("T\tX\nA:v"), ("T\tX", (("label", "A"),)))
        self.assertEqual(self.impl.structure("T\nA:v\tx"), ("T", (("label", "A"),)))
        self.assertEqual(self.impl.structure("T\n\nH:\na\tb"), ("T", (("section", "H"),)))
        self.assertIsNone(self.impl.structure("T\nA:v\x0bx"))  # VT beside TAB stays refused
        for char in ("\u00a0", "\u2003", "\u200b", "\ufeff", "\U0010ffff"):
            want = ("T" + char, (("label", char + "A" + char),))
            self.assertEqual(self.impl.structure("T" + char + "\n" + char + "A" + char + ":v"), want)
        self.assertNotEqual(self.impl.structure("Ｔ\nA:v"), self.impl.structure("T\nA:v"))
        self.assertNotEqual(self.impl.structure("é\nA:v"), self.impl.structure("e\u0301\nA:v"))
        self.assertNotEqual(self.impl.structure("t\nA:v"), self.impl.structure("T\nA:v"))

    def test_n3_header_labels_first_colon_and_ascii_key_trim(self):
        text = "T:TITLE\n A : \nB:v:more:colons\nC:"
        self.assertEqual(self.impl.structure(text), ("T:TITLE", (("label", "A"), ("label", "B"), ("label", "C"))))
        for bad in ("T\nno colon", "T\n:v", "T\n   :v", "T\nA:v\nbody"):
            self.assertIsNone(self.impl.structure(bad))
        self.assertEqual(self.impl.structure("T"), ("T", ()))
        self.assertEqual(self.impl.structure(" T\n A :v"), (" T", (("label", "A"),)))
        # AM3: ASCII space AND TAB around a key are equivalent; the key itself keeps its bytes.
        self.assertEqual(self.impl.structure("T\n\tA\t:v"), self.impl.structure("T\nA:v"))
        self.assertEqual(self.impl.structure("T\n \tA B\t :v"), ("T", (("label", "A B"),)))

    def test_n3_sections_and_later_label_blocks(self):
        text = "T\n\n L :v\nM:\n\n H : \nbody\nmore body\n\nN:z:rest"
        self.assertEqual(self.impl.structure(text), ("T", (("label", "L"), ("label", "M"), ("section", "H"), ("label", "N"))))
        for bad in ("T\n\nH:", "T\n\nH:\n\n", "T\n\nH:\nL:v", "T\n\nH:\nbody:tail",
                    "T\n\nbody", "T\n\nL:v\nbody", "T\n\n :\nbody", "T\n\nH:\nbody\n\ncontinuation"):
            with self.subTest(bad=bad):
                self.assertIsNone(self.impl.structure(bad))
        self.assertEqual(self.impl.structure("T\n\nH:\n\u00a0"), ("T", (("section", "H"),)))
        self.assertEqual(self.impl.structure("T\n\n\tH\t:\nbody"), self.impl.structure("T\n\nH:\nbody"))
        self.assertEqual(self.impl.structure("T\n\n\tL\t:v"), ("T", (("label", "L"),)))
        self.assertEqual(self.impl.structure("T\n\nH:\u00a0"), ("T", (("label", "H"),)))

    def test_n3_structure_has_no_layout_registry_or_literal_length_cap(self):
        self.assertEqual(self.impl.structure("Novel\nNovel key:value"), ("Novel", (("label", "Novel key"),)))
        long = "x" * 257
        self.assertEqual(self.impl.structure(long + "\n" + long + ":v"), (long, (("label", long),)))
        self.assertEqual(len(self.impl.structure("T\n" + "\n".join("A:v" for _ in range(257)))[1]), 257)


class ProjectionMixin(BoundMixin):
    def test_n1_exact_input_shape_and_json_type_domain(self):
        program = self.impl.parse_program(minimal(keep=("k",)))
        self.matched(program, {"document": "T\nA:v", "k": None})
        for value in (None, False, 0, "T\nA:v", [], {}, {"document": "T\nA:v"},
                      {"document": "T\nA:v", "k": 0, "extra": 1}, {"Document": "T\nA:v", "k": 0}):
            with self.subTest(value=value):
                self.refused(program, value, "input")
        for text in (None, True, 1, [], {}):
            self.refused(program, {"document": text, "k": 0}, "input")
        custom = minimal(keep=("document",))
        custom["text"] = "payload"
        parsed = self.impl.parse_program(custom)
        self.matched(parsed, {"payload": "T\nA:v", "document": 7})
        self.refused(parsed, {"document": "T\nA:v", "k": 7}, "input")

    def test_n4_exact_layout_match_order_kind_title_and_empty_structure(self):
        spec = minimal(entries=[{"label": "A"}, {"label": "B"}, {"section": "H"}])
        program = self.impl.parse_program(spec)
        base = "T\nA:v\nB:w\n\nH:\nbody"
        result = self.matched(program, {"document": base})
        self.assertEqual(result.key, expected_key("T", (("label", "A"), ("label", "B"), ("section", "H"))))
        for text in (base.replace("T", "t", 1), base.replace("A:", "a:"), base.replace("H:", "h:"),
                     base.replace("A:v\nB:w", "B:w\nA:v"), base.replace("B:w\n", ""),
                     base.replace("A:v", "A:v\nA:v"), base.replace("B:w", "B:w\nNew:z"),
                     base.replace("H:\nbody", "H:v"), "T"):
            with self.subTest(text=text):
                self.refused(program, {"document": text}, "layout")
        spec["layouts"].insert(0, {"name": "same title different entries", "title": "T", "entries": [{"label": "Z"}]})
        self.assertEqual(self.matched(self.impl.parse_program(spec), {"document": base}).key, result.key)

    def test_n5_key_omits_values_and_name_preserves_all_kept_json(self):
        values = [None, True, False, 0, -(2**63), 2**63 - 1, "é文🙂", [], {}, [1, {"x": [None, True]}], {"z": 1, "a": "v"}]
        for value in values:
            spec = minimal(keep=("keep",))
            program = self.impl.parse_program(spec)
            raw = {"document": "T\nA:private:value", "keep": value}
            before = deepcopy(raw)
            first = self.matched(program, raw)
            self.assertEqual(first.key, expected_key("T", (("label", "A"),), {"keep": value}))
            self.assertEqual(raw, before)
            spec["layouts"][0]["name"] = "renamed"
            second = self.matched(self.impl.parse_program(spec), {"document": "T\nA:other", "keep": value})
            self.assertEqual(first.key, second.key)
        p = self.impl.parse_program(minimal(keep=("keep",)))
        one = self.matched(p, {"document": "T\nA:v", "keep": 1})
        two = self.matched(p, {"document": "T\nA:v", "keep": 2})
        self.assertNotEqual(one.key.text, two.key.text)
        raw = {"document": "T\nA:v", "keep": {"mutable": [1]}}
        frozen = self.matched(p, raw)
        raw["keep"]["mutable"].append(2)
        self.assertEqual(frozen.key.value["keep"], {"keep": {"mutable": [1]}})

    def test_n5_key_depth_cap_adjacent_pair_from_valid_inputs(self):
        p = self.impl.parse_program(minimal(keep=("k",)))
        good = {"document": "T\nA:v", "k": nested(62)}
        bad = {"document": "T\nA:v", "k": nested(63)}
        canonicalize(good)
        canonicalize(bad)
        self.matched(p, good)
        self.refused(p, bad, "key")

    def test_n5_key_byte_cap_adjacent_pair_from_valid_inputs(self):
        p = self.impl.parse_program(minimal(keep=("k",)))
        empty_key = expected_key("T", (("label", "A"),), {"k": ""})
        room = 1_048_576 - len(empty_key.text.encode())
        good = {"document": "T\nA:v", "k": "x" * room}
        bad = {"document": "T\nA:v", "k": "x" * (room + 1)}
        self.assertLessEqual(len(canonicalize(bad).text.encode()), 1_048_576)
        self.assertEqual(len(self.matched(p, good).key.text.encode()), 1_048_576)
        self.refused(p, bad, "key")

    def test_n5_key_item_cap_adjacent_pair_from_valid_inputs(self):
        p = self.impl.parse_program(minimal(keep=("k",)))
        # Key: root 2 + form 2 + structure 1 + pair 2 + keep 1 = 8 items.
        good = {"document": "T\nA:v", "k": [0] * (100_000 - 8)}
        bad = {"document": "T\nA:v", "k": [0] * (100_000 - 7)}
        canonicalize(bad)
        self.matched(p, good)
        self.refused(p, bad, "key")

    def test_i4_each_refusal_has_an_adjacent_accept_pair(self):
        p = self.impl.parse_program(minimal(keep=("k",)))
        good = {"document": "T\nA:v", "k": 0}
        self.matched(p, good)
        self.refused(p, {**good, "extra": 0}, "input")
        self.refused(p, {**good, "document": "T\nAv"}, "text")
        self.refused(p, {**good, "document": "T\na:v"}, "layout")
        self.matched(p, {**good, "k": nested(62)})
        self.refused(p, {**good, "k": nested(63)}, "key")

    def test_n1_n5_error_precedence_is_step_order(self):
        p = self.impl.parse_program(minimal(keep=("k",)))
        self.refused(p, {"document": "\x00", "k": nested(63), "extra": 0}, "input")
        self.refused(p, {"document": "\x00", "k": nested(63)}, "text")
        self.refused(p, {"document": "U\nA:v", "k": nested(63)}, "layout")
        self.refused(p, {"document": "T\nA:v", "k": nested(63)}, "key")


class PropertyMixin(BoundMixin):
    def test_i1_seven_fixture_structures_and_fixed_titles(self):
        spec, documents = corpus()
        self.assertEqual(len(documents), 7)
        p = self.impl.parse_program(spec)
        for name, text in documents:
            with self.subTest(fixture=name):
                want_pairs = tuple((item["kind"], item["key"]) for item in layout_signature(text)["structure"])
                title = TITLES[name[:8]]
                self.assertEqual(text.split("\n")[0], title)
                self.assertEqual(self.impl.structure(text), (title, want_pairs))
                result = self.matched(p, {"document": text, "fields": ["patient_name"]})
                want = expected_key(title, want_pairs, {"fields": ["patient_name"]})
                self.assertEqual(result.key.text.encode("utf-8"), want.text.encode("utf-8"))
                self.assertEqual(result.key.digest, hashlib.sha256(want.text.encode("utf-8")).hexdigest())
                self.bound(p, text, result)

    def test_i2_generated_value_substitutions_preserve_keys(self):
        spec, documents = corpus()
        p = self.impl.parse_program(spec)
        tested = 0
        for index, (name, text) in enumerate(documents):
            original = self.matched(p, {"document": text, "fields": ["x"]})
            for kind, changed in generated_documents(text, 701 + index):
                if kind != "value":
                    continue
                with self.subTest(fixture=name, variant=tested):
                    result = self.matched(p, {"document": changed, "fields": ["x"]})
                    self.assertEqual(result.key, original.key)
                tested += 1
        self.assertGreater(tested, 1000)

    def test_i2_later_labels_and_body_substitutions(self):
        p = self.impl.parse_program(minimal(entries=[{"label": "A"}, {"label": "B"}, {"section": "H"}]))
        base = "T\n\nA:v\nB:w\n\nH:\nbody"
        original = self.matched(p, {"document": base}).key
        for label_value in ("é文", " :a:b ", "\u00a0", "\u2003", "e\u0301"):
            for body in ("é文", "\u00a0", " leading space", "e\u0301", "🙂" * 200):
                changed = f"T\n\nA:{label_value}\nB:{label_value}\n\nH:\n{body}"
                self.assertEqual(self.matched(p, {"document": changed}).key, original)
        self.refused(p, {"document": base.replace("A:v", "A:")}, "text")
        self.refused(p, {"document": base.replace("body", "body:colon")}, "text")

    def test_i3_generated_structural_changes_never_keep_original_key(self):
        spec, documents = corpus()
        p = self.impl.parse_program(spec)
        count = 0
        for index, (name, text) in enumerate(documents):
            original = self.matched(p, {"document": text, "fields": []}).key.text
            for kind, changed in generated_documents(text, index):
                if kind != "structural":
                    continue
                with self.subTest(fixture=name, variant=count):
                    result = self.impl.project(p, {"document": changed, "fields": []})
                    self.assertTrue(not result.matched or result.key.text != original)
                count += 1
        self.assertGreater(count, 150)

    def test_i3_explicit_changed_layouts_match_different_keys(self):
        base = minimal(entries=[{"label": "A"}, {"label": "B"}])
        forms = ["T\nA:v\nB:w", "T\nB:w\nA:v", "T\nA:v\nA:v\nB:w", "T\nA:v", "t\nA:v\nB:w", "T\nA:v\nB:w\nC:z"]
        layouts = []
        for index, text in enumerate(forms):
            title, *labels = text.split("\n")
            layouts.append({"name": str(index), "title": title,
                            "entries": [{"label": line.partition(":")[0]} for line in labels]})
        base["layouts"] = layouts
        p = self.impl.parse_program(base)
        keys = [self.matched(p, {"document": text}).key.text for text in forms]
        self.assertEqual(len(set(keys)), len(forms))

    def test_i3_declared_normalization_equivalences_preserve_keys(self):
        spec, documents = corpus()
        p = self.impl.parse_program(spec)
        for index, (name, text) in enumerate(documents):
            original = self.matched(p, {"document": text, "fields": []}).key
            for kind, changed in generated_documents(text, index):
                if kind == "equivalent":
                    with self.subTest(fixture=name, text=changed[:40]):
                        self.assertEqual(self.matched(p, {"document": changed, "fields": []}).key, original)

    def test_i6_purity_repetition_and_input_nonmutation(self):
        spec, documents = corpus()
        inputs = [{"document": text, "fields": ["x"]} for _, text in documents]
        inputs += [None, {"document": "\x00", "fields": []}, {"document": "Other\nA:v", "fields": []},
                   {"document": documents[0][1], "fields": nested(63)}]
        before = deepcopy((spec, inputs))
        # Modules are imported before tripwires, exactly as a package consumer imports them.
        with ExitStack() as stack:
            for target in ("builtins.open", "time.time", "os.urandom", "sqlite3.connect"):
                stack.enter_context(patch(target, side_effect=AssertionError(target)))
            p = self.impl.parse_program(spec)
            for value in inputs:
                first = self.impl.project(p, value)
                for _ in range(3):
                    self.assertEqual(self.impl.project(p, value), first)
            self.assertEqual(self.impl.structure(documents[0][1]), self.impl.structure(documents[0][1]))
        self.assertEqual((spec, inputs), before)

    def test_i7_linear_work_large_matching_and_rejecting_inputs(self):
        p = self.impl.parse_program(minimal(entries=[{"section": "H"}]))
        for line_count in (4, 100, 1000, 10_000, 50_000):
            text = "T\n\nH:\n" + "\n".join("v" for _ in range(line_count - 3))
            self.assertEqual(len(text.split("\n")), line_count)
            result = self.matched(p, {"document": text})
            self.bound(p, text, result)
            for bad, reason in ((text[:-1] + ":", "text"), ("U" + text[1:], "layout"), (text[:-1] + "\x00", "text")):
                result = self.refused(p, {"document": bad}, reason)
                self.bound(p, bad, result)
        room = 1_048_576 - len(canonicalize({"document": "T\n\nH:\nv"}).text.encode())
        text = "T\n\nH:\nv" + "x" * room
        self.assertEqual(len(canonicalize({"document": text}).text.encode()), 1_048_576)
        for candidate, reason in ((text, None), (text[:-1] + ":", "text"), ("U" + text[1:], "layout")):
            result = self.matched(p, {"document": candidate}) if reason is None else self.refused(p, {"document": candidate}, reason)
            self.bound(p, candidate, result)
        unicode_text = "T\n\nH:\n" + "🙂" * 200_000
        self.bound(p, unicode_text, self.matched(p, {"document": unicode_text}))
        rejected = unicode_text[:-1] + ":"
        self.bound(p, rejected, self.refused(p, {"document": rejected}, "text"))

    def test_i7_many_layouts_and_long_prefix_comparisons(self):
        spec = minimal()
        spec["layouts"] = [{"name": str(i), "title": "T", "entries": [{"label": "A"}, {"label": str(i)}]} for i in range(600)]
        p = self.impl.parse_program(spec)
        for text, reason in (("T\nA:v\n599:w", None), ("T\nA:v\nabsent:w", "layout"), ("U\nA:v", "layout")):
            result = self.matched(p, {"document": text}) if reason is None else self.refused(p, {"document": text}, reason)
            self.bound(p, text, result)

    def test_totality_over_generated_canonical_json(self):
        rng = random.Random(1904)
        p = self.impl.parse_program(minimal(keep=("k",)))
        atoms = [None, False, True, -2**63, 2**63 - 1, "", "é文🙂", "\x00", "\u2028"]
        def draw(depth):
            if depth == 0 or rng.randrange(3) == 0:
                return rng.choice(atoms)
            if rng.randrange(2):
                return [draw(depth - 1) for _ in range(rng.randrange(5))]
            return {f"k{i}": draw(depth - 1) for i in range(rng.randrange(5))}
        reasons = set()
        for index in range(250):
            value = draw(4)
            candidate = {"document": "T\nA:v", "k": value} if index % 2 else value
            canonicalize(candidate)
            result = self.impl.project(p, candidate)
            self.assertEqual(result.matched, result.key is not None)
            self.assertEqual(result.matched, result.reason is None)
            reasons.add(result.reason)
            if result.matched:
                self.assertEqual(result.key.value["keep"]["k"], value)
            else:
                self.assertEqual(result.reason, "input")
        self.assertEqual(reasons, {None, "input"})


class DifferentialMixin(BoundMixin):
    def test_d1_generated_fixture_corpus_matches_independent_oracle(self):
        spec, documents = corpus()
        actual_program = self.impl.parse_program(spec)
        oracle_program = projection_oracle.parse_program(spec)
        kinds = set()
        count = 0
        for index, (name, text) in enumerate(documents):
            candidates = [("original", text), *generated_documents(text, 4200 + index)]
            for kind, changed in candidates:
                value = {"document": changed, "fields": ["x", {"locale": "é"}]}
                canonicalize(value)
                actual = self.impl.project(actual_program, value)
                expected = projection_oracle.project(oracle_program, value)
                with self.subTest(fixture=name, kind=kind, variant=count):
                    self.assertEqual(actual.matched, expected.matched)
                    self.assertEqual(actual.reason, expected.reason)
                    self.assertEqual(None if actual.key is None else actual.key.text.encode("utf-8"),
                                     None if expected.key is None else expected.key.text.encode("utf-8"))
                    self.assertEqual(self.impl.structure(changed), projection_oracle.structure(changed))
                    self.bound(actual_program, changed, actual)
                kinds.add(kind)
                count += 1
        self.assertEqual(kinds, {"original", "value", "structural", "equivalent", "invalid"})
        self.assertGreater(count, 1200)


class RuntimeApiTests(ApiMixin, unittest.TestCase):
    module_name = "cement_runtime.projection"

    def test_exports_exactly_the_contract_api(self):
        # §4 names seven exports; limits, `Reason` and imported helpers stay private.
        self.assertEqual(
            sorted(importlib.import_module(self.module_name).__all__),
            sorted(["PROJECTION_ABI", "Layout", "ProjectionProgram", "Projection", "parse_program", "project", "structure"]),
        )


class OracleApiTests(ApiMixin, unittest.TestCase):
    module_name = "tests.projection_oracle"


class RuntimeValidationTests(ValidationMixin, unittest.TestCase):
    module_name = "cement_runtime.projection"


class OracleValidationTests(ValidationMixin, unittest.TestCase):
    module_name = "tests.projection_oracle"


class RuntimeGrammarTests(GrammarMixin, unittest.TestCase):
    module_name = "cement_runtime.projection"


class OracleGrammarTests(GrammarMixin, unittest.TestCase):
    module_name = "tests.projection_oracle"


class RuntimeProjectionTests(ProjectionMixin, unittest.TestCase):
    module_name = "cement_runtime.projection"


class OracleProjectionTests(ProjectionMixin, unittest.TestCase):
    module_name = "tests.projection_oracle"


class RuntimePropertyTests(PropertyMixin, unittest.TestCase):
    module_name = "cement_runtime.projection"


class OraclePropertyTests(PropertyMixin, unittest.TestCase):
    module_name = "tests.projection_oracle"


class RuntimeDifferentialTests(DifferentialMixin, unittest.TestCase):
    module_name = "cement_runtime.projection"


class OracleDifferentialTests(DifferentialMixin, unittest.TestCase):
    module_name = "tests.projection_oracle"


if __name__ == "__main__":
    unittest.main()
