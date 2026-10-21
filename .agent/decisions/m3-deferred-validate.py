#!/usr/bin/env python3
"""Structural validator for the deferral queue `.agent/deferred.md` + its closed ledger.

Usage:
  uv run python .agent/decisions/m3-deferred-validate.py              # grade
  uv run python .agent/decisions/m3-deferred-validate.py --emit-stub  # seed skeleton

The queue carries one entry per open row of the archived polish register plus every
open row born after the migration; the archive keeps the full text, evidence and grounds
for the rows it holds. An entry = its row line plus the indented lines directly under
it, so `Accept:` and `unknown` are graded over the whole entry. The archive id set is DERIVED and asserted as a FLOOR, not an
identity: a queue that drops an archived row fails, while a new id is admitted, since
every off-path improvement born from here on enters the queue. `pri` is re-read from
the archive for every row the archive holds, so a hand-list cannot drift from it
(assurance law: assert the complement).

The archive's own headers are NOT uniform -- 11 of 61 rows spell `pri` without
backticks and 3 carry no `size` at all -- so the parse is pinned against a loose
`^- \\`pNN\\`` bound. Without that pin an over-strict header regex under-reads the
archive, the stub inherits the same short id set, and the id-set equality agrees
with itself: every downstream count stays self-consistent while rows vanish.
`size` stays in the archive alone; it was the retired flow's estimate and 3 rows
lack it, so it cannot be checked here.

Closure: a closed row leaves the queue in its closing commit and lands in the closed
ledger `.agent/archive/deferred-closed.md` as its queue entry verbatim, with `closed`
or `closed=<sha>` after `pri` plus a `Closed:` line carrying the rerun acceptance
evidence. `closed=<sha>` names the commit where the acceptance first held and must
resolve to a commit that is an ancestor of HEAD; bare `closed` = met by the pruning
commit itself, which cannot name its own SHA. Either way the grader DERIVES the pruning
commit from the ledger's history (`pending` while uncommitted) and reports closed rows
apart from open ones.

Monotonicity is enforced against EVERY committed revision of both files, not against
the archive and not against HEAD: the archive alone cannot see a born row, and a HEAD
floor collapses at a closing commit, where HEAD IS the candidate and a dropped row
leaves both sides at once. The floor is `archive ids | ids over both files' histories`,
and every floor id sits in exactly one of the queue and the closed ledger -- so a row
leaves the queue only by closing, and a closed row never leaves the ledger.

Exits 0 only when the archive parse is total, no row of that floor is missing, no id is
both open and closed, every row parses, every entry carries `Accept:` (a closed entry
also `Closed:`), every closure SHA resolves, and no cell is `unknown`. Cell length is
never graded (owner ruling, `CLAUDE.md` `Authoring`: strict limits stay out of checks on text).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

QUEUE_RE = re.compile(r"^- `(?P<id>p\d{2,})` `pri=(?P<pri>\d)` — (?P<body>.+)$")
CLOSED_RE = re.compile(
    r"^- `(?P<id>p\d{2,})` `pri=(?P<pri>\d)` `closed(?:=(?P<sha>[^`]*))?` — (?P<body>.+)$"
)
ARCHIVE_RE = re.compile(r"^- `(?P<id>p\d{2,})` `?pri=(?P<pri>\d)`?")
ARCHIVE_LOOSE_RE = re.compile(r"^- `p\d{2,}`")
ACCEPT_RE = re.compile(r"\bAccept: (?P<check>.+)$")
CLOSED_CLAUSE_RE = re.compile(r"\bClosed: \S")
SHA_RE = re.compile(r"[0-9a-f]{7,40}")


def _root() -> Path:
    """Repo root by upward search, so the file works from any tracked location."""
    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


ROOT = _root()
QUEUE = ROOT / ".agent/deferred.md"
CLOSED = ROOT / ".agent/archive/deferred-closed.md"
ARCHIVE = ROOT / ".agent/archive/polish.md"

HEADER = """# Deferral queue

Off-path improvements, one entry + acceptance check each: a `p<nn>` row line plus the
indented lines directly under it. Nothing here reaches a session for free;
`.agent/spec.md` `Tasks` names the rows that block the current spine. `pri` 1 = highest.
p01-p61 came from the frozen `.agent/archive/polish.md`, which holds their full text,
evidence + grounds under the same `p<nn>` id; a row born here (p62 on) is absent from the
archive, so its own entry is its whole record and must carry every anchor a future
session needs.

