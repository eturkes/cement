---
paths:
  - "src/cement_runtime/**"
---

# Runtime law — library, store, CLI

## Storage

- All 13 user tables are `STRICT` (`sqlite_sequence` excepted) ⇒ non-numeric `TEXT` is unstorable in an `INTEGER` column, numeric `TEXT` converts at write, and integer columns are `NOT NULL` ⇒ `NULL` is unstorable. Exactly 3 nullable `INTEGER` columns exist (`requests.lease_until_us`, `proposals.reviewed_at_us`, `artifacts.promoted_at_us`) and every conversion reading one is guarded, so guarded/unguarded tracks nullable/NOT NULL exactly.
- A stored-scalar conversion raises `TypeError` and `OverflowError`, not only `ValueError`: translate all three to `IntegrityError` or validate the exact stored type first (`_stored_int` uses `type(value) is not int`, which also rejects `bool`).
- A fresh `System` — which every CLI invocation constructs — rejects a rewritten schema at construction and exits 5, so a probe needing a schema rewrite, a fabricated row or a cursor proxy is labelled fabricated and is never cited as a real-ledger repro. A library-level corruption fixture does not transfer to a CLI test: capture the trigger DDL from `sqlite_master`, drop, corrupt, recreate, commit.
- A validator whose RESULT is discarded is not a check: a validator's return value must be compared, bound or recomputed against something.
- Public writes carry a commit-then-raise window: a durable commit that then fails leaves `StateError` with no id and every row written. Scope purity claims to failures BEFORE commit, publish the window, and make recovery ENUMERATION — a retry writes a second row, since no route is idempotent.
- Authorization or validation written as a loop over members has an empty-set hole: gate collection emptiness explicitly before clock/ID/write work.

## Read capability

- `mode=ro` protects ONLY the main database file — TEMP table creation, ATTACH-then-write and `PRAGMA foreign_keys=OFF` all still succeed under it, and it alone refuses a missing path (the authorizer installs after `connect`, so it can never prevent file creation).
- Deny-by-default authorizer allowlists by NAME, split into a readable-bare set and an introspection set; a SHAPE rule fails both ways, since SQLite reports a pragma's subject and its assigned value in the same argument. Denials produce a uniform `sqlite3.DatabaseError("not authorized")`, cover explicit `commit()`, and must cover ROLLBACK — a caller that can end the snapshot does not leave the owner owning it.
- Classify on `sqlite_errorcode` alone: `SQLITE_AUTH`(23) is reachable only from the authorizer, `SQLITE_READONLY`(8) only from `mode=ro`, `SQLITE_CANTOPEN`(14) covers missing and unreadable alike and is never split. An authorizer denial lands on `except sqlite3.DatabaseError` → `IntegrityError` → exit 5, which misnames a caller bug as ledger corruption.
- `VACUUM` inside a read block is refused by the open TRANSACTION, not by the capability, and raises identically under `write=True`; the shipped claim is a PARITY assertion.
- Convert a path to a `file:` URI with `Path.absolute().as_uri()`; concatenation opens a DIFFERENT file for names carrying `?`, `#` or `%`.
- Test-only pragma injection (`reverse_unordered_selects`) uses a named helper that clears the authorizer, injects, and reinstalls — never a wider production allowlist.
- Read-only proof and single-snapshot lifetime are separate guarantees: a mid-method `commit()` passes every read-only assertion while splitting the snapshot. Pin lifetime by asserting `connection.in_transaction` inside the inner helper. Layer the claim by what the caller can reverse: the LEDGER stays read-only even after `set_authorizer(None)` because `mode=ro` is an open-time flag; TEMP and ATTACH are protected only while the caller cooperates.

## Verification, function identity, cost

- `verify_function` raises for EXACTLY five conditions (unregistered operation; malformed stored revision, policy hash or policy JSON; promoted-set count disagreeing with the enumerated rows). Every other defect — corrupt artifact JSON, broken report bindings, revocation, projection mismatch — is caught locally and becomes a FALSE check with bounded detail, and an over-capacity set (`FUNCTION_MAX_ENTRIES` 50,000) returns early with all six checks FALSE. A consumer mapping structural corruption to a raised class is wrong about most of the surface.
- Function identity = verified-content identity: `entry_seal` is `cement-promotion-v2` minus `promoted_by`/`promoted_at_us`, so a prospective hash is computable before promotion and re-promoting identical content yields one hash. Never move promoter/time out of `cement-promotion-v2` — `_validate_promoted` recomputes from those row fields, and that is the only detection of active-row provenance forgery.
- Draft eligibility is RECONSTRUCTION, not status filtering: current revision, `draft`, exact canonical input, AND the `build_hash` that `_project_current_build` independently projects, with `compile` and the batch enumerator sharing that helper.
- `resolve` pays full P1-P6 verification per call — 35,550 ms cold / 985,864 KiB peak RSS at the 50,000-entry cap, 616 ms at 1,000, 4.1 ms at one; time scales `N^1.037`, memory `N^1.000`, the evaluator is 0.00028% of the total. Never write read-only, pure or deterministic in a way that implies fast; cite the numbers. Re-measure any cost claim whose harness predates the surface it prices, publish per-point provenance (commit, environment, repeats) and refuse to merge points across differing provenance, and measure only on a quiet machine (ordinary editing inflates both figures ~22%).
- `function_report`'s six detail lists share no ordering guarantee: members project by `ordinal` and artifacts by `sequence DESC`, but `pending_proposals` orders by `p.id` and `stale_revision_anomalies` by artifact `id` — random hex, stable per ledger, arbitrary as a page. Pin set membership plus per-ledger byte stability.
- Cursor pagination over per-call transactions is not a snapshot; a row promoted mid-traversal is never seen by the walk in progress. Enumeration leaves report their own table, never existence — `function_receipts` has no FK to `operations`.
- An exported bundle is NOT byte-reproducible across clean runs: per-run evidence and verification-example IDs feed `evidence_snapshot_hash`/`test_set_hash` → `entry_seal` → `function_hash`. A committed bundle is a captured sample.
- No `cement_runtime` submodule import is store-free — the package `__init__` imports `.system` → `.store` → `sqlite3`. Ledger-free, import-free and capability-free are three properties needing three words: `function eval` is ledger-free but opens a filesystem path. Prove ledger-freedom by patching `System` to raise plus `sqlite3.connect`, never by inspecting the import graph.

