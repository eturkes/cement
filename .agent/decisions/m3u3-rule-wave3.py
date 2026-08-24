#!/usr/bin/env python3
"""Fill `main_ruling` in m3u3-review.json and m3u3-divergences.json. Idempotent.

    python3 .agent/decisions/m3u3-rule-wave3.py [--check]

Rulings are MAIN-final. Section 13 of m3u3-contract.md carries them with their landing sites;
these tables are the machine copy that keeps each artifact self-contained.

ACCEPTED  correct; the contract, the code or an instrument changed at S3
SCOPED    correct in substance; MAIN rules the boundary narrower or wider than the finding states
CARRIED   correct and undischarged; the acceptance check is S4's, restated verbatim here
REJECTED  MAIN probed it and the finding does not hold
CLEARED   the lens found no defect and MAIN agrees
"""

from __future__ import annotations

import json
import pathlib
import sys

REVIEW = pathlib.Path(__file__).with_name("m3u3-review.json")
DIVERGENCES = pathlib.Path(__file__).with_name("m3u3-divergences.json")

REVIEW_RULINGS: dict[str, str] = {
    "R01": (
        "ACCEPTED, three of four, and the fourth ruled the other way. Two lenses reached the pair-"
        "iterable defect (R01 + R15), so the council rule accepts outright. LANDED: "
        "`isinstance(candidate.provenance, Mapping)` now gates the conversion, which rejects a list, "
        "a tuple, a generator and a keys/__getitem__ duck type on both paths; D43 publishes that "
        "domain. The unreachable JSON-object branch is DELETED with its section 7 row on the "
        "standing mutation criterion - `canonicalize(dict).value` is always `dict`, and a non-str-key "
        "mapping raises `JSON object keys must be strings` from the canonicalizer first, so no input "
        "reaches it. Mutant `provenance-object-check-deleted` survived for exactly that reason: a "
        "dead branch and a surviving mutant are one fact seen twice. RULED THE OTHER WAY, the "
        "items-raising case: `dict(Mapping)` reads `keys()` and `__getitem__`, so `items` is never "
        "called and the contract's own settling case was off the access path. D38 now names the path "
        "and moves the settling case onto it; the battery's `ExplodingAccess` raises from `__iter__` "
        "and `__getitem__`. SCOPED, the direct raw exception: a direct caller owns the object it "
        "passed, so its `RuntimeError` reaches it unchanged. Rewriting it into `candidate provenance "
        "must be a mapping` would misdescribe an object that IS a mapping, and the partial "
        "`except (TypeError, ValueError)` that did so is DELETED - the boundary is now total and "
        "matches `handle`'s."
    ),
    "R02": "CLEARED. MAIN agrees; V-D12 is the ruling this lens re-derives, and both revision tests stay green.",
    "R03": "CLEARED. MAIN agrees; D42's row shape is pinned by the battery's own D42 test and by mutants `status-sequence-unbound` and `provenance-columns-swapped`, both killed.",
    "R04": "CLEARED. MAIN agrees; mutants `contained-raise-keeps-cause`, `raise-moved-inside-handler` and `request-input-is-caller-object` are all killed, so the containment this lens measured is now pinned against deletion.",
    "R05": "CLEARED. MAIN agrees; mutant `catch-widened-to-baseexception` is killed by the battery's D39 test, so the exact `Exception` boundary cannot regress silently.",
    "R06": (
        "CARRIED to S4, blocking there. The interior rollback matrix is ACCEPTED and shipped as "
        "D15's fifth pin, which discharges X12. The commit-uncertainty half is a REAL and UNRULED "
        "gap: a `Connection` whose commit durably succeeds and then raises leaves all three rows "
        "committed while the caller sees `StateError` and no proposal id. That is a property of the "
        "`Store` seam, not of submission, and every method in the codebase shares it - so scoping "
        "it belongs with the seam, not inside M3.3's candidate boundary. S4 CHECK, verbatim: scope "
        "D15 and the public prose to failures before commit, publish the commit-uncertainty window "
        "with the recovery route (the proposal id is discoverable through `get_proposal` by "
        "partition), and pin the probe."
    ),
    "R07": (
        "ACCEPTED IN PART at S3, remainder CARRIED. LANDED NOW: D37 no longer contradicts the "
        "constructor, because the pre-flight is deleted - the battery drove a raising descriptor "
        "through construction and read the planted secret out, which is the hazard D37's own "
        "grounds name; D44 publishes the 65,536-byte provenance bound the shipped code always "
        "applied; D38 states the complete direct/source mapping failure taxonomy including the raw "
        "direct exception. CARRIED to S4: D01, D07, D09, D15 and D16 each quantify over work the "
        "SOURCE may perform outside every Cement transaction, and the fix is one shared scoping "
        "sentence - 'submission-attributable' - applied to five obligations plus the commit window "
        "of R06. Ruled together with R06 because they are one boundary seen from two lenses."
    ),
    "R08": (
        "ACCEPTED, all four. LANDED: memory scoped to the actual call boundary; the roadmap lists "
        "`4b96e4d`, `719b48a` and `57a4571`; the differential is now RUN and credited by MAIN's own "
        "re-derivation rather than described as ruled; and the smoke check is renamed to state only "
        "what it measures. The general rule this pays for: a record that says 'ruled' where it "
        "means 'planned' reads as closure to every later session, and the only defence is naming "
        "the instrument that produced the number."
    ),
    "R09": "ACCEPTED, all three. LANDED: `submit_proposal`'s docstring drops the unreachable revision `StateError` and states positively that it binds whatever revision is current under its sole write lock; `propose` scopes transaction absence to transactions the call holds and names the reentrancy caveat; `CandidateSourceError`'s docstring scopes 'carries no detail' to the instance `System.propose` raises, leaving an adapter's own detailed instance untouched.",
    "R10": "ACCEPTED, all three. LANDED: README publishes direct and source revision behaviour separately; README and `architecture.md` say the source runs outside every transaction the call holds; `adapter-protocol.md` says at most one invocation per call and zero for calls that fail validation or lookup. The battery's D34 fragments move with them, so the prose cannot drift back.",
    "R11": "CLEARED. MAIN agrees; D28's landed totals are published at S3 per review Z01, so the census now states the numbers this lens measured.",
    "R12": (
        "ACCEPTED, and DISCHARGED with a wider corpus than the finding asked for. The committed "
        "catalogue is `.agent/decisions/m3u3-mutants.py`, 42 mutants over every predicate the unit "
        "adds, enumerated by site in D30. Measured at S3 close with `tests.test_submission` plus "
        "`tests.test_submission_battery` as verdict: 42 killed, 0 survivors, 0 battery gaps, green "
        "control. M05 is deleted with its dead branch per R01. The lens's own sweep read 12 of 25 "
        "surviving because it graded a corpus the battery had not yet been added to - which is the "
        "reusable rule: a mutation number is meaningless without its verdict module list."
    ),
    "R13": "ACCEPTED. LANDED: the battery gains a `Candidate` subclass rejection and four pair-iterable rejections (D43), an oversized-provenance case with the exact bound text plus the same payload passing as `output` (D44), and the D13 collider fixtures already plant `tenantXa`/`echoX1`/`TENANT_A` rows. Mutants `candidate-type-widened-to-isinstance`, `provenance-bound-dropped`, and all four `LIKE` scope weakenings are killed.",
    "R14": "ACCEPTED. LANDED: the memory bullets are rewritten as provenance-free general rules and the unit history stays in this decision record, which is where a measurement is checkable. REJECTED on one point: measurements, SHAs and named conventions are this document's payload, and the Authoring rule's provenance ban targets dates, discovery narration and origin stories - the same boundary attack row X06 already fixed. Negative-form shipped instructions are rewritten positively.",
    "R15": "ACCEPTED. Confirmed independently by R01, so the council rule accepts outright. LANDED: `_canonical_candidate` is now one minimal total boundary - exact `Candidate`, `Mapping` instance, one canonicalization under the published bound - with no partial exception translation and no dead branch. Ownership normalizes by path, not by exception class: the direct caller keeps its own exception, the source path contains everything.",
    "R16": "CLEARED. MAIN agrees, and re-derived every pin: schema 14,580 B / `5be3d79f...` equal to `SCHEMA_FINGERPRINT`; `cli.py`, `_command_supervisor.py` and `example_adapter.py` byte-identical to `f9b9755`; all three `handle` conventions reproduce. S3 adds one deliberate out-of-unit edit, ruled in D37: `System.__init__`'s pre-flight is deleted and `tests/test_system.py` records the change where the old assertion stood.",
    "Z01": "ACCEPTED. LANDED: D27 identifies 17 reads / 15 writes as the `f9b9755` BASELINE, and D28 publishes the landed 18 reads / 16 writes / 12 reached helpers / zero violations. The stale-anchor lesson repeats from A09 and X03: a count inside a document the unit edits is stale on arrival unless it names which state it measures.",
    "Z02": (
        "CARRIED to S4. The finding holds: `test_both_methods_route_through_one_persistence_seam` "
        "spies that both public methods CALL the seam, which a split writer satisfies while the "
        "requests INSERT lives in a second private helper. Section 12's description of it as a "
        "call-graph pin overstates what it measures. Mutant `seam-write-becomes-two-transactions` "
        "kills the two-TRANSACTION split but not the one-transaction two-HELPER split. S4 CHECK, "
        "verbatim: an AST probe enumerating the M3.3 requests INSERT, the proposals INSERT and the "
        "`proposal.created` call, requiring all three inside `_persist_proposal` and both public "
        "methods calling that sole owner, plus a split-writer mutant in the corpus that it kills."
    ),
    "Z03": (
        "CARRIED to S4. Two of the five ABI mutants are already dead - `direct-keyword-marker-"
        "dropped` and `direct-candidate-defaulted` are in the corpus and killed by the battery's "
        "P01 signature test. The three ANNOTATION weakenings survive because no committed test "
        "reads annotations. S4 CHECK, verbatim: one `inspect.signature` plus "
        "`typing.get_type_hints` test pinning parameter order, keyword-only kind, required state, "
        "the exact `Candidate` annotation, the absence of a candidate or source parameter on "
        "`propose`, and both `str` returns; add the three annotation mutants to the corpus and "
        "require the sweep to kill them."
    ),
    "Z04": "ACCEPTED. LANDED: the contract title and scope sentence now say `explicit proposal submission over a retained schema-v2 request row`, and `tests/test_submission.py`'s docstring says the same. D33's own prohibition applied to D33's own document was the defect. The roadmap unit name stays as the one expressly exempt label.",
    "Z05": (
        "CARRIED to S4, blocking there, and NARROWED by measurement. The battery is already clean: "
        "`table_counts` enumerates every table from `sqlite_schema` and excludes only `sqlite_%`, "
        "so its D01, D15 and D38 footprint pins compare all 13 application tables and the extra-"
        "`schema_metadata` mutant would fail them. The finding stands against `tests/"
        "test_submission.py` and `.agent/decisions/m3u3-smoke.py`, which still count 9 named "
        "tables. S4 CHECK, verbatim: derive the footprint table set from the live declared schema "
        "in both, excluding SQLite-owned tables by an explicit rule, and add a `schema_metadata` "
        "write mutant the corpus kills."
    ),
    "Z06": (
        "CARRIED to S4. The finding holds and is a FORCING-POWER defect, not a style point: `if "
        "table in sql` over raw SQL misses `FROM ARTIFACTS`, so D17's forbidden-read guarantee is "
        "asserted and not measured. S4 CHECK, verbatim: normalize parsed SQL identifiers case-"
        "insensitively or read SQLite authorization events instead of substrings, cover every "
        "table D17 names on both paths, keep the non-empty recorded list as the positive control, "
        "and add the uppercase-`ARTIFACTS` mutant to the corpus."
    ),
}

