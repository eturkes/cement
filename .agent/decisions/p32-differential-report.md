# p32 differential instrument — scenario coverage (tester-1)

Contract = `p32-plan.md` observable equivalence + dispatch scenario floor. Oracle = runtime at
`1b5b7d7`, executed black-box; runtime implementation and MAIN's changes stay unread.
Status = covered; baseline/base PASS (2,712 lines); determinism PASS; detail and order mutants
both detected. Grading command = `rg -c 'un[k]nown' .agent/decisions/p32-differential-report.md`
→ no matches, rc 1. Outcome counts include each call's ledger/counter companion line.

| id | scenario | defects planted | probes run | outcomes recorded (count) | status |
|---|---|---|---|---|---|
| S01 | healthy exact function, 3 entries | none; empty set; uncompiled examples; invalid limits/hash/input; scope collision spellings; generated JSON domain (scalar/container/Unicode/int64 boundaries) | common sweep + ABI signatures + per-member verify/promote + generated resolve before/after promotion | 372 | covered |
| S02 | policy text + digest | whitespace/key-order noncanonical JSON and zero digest together | common sweep | 48 | covered |
| S03 | policy non-object / parse failure | array, null, string, malformed JSON, each with matching byte digest | common sweep per variant | 192 | covered |
| S04 | invalid CompilePolicy object | missing keys; confirmations below 2; boolean reviewer threshold; negative span | common sweep per variant | 192 | covered |
| S05 | policy_hash mismatch alone | zero digest; valid canonical policy unchanged | common sweep | 48 | covered |
| S06 | compound promoted members | 7 members: missing report, failed report, scope mismatch, report artifact_hash mismatch, report build_hash mismatch, malformed artifact JSON, artifact revision mismatch; separate report-details shapes | common sweep + every member verify/promote | 216 | covered |
| S07 | receipt membership | tail seal, input_hash, ordinal; function_hash rewritten in membership + receipt to retain FK validity; compound seal/input/ordinal in one receipt | common sweep per variant | 240 | covered |
| S08 | promotion-plan candidates/retained | duplicate valid candidate; contradicted retained member; ineligible build; old-program retained and candidate rows; all four in one set | common sweep; every member on compound sets | 440 | covered |
| S09 | stale revision + bounded projections | old-revision draft after revision; 16 pending proposals; last pending input_hash corruption beyond limits 1/2; ready and blocked scopes | common sweep before/after tail corruption | 96 | covered |
| S10 | learning cases exact/current/candidate | recognized and unmatched raw inputs; differing pending outputs; exact-only example; stored program; candidate with unwitnessed layout; malformed/null candidates | common sweep before/after stored projection + explicit candidate calls | 108 | covered |
| S11 | verification failures | artifact snapshot digest tamper; actual added evidence; replay output mismatch; four widened boundaries; structural edit incorrectly retaining key | common sweep + every member verify/promote | 280 | covered |
| S12 | single-artifact promotion binding | missing report; failed report; resealed wrong scope/details; all four report binding fields separately | common sweep + every member verify/promote per defect | 384 | covered |
| S13 | over-capacity set | 3-member set under patched cap 3 (accepted) and 2 (rejected) | common sweep at both adjacent caps | 96 | covered |

## Probe contract

Common sweep = `verify_function` (with/without expected hash), `function_report` (limits 1, 2,
default; explicit receipt where present), `latest_function_receipt`, receipt reconstruction,
`resolve` (hit/miss under off/follow/pinned; pinned only with receipt), promotion inspection,
`promote_function` (held hash + freshly inspected hash), `verify_drafts`, `compile`,
`learning_cases` (current/exact + candidate program), `test_projection`, `verify`, `promote`.
Each probe owns a copied ledger and fresh deterministic counter/clock; failed writes cannot
contaminate later probes. Every call emits its full result or exception class/full message, then
all-table row counts + hashes, SQLite dump hash, and clock/ID call counts (including failed writes).
Mapping insertion order and vector order stay observable. Verification documents carry text SHA-256; other dataclasses serialize recursively.

Corruption = assert nonzero rowcount → restore every trigger's exact DDL and original order →
commit → reopen `System`. Switch selection uses the same schema-preserving edit to reach corrupted
follow/pinned read paths without the setter's admission checks masking them. No rewritten-schema
fixture, no schema-validation bypass. S11 interpreter faults are labelled injected library-boundary
fixtures, not real-ledger corruption reproductions. S13 patches only the exported set-cap constant.

