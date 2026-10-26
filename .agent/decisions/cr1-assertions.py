"""F5: assertion grading accepts AST calls, not inert comments or strings."""
import ast
import contextlib
import io
import pathlib
import runpy
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT


def fill(stub, comment_only):
    lines = stub.splitlines(keepends=True)
    calls = [n for n in ast.walk(ast.parse(stub))
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
             and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "fail"]
    for node in sorted(calls, key=lambda n: n.lineno, reverse=True):
        indent = " " * node.col_offset
        code = ("# self.assertTrue(True)\n" + indent + "pass") if comment_only else "self.assertTrue(True)"
        lines[node.lineno - 1:node.end_lineno] = [indent + code + "\n"]
    result = "".join(lines)
    assertions = [n for n in ast.walk(ast.parse(result))
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr.startswith("assert")]
    assert len(assertions) == (0 if comment_only else len(calls))
    return result, len(calls)


def grade(call):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = call()
    return rc, output.getvalue()


failed = False
with tempfile.TemporaryDirectory(prefix="F5-", dir=SCRATCH) as directory:
    path = pathlib.Path(directory) / "battery.py"
    for name in ("m3u5a-battery", "m3u5a-suite", "m3u5b-battery", "m3u6a1-battery"):
        ns = runpy.run_path(str(ROOT / f".agent/decisions/{name}-validate.py"))
        stub = ns["emit_stub"](ROOT) if name == "m3u6a1-battery" else ns["emit_stub"]()
        if name == "m3u5b-battery":
            call = lambda: ns["grade"](path, ns["DEFAULT_CONTROLS"])
        elif name == "m3u6a1-battery":
            call = lambda: ns["grade"](path, ROOT)
        else:
            call = lambda: ns["grade"](path)
        positive, count = fill(stub, False)
        path.write_text(positive)
        rc, output = grade(call)
        assert rc == 0, (name, rc, output)
        print(f"CONTROL: {name}: {count} assertion calls; rc=0")
        negative, _ = fill(stub, True)
        path.write_text(negative)
        rc, output = grade(call)
        counter = next(line for line in output.splitlines() if line.startswith("ASSERTIONLESS:"))
        print(f"OBSERVED: {name}: 0 assertion calls, {count} comments; rc={rc}; {counter}")
        failed |= rc == 0
if failed:
    print("RED: four battery graders accept comment-only assertions and report zero assertionless tests")
    raise SystemExit(1)
print("GREEN")

has_assertion = runpy.run_path(str(ROOT / ".agent/decisions/battery_ast.py"))["has_assertion"]
for body, expected in (
    ("self.assertEqual (\n        1, 1\n    )", True),
    ('self.fail("expected")', True),
    ('"self.assertTrue(True)"', False),
    ("pass # self.assertTrue(True)", False),
    ("other.assertTrue(True)", False),
    ("self.assertTrue", False),
):
    node = ast.parse("def test_shape(self):\n    " + body + "\n").body[0]
    assert has_assertion(node) == expected, (body, expected)
print("GREEN: call whitespace + fail accepted; comment/string/foreign object/uncalled attribute rejected")
