# M2.u4c6 acceptance contract — MAIN

Baseline `819f523`. Tier `kernel`. Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`; every
other tracked path stays byte-identical, `.agent/` records aside.

Scope = `function eval --bundle PATH --input JSON [--expected-function-hash HEX]`: the offline, ledger-free
leaf over `parse_function` + `evaluate` that closes the export -> eval loop and makes paragraph 1's
`once built and verified, that function is deterministic` executable with no ledger, no adapter, no LLM.

## Decision 1 — a miss is a negative verdict at exit 6, payload on stdout

RULING: hit -> `_Outcome(payload, status=0)`; miss -> `_Outcome(payload, status=6)`. Same payload shape both
ways, stdout both ways, stderr empty both ways.

The rule for the whole `function` group, stated once: **exit 6 = the command executed correctly and the
answer is negative.** Four leaves carry it — `verify-drafts` (a draft failed), `verify` (the committed set
failed), `export` (the set failed, so no bundle), `eval` (the input is outside the function's domain) — one
meaning, four payload shapes. A direct caller that selects the leaf discriminates on command + channel; a
generic status-only supervisor cannot, and u4c3's `Restart=on-failure` retry caveat continues to apply to
it unchanged.

Rationale facts:

- Reusing 6 keeps the group rule statable in one sentence. A dedicated code for the miss makes it `6 = a
  negative verdict, except eval`, and splits one semantic class across two codes exactly as u4c3 warned for
  sibling verbs over one field.
- Exit 0 with the verdict in the payload reserves `$?` for faults, the ordinary UNIX shape, but taxes every
  caller with a structural parser: `jq -e '.matched == true'` itself returns status 1 on a legitimate
  `false`, so even the payload route needs `jq -r` plus a string comparison.

Scope note: this record fixes the four shapes and the discriminator. `.agent/polish.md`'s exit-6 item stays
OPEN — its acceptance is conjunctive and the remaining two parts (a shared statement in `README.md` and
`docs/`, and the M2 claim replayer re-deriving it across all four leaves) belong to u5 and the review.

## Decision 2 — bundle digest failures keep the native `IntegrityError` -> exit 5 / `integrity`

RULING: no translation layer. `parse_function`'s exceptions reach `main` unchanged — `ValidationError` -> 2
`invalid`, `IntegrityError` -> 5 `integrity`. The leaf adds no exception class and no `main` clause.

The competing rule — a caller-supplied file is untrusted input, so `integrity` (which every shipped use
means as ledger corruption) misnames it — has a real cost on the other side: bundle self-integrity, path
failure, JSON grammar, document shape and request grammar would all collapse into exit 2, losing the one
distinction worth having, `this file was modified` vs `this file is malformed`.

Its premise fails on this leaf specifically. `eval` constructs no `System`, takes no `--db`, and opens no
connection. Source inventory of `IntegrityError` sites reachable here — exactly four, all below
`parse_function`:

| site | condition |
| --- | --- |
| `function.py:194` | entry input digest mismatch |
| `function.py:196` | entry output digest mismatch |
| `function.py:349` | embedded function digest mismatch |
| `function.py:353` | caller-held `expected_function_hash` mismatch |

`evaluate` has no `IntegrityError` site; its only validating call is `parse_json(entry.output.text)`
(`function.py:396`), which raises `ValidationError` alone. Within `function eval`, exit 5 therefore has
exactly one leaf-local meaning: **a digest check failed on the bundle you supplied.**

The repo-wide taxonomy is broader than that and is NOT the justification: `errors.py:24-25` states
`IntegrityError` as persisted content not matching its bound digest **or ABI**, and `system.py` also raises
it for invalid scalar fields, missing rows, noncontiguous ordinals, unknown statuses and state-binding
failures. The leaf-local four-site inventory above is what carries the ruling.

REJECTED — a third code / token `bundle_integrity`. It fragments `a digest check failed` across two codes,
so a caller wanting any integrity failure must match two, and it buys a distinction the command name already
carries. Cost is also real: a new token, a new class or translation, and a new `main` clause against a seam
three sub-units have kept byte-identical.

## Decision 3 — `--expected-function-hash` ships, and every payload carries the answering `function_hash`

RULING: optional `--expected-function-hash HEX`, forwarded UNVALIDATED into the same `parse_function` call
that produces the evaluated document; the emitted payload always carries the bundle's own `function_hash`.

The roadmap's u4c6 line named `--bundle PATH --input JSON` alone. Overruled; the roadmap line is amended at
close so exactly one public scope exists. Grounds:

1. Sibling consistency. `function verify OPERATION [--expected-function-hash HEX]` (u4c3) already exposes
   the same flag name, the same 64-hex grammar and the same caller-held content-binding purpose. The offline
   side is where transport is untrusted, so omitting it there is the inconsistency. The mismatch STATUS
   differs by design and is pinned as a paired row: `verify` mismatch = 6 (a verdict about the ledger set),
   `eval` mismatch = 5 (a bundle integrity failure). Callers cannot transfer status handling between them.
2. Binding inside one parse. The closest shipped substitute is `jq PATH` to read the hash, then `eval PATH`
   to use it; `jq` reads the path and `eval` reopens it, so the binding is not equivalent under concurrent
   replacement. The flag compares inside the same parse that supplies `evaluate`. This is a property of the
   ordinary path-reopen composition, not an impossibility claim: an inherited descriptor spelled
   `/proc/self/fd/N` is accepted by the reader and does stabilize the inode, at the cost of being
   platform-specific and operationally awkward.
3. Cost. Net +6 production lines.

`function_hash` in the payload is the load-bearing half. Without it, `eval` answers with
`matched`/`output`/`artifact_hash` and never says WHICH function answered, so no CLI output links an answer
back to the verified set. `sha256sum bundle.json` cannot substitute, since the function hash is a
canonical-content digest and two byte-different files can carry one function hash.

The guarantee, stated exactly: **if `function verify` exits 0 with hash H and `eval` reports H, the
evaluated normalized content equals that verified snapshot under the SHA-256 identity assumption.** It does
NOT prove bundle origin — `function.py:64-65` states the unkeyed hash binds normalized content, not origin —
and it requires a PASSING verify, since that command can report a diagnostic hash on a failed verdict.

Payload = an explicit 4-key projection, `_emit`'ed as a plain dict:

```
{"artifact_hash": <str|null>, "function_hash": <str>, "matched": <bool>, "output": <JSON|null>}
```

This is the u4c1-A exception, not a departure: emit-the-model applies where the model carries what the
operator needs, and `FunctionMatch` has no field for document identity — the same reason `function verify`
projects four fields and `function inspect` projects the manifest. Two distinct mitigations, both mandatory,
because one golden key-set test cannot do both jobs:

- Key-set golden on both verdicts -> CLI schema expansion stays deliberate.
- `dataclasses.fields(FunctionMatch)` introspection asserted as a SUBSET of the payload keys -> a field
  added to the library model fails the test instead of being silently dropped by the fixed projection.

## Decision 4 — the reader: one open, `S_ISREG`, a size pre-check, and a bounded read that is authoritative

RULING, `_read_function_bundle(value: str) -> str`. Name and signature are binding, because tests patch the
helper; physical placement and comment shape are non-decisions.

1. `os.open(value, os.O_RDONLY | os.O_NONBLOCK)`. `O_NONBLOCK` is what makes step 2 reachable on a FIFO with
   no writer instead of hanging there.
2. `os.fstat(descriptor)`; `stat.S_ISREG` required. Identity is graded on the DESCRIPTOR, before any
   buffered stream: `os.fdopen` refuses a directory itself, so grading after it reports a read failure where
   the honest verdict is the file type.
3. Size pre-check `st_size > FUNCTION_MAX_BYTES` -> reject. An optimization, not the gate: max+1 rejects in
   0.007 s at +256 KiB growth versus 0.154 s at ~88 MiB without it, and a 4x oversize file costs the same as
   max+1 either way.
4. `os.fdopen(descriptor, "rb")` only after steps 2 and 3 pass, with `except BaseException:
   os.close(descriptor); raise` around every pre-handover failure, mirroring `_write_export`. After the
   handover the stream owns the descriptor and `with stream:` closes it.
5. `stream.read(FUNCTION_MAX_BYTES + 1)`; `len(raw) > FUNCTION_MAX_BYTES` -> reject. This is the
   authoritative gate: a regular file may grow between steps 3 and 5, and only the bounded read holds under
   that race. Both checks raise the same message.
6. `raw.decode("utf-8")`, strict.

The catch is `(OSError, ValueError)` at both boundaries, guarded by an earlier `except ValidationError:
raise`. TOTALITY is the reason, and it is not optional: `os.open` raises base `ValueError` on an embedded
NUL and `UnicodeEncodeError` (a `ValueError` subclass) on a lone surrogate, neither of which is an `OSError`.
Catching `OSError` alone lets both escape `main` as a traceback. `ValidationError` also subclasses
`ValueError`, so without the guard clause the residual catch rewrites this helper's own regular-file and
oversize verdicts as read failures.

Exact messages, all `ValidationError` -> exit 2 `invalid`. The split is by WHERE the failure lands, because
several object types never reach the identity test:

| stage | condition | message |
| --- | --- | --- |
| `os.open` fails | `OSError` (ENOENT, ENOTDIR, EACCES, ELOOP, ENXIO — includes an AF_UNIX socket and a trailing slash on a regular file), `ValueError` (embedded NUL), `UnicodeEncodeError` (lone surrogate) | `function bundle could not be read` |
| open succeeds, `fstat` nonregular | directory, FIFO, character or block device | `function bundle path must identify a regular file` |
| `fstat` / `read` fail | `OSError` | `function bundle could not be read` |
| size | `st_size` or read length exceeds the cap | `function bundle exceeds 67108864 bytes` |
| decode | `UnicodeDecodeError` | `function bundle is not valid UTF-8` |

Regular-file identity is REQUIRED, and it is a deliberate capability cut. A FIFO or `/dev/stdin` whose
producer never closes blocks forever, and this leaf has no read timeout. u4c5b's `--out` writer takes the
same `S_ISREG` posture. The asymmetry with that writer is intentional: `--out` refuses a SYMLINK because
writing through one destroys an unintended target, while `--bundle` follows a symlink to a regular file
because reading through one destroys nothing — non-destructive relative to REPLACEMENT only; reading still
discloses a redirected target and updates access metadata, and it authenticates no origin. Where path
substitution matters, `--expected-function-hash` is the answer.

The cut is wider than the ledger argument suggests, so state it plainly: `--bundle <(cement function export
OP)` (process substitution) and `--bundle /dev/stdin` fed by a pipe are both refused, and
`cat bundle.json | ... --bundle /dev/stdin` is a genuinely ledger-free route that this policy removes.
`--bundle /dev/stdin` still works when stdin is a REGULAR file (`< bundle.json`).

## Decision 5 — failure precedence: request-local input before external bundle work

RULING, one order, deterministic and stated:

1. `--input` parse + canonicalize (no filesystem, bounded at `DEFAULT_MAX_BYTES`).
2. bundle read (Decision 4).
3. `parse_function`, including `expected_function_hash`.
4. `evaluate`.

This is u4c5b's ruling applied to a reader: a structurally unusable request is repaired by no amount of work
downstream of it. It is NOT a cost ordering — a near-limit valid `--input` costs ~0.02 s to parse and
canonicalize twice while a missing path costs ~0.00002 s to reject, so step 1 can be ~1000x more expensive
than step 2. Locality and repair order carry the rule; strict cost monotonicity is false.

Step 3's INTERNAL order is delegated to `parse_function` and is binding as it stands: source bytes and JSON
grammar, then shape/ABI/entries and per-entry digests, then the embedded function hash, then
`expected_function_hash` grammar, then the expected-hash comparison. Every bundle defect therefore outranks
a malformed expected hash. The leaf must forward the flag unvalidated; pre-grading it in the CLI reverses
the reported cause.

Accepted cost of input-first, stated exactly: **no bundle integrity guarantee is made on an invocation whose
input fails.** A later valid-input invocation is required to surface tampering, and nothing forces one — a
wrapper can stop after exit 2 or resupply the same malformed input forever.

## Decision 6 — `--bundle -` is an ordinary filename

RULING: no special case. `-` names a file called `-`; with no such file the leaf exits 2 with `function
bundle could not be read`, and with one it reads it like any other path. Stdin is reserved exclusively for
`--input`. A literal dash file is spelled `-`, `./-` or an absolute path.

REJECTED: intercepting `-` with a dedicated message. `_input` already special-cases the VALUE `-`, so the
"only special case" objection does not hold; the real ground is that stdin has one owner on this leaf, and
that interception makes a legitimately named file unreachable under its own name.

Pinning requires BOTH rows, because the absent-file row alone is satisfied by a hard-coded rejection: absent
`-` -> read error, AND a real bundle at cwd basename `-` -> ordinary hit.

## Decision 7 — input canonicalization keeps the default channel, spelled implicitly

RULING: `evaluate(document, input_json=canonicalize(_input(args.input)))`, no explicit bounds kwargs.

There is NO reachability gap. `_normalize` canonicalizes every entry `input` with DEFAULT bounds
(`function.py:191`), and `build_function` does the same (`function.py:299-300`), so the 64x/10x/+3-depth
envelope applies to the aggregate document and never to one lookup key. Sharper: for every entry input
accepted by `_normalize`, its canonical text C is itself a valid JSON source of the same value within
`DEFAULT_MAX_BYTES`, depth 64 and 100,000 items, so `parse_json(C)` succeeds under the same defaults. A
verbose SOURCE spelling of that value can exceed the byte bound; the VALUE always remains supplyable.
Passing `FUNCTION_*` bounds here would widen a channel with nothing on the other side to reach.

Qualification: "fits `--input`" means the input SURFACE, not one argv word. Linux refuses a single exec
argument well below 1 MiB on this host (~120 KB launches, ~140 KB fails with E2BIG), so a near-limit value
must arrive through `--input -`. In-process `main([...])` bypasses that wall, so a byte-bound test that uses
only the in-process runner must pin the pair through stdin.

Accepted cost, recorded: `_input` discards the `CanonicalJSON` that `parse_json` already built, so the value
is canonicalized twice. Rejected fixes: a private stdin-duplicating helper (duplicates the three-branch
transport `_input` owns), and changing `_input`'s return type (touches four shipped leaves for a second pass
over at most 1 MiB).

## Probe corpus — expected outcomes are contract, not suggestion

Bundles are produced by the shipped pipeline: `operation register` -> `handle` -> `proposal review`
(x2 confirmations) -> `compile` -> `function verify-drafts` -> `function inspect` -> `function promote` ->
`function export OP --out PATH`. Corruption fixtures edit that exported text.

| invocation | exit | stdout | stderr |
| --- | --- | --- | --- |
| hit | 0 | 4-key payload, `matched: true`, `output`/`artifact_hash` non-null | empty |
| miss | 6 | 4-key payload, `matched: false`, `output`/`artifact_hash` null, same `function_hash` | empty |
| hit whose stored `output` is JSON `null` | 0 | `output: null`, `matched: true`, `artifact_hash` non-null | empty |
| zero-entry exported bundle, any input | 6 | 4-key miss payload with the bundle's `function_hash` | empty |
| hit, `--input -` (buffer-bearing stdin) | 0 | identical to the literal-value hit | empty |
| hit, `--input -` (text-only stdin, no `.buffer`) | 0 | identical to the literal-value hit | empty |
| hit, matching `--expected-function-hash` | 0 | identical to the plain hit | empty |
| `--expected-function-hash` off by one hex digit | 5 | empty | `integrity` / `function does not match expected_function_hash` |
| `--expected-function-hash` not 64 hex | 2 | empty | `invalid` / `expected_function_hash must be a SHA-256 hex digest` |
| entry `output` VALUE changed, its `output_hash` left stale, outer hash recomputed | 5 | empty | `integrity` / `function entry <i> output digest mismatch` |
| entry `input` VALUE changed, its `input_hash` left stale, outer hash recomputed | 5 | empty | `integrity` / `function entry <i> input digest mismatch` |
| embedded `function_hash` byte flipped | 5 | empty | `integrity` / `function hash mismatch` |
| empty file, and the exact bytes `not-json` | 2 | empty | `invalid` / `invalid JSON: Expecting value: line 1 column 1 (char 0)` |
| bytes `ff fe` | 2 | empty | `invalid` / `function bundle is not valid UTF-8` |
| valid JSON, wrong shape (`{}` / `[]`) | 2 | empty | `invalid` / `invalid function: expected keys ['abi', 'canonicalizer', 'entries', 'function_hash', 'scope']` |
| duplicate source key | 2 | empty | `invalid` / `duplicate JSON object key: '<key>'` |
| `abi` altered | 2 | empty | `invalid` / `unsupported function ABI` |
| `canonicalizer` altered | 2 | empty | `invalid` / `unsupported function canonicalizer` |
| exactly 67,108,864 bytes | reader ADMITS it and calls `parse_function` | outcome is the fixture's | a valid exact-max source hits or misses; a sparse NUL fixture is a parse error |
| 67,108,865 bytes | 2 | empty | `invalid` / `function bundle exceeds 67108864 bytes` |
| missing path | 2 | empty | `invalid` / `function bundle could not be read` |
| dangling symlink | 2 | empty | `invalid` / `function bundle could not be read` |
| search-denied ancestor (mode `000`) | 2 | empty | `invalid` / `function bundle could not be read` |
| AF_UNIX socket, trailing slash on a regular file, embedded NUL, lone surrogate, `""` | 2 | empty | `invalid` / `function bundle could not be read` |
| injected `OSError` at `open`, `fstat`, `fdopen`, or the stream's `read` | 2 | empty | `invalid` / `function bundle could not be read` |
| `--bundle -` with no file named `-` | 2 | empty | `invalid` / `function bundle could not be read` |
| `--bundle -` with a valid bundle at cwd basename `-` | 0 | identical to the direct hit | empty |
| directory, FIFO with no writer, `/dev/null`, `/dev/zero` | 2 | empty | `invalid` / `function bundle path must identify a regular file` |
| symlink -> valid bundle | 0 | identical to the direct hit | empty |
| `--input` malformed AND bundle tampered | 2 | empty | `invalid` / the `--input` error |
| `--input` malformed AND bundle missing / a directory | 2 | empty | `invalid` / the `--input` error |
| wrong-shape bundle AND malformed `--expected-function-hash` | 2 | empty | `invalid` / the shape error |
| entry-digest tamper AND malformed `--expected-function-hash` | 5 | empty | `integrity` / the entry digest error |
| valid bundle AND malformed `--expected-function-hash` | 2 | empty | `invalid` / the grammar error |
| `--input` decimal or exponent (`1.0`, `1e0`) | 2 | empty | `invalid` / `cement-json-v1 rejects decimal/exponent number '<t>'; encode it as a string` |
| `--input` exceeding `DEFAULT_MAX_BYTES` | 2 | empty | `invalid` / the existing `_input` bound message |
| repeated `--bundle` / `--input` / `--expected-function-hash` | last occurrence alone is graded | earlier values are never opened or parsed | — |
| missing `--bundle` / missing `--input` | 2 | empty | `invalid` / argparse text, MAIN-verified live |
| `function eval` with no `--db` and no `--partition`, or with an unusable `--db` | as above | as above | as above |

Library-owned bounds, discharged by `tests/test_function.py` rather than re-proved here: `FUNCTION_MAX_ENTRIES`
50,000 accepted / 50,001 rejected with `function exceeds 50000 entries` (~31 MB and ~3 s to build, too heavy
for the CLI suite), and `DEFAULT_MAX_ITEMS` 100,000 / +1. The CLI owes one forwarding case, not a rebuild.

## Behavioral pins beyond the table

1. LEDGER FREEDOM, by construction failure: with `System.__init__` AND `sqlite3.connect` patched to raise, a
   hit still exits 0 with byte-identical stdout. Patching `System` alone leaves a direct store or connection
   unproved. Import-graph inspection proves nothing — `cement_runtime.function` reaches `sqlite3` through the
   package `__init__`, and the claim is no instance, no path, no connection.
2. EXIT 6 IS EXACTLY THE MISS, as a branch predicate: `status == 6` iff `evaluate` returns normally with
   `matched is False`; every mapped exception keeps its existing code. Injected `FunctionMatch` values in
   both polarities and each mapped exception pin it. Finite fixtures cannot establish a universal over all
   inputs, so the pin binds the predicate, not the input domain.
3. `function_hash` in the payload EQUALS the value a PASSING `function verify` reports for the same set, and
   equals the bundle's own embedded `function_hash`, on both the hit and the miss. The emitted value is read
   from the `FunctionDocument` that `parse_function` returned, not re-extracted from the raw text; a boundary
   spy where reader text and parsed identity differ pins the source.
4. MULTI-ENTRY, MIDDLE AND LAST: corruption probes use a >=3-entry bundle and corrupt the middle AND the
   last entry in separate probes; a one-entry bundle proves only that one case can be rejected.
5. TAMPER ISOLATION, by construction: parse the exported document, change an entry's `input` or `output`
   VALUE, leave that entry's declared `input_hash`/`output_hash` stale, recompute ONLY the outer
   `function_hash` over hash-excluded content, reserialize. A raw byte flip is insufficient — it can alter
   whitespace, an equivalent escape, UTF-8 validity or a different field, and then another rejecter fires
   first and the per-entry check stays unpinned.
6. EXACTNESS OF THE LOOKUP: canonical-equivalent input (reordered object keys, `1` vs ` 1 `) is a HIT;
   near-collisions (`echo_1` vs `echoX1`, case variants, `1` vs `"1"`, `{"x":1}` vs `{"x":1,"y":null}`, `{}`)
   are MISSES. `1.0` and `1e0` are NOT misses: `cement-json-v1` rejects the token before evaluation, so they
   exit 2 as invalid requests.
7. ADJACENT PAIRS AT EVERY WALL: 67,108,864 admitted by the reader / 67,108,865 rejected for the bundle;
   `DEFAULT_MAX_BYTES` accepted / +1 rejected for `--input`, pinned through stdin because argv cannot carry
   the maximum; depth 64 accepted / 65 rejected. Bundle-size fixtures are built with multibyte content
   somewhere, so a byte cap cannot pass as a character cap.
8. BOUNDED MATERIALIZATION: the reader binds `FUNCTION_MAX_BYTES + 1` exactly. Pin it with a spy wrapping
   the stream, since an unbounded `read()` returns byte-identical results for every in-bounds fixture and
   `io.BufferedReader.read` cannot be replaced on the instance.
9. VALIDATOR RESULTS ARE BOUND, asserted by identity (`is`): the document `parse_function` returns is the
   one `evaluate` receives, and the canonicalized input is the one passed as `input_json`. A
   statement-position call proves only well-formed text.
10. PRECEDENCE IS TESTED DIRECTLY, not inferred from source order: input-vs-tampered-bundle,
    input-vs-missing-path, input-vs-directory, bundle-shape-vs-expected-hash-grammar,
    entry-digest-vs-expected-hash-grammar, valid-bundle-vs-expected-hash-grammar, and argparse-vs-all.
11. MOCK THE LIBRARY BOUNDARY: exit-map probes patch `parse_function` / `evaluate` / the reader helper, never
    `cli._run`, which is the branch under test. The map must not widen: an unmapped exception class raised by
    `evaluate` still escapes `main`.
12. THE OTHER 27 LEAVES ARE UNCHANGED: `_Outcome`, `_emit`, `main`'s clause list and every existing mapping
    stay byte-identical; the count is derived from `_parser()` in the test rather than written down, and at
    least one shipped leaf pins unchanged exit code and stdout bytes. The diff proves branch bodies
    unchanged; the byte pin is sampled behavioral evidence, not a proof over all 27.
13. `--help` for the new flags reuses the shipped register rather than inventing one: `--input` carries the
    same string as `handle --input` verbatim, help fragments are <=20 words, carry no em dash and no
    `simply`/`robust`/`seamlessly`/`leverage`, and open lowercase EXCEPT where a term the project already
    capitalizes (`JSON`, `SQLite`) starts the line. The test asserts the reuse and those properties; there is
    no repo-wide help linter to defer to.

## Invariant surfaces

- `git diff --name-only 819f523..<unit commit>` touches exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py`, and `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/` stay
  byte-identical.
