"""F3: named class/function subjects own decorators + bodies, not sibling definitions."""
import ast
import json
import pathlib
import runpy

ROOT = pathlib.Path(__file__).resolve().parents[2]
PIN = "tests.test_system.SystemTests.test_function_report_public_shape_is_exact_frozen_slotted_and_exported"
triage = runpy.run_path(str(ROOT / ".agent/survivor-triage"))
subjects = json.loads((ROOT / ".agent/decisions/survivor-subjects.json").read_text())[PIN]
source = (ROOT / "src/cement_runtime/models.py").read_text()
spans = triage["_functions"](source)
checked = 0
for node in ast.parse(source).body:
    if not isinstance(node, ast.ClassDef) or f"models.py:{node.name}" not in subjects:
        continue
    first = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
    for line in range(first, node.end_lineno + 1):
        owner = triage["_enclosing"](spans, line)
        assert owner == node.name or str(owner).startswith(f"{node.name}."), (line, owner)
        checked += 1
assert checked > 0
print(f"SHIPPED: {checked} lines in declared class subjects retained")

source = """@decorate
class Subject:
    field: int
    @decorate
    def method(self):
        return 1

@decorate
class Sibling:
    field: int

@decorate
def subject():
    @decorate
    def inner():
        return 2
    return inner()

@decorate
def sibling():
    return 3
"""
spans = triage["_functions"](source)
for node in ast.walk(ast.parse(source)):
    if not isinstance(node, (ast.ClassDef, ast.FunctionDef)):
        continue
    name = {"method": "Subject.method", "inner": "subject.inner"}.get(node.name, node.name)
    for line in (node.decorator_list[0].lineno, node.lineno, node.end_lineno):
        owner = triage["_enclosing"](spans, line)
        assert owner == name or str(owner).startswith(f"{name}."), (line, name, owner)
assert triage["_enclosing"](spans, 7) is None
assert triage["_enclosing"](spans, 10) == "Sibling"
assert triage["_enclosing"](spans, 21) == "sibling"
print("GREEN: decorators + fields + nested methods/functions retained; siblings stay separate")
