#!/usr/bin/env python
"""Mutation battery for every predicate M3.3 adds. Discharges contract D30.

A green suite is never closure: deleting a behaviour together with its pin leaves the gate green
and the test count unchanged. This script is the mechanical form of D30 - every obligation must
have a committed test that fails when the code discharging it alone is removed.

    uv run python .agent/decisions/m3u3-mutants.py [--id ID ...] [--verdict MODULE ...] [--full]

Default verdict modules are the unit's own suites, which keeps a sweep to seconds per mutant
instead of the full suite's ~204 s. `--full` re-runs the whole suite on a survivor, which
separates "the battery does not pin it" from "nothing pins it".

Each mutant is addressed by a UNIQUE anchor string, never a line number or an occurrence index.
The run asserts the anchor occurs exactly once, asserts the patch changed the file, purges
`__pycache__` under `PYTHONDONTWRITEBYTECODE=1` (CPython invalidates bytecode on `(mtime, size)`,
so a length-preserving edit inside one mtime-second would otherwise run the ORIGINAL code and
report a live mutant as surviving), restores byte-exactly, and proves the restore by hash.

Verdicts: `killed` = a verdict module fails. `survived` = it passes. `killed-by-suite` = only the
wider suite catches it, which is a battery coverage gap. Exit 0 only when every mutant is killed
by a verdict module or is a declared equivalent.
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

SYSTEM = "src/cement_runtime/system.py"
ERRORS = "src/cement_runtime/errors.py"
BATTERY = ["tests.test_submission", "tests.test_submission_battery"]

# --- anchors, each proved unique by the runner ------------------------------

CANDIDATE_TYPE = "        if type(candidate) is not Candidate:\n"
PROVENANCE_MAPPING = (
    "        if not isinstance(candidate.provenance, Mapping):\n"
    '            raise ValidationError("candidate provenance must be a mapping")\n'
)
PROVENANCE_BOUND = (
    "        # source path contains the same failure with every other adapter defect.\n"
    "        provenance = canonicalize(dict(candidate.provenance), max_bytes=65_536)\n"
)
INIT_NO_PREFLIGHT = (
    "        # A source is classified where it is invoked, never here: reading\n"
    "        # ``propose`` off a descriptor already executes caller-supplied code, so a\n"
    "        # constructor pre-flight is the very hazard it looks like a guard against.\n"
)
READ_TRANSACTION = (
    "    def _submission_revision(self, partition: str, operation: str) -> int:\n"
    "        with self.store.transaction() as connection:\n"
)
READ_QUERY = (
    "            registered = connection.execute(\n"
    '                "SELECT revision FROM operations WHERE partition = ? AND name = ?",\n'
    "                (partition, operation),\n"
    "            ).fetchone()\n"
    "        if registered is None:\n"
)
SEAM_QUERY = (
    "            registered = connection.execute(\n"
    '                "SELECT revision FROM operations WHERE partition = ? AND name = ?",\n'
    "                (partition, operation),\n"
    "            ).fetchone()\n"
    "            if registered is None:\n"
    '                raise NotFoundError("operation is not registered in this partition")\n'
    '            revision = int(registered["revision"])\n'
    "            if expected_revision is not None and revision != expected_revision:\n"
)
REVISION_GUARD = (
    "            if expected_revision is not None and revision != expected_revision:\n"
    '                raise StateError("operation revision changed before proposal submission")\n'
)
SEAM_IDS = "            proposal_id = _new_id(\"prop\")\n            created = self._now()\n"
SEAM_WRITE_OPEN = (
    "        # generation — holds an expectation the seam can find stale.\n"
    "        with self.store.transaction(write=True) as connection:\n"
)
REQUEST_STATUS = "                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)\n"
EVENT_WRITE = (
    "            status_sequence = _event(\n"
    "                connection,\n"
    "                partition=partition,\n"
    '                kind="proposal.created",\n'
    '                subject_type="proposal",\n'
    "                subject_id=proposal_id,\n"
    "                payload={},\n"
    "                now_us=created,\n"
    "            )\n"
)
PROPOSAL_BIND = (
    "                    proposed.text,\n"
    "                    proposed.digest,\n"
    "                    provenance.text,\n"
    "                    provenance.digest,\n"
    "                    created,\n"
    "                    status_sequence,\n"
)
DIRECT_SIGNATURE = (
    "        input_value: object,\n"
    "        *,\n"
    "        candidate: Candidate,\n"
    "    ) -> str:\n"
)
DIRECT_VALIDATION = (
    '        partition = _name(partition, "partition")\n'
    '        operation = _name(operation, "operation")\n'
    "        input_json = canonicalize(input_value)\n"
    "        proposed, provenance = self._canonical_candidate(candidate)\n"
)
DIRECT_CALL = (
    "        return self._persist_proposal(\n"
    "            partition=partition,\n"
    "            operation=operation,\n"
    "            expected_revision=None,\n"
    '            request_id=_new_id("req"),\n'
)
SOURCE_PRELUDE = (
    "        input_json = canonicalize(input_value)\n"
    "        source = self.candidate_source\n"
    "        if source is None:\n"
    '            raise StateError("candidate source is not configured")\n'
    "        revision = self._submission_revision(partition, operation)\n"
    '        request_id = _new_id("req")\n'
)
SOURCE_CALL = (
    "        try:\n"
    "            candidate = source.propose(\n"
    "                CandidateRequest(\n"
    "                    partition=partition,\n"
    "                    operation=operation,\n"
    "                    operation_revision=revision,\n"
    "                    request_id=request_id,\n"
    "                    input=input_json.value,\n"
    "                )\n"
    "            )\n"
    "            generated = self._canonical_candidate(candidate)\n"
    "        except Exception:\n"
    "            generated = None\n"
)
CONTAINED_COMMENT = (
    "        # Raising outside the handler leaves __context__ itself empty, so no\n"
    "        # adapter frame, class, or message survives into the caller's traceback.\n"
)
CONTAINED_RAISE = (
    "        if generated is None:\n"
    '            raise CandidateSourceError("candidate source failed") from None\n'
)
SOURCE_PERSIST = (
    "        return self._persist_proposal(\n"
    "            partition=partition,\n"
    "            operation=operation,\n"
    "            expected_revision=revision,\n"
)
# --- S4 anchors: the six mutants the carried review rows demanded ------------

SEAM_HEADER = (
    "    def _persist_proposal(\n"
    "        self,\n"
    "        *,\n"
    "        partition: str,\n"
    "        operation: str,\n"
    "        expected_revision: int | None,\n"
    "        request_id: str,\n"
    "        input_json: CanonicalJSON,\n"
    "        proposed: CanonicalJSON,\n"
    "        provenance: CanonicalJSON,\n"
    "    ) -> str:\n"
    "        # The proposal binds to the revision current under the write lock. Only a\n"
)
# One transaction, TWO helpers: `_persist_proposal` survives as a wrapper both
# public methods still call, so every behavioural pin and the runtime seam spy
# stay green while the seam has stopped owning a single write.
SEAM_SPLIT_WRITER = (
    "    def _persist_proposal(\n"
    "        self,\n"
    "        *,\n"
    "        partition: str,\n"
    "        operation: str,\n"
    "        expected_revision: int | None,\n"
    "        request_id: str,\n"
    "        input_json: CanonicalJSON,\n"
    "        proposed: CanonicalJSON,\n"
    "        provenance: CanonicalJSON,\n"
    "    ) -> str:\n"
    "        return self._write_submission_rows(\n"
    "            partition=partition,\n"
    "            operation=operation,\n"
    "            expected_revision=expected_revision,\n"
    "            request_id=request_id,\n"
    "            input_json=input_json,\n"
    "            proposed=proposed,\n"
    "            provenance=provenance,\n"
    "        )\n"
    "\n"
    "    def _write_submission_rows(\n"
    "        self,\n"
    "        *,\n"
    "        partition: str,\n"
    "        operation: str,\n"
    "        expected_revision: int | None,\n"
    "        request_id: str,\n"
    "        input_json: CanonicalJSON,\n"
    "        proposed: CanonicalJSON,\n"
    "        provenance: CanonicalJSON,\n"
    "    ) -> str:\n"
    "        # The proposal binds to the revision current under the write lock. Only a\n"
)
SEAM_MINT = (
    '            proposal_id = _new_id("prop")\n'
    "            created = self._now()\n"
    "            connection.execute(\n"
    '                """\n'
    "                INSERT INTO requests(\n"
)
DIRECT_SIG_TAIL = (
    "        *,\n"
    "        candidate: Candidate,\n"
    "    ) -> str:\n"
)
SOURCE_SIG_TAIL = (
    "        input_value: object,\n"
    "    ) -> str:\n"
    '        """Ask the configured candidate source for a candidate, then submit it.\n'
)

