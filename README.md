# Cement

Cement turns repeated LLM work into narrowly scoped deterministic functions. In a chat deployment
such as Open WebUI, people ask for one kind of task many times with small variations: an OCR
extraction from different documents, for example. The LLM answers each one, often with a small
script, and Cement retains each input and answer. Periodically, an LLM-driven learning pass reads
the retained answers, finds the tasks that recur, and merges their scripts into one deterministic
function. The function covers every case that it has seen, and each case stays exact. The function
grows as new variations appear.

A person can read the function and decides whether to switch it on or off in production. While it
is on, the function answers matching inputs instead of the LLM, so those results stop depending on
probabilistic processing. Every other input still goes to the LLM. Learning never widens a case
beyond the inputs that it has seen. Where inputs share one structure (one form layout, for
example) but differ in their values, a verified projection maps each new input to the key of its
case. The LLM answers an input that the projection does not recognize.

```text
chat input ───┬─ switched-on function covers it → the function answers (deterministic)
              └─ no coverage → the LLM answers → Cement retains the answer as a proposal
                                                        ↓ learning pass (periodic skill)
                                    review (learning-pass) · projection program · compile
                                                        ↓ replay + boundary tests
                                    verified artifacts → set promotion → a new version
                                                        ↓ a person
                                    switch: off | follow the newest version | pinned to one
resolve, against the ledger → the selected version answers, or a verified miss
export → portable bundle → function eval, with no ledger → the same answer, or an inert miss
```

The safety boundary is small on purpose. Cement compiles exact lookups only. A promoted entry
matches one case key inside one partition and one operation revision: the canonical JSON input, or
the key that a verified projection gives it. This finite scope is fully replayable. Repetition does
not justify a broader rule, and Cement makes no claim that repeated confirmation proves domain
correctness.

## Guarantees

- LLM output is inert until the learning pass accepts or corrects it, and a function answers only
  after a person switches it on.
- A proposal-creating call returns a proposal ID, never the proposed output. Review uses a
  separate surface.
- Confirmed examples bind partition, operation revision, canonical input, final output, reviewer,
  resolution, time, and receipt digest.
- Compilation is deterministic and model-free. Conflicts block builds; no majority vote hides them.
- Verification replays every active example in the exact scope plus partition, operation, revision,
  and input boundary probes. Under a projection program it also replays each raw input to its key and
  shows that a structural edit leaves the case. Set verification adds seven ordered checks over the
  complete promoted set.
- Promotion names the verified scope hash and atomically rechecks operation policy, artifact content,
  the complete evidence snapshot, and the sealed verification test set. Its receipt binds all of
  those values; retirement and suspension are one-way states. Set promotion repeats one function hash,
  retires predecessors, activates candidates, and writes one immutable receipt plus ordered
  memberships in the same transaction.
- A new confirmation that contradicts a promoted case is a revision: the live set fails verification
  and answers nothing until a promotion replaces that case or the contradicting example is revoked
  or superseded. A challenge suspends the contradicted
  artifact; an evidence revocation suspends every dependent build. A pinned version stops answering
  when one of its members is challenged, revoked, or suspended.
- The switch of each operation selects what production serves: `off` (the default for a new
  operation), `follow` the newest version, or `pinned` to one version. Only a person sets it.
- A configured candidate source runs outside every Cement transaction. `System.propose` invokes it
  one time for each call, and Cement never retries it.

The promoted artifacts of one operation aggregate into a single portable object:

- `cement-function-v3` is a capability-free JSON document. It gives the opening sentence a concrete
  referent: the whole promoted set is one function, not one entry. It carries the projection program
  of its version, so it answers raw inputs exactly as `resolve` does. A `cement-function-v2` bundle
  still evaluates.
- Entry order is normalized by input hash, so equal content produces equal bytes and one equal
  `function_hash`. The embedded hash proves normalized self-consistency. An independently obtained
  expected hash also pins caller-held identity. Neither mode proves origin or supplies a signature.