Gate for every row unless the row says otherwise: the full gate `.agent/gate`
(`.claude/rules/ops.md`). A row needing a scope source, an assurance tier or the unit set
changed is spine work, not queue work.

Closing a row = its closing commit moves the entry verbatim into
`.agent/archive/deferred-closed.md`, `closed` (met by that commit) or `closed=<sha>` (met
at an earlier commit, an ancestor of HEAD) after `pri`, plus a `Closed:` line holding the
rerun acceptance evidence.

Grader: `uv run python .agent/decisions/m3-deferred-validate.py` (floor = archive ids | the ids
of every committed revision of this queue and of the closed ledger; each floor id open here or
closed there, never both and never neither; `unknown` cells, a missing `Accept:` or `Closed:`
and an unresolvable closure SHA red).
"""

CLOSED_HEADER = """# Closed deferral rows

Rows closed out of `.agent/deferred.md`, ascending by id: each = its queue entry verbatim,
`closed` (met by the commit that moved it here) or `closed=<sha>` (met at that earlier
commit) after `pri`, plus a `Closed:` line holding the rerun acceptance evidence. A closed
row stays here for good; the grader `.agent/decisions/m3-deferred-validate.py` derives each
row's pruning commit from this file's history.
"""


def entries(
    text: str, unparsed: list[str], name: str, pattern: re.Pattern[str]
) -> list[tuple[int, re.Match[str], str]]:
    """Each `(lineno, row match, body)`; body joins the row line's body with its indented lines."""
    out: list[tuple[int, re.Match[str], list[str]]] = []
    current: list[str] | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.startswith("- `p"):
            match = pattern.match(line)
            if not match:
                unparsed.append(f"{name}:{lineno} {line[:70]!r}")
                current = None
                continue
            current = [match.group("body")]
            out.append((lineno, match, current))
        elif current is not None and line.strip() and line[0] in " \t":
            current.append(line.strip())
        else:
            current = None
    return [(lineno, match, " ".join(parts)) for lineno, match, parts in out]


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


def committed_ids(relative: str, pattern: re.Pattern[str]) -> tuple[dict[str, str], int, list[str]]:
    """`{id: oldest committed revision holding it}` over EVERY committed revision of one file.

    A floor read from HEAD alone collapses at a closing commit: HEAD is then the
    candidate itself, so a dropped row leaves both sides at once and grades clean.
    The union over history is append-only by construction and independent of any
    single revision, so a COMMITTED deletion still fails.

    A git failure must FAIL CLOSED: an empty floor grades clean while monotonicity is
    not graded at all. Only a genuinely untracked file (the first seed) is allowed to
    produce an empty history.
    """
    log = _git("log", "--format=%H", "--", relative)
    if log is None:
        return {}, 0, [f"git log over {relative} failed; history floor ungraded"]
    shas = log.split()
    errors: list[str] = []
    if not shas and _git("ls-files", "--error-unmatch", relative) is not None:
        errors.append(f"{relative} is tracked but has no commit touching it; history floor ungraded")
    out: dict[str, str] = {}
    # `git log` lists newest first; walking it reversed leaves each id's OLDEST holder.
    for sha in reversed(shas):
        text = _git("show", f"{sha}:{relative}")
        if text is None:
            errors.append(f"git show {sha[:9]}:{relative} failed; that revision ungraded")
            continue
        for match in map(pattern.match, text.splitlines()):
            if match:
                out.setdefault(match.group("id"), sha)
    return out, len(shas), errors


def shallowness() -> list[str]:
    # Comparing the call against "true\n" inline swallows its failure: `None` is not
    # "true\n", so an unanswerable shallowness question grades exactly like a proven
    # full clone. Every git read here fails closed only if this one does too.
    shallow = _git("rev-parse", "--is-shallow-repository")
    if shallow is None:
        return ["git rev-parse --is-shallow-repository failed; shallowness ungraded"]
    if shallow.strip() == "true":
        return ["shallow clone: history floor cannot cover every revision"]
    return []