## Errors and boundaries

- `ValidationError` subclasses `ValueError`, so a helper raising its own verdicts under a residual `except (OSError, ValueError)` rewrites those verdicts; keep the wide catch for totality (`os.open` raises bare `ValueError` on an embedded NUL, `UnicodeEncodeError` on a lone surrogate) and precede it with `except ValidationError: raise`.
- `raise X from None` INSIDE an `except` block leaves the adapter's exception reachable on `__context__`; catch, discard, EXIT the handler, then raise. `__context__ is None` is the pin.
- Ownership, not exception class, decides translation: a caller's own object raising during validation reaches the caller UNCHANGED; the same failure behind an adapter boundary is contained totally or not at all. A constructor pre-flight reading an attribute (`callable(getattr(source, "propose", None))`) IS the hazard it looks like a guard against — classify an unusable collaborator where it is INVOKED, and give only `None` its own error.
- A guard protecting a window is meaningless for a caller that never opened one: compare a captured revision only when the caller supplied an expectation.
- Filesystem writers: one `os.lstat` + `stat.S_ISREG` beats chained `pathlib` predicates (each is a syscall, and they suppress only `_IGNORED_ERRNOS`, so a search-denied ancestor escapes as a bare `PermissionError`); name the temp yourself with random bytes and `O_CREAT | O_EXCL` (a `mkstemp` prefix can draw the destination's own name); `os.fchmod` the descriptor, since `mkstemp` and `os.open(..., 0o600)` both request `mode & ~umask`; grade `os.fstat(descriptor)` before the handover, closing on every pre-handover failure, because `os.fdopen` refuses a directory itself.

## CLI

- Exit classes: 2 usage/validation, 3 absent, 4 conflict (the ONE class where retry is the intended recovery), 5 integrity, 6 negative verdict. Retryability is per class; defending a new nonzero code as "no worse than the existing ones" is a claim-soundness defect. Exit class is the shared vocabulary; CHANNEL is the leaf's own stdout contract — a byte-producing leaf keeps stdout empty on a negative verdict, because a redirect truncates the target before the process runs. Root `verify` reports failure with exit 0: frozen precedent, never a model, and every new verdict leaf pins both branches explicitly.
- `argparse` option abbreviation is live on EVERY node except where `allow_abbrev=False` was added (`resolve`, `proposal submit`): `--part`, `--bun` and `--in` resolve today, a deleted flag stays reachable through any unambiguous prefix of a surviving one, and a new flag colliding with an existing prefix is a grammar defect no exact-spelling test sees. Removal predicates drive the ABBREVIATIONS too.
- Derive the leaf census from `_parser()` inside the test, never from a number in a record. Assert the NAME SET: a count collides across opposite states (removing two leaves returns the exact pre-addition count over the inverse set). The `parser_shape` digest covers dest, option strings, default, required, nargs, class and `allow_abbrev` — NOT help, `choices` or `type`, so a lying help string or a swapped `type` survives it.
- Where one leaf routes the same argument to two library calls, check that EVERY branch grades it — import the library's own validator (`_name`, `_request_id`) and call it before dispatch.
- A CLI-owned bound over an unclamped library projection makes state CLI-unreachable and buys nothing: the bound belongs to whichever layer owns the query. An unsliced payload takes no count field.
- Linux refuses an exec argument well below 1 MiB here (~120 KB launches, ~140 KB is E2BIG) while in-process `main([...])` has no wall, so any adjacent-pair test at `DEFAULT_MAX_BYTES` travels through `--input -`.
- Known residue, each owning a `.agent/deferred.md` row: every WRITE leaf creates a ledger on a typo'd `--db` or an invalid argument value (value parsing runs after `System(...)`); `_input` does not translate an `OSError` from stdin; `_emit` performs no explicit flush; `main` does not handle `KeyboardInterrupt`; `_request_id` reports the label `request_id` for proposal, artifact, example, report and receipt ids; `system.py` re-implements the 64-hex predicate at three sites beside `_digest`.

## Events

- `System.events()` dicts key the event name under `kind`; there is no `type` field. `_event(kind=...)` takes three spellings — a plain `Constant`, an `IfExp` whose SECOND branch a first-branch scan never reads, and a `JoinedStr` whose interpolation resolves only through a `Literal[...]` annotation on a local — so derive any kind set over all three.
- Every event producer and branch pins its own payload keys; a key with zero pins repo-wide is unobservable to the gate, so its removal needs a pin written first.
