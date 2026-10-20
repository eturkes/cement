"""Open WebUI local instance — the launcher's wiring (MAINTAIN W5).

`examples/open_webui/local.py` pastes the four generated files, the skill and two workspace
models into a local Open WebUI 0.12.3. The live run is the spot-check; these frames pin what a
wrong wiring would hide: chat users must never reach the learning tool or the switch, every
pasted file is the generated (self-contained) one, and the model key never enters argv.
"""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import types
import unittest
from unittest import mock

from tests.test_open_webui_example import FILTER

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "open_webui"


def _launcher() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("open_webui_local", EXAMPLE / "local.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOCAL = _launcher()


class LocalLauncherBattery(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-local-")
        self.addCleanup(directory.cleanup)
        self.paths = LOCAL._paths(pathlib.Path(directory.name))
        self.items = {(kind, name): form for kind, name, form in LOCAL.plan("m-1", self.paths["ledger"])}

    def test_w5_chat_users_get_the_chat_tool_and_the_filter_alone(self) -> None:
        chat = self.items[("model", LOCAL.CHAT_MODEL)]
        learning = self.items[("model", LOCAL.LEARNING_MODEL)]
        self.assertEqual(
            {key: chat["meta"].get(key) for key in ("toolIds", "filterIds", "skillIds", "actionIds")},
            {"toolIds": ["cement"], "filterIds": ["cement_filter"], "skillIds": None, "actionIds": None},
        )
        self.assertEqual(
            {key: learning["meta"].get(key) for key in ("toolIds", "filterIds", "skillIds", "actionIds")},
            {"toolIds": ["cement_learning"], "filterIds": None, "skillIds": ["cement-learn"],
             "actionIds": ["cement_switch"]},
        )
        for form in (chat, learning):
            self.assertEqual((form["base_model_id"], form["params"]), ("m-1", {"function_calling": "native"}))
        # Built-in skill tools off ⇒ Open WebUI 0.12.3 injects the attached skill's whole text;
        # on, it lists the skill and gpt-6-luna skipped `view_skill` in the live run.
        self.assertEqual(learning["meta"].get("builtinTools"), {"skills": False})
        self.assertNotIn("builtinTools", chat["meta"])

    def test_w5_every_pasted_file_is_the_generated_one_with_one_ledger(self) -> None:
        pasted = {
            name: form["content"] for (kind, name), form in self.items.items() if kind in ("tool", "function")
        }
        files = {"cement": "cement_tools", "cement_learning": "cement_learning",
                 "cement_filter": "cement_filter", "cement_switch": "cement_admin"}
        self.assertEqual(set(pasted), set(files))
        for name, stem in files.items():
            self.assertEqual(pasted[name], (EXAMPLE / "paste-in" / f"{stem}.py").read_text(encoding="utf-8"))
            self.assertIn("_CEMENT_SOURCES = {", pasted[name])
        valves = [form["valves"] for (kind, _), form in self.items.items() if kind in ("tool", "function")]
        self.assertEqual({(v["ledger_path"], v["partition"], v["operations"]) for v in valves},
                         {(str(self.paths["ledger"]), LOCAL.PARTITION, LOCAL.OPERATIONS)})
        self.assertTrue(self.paths["ledger"].is_relative_to(self.paths["data"]))
        skill = self.items[("skill", "cement-learn")]
        self.assertEqual(skill["content"], (EXAMPLE / "cement-learn" / "SKILL.md").read_text(encoding="utf-8"))

    def test_w5_the_guide_names_one_operation_and_its_exact_input(self) -> None:
        guide = FILTER._operations(LOCAL.OPERATIONS)
        self.assertEqual(list(guide), ["extraction_plan"])
        self.assertIn('{"document":', guide["extraction_plan"])

    def test_w5_the_instance_runs_offline_and_the_key_stays_out_of_argv(self) -> None:
        self.paths["secret"].parent.mkdir(parents=True, exist_ok=True)
        with mock.patch.dict("os.environ", {}, clear=True):
            env = LOCAL._environment(self.paths, "http://127.0.0.1:1/v1", "k-secret")
        expected = {
            "DATA_DIR": str(self.paths["data"]), "WEBUI_AUTH": "False", "OFFLINE_MODE": "True",
            "ENABLE_PERSISTENT_CONFIG": "False", "ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS": "False",
            "BYPASS_EMBEDDING_AND_RETRIEVAL": "True", "OPENAI_API_BASE_URL": "http://127.0.0.1:1/v1",
            "OPENAI_API_KEY": "k-secret", "ENABLE_CODE_INTERPRETER": "False",
        }
        self.assertEqual({key: env[key] for key in expected}, expected)
        self.assertEqual(self.paths["secret"].stat().st_mode & 0o777, 0o600)
        parser_flags = {
            option
            for action in LOCAL._parser()._subparsers._group_actions[0].choices["serve"]._actions
            for option in action.option_strings
        }
        self.assertNotIn("--api-key", parser_flags)
        self.assertTrue({"--base-url", "--model"} <= parser_flags)

    def test_w6_serve_starts_the_server_with_the_key_in_its_environment_alone(self) -> None:
        self.paths["server"].parent.mkdir(parents=True)
        self.paths["server"].write_text("")
        started = []

        class Exited:
            pid = 0

            def poll(self) -> int:
                return 1

        def popen(argv: list[str], **kwargs: object) -> Exited:
            started.append((argv, kwargs["env"]))
            return Exited()

        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "k-sentinel"}), \
                mock.patch.object(LOCAL.subprocess, "Popen", popen), self.assertRaises(SystemExit):
            LOCAL.serve(self.paths["venv"].parent, "http://127.0.0.1:1/v1", "m-1", 1, False)
        ((argv, env),) = started
        self.assertNotIn("k-sentinel", " ".join(argv))
        self.assertEqual(env["OPENAI_API_KEY"], "k-sentinel")
        self.assertEqual(argv[1:], ["serve", "--host", "127.0.0.1", "--port", "1"])

    def test_w6_a_server_that_outlives_its_grace_period_is_killed(self) -> None:
        import signal
        import subprocess

        class Stubborn:
            pid = 4242
            waits = 0

            def poll(self) -> None:
                return None

            def wait(self, timeout: float | None = None) -> int:
                self.waits += 1
                if self.waits == 1:
                    raise subprocess.TimeoutExpired("open-webui", timeout or 0)
                return -9

        sent = []
        with mock.patch.object(LOCAL.os, "killpg", lambda pid, sig: sent.append((pid, sig))):
            LOCAL._stop(Stubborn())
        self.assertEqual(sent, [(4242, signal.SIGTERM), (4242, signal.SIGKILL)])

    def test_w5_a_server_that_is_not_listening_yet_reads_as_not_ready(self) -> None:
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        status, _ = LOCAL._Client(f"http://127.0.0.1:{port}").call("GET", "/health")
        self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