def closure_sha_errors(row_id: str, sha: str | None) -> list[str]:
    """`closed=<sha>` must name a commit HEAD contains; bare `closed` carries no SHA."""
    if sha is None:
        return []
    if not SHA_RE.fullmatch(sha):
        return [f"{row_id} closure cell `closed={sha}` is not a 7-40 hex commit id"]
    if _git("cat-file", "-e", f"{sha}^{{commit}}") is None:
        return [f"{row_id} closure SHA {sha} does not resolve to a commit"]
    if _git("merge-base", "--is-ancestor", sha, "HEAD") is None:
        return [f"{row_id} closure SHA {sha} is not an ancestor of HEAD"]
    return []


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

    for lineno, match, body in entries(text, unparsed, "deferred.md", QUEUE_RE):
        row_id = match.group("id")
        order.append(row_id)
        seen[row_id] = match.group("pri")
        if not ACCEPT_RE.search(body):
            bad.append(f"deferred.md:{lineno} {row_id} has no `Accept:` clause")
            continue
        if "unknown" in body.lower():
            unknown.append(f"deferred.md:{lineno} {row_id}")

    closed: dict[str, str] = {}
    closed_order: list[str] = []
    met_at: dict[str, str] = {}
    closed_text = CLOSED.read_text(encoding="utf-8") if CLOSED.is_file() else None
    if closed_text is not None and not closed_text.startswith(CLOSED_HEADER):
        bad.append("closed ledger header has drifted from this file's CLOSED_HEADER constant")
    for lineno, match, body in entries(closed_text or "", unparsed, "deferred-closed.md", CLOSED_RE):
        row_id = match.group("id")
        closed_order.append(row_id)
        closed[row_id] = match.group("pri")
        if match.group("sha") is not None:
            met_at[row_id] = match.group("sha")
        bad.extend(closure_sha_errors(row_id, match.group("sha")))
        if not ACCEPT_RE.search(body):
            bad.append(f"deferred-closed.md:{lineno} {row_id} has no `Accept:` clause")
        if not CLOSED_CLAUSE_RE.search(body):
            bad.append(f"deferred-closed.md:{lineno} {row_id} has no `Closed:` clause")
        if "unknown" in body.lower():
            unknown.append(f"deferred-closed.md:{lineno} {row_id}")

    if len(want) != loose:
        bad.append(f"archive parse read {len(want)} of {loose} `- `pNN`` rows")
    committed, revisions, history_errors = committed_ids(".agent/deferred.md", QUEUE_RE)
    pruned, closed_revisions, closed_errors = committed_ids(
        ".agent/archive/deferred-closed.md", CLOSED_RE
    )
    bad.extend(history_errors + closed_errors + shallowness())
    floor = set(want) | set(committed) | set(pruned)
    missing = sorted(floor - set(seen) - set(closed), key=_ordinal)
    both = sorted(set(seen) & set(closed), key=_ordinal)
    never_queued = sorted(set(closed) - set(want) - set(committed), key=_ordinal)
    born = sorted((set(seen) | set(closed)) - set(want), key=_ordinal)
    for row_id, pri in (*seen.items(), *closed.items()):
        if row_id in want and want[row_id] != pri:
            bad.append(f"{row_id} pri={pri} != archive pri={want[row_id]}")
    if both:
        bad.append(f"open AND closed: {both}")
    if never_queued:
        bad.append(f"closed but never queued: {never_queued}")
    # Ordinal, not lexicographic: `sorted` puts p100 before p99.
    for name, ids in (("queue", order), ("closed ledger", closed_order)):
        if ids != sorted(ids, key=_ordinal):
            bad.append(f"{name} order is not ascending by id (first break at {_first_break(ids)})")
        if len(ids) != len(set(ids)):
            bad.append(f"duplicate row ids in the {name}")

    print(f"ARCHIVE-ROWS: {len(want)} of {loose} loose")
    print(f"COMMITTED-FLOOR: {len(floor)} over {revisions} queue + {closed_revisions} ledger revisions")
    print(f"QUEUE-ROWS: {len(seen)}")
    print(f"CLOSED-ROWS: {len(closed)}")
    for row_id in sorted(closed, key=_ordinal):
        pruning = pruned.get(row_id)
        met = f" met at {met_at[row_id]}" if row_id in met_at else ""
        print(f"  {row_id} pruned in {pruning[:9] if pruning else 'pending'}{met}")
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
