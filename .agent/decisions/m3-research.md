# M3 removal research

| id | question | answer | source | confidence |
|---|---|---|---|---|
| Q1 | Optional surface that stays tested | Keep `CommandCandidateSource` in `examples/command_candidate_source/` and import it from `tests/` with the existing explicit `sys.path` pattern. | `pyproject.toml`; `tests/test_hospital_ocr_example.py` | measured |
| Q2 | Honest claim scoping after withdrawing idempotency | Document `resolve` as a read-only query and proposal submission as an at-least-once-capable command with no Cement-owned idempotency or exactly-once guarantee. | https://docs.stripe.com/error-low-level; https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html | sourced |
| Q3 | Pre-1.0 schema break without migration | Bump the package minor and `SCHEMA_VERSION`, keep fingerprint/full-schema refusal before writes, and ship an explicit archive-and-rebuild release note plus actionable exit-5 diagnostic. | `/tmp/res-m3-q3-probe.sh` | measured |
| Q4 | Provably non-mutating SQLite reads | Give `resolve` a dedicated existing-only `mode=ro` connection, enable `query_only`, install a write/DDL/PRAGMA/attach-denying authorizer, and hold one explicit read transaction that always rolls back. | `/tmp/res-m3-q4-probe.py` | measured |

## Q1 — Optional surface that stays tested

**Recommendation.** Put the reference implementation in `examples/command_candidate_source/`, outside `src/cement_runtime`. Keep only the structural `CandidateSource` protocol in core. Add ordinary `unittest` coverage under `tests/` that inserts the example directory into `sys.path`, exactly as `tests/test_hospital_ocr_example.py` does. This is the smallest split that keeps the sole configured gate authoritative and makes the core wheel omit subprocess-launching code.

### Comparison

| shape | `pyproject.toml` effect | built wheel effect | single-gate effect | ruling |
|---|---|---|---|---|
| `examples/` imported by tests | No change is required. The existing `source-include = ["docs/**", "examples/**", "tests/**"]` puts the example and its tests into the sdist. | None. `uv_build` does not use `source-include` for wheels, so the core wheel excludes `examples/` and `tests/`. | `uv run python -m unittest discover -s tests -t .` discovers a test that inserts the example directory and imports the implementation. | **Use this now.** It exactly meets the stated criterion and matches established repository practice. |
| One distribution plus an optional dependency extra | Add `[project.optional-dependencies]`, for example `command-source = ["some-dependency"]`. If the implementation has no third-party dependency, the extra has nothing meaningful to declare. | One fixed wheel still contains every package module. An extra only adds `Provides-Extra` and conditional `Requires-Dist` metadata; it cannot make a module appear only when selected. Code under `src/cement_runtime` therefore remains bundled, while code left under `examples/` remains absent. | The current gate can test either location, but the extra itself adds no test/install boundary. | **Reject for this split.** Extras select dependencies, not files, and therefore do not move the implementation out of core. |
| Separate distribution | Add another project root with its own `pyproject.toml`. A uv workspace also needs `[tool.uv.workspace] members = [...]`; to make the unchanged root `uv run` install the sibling, the root must declare it as a development dependency and map it with `[tool.uv.sources] ... = { workspace = true }`. | The core wheel stays free of the implementation; a second independently buildable wheel contains it. | It stays in the one command only if the root environment installs the member, or if tests use another source-path insertion. Plain `uv run` targets the workspace root and its dependencies, not every member. | **Defer.** This is correct only when an independently installable, versioned, publishable adapter becomes a product requirement; it adds a second release surface now. |

The current artifact was measured from this checkout without writing into the repository:

```text
$ UV_CACHE_DIR=/tmp/res-m3-q1-uv-cache uv build --out-dir /tmp/res-m3-q1-dist
build_rc=0
$ UV_CACHE_DIR=/tmp/res-m3-q1-uv-cache uv run --no-project python <archive-inspection>
wheel=cement_runtime-0.1.0-py3-none-any.whl
wheel_examples=0
wheel_tests=0
wheel_files=20
sdist=cement_runtime-0.1.0.tar.gz
sdist_examples=14
sdist_tests=7
sdist_files=48
inspect_rc=0
```

