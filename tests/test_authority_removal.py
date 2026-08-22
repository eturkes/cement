"""M3.1 closure battery: the authority callback is gone and identity recording survives.

A green suite is never closure for a removal, because deleting a behavior together with
its pin keeps the gate green. Every test here fails when one removal obligation stays
undone, or when one deliberately preserved invariant disappears.
"""

from __future__ import annotations

import inspect
import pathlib
import re
import typing
import unittest

from cement_runtime import cli, system


def _root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve().parent
    while not (here / "pyproject.toml").exists():
        here = here.parent
    return here


ROOT = _root()
SOURCES = tuple(sorted((ROOT / "src").rglob("*.py")))
DOCS = (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")))
# This battery names every forbidden token, so it must exclude itself from its own scans.
TESTS = tuple(
    path
    for path in sorted((ROOT / "tests").glob("*.py"))
    if path.name != pathlib.Path(__file__).name
)

# Every surviving `authoriz` occurrence, classified. An unclassified survivor fails the
# unit: a removal budget counted by substring is inflated by name collisions.
ALLOWED_SURVIVORS = (
    # The caller owns its own live authorization gate. Cement decides no permission.
    "live authorization/policy gate",
    "Re-run live authorization/policy",
    "Re-run live policy and authorization",
    "authentication, authorization, policy",
    "Authentication, authorization,",
    "Authenticate and authorize every control-plane call",
    "your service already authorized access",
    # SQLite's own read-only prover, unrelated to the deleted Cement callback.
    "set_authorizer",
    "def authorize(",
    "read_only_by_authorizer",
)


class ResidueTests(unittest.TestCase):
    """Absence predicates R1-R13 of `.agent/decisions/m3u1-contract.md`."""

    def _hits(self, paths: tuple[pathlib.Path, ...], pattern: str) -> list[str]:
        found: list[str] = []
        for path in paths:
            for number, line in enumerate(path.read_text().splitlines(), start=1):
                if re.search(pattern, line):
                    found.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
        return found

    def test_callback_symbols_are_absent_from_the_package(self) -> None:
        for token in (
            r"\bAuthorityCheck\b",  # R1
            r"\b_authorize\b",  # R2
            r"\b_authority\b",  # R3
            r"authority\s*=",  # R4
            r"\bauthorized_(revision|ids|member_ids|candidate_ids|retired_ids)\b",  # R9
        ):
            with self.subTest(token=token):
                self.assertEqual(self._hits(SOURCES, token), [])

    def test_callback_messages_are_absent_everywhere(self) -> None:
        for message in (
            "authority must be callable",  # R5
            "actor is not authorized for",  # R6
            "draft eligibility changed during authorization",  # R7
            "function promotion candidates changed during authorization",  # R8
        ):
            with self.subTest(message=message):
                self.assertEqual(self._hits(SOURCES + DOCS + TESTS, re.escape(message)), [])

    def test_documentation_makes_no_callback_promise(self) -> None:
        for phrase in ("authority callback", "authority-free", "authority conflict"):
            with self.subTest(phrase=phrase):  # R10, R11, R12
                self.assertEqual(self._hits(DOCS, re.escape(phrase)), [])

    def test_every_surviving_authorization_mention_is_classified(self) -> None:
        unclassified = [
            hit
            for hit in self._hits(SOURCES + DOCS + TESTS, r"[Aa]uthoriz")
            if not any(allowed in hit for allowed in ALLOWED_SURVIVORS)
        ]
        self.assertEqual(unclassified, [], "R13: classify or remove each survivor")

    def test_the_constructor_keyword_is_gone_rather_than_ignored(self) -> None:
        with self.assertRaises(TypeError):  # D1: a silently ignored keyword would lie
            system.System(str(ROOT / "unreachable.db"), authority=lambda *_: True)
        with self.assertRaises(TypeError):
            system.System(str(ROOT / "unreachable.db"), authority=None)


class FrozenShapeTests(unittest.TestCase):
    """Preserved invariants P3-P5: shapes behavioral tests cannot see."""

    def test_system_constructor_shape(self) -> None:  # P3
        parameters = inspect.signature(system.System.__init__).parameters
        self.assertEqual(
            list(parameters),
            ["self", "database", "candidate_source", "clock_us", "generation_lease_seconds"],
        )
        for name in ("candidate_source", "clock_us", "generation_lease_seconds"):
            self.assertIs(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIsNone(parameters["candidate_source"].default)
        self.assertIsNone(parameters["clock_us"].default)
        self.assertEqual(parameters["generation_lease_seconds"].default, 120)
        hints = typing.get_type_hints(system.System.__init__)
        self.assertIs(hints["return"], type(None))

    def test_library_identity_arguments_keep_their_required_or_defaulted_shape(self) -> None:
        # P5 / D2. Actor and reviewer arguments stop authorizing but keep their exact
        # public shape: making them uniformly required is a separate ABI expansion.
        expected = {
            "register_operation": ("registered_by", "local-system"),
            "revise_operation": ("revised_by", inspect.Parameter.empty),
            "review": ("reviewer", inspect.Parameter.empty),
            "compile": ("compiled_by", "local-system"),
            "verify": ("verified_by", "local-system"),
            "promote": ("promoted_by", inspect.Parameter.empty),
            "challenge": ("reviewer", inspect.Parameter.empty),
            "revoke_example": ("revoked_by", inspect.Parameter.empty),
            "suspend_artifact": ("suspended_by", inspect.Parameter.empty),
            "verify_drafts": ("verified_by", inspect.Parameter.empty),
            "promote_function": ("promoted_by", inspect.Parameter.empty),
        }
        self.assertEqual(len(expected), 11)
        for method, (argument, default) in expected.items():
            with self.subTest(method=method):
                parameters = inspect.signature(getattr(system.System, method)).parameters
                self.assertIn(argument, parameters)
                self.assertIs(parameters[argument].kind, inspect.Parameter.KEYWORD_ONLY)
                self.assertEqual(parameters[argument].default, default)


class IdentityFlagCensusTests(unittest.TestCase):
    """Preserved invariant P4: the CLI keeps every identity flag it exposed."""

    # (leaf path, flag, required, default)
    EXPECTED = (
        (("operation", "revise"), "--actor", True, None),
        (("operation", "register"), "--actor", False, "local-system"),
        (("proposal", "review"), "--reviewer", True, None),
        (("compile",), "--actor", False, "local-system"),
        (("verify",), "--actor", False, "local-system"),
        (("promote",), "--actor", True, None),
        (("challenge",), "--reviewer", True, None),
        (("example", "revoke"), "--actor", True, None),
        (("artifact", "suspend"), "--actor", True, None),
        (("function", "verify-drafts"), "--actor", True, None),
        (("function", "promote"), "--actor", True, None),
    )

    @staticmethod
    def _leaves(parser, prefix=()):  # derive the census, never copy a written number
        import argparse

        subparsers = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if not subparsers:
            yield prefix, parser
            return
        for action in subparsers:
            for name, child in action.choices.items():
                yield from IdentityFlagCensusTests._leaves(child, (*prefix, name))

    def test_identity_flags_keep_their_exact_shape(self) -> None:
        leaves = dict(self._leaves(cli._parser()))
        self.assertEqual(len(self.EXPECTED), 11)
        for path, flag, required, default in self.EXPECTED:
            with self.subTest(command=" ".join(path), flag=flag):
                self.assertIn(path, leaves)
                option = next(
                    (
                        action
                        for action in leaves[path]._actions
                        if flag in action.option_strings
                    ),
                    None,
                )
                self.assertIsNotNone(option, f"{' '.join(path)} lost {flag}")
                assert option is not None
                self.assertEqual(option.required, required)
                self.assertEqual(option.default, default)


class LockedGuardTests(unittest.TestCase):
    """Preserved invariant P11: both locked transition guards survive the collapse."""

    def test_promote_function_keeps_both_locked_guards(self) -> None:
        source = inspect.getsource(system.System.promote_function)
        for guard in (
            "expected_function_hash does not match the locked prospective function",
            "function predecessor changed before locked retirement",
            "function candidate changed before locked activation",
            "function promotion requires at least one member",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, source)

    def test_each_collapsed_method_plans_exactly_once(self) -> None:
        # D4/D5: the second plan existed only to bind the removed callback's subject set.
        self.assertEqual(
            inspect.getsource(system.System.verify_drafts).count(
                "self._draft_verification_plan("
            ),
            1,
        )
        self.assertEqual(
            inspect.getsource(system.System.promote_function).count(
                "self._function_promotion_plan("
            ),
            1,
        )

    def test_the_expected_hash_conflict_precedes_the_clock_read(self) -> None:
        # Narrowing against 3a53389, where the clock read sat between the unlocked plan
        # and the locked hash comparison: a caller passing both a stale
        # `expected_function_hash` and a failing `clock_us` saw the clock `StateError`.
        # The collapse moves the comparison ahead of the clock, so `ConflictError` wins.
        source = inspect.getsource(system.System.promote_function)
        self.assertLess(
            source.index("expected_function_hash does not match"),
            source.index("self._now()"),
        )

    def test_neither_collapsed_method_reads_the_clock_before_its_lock(self) -> None:
        # D4 correction: a clock read before `BEGIN IMMEDIATE` lets a draft committed
        # after that read be verified with an earlier timestamp.
        for method in (system.System.verify_drafts, system.System.promote_function):
            with self.subTest(method=method.__name__):
                source = inspect.getsource(method)
                self.assertLess(
                    source.index("with self.store.transaction(write=True)"),
                    source.index("self._now()"),
                )


if __name__ == "__main__":
    unittest.main()
