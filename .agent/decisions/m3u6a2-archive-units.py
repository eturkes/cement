"""Move M3's DONE unit blocks to .agent/archive/m3-units.md, leaving one summary each.

Replay from the pre-archive roadmap reproduces both files byte-identically; a rerun on the
post-archive tree is a NO-OP. The guard is BLOCK-vs-SUMMARY equality, not block PRESENCE:
every archived unit keeps its `  - M3.<id> ` line, so a presence test passes on the archived
tree and re-emits the archive from the summaries alone - measured, that silently rewrote
147540 B of detail down to 6913 B while leaving the roadmap byte-stable, which is the shape
no roadmap diff exposes.
"""
import pathlib, re, sys

ROADMAP = pathlib.Path(".agent/roadmap.md")
ARCHIVE = pathlib.Path(".agent/archive/m3-units.md")

SUMMARIES: dict[str, str] = {
"M3.1": """  - M3.1 DONE tier=kernel tags=- depends=none - est calibration -> 1 session. Deleted the
    `authority()` callback and its scaffolds: `AuthorityCheck`, the constructor keyword,
    `_authorize` and all 11 call sites gone; both double-plan authorization windows collapsed to
    ONE locked plan; every actor/reviewer capture, validation, persistence and event survives;
    `store.py` byte-identical at `SCHEMA_VERSION` 2. Suite 548 -> 548 (11 deleted, 21 rewritten,
    11 added). `main=` 92% 220K/240K, `mate=` 54% 129K/240K.
    Contract `.agent/decisions/m3u1-contract.md` · detail `.agent/archive/m3-units.md#m31`.""",

"M3.2a": """  - M3.2a DONE tier=kernel tags=oracle depends=none - est 2 -> 3 sessions (1.50).
    Store-owned enforced-read capability behind an unchanged public seam: rolled-back
    transaction + deny-by-default authorizer allowlisting pragmas by NAME + percent-encoded
    existing-only `file:` URI `mode=ro`, classified by `sqlite_errorcode` alone. Both headline
    defects closed against a real ledger. Suite 551 -> 600; battery 49 tests / 22 obligations;
    19 mutants / 0 survivors. `main=` 93% 223K/240K (s1 75, s2 80), `mate=` 65% 155K/240K.
    Contract `.agent/decisions/m3u2a-contract.md` · detail `.agent/archive/m3-units.md#m32a`.""",

"M3.2b": """  - M3.2b DONE tier=kernel tags=oracle depends=M3.2a - est 3 -> 4 sessions (1.33).
    One-snapshot P1-P6 verification plus `evaluate` behind a pure `resolve`; failed
    verification, verified miss and verified hit stay distinct; 1/1,000/50,000 costs published
    with per-point provenance. +56/-1 production lines at `b5916a9`. Suite 600 -> 635; battery
    35 tests; 23 mutants / 1 ruled survivor closed by B34; differential 26 probes / 0
    divergences. `main=` 86/92/92/97%, `mate=` 68% 163K/240K.
    Contract `.agent/decisions/m3u2b-contract.md` · detail `.agent/archive/m3-units.md#m32b`.""",

"M3.3": """  - M3.3 DONE tier=kernel tags=oracle depends=M3.1 - est 4 -> 4 sessions. Request-free
    direct and source-backed submission over unchanged schema v2: `submit_proposal(...,
    *, candidate)` and `propose(...)`, both returning the proposal id, so arity makes both
    illegal states unrepresentable; `CandidateSourceError` normalization leaks nothing. Also
    deleted `System.__init__`'s `callable(getattr(source, "propose", None))` pre-flight, a ruled
    public behaviour change. Suite 635 -> 744; battery 73 tests / 52 obligations; 48 mutants /
    0 survivors. `main=` 84/100/96/86%, `mate=` 99% 239K/240K.
    Contract `.agent/decisions/m3u3-contract.md` · detail `.agent/archive/m3-units.md#m33`.""",

"M3.4": """  - M3.4 DONE tier=kernel tags=oracle depends=M3.3 - est 4 -> 4 sessions. Froze the
    request-free proposal/read/review/report/event seams behind one internal binding adapter at
    schema v2: fork 1 = COMPOSE (`_proposal_bindings` issues the complete statement per
    selection), fork 2 = R2+ four fields with `status` newly `accepted`/`corrected`/`rejected`.
    Owns exactly EIGHT `requests` sites in `system.py`. Suite 744 -> 811; battery 55 tests / 40
    obligations; 44 mutants / 4 NAMED ruled survivors; differential 42 probes / 2 rulings.
    `main=` 84/98/76/90%, `mate=` 100% 240K/240K.
    Contract `.agent/decisions/m3u4-contract.md` · chronology
    `.agent/archive/m3u4-chronology.md` · detail `.agent/archive/m3-units.md#m34`.""",

"M3.5a": """  - M3.5a DONE tier=kernel tags=- depends=M3.2b,M3.4 - est 4 -> 4 sessions. Added the
    `resolve` root leaf and `proposal submit` with exact exit and payload contracts: fork 1 =
    ENVELOPE CORE with `@PATH` cut and the cap DERIVED, fork 2 = one fixed seven-key payload
    across all three resolve states with three-valued `matched`. Exported
    `PROVENANCE_MAX_BYTES`. Suite 811 -> 901; battery 30 tests / 30 obligations, 30/30 red at
    `c8b82cd` and green at HEAD; 128 mutants / 1 NAMED ruled survivor (M41); 23 amendments over
    18 amended obligations. `main=` 85/79/95/100%, `mate=` 97% 232K/240K.
    Contract `.agent/decisions/m3u5a-contract.md` · detail `.agent/archive/m3-units.md#m35a`.""",

"M3.5b": """  - M3.5b DONE tier=kernel tags=- depends=M3.5a - est 3 -> 3 sessions. Removed the
    `handle`/`request`/source CLI grammar, imports, fixtures, help and CLI-route operator prose
    through `m3u5b-burden.py`'s 7 occurrence-asserted EDITS (`cli.py` -44/+1); library-API prose
    naming `System.handle` was deliberately DEFERRED to M3.6a. Census 28 leaves / 35 nodes,
    `parser_shape` 151 `ebd2ac811bd9776d`. Suite 901 -> 949; battery 48 clauses / 28
    obligations; sweep 48 killed / 0 misdirected / 0 survivors; gate 5 `m3u5b-doc-parse.py` new.
    `main=` 80/96/86%, `mate=` 100% 240K/240K.
    Contract `.agent/decisions/m3u5b-contract.md` · detail `.agent/archive/m3-units.md#m35b`.""",

"M3.6a": """  - M3.6a SPLIT INTO M3.6a1 + M3.6a2 + M3.6a3 at its own pre-open measurement. `main=` 88%
    212K/240K; no teammate dispatched. Unsplit it measured 3.2x M3.5b's frame count plus a
    7-site demo rewrite, a transcript regeneration and a five-document prose pass. Split axis =
    CONSUMER-MIGRATION-BEFORE-DELETION, available because both APIs shipped simultaneously.
    Detail `.agent/archive/m3-units.md#m36a`.""",

"M3.6a1": """  - M3.6a1 DONE tier=kernel tags=- depends=M3.5b - est 3 -> 8 sessions (2.67, the project's
    largest overrun; driver measured four sessions running = ENTRY COST, not the work).
    Migrated every consumer off `handle`/`request_status` while both still shipped, through one
    idempotent count-asserted `m3u6a1-surgery.py`: 23 RETAIN definitions over 45 sites, the four
    `handle`-driven fixture helpers plus `_promoted_example_ledger` re-based onto
    `propose`/`get_proposal`/`review`, four MISS-GUARDED sites moved onto `resolve`, the demo's
    seven sites rewritten with the set checkpoint moved after each artifact promotion, and the
    README transcript regenerated. Suite 949 -> 979; 30 obligations / 19 corrections; battery 30
    tests, 23 red / 6 green at `6fb4d92`; 92 mutants / 92 killed / 0 survivors over 29 clauses;
    36 attack rows disposed. `main=` 82-98%, `mate=` 86% 206K/240K.
    Contract `.agent/decisions/m3u6a1-contract.md` · detail `.agent/archive/m3-units.md#m36a1`
    · tips `archive/m3u6a1-{test,rev,gate}`, `archive/m3u6a2-scout`.""",
}

