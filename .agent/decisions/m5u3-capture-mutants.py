"""M5.3 closure probe: the nine capture-binding obligations reviewer-25 found unpinned now red the battery.

Usage: `uv run python .agent/decisions/m5u3-capture-mutants.py <checkout>` — copies the checkout per
mutant, edits `examples/open_webui/cement_filter.py` (anchor count 1 asserted), runs
`tests.test_open_webui_example` with the checkout's `.venv`; prints KILLED/SURVIVED, `survivors: none`
when every mutant reds it.
"""
import pathlib, shutil, subprocess, sys, tempfile
X = pathlib.Path(sys.argv[1])
F = "examples/open_webui/cement_filter.py"
MUTANTS = [
    ("retention re-raises", 'log.exception("cement: retention failed")', "raise"),
    ("emitter re-raises", 'log.exception("cement: notification failed")', "raise"),
    ("source deployment", "                    self.valves.deployment_id,\n", '                    "wrong",\n'),
    ("source chat", "                    chat_id,\n                    user_message_id,\n", '                    "wrong",\n                    user_message_id,\n'),
    ("source user message", "                    user_message_id,\n                    pair[\"input_hash\"],\n", '                    "wrong",\n                    pair["input_hash"],\n'),
    ("source input hash", '                    pair["input_hash"],\n                )', '                    "wrong",\n                )'),
    ("provenance chat", '"chat_id": chat_id,', '"chat_id": None,'),
    ("provenance message", '"assistant_message_id": message_id,', '"assistant_message_id": None,'),
    ("provenance model", '"model": body.get("model"),', '"model": None,'),
]
survivors = []
for label, old, new in MUTANTS:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "t"
        shutil.copytree(X, root, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__"))
        path = root / F
        text = path.read_text()
        assert text.count(old) == 1, (label, text.count(old))
        path.write_text(text.replace(old, new))
        r = subprocess.run([str(X / ".venv/bin/python"), "-B", "-m", "unittest", "tests.test_open_webui_example"],
                           cwd=root, capture_output=True, text=True, env={"PYTHONPATH": str(root / "src"), "PATH": "/usr/bin"})
        killed = r.returncode != 0
        print(f"{label:22} {'KILLED' if killed else 'SURVIVED'}")
        if not killed: survivors.append(label)
print("survivors:", survivors or "none")
sys.exit(1 if survivors else 0)
