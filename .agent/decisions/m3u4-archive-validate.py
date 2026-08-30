#!/usr/bin/env python3
"""Grade M3.4's provenance split (review finding R15).

The wave chronology moved from ``.agent/decisions/m3u4-contract.md`` to
``.agent/archive/m3u4-chronology.md``. The contract keeps every ruled obligation, every
interpretive ground and every measured number. This validator proves that the move lost
nothing a later reader depends on, and it reruns from committed state.

Six checks, each with a DERIVED domain rather than a hand-written list, because a
forbidden list fails open on exactly the member nobody thought of (contract D02):

1. SECTIONS  - headings ``## 1.`` .. ``## 15.`` all present in the live contract. Section
   numbers are cited by six artifact tables, so a section may be rewritten but never
   renumbered or dropped.
2. OBLIGATIONS - D01..D27 all defined in the live contract.
3. CITATIONS - every ``section`` value in the six artifact tables resolves: each ``§N``
   names a live heading and each ``Dnn`` names a live obligation.
4. NUMBERS - every measured token in the PRE-SPLIT contract (multi-digit integers,
   decimals, ``+N/-N`` diffs, hex digests) survives in the live contract OR the archive.
   Domain is extracted from the baseline text, never enumerated by hand.
5. IDENTIFIERS - same rule for every backticked identifier in the pre-split contract.
6. BATTERY-NUMBERS - every multi-digit number the battery grader's own obligation texts
   name must resolve in the LIVE contract, because the battery grades against the
   contract and not against the archive. Domain is read out of
   ``m3u4-battery-validate.py``.

Checks 4 and 5 grade the PAIR, so they prove a token MOVED rather than vanished; check 6
is what holds the contract itself to the numbers a gate depends on. All three carry an
explicit PRUNED allowlist: a token may only leave with a recorded reason, and every
unmatched token is PRINTED rather than counted.

Usage::

    uv run python .agent/decisions/m3u4-archive-validate.py
    uv run python .agent/decisions/m3u4-archive-validate.py --root <staged-copy>

``--root`` grades a copy of the tree instead of the repository, so a seeded control never
touches the shipped files. The baseline always comes from this repository's pinned commit.

Exit 0 = the split is sound. Exit 1 = at least one check failed, with every offending
token printed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

REPO: Final = Path(__file__).resolve().parents[2]

# The contract as it stood before the split. Pinned, so the check reruns from any later
# commit and always grades against the same baseline.
BASELINE_SHA: Final = "77f44b0"
BASELINE_PATH: Final = ".agent/decisions/m3u4-contract.md"

SECTIONS: Final = tuple(range(1, 16))
OBLIGATIONS: Final = tuple(f"D{index:02d}" for index in range(1, 28))

ARTIFACTS: Final = (
    "m3u4-verdicts.json",
    "m3u4-attack.json",
    "m3u4-review.json",
    "m3u4-probes.json",
    "m3u4-map.json",
    "m3u4-mutants.json",
)

# Tokens deliberately dropped by the split, each with the reason it may go. Anything not
# listed here must survive in the contract or the archive.
PRUNED_NUMBERS: Final = {
    "320": "the plan draft's rejected pre-open split trigger; the review's L7 rejects it "
    "as not pre-open measurable, so quoting the number kept a dead threshold alive",
    "24": "the stale attack-lens count; m3u4-attack.json holds 39 rows and the contract "
    "now states 39",
}
PRUNED_IDENTIFIERS: Final = {
    "wt/spike-m3u4-binding": "worktree path, retired; the tree is reachable as tag "
    "m3u4-alt-binding and the archive names it",
    "wt/spike-m3u4-projection": "worktree path, retired; the tree is reachable as tag "
    "m3u4-alt-projection and the archive names it",
    "spike-m3u4-binding": "teammate name, dispatch state; the archive keeps the record",
    "spike-m3u4-projection": "teammate name, dispatch state; the archive keeps the record",
    ".agent/archive/": "superseded by the exact destination .agent/archive/m3u4-chronology.md, "
    "which the contract and this validator both name",
}

PRUNED_BATTERY_NUMBERS: Final[dict[str, str]] = {}

NUMBER_PATTERN: Final = re.compile(
    r"\+\d+/-\d+"  # diff sizes
    r"|\b\d+(?:,\d{3})+\b"  # grouped integers
    r"|\b\d+\.\d+\b"  # decimals
    r"|\b\d{2,}\b"  # multi-digit integers
    r"|\b[0-9a-f]{7,}\b"  # short SHAs and digests
)
IDENTIFIER_PATTERN: Final = re.compile(r"`([^`\n]+)`")
SECTION_TOKEN: Final = re.compile(r"§\s*(\d+)")
OBLIGATION_TOKEN: Final = re.compile(r"\bD(\d{2})\b")


def baseline_text() -> str:
    """Read the pre-split contract out of the pinned commit."""
    completed = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{BASELINE_SHA}:{BASELINE_PATH}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"cannot read {BASELINE_PATH} at {BASELINE_SHA}: {completed.stderr.strip()}"
        )
    return completed.stdout


def numbers(text: str) -> set[str]:
    """Every measured token, with digit grouping normalized away."""
    return {token.replace(",", "") for token in NUMBER_PATTERN.findall(text)}


def identifiers(text: str) -> set[str]:
    """Every backticked span, minus the ones that are prose rather than a name."""
    found: set[str] = set()
    for raw in IDENTIFIER_PATTERN.findall(text):
        value = raw.strip()
        # A backticked span carrying whitespace is quoted prose or SQL, not an identifier.
        if not value or " " in value:
            continue
        found.add(value)
    return found


def report(label: str, missing: list[str], detail: dict[str, str] | None = None) -> bool:
    """Print a check's verdict, naming every offending token."""
    if not missing:
        print(f"{label}: OK")
        return True
    print(f"{label}: FAIL, {len(missing)} missing")
    for token in sorted(missing):
        note = (detail or {}).get(token)
        print(f"  - {token}" + (f"  ({note})" if note else ""))
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="grade M3.4's provenance split")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO,
        help="tree to grade; defaults to this repository",
    )
    root = parser.parse_args(argv).root.resolve()
    contract = root / ".agent" / "decisions" / "m3u4-contract.md"
    archive_path = root / ".agent" / "archive" / "m3u4-chronology.md"

    live = contract.read_text(encoding="utf-8")
    archived = archive_path.read_text(encoding="utf-8")
    baseline = baseline_text()
    pair = live + "\n" + archived

    ok = True

    heading_numbers = {
        int(match) for match in re.findall(r"^##\s*(\d+)\.", live, flags=re.MULTILINE)
    }
    ok &= report(
        "SECTIONS",
        [f"## {number}." for number in SECTIONS if number not in heading_numbers],
    )

    defined = {
        match for match in re.findall(r"^(D\d{2})[.\s]", live, flags=re.MULTILINE)
    }
    defined |= {
        match
        for match in re.findall(r"^(D\d{2}) [A-Z]", live, flags=re.MULTILINE)
    }
    ok &= report("OBLIGATIONS", [item for item in OBLIGATIONS if item not in defined])

    unresolved: list[str] = []
    citations = 0
    for name in ARTIFACTS:
        path = root / ".agent" / "decisions" / name
        rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
        for row in rows:
            value = row.get("section") or ""
            for number in SECTION_TOKEN.findall(value):
                citations += 1
                if int(number) not in heading_numbers:
                    unresolved.append(f"{name}:{row.get('id')} cites §{number}")
            for number in OBLIGATION_TOKEN.findall(value):
                citations += 1
                if f"D{number}" not in defined:
                    unresolved.append(f"{name}:{row.get('id')} cites D{number}")
    ok &= report("CITATIONS", unresolved)
    print(f"CITATIONS-CHECKED: {citations}")

    # Membership is on whole TOKENS, never substrings: `24` sits inside `243` and
    # `_proposal_binding` sits inside `_proposal_bindings`, so a containment test would
    # certify a dropped token as surviving. Same rule the contract's own D05 states.
    # Digit grouping is presentation, so 10,000 and 10000 are one number.
    baseline_numbers = numbers(baseline)
    pair_numbers = numbers(pair)
    lost_numbers = [
        token
        for token in baseline_numbers
        if token not in pair_numbers and token not in PRUNED_NUMBERS
    ]
    ok &= report("NUMBERS", lost_numbers)
    print(f"NUMBERS-CHECKED: {len(baseline_numbers)}")

    baseline_identifiers = identifiers(baseline)
    pair_identifiers = identifiers(pair)
    lost_identifiers = [
        token
        for token in baseline_identifiers
        if token not in pair_identifiers and token not in PRUNED_IDENTIFIERS
    ]
    ok &= report("IDENTIFIERS", lost_identifiers)
    print(f"IDENTIFIERS-CHECKED: {len(baseline_identifiers)}")

    grader = (root / ".agent" / "decisions" / "m3u4-battery-validate.py").read_text(
        encoding="utf-8"
    )
    block = grader.split("OBLIGATIONS: dict[str, tuple[int, str]] = {", 1)[1].split(
        "\n}", 1
    )[0]
    graded_numbers = numbers(block) - set(re.findall(r'"B(\d{2})"', block))
    live_numbers = numbers(live)

    def resolves(token: str) -> bool:
        if token in live_numbers:
            return True
        # A digest is routinely quoted abbreviated, so a hex token resolves against any
        # longer live hex token it prefixes.
        if re.fullmatch(r"[0-9a-f]{7,}", token):
            return any(
                other.startswith(token)
                for other in live_numbers
                if re.fullmatch(r"[0-9a-f]{7,}", other)
            )
        return False

    lost_graded = [
        token
        for token in graded_numbers
        if not resolves(token) and token not in PRUNED_BATTERY_NUMBERS
    ]
    ok &= report("BATTERY-NUMBERS", lost_graded)
    print(f"BATTERY-NUMBERS-CHECKED: {len(graded_numbers)}")

    for token, reason in sorted({**PRUNED_NUMBERS, **PRUNED_IDENTIFIERS}.items()):
        print(f"PRUNED {token}: {reason}")

    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
