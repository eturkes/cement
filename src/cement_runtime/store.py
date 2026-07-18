"""SQLite durability boundary.

Connections are short-lived; candidate generation never holds a database lock.
Rollback journaling + ``synchronous=EXTRA`` prioritize crash durability over write
throughput. The database file is the local trust boundary.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sqlite3

from .errors import CementError, IntegrityError, StateError, ValidationError

SCHEMA_VERSION = 1
MIN_SQLITE = (3, 37, 0)  # STRICT tables

SCHEMA = r"""
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS operations (
    partition TEXT NOT NULL,
    name TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    policy_json TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    created_at_us INTEGER NOT NULL,
    updated_at_us INTEGER NOT NULL,
    PRIMARY KEY (partition, name)
) STRICT;

CREATE TABLE IF NOT EXISTS requests (
    id TEXT NOT NULL,
    partition TEXT NOT NULL,
    operation TEXT NOT NULL,
    operation_revision INTEGER NOT NULL CHECK (operation_revision >= 1),
    input_json TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('generating', 'pending', 'resolved', 'rejected', 'failed')
    ),
    output_json TEXT,
    source_kind TEXT CHECK (source_kind IS NULL OR source_kind IN ('artifact', 'confirmed')),
    artifact_id TEXT,
    proposal_id TEXT,
    example_id TEXT,
    error_code TEXT,
    lease_owner TEXT,
    lease_until_us INTEGER,
    attempts INTEGER NOT NULL DEFAULT 1 CHECK (attempts >= 1),
    created_at_us INTEGER NOT NULL,
    updated_at_us INTEGER NOT NULL,
    CHECK (
        (status = 'generating' AND output_json IS NULL AND source_kind IS NULL
            AND artifact_id IS NULL AND proposal_id IS NULL AND example_id IS NULL
            AND error_code IS NULL AND lease_owner IS NOT NULL AND lease_until_us IS NOT NULL)
        OR (status = 'pending' AND output_json IS NULL AND source_kind IS NULL
            AND artifact_id IS NULL AND proposal_id IS NOT NULL AND example_id IS NULL
            AND error_code IS NULL AND lease_owner IS NULL AND lease_until_us IS NULL)
        OR (status = 'resolved' AND output_json IS NOT NULL AND error_code IS NULL
            AND lease_owner IS NULL AND lease_until_us IS NULL
            AND ((source_kind = 'artifact' AND artifact_id IS NOT NULL
                    AND proposal_id IS NULL AND example_id IS NULL)
                OR (source_kind = 'confirmed' AND artifact_id IS NULL
                    AND proposal_id IS NOT NULL AND example_id IS NOT NULL)))
        OR (status = 'rejected' AND output_json IS NULL AND source_kind IS NULL
            AND artifact_id IS NULL AND proposal_id IS NOT NULL AND example_id IS NULL
            AND error_code IS NULL AND lease_owner IS NULL AND lease_until_us IS NULL)
        OR (status = 'failed' AND output_json IS NULL AND source_kind IS NULL
            AND artifact_id IS NULL AND proposal_id IS NULL AND example_id IS NULL
            AND error_code IS NOT NULL AND lease_owner IS NULL AND lease_until_us IS NULL)
    ),
    PRIMARY KEY (partition, id)
) STRICT;

CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    partition TEXT NOT NULL,
    request_id TEXT NOT NULL,
    proposed_output_json TEXT NOT NULL,
    proposed_output_hash TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'corrected', 'rejected')),
    final_output_json TEXT,
    final_output_hash TEXT,
    reviewer TEXT,
    review_note TEXT,
    created_at_us INTEGER NOT NULL,
    reviewed_at_us INTEGER,
    status_sequence INTEGER NOT NULL UNIQUE CHECK (status_sequence >= 1),
    CHECK (
        (status = 'pending' AND final_output_json IS NULL AND final_output_hash IS NULL
            AND reviewer IS NULL AND review_note IS NULL AND reviewed_at_us IS NULL)
        OR (status = 'rejected' AND final_output_json IS NULL AND final_output_hash IS NULL
            AND reviewer IS NOT NULL AND review_note IS NOT NULL AND reviewed_at_us IS NOT NULL)
        OR (status IN ('accepted', 'corrected')
            AND final_output_json IS NOT NULL AND final_output_hash IS NOT NULL
            AND reviewer IS NOT NULL AND review_note IS NOT NULL AND reviewed_at_us IS NOT NULL)
    ),
    UNIQUE (partition, request_id),
    FOREIGN KEY (partition, request_id) REFERENCES requests(partition, id)
) STRICT;

