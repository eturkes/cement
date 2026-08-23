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
  mirror, no `checks` copy. EXACTLY is unconditional for this unit (D02): the mutation criterion
  below explains why each candidate is excluded and never authorizes widening M3.2b's frozen shape.
  A later unit may revisit the shape; a reader of this one may not. Every candidate field faces the
  mutation criterion: ship it only with a
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
| verified miss | `True` | `FunctionMatch(matched=False, output=None, artifact_hash=None)` | the unchanged full document | yes |
| verified hit | `True` | `FunctionMatch(matched=True, output=..., artifact_hash=...)` | the unchanged full document | yes |

Both verified rows carry the SAME value (D04): the complete `FunctionDocument` `verify_function`
reconstructed, forwarded by object identity. Hit and miss differ only in the `FunctionMatch`
evaluation produces. `resolve` never projects, trims or re-derives a document, and B08's
`assertIs(resolution.verification, verification)` is the pin.

The six checks, in emitted order, are `verify_function`'s and are neither renamed nor re-scored
here: `duplicate-input-digests`, `abi-canonicalizer-uniform`, `sealed-passing-reports`,
`current-promotion-receipts`, `function-hash-matches-snapshot`, `persisted-function-receipt`.

CAPACITY IS A FAILED VERDICT, NOT AN ERROR. `FUNCTION_MAX_ENTRIES` is 50,000
(`function.py:27`). A promoted set above it returns early at `system.py:3037` with `passed=False`,
`entries` set to the real count, `document=None`, `function_hash=None` and all six checks FALSE,
without enumerating a single row. ENUMERATE is the observable helper boundary (D05): fetching or
materializing promoted member rows. One scalar `COUNT` query is permitted and is what the cap check
itself needs; the storage-engine reading, under which SQLite visiting index entries to satisfy that
count is enumeration, would forbid the very query the rule depends on. `resolve` therefore answers
`match=None` for an over-capacity scope. This is the unverified state, not a miss and not an exception, and the battery pins the
adjacent pair: exactly 50,000 entries verifies, 50,001 does not.

- A failed verdict is NOT a miss. An unverified function has no answer at all; a verified miss is a
  proven absence within a function that verified. Any consumer collapsing the two is a defect.
- `match is None` iff `passed is False`, OVER EVERY VERIFICATION THE UNMODIFIED
  `System.verify_function` IMPLEMENTATION PRODUCES. The domain names the implementation, not the
  attribute (D06): Python dispatch means a subclass or a patch "produces" its return value too, and
  such a value falsifies the biconditional by construction. `resolve`'s own weaker invariant holds
  for an arbitrary override return: `match is None` whenever `passed is False` OR `document is
  None`, which B14 and B34 pin one term each. Both
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

Then the ledger read, then evaluation. THE LEDGER READ begins at transaction entry or first SQL
access (D08), so `verify_function`'s own pure re-validation before that boundary conforms. B17 pins
the stronger property anyway: a call this section rejects makes zero `Store.transaction` calls AND
zero `verify_function` calls.

EXACT MESSAGES, published here because the battery pins them and a contract that names none invites
a paraphrase to become the pin (D09). Message identity is normative; reuse of the `_digest` helper
is an implementation choice.

| argument | class | message |
|---|---|---|
| `partition` | `ValidationError` | `partition must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'` |
| `operation` | `ValidationError` | `operation must be 1-128 ASCII letters, digits, '.', '_', ':', '/', or '-'` |
| `expected_function_hash` | `ValidationError` | `expected_function_hash must be a SHA-256 hex digest` |
| `input_value` | `ValidationError` | `canonicalize`'s own text, e.g. `value of type 'object' is not JSON` |

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

LEAVE A TRANSACTION OPEN means, observably (D10): the read context has exited and no SQLite
transaction or lock is still held. Closing the only connection handle satisfies it and is what the
Store does; no clause requires an inspectable post-return connection.

Pins, one per obligation, never one composite assertion:

- Ledger bytes: sha256 of the ledger file AND full `connection.iterdump()` text are byte-identical
  across a hit, a miss and a failed verdict. Row-count snapshots are insufficient - an injected
  `UPDATE` passes them.
