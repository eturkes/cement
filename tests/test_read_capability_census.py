"""Reachability census backing M3.2a's private `_ReadOnlyViolation`.

`.agent/decisions/m3u2a-contract.md` section 3a licenses the private class on the
claim that every ``Store.transaction(write=False)`` block in ``system.py`` is
SELECT-only. Section 7 makes the census a committed check: it must rerun and still
report zero mutating read sites, or the section 3 decision is void.
"""

from __future__ import annotations

import ast
from pathlib import Path

import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "cement_runtime" / "system.py"
MUTATING = ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE", "ATTACH", "VACUUM")


def _is_transaction_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "transaction"
    )


def _writes(call: ast.Call) -> bool:
    """True when ``transaction(write=True)`` is requested explicitly."""
    for keyword in call.keywords:
        if keyword.arg == "write":
            return not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
    return False


def _sql_literals(node: ast.AST) -> list[str]:
    """Every SQL string handed to ``.execute``/``.executemany`` under ``node``."""
    found: list[str] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
            continue
        if child.func.attr not in {"execute", "executemany", "executescript"}:
            continue
        if not child.args:
            found.append("<no-argument>")
            continue
        first = child.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.append(first.value)
        elif isinstance(first, ast.JoinedStr):
            parts = [p.value for p in first.values if isinstance(p, ast.Constant)]
            found.append("".join(parts))
        else:
            found.append("<non-literal>")
    return found


def census() -> dict[str, object]:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    read_sites = 0
    write_sites = 0
    offenders: list[str] = []
    helpers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            if not _is_transaction_call(item.context_expr):
                continue
            assert isinstance(item.context_expr, ast.Call)
            if _writes(item.context_expr):
                write_sites += 1
                continue
            read_sites += 1
            bound = item.optional_vars
            name = bound.id if isinstance(bound, ast.Name) else None
            for statement in _sql_literals(node):
                head = statement.strip().split(None, 1)
                verb = head[0].upper() if head else ""
                if verb in MUTATING or statement in {"<non-literal>", "<no-argument>"}:
                    offenders.append(f"line {node.lineno}: {statement[:70]}")
            # Helpers handed the read connection.
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    if any(isinstance(a, ast.Name) and a.id == name for a in child.args):
                        helpers.add(child.func.id)
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if any(isinstance(a, ast.Name) and a.id == name for a in child.args):
                        helpers.add(child.func.attr)
    # Transitive pass: every helper body must also be SELECT-only.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in helpers:
            for statement in _sql_literals(node):
                head = statement.strip().split(None, 1)
                verb = head[0].upper() if head else ""
                if verb in MUTATING or statement in {"<non-literal>", "<no-argument>"}:
                    offenders.append(f"helper {node.name}: {statement[:70]}")
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "commit"
                ):
                    offenders.append(f"helper {node.name}: commit()")
    return {
        "read_sites": read_sites,
        "write_sites": write_sites,
        "helpers": sorted(helpers),
        "offenders": offenders,
    }


class ReadReachabilityTests(unittest.TestCase):
    """Section 3a: enforcement breaks no shipped call site."""

    def test_every_read_transaction_block_is_select_only(self) -> None:
        result = census()
        self.assertEqual(result["offenders"], [], "a read block reaches a mutating statement")

    def test_the_census_still_finds_the_surface_it_was_measured_against(self) -> None:
        # A collapsed census would report zero offenders over zero sites.
        result = census()
        self.assertGreaterEqual(result["read_sites"], 17)
        self.assertGreaterEqual(result["write_sites"], 15)
        self.assertGreaterEqual(len(result["helpers"]), 12)


if __name__ == "__main__":
    unittest.main()
