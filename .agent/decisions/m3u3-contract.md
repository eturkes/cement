# M3.3 acceptance contract - request-free submission over unchanged schema v2

Every downstream artifact decides against this document: the diff-blind red suite, the independent
oracle, the differential probes, both reviewers, and MAIN's own implementation. A disagreement with
the code is a defect in one of them, never a difference of opinion.

Sections 12 and 13 are PENDING until the verdict table and the review dispositions exist.

## 1. Scope

M3.3 adds request-free proposal submission beside the existing request lifecycle. Two paths ship:
DIRECT, where the caller supplies the candidate, and SOURCE-BACKED, where Cement invokes the
configured `CandidateSource`. `System.resolve`, shipped by M3.2b, already answers the read side.

IN SCOPE: `System.submit_proposal`, `System.propose`, the private persistence seam both share,
`CandidateSourceError`'s public contract and docstring in `src/cement_runtime/errors.py`, the
`tests/test_read_capability_battery.py` census update the new transaction sites force, and the
normative prose that publishes the new surface.

OUT OF SCOPE, each owned by a named later unit. `handle`, `request_status`, `get_proposal`,
`proposal`, `proposals`, `review`, `function_report` and every `Outcome` member keep working
UNCHANGED; M3.5b and M3.6a delete them. `SCHEMA_VERSION` stays 2 and no schema byte changes; M3.6b
cuts to 3. The CLI is untouched; M3.5a adds its channels. `CommandCandidateSource`,
`_command_supervisor.py` and `example_adapter.py` stay byte-stable; M3.7 relocates them. The hospital
demo keeps calling `handle`; M3.5b and the M3 example unit rewrite it.

Deleting anything is out of scope. M3.3 adds beside.

## 2. Frozen public shape - RULED

```python
def submit_proposal(
    self,
    partition: str,
    operation: str,
    input_value: object,
    *,
    candidate: Candidate,
) -> str: ...

def propose(
    self,
    partition: str,
    operation: str,
    input_value: object,
) -> str: ...
```

- P01. TWO methods, not one. `candidate` is keyword-only and REQUIRED on `submit_proposal`.
  `propose` accepts no candidate and no source keyword. Section 10 rules the fork.
- P02. Both return the proposal ID as a bare `str`. No new model, no reuse of `ReviewRequired` or
  `ProposalView`: both of those carry `request_id`, which section 8 forbids this API from publishing.
- P03. `submit_proposal` NEVER invokes a source. A configured `self.candidate_source` whose `propose`
  raises must not affect it.
- P04. `propose` invokes `self.candidate_source` and nothing else. There is no per-call source
  argument; section 10 rules why.
- P05. Both names are exported from `cement_runtime` only through `System`; `__init__.py` gains no
  new symbol. `Candidate` is already exported.
- P06. Both methods are added beside `handle`. The `handle` bytes stay identical to `1182130a2b3a`
  (12,866 B by AST slice without the trailing newline), as they have been since `3b7769b`.

## 3. The two submission paths - the unit's headline predicates

- D01. SUCCESS FOOTPRINT, identical for both paths after generated-ID normalization: exactly one new
  `requests` row, exactly one new `proposals` row, exactly one new `events` row. No other table
  changes.
- D02. The request row is written DIRECTLY as `status='pending'` with `proposal_id` set,
  `lease_owner IS NULL`, `lease_until_us IS NULL`, `attempts=1`. The schema v2 CHECK constraint
  already admits exactly this shape. No `generating` state is ever reserved, so no lease exists to
  expire, take over, or fence.
- D03. The event is `proposal.created`. Its payload and subject match what `handle`'s proposal write
  emits today, MINUS any request identity - see section 8.
- D04. Neither method accepts a caller-supplied identifier of any kind. Submitting byte-identical
  content twice produces two request rows, two proposal rows, two events and two distinct proposal
  IDs. Cement offers NO idempotency, and no returned value may be mistaken for an idempotency token.
- D05. `propose` invokes the source EXACTLY ONCE per successful call, and exactly zero times on every
  path that raises before invocation.
- D06. Both paths route through ONE private persistence seam. The seam is the single writer of the
  request row, the proposal row and the event, and its behaviour is identical whichever public method
  entered it.

## 4. Argument validation precedence - RULED

- D07. Argument validation runs BEFORE any ledger read and before any source invocation, in this
  order: `partition`, `operation`, `input_value` canonicalization, then `candidate` on the DIRECT
  path.
- D08. A bad `partition` together with a bad `input_value` reports the PARTITION error. Both spikes
  measured this on both alternatives; it matches `resolve`'s ruled precedence in
  `m3u2b-contract.md` section 4.
