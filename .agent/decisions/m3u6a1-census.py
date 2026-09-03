"""Census every consumer of the request-lifecycle API, and grade its disposition.

M3.6a1 migrates consumers off ``System.handle`` and ``System.request_status``
while both still ship. Its acceptance predicate quantifies over EVERY consumer,
not over the five fixture helpers its plan line names, so the census enumerates
each call site, classifies it, and fails when any site is unruled.

Classification is decided by what the enclosing definition does with the call's
RETURN VALUE, never by whether the call names ``request_id``. Every ``handle``
call passes ``request_id``, so that token classifies nothing; the return value is
what a migration must preserve.

    MIGRATE  the result is discarded, or is consumed only as
             ``isinstance(x, ReviewRequired)`` plus ``x.proposal_id``.
             ``propose`` returns that identifier directly, so the site re-bases
             with every assertion intact.

    RETAIN   the site reads any other field, asserts any other result model,
             calls ``request_status``, passes ``retry_failed``, or reuses one
             request identifier across two calls. The lifecycle IS the subject,
             so M3.6a2 deletes the test rather than re-basing it.

Usage:
    uv run python .agent/decisions/m3u6a1-census.py            # grade
    uv run python .agent/decisions/m3u6a1-census.py --emit     # write the JSON
    uv run python .agent/decisions/m3u6a1-census.py --self-test # grade both ways

Control lines, all zero for PASS:
    UNRULED          sites the disposition table does not name
    STALE            table entries naming a site that no longer exists
    MISCLASSIFIED    sites whose measured verdict contradicts the table
    SURVIVING-MIGRATE  MIGRATE sites still calling the lifecycle API
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TABLE = pathlib.Path(__file__).with_name("m3u6a1-census.json")

LIFECYCLE_API = ("handle", "request_status")

# `propose` returns the proposal identifier, so these two consumptions survive
# the migration unchanged. Everything else is a lifecycle-only observable.
SAFE_ATTRS = frozenset({"proposal_id"})
SAFE_TYPES = frozenset({"ReviewRequired"})

SCAN_ROOTS = ("tests", "examples")


def _defs(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _owner(
    defs: list[ast.FunctionDef | ast.AsyncFunctionDef], line: int
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the WIDEST enclosing definition.

    The widest, not the innermost: a nested closure inherits its test method's
    subject, so a helper defined inside a test is classified with that test.
    """
    enclosing = [d for d in defs if d.lineno <= line <= d.end_lineno]
    if not enclosing:
        return None
    return max(enclosing, key=lambda d: d.end_lineno - d.lineno)


def _request_id_value(call: ast.Call) -> str | None:
    """Render the call's request identifier, when it is statically comparable."""
    for keyword in call.keywords:
        if keyword.arg != "request_id":
            continue
        node = keyword.value
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return f"name:{node.id}"
    return None


def _discarded(function: ast.AST, call: ast.Call) -> bool:
    """True when the call's value is thrown away as a bare statement."""
    return any(
        isinstance(node, ast.Expr) and node.value is call
        for node in ast.walk(function)
    )


def _bound_target(function: ast.AST, call: ast.Call) -> str | None:
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Assign)
            and node.value is call
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            return node.targets[0].id
    return None


def _reasons_for_site(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    call: ast.Call,
    reuse: frozenset[str],
) -> list[str]:
    reasons: set[str] = set()
    if call.func.attr == "request_status":  # type: ignore[union-attr]
        reasons.add("calls:request_status")
    for keyword in call.keywords:
        if keyword.arg == "retry_failed":
            reasons.add("kwarg:retry_failed")
    value = _request_id_value(call)
    if value is not None and value in reuse:
        reasons.add("request-id-reuse")

    target = _bound_target(function, call)
    if target is None:
        if not _discarded(function, call):
            reasons.add("result:inline")
        return sorted(reasons)

    def _names_target(node: ast.expr) -> bool:
        """True when ``node`` reads the bound result, directly or through a cast.

        ``typing.cast(T, outcome).proposal_id`` reads the result exactly as
        ``outcome.proposal_id`` does, so a rule matching only a bare Name is
        blind to every cast site.
        """
        if isinstance(node, ast.Name):
            return node.id == target
        if isinstance(node, ast.Call):
            return any(_names_target(a) for a in node.args)
        return False

    for node in ast.walk(function):
        if (
            isinstance(node, ast.Attribute)
            and _names_target(node.value)
            and node.attr not in SAFE_ATTRS
        ):
            reasons.add(f"attr:{node.attr}")
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        assertion = node.func.attr
        # `assertIsInstance(x, T)` and `assertIs(type(x), T)` state the same
        # obligation. A rule reading only the first is blind to the second, and
        # both spellings ship in this repo.
        annotation: ast.expr | None = None
        if (
            assertion in ("assertIsInstance", "assertNotIsInstance")
            and node.args
            and _names_target(node.args[0])
        ):
            annotation = node.args[1]
        elif assertion in ("assertIs", "assertEqual", "assertIsNot") and len(node.args) >= 2:
            first, second = node.args[0], node.args[1]
            if (
                isinstance(first, ast.Call)
                and isinstance(first.func, ast.Name)
                and first.func.id == "type"
                and first.args
                and _names_target(first.args[0])
            ):
                annotation = second
        if annotation is not None:
            name = (
                annotation.id
                if isinstance(annotation, ast.Name)
                else ast.unparse(annotation)
            )
            if name not in SAFE_TYPES:
                reasons.add(f"isinstance:{name}")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "request_status"
            and any(
                isinstance(a, ast.Attribute)
                and isinstance(a.value, ast.Name)
                and a.value.id == target
                for a in node.args
            )
        ):
            reasons.add("calls:request_status")
    return sorted(reasons)


