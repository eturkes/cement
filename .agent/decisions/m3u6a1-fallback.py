"""Attribute every M3.6a1 MIGRATE site by what its ``handle`` call actually claims.

The consumer census classifies a site by what the enclosing definition does with
the call's RETURN VALUE. That rule is blind to the call's SIDE EFFECTS on other
state, so it reads two distinct populations as one:

FACTORY
    The scope holds no promoted artifact for this canonical input. Supervision is
    the only reachable branch, so ``propose`` states exactly what ``handle``
    stated. Migration is a rename.

MISS-GUARDED
    EVERY execution of the site sees an artifact for this exact input that was
    once promoted, and it still declines to answer because it is now suspended or
    retired. The ``assertIsInstance(x, ReviewRequired)`` line therefore carries a
    second claim -- the stored artifact did not answer -- that ``propose`` cannot
    express. ``resolve`` can: this probe measures ``passed=True match=False`` at
    every one of those sites, which is the post-trim spelling of a verified miss.

    Both qualifiers are load-bearing. ``handle`` looks up ``status = 'promoted'``
    alone, so a ``draft`` or ``verified`` artifact is invisible to it and its
    presence proves nothing. And a claim a SITE makes must hold at every execution
    of that site: the two shared fixture helpers see a once-promoted artifact on
    15 of 1273 and 2 of 78 calls, which is incidental scope history rather than an
    assertion, so both stay FACTORY.

HIT
    ``handle`` ANSWERED from the stored artifact at least once, which is a
    ``Resolved`` outcome. The site asserts a hit, so a verified-miss assertion
    would misstate it.

AMBIGUOUS
    ``handle`` saw a once-promoted artifact and REFUSED TO CHOOSE, which is a
    ``ReconciliationRequired`` outcome. It neither answered nor supervised. This
    class exists because reading it as HIT states that the artifact answered,
    which is false, and reading it as MISS-GUARDED prescribes a verified-miss
    assertion the site never made. Both members are RETAIN, so no migration
    ruling depends on the split; the taxonomy's truth does.

ACTOR
    ``handle`` is the writer that performs the quarantine: the artifact is
    ``promoted`` before the call and ``suspended`` after it. No post-trim method
    performs a dispatch-time quarantine, so the transition the test asserts has no
    surviving producer. These sites are NOT migratable; M3.6a2 owns them.

Positive control, EVERY call, non-optional, attributed to its site: the digest
this probe computed is compared against ``requests.input_hash``, the hash the
ledger itself recorded for the request the call just created. Every outcome
carries a ``request_id``, so the control runs on ``Resolved``,
``ReconciliationRequired``, ``ReviewRequired``, ``FallbackFailed`` and
``InProgress`` alike, and each failure names the site that produced it.

An earlier revision compared the input of the PROPOSAL instead, which only
``ReviewRequired`` carries, so every answered and every ambiguous call went
uncontrolled and the one global counter could not say which site it covered. A
site-selective wrong digest on an uncontrolled call empties that site's before-state
and silently reshapes it to FACTORY with every counter clean.

The first draft of this probe derived the digest as
``_digest_strings("cement-input-v1", ...)`` instead of ``canonicalize(v).digest``
and reported a uniform FACTORY verdict over all 30 sites -- a fail-open control
reporting a clean result. A uniform verdict over a heterogeneous population is
the tell; the control is what makes the verdict checkable.

Usage:
    uv run python .agent/decisions/m3u6a1-fallback.py            # grade
    uv run python .agent/decisions/m3u6a1-fallback.py --emit     # write the JSON
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import traceback
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TABLE = HERE / "m3u6a1-fallback.json"
CENSUS = HERE / "m3u6a1-census.json"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from cement_runtime.json_value import canonicalize  # noqa: E402
from cement_runtime.system import System  # noqa: E402

_TEST_ROOTS = ("tests/", "examples/")
# `handle` looks up `status = 'promoted'` alone, so only these statuses record an
# artifact that was ever reachable by a dispatch for this input.
_ONCE_PROMOTED = frozenset({"promoted", "suspended", "retired"})
_records: list[dict[str, object]] = []
_control = {"checked": 0, "failed": 0, "errors": 0}
_real_handle = System.handle


def _call_site() -> str:
    """Name the outermost test-tree frame, which is the census's own key."""
    for frame in reversed(traceback.extract_stack()[:-2]):
        for root in _TEST_ROOTS:
            index = frame.filename.find(root)
            if index != -1:
                return f"{frame.filename[index:]}:{frame.lineno}"
    return "<unknown>"


