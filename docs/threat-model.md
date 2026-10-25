# Threat model

## Trusted

- The host, Python/SQLite runtime, database file permissions, Cement interpreter, and the deployment's
  external access control. Cement enforces no permission of its own.
- The operator who runs the learning pass and the person who sets the switch, each only within the
  context represented by their partition. The CLI records identity strings but does not authenticate
  them.
- The provider adapter process as a credential-bearing transport. Its model output remains untrusted.
- For offline evaluation, the host runtime, the channel that delivers an independently held function
  hash, and the allowed signers file that `function eval --signature` checks a bundle signature
  against. That path opens no database and starts no adapter. A child-process audit hook proves this
  for `function eval`, and `python -S` does not remove it (README `Deployment boundary`).

## Untrusted

- Request JSON, including prompt injection.
- LLM candidate output and self-reported provenance. A retained answer is evidence for the learning
  pass, never an instruction: a chat integration can deliver fabricated tool calls (the Open WebUI
  example states how). In the nucllei example, the chat model itself writes each retained answer and
  runs the switch command when the user asks. The sandbox cannot tell who asked, so there a model
  that ignores its skills can switch a function on (the example README states this limit).
- The learning pass's judgment. It is an LLM run: its reviews, merges, and projection programs can be
  wrong. Cement verifies a program's grammar and consistency, never its semantic correctness. The
  switch keeps a person's decision between learned versions and production: it starts `off`, `follow`
  is a standing choice to serve each new version, and `pinned` keeps one version.
- Stored input/output content when rendered by another system.
- Frequency by itself, reviewer labels without deployment authentication, and any inferred scope.
- Exported bundle files, including the hash embedded in them, and their signature files. The parser
  validates every bundle and every signature as untrusted input. Only an independently obtained
  expected hash pins identity, and only a verified signature proves the publisher.

## Enforced controls

- Strict bounded JSON; duplicate keys, decimal/non-finite numbers, non-string keys, deep/large
  containers, and signed-64-bit overflow fail closed. Decimal quantities use application-defined
  strings. Cement preserves Unicode without case folding or normalization.
- Partition, operation revision, and byte-stable canonical equality of the case key control scope.
  For unknown or near-match input, `resolve` returns a miss, and the caller gives that input to the
  LLM. Offline function evaluation has no fallback path: an unknown input returns an inert miss.
- A projection program is a closed recognizer, not code: no regular expression runs on input, no
  expression is evaluated, and the work is linear in the input. Both ABIs keep this: v2 only adds
  one character, a full-width colon, to a fixed separator set. A program is stored only after it
  parses, after an active example witnesses every layout, after no key merges different outputs, and
  after at least one example projects. An input that no layout recognizes is a miss.
- A switched-off operation answers nothing. Only `function switch` changes the switch, and every
  change writes one row and one event.
- Artifacts and function bundles are inert data: no code, templates, loops, filesystem, process,
  network, environment, clock, randomness, or external effects.
- The `cement-function-v3` format is bounded at 64 MiB, 50,000 entries, one million items, and depth
  67. Per-value limits of 1 MiB, 100,000 items, and depth 64 also apply. The bundle reader accepts one
  strict UTF-8 regular file and enforces the 64 MiB bound independently from the 1 MiB bound on the
  evaluation input.
- Entry order is normalized by input hash, so equal content produces equal bytes and one equal
  `function_hash`. The embedded hash proves normalized self-consistency only. An independently obtained
  expected hash additionally pins caller-held identity. The hash is unkeyed, so neither mode proves
  origin or acts as a signature. An expected hash copied from the same untrusted bundle adds no trust.
- A bundle signature proves origin. `function eval --signature` checks an `ssh-ed25519` SSHSIG
  signature in the `cement-function-v3` namespace against the allowed signers file before the bundle
  parses, under strict RFC 8032 rules. The allowed signers file takes exact principals and the
  `namespaces` option. Cement refuses patterns, certificate authorities, validity windows, and FIDO
  keys rather than ignore them. A verified result names the principals of the signing key.
- An export follows the switch. Under `follow` it emits bundle bytes only after all seven set checks
  pass; under `pinned` only after the four pinned checks pass; under `off` it emits nothing. A
  drifted set produces no bytes and reports the complete failed check vector on stderr. A historical
  export emits bytes only after full receipt reconstruction.
- `function export --out` writes atomically through a mode-0600 temporary file and refuses a
  non-regular destination. The destination is old or new, never partial, if no other process mutates
  it. After the rename, the write flushes the destination's directory, so a completed export survives a
  power loss. If that flush fails, the command reports a failure while the destination already holds
  the new bundle. A final target race remains possible.
