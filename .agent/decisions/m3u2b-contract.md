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
- `expected_function_hash` is keyword-only and passes through to `verify_function` unchanged. The
  original rationale is WITHDRAWN on review (A01): it claimed that omitting the parameter costs a
  caller a second snapshot, and section 11's own C13 refutes that - a caller can pin identity in ONE
  snapshot with `verify_function(..., expected_function_hash=h)` followed by `evaluate` over the
  returned document. The parameter ships on the real reason: a resolver that cannot pin the identity
  it resolved against forces every pinning caller to reimplement the composition by hand.
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

`resolve` returns exactly one of three shapes FOR EVERY VERIFICATION `verify_function` PRODUCES, and
the three stay mutually distinguishable by `verification.passed` and `match` alone.

The domain qualifier on that headline sentence is CORRECTED on review (V02) and is load-bearing for
exactly the reason A12 gave for the biconditional below. Repairing one and leaving the other left the
exhaustiveness claim false: section 11's `or document is None` clause admits a FOURTH shape -
`passed=True`, `document=None`, `match=None` - which is the clause's whole purpose. That shape is
reachable only from a hand-built `FunctionVerification` or an override of public `verify_function`,
never from the unmodified method, and B14 pins it. Any claim in this file about what `resolve`
returns carries the same domain or it is false.

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
- `match is None` iff `passed is False`, OVER EVERY VERIFICATION `verify_function` PRODUCES. Both
  directions are pinned; the biconditional is asserted here deliberately because MAIN-authored
  contracts have repeatedly claimed one where the code implements the other. The domain qualifier is
  load-bearing and was added on review (A12): `FunctionVerification` carries no invariant binding
  `passed` to `document`, so a hand-constructed `passed=True, document=None` value reaches `match is
  None` with `passed is True` and falsifies the unqualified form. `verify_function` never emits that
  value - `system.py:3355` sets `document=document if passed else None` - so the qualified claim is
  the true one and the one the battery pins.
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
carries explicit multi-invalid pairs. The original two pairs (bad partition + bad input; bad
operation + bad expected hash) are INSUFFICIENT (A05): the permutation
`operation, partition, input, expected hash` satisfies both while violating both `partition <
operation` and `expected hash < input`. Four pairs are required, one per ADJACENT edge of the order:
partition + operation reports partition; operation + expected hash reports operation; expected hash
+ input reports the expected hash; and partition + input reports partition as the end-to-end check.
Adjacency is the point - a pair spanning two edges cannot localise which one moved.

## 5. Purity obligations - each pinned independently

No `resolve` path may: write any row, commit, allocate an ID, read the clock, emit an event,
suspend, quarantine, revoke, invoke a `CandidateSource`, create a file, or leave a transaction open.

Pins, one per obligation, never one composite assertion:

- Ledger bytes: sha256 of the ledger file AND full `connection.iterdump()` text are byte-identical
  across a hit, a miss and a failed verdict. Row-count snapshots are insufficient - an injected
  `UPDATE` passes them.
- Clock: a `System` whose `_now` raises resolves all three states unchanged.
- Events: `events()` is byte-identical before and after; the event sequence counter is unchanged.
- IDs (ADDED, A06): no stated pin detected a discarded allocation, because a wasted
  `uuid.uuid4()` moves neither the events table nor `sqlite_sequence`. Pin it the way
  `tests/test_system.py:2530-2531` already does - patch `cement_runtime.system.uuid.uuid4` to raise -
  across all three states.
- No file creation (WIDENED, A07): the deleted-ledger probe fails inside `Store.transaction`, before
  any post-verification branch, so it cannot see a file created on the hit path. Snapshot the full
  ledger DIRECTORY listing across hit, miss and failed verdict, and keep the deleted-ledger probe for
  its own separate claim - `resolve` raises and does not recreate the path.
- Source (WIDENED, A08): the miss case alone leaves a hit-guarded or failed-verdict-guarded call
  alive. Spy the source object across ALL THREE states and assert zero calls on each; a source whose
  `propose` raises stays as the belt-and-braces form.

