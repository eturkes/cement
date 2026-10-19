"""M3.6a3 removal battery — the seven dead outcome types leave the package.

Contract: `.agent/decisions/m3u6a3-contract.md`. BASE = the gate-tooling squash, the unit's own
opening state, read from git so a later unit's edits to the tree never redden a settled question;
HEAD-side frames read the working tree because their subject IS the shipped package.
"""

from __future__ import annotations

import ast
import dataclasses
import io
import pathlib
import subprocess
import tokenize
import unittest

import cement_runtime
import cement_runtime.models as models

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "629577d"  # the gate-tooling squash on main
DELETED = (
    "Resolved",
    "ReviewRequired",
    "InProgress",
    "FallbackFailed",
    "Rejected",
    "ReconciliationRequired",
    "Outcome",
)
EXPORTED = DELETED[:-1]
PRESERVED = ("CandidateRequest", "Candidate", "ReviewResult", "ProposalView")


def _git_text(revision: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _src_paths() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--", "src"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.split()
    return [path for path in listed if path.endswith(".py")]


def _parsed_all(source: str) -> list[str]:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            return list(ast.literal_eval(node.value))
    raise AssertionError("no __all__")


def _bound_names(target: ast.expr) -> list[str]:
    """Every name an assignment target binds, destructuring (`(a, *b) = …`) included."""
    return [node.id for node in ast.walk(target) if isinstance(node, ast.Name)]


def _top_definitions(source: str) -> list[tuple[str, str]]:
    lines = source.splitlines()
    result = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            name = node.targets[0].id
        else:
            continue
        start = min([node.lineno, *(item.lineno for item in getattr(node, "decorator_list", []))])
        result.append((name, "\n".join(lines[start - 1 : node.end_lineno])))
    return result


class OutcomeRemovalBattery(unittest.TestCase):
    def test_o1_no_src_module_defines_a_deleted_type(self) -> None:
        defined = []
        for path in _src_paths():
            for node in ast.walk(ast.parse((ROOT / path).read_text(encoding="utf-8"))):
                names: list[str] = []
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    names = [node.name]
                elif isinstance(node, ast.Assign):
                    names = [name for target in node.targets for name in _bound_names(target)]
                elif isinstance(node, ast.AnnAssign):
                    names = _bound_names(node.target)
                defined += [f"{path}:{node.lineno}:{name}" for name in names if name in DELETED]
        self.assertEqual(defined, [])
        self.assertGreaterEqual(len(_src_paths()), 10)  # anti-collapse: the scan saw the package

    def test_o1_neither_package_nor_models_exposes_a_deleted_type(self) -> None:
        for name in DELETED:
            with self.subTest(name=name):
                self.assertFalse(hasattr(cement_runtime, name))
                self.assertFalse(hasattr(models, name))

    def test_o2_all_loses_exactly_the_six_exports(self) -> None:
        base = _parsed_all(_git_text(BASE, "src/cement_runtime/__init__.py"))
        head = _parsed_all((ROOT / "src/cement_runtime/__init__.py").read_text(encoding="utf-8"))
        self.assertEqual(sorted(set(base) & set(EXPORTED)), sorted(EXPORTED))  # BASE had them
        self.assertEqual(head, [name for name in base if name not in EXPORTED])

    def test_o3_no_src_token_names_a_deleted_type(self) -> None:
        hits = []
        for path in _src_paths():
            source = (ROOT / path).read_text(encoding="utf-8")
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.NAME and token.string in DELETED:
                    hits.append(f"{path}:{token.start[0]}:{token.string}")
        self.assertEqual(hits, [])

    def test_o3_the_resolve_docstring_keeps_its_rule(self) -> None:
        source = (ROOT / "src/cement_runtime/system.py").read_text(encoding="utf-8")
        self.assertNotIn("``Resolved``", source)
        self.assertIn("applies a resolved plan only", source)

    def test_o4_models_survivors_are_byte_identical_and_in_order(self) -> None:
        base = _top_definitions(_git_text(BASE, "src/cement_runtime/models.py"))
        head = _top_definitions((ROOT / "src/cement_runtime/models.py").read_text(encoding="utf-8"))
        self.assertEqual(sorted({name for name, _ in base} & set(DELETED)), sorted(DELETED))
        self.assertEqual(head, [(name, span) for name, span in base if name not in DELETED])

    def test_o5_preserved_models_keep_their_abi(self) -> None:
        base_source = _git_text(BASE, "src/cement_runtime/models.py")
        base_tree = ast.parse(base_source)
        for name in PRESERVED:
            with self.subTest(name=name):
                cls = getattr(models, name)
                base_class = next(
                    node for node in base_tree.body
                    if isinstance(node, ast.ClassDef) and node.name == name
                )
                base_fields = [
                    (node.target.id, ast.unparse(node.annotation),
                     None if node.value is None else ast.unparse(node.value))
                    for node in base_class.body
                    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                ]
                head_fields = [
                    (field.name, field.type if isinstance(field.type, str) else repr(field.type),
                     None if field.default is dataclasses.MISSING else repr(field.default))
                    for field in dataclasses.fields(cls)
                ]
                self.assertEqual([item[:2] for item in head_fields], [item[:2] for item in base_fields])
                self.assertEqual(
                    [item[2] for item in head_fields],
                    [None if value is None else repr(ast.literal_eval(value)) for *_, value in base_fields],
                )
                # Requiredness: a `default_factory` keeps `default` MISSING yet drops the argument.
                self.assertEqual(
                    [
                        field.default is dataclasses.MISSING
                        and field.default_factory is dataclasses.MISSING
                        for field in dataclasses.fields(cls)
                    ],
                    [value is None for *_, value in base_fields],
                )
        self.assertIn("request_id", {field.name for field in dataclasses.fields(models.CandidateRequest)})


if __name__ == "__main__":
    unittest.main()