- No new dependency; imports stay stdlib plus in-package.
- `main` gains no catch-all: a corrupt persisted scalar still escapes elsewhere in the CLI, and no test here
  may claim total error mapping over corrupt ledgers. `function eval` reads no ledger, so that limit is
  outside this leaf, not fixed by it.

## Known limits, to be carried into the roadmap at close

- Exit 6 now names four objects across four leaves, one meaning and four payload shapes, discriminated by
  command and channel rather than by `$?`. A generic status-only supervisor cannot discriminate.
- Exit 2 on this leaf covers argparse faults, `--input` faults, five reader conditions and every structural
  bundle fault, separated only by message.
- `--expected-function-hash` mismatch is exit 5 here and exit 6 on `function verify`. The flag's grammar and
  purpose transfer between the siblings; its failure status does not.
- A FIFO, socket or device path is refused, so no streaming or process-substitution route exists — including
  the ledger-free `cat bundle.json | ... --bundle /dev/stdin`.
- The size pre-check is advisory; the authoritative bound is on the MATERIALIZED bytes. `raw` is at most
  `FUNCTION_MAX_BYTES`, and growth observed by the bounded read yields cap+1 and is rejected. Growth after
  the read observes EOF is outside the consumed snapshot and is not detected.
- One open prevents path-reopen substitution. It takes no lock and snapshots no content, so in-place writes
  to the opened inode can be read; the self and expected hashes then reject the materialized bytes rather
  than preventing the race.
