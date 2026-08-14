# Cement

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior.
The goal is to aggregate repeated work into a regular, if large, function that covers many situations
and edge cases. That goal would be difficult to reach without LLMs. Once built and verified, the
function is deterministic.

The safety boundary is intentionally small: Cement compiles only exact lookups. A promoted artifact
matches one canonical JSON input inside one partition and one operation revision. This finite scope is
fully replayable. Repetition does not justify a broader rule, and Cement makes no claim that repeated
approval proves domain correctness.

```text
handle(request)
  ├─ one promoted exact match → resolved JSON plan
  └─ no safe match → LLM proposal (hidden from consumer)
                       ├─ reject → audit only
                       └─ accept/correct → immutable example
                                              ↓ periodic compile
                                         draft artifact
                                              ↓ replay + boundary tests
                                         verified artifact
                                              ↓ explicit scope-hash promotion
                                         promoted exact match
                                              ↓ set verification + set promotion
                                    one function: every promoted match
                                              ↓ export
                                         portable bundle
                                              ↓ evaluate, with no ledger
                                         ├─ exact match → resolved JSON plan
                                         └─ no exact match → inert miss
```

## Guarantees

- LLM output is inert until an explicit supervisor accepts or corrects it.
- The ordinary `handle` result exposes a proposal ID, never the proposed output. Review uses a
  separate surface.
- Confirmed examples bind partition, operation revision, canonical input, final output, reviewer,
  resolution, time, and receipt digest.
- Compilation is deterministic and model-free. Conflicts block builds; no majority vote hides them.
- Verification replays every active example in the exact scope plus partition, operation, revision,
  and input boundary probes. Set verification adds six ordered checks over the complete promoted set.
- Promotion names the verified scope hash and atomically rechecks operation policy, artifact content,
  the complete evidence snapshot, and the sealed verification test set. Its receipt binds all of
  those values; retirement and suspension are one-way states. Set promotion repeats one function hash,
  retires predecessors, activates candidates, and writes one immutable receipt plus ordered
  memberships in the same transaction.
- Counterexamples, evidence revocation, ambiguity, or runtime integrity failure quarantine affected
  artifacts before fallback.
- Request IDs are partition-local idempotency keys bound to immutable operation and input content.
  Candidate generation runs outside database transactions under a recoverable lease.

The promoted artifacts of one operation aggregate into a single portable object:

- `cement-function-v2` is a capability-free JSON document. It gives the opening sentence a concrete
  referent: the whole promoted set is one function, not one entry.
- Entry order is normalized by input hash, so equal content produces equal bytes and one equal
  `function_hash`. The embedded hash proves normalized self-consistency. An independently obtained
  expected hash also pins caller-held identity. Neither mode proves origin or supplies a signature.
- Function identity is verified-content identity. The promoter and the promotion time never change the
  `function_hash`; the promotion receipt keeps that provenance separate.
- `verify_function` is read-only and authority-free. It returns six ordered checks over one snapshot of
  the complete promoted set. The sixth check requires the latest persisted receipt to bind that
  snapshot, so individually valid artifacts cannot pass as a set without a current checkpoint.
- An exported bundle evaluates with no ledger, no adapter, and no LLM. It stays deterministic after the
  ledger changes, so a revocation or a policy revision needs a newly verified export.
- An empty promoted set is a supported function, not an error. It verifies vacuously, exports a real
  empty document, and evaluates every input as a miss.
- Every verification result is one committed snapshot. It is not a lease and states nothing about
  future ledger state.

Cement returns data, not effects. The caller must run every resolved plan through current
authentication, authorization, policy, and idempotent effect execution. Determinism is not permission.

## Quick start

Requirements: Python 3.11+ with SQLite 3.37+ and `uv` for the development workflow.

```bash
uv sync
uv run cement --db demo.db --partition acme operation register support.reply \
  --min-confirmations 2 --min-reviewers 1 --min-span-seconds 0
```

The relaxed thresholds above are for a local demonstration. Defaults require three confirmations,
two recorded reviewers, and a seven-day observation span.

Ask the registered operation to handle JSON. The bundled adapter is a deterministic protocol stub,
not an LLM. Replace its command with your provider wrapper.

```bash
uv run cement --db demo.db --partition acme handle support.reply \
  --request-id ticket-001 \
  --input '{"question":"Where is my invoice?"}' \
  --source-command '["python3","-m","cement_runtime.example_adapter"]'
```

A miss returns `review_required` and a proposal ID. Only the review surface reveals the suggestion:

```bash
uv run cement --db demo.db --partition acme proposal list
uv run cement --db demo.db --partition acme proposal show prop_REPLACE_ME
uv run cement --db demo.db --partition acme proposal review prop_REPLACE_ME \
  --reviewer operator-1 --decision accept
```

Repeat with a distinct request ID until the confirmations satisfy the operation policy. Then run the
independently gated lifecycle:

```bash
uv run cement --db demo.db --partition acme compile support.reply
uv run cement --db demo.db --partition acme function verify-drafts support.reply \
  --actor release-manager
uv run cement --db demo.db --partition acme function inspect support.reply
uv run cement --db demo.db --partition acme function promote support.reply \
  --expected-function-hash HASH_FROM_INSPECT --actor release-manager
```

`function verify-drafts` verifies every current-build draft of the operation in one locked transaction.
`function inspect` then previews the retained members, the verified candidates, the replacements, and
the skipped rows. It returns the prospective function hash that `function promote` must repeat.
Promotion fails if the set drifts after the preview. The per-artifact `verify` and `promote` commands
remain available for one artifact at a time. Per-artifact promotion leaves the sixth set check failing
until you promote a set checkpoint. A live export then exits 6.

Run `compile` periodically with a scheduler of your choice. It creates drafts and never verifies or
promotes them automatically.

### The function group

`cement function` has eight leaves:

| Leaf | Purpose |
|---|---|
| `show` | Report the receipt anchor beside the current operation state. |
| `receipts` | Page the receipt history in descending sequence order. |
| `verify-drafts` | Verify every current-build draft in one locked transaction. |
| `verify` | Run the six ordered checks over the current promoted set. |
| `inspect` | Preview the prospective set and return its function hash. |
| `promote` | Promote the whole set atomically against a repeated hash. |
| `export` | Emit bundle bytes for the live set or for a historical receipt. |
| `eval` | Answer one canonical input from a bundle, with no ledger. |

Pass `--expected-function-hash` to `function verify` to pin the verified snapshot. The check then fails
on set growth and on any other drift. That result is one read snapshot, not a lease. A later export can
still see a different set. [docs/architecture.md](docs/architecture.md) names the six checks in their
returned order.

Verify the set and export it. Then answer inputs where no ledger exists:

```bash
uv run cement --db demo.db --partition acme function verify support.reply
uv run cement --db demo.db --partition acme function export support.reply \
  --out support.function.json
uv run cement function eval --bundle support.function.json \
  --input '{"question":"Where is my invoice?"}' \
  --expected-function-hash HASH_FROM_VERIFY
```

`function eval` needs no `--db` and no `--partition`. It returns `artifact_hash`, `function_hash`,
`matched`, and `output`. `function export --receipt-id` serves a historical receipt, including one from
a superseded operation revision.

## Library API

```python
from cement_runtime import Candidate, CompilePolicy, System

class ProviderAdapter:
    def propose(self, request):
        # Call an LLM here; provenance should identify model/prompt/tool revisions.
        return Candidate(
            output={"kind": "reply", "text": "candidate"},
            provenance={"model": "provider/model", "prompt_revision": "sha256:..."},
        )

system = System("cement.db", candidate_source=ProviderAdapter())
system.register_operation("tenant-42", "support.reply", policy=CompilePolicy())

outcome = system.handle(
    "tenant-42",
    "support.reply",
    {"question": "Where is my invoice?", "locale": "en-GB", "policy_revision": 7},
    request_id="ticket-123/attempt-1",
)
```

Put every fact that can change the answer into the JSON input, including identity, locale,
permissions, time, external-state revision, and policy revision. Cement cannot compile hidden context
safely.

## Request outcomes

`handle` and `request` return explicit states:

| Status | Meaning | Caller action |
|---|---|---|
| `resolved` | Current promoted artifact or still-valid confirmed fixture produced the output. | Re-run live authorization/policy. Then apply the plan idempotently. |
| `review_required` | A hidden candidate awaits supervision. | Inspect the named proposal on the separate review surface. |
| `in_progress` | This partition's generation lease is active. | Poll `request REQUEST_ID`. While the lease is active, the input needs no resubmission. |
| `fallback_failed` | The candidate source failed, or its generation lease expired, and Cement stored no output. | For a stored source failure, retry `handle` with `--retry-failed` or use a new ID. For `generation_lease_expired`, resubmit the original `handle` input and request ID to reclaim the lease. |
| `rejected` | A supervisor rejected the proposal. | Use a new request ID to request another candidate. |
| `reconciliation_required` | A previously returned source lost validity through revocation, suspension, a failed integrity check, or an obsolete operation revision. Cement returns no cached output. | Reconcile any effects already attempted. Then submit a new request ID. |

