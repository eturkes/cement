# p135-e3 contract — schema v4, retention prune, partition erase (revision 2)

Plan: `.agent/decisions/p87-milestone.md` E3. Owner rulings (`.agent/spec.md` `Decisions` Deployment
trust): D5 = schema v4 with erase grant clauses + an `erasures` tombstone, v3 ledgers refused, no
migration; prune + erase also cover the shadow telemetry store (that half lands with p136-store, which
owns the store). Revision 1 → 2 = consultant-1's verdicts (`.scratch/p135/consultant-1/verdicts.md`,
probed at `3333d7c`) + MAIN's stale-copy measurement: the byte claim, the erase order, the
acceptance cases. Tier `kernel`: an erasure or a prune has no downstream re-check, and a guard trigger
that opens too wide deletes evidence for good.

## Premises (measured at the p135-e5 commit)

- R1 Tables with a `partition` column (8): `artifacts`, `events`, `examples`, `function_receipts`,
  `operations`, `projection_settings`, `proposals`, `switch_settings`. Reached through a parent (5):
  `example_revocations` → `examples`; `artifact_evidence`, `test_reports` → `artifacts`;
  `artifact_tests` → `test_reports`; `function_memberships` → `function_receipts`. Shared by hash:
  `projection_programs` (named by `projection_settings`, `artifacts`, `function_receipts`). Neither:
  `schema_metadata`, `sqlite_sequence`.
- R2 Delete-refusing triggers (12): `examples`, `example_revocations`, `artifact_evidence`,
  `test_reports`, `artifact_tests`, `function_memberships`, `function_receipts`,
  `projection_programs`, `projection_settings`, `switch_settings`, `events`, `schema_metadata`.
  `proposals`, `operations`, `artifacts` carry none.
- R3 Foreign keys are ON; `artifact_tests.report_id` and `function_memberships.(receipt_id,
  function_hash)` are deferred; `examples.supersedes_example_id` references `examples`.
- R4 `proposal.created` events carry `{}`; review events keep reviewer, receipt and example ids, never
  document bodies; a proposal's events name it by id alone.
- R5 Any commit through SQLite invalidates the serving cache (p35).
- R6 SQLite leaves a deleted or replaced row's bytes in freed space unless `secure_delete` is on WHEN
  that space is freed: switched on at erase time alone, the battery fixture kept 16 copies of the
  erased marker (earlier page moves + updates); on for every write connection from creation, 0
  (`.scratch/p135/probe_erase_bytes.py`). The rollback journal holds page images during a write and
  is unlinked, not overwritten, at commit; `Store._initialize` alone sets `journal_mode = DELETE`, so
  an operator-switched WAL ledger keeps old pages in its `-wal` file until a checkpoint.
- R7 `Store._open_existing` validates on a read-only connection (`PRAGMA user_version`, integrity,
  foreign keys, fingerprint, live schema = expected); `_unsupported_schema` names the expected version
  and "start a new ledger".

## Obligations

- V1 Schema v4: `SCHEMA_VERSION = 4`, metadata key `schema-v4`; new tables `erasure_grants(partition
  TEXT PRIMARY KEY) STRICT` and `erasures(sequence, id UNIQUE, partition_hash, counts_json, erased_by,
  erased_at_us) STRICT` with `erasures_no_update` + `erasures_no_delete` (no grant clause). Each R2
  trigger except `schema_metadata_no_delete` and `projection_programs_no_delete` gains `WHEN NOT
  EXISTS (SELECT 1 FROM erasure_grants WHERE partition = <the row's partition>)`, the partition read
  from the row (R1 direct) or its parent chain (R1 reached); `projection_programs_no_delete` gains
  `WHEN NOT (EXISTS (SELECT 1 FROM erasure_grants) AND` no `projection_settings`, `artifacts` or
  `function_receipts` row names `OLD.program_hash)`. A v2 or v3 ledger refuses at construction (exit
  5, file bytes unchanged). The package version moves to 0.3.0 at the phase close, not here: it
  changes `uv.lock`, which re-keys every D28 verdict, and `ci/*` runs restore `main`'s cache, so an
  early bump makes every later CI gate of the phase replay the whole range cold.
- V2 `System.prune_proposals(partition, *, older_than_seconds: int, actor: str) -> PruneResult`:
  one write transaction; deletes every proposal of `partition` that no
  `examples` row references (pending or rejected) and whose `created_at_us < now − older_than_seconds
  × 10⁶`; one `retention.pruned` event (subject `partition`, payload exactly `actor`, `cutoff_us`,
  `count`, `proposal_ids`, `proposal_ids_hash` via `_id_list_projection`). Nothing to prune → no
  write, no event, `count` 0. `older_than_seconds` = an int ≥ 0 (bool refused); `actor` = the actor
  convention (`_text`, ≤ 256 UTF-8 bytes); every argument graded before the clock or any write. The
  age counts from the proposal's `created_at_us` (when the answer was retained), for a rejected one too. `PruneResult(cutoff_us, count, proposal_ids, proposal_ids_hash)`.
