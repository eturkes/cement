#!/usr/bin/env python3
"""MAIN's end-to-end smoke probe for M3.3, run against a real ledger.

Usage: uv run python .agent/decisions/m3u3-smoke.py

Audits the acceptance contract, not only the code: every check names the
obligation it exercises, so a check that cannot be written is a contract defect.
Exit 0 = every check passed. Exit 1 = at least one FAIL, listed at the end.

This probe is tracked, so a durable claim may cite it and any clone reruns it.
It is not the unit's battery; the battery is diff-blind and graded separately.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cement_runtime import (  # noqa: E402
    Candidate,
    CandidateSourceError,
    CompilePolicy,
    NotFoundError,
    StateError,
    System,
    ValidationError,
)

RESULTS: list[tuple[str, str, str]] = []

# D01's footprint is derived from the LIVE declared schema, never named: nine
# named tables left four unmeasured, so an extra write to `schema_metadata`,
# `artifact_evidence`, `artifact_tests` or `test_reports` passed every count.
# One explicit exclusion rule - SQLite owns the `sqlite_` prefix, and
# `events.sequence` is AUTOINCREMENT so `sqlite_sequence` legitimately moves.
SQLITE_OWNED = "sqlite_"
DECLARED_APPLICATION_TABLES = 13


def check(obligation: str, name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(("PASS" if ok else "FAIL", f"{obligation} {name}", detail))


class Recorder:
    """Candidate source that records every invocation."""

    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls: list[object] = []

    def propose(self, request):
        self.calls.append(request)
        return self.behaviour(request)


def counts(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        tables = [
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
            )
            if not name.startswith(SQLITE_OWNED)
        ]
        if len(tables) != DECLARED_APPLICATION_TABLES:
            raise SystemExit(f"schema derivation found {len(tables)} application tables")
        return {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in tables
        }


def snapshot(path: Path) -> tuple[str, str]:
    with sqlite3.connect(path) as connection:
        dump = "\n".join(connection.iterdump())
    return hashlib.sha256(path.read_bytes()).hexdigest(), dump


def build(directory: Path, source=None) -> tuple[System, Path]:
    ledger = directory / "ledger.db"
    system = System(str(ledger), candidate_source=source)
    system.register_operation("tenant_a", "echo_1", policy=CompilePolicy(2, 1, 0))
    return system, ledger


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        good = Candidate(output={"v": 10}, provenance={"model": "probe"})

        # --- DIRECT path -------------------------------------------------
        system, ledger = build(_mk(directory, "d1"))
        before = counts(ledger)
        proposal_id = system.submit_proposal("tenant_a", "echo_1", {"k": 1}, candidate=good)
        after = counts(ledger)
        delta = {t: after[t] - before[t] for t in after if after[t] != before[t]}
        check("D01", "direct footprint is one request, one proposal, one event",
              delta == {"requests": 1, "proposals": 1, "events": 1}, str(delta))
        check("P02", "submit_proposal returns a bare str proposal id",
              type(proposal_id) is str and proposal_id.startswith("prop_"), proposal_id)

        with sqlite3.connect(ledger) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM requests").fetchone()
            event = connection.execute(
                "SELECT * FROM events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        check("D02", "request row is pending with proposal_id and no lease",
              row["status"] == "pending" and row["proposal_id"] == proposal_id
              and row["lease_owner"] is None and row["lease_until_us"] is None
              and row["attempts"] == 1,
              f"{row['status']} lease={row['lease_owner']} attempts={row['attempts']}")
        check("D03", "event is proposal.created on the proposal subject",
              event["kind"] == "proposal.created" and event["subject_type"] == "proposal"
              and event["subject_id"] == proposal_id, event["kind"])
        check("D22", "event payload publishes no request identifier",
              row["id"] not in event["payload_json"], event["payload_json"])

        # --- D04 no idempotency -------------------------------------------
        second = system.submit_proposal("tenant_a", "echo_1", {"k": 1}, candidate=good)
        again = counts(ledger)
        check("D04", "identical content submitted twice writes two of everything",
              second != proposal_id and again["requests"] - after["requests"] == 1
              and again["proposals"] - after["proposals"] == 1,
              f"{proposal_id} vs {second}")

        # --- P03 direct never invokes a configured source -------------------
        exploding = Recorder(lambda request: (_ for _ in ()).throw(RuntimeError("boom")))
        system2, ledger2 = build(_mk(directory, "d2"), source=exploding)
        third = system2.submit_proposal("tenant_a", "echo_1", {"k": 2}, candidate=good)
        check("P03", "submit_proposal never invokes a configured raising source",
              exploding.calls == [] and third.startswith("prop_"), str(len(exploding.calls)))

        # --- SOURCE path ----------------------------------------------------
        working = Recorder(lambda request: good)
        system3, ledger3 = build(_mk(directory, "d3"), source=working)
        before3 = counts(ledger3)
        source_id = system3.propose("tenant_a", "echo_1", {"k": 3})
        after3 = counts(ledger3)
        delta3 = {t: after3[t] - before3[t] for t in after3 if after3[t] != before3[t]}
        check("D01", "source footprint matches the direct footprint",
              delta3 == {"requests": 1, "proposals": 1, "events": 1}, str(delta3))
        check("D05", "propose invokes the source exactly once",
              len(working.calls) == 1, str(len(working.calls)))
        check("D14", "the source receives the generated internal request id",
              working.calls[0].request_id.startswith("req_")
              and working.calls[0].operation_revision == 1,
              working.calls[0].request_id)

        # --- D11 source runs outside every transaction ----------------------
        # Structural pin: every connection Cement opens is tracked, and the
        # source observes all of them. A closed connection cannot be in a
        # transaction, so ProgrammingError reads as False.
        system4, ledger4 = build(_mk(directory, "d4"))
        opened: list[sqlite3.Connection] = []
        real_connect = system4.store._connect

        def tracking(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        def in_txn(connection: sqlite3.Connection) -> bool:
            try:
                return connection.in_transaction
            except sqlite3.ProgrammingError:
                return False

        system4.store._connect = tracking
        during: list[bool] = []

        def watcher(request):
            during.append(any(in_txn(connection) for connection in opened))
            return good

        system4.candidate_source = Recorder(watcher)
        system4.propose("tenant_a", "echo_1", {"k": 4})
        check("D11", "no Cement connection is in a transaction while the source runs",
              during == [False] and len(opened) >= 2,
              f"{during} over {len(opened)} tracked connections")
        with system4.store.transaction(write=True):
            control = any(in_txn(connection) for connection in opened)
        check("D11", "positive control: the same spy sees an open transaction",
              control is True, str(control))

        # --- section 7 error texts ------------------------------------------
        for label, behaviour, expected in (
            ("declared", lambda r: (_ for _ in ()).throw(CandidateSourceError("inner secret")), "candidate source failed"),
            ("arbitrary", lambda r: (_ for _ in ()).throw(RuntimeError("SECRET-42")), "candidate source failed"),
            ("bad-candidate", lambda r: Candidate(output=object(), provenance={}), "candidate source failed"),
        ):
            recorder = Recorder(behaviour)
            system5, ledger5 = build(_mk(directory, f"e-{label}"), source=recorder)
            base_counts, (base_sha, base_dump) = counts(ledger5), snapshot(ledger5)
            try:
                system5.propose("tenant_a", "echo_1", {"k": 5})
                raised: BaseException | None = None
            except BaseException as exc:  # noqa: BLE001
                raised = exc
            check("T01/T02", f"{label} source failure raises the exact public text",
                  type(raised) is CandidateSourceError and str(raised) == expected,
                  f"{type(raised).__name__}: {raised}")
            check("D18", f"{label} failure leaks no cause, context, or secret",
                  raised is not None and raised.__cause__ is None
                  and raised.__context__ is None and "SECRET-42" not in repr(raised),
                  f"cause={raised.__cause__!r} context={raised.__context__!r}")
            after_counts, (after_sha, after_dump) = counts(ledger5), snapshot(ledger5)
            check("D15", f"{label} failure leaves the ledger byte-identical",
                  base_counts == after_counts and base_sha == after_sha
                  and base_dump == after_dump,
                  f"sha {base_sha[:12]} -> {after_sha[:12]}")
            check("D20", f"{label} failure writes no failed row and no event",
                  after_counts["requests"] == 0 and after_counts["events"] == 1,
                  str(after_counts["events"]))

        # --- StateError / NotFoundError --------------------------------------
        system6, ledger6 = build(_mk(directory, "s1"))
        try:
            system6.propose("tenant_a", "echo_1", {"k": 6})
            unconfigured: BaseException | None = None
        except BaseException as exc:  # noqa: BLE001
            unconfigured = exc
        check("T03", "propose with no configured source raises the exact text",
              type(unconfigured) is StateError
              and str(unconfigured) == "candidate source is not configured",
              f"{type(unconfigured).__name__}: {unconfigured}")

        counting = Recorder(lambda request: good)
        system7, ledger7 = build(_mk(directory, "s2"), source=counting)
        try:
            system7.propose("tenant_a", "absent_1", {"k": 7})
            missing: BaseException | None = None
        except BaseException as exc:  # noqa: BLE001
            missing = exc
        check("T05", "an unregistered operation raises the exact NotFoundError text",
              type(missing) is NotFoundError
              and str(missing) == "operation is not registered in this partition",
              f"{type(missing).__name__}: {missing}")
        check("D21", "the source never ran for an unregistered operation",
              counting.calls == [], str(len(counting.calls)))

        # --- D12 revision changes during generation ---------------------------
        system8, ledger8 = build(_mk(directory, "r1"))
        reviser = Recorder(
            lambda request: (
                system8.revise_operation("tenant_a", "echo_1",
                                         policy=CompilePolicy(3, 1, 0), revised_by="probe"),
                good,
            )[1]
        )
        system8.candidate_source = reviser
        before8 = counts(ledger8)
        try:
            system8.propose("tenant_a", "echo_1", {"k": 8})
            stale: BaseException | None = None
        except BaseException as exc:  # noqa: BLE001
            stale = exc
        after8 = counts(ledger8)
        check("T04", "a revision change during generation raises the exact text",
              type(stale) is StateError
              and str(stale) == "operation revision changed before proposal submission",
              f"{type(stale).__name__}: {stale}")
        check("D12", "the stale-revision path writes no request and no proposal",
              after8["requests"] == before8["requests"]
              and after8["proposals"] == before8["proposals"],
              f"{before8['requests']}->{after8['requests']}")

        # --- section 4 precedence ---------------------------------------------
        system9, ledger9 = build(_mk(directory, "v1"), source=Recorder(lambda r: good))
        cases = (
            ("D08", "bad partition beats bad input", lambda: system9.submit_proposal(
                "bad partition!", "echo_1", object(), candidate=good), "partition must"),
            ("D07", "bad operation beats bad input", lambda: system9.submit_proposal(
                "tenant_a", "bad op!", object(), candidate=good), "operation must"),
            ("D07", "bad input beats bad candidate", lambda: system9.submit_proposal(
                "tenant_a", "echo_1", object(), candidate="not a candidate"), "JSON"),
            ("D07", "bad partition beats an absent operation", lambda: system9.propose(
                "bad partition!", "absent_1", {"k": 9}), "partition must"),
        )
        for obligation, name, call, fragment in cases:
            try:
                call()
                error: BaseException | None = None
            except BaseException as exc:  # noqa: BLE001
                error = exc
            check(obligation, name,
                  isinstance(error, ValidationError) and fragment in str(error),
                  f"{type(error).__name__}: {error}")

        # --- D09 a rejected call touches nothing --------------------------------
        rejecting = Recorder(lambda request: good)
        system10, ledger10 = build(_mk(directory, "v2"), source=rejecting)
        base10, (sha10, dump10) = counts(ledger10), snapshot(ledger10)
        for call in (
            lambda: system10.submit_proposal("bad!", "echo_1", {"k": 1}, candidate=good),
            lambda: system10.propose("bad!", "echo_1", {"k": 1}),
            lambda: system10.submit_proposal("tenant_a", "echo_1", object(), candidate=good),
        ):
            try:
                call()
            except ValidationError:
                pass
        after10, (sha10b, dump10b) = counts(ledger10), snapshot(ledger10)
        check("D09", "rejected calls invoke no source and change no byte",
              rejecting.calls == [] and base10 == after10 and sha10 == sha10b
              and dump10 == dump10b, str(len(rejecting.calls)))

        # --- D10 the signature is the check --------------------------------------
        for name, call in (
            ("omitted candidate", lambda: system10.submit_proposal("tenant_a", "echo_1", {})),
            ("source= on submit_proposal", lambda: system10.submit_proposal(
                "tenant_a", "echo_1", {}, candidate=good, source=object())),
            ("source= on propose", lambda: system10.propose(
                "tenant_a", "echo_1", {}, source=object())),
        ):
            try:
                call()
                error = None
            except BaseException as exc:  # noqa: BLE001
                error = exc
            check("D10", f"{name} raises Python's own TypeError",
                  type(error) is TypeError, f"{type(error).__name__}: {error}")

        # --- D23 the submitted proposal stays reachable ---------------------------
        view = system.get_proposal("tenant_a", proposal_id)
        check("D23", "the returned proposal id reaches get_proposal",
              view.id == proposal_id, view.id)
        listed = system.proposals("tenant_a", status="pending")
        check("D06", "both paths write rows the existing readers project",
              any(entry["id"] == proposal_id for entry in listed), str(len(listed)))

        # --- P06 handle still works unchanged --------------------------------------
        # P06 freezes handle's BYTES; this check measures only its outcome class, so
        # the name states that. The byte pin lives in the battery's own P06 test.
        system11, ledger11 = build(_mk(directory, "h1"), source=Recorder(lambda r: good))
        outcome = system11.handle("tenant_a", "echo_1", {"k": 11})
        check("P06", "handle still returns ReviewRequired",
              type(outcome).__name__ == "ReviewRequired", type(outcome).__name__)

    failures = [row for row in RESULTS if row[0] == "FAIL"]
    for status, name, detail in RESULTS:
        print(f"{status} {name}" + (f"  [{detail}]" if status == "FAIL" else ""))
    print(f"\nCHECKS: {len(RESULTS)}  PASS: {len(RESULTS) - len(failures)}  FAIL: {len(failures)}")
    return 1 if failures else 0


def _mk(directory: Path, name: str) -> Path:
    path = directory / name
    path.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    raise SystemExit(main())
