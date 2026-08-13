# M2.u4c5a acceptance contract — MAIN

Baseline `7c969dd`, gate green under MAIN's own rerun (`Ran 453 tests in 91.648s / OK`, `uv build` rc 0).
Tier `kernel`. Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`; every other tracked path
stays byte-identical, `.agent/` records aside.

Scope = the first half of `function export`: source selection, the verification gate, and the raw byte
channel to stdout. `--out PATH` is u4c5b and stays a usage error here. Decisions 1, 3 and 4 of
`.agent/decisions/m2u4c5-design.md` bind and are not re-litigated; this record adds the testable
predicates, the exact strings, and the probe corpus. Structural facts are inlined with anchors;
measurements taken outside the committed suite are marked as fixture results and carry no acceptance
weight — a claim that matters is a committed test.

## A — surface

```
cement --db DB --partition P function export OPERATION [--receipt-id ID]
```

- Parser slot: `function_export = function_commands.add_parser("export")` appended after `promote`
  (`cli.py:189-196`) and before the blank line preceding `events` (`cli.py:198`), with the matching
  dispatch leaf appended after `promote`'s in `_run`. Parser order and dispatch order stay identical,
  which is the repo's uniform convention across all 13 top-level groups.
- Positional `operation`; optional `--receipt-id` (no `type=`, no default, so absent ⇒ `None`), same flag
  name and help vocabulary as `function show`.
- No other flag. `--out`, `--expected-function-hash`, `--projection-limit` are argparse usage errors at
  exit 2 here; `--out` becomes legal only when u4c5b lands. Long-option abbreviation stays unpinned
  (`allow_abbrev` inherited), per u4c2.
- REJECTED `--expected-function-hash`: the exported document embeds its own `function_hash` as its sole
  excluded field and self-checks on parse, and `function verify OP --expected-function-hash HEX` already
  binds caller-held identity at exit 6. A second copy of that gate on the byte channel would either
  duplicate `verify` or invent a third negative-verdict shape.

## B — two sources, never mixed, one call each

| flag | library call | verified by |
| --- | --- | --- |
| absent | `System.verify_function(partition, operation)` | the six ordered checks, live, at call time |
| `--receipt-id ID` | `System.reconstruct_function_receipt(partition, ID)` | the reconstruction core's own integrity raises |

- The prospective union is not an export source at any flag value; `inspect_function_promotion` is never
  called here.
- The historical branch runs NO live verification: reconstruction already revalidates the 14-field
  receipt ABI, membership count, ordinal contiguity, ascending `input_hash`, the membership digest, the
  joined artifact/report rows, scope binding, report child sets, recomputed entry seals, the rebuilt hash
  and the normalized self-check — 20 direct `IntegrityError` raises in `_reconstruct_function_receipt`
  (`system.py:2000-2158`) plus 7 more in the `_function_receipt_from_row` scalar helper it calls. Adding
  `verify_function` on top would report the CURRENT set's health while exporting HISTORICAL bytes —
  exactly the mixing Decision 3 forbids.
- The OPERATION is graded by grammar on BOTH sources, before either library call:
  `_name(args.operation, "operation")` (`system.py:145`) runs first, so a malformed operation is a usage
  error at exit 2 whichever flag is present. Without it the historical branch grades the same positional
  by receipt membership alone — the live branch validates through `verify_function` while
  `reconstruct_function_receipt` takes no operation — so an unset `$OP` would report *no receipt for this
  operation* (3) instead of *operation must be …* (2), and `export --receipt-id` would diverge from
  `show --receipt-id`, which validates through `function_report`. Importing the library's own validator is
  what keeps one grammar in one place.
- `verify_function` is called without `expected_function_hash` (no flag exists), so its
  `ValidationError` on a malformed digest is unreachable from `export`.

## C — the live gate: a negative verdict is stderr + exit 6, never bundle bytes

`_run`'s export leaf, live branch:

1. `verification = system.verify_function(args.partition, args.operation)`.
2. `not verification.passed` ⇒ `raise _Unverified(payload)`; `main` emits `payload` to stderr and returns 6.
3. `verification.document is None` ⇒ `raise IntegrityError("function verification passed without an
   exportable document")` ⇒ exit 5.
4. otherwise ⇒ `return _Outcome(raw=verification.document.text)` ⇒ exit 0.

Mechanics, entirely inside the write set:

```python
class _Unverified(Exception):
    """A verification verdict came back negative; carries its finished stderr payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload["message"])
        self.payload = payload
```

- `_Unverified` subclasses `Exception` DIRECTLY. Subclassing `CementError` would put it inside
  `main`'s line-460 `except (ValidationError, CementError)` clause, which precedes any appended branch and
  would silently downgrade every refused export to exit 2. This is a pinned structural property, not a
  stylistic one.
- `main` gains exactly ONE appended `except _Unverified` branch after the existing
  `(ValidationError, CementError)` clause (`cli.py:460-462`) and before `if isinstance(result, _Outcome)`
  (`cli.py:463`): `_emit(exc.payload, stream=sys.stderr); return 6`. `_Outcome`, `_emit`, `main`'s channel
  branch and all five existing exception clauses stay byte-identical.
- No leaf writes a stream itself; all output stays in `main`.

Payload, exactly three keys:

```python
{
    "error": "unverified",
    "message": "function verification failed; no bundle exported: "
               + "; ".join(f"{check.key}: {check.detail}" for check in checks if not check.passed),
    "checks": [asdict(check) for check in verification.checks],
}
```

- `checks` is the FULL ordered vector — every check, passing ones included — identical in shape and
  vocabulary to `function verify`'s stdout `checks`, so one `jq` path serves both.
- `message` names ONLY the failing checks, joined by `"; "`. `passed=False ⇒ at least one failing check`
  holds structurally in both return branches: the normal return computes `passed = all(check.passed ...)`
  (`system.py:3373`) and the aggregate-limit branch returns six explicitly failed checks
  (`system.py:3023-3052`), so the joined tail is never empty and no defensive branch is written for a
  state the library cannot produce.
- `error: "unverified"` is a new token; the token↔exit bijection survives: `invalid`→2, `not_found`→3,
  `conflict`→4, `integrity`→5, `unverified`→6.
- `function_hash` and `entries` are deliberately absent: a failed verification may still carry a
  diagnostic hash (`system.py:3376` returns `function_hash` regardless of `passed`), and an error object
  with a bare hash and no `passed` field invites copying the identity of a set that did not verify. Every
  discriminator, including the entry count inside the aggregate-limit detail, is already in `checks`.
- `_emit` applies `sort_keys=True`, so the stderr object serializes as `checks`, `error`, `message`, and
  each check as `detail`, `key`, `passed`.
- stdout on this path is exactly `b""`. That is the whole reason the verdict is not on stdout: with the
  verdict on stdout, `function export OP > f` at exit 6 leaves `f` holding a kilobyte of verdict JSON
  under the name of a bundle, because the redirect creates and truncates `f` before Cement runs. Pin 6
  below is the committed form of the claim.

## D — the historical branch: reconstruct, then cross-check the operation

```python
_name(args.operation, "operation")
reconstruction = system.reconstruct_function_receipt(args.partition, args.receipt_id)
if reconstruction.receipt.operation != args.operation:
    raise NotFoundError("function receipt does not exist for this operation")
return _Outcome(raw=reconstruction.document.text)
```

- `_name` runs BEFORE reconstruction, so grammar beats lookup on this branch too: an empty or malformed
  operation is exit 2, never a not_found on a receipt that was never consulted. Order also decides the
  pair (malformed operation, unknown receipt id) — exit 2, since grammar precedes both queries.

- The cross-check is MANDATORY: the library's lookup predicates are `WHERE partition = ? AND id = ?`
  (`system.py:2918-2919`) and it takes no operation, so without it a receipt of operation B exports
  successfully under positional operation A: reconstruction returns B's document, whose `scope.operation`
  never mentions A.
- The message REUSES `function_report`'s exact string (`system.py:2621`), so `show` and `export` speak one
  vocabulary for one condition. It is distinct from the library's own
  `"function receipt does not exist in this partition"` (`system.py:2925`), and both exit 3: the CLI
  string means *this receipt exists but belongs to another operation*, the library string means *no such
  receipt row in this partition*.
- ORDER IS RECONSTRUCT-FIRST, and its consequence is contractual: a receipt that belongs to another
  operation AND fails reconstruction exits 5, not 3, because the integrity raise precedes the
  cross-check. The alternative — a cheap row lookup before reconstruction — has no public API
  (`function_receipts` pages by scope and would re-answer a different question), and the CLI invents no
  second query.
- Comparison is exact `!=` on `FunctionReceipt.operation` (`models.py:198`) against the positional
  operation as typed. The library normalizes neither side beyond `_name`'s grammar, so `Echo` and `echo`
  are different operations here, matching every other scope comparison in the repo.
- Historical failure stays exit 5 and the asymmetry with the live branch's exit 6 is deliberate: the live
  set is a current aggregate that legitimately drifts, so its negative is a verdict; a receipt is
  immutable, so a receipt that no longer reconstructs is corruption. `$?` separates them.
- The historical branch issues no `operations` query, so it neither proves nor requires that OPERATION is
  currently registered, and a receipt on a SUPERSEDED operation revision still exports: reconstruction is
  documented and probed status-independent (`system.py:2000`, u3b2), keying members by immutable ID and
  validating against the receipt's own `partition`/`operation`/`operation_revision`/`policy_hash`.

## E — byte exactness on stdout

- `FunctionDocument.text` (`function.py:69`) reaches stdout as `text.encode("utf-8")` through the frozen
  raw channel, with NOTHING appended: no newline, no BOM, no framing.
- The text is `json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"),
  sort_keys=True)` (`json_value.py:106-111`) stored unchanged (`function.py:268`), so it is compact,
  key-sorted, terminator-free, and emits non-ASCII literally: on a `Grüße 日本語` corpus the exported bytes
  carry those code points verbatim and contain zero `\uXXXX` escapes, so the UTF-8 byte count exceeds the
  character count. The committed test pins the escape-freedom and the byte equality, not a length.
- Both stdout hosts are pinned: the buffer-bearing runner (bytes through `sys.stdout.buffer`) and
  `run_cli(..., text_only=True)` (no `.buffer`, characters through `sys.stdout.write`) yield the same
  UTF-8 bytes.
- ROUND TRIP is contractual, because u4c6's `eval` consumes exactly these bytes:
  `parse_function(run.stdout_text)` succeeds and its `function_hash` equals the live/historical hash, and
  `evaluate(parsed, <a promoted input>)` returns that input's promoted output with `matched=True`.
- An operation with nothing promoted exports its real document at exit 0 — `{"abi":"cement-function-v2",
  "canonicalizer":"cement-json-v1","entries":[],"function_hash":"<64hex>","scope":{...}}`. CORRECTION to
  the design record, which calls that document 304 bytes: the length is a fixture property, not a
  constant — the document embeds partition, operation and policy hash, so the count moves with the names
  (`tenant`/`empty` measures 312). Tests pin `entries == []` and byte equality against the library's own
  `document.text`, never a literal length.
- `promote_function`'s refusal to seal an empty union does not transfer: `promote` writes, `export`
  reports.

## F — probe corpus (expected outcomes are contract, not suggestion)

Fixtures reuse the committed helpers: `promoted_operation(op, members)` (register → 2 accepted
confirmations per input → CLI `compile` → library `verify_drafts`/`inspect`/`promote_function`,
`test_cli.py:274-297`), `register`, `confirm`, `receipt_history`.

| invocation | exit | stdout | stderr |
| --- | --- | --- | --- |
| `function export OP`, healthy promoted set | 0 | exact `document.text` bytes | empty |
| `function export OP`, registered, nothing promoted | 0 | `"entries":[]` document, no newline | empty |
| `function export OP` after `artifact suspend` of a member | 6 | `b""` | `{"checks":[6 items],"error":"unverified","message":"…persisted-function-receipt: latest receipt does not bind the promoted snapshot"}` |
| `function export OP`, operation unregistered | 3 | `b""` | `{"error":"not_found","message":"operation is not registered in this partition"}` |
| `function export OP`, operation in another partition | 3 | `b""` | same as above |
| `function export OP --receipt-id <own receipt>` | 0 | exact historical `document.text` bytes | empty |
| `--receipt-id <receipt of another operation>` | 3 | `b""` | `{"error":"not_found","message":"function receipt does not exist for this operation"}` |
| `--receipt-id <unknown well-formed id>` | 3 | `b""` | `{"error":"not_found","message":"function receipt does not exist in this partition"}` |
| `--receipt-id <valid id, wrong partition>` | 3 | `b""` | same as above |
| `--receipt-id not-an-id` | 3 | `b""` | same as above — grammar-valid, so it reaches lookup |
| `--receipt-id ""` / 193-char id | 2 | `b""` | `{"error":"invalid","message":"request_id must be a bounded ASCII identifier"}` |
| `function export ""` / `♥` / `.leading` / 129-char operation | 2 | `b""` | `{"error":"invalid","message":"operation must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'"}` |
| the same operations plus `--receipt-id <any well-formed id>` | 2 | `b""` | same as above — grammar precedes both library calls |
| `--receipt-id <corrupted receipt>` | 5 | `b""` | `{"error":"integrity","message":"function receipt membership digest mismatch"}` |
| live verification injected `passed=True, document=None` | 5 | `b""` | `{"error":"integrity","message":"function verification passed without an exportable document"}` |
| `function export` with no operation | 2 | `b""` | `{"error":"invalid","message":"the following arguments are required: operation"}` |
| `function export OP --out /tmp/x` | 2 | `b""` | `{"error":"invalid","message":"unrecognized arguments: --out /tmp/x"}` |
| `function export OP --expected-function-hash <64hex>` | 2 | `b""` | `{"error":"invalid","message":"unrecognized arguments: --expected-function-hash …"}` |
| missing `--db` / missing `--partition` | 2 | `b""` | `{"error":"invalid",…}` |

Behavioral pins beyond the table:

1. `_Unverified` is not a `CementError`: `issubclass(_Unverified, Exception)` and
   `not issubclass(_Unverified, CementError)`, and an injected negative verdict returns 6 — the shadowing
   regression is otherwise invisible, since a shadowed `_Unverified` would exit 2 with a plausible
   `{"error":"invalid"}` body.
2. Multi-failure message: an injected verdict carrying two failing checks and one passing check puts BOTH
   failures in `message` joined by `"; "`, in check order, and ALL THREE checks in `checks`. The real
   drift fixture pins the six-check vector with one failure.
3. Exit map, symbol-qualified, patched at the LIBRARY boundary
   (`mock.patch.object(System, "verify_function", …)` / `"reconstruct_function_receipt"`), never at
   `cli._run`: `ValidationError`→2, `NotFoundError`→3, `StateError`→4, `IntegrityError`→5, negative
   verdict→6, and for every nonzero code `stdout_bytes == b""`.
4. Source selection is exclusive: with `--receipt-id`, `System.verify_function` is never called (spy
   asserts zero calls); without it, `reconstruct_function_receipt` is never called. The drift fixture
   additionally proves the branches disagree — after a second promotion the older receipt exports its own
   hash while the live export reports the new one, and the test asserts the two differ rather than any
   particular digest.
5. Scope forwarding is exact: partition from `--partition`, operation from the positional, receipt id
   from `--receipt-id`, each passed positionally in library order, with a spy pinning the call arguments.
6. A promoted set drifted by `artifact suspend` exports NOTHING and leaves a shell-redirect target empty
   — the test asserts `stdout_bytes == b""` at exit 6, which is the operator-visible form of that claim.
7. Cross-revision history: after `operation revise`, a receipt from the previous revision still exports
   at exit 0 with unchanged bytes, while the live export reflects the current revision. The fixture must
   VARY the revision, since same-revision receipts cannot kill a current-revision restriction.
8. Foreign + corrupt is exit 5: a corrupted receipt of operation B exported under operation A reports
   `integrity`, pinning the reconstruct-before-cross-check order.
9. Every negative branch keeps stdout byte-empty and every positive branch keeps stderr byte-empty
   (`stderr_text == ""`), so a redirect never mixes channels.
10. Operation grammar is graded identically on both sources: the four rejects above exit 2 with and
    without `--receipt-id`. The adjacent accept side pins the boundary rather than a blanket refusal — a
    128-character operation passes the guard and reaches the receipt comparison, exit 3 with
    `function receipt does not exist for this operation`.
11. The full six-failure capacity vector — the aggregate-limit branch's 50,001-entry verdict, injected —
    reaches stderr complete: six entries in `checks`, all `passed=False`, every detail joined into
    `message` in check order, exit 6, stdout `b""`. The ledger cannot build that state (see H), so the
    injection is the only reachable form of the claim.

## G — invariant surfaces

- `git diff --name-only 7c969dd..<unit commit>` touches exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py`, and `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/`
  stay byte-identical: no library delta, and the leaf forwards to two already-shipped APIs.
- The 26 pre-existing `_run` leaves keep their returns, exit codes and stdout bytes; `main`'s only new
  branch is `except _Unverified`, which no existing leaf can raise.
- No new dependency; imports stay in-package plus stdlib, with `_name` newly imported from `.system`
  beside `System`. `IntegrityError`, `NotFoundError` and `ValidationError` are already imported in
  `cli.py` (lines 15, 16, 18); this leaf carries the first explicit raises of `IntegrityError` and
  `NotFoundError` in this module, which until now raised only `ValidationError` (`cli.py:228-247`).

## H — known limits

- The aggregate-limit vector (>50,000 promoted entries ⇒ all six checks fail with `document=None`) is
  reachable only through the legacy per-artifact `System.promote`, which carries no aggregate guard
  (`system.py:4457-4580` contains zero `FUNCTION_MAX_ENTRIES` references; every site is
  `function.py:142,292`, `system.py:330,3011,3047`). No test builds 50,001 real entries — a ledger
  surrogate would patch the cap rather than fill the ledger — so the library's route into that state stays
  reasoned; pin 11 injects the verdict it produces and pins the CLI's whole handling of it.
- Neither branch claims total error mapping over corrupt ledgers. `_function_receipt_from_row`-class
  stored-scalar conversions still use bare `int(...)` and leak raw `TypeError`/`ValueError`/`OverflowError`
  past `main`, and the historical branch reaches them; the audit stays the tracked `.agent/polish.md`
  item, which already names `reconstruct_function_receipt` among the reachable callers.
- Exit 6 now names three objects across three leaves — failed drafts, a failed committed set, and a
  refused export — one meaning (a verification verdict came back negative), three payload shapes,
  distinguished by command and channel. `$?` alone cannot tell them apart.
- Exit 3 covers three distinct conditions on this leaf (unregistered operation, no such receipt row,
  receipt of another operation), separated only by message; exit 2 covers argparse usage errors and the
  receipt-id grammar alike.
- `--receipt-id` accepts the generic `_request_id` grammar (`[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}`), not an
  `fpr_<32hex>` shape, so a typo that stays inside the grammar is a not_found (3), not an invalid (2):
  `not-an-id` and a well-formed id of the wrong prefix both reach lookup.
- A document up to 64 MiB and up to 50,000 entries is emitted in ONE write to stdout; there is no cursor
  and no paging, by construction — a bundle is meaningless in fragments.

## Gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, rerun by MAIN
from committed state at close.
