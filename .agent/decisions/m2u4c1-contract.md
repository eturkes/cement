# M2.u4c1 acceptance contract — MAIN

Baseline `a717544`, gate green (`Ran 353 tests in 61.271s / OK`, `uv build` exit 0). Tier `kernel`.
Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`. Every other tracked path stays
byte-identical, `.agent/` records aside.

Scope = u4c1's two halves: the `function show` leaf over `function_report`'s current anchor, and the
cross-unit CLI interfaces u4c2–u4c6 inherit (`.agent/decisions/m2u4c-design.md` Decision 3). Facts this
record depends on are inlined; it never defers to a session-local pointer.

## A — `function show` emits the library model directly

RULING: `_emit(system.function_report(partition, operation, projection_limit=...))`. No hand-written
field projection.

- `FunctionReport`'s whole transitive graph is scalars plus bounded tuples; nothing reaches
  `FunctionDocument`, its `text`, or the private `_FunctionCase` cache, so the Decision-3 ban is
  satisfied structurally rather than by field selection.
- Every detail list is `projection_limit`-bounded (`members`, `compile_ready_scopes`,
  `compile_blocked_scopes`, `pending_proposals`, `artifact_statuses[].artifacts`,
  `stale_revision_anomalies`); the only unbounded values are exact integer counts.
- Measured whole-model emit at 300 members + 100 blocked scopes + 100 pending proposals,
  `--projection-limit 10000`: 284,603 stdout bytes in 0.446 s, no document or private-cache token
  anywhere in the payload.
- Precedent is uniform: all 20 existing `_run` leaves emit library return values, and Decision 3 bans
  `_emit` only for document-bearing models.

REJECTED: hand-built projection. Its own exhaustive prototype measured the saving at exactly zero —
285,222 stdout bytes either way over the same 300/100/100 ledger and 1,100 emitted detail records — for
+108 production lines mirroring nine model types, buying only 1.4 ms of avoided deep-copy per call. It
creates a second field list maintained by hand against `models.py`, where a field added to the model but
missed in the projection is invisible to behavioral tests, and it breaks the one-convention rule for a
single leaf. Any narrower field subset is worse still: dropping receipt hashes, build-vs-current evidence
metrics, artifact details or stale reasons erases operator questions the report exists to answer.

MITIGATION, mandatory: the emitted JSON schema is pinned by a golden key-set test — exact depth-1 keys,
exact `operation_now` and `function_anchor` key sets, exact `artifact_statuses` status vocabulary in
order — so later model growth surfaces as a deliberate CLI-schema change instead of a silent one.

## B — `_Outcome`: frozen, slotted, keyword-only modifiers, exactly one output channel

```python
@dataclass(frozen=True, slots=True)
class _Outcome:
    payload: Any = _MISSING
    status: int = field(default=0, kw_only=True)
    raw: str | None = field(default=None, kw_only=True)
