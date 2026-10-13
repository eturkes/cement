#!/usr/bin/env python3
"""Structural validator for the deferral queue `.agent/deferred.md`.

Usage:
  uv run python .agent/decisions/m3-deferred-validate.py              # grade
  uv run python .agent/decisions/m3-deferred-validate.py --emit-stub  # seed skeleton

The queue carries one entry per live row of the archived polish register plus every
row born after the migration; the archive keeps the full text, evidence and grounds
for the rows it holds. An entry = its row line plus the indented lines directly under
it, so `Accept:` and `unknown` are graded over the whole entry. The archive id set is DERIVED and asserted as a FLOOR, not an
identity: a queue that drops an archived row fails, while a new id is admitted, since
the queue is monotonic and takes every off-path improvement born from here on. `pri`
is re-read from the archive for every row the archive holds, so a hand-list cannot
drift from it (assurance law: assert the complement).

The archive's own headers are NOT uniform -- 11 of 61 rows spell `pri` without
backticks and 3 carry no `size` at all -- so the parse is pinned against a loose
`^- \\`pNN\\`` bound. Without that pin an over-strict header regex under-reads the
archive, the stub inherits the same short id set, and the id-set equality agrees
with itself: every downstream count stays self-consistent while rows vanish.
`size` stays in the archive alone; it was the retired flow's estimate and 3 rows
lack it, so it cannot be checked here.

Monotonicity is enforced against EVERY committed revision of the queue, not against
the archive and not against HEAD: the archive alone cannot see a born row, and a HEAD
floor collapses at a closing commit, where HEAD IS the candidate and a dropped row
leaves both sides at once. The floor is `archive ids | ids over the file's history`.

Exits 0 only when the archive parse is total, no row of that floor is missing, every
row parses, every entry carries `Accept:`, and no cell is `unknown`. Cell length is
never graded (owner ruling, global `Authoring`: strict limits stay out of checks on text).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

QUEUE_RE = re.compile(r"^- `(?P<id>p\d{2,})` `pri=(?P<pri>\d)` — (?P<body>.+)$")
ARCHIVE_RE = re.compile(r"^- `(?P<id>p\d{2,})` `?pri=(?P<pri>\d)`?")
ARCHIVE_LOOSE_RE = re.compile(r"^- `p\d{2,}`")
ACCEPT_RE = re.compile(r"\bAccept: (?P<check>.+)$")


def _root() -> Path:
    """Repo root by upward search, so the file works from any tracked location."""
    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


ROOT = _root()
QUEUE = ROOT / ".agent/deferred.md"
ARCHIVE = ROOT / ".agent/archive/polish.md"

HEADER = """# Deferral queue

Off-path improvements, one entry + acceptance check each: a `p<nn>` row line plus the
indented lines directly under it. The queue is monotonic and unattached, so nothing here
reaches a session for free; `.agent/spec.md` `Tasks` names the rows that block the current
spine. `pri` 1 = highest. p01-p61 came from the frozen `.agent/archive/polish.md`, which
holds their full text, evidence + grounds under the same `p<nn>` id; a row born here (p62
on) is absent from the archive, so its own entry is its whole record and must carry every
anchor a future session needs.

Gate for every row unless the row says otherwise: `uv run python -m unittest discover -s tests
-t .` plus `uv build` plus `.agent/spec-lint`. A row needing a scope source, an assurance tier
or the unit set changed is spine work, not queue work.

Grader: `uv run python .agent/decisions/m3-deferred-validate.py` (floor = archive ids | the ids
of every committed revision, so a born row cannot be dropped either; `unknown` cells + a missing
`Accept:` red).
"""


def entries(text: str, unparsed: list[str]) -> list[tuple[int, str, str, str]]:
    """Each `(lineno, id, pri, body)`; body joins the row line's body with its indented lines."""
    out: list[tuple[int, str, str, list[str]]] = []
    current: list[str] | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.startswith("- `p"):
            match = QUEUE_RE.match(line)
            if not match:
                unparsed.append(f"deferred.md:{lineno} {line[:70]!r}")
                current = None
                continue
            current = [match.group("body")]
            out.append((lineno, match.group("id"), match.group("pri"), current))
        elif current is not None and line.strip() and line[0] in " \t":
            current.append(line.strip())
        else:
            current = None
    return [(lineno, row_id, pri, " ".join(parts)) for lineno, row_id, pri, parts in out]


def archive_rows() -> tuple[dict[str, str], int]:
    """Return `{id: pri}` plus the loose row count the parse must equal."""
    lines = ARCHIVE.read_text(encoding="utf-8").splitlines()
    out: dict[str, str] = {}
    for line in lines:
        match = ARCHIVE_RE.match(line)
        if match:
            out[match.group("id")] = match.group("pri")
    loose = sum(1 for line in lines if ARCHIVE_LOOSE_RE.match(line))
    return out, loose


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(("git", "-C", str(ROOT), *args), capture_output=True, check=False)
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8", errors="replace")


