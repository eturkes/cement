#!/usr/bin/env python3
"""Structural validator for M3 planning-wave reports.

Usage:
  uv run python .agent/decisions/m3-report-validate.py <report.md> [--rev SHA]
  uv run python .agent/decisions/m3-report-validate.py --all

`--rev` resolves every anchor in git object `SHA` instead of the working tree. `--all` grades
every tracked `.agent/decisions/*.md` holding a recognized table AT THE COMMIT THAT ADDED IT
(p05): a record's anchors describe the tree it was written against, so grading it against a
later tree reds correct history, while grading it at its own base still catches an anchor that
was false when written.

Validates every pipe table whose header matches a known shape:

  ANCHOR table   | id | anchor | symbol | role | disposition | note |
  CLAIM table    | id | anchor | quote | falsified_by | note |
  QA table       | id | question | answer | source | confidence |

Checks:
  - ANCHOR/CLAIM: `anchor` cell is `path:line`, the path exists, the line exists,
    and the backticked `symbol`/`quote` text is a substring of that source line.
  - every table: no cell equals `unknown` (case-insensitive) once filled.
  - QA: `source` cell holds at least one http(s) URL or a repo path.

Prints one summary block and exits 0 only when TABLES>0, ANCHORS-BAD=0 and
UNKNOWN-CELLS=0.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

def _root() -> Path:
    """Repo root by upward search, so the file works from any tracked location."""
    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


ROOT = _root()
ANCHOR_RE = re.compile(r"^([\w./+-]+):(\d+)$")
TICK_RE = re.compile(r"`([^`]+)`")
URL_RE = re.compile(r"https?://\S+")

SHAPES = {
    ("id", "anchor", "symbol", "role", "disposition", "note"): ("anchor", 1, 2),
    ("id", "anchor", "quote", "falsified_by", "note"): ("claim", 1, 2),
    ("id", "question", "answer", "source", "confidence"): ("qa", None, None),
    ("unit", "tier", "tags", "owns", "depends", "size", "acceptance"): ("unit", None, None),
}
TIERS = {"kernel", "data", "docs"}


def cells(line: str) -> list[str]:
    body = line.strip()
    if not body.startswith("|"):
        return []
    parts = [c.strip() for c in body.strip("|").split("|")]
    return parts


def _git(*args: str) -> str | None:
    done = subprocess.run(("git", "-C", str(ROOT), *args), capture_output=True, check=False)
    return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None


def _lines(rel: str, rev: str | None) -> list[str]:
    """The file's lines in the working tree, or in git object `rev`; [] when absent."""
    if rev is not None:
        text = _git("show", f"{rev}:{rel}")
        return [] if text is None else text.splitlines()
    target = (ROOT / rel).resolve()
    return target.read_text(encoding="utf-8", errors="replace").splitlines() if target.is_file() else []


def _exists(rel: str, rev: str | None) -> bool:
    if rev is None:
        return (ROOT / rel).exists()
    return _git("cat-file", "-e", f"{rev}:{rel}") is not None


def main(argv: list[str]) -> int:
    if argv[1:] == ["--all"]:
        return grade_all()
    if len(argv) == 4 and argv[2] == "--rev":
        return grade(Path(argv[1]), argv[3])
    if len(argv) != 2:
        print("usage: m3-report-validate.py <report.md> [--rev SHA] | --all", file=sys.stderr)
        return 2
    return grade(Path(argv[1]), None)


# Records `--all` skips, each with its reason (owner-ruled at the MAINTAIN queue run's close, p05).
EXEMPT = {
    ".agent/decisions/m3-plan-review.md": "its 48 anchors point into the gitignored, deleted"
    " `.scratch/agents/plan-m3.md` (p10), so it reds at every revision, its adding commit included",
}


def grade_all() -> int:
    listed = (_git("ls-files", "--", ".agent/decisions/*.md") or "").split()
    failed = graded = 0
    for rel in sorted(set(EXEMPT) - set(listed)):
        print(f"STALE-EXEMPT {rel}: not a tracked record")
        failed += 1
    for rel in listed:
        if rel in EXEMPT:
            print(f"EXEMPT {rel}: {EXEMPT[rel]}")
            continue
        if not any(tuple(c.lower() for c in cells(line)) in SHAPES
                   for line in (ROOT / rel).read_text(encoding="utf-8").splitlines()):
            continue
        added = (_git("log", "--diff-filter=A", "--format=%H", "--", rel) or "").split()
        base = added[-1] if added else None
        print(f"== {rel} @ {base[:9] if base else 'working tree'}", flush=True)
        graded += 1
        failed += grade(ROOT / rel, base) != 0
    print(f"RECORDS: {graded} graded, {failed} failed")
    return 1 if failed or not graded else 0


