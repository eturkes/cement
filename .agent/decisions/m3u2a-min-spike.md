# M3.2a ALT-MIN spike

## Verdict

**Minimal sufficient set = three mechanisms.** The final candidate passed all 32 fixed probes on Python 3.13.14 with SQLite 3.53.1:

1. One explicit transaction, owned by the Store and ended with rollback.
2. A deny-by-default, read-allowlisted SQLite authorizer.
3. A percent-encoded, existing-only `file:` URI with `mode=ro`.

`PRAGMA query_only` has no forcing probe. The three-mechanism candidate omits it and records 32/32 expected outcomes. The prescribed fourth mechanism is therefore defense-in-depth, not a measured requirement of this corpus.

Spike code commit: `7c8831b0730f0a29ef530d311de7f719d58b9ccc`.

## Fixture and method

- `Store(path)` created a real schema-v2 ledger.
- `Store.transaction(write=True)` populated `operations` and `events`.
- The fixture used `operations.revision = 12`, so integer framing crossed the single-digit boundary.
- Every write probe used an isolated byte-copy of the closed fixture.
- W5 discovered `artifact_evidence_building_insert` from `sqlite_schema`; it did not use a hard-coded trigger.
- The final matrix was rewritten after probes 6, 12, 18, 24, 30, and 32.
- Each incremental stage ran the full 32-probe corpus.
- Leave-one-out controls reran the full corpus after the final set was known.

## Incremental result and forcing probes

| Stage | Mechanisms in force | Expected outcomes | Mismatches | Addition forced by | What the addition bought |
|---|---|---:|---:|---|---|
| 1 | owner-rollback transaction | 17/32 | 15 | R8 is the first direct transaction requirement; S5 and S6 confirm it structurally | One snapshot and rollback cleanup. It incidentally denied W8, W13, and W16. It did not enforce general read-only behavior. |
| 2 | stage 1 + authorizer | 31/32 | 1 | W1 was the first successful write. Leave-one-out W10, W11, and W15 prove that `mode=ro` cannot substitute for the authorizer. | Closed all 14 stage-1 write gaps. It also denied explicit COMMIT, so a caller cannot split the snapshot. |
| 3 | stage 2 + encoded `file:` URI `mode=ro` | 32/32 | 0 | S3 | Refused a missing path without creating a file. S4 separately forced percent encoding of the URI path component. |

### Leave-one-out minimality

| Omitted member | Exact failures | Meaning |
|---|---|---|
| Transaction | R8: `RuntimeError: in_transaction states=[False, False, False]`; S5: `AssertionError: counts before=1, inside_after_writer=2, after=2`; S6: `AssertionError: no read transaction existed; commit split the snapshot` | The authorizer and `mode=ro` deny writes but provide no snapshot lifetime. |
| Authorizer | W10 TEMP table succeeded; W11 ATTACH + CREATE + INSERT succeeded; W15 `PRAGMA foreign_keys=OFF` executed with readback `1` | `mode=ro` protects only the main database file. It does not deny TEMP writes, writes through a newly attached database, or connection-state mutation attempts. |
| Encoded `mode=ro` URI | S3 opened the missing path and created it | The authorizer is installed only after `sqlite3.connect`; it cannot prevent connect-time file creation. |
| `PRAGMA query_only` | None; final result remained 32/32 | No corpus probe forces it. |

## Every mismatch and its meaning

### Stage 1: transaction only — 15 mismatches

The following expected-denial probes completed successfully: W1 INSERT, W2 UPDATE, W3 DELETE, W4 CREATE TABLE, W5 DROP TRIGGER, W6 ALTER TABLE, W7 `user_version` write, W9 `application_id` write, W10 CREATE TEMP TABLE, W11 ATTACH + CREATE + INSERT, W12 INSERT + explicit COMMIT, W14 SAVEPOINT + INSERT, W15 `foreign_keys=OFF`, and W17 REINDEX + ANALYZE. S3 also opened and created the missing file.

This stage denied only three write probes, for incidental transaction-context reasons:

- W8: `sqlite3.OperationalError: cannot change into wal mode from within a transaction`
- W13: `sqlite3.OperationalError: cannot VACUUM from within a transaction`
- W16: `sqlite3.OperationalError: table sqlite_master may not be modified`

These three errors do not establish a general read-only capability. Fourteen valid write paths still executed.

### Stage 2: transaction + authorizer — one mismatch

- S3 succeeded and created the missing file. The callback cannot act before the connection exists.

