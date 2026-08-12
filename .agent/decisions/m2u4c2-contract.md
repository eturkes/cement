# M2.u4c2 acceptance contract — MAIN

Baseline `376373e`, gate green under MAIN's own run (`Ran 380 tests in 65.525s / OK`, `uv build` rc=0).
Tier `kernel`. Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`. Every other tracked path
stays byte-identical, `.agent/` records aside.

Scope = two operator routes over already-shipped library APIs, no library delta:
`function receipts OPERATION [--operation-revision N] [--before-sequence N] [--limit N]` over
`System.function_receipts`, and `function show OPERATION --receipt-id ID` historical mode over
`System.function_report`'s function anchor. Facts this record depends on are inlined; it defers to no
session-local pointer.

## Decision 1 — no material design fork ⇒ no spike wave

Three candidate forks, all ruled from committed precedent alone.

1. **Payload shape.** u4c1 contract §A froze *emit the library model directly*. `FunctionReceiptPage`'s
   whole transitive graph = `receipts: tuple[FunctionReceipt, ...]` + `next_before_sequence: int | None`,
   and `FunctionReceipt` is 16 scalar fields (`models.py:194-218`). Nothing reaches `FunctionDocument`,
   `text`, or a private `_FunctionCase` cache, so u4c design Decision 3's document ban is satisfied
   structurally rather than by field selection. Not a fork.
2. **`receipts` vs the repo's `<group> list` enumeration convention** (`proposal list` `cli.py:94`,
   `example list` `cli.py:132`, `artifact list` `cli.py:143`, `report list` `cli.py:166`). RULED: keep
   `function receipts`, as roadmap and u4c design Decision 1 froze it. The `function` group's leaves are
   verbs over ONE function set (`show`, `verify-drafts`, `verify`, `inspect`, `promote`, `export`,
   `eval`); `list` would name the wrong noun, since no list of functions exists, and a third nesting
   level (`function receipt list`) for a single leaf costs more than the divergence. Divergence recorded,
   not silent.
3. **`--receipt-id` as a flag on `show` vs its own leaf.** Frozen by the roadmap line and by u4c design
   Decision 1, which omits `reconstruct_function_receipt` as a verb precisely because historical `show`
   plus historical `export` already reach it.

⇒ Wave 1 = `map-m2u4c2` alone; no `spike-` dispatch.

## Decision 2 — `function receipts` parser + dispatch

```python
function_receipts = function_commands.add_parser("receipts")
function_receipts.add_argument("operation")
function_receipts.add_argument("--operation-revision", type=int)
function_receipts.add_argument("--before-sequence", type=int)
function_receipts.add_argument("--limit", type=int, default=100)
```

- `--operation-revision` / `--before-sequence` carry NO argparse default ⇒ argparse supplies `None` and
  the library's own `None` = *no predicate* sentinel is reached unaltered. Precedent for the
  `None`-defaulted optional flag: `handle --request-id` (`cli.py:82`), `report list --artifact-id`
  (`cli.py:167`). This unit is first to pair it with `type=int` — the natural extension, adding no new
  convention.
- `--limit` default `100` = the library default (`system.py:2254`) and the `report list` / `proposal
  list` precedent. The `1_000` default at `example list` / `artifact list` mirrors those APIs' own
  library defaults, so matching the library default is the invariant convention in both cases.
- Unclamped forwarding (u4c design Decision 3): CLI never clamps, never substitutes its own bound.
  `1..10_000` stays `_bounded_int`'s, raised as `ValidationError` → exit 2.
- Leaf order = `show` then `receipts` in both `_parser` and the `_run` dispatch chain, matching landing
  order; `function` itself stays between `report` and `events` (u4c1 pin `test_cli.py:705`).

Dispatch returns the bare `FunctionReceiptPage` — no `_Outcome`, matching `show` and the 20 pre-existing
leaves. `_emit`'s `asdict` yields `{"next_before_sequence": int|null, "receipts": [...]}`, each receipt
the 16 scalar fields.

## Decision 3 — `function show --receipt-id`

`function_show.add_argument("--receipt-id")` (str, argparse default `None`), declared BEFORE
`--projection-limit` so the parser mirrors the library keyword order (`receipt_id`, then
`projection_limit`, `system.py:2549-2556`). Dispatch forwards `receipt_id=args.receipt_id`
unconditionally, `None` included.

Unconditional keyword rather than a conditionally-built kwargs dict: the library default IS `None`, so
the unconditional form is behaviourally identical, and the conditional form exists in `_run` only at
`proposal review` (`cli.py:255-262`), where the `_MISSING` sentinel is forced because `None` is itself a
legal `corrected_output` JSON value. `receipt_id` has no such collision.

## Decision 4 — three identities never swap (u4c design Decision 5, applied)

| command | identity named | call |
| --- | --- | --- |
| `function show OP` | current committed snapshot — latest receipt of the CURRENT revision, plus live operation-now | `function_report(p, op, receipt_id=None, projection_limit=L)` |
| `function show OP --receipt-id ID` | ONE immutable historical receipt, ANY revision, plus live operation-now | `function_report(p, op, receipt_id=ID, projection_limit=L)` |
| `function receipts OP` | the enumeration of immutable historical receipts, all revisions unless filtered | `function_receipts(p, op, ...)` |

Neither leaf names the prospective union — `inspect` / `promote` (u4c4) own it. Neither reconstructs:
`reconstruct_function_receipt` stays the sole reconstruction surface (u3b2 freeze). Historical `show`
therefore proves row-level receipt self-binding plus validity of the members it returns, never that the
whole membership reconstructs — tests must not overclaim it.

Historical `show` still carries a LIVE `operation_now`: the function anchor is frozen at the receipt, the
operation half is current. u4b's structural naming split (`build_*` frozen / `active_*` current) is what
keeps that readable; the CLI adds no subtraction, ratio or complement across the two anchors.

## Decision 5 — exit codes + validation order

Inlined validator vocabulary (`system.py:145-176`), because the probe corpus pins exact messages:

- `_name(value, label)` → `ValidationError(f"{label} must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'")`; regex `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z`.
- `_request_id(value)` → `ValidationError("request_id must be a bounded ASCII identifier")`; regex `[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}\Z`.
- `_bounded_int(value, label, *, minimum, maximum)` → `ValidationError(f"{label} must be an integer between {minimum} and {maximum}")`; `type(value) is not int` rejects `bool`.

Validation ORDER decides which message wins when two arguments are bad at once:

- `function_report`: `partition` → `operation` → `receipt_id` → `projection_limit`. So
  `--receipt-id <bad> --projection-limit 0` reports the receipt id, NOT the limit.
- `function_receipts`: `partition` → `operation` → `operation_revision` → `before_sequence` → `limit`.
  So `--operation-revision 0 --limit 0` reports `operation_revision`.

ACCEPTED, not a u4c2 regression: `_request_id` reports the label `request_id` for every id it validates —
`proposal_id` (`system.py:1087,1128,1229`), `artifact_id` (`3704,4466,4829,4968`), `example_id` (`4761`),
`report_id` (`5006`) — so `--receipt-id` inherits a pre-existing repo-wide vocabulary leak consistently.
Fixing it means either editing `system.py` (outside the write set) or duplicating library validation in
the CLI, which is the same violation class as clamping. Pin the message as-is; → `.agent/polish.md`.

Exit map (`cli.py` `main`, unchanged): usage/`ValidationError`/`CementError` → 2, `NotFoundError` → 3,
`Conflict`/`State` → 4, `IntegrityError` → 5. Anchored by symbol, not line span: this unit shifts
`main`'s line numbers, so a range recorded here would be stale the moment the unit lands.

## Decision 6 — the unknown-operation divergence is deliberate and must be pinned

`function_report` opens with an `operations` lookup and raises `NotFoundError` when the row is absent
(`system.py:2571-2575`) → exit 3. `function_receipts` performs NO `operations` lookup at all: its
predicates are `partition = ? AND operation = ?` against `function_receipts` alone
(`system.py:2280-2300`) → an operation with no matching receipt row yields an empty page at exit 0,
whether or not it is registered, so an unregistered operation is indistinguishable from a registered one
holding zero receipts.

Stated precisely, because the loose form is false: the leaf reports the RECEIPT table, not operation
existence. `function_receipts` carries no foreign key to `operations` (`store.py:205-223`), so an
out-of-band orphan receipt written under a scope whose operation row is absent IS enumerated. Accepted:
the receipt ledger stays authoritative after operation-row loss, matching the u3b1/u4b posture that
`PRAGMA foreign_keys = ON` makes such states unreachable through any ordinary API. The claim this unit
may make is *no matching receipt row*, never *no such operation*.

RULED: the CLI does not normalize this. u4a chose the convention deliberately (roadmap u4a: *enumeration
returns an empty page for an unknown operation while only the current-revision lookup raises
`NotFoundError`*), and adding a CLI-side existence probe would (a) invent semantics the library does not
have, (b) add a second query and a second snapshot to a one-transaction read. Pinned as a deliberate
divergence in both directions, so a later unit cannot "fix" it silently.

## Decision 7 — committed-test impact set = exactly three

u4c2 is the first sub-unit to invalidate u4c1 pins. Each change is a scope transition, not a weakening:

1. `test_function_show_forwards_scope_and_limit_unclamped` (`test_cli.py:602`) asserts
   `spy.call_args.kwargs == {"projection_limit": expected}`. Now `{"receipt_id": None,
   "projection_limit": expected}`, and the case table gains `--receipt-id` forwarding rows.
2. `test_function_group_rejects_missing_and_future_arguments` (`test_cli.py:684`) asserts
   `("function", "show", "echo", "--receipt-id", "fpr_1")` → exit 2. `fpr_1` matches `_REQUEST_ID`, so
   post-landing that argv reaches the library and exits 3 on the unregistered `echo`. Drop the row,
   rename the test to its surviving obligation, and re-home the exit-3 behaviour in the receipt-id probe
   set.
3. `test_unknown_function_leaf_is_fatal_rather_than_silent` (`test_cli.py:851`) hand-builds
   `Namespace(function_command="receipts")` as a not-yet-dispatched sentinel. `receipts` ships here, so
   the sentinel moves to a name no u4c sub-unit will ever claim (`show`, `receipts`, `verify-drafts`,
   `verify`, `inspect`, `promote`, `export`, `eval` are all reserved). The guarantee — a parser leaf
   missed in dispatch must raise, never emit `null` — is unchanged.

No other committed test may change. Any further diff in `tests/test_cli.py` outside these three plus new
additions is a contract breach.

## Decision 8 — probe corpus (expected outcomes, contract not suggestion)

Fixtures reuse u4c1's helpers: `promoted_operation(op, members) -> receipt_id` (`test_cli.py:252`) and
`promote_set(op) -> receipt_id` (`test_cli.py:237`), which drive `verify_drafts` /
`inspect_function_promotion` / `promote_function` in-process because no CLI route exists before u4c3/u4c4.
Repeated `promote_set` on an unchanged set is legal (u3b1: a zero-candidate checkpoint over a nonempty
retained set stays legal), so N receipts cost N calls and no new confirmations.

| invocation | exit | stdout | stderr |
| --- | --- | --- | --- |
| `function receipts OP`, 3 receipts | 0 | 3 rows `sequence DESC`, `next_before_sequence: null` | empty |
| `function receipts OP`, registered, 0 receipts | 0 | `{"next_before_sequence": null, "receipts": []}` | empty |
| `function receipts OP`, operation UNREGISTERED | 0 | same empty page | empty |
| `function receipts OP`, operation lives in another partition | 0 | same empty page | empty |
| `function receipts OP --limit 2` over 3 | 0 | 2 rows, `next_before_sequence` = 2nd row's `sequence` | empty |
| `function receipts OP --limit N` over exactly N | 0 | N rows AND `next_before_sequence: null` — full yet terminal | empty |
| … then `--before-sequence <that>` | 0 | the 3rd row, `next_before_sequence: null` | empty |
| `--limit 0` / `-1` / `10001` | 2 | empty | `invalid`, message contains `limit` |
| `--limit abc` / `0x10` / `1e2` / `` | 2 | empty | `invalid`, `invalid int value` (argparse) |
| `--operation-revision 0` / `-1` | 2 | empty | `invalid`, contains `operation_revision` |
| `--before-sequence -1` | 2 | empty | `invalid`, contains `before_sequence` |
| `--before-sequence 0` | 0 | empty page — `sequence < 0` matches nothing, and `0` is a legal bound | empty |
| `--operation-revision <old>` after `operation revise` | 0 | that revision's receipts only | empty |
| `--operation-revision <current>` with no receipt yet | 0 | empty page | empty |
| `--operation-revision 0 --limit 0` | 2 | empty | message names `operation_revision` (order pin) |
| `function receipts` (no operation) | 2 | empty | `required: operation` |
| `function show OP --receipt-id <current>` | 0 | `function_anchor.receipt.id == ID` | empty |
| `function show OP --receipt-id <older>` after a newer promotion | 0 | anchor pinned to the OLDER receipt, differing from bare `show` | empty |
| `function show OP --receipt-id <well-formed, absent>` | 3 | empty | `not_found` |
| `function show OP --receipt-id <malformed>` (``, `.lead`, `a b`, 193 chars, non-ASCII) | 2 | empty | `invalid`, `request_id must be a bounded ASCII identifier` |
| `function show OP --receipt-id=-lead` (equals form) | 2 | empty | same library message — `=` forces the leading-`-` value past argparse |
| `function show OP --receipt-id -lead` (separated) | 2 | empty | `invalid`, argparse's own `expected one argument`; text is argparse-owned and NOT pinned |
| `function show OTHER_OP --receipt-id <id of OP>` | 3 | empty | `not_found` |
| `function show OP --receipt-id <id>` from the wrong partition | 3 | empty | `not_found` |
| `function show OP --receipt-id <bad> --projection-limit 0` | 2 | empty | receipt-id message, NOT `projection_limit` (order pin) |

## Decision 9 — behavioral pins

1. **Cursor round-trip is end-to-end.** Page a ≥3-receipt ledger at `--limit 1` until
   `next_before_sequence` is `null`; assert the concatenation equals the full descending set exactly —
   no duplicate, no gap, no re-visit — and that the terminal page carries `null`. A cursor that is
   inclusive rather than exclusive re-emits its own boundary row and this pin fails.
2. **Truncation is visible without a `has_more` field.** Terminality is EXACTLY
   `next_before_sequence is None`. A short page (`len(receipts) < limit`) is sufficient but NOT
   necessary: `system.py:2294-2308` fetches `limit + 1` and sets the cursor only when the extra row
   exists, so a page of exactly `limit` rows with nothing behind it is full AND terminal. MAIN-probed:
   2 receipts at `--limit 2` → `len 2`, cursor `null`; at `--limit 1` → `len 1`, cursor `2`. Pin the
   exact-limit boundary separately from the short-page one, and never derive terminality from length.
3. **Unclamped forwarding, both leaves.** Spy on `System.function_receipts` / `System.function_report`;
   assert exact kwargs including `10001`, `+1`, ` 1 `, `1_0` spellings reaching the library as `int()`
   produced them, and `None` for unsupplied `--operation-revision` / `--before-sequence` / `--receipt-id`.
4. **Scope is the library's, not the operator's.** `--partition` → partition, positional → operation, in
   that positional order; exact `=` matching, so `_` never behaves as a `LIKE` wildcard and case never
   folds. Both leaves need their own colliders (`echoX1` / `Echo_1` vs `echo_1`), since they query
   different tables.
5. **Revision filtering isolates.** Receipts of revision N are absent from an `--operation-revision M`
   page and present in the unfiltered one.
6. **Anchor divergence is observable.** With ≥2 receipts, bare `show` and `show --receipt-id <older>`
   return DIFFERENT `function_anchor.receipt.id` while returning the SAME `operation_now.operation_revision`
   — the frozen/live split of Decision 4, and the pin that fails if `receipt_id` is dropped in dispatch.
7. **`--projection-limit` still bounds members in historical mode**: `member_count > len(members)`.
8. **Bare-value return.** `_run` returns the library value itself for both leaves; `assertNotIsInstance(result, _Outcome)`.
9. **Golden key sets.** `FunctionReceiptPage` = `{next_before_sequence, receipts}`; each receipt = the 16
   keys already frozen at `test_cli.py:_RECEIPT_KEYS`. Reuse that constant rather than restating it.
10. **Existing-leaf regression.** At least one previously-shipped command keeps identical exit + stdout
    bytes.

## Decision 10 — deliberately unpinned

Long-option ABBREVIATION (`--lim`, `--receipt`, `--projection-lim`). `allow_abbrev` sits at argparse's
default across all 12 existing groups, so prefix matching is inherited behavior, not u4c2 vocabulary.
Pinning acceptance would freeze a prefix space that u4c3-u4c6 may legally make ambiguous by adding a
single flag — `--limit-…` alone would kill `--lim` — turning a future sub-unit's legal addition into a
red gate. No test asserts abbreviation in either direction.

Boundary maxima, now authoritative for every probe (`system.py` `function_receipts`):
`operation_revision` `minimum=1, maximum=2**63 - 1`; `before_sequence` `minimum=0, maximum=2**63 - 1`;
`limit` `minimum=1, maximum=10_000`. Each maximum is pinned as an adjacent accept/reject PAIR — a lone
rejection pins nothing about where the boundary sits.

## Invariant surfaces

- `git diff --name-only 376373e..<unit commit>` = exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py`, `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/`
  stay byte-identical. No new dependency; imports stay stdlib plus in-package.
