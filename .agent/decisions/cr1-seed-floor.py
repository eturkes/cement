"""F6: seed membership is a floor even when extension rows mask a deletion.

Optional argument = p46-differential.py --json output; permit only missing-seed deltas.
"""
import contextlib
import io
import json
import pathlib
import runpy
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT
sys.path.insert(0, str(ROOT / ".agent/decisions"))
ns = runpy.run_path(str(ROOT / ".agent/decisions/m3u4-s3-validate.py"))


def grade(path):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = ns["grade"](path)
    return rc, output.getvalue()


failed = False
with tempfile.TemporaryDirectory(prefix="F6-", dir=SCRATCH) as directory:
    for kind in ("probes", "review", "mutants"):
        original = ROOT / f".agent/decisions/m3u4-{kind}.json"
        rc, output = grade(original)
        assert rc == 0, (kind, rc, output)
        document = json.loads(original.read_text())
        print(f"CONTROL: {kind}: {len(document['rows'])} rows; rc=0")
        victim = document["rows"].pop(0)["id"]
        path = pathlib.Path(directory) / f"{kind}.json"
        path.write_text(json.dumps(document))
        rc, output = grade(path)
        print(f"OBSERVED: {kind}: deleted seeded {victim}; rc={rc}; "
              + next(line for line in output.splitlines() if line.startswith("ROWS:")))
        failed |= rc != 1 or f"missing seeded id {victim}" not in output
if failed:
    print("RED: all three wave table kinds accept deletion of a required seeded row")
    raise SystemExit(1)
print("GREEN")

if len(sys.argv) > 1:
    assert len(sys.argv) == 2, "usage: cr1-seed-floor.py [p46-differential.json]"
    rows = json.loads(pathlib.Path(sys.argv[1]).read_text())["cases"]
    differences = [row for row in rows if not row["match"]]
    assert differences, "differential must exercise the repaired seed floor"
    for row in differences:
        assert row["validator"] == "m3u4-s3", row
        kind = row["label"].split()[0]
        subjects = ns[{"probes": "PROBE_SUBJECTS", "review": "REVIEW_SUBJECTS",
                       "mutants": "MUTANT_SUBJECTS"}[kind]]
        diagnostics = [f"INVALID: missing seeded id {identifier}\n"
                       for identifier, _, _ in subjects
                       if f"INVALID: missing seeded id {identifier}\n" in row["new_stdout"]]
        assert diagnostics, row
        normalized = row["new_stdout"]
        for diagnostic in diagnostics:
            normalized = normalized.replace(diagnostic, "")
        assert row["new"] == 1 and row["old"] in (0, 1), row
        if row["old"] == 0:
            normalized = normalized.replace("RESULT: FAIL", "RESULT: PASS")
        assert normalized == row["old_stdout"] and row["old_stderr"] == row["new_stderr"], row
    artifacts = [row for row in rows if row["label"].endswith(".json")]
    assert artifacts and all(row["match"] for row in artifacts)
    print(f"DIFFERENTIAL: {len(artifacts)} shipped artifacts unchanged; "
          f"{len(rows) - len(differences)}/{len(rows)} identical; "
          f"{len(differences)} missing-seed diagnostic/verdict changes alone")
