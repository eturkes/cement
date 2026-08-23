#!/usr/bin/env python3
"""Structural validator for M3.3 wave-2 artifacts.

Usage:
  uv run python .agent/decisions/m3u3-wave2-validate.py <artifact.json>
  uv run python .agent/decisions/m3u3-wave2-validate.py --emit-seed verdicts|attack|probes

The artifact's top-level ``kind`` selects the schema:

  "verdicts"  divergent readings of the acceptance contract, one row per obligation
  "attack"    contract attack findings, one row per seeded lens
  "probes"    the differential probe corpus, one row per seeded probe

Exit 0 = structurally valid AND nothing left ``unknown`` outside a MAIN-owned
field. Exit 1 = structural defect or an unfilled cell.

Seeding contract: ``--emit-seed`` writes every required id with every value
``unknown``. That file is STRUCTURALLY valid and still exits 1, so UNKNOWN-CELLS
is the flush metric and each filled cell lowers it by one.

``locus``, ``lens`` and ``probe`` are MAIN-owned row identity: the validator
rejects any value other than the seeded text, so a row keeps its assigned
subject. Report a wrong subject to MAIN instead of rewriting it. ``main_verdict``
and ``main_disposition`` are MAIN-owned in the other direction: MAIN fills them,
the teammate leaves them ``unknown``, and they never count as unfilled.

Retarget clause: seeding must never cap discovery. Every kind accepts EXTRA rows
whose id matches its own extension pattern (``X<nn>`` for verdicts and probes,
``Y<nn>`` for attack); an extra row is graded exactly like a seeded one except
that the teammate owns its subject text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

UNKNOWN = "unknown"
MAIN_OWNED = {"main_verdict", "main_disposition", "contract_action"}
PROSE_MIN = 20
CLEARED = re.compile(r"^(no defensible alternative|no defect|not reachable): .{20,}$", re.S)

SEVERITIES = {"blocking", "material", "minor", "cleared", UNKNOWN}
OUTCOMES = {"ok", "error", "differs", "unreachable", UNKNOWN}

VERDICT_FIELDS = (
    "locus",
    "divergence",
    "distinguishing_probe",
    "proposed",
    "main_verdict",
    "contract_action",
)
ATTACK_FIELDS = ("lens", "finding", "evidence", "severity", "acceptance_check", "main_disposition")
PROBE_FIELDS = ("probe", "outcome", "observation", "note")

# ---------------------------------------------------------------------------
# Row identity. MAIN owns every string below.
# ---------------------------------------------------------------------------

# One row per contract obligation. The teammate is diff-blind: it reads the
# contract and the normative docs, never MAIN's implementation.
VERDICT_LOCI: dict[str, str] = {
    "P01": "two methods, candidate keyword-only and REQUIRED on submit_proposal",
    "P02": "both return the proposal ID as a bare str, no new model",
    "P03": "submit_proposal NEVER invokes a source, even when one is configured and raising",
    "P04": "propose invokes self.candidate_source and nothing else; no per-call source argument",
    "P05": "neither name is exported from __init__.py; reachable only through System",
    "P06": "handle's bytes stay identical to 1182130a2b3a, 12,866 B by AST slice",
    "D01": "success footprint: exactly one requests row, one proposals row, one events row, nothing else",
    "D02": "the request row is written directly as pending with proposal_id set and no lease",
    "D03": "the event is proposal.created; payload and subject match handle's write MINUS request identity",
    "D04": "no caller-supplied identifier; byte-identical content submitted twice writes two of everything",
    "D05": "propose invokes the source exactly once on success and exactly zero times on every raising path",
    "D06": "one private persistence seam writes the request row, the proposal row and the event for both paths",
    "D07": "validation order: partition, operation, input_value canonicalization, then candidate",
    "D08": "a bad partition together with a bad input_value reports the PARTITION error",
    "D09": "a rejected call performs zero transactions and zero source invocations, measured with live spies",
    "D10": "omitted candidate and passing source= both raise Python's own TypeError; no shipped validator",
    "D11": "the source runs outside every open transaction; no connection reports in_transaction",
    "D12": "the operation revision is read before invocation and re-read inside the write transaction",
    "D13": "the revision re-read uses a scoped query; reusing System.operations() is rejected",
    "D14": "propose hands the source a CandidateRequest carrying the generated internal request ID",
    "D15": "a failed submission leaves the ledger byte-identical under four independent pins",
    "D16": "zero commit() calls on any failure path, measured through a connect-factory spy",
    "D17": "neither method reads the clock except through self._now nor consults artifact/example/function tables",
    "D18": "both source-failure rows raise from None; no class, message, cause, context or frame reaches the caller",
    "D19": "the two source-failure rows are indistinguishable to the caller",
    "D20": "failure raises; it never returns a value and never writes request.fallback_failed or a failed row",
    "D21": "NotFoundError for an unregistered operation is raised BEFORE the source is invoked",
    "D22": "neither the return value nor the proposal.created event publishes the request identifier",
    "D23": "the contract publishes the eight live seams that still expose the identifier rather than claiming privacy",
    "D24": "private in M3.3 means a storage role the new API neither accepts nor returns",
    "D25": "no shipped sentence may state or imply that M3.3 removed request identity",
    "D26": "decisive gate reaches 635 + N tests with zero failures",
    "D27": "the read-site census counts are a TRIPWIRE; violations == [] is the load-bearing assertion",
    "D28": "M3.3 updates the census counts in the same commit that adds the sites, recording each site by method",
    "D29": "violations == [] and the reached-helper discipline stay untouched",
    "D30": "closure is mechanical: full gate, battery grader, mutation sweep over the added predicates",
    "D31": "CandidateSourceError's docstring is rewritten away from supervised fallback",
    "D32": "both docstrings state what is persisted, that no idempotency exists, the adapter execution, and each error",
    "D33": "no shipped sentence calls submission cheap, safe-to-retry, deduplicated or request-free",
    "D34": "README, docs/architecture.md and docs/threat-model.md are checked for sentences the new surface falsifies",
    "T01": "error text table row: source raises CandidateSourceError -> CandidateSourceError('candidate source failed')",
    "T02": "error text table row: source raises any other Exception -> the identical class and message",
    "T03": "error text table row: propose with no configured source -> StateError('candidate source is not configured')",
    "T04": "error text table row: revision changed -> StateError('operation revision changed before proposal submission')",
    "T05": "error text table row: operation absent -> NotFoundError('operation is not registered in this partition')",
    "T06": "error text table row: rejected partition, operation or input_value -> the existing unchanged ValidationError texts",
}

# One row per attack lens. Sections A01-A11 walk the contract; X01-X07 are the
# defect shapes this project has already paid for.
ATTACK_LENSES: dict[str, str] = {
    "A01": "section 1 Scope: is every named out-of-scope surface actually untouched by what section 2-9 mandate?",
    "A02": "section 2 frozen shape: are P01-P06 satisfiable together, and is the handle byte claim checkable as written?",
    "A03": "section 3 two paths: is the success footprint complete, and does after generated-ID normalization have one meaning?",
    "A04": "section 4 precedence: does D07's order have a probe per ADJACENT edge, or only spanning pairs?",
    "A05": "section 5 source invocation: is the read-then-re-read window specified tightly enough to be implementable one way?",
    "A06": "section 6 purity: does each of D15-D17 have its own instrument, or is one obligation discharged by a proxy?",
    "A07": "section 7 error taxonomy: is every reachable failure of both methods listed with an exact text?",
    "A08": "section 8 private request row: is the eight-seam list complete and each entry true at HEAD?",
    "A09": "section 9 gate identity: are the cited census line numbers and counts accurate at HEAD?",
    "A10": "section 10 fork ruling: do the four measured grounds support TWO METHODS, or does any overreach?",
    "A11": "section 11 normative claims: are D31-D34 checkable, and is the cited errors.py:28 docstring text exact?",
    "X01": "biconditional asserted where the design admits only one-way implication",
    "X02": "a claim that is unconditional in the prose but holds only under a particular fixture or configuration",
    "X03": "a stale structural inventory: any count, line anchor, byte length or SHA the contract states as fact",
    "X04": "an obligation with no forcing probe, so no committed test could detect its deletion",
    "X05": "guarantee-vs-claim gap on private, transitional, identical, indistinguishable or unchanged",
    "X06": "CLAUDE.md Authoring conformance of the contract itself and of the prose M3.3 will ship",
    "X07": "a hazard the contract declares injection-only or unreachable that is real behaviour of a default System",
}

# Differential probe corpus. MAIN's implementation and the oracle answer every id
# with the same observation keys, so the differential compares field by field.
PROBE_SUBJECTS: dict[str, str] = {
    "Q01": "direct submission of a caller-supplied candidate: returned type, value shape and id prefix",
    "Q02": "direct submission durable footprint: per-table row-count delta across every table in the schema",
    "Q03": "direct submission event: kind, subject_type, subject_id and the exact payload keys",
    "Q04": "direct request row shape: status, proposal_id, lease_owner, lease_until_us, attempts, operation_revision",
    "Q05": "direct submission while a configured candidate_source raises: source invocation count and the result",
    "Q06": "direct proposals row: output and provenance text plus digests, status, and the status_sequence binding",
    "Q07": "source-backed submission: returned type, and the footprint compared with Q02 after id normalization",
    "Q08": "source-backed submission: source invocation count and every field of the CandidateRequest handed over",
    "Q09": "connection.in_transaction observed on every Cement-held connection while the source executes",
    "Q10": "the source raises CandidateSourceError: public class, message, __cause__, __context__ and frames",
    "Q11": "the source raises an arbitrary Exception carrying a planted secret: same observations, secret absent",
    "Q12": "propose with candidate_source None: class, message and source invocation count",
    "Q13": "the source returns a non-Candidate or a malformed provenance: class and exact message",
    "Q14": "the operation revision changes between generation and the write: class, message and durable footprint",
    "Q15": "a bad partition together with a bad input_value: which error is reported",
    "Q16": "a bad operation together with a bad input_value: which error is reported",
    "Q17": "a bad partition together with an unregistered operation: which error, and transaction count",
    "Q18": "a rejected call: transaction count and source invocation count, each with a positive control",
    "Q19": "submit_proposal called without the candidate keyword: exact TypeError text",
    "Q20": "source= passed to submit_proposal and to propose: exact TypeError text for each",
    "Q21": "unregistered operation on the source path: class, message, and whether the source ran",
    "Q22": "a failed submission: ledger sha256, full iterdump, row counts and the event sequence counter",
    "Q23": "commit() call count on every failure path through a Connection-subclass factory, with a positive control",
    "Q24": "clock reads during a successful submission: self._now call count and any other clock consulted",
    "Q25": "every SELECT executed during a successful submission, by table",
    "Q26": "the submitted proposal seen through get_proposal, proposal, proposals and function_report",
    "Q27": "review accepting a submitted proposal, then compile and promote, end to end",
    "Q28": "byte-identical content submitted twice: proposal ids, request rows, events and any conflict",
    "Q29": "handle on the same System after a submission: result and durable footprint against the baseline",
    "Q30": "read-site census: read-transaction sites, write-transaction sites, reached helpers and violations",
}


def _fail(message: str) -> None:
    print(f"INVALID: {message}")
    raise SystemExit(1)


def _rows(payload: dict, required: dict[str, str], extension: str) -> dict[str, dict]:
    raw = payload.get("rows")
    if not isinstance(raw, list):
        _fail("'rows' must be a list")
    pattern = re.compile(rf"^{extension}\d{{2}}$")
    seen: dict[str, dict] = {}
    for row in raw:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            _fail("every row must be an object with a string id")
        if row["id"] in seen:
            _fail(f"duplicate row id {row['id']!r}")
        if row["id"] not in required and pattern.fullmatch(row["id"]) is None:
            _fail(f"row id {row['id']!r} is neither seeded nor a {extension}nn extension row")
        seen[row["id"]] = row
    missing = [identifier for identifier in required if identifier not in seen]
    if missing:
        _fail(f"missing row ids: {missing}")
    return seen


def _prose(identifier: str, field: str, value: object) -> None:
    if not isinstance(value, str):
        _fail(f"{identifier}.{field} must be a string")
    if len(value) < PROSE_MIN:
        _fail(f"{identifier}.{field} is {len(value)} chars, under {PROSE_MIN}")


def _validate_verdicts(payload: dict) -> int:
    rows = _rows(payload, VERDICT_LOCI, "X")
    unknown = 0
    for identifier, row in sorted(rows.items()):
        if set(row) != {"id", *VERDICT_FIELDS}:
            _fail(f"{identifier} must carry exactly id plus {list(VERDICT_FIELDS)}")
        seeded = VERDICT_LOCI.get(identifier)
        if seeded is not None and row["locus"] != seeded:
            _fail(f"{identifier}.locus was rewritten; MAIN owns it, report the objection instead")
        if seeded is None:
            _prose(identifier, "locus", row["locus"])
        for field in VERDICT_FIELDS[1:]:
            value = row[field]
            if not isinstance(value, str):
                _fail(f"{identifier}.{field} must be a string")
            if value == UNKNOWN:
                if field not in MAIN_OWNED:
                    unknown += 1
                continue
            if field == "divergence" and CLEARED.fullmatch(value) is not None:
                continue
            if field == "distinguishing_probe" and value == "n/a":
                continue
            if field not in MAIN_OWNED:
                _prose(identifier, field, value)
    return unknown


def _validate_attack(payload: dict) -> int:
    rows = _rows(payload, ATTACK_LENSES, "Y")
    unknown = 0
    for identifier, row in sorted(rows.items()):
        if set(row) != {"id", *ATTACK_FIELDS}:
            _fail(f"{identifier} must carry exactly id plus {list(ATTACK_FIELDS)}")
        seeded = ATTACK_LENSES.get(identifier)
        if seeded is not None and row["lens"] != seeded:
            _fail(f"{identifier}.lens was rewritten; MAIN owns it, report the objection instead")
        if seeded is None:
            _prose(identifier, "lens", row["lens"])
        severity = row["severity"]
        if severity not in SEVERITIES:
            _fail(f"{identifier}.severity={severity!r} is not one of {sorted(SEVERITIES)}")
        if severity == UNKNOWN:
            unknown += 1
        for field in ("finding", "evidence", "acceptance_check"):
            value = row[field]
            if not isinstance(value, str):
                _fail(f"{identifier}.{field} must be a string")
            if value == UNKNOWN:
                unknown += 1
                continue
            if field == "finding" and CLEARED.fullmatch(value) is not None:
                continue
            if field == "acceptance_check" and severity == "cleared":
                continue
            _prose(identifier, field, value)
        if not isinstance(row["main_disposition"], str):
            _fail(f"{identifier}.main_disposition must be a string")
    return unknown


def _validate_probes(payload: dict) -> int:
    unknown = 0
    for field in ("implementation", "worktree_commit"):
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            _fail(f"top-level {field!r} must be a non-empty string")
        if value == UNKNOWN:
            unknown += 1
    rows = _rows(payload, PROBE_SUBJECTS, "X")
    for identifier, row in sorted(rows.items()):
        if set(row) != {"id", *PROBE_FIELDS}:
            _fail(f"{identifier} must carry exactly id plus {list(PROBE_FIELDS)}")
        seeded = PROBE_SUBJECTS.get(identifier)
        if seeded is not None and row["probe"] != seeded:
            _fail(f"{identifier}.probe was rewritten; MAIN owns it, report the objection instead")
        if seeded is None:
            _prose(identifier, "probe", row["probe"])
        outcome = row["outcome"]
        if outcome not in OUTCOMES:
            _fail(f"{identifier}.outcome={outcome!r} is not one of {sorted(OUTCOMES)}")
        if not isinstance(row["note"], str):
            _fail(f"{identifier}.note must be a string")
        if outcome == UNKNOWN:
            unknown += 1
            continue
        if not isinstance(row["observation"], dict) or not row["observation"]:
            _fail(f"{identifier}.observation must be a non-empty object once outcome is filled")
        _prose(identifier, "note", row["note"])
    return unknown


def _seed(kind: str) -> dict:
    if kind == "verdicts":
        return {
            "kind": "verdicts",
            "rows": [
                {
                    "id": identifier,
                    "locus": locus,
                    "divergence": UNKNOWN,
                    "distinguishing_probe": UNKNOWN,
                    "proposed": UNKNOWN,
                    "main_verdict": UNKNOWN,
                    "contract_action": UNKNOWN,
                }
                for identifier, locus in VERDICT_LOCI.items()
            ],
        }
    if kind == "attack":
        return {
            "kind": "attack",
            "rows": [
                {
                    "id": identifier,
                    "lens": lens,
                    "finding": UNKNOWN,
                    "evidence": UNKNOWN,
                    "severity": UNKNOWN,
                    "acceptance_check": UNKNOWN,
                    "main_disposition": UNKNOWN,
                }
                for identifier, lens in ATTACK_LENSES.items()
            ],
        }
    return {
        "kind": "probes",
        "implementation": UNKNOWN,
        "worktree_commit": UNKNOWN,
        "rows": [
            {"id": identifier, "probe": probe, "outcome": UNKNOWN, "observation": {}, "note": ""}
            for identifier, probe in PROBE_SUBJECTS.items()
        ],
    }


VALIDATORS = {"verdicts": _validate_verdicts, "attack": _validate_attack, "probes": _validate_probes}


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--emit-seed" and argv[2] in VALIDATORS:
        print(json.dumps(_seed(argv[2]), indent=2))
        return 0
    if len(argv) != 2:
        print(__doc__)
        return 1
    path = Path(argv[1])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _fail(f"unreadable artifact: {exc}")
    if not isinstance(payload, dict):
        _fail("artifact must be a JSON object")
    kind = payload.get("kind")
    if kind not in VALIDATORS:
        _fail(f"kind={kind!r} is not one of {sorted(VALIDATORS)}")
    unknown = VALIDATORS[kind](payload)
    seeded = {"verdicts": VERDICT_LOCI, "attack": ATTACK_LENSES, "probes": PROBE_SUBJECTS}[kind]
    extra = [row["id"] for row in payload["rows"] if row["id"] not in seeded]
    print(f"KIND: {kind}")
    print(f"ROWS: {len(payload['rows'])} ({len(seeded)} seeded, {len(extra)} extension)")
    if extra:
        print(f"EXTENSION-ROWS: {sorted(extra)}")
    print(f"MAIN-OWNED-COLUMNS: {sorted(MAIN_OWNED)} (exempt from UNKNOWN-CELLS)")
    print(f"UNKNOWN-CELLS: {unknown}")
    if unknown:
        print("INCOMPLETE: fill every cell, then rerun this validator LAST")
        return 1
    print("VALID: structurally sound with zero unfilled cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