CREATE TABLE IF NOT EXISTS examples (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    partition TEXT NOT NULL,
    operation TEXT NOT NULL,
    operation_revision INTEGER NOT NULL CHECK (operation_revision >= 1),
    input_json TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_json TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ('accepted', 'corrected', 'challenge')),
    proposal_id TEXT UNIQUE REFERENCES proposals(id),
    receipt_json TEXT NOT NULL,
    receipt_hash TEXT NOT NULL UNIQUE,
    confirmed_at_us INTEGER NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS example_revocations (
    example_id TEXT PRIMARY KEY REFERENCES examples(id),
    revoked_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    revoked_at_us INTEGER NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS artifacts (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    partition TEXT NOT NULL,
    operation TEXT NOT NULL,
    operation_revision INTEGER NOT NULL CHECK (operation_revision >= 1),
    input_json TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_json TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    artifact_json TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    scope_hash TEXT NOT NULL,
    build_hash TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    evidence_snapshot_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('building', 'draft', 'verified', 'promoted', 'retired', 'suspended')
    ),
    support INTEGER NOT NULL CHECK (support >= 2),
    reviewer_count INTEGER NOT NULL CHECK (reviewer_count >= 1),
    span_seconds INTEGER NOT NULL CHECK (span_seconds >= 0),
    created_at_us INTEGER NOT NULL,
    verified_report_id TEXT,
    promoted_by TEXT,
    promoted_at_us INTEGER,
    promotion_hash TEXT,
    status_reason TEXT,
    CHECK (
        (status = 'promoted' AND verified_report_id IS NOT NULL
            AND promoted_by IS NOT NULL AND promoted_at_us IS NOT NULL
            AND promotion_hash IS NOT NULL)
        OR (status <> 'promoted' AND promotion_hash IS NULL)
    )
) STRICT;

CREATE TABLE IF NOT EXISTS artifact_evidence (
    artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    example_id TEXT NOT NULL REFERENCES examples(id),
    PRIMARY KEY (artifact_id, example_id)
) STRICT;