- Function receipt and membership rows are database-immutable. Historical receipt reconstruction
  survives member supersession, operation-revision retirement, and evidence revocation. An audit of a
  past promotion therefore does not depend on current artifact status.
- The optional command candidate source (`examples/command_source/`) bypasses the shell, applies
  timeout/output limits, and runs outside database locks. On Linux, its child-subreaper kills and
  reaps detached descendants before accepting output. That
  mechanism is lifecycle containment for the trusted adapter, not a hostile-code sandbox. The outer
  watchdog covers unexpected supervisor exit for the shared process group. A cgroup/container is
  necessary to contain detached descendants across simultaneous supervisor/watchdog failure or OOM.
- Proposed output is visible only through the review API. Accepted output can differ, and the final
  edited value is the fixture.
- Evidence conflicts block compilation. Evidence snapshots and policy/artifact digests block stale
  verification and promotion. Whole-set verification adds seven ordered checks, and set promotion repeats
  one prospective function hash under a write lock. The sixth check requires the latest persisted
  receipt to bind the live promoted snapshot. Individually valid artifacts therefore cannot pass as a
  set without a current checkpoint. The seventh check requires one program across the set.
- A contradicting confirmation fails live verification until a promotion replaces the member, or
  until the contradicting example is revoked or superseded. A
  challenge suspends the member it contradicts, a revocation suspends every dependent build, and an
  integrity failure fails closed. A pinned version stops answering when one of its members is
  challenged, revoked, or suspended.

## Deployment obligations

- Authenticate and authorize every control-plane call. That list covers operation registration and
  revision, proposal review, projection setting, compilation, verification, promotion, the switch,
  challenge, supersession, revocation, and suspension. It also covers database access and audit access.
- Read a learned version before you switch it on. Pin a version to stop a later learning pass from
  changing what production serves.
- Make every permission decision in your own service. Cement records the actor name that you supply.
- Put every mutable answer dependency into the input, including identity, permissions, locale, policy
  revision, and external-state revision. Exclude behavior with hidden context from compilation.
- Minimize, redact, encrypt, expire, and back up evidence according to its data classification. The
  ledger is plaintext and a blind copy of a live SQLite database is unsafe. An exported bundle is
  plaintext too. It carries the exact inputs, the exact outputs, and the governance digests, so it
  creates a second data-classification, retention, and disclosure surface outside the ledger.
- An exported bundle is intentionally sealed from later ledger state. If a revocation, a policy
  revision, or an evidence change must take effect, deploy a newly verified export.
- Treat results as plans. Re-run live policy and authorization immediately before an effect. Cement
  supplies no idempotency key, so supply one from your application and bind it to the exact input you
  act on. Stop for reconciliation after uncertain effect commit
  state. `propose` gives no idempotency, and `submit_proposal` gives none without a source id.
  `propose` invokes the configured source one time for each call, and it never retries. Each call
  without a source id writes a new proposal. Do not repeat those calls to recover. A `StateError` from either call does not prove that the proposal is
  absent, because a database commit can succeed and then fail. List the partition's pending proposals
  and match your input before you act. The `cement proposal submit` command inherits every sentence
  above, because it calls `submit_proposal` directly.
- Pass `cement proposal submit --submission -` for a candidate that must stay private. An inline
  value enters the argument list of the process. Cement cannot control who reads that list. On Linux
  the value appears in `/proc/<pid>/cmdline`, and other hosts expose equivalent process listings.
  Access depends on the host identity model and the local policy, so treat the value as visible to
  any observer on the same host. An interactive shell can also record the value in its history file.
  Cement controls neither mechanism. The same applies to `cement resolve --input`.
- Keep provider wrappers pure. A model call can repeat after a timeout.
- Monitor promoted scopes. When policy or expected behavior changes, challenge them. Revise the
  operation instead of overwriting contradictory history.
- Deploy command adapters on Linux. If crash-resilient process-tree containment is required, add an
  external cgroup/job/container boundary on every platform.
- Sign each exported bundle that leaves the database host. The person who switched the version on
  signs it with their own SSH key (`ssh-keygen -Y sign -n cement-function-v3`). Keep each private key
  and each allowed signers file where the bundle's consumers and its channel cannot change them.
  Cement verifies signatures and never holds a private key.

## Deliberately absent

This local release excludes:

- Remote API and authentication.
- Encryption and key erasure.
- Arbitrary code sandboxing.
- Generalized-rule synthesis. A projection maps inputs to exact keys; it never synthesizes a rule.
- Domain schemas and oracles.
- Active shadow sampling.
- Quotas across principals.
- Distributed consensus.

The exact formats, `cement-exact-lookup-v1` and `cement-function-v3`, leave those gaps visible. They
do not imply that Cement solves them.
