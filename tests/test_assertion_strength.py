"""Assertion-strength oracle (p56): a weakened assertion lets its witness through.

Each row names one strength-bearing assertion and a WITNESS: a wrapper around one real call that
breaks the property that assertion checks, every other observable left real. The row's target
must pass bare and fail under its witness AT that assertion's line, found by AST, never typed.
Dropping or loosening the assertion lets the target pass, or fail at another line, so this module
reds. Weakening catalogue + measured kills: `.agent/decisions/p56-strength.py`.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import importlib
import io
import pathlib
import sys
import types
import unittest
from collections.abc import Callable, Generator
from typing import Any
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "hospital_ocr"
MISS_IS_FALSE = "self.assertFalse(resolution.match.matched)"


def _lines(path: pathlib.Path, function: str, chosen: Callable[[ast.stmt], bool]) -> list[int]:
    """Lines of every statement inside `function` that `chosen` selects."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    [node] = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == function]
    return [s.lineno for s in ast.walk(node) if isinstance(s, ast.stmt) and chosen(s)]


def _calls_against_before(statement: ast.stmt) -> bool:
    """`assert source.calls <any comparison> before`: a loosened operator keeps the locus."""
    test = statement.test if isinstance(statement, ast.Assert) else None
    return (
        isinstance(test, ast.Compare)
        and ast.unparse(test.left) == "source.calls"
        and [ast.unparse(c) for c in test.comparators] == ["before"]
    )


def _raised_at(error: BaseException, path: pathlib.Path) -> int | None:
    """Line of the innermost traceback frame inside `path`."""
    line = None
    trace = error.__traceback__
    while trace is not None:
        if pathlib.Path(trace.tb_frame.f_code.co_filename).resolve() == path.resolve():
            line = trace.tb_lineno
        trace = trace.tb_next
    return line


class _Outcomes(unittest.TestResult):
    """Keeps each raised exception object; the stock result keeps formatted text alone."""

    def __init__(self) -> None:
        super().__init__()
        self.raised: list[BaseException] = []

    def addFailure(self, test: unittest.TestCase, err: Any) -> None:  # noqa: N802
        super().addFailure(test, err)
        self.raised.append(err[1])

    def addError(self, test: unittest.TestCase, err: Any) -> None:  # noqa: N802
        super().addError(test, err)
        self.raised.append(err[1])

    def addSubTest(self, test: unittest.TestCase, subtest: unittest.TestCase, err: Any) -> None:  # noqa: N802
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.raised.append(err[1])


