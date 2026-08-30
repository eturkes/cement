"""Re-anchor the six M3.4 mutants whose targets MAIN rewrote after the catalogue was authored.

Usage:
  uv run python .agent/decisions/m3u4-reanchor-mutants.py           # rewrite
  uv run python .agent/decisions/m3u4-reanchor-mutants.py --check   # in-sync gate, rc 1 when stale

`m3u4-mutants.py` was authored against `e64baff`. Two later commits rewrote the exact
statements six of its mutants target: the pending count became a pair of `FILTER`
aggregates over a LEFT JOIN, the ids and feed statements became LEFT JOINs guarded by a
NULL-binding refusal, `_proposal_record` began passing the binding, and the adapter's
error message changed. Their anchors then resolved zero times, and the harness aborts
the whole campaign on the first `ANCHOR-MISS`, so one stale anchor hid 35 later verdicts.

Two of the six INVERT rather than move, and that is the substance rather than an
accident of text. M18 mutated an inner join into an outer one; the shipped code now IS
the outer one, so the mutation that reintroduces the defect is outer to INNER. M34
mutated `_proposal_content(row)` into `_proposal_content(binding)`; `binding` is now
what ships, so the mutation is the reverse. A mutant left pointing at its own fix is
not a weaker mutant, it is a mutant that tests nothing.

Replacing whole `Mutant(...)` blocks keeps this rerunnable from a clean base: a second
run finds every block already in its target form and reports `updated 0`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / ".agent" / "decisions" / "m3u4-mutants.py"

# The four statement anchors as they stand in the shipped adapter. Each is the join line
# plus the WHERE line that follows it, which is what makes it unique: the LEFT JOIN line
# alone now occurs three times.
IDS = (
    '                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\\n"\n'
    '                "            WHERE p.partition = ? AND p.id IN ({placeholders})\\n",\n'
)
FEED = (
    '                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\\n"\n'
    '                "            WHERE p.partition = ? AND (? IS NULL OR p.status = ?)\\n",\n'
)
COUNT = (
    '                "            LEFT JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\\n"\n'
    '                "            WHERE p.partition = ? AND p.status = \'pending\'\\n",\n'
)
DETAIL = (
    '                "            JOIN requests AS r ON r.partition = p.partition AND r.id = p.request_id\\n"\n'
    '                "            WHERE p.partition = ? AND r.operation = ? AND p.status = \'pending\'\\n"\n'
    '                "            ORDER BY p.id LIMIT ?\\n",\n'
)


def _swap(block: str, old: str, new: str) -> str:
    """Rewrite one line of a two-line anchor into its mutated form."""

    assert old in block, old
    return block.replace(old, new)


def _edit(anchor: str, mutated: str) -> str:
    return f"            edit(\n                SYSTEM,\n{anchor}{mutated}            ),\n"


def _like_partition(anchor: str) -> str:
    return _swap(anchor, "r.partition = p.partition", "r.partition LIKE p.partition")


def _like_request(anchor: str) -> str:
    return _swap(anchor, "r.id = p.request_id", "r.id LIKE p.request_id")


def _inner(anchor: str) -> str:
    return _swap(anchor, "            LEFT JOIN requests", "            JOIN requests")


M09 = _edit(
    COUNT,
    _swap(COUNT, "WHERE p.partition = ?", "WHERE p.partition LIKE ?"),
)

M16 = "".join(
    _edit(anchor, _like_partition(anchor)) for anchor in (IDS, FEED, COUNT, DETAIL)
)

M17 = "".join(
    _edit(anchor, _like_request(anchor)) for anchor in (IDS, FEED, COUNT, DETAIL)
)

# The detail statement is deliberately absent from M18. Its inner join is unreachable as
# a defect, because the count statement raises on any pending orphan in the partition
# before the detail statement runs, so mutating it would ship an equivalent mutant.
M18 = "".join(_edit(anchor, _inner(anchor)) for anchor in (IDS, FEED, COUNT))

M20 = (
    "            edit(\n"
    "                SYSTEM,\n"
    '                "    except (IndexError, KeyError, TypeError, ValidationError) as exc:\\n"\n'
    '                "        raise IntegrityError(\\"proposal binding row has invalid scalar fields\\") from exc\\n",\n'
    '                "    except (IndexError, KeyError, TypeError) as exc:\\n"\n'
    '                "        raise IntegrityError(\\"proposal binding row has invalid scalar fields\\") from exc\\n",\n'
    "            ),\n"
)

M34 = (
    "            edit(\n"
    "                SYSTEM,\n"
    # `_proposal_content(binding)` also appears inside `review`, so the anchor carries
    # `_proposal_record`'s own preceding line to resolve exactly once.
    '                "        self._validate_proposal_shape(row)\\n"\n'
    '                "        input_json, proposed, provenance = self._proposal_content(binding)\\n",\n'
    '                "        self._validate_proposal_shape(row)\\n"\n'
    '                "        input_json, proposed, provenance = self._proposal_content(binding.row)\\n",\n'
    "            ),\n"
)

EDITS: dict[str, str] = {
    "M09": M09,
    "M16": M16,
    "M17": M17,
    "M18": M18,
    "M20": M20,
    "M34": M34,
}

BLOCK = re.compile(
    r'(    Mutant\(\n        "(?P<id>M\d\d)",\n        \(\n)(?P<edits>.*?)(\n?        \),\n        \()',
    re.DOTALL,
)


def rewrite(text: str) -> tuple[str, int]:
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        identifier = match.group("id")
        if identifier not in EDITS:
            return match.group(0)
        wanted = EDITS[identifier].rstrip("\n")
        if match.group("edits").rstrip("\n") == wanted:
            return match.group(0)
        changed += 1
        return f"{match.group(1)}{wanted}{match.group(4)}"

    return BLOCK.sub(replace, text), changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when the harness is stale")
    args = parser.parse_args(argv)

    text = HARNESS.read_text(encoding="utf-8")
    found = {match.group("id") for match in BLOCK.finditer(text)}
    missing = sorted(set(EDITS) - found)
    if missing:
        print(f"INVALID: the harness has no block for {missing}")
        return 2

    updated, changed = rewrite(text)
    if args.check:
        print(f"MUTANTS-REANCHORED: {len(EDITS)}  STALE: {changed}")
        print("RESULT: IN-SYNC" if changed == 0 else "RESULT: STALE")
        return 0 if changed == 0 else 1

    HARNESS.write_text(updated, encoding="utf-8")
    print(f"WROTE: {HARNESS.relative_to(ROOT)}  updated {changed} of {len(EDITS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
