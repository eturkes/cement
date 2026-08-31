#!/usr/bin/env python3
"""Fill the MAIN-owned `main_verdict` and `action` columns of m3u5a-verdicts.json.

    uv run python .agent/decisions/m3u5a-rule-verdicts.py [--check]

Idempotent, replayable from the teammate's committed table (wt/test-m3u5a-1 @ f87c8a2,
60 rows). `--check` exits 1 when the table is out of sync, so a later row addition fails
loudly instead of going unruled.

Every ruling is judged against the SHIPPED code at e6ba873 and the contract's section 13.

Verdict prefixes:
  CONFIRMED  the row's expected outcome is the ruled one; the battery encodes it as written
  SCOPED     the row overreaches; the ruling narrows its domain before the battery sees it
  CORRECTED  the row is WRONG against shipped code or a section 13 amendment
  ACCEPTED   the row found a real gap outside the shipped code

`action` is the battery instruction: ENCODE (pin as ruled), ENCODE-SCOPED (pin the narrowed
form), PROBE (record, never red), or DEFER (polish register).

Measurements this ruling rests on, all re-derived by MAIN from the primary tree:
  store.py 27,951 B sha256 2b2650144d4b384af4d8bfe67e1f9de0e186b609f3bb2632e2f81b53536770f7
  SCHEMA_VERSION 2; 13 CREATE TABLE names in store.SCHEMA
  PROVENANCE_MAX_BYTES 65536; DEFAULT_MAX_DEPTH 64; DEFAULT_MAX_ITEMS 100000
  envelope parses at max_depth 65, max_items 300003; SUBMISSION_MAX_BYTES 2162722
  cli.py holds one residual `65_536` at line 370 bounding --source-command (not provenance)
  main's except ladder: _UsageError 2, NotFoundError 3, (ConflictError, StateError) 4,
    IntegrityError 5, (ValidationError, CementError) 2, _Unverified 6
  invalid envelope: System.__init__ 1, sqlite3.connect >=1, Store.transaction 0,
    System.submit_proposal 0, ledger present ~208 KiB
  `resolve op --in 1` -> `the following arguments are required: --input`
  `resolve op --input 1 --in 1` -> `unrecognized arguments: --in 1`
  `resolve op --input '{bad' --expected-function-hash bad` -> `invalid JSON: ...`
  `resolve op --input 1 --expected-function-hash bad` -> library digest message
  absent ledger + `!` partition -> exit 5 `ledger file is missing or unreadable`, no file
  existing ledger + `!` partition -> exit 2 partition-shape message
  publication cells (`cement resolve`, `cement proposal submit`): README (1,1),
    architecture (1,1), threat-model (1,2), adapter-protocol (0,0)
"""

from __future__ import annotations

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).with_name("m3u5a-verdicts.json")
DUMP = dict(indent=2, ensure_ascii=False, sort_keys=False)

