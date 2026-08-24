#!/usr/bin/env python3
"""Measure M3.4's real test burden by DELETING the surface, never by counting names.

  uv run python .agent/decisions/m3u4-burden.py            # all stages
  uv run python .agent/decisions/m3u4-burden.py --stage 2  # one stage
  uv run python .agent/decisions/m3u4-burden.py --emit     # rewrite m3u4-burden.json

Why this exists. A vocabulary census predicts the wrong break set: M3.1's map
classified 29 tests by token and the actual 29 differed by 3 members. So the
burden is measured by performing the deletion against a scratch copy of the tree
and letting the gate produce the work list.

Why it is staged. A raw field deletion reports a break set dominated by the
PRODUCTION construction sites that still pass the removed keyword, which inflates
the number by two orders of magnitude and hides the real test burden underneath.
Each stage therefore repairs the previous stage's production cascade before
measuring the next surface.

  stage 1  drop `request_id` from ProposalView and PendingProposalGap only
  stage 2  stage 1 + repair the three production construction sites
  stage 3  stage 2 + `review` returns ReviewResult instead of Resolved/Rejected

The gate is the sole configured one: `python -m unittest discover -s tests -t .`.
Every stage runs against a fresh `git worktree` at the recorded base commit, so
the primary tree is never touched and the run is idempotent.

CASCADE ATTRIBUTION is the point of the report. A break set is only a work list
once the shared frames are factored out: the script groups every failure by its
DEEPEST test-tree frame, so one fixture helper standing behind a hundred failures
reads as one edit rather than a hundred.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORT = pathlib.Path(__file__).with_suffix(".json")
BASE = "da63741"

MODELS = "src/cement_runtime/models.py"
SYSTEM = "src/cement_runtime/system.py"
INIT = "src/cement_runtime/__init__.py"

# (path, old, new, expected occurrences). Every edit asserts its own count, so a
# repeated fragment aborts loudly instead of mutating the wrong span.
STAGE_EDITS: dict[int, list[tuple[str, str, str, int]]] = {
    1: [
        (MODELS, "class ProposalView:\n    id: str\n    partition: str\n    operation: str\n    operation_revision: int\n    request_id: str\n",
                 "class ProposalView:\n    id: str\n    partition: str\n    operation: str\n    operation_revision: int\n", 1),
        (MODELS, "class PendingProposalGap:\n    proposal_id: str\n    request_id: str\n",
                 "class PendingProposalGap:\n    proposal_id: str\n", 1),
    ],
    2: [
        (SYSTEM, '                request_id=str(row["bound_request_id"]),\n', "", 1),
        (SYSTEM, '            "request_id": str(row["bound_request_id"]),\n', "", 1),
        (SYSTEM, "            request_id=request_id,\n            operation_revision=operation_revision,",
                 "            operation_revision=operation_revision,", 1),
    ],
    3: [
        (MODELS, "@dataclass(frozen=True, slots=True)\nclass ProposalView:",
                 '@dataclass(frozen=True, slots=True)\nclass ReviewResult:\n    proposal_id: str\n'
                 '    status: Literal["accepted", "corrected", "rejected"]\n    example_id: str | None = None\n\n\n'
                 "@dataclass(frozen=True, slots=True)\nclass ProposalView:", 1),
        (SYSTEM, "Rejected(request_id=request_id, proposal_id=proposal_id)",
                 'ReviewResult(proposal_id=proposal_id, status="rejected")', 1),
        (SYSTEM, 'return Resolved(\n            request_id=request_id,\n            output=final.value,\n'
                 '            source="confirmed",\n            example_id=example_id,\n        )',
                 "return ReviewResult(proposal_id=proposal_id, status=proposal_status, example_id=example_id)", 1),
        (INIT, "    ProposalView,", "    ProposalView,\n    ReviewResult,", 1),
        (INIT, '    "ProposalView",', '    "ProposalView",\n    "ReviewResult",', 1),
    ],
}


def _apply(tree: pathlib.Path, stage: int) -> None:
    for relative, old, new, expected in STAGE_EDITS[stage]:
        path = tree / relative
        text = path.read_text(encoding="utf-8")
        found = text.count(old)
        if found != expected:
            raise SystemExit(f"stage {stage}: {relative} matched {found} times, expected {expected}")
        replaced = text.replace(old, new)
        if replaced == text:
            raise SystemExit(f"stage {stage}: {relative} edit changed no bytes")
        path.write_text(replaced, encoding="utf-8")
    if stage == 3:
        # `review` now names ReviewResult; import it beside the other models.
        path = tree / SYSTEM
        text = path.read_text(encoding="utf-8")
        match = re.search(r"from \.models import \(\n((?:    \w+,\n)+)\)", text)
        if match is None:
            raise SystemExit("stage 3: models import block not found")
        names = sorted(set(match.group(1).split()) | {"ReviewResult,"})
        path.write_text(text[:match.start(1)] + "".join(f"    {n}\n" for n in names) + text[match.end(1):],
                        encoding="utf-8")


def _analyse(log: str) -> dict:
    entries = re.findall(r"^(?:FAIL|ERROR): (\S+) \(([\w.]+)\)", log, re.M)
    modules = collections.Counter(qualified.rsplit(".", 1)[0] for _, qualified in entries)
    frames: collections.Counter[str] = collections.Counter()
    for block in log.split("=" * 70):
        hit = re.search(r"^(?:FAIL|ERROR): \S+ \([\w.]+\)", block, re.M)
        if hit is None:
            continue
        found = re.findall(r'File "[^"]*/((?:tests|src)/[\w./]+)", line (\d+), in (\S+)', block)
        if found:
            path, line, function = found[-1]
            frames[f"{path}:{line} in {function}"] += 1
    ran = re.search(r"^Ran (\d+) tests in ([\d.]+)s", log, re.M)
    return {
        "broken_tests": len(entries),
        "tests_run": int(ran.group(1)) if ran else None,
        "seconds": float(ran.group(2)) if ran else None,
        "by_module": dict(modules.most_common()),
        "deepest_frames": dict(frames.most_common(6)),
        "distinct_edit_sites": len(frames),
    }


def _run(stage: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="m3u4-burden-") as scratch:
        tree = pathlib.Path(scratch) / "tree"
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "-q", "--detach", str(tree), BASE], check=True)
        try:
            for applied in range(1, stage + 1):
                _apply(tree, applied)
            done = subprocess.run(
                ["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                cwd=tree, capture_output=True, text=True,
            )
            result = _analyse(done.stdout + done.stderr)
            result["stage"] = stage
            result["gate_returncode"] = done.returncode
            return result
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(tree)], check=False)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=sorted(STAGE_EDITS))
    parser.add_argument("--emit", action="store_true", help="rewrite the committed JSON report")
    args = parser.parse_args(argv[1:])
    stages = [args.stage] if args.stage else sorted(STAGE_EDITS)
    results = []
    for stage in stages:
        result = _run(stage)
        results.append(result)
        print(f"stage {stage}: {result['broken_tests']} broken of {result['tests_run']} "
              f"across {result['distinct_edit_sites']} distinct frames")
        for frame, count in result["deepest_frames"].items():
            print(f"    {count:4d}  {frame}")
    if args.emit:
        REPORT.write_text(json.dumps({"base": BASE, "stages": results}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
