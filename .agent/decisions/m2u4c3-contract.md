# M2.u4c3 acceptance contract — MAIN

Baseline `69a4104`, gate green (`Ran 396 tests in 61.094s / OK`, `uv build` rc 0). Tier `kernel`.
Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`. Every other tracked path stays
byte-identical, `.agent/` records aside.

Scope = two leaves in the existing `function` group: `function verify-drafts OPERATION --actor ACTOR`
over `System.verify_drafts`, and `function verify OPERATION [--expected-function-hash HEX]` over
`System.verify_function`. Facts this record depends on are inlined; it never defers to a session-local
pointer.

Inherited and NOT re-litigated here: `.agent/decisions/m2u4c-design.md` Decisions 1/3/5 and its write
set; `.agent/decisions/m2u4c1-contract.md` sections B/C/D/E (the `_Outcome` seam, `main`'s single-channel
write, parser conventions, the `_CLIRun` harness).

## A — `function verify-drafts` exits 6 on a negative verdict

RULING: `_Outcome(payload=verification, status=0 if verification.passed else 6)`, payload on **stdout**,
stderr empty. Same exit class and same convention as the frozen `function verify` of
`.agent/decisions/m2u4c-design.md` Decision 4.

Both spikes self-rejected, so the ruling rests on the asymmetry between their two objections, not on
either verdict token.

- Measured, and agreed by both independently: `DraftVerification.passed is False` is NOT reachable
  through any supported public flow. Ordinary evidence growth supersedes, suspends or retires a draft
  rather than leaving a failing one eligible, so a negative verdict requires out-of-band ledger
  corruption that is still schema-valid. The branch is nevertheless live code, because such a ledger is
  accepted and checked — it is corruption detection, not lifecycle gating.
- Measured, and agreed by both independently: `_draft_verification_plan` — the sole planner
  `verify_drafts` consumes — has exactly one `skipped.append` site emitting the single literal
  `superseded-build` (`src/cement_runtime/system.py:3468-3474`), it arises from ordinary flows, and it is
  benign. The claim is scoped to that planner: function-promotion planning carries its own skip site,
  which this leaf never reaches.
- Both lenses named the same dominant hazard, which is what decides the fork: `function verify` and
  `function verify-drafts` are sibling verbs in one group over one `passed` field, so mapping false to 6
  in one and 0 in the other silently drops the gate of any script moved between them. Two independent
  lenses confirming ⇒ accepted.
- The two self-rejections are not symmetric. PLAIN's defect is unconditional and sits on the contract
  itself: `$?` cannot separate all-pass from all-fail, so every caller must reimplement the gate, and its
  own real stop-script needed 11 lines plus a structural JSON parser. STRICT's defect is conditional and
  pre-existing: rerun non-idempotence belongs to `verify_drafts`, not to the exit code, and it fires only
  in the corruption-only branch.
- Cost of the ruling over PLAIN, from PLAIN's own accounting: ~4-6 production lines, ~12-20 test lines.

REJECTED, with the reason recorded: exit 0 always. Its strongest form — "a recorded negative verdict is
a successful write, exactly as root `verify` treats one" — is true and still loses, because under it a
corrupt artifact drops out of the promoted set with exit 0 on every command an operator runs.

Retry hazard, accepted rather than mitigated in code: exit 6 is a VERDICT class, never a transient
error, and an automated retry-on-nonzero wrapper double-writes. A failed row stays `draft` — the
transitions at `src/cement_runtime/system.py:3582-3600` cover `promoted` and `verified` only — so it
stays eligible and each rerun commits a fresh report plus `artifact.verification_failed` event with a
distinct report ID. The invariant is per target and per invocation — `+1` report and `+1` failure event
each time — never a fixed absolute count, which depends on how many reports the target already carried.

Exit 6 is distinctive in this respect and the ruling does not pretend otherwise. Codes 2 and 3 fail
before any write; code 4 is the one class where retry IS the intended recovery, since the locked-recheck
`StateError` rolls its transaction back and a fresh call succeeds once concurrent state settles; code 5
reports corruption a retry cannot clear. Only 6 guarantees a committed row and repeats the write on an
unchanged rerun, so a generic `Restart=on-failure` or retry-on-nonzero wrapper amplifies exactly this
code. That is a real cost of the ruling, accepted rather than mitigated in code, and u5 owns documenting
it alongside the exit map.

## B — the verdict predicate is `passed` alone

RULING: `skipped` NEVER affects exit status. A skipped row is deliberately ineligible, not tested and
not failed, and the library labels such a batch `passed=True`; letting it force 6 would make status
contradict its own payload and would rename expected supersession as verification failure.

Pinned as an adjacent accept/reject pair, per the standing bound rule:
`passed=true, skipped≠∅` → exit 0, and `passed=false, skipped=∅` → exit 6.

An empty eligible set is a vacuous pass: `passed=all(...)` over an empty tuple is True
(`src/cement_runtime/system.py:3690`), so a registered operation with nothing compiled exits 0 with
`entries: []`. Pinned adjacent to the all-pass case so exit 0 is never proved by emptiness alone.

## C — `verify-drafts` emits the library model; `verify` must project

`DraftVerification` → emitted whole through `_emit`'s `asdict`, per `.agent/decisions/m2u4c1-contract.md`
section A. Its transitive graph is `DraftEntry` → `VerificationReport` → scalars and a `failures` tuple,
plus `skipped` rows of exactly `{artifact_id, input_hash, reason}`; it reaches no `FunctionDocument`, no
text blob and no private cache, so the Decision-3 ban is satisfied structurally. `entry_seal` is `null`
on a failed row (`src/cement_runtime/system.py:3627`).

`FunctionVerification` carries `document: FunctionDocument | None`, so Decision 3 FORBIDS emitting it.
The projection is exactly the four fields Decision 4 names, and no more:

```
{"passed": bool, "entries": int, "function_hash": str|null,
 "checks": [{"key": str, "passed": bool, "detail": str}, ...]}
