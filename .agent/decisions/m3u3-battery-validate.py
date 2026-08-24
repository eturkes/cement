#!/usr/bin/env python3
"""Obligation grader for the M3.3 battery. Discharges contract D30.

Usage:
  uv run python .agent/decisions/m3u3-battery-validate.py
  uv run python .agent/decisions/m3u3-battery-validate.py --emit-stub

The graded artifact is ``tests/test_submission_battery.py``. Every obligation the
M3.3 acceptance contract numbers - B01-B02, P01-P06, D01-D42 - owns at least one
test there, named ``test_<id>_<slug>``. ``--emit-stub`` writes the seed: every
required test present, every body the UNFILLED marker. That file is
STRUCTURALLY valid and still exits 1, so UNFILLED-TESTS is the flush metric and
each filled test lowers it by one.

MAIN owns every id and every ``min_tests`` count below. A test whose name carries
an unknown obligation id is reported, never ignored: report a wrong subject to
MAIN instead of renaming it.

Retarget clause: seeding must never cap coverage. EXTRA tests for a seeded
obligation are graded exactly like seeded ones, so a lens that finds a second
edge of an obligation adds ``test_<id>_<other_slug>`` and the count rises.

Exit 0 = every obligation covered at its required count AND no test left
unfilled AND every test carrying a docstring that states its obligation. Exit 1 =
any gap. Exit 2 = the artifact is missing or unparseable.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATTERY = ROOT / "tests" / "test_submission_battery.py"
CONTRACT = ROOT / ".agent" / "decisions" / "m3u3-contract.md"

UNFILLED = "UNFILLED"
DOCSTRING_MIN = 40
TEST_NAME = re.compile(r"^test_(?P<id>[bpd]\d{2})_[a-z0-9_]+$")

# ---------------------------------------------------------------------------
# The obligation manifest. id -> (min_tests, subject).
#
# ``min_tests`` is 1 unless the contract itself demands several INDEPENDENT
# pins: D07 and D35 are total orders needing one probe per adjacent edge, D15
# carries four independent purity pins plus the rollback matrix X12 forced, and
# D16's commit spy needs its own positive control.
# ---------------------------------------------------------------------------
OBLIGATIONS: dict[str, tuple[int, str]] = {
    "B01": (1, "SCHEMA_VERSION is 2 and SCHEMA is 14,580 B / 5be3d79f..., equal to SCHEMA_FINGERPRINT"),
    "B02": (1, "cli.py, _command_supervisor.py and example_adapter.py are byte-identical to f9b9755"),
    "P01": (1, "two methods; candidate is keyword-only and REQUIRED on submit_proposal"),
    "P02": (1, "both return the proposal id as a bare str, type(result) is str, no new model"),
    "P03": (1, "submit_proposal never invokes a configured source, even one whose propose raises"),
    "P04": (1, "self.candidate_source is propose's only candidate authority for GENERATION"),
    "P05": (1, "neither name is in __all__ nor a module attribute; both reachable only through System"),
    "P06": (1, "handle is 12,866 B / 1182130a2b3a under the whole-line span with newlines stripped"),
    "D01": (1, "success footprint over declared SCHEMA tables: one requests, one proposals, one events row"),
    "D02": (1, "the request row is pending with proposal_id set, no lease, attempts == 1"),
    "D03": (1, "the event is proposal.created with handle's payload and subject minus request identity"),
    "D04": (1, "no idempotency: byte-identical content submitted twice writes two of everything"),
    "D05": (1, "propose invokes the source exactly once on success, zero times before invocation raises"),
    "D06": (1, "one private persistence seam writes all three rows for both paths, spied at the seam"),
    "D07": (3, "validation order: partition, operation, input canonicalization, then candidate"),
    "D08": (1, "a bad partition together with a bad input_value reports the PARTITION error"),
    "D09": (1, "an argument-rejected call opens zero transactions and invokes zero sources, live spies"),
    "D10": (1, "omitted candidate and source= both raise Python's own TypeError, no shipped validator"),
    "D11": (1, "no connection the call holds is in_transaction while the source runs, positive control"),
    "D12": (1, "propose re-reads the revision under the write lock; submit_proposal binds whatever is current"),
    "D13": (1, "the revision read is scoped to one operation by partition and name, not operations()"),
    "D14": (1, "propose hands the source a CandidateRequest carrying the generated internal request id"),
    "D15": (5, "a failed submission mutates nothing of its own: counts, sequence, file sha256, iterdump, rollback matrix"),
    "D16": (2, "zero commit() calls on failures before commit, connect-factory spy with a live positive control"),
    "D17": (1, "no clock except self._now and no artifact/example/function table read, statement recorder"),
    "D18": (1, "source failure raises with __cause__, __context__ and every adapter frame absent"),
    "D19": (1, "the declared and the arbitrary source failure are indistinguishable through the raised error"),
    "D20": (1, "failure raises; it never returns and never writes request.fallback_failed or a failed row"),
    "D21": (1, "NotFoundError precedes source invocation but never precedes the missing-configuration check"),
    "D22": (1, "neither the return value nor the proposal.created event publishes the request identifier"),
    "D23": (1, "the eight named seams still expose the identifier; get_proposal is reachable from the return"),
    "D24": (1, "private means a storage role the new API neither accepts nor returns"),
    "D25": (1, "shipped prose says schema v2 retains the row and the existing readers still show its id"),
    "D26": (1, "the battery module declares no skips and the contract records a battery-close measurement"),
    "D27": (1, "the census test is cited by name, asserts exact counts, and violations == [] is load-bearing"),
    "D28": (1, "the census counts match the sites the shipped design produces, each recorded by method name"),
    "D29": (1, "every census site binds a simple connection name, so violations stays empty"),
    "D30": (1, "closure instruments exist and the contract publishes the grader command and the mutant set"),
    "D31": (1, "CandidateSourceError's docstring names explicit submission, never a supervised fallback"),
    "D32": (1, "both docstrings state persistence, no idempotency, adapter execution, and each raised error"),
    "D33": (1, "no shipped surface calls submission cheap, safe-to-retry, deduplicated or request-free"),
    "D34": (1, "README and the three normative docs carry no sentence the new surface falsifies"),
    "D35": (3, "propose precedence: arguments, then source is None, then the lookup, then invocation"),
    "D36": (1, "propose snapshots candidate_source once, so the None check and the invocation bind one object"),
    "D37": (1, "unusable non-None configuration is contained as CandidateSourceError with no callable() pre-flight"),
    "D38": (1, "a malformed source RETURN is contained exactly like a raised source failure"),
    "D39": (1, "the catch is exactly Exception; BaseException members propagate unchanged with zero footprint"),
    "D40": (1, "one canonical snapshot serves the call; mutating request.input changes no stored byte"),
    "D41": (1, "README and the normative docs name both methods and publish authority, return, cost and containment"),
    "D42": (1, "the proposal row shape, including status_sequence bound to the proposal.created sequence"),
}

STUB_HEADER = '''"""Diff-blind obligation battery for M3.3 request-free submission.

