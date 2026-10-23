# p35 contract — `serving` reuses a verification while the ledger is unchanged (revision 2)

Row (verbatim acceptance, `.agent/deferred.md`): Key database identity+revision+latest receipt
sequence/hash+all check-affecting state; corruption and concurrent writers invalidate;
1/1,000/50,000 show material gain; cached bytes equal uncached; readers never block writers.
Owner rulings (queue run 3): funded; scope = writes made through SQLite (any connection, any
process, out-of-band SQL corruption included); a raw byte edit that bypasses SQLite and a ledger
path replaced during an open snapshot are outside the cache's guarantee; `function verify` stays
the uncached full check. Amends `.agent/spec.md` `Decisions` ("`resolve` pays full verification …
per call, no cache"). Tier `kernel`. Revision 1 → 2 = consultant-1's verdicts (+ its implementation audit: the observer reads `data_version` BEFORE `journal_mode`, whose answer is stale until the pager refreshes)
(`.scratch/queue-run-3/consultant-1/verdicts.md`, measured on SQLite 3.53.1 + 3.40.1): a second
descriptor on the ledger releases SQLite's POSIX locks when closed (header reads rejected), the
header counter is no snapshot token by itself, cached values must not alias caller-mutable JSON,
a `BEGIN` proves no lock release.

## Premises (measured)

- P1 `Store` = rollback journal (`journal_mode = DELETE` at creation; an existing ledger keeps
  its mode); a read transaction = deferred `BEGIN`, SHARED from its first main-table read until
  the closing rollback (`SELECT 1` takes no lock).
- P2 While any reader holds SHARED, no writer commits. A separate read-only connection's
  `PRAGMA data_version` changes after every commit by any OTHER connection (this process or
  another), never on a no-op or rolled-back write; a fresh connection starts again at 1; closing a
  SQLite connection keeps other connections' locks (SQLite's fd bookkeeping).
- P3 `serving` = `_switch_state` → `_verify_function_snapshot` (`follow`) |
  `_verify_pinned_snapshot` (`pinned`) | nothing (`off`); deterministic over the ledger, the
  verifier's code and `FUNCTION_MAX_ENTRIES` (patched at run time by the suite).
  `FunctionDocument.value` + nested values are caller-mutable.
- P4 Integrations build a fresh `System` per call in a long-lived process (Open WebUI tool) ⇒
  the cache is process-wide; CLI and nucllei calls are one process each, so always cold.

## Obligations

- C1 Scope: `System.serving` (⇒ `resolve`, `function export`) reuses a cached verification for
  an equal key; `verify_function` stays uncached.
- C2 Observation + key, in this order while the serving snapshot holds SHARED: `_switch_state`
  (a main-table read; `SELECT 1` would take no lock) → `os.stat(path)` (never a descriptor)
  → the process-wide read-only observer of that `(st_dev, st_ino)` reads `PRAGMA data_version`
  → then `PRAGMA journal_mode`, which answers from connection state until `data_version` has
  refreshed the observer's pager → the token is accepted only for `delete`. The snapshot
  connection runs SELECT alone (B20 + `tests/test_read_capability_census.py`). The observer =
  `mode=ro`, autocommit, busy timeout 0, no transaction or cursor between observations, created
  / used / closed under one lock, closed through SQLite only; each incarnation takes a
  never-reused generation. Key = `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` +
  generation + `data_version` + partition + operation + `(mode, function_hash, receipt_id)` +
  `expected_function_hash` + `FUNCTION_MAX_ENTRIES`. A miss verifies in that same snapshot,
  then stores.
- C3 Bypass (verify in full, no lookup, no store): journal mode other than `delete` (also retires
  that inode's observer: an idle WAL observer blocks a later switch to DELETE); observer BUSY
  (a same-process writer holding PENDING) or any observer error. The read authorizer is
  unchanged: the snapshot connection runs no PRAGMA.
- C4 Invalidation: a commit through SQLite by any connection or process changes the key: a
  `System` write, a commit by another process, out-of-band corruption of the first, middle and
  last promoted member (trigger-preserving SQL, committed), a concurrent writer between calls.
- C5 Isolation + equality: the cache keeps a private master copy (`copy.deepcopy` at store) and
  hands every hit its own deep copy (measured at 1,000 entries: 93 ms vs 213 ms for
  `parse_function`, which re-validates every entry), so a caller mutating a returned value never
  reaches a later call; memory = one document per cached verification. Cached results equal
  uncached ones for `off`, `follow` (pass + fail), `pinned` (pass + fail).
- C6 No held lock: observers hold no transaction; after a cached call (and after an observer's
  eviction) another process COMMITs an actual write at busy timeout 0, beside a control in which
  an open reader really blocks that COMMIT; WAL → DELETE succeeds after a WAL bypass retired the
  observer.
- C7 Bounds + safety: at most 8 cached verifications and 8 observers in the active maps (LRU
  each; evicting an observer orphans its generation's entries; a fork child parks its parent's
  maps unused, outside that bound); the lock is never held during a full
  verification; `os.register_at_fork` gives the child a fresh lock, fresh maps and fresh
  generations (inherited connections are dropped unused).
- C8 Measurement: a harness on today's lifecycle (`submit_proposal` → `review` ×2 → `compile`
  → `verify_drafts` → `promote_function` → `set_switch follow`) times a cold `resolve` and a
  warm one (same process, same key) at 1, 1,000 and 50,000 entries; provenance + host load per
  point; the warm/cold ratio recorded as measured (material = warm ≤ 10% of cold at 1,000 and
  50,000). Taken only on a host with a free offload slot; otherwise the row stays open, bench owed.
- C9 Records: `Decisions` ruling amended; README `resolve` cost paragraph, the `resolve` +
  `serving` docstrings, `.claude/rules/runtime.md` (+ the observer sits outside every
  `transaction(write=False)` block) + `human-facing.md` restated; prose pins X32
  (`tests/test_cli_channels.py`) + D30 (`tests/test_cli_channels_battery.py`) re-targeted at the
  new claim (standing pin-repair approval).

## Gates (numbered; rerun from committed state)

1. New tests, red at the parent: warm call verifies once (spy on the snapshot verifiers); a second
   `System` on the file shares the entry; same-process `System` write, other-process commit,
   first/middle/last corruption, concurrent writer → full verification; no-op write keeps the
   hit; WAL bypass + observer retirement (DELETE switch then succeeds); observer BUSY → bypass,
   no deadlock; observer eviction → new generation, repeated `data_version` 1 never reuses an
   entry; caller mutation of a returned document never reaches the next call; equality across
   modes; COMMIT at timeout 0 after a cached call + the blocking control; `FUNCTION_MAX_ENTRIES`
   in the key; LRU bounds; fork child resets.
2. Full gate = CI gate.
3. `uv run python .agent/decisions/p32-differential.py --base <parent>` → `SAME` (the uncached
   path unchanged; the corpus builds a fresh process per tree).
4. Bench C8.

Machine-local: each `.scratch/` path in this file names a gitignored input or output of the session that wrote it; no clone retrieves it, and the file states the substance it relied on (p10).