- `S_ISREG` admits procfs, FUSE and network-backed regular files, and `O_NONBLOCK` does not stop those from
  blocking. Regular-file identity is not a timeout guarantee.
- Repeated flags are last-wins by inherited argparse behavior; earlier values are never opened or graded.
  Long-option abbreviation stays inherited and unpinned, as in prior units.
- `--bundle /dev/stdin` combined with `--input -` has no two-value framing and is unsupported; use a literal
  `--input` value when the bundle arrives on redirected regular stdin.
- `_input` does not translate an `OSError` from `sys.stdin[.buffer].read`; `eval` inherits that raw-exception
  limit unchanged rather than adding a leaf-local message.
- Payload and status guarantees assume a healthy stdout. `_emit` performs no explicit flush, so a buffered
  embedding stream may retain data after `main` returns, and a `BrokenPipeError` or an exit-time flush
  failure can replace the intended 0/6 — the same cross-resource limit recorded for u4c5b's file receipt.
- Stored output is bounded by default canonicalization, but pretty `_emit` expands it; no exact stdout byte
  cap is promised.
- Error mapping is not total over process failure: `MemoryError`, `KeyboardInterrupt` and other
  non-operational `BaseException` classes stay unmapped.
- `--expected-function-hash` binds identity only when the operator obtained the hash independently; copied
  out of the same bundle it adds nothing, which is the library's own statement.
- The input value is canonicalized twice per invocation.

## Gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, rerun by MAIN
from committed state at close.
