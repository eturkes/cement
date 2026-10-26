"""p136-cmp battery — the per-operation comparator (`.agent/decisions/p136-cmp-contract.md`)."""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sqlite3
import tempfile
import unittest
from contextlib import closing

from cement_runtime import Candidate, CompilePolicy, IntegrityError, NotFoundError, System, ValidationError
from cement_runtime.cli import main
from cement_runtime.json_value import canonicalize
from cement_runtime.comparator import (
    MAX_BYTES,
    MAX_PATHS,
    MAX_RULES,
    MAX_SEGMENT,
    MAX_SEGMENTS,
    Comparison,
    compare,
    parse_comparator,
)

ABI = "cement-comparator-v1"
POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)


def _c(*rules: dict) -> dict:
    return {"abi": ABI, "rules": list(rules)}


def _rule(path: list[str], rule: str, within: str | None = None) -> dict:
    return {"path": path, "rule": rule} | ({} if within is None else {"within": within})


class GrammarTests(unittest.TestCase):
    def test_m1_a_valid_comparator_parses_and_its_hash_ignores_rule_order(self) -> None:
        rules = [
            _rule(["note"], "ignore"),
            _rule(["name"], "text"),
            _rule(["codes"], "unordered"),
            _rule(["codes", "*", "label"], "text"),
            _rule(["dose"], "tolerance", "0.5"),
            _rule(["id"], "tolerance", "0"),
        ]
        parsed = parse_comparator(_c(*rules))
        self.assertEqual([rule.path for rule in parsed.rules], sorted(tuple(r["path"]) for r in rules))
        self.assertEqual(parsed.comparator_hash, parse_comparator(_c(*reversed(rules))).comparator_hash)
        self.assertNotEqual(
            parsed.comparator_hash, parse_comparator(_c(*rules[:-1])).comparator_hash
        )
        self.assertEqual(parse_comparator(parsed.document()).comparator_hash, parsed.comparator_hash)

    def test_m1_each_refusal_names_its_rule(self) -> None:
        cases = {
            "repeated path": (_c(_rule(["a"], "text"), _rule(["a"], "ignore")), "comparator rule 1 repeats the path of rule 0"),
            "root ignore": (_c(_rule([], "ignore")), "comparator rule 0 ignores the whole answer"),
            "under ignore": (_c(_rule(["a"], "ignore"), _rule(["a", "b"], "text")), "comparator rule 1 sits under a ignore rule (rule 0)"),
            "under text": (_c(_rule(["a"], "text"), _rule(["a", "b"], "text")), "comparator rule 1 sits under a text rule (rule 0)"),
            "under tolerance": (_c(_rule(["a"], "tolerance", "1"), _rule(["a", "*"], "ignore")), "comparator rule 1 sits under a tolerance rule (rule 0)"),
            "unordered child not through *": (
                _c(_rule(["a"], "unordered"), _rule(["a", "b"], "ignore")),
                "comparator rule 1 must pass through * below its unordered rule (rule 0)",
            ),
            "tolerance under unordered": (
                _c(_rule(["a"], "unordered"), _rule(["a", "*", "n"], "tolerance", "1")),
                "comparator rule 1: tolerance cannot sit under an unordered rule",
            ),
            "unknown kind": (_c(_rule(["a"], "fuzzy")), "comparator rule 0 rule must be ignore, text, unordered, or tolerance"),
            "within on text": (_c({"path": ["a"], "rule": "text", "within": "1"}), "comparator rule 0 must hold exactly path, rule"),
            "missing within": (_c({"path": ["a"], "rule": "tolerance"}), "comparator rule 0 must hold exactly path, rule, within"),
            "wrong abi": ({"abi": "cement-comparator-v2", "rules": []}, f"comparator abi must be {ABI}"),
            "extra key": ({"abi": ABI, "rules": [], "x": 1}, "comparator must hold exactly abi, rules"),
            "empty segment": (_c(_rule([""], "text")), "comparator rule 0 path segments must be text"),
            "non-text segment": (_c({"path": [1], "rule": "text"}), "comparator rule 0 path segments must be text"),
        }
        for name, (value, message) in cases.items():
            with self.subTest(case=name), self.assertRaises(ValidationError) as caught:
                parse_comparator(value)
            self.assertTrue(str(caught.exception).startswith(message), str(caught.exception))

    def test_m1_bounds_are_adjacent_pairs(self) -> None:
        parse_comparator(_c(*(_rule([f"k{i}"], "text") for i in range(MAX_RULES))))
        with self.assertRaisesRegex(ValidationError, "at most 256 rules"):
            parse_comparator(_c(*(_rule([f"k{i}"], "text") for i in range(MAX_RULES + 1))))
        parse_comparator(_c(_rule(["k"] * MAX_SEGMENTS, "text")))
        with self.assertRaisesRegex(ValidationError, "at most 32 segments"):
            parse_comparator(_c(_rule(["k"] * (MAX_SEGMENTS + 1), "text")))
        parse_comparator(_c(_rule(["k" * MAX_SEGMENT], "text")))
        with self.assertRaisesRegex(ValidationError, "1 to 256 characters"):
            parse_comparator(_c(_rule(["k" * (MAX_SEGMENT + 1)], "text")))
        for within, ok in (("0", True), ("12.50", True), ("1" * 32, True), ("1" * 33, False), ("01", False), ("-1", False), ("1.", False), (".5", False), ("1e3", False)):
            with self.subTest(within=within):
                value = _c(_rule(["d"], "tolerance", within))
                if ok:
                    parse_comparator(value)
                else:
                    with self.assertRaisesRegex(ValidationError, "within must be"):
                        parse_comparator(value)
        # The canonical document is bounded too: exactly MAX_BYTES parses, one byte more refuses.
        def size(rules: list[dict]) -> int:
            document = {"abi": ABI, "rules": sorted(rules, key=lambda rule: rule["path"])}
            return len(canonicalize(document, max_bytes=10**7).text.encode())

        rules = [_rule([f"{i:03d}" + "k" * 247], "text") for i in range(225)]
        while True:
            gap = MAX_BYTES - size(rules)
            overhead = size(rules + [_rule(["z"], "text")]) - size(rules) - 1
            if 1 <= gap - overhead <= MAX_SEGMENT:
                break
            rules.append(_rule([f"{len(rules):03d}" + "k" * 100], "text"))  # a step below the window
        exact = rules + [_rule(["z" * (gap - overhead)], "text")]
        self.assertEqual(size(exact), MAX_BYTES)
        parse_comparator(_c(*exact))
        longer = exact[:-1] + [_rule(["z" * (len(exact[-1]["path"][0]) + 1)], "text")]
        self.assertEqual(size(longer), MAX_BYTES + 1)
        with self.assertRaisesRegex(ValidationError, str(MAX_BYTES)):
            parse_comparator(_c(*longer))