```

`checks` keeps library order (P1-P6) as a JSON array; `_emit`'s `sort_keys=True` sorts object keys only.
`function_hash` is `null` where no hash was reached and a DIAGNOSTIC hash where one survives a failed
check — it is never evidence of a passing set, and consumers gate on `passed`.

## D — parser surface

- Both leaves attach to the existing `function` group, after `receipts`, and dispatch in the matching
  slot inside `_run`'s `function` branch.
- `verify-drafts`: positional `operation`; `--actor` REQUIRED (actor-bearing write, per Decision 3).
  Forwarded as `verified_by=`.
- `verify`: positional `operation`; `--expected-function-hash`, no default, forwarded as
  `expected_function_hash=` UNVALIDATED — the library's 64-lowercase-hex check
  (`src/cement_runtime/system.py:2946-2951`) is the sole bound, exactly as the limit-family convention
  forwards unclamped. The CLI never pre-checks and never normalizes case.
- Neither leaf routes to the root per-artifact `verify` at `src/cement_runtime/cli.py:98-100`.

## E — probe corpus (expected outcomes are contract, not suggestion)

`function verify-drafts`:

| invocation / state | exit | stdout | stderr |
| --- | --- | --- | --- |
| every eligible draft passes | 0 | `passed: true`, `entries` length N | empty |
| registered, nothing compiled (empty batch) | 0 | `passed: true`, `entries: []` | empty |
| stale draft superseded by a newer build | 0 | `passed: true`, one `skipped` row, `reason: "superseded-build"` | empty |
| middle of three drafts corrupted | 6 | `passed: false`, `[true,false,true]`, failed row `entry_seal: null` | empty |
| immediate rerun of the same corrupt ledger | 6 | `passed: false` again | empty |
| unregistered operation | 3 | empty | `{"error":"not_found",...}` |
| operation lives in another partition | 3 | empty | `{"error":"not_found",...}` |
| `--actor` omitted | 2 | empty | `{"error":"invalid",...}` (argparse) |
| `--actor ""` | 2 | empty | `{"error":"invalid",...}` |

`function verify`:

| invocation / state | exit | stdout | stderr |
| --- | --- | --- | --- |
| promoted set passes P1-P6 | 0 | four keys exactly, `checks` in P1-P6 order | empty |
| `--expected-function-hash` matching | 0 | `passed: true` | empty |
| `--expected-function-hash` a different valid digest | 6 | `passed: false`, diagnostic `function_hash` non-null | empty |
| per-entry promotions with no `promote_function` checkpoint (P6) | 6 | `passed: false`, only the receipt check false | empty |
| empty promoted set | 0 | `passed: true`, `entries: 0` | empty |
| `--expected-function-hash` not 64-lowercase-hex | 2 | empty | `{"error":"invalid",...}` |
| unregistered operation | 3 | empty | `{"error":"not_found",...}` |

Behavioral pins beyond the tables:

1. Reaching a false draft verdict: adapt the committed recipe at `tests/test_system.py:5182-5190` —
   capture the trigger DDL from `sqlite_master`, `DROP TRIGGER artifacts_build_fields_immutable`,
   `UPDATE artifacts SET artifact_json = '{}' WHERE id = ?`, then RECREATE the trigger from the captured
   DDL before committing. Restoration is mandatory here and is absent from the library-level precedent,
   because that test reuses one long-lived `System` whose schema fingerprint was checked at construction,
   while every CLI invocation constructs a fresh `System`: a still-dropped trigger fails the fingerprint
   check first, measured as exit 5 `live database schema does not match the runtime schema` with the
   corrupt row never reached. Corrupt the MIDDLE of three, per the standing set-check rule; a single-row
   fixture proves only that the command can reject *a* row.
2. Exit 6 carries its payload on stdout with stderr EXACTLY empty, asserted on both leaves. A nonzero
   status that writes to stderr would make the verdict indistinguishable from an error class.
3. Durability at exit 6: after the failing `verify-drafts`, the report row and the
   `artifact.verification_failed` event are committed. Exit 6 must not read as a rolled-back call.
4. `function verify`'s payload has EXACTLY the four keys, asserted as an exact set, with no `document`
   key at any depth and no document text anywhere in the emitted bytes.
5. Forwarding is exact: a spy on each `System` method records partition and operation passed
   positionally in that order, `verified_by` from `--actor`, `expected_function_hash` `None` by default
   and the exact string when supplied — never upper-cased, stripped or defaulted.
6. Leaf isolation both ways: `function verify --projection-limit 5` and `function show --actor x` are
   usage errors, and `function verify-drafts` without `--actor` is a usage error while root `verify`
   keeps its defaulted actor.
7. Existing-leaf regression: one previously-shipped command keeps its exit code and exact stdout bytes
   through the runner.
8. The exit-map anchor stays symbol-qualified, not line-numbered, since this unit shifts `main`'s lines.

## F — invariant surfaces

- `git diff --name-only 69a4104..<unit commit>` touches exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py`, and `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/`
  stay byte-identical. u5 owns every M2 documentation edit, including exit 6.
