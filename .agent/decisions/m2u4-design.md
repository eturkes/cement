# M2 u4 design record — MAIN arbitration

Inputs: `.scratch/agents/map-m2u4.md` (surface map + sizing), plus three independent full-design spikes,
each with a staging prototype driven by real pipeline probes — `spike-m2u4-census.md` (operation-wide
ledger census behind one new `System` method), `spike-m2u4-anchored.md` (membership + complement of one
`function_hash`), `spike-m2u4-compose.md` (KISS baseline: CLI composes existing reads, no new API). All
three spike reports were persisted by MAIN from transcripts; the teammates' harness refused the file
write. Baseline HEAD `b87dde0`; gates green under MAIN's own run (293 tests OK, `uv build` OK). Every
staging tree independently reached green gates (census 3 tests, anchored 298 total, compose 297 total), so
all three costed designs are buildable, not sketches. Peaks: map 72%, compose 79%, census 85%, anchored
87%.

## Decision 1 — the compose baseline is rejected, on its own measurements

A library-level read-only report method is necessary. Three independent probe results, all from the
baseline's own author:

- **Compile-blocked scopes are unreachable read-only through existing methods.** Blocked state is
  persisted nowhere (`store.py` has no blocked table/column/event; `map-m2u4.md` Q2c), and public
  `compile()` is a write: obtaining blockers through it committed `{"artifact_evidence":3,"artifacts":1,
  "events":1}`. The decisive probe went further — two ledgers, one with a challenge-origin example's
  hidden `receipt_json` corrupted, were compared across all 13 existing read methods
  (`operations`, `proposals`, `proposal`, `artifacts`, `artifact`, `reports`, `report`, `examples`,
  `events`, `request_status`, `verify_function`, `inspect_function_promotion`,
  `reconstruct_function_receipt`). Every read was identical; both projections hashed to
  `6943b6908f5c02ecf86d112fe0ad3aace2a090c361d32cf27aa2d3c49b3c9091`. The compiler nonetheless diverged:
  healthy → two blockers, corrupt → `IntegrityError` on the receipt digest. `examples()` exposes
  `receipt_hash` but not `receipt_json`/`input_hash`/`output_hash`, and a challenge-origin example has no
  request whose status could expose it. No composition of existing reads can reproduce the compiler's
  verdict.
- **Composition is not atomic and the inconsistency is real, not theoretical.** Suspending one promoted
  artifact between two of the four composed reads produced a single emitted report asserting
  `promoted_entry_count = 2` with `passed = true` alongside an artifact page holding 1 promoted + 1
  suspended. Measured window 2,849 µs; the API bounds it nowhere.
- **Reachability cost is 122 non-blank lines** of paging/shaping every library consumer must duplicate,
  excluding parser, raw emission, export/eval, and the failed blocked derivation.

Carried forward from the baseline as accepted, because it proved these cheap: offline eval needs only a
narrow gating exception; live and receipt export need no new `System` API; per-entry support and reviewer
counts are stored columns, not an N+1 rollup — one `artifacts` call served 200 entries in 3.983 ms.

## Decision 2 — two separately-anchored surfaces, never one merged number space

Both surviving spikes self-rejected as the *sole* meaning of coverage, independently, on the same defect:
one object mixing temporal anchors is literally true and structurally misleading.

- census: "combines frozen build-time evidence, current compile-blocked evidence, and all-revision
  historical state without binding the report to a function hash… every number is literally true, but the
  report does not describe one coherent function or one coherent evidence time." Its own sample carried
  frozen A support `2` beside current blocked A support `1`, frozen promoted B support `3`, and historical
  retired B support `2`. It further fails closed on long-lived ledgers: historical suspended/retired/
  pending rows can exceed 50,000 while the live function has one entry, making `show` unavailable exactly
  when the function is small.
