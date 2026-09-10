#!/usr/bin/env python3
"""M3.6a2 gate 4 — closure checks over the post-state package.

Reports L09 (dangling references), L10 (the `.models` import delta), L11 (`request.*` emission
sites), L13 (the surviving `requests` site inventory) and L12/L14/L15 (byte identity) as
INDEPENDENTLY named checks with their own verdicts, so one green line never speaks for another.

The battery asserts the same obligations; this is the second instrument. Its value is that it
derives every figure from the tree and from `da70a56` rather than from the battery's literals, so a
battery clause rewritten to match a defect disagrees with it here.

    uv run python .agent/decisions/m3u6a2-closure.py              # grade the tree
    uv run python .agent/decisions/m3u6a2-closure.py --self-test  # grade the grader both ways
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import pathlib
import re
import subprocess
import sys
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE_SHA = "da70a56"
PACKAGE = "src/cement_runtime"
SYSTEM = f"{PACKAGE}/system.py"

# L09. `tokenize` NAME equality, so `handler` and `unhandled` never count. `request_status` is
# SEVEN, not zero: deleting the method removes one identifier and leaves the proposal plumbing,
# the last occurrence inside byte-frozen `get_proposal` (contract C09).
DANGLING = {
    "handle": 0,
    "request_status": 7,
    "_outcome": 0,
    "_fail_generation": 0,
    "_request_revision_is_current": 0,
    "_lease_us": 0,
}
DYNAMIC = {"getattr", "setattr", "hasattr", "delattr"}

# L10. The seven names `system.py` stops importing from `.models`; no other import moves.
DROPPED_IMPORTS = {
    "FallbackFailed",
    "InProgress",
    "Outcome",
    "ReconciliationRequired",
    "Rejected",
    "Resolved",
    "ReviewRequired",
}

# L11. The complete surviving vocabulary, asserted as a SET: an absence assertion stays green while
# a further kind is invented.
EVENT_KINDS = {
    "artifact.challenged",
    "artifact.compiled",
    "artifact.counterexample",
    "artifact.integrity_quarantined",
    "artifact.promoted",
    "artifact.suspended",
    "artifact.verification_failed",
    "artifact.verified",
    "example.revoked",
    "function.promoted",
    "operation.registered",
    "operation.revised",
    "proposal.accepted",
    "proposal.corrected",
    "proposal.created",
    "proposal.rejected",
}

# L13. Three instruments over the same sites; their DISAGREEMENT is the finding.
REQUESTS_OWNERS = {
    "_proposal_bindings": 4,
    "_write_proposal_request_status": 2,
    "_persist_proposal": 1,
}
REQUESTS_OWNER_KIND = {
    "_proposal_bindings": "function",
    "_write_proposal_request_status": "function",
    "_persist_proposal": "method",
}
REQUESTS_VERBS = {"SELECT": 4, "UPDATE": 2, "INSERT": 1}
REQUESTS_WORD = re.compile(r"\brequests\b")
SQL_VERB = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b")

# L12/L14/L15. Byte identity against `da70a56`.
MODELS_SHA256 = "6dd45cfb6b078636dcdd8ae2d89b35603b727f53cc8ca32a3574647db0838289"
FROZEN_FILES = (f"{PACKAGE}/models.py", f"{PACKAGE}/store.py")
FROZEN_SPANS = ("propose", "submit_proposal", "get_proposal", "review", "resolve")


def _git_text(sha: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{sha}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _tracked_package_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", f"{PACKAGE}/*.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def _system_class(tree: ast.Module) -> ast.ClassDef:
    return next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "System"
    )


def _span(source: str, node: ast.FunctionDef) -> str:
    start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
    return "\n".join(source.splitlines()[start - 1 : node.end_lineno]).rstrip("\r\n")


def _event_kinds(tree: ast.Module) -> tuple[set[str], int, list[str]]:
    """Expand every `_event` call's `kind=` argument. An unrecognised form FAILS the check.

    Three spellings ship: a plain constant, an `IfExp` over two constants, and one `JoinedStr`
    whose interpolation is annotated `Literal[...]` inside its OWN function. A scan reading the
    first alone reports 13 of 16 and calls that a complete set.
    """
    kinds: set[str] = set()
    unsupported: list[str] = []
    calls = 0
    owners: dict[ast.AST, ast.FunctionDef] = {}
    for function in ast.walk(tree):
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(function):
                owners.setdefault(child, function)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        named = node.func.id if isinstance(node.func, ast.Name) else None
        if named != "_event":
            continue
        calls += 1
        argument = next(
            (keyword.value for keyword in node.keywords if keyword.arg == "kind"), None
        )
        expanded = _expand_kind(argument, owners.get(node))
        if expanded is None:
            unsupported.append(ast.dump(argument) if argument else "kind= missing")
            continue
        kinds |= expanded
    return kinds, calls, unsupported


def _expand_kind(node: ast.expr | None, owner: ast.FunctionDef | None) -> set[str] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.IfExp):
        branches = [_expand_kind(node.body, owner), _expand_kind(node.orelse, owner)]
        if any(branch is None for branch in branches):
            return None
        return set().union(*branches)
    if isinstance(node, ast.JoinedStr):
        prefix = ""
        alternatives: set[str] | None = None
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                prefix += part.value
                continue
            if not isinstance(part, ast.FormattedValue) or alternatives is not None:
                return None
            alternatives = _literal_alternatives(part.value, owner)
            if alternatives is None:
                return None
        if alternatives is None:
            return None
        return {f"{prefix}{value}" for value in alternatives}
    return None


def _literal_alternatives(node: ast.expr, owner: ast.FunctionDef | None) -> set[str] | None:
    """Resolve an interpolated name from its OWN lexical function, never module-wide."""
    if not isinstance(node, ast.Name) or owner is None:
        return None
    for statement in ast.walk(owner):
        if not isinstance(statement, ast.AnnAssign):
            continue
        if not isinstance(statement.target, ast.Name) or statement.target.id != node.id:
            continue
        annotation = statement.annotation
        if (
            isinstance(annotation, ast.Subscript)
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id == "Literal"
        ):
            elements = (
                annotation.slice.elts
                if isinstance(annotation.slice, ast.Tuple)
                else [annotation.slice]
            )
            values = {
                element.value
                for element in elements
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            }
            if len(values) == len(elements):
                return values
    return None


def check_dangling(sources: dict[str, str]) -> tuple[bool, str]:
    counts = dict.fromkeys(DANGLING, 0)
    dynamic: list[str] = []
    for relative, text in sources.items():
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.NAME and token.string in counts:
                counts[token.string] += 1
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in DYNAMIC or len(node.args) < 2:
                continue
            name = node.args[1]
            if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
                dynamic.append(f"{relative}:{node.lineno}")
    ok = counts == DANGLING and not dynamic
    return ok, f"names={counts} want={DANGLING} computed_attribute_names={dynamic}"


def check_models_import(current: ast.Module, baseline: ast.Module) -> tuple[bool, str]:
    def imported(tree: ast.Module) -> list[str]:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "models" and node.level == 1:
                return [alias.name for alias in node.names]
        return []

    before, after = imported(baseline), imported(current)
    dropped = set(before) - set(after)
    added = set(after) - set(before)
    ok = dropped == DROPPED_IMPORTS and not added
    return ok, f"dropped={sorted(dropped)} want={sorted(DROPPED_IMPORTS)} added={sorted(added)}"


def check_event_kinds(tree: ast.Module) -> tuple[bool, str]:
    kinds, calls, unsupported = _event_kinds(tree)
    request_prefixed = sorted(kind for kind in kinds if kind.startswith("request."))
    ok = kinds == EVENT_KINDS and not unsupported and not request_prefixed
    detail = (
        f"kinds={len(kinds)} calls={calls} unsupported={unsupported} "
        f"request_prefixed={request_prefixed} missing={sorted(EVENT_KINDS - kinds)} "
        f"extra={sorted(kinds - EVENT_KINDS)}"
    )
    return ok, detail


def check_requests_sites(source: str, tree: ast.Module) -> tuple[bool, str]:
    lines = [
        index
        for index, line in enumerate(source.splitlines(), start=1)
        if REQUESTS_WORD.search(line)
    ]
    multiplicity = {
        index: len(REQUESTS_WORD.findall(source.splitlines()[index - 1])) for index in lines
    }
    methods = {
        node.name
        for klass in tree.body
        if isinstance(klass, ast.ClassDef)
        for node in klass.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    owners: dict[str, int] = {}
    kinds: dict[str, str] = {}
    verbs: dict[str, int] = {}
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nested = {
            id(node)
            for inner in ast.walk(function)
            if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)) and inner is not function
            for node in ast.walk(inner)
        }
        for node in ast.walk(function):
            if id(node) in nested:
                continue
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            hits = len(REQUESTS_WORD.findall(node.value))
            if not hits:
                continue
            owners[function.name] = owners.get(function.name, 0) + hits
            kinds[function.name] = "method" if function.name in methods else "function"
            verb = SQL_VERB.search(node.value)
            if verb:
                verbs[verb.group(1)] = verbs.get(verb.group(1), 0) + hits
    ok = (
        len(lines) == 7
        and set(multiplicity.values()) == {1}
        and owners == REQUESTS_OWNERS
        and kinds == REQUESTS_OWNER_KIND
        and verbs == REQUESTS_VERBS
    )
    return ok, f"lines={len(lines)} multiplicity={sorted(set(multiplicity.values()))} owners={owners} kinds={kinds} verbs={verbs}"


def check_byte_identity(sources: dict[str, str]) -> tuple[bool, str]:
    findings: list[str] = []
    digest = hashlib.sha256(sources[f"{PACKAGE}/models.py"].encode()).hexdigest()
    if digest != MODELS_SHA256:
        findings.append(f"models.py sha256={digest}")
    for relative in FROZEN_FILES:
        if sources[relative] != _git_text(BASE_SHA, relative):
            findings.append(f"{relative} differs from {BASE_SHA}")
    exports = _all_names(sources[f"{PACKAGE}/__init__.py"])
    baseline_exports = _all_names(_git_text(BASE_SHA, f"{PACKAGE}/__init__.py"))
    if exports != baseline_exports:
        findings.append(f"__all__ moved: {len(exports)} names vs {len(baseline_exports)}")
    schema = [
        node.value.value
        for node in ast.parse(sources[f"{PACKAGE}/store.py"]).body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SCHEMA_VERSION" for t in node.targets)
        and isinstance(node.value, ast.Constant)
    ]
    if schema != [2]:
        findings.append(f"SCHEMA_VERSION={schema}")
    findings.extend(_span_findings(sources[SYSTEM], _git_text(BASE_SHA, SYSTEM)))
    return not findings, f"exports={len(exports)} findings={findings}"


def _all_names(source: str) -> list[str]:
    for node in ast.parse(source).body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            return [
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant)
            ]
    return []


def _span_findings(current: str, baseline: str) -> list[str]:
    findings: list[str] = []
    for source, label in ((current, "current"), (baseline, "baseline")):
        klass = _system_class(ast.parse(source))
        for name in FROZEN_SPANS:
            found = [
                node
                for node in klass.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name
            ]
            if len(found) != 1:
                findings.append(f"{label} {name} definitions={len(found)}")
            elif found[0].decorator_list:
                findings.append(f"{label} {name} decorated")
    if findings:
        return findings
    current_class, baseline_class = _system_class(ast.parse(current)), _system_class(
        ast.parse(baseline)
    )
    for name in FROZEN_SPANS:
        left = _span(current, next(n for n in current_class.body if getattr(n, "name", "") == name))
        right = _span(
            baseline, next(n for n in baseline_class.body if getattr(n, "name", "") == name)
        )
        if left != right:
            findings.append(f"{name} span differs ({len(left)} B vs {len(right)} B)")
    return findings


def grade(sources: dict[str, str]) -> int:
    system_tree = ast.parse(sources[SYSTEM])
    baseline_tree = ast.parse(_git_text(BASE_SHA, SYSTEM))
    checks = (
        ("L09 dangling_references", check_dangling(sources)),
        ("L10 models_import_delta", check_models_import(system_tree, baseline_tree)),
        ("L11 event_kind_vocabulary", check_event_kinds(system_tree)),
        ("L13 requests_site_inventory", check_requests_sites(sources[SYSTEM], system_tree)),
        ("L12/L14/L15 byte_identity", check_byte_identity(sources)),
    )
    failed = 0
    for label, (ok, detail) in checks:
        print(f"CHECK {label} {'ok' if ok else 'FAIL'} {detail}")
        failed += 0 if ok else 1
    print(f"RESULT: {'PASS' if not failed else 'FAIL'} ({failed}/{len(checks)} checks failed)")
    return 1 if failed else 0


def _read_sources() -> dict[str, str]:
    return {
        relative: (ROOT / relative).read_text(encoding="utf-8")
        for relative in _tracked_package_files()
    }


def self_test() -> int:
    """Every check must die under a mutation aimed at ITS OWN subject."""
    base = _read_sources()
    seeds: list[tuple[str, dict[str, str], str]] = []

    revived = dict(base)
    revived[SYSTEM] = revived[SYSTEM].replace(
        "    def propose(", "    def handle(self, request):\n        return None\n\n    def propose(", 1
    )
    seeds.append(("L09 a revived `handle` method", revived, "L09"))

    reimported = dict(base)
    reimported[SYSTEM] = reimported[SYSTEM].replace(
        "from .models import (", "from .models import (\n    Resolved,", 1
    )
    seeds.append(("L10 a restored `.models` import", reimported, "L10"))

    invented = dict(base)
    invented[SYSTEM] = invented[SYSTEM].replace(
        'kind="operation.registered"', 'kind="request.resolved_by_artifact"', 1
    )
    seeds.append(("L11 an invented event kind", invented, "L11"))

    opaque = dict(base)
    opaque[SYSTEM] = opaque[SYSTEM].replace(
        'kind="operation.registered"', "kind=_operation_kind()", 1
    )
    seeds.append(("L11 an unrecognised `kind=` form", opaque, "L11"))

    packed = dict(base)
    packed[SYSTEM] = packed[SYSTEM].replace(
        "UPDATE requests SET status = 'rejected'",
        "UPDATE requests SET status = 'rejected' -- requests",
        1,
    )
    seeds.append(("L13 a second `requests` reference on one line", packed, "L13"))

    edited = dict(base)
    edited[f"{PACKAGE}/models.py"] = edited[f"{PACKAGE}/models.py"] + "\n# drift\n"
    seeds.append(("L12 an edited `models.py`", edited, "L12"))

    decorated = dict(base)
    decorated[SYSTEM] = decorated[SYSTEM].replace(
        "    def resolve(", "    @staticmethod\n    def resolve(", 1
    )
    seeds.append(("L15 a decorated frozen span", decorated, "L15"))

    silent: list[str] = []
    for label, mutated, expected in seeds:
        if mutated == base:
            silent.append(f"{label} -> anchor missing, the seed edited nothing")
            continue
        buffer = io.StringIO()
        stdout, sys.stdout = sys.stdout, buffer
        try:
            grade(mutated)
        except SyntaxError:
            silent.append(f"{label} -> seed produced unparsable source")
            continue
        finally:
            sys.stdout = stdout
        red = [
            line
            for line in buffer.getvalue().splitlines()
            if line.startswith("CHECK") and " FAIL " in line and expected in line
        ]
        if not red:
            silent.append(f"{label} -> {expected} stayed green")

    buffer = io.StringIO()
    stdout, sys.stdout = sys.stdout, buffer
    try:
        clean = grade(base)
    finally:
        sys.stdout = stdout
    if clean != 0:
        silent.append(f"the unmutated tree does not grade PASS:\n{buffer.getvalue()}")

    for line in silent:
        print(f"SILENT: {line}")
    print(f"CONTROLS: {len(seeds) - len(silent)}/{len(seeds)} firing")
    print(f"RESULT: {'FAIL' if silent else 'PASS'}")
    return 1 if silent else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M3.6a2 gate 4 closure checks.")
    parser.add_argument("--self-test", action="store_true", help="grade the grader both ways")
    args = parser.parse_args(argv)
    return self_test() if args.self_test else grade(_read_sources())


if __name__ == "__main__":
    raise SystemExit(main())