class CompareTests(unittest.TestCase):
    def check(self, rules: list[dict], expected: object, actual: object) -> Comparison:
        return compare(parse_comparator(_c(*rules)), expected, actual)

    def test_m2_none_is_canonical_equality(self) -> None:
        self.assertEqual(compare(None, {"a": 1, "b": [1]}, {"b": [1], "a": 1}), Comparison(True))
        self.assertEqual(compare(None, {"a": 1}, {"a": 2}), Comparison(False, ("$.a",)))
        self.assertEqual(compare(None, {"a": 1}, {"a": 2}), compare(parse_comparator(_c()), {"a": 1}, {"a": 2}))
        self.assertEqual(compare(None, 1, True), Comparison(False, ("$",)))

    def test_m2_each_rule_agrees_and_disagrees_on_an_adjacent_pair(self) -> None:
        base = {"name": "Hana Sato", "codes": ["b", "a"], "dose": "1.25", "note": "x", "id": 7}
        rules = [
            _rule(["note"], "ignore"),
            _rule(["name"], "text"),
            _rule(["codes"], "unordered"),
            _rule(["dose"], "tolerance", "0.5"),
        ]
        agree = {"name": "  hana\tSATO ", "codes": ["a", "b"], "dose": "1.75", "id": 7}
        self.assertEqual(self.check(rules, base, agree), Comparison(True))
        for change, path in (
            ({"name": "hana sat0"}, "$.name"),
            ({"codes": ["a", "c"]}, "$.codes"),
            ({"codes": ["a", "b", "b"]}, "$.codes"),
            ({"dose": "1.76"}, "$.dose"),
            ({"dose": 2}, "$.dose"),
            ({"id": 8}, "$.id"),
        ):
            with self.subTest(change=change):
                self.assertEqual(self.check(rules, base, agree | change), Comparison(False, (path,)))
        # An ignored key may be present on one side only; an unnamed key may not.
        self.assertTrue(self.check(rules, base, agree | {"note": "other"}).agreed)
        self.assertEqual(self.check(rules, base, agree | {"extra": 1}), Comparison(False, ("$.extra",)))

    def test_m2_tolerance_reads_integers_and_decimal_strings_exactly(self) -> None:
        rule = [_rule([], "tolerance", "0.1")]
        for left, right, agreed in (
            (1, "1.1", True), ("1.1", 1, True), ("1.10", "1.2", True), ("1.1", "1.2000001", False),
            (-1, "-0.9", True), ("-0.95", "-1.05", True), ("0.30000000000000000001", "0.1", False),
            (10**18, 10**18 + 1, False), ("1.0", True, False), ("1.0", "one", False), ("1e0", "1", False),
            ("1" * 65, "1" * 65, True),
        ):
            with self.subTest(left=left, right=right):
                self.assertEqual(self.check(rule, left, right).agreed, agreed)

    def test_m2_text_rule_compares_only_two_strings_loosely(self) -> None:
        rule = [_rule([], "text")]
        self.assertTrue(self.check(rule, " Hana\t\u00a0SATO\n", "hana sato").agreed)
        self.assertTrue(self.check(rule, "a\u3000b", "a b").agreed)  # ideographic space collapses
        # A-Z alone fold: the verdict reads no host Unicode table, so 3.12 and 3.15 agree.
        for left, right in (("Straße", "STRASSE"), ("É", "é"), ("\ua7cb", "\u0264"), ("e\u0301", "é")):
            with self.subTest(left=left):
                self.assertFalse(self.check(rule, left, right).agreed)
        self.assertFalse(self.check(rule, "a\u2003b", "a b").agreed)  # EM SPACE is not in the set
        self.assertFalse(self.check(rule, "ab", "a b").agreed)
        self.assertFalse(self.check(rule, "1", 1).agreed)
        self.assertTrue(self.check(rule, None, None).agreed)

    def test_m2_unordered_applies_the_rules_below_it(self) -> None:
        rules = [_rule(["items"], "unordered"), _rule(["items", "*", "label"], "text"), _rule(["items", "*", "seen"], "ignore")]
        left = {"items": [{"label": "A  b", "seen": 1}, {"label": "c", "seen": 2}]}
        right = {"items": [{"label": "C"}, {"label": "a B", "seen": 9}]}
        self.assertTrue(self.check(rules, left, right).agreed)
        self.assertFalse(self.check(rules, left, {"items": [{"label": "C"}]}).agreed)
        self.assertFalse(self.check(rules, left, {"items": "A b"}).agreed)

    def test_m2_unordered_applies_an_ignore_at_its_elements(self) -> None:
        # Closing review (reviewer-1 + reviewer-3): `*` ignored below `unordered` = only the count
        # of elements is compared, as it is without the `unordered` rule.
        for rules in ([_rule(["v", "*"], "ignore")], [_rule(["v"], "unordered"), _rule(["v", "*"], "ignore")]):
            with self.subTest(rules=rules):
                self.assertTrue(self.check(rules, {"k": 1, "v": [10, "a"]}, {"k": 1, "v": [{"x": 2}, 20]}).agreed)
                self.assertEqual(self.check(rules, {"v": [10]}, {"v": [10, 10]}), Comparison(False, ("$.v",)))

    def test_m2_arrays_without_a_rule_compare_in_order(self) -> None:
        rules = [_rule(["rows", "*", "note"], "ignore")]
        left = {"rows": [{"v": 1, "note": "x"}, {"v": 2}]}
        self.assertTrue(self.check(rules, left, {"rows": [{"v": 1}, {"v": 2, "note": "y"}]}).agreed)
        self.assertEqual(
            self.check(rules, left, {"rows": [{"v": 2}, {"v": 1}]}),
            Comparison(False, ("$.rows[0].v", "$.rows[1].v")),
        )
        self.assertEqual(self.check(rules, left, {"rows": [{"v": 1}]}), Comparison(False, ("$.rows",)))

    def test_m2_a_literal_star_key_is_an_ordinary_key(self) -> None:
        rules = [_rule(["rows", "*"], "text")]
        self.assertTrue(self.check(rules, {"rows": ["A"]}, {"rows": ["a"]}).agreed)
        # `{"*": …}` is an object member, so the array rule never reaches it.
        self.assertFalse(self.check(rules, {"rows": {"*": "A"}}, {"rows": {"*": "a"}}).agreed)

    def test_m2_a_long_path_is_capped(self) -> None:
        key = "k" * 1_000
        result = self.check([_rule(["unused"], "text")], {key: 1}, {key: 2})
        self.assertEqual(len(result.paths[0]), 256)
        self.assertTrue(result.paths[0].endswith("\u2026"))

    def test_m2_paths_render_keys_and_stop_at_the_cap(self) -> None:
        left = {f"k{i:02d}": i for i in range(MAX_PATHS + 5)} | {"a b": 1}
        right = {key: -1 for key in left}
        result = self.check([_rule(["unused"], "text")], left, right)
        self.assertFalse(result.agreed)
        self.assertEqual(len(result.paths), MAX_PATHS)
        self.assertEqual(result.paths[0], '$["a b"]')
        self.assertEqual(result.paths[1:3], ("$.k00", "$.k01"))