- D09. A rejected call performs ZERO transactions and ZERO source invocations. The obligation is
  measured with live spies proved on a positive control, never by a bare zero count.
- D10. Omitting `candidate` on `submit_proposal` raises Python's own missing-keyword-only
  `TypeError`. Passing `source=` to either method raises Python's own unexpected-keyword `TypeError`.
  M3.3 writes no validator for either: the signature is the check. A test may pin the exact text
  Python produces, but no shipped code may construct it.

## 5. Source-invocation obligations

- D11. The source runs OUTSIDE every open transaction. No Cement-held connection reports
  `in_transaction is True` while `CandidateSource.propose` executes. This preserves today's boundary
  at `system.py:758`.
- D12. The operation revision is read BEFORE invocation and RE-READ inside the write transaction. If
  it changed, the call raises and writes nothing.
- D13. The revision re-read uses a SCOPED query for the one operation by partition and name. Reusing
  `System.operations()` is REJECTED: it materializes and parses every operation in the partition to
  hide one static read site, which inverts the purpose of the census in section 9.
- D14. `propose` hands the source a `CandidateRequest` carrying the generated internal request ID.
  The field stays in the protocol for M3.3 and is TRANSITIONAL; M3.5b removes it together with the
  request lifecycle. `_command_supervisor.py` forwards opaque bytes and `example_adapter.py` reads
  only `input`, so neither changes.

## 6. Purity and containment obligations - each pinned independently

- D15. A failed submission leaves the ledger byte-identical. Four INDEPENDENT pins, never one
  aggregate assertion: `requests` and `proposals` row counts, the event count and the event sequence
  counter, the ledger file's sha256, and the full `tuple(connection.iterdump())` text.
- D16. Zero `commit()` calls occur on any failure path, measured through a `sqlite3.Connection`
  subclass injected as the connect `factory`, with a write-transaction positive control proving the
  spy live. This mirrors M3.2b's B35.
- D17. Neither method reads the clock except through `self._now`, and neither consults the artifact,
  example, function-receipt or membership tables. Submission records a proposal; it does not resolve.

## 7. Error classification - exact texts RULED

Every text below is published HERE, not merely asserted in a test. A test pins what this section
states.

| condition | class | exact message |
|---|---|---|
| source raises `CandidateSourceError` | `CandidateSourceError` | `candidate source failed` |
| source raises any other `Exception` | `CandidateSourceError` | `candidate source failed` |
| `propose` with `self.candidate_source is None` | `StateError` | `candidate source is not configured` |
| operation revision changed across generation | `StateError` | `operation revision changed before proposal submission` |
| operation absent from the partition | `NotFoundError` | `operation is not registered in this partition` |
| rejected `partition`, `operation`, or `input_value` | `ValidationError` | the existing `_name` and canonicalization texts, unchanged |

- D18. Both source-failure rows raise `from None`. The adapter's class, message, cause, context and
  traceback frames must not reach the caller, the message, the repr, or any event. Both spikes
  measured a planted secret absent from all of them.
- D19. The two source-failure rows are INDISTINGUISHABLE to the caller. A caller must not be able to
  learn whether the adapter raised the declared error or an arbitrary one.
- D20. Failure raises. It never returns a value, and it never writes the `request.fallback_failed`
  event or a `failed` request row - those belong to `handle`, which keeps them.
- D21. `NotFoundError` for an unregistered operation is raised BEFORE the source is invoked, measured
  with a live counter.

## 8. The private request row - TRANSITIONAL, never opaque

The `proposals` table carries `UNIQUE (partition, request_id)` and
`FOREIGN KEY (partition, request_id) REFERENCES requests(partition, id)`, so under unchanged schema
v2 no proposal can exist without a request row. M3.3 therefore generates one internally.

- D22. Neither return value nor the `proposal.created` event publishes that identifier.
- D23. M3.3 MUST NOT claim the identifier is private, hidden or opaque. EIGHT live seams still expose
  it, and the contract publishes the list rather than the claim: `CandidateRequest.request_id` handed
  to the source, `handle`, `request_status`, `get_proposal`, `proposal`, `proposals`,
  `function_report` (through `PendingProposalGap`), and `review`. The returned proposal ID makes
  `get_proposal` an immediate discovery path.
- D24. "Private" in M3.3 means one thing only: a STORAGE ROLE that the new API neither accepts nor
  returns. M3.4 owns removing the projections; only then may opacity be claimed.
- D25. Prose obligation. No shipped sentence may state or imply that M3.3 removed request identity.
  Section 11 carries the wording.

## 9. Gate identity and battery obligations

