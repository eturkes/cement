# M3.2a acceptance contract - Store-owned enforced-read capability

Unit: M3.2a, tier `kernel`, tags `oracle`, depends none. Oracle-calibration unit per the roadmap's
ORACLE SURCHARGE ruling. Sections 1-5 are settled MAIN-side and spike-independent. Section 6 is decided
by wave-1 spike arbitration. Every downstream artifact decides against this file.

## 1. Scope

`Store.transaction(write=False)` opens a read-write connection under plain `BEGIN`
(`src/cement_runtime/store.py:550-571`, `_connect` at `store.py:488-511`). Plain `BEGIN` is not
query-only, so the connection can upgrade to a write and commit. The unit makes the read capability
enforce read-only at the connection layer.

Measured base span = 46 production lines across exactly two methods (`_connect` 488-511,
`transaction` 550-571). Blast radius = 32 `.transaction(` sites in `system.py`, 113 in
`test_system.py`, 1 each in `test_cli.py` and `test_authority_removal.py`.

### 1a. Measured baseline - both defects reproduced against a real ledger

MAIN smoke probe, run before any test existed, against a freshly constructed `Store`:

- A write inside a `write=False` block does not merely upgrade, it COMMITS.
  `INSERT INTO schema_metadata(key, value)` inside `with s.transaction(write=False)` completed with no
  error, the row read back on the next transaction, and the ledger sha256 moved
  `090d735f101f17f4` -> `75a01c01cb380366`. `transaction` commits on clean exit
  (`store.py:562`), so the read seam is a silent write seam. `schema_metadata` carries
  `BEFORE UPDATE`/`BEFORE DELETE` triggers but no `BEFORE INSERT`, and `_validate_ledger` compares
  schema OBJECTS rather than rows, so the injected row survived undetected.
- A read transaction against a deleted ledger file created a 0-byte file at the ledger path and
  reported `StateError: database is busy or unavailable`. A later `Store(path)` sees a 0-byte file,
  finds `user_version` 0 and an empty `sqlite_schema`, and initializes a FRESH EMPTY LEDGER. Deletion
  of the ledger is therefore laundered into ordinary first-run initialization.

Both are measured, not inferred. They are the unit's justification and its two headline predicates.

## 2. Frozen public shape

`Store.transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]` keeps its exact
signature, keyword-only marker, and contextmanager decoration. Enforcement is internal. No call site
changes its call, so the unit's edit set stays inside `store.py` plus tests.

Rejected: splitting the seam into separate `read()`/`write()` managers. It buys the same enforcement
while editing 145 call sites, which converts a 46-line unit into the largest unit in the milestone.

Pin: one `inspect.signature` + `typing.get_type_hints` test, because frozen public shape is invisible
to behavioral tests (keyword-only markers, defaults, and return annotations all survive a green suite).

## 3. The error-class defect this unit must fix

Enforcement makes a previously-silent condition raise, and the existing `except` chain misclassifies it
in both directions:

- A `mode=ro` or `PRAGMA query_only` write raises `sqlite3.OperationalError`, which
  `store.py:565-566` maps to `StateError("database is busy or unavailable")` -> CLI exit 4
  (`cli.py:708-710`). Exit 4 is the ONE class where retry is the intended recovery. A write attempted
  inside a read capability is not transient and never succeeds on retry.
- An authorizer denial raises `sqlite3.DatabaseError` ("not authorized"), which `store.py:567-568` maps
  to `IntegrityError("database operation failed an integrity check")` -> exit 5, which asserts ledger
  corruption a retry cannot clear. The ledger is intact; the caller asked for the wrong capability.

Both readings are untruthful about what happened, so the unit owns the classification, not just the
denial. Measurement makes the `IntegrityError` path the DOMINANT one, not an edge case: under an
authorizer, 16 of 17 write-denial probes raise `sqlite3.DatabaseError("not authorized")`
(`spike-m3u2a-min` matrix), which is precisely the branch that currently reports exit 5 corruption.

DECISION, settled by the reachability census in section 3a: the condition is developer-only, so it
raises a dedicated non-retryable class - never `StateError`, never `IntegrityError`.