class _Ledger(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-cmp-")
        self.addCleanup(directory.cleanup)
        self.db = str(pathlib.Path(directory.name) / "ledger.db")
        self.system = System(self.db)
        self.system.register_operation("tenant_a", "plan", policy=POLICY)
        for output in ({"name": "Hana", "note": "n", "codes": ["a"]}, {"name": "Ken", "note": "m", "codes": []}):
            for reviewer in ("r1", "r2"):
                proposal = self.system.submit_proposal(
                    "tenant_a", "plan", {"x": output["name"]}, candidate=Candidate(output=output, provenance={})
                )
                self.system.review("tenant_a", proposal, reviewer=reviewer, decision="accept")

    def rows(self) -> int:
        with closing(sqlite3.connect(self.db)) as connection:
            return connection.execute("SELECT COUNT(*) FROM comparator_settings").fetchone()[0]


class SetComparatorTests(_Ledger):
    def test_m4_set_reads_back_and_repeats_idempotently(self) -> None:
        comparator = _c(_rule(["note"], "ignore"), _rule(["name"], "text"))
        self.assertIsNone(self.system.comparator("tenant_a", "plan"))
        first = self.system.set_comparator("tenant_a", "plan", comparator, actor="learning-pass")
        self.assertTrue(first["changed"])
        events = self.system.events("tenant_a")
        self.assertEqual(
            (events[-1]["kind"], events[-1]["payload"]),
            ("comparator.set", {"actor": "learning-pass", "comparator_hash": first["comparator_hash"],
                                "operation_revision": 1, "previous_comparator_hash": None}),
        )
        again = self.system.set_comparator("tenant_a", "plan", comparator, actor="other")
        self.assertEqual((again["changed"], self.rows(), len(self.system.events("tenant_a"))), (False, 1, len(events)))
        record = self.system.comparator("tenant_a", "plan")
        self.assertEqual(
            record,
            {"operation_revision": 1, "comparator": parse_comparator(comparator).document(),
             "comparator_hash": first["comparator_hash"], "set_by": "learning-pass",
             "set_at_us": record["set_at_us"], "sequence": 1},
        )
        changed = self.system.set_comparator("tenant_a", "plan", _c(_rule(["name"], "text")), actor="lp")
        self.assertEqual(self.system.events("tenant_a")[-1]["payload"]["previous_comparator_hash"], first["comparator_hash"])
        self.assertEqual(self.system.comparator("tenant_a", "plan")["comparator_hash"], changed["comparator_hash"])

    def test_m4_unwitnessed_rules_and_wholly_ignored_answers_write_nothing(self) -> None:
        before = pathlib.Path(self.db).read_bytes()
        for comparator, message in (
            (_c(_rule(["missing"], "text")), r"comparator rule at \['missing'\] names no text value"),
            (_c(_rule(["nope", "*"], "text")), "names no text value"),
            (_c(_rule(["name"], "ignore"), _rule(["note"], "ignore"), _rule(["codes"], "ignore")), "ignores the whole answer of example ex_"),
            (_c(_rule(["codes"], "text")), r"names no text value"),  # a list, not a string
            (_c(_rule(["name"], "tolerance", "1")), r"names no tolerance value"),
        ):
            with self.subTest(comparator=comparator), self.assertRaisesRegex(ValidationError, message):
                self.system.set_comparator("tenant_a", "plan", comparator, actor="lp")
        self.assertEqual(pathlib.Path(self.db).read_bytes(), before)
        # Control: one witnessed rule each; the `*` path reaches the non-empty `codes` list.
        self.assertTrue(self.system.set_comparator("tenant_a", "plan", _c(_rule(["codes", "*"], "text")), actor="lp")["changed"])
        with self.assertRaises(NotFoundError):
            self.system.set_comparator("tenant_a", "unknown", _c(), actor="lp")

    def test_m4_each_revision_keeps_its_own_comparator_and_erase_removes_them(self) -> None:
        first = self.system.set_comparator("tenant_a", "plan", _c(_rule(["note"], "ignore")), actor="lp")
        self.system.revise_operation("tenant_a", "plan", policy=POLICY, revised_by="ops")
        self.assertIsNone(self.system.comparator("tenant_a", "plan"))
        self.assertEqual(
            self.system.comparator("tenant_a", "plan", operation_revision=1)["comparator_hash"], first["comparator_hash"]
        )
        with self.assertRaisesRegex(ValidationError, "names no ignore value"):  # revision 2: no example yet
            self.system.set_comparator("tenant_a", "plan", _c(_rule(["note"], "ignore")), actor="lp")
        self.assertEqual(self.system.erase_partition("tenant_a", actor="ops").counts["comparator_settings"], 1)
        self.assertEqual(self.rows(), 0)


    def test_m4_reads_bound_the_revision_and_treat_a_bad_stored_comparator_as_corruption(self) -> None:
        # Closing review (reviewer-1): 2**63 leaked OverflowError; a stored comparator the grammar
        # refuses read as a usage error instead of corruption.
        self.assertIsNone(self.system.comparator("tenant_a", "plan", operation_revision=2**63 - 1))
        with self.assertRaisesRegex(ValidationError, "operation_revision"):
            self.system.comparator("tenant_a", "plan", operation_revision=2**63)
        self.system.set_comparator("tenant_a", "plan", _c(_rule(["note"], "ignore")), actor="lp")
        with closing(sqlite3.connect(self.db)) as connection:
            trigger = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'comparator_settings_no_update'"
            ).fetchone()[0]
            connection.execute("DROP TRIGGER comparator_settings_no_update")
            connection.execute("UPDATE comparator_settings SET comparator_json = '{}'")
            connection.execute(trigger)
            connection.commit()
        with self.assertRaisesRegex(IntegrityError, "stored comparator is invalid"):
            self.system.comparator("tenant_a", "plan")