- D26. Decisive gate: `PYTHONDONTWRITEBYTECODE=1 uv run -q python -m unittest discover -s tests -t .`
  It must reach 635 + N tests with zero failures, N = the tests M3.3 adds.
- D27. `test_b20_read_site_census_has_no_mutations` asserts EXACT counts at
  `tests/test_read_capability_battery.py:869-872`: 17 read sites, 15 write sites, 12 reached helpers,
  and `violations == []`. M3.3's new transaction sites break the first two. The counts are a
  TRIPWIRE that forces deliberate acknowledgement of every new site, not an invariant that the totals
  never grow; `violations == []` is the load-bearing assertion.
- D28. M3.3 UPDATES those counts to the numbers its ruled design actually produces, in the same
  commit that adds the sites, and the implementation records each new site by method name. Contorting
  production code to hold the old totals is a defect, not a pass - see D13.
- D29. `violations == []` and the reached-helper discipline stay untouched. A new site that cannot
  bind a simple connection name is a defect in the implementation.
- D30. Closure is mechanical: the full gate green, the battery grader reporting every obligation
  filled, and a mutation sweep over the added predicates. A green suite alone never closes this unit.

## 10. Fork ruling - two methods versus one XOR signature

RULED: TWO METHODS. Both spikes recommend it, including `spike-m3u3-xor`, which was built to defend
the single-signature alternative. Two independent lenses converging satisfies the council rule.

Measured grounds, from `m3u3-spike-split.json` and `m3u3-spike-xor.json`:

1. Illegal states are unrepresentable. XOR makes `candidate=None, source=None` and both-supplied
   representable, so it must ship a runtime validator, an exact message and a four-row precedence
   table that two methods never need. Python arity rejects both states first.
2. Authority is visible at the call site. `submit_proposal(..., candidate=...)` says the caller
   generated the content; `propose(...)` says Cement invokes generation. One verb hides two effect
   profiles: persistence-only against arbitrary adapter execution that can fail before persistence.
3. XOR's per-call `source=` SPLITS source ownership, measured: with a configured source and a
   per-call source, the configured one recorded 0 calls and the supplied one 1, while legacy `handle`
   recorded 1 on the same System - so configuration silently stops applying to the new path. Under
   XOR, omitting both keywords is an error EVEN WHEN a source is configured. M3.7 has to relocate
   source machinery; a second ownership path is a liability it would inherit.
4. `split` reached a full green gate; `xor` reached 634/635 and reported the census incompatibility
   it could not resolve within its brief.

Point 4 is evidence of implementability, NOT of correctness: `split` bought its green run with the
`operations()` reuse that D13 now rejects. Both alternatives face the same census update, and D28
governs both.

REJECTED ALTERNATIVES, recorded so they are not relitigated. One XOR method: above. A trivial
source wrapping a direct candidate, so one path serves both: it would force caller-supplied output
through the source-failure normalization of section 7 and destroy the P03/D05 separation. Reusing
`ReviewRequired` or `ProposalView` as the result: both carry `request_id`, which D22 forbids. A new
frozen result model: it adds a nominal type over `str` without adding forced behaviour, and M3.4 is
the unit that will know which fields it needs.

## 11. Normative claims - obligation without prose rewrite

- D31. The `CandidateSourceError` docstring at `errors.py:28` currently reads "The supervised
  fallback source failed before creating a proposal." M3.3 rewrites it: the error belongs to explicit
  submission, and nothing about it is a fallback.
- D32. Both new methods carry docstrings that state, in the project's human-facing register: what is
  persisted, that no idempotency exists (D04), that `propose` executes caller-supplied adapter code
  outside any transaction (D11), and the exact error each raises.
- D33. No shipped sentence may call submission cheap, safe-to-retry, deduplicated, or request-free in
  the sense of D25. `resolve`'s cost precedent applies: state the price, do not imply one.
- D34. README, `docs/architecture.md` and `docs/threat-model.md` are checked for sentences the new
  surface falsifies. A sentence that becomes false is corrected in this unit even when the code is
  correct; M3.2b found six consecutive units whose only defects were claim defects.

## 12. Verdict table - MAIN-final

Row-by-row rulings live in `m3u3-verdicts.json`, MAIN-owned columns `main_verdict` and
`contract_action`. This section carries only the rulings that bind CODE, ruled at implementation
time from the first 36 filled rows. The remaining rows are ruled at battery close.

ONE RULING CHANGED THE SHIPPED CODE.

