"""M3.5b removal-burden measurement.

A break count is not a work list until its shared frames are factored out
(`.agent/decisions/m3u4-burden.py` is the committed pattern this follows).
This script deletes M3.5b's source surface in stages inside a throwaway
`git worktree`, runs the configured gate at each stage, and groups every
failure by its DEEPEST `tests/` frame, which is what turns a raw count into
a per-frame work list.

Stages are cumulative:

  1 grammar  - the `handle` and `request` `add_parser` blocks leave `_parser()`.
  2 dispatch - and the `_source` helper, its construction site, both dispatch
               branches, and the `CommandCandidateSource` import leave `cli.py`.

Every edit asserts its own occurrence count before applying, so a repeated
fragment aborts loudly instead of mutating the wrong span. The primary tree is
never touched: each stage builds its own detached worktree and removes it.

Usage:

    uv run python .agent/decisions/m3u5b-burden.py --out .agent/decisions/m3u5b-burden.json
    uv run python .agent/decisions/m3u5b-burden.py --stage 1 --keep
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CLI = "src/cement_runtime/cli.py"

# (stage, path, old, new, expected occurrences of `old`)
EDITS: tuple[tuple[int, str, str, str, int], ...] = (
    (
        1,
        CLI,
        '''    handle = commands.add_parser("handle", help="route or create an inert LLM proposal")
    handle.add_argument("operation")
    handle.add_argument("--input", required=True, help="JSON text; \'-\' reads stdin")
    handle.add_argument("--request-id")
    handle.add_argument("--retry-failed", action="store_true")
    handle.add_argument(
        "--source-command",
        help=\'JSON argv, e.g. \\\'["python","adapter.py"]\\\'; Cement runs it without a shell\',
    )
    handle.add_argument("--source-id", default="command-adapter")
    handle.add_argument("--source-timeout", type=float, default=60.0)

''',
        "",
        1,
    ),
    (
        1,
        CLI,
        '''    request = commands.add_parser("request", help="poll a request without resupplying input")
    request.add_argument("request_id")

''',
        "",
        1,
    ),
    (
        2,
        CLI,
        '''def _source(value: str | None, *, source_id: str, timeout: float) -> CommandCandidateSource | None:
    if value is None:
        return None
    parsed = parse_json(value, max_bytes=65_536).value
    if type(parsed) is not list or not parsed or any(type(item) is not str for item in parsed):
        raise ValidationError("--source-command must be a non-empty JSON array of strings")
    argv = [str(item) for item in parsed]
    return CommandCandidateSource(argv, source_id=source_id, timeout_seconds=timeout)


''',
        "",
        1,
    ),
    (
        2,
        CLI,
        '''    source = None
    if args.command == "handle":
        source = _source(
            args.source_command,
            source_id=args.source_id,
            timeout=args.source_timeout,
        )
    system = System(args.db, candidate_source=source)
''',
        "    system = System(args.db)\n",
        1,
    ),
    (
        2,
        CLI,
        '''    if args.command == "handle":
        return system.handle(
            args.partition,
            args.operation,
            _input(args.input),
            request_id=args.request_id,
            retry_failed=args.retry_failed,
        )
''',
        "",
        1,
    ),
    (
        2,
        CLI,
        '''    if args.command == "request":
        return system.request_status(args.partition, args.request_id)
''',
        "",
        1,
    ),
    (2, CLI, "from .source import CommandCandidateSource\n", "", 1),
)

GATE = ("uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-t", ".")
HEADER = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)")
FRAME = re.compile(r'^  File "([^"]+)", line (\d+), in (\S+)')


def apply_stage(tree: pathlib.Path, stage: int) -> list[str]:
    """Apply every edit up to and including `stage`, asserting each occurrence count."""
    applied: list[str] = []
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
        GATE, cwd=tree, capture_output=True, text=True, env={**_env(), "PYTHONDONTWRITEBYTECODE": "1"}
    )
    return completed.returncode, completed.stdout + completed.stderr


def _env() -> dict[str, str]:
    import os

    return dict(os.environ)


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
    tree = pathlib.Path(tempfile.mkdtemp(prefix=f"m3u5b-burden-s{stage}-"))
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
        for failure in failures:
            frames[failure["frame"] or "(no tests/ frame)"] = frames.get(failure["frame"] or "(no tests/ frame)", 0) + 1
        modules: dict[str, int] = {}
        for failure in failures:
            module = failure["dotted"].split(".")[1] if "." in failure["dotted"] else failure["dotted"]
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, action="append", help="stage to measure; repeatable")
    parser.add_argument("--out", help="write the measurement JSON here")
    parser.add_argument("--keep", action="store_true", help="leave each worktree in place")
    args = parser.parse_args(argv)

    stages = args.stage or [1, 2]
    report = {"head": subprocess.check_output(("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True).strip()}
    results = [measure(stage, args.keep) for stage in stages]
    report["stages"] = results
    for result in results:
        print(
            f"stage {result['stage']}: broken={result['broken']} "
            f"frames={result['distinct_frames']} ran={result['tests_ran']} rc={result['gate_returncode']}"
        )
        for frame, count in list(result["frames"].items())[:12]:
            print(f"    {count:4d}  {frame}")
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
