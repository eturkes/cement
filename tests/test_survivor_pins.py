"""Tests that survivor rulings added as `missing-test` (`.agent/decisions/survivor-rulings.md`).

Each test names the row and the survivor it kills.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from cement_runtime import System, cli
from cement_runtime.errors import ValidationError


class SurvivorPinTests(unittest.TestCase):
    def test_p105_the_cli_prints_non_ascii_json_as_raw_utf8(self) -> None:
        # p105: `cli.py` `_emit` `ensure_ascii=False` → `True` survived every module, because each
        # byte-comparing CLI test prints ASCII alone. A Japanese deployment reads the raw text.
        with tempfile.TemporaryDirectory(prefix="cement-p105-") as directory:
            database = str(pathlib.Path(directory) / "ledger.db")
            base = ["--db", database, "--partition", "hospital"]

            def run(*argv: str) -> str:
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    self.assertEqual(cli.main([*base, *argv]), 0)
                return stdout.getvalue()

            run("operation", "register", "extract")
            submission = {"input": {"文書": "患者: 山田"}, "output": {"患者": "山田"}}
            proposal_id = json.loads(
                run("proposal", "submit", "extract", "--submission", json.dumps(submission))
            )["proposal_id"]
            shown = run("proposal", "show", proposal_id)
        self.assertIn('"患者": "山田"', shown)
        self.assertNotIn("\\u", shown)
        self.assertEqual(json.loads(shown)["proposed_output"], {"患者": "山田"})

    def test_p104_a_class_forging_equality_is_no_candidate(self) -> None:
        # p104: `type(candidate) is not Candidate` → `!=` survived every module. Identity cannot be
        # forged; equality can, through the class's metaclass, so only `is not` refuses this object.
        class ForgedEquality(type):
            def __eq__(cls, other: object) -> bool:
                return True

            def __ne__(cls, other: object) -> bool:
                return False

            __hash__ = type.__hash__

        class LooksLikeACandidate(metaclass=ForgedEquality):
            output = {"answer": 1}
            provenance: dict[str, object] = {}

        with tempfile.TemporaryDirectory(prefix="cement-p104-") as directory:
            system = System(str(pathlib.Path(directory) / "ledger.db"))
            system.register_operation("tenant-a", "echo")
            with self.assertRaises(ValidationError) as raised:
                system.submit_proposal(
                    "tenant-a", "echo", {"n": 1}, candidate=LooksLikeACandidate()  # type: ignore[arg-type]
                )
            self.assertEqual(str(raised.exception), "candidate must be a Candidate")
            self.assertEqual(system.events("tenant-a")[-1]["kind"], "operation.registered")


if __name__ == "__main__":
    unittest.main()
