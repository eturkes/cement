#!/usr/bin/env python3
"""p03-stored-int-census — every integer/boolean conversion in `system.py`, classified (§G of
`.agent/decisions/m2u4c-surface.md`).

Sites = each `int(…)`, `bool(…)` and `_stored_int(…)` call. Guard classes:
  exact        `_stored_int` (exact `type(v) is int`, schema bounds, `IntegrityError`)
  pre-checked  `type(<same expression>) is not int` raises within the 10 lines above
  in-memory    the value is computed in process (`assessment[…]`, a runtime `passed` bool,
               the `failures` list)
  driver       `cursor.lastrowid` behind an explicit `None` check
  UNGUARDED    anything else → rc 1
Column nullability = the schema's INTEGER columns of that name (`store.SCHEMA`, every table holding
it). Public surfaces = the public `System` methods whose call graph (`self.x(…)` + module-level
calls) reaches the enclosing function.

Usage: uv run python .agent/decisions/p03-stored-int-census.py [--markdown]
rc 0 = no UNGUARDED site; 1 = one or more (each printed).
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "src/cement_runtime/system.py"
STORE = ROOT / "src/cement_runtime/store.py"


def _schema_columns() -> dict[str, list[str]]:
    """column → ['table' or 'table?' (nullable)] over every INTEGER column."""
    text = STORE.read_text(encoding="utf-8")
    columns: dict[str, list[str]] = {}
    for table, body in re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+) \((.*?)\n\)", text, re.S):
        for name, rest in re.findall(r"^\s*(\w+) INTEGER\b([^,\n]*)", body, re.M):
            nullable = "NOT NULL" not in rest and "PRIMARY KEY" not in rest
            columns.setdefault(name, []).append(table + ("?" if nullable else ""))
    return columns


def _call_graph(tree: ast.Module) -> tuple[dict[str, set[str]], set[str]]:
    edges: dict[str, set[str]] = {}
    public: set[str] = set()
    functions: list[tuple[str, ast.FunctionDef]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append((node.name, node))
        elif isinstance(node, ast.ClassDef) and node.name == "System":
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    functions.append((item.name, item))
                    if not item.name.startswith("_"):
                        public.add(item.name)
    names = {name for name, _ in functions}
    for name, node in functions:
        called = set()
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self":
                called.add(func.attr)
            elif isinstance(func, ast.Name):
                called.add(func.id)
        edges[name] = called & names
    return edges, public


def _surfaces(target: str, edges: dict[str, set[str]], public: set[str]) -> list[str]:
    reach = []
    for start in sorted(public):
        seen, stack = set(), [start]
        while stack:
            name = stack.pop()
            if name == target:
                reach.append(start)
                break
            if name in seen:
                continue
            seen.add(name)
            stack.extend(edges.get(name, ()))
    return reach


def main(argv: list[str]) -> int:
    source = SYSTEM.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    edges, public = _call_graph(tree)
    columns = _schema_columns()
    spans = sorted(
        ((n.lineno, n.end_lineno or n.lineno, n.name) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)),
        key=lambda s: s[1] - s[0],
    )
    sites = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"int", "bool", "_stored_int"}):
            continue
        if node.func.id == "bool" and node.args and isinstance(node.args[0], ast.Call) and getattr(node.args[0].func, "id", "") == "_stored_int":
            continue  # its inner `_stored_int` is the site
        argument = node.args[0] if node.args else None
        expression = ast.unparse(argument) if argument is not None else ""
        function = next((name for start, end, name in spans if start <= node.lineno <= end), "-")
        root = argument
        while isinstance(root, (ast.Subscript, ast.Attribute, ast.Call)):
            root = root.value if not isinstance(root, ast.Call) else root.func
        root_name = root.id if isinstance(root, ast.Name) else ""
        window = "\n".join(lines[max(0, node.lineno - 11) : node.lineno - 1]).replace('"', "'")
        if node.func.id == "_stored_int":
            guard = "exact"
        elif expression and f"type({expression}) is not int" in window:
            guard = "pre-checked"
        elif root_name in {"assessment", "passed", "failures"}:
            guard = "in-memory"
        elif expression == "cursor.lastrowid":
            guard = "driver"
        else:
            guard = "UNGUARDED"
        key = argument.slice.value if isinstance(argument, ast.Subscript) and isinstance(argument.slice, ast.Constant) else None
        nullability = ", ".join(columns.get(key, [])) if isinstance(key, str) else "-"
        sites.append((node.lineno, function, f"{node.func.id}({expression})", guard, nullability or "-", _surfaces(function, edges, public)))
    sites.sort()
    unguarded = [site for site in sites if site[3] == "UNGUARDED"]
    if "--markdown" in argv:
        print("| line | function | conversion | guard | INTEGER column (`?` = nullable) | public surfaces |")
        print("|---|---|---|---|---|---|")
        for line, function, conversion, guard, nullability, surfaces in sites:
            shown = ", ".join(f"`{s}`" for s in surfaces) if surfaces else "-"
            print(f"| {line} | `{function}` | `{conversion}` | {guard} | {nullability} | {shown} |")
    for site in unguarded:
        print(f"UNGUARDED system.py:{site[0]} {site[1]}: {site[2]}")
    counts = {g: sum(s[3] == g for s in sites) for g in ("exact", "pre-checked", "in-memory", "driver", "UNGUARDED")}
    print(f"SITES: {len(sites)} {counts}", file=sys.stderr)
    return 1 if unguarded else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