ERROR_DOC = (
    '    """The candidate source failed to produce a usable candidate.\n'
    "\n"
    "    A source adapter raises this error to declare its own failure.\n"
    "    ``System.propose`` also raises it when the source fails. The instance that\n"
    "    ``System.propose`` raises carries no detail from the source: no class, no\n"
    "    message, no cause, no context, and no adapter frame.\n"
)


@dataclass(frozen=True)
class Mutant:
    identifier: str
    path: str
    old: str
    new: str
    obligation: str
    equivalent: bool = False


MUTANTS: tuple[Mutant, ...] = (
    # --- _canonical_candidate: the DIRECT path's own validation (D43, D44) ---
    Mutant(
        "candidate-type-check-deleted",
        SYSTEM,
        CANDIDATE_TYPE,
        "        if False:\n",
        "D43 candidate type domain",
    ),
    Mutant(
        "candidate-type-widened-to-isinstance",
        SYSTEM,
        CANDIDATE_TYPE,
        "        if not isinstance(candidate, Candidate):\n",
        "D43 candidate type domain",
    ),
    Mutant(
        "provenance-mapping-guard-deleted",
        SYSTEM,
        PROVENANCE_MAPPING,
        "        if False:\n"
        '            raise ValidationError("candidate provenance must be a mapping")\n',
        "D43 provenance mapping domain",
    ),
    Mutant(
        "provenance-mapping-widened-to-iterable",
        SYSTEM,
        PROVENANCE_MAPPING,
        "        if not isinstance(candidate.provenance, (Mapping, list)):\n"
        '            raise ValidationError("candidate provenance must be a mapping")\n',
        "D43 provenance mapping domain",
    ),
    Mutant(
        "provenance-bound-dropped",
        SYSTEM,
        PROVENANCE_BOUND,
        PROVENANCE_BOUND.replace(", max_bytes=65_536", ""),
        "D44 provenance byte bound",
    ),
    # --- System.__init__: the pre-flight D37 deleted -------------------------
    Mutant(
        "init-preflight-restored",
        SYSTEM,
        INIT_NO_PREFLIGHT,
        "        if candidate_source is not None and not callable(\n"
        '            getattr(candidate_source, "propose", None)\n'
        "        ):\n"
        '            raise ValidationError("candidate_source must provide a callable propose method")\n',
        "D37 no constructor pre-flight",
    ),
    # --- _submission_revision: the pre-invocation read (D13, D21, D35) -------
    Mutant(
        "pre-read-becomes-write",
        SYSTEM,
        READ_TRANSACTION,
        READ_TRANSACTION.replace("transaction()", "transaction(write=True)"),
        "D11/D13",
    ),
    Mutant(
        "pre-read-partition-scope-weakened",
        SYSTEM,
        READ_QUERY,
        READ_QUERY.replace("partition = ? AND name = ?", "partition LIKE ? AND name = ?"),
        "D13",
    ),
    Mutant(
        "pre-read-name-scope-weakened",
        SYSTEM,
        READ_QUERY,
        READ_QUERY.replace("partition = ? AND name = ?", "partition = ? AND name LIKE ?"),
        "D13",
    ),
    Mutant(
        "pre-read-missing-operation-admitted",
        SYSTEM,
        READ_QUERY + '            raise NotFoundError("operation is not registered in this partition")\n',
        READ_QUERY.replace("        if registered is None:\n", "        if registered is None:\n            return 0\n"),
        "D21/D35",
    ),
    # --- _persist_proposal: the single writer (D01-D03, D06, D12, D42) ------
    Mutant(
        "seam-partition-scope-weakened",
        SYSTEM,
        SEAM_QUERY,
        SEAM_QUERY.replace("partition = ? AND name = ?", "partition LIKE ? AND name = ?"),
        "D13",
    ),
    Mutant(
        "seam-name-scope-weakened",
        SYSTEM,
        SEAM_QUERY,
        SEAM_QUERY.replace("partition = ? AND name = ?", "partition = ? AND name LIKE ?"),
        "D13",
    ),
    Mutant(
        "seam-missing-operation-admitted",
        SYSTEM,
        SEAM_QUERY,
        SEAM_QUERY.replace(
            "            if registered is None:\n", "            if registered is False:\n"
        ),
        "D21",
    ),
    Mutant(
        "revision-guard-unconditional",
        SYSTEM,
        REVISION_GUARD,
        "            if revision != expected_revision:\n"
        '                raise StateError("operation revision changed before proposal submission")\n',
        "V-D12",
    ),
    Mutant(
        "revision-guard-deleted",
        SYSTEM,
        REVISION_GUARD,
        "            if False:\n"
        '                raise StateError("operation revision changed before proposal submission")\n',
        "D12",
    ),
    Mutant(
        "revision-guard-inverted",
        SYSTEM,
        REVISION_GUARD,
        "            if expected_revision is not None and revision == expected_revision:\n"
        '                raise StateError("operation revision changed before proposal submission")\n',
        "D12",
    ),
    Mutant(
        "proposal-id-prefix-changed",
        SYSTEM,
        SEAM_IDS,
        '            proposal_id = _new_id("req")\n            created = self._now()\n',
        "P02/D42",
    ),
    Mutant(
        "clock-read-per-row",
        SYSTEM,
        PROPOSAL_BIND,
        PROPOSAL_BIND.replace("                    created,\n", "                    self._now(),\n"),
        "D17/Y05",
    ),
    Mutant(
        "request-row-status-generating",
        SYSTEM,
        REQUEST_STATUS,
        "                ) VALUES (?, ?, ?, ?, ?, ?, 'generating', ?, ?, ?)\n",
        "D02",
    ),
    Mutant(
        "event-kind-renamed",
        SYSTEM,
        EVENT_WRITE,
        EVENT_WRITE.replace('kind="proposal.created"', 'kind="proposal.submitted"'),
        "D03",
    ),
    Mutant(
        "event-publishes-request-id",
        SYSTEM,
        EVENT_WRITE,
        EVENT_WRITE.replace("payload={}", 'payload={"request_id": request_id}'),
        "D22",
    ),
    Mutant(
        "event-subject-is-request",
        SYSTEM,
        EVENT_WRITE,
        EVENT_WRITE.replace("subject_id=proposal_id", "subject_id=request_id"),
        "D03/D22",
    ),
    Mutant(
        "status-sequence-unbound",
        SYSTEM,
        PROPOSAL_BIND,
        PROPOSAL_BIND.replace("                    status_sequence,\n", "                    0,\n"),
        "D42",
    ),
    Mutant(
        "provenance-columns-swapped",
        SYSTEM,
        PROPOSAL_BIND,
        PROPOSAL_BIND.replace(
            "                    provenance.text,\n                    provenance.digest,\n",
            "                    provenance.digest,\n                    provenance.text,\n",
        ),
        "D42",
    ),
    Mutant(
        "seam-write-becomes-two-transactions",
        SYSTEM,
        SEAM_WRITE_OPEN,
        "        with self.store.transaction(write=True) as _probe:\n"
        "            _probe.execute(\"SELECT 1\")\n"
        "        with self.store.transaction(write=True) as connection:\n",
        "D01/D06/D15",
    ),
    # --- submit_proposal: the DIRECT entry point (P01, D07, V-D12) ----------
    Mutant(
        "direct-keyword-marker-dropped",
        SYSTEM,
        DIRECT_SIGNATURE,
        "        input_value: object,\n        candidate: Candidate,\n    ) -> str:\n",
        "P01",
    ),
    Mutant(
        "direct-candidate-defaulted",
        SYSTEM,
        DIRECT_SIGNATURE,
        "        input_value: object,\n        *,\n        candidate: Candidate | None = None,\n    ) -> str:\n",
        "P01/D10",
    ),
    Mutant(
        "direct-validation-order-partition-operation",
        SYSTEM,
        DIRECT_VALIDATION,
        '        operation = _name(operation, "operation")\n'
        '        partition = _name(partition, "partition")\n'
        "        input_json = canonicalize(input_value)\n"
        "        proposed, provenance = self._canonical_candidate(candidate)\n",
        "D07/D08",
    ),
    Mutant(
        "direct-validation-order-input-candidate",
        SYSTEM,
        DIRECT_VALIDATION,
        '        partition = _name(partition, "partition")\n'
        '        operation = _name(operation, "operation")\n'
        "        proposed, provenance = self._canonical_candidate(candidate)\n"
        "        input_json = canonicalize(input_value)\n",
        "D07",
    ),
    Mutant(
        "direct-validation-order-operation-input",
        SYSTEM,
        DIRECT_VALIDATION,
        '        partition = _name(partition, "partition")\n'
        "        input_json = canonicalize(input_value)\n"
        '        operation = _name(operation, "operation")\n'
        "        proposed, provenance = self._canonical_candidate(candidate)\n",
        "D07",
    ),
    Mutant(
        "direct-captures-a-revision",
        SYSTEM,
        DIRECT_CALL,
        "        return self._persist_proposal(\n"
        "            partition=partition,\n"
        "            operation=operation,\n"
        "            expected_revision=self._submission_revision(partition, operation),\n"
        '            request_id=_new_id("req"),\n',
        "V-D12",
    ),
    # --- propose: the SOURCE entry point (D05, D35-D40, D18, D19) ----------
    Mutant(
        "source-attribute-read-twice",
        SYSTEM,
        SOURCE_PRELUDE,
        "        input_json = canonicalize(input_value)\n"
        "        if self.candidate_source is None:\n"
        '            raise StateError("candidate source is not configured")\n'
        "        revision = self._submission_revision(partition, operation)\n"
        '        request_id = _new_id("req")\n'
        "        source = self.candidate_source\n",
        "D36",
    ),
    Mutant(
        "missing-source-check-after-lookup",
        SYSTEM,
        SOURCE_PRELUDE,
        "        input_json = canonicalize(input_value)\n"
        "        source = self.candidate_source\n"
        "        revision = self._submission_revision(partition, operation)\n"
        "        if source is None:\n"
        '            raise StateError("candidate source is not configured")\n'
        '        request_id = _new_id("req")\n',
        "D21/D35",
    ),
    Mutant(
        "request-input-is-caller-object",
        SYSTEM,
        SOURCE_CALL,
        SOURCE_CALL.replace("input=input_json.value", "input=input_value"),
        "D40",
    ),
    Mutant(
        "source-invoked-twice",
        SYSTEM,
        SOURCE_CALL,
        SOURCE_CALL.replace(
            "            generated = self._canonical_candidate(candidate)\n",
            "            candidate = source.propose(\n"
            "                CandidateRequest(\n"
            "                    partition=partition,\n"
            "                    operation=operation,\n"
            "                    operation_revision=revision,\n"
            "                    request_id=request_id,\n"
            "                    input=input_json.value,\n"
            "                )\n"
            "            )\n"
            "            generated = self._canonical_candidate(candidate)\n",
        ),
        "D05",
    ),
    Mutant(
        "return-validation-outside-containment",
        SYSTEM,
        SOURCE_CALL,
        "        try:\n"
        "            candidate = source.propose(\n"
        "                CandidateRequest(\n"
        "                    partition=partition,\n"
        "                    operation=operation,\n"
        "                    operation_revision=revision,\n"
        "                    request_id=request_id,\n"
        "                    input=input_json.value,\n"
        "                )\n"
        "            )\n"
        "        except Exception:\n"
        "            candidate = None\n"
        "        generated = None if candidate is None else self._canonical_candidate(candidate)\n",
        "D38",
    ),
    Mutant(
        "catch-widened-to-baseexception",
        SYSTEM,
        SOURCE_CALL,
        SOURCE_CALL.replace("        except Exception:\n", "        except BaseException:\n"),
        "D39",
    ),
    Mutant(
        "catch-narrowed-to-declared-error",
        SYSTEM,
        SOURCE_CALL,
        SOURCE_CALL.replace(
            "        except Exception:\n",
            "        except (CandidateSourceError, ValidationError):\n",
        ),
        "D19",
    ),
    Mutant(
        "raise-moved-inside-handler",
        SYSTEM,
        SOURCE_CALL + CONTAINED_COMMENT + CONTAINED_RAISE,
        SOURCE_CALL.replace(
            "            generated = None\n",
            '            raise CandidateSourceError("candidate source failed") from None\n',
        ),
        "V-D18",
    ),
    Mutant(
        "contained-raise-keeps-cause",
        SYSTEM,
        CONTAINED_RAISE,
        "        if generated is None:\n"
        '            raise CandidateSourceError("candidate source failed")\n',
        "D18",
    ),
    Mutant(
        "source-path-drops-its-revision-guard",
        SYSTEM,
        SOURCE_PERSIST,
        "        return self._persist_proposal(\n"
        "            partition=partition,\n"
        "            operation=operation,\n"
        "            expected_revision=None,\n",
        "D12",
    ),
    # --- errors.py: the published contract (D31) ---------------------------
    Mutant(
        "candidate-source-error-doc-reverted",
        ERRORS,
        ERROR_DOC,
        '    """The supervised fallback source failed before creating a proposal.\n'
        "\n"
        "    A source adapter raises this error to declare its own failure.\n"
        "    ``System.propose`` also raises it when the source fails. It carries no detail\n"
        "    from the source.\n",
        "D31",
    ),
    # --- S4: the six mutants the carried review rows demanded ---------------
    Mutant(
        "seam-split-into-two-helpers",
        SYSTEM,
        SEAM_HEADER,
        SEAM_SPLIT_WRITER,
        "D06 the seam is the sole writer",
    ),
    # A fourteenth write the nine-table footprint could not see.
    Mutant(
        "seam-writes-schema-metadata",
        SYSTEM,
        SEAM_MINT,
        "            connection.execute(\n"
        '                "INSERT OR REPLACE INTO schema_metadata(key, value) VALUES (?, ?)",\n'
        '                ("last-proposal", request_id),\n'
        "            )\n" + SEAM_MINT,
        "D01 footprint over every declared application table",
    ),
    # A forbidden read that lowercase substring matching cannot see.
    Mutant(
        "seam-reads-artifacts-uppercase",
        SYSTEM,
        SEAM_MINT,
        '            connection.execute("SELECT count(*) FROM ARTIFACTS").fetchone()\n'
        + SEAM_MINT,
        "D17 no artifact, example or function-table read",
    ),
    # Three annotation weakenings no behavioural test can observe.
    Mutant(
        "direct-candidate-annotation-weakened",
        SYSTEM,
        DIRECT_SIG_TAIL,
        DIRECT_SIG_TAIL.replace("candidate: Candidate", "candidate: object"),
        "P01 frozen public shape",
    ),
    Mutant(
        "direct-return-annotation-weakened",
        SYSTEM,
        DIRECT_SIG_TAIL,
        DIRECT_SIG_TAIL.replace(") -> str:", ") -> object:"),
        "P01 frozen public shape",
    ),
    Mutant(
        "source-return-annotation-weakened",
        SYSTEM,
        SOURCE_SIG_TAIL,
        SOURCE_SIG_TAIL.replace(") -> str:", ") -> object:"),
        "P01 frozen public shape",
    ),
)