- Function identity is verified-content identity. The promoter and the promotion time never change the
  `function_hash`; the promotion receipt keeps that provenance separate.
- `verify_function` is read-only. It returns seven ordered checks over one snapshot of
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

Spell every option in full. The CLI rejects an abbreviated option, such as `--part` for
`--partition`, with exit 2 and `unrecognized arguments`.

```bash
uv sync
uv run cement --db demo.db --partition acme operation register support.reply
```

The default policy needs two confirmations of a case from at least one reviewer, with no minimum
observation span. The learning pass is the reviewer, and the person who switches the function on is
the gate. Pass `--min-confirmations`, `--min-reviewers`, or `--min-span-seconds` to require more.

Generate a candidate with your own model or tooling. Then submit it. Cement stores it as one
pending proposal.

```bash
uv run cement --db demo.db --partition acme proposal submit support.reply \
  --submission '{"input":{"question":"Where is my invoice?"},
                 "output":{"kind":"reply","text":"Your invoice is in the billing portal."}}'
```

The command returns a proposal ID and nothing else. Only the review surface reveals the candidate.
The learning pass reviews each proposal. To review by hand as the learning pass does, run:

```bash
uv run cement --db demo.db --partition acme proposal list
uv run cement --db demo.db --partition acme proposal show prop_REPLACE_ME
uv run cement --db demo.db --partition acme proposal review prop_REPLACE_ME \
  --reviewer learning-pass --decision accept
```

Repeat the submit and review steps until the confirmations satisfy the operation policy. Then the
learning pass compiles, verifies, and promotes a new version:

```bash
uv run cement --db demo.db --partition acme compile support.reply
uv run cement --db demo.db --partition acme function verify-drafts support.reply \
  --actor learning-pass
uv run cement --db demo.db --partition acme function inspect support.reply
uv run cement --db demo.db --partition acme function promote support.reply \
  --expected-function-hash HASH_FROM_INSPECT --actor learning-pass
```

The new version answers nothing yet. A person reads it and switches it on:

```bash
uv run cement --db demo.db --partition acme function read support.reply
uv run cement --db demo.db --partition acme function switch support.reply \
  --mode follow --actor ops-lead
```

`function verify-drafts` verifies every current-build draft of the operation in one locked transaction.
`function inspect` then previews the retained members, the verified candidates, the replacements, and
the skipped rows. It returns the prospective function hash that `function promote` must repeat.
Promotion fails if the set drifts after the preview. The per-artifact `verify` and `promote` commands
remain available for one artifact at a time in exact mode. Per-artifact promotion leaves the sixth
set check failing until you promote a set checkpoint. A live export then exits 6.

