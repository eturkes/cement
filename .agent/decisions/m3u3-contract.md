# M3.3 acceptance contract - explicit proposal submission over a retained schema-v2 request row

Every downstream artifact decides against this document: the diff-blind red suite, the independent
oracle, the differential probes, both reviewers, and MAIN's own implementation. A disagreement with
the code is a defect in one of them, never a difference of opinion.

Sections 12 and 13 are COMPLETE: all 58 verdict rows, all 24 attack rows, all 34 differential rows
and all 22 review rows are ruled. Six review findings are ruled CARRIED, with their acceptance checks
stated verbatim; they are S4's whole job.

## 1. Scope

M3.3 adds explicit proposal submission beside the existing request lifecycle. Two paths ship:
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

FREEZE PINS, because "unchanged" and "byte-stable" above are obligations and not prose. The
unit-entry baseline is `f9b9755`; a byte claim measured against any earlier commit is meaningless,
and `cli.py` compared to an M2-era tip shows a false DIFF that is entirely M2.4 work.

- B01. `SCHEMA_VERSION == 2`, `SCHEMA` is 14,580 bytes with sha256
  `5be3d79fe1e21aca524f3937c8ce78521bcc7203bfe20b7352ef4b6dff468a77`, and `SCHEMA_FINGERPRINT`
  equals that digest. Version equality alone admits a whitespace DDL edit, so byte identity carries
  the obligation.
- B02. `src/cement_runtime/cli.py`, `src/cement_runtime/_command_supervisor.py` and
  `src/cement_runtime/example_adapter.py` are byte-identical to `f9b9755` at unit close. The
  remaining legacy methods and `Outcome` members are pinned behaviourally, not by byte, because
  M3.3 may not refactor their code but never claimed their files frozen.

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
- P04. `self.candidate_source` is `propose`'s ONLY candidate authority. "Nothing else" scopes to
  GENERATION: no per-call source argument, no fallback source, no second attribute read. Argument
  validation, the revision read, `self._now` and persistence are the call's own work and are
  required on every successful call. Section 10 rules why no per-call source exists.
- P05. Both names are exported from `cement_runtime` only through `System`; `__init__.py` gains no
  new symbol. `Candidate` is already exported.
- P06. Both methods are added beside `handle`. The `handle` bytes stay identical to `1182130a2b3a`
  (12,866 B), as they have been since `3b7769b`. CONVENTION IS PART OF THE PIN. THREE slicing
  conventions measure the same unchanged source and produce three different answers, so "AST slice"
  alone names three claims and a correct `handle` can appear to fail under two of them:

  | convention | bytes | sha256 prefix |
  |---|---|---|
  | whole-line span `lineno`..`end_lineno`, trailing newlines STRIPPED - THE PIN | 12,866 | `1182130a2b3a` |
  | whole-line span, trailing newline KEPT | 12,867 | `cd60036faf5c` |
  | `ast.get_source_segment`, which drops the four-space indent | 12,862 | `c27e71b0b4c7` |

  The pin is row one. Any measurement of P06 states which row it used.

## 3. The two submission paths - the unit's headline predicates

- D01. SUCCESS FOOTPRINT, identical for both paths after generated-ID normalization: exactly one new
  `requests` row, exactly one new `proposals` row, exactly one new `events` row. No other table
  changes.
- D02. The request row is written DIRECTLY as `status='pending'` with `proposal_id` set,
  `lease_owner IS NULL`, `lease_until_us IS NULL`, `attempts=1`. The schema v2 CHECK constraint
  ADMITS this shape; it does not enforce it, and it also accepts a `pending` row with `attempts > 1`,
  so `attempts == 1` is pinned by test and never inferred from the schema. No `generating` state is ever reserved, so no lease exists to
  expire, take over, or fence.
- D03. The event is `proposal.created`. Its payload and subject match what `handle`'s proposal write
  emits today, MINUS any request identity - see section 8.
- D42. THE PROPOSAL ROW SHAPE, normative, because D01 counted the row without specifying it. The
  seam writes `id` (a fresh `prop_`-prefixed ID), `partition`, `request_id` bound to the request row
  written in the same transaction, `proposed_output_json`/`proposed_output_hash` from canonicalizing
  the candidate output, `provenance_json`/`provenance_hash` from canonicalizing the provenance
  mapping, `status='pending'`, `created_at_us` equal to the request row's and the event's, and
  `status_sequence` equal to the `proposal.created` event's own `sequence`. Every remaining column
  takes its schema-v2 default, so the review fields are NULL and the row is indistinguishable from a
  `handle`-created pending proposal except through its request row.
- D04. Cement alone mints ROW IDENTITY. Neither signature accepts a caller-supplied request ID,
  proposal ID, or idempotency key. SCOPE, because "identifier of any kind" is false read literally:
  `partition` and `operation` are caller-supplied identifiers by design, and `input_value`, the
  candidate output and the provenance may all carry domain identifiers Cement stores verbatim. The
  ban covers ledger row identity and deduplication keys only. Submitting byte-identical content
  twice produces two request rows, two proposal rows, two events and two distinct proposal IDs.
  Cement offers NO idempotency; treat the returned proposal ID as a handle to one new row.
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
  `m3u2b-contract.md` section 4. SAMPLE ONLY: that pair SPANS two edges of D07's order and pins
  neither interior one, so D07's three adjacent probes carry the obligation and D08 rides along.
