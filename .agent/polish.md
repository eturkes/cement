# Polish register

Deferred-perfection items, off the milestone spine. `/session-polish` = sole consumer; protocol lives
there. Rows are born at deferral with the acceptance check already written.

Gate for every row unless it says otherwise: `uv run python -m unittest discover -s tests -t .` plus
`uv build`. Scope sources, assurance tiers and the unit set stay fixed — a row needing any of those
changed is spine work, not polish.

- `pri=1` `size=M` — port the mutant replay driver to committed state. `.scratch/main-replay/replay.py`
  produced u4b's recorded mutation verdicts and is gitignored, so a gate backing a durable roadmap claim
  cannot rerun from a clean checkout. It survives on this workstation together with u4b's catalogue
  (`.scratch/agents/rev2b-m2u4b-mutants.jsonl`) and the wave's result sets
  (`.scratch/main-replay/final-*.jsonl`), so the port is a copy-and-harden while that holds — `.scratch/`
  is machine-local and unbacked, so treat the window as closing. Regeneration spec, should the sources go,
  is recorded in `.agent/memory.md`: N isolated clones of `src`/`tests`/`examples`,
  `PYTHONDONTWRITEBYTECODE=1` plus `__pycache__` purge, per-mutant proof that the interpreter loaded the
  mutated module from its clone, byte-exact restore, `--reanchor` over a `difflib` line map, `--control`
  pristine sweep at full worker count. Throughput reference: 61 mutants at 8 workers ≈ 13 min, 254 ≈ 50
  min. Acceptance: a committed dev tool runs a catalogue `.jsonl` from a clean checkout, its `--control`
  sweep is green, and a seeded known-live mutant reports as surviving while a seeded known-dead one
  reports as killed; where u4b's catalogue was recovered, replaying it reproduces 58 killed / 1 superseded
  / 2 surviving, those 2 being the reviewer's proved-equivalent pair.

- `pri=4` `size=M` — stored-scalar conversions in `system.py` are unguarded at several sites, third
  recorded instance of one class, and NONE of them is reachable through any supported route. Scope
  correction from the M2 review, which retired the escalating severity three earlier rows had assigned it:
  the storage layer already enforces what the missing guards would. All 13 user tables are `STRICT`
  (`sqlite_sequence` alone is not), so a non-numeric `TEXT` is unstorable in an `INTEGER` column and
  numeric `TEXT` converts to `INTEGER` at write; every integer column the unguarded sites read is
  `NOT NULL`, so `NULL` is unstorable too. Exactly three nullable `INTEGER` columns exist repo-wide -
  `requests.lease_until_us` (`store.py:56`), `proposals.reviewed_at_us` (`store.py:97`),
  `artifacts.promoted_at_us` (`store.py:163`) - and every conversion reading one is already guarded:
  `or 0` at `system.py:621`, `or now_us` at `system.py:993`, `is not None` at `system.py:1211` and
  `system.py:5159`. So the guarded/unguarded split tracks the nullable/NOT NULL split exactly, and the
  earlier `NULL`/non-numeric-text probes all reached their sites through a rewritten schema or a
  fabricated row. A fresh `System` - which every CLI invocation constructs - rejects a rewritten schema
  through its fingerprint check and maps it to exit 5, so the in-process rewrite route dies at
  construction. Remaining true statement: numeric text is accepted where an exact stored int is required,
  and a hostile in-process caller holding a fabricated row or a cursor proxy reaches raw
  `TypeError`/`ValueError`. Keep the row for defense in depth and consistency with the `_stored_int`
  pattern the memory rule already prescribes, not for reachability. Acceptance: the audit in
  `.agent/decisions/m2u4c-surface.md` Section G lists every conversion site with its guard status and its
  column's nullability; every site reachable from a public API either translates
  `TypeError`/`ValueError`/`OverflowError` to `IntegrityError` or rejects a non-`int` stored value
  outright; one committed probe drives numeric text through a receipt integer field and expects
  `IntegrityError`; any probe needing a schema rewrite or a fabricated row is labelled as such and is
  never cited as a real-ledger repro; suite green.