- anchored: a receipt seals `M(receipt)`; the complement is `U(now)` = current active-evidence scopes ∪
  current pending proposals ∪ all artifact rows. `U(now)` is neither sealed by the receipt nor a naturally
  complete universe (it excludes rejected proposals, failed requests, revoked-only scopes, resolved-request
  history), so "complement of the function" is the wrong name for it. Its three-promotion probe made the
  temporal defect concrete: receipt sequence 1 stayed fixed at `member_count = 2` while its reported
  current promoted count became 4 and it acquired 3 promoted nonmember gaps and 4 compile-ready gaps from
  later activity — **the gap report changes while the function object does not**.

Accepted synthesis, which is anchored's own recommended decomposition and census's own stated condition
for accepting its framing:

- **Function-anchored, identity-bearing.** Receipt discovery, receipt provenance, exact membership,
  build-time (frozen) support/reviewer annotations, reconstruction/export/evaluation. Bound to one
  `function_hash`.
- **Operation-centric, now-bearing.** Compile-blocked and compile-ready scopes, pending proposals,
  draft/verified/promoted/suspended/retired artifacts, explicit stale-revision anomalies. Bound to one
  read transaction's watermark.

Binding rule for u4b/u4c: the two anchors stay separately named and separately reported. Frozen build-time
counts and current-evidence counts never share a field name, and no surface subtracts one from the other.

Also settled by the anchored stale-revision probe: a stale-revision `verified` row is silently absent from
`inspect_function_promotion` (`entries=0, skipped=0`) because its SQL selects the current revision only,
yet the operation-centric census surfaces it with an explicit reason
(`"verified artifact belongs to stale operation revision 1; current revision is 2"`). This closes the
u3b1-carried observability asymmetry **in the reporting surface**; promotion planning itself stays silent
and that remains open.

## Decision 3 — u4 splits three ways: u4a → u4b → u4c

Two independent sources reached the same verdict. `map-m2u4.md` Q7 sized u4 as scoped (coverage/gap
report + receipt discovery + five CLI commands + offline eval, all mutation-grade) at **560–770 production
and 4,600–6,400 test lines**, against u3b2's landed 411 production + 3,225 tests which cost 90%
(216K/240K) — the warning line. anchored, from its own 881-line production prototype, independently
concluded "too large for a low-risk single implementation/review pass. If selected, receipt discovery,
coverage reporting, and CLI/export/eval should be separate implementation units."

A two-way cut was examined and rejected: discovery+report is already u3b2-sized before any CLI, and
discovery+CLI makes one teammate span `system.py`, `test_system.py`, `cli.py`, and `test_cli.py`, paying
both giant-surface contexts.

| unit | owns | write set | est. production / tests |
| --- | --- | --- | --- |
| u4a | receipt discovery/enumeration | `system.py`, `models.py`, `__init__.py`, `tests/test_system.py` | 100–160 / 900–1,400 |
| u4b | coverage + gap report core (both anchors) | `system.py`, `models.py`, `__init__.py`, `tests/test_system.py` | 280–360 / 2,200–2,800 |
| u4c | the five `function` CLI commands | `cli.py`, `tests/test_cli.py` | 180–250 / 1,500–2,200 |

Order `u4a → u4b → u4c` is sequential, not parallel: u4a and u4b edit the same `system.py` /
`test_system.py` surfaces. Semantic edges are u4a→u4c (show/export discovery) and u4b→u4c (show gaps);
u4a→u4b is the cheapest sequencing edge and leaves the CLI teammate working only in the small files.

## Decision 4 — u4a accepted surface (frozen)

```python
System.latest_function_receipt(partition: str, operation: str) -> FunctionReceipt

System.function_receipts(
    partition: str,
    operation: str,
    *,
    operation_revision: int | None = None,
    before_sequence: int | None = None,
    limit: int = 100,
) -> FunctionReceiptPage

@dataclass(frozen=True, slots=True)
class FunctionReceiptPage:
    receipts: tuple[FunctionReceipt, ...]
    next_before_sequence: int | None
```

