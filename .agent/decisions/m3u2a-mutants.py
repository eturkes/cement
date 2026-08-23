#!/usr/bin/env python
"""Mutation battery for M3.2a's read-capability predicates.

A green suite is never closure for a hardening: deleting a behavior together with its pin leaves
the gate green and the test count unchanged. This script is the mechanical form of the closure
criterion - every enforcement predicate must have a committed test that fails when that predicate
alone is removed.

    uv run python .agent/decisions/m3u2a-mutants.py [--id ID ...] [--full]

Each mutant is addressed by a UNIQUE anchor string, never a line number. The run asserts the
anchor occurs exactly once, asserts the patch changed the file, purges `__pycache__` under
`PYTHONDONTWRITEBYTECODE=1` (CPython invalidates bytecode on `(mtime, size)`, so a length-
preserving edit inside one mtime-second would otherwise run the ORIGINAL code and report a live
mutant as surviving), restores byte-exactly, and proves the restore with a hash compare.

Verdicts: `killed` = the unit battery fails. `survived` = the unit battery passes, and with
`--full` the whole suite passes too. Exit 0 only when every mutant is killed or is a declared
equivalent.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve()
while not (ROOT / "pyproject.toml").exists():
    if ROOT == ROOT.parent:
        raise SystemExit("pyproject.toml not found above this script")
    ROOT = ROOT.parent

TARGET = ROOT / "src" / "cement_runtime" / "store.py"
BATTERY = ["tests.test_read_capability_battery", "tests.test_read_capability_census"]


@dataclass(frozen=True)
class Mutant:
    identifier: str
    old: str
    new: str
    obligation: str
    equivalent: bool = False


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "authorizer-not-installed",
        "                connection.set_authorizer(_read_authorizer)",
        "                pass",
        "B2",
    ),
    Mutant(
        "mode-ro-dropped",
        '                f"{self.path.absolute().as_uri()}?mode=ro",',
        '                f"{self.path.absolute().as_uri()}",',
        "B3",
    ),
    Mutant(
        "raw-uri-concatenation",
        '                f"{self.path.absolute().as_uri()}?mode=ro",',
        '                f"file:{self.path.absolute()}?mode=ro",',
        "B4",
    ),
    Mutant(
        "release-keeps-authorizer",
        "    if enforced:\n        connection.set_authorizer(None)\n    connection.rollback()",
        "    if enforced:\n        pass\n    connection.rollback()",
        "B1",
    ),
    Mutant(
        "release-commits",
        "    if enforced:\n        connection.set_authorizer(None)\n    connection.rollback()",
        "    if enforced:\n        connection.set_authorizer(None)\n    connection.commit()",
        "B1",
    ),
    Mutant(
        "rollback-allowed",
        '_READ_AUTHORIZED_TRANSACTIONS = frozenset({"BEGIN"})',
        '_READ_AUTHORIZED_TRANSACTIONS = frozenset({"BEGIN", "ROLLBACK"})',
        "B12",
    ),
    Mutant(
        "commit-allowed",
        '_READ_AUTHORIZED_TRANSACTIONS = frozenset({"BEGIN"})',
        '_READ_AUTHORIZED_TRANSACTIONS = frozenset({"BEGIN", "COMMIT"})',
        "B1/B13",
    ),
    Mutant(
        "savepoint-granted-back",
        "    return sqlite3.SQLITE_DENY\n\n\ndef _release(",
        "    if action == sqlite3.SQLITE_SAVEPOINT:\n        return sqlite3.SQLITE_OK\n"
        "    return sqlite3.SQLITE_DENY\n\n\ndef _release(",
        "B18",
    ),
    Mutant(
        "recursive-grant-dropped",
        "        sqlite3.SQLITE_RECURSIVE,\n",
        "",
        "B17",
    ),
    Mutant(
        "pragma-graded-by-shape",
        '        name = (argument or "").lower()\n'
        "        if name in _READ_ONLY_PRAGMA_QUERIES:\n"
        "            return sqlite3.SQLITE_OK\n"
        "        if name in _READ_ONLY_PRAGMA_READS and value is None:\n"
        "            return sqlite3.SQLITE_OK\n"
        "        return sqlite3.SQLITE_DENY",
        "        if value is None:\n"
        "            return sqlite3.SQLITE_OK\n"
        "        return sqlite3.SQLITE_DENY",
        "B7",
    ),
    Mutant(
        "pragma-value-guard-dropped",
        "        if name in _READ_ONLY_PRAGMA_READS and value is None:",
        "        if name in _READ_ONLY_PRAGMA_READS:",
        "B7",
    ),
    Mutant(
        "denial-code-auth-dropped",
        "_READ_CAPABILITY_DENIALS = frozenset({sqlite3.SQLITE_AUTH, sqlite3.SQLITE_READONLY})",
        "_READ_CAPABILITY_DENIALS = frozenset({sqlite3.SQLITE_READONLY})",
        "B8/B9",
    ),
    Mutant(
        "denial-code-readonly-dropped",
        "_READ_CAPABILITY_DENIALS = frozenset({sqlite3.SQLITE_AUTH, sqlite3.SQLITE_READONLY})",
        "_READ_CAPABILITY_DENIALS = frozenset({sqlite3.SQLITE_AUTH})",
        "B19",
    ),
    Mutant(
        "cantopen-branch-dropped",
        "        if code == sqlite3.SQLITE_CANTOPEN:\n"
        '            return IntegrityError("ledger file is missing or unreadable")\n',
        "",
        "B10",
    ),
    Mutant(
        "read-capability-never-requested",
        "            connection = self._connect(read_only=not write)",
        "            connection = self._connect(read_only=False)",
        "B1/B2/B3",
    ),
    Mutant(
        "write-path-loses-immediate",
        '            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")',
        '            connection.execute("BEGIN")',
        "B15",
    ),
    Mutant(
        "busy-timeout-pragma-deleted",
        '            connection.execute("PRAGMA busy_timeout = 10000")\n',
        "",
        "B6",
    ),
    Mutant(
        "setconfig-trusted-deleted",
        "                if trusted is not None:\n"
        "                    connection.setconfig(trusted, False)\n",
        "",
        "B6",
    ),
    Mutant(
        "temp-store-pragma-deleted",
        '            connection.execute("PRAGMA temp_store = MEMORY")\n',
        "",
        "B5",
    ),
)


def run(selection: list[str], *, full: bool) -> int:
    pristine = TARGET.read_text(encoding="utf-8")
    digest = hashlib.sha256(pristine.encode("utf-8")).hexdigest()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def purge() -> None:
        for cache in ROOT.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)

    def suite(modules: list[str]) -> bool:
        purge()
        completed = subprocess.run(
            ["uv", "run", "python", "-m", "unittest", *modules],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0

    print("control: pristine battery ...", flush=True)
    if not suite(BATTERY):
        print("CONTROL FAILED - the battery is not green before mutation", file=sys.stderr)
        return 1
    print("control: green")

    chosen = [m for m in MUTANTS if not selection or m.identifier in selection]
    survivors: list[Mutant] = []
    for mutant in chosen:
        count = pristine.count(mutant.old)
        if count != 1:
            print(f"ANCHOR-MISS {mutant.identifier}: anchor occurs {count} times", file=sys.stderr)
            return 1
        mutated = pristine.replace(mutant.old, mutant.new)
        if mutated == pristine:
            print(f"IDENTITY {mutant.identifier}: patch changed nothing", file=sys.stderr)
            return 1
        TARGET.write_text(mutated, encoding="utf-8")
        try:
            killed = not suite(BATTERY)
            verdict = "killed" if killed else "survived"
            if not killed and full:
                verdict = "survived" if suite(["discover", "-s", "tests", "-t", "."]) else "killed-by-suite"
        finally:
            TARGET.write_text(pristine, encoding="utf-8")
            restored = hashlib.sha256(TARGET.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            if restored != digest:
                print(f"RESTORE FAILED after {mutant.identifier}", file=sys.stderr)
                return 1
        tag = " (declared equivalent)" if mutant.equivalent else ""
        print(f"{verdict:16} {mutant.identifier:32} {mutant.obligation}{tag}", flush=True)
        if verdict.startswith("survived") and not mutant.equivalent:
            survivors.append(mutant)

    purge()
    print(f"\nmutants={len(chosen)} survivors={len(survivors)}")
    for mutant in survivors:
        print(f"SURVIVOR {mutant.identifier} -> obligation {mutant.obligation} does not pin it")
    return 1 if survivors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", default=[], dest="ids")
    parser.add_argument("--full", action="store_true", help="re-run the whole suite on a survivor")
    arguments = parser.parse_args(argv)
    return run(arguments.ids, full=arguments.full)


if __name__ == "__main__":
    raise SystemExit(main())