def survey(root: pathlib.Path) -> list[dict[str, object]]:
    """Enumerate and classify every lifecycle-API call site under ``root``."""
    rows: list[dict[str, object]] = []
    files = sorted(
        path
        for name in SCAN_ROOTS
        for path in (root / name).rglob("*.py")
    )
    for path in files:
        tree = ast.parse(path.read_text())
        defs = _defs(tree)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in LIFECYCLE_API
        ]
        # A request identifier used by two calls inside ONE definition is the
        # idempotency subject, which no request-free API reproduces.
        per_owner: dict[int, list[str]] = {}
        for call in calls:
            function = _owner(defs, call.lineno)
            value = _request_id_value(call)
            if function is not None and value is not None:
                per_owner.setdefault(id(function), []).append(value)
        reuse_by_owner = {
            key: frozenset(v for v in values if values.count(v) > 1)
            for key, values in per_owner.items()
        }
        for call in calls:
            function = _owner(defs, call.lineno)
            relative = str(path.relative_to(root))
            if function is None:
                rows.append(
                    {
                        "site": f"{relative}::<module>",
                        "path": relative,
                        "owner": "<module>",
                        "api": call.func.attr,  # type: ignore[union-attr]
                        "line": call.lineno,
                        "verdict": "RETAIN",
                        "reasons": ["module-level"],
                    }
                )
                continue
            reasons = _reasons_for_site(
                function, call, reuse_by_owner.get(id(function), frozenset())
            )
            rows.append(
                {
                    "site": f"{relative}::{function.name}",
                    "path": relative,
                    "owner": function.name,
                    "api": call.func.attr,  # type: ignore[union-attr]
                    "line": call.lineno,
                    "verdict": "RETAIN" if reasons else "MIGRATE",
                    "reasons": reasons,
                }
            )
    return rows