One test per numbered obligation of ``.agent/decisions/m3u3-contract.md``, named
``test_<id>_<slug>``. Coverage is graded by
``uv run python .agent/decisions/m3u3-battery-validate.py``.

Every test states its obligation in its own docstring, including how the
assertion reproduces it, because a finding is graded by whether its reproduction
is stated and never by whether its number differs.
"""

from __future__ import annotations

import unittest


class SubmissionBatteryTests(unittest.TestCase):
    """Contract-derived pins. The author reads the contract, never the diff."""
'''


def _fail(message: str) -> None:
    print(f"INVALID: {message}")


def _slug(subject: str) -> str:
    words = re.findall(r"[a-z0-9]+", subject.lower())
    return "_".join(words[:6])


def emit_stub() -> int:
    """Write the seed: every required test present, every body UNFILLED."""
    parts = [STUB_HEADER]
    for identifier, (count, subject) in OBLIGATIONS.items():
        for index in range(count):
            suffix = "" if count == 1 else f"_{index + 1}"
            name = f"test_{identifier.lower()}_{_slug(subject)}{suffix}"
            parts.append(
                f'\n    def {name}(self) -> None:\n'
                f'        """{identifier}. {subject}\n\n'
                f'        Reproduction: state here how this test reproduces the obligation.\n'
                f'        """\n'
                f'        self.fail("{UNFILLED}: {identifier}")\n'
            )
    parts.append('\n\nif __name__ == "__main__":  # pragma: no cover\n    unittest.main()\n')
    BATTERY.parent.mkdir(parents=True, exist_ok=True)
    BATTERY.write_text("".join(parts), encoding="utf-8")
    print(f"WROTE: {BATTERY.relative_to(ROOT)}")
    return 0