All W1-W17 probes were denied.

### Stage 3: final candidate — zero mismatches

Every read and structural probe returned `ok`. Every write probe and S3 returned `denied`.

### Leave-one-out controls

The no-authorizer control mismatched W10, W11, and W15. The no-transaction control mismatched R8, S5, and S6. The authorizer-without-URI stage mismatched only S3. These disjoint failures establish that each member closes a distinct capability gap.

## Exact final denial surface

| Probe | Exception type | Exact message |
|---|---|---|
| W1 INSERT | `sqlite3.DatabaseError` | `not authorized` |
| W2 UPDATE | `sqlite3.DatabaseError` | `not authorized` |
| W3 DELETE | `sqlite3.DatabaseError` | `not authorized` |
| W4 CREATE TABLE | `sqlite3.DatabaseError` | `not authorized` |
| W5 DROP TRIGGER | `sqlite3.DatabaseError` | `not authorized` |
| W6 ALTER TABLE | `sqlite3.DatabaseError` | `not authorized` |
| W7 `PRAGMA user_version` write | `sqlite3.DatabaseError` | `not authorized` |
| W8 `PRAGMA journal_mode=WAL` | `sqlite3.DatabaseError` | `not authorized` |
| W9 `PRAGMA application_id` write | `sqlite3.DatabaseError` | `not authorized` |
| W10 CREATE TEMP TABLE | `sqlite3.DatabaseError` | `not authorized` |
| W11 ATTACH + write | `sqlite3.DatabaseError` | `not authorized` |
| W12 INSERT | `sqlite3.DatabaseError` | `not authorized` |
| W12 explicit COMMIT | `sqlite3.DatabaseError` | `not authorized` |
| W13 VACUUM | `sqlite3.OperationalError` | `cannot VACUUM from within a transaction` |
| W14 SAVEPOINT INSERT | `sqlite3.DatabaseError` | `not authorized` |
| W15 `PRAGMA foreign_keys=OFF` | `sqlite3.DatabaseError` | `not authorized` |
| W16 `PRAGMA writable_schema=ON` | `sqlite3.DatabaseError` | `not authorized` |
| W17 REINDEX | `sqlite3.DatabaseError` | `not authorized` |
| W17 ANALYZE | `sqlite3.DatabaseError` | `not authorized` |
| S3 missing file | `sqlite3.OperationalError` | `unable to open database file` |

Mechanism attribution:

- The authorizer produced the uniform `sqlite3.DatabaseError: not authorized` surface.
- The transaction rejected VACUUM before the authorizer callback ran.
- `mode=ro` produced S3's connect-time `sqlite3.OperationalError`.
- In the no-authorizer control, `mode=ro` rejected main-ledger writes with `sqlite3.OperationalError: attempt to write a readonly database`, but W10, W11, and W15 still succeeded.

The final messages are short and stable on this measured build. `not authorized` is generic, but it is not ambiguous about the verdict. The public Store context may still translate SQLite exceptions according to the final M3.2a contract.

## Read path

- R1 returned `[('fixture', 'base-marker', 12)]`.
- R2 returned `user_version=2`.
- R3 returned `application_id=0`.
- R4 returned 67 schema objects, including 23 triggers.
- R5 called `store._validate_ledger(connection)` successfully.
- R6 executed every existing setup pragma. Readbacks were `foreign_keys=1`, `busy_timeout=10000`, `synchronous=3` (`EXTRA`), `temp_store=2` (`MEMORY`), and `trusted_schema=0`.
- R7 found `Connection.setconfig`. DEFENSIVE read back `True`; TRUSTED_SCHEMA read back `False`.
- R8 recorded `connection.in_transaction == [True, True, True]` before and after both SELECTs.

The setup pragmas and `setconfig` run before the authorizer is installed. The capability then exposes only the read transaction.

## Structural probes

### S1 and S2

- Full `iterdump()` remained byte-identical: 14,400 bytes; SHA-256 `9974a98d2ce3e754452092ad0962bed46ccac02fa0186393577bb6d03c49f6e7`.
- The ledger file remained byte-identical: 208,896 bytes; SHA-256 `46c334fed4ddec688a0bd17eef59e3cad4f3042956ffb717351bf109419f0dd4`.

### S3

Opening a missing path raised `sqlite3.OperationalError: unable to open database file`. The path remained absent.

### S4: URI hazard paths

The active encoded URI opened every intended ledger and returned its distinguishing marker:

