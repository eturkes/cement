"""Structural validator for M3.4 wave-2 artifacts.

Usage:
    uv run python .agent/decisions/m3u4-wave2-validate.py <artifact.json>
    uv run python .agent/decisions/m3u4-wave2-validate.py --emit-seed verdicts
    uv run python .agent/decisions/m3u4-wave2-validate.py --emit-seed attack

The artifact's top-level ``kind`` selects the schema. Two kinds ship:

``verdicts``
    The diff-blind phase-1 divergence table. One row per LOCUS: a place where the
    acceptance contract admits more than one reading. The author states both readings
    and the outcome it expects; MAIN rules ``main_verdict`` afterwards.

``attack``
    The contract attack. One row per LENS: a claim in the contract, the attack that
    would falsify it, and the acceptance check that closes it. MAIN rules
    ``disposition`` afterwards.

Seeded ``id`` and ``locus`` values are MAIN-owned and may not be rewritten. Extension
rows are REQUIRED wherever the seed missed a real locus or lens: add ``X<n>`` rows to a
verdict table and ``Y<n>`` rows to an attack table. The seed is a floor, never a cap.

``main_verdict`` and ``disposition`` are MAIN-owned and exempt from the unfilled count.
The validator prints the exempt columns so a clean grade is never read as a closed table.
"""

from __future__ import annotations

import re
import sys

from wave_validate import StrictWave

UNKNOWN = "unknown"
PROSE_MIN = 40
# A `section` value is a POINTER, and the check is exactly the two things a pointer can be
# checked for: it resolves somewhere, and it stays short enough to be a pointer rather than
# an argument. Whether it points at the RIGHT place is MAIN's judgment at ruling time and
# no regex reaches it.
#
# Parsing the value as a citation LIST was tried and abandoned. Real tables cite ranges
# ("Sections 8.3, 9 and 12 S2 RULING"), whose internal commas collide with the element
# separator, and a locus with no number at all ("Contract preface, Sections 12 and 13").
# Each spelling costs a teammate round-trip while its table sits ungradeable, and the
# grammar never converges. Search for citations instead of parsing the whole string.
CITATION = re.compile(r"(?:§\s?|Sections?\s|\b[DPR])[0-9]{1,2}(?:[.\-][0-9A-Za-z]{1,3})?")
SECTION_MAX = 60
VERDICT_EXTENSION = re.compile(r"X[0-9]{1,3}")
ATTACK_EXTENSION = re.compile(r"Y[0-9]{1,3}")

VERDICT_FIELDS = ("section", "locus", "reading_a", "reading_b", "divergent", "expected",
                  "test_name", "main_verdict")
ATTACK_FIELDS = ("section", "locus", "claim", "attack", "severity", "reproduction",
                 "acceptance_check", "disposition")
MAIN_OWNED = {"main_verdict", "disposition"}
SEVERITIES = {"blocking", "material", "minor", "cleared", UNKNOWN}

# One row per locus where the contract admits two readings. Work the named locus.
VERDICT_LOCI: dict[str, str] = {
    "V01": "ReviewResult on reject: whether example_id and output are emitted as null keys or omitted",
    "V02": "ReviewResult.status vocabulary: accepted/corrected/rejected against the baseline's resolved/rejected",
    "V03": "review's return on accept versus correct: which fields differ and which must be byte-identical",
    "V04": "ProposalView without request_id: whether every remaining field keeps its baseline value exactly",
    "V05": "PendingProposalGap without request_id: identity of a gap when two proposals share an input_hash",
    "V06": "the confinement complement set: which definitions may name requests immediately after M3.4",
    "V07": "whether a module-level SQL constant counts as a definition naming requests, and under whose name",
    "V08": "case folding and identifier tokenizing: FROM REQUESTS, requests_scope, and a quoted \"requests\"",
    "V09": "get_proposal's error precedence: missing row, wrong partition, non-pending status, broken request binding",
    "V10": "proposals feed ordering and the status filter under the adapter: exact rows for status=all",
    "V11": "function_report pending count versus detail projection past the projection limit",
    "V12": "function_report pending detail ORDER: what may be asserted about the page and what may not",
    "V13": "review's stale-revision refusal: which decisions it applies to and what it raises",
    "V14": "review's conflict quarantine: artifacts suspended, events emitted, and their payload keys",
    "V15": "the private request-status write on reject versus accept/correct: rowcount checks and failure class",
    "V16": "adapter use inside review's write transaction: statement count and connection.in_transaction",
    "V17": "a proposal whose private request row is missing or mismatched: class, message, and which paths see it",
    "V18": "partition and operation colliders through every adapted read: tenant_a beside tenantXa, case variants",
    "V19": "scalar corruption of the MIDDLE and the LAST of three proposals read through the adapter",
    "V20": "cross-partition and cross-operation proposals: invisibility in every adapted read path",
    "V21": "the CLI proposal show and list payload key sets once request_id leaves the record",
    "V22": "whether any surviving public value reachable from a proposal, read, review or report carries request identity",
}

