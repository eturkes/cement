# M3.6a2 acceptance contract — delete the lifecycle API and rewrite the prose that documents it

Unit M3.6a2, `tier=kernel`, `tags=-`, `depends=M3.6a1`, budget `est 9 -> ?` sessions.
Base commit for every git-object pin in this contract: `da70a56`.

M3.6a1 migrated every consumer off `handle`/`request_status` while both still shipped. This unit
deletes them and everything that exists only to serve them, then rewrites the four normative
documents that still describe the deleted surface. Nothing migrates here; every consumer already
moved.

Obligation ids are `L01..L29` — a letter no other contract uses. `d`, `b`, `x`, `v` and `p` are all
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
- `request.*` event kinds: emitted at `handle:1208` and `_fail_generation:1356` and nowhere else.
- `requests` table: 20 lines over 7 methods. This unit removes 13 of them — `handle` 9,
  `_fail_generation` 2, `request_status` 1, `revise_operation` 1 — leaving exactly SEVEN over three
  methods: `_proposal_bindings` (534, 547, 574, 591), `_write_proposal_request_status` (643, 653)
  and `_persist_proposal` (893). Those are M3.4's private proposal plumbing and M3.6b's schema-cut
  targets; this unit does not touch them.

The five deleted methods form a CLOSED call-graph component whose only entries from outside it are
the two public methods being deleted. That is why the deletion needs no consumer migration and why
its closure is checkable by counting occurrences rather than by reasoning about call order.

Models: after the deletion, `FallbackFailed`, `InProgress`, `Outcome`, `ReconciliationRequired`,
`Rejected`, `Resolved` and `ReviewRequired` survive in `system.py` at their import lines ALONE
(`Resolved` also at 673, inside the `System` class docstring). Outside `system.py` they appear only
in `models.py` (definitions) and `__init__.py` (re-export plus `__all__`). This unit therefore
leaves seven exported models with no producer; deleting them is M3.6a3's, and `ReviewRequired`
losing its last producer here is the measurement behind M3.6a3's first ruling.

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

`m3u6a2-tripwires.json`, emitted by `m3u6a2-tripwires.py` at `da70a56`: PINS 15, FREEZES 4,
PROSE-HIT-LINES 48 over five documents. Hit lines count DOCUMENT LINES matching the census
vocabulary, not `handle` loci; M3.5b's D22 deferral table counted the latter, so its 18/7/8/4 and
this table's numbers are INCOMPARABLE and neither corrects the other.

| document | lines | hit lines | owner | grounds |
|---|---|---|---|---|
| `README.md` | 449 | 25 | M3.6a2 | the poll-state table, both lifecycle method names and the request-route section all describe surfaces this unit deletes |
| `docs/architecture.md` | 211 | 13 | M3.6a2 | steps 1-3 describe `handle`; the lease paragraph describes the deleted knob |
| `docs/adapter-protocol.md` | 61 | 7 | M3.6a2 | M3.7 relocates this document under BYTE EQUALITY and never rewrites a claim, so false `handle` prose left here would be RELOCATED, not deferred |
| `docs/threat-model.md` | 114 | 2 | M3.6a2 | the `handle` request ID as an idempotency key, and lease recovery, both cease to exist |
| `examples/hospital_ocr/README.md` | 247 | 1 | M3.6a1 | already rewritten by M3.6a1's D22-D23 transcript regeneration; the surviving hit names no deleted surface |

Owned hit lines, for the rewrite's own work list:

- `README.md`: 14, 52, 70, 145, 256, 266, 281, 303, 325, 327, 332, 345, 346, 347, 351, 355, 356,
  362, 363, 364, 365, 367, 368, 370, 444.
- `docs/architecture.md`: 11, 16, 17, 18, 61, 65, 67, 68, 97, 99, 124, 148, 149.
- `docs/adapter-protocol.md`: 35, 36, 37, 52, 53, 56, 57.
- `docs/threat-model.md`: 78, 90.

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
7. The two event kinds `request.resolved_by_artifact` and `request.fallback_failed`, which have no
   emission site outside the deleted spans.
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

- **L01** `System` has no `handle` attribute, and `system.py` contains no `def handle`.
- **L02** `System` has no `request_status` attribute.
- **L03** `System` has no `_outcome`, `_fail_generation` or `_request_revision_is_current`
  attribute.
- **L04** `System.__init__`'s signature is exactly `self, database, *, candidate_source, clock_us`.
  `System(db, generation_lease_seconds=1)` raises `TypeError`. Derive the parameter list from
  `inspect.signature`, never from source text.
