"""M3.4 instruments: request-row confinement and frozen public shape.

Neither instrument is behavioural. A green suite is not closure for this unit, because
deleting a behaviour together with its pin leaves the gate green and the coverage number
unchanged. These two tests fail when the confinement set changes or when a frozen shape
moves, and nothing else in the suite does.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import sys
import typing
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cement_runtime import models, system  # noqa: E402
from cement_runtime.models import (  # noqa: E402
    PendingProposalGap,
    ProposalView,
    ReviewResult,
)

# Every definition allowed to name the private request row after M3.4. This is a COMPLEMENT
# assertion, not a forbidden list: a forbidden list fails open on exactly the member nobody
# thought of, while an equality against this set fails closed and covers every definition
# added later. It is a TRIPWIRE a later unit updates deliberately in the same commit that
# adds or removes a member -- never a gate to route around by hiding an access.
PERMITTED_REQUEST_NAMERS = frozenset(
    {
        # M3.3 storage plumbing: the private row a proposal's scope still lives on.
        "_persist_proposal",
        # M3.4's adapter. Its two members are the sole request access for the proposal
        # read, review and report paths, so M3.6b rewrites them and no consumer moves.
        "_proposal_bindings",
        "_write_proposal_request_status",
        # handle-lifecycle owners. M3.5b removes the grammar; M3.6a deletes the methods.
        "handle",
        "_fail_generation",
        "request_status",
        "revise_operation",
    }
)

# Definitions that reached the request row before M3.4 and must not reach it after.
FREED_BY_M3_4 = frozenset(
    {
        "get_proposal",
        "proposal",
        "proposals",
        "review",
        "function_report",
        "_proposal_record",
        "_proposal_content",
        "_pending_proposal_gap_from_row",
    }
)

TABLE = "requests"


def _sql_identifiers(text: str) -> set[str]:
    """Case-folded SQL identifiers in one string constant.

    Matching is on whole identifiers, never substrings: ``FROM ARTIFACTS`` escaped a prior
    instrument on case alone, and ``requests`` is a substring of ``requests_scope``. Double
    quotes are separators so a quoted ``"REQUESTS"`` tokenizes to the identifier itself.
    """

    tokens: set[str] = set()
    current: list[str] = []
    for char in text:
        if char.isalnum() or char == "_":
            current.append(char)
            continue
        if current:
            tokens.add("".join(current).casefold())
            current = []
    if current:
        tokens.add("".join(current).casefold())
    return tokens


def _definitions_naming_table(source: str, table: str) -> set[str]:
    """Names of the top-level and nested definitions whose SQL names ``table``.

    The walk covers the WHOLE module, not only function bodies: an alternative that hoists
    its SQL into a module-level constant moves the token out of every function, and an
    instrument scoped to function bodies reports a clean set while the join is still
    composed into its consumers. A module-level constant is attributed to its own assigned
    name; every other string is attributed to the innermost function or method enclosing it.
    """

    tree = ast.parse(source)
    named: set[str] = set()

    def strings_under(node: ast.AST) -> list[str]:
        found = []
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                found.append(child.value)
        return found

    def visit(node: ast.AST, owner: str | None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for text in strings_under(child):
                    if table in _sql_identifiers(text):
                        named.add(child.name)
                        break
                visit(child, child.name)
                continue
            if isinstance(child, ast.ClassDef):
                visit(child, owner)
                continue
            if owner is None and isinstance(child, (ast.Assign, ast.AnnAssign)):
                targets = (
                    child.targets if isinstance(child, ast.Assign) else [child.target]
                )
                assigned = [
                    target.id for target in targets if isinstance(target, ast.Name)
                ]
                if assigned and any(
                    table in _sql_identifiers(text) for text in strings_under(child)
                ):
                    named.update(assigned)
                continue
            visit(child, owner)

    visit(tree, None)
    return named


class RequestRowConfinementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Path(system.__file__).read_text(encoding="utf-8")

    def test_exactly_the_permitted_definitions_name_the_request_row(self) -> None:
        self.assertEqual(
            _definitions_naming_table(self.source, TABLE),
            set(PERMITTED_REQUEST_NAMERS),
        )

    def test_every_path_freed_by_this_unit_stopped_naming_the_request_row(self) -> None:
        # Redundant against the complement above by construction, and deliberately so: it
        # names the eight sites this unit owns, so a future edit to the permitted set that
        # silently readmits one of them fails here with the member spelled out.
        self.assertEqual(
            _definitions_naming_table(self.source, TABLE) & FREED_BY_M3_4,
            set(),
        )

    def test_the_instrument_detects_a_hidden_namer(self) -> None:
        # Positive control. Without it a broken tokenizer reports an empty set forever.
        planted = "def leaked():\n    return 'SELECT id FROM REQUESTS'\n"
        self.assertEqual(_definitions_naming_table(planted, TABLE), {"leaked"})
        hoisted = "SQL = 'SELECT id FROM requests'\n"
        self.assertEqual(_definitions_naming_table(hoisted, TABLE), {"SQL"})

    def test_the_instrument_matches_identifiers_and_not_substrings(self) -> None:
        near_miss = "def other():\n    return 'SELECT requests_scope FROM audit'\n"
        self.assertEqual(_definitions_naming_table(near_miss, TABLE), set())
        quoted = 'def quoted():\n    return \'SELECT id FROM "REQUESTS"\'\n'
        self.assertEqual(_definitions_naming_table(quoted, TABLE), {"quoted"})


class FrozenPublicShapeTests(unittest.TestCase):
    """This test carries every M3.4 shape pin at once.

    Frozen shape is invisible to behavioural tests: removing a keyword-only marker, adding a
    defaulted field and changing a return annotation each pass a full suite. Weakening any
    assertion below unpins the shape it names, so read the whole test as one pin.
    """

    def test_review_result_and_proposal_shapes_are_frozen(self) -> None:
        self.assertEqual(
            tuple(ReviewResult.__dataclass_fields__),
            ("proposal_id", "status", "example_id", "output"),
        )
        # Annotations are compared as written, not as resolved. `JSONValue` is a recursive
        # alias, and `typing.get_type_hints` expands it to a different depth for each class
        # that names it, so a resolved comparison fails on the expansion rather than on the
        # shape. The annotation text is the stable pin. PEP 563 stringifies from the AST,
        # so the module's double-quoted `Literal` arguments arrive single-quoted here.
        self.assertEqual(
            dict(ReviewResult.__annotations__),
            {
                "proposal_id": "str",
                "status": "Literal['accepted', 'corrected', 'rejected']",
                "example_id": "str | None",
                "output": "JSONValue | None",
            },
        )
        resolved = typing.get_type_hints(ReviewResult)
        self.assertEqual(resolved["proposal_id"], str)
        self.assertEqual(
            resolved["status"], typing.Literal["accepted", "corrected", "rejected"]
        )
        self.assertEqual(resolved["example_id"], str | None)
        self.assertIn(type(None), typing.get_args(resolved["output"]))
        # No field is defaulted: every decision states all four values explicitly. The
        # sentinel is compared by identity -- `repr(dataclasses.MISSING)` embeds the
        # object's address, so a text comparison against it never matches.
        self.assertEqual(
            [
                name
                for name, field in ReviewResult.__dataclass_fields__.items()
                if field.default is not dataclasses.MISSING
                or field.default_factory is not dataclasses.MISSING
            ],
            [],
        )
        self.assertTrue(ReviewResult.__dataclass_params__.frozen)

        self.assertEqual(
            tuple(ProposalView.__dataclass_fields__),
            (
                "id",
                "partition",
                "operation",
                "operation_revision",
                "input",
                "proposed_output",
                "provenance",
                "created_at_us",
            ),
        )
        self.assertEqual(
            tuple(PendingProposalGap.__dataclass_fields__),
            ("proposal_id", "operation_revision", "input_hash"),
        )
        self.assertTrue(ProposalView.__dataclass_params__.frozen)
        self.assertTrue(PendingProposalGap.__dataclass_params__.frozen)

    def test_no_proposal_shape_carries_request_identity(self) -> None:
        for shape in (ReviewResult, ProposalView, PendingProposalGap):
            with self.subTest(shape=shape.__name__):
                self.assertNotIn("request_id", shape.__dataclass_fields__)

    def test_handle_lifecycle_shapes_keep_their_request_identity(self) -> None:
        # D10: these are handle-lifecycle values owned by a later unit. They keep the field;
        # what changed is that no review or proposal read reaches them.
        for name in (
            "Resolved",
            "Rejected",
            "ReviewRequired",
            "InProgress",
            "FallbackFailed",
            "ReconciliationRequired",
            "CandidateRequest",
        ):
            with self.subTest(shape=name):
                self.assertIn(
                    "request_id", getattr(models, name).__dataclass_fields__
                )

    def test_review_returns_review_result_and_keeps_its_keyword_only_marker(self) -> None:
        signature = inspect.signature(system.System.review)
        self.assertIs(
            typing.get_type_hints(system.System.review)["return"], ReviewResult
        )
        kinds = {
            name: parameter.kind for name, parameter in signature.parameters.items()
        }
        self.assertEqual(kinds["partition"], inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(kinds["proposal_id"], inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for name in ("reviewer", "decision", "corrected_output", "note"):
            self.assertEqual(kinds[name], inspect.Parameter.KEYWORD_ONLY)

    def test_review_result_is_exported(self) -> None:
        import cement_runtime

        self.assertIn("ReviewResult", cement_runtime.__all__)
        self.assertIs(cement_runtime.ReviewResult, ReviewResult)


if __name__ == "__main__":
    unittest.main()
