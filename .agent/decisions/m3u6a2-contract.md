# M3.6a2 acceptance contract — delete the lifecycle API and rewrite the prose that documents it

Unit M3.6a2, `tier=kernel`, `tags=-`, `depends=M3.6a1`, budget `est 9 -> ?` sessions.
Base commit for every git-object pin in this contract: `da70a56`.

M3.6a1 migrated every consumer off `handle`/`request_status` while both still shipped. This unit
deletes them and everything that exists only to serve them, then rewrites the four normative
documents that still describe the deleted surface. Nothing migrates here; every consumer already
moved.

Obligation ids are `L01..L31` — a letter no other contract uses. `d`, `b`, `x`, `v` and `p` are all
live prefixes in `tests/`, and an id colliding across contracts is invisible to a reader who knows
the local numbering. Cite another unit's obligation with its unit name attached.

## 1. Ground state, measured at `da70a56`

`src/cement_runtime/system.py` = 5710 lines, 235,939 B. Method spans, from the module's own AST:

| method | span | lines | disposition |
|---|---|---|---|
| `__init__` | 680..702 | 23 | EDIT — drop the lease knob |
| `_now` | 704..712 | 9 | EDIT — drop the lease term from the bound |
| `revise_operation` | 762..836 | 75 | EDIT — drop the request cancellation |
| `handle` | 1059..1329 | 271 | DELETE |
| `_fail_generation` | 1331..1362 | 32 | DELETE |
| `_outcome` | 1364..1479 | 116 | DELETE |
| `_request_revision_is_current` | 1482..1492 | 11 | DELETE |
| `request_status` | 1546..1559 | 14 | DELETE |

Deleted method spans total 444 lines. Every other method in the class survives.

Reference census, `src/` + `tests/` + `examples/` + `docs/` + `README.md`:

| symbol | `src/cement_runtime/system.py` | elsewhere in `src/` | tests | docs + README |
|---|---|---|---|---|
| `handle` / `request_status` | the spans above | 0 | 75 refs over 9 files | README, architecture, adapter-protocol, threat-model |
| `_outcome` | 7 | 0 | 0 | 0 |
| `_fail_generation` | 4 | 0 | 3 (2 in `test_proposal_binding_battery.py`, 1 in `test_proposal_binding.py`) | 0 |
| `_request_revision_is_current` | 4 | 0 | 0 | 0 |
| `_lease_us` | 5 | 0 | 0 | 0 |
| `generation_lease_seconds` | 5 | 0 | 5 (3 in `test_authority_removal.py`, 2 in `test_system.py`) | 0 |
| `invalidated_generators` | 2 | 0 | 0 | 0 |
| `resolved_by_artifact` | 1 | 0 | 2 (`test_migration_battery.py`) | 0 |
| `fallback_failed` | 1 | `models.py` 1 | 7 over 3 files | README 1, adapter-protocol 1 |

Site ownership inside `system.py`, by the method that contains each line:

- `_lease_us`: `__init__:702` (assignment), `_now:709` (bound), `handle:1099, 1110, 1235`. Deleting
  `handle` plus the knob plus the bound term takes this to ZERO.
- `_request_revision_is_current`: called from `handle:1089, 1274` and `_outcome:1372`; both callers
  are deleted, so the definition has no surviving caller.
- `_outcome`: called from `handle:1090, 1114, 1273, 1291`, `_fail_generation:1343` and
  `request_status:1559`; all three callers are deleted.
- `_fail_generation`: called from `handle:1242, 1258, 1261` only.
- Single-producer event kinds inside the deleted spans: `request.resolved_by_artifact`
  (`handle:1208`), `request.fallback_failed` (`_fail_generation:1356`) and
  `artifact.ambiguity_quarantined` (`handle:1143`). Each has exactly one emission site repo-wide, so
  all three lose their producer here (C05).
- `requests` table: 20 lines over 7 methods. This unit removes 13 of them — `handle` 9,
  `_fail_generation` 2, `request_status` 1, `revise_operation` 1 — leaving exactly SEVEN over three
  owners: `_proposal_bindings` (534, 547, 574, 591) and `_write_proposal_request_status` (643, 653),
  both MODULE-LEVEL functions, plus `_persist_proposal` (893), which is a `System` METHOD (C09). A
  class-body-only scan therefore sees ONE surviving site, not zero. Those are M3.4's private
  proposal plumbing and M3.6b's schema-cut targets; this unit does not touch them.

The five deleted methods form a CLOSED call-graph component whose only entries from outside it are
the two public methods being deleted. That is why the deletion needs no consumer migration and why
its closure is checkable by counting occurrences rather than by reasoning about call order.

Models: after the deletion, `FallbackFailed`, `InProgress`, `Outcome`, `ReconciliationRequired`,
`Rejected`, `Resolved` and `ReviewRequired` survive in `system.py` at their import lines ALONE
(`Resolved` also at 673, inside the `System` class docstring). Outside `system.py` they appear only
in `models.py` (definitions) and `__init__.py` (re-export plus `__all__`). This unit therefore
leaves SEVEN model DEFINITIONS and SIX package EXPORTS with no producer — `Outcome` is a
models-only alias and is not in `__all__` (C10) — and all seven leave `system.py`. Deleting them is
M3.6a3's, and `ReviewRequired` losing its last producer here is the measurement behind M3.6a3's
first ruling.

### 1.1 Burden

GOVERNING BURDEN = 48 NORMALISED FRAMES, `m3u6a-burden.py` over throwaway worktrees at `da70a56`,
recorded in `m3u6a2-stages.json`:

| stage | label | broken | ran | raw frames | normalised |
|---|---|---|---|---|---|
| 1 | methods | 50 | 979 | 48 | 47 |
| 2 | lease | 50 | 979 | 48 | 48 |
| 3 | revise | 50 | 979 | 48 | 48 |

Union over the three stages = 51 raw frames. Stages 4-5 belong to M3.6a3 and were not measured.

Two readings bind the work:

- STAGE 3'S FAILURE SET IS BYTE-IDENTICAL TO STAGE 2'S. Deleting the request cancellation and the
  `invalidated_generators` payload key breaks nothing the methods deletion had not already broken,
  and `invalidated_generators` has ZERO pins repo-wide. Its removal is unobservable to the current
  gate, so L08 exists to supply the pin the gate never had.
- STAGES 1 AND 2 BOTH READ broken=50 AND THE EQUALITY IS A COINCIDENCE. Raw frames move +3/-3:
  `test_authority_removal.py:118 test_system_constructor_shape` is genuinely new;
  `test_system.py test_expired_generation_poll_is_retryable_and_handle_reclaims` moves `:702` to
  `:686`, a frame under the RAW key and none under the normalised one; and
  `test_system.py:732 test_public_scalar_validation_fails_with_domain_errors` replaces its own two
  `<lambda>` subtest rows at `:735` and `:736`, because it now fails before the subtest loop. Net
  breaks -2+1+1 = 0. A subtest-bearing test contributes a VARIABLE number of breaks, so the count is
  not monotone under cumulative deletion. Compare the SET; size on normalised frames.

Frame key convention, stated beside every count in this unit: RAW keys are `file:line in name`,
NORMALISED keys are `file in name`. The two differ by roughly 5-10% and comparing across them
manufactures a defect out of nothing.

### 1.2 Prose

`m3u6a2-tripwires.json`, emitted by `m3u6a2-tripwires.py`: PINS 16, FREEZES 4, PROSE-HIT-LINES 50
over five documents, re-measured by C06 under the widened vocabulary and with this unit's own
battery excluded from both scanners. Hit lines count DOCUMENT LINES matching the census
vocabulary, not `handle` loci; M3.5b's D22 deferral table counted the latter, so its 18/7/8/4 and
this table's numbers are INCOMPARABLE and neither corrects the other.