- **L05** `_lease_us` has zero occurrences under `src/`.
- **L06** `_now`'s upper bound carries no lease term: a clock returning `_MAX_SQLITE_INTEGER` is
  ACCEPTED, `_MAX_SQLITE_INTEGER + 1` is REJECTED, and the `StateError` message does not contain
  `lease-safe`. Probe both sides of the boundary in one test so the assertion cannot pass by
  rejecting everything.
- **L07** `revise_operation` performs no `requests` write: its source contains no `UPDATE requests`,
  and a revision executed while a `generating` request row exists at the previous revision leaves
  that row's `status`, `error_code`, `lease_owner` and `lease_until_us` unchanged.
- **L08** the `operation.revised` event payload has EXACTLY the keys `previous_revision`,
  `policy_hash`, `revised_by`. Assert the whole key set, not the absence of one key: this payload
  had zero pins before this unit, so an over-narrow assertion here leaves the same blind spot the
  deletion exposed.

### Closure

- **L09** zero dangling references. `handle`, `request_status`, `_outcome`, `_fail_generation`,
  `_request_revision_is_current` and `_lease_us` each have zero occurrences under `src/`. Count over
  the whole package, not over `system.py`.
- **L10** `system.py`'s `from .models import (...)` list loses exactly `FallbackFailed`,
  `InProgress`, `Outcome`, `ReconciliationRequired`, `Rejected`, `Resolved`, `ReviewRequired` —
  seven names — and no other import moves. Compare the parsed import list, not the source text.
- **L11** the emitted event-kind vocabulary is EXACTLY the thirteen surviving kinds —
  `artifact.ambiguity_quarantined`, `artifact.compiled`, `artifact.counterexample`,
  `artifact.integrity_quarantined`, `artifact.promoted`, `artifact.suspended`, `artifact.verified`,
  `example.revoked`, `function.promoted`, `operation.registered`, `operation.revised`,
  `proposal.created`, `proposal.rejected` — and the `request.` prefix is gone from the namespace.
  Assert the whole SET, not the absence of the two deleted kinds: an absence assertion passes while
  a third kind is invented, and the project's own rule is to pin the complete vector rather than a
  derivative of it. `request.resolved_by_artifact` (`handle:1208`) and `request.fallback_failed`
  (`_fail_generation:1356`) are the only two emission sites either kind ever had.
- **L12** `src/cement_runtime/models.py` is byte-identical to its `da70a56` blob and
  `src/cement_runtime/__init__.py`'s `__all__` is unchanged. The seven models survive without
  producers; deleting them is M3.6a3's and doing it here would take that unit's measurement with it.

### Preserved invariants

- **L13** the surviving `requests` sites in `system.py` are exactly eleven, in `_proposal_bindings`,
  `_write_proposal_request_status` and `_persist_proposal`. Pin the count AND the owning method
  names: a count alone passes when a site moves between methods.
- **L14** `SCHEMA_VERSION` stays 2 and `src/cement_runtime/store.py` is byte-identical to its
  `da70a56` blob.
- **L15** `propose`, `submit_proposal`, `get_proposal`, `review` and `resolve` are byte-identical to
  their `da70a56` spans, under the whole-line `lineno..end_lineno` convention with trailing newlines
  stripped. That convention is M3.3's P06 convention; a column-offset slice measures four bytes
  shorter and is a different claim.
- **L16** the proposal round trip still ends with the private request row `resolved`: propose,
  review-accept, then read the row through the store and assert `status = 'resolved'` with its
  `output_json` and `example_id` set. `_write_proposal_request_status` is untouched by this unit and
  this is the probe that proves it.
- **L17** `revise_operation` still bumps the revision by one and still retires `draft`, `verified`
  and `promoted` artifacts at the previous revision with `status_reason = 'operation revised'`.
- **L18** `_now` still rejects a non-`int`, a `bool`, a negative value and a non-callable
  `clock_us`, and every surviving caller of `_now` is unchanged.

### Prose

- **L19** `README.md` names neither `handle` nor `request_status`, carries no poll-state table and
  no lease configuration, and its request-route section describes the proposal route instead.
- **L20** `docs/architecture.md` steps 1-3 describe `propose`/`review`; the lease paragraph is gone.
- **L21** `docs/adapter-protocol.md` names no deleted surface. M3.7 relocates this file under byte
  equality, so it must be correct HERE.
- **L22** `docs/threat-model.md` no longer claims a `handle` request ID as an idempotency key and no
  longer describes lease recovery; whatever replaces each claim describes surviving behaviour.
- **L23** all 15 census pins in section 5 are green after the rewrite, each either satisfied by the
  new prose or re-scoped with grounds recorded in section 8.
