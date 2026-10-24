"""M4.2 battery — the projection lifecycle on the ledger.

Contract: `.agent/decisions/m45-contract.md` §5 (L1-L9). A projection (O5) maps raw input to an
exact case key; the learning pass writes it, Cement verifies it (V1-V4) and builds, verifies,
promotes and serves projected cases without ever widening a key beyond the inputs it has seen.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
import unittest.mock

import sqlite3
from contextlib import closing

from cement_runtime import (
    Candidate,
    CompilePolicy,
    ConflictError,
    IntegrityError,
    System,
    ValidationError,
    evaluate,
    parse_function,
)
from cement_runtime.json_value import canonicalize
from cement_runtime.projection import parse_program, project, structure

P, OP = "tenant_a", "plan"
POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
# Contract §5 C4 owns this vector: the six checks + `projection-uniform`, in order.
LIVE_CHECKS = [
    "duplicate-input-digests",
    "abi-canonicalizer-uniform",
    "sealed-passing-reports",
    "current-promotion-receipts",
    "function-hash-matches-snapshot",
    "persisted-function-receipt",
    "projection-uniform",
]
DOCS = sorted((pathlib.Path(__file__).resolve().parents[1] / "examples/hospital_ocr/documents").glob("*.txt"))


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


class _ProjectionCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-projection-")
        self.addCleanup(directory.cleanup)
        self.system = System(str(pathlib.Path(directory.name) / "ledger.db"))
        self.system.register_operation(P, OP, policy=POLICY)
        self.texts = [doc.read_text(encoding="utf-8") for doc in DOCS]

    def _confirm(self, text: str, output: object) -> None:
        proposal = self.system.submit_proposal(
            P, OP, {"document": text}, candidate=Candidate(output=output, provenance={})
        )
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")

    def _learn_all(self) -> dict[str, object]:
        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        program = _program(self.texts)
        self.system.set_projection(P, OP, program, actor="learning-pass")
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        self.system.set_switch(P, OP, mode="follow", actor="person")
        return program

    def _confirm_raw(self, value: object, output: object) -> None:
        proposal = self.system.submit_proposal(
            P, OP, value, candidate=Candidate(output=output, provenance={})
        )
        self.system.review(P, proposal, reviewer="learning-pass", decision="accept")

    def _build_and_promote(self) -> str:
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        return manifest.function_hash

    def _ledger(self) -> tuple[object, ...]:
        """Every table's row count + each artifact's status: a refusal leaves both unchanged."""
        with self.system.store.transaction() as connection:
            tables = [
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                )
            ]
            counts = tuple(
                int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
                for table in tables
            )
            statuses = tuple(
                tuple(row)
                for row in connection.execute("SELECT id, status, status_reason FROM artifacts ORDER BY id")
            )
        return counts, statuses

    def _counts(self) -> tuple[int, ...]:
        with self.system.store.transaction() as connection:
            return tuple(
                int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("projection_settings", "projection_programs", "events")
            )


class ProjectionLifecycleBattery(_ProjectionCase):
    def test_l1_a_new_document_of_a_seen_layout_resolves_and_a_new_layout_misses(self) -> None:
        self._learn_all()
        fresh = self.texts[0].replace("Jane Doe", "Someone New").replace("MG-100241", "MG-777777")
        answer = self.system.resolve(P, OP, {"document": fresh}).match
        self.assertEqual((answer.matched, answer.output), (True, {"plan": self.texts[0].splitlines()[0]}))
        extra = self.texts[3].replace("Primary Complaint:", "Referral: none\nPrimary Complaint:")
        missed = self.system.resolve(P, OP, {"document": extra})
        self.assertEqual((missed.verification.passed, missed.match.matched), (True, False))
        self.assertFalse(self.system.resolve(P, OP, {"document": "not a form"}).match.matched)

    def test_l2_each_refusal_writes_nothing(self) -> None:
        program = self._learn_all()
        layouts = program["layouts"]
        unwitnessed = dict(program, layouts=[*layouts, {"name": "x", "title": "NEVER SEEN", "entries": [{"label": "A"}]}])  # type: ignore[misc]
        before = self._ledger()
        with self.assertRaisesRegex(ValidationError, "layouts no confirmed example shows"):
            self.system.set_projection(P, OP, unwitnessed, actor="learning-pass")
        self.assertEqual(self._ledger(), before)
        self._confirm(self.texts[1], {"plan": "a different answer for the same layout"})
        renamed = dict(program, layouts=[dict(layout, name=f"{layout['name']} v2") for layout in layouts])  # type: ignore[attr-defined]
        before = self._ledger()
        with self.assertRaisesRegex(ValidationError, "merges confirmed examples with different outputs"):
            self.system.set_projection(P, OP, renamed, actor="learning-pass")
        self.assertEqual(self._ledger(), before)

    def test_l2_a_program_no_example_satisfies_is_refused(self) -> None:
        self._confirm(self.texts[0], {"plan": "x"})
        program = _program([self.texts[0]])
        program["text"] = "ocr"
        before = self._counts()
        with self.assertRaises(ValidationError):
            self.system.set_projection(P, OP, program, actor="learning-pass")
        self.assertEqual(self._counts(), before)

    def test_l3_a_program_change_retires_stale_builds_and_keeps_promoted_ones(self) -> None:
        program = self._learn_all()
        promoted = {row["id"] for row in self.system.artifacts(P, OP) if row["status"] == "promoted"}
        for text in self.texts[:2]:
            self._confirm(text.replace("Jane", "J"), {"plan": text.splitlines()[0]})
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        self._confirm(self.texts[5].replace("Jane", "J"), {"plan": self.texts[5].splitlines()[0]})
        self.system.compile(P, OP)
        stale = {row["id"]: row["status"] for row in self.system.artifacts(P, OP) if row["status"] in ("draft", "verified")}
        self.assertEqual(set(stale.values()), {"draft", "verified"})
        smaller = dict(program, layouts=program["layouts"][:2])  # type: ignore[index]
        result = self.system.set_projection(P, OP, smaller, actor="learning-pass")
        self.assertTrue(result["changed"])
        self.assertEqual(sorted(result["retired"]), sorted(stale))  # type: ignore[arg-type]
        after = {row["id"]: (row["status"], row["status_reason"]) for row in self.system.artifacts(P, OP)}
        for artifact_id in stale:
            self.assertEqual(after[artifact_id], ("retired", "projection superseded"))
        self.assertEqual({artifact_id: after[artifact_id][0] for artifact_id in promoted}, dict.fromkeys(promoted, "promoted"))
        self.assertTrue(self.system.resolve(P, OP, {"document": self.texts[0]}).match.matched)

    def test_l4_compile_reports_examples_the_program_refuses(self) -> None:
        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        self.system.set_projection(P, OP, _program(self.texts), actor="learning-pass")
        self._confirm("free text, no form", {"plan": "none"})
        self._confirm("free text, no form", {"plan": "none"})
        blocked = self.system.compile(P, OP).blocked
        self.assertEqual([entry["support"] for entry in blocked], [2])
        self.assertIn("unprojected", str(blocked[0]["reasons"]))

    def test_l5_the_bundle_answers_raw_input_ledger_free_like_resolve(self) -> None:
        self._learn_all()
        verification = self.system.verify_function(P, OP)
        self.assertEqual([check.key for check in verification.checks], LIVE_CHECKS)
        self.assertTrue(all(check.passed for check in verification.checks))
        bundle = parse_function(verification.document.text, expected_function_hash=verification.function_hash)
        raws = [*self.texts, "not a form"]
        online = [self.system.resolve(P, OP, {"document": text}).match for text in raws]
        ledger = AssertionError("bundle evaluation reached a ledger")
        with (
            unittest.mock.patch("cement_runtime.system.System", side_effect=ledger),
            unittest.mock.patch("sqlite3.connect", side_effect=ledger),
        ):
            offline = [evaluate(bundle, input_json=canonicalize({"document": text})) for text in raws]
        self.assertEqual(
            [(match.matched, match.output) for match in offline],
            [(match.matched, match.output) for match in online],
        )
        self.assertEqual([match.matched for match in online], [True] * len(self.texts) + [False])

    def test_l8_an_identical_program_is_a_no_op_and_a_b_a_rebuilds(self) -> None:
        program = self._learn_all()
        before = self._ledger()
        self.assertFalse(self.system.set_projection(P, OP, program, actor="learning-pass")["changed"])
        self.assertEqual(self._ledger(), before)
        (version_a,) = self.system.function_receipts(P, OP).receipts
        first_a = {row["id"]: row["build_hash"] for row in self.system.artifacts(P, OP) if row["status"] == "promoted"}
        dropped_title = program["layouts"][2]["title"]  # type: ignore[index]
        dropped_doc = next(text for text in self.texts if text.startswith(str(dropped_title)))
        self.system.set_projection(P, OP, dict(program, layouts=program["layouts"][:2]), actor="learning-pass")  # type: ignore[index]
        self._build_and_promote()
        self.assertFalse(self.system.resolve(P, OP, {"document": dropped_doc}).match.matched)
        self.system.set_projection(P, OP, program, actor="learning-pass")
        self._build_and_promote()
        again = {row["id"]: row["build_hash"] for row in self.system.artifacts(P, OP) if row["status"] == "promoted"}
        # A→B→A = content reuse, never row reuse: fresh rows carrying A's build hashes.
        self.assertFalse(set(again) & set(first_a))
        self.assertEqual(sorted(again.values()), sorted(first_a.values()))
        answer = self.system.resolve(P, OP, {"document": dropped_doc}).match
        self.assertEqual((answer.matched, answer.output), (True, {"plan": dropped_title}))
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=version_a.function_hash)
        pinned = self.system.resolve(P, OP, {"document": dropped_doc})
        self.assertEqual((pinned.verification.passed, pinned.match.output), (True, {"plan": dropped_title}))

    def test_v1_an_invalid_program_is_refused_before_any_write(self) -> None:
        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        good = _program(self.texts)
        before = self._ledger()
        for label, bad in (
            ("empty", {}),
            ("abi", dict(good, abi="cement-projection-v0")),
            ("no layouts", dict(good, layouts=[])),
        ):
            with self.subTest(label), self.assertRaises(ValidationError):
                self.system.set_projection(P, OP, bad, actor="learning-pass")
            with self.subTest(label), self.assertRaises(ValidationError):
                self.system.test_projection(P, OP, bad)
        self.assertEqual(self._ledger(), before)

    def test_l18_verification_fails_an_interpreter_that_ignores_a_missing_last_structural_line(self) -> None:
        import cement_runtime.system as system_module

        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        self.system.set_projection(P, OP, _program(self.texts), actor="learning-pass")
        self.system.compile(P, OP)
        real = system_module.project

        def without_last(text: str) -> str:
            lines = text.split("\n")
            last = max(index for index, line in enumerate(lines) if ":" in line)
            return "\n".join(lines[:last] + lines[last + 1 :])

        shortened = {without_last(text): text for text in self.texts}

        def lenient(program: object, raw: object) -> object:
            # An interpreter that accepts a document missing its last field as the full one.
            if type(raw) is dict and raw.get("document") in shortened:
                raw = {**raw, "document": shortened[raw["document"]]}
            return real(program, raw)  # type: ignore[arg-type]

        with unittest.mock.patch.object(system_module, "project", lenient):
            self.assertFalse(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)



FIXTURE_V2 = pathlib.Path(__file__).resolve().parent / "fixtures/function-v2.json"



class ProjectionLifecycleBatteryII(_ProjectionCase):
    """L6, L7, L9 + S7 (the program-row hash check on read, owned here: no trigger can sha256)."""

    def test_l6_a_v2_bundle_still_parses_and_evaluates(self) -> None:
        # Captured from the real v2 package (`git archive 1935f68 src`): two exact entries,
        # {"doc": 1} → {"plan": "one"} and {"doc": 2} → {"plan": "two"}.
        document = parse_function(FIXTURE_V2.read_text(encoding="utf-8"))
        self.assertEqual(document.value["abi"], "cement-function-v2")
        pairs = [(entry["input"], entry["output"]) for entry in json.loads(FIXTURE_V2.read_text(encoding="utf-8"))["entries"]]
        self.assertEqual(len(pairs), 2)
        for value, output in pairs:
            match = evaluate(document, input_json=canonicalize(value))
            self.assertEqual((match.matched, match.output), (True, output))
        unseen = {"doc": 3}
        self.assertNotIn(unseen, [value for value, _ in pairs])
        self.assertFalse(evaluate(document, input_json=canonicalize(unseen)).matched)

    def _fabricate(
        self, sql: str, values: tuple[object, ...], trigger: str = "artifacts_build_fields_immutable"
    ) -> None:
        # FABRICATED (runtime law): the fields are immutable by trigger, so the probe captures
        # the trigger DDL, drops it, corrupts, and recreates it.
        with closing(sqlite3.connect(self.system.store.path)) as connection:
            (ddl,) = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = ?", (trigger,)
            ).fetchone()
            connection.execute(f"DROP TRIGGER {trigger}")
            connection.execute(sql, values)
            connection.execute(ddl)
            connection.commit()

    def test_l7_a_fabricated_mixed_set_fails_projection_uniform_alone_of_its_cause(self) -> None:
        self._learn_all()
        self.assertTrue(self.system.verify_function(P, OP).passed)
        member = sorted(row["id"] for row in self.system.artifacts(P, OP) if row["status"] == "promoted")[1]
        self._fabricate("UPDATE artifacts SET projection_hash = NULL WHERE id = ?", (member,))
        result = self.system.verify_function(P, OP)
        checks = {check.key: check for check in result.checks}
        self.assertFalse(result.passed)
        self.assertFalse(checks["projection-uniform"].passed)
        self.assertEqual(checks["projection-uniform"].detail, "2 programs across one set")
        self.assertEqual(list(checks), LIVE_CHECKS)
        failed = [check.key for check in result.checks if not check.passed]
        self.assertIn("projection-uniform", failed)

    def test_l9_a_projection_set_between_inspect_and_promote_refuses_the_stale_hash(self) -> None:
        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        program = _program(self.texts)
        self.system.set_projection(P, OP, program, actor="learning-pass")
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        stale = self.system.inspect_function_promotion(P, OP).function_hash
        # Same keys, another program hash: `name` is display only, so every key survives.
        renamed = dict(program, layouts=[dict(layout, name=f"{layout['name']} v2") for layout in program["layouts"]])  # type: ignore[attr-defined]
        self.system.set_projection(P, OP, renamed, actor="learning-pass")
        before = self._counts()
        with self.assertRaisesRegex(Exception, "at least one member"):
            self.system.promote_function(P, OP, expected_function_hash=stale, promoted_by="learning-pass")
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        current = self.system.inspect_function_promotion(P, OP).function_hash
        self.assertNotEqual(current, stale)
        with self.assertRaises(ConflictError):
            self.system.promote_function(P, OP, expected_function_hash=stale, promoted_by="learning-pass")
        with self.system.store.transaction() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM function_receipts").fetchone()[0], 0)
        self.system.promote_function(P, OP, expected_function_hash=current, promoted_by="learning-pass")
        self.assertGreater(self._counts()[2], before[2])

    def test_l10_a_pinned_projected_version_answers_until_a_challenge_hits_a_member_key(self) -> None:
        self._learn_all()
        (receipt,) = self.system.function_receipts(P, OP).receipts
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=receipt.function_hash)
        fresh = self.texts[0].replace("Jane Doe", "Someone New")
        served = self.system.resolve(P, OP, {"document": fresh})
        self.assertEqual((served.verification.passed, served.match.output), (True, {"plan": self.texts[0].splitlines()[0]}))
        other = self.texts[0].replace("Jane Doe", "A Third Patient")
        self.system.challenge(P, OP, {"document": other}, {"plan": "WRONG"}, reviewer="person")
        failed = self.system.resolve(P, OP, {"document": fresh})
        self.assertEqual((failed.verification.passed, failed.match), (False, None))
        # The challenge also suspends the member it contradicts (challenge = explicit judgment).
        self.assertEqual(
            [check.key for check in failed.verification.checks if not check.passed],
            ["pinned-members-unsuspended", "pinned-no-counterexample"],
        )
        intake = next(text for text in self.texts if text.startswith("PATIENT INTAKE FORM"))
        _, suspended = self.system.challenge(
            P, OP, {"document": intake + "\n"}, {"plan": "PATIENT INTAKE FORM"}, reviewer="person"
        )
        self.assertFalse(suspended)

    def test_l11_a_narrower_program_promotes_a_uniform_set_and_retires_the_dropped_layout(self) -> None:
        program = self._learn_all()
        (v1,) = self.system.function_receipts(P, OP).receipts
        kept = program["layouts"][:2]  # type: ignore[index]
        dropped_title = program["layouts"][2]["title"]  # type: ignore[index]
        self.system.set_projection(P, OP, dict(program, layouts=kept), actor="learning-pass")
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        manifest = self.system.inspect_function_promotion(P, OP)
        superseded = [entry for entry in manifest.skipped if entry["reason"] == "projection-superseded"]
        self.assertEqual(len(superseded), 1)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        live = self.system.verify_function(P, OP)
        self.assertTrue(live.passed, [check for check in live.checks if not check.passed])
        self.assertEqual(self.system.artifact(P, str(superseded[0]["artifact_id"]))["status"], "retired")
        dropped_doc = next(text for text in self.texts if text.startswith(str(dropped_title)))
        missed = self.system.resolve(P, OP, {"document": dropped_doc})
        self.assertEqual((missed.verification.passed, missed.match.matched), (True, False))
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=v1.function_hash)
        pinned = self.system.resolve(P, OP, {"document": dropped_doc})
        self.assertEqual((pinned.verification.passed, pinned.match.output), (True, {"plan": dropped_title}))

    def test_l13_the_preview_lists_pending_proposals_with_their_key_or_reason(self) -> None:
        for text in self.texts[:2]:
            self._confirm(text, {"plan": text.splitlines()[0]})
        waiting = self.system.submit_proposal(
            P, OP, {"document": self.texts[2]}, candidate=Candidate(output={"plan": "x"}, provenance={})
        )
        stray = self.system.submit_proposal(
            P, OP, {"document": "free text"}, candidate=Candidate(output={"plan": "y"}, provenance={})
        )
        report = self.system.test_projection(P, OP, _program(self.texts[:3]))
        items = {item["id"]: item for item in report["items"]}
        self.assertEqual(items[stray]["key_hash"], None)
        self.assertEqual(items[stray]["reason"], "layout")
        self.assertIsNotNone(items[waiting]["key_hash"])
        keys = {entry["key_hash"]: entry for entry in report["keys"]}
        self.assertEqual(keys[items[waiting]["key_hash"]]["pending"], 1)
        self.assertEqual({entry["ready"] for entry in report["keys"]}, {True} | ({False} if len(keys) > 1 else set()))

    def test_l19_preview_readiness_agrees_with_every_compile_gate(self) -> None:
        text = "FORM\nA: value"
        program = _program([text])
        for gate, policy in (
            ("reviewers", CompilePolicy(min_confirmations=2, min_reviewers=2, min_span_seconds=0)),
            ("span", CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=86400)),
            ("none", POLICY),
        ):
            with self.subTest(gate=gate):
                self.system.revise_operation(P, OP, policy=policy, revised_by="person")
                for _ in range(2):
                    self._confirm(text, {"plan": "same"})
                (key,) = self.system.test_projection(P, OP, program)["keys"]  # type: ignore[misc]
                self.system.set_projection(P, OP, program, actor="learning-pass")
                compiled = self.system.compile(P, OP)
                self.assertEqual(key["ready"], not compiled.blocked)
                self.assertEqual(len(compiled.created) + len(compiled.blocked), 1)

    def test_l14_one_verification_projects_each_raw_input_once(self) -> None:
        import cement_runtime.system as system_module

        self._learn_all()
        fresh = System(self.system.store.path, create=False)
        with unittest.mock.patch.object(system_module, "project", wraps=system_module.project) as spy:
            self.assertTrue(fresh.verify_function(P, OP).passed)
        self.assertEqual(spy.call_count, len(self.texts))

    def _contradiction_events(self) -> int:
        with self.system.store.transaction() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM events WHERE kind = 'artifact.contradicted'"
            ).fetchone()
            return int(row[0])

    def test_l15_only_evidence_that_projects_to_a_key_contradicts_its_projected_member(self) -> None:
        self._learn_all()
        live = self.system.verify_function(P, OP)
        key = live.document.entries[0].input.value
        self.assertFalse(project(live.document.projection, key).matched)
        # The raw key itself is NoMatch under the member's program: different evidence on it
        # reaches no member, so review records no contradiction and the live set still verifies.
        self._confirm_raw(key, {"other": 1})
        self.assertEqual(self._contradiction_events(), 0)
        after = self.system.verify_function(P, OP)
        self.assertTrue(after.passed, [check for check in after.checks if not check.passed])
        # A raw document of the member's layout reaches the key: the same act now contradicts.
        reached = next(
            text for text in self.texts
            if canonicalize(project(live.document.projection, {"document": text}).key.value).text
            == canonicalize(key).text
        )
        self._confirm(reached.replace("Jane Doe", "Another Patient"), {"plan": "CONTRARY"})
        self.assertEqual(self._contradiction_events(), 1)
        failed = self.system.verify_function(P, OP)
        self.assertEqual(
            [check.key for check in failed.checks if not check.passed], ["current-promotion-receipts"]
        )

    def test_l16_a_challenge_that_is_nomatch_under_the_pinned_program_leaves_the_pin_answering(self) -> None:
        text = "FORM\nA: value"
        program = _program([text])
        key = project(parse_program(program), {"document": text}).key.value
        self.assertFalse(project(parse_program(program), key).matched)
        for _ in range(2):
            self._confirm_raw(key, {"old": "exact"})
        self._build_and_promote()
        self.system.challenge(P, OP, key, {"old": "counterexample"}, reviewer="person")
        projected_answer = {"new": "projected"}
        for _ in range(2):
            self._confirm(text, projected_answer)
        self.system.set_projection(P, OP, program, actor="learning-pass")
        manifest = self._build_and_promote()
        self.system.set_switch(P, OP, mode="pinned", function_hash=manifest, actor="person")
        result = self.system.resolve(P, OP, {"document": text})
        self.assertTrue(
            result.verification.passed, [check for check in result.verification.checks if not check.passed]
        )
        self.assertEqual(result.match.output, projected_answer)

    def test_l17_reconstruction_refuses_a_member_built_under_another_program_than_its_receipt(self) -> None:
        import cement_runtime.system as system_module

        program = self._learn_all()
        renamed = dict(program, layouts=[dict(layout, name=f"{layout['name']} v2") for layout in program["layouts"]])  # type: ignore[attr-defined]
        self.system.set_projection(P, OP, renamed, actor="learning-pass")
        # Regression probe: a plan that seals the previous program's members under the new
        # program (the mixed receipt the drop rule prevents) must still fail reconstruction.
        old, new = parse_program(program), parse_program(renamed)
        build = system_module.build_function

        def sealed_under_new(*args: object, **kwargs: object) -> object:
            return build(*args, **dict(kwargs, projection=new))

        with (
            unittest.mock.patch.object(System, "_build_program", staticmethod(lambda *a, **k: old)),
            unittest.mock.patch.object(system_module, "build_function", sealed_under_new),
        ):
            manifest = self.system.inspect_function_promotion(P, OP)
            self.system.promote_function(
                P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
            )
        with self.system.store.transaction() as connection:
            programs = connection.execute(
                """
                SELECT DISTINCT f.projection_hash, a.projection_hash FROM function_receipts AS f
                JOIN function_memberships AS m ON m.receipt_id = f.id
                JOIN artifacts AS a ON a.id = m.artifact_id WHERE f.function_hash = ?
                """,
                (manifest.function_hash,),
            ).fetchall()
        self.assertEqual([tuple(row) for row in programs], [(new.program_hash, old.program_hash)])
        self.system.set_switch(P, OP, mode="pinned", actor="person", function_hash=manifest.function_hash)
        served = self.system.resolve(P, OP, {"document": self.texts[0]})
        failed = {check.key: check.detail for check in served.verification.checks if not check.passed}
        self.assertFalse(served.verification.passed)
        self.assertIn("program binding mismatch", " ".join(failed.values()), failed)

    def test_l20_a_full_memo_never_repeats_a_projection_inside_one_verification(self) -> None:
        import collections

        import cement_runtime.system as system_module

        program = parse_program(self._learn_all())
        capacity = len(self.texts) + 1  # the bound's logic, at a size the test can fill
        with unittest.mock.patch.object(system_module, "_CASE_KEY_MEMO_MAX", capacity):
            for warm in (0, capacity - 1):
                fresh = System(self.system.store.path, create=False)
                for number in range(warm):
                    raw = canonicalize({"document": f"unrecognized form {number}"})
                    fresh._case_key_text(program, raw.text, raw.digest)
                calls: collections.Counter[str] = collections.Counter()
                real = system_module.project

                def counted(program: object, value: object) -> object:
                    calls[canonicalize(value).digest] += 1  # type: ignore[arg-type]
                    return real(program, value)  # type: ignore[arg-type]

                with self.subTest(warm=warm), unittest.mock.patch.object(system_module, "project", counted):
                    self.assertTrue(fresh.verify_function(P, OP).passed)
                    self.assertEqual(sorted(calls.values()), [1] * len(self.texts))

    def test_s7_a_stored_program_that_does_not_hash_to_its_key_is_refused_on_read(self) -> None:
        program = _program(self.texts)
        forged = "a" * 64
        with self.system.store.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO projection_programs(program_hash, abi, program_json) VALUES (?, ?, ?)",
                (forged, "cement-projection-v1", canonicalize(program).text),
            )
            connection.execute(
                """
                INSERT INTO projection_settings(
                    id, partition, operation, operation_revision, program_hash, set_by, set_at_us
                ) VALUES ('ps_forged', ?, ?, 1, ?, 'forger', 1)
                """,
                (P, OP, forged),
            )
        for call in (lambda: self.system.projection(P, OP), lambda: self.system.compile(P, OP)):
            with self.assertRaisesRegex(IntegrityError, "does not hash to its key"):
                call()


class ProjectionEventBoundTests(_ProjectionCase):
    """p138: list payloads stay inside `_event`'s 262,144-byte bound, whatever the ledger holds."""

    def test_p138_set_projection_retires_ten_thousand_stale_artifacts(self) -> None:
        # An `art_<32 hex>` id costs 39 canonical bytes, so the full list passed the event bound
        # at about 6,717 stale artifacts and the projection could no longer change.
        import cement_runtime.system as system_module

        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
            self._confirm(text, {"plan": text.splitlines()[0]})
        self.system.compile(P, OP)
        with self.system.store.transaction(write=True) as connection:
            columns = [str(row[1]) for row in connection.execute("PRAGMA table_info(artifacts)")][2:]
            (built,) = connection.execute("SELECT COUNT(*) FROM artifacts WHERE status = 'draft'").fetchone()
            # Stale drafts beside the real ones: copies of one draft row under fresh ids.
            connection.execute(
                f"""
                WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < ?)
                INSERT INTO artifacts(id, {", ".join(columns)})
                SELECT printf('art_%032x', i), {", ".join(columns)}
                FROM n, (SELECT * FROM artifacts WHERE status = 'draft' ORDER BY sequence LIMIT 1)
                """,
                (10_000 - int(built),),
            )
        change = self.system.set_projection(P, OP, _program(self.texts), actor="learning-pass")
        retired = sorted(change["retired"])
        self.assertEqual(len(retired), 10_000)
        (event,) = [event for event in self.system.events(P) if event["kind"] == "projection.set"]
        payload = event["payload"]
        self.assertEqual(
            {key: payload[key] for key in ("retired_artifact_count", "retired_artifact_ids", "retired_artifact_ids_hash")},
            {
                "retired_artifact_count": 10_000,
                "retired_artifact_ids": retired[:100],
                "retired_artifact_ids_hash": system_module._id_list_hash(retired),
            },
        )

    def test_p138_a_failing_structural_probe_counts_into_one_failure(self) -> None:
        # `_run_verification` appended one "structural edit" failure per example, so a case's
        # failure list grew with its evidence until the report passed its own byte bound.
        import collections

        import cement_runtime.system as system_module

        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        program = _program(self.texts)
        self.system.set_projection(P, OP, program, actor="learning-pass")
        self.system.compile(P, OP)
        parsed = parse_program(program)
        support = collections.Counter(project(parsed, {"document": text}).key.digest for text in self.texts)  # type: ignore[union-attr]
        real = system_module.project

        def without_last(text: str) -> str:
            lines = text.split("\n")
            last = max(index for index, line in enumerate(lines) if ":" in line)
            return "\n".join(lines[:last] + lines[last + 1 :])

        shortened = {without_last(text): text for text in self.texts}

        def lenient(program: object, raw: object) -> object:
            # L18's defective interpreter: a document missing its last field reads as the full one.
            if type(raw) is dict and raw.get("document") in shortened:
                raw = {**raw, "document": shortened[raw["document"]]}
            return real(program, raw)  # type: ignore[arg-type]

        with unittest.mock.patch.object(system_module, "project", lenient):
            result = self.system.verify_drafts(P, OP, verified_by="learning-pass")
        self.assertFalse(result.passed)
        self.assertTrue(result.entries)
        for entry in result.entries:
            with self.subTest(case=entry.input_hash[:12]):
                self.assertGreaterEqual(support[entry.input_hash], 2)
                self.assertEqual(
                    [failure for failure in entry.report.failures if "structural" in failure],
                    [f"{support[entry.input_hash]} structural-edit probes kept the projected key"],
                )


if __name__ == "__main__":
    unittest.main()
