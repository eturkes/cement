"""Record MAIN's rulings over the M3.6a1 consumer census, idempotently.

The census classifies each definition mechanically, from what it does with the
lifecycle call's return value. That rule is a first pass: it reads consumption,
never intent, so three definitions need MAIN's ruling with its grounds. This
script regenerates the census, re-applies every ruling, and asserts the ruled id
set matches the table exactly, so a later row addition fails loudly rather than
going unruled.

    uv run python .agent/decisions/m3u6a1-rule-census.py           # write
    uv run python .agent/decisions/m3u6a1-rule-census.py --check   # in-sync gate
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TABLE = HERE / "m3u6a1-census.json"

_spec = importlib.util.spec_from_file_location("m3u6a1_census", HERE / "m3u6a1-census.py")
assert _spec and _spec.loader
census = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(census)

# site -> (verdict, grounds). Every entry overrides the mechanical verdict, so
# each one states why the measurement is not the ruling.
RULINGS: dict[str, tuple[str, str]] = {
    "examples/hospital_ocr/run_demo.py::main": (
        "MIGRATE-RESOLVE",
        "Owner ruling: the walkthrough promotes its function set right after each "
        "artifact promotion, so Acts 2 and 3 answer through `resolve`. Five sites "
        "re-base onto `propose`; the two `Resolved(source=\"artifact\")` sites "
        "re-base onto `resolve`. Measured RETAIN because the mechanical rule reads "
        "`.source`/`.output` consumption and cannot name a second migration target. "
        "`m3u6a1-premise.py` P2 measures that `resolve` fails on check "
        "`persisted-function-receipt` at the Act-2 ledger state and matches once the "
        "set is promoted, which is why the checkpoint moves rather than the assertion.",
    ),
    "tests/test_submission.py::test_handle_still_answers_on_a_system_that_submitted_directly": (
        "RETAIN",
        "The method under test IS `handle`: the test asserts that a system which "
        "submitted directly still answers the lifecycle route. Migrating it would "
        "delete its own subject. Measured MIGRATE because the result is consumed "
        "only as a `ReviewRequired` type check, which the rule reads as a fixture "
        "route. M3.6a2 deletes this test with the method.",
    ),
    "tests/test_proposal_binding_battery.py::test_b30_the_six_owned_event_payloads_are_2": (
        "RETAIN",
        "Pins the handle-route `proposal.created` payload as `{\"request_id\": ...}` "
        "unchanged. `m3u6a1-premise.py` P1 measures that payload as the migration's "
        "SOLE attributable row difference -- `propose` writes `{}` -- so migrating "
        "this test would silently retire the pin that records the difference. "
        "Measured MIGRATE because `typing.cast(ReviewRequired, outcome).proposal_id` "
        "reads as a safe consumption. M3.6a2 deletes it with the route.",
    ),
}


def build() -> dict[str, object]:
    previous = json.loads(TABLE.read_text()) if TABLE.exists() else None
    table = census.emit(ROOT, previous)
    sites = {str(entry["site"]) for entry in table["definitions"]}  # type: ignore[union-attr]
    unknown = sorted(set(RULINGS) - sites)
    if unknown:
        raise SystemExit(f"ruling names a site the census does not hold: {unknown}")

    for entry in table["definitions"]:  # type: ignore[union-attr]
        site = str(entry["site"])
        if site in RULINGS:
            verdict, grounds = RULINGS[site]
            entry["verdict"] = verdict
            entry["grounds"] = grounds
        else:
            entry["verdict"] = entry["measured"]
            entry.pop("grounds", None)

    overridden = {
        str(e["site"])
        for e in table["definitions"]  # type: ignore[union-attr]
        if e["verdict"] != e["measured"]
    }
    if overridden != set(RULINGS):
        raise SystemExit(
            f"override set drifted: {sorted(overridden ^ set(RULINGS))}"
        )

    # Totals are recomputed HERE, after the rulings land. Emitting them from the
    # mechanical verdicts would report the pre-ruling census and make the write
    # non-idempotent, because the next run reads the ruled verdicts back.
    definitions = table["definitions"]
    assert isinstance(definitions, list)
    table["totals"] = {
        "definitions": len(definitions),
        "measured_migrate": sum(1 for e in definitions if e["measured"] == "MIGRATE"),
        "measured_retain": sum(1 for e in definitions if e["measured"] == "RETAIN"),
        "ruled_migrate": sum(1 for e in definitions if e["verdict"] == "MIGRATE"),
        "ruled_migrate_resolve": sum(
            1 for e in definitions if e["verdict"] == "MIGRATE-RESOLVE"
        ),
        "ruled_retain": sum(1 for e in definitions if e["verdict"] == "RETAIN"),
        "overrides": len(overridden),
        "sites": sum(int(e["sites"]) for e in definitions),
    }
    return table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    table = build()
    text = json.dumps(table, indent=2, sort_keys=True) + "\n"
    if args.check:
        current = TABLE.read_text() if TABLE.exists() else ""
        if current != text:
            print("OUT-OF-SYNC: regenerate with m3u6a1-rule-census.py")
            return 1
        print("IN-SYNC")
        return 0
    TABLE.write_text(text)
    totals = table["totals"]
    assert isinstance(totals, dict)
    print(f"wrote {TABLE.name}: {json.dumps(totals, sort_keys=True)}")
    print(f"rulings applied: {len(RULINGS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
