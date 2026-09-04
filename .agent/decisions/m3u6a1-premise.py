"""Measure M3.6a1's two migration premises against a real ledger.

The unit's plan line asserts two replacements. Neither is a fact until it is run,
so this probe runs both and prints a verdict per premise.

P1 -- ``propose`` reaches the identical final row state as ``handle``'s
generation branch. Every re-based fixture helper depends on it: the helpers call
``handle`` only to mint a pending proposal, then review it. If the two routes
differ in any application row the migration is not behaviour-preserving.

P2 -- ``resolve`` replaces ``handle``'s artifact-hit branch. The demo's Act 2 and
Act 3 assert ``Resolved(source="artifact")`` while the demo promotes its function
set only in Act 5, so this probe reproduces the Act-2 ledger state exactly and
asks ``resolve`` the same question ``handle`` answers there.

Run: ``uv run python .agent/decisions/m3u6a1-premise.py``
Exit 0 when every premise verdict was produced; the verdicts themselves are the
output, and a FALSE verdict is a finding rather than a harness failure.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cement_runtime.models import (  # noqa: E402
    Candidate,
    CandidateRequest,
    CompilePolicy,
    ReviewRequired,
)
from cement_runtime.system import System  # noqa: E402

PARTITION = "tenant-a"
OPERATION = "echo"

# Rows the two routes are compared over. `requests` is deliberately included:
# M3.6a1 keeps schema v2, so a private request row still backs every proposal and
# a difference there is a real difference, even though no public API exposes it.
TABLES = (
    "requests",
    "proposals",
    "events",
    "examples",
    "artifacts",
    "operations",
)


class EchoSource:
    """Deterministic candidate source, identical for both routes."""

    def __init__(self) -> None:
        self.calls = 0

    def propose(self, request: CandidateRequest) -> Candidate:
        self.calls += 1
        return Candidate(output={"echo": request.input}, provenance={"by": "probe"})


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000

    def __call__(self) -> int:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += seconds * 1_000_000


def _dump(database: str) -> dict[str, list[dict[str, object]]]:
    """Project every compared table as ordered plain rows."""
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        out: dict[str, list[dict[str, object]]] = {}
        for table in TABLES:
            rows = connection.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            out[table] = [dict(row) for row in rows]
        return out
    finally:
        connection.close()


def _volatile(table: str, column: str) -> bool:
    """Columns whose value is a fresh identifier or a wall-clock reading.

    These differ between any two runs of the same route, so comparing them would
    report a difference that carries no information about the migration.
    """
    if column in {"id", "request_id", "proposal_id", "example_id", "artifact_id"}:
        return True
    return column.endswith("_at_us") or column.endswith("_until_us")


def _shape(dump: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    """Reduce a dump to the part two routes must agree on."""
    shape: dict[str, object] = {}
    for table, rows in dump.items():
        shape[f"{table}.count"] = len(rows)
        shape[f"{table}.rows"] = [
            {k: v for k, v in row.items() if not _volatile(table, k)} for row in rows
        ]
    return shape


def _build(database: str, *, route: str) -> tuple[dict[str, object], int]:
    """Drive one proposal to an accepted review through the named route."""
    source = EchoSource()
    clock = Clock()
    system = System(database, candidate_source=source, clock_us=clock)
    system.register_operation(
        PARTITION, OPERATION, policy=CompilePolicy(3, 2, 10)
    )
    if route == "handle":
        outcome = system.handle(PARTITION, OPERATION, {"x": 1}, request_id="r1")
        assert isinstance(outcome, ReviewRequired), outcome
        proposal_id = outcome.proposal_id
    else:
        proposal_id = system.propose(PARTITION, OPERATION, {"x": 1})
    view = system.get_proposal(PARTITION, proposal_id)
    assert view.proposed_output == {"echo": {"x": 1}}, view.proposed_output
    system.review(
        PARTITION, proposal_id, reviewer="alice", decision="accept"
    )
    return _shape(_dump(database)), source.calls


def _keys_differing(
    left: dict[str, object], right: dict[str, object]
) -> tuple[str, ...]:
    return tuple(
        key for key in sorted(set(left) | set(right)) if left.get(key) != right.get(key)
    )


def _row_columns_differing(
    left: dict[str, object], right: dict[str, object], key: str
) -> tuple[str, ...]:
    """Name every differing cell as ``row<index>.<column>``.

    Attribution is per ROW, never per column. A column carrying a fresh
    identifier in one row and a pinned payload in another is volatile only in
    the first row, and aggregating the two would let the control certify the
    second -- the fail-open shape of a forbidden-list check.
    """
    cells: set[str] = set()
    lrows = left.get(key) or []
    rrows = right.get(key) or []
    assert isinstance(lrows, list) and isinstance(rrows, list)
    for index, (lrow, rrow) in enumerate(zip(lrows, rrows)):
        assert isinstance(lrow, dict) and isinstance(rrow, dict)
        for column in set(lrow) | set(rrow):
            if lrow.get(column) != rrow.get(column):
                cells.add(f"row{index}.{column}")
    if len(lrows) != len(rrows):
        cells.add("<row-count>")
    return tuple(sorted(cells))


def premise_1() -> bool:
    """Compare the two routes over one confirm-and-accept cycle.

    A same-route control runs first. Fresh identifiers feed several persisted
    digests, so a column differing between two runs of ONE route carries no
    information about the migration and must not be read as a difference the
    migration causes.
    """
    with tempfile.TemporaryDirectory() as directory:
        base = pathlib.Path(directory)
        control_a, _ = _build(str(base / "control-a.db"), route="handle")
        control_b, _ = _build(str(base / "control-b.db"), route="handle")
        left, left_calls = _build(str(base / "handle.db"), route="handle")
        right, right_calls = _build(str(base / "propose.db"), route="propose")

    volatile: set[str] = set()
    for key in _keys_differing(control_a, control_b):
        for column in _row_columns_differing(control_a, control_b, key):
            volatile.add(f"{key}:{column}")
    print(f"P1 control (handle vs handle) volatile columns: {sorted(volatile) or 'none'}")
    print(f"P1 source calls: handle={left_calls} propose={right_calls}")

    attributable: list[str] = []
    for key in _keys_differing(left, right):
        columns = _row_columns_differing(left, right, key)
        for column in columns:
            label = f"{key}:{column}"
            verdict = "VOLATILE" if label in volatile else "ATTRIBUTABLE"
            if verdict == "ATTRIBUTABLE":
                attributable.append(label)
            print(f"P1 DIFF {label} [{verdict}]")
        if not columns:
            attributable.append(key)
            print(f"P1 DIFF {key} [ATTRIBUTABLE]")

    for label in attributable:
        key = label.split(":")[0]
        print(f"   handle : {json.dumps(left.get(key), sort_keys=True)[:300]}")
        print(f"   propose: {json.dumps(right.get(key), sort_keys=True)[:300]}")

    print(f"P1 attributable differences: {attributable or 'none'}")
    return attributable


def premise_2() -> bool:
    """Ask ``resolve`` the question the demo's Act 2 asks ``handle``."""
    with tempfile.TemporaryDirectory() as directory:
        database = str(pathlib.Path(directory) / "act2.db")
        source = EchoSource()
        clock = Clock()
        system = System(database, candidate_source=source, clock_us=clock)
        # Act 1: two confirmations, compile, verify, promote the ARTIFACT.
        # The demo promotes no function set until Act 5, so none is promoted here.
        system.register_operation(
            PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0)
        )
        for _ in range(2):
            proposal_id = system.propose(PARTITION, OPERATION, {"x": 1})
            system.review(
                PARTITION, proposal_id, reviewer="alice", decision="accept"
            )
        build = system.compile(PARTITION, OPERATION)
        assert len(build.created) == 1, build
        artifact_id = build.created[0]
        report = system.verify(PARTITION, artifact_id)
        assert report.passed, report
        system.promote(
            PARTITION,
            artifact_id,
            scope_hash=report.scope_hash,
            promoted_by="release-manager",
        )

        # The route the demo ships today.
        calls_before = source.calls
        outcome = system.handle(
            PARTITION, OPERATION, {"x": 1}, request_id="act2"
        )
        handle_hit = getattr(outcome, "source", None) == "artifact"
        handle_flat = source.calls == calls_before
        print(
            f"P2 handle : status={getattr(outcome, 'status', None)!r} "
            f"source={getattr(outcome, 'source', None)!r} adapter_flat={handle_flat}"
        )

        # The route the plan line prescribes, at the identical ledger state.
        resolution = system.resolve(PARTITION, OPERATION, {"x": 1})
        failed = [
            check.key
            for check in resolution.verification.checks
            if not check.passed
        ]
        print(
            f"P2 resolve: passed={resolution.verification.passed} "
            f"match={resolution.match!r} failed_checks={failed}"
        )
        resolve_hit = (
            resolution.verification.passed
            and resolution.match is not None
            and resolution.match.matched
        )

        # Does promoting the function set at this point recover the hit?
        manifest = system.inspect_function_promotion(PARTITION, OPERATION)
        system.promote_function(
            PARTITION,
            OPERATION,
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        after = system.resolve(PARTITION, OPERATION, {"x": 1})
        after_hit = (
            after.verification.passed
            and after.match is not None
            and after.match.matched
        )
        print(
            f"P2 resolve-after-set-promotion: passed={after.verification.passed} "
            f"matched={after_hit}"
        )

    print(f"P2 handle-hits-artifact: {handle_hit}")
    print(f"P2 resolve-replaces-it-at-Act-2-state: {resolve_hit}")
    print(f"P2 resolve-replaces-it-after-set-promotion: {after_hit}")
    return handle_hit, resolve_hit, after_hit


# The findings this probe exists to establish. Naming them here is what lets the
# command FAIL: a probe that returns 0 for every possible output cannot be a gate,
# and recording its rc as green asserts a check that never ran.
EXPECTED_P1_ATTRIBUTABLE = ["events.rows:row1.payload_json"]
EXPECTED_P2 = (True, False, True)


def main() -> int:
    print("=== M3.6a1 premise probe ===")
    attributable = premise_1()
    print()
    observed = premise_2()
    print()

    failures: list[str] = []
    if attributable != EXPECTED_P1_ATTRIBUTABLE:
        failures.append(
            f"P1-DRIFT: expected {EXPECTED_P1_ATTRIBUTABLE}, measured {attributable}"
        )
    if observed != EXPECTED_P2:
        failures.append(f"P2-DRIFT: expected {EXPECTED_P2}, measured {observed}")

    # Stated positively, so the printed value is the claim rather than its negation.
    # P1 is an equivalence UNDER A PROJECTION: minted identifiers and every column
    # derived from them are dropped first, and exactly one difference survives it.
    print(
        "FINDING P1 propose-matches-handle-after-identity-projection-except: "
        f"{attributable}"
    )
    print(f"FINDING P2 handle-hits-artifact-at-Act-2-state: {observed[0]}")
    print(f"FINDING P2 resolve-matches-at-Act-2-state: {observed[1]}")
    print(f"FINDING P2 resolve-matches-after-function-set-promotion: {observed[2]}")
    for failure in failures:
        print(failure)
    print("RESULT: " + ("PASS" if not failures else "FAIL"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