- `_emit`, `_Outcome`, `main`'s channel branch and every existing exception mapping stay byte-identical.
- `CLITests.promote_set` keeps driving `System.verify_drafts` directly. Test SETUP must not run through
  the leaf under test, or the leaf's own probes stop being independent evidence.
- No new dependency; imports stay stdlib plus in-package.

## G — known limits, to be carried into the roadmap entry

- The `verify-drafts` negative branch is unreachable through supported flows; every test of it drives
  out-of-band corruption, so the suite proves the CLI's handling of a corrupt ledger, never that ordinary
  operation can produce one.
- Rerun after exit 6 is not idempotent: each invocation commits a fresh report and event for the same
  unchanged bad draft, with a distinct report ID.
- Exit 6 now means two different objects across two leaves — an aggregate committed-set P1-P6 failure,
  and at least one per-draft verification failure. `$?` says only "verification negative"; the payload
  distinguishes them.
- `$?` cannot separate authority denial from the locked-recheck `StateError` (both 4), nor an
  unregistered operation from a wrong partition (both 3).
- `main` still has no catch-all, so a corrupt persisted receipt scalar reachable from `verify`'s P6
  escapes as a raw `TypeError`, `ValueError` or `OverflowError` — all three, per the standing
  persisted-scalar rule, since `_function_receipt_from_row` converts with bare `int(...)` and P6 catches
  `IntegrityError` alone (`.agent/polish.md` `pri=2`). No test may claim total CLI error mapping over
  corrupt ledgers.

## Gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, rerun by
MAIN from committed state at close.
