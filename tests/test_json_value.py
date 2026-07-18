import unittest

from cement_runtime.errors import ValidationError
from cement_runtime.json_value import canonicalize, parse_json


class CanonicalJSONTests(unittest.TestCase):
    def test_object_order_is_erased_but_number_and_unicode_semantics_are_conservative(self) -> None:
        left = canonicalize({"b": 2, "a": [1, "é"]})
        right = parse_json('{"a":[1,"é"],"b":2}')
        self.assertEqual(left.text, right.text)
        self.assertEqual(left.digest, right.digest)
        with self.assertRaises(ValidationError):
            canonicalize(1.0)
        with self.assertRaises(ValidationError):
            parse_json("1e-400")
        self.assertNotEqual(canonicalize("é").text, canonicalize("e\u0301").text)

    def test_parser_rejects_ambiguous_or_unbounded_values(self) -> None:
        invalid = (
            '{"x":1,"x":2}',
            "NaN",
            "Infinity",
            "-Infinity",
            str(2**63),
            '"\\ud800"',
            "1" * 5_000,
            "-" + "1" * 5_000,
        )
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValidationError):
                parse_json(source)
        with self.assertRaises(ValidationError):
            canonicalize((1, 2))
        with self.assertRaises(ValidationError):
            canonicalize([[[0]]], max_depth=1)
        with self.assertRaises(ValidationError):
            canonicalize({"x": "too large"}, max_bytes=4)
        with self.assertRaises(ValidationError):
            canonicalize("\ud800")

    def test_api_rejects_non_string_keys_and_cycles(self) -> None:
        with self.assertRaises(ValidationError):
            canonicalize({1: "value"})
        cycle: list[object] = []
        cycle.append(cycle)
        with self.assertRaises(ValidationError):
            canonicalize(cycle)

    def test_limit_configuration_requires_exact_integers(self) -> None:
        for limits in (
            {"max_bytes": True},
            {"max_depth": 1.0},
            {"max_items": False},
        ):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                canonicalize(None, **limits)
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                parse_json("null", **limits)


if __name__ == "__main__":
    unittest.main()
