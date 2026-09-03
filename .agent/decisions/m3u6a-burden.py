"""Measure M3.6a's removal burden by staging the deletion and running the gate.

A vocabulary census cannot produce a work list: it names lines, not the tests that
break. This stages the source-only deletion in throwaway `git worktree`s, runs the
sole configured gate per stage, and groups every failure by its deepest `tests/`
frame, because a break count collapses onto shared fixture helpers and overstates
the work by an order of magnitude.

Two edit kinds. `DELETIONS` removes a named definition through the AST, asserting
exactly one match, so no anchor can drift onto a sibling. `EDITS` is the anchored
text form with a per-edit occurrence assertion. Both are idempotent against a fresh
worktree and abort loudly rather than mutate the wrong span.

Stages, each cumulative:

  1 methods  - the public lifecycle methods plus every private helper reachable
               only from them.
  2 lease    - the generation-lease constructor knob, its microsecond field, and
               the clock bound named after it.
  3 revise   - request cancellation on operation revision, plus the event payload
               key that reports its row count.
  4 models   - the five lifecycle result models, the `Outcome` alias, and every
               import and `__all__` entry naming them.
  5 request  - `CandidateRequest.request_id`, with the private request-row id
               minted inside `_persist_proposal` instead.
  6 imports  - stage 5 plus the two test-module import lists that name a deleted
               model. Stage 5 alone hides its own worst frames: three modules fail
               at import, so 342 tests never run and the break count READS LOWER
               than stage 1's. The hospital demo stays broken on purpose - it is
               the unit's own implementation work, never an import repair.

Usage:
    uv run python .agent/decisions/m3u6a-burden.py --stage 1 --stage 5 --out out.json
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SYSTEM = "src/cement_runtime/system.py"
MODELS = "src/cement_runtime/models.py"
INIT = "src/cement_runtime/__init__.py"
DEMO = "examples/hospital_ocr/run_demo.py"

# (stage, relative path, container class or None, definition name)
DELETIONS: tuple[tuple[int, str, str | None, str], ...] = (
    (1, SYSTEM, "System", "handle"),
    (1, SYSTEM, "System", "_fail_generation"),
    (1, SYSTEM, "System", "_outcome"),
    (1, SYSTEM, "System", "request_status"),
    (1, SYSTEM, "System", "_request_revision_is_current"),
    (4, MODELS, None, "Resolved"),
    (4, MODELS, None, "InProgress"),
    (4, MODELS, None, "FallbackFailed"),
    (4, MODELS, None, "Rejected"),
    (4, MODELS, None, "ReconciliationRequired"),
)

# (stage, relative path, old, new, expected occurrence count)
EDITS: tuple[tuple[int, str, str, str, int], ...] = (
    (
        1,
        SYSTEM,
        "    # -- routing + supervised fallback --------------------------------------\n\n",
        "",
        1,
    ),
    (
        2,
        SYSTEM,
        "        clock_us: Callable[[], int] | None = None,\n"
        "        generation_lease_seconds: int = 120,\n"
        "    ) -> None:\n"
        "        generation_lease_seconds = _bounded_int(\n"
        "            generation_lease_seconds,\n"
        '            "generation_lease_seconds",\n'
        "            minimum=1,\n"
        "            maximum=3_600,\n"
        "        )\n",
        "        clock_us: Callable[[], int] | None = None,\n    ) -> None:\n",
        1,
    ),
    (
        2,
        SYSTEM,
        "        self._clock_us = clock_us if clock_us is not None else (lambda: time.time_ns() // 1_000)\n"
        "        self._lease_us = generation_lease_seconds * 1_000_000\n",
        "        self._clock_us = clock_us if clock_us is not None else (lambda: time.time_ns() // 1_000)\n",
        1,
    ),
    (
        2,
        SYSTEM,
        "            or now > _MAX_SQLITE_INTEGER - self._lease_us\n"
        "        ):\n"
        '            raise StateError("clock must return a lease-safe signed 64-bit microsecond timestamp")\n',
        "            or now > _MAX_SQLITE_INTEGER\n"
        "        ):\n"
        '            raise StateError("clock must return a signed 64-bit microsecond timestamp")\n',
        1,
    ),
    (
        3,
        SYSTEM,
        "            invalidated_generators = connection.execute(\n"
        '                """\n'
        "                UPDATE requests\n"
        "                SET status = 'failed', error_code = 'operation_revised',\n"
        "                    lease_owner = NULL, lease_until_us = NULL, updated_at_us = ?\n"
        "                WHERE partition = ? AND operation = ? AND operation_revision = ?\n"
        "                  AND status = 'generating'\n"
        '                """,\n'
        "                (now, partition, operation, previous),\n"
        "            ).rowcount\n",
        "",
        1,
    ),
    (
        3,
        SYSTEM,
        '                    "revised_by": revised_by,\n'
        '                    "invalidated_generators": invalidated_generators,\n',
        '                    "revised_by": revised_by,\n',
        1,
    ),
    (
        4,
        MODELS,
        "Outcome: TypeAlias = (\n"
        "    Resolved\n"
        "    | ReviewRequired\n"
        "    | InProgress\n"
        "    | FallbackFailed\n"
        "    | Rejected\n"
        "    | ReconciliationRequired\n"
        ")\n\n\n",
        "",
        1,
    ),
    (4, SYSTEM, "    FallbackFailed,\n", "", 1),
    (4, SYSTEM, "    InProgress,\n", "", 1),
    (4, SYSTEM, "    Outcome,\n", "", 1),
    (4, SYSTEM, "    ReconciliationRequired,\n    Rejected,\n    Resolved,\n", "", 1),
    (4, INIT, "    FallbackFailed,\n", "", 1),
    (4, INIT, "    InProgress,\n", "", 1),
    (4, INIT, "    ReconciliationRequired,\n    Rejected,\n    Resolved,\n", "", 1),
    (4, INIT, '    "FallbackFailed",\n', "", 1),
    (4, INIT, '    "InProgress",\n', "", 1),
    (4, INIT, '    "ReconciliationRequired",\n    "Rejected",\n    "Resolved",\n', "", 1),
    (
        5,
        MODELS,
        "    operation_revision: int\n    request_id: str\n    input: JSONValue\n",
        "    operation_revision: int\n    input: JSONValue\n",
        1,
    ),
    (
        5,
        SYSTEM,
        "        expected_revision: int | None,\n        request_id: str,\n        input_json: CanonicalJSON,\n",
        "        expected_revision: int | None,\n        input_json: CanonicalJSON,\n",
        1,
    ),
    (
        5,
        SYSTEM,
        "            proposal_id = _new_id(\"prop\")\n",
        "            proposal_id = _new_id(\"prop\")\n            request_id = _new_id(\"req\")\n",
        1,
    ),
    (
        5,
        SYSTEM,
        "            expected_revision=None,\n            request_id=_new_id(\"req\"),\n",
        "            expected_revision=None,\n",
        1,
    ),
    (
        5,
        SYSTEM,
        "        revision = self._submission_revision(partition, operation)\n"
        '        request_id = _new_id("req")\n',
        "        revision = self._submission_revision(partition, operation)\n",
        1,
    ),
    (
        5,
        SYSTEM,
        "                    operation_revision=revision,\n"
        "                    request_id=request_id,\n"
        "                    input=input_json.value,\n",
        "                    operation_revision=revision,\n                    input=input_json.value,\n",
        1,
    ),
    (
        5,
        SYSTEM,
        "            expected_revision=revision,\n            request_id=request_id,\n",
        "            expected_revision=revision,\n",
        1,
    ),
    (6, "tests/test_system.py", "    FallbackFailed,\n", "", 1),
    (6, "tests/test_system.py", "    InProgress,\n", "", 1),
    (6, "tests/test_system.py", "    ReconciliationRequired,\n    Resolved,\n", "", 1),
    (6, "tests/test_resolve_battery.py", "    Resolved,\n", "", 1),
)