- `pri=2` `size=M` — `function_receipts` has no index carrying `(partition, operation, sequence)`, so
  receipt pagination costs O(all receipts in the partition) per page. `EXPLAIN QUERY PLAN` shows
  `USE TEMP B-TREE FOR ORDER BY` on the default all-revision query: measured 1,001 of 1,001 rows visited
  for `limit=3`, and 899 of 899 on the cursor path, against 3 when a revision filter applies. Receipt
  history is unbounded and append-only, so the cost grows without limit while `limit + 1` bounds only the
  rows Python materializes. No answer is ever wrong, which is why this is polish and not a review fix, and
  the roadmap's u4a "exact bounded materialization" claim has been narrowed to say so. The fix is not
  free: adding the index moves `SCHEMA_VERSION` 2 -> 3, changes the schema fingerprint, forces the
  pre-1.0 ledger reset u3b1 already established as the migration posture, and churns every
  schema-structure pin. Acceptance: an index covering `(partition, operation, sequence)` exists,
  `EXPLAIN QUERY PLAN` on both the default and the cursor receipt queries reports no
  `USE TEMP B-TREE FOR ORDER BY`, a probe over a 1,001-receipt ledger asserts rows visited stays within a
  small constant of the page size on both paths, `SCHEMA_VERSION` and the fingerprint move together, and
  the suite is green with the reset documented.

