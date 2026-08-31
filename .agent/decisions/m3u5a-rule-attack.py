#!/usr/bin/env python
"""Record MAIN's per-row ruling on the M3.5a attack table. Idempotent; `--check` is a gate.

    uv run python .agent/decisions/m3u5a-rule-attack.py [--check]

The reviewer owns `attack`, `evidence` and `severity`; MAIN owns `disposition` and `main_note`,
which the wave-2 validator EXEMPTS by design. An exempt column is ungraded, so a table can read
`UNKNOWN-CELLS: 0` while every ruling is still `None` — this script is what makes MAIN's half
re-derivable instead of hand-edited.

The id set is asserted against the table, so a row added later fails LOUDLY rather than going
unruled. Serialization is pinned by round-trip against the raw bytes before anything is written,
because a re-dump under the wrong `ensure_ascii`/indent rewrites the whole file as one diff.

Every ruling here is already binding in contract sections 14 and 15. This records it per row; it
decides nothing. `disposition` vocabulary:

    ACCEPTED-AMENDED    upheld; contract text superseded by the cited amendment
    ACCEPTED-FIXED      upheld; code or a gate changed
    BATTERY-CONSTRAINT  upheld as a constraint on how the battery must assert
    SCOPED              partly upheld; the claim is narrowed, not withdrawn
    DISCHARGED          already closed by an existing amendment or gate
    CLEARED             probe with no defensible alternative; kept as filed
    REJECTED            not a defect, with grounds
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).resolve().parent / "m3u5a-attack.json"

# id -> (disposition, main_note)
RULINGS: dict[str, tuple[str, str]] = {
    # --- blocking, all eleven ruled in section 14 -------------------------------------
    "A01": ("ACCEPTED-AMENDED", "A4 narrows D09's biconditional to `matched` alone over the values `System.resolve` computes. Same finding as verdict X02; two lenses, accepted without adjudication."),
    "A03": ("ACCEPTED-AMENDED", "A7 withdraws D13's unconditional `never worsens`: the inverse race turns a would-be success into exit 5. No code change; the sentence was the defect."),
    "A12": ("ACCEPTED-AMENDED", "A8 withdraws `strictly stronger`. D24/D25/D26 miss an old leaf's changed default; gate 4's `parser_shape` digest carries what B02 lost."),
    "Y01": ("ACCEPTED-FIXED", "Gate 4 stopped grading the fresh-ledger byte size, which is a host SQLite page-size property, and grades `bytes_positive` + `bytes_deterministic` instead."),
    "Y02": ("ACCEPTED-FIXED", "Gate 4 re-anchored: two pins carried S1 pre-implementation values that D25 and D16 move by design, so the gate was unsatisfiable as written."),
    "Y03": ("ACCEPTED-FIXED", "`m3u5a-s2-probe.py` printed its findings and returned 0 unconditionally. It now grades 19 pinned facts and exits 1 on any mismatch."),
    "Y04": ("ACCEPTED-AMENDED", "A2 scopes D05's precedence to library validations; CLI value-parsing necessarily precedes the call. Same finding as verdict X01."),
    "Y05": ("ACCEPTED-AMENDED", "A3 scopes D06 to invocations that REACH the ledger; a rejected invocation opens zero transactions. Same finding as verdict X06."),
    "Y06": ("ACCEPTED-AMENDED", "A1 restates D01/D14 as `no option prefix ever BINDS`; a prefix standing in place of the required option answers the required-argument message. Same finding as V02/V18."),
    "Y18": ("ACCEPTED-FIXED", "The argv disclosure claim was platform- and policy-unconditional. Scoped in `docs/threat-model.md` and `README.md`."),
    "Y21": ("ACCEPTED-FIXED", "The cap pair was cited to spike probes carrying it through the `@PATH` route the fork ruling REMOVED. Re-cited to `m3u5a-smoke.py`, which drives the shipped `main`."),
    # --- upheld as contract-text defects, section 15 --------------------------------
    "A04": ("ACCEPTED-AMENDED", "A9 states framing = 34 and derives it from `_SUBMISSION_KEYS`. D16 gave the total while naming no byte template, so a copied total satisfied the pin with nothing deriving it."),
    "A07": ("ACCEPTED-AMENDED", "A10 replaces `every successful submission is pending` with `every proposal is INSERTED pending`. Measured: a reviewer in the post-commit, pre-return window returns `rejected`. The key stays rejected on the corrected ground."),
    "A08": ("ACCEPTED-AMENDED", "A11 scopes the no-retry corpus to submission-owned prose and states it positively. A repository-wide grep fails both ways: legacy `handle` advises retry legitimately, and absence passes when the recovery prose is deleted."),
    "A10": ("ACCEPTED-FIXED", "A23 + gate 4. `parser_shape` digested ACTIONS, and `allow_abbrev` belongs to the PARSER, so the property D25 claims to preserve had no instrument. One `<node>` line per node: 126 -> 163 lines, digest `89dfa3d982d8c54b` -> `8b58b465c08aa693`; the control mutation moves it to `515b30796c61d189` while the census holds at 30/37."),
    "A11": ("ACCEPTED-AMENDED", "A12 names the oracle: git object `4783eed:src/cement_runtime/store.py`, blob `b870dacbaf2718b7cba3567b59d69a994ca4ca42`, 27,951 bytes. A self-comparison divorces the claim from its referent."),
    "A17": ("ACCEPTED-AMENDED", "A13 names D12's object and slicing convention — `main`'s whole-line AST span, 1,306 bytes, sha256 `973b7ee6...` — plus one planted exception per mapped class, because a span is not a behaviour."),
    "A20": ("ACCEPTED-AMENDED", "A21 copies `.agent/polish.md`'s observable into the section 12 deferral: one test per write leaf asserting NO file and a path-focused diagnosis. `one ruling applied uniformly` is a decision, not an acceptance check."),
    "Y08": ("ACCEPTED-FIXED", "A14 + `_absent_ledger` at `8f091fe`. THE ONLY CODE DEFECT THIS TABLE FOUND. `os.path.exists` follows the link, so a dangling symlink, a missing parent and an embedded NUL all fired D13's precheck at exit 5 where the same paths answer exit 2 elsewhere — and D12 freezes that map, so two obligations contradicted each other in shipped code."),
    "Y10": ("ACCEPTED-AMENDED", "A15 scopes D21 to the status-0 acknowledgement. Read across the leaf it is false: strict parsing quotes the offending token (`... rejects decimal/exponent number '12345.678901'`). No redaction boundary is added; the echo IS the diagnosis."),
    "Y15": ("ACCEPTED-AMENDED", "A16 labels the figures `System.resolve` METHOD latency. The harness constructs `System` before its timer, so startup, argparse, the precheck, schema init and JSON projection sit outside them — material at the 5.7 ms point."),
    "Y16": ("ACCEPTED-AMENDED", "A16 withdraws `costs what verify_function costs`. The two artifacts were measured at different commits, which the project's own per-point provenance rule makes non-evidentiary; cold ratios span 1.393 / 0.995 / 1.025."),
    "Y17": ("ACCEPTED-AMENDED", "A22 scopes G1's `under any invocation` to the measured host regime and records its provenance. The asymmetry-of-relief argument is unaffected: it holds on any host with a finite argv wall."),
    "Y19": ("ACCEPTED-AMENDED", "A18 scopes the byte wording to binary stdin. A text-only host has no `.buffer`, reads CHARACTERS, and has no invalid-UTF-8 family of its own because the parser's encoded-byte check stays authoritative."),
    "Y20": ("ACCEPTED-AMENDED", "A19 makes publication enumerate BOTH schemas. A reader who learns every output key and no input key cannot construct `--submission`."),
    "Y24": ("ACCEPTED-AMENDED", "A17 scopes the prefix rejection to the leaf's OWN options. Root options are parsed before the child is reached, so `--d`/`--part` keep resolving — which D25 requires. Unscoped, D01 and D25 demand opposite results for one invocation."),
    "Y25": ("ACCEPTED-AMENDED", "A20 replaces `admits every submission the library accepts` with the canonical-envelope guarantee. Insignificant whitespace is unbounded, so no transport bound can admit every serialization."),
    # --- battery-design constraints, section 15 -------------------------------------
    "A02": ("BATTERY-CONSTRAINT", "D07's test asserts set EQUALITY to the literal seven keys INDEPENDENTLY in each of the three states. Measured: subset plus cross-state identity accepts `{}` everywhere."),
    "A09": ("BATTERY-CONSTRAINT", "D24's test injects a CONFIGURED source whose every attribute access raises, then requires success plus one write. Two named-method spies miss direct `candidate_source` reach, and a `None` source makes all three counters vacuous."),
    "A13": ("BATTERY-CONSTRAINT", "D30's test LOADS `m3u2b-resolve-bench.json` and formats each published token at runtime. A hard-coded assertion passes today and stays green after remeasurement."),
    "A18": ("BATTERY-CONSTRAINT", "D28's grep is necessary and not sufficient. The test asserts every grammar token, envelope key, payload key, exit class and invariant inside an anchored human-visible section, so two bare command-name lines cannot satisfy it."),
    "A19": ("BATTERY-CONSTRAINT", "D29's placeholder grammar = shell variables alone, each needing an earlier assignment or command substitution in the same fence. Uppercase detection misses `hash_from_verify`; treating every symbolic argument as a placeholder makes operator-supplied JSON unproducible."),
    "Y11": ("BATTERY-CONSTRAINT", "The census test asserts the NAME sets gate 4 already grades — `lost_baseline_leaves` empty and `added_leaves` exactly `{proposal submit, resolve}` — and derives 30/37 from them. Deriving current counts is not deriving the oracle."),
    "Y14": ("BATTERY-CONSTRAINT", "A compound obligation carries one `subTest` per clause; D26 and D28 each hold five. One filled body otherwise covers one clause and marks the whole obligation covered. The mutation sweep is the complementary instrument, since each clause carries its own mutant."),
    "Y29": ("BATTERY-CONSTRAINT", "D06's acceptance surrounds full `_run` dispatch INCLUDING `System` construction — hash the database and journal around it — with the method-level transaction, clock, event and ID spies retained. A3 supplies the scoping."),
    # --- scoped ----------------------------------------------------------------------
    "A16": ("SCOPED", "Upheld: no obligation compares old-leaf behaviour to base `4783eed`. Section 1's `preservation` narrows to what is instrumented — gate 4's `parser_shape` digest over the whole CLI grammar surface plus D26's enumerated invariants. Behaviour outside the parser surface has the full suite alone, which is not a preservation oracle."),
    "Y07": ("SCOPED", "G3's strict-duplicate ground narrows to duplicate JSON object MEMBERS. Repeated `--submission` is argparse last-wins, uniformly across all 30 leaves, so hardening two leaves against repetition would be the asymmetry — the same ruling section 14 made for Y28."),
    "Y12": ("SCOPED", "Upheld and already satisfied in gate 3's shipped form: a survivor ruling must PRE-DATE the decisive sweep, and `M41`'s equivalence proof is committed at `75f0678` before dispatch. The harness compares observed survivors against the catalogue's declared `expect: equivalent` set, so a post-hoc member fails."),
    "Y13": ("SCOPED", "Partly closed: the catalogue is contract-owned with all 50 sites named and mapped to obligations, and the harness prints every id. The residual — a generator deriving the catalogue from AST branches rather than from a written list — is NOT built and is recorded rather than claimed."),
    # --- discharged, cleared, rejected -----------------------------------------------
    "Y09": ("DISCHARGED", "A5 already states that `System(...)` runs before envelope validation and that `_initialize` transacts, so a `Store.transaction` spy passing is expected rather than evasive."),
    "Y22": ("DISCHARGED", "Gate 4 replaced substring counting with an AST literal census plus an imported-symbol check: `literal_sites` 1, `reference_sites` 4."),
    "Y23": ("DISCHARGED", "Gate 4's docstring probe count now agrees with the contract."),
    "Y26": ("DISCHARGED", "Gate 2 counts `SKIPPED` over both `self.skipTest` and the decorator list, and `ASSERTIONLESS` over filled bodies that assert nothing."),
    "Y27": ("DISCHARGED", "Gate 3 runs the UNMUTATED control first, prints `CONTROL: GREEN`, and ABORTS without writing verdicts when it is red."),
    "Y30": ("DISCHARGED", "A8 supersedes D27's rationale, so the self-contradiction the row names is gone with the sentence."),
    "A05": ("CLEARED", "No defensible alternative. `parse_json` installs `object_pairs_hook`, so any duplicate raises before a dict reaches the type or key checks. Kept as filed."),
    "A06": ("CLEARED", "No defensible alternative. The pin reads the COMMITTED row, so an omitted provenance must round-trip as `{}` and stay `{}` after the caller mutates its original mapping — forcing detachment and durability together."),
    "A14": ("CLEARED", "No defensible alternative. The seams are disjoint: `_Unverified` emits stderr at 6 while an `_Outcome` emits its payload on stdout with its own status, and existing export regressions force the old channel."),
    "A15": ("CLEARED", "No defensible alternative. Wrap the real instance's `store.transaction` preserving the context manager and assert `call_args_list == [call(write=False)]`; a bare mock observes no nested work."),
    "Y28": ("REJECTED", "Not a defect. Repeated options are argparse last-wins uniformly across all 30 leaves — measured, `--input 1 --input 2` resolves against `2` — and D01/D14 fix the option SET rather than repetition arity, so making two leaves differ would be the asymmetry."),
}


def _serialization(raw: str, data: object) -> dict[str, object]:
    """Pin the dump options by ROUND-TRIP against the raw bytes, never by assumption."""

    for indent in (2, 4, None):
        for ensure_ascii in (True, False):
            for sort_keys in (False, True):
                options = {
                    "indent": indent,
                    "ensure_ascii": ensure_ascii,
                    "sort_keys": sort_keys,
                }
                if json.dumps(data, **options) + "\n" == raw:  # type: ignore[arg-type]
                    return options
                if json.dumps(data, **options) == raw:  # type: ignore[arg-type]
                    return {**options, "_trailing_newline": False}
    raise SystemExit("ABORT   no candidate serialization round-trips the raw bytes")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv[1:])

    raw = TABLE.read_text(encoding="utf-8")
    data = json.loads(raw)
    rows = data["rows"]

    table_ids = {row["id"] for row in rows}
    ruled_ids = set(RULINGS)
    if table_ids != ruled_ids:
        print(f"UNRULED: {sorted(table_ids - ruled_ids)}")
        print(f"ORPHAN-RULINGS: {sorted(ruled_ids - table_ids)}")
        print("FAIL")
        return 1

    options = _serialization(raw, data)
    trailing = options.pop("_trailing_newline", True)

    changed = 0
    for row in rows:
        disposition, note = RULINGS[row["id"]]
        if row.get("disposition") != disposition or row.get("main_note") != note:
            changed += 1
        row["disposition"] = disposition
        row["main_note"] = note

    print(f"ROWS: {len(rows)}")
    print(f"RULED: {len(ruled_ids)}")
    print(f"UNRULED: 0 []")
    print(f"OUT-OF-SYNC: {changed}")
    if args.check:
        print("PASS" if changed == 0 else "FAIL")
        return 0 if changed == 0 else 1
    if changed:
        text = json.dumps(data, **options)  # type: ignore[arg-type]
        TABLE.write_text(text + ("\n" if trailing else ""), encoding="utf-8")
        print("WROTE")
    else:
        print("NO-OP")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
