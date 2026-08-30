"""M3.3 explicit proposal submission over a retained schema-v2 request row - the implementation suite.

Pins the headline predicates of `.agent/decisions/m3u3-contract.md`: the two
paths' durable footprint, validation precedence on every adjacent edge, source
containment, error texts, purity, and the frozen shapes the unit must not move.

The unit's obligation-graded battery is diff-blind and lands separately; this
suite is MAIN's own, written beside the implementation.
"""

from __future__ import annotations

import ast
from contextlib import closing
import hashlib
import inspect
import pathlib
import re
import sqlite3
import tempfile
import typing
import unittest
from unittest import mock

import cement_runtime
from cement_runtime import (
    Candidate,
    CandidateSourceError,
    CompilePolicy,
    NotFoundError,
    ReviewRequired,
    StateError,
    System,
    ValidationError,
    store as store_module,
)

SECRET = "adapter-secret-42"

# D01's footprint quantifies over every APPLICATION table the live ledger
# declares, derived here rather than named, because a hand-written list is a
# footprint with holes: nine named tables left `artifact_evidence`,
# `artifact_tests`, `schema_metadata` and `test_reports` unmeasured, so an extra
# write to any of them passed every count. The exclusion rule is explicit and is
# the only one: SQLite owns the `sqlite_` prefix, and `events.sequence` is
# AUTOINCREMENT, so `sqlite_sequence` legitimately moves on every success.
SQLITE_OWNED = "sqlite_"
DECLARED_APPLICATION_TABLES = 13


def _application_tables(connection: sqlite3.Connection) -> list[str]:
    tables = [
        name
        for (name,) in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
        )
        if not name.startswith(SQLITE_OWNED)
    ]
    if not tables:
        raise AssertionError("the schema derivation found no application tables")
    return tables


class _Source:
    """Candidate source recording every invocation, with pluggable behaviour."""

    def __init__(self, behaviour=None) -> None:
        self.calls: list[object] = []
        self.behaviour = behaviour

    def propose(self, request):
        self.calls.append(request)
        if self.behaviour is not None:
            return self.behaviour(request)
        return Candidate(output={"echo": request.input}, provenance={"model": "suite"})


