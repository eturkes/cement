# M2.u4c4 acceptance contract — MAIN

Baseline `23a1c00`, gate green (`Ran 424 tests in 72.276s / OK`, `uv build` rc 0). Tier `kernel`.
Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`. Every other tracked path stays
byte-identical, `.agent/` records aside.

Scope = the last two mandatory ledger-write commands of `.agent/decisions/m2u4c-design.md` Decision 1:

- `function inspect OPERATION` over `System.inspect_function_promotion` → `FunctionPromotionManifest`
- `function promote OPERATION --expected-function-hash HEX --actor ACTOR` over `System.promote_function`
  → `FunctionSetPromotion`

The pair is one seam: `inspect` is the sole producer of the hash `promote` demands the operator repeat.
Every fact this record depends on is inlined; it cites no session-local path.

## A — `inspect` emits the manifest minus `text` and `document`, with no counts

RULING: payload = exactly four keys.

```
{"operation_revision": int, "function_hash": hex64,
 "entries": [asdict(FunctionPromotionEntry), ...], "skipped": [dict, ...]}
```

`entries` is every prospective member in library order (ascending `input_hash`), each the whole
`FunctionPromotionEntry`: `artifact_id`, `input_hash`, `artifact_hash`, `output_hash`, `entry_seal`,
`disposition` (`retained`|`candidate`), `replaces_artifact_id` (`null` unless the candidate displaces a
retained member). `skipped` is every skipped dict verbatim. No slicing, no limit flag, no count fields.

`text` and `document` are excluded structurally, not by taste: `text` is the canonical manifest embedding
the whole function document (`system.py` `_function_promotion_plan` builds `"function": document.value`)
under a 134,217,728-byte cap, and `asdict(document)` measures 3.999x expansion while exposing the private
`_FunctionCase` cache. `.agent/decisions/m2u4c-design.md` Decision 3 bans both.

Entry projection is `asdict(entry)`, never a hand-written field list — the `m2u4c1-contract.md` section A
ruling, for its reason: a hand-mirrored list is a second field set maintained against `models.py` where an
added field is invisible to behavioral tests. The golden key-set test below is the mitigation.

FORK ARBITRATION. Two prototyped alternatives, each built to green gates in its own worktree, each
self-rejecting:

- FULL (this ruling, minus counts): 499 marginal stdout bytes per entry for a candidate with no
  replacement, measured identically across 10→100 and 100→1,000 entries (5,143 / 50,053 / 499,153 bytes;
  affine fit `153 + 499N`), extrapolating to 24,950,153 bytes = 23.794 MiB at 50,000 entries. Entry width
  is state-dependent, so that figure is a fixture result and NOT the payload maximum: a retained entry
  costs 498 B (24,900,153 at 50,000) and a candidate carrying a non-null `replaces_artifact_id` costs
  533 B (26,650,153 = 25.416 MiB), with `skipped` rows adding independently on top. N=1,000 costs
  1.290763 s wall and 49,984 KiB peak RSS. Production cost +25 `cli.py` lines, 20 implied test methods.
- BOUNDED: same payload plus `entry_count`/`candidate_count`/`retained_count`/`skipped_count` and a
  CLI-owned `--projection-limit` (default 100, validated `1..10_000` CLI-side) slicing both detail lists.
  Production cost +44 lines, 48% of them the bound; ~120-180 bound-specific test lines on top.

FULL's self-rejection rests on three disjunctive conditions: multi-MiB unpaginated output at maximum
contract, duplication of the shipped `function show` leaf, and inability to answer behavior. It is
overruled on all three. The third does not discriminate — BOUNDED cannot answer behavior either, because
Decision 3 bans the document from both, and `export`/`eval` (u4c5/u4c6) are the commands that answer
content. The second is measured as overlap on `operation_revision` plus retained artifact IDs and input
hashes only; per `m2u4c-design.md` Decision 5 the prospective union and the committed snapshot are
different identities that never swap, so coinciding values are not duplicated meaning, and disposition,
replacement, `entry_seal`, `output_hash` and `skipped` have no analogue in `show`. The first is real and
survives as a known limit.

BOUNDED's self-rejection is unconditional, structural, and measured on all three of its own counts:

1. The bound buys no UPSTREAM resource benefit — no planner, materialization or peak-RSS saving. N=1,000
   peak RSS is 49,816 KiB bounded against 49,752 KiB unbounded, 64 KiB in the wrong direction, i.e. noise,
   because `inspect_function_promotion` materializes the whole manifest, document and entry tuple before
   the CLI can slice anything. Both spikes reached this independently; under the council rule that
   convergence decides. The bound DOES cut terminal bytes, by 99.799% at N=50,000 with projection 100
   (24,950,153 → 50,053), and with them serialization, pipe, log-ingestion and downstream parse cost. That
   saving is real and is outweighed here, not absent: it is purchasable at zero capability cost by piping
   FULL's output, whereas the bound's reachability hole and wrong-layer ownership are not purchasable back.
2. A CLI-owned maximum of 10,000 leaves prospective members 10,001..50,000 unreachable through any CLI
   route, on sets the library declares legal. This is the identical reachability defect that self-rejected
   u4b's `minimal` spike, which left 9,900 of 10,000 pending IDs unreachable.
3. It invents a CLI-layer bound exactly where `m2u4c1-contract.md` section D and `m2u4c-design.md`
   Decision 3 freeze the opposite convention — limit-family flags forward unclamped and the library owns
   the bound. Here the library exposes no bound to forward to, so the flag has no owner but the CLI.

Asymmetry decides, as it did on u4c3: BOUNDED's defects are unconditional and hold at every cardinality;
FULL's bite only at the extreme, where the alternative provides no relief anyway.

COUNTS REJECTED, including the losing spike's minimum-honest variant. Under FULL nothing is ever sliced,
so `entry_count == len(entries)` and `skipped_count == len(skipped)` identically. A count field whose
value is always its own list's length is not information; worse, it advertises a truncation semantics this
payload does not have, and a later reader would reasonably infer one. `jq '.entries | length'` is the
whole cost of the alternative.

KNOWN LIMIT, stated rather than mitigated: at the 50,000-entry maximum this command emits tens of MiB of
JSON in one write, with no cursor and no paging — 23.8 MiB of candidates without replacements, 25.4 MiB
when every entry displaces a predecessor, and more again once `skipped` is nonempty. It is smaller than the manifest the library already
materialized in memory to answer the call, and one unit later `function export` writes up to 64 MiB of
document bytes to stdout by design, so it is the group's established shape and not a new hazard class.

## B — `promote` emits its whole model as a bare return

`FunctionSetPromotion` = `receipt_id`, `receipt_hash`, `function_hash`, `operation_revision`,
`member_artifact_ids`, `candidate_artifact_ids`, `retired_artifact_ids`, `promoted_at_us`. Scalars plus
three string tuples; the transitive graph reaches no `FunctionDocument`, so `m2u4c1-contract.md` section A
applies unchanged and `_emit` takes the model directly.

Neither leaf returns `_Outcome`. Both are ordinary success-or-raise commands: `inspect` reports no verdict,
and `promote` either commits or raises. `_Outcome` stays reserved for the verdict leaves (`function verify`,
`function verify-drafts` at exit 6) and for u4c5's raw byte channel. Exit codes come entirely from `main`'s
existing exception map, which neither leaf changes.

The three unbounded string tuples inherit the same known limit as A, and the bound is per payload rather
than per field: one 50,000-ID tuple is ~2.10 MiB, and the three are independently large, since every
member can be a candidate displacing a predecessor. A 50,000/50,000/50,000 projection measures 6,600,379
bytes = 6.295 MiB, which is the figure this contract claims. No relational invariant is asserted here that
would forbid it.

## C — parser surface

Appended to the `function` group after `verify`, in `m2u4c-design.md` Decision 1 table order, with the
matching slot in `_run`'s `function` dispatch chain — parser order equals dispatch order across all 12
existing groups.

- `inspect`: positional `operation`. No other flag. `--projection-limit` and `--receipt-id` are usage
  errors here; `inspect` names exactly one identity, the prospective union.
- `promote`: positional `operation`; `--expected-function-hash` required; `--actor` required, matching
  root `promote` and every actor-bearing function write.
- `--expected-function-hash` is forwarded verbatim as the `expected_function_hash` keyword; the library's
  `_digest` validation is the sole grammar check, so a malformed digest is `ValidationError` → exit 2. The
  CLI never normalizes case, never strips, never pre-validates.
- `--actor` forwards verbatim as `promoted_by`.
- Nested `function promote` never routes to root `promote artifact_id --scope-hash --actor`; the two
  parsers share no option and cannot cross.

## D — the handshake, and what moves the hash

Load-bearing invariant, and the roadmap's own acceptance line for this unit: the hash `inspect` displays
feeds `promote` unchanged, and a prospective change makes a stale hash fail.

- `inspect` → take `function_hash` → `promote --expected-function-hash <it>` → exit 0. Probed end to end
  by both spikes.
- A qualifying ledger change between the two (a newly verified candidate on a new input) moves the
  prospective hash; the stale hash then raises `ConflictError("expected_function_hash does not match the
  locked prospective function")` → exit 4, stdout empty, that exact JSON on stderr.
- A non-qualifying change does NOT move it: adding one confirmation where policy requires two leaves the
  prospective union identical and the hash unchanged. That is a hash invariant only. Whether the repeated
  hash then PROMOTES is a separate predicate — a zero-candidate checkpoint succeeds at exit 0 iff the
  union is nonempty, so the same non-qualifying change over an empty union leaves the hash equally
  unchanged and still exits 4 on the empty-set guard. Probed both ways; a fixture for the exit-0 branch
  must start from at least one retained member.
- `operation revise` between the two does NOT reach `ConflictError`. Revision bump retires every stranded
  artifact, so the prospective union becomes empty and the empty-set guard fires first:
  `StateError("function promotion requires at least one member")` → exit 4. Both branches are exit 4 and
  `$?` cannot separate them; only the message distinguishes them. Pin both.
- Empty prospective union is asymmetric between the pair, deliberately: `inspect` succeeds at exit 0 with
  `entries: []` and the hash of the empty document, while `promote` with that same hash fails at exit 4.
  `inspect` reports state; `promote` refuses to seal nothing.
- Empty union is `entries == []` ALONE, never `entries == [] and skipped == []`. The two lists are
  independent: rows are classified before the union is assembled, so a verified row that fails
  current-build eligibility is skipped while the union it would have joined stays empty. Probed:
  `entries=0, skipped=1` through supported flows. Both shapes belong in the corpus.
- An unverified `draft` is IGNORED, not skipped and not blocking — the planner selects `status='verified'`
  rows only. A ledger holding drafts alone inspects as an empty union.
- `skipped` carries exactly one reason in the current implementation, `superseded-build`, with the exact
  key set `{artifact_id, input_hash, reason}`; two independent probes agree. It is not a general warning
  stream: only a verified row that fails current-build eligibility lands there. Reached by verifying a
  replacement build for an input that already had a verified one.
- Displacement and supersession are the same evidence event landing on two different predecessor states,
  and the distinction is exact: a PROMOTED predecessor plus a newer verified build yields one entry with
  `disposition: candidate` and `replaces_artifact_id` set to the predecessor, while a merely VERIFIED
  predecessor yields a candidate plus the predecessor in `skipped` as `superseded-build`. Probed both ways.
- Reaching either requires new evidence on a scope, and on a PROMOTED scope `handle` cannot supply it:
  it resolves deterministically from the promoted artifact and returns `status: resolved`, never a
  proposal, so `confirm`-style setup raises on its own `review_required` assertion. `challenge OPERATION
  --input I --expected <the resolved output> --reviewer R` is the supported route — agreeing with the
  active output records an example with `suspended: false`, which moves `build_hash` and makes `compile`
  emit exactly one replacement build. This is a fixture recipe, not a code claim; a test that reaches for
  `confirm` on a promoted input fails in setup for a reason unrelated to the leaf under test.

## E — `promote_set` stays library-driven

`tests/test_cli.py`'s `promote_set` helper drives `verify_drafts` + `inspect_function_promotion` +
`promote_function` through the library, carrying a comment that the CLI cannot promote until u4c3/u4c4.
After this unit the CLI can — and the helper still must not switch. It is transitively consumed by exactly
18 test methods pinning `function show`, `function receipts`, historical `show` and `function verify`;
routing their setup through the leaf under test would make an inspect/promote defect fail 18 tests that
pin other leaves, and would make those tests' intent unreadable. The comment is rewritten to state that
reason. u4c4's own tests exercise the CLI path end to end, which is where that coverage belongs.

## F — probe corpus (expected outcomes are contract, not suggestion)

| invocation | exit | stdout | stderr |
| --- | --- | --- | --- |
| `function inspect OP`, 3 candidates | 0 | four-key payload, 3 entries, `skipped: []` | empty |
| `function inspect OP`, retained + candidate displacing one | 0 | mixed `disposition`, non-null `replaces_artifact_id` on the displacer | empty |
| `function inspect OP`, empty union | 0 | `entries: []`, `skipped: []`, hash present | empty |
| `function inspect OP`, drafts only, none verified | 0 | empty union | empty |
| `function inspect OP`, one superseded verified build | 0 | `skipped` = 1 row, keys exactly `{artifact_id,input_hash,reason}` | empty |
| `function inspect OP`, unregistered / other partition | 3 | empty | `{"error":"not_found",...}` |
| `function inspect OP --projection-limit 5` / `--receipt-id X` | 2 | empty | `{"error":"invalid",...}` (argparse) |
| `function promote OP --expected-function-hash <fresh> --actor a` | 0 | whole `FunctionSetPromotion` | empty |
| `function promote OP` after a qualifying change, stale hash | 4 | empty | `{"error":"conflict","message":"expected_function_hash does not match the locked prospective function"}` |
| `function promote OP` after `operation revise`, stale hash | 4 | empty | `{"error":"conflict"...}` carrying the empty-set message |
| `function promote OP`, empty union | 4 | empty | conflict-class JSON, empty-set message |
| `function promote OP --expected-function-hash <non-hex/63/65/uppercase>` | 2 | empty | `{"error":"invalid",...}` |
| `function promote OP` missing `--expected-function-hash` or `--actor` | 2 | empty | `{"error":"invalid",...}` (argparse) |
| `function promote OP`, unregistered / other partition | 3 | empty | `{"error":"not_found",...}` |
| either leaf on a corrupt artifact row | 5 | empty | `{"error":"integrity",...}` |

Behavioral pins beyond the table:

1. Golden key sets: exact depth-1 key set `{operation_revision, function_hash, entries, skipped}`; exact
   entry key set, all seven; exact `FunctionSetPromotion` key set, all eight. No `text`, no `document`, no
   `value`, no `input_hashes`, no `_FunctionCase` token (`artifact_hash`/`input`/`output`/`digest` nesting)
   anywhere in either payload.
2. Cardinality: no slicing at any size. A union larger than any plausible default emits every entry —
   tail sentinel well past 100, asserting `len(entries)` equals the true member count and that the LAST
   entry is present, since a loop-quantified projection weakens at its tail.
3. Forwarding is exact: spies record `inspect_function_promotion(partition, operation)` positionally with
   no keyword, and `promote_function(partition, operation, expected_function_hash=<verbatim>,
   promoted_by=<verbatim>)`. Uppercase and whitespace-padded digests reach the library unmodified and are
   rejected there.
4. Scope isolation uses collision pairs, not hyphens only: `tenant_a` vs `tenantXa` and `echo_1` vs
   `echoX1`, plus a case variant, so an `=` → `LIKE` weakening in any query these leaves reach is visible.
5. The handshake round trip and every branch of D, each pinned separately. The two exit-4 messages are
   asserted by message, not by code alone.
6. Determinism: a repeated `inspect` over an unchanged ledger is byte-identical on stdout.
7. Boundary injection, at the library boundary and never by patching `cli._run` — the u4c3 lesson, where
   patching `_run` replaced the very branch the test claimed to pin. Authority denial alone is genuinely
   unreachable: the CLI constructs `System(args.db, candidate_source=source)` and passes no `authority`
   callback, so no ledger state can produce it. The locked-recheck `StateError` is NOT in that class — it
   is real concurrency behavior of the default-constructed `System`, reachable when a supported write
   (`artifact suspend`) lands in the interval between the authorizing read plan and the write-locked
   re-plan, probed to raise exactly `function promotion candidates changed during authorization`. This
   unit pins `main`'s exit-4 mapping for both by injection and does not add a threaded race to the CLI
   suite; the library already carries the race test, and a CLI-level concurrency probe is registered as
   polish rather than smuggled in as a mock that would prove only the map.
8. Corruption reaches exit 5 for the `artifact_json` recipe specifically — the claim is scoped to that
   mutation and no test may generalize it to totality over corrupt ledgers. Both leaves also traverse
   report and artifact-build stored-scalar conversions (`test_count`, support/reviewer/span) whose bare
   `int(...)` can still leak raw `TypeError`/`ValueError`/`OverflowError` past `main`; that class is the
   tracked `.agent/polish.md` audit, widened by this unit to name the candidate and retained planning
   paths. The recipe: capture `artifacts_build_fields_immutable`
   DDL from `sqlite_master`, drop it, set the target row's `artifact_json` to `{}`, recreate the trigger,
   commit. Leaving the trigger dropped fails the schema fingerprint at exit 5 for the wrong reason, which
   would pass an assertion on the code while proving nothing.
9. Actor grammar is library-owned and separate from argparse requiredness: `_text(promoted_by,
   "promoted_by", maximum=256)` rejects empty and over-256-byte actors at exit 2 while accepting
   whitespace-only, and `_digest` runs first, so a simultaneously bad hash and bad actor reports the hash.
   Pin the adjacent pair at 256/257 and the precedence.
10. Regression: `function verify`'s optional `--expected-function-hash` and `promote`'s required one do not
   leak across leaves in either direction, and root `promote` keeps `--scope-hash` with its exit codes.

## G — invariant surfaces

- `git diff --name-only 23a1c00..<unit commit>` touches exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py`, and `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/`
  stay byte-identical. No library delta: both leaves forward to shipped APIs.
- The 22 pre-existing `_run` leaves keep their returns, exit codes and stdout bytes; `_emit`, `_Outcome`,
  `main`'s channel branch and every exception mapping stay byte-identical.
- `main` gains no catch-all. `_function_receipt_from_row`-class stored-scalar leaks are outside this write
  set and remain a tracked `.agent/polish.md` item; no test may claim total CLI error mapping over corrupt
  ledgers. Neither of these two leaves reads a receipt row, so neither is a new instance of that class.
- No new dependency; imports stay stdlib plus in-package.

## Gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, rerun by MAIN
from committed state at close.
