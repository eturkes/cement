# Threat model

## Trusted

- The host, Python/SQLite runtime, database file permissions, Cement interpreter, and deployment's
  authority callback or external access control.
- Supervisors and release managers only within the authority and context represented by their
  partition. The CLI records identity strings but does not authenticate them.
- The provider adapter process as a credential-bearing transport. Its model output remains untrusted.

## Untrusted

- Request JSON, including prompt injection.
- LLM candidate output and self-reported provenance.
- Stored input/output content when rendered by another system.
- Frequency by itself, reviewer labels without deployment authentication, and any inferred scope.

## Enforced controls

- Strict bounded JSON; duplicate keys, decimal/non-finite numbers, non-string keys, deep/large
  containers, and signed-64-bit overflow fail closed. Decimal quantities use application-defined
  strings. Cement preserves Unicode without case folding or normalization.
- Partition, operation revision, and byte-stable canonical equality control scope. Unknown or
  near-match input falls back.
- Artifacts are inert data: no code, templates, loops, filesystem, process, network, environment,
  clock, randomness, or external effects.
- Candidate commands bypass the shell, have timeout/output limits, and run outside database locks. On
  Linux, a child-subreaper kills and reaps detached descendants before accepting output. That
  mechanism is lifecycle containment for the trusted adapter, not a hostile-code sandbox. The outer
  watchdog covers unexpected supervisor exit for the shared process group. A cgroup/container is
  necessary to contain detached descendants across simultaneous supervisor/watchdog failure or OOM.
- Proposed output is visible only through the review API. Accepted output can differ, and the final
  edited value is the fixture.
- Evidence conflicts block compilation. Evidence snapshots and policy/artifact digests block stale
  verification and promotion.
- Counterexample, revocation, ambiguity, and integrity failure quarantine builds.

## Deployment obligations

- Authenticate and authorize proposal review, operation revision, promotion, challenge, revocation,
  suspension, database access, and audit access.
- Put every mutable answer dependency into the input, including identity, permissions, locale, policy
  revision, and external-state revision. Exclude behavior with hidden context from compilation.
- Minimize, redact, encrypt, expire, and back up evidence according to its data classification. The
  ledger is plaintext and a blind copy of a live SQLite database is unsafe.
- Treat results as plans. Re-run live policy and authorization immediately before an effect. Use the
  request ID as an idempotency key. Stop for reconciliation after uncertain effect commit state.
- Keep provider wrappers pure. Model calls can repeat after timeout or lease recovery.
- Monitor promoted scopes. When policy or expected behavior changes, challenge them. Revise the
  operation instead of overwriting contradictory history.
- Deploy command adapters on Linux. If crash-resilient process-tree containment is required, add an
  external cgroup/job/container boundary on every platform.
- If the database-file trust root is insufficient, protect or sign exported artifacts.

## Deliberately absent

This local release excludes:

- Remote API and authentication.
- Encryption and key erasure.
- External signatures.
- Arbitrary code sandboxing.
- Generalized-rule synthesis.
- Domain schemas and oracles.
- Active shadow sampling.
- Quotas across principals.
- Distributed consensus.

The exact artifact format leaves those gaps visible. It does not imply that Cement solves them.