| Path class | Expected marker | Actual marker | Result |
|---|---|---|---|
| `?` | `marker-question` | `marker-question` | correct target |
| `#` | `marker-fragment` | `marker-fragment` | correct target |
| `%` | `marker-percent` | `marker-percent` | correct target |
| space | `marker-space` | `marker-space` | correct target |
| newline | `marker-newline` | `marker-newline` | correct target |
| non-ASCII | `marker-non_ascii` | `marker-non_ascii` | correct target |

A raw `file:{path}?mode=ro` URI opened deliberately planted wrong ledgers for three names:

- `?` returned `raw-decoy-question`.
- `#` returned `raw-decoy-fragment`.
- `%25` decoded and returned `raw-decoy-percent`.
- Space, newline, and non-ASCII names happened to return their intended markers on this build.

`Path.absolute().as_uri()` encoded all six path components. It closed every observed wrong-target case. Raw URI concatenation is therefore disallowed, even where a particular character happened to work.

### S5: concurrent writer

Counts were `before=1`, `inside_after_writer=1`, and `after=2`. The reader did not observe the committed row inside its transaction.

The ledger used rollback journal mode `DELETE`. The writer was still blocked at the 150 ms sample and completed after 179.688 ms. This is the availability cost: a reader holds a shared lock, so the writer can prepare its write but its commit waits for reader rollback.

### S6: rollback versus commit

Rollback preserved the 208,896-byte file and SHA-256 `46c334fed4ddec688a0bd17eef59e3cad4f3042956ffb717351bf109419f0dd4`.

An explicit `commit()` raised `sqlite3.DatabaseError: not authorized`. `connection.in_transaction` stayed `True`; the snapshot did not split. The owner then rolled it back. In the transaction-only stage, INSERT and explicit COMMIT both succeeded, which proves that owner rollback alone cannot constrain a yielded raw connection.

### S7: setup cost

Measured one interleaved run of 1,000 opens for each path after 20 warmups:

- Current `Store._connect`: **486.550 µs/open**.
- Current 200-open round range: **462.998–505.917 µs/open**.
- ALT-MIN connection: **498.115 µs/open**.
- ALT-MIN 200-open round range: **462.999–524.958 µs/open**.
- Delta: **+11.565 µs/open**.
- Ratio: **1.024×**.

The measured setup surcharge was 2.4%. The per-round ranges overlapped substantially. This is one machine/build measurement, not a portability claim.

## Recommendation

Implement the three-mechanism set as the M3.2a behavioral minimum:

1. Build the URI from an absolute `Path.as_uri()` result, then append `?mode=ro`.
2. Run the five current connection pragmas and both available `setconfig` calls before enforcement.
3. Install a deny-by-default authorizer that allows SELECT, READ, FUNCTION, RECURSIVE, read-form PRAGMAs, BEGIN, ROLLBACK, and SAVEPOINT control.
4. Start one explicit transaction.
5. Deny COMMIT through the authorizer.
6. Roll back and close in the Store-owned cleanup path.

Do not add `PRAGMA query_only` to claim corpus sufficiency. No probe forces it. If M3.2a retains it, label it explicitly as non-minimal defense-in-depth against implementation mistakes or future SQLite behavior.

The final production tests should pin the allowlist, not only the 17 named write statements. A permissive authorizer mutation can otherwise make `mode=ro` look sufficient while TEMP and ATTACH capabilities remain writable.

## Self-rejection

**SELF-REJECTION: NO.** The alternative passed 32/32, each retained member has a distinct leave-one-out failure, URI encoding closed three demonstrated wrong-target hazards, the denial messages were clear on the measured build, and setup cost was +11.565 µs/open.

Limits do not reverse the result:

- Measurements cover Linux, CPython 3.13.14, and SQLite 3.53.1 only.
- The fixed corpus does not enumerate every future SQLite authorizer action or side-effecting extension function.
- `PRAGMA query_only` can still be chosen as defense-in-depth, but this spike found no behavioral obligation that requires it.

## Verification and worktree state

- All five full-corpus runs completed: transaction-only, +authorizer, final, no-authorizer, and no-transaction.
- `git diff --check` passed.
- The 548-test project gate was not run. The spike adds no imported production or test module, and the brief did not require the gate.
- An unowned validator delta appeared in the isolated worktree: `outcome != "ok"` changed to `outcome not in ("ok", "unknown")`. It was preserved and excluded from commit `7c8831b`.

Final validator output:

```text
FLUSHED: 32/32
MISMATCHES: 0
STRUCTURE: OK
```
