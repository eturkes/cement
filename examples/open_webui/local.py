"""Run a local Open WebUI 0.12.3 with the Cement paste-ins, to test Cement with a real model.

    uv run python examples/open_webui/local.py setup
    OPENAI_API_KEY=... uv run python examples/open_webui/local.py serve \\
        --base-url http://127.0.0.1:8000/v1 --model MODEL

The instance mirrors a network-less deployment on Cement's target Python 3.12, with no Cement
package installed beside Open WebUI, and every Cement part pasted in through the REST API.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
PASTE_IN = HERE / "paste-in"
SKILL = HERE / "cement-learn" / "SKILL.md"
DOCUMENTS = HERE.parent / "hospital_ocr" / "documents"
OPEN_WEBUI = "open-webui==0.12.3"
# Every package `OPEN_WEBUI` pulls in, pinned with its hashes; the file header names the command
# that regenerates it after a bump.
LOCK = HERE / "local-requirements.txt"
# Cement's target line, the nucllei jail's (owner-ruled); Open WebUI 0.12.3 admits 3.11-3.12.
PYTHON = "3.12"
PARTITION = "local"
OPERATIONS = (
    "extraction_plan: The user pastes one form, such as a progress note, an intake form or a lab"
    " slip, and asks which fields to extract from it or where they are. input ="
    ' {"document": "<the whole form text, exactly as the user pasted it>"}. output = the'
    " extraction plan, which says where each field is and never holds the patient's values:"
    ' {"fields": [{"name": "<snake_case name>", "label": "<the text before the colon>"} or'
    ' {"name": "<snake_case name>", "section": "<the section heading>"}]}.'
)
CHAT_MODEL = "cement-chat"
LEARNING_MODEL = "cement-learning"
ADMIN = "admin@localhost"
# Open WebUI 0.12.3 without a login gives its admin this password (`routers/auths.py` signin).
NO_LOGIN_PASSWORD = "admin"  # noqa: S105 — Open WebUI's public default, read only to replace it


def _write(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _paths(directory: pathlib.Path) -> dict[str, pathlib.Path]:
    return {
        "venv": directory / "venv",
        "python": directory / "venv" / "bin" / "python",
        "server": directory / "venv" / "bin" / "open-webui",
        "data": directory / "data",
        "ledger": directory / "data" / "cement" / "ledger.db",
        "secret": directory / "secret",
        "password": directory / "admin-password",
        "log": directory / "open-webui.log",
    }


def _kept_token(path: pathlib.Path) -> str:
    """A random token written once with mode 0600, then read back on every later run."""

    if not path.is_file():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(secrets.token_hex(32))
    return path.read_text(encoding="utf-8")


def plan(model: str, ledger: pathlib.Path) -> list[tuple[str, str, dict[str, Any]]]:
    """Every Open WebUI object that the instance needs, as (kind, id, form) in creation order."""

    valves = {"ledger_path": str(ledger), "partition": PARTITION, "operations": OPERATIONS}

    def code(name: str) -> str:
        return (PASTE_IN / f"{name}.py").read_text(encoding="utf-8")

    def model_form(identifier: str, name: str, description: str, meta: dict[str, Any]) -> dict:
        return {
            "id": identifier,
            "base_model_id": model,
            "name": f"{name} ({model})",
            "meta": {"description": description, **meta},
            "params": {"function_calling": "native"},
        }

    return [
        (
            "tool",
            "cement",
            {"name": "Cement learned functions", "content": code("cement_tools"), "valves": valves},
        ),
        (
            "tool",
            "cement_learning",
            {"name": "Cement learning pass", "content": code("cement_learning"), "valves": valves},
        ),
        (
            "function",
            "cement_filter",
            {
                "name": "Cement answer retention",
                "content": code("cement_filter"),
                "valves": valves | {"deployment_id": "local"},
            },
        ),
        (
            "function",
            "cement_switch",
            {"name": "Cement switch", "content": code("cement_admin"), "valves": valves},
        ),
        (
            "skill",
            "cement-learn",
            {"name": "Cement learning pass", "content": SKILL.read_text(encoding="utf-8")},
        ),
        (
            "model",
            CHAT_MODEL,
            model_form(
                CHAT_MODEL,
                "Cement chat",
                "The users' chat model: it answers from switched-on Cement functions.",
                {"toolIds": ["cement"], "filterIds": ["cement_filter"]},
            ),
        ),
        (
            "model",
            LEARNING_MODEL,
            model_form(
                LEARNING_MODEL,
                "Cement learning",
                "The administrator's model: it runs the learning pass and has the switch button.",
                {
                    "toolIds": ["cement_learning"],
                    "skillIds": ["cement-learn"],
                    "actionIds": ["cement_switch"],
                    # With built-in skill tools on, Open WebUI 0.12.3 only lists the skill, and
                    # a model can skip loading it; off, it puts the whole skill text in the chat.
                    "builtinTools": {"skills": False},
                },
            ),
        ),
    ]


class _Client:
    def __init__(self, base: str) -> None:
        self.base = base
        self.token: str | None = None

    def call(self, method: str, path: str, body: object = None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        # `base` is the loopback http:// instance this launcher started, never a caller's URL.
        request = urllib.request.Request(self.base + path, data=data, method=method)  # noqa: S310
        request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            # The same loopback request the launcher built above.
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                text = response.read().decode()
                return response.status, json.loads(text or "null")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode(errors="replace")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            # A server still starting refuses connections: status 0 reads as "not ready".
            return 0, str(exc)

    def ok(self, method: str, path: str, body: object = None) -> Any:
        status, payload = self.call(method, path, body)
        if status != 200:
            raise SystemExit(f"local: {method} {path} answered {status}: {str(payload)[:300]}")
        return payload


def _sign_in(client: _Client, password: str) -> str:
    """The admin's token: the kept password, else the first signup, else a no-login instance's
    admin, whose password becomes the kept one."""

    credentials = {"email": ADMIN, "password": password}

    def token(path: str, body: dict[str, str]) -> str | None:
        status, payload = client.call("POST", path, body)
        return str(payload["token"]) if status == 200 else None

    found = token("/api/v1/auths/signin", credentials) or token(
        "/api/v1/auths/signup", credentials | {"name": "Admin"}
    )
    if found is None:
        client.token = token("/api/v1/auths/signin", credentials | {"password": NO_LOGIN_PASSWORD})
        if client.token is not None:
            client.ok(
                "POST",
                "/api/v1/auths/update/password",
                {"password": NO_LOGIN_PASSWORD, "new_password": password},
            )
            found = token("/api/v1/auths/signin", credentials)
    if found is None:
        raise SystemExit(
            f"local: {ADMIN} does not sign in with the kept password;"
            " start a new instance with `serve --fresh`"
        )
    return found


def provision(client: _Client, model: str, paths: dict[str, pathlib.Path]) -> None:
    """Create or update every object of `plan`, so a restart picks up regenerated paste-ins."""

    client.token = _sign_in(client, _kept_token(paths["password"]))
    for kind, identifier, form in plan(model, paths["ledger"]):
        if kind in ("tool", "function"):
            root = f"/api/v1/{kind}s"
            body = {
                "id": identifier,
                "name": form["name"],
                "content": form["content"],
                "meta": {"description": form["name"], "manifest": {}},
            }
            exists = client.call("GET", f"{root}/id/{identifier}")[0] == 200
            client.ok(
                "POST", f"{root}/id/{identifier}/update" if exists else f"{root}/create", body
            )
            client.ok("POST", f"{root}/id/{identifier}/valves/update", form["valves"])
            if kind == "function" and not client.ok("GET", f"{root}/id/{identifier}")["is_active"]:
                client.ok("POST", f"{root}/id/{identifier}/toggle")
        elif kind == "skill":
            body = {"id": identifier, "name": form["name"], "content": form["content"], "meta": {}}
            exists = client.call("GET", f"/api/v1/skills/id/{identifier}")[0] == 200
            path = f"/api/v1/skills/id/{identifier}/update" if exists else "/api/v1/skills/create"
            client.ok("POST", path, body)
        else:
            exists = client.call("GET", f"/api/v1/models/model?id={identifier}")[0] == 200
            path = "/api/v1/models/model/update" if exists else "/api/v1/models/create"
            client.ok("POST", path, form)


def _environment(
    paths: dict[str, pathlib.Path], base_url: str, key: str, port: int
) -> dict[str, str]:
    return os.environ | {
        "DATA_DIR": str(paths["data"]),
        "WEBUI_SECRET_KEY": _kept_token(paths["secret"]),
        # Without a login, every caller gets an admin token, and an admin token runs code
        # (`tools/create` executes the pasted source). The launcher's admin is the one account.
        "WEBUI_AUTH": "True",
        "ENABLE_SIGNUP": "False",
        # Open WebUI's default `*` lets any web page read its responses, the token included.
        "CORS_ALLOW_ORIGIN": f"http://127.0.0.1:{port};http://localhost:{port}",
        # The launcher's flags win over settings saved by an earlier run.
        "ENABLE_PERSISTENT_CONFIG": "False",
        "OPENAI_API_BASE_URL": base_url,
        "OPENAI_API_KEY": key,
        "ENABLE_OLLAMA_API": "False",
        # Like a network-less image: no model downloads, no package installs.
        "OFFLINE_MODE": "True",
        "BYPASS_EMBEDDING_AND_RETRIEVAL": "True",
        "ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS": "False",
        "ENABLE_CODE_EXECUTION": "False",
        "ENABLE_CODE_INTERPRETER": "False",
    }


def _banner(url: str, model: str, paths: dict[str, pathlib.Path]) -> str:
    documents = sorted(path.name for path in DOCUMENTS.glob("*.txt"))
    ledger = paths["ledger"]
    return "\n".join(
        [
            f"Open WebUI with Cement: {url}",
            f"  Sign in as {ADMIN} with the password in {paths['password']}.",
            f"  Users chat with 'Cement chat ({model})'.",
            f"  The administrator uses 'Cement learning ({model})'.",
            "",
            "1. Set up the operation. Open a chat with Cement learning and send 'Hello'.",
            "   Under the reply, click the Cement switch button. Choose 'Set up extraction_plan'.",
            "2. Ask. In a new chat with Cement chat, paste one form from",
            f"   {DOCUMENTS} and ask: 'Which fields should I extract from this form?'",
            "   Do this for two forms of one layout, each in a new chat:",
            "   " + ", ".join(documents),
            "3. Learn. In a chat with Cement learning, send:",
            "   'Run a Cement learning pass for extraction_plan.'",
            "4. Switch on. Click the Cement switch button under that reply. Choose",
            "   'Switch extraction_plan on: follow the newest version'.",
            "5. Use. Paste a third form of the same layout into a new chat with Cement chat.",
            "   Open the use_learned_function tool call. Its result says 'covered': true.",
            "",
            f"Ledger: {ledger}",
            f"  uv run cement --db {ledger} --partition {PARTITION} \\",
            "    function versions extraction_plan",
            "Press Ctrl-C to stop.",
        ]
    )


def _venv_line(venv: pathlib.Path) -> str | None:
    """The `major.minor` line an existing venv runs (`pyvenv.cfg` `version_info`), else None."""
    try:
        config = (venv / "pyvenv.cfg").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in config.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "version_info":
            return ".".join(value.strip().split(".")[:2])
    return None


def setup(directory: pathlib.Path) -> int:
    paths = _paths(directory)
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("local: uv is not on PATH")
    directory.mkdir(parents=True, exist_ok=True)
    if _venv_line(paths["venv"]) != PYTHON or not paths["python"].is_file():
        # Fixed arguments: uv (re)creates the instance venv on the pinned interpreter; a venv on
        # another line would take a lock resolved for this one.
        venv = str(paths["venv"])
        subprocess.run([uv, "venv", "--clear", "--python", PYTHON, venv], check=True)  # noqa: S603
    python = str(paths["python"])
    subprocess.run(  # noqa: S603 — fixed arguments: uv installs the hash-pinned lock alone
        [uv, "pip", "install", "--python", python, "--require-hashes", "-r", str(LOCK)], check=True
    )
    _write(f"Open WebUI is installed in {paths['venv']}. Cement is not: the paste-ins carry it.")
    return 0


def _stop(server: Any) -> None:
    """Stop the server's whole session; a server that outlives 30 s of SIGTERM gets SIGKILL."""

    if server.poll() is not None:
        return
    os.killpg(server.pid, signal.SIGTERM)
    try:
        server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(server.pid, signal.SIGKILL)
        server.wait()


