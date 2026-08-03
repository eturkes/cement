# M2 u4b design record — MAIN arbitration

Inputs: three independent full-design spikes, each with a staging worktree prototype driven by real
public-API probes — `.scratch/agents/spike-m2u4b-composite.md` (one composite call, two nested anchor
sections), `spike-m2u4b-split.md` (two per-anchor methods plus a shared-snapshot mechanism),
`spike-m2u4b-minimal.md` (KISS baseline: flat counts, hard projection cap, per-category digests).
Baseline HEAD `d0b7e93`; gates green under MAIN's own run (314 tests OK, `uv build` OK). Every staging
tree independently reached green gates (composite 320 tests, split 318, minimal 318) and each prototype
held the u4b write set, so all three costed designs are buildable, not sketches. Peaks: composite 66%,
minimal 83%, split 86%.

## Decision 1 — one composite read-only call; the split is rejected by its own author

`split` self-rejected on its own measurements after building the mechanism it was asked to defend:

- Atomicity degrades from a structural property to caller discipline. Both methods stay conveniently
  callable standalone, which is exactly the composition Decision 1 of `m2u4-design.md` measured as
  contradictory. Its own standalone interleave produced membership at event watermark 14 beside operation
  state at watermark 15, with a 5,777.819 µs window.
- The mechanism costs a stateful public `CoverageSnapshot` lease owning a live connection. A deliberately
  unclosed snapshot blocked a writer **10,017.791 ms** and then failed it with
  `StateError("database is busy or unavailable")` — SQLite `journal_mode=DELETE` lets the writer stage but
  not commit behind a live reader, and `busy_timeout` is 10 s. Correct use still extends write latency,
  since its own 10,000-scope report takes 2.083 s inside the snapshot.
- Cost `+676/-33` production, roughly twice the unit estimate, mostly validation duplicated to make each
  method independently callable.

Its recommendation is the accepted shape: one composite call returning separately named nested anchors, so
Decision 2 of `m2u4-design.md` stays semantic while the one-transaction guarantee becomes structural and
connection lifetime never escapes the method. `composite` reached the same shape independently.

## Decision 2 — the function anchor does not reconstruct; it validates the receipt row and the members it returns

All three prototypes called full receipt reconstruction from the report, and `composite` then named the
consequence as the strongest case against itself: `_function_anchor_report` → `_reconstruct_function_receipt`
walks memberships, artifacts, reports and every sealed test set, so a corrupt or 50,000-member selected
receipt makes the **operation-now** report unavailable even though current compile/pending/status data is
healthy.

Rejected. The report validates the receipt row through the existing `_function_receipt_from_row` and
validates only the member rows it actually returns. Three independent reasons:

1. It is the repository's own frozen convention. u4a's accepted surface validates every returned row and
   nothing else (`m2u4-design.md` Decision 4), and its review pinned exact bounded materialization —
   `LIMIT ?` bound to the limit, never slice-after-fetch.
2. `reconstruct_function_receipt` stays the sole reconstruction surface. u3b2 froze that, and u4a's record
   kept exactly one meaning of "reconstruct" in the API; calling it from a reporting method reintroduces
   the second meaning u4a rejected.
3. It removes the coupling defect at no honesty cost, provided the limit is recorded: the anchor proves
   row-level receipt self-binding plus the validity of returned members, never that the whole membership
   reconstructs. A caller wanting that composes `reconstruct_function_receipt(partition, receipt.id)`.

## Decision 3 — exact SQL counts plus a bounded projection; no per-category digest

`minimal` added a SHA-256 digest per category over every ordered item, mirroring u3b1's revocation
projection. Rejected here, on three grounds:

- The u3b1 pattern exists because that projection is sealed into an **immutable event payload**. This
  report is ephemeral, carries no identity, and is persisted nowhere.
