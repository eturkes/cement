# M3.2a acceptance contract - Store-owned enforced-read capability

Unit: M3.2a, tier `kernel`, tags `oracle`, depends none. Oracle-calibration unit per the roadmap's
ORACLE SURCHARGE ruling. Every downstream artifact decides against this file; where an earlier report,
verdict table or roadmap line disagrees with it, this file governs.

## 1. Scope

`Store.transaction(write=False)` opened a read-write connection under plain `BEGIN`. Plain `BEGIN` is
not query-only, so the connection could upgrade to a write and commit. The unit makes the read
capability enforce read-only inside `store.py`, behind an unchanged public seam.

Measured base span = 46 production lines across exactly two methods (`_connect`, `transaction`).
Blast radius is DERIVED, never restated: `/usr/bin/rg -o '\.transaction\(' src tests examples | wc -l`.
At the unit's close that command reports 148 (`system.py` 32, `test_system.py` 113, `test_cli.py` 1,
`test_authority_removal.py` 1, `test_read_capability_census.py` 1).

### 1a. Measured baseline - both defects reproduced against a real ledger

MAIN smoke probe, run before any test existed, against a freshly constructed `Store`:

- A write inside a `write=False` block did not merely upgrade, it COMMITTED.
  `INSERT INTO schema_metadata(key, value)` inside `with s.transaction(write=False)` completed with no
  error, the row read back on the next transaction, and the ledger sha256 moved
  `090d735f101f17f4` -> `75a01c01cb380366`. `transaction` commits on clean exit, so the read seam was a
  silent write seam. `schema_metadata` carries `BEFORE UPDATE`/`BEFORE DELETE` triggers but no
  `BEFORE INSERT`, and `_validate_ledger` compares schema OBJECTS rather than rows, so the injected row
  survived undetected.
- A read transaction against a deleted ledger file created a 0-byte file at the ledger path and
  reported `StateError: database is busy or unavailable`. A later `Store(path)` saw a 0-byte file,
  found `user_version` 0 and an empty `sqlite_schema`, and initialized a FRESH EMPTY LEDGER. Deletion
  of the ledger was therefore laundered into ordinary first-run initialization.

Both are measured, not inferred. They are the unit's justification and its two headline predicates.

### 1b. Threat model - the guarantee is LAYERED, and the layers differ in strength

The seam yields the raw `sqlite3.Connection` (section 2), whose public methods a caller can use to
reconfigure connection policy. Two layers, measured separately, both stated wherever the capability is
described:

- LAYER 1, not caller-reversible: THE LEDGER FILE ITSELF. `mode=ro` is a connection-open flag, so no
  method on the yielded object can make the main database writable. Measured: after
  `connection.set_authorizer(None)`, `INSERT INTO schema_metadata` still fails
  `sqlite3.OperationalError` `SQLITE_READONLY`(8) and the ledger sha256 is unchanged.
- LAYER 2, caller-reversible: EVERYTHING BEYOND THE LEDGER - TEMP storage, ATTACHed databases, and
  connection policy itself. The authorizer is the only guard, and `connection.set_authorizer(None)`
  removes it. Measured: after removal, a TEMP table and an ATTACHed database both accept writes and the
  attached file persists.

The capability therefore binds SQL and transaction control issued through the configured connection by
a caller that does not dismantle it. It is developer-error enforcement over the ledger, not a sandbox
against a hostile holder of the connection. Claiming otherwise is forbidden: the enforcement wording is
"the ledger cannot be written through this connection", never "the connection cannot write".

Translation is likewise seam-bound. `_transaction_error` maps only what ESCAPES the `with` body; a
caller who catches inside the block sees the raw `sqlite3.DatabaseError("not authorized")` or
`sqlite3.OperationalError`. Both facts get their own pin (B19, B8).

## 2. Frozen public shape

`Store.transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]` keeps its exact
signature, keyword-only marker, and contextmanager decoration. Enforcement is internal. No call site
changes its call, so the unit's edit set stays inside `store.py` plus tests.

Rejected: splitting the seam into separate `read()`/`write()` managers. It buys the same enforcement
while editing every derived call site - the count is the derived total in section 1, not a written
constant - which converts a 46-line unit into the largest unit in the milestone.

