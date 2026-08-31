#!/usr/bin/env python3
"""Fill the MAIN-owned `disposition` and `main_note` columns of m3u5b-attack.json.

    uv run python .agent/decisions/m3u5b-rule-attack.py [--check]

Idempotent, replayable from the teammate's committed table (wt/rev-m3u5b-1 @ 23935a2,
41 rows: 23 seeded A01-A23, 18 extension Y01-Y18). `--check` exits 1 when the table is
out of sync, so a later row addition fails loudly instead of going undisposed.

Dispositions:
  ACCEPTED  the attack lands; the contract, a gate or MAIN's product is wrong or short
  SCOPED    the attack lands only outside the obligation's real domain; the ruling names it
  REJECTED  the attack does not land against the shipped state
  CLEARED   the reviewer found no defensible alternative and MAIN concurs
  DEFERRED  real, but its owner is the polish register or a later unit

Counts the reviewer reported: 22 blocking, 4 material, 15 cleared.
MAIN's dispositions: 24 ACCEPTED, 2 SCOPED, 15 CLEARED.

Measurements this ruling rests on, derived by MAIN in the primary tree at 087093d:
  parser_shape omits action.help, action.choices and action.type; two D26 help rewrites
    left 151/ebd2ac811bd9776d unmoved
  test_cli: 105 failures, 102 cleared by the three re-based helpers, 3 re-based in place
  roadmap M3.6a = library lifecycle deletion, M3.7 = command-runtime relocation; NEITHER
    names cli.py, and post-removal cli.py holds no lifecycle or source residue
  gate 4 = 19 CHECK lines; gate 5 = 18 invocations over 5 surfaces, mutation-tested
  the seven EDITS delete five predicates and add none: a final-tree mutant set is EMPTY
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u5b-attack.json")
DUMP = dict(indent=2, ensure_ascii=True, sort_keys=False)

_CLEARED = (
    "CLEARED. The reviewer found no defensible alternative reading and MAIN concurs: "
    "the obligation admits one reading against the shipped parser, and the probe that "
    "would separate a second reading returns the same result either way."
)

# id -> (disposition, main_note)
RULINGS: dict[str, tuple[str, str]] = {
    "A01": ("CLEARED", _CLEARED),
    "A02": ("CLEARED", _CLEARED),
    "A03": ("CLEARED", _CLEARED),
    "A04": (
        "ACCEPTED",
        "Lands. D08's two literal conditions — no `_source` symbol, no name imported from "
        "`.source` — are satisfiable by an inline source class under a different name. They "
        "are necessary, not sufficient. D07 and D09 close the hole between them: no dispatch "
        "branch survives, and every reachable path constructs `System(args.db)` with no "
        "candidate-source argument. Gate 2 must encode the CONJUNCTION and add one runtime "
        "assertion that the constructed system's source is None, because an AST pin cannot see "
        "a source configured through a value.",
    ),
    "A05": ("CLEARED", _CLEARED),
    "A06": ("CLEARED", _CLEARED),
    "A07": (
        "ACCEPTED",
        "Lands, and it is the unit's most-confirmed finding: this row, Y07, verdict rows V15 "
        "and X26, and MAIN's own D26 measurement all reach it independently. "
        "`probe_parser_shape` digests dest, option strings, default, required, nargs, class and "
        "`allow_abbrev`. It digests no help, no `choices`, no `type`. D14's byte-equality claim "
        "therefore does not rest on the digest. V15 reading A replaces it with direct full-facet "
        "comparison (shared=28, equal=28, different=[]), and the uninstrumented facets are a "
        "polish row with its acceptance check written.",
    ),
    "A08": (
        "ACCEPTED",
        "Lands against the PIN, not against the practice. Section 9.1's six-module blob omits "
        "the examples tree, so an example-scope breach passes it silently. The teammate's own "
        "run already exceeded the pin — 18 protected paths verified, 6 runtime modules and 12 "
        "example files — which is exactly the gap: the practice is right and the written scope "
        "is short. Section 10 widens D15's scope pin to the examples tree, and gate 2 asserts "
        "against the named git object rather than against a second copy of the bytes. Y08 is "
        "the same defect reached from `errors.py`.",
    ),
    "A09": (
        "ACCEPTED",
        "Lands. D17 demands an all-check closure credential of 16; the executable probe grades "
        "19, and the roadmap already recorded 19. MAIN's rerun: rc 0 over 19 CHECK lines, with "
        "exactly five re-based and no others. Verdict row V19 rules the same defect. The "
        "contract's number is simply wrong.",
    ),
    "A10": (
        "ACCEPTED",
        "Lands, and MAIN's measurement corrects the number. `test_cli` showed 105 failures. "
        "Re-basing the three helpers cleared 102 of them together; 3 needed re-basing IN PLACE, "
        "each keeping its property on a surviving leaf. D18's '103 shielded assertions' is off "
        "by one and hides the 3-test residue. The correct triple is 105 / 102 / 3.",
    ),
    "A11": (
        "ACCEPTED",
        "Lands, same class as A04 on the test side. A negative symbol inversion accepts an "
        "inline replacement class and a renamed helper. The `hasattr(cement_cli, '_source')` "
        "absence assertions MAIN landed are strictly stronger than the zero call counts they "
        "replace, but absence of one name is still not absence of the route. Gate 2 pairs them "
        "with the runtime assertion named in A04.",
    ),
    "A12": (
        "ACCEPTED",
        "Lands, and it is the recursive form of this unit's own thesis. B02 never GRADES its "
        "migration narrative: the docstring can carry any census numbers and the test stays "
        "green, which is precisely why D20 exists — and D20's own fix inherits the defect. "
        "Gate 2 must derive B02's census numbers from `_parser()` and assert the docstring "
        "contains them, so the narrative becomes self-grading instead of merely correct today.",
    ),
    "A13": (
        "ACCEPTED",
        "Lands, and MAIN found and fixed exactly the two sentences at d54ddde: 'Use it instead "
        "of `handle` when you generate the candidate yourself' and 'Review a submitted proposal "
        "with the same `proposal review` command that the `handle` route uses'. Both sit in the "
        "proposal-submit section and both are absent from D22's locus table. The table is a "
        "FLOOR, and section 10 says so.",
    ),
    "A14": (
        "SCOPED",
        "Lands against an underspecified extractor and is answered by gate 5's construction "
        "rather than by its green result. Two controls exist for exactly this: an invocation "
        "floor of 18, which trips on a silent extractor regression, and a mutation test — "
        "injecting `cement ... handle support.reply --request-id t` into a README block turns "
        "the gate red at `README.md:102` with the argparse invalid-choice message and lifts the "
        "count to 19, and restoring turns it green. A green run alone would indeed prove "
        "nothing; the mutation is the credential.",
    ),
    "A15": (
        "ACCEPTED",
        "Lands. Keyword presence satisfies a naive D26 while root help omits every verb that "
        "tells a reader how to capture a proposal — which is exactly the state MAIN found: the "
        "`proposal` group help read 'inspect/review supervised proposals', naming no capture. "
        "Fixed at d54ddde with `submit/` added and the root description rewritten from "
        "'Supervised LLM fallback' to 'Supervised proposal capture'. Gate 2 asserts a capture "
        "VERB, not the noun.",
    ),
    "A16": (
        "ACCEPTED",
        "Lands. D27's supersession table has three rows — M3.5a D24, D25 and D27 — and omits "
        "M3.5a D26, whose source-import clause M3.5b inverts. MAIN's frame re-base already "
        "inverted it in the battery (`d26`'s source-import and `handle` clauses), so the code "
        "is right and the record is short by one row. Section 10 adds the fourth row.",
    ),
    "A17": (
        "ACCEPTED",
        "Lands as a STATED LIMIT rather than a repairable defect. A direct edit producing "
        "identical bytes is indistinguishable from the staged apply in any final-state battery; "
        "no diff-blind test can separate them, and inventing one would only move the "
        "unverifiable step. The procedural credential lives outside the battery: the commit "
        "record plus a rerun of `apply_stage(pathlib.Path('.'), 2)` over the committed EDITS, "
        "which aborts on a moved anchor. Section 11 records the limit instead of claiming "
        "coverage the battery does not have.",
    ),
    "A18": (
        "ACCEPTED",
        "Lands twice over, and both halves are MAIN's own defects. D03/D18 carry three "
        "incompatible cardinalities for one work list: prose 11, table 18 rows, measurement 17. "
        "The surplus table row `test_cli_channels_battery.py:139 _leaf_parser` is not a distinct "
        "frame. MAIN then found an eighteenth, PROSE-coupled frame the code census could not "
        "see — `test_cli_channels_battery.py` `test_d23_...`, which broke on the D22 prose edit "
        "alone. So the census undercounts in two independent ways: a wrong literal and a "
        "category it never scanned.",
    ),
    "A19": ("CLEARED", _CLEARED),
    "A20": ("CLEARED", _CLEARED),
    "A21": (
        "DEFERRED",
        "Lands. D25 states register properties with no acceptance gate naming a sentence "
        "parser, a register checker or a reproducible grading command, so MAIN's conformance "
        "pass is by hand and cannot rerun from a clean checkout. Owner is the polish register's "
        "existing 'port the human-facing register audit to committed state' row, which already "
        "carries the acceptance check and now has a third consumer. Verdict row X31 is the same "
        "finding; no fourth duplicate row is opened.",
    ),
    "A22": (
        "ACCEPTED",
        "Lands, and it is the most consequential finding for S3. Gate 3 as written mutates "
        "TOUCHED PREDICATES read from the final tree. The seven EDITS delete five predicates and "
        "add none, so that set is EMPTY and gate 3 passes vacuously. Section 11 redefines gate "
        "3's catalogue as REINSERTION mutants: re-add the removed leaf, each removed flag, the "
        "`.source` import, each dispatch branch and the `candidate_source=` construction, and "
        "require a NAMED red per mutant. That is the only mutation that can bind a removal.",
    ),
    "A23": (
        "SCOPED",
        "Lands only across a register boundary the contract failed to name. The project rule "
        "splits surfaces: human-facing prose a person reads at consumption time takes the "
        "ASD-STE100 register; machine-consumed and agent-consumed surfaces take the dense, "
        "symbol-forward project register. A test docstring is the second kind, so mandating "
        "narration there does not conflict with D25's caps on README and docs prose. Section 11 "
        "names both registers and their surfaces so the apparent contradiction cannot recur.",
    ),
    "Y01": (
        "ACCEPTED",
        "Lands. D14 cites D16 as the parser-shape carrier, but D16 specifies exit classes and "
        "payload key sets; D17 is what defines the digest re-base. A wrong cross-reference in a "
        "binding section sends the battery to the wrong obligation. Section 10 corrects it.",
    ),
    "Y02": (
        "ACCEPTED",
        "Lands. A kwargs dictionary configures `candidate_source` while leaving no named keyword "
        "node for a literal AST pin to find. This is A04's hole reached from the construction "
        "side, and it has the same answer: gate 2 asserts at RUNTIME that the constructed "
        "system's candidate source is None on every reachable CLI path, which no static shape "
        "can be made to guarantee.",
    ),
    "Y03": (
        "ACCEPTED",
        "Lands, and verdict row V18 rules it. M3.5a's contract supplies no named baseline for "
        "`proposal show` or `proposal list`, so D16's literal reading leaves three of its five "
        "leaves with no oracle at all. Reading B makes the M3.5a SHIPPED git object the "
        "preservation oracle, which resolves all five to mismatches=0.",
    ),
    "Y04": (
        "SCOPED",
        "Does not land against D24's real domain. `candidate.json` is a CALLER-SUPPLIED input "
        "file, not a value an earlier cement command produces. D24's placeholder grammar is "
        "`*_FROM_*` and `*_REPLACE_ME` — tokens whose producer is a preceding command — and "
        "X30's extractor already encodes exactly that. Section 10 states the domain so a future "
        "battery does not red on every shipped `< file` redirection.",
    ),
    "Y05": (
        "ACCEPTED",
        "Lands. Section 9's 56-hit figure names no vocabulary matcher, and three reasonable "
        "route vocabularies over the stated corpus give 53, 60 and 68. An unreproducible count "
        "in a binding section is worse than no count, because it reads as measured. Section 11 "
        "drops the figure and states the matcher-dependence instead of inventing a matcher after "
        "the fact.",
    ),
    "Y06": (
        "ACCEPTED",
        "Lands, and MAIN verified it independently against the roadmap. M3.6a deletes public "
        "lifecycle methods, leases, result models and exports; M3.7 relocates the command "
        "runtime to an optional example surface. NEITHER names `cli.py`, and post-removal "
        "`cli.py` holds no lifecycle or source residue for either to reach. D28's stated ground "
        "was false. The CONCLUSION survives on a different ground — `cli.py` took two commits "
        "each from M3.5a and M3.5b, and M3.6b's refusal fixtures and M3.9a's documentation "
        "rewrite both plausibly land there — and B02's docstring now says that instead.",
    ),
    "Y07": (
        "ACCEPTED",
        "Lands, and it sharpens A07. Reordering the surviving root command listing changes "
        "operator help while `parser_shape` stays identical and D13's set equality stays true. "
        "The help SHA moved and the digest did not. Same polish row.",
    ),
    "Y08": (
        "ACCEPTED",
        "Lands, and it is A08 reached from a second direction. A change to `errors.py` sits "
        "outside the sole owned runtime file yet passes D15, because six other runtime modules "
        "are absent from its scope pin. Section 10 widens the pin.",
    ),
    "Y09": (
        "ACCEPTED",
        "Lands, and MAIN is the proof: gate 1 was run from the working tree repeatedly this "
        "session before the frame re-bases were committed. Only D29 binds gate 2 to a committed "
        "checkpoint, so gates 1, 3 and 4 can support closure from uncommitted or mismatched "
        "bytes. The project rule already requires a gate backing a durable claim to rerun from "
        "committed state; the contract failed to bind it. Section 11 makes the closure "
        "credential require every gate rerun from the committed tip, with the tip SHA recorded "
        "beside each result.",
    ),
    "Y10": ("CLEARED", _CLEARED),
    "Y11": ("CLEARED", _CLEARED),
    "Y12": ("CLEARED", _CLEARED),
    "Y13": ("CLEARED", _CLEARED),
    "Y14": ("CLEARED", _CLEARED),
    "Y15": ("CLEARED", _CLEARED),
    "Y16": ("CLEARED", _CLEARED),
    "Y17": ("CLEARED", _CLEARED),
    "Y18": (
        "ACCEPTED",
        "Lands, and MAIN had already OVERRULED the disposition on the same grounds before "
        "reading this row; verdict row X27 is the third independent arrival. D22 dispositions "
        "README's `handle`/`request` return-state table `remove; no command reaches these "
        "states`. No COMMAND reaches them, but `System.handle` and `System.request_status` both "
        "survive and both return every listed status, so the table is live library-API "
        "documentation and removing it does what D22's own header forbids. Kept with six status "
        "rows intact and the CLI-shaped caller actions re-scoped at d54ddde.",
    ),
}


def main(argv: list[str]) -> int:
    check = argv[1:] == ["--check"]
    raw = TABLE.read_bytes()
    payload = json.loads(raw)
    rows = payload["rows"]
    ids = [row["id"] for row in rows]

    if (json.dumps(payload, **DUMP) + "\n").encode() != raw:
        print("table is not in canonical dump form", file=sys.stderr)
        return 1

    if set(ids) != set(RULINGS):
        missing = sorted(set(ids) - set(RULINGS))
        extra = sorted(set(RULINGS) - set(ids))
        print(f"undisposed rows: {missing}\nunknown rulings: {extra}", file=sys.stderr)
        return 1

    stale = [
        row["id"]
        for row in rows
        if (row["disposition"], row["main_note"]) != RULINGS[row["id"]]
    ]
    if check:
        if stale:
            print(f"out of sync: {stale}", file=sys.stderr)
            return 1
        print(f"IN SYNC: {len(rows)} rows disposed")
        return 0

    for row in rows:
        row["disposition"], row["main_note"] = RULINGS[row["id"]]
    TABLE.write_text(json.dumps(payload, **DUMP) + "\n", encoding="utf-8")
    print(f"DISPOSED: {len(rows)} rows, {len(stale)} changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