- It forces O(n) materialization plus canonical JSON of every row in every category, which forfeits the
  bounded-materialization contract u4a's review pinned. `split` measured exact `COUNT(*)` + `LIMIT`
  answering 50,001 pending proposals in 429.285 ms; `minimal` measured its digest path 7.6% slower than
  even an unbounded projection at 10,000 rows, because the honest full digest is unavoidably O(n).
- A digest on a now-bearing surface invites exactly the coverage-identity misreading Decision 2 of
  `m2u4-design.md` forbids. The function anchor already carries the one real identity, `function_hash`.

Accepted rule: exact counts are never sampled, estimated or clamped; detail tuples hold at most
`projection_limit` items; truncation is visible as `count > len(items)`, with no redundant `has_more`.
Compile-ready and compile-blocked are the sole categories whose **counts** cost a full pass, because
ready-vs-blocked cannot be read from stored status — all three spikes agree evaluation is full while
retention is bounded (`split`: 10,000 live scopes in 2.083 s).

## Decision 4 — `projection_limit` is a validated `1..10_000` argument, not a private constant

`minimal` hard-coded 100 with no argument and then self-rejected on it: 9,900 of 10,000 pending IDs and
49,900 of 50,000 member annotations become unreachable through any public read, since
`reconstruct_function_receipt` returns document entries with artifact hashes rather than membership
artifact IDs and sealed support/reviewer columns. The repository bound already answers this —
`_bounded_int(limit, ..., minimum=1, maximum=10_000)` is used by every existing read method, and
`m2u4-design.md` corrected the same deviation once already for u4a. Validated, never clamped; over-cap
raises `ValidationError`. The name is `projection_limit` rather than `limit` because it bounds per-category
detail retention and there is deliberately no cursor: this surface does not page.

## Decision 5 — accepted surface (frozen)

```python
System.function_report(
    partition: str,
    operation: str,
    *,
    receipt_id: str | None = None,
    projection_limit: int = 100,
) -> FunctionReport
```

All models `@dataclass(frozen=True, slots=True)`, every field required, no defaults.

```python
class FunctionMember:
    ordinal: int
    artifact_id: str
    input_hash: str
    build_support: int            # sealed artifacts.support
    build_reviewer_count: int     # sealed artifacts.reviewer_count

class FunctionAnchorReport:
    receipt: FunctionReceipt      # unchanged u4a model
    member_count: int             # receipt member_count, exact
    members: tuple[FunctionMember, ...]

class CompileScope:
    input_hash: str
    active_support: int
    active_reviewer_count: int
    active_span_seconds: int
    reasons: tuple[str, ...]      # () = ready

class PendingProposalGap:
    proposal_id: str
    request_id: str
    operation_revision: int
    input_hash: str

class OperationArtifact:
    sequence: int
    artifact_id: str
    operation_revision: int
    input_hash: str
    status_reason: str | None

class OperationArtifactStatus:
    status: Literal["draft", "verified", "promoted", "suspended", "retired"]
    count: int
    artifacts: tuple[OperationArtifact, ...]

class StaleRevisionAnomaly:
    artifact_id: str
    status: Literal["draft", "verified", "promoted"]
    artifact_revision: int
    current_revision: int
    reason: str

class OperationNowReport:
    operation_revision: int
    policy_hash: str
    projection_limit: int
    promoted_entry_count: int
    compile_ready_scope_count: int
    compile_ready_scopes: tuple[CompileScope, ...]
    compile_blocked_scope_count: int
    compile_blocked_scopes: tuple[CompileScope, ...]
    pending_proposal_count: int
    pending_proposals: tuple[PendingProposalGap, ...]
    artifact_statuses: tuple[OperationArtifactStatus, ...]   # exactly 5, fixed order
    stale_revision_anomaly_count: int
    stale_revision_anomalies: tuple[StaleRevisionAnomaly, ...]

class FunctionReport:
    partition: str
    operation: str
    function_anchor: FunctionAnchorReport | None
    operation_now: OperationNowReport
```

