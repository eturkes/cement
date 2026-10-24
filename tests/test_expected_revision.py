"""p134: `submit_proposal(..., expected_revision=)` + the CLI envelope's `operation_revision`.

A caller that generated a candidate for one operation revision binds it to that revision: when the
revision under the write lock differs, Cement refuses with `StateError` and writes nothing.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from cement_runtime import Candidate, CompilePolicy, StateError, System, ValidationError
from cement_runtime import cli as cement_cli

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "outbox"))

import outbox  # noqa: E402

PARTITION, OPERATION = "tenant-a", "extract"
CANDIDATE = Candidate(output={"name": "Ada"}, provenance={})
REFUSED = "operation revision changed before proposal submission"


class ExpectedRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-p134-")
        self.addCleanup(directory.cleanup)
        self.database = str(pathlib.Path(directory.name) / "ledger.db")
        self.system = System(self.database)
        self.system.register_operation(PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0))

    def created(self) -> int:
        return sum(event["kind"] == "proposal.created" for event in self.system.events(PARTITION))

    def revise(self) -> None:
        self.system.revise_operation(
            PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0), revised_by="operator"
        )

    def submit(self, expected: object) -> str:
        return self.system.submit_proposal(
            PARTITION, OPERATION, {"n": 12}, candidate=CANDIDATE, expected_revision=expected  # type: ignore[arg-type]
        )

    def test_the_current_revision_writes_and_another_is_refused_with_no_write(self) -> None:
        first = self.submit(1)
        self.assertEqual(self.system.proposal(PARTITION, first)["operation_revision"], 1)
        self.revise()
        with self.assertRaises(StateError) as raised:
            self.submit(1)
        self.assertEqual(str(raised.exception), REFUSED)
        self.assertEqual(self.created(), 1)
        second = self.submit(2)
        self.assertEqual(self.system.proposal(PARTITION, second)["operation_revision"], 2)
        self.assertEqual(self.created(), 2)

    def test_the_value_is_a_positive_signed_64_bit_integer(self) -> None:
        message = "expected_revision must be an integer between 1 and 9223372036854775807"
        for value in (0, -1, True, 1.0, "1", 2**63):
            with self.subTest(value=value), self.assertRaises(ValidationError) as raised:
                self.submit(value)
            self.assertEqual(str(raised.exception), message)
        # The adjacent bound passes validation and reaches the revision comparison.
        with self.assertRaises(StateError):
            self.submit(2**63 - 1)
        self.assertEqual(self.created(), 0)

    def test_the_cli_envelope_routes_operation_revision(self) -> None:
        def submit(revision: object) -> tuple[int, str, str]:
            envelope = {"input": {"n": 1}, "output": {"name": "Ada"}, "operation_revision": revision}
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = cement_cli.main([
                    "--db", self.database, "--partition", PARTITION,
                    "proposal", "submit", OPERATION, "--submission", json.dumps(envelope),
                ])
            return status, stdout.getvalue(), stderr.getvalue()

        status, stdout, _ = submit(1)
        self.assertEqual(status, 0)
        self.assertEqual(set(json.loads(stdout)), {"proposal_id"})
        self.revise()
        status, stdout, stderr = submit(1)
        self.assertEqual((status, stdout), (4, ""))
        self.assertEqual(json.loads(stderr), {"error": "conflict", "message": REFUSED})
        status, _, stderr = submit(True)
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stderr)["error"], "invalid")
        self.assertEqual(self.created(), 1)

    def test_the_envelope_byte_budget_admits_the_largest_revision(self) -> None:
        self.assertIn("operation_revision", cement_cli._SUBMISSION_KEYS)
        self.assertEqual(cement_cli._REVISION_WIRE_BYTES, len(str(2**63 - 1)))
        self.assertEqual(
            cement_cli.SUBMISSION_MAX_BYTES,
            2 * cement_cli.DEFAULT_MAX_BYTES
            + cement_cli.PROVENANCE_MAX_BYTES
            + cement_cli._SOURCE_ID_WIRE_BYTES
            + cement_cli._REVISION_WIRE_BYTES
            + cement_cli._SUBMISSION_FRAMING,
        )

    def test_the_outbox_relay_binds_the_intent_revision(self) -> None:
        box = outbox.Outbox(pathlib.Path(self.database).with_name("outbox.db"))
        box.record(
            "i-1", partition=PARTITION, operation=OPERATION, operation_revision=1,
            input_value={"n": 1}, output={"name": "Ada"}, provenance={}, source_revision="p-1",
        )
        with mock.patch.object(System, "submit_proposal", autospec=True, wraps=System.submit_proposal) as spy:
            (delivery,) = box.relay(self.system)
        self.assertEqual(delivery.state, "delivered")
        self.assertEqual(spy.call_args.kwargs["expected_revision"], 1)


if __name__ == "__main__":
    unittest.main()
