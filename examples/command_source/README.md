# Command candidate source

This optional example runs a trusted adapter executable for one candidate. The Cement core does
not ship it: the core keeps only the `CandidateSource` protocol that `System.propose` calls.

## Use the example

Put this directory on the import path. Then pass a `CommandCandidateSource` to `System`. Run the
block from the repository root:

```python
import sys

sys.path.insert(0, "examples/command_source")

from command_source import CommandCandidateSource
from cement_runtime import CandidateRequest, System

source = CommandCandidateSource([sys.executable, "examples/command_source/example_adapter.py"])
system = System("cement.db", candidate_source=source)

candidate = source.propose(CandidateRequest("tenant-42", "support.reply", 1, {"domain": "value"}))
print(candidate.output)
```

`example_adapter.py` is a protocol stub, not an LLM. It echoes the input so that you can try the
protocol locally. The block prints `{'kind': 'echo', 'value': {'domain': 'value'}}`.

## Protocol

`CommandCandidateSource` invokes a trusted executable directly with `shell=False`. It writes one
compact JSON object to stdin:

```json
{
  "input": {"domain": "value"},
  "operation": "support.reply",
  "operation_revision": 1,
  "partition": "tenant-42",
  "protocol": "cement-candidate-v2"
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
stderr from stored errors, because stderr can contain secrets. Exit failure, timeout, malformed JSON,
and an oversized result are the four adapter failures Cement recognizes. Through
`System.propose`, the same failures raise `CandidateSourceError`. That call then writes no row, no
proposal, and no event.

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

The adapter receives no stored examples and cannot verify or promote its own proposal. Treat every
field of the input object as untrusted prompt content. Keep system instructions and provider
credentials out of that object. The command inherits the current environment by default, so it can
access deliberately configured credentials. The Python API can instead pass an exact environment
mapping.

`System.propose` invokes the adapter at most one time for each call, and it never retries. A
call that fails input validation or operation lookup invokes the adapter zero times. Provider
calls must create no external effects. The request carries no per-call identifier, so an adapter
that needs idempotency must derive its own key from the partition, the operation and the input.