- D09. A rejected call performs ZERO transactions and ZERO source invocations. The obligation is
  measured with live spies proved on a positive control, never by a bare zero count.
- D10. Omitting `candidate` on `submit_proposal` raises Python's own missing-keyword-only
  `TypeError`. Passing `source=` to either method raises Python's own unexpected-keyword `TypeError`.
  M3.3 writes no validator for either: the signature is the check. A test may pin the exact text
  Python produces, but no shipped code may construct it.

## 5. Source-invocation obligations

- D11. The source runs OUTSIDE every transaction THE SUBMISSION CALL HOLDS. Every connection the
  call itself opens reports `in_transaction is False` while `CandidateSource.propose` executes, and
  the pin observes exactly those connections with a positive control. SCOPE: a source that reenters
  the same `System` and opens its own transaction makes a Cement-held connection report
  `in_transaction is True`, which no library can prevent and which the caller chose. The obligation
  is that submission never holds the lock across adapter code. This preserves today's boundary at
  `system.py:758`.
- D12. SOURCE PATH ONLY. `propose` reads the operation revision BEFORE invocation and RE-READ inside
  the write transaction; if it changed across generation, the call raises and writes nothing. The
  guard protects a GENERATION WINDOW, so it has no direct-path meaning: `submit_proposal` captures
  no revision, validates the operation once inside its single write transaction, and binds whatever
  revision is current under that lock. Imposing the two-read guard on the direct path manufactures a
  failure its caller cannot have earned. Section 12 V-D12 records the code change this ruling forced.
- D13. The revision re-read uses a SCOPED query for the one operation by partition and name. Reusing
  `System.operations()` is REJECTED: it materializes and parses every operation in the partition to
  hide one static read site, which inverts the purpose of the census in section 9.
- D14. `propose` hands the source a `CandidateRequest` carrying the generated internal request ID.
  The field stays in the protocol for M3.3 and is TRANSITIONAL; M3.5b removes it together with the
  request lifecycle. `_command_supervisor.py` forwards opaque bytes and `example_adapter.py` reads
  only `input`, so neither changes.
- D35. PRECEDENCE, four steps, total: arguments, then `candidate_source is None`, then the operation
  lookup, then invocation. Missing configuration therefore costs ZERO transactions even when the
  operation is also unregistered - the split spike measured that, and reading the ledger first would
  buy a `NotFoundError` the caller cannot act on while unconfigured.
- D36. `propose` SNAPSHOTS `self.candidate_source` into one local before the `None` check, so the
  check and the single invocation bind the same object. Reassignment during the call cannot split
  them, and no second attribute read exists to invoke a different source.
- D37. Unusable non-`None` configuration is CONTAINED, not pre-validated, AT EVERY SITE INCLUDING
  `System.__init__`. A missing `propose` attribute, a non-callable `propose`, and a descriptor that
  raises all normalize to `CandidateSourceError`, exactly like a raised or malformed source result.
  No `callable()` pre-flight ships: it is unsound under descriptors and `__getattr__`, it duplicates
  the failure the invocation itself produces, and testing a descriptor means EXECUTING it - which is
  the case whose exception can carry a secret. Only `None` gets its own published error, because only
  `None` is unambiguously "not configured" rather than "configured wrong". Footprint stays zero.
  RULED BEHAVIOUR CHANGE, carried by this unit. `System.__init__` shipped
  `callable(getattr(candidate_source, "propose", None))` from `3b7769b` and raised
  `ValidationError("candidate_source must provide a callable propose method")`. The battery, reading
  D37 alone, drove a raising descriptor through construction and read the planted secret out of the
  traceback: the pre-flight IS the hazard D37's grounds name, and it made D37 false while it shipped.
  It is DELETED. `System(database, candidate_source=<unusable>)` now constructs, and the first
  `propose` raises `CandidateSourceError`. `handle` already contained the same failures, so no route
  loses a check; the construction-time `ValidationError` is the sole observable loss, and buying
  fail-fast ergonomics with an unsound check that executes caller code at construction is the wrong
  trade. `tests/test_system.py` records the change where the old assertion stood.

## 6. Purity and containment obligations - each pinned independently

- D15. A failed submission causes ZERO ledger mutation of its own. Four INDEPENDENT pins, never one
  aggregate assertion: `requests` and `proposals` row counts, the event count and the event sequence
  counter, the ledger file's sha256, and the full `tuple(connection.iterdump())` text.
  DOMAIN, and the wording is load-bearing: the source runs outside every Cement transaction and may
  itself write to the same ledger, which the revision-race fixture does deliberately through
  `revise_operation`. Byte identity therefore compares the ledger AFTER any such injected commit
  against the ledger after the rejected submission returns - never call entry against call exit.
- D16. Zero `commit()` calls occur on every failure that arises BEFORE commit, measured through a
  `sqlite3.Connection` subclass injected as the connect `factory`, with a write-transaction positive
  control proving the spy live. This mirrors M3.2b's B35. A `commit()` that itself raises is one
  invocation and no reading forbids it; the obligation is that no failure reaches commit.
