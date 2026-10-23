"""p89: every dict a public `cement_runtime` function returns is typed per field.

The records are TypedDicts (`cement_runtime.models`, `cement_runtime.projection`): runtime values
stay plain dicts, so the CLI's JSON is unchanged, while mypy sees each field's own type.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
import pathlib
import subprocess
import sys
import types
import typing
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "typed_records_caller.py"
MODULES = tuple(sorted(path.stem for path in (ROOT / "src" / "cement_runtime").glob("[!_]*.py")))


def _untyped(annotation: object) -> bool:
    """A bare `dict[...]` at the top, or inside a list, tuple or optional; `JSONValue` (the union
    that admits a dict among its JSON shapes) is a JSON document, not a record."""

    origin = typing.get_origin(annotation)
    arguments = typing.get_args(annotation)
    if annotation is dict or origin is dict:
        return True
    if origin in (typing.Union, types.UnionType) and {bool, int, str, type(None)} <= set(arguments):
        return False
    return any(_untyped(argument) for argument in arguments) if origin else False


class TypedRecordTests(unittest.TestCase):
    def test_no_public_function_returns_an_untyped_dict(self) -> None:
        offenders = []
        checked = 0
        for name in MODULES:
            module = importlib.import_module(f"cement_runtime.{name}")
            owners = [module, *(value for value in vars(module).values() if inspect.isclass(value))]
            for owner in owners:
                if inspect.isclass(owner) and owner.__module__ != module.__name__:
                    continue
                for attribute, value in vars(owner).items():
                    function = value.__func__ if isinstance(value, (classmethod, staticmethod)) else value
                    if attribute.startswith("_") or not inspect.isfunction(function):
                        continue
                    if function.__module__ != module.__name__:
                        continue
                    checked += 1
                    returned = typing.get_type_hints(function).get("return")
                    if _untyped(returned):
                        offenders.append(f"{name}.{function.__qualname__} -> {returned}")
        self.assertEqual(offenders, [])
        self.assertGreaterEqual(checked, 60)  # anti-collapse: the walk saw the public API

    def test_the_caller_fixture_binds_every_record_field_to_its_type(self) -> None:
        from cement_runtime import models, projection

        records = [
            value
            for module in (models, projection)
            for value in vars(module).values()
            if typing.is_typeddict(value) and value.__module__ == module.__name__
        ]
        self.assertGreaterEqual(len(records), 20)
        bound = {
            node.slice.value
            for node in ast.walk(ast.parse(FIXTURE.read_text(encoding="utf-8")))
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        }
        missing = sorted(
            f"{record.__name__}.{field}"
            for record in records
            for field in record.__annotations__
            if field not in bound
        )
        self.assertEqual(missing, [])
        # MYPYPATH outranks site-packages, so the fixture checks against THIS tree's source even
        # where the venv's editable install points at another checkout (D28's replays).
        checked = subprocess.run(
            [sys.executable, "-m", "mypy", "--strict", "--disallow-any-expr", str(FIXTURE)],
            cwd=ROOT,
            env={**os.environ, "MYPYPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            (checked.returncode, checked.stdout.strip()),
            (0, "Success: no issues found in 1 source file"),
            checked.stdout + checked.stderr,
        )


if __name__ == "__main__":
    unittest.main()