- V-D12. The pre-read/re-read revision guard belongs to `propose` ALONE. MAIN's first implementation
  gave both paths `_submission_revision` then a seam re-read, for symmetry. That is a defect: a
  direct caller captures no revision, so a `revise_operation` landing between the two reads produced
  `StateError("operation revision changed before proposal submission")` for a submission with no
  generation window to protect - a failure mode the caller cannot have earned. SHIPPED: the seam
  takes `expected_revision: int | None`, reads the current revision under the write lock, and
  compares only when the caller supplied an expectation. `submit_proposal` passes `None` and opens
  exactly ONE transaction; `propose` passes its pre-read revision and keeps the two-read guard.
  Section 5's D12 is hereby scoped to the source path. Pins:
  `test_a_revised_operation_still_accepts_a_direct_submission` and the transaction-count control in
  `test_a_rejected_call_opens_no_transaction_and_invokes_no_source`.

RULINGS THAT CONFIRMED THE SHIPPED READING, each already pinned.

- V-D18. `raise ... from None` INSIDE an `except` block leaves `__context__` populated with the
  adapter's exception, so reading A of D18 fails its own prohibition. The seam raises OUTSIDE the
  handler, where `__context__` is genuinely `None`, and keeps `from None` so both readings hold.
- V-D06. "ONE private persistence seam" is structural, not behavioural: three shared row-level
  helpers produce an identical footprint. `_persist_proposal` contains all three writes and is the
  only writer, pinned by call-graph spy rather than by footprint alone.
- V-D07. The four-item order is a total order needing one probe per ADJACENT edge. D08's
  partition-versus-input pair SPANS two edges and pins neither interior one. Three adjacent probes
  ship, plus two for `propose`'s configured-source slot.
- V-D11. Reading B: no Cement-held connection may be IN A TRANSACTION while the source runs. Idle
  open connections are permitted; the shipped pin observes every connection Cement opens and carries
  a positive control.
- V-D17. The clock source is mandatory and the call count is not, but one `self._now` inside the
  write transaction, shared by all three rows, is what ships - the M3.1 ruling that a clock read
  ahead of the authoritative plan can commit a row older than its own build.
- V-P03/V-P04. `submit_proposal` neither reads nor validates `self.candidate_source`. `propose`
  snapshots the attribute once, so its `None` check and its single invocation bind the same object.
- V-D13. Row scope is mandatory, column projection is not. `SELECT revision` ships because it is the
  only consumed value.

CONTRACT CORRECTIONS, no code effect.

- V-D01. The footprint quantifies over Cement's declared SCHEMA tables. `events.sequence` is
  AUTOINCREMENT, so every success necessarily mutates `sqlite_sequence`; a reading covering every
  SQLite table is unsatisfiable.
- V-D09. "A rejected call" means a call rejected by ARGUMENT VALIDATION. Read wider it contradicts
  D12's read transaction, D21's lookup, and any failure after one source invocation.
- V-D16. Zero commits is scoped to failures occurring BEFORE commit. A `commit()` that itself raises
  is one invocation and no reading can forbid it.
- V-D19. Indistinguishability is scoped to observations THROUGH the raised Cement exception - class,
  message, repr, cause, context, frames. The caller owns the adapter and can always instrument it.
- V-D22. "Publishes" is channel-local: the return value and the event. D23's `get_proposal` route is
  transitive discovery and is not a violation.
- V-D23. Eight NAMED high-level seams in the union, not an exhaustive security count and not eight
  per path - the DIRECT path never constructs a `CandidateRequest`. Authorized ledger access exposes
  every storage identifier by design.
- V-D26. 635 + N DISCOVERED tests, zero failures, zero errors, and zero skips among the tests M3.3
  adds. A skipped test increments the count and still prints OK.
- V-P02/V-P05. `type(result) is str`, not a `str` subclass. Neither name appears in `__all__` nor as
  a module attribute; both are reachable only as `System` methods.

HISTORY CORRECTION. `m3u3-map.json` row S01 states that M3.3 removes `CandidateRequest.request_id`.
That is STALE and contradicts D14, which retains the field as transitional until M3.5b. This
contract governs; the map row is superseded, not followed.

MEASUREMENT. P06 is verified mechanically, and the contract's own numbers reproduce exactly under
one stated convention: the whole-line span from `node.lineno` to `node.end_lineno` with trailing
newlines stripped gives 12,866 B / `1182130a2b3a`, byte-identical to `3b7769b`. A column-offset AST
slice (`ast.get_source_segment`) drops the four-space indent and measures 12,862 B / `c27e71b0b4c7`;
"AST slice" alone is ambiguous by exactly those four bytes, so the pin states its convention.

## 13. Review dispositions and differential result

PENDING. Records the contract attack, the oracle's probe agreement, the differential result, the
post-implementation review with one MAIN disposition per finding, and any history correction.