DIVERGENCE_RULINGS: dict[str, str] = {
    "Z01": (
        "NOT BEHAVIOURAL, and it is a second implementation confirming D06. Both implementations "
        "route both public paths through exactly ONE private persistence seam; only the private "
        "name differs (`_persist_proposal` against `_persist_submission`), and D06 constrains the "
        "COUNT, never the identifier. The differential's own normalization maps the two names, so "
        "Q30 compares identical. MAIN's name stands."
    ),
    "Z02": (
        "MAIN STANDS, V-D12. The oracle opens an entry read transaction on the direct path and "
        "carries its revision into the write, giving `direct_transaction_count` 2 against MAIN's 1. "
        "The extra read exists only to feed a guard that protects a GENERATION WINDOW the direct "
        "caller does not have. Verdict row D12 and attack row A05 warned about this branch before "
        "the oracle built it; the oracle building it is the exhibit."
    ),
    "Z03": (
        "MAIN STANDS, and this row is the one that makes the differential evidentiary. Under a "
        "`revise_operation` injected mid-call, MAIN succeeds - one request, one proposal, one "
        "event, `operation_revision` bound to 2 under its sole write lock, `stored_revision_matches"
        "_current` true - while the oracle raises `StateError` and stores nothing "
        "(`stored_request_operation_revisions` empty). That is exactly the failure V-D12 says a "
        "direct caller cannot have earned, exhibited rather than argued. The 30 seeded probes could "
        "not reach it because they measure the oracle's own conformance; a corpus written to "
        "demonstrate conformance cannot discriminate two designs."
    ),
    "Z04": (
        "MAIN STANDS, D17 and Y05 on M3.1's grounds. Both implementations read the clock exactly "
        "once; MAIN reads inside the write transaction, the oracle before it. The oracle's ground - "
        "do not hold the write lock across caller-supplied clock code - is sound, and M3.1 already "
        "decided against it: a clock read taken ahead of the authoritative plan can commit a row "
        "older than its own build, and the lock-hold cost is bounded by `self._now`, which is "
        "Cement's own seam and not adapter code. Mutant `clock-read-per-row` pins the cardinality."
    ),
}