def _statuses(rows: list[dict[str, object]], digest: str) -> dict[str, str]:
    return {
        str(row["id"]): str(row["status"])
        for row in rows
        if row["input_hash"] == digest
    }


def _spy(self, partition, operation, input_value, *, request_id=None, **kwargs):
    site = _call_site()
    digest = canonicalize(input_value).digest
    try:
        before = _statuses(self.artifacts(partition, operation), digest)
    except Exception:  # noqa: BLE001 - an unregistered operation holds no artifact
        before = {}

    resolution = "<not-called>"
    if before:
        try:
            answer = self.resolve(partition, operation, input_value)
            failed = [check.key for check in answer.verification.checks if not check.passed]
            matched = None if answer.match is None else answer.match.matched
            resolution = f"passed={answer.verification.passed} match={matched} failed={failed}"
        except Exception as exc:  # noqa: BLE001 - record, never mask
            resolution = f"{type(exc).__name__}: {exc}"

    # The record lands BEFORE the call, because many `handle` calls in this suite
    # raise deliberately and a record written afterwards is lost for every one of
    # them. An earlier draft appended last and observed 4 sites of 30.
    record: dict[str, object] = {
        "site": site,
        "before": sorted(before.values()),
        "after": [],
        "actor": False,
        "resolution": resolution,
        "outcome": "<raised>",
        "control": "<not-reached>",
    }
    _records.append(record)

    outcome = _real_handle(
        self, partition, operation, input_value, request_id=request_id, **kwargs
    )

    record["outcome"] = type(outcome).__name__
    # Every outcome carries `request_id`, so this control runs on every call
    # rather than on the supervised branch alone, and its verdict is attributed
    # to the site that produced it.
    _control["checked"] += 1
    try:
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT input_hash FROM requests WHERE partition = ? AND id = ?",
                (partition, outcome.request_id),
            ).fetchone()
        stored = None if row is None else str(row["input_hash"])
    except Exception:  # noqa: BLE001 - an unreadable request is an error, not a pass
        _control["errors"] += 1
        record["control"] = "unreadable"
    else:
        if stored is None:
            _control["errors"] += 1
            record["control"] = "unreadable"
        elif stored != digest:
            _control["failed"] += 1
            record["control"] = "failed"
        else:
            record["control"] = "ok"

    if before:
        try:
            after = _statuses(self.artifacts(partition, operation), digest)
        except Exception:  # noqa: BLE001
            after = dict(before)
        record["after"] = sorted(after.values())
        record["actor"] = before != after
    return outcome


def _shape(*, actor: bool, calls: int, promoted_hits: int, outcomes: set[str]) -> str:
    """Classify one site from its recorded evidence alone.

    A pure function of fields the table already stores, so a corrected rule can be
    replayed over a FROZEN measurement without re-measuring it. That is the only
    way to repair the opening attribution's labels without rewriting its evidence.
    """
    if actor:
        return "ACTOR"
    if not promoted_hits or not calls:
        return "FACTORY"
    if "Resolved" in outcomes:
        # `handle` ANSWERED from the artifact at least once, so this site is a HIT
        # pin, never a miss claim. Reaching MISS-GUARDED here would have prescribed
        # a verified-miss assertion for a site asserting a hit.
        return "HIT"
    if outcomes != {"ReviewRequired"}:
        # Once-promoted artifact present, no `Resolved` anywhere: `handle` REFUSED
        # TO CHOOSE. Not an answer, so not a HIT; not a declared miss either, so
        # not MISS-GUARDED.
        return "AMBIGUOUS"
    if promoted_hits == calls:
        return "MISS-GUARDED"
    return "FACTORY"


def _totals(rows: dict[str, dict[str, object]], targets: int) -> dict[str, int]:
    counts = {
        key: sum(1 for row in rows.values() if row["shape"] == shape)
        for key, shape in (
            ("actor", "ACTOR"),
            ("miss_guarded", "MISS-GUARDED"),
            ("factory", "FACTORY"),
            ("hit", "HIT"),
            ("ambiguous", "AMBIGUOUS"),
            ("unobserved", "UNOBSERVED"),
        )
    }
    return {"targets": targets, **counts}


