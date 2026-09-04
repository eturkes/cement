"""M3.6a1 obligation battery — one test per contract obligation.

DIFF-BLIND. Written from `.agent/decisions/m3u6a1-contract.md` and this
worktree's own pre-implementation baseline. The migrated `tests/` and
`examples/` trees, `m3u6a1-surgery.py`, `git show main:` and `git diff main`
are all out of bounds.

Each test asserts the PROPERTY its obligation states, derived from the shipped
tree by AST or by running the named gate. It never pins a helper name, a
variable name, an occurrence count or an assertion spelling that the contract
does not itself state: those are the migration author's choice, and a pin on
one of them goes red against correct code.

Graded by `.agent/decisions/m3u6a1-battery-validate.py`.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from collections.abc import Iterator
from typing import Any
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE = "6fb4d92"
SURGERY = ROOT / ".agent" / "decisions" / "m3u6a1-surgery.py"
LIFECYCLE = frozenset({"handle", "request_status"})


def _environment(root: pathlib.Path) -> dict[str, str]:
    environment = os.environ.copy()
    prefixes = [str(root), str(root / "src")]
    if environment.get("PYTHONPATH"):
        prefixes.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(prefixes)
    return environment


def _run(
    command: list[str],
    *,
    cwd: pathlib.Path = ROOT,
    root: pathlib.Path = ROOT,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=_environment(root),
        timeout=timeout,
        check=False,
    )


def _result(result: subprocess.CompletedProcess[str]) -> str:
    return (
        f"command={result.args!r} rc={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _required_match(pattern: str, text: str) -> re.Match[str]:
    match = re.search(pattern, text)
    if match is None:
        raise AssertionError(f"pattern did not match: {pattern!r}")
    return match


def _source(root: pathlib.Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def _tree(root: pathlib.Path, path: str) -> ast.Module:
    return ast.parse(_source(root, path), filename=path)


def _baseline_source(path: str) -> str:
    result = _run(["git", "show", f"{BASELINE}:{path}"])
    if result.returncode != 0:
        raise AssertionError(_result(result))
    return result.stdout


def _baseline_tree(path: str) -> ast.Module:
    return ast.parse(_baseline_source(path), filename=f"{BASELINE}:{path}")


def _top_definitions(tree: ast.Module) -> Iterator[ast.FunctionDef]:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            yield node
        elif isinstance(node, ast.ClassDef):
            yield from (
                member for member in node.body if isinstance(member, ast.FunctionDef)
            )


def _top_definition(root: pathlib.Path, path: str, name: str) -> ast.FunctionDef:
    matches = [node for node in _top_definitions(_tree(root, path)) if node.name == name]
    if len(matches) != 1:
        raise AssertionError(f"{path}::{name}: expected one top definition, got {len(matches)}")
    return matches[0]


def _class_method(root: pathlib.Path, path: str, name: str) -> ast.FunctionDef:
    tree = _tree(root, path)
    matches = [
        member
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        for member in node.body
        if isinstance(member, ast.FunctionDef) and member.name == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"{path}::{name}: expected one class method, got {len(matches)}")
    return matches[0]


def _module_function(root: pathlib.Path, path: str, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in _tree(root, path).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"{path}::{name}: expected one module function, got {len(matches)}")
    return matches[0]


def _calls(node: ast.AST, name: str) -> list[ast.Call]:
    return [
        item
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and (
            isinstance(item.func, ast.Attribute)
            and item.func.attr == name
            or isinstance(item.func, ast.Name)
            and item.func.id == name
        )
    ]


def _attribute_calls(node: ast.AST, names: set[str] | frozenset[str]) -> list[ast.Call]:
    return [
        item
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and isinstance(item.func, ast.Attribute)
        and item.func.attr in names
    ]


def _lifecycle_count(node: ast.AST) -> int:
    return len(_attribute_calls(node, LIFECYCLE))


def _consumer_map(root: pathlib.Path) -> dict[str, int]:
    consumers: dict[str, int] = {}
    paths = sorted((root / "tests").rglob("*.py")) + sorted(
        (root / "examples").rglob("*.py")
    )
    for file_path in paths:
        relative = file_path.relative_to(root).as_posix()
        for definition in _top_definitions(_tree(root, relative)):
            count = _lifecycle_count(definition)
            if count:
                consumers[f"{relative}::{definition.name}"] = count
    return consumers


def _census() -> dict[str, Any]:
    return json.loads(
        (ROOT / ".agent" / "decisions" / "m3u6a1-census.json").read_text(
            encoding="utf-8"
        )
    )


def _fallback() -> dict[str, Any]:
    return json.loads(
        (ROOT / ".agent" / "decisions" / "m3u6a1-fallback.json").read_text(
            encoding="utf-8"
        )
    )


def _owner_at(tree: ast.Module, line: int) -> ast.FunctionDef:
    matches = [
        node
        for node in _top_definitions(tree)
        if node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    if len(matches) != 1:
        raise AssertionError(f"line {line}: expected one owning definition, got {len(matches)}")
    return matches[0]


def _shape_owners(shape: str) -> list[tuple[str, str]]:
    owners: list[tuple[str, str]] = []
    sites = _fallback()["sites"]
    if not isinstance(sites, dict):
        raise TypeError("fallback sites must be an object")
    trees: dict[str, ast.Module] = {}
    for key, row in sites.items():
        if not isinstance(row, dict) or row.get("shape") != shape:
            continue
        path, raw_line = key.rsplit(":", 1)
        tree = trees.setdefault(path, _baseline_tree(path))
        owners.append((path, _owner_at(tree, int(raw_line)).name))
    return owners


def _test_id(path: str, name: str) -> str:
    tree = _tree(ROOT, path)
    module = path.removesuffix(".py").replace("/", ".")
    matches: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            matches.append(f"{module}.{name}")
        elif isinstance(node, ast.ClassDef) and any(
            isinstance(member, ast.FunctionDef) and member.name == name
            for member in node.body
        ):
            matches.append(f"{module}.{node.name}.{name}")
    if len(matches) != 1:
        raise AssertionError(f"{path}::{name}: expected one test id, got {matches}")
    return matches[0]


def _run_test_methods(specifications: list[tuple[str, str]]) -> subprocess.CompletedProcess[str]:
    ids = [_test_id(path, name) for path, name in specifications]
    return _run([sys.executable, "-m", "unittest", *ids], timeout=600)


def _string_constants(node: ast.AST) -> list[str]:
    return [
        item.value
        for item in ast.walk(node)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    ]


def _parameters(node: ast.FunctionDef) -> list[str]:
    return [
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    ]


def _confirm_call_owners(tree: ast.AST) -> set[str]:
    owners = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _attribute_calls(node, {"confirm"}):
            owners.add(node.name)
    return owners


def _unused_parameters(node: ast.FunctionDef) -> set[str]:
    loaded = {
        item.id
        for statement in node.body
        for item in ast.walk(statement)
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load)
    }
    # `self`/`cls` are bound by the method protocol, never migration residue: removing
    # one rewrites the call convention of every caller. D14's domain is the parameters
    # the migration itself could drop.
    return set(_parameters(node)) - loaded - {"self", "cls"}


def _attribute_path(node: ast.AST) -> tuple[str, tuple[str, ...]] | None:
    attributes: list[str] = []
    while isinstance(node, ast.Attribute):
        attributes.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return node.id, tuple(reversed(attributes))


def _relation_claims(node: ast.AST, expected: bool = True) -> list[tuple[ast.AST, bool]]:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _relation_claims(node.operand, not expected)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And) and expected:
        return [claim for value in node.values for claim in _relation_claims(value, True)]
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        left, right = node.left, node.comparators[0]
        operator = node.ops[0]
        equal = isinstance(operator, (ast.Eq, ast.Is))
        unequal = isinstance(operator, (ast.NotEq, ast.IsNot))
        for candidate, constant in ((left, right), (right, left)):
            if (
                isinstance(constant, ast.Constant)
                and isinstance(constant.value, bool)
                and (equal or unequal)
            ):
                value = constant.value if equal else not constant.value
                return _relation_claims(candidate, value if expected else not value)
        if (
            isinstance(left, (ast.Tuple, ast.List))
            and isinstance(right, (ast.Tuple, ast.List))
            and len(left.elts) == len(right.elts)
            and equal
            and expected
        ):
            return [
                claim
                for left_item, right_item in zip(left.elts, right.elts, strict=True)
                for claim in _relation_claims(
                    ast.Compare(left=left_item, ops=[ast.Eq()], comparators=[right_item]),
                    True,
                )
            ]
    return [(node, expected)]


def _boolean_claims(node: ast.FunctionDef) -> list[tuple[int, str, tuple[str, ...], bool]]:
    claims: list[tuple[int, str, tuple[str, ...], bool]] = []
    for item in ast.walk(node):
        relations: list[tuple[ast.AST, bool]] = []
        if isinstance(item, ast.Assert):
            relations = _relation_claims(item.test)
        elif (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr
            in {"assertTrue", "assertFalse", "assertEqual", "assertIs", "assertNotEqual", "assertIsNot"}
        ):
            if item.func.attr == "assertTrue" and item.args:
                relations = _relation_claims(item.args[0], True)
            elif item.func.attr == "assertFalse" and item.args:
                relations = _relation_claims(item.args[0], False)
            elif len(item.args) >= 2:
                operator: ast.cmpop
                if item.func.attr in {"assertEqual", "assertIs"}:
                    operator = ast.Eq()
                else:
                    operator = ast.NotEq()
                relations = _relation_claims(
                    ast.Compare(left=item.args[0], ops=[operator], comparators=[item.args[1]])
                )
        for expression, value in relations:
            path = _attribute_path(expression)
            if path is not None:
                claims.append((getattr(item, "lineno", 0), path[0], path[1], value))
    return claims


def _resolve_bindings(node: ast.FunctionDef) -> list[tuple[int, str]]:
    bindings: list[tuple[int, str]] = []
    for item in ast.walk(node):
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(item, ast.Assign) and len(item.targets) == 1:
            target, value = item.targets[0], item.value
        elif isinstance(item, ast.AnnAssign):
            target, value = item.target, item.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        resolve_calls = _attribute_calls(value, {"resolve"})
        if len(resolve_calls) == 1:
            bindings.append((resolve_calls[0].lineno, target.id))
    return bindings


def _assert_calls_fit(
    case: unittest.TestCase,
    node: ast.FunctionDef,
    calls: list[ast.Call],
    *,
    bound: bool,
) -> None:
    positional = [*node.args.posonlyargs, *node.args.args]
    allowed = len(positional) - int(bound)
    names = set(_parameters(node))
    for call in calls:
        if not any(isinstance(argument, ast.Starred) for argument in call.args):
            case.assertLessEqual(len(call.args), allowed, ast.unparse(call))
        for keyword in call.keywords:
            if keyword.arg is not None:
                case.assertIn(keyword.arg, names, ast.unparse(call))


@contextlib.contextmanager
def _detached_worktree(revision: str) -> Iterator[pathlib.Path]:
    with tempfile.TemporaryDirectory(prefix="cement-m3u6a1-") as directory:
        path = pathlib.Path(directory) / "tree"
        added = _run(["git", "worktree", "add", "--detach", str(path), revision])
        if added.returncode != 0:
            raise AssertionError(_result(added))
        try:
            yield path
        finally:
            _run(["git", "worktree", "remove", "--force", str(path)])
            _run(["git", "worktree", "prune"])


def _copy_surgery(root: pathlib.Path) -> pathlib.Path:
    target = root / ".agent" / "decisions" / SURGERY.name
    shutil.copy2(SURGERY, target)
    return target


def _run_demo(root: pathlib.Path = ROOT, *flags: str) -> subprocess.CompletedProcess[str]:
    return _run(
        [sys.executable, *flags, "run_demo.py"],
        cwd=root / "examples" / "hospital_ocr",
        root=root,
    )


@contextlib.contextmanager
def _demo_module() -> Iterator[Any]:
    example = ROOT / "examples" / "hospital_ocr"
    module_name = "_m3u6a1_run_demo"
    spec = importlib.util.spec_from_file_location(module_name, example / "run_demo.py")
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load hospital OCR demo")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(example))
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(module_name, None)
        sys.path.remove(str(example))


def _text_blocks(text: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if current is None:
            if line == "```text":
                current = []
        elif line == "```":
            blocks.append(current)
            current = None
        else:
            current.append(line)
    if current is not None:
        raise AssertionError("unterminated text fence")
    return ["".join(f"{line}\n" for line in block) for block in blocks]


class MigrationBatteryTests(unittest.TestCase):

    def test_d01_m3u6a1_census_py_reports_surviving_migrate_0_with_unruled(self) -> None:
        """D01 — `m3u6a1-census.py` reports `SURVIVING-MIGRATE: 0`, with `UNRULED`, `STALE`,
        `MEASURE-DRIFT`, `UNGROUNDED-OVERRIDE` and `BAD-VERDICT` all 0.

        CORRECTED-BY C02, C11
        """
        result = _run(
            [sys.executable, str(ROOT / ".agent" / "decisions" / "m3u6a1-census.py")]
        )
        self.assertEqual(result.returncode, 0, _result(result))
        for label in (
            "UNRULED",
            "STALE",
            "MEASURE-DRIFT",
            "UNGROUNDED-OVERRIDE",
            "BAD-VERDICT",
            "SURVIVING-MIGRATE",
        ):
            self.assertRegex(result.stdout, rf"(?m)^{re.escape(label)}: 0$")
        self.assertIn("RESULT: PASS", result.stdout)

        corrected = [
            (
                "tests/test_system.py",
                "test_proposal_paths_translate_malformed_persisted_json",
            ),
            (
                "tests/test_system.py",
                "test_orphaned_binding_fails_closed_and_stays_distinct_from_an_absent_proposal",
            ),
            (
                "tests/test_system.py",
                "test_review_rejects_cross_table_state_corruption",
            ),
            (
                "tests/test_system.py",
                "test_function_report_pending_request_join_is_like_and_case_exact",
            ),
        ]
        corrected_result = _run_test_methods(corrected)
        self.assertEqual(corrected_result.returncode, 0, _result(corrected_result))

    def test_d02_m3u6a1_rule_census_py_check_reports_in_sync(self) -> None:
        """D02 — `m3u6a1-rule-census.py --check` reports `IN-SYNC`.
        """
        result = _run(
            [
                sys.executable,
                str(ROOT / ".agent" / "decisions" / "m3u6a1-rule-census.py"),
                "--check",
            ]
        )
        self.assertEqual(result.returncode, 0, _result(result))
        self.assertEqual(result.stdout.strip(), "IN-SYNC")

    def test_d03_no_definition_ruled_retain_is_edited_to_remove_its(self) -> None:
        """D03 — No definition ruled RETAIN is edited to remove its lifecycle call. The census
        cannot see the difference between a migrated site and a deleted one, so the RETAIN
        set is pinned by name and by call count.

        CORRECTED-BY C03
        """
        retained = [
            row for row in _census()["definitions"] if row["verdict"] == "RETAIN"
        ]
        self.assertEqual(len(retained), 23)
        specifications: list[tuple[str, str]] = []
        for row in retained:
            path, name = row["site"].split("::", 1)
            definition = _top_definition(ROOT, path, name)
            self.assertEqual(
                _lifecycle_count(definition),
                row["sites"],
                f"{row['site']} lost or gained a retained lifecycle call",
            )
            specifications.append((path, name))
        specifications.append(
            (
                "tests/test_system.py",
                "test_unknown_resolved_source_kind_fails_closed_at_storage",
            )
        )
        result = _run_test_methods(list(dict.fromkeys(specifications)))
        self.assertEqual(result.returncode, 0, _result(result))

    def test_d04_system_handle_and_system_request_status_still_ship(self) -> None:
        """D04 — `System.handle` and `System.request_status` still ship, unchanged, and are
        still reachable. The unit deletes no production surface.

        CORRECTED-BY C15
        """
        unchanged = _run(["git", "diff", "--exit-code", BASELINE, "--", "src"])
        self.assertEqual(unchanged.returncode, 0, _result(unchanged))

        from cement_runtime import System

        for name in ("handle", "request_status"):
            with self.subTest(name=name):
                method = getattr(System, name, None)
                self.assertIsNotNone(method)
                self.assertTrue(callable(method))

    def test_d05_the_surviving_lifecycle_consumers_after_this_unit_are(self) -> None:
        """D05 — The surviving lifecycle consumers after this unit are exactly: the 23 RETAIN
        definitions, the two ACTOR tests among them, and the library itself.

        CORRECTED-BY C11
        """
        retained = {
            row["site"]: row["sites"]
            for row in _census()["definitions"]
            if row["verdict"] == "RETAIN"
        }
        self.assertEqual(len(retained), 23)
        self.assertEqual(sum(retained.values()), 45)
        self.assertEqual(_consumer_map(ROOT), retained)

        system_tree = _tree(ROOT, "src/cement_runtime/system.py")
        methods = {
            node.name
            for node in _top_definitions(system_tree)
            if node.name in LIFECYCLE
        }
        self.assertEqual(methods, LIFECYCLE)

    def test_d06_each_of_the_four_miss_guarded_sites_carries_a_resolve_call(self) -> None:
        """D06 — Each of the four MISS-GUARDED sites carries a `resolve` call asserting
        `verification.passed` true and `match.matched` false, positioned BEFORE its
        `propose` call in the same test body.
        """
        owners = _shape_owners("MISS-GUARDED")
        self.assertEqual(len(owners), 4)
        for path, name in owners:
            with self.subTest(site=f"{path}::{name}"):
                definition = _top_definition(ROOT, path, name)
                proposes = sorted(
                    _attribute_calls(definition, {"propose"}), key=lambda call: call.lineno
                )
                claims = _boolean_claims(definition)
                preserved = False
                for resolve_line, binding in _resolve_bindings(definition):
                    later = [call.lineno for call in proposes if call.lineno > resolve_line]
                    if not later:
                        continue
                    propose_line = min(later)
                    local = {
                        (attributes, value)
                        for line, root, attributes, value in claims
                        if resolve_line < line < propose_line and root == binding
                    }
                    preserved |= (
                        (("verification", "passed"), True) in local
                        and (("match", "matched"), False) in local
                    )
                self.assertTrue(
                    preserved,
                    f"{path}::{name} lacks the verified-miss claims before propose",
                )

    def test_d07_each_of_the_four_miss_guarded_sites_retains_a_propose_call(self) -> None:
        """D07 — Each of the four MISS-GUARDED sites retains a `propose` call, so P1's row-
        state equivalence holds site by site.
        """
        owners = _shape_owners("MISS-GUARDED")
        self.assertEqual(len(owners), 4)
        for path, name in owners:
            with self.subTest(site=f"{path}::{name}"):
                definition = _top_definition(ROOT, path, name)
                resolves = _attribute_calls(definition, {"resolve"})
                proposes = _attribute_calls(definition, {"propose"})
                self.assertTrue(
                    any(propose.lineno > resolve.lineno for resolve in resolves for propose in proposes),
                    f"{path}::{name} dropped the row-creating propose call",
                )

    def test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss(self) -> None:
        """D08 — No FACTORY site gains a `resolve` call. A verified-miss assertion at a site
        with no once-promoted artifact asserts nothing and would misrepresent the shape
        table.
        """
        shapes: dict[tuple[str, str], list[str]] = defaultdict(list)
        sites = _fallback()["sites"]
        self.assertIsInstance(sites, dict)
        baseline_trees: dict[str, ast.Module] = {}
        for key, row in sites.items():
            path, raw_line = key.rsplit(":", 1)
            tree = baseline_trees.setdefault(path, _baseline_tree(path))
            owner = _owner_at(tree, int(raw_line)).name
            shapes[(path, owner)].append(row["shape"])

        factory_owners = {
            owner_shapes: values
            for owner_shapes, values in shapes.items()
            if "FACTORY" in values
        }
        self.assertTrue(factory_owners)
        for (path, name), values in factory_owners.items():
            with self.subTest(site=f"{path}::{name}"):
                baseline = _owner_at(
                    baseline_trees[path],
                    next(
                        int(key.rsplit(":", 1)[1])
                        for key, row in sites.items()
                        if key.startswith(f"{path}:")
                        and _owner_at(
                            baseline_trees[path], int(key.rsplit(":", 1)[1])
                        ).name
                        == name
                    ),
                )
                current = _top_definition(ROOT, path, name)
                expected = len(_attribute_calls(baseline, {"resolve"})) + values.count(
                    "MISS-GUARDED"
                )
                self.assertEqual(
                    len(_attribute_calls(current, {"resolve"})),
                    expected,
                    f"{path}::{name} added resolve outside a MISS-GUARDED site",
                )

    def test_d09_m3u6a1_fallback_py_reruns_from_committed_state_and_reports(self) -> None:
        """D09 — `m3u6a1-fallback.py` reruns from committed state and reports `RESULT: PASS`,
        with its per-call positive control at 0 failed and 0 unreadable. After migration its
        target population shrinks; the grader's `UNOBSERVED-MIGRATE` control stays 0.
        """
        result = _run(
            [sys.executable, str(ROOT / ".agent" / "decisions" / "m3u6a1-fallback.py")],
            timeout=600,
        )
        self.assertEqual(result.returncode, 0, _result(result))
        self.assertIn("RESULT: PASS", result.stdout)
        control = _required_match(
            r"(?m)^CONTROL-DIGESTS: (\d+) checked, (\d+) failed, (\d+) unreadable$",
            result.stdout,
        )
        checked, failed, unreadable = map(int, control.groups())
        self.assertGreater(checked, 0)
        self.assertEqual((failed, unreadable), (0, 0))
        targets = _required_match(r"(?m)^TARGETS: (\d+)$", result.stdout)
        retained_sites = sum(
            row["sites"]
            for row in _census()["definitions"]
            if row["verdict"] == "RETAIN"
        )
        self.assertEqual(int(targets.group(1)), retained_sites)
        self.assertNotIn("UNOBSERVED-MIGRATE:", result.stdout)

    def test_d10_tests_test_system_py_confirm_loses_its_request_id(self) -> None:
        """D10 — `tests/test_system.py::confirm` loses its `request_id` positional parameter.
        Every one of its 41 call sites drops the corresponding argument.

        CORRECTED-BY C12
        """
        path = "tests/test_system.py"
        helper = _class_method(ROOT, path, "confirm")
        self.assertNotIn("request_id", _parameters(helper))
        baseline_calls = _attribute_calls(_baseline_tree(path), {"confirm"})
        current_calls = _attribute_calls(_tree(ROOT, path), {"confirm"})
        self.assertEqual(len(baseline_calls), 41)
        # C03's third repair re-bases `test_operation_revision_invalidates_every_old_
        # request_path` onto a direct `handle` + `review` plant, so exactly one RETAIN
        # consumer leaves the population. Pin WHICH site left, not just the arithmetic.
        self.assertEqual(len(current_calls), 40)
        self.assertEqual(
            _confirm_call_owners(_baseline_tree(path))
            - _confirm_call_owners(_tree(ROOT, path)),
            {"test_operation_revision_invalidates_every_old_request_path"},
        )
        _assert_calls_fit(self, helper, current_calls, bound=True)

    def test_d11_tests_test_system_py_confirm_scope_loses_its_request_id(self) -> None:
        """D11 — `tests/test_system.py::_confirm_scope` loses its `request_id` positional
        parameter. Every one of its 65 call sites drops the corresponding argument.
        """
        path = "tests/test_system.py"
        helper = _class_method(ROOT, path, "_confirm_scope")
        self.assertNotIn("request_id", _parameters(helper))
        baseline_calls = _attribute_calls(_baseline_tree(path), {"_confirm_scope"})
        current_calls = _attribute_calls(_tree(ROOT, path), {"_confirm_scope"})
        self.assertEqual(len(baseline_calls), 65)
        self.assertEqual(len(current_calls), len(baseline_calls))
        _assert_calls_fit(self, helper, current_calls, bound=True)

    def test_d12_tests_test_system_py_promote_scope_loses_its_prefix(self) -> None:
        """D12 — `tests/test_system.py::_promote_scope` loses its `prefix` positional
        parameter, because `prefix` exists only to build the two request identifiers
        `_confirm_scope` no longer takes. RULED REMOVE, not keep: a parameter that every
        caller supplies and no callee reads is exactly the residue a migration unit must not
        leave behind, and the surgery script rewrites its 14 call sites at the same cost as
        leaving them. The removal is observable — a retained `prefix` fails D14's dead-
        parameter check.
        """
        path = "tests/test_system.py"
        helper = _class_method(ROOT, path, "_promote_scope")
        self.assertNotIn("prefix", _parameters(helper))
        baseline_calls = _attribute_calls(_baseline_tree(path), {"_promote_scope"})
        current_calls = _attribute_calls(_tree(ROOT, path), {"_promote_scope"})
        self.assertEqual(len(baseline_calls), 14)
        self.assertEqual(len(current_calls), len(baseline_calls))
        _assert_calls_fit(self, helper, current_calls, bound=True)

    def test_d13_tests_test_resolve_battery_py_confirm_tests_test_proposal(self) -> None:
        """D13 — `tests/test_resolve_battery.py::_confirm`,
        `tests/test_proposal_binding_battery.py::_promoted_conflict_fixture` and
        `tests/test_hospital_ocr_example.py::_promoted_example_ledger` migrate onto
        `propose`; any parameter that becomes unread is removed with its arguments.

        CORRECTED-BY C13, C14
        """
        helpers = [
            ("tests/test_resolve_battery.py", "_confirm", True, 1),
            (
                "tests/test_proposal_binding_battery.py",
                "_promoted_conflict_fixture",
                True,
                6,
            ),
            (
                "tests/test_hospital_ocr_example.py",
                "_promoted_example_ledger",
                False,
                3,
            ),
        ]
        for path, name, bound, expected_calls in helpers:
            with self.subTest(helper=f"{path}::{name}"):
                helper = (
                    _class_method(ROOT, path, name)
                    if bound
                    else _module_function(ROOT, path, name)
                )
                self.assertEqual(len(_attribute_calls(helper, {"handle"})), 0)
                self.assertGreaterEqual(len(_attribute_calls(helper, {"propose"})), 1)
                self.assertEqual(_unused_parameters(helper), set())
                baseline_calls = _calls(_baseline_tree(path), name)
                current_calls = _calls(_tree(ROOT, path), name)
                self.assertEqual(len(baseline_calls), expected_calls)
                self.assertEqual(len(current_calls), len(baseline_calls))
                _assert_calls_fit(self, helper, current_calls, bound=bound)

    def test_d14_no_migrated_helper_retains_a_parameter_that_no_statement(self) -> None:
        """D14 — No migrated helper retains a parameter that no statement in its body reads.
        Checked over the shipped source by AST, not by grep.

        CORRECTED-BY C13
        """
        helpers = [
            ("tests/test_system.py", _class_method(ROOT, "tests/test_system.py", "confirm")),
            (
                "tests/test_system.py",
                _class_method(ROOT, "tests/test_system.py", "_confirm_scope"),
            ),
            (
                "tests/test_system.py",
                _class_method(ROOT, "tests/test_system.py", "_promote_scope"),
            ),
            (
                "tests/test_resolve_battery.py",
                _class_method(ROOT, "tests/test_resolve_battery.py", "_confirm"),
            ),
            (
                "tests/test_proposal_binding_battery.py",
                _class_method(
                    ROOT,
                    "tests/test_proposal_binding_battery.py",
                    "_promoted_conflict_fixture",
                ),
            ),
            (
                "tests/test_hospital_ocr_example.py",
                _module_function(
                    ROOT,
                    "tests/test_hospital_ocr_example.py",
                    "_promoted_example_ledger",
                ),
            ),
        ]
        outer = _top_definition(
            ROOT,
            "tests/test_system.py",
            "test_function_report_reaches_every_compiler_block_reason_through_public_apis",
        )
        nested = [
            node
            for node in ast.walk(outer)
            if isinstance(node, ast.FunctionDef) and node.name == "confirm"
        ]
        self.assertEqual(len(nested), 1)
        helpers.append(("tests/test_system.py", nested[0]))

        for path, helper in helpers:
            with self.subTest(helper=f"{path}:{helper.name}:{helper.lineno}"):
                self.assertEqual(_unused_parameters(helper), set())
                baseline_matches = [
                    node
                    for node in ast.walk(_baseline_tree(path))
                    if isinstance(node, ast.FunctionDef)
                    and node.name == helper.name
                    and _lifecycle_count(node)
                ]
                if baseline_matches:
                    self.assertEqual(len(_attribute_calls(helper, {"handle"})), 0)
                    self.assertGreaterEqual(
                        len(_attribute_calls(helper, {"propose"})), 1
                    )

    def test_d14a_tests_test_system_py_holds_two_definitions_named_confirm(self) -> None:
        """D14a — `tests/test_system.py` holds TWO definitions named `confirm`: the method at
        `:226`, called as `self.confirm(...)` 41 times, and a nested function at `:14452`
        shadowing it inside
        `test_function_report_reaches_every_compiler_block_reason_through_public_apis`,
        which takes `system` as its first parameter and is called bare. The two carry
        different signatures and different lifecycle sites (`:235` and `:14461`), so each is
        migrated under its own anchor. A bare `confirm(` anchor spans both and is forbidden.

        CORRECTED-BY C06, C12
        """
        path = "tests/test_system.py"
        tree = _tree(ROOT, path)
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "confirm"
        ]
        self.assertEqual(len(definitions), 2)
        method = _class_method(ROOT, path, "confirm")
        outer = _top_definition(
            ROOT,
            path,
            "test_function_report_reaches_every_compiler_block_reason_through_public_apis",
        )
        nested = [
            node
            for node in ast.walk(outer)
            if isinstance(node, ast.FunctionDef) and node.name == "confirm"
        ]
        self.assertEqual(len(nested), 1)
        nested_function = nested[0]
        self.assertEqual(_parameters(method)[0], "self")
        self.assertEqual(_parameters(nested_function)[0], "system")
        self.assertNotEqual(_parameters(method), _parameters(nested_function))
        for definition in (method, nested_function):
            self.assertEqual(len(_attribute_calls(definition, {"handle"})), 0)
            self.assertGreaterEqual(len(_attribute_calls(definition, {"propose"})), 1)
        self.assertEqual(len(_attribute_calls(tree, {"confirm"})), 40)
        bare_calls = [
            call
            for call in _calls(outer, "confirm")
            if isinstance(call.func, ast.Name)
        ]
        self.assertTrue(bare_calls)

    def test_d15_the_migration_lands_through_one_idempotent_script_m3u6a1(self) -> None:
        """D15 — The migration lands through ONE idempotent script, `m3u6a1-surgery.py`, which
        asserts the expected occurrence count of every anchor before applying it and prints
        `no-op` on a second run against a repaired tree. A repeated fragment aborts loudly
        rather than mutating the wrong span.

        CORRECTED-BY C02, C05
        """
        self.assertTrue(SURGERY.is_file())
        with _detached_worktree("HEAD") as repaired:
            result = _run(
                [sys.executable, str(repaired / SURGERY.relative_to(ROOT))],
                cwd=repaired,
                root=repaired,
            )
            self.assertEqual(result.returncode, 0, _result(result))
            self.assertIn("no-op", result.stdout + result.stderr)
            dirty = _run(
                ["git", "status", "--short", "--", "tests", "examples"],
                cwd=repaired,
                root=repaired,
            )
            self.assertEqual(dirty.returncode, 0, _result(dirty))
            self.assertEqual(dirty.stdout, "")

        with _detached_worktree(BASELINE) as repeated:
            script = _copy_surgery(repeated)
            demo = repeated / "examples" / "hospital_ocr" / "run_demo.py"
            text = demo.read_text(encoding="utf-8")
            tree = ast.parse(text)
            main = next(
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main"
            )
            fragment = ast.get_source_segment(text, main)
            self.assertIsNotNone(fragment)
            demo.write_text(f"{text}\n\n{fragment}\n", encoding="utf-8")
            before = demo.read_bytes()
            result = _run([sys.executable, str(script)], cwd=repeated, root=repeated)
            self.assertNotEqual(result.returncode, 0, _result(result))
            self.assertEqual(demo.read_bytes(), before)

    def test_d16_the_script_is_replayable_from_a_clean_base_applying_it_to(self) -> None:
        """D16 — The script is replayable from a clean base: applying it to a detached worktree
        at this unit's opening commit reproduces the shipped tree, with every divergence
        recorded as a named exception in section 10.

        CORRECTED-BY C05
        """
        self.assertTrue(SURGERY.is_file())
        expected_result = _run(
            [
                "git",
                "diff",
                "--name-only",
                f"{BASELINE}..HEAD",
                "--",
                "tests",
                "examples",
            ]
        )
        self.assertEqual(expected_result.returncode, 0, _result(expected_result))
        expected = {
            path
            for path in expected_result.stdout.splitlines()
            if path != "tests/test_migration_battery.py"
        }
        self.assertTrue(expected)

        with _detached_worktree(BASELINE) as replay:
            script = _copy_surgery(replay)
            result = _run([sys.executable, str(script)], cwd=replay, root=replay)
            self.assertEqual(result.returncode, 0, _result(result))
            changed_result = _run(
                ["git", "diff", "--name-only", BASELINE, "--", "tests", "examples"],
                cwd=replay,
                root=replay,
            )
            self.assertEqual(changed_result.returncode, 0, _result(changed_result))
            changed = set(changed_result.stdout.splitlines())
            self.assertEqual(changed, expected)
            for path in sorted(expected):
                with self.subTest(path=path):
                    self.assertEqual((replay / path).read_bytes(), (ROOT / path).read_bytes())

    def test_d17_multi_line_anchors_wherever_a_fragment_repeats_a_count_1(self) -> None:
        """D17 — Multi-line anchors wherever a fragment repeats. A `count == 1` assertion is
        what converts the occurrence-index trap into a loud failure.

        CORRECTED-BY C06
        """
        self.assertTrue(SURGERY.is_file())
        with _detached_worktree(BASELINE) as shifted:
            script = _copy_surgery(shifted)
            system_tests = shifted / "tests" / "test_system.py"
            system_tests.write_text(
                "\n" * 37 + system_tests.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            first = _run([sys.executable, str(script)], cwd=shifted, root=shifted)
            self.assertEqual(first.returncode, 0, _result(first))
            second = _run([sys.executable, str(script)], cwd=shifted, root=shifted)
            self.assertEqual(second.returncode, 0, _result(second))
            self.assertIn("no-op", second.stdout + second.stderr)

            for row in _census()["definitions"]:
                if row["verdict"] not in {"MIGRATE", "MIGRATE-RESOLVE"}:
                    continue
                path, name = row["site"].split("::", 1)
                definition = _top_definition(shifted, path, name)
                self.assertEqual(
                    _lifecycle_count(definition),
                    0,
                    f"line-shifted replay missed {row['site']}",
                )
            self.assertNotIn(
                "request_id",
                _parameters(_class_method(shifted, "tests/test_system.py", "confirm")),
            )
            self.assertNotIn(
                "request_id",
                _parameters(
                    _class_method(shifted, "tests/test_system.py", "_confirm_scope")
                ),
            )
            self.assertNotIn(
                "prefix",
                _parameters(
                    _class_method(shifted, "tests/test_system.py", "_promote_scope")
                ),
            )

    def test_d18_examples_hospital_ocr_run_demo_py_s_seven_system_handle(self) -> None:
        """D18 — `examples/hospital_ocr/run_demo.py`'s seven `system.handle` sites migrate:
        five onto `propose`, and the two `Resolved(source="artifact")` sites onto `resolve`.

        CORRECTED-BY C07
        """
        main = _module_function(ROOT, "examples/hospital_ocr/run_demo.py", "main")
        counts = {
            name: len(_attribute_calls(main, {name}))
            for name in ("handle", "propose", "resolve")
        }
        self.assertEqual(counts, {"handle": 0, "propose": 5, "resolve": 2})

    def test_d19_the_walkthrough_promotes_its_function_set_immediately(self) -> None:
        """D19 — The walkthrough promotes its function set immediately after each artifact
        promotion, so Acts 2 and 3 answer through `resolve`. P2 measures that `resolve`
        fails `persisted-function-receipt` at the un-checkpointed Act-2 state and matches
        once the set is promoted, so the checkpoint MOVES rather than the assertion
        weakening.

        CORRECTED-BY C09
        """
        with _demo_module() as demo:
            events: list[tuple[str, int | bool]] = []
            verifications: list[object] = []
            real_checkpoint = demo.checkpoint_function
            real_resolve = demo.System.resolve
            real_verify = demo.System.verify_function

            def recording_checkpoint(system):
                document = real_checkpoint(system)
                events.append(("checkpoint", len(document.input_hashes)))
                return document

            def recording_resolve(system, *args, **kwargs):
                resolution = real_resolve(system, *args, **kwargs)
                events.append(
                    (
                        "resolve",
                        resolution.match is not None and resolution.match.matched,
                    )
                )
                return resolution

            def recording_verify(system, *args, **kwargs):
                verification = real_verify(system, *args, **kwargs)
                verifications.append(verification)
                return verification

            with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                demo, "checkpoint_function", recording_checkpoint
            ), mock.patch.object(
                demo.System, "resolve", recording_resolve
            ), mock.patch.object(
                demo.System, "verify_function", recording_verify
            ):
                demo.main()

        self.assertEqual(
            events,
            [
                ("checkpoint", 1),
                ("resolve", True),
                ("checkpoint", 2),
                ("resolve", True),
            ],
        )
        self.assertEqual(len(verifications), 4)

    def test_d20_act_5_keeps_export_and_identity_and_loses_its_becomes_one(self) -> None:
        """D20 — Act 5 keeps export and identity and loses its "becomes one exportable
        function" framing, because the set is now promoted earlier. The demo teaches M3's
        post-trim lifecycle: propose, review, compile, verify, promote artifact, promote
        set, resolve.
        """
        path = "examples/hospital_ocr/run_demo.py"
        main = _module_function(ROOT, path, "main")
        lifecycle = sorted(
            [
                (call.lineno, call.func.attr)
                for call in ast.walk(main)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr
                in {"propose", "review", "compile", "verify", "promote", "resolve"}
            ]
            + [
                (call.lineno, "checkpoint_function")
                for call in _calls(main, "checkpoint_function")
            ]
        )
        cursor = -1
        for name in (
            "propose",
            "review",
            "compile",
            "verify",
            "promote",
            "checkpoint_function",
            "resolve",
        ):
            candidates = [
                line for line, candidate in lifecycle if line > cursor and candidate == name
            ]
            self.assertTrue(candidates, f"demo omits lifecycle step {name!r}")
            cursor = min(candidates)

        result = _run_demo()
        self.assertEqual(result.returncode, 0, _result(result))
        self.assertNotIn("becomes one exportable function", result.stdout)
        act_five = result.stdout.split("=== Act 5:", 1)[1].split(
            "=== Audit event trace ===", 1
        )[0]
        self.assertRegex(act_five, r"(?i)function hash")
        self.assertIn("Exported bundle:", act_five)

    def test_d21_the_demo_still_refuses_to_run_under_o_oo_and_its_assert(self) -> None:
        """D21 — The demo still refuses to run under `-O`/`-OO`, and its `assert` verdict count
        is re-derived rather than carried; the count moves with the act structure.
        """
        path = "examples/hospital_ocr/run_demo.py"
        # The refusal claim is MODULE-wide - every verdict in the demo is an `assert`,
        # and `-O` strips them wherever they sit. Counting inside `main` alone reads 33
        # against the module's 35 and cannot match the shipped pin.
        current_count = sum(
            isinstance(node, ast.Assert) for node in ast.walk(_tree(ROOT, path))
        )
        baseline_count = sum(
            isinstance(node, ast.Assert) for node in ast.walk(_baseline_tree(path))
        )
        self.assertNotEqual(current_count, baseline_count)

        test_path = "tests/test_hospital_ocr_example.py"
        test_source = _source(ROOT, test_path)
        refusal_test = _top_definition(
            ROOT,
            test_path,
            "test_demo_refuses_to_run_where_python_removes_its_assertions",
        )
        refusal_segment = ast.get_source_segment(test_source, refusal_test)
        if refusal_segment is None:
            self.fail("cannot recover the optimization-refusal test source")
        self.assertRegex(refusal_segment, rf"\b{current_count}\b")

        for flag in ("-O", "-OO"):
            with self.subTest(flag=flag):
                result = _run_demo(ROOT, flag)
                self.assertNotEqual(result.returncode, 0, _result(result))
                self.assertNotIn("All checks passed.", result.stdout)

    def test_d22_the_example_readme_s_text_transcript_block_is_regenerated(self) -> None:
        """D22 — The example README's `text` transcript block is regenerated from the demo's
        own output. Both dynamic-value masks and their occurrence counts move with the act
        structure, and
        `DemoTranscriptTests.test_demo_output_matches_the_pinned_readme_transcript` keeps
        asserting exactly one match per mask.

        CORRECTED-BY C05, C15
        """
        result = _run_demo()
        self.assertEqual(result.returncode, 0, _result(result))
        artifact_mask = re.compile(r"art_[0-9a-f]{32}")
        function_mask = re.compile(r"[0-9a-f]{64}")
        self.assertEqual(len(artifact_mask.findall(result.stdout)), 1)
        self.assertEqual(len(function_mask.findall(result.stdout)), 1)
        masked = artifact_mask.sub(
            "art_<hex>", function_mask.sub("<function-hash>", result.stdout)
        )
        blocks = _text_blocks(
            (ROOT / "examples" / "hospital_ocr" / "README.md").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(masked, blocks[0])

        frame = _run_test_methods(
            [
                (
                    "tests/test_hospital_ocr_example.py",
                    "test_demo_output_matches_the_pinned_readme_transcript",
                )
            ]
        )
        self.assertEqual(frame.returncode, 0, _result(frame))

    def test_d23_examples_hospital_ocr_readme_md_208_and_216_name_the(self) -> None:
        """D23 — `examples/hospital_ocr/README.md:208` and `:216` name the vanishing
        `request.resolved_by_artifact` event inside the pinned transcript. Both are
        rewritten by regeneration, never by hand. No shipped prose names an event kind the
        migrated demo no longer emits.

        CORRECTED-BY C07
        """
        paths = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
        paths.extend(sorted((ROOT / "examples").glob("*/README.md")))
        offenders = {
            path.relative_to(ROOT).as_posix(): [
                line_number
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                )
                if "request.resolved_by_artifact" in line
            ]
            for path in paths
        }
        offenders = {path: lines for path, lines in offenders.items() if lines}
        self.assertEqual(offenders, {})

    def test_d24_tests_test_proposal_binding_battery_py_test_b30_and_the(self) -> None:
        """D24 — `tests/test_proposal_binding_battery.py::test_b30_...` and the `test_d03_...`
        payload pin stay RETAIN and stay green. They pin the `{"request_id": ...}` payload
        that P1 measures as the migration's sole attributable row difference, so retiring
        either would silently delete the record of that difference.

        CORRECTED-BY C15
        """
        targets = [
            (
                "tests/test_proposal_binding_battery.py",
                "test_b30_the_six_owned_event_payloads_are_2",
            ),
            (
                "tests/test_submission_battery.py",
                "test_d03_the_event_is_proposal_created_with",
            ),
        ]
        rows = {row["site"]: row for row in _census()["definitions"]}
        for path, name in targets:
            site = f"{path}::{name}"
            with self.subTest(site=site):
                self.assertEqual(rows[site]["verdict"], "RETAIN")
                self.assertEqual(
                    _lifecycle_count(_top_definition(ROOT, path, name)),
                    rows[site]["sites"],
                )
        result = _run_test_methods(targets)
        self.assertEqual(result.returncode, 0, _result(result))

    def test_d25_m3_3_s_p06_byte_span_freeze_on_system_handle_stays_green(self) -> None:
        """D25 — M3.3's P06 byte-span freeze on `System.handle` stays green. The unit edits no
        production source, so the span must not move; the three slicing conventions (12,866
        B `1182130a2b3a`, 12,867 B `cd60036faf5c`, 12,862 B `c27e71b0b4c7`) are recorded
        here so a lens on the wrong row is checkable.

        CORRECTED-BY C10, C15
        """
        path = "src/cement_runtime/system.py"
        source = _source(ROOT, path)
        tree = ast.parse(source)
        system = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "System"
        )
        handle = next(
            node
            for node in system.body
            if isinstance(node, ast.FunctionDef) and node.name == "handle"
        )
        kept = "".join(
            source.splitlines(keepends=True)[handle.lineno - 1 : handle.end_lineno]
        )
        stripped = kept.rstrip("\r\n")
        segment = ast.get_source_segment(source, handle)
        if segment is None:
            self.fail("cannot recover the shipped handle source")
        measured = tuple(
            (len(value.encode()), hashlib.sha256(value.encode()).hexdigest()[:12])
            for value in (stripped, kept, segment)
        )

        baseline_source = _baseline_source(path)
        baseline_tree = ast.parse(baseline_source)
        baseline_system = next(
            node
            for node in baseline_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "System"
        )
        baseline_handle = next(
            node
            for node in baseline_system.body
            if isinstance(node, ast.FunctionDef) and node.name == "handle"
        )
        baseline_kept = "".join(
            baseline_source.splitlines(keepends=True)[
                baseline_handle.lineno - 1 : baseline_handle.end_lineno
            ]
        )
        baseline_segment = ast.get_source_segment(baseline_source, baseline_handle)
        if baseline_segment is None:
            self.fail("cannot recover the baseline handle source")
        baseline_measured = tuple(
            (len(value.encode()), hashlib.sha256(value.encode()).hexdigest()[:12])
            for value in (
                baseline_kept.rstrip("\r\n"),
                baseline_kept,
                baseline_segment,
            )
        )
        self.assertEqual(measured, baseline_measured)

        restored = tuple(
            (len(value.encode()), hashlib.sha256(value.encode()).hexdigest()[:12])
            for value in (
                text.replace("PROVENANCE_MAX_BYTES", "65_536")
                for text in (stripped, kept, segment)
            )
        )
        self.assertEqual(
            restored,
            (
                (12_866, "1182130a2b3a"),
                (12_867, "cd60036faf5c"),
                (12_862, "c27e71b0b4c7"),
            ),
        )

        frames = _run_test_methods(
            [
                (
                    "tests/test_submission.py",
                    "test_handle_is_byte_identical_to_the_unit_baseline",
                ),
                (
                    "tests/test_submission_battery.py",
                    "test_p06_handle_is_12_866_b_1182130a2b3a",
                ),
                (
                    "tests/test_submission_battery.py",
                    "test_p06_three_slicing_conventions_are_distinct",
                ),
            ]
        )
        self.assertEqual(frames.returncode, 0, _result(frames))

    def test_d26_m3_5b_s_d01_pin_at_tests_test_cli_removal_battery_py_617(self) -> None:
        """D26 — M3.5b's D01 pin at `tests/test_cli_removal_battery.py:617`, asserting
        `System.handle` and `System.request_status` still ship as library methods, stays
        green.

        CORRECTED-BY C15
        """
        from cement_runtime import System

        self.assertTrue(callable(getattr(System, "handle", None)))
        self.assertTrue(callable(getattr(System, "request_status", None)))
        result = _run_test_methods(
            [
                (
                    "tests/test_cli_removal_battery.py",
                    "test_d01_m3_5b_ships_system_handle_and_system_request_status_as",
                )
            ]
        )
        self.assertEqual(result.returncode, 0, _result(result))

    def test_d27_m3_5b_s_d15a_six_module_byte_identity_freeze_stays_green(self) -> None:
        """D27 — M3.5b's D15a six-module byte-identity freeze stays green.

        CORRECTED-BY C15
        """
        result = _run_test_methods(
            [
                (
                    "tests/test_cli_removal_battery.py",
                    "test_d15a_the_six_runtime_modules_stay_byte_identical_to_their_3",
                )
            ]
        )
        self.assertEqual(result.returncode, 0, _result(result))

    def test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last(self) -> None:
        """D28 — Gate 1 stays green at every commit, never only at the last one. A migration
        that lands red and is repaired later forfeits the axis's own guarantee.

        This battery is the instrument, not part of what it measures: every checkout drops
        `tests/test_migration_battery.py` before the inner run. Keeping it turns D28 into its
        own subject — each battery-bearing revision re-enters this method, and the nesting
        alone exhausts the timeout.
        """
        revision_result = _run(
            [
                "git",
                "rev-list",
                "--reverse",
                f"{BASELINE}..HEAD",
                "--",
                ".agent/decisions/m3u6a1-surgery.py",
                "tests",
                "examples",
                ":(exclude)tests/test_migration_battery.py",
            ]
        )
        self.assertEqual(revision_result.returncode, 0, _result(revision_result))
        revisions = revision_result.stdout.splitlines()
        self.assertTrue(revisions, "no migration commit exists after the opening commit")
        for revision in revisions:
            with self.subTest(revision=revision), _detached_worktree(revision) as tree:
                (tree / "tests" / pathlib.Path(__file__).name).unlink(missing_ok=True)
                result = _run(
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-t",
                        ".",
                    ],
                    cwd=tree,
                    root=tree,
                    timeout=600,
                )
                self.assertEqual(result.returncode, 0, _result(result))
                ran = _required_match(
                    r"(?m)^Ran (\d+) tests? in ", result.stdout + result.stderr
                )
                self.assertGreaterEqual(int(ran.group(1)), 949)


if __name__ == "__main__":
    unittest.main()