## Reachability controls

- S06: `sealed-passing-reports` reports `5 failure(s)` and previews the first three; promotion check
  reports `7 failure(s)` and previews the first three. Middle/last members break independently.
- S08: duplicate candidates → `IntegrityError: multiple verified candidates claim current input …`;
  contradicted retained → `StateError` naming supersede/revoke/suspend; healthy program transition
  yields `projection-superseded` skips; stale valid-key candidate and ineligible build yield
  `superseded-build` skips. Compound set stops at the duplicate candidate: that precedence is compared.
- S11: added evidence → `verify` failure `evidence snapshot changed`; batch eligibility correctly
  reports that draft as `superseded-build` rather than verifying it. Replay injection →
  `2 exact fixture replay tests failed`; boundary injection → partition/operation/revision/input
  widened-scope failures; structural injection → four `a structural edit kept the projected key`
  failures on the projected draft.

## Commands / results

- Seed validator: `rg -c 'un[k]nown' .agent/decisions/p32-differential-report.md` → `15`, rc 0
  (positive control: seeded unfinished cells present; bracket spelling keeps this record outside its census).
- Scenario families: explicit project interpreter + baseline `PYTHONPATH`, `p32-scenarios.py
  --scenario S01` through `--scenario S13` → rc 0 after fixture repairs. The initial S01 family
  (before generated-hit extension) measured wall 2.52 s, user 1.58 s, system 0.14 s.
- Initial fixture failures (not runtime defects): pinned switch omitted required receipt_id →
  SQLite CHECK failure; rewriting receipt function_hash while selecting its old switch hash →
  FK failure. Both fixtures corrected to preserve schema and FK validity.
- Scheduling: the first `offload run --local` attempt waited for occupied slots and was stopped
  before execution. These targeted unit instruments then ran directly under the fast-gate allowance;
  the full project gate/suite remained unrun.
- Python LSP `documentSymbol` on the driver succeeded; AST parse of both scripts passed.
- Comparator controls: identical outcome → `SAME 1`, `RESULT: PASS`, rc 0; changed outcome and
  deleted outcome → `DIFF S01.1.control`, `RESULT: FAIL (1 differing lines)`, rc 1 each.
- Setup control: `p32-differential.py --base p32-deliberately-absent-revision` →
  `fatal: invalid reference: p32-deliberately-absent-revision`, `RESULT: ERROR`, rc 2.

Executed argv below use portable path variables: `$WT` = invoking worktree; `$PY` = primary
checkout's existing `.venv/bin/python`. The driver freezes its invoking-head scenario bytes once
and executes that same copy against both selected trees. A revision preceding the instrument
therefore works. Temporary detached worktrees are removed in `finally`; child imports assert
that `cement_runtime.__file__` lies beneath the selected tree's `src`, and isolate bytecode caches.

```sh
"$PY" -B "$WT/.agent/decisions/p32-differential.py" --base 1b5b7d7 --head 1b5b7d7
```

```text
CENSUS S01=372 S02=48 S03=192 S04=192 S05=48 S06=216 S07=240 S08=440 S09=96 S10=108 S11=280 S12=384 S13=96
SAME 2712
RESULT: PASS
rc=0; wall=83.10 s; user=49.16 s; system=4.05 s
```

```sh
"$PY" -B "$WT/.agent/decisions/p32-differential.py" --base 1b5b7d7 --self-test
```

```text
SELF determinism: SAME 2712
SELF detail: DIFF rc=1 lines=243 first=S01.1.healthy.verify_function
SELF check-order: DIFF rc=1 lines=103 first=S01.1.healthy.verify_function
RESULT: PASS
rc=0; wall=176.55 s; user=98.52 s; system=7.89 s
```

The two DIFF lines are the negative credentials: a temporary source-copy literal changes
`entries have unique input digests` to `entries have MUTATED input digests`; separately, a
signature-preserving wrapper in that copy exchanges the first two returned checks. The same
comparator used by normal runs returns 1 for each. No source file in a tracked checkout changes.

## Findings / limits

No baseline defect asserted. Equality corpus is finite, not an exhaustive proof over arbitrary
ledgers. Runtime exceptions are outcomes, not skipped probes. The full suite, gate, build and
cosmic-ray mutation campaign are not run by this instrument. Its two planted controls credit the
instrument's ability to detect detail/order drift, not preservation-test mutation credit.
No refactor result is claimed here: MAIN runs this same fixed corpus against its head.
