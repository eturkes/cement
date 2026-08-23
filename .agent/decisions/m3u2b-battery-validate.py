#!/usr/bin/env python
"""Grade the M3.2b battery against the acceptance contract's obligation set.

    uv run python .agent/decisions/m3u2b-battery-validate.py tests/test_resolve_battery.py
    uv run python .agent/decisions/m3u2b-battery-validate.py --emit-stub tests/test_resolve_battery.py

`OBLIGATIONS` below is the single source of truth. `--emit-stub` writes the seed module from it,
so the stub and the grade can never drift. Each test method's docstring must OPEN with its
obligation id, `Bnn: `. A test whose body is still the seeded `self.skipTest("unfilled")` counts as
UNFILLED and does not discharge its obligation.

Exit 0 = every obligation carries at least one FILLED test, ids are unique and in-contract.
Exit 1 = anything else. UNFILLED is the flush metric: it falls as cells fill while the module's
test-name set stays flat.

Obligation ids trace to `.agent/decisions/m3u2b-contract.md` sections 2-9. Coverage is necessary,
never sufficient: section 10 also requires each obligation's test to FAIL when that obligation alone
is removed, which this grader cannot see and the mutation sweep measures.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys

CLAIM = re.compile(r"^(B\d{2})\s*:")
UNFILLED_MARK = "unfilled"

OBLIGATIONS: dict[str, str] = {
    # Section 2 - frozen public shape.
    "B01": (
        "resolve's signature ABI is frozen: parameter names and order "
        "(partition, operation, input_value), the keyword-only marker before "
        "expected_function_hash, its None default, and the FunctionResolution return "
        "annotation, pinned by inspect.signature plus typing.get_type_hints"
    ),
    "B02": (
        "FunctionResolution's shape is frozen: frozen=True, slots=True, NO kw_only so positional "
        "construction works, exactly the two fields verification and match, and resolved type hints"
    ),
    "B03": (
        "FunctionResolution is exported from cement_runtime and sits in __all__ in alphabetical "
        "position, between FunctionReport and FunctionSetPromotion"
    ),
    "B04": (
        "the two live resolve vocabularies never cross-wire: resolve returns exactly "
        "FunctionResolution by type identity and constructs no Resolved, and handle constructs no "
        "FunctionResolution"
    ),
    # Section 3 - the three states.
    "B05": (
        "verified hit shape: passed True, matched True, output equal to the promoted output, "
        "artifact_hash the promoted member's 64-hex digest, and verification.document present"
    ),
    "B06": (
        "verified miss shape: passed True, matched False, output None, artifact_hash None, and "
        "verification.document present"
    ),
    "B07": (
        "failed verdict shape: passed False, match None, verification.document None"
    ),
    "B08": (
        "the six checks keep verify_function's keys and emitted order and are neither renamed nor "
        "re-scored: duplicate-input-digests, abi-canonicalizer-uniform, sealed-passing-reports, "
        "current-promotion-receipts, function-hash-matches-snapshot, persisted-function-receipt"
    ),
    "B09": (
        "capacity is an adjacent accept/reject pair at the effective FUNCTION_MAX_ENTRIES: a set of "
        "exactly N entries verifies and N+1 returns passed False with all six checks False, entries "
        "set to the real count, document None, and zero row enumeration (FABRICATED: the cap is "
        "patched, never built to 50,000)"
    ),
    "B10": (
        "an over-capacity failed verdict is NOT a miss: it is distinguishable from a verified miss "
        "by verification.passed and match alone, with no consumer needing the check detail"
    ),
    "B11": (
        "match is None iff verification.passed is False, both directions asserted, over every "
        "verification verify_function actually produces (hit, miss, and at least one failed verdict)"
    ),
    "B12": (
        "evaluate call counts by state, taken with a spy: hit 1, miss 1, failed verdict 0, so "
        "evaluation never runs on a failed verdict"
    ),
    "B13": (
        "a registered operation with a zero-entry promoted set is a verified miss for every input, "
        "never an error: passed True, entries 0, matched False"
    ),
    "B14": (
        "the `or document is None` clause is forced: a FABRICATED public "
        "FunctionVerification(passed=True, document=None) reaching resolve through an override of "
        "public verify_function returns match None instead of raising AttributeError"
    ),
    # Section 4 - argument validation precedence.
    "B15": (
        "each rejected argument carries its exact class and message: partition, operation, "
        "expected_function_hash 64-hex shape, and an input canonicalize refuses, including one "
        "above DEFAULT_MAX_BYTES"
    ),
    "B16": (
        "precedence is pinned by four ADJACENT-edge multi-invalid pairs: partition+operation reports "
        "partition, operation+expected hash reports operation, expected hash+input reports the "
        "expected hash, partition+input reports partition"
    ),
    "B17": (
        "all validation precedes any ledger read: a call section 4 rejects makes ZERO "
        "Store.transaction calls and ZERO verify_function calls, taken with spies"
    ),
    # Section 5 - purity, one pin per obligation.
    "B18": (
        "ledger bytes are unmoved: sha256 of the ledger file AND the full connection.iterdump() text "
        "are byte-identical across a hit, a miss and a failed verdict"
    ),
    "B19": (
        "the clock is never read: a System whose _now raises resolves all three states and returns "
        "the same resolutions"
    ),
    "B20": (
        "no event is emitted: events() is byte-identical and the event sequence counter is unmoved "
        "across all three states"
    ),
    "B21": (
        "no identifier is allocated, including a discarded one: cement_runtime.system.uuid.uuid4 "
        "patched to raise resolves all three states unchanged"
    ),
    "B22": (
        "no file is created: the full ledger DIRECTORY listing is identical across a hit, a miss and "
        "a failed verdict"
    ),
    "B23": (
        "a deleted ledger raises the contracted IntegrityError and does not recreate the path, "
        "checked absent before and after"
    ),
    "B24": (
        "no CandidateSource is invoked: a source spy records zero propose calls on ALL THREE states, "
        "with a raising propose as the belt-and-braces form"
    ),
    # Section 6 - snapshot obligations.
    "B25": (
        "exactly ONE Store.transaction(write=False) opens per resolve that reaches the ledger, and "
        "ZERO for a call section 4 rejects, both counted by a wraps= spy"
    ),
    "B26": (
        "connection.in_transaction stays True across the whole six-check pass, sampled at the sixth "
        "check rather than only at entry"
    ),
    "B27": (
        "evaluation runs over the DOCUMENT VALUE: evaluating the returned document after the "
        "snapshot has closed equals evaluating it inside the snapshot, artifact hash included"
    ),
    # Section 7 - raise versus failed verdict.
    "B28": (
        "the two conditions reachable through supported calls raise with exact class and message: an "
        "unregistered operation gives NotFoundError, a missing or unreadable ledger gives "
        "IntegrityError"
    ),
    "B29": (
        "ordinary supported state changes give a FAILED VERDICT and never an exception: a suspended "
        "member, a revoked member, revision drift, and a valid-but-wrong expected_function_hash"
    ),
    "B30": (
        "structurally corrupt bound content gives a FALSE check with bounded detail rather than a "
        "raise, corrupting the MIDDLE and the LAST of at least three entries"
    ),
    # Sections 8-9 - published cost and prose obligation.
    "B31": (
        "no shipped docstring reachable from resolve or FunctionResolution calls the path cheap, "
        "fast, cached, repeatable across calls, or a lease, and the cost referent stays citable"
    ),
    "B32": (
        "a canonically equivalent input resolves identically: the same object with reversed key "
        "insertion order gives the same matched output and the same artifact_hash"
    ),
    "B33": (
        "scope isolation survives the forward to verify_function: collider partitions and operations "
        "(tenant_a vs tenantXa, echo_1 vs echoX1, plus a case variant) never answer each other, and "
        "partition and operation are not swapped"
    ),
}

STUB_HEADER = '''"""M3.2b acceptance battery - one obligation at a time.

