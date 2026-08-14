# Architecture

## Contract

Cement is a pure decision-plan router plus a local control plane:

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
8. Promotion explicitly repeats the tested scope hash and rechecks every binding in one immediate
   transaction. Its activation receipt binds the artifact, policy, evidence, report outcome, and exact
   test-set digest. Only then can runtime dispatch use the artifact.

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
it suspends every non-retired dependent build. Artifact suspension and retirement are terminal, so
Cement cannot replay a historical promotion receipt. Audit events are append-only projections.

## Stability and verification claims

A scope is recurring when it has enough distinct, idempotent confirmations. It is stable when those
confirmations span the configured observation interval without conflicting final outputs. It is
verifiable when the exact finite match set replays against all active fixtures and fixed boundary
tests.

These are operational gates, not proof that supervisors were correct. Exact matching makes the coverage
claim honest: the artifact's match set contains one canonical value. Broader predicates require a future
domain contract with schemas, a trusted oracle/properties, exhaustive finite coverage, or formal proof.

## Storage and transactions

SQLite uses foreign keys, STRICT tables, rollback journaling, `synchronous=EXTRA`, a busy timeout,
defensive connection configuration when available, and explicit `BEGIN IMMEDIATE` write transitions.
Candidate generation holds no lock. A lease permits recovery after a crashed generator; a stale
generator cannot overwrite a proposal claimed by another lease owner.

Initialization adopts only a schema-empty SQLite database. It creates the schema atomically and runs
SQLite integrity and foreign-key checks. It then validates the database metadata fingerprint plus
the live tables, indexes, and triggers. Unrecognized non-empty databases reject without journal/schema
mutation. Evidence edges,
receipts, verification reports/tests, revocations, and events are database-immutable. Evidence replay
and test recording stream rows in bounded batches. Monotonic sequences provide a proposal transition
feed, an immutable verification-report feed, and insertion catalogs for examples/artifacts even if the
wall clock rolls backward. The append-only event feed carries later revocation and artifact lifecycle
changes. Consumers refetch named records or rescan the affected operation catalog. Promotion performs
the full verification-child-set hash. Runtime dispatch checks the sealed report and promotion receipt
without re-hashing test rows. It still scans active scope evidence for late conflicts and revocations,
so its safety-check cost grows with the artifact's support. Report inspection can re-hash the
child set.

The database file is the integrity and confidentiality trust root in this release. Cement
content-addresses artifact content, policies, receipts, snapshots, scopes, and builds, so accidental
mutation fails closed. No external signature protects against an attacker who can rewrite the ledger.

## Tooling decision

The runtime uses Python 3.11+ and the standard-library `sqlite3`, JSON, subprocess, typing, and unittest
modules. This exact-lookup envelope needs no expression engine or provider SDK. A generalized
language would enlarge the trusted computing base without expanding the honestly tested scope.
[Python's SQLite interface](https://docs.python.org/3/library/sqlite3.html) supplies the embedded
serverless store; startup checks the distributor SQLite for STRICT-table support.

Packaging uses the pure-Python [`uv_build` backend](https://docs.astral.sh/uv/concepts/build-backend/).
The backend validates the `src/` layout, and `pyproject.toml` bounds its version. There are zero runtime
package dependencies. SQLite's own documentation motivates
[STRICT tables](https://www.sqlite.org/stricttables.html) and the rollback-journal
[`synchronous=EXTRA` durability mode](https://www.sqlite.org/pragma.html#pragma_synchronous).

The project evaluated Go plus CEL for future generalized artifacts. CEL offers a constrained
expression runtime, and Go offers a single binary. It is unnecessary for a finite equality/return
interpreter and would add a SQLite driver, CEL runtime, and module supply chain. Revisit that choice
only with a concrete, independently verifiable wider-scope requirement.
