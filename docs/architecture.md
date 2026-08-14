# Architecture

## Contract

Cement is a pure decision-plan router, a local control plane, and a portable function object:

1. Canonicalize bounded JSON with `cement-json-v1`. It uses signed 64-bit integers and string decimal
   quantities, so binary-float rounding cannot widen an exact scope.
2. Resolve only one integrity-valid promoted artifact whose partition, operation revision, and exact
   canonical input all match.
3. Otherwise reserve the idempotent request, call the candidate source outside the SQLite transaction,
   and store a pending proposal.
4. A separate review action accepts, corrects, or rejects the candidate. Accept/correct creates an
   immutable replay fixture; reject remains audit evidence only.
5. A scheduled compiler groups active fixtures by exact scope. It requires the operation's configured
   support, distinct-reviewer, time-span, and zero-conflict gates.
6. The compiler emits `cement-exact-lookup-v1`, a capability-free JSON document with only `exact` and
   `return` operations.
7. Verification binds artifact, policy, runtime/canonicalizer ABI, and the complete evidence snapshot.
   It replays the finite scope and negative boundaries into a sealed, content-addressed test set.
   `verify_drafts` verifies every current-build draft of one operation in one locked write transaction.
   It reports superseded rows as benign skips.
8. Promotion explicitly repeats the tested scope hash and rechecks every binding in one immediate
   transaction. Its activation receipt binds the artifact, policy, evidence, report outcome, and exact
   test-set digest. Only then can runtime dispatch use the artifact.

Steps 9 to 11 aggregate the promoted artifacts of one operation into a single portable object. Check
six binds the persisted receipt. A first nonempty set must therefore complete step 9 before step 10
can pass:

9. `inspect_function_promotion` projects the prospective union of retained members and verified
   candidates. It returns the prospective function hash. `promote_function` repeats that hash under a
   write lock. It then retires predecessors, activates candidates, and writes one immutable receipt
   plus ordered memberships in one transaction. Set promotion retains established entries during
   growth. It also permits a zero-candidate checkpoint over a nonempty retained set.
10. `verify_function` returns six ordered checks over one read snapshot of the complete promoted set:
    `duplicate-input-digests`, `abi-canonicalizer-uniform`, `sealed-passing-reports`,
    `current-promotion-receipts`, `function-hash-matches-snapshot`, and `persisted-function-receipt`.
    The call is read-only and authority-free. A caller can supply an expected function hash. That hash
    detects set growth or drift. An empty promoted set passes vacuously and builds a real empty
    function.
11. The set projects to `cement-function-v2`, a capability-free JSON document. Each entry carries the
    exact canonical input and output plus the artifact, evidence, report, and `entry_seal` governance
    digests. `evaluate` resolves an exported document without a ledger, an adapter, or an LLM.

Entry order is normalized by input hash, so equal content always produces equal bytes and one equal
`function_hash`. The embedded hash proves normalized self-consistency. Only an independently obtained
expected hash binds caller-held identity. Neither mode proves origin or supplies a signature.

Function identity is verified-content identity, not activation identity. `entry_seal` excludes the
promoter and the promotion time, so those values never change the `function_hash`. The
`cement-promotion-v2` receipt and the function receipt retain that activation provenance.

The function format is bounded at 64 MiB, 50,000 entries, one million items, and depth 67. Per-value
limits of 1 MiB, 100,000 items, and depth 64 still apply, so a rich set can fail before 50,000 entries.

The LLM proposes instance behavior. It never chooses scope, confirms examples, runs verification, or
activates artifacts.

## Isolation and revisioning

Scope identity is:

```text
(partition, operation, operation_revision, canonical_input)
```

`partition` is mandatory to prevent accidental cross-tenant/workflow learning. Every explicit
operation revision retires prior builds, including a revision that keeps the same numeric thresholds.
Request IDs are unique within a partition and bind immutable operation and input content. The same ID
in another partition is independent. A revision invalidates every older request path. Cement
withholds cached output and cancels generators. Failed calls cannot retry, and pending proposals
cannot become examples. Callers reconcile prior effects and use a new request ID under the current
revision.

Confirmed receipt data and artifact evidence edges are immutable. Revocation is a separate tombstone;
it suspends every non-retired dependent build. Artifact suspension and retirement are terminal, and no
public surface replays a historical per-artifact promotion receipt.

Historical function receipts behave differently. `reconstruct_function_receipt` returns the exact
promoted document of a past receipt. Reconstruction ignores the current lifecycle status of each
member. It therefore survives member supersession, operation-revision retirement, and revocation of
every member's evidence. `function export --receipt-id` serves a receipt from a superseded operation
revision for the same reason. Reconstruction asserts no current status, and its cost grows with the
member count and the joined reports. A receipt stores the candidate and retired artifact ID sets as
counts and digests only, so reconstruction cannot recover those full transition sets. Audit events are
append-only projections.

## Stability and verification claims

A scope is recurring when it has enough distinct, idempotent confirmations. It is stable when those
confirmations span the configured observation interval without conflicting final outputs. It is
verifiable when the exact finite match set replays against all active fixtures and fixed boundary
tests. Those three definitions apply to one entry. The promoted set adds one more gate. A passing
`verify_function` result binds the complete current snapshot to all six ordered checks. It also binds
that snapshot to the latest current-revision receipt.

