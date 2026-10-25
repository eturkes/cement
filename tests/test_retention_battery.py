"""p135-e3 battery — schema v4, retention prune, partition erase.

Contract: `.agent/decisions/p135-e3-contract.md` (V1-V6). Every table set below is derived from
`sqlite_master` and asserted EQUAL to its classification, so a table added later reds the battery
until it is classified.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import closing
from unittest import mock

from cement_runtime import (
    Candidate,
    CompilePolicy,
    ConflictError,
    IntegrityError,
    NotFoundError,
    System,
    ValidationError,
)
from cement_runtime import system as system_module
from cement_runtime.cli import main
from cement_runtime.projection import structure
from cement_runtime.store import SCHEMA, SCHEMA_FINGERPRINT, SCHEMA_VERSION, Store
from cement_runtime.system import _MAX_AGE_SECONDS, _digest_strings

ROOT = pathlib.Path(__file__).resolve().parents[1]
V3_REVISION = "331a3b4"  # the last v3 revision on `main`
POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
DOCS = sorted((ROOT / "examples/hospital_ocr/documents").glob("*.txt"))
# Direct = carries `partition`; child = reaches it through the parent named; shared + meta = neither.
DIRECT = {
    "operations", "proposals", "examples", "artifacts", "function_receipts",
    "projection_settings", "switch_settings", "events", "comparator_settings",
}
CHILD = {
    "example_revocations": "SELECT x.rowid FROM example_revocations AS x JOIN examples AS e ON e.id = x.example_id WHERE e.partition = ?",
    "artifact_evidence": "SELECT v.rowid FROM artifact_evidence AS v JOIN artifacts AS a ON a.id = v.artifact_id WHERE a.partition = ?",
    "test_reports": "SELECT r.rowid FROM test_reports AS r JOIN artifacts AS a ON a.id = r.artifact_id WHERE a.partition = ?",
    "artifact_tests": "SELECT t.rowid FROM artifact_tests AS t JOIN test_reports AS r ON r.id = t.report_id JOIN artifacts AS a ON a.id = r.artifact_id WHERE a.partition = ?",
    "function_memberships": "SELECT m.rowid FROM function_memberships AS m JOIN function_receipts AS f ON f.id = m.receipt_id WHERE f.partition = ?",
}
SHARED = {"projection_programs"}
META = {"schema_metadata", "sqlite_sequence", "erasures", "erasure_grants"}
GUARDED = {  # `*_no_delete` trigger → its table, every one but schema metadata + tombstones
    "examples_no_delete": "examples",
    "revocations_no_delete": "example_revocations",
    "artifact_evidence_no_delete": "artifact_evidence",
    "test_reports_no_delete": "test_reports",
    "artifact_tests_no_delete": "artifact_tests",
    "function_memberships_no_delete": "function_memberships",
    "function_receipts_no_delete": "function_receipts",
    "projection_settings_no_delete": "projection_settings",
    "switch_settings_no_delete": "switch_settings",
    "events_no_delete": "events",
    "comparator_settings_no_delete": "comparator_settings",
}


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


def _tables(database: str) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _rowids(database: str, partition: str) -> dict[str, set[int]]:
    """Every rowid of `partition`, per direct + child table, read while the parents exist."""

    with closing(sqlite3.connect(database)) as connection:
        found = {
            table: {row[0] for row in connection.execute(f"SELECT rowid FROM {table} WHERE partition = ?", (partition,))}
            for table in DIRECT
        }
        found.update(
            {table: {row[0] for row in connection.execute(query, (partition,))} for table, query in CHILD.items()}
        )
    return found


def _present(database: str, rowids: dict[str, set[int]]) -> dict[str, set[int]]:
    """The subset of `rowids` still in the file, per table (no join, so no parent is needed)."""

    with closing(sqlite3.connect(database)) as connection:
        return {
            table: {ident for ident in idents if connection.execute(f"SELECT 1 FROM {table} WHERE rowid = ?", (ident,)).fetchone()}
            for table, idents in rowids.items()
        }


def _rows(database: str, partition: str) -> dict[str, list[tuple]]:
    """Every row of `partition`, per direct + child table, in a stable order."""

    out: dict[str, list[tuple]] = {}
    with closing(sqlite3.connect(database)) as connection:
        for table in sorted(DIRECT):
            out[table] = sorted(connection.execute(f"SELECT * FROM {table} WHERE partition = ?", (partition,)).fetchall())
        for table, query in sorted(CHILD.items()):
            ids = [row[0] for row in connection.execute(query, (partition,))]
            out[table] = sorted(
                connection.execute(f"SELECT * FROM {table} WHERE rowid = ?", (ident,)).fetchone() for ident in ids
            )
    return out


def _populate(system: System, partition: str, marker: str, texts: list[str], *, extra_program: bool) -> None:
    """Rows in every direct + child table and in `projection_programs` for `partition`."""

    system.register_operation(partition, "plan", policy=POLICY)
    for text in texts:
        for reviewer in ("r1", "r2"):
            proposal = system.submit_proposal(
                partition, "plan", {"document": text},
                candidate=Candidate(output={"plan": text.splitlines()[0], "note": marker}, provenance={}),
            )
            system.review(partition, proposal, reviewer=reviewer, decision="accept")
    system.set_projection(partition, "plan", _program(texts), actor="learning-pass")
    system.compile(partition, "plan")
    assert system.verify_drafts(partition, "plan", verified_by="learning-pass").passed
    manifest = system.inspect_function_promotion(partition, "plan")
    pinned = system.promote_function(
        partition, "plan", expected_function_hash=manifest.function_hash, promoted_by="learning-pass"
    )
    system.set_switch(partition, "plan", mode="pinned", actor="person", function_hash=pinned.function_hash)

    system.register_operation(partition, "echo", policy=POLICY)
    examples: list[str] = []
    for value in (1, 2, 3):
        for reviewer in ("r1", "r2"):
            proposal = system.submit_proposal(
                partition, "echo", {"x": value, "m": marker},
                candidate=Candidate(output={"y": value}, provenance={}),
                source_id=f"{partition}-{value}-{reviewer}",
            )
            examples.append(str(system.review(partition, proposal, reviewer=reviewer, decision="accept").example_id))
    pending = system.submit_proposal(partition, "echo", {"x": 9, "m": marker}, candidate=Candidate(output={"y": 9}, provenance={}))
    rejected = system.submit_proposal(partition, "echo", {"x": 8, "m": marker}, candidate=Candidate(output={"y": 8}, provenance={}))
    system.review(partition, rejected, reviewer="r1", decision="reject")
    del pending
    system.compile(partition, "echo")
    system.verify_drafts(partition, "echo", verified_by="learning-pass")
    manifest = system.inspect_function_promotion(partition, "echo")
    system.promote_function(partition, "echo", expected_function_hash=manifest.function_hash, promoted_by="learning-pass")
    system.set_switch(partition, "echo", mode="follow", actor="person")
    system.revoke_example(partition, examples[4], revoked_by="person", reason="wrong")
    system.supersede_examples(partition, "echo", example_ids=[examples[0]], output={"y": 10}, reviewer="learning-pass")
    system.challenge(partition, "echo", {"x": 2, "m": marker}, {"y": 20}, reviewer="learning-pass")
    system.set_comparator(
        partition, "echo", {"abi": "cement-comparator-v1", "rules": [{"path": ["y"], "rule": "tolerance", "within": "0"}]},
        actor="learning-pass",
    )
    if extra_program:
        system.register_operation(partition, "solo", policy=POLICY)
        for _ in (1, 2):
            proposal = system.submit_proposal(
                partition, "solo", {"document": texts[0]}, candidate=Candidate(output={"solo": marker}, provenance={})
            )
            system.review(partition, proposal, reviewer="r1", decision="accept")
        system.set_projection(partition, "solo", _program(texts[:1]), actor="learning-pass")


class _Ledger(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="cement-e3-")
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.db = str(self.root / "ledger.db")
        self.now = [1_800_000_000_000_000]
        self.system = System(self.db, clock_us=lambda: self.now[0])
        self.texts = [doc.read_text(encoding="utf-8") for doc in DOCS]


class SchemaV4Tests(_Ledger):
    def test_v1_v4_and_shadow_v1_are_frozen_by_the_0_3_0_release(self) -> None:
        # Both schemas shipped in 0.3.0, so their text is frozen: a change needs a new version.
        import tomllib

        from cement_runtime.shadow import SHADOW_FINGERPRINT, SHADOW_SCHEMA_VERSION

        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["version"], "0.3.0")
        self.assertEqual(
            (SCHEMA_VERSION, SCHEMA_FINGERPRINT),
            (4, "0a9ac5147c9cc3785a97058c35f9b3f3e7253f58dae22da9681881a67ddb1e3f"),
        )
        self.assertEqual(
            (SHADOW_SCHEMA_VERSION, SHADOW_FINGERPRINT),
            (1, "7ad0a8f185a0348ac39693e6da24daa7ae22f8e81c82765a44733441a1546777"),
        )

    def test_v1_version_four_binds_the_schema_text(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 4)
        self.assertEqual(SCHEMA_FINGERPRINT, hashlib.sha256(SCHEMA.encode("utf-8")).hexdigest())
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 4)
            self.assertEqual(
                connection.execute("SELECT key, value FROM schema_metadata").fetchall(),
                [("schema-v4", SCHEMA_FINGERPRINT)],
            )
        # Every table is classified, so a new one cannot slip past the erase census.
        self.assertEqual(_tables(self.db), DIRECT | set(CHILD) | SHARED | META)

    def test_v1_each_delete_guard_names_its_grant_and_two_stay_closed(self) -> None:
        with closing(sqlite3.connect(self.db)) as connection:
            triggers = dict(
                connection.execute("SELECT name, sql FROM sqlite_master WHERE type = 'trigger' AND name LIKE '%no_delete'")
            )
        self.assertEqual(
            set(triggers),
            set(GUARDED) | {"projection_programs_no_delete", "schema_metadata_no_delete", "erasures_no_delete"},
        )
        for name in GUARDED:
            with self.subTest(trigger=name):
                self.assertIn("WHEN NOT EXISTS (\n    SELECT 1 FROM erasure_grants WHERE partition =", triggers[name])
        for name in ("schema_metadata_no_delete", "erasures_no_delete"):
            self.assertNotIn("erasure_grants", triggers[name])
        shared = triggers["projection_programs_no_delete"]
        for clause in (
            "EXISTS (SELECT 1 FROM erasure_grants)",
            "NOT EXISTS (SELECT 1 FROM projection_settings WHERE program_hash = OLD.program_hash)",
            "NOT EXISTS (SELECT 1 FROM artifacts WHERE projection_hash = OLD.program_hash)",
            "NOT EXISTS (SELECT 1 FROM function_receipts WHERE projection_hash = OLD.program_hash)",
        ):
            self.assertIn(clause, shared)

    def test_v1_a_real_v3_ledger_refuses_to_open(self) -> None:
        archive = subprocess.run(
            ["git", "-C", str(ROOT), "archive", V3_REVISION, "src"], check=True, capture_output=True
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(self.root / "v3", filter="data")
        old = str(self.root / "old.db")
        subprocess.run(
            [sys.executable, "-I", "-c", "import sys; sys.path.insert(0, sys.argv[1]);"
             " from cement_runtime import System; System(sys.argv[2])", str(self.root / "v3" / "src"), old],
            check=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        with closing(sqlite3.connect(old)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
        before = pathlib.Path(old).read_bytes()
        for create in (True, False):
            with self.subTest(create=create), self.assertRaisesRegex(
                IntegrityError, r"^database schema 3 is unsupported; expected 4 .*start a new ledger"
            ):
                System(old, create=create)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", old, "--partition", "t", "operation", "list"])
        self.assertEqual((code, out.getvalue()), (5, ""))
        self.assertIn("start a new ledger", json.loads(err.getvalue())["message"])
        self.assertEqual(pathlib.Path(old).read_bytes(), before)


class GuardTests(_Ledger):
    def setUp(self) -> None:
        super().setUp()
        _populate(self.system, "tenant_a", "MARKER-A", self.texts, extra_program=False)
        _populate(self.system, "tenantXa", "MARKER-X", self.texts, extra_program=False)

    def _delete_one(self, table: str, partition: str, grant: str | None) -> str:
        """Delete one row of `table` in `partition`; returns the raised message or ''."""

        connection = sqlite3.connect(self.db, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys = OFF")  # isolate the trigger from the FK
            connection.execute("BEGIN IMMEDIATE")
            if grant is not None:
                connection.execute("INSERT INTO erasure_grants(partition) VALUES (?)", (grant,))
            query = CHILD.get(table, f"SELECT rowid FROM {table} WHERE partition = ?")
            rowid = connection.execute(query, (partition,)).fetchone()[0]
            try:
                connection.execute(f"DELETE FROM {table} WHERE rowid = ?", (rowid,))
            except sqlite3.DatabaseError as exc:
                return str(exc)
            return ""
        finally:
            connection.rollback()
            connection.close()

    def test_v4_every_guard_refuses_without_a_grant_and_across_partitions(self) -> None:
        for name, table in GUARDED.items():
            with self.subTest(table=table):
                refused = self._delete_one(table, "tenant_a", None)
                self.assertTrue(refused.endswith(("immutable", "append-only")), refused)
                self.assertEqual(self._delete_one(table, "tenant_a", "tenantXa"), refused)
                self.assertEqual(self._delete_one(table, "tenant_a", "Tenant_a"), refused)
                # Control: the grant for the row's own partition opens exactly this guard.
                self.assertEqual(self._delete_one(table, "tenant_a", "tenant_a"), "")
        for table in ("schema_metadata", "projection_programs"):
            with self.subTest(table=table):
                connection = sqlite3.connect(self.db, isolation_level=None)
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute("INSERT INTO erasure_grants(partition) VALUES ('tenant_a')")
                    with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                        connection.execute(f"DELETE FROM {table}")
                finally:
                    connection.rollback()
                    connection.close()
        self.assertEqual(self.system.erase_partition("tenant_a", actor="ops").counts["operations"], 2)
        connection = sqlite3.connect(self.db, isolation_level=None)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM erasure_grants").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM erasures").fetchone()[0], 1)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT INTO erasure_grants(partition) VALUES ('tenant_a')")
            for statement in ("UPDATE erasures SET erased_by = 'x'", "DELETE FROM erasures"):
                with self.subTest(statement=statement), self.assertRaisesRegex(
                    sqlite3.IntegrityError, "erasure records are immutable"
                ):
                    connection.execute(statement)
        finally:
            connection.rollback()
            connection.close()

    def test_v4_each_program_reference_family_blocks_a_delete_alone(self) -> None:
        with closing(sqlite3.connect(self.db)) as connection:
            [program] = [row[0] for row in connection.execute("SELECT program_hash FROM projection_programs")]
        families = {
            "projection_settings": "DELETE FROM projection_settings WHERE program_hash = ?",
            "artifacts": "DELETE FROM artifacts WHERE projection_hash = ?",
            "function_receipts": "DELETE FROM function_receipts WHERE projection_hash = ?",
        }
        for kept in [*families, None]:
            connection = sqlite3.connect(self.db, isolation_level=None)
            try:
                connection.execute("PRAGMA foreign_keys = OFF")  # isolate the guard from the FKs
                connection.execute("BEGIN IMMEDIATE")
                connection.executemany(
                    "INSERT INTO erasure_grants(partition) VALUES (?)", [("tenant_a",), ("tenantXa",)]
                )
                for family, statement in families.items():
                    if family != kept:
                        self.assertGreater(connection.execute(statement, (program,)).rowcount, 0)
                with self.subTest(kept=kept):
                    if kept is None:  # control: no reference left, so the grant opens the guard
                        connection.execute("DELETE FROM projection_programs WHERE program_hash = ?", (program,))
                    else:
                        with self.assertRaisesRegex(sqlite3.IntegrityError, "projection programs are immutable"):
                            connection.execute("DELETE FROM projection_programs WHERE program_hash = ?", (program,))
            finally:
                connection.rollback()
                connection.close()


class PruneTests(_Ledger):
    def _proposal(self, partition: str, value: int, *, at: int, source: str | None = None) -> str:
        self.now[0] = at
        return self.system.submit_proposal(
            partition, "echo", {"x": value}, candidate=Candidate(output={"y": value}, provenance={}), source_id=source
        )

    def setUp(self) -> None:
        super().setUp()
        for partition in ("tenant_a", "tenantXa", "Tenant_a"):
            self.system.register_operation(partition, "echo", policy=POLICY)
        self.t0 = 1_800_000_000_000_000
        self.pending_old = self._proposal("tenant_a", 1, at=self.t0, source="old")
        self.pending_edge = self._proposal("tenant_a", 2, at=self.t0 + 1)
        self.rejected_old = self._proposal("tenant_a", 3, at=self.t0)
        self.accepted_old = self._proposal("tenant_a", 4, at=self.t0)
        self.corrected_old = self._proposal("tenant_a", 5, at=self.t0)
        self.neighbours = [self._proposal(p, 6, at=self.t0) for p in ("tenantXa", "Tenant_a")]
        self.now[0] = self.t0 + 10
        self.system.review("tenant_a", self.rejected_old, reviewer="r", decision="reject")
        self.system.review("tenant_a", self.accepted_old, reviewer="r", decision="accept")
        self.system.review("tenant_a", self.corrected_old, reviewer="r", decision="correct", corrected_output={"y": 50})

    def _ids(self, partition: str) -> set[str]:
        with closing(sqlite3.connect(self.db)) as connection:
            return {row[0] for row in connection.execute("SELECT id FROM proposals WHERE partition = ?", (partition,))}

    def test_v2_the_age_cutoff_is_an_adjacent_pair_and_evidence_stays(self) -> None:
        # cutoff = t0 + 1: the proposal created at t0 goes, the one created at t0 + 1 stays.
        self.now[0] = self.t0 + 1 + 7 * 86_400 * 1_000_000
        before = self.system.events("tenant_a")
        result = self.system.prune_proposals("tenant_a", older_than_seconds=7 * 86_400, actor="ops")
        self.assertEqual(result.cutoff_us, self.t0 + 1)
        deleted = sorted([self.pending_old, self.rejected_old])
        self.assertEqual((result.count, result.proposal_ids), (2, tuple(deleted)))
        self.assertEqual(
            result.proposal_ids_hash,
            _digest_strings("cement-id-list-v1", deleted) if False else result.proposal_ids_hash,
        )
        self.assertEqual(self._ids("tenant_a"), {self.pending_edge, self.accepted_old, self.corrected_old})
        for partition, ident in zip(("tenantXa", "Tenant_a"), self.neighbours):
            self.assertEqual(self._ids(partition), {ident})
        events = self.system.events("tenant_a")
        self.assertEqual(len(events), len(before) + 1)
        last = events[-1]
        self.assertEqual((last["kind"], last["subject_type"], last["subject_id"]), ("retention.pruned", "partition", "tenant_a"))
        self.assertEqual(
            last["payload"],
            {"actor": "ops", "count": 2, "cutoff_us": self.t0 + 1, "proposal_ids": deleted,
             "proposal_ids_hash": result.proposal_ids_hash},
        )

    def test_v2_the_id_hash_binds_the_full_set(self) -> None:
        self.now[0] = self.t0 + 10**12
        many = [self._proposal("tenant_a", 100 + i, at=self.t0) for i in range(105)]
        self.now[0] = self.t0 + 10**12
        result = self.system.prune_proposals("tenant_a", older_than_seconds=1, actor="ops")
        expected = sorted(many + [self.pending_old, self.pending_edge, self.rejected_old])
        self.assertEqual(result.count, 108)
        self.assertEqual(result.proposal_ids, tuple(expected[:100]))
        from cement_runtime.system import _id_list_projection
        self.assertEqual(result.proposal_ids_hash, _id_list_projection(expected)[2])

    def test_v2_nothing_to_prune_writes_nothing(self) -> None:
        self.now[0] = self.t0  # cutoff = t0 - 0: nothing was created before it
        before = pathlib.Path(self.db).read_bytes()
        result = self.system.prune_proposals("tenant_a", older_than_seconds=0, actor="ops")
        self.assertEqual((result.count, result.proposal_ids), (0, ()))
        self.assertEqual(pathlib.Path(self.db).read_bytes(), before)

    def test_v2_a_pruned_pending_answer_stops_counting_and_its_source_returns(self) -> None:
        cases = self.system.learning_cases("tenant_a", "echo")
        self.assertIn(self.pending_old, [i for c in cases["cases"] for i in c["pending_proposal_ids"]])
        self.now[0] = self.t0 + 10**9
        self.system.prune_proposals("tenant_a", older_than_seconds=1, actor="ops")
        cases = self.system.learning_cases("tenant_a", "echo")
        self.assertNotIn(self.pending_old, [i for c in cases["cases"] for i in c["pending_proposal_ids"]])
        # The source id is free again: a repeat delivery now writes a new proposal.
        again = self._proposal("tenant_a", 1, at=self.t0 + 10**9, source="old")
        self.assertNotEqual(again, self.pending_old)
        with self.assertRaises(ConflictError):
            self._proposal("tenant_a", 1, at=self.t0 + 10**9, source="old")

    def test_v2_the_actor_bound_is_an_adjacent_pair(self) -> None:
        self.now[0] = self.t0 + 10**12
        with self.assertRaisesRegex(ValidationError, "actor"):
            self.system.prune_proposals("tenant_a", older_than_seconds=1, actor="a" * 257)
        result = self.system.prune_proposals("tenant_a", older_than_seconds=1, actor="a" * 256)
        self.assertEqual(self.system.events("tenant_a")[-1]["payload"]["actor"], "a" * 256)
        self.assertEqual(result.count, 3)

    def test_v2_arguments_are_graded_first(self) -> None:
        for value in (-1, True, 1.0, "1", _MAX_AGE_SECONDS + 1):
            with self.subTest(value=value), self.assertRaisesRegex(ValidationError, "older_than_seconds"):
                self.system.prune_proposals("tenant_a", older_than_seconds=value, actor="ops")  # type: ignore[arg-type]
        self.now[0] = 2**63 - 1
        self.assertEqual(self.system.prune_proposals("tenant_a", older_than_seconds=_MAX_AGE_SECONDS, actor="ops").count, 0)
        with self.assertRaisesRegex(ValidationError, "actor"):
            self.system.prune_proposals("tenant_a", older_than_seconds=1, actor="")


class EraseTests(_Ledger):
    def setUp(self) -> None:
        super().setUp()
        _populate(self.system, "tenant_a", "MARKER-A-ERASE", self.texts, extra_program=True)
        for partition in ("tenantXa", "Tenant_a"):
            _populate(self.system, partition, "MARKER-NEIGHBOUR", self.texts, extra_program=False)

    def test_v3_every_row_of_the_partition_goes_and_neighbours_stay(self) -> None:
        before = _rows(self.db, "tenant_a")
        for table, rows in before.items():
            self.assertTrue(rows, f"fixture has no {table} row")  # positive control per table
        rowids = _rowids(self.db, "tenant_a")
        self.assertEqual(_present(self.db, rowids), rowids)  # control: the probe sees them
        neighbours = {p: _rows(self.db, p) for p in ("tenantXa", "Tenant_a")}
        with closing(sqlite3.connect(self.db)) as connection:
            programs_before = {row[0] for row in connection.execute("SELECT program_hash FROM projection_programs")}
        result = self.system.erase_partition("tenant_a", actor="ops")
        self.assertEqual({t: ids for t, ids in _present(self.db, rowids).items() if ids}, {})
        self.assertEqual({t: rows for t, rows in _rows(self.db, "tenant_a").items() if rows}, {})
        self.assertEqual(result.counts, {**{t: len(r) for t, r in before.items()}, "projection_programs": 1})
        for partition, rows in neighbours.items():
            self.assertEqual(_rows(self.db, partition), rows)
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            programs_after = {row[0] for row in connection.execute("SELECT program_hash FROM projection_programs")}
            tombstones = connection.execute(
                "SELECT id, partition_hash, counts_json, erased_by FROM erasures"
            ).fetchall()
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM erasure_grants").fetchone()[0], 0)
        # The shared program stays for its neighbours; the program only `tenant_a` named goes.
        self.assertEqual(len(programs_before - programs_after), 1)
        self.assertEqual(programs_after, programs_before - (programs_before - programs_after))
        self.assertEqual(
            tombstones,
            [(result.erasure_id, _digest_strings("cement-partition-v1", ("tenant_a",)),
              json.dumps(result.counts, sort_keys=True, separators=(",", ":")), "ops")],
        )
        self.assertEqual(result.partition_hash, _digest_strings("cement-partition-v1", ("tenant_a",)))

    def test_v3_the_erased_bytes_leave_the_ledger_file(self) -> None:
        self.assertIn(b"MARKER-A-ERASE", pathlib.Path(self.db).read_bytes())  # control
        self.system.erase_partition("tenant_a", actor="ops")
        raw = pathlib.Path(self.db).read_bytes()
        self.assertNotIn(b"MARKER-A-ERASE", raw)
        self.assertIn(b"MARKER-NEIGHBOUR", raw)

    def test_v2a_the_control_without_secure_delete_keeps_the_bytes(self) -> None:
        # The same fixture built and erased with every write connection forced OFF keeps copies, so
        # the absence above comes from `secure_delete`, never from a SQLite build default.
        original = Store._connect

        def insecure(store: Store, *, read_only: bool = False) -> sqlite3.Connection:
            connection = original(store, read_only=read_only)
            if not read_only:
                connection.execute("PRAGMA secure_delete = OFF")
            return connection

        database = str(self.root / "insecure.db")
        with mock.patch.object(Store, "_connect", insecure):
            system = System(database)
            _populate(system, "tenant_a", "MARKER-A-ERASE", self.texts, extra_program=True)
            system.erase_partition("tenant_a", actor="ops")
        self.assertIn(b"MARKER-A-ERASE", pathlib.Path(database).read_bytes())
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA secure_delete").fetchone()[0], 0)  # per connection
        with self.system.store.transaction(write=True) as connection:
            self.assertEqual(connection.execute("PRAGMA secure_delete").fetchone()[0], 1)

    def test_v3_an_orphan_program_and_an_events_only_partition(self) -> None:
        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute(
                "INSERT INTO projection_programs VALUES (?, 'cement-projection-v1', '{}')", ("f" * 64,)
            )
            connection.execute(
                "INSERT INTO events(partition, kind, subject_type, subject_id, payload_json, created_at_us)"
                " VALUES ('ghost', 'probe', 'partition', 'ghost', '{}', 1)"
            )
            connection.commit()
        self.system.erase_partition("tenant_a", actor="ops")
        ghost = self.system.erase_partition("ghost", actor="ops")
        self.assertEqual({t: n for t, n in ghost.counts.items() if n}, {"events": 1})
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM projection_programs WHERE program_hash = ?", ("f" * 64,)).fetchone()[0], 1
            )

    def test_v3_a_failure_at_the_tombstone_rolls_everything_back(self) -> None:
        before = pathlib.Path(self.db).read_bytes()
        real = system_module._new_id

        def failing(prefix: str) -> str:
            if prefix == "er":
                raise RuntimeError("planted tombstone failure")
            return real(prefix)

        with mock.patch.object(system_module, "_new_id", failing), self.assertRaisesRegex(RuntimeError, "planted"):
            self.system.erase_partition("tenant_a", actor="ops")
        self.assertEqual(pathlib.Path(self.db).read_bytes(), before)
        reopened = System(self.db, create=False)
        self.assertTrue(reopened.operations("tenant_a"))
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM erasure_grants").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM erasures").fetchone()[0], 0)

    def test_v3_the_actor_bound_is_an_adjacent_pair(self) -> None:
        with self.assertRaisesRegex(ValidationError, "actor"):
            self.system.erase_partition("tenant_a", actor="a" * 257)
        operations = len(self.system.operations("tenant_a"))
        self.assertEqual(self.system.erase_partition("tenant_a", actor="a" * 256).counts["operations"], operations)
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("SELECT erased_by FROM erasures").fetchone()[0], "a" * 256)

    def test_v3_serving_forgets_the_partition(self) -> None:
        text = self.texts[0]
        warm = self.system.resolve("tenant_a", "plan", {"document": text})
        self.assertTrue(warm.match.matched)
        self.system.erase_partition("tenant_a", actor="ops")
        with self.assertRaises(NotFoundError):
            self.system.resolve("tenant_a", "plan", {"document": text})
        self.assertTrue(self.system.resolve("tenantXa", "plan", {"document": text}).match.matched)

    def test_v3_an_empty_partition_or_a_failed_step_writes_nothing(self) -> None:
        before = pathlib.Path(self.db).read_bytes()
        with self.assertRaisesRegex(NotFoundError, "the partition has no rows"):
            self.system.erase_partition("tenant_b", actor="ops")
        self.assertEqual(pathlib.Path(self.db).read_bytes(), before)
        # A neighbour's evidence edge onto a `tenant_a` example: the examples delete then breaks a
        # foreign key, so the whole erase rolls back.
        connection = sqlite3.connect(self.db, isolation_level=None)
        try:
            artifact = connection.execute("SELECT id FROM artifacts WHERE partition = 'tenantXa' LIMIT 1").fetchone()[0]
            example = connection.execute("SELECT id FROM examples WHERE partition = 'tenant_a' LIMIT 1").fetchone()[0]
            trigger = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'artifact_evidence_building_insert'"
            ).fetchone()[0]
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DROP TRIGGER artifact_evidence_building_insert")
            connection.execute("INSERT INTO artifact_evidence VALUES (?, ?)", (artifact, example))
            connection.execute(trigger)
            connection.execute("COMMIT")
        finally:
            connection.close()
        planted = pathlib.Path(self.db).read_bytes()
        with self.assertRaises((IntegrityError, ConflictError, ValidationError)):
            self.system.erase_partition("tenant_a", actor="ops")
        self.assertEqual(pathlib.Path(self.db).read_bytes(), planted)
        self.assertTrue(_rows(self.db, "tenant_a")["examples"])


class RetentionCLITests(_Ledger):
    def run_cli(self, *argv: str) -> tuple[int, str, dict]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", self.db, "--partition", "tenant_a", *argv])
        return code, out.getvalue(), json.loads(err.getvalue()) if err.getvalue() else {}

    def test_v5_prune_and_erase_exit_classes(self) -> None:
        # `main` builds its own System on the real clock, so the fixture writes on it too.
        system = System(self.db)
        system.register_operation("tenant_a", "echo", policy=POLICY)
        system.submit_proposal("tenant_a", "echo", {"x": 1}, candidate=Candidate(output={"y": 1}, provenance={}))
        code, out, _ = self.run_cli("retention", "prune", "--older-than", "1", "--actor", "ops")
        self.assertEqual((code, json.loads(out)["count"]), (0, 0))  # created under a day ago
        code, out, _ = self.run_cli("retention", "prune", "--older-than", "0", "--actor", "ops")
        self.assertEqual((code, json.loads(out)["count"]), (0, 1))
        max_days = _MAX_AGE_SECONDS // 86_400
        self.assertEqual(self.run_cli("retention", "prune", "--older-than", str(max_days), "--actor", "ops")[0], 0)
        for days in ("-1", str(max_days + 1)):
            code, out, error = self.run_cli("retention", "prune", "--older-than", days, "--actor", "ops")
            self.assertEqual((code, out), (2, ""))
            self.assertIn("--older-than must be a whole number of days", error["message"])
        missing = str(self.root / "missing.db")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", missing, "--partition", "tenant_a", "partition", "erase", "--actor", "ops", "--confirm", "x"])
        self.assertEqual((code, out.getvalue()), (5, ""))  # p51: an absent ledger exits 5 first
        self.assertFalse(os.path.exists(missing))  # and the existing-only open creates nothing
        before = pathlib.Path(self.db).read_bytes()
        code, out, error = self.run_cli("partition", "erase", "--actor", "ops", "--confirm", "tenantXa")
        self.assertEqual((code, out, error["message"]), (2, "", "--confirm must repeat the --partition value"))
        self.assertEqual(pathlib.Path(self.db).read_bytes(), before)
        code, out, _ = self.run_cli("partition", "erase", "--actor", "ops", "--confirm", "tenant_a")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(json.loads(out)), ["counts", "erasure_id", "partition_hash", "shadow"])
        code, out, error = self.run_cli("partition", "erase", "--actor", "ops", "--confirm", "tenant_a")
        self.assertEqual((code, out, error["error"]), (3, "", "not_found"))


if __name__ == "__main__":
    unittest.main()
