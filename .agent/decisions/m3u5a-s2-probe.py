#!/usr/bin/env python
"""S2 ground probes: MAIN's own re-derivation of the wave-1 map findings the M3.5a
acceptance contract asserts as facts. Seven probes, 19 graded pins.

A grade proves each map anchor resolves and each cell is filled; it never proves a
finding true. Run from the repository root:

    uv run python .agent/decisions/m3u5a-s2-probe.py

Emits one JSON object on stdout and one `CHECK` line per pinned fact on stderr.
**Exit 0 = every pinned fact still holds**; any mismatch exits 1 and names the fact.

`--emit-pins` prints the live values in `EXPECTED` form, so a deliberate re-anchor is a
copy rather than a retype.

Two pins carry POST-implementation values because M3.5a's own obligations move them, and
pinning the S1 measurement would make the unit's gate contradict the unit's contract:

  parser_census      D25 moves 28 leaves / 35 nodes -> 30 / 37, adding exactly
                     `resolve` and `proposal submit` while all 28 baseline names survive.
  provenance_literal D16 exports `PROVENANCE_MAX_BYTES`, so system.py's three unexported
                     `65_536` copies collapse to the single declaration site.

Every other pin is the S1 measurement unchanged. Legacy option abbreviation stays ACCEPTED
here on purpose: M3.5a scopes `allow_abbrev=False` to its two new leaves, and a global
sweep is deferred to M3.5b, so this pin failing green would hide that deferral closing.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from cement_runtime import cli as cement_cli  # noqa: E402
from cement_runtime.errors import IntegrityError  # noqa: E402
from cement_runtime.models import CompilePolicy  # noqa: E402
from cement_runtime.system import System  # noqa: E402


def probe_absent_path_construction() -> dict[str, object]:
    """M18/X02: does ordinary `System` construction create an absent ledger?

    The graded facts are creation and DETERMINISM, never the byte size. A fresh v2
    ledger's size is a function of the host SQLite build's page size and storage layout,
    so pinning it would fail on a library upgrade that changes nothing this unit claims.
    `bytes_after` stays REPORTED because the deferral entries cite it; `bytes_positive`
    and `bytes_deterministic` are what the gate grades.
    """
    with tempfile.TemporaryDirectory() as root:
        target = pathlib.Path(root) / "typo.db"
        before = target.exists()
        System(str(target))
        size = target.stat().st_size if target.exists() else None

        sibling = pathlib.Path(root) / "twin.db"
        System(str(sibling))
        twin = sibling.stat().st_size if sibling.exists() else None

        return {
            "exists_before": before,
            "exists_after": target.exists(),
            "bytes_after": size,
            "bytes_positive": bool(size),
            "bytes_deterministic": size is not None and size == twin,
        }


def probe_deleted_ledger_resolve() -> dict[str, object]:
    """X17: exact class and message `resolve` raises once its ledger is removed."""
    with tempfile.TemporaryDirectory() as root:
        target = pathlib.Path(root) / "ledger.db"
        system = System(str(target))
        system.register_operation("tenant_a", "echo_1", policy=CompilePolicy())
        target.unlink()
        try:
            system.resolve("tenant_a", "echo_1", {"case": 12})
        except IntegrityError as exc:
            return {
                "raised": type(exc).__name__,
                "message": str(exc),
                "path_absent_after": not target.exists(),
            }
        return {"raised": None, "message": None, "path_absent_after": not target.exists()}


def _walk(parser: argparse.ArgumentParser) -> tuple[int, int, list[str]]:
    nodes = 0
    leaves: list[str] = []

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        nonlocal nodes
        nodes += 1
        children = [
            action
            for action in node._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if not children:
            leaves.append(" ".join(path))
            return
        for action in children:
            for name, child in action.choices.items():
                visit(child, path + (name,))

    visit(parser, ())
    return len(leaves), nodes, sorted(leaves)


def probe_parser_census() -> dict[str, object]:
    """M17: terminal-leaf and total-node counts derived from the live parser."""
    leaves, nodes, names = _walk(cement_cli._parser())
    return {"leaves": leaves, "nodes": nodes, "leaf_names": names}


def probe_parser_shape() -> dict[str, object]:
    """A12: a canonical digest of the WHOLE parser, replacing B02's retired `cli.py` pin.

    D24, D25 and D26 between them cover source reach, leaf names and option isolation.
    None of the three notices an old leaf's changed default, so mutating `events --limit`
    from 1000 to 7 left all of them green while operator-visible behaviour changed. This
    digest is what makes D27's migration claim true: every leaf's option strings,
    destinations, defaults, required flags and nargs, canonically ordered.

    A per-NODE line carries `allow_abbrev`, because that flag belongs to the parser and
    not to any action: without it, disabling abbreviation on an existing leaf leaves every
    action attribute, the 30/37 census and all three section-2 probes unchanged, so D25's
    `option abbreviation elsewhere is unchanged` had no instrument at all.
    """
    shape: list[str] = []

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        shape.append("|".join((" ".join(path), "<node>", repr(bool(node.allow_abbrev)))))
        children = [
            action
            for action in node._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        for action in sorted(node._actions, key=lambda item: item.dest):
            if isinstance(action, argparse._SubParsersAction):
                continue
            shape.append(
                "|".join(
                    (
                        " ".join(path),
                        action.dest,
                        ",".join(sorted(action.option_strings)),
                        repr(action.default),
                        repr(bool(action.required)),
                        repr(action.nargs),
                        type(action).__name__,
                    )
                )
            )
        for action in children:
            for name, child in sorted(action.choices.items()):
                visit(child, path + (name,))

    visit(cement_cli._parser(), ())
    payload = "\n".join(shape).encode("utf-8")
    return {
        "actions": len(shape),
        "digest": hashlib.sha256(payload).hexdigest()[:16],
    }


def probe_abbreviation() -> dict[str, object]:
    """M16: is option abbreviation reachable on the root and on a nested leaf?"""
    parser = cement_cli._parser()
    results: dict[str, object] = {}
    for label, argv in (
        ("root_--part", ["--part", "tenant_a", "--db", "x", "events"]),
        ("nested_function_eval_--bun", ["function", "eval", "--bun", "b", "--in", "1"]),
    ):
        try:
            namespace = parser.parse_args(argv)
        except cement_cli._UsageError as exc:
            results[label] = {"accepted": False, "message": str(exc)}
        else:
            results[label] = {
                "accepted": True,
                "partition": getattr(namespace, "partition", None),
                "bundle": getattr(namespace, "bundle", None),
                "input": getattr(namespace, "input", None),
            }
    return results


def probe_bare_string_emit() -> dict[str, object]:
    """X07: bytes `main`'s output seam writes for a bare proposal-id return."""
    stream = io.StringIO()
    cement_cli._emit("prop_probe", stream=stream)
    return {"bytes": stream.getvalue().encode("utf-8").decode("unicode_escape")}