- Commit (ADDED, V10): its own spy, because the ledger-bytes pin cannot discharge it. A successful
  NO-OP commit moves neither the file sha256 nor the iterdump text, so B18 passes through one. B35
  counts `commit()` on a `sqlite3.Connection` subclass injected as the connect `factory`, asserts
  zero across all three states, and first proves the instrument live on a write transaction whose
  commit moves no ledger byte. MEASURED against the mutant this obligation exists for - `_release`
  clearing the authorizer and committing instead of rolling back, which is a plausible "end the
  snapshot" refactor: B18, B25 and B26 all PASS and B35 alone fails, on each of the three states.
- Clock: a `System` whose `_now` raises resolves all three states unchanged.
- Events: `events()` is byte-identical before and after; the event sequence counter is unchanged.
- IDs (ADDED, A06; NARROWED, D11): the obligation is UUID allocation through `_new_id`/`uuid.uuid4`,
  discarded results included, never the allocator-independent universal. Nothing establishes that
  every possible identifier flows through `uuid4`, so the universal claim outran its own mandated
  probe. No stated pin detected a discarded allocation, because a wasted `uuid.uuid4()` moves
  neither the events table nor `sqlite_sequence`. Pin it the way `tests/test_system.py:2530-2531`
  already does - patch `cement_runtime.system.uuid.uuid4` to raise - across all three states.
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
  The counted event is INVOCATION, because that is what a `wraps=` spy sees (D12): a call whose
  preflight passes invokes `Store.transaction` exactly once even when the context fails to enter, as
  a deleted ledger does. SNAPSHOT is the narrower word and means a context that entered.
  The battery pins BOTH counts, by a `wraps=` spy on `Store.transaction`, never by a read-only
  assertion alone: read-only proof and single-snapshot lifetime are separate guarantees.
- `connection.in_transaction` stays `True` across the whole six-check pass. The stated hazard is
  CORRECTED (A03): M3.2a's authorizer denies COMMIT, so a mid-method commit raises
  `_ReadOnlyViolation` rather than silently splitting the snapshot
  (`store.py:439,493-496`, `tests/test_read_capability_battery.py:71-81`). The pin survives the
  correction because it covers what the authorizer cannot - a helper that returns before the sixth
  check, or a future refactor that ends the block early - so it stays a battery obligation. That
  same gap is what section 5's commit spy (B35) closes: the authorizer grades caller SQL, never a
  Store-owned release path that lifts enforcement before it acts.
- Evaluation runs over the DOCUMENT VALUE. The document is a self-contained reconstruction, so
  evaluating it after the snapshot ends returns the same answer as evaluating it inside; the battery
  proves that equality rather than assuming it.
- NO cross-call consistency claim. Two consecutive `resolve` calls are two snapshots, and a writer
  committing between them legitimately changes the second answer. Prose must never call `resolve`
  repeatable across calls. Determinism and snapshot stability are SEPARATE (D13): equality across
  two calls over a byte-identical ledger state does follow from purity plus canonical evaluation,
  but it is not a tested invariant here and no shipped sentence may promise it. What is disclaimed
  is stability across an intervening writer; what is untested is the byte-identical case.

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
| suspended member, revocation, absent current receipt WHERE PROMOTED MEMBERS EXIST, wrong expected hash, over-capacity set | failed verdict, `passed=False` |
| a registered operation that has promoted nothing, so no receipt was ever persisted | VERIFIED MISS, `passed=True`, `entries=0` |
| a FABRICATED stale promoted revision (direct `UPDATE` of `operations.revision`) | failed verdict, `passed=False` |
| a revision bump through supported `revise_operation` | VERIFIED MISS, `passed=True`, `entries=0` |
| structurally corrupt bound content - ABI, report binding, digest, projection (`system.py:3098-3319`) | failed verdict, `passed=False` |

FABRICATED - the taxonomy, because the label was defined by API-unreachable STATE while being
applied to instrumentation too, leaving its evidentiary weight unstated (D15). Three categories,
three claim limits:

- CONSTANT PATCH (the cap lowered to 3): the code path is real and ordinary; only the boundary
  moves. Substantiates branch behaviour AND the adjacent-pair shape, never the production constant.
- PUBLIC OVERRIDE (a `verify_function` returning a value the base method never emits): the caller
  is real Python, the VALUE is unreachable. Substantiates `resolve`'s defensive branch, never a
  claim about states a real ledger reaches.