| document | lines | hit lines | owner | grounds |
|---|---|---|---|---|
| `README.md` | 449 | 26 | M3.6a2 | the poll-state table, both lifecycle method names and the request-route section all describe surfaces this unit deletes |
| `docs/architecture.md` | 211 | 13 | M3.6a2 | steps 1-3 describe `handle`; the lease paragraph describes the deleted knob |
| `docs/adapter-protocol.md` | 61 | 7 | M3.6a2 | M3.7 relocates this document under BYTE EQUALITY and never rewrites a claim, so false `handle` prose left here would be RELOCATED, not deferred |
| `docs/threat-model.md` | 114 | 3 | M3.6a2 | the `handle` request ID as an idempotency key, and lease recovery, both cease to exist |
| `examples/hospital_ocr/README.md` | 247 | 1 | M3.6a1 | already rewritten by M3.6a1's D22-D23 transcript regeneration; the surviving hit names no deleted surface |

Owned hit lines, for the rewrite's own work list:

- `README.md`: 14, 49, 52, 70, 145, 256, 266, 281, 303, 325, 327, 332, 345, 346, 347, 351, 355,
  356, 362, 363, 364, 365, 367, 368, 370, 444.
- `docs/architecture.md`: 11, 16, 17, 18, 61, 65, 67, 68, 97, 99, 124, 148, 149.
- `docs/adapter-protocol.md`: 35, 36, 37, 52, 53, 56, 57.
- `docs/threat-model.md`: 61, 78, 90.

## 2. The deletion set

1. `System.handle` — the whole 1059..1329 span.
2. `System.request_status` — 1546..1559.
3. `System._outcome`, `System._fail_generation`, `System._request_revision_is_current`.
4. `System.__init__`'s `generation_lease_seconds` keyword, its `_bounded_int` validation call and
   the `self._lease_us` assignment. `_bounded_int` itself survives: it has 16 call sites and 15 of
   them are elsewhere.
5. The lease term in `_now`'s upper bound. `now > _MAX_SQLITE_INTEGER - self._lease_us` becomes
   `now > _MAX_SQLITE_INTEGER`, and the `StateError` message stops saying `lease-safe`. No test
   pins that message string today, so the battery supplies the pin.