CREATE TABLE IF NOT EXISTS test_reports (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    artifact_hash TEXT NOT NULL,
    build_hash TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    evidence_snapshot_hash TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
    details_json TEXT NOT NULL,
    details_hash TEXT NOT NULL,
    test_count INTEGER NOT NULL CHECK (test_count >= 1),
    test_set_hash TEXT NOT NULL,
    created_at_us INTEGER NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS artifact_tests (
    report_id TEXT NOT NULL REFERENCES test_reports(id) DEFERRABLE INITIALLY DEFERRED,
    test_key TEXT NOT NULL,
    example_id TEXT REFERENCES examples(id),
    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
    detail TEXT NOT NULL,
    PRIMARY KEY (report_id, test_key)
) STRICT;

CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    partition TEXT NOT NULL,
    kind TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_us INTEGER NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS requests_scope
    ON requests(partition, operation, operation_revision, input_hash);
CREATE INDEX IF NOT EXISTS examples_scope
    ON examples(partition, operation, operation_revision, input_hash, confirmed_at_us);
CREATE INDEX IF NOT EXISTS artifacts_scope
    ON artifacts(partition, operation, operation_revision, input_hash, status);
CREATE INDEX IF NOT EXISTS artifacts_build
    ON artifacts(build_hash, status);
CREATE UNIQUE INDEX IF NOT EXISTS one_promoted_exact_scope
    ON artifacts(partition, operation, operation_revision, input_hash)
    WHERE status = 'promoted';
CREATE INDEX IF NOT EXISTS events_subject
    ON events(subject_type, subject_id, sequence);
CREATE INDEX IF NOT EXISTS events_partition
    ON events(partition, sequence);

CREATE TRIGGER IF NOT EXISTS examples_no_update
BEFORE UPDATE ON examples BEGIN
    SELECT RAISE(ABORT, 'examples are immutable');
END;
CREATE TRIGGER IF NOT EXISTS examples_no_delete
BEFORE DELETE ON examples BEGIN
    SELECT RAISE(ABORT, 'examples are immutable');
END;
CREATE TRIGGER IF NOT EXISTS revocations_no_update
BEFORE UPDATE ON example_revocations BEGIN
    SELECT RAISE(ABORT, 'revocations are immutable');
END;
CREATE TRIGGER IF NOT EXISTS revocations_no_delete
BEFORE DELETE ON example_revocations BEGIN
    SELECT RAISE(ABORT, 'revocations are immutable');
END;
CREATE TRIGGER IF NOT EXISTS artifact_evidence_no_update
BEFORE UPDATE ON artifact_evidence BEGIN
    SELECT RAISE(ABORT, 'artifact evidence edges are immutable');
END;
CREATE TRIGGER IF NOT EXISTS artifact_evidence_building_insert
BEFORE INSERT ON artifact_evidence
WHEN COALESCE((SELECT status FROM artifacts WHERE id = NEW.artifact_id), '') <> 'building'
BEGIN
    SELECT RAISE(ABORT, 'artifact evidence set is sealed');
END;
CREATE TRIGGER IF NOT EXISTS artifacts_status_lifecycle
BEFORE UPDATE OF status ON artifacts
WHEN NOT (
    NEW.status = OLD.status
    OR (OLD.status = 'building' AND NEW.status = 'draft')
    OR (OLD.status = 'draft' AND NEW.status IN ('verified', 'retired', 'suspended'))
    OR (OLD.status = 'verified' AND NEW.status IN ('draft', 'promoted', 'retired', 'suspended'))
    OR (OLD.status = 'promoted' AND NEW.status IN ('retired', 'suspended'))
)
BEGIN
    SELECT RAISE(ABORT, 'invalid artifact lifecycle transition');
END;
CREATE TRIGGER IF NOT EXISTS artifacts_build_fields_immutable
BEFORE UPDATE OF
    sequence, id, partition, operation, operation_revision, input_json, input_hash,
    output_json, output_hash, artifact_json, artifact_hash, scope_hash, build_hash,
    policy_json, policy_hash, evidence_snapshot_hash, support, reviewer_count,
    span_seconds, created_at_us
ON artifacts BEGIN
    SELECT RAISE(ABORT, 'artifact build fields are immutable');
END;
CREATE TRIGGER IF NOT EXISTS artifact_evidence_no_delete
BEFORE DELETE ON artifact_evidence BEGIN
    SELECT RAISE(ABORT, 'artifact evidence edges are immutable');
END;
CREATE TRIGGER IF NOT EXISTS test_reports_no_update
BEFORE UPDATE ON test_reports BEGIN
    SELECT RAISE(ABORT, 'test reports are immutable');
END;
CREATE TRIGGER IF NOT EXISTS test_reports_no_delete
BEFORE DELETE ON test_reports BEGIN
    SELECT RAISE(ABORT, 'test reports are immutable');
END;
CREATE TRIGGER IF NOT EXISTS artifact_tests_no_update
BEFORE UPDATE ON artifact_tests BEGIN
    SELECT RAISE(ABORT, 'artifact tests are immutable');
END;
CREATE TRIGGER IF NOT EXISTS artifact_tests_sealed_insert
BEFORE INSERT ON artifact_tests
WHEN EXISTS (SELECT 1 FROM test_reports WHERE id = NEW.report_id)
BEGIN
    SELECT RAISE(ABORT, 'artifact test set is sealed');
END;
CREATE TRIGGER IF NOT EXISTS artifact_tests_no_delete
BEFORE DELETE ON artifact_tests BEGIN
    SELECT RAISE(ABORT, 'artifact tests are immutable');
END;
CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events BEGIN
    SELECT RAISE(ABORT, 'events are append-only');
END;
CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events BEGIN
    SELECT RAISE(ABORT, 'events are append-only');
END;
CREATE TRIGGER IF NOT EXISTS schema_metadata_no_update
BEFORE UPDATE ON schema_metadata BEGIN
    SELECT RAISE(ABORT, 'schema metadata is immutable');
END;
CREATE TRIGGER IF NOT EXISTS schema_metadata_no_delete
BEFORE DELETE ON schema_metadata BEGIN
    SELECT RAISE(ABORT, 'schema metadata is immutable');
END;
"""

SCHEMA_FINGERPRINT = hashlib.sha256(SCHEMA.encode("utf-8")).hexdigest()
_EXPECTED_SCHEMA: dict[tuple[str, str], str] | None = None


def _execute_schema(connection: sqlite3.Connection) -> None:
    statement = ""
    for line in SCHEMA.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    if statement.strip():
        raise IntegrityError("internal schema contains an incomplete SQL statement")


def _schema_objects(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    return {
        (str(row[0]), str(row[1])): str(row[2])
        for row in connection.execute(
            """
            SELECT type, name, sql FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL
            ORDER BY type, name
            """
        ).fetchall()
    }


def _expected_schema() -> dict[tuple[str, str], str]:
    global _EXPECTED_SCHEMA
    if _EXPECTED_SCHEMA is None:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        try:
            _execute_schema(connection)
            _EXPECTED_SCHEMA = _schema_objects(connection)
        finally:
            connection.close()
    return _EXPECTED_SCHEMA


def _validate_ledger(connection: sqlite3.Connection) -> None:
    problems = connection.execute("PRAGMA integrity_check").fetchall()
    if [row[0] for row in problems] != ["ok"]:
        raise IntegrityError("SQLite integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise IntegrityError("SQLite foreign-key check failed")
    try:
        fingerprint = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = ?",
            (f"schema-v{SCHEMA_VERSION}",),
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise IntegrityError("database schema metadata is missing") from exc
    if fingerprint is None or fingerprint[0] != SCHEMA_FINGERPRINT:
        raise IntegrityError("database schema fingerprint mismatch")
    if _schema_objects(connection) != _expected_schema():
        raise IntegrityError("live database schema does not match the runtime schema")


class Store:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        if sqlite3.sqlite_version_info < MIN_SQLITE:
            version = ".".join(str(part) for part in sqlite3.sqlite_version_info)
            raise IntegrityError(f"SQLite {version} is too old; 3.37+ is required")
        try:
            self.path = Path(path)
        except (TypeError, ValueError) as exc:
            raise ValidationError("database path must be text or a path-like value") from exc
        path_text = str(self.path)
        try:
            path_text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationError("database path must contain valid Unicode scalar values") from exc
        if "\0" in path_text:
            raise ValidationError("database path must not contain NUL")
        if path_text == ":memory:":
            raise ValidationError("the durable ledger does not support ':memory:' databases")
        if self.path.is_symlink():
            raise ValidationError("database path must not be a symbolic link")
        if self.path.exists() and not self.path.is_file():
            raise ValidationError("database path must identify a regular file")
        if not self.path.parent.is_dir():
            raise ValidationError("database parent directory does not exist")
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValidationError("database path must identify a non-symlink regular file")
        except (OSError, ValueError, UnicodeError) as exc:
            raise ValidationError("database path could not be created safely") from exc
        else:
            os.close(descriptor)
        if self.path.is_symlink():
            raise ValidationError("database path must not be a symbolic link")
        try:
            self._initialize()
        except CementError:
            raise
        except sqlite3.OperationalError as exc:
            raise StateError("database is busy or unavailable during initialization") from exc
        except sqlite3.DatabaseError as exc:
            raise IntegrityError("database could not be validated as a Cement ledger") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = EXTRA")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.execute("PRAGMA trusted_schema = OFF")
        if hasattr(connection, "setconfig"):
            defensive = getattr(sqlite3, "SQLITE_DBCONFIG_DEFENSIVE", None)
            trusted = getattr(sqlite3, "SQLITE_DBCONFIG_TRUSTED_SCHEMA", None)
            if defensive is not None:
                connection.setconfig(defensive, True)
            if trusted is not None:
                connection.setconfig(trusted, False)
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                current = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if current not in (0, SCHEMA_VERSION):
                    raise IntegrityError(
                        f"database schema {current} is unsupported; expected {SCHEMA_VERSION}"
                    )
                if current == 0:
                    if (
                        connection.execute("SELECT 1 FROM sqlite_schema LIMIT 1").fetchone()
                        is not None
                        or int(connection.execute("PRAGMA application_id").fetchone()[0]) != 0
                    ):
                        raise IntegrityError(
                            "refusing to initialize a non-empty unrecognized SQLite database"
                        )
                    _execute_schema(connection)
                    connection.execute(
                        """
                        INSERT INTO schema_metadata(key, value) VALUES (?, ?)
                        """,
                        (f"schema-v{SCHEMA_VERSION}", SCHEMA_FINGERPRINT),
                    )
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                _validate_ledger(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            # Journal policy changes only after identity + integrity are established.
            connection.execute("PRAGMA journal_mode = DELETE")
        finally:
            connection.close()

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        except CementError:
            raise
        except sqlite3.OperationalError as exc:
            raise StateError("database is busy or unavailable") from exc
        except sqlite3.DatabaseError as exc:
            raise IntegrityError("database operation failed an integrity check") from exc
        finally:
            if connection is not None:
                connection.close()