ANCHORS = {"M3.1": "m31", "M3.2a": "m32a", "M3.2b": "m32b", "M3.3": "m33", "M3.4": "m34",
           "M3.5a": "m35a", "M3.5b": "m35b", "M3.6a": "m36a", "M3.6a1": "m36a1"}

text = ROADMAP.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
starts = [(i, re.match(r"^  - (M3\.\S+?)[ ]", l).group(1))
          for i, l in enumerate(lines) if re.match(r"^  - M3\.\S+?[ ]", l)]
blocks: dict[str, tuple[int, int]] = {}
for n, (i, unit) in enumerate(starts):
    end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
    blocks[unit] = (i, end)

absent = [u for u in SUMMARIES if u not in blocks]
if absent:
    sys.exit(f"ABORT: roadmap has no block for {absent}")

pending = [u for u in SUMMARIES
           if "".join(lines[slice(*blocks[u])]) != SUMMARIES[u].rstrip("\n") + "\n"]
if not pending:
    print(f"NO-OP: all {len(SUMMARIES)} blocks already archived")
    sys.exit(0)
if len(pending) != len(SUMMARIES):
    sys.exit(f"ABORT: mixed state, {len(pending)} of {len(SUMMARIES)} unarchived: {pending}")

archived: list[str] = [
    "# M3 unit records\n\n",
    "Per-unit detail for M3's closed units, moved out of `.agent/roadmap.md` because attached\n",
    "state rides every session whole and closed-unit detail was 88% of that file. The roadmap\n",
    "keeps one summary per unit; every ruling, measured number and standing instruction that\n",
    "binds a LATER unit stays in the roadmap or in `.agent/memory.md`. MILESTONE-REVIEW\n",
    "dispatches from each unit's committed contract in `.agent/decisions/`, never from here.\n",
]
for unit in SUMMARIES:
    start, end = blocks[unit]
    archived.append(f"\n## {unit} <a id=\"{ANCHORS[unit]}\"></a>\n\n")
    archived.extend(lines[start:end])

for unit, (start, end) in sorted(blocks.items(), key=lambda kv: -kv[1][0]):
    if unit in SUMMARIES:
        lines[start:end] = [SUMMARIES[unit].rstrip("\n") + "\n"]

ARCHIVE.write_text("".join(archived), encoding="utf-8")
ROADMAP.write_text("".join(lines), encoding="utf-8")
print(f"ARCHIVED: {len(pending)} blocks -> {ARCHIVE}  ({ARCHIVE.stat().st_size} B)")
print(f"ROADMAP: {len(text.encode('utf-8'))} B -> {ROADMAP.stat().st_size} B")
