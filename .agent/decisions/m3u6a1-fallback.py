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

ACTOR
    ``handle`` is the writer that performs the quarantine: the artifact is
    ``promoted`` before the call and ``suspended`` after it. No post-trim method
    performs a dispatch-time quarantine, so the transition the test asserts has no
    surviving producer. These sites are NOT migratable; M3.6a2 owns them.

Positive control, per call, non-optional: the computed input digest is compared
against the digest the ledger itself stored for the proposal the call just
created. The first draft of this probe derived the digest as
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
from cement_runtime.system import ReviewRequired, System  # noqa: E402

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
    }
    _records.append(record)

    outcome = _real_handle(
        self, partition, operation, input_value, request_id=request_id, **kwargs
    )

    record["outcome"] = type(outcome).__name__
    if isinstance(outcome, ReviewRequired):
        _control["checked"] += 1
        try:
            view = self.get_proposal(partition, outcome.proposal_id)
            stored = canonicalize(view.input).digest
        except Exception:  # noqa: BLE001 - an unreadable proposal is an error, not a pass
            _control["errors"] += 1
        else:
            if stored != digest:
                _control["failed"] += 1

    if before:
        try:
            after = _statuses(self.artifacts(partition, operation), digest)
        except Exception:  # noqa: BLE001
            after = dict(before)
        record["after"] = sorted(after.values())
        record["actor"] = before != after
    return outcome


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
            },
        )
        current["calls"] = int(current["calls"]) + 1  # type: ignore[call-overload]
        current["outcomes"].add(record["outcome"])  # type: ignore[union-attr]
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
        supervised = current["outcomes"] == {"ReviewRequired"}
        if current["actor"]:
            shape = "ACTOR"
        elif not current["promoted_hits"] or not current["calls"]:
            shape = "FACTORY"
        elif not supervised:
            # `handle` answered from the artifact at least once, so this site is a
            # HIT pin, never a miss claim. Reaching MISS-GUARDED here would have
            # prescribed a verified-miss assertion for a site asserting a hit.
            shape = "HIT"
        elif current["promoted_hits"] == current["calls"]:
            shape = "MISS-GUARDED"
        else:
            shape = "FACTORY"
        rows[site] = {
            "shape": shape,
            "calls": current["calls"],
            "hits": current["hits"],
            "promoted_hits": current["promoted_hits"],
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
    table["totals"] = {
        "targets": len(targets),
        "actor": sum(1 for row in rows.values() if row["shape"] == "ACTOR"),
        "miss_guarded": sum(1 for row in rows.values() if row["shape"] == "MISS-GUARDED"),
        "factory": sum(1 for row in rows.values() if row["shape"] == "FACTORY"),
        "hit": sum(1 for row in rows.values() if row["shape"] == "HIT"),
        "unobserved": sum(1 for row in rows.values() if row["shape"] == "UNOBSERVED"),
    }
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
        failures.append(f"CONTROL-UNREADABLE: {control['errors']} proposals could not be read")
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

    print(
        f"CONTROL-DIGESTS: {control['checked']} checked, "
        f"{control['failed']} failed, {control['errors']} unreadable"
    )
    for key in ("targets", "actor", "miss_guarded", "hit", "factory", "unobserved"):
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
    args = parser.parse_args(argv)

    table = measure()
    if args.emit:
        TABLE.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
        print(f"wrote {TABLE.name}")
    return grade(table)


if __name__ == "__main__":
    sys.exit(main())
