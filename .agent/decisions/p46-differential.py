#!/usr/bin/env python3
"""Replay p46 against a pre-extraction revision; rc 0 = every comparison agrees.

Usage:
    uv run python .agent/decisions/p46-differential.py [--base REV] [--json PATH]
    uv run python .agent/decisions/p46-differential.py --self-test

Old validators = `git show REV:<file>`; new validators = working-tree scripts.
Artifact domain = recognized tables in the baseline OR tracked tree; both runs
read the SAME current artifact bytes. Preserve baseline failures rather than demanding green historical tables.
Compare rc, full stdout/stderr and the reported unfilled count. Seed and malformed
cases run in-process and also compare exception class/message (not traceback
locations). Malformed variants cover every header + first-row cell, row-set
changes, cancellation and differential columns; this is a bounded corpus, not an
all-input proof. Temporary seeds/old scripts are removed at exit. --json retains
per-case results and full outputs for any mismatch or pre-existing red artifact.
"""

from pathlib import Path
import ast, contextlib, copy, io, json, os, re, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / ".agent/decisions"
BASE = "02440b851e1c2e42679491a2c8c7e6c1bf46019d"
KINDS = {
    "m3u2b-wave2": {"attack", "divergences", "oracle", "review"},
    "m3u3-wave1": {"map", "spike"},
    "m3u3-wave2": {"attack", "probes", "verdicts"},
    "m3u3-wave3": {"divergences", "review"},
    "m3u3-s4": {"attack", "window"},
    "m3u4-wave1": {"map", "spike"},
    "m3u4-wave2": {"attack", "verdicts"},
    "m3u4-s3": {"mutants", "probes", "review"},
    "m3u5a-wave1": {"map", "spike"},
    "m3u5a-wave2": {"attack", "verdicts"},
    "m3u5b-wave2": {"attack", "verdicts"},
    "m3u6a1-attack": {None},
    "m3u6a2-wave2": {"attack", "verdicts"},
}
NAMES = {}


def artifacts():
    paths = subprocess.check_output(
        ["git", "ls-files", "--", ".agent/decisions/*.json"], cwd=ROOT, text=True
    ).splitlines()
    baseline_paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE, "--", ".agent/decisions"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    documents = [
        (
            Path(path),
            json.loads(subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)),
        )
        for path in baseline_paths
        if path.endswith(".json")
    ]
    documents.extend((Path(path), json.loads((ROOT / path).read_text())) for path in paths)
    found = {}
    for name, kinds in KINDS.items():
        unit = name.split("-")[0]
        suffixes = set()
        for path, document in documents:
            if not path.name.startswith(unit + "-") or not isinstance(document, dict):
                continue
            suffix = path.stem[len(unit) + 1 :]
            if name == "m3u3-s4" and suffix not in ("s4-attack", "window"):
                continue
            if name == "m3u3-wave2" and suffix == "s4-attack":
                continue
            if name == "m3u6a1-attack" and suffix != "attack":
                continue
            if document.get("kind") in kinds:
                suffixes.add(suffix)
        if not suffixes:
            raise ValueError(f"no tracked artifacts for {name}")
        found[name] = sorted(suffixes)
    return found


def old_source(path):
    source = subprocess.check_output(["git", "show", f"{BASE}:{path.relative_to(ROOT)}"], cwd=ROOT)
    if any(
        isinstance(node, ast.ImportFrom) and node.module == "wave_validate"
        for node in ast.parse(source).body
    ):
        raise ValueError("--base must precede the wave_validate extraction")
    return source


def record(name, label, args, old, new, ok, unfilled):
    row = dict(
        validator=name,
        label=label,
        argv=args,
        old=old[0],
        new=new[0],
        unfilled=unfilled,
        stdout_equal=old[1] == new[1],
        stderr_equal=old[2] == new[2],
        match=ok,
    )
    if not ok or (label.endswith(".json") and old[0]):
        text = lambda value: value.decode() if isinstance(value, bytes) else value
        row.update(
            old_stdout=text(old[1]),
            new_stdout=text(new[1]),
            old_stderr=text(old[2]),
            new_stderr=text(new[2]),
        )
    ALL.append(row)


SCRATCH: Path
ALL = []
FAILED = []


def run(name, args, old=False):
    path = HERE / (name + "-validate.py")
    if old:
        source = SCRATCH / (name + "-old.py")
        if not source.exists():
            source.write_bytes(old_source(path))
        code = "import sys; from pathlib import Path; source=Path(sys.argv.pop(1)); target=sys.argv.pop(1); sys.argv[0]=target; sys.path.insert(0,str(Path(target).parent)); exec(compile(source.read_bytes(),target,'exec'),{'__file__':target,'__name__':'__main__'})"
        command = [sys.executable, "-c", code, str(source), str(path), *args]
    else:
        command = [sys.executable, str(path), *args]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


