"""M3.6a3 closure controls (reviewer-18): undo one obligation in a read overlay → the battery reds. Usage: `uv run --no-project python -B .agent/decisions/m3u6a3-controls.py <checkout> controls|red`."""
import ast
import contextlib
import dataclasses
import io
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(sys.argv[1]).resolve()
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from tests import test_outcome_removal_battery as battery

assert pathlib.Path(battery.__file__).resolve() == ROOT / "tests/test_outcome_removal_battery.py"
assert pathlib.Path(battery.models.__file__).resolve() == ROOT / "src/cement_runtime/models.py"
ORIGINAL_READ = pathlib.Path.read_text
ERRORS = ROOT / "src/cement_runtime/errors.py"
MODELS = ROOT / "src/cement_runtime/models.py"
INIT = ROOT / "src/cement_runtime/__init__.py"
SYSTEM = ROOT / "src/cement_runtime/system.py"
O1_AST = "test_o1_no_src_module_defines_a_deleted_type"
O1_API = "test_o1_neither_package_nor_models_exposes_a_deleted_type"
O2 = "test_o2_all_loses_exactly_the_six_exports"
O3_TOKEN = "test_o3_no_src_token_names_a_deleted_type"
O3_DOC = "test_o3_the_resolve_docstring_keeps_its_rule"
O4 = "test_o4_models_survivors_are_byte_identical_and_in_order"
O5 = "test_o5_preserved_models_keep_their_abi"


@contextlib.contextmanager
def overlay(path, text):
    assert text != ORIGINAL_READ(path, encoding="utf-8")
    ast.parse(text)
    def read(self, *args, **kwargs):
        return text if self == path else ORIGINAL_READ(self, *args, **kwargs)
    with mock.patch.object(pathlib.Path, "read_text", read):
        yield


def run_case(name):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(
        battery.OutcomeRemovalBattery(name)
    )
    assert result.testsRun == 1 and not result.errors and not result.skipped, stream.getvalue()
    return result, stream.getvalue()


def changed_candidate(last_field=None, extra=False, annotation="object"):
    fields = [("output", annotation), ("provenance", "Mapping[str, object]")]
    if last_field is not None:
        fields[-1] = (*fields[-1], last_field)
    if extra:
        fields.append(("new_field", "int"))
    return dataclasses.make_dataclass("Candidate", fields, frozen=True, slots=True)


def controls():
    cls = battery.OutcomeRemovalBattery
    all_result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    assert all_result.wasSuccessful() and all_result.testsRun == 7
    controls = [
        ("O1-ClassDef", O1_AST, overlay(ERRORS, ERRORS.read_text() + "\nclass Resolved: pass\n")),
        ("O1-Assign", O1_AST, overlay(ERRORS, ERRORS.read_text() + "\nOutcome = int\n")),
        ("O1-AnnAssign", O1_AST, overlay(ERRORS, ERRORS.read_text() + "\nOutcome: object = int\n")),
        ("O1-hasattr-package", O1_API, mock.patch.object(battery.cement_runtime, "Resolved", object, create=True)),
        ("O1-hasattr-models", O1_API, mock.patch.object(battery.models, "Outcome", object, create=True)),
        ("O2-extra-removal", O2, overlay(INIT, INIT.read_text().replace('    "Candidate",\n', "", 1))),
        ("O2-extra-addition", O2, overlay(INIT, INIT.read_text().replace('__all__ = [', '__all__ = ["Unexpected",', 1))),
        ("O3-NAME", O3_TOKEN, overlay(ERRORS, ERRORS.read_text() + "\nif False:\n    Resolved\n")),
        ("O3-docstring", O3_DOC, overlay(SYSTEM, SYSTEM.read_text().replace("applies a resolved plan only", "applies a plan", 1))),
        ("O4-survivor-change", O4, overlay(MODELS, MODELS.read_text().replace("min_confirmations: int = 3", "min_confirmations: int = 4", 1))),
        ("O4-renamed-class", O4, overlay(MODELS, MODELS.read_text() + "\nclass RenamedOutcome: pass\n")),
        ("O5-field", O5, mock.patch.object(battery.models, "Candidate", changed_candidate(extra=True))),
        ("O5-annotation", O5, mock.patch.object(battery.models, "Candidate", changed_candidate(annotation="str"))),
        ("O5-default", O5, mock.patch.object(battery.models, "Candidate", changed_candidate(dataclasses.field(default=None)))),
    ]
    for label, name, change in controls:
        with change:
            result, output = run_case(name)
        assert result.failures, f"{label}: control survived\n{output}"
        print(f"{label}: red; failures={len(result.failures)} errors={len(result.errors)}")
    with overlay(ERRORS, ERRORS.read_text() + '\n# Resolved\n"Outcome"\n'):
        result, _ = run_case(O3_TOKEN)
        assert result.wasSuccessful()
    print("O3-comment/string: green (NAME-token positive contrast)")


class ReviewRegressions(unittest.TestCase):
    def test_o1_destructured_assignment_is_detected(self):
        with overlay(ERRORS, ERRORS.read_text() + "\n(Outcome,) = (int,)\n"):
            result, _ = run_case(O1_AST)
            token_result, _ = run_case(O3_TOKEN)
        self.assertFalse(token_result.wasSuccessful(), "control: O3 must see the inserted NAME")
        self.assertFalse(result.wasSuccessful(), "O1 AST gate accepted an Assign target that binds Outcome via tuple unpacking")

    def test_o4_added_top_level_function_is_detected(self):
        with overlay(MODELS, MODELS.read_text() + "\ndef renamed_outcome():\n    return object()\n"):
            result, _ = run_case(O4)
        self.assertFalse(result.wasSuccessful(), "O4 structural gate accepted an extra top-level function definition")

    def test_o5_default_factory_is_detected(self):
        candidate = changed_candidate(dataclasses.field(default_factory=dict))
        self.assertEqual(candidate(output=17).provenance, {})
        with mock.patch.object(battery.models, "Candidate", candidate):
            result, _ = run_case(O5)
        self.assertFalse(result.wasSuccessful(), "O5 ABI gate accepted a new default_factory; Candidate(output=17) no longer requires provenance")


if sys.argv[2] == "controls":
    controls()
elif sys.argv[2] == "red":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewRegressions)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
else:
    raise SystemExit("expected controls | red")