Yielding a restricting wrapper instead of the raw connection is likewise rejected: it changes the
annotated return type on a frozen seam, and section 1b's layer 1 already protects the ledger, which is
the object this capability exists to protect.

Pin: one `inspect.signature` + `typing.get_type_hints` test, because frozen public shape is invisible
to behavioral tests (keyword-only markers, defaults, and return annotations all survive a green suite).

## 3. Error classification - owned by this unit

Enforcement makes a previously-silent condition raise, and the pre-unit `except` chain misclassified it
in both directions:

- A `mode=ro` write raised `sqlite3.OperationalError`, mapped to
  `StateError("database is busy or unavailable")` -> CLI exit 4. Exit 4 is the ONE class where retry is
  the intended recovery. A write attempted inside a read capability is not transient.
- An authorizer denial raised `sqlite3.DatabaseError("not authorized")`, mapped to
  `IntegrityError("database operation failed an integrity check")` -> exit 5, which asserts ledger
  corruption. The ledger is intact; the caller asked for the wrong capability. Measurement makes this
  the DOMINANT branch: 16 of 17 write-denial probes raise it.

RULED - classification is by `sqlite_errorcode`, never by message text and never by a sticky flag,
and it applies ONLY on the `write=False` path:

| condition | code | raised class | message | CLI exit |
|---|---|---|---|---|
| authorizer denial | `SQLITE_AUTH`(23) | `_ReadOnlyViolation` | `read-only ledger transaction refused a write` | 2 |
| `mode=ro` refusal | `SQLITE_READONLY`(8) | `_ReadOnlyViolation` | `read-only ledger transaction refused a write` | 2 |
| ledger missing or unreadable | `SQLITE_CANTOPEN`(14) | `IntegrityError` | `ledger file is missing or unreadable` | 5 |
| any other `OperationalError` | - | `StateError` | `database is busy or unavailable` | 4 |
| any other `DatabaseError` | - | `IntegrityError` | `database operation failed an integrity check` | 5 |

`_ReadOnlyViolation(CementError)` is PRIVATE to `store.py` and unexported. It lands on CLI exit 2
through the existing catch-all with no CLI edit, and exit 2 is truthful because the process failed
before any write. Private rather than public because M3 is a trimming milestone and an
unreachable-by-operators fault must not grow the public API; callers who want it can catch
`CementError`, and the unit's tests import it directly. The originating `sqlite3` exception is
preserved as `__cause__`.

Forbidden resolutions, each rejected on record: reuse `StateError` (advertises retry for a permanent
condition); reuse `IntegrityError` (misnames a caller bug as corruption); let `sqlite3.OperationalError`
or `sqlite3.DatabaseError` propagate raw out of the seam (leaks a stdlib class through a public API);
guard with `assert` (`python -O` strips it, and this project has already paid for an `assert`-bound
invariant); classify on message text (not a stable contract across SQLite builds).

Scope limit, stated because the table above reads wider than it is: the unit owns the classification of
refusals the CAPABILITY ITSELF produces. A statement both capabilities refuse identically is not one of
them - see V03/W13 in section 8.

### 3a. Reachability census - MAIN-derived, in the gate

`ast` walk of `src/cement_runtime/system.py`, classifying by parsed SQL rather than by vocabulary:

- 32 `transaction()` `with`-sites: 15 `write=True`, 17 read.
- All 17 read sites execute SELECT only. Zero mutating verbs, zero `connection.commit()` calls.
- 9 read sites hand the connection to 12 distinct helpers. Transitive walk of all 12: SELECT only,
  zero commits.
- Whole-file `execute()` census: 74 literal SELECT, 3 f-string SELECT, 14 INSERT, 29 UPDATE,
  1 SAVEPOINT, 2 RELEASE, 1 ROLLBACK. NO non-literal, non-f-string SQL exists anywhere in the file, so
  no execute site escapes static classification. The single SAVEPOINT/RELEASE/ROLLBACK TO group sits in
  `_verify_row`, reached only from two `write=True` call sites.

Conclusion: enforcement breaks no shipped call site, and a write inside a read block is unreachable
except as a programming error. This licenses the private, non-retryable class above. Shipped as
`tests/test_read_capability_census.py`; it must rerun and still report zero mutating read sites, or the
private-class decision is void.

## 4. Existing-only opening is a separate guarantee from write denial

