"""M3.2b acceptance battery - one obligation at a time.

Seeded by `uv run python .agent/decisions/m3u2b-battery-validate.py --emit-stub <path>` from the
obligation set in that grader, which is derived from `.agent/decisions/m3u2b-contract.md`.

Fill one test per commit. Replace the seeded `self.skipTest` with the real probe; keep the leading
`Bnn:` docstring claim, because the grader reads it. A test may cover only the obligation it claims.
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest
from unittest import mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    FunctionResolution,
    Resolved,
    ReviewRequired,
    System,
)


class _Clock:
    def __init__(self, now_us: int = 1_000_000) -> None:
        self.now_us = now_us
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        return self.now_us


class _Source:
    def __init__(self) -> None:
        self.calls = []

    def propose(self, request):
        self.calls.append(request)
        return Candidate(output={"echo": request.input}, provenance={"model": "battery"})


class ResolveBatteryTests(unittest.TestCase):
    def _make_system(
        self,
        *,
        partition: str = "tenant_a",
        operation: str = "echo_1",
    ) -> tuple[System, pathlib.Path, _Source, _Clock]:
        temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(temporary.cleanup)
        database = pathlib.Path(temporary.name) / "cement.db"
        source = _Source()
        clock = _Clock()
        system = System(database, candidate_source=source, clock_us=clock)
        system.register_operation(
            partition,
            operation,
            policy=CompilePolicy(2, 2, 0),
        )
        return system, database, source, clock

    def _confirm(
        self,
        system: System,
        partition: str,
        operation: str,
        input_value: object,
        prefix: str,
    ) -> None:
        for index, reviewer in enumerate(("alice", "bob"), start=1):
            outcome = system.handle(
                partition,
                operation,
                input_value,
                request_id=f"{prefix}-{index}",
            )
            self.assertIs(type(outcome), ReviewRequired)
            system.review(
                partition,
                outcome.proposal_id,
                reviewer=reviewer,
                decision="accept",
            )

    def _promote_values(
        self,
        system: System,
        values: tuple[object, ...],
        *,
        partition: str = "tenant_a",
        operation: str = "echo_1",
        prefix: str = "battery",
    ) -> tuple[tuple[str, ...], str]:
        for index, value in enumerate(values):
            self._confirm(
                system,
                partition,
                operation,
                value,
                f"{prefix}-{index}",
            )
        compiled = system.compile(partition, operation)
        self.assertEqual(len(compiled.created), len(values))
        for artifact_id in compiled.created:
            report = system.verify(partition, artifact_id)
            self.assertTrue(report.passed)
            system.promote(
                partition,
                artifact_id,
                scope_hash=report.scope_hash,
                promoted_by="release-manager",
            )
        manifest = system.inspect_function_promotion(partition, operation)
        system.promote_function(
            partition,
            operation,
            expected_function_hash=manifest.function_hash,
            promoted_by="release-manager",
        )
        return compiled.created, manifest.function_hash
    def test_b01(self) -> None:
        """
        B01: resolve's signature ABI is frozen: parameter names and order (partition, operation,
        input_value), the keyword-only marker before expected_function_hash, its None default,
        and the FunctionResolution return annotation, pinned by inspect.signature plus
        typing.get_type_hints
        """

        import inspect
        import typing

        from cement_runtime import FunctionResolution, System

        signature = inspect.signature(System.resolve)
        parameters = tuple(signature.parameters.values())
        self.assertEqual(
            tuple(parameter.name for parameter in parameters),
            ("self", "partition", "operation", "input_value", "expected_function_hash"),
        )
        self.assertEqual(
            tuple(parameter.kind for parameter in parameters),
            (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ),
        )
        self.assertIs(parameters[-1].default, None)
        hints = typing.get_type_hints(System.resolve)
        self.assertEqual(hints["partition"], str)
        self.assertEqual(hints["operation"], str)
        self.assertEqual(hints["input_value"], object)
        self.assertEqual(hints["expected_function_hash"], str | None)
        self.assertIs(hints["return"], FunctionResolution)

    def test_b02(self) -> None:
        """
        B02: FunctionResolution's shape is frozen: frozen=True, slots=True, NO kw_only so
        positional construction works, exactly the two fields verification and match, and
        resolved type hints
        """

        import dataclasses
        import inspect
        import typing

        from cement_runtime import (
            FunctionMatch,
            FunctionResolution,
            FunctionVerification,
        )

        verification = FunctionVerification(False, 0, None, None, ())
        resolution = FunctionResolution(verification, None)
        self.assertIs(resolution.verification, verification)
        self.assertIsNone(resolution.match)
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(FunctionResolution)),
            ("verification", "match"),
        )
        self.assertEqual(
            typing.get_type_hints(FunctionResolution),
            {
                "verification": FunctionVerification,
                "match": FunctionMatch | None,
            },
        )
        self.assertEqual(
            tuple(
                parameter.kind
                for parameter in inspect.signature(FunctionResolution).parameters.values()
            ),
            (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ),
        )
        self.assertTrue(FunctionResolution.__dataclass_params__.frozen)
        self.assertFalse(FunctionResolution.__dataclass_params__.kw_only)
        self.assertTrue(FunctionResolution.__dataclass_params__.slots)
        self.assertFalse(hasattr(resolution, "__dict__"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            resolution.match = None

    def test_b03(self) -> None:
        """
        B03: FunctionResolution is exported from cement_runtime and sits in __all__ in
        alphabetical position, between FunctionReport and FunctionSetPromotion
        """

        import cement_runtime
        from cement_runtime.models import FunctionResolution as ModelFunctionResolution

        self.assertIs(cement_runtime.FunctionResolution, ModelFunctionResolution)
        names = tuple(cement_runtime.__all__)
        index = names.index("FunctionResolution")
        self.assertEqual(
            names[index - 1 : index + 2],
            ("FunctionReport", "FunctionResolution", "FunctionSetPromotion"),
        )

    def test_b04(self) -> None:
        """
        B04: the two live resolve vocabularies never cross-wire: resolve returns exactly
        FunctionResolution by type identity and constructs no Resolved, and handle constructs no
        FunctionResolution
        """

        system, _, _, _ = self._make_system()
        self._promote_values(system, ({"n": 12},), prefix="cross-wire")

        with mock.patch(
            "cement_runtime.system.Resolved",
            side_effect=AssertionError("resolve constructed Resolved"),
        ):
            resolution = system.resolve("tenant_a", "echo_1", {"n": 12})
        self.assertIs(type(resolution), FunctionResolution)

        with mock.patch(
            "cement_runtime.system.FunctionResolution",
            side_effect=AssertionError("handle constructed FunctionResolution"),
        ):
            outcome = system.handle(
                "tenant_a",
                "echo_1",
                {"n": 12},
                request_id="cross-wire-handle",
            )
        self.assertIs(type(outcome), Resolved)

    def test_b05(self) -> None:
        """
        B05: verified hit shape: passed True, matched True, output equal to the promoted output,
        artifact_hash the promoted member's 64-hex digest, and verification.document present
        """

        from cement_runtime import FunctionMatch

        system, _, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 12},),
            prefix="verified-hit",
        )
        promoted = system.artifact("tenant_a", artifact_ids[0])

        resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertTrue(resolution.verification.passed)
        self.assertIsNotNone(resolution.verification.document)
        self.assertIs(type(resolution.match), FunctionMatch)
        assert resolution.match is not None
        self.assertTrue(resolution.match.matched)
        self.assertEqual(resolution.match.output, {"echo": {"n": 12}})
        self.assertEqual(resolution.match.artifact_hash, promoted["artifact_hash"])
        self.assertRegex(resolution.match.artifact_hash or "", r"^[0-9a-f]{64}$")

    def test_b06(self) -> None:
        """
        B06: verified miss shape: passed True, matched False, output None, artifact_hash None,
        and verification.document present
        """

        from cement_runtime import FunctionMatch

        system, _, _, _ = self._make_system()
        self._promote_values(system, ({"n": 12},), prefix="verified-miss")

        resolution = system.resolve("tenant_a", "echo_1", {"n": 13})

        self.assertTrue(resolution.verification.passed)
        self.assertIsNotNone(resolution.verification.document)
        self.assertIs(type(resolution.match), FunctionMatch)
        assert resolution.match is not None
        self.assertFalse(resolution.match.matched)
        self.assertIsNone(resolution.match.output)
        self.assertIsNone(resolution.match.artifact_hash)

    def test_b07(self) -> None:
        """
        B07: failed verdict shape: passed False, match None, verification.document None
        """

        system, _, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="failed-verdict",
        )
        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )

        resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertFalse(resolution.verification.passed)
        self.assertIsNone(resolution.match)
        self.assertIsNone(resolution.verification.document)

    def test_b08(self) -> None:
        """
        B08: the six checks keep verify_function's keys and emitted order and are neither
        renamed nor re-scored: duplicate-input-digests, abi-canonicalizer-uniform,
        sealed-passing-reports, current-promotion-receipts, function-hash-matches-snapshot,
        persisted-function-receipt
        """

        system, _, _, _ = self._make_system()
        verification = system.verify_function("tenant_a", "echo_1")

        with mock.patch.object(system, "verify_function", return_value=verification):
            resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertIs(resolution.verification, verification)
        self.assertEqual(
            tuple((check.key, check.passed) for check in resolution.verification.checks),
            (
                ("duplicate-input-digests", True),
                ("abi-canonicalizer-uniform", True),
                ("sealed-passing-reports", True),
                ("current-promotion-receipts", True),
                ("function-hash-matches-snapshot", True),
                ("persisted-function-receipt", True),
            ),
        )
        self.assertEqual(
            resolution.verification.passed,
            all(check.passed for check in resolution.verification.checks),
        )

    def test_b09(self) -> None:
        """
        B09: capacity is an adjacent accept/reject pair at the effective FUNCTION_MAX_ENTRIES: a
        set of exactly N entries verifies and N+1 returns passed False with all six checks
        False, entries set to the real count, document None, and zero row enumeration
        (FABRICATED: the cap is patched, never built to 50,000)
        """

        system, _, _, _ = self._make_system()
        self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="capacity",
        )

        with mock.patch("cement_runtime.system.FUNCTION_MAX_ENTRIES", 3):
            accepted = system.resolve("tenant_a", "echo_1", {"n": 12})
        self.assertTrue(accepted.verification.passed)
        self.assertIsNotNone(accepted.match)

        with (
            mock.patch("cement_runtime.system.FUNCTION_MAX_ENTRIES", 2),
            mock.patch.object(
                System,
                "_promoted_function_rows",
                side_effect=AssertionError("over-capacity set was enumerated"),
            ) as enumerate_rows,
        ):
            rejected = system.resolve("tenant_a", "echo_1", {"n": 12})

        enumerate_rows.assert_not_called()
        self.assertFalse(rejected.verification.passed)
        self.assertEqual(rejected.verification.entries, 3)
        self.assertEqual(
            tuple(check.passed for check in rejected.verification.checks),
            (False, False, False, False, False, False),
        )
        self.assertIsNone(rejected.verification.document)
        self.assertIsNone(rejected.match)

    def test_b10(self) -> None:
        """
        B10: an over-capacity failed verdict is NOT a miss: it is distinguishable from a
        verified miss by verification.passed and match alone, with no consumer needing the check
        detail
        """

        system, _, _, _ = self._make_system()
        self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="capacity-vs-miss",
        )

        with mock.patch("cement_runtime.system.FUNCTION_MAX_ENTRIES", 2):
            failed = system.resolve("tenant_a", "echo_1", {"n": 99})
        with mock.patch("cement_runtime.system.FUNCTION_MAX_ENTRIES", 3):
            miss = system.resolve("tenant_a", "echo_1", {"n": 99})

        self.assertEqual((failed.verification.passed, failed.match), (False, None))
        self.assertTrue(miss.verification.passed)
        self.assertIsNotNone(miss.match)
        assert miss.match is not None
        self.assertFalse(miss.match.matched)
        self.assertNotEqual(
            (failed.verification.passed, failed.match),
            (miss.verification.passed, miss.match),
        )

    def test_b11(self) -> None:
        """
        B11: match is None iff verification.passed is False, both directions asserted, over
        every verification verify_function actually produces (hit, miss, and at least one failed
        verdict)
        """

        system, _, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="biconditional",
        )
        hit = system.resolve("tenant_a", "echo_1", {"n": 12})
        miss = system.resolve("tenant_a", "echo_1", {"n": 99})
        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        failed = system.resolve("tenant_a", "echo_1", {"n": 12})

        for label, resolution in (("hit", hit), ("miss", miss), ("failed", failed)):
            with self.subTest(state=label):
                self.assertEqual(
                    resolution.match is None,
                    resolution.verification.passed is False,
                )

    def test_b12(self) -> None:
        """
        B12: evaluate call counts by state, taken with a spy: hit 1, miss 1, failed verdict 0,
        so evaluation never runs on a failed verdict
        """

        from cement_runtime import evaluate

        system, _, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="evaluate-counts",
        )

        counts = {}
        for state, input_value in (("hit", {"n": 12}), ("miss", {"n": 99})):
            with mock.patch("cement_runtime.system.evaluate", wraps=evaluate) as evaluate_spy:
                system.resolve("tenant_a", "echo_1", input_value)
            counts[state] = evaluate_spy.call_count

        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        with mock.patch("cement_runtime.system.evaluate", wraps=evaluate) as evaluate_spy:
            system.resolve("tenant_a", "echo_1", {"n": 12})
        counts["failed"] = evaluate_spy.call_count

        self.assertEqual(counts, {"hit": 1, "miss": 1, "failed": 0})

    def test_b13(self) -> None:
        """
        B13: a registered operation with a zero-entry promoted set is a verified miss for every
        input, never an error: passed True, entries 0, matched False
        """

        system, _, _, _ = self._make_system()

        for input_value in (None, {"n": 12}, [1, 2, 13], "absent"):
            with self.subTest(input_value=input_value):
                resolution = system.resolve("tenant_a", "echo_1", input_value)
                self.assertTrue(resolution.verification.passed)
                self.assertEqual(resolution.verification.entries, 0)
                self.assertIsNotNone(resolution.match)
                assert resolution.match is not None
                self.assertFalse(resolution.match.matched)
                self.assertIsNone(resolution.match.output)
                self.assertIsNone(resolution.match.artifact_hash)

    def test_b14(self) -> None:
        """
        B14: the `or document is None` clause is forced: a FABRICATED public
        FunctionVerification(passed=True, document=None) reaching resolve through an override of
        public verify_function returns match None instead of raising AttributeError
        """

        from cement_runtime import FunctionVerification

        system, _, _, _ = self._make_system()
        fabricated = FunctionVerification(True, 0, None, None, ())

        with (
            mock.patch.object(system, "verify_function", return_value=fabricated),
            mock.patch(
                "cement_runtime.system.evaluate",
                side_effect=AssertionError("document=None reached evaluate"),
            ) as evaluate_spy,
        ):
            resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertIs(resolution.verification, fabricated)
        self.assertIsNone(resolution.match)
        evaluate_spy.assert_not_called()

    def test_b15(self) -> None:
        """
        B15: each rejected argument carries its exact class and message: partition, operation,
        expected_function_hash 64-hex shape, and an input canonicalize refuses, including one
        above DEFAULT_MAX_BYTES
        """

        from cement_runtime import ValidationError
        from cement_runtime.json_value import DEFAULT_MAX_BYTES

        system, _, _, _ = self._make_system()
        cases = (
            (
                "partition",
                lambda: system.resolve("", "echo_1", None),
                "partition must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'",
            ),
            (
                "operation",
                lambda: system.resolve("tenant_a", "", None),
                "operation must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'",
            ),
            (
                "expected hash",
                lambda: system.resolve(
                    "tenant_a",
                    "echo_1",
                    None,
                    expected_function_hash="not-a-digest",
                ),
                "expected_function_hash must be a SHA-256 hex digest",
            ),
            (
                "input type",
                lambda: system.resolve("tenant_a", "echo_1", object()),
                "value of type 'object' is not JSON",
            ),
            (
                "input bytes",
                lambda: system.resolve(
                    "tenant_a",
                    "echo_1",
                    "x" * DEFAULT_MAX_BYTES,
                ),
                "canonical JSON exceeds 1048576 bytes",
            ),
        )
        for label, call, message in cases:
            with self.subTest(argument=label), self.assertRaises(ValidationError) as caught:
                call()
            self.assertEqual(str(caught.exception), message)

    def test_b16(self) -> None:
        """
        B16: precedence is pinned by four ADJACENT-edge multi-invalid pairs: partition+operation
        reports partition, operation+expected hash reports operation, expected hash+input
        reports the expected hash, partition+input reports partition
        """

        from cement_runtime import ValidationError

        system, _, _, _ = self._make_system()
        partition_message = (
            "partition must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"
        )
        operation_message = (
            "operation must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"
        )
        hash_message = "expected_function_hash must be a SHA-256 hex digest"
        pairs = (
            (
                "partition before operation",
                lambda: system.resolve("", "", None),
                partition_message,
            ),
            (
                "operation before expected hash",
                lambda: system.resolve(
                    "tenant_a",
                    "",
                    None,
                    expected_function_hash="bad",
                ),
                operation_message,
            ),
            (
                "expected hash before input",
                lambda: system.resolve(
                    "tenant_a",
                    "echo_1",
                    object(),
                    expected_function_hash="bad",
                ),
                hash_message,
            ),
            (
                "partition before input",
                lambda: system.resolve("", "echo_1", object()),
                partition_message,
            ),
        )
        for label, call, message in pairs:
            with self.subTest(edge=label), self.assertRaises(ValidationError) as caught:
                call()
            self.assertEqual(str(caught.exception), message)

    def test_b17(self) -> None:
        """
        B17: all validation precedes any ledger read: a call section 4 rejects makes ZERO
        Store.transaction calls and ZERO verify_function calls, taken with spies
        """

        from cement_runtime import ValidationError
        from cement_runtime.json_value import DEFAULT_MAX_BYTES

        system, _, _, _ = self._make_system()
        rejected_calls = (
            lambda: system.resolve("", "echo_1", None),
            lambda: system.resolve("tenant_a", "", None),
            lambda: system.resolve(
                "tenant_a",
                "echo_1",
                None,
                expected_function_hash="bad",
            ),
            lambda: system.resolve("tenant_a", "echo_1", object()),
            lambda: system.resolve(
                "tenant_a",
                "echo_1",
                "x" * DEFAULT_MAX_BYTES,
            ),
        )
        for index, call in enumerate(rejected_calls):
            with (
                self.subTest(rejection=index),
                mock.patch.object(
                    system.store,
                    "transaction",
                    wraps=system.store.transaction,
                ) as transaction_spy,
                mock.patch.object(
                    system,
                    "verify_function",
                    wraps=system.verify_function,
                ) as verify_spy,
                self.assertRaises(ValidationError),
            ):
                call()
            transaction_spy.assert_not_called()
            verify_spy.assert_not_called()

    def test_b18(self) -> None:
        """
        B18: ledger bytes are unmoved: sha256 of the ledger file AND the full
        connection.iterdump() text are byte-identical across a hit, a miss and a failed verdict
        """

        import hashlib
        import sqlite3

        system, database, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="ledger-stability",
        )

        def snapshot() -> tuple[str, str]:
            digest = hashlib.sha256(database.read_bytes()).hexdigest()
            connection = sqlite3.connect(database)
            try:
                dump = "\n".join(connection.iterdump())
            finally:
                connection.close()
            return digest, dump

        states = (
            ("hit", {"n": 12}),
            ("miss", {"n": 99}),
        )
        for label, input_value in states:
            before = snapshot()
            system.resolve("tenant_a", "echo_1", input_value)
            after = snapshot()
            with self.subTest(state=label):
                self.assertEqual(after, before)

        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        before = snapshot()
        failed = system.resolve("tenant_a", "echo_1", {"n": 12})
        after = snapshot()
        self.assertFalse(failed.verification.passed)
        self.assertEqual(after, before)

    def test_b19(self) -> None:
        """
        B19: the clock is never read: a System whose _now raises resolves all three states and
        returns the same resolutions
        """

        system, database, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="clock-purity",
        )
        baseline_reader = System(database, clock_us=lambda: 2_000_000)
        raising_clock = mock.Mock(side_effect=AssertionError("resolve read the clock"))
        guarded_reader = System(database, clock_us=raising_clock)

        for label, input_value in (("hit", {"n": 12}), ("miss", {"n": 99})):
            expected = baseline_reader.resolve("tenant_a", "echo_1", input_value)
            actual = guarded_reader.resolve("tenant_a", "echo_1", input_value)
            with self.subTest(state=label):
                self.assertEqual(actual, expected)

        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        expected = baseline_reader.resolve("tenant_a", "echo_1", {"n": 12})
        actual = guarded_reader.resolve("tenant_a", "echo_1", {"n": 12})
        self.assertFalse(actual.verification.passed)
        self.assertEqual(actual, expected)
        raising_clock.assert_not_called()

    def test_b20(self) -> None:
        """
        B20: no event is emitted: events() is byte-identical and the event sequence counter is
        unmoved across all three states
        """

        import json
        import sqlite3

        system, database, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="event-purity",
        )

        def event_snapshot() -> tuple[bytes, int | None]:
            event_bytes = json.dumps(
                system.events("tenant_a"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            connection = sqlite3.connect(database)
            try:
                row = connection.execute(
                    "SELECT seq FROM sqlite_sequence WHERE name = 'events'"
                ).fetchone()
            finally:
                connection.close()
            return event_bytes, None if row is None else int(row[0])

        for label, input_value in (("hit", {"n": 12}), ("miss", {"n": 99})):
            before = event_snapshot()
            system.resolve("tenant_a", "echo_1", input_value)
            after = event_snapshot()
            with self.subTest(state=label):
                self.assertEqual(after, before)

        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        before = event_snapshot()
        failed = system.resolve("tenant_a", "echo_1", {"n": 12})
        after = event_snapshot()
        self.assertFalse(failed.verification.passed)
        self.assertEqual(after, before)

    def test_b21(self) -> None:
        """
        B21: no identifier is allocated, including a discarded one:
        cement_runtime.system.uuid.uuid4 patched to raise resolves all three states unchanged
        """

        system, _, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="identifier-purity",
        )

        for label, input_value in (("hit", {"n": 12}), ("miss", {"n": 99})):
            expected = system.resolve("tenant_a", "echo_1", input_value)
            with mock.patch(
                "cement_runtime.system.uuid.uuid4",
                side_effect=AssertionError("resolve allocated an identifier"),
            ) as uuid_spy:
                actual = system.resolve("tenant_a", "echo_1", input_value)
            with self.subTest(state=label):
                self.assertEqual(actual, expected)
                uuid_spy.assert_not_called()

        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        expected = system.resolve("tenant_a", "echo_1", {"n": 12})
        with mock.patch(
            "cement_runtime.system.uuid.uuid4",
            side_effect=AssertionError("resolve allocated an identifier"),
        ) as uuid_spy:
            actual = system.resolve("tenant_a", "echo_1", {"n": 12})
        self.assertEqual(actual, expected)
        uuid_spy.assert_not_called()

    def test_b22(self) -> None:
        """
        B22: no file is created: the full ledger DIRECTORY listing is identical across a hit, a
        miss and a failed verdict
        """

        system, database, _, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="file-purity",
        )

        def directory_listing() -> tuple[str, ...]:
            return tuple(sorted(entry.name for entry in database.parent.iterdir()))

        for label, input_value in (("hit", {"n": 12}), ("miss", {"n": 99})):
            before = directory_listing()
            system.resolve("tenant_a", "echo_1", input_value)
            after = directory_listing()
            with self.subTest(state=label):
                self.assertEqual(after, before)

        system.suspend_artifact(
            "tenant_a",
            artifact_ids[1],
            suspended_by="auditor",
            reason="battery failed state",
        )
        before = directory_listing()
        failed = system.resolve("tenant_a", "echo_1", {"n": 12})
        after = directory_listing()
        self.assertFalse(failed.verification.passed)
        self.assertEqual(after, before)

    def test_b23(self) -> None:
        """
        B23: a deleted ledger raises the contracted IntegrityError and does not recreate the
        path, checked absent before and after
        """

        from cement_runtime import IntegrityError

        system, database, _, _ = self._make_system()
        database.unlink()
        self.assertFalse(database.exists())

        with self.assertRaises(IntegrityError) as caught:
            system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertEqual(str(caught.exception), "ledger file is missing or unreadable")
        self.assertFalse(database.exists())

    def test_b24(self) -> None:
        """
        B24: no CandidateSource is invoked: a source spy records zero propose calls on ALL THREE
        states, with a raising propose as the belt-and-braces form
        """

        system, _, source, _ = self._make_system()
        artifact_ids, _ = self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="source-purity",
        )
        source.calls.clear()

        with mock.patch.object(
            source,
            "propose",
            side_effect=AssertionError("resolve invoked CandidateSource.propose"),
        ) as propose_spy:
            hit = system.resolve("tenant_a", "echo_1", {"n": 12})
            miss = system.resolve("tenant_a", "echo_1", {"n": 99})
            system.suspend_artifact(
                "tenant_a",
                artifact_ids[1],
                suspended_by="auditor",
                reason="battery failed state",
            )
            failed = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertTrue(hit.verification.passed)
        self.assertTrue(miss.verification.passed)
        self.assertFalse(failed.verification.passed)
        self.assertEqual(source.calls, [])
        propose_spy.assert_not_called()

    def test_b25(self) -> None:
        """
        B25: exactly ONE Store.transaction(write=False) opens per resolve that reaches the
        ledger, and ZERO for a call section 4 rejects, both counted by a wraps= spy
        """

        from cement_runtime import ValidationError

        system, _, _, _ = self._make_system()
        self._promote_values(system, ({"n": 12},), prefix="one-snapshot")

        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transaction_spy:
            system.resolve("tenant_a", "echo_1", {"n": 12})
        self.assertEqual(transaction_spy.call_args_list, [mock.call(write=False)])

        with mock.patch.object(
            system.store,
            "transaction",
            wraps=system.store.transaction,
        ) as transaction_spy:
            with self.assertRaises(ValidationError):
                system.resolve("", "echo_1", object())
        transaction_spy.assert_not_called()

    def test_b26(self) -> None:
        """
        B26: connection.in_transaction stays True across the whole six-check pass, sampled at
        the sixth check rather than only at entry
        """

        system, _, _, _ = self._make_system()
        self._promote_values(system, ({"n": 12},), prefix="snapshot-lifetime")
        original_check = system._persisted_function_receipt_check
        sixth_check_states: list[bool] = []

        def sampled_sixth_check(connection, **kwargs):
            sixth_check_states.append(connection.in_transaction)
            check = original_check(connection, **kwargs)
            self.assertEqual(check.key, "persisted-function-receipt")
            return check

        with mock.patch.object(
            system,
            "_persisted_function_receipt_check",
            side_effect=sampled_sixth_check,
        ) as sixth_check_spy:
            resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertTrue(resolution.verification.passed)
        self.assertEqual(
            tuple(check.key for check in resolution.verification.checks)[-1],
            "persisted-function-receipt",
        )
        self.assertEqual(sixth_check_states, [True])
        sixth_check_spy.assert_called_once()

    def test_b27(self) -> None:
        """
        B27: evaluation runs over the DOCUMENT VALUE: evaluating the returned document after the
        snapshot has closed equals evaluating it inside the snapshot, artifact hash included
        """

        from cement_runtime import evaluate
        from cement_runtime.json_value import canonicalize

        system, _, _, _ = self._make_system()
        self._promote_values(system, ({"n": 12},), prefix="document-value")
        resolution = system.resolve("tenant_a", "echo_1", {"n": 12})
        document = resolution.verification.document
        self.assertIsNotNone(document)
        assert document is not None
        input_json = canonicalize({"n": 12})

        with system.store.transaction(write=False) as connection:
            self.assertTrue(connection.in_transaction)
            inside_snapshot = evaluate(document, input_json=input_json)
        outside_snapshot = evaluate(document, input_json=input_json)

        self.assertEqual(outside_snapshot, inside_snapshot)
        self.assertEqual(outside_snapshot, resolution.match)
        self.assertTrue(outside_snapshot.matched)
        self.assertRegex(outside_snapshot.artifact_hash or "", r"^[0-9a-f]{64}$")

    def test_b28(self) -> None:
        """
        B28: the two conditions reachable through supported calls raise with exact class and
        message: an unregistered operation gives NotFoundError, a missing or unreadable ledger
        gives IntegrityError
        """

        from cement_runtime import IntegrityError, NotFoundError

        system, _, _, _ = self._make_system()
        with self.assertRaises(NotFoundError) as caught:
            system.resolve("tenant_a", "missing", {"n": 12})
        self.assertEqual(
            str(caught.exception),
            "operation is not registered in this partition",
        )

        missing_system, database, _, _ = self._make_system(operation="missing_ledger")
        database.unlink()
        with self.assertRaises(IntegrityError) as caught:
            missing_system.resolve("tenant_a", "missing_ledger", {"n": 12})
        self.assertEqual(str(caught.exception), "ledger file is missing or unreadable")
        self.assertFalse(database.exists())

    def test_b29(self) -> None:
        """
        B29: ordinary supported state changes give a FAILED VERDICT and never an exception: a
        suspended member, a revoked member, revision drift, and a valid-but-wrong
        expected_function_hash

        RED CONTRACT/CODE DIVERGENCE: public revise_operation retires every old artifact, so
        resolve sees a zero-entry current set and returns a verified miss; no supported call in
        the contract creates a stale promoted revision.
        """

        def assert_failed(label: str, resolution) -> None:
            with self.subTest(state_change=label):
                self.assertFalse(resolution.verification.passed)
                self.assertIsNone(resolution.verification.document)
                self.assertIsNone(resolution.match)

        for target_index, target_label in ((1, "middle"), (-1, "last")):
            system, _, _, _ = self._make_system()
            self._promote_values(
                system,
                ({"n": 11}, {"n": 12}, {"n": 13}),
                prefix=f"suspended-{target_label}",
            )
            target = system.inspect_function_promotion(
                "tenant_a", "echo_1"
            ).entries[target_index]
            system.suspend_artifact(
                "tenant_a",
                target.artifact_id,
                suspended_by="auditor",
                reason=f"battery {target_label} suspension",
            )
            assert_failed(
                f"suspended-{target_label}",
                system.resolve("tenant_a", "echo_1", {"n": 99}),
            )

        for target_index, target_label in ((1, "middle"), (-1, "last")):
            system, _, _, _ = self._make_system()
            self._promote_values(
                system,
                ({"n": 11}, {"n": 12}, {"n": 13}),
                prefix=f"revoked-{target_label}",
            )
            target = system.inspect_function_promotion(
                "tenant_a", "echo_1"
            ).entries[target_index]
            artifact = system.artifact("tenant_a", target.artifact_id)
            evidence_ids = artifact["evidence_ids"]
            self.assertIs(type(evidence_ids), list)
            suspended = system.revoke_example(
                "tenant_a",
                evidence_ids[0],
                revoked_by="auditor",
                reason=f"battery {target_label} revocation",
            )
            self.assertIn(target.artifact_id, suspended)
            assert_failed(
                f"revoked-{target_label}",
                system.resolve("tenant_a", "echo_1", {"n": 99}),
            )

        revision_system, _, _, _ = self._make_system()
        self._promote_values(
            revision_system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="revision-drift",
        )
        self.assertEqual(
            revision_system.revise_operation(
                "tenant_a",
                "echo_1",
                policy=CompilePolicy(3, 2, 0),
                revised_by="release-manager",
            ),
            2,
        )
        # MAIN RULING on this battery's red: through the supported route a revision
        # bump RETIRES every stranded artifact, so the current set is empty and
        # `resolve` answers a VERIFIED MISS, not a failed verdict. Contract section 7
        # is amended to say so; a genuinely stale promoted revision needs a fabricated
        # direct UPDATE and no supported call reaches it.
        with self.subTest(state_change="revision-drift"):
            drifted = revision_system.resolve("tenant_a", "echo_1", {"n": 99})
            self.assertTrue(drifted.verification.passed)
            self.assertEqual(drifted.verification.entries, 0)
            self.assertIsNotNone(drifted.match)
            self.assertFalse(drifted.match.matched)

        hash_system, _, _, _ = self._make_system()
        _, current_hash = self._promote_values(
            hash_system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="wrong-expected-hash",
        )
        wrong_hash = "0" * 64
        self.assertNotEqual(wrong_hash, current_hash)
        assert_failed(
            "wrong-expected-hash",
            hash_system.resolve(
                "tenant_a",
                "echo_1",
                {"n": 99},
                expected_function_hash=wrong_hash,
            ),
        )

    def test_b30(self) -> None:
        """
        B30: structurally corrupt bound content gives a FALSE check with bounded detail rather
        than a raise, corrupting the MIDDLE and the LAST of at least three entries
        (FABRICATED: public verification's row validator is overridden to inject corruption)
        """

        from cement_runtime import IntegrityError

        system, _, _, _ = self._make_system()
        self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}, {"n": 14}),
            prefix="bounded-corruption",
        )
        entries = system.inspect_function_promotion("tenant_a", "echo_1").entries
        ordered_ids = tuple(entry.artifact_id for entry in entries)
        corrupted_ids: list[str] = []

        def corrupt_bound_content(connection, row):
            del connection
            corrupted_ids.append(str(row["id"]))
            raise IntegrityError("fabricated bound-content defect")

        with mock.patch.object(
            System,
            "_validate_promoted",
            side_effect=corrupt_bound_content,
        ):
            resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertFalse(resolution.verification.passed)
        self.assertIsNone(resolution.match)
        self.assertEqual(set(corrupted_ids), set(ordered_ids))
        self.assertIn(ordered_ids[1], corrupted_ids)
        self.assertIn(ordered_ids[-1], corrupted_ids)
        checks = {check.key: check for check in resolution.verification.checks}
        receipt_check = checks["current-promotion-receipts"]
        self.assertFalse(receipt_check.passed)
        self.assertTrue(receipt_check.detail.startswith("4 failure(s): "))
        self.assertEqual(
            receipt_check.detail.count("fabricated bound-content defect"),
            3,
        )

    def test_b31(self) -> None:
        """
        B31: no shipped docstring reachable from resolve or FunctionResolution calls the path
        cheap, fast, cached, repeatable across calls, or a lease, and the cost referent stays
        citable

        RED CONTRACT/CODE DIVERGENCE: System.resolve cites the component-only m3u2b-bench.json;
        contract section 8 requires every resolver-cost claim to cite m3u2b-resolve-bench.json.
        """

        import inspect
        import json
        import re

        from cement_runtime import (
            FunctionMatch,
            FunctionResolution,
            FunctionVerification,
            evaluate,
        )

        reachable = {
            "System.resolve": System.resolve,
            "System.verify_function": System.verify_function,
            "evaluate": evaluate,
            "FunctionResolution": FunctionResolution,
            "FunctionVerification": FunctionVerification,
            "FunctionMatch": FunctionMatch,
        }
        forbidden = (
            re.compile(r"\bcheap\b"),
            re.compile(r"\bfast\b"),
            re.compile(r"\bcached\b"),
            re.compile(r"\brepeatable across calls\b"),
        )
        for label, target in reachable.items():
            documentation = (inspect.getdoc(target) or "").lower()
            for pattern in forbidden:
                with self.subTest(target=label, claim=pattern.pattern):
                    self.assertIsNone(pattern.search(documentation))
            affirmative_lease_text = documentation.replace("not a lease", "")
            with self.subTest(target=label, claim="lease"):
                self.assertNotRegex(affirmative_lease_text, r"\blease\b")

        referent = ".agent/decisions/m3u2b-resolve-bench.json"
        resolve_doc = inspect.getdoc(System.resolve) or ""
        self.assertIn(referent, resolve_doc)
        payload = json.loads(
            (pathlib.Path(__file__).resolve().parents[1] / referent).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["kind"], "resolve-bench")
        cap = payload["points"]["n50000"]
        self.assertEqual(cap["entries"], 50_000)
        self.assertEqual(cap["resolve_cold_hit_ms"], 37_227.984277)
        self.assertEqual(cap["peak_rss_kib"], 985_568)

    def test_b32(self) -> None:
        """
        B32: a canonically equivalent input resolves identically: the same object with reversed
        key insertion order gives the same matched output and the same artifact_hash
        """

        system, _, _, _ = self._make_system()
        forward = {"a": 1, "b": 12}
        reverse = {"b": 12, "a": 1}
        self._promote_values(system, (forward,), prefix="canonical-input")

        first = system.resolve("tenant_a", "echo_1", forward)
        second = system.resolve("tenant_a", "echo_1", reverse)

        self.assertIsNotNone(first.match)
        self.assertIsNotNone(second.match)
        assert first.match is not None and second.match is not None
        self.assertTrue(first.match.matched)
        self.assertTrue(second.match.matched)
        self.assertEqual(second.match.output, first.match.output)
        self.assertEqual(second.match.artifact_hash, first.match.artifact_hash)
        self.assertRegex(second.match.artifact_hash or "", r"^[0-9a-f]{64}$")

    def test_b33(self) -> None:
        """
        B33: scope isolation survives the forward to verify_function: collider partitions and
        operations (tenant_a vs tenantXa, echo_1 vs echoX1, plus a case variant) never answer
        each other, and partition and operation are not swapped
        """

        class ScopeSource:
            def propose(self, request):
                return Candidate(
                    output={
                        "input": request.input,
                        "scope": [request.partition, request.operation],
                    },
                    provenance={"model": "scope-battery"},
                )

        temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(temporary.cleanup)
        database = pathlib.Path(temporary.name) / "cement.db"
        system = System(database, candidate_source=ScopeSource(), clock_us=_Clock())
        scopes = (
            ("tenant_a", "echo_1"),
            ("tenantXa", "echo_1"),
            ("Tenant_A", "echo_1"),
            ("tenant_a", "echoX1"),
            ("tenant_a", "Echo_1"),
            ("echo_1", "tenant_a"),
        )
        for partition, operation in scopes:
            system.register_operation(
                partition,
                operation,
                policy=CompilePolicy(2, 2, 0),
            )
        for index, (partition, operation) in enumerate(scopes):
            self._promote_values(
                system,
                ({"n": 12},),
                partition=partition,
                operation=operation,
                prefix=f"scope-{index}",
            )

        for partition, operation in scopes:
            with self.subTest(partition=partition, operation=operation):
                resolution = system.resolve(partition, operation, {"n": 12})
                self.assertTrue(resolution.verification.passed)
                self.assertIsNotNone(resolution.match)
                assert resolution.match is not None
                self.assertTrue(resolution.match.matched)
                self.assertEqual(
                    resolution.match.output,
                    {
                        "input": {"n": 12},
                        "scope": [partition, operation],
                    },
                )

        with mock.patch.object(
            system,
            "verify_function",
            wraps=system.verify_function,
        ) as verify_spy:
            system.resolve("tenant_a", "echo_1", {"n": 12})
        verify_spy.assert_called_once_with(
            "tenant_a",
            "echo_1",
            expected_function_hash=None,
        )

    def test_b34(self) -> None:
        """
        B34: the `not verification.passed` term of the gate is pinned INDEPENDENTLY of the
        `or document is None` term: a FABRICATED verification carrying passed False WITH a real
        document reaches resolve and still returns match None (FABRICATED, mock-reachable only)

        Added by MAIN after the mutation sweep: deleting `not verification.passed or` survived
        all 633 tests. B14 forces the document term and every real verify_function output binds
        the two, so only this mirror probe can force the passed term.
        """

        from unittest import mock

        from cement_runtime import FunctionVerification, System

        system, _, _, _ = self._make_system()
        self._promote_values(
            system,
            ({"n": 11}, {"n": 12}, {"n": 13}),
            prefix="passed-term",
        )
        verified = system.verify_function("tenant_a", "echo_1")
        self.assertTrue(verified.passed)
        self.assertIsNotNone(verified.document)

        fabricated = FunctionVerification(
            passed=False,
            entries=verified.entries,
            document=verified.document,
            function_hash=verified.function_hash,
            checks=verified.checks,
        )
        with mock.patch.object(System, "verify_function", return_value=fabricated):
            resolution = system.resolve("tenant_a", "echo_1", {"n": 12})

        self.assertFalse(resolution.verification.passed)
        self.assertIsNone(resolution.match)

    def test_b35(self) -> None:
        """
        B35: no commit is issued on any resolve path, pinned INDEPENDENTLY of ledger bytes: a
        sqlite3.Connection subclass counting commit() records ZERO across a hit, a miss and a
        failed verdict, while the same spy counts a write transaction's commit and the ledger
        sha256 stays unmoved across it - the no-op commit B18 cannot see

        Added by MAIN after review finding V10. Section 5 lists `commit` as its own purity
        obligation, and B18's sha256 + iterdump pin cannot discharge it: the positive control
        below commits and moves neither. The write-transaction control also stops the probe
        passing vacuously, which a spy that failed to install would otherwise do.
        """

        import hashlib
        import sqlite3

        from cement_runtime import store as store_module

        commits: list[str] = []

        class _CountingConnection(sqlite3.Connection):
            def commit(self) -> None:
                commits.append("commit")
                super().commit()

        real_connect = sqlite3.connect

        def spy_connect(*args, **kwargs):
            kwargs["factory"] = _CountingConnection
            return real_connect(*args, **kwargs)

        system, database, _, _ = self._make_system()
        self._promote_values(
            system,
            ({"n": 21}, {"n": 22}, {"n": 23}),
            prefix="no-commit",
        )

        with mock.patch.object(store_module.sqlite3, "connect", spy_connect):
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            with system.store.transaction(write=True) as connection:
                connection.execute("SELECT 1").fetchone()
            self.assertEqual(commits, ["commit"])
            self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)

            commits.clear()
            states = {
                "hit": lambda: system.resolve("tenant_a", "echo_1", {"n": 22}),
                "miss": lambda: system.resolve("tenant_a", "echo_1", {"n": 99}),
                "failed": lambda: system.resolve(
                    "tenant_a",
                    "echo_1",
                    {"n": 22},
                    expected_function_hash="0" * 64,
                ),
            }
            resolutions = {}
            for label, call in states.items():
                resolutions[label] = call()
                with self.subTest(state=label):
                    self.assertEqual(commits, [])

        self.assertTrue(resolutions["hit"].match.matched)
        self.assertFalse(resolutions["miss"].match.matched)
        self.assertFalse(resolutions["failed"].verification.passed)


if __name__ == "__main__":
    unittest.main()