GATE = ("uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-t", ".")
HEADER = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)")
FRAME = re.compile(r'^  File "([^"]+)", line (\d+), in (\S+)')


def _definition(tree: ast.Module, container: str | None, name: str) -> ast.AST:
    scope: list[ast.AST]
    if container is None:
        scope = list(tree.body)
    else:
        holder = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == container]
        if len(holder) != 1:
            raise SystemExit(f"CONTAINER-MISS: {container} matched {len(holder)} definitions")
        scope = list(holder[0].body)
    found = [
        node
        for node in scope
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name
    ]
    if len(found) != 1:
        raise SystemExit(f"DEFINITION-MISS: {container or '<module>'}.{name} matched {len(found)}")
    return found[0]


def delete_definition(path: pathlib.Path, container: str | None, name: str) -> int:
    """Drop one named definition, its decorators, and the blank lines it owned."""
    text = path.read_text(encoding="utf-8")
    node = _definition(ast.parse(text), container, name)
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    lines = text.splitlines(keepends=True)
    # Absorb the blank separator lines that followed the definition, so the file
    # keeps its two-blank-line module rhythm and one-blank-line class rhythm.
    end = node.end_lineno
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    removed = end - start + 1
    del lines[start - 1 : end]
    path.write_text("".join(lines), encoding="utf-8")
    return removed