6. `revise_operation`'s request cancellation: the `UPDATE requests SET status = 'failed',
   error_code = 'operation_revised' ...` statement, the `invalidated_generators` local it assigns,
   and that key in the `operation.revised` event payload.
7. The three event kinds `request.resolved_by_artifact` (`handle:1208`), `request.fallback_failed`
   (`_fail_generation:1356`) and `artifact.ambiguity_quarantined` (`handle:1143`), each of which has
   exactly one emission site and no emission site outside the deleted spans. Ambiguity quarantine is
   a BEHAVIOUR this unit removes: `handle` was its only producer, `resolve` is read-only and cannot
   quarantine, and two shipped prose lines still claim it. Added by C05.
8. The seven now-unused `.models` imports in `system.py`.

### 2.1 The one behaviour change, ruled

Removing the lease term WIDENS the accepted clock range. A `clock_us` returning a value in
`(_MAX_SQLITE_INTEGER - lease_us, _MAX_SQLITE_INTEGER]` raises `StateError` today and is accepted
after this unit. That is correct: the rejected band existed so a lease deadline computed from the
timestamp could not overflow the column, and no lease deadline is computed anywhere after this
unit. The change is public and gets an obligation (L06) plus probes on both sides of the new
boundary, not a silent widening.

## 3. Obligations

Each obligation is a testable predicate. `L<n>` is the id; the battery test is `test_l<n>_...` in
`tests/test_lifecycle_removal_battery.py`.

### Deletion completeness

- **L01** `System` has no `handle` attribute under EVERY access route — `hasattr`, `getattr`,
  `dir()`, `inspect.getmembers` — neither `System` nor its metaclass defines `__getattr__`, and
  `system.py` holds no `FunctionDef` named `handle` at any scope. PLUS the structural subtraction
  (A01): the post-state `System` method-name set EQUALS its `da70a56` set minus exactly
  `{handle, request_status, _outcome, _fail_generation, _request_revision_is_current}`. A text
  predicate grades the spelling; only the set subtraction grades the subtraction, and renaming the
  271-line body satisfies every text half.
- **L02** `System` has no `request_status` attribute under the same four routes and no `FunctionDef`
  named `request_status` at any scope. The surviving `_ProposalBinding.request_status` field and the
  six other proposal-plumbing identifiers are a DIFFERENT subject and must remain (X01, L15).
- **L03** `System` has no `_outcome`, `_fail_generation` or `_request_revision_is_current`
  attribute, and `system.py` holds zero `FunctionDef` of each name at any scope — module level,
  class body and nested closure alike (V02).
- **L04** `System.__init__`'s signature is exactly `self, database, *, candidate_source, clock_us`.
  `System(db, generation_lease_seconds=1)` raises `TypeError`. Derive the parameter list from
  `inspect.signature`, never from source text.
- **L05** `_lease_us` has zero RAW BYTE occurrences across the git-tracked `src/` file set — the
  contract says occurrences, so strings, comments and docstrings count, and git-tracked scope
  excludes `__pycache__` (V05). Baseline 5, all in `system.py` at 702, 709, 1099, 1110, 1235. Token
  absence alone is satisfied by a rename, so L05 carries the AST SHAPE pin that a rename cannot
  (A03): `_now`'s comparator is exactly `now > _MAX_SQLITE_INTEGER` — the right operand is a bare
  `Name`, not a `BinOp` — and `__init__` binds no attribute whose value derives from a lease
  parameter. `generation_lease_seconds` likewise reaches zero raw occurrences across tracked `src/`
  (X03; baseline 5), since `inspect.signature` cannot see a dead literal or comment.
- **L06** `_now`'s upper bound carries no lease term: a clock returning `_MAX_SQLITE_INTEGER` is
  ACCEPTED and reaches a real write, `_MAX_SQLITE_INTEGER + 1` is REJECTED, and the `StateError`
  message is EXACTLY `clock must return a signed 64-bit microsecond timestamp`. Probe both sides of
  the boundary in one test so the assertion cannot pass by rejecting everything. The positive text
  pin is MAIN's own wording, not a diff-blind paraphrase, and it exists because a
  forbidden-substring predicate cannot see a silent re-wording (V07, V22). The dead
  `lease-safe` literal must also be absent from tracked `src/` (X27).
- **L07** `revise_operation` performs no `requests` write. The source half scans AST string
  constants case-insensitively and rejects every spelling — `UPDATE`/`update`, arbitrary
  whitespace, a multiline split, and `` `requests` ``, `"requests"`, `[requests]`,
  `main.requests`, `temp.requests` (V10). The behavioural half executes a revision while a
  `generating` request row exists at the previous revision and asserts that row's `status`,
  `error_code`, `lease_owner` and `lease_until_us` are unchanged. THAT ROW IS FABRICATED LEGACY
  STATE and is labelled as such: after this unit no supported route produces `generating`, so the
  probe seeds it through `Store.transaction(write=True)`, modelling a ledger left by an older
  release at surviving schema v2 (V09, X28). The probe MUST assert the row exists at
  `status='generating'` BEFORE the revision — a zero-row UPDATE raises nothing, so an unguarded
  preservation probe is green-and-empty rather than red (A05).
- **L08** the `operation.revised` event payload, read back from the persisted
  `events.payload_json`, has EXACTLY the keys `previous_revision`, `policy_hash`, `revised_by` AND
  each key's VALUE is bound: `previous_revision` == the operation's pre-revision integer,
  `policy_hash` == the canonical policy digest, `revised_by` == the actor the caller supplied.
  Assert the whole key set, not the absence of one key, and assert the values, not just the keys: a
  three-key set assertion passes while all three values are wrong (A06), and `revise_operation`
  returns only the new revision, so the return value cannot evidence the payload. This payload had
  zero pins before this unit. `invalidated_generators` additionally reaches zero RAW occurrences
  across tracked `src/` — baseline 3, being one assignment, one payload key STRING and one value
  identifier, which is why the census's `2` (NAME tokens) is not the closure number (X04).

### Closure

- **L09** zero dangling references, counted as `tokenize` NAME equality over tracked `src/` `.py`
  files so `handler` and `unhandled` never count. The expected post-state vector is
  `{handle: 0, request_status: 7, _outcome: 0, _fail_generation: 0,
  _request_revision_is_current: 0, _lease_us: 0}` (X02, X24; baseline
  `1, 8, 7, 4, 4, 5`). `request_status` IS NOT ZERO and cannot be: MAIN measured eight identifiers
  at `da70a56`, of which deleting the method removes line 1546 alone, leaving SEVEN
  proposal-plumbing identifiers at 458, 503, 1529, 1532, 1535, 1542 and 1579 — the last inside
  `get_proposal`, which L15 freezes byte-for-byte. The original `zero occurrences` reading was
  false-by-construction against L15 and is corrected by C09; L02 carries the `System`-attribute
  claim instead. Dynamic reach is closed by a bounded, MEASURED pin (A07): tracked `src/` holds
  ZERO `getattr`/`setattr`/`hasattr`/`delattr` calls whose name argument is not a string
  `Constant`, which rejects `getattr(self, '_out' + 'come')` by construction. Count over the whole
  package, not over `system.py`.
- **L10** `system.py`'s `from .models import (...)` list loses exactly `FallbackFailed`,
  `InProgress`, `Outcome`, `ReconciliationRequired`, `Rejected`, `Resolved`, `ReviewRequired` —
  seven names — and no other import moves. Compare the parsed import list, not the source text.
- **L11** the emitted event-kind vocabulary is EXACTLY the SIXTEEN surviving kinds —
  `artifact.challenged`, `artifact.compiled`, `artifact.counterexample`,
  `artifact.integrity_quarantined`, `artifact.promoted`, `artifact.suspended`,
  `artifact.verification_failed`, `artifact.verified`, `example.revoked`, `function.promoted`,
  `operation.registered`, `operation.revised`, `proposal.accepted`, `proposal.corrected`,
  `proposal.created`, `proposal.rejected` — and the `request.` prefix is gone from the namespace.
  Assert the whole SET, not the absence of the deleted kinds: an absence assertion passes while a
  further kind is invented, and the project's own rule is to pin the complete vector rather than a
  derivative of it. Corrected by C05; the count and three of the members moved.

  THE DERIVATION IS TOTAL, NOT BEST-EFFORT (A09, X05): every `_event` call's `kind` argument must
  match one of the three ruled AST forms and must expand non-empty, and an unsupported form FAILS
  the check rather than being skipped. Set equality alone stays green when a fourth form
  (`kind=event_kind`) ships a new runtime kind, because the recognized set is unchanged.

  THE VOCABULARY HAS THREE SPELLINGS AND A RULE READING ONE IS BLIND TO THE REST. Every event is
  written by the module-level `_event(connection, *, kind=..., ...)` helper (`system.py:380`),
  called NINETEEN times at `da70a56` — 16 `Constant`, 2 `IfExp`, 1 `JoinedStr`, falling to FOURTEEN
  post-state — and its `kind` argument takes three forms: a plain string constant; an `IfExp` whose two
  branches are both constants (`kind="artifact.verified" if passed else "artifact.verification_failed"`
  at `_verify_row:4065`, `kind="artifact.counterexample" if suspended else "artifact.challenged"` at
  `challenge:5129`); and one `JoinedStr`, `kind=f"proposal.{proposal_status}"` at `review:1881`, whose
  interpolation is annotated `Literal["accepted", "corrected"]` at `system.py:1770` and is resolved
  from THAT lexical function, never from a module-wide same-name search (X29). Derive the set from
  all three; a scan reading only the first reports 13 of the 16 and is what C05 corrects. C05's own
  supporting count of `20` was wrong and is corrected by C08: 19 static calls, the textual
  `_event(` count of 20 including the DEFINITION line. The 16-kind SET is unaffected because it was
  derived per call site, and the call count is REPORTED separately rather than used as a
  completeness control. Each of the three removed kinds loses its unique producer independently
  (X32).

  THREE KINDS LOSE THEIR ONLY PRODUCER HERE, not two. `request.resolved_by_artifact`
  (`handle:1208`), `request.fallback_failed` (`_fail_generation:1356`) AND
  `artifact.ambiguity_quarantined` (`handle:1143`) are each emitted at exactly one site, all three
  inside deleted spans. Ambiguity quarantine is therefore a behaviour this unit removes, which
  section 2's deletion set and the prose census both now record.
- **L12** `src/cement_runtime/models.py` is byte-identical to its `da70a56` blob (sha256
  `6dd45cfb6b078636dcdd8ae2d89b35603b727f53cc8ca32a3574647db0838289`) and
  `src/cement_runtime/__init__.py`'s `__all__` — compared as the PARSED ordered list of 57 names,
  not as source text — is unchanged (V16). PLUS binding identity (A08): each of the six exported
  model names resolves in `cement_runtime` to the SAME OBJECT as in `cement_runtime.models`, which
  an aliasing re-export (`from .models import Resolved as _Resolved`) breaks while `__all__` stays
  AST-equal. The post-state vector is six names at `(models=True, __all__=True, package=True,
  system=False)` and `Outcome` at `(True, False, False, False)` — SEVEN definitions, SIX exports
  (X06, X34, C10). The models survive without producers; deleting them is M3.6a3's and doing it
  here would take that unit's measurement with it.

### Preserved invariants

- **L13** the surviving `requests` sites in `system.py` are exactly SEVEN — `_proposal_bindings` 4,
  `_write_proposal_request_status` 2, `_persist_proposal` 1 — pinned by THREE instruments whose
  disagreement is the finding: hit LINES (7), standalone WORD occurrences (7, per-line multiplicity
  1, so a second reference cannot be packed onto an existing line — X20), and parsed SQL string
  CONSTANTS with their verbs (`SELECT` x4, `UPDATE` x2, `INSERT` x1), which excludes comments and
  docstrings and follows a statement moved to a new line (X30). Ownership binds to the NEAREST
  lexical `FunctionDef`, never to an outer `ast.walk`, and the pin compares the exact multiset
  `{owner: count}` PLUS owner KIND, so a site relocated into a newly nested helper fails instead of
  being attributed to the expected outer function (A12). Corrected by C04 from `eleven`, which
  contradicted section 1's own inventory. Corrected again by C09: `_proposal_bindings` and
  `_write_proposal_request_status` are module-level FUNCTIONS but `_persist_proposal` is a `System`
  METHOD, so a class-body-only scan sees ONE surviving site, not zero.
- **L14** `SCHEMA_VERSION` stays 2 and `src/cement_runtime/store.py` is byte-identical to its
  `da70a56` blob.
- **L15** `propose`, `submit_proposal`, `get_proposal`, `review` and `resolve` are byte-identical to
  their `da70a56` spans, under the whole-line `lineno..end_lineno` convention with trailing newlines
  stripped. That convention is M3.3's P06 convention; a column-offset slice measures four bytes
  shorter and is a different claim. TWO PRECONDITIONS BIND BEFORE THE COMPARISON. First, definition
  CARDINALITY: exactly one `FunctionDef` per name, asserted first, because a name-keyed span map
  silently drops a duplicate and compares the base-identical copy while Python binds the other
  (X36). Second, the span STARTS AT `min(decorator lineno, def lineno)` and the baseline decorator
  vector — EMPTY for all five — is asserted: `FunctionDef.lineno` points at `def`, so adding
  `@staticmethod` leaves every compared byte identical while changing the runtime binding (A13).
- **L16** the proposal round trip still ends with the private request row `resolved`: propose,
  review-accept, then read the row through the store and assert `status = 'resolved'` with its
  `output_json` and `example_id` set. The row must be the CONFIRMED variant — `source_kind =
  'confirmed'`, `artifact_id` NULL, `proposal_id` bound to the reviewed proposal, `example_id` bound
  to the `ReviewResult` — or the three named fields pass on a malformed artifact-shaped row (X35).
  A REJECT round trip is required beside it (A14): `_write_proposal_request_status` has a dedicated
  rejection branch that the accept path never executes, so an accept-only probe leaves half the
  helper unobserved and the claim `this is the probe that proves it` false for that half.
- **L17** `revise_operation` still bumps the revision by one and still retires `draft`, `verified`
  and `promoted` artifacts at the previous revision with `status_reason = 'operation revised'`.
- **L18** `_now` still rejects a non-`int`, a `bool`, a negative value (all three `StateError`, with
  L06's exact replacement text) and a non-callable `clock_us` (`ValidationError`, message
  `clock_us must be callable`, raised by `__init__` before `_now` runs). The surviving-caller half
  is stated as an exact CALL-SITE set, never as caller identity: the methods calling `self._now()`
  are EXACTLY the twelve remaining after `handle`, `_fail_generation` and `request_status` go —
  `register_operation`, `revise_operation`, `_persist_proposal`, `review`, `compile`,
  `verify_drafts`, `verify`, `promote_function`, `promote`, `challenge`, `revoke_example`,
  `suspend_artifact` — and each holds exactly one call spelled `self._now()`. The original wording
  (`every surviving caller of _now is unchanged`) was SELF-CONTRADICTORY, because
  `revise_operation` is both a surviving caller and an L07/L08 edit target whose body legitimately
  shrinks; whole-method equality is NOT expected for it (A15, X08). MAIN measured 15 callers at
  `da70a56`.

### Prose

EVERY PROSE OBLIGATION SPLITS IN TWO AND THE HALVES ARE GRADED DIFFERENTLY (A16). The MECHANICAL
half is a battery assertion. The SEMANTIC half — whether replacement prose describes SURVIVING
behaviour — is MAIN's ruling, recorded in section 8 at closure, because a token predicate accepts
`Never call propose or review; use the legacy lifecycle dispatcher`, which names both required
symbols and is false. Claiming a test decides the semantic half would be a guarantee-vs-claim gap.

- **L19** MECHANICAL: `README.md` contains zero standalone `handle` words (baseline 8) and zero
  `request_status` substrings (baseline 4), counting code fences, links and inline code, all of
  which ship to readers (V23); zero Markdown tables whose `Status`-headed column carries any frozen
  lifecycle poll state (`resolved`, `review_required`, `in_progress`, `fallback_failed`, `rejected`,
  `reconciliation_required`) — that structural shape IS the poll-state table, so a renamed heading
  does not evade it; zero generation/request LEASE claims, while the two truthful `a verification
  snapshot is not a lease` statements SURVIVE, so the ban is context-classed rather than a global
  word ban that would delete correct prose to reach zero (X25); and the surviving Library API region
  still names `System.submit_proposal`, `System.propose`, `System.review` and `proposal_id` at least
  once each — L19 is CONJUNCTIVE, and deleting the lifecycle section is necessary, never sufficient
  (X09). RULED: that the replacement request-route prose teaches the proposal route correctly.
- **L20** MECHANICAL: `docs/architecture.md`'s Contract H2 ordered-list items 1-3, identified
  structurally so later list text stays free, contain `propose` >= 1 AND `review` >= 1 (MAIN rules
  the implicit question YES — both, not either) and `handle` == 0; zero paragraphs match
  `candidate generation` together with a standalone `lease` (V24). RULED: that steps 1-3 describe
  the surviving flow in the right order.
- **L21** MECHANICAL: `docs/adapter-protocol.md` matches zero deleted-surface tokens across prose,
  code fences and examples; `fallback_failed` reaches 0. TWO RETENTIONS bind, because M3.7
  relocates this file under BYTE EQUALITY and a wrong deletion here is permanent too. First, the
  `"request_id"` JSON wire key SURVIVES (X16), described as an opaque per-call tracing identifier —
  `CandidateRequest.request_id` is M3.6a3's and byte-frozen `propose` still constructs it; the
  `\brequests?\b` ban never reaches it because `_` is a word character. Second, `System.propose`'s
  failure contract survives (X26): the document still names `CandidateSourceError` and one concrete
  no-write observable (proposal count 0, event count 0), while `handle`'s inert fallback branch
  goes. RULED: that the rewritten protocol description is true of the surviving adapter path.
- **L22** MECHANICAL: `docs/threat-model.md` matches zero standalone `handle` or `lease` lines
  (baseline 78 and 90); the ambiguity claim at line 61 goes while the three surviving quarantine
  causes stay (X17). RULED, and this obligation is MOSTLY semantic: the replacement states an
  application-owned idempotency key because Cement supplies none, at-most-once source invocation per
  `System.propose` call, and enumerate-pending recovery rather than retry (V26).
- **L23** all 16 census pins in section 5 are green after the rewrite, each either satisfied by the
  new prose or re-scoped with grounds recorded in section 8. Sixteen, not fifteen, by C06. ANTI-
  WEAKENING (A17): each of the 14 working-tree pins keeps its assertion body BYTE-IDENTICAL to its
  `da70a56` blob unless section 8 PERMITS the delta, and every permitted delta is enumerated
  there. Without this, `all pins green` is satisfiable by making a pin tautological — a test with an
  unreachable document read and `assertIn('handle', 'handle')` scores `reads-doc True`, `vocab
  True`, stays in the census and keeps gate 1 green. The pins are additionally EXECUTED by id, not
  merely counted (X10).
- **L24** no human-facing surface gains a NEW claim about a deleted surface. Re-run the census
  (gate 3) against the rewritten documents. THE PREDICATE BINDS A NAMED TOKEN SUBSET, not the whole
  vocabulary (A18, V27): owned hits must reach ZERO for `handle`, `request_status`, `retry_failed`,
  `invalidated_generators`, `resolved_by_artifact`, `in_progress`, `fallback_failed`,
  `reconciliation_required` and every ambiguity-quarantine promise. The literal all-token reading is
  UNSATISFIABLE and MAIN reproduced why: M3.5b's D25 requires at least two shipped paragraphs
  containing `request row stays internal`, measurement finds exactly two (`README.md`,
  `docs/architecture.md`), and the census `\brequests?\b` matches both — so a green D25 and a
  zero `requests` count cannot hold together. Every surviving generic hit (`request`, `requests`,
  `lease`, `ambigu`) therefore carries explicit GROUNDS as private-table prose or a
  non-generation-lease statement. SCANNER COVERAGE IS ITSELF PINNED (X18): the census `DOCS` tuple
  must EQUAL the tracked human-facing Markdown set (`README.md`, `docs/*.md`,
  `examples/*/README.md`, five paths at `da70a56`), so a document added during implementation cannot
  become an unscanned home for a deleted claim. THIS PARAGRAPH IS GATE 3'S INDEPENDENT ORACLE
  (A22): the expectation lives in the contract, which `--emit` cannot rewrite, so re-emitting after
  a bad rewrite now contradicts a number MAIN authored rather than blessing the tree.

### Tripwire repairs

- **L25** M3.5b's D15a (`tests/test_cli_removal_battery.py:1131`, assertion `:1158`) is re-scoped to
  the closed range `36f7890..1146421`, exactly as M3.6a1 re-scoped its siblings D15b (`:1160`) and
  D22b (`:2766`). The repair is a family repair: after it, no D15/D22 clause reads the working tree
  for a runtime module.
- **L26** the four P06 span freezes are RETIRED with their history preserved, not re-based: they
  freeze the bytes of a method that no longer exists. Retirement DERIVES all three figures
  (`12,866 B / 1182130a2b3a`, `12,867 B / cd60036faf5c`, `12,862 B / c27e71b0b4c7`) from git object
  `3b7769b` on EVERY RUN and compares them; recording them as prose leaves a copied typo satisfying
  a text-presence assertion while disagreeing with history, and the only executable recomputers
  today are the frames being retired (A19). All FOUR test identities stay DISCOVERABLE — one
  aggregate replacement erases three independent tripwire records even where the figures appear
  once (X21) — and none reads the working-tree `System.handle` span. L15 replaces their protective
  value for the methods that survive.
- **L27** M3.5b's D01 (`tests/test_cli_removal_battery.py:608`, assertions `:617` + `:618`) is
  INVERTED: it
  asserted `System.handle` and `System.request_status` still ship as library methods; it now asserts
  their absence. An inverted pin keeps the obligation and reverses the predicate; deleting it would
  delete the behaviour's only pin along with the behaviour. The inversion PAIRS absence with
  positive identity controls in the same test — `System.__module__ == 'cement_runtime.system'` and
  `callable(System.propose)` — or both negative assertions pass against an empty dummy class
  (X12), and D01's existing CLI leaf-set complement stays green beside them, which is the two
  non-overlapping subproperties that make retention worth more than deletion (A20).
- **L28** `tests/test_authority_removal.py:118 test_system_constructor_shape` is rewritten to the
  three-parameter signature and keeps asserting defaults for the parameters that remain.
- **L29** `m3u6a2-tripwires.py`'s `_freezes()` detector is widened to see the P06 family, behind a
  self-test control that FIRES on a P06 frame. Today it requires the literal
  `cement_runtime/system.py` or `System.handle` AND one of `read_bytes()`/`getsource`/`_git_bytes(`,
  while the four P06 frames reach the same source through `cement_runtime.system.__file__`,
  `inspect.getsourcefile(System)` and a `_source(ROOT, path)` helper — so the instrument reported
  `FREEZES: 4` over a set DISJOINT from the four freezes this unit actually inverts, and its 6/6
  self-test covered none of that negative space. THE CONTROL RUNS AGAINST AN IMMUTABLE SYNTHETIC
  P06 SOURCE FIXTURE, never a live frame, because L26 empties the live positive set in this same
  unit — after retirement a working detector and one returning no P06 rows are otherwise
  indistinguishable (A21). Detection is factored into a `_is_freeze(segment)` seam so it can be
  probed directly, and the control is a PAIR: the P06 shape must be INCLUDED, and the same source
  acquisition selecting a PRESERVED method (`propose`) must be EXCLUDED, or over-reporting
  satisfies the positive half alone (X14, V30). Live `_freezes()` stays 4 and `--self-test` goes
  8/8. If widening proves to over-report, record the exclusion with grounds instead; what is not
  acceptable is leaving a detector whose name promises the family it cannot see. The battery's own
  file stays excluded from both scanners (C06, X22).
- **L30** M3.6a1's D16 (`tests/test_migration_battery.py:993`) is re-scoped to the CLOSED range
  `6fb4d92..dc4ab5e` — M3.6a1's baseline and its own DONE tip — on BOTH halves: the expected path
  set and the per-path byte comparison, which read `HEAD` and the working tree respectively. Read
  against `HEAD`, D16 asserted that M3.6a1's surgery script reproduces every LATER unit's `tests/`
  and `examples/` edits, which no script pinned to an earlier baseline can do. It is the same family
  as D15a (L25), and it is stricter: D15a inverts when this unit EDITS a runtime module, while D16
  inverts when this unit ADDS ANY FILE under `tests/` or `examples/` — the battery seed alone
  tripped it. Its repair therefore lands NO LATER THAN the first commit that adds a file under
  `tests/` or `examples/`. `Before` was the wrong word (X33, C11): git has no intra-commit
  ordering, and `7cfc748` both repaired D16 and added the seed, which satisfies the practical
  reading and needs no history rewrite. D16's closed expected-path set is an exact eight-member
  historical delta, not merely a nonempty one (X23), and BOTH halves use `6fb4d92..dc4ab5e` (X15).
- **L31** AMBIGUITY QUARANTINE IS REMOVED AS A BEHAVIOUR, not merely as an event spelling (A10).
  After this unit no code path suspends an artifact with reason `ambiguous active scope`: that
  reason string has zero occurrences in `src/`, and a probe that drives the duplicate-promotion
  condition leaves BOTH artifacts `promoted` with their promotion receipts intact and emits ZERO
  ambiguity events. `tests/test_system.py`'s surviving assertion is INVERTED to that post-state
  rather than deleted (V15). This obligation exists because C05 reclassified the quarantine as a
  deleted behaviour while L11 pinned only its vocabulary — a renamed private path could keep the
  storage mutation, emit an allowed kind and satisfy the sixteen-kind set — and because section 2.1
  gave the clock widening its own obligation on exactly this reasoning.

## 4. What this unit does NOT do

- It deletes no model. `Resolved`, `InProgress`, `FallbackFailed`, `Rejected`,
  `ReconciliationRequired`, `ReviewRequired` and the `Outcome` alias survive, exported and
  unproduced, until M3.6a3.
- It deletes no `CandidateRequest` field. `request_id` is M3.6a3's, and the 34-break concentration
  in `test_hospital_ocr_example.py` and `test_source.py` is that unit's burden, not this one's.
- It changes no schema. The `requests` table, its indexes and `SCHEMA_VERSION` 2 are M3.6b's.
- It relocates nothing. `docs/adapter-protocol.md` is REWRITTEN here and RELOCATED by M3.7.
- It adds no gate to a closed contract. Gates are fixed by section 6 before implementation starts.

## 5. Tripwires, numbered rather than met as regressions

Two instruments, disjoint surfaces. The burden stages measure what the CODE DELETION breaks; the
census measures what the PROSE REWRITE breaks. The burden set already contains D15a and all four P06
freezes. NOT ONE of the 15 census pins appears in any stage's frame set, because no burden stage
rewrites a document. Read each instrument for its own surface; neither covers the other's.

### 5.1 Pins that invert, all of them inside the measured burden

| pin | def | assertion | red at stages | repair |
|---|---|---|---|---|
| M3.5b D15a | `tests/test_cli_removal_battery.py:1131` | `:1158` | 1, 2, 3 | L25 — re-scope to `36f7890..1146421` |
| M3.3 P06 | `tests/test_submission.py:670` | `:692` | 1, 2, 3 | L26 — retire with figures recorded |
| M3.3 P06 | `tests/test_submission_battery.py:289` | `:307` | 1, 2, 3 | L26 |
| M3.3 P06 | `tests/test_submission_battery.py:329` | `:337` | 1, 2, 3 | L26 |
| M3.6a1 D25 | `tests/test_migration_battery.py:1322` | `:1338` | 1, 2, 3 | L26 |
| M3.5b D01 | `tests/test_cli_removal_battery.py:608` | `:617` + `:618` | 1, 2, 3 | L27 — invert |
| constructor shape | `tests/test_authority_removal.py:118` | `:120`-`:126` | 2, 3 | L28 — rewrite to three parameters |

The constructor-shape row is red at stages 2 and 3 ALONE, because the lease keyword survives stage
1. Its stage membership is the evidence that the lease deletion is a separate observable change and
not a side effect of removing the methods.

D15a is the sharpest of these: scope MIXED, it compares the WORKING TREE against `36f7890` for six
runtime modules including `system.py`, so it inverts the instant this unit edits one.

`B02` is NOT a tripwire: its frozen tuple is `_command_supervisor.py` and `example_adapter.py`
alone, and `system.py` was never a member.

### 5.2 Prose pins, none of them reachable by the deletion (census, `m3u6a2-tripwires.json`)

| scope | test | locus |
|---|---|---|
| WORKING-TREE | `test_x20` | `tests/test_cli_channels.py:2491` |
| WORKING-TREE | `test_x29` | `tests/test_cli_channels.py:2940` |
| WORKING-TREE | `test_x30` | `tests/test_cli_channels.py:2990` |
| WORKING-TREE | `test_d23` | `tests/test_cli_channels_battery.py:2488` |
| WORKING-TREE | `test_d22a` | `tests/test_cli_removal_battery.py:2685` |
| WORKING-TREE | `test_d23` | `tests/test_migration_battery.py:1282` |
| WORKING-TREE | `test_b25` | `tests/test_proposal_binding_battery.py:2088` |
| WORKING-TREE | `test_b26` | `tests/test_proposal_binding_battery.py:2123` |
| WORKING-TREE | `test_b27` | `tests/test_proposal_binding_battery.py:2176` |
| WORKING-TREE | `test_d25` | `tests/test_submission_battery.py:1541` |
| WORKING-TREE | `test_d33` | `tests/test_submission_battery.py:1774` |
| WORKING-TREE | `test_d34` | `tests/test_submission_battery.py:1791` |
| WORKING-TREE | `test_d41` | `tests/test_submission_battery.py:2223` |
| MIXED | `test_d25` | `tests/test_cli_removal_battery.py:3046` |
| GIT-RANGE | `test_d22b` | `tests/test_cli_removal_battery.py:2766` |
| GIT-RANGE | `test_d22c` | `tests/test_cli_removal_battery.py:2875` |

The two GIT-RANGE rows assert a closed historical diff and are SAFE by construction. The fourteen
others read the working tree and are L23's work list. `test_x29` entered under C06's widened
vocabulary on an incidental `ambiguous` and is RETAINED rather than filtered: it reads shipped prose
this unit rewrites, so it is a genuine work-list row whatever admitted it, and under-inclusion costs
a red gate at closure where over-inclusion costs one verification.

The census's own `FREEZES: 4` field names D15a, D15b, D22b and D22c — a set DISJOINT from the four
P06 freezes above, sharing only the count. L29 is the repair.

### 5.3 Addition tripwires — what breaks when this unit ADDS a file

Neither instrument covers this class. The burden stages only delete and the census only reads
documents, so the first file this unit committed is what found the class. Added by C03.

| pin | locus | trips on | repair |
|---|---|---|---|
| M3.6a1 D16 | `tests/test_migration_battery.py:993` | ANY new or edited path under `tests/` or `examples/` | L30 — close both halves to `6fb4d92..dc4ab5e` |
| M3.6a1 D28 | `tests/test_migration_battery.py` | any commit where gate 1 is red | none — the seed SKIPS instead of failing |

D16 is stricter than D15a: D15a inverts when a runtime module is EDITED, D16 when any test or
example file is ADDED. Its repair lands before every other edit rather than beside them. D28 needs
no repair, but it makes a deliberately-red commit permanently costly, because history keeps the red
revision after the unit that made it green closes.

## 6. Gates — the numbered list every closure claim reruns from committed state

A gate added mid-unit invalidates these pins instead of strengthening them. Adding one is a
correction in section 8, and every closure claim after it reruns the whole list.

A GATE'S IDENTITY IS (COMMAND, ACCEPTED LANGUAGE), never the pathname alone (C07). Repairing a
gate's INSTRUMENT — new vocabulary, a new excluded file class, a new failure mode, moved expected
rows — is a numbered correction that VOIDS prior runs of THAT gate and requires the FULL numbered
list to rerun at the next closure claim. It is not an added gate, so the numbered pins survive.

1. `uv run python -m unittest discover -s tests -t .` — green, with the post-state test count
   recorded beside the claim.
2. `uv run python .agent/decisions/m3u6a2-battery-validate.py` — every `L<n>` in section 3 is
   covered by AT LEAST one battery test, ids are contiguous, no test names an id the contract does
   not define, and no test is still a seed stub. Coverage is a FLOOR, corrected by C02.
3. `uv run python .agent/decisions/m3u6a2-tripwires.py` — the census reruns against the
   post-state tree and matches the committed expectation, including the L29 detector repair and its
   self-test controls.
4. `uv run python .agent/decisions/m3u6a2-closure.py` — dangling references (L09), the `.models`
   import delta (L10), `request.*` emission sites (L11), the surviving `requests` site inventory
   (L13) and the byte-identity pins (L12, L14, L15), each as an independently reported check.
5. `uv run python .agent/decisions/m3u5b-doc-parse.py` — M3.5b's documentation parser stays green
   across the prose rewrite.
6. `uv run python .agent/decisions/m3u6a2-rule-attack.py --check` — every attack row is ruled and
   the ruled ids match the committed set.
7. `uv run python .agent/decisions/m3u6a2-mutants.py --replay` — the mutation catalogue replays by
   unique anchor with a per-mutant liveness proof and a pristine control.
8. The reversion sweep over the battery: every clause dies when its subject is reverted, one row per
   SUBPROPERTY rather than one per clause, with grounded exclusions printed on every control line.

## 7. Battery

`tests/test_lifecycle_removal_battery.py`, one `test_l<n>_...` per obligation, authored diff-blind
against this contract and required RED at `da70a56` for every obligation that asserts a post-state.
An obligation asserting a preserved invariant (L12, L14, L15, L16, L17, L18) is legitimately GREEN
at baseline; the report states which, and MAIN owns the red-at-baseline / green-at-HEAD credential
rather than forcing it.

Clause discipline, carried from M3.6a1's sweep:

- A clause is a CONJUNCTION. One row per clause certifies only that the clause has SOME live
  content; the sweep catalogue enumerates SUBPROPERTIES.
- Never draw a clause's work list from a post-state census whose emptiness is another gate's
  acceptance criterion. Draw it from the baseline census or the frozen opening set.
- Re-derive every asserted literal from the baseline blob rather than retyping it.
- Name ONE source per clause. A clause running one half against a committed blob and the other half
  against the working tree cannot go red during development.
- A clause whose subject is committed history is insensitive to every working-tree mutation and
  takes a GROUNDED EXCLUSION from the sweep, printed on every control line, rather than a row.

GATE 8'S EXCLUSION CATALOGUE IS FIXED HERE, not chosen at sweep time (A23), because an open-ended
exclusion list hides omissions behind the same word that legitimises them:

| excluded subject | grounds |
|---|---|
| L23's D22b pin | git-only endpoints; no working-tree mutation can redden it |
| L25's D15a AFTER the repair | its six per-module comparisons become closed-range `36f7890..1146421` |
| L26's three historical span figures | derived from `3b7769b`; immutable under any tree edit |
| L30's D16, BOTH halves | expected path set and per-path blob comparison both read `6fb4d92..dc4ab5e` |

D22c is MIXED and gets LIVE ROWS despite the census label: it reads live `README.md` beside a git
blob, so its live half is mutable and must die under reversion. Every exclusion prints on the
control line as an explicit test-id selection, since `unittest` has no negative selector, and cost
never grounds an exclusion — insensitivity does.

## 8. Corrections to this contract

Each correction states the obligation it binds explicitly in its own text; a correction whose
subject is a section rather than a numbered clause legitimately binds none, and illustrative ids
stay out of any text a binder parses.

- **C01** — binds SECTION 9 ALONE, no obligation, and leaves section 6's gate list untouched. The
  session table as first written put implementation at S3 and the battery at S5, which inverts the
  project's own order: the red suite sits in the primary tree and runs RED before implementation
  starts, and the battery is authored DIFF-BLIND against this contract, which is impossible once the
  diff exists. The corrected table below dispatches wave 2 at S3 and implements at S4. No predicate
  moved, so no closure claim built on section 6 is affected.
- **C02** — binds GATE 2 in section 6, no obligation. Gate 2 first read "covers every `L<n>` exactly
  once". An identity makes coverage a ceiling as well as a floor, so a second test for one
  obligation fails the gate and extension needs permission. M3.6a1 measured the cost of the same
  shape from the other side: its 29-row seed grew to 92 rows over the same 29 clauses once the
  catalogue was filled per SUBPROPERTY, and the one-row-per-clause reading was blind to three dead
  conjuncts. Coverage is a FLOOR of one; ORPHAN and STUB are the identities.
- **C03** — ADDS L30 and adds a THIRD tripwire class to section 5. The two instruments measured what
  the DELETION breaks and what the PROSE REWRITE breaks; neither could see what an ADDITION breaks,
  and committing the battery seed is an addition. It tripped M3.6a1's D16 immediately. Section 6's
  gate list is unchanged, so no closure claim is affected; gate 2's contiguity check absorbs the new
  id. The seed's stub body also SKIPS rather than fails, because M3.6a1's D28 asserts gate 1 is
  green at EVERY commit in its range and history keeps a red revision after the unit that made it
  green closes.

- **C04** — binds L13 alone. L13 read "exactly eleven" surviving `requests` sites while section 1 of
  this same contract inventoried SEVEN and named all seven line numbers. Measured at `da70a56`: 20
  `requests` lines total, 13 inside deleted spans (`handle` 9, `_fail_generation` 2, `request_status`
  1, `revise_operation` 1), 7 surviving at 534, 547, 574, 591 (`_proposal_bindings`), 643, 653
  (`_write_proposal_request_status`) and 893 (`_persist_proposal`). A diff-blind author encoding
  `eleven` would have gone red against correct code, which is the whole cost of an unverified number
  in a contract.

- **C05** — binds L11 and section 2's item 7. L11's set was wrong in three independent ways and the
  root cause is one fact the contract never recorded: `artifact.ambiguity_quarantined` is emitted at
  `handle:1143` and nowhere else, so deleting `handle` deletes ambiguity quarantine. L11 therefore
  (a) RETAINED a kind that loses its only producer, (b) omitted `artifact.challenged` and
  `artifact.verification_failed`, hidden because their `kind=` argument is an `IfExp` whose second
  branch a first-branch scan never reads, and (c) omitted `proposal.accepted` and `proposal.corrected`,
  hidden because their `kind=` argument is an f-string over a `Literal["accepted", "corrected"]`
  annotation. Thirteen becomes SIXTEEN and the derivation is stated in L11 itself, because a set
  obligation whose derivation is unstated is re-derived by every reader under whichever spelling it
  happens to know. Section 2's "two event kinds" becomes three for the same reason.

- **C06** — binds L23 and L24, and re-measures section 1.2 and section 5.2. Two repairs to
  `m3u6a2-tripwires.py`, both grounded. FIRST, the vocabulary gains `ambigu`: by C05 the ambiguity
  quarantine is a deleted surface, and `README.md:49` plus `docs/threat-model.md:61` each claim it
  while no other token in the convention reaches either line, so the prose work list was missing two
  lines and L24's owned-hit predicate could have read zero over a README that still promised the
  behaviour. `idempot` was measured as a candidate and EXCLUDED with grounds: it adds 11 lines of
  which 9 correctly describe the surviving proposal API, and a token whose hits cannot legitimately
  reach zero makes L24 unsatisfiable. SECOND, the scanners now exclude
  `tests/test_lifecycle_removal_battery.py`. This unit's battery quotes the contract's obligation
  text in its docstrings, so committing the seed alone took PINS 15 -> 18 and FREEZES 4 -> 5 and left
  GATE 3 RED from that commit onward — the census counted its own instrument, and it would have
  drifted again on every battery edit through S4 and S5. Post-repair: PINS 16, PINS-WORKING-TREE 14,
  FREEZES 4, PROSE-HIT-LINES 50, `--self-test` 7/7 firing with a new SELF-REFERENCE control. The
  `test_migration_battery.py` D23 pin also moved `:1269` -> `:1282` under L30's own repair, which is
  drift the committed table had never absorbed. No gate was added; gate 3's instrument was repaired
  and its expectation re-emitted.

## 9. Session boundaries

Budget 9, no pre-open split. Every candidate seam was measured and rejected: a deletion-layer split
is the 46:10 imbalance M3.6a already rejected; consumer-migration relief was measured ABSENT
(46 -> 47 frames); the only clean seam, prose, would ship a DONE state whose README documents a
deleted method; and two kernel units duplicate the ~6 machinery sessions that dominate the cost
(2x6+3 = 15 > 9). The overrun records against 9.

Corrected by C01.

| session | buys |
|---|---|
| S1 | burden + tripwire measurement, sizing and ownership rulings — DONE |
| S2 | this contract — DONE |
| S3 | wave 2 in one block: `test-m3u6a2` phase 1 against section 3, `attack-m3u6a2` against this contract; MAIN batch-rules the phase-1 table |
| S4 | the batch ruling — 96 rows into sections 1, 3, 6, 7 and 8 through `m3u6a2-rule-attack.py`; phase-2 re-dispatch |
| S5 | harvest the phase-2 red suite, credential it red at `da70a56`, implement the deletions, the two edits and the import shrink against it |
| S6 | prose rewrite over the four owned documents plus the tripwire repairs L25-L29 |
| S7 | battery verdict ruling and `m3u6a2-closure.py` (gate 4) |
| S8 | mutation catalogue and gate 7 |
| S9 | reversion sweep, gate list rerun, DONE commit |

Corrected again by C07's session accounting: S3 did not buy the batch ruling C01's table assigned
it, so the ruling took S4 whole and every later session shifts by one. The attack ruling C01 placed
at S7 landed at S4 instead, which is where its blocking rows had to be answered before a diff-blind
author could encode them. The budget of 9 absorbs the shift with no session left over.

S4 then bought back the shift. A compaction gave it a second full window, so one session carried the
96-row ruling, the phase-2 dispatch and harvest, both baseline credentials, and the whole code
implementation — S5's cell as the table wrote it. The remaining work is the prose rewrite (L19-L24),
the tripwire repairs (L25-L29) and L31's test-inversion half, which is S6 and S7 unchanged. Sessions
are counted by what they buy, never by the number in the table, and the overrun still records
against 9.

## 10. Interpretive grounds

- SIZE BY NORMALISED FRAMES, NEVER BY BREAK COUNT. The count is not monotone under cumulative
  deletion and two stages sharing a count can have different failure sets.
- THE PROSE IS PART OF THE DELETION, not a follow-up. A green suite plus a prose assertion is never
  closure for a removal, because deleting a behaviour together with its pin keeps the gate green.
- AN INVERTED PIN IS THE DEFAULT REPAIR for a tripwire whose subject this unit removes. Retirement
  needs grounds, and L26 has them: the P06 freezes pin the BYTES of a span that ceases to exist,
  which no inversion can express, while L27's D01 pins the EXISTENCE of two methods and inverts
  cleanly.
- EVERY BYTE-IDENTITY CLAIM NAMES ITS BASE OBJECT. `da70a56` is this contract's base; a claim
  against the working tree is a claim that inverts the moment the unit starts, which is exactly the
  D15a defect L25 repairs.

- **C07** — binds SECTION 6 and GATE 3, no obligation. A24 asked whether repairing gate 3's
  INSTRUMENT at S3 is an added gate under this contract's own rule. Ruling: it is NOT — the pin is
  the numbered LIST and C06 added no entry, and no closure claim is unbuilt because none existed
  (S2 claimed gate 1 alone, while gate 3 was in fact RED at that commit). The substance stands: a
  gate's identity is (command, ACCEPTED LANGUAGE), and C06 changed the accepted language by adding
  `ambigu` to the vocabulary, excluding a file class, adding a failure mode and moving expected
  rows. Section 6 therefore reads: an INSTRUMENT change is a numbered correction that VOIDS prior
  runs of that gate alone and requires the FULL numbered list to rerun at the next closure claim.
  Gate 3's post-C06 expectation stands. `--emit` is additionally forbidden after S3's re-emission
  except through a numbered correction, and L24 now carries gate 3's independent oracle in contract
  prose that `--emit` cannot rewrite.

- **C08** — binds L11 and corrects C05. C05's supporting count of `20` `_event` calls is wrong: MAIN
  measured NINETEEN static calls at `da70a56` (16 `Constant`, 2 `IfExp`, 1 `JoinedStr`), falling to
  FOURTEEN post-state, while the textual `_event(` count is 20 because the DEFINITION line matches.
  The sixteen-kind SET is unaffected — it was derived per call site, not from the total — but a
  structural count inside a correction written to fix structural counts is exactly the shape this
  unit keeps paying for, and a battery treating 20 as a completeness control would reject correct
  code. The call count is REPORTED, never used as a completeness control; L11's total-accounting
  clause is what closes the form gap instead.

- **C09** — binds L09 and L13, and corrects C04 and section 1. TWO measured errors. FIRST, L09's
  `zero occurrences` for `request_status` is FALSE-BY-CONSTRUCTION against L15: `da70a56` holds
  EIGHT `request_status` NAME tokens in `system.py`, deleting the method removes line 1546 alone,
  and the seven survivors at 458, 503, 1529, 1532, 1535, 1542 and 1579 are proposal plumbing — the
  last inside byte-frozen `get_proposal`. L09 now pins the exact per-name vector with
  `request_status` at SEVEN, and L02 carries the `System`-attribute claim. SECOND, C04 and section 1
  called all three surviving `requests` owners module-level FUNCTIONS; `_persist_proposal` is a
  `System` METHOD, so a class-body-only scan sees ONE surviving site, not zero. Both errors were
  reachable only by running the count.

- **C10** — binds L12 and section 1. Section 1 said this unit `leaves seven exported models`.
  Measured: `__all__` holds 57 names and `Outcome` is NOT among them — it is a models-only alias.
  The state M3.6a3 inherits is SEVEN definitions in `models.py`, SIX package exports, and ZERO of
  the seven imported into `system.py`. L12 additionally binds EXPORT IDENTITY rather than `__all__`
  text, because an aliasing re-export leaves the parsed `__all__` equal while the binding moves.

- **C11** — binds L30. `Its repair therefore lands BEFORE every other edit` is unsatisfiable as
  written: git has no intra-commit ordering, and `7cfc748` both repaired D16 and added the battery
  seed. Corrected to `NO LATER THAN the first commit that adds a file under tests/ or examples/`,
  which the measured history satisfies. The alternative was rewriting published local ancestry to
  buy a distinction with no observable.

- **C12** — binds SECTION 3's prose obligations (L19-L22), no gate. Each splits into a MECHANICAL
  half the battery asserts and a SEMANTIC half MAIN rules and records at closure. Measured grounds:
  the committed census vocabulary scores `vocab-hit False` on `Never call propose or review; use the
  legacy lifecycle dispatcher` and on `Use the proposal identifier as an idempotency key`, so a
  token predicate accepts prose that is false about surviving behaviour. Asserting that a test
  decides the semantic half would be a guarantee-vs-claim gap of exactly the kind this unit's own
  reviewers are dispatched to find.

- **C13** — binds NO obligation and NO gate; it records an instrument repair outside the numbered
  list. `m3u6a2-wave2-validate.py`'s `CONCRETE` regex required a TWO-digit number, so it rejected 14
  verdict rows whose observable is a single-digit count (`prints exactly 7 hit lines`), a boolean,
  an empty collection or an exception class — every one of them checkable. The verdicts table
  therefore graded FAIL (14 findings) at harvest while the attack table passed, and the S3 record's
  `validator PASS` covered the attack table alone. Widened to admit any integer, `True`/`False`/
  `None`, `[]` and an `*Error`/`*Exception` class name; re-graded BOTH ways — 66/66 concrete and
  PASS, a seeded vague-prose expectation still FAILS with rc 1, `--self-test` 8/8 firing. The
  wave-2 validator is a pre-dispatch grading tool and is not in section 6, so no gate pin moves.

- **C14** — binds GATE 3's command text alone. Section 6 wrote
  `m3u6a2-tripwires.py --check`; the instrument accepts only `--emit` and `--self-test`, and the
  BARE invocation is its check mode, so the gate as written exits 2 on an unrecognized argument and
  could never have been run. Corrected to the bare command. This narrows nothing and widens
  nothing — an unrunnable gate has no accepted language to change — but it is the second time this
  unit found a contract number or command that no one had executed, which is the standing reason
  every gate is rerun from committed state rather than cited.

- **C15** — binds GATE 2's instrument, `m3u6a2-battery-validate.py`, and no obligation. Its
  CORRECTION-BIND check accepted an obligation id, `binds SECTION n` or `binds GATE n` and nothing
  else, so C13 — a legitimate repair of an instrument outside section 6 — graded UNBOUND and gate 2
  failed on a second count beside its expected `STUB`. The check now accepts a fourth form: an
  explicit `binds NO obligation` that ALSO names the repaired file, since a bare declaration would
  be a free bypass for every later correction. Re-graded both ways, `--self-test` 6/6 with the new
  control (an explicit none naming no file still fires). Per C07 this VOIDS gate 2's prior runs and
  the next closure claim reruns the full numbered list; no closure claim cites one, because gate 2
  is legitimately red until the battery is filled.

- **C16** — binds L12, L18 and SECTION 7. Section 7's baseline-green list is written per OBLIGATION
  and three of its members are MIXED, so a diff-blind author reading it literally would have made
  post-state predicates green at `da70a56`. The classification is SUBPROPERTY-level: legitimately
  green at baseline are L14, L15, L16, L17, L12's preservation half (`models.py` byte-identity, the
  ordered `__all__`, export-binding identity) and L18's non-callable-`clock_us` half
  (`ValidationError`, message `clock_us must be callable`). Red at baseline are L12's
  `(models, __all__, package, system)` post-state vector — `system.py` still imports all seven names
  there — and both of L18's remaining halves, since L06 replaces the `StateError` text and the
  caller set falls 15 -> 12. MAIN's measured credential over the delivered battery: 59 tests, 48 red
  methods at HEAD pre-implementation (55 failure records, 0 errors, rc 1) and 50 red at `da70a56`,
  where four rows ERROR on a `FileNotFoundError` for `m3u6a2-tripwires.py` because the pinned
  baseline predates this unit's own instruments.

- **C17** — binds L23. Its ANTI-WEAKENING clause freezes each of the 14 working-tree pin bodies
  byte-identical to `da70a56` unless section 8 permits the delta, and section 8 enumerated NO
  permitted delta — which makes L23 and L19-L22 jointly unsatisfiable, because correct prose removal
  necessarily inverts pins that assert the removed prose POSITIVELY. Three are measured and
  PERMITTED-AND-REQUIRED to invert, each to the new post-state rather than to a weaker predicate:
  `test_b27_no_public_surface_retains_the_unqualified`
  (`tests/test_proposal_binding_battery.py:2176`) requires README to contain
  `` The older `System.request_status` and `System.handle` lifecycle values still report `resolved` ``,
  which L19 deletes; `test_d23_there_is_no_idempotency_two_byte_identical_submissions_ret`
  (`tests/test_cli_channels_battery.py:2488`) carries the positive control
  ``call `System.handle` again with `retry_failed=True``, whose ROLE — keeping D23's scoped absence
  assertion non-vacuous — must be re-based onto a surviving retry-advice locus, never deleted (A08);
  `test_d34_readme_and_the_three_normative_docs` (`tests/test_submission_battery.py:1791`) requires
  `` steps 1 to 3 describe `handle`, the request lifecycle `` and `` through `handle` ``, which L20
  and L21 delete. The enumeration is a FLOOR that the prose session extends by MEASUREMENT under the same
  standard: a permitted delta names the pin, the deleted claim that forces it, and the post-state the
  inverted body asserts. `test_d22a_direction_cli_route_every_cli_route_locus_was_rewritte` is
  UNMEASURED — its docstring locus table is not its assertion body — and takes no permission until
  the rewrite shows one is needed. D22c's scope is section 7's `MIXED`, not the census row's
  `GIT-RANGE`: it reads live `README.md` beside a git blob, so its live half gets rows in gate 8.

- **C18** — binds L24. Its grounds catalogue admits a generic `request` hit only as private-table
  prose or a non-generation-lease statement, and a third class is required by pins L23 freezes:
  NEGATIVE REQUEST-IDENTITY CLAIMS. `README.md:332` reads `It carries four fields and no request
  identity`, asserted by `tests/test_proposal_binding_battery.py:2104`, and `:2121` asserts
  `expose no request identifier`. Both are claims that the surviving proposal API exposes NO request
  identifier — the opposite of a claim about a deleted surface — so deleting them to reach a lower
  generic count would break a standing pin to satisfy a census. The catalogue is private-table or
  storage prose, a non-generation-lease statement, or a negative request-identity claim. The
  ambiguity-quarantine subset stays at ZERO and takes no grounds.
