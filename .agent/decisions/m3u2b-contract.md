# M3.2b acceptance contract - pure `resolve` over one verified snapshot

Unit M3.2b, tier `kernel`, tags `oracle`, depends M3.2a (DONE). Every downstream artifact -
diff-blind battery, oracle, differential, mutation catalogue, review - decides against this file.

Sections 1-10 are settled and binding. Sections 11-13 fill from wave evidence and are marked
`PENDING` until they do; a `PENDING` section is not a licence to implement against a guess.

## 1. Scope

ADDS: `System.resolve(...) -> FunctionResolution` = one full six-check `verify_function` snapshot,
then M2's pure `evaluate` over the document that snapshot reconstructed. One public model,
`FunctionResolution`, pairing the existing `FunctionVerification` with `FunctionMatch | None`.

SETTLED UPSTREAM, never re-litigated here:

- The enforced-read capability is M3.2a's and ships already: `Store.transaction(write=False)` =
  Store-owned rolled-back transaction + deny-by-default authorizer + percent-encoded existing-only
  `file:` URI `mode=ro`, classified by `sqlite_errorcode` alone
  (`.agent/decisions/m3u2a-contract.md`). M3.2b consumes it and adds no mechanism to it.
- Verification scope = the full current six checks, never a narrower private projection and never a
  reconstructed historical receipt (plan draft D5). `resolve` answers CURRENT ledger state.

OUT OF SCOPE, owned elsewhere:

- CLI channel, exit classes, payload shape → M3.5a.
- Proposal submission on a miss → M3.3. A miss here is INERT: it invokes nothing and writes nothing.
- README / `docs/` prose rewrites → M3.9a. Section 9 states M3.2b's narrower obligation.
- Caching, pooled read connections, resolver-triggered quarantine/repair → `.agent/polish.md`
  rows 2 and 3, explicitly deferred. M3.2b ships NO cache.

## 2. Frozen public shape

```python
def resolve(
    self,
    partition: str,
    operation: str,
    input_value: object,
    *,
    expected_function_hash: str | None = None,
) -> FunctionResolution: ...
```

```python
@dataclass(frozen=True, slots=True)
class FunctionResolution:
    verification: FunctionVerification
    match: FunctionMatch | None
```

DECORATOR - RULED to the models-layer convention, deliberately, because the two layers disagree.
`models.py` `FunctionCheck:328` and `FunctionVerification:337` are `frozen=True, slots=True` with NO
`kw_only`; `function.py` `FunctionMatch:75` and `FunctionDocument:57` are `kw_only=True`.
`FunctionResolution` lives in `models.py` beside the model it wraps, so it takes that file's form.
Two fields of unrelated types make positional construction unambiguous, and the keyword marker is
pinned either way by the `inspect.signature` ABI test - which is the only thing that makes the
choice safe to make on consistency grounds.

- `input_value` is positional, matching `handle`'s `(partition, operation, input_value)` order.
- `expected_function_hash` is keyword-only and passes through to `verify_function` unchanged. It is
  FORCED, not convenience: without it a caller wanting identity pinning plus a lookup must call
  `verify_function` and then evaluate separately, which is two snapshots - the exact defect this
  unit exists to remove.
- EXACTLY two fields on `FunctionResolution`. No `input_hash`, no flattened `output`, no `matched`
  mirror, no `checks` copy. Every candidate field faces the mutation criterion: ship it only with a
  committed probe that fails when the field's population logic alone is deleted. A convenience
  mirror of `verification.passed` cannot meet that bar and duplicates the check vocabulary D5
  forbids duplicating.
- Export in `src/cement_runtime/__init__.py`: `FunctionResolution` joins the `models` import block
  and `__all__` in alphabetical position, between `FunctionReport` and `FunctionSetPromotion`.
- `inspect.signature` + `typing.get_type_hints` pin both shapes, per the frozen-ABI rule: keyword
  markers, field set, defaults and return annotation are invisible to behavioural tests.

NAMING - RULED, with a transient overlap. Two `resolve` vocabularies are alive between M3.2b and
M3.6a: the request lifecycle's `Resolved` outcome (`models.py:69`, `status: Literal["resolved"]`)
and this unit's `resolve`/`FunctionResolution`. The name stays `resolve`, because the plan's track
order deletes `Resolved` at M3.6a and the CLI leaf at M3.5a is already specified as root `resolve`;
renaming now would pay a rename twice. The overlap carries one testable obligation: the two never
cross-wire. `resolve` constructs no `Resolved` and `handle` constructs no `FunctionResolution`, and
a probe asserts each returned type exactly rather than by duck-typed field access.

## 3. The three states - the unit's headline predicates

`resolve` returns exactly one of three shapes, and the three stay mutually distinguishable by
`verification.passed` and `match` alone.

