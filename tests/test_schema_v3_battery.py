"""M3.6b battery — schema v3, the single cut, and existing-only construction (p50 + p51).

Contract: `.agent/decisions/m45-contract.md` §1 (S1-S7). S5 (amend v3 in place) is a process rule
graded by the fingerprint pin below; S7 (a program row that does not hash to its key) has no
reader before M4.2, whose battery owns it, since SQLite triggers cannot compute sha256.
"""

from __future__ import annotations

import argparse
import contextlib
from contextlib import closing
import hashlib
import inspect
import io
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import tokenize
import unittest

from cement_runtime import Candidate, CompilePolicy, ConflictError, IntegrityError, System
from cement_runtime.cli import _parser, main
from cement_runtime.store import SCHEMA, SCHEMA_FINGERPRINT, SCHEMA_VERSION, Store

ROOT = pathlib.Path(__file__).resolve().parents[1]
# A v2 revision on `main` forever (the p78 squash): the real v2 package builds the v2 ledger.
V2_REVISION = "1935f68"
P, OP = "tenant_a", "plan"
POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)


def _run(db: str, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["--db", db, "--partition", P, *argv])
    return code, out.getvalue(), err.getvalue()


def _leaves() -> dict[str, argparse.ArgumentParser]:
    found: dict[str, argparse.ArgumentParser] = {}

    def walk(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        if not subs:
            found[" ".join(path)] = parser
            return
        for name, child in subs[0].choices.items():
            walk(child, (*path, name))

    walk(_parser(), ())
    return found


def _minimal_argv(leaf: str, parser: argparse.ArgumentParser) -> list[str]:
    argv = leaf.split()
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        value = "1" if action.type is int else "{}"
        if action.choices:
            value = sorted(action.choices)[0]
        if not action.option_strings:
            argv.append("x" if value == "{}" else value)
        elif action.required:
            argv.extend([action.option_strings[0], value])
    return argv


class _Ledger(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-v3-")
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.db = str(self.root / "ledger.db")


class SchemaIdentityBattery(_Ledger):
    def test_s1_version_three_and_the_fingerprint_bind_the_schema_text(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 3)
        self.assertEqual(SCHEMA_FINGERPRINT, hashlib.sha256(SCHEMA.encode("utf-8")).hexdigest())
        System(self.db)
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(
                connection.execute("SELECT key, value FROM schema_metadata").fetchall(),
                [("schema-v3", SCHEMA_FINGERPRINT)],
            )

    def test_s1_a_real_v2_ledger_refuses_to_open_naming_the_reset(self) -> None:
        archive = subprocess.run(
            ["git", "-C", str(ROOT), "archive", V2_REVISION, "src"],
            check=True,
            capture_output=True,
        ).stdout
        package = self.root / "v2"
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(package, filter="data")
        subprocess.run(
            [sys.executable, "-I", "-c", "import sys; sys.path.insert(0, sys.argv[1]);"
             " from cement_runtime import System; System(sys.argv[2])",
             str(package / "src"), self.db],
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
        before = pathlib.Path(self.db).read_bytes()
        for create in (True, False):
            with self.subTest(create=create), self.assertRaisesRegex(
                IntegrityError, r"database schema 2 is unsupported; expected 3 .*start a new ledger"
            ):
                System(self.db, create=create)
        code, out, err = _run(self.db, "operation", "list")
        self.assertEqual((code, out), (5, ""))
        self.assertIn("start a new ledger", json.loads(err)["message"])
        self.assertEqual(pathlib.Path(self.db).read_bytes(), before)

    def test_s1_an_unhashable_bundle_abi_refuses_as_validation(self) -> None:
        from cement_runtime import ValidationError, parse_function
        from cement_runtime.function import FUNCTION_ABI

        root = {"abi": FUNCTION_ABI, "canonicalizer": "cement-json-v1", "entries": [],
                "function_hash": "0" * 64, "projection": None, "projection_hash": None,
                "scope": {}}
        for abi in ([], {}, [FUNCTION_ABI], 3):
            with self.subTest(abi=abi), self.assertRaisesRegex(ValidationError, "unsupported function ABI"):
                parse_function(json.dumps(dict(root, abi=abi)))

    def test_s1_the_package_version_is_the_cut(self) -> None:
        import tomllib

        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["version"], "0.2.0")


class AppendOnlyBattery(_Ledger):
    def setUp(self) -> None:
        super().setUp()
        self.system = System(self.db)
        self.system.register_operation(P, OP, policy=POLICY)
        self.system.register_operation(P, "other", policy=POLICY)
        for _ in range(2):
            proposal = self.system.submit_proposal(
                P, OP, {"doc": 1}, candidate=Candidate(output={"f": 1}, provenance={})
            )
            self.system.review(P, proposal, reviewer="learning-pass", decision="accept")
        self.system.compile(P, OP)
        self.assertTrue(self.system.verify_drafts(P, OP, verified_by="learning-pass").passed)
        manifest = self.system.inspect_function_promotion(P, OP)
        self.system.promote_function(
            P, OP, expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
        )
        with self.system.store.transaction() as connection:
            row = connection.execute("SELECT id, function_hash FROM function_receipts").fetchone()
        self.receipt, self.function_hash = str(row["id"]), str(row["function_hash"])

    def _insert(self, sql: str, values: tuple[object, ...]) -> None:
        with self.system.store.transaction(write=True) as connection:
            connection.execute(sql, values)

    def _switch(self, mode: str, receipt: str | None, digest: str | None, operation: str = OP) -> None:
        self._insert(
            """
            INSERT INTO switch_settings(
                id, partition, operation, mode, receipt_id, function_hash, set_by, set_at_us
            ) VALUES (?, ?, ?, ?, ?, ?, 'person', 1)
            """,
            (f"sw_{mode}_{receipt}_{digest}_{operation}", P, operation, mode, receipt, digest),
        )

    def test_s2_each_new_table_refuses_update_and_delete_on_a_present_row(self) -> None:
        self._insert(
            "INSERT INTO projection_programs(program_hash, abi, program_json) VALUES (?, ?, ?)",
            ("a" * 64, "cement-projection-v1", "{}"),
        )
        self._insert(
            """
            INSERT INTO projection_settings(
                id, partition, operation, operation_revision, program_hash, set_by, set_at_us
            ) VALUES ('ps_1', ?, ?, 1, ?, 'learning-pass', 1)
            """,
            (P, OP, "a" * 64),
        )
        self._switch("off", None, None)
        expected = {
            "projection_programs": "cement-projection-v1",
            "projection_settings": "learning-pass",
            "switch_settings": "person",
        }
        for table, column in (
            ("projection_programs", "abi"),
            ("projection_settings", "set_by"),
            ("switch_settings", "set_by"),
        ):
            with self.subTest(table=table):
                with self.system.store.transaction() as connection:
                    count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                self.assertEqual(count, 1)
                for statement in (f"UPDATE {table} SET {column} = 'x'", f"DELETE FROM {table}"):
                    with self.assertRaises(IntegrityError):
                        self._insert(statement, ())
                with self.system.store.transaction() as connection:
                    self.assertEqual(
                        connection.execute(f"SELECT {column} FROM {table}").fetchall()[0][0],
                        expected[table],
                    )

    def test_s3_the_switch_check_refuses_every_half_populated_row(self) -> None:
        r, h = self.receipt, self.function_hash
        for mode, receipt, digest in (
            ("off", r, None), ("off", None, h), ("follow", r, None),
            ("follow", None, h), ("pinned", r, None), ("pinned", None, h),
            ("off", r, h), ("follow", r, h), ("pinned", None, None), ("on", None, None),
        ):
            with self.subTest(mode=mode, receipt=receipt, digest=digest), self.assertRaises(
                IntegrityError
            ):
                self._switch(mode, receipt, digest)
        for mode, receipt, digest in (("off", None, None), ("follow", None, None), ("pinned", r, h)):
            with self.subTest(accepted=mode):
                self._switch(mode, receipt, digest)
        with self.system.store.transaction() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM switch_settings").fetchone()[0], 3)

    def test_s3_a_pin_must_name_one_receipt_of_its_own_operation(self) -> None:
        with self.assertRaises(IntegrityError):
            self._switch("pinned", self.receipt, "0" * 64)
        with self.assertRaises(IntegrityError):
            self._switch("pinned", "fpr_" + "0" * 32, self.function_hash)
        with self.assertRaises(IntegrityError):
            self._switch("pinned", self.receipt, self.function_hash, operation="other")
        self._switch("pinned", self.receipt, self.function_hash)

    def test_s2_supersession_columns_bind_origin_and_supersede_each_example_once(self) -> None:
        with self.system.store.transaction() as connection:
            row = dict(connection.execute("SELECT * FROM examples ORDER BY sequence LIMIT 1").fetchone())
        columns = [key for key in row if key != "sequence"]

        def insert(suffix: str, origin: str, supersedes: str | None) -> None:
            values = dict(row, id=f"ex_{suffix}", receipt_hash=suffix * 64, origin=origin,
                          supersedes_example_id=supersedes, proposal_id=None)
            self._insert(
                f"INSERT INTO examples({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                tuple(values[key] for key in columns),
            )

        for suffix, origin, supersedes in (("a", "superseded", None), ("b", "accepted", row["id"])):
            with self.subTest(origin=origin, supersedes=supersedes), self.assertRaises(IntegrityError):
                insert(suffix, origin, supersedes)
        insert("c", "superseded", row["id"])
        with self.assertRaises(IntegrityError):
            insert("d", "superseded", row["id"])
        with self.system.store.transaction() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT id FROM examples WHERE supersedes_example_id = ?", (row["id"],)
                ).fetchall()[0][0],
                "ex_c",
            )


