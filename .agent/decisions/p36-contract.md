# p36 contract — an explicit quarantine after a failed verification (revision 2)

Row (verbatim acceptance, `.agent/deferred.md`): Consume displayed failure identity, recheck under
one write lock, change only still-affected artifacts, emit one bounded event, rerun idempotently,
preserve ordinary misses; moved-state race returns conflict with zero writes.
Owner ruling (queue run 3): funded; it replaces the `Decisions` sentence "Ambiguity quarantine
leaves with `handle`." Tier `kernel`. `resolve` stays pure (it reports, never writes); the
quarantine is a separately named mutator a person runs. Revision 1 → 2 = consultant-1's verdicts
(`.scratch/queue-run-3/consultant-1/p36-verdicts.md`, measured on HEAD copies): a status text is no
application receipt (public `suspend_artifact` can write it), the plan needs an exact unbounded
preimage, the race is about the DISPLAYED plan, and a quarantine does not restore serving.

## Premises (measured at HEAD)

- P1 A live promoted member's findings already exist per row: `_snapshot_member` (ABI, bound
  report, artifact + scope + live receipt, projection). Ambiguity = several live members claiming
  one input digest, derived from the rows (`_duplicate_digest_check`'s detail previews 3 of N).
- P2 `revise_operation` retires every promoted member of the old revision, so a live member whose
  revision or policy disagrees with its operation is corrupt, not stale.
- P3 An operation row whose own policy fails its binding (`_snapshot_policy_failures` non-empty)
  makes every member disagree with it: the plan refuses rather than blame the members.
- P4 Suspension (`status = 'suspended'`, `promotion_hash = NULL`, a `status_reason`) is terminal in
  the supported lifecycle. It removes members from the live promoted set but publishes no
  replacement function: `follow` can stay failed (`persisted-function-receipt`) until a new
  promotion binds the remaining or replacement set; a pin containing a suspended member fails its
  suspension check; other versions keep their own pin checks. Quarantine contains; it never
  restores serving by itself.

## Obligations

- Q1 Display (read-only): `System.quarantine_plan(partition, operation)` → `QuarantinePlan`
  (`partition`, `operation`, `operation_revision`, `members`: `QuarantineMember(artifact_id,
  reasons)` sorted by artifact id, `plan_digest`). Members = every live promoted member of the
  partition + operation (any revision) with a member-local finding; reasons in channel order ABI,
  report, receipt, projection, ambiguity (`ambiguous input digest <digest>` on every claimant), each
  finding kept even where two channels share a text. An empty plan means no actionable member
  finding, never a passing verification (a corrupt function receipt alone yields an empty plan).
  Refused: unregistered operation → `NotFoundError`; P3 → `StateError`. `plan_digest` =
  `_digest_strings("cement-quarantine-plan-v1", …)` over partition, operation, revision and per
  member its id, its reason count and its reasons — length-prefixed, so no size ceiling applies.
  The digest binds the display, not every ledger byte.
- Q2 Mutator: `System.quarantine(partition, operation, *, plan_digest, actor)` →
  `QuarantineResult(plan_digest, quarantined, already_applied)`. One write transaction: recompute
  the plan on that connection and compare before any write; equal → for each member
  `UPDATE artifacts SET status = 'suspended', promotion_hash = NULL, status_reason =
  'quarantined <plan_digest>' WHERE id = ? AND status = 'promoted'` (each asserting one row) + ONE
  event `function.quarantined` (subject `operation`, `<partition>/<operation>`; payload keys
  exactly `actor`, `plan_digest`, `count`, `artifact_ids`, `artifact_ids_hash`, the last three
  from `_id_list_projection` over the complete sorted set); an empty equal plan writes nothing and
  emits no event. `actor` = the 256-character actor convention.
- Q3 Idempotent rerun: when the recomputed plan differs, return `already_applied=True` only if a
  `function.quarantined` event of this partition + operation records `plan_digest`, and the
  nonempty complete set of artifacts tagged `quarantined <plan_digest>` there is still suspended
  and matches that event's `count` and `artifact_ids_hash`; read inside the same transaction;
  return those ids sorted; write nothing. Missing event, a partial or extra tagged set, or a tagged
  member no longer suspended → `ConflictError`, zero writes.
- Q4 Race: a change to the displayed plan (members, reasons, revision) since display →
  `ConflictError`, zero writes, unless Q3 holds; an intervening commit that leaves the displayed
  plan unchanged is no conflict (the person approved exactly that plan).
- Q5 Misses: an input absent from the served function is never a finding; quarantine touches only
  live promoted members of this partition + operation.
- Q6 CLI: `cement function quarantine-plan OPERATION` (read; exit 0, JSON plan; refusals 2-5 by
  class) and `cement function quarantine OPERATION --plan-digest D --actor A` (write; conflict and
  refused plan = exit 4; unregistered = 3); help in the ASD-STE100 register.
- Q7 Records: `Decisions` sentence replaced; README + `docs/architecture.md` name both commands,
  their authority, idempotency, conflict and P4; the event census (`EVENT_PAYLOAD_KEYS`) gains the
  kind and its keys.

## Gates (numbered; rerun from committed state)

1. New tests, red at the parent: the plan names every member per finding channel (report,
   artifact, scope / live receipt, projection drift, ambiguity with 4 claimants) and nothing
   else; a healthy set and a receipt-only fault → empty plan, zero writes; P3 refusal; equal digest
   → exactly those members suspended + one event with exact keys, count + full-id hash; rerun →
   `already_applied`, zero writes; manual `suspend_artifact` with a forged reason → not applied
   (conflict); a partial tagged set → conflict; a displayed-plan change between plan and apply →
   conflict, zero writes; an unrelated commit between plan and apply → applies; misses untouched;
   a planted event failure rolls the suspensions back; CLI exit codes + JSON.
2. Full gate = CI gate.
3. `p32-differential.py --base <parent>` → `SAME` (existing surfaces unchanged).