Before the unit, a read transaction against a deleted ledger silently CREATED an empty database and the
first `SELECT` then failed as `no such table` -> `StateError`. Two defects in one path: a spurious empty
file appeared where the ledger was, and the report named a transient condition.

The capability refuses to open a nonexistent path and leaves no file behind. Missing and unreadable
share one class and one message (`IntegrityError("ledger file is missing or unreadable")`, exit 5) -
see V01/V02 in section 8 for why splitting them is refused. The predicate needs its own adjacent pair:
an existing ledger opens, a missing one is refused with the path still absent afterward.

## 5. Preserved invariants - each pinned independently

A hardening keeps a green suite while deleting a behavior together with its pin, so every item below
gets its own assertion that fails when that item alone disappears:

- All eight read-path probes `R1-R8` keep answering. `R6` matters most: `_connect` executes five
  pragmas, several of which are writes or authorizer-visible, so a mechanism that denies them breaks
  connection setup itself.
- Snapshot lifetime: `connection.in_transaction` stays True across a multi-read block. Read-only proof
  and single-snapshot lifetime are separate guarantees; a mid-block `commit()` satisfies every
  read-only assertion while splitting one snapshot into two.
- `_validate_ledger` stays AUTHORIZER-COMPATIBLE. It runs once in `Store._initialize` and never per
  transaction; the preserved property is that its SQL (`PRAGMA integrity_check`,
  `PRAGMA foreign_key_check`, a `schema_metadata` SELECT, `_schema_objects`) is still permitted when
  called explicitly inside an enforced block. Adding a per-transaction validation call is FORBIDDEN: it
  is new behavior, not preservation, and no spike measured its cost.
- `SCHEMA_VERSION` stays 2 and `store.py`'s schema DDL stays byte-identical. M3 cuts schema ONCE, at
  M3.6b.
- Write transactions (`write=True`, `BEGIN IMMEDIATE`) keep their exact current behavior, including the
  `OperationalError` -> `StateError` and `DatabaseError` -> `IntegrityError` mappings, which stay
  correct on that path. The write path opens a plain (non-URI) connection and installs no authorizer.
- `Store.__init__`'s path validation ladder is untouched.

## 6. Mechanism composition - RULED

Evidence: `.agent/decisions/m3u2a-min-matrix.json` (32/32, 0 mismatches, validator exit 0),
`m3u2a-min-spike.md`, `m3u2a-min-spike.py` (1,141-line probe harness). `spike-m3u2a-full` died twice and
produced no matrix; its ablation deliverable is SUPERSEDED, not merely missing - ALT-MIN's leave-one-out
controls measure the same per-mechanism attribution constructively, by adding each mechanism only when a
probe forced it and then re-running the full corpus with each member omitted in turn.

ADOPTED - three mechanisms, each with a distinct forcing probe and a distinct leave-one-out failure:

1. One explicit Store-owned transaction ended with rollback. Forced by `R8`; confirmed by `S5`/`S6`.
   Omitting it: `R8` `in_transaction` reads `[False, False, False]`, `S5` sees the concurrent writer's
   row mid-transaction, `S6` commit splits the snapshot. The other two mechanisms deny writes but
   supply NO snapshot lifetime.
2. Deny-by-default, read-allowlisted SQLite authorizer. Forced by `W1`. Omitting it: `W10` TEMP table,
   `W11` ATTACH-then-write, and `W15` `PRAGMA foreign_keys=OFF` all SUCCEED, because `mode=ro` protects
   only the main database file. It also denies explicit `commit()` and `rollback()`, closing the
   snapshot-split hazard from both sides.
3. Percent-encoded, existing-only `file:` URI with `mode=ro`, built from `Path.absolute().as_uri()`.
   Forced by `S3`. Omitting it: the missing path is opened AND created, because the authorizer is
   installed after `sqlite3.connect` and cannot act before the connection exists. It also supplies
   layer 1 of section 1b.

REJECTED - `PRAGMA query_only`, the prescription's fourth mechanism. No probe in the corpus forces it;
the three-mechanism candidate scores 32/32 without it. The decisive argument is this project's own
mutation criterion: for every check, some committed test must fail when that check's logic alone is
deleted. A mechanism with no forcing probe is a mechanism no test can pin, so shipping it would add an
undetectably-deletable line and a defense-in-depth claim nothing verifies. It may be adopted later only
together with a probe that fails without it.