def probe_provenance_literal() -> dict[str, object]:
    """Y10: how many unexported copies of the provenance cap the library holds.

    Counted over the AST, not the text: a substring census also counts the number inside
    comments and docstrings, and substring membership is not an exported-symbol check, so
    a module that only MENTIONS `PROVENANCE_MAX_BYTES` in prose would read as exporting it.
    """
    path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "cement_runtime"
        / "system.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == 65_536
    ]
    import cement_runtime.system as system_module

    return {
        "literal_sites": len(literals),
        "exported_constant": getattr(system_module, "PROVENANCE_MAX_BYTES", None) == 65_536,
        "reference_sites": sum(
            isinstance(node, ast.Name) and node.id == "PROVENANCE_MAX_BYTES"
            for node in ast.walk(tree)
        ),
    }


# The 28 leaf paths that predate M3.5a, walked out of `_parser()` at c8b82cd, whose
# `cli.py` is 83198e1's. D25 requires every one to survive by NAME, which is the
# assertion the leaf COUNT cannot make. Derived, never recalled: a hand-written set got
# three names wrong and this gate caught it.
BASELINE_LEAVES = frozenset(
    {
        "artifact list",
        "artifact show",
        "artifact suspend",
        "challenge",
        "compile",
        "events",
        "example list",
        "example revoke",
        "function eval",
        "function export",
        "function inspect",
        "function promote",
        "function receipts",
        "function show",
        "function verify",
        "function verify-drafts",
        "handle",
        "operation list",
        "operation register",
        "operation revise",
        "promote",
        "proposal list",
        "proposal review",
        "proposal show",
        "report list",
        "report show",
        "request",
        "verify",
    }
)