def grade(report: Path, rev: str | None) -> int:
    if not report.is_file():
        print(f"MISSING-REPORT: {report}", file=sys.stderr)
        return 2

    lines = report.read_text(encoding="utf-8").splitlines()
    tables = 0
    rows = 0
    anchors_ok = 0
    anchors_bad: list[str] = []
    unknown_cells: list[str] = []
    qa_no_source: list[str] = []
    shape: tuple[str, int | None, int | None] | None = None
    width = 0
    in_fence = False
    cache: dict[str, list[str]] = {}

    for lineno, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        row = cells(line)
        if not row:
            shape = None
            continue
        key = tuple(c.lower() for c in row)
        if key in SHAPES:
            shape = SHAPES[key]
            width = len(row)
            tables += 1
            continue
        if shape is None:
            continue
        if all(set(c) <= set("-: ") for c in row if c):
            continue
        if len(row) != width:
            anchors_bad.append(f"{report.name}:{lineno} width {len(row)} != {width}")
            continue
        rows += 1
        for cell in row:
            if cell.lower() == "unknown":
                unknown_cells.append(f"{report.name}:{lineno}")
                break
        kind, a_idx, s_idx = shape
        if kind == "unit":
            tier = row[1].strip("`").lower()
            if tier not in TIERS:
                anchors_bad.append(f"{report.name}:{lineno} tier {tier!r} not in {sorted(TIERS)}")
            for path in TICK_RE.findall(row[3]):
                probe = path.rstrip("/")
                if not _exists(probe, rev) and not probe.endswith("/"):
                    parent = str(Path(probe).parent)
                    if not _exists(parent, rev):
                        anchors_bad.append(f"{report.name}:{lineno} owns {path!r} has no parent dir")
                        continue
                anchors_ok += 1
            if not TICK_RE.findall(row[3]):
                anchors_bad.append(f"{report.name}:{lineno} owns cell has no backticked path")
            continue
        if kind == "qa":
            src = row[3]
            if not URL_RE.search(src) and ":" not in src and "/" not in src:
                qa_no_source.append(f"{report.name}:{lineno}")
            continue
        anchor = row[a_idx]
        match = ANCHOR_RE.match(anchor)
        if not match:
            anchors_bad.append(f"{report.name}:{lineno} bad anchor {anchor!r}")
            continue
        rel, num = match.group(1), int(match.group(2))
        if rel not in cache:
            cache[rel] = _lines(rel, rev)
        src_lines = cache[rel]
        if not src_lines:
            anchors_bad.append(f"{report.name}:{lineno} no such file {rel}")
            continue
        if not (1 <= num <= len(src_lines)):
            anchors_bad.append(f"{report.name}:{lineno} {rel} has {len(src_lines)} lines, want {num}")
            continue
        ticks = TICK_RE.findall(row[s_idx])
        if not ticks:
            anchors_bad.append(f"{report.name}:{lineno} no backticked symbol in {row[s_idx]!r}")
            continue
        source = src_lines[num - 1]
        missing = [t for t in ticks if t not in source]
        if missing:
            anchors_bad.append(f"{report.name}:{lineno} {rel}:{num} lacks {missing!r}")
            continue
        anchors_ok += 1

    print(f"TABLES: {tables}")
    print(f"ROWS: {rows}")
    print(f"ANCHORS-OK: {anchors_ok}")
    print(f"ANCHORS-BAD: {len(anchors_bad)}")
    print(f"UNKNOWN-CELLS: {len(unknown_cells)}")
    print(f"QA-NO-SOURCE: {len(qa_no_source)}")
    for entry in anchors_bad[:40]:
        print(f"  BAD {entry}")
    for entry in unknown_cells[:20]:
        print(f"  UNKNOWN {entry}")
    for entry in qa_no_source[:20]:
        print(f"  NOSOURCE {entry}")
    failed = bool(anchors_bad or unknown_cells or qa_no_source) or tables == 0
    print("VERDICT: FAIL" if failed else "VERDICT: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