RESOLVED HAZARD - path-to-URI conversion is NOT safe by concatenation, measured with planted decoys.
A raw `file:{path}?mode=ro` opened a DIFFERENT ledger for three of six hazardous names: `?` returned
`raw-decoy-question`, `#` returned `raw-decoy-fragment`, `%` returned `raw-decoy-percent`. Space,
newline and non-ASCII happened to resolve correctly on this build, which is exactly why "it worked when
I tried it" is not evidence here. `Path.absolute().as_uri()` encoded all six components and returned
every intended marker. Raw URI concatenation is forbidden; the encoded form is contractual, and the
adjacent test is the decoy pair, not a single happy path.

### 6a. Allowlist composition - RULED, by NAME and by ACTION

Grading a pragma by argument SHAPE (`arg2 is None` means "read") fails BOTH ways: SQLite reports a
pragma's subject and its assigned value in the same argument, so the shape rule admits bare writers
(`PRAGMA optimize` runs ANALYZE and writes `sqlite_stat1`) and denies argument-carrying reads
(`PRAGMA table_info(t)`, `index_list(t)`, which broke a committed test). A shape rule also silently
inherits every pragma SQLite adds later. Pragmas are therefore allowlisted by NAME, in two sets:

- readable-bare, allowed only with no assigned value, so `PRAGMA foreign_keys = OFF` stays denied:
  `application_id`, `busy_timeout`, `foreign_keys`, `synchronous`, `temp_store`, `trusted_schema`,
  `user_version`.
- introspection, allowed with or without an argument: `collation_list`, `database_list`,
  `foreign_key_check`, `foreign_key_list`, `function_list`, `index_info`, `index_list`, `index_xinfo`,
  `integrity_check`, `quick_check`, `table_info`, `table_list`, `table_xinfo`.

Every other pragma name is denied. Action grants:

- `SQLITE_SELECT`, `SQLITE_READ`, `SQLITE_FUNCTION` - forced by `R1`-`R5`.
- `SQLITE_RECURSIVE` - KEPT, forced by B17's recursive-CTE read. Without the grant that read is denied;
  the grant enables a genuine read, so a probe that exercises it is the forcing probe.
- `SQLITE_TRANSACTION` with argument `BEGIN` only. `COMMIT` and `ROLLBACK` are DENIED: a caller
  `rollback()` ends the Store's snapshot exactly as `commit()` does, and single-snapshot lifetime is a
  guarantee the caller must not be able to cut. The owner lifts enforcement in `_release` to end its own
  snapshot, where no caller SQL runs and the connection closes immediately after.
- `SQLITE_SAVEPOINT` - REMOVED. Both users of savepoints are `write=True` call sites (section 3a), so no
  read path can reach one; the grant was pinned by no probe, and W14 stayed "denied" with or without it,
  so no probe could ever detect its deletion. It fails the same mutation criterion that rejected
  `PRAGMA query_only`. Pinned by B18's denial probe.

### 6b. Cost - RE-MEASURED against the landed implementation

Method: interleaved alternating pairs, both arms in one loop, first arm swapped per round, after
warmups. `.agent/decisions/m3u2a-connect-benchmark.py` reruns it from committed state.