Deliberate exclusions, each with its reason:

- **No event watermark.** `composite` and `split` both carried `observed_event_sequence` so a consumer
  could detect that two reports came from two snapshots. One composite call removes that use, and
  `split`'s own self-critique warns the number is only a public-write watermark that schema-preserving
  mutation bypasses — a field inviting a snapshot-identity reading it cannot support.
- **No typed reason codes.** `composite` classified into a five-member `Literal`, then listed
  fail-closed-on-unknown-detail as a required mutation obligation. The compiler's ordered strings are the
  authoritative vocabulary; re-deriving codes duplicates it and adds a classifier that can drift.
- **No `entry_seal` / `report_id` on members, no `projected_build_hash` / `was_promoted`.** Already
  reachable through `reconstruct_function_receipt` and `inspect_function_promotion`.
- **No frozen support/reviewer columns on `OperationArtifact`.** Those are build-time values; exposing
  them beside `active_*` inside the now-bearing anchor blurs exactly the boundary Decision 2 of
  `m2u4-design.md` draws. They appear only under the function anchor, named `build_*`.

Naming boundary, structural: frozen fields are `build_support` / `build_reviewer_count`; current fields are
`active_support` / `active_reviewer_count` / `active_span_seconds`. No field subtracts, ratios or
complements one anchor against the other, and no field is named for the other anchor.

## Decision 6 — selection, resolution and failure convention

- `receipt_id=None` → the newest receipt of the operation's **current** revision, read inside the report
  transaction. Current revision with no receipt → `function_anchor=None`, and the operation report still
  returns. This differs deliberately from u4a's `latest_function_receipt`, which raises
  `NotFoundError("current operation revision has no function receipt")`: that method's whole purpose is
  resolving an identity, while here the operation-now anchor must stay renderable for a new operation.
- Explicit `receipt_id` → exact `(partition, operation, id)`; historical revisions are legal, since the
  anchor is immutable identity. Missing or wrong-operation → `NotFoundError("function receipt does not
  exist for this operation")`.
- Unknown operation or partition → `NotFoundError("operation is not registered in this partition")`, the
  shared repository string. `function_report` resolves current revision and policy, so it raises like
  every other current-revision method; u4a's empty-page convention binds pure enumeration only, and
  `function_receipts` keeps it.
- Registered operation with no evidence → zero counts, empty tuples, `function_anchor=None`.
- Integrity failures stay raised as `IntegrityError` and are never downgraded into a gap reason or a
  friendly category. A persisted `building` artifact and an unknown stored status are integrity failures,
  since no reader can legitimately observe either committed. Unselected rows beyond `projection_limit` are
  counted but not validated — the report never claims validated history.

## Decision 7 — compiler factoring (converged, all three prototypes)

All three independently produced the same read-callable generator, and all three proved `compile()`
byte-identical before and after:

```python
def _current_build_projections(
    self, connection: sqlite3.Connection, operation_row: sqlite3.Row,
) -> Iterator[tuple[str, str, _CurrentBuild | _BlockedBuild]]:
```

It selects active (non-revoked) examples for the operation's current revision, grouped by
`(input_hash, input_json)` and ordered by both, raising `IntegrityError("one input digest maps to multiple
canonical inputs")` when one digest carries two canonical texts, and yields
`self._project_current_build(...)` per scope. `compile()` consumes the iterator and keeps its insert /
existing / block shaping outside; its serialized blocked shape (`input_hash`, `reasons`, `support`) stays
frozen. `_BlockedBuild` gains `reviewer_count` and `span_seconds`, values `_project_current_build` already
computes, so `CompileScope` needs no recomputation. Laziness is preserved (generator, not a materialized
list) so compile's per-group interleaving is unchanged.