Seeded by `uv run python .agent/decisions/m3u2b-battery-validate.py --emit-stub <path>` from the
obligation set in that grader, which is derived from `.agent/decisions/m3u2b-contract.md`.

Fill one test per commit. Replace the seeded `self.skipTest` with the real probe; keep the leading
`Bnn:` docstring claim, because the grader reads it. A test may cover only the obligation it claims.
"""

from __future__ import annotations

import unittest


class ResolveBatteryTests(unittest.TestCase):
'''


def _emit_stub(path: Path) -> int:
    lines = [STUB_HEADER]
    for index, (identifier, text) in enumerate(sorted(OBLIGATIONS.items())):
        if index:
            lines.append("\n")
        body = "\n".join(f"        {fragment}" for fragment in _wrap(f"{identifier}: {text}"))
        lines.append(
            f"    def test_{identifier.lower()}(self) -> None:\n"
            f'        """\n{body}\n        """\n\n'
            f'        self.skipTest("{UNFILLED_MARK}")\n'
        )
    lines.append('\n\nif __name__ == "__main__":\n    unittest.main()\n')
    path.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {path} with {len(OBLIGATIONS)} seeded obligations")
    return 0


def _wrap(text: str, width: int = 88) -> list[str]:
    out: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            out.append(current)
            current = word
        else:
            current = candidate
    if current:
        out.append(current)
    return out


def _is_unfilled(node: ast.FunctionDef) -> bool:
    body = [item for item in node.body if not isinstance(item, ast.Expr) or not isinstance(item.value, ast.Constant)]
    if len(body) != 1 or not isinstance(body[0], ast.Expr):
        return False
    call = body[0].value
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "skipTest"
        and any(isinstance(arg, ast.Constant) and UNFILLED_MARK in str(arg.value) for arg in call.args)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", nargs="+", type=Path)
    parser.add_argument("--emit-stub", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.emit_stub:
        if len(arguments.module) != 1:
            print("--emit-stub takes exactly one path", file=sys.stderr)
            return 1
        return _emit_stub(arguments.module[0])

    filled: dict[str, list[str]] = {}
    unfilled: dict[str, list[str]] = {}
    names: list[str] = []
    problems: list[str] = []
    for path in arguments.module:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
                continue
            names.append(node.name)
            documentation = (ast.get_docstring(node) or "").strip()
            match = CLAIM.match(documentation)
            if match is None:
                problems.append(f"{path}:{node.lineno} {node.name} has no leading 'Bnn:' claim")
                continue
            target = unfilled if _is_unfilled(node) else filled
            target.setdefault(match.group(1), []).append(node.name)

    duplicates = sorted({name for name in names if names.count(name) > 1})
    claimed = set(filled) | set(unfilled)
    unknown = sorted(claimed - set(OBLIGATIONS))
    missing = [item for item in sorted(OBLIGATIONS) if item not in filled]

    print(f"tests={len(names)} obligations_filled={len(filled)}/{len(OBLIGATIONS)}")
    for item in sorted(OBLIGATIONS):
        mark = " ".join(filled.get(item, [])) or f"UNFILLED {' '.join(unfilled.get(item, ['absent']))}"
        print(f"  {item}: {mark}")
    print(f"UNFILLED: {len(missing)}")
    if duplicates:
        problems.append(f"duplicate test names: {duplicates}")
    if unknown:
        problems.append(f"obligation ids outside the contract: {unknown}")
    if missing:
        problems.append(f"UNCOVERED: {missing}")
    for problem in problems:
        print(f"PROBLEM {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