Four MAIN runs at 400 opens x 9 rounds: ratios 0.980, 0.961, 0.978, 0.961 (enforced 456-463 us/open
against plain 466-482), and the two independent probe-harness runs of `S7` report 0.995x (MAIN's
implementation) and 1.002x (the oracle's). RULED CLAIM: the enforced read open costs no more than the
plain open; every measurement lands at or below parity and the per-round ranges overlap.

The earlier "1.361x sequential vs 1.024x interleaved" discrepancy is WITHDRAWN. No committed artifact
reproduces 455.759 -> 620.394, and neither the 1.361x nor the 1.024x figure reproduces against the
landed implementation. Do not carry any overhead percentage into a durable claim; carry the ratio band
and the script.

## 7. Gate identity and battery obligations

Decisive gate = `uv run python -m unittest discover -s tests -t .`. Counts: 548 at M3.1's close, 549 at
this unit's entry (the difference is one later test, never a deletion target), 551 after the
implementation commit. Never delete a test to recover an older count.

A green suite is NEVER closure here: enforcement is a hardening, and deleting a pin alongside the
behavior it pins leaves the gate green and the count unchanged. The battery below is the closure
criterion. Each obligation must FAIL when its own subject alone is removed, and must rerun from this
unit's committed checkpoint.

- B1 snapshot lifetime: `in_transaction` True across >= 3 reads; a concurrent writer's committed row is
  invisible for the whole block; caller `commit()` denied.
- B2 authorizer necessity: TEMP-table write, ATTACH-then-write, and `PRAGMA foreign_keys = OFF` each
  denied inside a read block.
- B3 existing-only opening, adjacent pair: an existing ledger opens; a missing one is refused AND the
  path is still absent afterward.
- B4 URI encoding, decoy pair: a ledger whose path contains `?`, `#` and `%`, with a decoy planted where
  raw concatenation would resolve; the read must answer the real ledger's marker.
- B5 `R6` readbacks inside the enforced block: `foreign_keys=1`, `busy_timeout=10000`, `synchronous=3`,
  `temp_store=2`, `trusted_schema=0`.
- B6 setup order and identity: connect arguments per path, the five pragmas in order, both `setconfig`
  calls with their exact arguments, authorizer installed LAST, then `BEGIN`. Two of these operations are
  same-value redundant with other settings (`busy_timeout` with `timeout=10.0`; `setconfig` TRUSTED_SCHEMA
  with `PRAGMA trusted_schema = OFF`), so a readback CANNOT detect their deletion - this obligation needs
  a call spy, not a state assertion.
- B7 pragma allowlist by name: one allowed bare read, one denied assignment on the same name
  (`foreign_keys`), one allowed introspection pragma WITH an argument, one denied unlisted bare pragma
  (`optimize`).
- B8 denial class and exact message for DML, DDL, ATTACH, TEMP write and pragma write; `__cause__`
  preserved; the raw `sqlite3` class is what a caller sees when it catches INSIDE the block.
- B9 absence assertion: the denial class is neither `StateError` nor `IntegrityError`, so a later
  widening of an `except` clause cannot silently re-merge them.
- B10 missing ledger: exact `IntegrityError` message, path absent, CLI exit 5.
- B11 `VACUUM` parity: identical class AND message under `write=False` and `write=True`.
- B12 caller `rollback()` denied; `in_transaction` stays True; the next read answers from the same
  snapshot.
- B13 `executescript("SELECT 1;")` denied through its implicit COMMIT; `in_transaction` stays True.
  Separate pin from `connection.commit()`.
- B14 non-denial branches: a malformed read keeps `StateError`; a non-denial `DatabaseError` keeps
  `IntegrityError("database operation failed an integrity check")`.
- B15 write path exactness: plain `sqlite3.connect(self.path, timeout=10.0, isolation_level=None)`, no
  URI, no authorizer, `BEGIN IMMEDIATE`, commit on clean exit, rollback on exception, always closed.
- B16 frozen public shape: `inspect.signature` + `typing.get_type_hints`.
- B17 recursive-CTE read succeeds (forces the `SQLITE_RECURSIVE` grant).
- B18 `SAVEPOINT` denied inside a read block (pins the removed grant).
- B19 layered guarantee (section 1b): after `set_authorizer(None)`, a ledger write is still refused and
  the ledger sha256 is unchanged, while an ATTACHed write succeeds - the stated limit, asserted so a
  future wider claim fails a test.
- B20 reachability census reruns and still reports zero mutating read sites.
- B21 `_validate_ledger` compatibility: an explicit call inside an enforced block succeeds, and
  `transaction()` makes ZERO calls to it (spy both directions).
- B22 `SCHEMA_VERSION` is 2 and the schema DDL is byte-identical to the unit's entry state.

## 8. Verdict table - MAIN-final

Phase-1 divergences from `test-m3u2a`, with MAIN's rulings. Where a ruling differs from the proposal in
`.scratch/agents/test-m3u2a.md`, this table governs and the difference is stated.

| id | question | MAIN's ruling |
|---|---|---|
| V01 | class for a ledger deleted after `Store` construction | `IntegrityError("ledger file is missing or unreadable")`, exit 5, path still absent. |
| V02 | class for an existing but unreadable ledger | SAME as V01. OVERRULES the proposed `StateError`/exit 4 split: both raise `SQLITE_CANTOPEN` with identical text, so splitting them needs a pre-connect stat whose answer can disagree with what `connect` did, and it would assign retryable exit 4 to a condition retry cannot fix. |
| V03 | `VACUUM` inside `write=False` | Keeps `StateError`, exit 4. OVERRULES the proposed `_ReadOnlyViolation`. Measured: `write=True` raises the IDENTICAL class and message, because the open TRANSACTION refuses `VACUUM` before the authorizer is ever consulted - it is not a capability outcome. The oracle's alternative translates it by exact SQLite message text, which this project forbids as a classification input. The residual defect (exit 4 advertises retry for a permanent condition on BOTH paths) is real, out of this unit's scope, and deferred to `.agent/polish.md`. Pinned by B11's parity assertion. |
| V04 | stale gate count | Baseline 549, 551 after implementation; correct the count, never delete a test to recover 548. |
| V05 | write-path channel | Pinned exactly, per section 5 and B15. |
| V06 | `_validate_ledger` on the read path | No per-transaction validation. One call in `_initialize`, zero in `transaction`, explicit call inside a read block succeeds; order = pragmas -> `setconfig` -> authorizer -> `BEGIN`. B21, B6. |
| V07 | caller `rollback()` | Denied; `in_transaction` stays True; owner alone lifts enforcement to end the snapshot. Landed. B12. |
| V08 | exact denial message | `read-only ledger transaction refused a write`, `__cause__` preserved. The proposed alternative wording is superseded by the landed string. B8. |
| V09 | unrelated read failures | Denial provenance alone selects `_ReadOnlyViolation`; genuine `OperationalError` and `DatabaseError` keep baseline mappings. B14. |
| V10 | pragma allowlist | By NAME, two sets, per section 6a. B7. |
| V11 | `set_authorizer(None)` | Enforcement is bound to a non-sabotaging caller, and the guarantee is layered per section 1b: the LEDGER stays protected by `mode=ro` even after removal. No resistance is claimed for TEMP or ATTACH. B19. |
| V12 | `executescript` | Denied through the implicit COMMIT, `in_transaction` stays True. B13. |

## 9. Review dispositions and differential result

`rev-m3u2a` findings C01-C07, each with an executed proof in `.scratch/agents/rev-m3u2a.md`:

- C01 ACCEPTED IN PART. The report's proof writes to an ATTACHED database, not the ledger; MAIN's probe
  shows the ledger itself stays read-only after `set_authorizer(None)`, sha256 unchanged. Resolution is
  the layered claim in section 1b plus B19, not a wrapper.
- C02 ALREADY CLOSED by the landed implementation: `ROLLBACK` is absent from the transaction allowlist,
  so caller `rollback()` raises and `in_transaction` stays True. B12 pins it.
- C03 ACCEPTED. `SQLITE_SAVEPOINT` REMOVED (unforced, unreachable from any read path);
  `SQLITE_RECURSIVE` KEPT and now forced by B17. Section 6a records both.
- C04 ACCEPTED. Two setup operations are same-value redundant, so readbacks cannot detect their
  deletion; B6 requires a call spy instead of a state assertion. Production stays unchanged - the
  redundancy itself is off-spine and belongs to `.agent/polish.md`.
- C05 ACCEPTED. Section 5's `_validate_ledger` claim is rewritten to authorizer-compatibility; B21 pins
  both directions.
- C06 ACCEPTED. Section 6b withdraws the discrepancy and records a re-measured band plus a committed
  benchmark script.
- C07 ACCEPTED. Section 1 derives the call-site total instead of restating it.

DIFFERENTIAL (`diff`), MAIN's rerun of the oracle's own 32-seam driver
(`.agent/decisions/m3u2a-store-probes.py`) against both implementations, compared on outcome, exception
type and message:

- 32/32 probes ran on both. ONE behavioral divergence: W13 `VACUUM` (`StateError` here,
  `_ReadOnlyViolation` in the oracle), ruled in V03.
- 17 message-text divergences, all of them the oracle's independently chosen wording for the same
  outcome and class. The contract owns the exact strings; the landed ones govern.
- `.agent/decisions/m3u2a-differential.py` grades the comparison and carries the ruled divergence set,
  so the claim reruns instead of resting on this paragraph.
- `S7` cost agrees across implementations (0.995x, 1.002x), which is what closes C06.
