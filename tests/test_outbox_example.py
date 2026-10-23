"""p37: the caller-side outbox example (`examples/outbox/`) — lost-intent protection only.

The acknowledgement-crash probe kills a real relay process between Cement's commit and the
outbox acknowledgement, then relays again: a keyed relay (`source_id` = the intent id) ends with
one proposal and a replayed delivery, an unkeyed relay with two identical proposals.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "outbox"
sys.path.insert(0, str(EXAMPLE_DIR))

import outbox  # noqa: E402

from cement_runtime import CompilePolicy, System  # noqa: E402

PARTITION, OPERATION = "tenant-a", "extract"
INTENT = {
    "partition": PARTITION,
    "operation": OPERATION,
    "operation_revision": 1,
    "input_value": {"form": "intake", "n": 12},
    "output": {"name": "Ada"},
    "provenance": {"model": "provider/model"},
    "source_revision": "prompt-7",
}
CRASH_EXIT = 70
CRASHING_RELAY = textwrap.dedent(
    """
    import os, sys
    import outbox
    from cement_runtime import System
    box = outbox.Outbox(sys.argv[1])
    box.relay(System(sys.argv[2], create=False), keyed=sys.argv[3] == "keyed",
              submitted=lambda intent_id, proposal_id: os._exit({exit}))
    """
).format(exit=CRASH_EXIT)


class OutboxTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-p37-")
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.ledger = str(self.root / "ledger.db")
        self.system = System(self.ledger)
        self.system.register_operation(PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0))
        self.box = outbox.Outbox(self.root / "outbox.db")

    def proposals(self) -> list[dict]:
        events = self.system.events(PARTITION)
        return [
            self.system.proposal(PARTITION, event["subject_id"])
            for event in events
            if event["kind"] == "proposal.created"
        ]

    def crash_after_submit(self, mode: str) -> None:
        environment = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(EXAMPLE_DIR), str(ROOT / "src")]),
        }
        crashed = subprocess.run(
            [sys.executable, "-c", CRASHING_RELAY, str(self.root / "outbox.db"), self.ledger, mode],
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(crashed.returncode, CRASH_EXIT, crashed.stderr)

    def test_the_id_binds_the_content(self) -> None:
        digest = self.box.record("i-1", **INTENT)
        self.assertEqual(self.box.record("i-1", **INTENT), digest)
        self.assertEqual(len(self.box.intents()), 1)
        variants = {
            "partition": "tenant-b",
            "operation": "extract-v2",
            "operation_revision": 2,
            "input_value": {"form": "intake", "n": 13},
            "output": {"name": "Ada L."},
            "provenance": {"model": "provider/other"},
            "source_revision": "prompt-8",
        }
        for field, value in variants.items():
            with self.subTest(field=field), self.assertRaises(outbox.IntentConflictError):
                self.box.record("i-1", **{**INTENT, field: value})
        self.assertEqual(self.box.intents(), [
            {"id": "i-1", "state": "pending", "proposal_id": None, "attempts": 0}
        ])
        self.assertEqual(self.proposals(), [])

    def test_a_relay_delivers_once_and_binds_the_intent_in_provenance(self) -> None:
        self.box.record("i-1", **INTENT)
        (delivery,) = self.box.relay(self.system)
        self.assertEqual((delivery.state, delivery.replayed), ("delivered", False))
        (proposal,) = self.proposals()
        self.assertEqual(proposal["id"], delivery.proposal_id)
        self.assertEqual(proposal["input"], INTENT["input_value"])
        self.assertEqual(proposal["proposed_output"], INTENT["output"])
        self.assertEqual(
            proposal["provenance"],
            {"intent": "i-1", "reported": INTENT["provenance"], "source_revision": "prompt-7"},
        )
        self.assertEqual(self.box.relay(self.system), [])

    def test_keyed_acknowledgement_crash_replays_into_one_proposal(self) -> None:
        self.box.record("i-1", **INTENT)
        self.crash_after_submit("keyed")
        self.assertEqual(len(self.proposals()), 1)
        self.assertEqual(self.box.intents()[0]["state"], "pending")
        (delivery,) = self.box.relay(self.system)
        (proposal,) = self.proposals()
        self.assertEqual((delivery.replayed, delivery.proposal_id), (True, proposal["id"]))
        self.assertEqual(self.box.intents(), [
            {"id": "i-1", "state": "delivered", "proposal_id": proposal["id"], "attempts": 2}
        ])

    def test_unkeyed_acknowledgement_crash_duplicates_the_proposal(self) -> None:
        self.box.record("i-1", **INTENT)
        self.crash_after_submit("unkeyed")
        (delivery,) = self.box.relay(self.system, keyed=False)
        first, second = self.proposals()
        self.assertFalse(delivery.replayed)
        self.assertNotEqual(first["id"], second["id"])
        for field in ("input", "proposed_output", "provenance", "operation_revision"):
            self.assertEqual(first[field], second[field], field)
        self.assertEqual(self.box.intents()[0]["attempts"], 2)

    def test_a_revised_operation_leaves_the_intent_stale(self) -> None:
        self.box.record("i-1", **INTENT)
        self.system.revise_operation(
            PARTITION, OPERATION, policy=CompilePolicy(2, 1, 0), revised_by="operator"
        )
        (delivery,) = self.box.relay(self.system)
        self.assertEqual((delivery.state, delivery.proposal_id), ("stale", None))
        self.assertEqual(self.proposals(), [])
        self.assertEqual(self.box.relay(self.system), [])


if __name__ == "__main__":
    unittest.main()
