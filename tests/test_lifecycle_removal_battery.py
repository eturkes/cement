"""M3.6a2 acceptance battery — one test per obligation in `m3u6a2-contract.md` section 3.

Authored against the contract alone. Every test must be RED at `da70a56` unless its obligation
asserts a PRESERVED invariant (L12, L14, L15, L16, L17, L18), which is legitimately green there.

Regenerate the stub set with `.agent/decisions/m3u6a2-seed-battery.py`; grade coverage with
`.agent/decisions/m3u6a2-battery-validate.py`.
"""
import ast
from collections import Counter
import contextlib
import hashlib
import importlib
import inspect
import io
from itertools import product
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import tokenize
import unittest

from cement_runtime import Candidate, CompilePolicy, StateError, ValidationError
from cement_runtime.json_value import canonicalize
from cement_runtime.store import SCHEMA_VERSION
import cement_runtime.system as system_module
from cement_runtime.system import System


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PATH = ROOT / "src/cement_runtime/system.py"
BASE_SHA = "da70a56"

# D28 replays gate 1 at every revision and unlinks its own module from each checkout it grades,
# so the four frames below that reach INSTRUMENT find nothing there. The inner run announces
# itself and those frames narrow to what the checkout holds. Checked BOTH ways: an `is_file()`
# test alone would let a real deletion of the instrument narrow them instead of reddening them.
D28_INNER_REPLAY = "CEMENT_D28_INNER_REPLAY"
INSTRUMENT = "tests/test_migration_battery.py"


def instrument_pruned() -> bool:
    announced = os.environ.get(D28_INNER_REPLAY) == "1"
    present = (ROOT / INSTRUMENT).is_file()
    if announced == present:
        raise AssertionError(
            f"{D28_INNER_REPLAY} set={announced} contradicts {INSTRUMENT} present={present}"
        )
    return announced


def _git_bytes(revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def _git_text(revision: str, path: str) -> str:
    return _git_bytes(revision, path).decode()


def _system_tree(source: str | None = None) -> ast.Module:
    return ast.parse(SYSTEM_PATH.read_text() if source is None else source)


def _system_method(name: str, tree: ast.Module | None = None) -> ast.FunctionDef:
    tree = _system_tree() if tree is None else tree
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "System"]
    if len(classes) != 1:
        raise AssertionError(f"expected one System class, found {len(classes)}")
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(methods) != 1:
        raise AssertionError(f"expected one System.{name}, found {len(methods)}")
    return methods[0]