- D17. Neither method reads the clock except through `self._now`, and neither consults the artifact,
  example, function-receipt or membership tables. Submission records a proposal; it does not resolve.
  FORCING INSTRUMENT, required because row, file, dump and commit pins all pass while a forbidden
  table is read: a `sqlite3.Connection` subclass recording every executed statement, asserted to
  name none of the forbidden tables on either path, with the recorded list non-empty as its own
  positive control. One `self._now` call inside the write transaction serves all three rows.

## 7. Error classification - submission-domain texts RULED

Every text below is published HERE, not merely asserted in a test. A test pins what this section
states.

DOMAIN. This table is the SUBMISSION-DOMAIN taxonomy, not an exhaustive public error list. Both
methods additionally inherit, unchanged and unrespecified by M3.3, the clock and `Store` failures
already reachable through `self._now` and `store.transaction` - `StateError` and `IntegrityError`
with their existing texts. Claiming completeness while those stay unlisted is the only error here;
adding them to M3.3's scope is not.

| condition | class | exact message |
|---|---|---|
| source raises `CandidateSourceError` | `CandidateSourceError` | `candidate source failed` |
| source raises any other `Exception` | `CandidateSourceError` | `candidate source failed` |
| source RETURNS an unusable candidate | `CandidateSourceError` | `candidate source failed` |
| `propose` with `self.candidate_source is None` | `StateError` | `candidate source is not configured` |
| operation revision changed across generation | `StateError` | `operation revision changed before proposal submission` |
| operation absent from the partition | `NotFoundError` | `operation is not registered in this partition` |
| rejected `partition`, `operation`, or `input_value` | `ValidationError` | the existing `_name` and canonicalization texts, unchanged |
| `candidate` is not a `Candidate` (DIRECT) | `ValidationError` | `candidate must be a Candidate` |
| `candidate.provenance` is not a `Mapping` (DIRECT) | `ValidationError` | `candidate provenance must be a mapping` |
| `candidate.output` or provenance fails canonicalization (DIRECT) | `ValidationError` | the existing canonicalization texts, unchanged |
| canonical provenance exceeds 65,536 bytes (DIRECT) | `ValidationError` | `canonical JSON exceeds 65536 bytes` |

- D43. THE CANDIDATE DOMAIN, published as a type test. `candidate` is accepted when
  `type(candidate) is Candidate`; a SUBCLASS is rejected with the same text, because a subclass may
  reimplement `output` or `provenance` as a descriptor and a type test is the only check that reads
  no caller code. `candidate.provenance` is accepted when it is a
  `collections.abc.Mapping` instance. A list of pairs, a generator of pairs, and any other iterable
  of pairs are REJECTED: `dict()` alone accepts all three, which admits a one-shot iterator whose
  drain the caller cannot observe. The pin covers both paths - `ValidationError` direct,
  `CandidateSourceError` source.
- D44. THE PROVENANCE BOUND, published as a number. Provenance canonicalizes under
  `max_bytes=65_536`; `output` canonicalizes under the module default. The bound is the same figure
  `source.py` and `cli.py` already apply to provenance, so the three submission routes agree. Both
  bounds ship pinned, because an unpinned limit is a limit a later edit can drop silently.