def committed_ids() -> tuple[set[str], int, list[str]]:
    """Union of queue ids over EVERY committed revision of the file.

    A floor read from HEAD alone collapses at a closing commit: HEAD is then the
    candidate itself, so a dropped row leaves both sides at once and grades clean.
    The union over history is append-only by construction and independent of any
    single revision, so a COMMITTED deletion still fails.

    A git failure must FAIL CLOSED: an empty floor grades clean while monotonicity is
    not graded at all. Only a genuinely untracked queue (the first seed) is allowed to
    produce an empty history.
    """
    log = _git("log", "--format=%H", "--", ".agent/deferred.md")
    if log is None:
        return set(), 0, ["git log over .agent/deferred.md failed; history floor ungraded"]
    shas = log.split()
    errors: list[str] = []
    if not shas and _git("ls-files", "--error-unmatch", ".agent/deferred.md") is not None:
        errors.append("queue is tracked but has no commit touching it; history floor ungraded")
    out: set[str] = set()
    for sha in shas:
        text = _git("show", f"{sha}:.agent/deferred.md")
        if text is None:
            errors.append(f"git show {sha[:9]}:.agent/deferred.md failed; that revision ungraded")
            continue
        out |= {m.group("id") for m in map(QUEUE_RE.match, text.splitlines()) if m}
    # Comparing the call against "true\n" inline swallows its failure: `None` is not
    # "true\n", so an unanswerable shallowness question grades exactly like a proven
    # full clone. Every git read here fails closed only if this one does too.
    shallow = _git("rev-parse", "--is-shallow-repository")
    if shallow is None:
        errors.append("git rev-parse --is-shallow-repository failed; shallowness ungraded")
    elif shallow.strip() == "true":
        errors.append("shallow clone: history floor cannot cover every revision")
    return out, len(shas), errors


def _ordinal(row_id: str) -> int:
    return int(row_id[1:])


def emit_stub() -> int:
    rows, loose = archive_rows()
    if len(rows) != loose:
        print(f"ARCHIVE-PARSE-SHORT: {len(rows)} of {loose} rows", file=sys.stderr)
        return 2
    # The stub is built from the archive alone, so re-emitting over a live queue
    # silently deletes every row born after the freeze.
    if QUEUE.is_file():
        print(f"REFUSING-OVERWRITE: {QUEUE.relative_to(ROOT)} exists", file=sys.stderr)
        return 2
    body = [f"- `{row_id}` `pri={rows[row_id]}` — unknown. Accept: unknown." for row_id in sorted(rows)]
    QUEUE.write_text(HEADER + "\n" + "\n".join(body) + "\n", encoding="utf-8")
    print(f"WROTE {QUEUE.relative_to(ROOT)}: {len(rows)} rows")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:] == ["--emit-stub"]:
        return emit_stub()
    if argv[1:]:
        print("usage: m3-deferred-validate.py [--emit-stub]", file=sys.stderr)
        return 2
    if not QUEUE.is_file():
        print(f"MISSING-QUEUE: {QUEUE}", file=sys.stderr)
        return 2

    want, loose = archive_rows()
    seen: dict[str, str] = {}
    order: list[str] = []
    bad: list[str] = []
    unknown: list[str] = []
    unparsed: list[str] = []

    # The header states the grading rule this file implements, and `--emit-stub` is the
    # only writer that emits it -- yet it refuses to overwrite a live queue, so after the
    # first seed the two drift by hand-edit alone and nothing else would notice a header
    # that describes a floor the code stopped using.
    text = QUEUE.read_text(encoding="utf-8")
    if not text.startswith(HEADER):
        bad.append("queue header has drifted from this file's HEADER constant")

    for lineno, row_id, pri, body in entries(text, unparsed):
        order.append(row_id)
        seen[row_id] = pri
        if not ACCEPT_RE.search(body):
            bad.append(f"deferred.md:{lineno} {row_id} has no `Accept:` clause")
            continue
        if "unknown" in body.lower():
            unknown.append(f"deferred.md:{lineno} {row_id}")

    if len(want) != loose:
        bad.append(f"archive parse read {len(want)} of {loose} `- `pNN`` rows")
    committed, revisions, history_errors = committed_ids()
    bad.extend(history_errors)
    floor = set(want) | committed
    missing = sorted(floor - set(seen), key=_ordinal)
    born = sorted(set(seen) - set(want), key=_ordinal)
    for row_id in sorted(set(want) & set(seen), key=_ordinal):
        if want[row_id] != seen[row_id]:
            bad.append(f"{row_id} pri={seen[row_id]} != archive pri={want[row_id]}")
    # Ordinal, not lexicographic: `sorted` puts p100 before p99.
    if order != sorted(order, key=_ordinal):
        bad.append(f"row order is not ascending by id (first break at {_first_break(order)})")
    if len(order) != len(set(order)):
        bad.append("duplicate row ids in the queue")

    print(f"ARCHIVE-ROWS: {len(want)} of {loose} loose")
    print(f"COMMITTED-FLOOR: {len(committed)} over {revisions} revisions")
    print(f"QUEUE-ROWS: {len(seen)}")
    print(f"MISSING: {len(missing)} {missing[:10]}")
    print(f"BORN-AFTER-ARCHIVE: {len(born)} {born[:10]}")
    print(f"UNPARSED: {len(unparsed)}")
    print(f"UNKNOWN-ROWS: {len(unknown)}")
    print(f"BAD: {len(bad)}")
    for entry in (*unparsed[:10], *unknown[:10], *bad[:10]):
        print(f"  {entry}")
    failed = bool(missing or unparsed or unknown or bad) or not want
    print("VERDICT: FAIL" if failed else "VERDICT: PASS")
    return 1 if failed else 0


def _first_break(order: list[str]) -> str:
    for left, right in zip(order, order[1:]):
        if _ordinal(right) < _ordinal(left):
            return f"{left} -> {right}"
    return "?"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