EXPECTED: dict[str, dict[str, object]] = {
    "absent_path_construction": {
        "exists_before": False,
        "exists_after": True,
        "bytes_positive": True,
        "bytes_deterministic": True,
    },
    "deleted_ledger_resolve": {
        "raised": "IntegrityError",
        "message": "ledger file is missing or unreadable",
        "path_absent_after": True,
    },
    # Re-based by M3.5b D17: `handle` and `request` leave the grammar, so 30/37 -> 28/35.
    # The count alone cannot separate this state from pre-M3.5a `c8b82cd`, which is also
    # 28/35 over the exact INVERSE set, so the name-set grade below carries the claim.
    "parser_census": {"leaves": 28, "nodes": 35},
    # 116 action lines + one `<node>` line per parser node, which is exactly the census's
    # 35. The node line carries `allow_abbrev`, so disabling it on an existing leaf moves
    # the digest (`proposal review` -> `515b30796c61d189`) while the census stays 28/35.
    # M3.5b D21: `c8b82cd` reads 154 / `af19339c3995c97d` under THIS algorithm, so the
    # digest separates the two 28/35 states the census collides.
    "parser_shape": {"actions": 151, "digest": "ebd2ac811bd9776d"},
    "bare_string_emit": {"bytes": '"prop_probe"\n'},
    "provenance_literal": {
        "exported_constant": True,
        "literal_sites": 1,
        # 1 declaration target + the 3 former literal sites D16 rewired.
        "reference_sites": 4,
    },
}


def _grade(report: dict[str, object]) -> list[str]:
    """Return one failure sentence per broken pin; empty means the gate passes."""
    failures: list[str] = []
    for probe, pins in EXPECTED.items():
        answered = report[probe]
        assert isinstance(answered, dict)
        for fact, want in pins.items():
            got = answered.get(fact)
            verdict = "ok" if got == want else "FAIL"
            print(f"CHECK   {probe}.{fact} {verdict} want={want!r} got={got!r}", file=sys.stderr)
            if got != want:
                failures.append(f"{probe}.{fact}: want {want!r}, got {got!r}")

    # D25 is a NAME claim, so the census pin above is graded a second way. M3.5b D17
    # moves the EXPECTATION, never `BASELINE_LEAVES`: the frozenset records `c8b82cd`,
    # which is history. "Nothing is lost" becomes "exactly these two are lost", which is
    # what makes the pin discriminate a landed removal from an unlanded one.
    names = set(report["parser_census"]["leaf_names"])  # type: ignore[index,call-overload]
    lost = sorted(BASELINE_LEAVES - names)
    added = sorted(names - BASELINE_LEAVES)
    for label, got, want in (
        ("parser_census.lost_baseline_leaves", lost, ["handle", "request"]),
        ("parser_census.added_leaves", added, ["proposal submit", "resolve"]),
    ):
        verdict = "ok" if got == want else "FAIL"
        print(f"CHECK   {label} {verdict} want={want!r} got={got!r}", file=sys.stderr)
        if got != want:
            failures.append(f"{label}: want {want!r}, got {got!r}")

    # Legacy abbreviation is DEFERRED, never fixed here; a green would mean M3.5b landed
    # early and this probe stopped describing the tree.
    abbreviation = report["abbreviation"]
    assert isinstance(abbreviation, dict)
    for label, field, want in (
        ("root_--part", "partition", "tenant_a"),
        ("nested_function_eval_--bun", "bundle", "b"),
    ):
        cell = abbreviation[label]
        assert isinstance(cell, dict)
        got = (cell.get("accepted"), cell.get(field))
        verdict = "ok" if got == (True, want) else "FAIL"
        print(
            f"CHECK   abbreviation.{label} {verdict} want={(True, want)!r} got={got!r}",
            file=sys.stderr,
        )
        if got != (True, want):
            failures.append(f"abbreviation.{label}: want {(True, want)!r}, got {got!r}")
    return failures


def main(argv: list[str]) -> int:
    report = {
        "absent_path_construction": probe_absent_path_construction(),
        "deleted_ledger_resolve": probe_deleted_ledger_resolve(),
        "parser_census": probe_parser_census(),
        "parser_shape": probe_parser_shape(),
        "abbreviation": probe_abbreviation(),
        "bare_string_emit": probe_bare_string_emit(),
        "provenance_literal": probe_provenance_literal(),
    }
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if argv[1:] == ["--emit-pins"]:
        json.dump(report, sys.stderr, indent=2, sort_keys=True)
        sys.stderr.write("\n")
        return 0

    failures = _grade(report)
    total = sum(len(pins) for pins in EXPECTED.values()) + 4
    if failures:
        print(f"FAIL    {len(failures)} of {total} pinned facts moved", file=sys.stderr)
        for line in failures:
            print(f"        {line}", file=sys.stderr)
        return 1
    print(f"PASS    {total} pinned facts hold", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