Every verification result and every report is one committed read snapshot. It is not a lease, a
signature, a semantic replay, or a statement about future state. The live ledger can later revise,
suspend, revoke, replace, or checkpoint the same scope. Exported bytes stay deterministic because they
leave the ledger.

`function_report` returns the immutable receipt membership and the current operation state in one read
snapshot, and it keeps the two anchors in separate number spaces. Historical member support and
reviewer counts are frozen at build time. Active evidence and policy state remain current, so
complements or ratios across the two anchors are meaningless. The current-state half counts ready and
blocked scopes, pending proposals, artifact statuses, and stale-revision anomalies. `projection_limit`
bounds the returned detail. The report validates only the members it returns; use
`reconstruct_function_receipt` to validate every member.

These are operational gates, not proof that supervisors were correct. Exact matching makes the coverage
claim honest: the artifact's match set contains one canonical value. The function object aggregates
exact entries without widening any entry, so it proves no coverage outside its enumerated inputs.
Broader predicates require a future domain contract with schemas, a trusted oracle/properties,
exhaustive finite coverage, or formal proof.

## Storage and transactions

SQLite uses foreign keys, STRICT tables, rollback journaling, `synchronous=EXTRA`, a busy timeout,
defensive connection configuration when available, and explicit `BEGIN IMMEDIATE` write transitions.
Candidate generation holds no lock. A lease permits recovery after a crashed generator; a stale
generator cannot overwrite a proposal claimed by another lease owner.

Initialization adopts only a schema-empty SQLite database. It creates the schema atomically and runs
SQLite integrity and foreign-key checks. It then validates the database metadata fingerprint plus
the live tables, indexes, and triggers. Unrecognized non-empty databases reject without journal/schema
mutation. Evidence edges, receipts, verification reports/tests, revocations, events, function
receipts, and function memberships are database-immutable. Evidence replay
and test recording stream rows in bounded batches. Monotonic sequences provide a proposal transition
feed, an immutable verification-report feed, and insertion catalogs for examples/artifacts even if the
wall clock rolls backward. The append-only event feed carries later revocation and artifact lifecycle
changes. Consumers refetch named records or rescan the affected operation catalog. Promotion performs
the full verification-child-set hash. Runtime dispatch checks the sealed report and promotion receipt
without re-hashing test rows. It still scans active scope evidence for late conflicts and revocations,
so its safety-check cost grows with the artifact's support. Report inspection can re-hash the
child set.

Schema version 2 adds the function layer: the `function_receipts` and `function_memberships` tables,
three indexes, and five triggers. A receipt is self-bound and stores the candidate and retired ID sets
as counts and digests. A membership row names its receipt, its ordinal, its artifact, and its report.
Triggers reject every update and delete on both tables. A further trigger rejects a membership insert
once the receipt row exists, so promotion must write the whole membership set before its receipt. A
deferred composite foreign key binds each membership to its receipt and to exactly that receipt's
`function_hash`. Initialization rejects a version-1 ledger; this release ships no migration runner.

Set promotion emits one `function.promoted` event with bounded ID projections. The membership table
stays authoritative for the exact member list. `latest_function_receipt` returns the current-revision
receipt, and `function_receipts` pages history across revisions in descending sequence order with an
exclusive cursor. Discovery returns immutable rows and never reconstructs memberships. An unknown
operation and an operation with no receipts both return an empty page, so enumeration proves nothing
about whether the operation exists. Each page is a separate transaction, so a receipt inserted above
the cursor mid-walk is omitted from that traversal.

The database file is the integrity and confidentiality trust root for the ledger. Cement
content-addresses artifact content, policies, receipts, snapshots, scopes, and builds, so accidental
mutation fails closed. No external signature protects against an attacker who can rewrite the ledger.

An exported bundle leaves that trust root. It evaluates with no database, and an independently held
expected function hash binds its identity instead. That hash is unkeyed and proves no origin. An
expected hash copied from the same untrusted bundle adds no trust. Before export, establish ledger
governance with `verify_function` or receipt reconstruction. Then transfer the expected hash over a
channel that the database file does not protect.

## Tooling decision

The runtime uses Python 3.11+ and the standard library alone. It imports no test framework and no
third-party package. Examples of that use are `sqlite3` for the store and `json` for canonical
encoding. Others are `hashlib` for content addressing and `unicodedata` for control-character
validation. The command adapter uses `subprocess` and `signal`. This exact-lookup envelope needs no
expression engine or provider SDK. A generalized language would enlarge the trusted computing base
without expanding the honestly tested scope.
[Python's SQLite interface](https://docs.python.org/3/library/sqlite3.html) supplies the embedded
serverless store; startup checks the distributor SQLite for STRICT-table support.

Packaging uses the pure-Python [`uv_build` backend](https://docs.astral.sh/uv/concepts/build-backend/).
The backend validates the `src/` layout, and `pyproject.toml` bounds its version. There are zero runtime
package dependencies. SQLite's own documentation motivates
[STRICT tables](https://www.sqlite.org/stricttables.html) and the rollback-journal
[`synchronous=EXTRA` durability mode](https://www.sqlite.org/pragma.html#pragma_synchronous).

Go plus CEL is the obvious alternative for future generalized artifacts. CEL offers a constrained
expression runtime, and Go offers a single binary. Both are unnecessary for a finite equality/return
interpreter. They would add a SQLite driver, a CEL runtime, and a module supply chain. Adopt them only
for a concrete, independently verifiable wider-scope requirement.