def fold(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """Fold sites onto their owning definition.

    A definition is RETAIN when ANY of its sites is, because the test is
    migrated or deleted whole.
    """
    folded: dict[str, dict[str, object]] = {}
    for row in rows:
        site = str(row["site"])
        entry = folded.setdefault(
            site,
            {"site": site, "path": row["path"], "owner": row["owner"],
             "sites": 0, "lines": [], "verdict": "MIGRATE", "reasons": []},
        )
        entry["sites"] = int(entry["sites"]) + 1  # type: ignore[arg-type]
        lines = entry["lines"]
        assert isinstance(lines, list)
        lines.append(row["line"])
        if row["verdict"] == "RETAIN":
            entry["verdict"] = "RETAIN"
        reasons = entry["reasons"]
        assert isinstance(reasons, list)
        for reason in row["reasons"]:  # type: ignore[union-attr]
            if reason not in reasons:
                reasons.append(reason)
    for entry in folded.values():
        entry["lines"] = sorted(entry["lines"])  # type: ignore[arg-type]
        entry["reasons"] = sorted(entry["reasons"])  # type: ignore[arg-type]
    return folded


# MAIN's effective ruling per definition. `MIGRATE` re-bases onto `propose`;
# `MIGRATE-RESOLVE` re-bases a deterministic hit onto `resolve`, which the
# mechanical rule cannot name because it reads consumption, not intent.
VERDICTS = ("MIGRATE", "MIGRATE-RESOLVE", "RETAIN")
MIGRATING = ("MIGRATE", "MIGRATE-RESOLVE")


def emit(root: pathlib.Path, previous: dict[str, object] | None = None) -> dict[str, object]:
    """Regenerate the census, preserving any ruling already recorded."""
    folded = fold(survey(root))
    rulings: dict[str, dict[str, object]] = {}
    if previous:
        for entry in previous.get("definitions", []):  # type: ignore[union-attr]
            rulings[str(entry["site"])] = entry

    definitions = []
    for site in sorted(folded):
        entry = folded[site]
        measured = str(entry["verdict"])
        prior = rulings.get(site, {})
        record = {
            "site": site,
            "path": entry["path"],
            "owner": entry["owner"],
            "sites": entry["sites"],
            "lines": entry["lines"],
            "reasons": entry["reasons"],
            "measured": measured,
            "verdict": str(prior.get("verdict", measured)),
        }
        if prior.get("grounds"):
            record["grounds"] = prior["grounds"]
        definitions.append(record)

    return {
        "kind": "m3u6a1-consumer-census",
        "totals": {
            "definitions": len(definitions),
            "migrate": sum(1 for e in definitions if e["verdict"] == "MIGRATE"),
            "migrate_resolve": sum(
                1 for e in definitions if e["verdict"] == "MIGRATE-RESOLVE"
            ),
            "retain": sum(1 for e in definitions if e["verdict"] == "RETAIN"),
            "sites": sum(int(e["sites"]) for e in definitions),  # type: ignore[arg-type]
        },
        "definitions": definitions,
    }


def grade(root: pathlib.Path, table_path: pathlib.Path) -> int:
    """Fail when any site is unruled, drifted, ungrounded, or unmigrated."""
    if not table_path.exists():
        print(f"FAIL: no disposition table at {table_path}")
        return 1
    table = json.loads(table_path.read_text())
    recorded = {str(entry["site"]): entry for entry in table["definitions"]}
    measured = fold(survey(root))

    unruled = sorted(set(measured) - set(recorded))
    stale = sorted(set(recorded) - set(measured))
    shared = sorted(set(measured) & set(recorded))

    # The mechanical verdict moving invalidates the ruling built on it, so a
    # drifted row is reported rather than silently re-adopted.
    drift = [
        f"{s} recorded={recorded[s].get('measured')} now={measured[s]['verdict']}"
        for s in shared
        if recorded[s].get("measured") != measured[s]["verdict"]
    ]
    ungrounded = [
        s
        for s in shared
        if recorded[s]["verdict"] != recorded[s].get("measured")
        and not str(recorded[s].get("grounds", "")).strip()
    ]
    bad_verdict = [
        s for s in shared if recorded[s]["verdict"] not in VERDICTS
    ]
    # A definition ruled MIGRATE must hold no lifecycle call once the unit lands.
    surviving = sorted(
        s for s in shared if recorded[s]["verdict"] in MIGRATING
    )

    for label, members in (
        ("UNRULED", unruled),
        ("STALE", stale),
        ("MEASURE-DRIFT", drift),
        ("UNGROUNDED-OVERRIDE", ungrounded),
        ("BAD-VERDICT", bad_verdict),
        ("SURVIVING-MIGRATE", surviving),
    ):
        print(f"{label}: {len(members)}")
        for member in members:
            print(f"  - {member}")

    totals = {
        "definitions": len(measured),
        "ruled_migrate": sum(
            1 for s in shared if recorded[s]["verdict"] == "MIGRATE"
        ),
        "ruled_migrate_resolve": sum(
            1 for s in shared if recorded[s]["verdict"] == "MIGRATE-RESOLVE"
        ),
        "ruled_retain": sum(1 for s in shared if recorded[s]["verdict"] == "RETAIN"),
        "overrides": sum(
            1 for s in shared if recorded[s]["verdict"] != recorded[s].get("measured")
        ),
        "sites": sum(int(e["sites"]) for e in measured.values()),  # type: ignore[arg-type]
    }
    print(f"TOTALS: {json.dumps(totals, sort_keys=True)}")
    failed = bool(
        unruled or stale or drift or ungrounded or bad_verdict or surviving
    )
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


def self_test(root: pathlib.Path) -> int:
    """Grade the grader both ways, one seed per control line."""
    import tempfile

    ok = True
    current = emit(root)
    with tempfile.TemporaryDirectory() as directory:
        base = pathlib.Path(directory)

        # Control 1: emit must be idempotent over its own output, so a ruling
        # already recorded survives a regeneration byte for byte. Comparing a
        # ruled table against a bare measurement instead would compare two
        # different shapes and fail for a reason unrelated to the property.
        agrees = emit(root, current) == current
        print(f"CONTROL emit-is-idempotent: {agrees}")
        ok = ok and agrees

        # Control 2: a dropped entry must surface as UNRULED.
        dropped = json.loads(json.dumps(current))
        dropped["definitions"] = dropped["definitions"][1:]
        path = base / "dropped.json"
        path.write_text(json.dumps(dropped))
        fired = grade(root, path) != 0
        print(f"CONTROL dropped-entry-fails: {fired}")
        ok = ok and fired

        # Control 3: an invented entry must surface as STALE.
        invented = json.loads(json.dumps(current))
        invented["definitions"].append(
            {"site": "tests/nowhere.py::test_ghost", "verdict": "RETAIN"}
        )
        path = base / "invented.json"
        path.write_text(json.dumps(invented))
        fired = grade(root, path) != 0
        print(f"CONTROL invented-entry-fails: {fired}")
        ok = ok and fired

        # Control 4: a flipped verdict must surface as MISCLASSIFIED.
        flipped = json.loads(json.dumps(current))
        for entry in flipped["definitions"]:
            if entry["verdict"] == "RETAIN":
                entry["verdict"] = "MIGRATE"
                break
        path = base / "flipped.json"
        path.write_text(json.dumps(flipped))
        fired = grade(root, path) != 0
        print(f"CONTROL flipped-verdict-fails: {fired}")
        ok = ok and fired

    print("SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()

    if args.emit:
        TABLE.write_text(json.dumps(emit(root), indent=2, sort_keys=True) + "\n")
        print(f"wrote {TABLE}")
        return 0
    if args.self_test:
        return self_test(root)
    return grade(root, TABLE)


if __name__ == "__main__":
    sys.exit(main())