def reclassify(table: dict[str, object]) -> int:
    """Replay the current shape rule over an existing table's own records.

    Measurements are never touched. This exists because the committed table is the
    FROZEN OPENING attribution, evidence the migration rulings were derived from -
    re-measuring it against the migrated tree would destroy it, and leaving stale
    labels would keep certifying a taxonomy correction C01 calls false.
    """
    rows = table["sites"]
    assert isinstance(rows, dict)
    changed = 0
    for row in rows.values():
        if row["shape"] == "UNOBSERVED":
            continue
        # `actor` is the per-site union `before != after`, which is how measure()
        # derived it and what the stored columns still express.
        shape = _shape(
            actor=row["before"] != row["after"],
            calls=int(row["calls"]),
            promoted_hits=int(row["promoted_hits"]),
            outcomes=set(row["outcomes"]),
        )
        if shape != row["shape"]:
            row["shape"] = shape
            changed += 1
    totals = table["totals"]
    assert isinstance(totals, dict)
    table["totals"] = _totals(rows, int(totals["targets"]))
    return changed


class _Result(unittest.TextTestResult):
    pass


def measure() -> dict[str, object]:
    census = json.loads(CENSUS.read_text())
    # Every test-tree consumer is a target, whatever its ruled verdict. Scoping
    # this to MIGRATE alone would erase the ACTOR rows from the table the moment
    # their ruling lands, taking the ruling's own evidence with it.
    consumers = [
        entry
        for entry in census["definitions"]
        if entry["path"].startswith("tests/")
    ]
    targets = {f"{entry['path']}:{line}" for entry in consumers for line in entry["lines"]}
    modules = sorted({entry["path"] for entry in consumers})

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for path in modules:
        module = __import__(f"tests.{path[len('tests/') : -3]}", fromlist=["*"])
        suite.addTests(loader.loadTestsFromModule(module))

    _records.clear()
    _control.update(checked=0, failed=0, errors=0)
    with mock.patch.object(System, "handle", _spy):
        with open("/dev/null", "w", encoding="utf-8") as sink:
            unittest.TextTestRunner(verbosity=0, resultclass=_Result, stream=sink).run(suite)

    sites: dict[str, dict[str, object]] = {}
    for record in _records:
        site = str(record["site"])
        if site not in targets:
            continue
        current = sites.setdefault(
            site,
            {
                "calls": 0,
                "hits": 0,
                "promoted_hits": 0,
                "before": set(),
                "after": set(),
                "resolutions": set(),
                "outcomes": set(),
                "actor": False,
                "control_checked": 0,
                "control_bad": 0,
                "returned": 0,
            },
        )
        current["calls"] = int(current["calls"]) + 1  # type: ignore[call-overload]
        current["outcomes"].add(record["outcome"])  # type: ignore[union-attr]
        if record["outcome"] != "<raised>":
            current["returned"] = int(current["returned"]) + 1  # type: ignore[call-overload]
        if record["control"] != "<not-reached>":
            current["control_checked"] = int(current["control_checked"]) + 1  # type: ignore[call-overload]
            if record["control"] != "ok":
                current["control_bad"] = int(current["control_bad"]) + 1  # type: ignore[call-overload]
        if record["before"]:
            current["hits"] = int(current["hits"]) + 1  # type: ignore[call-overload]
            current["before"].update(record["before"])  # type: ignore[union-attr]
            current["after"].update(record["after"])  # type: ignore[union-attr]
            current["resolutions"].add(record["resolution"])  # type: ignore[union-attr]
            if _ONCE_PROMOTED.intersection(record["before"]):  # type: ignore[arg-type]
                current["promoted_hits"] = int(current["promoted_hits"]) + 1  # type: ignore[call-overload]
            if record["actor"]:
                current["actor"] = True

    table: dict[str, object] = {"kind": "m3u6a1-fallback-attribution", "sites": {}}
    rows = table["sites"]
    assert isinstance(rows, dict)
    for site in sorted(targets):
        current = sites.get(site)
        if current is None:
            rows[site] = {"shape": "UNOBSERVED"}
            continue
        shape = _shape(
            actor=bool(current["actor"]),
            calls=int(current["calls"]),  # type: ignore[call-overload]
            promoted_hits=int(current["promoted_hits"]),  # type: ignore[call-overload]
            outcomes=set(current["outcomes"]),  # type: ignore[arg-type]
        )
        rows[site] = {
            "shape": shape,
            "calls": current["calls"],
            "hits": current["hits"],
            "promoted_hits": current["promoted_hits"],
            "control_checked": current["control_checked"],
            "control_bad": current["control_bad"],
            "returned": current["returned"],
            "outcomes": sorted(current["outcomes"]),  # type: ignore[arg-type]
            "before": sorted(current["before"]),  # type: ignore[arg-type]
            "after": sorted(current["after"]),  # type: ignore[arg-type]
            "resolutions": sorted(current["resolutions"]),  # type: ignore[arg-type]
        }
    table["migrate_sites"] = sorted(
        f"{entry['path']}:{line}"
        for entry in consumers
        if entry["verdict"] == "MIGRATE"
        for line in entry["lines"]
    )
    table["control"] = dict(_control)
    table["totals"] = _totals(rows, len(targets))
    return table