| state | `verification.passed` | `match` | `verification.document` | evaluate called |
|---|---|---|---|---|
| unverified | `False` | `None` | `None` | no |
| verified miss | `True` | `FunctionMatch(matched=False, output=None, artifact_hash=None)` | the document | yes |
| verified hit | `True` | `FunctionMatch(matched=True, output=..., artifact_hash=...)` | the document | yes |

The six checks, in emitted order, are `verify_function`'s and are neither renamed nor re-scored
here: `duplicate-input-digests`, `abi-canonicalizer-uniform`, `sealed-passing-reports`,
`current-promotion-receipts`, `function-hash-matches-snapshot`, `persisted-function-receipt`.

CAPACITY IS A FAILED VERDICT, NOT AN ERROR. `FUNCTION_MAX_ENTRIES` is 50,000
(`function.py:27`). A promoted set above it returns early at `system.py:3037` with `passed=False`,
`entries` set to the real count, `document=None`, `function_hash=None` and all six checks FALSE,
without enumerating a single row. `resolve` therefore answers `match=None` for an over-capacity
scope. This is the unverified state, not a miss and not an exception, and the battery pins the
adjacent pair: exactly 50,000 entries verifies, 50,001 does not.

- A failed verdict is NOT a miss. An unverified function has no answer at all; a verified miss is a
  proven absence within a function that verified. Any consumer collapsing the two is a defect.
- `match is None` iff `passed is False`. Both directions are pinned; the biconditional is asserted
  here deliberately because MAIN-authored contracts have repeatedly claimed one where the code
  implements the other.
- Evaluation NEVER runs on a failed verdict. `verification.document is None` when `passed is False`,
  so an implementation that evaluated anyway would raise rather than answer; the pin is a spy on
  `evaluate` asserting zero calls, not an assertion about the returned value.
- `passed is True` with a zero-entry promoted set is a verified miss for every input, not an error.

## 4. Argument validation precedence - RULED

`resolve` validates in this exact order, and ALL of it precedes any ledger read:

1. `partition` → `_name`
2. `operation` → `_name`
3. `expected_function_hash` → 64-hex shape check
4. `input_value` → `canonicalize(input_value)` (`DEFAULT_MAX_BYTES` 1,048,576, default depth/item
   caps; `ValidationError` on violation)

Then the ledger read, then evaluation.

Rationale: a caller's malformed input is rejected identically whether or not the function verifies,
and a bad input never buys a full six-check pass over a 50,000-entry set. `_name` is a pure
validator returning its argument unchanged (`system.py:143-148`), so `verify_function` re-running
steps 1-3 internally is idempotent and keeps that method independently safe as a public entry point.

Precedence is a CONTRACT, not an accident: a call with two invalid arguments reports the earlier one
in this list. Behavioural tests firing one failure at a time cannot see a reordering, so the battery
carries explicit multi-invalid pairs (bad partition + bad input; bad operation + bad expected hash).

## 5. Purity obligations - each pinned independently

No `resolve` path may: write any row, commit, allocate an ID, read the clock, emit an event,
suspend, quarantine, revoke, invoke a `CandidateSource`, create a file, or leave a transaction open.

Pins, one per obligation, never one composite assertion:

- Ledger bytes: sha256 of the ledger file AND full `connection.iterdump()` text are byte-identical
  across a hit, a miss and a failed verdict. Row-count snapshots are insufficient - an injected
  `UPDATE` passes them.
- Clock: a `System` whose `_now` raises resolves all three states unchanged.
- Events: `events()` is byte-identical before and after; the event sequence counter is unchanged.
- No file creation: `resolve` against a deleted ledger raises and leaves the path absent afterwards.
- Source: a `System` built with a source whose `propose` raises resolves a miss without calling it.

## 6. Snapshot obligations

- EXACTLY ONE `store.transaction(write=False)` opens per `resolve` call. Pinned by a `wraps=` spy on
  `Store.transaction` asserting one call with `write=False`, never by a read-only assertion alone:
  read-only proof and single-snapshot lifetime are separate guarantees.
- `connection.in_transaction` stays `True` across the whole six-check pass. A mid-method `commit()`
  splits one snapshot into two while every read-only assertion still holds.
- Evaluation runs over the DOCUMENT VALUE. The document is a self-contained reconstruction, so
  evaluating it after the snapshot ends returns the same answer as evaluating it inside; the battery
  proves that equality rather than assuming it.
- NO cross-call consistency claim. Two consecutive `resolve` calls are two snapshots, and a writer
  committing between them legitimately changes the second answer. Prose must never call `resolve`
  repeatable across calls.

## 7. Error classification

Raising and returning-a-failed-verdict are different outcomes and the line between them is
inherited from `verify_function`, not invented here.