# One row per lens attacking a claim the contract makes. Work the named lens.
ATTACK_LENSES: dict[str, str] = {
    "A01": "D12's no-other-projected-value rule applied to the ReviewResult ruling's own removals",
    "A02": "the ruled status change from resolved to accepted/corrected: every surface that still says resolved",
    "A03": "D01's exactly ONE named private surface against the shipped adapter's actual member count",
    "A04": "D02's complement assertion: how a conforming-looking instrument could pass while an access hides",
    "A05": "D06's fragment-composition prohibition against the shipped adapter's own parameter handling",
    "A06": "D11's single shape test: what a shape it does not enumerate would look like when it breaks",
    "A07": "D13's design-smell clause: whether _proposal_record or _proposal_content actually grew",
    "A08": "D15's exact row writes and their order under the adapter's writer helper",
    "A09": "D17's exactly-one-example claim against every path through review, including quarantine",
    "A10": "D19's event sequencing and status_sequence binding under a changed return type",
    "A11": "D21's = versus LIKE isolation: whether the shipped fixtures actually carry the colliders",
    "A12": "D22's bounded detail and reachable tail against the adapter's own LIMIT handling",
    "A13": "D23's preserved-not-fixed ordering: an assertion that passes twice and fails on the third run",
    "A14": "D24's fail-closed scalars: which probes are fabricated and whether any is cited as a real-ledger repro",
    "A15": "D25 and D26 publication: whether prose alone teaches ReviewResult and the lost request identity",
    "A16": "D27's unqualified-form sweep for every qualifier the S2 rulings introduce",
    "A17": "section 7's work-list measurement: whether the shipped diff stayed inside it and what moved",
    "A18": "the fork-1 ruling's Z50 grounds: whether the shipped adapter really survives the M3.6b swap untouched",
}


EXEMPT = {"verdicts": ["main_verdict"], "attack": ["disposition"]}


TABLES = {
    "verdicts": dict(subjects=VERDICT_LOCI, fields=VERDICT_FIELDS, identity="locus",
                     extension=VERDICT_EXTENSION, section_pointer=True, paired=True, test_name=True,
                     strings=("section", "reading_a", "reading_b", "expected", "test_name", "main_verdict"),
                     prose=("reading_a", "reading_b", "expected"), exempt=EXEMPT["verdicts"]),
    "attack": dict(subjects=ATTACK_LENSES, fields=ATTACK_FIELDS, identity="locus",
                   extension=ATTACK_EXTENSION, section_pointer=True, severity_first=True,
                   severity_value=False, enums={"severity": SEVERITIES},
                   strings=("section", "claim", "attack", "severity", "reproduction", "acceptance_check", "disposition"),
                   prose=("claim", "attack", "reproduction", "acceptance_check"), exempt=EXEMPT["attack"]),
}
ENGINE = StrictWave(TABLES, doc=__doc__, main_owned=MAIN_OWNED, prose_min=PROSE_MIN,
                    citation=CITATION, section_max=SECTION_MAX, report="exempt")
VALIDATORS = ENGINE.validators
_seed = ENGINE.seed
main = ENGINE.main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
