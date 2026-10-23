# Caller outbox

This optional example keeps a submission intent durable until Cement records it. Cement owns no
request lifecycle, so a caller that must not lose an answer keeps its own record and delivers it
later. The example gives lost-intent protection only. It does not make a submission exactly-once.

## Record and relay intents

`outbox.py` keeps one row for each intent in a SQLite table. In a real caller, put this table in
the caller's own database. Write each intent in the same transaction as the state that creates it.

- `Outbox.record` binds an intent ID to its content: the partition, the operation, the operation
  revision, the canonical input, the candidate output and provenance, and the source revision. A
  second call with the same ID and the same content changes nothing. A call with the same ID and
  other content raises `IntentConflictError` and writes nothing.
- `Outbox.relay` delivers each pending intent through `System.submit_proposal`, in ID order. Then
  it marks the intent as delivered. The provenance of each proposal names its intent and the
  source revision.
- When the current operation revision differs from the intent revision, the relay marks the intent
  as stale and submits nothing. `submit_proposal` takes no expected revision. Thus a revision
  change after this check and before `submit_proposal` binds the proposal to the new revision.

## Delivery is at least once

A crash after Cement commits a proposal and before the outbox marks the intent as delivered leaves
the intent pending. The next relay delivers it again:

- A keyed relay (the default) sends `outbox:<intent ID>` as the `source_id`. Cement refuses the
  second delivery with `ConflictError`, and the error names the first proposal. The relay marks the
  intent as delivered with that proposal, so the ledger keeps one proposal.
- An unkeyed relay (`keyed=False`) sends no `source_id`. The second delivery writes a second
  proposal with the same content.

Cement compares a `source_id` only inside one partition and operation. An intent that never
reaches the outbox is lost, and a relay that never runs delivers nothing.

The probe in `tests/test_outbox_example.py` stops a real relay process between the two commits and
shows both results. Run it from the repository root:

```sh
uv run python -m unittest tests.test_outbox_example
```