def _is_unfilled(node: ast.FunctionDef) -> bool:
    for statement in ast.walk(node):
        if isinstance(statement, ast.Constant) and isinstance(statement.value, str):
            if statement.value.startswith(f"{UNFILLED}:"):
                return True
    return False


def grade() -> int:
    if not BATTERY.exists():
        _fail(f"{BATTERY.relative_to(ROOT)} is missing; run --emit-stub first")
        return 2
    try:
        tree = ast.parse(BATTERY.read_text(encoding="utf-8"))
    except SyntaxError as error:
        _fail(f"{BATTERY.relative_to(ROOT)} does not parse: {error}")
        return 2

    found: dict[str, list[str]] = {identifier: [] for identifier in OBLIGATIONS}
    unfilled: list[str] = []
    undocumented: list[str] = []
    unknown: list[str] = []
    skipped: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
            continue
        for decorator in node.decorator_list:
            if "skip" in ast.dump(decorator):
                skipped.append(node.name)
        match = TEST_NAME.match(node.name)
        if match is None:
            unknown.append(f"{node.name} (name does not match test_<id>_<slug>)")
            continue
        identifier = match.group("id").upper()
        if identifier not in OBLIGATIONS:
            unknown.append(f"{node.name} (no obligation {identifier} in the contract)")
            continue
        found[identifier].append(node.name)
        if _is_unfilled(node):
            unfilled.append(node.name)
            continue
        docstring = ast.get_docstring(node) or ""
        if not docstring.startswith(f"{identifier}.") or len(docstring) < DOCSTRING_MIN:
            undocumented.append(node.name)

    uncovered = {
        identifier: (len(names), OBLIGATIONS[identifier][0])
        for identifier, names in found.items()
        if len(names) - sum(1 for name in names if name in unfilled) < OBLIGATIONS[identifier][0]
    }

    for identifier, (have, need) in sorted(uncovered.items()):
        print(f"UNCOVERED: {identifier} has {have} filled test(s), needs {need}")
    for name in sorted(unknown):
        _fail(f"unknown obligation: {name}")
    for name in sorted(undocumented):
        _fail(f"docstring must open with the obligation id and state its reproduction: {name}")
    for name in sorted(skipped):
        _fail(f"skip decorator on {name}; a skipped test increments the count and still prints OK")

    total = sum(len(names) for names in found.values())
    print(f"OBLIGATIONS: {len(OBLIGATIONS)}")
    print(f"TESTS: {total}")
    print(f"UNFILLED-TESTS: {len(unfilled)}")
    print(f"OBLIGATIONS-UNCOVERED: {len(uncovered)}")
    ok = not (uncovered or unknown or undocumented or skipped or unfilled)
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-stub", action="store_true", help="write the all-UNFILLED seed")
    args = parser.parse_args(argv)
    return emit_stub() if args.emit_stub else grade()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
