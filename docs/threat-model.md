# Threat model

## Trusted

- The host, Python/SQLite runtime, database file permissions, Cement interpreter, and the deployment's
  external access control. Cement enforces no permission of its own.
- Supervisors and release managers only within the context represented by their partition. The CLI
  records identity strings but does not authenticate them.
- The provider adapter process as a credential-bearing transport. Its model output remains untrusted.
- For offline evaluation, the host runtime and the channel that delivers an independently held function
  hash. That path opens no database and starts no adapter.

## Untrusted

- Request JSON, including prompt injection.
- LLM candidate output and self-reported provenance.
- Stored input/output content when rendered by another system.
- Frequency by itself, reviewer labels without deployment authentication, and any inferred scope.
- Exported bundle files, including the hash embedded in them. The parser validates every bundle as
  untrusted input. Only an independently obtained expected hash pins identity.

## Enforced controls

- Strict bounded JSON; duplicate keys, decimal/non-finite numbers, non-string keys, deep/large
  containers, and signed-64-bit overflow fail closed. Decimal quantities use application-defined
  strings. Cement preserves Unicode without case folding or normalization.
- Partition, operation revision, and byte-stable canonical equality control scope. Unknown or
  near-match input falls back. Offline function evaluation has no fallback path: an unknown input
  returns an inert miss.
- Artifacts and function bundles are inert data: no code, templates, loops, filesystem, process,
  network, environment, clock, randomness, or external effects.
- The `cement-function-v2` format is bounded at 64 MiB, 50,000 entries, one million items, and depth
  67. Per-value limits of 1 MiB, 100,000 items, and depth 64 also apply. The bundle reader accepts one
  strict UTF-8 regular file and enforces the 64 MiB bound independently from the 1 MiB bound on the
  evaluation input.
- Entry order is normalized by input hash, so equal content produces equal bytes and one equal
  `function_hash`. The embedded hash proves normalized self-consistency only. An independently obtained
  expected hash additionally pins caller-held identity. The hash is unkeyed, so neither mode proves
  origin or acts as a signature. An expected hash copied from the same untrusted bundle adds no trust.
- A live export emits bundle bytes only after all six set checks pass. A drifted set produces no bytes
  and reports the complete failed check vector on stderr. A historical export emits bytes only after
  full receipt reconstruction.
- `function export --out` writes atomically through a mode-0600 temporary file and refuses a
  non-regular destination. The destination is old or new, never partial, if no other process mutates
  it. The write performs no directory fsync, and a final target race remains possible.
- Function receipt and membership rows are database-immutable. Historical receipt reconstruction
  survives member supersession, operation-revision retirement, and evidence revocation. An audit of a
  past promotion therefore does not depend on current artifact status.
- Candidate commands bypass the shell, have timeout/output limits, and run outside database locks. On
  Linux, a child-subreaper kills and reaps detached descendants before accepting output. That
  mechanism is lifecycle containment for the trusted adapter, not a hostile-code sandbox. The outer
  watchdog covers unexpected supervisor exit for the shared process group. A cgroup/container is
  necessary to contain detached descendants across simultaneous supervisor/watchdog failure or OOM.
- Proposed output is visible only through the review API. Accepted output can differ, and the final
  edited value is the fixture.
- Evidence conflicts block compilation. Evidence snapshots and policy/artifact digests block stale
  verification and promotion. Whole-set verification adds six ordered checks, and set promotion repeats
  one prospective function hash under a write lock. The sixth check requires the latest persisted
  receipt to bind the live promoted snapshot. Individually valid artifacts therefore cannot pass as a
  set without a current checkpoint.
- Counterexample, revocation, ambiguity, and integrity failure quarantine builds.

## Deployment obligations

- Authenticate and authorize every control-plane call. That list covers operation registration and
  revision, proposal review, compilation, verification, promotion, challenge, revocation, and
  suspension. It also covers database access and audit access.
- Make every permission decision in your own service. Cement records the actor name that you supply.
- Put every mutable answer dependency into the input, including identity, permissions, locale, policy
  revision, and external-state revision. Exclude behavior with hidden context from compilation.
- Minimize, redact, encrypt, expire, and back up evidence according to its data classification. The
  ledger is plaintext and a blind copy of a live SQLite database is unsafe. An exported bundle is
  plaintext too. It carries the exact inputs, the exact outputs, and the governance digests, so it
  creates a second data-classification, retention, and disclosure surface outside the ledger.
- An exported bundle is intentionally sealed from later ledger state. If a revocation, a policy
  revision, or an evidence change must take effect, deploy a newly verified export.
- Treat results as plans. Re-run live policy and authorization immediately before an effect. Use the
  `handle` request ID as an idempotency key. Stop for reconciliation after uncertain effect commit
  state. `submit_proposal` and `propose` give no idempotency. Each call writes a new proposal. Do not
  repeat those calls to recover. A `StateError` from either call does not prove that the proposal is
  absent, because a database commit can succeed and then fail. List the partition's pending proposals
  and match your input before you act. The `cement proposal submit` command inherits every sentence
  above, because it calls `submit_proposal` directly.
- Pass `cement proposal submit --submission -` for a candidate that must stay private. An inline
  value enters the argument list of the process. Cement cannot control who reads that list. On Linux
  the value appears in `/proc/<pid>/cmdline`, and other hosts expose equivalent process listings.
  Access depends on the host identity model and the local policy, so treat the value as visible to
  any observer on the same host. An interactive shell can also record the value in its history file.
  Cement controls neither mechanism. The same applies to `cement resolve --input`.
- Keep provider wrappers pure. Model calls can repeat after timeout or lease recovery.
- Monitor promoted scopes. When policy or expected behavior changes, challenge them. Revise the
  operation instead of overwriting contradictory history.
- Deploy command adapters on Linux. If crash-resilient process-tree containment is required, add an
  external cgroup/job/container boundary on every platform.
- If the database-file trust root is insufficient, protect or sign exported artifacts. Cement supplies
  an embedded self-hash and an optional caller-held expected hash. Neither establishes origin, so an
  external signature or a protected channel remains a deployment responsibility.

## Deliberately absent

This local release excludes:

- Remote API and authentication.
- Encryption and key erasure.
- External signatures. A `function_hash` binds content integrity only.
- Arbitrary code sandboxing.
- Generalized-rule synthesis.
- Domain schemas and oracles.
- Active shadow sampling.
- Quotas across principals.
- Distributed consensus.

Both exact formats, `cement-exact-lookup-v1` and `cement-function-v2`, leave those gaps visible. They
do not imply that Cement solves them.