def serve(directory: pathlib.Path, base_url: str, model: str, port: int, fresh: bool) -> int:
    paths = _paths(directory)
    if not paths["server"].is_file():
        raise SystemExit("local: run `local.py setup` first")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit(
            "local: set OPENAI_API_KEY to the access key that the endpoint accepts"
            " (for a subscription proxy, the proxy's own access key)"
        )
    if fresh and paths["data"].exists():
        shutil.rmtree(paths["data"])
    paths["data"].mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{port}"

    def stop(_signal: int, _frame: object) -> None:
        raise KeyboardInterrupt

    # The server runs in its own session, so a terminated launcher must stop it too.
    signal.signal(signal.SIGTERM, stop)
    with paths["log"].open("ab") as log:
        server = subprocess.Popen(  # noqa: S603 — the venv's own entry point, fixed arguments
            [str(paths["server"]), "serve", "--host", "127.0.0.1", "--port", str(port)],
            env=_environment(paths, base_url, key, port),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    try:
        client = _Client(url)
        deadline = time.monotonic() + 300
        while client.call("GET", "/health")[0] != 200:
            if server.poll() is not None or time.monotonic() > deadline:
                raise SystemExit(f"local: Open WebUI did not start; read {paths['log']}")
            time.sleep(1)
        provision(client, model, paths)
        _write(_banner(url, model, paths))
        server.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _stop(server)
    return 0


def reprovision(directory: pathlib.Path, model: str, port: int) -> int:
    provision(_Client(f"http://127.0.0.1:{port}"), model, _paths(directory))
    _write("Pasted every Cement part into the running instance again.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local Open WebUI with the Cement paste-ins."
    )
    parser.add_argument(
        "--dir", type=pathlib.Path, default=HERE.parents[1] / ".open-webui", help="state directory"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="install Open WebUI 0.12.3 in a Python 3.12 environment")
    run = commands.add_parser("serve", help="start Open WebUI and paste in every Cement part")
    run.add_argument("--base-url", required=True, help="OpenAI-compatible endpoint of the model")
    run.add_argument("--model", required=True, help="model id at that endpoint")
    run.add_argument("--port", type=int, default=8090)
    run.add_argument(
        "--fresh", action="store_true", help="delete the saved instance and ledger first"
    )
    again = commands.add_parser(
        "provision", help="paste every Cement part into the running instance again"
    )
    again.add_argument("--model", required=True, help="model id that serve was started with")
    again.add_argument("--port", type=int, default=8090)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    directory = args.dir.resolve()
    if args.command == "setup":
        return setup(directory)
    if args.command == "provision":
        return reprovision(directory, args.model, args.port)
    return serve(directory, args.base_url, args.model, args.port, args.fresh)


if __name__ == "__main__":
    raise SystemExit(main())
