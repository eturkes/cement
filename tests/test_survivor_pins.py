"""Tests that survivor rulings added as `missing-test` (`.agent/decisions/survivor-rulings.md`).

Each test names the row and the survivor it kills.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from typing import Any
from unittest import mock

from cement_runtime import System, cli
from cement_runtime.errors import ValidationError
from cement_runtime.json_value import canonicalize
from cement_runtime.projection import PROJECTION_ABI, PROJECTION_ABI_V2, parse_program
from tests.test_open_webui_example import DOC, OP, PLAN, _call, _Example
from tests.test_projection_lifecycle_battery import OP as PROJECTION_OP
from tests.test_projection_lifecycle_battery import P as PROJECTION_P
from tests.test_projection_lifecycle_battery import _program, _ProjectionCase


class ForgedEquality(type):
    """A metaclass whose classes claim equality with every class: `type(x) == T` holds for its
    instances, `type(x) is T` never does — the gap each `is` → `==` survivor ruling pins."""

    def __eq__(cls, other: object) -> bool:
        return True

    def __ne__(cls, other: object) -> bool:
        return False

    __hash__ = type.__hash__


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

    def test_p115_a_long_distinct_id_selection_is_no_duplicate(self) -> None:
        # p115: `len(set(ids)) != len(ids)` → `is not` survived. CPython caches small ints alone
        # (to 256), so the identity form refuses every distinct selection longer than that.
        from cement_runtime import system as system_module

        with tempfile.TemporaryDirectory(prefix="cement-p115-") as directory:
            system = System(str(pathlib.Path(directory) / "ledger.db"))
            system.register_operation("tenant-a", "echo")
            ids = tuple(f"prop_{index:032x}" for index in range(300))
            with system.store.transaction() as connection:
                bound = system_module._proposal_bindings(
                    connection, partition="tenant-a", selection=system_module._ProposalIds(ids)
                )
        self.assertEqual((bound.total, bound.rows), (0, ()))

    def test_p114_text_refuses_a_class_forging_equality_with_str(self) -> None:
        # p114: `_text`'s `type(value) is not str` → `!=` survived; equality with `str` can be
        # forged through a metaclass, identity cannot.
        class LooksLikeText(metaclass=ForgedEquality):
            def encode(self, encoding: str) -> bytes:
                return b"actor"

            def __iter__(self):  # noqa: ANN204 — the shape `_text` iterates
                return iter("actor")

        with tempfile.TemporaryDirectory(prefix="cement-p114-") as directory:
            system = System(str(pathlib.Path(directory) / "ledger.db"))
            with self.assertRaises(ValidationError) as raised:
                system.register_operation("tenant-a", "echo", registered_by=LooksLikeText())  # type: ignore[arg-type]
        self.assertEqual(str(raised.exception), "registered_by must be non-empty text")

    def test_p114_the_event_payload_cap_is_an_adjacent_pair(self) -> None:
        # p114: `_event`'s `max_bytes=262_144` ±1 survived; `set_projection` reaches the cap (p138).
        from cement_runtime import system as system_module

        frame = len('{"p":""}')
        with tempfile.TemporaryDirectory(prefix="cement-p114-") as directory:
            store = system_module.Store(str(pathlib.Path(directory) / "ledger.db"))
            for size, accepted in ((262_144, True), (262_145, False)):
                with self.subTest(size=size), store.transaction(write=True) as connection:
                    write = lambda: system_module._event(  # noqa: E731 — one call, two outcomes
                        connection, partition="tenant-a", kind="operation.registered",
                        subject_type="operation", subject_id="tenant-a/echo@1",
                        payload={"p": "x" * (size - frame)}, now_us=1,
                    )
                    if accepted:
                        self.assertGreater(write(), 0)
                    else:
                        with self.assertRaises(ValidationError) as raised:
                            write()
                        self.assertEqual(str(raised.exception), "canonical JSON exceeds 262144 bytes")

    def test_p101_bundle_type_checks_refuse_classes_forging_equality(self) -> None:
        # p101: `validate_function` + `build_function` take caller objects, and each `type(x) is T`
        # → `==` survived (`function.py` `_normalize` document, abi, operation revision, entries;
        # `build_function` entries). Forged equality passes `==`; identity refuses.
        from copy import deepcopy

        from cement_runtime import FUNCTION_ABI, build_function, validate_function
        from tests.test_function import _build, _entry

        class Forged(metaclass=ForgedEquality):
            pass

        class ForgedAbi(metaclass=ForgedEquality):
            # Equal to the v3 ABI alone, so `_normalize` keeps v3's key set and reaches the check.
            def __eq__(self, other: object) -> bool:
                return other == FUNCTION_ABI

            def __hash__(self) -> int:
                return hash(FUNCTION_ABI)

        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="p101"),))
        cases = {
            "document": (lambda: Forged(), "invalid function: expected keys"),
            "abi": (lambda: {**deepcopy(bundle.value), "abi": ForgedAbi()}, "unsupported function ABI"),
            "operation_revision": (
                lambda: {**deepcopy(bundle.value), "scope": {**bundle.value["scope"], "operation_revision": Forged()}},
                "function operation revision must be a positive signed 64-bit integer",
            ),
            "entries": (lambda: {**deepcopy(bundle.value), "entries": Forged()}, "function entries must be an array"),
        }
        for name, (document, message) in cases.items():
            with self.subTest(field=name), self.assertRaises(ValidationError) as raised:
                validate_function(document())
            self.assertTrue(str(raised.exception).startswith(message), str(raised.exception))
        with self.assertRaises(ValidationError) as raised:
            build_function(
                partition="tenant-a", operation="echo", operation_revision=1,
                policy_hash="0" * 64, entries=[Forged()],
            )
        self.assertEqual(str(raised.exception), "function entries must be FunctionEntry values")

    def test_p101_a_half_set_projection_is_refused_as_invalid(self) -> None:
        # p101: `projection is not None or projection_hash is not None` → `and` survived: with one
        # of the two set, the projected branch must still run and refuse the missing half.
        from copy import deepcopy

        from cement_runtime import validate_function
        from cement_runtime.projection import draft_program, parse_program
        from tests.test_function import _build, _entry, _rehash

        program = parse_program(draft_program([{"doc": "Intake\nName: Ada"}]))
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="p101-half"),))
        for name, projection, projection_hash in (
            ("hash alone", None, program.program_hash),
            ("program alone", program.canonical.value, None),
        ):
            document = deepcopy(bundle.value)
            document["projection"], document["projection_hash"] = projection, projection_hash
            _rehash(document)
            with self.subTest(case=name), self.assertRaises(ValidationError):
                validate_function(document)

    def test_p101_a_projection_hash_mismatch_is_refused_in_both_orders(self) -> None:
        # p101: `program_hash != projection_hash` → `<`, `>` and `is` survived; a mismatch below
        # and above the program's hash must both refuse.
        from copy import deepcopy

        from cement_runtime import IntegrityError, validate_function
        from cement_runtime.projection import draft_program, parse_program
        from tests.test_function import _build, _entry, _rehash

        program = parse_program(draft_program([{"doc": "Intake\nName: Ada"}]))
        bundle = _build((_entry({"x": 1}, {"answer": 1}, label="p101-order"),))
        for wrong in ("0" * 64, "f" * 64):
            document = deepcopy(bundle.value)
            document["projection"], document["projection_hash"] = program.canonical.value, wrong
            _rehash(document)
            with self.subTest(projection_hash=wrong[:4]), self.assertRaises(IntegrityError) as raised:
                validate_function(document)
            self.assertEqual(
                str(raised.exception), "function projection does not hash to its projection_hash"
            )

    def test_p111_register_grades_its_actor_before_creating_a_ledger(self) -> None:
        # p111: the CLI pre-check `_text(args.actor, "registered_by", maximum=256)` ±1 survived;
        # 256 bytes register, and 257 are refused before `System(create=True)` makes a file (p51).
        with tempfile.TemporaryDirectory(prefix="cement-p111-") as directory:
            for size, status in ((256, 0), (257, 2)):
                database = pathlib.Path(directory) / f"ledger-{size}.db"
                stdout, stderr = io.StringIO(), io.StringIO()
                with self.subTest(size=size), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = cli.main([
                        "--db", str(database), "--partition", "tenant-a",
                        "operation", "register", "echo", "--actor", "a" * size,
                    ])
                    self.assertEqual(result, status, stderr.getvalue())
                    self.assertEqual(database.exists(), status == 0)


class PinCheckPins(unittest.TestCase):
    """p93: `System._pin_checks` survivors (W5 + W5c subject-scoped campaign)."""

    def ledger(self) -> tuple[System, str, str]:
        from cement_runtime import Candidate, CompilePolicy

        directory = tempfile.TemporaryDirectory(prefix="cement-p93-")
        self.addCleanup(directory.cleanup)
        database = str(pathlib.Path(directory.name) / "ledger.db")
        system = System(database)
        system.register_operation("tenant_a", "op", policy=CompilePolicy(2, 1, 0))
        for _ in range(2):
            proposal = system.submit_proposal(
                "tenant_a", "op", {"doc": 1}, candidate=Candidate(output={"f": 1}, provenance={})
            )
            system.review("tenant_a", proposal, reviewer="learning-pass", decision="accept")
        system.compile("tenant_a", "op")
        system.verify_drafts("tenant_a", "op", verified_by="learning-pass")
        manifest = system.inspect_function_promotion("tenant_a", "op")
        promotion = system.promote_function(
            "tenant_a", "op", expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        system.set_switch("tenant_a", "op", mode="pinned", actor="person", function_hash=promotion.function_hash)
        return system, database, promotion.function_hash

    def vector(self, system: System) -> list[tuple[str, bool, str]]:
        resolution = system.resolve("tenant_a", "op", {"doc": 1})
        return [(check.key, check.passed, check.detail) for check in resolution.verification.checks]

    def test_p93_each_pinned_check_names_its_count(self) -> None:
        # `detail="ok" if n == 0 else f"{n} …"` for revoked, suspended and counterexample counts:
        # AddNot, 0 → ±1 and every comparison but `<=` survived, because no test read a detail.
        ok = ("pinned-receipt-rebuilds", True, "ok")
        system, _, _ = self.ledger()
        self.assertEqual(self.vector(system), [
            ok, ("pinned-evidence-unrevoked", True, "ok"),
            ("pinned-members-unsuspended", True, "ok"), ("pinned-no-counterexample", True, "ok"),
        ])
        example = system.examples("tenant_a", "op")[0]["id"]
        system.revoke_example("tenant_a", example, revoked_by="person", reason="wrong")
        self.assertEqual(self.vector(system), [
            ok, ("pinned-evidence-unrevoked", False, "1 member evidence example(s) revoked"),
            ("pinned-members-unsuspended", False, "1 member artifact(s) suspended"),
            ("pinned-no-counterexample", True, "ok"),
        ])
        system, _, _ = self.ledger()
        system.challenge("tenant_a", "op", {"doc": 1}, {"f": 7}, reviewer="person")
        self.assertEqual(self.vector(system), [
            ok, ("pinned-evidence-unrevoked", True, "ok"),
            ("pinned-members-unsuspended", False, "1 member artifact(s) suspended"),
            ("pinned-no-counterexample", False, "1 counterexample(s) on member keys"),
        ])

    def test_p93_a_pin_naming_another_hash_fails_in_both_orders(self) -> None:
        # `reconstruction.function_hash != function_hash` → `<`, `>`, `is` survived: a long-lived
        # `System` reads a pin row forged after it opened (its foreign-key check runs at open).
        import sqlite3

        for forged in ("0" * 64, "f" * 64):
            system, database, _ = self.ledger()
            with contextlib.closing(sqlite3.connect(database)) as raw, raw:
                receipt = raw.execute(
                    "SELECT receipt_id FROM switch_settings ORDER BY sequence DESC LIMIT 1"
                ).fetchone()[0]
                raw.execute(
                    "INSERT INTO switch_settings(id, partition, operation, mode, receipt_id,"
                    " function_hash, set_by, set_at_us) VALUES (?, ?, ?, 'pinned', ?, ?, 'forger', 1)",
                    ("sw_forged", "tenant_a", "op", receipt, forged),
                )
            resolution = system.resolve("tenant_a", "op", {"doc": 1})
            with self.subTest(forged=forged[:4]):
                self.assertIsNone(resolution.match)
                self.assertEqual(
                    self.vector(system)[0],
                    ("pinned-receipt-rebuilds", False, "pinned receipt rebuilds a different function"),
                )


MISS = {"covered": False, "reason": "off", "instruction": "..."}
OTHER = {"document": "PATIENT INTAKE FORM\nName: B\n"}


def _lookup(call_id: str, result: object = MISS, value: object = DOC, **extra: object) -> list[dict[str, Any]]:
    return _call(call_id, "use_learned_function", {"operation": OP, "input": value, **extra}, result)


def _record(call_id: str, result: object = None, value: object = DOC, output: object = PLAN,
            **extra: object) -> list[dict[str, Any]]:
    arguments = {"operation": OP, "input": value, "output": output, **extra}
    return _call(call_id, "record_answer", arguments, {"accepted": True} if result is None else result)


class FilterCapturePins(_Example):
    """p93: `examples/open_webui/cement_filter.py` `Filter._pairs`, `_retain` + `outlet` survivors.

    The capture battery builds bodies from Python literals, whose interned strings let `==` → `is`
    survive, and counts notes without reading them. Open WebUI delivers JSON, and the outlet body of
    `/api/chat/completed` is the client's, so only JSON booleans decide `covered` and `accepted`.
    """

    def _body(self, output: list[dict[str, Any]], *, history: tuple[dict[str, Any], ...] = (),
              between: tuple[dict[str, Any], ...] = (), user: bool = True,
              chat_id: str | None = "chat-1") -> dict[str, Any]:
        question = [{"id": "msg-u", "role": "user", "content": "plan this note"}] if user else []
        answer = {"id": "msg-a", "role": "assistant", "content": "Here is the plan.", "output": output}
        body = {"model": "stub-model", "id": "msg-a", "messages": [*history, *question, *between, answer]}
        if chat_id is not None:
            body["chat_id"] = chat_id
        return json.loads(json.dumps(body))  # as Open WebUI delivers it: no string is interned

    def _pairs(self, output: list[dict[str, Any]], **shape: Any) -> tuple[list[dict[str, Any]], list[str]]:
        return self.filter._pairs(self._body(output, **shape), {})

    def _outlet(self, body: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
        async def emit(event: dict[str, Any]) -> None:
            self.notes.append(event)

        asyncio.run(self.filter.outlet(body, __event_emitter__=emit, __metadata__=metadata))
        return [note["data"]["content"] for note in self.notes]

    def _source_ids(self) -> list[str]:
        with self.system.store.transaction() as connection:
            return [row[0] for row in connection.execute("SELECT source_id FROM proposals ORDER BY id")]

    @staticmethod
    def _expected(use_id: str, record_id: str, value: object = DOC, output: object = PLAN) -> dict[str, Any]:
        digest = canonicalize(value).digest
        provenance = {
            "chat_id": "chat-1", "assistant_message_id": "msg-a", "user_message_id": "msg-u",
            "model": "stub-model", "use_call_id": use_id, "record_call_id": record_id,
            "reply": "Here is the plan.", "reply_truncated": False,
        }
        return {
            "operation": OP, "input": value, "output": output, "input_hash": digest,
            "use_call_id": use_id, "record_call_id": record_id, "provenance": provenance,
            "source_id": f"ward-7:chat-1:msg-u:{digest}",
        }

    def test_p93_only_the_current_answer_counts_bound_to_its_question(self) -> None:
        # `role == "assistant"`, `id == message_id`, `role == "user"` + `name == USE` → `is`, and
        # the orderings over roles + ids: an earlier turn, another role between the question and
        # the answer, or a message without a role must change neither the pairs nor their question.
        earlier = {"id": "msg-0a", "role": "assistant", "content": "earlier",
                   "output": _lookup("h1", value=OTHER) + _record("h2", value=OTHER)}
        history = ({"id": "msg-0", "content": "no role"},
                   {"id": "msg-0u", "role": "user", "content": "plan the earlier note"}, earlier)
        between = ({"id": "msg-s", "role": "system", "content": "a note"}, {"id": "msg-x", "content": "no role"})
        output = _lookup("c1") + _record("c2") + _lookup("c3", value=OTHER) + _record("c4", value=OTHER)
        self.assertEqual(
            self._pairs(output, history=history, between=between),
            ([self._expected("c1", "c2"), self._expected("c3", "c4", OTHER)], []),
        )

    def test_p93_each_defect_note_names_its_call(self) -> None:
        # The battery counted one note per defect; these read it (AddNot on the covered branch,
        # `name == RECORD` → `is`, which drops `output` from what a record call requires).
        covered = {"covered": True, "output": PLAN, "function_hash": "0" * 64}
        self.assertEqual(self._pairs(_lookup("c1", covered) + _record("c2")),
                         ([], ["record_answer call c2 answers a covered request"]))
        no_output = _call("c2", "record_answer", {"operation": OP, "input": DOC}, {"accepted": True})
        self.assertEqual(self._pairs(_lookup("c1") + no_output), ([], [
            "record_answer call c2 is malformed or names a disabled operation",
            "use_learned_function call c1 missed without record_answer",
        ]))

    def test_p93_only_json_booleans_decide_covered_and_accepted(self) -> None:
        # `is True` / `is False` → `==`, orderings and `and` → `or` over the tool results.
        unpaired = ([], ["record_answer call c2 has no matching uncovered call"])
        for covered in (1, 2, 0):
            with self.subTest(covered=covered):
                self.assertEqual(self._pairs(_lookup("c1", {"covered": covered}) + _record("c2")), unpaired)
        with self.subTest(covered="no result"):
            self.assertEqual(self._pairs(_lookup("c1")[:1] + _record("c2")), unpaired)
        refused = ([], ["record_answer call c2 was not accepted",
                        "use_learned_function call c1 missed without record_answer"])
        for accepted in (1, 2, False, 0):
            with self.subTest(accepted=accepted):
                self.assertEqual(self._pairs(_lookup("c1") + _record("c2", {"accepted": accepted})), refused)

    def test_p93_a_chat_or_a_question_without_an_id_retains_nothing(self) -> None:
        # `chat_id is None or user_message_id is None` → `and`: either id missing alone suffices.
        for shape in ({"chat_id": None}, {"user": False}):
            with self.subTest(shape=shape):
                self.assertEqual(self._pairs(_lookup("c1") + _record("c2"), **shape),
                                 ([], ["the chat or its question has no id, so no answer was retained"]))

    def test_p93_extra_arguments_and_an_earlier_malformed_call_keep_the_pair(self) -> None:
        # `required <= arguments.keys()` → `==` and the malformed call's `continue` → `break`.
        malformed = _call("c0", "record_answer", {"operation": [], "input": DOC, "output": PLAN}, {"accepted": True})
        self.assertEqual(
            self._pairs(malformed + _lookup("c1", note="x") + _record("c2", note="x")),
            ([self._expected("c1", "c2")], ["record_answer call c0 is malformed or names a disabled operation"]),
        )

    def test_p93_a_retention_error_names_its_call(self) -> None:
        # `_retain`'s `except CementError` → another class: the note names the call + the error.
        self.filter.valves.operations = f"{OP}\nbilling_codes"
        output = _call("c1", "use_learned_function", {"operation": "billing_codes", "input": DOC}, MISS)
        output += _call("c2", "record_answer", {"operation": "billing_codes", "input": DOC, "output": PLAN},
                        {"accepted": True})
        self.assertEqual(self._outlet(self._body(output), {}), [
            "record_answer call c2 was not retained: operation is not registered in this partition"
        ])

    def test_p93_the_metadata_names_the_question_the_body_lacks(self) -> None:
        # `outlet`'s `__metadata__ or {}` → `and`: the metadata's `user_message_id` then never reads.
        self.assertEqual(self._outlet(self._body(_lookup("c1") + _record("c2"), user=False),
                                      {"user_message_id": "msg-u"}), [])
        self.assertEqual(self._source_ids(), [f"ward-7:chat-1:msg-u:{canonicalize(DOC).digest}"])


class ForgedAbi(metaclass=ForgedEquality):
    """Hashes, compares and prints as the v1 ABI string while its class is no `str`."""

    def __eq__(self, other: object) -> bool:
        return other == PROJECTION_ABI

    def __hash__(self) -> int:
        return hash(PROJECTION_ABI)

    def __str__(self) -> str:
        return PROJECTION_ABI


class ProjectionPins(_ProjectionCase):
    """p93: `projection.py` `parse_program` + `system.py` projection-path survivors."""

    def test_p93_a_forged_abi_string_is_refused_by_its_rule(self) -> None:
        # `type(root["abi"]) is not str` → `!=`: equality can be forged through the metaclass, so
        # only `is not` refuses an object that hashes and compares as the ABI string.
        program = {**_program(self.texts), "abi": ForgedAbi()}
        with self.assertRaises(ValidationError) as raised:
            parse_program(program)
        self.assertEqual(
            str(raised.exception), f"projection abi must be {PROJECTION_ABI!r} or {PROJECTION_ABI_V2!r}"
        )

    def test_p93_the_uniform_check_names_the_program_every_member_projects_with(self) -> None:
        # AddNot on `program.program_hash if program else ''`: no test read the passing detail.
        program = parse_program(self._learn_all())
        checks = {check.key: check for check in self.system.verify_function(PROJECTION_P, PROJECTION_OP).checks}
        self.assertEqual(
            (checks["projection-uniform"].passed, checks["projection-uniform"].detail),
            (True, f"every member projects with {program.program_hash}"),
        )

    def test_p93_set_projection_bounds_its_actor_at_256_utf8_bytes(self) -> None:
        # `_text(actor, "actor", maximum=256)` → 255 / 257; two-byte characters, as p18's pin.
        for text in self.texts:
            self._confirm(text, {"plan": text.splitlines()[0]})
        program = _program(self.texts)
        with self.assertRaises(ValidationError) as raised:
            self.system.set_projection(PROJECTION_P, PROJECTION_OP, program, actor="é" * 128 + "a")
        self.assertEqual(str(raised.exception), "actor must be control-free and at most 256 UTF-8 bytes")
        change = self.system.set_projection(PROJECTION_P, PROJECTION_OP, program, actor="é" * 128)
        self.assertEqual((change["changed"], change["program_hash"]), (True, parse_program(program).program_hash))

    def test_p93_the_case_key_memo_evicts_its_oldest_key_at_its_bound(self) -> None:
        # `len(memo) >= _CASE_KEY_MEMO_MAX` → `>` holds one key past the bound, and → `is` never
        # evicts once the bound leaves CPython's small-int cache (the real bound = 65,536): a
        # bound of 300 keeps identity apart from equality, as L20's smaller one cannot.
        import collections

        import cement_runtime.system as system_module

        program = parse_program(_program(self.texts))
        raws = [canonicalize({"document": f"unrecognized form {number}"}) for number in range(301)]
        calls: collections.Counter[str] = collections.Counter()
        real = system_module.project

        def counted(program: object, value: object) -> object:
            calls[canonicalize(value).digest] += 1  # type: ignore[arg-type]
            return real(program, value)  # type: ignore[arg-type]

        with mock.patch.object(system_module, "_CASE_KEY_MEMO_MAX", 300), mock.patch.object(
            system_module, "project", counted
        ):
            for raw in [*raws, raws[-1], raws[0]]:
                self.system._case_key_text(program, raw.text, raw.digest)
        self.assertEqual((calls[raws[-1].digest], calls[raws[0].digest]), (1, 2))


class EvaluatePins(unittest.TestCase):
    """p93: `function.py` `evaluate` survivors."""

    def test_p93_a_miss_past_every_entry_of_a_large_bundle_is_inert(self) -> None:
        # `index == len(bundle.input_hashes)` → `is` holds only inside CPython's small-int cache:
        # past 256 entries, a digest sorting after the last one indexes past the end.
        from cement_runtime import Candidate, CompilePolicy, evaluate, parse_function

        directory = tempfile.TemporaryDirectory(prefix="cement-p93-")
        self.addCleanup(directory.cleanup)
        system = System(str(pathlib.Path(directory.name) / "ledger.db"))
        system.register_operation("tenant_a", "op", policy=CompilePolicy(2, 1, 0))
        for number in range(257):
            for _ in range(2):
                proposal = system.submit_proposal(
                    "tenant_a", "op", {"n": number}, candidate=Candidate(output={"m": number}, provenance={})
                )
                system.review("tenant_a", proposal, reviewer="learning-pass", decision="accept")
        system.compile("tenant_a", "op")
        system.verify_drafts("tenant_a", "op", verified_by="learning-pass")
        manifest = system.inspect_function_promotion("tenant_a", "op")
        system.promote_function("tenant_a", "op", expected_function_hash=manifest.function_hash,
                                promoted_by="learning-pass")
        verification = system.verify_function("tenant_a", "op")
        bundle = parse_function(verification.document.text, expected_function_hash=verification.function_hash)
        self.assertEqual(len(bundle.input_hashes), 257)
        past = next(canonicalize({"n": n}) for n in range(257, 10_000)
                    if canonicalize({"n": n}).digest > bundle.input_hashes[-1])
        self.assertFalse(evaluate(bundle, input_json=past).matched)
        self.assertEqual(evaluate(bundle, input_json=canonicalize({"n": 7})).output, {"m": 7})


if __name__ == "__main__":
    unittest.main()