Chosen shape: a PRIVATE `_ReadOnlyViolation(CementError)` in `store.py`, not exported from
`__init__.py`. It lands on CLI exit 2 through the existing catch-all (`cli.py:714-716`) with no CLI
edit, and exit 2 is truthful here because the process failed before any write. Private rather than
public because M3 is a trimming milestone and an unreachable-by-operators fault must not grow the
public API; callers who want it can still catch `CementError`, and the unit's tests import it directly.

Forbidden resolutions, each rejected on record: reuse `StateError` (advertises retry for a permanent
condition); reuse `IntegrityError` (misnames a caller bug as corruption); let `sqlite3.OperationalError`
or `sqlite3.DatabaseError` propagate raw (leaks a stdlib class through a public seam); guard with
`assert` (`python -O` strips it, and this project has already paid for an `assert`-bound invariant).

### 3a. Reachability census - MAIN-derived, complete

`ast` walk of `src/cement_runtime/system.py`, classifying by parsed SQL rather than by vocabulary:

- 32 `transaction()` `with`-sites: 15 `write=True`, 17 read.
- All 17 read sites execute SELECT only. Zero mutating verbs, zero `connection.commit()` calls.
- 9 read sites hand the connection to 12 distinct helpers. Transitive walk of all 12: SELECT only,
  zero commits.
- Whole-file `execute()` census: 74 literal SELECT, 3 f-string SELECT, 14 INSERT, 29 UPDATE,
  1 SAVEPOINT, 2 RELEASE, 1 ROLLBACK. NO non-literal, non-f-string SQL exists anywhere in the file, so
  no execute site escapes static classification.

Conclusion: enforcement breaks no shipped call site, and a write inside a read block is unreachable
except as a programming error. This is what licenses the private, non-retryable class above. The census
is a script result, not a reading - it reruns from committed state and must be rerun if `system.py`
changes before the unit lands.

Forbidden resolutions, each rejected on record: reuse `StateError` (advertises retry for a permanent
condition); reuse `IntegrityError` (misnames a caller bug as corruption); let `sqlite3.OperationalError`
propagate raw (leaks a stdlib class through a public seam); guard with `assert` (`python -O` strips it,
and this project has already paid for an `assert`-bound invariant).

Pin: both branches. One test that a denied write raises the chosen class with the exact message, and one
that the class is NOT `StateError` and NOT `IntegrityError` - an absence assertion, because a later
widening of an `except` clause would otherwise silently re-merge the classes.

## 4. Existing-only opening is a separate guarantee from write denial

Today a read transaction against a deleted ledger file silently CREATES an empty database, and the
first `SELECT` then fails as `no such table` -> `StateError("database is busy or unavailable")`. Two
defects in one path: a spurious empty file appears where the ledger was, and the report names a
transient condition.

The capability must refuse to open a nonexistent path and must leave no file behind (`S3` in the probe
corpus). This is a distinct predicate from write denial and needs its own adjacent pair: an existing
ledger opens, a missing one is refused with the path still absent afterward.

## 5. Preserved invariants - each pinned independently

A removal or hardening keeps a green suite while deleting a behavior together with its pin, so every
item below gets its own assertion that fails when that item alone disappears:

- All eight read-path probes `R1-R8` keep answering. `R6` matters most: `_connect` executes five
  pragmas, several of which are writes or authorizer-visible, so a mechanism that denies them breaks
  connection setup itself.
- Snapshot lifetime: `connection.in_transaction` stays True across a multi-read block. Read-only proof
  and single-snapshot lifetime are separate guarantees; a mid-method `commit()` satisfies every
  read-only assertion while splitting one snapshot into two.
- `_validate_ledger` still runs on the read path.
- `SCHEMA_VERSION` stays 2 and `store.py`'s schema DDL stays byte-identical. M3 cuts schema ONCE, at
  M3.6b.
- Write transactions (`write=True`, `BEGIN IMMEDIATE`) keep their exact current behavior, including the
  `OperationalError` -> `StateError` and `DatabaseError` -> `IntegrityError` mappings, which stay
  correct on that path.