def compare(name, label, args, expect=None):
    a = run(name, args, True)
    b = run(name, args)
    same = a == b
    count = lambda out: re.findall(rb"^UNKNOWN-CELLS: (\d+)", out, re.M)
    ok = same and count(a[1]) == count(b[1]) and (expect is None or b[0] == expect)
    record(name, label, args, a, b, ok, [x.decode() for x in count(b[1])])
    if not ok:
        FAILED.append((name, label))
        print("FAIL", name, label, "rc", a[0], b[0], "expected", expect)
        for prefix, result in [("old", a), ("new", b)]:
            print(prefix, result[1].decode(), result[2].decode())
    return b


def grade_artifacts():
    for name, suffixes in NAMES.items():
        unit = name.split("-")[0]
        for suffix in suffixes:
            path = HERE / (unit + "-" + suffix + ".json")
            args = [str(path)]
            if name.endswith("-s4"):
                args = ["--kind", "window" if suffix == "window" else "attack", *args]
            if name == "m3u6a1-attack":
                args = ["--table", str(path)]
            result = compare(name, path.name, args)
            print(
                name,
                path.name,
                "rc=" + str(result[0]),
                "unfilled="
                + ",".join(
                    x.decode() for x in re.findall(rb"^UNKNOWN-CELLS: (\d+)", result[1], re.M)
                ),
            )
            if name == "m3u4-s3" and suffix == "probes":
                compare(name, path.name + " differential", args + ["--differential"])
        compare(name, "default", [])
        compare(name, "help", ["--help"])


def load(name, old):
    path = HERE / (name + "-validate.py")
    source = old_source(path).decode() if old else path.read_text()
    ns = {"__file__": str(path), "__name__": "baseline" if old else "candidate"}
    exec(compile(source, str(path), "exec"), ns)
    guard = next(n for n in ast.parse(source).body if isinstance(n, ast.If))
    call = next(
        n
        for n in ast.walk(guard)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "main"
    )
    ns["_main_call"] = compile(ast.Expression(call), str(path), "eval")
    return ns


def inline(ns, args):
    stdout = io.StringIO()
    stderr = io.StringIO()
    before = sys.argv
    sys.argv = [ns["__file__"], *args]
    exception = None
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = eval(ns["_main_call"], ns)
            except SystemExit as error:
                code = error.code if isinstance(error.code, int) else 1 if error.code else 0
                if isinstance(error.code, str):
                    print(error.code, file=sys.stderr)
            except Exception as error:
                exception = (type(error).__name__, str(error))
                code = 1
    finally:
        sys.argv = before
    return code, stdout.getvalue(), stderr.getvalue(), exception


def compared_inline(name, label, args, pair, expect=None):
    a, b = [inline(ns, args) for ns in pair]
    ok = a == b and (expect is None or b[0] == expect)
    record(name, label, args, a, b, ok, re.findall(r"^UNKNOWN-CELLS: (\d+)", b[1], re.M))
    if not ok:
        FAILED.append((name, label))
        print("FAIL", name, label, "expected", expect, "old", a, "new", b)
    return b


def filled(seed, name):
    d = copy.deepcopy(seed)
    prose = "filled evidence with one checkable observation and its explicit reproduction " * 3

    def value(field):
        return (
            {
                "anchor": "src/cement_runtime/__init__.py:1",
                "symbol": (ROOT / "src/cement_runtime/__init__.py").read_text().splitlines()[0],
                "section": "§1",
                "outcome": "ok",
                "observation": {"observed": True},
                "action": "unchanged",
                "lens": "correctness-vs-code",
                "severity": "note" if name == "m3u2b-wave2" else "cleared",
                "finding": "no defect: " + prose,
                "divergence": "no divergence: " + prose,
                "verdict": "identical" if name == "m3u3-wave3" else "ok",
                "divergent": True if name == "m3u4-wave2" else "no",
                "test_name": "test_control",
                "head_sha": BASE,
                "diff_stat": "+20/-0",
                "driver": "pyproject.toml",
                "baseline": "the baseline observation before changes",
                "alt": "the alternative observation after changes",
                "expected": "exit 0 and the observable key set `{a, b}` " + prose,
                "result": "killed",
                "differs": "no",
            }
        ).get(field, prose)

    for field, v in d.items():
        if v == "unknown":
            d[field] = value(field)
    rows = d.get("rows", list(d.get("probes", {}).values()))
    for row in rows:
        for field, v in row.items():
            if v == "unknown" or v == {} or v == "":
                row[field] = value(field)
    return d


