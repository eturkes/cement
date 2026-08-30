#!/usr/bin/env python
"""S2 ground probes: MAIN's own re-derivation of the five wave-1 map findings the
M3.5a acceptance contract asserts as facts.

A grade proves each map anchor resolves and each cell is filled; it never proves a
finding true. Run from the repository root:

    uv run python .agent/decisions/m3u5a-s2-probe.py

Emits one JSON object on stdout. Exit 0 = every probe answered; the contract cites
these values, so a changed answer is a contract defect rather than a test failure.
"""

from __future__ import annotations

import argparse
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
    """M18/X02: does ordinary `System` construction create an absent ledger?"""
    with tempfile.TemporaryDirectory() as root:
        target = pathlib.Path(root) / "typo.db"
        before = target.exists()
        System(str(target))
        return {
            "exists_before": before,
            "exists_after": target.exists(),
            "bytes_after": target.stat().st_size if target.exists() else None,
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
    """Y10: how many unexported copies of the provenance cap the library holds."""
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "cement_runtime"
        / "system.py"
    ).read_text(encoding="utf-8")
    return {
        "literal_sites": source.count("65_536"),
        "exported_constant": "PROVENANCE_MAX_BYTES" in source,
    }


def main() -> int:
    report = {
        "absent_path_construction": probe_absent_path_construction(),
        "deleted_ledger_resolve": probe_deleted_ledger_resolve(),
        "parser_census": probe_parser_census(),
        "abbreviation": probe_abbreviation(),
        "bare_string_emit": probe_bare_string_emit(),
        "provenance_literal": probe_provenance_literal(),
    }
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