# An `identical` probe carries no divergence to rule, so its ruling states what the row is worth:
# one independent measurement of the obligation named in its probe text.
IDENTICAL_RULING = (
    "IDENTICAL. No divergence to rule. The row stands as a second independent measurement of the "
    "obligation its probe names, re-derived by MAIN against the shipped code at S3 close."
)


def _apply(path: pathlib.Path, rulings: dict[str, str], *, check: bool) -> tuple[int, int, str]:
    document = json.loads(path.read_text())
    rows = document["rows"]
    ids = {row["id"] for row in rows}
    extra = [i for i in rulings if i not in ids]
    unruled = [
        row["id"]
        for row in rows
        if row["id"] not in rulings and row.get("verdict") != "identical"
    ]
    if unruled or extra:
        print(f"{path.name} MISSING RULINGS: {unruled}\n{path.name} UNKNOWN IDS: {extra}")
        raise SystemExit(2)
    for row in rows:
        row["main_ruling"] = rulings.get(row["id"], IDENTICAL_RULING)
    rendered = json.dumps(document, indent=2) + "\n"
    if check:
        return len(rows), len(rulings), "IN-SYNC" if rendered == path.read_text() else "STALE"
    path.write_text(rendered)
    return len(rows), len(rulings), "WRITTEN"


def main() -> int:
    check = "--check" in sys.argv
    stale = False
    for path, rulings in ((REVIEW, REVIEW_RULINGS), (DIVERGENCES, DIVERGENCE_RULINGS)):
        rows, filled, state = _apply(path, rulings, check=check)
        print(f"{path.name}: ROWS {rows}, RULED {filled}, {state}")
        stale = stale or state == "STALE"
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
