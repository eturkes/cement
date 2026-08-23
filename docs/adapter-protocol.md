# Candidate adapter protocol

`CommandCandidateSource` invokes a trusted executable directly with `shell=False`. Cement writes one
compact JSON object to stdin:

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

The response must contain both fields. Additional top-level fields fail closed. Cement bounds the
output. It rejects duplicate object keys, decimal/exponent and non-finite numbers, signed-64-bit
overflow,
invalid Unicode, and oversized or deep containers. Encode domain decimals as strings. Cement excludes
stderr from stored errors, because stderr can contain secrets. Through `handle`, exit failure,
timeout, malformed JSON, or an oversized result becomes an inert `fallback_failed` request. Through
`System.propose`, the same failures raise `CandidateSourceError`. That call then writes no request
row, no proposal, and no event.

On Linux with `/proc`, Cement launches the adapter beneath a private child-subreaper. The supervisor
enforces the primary timeout and the stdout/stderr limits. It terminates the adapter. It discovers and
terminates descendants that detach into new sessions, then reaps them. It releases stdout to the
runtime only after that cleanup, and it stays alive throughout. If the supervisor exits unexpectedly,
the outer watchdog also kills the shared process group. Detached descendants can still outlive
simultaneous watchdog and supervisor failure, including OOM. Use a cgroup/container job boundary for
that crash-resilient guarantee. Cleanup failure is inert. Other POSIX hosts receive process-group
cleanup only. Hosts without that facility terminate only the direct process. When descendant
containment matters, use Linux or an external job/container boundary. This mechanism controls
lifecycle. It does not make an untrusted executable safe.

The adapter receives no stored examples and cannot verify or promote its own proposal. Treat all
request fields as untrusted prompt content. Keep system instructions and provider credentials outside
the request. The command inherits the current environment by default, so it can access deliberately
configured credentials. The Python API can instead pass an exact environment mapping.

Through `handle`, Cement can invoke the adapter again after a failed request or an expired generation
lease. `System.propose` invokes the adapter one time for each call, and it never retries. Provider
calls must create no external effects. `request_id` is partition-local and available for provider-side
idempotency and tracing. Adapters that use a global idempotency namespace must key on
`(partition, request_id)`.
