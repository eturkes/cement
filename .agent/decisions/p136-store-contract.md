# p136-store contract — shadow observations, agreement, drift (revision 2)

Plan: `.agent/decisions/p88-milestone.md` S2-S4, amended by the owner's T rulings (`.agent/spec.md`
`Decisions` Shadow sampling): T2 + T9 = each observation keeps the input, both answers, model + prompt
revision + timing; T3 = a disagreement also becomes a pending ledger proposal; T6 = a separate
telemetry SQLite file (an agreement never writes the ledger); T7 = observation id = the caller's
identity (chat message + tool call), admitted once before any model work; prune + erase cover the
store (owner). Tier `kernel` for admission identity, the captured answer + comparator, the verdict,
the proposal write and the counts (no downstream re-check); `data` for stored payloads, re-validated
on read. Revision 1 → 2 = consultant-2's N1-N8 (`.scratch/p136/consultant-2/verdicts.md`, probes at
`723abe9`) + consultant-1's L4: capture at admission, a durable `prepared` row before any ledger write,
recovery by an exact source lookup with binding checks, a caller-derived source id, cancellation,
honest two-file retention.

## Premises (measured at `6af77ce`)

- H1 Any commit through SQLite makes the next `serving`/`resolve` cold (p35); a disagreement proposal
  is one such commit; an agreement writes only the shadow file. `serving(expected_function_hash=H)` keys
  its cache apart from a plain `resolve`, so the first admission after a ledger commit pays one more
  verification (gate 3 measures it).
- H2 `submit_proposal(…, source_id, expected_revision)` checks the revision BEFORE the source-id
  dedupe, and a repeated source id raises `ConflictError` whatever the payload (consultant-2 probes);
  `SOURCE_ID_MAX_BYTES` = 512; `PROVENANCE_MAX_BYTES` = 65,536; a submission writes one proposal + one
  `proposal.created` event (payload `{}`).
- H3 A comparator is mutable revision-scoped policy (p136-cmp): two settings in one revision can flip a
  verdict, so a verdict reads the comparator CAPTURED with the observation, never the latest one.
- H4 A pending proposal on a promoted case leaves support + serving intact, sets `nothing_to_learn`
  false and enters `learning_cases` like any answer; its review is the learning pass's act (N4).

## Obligations

- S1 Store (`cement_runtime.shadow.ShadowStore(path, *, create=True)`): one SQLite file, mode 0600 at
  creation, `STRICT`, its own `user_version` + metadata fingerprint + live-schema comparison at every
  open (a ledger file, a foreign database, a changed schema → `IntegrityError`); `create=False` opens
  an existing file only (missing → `NotFoundError`, nothing created); rollback journal; every write
  connection `secure_delete` + busy timeout 10 s; `shadow_path(ledger)` = `<ledger>.shadow`. States:
  `admitted`, `prepared`, `agreed`, `disagreed`, `failed`, `cancelled`, `dropped`; a trigger allows only
  `admitted` → `agreed | prepared | failed | cancelled` and `prepared` → `disagreed`; identity + capture
  columns are immutable; CHECKs bind each state's required columns.
- S2 Admission (`admit(system, store, partition, operation, *, observation_id, function_hash,
  input_value, observed_at_us) -> Admission(admitted, id)`): `observation_id` = text ≤ 505 UTF-8 bytes
  (`SOURCE_ID_MAX_BYTES` − `len("shadow:")`), no control character; in ONE call, before the shadow
  write, `System.shadow_capture` reads the captured version: the receipt of `function_hash` in this
  partition + operation (absent → `NotFoundError`), its answer to the input (the serving fast path when
  it serves exactly that hash and passes, else the receipt rebuilt; a miss → `ValidationError`; a
  failed rebuild → `IntegrityError`), its operation revision, and the comparator in force for that
  revision (JSON + hash + setting sequence, or none). Then one write: a new identity → an `admitted`
  row holding identity + capture; a repeated identity → no row, the duplicate counter + 1, `admitted`
  False with the ORIGINAL row id. Admission happens before any model call (T7).
- S3 Other outcomes: `drop(store, …, reason)` = a NEW identity that never reached the model (a full
  queue), written `dropped` without capture; `cancel(store, id, reason)` = `admitted` → `cancelled` (a
  shutdown); `fail(store, id, *, reason, model, prompt_revision, latency_ms)` = `admitted` → `failed`
  (a model error, a timeout, an output that is no `cement-json-v1` value within 1 MiB). None writes the
  ledger. Texts ≤ 256 UTF-8 bytes, no control characters; integers exact, non-negative, < 2⁶³.
- S4 `record_shadow(system, store, id, *, llm_output, model, prompt_revision, latency_ms) ->
  ShadowRecord`: arguments graded first; under the shadow write lock the row must be `admitted`
  (`ConflictError` otherwise); verdict = `compare(captured comparator, captured answer, llm_output)`.
  Agreed → one shadow write (`agreed` + the answer, model, prompt, latency, differences `[]`), no ledger
  access. Disagreed → one shadow write to `prepared` holding everything a retry needs (the LLM answer,
  differences, source id `shadow:<observation_id>`, model, prompt, latency), then the finish step.