- **L24** no human-facing surface gains a NEW claim about a deleted surface. Re-run the census
  (`gate 3`) against the rewritten documents and require the owned hit count to be zero for every
  vocabulary token naming a deleted surface.

### Tripwire repairs

- **L25** M3.5b's D15a (`tests/test_cli_removal_battery.py:1131`, assertion `:1158`) is re-scoped to
  the closed range `36f7890..1146421`, exactly as M3.6a1 re-scoped its siblings D15b (`:1160`) and
  D22b (`:2766`). The repair is a family repair: after it, no D15/D22 clause reads the working tree
  for a runtime module.
- **L26** the four P06 span freezes are RETIRED with their history preserved, not re-based: they
  freeze the bytes of a method that no longer exists. Each retirement records the frozen figures it
  carried (`12,866 B / 1182130a2b3a`, `12,867 B / cd60036faf5c`, `12,862 B / c27e71b0b4c7`) so the
  claim stays checkable against history, and L15 is what replaces their protective value for the
  methods that survive.
- **L27** M3.5b's D01 (`tests/test_cli_removal_battery.py:608`, assertions `:617` + `:618`) is
  INVERTED: it
  asserted `System.handle` and `System.request_status` still ship as library methods; it now asserts
  their absence. An inverted pin keeps the obligation and reverses the predicate; deleting it would
  delete the behaviour's only pin along with the behaviour.
- **L28** `tests/test_authority_removal.py:118 test_system_constructor_shape` is rewritten to the
  three-parameter signature and keeps asserting defaults for the parameters that remain.
- **L29** `m3u6a2-tripwires.py`'s `_freezes()` detector is widened to see the P06 family, behind a
  self-test control that FIRES on a P06 frame. Today it requires the literal
  `cement_runtime/system.py` or `System.handle` AND one of `read_bytes()`/`getsource`/`_git_bytes(`,
  while the four P06 frames reach the same source through `cement_runtime.system.__file__`,
  `inspect.getsourcefile(System)` and a `_source(ROOT, path)` helper — so the instrument reported
  `FREEZES: 4` over a set DISJOINT from the four freezes this unit actually inverts, and its 6/6
  self-test covered none of that negative space. If widening proves to over-report, record the
  exclusion with grounds instead; what is not acceptable is leaving a detector whose name promises
  the family it cannot see.
- **L30** M3.6a1's D16 (`tests/test_migration_battery.py:993`) is re-scoped to the CLOSED range
  `6fb4d92..dc4ab5e` — M3.6a1's baseline and its own DONE tip — on BOTH halves: the expected path
  set and the per-path byte comparison, which read `HEAD` and the working tree respectively. Read
  against `HEAD`, D16 asserted that M3.6a1's surgery script reproduces every LATER unit's `tests/`
  and `examples/` edits, which no script pinned to an earlier baseline can do. It is the same family
  as D15a (L25), and it is stricter: D15a inverts when this unit EDITS a runtime module, while D16
  inverts when this unit ADDS ANY FILE under `tests/` or `examples/` — the battery seed alone
  tripped it. Its repair therefore lands BEFORE every other edit rather than beside them.

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
| WORKING-TREE | `test_x30` | `tests/test_cli_channels.py:2990` |
| WORKING-TREE | `test_d23` | `tests/test_cli_channels_battery.py:2488` |
| WORKING-TREE | `test_d22a` | `tests/test_cli_removal_battery.py:2685` |
| WORKING-TREE | `test_d23` | `tests/test_migration_battery.py:1269` |
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

The two GIT-RANGE rows assert a closed historical diff and are SAFE by construction. The thirteen
others read the working tree and are L23's work list.

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

1. `uv run python -m unittest discover -s tests -t .` — green, with the post-state test count
   recorded beside the claim.
2. `uv run python .agent/decisions/m3u6a2-battery-validate.py` — every `L<n>` in section 3 is
   covered by AT LEAST one battery test, ids are contiguous, no test names an id the contract does
   not define, and no test is still a seed stub. Coverage is a FLOOR, corrected by C02.
3. `uv run python .agent/decisions/m3u6a2-tripwires.py --check` — the census reruns against the
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
| S4 | harvest the phase-2 red suite, credential it red at `da70a56`, implement the deletions, the two edits and the import shrink against it |
| S5 | prose rewrite over the four owned documents plus the tripwire repairs L25-L29 |
| S6 | battery verdict ruling and `m3u6a2-closure.py` (gate 4) |
| S7 | attack ruling into section 8 through the `--check` patcher |
| S8 | mutation catalogue and gate 7 |
| S9 | reversion sweep, gate list rerun, DONE commit |

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