def grade_controls():
    for name in NAMES:
        pair = [load(name, old) for old in (True, False)]
        old, new = pair
        kinds = list(
            old.get("VALIDATORS", old.get("KINDS", old.get("SPEC", old.get("FIELDS", {}))))
        )
        if name == "m3u5a-wave1":
            kinds = ["map", "spike"]
        if name == "m3u6a1-attack":
            kinds = ["attack"]
        for kind in kinds:
            control = SCRATCH / (name + "-" + kind + "-control.json")
            if name == "m3u2b-wave2":
                if kind == "oracle":
                    seed = {
                        "kind": kind,
                        "impl_path": "unknown",
                        "driver_path": "unknown",
                        "commit": "unknown",
                        "probes": {
                            p: {"outcome": "unknown", "observation": {}, "note": ""}
                            for p in old["ORACLE_PROBES"]
                        },
                    }
                else:
                    prefix = {"divergences": "DIVERGENCE", "attack": "ATTACK", "review": "REVIEW"}[
                        kind
                    ]
                    seed = {
                        "kind": kind,
                        "rows": [
                            {"id": rid, **{field: "unknown" for field in old[prefix + "_FIELDS"]}}
                            for rid in old[prefix + "_IDS"]
                        ],
                    }
            else:
                if name == "m3u4-s3":
                    for ns in pair:
                        ns["SPEC"][kind]["path"] = control
                    inline(old, ["--emit-seed", kind])
                    old_bytes = control.read_bytes()
                    result = compared_inline(name, "emit " + kind, ["--emit-seed", kind], pair, 0)
                    if old_bytes != control.read_bytes():
                        FAILED.append((name, kind + " emitted seed bytes differ"))
                        print("FAIL", name, kind, "emitted seed bytes differ")
                    seed = json.loads(control.read_text())
                else:
                    args = (
                        ["--emit-stub", kind]
                        if name in ("m3u5a-wave1", "m3u5a-wave2", "m3u5b-wave2", "m3u6a2-wave2")
                        else ["--emit-seed"]
                        if name == "m3u6a1-attack"
                        else ["--kind", kind, "--emit-stub"]
                        if name == "m3u3-s4"
                        else ["--emit-seed", kind]
                    )
                    result = compared_inline(name, "emit " + kind, args, pair, 0)
                    seed = json.loads(result[1])
            args = (
                ["--kind", kind, str(control)]
                if name == "m3u3-s4"
                else ["--table", str(control)]
                if name == "m3u6a1-attack"
                else [str(control)]
            )
            control.write_text(json.dumps(seed))
            blank = compared_inline(name, "blank " + kind, args, pair, 1)
            good = filled(seed, name)
            control.write_text(json.dumps(good))
            green = compared_inline(name, "filled " + kind, args, pair, 0)
            print(
                "CONTROL",
                name,
                kind,
                "blank=" + str(blank[0]),
                re.findall(r"^UNKNOWN-CELLS: (\d+)", blank[1], re.M),
                "filled=" + str(green[0]),
            )
            # Every field on the first row crosses types, omission and placeholder variants.
            rows = good.get("rows", list(good.get("probes", {}).values()))
            keys = list(rows[0])
            for field in keys:
                for v in [None, False, 0, [], {}, "", "unknown", " UNKNOWN ", "cancelled", "x"]:
                    candidate = copy.deepcopy(good)
                    target = candidate.get("rows", list(candidate.get("probes", {}).values()))[0]
                    target[field] = v
                    control.write_text(json.dumps(candidate))
                    compared_inline(name, kind + " " + field + "=" + repr(v), args, pair)
                candidate = copy.deepcopy(good)
                del candidate.get("rows", list(candidate.get("probes", {}).values()))[0][field]
                control.write_text(json.dumps(candidate))
                compared_inline(name, kind + " omit " + field, args, pair)
            for change in (
                "missing",
                "duplicate",
                "extra",
                "empty",
                "wrong rows",
                "not object",
                "extra field",
            ):
                d = copy.deepcopy(good)
                if "rows" in d:
                    if change == "missing":
                        d["rows"].pop(0)
                    if change == "duplicate":
                        d["rows"].append(copy.deepcopy(d["rows"][0]))
                    if change == "extra":
                        d["rows"].append({**d["rows"][0], "id": "X99"})
                    if change == "empty":
                        d["rows"] = []
                    if change == "wrong rows":
                        d["rows"] = {}
                    if change == "not object":
                        d["rows"][0] = False
                    if change == "extra field":
                        d["rows"][0]["surplus"] = "x"
                else:
                    if change == "missing":
                        d["probes"].pop(next(iter(d["probes"])))
                    if change == "extra":
                        d["probes"]["surplus"] = copy.deepcopy(next(iter(d["probes"].values())))
                    if change == "empty":
                        d["probes"] = {}
                    if change == "wrong rows":
                        d["probes"] = []
                    if change == "not object":
                        d["probes"][next(iter(d["probes"]))] = False
                    if change == "extra field":
                        next(iter(d["probes"].values()))["surplus"] = "x"
                control.write_text(json.dumps(d))
                compared_inline(name, kind + " " + change, args, pair)
            for field in good:
                if field in ("rows", "probes"):
                    continue
                for v in (None, 0, [], {}, "", "unknown", " UNKNOWN ", "not-a-kind"):
                    d = copy.deepcopy(good)
                    d[field] = v
                    control.write_text(json.dumps(d))
                    compared_inline(name, kind + " top " + field + "=" + repr(v), args, pair)
                d = copy.deepcopy(good)
                del d[field]
                control.write_text(json.dumps(d))
                compared_inline(name, kind + " top omit " + field, args, pair)
            if name == "m3u2b-wave2" and kind != "oracle":
                d = copy.deepcopy(good)
                for field in d["rows"][0]:
                    if field != "id":
                        d["rows"][0][field] = "cancelled"
                control.write_text(json.dumps(d))
                compared_inline(name, kind + " cancelled row", args, pair, 0)
            if name == "m3u4-s3":
                control.write_text(json.dumps(seed))
                compared_inline(
                    name,
                    kind + " differential blank",
                    args + ["--differential"],
                    pair,
                    1 if kind == "probes" else 2,
                )
                d = copy.deepcopy(good)
                for row in d["rows"]:
                    row["main_observed"] = (
                        "filled observation with sufficient detail for this differential"
                    )
                    row["differs"] = "no"
                control.write_text(json.dumps(d))
                compared_inline(
                    name,
                    kind + " differential filled",
                    args + ["--differential"],
                    pair,
                    0 if kind == "probes" else 2,
                )
            control.unlink()
        for args in (["--self-test"],) if "self_test" in old else ():
            if name == "m3u6a1-attack":
                original_dir = SCRATCH / "original"
                original_dir.mkdir(exist_ok=True)
                target = original_dir / (name + "-validate.py")
                target.write_bytes(
                    subprocess.check_output(
                        ["git", "show", f"{BASE}:.agent/decisions/{target.name}"], cwd=ROOT
                    )
                )
                old["HERE"] = original_dir
                compared_inline(name, "self-test", args, pair, 0)
                target.unlink()
                original_dir.rmdir()
            else:
                compare(name, "self-test", args, 0)