- S5 Finish (`finish_shadow(system, store, id) -> ShadowRecord`, also the retry for a `prepared` row):
  lock order shadow → ledger; under the shadow write lock the row must be `prepared`; the ledger is
  searched for the source id across EVERY status (`System.proposal_by_source`): found → its input hash,
  proposed output hash, operation revision and shadow provenance must equal the prepared row (else
  `ConflictError`, the row stays `prepared`), and its id is recorded; not found → when the captured
  revision is the current one, `submit_proposal(…, source_id, expected_revision=captured)` with bounded
  provenance `{"shadow": {observation_id, function_hash, receipt_id, comparator_hash, model,
  prompt_revision, difference_count, differences (first 5 paths)}}` (≤ 4 KiB by construction); another
  revision (or a `StateError` that names a revision change) → no proposal, the omission noted; then the
  row → `disagreed` with the proposal id or the note. A crash between the ledger commit and the shadow
  commit leaves `prepared`; `finish_shadow` completes it with no second proposal.
- S6 Reads (`drift`, `observations`, `pending`): one read snapshot each; names + arguments graded
  (exact non-bool integers, `limit` 1..1,000, SQL `LIMIT`); stored JSON + hashes re-validated
  (`IntegrityError`). `drift(store, partition, operation, *, since_us=None) -> DriftReport`: the rows
  with `observed_at_us >= since_us` (inclusive) grouped by `function_hash`, ordered by each group's
  first sequence, counting the seven states; `disagreements` = `prepared` + `disagreed`; totals over the
  window; `duplicates` = the lifetime counter, reported apart. `observations(…, state, function_hash,
  after_sequence, limit)` = rows in sequence order with every stored field. `pending(store, *, state =
  "admitted" | "prepared", after_sequence, limit)` = a cursor for one batch consumer; enumeration is no
  lease (one consumer per store; the nucllei job holds a lock).
- S7 Retention: `ShadowStore.prune(partition, *, older_than_seconds)` deletes the partition's rows with
  `observed_at_us` before the cutoff, every state (the dedupe horizon ends with them);
  `ShadowStore.erase(partition)` deletes every row + the counter. CLI `retention prune` and `partition
  erase` grade every argument first, then run the shadow store beside `--db` (`--shadow` overrides; an
  absent default store is skipped and never created; an explicit missing one exits 3), then the ledger;
  the two files are two transactions, so each reports its own result, and a rerun completes the other
  (a partition already gone from the ledger after a shadow erase reports `ledger: null`). Complete
  erasure needs the integration's sampling stopped for that partition (documented).
- S8 Never act: no store or read path calls `challenge` or changes a switch, function, projection,
  comparator or example; the only ledger writes are S5's proposal + its `proposal.created` event.
- S9 CLI: `cement function drift OPERATION [--since-us N]` + `cement function observations OPERATION
  [--state S] [--function-hash H] [--after N] [--limit N]`; both open the shadow store beside `--db`
  existing-only (`--shadow` overrides) without constructing a `System`; missing → exit 3, corrupt → 5.
- S10 Docs: README `### Shadow answers`; threat model (`Active shadow sampling` → its scope; the shadow
  answer = untrusted evidence; the store = plaintext with its own retention; an observation proves no
  production request; agreement is policy-relative, never correctness); architecture.

## Gates (numbered; rerun from committed state)

1. New tests red at `6af77ce`: S1 identity refusals (a ledger file, a foreign DB, a changed live schema)
   with byte-identical files, mode 0600, every illegal transition + immutable column; S2 capture (old
   and new versions answer differently: the captured one decides, in both directions; switch off;
   projected input; foreign scope / miss / corrupt receipt refuse with zero writes in both files), a
   repeated identity returns the original id + counts, two connections racing one identity → one row;
   S3 drop / cancel / fail; S4 agree writes no ledger row (serving cache stays warm), disagree → one
   proposal + one event with the source id + bounded provenance; S5 a planted failure after the ledger
   commit → `prepared`, `finish_shadow` recovers the same proposal (also after the proposal was
   reviewed), a mismatching proposal under the source id → `ConflictError` + still `prepared`, a revision
   change → no proposal + the note, a comparator change after admission → the captured one still
   decides; adjacent pairs (505 / 506-byte observation id, 1 MiB / + 1 output, 256 / 257-byte model);
   S6 drift across two hashes, the inclusive cutoff edge, an empty window with a nonzero lifetime
   counter, paging + filters + the pending cursor; S7 an adjacent age pair, a collision partition
   intact, the two-file CLI order + an absent default store left uncreated; S8 ledger table deltas per
   path; `p32-differential.py` `SAME`; CLI exits.
2. Full gate = CI gate (`.agent/ci-gate p136-store`).
3. Register + article audits rc 0; the `admit → record → resolve` cost measured with per-point
   provenance (agreeing and disagreeing records) at 1 and 1,000 entries.

```claims
10	Revision 1 → 2	unchecked	revision numbers of this contract, not counts	-
23	`SOURCE_ID_MAX_BYTES` = 512	unchecked	constants read by MAIN at 6af77ce (`system.py` `SOURCE_ID_MAX_BYTES = 512`, `PROVENANCE_MAX_BYTES = 65_536`)	-
32	mode 0600 at	unchecked	a file mode, not a count	-
36	busy timeout 10 s	unchecked	a constant of the store, not a measurement	-
41	≤ 505 UTF-8 bytes	unchecked	512 minus len("shadow:"), the `OBSERVATION_ID_MAX_BYTES` constant; pinned by an adjacent pair	-
53	within 1 MiB	unchecked	the answer bound `ANSWER_MAX_BYTES`, pinned by an adjacent pair	-
116	3. Register + article audits rc 0;	unchecked	a gate expectation	-
```