- STORAGE REWRITE (direct `UPDATE`, schema rewrite, cursor proxy): substantiates that the guard
  translates corruption, never that the corruption is reachable or that it ever occurs.

No fabricated probe may be cited for reachability, frequency or operator-visible behaviour, and a
row reached only by fabrication says so where it is claimed.

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
3 repetitions, same separate-process fixture method, machine otherwise idle. Every point carries its
own provenance and the harness refuses to merge points whose provenance differs, so this curve is
one build measured three times: `23ec5717`, clean tree, CPython 3.13.14, SQLite 3.53.1,
`Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz`. Re-derivation path, which regrades the table and
reprints the exponents below:
`uv run python .agent/decisions/m3u2b-validate.py .agent/decisions/m3u2b-resolve-bench.json`.

| entries | cold hit ms | warm miss ms | warm failed ms | peak RSS KiB | baseline RSS KiB | document bytes | fixture build s |
|---|---|---|---|---|---|---|---|
| 1 | 5.736265 | 2.301882 | 2.110633 | 27,380 | 26,760 | 935 | 0.033 |
| 1,000 | 613.171690 | 604.683021 | 593.839974 | 47,692 | 28,848 | 619,100 | 7.287 |
| 50,000 | 36,452.212317 | 36,967.247511 | 37,107.096461 | 985,696 | 28,644 | 31,128,100 | 405.696 |

- ONE RESOLVE AT THE 50,000 CAP COSTS ~36.5 SECONDS AND ~963 MiB. Full verification is the entire
  shape of the curve; the evaluator remains 0.00028% of it.
- RESOLVER OVERHEAD IS NOT RESOLVABLE AT SCALE, and the earlier "~4.7% at cap / ~4.4% at 1,000"
  figures are withdrawn as over-precise. The two tables are separate runs, so their difference
  carries both runs' noise: at cap end-to-end reads +2.5% over the component baseline (36.45 s
  against 35.55 s) and at 1,000 it reads 0.5% FASTER (613.17 ms against 616.36 ms), which no real
  overhead can be. Only the single-entry point exceeds noise, at +39% (5.74 ms against 4.12 ms),
  where fixed argument validation and result construction dominate a 4 ms verification. Any tighter
  overhead claim requires both paths measured in one harness run.
- Scaling 1,000 -> 50,000 is `N^1.044` in time, re-derived end-to-end at `1.044246`.
- RESIDENT MEMORY, corrected (A10). The published exponent `N^1.000` is INCREMENTAL - peak RSS minus
  the process baseline - and the committed component artifact records no baseline at all, so that
  number was not re-derivable from the artifact backing it. Both figures are now published and both
  are honest about what they measure: raw peak RSS scales `N^0.774` (measured `0.774173`),
  incremental RSS scales `N^1.004` (measured `1.003998`). The interpreter and imports are the
  difference, ~28 MiB flat.
- WARM REUSE, corrected (A11). At cap the warm calls are SLOWER than the cold one (36.97 s and
  37.11 s against 36.45 s), so warm reuse buys nothing measurable. The original inference - that this
  "independently confirms no hidden cache exists" - is withdrawn: timing equivalence bounds a cache's
  benefit below run-to-run noise and cannot establish absence. Absence rests on the code, where no
  resolver path stores state between calls.
- The full 50,000-entry set verifies successfully; `FUNCTION_MAX_ENTRIES` is a reachable working
  maximum, not an aspirational one. No bisect was needed and no point is interpolated.
- Prose obligation: `resolve` is pure, and pure is not cheap. No shipped sentence may imply that a
  read-only path is a fast path, and the table above is the referent. A caller holding a
  cap-scale function must be told the per-call price before it designs a request path around it.
- Method notes, both binding on any successor harness. Build the fixture in a SEPARATE process: a
  Linux child inherits the builder's `ru_maxrss` high-water across exec, which silently contaminates
  the verification RSS measurement. Measure on an IDLE machine: a curve taken while the same
  workstation edited files and ran short test runs read 44.6 s at cap and 746 ms at 1,000, +22% and
  +22% over the idle values published above, and nothing in the artifact marks it contaminated.

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

CLOSED. 16 divergences enumerated diff-blind from sections 1-11, every one ruled by MAIN:
`.agent/decisions/m3u2b-divergences.json`, `UNKNOWN-CELLS: 0`, `main_verdict` filled on all 16,
applied by the idempotent `.scratch/m3u2b-rule-divergences.py` (reruns to the same bytes).