- `Store.__init__`'s path validation ladder is untouched.

## 6. Mechanism composition - RULED

Evidence: `.agent/decisions/m3u2a-min-matrix.json` (32/32, 0 mismatches, validator exit 0),
`m3u2a-min-spike.md` (report), `m3u2a-min-spike.py` (1,141-line probe harness, reruns from committed
state). `spike-m3u2a-full` died twice and produced no matrix; its ablation deliverable is SUPERSEDED,
not merely missing - ALT-MIN's leave-one-out controls measure the same per-mechanism attribution
constructively, by adding each mechanism only when a probe forced it and then re-running the full
corpus with each member omitted in turn.

ADOPTED - three mechanisms, each with a distinct forcing probe and a distinct leave-one-out failure:

1. One explicit Store-owned transaction ended with rollback. Forced by `R8`; confirmed by `S5`/`S6`.
   Omitting it: `R8` `in_transaction` reads `[False, False, False]`, `S5` sees the concurrent writer's
   row mid-transaction, `S6` commit splits the snapshot. The other two mechanisms deny writes but
   supply NO snapshot lifetime, which is the separate guarantee section 5 requires.
2. Deny-by-default, read-allowlisted SQLite authorizer. Forced by `W1`. Omitting it: `W10` TEMP table,
   `W11` ATTACH-then-write, and `W15` `PRAGMA foreign_keys=OFF` all SUCCEED, because `mode=ro` protects
   only the main database file. It also denies explicit `commit()`, closing the snapshot-split hazard.
3. Percent-encoded, existing-only `file:` URI with `mode=ro`, built from `Path.absolute().as_uri()`.
   Forced by `S3`. Omitting it: the missing path is opened AND created, because the authorizer is
   installed after `sqlite3.connect` and cannot act before the connection exists.

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

COST - unresolved discrepancy, re-measure at implementation. The spike's matrix note records a
SEQUENTIAL 1,000-open pass at 455.759 -> 620.394 us/open (1.361x), while its report records an
INTERLEAVED pass at 486.550 -> 498.115 us/open (+11.565 us, 1.024x). The interleaved method is the
sounder one and the ranges overlap, but the artifact and the report disagree by an order of magnitude
in the delta, so neither number is quotable yet. Re-measure against the real implementation, interleaved,
and record one number. Do not carry 2.4% into any durable claim before then.

## 7. Gate identity

Decisive gate = `uv run python -m unittest discover -s tests -t .`, currently 548 tests. The unit's own
battery must fail when one obligation above remains undone OR one preserved invariant disappears, and
must rerun from this unit's committed checkpoint.

A green suite is never closure here: enforcement is a hardening, and deleting a pin alongside the
behavior it pins leaves the gate green and the count unchanged.

Binding test directives carried from the spike:

- Pin the AUTHORIZER ALLOWLIST itself, not only the 17 named write statements. A permissive authorizer
  mutation otherwise leaves `mode=ro` looking sufficient while TEMP and ATTACH capabilities stay
  writable - `W10`, `W11` and `W15` are the probes that catch it, and they are the ones a
  statement-only suite omits.
- Each of the three mechanisms needs its own leave-one-out red test, because the spike proved their
  failure sets are disjoint. One combined "read-only works" test pins none of them individually.
- `S4` ships as a decoy pair: a hazardous path that resolves correctly under encoding, beside the raw
  concatenation that resolves to a planted decoy. A single-path test passes under both codepaths for
  space, newline and non-ASCII names.
- `S3` ships as an adjacent pair: an existing ledger opens, a missing one is refused AND leaves the
  path absent. Assert the absence; the defect being removed is file CREATION, not just failure.
- `R6` pins all five setup pragmas with their exact readbacks (`foreign_keys=1`, `busy_timeout=10000`,
  `synchronous=3`, `temp_store=2`, `trusted_schema=0`), since setup runs before enforcement is
  installed and a reordering would silently move them behind the authorizer.
- The reachability census in 3a is itself a committed check: it must rerun and still report zero
  mutating read sites, or the private-class decision in section 3 is void.
