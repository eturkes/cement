#!/usr/bin/env python3
"""Structural validator for M3 planning-wave reports.

Usage: uv run python .scratch/m3-report-validate.py .scratch/agents/<name>.md

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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: m3-report-validate.py <report.md>", file=sys.stderr)
        return 2
    report = Path(argv[1])
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
                if not (ROOT / probe).exists() and not probe.endswith("/"):
                    parent = (ROOT / probe).parent
                    if not parent.is_dir():
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
        target = (ROOT / rel).resolve()
        if rel not in cache:
            if not target.is_file():
                cache[rel] = []
            else:
                cache[rel] = target.read_text(encoding="utf-8", errors="replace").splitlines()
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