- D38. THE RETURN ROW. Candidate validation on the SOURCE path runs inside the same containment
  boundary as invocation, outside every transaction. A non-`Candidate` return, an unusable
  `output`, a non-`Mapping` provenance, an oversized provenance, and a provenance `Mapping` whose
  own access raises are all adapter failures. Containment must not depend on whether the adapter
  raised or returned - a `Mapping` whose `__iter__` raises with a secret is the case that settles
  it. THE ACCESS PATH IS NAMED, because a settling case off the path settles nothing: `dict(Mapping)`
  reads `keys()` and `__getitem__`, so `items()` is never called and a `Mapping` whose `items` raises
  submits normally. The DIRECT path keeps the `ValidationError` rows above for the shapes those rows
  name, and otherwise lets the caller's own exception reach the caller UNCHANGED: there the object is
  the CALLER'S argument, and rewriting their `RuntimeError` into `candidate provenance must be a
  mapping` would misdescribe an object that is a mapping.
- D39. THE `BaseException` BOUNDARY. The catch is exactly `Exception`. `KeyboardInterrupt`,
  `SystemExit`, `GeneratorExit` and cancellation propagate UNCHANGED, because swallowing process
  control costs more than the containment it would buy. Footprint on that path is still zero;
  nothing is written before the persistence seam.
- D18. Both source-failure rows raise `from None`. The adapter's class, message, cause, context and
  traceback frames must not reach the caller, the message, the repr, or any event. Both spikes
  measured a planted secret absent from all of them.
- D19. The two source-failure rows are INDISTINGUISHABLE to the caller. A caller must not be able to
  learn whether the adapter raised the declared error or an arbitrary one.
- D20. Failure raises. It never returns a value, and it never writes the `request.fallback_failed`
  event or a `failed` request row - those belong to `handle`, which keeps them.
- D21. `NotFoundError` for an unregistered operation is raised BEFORE the source is invoked, measured
  with a live counter. It does NOT precede the missing-configuration check: with
  `candidate_source is None` AND an unregistered operation, `propose` raises the D35/T03 `StateError`
  having opened zero transactions.

## 8. The private request row - TRANSITIONAL, never opaque

The `proposals` table carries `UNIQUE (partition, request_id)` and
`FOREIGN KEY (partition, request_id) REFERENCES requests(partition, id)`, so under unchanged schema
v2 no proposal can exist without a request row. M3.3 therefore generates one internally.

- D22. Neither return value nor the `proposal.created` event publishes that identifier.
- D23. M3.3 states WHERE the identifier stays visible, and publishes the list in place of a privacy
  claim. EIGHT live seams expose it: `CandidateRequest.request_id` handed
  to the source, `handle`, `request_status`, `get_proposal`, `proposal`, `proposals`,
  `function_report` (through `PendingProposalGap`), and `review`. The returned proposal ID makes
  `get_proposal` an immediate discovery path.
- D24. "Private" in M3.3 means one thing only: a STORAGE ROLE that the new API neither accepts nor
  returns. M3.4 owns removing the projections; only then may opacity be claimed.
- D25. Prose obligation, stated positively. Every shipped sentence touching request identity says
  that schema v2 RETAINS the row and that the existing request and proposal readers still show its
  ID. A method-scoped absence claim - "the two signatures neither accept nor return it" - ships only
  inside that pairing. Section 11 carries the wording.
- D40. ONE canonical snapshot serves the whole call. `CandidateRequest.input` receives the
  canonicalizer's DETACHED structure, and persistence reuses the `text` and `digest` computed before
  invocation. An adapter that mutates `request.input` therefore changes neither the stored bytes nor
  the caller's object, and the stored input can never be adapter-influenced data. The remaining
  fields carry the normalized partition and operation, the pre-invocation revision, and the
  generated internal request ID.

## 9. Gate identity and battery obligations

- D26. Decisive gate: `PYTHONDONTWRITEBYTECODE=1 uv run -q python -m unittest discover -s tests -t .`
  It must reach 635 + N tests with zero failures, N = the tests M3.3 adds. Zero errors and zero
  SKIPS among the added tests, because a skipped test increments the count and still prints OK.
  MEASURED at implementation close: 668 tests (N = 33), 0 failures, 0 errors, 206.045 s.
  MEASURED at battery close: 741 tests, 0 failures, 0 errors, 0 skips, 205.725 s. 668 + 73 = 741 is
  exact: the battery contributes all 73 and nothing else survives from the battery wave. The
  four-test review-probe module was added at the red checkpoint and DELETED at close, because the
  battery now carries its findings permanently and two parallel probe files for one boundary is the
  duplication this project prunes. Grader: 52 obligations, 73 tests, UNFILLED 0, UNCOVERED 0, PASS.
- D27. `test_b20_read_site_census_has_no_mutations` asserts EXACT counts. AT THE `f9b9755` BASELINE
  those counts are 17 read sites, 15 write sites, 12 reached helpers, and `violations == []`. The
  test is cited by NAME, because a line anchor into a file this unit edits is stale on arrival.
  M3.3's new transaction sites break the first two. The counts are a TRIPWIRE that forces deliberate
  acknowledgement of every new site, not an invariant that the totals never grow; `violations == []`
  is the load-bearing assertion.
- D28. M3.3 UPDATES those counts to the numbers its ruled design actually produces, in the same
  commit that adds the sites, and the implementation records each new site by method name. Contorting
  production code to hold the old totals is a defect, not a pass - see D13. LANDED TOTALS, published
  here so no later lens has to re-derive them: 18 read sites, 16 write sites, 12 reached helpers,
  `violations == []`. The two additions are `_submission_revision` (read) and `_persist_proposal`
  (write), each recorded by method name.
- D29. `violations == []` and the reached-helper discipline stay untouched. A new site that cannot
  bind a simple connection name is a defect in the implementation.
- D30. Closure is mechanical: the full gate green, the battery grader reporting every obligation
  filled, and a mutation sweep over the added predicates. A green suite alone never closes this unit.
  THREE COMMANDS, published verbatim, each rerunnable from committed state:

  1. `PYTHONDONTWRITEBYTECODE=1 uv run -q python -m unittest discover -s tests -t .`
  2. `uv run python .agent/decisions/m3u3-battery-validate.py`
  3. `uv run python .agent/decisions/m3u3-mutants.py`

  Command 2 grades `tests/test_submission_battery.py` against the obligation manifest inside the
  grader and exits 0 only when every id owns at least its required number of filled, documented
  tests. Command 3 runs the MUTATION CORPUS below. Its verdict modules default to
  `tests.test_submission` plus `tests.test_submission_battery`; `--full` re-runs the whole suite on a
  survivor, which separates "the battery misses it" from "nothing pins it".

  THE MUTATION CORPUS IS ENUMERATED IN `.agent/decisions/m3u3-mutants.py`: 42 mutants over the
  predicates this unit adds, each addressed by a unique anchor string the runner proves occurs
  exactly once. By site: `_canonical_candidate` 5 (candidate type test deleted and widened to
  `isinstance`, provenance mapping guard deleted and widened, provenance byte bound dropped);
  `System.__init__` 1 (the deleted pre-flight restored); `_submission_revision` 4 (read becomes a
  write, partition scope weakened to `LIKE`, name scope weakened, missing operation admitted);
  `_persist_proposal` 15 (seam partition and name scopes weakened, missing operation admitted,
  revision guard unconditional, deleted and inverted, proposal id prefix changed, clock read per row,
  request row status, event kind renamed, event publishes the request id, event subject is the
  request, status sequence unbound, provenance columns swapped, seam split into two transactions);
  `submit_proposal` 6 (keyword marker
  dropped, candidate defaulted, three validation-order swaps, revision captured); `propose` 10
  (source attribute read twice, missing-source check moved after the lookup, caller object passed as
  request input, source invoked twice, return validation moved outside containment, catch widened to
  `BaseException` and narrowed to the declared error, raise moved inside the handler, contained raise
  keeps its cause, source path drops its revision guard); `errors.py` 1 (the D31 docstring reverted).

  THE STANDARD IS ZERO. Command 3 exits 0 only when every mutant is killed by a verdict module or is
  a declared equivalent. A survivor names the obligation no committed test pins, and the fix is the
  missing test, never a corpus deletion: a mutant leaves the corpus only when the predicate it
  targets leaves the code.

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
- D33. Shipped prose states submission's PRICE explicitly: three rows in one transaction, no
  idempotency, and one adapter invocation on the source path. `resolve`'s cost precedent applies -
  state the price. The mechanical check is a scan of README, `docs/` and `src/` for `cheap`,
  `safe-to-retry`, `deduplicated` and `request-free`, which returns zero; the last is avoided because
  D14 retains a real request row, so the phrase is overbroad even though the roadmap uses it as the
  unit's name.
- D34. README, `docs/architecture.md`, `docs/threat-model.md` AND `docs/adapter-protocol.md` are
  checked for sentences the new surface falsifies. A sentence that becomes false is corrected in this
  unit even when the code is correct; M3.2b found six consecutive units whose only defects were claim
  defects. `adapter-protocol.md` is the doc that owns adapter FAILURE behaviour, so it is the one the
  new raising path falsifies, and omitting it from this list was itself a defect.
- D41. POSITIVE PUBLICATION, and it is a separate obligation from D34. Section 1 puts "the normative
  prose that publishes the new surface" in scope. Docstrings do not discharge that, and neither does
  stale-claim cleanup: a reader must be able to learn from human-facing prose alone that both methods
  exist, what each one's authority is, what the call returns, what three rows it costs, that it
  carries no idempotency, that source failure is contained, and that the request row is retained. The
  test is mechanical - search README and the normative docs for both method names.

## 12. Verdict table - MAIN-final

Row-by-row rulings live in `m3u3-verdicts.json`, MAIN-owned columns `main_verdict` and
`contract_action`. All 58 rows are ruled: 46 seeded plus 12 extension rows the diff-blind lens added.
`m3u3-rule-verdicts.py` is the idempotent patcher that fills those two columns from a clean copy of
the teammate's table, so the wave stays re-derivable; `--check` reports whether the committed table
matches the rulings. This section carries only what does not fit a table cell.

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

MEASUREMENT. P06 is verified mechanically and reproduces exactly under all three conventions P06 now
tabulates - 12,866 / 12,867 / 12,862 bytes, byte-identical at `3b7769b` and at HEAD. Two lenses
reached the third figure independently before MAIN re-derived every one, which is the whole reason
the pin ships a table instead of a number.

EXTENSION ROWS. The diff-blind lens added twelve loci the seed never carried, and they moved the
contract more than the seeded forty-six did. Eight new obligations landed from them: B01/B02 (X05,
X06) freeze the schema and the byte-stable files with a NAMED baseline; D35/D36/D37 (X03, P04, X09)
publish the four-step precedence, the source snapshot, and the containment boundary; D38/D39 (X02,
X10) publish the malformed-RETURN row and the `BaseException` boundary; D40 (X04) publishes the
single canonical snapshot; D41 (X11) separates positive publication from stale-claim cleanup. Section
7's heading is qualified to the submission DOMAIN (X08), because the table omitted reachable clock
and `Store` failures while claiming to be exact.

TWO ROWS ARE WORTH RE-READING BEFORE M3.4 REOPENS THIS SURFACE.

- V-X09. This is the one place the shipped code deliberately REJECTS a teammate recommendation. The
  row proposes validating `propose` callable before the operation read and publishing a distinct
  `StateError` for unusable configuration. Shipped instead: only `None` gets a published error;
  every other unusable configuration is contained as `CandidateSourceError`. Grounds, in order of
  weight - testing a descriptor means EXECUTING it, so the pre-flight IS the invocation and can
  itself raise with a secret; `callable()` is unsound under `__getattr__` and descriptor protocols,
  so the check can pass and the call still fail; and a second configuration-error channel would let
  a caller distinguish adapter shapes that D19 keeps indistinguishable. Do not relitigate without
  new evidence on those three points.
- V-X11. A REAL OPEN GAP at implementation close, found by no other lens. README matched only the
  adapter snippet's `def propose(self, request)`; neither `architecture.md` nor `threat-model.md`
  named either method. The unit had shipped a public API that no human-facing surface published.
  Fixed at S2 close, and D41 now states the obligation positively so a docstring cannot discharge it
  again.

DISCHARGED AT S3, both raised at S2 and both ruled then. D30 now publishes its three commands
verbatim and enumerates all 42 mutants by site; section 9 carries the standard and section 13 the
measurement. X12 asked for a measurement where S2 had only the argument that the seam is
structurally atomic - one write transaction containing all three INSERTs - because D15 could pass on
pre-write failures alone. The battery ships the rollback matrix that injects after each interior
write, so D15's fifth pin now measures what X12 asked for.

## 13. Review dispositions and differential result

COMPLETE at S3. The contract attack is disposed below, the differential is run and credited by MAIN's
own re-derivation, and every review row is ruled. Machine copies:
`m3u3-attack.json` (`main_disposition`, patcher `m3u3-rule-attack.py`), `m3u3-review.json` and
`m3u3-divergences.json` (`main_ruling`, patcher `m3u3-rule-wave3.py`). Both patchers take `--check`
and are the in-sync gate.

DIFFERENTIAL RESULT, S3, MAIN-rerun credited. `m3u3-probe-driver.py` re-derived all 34 probe
outcomes against the shipped post-fix code (`system.py` sha256 `302d0342f06a...`), and
`m3u3-differential.py` graded them against the oracle's committed table: 30 of 30 seeded probes
IDENTICAL across `probe`, `outcome`, `observation` and `note`, with Q30 identical under the single
declared normalization `_persist_proposal` -> `_persist_submission`. All four Z extensions re-derived
byte-identically to their recorded MAIN observations.

THE EMPTY SEEDED DIVERGENCE SET IS ITSELF THE FINDING, and it is the reusable one. The oracle wrote
its 30 probes to demonstrate its own conformance to this contract, so every probe measures a property
both implementations were built to satisfy. Such a corpus CANNOT discriminate two designs: 29
identical, 1 adapted, 0 differs. The instrument only became evidentiary once MAIN added Z01-Z04
targeting the two RULED divergences directly, and Z03 is the row that pays for the whole exercise -
it exhibits the oracle raising `StateError` and storing nothing where MAIN succeeds, which is the
defect V-D12 removed from MAIN's own code. Write oracle probes against the ruled disagreements, never
against the shared contract.

CLOSURE MEASUREMENT, S3. Full gate 741 tests / 0 failures / 0 errors / 0 skips / 205.725 s. Grader
52 obligations / 73 tests / UNFILLED 0 / UNCOVERED 0 / PASS. Mutation sweep 42 mutants / 42 killed /
0 survivors / 0 battery gaps against a green control. D30 and X12 are both discharged.

POST-IMPLEMENTATION REVIEW, `rev-m3u3-2`, 16 seeded lenses plus 6 the reviewer added, 22 rows: 3
blocking, 12 material, 7 cleared. Rulings are in `m3u3-review.json`. Summary, MAIN-final.

TWO CODE DEFECTS, each confirmed by two independent lenses, so the council rule accepts both outright
without a MAIN probe - and MAIN probed them anyway because both change shipped behaviour.

- `dict(candidate.provenance)` accepted a list of pairs and a generator of pairs as "a mapping",
  violating the declared `Candidate.provenance: Mapping[str, object]` and silently draining a
  one-shot iterator. R01 and R15 both reached it. FIXED: D43's `isinstance` guard. The same edit
  deleted the unreachable JSON-object branch, which mutant `provenance-object-check-deleted` had
  already reported as dead by surviving - a dead branch and a surviving mutant are one fact seen
  twice.
- `System.__init__` pre-flighted `callable(getattr(candidate_source, "propose", None))`. R07a and the
  battery's own D37 test both drove a raising descriptor through construction and read the planted
  secret out of the traceback. FIXED by DELETION, ruled in D37 with its behaviour change recorded.

CLAIM DEFECTS, all landed at S3: `submit_proposal`'s docstring promised the revision `StateError`
V-D12 made unreachable (R09a with battery D32) · `65_536` appeared nowhere in the contract though
section 13 claimed the bound was published (R07b, now D44) · D38 named a mapping whose `items()`
raises as the settling case, but `dict(Mapping)` reads `keys()` and `__getitem__`, so it was never
called (R01) · section 7 carried two rows that conflicted for a non-str-key mapping (R01) · README,
`architecture.md` and `adapter-protocol.md` repeated the rejected direct-path revision guard and
over-broadened two quantifiers (R10) · D27 published the pre-unit census totals as if they were the
landed ones (Z01) · the roadmap and memory overclaimed closure in four places (R08) · this contract's
own title used the `request-free` label D33 bans (Z04).

SIX ROWS RULED CARRIED, undischarged, and they are S4's whole job. Acceptance checks are stated
verbatim in `m3u3-review.json`; the subjects are: R06 + R07 commit-uncertainty and the shared
"submission-attributable" scoping of D01/D07/D09/D15/D16 · Z02 the AST single-writer probe that a
one-transaction two-helper split would fail · Z03 the annotation half of the frozen ABI · Z05 the
9-of-13-table footprint instrument in `tests/test_submission.py` and `m3u3-smoke.py`, which the
battery's own `sqlite_schema`-derived counter already avoids · Z06 the case-sensitive substring SQL
spy behind D17.

THE MUTATION NUMBER IS MEANINGLESS WITHOUT ITS VERDICT MODULE LIST. R12 measured 12 of 25 mutants
surviving and MAIN's own pre-battery baseline measured 13 of 41, both against
`tests.test_submission` alone. The same corpus against `tests.test_submission` plus
`tests.test_submission_battery` kills everything. Neither earlier number was wrong; both were
answering a different question, and a sweep that does not print its verdict modules invites the
reader to answer the wrong one.

ORACLE, `orc-m3u3-1`, 30 probes, corpus at `m3u3-probes.json`, implementation on `wt/orc-m3u3-1`,
worktree RETAINED for S3. It built the identical contract without seeing MAIN's code and was
instructed NOT to match MAIN's rulings, because divergence is the instrument.

AGREEMENT, each an independent second measurement of a MAIN claim: Q09 held four Cement-created
connections open and observed `in_transaction is False` on every one during source execution (D11);
Q10/Q11 measured `__cause__ is None`, `__context__ is None`, and no source frame (D18); Q22
preserved the ledger sha256, the full 53-statement dump, every row count and the event sequence
(D15); Q23 measured zero `commit()` calls across EIGHT failure families against a positive control
of one (D16); Q25 recorded exactly two `SELECT` statements, both scoped reads of `operations` (D13);
Q27 drove submission through review, compile, verify, promote and an artifact-backed `handle`; Q29
showed unchanged `handle` still adding exactly one request, proposal and event afterwards (P06,
behaviourally). The oracle also reached the `m3u3-map.json` S01 conflict independently and retained
`request_id` per D14 - a third lens on that row.

TWO DIVERGENCES, both ruled.

- DIRECT TRANSACTION COUNT. The oracle gives BOTH paths a scoped read transaction plus a write
  transaction with a revision re-read: two transactions on the direct path where MAIN opens one.
  MAIN's ruling stands (V-D12), and the oracle is the exhibit: carrying an entry-captured revision
  into a direct submission reproduces exactly the `StateError` that a caller with no generation
  window cannot have earned. Two lenses independently identified the ambiguity - verdict row D12 and
  attack row A05 - and the oracle independently BUILT the branch they warned about. Divergence
  found the defect, and agreement would have hidden it.
- CLOCK PLACEMENT. The oracle reads `_now` BEFORE the write transaction, to avoid holding the write
  lock while caller-supplied clock code runs. MAIN reads it INSIDE. This is a real trade and the
  oracle's ground is sound, but M3.1 already ruled it: a clock read taken ahead of the authoritative
  plan can commit a row older than its own build, and one timestamp shared by all three rows (D17,
  Y05) is what the row shape requires. MAIN's placement stands; the lock-hold cost is bounded by
  `self._now`, which is Cement's own seam and not adapter code.

CONTRACT ATTACK, `rev-m3u3-1`, 24 lenses: 18 seeded plus 6 the reviewer added. Dispositions,
MAIN-final. Row detail in `m3u3-attack.json`, MAIN column `main_disposition`, filled by the
idempotent patcher `m3u3-rule-attack.py`.

| id | severity | disposition | landed |
|---|---|---|---|
| A03 | blocking | UPHELD. `events.sequence` is AUTOINCREMENT, so every success mutates `sqlite_sequence` and a literal reading of D01 is unsatisfiable. Confirmed independently by the verdict table's D01 row, so the council rule accepts it outright. | section 12 V-D01; the suite compares declared SCHEMA tables only |
| A07 | blocking | UPHELD. D07 ordered DIRECT candidate validation while section 7 published no class or text for any of its failures. | four rows added to the section 7 table; `test_a_rejected_candidate_reports_its_own_validation_text` |
| X02 | blocking | UPHELD, and the sharpest finding of the wave. D15/D16 were unconditional, yet the source runs outside every Cement transaction and the revision-race fixture's own source commits through `revise_operation`. | D15 restated as zero submission-attributable mutation with its comparison window named; D16 scoped to failures before commit |
| A05 | material | UPHELD. Confirmed independently by the verdict table's D12 row. This pair is what changed MAIN's shipped code. | section 12 V-D12 |
| A04 | material | UPHELD. Confirmed independently by the verdict table's D07 row. | three adjacent-edge probes plus two for `propose`'s source slot |
| A06 | material | UPHELD against the contract: D15 and D16 named instruments and D17 named none. | D17 now carries a statement-recording `Connection` subclass with its own positive control |
| X04 | material | UPHELD against the contract: D06's single-writer obligation was structural with only behavioural probes, which duplicated writers satisfy. | `test_both_methods_route_through_one_persistence_seam` spies the seam itself, not the footprint |
| A11 | material | UPHELD. `docs/adapter-protocol.md` promised an inert `fallback_failed` request and possible re-invocation, both false through `propose`. | both sentences qualified by route; D34's list corrected |
| A08 | material | UPHELD in part. The eight named seams are API-level; `cli.py` also serializes the identifier, and authorized ledger access exposes it by design. | section 12 V-D23 states the list is named high-level seams, never an exhaustive count |
| A09 | material | UPHELD. D27 cited `tests/test_read_capability_battery.py:869-872`, which is the violation branch; the assertions sat at 875-878 and this unit moved them again. | D27 cites the test by NAME; a line anchor into a file the unit edits is stale on arrival |
| X01 | material | UPHELD. The v2 CHECK ADMITS the required shape; it does not enforce it, and a `pending` row with `attempts > 1` also satisfies it. D02's "already admits exactly this shape" overstated. | D02 reads as a permission, and `attempts == 1` is pinned by test rather than inferred from the schema |
| X03 | material | UPHELD, and narrowed by the reviewer itself: swept for stale counts, byte lengths and SHAs, the inventory yields exactly ONE stale anchor, D27's. Same defect as A09 from a different lens; every other stated figure reproduces. | D27 cites the test by NAME |
| A02 | cleared | CLEARED, and the clearing is the useful result. The reviewer reproduced P06 under the line-start slice with the trailing newline removed and got the contract's exact figure - independently identifying the convention that makes the claim checkable. MAIN measured both: 12,866 B / `1182130a2b3a` whole-line span against 12,862 B / `c27e71b0b4c7` from `ast.get_source_segment`, same unchanged source, four bytes of indentation apart. | P06 states the convention; the test states it again in its docstring |

| Y01 | blocking | UPHELD. `propose` with `candidate_source is None` AND an absent operation was unruled, and the two orders differ observably: zero transactions against one read. Confirmed independently by the verdict table's X03 row. | D35 publishes the four-step precedence; D21 carries the cross-reference |
| Y02 | blocking | UPHELD, and broader than A07. The accepted candidate domain, the provenance byte limit, and the ownership split between DIRECT `ValidationError` and SOURCE-BACKED containment were all undefined. Confirmed independently by the verdict table's X01 and X02 rows. | section 7 gains four candidate rows plus the malformed-RETURN row; D38 rules the ownership split |
| Y03 | blocking | UPHELD. D01 counted the proposals row and specified nothing about it, so a conforming writer could omit the provenance hash, the status, or the event binding and still pass every count. | D42 states the row shape, including `status_sequence` bound to the event's own `sequence` |
| X07 | material | UPHELD. "Invokes `self.candidate_source` and nothing else" is false on every successful call, which also reads the clock, the ledger, and the operation revision. | P04 scopes "nothing else" to GENERATION authority |
| Y04 | material | UPHELD. "Caller-supplied identifier of any kind" bans `partition` and `operation`, which are caller-supplied identifiers the signature requires. | D04 scopes the ban to ledger row identity and deduplication keys |
| Y06 | material | UPHELD. A source that reenters the same `System` opens a Cement-held connection that reports `in_transaction is True`, which D11 forbade unconditionally and no library can prevent. | D11 scopes the quantifier to transactions the SUBMISSION CALL holds |
| Y05 | material | UPHELD against the contract, already satisfied by the code. D17 named the clock seam and not its cardinality, so two conforming writers could give the three rows different timestamps. | D17 states one `self._now` inside the write transaction serving all three rows; section 12 V-D17 carries the M3.1 grounds |
| X05 | material | UPHELD as a claim-soundness defect. Confirmed independently by the verdict table's D19 row - the council rule accepts it. Cement cannot hide adapter behaviour from a caller who owns the adapter. | section 12 V-D19 scopes indistinguishability to observations through the raised Cement exception |
| X06 | minor | UPHELD IN PART, with the boundary ruled. Negative-form obligations are the real defect: D23, D25 and D33 told the reader what may not be written, which is the pink-elephant shape the project bans, and they govern SHIPPED prose. All three are now positive. REJECTED on provenance: measurements, SHAs, baselines and named conventions are this document's PAYLOAD, and the Authoring rule's ban targets dates, discovery narration and origin stories. A decision record that drops its measurements stops being checkable. | D23, D25 and D33 restated positively; measurements retained |
| A01 | cleared | ACCEPTED as cleared, and B01/B02 now make it checkable rather than argued. The verdict table's X05 and X06 rows found the same gap from the other side: scope said "unchanged" and "byte-stable" without a pin or a baseline. | section 1 gains B01 and B02 with the `f9b9755` baseline named |
| A10 | cleared | ACCEPTED as cleared. The fork ruling separates measured API hazards from implementability evidence, and section 10 already states that `split`'s green gate is not correctness. | no change |

TWO LENSES, DISJOINT YIELD, as on u3b1. The diff-blind verdict table and the contract attack agreed
on D01, D07 and the direct-path revision binding - three convergences the council rule accepts
without a MAIN probe - while each also reached findings the other did not: the attack alone caught
the missing candidate error taxonomy, the falsified adapter doc and the unconditional purity claims;
the verdict table alone caught the `__context__` retention that `from None` inside a handler does not
clear, and the seven-versus-eight seam count per path.

SUBSTANCE AND REPRODUCTION ARE GRADED SEPARATELY, and P06 is why the rule exists. `handle`'s byte
count has TWO defensible measurements four bytes apart on identical unchanged source: 12,866 B /
`1182130a2b3a` from the whole-line span, 12,862 B / `c27e71b0b4c7` from `ast.get_source_segment`,
which drops the four-space indent. A lens that picks the second convention reports a correct `handle`
as stale. The reviewer picked the first, cleared A02, and named the convention in its own words -
so MAIN re-derived both before acting, and the pin now carries the convention rather than the number
alone. Grade a finding by whether its reproduction is stated, never by whether its number differs.