def apply_stage(tree: pathlib.Path, stage: int) -> list[str]:
    """Apply every deletion and edit up to `stage`, asserting each match count."""
    applied: list[str] = []
    for edit_stage, relative, container, name in DELETIONS:
        if edit_stage > stage:
            continue
        removed = delete_definition(tree / relative, container, name)
        applied.append(f"{relative}: -{removed} lines for {container or '<module>'}.{name}")
    for edit_stage, relative, old, new, expected in EDITS:
        if edit_stage > stage:
            continue
        path = tree / relative
        text = path.read_text(encoding="utf-8")
        found = text.count(old)
        if found != expected:
            raise SystemExit(
                f"ANCHOR-MISS stage {edit_stage} {relative}: "
                f"expected {expected} occurrence(s), found {found}\n--- anchor ---\n{old}"
            )
        updated = text.replace(old, new, expected)
        if updated == text:
            raise SystemExit(f"IDENTITY-EDIT stage {edit_stage} {relative}: replacement changed nothing")
        path.write_text(updated, encoding="utf-8")
        applied.append(f"{relative}:{old.splitlines()[0][:72]}")
    return applied


def run_gate(tree: pathlib.Path) -> tuple[int, str]:
    completed = subprocess.run(
        GATE,
        cwd=tree,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return completed.returncode, completed.stdout + completed.stderr


def parse_failures(output: str) -> list[dict[str, str]]:
    """Group each summary-header failure by its deepest `tests/` traceback frame.

    The summary header is authoritative: a docstring moves the inline verbose
    record's verdict onto the next line, so the inline form silently under-counts.
    """
    lines = output.splitlines()
    failures: list[dict[str, str]] = []
    index = 0
    while index < len(lines):
        match = HEADER.match(lines[index])
        if match is None:
            index += 1
            continue
        kind, name, dotted = match.groups()
        deepest = ""
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].startswith("====="):
            frame = FRAME.match(lines[cursor])
            if frame is not None and "/tests/" in frame.group(1):
                relative = frame.group(1).split("/tests/", 1)[1]
                deepest = f"tests/{relative}:{frame.group(2)} in {frame.group(3)}"
            cursor += 1
        failures.append({"kind": kind, "test": name, "dotted": dotted, "frame": deepest})
        index = cursor
    return failures


def measure(stage: int, keep: bool) -> dict[str, object]:
    tree = pathlib.Path(tempfile.mkdtemp(prefix=f"m3u6a-burden-s{stage}-"))
    shutil.rmtree(tree)
    subprocess.run(
        ("git", "-C", str(ROOT), "worktree", "add", "--detach", str(tree), "HEAD"),
        check=True,
        capture_output=True,
    )
    try:
        applied = apply_stage(tree, stage)
        code, output = run_gate(tree)
        failures = parse_failures(output)
        frames: dict[str, int] = {}
        modules: dict[str, int] = {}
        for failure in failures:
            key = failure["frame"] or "(no tests/ frame)"
            frames[key] = frames.get(key, 0) + 1
            dotted = failure["dotted"]
            module = dotted.split(".")[1] if "." in dotted else dotted
            modules[module] = modules.get(module, 0) + 1
        ran = re.search(r"^Ran (\d+) tests", output, re.MULTILINE)
        return {
            "stage": stage,
            "edits_applied": applied,
            "gate_returncode": code,
            "tests_ran": int(ran.group(1)) if ran else None,
            "broken": len(failures),
            "distinct_frames": len(frames),
            "frames": dict(sorted(frames.items(), key=lambda item: (-item[1], item[0]))),
            "modules": dict(sorted(modules.items(), key=lambda item: (-item[1], item[0]))),
            "failures": failures,
        }
    finally:
        if not keep:
            subprocess.run(
                ("git", "-C", str(ROOT), "worktree", "remove", "--force", str(tree)),
                check=False,
                capture_output=True,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure M3.6a's staged removal burden.")
    parser.add_argument("--stage", type=int, action="append", help="stage to measure; repeatable")
    parser.add_argument("--out", help="write the measurement JSON here")
    parser.add_argument("--keep", action="store_true", help="leave each worktree in place")
    args = parser.parse_args(argv)

    stages = args.stage or [1, 5]
    head = subprocess.check_output(("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True).strip()
    results = [measure(stage, args.keep) for stage in stages]
    report: dict[str, object] = {"head": head, "stages": results}
    for result in results:
        print(
            f"stage {result['stage']}: broken={result['broken']} "
            f"frames={result['distinct_frames']} ran={result['tests_ran']} rc={result['gate_returncode']}"
        )
        for frame, count in list(result["frames"].items())[:14]:
            print(f"    {count:4d}  {frame}")
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
