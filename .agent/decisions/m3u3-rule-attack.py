#!/usr/bin/env python3
"""Fill `main_disposition` in m3u3-attack.json. Idempotent, replayable from the reviewer's
committed table (wt/rev-m3u3-1).

    python3 .agent/decisions/m3u3-rule-attack.py [--check]

Dispositions are MAIN-final. Section 13 of m3u3-contract.md carries the same rulings with their
landing sites; this file is the machine copy that keeps the artifact self-contained.

UPHELD    the finding is correct and the contract or code changed
PARTIAL   correct in part; the ruling states which part and rejects the rest
DOWNGRADE correct in substance, wrong in reproduction, so severity drops
CLEARED   the reviewer found no defect and MAIN agrees
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u3-attack.json")

DISPOSITIONS: dict[str, str] = {
    "A01": (
        "CLEARED, and now CHECKABLE. Scope ownership is satisfiable, but section 1 said 'unchanged' "
        "and 'byte-stable' with no pin and no baseline. Verdict rows X05/X06 found the same gap "
        "from the other side. LANDED: B01 pins the schema bytes and fingerprint; B02 pins the three "
        "byte-stable files against the named unit-entry baseline `f9b9755`."
    ),
    "A02": (
        "CLEARED, and the clearing is itself the useful result. The reviewer reproduced P06 under "
        "the LINE-START slice with the trailing newline removed and got the contract's exact "
        "figure, independently identifying the convention that makes the claim checkable. MAIN "
        "measured both: `1182130a2b3a` / 12,866 B whole-line span, `c27e71b0b4c7` / 12,862 B from "
        "`ast.get_source_segment`, which drops the four-space indent. Same unchanged source, two "
        "numbers, four bytes apart. LANDED: P06 states the convention so no future lens has to "
        "rediscover it."
    ),
    "A03": (
        "UPHELD, blocking. `events.sequence` is AUTOINCREMENT, so every success mutates "
        "`sqlite_sequence` and D01 read literally is unsatisfiable by correct code. Verdict row D01 "
        "confirms independently, so the council rule accepts without a MAIN probe. LANDED: section "
        "12 V-D01 scopes the footprint to Cement's declared SCHEMA tables."
    ),
    "A04": (
        "UPHELD. D07 declares a four-stage total order; D08's partition/input pair spans two edges "
        "and pins neither interior one, so three of four edges could regress undetected. Verdict "
        "row D07 confirms independently. LANDED: three adjacent-edge probes plus two for "
        "`propose`'s configured-source slot; D08 is recorded as a sample."
    ),
    "A05": (
        "UPHELD, and THIS PAIR CHANGED THE SHIPPED CODE. D12 ruled the source-path revision window "
        "and left DIRECT binding unruled. MAIN's first implementation gave both paths a pre-read "
        "plus a seam re-read, which raised `StateError` for a direct submission with no generation "
        "window to protect. Verdict row D12 reached the same conclusion independently. LANDED: "
        "`expected_revision: int | None`; D12 scoped to the source path; section 12 V-D12."
    ),
    "A06": (
        "UPHELD against the contract. D15 and D16 each named an instrument and D17 named none, so "
        "row, file, dump and commit pins could all pass while the code read a forbidden table or "
        "another clock. LANDED: D17 carries a statement-recording `Connection` subclass with a "
        "non-empty recorded list as its own positive control."
    ),
    "A07": (
        "UPHELD, blocking. D07 ordered DIRECT candidate validation while section 7 published no "
        "class, text, or accepted shape for any of its failures. LANDED: four candidate rows in the "
        "section 7 table, covering the wrong container, non-mapping provenance, non-object "
        "provenance, and canonicalization failure."
    ),
    "A08": (
        "UPHELD IN PART. The eight seams are API-level and true as named; `cli.py` also serializes "
        "the identifier, and authorized ledger access exposes it by design. REJECTED as a "
        "completeness defect: the list was never an exhaustive security count. LANDED: section 12 "
        "V-D23 states the scope."
    ),
    "A09": (
        "UPHELD. D27 cited lines 869-872, the violation branch; the four census assertions sat at "
        "875-878, and this unit moved them again. LANDED: D27 cites the test by NAME, because a "
        "line anchor into a file the unit edits is stale on arrival."
    ),
    "A10": (
        "CLEARED. Section 10 separates measured API hazards from implementability evidence and "
        "already states that `split`'s green gate is not correctness. No change."
    ),
    "A11": (
        "UPHELD. `docs/adapter-protocol.md` promised an inert `fallback_failed` request and possible "
        "re-invocation for the same `CommandCandidateSource` that `propose` must expose as an "
        "exception with zero rows. Verdict row X07 confirms independently. LANDED: both sentences "
        "qualified by route; D34's file list corrected."
    ),
    "X01": (
        "UPHELD. The v2 CHECK ADMITS the required row shape; it does not enforce it, and a "
        "`pending` row with `attempts > 1` satisfies it too. D02's original wording turned a "
        "one-way implication into a biconditional. LANDED: D02 reads as a permission, and "
        "`attempts == 1` is pinned by test rather than inferred from the schema."
    ),
    "X02": (
        "UPHELD, blocking, and the sharpest finding of the wave. D15/D16 were unconditional, yet "
        "the source runs outside every Cement transaction and may commit to the same ledger - which "
        "the required revision-race fixture does deliberately through `revise_operation`. A correct "
        "implementation fails the literal reading. LANDED: D15 restated as zero "
        "submission-attributable mutation with its comparison window named; D16 scoped to failures "
        "before commit."
    ),
    "X03": (
        "UPHELD, and correctly narrowed by the reviewer itself: swept for stale counts, byte "
        "lengths and SHAs, the structural inventory yields exactly ONE stale anchor - D27's "
        "869-872, three lines before its four census assertions. Every other stated figure "
        "reproduces. Same defect as A09, reached by a different lens. LANDED: D27 cites the test by "
        "NAME."
    ),
    "X04": (
        "UPHELD against the contract. D06's ONE-seam/single-writer obligation is structural, and "
        "every probe against it was behavioural - duplicated but equal SQL writers satisfy every "
        "footprint and differential assertion. Verdict row D06 reaches the same conclusion. LANDED: "
        "the pin spies the seam's call graph, not the footprint."
    ),
    "X05": (
        "UPHELD as a claim-soundness defect. D19's caller-level indistinguishability is stronger "
        "than any library can guarantee: the caller owns the adapter and can observe its state, "
        "timing, logs, and external effects. Verdict row D19 confirms independently, so the council "
        "rule accepts. LANDED: section 12 V-D19 scopes it to observations through the raised Cement "
        "exception."
    ),
    "X06": (
        "UPHELD IN PART, with the boundary ruled. ACCEPTED on negative form: D23, D25 and D33 told "
        "the reader what may not be written, which is the pink-elephant shape the project bans, and "
        "they govern SHIPPED prose - the worst place for it. All three are now positive. REJECTED "
        "on provenance: measurements, SHAs, baselines and named conventions are this document's "
        "PAYLOAD, and the Authoring rule targets dates, discovery narration and origin stories. A "
        "decision record stripped of its measurements stops being checkable, and the same CLAUDE.md "
        "funds measurements as commit-body payload."
    ),
    "X07": (
        "UPHELD. 'Invokes `self.candidate_source` and nothing else' is false on every successful "
        "call, each of which also validates arguments, reads the operation revision, reads the "
        "clock, and writes three rows. LANDED: P04 scopes 'nothing else' to GENERATION authority - "
        "no per-call source, no fallback source, no second attribute read."
    ),
    "Y01": (
        "UPHELD, blocking. `propose` with `candidate_source is None` AND an absent operation was "
        "unruled, and the two orders differ observably: zero transactions against one read. Verdict "
        "row X03 confirms independently. LANDED: D35 publishes the four-step precedence - "
        "arguments, configuration, lookup, invocation - and D21 carries the cross-reference."
    ),
    "Y02": (
        "UPHELD, blocking, and broader than A07. The accepted candidate runtime shape, the "
        "provenance byte limit, and the ownership split between DIRECT `ValidationError` and "
        "SOURCE-BACKED containment were all undefined. Verdict rows X01 and X02 confirm both halves "
        "independently. LANDED: four candidate rows plus the malformed-RETURN row in section 7; "
        "D38 rules the ownership split and names the secret-carrying `items` case that settles it."
    ),
    "Y03": (
        "UPHELD, blocking. D01 counted the proposals row and specified nothing about it, so a "
        "conforming writer could omit the provenance hash, the pending status, or the event binding "
        "and still pass every count. LANDED: D42 states the row shape, including `status_sequence` "
        "bound to the `proposal.created` event's own `sequence` and NULL review fields by schema "
        "default."
    ),
    "Y04": (
        "UPHELD. 'Caller-supplied identifier of any kind' bans `partition` and `operation`, which "
        "the signature requires, and would ban domain identifiers inside the input and the "
        "provenance that Cement stores verbatim. LANDED: D04 scopes the ban to ledger row identity "
        "and deduplication keys."
    ),
    "Y05": (
        "UPHELD against the contract, already satisfied by the code. D17 named the clock seam and "
        "not its cardinality, so two conforming writers could give the request, proposal and event "
        "different timestamps. LANDED: D17 states one `self._now` inside the write transaction "
        "serving all three rows; section 12 V-D17 carries the M3.1 grounds - a clock read ahead of "
        "the authoritative plan can commit a row older than its own build."
    ),
    "Y06": (
        "UPHELD. A source that reenters the same `System` opens a Cement-held connection reporting "
        "`in_transaction is True`, which D11 forbade unconditionally and which no library can "
        "prevent. LANDED: D11 scopes the quantifier to transactions the SUBMISSION CALL holds, "
        "which is the property that actually matters - submission never holds the lock across "
        "adapter code."
    ),
}


def main() -> int:
    check = "--check" in sys.argv
    document = json.loads(TABLE.read_text())
    rows = document["rows"]
    ids = [row["id"] for row in rows]

    missing = [i for i in ids if i not in DISPOSITIONS]
    extra = [i for i in DISPOSITIONS if i not in ids]
    if missing or extra:
        print(f"MISSING DISPOSITIONS: {missing}\nUNKNOWN IDS: {extra}")
        return 2

    for row in rows:
        row["main_disposition"] = DISPOSITIONS[row["id"]]

    rendered = json.dumps(document, indent=2) + "\n"
    if check:
        same = rendered == TABLE.read_text()
        print(f"IN-SYNC: {same}")
        return 0 if same else 1

    TABLE.write_text(rendered)
    unfilled = sum(1 for row in rows if row["main_disposition"] == "unknown")
    severities: dict[str, int] = {}
    for row in rows:
        severities[row["severity"]] = severities.get(row["severity"], 0) + 1
    print(f"ROWS: {len(rows)}\nDISPOSED: {len(DISPOSITIONS)}\nUNFILLED: {unfilled}")
    print("SEVERITY: " + ", ".join(f"{k}={v}" for k, v in sorted(severities.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