# id -> (main_verdict, action)
RULINGS: dict[str, tuple[str, str]] = {
    # ---- D01-D06, the resolve leaf ----------------------------------------
    "V01": (
        "CONFIRMED. Shipped grammar is exactly that: one positional `operation`, required "
        "`--input`, optional `--expected-function-hash` defaulting to None, `allow_abbrev=False`. "
        "Deriving the destination set from the node rather than transcribing it is what makes a "
        "fourth argument fail the test instead of passing unnoticed.",
        "ENCODE",
    ),
    "V02": (
        "CONFIRMED, and the probe's construction is why it survives amendment A1. It supplies a "
        "full `--input 0` alongside each prefix, which is exactly the condition under which "
        "argparse reaches its leftover check. Measured: `--in 1` and `--exp x` both yield "
        "`unrecognized arguments: <prefix> <value>` at exit 2 with empty stdout. A prefix-ALONE "
        "probe would instead report the missing required option; see A1 and the V18 ruling.",
        "ENCODE",
    ),
    "V03": (
        "CONFIRMED. `--input` is the shipped `_input` verbatim; resolve adds no reader, so the "
        "1,048,576-byte bound and its message are inherited rather than restated. The adjacent "
        "accept/reject pair is the whole obligation - a constant-only pin would pass against a "
        "bound the code never applies.",
        "ENCODE",
    ),
    "V04": (
        "CONFIRMED. The invalid-JSON family answers, `System.resolve` is never called, and the "
        "message carries the parser's own position text. Pinning the full sentence including "
        "`line 1 column 2 (char 1)` is deliberate: it proves the CLI forwards the parser verdict "
        "rather than substituting a summary.",
        "ENCODE",
    ),
    "V05": (
        "CONFIRMED. This is D24's headline isolation predicate on the resolve side. A configured "
        "source must be present for the zero to mean anything, which the probe does, and the "
        "counter set covers the builder, the library route and the source object separately.",
        "ENCODE",
    ),
    "V06": (
        "CONFIRMED. Both gates keep their shipped order and exact text, and both precede `_input` "
        "and `System`. Asserting zero `_input` calls is what distinguishes a gate that runs first "
        "from a gate that merely runs.",
        "ENCODE",
    ),
    "V07": (
        "CONFIRMED and it separates the two halves of D05 correctly. A malformed digest is a "
        "library ValidationError at exit 2; a well-formed digest that does not match the promoted "
        "set is a negative VERDICT at exit 6 with the full payload on stdout. The CLI grades "
        "neither - it forwards the value verbatim.",
        "ENCODE",
    ),
    "V08": (
        "CONFIRMED. Four independent instruments - ledger digest, ledger dump, event delta and "
        "`_new_id` call count - over all three resolve states. The dump matters beyond the digest "
        "because a write that restores the previous bytes would defeat a hash alone.",
        "ENCODE",
    ),
    "V09": (
        "CONFIRMED. `_emit` sorts keys, so the closed set and the emitted order are one assertion. "
        "Requiring the SAME set in all three states is the structural half of D11: a payload that "
        "grows a key on a failed verdict would leak the verification shape.",
        "ENCODE",
    ),
    "V10": (
        "CONFIRMED. `checks` is `[asdict(check) for check in verification.checks]`, so the vector "
        "is the library's own ordering. Pinning first and last key names plus the exact triple "
        "field set pins the projection without freezing the six check names as CLI vocabulary.",
        "ENCODE",
    ),
    "V11": (
        "CONFIRMED. This is the property a shared exit 6 exists to preserve. Both objects carry "
        "the same seven keys, so `matched` alone separates a verified absence from a failed "
        "verdict, and asserting the two payloads are unequal blocks a regression that collapses "
        "them.",
        "ENCODE",
    ),
    "V12": (
        "CONFIRMED, and it forced amendment A4. The row is right that D09's locus sentence "
        "overstates: null-ness of `output` and `artifact_hash` tracks `match is None`, while "
        "`matched` is null only on a failed verdict. Measured triples of "
        "`(matched is None, output is None, artifact_hash is None)` are hit (F,F,F), miss (F,T,T), "
        "failed (T,T,T). A4 rules D09's biconditional to bind `matched` ALONE; the other two are "
        "null whenever no artifact is projected, which includes the verified miss.",
        "ENCODE",
    ),
    "V13": (
        "CONFIRMED. `status=0 if matched is True else 6` is shipped, and the `is True` identity "
        "test is load-bearing: `matched` is a tri-state, so a truthiness test would map null to 6 "
        "by accident rather than by rule. Both negative states use stdout, never `function "
        "export`'s exceptional stderr channel.",
        "ENCODE",
    ),
    "V14": (
        "CONFIRMED. The planted document-only string is what raises this above D07's structural "
        "pin: a closed key set proves no NEW key appeared, while the planted string proves no "
        "document byte reached an EXISTING key.",
        "ENCODE",
    ),
    "V15": (
        "CONFIRMED, and the empty-set case is the discriminating one. An empty promoted set "
        "verifies successfully and reports a verified absence at exit 6, not an error - "
        "`build_function` yields an empty document rather than None, so `matched` is false and "
        "never null. A retired-artifact revision reads identically.",
        "ENCODE",
    ),
    "V16": (
        "CONFIRMED. Exit 5, the exact two-key stderr object, and path absence BEFORE and AFTER. "
        "The after-check is the obligation: D13 exists because `Store` construction would "
        "otherwise create the file that resolve was asked to read.",
        "ENCODE",
    ),
    "V17": (
        "CONFIRMED. Placing the precheck between the `--partition` gate and `System(...)` is what "
        "makes D04's ordering safe: with the ledger absent nothing is constructed, so a malformed "
        "`--input` rejected later can only ever touch a ledger that already existed. Zero `_input` "
        "calls is the ordering evidence.",
        "ENCODE",
    ),
    # ---- D14-D19, the proposal submit leaf --------------------------------
    "V18": (
        "CONFIRMED as revised. The revision is correct and follows A1: `--sub` yields "
        "`unrecognized arguments` only when a full `--submission` is also supplied; `--sub` alone "
        "reports `the following arguments are required: --submission`. `proposal sub` yields "
        "`argument proposal_command: invalid choice: 'sub' (choose from 'submit', 'show', 'list', "
        "'review')`. Both are exit 2 with empty stdout.",
        "ENCODE",
    ),
    "V19": (
        "CONFIRMED. The three shipped sentences are exactly `submission stdin could not be read`, "
        "`submission stdin exceeds 2162722 bytes` and `submission stdin is not valid UTF-8`. One "
        "warning for the battery: the TEXT-stream path says `exceeds 2162722 characters`, so a "
        "probe that patches a text `sys.stdin` must expect the characters wording. Mirroring "
        "`_input`'s three families with submission-specific nouns is the whole of D15.",
        "ENCODE",
    ),
    "V20": (
        "CONFIRMED. The adjacent accept/reject pair at 2,162,722 and 2,162,723 is what proves the "
        "cap is APPLIED; X11 separately proves it is DERIVED. Neither claim implies the other.",
        "ENCODE",
    ),
    "V21": (
        "CONFIRMED. `parse_json` is strict, so `{\"input\":1,\"input\":2}` fails inside the parser "
        "with `duplicate JSON object key: 'input'` before the exact-key check runs. That ordering "
        "is D17's reason for existing: a permissive parser would silently keep one of two values "
        "and the key check would see a well-formed envelope.",
        "ENCODE",
    ),
    "V22": (
        "CONFIRMED as revised. The shipped sentences are `submission has unknown keys: a, z` and "
        "`submission is missing required keys: input, output` - the word `required` is present, "
        "and the pre-revision expectation would have gone red against correct code. Both lists are "
        "sorted and exhaustive, and `System.submit_proposal` is never called.",
        "ENCODE",
    ),
    "V23": (
        "CONFIRMED. Provenance shape stays library-graded: `candidate provenance must be a "
        "mapping` comes from `Candidate`, not the CLI, and the CLI adds no coercion. Zero request, "
        "proposal and event deltas prove the rejection precedes the write.",
        "ENCODE",
    ),
    "V24": (
        "CONFIRMED. Exactly one key. The bare string `submit_proposal` returns is not emitted "
        "directly because `_emit` would render it as a keyless JSON string, and the flags patch's "
        "`\"status\": \"review_required\"` stays REJECTED: every successful submission is pending "
        "by construction, so that key would advertise a variability the API does not have.",
        "ENCODE",
    ),
    "V25": (
        "CONFIRMED. Exit 3 with zero rows across all 13 application tables. Sweeping every table "
        "rather than the expected three is what turns this from a spot check into a footprint "
        "claim.",
        "ENCODE",
    ),
    "V26": (
        "CONFIRMED. This is D23 stated as an observable rather than a warning: two byte-identical "
        "submissions, two distinct ids, exactly two of each of the three rows and zero elsewhere. "
        "There is no idempotency and the battery says so in deltas.",
        "ENCODE",
    ),
    "V27": (
        "CONFIRMED, re-derived by MAIN from `_parser()` at e6ba873: 30 leaves, 37 nodes, and the "
        "set difference against the 28-path baseline is exactly {'resolve', 'proposal submit'}. "
        "The census MOVING is the obligation landing, not a regression; deriving it inside the "
        "test rather than transcribing it is why the number can be trusted.",
        "ENCODE",
    ),
    "V28": (
        "CONFIRMED. Isolation in both directions is the point: `--submission` must not appear on "
        "any other leaf and `--expected-function-hash` must stay off `proposal submit`. The count "
        "of 4 for the expected-hash option covers its pre-existing homes plus resolve, so the "
        "battery derives it from the census rather than asserting a bare 1.",
        "ENCODE",
    ),
    # ---- extension rows ----------------------------------------------------
    "X01": (
        "CONFIRMED, and it forced amendment A2. Measured: `--input '{bad' "
        "--expected-function-hash bad` exits 2 with `invalid JSON: ...`, while `--input 1 "
        "--expected-function-hash bad` exits 2 with `expected_function_hash must be a SHA-256 hex "
        "digest`. A2 narrows D05 to the truth: the library owns precedence AMONG library "
        "validations, and CLI value-parsing necessarily precedes all of them because a value must "
        "exist before `System.resolve` can be called. Duplicating `_digest` in the CLI to restore "
        "the literal edge is REJECTED - it would put a second copy of a library validator on the "
        "surface D05 exists to keep thin.",
        "ENCODE-SCOPED",
    ),
    "X02": (
        "SCOPED, and it forced the second half of amendment A4. The row is factually right: "
        "system.py:3835 returns `match=None` whenever `not verification.passed or document is "
        "None`, so a passing verification with no document yields payload `(passed:true, "
        "matched:null)`, which D09's literal biconditional forbids. A4 narrows D09's domain to "
        "values `System.resolve` computes THROUGH the shipped `verify_function`; the row's own "
        "route to the forbidden pair is an override of `verify_function`, which is not such a "
        "value. Normalizing it in the CLI is REJECTED on merits: mapping the pair to "
        "`matched:false` would launder an internal inconsistency into an ordinary miss, and "
        "`matched:null` at `passed:true` is precisely the signal that should stay visible. Encode "
        "the three reachable states as red; record the override behaviour as a probe.",
        "ENCODE-SCOPED",
    ),
    "X03": (
        "CONFIRMED. `_input`'s two non-size families survive on the resolve path unchanged, which "
        "is D02's whole claim - resolve adds no reader, so it can add no failure family either.",
        "ENCODE",
    ),
    "X04": (
        "CONFIRMED. Exactly one `System.resolve` call and zero on every neighbouring route. "
        "`verify_function` is in the counter set for a good reason: resolve calls it INTERNALLY, "
        "so a zero there proves the CLI reaches the library once at the composed entry point "
        "rather than assembling the operation itself.",
        "ENCODE",
    ),
    "X05": (
        "CONFIRMED, and the two obligations do not actually conflict. Measured: absent ledger with "
        "partition `!` exits 5 with `ledger file is missing or unreadable` and creates no file; "
        "EXISTING ledger with partition `!` exits 2 with `partition must be 1-128 ASCII letters, "
        "digits, '.', '_', ':', '/', or '-'`. D13's precheck is upstream of construction and D05's "
        "shape check is downstream of it, so the first observable differs by ledger existence and "
        "neither reading needs `_name` duplicated in the CLI. Encode BOTH cells; the pair is the "
        "ruling.",
        "ENCODE",
    ),
    "X06": (
        "SCOPED, and it forced amendment A3. D06's `one transaction per invocation` was written "
        "without a reaching-ledger qualifier and is false for rejected invocations. A3 scopes it "
        "to invocations that reach the ledger. The ruled observable is the row's own "
        "`{valid:1, invalid:0}`, which is strictly more informative than the literal reading it "
        "replaces.",
        "ENCODE-SCOPED",
    ),
    "X07": (
        "CONFIRMED. `function_hash` surviving a failed verdict as a diagnostic is the D08 clause "
        "most likely to be optimized away, because it is the one field a naive implementation "
        "would null out alongside the match. Comparing it to the direct verification's own digest "
        "is the right instrument.",
        "ENCODE",
    ),
    "X08": (
        "CONFIRMED, re-derived from `main`'s except ladder: `_UsageError` 2, `NotFoundError` 3, "
        "`(ConflictError, StateError)` 4, `IntegrityError` 5, `(ValidationError, CementError)` 2, "
        "`_Unverified` 6. The map is correct BECAUSE of ladder order - the specific subclasses are "
        "caught ahead of the `CementError` base - so the battery must exercise real raises rather "
        "than reading a dict, which is what this row does.",
        "ENCODE",
    ),
    "X09": (
        "CONFIRMED. Section 3.2 ruled D-A out, so an at-sign submission must be ordinary inline "
        "JSON that fails as invalid JSON. Zero `Path.open` calls plus an untouched named path is "
        "the evidence that no filesystem route was silently reintroduced; a message-only assertion "
        "would pass against a CLI that stats the path first.",
        "ENCODE",
    ),
    "X10": (
        "CONFIRMED, and it pins the defect that killed the per-field alternative. A second `-` read "
        "finds a drained stream, so any design needing two stdin reads truncates one field "
        "silently. Asserting exactly one read requesting at most `cap + 1` bytes proves both the "
        "single-read property and the bounded-read property in one instrument.",
        "ENCODE",
    ),
    "X11": (
        "CONFIRMED as revised, and the revision is one MAIN supplied after measuring. `cli.py` "
        "retains exactly one `65_536` literal, at line 370, bounding `--source-command`; it is "
        "unrelated to provenance and shares the value by coincidence. The pre-revision `0 numeric "
        "65536 literals` claim would have gone red against correct code. The ruled obligation is "
        "that the SUBMISSION path copies no limit: `SUBMISSION_MAX_BYTES` is "
        "`2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + _SUBMISSION_FRAMING`, framing is computed "
        "from `_SUBMISSION_KEYS` at 34, and all three system.py provenance sites reference the "
        "exported constant. Retiring the coincidental literal is DEFERRED to polish.",
        "ENCODE-SCOPED",
    ),
    "X12": (
        "CONFIRMED. The shipped sentence is `submission must be a JSON object` for every non-object "
        "top level, verified by MAIN against `[]`. D17 quoted no wording, so this ruling supplies "
        "it; `type(parsed) is not dict` is the shipped test, which correctly rejects a list, a "
        "scalar and null alike.",
        "ENCODE",
    ),
    "X13": (
        "CONFIRMED, re-derived from the shipped call: `max_depth=DEFAULT_MAX_DEPTH + 1` = 65 and "
        "`max_items=3 * DEFAULT_MAX_ITEMS + 3` = 300003, against library constants 64 and 100000. "
        "The envelope nests each field one level deeper and adds three members, so those are the "
        "only values that let a submission the library accepts survive the transport. The adjacent "
        "reject at 66 and 300004 is what proves the derived maxima are applied rather than merely "
        "named.",
        "ENCODE",
    ),
    "X14": (
        "CONFIRMED. Unknown precedes missing in the shipped order, and asserting the message "
        "contains NEITHER required key name is the discriminating half - a validator that reported "
        "both violations together would pass a weaker containment test.",
        "ENCODE",
    ),
    "X15": (
        "CONFIRMED. Distinct object identity is the load-bearing clause: a module-level `{}` "
        "default shared across calls would satisfy an equality-only test and still let one "
        "submission mutate another's provenance. The 2-byte stored `{}` proves the default is "
        "durable rather than merely present in memory.",
        "ENCODE",
    ),
    "X16": (
        "CONFIRMED as revised, and the revision is the honest boundary that forced amendment A5. "
        "Measured on all four envelope failures: `System.__init__` 1, `sqlite3.connect` >= 1, "
        "`Store.transaction` 0, `System.submit_proposal` 0, ledger present afterwards at ~208 KiB. "
        "D18's `before any transaction opens` is therefore TRUE as written at the "
        "`Store.transaction` seam and is retained; A5 adds the clause D18 was missing - "
        "construction precedes envelope validation, so a writing leaf creates its ledger before "
        "rejecting a malformed envelope. Giving submit a D13-style precheck is REJECTED: creating "
        "the ledger is a legitimate first use of a writing leaf. The residual - an invalid "
        "argument value creating the ledger on any writing leaf - is CLI-wide and pre-existing, "
        "and is DEFERRED to polish.",
        "ENCODE-SCOPED",
    ),
    "X17": (
        "CONFIRMED. This is D19 as a wiring assertion: the envelope's `input` is the library's "
        "third POSITIONAL while `output` and `provenance` travel inside `Candidate`. Checking "
        "positional args and candidate fields separately is what would catch a transposition that "
        "a round-trip test would not.",
        "ENCODE",
    ),
    "X18": (
        "CONFIRMED. The acknowledgement carries no request identity and `proposal.created` keeps "
        "payload `{}` on this route. Counting occurrences of the input, output and provenance "
        "bytes across BOTH surfaces is the disclosure claim; one key on stdout alone would not "
        "cover the event.",
        "ENCODE",
    ),
    "X19": (
        "CONFIRMED. Six classes, each with empty stdout and exactly one JSON stderr object. The "
        "empty-stdout half matters as much as the status: a leaf that printed a partial payload "
        "before failing would still exit correctly. Encoding note: one object is NOT one line. "
        "cli.py emits every envelope as `json.dumps(value, ensure_ascii=False, sort_keys=True, "
        "indent=2) + \"\\n\"`, unchanged since c8b82cd, so the stderr of a single-object failure "
        "holds 4 newlines. Assert the exact round-trip of that framing, never a newline count.",
        "ENCODE",
    ),
    "X20": (
        "CONFIRMED with one scoping the battery must honour. The retry prohibition is D23's and it "
        "covers sentences about `resolve` and `proposal submit`; README's request-outcomes table "
        "legitimately advises `retry handle with --retry-failed` for the HANDLE route, so a "
        "document-wide `retry` count would go red against correct prose. Shipped text carries "
        "`Cement gives no idempotency here`, `Do not retry a failed submission` and a "
        "`proposal list --status pending` recovery block.",
        "ENCODE-SCOPED",
    ),
    "X21": (
        "CONFIRMED. Static and dynamic evidence for one claim: the new nodes carry no source "
        "OPTION, and the new dispatches make no source CALL. Either alone is defeatable - an "
        "option-free node could still reach a configured source, and a zero call count could "
        "reflect an unconfigured source - so D24 needs both.",
        "ENCODE",
    ),
    "X22": (
        "CONFIRMED. Identity, not cardinality, is the obligation: two set subtractions in both "
        "directions catch a rename that leaves the count at 30. This is the assertion V27's count "
        "cannot make.",
        "ENCODE",
    ),
    "X23": (
        "CONFIRMED. The new nodes set `allow_abbrev=False` and no other node changed, so legacy "
        "abbreviation must still work while the new leaves reject it. Verified by MAIN that all "
        "four new-node prefix probes exit 2. Asserting only the new-node failures would let a "
        "global `allow_abbrev=False` regression pass.",
        "ENCODE",
    ),
    "X24": (
        "CONFIRMED, re-derived by MAIN from the primary tree: `store.py` is 27,951 bytes, sha256 "
        "2b2650144d4b384af4d8bfe67e1f9de0e186b609f3bb2632e2f81b53536770f7, `SCHEMA_VERSION` 2. "
        "Byte comparison plus length plus digest is deliberately redundant, because each one alone "
        "has a failure mode the others do not.",
        "ENCODE",
    ),
    "X25": (
        "CONFIRMED, and the complete-map form is what makes it a footprint claim. 13 application "
        "tables derived from `store.SCHEMA`; the nonzero delta map is exactly "
        "`{requests:1, proposals:1, events:1}`. Deriving the table list rather than transcribing "
        "it means a future table joins the sweep automatically.",
        "ENCODE",
    ),
    "X26": (
        "CONFIRMED. `cli.py` holds three `CommandCandidateSource` references: the import and its "
        "uses inside `_source`. The seam must survive intact - D24 forbids the new leaves from "
        "REACHING a source, never the CLI from offering one to the routes that always had it.",
        "ENCODE",
    ),
    "X27": (
        "CONFIRMED. `test_b02_cli_py_command_supervisor_py_and` in tests/test_submission_battery.py "
        "retires the `cli.py` member and keeps the other two frozen against git object f9b9755, "
        "with a docstring naming D24, D25 and D26. This is D27's substance: the property the pin "
        "carried for `cli.py` - M3.3 added no CLI channel and no CLI source reach - MIGRATED to "
        "three live obligations rather than being dropped. A byte pin over a file the unit is "
        "chartered to extend can only be retired, and retiring it silently is the failure D27 "
        "exists to prevent.",
        "ENCODE",
    ),
    "X28": (
        "CONFIRMED, verified against shipped prose. README ships both grammars in runnable blocks, "
        "the seven-key payload table, `proposal_id` at status 0, every exit class, `Cement gives "
        "no idempotency here` and the write-freedom sentence. Three spellings the battery must "
        "honour, each measured against the shipped bytes. First, the runnable blocks spell the "
        "invocation `uv run cement ... resolve` while prose says `cement resolve`, so a token "
        "search must accept both. Second, the exit classes ship as PROSE, not as table cells: "
        "`Exit 6 is the negative-verdict class`, then `Exit 2 covers usage and validation. Exit 3 "
        "means an absent object, exit 4 a state conflict, and exit 5 an integrity failure.`, with "
        "exit 0 named where root `verify` reports a failed verification. A markdown numeric-cell "
        "regex over the publication set matches ZERO rows, so scan `exit N`/`status N` tokens and "
        "require {0,2,3,4,5,6} while 1 stays absent. Third, README:186 ships the write-freedom "
        "sentence as ``resolve` writes nothing.` with the identifier backticked, seconded by "
        "`The leaf writes nothing` at architecture.md:78; an unbackticked literal search for "
        "`resolve writes nothing` matches nothing. Quote shipped prose byte-exact in a ruling or "
        "name the token search that must match it.",
        "ENCODE",
    ),
    "X29": (
        "CONFIRMED as a real ambiguity, resolved by amendment A6 in favour of the UNION. Measured "
        "cells for (`cement resolve`, `cement proposal submit`): README (1,1), architecture (1,1), "
        "threat-model (1,2), adapter-protocol (0,0). A6 rules the union over README, "
        "docs/architecture.md and docs/threat-model.md, with README additionally required to carry "
        "both; docs/adapter-protocol.md is OUTSIDE the union because it documents the adapter "
        "protocol and names no CLI leaf. The per-file reading is rejected on merits: it would force "
        "redundant grammar transcription into documents whose job is not teaching invocation, and "
        "duplicated grammar is exactly what goes stale.",
        "ENCODE-SCOPED",
    ),
    "X30": (
        "CONFIRMED. The single placeholder in the new blocks is `HASH_FROM_VERIFY`, and its "
        "producer `function verify support.reply` is the FIRST line of the same block, with the "
        "prose above naming it. Two derivation warnings MAIN measured the hard way: a naive fence "
        "regex spans fence boundaries and reports prose words such as `LLM`, `OCR` and `README` as "
        "placeholders, and placeholders inside inline code in prose - `request REQUEST_ID`, "
        "`events --after SEQUENCE` - are outside D29's scope. The battery must walk fences line by "
        "line and consider shipped command blocks only.",
        "ENCODE",
    ),
    "X31": (
        "CONFIRMED. All four figures derive from `m3u2b-resolve-bench.json` at the precision each "
        "entry count states: 5.7 ms at one entry, 613 ms at 1,000, 36,452 ms and 985,696 KiB at "
        "50,000, matching the method docstring's ~36.5 s and ~963 MiB. Deriving rather than "
        "transcribing is D30's mechanism - a re-measurement then moves prose and artifact together "
        "or fails loudly.",
        "ENCODE",
    ),
    "X32": (
        "CONFIRMED with the shipped sentence named. `fast` and `cheap` are absent; the two `cached` "
        "occurrences both describe WITHHOLDING cached output on the reconciliation path and are not "
        "affirmative claims about resolve. The positive half is shipped as `Cement caches no "
        "verification between calls.` in README alongside `One resolve runs the full six-check "
        "verification, so it costs what function verify costs.` The battery must match those "
        "meaning-bearing tokens, NOT the literal string `caches nothing`, which appears only in the "
        "method docstring. This row is D27's rule applied to cost: `resolve writes nothing` invites "
        "a cheapness inference that only the caching sentence closes.",
        "ENCODE",
    ),
}