| condition | outcome |
|---|---|
| invalid partition / operation / expected-hash shape / uncanonicalizable input | `ValidationError` |
| operation not registered in the partition (`system.py:2958`) | `NotFoundError` |
| missing or unreadable ledger file | `IntegrityError` (M3.2a mapping, no file created) |
| malformed stored operation scalar - revision, policy hash, policy JSON (`system.py:2960-2967`) | `IntegrityError` |
| promoted-set count disagrees with the enumerated rows under one snapshot (`system.py:3051`) | `IntegrityError` |
| suspended member, revocation, revision drift, absent current receipt, wrong expected hash, over-capacity set | failed verdict, `passed=False` |
| structurally corrupt bound content - ABI, report binding, digest, projection (`system.py:3098-3319`) | failed verdict, `passed=False` |

The last row is inherited, not chosen: those `IntegrityError` raises are LOCAL and every one is
caught by its own check's `(IntegrityError, ValidationError)` handler, which converts the defect into
a FALSE check with bounded detail. Only the five conditions above them escape `verify_function`.
`resolve` re-maps none of it and adds no exception class of its own.

This SUPERSEDES the plan draft's D5 sentence "structural corruption may still raise
`IntegrityError`", which is true only of the five escaping conditions above. Corrupt artifact,
report or projection content produces a FALSE check with bounded detail, verified by MAIN against
the six local catch sites at `system.py:2973, 3111, 3138, 3145, 3170, 3322`.

- Ordinary supported state changes produce a FAILED VERDICT, never an exception: `artifact suspend`
  alone drives the check vector to `passed=False`, and naming that corruption is untruthful.
- `resolve` adds NO new exception class and re-maps nothing. Section 11's verdict table fixes the
  exact class and message for every probe where the two branches could diverge.

## 8. Cost publication - a durable, binding obligation

M3.2b deliberately pays the whole promoted-set verification on every call. That is honest only if
its price is published and rerunnable.

- The unit ships `.agent/decisions/m3u2b-benchmark.py` (`N REPEATS`, rerunnable from committed
  state) and `.agent/decisions/m3u2b-bench.json`, graded by
  `uv run python .agent/decisions/m3u2b-validate.py .agent/decisions/m3u2b-bench.json`.

MEASURED at `019d040`, 3 repetitions, fixture built through public `System` methods in a separate
process, each cold sample a fresh process and a fresh `System`. The OS page cache was NOT dropped,
so cold means process-cold, never disk-cold.

Environment: Python 3.13.14, SQLite 3.53.1, Intel i7-8650U @ 1.90 GHz.

| entries | verify cold ms | verify warm ms | evaluate hit ms | evaluate miss ms | peak RSS KiB | document bytes | items | fixture build s |
|---|---|---|---|---|---|---|---|---|
| 1 | 4.118654 | 1.822191 | 0.024798 | 0.002421 | 27,928 | 935 | 20 | 0.019115 |
| 1,000 | 616.362414 | 607.041677 | 0.060578 | 0.004549 | 48,160 | 619,100 | 11,009 | 7.395446 |
| 50,000 | 35,550.307898 | 36,461.347339 | 0.100214 | 0.007274 | 985,864 | 31,128,100 | 550,009 | 409.582130 |

These are the numbers every claim about resolver cost must cite.

- ONE RESOLVE AT THE 50,000 CAP COSTS ~35.5 SECONDS AND ~963 MiB. The evaluator is 0.00028% of it;
  full verification is the entire cost. Scaling 1,000 -> 50,000 is `N^1.037` in time and `N^1.000`
  in resident memory. Warm reuse buys nothing at cap scale (36.5 s warm against 35.5 s cold), which
  independently confirms no hidden cache exists.
- The full 50,000-entry set verifies successfully; `FUNCTION_MAX_ENTRIES` is a reachable working
  maximum, not an aspirational one. No bisect was needed and no point is interpolated.
- MAIN re-derived the n1 point from committed state: cold 4.159849 ms, warm 1.830171 ms, within
  noise of the recorded values.
- Prose obligation: `resolve` is pure, and pure is not cheap. No shipped sentence may imply that a
  read-only path is a fast path, and the table above is the referent. A caller holding a
  cap-scale function must be told the per-call price before it designs a request path around it.
- Method note worth preserving in any successor harness: build the fixture in a SEPARATE process.
  A Linux child inherits the builder's `ru_maxrss` high-water across exec, which silently
  contaminates the verification RSS measurement.

## 9. Normative claims - obligation without prose rewrite

`.agent/decisions/m3-map-c-lifecycle.md` rows S4-R01, S4-R02, S4-R04, S4-R14, S4-A01 and S4-A02
describe the `handle` lifecycle that is still LIVE at M3.2b. M3.2b adds `resolve` beside it and
deletes nothing, so rewriting that prose now would describe behaviour the code does not yet have.