class SubmissionTests(unittest.TestCase):
    def _make_system(self, *, source: _Source | None = None) -> tuple[System, pathlib.Path, _Source]:
        temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(temporary.cleanup)
        database = pathlib.Path(temporary.name) / "cement.db"
        source = _Source() if source is None else source
        system = System(database, candidate_source=source)
        system.register_operation("tenant_a", "echo_1", policy=CompilePolicy(2, 2, 0))
        return system, database, source

    def _candidate(self) -> Candidate:
        return Candidate(output={"v": 10}, provenance={"model": "suite"})

    def _counts(self, database: pathlib.Path) -> dict[str, int]:
        with closing(sqlite3.connect(database)) as connection:
            tables = _application_tables(connection)
            self.assertEqual(len(tables), DECLARED_APPLICATION_TABLES)
            return {
                table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in tables
            }

    def _fingerprint(self, database: pathlib.Path) -> tuple[str, str]:
        with closing(sqlite3.connect(database)) as connection:
            dump = "\n".join(connection.iterdump())
        return hashlib.sha256(database.read_bytes()).hexdigest(), dump

    def _rows(self, database: pathlib.Path, sql: str) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(database)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(sql).fetchall()

    # -- direct path ------------------------------------------------------

    def test_submit_proposal_returns_a_bare_proposal_id(self):
        system, _, _ = self._make_system()
        proposal_id = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        self.assertIs(type(proposal_id), str)
        self.assertTrue(proposal_id.startswith("prop_"))
        self.assertEqual(len(proposal_id), len("prop_") + 32)

    def test_submit_proposal_writes_one_request_one_proposal_and_one_event(self):
        system, database, _ = self._make_system()
        before = self._counts(database)
        system.submit_proposal("tenant_a", "echo_1", {"k": 1}, candidate=self._candidate())
        after = self._counts(database)
        self.assertEqual(
            {table: after[table] - before[table] for table in after if after[table] != before[table]},
            {"requests": 1, "proposals": 1, "events": 1},
        )

    def test_submit_proposal_writes_a_pending_request_row_without_a_lease(self):
        system, database, _ = self._make_system()
        proposal_id = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        row = self._rows(database, "SELECT * FROM requests")[0]
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["proposal_id"], proposal_id)
        self.assertIsNone(row["lease_owner"])
        self.assertIsNone(row["lease_until_us"])
        self.assertEqual(row["attempts"], 1)
        self.assertEqual(row["operation_revision"], 1)
        self.assertIsNone(row["output_json"])
        self.assertIsNone(row["error_code"])

    def test_submit_proposal_event_carries_no_request_identity(self):
        system, database, _ = self._make_system()
        proposal_id = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        request_id = self._rows(database, "SELECT id FROM requests")[0]["id"]
        event = self._rows(database, "SELECT * FROM events ORDER BY sequence DESC LIMIT 1")[0]
        self.assertEqual(event["kind"], "proposal.created")
        self.assertEqual(event["subject_type"], "proposal")
        self.assertEqual(event["subject_id"], proposal_id)
        self.assertEqual(event["payload_json"], "{}")
        self.assertNotIn(request_id, event["payload_json"])

    def test_submit_proposal_never_invokes_a_configured_source(self):
        exploding = _Source(lambda request: (_ for _ in ()).throw(RuntimeError(SECRET)))
        system, _, source = self._make_system(source=exploding)
        proposal_id = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        self.assertEqual(source.calls, [])
        self.assertTrue(proposal_id.startswith("prop_"))

    def test_submit_proposal_persists_the_candidate_output_and_provenance(self):
        system, database, _ = self._make_system()
        system.submit_proposal("tenant_a", "echo_1", {"k": 1}, candidate=self._candidate())
        row = self._rows(database, "SELECT * FROM proposals")[0]
        self.assertEqual(row["proposed_output_json"], '{"v":10}')
        self.assertEqual(row["provenance_json"], '{"model":"suite"}')
        self.assertEqual(row["status"], "pending")
        event = self._rows(database, "SELECT * FROM events ORDER BY sequence DESC LIMIT 1")[0]
        self.assertEqual(row["status_sequence"], event["sequence"])

    # -- source path ------------------------------------------------------

    def test_propose_matches_the_direct_footprint(self):
        system, database, _ = self._make_system()
        before = self._counts(database)
        proposal_id = system.propose("tenant_a", "echo_1", {"k": 3})
        after = self._counts(database)
        self.assertIs(type(proposal_id), str)
        self.assertEqual(
            {table: after[table] - before[table] for table in after if after[table] != before[table]},
            {"requests": 1, "proposals": 1, "events": 1},
        )

    def test_propose_invokes_the_source_once_with_the_generated_request_id(self):
        system, database, source = self._make_system()
        system.propose("tenant_a", "echo_1", {"k": 3})
        self.assertEqual(len(source.calls), 1)
        request = source.calls[0]
        stored = self._rows(database, "SELECT id FROM requests")[0]["id"]
        self.assertEqual(request.request_id, stored)
        self.assertEqual(request.partition, "tenant_a")
        self.assertEqual(request.operation, "echo_1")
        self.assertEqual(request.operation_revision, 1)
        self.assertEqual(request.input, {"k": 3})

    def test_propose_runs_the_source_outside_every_transaction(self):
        """Structural pin: every connection Cement opens is observed while the source runs.

        A closed connection cannot be in a transaction, so ProgrammingError reads
        as False. The positive control stops the probe passing vacuously, which a
        spy that failed to install would otherwise do.
        """

        opened: list[sqlite3.Connection] = []
        real_connect = store_module.sqlite3.connect

        def spy_connect(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        def in_transaction() -> bool:
            for connection in opened:
                try:
                    if connection.in_transaction:
                        return True
                except sqlite3.ProgrammingError:
                    continue
            return False

        observed: list[bool] = []
        source = _Source(lambda request: observed.append(in_transaction()) or self._candidate())
        system, _, _ = self._make_system(source=source)

        with mock.patch.object(store_module.sqlite3, "connect", spy_connect):
            system.propose("tenant_a", "echo_1", {"k": 4})
            self.assertEqual(observed, [False])
            self.assertGreaterEqual(len(opened), 2)
            with system.store.transaction(write=True):
                self.assertTrue(in_transaction())

    # -- no idempotency ----------------------------------------------------

    def test_identical_content_submitted_twice_writes_two_of_everything(self):
        system, database, _ = self._make_system()
        first = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        second = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        self.assertNotEqual(first, second)
        counts = self._counts(database)
        self.assertEqual(counts["requests"], 2)
        self.assertEqual(counts["proposals"], 2)
        self.assertEqual(len(self._rows(database, "SELECT DISTINCT id FROM requests")), 2)

    # -- error classification ----------------------------------------------

    def test_declared_and_arbitrary_source_failures_are_indistinguishable(self):
        observations = []
        for behaviour in (
            lambda request: (_ for _ in ()).throw(CandidateSourceError(SECRET)),
            lambda request: (_ for _ in ()).throw(RuntimeError(SECRET)),
            lambda request: Candidate(output=object(), provenance={}),
        ):
            system, _, _ = self._make_system(source=_Source(behaviour))
            with self.assertRaises(CandidateSourceError) as caught:
                system.propose("tenant_a", "echo_1", {"k": 5})
            observations.append((type(caught.exception), str(caught.exception)))
        self.assertEqual(len(set(observations)), 1)
        self.assertEqual(observations[0], (CandidateSourceError, "candidate source failed"))

    def test_source_failure_leaks_no_cause_context_or_detail(self):
        system, _, _ = self._make_system(
            source=_Source(lambda request: (_ for _ in ()).throw(RuntimeError(SECRET)))
        )
        with self.assertRaises(CandidateSourceError) as caught:
            system.propose("tenant_a", "echo_1", {"k": 5})
        error = caught.exception
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertTrue(error.__suppress_context__)
        self.assertNotIn(SECRET, repr(error))
        self.assertNotIn(SECRET, str(error))

    def test_propose_without_a_configured_source_raises_state_error(self):
        system, _, _ = self._make_system()
        system.candidate_source = None
        with self.assertRaises(StateError) as caught:
            system.propose("tenant_a", "echo_1", {"k": 6})
        self.assertEqual(str(caught.exception), "candidate source is not configured")

    def test_unregistered_operation_raises_not_found_before_the_source_runs(self):
        system, _, source = self._make_system()
        with self.assertRaises(NotFoundError) as caught:
            system.propose("tenant_a", "absent_1", {"k": 7})
        self.assertEqual(
            str(caught.exception), "operation is not registered in this partition"
        )
        self.assertEqual(source.calls, [])

    def test_revision_change_during_generation_raises_state_error(self):
        system, database, _ = self._make_system()

        def revise(request):
            system.revise_operation(
                "tenant_a", "echo_1", policy=CompilePolicy(3, 1, 0), revised_by="probe"
            )
            return self._candidate()

        system.candidate_source = _Source(revise)
        before = self._counts(database)
        with self.assertRaises(StateError) as caught:
            system.propose("tenant_a", "echo_1", {"k": 8})
        self.assertEqual(
            str(caught.exception), "operation revision changed before proposal submission"
        )
        after = self._counts(database)
        self.assertEqual(after["requests"], before["requests"])
        self.assertEqual(after["proposals"], before["proposals"])

    def test_a_revised_operation_still_accepts_a_direct_submission(self):
        """The revision guard belongs to the generation window, not to submission.

        A direct caller captures no revision, so a revision that moves before the
        call has nothing to invalidate. The proposal binds to whatever revision
        holds under the write lock.
        """

        system, database, _ = self._make_system()
        system.revise_operation(
            "tenant_a", "echo_1", policy=CompilePolicy(3, 1, 0), revised_by="probe"
        )
        proposal_id = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        row = self._rows(database, "SELECT * FROM requests")[0]
        self.assertEqual(row["proposal_id"], proposal_id)
        self.assertEqual(row["operation_revision"], 2)

    # -- purity ------------------------------------------------------------

    def test_failed_submission_leaves_the_ledger_byte_identical(self):
        system, database, _ = self._make_system(
            source=_Source(lambda request: (_ for _ in ()).throw(RuntimeError(SECRET)))
        )
        before_counts = self._counts(database)
        before_sha, before_dump = self._fingerprint(database)
        with self.assertRaises(CandidateSourceError):
            system.propose("tenant_a", "echo_1", {"k": 5})
        with self.assertRaises(NotFoundError):
            system.submit_proposal(
                "tenant_a", "absent_1", {"k": 5}, candidate=self._candidate()
            )
        after_sha, after_dump = self._fingerprint(database)
        self.assertEqual(self._counts(database), before_counts)
        self.assertEqual(after_sha, before_sha)
        self.assertEqual(after_dump, before_dump)

    def test_no_commit_is_issued_on_any_submission_failure_path(self):
        """Independent of ledger bytes: a successful no-op commit moves neither."""

        commits: list[str] = []

        class _CountingConnection(sqlite3.Connection):
            def commit(self) -> None:
                commits.append("commit")
                super().commit()

        real_connect = store_module.sqlite3.connect

        def spy_connect(*args, **kwargs):
            kwargs["factory"] = _CountingConnection
            return real_connect(*args, **kwargs)

        system, database, _ = self._make_system(
            source=_Source(lambda request: (_ for _ in ()).throw(RuntimeError(SECRET)))
        )
        with mock.patch.object(store_module.sqlite3, "connect", spy_connect):
            with system.store.transaction(write=True) as connection:
                connection.execute("SELECT 1").fetchone()
            self.assertEqual(commits, ["commit"], "the commit spy failed to install")

            commits.clear()
            failures = {
                "source": lambda: system.propose("tenant_a", "echo_1", {"k": 5}),
                "absent": lambda: system.submit_proposal(
                    "tenant_a", "absent_1", {"k": 5}, candidate=self._candidate()
                ),
                "rejected": lambda: system.submit_proposal(
                    "bad partition!", "echo_1", {"k": 5}, candidate=self._candidate()
                ),
            }
            for label, call in failures.items():
                with self.subTest(failure=label):
                    with self.assertRaises(Exception):
                        call()
                    self.assertEqual(commits, [])

    def test_a_commit_that_succeeds_then_raises_leaves_the_rows_durable(self):
        """D46: the one window where submission raises and the rows are durable.

        D15 is scoped to failures BEFORE commit precisely because this window
        exists. `Store.transaction` commits, and a `commit()` that durably
        succeeds and only then raises maps to `StateError` like any other store
        failure - so the caller sees a raise, receives no proposal id, and the
        three rows are committed anyway.

        The control is the load-bearing half: the same injection WITHOUT the
        raise leaves an identical ledger delta. No observable in the ledger
        separates the two, which is why the published recovery route is
        enumeration by partition and never a blind retry.
        """

        def run(*, raise_after_commit: bool):
            commits: list[str] = []

            class _CommitThenFail(sqlite3.Connection):
                def commit(self):
                    commits.append("commit")
                    super().commit()
                    if raise_after_commit:
                        raise sqlite3.OperationalError("database is locked")

            real_connect = store_module.sqlite3.connect

            def spy_connect(*args, **kwargs):
                kwargs["factory"] = _CommitThenFail
                return real_connect(*args, **kwargs)

            system, database, _ = self._make_system()
            before = self._counts(database)
            raised: Exception | None = None
            returned: str | None = None
            with mock.patch.object(store_module.sqlite3, "connect", spy_connect):
                try:
                    returned = system.submit_proposal(
                        "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
                    )
                except StateError as error:
                    raised = error
            after = self._counts(database)
            delta = {
                table: after[table] - before[table]
                for table in after
                if after[table] != before[table]
            }
            return system, database, commits, raised, returned, delta

        system, database, commits, raised, returned, delta = run(raise_after_commit=True)
        self.assertEqual(commits, ["commit"], "the commit injection failed to install")
        self.assertIsNotNone(raised, "the injected commit failure did not reach the caller")
        self.assertEqual(str(raised), "database is busy or unavailable")
        self.assertIsNone(returned, "the caller must receive no proposal id")
        # Durability is read from a SEPARATE connection, never the injected one.
        self.assertEqual(delta, {"requests": 1, "proposals": 1, "events": 1})

        # The recovery route, exactly as published: enumerate by partition, then
        # resolve. Both are ordinary read APIs that need no id from the caller.
        pending = system.proposals("tenant_a", status="pending")
        self.assertEqual(len(pending), 1)
        orphan = pending[0]["id"]
        view = system.get_proposal("tenant_a", orphan)
        self.assertEqual(view.input, {"k": 1})
        self.assertEqual(view.proposed_output, {"v": 10})
        self.assertEqual(
            self._rows(database, "SELECT proposal_id FROM requests")[0]["proposal_id"],
            orphan,
        )

        # Control: identical ledger delta, and the id returned. The ledger cannot
        # tell the operator which of the two happened.
        _, _, control_commits, control_raised, control_returned, control_delta = run(
            raise_after_commit=False
        )
        self.assertEqual(control_commits, ["commit"])
        self.assertIsNone(control_raised)
        self.assertIsNotNone(control_returned)
        self.assertEqual(control_delta, delta)

    def test_submission_reads_no_artifact_example_or_function_table(self):
        """D17: neither path touches a table outside submission's own four.

        The instrument is a COMPLEMENT, not a hand-written forbidden list: it
        tokenizes each recorded statement into SQL identifiers, folds them to
        lower case, and asserts the set of application tables named is exactly
        the permitted four. `if table in sql` over raw SQL was neither - it
        missed `FROM ARTIFACTS` on case alone, and it could never see a table
        the list forgot to name.

        This is a TRIPWIRE. A change that legitimately reads a fifth table must
        widen `permitted` deliberately, which is the acknowledgement D17 exists
        to force. It is not a cardinality gate: nothing here can be satisfied by
        hiding a read behind a wider query, because a wider query names more
        tables, not fewer.
        """

        executed: list[str] = []

        class _RecordingCursor:
            """Total over the cursor API, so no read escapes by changing channel."""

            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __iter__(self):
                return iter(self._inner)

            def execute(self, sql, *args, **kwargs):
                executed.append(sql)
                return self._inner.execute(sql, *args, **kwargs)

            def executemany(self, sql, *args, **kwargs):
                executed.append(sql)
                return self._inner.executemany(sql, *args, **kwargs)

            def executescript(self, sql, *args, **kwargs):
                executed.append(sql)
                return self._inner.executescript(sql, *args, **kwargs)

        class _RecordingConnection(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                executed.append(sql)
                return super().execute(sql, *args, **kwargs)

            def executemany(self, sql, *args, **kwargs):
                executed.append(sql)
                return super().executemany(sql, *args, **kwargs)

            def executescript(self, sql, *args, **kwargs):
                executed.append(sql)
                return super().executescript(sql, *args, **kwargs)

            def cursor(self, *args, **kwargs):
                return _RecordingCursor(super().cursor(*args, **kwargs))

        real_connect = store_module.sqlite3.connect

        def spy_connect(*args, **kwargs):
            kwargs["factory"] = _RecordingConnection
            return real_connect(*args, **kwargs)

        system, database, _ = self._make_system()
        with mock.patch.object(store_module.sqlite3, "connect", spy_connect):
            executed.clear()
            system.submit_proposal(
                "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
            )
            direct = list(executed)
            executed.clear()
            system.propose("tenant_a", "echo_1", {"k": 2})
            sourced = list(executed)

        self.assertTrue(direct and sourced, "the SQL spy failed to install")
        with closing(sqlite3.connect(database)) as connection:
            application = set(_application_tables(connection))
        permitted = {"operations", "requests", "proposals", "events"}
        self.assertLess(permitted, application, "the permitted set must be a strict subset")
        forbidden = application - permitted
        self.assertEqual(len(forbidden), DECLARED_APPLICATION_TABLES - len(permitted))

        identifier = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        for label, statements in (("direct", direct), ("source", sourced)):
            words = {word.lower() for sql in statements for word in identifier.findall(sql)}
            with self.subTest(path=label):
                self.assertEqual(
                    sorted(application & words),
                    sorted(permitted),
                    f"{label} path named {sorted(forbidden & words)} outside its four tables",
                )

    # -- validation precedence, one probe per ADJACENT edge -----------------

    def test_precedence_reports_partition_before_operation(self):
        system, _, _ = self._make_system()
        with self.assertRaises(ValidationError) as caught:
            system.submit_proposal(
                "bad partition!", "bad operation!", {"k": 1}, candidate=self._candidate()
            )
        self.assertIn("partition must", str(caught.exception))

    def test_precedence_reports_operation_before_input_value(self):
        system, _, _ = self._make_system()
        with self.assertRaises(ValidationError) as caught:
            system.submit_proposal(
                "tenant_a", "bad operation!", object(), candidate=self._candidate()
            )
        self.assertIn("operation must", str(caught.exception))

    def test_precedence_reports_input_value_before_candidate(self):
        system, _, _ = self._make_system()
        with self.assertRaises(ValidationError) as caught:
            system.submit_proposal(
                "tenant_a", "echo_1", object(), candidate="not a candidate"
            )
        self.assertNotIn("candidate must", str(caught.exception))

    def test_precedence_reports_input_value_before_the_configured_source_check(self):
        system, _, _ = self._make_system()
        system.candidate_source = None
        with self.assertRaises(ValidationError):
            system.propose("tenant_a", "echo_1", object())

    def test_precedence_reports_an_unconfigured_source_before_an_absent_operation(self):
        system, _, _ = self._make_system()
        system.candidate_source = None
        with self.assertRaises(StateError) as caught:
            system.propose("tenant_a", "absent_1", {"k": 1})
        self.assertEqual(str(caught.exception), "candidate source is not configured")

    def test_a_rejected_candidate_reports_its_own_validation_text(self):
        system, _, _ = self._make_system()
        for candidate, fragment in (
            ("not a candidate", "candidate must be a Candidate"),
            (Candidate(output={"v": 1}, provenance=5), "candidate provenance must be a mapping"),
        ):
            with self.subTest(candidate=type(candidate).__name__):
                with self.assertRaises(ValidationError) as caught:
                    system.submit_proposal(
                        "tenant_a", "echo_1", {"k": 1}, candidate=candidate
                    )
                self.assertEqual(str(caught.exception), fragment)

    def test_a_rejected_call_opens_no_transaction_and_invokes_no_source(self):
        system, _, source = self._make_system()
        with mock.patch.object(
            system.store, "transaction", wraps=system.store.transaction
        ) as transaction:
            for call in (
                lambda: system.submit_proposal(
                    "bad partition!", "echo_1", {"k": 1}, candidate=self._candidate()
                ),
                lambda: system.propose("bad partition!", "echo_1", {"k": 1}),
                lambda: system.submit_proposal(
                    "tenant_a", "echo_1", object(), candidate=self._candidate()
                ),
            ):
                with self.assertRaises(ValidationError):
                    call()
            self.assertEqual(transaction.call_count, 0)
            self.assertEqual(source.calls, [])
            # Positive control: the same spy counts a real submission, which
            # opens exactly one write transaction. The direct path holds no
            # captured revision, so it needs no pre-read to guard.
            system.submit_proposal(
                "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
            )
            self.assertEqual(transaction.call_count, 1)

    # -- the signature is the check ----------------------------------------

    def test_omitting_candidate_raises_python_type_error(self):
        system, _, _ = self._make_system()
        with self.assertRaises(TypeError) as caught:
            system.submit_proposal("tenant_a", "echo_1", {"k": 1})
        self.assertIn("candidate", str(caught.exception))

    def test_a_source_keyword_is_rejected_by_both_signatures(self):
        system, _, _ = self._make_system()
        with self.assertRaises(TypeError):
            system.submit_proposal(
                "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate(), source=object()
            )
        with self.assertRaises(TypeError):
            system.propose("tenant_a", "echo_1", {"k": 1}, source=object())

    # -- frozen shapes ------------------------------------------------------

    def test_handle_is_byte_identical_to_the_unit_baseline(self):
        """P06: `handle` keeps the bytes it has carried since 3b7769b, less one constant.

        Convention: the whole-line span from `node.lineno` to `node.end_lineno`,
        which keeps the leading indentation, with trailing newlines stripped.
        A column-offset slice measures 4 bytes shorter and is a different claim.

        M3.5a's D16 routes every provenance limit through the exported
        `PROVENANCE_MAX_BYTES`, and one of the three literal sites sits inside
        this method, so the freeze broke on a value-preserving identifier
        substitution rather than on any behaviour change. The pin is re-anchored
        with its delta asserted: substituting the literal back reproduces
        M3.3's own numbers, so the substitution is the whole delta.
        """

        source = pathlib.Path(cement_runtime.system.__file__).read_text(encoding="utf-8")
        lines = source.splitlines(keepends=True)
        spans = [
            "".join(lines[node.lineno - 1 : node.end_lineno]).rstrip("\n")
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == "handle"
        ]
        self.assertEqual(len(spans), 1)
        payload = spans[0].encode("utf-8")
        self.assertEqual(len(payload), 12_880)
        self.assertTrue(
            hashlib.sha256(payload).hexdigest().startswith("eec7cb7c85f8")
        )

        self.assertEqual(spans[0].count("PROVENANCE_MAX_BYTES"), 1)
        restored = spans[0].replace("PROVENANCE_MAX_BYTES", "65_536").encode("utf-8")
        self.assertEqual(len(restored), 12_866)
        self.assertTrue(
            hashlib.sha256(restored).hexdigest().startswith("1182130a2b3a")
        )

    def test_submission_adds_no_exported_symbol(self):
        for name in ("submit_proposal", "propose"):
            with self.subTest(name=name):
                self.assertNotIn(name, cement_runtime.__all__)
                self.assertFalse(hasattr(cement_runtime, name))
                self.assertTrue(hasattr(System, name))

    def test_the_seam_is_the_sole_writer_in_both_call_closures(self):
        """D06, structurally: `_persist_proposal` OWNS all three writes.

        The runtime spy below proves both public methods CALL the seam. That is
        satisfied by a split writer - keep `_persist_proposal` as a wrapper, move
        the `requests` INSERT into a second private helper it calls, and every
        behavioural pin still passes. Ownership is a property of the source, so
        it is measured on the source.

        The probe walks the `self.<method>` call closure of each public method
        and requires exactly ONE function in it to execute SQL writes. Scoping to
        the closure is what keeps `handle`'s own request/proposal writes, which
        M3.3 does not touch, out of the measurement.
        """

        source = pathlib.Path(cement_runtime.system.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        system_class = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "System"
        )
        methods = {
            node.name: node
            for node in system_class.body
            if isinstance(node, ast.FunctionDef)
        }

        def self_calls(node: ast.FunctionDef) -> set[str]:
            return {
                child.func.attr
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "self"
                and child.func.attr in methods
            }

        def closure(entry: str) -> set[str]:
            seen: set[str] = set()
            pending = [entry]
            while pending:
                name = pending.pop()
                if name in seen:
                    continue
                seen.add(name)
                pending.extend(self_calls(methods[name]) - seen)
            return seen

        writes = re.compile(r"\binsert\s+into\s+(requests|proposals)\b", re.IGNORECASE)

        def write_profile(node: ast.FunctionDef) -> tuple[list[str], int]:
            tables = [
                match.group(1).lower()
                for child in ast.walk(node)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
                for match in writes.finditer(child.value)
            ]
            events = [
                child
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "_event"
                and any(
                    keyword.arg == "kind"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value == "proposal.created"
                    for keyword in child.keywords
                )
            ]
            return sorted(tables), len(events)

        for entry in ("submit_proposal", "propose"):
            with self.subTest(entry=entry):
                reached = closure(entry)
                self.assertIn("_persist_proposal", reached)
                writers = {
                    name for name in reached if write_profile(methods[name]) != ([], 0)
                }
                self.assertEqual(
                    writers,
                    {"_persist_proposal"},
                    f"{entry} reaches writers outside the seam: {sorted(writers)}",
                )
                # The public method delegates; it holds no write of its own.
                self.assertEqual(write_profile(methods[entry]), ([], 0))

        # Positive control plus the exact ownership claim: the seam writes each
        # row once and emits the event once. A count of 0 anywhere would make the
        # `writers` comparison above pass vacuously.
        self.assertEqual(write_profile(methods["_persist_proposal"]), (["proposals", "requests"], 1))

    def test_the_frozen_public_shape_of_both_submission_methods(self):
        """P01: signature AND annotations, neither of which behaviour can see.

        Removing the keyword-only marker, weakening `candidate` to `object`,
        weakening either return annotation, and adding an ignored `candidate`
        keyword to `propose` all leave every behavioural test green.
        """

        expected = {
            "submit_proposal": (
                (
                    ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("partition", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("operation", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("input_value", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("candidate", inspect.Parameter.KEYWORD_ONLY, True),
                ),
                {
                    "partition": str,
                    "operation": str,
                    "input_value": object,
                    "candidate": Candidate,
                    "return": str,
                },
            ),
            "propose": (
                (
                    ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("partition", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("operation", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                    ("input_value", inspect.Parameter.POSITIONAL_OR_KEYWORD, True),
                ),
                {
                    "partition": str,
                    "operation": str,
                    "input_value": object,
                    "return": str,
                },
            ),
        }
        for name, (parameters, hints) in expected.items():
            method = getattr(System, name)
            with self.subTest(method=name):
                # Order, kind and required-vs-defaulted state, all in one tuple.
                self.assertEqual(
                    tuple(
                        (
                            parameter.name,
                            parameter.kind,
                            parameter.default is inspect.Parameter.empty,
                        )
                        for parameter in inspect.signature(method).parameters.values()
                    ),
                    parameters,
                )
                # Exact annotation objects, resolved through the module globals
                # that `from __future__ import annotations` defers them to. An
                # equality on the whole mapping pins absence as well as presence,
                # so an added `candidate` on `propose` fails here too.
                self.assertEqual(typing.get_type_hints(method), hints)

        self.assertNotIn("source", inspect.signature(System.propose).parameters)
        self.assertNotIn("candidate", inspect.signature(System.propose).parameters)
        self.assertNotIn("source", inspect.signature(System.submit_proposal).parameters)

    def test_both_methods_route_through_one_persistence_seam(self):
        """D06: the seam is the single writer, and it behaves the same either way."""

        seen: list[str] = []
        real_seam = System._persist_proposal

        def spy(self, **kwargs):
            seen.append(kwargs["request_id"])
            return real_seam(self, **kwargs)

        system, database, _ = self._make_system()
        with mock.patch.object(System, "_persist_proposal", spy):
            system.submit_proposal(
                "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
            )
            system.propose("tenant_a", "echo_1", {"k": 2})
        self.assertEqual(len(seen), 2)
        self.assertEqual(sorted(seen), sorted(
            row["id"] for row in self._rows(database, "SELECT id FROM requests")
        ))

    # -- interop -------------------------------------------------------------

    def test_a_submitted_proposal_flows_through_review(self):
        system, database, _ = self._make_system()
        proposal_id = system.submit_proposal(
            "tenant_a", "echo_1", {"k": 1}, candidate=self._candidate()
        )
        view = system.get_proposal("tenant_a", proposal_id)
        self.assertEqual(view.id, proposal_id)
        self.assertEqual(view.proposed_output, {"v": 10})
        self.assertEqual(view.input, {"k": 1})
        self.assertIn(
            proposal_id,
            [entry["id"] for entry in system.proposals("tenant_a", status="pending")],
        )
        system.review("tenant_a", proposal_id, reviewer="alice", decision="accept")
        self.assertIn(
            proposal_id,
            [entry["id"] for entry in system.proposals("tenant_a", status="accepted")],
        )
        request = self._rows(database, "SELECT * FROM requests")[0]
        self.assertEqual(request["status"], "resolved")
        self.assertEqual(request["source_kind"], "confirmed")
        self.assertEqual(self._counts(database)["examples"], 1)

    def test_handle_still_answers_on_a_system_that_submitted_directly(self):
        system, _, _ = self._make_system()
        system.submit_proposal("tenant_a", "echo_1", {"k": 1}, candidate=self._candidate())
        outcome = system.handle("tenant_a", "echo_1", {"k": 99})
        self.assertIs(type(outcome), ReviewRequired)


if __name__ == "__main__":
    unittest.main()
