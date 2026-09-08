"""Serve the Cement web UI demo.

Run it from the checkout root:

    uv run python prototype/webui-demo/app.py

The server is standard library only. It holds one live ``demo.Session``, which owns a
temporary SQLite ledger and disappears with the process.
"""

from __future__ import annotations

import argparse
import http.server
import json
from pathlib import Path
import socketserver
import threading
import webbrowser

from cement_runtime import CementError

import demo

STATIC = Path(__file__).resolve().parent / "static"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
}

_state_lock = threading.Lock()
_session: demo.Session | None = None
_seed = 0


def session() -> demo.Session:
    global _session
    with _state_lock:
        if _session is None:
            _session = demo.Session(seed=_seed)
        return _session


def reset() -> demo.Session:
    global _session
    with _state_lock:
        if _session is not None:
            _session.close()
        _session = demo.Session(seed=_seed)
        return _session


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "cement-demo"
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    # -- helpers --

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _text(self, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        self._send(200, text.encode("utf-8"), content_type)

    def _file(self, name: str) -> None:
        path = (STATIC / name).resolve()
        if not path.is_file() or STATIC not in path.parents:
            self._json({"error": "not found"}, status=404)
            return
        self._send(
            200,
            path.read_bytes(),
            CONTENT_TYPES.get(path.suffix, "application/octet-stream"),
        )

    def _body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    # -- routes --

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/index.html"}:
            self._file("index.html")
            return
        if path.startswith("/static/"):
            self._file(path[len("/static/") :])
            return
        if path == "/api/state":
            self._json(session().state())
            return
        if path == "/api/transcript.txt":
            self._text(session().transcript())
            return
        if path == "/api/bundle.json":
            bundle = session().bundle_text
            if bundle is None:
                self._json({"error": "no verified function to export"}, status=409)
                return
            self._send(200, bundle.encode("utf-8"), "application/json; charset=utf-8")
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        actions = {
            "/api/send": lambda body: session().send(str(body["document_id"])),
            "/api/review": lambda body: session().review(
                str(body["proposal_id"]), str(body["decision"])
            ),
            "/api/revoke": lambda body: session().revoke(str(body["example_id"])),
            "/api/compile": lambda body: session().compile(),
            "/api/verify": lambda body: session().verify(),
            "/api/promote": lambda body: session().promote(),
            "/api/route": lambda body: session().route(bool(body["enabled"])),
            "/api/offline": lambda body: session().evaluate_offline(
                str(body["document_id"])
            ),
            "/api/reset": lambda body: reset(),
        }
        action = actions.get(path)
        if action is None:
            self._json({"error": "not found"}, status=404)
            return
        try:
            action(self._body())
        except CementError as error:
            self._json(
                {"error": str(error), "kind": type(error).__name__, "state": session().state()},
                status=409,
            )
            return
        except (KeyError, ValueError, RuntimeError) as error:
            self._json(
                {"error": str(error), "kind": type(error).__name__, "state": session().state()},
                status=400,
            )
            return
        self._json(session().state())


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    global _seed
    parser = argparse.ArgumentParser(description="Serve the Cement web UI demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--open", action="store_true", help="open a browser window")
    arguments = parser.parse_args()
    _seed = arguments.seed

    session()
    url = f"http://{arguments.host}:{arguments.port}/"
    server = Server((arguments.host, arguments.port), Handler)
    print(f"Cement web UI demo: {url}")
    print("The ledger is temporary. Stop the server with Ctrl+C.")
    if arguments.open:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        if _session is not None:
            _session.close()


if __name__ == "__main__":
    main()