- V2a Every write connection runs `PRAGMA secure_delete = ON` (`Store._connect`, write branch alone; the
  read setup's pinned pragma list is unchanged), so space any write frees is overwritten from the
  ledger's creation; the claim is bounded by R6 (journal + WAL + disk copies outside the file).
- V3 `System.erase_partition(partition, *, actor: str) -> ErasureResult`: one write transaction: read
  the program hashes the partition names; insert the grant; delete the partition's rows in any order
  where each child goes while the parent its guard reads still exists and each foreign key holds at
  every statement's end (constraint: `artifact_tests` before `test_reports` before `artifacts`;
  `function_memberships` before `function_receipts`; `artifact_evidence` before `artifacts` +
  `examples`; `example_revocations` before `examples`; `switch_settings` before `function_receipts` +
  `operations`; `examples` before `proposals` and in ONE statement (its supersession self-reference);
  `operations` last among the direct tables), then each captured program hash that no remaining row names (an unrelated orphan
  program stays); delete
  the grant; insert one `erasures` row (`partition_hash` = `_digest_strings("cement-partition-v1",
  partition)`, `counts_json` = per-table deleted counts over every R1 table + `projection_programs`,
  `erased_by`, `erased_at_us`); commit. A partition with no row in any R1 table → `NotFoundError`,
  nothing written. `ErasureResult(erasure_id, partition_hash, counts)`.
- V4 Outside an erase transaction every guard trigger still refuses: a raw `DELETE` of each R2 table
  aborts with its message; with a grant row for partition A, a row of partition B (and a parent chain
  in B) still aborts; `erasure_grants` is empty after every erase.
- V5 CLI: `cement retention prune --older-than DAYS --actor NAME` (DAYS = an int ≥ 0; JSON
  `PruneResult`, exit 0); `cement partition erase --actor NAME --confirm PARTITION` (`--confirm` must
  equal `--partition`, checked after the existing-only open (an absent ledger exits 5 first, p51)
  and before any write, else exit 2 with nothing written; unknown partition exit 3; JSON
  `ErasureResult`, exit 0). Help in the ASD-STE100 register.
- V6 Docs: README `### Retention and erasure` (both commands, their cost: one transaction each, a
  pruned pending proposal stops counting toward recurrence, a pruned source id can be retained again,
  backups keep erased rows until the deployment's backup retention expires them); threat model
  `## Enforced controls` immutability bullet → "except inside a partition erasure", `## Deployment
  obligations` minimize bullet → the two commands; `docs/architecture.md` storage section.

## Gates (numbered; rerun from committed state)

1. New tests red at the p135-e5 commit (`cd0d2cf`): V1 identity (version 4, fingerprint, `schema-v4`, the two
   tables, each trigger's grant clause by name); a real v3 ledger (package from git at `331a3b4`)
   refuses with exit 5 and unchanged bytes; prune: an adjacent age pair (created exactly at the
   cutoff kept, 1 µs older deleted), an accepted and a corrected proposal kept, pending + rejected
   deleted, another partition untouched, the event payload exact, nothing to prune → zero writes;
   erase: every rowid of the partition, snapshotted per table BEFORE the erase (direct by column,
   child by parent join, the table set derived from `sqlite_master`), is absent after, and
   `foreign_key_check` is empty; a collision pair (`tenant_a` / `tenantXa`) and a case
   variant (`Tenant_a`) intact, a shared program kept and an unshared one deleted, the tombstone row,
   `erasure_grants` empty, a marker string from the erased content absent from the ledger file bytes
   (present before; a forced-OFF control keeps it), `resolve` after a WARM serve refuses the
   unregistered operation; an unrelated orphan program kept; an events-only partition erased; a failure
   injected at the tombstone rolls back every row, the grant and the tombstone; V4 each trigger refuses
   without a grant and across partitions, each program-reference family (settings, artifacts,
   receipts) blocks a program delete alone, the tombstone refuses update + delete under a grant; actor
   256 / 257 bytes; CLI exits, a `--confirm` mismatch writes nothing (identical bytes), a missing `--db`
   exits 5 and stays missing (p51).
2. Full gate = CI gate (`.agent/ci-gate p135-e3`).
3. Register + article audits rc 0; each repaired pin named in the commit body + a `.agent/review.md`
   row (standing pin-repair approval).

```claims
6	Revision 1 → 2	unchecked	revision numbers of this contract, not counts	-
13	- R1 Tables with a `partition` column (8)	unchecked	the eight direct tables named here; MAIN counted 8 `partition TEXT NOT NULL` columns at cd0d2cf	-
14	Reached through a parent (5)	unchecked	the five child tables named on this line and the next	-
19	- R2 Delete-refusing triggers (12)	unchecked	the twelve tables listed in this bullet; MAIN counted 12 `_no_delete` triggers at cd0d2cf	-
56	write, no event, `count` 0.	unchecked	a value the obligation names (an empty prune), not a measurement	-
57	≤ 256 UTF-8 bytes	unchecked	the `_text` actor bound (`maximum=256`), a constant	-
78	(DAYS = an int ≥ 0; JSON	unchecked	a range bound in the obligation	-
79	`PruneResult`, exit 0);	unchecked	an exit class (`.claude/rules/runtime.md`)	-
80	(an absent ledger exits 5 first, p51)	unchecked	an exit class	-
82	`ErasureResult`, exit 0). Help	unchecked	an exit class	-
106	256 / 257 bytes;	unchecked	an adjacent bound pair the gate pins	-
109	3. Register + article audits rc 0;	unchecked	a gate expectation	-
```

Machine-local: each `.scratch/` path in this file names a gitignored input or output of the session that wrote it; no clone retrieves it, and the file states the substance it relied on (p10). Here: consultant-1's verdicts = `.agent/review.md` `## p135-e3 close`, rows K1-K8, each re-derived by MAIN; the byte probe's measurement = R6 above.
