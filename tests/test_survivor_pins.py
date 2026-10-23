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

from cement_runtime import cli


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


if __name__ == "__main__":
    unittest.main()
