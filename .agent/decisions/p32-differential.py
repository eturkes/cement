#!/usr/bin/env python3
"""p32 observable-equivalence driver; rc 0 equal, 1 different, 2 setup failure."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = Path(__file__).with_name("p32-scenarios.py")


class SetupError(Exception):
    pass


def git(*args):
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True,
    )
    if result.returncode:
        raise SetupError(f"git {' '.join(args)}: rc {result.returncode}: {result.stderr.strip()}")
    return result.stdout.strip()


@contextmanager
def checkout(revision, path):
    git("worktree", "add", "--quiet", "--detach", str(path), revision)
    try:
        yield path
    finally:
        git("worktree", "remove", "--force", str(path))


def run(tree, script):
    env = os.environ.copy()
    env.update(PYTHONPATH=os.pathsep.join((str(tree), str(tree / "src"))),
               PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    # A venv's editable-install path must never silently select the primary tree.
    launcher = (
        "import pathlib,runpy,sys; sys.pycache_prefix=sys.argv[2]+'.pycache'; "
        "import cement_runtime; root=pathlib.Path(sys.argv[1]).resolve(); "
        "loaded=pathlib.Path(cement_runtime.__file__).resolve(); "
        "assert loaded.is_relative_to(root/'src'), (loaded,root); "
        "script=sys.argv[2]; sys.argv=[script]; runpy.run_path(script,run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", launcher, str(tree), str(script)],
        cwd=tree, env=env, capture_output=True, text=True, timeout=300,
    )
    if result.returncode:
        raise SetupError(f"scenario process rc {result.returncode}: {result.stderr.strip()}")
    lines = result.stdout.splitlines()
    if not lines:
        raise SetupError("scenario process emitted no probes")
    seen = set()
    for line in lines:
        try:
            record = json.loads(line)
            probe = record["probe"]
            if not isinstance(probe, str) or probe in seen:
                raise ValueError("duplicate/non-string probe")
            if set(record) not in ({"probe", "result"}, {"probe", "raises"}):
                raise ValueError("invalid outcome keys")
            seen.add(probe)
        except (KeyError, TypeError, ValueError) as exc:
            raise SetupError(f"invalid scenario line: {line!r}: {exc}") from exc
    expected = {f"S{i:02d}" for i in range(1, 14)}
    actual = {probe.split(".")[0] for probe in seen}
    if actual != expected:
        raise SetupError(f"scenario census differs: expected {sorted(expected)}, got {sorted(actual)}")
    return lines


def compare(before, after, *, show=True):
    differences = 0
    for index in range(max(len(before), len(after))):
        left = before[index] if index < len(before) else "<missing>"
        right = after[index] if index < len(after) else "<missing>"
        if left == right:
            continue
        differences += 1
        if show:
            record = json.loads(left if left != "<missing>" else right)
            print(f"DIFF {record['probe']}")
            print(f"BASE {left}")
            print(f"HEAD {right}")
    if differences:
        if show:
            print(f"RESULT: FAIL ({differences} differing lines)")
        return 1
    if show:
        print(f"SAME {len(before)}")
        print("RESULT: PASS")
    return 0


def census(lines):
    counts = {}
    for line in lines:
        scenario = json.loads(line)["probe"].split(".")[0]
        counts[scenario] = counts.get(scenario, 0) + 1
    print("CENSUS " + " ".join(f"{name}={count}" for name, count in sorted(counts.items())))


def self_test(tree, script, temp):
    original = run(tree, script)
    census(original)
    repeat = run(tree, script)
    deterministic = compare(original, repeat, show=False) == 0
    print(f"SELF determinism: {'SAME' if deterministic else 'DIFF'} {len(original)}")
    if not deterministic:
        compare(original, repeat)
        return 1
    source = tree / "src/cement_runtime/system.py"
    for name in ("detail", "check-order"):
        mutant = temp / name
        shutil.copytree(tree / "src", mutant / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        target = mutant / "src/cement_runtime/system.py"
        text = source.read_text()
        if name == "detail":
            anchor = "entries have unique input digests"
            if text.count(anchor) != 1:
                raise SetupError(f"detail mutant anchor count={text.count(anchor)}, expected 1")
            changed = text.replace(anchor, "entries have MUTATED input digests", 1)
        else:
            # Mutate exactly the observable vector, independent of helper decomposition.
            changed = text + '''\n\n# p32 self-test: adjacent-check-order corruption in a disposable source copy.\nimport functools as _p32_functools\n_p32_original_verify = System.verify_function\n@_p32_functools.wraps(_p32_original_verify)\ndef _p32_swapped_verify(self, *args, **kwargs):\n    import dataclasses\n    result = _p32_original_verify(self, *args, **kwargs)\n    checks = result.checks\n    if len(checks) >= 2:\n        result = dataclasses.replace(result, checks=(checks[1], checks[0], *checks[2:]))\n    return result\nSystem.verify_function = _p32_swapped_verify\n'''
        if text == changed:
            raise SetupError(f"{name}: source mutation was a no-op")
        target.write_text(changed)
        observed = run(mutant, script)
        status = compare(original, observed, show=False)
        first = next((json.loads(a)["probe"] for a, b in zip(original, observed) if a != b), None)
        count = sum(a != b for a, b in zip(original, observed)) + abs(len(original) - len(observed))
        print(f"SELF {name}: {'DIFF' if status == 1 else 'SURVIVED'} rc={status} lines={count} first={first}")
        if status != 1:
            print("RESULT: FAIL")
            return 1
    print("RESULT: PASS")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--head")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        # Freeze ONE invoking-head scenario copy; old revisions need not carry the instrument.
        scenario_bytes = SCENARIOS.read_bytes()
        with tempfile.TemporaryDirectory(prefix="cement-p32-") as directory:
            temp = Path(directory)
            script = temp / "scenarios.py"
            script.write_bytes(scenario_bytes)
            with checkout(args.base, temp / "base") as base:
                if args.self_test:
                    return self_test(base, script, temp)
                before = run(base, script)
                census(before)
                if args.head:
                    with checkout(args.head, temp / "head") as head:
                        after = run(head, script)
                else:
                    after = run(ROOT, script)
                return compare(before, after)
    except (OSError, subprocess.SubprocessError, SetupError) as exc:
        print(f"SETUP: {exc}", file=sys.stderr)
        print("RESULT: ERROR")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