Distribution: 2 CLEARED with no change (D01, D03 - each conceding no defensible alternative), 12
ACCEPTED as contract clarifications landed in the section each corrects, and 2 ACCEPTED that were
already fixed at `455be4c` by MAIN's own battery. ZERO code defects, the sixth consecutive unit
with that shape.

The two independent confirmations are the ones worth naming, because both are the council rule
firing across instruments rather than lenses. D14 and battery obligation B29 separately found that
section 7 listed `revision drift` unqualified while `revise_operation` retires every stranded
artifact, so the supported route gives a verified miss. D16 and battery obligation B31 separately
found `System.resolve` citing the COMPONENT benchmark that section 8 forbids as a resolver-cost
referent.

Delivery record, because it is the unit's clearest measurement of what makes a dispatch land.
`test-m3u2b` got the validator plus an all-`unknown` 16-row seed committed before dispatch, ran to
58% of its window across three polls and one flush directive, and filled ZERO cells. Its successor
`test-m3u2b-2` got the identical validator, the identical brief shape and the identical seed plus
one addition - a `section` anchor and an ungraded `locus` naming each row's SUBJECT - and filled
16 of 16. Seeding the deliverable is necessary; seeding the row subjects is what makes a generative
deliverable resumable.

What implementation ran against before this table existed, stated plainly: sections 1-11 as
written, plus MAIN's own real-ledger smoke probe, plus the twelve review findings in section 13.
That probe was machine-local and is now superseded - all 43 of its checks map to committed tests in
`.agent/decisions/m3u2b-smoke-crosswalk.json` (`UNCOVERED: 0`), so no durable claim rests on it.

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

CLOSED, and it returned nothing. 26 probes compared field by field over two committed JSON
documents keyed by the same `ORACLE_PROBES` ids: 0 behavioral divergences, 0 text differences, 0
missing keys, exit 0 (`.agent/decisions/m3u2b-differential.py` over `m3u2b-main.json` and
`m3u2b-oracle.json`). MAIN credited it by RE-DERIVATION, never by report - the driver replays
`m3u2b-main.json` byte-identically, sha256 `55a3f586...`.

Zero TEXT differences is the informative half, against M3.2a's 17 on the same instrument: every
pinned message here comes from a library validator both implementations delegate to, while
M3.2a's came from a translation layer authored twice. A differential measures authored surface,
so a composition that adds none returns none, and that is a result rather than a failure.

### Post-implementation review - 12 findings

`rev2-m3u2b`, dispatched against the landed diff: `.agent/decisions/m3u2b-review.json`. Four
CLEARED with enforcement classification (V01, V03, V04, V06), eight upheld. V02, V05, V09 and V12
closed in session 3; V07, V08, V10 and V11 closed in session 4 and are recorded in the sections
they corrected.

V12 is the one that changes how this unit is closed. Deleting `not verification.passed or` from
`resolve`'s gate passed all 633 committed tests, and MAIN's independent 23-mutant sweep found the
same survivor. Cause is structural: `verify_function` sets `document=None` whenever `passed` is
False, so every REAL output binds both gate terms and no real-ledger probe can separate them. B34
is the mirror of B14's fabricated probe and closes it. Whenever a fabricated probe or a mutation
exemption is written for one term of a compound condition, write its mirror in the same breath.

### History correction - `b5916a9`'s subject cause is false (V08)

`b5916a9`'s subject reads `resolving an input cost two snapshots → compose evaluate onto one
verified snapshot`. The stated cause is REFUTED by this contract's own accepted A01: `verify_function`
followed by `evaluate` over the returned document was ALREADY one snapshot, because the document is
a self-contained reconstruction and evaluating it after the snapshot closes returns the same answer
(section 11, probe C13). Git history cannot be rewritten, so the correction lives here.

What that commit actually bought, stated truthfully: one public entry point for a two-call sequence
every caller would otherwise compose by hand, with the failed-verdict gate and the `match is None`
biconditional enforced in one place instead of at each call site. The cost claim in the same commit
body stands; only the subject's causal clause is wrong. A scoped-commit subject is durable and
unrewritable, so a later correction needs a tracked home and this section is it.