def main(argv: list[str]) -> int:
    check = argv[1:] == ["--check"]
    if argv[1:] and not check:
        print(__doc__)
        return 2

    raw = TABLE.read_bytes()
    payload = json.loads(raw)
    # Serialization pin: prove the round-trip BEFORE patching, so a rewrite never reformats
    # the teammate's committed bytes as a side effect.
    if (json.dumps(payload, **DUMP) + "\n").encode() != raw:
        print(f"ABORT   {TABLE.name}: serialization does not round-trip; re-measure DUMP")
        return 1

    rows = payload["rows"]
    ids = [row["id"] for row in rows]
    if set(ids) != set(RULINGS):
        missing = sorted(set(ids) - set(RULINGS))
        extra = sorted(set(RULINGS) - set(ids))
        print(f"ABORT   id set differs. Unruled rows: {missing}. Ruling has no row: {extra}")
        return 1

    stale = [
        row["id"]
        for row in rows
        if (row["main_verdict"], row["action"]) != RULINGS[row["id"]]
    ]
    if check:
        print(
            f"CHECK   {len(stale)} of {len(rows)} rows out of sync"
            if stale
            else f"CHECK   in sync, {len(rows)} rows ruled"
        )
        return 1 if stale else 0

    for row in rows:
        row["main_verdict"], row["action"] = RULINGS[row["id"]]
    TABLE.write_text(json.dumps(payload, **DUMP) + "\n", encoding="utf-8")
    print(f"RULED   {len(stale)} of {len(rows)} rows updated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