Replaying a request ID is content-idempotent. It does not promise to replay an unsafe old output.
Quarantine or an explicit operation revision can move a prior request to `reconciliation_required`.
Cement allows only rejection for pending proposals from an older revision. Another partition can
reuse the same ID without coupling the two requests.

`cement-json-v1` accepts null, booleans, strings, signed 64-bit integers, arrays, and string-keyed
objects. It rejects decimal and exponent numbers. Encode domain decimals as strings with a documented
application format. Cement caps each input/output at 1 MiB, combined records and artifacts at 3 MiB,
nesting at 64 levels, and container items at 100,000.

Proposal and report feeds plus example and artifact insertion catalogs carry monotonic `sequence`
values. To page them, pass the last observed value to `--after-sequence`. Example revocations and
artifact lifecycle changes do not reinsert catalog rows. Consume `events --after SEQUENCE`. Then
refetch named records or rescan the affected operation catalog. Report test rows use the last `key`
with `report show --after-test-key`. `function receipts` pages in the other direction. It returns rows
in descending sequence order, and `--before-sequence` takes an exclusive cursor. Set promotion emits
one `function.promoted` event with bounded ID projections; the membership table stays authoritative
for the exact member list. CLI usage and domain failures are JSON on stderr with stable
nonzero exit classes. Cement bounds JSON from stdin by byte count before it parses the input.

Exit 6 is the negative-verdict class. It means that the command completed correctly and that its answer
is negative. The leaf names the object, and the object selects the payload channel:

| Leaf | Exit-6 answer | Payload |
|---|---|---|
| `function verify-drafts` | The batch completed and at least one report failed. | `stdout` |
| `function verify` | At least one of the six set checks failed. | `stdout` |
| `function export` | The live set is unverified, so no bundle bytes exist. | `stderr` |
| `function eval` | The bundle holds no exact case for the canonical input. | `stdout` |

Every other nonzero exit reports a failure to complete. Exit 2 covers usage and validation. Exit 3
means an absent object, exit 4 a state or authority conflict, and exit 5 an integrity failure.

Read [docs/adapter-protocol.md](docs/adapter-protocol.md) for the command adapter protocol. Read
[docs/architecture.md](docs/architecture.md) and [docs/threat-model.md](docs/threat-model.md) for the
full state model and trust boundaries.

## Examples

[Hospital OCR layout-learning](examples/hospital_ocr/README.md) - offline walkthrough of supervised
per-layout extraction plans becoming deterministic reuse. It ends by sealing the promoted layouts into
one function, deleting the ledger, and answering a document from the exported bundle alone.

## Development

```bash
uv run python -m unittest discover -s tests -t .
uv build
```

The project has no runtime package dependencies. It uses `uv_build` only to produce the wheel and
source distribution.

## Deployment boundary

This release is a local control plane, not a network service or an ACL system. A new database starts
with mode `0600`, but evidence is plaintext. CLI actor names are recorded assertions, not
authentication. A library deployment can supply an `authority(partition, actor, action, subject)`
callback; remote authentication, encryption, retention, signing, and tenant-aware API authorization
remain deployment responsibilities.

An exported bundle is a second deployment object with its own boundary. It executes without the
database and without the authority callback, so the ledger's file permissions no longer protect it.
The bundle is plaintext and carries the exact inputs, the exact outputs, and the governance digests.
Classify it with your other sensitive data. Apply the same retention and disclosure rules.
`function export --out` writes atomically through a mode-0600 temporary file and refuses a non-regular
destination. The reader accepts one strict UTF-8 regular file and bounds it at 64 MiB, independently
from the 1 MiB bound on the evaluation input. `function eval` is ledger-free, not import-free: it opens
and reads the bundle path, and importing `cement_runtime` still loads `sqlite3`.

The callback gates operation registration/revision, proposal review, compilation, verification,
promotion, challenge, evidence revocation, and artifact suspension. `handle` and read APIs assume the
embedding service has already authorized access to the exact partition. `operation revise`
always creates a semantic revision and retires older builds, even when threshold values stay unchanged.
Linux is the strongest command-adapter deployment target: Cement uses a subreaper supervisor there to
kill and reap detached descendants. This is lifecycle containment for a trusted provider wrapper, not
an arbitrary-code sandbox. If cleanup must survive simultaneous runtime/supervisor
termination or OOM, a host cgroup/container boundary remains necessary.