`compile` creates drafts and never verifies or promotes them. In production, the learning pass runs
these commands: see [The learning pass](https://github.com/eturkes/cement#the-learning-pass).

### The function group

`cement function` has eleven leaves:

| Leaf | Purpose |
|---|---|
| `show` | Report the receipt anchor beside the current operation state. |
| `receipts` | Page the receipt history in descending sequence order. |
| `verify-drafts` | Verify every current-build draft in one locked transaction. |
| `verify` | Run the seven ordered checks over the current promoted set. |
| `inspect` | Preview the prospective set and return its function hash. |
| `promote` | Promote the whole set atomically against a repeated hash. |
| `export` | Emit bundle bytes for the live set or for a historical receipt. |
| `read` | Show one version as code: its cases, and the proposals behind each case. |
| `switch` | Turn the function off, make it follow the newest version, or pin one version. |
| `versions` | List the promoted versions, newest first. `--check` also reports whether each one can serve now. |
| `diff` | Compare two versions: the cases that the second one adds, removes, or changes. |
| `eval` | Answer one canonical input from a bundle, with no ledger. |

Pass `--expected-function-hash` to `function verify` to pin the verified snapshot. The check then fails
on set growth and on any other drift. That result is one read snapshot, not a lease. A later export can
still see a different set. [docs/architecture.md](https://github.com/eturkes/cement/blob/main/docs/architecture.md) names the seven checks in their
returned order.

A newly registered operation starts with its switch `off`, so `resolve` answers nothing until a
person turns the function on. `function switch OPERATION --mode follow --actor NAME` serves the newest
promoted version. `--mode pinned --function-hash HASH` serves one version, and a later promotion does
not change it. To roll back, pin an earlier version that `function versions` lists.

`function read OPERATION` shows a version as code before you switch it on. Each case is one branch,
with the proposals that the learning pass confirmed for it. The command reads the version that the
switch pins, or else the newest version. `--receipt-id` reads any version, and `--json` prints the same
listing as JSON. An operation that has no promoted version exits 3.

When verification fails because promoted members are damaged, or because two members claim one input,
contain them in two steps.
`function quarantine-plan OPERATION` writes nothing. It lists each promoted member with a
member-local finding and its reasons, and it prints a `plan_digest`. An empty list means that no member
needs containment, not that verification passes. `function quarantine OPERATION --plan-digest DIGEST
--actor NAME` suspends exactly the members of that plan and writes one `function.quarantined` event.
If the plan changed after you read it, the command writes nothing and exits 4. A second run with the
same digest reports `already_applied` and writes nothing. Suspension contains the members but
publishes no replacement, so `follow` stays failed until you promote a new version.

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

### Answering one input from the ledger

`cement resolve` reads the operation's switch, verifies the version that the switch selects, and then
answers one input from it. Use it where the ledger is available. Use `function eval` where it is not.
An `off` switch answers nothing.

```bash
uv run cement --db demo.db --partition acme resolve support.reply \
  --input '{"question":"Where is my invoice?"}'
```

The command takes one operation name and one required `--input`. `--input` accepts JSON text, or `-`
to read standard input. Pass the optional `--expected-function-hash` to pin the answer to one set. The
command then verifies and answers under one snapshot. `function verify` prints that digest.

```bash
uv run cement --db demo.db --partition acme function verify support.reply
uv run cement --db demo.db --partition acme resolve support.reply \
  --input '{"question":"Where is my invoice?"}' \
  --expected-function-hash HASH_FROM_VERIFY
```

`resolve` writes nothing. It opens one read transaction. It creates no row, no event, and no example.
It also refuses a `--db` path that does not exist, and it creates no ledger file there.

The command prints the same eight keys in every state:

| Key | Meaning |
|---|---|
| `passed` | The verification verdict over the promoted set. |
| `entries` | The number of entries in the verified set. |
| `function_hash` | The digest of the verified set. It survives a failed verdict as a diagnostic. |
| `checks` | The ordered checks of the selected version, each with `key`, `passed`, and `detail`: the seven set checks under `follow`, the four pinned checks under `pinned`, none under `off`. |
| `matched` | `true` for an answer, `false` for a verified absence, `null` for a failed verdict. |
| `output` | The answer. It is `null` unless `matched` is `true`. |
| `artifact_hash` | The digest of the answering artifact. It is `null` unless `matched` is `true`. |
| `switch` | The switch mode: `off`, `follow`, or `pinned`. An `off` switch verifies nothing, so every other key is `null` and `checks` is empty. |

Status 0 means `matched` is `true`. Status 6 covers both other states, and `matched` separates them. A
verified absence reports `false`, and a failed verdict reports `null`. An unregistered operation is
status 3. An empty promoted set is not an error: it verifies and reports a verified absence.

One resolve under `follow` runs the full seven-check verification, so it costs what `function verify` costs. Measured
end to end through the shipped method, in exact mode before the seventh check existed: 5.7 ms for
one entry, 613 ms for 1,000 entries, and 36,452 ms with 985,696 KiB peak resident memory at the
50,000-entry maximum (`.agent/decisions/m3u2b-resolve-bench.json`). The cost grows with the size of
the set, not with the size of the input. In one process, a later call reuses that verification until a
commit through SQLite changes the ledger, from any connection or any process. Each `cement` command is
a new process, so each command pays the full cost.
A raw edit of the ledger file that bypasses SQLite is outside this guarantee, and `cement function
verify` always runs the full verification.

### Submitting a candidate you already hold

`cement proposal submit` writes one pending proposal from a candidate you supply. It is the only
command that creates a proposal. No command runs a candidate source.

```bash
uv run cement --db demo.db --partition acme proposal submit support.reply \
  --submission '{"input":{"question":"Where is my invoice?"},
                 "output":{"kind":"reply","text":"candidate"},
                 "provenance":{"model":"provider/model"}}'
```

The command takes one operation name and one required `--submission`. `--submission` carries the whole
candidate in one JSON object. Pass `-` to read that object from standard input:

```bash
cat > candidate.json <<'JSON'
{"input": {"question": "Where is my invoice?"},
 "output": {"kind": "reply", "text": "candidate"},
 "source_id": "chat-7:message-3"}
JSON
uv run cement --db demo.db --partition acme proposal submit support.reply --submission - < candidate.json
```

One frame carries every field at its maximum size. Separate flags cannot, because the operating system
refuses an argument list above 131,071 bytes, and only one flag can read standard input. Inline text is
also visible to observers on the same host, because it enters the argument list of the process.
Prefer `-` for a candidate you must protect.

The object takes four keys. `input` and `output` are required. `provenance` is optional and defaults to
an empty object. `source_id` is optional: it names the observation, and Cement refuses a second
proposal with the same source id (exit 4). Any other key is an error, and the message names every offending key. A repeated key is
also an error, so the command never silently keeps one of two values.

Success prints one key, `proposal_id`, at status 0. The command echoes no part of the candidate.

Without a source id, Cement gives no idempotency here. Two identical submissions write two proposals
and return two identifiers. With one, the second submission exits 4 and writes nothing. Do not retry a failed submission. List the partition's pending proposals instead:

```bash
uv run cement --db demo.db --partition acme proposal list --status pending
```

Review a submitted proposal with the `proposal review` command. Every route that writes a proposal
shares that one review surface.

### Projection

Some operations receive inputs that share one structure and differ in their values: forms of one
layout with different patients, for example. Exact keys would never repeat there. A projection program
(`cement-projection-v1`) maps each raw input to the key of its case: the layout and its field names.
A `cement-projection-v2` program also ends a label at a full-width colon `：`, for forms such as
Japanese forms.
The learning pass writes the program. Cement verifies it before it stores it. This program
recognizes one intake form layout of an operation `form.plan` whose input is `{"document": TEXT}`.
`projection set` refuses a layout that no confirmed example shows, so the learning pass first
confirms examples of each layout:

```bash
cat > program.json <<'JSON'
{"abi": "cement-projection-v1", "text": "document", "keep": [],
 "layouts": [{"name": "intake", "title": "PATIENT INTAKE FORM",
              "entries": [{"label": "Name"}, {"label": "Date of birth"}]}]}
JSON
uv run cement --db demo.db --partition acme projection test form.plan --program - < program.json
uv run cement --db demo.db --partition acme projection set form.plan --program - \
  --actor learning-pass < program.json
uv run cement --db demo.db --partition acme projection show form.plan
```

`projection test` previews the program and writes nothing. `projection set` refuses a program that
fails to parse, a layout that no confirmed example shows, a key that would merge different outputs,
and a program that no confirmed example matches. A new program retires the drafts and verified
builds of the old one.
Promoted versions keep their own program. An input that no layout recognizes is a miss, and the LLM
answers it. Cement verifies the program's grammar and consistency, not its semantic correctness: the
learning pass decides that an operation's answers depend on the structure alone.

### The learning pass

The learning pass is an agent skill in `skills/cement-learn/`. An operator runs it periodically
with an agent that loads Agent Skills. It reads the retained answers, merges the scripts of each
recurring case into one output, reviews each proposal as `learning-pass`, writes or extends the
projection program, compiles, verifies, and promotes. It never switches a function on. The Open
WebUI example ships the same pass as an Open WebUI skill and an administrator tool, so the pass
runs inside Open WebUI with the chat model. The nucllei example ships the pass as a nucllei skill:
the chat model runs it inside a chat, on the ledger of one user.

Its read surface groups pending proposals and active examples by case key:

```bash
uv run cement --db demo.db --partition acme learn cases support.reply
uv run cement --db demo.db --partition acme learn cases form.plan --projectable
uv run cement --db demo.db --partition acme learn cases form.plan --program - < program.json
```

`--projectable` derives a program from the raw inputs: one layout for each form structure. The
result shows that program as `program`.

Two commands make the changes of a pass. They act as `learning-pass` unless you pass
`--reviewer` or `--actor`:

```bash
uv run cement --db demo.db --partition acme proposal list --status pending
uv run cement --db demo.db --partition acme learn cases support.reply
cat > merged.json <<'JSON'
{"kind": "reply", "text": "Your invoice is in the billing portal."}
JSON
uv run cement --db demo.db --partition acme learn merge support.reply --output - \
  --note "run 7, model X" --proposals prop_REPLACE_ME < merged.json
uv run cement --db demo.db --partition acme learn publish support.reply
```

`learn merge` confirms one merged output for one case. `learn cases` groups the pending proposals
that `proposal list` shows into cases. Name the pending proposals of one case with `--proposals`
and its active examples with `--examples`; a flag without ids names none. The
command accepts each proposal that equals the merge and corrects the others to it. Then it
supersedes each named example whose output differs. Pass `--projectable` to group the cases as
`learn cases --projectable` does. An empty or repeated id list, or ids of more than one case, is
refused before any write (exit 2). Each write commits alone. If a write fails, stdout lists the
writes that returned, stderr shows the error, and the exit code is its class. The write that
failed can also have committed. A merge is not idempotent, so run `learn cases` again before you
repeat a step.

`learn publish` compiles, verifies, and promotes a new version. With `--projectable`, it first
sets the program that it derives from the confirmed inputs. When it promotes nothing, `reason`
names why: `failed` (a draft failed verification, exit 6), `empty` (no case has enough
confirmations), or `same` (the newest version already holds the set). A publication leaves the
switch as it is. Under `off`, the new version answers nothing. Under `follow`, it answers at once.
A pinned switch keeps its version.

Two commands change earlier confirmations. `example supersede` replaces earlier examples with a
re-merged output that extends them: one new example for each old one, with the same input. It
writes nothing and refuses an empty or repeated id, an example of another operation, or an output
equal to the old one (exit 2), an unknown example (exit 3), and a revoked or already superseded
example (exit 4). `example revoke` withdraws an example that is wrong, and it also
stops every version built on that example from answering.

## Library API

```python
from cement_runtime import Candidate, CandidateRequest, CompilePolicy, System


class ProviderAdapter:
    def propose(self, candidate_request: CandidateRequest) -> Candidate:
        # Call an LLM here; provenance should identify model/prompt/tool revisions.
        return Candidate(
            output={"kind": "reply", "text": "candidate"},
            provenance={"model": "provider/model", "prompt_revision": "sha256:..."},
        )


system = System("cement.db", candidate_source=ProviderAdapter())
system.register_operation("tenant-42", "support.reply", policy=CompilePolicy())  # 2 / 1 / 0 s

proposal_id = system.propose(
    "tenant-42",
    "support.reply",
    {"question": "Where is my invoice?", "locale": "en-GB", "policy_revision": 7},
)
```

Put every fact that can change the answer into the JSON input, including identity, locale,
permissions, time, external-state revision, and policy revision. Cement cannot compile hidden context
safely.

The `System` methods group by purpose. Each write runs in one transaction and writes one event; a
refusal writes nothing:

| Purpose | Methods |
|---|---|
| Retain answers | `submit_proposal`, `propose` (pending proposals; optional `source_id`, a repeat raises `ConflictError`) |
| Review | `review` (`ReviewResult`), `supersede_examples`, `revoke_example`, `challenge`, `suspend_artifact` |
| Projection | `test_projection` (preview, writes nothing), `set_projection` (V1-V4 or `ValidationError`), `projection` (the stored program or `None`) |
| Learning pass | `learning_cases` (cases by key + unfinished work, read-only) |
| Build | `compile`, `verify_drafts`, `inspect_function_promotion`, `promote_function` (repeats the inspected hash or raises `ConflictError`) |
| Versions + switch | `function_receipts`, `function_versions`, `diff_versions`, `set_switch` (`off`, `follow`, `pinned`), `switch`, `serving` |
| Answer | `resolve`, `verify_function`, `function_report`, `reconstruct_function_receipt`; `evaluate` + `parse_function` answer from a bundle with no ledger |

`cement_runtime.learning` makes the changes of a learning pass over these methods. `merge_case`
and `publish` do what `learn merge` and `learn publish` do, and they return a `Merge` and a
`Publication`. `cases` and `raw_inputs` read what they group by. A merge whose write fails after
it starts raises `MergeInterruptedError`, which holds the error and the writes that returned.
The write that raised can also have committed, so read the cases again before you retry.

A method that returns a record gives a typed dictionary, and a type checker sees each field with
its own type. `cement_runtime.models` defines the records, for example `ProposalRecord`
(`proposal`, `proposals`), `ExampleRecord`, `ArtifactRecord`, `ReportRecord`, `EventRecord`,
`ProjectionPreview` and `LearningCasesRecord`. `cement_runtime.projection` defines
`ProgramDocument`, which `draft_program` returns. At run time each record is a plain `dict`, so
the CLI prints the same JSON. A field that holds stored JSON, such as an input or an output, has
the type `JSONValue`. `cement_runtime.json_value` declares `JSONValue` and `JSONScalar` with `type`
statements, so they serve annotations, and `isinstance` refuses them.

### Explicit proposal submission

`System.submit_proposal` and `System.propose` write one pending proposal directly. Use them when you
already hold a candidate, or when you want exactly one candidate from the configured source.

```python
proposal_id = system.submit_proposal(
    "tenant-42",
    "support.reply",
    {"question": "Where is my invoice?"},
    candidate=Candidate(
        output={"kind": "reply", "text": "candidate"},
        provenance={"model": "provider/model", "prompt_revision": "sha256:..."},
    ),
)

proposal_id = system.propose("tenant-42", "support.reply", {"question": "Where is my invoice?"})
```

`submit_proposal` takes the candidate from the caller. It never invokes the configured candidate
source. `propose` invokes the configured source one time for each call that reaches invocation, and
it never retries. The source runs outside every transaction that the call holds. A source that calls
back into the same `System` opens its own transaction, which Cement cannot prevent. Both methods
return the new proposal identifier as a string.

Each call writes one proposal row and one `proposal.created` event. Cement writes the two records
in one transaction, and it writes no other row. That count covers Cement's own transaction only. A
source that calls back into the same `System` writes on its own transaction. Without a source id,
Cement gives no idempotency here. Two identical calls write two proposals and return two different
identifiers.

`submit_proposal` raises `ValidationError` for a rejected partition, operation, input value, or
candidate. `propose` raises `StateError` when no candidate source is configured. It raises
`CandidateSourceError` when the source fails or returns an unusable candidate. That error carries no
detail from the source. Both methods raise `NotFoundError` when the partition holds no such
operation. `propose` also raises `StateError` when the operation revision changes during generation,
because it captures the revision before it calls the source. `submit_proposal` captures no revision.
It binds whatever revision is current under its own write lock, so a concurrent revision change
cannot make it fail.

A failure before the commit writes nothing. One window is different. If the database commit succeeds
and then fails, Cement raises `StateError` and returns no identifier, but the proposal and its event
are durable. The ledger then looks the same as a success. Do not retry a call that has no source
id, because a retry writes a second proposal. To recover, list the pending proposals for the
partition with `System.proposals`. Then read each candidate with `System.get_proposal` and match your
own input.

A proposal can carry a source id that names the observation it came from, for example the
deployment, the chat, the user message and the digest of the input. Pass it as
`submit_proposal(..., source_id=...)`, or as the `source_id` key of the `--submission` object.
Cement refuses a second proposal with the same source id for the same partition and operation
(`ConflictError`, exit 4), so a repeated delivery adds no second proposal.

### Reviewing a proposal

`System.review` returns a `ReviewResult`. It carries four fields and no request identity:

| Field | Meaning |
|---|---|
| `proposal_id` | The reviewed proposal. It is the only identity in the value. |
| `status` | `accepted`, `corrected`, or `rejected`. It equals the proposal's own status, so `proposal show` reports the same word. |
| `example_id` | The confirmed example that accept and correct create. It is `null` after a rejection, which creates no example. |
| `output` | The confirmed output. It is the proposed output after accept and your supplied output after correct. It is `null` after a rejection. |

Accept and correct each create exactly one confirmed example. Reject creates none. The three
decisions return the same four keys, so a script can test `example_id` for null instead of testing
for a missing key.

`ReviewResult.status` and `proposal show` report the same word for the same decision: `accepted`,
`corrected`, or `rejected`. Cement publishes one review vocabulary and no second one.

`System.get_proposal`, `System.proposal`, `System.proposals`, and `function_report` also expose no
request identifier. Use `proposal_id` to name a proposal on every surface.

## Outcomes

Two routes answer a caller. `resolve` reads the ledger, and `function eval` reads an exported
bundle. Each route reports an exact match, a verified absence, or a failed verdict, and neither route
writes. `resolve` also reports an `off` switch, which answers nothing. Review reports its own outcome
through `proposal show` and `System.review`, which both return `accepted`, `corrected`, or `rejected`.

A suspended artifact stops answering, and a contradicted one makes the live set fail verification
until a promotion replaces it or the contradicting example is revoked or superseded. A later operation revision retires the older builds, and Cement then
allows only rejection for a pending proposal from that older revision.

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
| `function verify` | At least one of the seven set checks failed. | `stdout` |
| `function export` | The live set is unverified, so no bundle bytes exist. | `stderr` |
| `function eval` | The bundle holds no exact case for the canonical input. | `stdout` |

Every other nonzero exit reports a failure to complete. Exit 2 covers usage and validation. Exit 3
means an absent object, exit 4 a state conflict, and exit 5 an integrity failure.

The CLI writes `stdout` without an explicit flush, and Python flushes it when the process exits. If
the reader closes the pipe first, the process exits 120, and Python writes a `BrokenPipeError` notice
to `stderr` that is not JSON. An embedding host that calls `main` flushes its own `stdout`.

An interrupt (`SIGINT`, Ctrl-C) stops the `cement` command with exit 130 and an `interrupted` error
on `stderr`. If the command waits for the ledger lock, the interrupt takes effect when that wait
ends, after 10 seconds at most. A write that the interrupt stopped did not commit, so it leaves no
row behind. A host that calls `main` itself receives the `KeyboardInterrupt`. If the process
starts with `SIGINT` ignored, it ignores the interrupt, and a lock wait ends with exit 4 after 10
seconds. A command that a shell script starts with `&` starts that way.

The root `verify` command does not use exit 6. It reports a failed verification as exit 0 with
`"passed": false` in its payload. Read the `passed` field to get the verdict from root `verify`. Read
the exit status to get the verdict from the `function` commands in the table above. A script that
changes between these two commands must change its verdict check at the same time.

Read [examples/command_source/README.md](https://github.com/eturkes/cement/blob/main/examples/command_source/README.md) for the optional command
candidate source and its protocol. Read
[docs/architecture.md](https://github.com/eturkes/cement/blob/main/docs/architecture.md) and [docs/threat-model.md](https://github.com/eturkes/cement/blob/main/docs/threat-model.md) for the
full state model and trust boundaries.

## Examples

- [Hospital OCR](https://github.com/eturkes/cement/blob/main/examples/hospital_ocr/README.md): an offline walkthrough. Raw documents of three
  form layouts become proposals, a scripted learning pass learns a projection and promotes a version,
  a person switches it on, a later pass adds a case, and a pin rolls back to the first version. It
  ends by exporting the version and answering a document from the bundle alone.
- [Open WebUI](https://github.com/eturkes/cement/blob/main/examples/open_webui/README.md): Cement as a tool that the chat model calls, plus a
  filter that retains the model's answers for the learning pass. The learning pass and the switch
  also run inside Open WebUI. Every part installs by paste, and `local.py` starts a local instance
  for a test with a real model.
- [nucllei](https://github.com/eturkes/cement/blob/main/examples/nucllei/README.md): Cement as a skill in nucllei, the chat platform of the
  LLENS deployment. The chat model runs one sandbox command, and each user has a ledger of their own.
  The learning pass runs in the chat, and the user switches each function on with `/cement-switch`.
- [Caller outbox](https://github.com/eturkes/cement/blob/main/examples/outbox/README.md): a caller-side intent table and relay that keep an
  answer durable until Cement records it. It protects against a lost intent, and it shows why
  delivery is at least once.
- [Command candidate source](https://github.com/eturkes/cement/blob/main/examples/command_source/README.md): an optional source that runs a
  trusted adapter executable for one candidate. It also builds as a separate wheel, which adds the
  `cement-command-source` command.

## Development

```bash
uv sync
.agent/gate
```

`.agent/gate` runs every check in order. First come format, lint, and type check (`ruff`, `mypy`).
Then come the dependency audit (`uv audit`), the secret scan (`gitleaks`), a CI workflow scan
(`zizmor`), a shell script check (`ShellCheck`), and the skip census. The prose register audit, an
audit of definite references, and the report anchor check follow. The test suite, the package build,
and the spec check run last. The command prints each step's exit status and time, and it
exits 0 only when every step passes. CI runs the same command.

The runtime has no package dependencies. The development tools come from `uv sync`, and `uv_build`
produces the wheel and the source distribution.

## Deployment boundary

This release is a local control plane, not a network service or an ACL system. A new database starts
with mode `0600`, but evidence is plaintext. CLI actor names are recorded assertions, not
authentication. Cement makes no principal or permission decision. Authentication, authorization,
encryption, retention, signing, and tenant-aware API access all remain deployment responsibilities.

An exported bundle is a second deployment object with its own boundary. It executes without the
database, so the ledger's file permissions no longer protect it.
The bundle is plaintext and carries the exact inputs, the exact outputs, and the governance digests.
Classify it with your other sensitive data. Apply the same retention and disclosure rules.
`function export --out` writes atomically through a mode-0600 temporary file and refuses a non-regular
destination. The reader accepts one strict UTF-8 regular file and bounds it at 64 MiB, independently
from the 1 MiB bound on the evaluation input. `function eval` is ledger-free, not import-free: it opens
and reads the bundle path, and importing `cement_runtime` still loads `sqlite3`. A test runs
`function eval` in a child process with an audit hook that the child installs before it imports
`cement_runtime`. That hook records no database connection and no file open other than the bundle.
`python -S` does not remove it, because the child installs it itself. It does not see interpreter
startup, or file access that bypasses Python audit events.

Every library call and every CLI command assumes that your service already authorized access to the
exact partition. That applies to operation registration and revision, proposal review, compilation,
verification, promotion, challenge, evidence revocation, and artifact suspension. It applies equally to
every write route and to all reads. `operation revise`
always creates a semantic revision and retires older builds, even when threshold values stay unchanged.
The optional command candidate source in `examples/command_source/` uses a subreaper supervisor on
Linux to kill and reap detached descendants. This is lifecycle containment for a trusted provider
wrapper, not an arbitrary-code sandbox. If cleanup must survive simultaneous runtime/supervisor
termination or OOM, a host cgroup/container boundary remains necessary.