The five block reasons are the compiler's own strings, in emitted order, all five reached by real
public-API probes in all three spikes: `confirmed outputs conflict`; `support {n} is below required {m}`;
`reviewers {n} is below required {m}`; `span {n}s is below required {m}s`; and the singleton
`artifact constraint: {ValidationError}`, reachable with a 63-level nested input that public
`handle`/`review` accept while the artifact wrapper crosses canonical depth 64.

## Decision 8 — ordering (deterministic, pinned)

- `members` — receipt ordinal ascending, which is canonical `input_hash` ascending.
- `compile_ready_scopes` / `compile_blocked_scopes` — `(input_hash, input_json)` ascending, the helper's
  own order.
- `pending_proposals` — proposal ID ascending.
- `artifact_statuses` — the fixed vocabulary order draft, verified, promoted, suspended, retired, always
  five entries even when a count is 0.
- `artifacts` within a status — `sequence` descending (newest first); `sequence` is returned so the order
  is observable.
- `stale_revision_anomalies` — artifact ID ascending.

`promoted_entry_count` is revision-unfiltered, matching `verify_function`, so a stale promoted row is
counted and additionally reported as an anomaly rather than hidden. Stale anomalies cover
`draft|verified|promoted` rows whose stored revision differs from current; suspended and retired rows on
old revisions are expected history, not anomalies. This closes the u3b1 observability asymmetry in the
reporting surface — `inspect_function_promotion` returns `entries=0, skipped=0` for a stale verified row
while this report names it — and promotion planning itself stays silent, which remains open.

## Cost estimate, corrected against measurement

The planning band was 280–360 production / 2,200–2,800 tests, estimated from a surface map before any
prototype existed. Measured prototypes: minimal `+320/-28`, composite `+630/-28`, split `+676/-33`. The
accepted design is minimal's economy plus typed models, `projection_limit`, policy binding and the five
status groups, minus reconstruction call-through and digests, so **340–420 production / 2,200–2,800 tests**
is the corrected estimate. It exceeds the band's top by at most ~17%; the smallest complete prototype
satisfying the scoped measure list was already +320 while carrying neither a limit argument nor typed
models. Scope is unchanged — only the estimate moves, onto evidence.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root.

## Required test construction

Binding, from `.agent/memory.md` and `m2u4-design.md`; each rule cost a prior unit a real defect:

- Mutation criterion binds every added check: some committed test fails when that check's logic alone is
  deleted.
- Set/loop-quantified checks corrupt the **middle AND the last** of ≥3 elements. Middle-only probes left
  8 separate u3b2 checks with every last-row mutant alive.
- Enumeration completeness needs a tail sentinel past any plausible `LIMIT`; `LIMIT 1000` on two u3b1
  queries left all 208 tests green.
- Scope isolation needs `_` and case collision pairs (`tenant_a` vs `tenantXa`, `echo_1` vs `echoX1`),
  because `=` weakens to `LIKE` undetected otherwise — u4a had four live `=`→`LIKE` mutants pass 307 tests.
  The pending join binds **both** `partition` and request ID, since the request PK is `(partition, id)`.
- Read-only proof and single-snapshot lifetime are separate pins: a write-denying authorizer plus a full
  `iterdump()` comparison for non-mutation, and `connection.in_transaction` asserted still True at the
  last read for lifetime, since a mid-method `commit()` survives every read-only assertion.
- Resource contracts are invisible to behavioral tests: pin exact bounded materialization with a
  connection/cursor proxy asserting the final `LIMIT` bind and the row count actually fetched.
- Frozen public shape needs one `inspect.signature` + `typing.get_type_hints` test per frozen ABI;
  removing a `*`, adding a defaulted field and changing a return annotation are all invisible otherwise.
- Vary fixtures across every boundary a check depends on and drive at least one integer ≥10, since values
  below 10 make base-10 and hex framing identical.
- Mutation harnesses purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`, prove the mutant reached the
  interpreter, and target by line plus an asserted anchor string, never by occurrence index.
