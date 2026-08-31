#!/usr/bin/env python3
"""Fill the MAIN-owned `main_verdict` and `action` columns of m3u5b-verdicts.json.

    uv run python .agent/decisions/m3u5b-rule-verdicts.py [--check]

Idempotent, replayable from the teammate's committed table (wt/test-m3u5b-1 @ 1f0ce30,
70 rows: 30 seeded V01-V30, 40 extension X01-X40). `--check` exits 1 when the table is
out of sync, so a later row addition fails loudly instead of going unruled.

Verdict prefixes:
  CONFIRMED  the row's expected outcome is the ruled one; the battery encodes it as written
  SCOPED     the row overreaches; the ruling narrows its domain before the battery sees it
  CORRECTED  the row is WRONG against shipped code or against a MAIN measurement
  ACCEPTED   the row found a real gap outside the shipped code

`action` is the battery instruction:
  ENCODE         pin as ruled
  ENCODE-SCOPED  pin the narrowed form named in the verdict
  GATE-SPEC      binds how S3 CONSTRUCTS gate 2 or gate 3, not a battery assertion
  PROBE          record, never red
  DEFER          polish register

Measurements this ruling rests on, all derived by MAIN in the primary tree at 75f92b2:
  post-removal census 28 leaves / 35 nodes; parser_shape 151 actions / ebd2ac811bd9776d
  151 = 116 action lines + 35 node lines, measured rather than added
  cli.py -44/+1 over the seven occurrence-asserted EDITS; no hand edit
  gate 4 = 19 CHECK lines, PASS; exactly 5 re-based, lost_baseline_leaves ['handle','request']
  BASELINE_LEAVES keeps both members; the frozenset records c8b82cd, the EXPECTATION moved
  fixture re-base cleared 102 of 105 test_cli failures; 3 tests re-based in place
  17 code-coupled frames + 1 prose-coupled frame (test_d23) actually required edits
  gate 5 = 5 surfaces, 18 invocations, 0 parse failures, 3 control classes, rc 0
  help/choices/type mutants leave 151/ebd2ac811bd9776d unmoved: the digest omits all three
  cli.py holds 0 bare `65_536`; one submit_proposal call site, cli.py:627
  suite 901 tests OK rc 0
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u5b-verdicts.json")
DUMP = dict(indent=2, ensure_ascii=True, sort_keys=False)

_CENSUS = (
    "MAIN measured 28 leaves and 35 nodes from `_parser()` after the removal, and "
    "parser_shape re-derived to 151 actions and `ebd2ac811bd9776d`. "
)
_FRAMES = (
    "Landed this session as part of the frame re-base; the suite is green at 901 tests. "
)

# id -> (main_verdict, action)
RULINGS: dict[str, tuple[str, str]] = {
    # ---- refusal grammar, D05-D11 -----------------------------------------
    "V01": (
        "CONFIRMED. `handle` is no longer a choice of the `command` subparser, so argparse "
        "refuses it before any dispatch code runs. Routing through `_UsageError` rather than a "
        "dispatch branch is the whole point: a dispatch-branch refusal would mean the leaf still "
        "exists and merely declines.",
        "ENCODE",
    ),
    "V02": (
        "CONFIRMED. Same channel as V01 with no positional of its own. The message must name "
        "`command` as the offending argument, which distinguishes a removed ROOT command from a "
        "removed leaf under a surviving group.",
        "ENCODE",
    ),
    "V03": (
        "CONFIRMED. D05's complement is free: argparse's invalid-choice text enumerates the twelve "
        "survivors, so one assertion pins both the refusal and the survivor set. Encode the "
        "enumeration as a set comparison against the census, never as a substring of the message.",
        "ENCODE",
    ),
    "V04": (
        "CONFIRMED. Decide over the module AST, not a text grep. A grep matches `_source` inside a "
        "docstring or a comment and reports a symbol that no longer exists; the AST answers the "
        "question actually asked.",
        "ENCODE",
    ),
    "V05": (
        "CONFIRMED. `from .source import CommandCandidateSource` left with the helper. Decide over "
        "import nodes so a re-import under an alias cannot pass.",
        "ENCODE",
    ),
    "V06": (
        "CONFIRMED. Both dispatch branches went with the seven EDITS. Decide over `_run`'s AST for "
        "the same reason as V04.",
        "ENCODE",
    ),
    "V07": (
        "CONFIRMED. The `source = None` construction collapsed to `System(args.db)`. Every "
        "reachable CLI path now constructs with the database alone, which is the property D09 "
        "actually needs — a `candidate_source=None` keyword would satisfy a weaker reading.",
        "ENCODE",
    ),
    "V08": (
        "CONFIRMED. `--request-id` must be refused by every one of the 28 surviving leaves, with "
        "the exact message and exit recorded per leaf rather than asserted uniformly.",
        "ENCODE",
    ),
    "V09": (
        "CONFIRMED. Same shape as V08 over the four source flags. The four-by-28 matrix is the "
        "assertion; a spot check on one leaf is not.",
        "ENCODE",
    ),
    "V10": (
        "CONFIRMED, reading A. The exemption is whatever the LIVE parser resolves to a surviving "
        "option, not whatever the removed flag's original arity would have accepted. Reading B "
        "asserts `expected one argument` for the twelve `--r`/`--re` retry-failed cells, which "
        "would pin a message produced by an arity that no longer exists anywhere in the parser. "
        "Encode the measured collision map: `--r`/`--re` bind reviewer, reason or receipt-id on 6 "
        "leaves; `--s` binds status on `proposal list` and scope-hash on `promote`, while "
        "`proposal submit` rejects `--s` because it sets `allow_abbrev=False`. Every unclaimed "
        "cell says `unrecognized arguments`.",
        "ENCODE-SCOPED",
    ),
    "V11": (
        "CONFIRMED. Walk every node, not the root. The ban covers help strings at all 35 nodes, "
        "and X10's normalization ruling binds how the spellings are compared.",
        "ENCODE",
    ),
    # ---- census and preservation, D12-D15 ---------------------------------
    "V12": (
        "CONFIRMED. Set equality in both directions, never cardinality. " + _CENSUS,
        "ENCODE",
    ),
    "V13": (
        "CONFIRMED, and this is the row the census design rests on. The teammate re-derived the "
        "c8b82cd collision independently: 28 leaves and 35 nodes there too, with INVERSE two-leaf "
        "sets and shape `154 / af19339c3995c97d`. A count-only census therefore cannot separate "
        "'both M3.5a leaves landed and both M3.5b leaves left' from 'neither happened'. Exhibit "
        "the collision in the battery so the set-difference assertions read as load-bearing.",
        "ENCODE",
    ),
    "V14": (
        "CONFIRMED. Derive the twelve root commands from `_parser()`. A transcribed list passes "
        "against a parser that lost a command.",
        "ENCODE",
    ),
    "V15": (
        "CONFIRMED, reading A. Direct full-facet baseline comparison, measured shared=28, "
        "equal=28, different=[]. Reading B is UNSOUND and its own controls prove it: D14 claims "
        "the parser_shape digest carries choices, types and help, and independent choices, type "
        "and help mutants each leave 151/`ebd2ac811bd9776d` unmoved. Delegating leaf preservation "
        "to a digest that omits three of the facets it is trusted for would make this obligation "
        "pass on a leaf whose help had been rewritten into a lie. See X26 for the same defect in "
        "B02's docstring, corrected at 75f92b2.",
        "ENCODE-SCOPED",
    ),
    "V16": (
        "CONFIRMED. " + _CENSUS + "The digest is re-derived, never transcribed from the contract.",
        "ENCODE",
    ),
    "V17": (
        "CONFIRMED. Assert against the named git object, not against a second copy of the bytes. "
        "The teammate verified 18 protected paths: 6 runtime modules and 12 example files.",
        "ENCODE",
    ),
    "V18": (
        "CONFIRMED, reading B. The M3.5a SHIPPED git object is the preservation oracle. Reading A "
        "takes 'from M3.5a's contract' literally and leaves `proposal show`, `proposal list` and "
        "`proposal review` with unresolved_contract_oracles=3, which makes the obligation "
        "uncheckable for three of its five leaves. Reading B requires mismatches=0 across all "
        "five, retaining submit `{'proposal_id'}` and resolve `{'artifact_hash','checks',"
        "'entries','function_hash','matched','output','passed'}`.",
        "ENCODE-SCOPED",
    ),
    "V19": (
        "CORRECTED against the contract, reading B. Gate 4 has NINETEEN checks, not the sixteen "
        "D17 claims; the roadmap already recorded 19. MAIN's rerun: rc 0 over 19 CHECK lines, "
        "leaves=28, nodes=35, actions=151, digest `ebd2ac811bd9776d`, lost_baseline_leaves "
        "`['handle','request']`. Exactly five checks were re-based and no others. "
        "`BASELINE_LEAVES` keeps both members because the frozenset records c8b82cd history; the "
        "EXPECTATION is what moved. Second contract-claim defect of this unit.",
        "ENCODE-SCOPED",
    ),
    # ---- test surfaces, D18-D21 -------------------------------------------
    "V20": (
        "CONFIRMED. The shared `submission()` builder mirrors `examples/echo_adapter.py` byte for "
        "byte, and `submit()` asserts the acknowledgement key set is exactly `{'proposal_id'}` — "
        "which carries the property the removed `review_required` status assertion held. Re-basing "
        "the three helpers cleared 102 of 105 `test_cli` failures together. " + _FRAMES,
        "ENCODE",
    ),
    "V21": (
        "CONFIRMED. `x26` is fully INVERTED to the post-removal property rather than deleted. " + _FRAMES,
        "ENCODE",
    ),
    "V22": (
        "CONFIRMED, and this is the sharper half of D19. A `mock.patch.object` spy on a deleted "
        "symbol RAISES; it does not fail. `d24`'s spies became `hasattr(cement_cli, '_source')` "
        "absence assertions, which are strictly stronger than a zero call count — zero calls is "
        "satisfiable by a live-but-unreached symbol, absence is not. " + _FRAMES,
        "ENCODE",
    ),
    "V23": (
        "CONFIRMED, landed at 1880241 and corrected again at 75f92b2. B02 now records the 30 to 28 "
        "and 37 to 35 reversal, D24's zero-call clause becoming an absence assertion, and D28's "
        "standing refusal to re-pin `cli.py` citing M3.6a and M3.7 as the scheduled edits.",
        "ENCODE",
    ),
    "V24": (
        "CONFIRMED. The duplication stays: importing the graded function would make the check "
        "circular. Re-derived to 151 actions and `ebd2ac811bd9776d`.",
        "ENCODE",
    ),
    # ---- documentation, D22-D26 -------------------------------------------
    "V25": (
        "CONFIRMED, landed at d54ddde. The quick start reaches a proposal through `proposal submit "
        "--submission` and names no removed command. Gate 5 measures the whole shipped set: 5 "
        "surfaces, 18 invocations, 0 parse failures.",
        "ENCODE",
    ),
    "V26": (
        "CONFIRMED, and BOTH directions are defects. `System.handle` prose survives byte-identical: "
        "the API example with its `request_id=` argument, `docs/architecture.md` steps 1-3, "
        "`docs/threat-model.md:78` and `examples/hospital_ocr/README.md`. Deleting it pre-empts "
        "M3.6a's own doc pass and breaks the track order.",
        "ENCODE",
    ),
    "V27": (
        "CONFIRMED, scoped by X37's ruling. 'Every invocation' means every invocation inside a "
        "fenced shell block; inline prose references legitimately omit required positionals and "
        "cannot parse. Gate 5 ships as `.agent/decisions/m3u5b-doc-parse.py` and measures 18 "
        "invocations across 5 surfaces with 0 failures, behind three control classes.",
        "ENCODE-SCOPED",
    ),
    "V28": (
        "CONFIRMED. X30 already implements this and already treats `proposal submit` as a producer "
        "of `prop_REPLACE_ME`. The rewritten quick start keeps `proposal list` ahead of `proposal "
        "show prop_REPLACE_ME` inside the same block, so the orphan set stays empty.",
        "ENCODE",
    ),
    "V29": (
        "CONFIRMED, landed at d54ddde. Root help named no request lifecycle but its DESCRIPTION "
        "still sold one. `Supervised LLM fallback ...` became `Supervised proposal capture that "
        "compiles confirmed behavior into exact deterministic artifacts, then answers inputs from "
        "the promoted function set`, and `proposal` gained `submit/` in its group help. Map rows "
        "S4-C01, S4-C07 and S3-054 called both. Neither edit moves gate 4, because the digest "
        "omits help text entirely.",
        "ENCODE",
    ),
    "V30": (
        "CONFIRMED. D01's headline: the LIBRARY surface is untouched. `System.handle` and "
        "`System.request_status` stay public, and no shipped prose offers an operator route to "
        "either. Encode both halves — public in the module, absent from the parser.",
        "ENCODE",
    ),
    # ---- extension rows ---------------------------------------------------
    "X01": (
        "CONFIRMED. A raw failing-test count is not reproducible across a gate-4 re-base; a frame "
        "work list is. Measured: the post-removal gate showed 118 failures against the burden's "
        "predicted 119, and `test_d27_...` passes where the burden showed it failing — plausibly "
        "because the burden run did not re-base gate 4 and this session did. Unconfirmed, and "
        "exactly why the count is the wrong unit.",
        "ENCODE",
    ),
    "X02": (
        "CONFIRMED, and it is MAIN's own defect. D03/D18 carry THREE different numbers for one work "
        "list: D18's prose says eleven, its table has 18 rows, and the measurement is 17. The "
        "surplus table row is `test_cli_channels_battery.py:139 _leaf_parser`, which is not a "
        "distinct frame. The teammate's total_frames=17 is right for CODE-coupled frames. MAIN then "
        "found an EIGHTEENTH, PROSE-coupled frame the census could not see: "
        "`test_cli_channels_battery.py` `test_d23_...` broke on the D22 prose edit alone. So the "
        "true touched total is 18 by coincidence of arithmetic and different in membership.",
        "ENCODE-SCOPED",
    ),
    "X03": (
        "CONFIRMED. Every deletion went through `apply_stage(pathlib.Path('.'), 2)` over the "
        "committed anchored EDITS table; no hand edit was made. `cli.py` moved -44/+1. A moved "
        "anchor aborts rather than applying, which is the property that makes the removal replayable.",
        "ENCODE",
    ),
    "X04": (
        "CONFIRMED. Constructor, models, schema, source runtime, adapter protocol and demo are all "
        "outside the write set. Assert the boundary positively against git objects rather than "
        "inferring it from an unchanged diff.",
        "ENCODE",
    ),
    "X05": (
        "CONFIRMED. M3.5a is DONE and its contract is history. The supersession is recorded in "
        "M3.5b's D27 and the affected tests are re-based IN PLACE, so no M3.5a record is rewritten. "
        "Where a re-based docstring carried an M3.5a amendment verbatim, the amendment stayed and "
        "an M3.5b note was appended beneath it.",
        "ENCODE",
    ),
    "X06": (
        "ACCEPTED, and the ownership claim is CORRECTED. M3.5a's deferral named M3.5b as owner "
        "because the weakness bites on removal predicates. M3.5b DECLINED the global grammar "
        "change — disabling abbreviation repo-wide breaks `--part`, `--bun` and `--in` for existing "
        "callers and needs its own mandate — and closed the removal half locally instead: D06 "
        "refuses every proper prefix of a removed flag over all 112 removed-flag/leaf combinations, "
        "D10 exempts prefixes a surviving flag legitimately claims. The polish row now carries the "
        "public-grammar residue alone, owned by no unit.",
        "DEFER",
    ),
    "X07": (
        "CORRECTED. D06 and D10 do not conflict; D10 is D06's exemption clause and takes "
        "precedence where the live parser resolves a token to a surviving option. V10 reading A "
        "fixes how that precedence is decided. Encode the conjunction, not either half.",
        "ENCODE-SCOPED",
    ),
    "X08": (
        "ACCEPTED and DISCHARGED. M3.5a deferred naming a constant for `cli.py:370`'s bare "
        "`65_536` bounding `--source-command`. That literal lived inside `_source` and left with "
        "it. Measured: `cli.py` now holds ZERO bare `65_536`. The deferral's first clause is moot "
        "and its second is satisfied, so the polish row is pruned. Obligations `x11` and `d16` "
        "strengthen from 'exactly one, and it is the source-command bound' to 'no bare copy "
        "survives'.",
        "ENCODE",
    ),
    "X09": (
        "CONFIRMED. The seven-edit EDITS table deletes code and cannot teach anything. D26 needed "
        "two help-string edits OUTSIDE that table, applied by hand and verified not to move the "
        "digest: the root description and the `proposal` group help. A contract that lists its "
        "source plan as exhaustive and also carries a help obligation is internally inconsistent "
        "until one of them names the other.",
        "ENCODE",
    ),
    "X10": (
        "CONFIRMED. Normalize flag and identifier spellings before scanning. A prose-phrase scan "
        "passes on help text containing `--request-id` or `request_id` while failing on 'request "
        "id', which inverts the obligation's sensitivity.",
        "ENCODE-SCOPED",
    ),
    "X11": (
        "CONFIRMED. `test_usage_errors_and_oversized_stdin_are_machine_readable` moved to "
        "`resolve --input -`, and it needs `self.register('echo')` first because M3.5a D13's "
        "existence check precedes `--input` parsing — without the registration, exit 5 pre-empts "
        "the cap and the test measures the wrong refusal. " + _FRAMES,
        "ENCODE",
    ),
    "X12": (
        "CONFIRMED. `test_function_eval_help_reuses_the_shipped_flag_register` retargets its "
        "`--input` register reference from `handle` to `resolve`, keeping the shared-input wording "
        "pin. " + _FRAMES,
        "ENCODE",
    ),
    "X13": (
        "CONFIRMED. `v27` becomes the inverse-set removal census, not two changed cardinalities. "
        "Set difference in both directions with the counts riding along. " + _FRAMES,
        "ENCODE",
    ),
    "X14": (
        "CONFIRMED. `v28` keeps its two-direction property over the reduced 28-leaf set. " + _FRAMES,
        "ENCODE",
    ),
    "X15": (
        "CONFIRMED. `x04` drops its deleted `_source` spy without weakening the composed "
        "entry-point assertion. " + _FRAMES,
        "ENCODE",
    ),
    "X16": (
        "CONFIRMED. `x11`'s aggregate-cap derivation survives; its assertion about the deleted "
        "source helper inverts, and strengthens to zero bare `65_536` per X08. " + _FRAMES,
        "ENCODE",
    ),
    "X17": (
        "CONFIRMED. `x21` expands from the two M3.5a leaves to the complete surviving CLI, which "
        "the source-grammar deletion makes both possible and necessary. " + _FRAMES,
        "ENCODE",
    ),
    "X18": (
        "CONFIRMED. `x22` inverts exactly two historical members and retains the other 26. "
        "Encode as a set operation so a third change cannot ride along. " + _FRAMES,
        "ENCODE",
    ),
    "X19": (
        "CONFIRMED. `v05` keeps every meaningful counter after the deleted builder counter leaves; "
        "a counter set that shrinks silently is how an isolation pin becomes a tautology. " + _FRAMES,
        "ENCODE",
    ),
    "X20": (
        "CONFIRMED. The battery's `_leaf_parser` caller set stops demanding a deleted `handle` node "
        "while retaining both M3.5a leaf assertions. " + _FRAMES,
        "ENCODE",
    ),
    "X21": (
        "CONFIRMED. Battery D03 removes the deleted source-builder patch and preserves exact "
        "resolve dispatch plus configured-source non-reach. " + _FRAMES,
        "ENCODE",
    ),
    "X22": (
        "CONFIRMED. Battery D16 keeps its aggregate-cap derivation and re-bases the coincidental "
        "literal count from one to zero. Same measurement as X08. " + _FRAMES,
        "ENCODE",
    ),
    "X23": (
        "CONFIRMED, with the control RELOCATED rather than deleted. `handle` was the CLI witness "
        "that a configured source IS reachable — the fact that stops `d24`'s two zeros from being "
        "vacuous. The CLI route is gone and the LIBRARY method survives, so the control moved onto "
        "`System.handle` itself: `status == 'fallback_failed'`, `code == "
        "'candidate_source_error'`. A control deleted rather than relocated turns an isolation pin "
        "into a tautology.",
        "ENCODE",
    ),
    "X24": (
        "CONFIRMED, resolved by X06. Battery D25's abbreviation-preservation clause inherits the "
        "DECLINE: legacy abbreviation is preserved deliberately, and `d25`'s `abbreviation_map` "
        "comparison is scoped to shared paths so a removal reports as a removal rather than as a "
        "`KeyError` instrument error. " + _FRAMES,
        "ENCODE-SCOPED",
    ),
    "X25": (
        "CONFIRMED. Battery D26 retains store, schema, submission footprint and option isolation "
        "while its source-import and `handle` clauses invert. `d26` now pins the removed leaf's "
        "refusal as `cement_cli._UsageError` whose message ENUMERATES the survivors, which is "
        "D05's free complement. " + _FRAMES,
        "ENCODE",
    ),
    "X26": (
        "ACCEPTED, and it caught a defect in MAIN's own D20 edit. The corrected B02 docstring still "
        "said the parser_shape digest carries 'changed default, help string, payload or dispatch'; "
        "only the default is true. `probe_parser_shape` digests dest, option strings, default, "
        "required, nargs, class and `allow_abbrev` — no help, no choices, no type. Proved by "
        "measurement: M3.5b rewrote the root description and the `proposal` group help under D26 "
        "and the digest held at 151/`ebd2ac811bd9776d`. Fixed at 75f92b2, and the uninstrumented "
        "facets are now a polish row with its acceptance check. Reading B.",
        "ENCODE",
    ),
    "X27": (
        "ACCEPTED. D22's locus table dispositions README's `handle`/`request` return-state table "
        "`remove; no command reaches these states`. OVERRULED, reading B. No COMMAND reaches those "
        "states, but `System.handle` and `System.request_status` both survive and both return "
        "them, so the table is live library-API documentation and removing it does exactly what "
        "D22's own header forbids. The table is KEPT with library_status_rows=6 intact and its "
        "CLI-shaped caller actions re-scoped: `Poll `request REQUEST_ID`` became `Poll "
        "`System.request_status``, and `retry `handle` with `--retry-failed`` became `call "
        "`System.handle` again with `retry_failed=True``. Third contract-claim defect this unit, "
        "and the teammate reached it diff-blind.",
        "ENCODE-SCOPED",
    ),
    "X28": (
        "ACCEPTED, reading B. D22's table assigns the opening `handle(request)` lifecycle fence "
        "zero dispositions, which is a gap rather than a KEEP. Ruling: the fence depicts the "
        "surviving `System.handle` pipeline, it contains zero literal `cement` invocations, and it "
        "is therefore protected on exactly the same grounds as every other `System.handle` locus. "
        "protected_fence_equal=True. Gate 5 does not reach it because it is a ```text fence, so "
        "the battery must assert the byte equality directly.",
        "ENCODE",
    ),
    "X29": (
        "CONFIRMED, landed at d54ddde. 'Only the `handle` and `request` route still carries a "
        "request identifier' became 'Only the `System.handle` and `System.request_status` library "
        "route ...'. The same re-scope was applied to the deployment-boundary sentence, which "
        "named a bare `handle` inside a CLI-command enumeration.",
        "ENCODE",
    ),
    "X30": (
        "CONFIRMED. Route classification is what protects them, not their file paths. "
        "`docs/architecture.md` steps 1-3, `docs/threat-model.md:78` and "
        "`examples/hospital_ocr/README.md` are library-route; `docs/adapter-protocol.md` is M3.7's "
        "and stays untouched. MAIN's sweep found zero remaining `cement <removed>` invocations "
        "across all of them.",
        "ENCODE",
    ),
    "X31": (
        "ACCEPTED. D25's register claim has no committed grader, so MAIN's conformance pass is "
        "by hand and cannot rerun from a clean checkout. This is the SAME row the polish register "
        "already carries twice — 'port the human-facing register audit to committed state' and its "
        "M3.1 duplicate — now with a third consumer. Do not open a fourth row; the acceptance check "
        "already written covers M3.5b's surfaces.",
        "DEFER",
    ),
    "X32": (
        "CONFIRMED. B02 keeps `cli.py` OUT and retains exactly `_command_supervisor.py` and "
        "`example_adapter.py`. D28's grounds are unchanged and now cite M3.6a and M3.7 as the "
        "scheduled edits rather than M3.5b.",
        "ENCODE",
    ),
    "X33": (
        "CONFIRMED. Gate 2 must demonstrate ONE INDEPENDENT RED CONTROL per obligation D01-D28. "
        "Inferring sensitivity from coverage is how a diff-blind battery ships assertions that "
        "cannot fail. This binds S3's construction, not a test body.",
        "GATE-SPEC",
    ),
    "X34": (
        "CONFIRMED. Gate 2's validator result and its red/green credential are SEPARATE artifacts "
        "from the battery's ordinary pass. A green suite proves the assertions run; only the red "
        "control proves they bind.",
        "GATE-SPEC",
    ),
    "X35": (
        "CONFIRMED. Gate 3's control line must bind the mutation verdict modules, the NAMED "
        "SURVIVOR SET and a green unmutated run together. A survivor count without names is not "
        "checkable at the next unit.",
        "GATE-SPEC",
    ),
    "X36": (
        "CONFIRMED. Gate 1 is the complete committed suite with zero failures, zero errors and zero "
        "skips — not a targeted green subset. MAIN's runs this session report 901 tests OK rc 0.",
        "GATE-SPEC",
    ),
    "X37": (
        "CONFIRMED, and it resolves V27. D23's 'every `cement <command>` invocation' is undefined "
        "against inline prose references, which legitimately omit required positionals and can "
        "never parse. The corpus is every invocation inside a fenced SHELL block. Gate 5 "
        "implements exactly that and rebuilds logical commands across backslash continuations AND "
        "across newlines held open by an unterminated quote, because the repo ships multi-line "
        "single-quoted JSON arguments.",
        "ENCODE-SCOPED",
    ),
    "X38": (
        "CONFIRMED. Placeholder production is decided by command semantics and line order inside "
        "each fence, which is what X30 already does. A naive fence regex spans fence boundaries "
        "and reports prose words such as `LLM`, `OCR` and `README` as placeholders.",
        "ENCODE",
    ),
    "X39": (
        "CONFIRMED. D15, D18 and D22 are compound and cannot be certified by one asserted clause "
        "plus an obligation citation. Each clause needs its own assertion and its own red control. "
        "D22 in particular has two directions — CLI-route prose that MUST change and library-route "
        "prose that MUST NOT — and a single-clause test can satisfy one while violating the other.",
        "GATE-SPEC",
    ),
    "X40": (
        "ACCEPTED. Section 9's zero-fork claim is FALSE. Five material forks existed and MAIN ruled "
        "every one this session: global abbreviation (DECLINED, X06), explicit capture help (TAKEN, "
        "V29), status-table scope (KEPT and re-scoped, X27), invocation extraction (fenced shell "
        "blocks, X37), and digest sufficiency (gap named, X26). A contract that claims no fork and "
        "carries five is a sizing defect as much as a claim defect: each fork cost a ruling the "
        "plan did not budget.",
        "ENCODE",
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
        print(f"unruled rows: {missing}\nunknown rulings: {extra}", file=sys.stderr)
        return 1

    stale = [
        row["id"]
        for row in rows
        if (row["main_verdict"], row["action"]) != RULINGS[row["id"]]
    ]
    if check:
        if stale:
            print(f"out of sync: {stale}", file=sys.stderr)
            return 1
        print(f"IN SYNC: {len(rows)} rows ruled")
        return 0

    for row in rows:
        row["main_verdict"], row["action"] = RULINGS[row["id"]]
    TABLE.write_text(json.dumps(payload, **DUMP) + "\n", encoding="utf-8")
    print(f"RULED: {len(rows)} rows, {len(stale)} changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