def _tracked_src_paths() -> tuple[Path, ...]:
    output = subprocess.run(
        ["git", "ls-files", "-z", "--", "src"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return tuple(ROOT / path.decode() for path in output.split(b"\0") if path)


def _raw_src_hits(needle: str) -> dict[str, int]:
    encoded = needle.encode()
    return {
        str(path.relative_to(ROOT)): count
        for path in _tracked_src_paths()
        if (count := path.read_bytes().count(encoded))
    }


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _nearest_function(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    parent = parents.get(node)
    while parent is not None and not isinstance(
        parent, (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        parent = parents.get(parent)
    return parent


def _lexical_nodes(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[ast.AST, ...]:
    nodes: list[ast.AST] = []

    class Visitor(ast.NodeVisitor):
        def visit(self, node: ast.AST) -> None:
            nodes.append(node)
            super().visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is function:
                self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node is function:
                self.generic_visit(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

    Visitor().visit(function)
    return tuple(nodes)


def _literal_annotation_values(annotation: ast.expr) -> tuple[str, ...] | None:
    if not isinstance(annotation, ast.Subscript):
        return None
    marker = annotation.value
    if not (
        (isinstance(marker, ast.Name) and marker.id == "Literal")
        or (isinstance(marker, ast.Attribute) and marker.attr == "Literal")
    ):
        return None
    elements = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
    if not all(
        isinstance(element, ast.Constant)
        and isinstance(element.value, str)
        and element.value
        for element in elements
    ):
        return None
    return tuple(element.value for element in elements)


def _expand_event_kind(
    expression: ast.expr,
    call: ast.Call,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    if isinstance(expression, ast.Constant):
        if isinstance(expression.value, str) and expression.value:
            return {expression.value}
        raise ValueError("Constant kind must be a non-empty string")
    if isinstance(expression, ast.IfExp):
        branches = (expression.body, expression.orelse)
        if all(
            isinstance(branch, ast.Constant)
            and isinstance(branch.value, str)
            and branch.value
            for branch in branches
        ):
            return {branch.value for branch in branches}
        raise ValueError("IfExp kind branches must be non-empty string constants")
    if not isinstance(expression, ast.JoinedStr):
        raise ValueError(f"unsupported kind form {type(expression).__name__}")

    choices: list[tuple[str, ...]] = []
    for part in expression.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            choices.append((part.value,))
            continue
        if not (
            isinstance(part, ast.FormattedValue)
            and isinstance(part.value, ast.Name)
            and part.conversion == -1
            and part.format_spec is None
        ):
            raise ValueError("JoinedStr kind has an unsupported interpolation")
        definitions = [
            node
            for node in _lexical_nodes(owner)
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == part.value.id
            and node.lineno < call.lineno
        ]
        if len(definitions) != 1:
            raise ValueError(
                f"{part.value.id} needs one dominating lexical annotation, found {len(definitions)}"
            )
        values = _literal_annotation_values(definitions[0].annotation)
        if values is None:
            raise ValueError(f"{part.value.id} must have a non-empty Literal annotation")
        choices.append(values)
    expanded = {"".join(parts) for parts in product(*choices)}
    if not expanded or "" in expanded:
        raise ValueError("JoinedStr kind expansion must be non-empty")
    return expanded


def _event_rows(tree: ast.Module) -> tuple[list[tuple[str, set[str]]], list[str]]:
    parents = _parents(tree)
    rows: list[tuple[str, set[str]]] = []
    errors: list[str] = []
    for call in (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_event"
    ):
        owner = _nearest_function(call, parents)
        kinds = [keyword.value for keyword in call.keywords if keyword.arg == "kind"]
        if owner is None or len(kinds) != 1:
            errors.append(f"line {call.lineno}: owner={owner is not None}, kind_args={len(kinds)}")
            continue
        try:
            rows.append((owner.name, _expand_event_kind(kinds[0], call, owner)))
        except ValueError as error:
            errors.append(f"line {call.lineno}: {error}")
    return rows, errors


class LifecycleRemovalBattery(unittest.TestCase):

    def test_l01_system_has_no_handle_attribute_under_every_access_route(self) -> None:
        """L01. `System` has no `handle` attribute under EVERY access route — `hasattr`, `getattr`, `dir()`, `inspect.getmembers` — neither `System` nor its metaclass defines `__getattr__`, and `system.py` holds no `FunctionDef` named `handle` at any scope. PLUS the structural subtraction (A01): the post-state `System` method-name set EQUALS its `da70a56` set minus exactly `{handle, request_status, _outcome, _fail_generation, _request_revision_is_current}`. A text predicate grades the spelling; only the set subtraction grades the subtraction, and renaming the 271-line body satisfies every text half."""

        import inspect

        from cement_runtime.system import System

        self.assertFalse(hasattr(System, "handle"))
        with self.assertRaises(AttributeError):
            getattr(System, "handle")
        self.assertNotIn("handle", dir(System))
        self.assertNotIn("handle", dict(inspect.getmembers(System)))
        self.assertNotIn("__getattr__", System.__dict__)
        self.assertNotIn("__getattr__", type(System).__dict__)

    def test_l01_no_functiondef_named_handle_at_any_scope(self) -> None:
        import ast
        from pathlib import Path

        source = (Path(__file__).parents[1] / "src/cement_runtime/system.py").read_text()
        self.assertFalse(
            any(isinstance(node, ast.FunctionDef) and node.name == "handle" for node in ast.walk(ast.parse(source)))
        )

    def test_l01_system_method_set_is_exact_baseline_subtraction(self) -> None:
        import ast
        from pathlib import Path
        import subprocess

        root = Path(__file__).parents[1]
        current = ast.parse((root / "src/cement_runtime/system.py").read_text())
        baseline = ast.parse(
            subprocess.run(
                ["git", "show", "da70a56:src/cement_runtime/system.py"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )

        def system_methods(tree: ast.Module) -> set[str]:
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "System"]
            self.assertEqual(len(classes), 1)
            return {node.name for node in classes[0].body if isinstance(node, ast.FunctionDef)}

        removed = {"handle", "request_status", "_outcome", "_fail_generation", "_request_revision_is_current"}
        self.assertEqual(system_methods(current), system_methods(baseline) - removed)

    def test_l02_system_has_no_request_status_attribute_under_the_same_four(self) -> None:
        """L02. `System` has no `request_status` attribute under the same four routes and no `FunctionDef` named `request_status` at any scope. The surviving `_ProposalBinding.request_status` field and the six other proposal-plumbing identifiers are a DIFFERENT subject and must remain (X01, L15)."""

        self.assertFalse(hasattr(System, "request_status"))
        with self.assertRaises(AttributeError):
            getattr(System, "request_status")
        self.assertNotIn("request_status", dir(System))
        self.assertNotIn("request_status", dict(inspect.getmembers(System)))

    def test_l02_no_functiondef_named_request_status_at_any_scope(self) -> None:
        self.assertFalse(
            any(
                isinstance(node, ast.FunctionDef) and node.name == "request_status"
                for node in ast.walk(_system_tree())
            )
        )

    def test_l03_system_has_no__outcome__fail_generation_or(self) -> None:
        """L03. `System` has no `_outcome`, `_fail_generation` or `_request_revision_is_current` attribute, and `system.py` holds zero `FunctionDef` of each name at any scope — module level, class body and nested closure alike (V02)."""

        names = ("_outcome", "_fail_generation", "_request_revision_is_current")
        members = dict(inspect.getmembers(System))
        for name in names:
            with self.subTest(name=name):
                self.assertFalse(hasattr(System, name))
                with self.assertRaises(AttributeError):
                    getattr(System, name)
                self.assertNotIn(name, dir(System))
                self.assertNotIn(name, members)

    def test_l03_no_private_lifecycle_functiondefs_at_any_scope(self) -> None:
        forbidden = {"_outcome", "_fail_generation", "_request_revision_is_current"}
        found = {
            node.name
            for node in ast.walk(_system_tree())
            if isinstance(node, ast.FunctionDef) and node.name in forbidden
        }
        self.assertEqual(found, set())

    def test_l04_system___init___s_signature_is_exactly_self_database(self) -> None:
        """L04. `System.__init__`'s signature is exactly `self, database, *, candidate_source, clock_us`. `System(db, generation_lease_seconds=1)` raises `TypeError`. Derive the parameter list from `inspect.signature`, never from source text."""

        parameters = tuple(inspect.signature(System.__init__).parameters.values())
        self.assertEqual(
            tuple((parameter.name, parameter.kind) for parameter in parameters),
            (
                ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                ("database", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                ("candidate_source", inspect.Parameter.KEYWORD_ONLY),
                ("clock_us", inspect.Parameter.KEYWORD_ONLY),
            ),
        )

    def test_l04_generation_lease_keyword_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            database = Path(directory) / "cement.db"
            with self.assertRaises(TypeError):
                System(database, generation_lease_seconds=1)

    def test_l05__lease_us_has_zero_raw_byte_occurrences_across_the_git(self) -> None:
        """L05. `_lease_us` has zero RAW BYTE occurrences across the git-tracked `src/` file set — the contract says occurrences, so strings, comments and docstrings count, and git-tracked scope excludes `__pycache__` (V05). Baseline 5, all in `system.py` at 702, 709, 1099, 1110, 1235. Token absence alone is satisfied by a rename, so L05 carries the AST SHAPE pin that a rename cannot (A03): `_now`'s comparator is exactly `now > _MAX_SQLITE_INTEGER` — the right operand is a bare `Name`, not a `BinOp` — and `__init__` binds no attribute whose value derives from a lease parameter. `generation_lease_seconds` likewise reaches zero raw occurrences across tracked `src/` (X03; baseline 5), since `inspect.signature` cannot see a dead literal or comment."""

        self.assertEqual(_raw_src_hits("_lease_us"), {})

    def test_l05_now_upper_bound_is_bare_sqlite_maximum(self) -> None:
        method = _system_method("_now")
        upper_bounds = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "now"
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Gt)
        ]
        self.assertEqual(len(upper_bounds), 1)
        self.assertIsInstance(upper_bounds[0].comparators[0], ast.Name)
        self.assertEqual(upper_bounds[0].comparators[0].id, "_MAX_SQLITE_INTEGER")

    def test_l05_init_binds_no_attribute_derived_from_removed_parameter(self) -> None:
        method = _system_method("__init__")
        parameters = {
            argument.arg
            for argument in (
                *method.args.posonlyargs,
                *method.args.args,
                *method.args.kwonlyargs,
            )
        }
        tainted = parameters - {"self", "database", "candidate_source", "clock_us"}
        derived_attributes: set[str] = set()
        assignments = [
            node
            for node in ast.walk(method)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        changed = True
        while changed:
            changed = False
            for assignment in assignments:
                value = assignment.value
                if value is None or not any(
                    isinstance(node, ast.Name) and node.id in tainted
                    for node in ast.walk(value)
                ):
                    continue
                targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in tainted:
                        tainted.add(target.id)
                        changed = True
                    elif (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        derived_attributes.add(target.attr)
        self.assertEqual(derived_attributes, set())

    def test_l05_generation_lease_seconds_has_zero_raw_src_occurrences(self) -> None:
        self.assertEqual(_raw_src_hits("generation_lease_seconds"), {})

    def test_l06__now_s_upper_bound_carries_no_lease_term_a_clock_returning(self) -> None:
        """L06. `_now`'s upper bound carries no lease term: a clock returning `_MAX_SQLITE_INTEGER` is ACCEPTED and reaches a real write, `_MAX_SQLITE_INTEGER + 1` is REJECTED, and the `StateError` message is EXACTLY `clock must return a signed 64-bit microsecond timestamp`. Probe both sides of the boundary in one test so the assertion cannot pass by rejecting everything. The positive text pin is MAIN's own wording, not a diff-blind paraphrase, and it exists because a forbidden-substring predicate cannot see a silent re-wording (V07, V22). The dead `lease-safe` literal must also be absent from tracked `src/` (X27)."""

        message = "clock must return a signed 64-bit microsecond timestamp"
        maximum = system_module._MAX_SQLITE_INTEGER
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            accepted_database = Path(directory) / "accepted.db"
            accepted = System(accepted_database, clock_us=lambda: maximum)
            accepted_error: Exception | None = None
            accepted_revision: int | None = None
            try:
                accepted_revision = accepted.register_operation("partition", "operation")
            except Exception as error:
                accepted_error = error
            self.assertIsNone(accepted_error)
            self.assertEqual(accepted_revision, 1)
            with accepted.store.transaction() as connection:
                row = connection.execute(
                    "SELECT created_at_us, updated_at_us FROM operations"
                ).fetchone()
            self.assertEqual(tuple(row), (maximum, maximum))

            rejected_database = Path(directory) / "rejected.db"
            rejected = System(rejected_database, clock_us=lambda: maximum + 1)
            with self.assertRaises(StateError) as raised:
                rejected.register_operation("partition", "operation")
            self.assertEqual(str(raised.exception), message)

    def test_l06_lease_safe_literal_has_zero_raw_src_occurrences(self) -> None:
        self.assertEqual(_raw_src_hits("lease-safe"), {})

    def test_l07_revise_operation_performs_no_requests_write_the_source(self) -> None:
        """L07. `revise_operation` performs no `requests` write. The source half scans AST string constants case-insensitively and rejects every spelling — `UPDATE`/`update`, arbitrary whitespace, a multiline split, and `` `requests` ``, `"requests"`, `[requests]`, `main.requests`, `temp.requests` (V10). The behavioural half executes a revision while a `generating` request row exists at the previous revision and asserts that row's `status`, `error_code`, `lease_owner` and `lease_until_us` are unchanged. THAT ROW IS FABRICATED LEGACY STATE and is labelled as such: after this unit no supported route produces `generating`, so the probe seeds it through `Store.transaction(write=True)`, modelling a ledger left by an older release at surviving schema v2 (V09, X28). The probe MUST assert the row exists at `status='generating'` BEFORE the revision — a zero-row UPDATE raises nothing, so an unguarded preservation probe is green-and-empty rather than red (A05)."""

        table = r'(?:requests\b|`requests`|"requests"|\[requests\])'
        qualifier = r'(?:(?:main|temp)\s*\.\s*)?'
        write = re.compile(
            rf'\b(?:update|insert\s+(?:or\s+\w+\s+)?into|delete\s+from|replace\s+into)\s+{qualifier}{table}',
            re.IGNORECASE | re.DOTALL,
        )
        strings = [
            node.value
            for node in ast.walk(_system_method("revise_operation"))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        self.assertEqual([value for value in strings if write.search(value)], [])

    def test_l07_fabricated_legacy_generating_row_survives_revision(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            database = Path(directory) / "cement.db"
            old_process = System(database, clock_us=lambda: 100)
            old_process.register_operation("partition", "operation", policy=CompilePolicy())
            with old_process.store.transaction(write=True) as connection:
                connection.execute(
                    """
                    INSERT INTO requests(
                        id, partition, operation, operation_revision,
                        input_json, input_hash, status, lease_owner,
                        lease_until_us, created_at_us, updated_at_us
                    ) VALUES (?, ?, ?, ?, ?, ?, 'generating', ?, ?, ?, ?)
                    """,
                    (
                        "legacy-request",
                        "partition",
                        "operation",
                        1,
                        "{}",
                        "legacy-input-hash",
                        "old-process",
                        999,
                        10,
                        10,
                    ),
                )
            selection = (
                "SELECT status, error_code, lease_owner, lease_until_us "
                "FROM requests WHERE partition = ? AND id = ?"
            )
            identity = ("partition", "legacy-request")
            with old_process.store.transaction() as connection:
                before = connection.execute(selection, identity).fetchone()
            self.assertIsNotNone(before)
            self.assertEqual(tuple(before), ("generating", None, "old-process", 999))

            reopened = System(database, clock_us=lambda: 200)
            reopened.revise_operation(
                "partition",
                "operation",
                policy=CompilePolicy(),
                revised_by="revision-actor",
            )
            with reopened.store.transaction() as connection:
                after = connection.execute(selection, identity).fetchone()
            self.assertEqual(tuple(after), tuple(before))

    def test_l08_the_operation_revised_event_payload_read_back_from_the(self) -> None:
        """L08. the `operation.revised` event payload, read back from the persisted `events.payload_json`, has EXACTLY the keys `previous_revision`, `policy_hash`, `revised_by` AND each key's VALUE is bound: `previous_revision` == the operation's pre-revision integer, `policy_hash` == the canonical policy digest, `revised_by` == the actor the caller supplied. Assert the whole key set, not the absence of one key, and assert the values, not just the keys: a three-key set assertion passes while all three values are wrong (A06), and `revise_operation` returns only the new revision, so the return value cannot evidence the payload. This payload had zero pins before this unit. `invalidated_generators` additionally reaches zero RAW occurrences across tracked `src/` — baseline 3, being one assignment, one payload key STRING and one value identifier, which is why the census's `2` (NAME tokens) is not the closure number (X04)."""

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            database = Path(directory) / "cement.db"
            system = System(database, clock_us=iter((100, 200)).__next__)
            system.register_operation("partition", "operation", policy=CompilePolicy())
            revised_policy = CompilePolicy(4, 3, 86_400)
            pre_revision = 1
            actor = "revision-actor"
            self.assertEqual(
                system.revise_operation(
                    "partition",
                    "operation",
                    policy=revised_policy,
                    revised_by=actor,
                ),
                pre_revision + 1,
            )
            with system.store.transaction() as connection:
                rows = connection.execute(
                    "SELECT payload_json FROM events WHERE kind = 'operation.revised'"
                ).fetchall()
            self.assertEqual(len(rows), 1)
            payload = json.loads(rows[0]["payload_json"])
            self.assertEqual(
                payload,
                {
                    "previous_revision": pre_revision,
                    "policy_hash": canonicalize(
                        revised_policy.as_json(), max_bytes=16_384
                    ).digest,
                    "revised_by": actor,
                },
            )

    def test_l08_invalidated_generators_has_zero_raw_src_occurrences(self) -> None:
        self.assertEqual(_raw_src_hits("invalidated_generators"), {})

    def test_l09_zero_dangling_references_counted_as_tokenize_name_equality(self) -> None:
        """L09. zero dangling references, counted as `tokenize` NAME equality over tracked `src/` `.py` files so `handler` and `unhandled` never count. The expected post-state vector is `{handle: 0, request_status: 7, _outcome: 0, _fail_generation: 0, _request_revision_is_current: 0, _lease_us: 0}` (X02, X24; baseline `1, 8, 7, 4, 4, 5`). `request_status` IS NOT ZERO and cannot be: MAIN measured eight identifiers at `da70a56`, of which deleting the method removes line 1546 alone, leaving SEVEN proposal-plumbing identifiers at 458, 503, 1529, 1532, 1535, 1542 and 1579 — the last inside `get_proposal`, which L15 freezes byte-for-byte. The original `zero occurrences` reading was false-by-construction against L15 and is corrected by C09; L02 carries the `System`-attribute claim instead. Dynamic reach is closed by a bounded, MEASURED pin (A07): tracked `src/` holds ZERO `getattr`/`setattr`/`hasattr`/`delattr` calls whose name argument is not a string `Constant`, which rejects `getattr(self, '_out' + 'come')` by construction. Count over the whole package, not over `system.py`."""

        expected = {
            "handle": 0,
            "request_status": 7,
            "_outcome": 0,
            "_fail_generation": 0,
            "_request_revision_is_current": 0,
            "_lease_us": 0,
        }
        counts = dict.fromkeys(expected, 0)
        trees: list[tuple[str, ast.Module]] = []
        for path in _tracked_src_paths():
            if path.suffix != ".py":
                continue
            source = path.read_text()
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.NAME and token.string in counts:
                    counts[token.string] += 1
            trees.append((str(path.relative_to(ROOT)), ast.parse(source)))
        self.assertEqual(counts, expected)

        dynamic_calls: list[tuple[str, int, str]] = []
        dispatchers = {"getattr", "setattr", "hasattr", "delattr"}
        for relative, tree in trees:
            for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
                if isinstance(call.func, ast.Name):
                    dispatcher = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    dispatcher = call.func.attr
                else:
                    continue
                if dispatcher not in dispatchers:
                    continue
                name_argument = call.args[1] if len(call.args) > 1 else None
                if not (
                    isinstance(name_argument, ast.Constant)
                    and isinstance(name_argument.value, str)
                ):
                    dynamic_calls.append((relative, call.lineno, dispatcher))
        self.assertEqual(dynamic_calls, [])

    def test_l10_system_py_s_from_models_import_list_loses_exactly(self) -> None:
        """L10. `system.py`'s `from .models import (...)` list loses exactly `FallbackFailed`, `InProgress`, `Outcome`, `ReconciliationRequired`, `Rejected`, `Resolved`, `ReviewRequired` — seven names — and no other import moves. Compare the parsed import list, not the source text."""

        def model_imports(tree: ast.Module) -> tuple[tuple[str, str | None], ...]:
            imports = [
                node
                for node in tree.body
                if isinstance(node, ast.ImportFrom)
                and node.level == 1
                and node.module == "models"
            ]
            self.assertEqual(len(imports), 1)
            return tuple((alias.name, alias.asname) for alias in imports[0].names)

        baseline = model_imports(_system_tree(_git_text(BASE_SHA, "src/cement_runtime/system.py")))
        removed = {
            "FallbackFailed",
            "InProgress",
            "Outcome",
            "ReconciliationRequired",
            "Rejected",
            "Resolved",
            "ReviewRequired",
        }
        expected = tuple(alias for alias in baseline if alias[0] not in removed)
        self.assertEqual(model_imports(_system_tree()), expected)

    def test_l11_the_emitted_event_kind_vocabulary_is_exactly_the_sixteen(self) -> None:
        """L11. the emitted event-kind vocabulary is EXACTLY the SIXTEEN surviving kinds — `artifact.challenged`, `artifact.compiled`, `artifact.counterexample`, `artifact.integrity_quarantined`, `artifact.promoted`, `artifact.suspended`, `artifact.verification_failed`, `artifact.verified`, `example.revoked`, `function.promoted`, `operation.registered`, `operation.revised`, `proposal.accepted`, `proposal.corrected`, `proposal.created`, `proposal.rejected` — and the `request.` prefix is gone from the namespace. Assert the whole SET, not the absence of the deleted kinds: an absence assertion passes while a further kind is invented, and the project's own rule is to pin the complete vector rather than a derivative of it. Corrected by C05; the count and three of the members moved. THE DERIVATION IS TOTAL, NOT BEST-EFFORT (A09, X05): every `_event` call's `kind` argument must match one of the three ruled AST forms and must expand non-empty, and an unsupported form FAILS the check rather than being skipped. Set equality alone stays green when a fourth form (`kind=event_kind`) ships a new runtime kind, because the recognized set is unchanged. THE VOCABULARY HAS THREE SPELLINGS AND A RULE READING ONE IS BLIND TO THE REST. Every event is written by the module-level `_event(connection, *, kind=..., ...)` helper (`system.py:380`), called NINETEEN times at `da70a56` — 16 `Constant`, 2 `IfExp`, 1 `JoinedStr`, falling to FOURTEEN post-state — and its `kind` argument takes three forms: a plain string constant; an `IfExp` whose two branches are both constants (`kind="artifact.verified" if passed else "artifact.verification_failed"` at `_verify_row:4065`, `kind="artifact.counterexample" if suspended else "artifact.challenged"` at `challenge:5129`); and one `JoinedStr`, `kind=f"proposal.{proposal_status}"` at `review:1881`, whose interpolation is annotated `Literal["accepted", "corrected"]` at `system.py:1770` and is resolved from THAT lexical function, never from a module-wide same-name search (X29). Derive the set from all three; a scan reading only the first reports 13 of the 16 and is what C05 corrects. C05's own supporting count of `20` was wrong and is corrected by C08: 19 static calls, the textual `_event(` count of 20 including the DEFINITION line. The 16-kind SET is unaffected because it was derived per call site, and the call count is REPORTED separately rather than used as a completeness control. Each of the three removed kinds loses its unique producer independently (X32). THREE KINDS LOSE THEIR ONLY PRODUCER HERE, not two. `request.resolved_by_artifact` (`handle:1208`), `request.fallback_failed` (`_fail_generation:1356`) AND `artifact.ambiguity_quarantined` (`handle:1143`) are each emitted at exactly one site, all three inside deleted spans. Ambiguity quarantine is therefore a behaviour this unit removes, which section 2's deletion set and the prose census both now record."""

        baseline_rows, baseline_errors = _event_rows(
            _system_tree(_git_text(BASE_SHA, "src/cement_runtime/system.py"))
        )
        self.assertEqual(baseline_errors, [])
        deleted_owners = {
            "handle",
            "request_status",
            "_outcome",
            "_fail_generation",
            "_request_revision_is_current",
        }
        expected = {
            kind
            for owner, kinds in baseline_rows
            if owner not in deleted_owners
            for kind in kinds
        }
        self.assertEqual(len(expected), 16)

        current_rows, current_errors = _event_rows(_system_tree())
        self.assertEqual(current_errors, [])
        current = {kind for _, kinds in current_rows for kind in kinds}
        self.assertEqual(current, expected)
        self.assertFalse(any(kind.startswith("request.") for kind in current))

    def test_l11_each_unique_deleted_event_producer_is_absent(self) -> None:
        baseline_rows, baseline_errors = _event_rows(
            _system_tree(_git_text(BASE_SHA, "src/cement_runtime/system.py"))
        )
        self.assertEqual(baseline_errors, [])
        deleted_owners = {
            "handle",
            "request_status",
            "_outcome",
            "_fail_generation",
            "_request_revision_is_current",
        }
        totals = Counter(
            kind for _, kinds in baseline_rows for kind in kinds
        )
        unique_deleted = {
            kind
            for owner, kinds in baseline_rows
            if owner in deleted_owners
            for kind in kinds
            if totals[kind] == 1
        }
        self.assertEqual(len(unique_deleted), 3)
        current_rows, current_errors = _event_rows(_system_tree())
        self.assertEqual(current_errors, [])
        current = {kind for _, kinds in current_rows for kind in kinds}
        self.assertEqual(current & unique_deleted, set())

    def test_l12_src_cement_runtime_models_py_is_byte_identical_to_its(self) -> None:
        """L12. `src/cement_runtime/models.py` is byte-identical to its `da70a56` blob (sha256 `6dd45cfb6b078636dcdd8ae2d89b35603b727f53cc8ca32a3574647db0838289`) and `src/cement_runtime/__init__.py`'s `__all__` — compared as the PARSED ordered list of 57 names, not as source text — is unchanged (V16). PLUS binding identity (A08): each of the six exported model names resolves in `cement_runtime` to the SAME OBJECT as in `cement_runtime.models`, which an aliasing re-export (`from .models import Resolved as _Resolved`) breaks while `__all__` stays AST-equal. The post-state vector is six names at `(models=True, __all__=True, package=True, system=False)` and `Outcome` at `(True, False, False, False)` — SEVEN definitions, SIX exports (X06, X34, C10). The models survive without producers; deleting them is M3.6a3's and doing it here would take that unit's measurement with it."""

        path = ROOT / "src/cement_runtime/models.py"
        baseline = _git_bytes(BASE_SHA, "src/cement_runtime/models.py")
        self.assertEqual(
            hashlib.sha256(baseline).hexdigest(),
            "6dd45cfb6b078636dcdd8ae2d89b35603b727f53cc8ca32a3574647db0838289",
        )
        self.assertEqual(path.read_bytes(), baseline)

    def test_l12_package_all_is_the_same_ordered_57_name_list(self) -> None:
        def parsed_all(source: str) -> tuple[str, ...]:
            tree = ast.parse(source)
            assignments = [
                node
                for node in tree.body
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in (
                        node.targets if isinstance(node, ast.Assign) else [node.target]
                    )
                )
            ]
            self.assertEqual(len(assignments), 1)
            value = ast.literal_eval(assignments[0].value)
            self.assertIsInstance(value, (list, tuple))
            self.assertTrue(all(isinstance(name, str) for name in value))
            return tuple(value)

        baseline = parsed_all(_git_text(BASE_SHA, "src/cement_runtime/__init__.py"))
        self.assertEqual(len(baseline), 57)
        current = parsed_all((ROOT / "src/cement_runtime/__init__.py").read_text())
        self.assertEqual(current, baseline)

    def test_l12_six_package_exports_are_identical_model_bindings(self) -> None:
        import cement_runtime
        import cement_runtime.models as models

        names = (
            "FallbackFailed",
            "InProgress",
            "ReconciliationRequired",
            "Rejected",
            "Resolved",
            "ReviewRequired",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(cement_runtime, name), getattr(models, name))

    def test_l12_post_state_model_definition_export_import_vector(self) -> None:
        import cement_runtime
        import cement_runtime.models as models

        exported = (
            "FallbackFailed",
            "InProgress",
            "ReconciliationRequired",
            "Rejected",
            "Resolved",
            "ReviewRequired",
        )
        vector = {
            name: (
                hasattr(models, name),
                name in cement_runtime.__all__,
                hasattr(cement_runtime, name),
                hasattr(system_module, name),
            )
            for name in (*exported, "Outcome")
        }
        self.assertEqual(
            vector,
            {
                **{name: (True, True, True, False) for name in exported},
                "Outcome": (True, False, False, False),
            },
        )

    def test_l13_the_surviving_requests_sites_in_system_py_are_exactly(self) -> None:
        """L13. the surviving `requests` sites in `system.py` are exactly SEVEN — `_proposal_bindings` 4, `_write_proposal_request_status` 2, `_persist_proposal` 1 — pinned by THREE instruments whose disagreement is the finding: hit LINES (7), standalone WORD occurrences (7, per-line multiplicity 1, so a second reference cannot be packed onto an existing line — X20), and parsed SQL string CONSTANTS with their verbs (`SELECT` x4, `UPDATE` x2, `INSERT` x1), which excludes comments and docstrings and follows a statement moved to a new line (X30). Ownership binds to the NEAREST lexical `FunctionDef`, never to an outer `ast.walk`, and the pin compares the exact multiset `{owner: count}` PLUS owner KIND, so a site relocated into a newly nested helper fails instead of being attributed to the expected outer function (A12). Corrected by C04 from `eleven`, which contradicted section 1's own inventory. Corrected again by C09: `_proposal_bindings` and `_write_proposal_request_status` are module-level FUNCTIONS but `_persist_proposal` is a `System` METHOD, so a class-body-only scan sees ONE surviving site, not zero."""

        source = SYSTEM_PATH.read_text()
        hits = [
            (line_number, len(re.findall(r"\brequests\b", line)))
            for line_number, line in enumerate(source.splitlines(), 1)
            if re.search(r"\brequests\b", line)
        ]
        self.assertEqual(
            (len(hits), sum(count for _, count in hits), {count for _, count in hits}),
            (7, 7, {1}),
        )

    def test_l13_requests_sql_constants_have_exact_verbs_and_nearest_owners(self) -> None:
        def sql_rows(tree: ast.Module) -> list[tuple[str, str, str, int]]:
            parents = _parents(tree)
            rows: list[tuple[str, str, str, int]] = []
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and re.search(r"\brequests\b", node.value, re.IGNORECASE)
                ):
                    continue
                verb = re.search(
                    r"\b(SELECT|INSERT|UPDATE|DELETE|REPLACE)\b",
                    node.value,
                    re.IGNORECASE,
                )
                if verb is None:
                    continue
                owner = _nearest_function(node, parents)
                self.assertIsNotNone(owner)
                container = parents.get(owner)
                if isinstance(container, ast.Module):
                    owner_kind = "function"
                elif (
                    isinstance(container, ast.ClassDef)
                    and container.name == "System"
                ):
                    owner_kind = "method"
                else:
                    owner_kind = "nested"
                rows.append(
                    (
                        owner_kind,
                        owner.name,
                        verb.group(1).upper(),
                        len(re.findall(r"\brequests\b", node.value, re.IGNORECASE)),
                    )
                )
            return rows

        deleted_owners = {
            "handle",
            "request_status",
            "_outcome",
            "_fail_generation",
            "_request_revision_is_current",
            "revise_operation",
        }
        baseline = sql_rows(_system_tree(_git_text(BASE_SHA, "src/cement_runtime/system.py")))
        expected = sorted(row for row in baseline if row[1] not in deleted_owners)
        self.assertEqual(len(expected), 7)
        self.assertTrue(all(row[3] == 1 for row in expected))
        self.assertEqual(sorted(sql_rows(_system_tree())), expected)

    def test_l14_schema_version_stays_2_and_src_cement_runtime_store_py_is(self) -> None:
        """L14. `SCHEMA_VERSION` stays 2 and `src/cement_runtime/store.py` is byte-identical to its `da70a56` blob."""

        self.assertEqual(SCHEMA_VERSION, 2)
        self.assertEqual(
            (ROOT / "src/cement_runtime/store.py").read_bytes(),
            _git_bytes(BASE_SHA, "src/cement_runtime/store.py"),
        )

    def test_l15_propose_submit_proposal_get_proposal_review_and_resolve(self) -> None:
        """L15. `propose`, `submit_proposal`, `get_proposal`, `review` and `resolve` are byte-identical to their `da70a56` spans, under the whole-line `lineno..end_lineno` convention with trailing newlines stripped. That convention is M3.3's P06 convention; a column-offset slice measures four bytes shorter and is a different claim. TWO PRECONDITIONS BIND BEFORE THE COMPARISON. First, definition CARDINALITY: exactly one `FunctionDef` per name, asserted first, because a name-keyed span map silently drops a duplicate and compares the base-identical copy while Python binds the other (X36). Second, the span STARTS AT `min(decorator lineno, def lineno)` and the baseline decorator vector — EMPTY for all five — is asserted: `FunctionDef.lineno` points at `def`, so adding `@staticmethod` leaves every compared byte identical while changing the runtime binding (A13)."""

        names = ("propose", "submit_proposal", "get_proposal", "review", "resolve")
        baseline_source = _git_text(BASE_SHA, "src/cement_runtime/system.py")
        current_source = SYSTEM_PATH.read_text()
        baseline_tree = _system_tree(baseline_source)
        current_tree = _system_tree(current_source)

        def definitions(
            tree: ast.Module, name: str
        ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
            return [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name
            ]

        baseline_nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        current_nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        for name in names:
            baseline_definitions = definitions(baseline_tree, name)
            current_definitions = definitions(current_tree, name)
            self.assertEqual(len(baseline_definitions), 1, name)
            self.assertEqual(len(current_definitions), 1, name)
            baseline_nodes[name] = baseline_definitions[0]
            current_nodes[name] = current_definitions[0]

        empty_decorators = {name: () for name in names}
        baseline_decorators = {
            name: tuple(ast.unparse(decorator) for decorator in node.decorator_list)
            for name, node in baseline_nodes.items()
        }
        current_decorators = {
            name: tuple(ast.unparse(decorator) for decorator in node.decorator_list)
            for name, node in current_nodes.items()
        }
        self.assertEqual(baseline_decorators, empty_decorators)
        self.assertEqual(current_decorators, baseline_decorators)

        def whole_line_span(
            source: str, node: ast.FunctionDef | ast.AsyncFunctionDef
        ) -> str:
            start = min(
                [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
            )
            return "\n".join(source.splitlines()[start - 1 : node.end_lineno])

        for name in names:
            with self.subTest(name=name):
                self.assertEqual(
                    whole_line_span(current_source, current_nodes[name]),
                    whole_line_span(baseline_source, baseline_nodes[name]),
                )

    def test_l16_the_proposal_round_trip_still_ends_with_the_private(self) -> None:
        """L16. the proposal round trip still ends with the private request row `resolved`: propose, review-accept, then read the row through the store and assert `status = 'resolved'` with its `output_json` and `example_id` set. The row must be the CONFIRMED variant — `source_kind = 'confirmed'`, `artifact_id` NULL, `proposal_id` bound to the reviewed proposal, `example_id` bound to the `ReviewResult` — or the three named fields pass on a malformed artifact-shaped row (X35). A REJECT round trip is required beside it (A14): `_write_proposal_request_status` has a dedicated rejection branch that the accept path never executes, so an accept-only probe leaves half the helper unobserved and the claim `this is the probe that proves it` false for that half."""

        class Source:
            def propose(self, request):
                return Candidate(
                    output={"echo": request.input},
                    provenance={"source": "lifecycle-battery"},
                )

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            system = System(
                Path(directory) / "cement.db",
                candidate_source=Source(),
                clock_us=iter(range(10, 100)).__next__,
            )
            system.register_operation("partition", "operation", policy=CompilePolicy())
            proposal_id = system.propose("partition", "operation", {"x": 1})
            result = system.review(
                "partition",
                proposal_id,
                reviewer="accept-reviewer",
                decision="accept",
            )
            with system.store.transaction() as connection:
                row = connection.execute(
                    """
                    SELECT r.status, r.output_json, r.example_id, r.source_kind,
                           r.artifact_id, r.proposal_id
                    FROM requests AS r
                    JOIN proposals AS p
                      ON p.partition = r.partition AND p.request_id = r.id
                    WHERE p.partition = ? AND p.id = ?
                    """,
                    ("partition", proposal_id),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "resolved")
            self.assertEqual(json.loads(row["output_json"]), {"echo": {"x": 1}})
            self.assertEqual(row["example_id"], result.example_id)
            self.assertEqual(row["source_kind"], "confirmed")
            self.assertIsNone(row["artifact_id"])
            self.assertEqual(row["proposal_id"], proposal_id)

    def test_l16_rejected_proposal_writes_the_private_rejected_variant(self) -> None:
        class Source:
            def propose(self, request):
                return Candidate(output=request.input, provenance={})

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            system = System(
                Path(directory) / "cement.db",
                candidate_source=Source(),
                clock_us=iter(range(100, 200)).__next__,
            )
            system.register_operation("partition", "operation", policy=CompilePolicy())
            proposal_id = system.propose("partition", "operation", {"x": 2})
            result = system.review(
                "partition",
                proposal_id,
                reviewer="reject-reviewer",
                decision="reject",
            )
            self.assertEqual(result.status, "rejected")
            with system.store.transaction() as connection:
                row = connection.execute(
                    """
                    SELECT r.status, r.output_json, r.source_kind, r.artifact_id,
                           r.proposal_id, r.example_id, r.error_code,
                           r.lease_owner, r.lease_until_us
                    FROM requests AS r
                    JOIN proposals AS p
                      ON p.partition = r.partition AND p.request_id = r.id
                    WHERE p.partition = ? AND p.id = ?
                    """,
                    ("partition", proposal_id),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(
                tuple(row),
                (
                    "rejected",
                    None,
                    None,
                    None,
                    proposal_id,
                    None,
                    None,
                    None,
                    None,
                ),
            )

    def test_l17_revise_operation_still_bumps_the_revision_by_one_and_still(self) -> None:
        """L17. `revise_operation` still bumps the revision by one and still retires `draft`, `verified` and `promoted` artifacts at the previous revision with `status_reason = 'operation revised'`."""

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            system = System(
                Path(directory) / "cement.db",
                clock_us=iter((100, 200)).__next__,
            )
            self.assertEqual(
                system.register_operation(
                    "partition", "operation", policy=CompilePolicy()
                ),
                1,
            )
            columns = (
                "id",
                "partition",
                "operation",
                "operation_revision",
                "input_json",
                "input_hash",
                "output_json",
                "output_hash",
                "artifact_json",
                "artifact_hash",
                "scope_hash",
                "build_hash",
                "policy_json",
                "policy_hash",
                "evidence_snapshot_hash",
                "status",
                "support",
                "reviewer_count",
                "span_seconds",
                "created_at_us",
                "verified_report_id",
                "promoted_by",
                "promoted_at_us",
                "promotion_hash",
                "status_reason",
            )
            with system.store.transaction(write=True) as connection:
                for status in ("draft", "verified", "promoted"):
                    promoted = status == "promoted"
                    connection.execute(
                        f"INSERT INTO artifacts({', '.join(columns)}) "
                        f"VALUES ({', '.join('?' for _ in columns)})",
                        (
                            f"artifact-{status}",
                            "partition",
                            "operation",
                            1,
                            "{}",
                            f"input-{status}",
                            "{}",
                            f"output-{status}",
                            "{}",
                            f"artifact-hash-{status}",
                            f"scope-{status}",
                            f"build-{status}",
                            "{}",
                            "policy-hash",
                            f"evidence-{status}",
                            status,
                            2,
                            1,
                            0,
                            100,
                            f"report-{status}" if status != "draft" else None,
                            "promoter" if promoted else None,
                            100 if promoted else None,
                            f"promotion-{status}" if promoted else None,
                            None,
                        ),
                    )
            self.assertEqual(
                system.revise_operation(
                    "partition",
                    "operation",
                    policy=CompilePolicy(4, 2, 20),
                    revised_by="revision-owner",
                ),
                2,
            )
            with system.store.transaction() as connection:
                persisted_revision = connection.execute(
                    "SELECT revision FROM operations WHERE partition = ? AND name = ?",
                    ("partition", "operation"),
                ).fetchone()[0]
                artifacts = [
                    tuple(row)
                    for row in connection.execute(
                        """
                        SELECT id, status, promotion_hash, status_reason
                        FROM artifacts ORDER BY id
                        """
                    )
                ]
            self.assertEqual(persisted_revision, 2)
            self.assertEqual(
                artifacts,
                [
                    ("artifact-draft", "retired", None, "operation revised"),
                    ("artifact-promoted", "retired", None, "operation revised"),
                    ("artifact-verified", "retired", None, "operation revised"),
                ],
            )

    def test_l18__now_still_rejects_a_non_int_a_bool_a_negative_value_all(self) -> None:
        """L18. `_now` still rejects a non-`int`, a `bool`, a negative value (all three `StateError`, with L06's exact replacement text) and a non-callable `clock_us` (`ValidationError`, message `clock_us must be callable`, raised by `__init__` before `_now` runs). The surviving-caller half is stated as an exact CALL-SITE set, never as caller identity: the methods calling `self._now()` are EXACTLY the twelve remaining after `handle`, `_fail_generation` and `request_status` go — `register_operation`, `revise_operation`, `_persist_proposal`, `review`, `compile`, `verify_drafts`, `verify`, `promote_function`, `promote`, `challenge`, `revoke_example`, `suspend_artifact` — and each holds exactly one call spelled `self._now()`. The original wording (`every surviving caller of _now is unchanged`) was SELF-CONTRADICTORY, because `revise_operation` is both a surviving caller and an L07/L08 edit target whose body legitimately shrinks; whole-method equality is NOT expected for it (A15, X08). MAIN measured 15 callers at `da70a56`."""

        message = "clock must return a signed 64-bit microsecond timestamp"
        invalid = {
            "non-int": lambda: "1",
            "bool": lambda: True,
            "negative": lambda: -1,
        }
        for label, clock in invalid.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                system = System(Path(directory) / "cement.db", clock_us=clock)
                with self.assertRaises(StateError) as raised:
                    system.register_operation("partition", "operation")
                self.assertEqual(str(raised.exception), message)

    def test_l18_non_callable_clock_keeps_exact_validation_error(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaises(ValidationError) as raised:
                System(Path(directory) / "cement.db", clock_us=7)
        self.assertEqual(str(raised.exception), "clock_us must be callable")

    def test_l18_now_call_sites_are_the_exact_surviving_set(self) -> None:
        def call_sites(tree: ast.Module) -> dict[str, tuple[str, ...]]:
            parents = _parents(tree)
            calls: dict[str, list[str]] = {}
            for call in (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_now"
            ):
                owner = _nearest_function(call, parents)
                self.assertIsNotNone(owner)
                calls.setdefault(owner.name, []).append(ast.unparse(call))
            return {name: tuple(values) for name, values in calls.items()}

        baseline = call_sites(
            _system_tree(_git_text(BASE_SHA, "src/cement_runtime/system.py"))
        )
        deleted = {"handle", "_fail_generation", "request_status"}
        expected = {name: values for name, values in baseline.items() if name not in deleted}
        self.assertEqual(len(expected), 12)
        self.assertTrue(all(values == ("self._now()",) for values in expected.values()))
        self.assertEqual(call_sites(_system_tree()), expected)

    def test_l19_mechanical_readme_md_contains_zero_standalone_handle_words(self) -> None:
        """L19. MECHANICAL: `README.md` contains zero standalone `handle` words (baseline 8) and zero `request_status` substrings (baseline 4), counting code fences, links and inline code, all of which ship to readers (V23); zero Markdown tables whose `Status`-headed column carries any frozen lifecycle poll state (`resolved`, `review_required`, `in_progress`, `fallback_failed`, `rejected`, `reconciliation_required`) — that structural shape IS the poll-state table, so a renamed heading does not evade it; zero generation/request LEASE claims, while the two truthful `a verification snapshot is not a lease` statements SURVIVE, so the ban is context-classed rather than a global word ban that would delete correct prose to reach zero (X25); and the surviving Library API region still names `System.submit_proposal`, `System.propose`, `System.review` and `proposal_id` at least once each — L19 is CONJUNCTIVE, and deleting the lifecycle section is necessary, never sufficient (X09). RULED: that the replacement request-route prose teaches the proposal route correctly."""

        text = (ROOT / "README.md").read_text()
        library_match = re.search(
            r"(?ms)^## Library API\s*$\n(?P<body>.*?)(?=^## |\Z)", text
        )
        self.assertIsNotNone(library_match)
        library = library_match.group("body")
        for symbol in (
            "System.submit_proposal",
            "System.propose",
            "System.review",
            "proposal_id",
        ):
            with self.subTest(symbol=symbol):
                self.assertGreaterEqual(library.count(symbol), 1)
        self.assertEqual(len(re.findall(r"\bhandle\b", text)), 0)
        self.assertEqual(text.count("request_status"), 0)

    def test_l19_no_markdown_poll_state_table_survives(self) -> None:
        lines = (ROOT / "README.md").read_text().splitlines()
        lifecycle = {
            "resolved",
            "review_required",
            "in_progress",
            "fallback_failed",
            "rejected",
            "reconciliation_required",
        }

        def cells(line: str) -> list[str]:
            return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]

        tables: list[tuple[int, str]] = []
        for index, line in enumerate(lines[:-1]):
            if not line.lstrip().startswith("|"):
                continue
            headers = cells(line)
            status_columns = [
                position
                for position, header in enumerate(headers)
                if header.casefold() == "status"
            ]
            separators = cells(lines[index + 1])
            if not status_columns or len(separators) != len(headers) or not all(
                re.fullmatch(r":?-{3,}:?", separator) for separator in separators
            ):
                continue
            for row in lines[index + 2 :]:
                if not row.lstrip().startswith("|"):
                    break
                values = cells(row)
                for position in status_columns:
                    if position < len(values) and values[position].casefold() in lifecycle:
                        tables.append((index + 1, values[position].casefold()))
        self.assertEqual(tables, [])

    def test_l19_generation_lease_claims_leave_snapshot_controls_intact(self) -> None:
        generation_claim = re.compile(
            r"(?i)(candidate|generation|request).{0,120}\blease\b|"
            r"\blease\b.{0,120}(candidate|generation|request)"
        )
        snapshot_control = re.compile(
            r"(?i)(snapshot|verification result).{0,80}not a lease"
        )
        baseline_lines = _git_text(BASE_SHA, "README.md").splitlines()
        baseline_controls = [
            line for line in baseline_lines if snapshot_control.search(line)
        ]
        self.assertEqual(len(baseline_controls), 2)

        current_lines = (ROOT / "README.md").read_text().splitlines()
        self.assertEqual(
            len([line for line in current_lines if snapshot_control.search(line)]),
            len(baseline_controls),
        )
        self.assertEqual(
            [line for line in current_lines if generation_claim.search(line)],
            [],
        )

    def test_l20_mechanical_docs_architecture_md_s_contract_h2_ordered_list(self) -> None:
        """L20. MECHANICAL: `docs/architecture.md`'s Contract H2 ordered-list items 1-3, identified structurally so later list text stays free, contain `propose` >= 1 AND `review` >= 1 (MAIN rules the implicit question YES — both, not either) and `handle` == 0; zero paragraphs match `candidate generation` together with a standalone `lease` (V24). RULED: that steps 1-3 describe the surviving flow in the right order."""

        text = (ROOT / "docs/architecture.md").read_text()
        contract_match = re.search(
            r"(?ms)^## Contract\s*$\n(?P<body>.*?)(?=^## |\Z)", text
        )
        self.assertIsNotNone(contract_match)
        items: dict[int, list[str]] = {}
        active: int | None = None
        for line in contract_match.group("body").splitlines():
            item = re.match(r"^(\d+)\.\s+(.*)", line)
            if item:
                active = int(item.group(1))
                items.setdefault(active, []).append(item.group(2))
            elif active is not None and (line.startswith("   ") or line.strip()):
                items[active].append(line.strip())
        self.assertTrue(all(number in items for number in (1, 2, 3)))
        first_three = " ".join(
            part for number in (1, 2, 3) for part in items[number]
        )
        self.assertGreaterEqual(len(re.findall(r"\bpropose\b", first_three)), 1)
        self.assertGreaterEqual(len(re.findall(r"\breview\b", first_three)), 1)
        self.assertEqual(len(re.findall(r"\bhandle\b", first_three)), 0)

    def test_l20_no_candidate_generation_lease_paragraph_survives(self) -> None:
        paragraphs = [
            " ".join(paragraph.split())
            for paragraph in re.split(
                r"\n\s*\n", (ROOT / "docs/architecture.md").read_text()
            )
        ]
        obsolete = [
            paragraph
            for paragraph in paragraphs
            if re.search(r"candidate generation", paragraph, re.IGNORECASE)
            and re.search(r"\blease\b", paragraph, re.IGNORECASE)
        ]
        self.assertEqual(obsolete, [])

    def test_l21_mechanical_docs_adapter_protocol_md_matches_zero_deleted(self) -> None:
        """L21. MECHANICAL: `docs/adapter-protocol.md` matches zero deleted-surface tokens across prose, code fences and examples; `fallback_failed` reaches 0. TWO RETENTIONS bind, because M3.7 relocates this file under BYTE EQUALITY and a wrong deletion here is permanent too. First, the `"request_id"` JSON wire key SURVIVES (X16), described as an opaque per-call tracing identifier — `CandidateRequest.request_id` is M3.6a3's and byte-frozen `propose` still constructs it; the `\brequests?\b` ban never reaches it because `_` is a word character. Second, `System.propose`'s failure contract survives (X26): the document still names `CandidateSourceError` and one concrete no-write observable (proposal count 0, event count 0), while `handle`'s inert fallback branch goes. RULED: that the rewritten protocol description is true of the surviving adapter path."""

        text = (ROOT / "docs/adapter-protocol.md").read_text()
        deleted = re.compile(
            r"\bhandle\b|request_status|retry_failed|invalidated_generators|"
            r"resolved_by_artifact|\brequests?\b|\blease\b|in_progress|"
            r"fallback_failed|reconciliation_required|[Aa]mbigu\w*|_lease_us|"
            r"generation_lease_seconds|_outcome|_fail_generation|"
            r"_request_revision_is_current|artifact\.ambiguity_quarantined"
        )
        hits = [
            (line_number, tuple(match.group(0) for match in deleted.finditer(line)))
            for line_number, line in enumerate(text.splitlines(), 1)
            if deleted.search(line)
        ]
        self.assertEqual(hits, [])
        self.assertEqual(text.count('"request_id"'), 1)
        request_paragraphs = [
            " ".join(paragraph.split())
            for paragraph in re.split(r"\n\s*\n", text)
            if "request_id" in paragraph
        ]
        self.assertTrue(
            any(
                re.search(r"\bopaque\b", paragraph, re.IGNORECASE)
                and re.search(r"\bper-call\b", paragraph, re.IGNORECASE)
                and re.search(r"\btracing\b", paragraph, re.IGNORECASE)
                and re.search(r"\bidentifier\b", paragraph, re.IGNORECASE)
                for paragraph in request_paragraphs
            )
        )

    def test_l21_propose_failure_contract_survives_without_fallback_state(self) -> None:
        text = (ROOT / "docs/adapter-protocol.md").read_text()
        self.assertEqual(text.count("fallback_failed"), 0)
        self.assertGreaterEqual(text.count("System.propose"), 1)
        self.assertGreaterEqual(text.count("CandidateSourceError"), 1)
        failure_paragraphs = [
            " ".join(paragraph.split())
            for paragraph in re.split(r"\n\s*\n", text)
            if "CandidateSourceError" in paragraph
        ]
        no_proposal = re.compile(
            r"(?i)(?:\bno\s+proposals?\b|\bzero\s+proposals?\b|"
            r"\bproposals?\s+(?:count\s+)?(?:is\s+|=\s*)?0\b)"
        )
        no_event = re.compile(
            r"(?i)(?:\bno\s+events?\b|\bzero\s+events?\b|"
            r"\bevents?\s+(?:count\s+)?(?:is\s+|=\s*)?0\b)"
        )
        self.assertTrue(
            any(no_proposal.search(paragraph) and no_event.search(paragraph) for paragraph in failure_paragraphs)
        )

    def test_l22_mechanical_docs_threat_model_md_matches_zero_standalone(self) -> None:
        """L22. MECHANICAL: `docs/threat-model.md` matches zero standalone `handle` or `lease` lines (baseline 78 and 90); the ambiguity claim at line 61 goes while the three surviving quarantine causes stay (X17). RULED, and this obligation is MOSTLY semantic: the replacement states an application-owned idempotency key because Cement supplies none, at-most-once source invocation per `System.propose` call, and enumerate-pending recovery rather than retry (V26)."""

        text = (ROOT / "docs/threat-model.md").read_text()
        deleted_lines = [
            (line_number, line.strip())
            for line_number, line in enumerate(text.splitlines(), 1)
            if re.search(r"\b(?:handle|lease)\b", line, re.IGNORECASE)
        ]
        self.assertEqual(deleted_lines, [])

    def test_l22_ambiguity_leaves_the_three_surviving_quarantine_causes(self) -> None:
        text = (ROOT / "docs/threat-model.md").read_text()
        paragraphs = [
            " ".join(paragraph.split())
            for paragraph in re.split(r"\n\s*\n", text)
            if re.search(r"\bquarantin\w*\b", paragraph, re.IGNORECASE)
        ]
        surviving = [
            paragraph
            for paragraph in paragraphs
            if re.search(r"\bcounterexample\b", paragraph, re.IGNORECASE)
            and re.search(r"\brevocation\b", paragraph, re.IGNORECASE)
            and re.search(r"\bintegrity failure\b", paragraph, re.IGNORECASE)
        ]
        self.assertEqual(len(surviving), 1)
        self.assertEqual(
            len(re.findall(r"\bambigu\w*\b", text, re.IGNORECASE)),
            0,
        )

    def test_l23_all_16_census_pins_in_section_5_are_green_after_the(self) -> None:
        """L23. all 16 census pins in section 5 are green after the rewrite, each either satisfied by the new prose or re-scoped with grounds recorded in section 8. Sixteen, not fifteen, by C06. ANTI- WEAKENING (A17): each of the 14 working-tree pins keeps its assertion body BYTE-IDENTICAL to its `da70a56` blob unless section 8 PERMITS the delta, and every permitted delta is enumerated there. Without this, `all pins green` is satisfiable by making a pin tautological — a test with an unreachable document read and `assertIn('handle', 'handle')` scores `reads-doc True`, `vocab True`, stays in the census and keeps gate 1 green. The pins are additionally EXECUTED by id, not merely counted (X10)."""

        table = json.loads(
            (ROOT / ".agent/decisions/m3u6a2-tripwires.json").read_text()
        )
        rows = table["pins"]
        self.assertEqual(len(rows), 16)
        if instrument_pruned():
            rows = [row for row in rows if not row["locus"].startswith(f"{INSTRUMENT}:")]
            self.assertEqual(len(rows), 15)

        def flatten(suite: unittest.TestSuite):
            for test in suite:
                if isinstance(test, unittest.TestSuite):
                    yield from flatten(test)
                else:
                    yield test

        loader = unittest.defaultTestLoader
        selected: list[unittest.TestCase] = []
        cardinalities: list[int] = []
        for row in rows:
            path = row["locus"].split(":", 1)[0]
            module_name = Path(path).with_suffix("").as_posix().replace("/", ".")
            module = importlib.import_module(module_name)
            matches = [
                test
                for test in flatten(loader.loadTestsFromModule(module))
                if test.id().rsplit(".", 1)[-1] == row["test"]
            ]
            cardinalities.append(len(matches))
            selected.extend(matches)
        self.assertEqual(cardinalities, [1] * len(rows))

        result = unittest.TestResult()
        unittest.TestSuite(selected).run(result)
        self.assertEqual(result.testsRun, len(rows))
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])
        self.assertEqual(result.expectedFailures, [])
        self.assertEqual(result.unexpectedSuccesses, [])

    def test_l23_pin_bodies_freeze_unless_the_deleted_claim_forces_inversion(self) -> None:
        opening = (
            ("tests/test_cli_channels.py", "test_x20_new_command_help_and_publication_prohibit_retry_advice_and"),
            ("tests/test_cli_channels.py", "test_x29_the_publication_grep_scope_is_ambiguous_between_a_document"),
            ("tests/test_cli_channels.py", "test_x30_every_placeholder_in_each_shipped_shell_block_is_produced"),
            ("tests/test_cli_channels_battery.py", "test_d23_there_is_no_idempotency_two_byte_identical_submissions_ret"),
            ("tests/test_cli_removal_battery.py", "test_d22a_direction_cli_route_every_cli_route_locus_was_rewritte"),
            ("tests/test_cli_removal_battery.py", "test_d25_rewritten_human_facing_prose_holds_the_project_registe"),
            ("tests/test_migration_battery.py", "test_d23_examples_hospital_ocr_readme_md_208_and_216_name_the"),
            ("tests/test_proposal_binding_battery.py", "test_b25_prose_alone_teaches_reviewresult_and_the"),
            ("tests/test_proposal_binding_battery.py", "test_b26_a15_prose_outside_code_fences_names"),
            ("tests/test_proposal_binding_battery.py", "test_b27_no_public_surface_retains_the_unqualified"),
            ("tests/test_submission_battery.py", "test_d25_shipped_prose_says_schema_v2_retains"),
            ("tests/test_submission_battery.py", "test_d33_no_shipped_surface_calls_submission_cheap"),
            ("tests/test_submission_battery.py", "test_d34_readme_and_the_three_normative_docs"),
            ("tests/test_submission_battery.py", "test_d41_readme_and_the_normative_docs_name"),
        )
        required_inversions = {
            ("tests/test_cli_channels_battery.py", "test_d23_there_is_no_idempotency_two_byte_identical_submissions_ret"),
            ("tests/test_cli_removal_battery.py", "test_d22a_direction_cli_route_every_cli_route_locus_was_rewritte"),
            ("tests/test_proposal_binding_battery.py", "test_b27_no_public_surface_retains_the_unqualified"),
            ("tests/test_submission_battery.py", "test_d34_readme_and_the_three_normative_docs"),
        }
        # C20. D25's vocabulary lists are a CENSUS of the prose they grade, so the L19-L22 rewrite
        # forces them to move. A SHA pin was never available here: main's `d9e2c90` partition rename
        # had already moved the body away from `da70a56` before this unit opened. The row stays an
        # obligation rather than a blanket permission by naming the post-state the delta must buy -
        # the sentence openers the proposal-route prose introduces, each absent at the baseline.
        permitted_deltas = {
            (
                "tests/test_cli_removal_battery.py",
                "test_d25_rewritten_human_facing_prose_holds_the_project_registe",
            ): ('"propose"', '"resolve"', '"submitproposal"', '"verifydrafts"', '"reviewresult"'),
            # C28. C26's refreeze moves every non-D28 frame onto the closed transition, and this
            # is the one migration-battery body L23 froze. The delta is the `ROOT` -> `self.root`
            # conversion ALONE; the assertion logic is byte-identical either side, so nothing this
            # pin grades was weakened. Named rather than blanket, like C20: this row states what
            # the delta must BUY, and D30 owns the complementary half by forbidding `ROOT` in any
            # frame off its allowlist — what this buys plus what D30 forbids is total.
            (
                "tests/test_migration_battery.py",
                "test_d23_examples_hospital_ocr_readme_md_208_and_216_name_the",
            ): ("self.root",),
        }

        def function_span(source: str, name: str) -> str:
            matches = [
                node
                for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.FunctionDef) and node.name == name
            ]
            self.assertEqual(len(matches), 1, name)
            node = matches[0]
            start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
            return "\n".join(source.splitlines()[start - 1 : node.end_lineno])

        if instrument_pruned():
            opening = tuple(item for item in opening if item[0] != INSTRUMENT)
            self.assertEqual(len(opening), 13)

        for path, name in opening:
            baseline = function_span(_git_text(BASE_SHA, path), name)
            current = function_span((ROOT / path).read_text(), name)
            with self.subTest(path=path, name=name):
                if (path, name) in required_inversions:
                    self.assertNotEqual(current, baseline)
                elif (path, name) in permitted_deltas:
                    self.assertNotEqual(current, baseline)
                    for token in permitted_deltas[(path, name)]:
                        self.assertNotIn(token, baseline)
                        self.assertIn(token, current)
                else:
                    self.assertEqual(current, baseline)

    def test_l24_no_human_facing_surface_gains_a_new_claim_about_a_deleted(self) -> None:
        """L24. no human-facing surface gains a NEW claim about a deleted surface. Re-run the census (gate 3) against the rewritten documents. THE PREDICATE BINDS A NAMED TOKEN SUBSET, not the whole vocabulary (A18, V27): owned hits must reach ZERO for `handle`, `request_status`, `retry_failed`, `invalidated_generators`, `resolved_by_artifact`, `in_progress`, `fallback_failed`, `reconciliation_required` and every ambiguity-quarantine promise. The literal all-token reading is UNSATISFIABLE and MAIN reproduced why: M3.5b's D25 requires at least two shipped paragraphs containing `request row stays internal`, measurement finds exactly two (`README.md`, `docs/architecture.md`), and the census `\brequests?\b` matches both — so a green D25 and a zero `requests` count cannot hold together. Every surviving generic hit (`request`, `requests`, `lease`, `ambigu`) therefore carries explicit GROUNDS as private-table prose or a non-generation-lease statement. SCANNER COVERAGE IS ITSELF PINNED (X18): the census `DOCS` tuple must EQUAL the tracked human-facing Markdown set (`README.md`, `docs/*.md`, `examples/*/README.md`, five paths at `da70a56`), so a document added during implementation cannot become an unscanned home for a deleted claim. THIS PARAGRAPH IS GATE 3'S INDEPENDENT ORACLE (A22): the expectation lives in the contract, which `--emit` cannot rewrite, so re-emitting after a bad rewrite now contradicts a number MAIN authored rather than blessing the tree."""

        owned = (
            "README.md",
            "docs/architecture.md",
            "docs/adapter-protocol.md",
            "docs/threat-model.md",
        )
        deleted = re.compile(
            r"\bhandle\b|request_status|retry_failed|invalidated_generators|"
            r"resolved_by_artifact|in_progress|fallback_failed|reconciliation_required"
        )
        offenders: list[tuple[str, int, str]] = []
        ambiguities: list[tuple[str, int, str]] = []
        for relative in owned:
            for line_number, line in enumerate((ROOT / relative).read_text().splitlines(), 1):
                if deleted.search(line):
                    offenders.append((relative, line_number, line.strip()))
                if re.search(r"[Aa]mbigu\w*", line):
                    ambiguities.append((relative, line_number, line.strip()))
        self.assertEqual(offenders, [])
        self.assertEqual(ambiguities, [])

    def test_l24_scanner_covers_all_human_markdown_and_grounds_generic_hits(self) -> None:
        import runpy

        namespace = runpy.run_path(
            str(ROOT / ".agent/decisions/m3u6a2-tripwires.py")
        )
        output = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        tracked = {
            path.decode()
            for path in output.split(b"\0")
            if path
            and (
                path == b"README.md"
                or re.fullmatch(rb"docs/[^/]+\.md", path)
                or re.fullmatch(rb"examples/[^/]+/README\.md", path)
            )
        }
        docs = tuple(namespace["DOCS"])
        self.assertEqual(len(docs), len(set(docs)))
        self.assertEqual(set(docs), tracked)

        generic = re.compile(r"\brequests?\b|\blease\b|[Aa]mbigu\w*")
        ungrounded: list[tuple[str, tuple[str, ...], str]] = []
        for relative in docs:
            if relative.startswith("examples/"):
                continue
            text = (ROOT / relative).read_text()
            for raw_paragraph in re.split(r"\n\s*\n", text):
                tokens = tuple(match.group(0) for match in generic.finditer(raw_paragraph))
                if not tokens:
                    continue
                paragraph = " ".join(raw_paragraph.split())
                request_ground = bool(
                    re.search(
                        r"\brequests? (?:rows?|table|storage|records?)\b",
                        paragraph,
                        re.IGNORECASE,
                    )
                    or re.search(
                        r"\bno request (?:identity|identifier)\b",
                        paragraph,
                        re.IGNORECASE,
                    )
                    or re.search(
                        r"\brequest-(?:free|identity-free)\b",
                        paragraph,
                        re.IGNORECASE,
                    )
                )
                lease_ground = bool(
                    re.search(
                        r"(?:snapshot|verification result).{0,200}\bnot a lease\b",
                        paragraph,
                        re.IGNORECASE,
                    )
                )
                grounded = all(
                    (token.startswith("request") and request_ground)
                    or (token == "lease" and lease_ground)
                    for token in tokens
                )
                if not grounded:
                    ungrounded.append((relative, tokens, paragraph[:240]))
        self.assertEqual(ungrounded, [])

    def test_l25_m3_5b_s_d15a_tests_test_cli_removal_battery_py_1131(self) -> None:
        """L25. M3.5b's D15a (`tests/test_cli_removal_battery.py:1131`, assertion `:1158`) is re-scoped to the closed range `36f7890..1146421`, exactly as M3.6a1 re-scoped its siblings D15b (`:1160`) and D22b (`:2766`). The repair is a family repair: after it, no D15/D22 clause reads the working tree for a runtime module."""

        protected = (
            "src/cement_runtime/system.py",
            "src/cement_runtime/store.py",
            "src/cement_runtime/models.py",
            "src/cement_runtime/source.py",
            "src/cement_runtime/_command_supervisor.py",
            "src/cement_runtime/example_adapter.py",
        )
        for relative in protected:
            with self.subTest(relative=relative):
                self.assertEqual(
                    _git_bytes("1146421", relative),
                    _git_bytes("36f7890", relative),
                )

        path = ROOT / "tests/test_cli_removal_battery.py"
        source = path.read_text()
        functions = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_d15a_")
        ]
        self.assertEqual(len(functions), 1)
        segment = ast.get_source_segment(source, functions[0]) or ""
        self.assertIn("36f7890", segment)
        self.assertIn("1146421", segment)
        self.assertFalse(
            any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr in {"read_bytes", "read_text"}
                for call in ast.walk(functions[0])
            )
        )

    def test_l25_entire_d15_d22_freeze_family_is_git_range_scoped(self) -> None:
        import runpy

        namespace = runpy.run_path(
            str(ROOT / ".agent/decisions/m3u6a2-tripwires.py")
        )
        rows = namespace["_freezes"]()
        expected = {
            "test_d15a_the_six_runtime_modules_stay_byte_identical_to_their_3",
            "test_d15b_the_twelve_examples_files_stay_byte_identical_to_their",
            "test_d22b_direction_library_route_every_library_api_locus_is_byt",
            "test_d22c_the_opening_text_handle_request_fence_is_protected_and",
        }
        self.assertEqual({row["test"] for row in rows}, expected)
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["scope"] for row in rows}, {"GIT-RANGE"})

    def test_l26_the_four_p06_span_freezes_are_retired_with_their_history(self) -> None:
        """L26. the four P06 span freezes are RETIRED with their history preserved, not re-based: they freeze the bytes of a method that no longer exists. Retirement DERIVES all three figures (`12,866 B / 1182130a2b3a`, `12,867 B / cd60036faf5c`, `12,862 B / c27e71b0b4c7`) from git object `3b7769b` on EVERY RUN and compares them; recording them as prose leaves a copied typo satisfying a text-presence assertion while disagreeing with history, and the only executable recomputers today are the frames being retired (A19). All FOUR test identities stay DISCOVERABLE — one aggregate replacement erases three independent tripwire records even where the figures appear once (X21) — and none reads the working-tree `System.handle` span. L15 replaces their protective value for the methods that survive."""

        source = _git_text("3b7769b", "src/cement_runtime/system.py")
        tree = ast.parse(source)
        systems = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "System"
        ]
        self.assertEqual(len(systems), 1)
        handles = [
            node
            for node in systems[0].body
            if isinstance(node, ast.FunctionDef) and node.name == "handle"
        ]
        self.assertEqual(len(handles), 1)
        handle = handles[0]
        kept = "".join(
            source.splitlines(keepends=True)[handle.lineno - 1 : handle.end_lineno]
        )
        spans = (
            kept.rstrip("\r\n"),
            kept,
            ast.get_source_segment(source, handle) or "",
        )
        figures = tuple(
            (len(span.encode()), hashlib.sha256(span.encode()).hexdigest()[:12])
            for span in spans
        )
        self.assertEqual(
            figures,
            (
                (12_866, "1182130a2b3a"),
                (12_867, "cd60036faf5c"),
                (12_862, "c27e71b0b4c7"),
            ),
        )

        targets = (
            (
                "tests/test_submission.py",
                "test_handle_is_byte_identical_to_the_unit_baseline",
                "tests.test_submission.SubmissionTests.test_handle_is_byte_identical_to_the_unit_baseline",
            ),
            (
                "tests/test_submission_battery.py",
                "test_p06_handle_is_12_866_b_1182130a2b3a",
                "tests.test_submission_battery.SubmissionBatteryTests.test_p06_handle_is_12_866_b_1182130a2b3a",
            ),
            (
                "tests/test_submission_battery.py",
                "test_p06_three_slicing_conventions_are_distinct",
                "tests.test_submission_battery.SubmissionBatteryTests.test_p06_three_slicing_conventions_are_distinct",
            ),
            (
                "tests/test_migration_battery.py",
                "test_d25_m3_3_s_p06_byte_span_freeze_on_system_handle_stays_green",
                "tests.test_migration_battery.MigrationBatteryTests.test_d25_m3_3_s_p06_byte_span_freeze_on_system_handle_stays_green",
            ),
        )
        if instrument_pruned():
            targets = tuple(item for item in targets if item[0] != INSTRUMENT)
            self.assertEqual(len(targets), 3)

        violations: list[tuple[str, str]] = []
        for path, name, _ in targets:
            test_source = (ROOT / path).read_text()
            module = ast.parse(test_source)
            definitions = [
                node
                for node in ast.walk(module)
                if isinstance(node, ast.FunctionDef) and node.name == name
            ]
            if len(definitions) != 1:
                violations.append((name, f"definition-count={len(definitions)}"))
                continue
            by_name: dict[str, list[ast.FunctionDef]] = {}
            for function in (
                node for node in ast.walk(module) if isinstance(node, ast.FunctionDef)
            ):
                by_name.setdefault(function.name, []).append(function)
            closure: list[ast.FunctionDef] = []
            pending = [definitions[0]]
            seen: set[int] = set()
            while pending:
                function = pending.pop()
                if id(function) in seen:
                    continue
                seen.add(id(function))
                closure.append(function)
                for call in (
                    node for node in ast.walk(function) if isinstance(node, ast.Call)
                ):
                    called = (
                        call.func.id
                        if isinstance(call.func, ast.Name)
                        else call.func.attr
                        if isinstance(call.func, ast.Attribute)
                        else None
                    )
                    if called is not None and len(by_name.get(called, ())) == 1:
                        pending.append(by_name[called][0])
            calls = [
                call
                for function in closure
                for call in ast.walk(function)
                if isinstance(call, ast.Call)
            ]
            closure_source = "\n".join(ast.unparse(function) for function in closure)
            git_read = any(
                (
                    isinstance(call.func, ast.Name)
                    and call.func.id in {"_git_bytes", "git_bytes"}
                )
                or (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr in {"_git_bytes", "git_bytes", "check_output", "run"}
                )
                for call in calls
            ) and all(
                literal in closure_source
                for literal in ("3b7769b", "src/cement_runtime/system.py")
            )
            live_readers = {
                call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id
                for call in calls
                if (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr in {"read_text", "read_bytes", "getsource", "getsourcefile"}
                )
                or (
                    isinstance(call.func, ast.Name)
                    and call.func.id in {"_source", "getsource", "getsourcefile"}
                )
            }
            call_names = {
                call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id
                for call in calls
                if isinstance(call.func, (ast.Name, ast.Attribute))
            }
            if not git_read:
                violations.append((name, "no 3b7769b system.py git-read dependency"))
            if live_readers:
                violations.append((name, f"live readers={sorted(live_readers)}"))
            if not {"len", "sha256"}.issubset(call_names):
                violations.append((name, "does not recompute size and sha256"))
        self.assertEqual(violations, [])

        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromName(full_name)
            for _, _, full_name in targets
        )
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.testsRun, len(targets))
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])

    def test_l27_m3_5b_s_d01_tests_test_cli_removal_battery_py_608(self) -> None:
        """L27. M3.5b's D01 (`tests/test_cli_removal_battery.py:608`, assertions `:617` + `:618`) is INVERTED: it asserted `System.handle` and `System.request_status` still ship as library methods; it now asserts their absence. An inverted pin keeps the obligation and reverses the predicate; deleting it would delete the behaviour's only pin along with the behaviour. The inversion PAIRS absence with positive identity controls in the same test — `System.__module__ == 'cement_runtime.system'` and `callable(System.propose)` — or both negative assertions pass against an empty dummy class (X12), and D01's existing CLI leaf-set complement stays green beside them, which is the two non-overlapping subproperties that make retention worth more than deletion (A20)."""

        path = ROOT / "tests/test_cli_removal_battery.py"
        source = path.read_text()
        names = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef)
            and node.name.startswith("test_d01_m3_5b_ships_system_handle")
        ]
        self.assertEqual(len(names), 1)
        assertions = [
            ast.unparse(call)
            for call in ast.walk(names[0])
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr.startswith("assert")
        ]
        assertion_nodes = [
            call
            for call in ast.walk(names[0])
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr.startswith("assert")
        ]
        for lifecycle_name in ("handle", "request_status"):
            relevant = [
                call
                for call in assertion_nodes
                if any(
                    isinstance(node, ast.Constant) and node.value == lifecycle_name
                    for node in ast.walk(call)
                )
            ]
            self.assertTrue(relevant, lifecycle_name)
            forbidden_positive = [
                call
                for call in relevant
                if call.func.attr == "assertTrue"
                and call.args
                and isinstance(call.args[0], ast.Call)
                and isinstance(call.args[0].func, ast.Name)
                and call.args[0].func.id in {"callable", "hasattr"}
            ]
            self.assertEqual(forbidden_positive, [], lifecycle_name)
        combined = "\n".join(assertions)
        for control in (
            "__module__",
            "cement_runtime.system",
            "propose",
            "callable",
            "SURVIVING_LEAVES",
            "REMOVED_LEAVES",
        ):
            with self.subTest(control=control):
                self.assertIn(control, combined)

        self.assertEqual(System.__module__, "cement_runtime.system")
        self.assertTrue(callable(System.propose))
        self.assertFalse(hasattr(System, "handle"))
        self.assertFalse(hasattr(System, "request_status"))
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(
            "tests.test_cli_removal_battery.RemovalObligationBatteryTests."
            "test_d01_m3_5b_ships_system_handle_and_system_request_status_as"
        ).run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])

    def test_l28_tests_test_authority_removal_py_118(self) -> None:
        """L28. `tests/test_authority_removal.py:118 test_system_constructor_shape` is rewritten to the three-parameter signature and keeps asserting defaults for the parameters that remain."""

        import typing

        parameters = inspect.signature(System.__init__).parameters
        self.assertEqual(
            tuple(
                (
                    name,
                    parameter.kind,
                    parameter.default,
                )
                for name, parameter in parameters.items()
            ),
            (
                (
                    "self",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.empty,
                ),
                (
                    "database",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.empty,
                ),
                ("candidate_source", inspect.Parameter.KEYWORD_ONLY, None),
                ("clock_us", inspect.Parameter.KEYWORD_ONLY, None),
            ),
        )
        self.assertIs(typing.get_type_hints(System.__init__)["return"], type(None))

        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(
            "tests.test_authority_removal.FrozenShapeTests.test_system_constructor_shape"
        ).run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])

    def test_l29_m3u6a2_tripwires_py_s__freezes_detector_is_widened_to_see(self) -> None:
        """L29. `m3u6a2-tripwires.py`'s `_freezes()` detector is widened to see the P06 family, behind a self-test control that FIRES on a P06 frame. Today it requires the literal `cement_runtime/system.py` or `System.handle` AND one of `read_bytes()`/`getsource`/`_git_bytes(`, while the four P06 frames reach the same source through `cement_runtime.system.__file__`, `inspect.getsourcefile(System)` and a `_source(ROOT, path)` helper — so the instrument reported `FREEZES: 4` over a set DISJOINT from the four freezes this unit actually inverts, and its 6/6 self-test covered none of that negative space. THE CONTROL RUNS AGAINST AN IMMUTABLE SYNTHETIC P06 SOURCE FIXTURE, never a live frame, because L26 empties the live positive set in this same unit — after retirement a working detector and one returning no P06 rows are otherwise indistinguishable (A21). Detection is factored into a `_is_freeze(segment)` seam so it can be probed directly, and the control is a PAIR: the P06 shape must be INCLUDED, and the same source acquisition selecting a PRESERVED method (`propose`) must be EXCLUDED, or over-reporting satisfies the positive half alone (X14, V30). Live `_freezes()` stays 4 and `--self-test` goes 8/8. If widening proves to over-report, record the exclusion with grounds instead; what is not acceptable is leaving a detector whose name promises the family it cannot see. The battery's own file stays excluded from both scanners (C06, X22)."""

        import runpy

        namespace = runpy.run_path(
            str(ROOT / ".agent/decisions/m3u6a2-tripwires.py")
        )
        self.assertTrue("_is_freeze" in namespace)
        detector = namespace["_is_freeze"]
        positive = """
        def test_p06_history():
            source_path = Path(inspect.getsourcefile(System) or "")
            source = source_path.read_text(encoding="utf-8")
            handle = next(
                node for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.FunctionDef) and node.name == "handle"
            )
        """
        negative = positive.replace('node.name == "handle"', 'node.name == "propose"')
        self.assertTrue(detector(positive))
        self.assertFalse(detector(negative))

        pins = namespace["_pins"]()
        freezes = namespace["_freezes"]()
        # `_pins()` scans the working tree, so the pruned instrument's row leaves with it.
        # All four freezes live in `test_cli_removal_battery.py`, so that count is unaffected.
        self.assertEqual(len(pins), 15 if instrument_pruned() else 16)
        self.assertEqual(len(freezes), 4)
        leaked = [
            row["locus"]
            for row in (*pins, *freezes)
            if "test_lifecycle_removal_battery.py" in row["locus"]
        ]
        self.assertEqual(leaked, [])
        emitted = namespace["emit"]()
        self.assertEqual(
            emitted["excluded"],
            ["tests/test_lifecycle_removal_battery.py"],
        )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            return_code = namespace["self_test"]()
        self.assertEqual(return_code, 0)
        self.assertIn("CONTROLS: 8/8 firing", output.getvalue())
        self.assertIn("RESULT: PASS", output.getvalue())

    def test_l30_m3_6a1_s_d16_tests_test_migration_battery_py_993_is_re(self) -> None:
        """L30. M3.6a1's D16 (`tests/test_migration_battery.py:993`) is re-scoped to the CLOSED range `6fb4d92..dc4ab5e` — M3.6a1's baseline and its own DONE tip — on BOTH halves: the expected path set and the per-path byte comparison, which read `HEAD` and the working tree respectively. Read against `HEAD`, D16 asserted that M3.6a1's surgery script reproduces every LATER unit's `tests/` and `examples/` edits, which no script pinned to an earlier baseline can do. It is the same family as D15a (L25), and it is stricter: D15a inverts when this unit EDITS a runtime module, while D16 inverts when this unit ADDS ANY FILE under `tests/` or `examples/` — the battery seed alone tripped it. Its repair therefore lands NO LATER THAN the first commit that adds a file under `tests/` or `examples/`. `Before` was the wrong word (X33, C11): git has no intra-commit ordering, and `7cfc748` both repaired D16 and added the seed, which satisfies the practical reading and needs no history rewrite. D16's closed expected-path set is an exact eight-member historical delta, not merely a nonempty one (X23), and BOTH halves use `6fb4d92..dc4ab5e` (X15)."""

        if instrument_pruned():
            self.skipTest("D28 replay: the instrument this frame grades is not in the checkout")

        path = ROOT / INSTRUMENT
        source = path.read_text()
        tree = ast.parse(source)
        endpoints = {
            target.id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and target.id in {"BASELINE", "M3U6A1_TIP"}
        }
        self.assertEqual(
            endpoints,
            {"BASELINE": "6fb4d92", "M3U6A1_TIP": "dc4ab5e"},
        )
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_d16_")
        ]
        self.assertEqual(len(functions), 1)
        function = functions[0]
        self.assertEqual(
            sum(
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id == "M3U6A1_TIP"
                for node in ast.walk(function)
            ),
            2,
        )
        self.assertEqual(
            [
                node.value
                for node in ast.walk(function)
                if isinstance(node, ast.Constant) and node.value == "HEAD"
            ],
            [],
        )

        changed = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "6fb4d92..dc4ab5e",
                "--",
                "tests",
                "examples",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        changed.remove("tests/test_migration_battery.py")
        self.assertEqual(
            tuple(changed),
            (
                "examples/hospital_ocr/README.md",
                "examples/hospital_ocr/run_demo.py",
                "tests/test_cli.py",
                "tests/test_cli_removal_battery.py",
                "tests/test_hospital_ocr_example.py",
                "tests/test_proposal_binding_battery.py",
                "tests/test_resolve_battery.py",
                "tests/test_system.py",
            ),
        )
        seed_commit = subprocess.run(
            ["git", "show", "--format=", "--name-status", "7cfc748"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertIn("M\ttests/test_migration_battery.py", seed_commit)
        self.assertIn("A\ttests/test_lifecycle_removal_battery.py", seed_commit)

        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(
            "tests.test_migration_battery.MigrationBatteryTests."
            "test_d16_the_script_is_replayable_from_a_clean_base_applying_it_to"
        ).run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])

    def test_l31_ambiguity_quarantine_is_removed_as_a_behaviour_not_merely(self) -> None:
        """L31. AMBIGUITY QUARANTINE IS REMOVED AS A BEHAVIOUR, not merely as an event spelling (A10). After this unit no code path suspends an artifact with reason `ambiguous active scope`: that reason string has zero occurrences in `src/`, and a probe that drives the duplicate-promotion condition leaves BOTH artifacts `promoted` with their promotion receipts intact and emits ZERO ambiguity events. `tests/test_system.py`'s surviving assertion is INVERTED to that post-state rather than deleted (V15). This obligation exists because C05 reclassified the quarantine as a deleted behaviour while L11 pinned only its vocabulary — a renamed private path could keep the storage mutation, emit an allowed kind and satisfy the sixteen-kind set — and because section 2.1 gave the clock widening its own obligation on exactly this reasoning."""

        self.assertEqual(_raw_src_hits("ambiguous active scope"), {})

        class Source:
            def propose(self, request):
                return Candidate(
                    output={"echo": request.input},
                    provenance={"source": "ambiguity-battery"},
                )

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            database = Path(directory) / "cement.db"
            system = System(
                database,
                candidate_source=Source(),
                clock_us=iter(range(1_000_000, 1_001_000)).__next__,
            )
            system.register_operation(
                "partition",
                "operation",
                policy=CompilePolicy(2, 2, 0),
            )
            input_value = {"x": 1}
            for reviewer in ("alice", "bob"):
                proposal_id = system.propose("partition", "operation", input_value)
                system.review(
                    "partition",
                    proposal_id,
                    reviewer=reviewer,
                    decision="accept",
                )
            build = system.compile("partition", "operation")
            self.assertEqual(len(build.created), 1)
            artifact_id = build.created[0]
            report = system.verify("partition", artifact_id)
            self.assertTrue(report.passed)
            system.promote(
                "partition",
                artifact_id,
                scope_hash=report.scope_hash,
                promoted_by="release-manager",
            )

            duplicate_id = "artifact-duplicate"
            duplicate_report_id = "report-duplicate"
            connection = sqlite3.connect(database)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                artifact = connection.execute(
                    "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
                ).fetchone()
                self.assertIsNotNone(artifact)
                report_row = connection.execute(
                    "SELECT * FROM test_reports WHERE id = ?",
                    (artifact["verified_report_id"],),
                ).fetchone()
                self.assertIsNotNone(report_row)
                promotion_hash = system_module._digest_strings(
                    "cement-promotion-v2",
                    (
                        duplicate_id,
                        str(artifact["artifact_hash"]),
                        str(artifact["build_hash"]),
                        str(artifact["policy_hash"]),
                        str(artifact["evidence_snapshot_hash"]),
                        str(artifact["support"]),
                        str(artifact["reviewer_count"]),
                        str(artifact["span_seconds"]),
                        str(artifact["scope_hash"]),
                        duplicate_report_id,
                        str(report_row["details_hash"]),
                        str(report_row["test_set_hash"]),
                        str(report_row["test_count"]),
                        str(report_row["passed"]),
                        str(artifact["promoted_by"]),
                        str(artifact["promoted_at_us"]),
                    ),
                )
                connection.execute("DROP INDEX IF EXISTS one_promoted_exact_scope")
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, partition, operation, operation_revision, input_json, input_hash,
                        output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                        build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                        support, reviewer_count, span_seconds, created_at_us,
                        verified_report_id, promoted_by, promoted_at_us, promotion_hash,
                        status_reason
                    )
                    SELECT ?, partition, operation, operation_revision, input_json, input_hash,
                        output_json, output_hash, artifact_json, artifact_hash, scope_hash,
                        build_hash, policy_json, policy_hash, evidence_snapshot_hash, status,
                        support, reviewer_count, span_seconds, created_at_us,
                        ?, promoted_by, promoted_at_us, ?, status_reason
                    FROM artifacts WHERE id = ?
                    """,
                    (duplicate_id, duplicate_report_id, promotion_hash, artifact_id),
                )
                connection.execute(
                    """
                    INSERT INTO artifact_tests(report_id, test_key, example_id, passed, detail)
                    SELECT ?, test_key, example_id, passed, detail
                    FROM artifact_tests WHERE report_id = ?
                    """,
                    (duplicate_report_id, report_row["id"]),
                )
                connection.execute(
                    """
                    INSERT INTO test_reports(
                        id, artifact_id, artifact_hash, build_hash, policy_hash,
                        evidence_snapshot_hash, passed, details_json, details_hash,
                        test_count, test_set_hash, created_at_us
                    )
                    SELECT ?, ?, artifact_hash, build_hash, policy_hash,
                        evidence_snapshot_hash, passed, details_json, details_hash,
                        test_count, test_set_hash, created_at_us
                    FROM test_reports WHERE id = ?
                    """,
                    (duplicate_report_id, duplicate_id, report_row["id"]),
                )
                connection.commit()
                before = connection.execute(
                    """
                    SELECT id, status, promotion_hash FROM artifacts
                    WHERE id IN (?, ?) ORDER BY id
                    """,
                    (artifact_id, duplicate_id),
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(len(before), 2)
            self.assertEqual({row["status"] for row in before}, {"promoted"})
            self.assertTrue(all(row["promotion_hash"] is not None for row in before))

            with self.assertRaisesRegex(StateError, "exactly one active artifact match"):
                system.challenge(
                    "partition",
                    "operation",
                    input_value,
                    {"echo": input_value},
                    reviewer="auditor",
                )
            connection = sqlite3.connect(database)
            connection.row_factory = sqlite3.Row
            try:
                after = connection.execute(
                    """
                    SELECT id, status, promotion_hash FROM artifacts
                    WHERE id IN (?, ?) ORDER BY id
                    """,
                    (artifact_id, duplicate_id),
                ).fetchall()
                ambiguity_events = connection.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE kind = 'artifact.ambiguity_quarantined'
                    """
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual([tuple(row) for row in after], [tuple(row) for row in before])
            self.assertEqual(ambiguity_events, 0)

    def test_l31_existing_duplicate_regression_is_inverted_not_deleted(self) -> None:
        source = (ROOT / "tests/test_system.py").read_text()
        functions = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef)
            and node.name == "test_function_verification_duplicate_gate_and_runtime_defenses"
        ]
        self.assertEqual(len(functions), 1)
        function = functions[0]
        self.assertFalse(
            any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "handle"
                for call in ast.walk(function)
            )
        )
        assertions = [
            call
            for call in ast.walk(function)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr.startswith("assert")
        ]
        rendered = "\n".join(ast.unparse(call) for call in assertions)
        self.assertIn("promoted", rendered)
        self.assertIn("promotion_hash", rendered)
        self.assertTrue("is not None" in rendered or "assertIsNotNone" in rendered)
        self.assertTrue(
            any(
                call.func.attr == "assertEqual"
                and len(call.args) >= 2
                and any(
                    isinstance(node, ast.Name) and node.id == "ambiguity_events"
                    for node in ast.walk(call.args[0])
                )
                and isinstance(call.args[1], ast.Constant)
                and call.args[1].value == 0
                for call in assertions
            )
        )

        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(
            "tests.test_system.SystemTests."
            "test_function_verification_duplicate_gate_and_runtime_defenses"
        ).run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.skipped, [])
