"""Open WebUI paste-ins — generated files that embed `cement_runtime` (MAINTAIN W1).

A network-less Open WebUI image installs nothing, so each pasted file must run with no
`cement_runtime` importable, equal the generator's output byte for byte, and refuse an edited
embedded library. `examples/open_webui/generate.py` writes `examples/open_webui/paste-in/`.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

from cement_runtime import Candidate, CompilePolicy, System
from tests.test_open_webui_example import _call, _pydantic

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "open_webui"
PASTE_IN = EXAMPLE / "paste-in"
P, OP = "tenant_a", "extraction_plan"
DOC = {"document": "PHYSICIAN PROGRESS NOTE\nPatient: A\n"}
PLAN = {"fields": ["patient"]}


def _generator() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("open_webui_generate", EXAMPLE / "generate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = _generator()


class _PasteIn(unittest.TestCase):
    """Every load sees a stub `pydantic`, NO installed `cement_runtime` and a restorable path."""

    def setUp(self) -> None:
        saved = list(sys.meta_path)
        self.addCleanup(sys.meta_path.__setitem__, slice(None), saved)
        patcher = mock.patch.dict(sys.modules, {"pydantic": _pydantic(), "cement_runtime": None})
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory(prefix="cement-paste-in-")
        self.addCleanup(directory.cleanup)
        self.directory = pathlib.Path(directory.name)
        self.db = str(self.directory / "ledger.db")

    def _load(self, path: pathlib.Path) -> types.ModuleType:
        spec = importlib.util.spec_from_file_location(f"paste_in_{path.stem}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _packages(self) -> list[str]:
        return sorted(name for name in sys.modules if name.startswith("_cement_runtime_") and "." not in name)

    def _ledger(self, *, publish: bool) -> System:
        system = System(self.db)
        system.register_operation(P, OP, policy=CompilePolicy())
        if publish:
            for _ in range(2):
                proposal = system.submit_proposal(P, OP, DOC, candidate=Candidate(output=PLAN, provenance={}))
                system.review(P, proposal, reviewer="learning-pass", decision="accept")
            system.compile(P, OP)
            system.verify_drafts(P, OP, verified_by="learning-pass")
            manifest = system.inspect_function_promotion(P, OP)
            system.promote_function(
                P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
            )
            system.set_switch(P, OP, mode="follow", actor="ward-lead")
        return system


class PasteInBattery(_PasteIn):
    def test_w1_every_paste_in_equals_the_generator_output(self) -> None:
        self.assertEqual(GENERATOR.stale(ROOT), [])
        self.assertEqual(
            sorted(path.name for path in PASTE_IN.glob("*.py")),
            sorted(path.name for path in EXAMPLE.glob("cement_*.py")),
        )
        self.assertGreaterEqual(len(list(PASTE_IN.glob("*.py"))), 2)

    def test_w1_the_embedded_library_is_the_package_minus_its_cli(self) -> None:
        sources = GENERATOR.runtime_sources(ROOT)
        package = {path.stem for path in (ROOT / "src" / "cement_runtime").glob("*.py")}
        self.assertEqual(set(sources), package - {"cli", "__main__"})
        for path in PASTE_IN.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            assigned = {
                target.id: node.value
                for node in tree.body
                if isinstance(node, ast.Assign)
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            embedded = ast.literal_eval(assigned["_CEMENT_SOURCES"])
            self.assertEqual({name: text.removeprefix("\n") for name, text in embedded.items()}, sources)
            self.assertEqual(ast.literal_eval(assigned["_CEMENT_DIGEST"]), GENERATOR.digest(sources))
            imported = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
            self.assertNotIn("cement_runtime", imported, path.name)

    def test_w1_the_chat_tool_answers_with_no_installed_cement_runtime(self) -> None:
        with self.assertRaises(ImportError):
            import cement_runtime  # noqa: F401 — the positive control: the package is blocked
        self._ledger(publish=True)
        module = self._load(PASTE_IN / "cement_tools.py")
        self.assertTrue(module.System.__module__.startswith("_cement_runtime_"))
        self.assertIsNot(module.System, System)
        tools = module.Tools()
        tools.valves = module.Tools.Valves(ledger_path=self.db, partition=P, operations=OP)
        result = asyncio.run(tools.use_learned_function(OP, DOC))
        self.assertIs(result["covered"], True)
        self.assertEqual(result["output"], PLAN)
        miss = asyncio.run(tools.use_learned_function(OP, {"document": "LAB RESULT SLIP\nTest: CBC\n"}))
        self.assertEqual((miss["covered"], miss["reason"]), (False, "unrecognized"))

    def test_w1_the_filter_retains_a_pair_with_no_installed_cement_runtime(self) -> None:
        system = self._ledger(publish=False)
        module = self._load(PASTE_IN / "cement_filter.py")
        retention = module.Filter()
        retention.valves = module.Filter.Valves(
            ledger_path=self.db, partition=P, deployment_id="ward-7", operations=OP
        )
        output = [
            *_call("c1", "use_learned_function", {"operation": OP, "input": DOC}, {"covered": False}),
            *_call("c2", "record_answer", {"operation": OP, "input": DOC, "output": PLAN}, {"accepted": True}),
        ]
        body = {
            "model": "stub-model",
            "chat_id": "chat-1",
            "id": "msg-a",
            "messages": [
                {"id": "msg-u", "role": "user", "content": "plan this note"},
                {"id": "msg-a", "role": "assistant", "content": "Here is the plan.", "output": output},
            ],
        }
        asyncio.run(retention.outlet(body, __event_emitter__=None, __metadata__={}))
        proposals = system.proposals(P, status="pending")
        self.assertEqual(len(proposals), 1)
        self.assertEqual((proposals[0]["input"], proposals[0]["proposed_output"]), (DOC, PLAN))

    def test_w1_files_of_one_digest_share_one_package(self) -> None:
        modules = [self._load(path) for path in sorted(PASTE_IN.glob("*.py"))]
        self.assertEqual(len(modules), 4)
        tools = modules[0]
        self.assertEqual({module.System for module in modules}, {tools.System})
        self.assertEqual(self._packages(), [tools._CEMENT_PACKAGE])
        importers = [finder for finder in sys.meta_path if getattr(finder, "package", None)]
        self.assertEqual([finder.package for finder in importers], [tools._CEMENT_PACKAGE])

    def test_w1_an_edited_embedded_library_refuses_to_load(self) -> None:
        text = (PASTE_IN / "cement_tools.py").read_text(encoding="utf-8")
        anchor = '"""Cement public API."""'
        self.assertEqual(text.count(anchor), 1)
        edited = self.directory / "cement_tools.py"
        edited.write_text(text.replace(anchor, '"""Cement public API, edited."""'), encoding="utf-8")
        with self.assertRaisesRegex(ImportError, "embedded cement_runtime was edited"):
            self._load(edited)
        self.assertEqual(self._packages(), [])

    def test_w6_an_edited_copy_refuses_after_a_clean_copy_loaded(self) -> None:
        text = (PASTE_IN / "cement_tools.py").read_text(encoding="utf-8")
        self._load(PASTE_IN / "cement_tools.py")
        anchor = '"""Cement public API."""'
        edited = self.directory / "cement_tools.py"
        edited.write_text(text.replace(anchor, '"""Cement public API, edited."""'), encoding="utf-8")
        with self.assertRaisesRegex(ImportError, "embedded cement_runtime was edited"):
            self._load(edited)

    def test_w7_a_bare_interpreter_loads_the_embedded_library(self) -> None:
        # Under `python -I -S` nothing preloads importlib.machinery; a source with no import of its
        # own gives the loader no help, so a finder installed before that import re-enters itself.
        import subprocess

        source = "from cement_runtime.json_value import canonicalize\n\nprint(canonicalize({'a': 1}).text)\n"
        rendered = GENERATOR.render(source, GENERATOR.runtime_sources(ROOT), "0")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "bare.py"
            path.write_text(rendered, encoding="utf-8")
            run = subprocess.run(
                [sys.executable, "-I", "-S", "-B", str(path)],
                capture_output=True, text=True, timeout=60, check=False,
            )
        self.assertEqual((run.returncode, run.stdout), (0, '{"a":1}\n'), run.stderr[-500:])

    def test_w6_the_generator_refuses_import_shapes_it_cannot_rebind(self) -> None:
        sources = {"__init__": '"""x"""\n', "json_value": '"""y"""\n'}
        for label, source in (
            ("dotted without alias", "import cement_runtime.json_value\n\nX = 1\n"),
            ("mixed import", "import json as j, cement_runtime as cr\n\nX = (j, cr)\n"),
            ("statement between", "from cement_runtime import System\nOFFSET = 5\n"
             "from cement_runtime.json_value import canonicalize\n\nX = (System, OFFSET, canonicalize)\n"),
        ):
            with self.subTest(label), self.assertRaises(SystemExit):
                GENERATOR.render(source, sources, "0")

    def test_w1_the_generator_refuses_what_a_paste_in_cannot_carry(self) -> None:
        sources = {"__init__": '"""x"""\n'}
        good = "from __future__ import annotations\n\nfrom cement_runtime import System\n\nX = System\n"
        self.assertIn("X = System", GENERATOR.render(good, sources, "0"))
        for label, source in (
            ("triple quote", good + "Y = '''y'''\n"),
            ("rewritten prefix", good + "# from utils import z\n"),
            ("no library import", "import json\n\nX = json\n"),
            ("library before others", "from cement_runtime import System\nimport json\n\nX = (System, json)\n"),
        ):
            with self.subTest(label), self.assertRaises(SystemExit):
                GENERATOR.render(source, sources, "0")
        with self.assertRaises(SystemExit):
            GENERATOR.render(good, {"__init__": "Y = '''y'''\n"} | {"x": "from config import a\n"}, "0")


if __name__ == "__main__":
    unittest.main()