def self_test():
    from unittest.mock import patch
    import wave_validate

    name = "m3u3-wave1"
    pair = [load(name, old) for old in (True, False)]
    seed = pair[0]["_seed"]("map")
    path = SCRATCH / "canary.json"
    path.write_text(json.dumps(seed))
    before = [inline(ns, [str(path)]) for ns in pair]
    if before[0] != before[1] or before[0][0] != 1:
        print("SELF-TEST: clean blank control did not agree at rc 1")
        return 1
    start = len(FAILED)
    with patch.object(wave_validate.StrictWave, "strings", return_value=0):
        compared_inline(name, "planted unfilled-counter deletion", [str(path)], pair)
    detected = len(FAILED) == start + 1
    del FAILED[start:]
    print("SELF-TEST: planted counter deletion detected" if detected else "SELF-TEST: SILENT")
    return 0 if detected else 1


def main(argv=None):
    import argparse

    global BASE, SCRATCH, NAMES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE, help="pre-extraction git revision")
    parser.add_argument("--json", type=Path, help="write the per-case evidence")
    parser.add_argument(
        "--self-test", action="store_true", help="plant a counter deletion in memory"
    )
    args = parser.parse_args(argv)
    BASE = subprocess.check_output(
        ["git", "rev-parse", "--verify", args.base + "^{commit}"], cwd=ROOT, text=True
    ).strip()
    ALL.clear()
    FAILED.clear()
    scratch = ROOT / ".scratch"
    created = not scratch.exists()
    scratch.mkdir(exist_ok=True)
    old_import_path = list(sys.path)
    sys.path.insert(0, str(HERE))
    try:
        with tempfile.TemporaryDirectory(prefix="p46-", dir=scratch) as directory:
            SCRATCH = Path(directory)
            if args.self_test:
                return self_test()
            NAMES = artifacts()
            grade_artifacts()
            grade_controls()
            if not ALL:
                print("FAIL: no comparisons ran")
                return 1
            if args.json:
                args.json.write_text(json.dumps({"base": BASE, "cases": ALL}, indent=2) + "\n")
            print(f"ARTIFACTS: {sum(map(len, NAMES.values()))}; VALIDATORS: {len(NAMES)}")
            print(f"CASES: {len(ALL)}; DIFFERENCES: {len(FAILED)}")
            return 1 if FAILED else 0
    finally:
        sys.path[:] = old_import_path
        if created and not any(scratch.iterdir()):
            scratch.rmdir()


if __name__ == "__main__":
    raise SystemExit(main())
