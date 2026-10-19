"""Open WebUI 0.12.3 smoke for examples/open_webui (contract §7). Run with the owui venv python."""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request
import uuid

from cement_runtime import Candidate, CompilePolicy, System

BASE = "http://127.0.0.1:18765"
HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = pathlib.Path(sys.argv[1])
LEDGER = HERE / "ledger.db"
P, OP = "ward-7", "extraction_plan"
HIT = {"document": "PHYSICIAN PROGRESS NOTE\nPatient: Ada\n"}
MISS = {"document": "PATIENT INTAKE FORM\nName: Bo\n"}
MISS2 = {"document": "LAB RESULT SLIP\nTest: CBC\n"}
PLAN = {"fields": ["patient"]}


def call(method: str, path: str, body: object = None, token: str | None = None, raw: bool = False):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=120) as response:
        text = response.read().decode()
    return text if raw else json.loads(text or "null")


def proposals() -> list[dict]:
    with System(LEDGER, create=False).store.transaction() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id, input_json, proposed_output_json, source_id, provenance_json FROM proposals ORDER BY status_sequence")]


def turn(token: str, cases: list[dict], *, chat: str | None = None, user_id: str | None = None,
         title: str = "smoke") -> tuple[str, str, str, dict]:
    if chat is None:
        chat = call("POST", "/api/v1/chats/new", {"chat": {"title": title, "history": {"messages": {}, "currentId": None}}}, token)["id"]
    user_id = user_id or str(uuid.uuid4())
    assistant_id = str(uuid.uuid4())
    prompt = json.dumps({"cases": cases})
    body = {
        "model": "stub", "stream": True, "chat_id": chat, "id": assistant_id,
        "user_message": {"id": user_id, "role": "user", "content": prompt, "parentId": None,
                         "childrenIds": [], "timestamp": int(time.time())},
        "messages": [{"role": "user", "content": prompt}],
        "tool_ids": ["cement_tool"], "params": {"function_calling": "native"},
    }
    stream = call("POST", "/api/chat/completions", body, token, raw=True)
    message = {}
    for _ in range(60):
        saved = call("GET", f"/api/v1/chats/{chat}", token=token)
        message = saved["chat"].get("history", {}).get("messages", {}).get(assistant_id, {})
        if message.get("done"):
            break
        time.sleep(1)
    return chat, user_id, assistant_id, {"stream_tail": stream[-300:], "message": message}


def main() -> None:
    token = call("POST", "/api/v1/auths/signin", {"email": "admin@localhost", "password": "admin"})["token"]
    LEDGER.unlink(missing_ok=True)
    system = System(LEDGER)
    system.register_operation(P, OP, policy=CompilePolicy())
    for _ in range(2):
        proposal = system.submit_proposal(P, OP, HIT, candidate=Candidate(output=PLAN, provenance={}))
        system.review(P, proposal, reviewer="learning-pass", decision="accept")
    system.compile(P, OP)
    assert system.verify_drafts(P, OP, verified_by="learning-pass").passed
    manifest = system.inspect_function_promotion(P, OP)
    system.promote_function(P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass")
    system.set_switch(P, OP, mode="follow", actor="smoke")
    baseline = len(proposals())

    tools = (EXAMPLE / "cement_tools.py").read_text()
    filt = (EXAMPLE / "cement_filter.py").read_text()
    call("POST", "/api/v1/tools/create", {"id": "cement_tool", "name": "Cement learned functions", "content": tools, "meta": {"description": "smoke", "manifest": {}}}, token)
    call("POST", "/api/v1/tools/id/cement_tool/valves/update", {"ledger_path": str(LEDGER), "partition": P, "operations": OP}, token)
    call("POST", "/api/v1/functions/create", {"id": "cement_filter", "name": "Cement answer retention", "content": filt, "meta": {"description": "smoke", "manifest": {}}}, token)
    call("POST", "/api/v1/functions/id/cement_filter/valves/update", {"ledger_path": str(LEDGER), "partition": P, "operations": OP, "deployment_id": "smoke"}, token)
    state = call("GET", "/api/v1/functions/id/cement_filter", token=token)
    if not state.get("is_active"):
        call("POST", "/api/v1/functions/id/cement_filter/toggle", {}, token)
    if not state.get("is_global"):
        call("POST", "/api/v1/functions/id/cement_filter/toggle/global", {}, token)
    report: dict[str, object] = {}

    def items(message: dict) -> list[tuple[str, str]]:
        return [(item.get("type"), item.get("name") or item.get("call_id")) for item in message.get("output") or []]

    chat, user, assistant, result = turn(token, [{"operation": OP, "input": HIT, "reference": PLAN}], title="hit")
    report["hit"] = {"items": items(result["message"]), "content": result["message"].get("content", "")[:200], "new_proposals": len(proposals()) - baseline}

    before = len(proposals())
    chat, user, assistant, result = turn(token, [{"operation": OP, "input": MISS, "reference": PLAN}], title="miss")
    rows = proposals()[before:]
    report["miss_record"] = {"items": items(result["message"]), "new_proposals": len(rows), "source_ids": [r["source_id"] for r in rows],
                             "provenance_keys": sorted(json.loads(rows[0]["provenance_json"])) if rows else []}

    before = len(proposals())
    completed = call("POST", "/api/chat/completed", {"model": "stub", "chat_id": chat, "id": assistant, "session_id": None,
                                                    "messages": [{"id": user, "role": "user", "content": "x"},
                                                                 {"id": assistant, "role": "assistant", "content": result["message"].get("content"), "output": result["message"].get("output")}]}, token)
    report["duplicate_delivery"] = {"new_proposals": len(proposals()) - before, "completed_type": type(completed).__name__}

    before = len(proposals())
    _, _, _, regen = turn(token, [{"operation": OP, "input": MISS, "reference": PLAN}], chat=chat, user_id=user)
    report["regeneration"] = {"items": items(regen["message"]), "new_proposals": len(proposals()) - before}

    before = len(proposals())
    _, _, _, two = turn(token, [{"operation": OP, "input": MISS2, "reference": PLAN}, {"operation": OP, "input": {"document": "LAB RESULT SLIP\nTest: BMP\n"}, "reference": PLAN}], title="two")
    report["two_calls"] = {"items": items(two["message"]), "new_proposals": len(proposals()) - before}

    system.set_switch(P, OP, mode="off", actor="smoke")
    before = len(proposals())
    _, _, _, off = turn(token, [{"operation": OP, "input": HIT, "reference": PLAN}], title="off")
    report["off"] = {"items": items(off["message"]), "new_proposals": len(proposals()) - before,
                     "content": off["message"].get("content", "")[:200]}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