This observed result matches the current [`uv_build` inclusion rules](https://docs.astral.sh/uv/concepts/build-backend/): `source-include` applies to the source distribution, and there are no general wheel includes. It also matches the PyPA [`optional-dependencies` specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/): extras become dependency metadata, not conditional wheel contents. A future separate distribution can use a uv workspace, but [plain `uv run` operates on the root package](https://docs.astral.sh/uv/concepts/projects/workspaces/) unless that root depends on the sibling.

## Q2 — Honest claim scoping after withdrawing idempotency

**Recommendation.** Make the command/query boundary explicit, then disclaim the guarantee rather than transferring it with vague wording. Caller ownership is truthful only if the documentation names the retry gap: without a caller token in Cement's API and ledger, Cement cannot provide retry-safe or exactly-once proposal creation. A caller can prevent lost intent with an outbox, but an at-least-once relay can still create duplicate proposals.

### Claim sentences MAIN can adapt

| candidate claim sentence | what this commits Cement to |
|---|---|
| **“`resolve` is a read-only query over one committed ledger snapshot. It never invokes a candidate source, creates a proposal, acquires a lease, or changes ledger state.”** | A hard non-mutation contract, one snapshot per call, no hidden fallback, and no request lifecycle. Q4 must structurally pin the write prohibition. It does not promise that a later call sees the same state. |
| **“Proposal submission is a state-changing command. Each invocation is a new attempt, and retrying it can create another proposal.”** | Duplicate creation is allowed and visible. The implementation must not silently deduplicate by operation/input content or retain old request semantics. A returned proposal ID is a command receipt, not an idempotency guarantee. |
| **“Cement does not accept, persist, or enforce request idempotency keys, and it does not expose request-status polling.”** | The request ID, immutable request binding, leases, retry flags, and lifecycle statuses are absent from the public API, CLI, schema, and claims. |
| **“If retry safety is required, the caller must durably allocate one logical-operation ID and bind it to the partition, operation revision, canonical input, candidate content, and source revision before calling Cement.”** | This is integration guidance, not a Cement guarantee. It requires the caller's deduplication check and state transition to be atomic at the caller-owned boundary. Reusing an ID with different bound content must be a named mismatch, not a replay. |
| **“A timeout, process failure, or lost response during proposal submission leaves the outcome indeterminate. The caller must reconcile before retrying or accept that the retry may create a duplicate proposal.”** | Cement makes no success/failure inference from transport outcome. Documentation and errors must not say a failed call implies that no row was committed. |
| **“A business-state write and a Cement submission are not one atomic transaction. Use a transactional outbox or an equivalent durable handoff to prevent lost intent; assume that the relay can submit more than once.”** | No cross-database or cross-service atomicity claim. The advice accurately separates the outbox's lost-intent protection from duplicate suppression. |
| **“Cement provides neither exactly-once proposal submission nor exactly-once effect execution. Callers must tolerate duplicate and out-of-order delivery and make downstream effects idempotent.”** | No end-to-end exactly-once claim. The existing “returns data, not effects” boundary remains. If order matters, callers must persist sequence/order state themselves. |
| **“A `resolve` result is not a lease. Ledger state, authorization, policy, and external facts can change after it returns.”** | One-call snapshot semantics only. The caller must re-run live authorization and policy before effects; Cement does not reserve the answer or serialize later action. |

### Why these words are honest

[Stripe calls a lost or timed-out mutation **indeterminate**](https://docs.stripe.com/error-low-level) and tells clients to retry with the same key and parameters. That retry is safe only because Stripe's server persists and enforces the key. The [AWS idempotent-API precedent](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) likewise puts the unique caller identifier inside the API contract, atomically records it with the mutation, and rejects same-token/different-parameter reuse. After M3, Cement intentionally does none of those things, so it must not adapt the “safe to retry” half of either claim.

The command/query wording follows [Command Query Separation](https://martinfowler.com/bliki/CommandQuerySeparation.html): a query returns an answer without changing observable state, while a command changes state. For this repository, “read-only” should be stricter than Fowler's observable-state formulation: no SQLite write is authorized at all, including temporary or accidentally committed writes.

[AWS's transactional-outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) names the **dual-write problem** and commits business state plus outbox intent in one local transaction. It also warns that the relay can duplicate messages and that order can drift. [Kafka's delivery contract](https://kafka.apache.org/41/design/design/) names the acknowledgement crash window: processing before checkpointing yields duplicate processing, while checkpointing first can lose processing. Those precedents justify “at least once” only as a warning about duplicates, never as an exactly-once promise.

### Failure modes to name, not imply

- **Indeterminate or ambiguous outcome:** Cement may commit before the caller loses the response.
- **Duplicate submission / duplicate delivery:** a retry, concurrent worker, or outbox relay may create another proposal.
- **Concurrent deduplication race:** two caller workers can both observe “not submitted” unless the caller's check-and-mark is atomic.
- **Idempotency-key mismatch, reuse, or collision:** one caller-owned ID must not bind different immutable content or different scope.
- **Late-arriving retry:** an old attempt can arrive after a newer operation revision or superseding intent.
- **Dual-write inconsistency / lost intent:** the caller's business write can commit while submission does not, or submission can commit while the caller rolls back.
- **Out-of-order delivery:** asynchronous retries can reverse intended submission order.
- **Duplicate effect execution:** applying a resolved plan twice can repeat external effects even though resolution is deterministic.
- **Stale observation / time-of-check-to-time-of-use:** a resolve snapshot does not freeze later ledger, policy, authorization, or external state.

The sharp caveat is important: a transactional outbox alone cannot restore exactly-once Cement submission. It closes the **lost-intent** half of the dual write, but a crash after Cement commits and before the relay records success still causes a repeat. Exactly-once creation would require a recipient-side deduplication key or a shared atomic transaction—the very service-side lifecycle M3 removes.

## Q3 — Pre-1.0 schema break without migration

**Recommendation.** The current technical gate is sufficient to prevent an old ledger from being misread or rewritten, but a version bump alone is not sufficient release communication. For M3: bump the distribution from `0.1.x` to `0.2.0`, bump `SCHEMA_VERSION` from 2 to 3, regenerate the fingerprint, preserve the exact-schema comparison, refuse the old file before persistent changes, and publish an explicit archive-and-rebuild procedure. Do not add a partial or best-effort migration.

### What the repository already does correctly

`src/cement_runtime/store.py` uses all three independent identity checks:

1. `PRAGMA user_version` must be 0 for a genuinely empty database or equal `SCHEMA_VERSION`.
2. `schema_metadata['schema-vN']` must equal the SHA-256 fingerprint of the runtime's schema text.
3. Every live non-internal table, index, and trigger definition must equal the schema constructed in memory.

The version check runs before schema creation. A mismatch raises `IntegrityError`; `cli.py` emits the stable `integrity` object on stderr and returns 5. Initialization changes `journal_mode` only after identity and integrity validation. The probe below additionally found the rejected ledger byte-identical before and after the fresh CLI process.

### Exact probe transcript

Probe script actually run: `/tmp/res-m3-q3-probe.sh`.

```text
$ bash /tmp/res-m3-q3-probe.sh
$ PYTHONPATH=/home/eturkes/Projects/cement/src UV_CACHE_DIR=/tmp/res-m3-q3-uv-cache uv run --no-project python -m cement_runtime --db /tmp/res-m3-q3-ledger.db --partition probe operation list
stdout:
[]
stderr:
exit_code=0
$ UV_CACHE_DIR=/tmp/res-m3-q3-uv-cache uv run --no-project python -c <set-PRAGMA-user_version-to-1> /tmp/res-m3-q3-ledger.db
user_version=1
$ PYTHONPATH=/home/eturkes/Projects/cement/src UV_CACHE_DIR=/tmp/res-m3-q3-uv-cache uv run --no-project python -m cement_runtime --db /tmp/res-m3-q3-ledger.db --partition probe operation list
stdout:
stderr:
{
  "error": "integrity",
  "message": "database schema 1 is unsupported; expected 2"
}
exit_code=5
before_sha256=c72600fa1a61bfe022bcac26c5e0e76a99b30e2eb3f387aca100cab87dbe0dbe
after_sha256=c72600fa1a61bfe022bcac26c5e0e76a99b30e2eb3f387aca100cab87dbe0dbe
ledger_byte_identical=yes
user_version_after=1
schema_metadata_rows_after=1
```

**Exact observed diagnostic:** `database schema 1 is unsupported; expected 2` inside `{"error": "integrity", ...}` on stderr. **Exact observed exit code:** 5. The second construction did not rewrite the version, metadata, or any database byte.

### Release and recovery additions

- **Version:** [SemVer permits any change in `0.y.z`](https://semver.org/spec/v2.0.0.html), but that permission does not make a silent data-format break honest. Use the established pre-1.0 convention: patch for compatible fixes, minor for breaking interfaces or storage. M3 therefore merits `0.2.0`, not another `0.1.x` patch.
- **Changelog:** Add a versioned `0.2.0` entry. Under the current [Keep a Changelog convention](https://keepachangelog.com/en/2.0.0/), put API removals under `Removed` and the ledger-format change under `Changed`, prefixing each with `Breaking:`. Name removed request IDs, leases, statuses, retry flags, the authority callback, and bundled command runtime. State that schema 2 has no in-place migration.
- **Error:** Keep the old and expected schema numbers. Add an actionable sentence such as: `database schema 2 is unsupported; expected 3; this release cannot migrate the ledger in place—archive it and initialize a new database`. A documentation URL may follow, but the local message must remain useful offline.
- **Recovery:** Document **archive and rebuild**, not a bare destructive `rm`: stop writers; copy or move the old database and any sidecars; use the old `0.1.x` runtime to export required bundles or records; initialize a new path with `0.2.0`; re-register operations; explicitly resubmit and review the evidence that must survive. State which audit/history state cannot be imported. Never tell users to edit `PRAGMA user_version` or the fingerprint.
- **Refusal pin:** Retain a real or faithful schema-2 fixture with a sentinel row. A fresh `System` and one CLI leaf must reject it before mutation; pin library `IntegrityError`, CLI exit 5, exact stderr, sentinel preservation, `PRAGMA user_version == 2`, and a full dump or byte digest before/after. Also retain the same-version/wrong-fingerprint test, because a manually changed version must not bypass the break.

SQLite explicitly reserves [`PRAGMA user_version`](https://sqlite.org/pragma.html) for application-defined use and does not interpret it. Therefore, Cement—not SQLite—must couple the version, fingerprint, executable schema, package release, and recovery instructions. The existing coupling is technically strong; M3 mainly needs the release-facing half.

## Q4 — Provably non-mutating SQLite reads

**Recommendation for `resolve`.** Add a dedicated read connector, not another `Store.transaction(write=False)` branch. It must open an **existing** ledger with a `file:` URI plus `mode=ro`, set `PRAGMA query_only = ON`, then install an authorizer that denies all row writes, DDL, write-capable PRAGMAs, `ATTACH`, and `DETACH`. Start one explicit deferred transaction, perform all resolution reads, and always roll back and close. Do not use `immutable=1` on the live ledger. Do not pass this path through the current create-if-absent `Store.__init__`; `mode=ro` correctly makes a missing ledger an error without creating a file.

This is defense in depth with distinct jobs:

- `mode=ro` is SQLite/VFS enforcement for the main ledger even if a Python guard is removed.
- `query_only` cheaply rejects broad accidental SQL writes, including TEMP writes in the measured runtime.
- `set_authorizer` rejects writes before execution with `SQLITE_AUTH` and closes the `ATTACH` hole.
- `BEGIN` gives all reads one snapshot; it supplies consistency, **not** read-only enforcement.

### Mechanism matrix

| mechanism | what it actually prevents | what it does **not** prevent | cost | hard-pin status |
|---|---|---|---|---|
| `PRAGMA query_only = ON` | The measured connection rejected `UPDATE`, `CREATE TEMP TABLE`, and DDL in an attached database with `SQLITE_READONLY`. SQLite documents rejection of `CREATE`, `DELETE`, `DROP`, `INSERT`, and `UPDATE`. | It is a toggle, not a read-only open mode. The same connection turned it off and committed an update. `ATTACH` itself succeeded and created a zero-byte file. SQLite also documents that checkpoint and `COMMIT` remain possible. It cannot stop Python or user-defined-function side effects. | One connection-local pragma; negligible steady-state cost. | **Yes, as a guard pin:** assert `PRAGMA query_only == 1` and an injected write returns `SQLITE_READONLY`. **No, as the sole capability boundary:** code holding the connection can turn it off. |
| `Connection.set_authorizer` | A callback can deny row writes, DDL, virtual-table DDL, `ANALYZE`, `REINDEX`, PRAGMAs, `ATTACH`, and `DETACH`. The 27-action deny set in the probe rejected main/TEMP writes and attach with `SQLITE_AUTH`. Installing it also re-authorized a previously cached update in this runtime. | The callback can be replaced or disabled. An incomplete action list leaves holes. It does not stop non-SQL Python I/O, side effects inside an already-registered function, or writes by another connection. Install it before resolver SQL; do not rely on the measured statement-cache behavior as a portability guarantee. | One Python callback during statement preparation/access authorization, plus a maintained deny list. It is not called per result row. | **Yes:** inject one forbidden statement through the real resolver connection and require `DatabaseError.sqlite_errorname == "SQLITE_AUTH"`. Spy or wrap callback installation so deleting it fails the test. |
| `file:...?mode=ro`, `uri=True` | SQLite opens the named main database read-only. The probe rejected updates even after `query_only` was off. It refused a missing path with `SQLITE_CANTOPEN` and created no file. Normal locking and change detection remain active for a live database. | It did not block `CREATE TEMP TABLE`, `ATTACH`, or an update to the separately attached database. It does not stop other processes from changing the main ledger, non-SQL side effects, or changing snapshots between statements outside a transaction. | A dedicated connection/file descriptor and safe URI construction (`Path.resolve().as_uri()`). No migration or initialization through this connector. | **Yes:** inspect the actual `sqlite3.connect` URI/flags and, with the authorizer disabled in a focused subcase, require a main-ledger write to fail with `SQLITE_READONLY`. |
| `immutable=1` URI | It implies read-only and rejected an update in the probe. It skips locking and file-change detection. | It is an assertion that **all other actors** cannot change the file. The probe's open immutable connection kept returning `seed` after an ordinary connection committed `external-change`. SQLite warns of wrong answers or `SQLITE_CORRUPT` if the file changes. It is unsuitable for Cement's live ledger. | Less locking/change-detection overhead, bought by abandoning live-change safety. | Main-file write rejection is pinnable, but the immutability premise is operational and cannot be established by a unit test. **Reject for `resolve`.** Reserve it for a sealed filesystem snapshot only. |
| Separate connection | A separate connector can make the read capability structurally distinct and can avoid exposing Cement's normal read-write connection to resolution code. Combined with `mode=ro`, it cannot initialize a missing ledger. | Separation alone enforces nothing: the probe's ordinary “read” connection committed an update. It also does not create a stable snapshot unless one transaction spans all reads. | Connection setup, schema validation, and one extra descriptor per call or pooled reader. SQLite connections are local; keep ownership explicit because stdlib connections default to same-thread use. | **Yes, structurally:** pin that the public resolve path calls only the dedicated connector and never `_connect`/`transaction(write=True)`. It becomes a hard write barrier only when opened `mode=ro`. |
| `BEGIN` / `DEFERRED`, `isolation_level`, and `autocommit` | They choose transaction start and commit timing. An explicit read transaction is useful for one-snapshot resolution. | None is a read-only control. The measured plain `BEGIN` upgraded, updated, and committed. `isolation_level=None` auto-committed an update. Legacy deferred mode committed one. On Python 3.13, both `autocommit=True` and `autocommit=False` permitted persisted writes. Python 3.11 has no `Connection.autocommit` API. | No special barrier cost. A long read snapshot can retain old pages or delay maintenance, so keep one resolve call bounded. | **Not a hard read-only pin.** Pin `connection.in_transaction` across all resolver reads separately to prove snapshot lifetime; use the other mechanisms to prohibit writes. |

The behavior above agrees with the [Python `sqlite3` documentation](https://docs.python.org/3/library/sqlite3.html), SQLite's [`query_only` documentation](https://www.sqlite.org/pragma.html#pragma_query_only), and the SQLite [URI filename contract](https://www.sqlite.org/uri.html). `Connection.autocommit` arrived in Python 3.12, so Cement's Python 3.11 floor rules it out as a portable mechanism even if it were protective—which it is not.

### Exact probe transcript

Probe script actually run: `/tmp/res-m3-q4-probe.py`.

```text
$ rm -rf /tmp/res-m3-q4-uv-cache && UV_CACHE_DIR=/tmp/res-m3-q4-uv-cache uv run --no-project python /tmp/res-m3-q4-probe.py
python=3.13.14
sqlite=3.53.1
authorizer_write_action_count=27
[deferred-BEGIN]
in_transaction_after_BEGIN=True
value_after_commit=begin-upgraded
[legacy-transaction-settings]
isolation_none_in_transaction=False
isolation_none_persisted=isolation-none
default_isolation_level=''
legacy_after_update_in_transaction=True
legacy_commit_persisted=legacy-deferred
autocommit_true_persisted=autocommit-true
autocommit_false_commit_persisted=autocommit-false
[query-only]
pragma_value=1
select_value=seed
update=OperationalError|SQLITE_READONLY|attempt to write a readonly database
create_temp=OperationalError|SQLITE_READONLY|attempt to write a readonly database
attach_new=ALLOWED
attach_new_file_exists=True
attach_new_file_bytes=0
create_in_attached=OperationalError|SQLITE_READONLY|attempt to write a readonly database
value_after_disable=query-only-disabled
[authorizer]
select_value=seed
update=DatabaseError|SQLITE_AUTH|not authorized
create_temp=DatabaseError|SQLITE_AUTH|not authorized
attach=DatabaseError|SQLITE_AUTH|not authorized
value_after_disable=authorizer-disabled
cached_update_after_install=DatabaseError|SQLITE_AUTH|not authorized
[mode-ro]
pragma_query_only_initial=0
select_value=seed
update=OperationalError|SQLITE_READONLY|attempt to write a readonly database
update_after_query_only_off=OperationalError|SQLITE_READONLY|attempt to write a readonly database
create_temp=ALLOWED
attach_existing=ALLOWED
update_attached=ALLOWED
attached_value_after=aux-changed
open_missing=OperationalError|SQLITE_CANTOPEN|unable to open database file
missing_created=False
[immutable]
first_read=seed
update=OperationalError|SQLITE_READONLY|attempt to write a readonly database
second_read_same_immutable_connection=seed
ordinary_connection_reads=external-change
[separate-connection-alone]
normal_separate_connection_persisted=separate-normal-writes
[recommended-combination]
query_only_before_authorizer=1
select_value=seed
injected_update=DatabaseError|SQLITE_AUTH|not authorized
injected_attach=DatabaseError|SQLITE_AUTH|not authorized
vfs_backstop_update=OperationalError|SQLITE_READONLY|attempt to write a readonly database
database_sha256_before=f3939dacc035b869ddc23d05913868e265f2084d77e1bb1a6d4af23c53e12a07
database_sha256_after=f3939dacc035b869ddc23d05913868e265f2084d77e1bb1a6d4af23c53e12a07
database_byte_identical=True
database_dump_identical=True
combined_attach_created=False
```

Every requested mechanism was executed. The Python-3.11 absence of `Connection.autocommit` is sourced from the stdlib documentation rather than locally executed; the probe interpreter was Python 3.13.14.

### One hard-pin test recommendation

Write one adversarial public-API test around a seeded real Cement ledger. Wrap the dedicated connector and assert that it receives an existing-only `file:` URI containing `mode=ro` with `uri=True`. Replace the inner resolver helper with one that first attempts an `UPDATE`, then an `ATTACH`: both must fail with `SQLITE_AUTH`, and the attach target must stay absent. In a focused subcase, replace the authorizer with `SQLITE_OK`; the same main-table update must still fail with `SQLITE_READONLY`, proving the VFS backstop rather than merely observing unchanged rows. Assert `connection.in_transaction` during the real second read to pin one-snapshot lifetime. Finally compare the full `iterdump()` and file digest before/after, and call the public resolve path on an absent path to prove that it creates no file.

The exact error codes plus connector-call assertion are the hard structural pins. The dump/digest comparison is secondary evidence; unlike a row-count snapshot, it cannot hide a committed `UPDATE`, but by itself it would still only observe behavior.

## Research budget

WebSearch calls: 13 / 30 maximum.