## 6. Snapshot obligations

- EXACTLY ONE `store.transaction(write=False)` opens per `resolve` call THAT REACHES THE LEDGER, and
  ZERO for a call section 4 rejects. The original universal quantifier contradicted section 4 (A02).
  The battery pins BOTH counts, by a `wraps=` spy on `Store.transaction`, never by a read-only
  assertion alone: read-only proof and single-snapshot lifetime are separate guarantees.
- `connection.in_transaction` stays `True` across the whole six-check pass. The stated hazard is
  CORRECTED (A03): M3.2a's authorizer denies COMMIT, so a mid-method commit raises
  `_ReadOnlyViolation` rather than silently splitting the snapshot
  (`store.py:439,493-496`, `tests/test_read_capability_battery.py:71-81`). The pin survives the
  correction because it covers what the authorizer cannot - a helper that returns before the sixth
  check, or a future refactor that ends the block early - so it stays a battery obligation.
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
| suspended member, revocation, absent current receipt, wrong expected hash, over-capacity set | failed verdict, `passed=False` |
| a FABRICATED stale promoted revision (direct `UPDATE` of `operations.revision`) | failed verdict, `passed=False` |
| a revision bump through supported `revise_operation` | VERIFIED MISS, `passed=True`, `entries=0` |
| structurally corrupt bound content - ABI, report binding, digest, projection (`system.py:3098-3319`) | failed verdict, `passed=False` |

REACHABILITY, corrected on review (A04). The stored-operation-scalar row raises on WRONG TYPE alone
(`type(...) is not int` / `is not str`, `system.py:2960-2967`), never on a wrong VALUE of the right
type. All 13 user tables are `STRICT` and those columns are `NOT NULL`, so a type violation is
unstorable through any supported route: reaching that row needs a schema rewrite, a fabricated row or
a cursor proxy, and any probe for it is labelled FABRICATED. A wrong-value scalar takes the other
branch and produces a FAILED VERDICT - measured, three cases, none raising: `revision = 0` fails
`function-hash-matches-snapshot`; a non-hex `policy_hash` and a malformed `policy_json` each fail
`current-promotion-receipts` and `function-hash-matches-snapshot`. The same caveat applies to the
enumeration-count row, which needs a concurrent writer inside one snapshot. So of the five escaping
conditions, exactly TWO are reachable through supported calls: an unregistered operation and a
missing or unreadable ledger file.

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

- The unit ships two harnesses, both `N REPEATS` and both rerunnable from committed state:
  `.agent/decisions/m3u2b-benchmark.py` -> `m3u2b-bench.json` (components, graded by
  `uv run python .agent/decisions/m3u2b-validate.py .agent/decisions/m3u2b-bench.json`) and
  `.agent/decisions/m3u2b-resolve-benchmark.py` -> `m3u2b-resolve-bench.json` (the shipped
  `System.resolve`, end to end).

MEASURED at `019d040`, 3 repetitions, fixture built through public `System` methods in a separate
process, each cold sample a fresh process and a fresh `System`. The OS page cache was NOT dropped,
so cold means process-cold, never disk-cold.

Environment: Python 3.13.14, SQLite 3.53.1, Intel i7-8650U @ 1.90 GHz.

| entries | verify cold ms | verify warm ms | evaluate hit ms | evaluate miss ms | peak RSS KiB | document bytes | items | fixture build s |
|---|---|---|---|---|---|---|---|---|
| 1 | 4.118654 | 1.822191 | 0.024798 | 0.002421 | 27,928 | 935 | 20 | 0.019115 |
| 1,000 | 616.362414 | 607.041677 | 0.060578 | 0.004549 | 48,160 | 619,100 | 11,009 | 7.395446 |
| 50,000 | 35,550.307898 | 36,461.347339 | 0.100214 | 0.007274 | 985,864 | 31,128,100 | 550,009 | 409.582130 |

That table is a COMPONENT baseline and is labelled one on review (A09): its harness times
`verify_function` and standalone `evaluate` and never calls `resolve`, which did not exist at
`019d040`. It cannot see argument validation, the second dispatch or result construction, so it may
not be cited as the resolver's price.