def grade(table: dict[str, object]) -> int:
    migrate_sites = set(table["migrate_sites"])  # type: ignore[arg-type]
    rows = table["sites"]
    totals = table["totals"]
    control = table["control"]
    assert isinstance(rows, dict) and isinstance(totals, dict) and isinstance(control, dict)

    failures: list[str] = []
    if control["checked"] == 0:
        failures.append("CONTROL-NEVER-RAN: no proposal digest was compared")
    if control["failed"]:
        failures.append(f"CONTROL-FAILED: {control['failed']} digests disagree with the ledger")
    if control["errors"]:
        failures.append(f"CONTROL-UNREADABLE: {control['errors']} requests could not be read")
    # The global counters above say a control failed; these say WHERE, which is
    # the half a site-selective corruption relies on being missing. A call that
    # RAISED returns no outcome and therefore no request id, so it is
    # uncontrollable by construction; every call that returned must be covered.
    uncontrolled = sorted(
        f"{site}({row['control_checked']}/{row['returned']})"
        for site, row in rows.items()
        if row.get("returned") and row["control_checked"] != row["returned"]
    )
    if uncontrolled:
        failures.append(f"CONTROL-UNATTRIBUTED: {uncontrolled}")
    bad = sorted(
        f"{site}({row['control_bad']}/{row['control_checked']})"
        for site, row in rows.items()
        if row.get("control_bad")
    )
    if bad:
        failures.append(f"CONTROL-SITE-FAILED: {bad}")
    unmigratable = sorted(
        site for site, row in rows.items()
        if row["shape"] == "UNOBSERVED" and site in migrate_sites
    )
    if unmigratable:
        failures.append(f"UNOBSERVED-MIGRATE: {unmigratable}")
    # A uniform verdict over this population is the fail-open shape this probe
    # exists to defeat, so it fails rather than reporting clean.
    if totals["factory"] == 0 or totals["factory"] + totals["unobserved"] == totals["targets"]:
        failures.append("UNIFORM: every site reports one shape; the derivation is suspect")

    for site, row in sorted(rows.items()):
        if row["shape"] == "MISS-GUARDED":
            for resolution in row.get("resolutions", []):
                if not resolution.startswith("passed=True match=False"):
                    failures.append(f"NO-MISS-SPELLING {site}: {resolution}")

    raise_only = sum(
        1 for row in rows.values() if row["shape"] != "UNOBSERVED" and not row.get("returned")
    )
    print(
        f"CONTROL-DIGESTS: {control['checked']} checked, "
        f"{control['failed']} failed, {control['errors']} unreadable, "
        f"{raise_only} sites raise on every call and carry no request id"
    )
    for key in ("targets", "actor", "miss_guarded", "hit", "ambiguous", "factory", "unobserved"):
        print(f"{key.upper().replace('_', '-')}: {totals[key]}")
    for site, row in sorted(rows.items()):
        if row["shape"] == "FACTORY":
            continue
        print(
            f"  {row['shape']:12} {site} "
            f"before={row.get('before', [])} after={row.get('after', [])}"
        )
        for resolution in row.get("resolutions", []):
            print(f"{'':15}resolve -> {resolution}")
    for failure in failures:
        print(failure)
    print("RESULT: " + ("PASS" if not failures else "FAIL"))
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", action="store_true")
    parser.add_argument(
        "--reclassify",
        action="store_true",
        help="replay the shape rule over the committed table's own records",
    )
    args = parser.parse_args(argv)

    if args.reclassify:
        table = json.loads(TABLE.read_text())
        changed = reclassify(table)
        TABLE.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
        print(f"RECLASSIFIED: {changed} sites relabelled")
        print(f"TOTALS: {table['totals']}")
        return 0

    table = measure()
    if args.emit:
        TABLE.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
        print(f"wrote {TABLE.name}")
    return grade(table)


if __name__ == "__main__":
    sys.exit(main())