- `_Outcome`, `_CLIRun`, `_emit`, `main`'s channel branch, and the `report,function,events` group order
  stay byte-identical — u4c1 froze them for five sub-units.

## Known limits (must not be overclaimed)

- Row-level self-binding only; no membership reconstruction on either leaf.
- `_function_receipt_from_row` converts receipt integers with bare `int(...)` (`system.py:320-325`), so
  a corrupt persisted scalar leaks a raw conversion exception — `TypeError`, `ValueError` OR
  `OverflowError`, the last reachable via `int(float('inf'))` — past `main`'s `CementError` mapping, and
  numeric text (`'1'`) is accepted where an exact stored int is required. All three are named because
  `.agent/polish.md:35-40` already carries the standing three-exception conversion rule; naming only two
  here would contradict the tracked item. Reachable from both leaves. `system.py` is outside the write
  set and `main` has no catch-all by design ⇒ no u4c2 test may claim CLI totality over corrupt ledgers.
- `function receipts` cannot distinguish an unregistered operation from a registered one with zero
  receipts (Decision 6).
- Pagination is NOT snapshot-consistent across pages. Each call opens its own read transaction
  (`system.py:2293`) and the cursor is `sequence < boundary`, so a receipt promoted mid-traversal is
  never seen by the walk in progress: continuation is stable for rows OLDER than the boundary, and
  nothing more. Decision 9.1's round-trip pin is valid over a static ledger and must not be read as a
  cross-page snapshot guarantee; reaching newer rows requires a fresh traversal.

## Gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from repo root, rerun by MAIN
against committed state at close.