def _flip_a_miss(system_class: type, test_name: str) -> contextlib.AbstractContextManager[Any]:
    """`resolve`, called from `test_name` itself, reports its verified miss as a hit."""
    real = system_class.resolve

    def resolve(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = real(self, *args, **kwargs)
        if sys._getframe(1).f_code.co_name == test_name and result.match is not None and not result.match.matched:
            return dataclasses.replace(result, match=dataclasses.replace(result.match, matched=True))
        return result

    return mock.patch.object(system_class, "resolve", resolve)


def _key_on_creation(system_module: types.ModuleType) -> contextlib.AbstractContextManager[Any]:
    """`proposal.created` events carry one extra payload key; every other event stays real."""
    real = system_module._event

    def event(connection: Any, **fields: Any) -> Any:
        if fields["kind"] == "proposal.created":
            fields = {**fields, "payload": {**fields["payload"], "witness": True}}
        return real(connection, **fields)

    return mock.patch.object(system_module, "_event", event)


def _model_call_on_hit(system_class: type, document: object) -> contextlib.AbstractContextManager[Any]:
    """`resolve` of `document` also asks the model once when the function answers it."""
    real = system_class.resolve

    def resolve(self: Any, partition: str, operation: str, input_value: object, **kwargs: Any) -> Any:
        result = real(self, partition, operation, input_value, **kwargs)
        if input_value == document and result.match is not None and result.match.matched:
            self.propose(partition, operation, input_value)
        return result

    return mock.patch.object(system_class, "resolve", resolve)


@contextlib.contextmanager
def _demo() -> Generator[types.ModuleType]:
    added = str(DEMO) not in sys.path
    if added:
        sys.path.insert(0, str(DEMO))
    try:
        yield importlib.import_module("run_demo")
    finally:
        if added:
            sys.path.remove(str(DEMO))


class AssertionStrengthTests(unittest.TestCase):
    def _target(
        self,
        test_id: str,
        statement: str,
        witness: Callable[[types.ModuleType], contextlib.AbstractContextManager[Any]],
    ) -> None:
        module_name, _, test_name = test_id.rsplit(".", 2)
        module = importlib.import_module(module_name)
        path = pathlib.Path(module.__file__ or "")
        # A dropped or rewritten assertion leaves no line; the witness then decides the kill.
        found = _lines(path, test_name, lambda s: ast.unparse(s) == statement)
        self.assertLessEqual(len(found), 1)
        line = found[0] if found else None

        def run(patch: contextlib.AbstractContextManager[Any]) -> _Outcomes:
            outcomes = _Outcomes()
            with patch:
                unittest.defaultTestLoader.loadTestsFromName(test_id).run(outcomes)
            self.assertEqual(outcomes.testsRun, 1)
            return outcomes

        bare = run(contextlib.nullcontext())
        self.assertTrue(bare.wasSuccessful(), f"{test_id} fails without its witness")
        caught = run(witness(module))
        self.assertEqual(len(caught.raised), 1, f"{test_id} passed under its witness: {statement} no longer catches it")
        [error] = caught.raised
        self.assertIs(type(error), AssertionError)
        self.assertEqual(_raised_at(error, path), line, f"{test_id} failed away from {statement} (line {line})")

    def test_a_quarantined_case_misses_by_its_matched_flag(self) -> None:
        for name in (
            "test_counterexample_and_revocation_quarantine",
            "test_runtime_integrity_failure_quarantines_then_falls_back",
            "test_operation_revision_retires_old_artifacts",
        ):
            with self.subTest(test=name):
                self._target(
                    f"tests.test_system.SystemTests.{name}",
                    MISS_IS_FALSE,
                    lambda module, name=name: _flip_a_miss(module.System, name),
                )

    def test_the_proposal_created_payload_is_pinned_empty_by_equality(self) -> None:
        for test_id, statement in (
            (
                "tests.test_proposal_binding_battery.ProposalBindingBatteryTests.test_b30_the_six_owned_event_payloads_are_2",
                "self.assertEqual(json.loads(event['payload_json']), {})",
            ),
            (
                "tests.test_submission_battery.SubmissionBatteryTests.test_d03_the_event_is_proposal_created_with",
                "self.assertEqual(json.loads(row[3]), {})",
            ),
        ):
            with self.subTest(test=test_id):
                self._target(
                    test_id,
                    statement,
                    lambda module: _key_on_creation(sys.modules[module.System.__module__]),
                )

    def test_the_demo_pins_flat_model_calls_by_equality_on_each_hit(self) -> None:
        with _demo() as run_demo:
            path = pathlib.Path(run_demo.__file__ or "")
            lines = _lines(path, "main", _calls_against_before)
            self.assertEqual(len(lines), 2)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                run_demo.main()
            self.assertIn("All checks passed.", stream.getvalue())
            for line, name in zip(lines, ("layout_a_progress_note_03.txt", "layout_c_lab_slip_01.txt"), strict=True):
                with self.subTest(document=name):
                    witness = _model_call_on_hit(run_demo.System, run_demo._document(name))
                    # Caught by hand: `assertRaises` drops the traceback that locates the line.
                    try:
                        with witness, contextlib.redirect_stdout(io.StringIO()):
                            run_demo.main()
                    except AssertionError as error:
                        self.assertEqual(_raised_at(error, path), line, f"the demo failed away from line {line}")
                    else:
                        self.fail(f"the demo passed under its witness: line {line} no longer catches it")


if __name__ == "__main__":
    unittest.main()
