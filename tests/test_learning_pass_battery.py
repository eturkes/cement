"""M5.2 battery — supersession, the learning read surface and the learning pass.

Contract: `.agent/decisions/m45-contract.md` §2 (X1a-X1d) + §6 (LP0-LP4). The learning pass is the
only reviewer (`learning-pass`); it re-merges earlier confirmations through supersession, which
replaces a judgment without adding support, so one source observation earns one credit however
often it is re-merged.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import inspect
import io
import json
import pathlib
import re
import shlex
import tempfile
import unittest
import unittest.mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    NotFoundError,
    StateError,
    System,
    ValidationError,
)
from cement_runtime.cli import _parser, _UsageError, main
from cement_runtime.json_value import canonicalize
from cement_runtime.projection import structure

P, OP = "tenant_a", "plan"
NARROW = {"fields": ["patient"]}
MERGED = {"fields": ["patient", "provider"]}
DOC = {"doc": "progress note"}
FORMS = sorted(
    (pathlib.Path(__file__).resolve().parents[1] / "examples/hospital_ocr/documents").glob("*.txt")
)


def _program(texts: list[str]) -> dict[str, object]:
    layouts: dict[object, dict[str, object]] = {}
    for text in texts:
        parsed = structure(text)
        assert parsed is not None
        title, pairs = parsed
        layouts[(title, pairs)] = {
            "name": title.lower(), "title": title, "entries": [{kind: key} for kind, key in pairs]
        }
    return {"abi": "cement-projection-v1", "text": "document", "keep": [], "layouts": list(layouts.values())}


class _Ledger(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-learning-")
        self.addCleanup(directory.cleanup)
        self.db = str(pathlib.Path(directory.name) / "ledger.db")
        self.system = System(self.db)
        self.system.register_operation(P, OP, policy=CompilePolicy())
        self.system.register_operation(P, "other", policy=CompilePolicy())

    def _confirm(self, output: object, *, value: object = DOC, operation: str = OP) -> str:
        proposal = self.system.submit_proposal(
            P, operation, value, candidate=Candidate(output=output, provenance={})
        )
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        return proposal

    def _example_ids(self, operation: str = OP) -> list[str]:
        return [str(row["id"]) for row in self.system.examples(P, operation)]

    def _publish(self) -> str:
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        return str(manifest.function_hash)

    def _counts(self) -> tuple[int, ...]:
        with self.system.store.transaction() as connection:
            return tuple(
                int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("examples", "events", "artifacts", "proposals", "test_reports")
            )

    def _cli(self, *argv: str, stdin: str = "") -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        source = io.TextIOWrapper(io.BytesIO(stdin.encode()), encoding="utf-8")
        with (
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
            unittest.mock.patch("sys.stdin", source),
        ):
            code = main(["--db", self.db, "--partition", P, *argv])
        return code, out.getvalue(), err.getvalue()



class SupersessionBattery(_Ledger):
    def test_x1a_a_merge_extends_two_narrow_confirmations_into_one_case_of_support_three(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        v1 = self._publish()
        self.system.set_switch(P, OP, mode="follow", actor="person")
        old = self._example_ids()
        created = self.system.supersede_examples(
            P, OP, example_ids=old, output=MERGED, reviewer="learning-pass", note="run-2"
        )
        self.assertEqual(len(created), 2)
        self._confirm(MERGED)
        result = self.system.compile(P, OP)
        self.assertEqual((len(result.created), result.blocked), (1, ()))
        artifact = self.system.artifact(P, result.created[0])
        self.assertEqual((artifact["support"], artifact["document"]["behavior"]["value"]), (3, MERGED))
        v2 = self._publish()
        self.assertNotEqual(v1, v2)
        live = self.system.verify_function(P, OP)
        self.assertTrue(live.passed, [check for check in live.checks if not check.passed])
        answer = self.system.resolve(P, OP, DOC)
        self.assertEqual((answer.verification.passed, answer.match.output), (True, MERGED))

    def test_x1b_supersession_never_raises_support(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        before = self.system.compile(P, OP)
        built = self.system.artifact(P, before.created[0])
        self.system.supersede_examples(
            P, OP, example_ids=self._example_ids()[:2], output=MERGED, reviewer="learning-pass"
        )
        after = self.system.compile(P, OP)
        rebuilt = self.system.artifact(P, after.created[0])
        self.assertEqual((built["support"], rebuilt["support"]), (2, 2))
        self.assertEqual(rebuilt["document"]["behavior"]["value"], MERGED)
        again = self.system.supersede_examples(
            P,
            OP,
            example_ids=[row["id"] for row in self.system.examples(P, OP)[2:]],
            output={"fields": ["patient", "provider", "date"]},
            reviewer="learning-pass",
        )
        self.assertEqual(len(again), 2)
        third = self.system.compile(P, OP)
        chained = self.system.artifact(P, third.created[0])
        self.assertEqual(chained["support"], 2)

    def test_x1c_a_superseded_example_still_validates_the_pinned_version_built_on_it(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        v1 = self._publish()
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1)
        self.system.supersede_examples(
            P, OP, example_ids=self._example_ids(), output=MERGED, reviewer="learning-pass"
        )
        pinned = self.system.resolve(P, OP, DOC)
        self.assertEqual((pinned.verification.passed, pinned.match.output), (True, NARROW))
        self.system.set_switch(P, OP, mode="follow", actor="person")
        window = self.system.resolve(P, OP, DOC)
        self.assertEqual((window.verification.passed, window.match), (False, None))
        self._publish()
        served = self.system.resolve(P, OP, DOC)
        self.assertEqual((served.verification.passed, served.match.output), (True, MERGED))

    def test_x1d_every_refusal_writes_nothing(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        self._confirm({"other": 1}, operation="other")
        first, second = self._example_ids()
        (foreign,) = self._example_ids("other")
        self.system.supersede_examples(
            P, OP, example_ids=[second], output=MERGED, reviewer="learning-pass"
        )
        revoked = self._confirm(NARROW, value={"doc": "intake"})
        revoked_id = self.system.examples(P, OP)[-1]["id"]
        self.assertEqual(self.system.proposal(P, revoked)["status"], "accepted")
        self.system.revoke_example(P, revoked_id, revoked_by="person", reason="wrong")
        before = self._counts()
        for ids, output, error in (
            ([], MERGED, ValidationError),
            ([first, first], MERGED, ValidationError),
            ([first, "ex_" + "0" * 32], MERGED, NotFoundError),
            ([first, foreign], MERGED, ValidationError),
            ([first, revoked_id], MERGED, StateError),
            ([first, second], MERGED, StateError),
            ([first], NARROW, ValidationError),
        ):
            with self.subTest(ids=ids, output=output), self.assertRaises(error):
                self.system.supersede_examples(
                    P, OP, example_ids=ids, output=output, reviewer="learning-pass"
                )
            self.assertEqual(self._counts(), before)
        with self.assertRaises(NotFoundError):
            self.system.supersede_examples(
                "tenant_b", OP, example_ids=[first], output=MERGED, reviewer="learning-pass"
            )
        self.assertEqual(self._counts(), before)

    def test_supersession_writes_one_example_and_one_event_per_old_example(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        old = self._example_ids()
        before = self._counts()
        created = self.system.supersede_examples(
            P, OP, example_ids=old, output=MERGED, reviewer="learning-pass", note="run-2"
        )
        self.assertEqual(
            self._counts(), (before[0] + 2, before[1] + 2, before[2], before[3], before[4])
        )
        rows = {row["id"]: row for row in self.system.examples(P, OP)}
        for old_id, new_id in zip(old, created, strict=True):
            row = rows[new_id]
            self.assertEqual(
                (row["origin"], row["supersedes_example_id"], row["input"], row["output"]),
                ("superseded", old_id, rows[old_id]["input"], MERGED),
            )
            self.assertEqual((rows[old_id]["superseded_by"], row["superseded_by"]), (new_id, None))
            self.assertEqual(row["source_id"], rows[old_id]["source_id"])
        superseded = [event for event in self.system.events(P) if event["kind"] == "example.superseded"]
        self.assertEqual([event["subject_id"] for event in superseded], old)
        self.assertEqual(
            [event["payload"] for event in superseded],
            [{"example_id": new_id, "reviewer": "learning-pass"} for new_id in created],
        )

    def test_the_supersession_receipt_binds_the_new_example_and_names_the_old_one(self) -> None:
        self._confirm(NARROW)
        (old,) = self._example_ids()[:1]
        (new,) = self.system.supersede_examples(
            P, OP, example_ids=[old], output=MERGED, reviewer="learning-pass", note="run-2"
        )
        with self.system.store.transaction() as connection:
            row = connection.execute("SELECT * FROM examples WHERE id = ?", (new,)).fetchone()
        receipt = json.loads(row["receipt_json"])
        self.assertEqual(
            receipt,
            {
                "confirmed_at_us": row["confirmed_at_us"],
                "example_id": new,
                "format": "cement-supersession-v1",
                "input": DOC,
                "note": "run-2",
                "operation": OP,
                "operation_revision": 1,
                "output": MERGED,
                "partition": P,
                "reviewer": "learning-pass",
                "supersedes_example_id": old,
            },
        )
        self.assertEqual(canonicalize(receipt).digest, row["receipt_hash"])
        self.assertIsNone(row["proposal_id"])

    def test_cli_example_supersede_reads_the_merge_and_maps_refusals_to_exit_classes(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        old = self._example_ids()
        run = self._cli
        common = ["example", "supersede", OP, "--reviewer", "learning-pass", "--note", "run-2"]
        code, out, _ = run(*common, "--output", json.dumps(MERGED), *old)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["superseded_example_ids"], old)
        self.assertEqual(
            [row["id"] for row in self.system.examples(P, OP)][2:], payload["example_ids"]
        )
        self.assertEqual(run(*common, "--output", json.dumps(MERGED), old[0])[0], 4)
        self.assertEqual(run(*common, "--output", json.dumps(MERGED), "ex_" + "0" * 32)[0], 3)
        self.assertEqual(run(*common, "--output", "{", payload["example_ids"][0])[0], 2)
        self.assertEqual(
            run(*common, "--out", json.dumps(MERGED), payload["example_ids"][0])[:2], (2, "")
        )


class ContradictedPromotionBattery(_Ledger):
    """A confirmation that contradicts a promoted artifact is a ledger STATE, never corruption.

    Review no longer auto-suspends (contract §3), so the live set fails verification until the
    next promotion replaces the artifact; read surfaces, challenges and the promotion plan must
    grade integrity alone and report the contradiction as what it is.
    """

    def setUp(self) -> None:
        super().setUp()
        self._confirm(NARROW)
        self._confirm(NARROW)
        self.v1 = self._publish()
        (self.member,) = [row["id"] for row in self.system.artifacts(P, OP)]
        self.system.set_switch(P, OP, mode="follow", actor="person")
        self.wrong = self._confirm(MERGED)

    def test_read_surfaces_show_a_contradicted_artifact_without_an_integrity_failure(self) -> None:
        self.assertEqual(self.system.artifact(P, self.member)["status"], "promoted")
        report = self.system.function_report(P, OP)
        assert report.function_anchor is not None
        self.assertEqual(report.function_anchor.receipt.function_hash, self.v1)
        live = self.system.verify_function(P, OP)
        self.assertFalse(
            {check.key: check.passed for check in live.checks}["current-promotion-receipts"]
        )
        window = self.system.resolve(P, OP, DOC)
        self.assertEqual((window.verification.passed, window.match), (False, None))

    def test_promotion_without_a_replacement_refuses_as_a_state_and_writes_nothing(self) -> None:
        before = self._counts()
        with self.assertRaisesRegex(StateError, f"{self.member} conflicts with active evidence"):
            self.system.inspect_function_promotion(P, OP)
        with self.assertRaises(StateError):
            self.system.promote_function(
                P, OP, expected_function_hash=self.v1, promoted_by="learning-pass"
            )
        self.assertEqual(self._counts(), before)

    def test_the_learning_pass_resolves_it_by_revoking_or_by_superseding(self) -> None:
        wrong = self.system.examples(P, OP)[-1]["id"]
        self.system.revoke_example(P, wrong, revoked_by="learning-pass", reason="wrong merge")
        self.assertEqual(self.system.inspect_function_promotion(P, OP).function_hash, self.v1)
        self.assertTrue(self.system.verify_function(P, OP).passed)
        self._confirm(MERGED)
        self.system.supersede_examples(
            P, OP, example_ids=self._example_ids()[:2], output=MERGED, reviewer="learning-pass"
        )
        v2 = self._publish()
        self.assertNotEqual(v2, self.v1)
        served = self.system.resolve(P, OP, DOC)
        self.assertEqual((served.verification.passed, served.match.output), (True, MERGED))

    def test_a_challenge_on_a_contradicted_case_is_not_an_integrity_quarantine(self) -> None:
        _, suspended = self.system.challenge(P, OP, DOC, MERGED, reviewer="person")
        self.assertTrue(suspended)
        row = self.system.artifact(P, self.member)
        self.assertEqual(row["status"], "suspended")
        self.assertNotEqual(row["status_reason"], "challenge integrity failure")
        kinds = [event["kind"] for event in self.system.events(P)]
        self.assertNotIn("artifact.integrity_quarantined", kinds)


class LearningCasesBattery(_Ledger):
    """LP2: `learn cases` groups by exact input, by the build-current program or by a candidate."""

    def _submit(self, value: object, output: object, source_id: str | None = None) -> str:
        return self.system.submit_proposal(
            P,
            OP,
            value,
            candidate=Candidate(output=output, provenance={"model": "stand-in"}),
            source_id=source_id,
        )

    def test_lp2a_exact_cases_list_pending_and_active_ids_per_distinct_output(self) -> None:
        first = self._confirm(NARROW)
        pending_narrow = self._submit(DOC, NARROW, source_id="chat-1:msg-1")
        pending_merged = self._submit(DOC, MERGED)
        intake = self._submit({"doc": "intake"}, NARROW, source_id="chat-2:msg-1")
        before = self._counts()
        view = self.system.learning_cases(P, OP)
        self.assertEqual(self._counts(), before)
        self.assertEqual((view["grouped_by"], view["program_hash"]), ("exact", None))
        cases = {json.dumps(case["key"], sort_keys=True): case for case in view["cases"]}
        self.assertEqual(set(cases), {json.dumps(DOC), json.dumps({"doc": "intake"})})
        doc = cases[json.dumps(DOC)]
        (example,) = self._example_ids()
        self.assertEqual(self.system.proposal(P, first)["status"], "accepted")
        self.assertEqual(doc["key_hash"], canonicalize(DOC).digest)
        self.assertEqual(doc["pending_proposal_ids"], [pending_narrow, pending_merged])
        self.assertEqual(doc["active_example_ids"], [example])
        self.assertEqual(
            doc["outputs"],
            sorted(
                [
                    {"output": NARROW, "example_ids": [example], "proposal_ids": [pending_narrow]},
                    {"output": MERGED, "example_ids": [], "proposal_ids": [pending_merged]},
                ],
                key=lambda item: canonicalize(item["output"]).text,
            ),
        )
        self.assertEqual((doc["support"], doc["ready"], doc["artifact"]), (1, False, None))
        self.assertEqual(doc["blocked_reasons"], ["support 1 is below required 2"])
        self.assertEqual(cases[json.dumps({"doc": "intake"})]["pending_proposal_ids"], [intake])
        self.assertEqual(
            view["unsourced_pending"],
            [{"proposal_id": pending_merged, "provenance": {"model": "stand-in"}}],
        )
        self.assertFalse(view["nothing_to_learn"])

    def test_lp2b_a_candidate_program_groups_raw_forms_before_anything_is_confirmed(self) -> None:
        texts = [path.read_text(encoding="utf-8") for path in FORMS]
        ids = [self._submit({"document": text}, {"plan": text.splitlines()[0]}) for text in texts]
        stray = self._submit({"document": "not a form"}, {"plan": "none"})
        program = _program(texts)
        exact = self.system.learning_cases(P, OP)
        self.assertEqual(len(exact["cases"]), len(texts) + 1)
        grouped = self.system.learning_cases(P, OP, program=program)
        self.assertEqual(grouped["grouped_by"], "candidate")
        self.assertEqual(grouped["program_hash"], self.system.test_projection(P, OP, program)["program_hash"])
        self.assertEqual(grouped["unprojected"], {"example_ids": [], "proposal_ids": [stray]})
        titles = {text.splitlines()[0] for text in texts}
        self.assertEqual(len(grouped["cases"]), len(titles))
        self.assertEqual(
            sorted(sum((case["pending_proposal_ids"] for case in grouped["cases"]), [])), sorted(ids)
        )
        for case in grouped["cases"]:
            (output,) = case["outputs"]
            self.assertEqual(output["output"], {"plan": case["key"]["form"]["title"]})
        for proposal in ids:
            self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        self.system.set_projection(P, OP, program, actor="learning-pass")
        current = self.system.learning_cases(P, OP)
        self.assertEqual(current["grouped_by"], "build-current")
        self.assertEqual(current["program_hash"], grouped["program_hash"])
        self.assertEqual(
            [(case["key_hash"], len(case["active_example_ids"])) for case in current["cases"]],
            [(case["key_hash"], len(case["pending_proposal_ids"])) for case in grouped["cases"]],
        )
        self.assertEqual(current["unprojected"], {"example_ids": [], "proposal_ids": [stray]})

    def test_lp2c_work_names_each_unfinished_publication_step_in_order(self) -> None:
        self.assertTrue(self.system.learning_cases(P, OP)["nothing_to_learn"])
        self._confirm(NARROW)
        self._confirm(NARROW)
        key = canonicalize(DOC).digest
        steps = []
        for step in (
            lambda: self.system.compile(P, OP),
            lambda: self.system.verify_drafts(P, OP, verified_by="learning-pass"),
            lambda: self._promote(),
            lambda: None,
        ):
            work = self.system.learning_cases(P, OP)["work"]
            steps.append(
                (
                    work["compile_key_hashes"],
                    len(work["verify_artifact_ids"]),
                    len(work["promote_artifact_ids"]),
                    work["live_function_hash"] is not None,
                )
            )
            step()
        self.assertEqual(
            steps, [([key], 0, 0, False), ([], 1, 0, False), ([], 0, 1, False), ([], 0, 0, True)]
        )
        view = self.system.learning_cases(P, OP)
        self.assertTrue(view["nothing_to_learn"])
        self.assertEqual(view["work"]["live_function_hash"], view["work"]["prospective_function_hash"])
        (case,) = view["cases"]
        self.assertEqual((case["ready"], case["artifact"]["status"]), (True, "promoted"))

    def _promote(self) -> None:
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )

    def test_lp2d_stale_pending_and_a_blocked_promotion_keep_the_pass_open(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        self._publish()
        self._confirm(MERGED)
        blocked = self.system.learning_cases(P, OP)
        self.assertIn("conflicts with active evidence", blocked["work"]["promote_blocked"])
        self.assertEqual(blocked["work"]["promote_artifact_ids"], [])
        self.assertFalse(blocked["nothing_to_learn"])
        stale = self._submit({"doc": "intake"}, NARROW)
        self.system.revise_operation(P, OP, policy=CompilePolicy(), revised_by="operator")
        view = self.system.learning_cases(P, OP)
        self.assertEqual(view["stale_pending_proposal_ids"], [stale])
        self.assertEqual(view["cases"], [])
        self.assertFalse(view["nothing_to_learn"])

    def test_lp2f_an_unfinished_merge_keeps_the_pass_open_before_any_promotion(self) -> None:
        self._confirm(NARROW)
        self._confirm(MERGED)
        view = self.system.learning_cases(P, OP)
        (case,) = view["cases"]
        self.assertEqual(case["blocked_reasons"], ["confirmed outputs conflict"])
        self.assertEqual(view["work"]["merge_key_hashes"], [canonicalize(DOC).digest])
        self.assertFalse(view["nothing_to_learn"])
        narrow = case["outputs"][[o["output"] for o in case["outputs"]].index(NARROW)]["example_ids"]
        self.system.supersede_examples(
            P, OP, example_ids=narrow, output=MERGED, reviewer="learning-pass"
        )
        resumed = self.system.learning_cases(P, OP)["work"]
        self.assertEqual((resumed["merge_key_hashes"], resumed["compile_key_hashes"]), ([], [canonicalize(DOC).digest]))

    def test_lp2g_one_snapshot_reconstructs_the_build_current_cases_once(self) -> None:
        self._confirm(NARROW)
        self._confirm(NARROW)
        self.system.compile(P, OP)
        with unittest.mock.patch.object(
            System, "_current_build_projections", autospec=True,
            side_effect=System._current_build_projections,
        ) as spy:
            view = self.system.learning_cases(P, OP)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(len(view["work"]["verify_artifact_ids"]), 1)

    def test_lp2e_cli_learn_cases_prints_the_library_view(self) -> None:
        texts = [path.read_text(encoding="utf-8") for path in FORMS[:2]]
        for text in texts:
            self._submit({"document": text}, {"plan": text.splitlines()[0]})
        code, out, err = self._cli("learn", "cases", OP)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out), self.system.learning_cases(P, OP))
        program = _program(texts)
        code, out, _ = self._cli("learn", "cases", OP, "--program", "-", stdin=json.dumps(program))
        self.assertEqual((code, json.loads(out)), (0, self.system.learning_cases(P, OP, program=program)))
        self.assertEqual(self._cli("learn", "cases", OP, "--program", "{}")[0], 2)
        self.assertEqual(self._cli("learn", "cases", "missing")[0], 3)
        self.assertEqual(self._cli("learn", "cases", OP, "--prog", "{}")[:2], (2, ""))


class ScriptedPassBattery(_Ledger):
    """LP1 + LP0: the skill's workflow run through the CLI, with reference merges for the LLM.

    `_pass` follows `skills/cement-learn/SKILL.md` step by step and reads nothing but `learn
    cases`; `stop_after` interrupts it at a named step to prove the rerun resumes.
    """

    def _json(self, *argv: str, stdin: str = "") -> object:
        code, out, err = self._cli(*argv, stdin=stdin)
        self.assertEqual(code, 0, (argv, err))
        return json.loads(out)

    def _pass(self, merge: object, *, stop_after: str | None = None, partial: int | None = None) -> str:
        note = "run, model reference"
        view = self._json("learn", "cases", OP)
        if view["nothing_to_learn"]:
            return "nothing to learn"
        merged = json.dumps(merge)
        for case in view["cases"]:
            for proposal in case["pending_proposal_ids"]:
                carried = next(o for o in case["outputs"] if proposal in o["proposal_ids"])
                decision = ["--decision", "accept"] if carried["output"] == merge else [
                    "--decision", "correct", "--output", "-"
                ]
                self._json(
                    "proposal", "review", proposal, "--reviewer", "learning-pass", *decision,
                    "--note", note, stdin=merged,
                )
        if stop_after == "reviews":
            return "interrupted"
        view = self._json("learn", "cases", OP)
        for case in view["cases"]:
            narrower = [
                example
                for output in case["outputs"]
                if output["output"] != merge
                for example in output["example_ids"]
            ][:partial]
            if narrower:
                self._json(
                    "example", "supersede", OP, *narrower, "--output", "-",
                    "--reviewer", "learning-pass", "--note", note, stdin=merged,
                )
        if stop_after == "supersession":
            return "interrupted"
        work = self._json("learn", "cases", OP)["work"]
        if work["compile_key_hashes"]:
            self._json("compile", OP, "--actor", "learning-pass")
            work = self._json("learn", "cases", OP)["work"]
        if work["verify_artifact_ids"]:
            self._json("function", "verify-drafts", OP, "--actor", "learning-pass")
            work = self._json("learn", "cases", OP)["work"]
        self.assertIsNone(work["promote_blocked"])
        manifest = self._json("function", "inspect", OP)
        self._json(
            "function", "promote", OP, "--expected-function-hash", manifest["function_hash"],
            "--actor", "learning-pass",
        )
        return str(manifest["function_hash"])

    def _ask(self, output: object) -> None:
        self.system.submit_proposal(P, OP, DOC, candidate=Candidate(output=output, provenance={}))

    def _support(self) -> int:
        report = self.system.function_report(P, OP)
        assert report.function_anchor is not None
        (member,) = report.function_anchor.members
        return int(self.system.artifact(P, member.artifact_id)["support"])

    def _first_version(self) -> str:
        self._ask(NARROW)
        self._ask(NARROW)
        v1 = self._pass(NARROW)
        self.assertEqual(self._support(), 2)
        return v1

    def _assert_second_version(self, v1: str, v2: str) -> None:
        self.assertNotEqual(v1, v2)
        self.assertEqual(self._support(), 3)
        versions = [
            row["receipt"]["function_hash"]
            for row in self._json("function", "versions", OP)["versions"]
        ]
        self.assertEqual(sorted(versions), sorted([v1, v2]))
        self.assertEqual(self.system.switch(P, OP).mode, "off")
        self.assertFalse(self.system.resolve(P, OP, DOC).match)
        self.assertEqual(self._pass(MERGED), "nothing to learn")

    def test_lp1_a_partial_first_pass_then_an_expanded_second_pass(self) -> None:
        v1 = self._first_version()
        self.assertEqual(self.system.switch(P, OP).mode, "off")
        self._ask(MERGED)
        v2 = self._pass(MERGED)
        self._assert_second_version(v1, v2)
        self.system.set_switch(P, OP, mode="follow", actor="person")
        served = self.system.resolve(P, OP, DOC)
        self.assertEqual((served.verification.passed, served.match.output), (True, MERGED))

    def test_lp0_a_pass_interrupted_after_its_reviews_resumes_with_support_unchanged(self) -> None:
        v1 = self._first_version()
        self._ask(MERGED)
        self.assertEqual(self._pass(MERGED, stop_after="reviews"), "interrupted")
        view = self.system.learning_cases(P, OP)
        self.assertFalse(view["nothing_to_learn"])
        self.assertEqual(view["cases"][0]["pending_proposal_ids"], [])
        self._assert_second_version(v1, self._pass(MERGED))

    def test_lp0_a_pass_interrupted_mid_supersession_resumes_with_support_unchanged(self) -> None:
        v1 = self._first_version()
        self._ask(MERGED)
        self.assertEqual(self._pass(MERGED, stop_after="supersession", partial=1), "interrupted")
        (case,) = self.system.learning_cases(P, OP)["cases"]
        self.assertEqual((len(case["outputs"]), case["ready"]), (2, False))
        self.assertEqual(case["blocked_reasons"], ["confirmed outputs conflict"])
        self._assert_second_version(v1, self._pass(MERGED))

class ProjectableResumeBattery(_Ledger):
    """LP0d (reviewer-4 F2): a projectable pass interrupted after its reviews and before
    `projection set` leaves only exact support-1 cases, so `learn cases` alone reads idle. The
    skill keeps the candidate in `program.json` until step 4 finishes; the rerun groups by it,
    finds the cases ready and publishes, with each observation counted once."""

    def test_lp0d_the_saved_candidate_resumes_a_pass_stopped_before_projection_set(self) -> None:
        texts = [path.read_text(encoding="utf-8") for path in FORMS if "layout_a" in path.name]
        self.assertGreaterEqual(len(texts), 2)
        for text in texts:
            self.system.submit_proposal(
                P, OP, {"document": text},
                candidate=Candidate(output={"plan": text.splitlines()[0]}, provenance={}),
            )
        saved = _program(texts)  # step 2 writes program.json before any review
        grouped = self.system.learning_cases(P, OP, program=saved)
        for case in grouped["cases"]:
            for proposal in case["pending_proposal_ids"]:
                self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        # interrupted here: no `projection set`
        restart = self.system.learning_cases(P, OP)
        self.assertEqual(restart["grouped_by"], "exact")
        self.assertTrue(restart["nothing_to_learn"])
        self.assertEqual({case["support"] for case in restart["cases"]}, {1})
        self.assertIsNone(self.system.projection(P, OP))
        resumed = self.system.learning_cases(P, OP, program=saved)
        (case,) = resumed["cases"]
        self.assertEqual((case["ready"], case["support"]), (True, len(texts)))
        self.system.set_projection(P, OP, saved, actor="learning-pass")
        self._publish()
        self.assertTrue(self.system.learning_cases(P, OP)["nothing_to_learn"])
        self.assertEqual(self.system.switch(P, OP).mode, "off")

    def test_lp0d_the_skill_keeps_the_candidate_until_projection_set(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        one_line = " ".join(text.split())
        self.assertIn("keep that file until step 4 finishes", one_line)
        self.assertIn("If `program.json` exists from an earlier pass", one_line)
        self.assertIn('cement projection show "$OP"', one_line)


SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills/cement-learn"
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SHELL_STOPS = {"<", ">", ">>", "|", "&&", "||", ";", "2>"}


def _frontmatter_failures(text: str, directory: str) -> list[str]:
    """Agent Skills frontmatter rules (agentskills.io specification) over one SKILL.md."""

    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        return ["no YAML frontmatter"]
    fields = dict(line.split(": ", 1) for line in match.group(1).splitlines())
    failures = [f"unknown field {key}" for key in sorted(set(fields) - SPEC_FIELDS)]
    name = fields.get("name", "")
    if not (1 <= len(name) <= 64 and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)):
        failures.append(f"invalid name {name!r}")
    if name != directory:
        failures.append(f"name {name!r} does not match directory {directory!r}")
    if not 1 <= len(fields.get("description", "")) <= 1024:
        failures.append("description must hold 1-1024 characters")
    if fields.get("license") != "Apache-2.0":
        failures.append("license must be Apache-2.0")
    if len(fields.get("compatibility", "")) > 500:
        failures.append("compatibility exceeds 500 characters")
    return failures


def _leaf(words: list[str]) -> argparse.ArgumentParser | None:
    parser: argparse.ArgumentParser = _parser()
    for word in words:
        subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        if not subs:
            return parser
        if word not in subs[0].choices:
            return None
        parser = subs[0].choices[word]
    return parser if not [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)] else None


def _commands(text: str) -> tuple[list[str], list[str]]:
    """(full commands in fenced blocks, inline `cement ...` spans), shell syntax stripped."""

    fenced: list[str] = []
    for block in re.findall(r"^\s*```[a-z]*\n(.*?)^\s*```", text, re.DOTALL | re.MULTILINE):
        fenced.extend(line.strip() for line in block.splitlines() if line.strip().startswith("cement "))
    outside = re.sub(r"^\s*```[a-z]*\n.*?^\s*```", "", text, flags=re.DOTALL | re.MULTILINE)
    inline = [" ".join(span.split()) for span in re.findall(r"`(cement [^`]+)`", outside)]
    return fenced, inline


def _command_failures(text: str) -> list[str]:
    failures: list[str] = []
    fenced, inline = _commands(text)
    for command in fenced:
        tokens = shlex.split(command)[1:]
        cut = next((i for i, token in enumerate(tokens) if token in SHELL_STOPS), len(tokens))
        try:
            _parser().parse_args(tokens[:cut])
        except (_UsageError, SystemExit) as exc:
            failures.append(f"{command}: {exc}")
    for command in inline:
        words = shlex.split(command)[1:]
        if _leaf([word for word in words if not word.startswith(("-", "$"))][:2]) is None:
            failures.append(f"{command}: names no CLI leaf")
    return failures


class SkillBattery(unittest.TestCase):
    """LP3: the shipped skill's frontmatter and every command it names parse against `_parser()`."""

    def _texts(self) -> dict[str, str]:
        return {
            str(path.relative_to(SKILL)): path.read_text(encoding="utf-8")
            for path in sorted(SKILL.rglob("*.md"))
        }

    def test_lp3_the_shipped_skill_passes_both_checks(self) -> None:
        texts = self._texts()
        self.assertEqual(set(texts), {"SKILL.md", "references/projection.md", "references/workflow.md"})
        self.assertEqual(_frontmatter_failures(texts["SKILL.md"], SKILL.name), [])
        counted = 0
        for name, text in texts.items():
            with self.subTest(file=name):
                self.assertEqual(_command_failures(text), [])
                counted += sum(len(found) for found in _commands(text))
        self.assertGreaterEqual(counted, 25)
        leaves = {
            " ".join(shlex.split(command)[1:3])
            for text in texts.values()
            for command in _commands(text)[0]
        }
        for leaf in (
            "learn cases", "proposal review", "example supersede", "example revoke",
            "projection test", "projection set", "function verify-drafts", "function inspect",
            "function promote", "function diff",
        ):
            self.assertIn(leaf, leaves)

    def test_lp3_seeded_defects_red_each_check(self) -> None:
        good = self._texts()["SKILL.md"]
        for seeded in (
            good.replace("name: cement-learn", "name: Cement-Learn"),
            good.replace("name: cement-learn", "name: cement--learn"),
            good.replace("license: Apache-2.0", "license: MIT"),
            good.replace("license: Apache-2.0", "license: Apache-2.0\nversion: 1"),
            re.sub(r"description: .*", "description: " + "x" * 1025, good),
        ):
            self.assertNotEqual(_frontmatter_failures(seeded, SKILL.name), [])
        self.assertNotEqual(_frontmatter_failures(good, "cement-learn-2"), [])
        for seeded in (
            "```sh\ncement learn case \"$OP\"\n```\n",
            "```sh\ncement compile \"$OP\" --actr learning-pass\n```\n",
            "```sh\ncement function promote \"$OP\" --actor learning-pass\n```\n",
            "Never run `cement function swich`.\n",
        ):
            with self.subTest(seeded=seeded):
                self.assertEqual(len(_command_failures(seeded)), 1)
        self.assertEqual(_command_failures("Never run `cement function switch`.\n"), [])


class PolicyDefaultsBattery(unittest.TestCase):
    """LP4: owner ruling O2 — the defaults are 2 confirmations / 1 reviewer / 0 s, CLI included."""

    def test_lp4_signature_and_abi(self) -> None:
        parameters = inspect.signature(CompilePolicy).parameters
        self.assertEqual(
            [(name, p.default) for name, p in parameters.items()],
            [("min_confirmations", 2), ("min_reviewers", 1), ("min_span_seconds", 0)],
        )
        self.assertEqual(
            [(f.name, f.default) for f in dataclasses.fields(CompilePolicy)],
            [("min_confirmations", 2), ("min_reviewers", 1), ("min_span_seconds", 0)],
        )
        self.assertEqual(
            CompilePolicy().as_json(),
            {"min_confirmations": 2, "min_reviewers": 1, "min_span_seconds": 0},
        )

    def test_lp4_cli_register_and_revise_default_to_the_library_policy(self) -> None:
        for leaf in ("register", "revise"):
            args = _parser().parse_args(["operation", leaf, "plan", "--actor", "operator"])
            self.assertEqual(
                (args.min_confirmations, args.min_reviewers, args.min_span_seconds), (2, 1, 0)
            )


if __name__ == "__main__":
    unittest.main()