M3.2b's obligation is therefore narrow and testable: introduce no new claim that contradicts those
rows, and no docstring or model docstring that calls `resolve` cheap, cached, repeatable across
calls, or a lease. The rewrite executes in M3.9a against shipped code.

Shipped prose that M3.2b leaves TRUE and unchanged, each re-derived against the code:
`README.md:63` (`verify_function` is read-only, six ordered checks over one snapshot),
`README.md:66` (an exported bundle evaluates with no ledger, adapter or LLM), `README.md:70` (every
verification result is one committed snapshot, not a lease), `docs/architecture.md:44` (offline
bundle resolution). M3.2b touches none of them.

One row is left INCOMPLETE rather than false and is handed forward: `docs/architecture.md:44`
describes only the offline evaluator, so after M3.2b the architecture document names no live
`System.resolve`. M3.9a owns adding it, together with the measured cost from section 8.

## 10. Gate identity and battery obligations

Gate: `uv run python -m unittest discover -s tests -t .` - the sole configured gate.

Closure is MECHANICAL, never a green suite:

- A diff-blind battery derived from THIS FILE alone, one obligation at a time, with a coverage
  grader naming the obligation each test discharges.
- Every obligation in sections 3-7 fails the battery when that obligation alone is removed. An
  obligation with no probe that can detect its deletion does not ship.
- A mutation sweep over every predicate `resolve` adds, addressed by unique anchor with a
  `count == 1` assertion, patch-changed-bytes proof, `__pycache__` purge under
  `PYTHONDONTWRITEBYTECODE=1`, byte-exact restore, pristine control first.
- A differential against an independently written oracle over the same probe corpus.
- Fixture rules that bind here: vary every dimension a claim spans (revision, status, partition),
  drive at least one integer above 9, use `_`/case collider pairs for any scope isolation, and
  corrupt the middle AND the last of at least three entries for any set-level claim.

## 11. Fork ruling - composition versus factoring

RULED: the THIN COMPOSITION ships. The plan draft's prescribed "factor `verify_function` so its
six-check core can run on a supplied connection" is SUPERSEDED and does not ship.

Evidence, all re-runnable (`.agent/decisions/m3u2b-compose-probes.py`, matrix
`m3u2b-compose-matrix.json`, 17/17 probes, 0 unknown, 0 mismatches, MAIN-rerun):

- The prescription had no nesting to fix. No helper reached between `system.py:2952` and
  `system.py:3363` opens a second transaction; all six take the connection as a parameter
  (MAIN-derived, corroborated by the map's A28). `verify_function` was already a single-snapshot
  method when the prescription was written against M3.2a's pre-capability code.
- C13, fork-deciding: the returned document evaluated while `in_transaction` was True and again
  after the connection closed produced EQUAL matches including artifact hash. The document is a
  self-contained value, so evaluation needs no connection.
- C16, the ablation: no behaviour was found that a supplied connection can produce and the
  composition cannot. `evaluate` touches only `bundle.entries` and `bundle.input_hashes` and holds
  no connection-related name.
- C6: exactly one `Store.transaction` call per resolve, `write=False`, with `in_transaction` True
  across all 13 traced statements and 15 samples.
- Cost of the difference: +34/-1 production lines measured (`__init__.py` +2, `models.py` +7/-1,
  `system.py` +25) against the draft's ~170-line estimate. Suite 600 -> 600, no regression.

The spike's implementation is throwaway evidence and is NOT merged; MAIN authors the shipped code.

FINDING RULED - optional-document narrowing. `FunctionVerification.document` is
`FunctionDocument | None`, and no static reader can derive `passed => document is not None` from the
type. `resolve` therefore binds the document and gates on both terms in ONE condition:

```python
document = verification.document
if not verification.passed or document is None:
    return FunctionResolution(verification=verification, match=None)
```

`or document is None` is UNFORCED and ships anyway. That is a deliberate exception to the mutation
criterion, and the distinction is the reason: M3.2a deleted `PRAGMA query_only` because an unforced
ENFORCEMENT line carries a defence-in-depth claim nothing verifies. This clause carries no claim and
has no runtime effect on any reachable state - `system.py:3355` sets `document=document if passed
else None`, and `passed` requires the P5 build that produced it - so it is a type-narrowing device,
not a check. Consequences, both binding: the battery pins `passed` alone and writes NO probe for the
second disjunct, and the mutation catalogue pre-registers deleting `or document is None` as a
PROVED-EQUIVALENT mutant with this reason, so the sweep cannot manufacture it as a finding.

## 12. Verdict table - MAIN-final

`PENDING` the diff-blind `test` teammate's phase-1 divergence table, ruled by MAIN before
implementation.

## 13. Review dispositions and differential result

`PENDING` wave-2/3 review and differential.
