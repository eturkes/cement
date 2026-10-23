"""Open WebUI local instance — the launcher's wiring (MAINTAIN W5).

`examples/open_webui/local.py` pastes the four generated files, the skill and two workspace
models into a local Open WebUI 0.12.3. The live run is the spot-check; these frames pin what a
wrong wiring would hide: chat users must never reach the learning tool or the switch, every
pasted file is the generated (self-contained) one, and the model key never enters argv.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
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


class FakeInstance(LOCAL._Client):
    """Open WebUI 0.12.3 password auth as the launcher meets it (`routers/auths.py`): signin checks
    the stored password, signup admits the first user alone, update/password needs the old one."""

    def __init__(self, users: dict[str, str]) -> None:
        super().__init__("http://127.0.0.1:1")
        self.users = dict(users)
        self.passwords: list[str] = []
        self.provisioned: list[str] = []

    def call(self, method: str, path: str, body: object = None) -> tuple[int, object]:
        form = body if isinstance(body, dict) else {}
        if path == "/api/v1/auths/signin":
            self.passwords.append(form["password"])
            if self.users.get(form["email"]) == form["password"]:
                return 200, {"token": form["email"]}
            return 400, "The email or password provided is incorrect."
        if path == "/api/v1/auths/signup":
            if self.users:
                return 403, "access prohibited"
            self.users[form["email"]] = form["password"]
            return 200, {"token": form["email"]}
        if path == "/api/v1/auths/update/password":
            if self.token is None or self.users.get(self.token) != form["password"]:
                return 400, "The email or password provided is incorrect."
            self.users[self.token] = form["new_password"]
            return 200, True
        if self.token not in self.users:
            return 401, "not authenticated"
        if method == "POST":
            self.provisioned.append(path)
        return 200, {"is_active": True}


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
            env = LOCAL._environment(self.paths, "http://127.0.0.1:1/v1", "k-secret", 1)
        expected = {
            "DATA_DIR": str(self.paths["data"]), "WEBUI_AUTH": "True", "OFFLINE_MODE": "True",
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

    def _served(self, port: int) -> tuple[list[str], dict[str, str]]:
        """The argv + environment `serve` starts the server with (a server that exits at once)."""

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
            LOCAL.serve(self.paths["venv"].parent, "http://127.0.0.1:1/v1", "m-1", port, False)
        ((argv, env),) = started
        return argv, env

    def test_w6_serve_starts_the_server_with_the_key_in_its_environment_alone(self) -> None:
        argv, env = self._served(1)
        self.assertNotIn("k-sentinel", " ".join(argv))
        self.assertEqual(env["OPENAI_API_KEY"], "k-sentinel")
        self.assertEqual(argv[1:], ["serve", "--host", "127.0.0.1", "--port", "1"])

    def test_s1_serve_admits_its_own_pages_and_signed_in_users_alone(self) -> None:
        # Open WebUI 0.12.3 without a login hands every caller an admin token, an admin token runs
        # code (`tools/create` executes the pasted source), and its default CORS `*` lets any web
        # page read the token: a login + the instance's own origins close both routes.
        _, env = self._served(8123)
        self.assertEqual(
            {key: env.get(key) for key in ("WEBUI_AUTH", "ENABLE_SIGNUP", "CORS_ALLOW_ORIGIN")},
            {"WEBUI_AUTH": "True", "ENABLE_SIGNUP": "False",
             "CORS_ALLOW_ORIGIN": "http://127.0.0.1:8123;http://localhost:8123"},
        )

    def _provisioned(self, users: dict[str, str]) -> tuple["FakeInstance", str | None]:
        instance = FakeInstance(users)
        try:
            LOCAL.provision(instance, "m-1", self.paths)
        except SystemExit as exc:
            return instance, str(exc)
        return instance, None

    def _kept(self) -> str:
        path = self.paths["password"]
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return path.read_text(encoding="utf-8")

    def test_s1_a_new_instance_gets_one_admin_with_a_random_kept_password(self) -> None:
        self.paths["data"].mkdir(parents=True)
        instance, stopped = self._provisioned({})
        self.assertIsNone(stopped)
        kept = self._kept()
        self.assertGreaterEqual(len(kept), 32)
        self.assertEqual(instance.users, {"admin@localhost": kept})
        self.assertNotIn("admin", instance.passwords)

    def test_s1_a_no_login_instance_has_its_admin_password_replaced(self) -> None:
        self.paths["data"].mkdir(parents=True)
        instance, stopped = self._provisioned({"admin@localhost": "admin"})
        self.assertIsNone(stopped)
        self.assertEqual(instance.users, {"admin@localhost": self._kept()})

    def test_s1_a_later_run_signs_in_with_the_kept_password_alone(self) -> None:
        self.paths["data"].mkdir(parents=True)
        self.paths["password"].touch(mode=0o600)
        self.paths["password"].write_text("p-kept", encoding="utf-8")
        instance, stopped = self._provisioned({"admin@localhost": "p-kept"})
        self.assertIsNone(stopped)
        self.assertEqual(instance.passwords, ["p-kept"])

    def test_s1_an_admin_the_launcher_cannot_sign_in_stops_it(self) -> None:
        self.paths["data"].mkdir(parents=True)
        for users in ({"admin@localhost": "someone-else"}, {"first@example.org": "pw"}):
            instance, stopped = self._provisioned(users)
            self.assertIsNotNone(stopped)
            self.assertIn("--fresh", str(stopped))
            self.assertEqual(instance.users, users)
            self.assertEqual(instance.provisioned, [])

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

    def test_p128_setup_installs_the_hash_pinned_lock_alone(self) -> None:
        directory = self.paths["venv"].parent / "fresh"
        calls: list[list[str]] = []
        with mock.patch.object(LOCAL.shutil, "which", return_value="/bin/uv"), \
                mock.patch.object(LOCAL.subprocess, "run", lambda argv, **kwargs: calls.append(argv)):
            self.assertEqual(LOCAL.setup(directory), 0)
        python = str(directory / "venv" / "bin" / "python")
        lock = str(EXAMPLE / "local-requirements.txt")
        self.assertEqual(calls, [
            ["/bin/uv", "venv", "--python", "3.11", str(directory / "venv")],
            ["/bin/uv", "pip", "install", "--python", python, "--require-hashes", "-r", lock],
        ])

    def test_p128_the_lock_pins_the_target_and_hashes_every_package(self) -> None:
        text = (EXAMPLE / "local-requirements.txt").read_text(encoding="utf-8")
        _, _, body = text.partition("\n#    ")
        command = body.splitlines()[0]
        self.assertIn(f"echo {LOCAL.OPEN_WEBUI} | uv pip compile", command)
        self.assertIn(f"--python-version {LOCAL.PYTHON} --universal --generate-hashes", command)
        entries = re.split(r"(?m)^(?=[A-Za-z0-9])", body.partition("\n")[2])[1:]
        self.assertGreater(len(entries), 1)
        for entry in entries:
            with self.subTest(entry=entry.split(" ", 1)[0]):
                self.assertRegex(entry, r"^[A-Za-z0-9._-]+==[^ ;\\]+ ")
                self.assertRegex(entry, r"--hash=sha256:[0-9a-f]{64}")
        self.assertIn(f"\n{LOCAL.OPEN_WEBUI} \\\n", text)

    def test_w5_a_server_that_is_not_listening_yet_reads_as_not_ready(self) -> None:
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        status, _ = LOCAL._Client(f"http://127.0.0.1:{port}").call("GET", "/health")
        self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
