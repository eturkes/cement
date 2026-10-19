"""Deterministic OpenAI-compatible chat model for the Open WebUI smoke (stdlib only).

User message = a JSON object {"cases": [{"operation", "input", "reference"}, ...]}. The model calls
`use_learned_function` for every case, then `record_answer` (with the case's reference output)
for every case the tool reported as not covered, then replies with one line per case.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = open(sys.argv[2], "a", encoding="utf-8") if len(sys.argv) > 2 else None


def _tool_name(tools: list[dict], suffix: str) -> str:
    for tool in tools:
        name = tool.get("function", {}).get("name", "")
        if name.endswith(suffix):
            return name
    return suffix


def _plan(body: dict) -> dict:
    messages = body.get("messages", [])
    tools = body.get("tools") or []
    user = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    content = user.get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    try:
        cases = json.loads(content)["cases"]
    except (TypeError, ValueError, KeyError):
        return {"content": "I can only answer smoke requests."}
    use, record = _tool_name(tools, "use_learned_function"), _tool_name(tools, "record_answer")
    calls = {}
    for message in messages:
        for call in message.get("tool_calls") or []:
            calls[call["id"]] = call
    results = {
        m.get("tool_call_id"): m.get("content") for m in messages if m.get("role") == "tool"
    }
    asked = [c for c in calls.values() if c["function"]["name"] == use]
    if not asked:
        return {"tool_calls": [(use, {"operation": c["operation"], "input": c["input"]}) for c in cases]}
    recorded = [c for c in calls.values() if c["function"]["name"] == record]
    if not recorded:
        pending = []
        for case, call in zip(cases, asked):
            try:
                result = json.loads(results.get(call["id"]) or "{}")
            except ValueError:
                result = {}
            if result.get("covered") is False:
                pending.append((record, {"operation": case["operation"], "input": case["input"], "output": case["reference"]}))
        if pending:
            return {"tool_calls": pending}
    lines = []
    for case, call in zip(cases, asked):
        lines.append(f"{case['operation']}: {results.get(call['id'])}")
    return {"content": "\n".join(lines)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def _send(self, code: int, payload: object) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, {"object": "list", "data": [{"id": "stub", "object": "model", "owned_by": "smoke"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        plan = _plan(body)
        if LOG:
            LOG.write(json.dumps({"request": body, "plan": plan}, default=str) + "\n")
            LOG.flush()
        created, rid = int(time.time()), f"chatcmpl-{uuid.uuid4().hex[:12]}"
        tool_calls = [
            {"index": i, "id": f"call_{uuid.uuid4().hex[:10]}", "type": "function",
             "function": {"name": name, "arguments": json.dumps(args)}}
            for i, (name, args) in enumerate(plan.get("tool_calls", []))
        ]
        if not body.get("stream"):
            message = {"role": "assistant", "content": plan.get("content")}
            if tool_calls:
                message["tool_calls"] = [{k: v for k, v in c.items() if k != "index"} for c in tool_calls]
            self._send(200, {"id": rid, "object": "chat.completion", "created": created, "model": "stub",
                             "choices": [{"index": 0, "message": message,
                                          "finish_reason": "tool_calls" if tool_calls else "stop"}]})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        def chunk(delta: dict, finish: str | None = None) -> None:
            event = {"id": rid, "object": "chat.completion.chunk", "created": created, "model": "stub",
                     "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.flush()

        chunk({"role": "assistant"})
        if tool_calls:
            chunk({"tool_calls": tool_calls})
            chunk({}, "tool_calls")
        else:
            chunk({"content": plan.get("content") or ""})
            chunk({}, "stop")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