Converged across both surviving spikes, both prototyped: name/signature of both methods and of the page
model; `sequence DESC` newest-first ordering; exclusive `before_sequence` cursor; `limit + 1` fetch to
decide continuation; `next_before_sequence` = the last returned receipt's sequence when more rows exist,
else `None`; empty result `((), None)`; every returned row validated through the existing
`_function_receipt_from_row` (scalar types/bounds, digest grammar, transition-count relationships, the
14-field ABI hash); a malformed row inside the selected page raises `IntegrityError` and is **never**
skipped; one `Store.transaction(write=False)`, no authority call, no event, no write, no persisted
identity. Discovery proves row-level receipt self-binding only — it does not reconstruct memberships, so a
listed receipt is not yet proof that its members/reports/tests reconstruct. Ordering keys on immutable
`function_receipts.sequence`, never `promoted_at_us`; anchored's probe deliberately gave sequence 1 a
timestamp of `5000000` with later sequences carrying much larger wall-clock values, and sequence stayed
authoritative.

Two MAIN corrections, both against repository convention rather than either spike:

1. **`limit` bound is `1..10_000`, not 1,000.** Every existing read method uses
   `_bounded_int(limit, "limit", minimum=1, maximum=10_000)` (`system.py:4168`, `system.py:4215`, and the
   `proposals`/`reports`/`events` analogs). anchored's 1,000 cap would introduce a second convention for
   no reason. Bounds are validated, never clamped — over-cap raises `ValidationError`. `before_sequence`,
   when not `None`, takes the existing cursor bound `minimum=0, maximum=2**63 - 1`; `before_sequence=0`
   legally yields an empty page. Probed at scale by census: a 10,001-receipt ledger paged 10,000 then 1,
   with an over-limit request rejected rather than clamped.
2. **`function_receipts` does not raise on an unknown operation; `latest_function_receipt` does.** The
   repository's line is whether the method needs the operation's *current* revision or policy. Pure
   enumeration scoped by `(partition, operation)` returns empty — `artifacts` (`system.py:4205-4231`) and
   `examples` (`system.py:4149-4180`) read no operations row and raise nothing. `latest_function_receipt`
   must resolve the current revision, so it reads the operations row and raises
   `NotFoundError("operation is not registered in this partition")`, the exact message used at
   `system.py:508`, `1553`, `2244`, `2667`, `3219`, `3882`, `3926`. Both spikes proposed `NotFoundError`
   on both methods; that would break the enumeration convention.

`latest_function_receipt` raises `NotFoundError` on two DISTINCT conditions carrying two DISTINCT
messages: an unregistered operation → the shared string above; a registered current revision holding no
receipt → `"current operation revision has no function receipt"`. Both are pinned separately. The
conditions are genuinely different and conflating them would discard diagnostic information; merged
messages also make a wrong-scope lookup harder to detect, since a mis-scoped query then fails
indistinguishably from an unregistered one. An earlier phrasing of this record read as requiring one
shared message for both, which produced a rejected review finding — the two-message form is normative.

`latest_function_receipt` returns `FunctionReceipt`, not `FunctionReconstruction` (anchored over census).
Reasons: it keeps discovery internally uniform, since census's own enumeration deliberately validates rows
without reconstructing, so having `latest_*` reconstruct contradicts its sibling; it keeps exactly one
meaning of "reconstruct" in the API (`reconstruct_function_receipt`); and it avoids paying up to a
50,000-membership reconstruction for what is a naming query. A caller wanting the document composes
`reconstruct_function_receipt(partition, latest_function_receipt(...).id)`. Implementation promotes the
existing private `_latest_function_receipt_row` (`system.py:1931-1945`) without changing its exact
`(partition, operation, operation_revision)` binding.

**No schema delta.** `function_receipts_scope (partition, operation, operation_revision, sequence)`
(`store.py:261`) supplies the equality prefix plus a backward range scan for
`WHERE ... [operation_revision = ?] AND sequence < ? ORDER BY sequence DESC LIMIT ?`; SQLite traverses the
ascending B-tree backward, so no `DESC` index is warranted. `store.py`, `cli.py`, and `function.py` stay
byte-identical.

## Recorded direction for u4b and u4c — evidence, not a freeze

Each unit settles its own vocabulary against its own consumer; these are the council's probe-backed
findings, carried so the work is not re-derived.

