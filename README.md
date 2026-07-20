# Cement

Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior.
It is a local Python library and CLI with a durable SQLite ledger. Inputs and outputs are pure JSON;
provider adapters stay outside the core.

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
```

## Guarantees

- LLM output is inert until an explicit supervisor accepts or corrects it.
- The ordinary `handle` result exposes a proposal ID, never the proposed output. Review uses a
  separate surface.
- Confirmed examples bind partition, operation revision, canonical input, final output, reviewer,
  resolution, time, and receipt digest.
- Compilation is deterministic and model-free. Conflicts block builds; no majority vote hides them.
- Verification replays every active example in the exact scope plus partition, operation, revision,
  and input boundary probes.
- Promotion names the verified scope hash and atomically rechecks operation policy, artifact content,
  the complete evidence snapshot, and the sealed verification test set. Its receipt binds all of
  those values; retirement and suspension are one-way states.
- Counterexamples, evidence revocation, ambiguity, or runtime integrity failure quarantine affected
  artifacts before fallback.
- Request IDs are partition-local idempotency keys bound to immutable operation and input content.
  Candidate generation runs outside database transactions under a recoverable lease.

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
not an LLM; replace its command with your provider wrapper.

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

Repeat with a distinct request ID until the operation policy is satisfied, then run the independently
gated lifecycle:

```bash
uv run cement --db demo.db --partition acme compile support.reply
uv run cement --db demo.db --partition acme verify art_REPLACE_ME
uv run cement --db demo.db --partition acme report show report_REPLACE_ME
uv run cement --db demo.db --partition acme promote art_REPLACE_ME \
  --scope-hash HASH_FROM_VERIFY --actor release-manager
```

Run `compile` periodically with a scheduler of your choice. It creates drafts and never verifies or
promotes them automatically.

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

Include every fact that can change the answer - identity, locale, permissions, time, external-state
revision, and policy revision - in the JSON input. Hidden context cannot be compiled safely.

## Request outcomes

`handle` and `request` return explicit states:

| Status | Meaning | Caller action |
|---|---|---|
| `resolved` | Current promoted artifact or still-valid confirmed fixture produced the output. | Re-run live authorization/policy, then apply the plan idempotently. |
| `review_required` | A hidden candidate awaits supervision. | Inspect the named proposal on the separate review surface. |
| `in_progress` | This partition's generation lease is active. | Poll `request REQUEST_ID`; no input needs to be resubmitted while the lease is active. |
| `fallback_failed` | The candidate source failed, or its generation lease expired, and no output was stored. | For a stored source failure, retry `handle` with `--retry-failed` or use a new ID. For `generation_lease_expired`, resubmit the original `handle` input and request ID to reclaim the lease. |
| `rejected` | A supervisor rejected the proposal. | Use a new request ID if a fresh candidate is wanted. |
| `reconciliation_required` | A previously returned source was revoked/suspended, failed integrity checks, or belongs to an obsolete operation revision. No cached output is returned. | Reconcile any effects already attempted, then submit a new request ID. |

Replaying a request ID is content-idempotent, not a promise to replay an unsafe old output: quarantine
or an explicit operation revision can move a prior request to `reconciliation_required`. Pending
proposals from an older revision may only be rejected, never accepted or corrected. IDs may be reused
by another partition without coupling the two requests.

`cement-json-v1` accepts null, booleans, strings, signed 64-bit integers, arrays, and string-keyed
objects. Decimal/exponent numbers are rejected; encode domain decimals as strings with a documented
application format. Each input/output is capped at 1 MiB, combined records and artifacts at 3 MiB,
nesting at 64 levels, and container items at 100,000.

Proposal and report feeds plus example and artifact insertion catalogs carry monotonic `sequence`
values. Page them by passing the last observed value to `--after-sequence`. Example revocations and
artifact lifecycle changes do not reinsert catalog rows: consume `events --after SEQUENCE`, then
refetch named records or rescan the affected operation catalog. Report test rows use the last `key` with
`report show --after-test-key`. CLI usage and domain failures are JSON on stderr with stable nonzero
exit classes; JSON read from stdin is byte-bounded before parsing.

The command adapter protocol is documented in [docs/adapter-protocol.md](docs/adapter-protocol.md).
The full state model and trust boundaries are in [docs/architecture.md](docs/architecture.md) and
[docs/threat-model.md](docs/threat-model.md).

## Examples

[Hospital OCR layout-learning](examples/hospital_ocr/README.md) - offline walkthrough of supervised
per-layout extraction plans becoming deterministic reuse.

## Development

```bash
uv run python -m unittest discover -s tests -v
uv build
```

The project has no runtime package dependencies. `uv_build` is used only to produce the wheel and
source distribution.

## Deployment boundary

This release is a local control plane, not a network service or an ACL system. A new database starts
with mode `0600`, but evidence is plaintext. CLI actor names are recorded assertions, not
authentication. A library deployment can supply an `authority(partition, actor, action, subject)`
callback; remote authentication, encryption, retention, signing, and tenant-aware API authorization
remain deployment responsibilities.

The callback gates operation registration/revision, proposal review, compilation, verification,
promotion, challenge, evidence revocation, and artifact suspension. `handle` and read APIs assume the
embedding service has already authorized access to the exact partition. Calling `operation revise`
always creates a semantic revision and retires older builds, even when threshold values are unchanged.
Linux is the strongest command-adapter deployment target: Cement uses a subreaper supervisor there to
kill and reap detached descendants. This is lifecycle containment for a trusted provider wrapper, not
an arbitrary-code sandbox. A host cgroup/container boundary remains necessary if cleanup must survive
simultaneous runtime/supervisor termination or OOM.