END-TO-END, the numbers every claim about resolver cost must cite. Harness
`.agent/decisions/m3u2b-resolve-benchmark.py` calls the shipped `System.resolve` and nothing else,
3 repetitions, same separate-process fixture method, same environment, measured at `b5916a9`:

| entries | cold hit ms | warm miss ms | warm failed ms | peak RSS KiB | baseline RSS KiB | document bytes | fixture build s |
|---|---|---|---|---|---|---|---|
| 1 | 5.342079 | 2.177807 | 2.094797 | 27,280 | 26,640 | 935 | 0.019 |
| 1,000 | 643.635097 | 643.216052 | 634.907756 | 47,664 | 28,536 | 619,100 | 8.080 |
| 50,000 | 37,227.984277 | 40,169.974433 | 38,774.884113 | 985,568 | 28,496 | 31,128,100 | 437.082 |

- ONE RESOLVE AT THE 50,000 CAP COSTS ~37.2 SECONDS AND ~963 MiB. The resolver's own overhead above
  its components is ~4.7% at cap (37.23 s against the component 35.55 s), ~4.4% at 1,000, and ~30% at
  a single entry, where fixed validation cost dominates a 4 ms verification. Full verification is
  still the entire shape of the curve; the evaluator remains 0.00028% of it.
- Scaling 1,000 -> 50,000 is `N^1.037` in time, re-derived end-to-end at `1.037234`.
- RESIDENT MEMORY, corrected (A10). The published exponent `N^1.000` is INCREMENTAL - peak RSS minus
  the process baseline - and the committed component artifact records no baseline at all, so that
  number was not re-derivable from the artifact backing it. Both figures are now published and both
  are honest about what they measure: raw peak RSS scales `N^0.774`, incremental RSS scales
  `N^1.000` (measured `1.000180`). The interpreter and imports are the difference, ~28 MiB flat.
- WARM REUSE, corrected (A11). At cap the warm calls are SLOWER than the cold one (40.2 s and 38.8 s
  against 37.2 s), so warm reuse buys nothing measurable. The original inference - that this
  "independently confirms no hidden cache exists" - is withdrawn: timing equivalence bounds a cache's
  benefit below run-to-run noise and cannot establish absence. Absence rests on the code, where no
  resolver path stores state between calls.
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

`or document is None` ships. The original justification - unforced, no runtime effect on any
reachable state, therefore a deliberate exception to the mutation criterion - is WITHDRAWN (A12).
The clause IS forcible from the public surface: `FunctionVerification` is a public dataclass with no
invariant binding `passed` to `document`, so `FunctionVerification(passed=True, entries=0,
document=None, function_hash=None, checks=())` is constructible, and a subclass or mock of the public
`verify_function` returning it reaches `resolve` through ordinary Python. Measured on that probe:
with the clause, `match is None`; with it deleted, `evaluate(None, ...)` raises
`AttributeError: 'NoneType' object has no attribute 'input_hashes'`. Consequences, both binding and
both reversed from the original ruling: the battery WRITES that probe, and the mutation catalogue
pre-registers deleting `or document is None` as a KILLABLE mutant, never a proved-equivalent one.
The clause is therefore an ordinary defensive check meeting the standard criterion, and M3.2b takes
no exception to it. Note what the probe is and is not: mock-reachable, not real-ledger reachable, so
it is labelled FABRICATED like every other probe of an API-unreachable state.

## 12. Verdict table - MAIN-final

STILL `PENDING`, and the reason is a delivery failure, not a decision. `test-m3u2b` was dispatched
diff-blind with the validator and an all-`unknown` 16-row seed committed before dispatch, ran to 58%
of its window across three polls plus one explicit flush directive, and filled ZERO cells; it was
stopped at session close. Its worktree branch `wt/test-m3u2b` holds no rows. Session 3 re-dispatches
phase 1 as `test-m3u2b-2` against the seed, which is unchanged and still graded by the same command.

