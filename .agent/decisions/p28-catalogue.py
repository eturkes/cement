"""p28-catalogue.py <base> <out.jsonl> — p28's nine deletion mutants (`.agent/replay-mutants` format), line numbers derived at <base>."""
import json, subprocess, sys
base, out = sys.argv[1], sys.argv[2]
def text(path): return subprocess.run(["git", "show", f"{base}:{path}"], check=True, capture_output=True, text=True).stdout
F, S = "src/cement_runtime/function.py", "src/cement_runtime/system.py"
def guard(cond, message):
    return f"                if {cond}:\n                    raise IntegrityError({message})\n"
rows = [
    ("evidence-snapshot-digest-syntax", F, '        evidence_snapshot_hash = _digest(\n            entry["evidence_snapshot_hash"],\n            f"function entry {index} evidence_snapshot_hash",\n        )\n', '        evidence_snapshot_hash = entry["evidence_snapshot_hash"]\n'),
    ("output-digest-syntax", F, '        output_hash = _digest(entry["output_hash"], f"function entry {index} output_hash")\n', '        output_hash = entry["output_hash"]\n'),
    ("entry-seal-digest-syntax", F, '        entry_seal = _digest(entry["entry_seal"], f"function entry {index} entry_seal")\n', '        entry_seal = entry["entry_seal"]\n'),
    ("report-test-set-digest-syntax", F, '        report_test_set_hash = _digest(\n            report["test_set_hash"],\n            f"function entry {index} report test_set_hash",\n        )\n', '        report_test_set_hash = report["test_set_hash"]\n'),
    ("p5-abi", S, guard('document.value.get("abi") != FUNCTION_ABI', '"function ABI changed during projection"'), ""),
    ("p5-canonicalizer", S, guard('document.value.get("canonicalizer") != CANONICALIZER', '"function canonicalizer changed during projection"'), ""),
    ("p5-embedded-hash", S, guard('document.value.get("function_hash") != document.function_hash', '"function hash changed during projection"'), ""),
    ("p5-scope", S, guard('document.value.get("scope") != expected_scope', '"function scope does not equal the promoted snapshot"'), ""),
    ("p5-entries-array", S, guard("type(actual_entries) is not list", '"function entries are not an array"'), ""),
]
header = {
    "catalogue": "p28",
    "base": base,
    "unittest": [
        "tests.test_function.FunctionTests.test_entry_digest_syntax_rejects_after_outer_rehash",
        "tests.test_system.SystemTests.test_function_verification_pins_each_projected_document_field",
    ],
    "ran": 2,
    "expect": {"killed": 9, "superseded": [], "equivalent": {}},
    "source": "MAINTAIN p28: the nine integrity checks the M2 register found deletable green (.agent/archive/polish.md p28), each deleted alone; at b937a3b the pre-pin suite (every module but D28) already killed all nine, so this catalogue grades the two p28 pins alone",
}
lines = [json.dumps(header)]
for rid, path, old, new in rows:
    body = text(path)
    assert body.count(old) == 1, (rid, body.count(old))
    line = body[: body.index(old)].count("\n") + 1
    lines.append(json.dumps({"id": rid, "file": path, "line": line, "old": old, "new": new, "intent": rid}))
open(out, "w").write("\n".join(lines) + "\n")
print(f"{len(rows)} mutants at {base}")