```

INVARIANT: exactly one of `payload`/`raw` carries output. Both set, or neither set, raises
`AssertionError` from `__post_init__`, matching the module's existing impossible-state idiom at
`src/cement_runtime/cli.py:333`. The minimal alternative — accept both and let `main` silently prefer
`raw` — is rejected: five later sub-units inherit this seam, and a silent precedence rule is a defect
waiting for the first command that sets both.

`__post_init__` also rejects a non-exact-`int` `status` (`type(status) is not int`, which excludes `bool`),
because a wrong-typed status reaches `SystemExit` and degrades to exit 1 across every later sub-unit. No
range check: exit-code ranges belong to the commands that own each code.

## C — `main` writes exactly one channel

```
result = _run(args, parser)
_Outcome  -> raw is not None: write raw bytes, nothing appended; else _emit(payload); return status
otherwise -> _emit(result); return 0
```

Raw path = `getattr(sys.stdout, "buffer", None)`, `buffer.write(raw.encode("utf-8"))` when present,
`sys.stdout.write(raw)` when absent, mirroring the text-stream accommodation at
`src/cement_runtime/cli.py:156-174`. `_emit`'s trailing newline never reaches the raw channel.

`_emit` itself stays byte-identical (`json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2)`
plus `"\n"`), as does every existing exception mapping: usage 2, not_found 3, conflict/state 4,
integrity 5, validation/residual 2.

## D — parser surface, frozen for u4c2–u4c6

- `function` group is inserted after `report` and before `events` in `_parser`, and at the matching slot
  in `_run`'s dispatch chain: all 12 existing top-level groups appear in identical parser and dispatch
  order, and `events` is the audit tail.
- `function` takes `add_subparsers(dest="function_command", required=True)`, matching the five existing
  nested groups.
- Leaf `show`: positional `operation`; `--projection-limit`, `type=int`, `default=100`, forwarded
  unclamped as the `projection_limit` keyword so the library's own `1..10_000` validation is the sole
  bound.
- `show` returns the report as a bare value; `_Outcome` is reserved for the later leaves that need a
  status or raw bytes. u4c1 adds no other flag, so `--receipt-id` stays a usage error until u4c2.
- Actor-bearing function writes take a required `--actor` when they land, matching root `promote`
  rather than root `verify`'s defaulted actor.

## E — test harness replacement

`run_cli` returns one frozen slotted `_CLIRun` instead of a positional tuple: five channels across six
sub-units make anonymous positions the churn-prone shape, and the raw channel needs bytes that a
JSON-decoding tuple runner cannot express.

- Fields, all named, in this order: `status: int`, `stdout_text: str`, `stdout_bytes: bytes`,
  `stdout_json: object | None`, `stderr_text: str`, `stderr_json: object | None`. Decoding never raises —
  empty or non-JSON text decodes to `None`, and `stderr_text` is what distinguishes empty stderr from
  undecodable stderr, which later units need to prove stderr is exactly empty.
- Capture is buffer-bearing by default: a minimal writer object holding an `io.BytesIO` as `.buffer` and
  encoding text writes into it, so JSON emission and raw `buffer.write` land in one ordered byte stream.
  `io.TextIOWrapper` is rejected for capture — it closes and needs detaching from its underlying buffer,
  which the plain writer avoids.
- `run_cli(*arguments, text_only=False)`: `text_only=True` swaps in a bare `io.StringIO` with no
  `.buffer`, so the raw channel's text-stream fallback is exercised through the same runner rather than
  an ad-hoc redirect.
- The call boundary stays in-process `main([*self.base, *arguments])` with explicit `--db`/`--partition`.
- The three existing tests keep every behavioral assertion; only accessor form changes.

## F — probe corpus (expected outcomes are contract, not suggestion)

| invocation | exit | stdout | stderr |
| --- | --- | --- | --- |
| `function show OP`, receipt present | 0 | report JSON, `function_anchor` object | empty |
| `function show OP`, no receipt yet | 0 | report JSON, `function_anchor: null` | empty |
| `function show OP`, operation unregistered | 3 | empty | `{"error":"not_found",...}` |
| `function show OP`, operation lives in another partition | 3 | empty | `{"error":"not_found",...}` |
| `--projection-limit 0` / `-1` / `10001` | 2 | empty | `{"error":"invalid",...}` |
| `--projection-limit abc` | 2 | empty | `{"error":"invalid",...}` (argparse) |
| missing `--db` / missing `--partition` | 2 | empty | `{"error":"invalid",...}` |
| `function` with no leaf | 2 | empty | `{"error":"invalid",...}` |
| `function show` with no operation | 2 | empty | `{"error":"invalid",...}` |
| `function show OP --receipt-id X` | 2 | empty | `{"error":"invalid",...}` |

Behavioral pins beyond the table:

1. Truncation is visible: with more members/ready/blocked/pending/stale rows than `--projection-limit`,
   every `*_count` exceeds its projected list length, and `member_count` exceeds `len(members)`. A limit
   above the true count projects the count, never padding to the limit.

   Family reachability, established by probe:
   - `compile_ready_scopes` — confirmed inputs meeting policy. Promoted inputs stay ready, so a promoted
     3-member operation plus 2 fresh confirmations reports `compile_ready_scope_count == 5`.
   - `compile_blocked_scopes` — one confirmation reviewed: `reasons == ["support 1 is below required 2"]`.
   - `pending_proposals` — a handled request left unreviewed.
   - `stale_revision_anomalies` — REACHABLE ONLY FROM OUT-OF-BAND LEDGER STATE: `operation revise`
     retires every artifact it strands, so no supported command leaves a draft/verified/promoted artifact
     on a superseded revision. The test bumps `operations.revision` directly, which is exactly the
     corruption class this family exists to report.
   - Projection order is canonical for members (`ordinal`) and artifacts (`sequence DESC`), but
     `pending_proposals` and `stale_revision_anomalies` order by opaque `prop_*`/`art_*` ids. A truncated
     page of either is therefore an arbitrary — though per-ledger stable — subset, and the CLI offers no
     cursor to reach the rest. Tests pin set membership and per-ledger byte stability, never insertion
     order. Paging is `.agent/polish.md` `pri=2`.
2. Forwarding is exact and unclamped: a spy on `System.function_report` records
   `projection_limit == 10000` for `--projection-limit 10000`, and the default records `100`.
3. The scope reaching the library is the operator's: partition from `--partition`, operation from the
   positional, both passed positionally in that order.
4. `_Outcome` protocol: raw bytes exit through a buffer-bearing stdout with no trailing newline; the
   same bytes exit through a text-only stdout; a nonzero status still puts its JSON payload on stdout
   with stderr empty; both-channels and neither-channel construction raise `AssertionError`.
5. Existing-leaf regression: at least one previously-shipped command asserts unchanged exit code and
   unchanged stdout bytes through the new runner.
6. Frozen shape: one `inspect.signature` + `typing.get_type_hints` test over `_Outcome` and `_CLIRun`
   pinning field order, defaults, keyword-only kinds, `frozen`/`slots`, and return annotations.
7. Golden key sets per Decision A, including `artifact_statuses` order
   `draft, verified, promoted, suspended, retired`.

## G — invariant surfaces

- `git diff --name-only a717544..<unit commit>` touches exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py`, and `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/`
  stay byte-identical.
- The 20 pre-existing `_run` leaves keep their bare-value returns, exit codes, and stdout bytes. What is
  PROVED, and the exact wording any claim may use: `git diff` shows every pre-existing leaf body
  unchanged, and `main`'s only new branch is `isinstance(result, _Outcome)`, which no bare-value leaf can
  enter; one leaf (`operation register`) additionally pins exact stdout bytes, and the full suite covers
  9 of the 20 behaviorally. No differential run over all 20 against `a717544` exists, so no claim may
  assert measured byte equality across the whole set.
- `main` gains no catch-all: a corrupt persisted receipt scalar still escapes as a raw
  `TypeError`/`ValueError` (`_function_receipt_from_row` converts with bare `int(...)`), so no test may
  claim total CLI error mapping over corrupt ledgers. That defect is `.agent/polish.md` `pri=2`, outside
  this write set.
- No new dependency; imports stay stdlib plus in-package.

## Gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, rerun by
MAIN from committed state at close.