- `pri=3` `size=S` — the report anchor validator runs from no gate. `map` briefs make each report's
  `path:line` claims machine-checkable, and the M3 planning wave's validator is now tracked at
  `.agent/decisions/m3-report-validate.py` (pipe-table shapes anchor/claim/qa/unit; anchor path plus line
  must resolve and the backticked symbol must be a substring of that source line; repo root by upward
  `pyproject.toml` search, so a relocated copy still works). Nothing reruns it, so a stale anchor in a
  tracked record is invisible until a human reads it. The M2-era `.scratch/validate-anchors.py` variant
  (fenced ```anchors block, TAB-separated rows, 268 anchors under MAIN's rerun at u4c5) is retired with
  its report format. Acceptance: the validator runs from the configured gate over every tracked
  `.agent/decisions/*.md` carrying a recognized table shape, a committed fixture report carrying one
  resolving anchor and one stale anchor makes the gate fail, and briefs cite the tracked path.

- `pri=2` `size=M` — port the seam mutation battery to a committed dev tool. u4c1's 9-mutant battery over
  `_Outcome`, `main`'s channel branch, the parser slot and limit forwarding killed 9/9, but it ran from
  `.scratch/mutants.sh` and died with the wave, so the claim outlives its driver (same defect as the u4b
  replay driver already tracked here). Acceptance: a tracked script takes a catalogue of
  `(file, anchor, old, new, test)` rows, asserts each patch changed the file, purges `__pycache__` with
  `PYTHONDONTWRITEBYTECODE=1`, runs the named test per mutant, restores byte-exactly (`cmp` proves it),
  and exits nonzero on any survivor; rerunning it from a clean checkout reproduces 9/9 without edits.
  u4c5b is the third instance and the seed with the widest catalogue: `.scratch/mutants-u4c5b.py` carries
  13 mutants over the `--out` writer (12 killed, 1 proved equivalent), whole-file `str.replace` with an
  identity-check per mutant, kill decided by the suite's rc rather than by parsed names (subTest failures
  print no inline `FAIL`), a restore in `finally` plus a `RESTORED-IDENTICAL` compare, and a documented
  equivalent mutant so a survivor list of exactly `[installed-file-unlinked]` is the closure signal.
  u4c5a's driver is the better seed for anchor handling: `.scratch/mutate-u4c5a.py` already runs
  a 16-mutant catalogue over the export leaf (16/16 killed), asserts each anchor matches exactly once
  before patching, asserts `text != before`, rejects any run whose selected-test count moves, restores in
  a `finally` and proves the restore with a sha256 compare. It is gitignored like its predecessors, so the
  port is a copy-and-harden while it survives on this workstation. Its one measured trap is worth keeping:
  an anchor matching 2 times is reported as ANCHOR-MISS, not silently applied — `"checks": [asdict(check)
  for check in verification.checks],` occurs in both the `verify` and `export` leaves.

- `pri=2` `size=M` — bounded projections have no cursor, and two families page in opaque-id order.
  `function_report` clamps six detail lists with one `projection_limit`, but the only way to see a
  truncated remainder is to raise the limit toward 10,000; there is no offset, cursor or stable sort key
  exposed. Members project by `ordinal` and artifacts by `sequence DESC`, both canonical, while
  `pending_proposals` orders by `p.id` (`src/cement_runtime/system.py:2740`) and
  `stale_revision_anomalies` by artifact `id` (`src/cement_runtime/system.py:2846`) — random `prop_*`/
  `art_*` hex, so a truncated page of either is an arbitrary subset, stable per ledger but unrelated to
  insertion or content order. Probed: `pending-a` and `pending-b` swap places across runs at
  `--projection-limit 1`, which is what forced the CLI test to pin set membership plus per-ledger byte
  stability instead of insertion order. Affects every later `function` leaf that pages the same model.
  Acceptance: both queries order by a meaningful, documented key (creation time or input hash), one probe
  seeds three rows in each family and asserts the projected prefix at limits 1 and 2 is the canonical
  prefix of the limit-3 projection, and the report's docstring states the ordering guarantee per family.

- `pri=3` `size=S` — `stale_revision_anomalies` is unreachable through supported flows, so its projection
  path ships behaviorally untested except through out-of-band state. `operation revise`
  (`src/cement_runtime/system.py:509`) retires every artifact it strands, and no other command leaves a
  draft/verified/promoted artifact on a superseded revision; the CLI test reaches the family only by
  bumping `operations.revision` with a direct `UPDATE`. That is faithful to the family's purpose — it
  reports ledger corruption — but it means no test exercises the transition that would produce it in
  production. Acceptance: either a supported command can strand an artifact and a probe drives it, or the
  model documents the family as a corruption detector, and the CLI's own probe cites that documentation
  instead of asserting the state is otherwise reachable.

- `pri=3` `size=S` — `Candidate.provenance` contract unenforced at its sole consumer, `system.py:784` in
  `System.handle`. `Candidate` is a frozen dataclass typing `provenance: Mapping[str, object]` with no
  runtime check, and `canonicalize(dict(candidate.provenance), max_bytes=65_536)` is the only site that
  reads it. Probed: `[]` becomes `{}` and is stored as empty provenance; `'text'` escapes as a raw
  `ValueError`; `5` and `None` escape as raw `TypeError`. The `type(provenance.value) is not dict` guard
  on the following line never fires for any of them, because `dict()` normalizes or raises first. Same
  defect class memory already records twice for persisted scalars, here on an input path. Acceptance: one
  probe per shape (`[]`, `'text'`, `5`, `None`) raises `ValidationError` out of `handle`, with `[]`
  failing rather than silently becoming `{}`.

- `pri=4` `size=S` — `.agent/decisions/` input pointers read as live references but resolve nowhere except
  this workstation. Seven records open with `Inputs:` lines citing `.scratch/agents/*.md`, plus
  `.scratch/main-verify/tree`, `.scratch/main-verify/f1probe.py` and `.scratch/m2u3b1.patch`; `.scratch/`
  is gitignored, so all 14 resolve to nothing in any clone. Here 11 still resolve and 3 are gone outright
  (`m2u3b1.patch` and both `main-verify/` entries), so the substance behind most is still recoverable —
  rescue before the window closes. Acceptance: each record's inputs either carry the substance inline or
  are marked expired, and no tracked file cites a `.scratch/` path as though it were retrievable.

- `pri=5` `size=M` — 166 Pyright `reportAttributeAccessIssue` errors across `tests/test_system.py` lines
  221-1192, pre-existing at `d0b7e93`: unnarrowed union member access in baseline outcome assertions.
  Type noise only, no behavior at stake, and Pyright is not a configured gate. Acceptance: that region
  narrows its unions explicitly, an ad-hoc `uvx pyright tests/test_system.py` reports zero
  `reportAttributeAccessIssue`, and the suite stays green.

- `pri=3` `size=S` — port the human-facing register audit to committed state. `.scratch/register/audit.py`
  measured the ASD-STE100 pass over `README.md`, `docs/*.md` and `examples/hospital_ocr/README.md`, so the
  conformance numbers that pass recorded cannot rerun from a clean checkout; its spec sits in
  `.agent/memory.md`. Two known false positives survive: a possessive `'s` counts as a contraction, and a
  block without terminal punctuation joins the next block into one over-length sentence. Acceptance: a
  committed dev tool run from a clean checkout reports zero sentences over the caps across the four
  surfaces, flags a seeded 30-word instruction and a seeded `simply`, and leaves possessives and
  terminal-punctuation-free bullets unflagged.

## M2.u4c6 deferrals

- pri=2 `size=S` — `_input` does not translate an `OSError` raised by `sys.stdin.read` /
  `sys.stdin.buffer.read` (`cli.py:237,247`), so a read failure on `--input -` escapes `main` as a raw
  traceback on EVERY leaf that accepts the flag, not just `function eval`. u4c6 inherited the limit rather
  than adding a leaf-local message, because the fix belongs to the shared helper. Acceptance: the two
  stream reads translate to the leaf's existing exit 2 `invalid` vocabulary, one committed test injects an
  `OSError` at each of the two stdin hosts, and no existing `--input -` message changes.
- pri=3 `size=S` — `_emit` performs no explicit flush, so payload-and-status guarantees on every leaf
  assume a healthy stdout: a buffered embedding stream may retain data after `main` returns, and a
  `BrokenPipeError` or an exit-time flush failure can replace the intended status with a raw exception or
  Python's exit 120. Same cross-resource class as u4c5b's file receipt, now restated for stdout by u4c6's
  reviewer. Acceptance: a decision record either accepts the limit repo-wide and states it once in
  `README.md`/`docs/`, or `main` flushes before returning and one committed test proves a broken pipe maps
  to a stated code; either way one test pins a custom buffered stream's observed behavior.

## M2.u4c5a deferrals

- pri=3 `size=S` — merge-or-drop decision on the diff-blind teammate's export suite. 28 tests written from
  the contract alone, preserved byte-identically at `.scratch/agents/test-m2u4c5a-suite.py` (its worktree
  is gone); 36 failures + 2 errors at baseline, 28/28 green against the shipped implementation, and MAIN's
  own 21 tests carry every contract pin, so nothing merged. The question is whether any of its 28 probes
  covers a case the shipped 21 leave open, or whether all 28 are re-expressions — u4c1's suite contributed
  three genuinely new probes, u4c4's contributed none. `.scratch/` is machine-local and unbacked, so treat
  the window as closing. Acceptance: each of the 28 is mapped to the shipped test that subsumes it or
  merged into `tests/test_cli.py` under the existing naming, the file is then deleted rather than left
  dangling, and the suite is green with the merged count recorded.

- pri=3 `size=S` — exit 6 now names FOUR objects across four leaves (`verify-drafts` failed drafts,
  `verify` a failed committed set, `export` a refused export, `eval` an input outside the domain) with one
  meaning and four payload shapes, distinguished by command and channel alone. Nothing is wrong; the
  surface is simply at the point where a reader of `$?` cannot tell them apart. The decision-record part is
  DONE — `.agent/decisions/m2u4c6-contract.md` Decision 1 fixes the four shapes as final and names the
  discriminator (command + channel), noting that a generic status-only supervisor cannot discriminate.
  Remaining acceptance: `README.md`/`docs/` state the exit-6 contract once, and the M2 review's claim
  replayer re-derives it across all four leaves.

## M2.u4c4 deferrals

- pri=2 `size=S` — the locked-recheck race is pinned only by injection, though it is real behavior. A
  default-constructed `System` re-reads the locked prospective function inside `promote_function` and
  raises `StateError` when it moved between `inspect` and `promote`; the CLI maps that to exit 4 with
  `error: "conflict"`, and u4c4 drives it through `main`'s exit map with a patched `System.promote_function`
  rather than through a real ledger. Exit 4 is the one exit class where retry IS the intended recovery
  (`.agent/memory.md`), so the branch an operator's wrapper depends on is the one no end-to-end probe
  reaches. Acceptance, corrected by the M2 review — the original text named a message the described
  scenario cannot produce: `promote_function` compares member, candidate and retired IDs BEFORE the hash
  (`src/cement_runtime/system.py:4262-4277`), so a changed prospective union raises
  `function promotion candidates changed during authorization`, and the expected-hash branch runs only
  once those identities still match. So: a committed probe drives two CLI invocations against one ledger
  with a supported command changing the prospective union between the hash read and the promote, observes
  exit 4 with `function promotion candidates changed during authorization` and no patching, and asserts
  the rejected call adds no receipt and no status transition; the stale-hash message keeps its own
  separate pre-invocation probe.
- pri=3 `size=S` — `--actor` grammar is nearly unpinned on the promote leaf. The merged suite carries a
  single occurrence exercising the value's validation, so the accept/reject PAIR the memory rule requires
  at every bound is absent here: an empty actor, an over-long actor and one carrying illegal characters
  all ride on the library's `_name` behavior with no CLI-side pin, and `--actor` is what the promotion
  receipt attributes activation to. Acceptance: one probe per shape (empty, boundary-length accepted,
  boundary+1 rejected, illegal character) asserts the exit code and the mapped message, and the accepted
  boundary value is read back out of the promotion receipt.

## M2.u4c3 deferrals

- pri=2 `size=S` — port the agent-report anchor validator to a committed dev tool. u4c3 gated every
  Wave-1 and Wave-2 report on `.scratch/validate-anchors.py`, which parses fenced ```anchors blocks of
  TAB-separated `path<TAB>line<TAB>fragment` rows, resolves each against a `--root`, and exits nonzero on
  any bad anchor or leftover `TODO-FILL` sentinel. It caught a surface map whose own claims were 12/25
  wrong, which is exactly the failure a reported-but-unverified number hides. Gitignored, so no clone
  reruns it — third instance of this class alongside the replay driver and the seam battery. Acceptance:
  a tracked dev tool validates a report from a clean checkout, a seeded bad anchor exits nonzero with the
  offending line printed, a seeded `TODO-FILL` exits nonzero, and a clean report exits 0.
- pri=3 `size=S` — `verify_drafts` reruns are not idempotent on a failing draft. A failed row hits none
  of the status transitions at `src/cement_runtime/system.py:3582-3600`, so it stays `draft`, stays
  eligible, and every rerun commits a fresh report plus `artifact.verification_failed` event with a
  distinct report ID. Harmless today because the negative branch needs out-of-band corruption, but exit 6
  makes an automated retry-on-nonzero wrapper amplify it. Acceptance: either a failed row carries a
  status or reason that makes it ineligible until the operator clears it, or the model documents
  unbounded report growth per rerun and a probe pins the `+1 report / +1 event` invariant per invocation.

## M2.u4c2 deferrals

- pri=2 `function receipts` / historical `show`: merge the diff-blind teammate's 13 contract-derived
  tests. They passed 35/35 against the landed implementation but were never merged, and the worktree
  died with the wave. Acceptance: re-derive from `.agent/decisions/m2u4c2-contract.md` Decision 8/9 and
  keep only probes MAIN's 17 do not already reach — repeated-flag last-wins, Unicode decimal digits
  reaching `type=int`, cross-leaf flag isolation in both directions, and surplus-positional rejection
  are the named non-overlapping ones. Gate: suite green, no existing test weakened.
## M2.u5a deferrals

- pri=2 Bundle-identity determinism is pinned by observation, not by mechanism.
  `test_bundle_identity_is_per_run_while_its_length_is_stable` runs two clean lifecycles under default
  entropy and asserts unequal hashes; the review proved that holding the ID stream and clock fixed makes
  two independent ledgers byte-identical, so the test observes provenance entropy rather than the
  documented causal path. Acceptance: one test that fixes the entropy sources and proves two runs equal
  byte-for-byte, then varies exactly one evidence or verification-example ID and proves the root
  `function_hash` moves while the length holds at 3,341. Retire the two-run observation test once the
  mechanism test lands, and keep the example README's per-run sentence bound to whichever test survives.
- pri=3 The example's offline phase proves ledger-freedom through `System.__init__` +
  `sqlite3.connect` patches in-process only. The three CLI subprocesses prove the operator route and
  invocation shape, never that the child process opened nothing — `eval` dispatches ahead of the `--db`
  gate, so absent `CEMENT_DB`/`CEMENT_PARTITION` rules out configuration alone. Acceptance: a
  process-level probe (syscall trace, `sitecustomize` audit hook, or an `open`/`connect` audit hook via
  `sys.addaudithook`) asserting the `function eval` child opens no database file, with the `python -S`
  gap stated wherever the claim is made.

## M2 review deferrals

- `pri=4` `size=S` — `_verify_row`'s `except (IntegrityError, ValidationError)`
  (`src/cement_runtime/system.py:3522`) has an unreachable second arm, so no honest probe pins it.
  Removing `ValidationError` from the catch leaves the whole suite green. Reachability was traced and the
  arm is defensive breadth, not a gap in coverage of live behavior: `_validate_promoted` raises
  `IntegrityError` at all six of its raise sites; `_run_verification` wraps `_artifact_from_row` and
  re-raises as `IntegrityError` (`src/cement_runtime/system.py:3739-3741`); and the two remaining
  `ValidationError` sources inside the try read immutable stored bytes — `parse_json(row["input_json"])`
  (`src/cement_runtime/system.py:3806`) and `canonicalize(execution.output)`
  (`src/cement_runtime/system.py:3827`), where `execute` runs the stored artifact against the stored
  input. `input_json` cannot be corrupted in place at all: `artifacts_build_fields_immutable`
  (`src/cement_runtime/store.py:310-318`) aborts the UPDATE. Acceptance: either the arm is documented as
  deliberate breadth over inputs the schema already fixes, or one probe pins it behind a dropped
  immutability trigger and is labelled a fabricated-corruption probe that is never cited as a real-ledger
  repro; suite green either way.

- `pri=3` `size=S` — `main` does not handle `KeyboardInterrupt`, so operator cancellation leaks a
  traceback. A console probe held an exclusive SQLite lock, ran `cement ... function show`, and sent
  SIGINT during the wait: the process returned `-2` with a Python traceback on stderr ending in
  `KeyboardInterrupt`. That contradicts the JSON-first, traceback-free CLI posture everywhere else, and no
  record states the traceback is intentional. Acceptance: SIGINT during a blocked database operation
  terminates with a chosen interrupt status and no traceback, one committed probe pins it, and if JSON is
  deliberately omitted for interrupts the exception is documented once in `README.md`/`docs/`.

- `pri=3` `size=S` — `verify_drafts`'s `verified_by` bound is unpinned at the CLI. The library validates
  it with `_text(..., maximum=256)` (`src/cement_runtime/system.py:155-166,3645-3648`), but the scoped CLI
  suite (`tests/test_cli.py:1574-1588`) pins only required/nonempty behavior, so weakening the leaf to
  accept oversized or control-bearing provenance leaves the suite green. This is the accept/reject PAIR
  the memory rule requires at every bound. Acceptance: adjacent 256-byte accepted and 257-byte rejected
  UTF-8 cases plus an accepted-printable/rejected-control pair through `function verify-drafts`, asserting
  exit 0 against invalid/2 with exact empty stdout on rejection, and the accepted boundary value read back
  out of the verification report.

- `pri=3` `size=S` — `--out` writes no parent-directory `fsync`, so the atomic rename is durable against
  process death but not against power loss. Source-derived only; the review ran no power-loss simulation.
  Same cross-resource class as the `_emit` stdout-flush row. Acceptance: either the export path fsyncs the
  parent directory after `os.replace` and one probe pins the call, or a decision record states the
  durability bound once and `README.md`/`docs/` repeat it wherever export durability is claimed.

- `pri=2` `size=M` — nine integrity checks across the function ABI and the P5 verifier are each
  individually deletable with the whole suite still green, so the committed tests do not pin them. In
  `src/cement_runtime/function.py:153-182`, deleting any ONE of four digest-syntax checks keeps all 23
  `FunctionTests` green: `evidence_snapshot_hash`, `output_hash`, `entry_seal` and `report.test_set_hash`.
  Three of those admit malformed values once the outer hash is recomputed; the `output_hash` mutant still
  rejects, but only through the later digest mismatch, which silently converts a promised
  `ValidationError` into an `IntegrityError`. In `src/cement_runtime/system.py:3264-3338`, five P5 field
  checks delete cleanly with all 42 verifier tests green: projected document ABI, canonicalizer, embedded
  hash, scope and entries-array type. Those five are currently redundant with `build_function`, but u2
  claims field-by-field reconstruction and self-checking rather than reliance on one constructor
  invariant, so the redundancy IS the defense-in-depth the claim promises. Production code is correct
  today; the exposure is that an integrity-boundary regression ships undetected. Acceptance: outer-rehashed
  malformed-value subtests for all four `function.py` fields asserting `ValidationError`, plus
  parameterized altered `build_function` results per P5 field asserting that only
  `function-hash-matches-snapshot` fails with its field-specific detail; all nine deletion mutants then
  fail, proven by a rerun of the catalogue that produced them.

- `pri=3` `size=S` — two real-scale boundary pairs are asserted only against patched-down limits. The 1M
  item ceiling (`tests/test_function.py:598-623`) is exercised by patching `FUNCTION_MAX_ITEMS` to a small
  fixture value, so nothing committed drives the declared number. The M2 review ran the real-scale probes
  and they pass: exactly 1,000,000 accepted and 1,000,001 rejected, and likewise for the byte gate, depth
  67/68 and entry count 50,000/50,001. Acceptance: commit the exact-max/max+1 pair at the declared value
  for items, with the slow cases marked so the default gate stays usable, and keep the patched-down
  fixtures for the fast path.

- `pri=4` `size=S` — the single-snapshot race test (`tests/test_system.py:4007-4101`) infers transaction
  lifetime from writer blocking plus a coherent result, so no committed assertion inspects
  `connection.in_transaction` at an inner verification call. The proof is therefore load- and
  timing-dependent rather than local, and a refactor could weaken it without failing. Acceptance: a
  targeted test wraps `_promoted_function_rows`, asserts `connection.in_transaction is True` before
  delegating, and verifies one successful result.

- `pri=3` `size=S` — two test fixtures create temporary directories inside the repository root:
  `tempfile.TemporaryDirectory(dir=".")` at `tests/test_cli.py:165` and `tests/test_system.py:183`. An
  interrupted run leaves `tmp*/cli.db` directories behind in the working tree, which the M2 review had to
  clean before it could read a trustworthy `git status`. Acceptance: both fixtures allocate outside the
  repository, or the suite removes them on teardown even when the run is interrupted, and a deliberately
  interrupted run leaves `git status` clean.

- `pri=3` `size=L` — the function layer outgrew one class. `System` (`src/cement_runtime/system.py:403`)
  spans 4,920 lines and 62 methods, and four judgment-bearing methods are individually oversized:
  `verify_function` 452 lines / cyclomatic complexity 67, `function_report` 356 / 36,
  `_function_promotion_plan` 227 / 31, `promote_function` 272 / 26. Transaction ownership is genuinely
  cohesive, so the class boundary is not wrong in kind — the function layer simply now carries several
  E/F-rated methods inside the same service object, which makes every integrity change reason across
  oversized methods and makes review and mutation coverage more expensive. Acceptance: the public `System`
  facade and its transaction ownership stay unchanged while cohesive function-layer internals move out;
  operation-policy normalization and artifact/report/member validation each get one owner; validation
  depth stays explicit; no E/F-rated function-layer method remains; the full suite, `uv build`, the
  healthy lifecycle and the degraded and recovery matrices are unchanged.

- `pri=3` `size=M` — three validation contracts are assembled independently at five sites
  (`src/cement_runtime/system.py:1995,2311,2929,3893,3940`). Operation-policy scalar and canonical
  validation is built separately by verify, report and promotion planning; receipt-member
  artifact/report/binding checks are built separately by reconstruction, report projection and
  promotion-entry construction. Pylint finds no token-level clone, so this is conceptual duplication with
  partly implicit differences in depth — which is the dangerous shape: a correction can land on one
  surface while another keeps accepting or reporting a different record, and bounded report projection
  versus full receipt verification is exactly where that divergence is hardest to audit. Acceptance: one
  helper or normalized record owns each binding family, callers select row-only, bounded-projection or
  full-reconstruction validation explicitly, and the receipt-discovery contracts, projection-limit
  contracts, degraded scenarios and full suite are unchanged.

## M3 planning deferrals

Off-spine at M3 planning. Each row carries the close check written while the evidence was fresh; the
substance behind each sits in `.agent/decisions/m3-plan-draft.md` S5 and `m3-plan-review.md` L6.

- `pri=4` `size=L` — separately installable command-source distribution. M3.7 ships the runner as a
  source/sdist example, which is sufficient. Acceptance: a second versioned wheel installs beside a
  wheel-only `cement-runtime`; core metadata declares no provider or runtime dependency; importing core
  loads no optional module; the second wheel exposes one documented runner command; the root configured
  gate plus a clean two-wheel smoke pass; release and version ownership is explicit.

- `pri=3` `size=M` — resolver cache or pooled read connection. M3.2b deliberately pays full P1-P6 per
  call. Acceptance: cache identity binds database identity, current operation revision, latest receipt
  sequence and hash, and every state change that can fail a check; first/middle/last corruption never
  returns a cached hit; a concurrent-writer test proves invalidation; 1/1,000/50,000 benchmarks show a
  material cold/warm improvement; cached and uncached results are byte-equal; no long-lived read
  transaction blocks writers.

- `pri=3` `size=M` — explicit quarantine/repair command after a resolver failure. Pure `resolve` only
  reports, so ambiguity and integrity failure no longer quarantine. Acceptance: a separately named
  mutator consumes a displayed failure identity, rechecks under one write lock, changes only
  still-affected artifacts, emits one bounded event, is idempotent on rerun, and leaves an ordinary
  domain miss untouched; a race that moves the state returns conflict with no write.

- `pri=4` `size=M` — caller-lifecycle helper and outbox example. Core owns no request lifecycle after M3.
  Acceptance: an optional example durably binds a caller logical-operation ID to partition, operation
  revision, canonical input, candidate content and source revision; same-ID/different-content fails; an
  at-least-once relay probe demonstrates duplicate proposals after the acknowledgement crash window; the
  docs call this lost-intent protection and never exactly-once submission.

- `pri=4` `size=S` — rename the generic `_request_id` validator and repair entity labels. It reports the
  label `request_id` for `proposal_id` (`system.py:1087,1128,1229`), `artifact_id`
  (`3704,4466,4829,4968`), `example_id` (`4761`), `report_id` (`5006`) and the receipt id. Pre-existing;
  u4c2 pinned it as-is because fixing it meant editing `system.py` outside that unit's CLI write set.
  Lifecycle removal makes the private name more misleading without making the rename spine work.
  Acceptance: one `_entity_id(value, label)` owner validates proposal, artifact, example, report and
  receipt IDs; every caller supplies its own label; exact CLI and library messages name the correct
  entity; existing message pins update in one pass; request-lifecycle vocabulary stays absent; suite
  green.

## M3.1 deferrals

- `pri=3` `size=S` — every map S3 claim needs an explicit KEEP/REWRITE/DELETE row, and the source
  docstrings need falsifiers. M3.1's D8 table covered the human-facing docs it changed and rewrote the
  two source docstrings (`System` class contract, `promote_function`), but S3-001/004/005 KEEP claims and
  map rows S1-009/010/138 carry no per-row disposition, so a neighbouring edit can delete a governing
  supervision claim while the D8 table still reads satisfied. Acceptance: each S3 row carries a
  disposition plus its falsifier, source-docstring rows included, and one check rejects obsolete callback
  ATTRIBUTION rather than merely unclassified tokens.
- `pri=3` `size=S` — the human-facing register audit still runs from no gate, now with a concrete
  consumer. M3.1 ran `.scratch/register/audit.py` by hand over the three changed surfaces (README 161
  sentences >25w=0; threat-model 92 >25w=0; architecture 141 >25w=1, pre-existing), so no clone can
  reproduce the conformance claim. Merges with the existing register-audit port row. Acceptance: the
  tracked tool runs from the configured gate over every changed human-facing surface and reports zero new
  over-length sentences.
- `pri=3` `size=S` — clock and ID allocation now run under `BEGIN IMMEDIATE` in `verify_drafts` and
  `promote_function`, so a caller-supplied `clock_us` that blocks, or that re-enters the same ledger,
  holds the write lock while it runs. Accepted at M3.1 as the price of correct timestamp ordering, but
  pinned by nothing. Acceptance: one probe drives a blocking clock with a second default writer and one
  drives a re-entrant clock through another `System`, each asserting the chosen outcome, and the lock
  duration is recorded beside the ruling.
- `pri=3` `size=M` — preserved invariants P6-P10 rest on the pre-existing grade of the rewritten
  `test_system.py` / `test_cli.py` cases, which the M3.1 diff-blind table (V15/V16/V21-V24, contract
  Part 8) shows is coarser than the invariants claim. P8 in particular was closed by MAIN comparing
  `store.py` bytes to `3a53389` by hand, so no clone reproduces it. Acceptance: a frozen
  `SCHEMA_VERSION` plus a digest over `SCHEMA` bytes replaces the by-hand check; identity columns are
  read back per WRITER rather than per column; every event producer and branch pins its payload keys;
  both the retained and the candidate 1,001-member sentinels are pinned; and invalid-identity probes
  assert zero clock calls and zero ID allocations, not only an unchanged dump.