What implementation ran against instead, stated plainly so no reader mistakes this for a ruled
table: sections 1-11 as written, plus MAIN's own 38-check real-ledger smoke probe
(`.scratch/m3u2b-smoke.py`, all green at `b5916a9`), plus the twelve review findings in section 13.
The divergence table's distinct value - readings MAIN did not think to question - is UNBOUGHT, and
that gap is the honest state of this unit going into its battery session.

## 13. Review dispositions and differential result

### Contract attack, pre-implementation - 12 findings, 12 accepted

`rev-m3u2b`, dispatched against sections 1-11 before any code existed, returned 12 findings and MAIN
accepted all 12 in substance. Artifact with MAIN's per-finding disposition:
`.agent/decisions/m3u2b-attack.json` (validator-clean, `UNKNOWN-CELLS: 0`). Branch
`wt/rev-m3u2b` carries its four batch commits.

Distribution: 3 blocking, 9 major. ZERO were code defects and 12 were claim defects in MAIN's own
contract - a fifth consecutive unit with that shape, so the pre-implementation contract attack is now
unambiguously the default dispatch, not an experiment.

Amendments this drove, each landed in the section it corrects: section 2 (A01, withdrawn `FORCED`
rationale), section 3 (A12, domain qualifier on the biconditional), section 4 (A05, two precedence
pairs replaced by four adjacent-edge pairs), section 5 (A06/A07/A08, three widened or added purity
pins), section 6 (A02 quantifier, A03 hazard restatement), section 7 (A04 reachability), section 8
(A09/A10/A11, below), section 11 (A12, ruling reversed).

Three findings are worth naming for successors because each reverses something MAIN had ruled:

- A12 reversed MAIN's own deliberate exception to the mutation criterion. `or document is None` was
  pre-registered as a proved-equivalent mutant; it is in fact forcible from the public surface,
  because `FunctionVerification` binds `passed` to `document` by no invariant. The clause now meets
  the ordinary criterion and the battery writes the probe. The same construction falsifies the
  UNQUALIFIED biconditional in section 3, which is why that claim now names its domain.
- A05 caught a coverage hole MAIN had ALSO shipped in its own smoke probe: two precedence pairs pin
  only two of three adjacent edges, and the permutation `operation, partition, input, expected hash`
  survives both. A reviewer attacking the contract found the defect in MAIN's test design.
- A09 found the unit's headline durable claim unmeasured: the cost harness times `verify_function`
  and standalone `evaluate` and never calls `resolve`. Remedied by measurement, not by wording.

Cleared claims, recorded because a cleared claim is evidence and re-clearing it costs a session:
section 2's decorator recital and alphabetical export position; section 3's six check keys and their
order, the concrete `passed => document` invariant inside unmodified `verify_function`, the
over-capacity branch structure, and the zero-entry passing set; section 4's `_name` purity and the
canonicalization caps; section 6's one-snapshot count on the valid path, `in_transaction` across 15
samples, and document self-containment; section 7's invalid-argument classes, unregistered-operation
and missing-ledger mappings, wrong-scalar-TYPE raises, count-mismatch path, and locally caught
content corruption; section 8's time exponent (`1.036515`) and evaluator share (`0.000282%`);
section 9's four shipped prose references, all still true; section 11's call graph, confirming no
supplied-connection core is forced.

### Oracle - independent implementation, 26/26 probes

`orc-m3u2b` implemented sections 2-7 from the contract alone, with no access to MAIN's code, and
answered all 26 corpus probes `ok`: `.agent/decisions/m3u2b-oracle.json`, implementation
`oracle/m3u2b_oracle.py` and driver `oracle/driver.py` on branch `wt/orc-m3u2b` at
`a38d313f89c076c9475de2ad88e11049e1619076`. Observation key names are the ORACLE's, ruled so
deliberately: a MAIN-prescribed key set would leak MAIN's reading of each probe into the artifact and
shrink the divergence surface the differential exists to measure. Session 3's differential mirrors
those keys.

### Differential

`PENDING` session 3. Both observation files now exist in tracked state, keyed by the same
`ORACLE_PROBES` ids, so the comparison is a field-by-field pass over two committed JSON documents.