class RequestsResidueBattery(_Ledger):
    def test_s4_no_requests_table_and_no_query_names_one(self) -> None:
        System(self.db)
        with closing(sqlite3.connect(self.db)) as connection:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_schema")}
        self.assertNotIn("requests", names)
        self.assertFalse({name for name in names if name.startswith("requests")})
        sql = re.compile(r"(?i)\b(from|join|into|update|table|exists|on)\s+requests\b")
        survivors = {
            ("json_value.py", '"""Conservative, versioned JSON boundary used by requests and artifacts."""'),
        }
        hits: set[tuple[str, str]] = set()
        for path in sorted((ROOT / "src/cement_runtime").glob("*.py")):
            with path.open("rb") as handle:
                for token in tokenize.tokenize(handle.readline):
                    if token.type == tokenize.STRING and sql.search(token.string):
                        self.fail(f"{path.name}:{token.start[0]} names the requests table")
                    if token.type in (tokenize.NAME, tokenize.STRING) and re.search(
                        r"\brequests?_(id|status)\b|\brequests\b", token.string
                    ):
                        hits.add((path.name, token.string))
        self.assertEqual(hits, survivors, sorted(hits - survivors))


class SourceIdBattery(_Ledger):
    def setUp(self) -> None:
        super().setUp()
        self.system = System(self.db)
        for partition in (P, "tenant_b"):
            for operation in (OP, "other"):
                self.system.register_operation(partition, operation, policy=POLICY)

    def _submit(self, partition: str, operation: str, source_id: str | None) -> str:
        return self.system.submit_proposal(
            partition,
            operation,
            {"doc": 1},
            candidate=Candidate(output={"f": 1}, provenance={}),
            source_id=source_id,
        )

    def _counts(self) -> tuple[int, int]:
        with self.system.store.transaction() as connection:
            return (
                connection.execute("SELECT COUNT(*) FROM proposals").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            )

    def test_s6_a_repeated_source_id_is_a_conflict_naming_the_first_proposal(self) -> None:
        first = self._submit(P, OP, "deploy:chat-1:msg-1:abc")
        before = self._counts()
        with self.assertRaises(ConflictError) as caught:
            self._submit(P, OP, "deploy:chat-1:msg-1:abc")
        self.assertIn(first, str(caught.exception))
        self.assertEqual(self._counts(), before)
        self._submit(P, "other", "deploy:chat-1:msg-1:abc")
        self._submit("tenant_b", OP, "deploy:chat-1:msg-1:abc")
        self._submit(P, OP, None)
        self._submit(P, OP, None)
        self.assertEqual(self._counts(), (before[0] + 4, before[1] + 4))

    def test_s6_the_cli_maps_the_repeat_to_exit_four_with_empty_stdout(self) -> None:
        submission = json.dumps(
            {"input": {"doc": 1}, "output": {"f": 1}, "provenance": {}, "source_id": "s-1"}
        )
        argv = ("proposal", "submit", OP, "--submission", submission)
        self.assertEqual(_run(self.db, *argv)[0], 0)
        code, out, err = _run(self.db, *argv)
        self.assertEqual((code, out, json.loads(err)["error"]), (4, "", "conflict"))

    def test_s6_the_source_id_bound_is_an_adjacent_pair_on_both_channels(self) -> None:
        from cement_runtime import ValidationError
        from cement_runtime.cli import SUBMISSION_MAX_BYTES
        from cement_runtime.system import SOURCE_ID_MAX_BYTES

        widest = "\U0001f600" * (SOURCE_ID_MAX_BYTES // 4)
        self._submit(P, OP, widest)
        with self.assertRaises(ValidationError):
            self._submit(P, OP, widest + "a")
        submission = {"input": {"doc": 2}, "output": {"f": 1}, "provenance": {}}
        for value, code in ((widest[:-1] + "b", 0), (widest + "a", 2), (5, 2), ("", 2)):
            with self.subTest(length=len(str(value)), kind=type(value).__name__):
                text = json.dumps({**submission, "source_id": value})
                self.assertLessEqual(len(text.encode()), SUBMISSION_MAX_BYTES)
                self.assertEqual(_run(self.db, "proposal", "submit", OP, "--submission", text)[0], code)


class ExistingOnlyBattery(_Ledger):
    """p50 + p51: only `operation register` may create a ledger; nothing else writes one."""

    def test_p50_the_constructors_take_create_keyword_only_with_true_default(self) -> None:
        for target in (System, Store):
            parameter = inspect.signature(target).parameters["create"]
            self.assertEqual(
                (parameter.kind, parameter.default), (inspect.Parameter.KEYWORD_ONLY, True)
            )

    def test_p50_an_existing_only_open_of_a_missing_path_creates_nothing(self) -> None:
        with self.assertRaisesRegex(IntegrityError, "ledger file is missing or unreadable"):
            System(self.db, create=False)
        self.assertEqual(list(self.root.iterdir()), [])
        pathlib.Path(self.db).write_bytes(b"")
        with self.assertRaisesRegex(IntegrityError, "not an initialized Cement ledger"):
            System(self.db, create=False)
        self.assertEqual(pathlib.Path(self.db).read_bytes(), b"")

    def test_p50_an_existing_only_open_writes_no_byte_and_reads_from_a_read_only_directory(
        self,
    ) -> None:
        directory = self.root / "ro"
        directory.mkdir()
        db = str(directory / "ledger.db")
        System(db).register_operation(P, OP, policy=POLICY)
        before = pathlib.Path(db).read_bytes()
        directory.chmod(0o555)
        self.addCleanup(directory.chmod, 0o755)
        system = System(db, create=False)
        self.assertEqual([row["name"] for row in system.operations(P)], [OP])
        self.assertEqual(_run(db, "operation", "list")[0], 0)
        self.assertEqual(sorted(path.name for path in directory.iterdir()), ["ledger.db"])
        self.assertEqual(pathlib.Path(db).read_bytes(), before)

    def test_p51_every_leaf_but_register_exits_five_on_an_absent_ledger_creating_nothing(
        self,
    ) -> None:
        leaves = _leaves()
        exempt = {"operation register", "function eval"}
        self.assertLessEqual(exempt, set(leaves))
        checked = 0
        for leaf, parser in sorted(leaves.items()):
            if leaf in exempt:
                continue
            with self.subTest(leaf=leaf):
                code, out, err = _run(self.db, *_minimal_argv(leaf, parser))
                self.assertEqual((code, out), (5, ""), err)
                self.assertEqual(json.loads(err)["message"], "ledger file is missing or unreadable")
                self.assertEqual(list(self.root.iterdir()), [])
                checked += 1
        self.assertEqual(checked, len(leaves) - len(exempt))

    def test_p51_register_grades_every_value_before_it_creates_the_ledger(self) -> None:
        for argv in (
            ["--partition", "!", "operation", "register", OP],
            ["--partition", P, "operation", "register", "!"],
            ["--partition", P, "operation", "register", OP, "--actor", ""],
            ["--partition", P, "operation", "register", OP, "--min-confirmations", "-1"],
            ["--partition", P, "operation", "register", OP, "--min-span-seconds", "-1"],
        ):
            with self.subTest(argv=argv):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = main(["--db", self.db, *argv])
                self.assertEqual((code, out.getvalue()), (2, ""))
                self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(_run(self.db, "operation", "register", OP)[0], 0)
        self.assertEqual([path.name for path in self.root.iterdir()], ["ledger.db"])


class ReceiptFeedPlanBattery(_Ledger):
    """p04: a receipt page reads `function_receipts_feed` in order and stops near its size.

    The SQL graded is the statement `System.function_receipts` executes (a trace callback, bound
    values expanded), so the pin follows the shipped query rather than a retyped copy.
    """

    def _statement(self, system: System, **cursor: int) -> str:
        from unittest import mock

        seen: list[str] = []
        connect = Store._connect

        def traced(store: Store, *, read_only: bool = False) -> sqlite3.Connection:
            connection = connect(store, read_only=read_only)
            connection.set_trace_callback(seen.append)
            return connection

        with mock.patch.object(Store, "_connect", traced), contextlib.suppress(IntegrityError):
            # Fabricated rows fail receipt validation on read, after the page query ran.
            system.function_receipts("tenant_a", "plan", limit=3, **cursor)
        (statement,) = [sql for sql in seen if re.match(r"\s*SELECT \* FROM function_receipts", sql)]
        return statement

    def test_p04_receipt_pages_read_the_feed_index_without_a_temp_sort(self) -> None:
        system = System(self.db)
        with closing(sqlite3.connect(self.db)) as connection:
            connection.executemany(
                """
                INSERT INTO function_receipts(
                    id, partition, operation, operation_revision, policy_hash, function_hash,
                    membership_hash, member_count, candidate_artifact_ids_hash, candidate_count,
                    retired_artifact_ids_hash, retired_count, promoted_by, promoted_at_us,
                    receipt_hash
                ) VALUES (?, 'tenant_a', ?, ?, 'p', 'f', 'm', 0, 'c', 0, 'r', 0, 'x', ?, ?)
                """,
                [
                    (f"fr_{n}", "plan" if n % 2 else "other", 1 + n % 3, n, f"h{n}")
                    for n in range(1, 2003)
                ],
            )
            connection.commit()
        for label, cursor in (("default", {}), ("cursor", {"before_sequence": 1501})):
            with self.subTest(page=label):
                statement = self._statement(system, **cursor)
                with closing(sqlite3.connect(self.db)) as connection:
                    plan = " | ".join(
                        str(row[3]) for row in connection.execute(f"EXPLAIN QUERY PLAN {statement}")
                    )
                    steps = [0]

                    def step() -> int:
                        steps[0] += 1
                        return 0

                    connection.set_progress_handler(step, 1)
                    self.assertEqual(len(connection.execute(statement).fetchall()), 4)
                    page = steps[0]
                    steps[0] = 0
                    connection.execute(re.sub(r"LIMIT \d+", "LIMIT 100000", statement)).fetchall()
                    full = steps[0]
                self.assertIn("function_receipts_feed", plan)
                self.assertNotIn("TEMP B-TREE", plan)
                # 1,001 matching rows: a page of 4 must cost a small fraction of reading them all.
                self.assertLess(page * 20, full, (page, full))


if __name__ == "__main__":
    unittest.main()
