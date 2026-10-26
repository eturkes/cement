"""Shared shape predicates for obligation-battery graders."""
import ast


def has_assertion(node: ast.AST) -> bool:
    return any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "self"
        and call.func.attr.startswith(("assert", "fail"))
        for call in ast.walk(node)
    )
