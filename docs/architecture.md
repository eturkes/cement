# Architecture

## Contract

Cement is a local control plane and a portable function object. It turns retained LLM answers into
exact deterministic lookups:

1. Canonicalize bounded JSON with `cement-json-v1`. It uses signed 64-bit integers and string decimal
   quantities, so binary-float rounding cannot widen an exact scope.
2. Retain each answer as one pending proposal. `System.submit_proposal` takes the candidate from the
   caller. `System.propose` calls the configured candidate source outside the SQLite transaction. A
   proposal can carry a source id that names the observation it came from. Cement refuses a second
   proposal with the same source id for the same partition and operation.
3. The learning pass reviews each proposal: it accepts, corrects, or rejects the candidate. Accept and
   correct create an immutable example; reject remains audit evidence only. Review returns a
   `ReviewResult`, which names the proposal, the decision, the created example, and the confirmed
   output. It carries no request identifier, and neither does any proposal read or report value.
   The event payload of a proposal or a review action also carries no request identifier. The
   learning pass runs as an operator skill (`skills/cement-learn/`) and records its
   reviews as the reviewer `learning-pass`. Cement authenticates no reviewer name: it records the
   name and counts distinct names toward the policy's reviewer gate, and it decides nothing else
   from it.
4. Later confirmations can change the answer of a case. `supersede_examples` replaces earlier
   examples with a re-merged output, one new example for each old one, so one observation still earns
   one support credit. `revoke_example` withdraws an example that is wrong.
5. An optional projection program maps a raw input to the exact key of its case. The learning pass
   writes it; Cement verifies it before it stores it (see Projection below).
6. A scheduled compiler groups active examples by exact key: the canonical input, or the projected
   key under a program. It requires the operation's support, distinct-reviewer, time-span, and
   zero-conflict gates. The defaults are 2 confirmations, 1 reviewer, and 0 seconds.
7. The compiler emits `cement-exact-lookup-v1`, a capability-free JSON document with only `exact` and
   `return` operations.
8. Verification binds artifact, policy, runtime/canonicalizer ABI, program hash, and the complete
   evidence snapshot. It replays the finite scope and negative boundaries into a sealed,
   content-addressed test set. `verify_drafts` verifies every current-build draft of one operation in
   one locked write transaction. It reports superseded rows as benign skips.
9. `inspect_function_promotion` projects the prospective union of retained members and verified
   candidates and returns the prospective function hash. `promote_function` repeats that hash under a
   write lock. It retires predecessors, activates candidates, and writes one immutable receipt plus
   ordered memberships in one transaction. A receipt is a version of the function.
10. `verify_function` returns seven ordered checks over one read snapshot of the complete promoted set:
    `duplicate-input-digests`, `abi-canonicalizer-uniform`, `sealed-passing-reports`,
    `current-promotion-receipts`, `function-hash-matches-snapshot`, `persisted-function-receipt`, and
    `projection-uniform`. The call is read-only. A caller can supply an expected function hash. That
    hash detects set growth or drift. An empty promoted set passes vacuously and builds a real empty
    function.
11. The set projects to `cement-function-v3`, a capability-free JSON document. Each entry carries the
    exact key and output plus the artifact, evidence, report, and `entry_seal` governance digests. The
    document also carries the projection program and its hash, or `null` for exact mode. `evaluate`
    applies the program, then looks the key up, without a ledger, an adapter, or an LLM. A
    `cement-function-v2` document still parses and evaluates.
12. A person switches the function of each operation `off`, to `follow` the newest version, or
    `pinned` to one version. A new operation starts `off`. `resolve` and `function export` serve the
    version that the switch selects. This switch is the only human gate.

Steps 9 and 10 depend on each other: check six binds the persisted receipt, so a first nonempty set
must complete step 9 before step 10 can pass.

Entry order is normalized by key hash, so equal content always produces equal bytes and one equal
`function_hash`. The embedded hash proves normalized self-consistency. Only an independently obtained
expected hash binds caller-held identity. Neither mode proves origin or supplies a signature.

Function identity is verified-content identity, not activation identity. `entry_seal` excludes the
promoter and the promotion time, so those values never change the `function_hash`. The
`cement-promotion-v2` receipt and the function receipt retain that activation provenance.

The function format is bounded at 64 MiB, 50,000 entries, one million items, and depth 67. Per-value
limits of 1 MiB, 100,000 items, and depth 64 still apply, so a rich set can fail before 50,000 entries.

### Contrary evidence

A new confirmation that gives a promoted case a different output is a revision, not corruption. Review
records an `artifact.contradicted` event and changes no artifact status. The live set then fails
verification, so `follow` answers nothing for that operation until a promotion replaces the
contradicted member, or until the contradicting example is revoked or superseded. The promotion plan refuses (status 4) while a contradicted member has no verified
replacement, and it names the remedies: supersede, revoke, or suspend. A pinned version keeps
answering, because the switch pins what the person chose. `challenge` is an explicit judgment: it
records a counterexample and suspends the member that it contradicts. A pinned version stops
answering when a challenge, a revocation, or a suspension reaches one of its members.

### Projection

A projection program (`cement-projection-v1`) is a closed, line-oriented recognizer. It matches a raw
text field against named layouts. A layout is a title line, then labels and section headings. A match
returns the case key: the layout and its field names, plus the value of each field that the program
names in `keep`. The key holds no value from the text itself. An input that no layout recognizes is a miss,
and the LLM answers it. The interpreter is pure, total, and linear in its input: it runs no
regular expression on input and evaluates nothing.

`projection test` previews a program over the current revision and writes nothing. `projection set`
stores it in one write transaction after four checks:

- V1: the program parses.
- V2: an active example witnesses every layout.
- V3: no key groups examples with different outputs.
- V4: at least one active example projects.

Setting a new program retires the drafts and verified builds of the old one
(`projection superseded`). Promoted versions keep their own program, so a new program never
reinterprets an existing version.

Under a program, verification also replays every supporting raw input through the program to its key.
It then deletes the last structural line of each one and shows that the edited input leaves the case.
Set promotion keeps one program per version: members built under another program retire
(`projection-superseded`). Per-artifact promotion is refused under a program (status 4).

Cement verifies the grammar and the consistency of a program, never its semantic correctness. The
learning pass decides that the answers of an operation depend on structure alone, and its report
states that assumption.

### Entry points

`System.submit_proposal` and `System.propose` both write one proposal row and one
`proposal.created` event in one transaction, and they return the new proposal identifier. Neither
method resolves an artifact. `System.propose` validates its inputs and reads the operation first. If
those checks pass, it calls the configured candidate source one time, outside every transaction that
the call holds.

`cement proposal submit OPERATION --submission VALUE` calls `System.submit_proposal`. The leaf never
runs a candidate source. `--submission` carries `input`, `output`, an optional `provenance` and an
optional `source_id` in one JSON object, because separate flags cannot carry three maximum-size fields
through one argument list. Without a source id, the command inherits the method's non-idempotency: two
identical submissions write two proposals.

`cement resolve OPERATION --input VALUE` calls `System.resolve`. It reads the switch, verifies the
version that the switch selects, and evaluates that version under the same snapshot.
The leaf writes nothing and opens one read transaction. It prints eight fixed keys in every state. `switch` names the
mode that selected the version: an `off` switch verifies and answers nothing. `matched` carries the
distinction that the shared status 6 cannot. `false` is a verified absence inside a verified set.
`null` is a failed verdict that answers nothing. A caller must not collapse the two.

`cement learn cases OPERATION` is the learning pass's read surface. It groups pending proposals and
active examples by case key, under the stored program or a candidate one (`--program`), and it lists
unfinished publication work.

The LLM proposes instance behavior. It never chooses scope or activates artifacts. The learning pass
confirms examples, writes the program, compiles, verifies, and promotes. A person decides alone what
production serves.

## Isolation and revisioning

Scope identity is:

```text
(partition, operation, operation_revision, case_key)
```

The case key is the canonical input in exact mode, or the projected key under a projection program.

`partition` is mandatory to prevent accidental cross-tenant/workflow learning. Every explicit
operation revision retires prior builds, including a revision that keeps the same numeric thresholds.
A revision retires every older build at once. Cement withholds the cached output from `follow`, and
a pending proposal from an older revision cannot become an example. A pinned version keeps answering
across a revision until one of its members is revoked, suspended, or challenged. Callers reconcile prior effects, then work
under the current revision.

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
`verify_function` result binds the complete current snapshot to all seven ordered checks. It also binds
that snapshot to the latest current-revision receipt, and every member to one program.

Every verification result and every report is one committed read snapshot. It is not a lease, a
signature, a semantic replay, or a statement about future state. The live ledger can later revise,
suspend, revoke, replace, or checkpoint the same scope. Exported bytes stay deterministic because they
leave the ledger.

`function_report` returns the immutable receipt membership and the current operation state in one read
snapshot, and it keeps the two anchors in separate number spaces. Historical member support and
reviewer counts are frozen at build time. Active evidence and policy state remain current, so
complements or ratios across the two anchors are meaningless. The current-state half counts ready and
blocked scopes, pending proposals, artifact statuses, and stale-revision anomalies. `projection_limit`
bounds the returned detail. The report proves that every pending proposal in the partition keeps its
internal binding. It validates the content of only the members that it returns. Use
`reconstruct_function_receipt` to validate every member.

These are operational gates, not proof that supervisors were correct. Exact matching makes the coverage
claim honest: the artifact's match set contains one case key. The function object aggregates exact
entries without widening any entry. A projection program alone widens what one entry covers: every
raw input that the program maps to the key. Verification samples that set with every confirmed raw
input and one structural probe for each. It never proves the set complete. Broader predicates require a domain
contract with schemas, a trusted oracle or properties, exhaustive finite coverage, or formal proof.

## Storage and transactions

SQLite uses foreign keys, STRICT tables, rollback journaling, `synchronous=EXTRA`, a busy timeout,
defensive connection configuration when available, and explicit `BEGIN IMMEDIATE` write transitions.
A candidate source runs outside every write transaction, so it holds no lock while it works.

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

Schema version 3 holds the function layer: the `function_receipts` and `function_memberships` tables,
their indexes, and their triggers. A receipt is self-bound and stores the candidate and retired ID sets
as counts and digests. A membership row names its receipt, its ordinal, its artifact, and its report.
Triggers reject every update and delete on both tables. A further trigger rejects a membership insert
once the receipt row exists, so promotion must write the whole membership set before its receipt. A
deferred composite foreign key binds each membership to its receipt and to exactly that receipt's
`function_hash`. Version 3 also stores proposals with their scope and source id, and the supersession
links between examples. The projection programs, the projection settings, and the switch settings are
append-only.
Initialization rejects a version-2 ledger and names the reset; this release ships no migration runner.

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
validation. The core imports neither `subprocess` nor `signal`: the optional command candidate source
in `examples/command_source/` uses them. This exact-lookup envelope needs no expression engine or
provider SDK; the projection interpreter is a closed recognizer, not an expression language. A generalized language would enlarge the trusted computing base
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
