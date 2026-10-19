"""M3.7 relocation battery — the command runtime leaves the core for `examples/command_source/`.

Owner seed (a) (`.agent/spec.md` Decisions, M3 seeds): `CandidateSource` stays core while
`CommandCandidateSource`, the subreaper supervisor, `example_adapter.py` and the adapter-protocol
document relocate to an optional example surface, byte-identical, with no import back into the
core. BASE = the M3.6b squash, read from git so a later unit's edits never redden a settled move;
the relocated side reads the working tree because its subject IS the shipped example.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "93007ac"  # the M3.6b squash on main
SURFACE = "examples/command_source"
MOVED = {
    "src/cement_runtime/_command_supervisor.py": f"{SURFACE}/_command_supervisor.py",
    "src/cement_runtime/example_adapter.py": f"{SURFACE}/example_adapter.py",
}
RELOCATED_NAMES = {"command_source", "_command_supervisor", "example_adapter", "examples"}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def _class_span(source: str, name: str) -> str:
    node = next(
        node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == name
    )
    segment = ast.get_source_segment(source, node)
    assert segment is not None
    return segment


def _all(source: str) -> list[str]:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            return list(ast.literal_eval(node.value))
    raise AssertionError("no __all__")


class RelocationBattery(unittest.TestCase):
    def test_r1_moved_modules_are_byte_identical_and_leave_the_package(self) -> None:
        tracked = set(_git("ls-files").split())
        for old, new in MOVED.items():
            with self.subTest(module=new):
                base = subprocess.run(
                    ["git", "show", f"{BASE}:{old}"], cwd=ROOT, check=True, capture_output=True
                ).stdout
                self.assertEqual((ROOT / new).read_bytes(), base)
                self.assertNotIn(old, tracked)
                self.assertIn(new, tracked)

    def test_r2_the_class_span_is_byte_identical(self) -> None:
        base = _class_span(_git("show", f"{BASE}:src/cement_runtime/source.py"), "CommandCandidateSource")
        moved = _class_span(
            (ROOT / SURFACE / "command_source.py").read_text(encoding="utf-8"), "CommandCandidateSource"
        )
        self.assertEqual(moved, base)

    def test_r3_the_core_keeps_the_protocol_alone(self) -> None:
        base_source = _git("show", f"{BASE}:src/cement_runtime/source.py")
        head_source = (ROOT / "src/cement_runtime/source.py").read_text(encoding="utf-8")
        self.assertEqual(_class_span(head_source, "CandidateSource"), _class_span(base_source, "CandidateSource"))
        # Structural, not a spelling: the module = docstring + imports + the one protocol class,
        # so the runtime cannot return under another name (a rename passes a name check).
        body = ast.parse(head_source).body
        kept = [
            node for node in body
            if not isinstance(node, (ast.Import, ast.ImportFrom))
            and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
        ]
        self.assertEqual([type(node).__name__ for node in kept], ["ClassDef"])
        self.assertEqual(kept[0].name, "CandidateSource")  # type: ignore[attr-defined]
        imported = {
            node.module if isinstance(node, ast.ImportFrom) else alias.name
            for node in body if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertEqual(imported, {"__future__", "typing", "models"})
        base_all = _all(_git("show", f"{BASE}:src/cement_runtime/__init__.py"))
        head_all = _all((ROOT / "src/cement_runtime/__init__.py").read_text(encoding="utf-8"))
        self.assertIn("CommandCandidateSource", base_all)
        self.assertEqual(head_all, [name for name in base_all if name != "CommandCandidateSource"])

    def test_r3_the_process_machinery_left_the_core(self) -> None:
        # The supervisor's process control (`subprocess`, `signal`) lives in the example alone.
        reached = []
        for path in (p for p in _git("ls-files", "--", "src").split() if p.endswith(".py")):
            for node in ast.walk(ast.parse((ROOT / path).read_text(encoding="utf-8"))):
                names = (
                    [alias.name for alias in node.names] if isinstance(node, ast.Import)
                    else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                )
                reached += [f"{path}:{name}" for name in names if name.split(".")[0] in {"subprocess", "signal"}]
        self.assertEqual(reached, [])
        base = _git("show", f"{BASE}:src/cement_runtime/source.py")
        self.assertIn("import subprocess", base)  # anti-collapse: BASE's core held it

    def test_r4_no_core_module_imports_the_example_surface(self) -> None:
        reached = []
        paths = [p for p in _git("ls-files", "--", "src").split() if p.endswith(".py")]
        self.assertGreaterEqual(len(paths), 10)  # anti-collapse: the scan saw the package
        for path in paths:
            for node in ast.walk(ast.parse((ROOT / path).read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or "", *(alias.name for alias in node.names)]
                else:
                    continue
                reached += [
                    f"{path}:{node.lineno}:{name}"
                    for name in names
                    if set(name.split(".")) & RELOCATED_NAMES
                ]
        self.assertEqual(reached, [])
        probe = (
            "import sys, cement_runtime, cement_runtime.cli, cement_runtime.system\n"
            f"print(sorted(m for m in sys.modules if set(m.split('.')) & set({sorted(RELOCATED_NAMES)!r})))"
        )
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        loaded = subprocess.run(
            [sys.executable, "-c", probe], cwd=ROOT, env=env, check=True, capture_output=True, text=True
        ).stdout.strip()
        self.assertEqual(loaded, "[]")

    def test_r5_the_example_readme_runs_and_names_every_module(self) -> None:
        readme = (ROOT / SURFACE / "README.md").read_text(encoding="utf-8")
        modules = sorted(path.name for path in (ROOT / SURFACE).glob("*.py"))
        self.assertEqual(modules, ["_command_supervisor.py", "command_source.py", "example_adapter.py"])
        # p54: every operator-facing module (no leading underscore) appears in the shipped doc.
        for module in (name for name in modules if not name.startswith("_")):
            with self.subTest(module=module):
                self.assertIn(module.removesuffix(".py"), readme)
        # p54: the README's one Python block runs the bundled stub and prints what it states.
        (snippet,) = [block.split("```", 1)[0] for block in readme.split("```python\n")[1:]]
        self.assertIn("example_adapter.py", snippet)
        (stated,) = re.findall(r"The block prints `([^`]+)`", readme)
        with tempfile.TemporaryDirectory(prefix="cement-relocation-") as tmp:
            os.symlink(ROOT / "examples", pathlib.Path(tmp) / "examples")
            env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            ran = subprocess.run(
                [sys.executable, "-c", snippet], cwd=tmp, env=env, capture_output=True, text=True, timeout=60
            )
        self.assertEqual((ran.returncode, ran.stdout.strip()), (0, stated), ran.stderr)


if __name__ == "__main__":
    unittest.main()
