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


def _sql_values(expression: ast.AST, *, scope: ast.AST) -> list[str] | None:
    parents = {child: parent for parent in ast.walk(scope) for child in ast.iter_child_nodes(parent)}

    def owner(node: ast.AST) -> ast.AST | None:
        current = parents.get(node)
        while current is not None and not isinstance(current, ast.FunctionDef):
            current = parents.get(current)
        return current

    def assignment(name: ast.Name) -> ast.AST | None:
        stores = [n for n in ast.walk(scope) if isinstance(n, ast.Name)
                  and n.id == name.id and isinstance(n.ctx, ast.Store) and owner(n) is owner(name)]
        if len(stores) != 1:
            return None
        statement = parents.get(stores[0])
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            return statement.value
        return None

    def literal(node: ast.AST, seen: frozenset[ast.AST]) -> object:
        if node in seen:
            raise ValueError("cyclic constant")
        if isinstance(node, ast.Name):
            value = assignment(node)
            if value is None:
                raise ValueError("dynamic value")
            return literal(value, seen | {node})
        return ast.literal_eval(node)

    def values(node: ast.AST, seen: frozenset[ast.AST]) -> list[str] | None:
        if node in seen:
            return None
        seen = seen | {node}
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.JoinedStr):
            return ["".join(p.value for p in node.values if isinstance(p, ast.Constant))]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            templates = values(node.func.value, seen)
            if templates is None or any(k.arg is None for k in node.keywords):
                return None
            try:
                args = [literal(arg, frozenset()) for arg in node.args]
                kwargs = {k.arg: literal(k.value, frozenset()) for k in node.keywords}
                return [template.format(*args, **kwargs) for template in templates]
            except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                return None
        if not isinstance(node, ast.Name):
            return None
        assigned = assignment(node)
        if assigned is not None:
            return values(assigned, seen)
        for loop in (n for n in ast.walk(scope) if isinstance(n, ast.For) and owner(n) is owner(node)):
            if not isinstance(loop.target, (ast.Tuple, ast.List)):
                continue
            indexes = [i for i, target in enumerate(loop.target.elts)
                       if isinstance(target, ast.Name) and target.id == node.id]
            if len(indexes) != 1:
                continue
            stores = [n for n in ast.walk(scope) if isinstance(n, ast.Name)
                      and n.id == node.id and isinstance(n.ctx, ast.Store) and owner(n) is owner(node)]
            if stores != [loop.target.elts[indexes[0]]] or node not in set(ast.walk(loop)):
                return None
            try:
                rows = literal(loop.iter, frozenset())
                result = [row[indexes[0]] for row in rows]
                if result and all(isinstance(value, str) for value in result):
                    return result
            except (ValueError, TypeError, IndexError):
                pass
            return None
        function = owner(node)
        if not isinstance(function, ast.FunctionDef) or function is scope:
            return None
        parameters = [*function.args.posonlyargs, *function.args.args]
        positions = [i for i, arg in enumerate(parameters) if arg.arg == node.id]
        if len(positions) != 1 or any(
            isinstance(n, ast.Name) and n.id == node.id and not isinstance(n.ctx, ast.Load)
            for n in ast.walk(function)
        ):
            return None
        uses = [n for n in ast.walk(scope) if isinstance(n, ast.Name) and n.id == function.name]
        result = []
        for use in uses:
            call = parents.get(use)
            if not isinstance(call, ast.Call) or call.func is not use:
                return None
            index = positions[0]
            argument = call.args[index] if index < len(call.args) else next(
                (k.value for k in call.keywords if k.arg == node.id), None
            )
            if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
                return None
            result.append(argument.value)
        return result or None

    return values(expression, frozenset())


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
        values = _sql_values(child.args[0], scope=node)
        found.extend(values if values is not None else ["<non-literal>"])
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
    # Transitive pass to a fixpoint: a helper that hands its own `connection` on makes that
    # callee a helper too, so a read path split across several helpers stays covered.
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    frontier = set(helpers)
    while frontier:
        found: set[str] = set()
        for node in functions:
            if node.name not in frontier:
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                if not any(isinstance(a, ast.Name) and a.id == "connection" for a in child.args):
                    continue
                if isinstance(child.func, ast.Name):
                    found.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    found.add(child.func.attr)
        frontier = found - helpers
        helpers |= found
    # Every helper body must also be SELECT-only.
    for node in functions:
        if node.name in helpers:
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
        for statement in ("SELECT 1", "UPDATE operations SET revision = revision"):
            source = f"def outer(connection):\n def query(sql):\n  return connection.execute(sql)\n query({statement!r})\n"
            tree = ast.parse(source).body[0]
            self.assertEqual(_sql_literals(tree), [statement])
        dynamic = ast.parse("def outer(connection, sql):\n def query(text):\n  return connection.execute(text)\n query(sql)\n").body[0]
        self.assertEqual(_sql_literals(dynamic), ["<non-literal>"])
        for statement in ("SELECT 1", "DELETE FROM operations"):
            formatted = ast.parse(f"def outer(connection):\n sql = {statement!r} + ''\n connection.execute(sql)\n").body[0]
            self.assertEqual(_sql_literals(formatted), ["<non-literal>"])
            formatted = ast.parse(f"def outer(connection):\n sql = {statement!r}\n connection.execute(sql.format())\n").body[0]
            self.assertEqual(_sql_literals(formatted), [statement])
            loop = ast.parse(f"def outer(connection):\n sources = [('kind', {statement!r})]\n for kind, sql in sources:\n  connection.execute(sql)\n").body[0]
            self.assertEqual(_sql_literals(loop), [statement])
        reassigned = ast.parse("def outer(connection):\n sources = [('kind', 'SELECT 1')]\n for kind, sql in sources:\n  sql = 'DELETE FROM operations'\n  connection.execute(sql)\n").body[0]
        self.assertEqual(_sql_literals(reassigned), ["<non-literal>"])




    def test_the_census_still_finds_the_surface_it_was_measured_against(self) -> None:
        # A collapsed census would report zero offenders over zero sites.
        result = census()
        self.assertGreaterEqual(result["read_sites"], 17)
        self.assertGreaterEqual(result["write_sites"], 13)
        self.assertGreaterEqual(len(result["helpers"]), 12)


if __name__ == "__main__":
    unittest.main()
