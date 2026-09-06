"""Emit M3.6a2's battery seed from the contract's own obligation list.

Deliverable-first checkpointing for code: the unit's first tool call fills a committed stub that
already names every intended unit with a failing body, so the id set cannot drift while the suite
is authored and the lead's counter (`STUB: n`) moves in place instead of tracking a file that does
not exist yet.

Names and docstrings are DERIVED from the contract, never retyped, so a renamed obligation renames
its stub. The generator REFUSES to overwrite a battery whose tests are no longer all stubs: it
would destroy authored predicates while reporting success, and the diff that hides it is a file
this script claims to own.

A stub body SKIPS rather than fails. M3.6a1's D28 asserts gate 1 is green at EVERY commit in its
range and walks history to prove it, so a deliberately-red commit breaks a standing obligation
permanently — history keeps the red revision after the unit that made it green closes. A skip keeps
gate 1 green, keeps the id set frozen, and still reports as unfilled through the validator's `STUB`
counter, which is the counter that has to move.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".agent/decisions/m3u6a2-contract.md"
BATTERY = ROOT / "tests/test_lifecycle_removal_battery.py"
SEED_MARKER = "SEED STUB"

OBLIGATION = re.compile(r"^- \*\*(L\d\d)\*\* (.+?)(?=^- \*\*L\d\d\*\* |^#|\Z)", re.M | re.S)

HEADER = '''"""M3.6a2 acceptance battery — one test per obligation in `m3u6a2-contract.md` section 3.

Authored against the contract alone. Every test must be RED at `da70a56` unless its obligation
asserts a PRESERVED invariant (L12, L14, L15, L16, L17, L18), which is legitimately green there.

Regenerate the stub set with `.agent/decisions/m3u6a2-seed-battery.py`; grade coverage with
`.agent/decisions/m3u6a2-battery-validate.py`.
"""
import unittest


class LifecycleRemovalBattery(unittest.TestCase):
'''


def slug(text: str) -> str:
    sentence = re.split(r"(?<=[a-z0-9`)])\\.\\s", text.strip(), maxsplit=1)[0]
    sentence = re.sub(r"[`*]", "", sentence)
    words = re.findall(r"[A-Za-z0-9_]+", sentence.lower())
    out: list[str] = []
    for word in words:
        if len("_".join(out + [word])) > 58:
            break
        out.append(word)
    return "_".join(out) or "obligation"


def render(rows: list[tuple[str, str]]) -> str:
    parts = [HEADER]
    for oid, text in rows:
        summary = " ".join(re.sub(r"\s+", " ", text).strip().split())
        parts.append(
            f"\n    def test_{oid.lower()}_{slug(text)}(self) -> None:\n"
            f'        """{oid}. {summary}"""\n\n'
            f'        self.skipTest("{SEED_MARKER}: {oid} has no predicate yet")\n'
        )
    return "".join(parts)


def main() -> int:
    rows = OBLIGATION.findall(CONTRACT.read_text(encoding="utf-8"))
    if not rows:
        sys.exit("ABORT: the contract defines no obligations")
    if BATTERY.exists():
        source = BATTERY.read_text(encoding="utf-8")
        authored = [
            name for name in re.findall(r"def (test_l\d\d_\w+)", source)
            if SEED_MARKER not in source.split(f"def {name}", 1)[1].split("\n    def ", 1)[0]
        ]
        if authored:
            sys.exit(f"ABORT: {len(authored)} authored tests would be destroyed: {authored[:5]}")
        if source == render(rows):
            print(f"NO-OP: {len(rows)} stubs already seeded")
            return 0
    BATTERY.write_text(render(rows), encoding="utf-8")
    print(f"SEEDED: {len(rows)} stubs -> {BATTERY.relative_to(ROOT)} ({BATTERY.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