class ComparatorCLITests(_Ledger):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", self.db, "--partition", "tenant_a", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_m5_set_show_and_read(self) -> None:
        code, out, _ = self.run_cli("comparator", "show", "plan")
        self.assertEqual((code, json.loads(out)), (0, None))
        comparator = json.dumps(_c(_rule(["note"], "ignore"), _rule(["codes"], "unordered")))
        code, out, _ = self.run_cli("comparator", "set", "plan", "--comparator", comparator, "--actor", "lp")
        self.assertEqual((code, json.loads(out)["changed"]), (0, True))
        code, out, _ = self.run_cli("comparator", "show", "plan")
        self.assertEqual(json.loads(out)["comparator"], parse_comparator(json.loads(comparator)).document())
        code, _, err = self.run_cli("comparator", "set", "plan", "--comparator", '{"abi":"x","rules":[]}', "--actor", "lp")
        self.assertEqual((code, json.loads(err)["error"]), (2, "invalid"))
        code, _, err = self.run_cli("comparator", "show", "missing")
        self.assertEqual(code, 3)
        self.system.compile("tenant_a", "plan")
        self.system.verify_drafts("tenant_a", "plan", verified_by="lp")
        manifest = self.system.inspect_function_promotion("tenant_a", "plan")
        self.system.promote_function("tenant_a", "plan", expected_function_hash=manifest.function_hash, promoted_by="lp")
        code, out, _ = self.run_cli("function", "read", "plan")
        self.assertEqual(code, 0)
        record = self.system.comparator("tenant_a", "plan")
        self.assertIn(
            f"# Revision 1 comparator {record['comparator_hash']} (setting {record['sequence']}, a"
            " later setting replaces it): a shadow answer agrees when every value is equal, except:\n"
            '#   $["codes"]: the same items in any order\n'
            '#   $["note"]: ignored\n',
            out,
        )
        self.assertEqual(json.loads(self.run_cli("function", "read", "plan", "--json")[1])["comparator"]["comparator_hash"],
                         self.system.comparator("tenant_a", "plan")["comparator_hash"])

    def test_m5_show_exits_by_class_on_a_huge_revision_and_a_bad_stored_comparator(self) -> None:
        code, out, _ = self.run_cli("comparator", "show", "plan", "--operation-revision", str(2**63))
        self.assertEqual((code, out), (2, ""))
        self.system.set_comparator("tenant_a", "plan", _c(_rule(["note"], "ignore")), actor="lp")
        with closing(sqlite3.connect(self.db)) as connection:
            trigger = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'comparator_settings_no_update'"
            ).fetchone()[0]
            connection.execute("DROP TRIGGER comparator_settings_no_update")
            connection.execute("UPDATE comparator_settings SET comparator_json = '{}'")
            connection.execute(trigger)
            connection.commit()
        code, out, _ = self.run_cli("comparator", "show", "plan")
        self.assertEqual((code, out), (5, ""))


if __name__ == "__main__":
    unittest.main()