def run(selection: list[str], verdict_modules: list[str], *, full: bool) -> int:
    targets = sorted({mutant.path for mutant in MUTANTS})
    pristine = {path: (ROOT / path).read_text(encoding="utf-8") for path in targets}
    digests = {
        path: hashlib.sha256(text.encode("utf-8")).hexdigest() for path, text in pristine.items()
    }
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

    print(f"control: pristine verdict modules {verdict_modules} ...", flush=True)
    if not suite(verdict_modules):
        print("CONTROL FAILED - the verdict modules are not green before mutation", file=sys.stderr)
        return 1
    print("control: green")

    chosen = [m for m in MUTANTS if not selection or m.identifier in selection]
    survivors: list[Mutant] = []
    gaps: list[Mutant] = []
    for mutant in chosen:
        source = pristine[mutant.path]
        count = source.count(mutant.old)
        if count != 1:
            print(f"ANCHOR-MISS {mutant.identifier}: anchor occurs {count} times", file=sys.stderr)
            return 1
        mutated = source.replace(mutant.old, mutant.new)
        if mutated == source:
            print(f"IDENTITY {mutant.identifier}: patch changed nothing", file=sys.stderr)
            return 1
        (ROOT / mutant.path).write_text(mutated, encoding="utf-8")
        try:
            verdict = "killed" if not suite(verdict_modules) else "survived"
            if verdict == "survived" and full:
                verdict = (
                    "survived"
                    if suite(["discover", "-s", "tests", "-t", "."])
                    else "killed-by-suite"
                )
        finally:
            (ROOT / mutant.path).write_text(source, encoding="utf-8")
            restored = hashlib.sha256(
                (ROOT / mutant.path).read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            if restored != digests[mutant.path]:
                print(f"RESTORE FAILED after {mutant.identifier}", file=sys.stderr)
                return 1
        tag = " (declared equivalent)" if mutant.equivalent else ""
        print(f"{verdict:16} {mutant.identifier:44} {mutant.obligation}{tag}", flush=True)
        if mutant.equivalent:
            continue
        if verdict == "survived":
            survivors.append(mutant)
        elif verdict == "killed-by-suite":
            gaps.append(mutant)

    purge()
    # A survivor count is meaningless without its verdict module list: the same
    # 41-mutant corpus read 13 survivors against one module and 0 against two.
    print(
        f"\nmutants={len(chosen)} survivors={len(survivors)} battery_gaps={len(gaps)} "
        f"verdict_modules={verdict_modules}"
    )
    for mutant in survivors:
        print(f"SURVIVOR {mutant.identifier} -> obligation {mutant.obligation} does not pin it")
    for mutant in gaps:
        print(f"BATTERY-GAP {mutant.identifier} -> only the wider suite kills it")
    return 1 if survivors or gaps else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", default=[], dest="ids")
    parser.add_argument("--verdict", action="append", default=[], dest="verdict")
    parser.add_argument("--full", action="store_true", help="re-run the whole suite on a survivor")
    arguments = parser.parse_args(argv)
    return run(arguments.ids, arguments.verdict or list(BATTERY), full=arguments.full)


if __name__ == "__main__":
    raise SystemExit(main())
