"""Tests that survivor rulings added as `missing-test` (`.agent/decisions/survivor-rulings.md`).

Each test names the row and the survivor it kills.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from cement_runtime import System, cli
from cement_runtime.errors import ValidationError


class ForgedEquality(type):
    """A metaclass whose classes claim equality with every class: `type(x) == T` holds for its
    instances, `type(x) is T` never does — the gap each `is` → `==` survivor ruling pins."""

    def __eq__(cls, other: object) -> bool:
        return True

    def __ne__(cls, other: object) -> bool:
        return False

    __hash__ = type.__hash__


class SurvivorPinTests(unittest.TestCase):
    def test_p105_the_cli_prints_non_ascii_json_as_raw_utf8(self) -> None:
        # p105: `cli.py` `_emit` `ensure_ascii=False` → `True` survived every module, because each
        # byte-comparing CLI test prints ASCII alone. A Japanese deployment reads the raw text.
        with tempfile.TemporaryDirectory(prefix="cement-p105-") as directory:
            database = str(pathlib.Path(directory) / "ledger.db")
            base = ["--db", database, "--partition", "hospital"]

            def run(*argv: str) -> str:
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    self.assertEqual(cli.main([*base, *argv]), 0)
                return stdout.getvalue()

            run("operation", "register", "extract")
            submission = {"input": {"文書": "患者: 山田"}, "output": {"患者": "山田"}}
            proposal_id = json.loads(
                run("proposal", "submit", "extract", "--submission", json.dumps(submission))
            )["proposal_id"]
            shown = run("proposal", "show", proposal_id)
        self.assertIn('"患者": "山田"', shown)
        self.assertNotIn("\\u", shown)
        self.assertEqual(json.loads(shown)["proposed_output"], {"患者": "山田"})

    def test_p104_a_class_forging_equality_is_no_candidate(self) -> None:
        # p104: `type(candidate) is not Candidate` → `!=` survived every module. Identity cannot be
        # forged; equality can, through the class's metaclass, so only `is not` refuses this object.
        class LooksLikeACandidate(metaclass=ForgedEquality):
            output = {"answer": 1}
            provenance: dict[str, object] = {}

        with tempfile.TemporaryDirectory(prefix="cement-p104-") as directory:
            system = System(str(pathlib.Path(directory) / "ledger.db"))
            system.register_operation("tenant-a", "echo")
            with self.assertRaises(ValidationError) as raised:
                system.submit_proposal(
                    "tenant-a", "echo", {"n": 1}, candidate=LooksLikeACandidate()  # type: ignore[arg-type]
                )
            self.assertEqual(str(raised.exception), "candidate must be a Candidate")
            self.assertEqual(system.events("tenant-a")[-1]["kind"], "operation.registered")

    def test_p115_a_long_distinct_id_selection_is_no_duplicate(self) -> None:
        # p115: `len(set(ids)) != len(ids)` → `is not` survived. CPython caches small ints alone
        # (to 256), so the identity form refuses every distinct selection longer than that.
        from cement_runtime import system as system_module

        with tempfile.TemporaryDirectory(prefix="cement-p115-") as directory:
            system = System(str(pathlib.Path(directory) / "ledger.db"))
            system.register_operation("tenant-a", "echo")
            ids = tuple(f"prop_{index:032x}" for index in range(300))
            with system.store.transaction() as connection:
                bound = system_module._proposal_bindings(
                    connection, partition="tenant-a", selection=system_module._ProposalIds(ids)
                )
        self.assertEqual((bound.total, bound.rows), (0, ()))

    def test_p114_text_refuses_a_class_forging_equality_with_str(self) -> None:
        # p114: `_text`'s `type(value) is not str` → `!=` survived; equality with `str` can be
        # forged through a metaclass, identity cannot.
        class LooksLikeText(metaclass=ForgedEquality):
            def encode(self, encoding: str) -> bytes:
                return b"actor"

            def __iter__(self):  # noqa: ANN204 — the shape `_text` iterates
                return iter("actor")

        with tempfile.TemporaryDirectory(prefix="cement-p114-") as directory:
            system = System(str(pathlib.Path(directory) / "ledger.db"))
            with self.assertRaises(ValidationError) as raised:
                system.register_operation("tenant-a", "echo", registered_by=LooksLikeText())  # type: ignore[arg-type]
        self.assertEqual(str(raised.exception), "registered_by must be non-empty text")

    def test_p114_the_event_payload_cap_is_an_adjacent_pair(self) -> None:
        # p114: `_event`'s `max_bytes=262_144` ±1 survived; `set_projection` reaches the cap (p138).
        from cement_runtime import system as system_module

        frame = len('{"p":""}')
        with tempfile.TemporaryDirectory(prefix="cement-p114-") as directory:
            store = system_module.Store(str(pathlib.Path(directory) / "ledger.db"))
            for size, accepted in ((262_144, True), (262_145, False)):
                with self.subTest(size=size), store.transaction(write=True) as connection:
                    write = lambda: system_module._event(  # noqa: E731 — one call, two outcomes
                        connection, partition="tenant-a", kind="operation.registered",
                        subject_type="operation", subject_id="tenant-a/echo@1",
                        payload={"p": "x" * (size - frame)}, now_us=1,
                    )
                    if accepted:
                        self.assertGreater(write(), 0)
                    else:
                        with self.assertRaises(ValidationError) as raised:
                            write()
                        self.assertEqual(str(raised.exception), "canonical JSON exceeds 262144 bytes")

    def test_p101_bundle_type_checks_refuse_classes_forging_equality(self) -> None:
        # p101: `validate_function` + `build_function` take caller objects, and each `type(x) is T`
        # → `==` survived (`function.py` `_normalize` document, abi, operation revision, entries;
        # `build_function` entries). Forged equality passes `==`; identity refuses.
        from copy import deepcopy

        from cement_runtime import FUNCTION_ABI, build_function, validate_function
        from tests.test_function import _build, _entry

        class Forged(metaclass=ForgedEquality):
            pass

        class ForgedAbi(metaclass=ForgedEquality):
            # Equal to the v3 ABI alone, so `_normalize` keeps v3's key set and reaches the check.
            def __eq__(self, other: object) -> bool:
                return other == FUNCTION_ABI

            def __hash__(self) -> int:
                return hash(FUNCTION_ABI)

        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="p101"),))
        cases = {
            "document": (lambda: Forged(), "invalid function: expected keys"),
            "abi": (lambda: {**deepcopy(bundle.value), "abi": ForgedAbi()}, "unsupported function ABI"),
            "operation_revision": (
                lambda: {**deepcopy(bundle.value), "scope": {**bundle.value["scope"], "operation_revision": Forged()}},
                "function operation revision must be a positive signed 64-bit integer",
            ),
            "entries": (lambda: {**deepcopy(bundle.value), "entries": Forged()}, "function entries must be an array"),
        }
        for name, (document, message) in cases.items():
            with self.subTest(field=name), self.assertRaises(ValidationError) as raised:
                validate_function(document())
            self.assertTrue(str(raised.exception).startswith(message), str(raised.exception))
        with self.assertRaises(ValidationError) as raised:
            build_function(
                partition="tenant-a", operation="echo", operation_revision=1,
                policy_hash="0" * 64, entries=[Forged()],
            )
        self.assertEqual(str(raised.exception), "function entries must be FunctionEntry values")

    def test_p101_a_half_set_projection_is_refused_as_invalid(self) -> None:
        # p101: `projection is not None or projection_hash is not None` → `and` survived: with one
        # of the two set, the projected branch must still run and refuse the missing half.
        from copy import deepcopy

        from cement_runtime import validate_function
        from cement_runtime.projection import draft_program, parse_program
        from tests.test_function import _build, _entry, _rehash

        program = parse_program(draft_program([{"doc": "Intake\nName: Ada"}]))
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="p101-half"),))
        for name, projection, projection_hash in (
            ("hash alone", None, program.program_hash),
            ("program alone", program.canonical.value, None),
        ):
            document = deepcopy(bundle.value)
            document["projection"], document["projection_hash"] = projection, projection_hash
            _rehash(document)
            with self.subTest(case=name), self.assertRaises(ValidationError):
                validate_function(document)

    def test_p101_a_projection_hash_mismatch_is_refused_in_both_orders(self) -> None:
        # p101: `program_hash != projection_hash` → `<`, `>` and `is` survived; a mismatch below
        # and above the program's hash must both refuse.
        from copy import deepcopy

        from cement_runtime import IntegrityError, validate_function
        from cement_runtime.projection import draft_program, parse_program
        from tests.test_function import _build, _entry, _rehash

        program = parse_program(draft_program([{"doc": "Intake\nName: Ada"}]))
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="p101-order"),))
        for wrong in ("0" * 64, "f" * 64):
            document = deepcopy(bundle.value)
            document["projection"], document["projection_hash"] = program.canonical.value, wrong
            _rehash(document)
            with self.subTest(projection_hash=wrong[:4]), self.assertRaises(IntegrityError) as raised:
                validate_function(document)
            self.assertEqual(
                str(raised.exception), "function projection does not hash to its projection_hash"
            )


if __name__ == "__main__":
    unittest.main()
