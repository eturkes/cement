#!/usr/bin/env python
"""Compare two runs of the M3.2a probe driver and report every divergence.

Rerun path, from committed state:

    uv run python .agent/decisions/m3u2a-store-probes.py --json /tmp/main.json
    (in the oracle worktree) uv run python .agent/decisions/m3u2a-store-probes.py --json /tmp/orc.json
    uv run python .agent/decisions/m3u2a-differential.py /tmp/main.json /tmp/orc.json

Exit 0 when the behavioral divergences equal the ruled set, exit 1 otherwise. Message text is
reported but never graded: an independent implementation chooses its own wording, and the
contract owns the exact strings the shipped implementation uses.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ruled in the acceptance contract, section 8 V03: VACUUM is refused by the open transaction
# both paths hold, so it is not a capability outcome here.
RULED_BEHAVIORAL_DIVERGENCES = frozenset({"W13"})


def load(path: Path) -> dict[str, dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))["probes"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="probe JSON of the shipped implementation")
    parser.add_argument("right", type=Path, help="probe JSON of the comparison implementation")
    arguments = parser.parse_args(argv)

    left, right = load(arguments.left), load(arguments.right)
    keys = sorted(set(left) | set(right))
    behavioral: list[str] = []
    textual: list[str] = []
    for key in keys:
        one, two = left.get(key), right.get(key)
        if one is None or two is None:
            behavioral.append(f"{key}: present only in {'right' if one is None else 'left'}")
            continue
        if one["outcome"] != two["outcome"] or one["exc_type"] != two["exc_type"]:
            behavioral.append(
                f"{key}: outcome {one['outcome']}/{two['outcome']} "
                f"class {one['exc_type']}/{two['exc_type']}"
            )
        elif one["message"] != two["message"]:
            textual.append(f"{key}: {one['message']!r} vs {two['message']!r}")

    print(f"probes={len(keys)} behavioral={len(behavioral)} textual={len(textual)}")
    for line in behavioral:
        print(f"BEHAVIORAL {line}")
    for line in textual:
        print(f"TEXT       {line}")

    seen = {line.split(":", 1)[0] for line in behavioral}
    if seen != set(RULED_BEHAVIORAL_DIVERGENCES):
        unruled = sorted(seen - RULED_BEHAVIORAL_DIVERGENCES)
        missing = sorted(RULED_BEHAVIORAL_DIVERGENCES - seen)
        print(f"UNRULED={unruled} MISSING={missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
