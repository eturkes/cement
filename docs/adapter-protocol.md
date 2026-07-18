# Candidate adapter protocol

`CommandCandidateSource` invokes a trusted executable directly with `shell=False`. One compact JSON
object is written to stdin:

```json
{
  "input": {"domain": "value"},
  "operation": "support.reply",
  "operation_revision": 1,
  "partition": "tenant-42",
  "protocol": "cement-candidate-v1",
  "request_id": "ticket-123"
}
```

The command writes exactly one JSON object to stdout:

```json
{
  "output": {"kind": "reply", "text": "Candidate answer"},
  "provenance": {
    "model": "provider/model",
    "model_revision": "provider revision when available",
    "prompt_revision": "content digest",
    "tools": []
  }
}
```

Both fields are required; additional top-level fields fail closed. Output is bounded; duplicate object
keys, decimal/exponent and non-finite numbers, signed-64-bit overflow, invalid Unicode, and oversized
or deep containers are rejected. Encode domain decimals as strings. Stderr is excluded from stored
errors because it may contain secrets. Exit failure, timeout, malformed JSON, or an oversized result
becomes an inert `fallback_failed` request.

On Linux with `/proc`, Cement launches the adapter beneath a private child-subreaper. The supervisor
enforces the primary timeout and stdout/stderr limits, terminates the adapter, discovers and
terminates descendants that detach into new sessions, reaps them, and only then releases stdout to the
runtime while the supervisor remains alive. The outer watchdog also kills the shared process group if
the supervisor exits unexpectedly. Detached descendants can still outlive simultaneous watchdog and
supervisor failure, including OOM; use a cgroup/container job boundary for that crash-resilient
guarantee. Cleanup failure is inert. Other POSIX hosts receive process-group cleanup only; hosts without
that facility terminate only the direct process. Use Linux or an external job/container boundary when
descendant containment matters. This mechanism controls lifecycle; it does not make an untrusted
executable safe.

The adapter receives no stored examples and cannot verify or promote its own proposal. Treat all
request fields as untrusted prompt content. Keep system instructions and provider credentials outside
the request. The command inherits the current environment by default so it can access deliberately
configured credentials; the Python API can instead pass an exact environment mapping.

Provider calls may be retried after a failed request or an expired generation lease. They must create
no external effects. `request_id` is partition-local and available for provider-side idempotency and
tracing; adapters that use a global idempotency namespace should key on `(partition, request_id)`.