**u4b.** Blocked-scope reporting must factor the compiler's canonical-input enumeration plus
`_project_current_build` (`system.py:1428-1523`, `1541-1568`) into a helper callable inside the report's
read transaction; calling public `compile()` is disqualified as a write. Recompute the active scope by
both `input_hash` **and** canonical `input_json`. Integrity failures stay raised, never downgraded into a
friendly gap reason. Per-entry support/reviewer counts come from the sealed `artifacts.support` /
`artifacts.reviewer_count` columns (the frozen build snapshot); recomputing from current examples
over-counts later confirmations, filtering revocations under-counts the sealed snapshot, and counting
proposal confirmations misses challenge-origin evidence entirely (challenge examples carry
`proposal_id = NULL`). Promoted entry count must stay revision-unfiltered to match `verify_function`
semantics, so a stale promoted row is reported rather than hidden. Pending proposals must join
`requests` on **both** `partition` and `id` — the request PK is `(partition, id)`, so joining on
`request_id` alone leaks across partitions — and must not filter to the current revision, because
revision leaves already-pending proposals pending. Every category shares one read transaction; separate
calls observe different commits, which is exactly Decision 1's measured contradiction.

**u4c.** Offline eval: special-case exactly `function eval` ahead of the `--db`/`--partition` gate in
`_run` (`cli.py:195-207`), never make the globals generally optional; load the bundle through a bounded
reader capped at `FUNCTION_MAX_BYTES` with strict UTF-8, then `parse_function(..., expected_function_hash)`
and `evaluate`, so `System` is never constructed. Note `_input`'s 1 MiB stdin cap cannot carry a 64 MiB
bundle — bundle and eval input need separate channels. Export: default source = live promoted snapshot,
gated on `verify_function` P1–P6 passing (a failed verification raises `IntegrityError` → exit 5 rather
than exporting a diagnostic or stale document); `--receipt-id` selects the historical source and must
check the reconstructed receipt's operation against the positional operation. Export writes
`FunctionDocument.text` bytes exactly — no `_emit`, which JSON-quotes, escapes, and reindents, and whose
`asdict` on a `FunctionDocument` deep-copies value + duplicate canonical text + private `_FunctionCase`
caches; with `--out PATH` write the bytes to the path and emit only JSON metadata to stdout rather than
duplicating up to 64 MiB. `function verify` must make an explicit tested exit-code choice, since generic
`main` returns 0 for any returned dataclass and `FunctionVerification(passed=False)` would otherwise print
failure and exit 0. Nested dispatch must not route the existing per-artifact root `verify`/`promote`
(`cli.py:98-105`) to the function-set APIs. Keep `show`/`export`/`verify`/`promote` from silently swapping
the three distinct identities — current committed snapshot (`verify_function`), prospective union
(`inspect_function_promotion`), immutable historical receipt (`reconstruct_function_receipt`); exporting
inspect output would publish unpromoted candidates.

## Required test construction

Binding rules from `.agent/memory.md`, each of which cost a prior unit a real defect:

- Mutation criterion binds every added check: some committed test fails when that check's logic alone is
  deleted.
- Set/loop-quantified checks corrupt the **middle AND the last** of ≥3 elements; middle-only probes left
  8 separate u3b2 checks with every last-row mutant alive.
- Enumeration completeness needs a tail sentinel past any plausible `LIMIT` — `LIMIT 1000` on two u3b1
  queries left all 208 tests green.
- Vary fixtures across every boundary a check depends on, and drive at least one integer ≥10; integers
  below 10 make base-10 and hex framing identical.
- Read-only claims need a full `iterdump()`/schema comparison or a write-denying SQLite authorizer; row
  counts are insufficient, because `Store.transaction(write=False)` is deferred `BEGIN`, not
  `PRAGMA query_only`.
- Mutation harnesses purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`, and prove the mutant reached
  the interpreter; target by line plus an asserted anchor string, never by occurrence index.

u4a's own mutation obligations, enumerated by anchored: current-revision latest lookup; all-revision vs
exact-revision filtering; descending order; exclusive cursor; first/middle/last receipts; the 10,000 and
10,001 limit boundaries; cross-operation and cross-partition isolation; empty current revision; corrupt
receipt-row hashes; page continuation at exactly `limit` vs `limit + 1`.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root.
