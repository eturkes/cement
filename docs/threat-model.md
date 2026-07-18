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
  strings. Unicode is preserved without case folding or normalization.
- Partition + operation revision + byte-stable canonical equality controls scope. Unknown or near-match
  input falls back.
- Artifacts are inert data: no code, templates, loops, filesystem, process, network, environment,
  clock, randomness, or external effects.
- Candidate commands bypass the shell, have timeout/output limits, and run outside database locks. On
  Linux, a child-subreaper kills and reaps detached descendants before accepting output; this is
  lifecycle containment for the trusted adapter, not a hostile-code sandbox. The outer watchdog
  covers unexpected supervisor exit for the shared process group, but a cgroup/container is required
  to contain detached descendants across simultaneous supervisor/watchdog failure or OOM.
- Proposed output is visible only through the review API. Accepted output may differ and the final
  edited value is the fixture.
- Evidence conflicts block compilation. Evidence snapshots and policy/artifact digests block stale
  verification and promotion.
- Counterexample, revocation, ambiguity, and integrity failure quarantine builds.

## Deployment obligations

- Authenticate and authorize proposal review, operation revision, promotion, challenge, revocation,
  suspension, database access, and audit access.
- Put identity, permissions, locale, policy revision, external-state revision, and every other mutable
  answer dependency into the input. Exclude behavior with hidden context from compilation.
- Minimize, redact, encrypt, expire, and back up evidence according to its data classification. The
  ledger is plaintext and a blind copy of a live SQLite database is unsafe.
- Treat results as plans. Re-run live policy and authorization immediately before an effect; use the
  request ID as an idempotency key. Stop for reconciliation after uncertain effect commit state.
- Keep provider wrappers pure. Model calls may repeat after timeout or lease recovery.
- Monitor promoted scopes. Challenge them when policy or expected behavior changes; revise the
  operation rather than attempting to overwrite contradictory history.
- Deploy command adapters on Linux; add an external cgroup/job/container boundary whenever
  crash-resilient process-tree containment is required, on every platform.
- Protect or sign exported artifacts if the database-file trust root is insufficient.

## Deliberately absent

Remote API/authentication, encryption/key erasure, external signatures, arbitrary code sandboxing,
generalized-rule synthesis, domain schemas/oracles, active shadow sampling, quotas across principals,
and distributed consensus are outside this local release. The exact artifact format leaves those gaps
visible instead of implying they are solved.
