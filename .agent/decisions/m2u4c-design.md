# M2 u4c design record — MAIN arbitration

Baseline HEAD `14255dd`; `git diff --stat 62e6d09..HEAD -- src tests pyproject.toml README.md docs examples`
is empty, so every anchor here holds under the u4b unit commit too. Gates green under MAIN's own run:
`Ran 353 tests in 175.582s / OK`, `uv build` exit 0.

Facts live in `.agent/decisions/m2u4c-surface.md` — CLI anatomy, consumed-API inventory with verbatim
signatures, return-model field lists, serialization hazards, offline-evaluation constants, error taxonomy,
stored-scalar audit. This record holds judgment only and never restates a fact that file carries.

## Decision 1 — five commands understate the spine; eight are mandatory

`src/cement_runtime/cli.py` carries zero references to any function-layer API (exact search over
`function_report|function_receipts|latest_function_receipt|inspect_function_promotion|promote_function|verify_function|reconstruct_function_receipt|verify_drafts|parse_function|build_function`
returns rc 1; positive control finds `System` at `src/cement_runtime/cli.py:23` and
`src/cement_runtime/cli.py:207`). All of u1–u4b is CLI-unreachable at baseline.

The roadmap's five names (`show`, `export`, `eval`, `verify`, `promote`) leave the milestone's own measured
gap half open. That gap is stated at `.agent/roadmap.md:15-16`: `verify <artifact_id>` and
`promote <artifact_id> --scope-hash` are per entry, so N situations cost N human-typed hashes. Five commands
close the promotion half and leave the verification half exactly as it was, because nothing exposes
`System.verify_drafts` — the batch verifier u3a built for this purpose. Two further APIs are load-bearing
for commands the five names do include: `inspect_function_promotion` is the sole producer of the prospective
hash `promote_function` requires the operator to repeat, and `function_receipts` is the sole way to learn a
receipt ID that `show --receipt-id` / `export --receipt-id` accept.

Mandatory surface, eight commands:

| command | library surface | why spine |
| --- | --- | --- |
| `function show OPERATION [--receipt-id ID] [--projection-limit N]` | `function_report` | operator observability over both temporal anchors |
| `function receipts OPERATION [--operation-revision N] [--before-sequence N] [--limit N]` | `function_receipts` | without it no receipt ID is obtainable, so every historical mode is unusable |
| `function verify-drafts OPERATION --actor ACTOR` | `verify_drafts` | the verification half of the N-hashes gap; its absence leaves `.agent/roadmap.md:15-16` false |
| `function verify OPERATION [--expected-function-hash HEX]` | `verify_function` | aggregate committed-set verification, P1–P6 |
| `function inspect OPERATION` | `inspect_function_promotion` | sole producer of the hash `promote` demands; promotion is unusable without it |
| `function promote OPERATION --expected-function-hash HEX --actor ACTOR` | `promote_function` | one repeated hash replaces N typed scope hashes |
| `function export OPERATION [--receipt-id ID] [--out PATH]` | `verify_function` + `reconstruct_function_receipt` | produces the sealed ledger-free bundle |
| `function eval --bundle PATH --input JSON [--expected-function-hash HEX]` | `parse_function` + `evaluate` | proves determinism with no ledger, no adapter, no LLM |

Deliberately omitted, with reasons: `latest_function_receipt` (`receipts --limit 1` reaches the same newest
row; the two differ only in unregistered-operation and no-current-receipt diagnostics, which `show` already
surfaces), `reconstruct_function_receipt` as its own verb (historical `show` returns its metadata and
historical `export` its bytes — a third consumer adds a verb without adding capability),
`build_function` / `validate_function` (operators must not hand-author ledger-bound documents; every
consumer revalidates). Each stays library-only for M2; promoting any of them later is additive.

## Decision 2 — u4c splits six ways

Sizing recheck, as `.agent/roadmap.md:341-343` requires at u4c's open. Full mandatory surface estimates at
**244–365 production and 3,070–4,540 test lines**. Against recorded actuals — u4a `99 + 1,163` at
`impl=59%` / `main=93%`, u4b `776 + 3,725` at `impl=92%` / `main=81%`, u3b2 `411 + 3,225` at `impl=90%` —
u4c is ~2.5× u4a's production and ~2.6× its tests. Under the current authorship split the two halves add in
one window rather than alternating, and u4a's own halves already summed to 152% of one window, u4b's to
173%, u3b2's to 183%. **Verdict: does not fit, decisively.** The 175.582 s full-suite wall-clock compounds
this on iteration count without changing the arithmetic.

| unit | scope | est. production / tests | tier |
| --- | --- | --- | --- |
| u4c1 | shared scaffolding + `function show` (current anchor) | 46–69 / 500–740 | kernel |
| u4c2 | `function receipts` + `show --receipt-id` historical mode | 34–52 / 480–720 | kernel |
| u4c3 | `function verify-drafts` + `function verify` | 44–66 / 620–920 | kernel |
| u4c4 | `function inspect` + `function promote` | 36–55 / 510–760 | kernel |
| u4c5 | `function export` | 46–67 / 520–760 | kernel |
| u4c6 | `function eval` | 48–70 / 560–820 | kernel |

Order `u4c1 → u4c2 → u4c3 → u4c4 → u4c5 → u4c6`. Landing is sequential because every unit edits `_parser`,
`_run`, `main`, and the CLI test class; analysis and review parallelize freely by command. Discovery is
ordered second so `--receipt-id` stops being a flag with no operator route one unit after it appears.
Semantic edges: `inspect` → `promote` (expected hash), `receipts` → historical `show`/`export`,
`verify_function` pass → live `export`.

Cheapest cut, and why not a coarser one: a three-slice plan (ledger reads / ledger mutations / ledger-free
bytes) is more cohesive per slice, but each slice then bundles several independent mutation matrices and
lands at or past u4a's size, which already failed the arithmetic above. Re-reading `cli.py` (360 lines) and
`tests/test_cli.py` (121 lines) costs a few thousand tokens per unit — unlike the earlier u4a/u4b/u4c cut,
where re-reading `system.py` and `test_system.py` was the dominant cost and forced coarse slices. Small
files make the fine cut nearly free, and the chain rule lets one session close two sub-units when budget
allows, so undershooting a unit costs far less than overrunning one.

Strongest counterargument, recorded: six slices reload the same files, serialize merge pressure, and risk
freezing vocabulary piecemeal — a later unit may want a flag name an earlier one already shipped. Mitigated
by Decision 3, which freezes the shared vocabulary in u4c1 rather than letting it accrete.

## Decision 3 — u4c1 freezes the cross-unit interfaces

These bind every later sub-unit and are not re-litigated per unit.

**Outcome protocol.** `_run` keeps returning bare values for the 20 existing leaves, whose behavior stays
byte-identical. New leaves needing a non-default outcome return one frozen slotted `_Outcome(payload,
status=0, raw=None)`; `main` writes `raw` when present, emits `payload` through `_emit` unless it is the
no-payload sentinel, and returns `status`. A bare return keeps today's `_emit` + exit 0. This is the single
seam supporting all three shapes u4c needs — ordinary JSON, JSON with an explicit process status, and raw
document bytes — and no command may bypass it with a direct `sys.exit` or a private write.

**Raw byte channel.** `raw` carries `str` (a `FunctionDocument.text`), written as
`sys.stdout.buffer.write(text.encode("utf-8"))` when a buffer exists and `sys.stdout.write(text)` when it
does not, mirroring the existing text-stream accommodation at `src/cement_runtime/cli.py:156-174`. Exactly
the document bytes, nothing appended — `_emit`'s trailing newline is a JSON-mode convention and must not
reach an exported artifact, which has to round-trip through `parse_function` unchanged.

**Parser conventions.** `function` is a required nested subparser (`dest="function_command"`), matching the
five existing nested groups. `OPERATION` is positional everywhere it appears. Actor-bearing writes take
`--actor` required, matching root `promote` rather than root `verify`'s defaulted actor, because every
function-set write records provenance. Every `limit`-family flag passes the operator's value through
unclamped so the library's own `1..10_000` validation raises `ValidationError`; the CLI never clamps and
never substitutes its own bound.

**Payload projection.** No command emits a model that nests a `FunctionDocument`. `FunctionVerification`
carries `document: FunctionDocument | None`, `FunctionReconstruction` carries `document`,
`FunctionPromotionManifest` carries BOTH `text: str` and `document: FunctionDocument`, and `_emit`'s
`asdict` on a document measures a 3.999x compact expansion while also exposing the private `_FunctionCase`
cache. Emitting one directly would put up to 64 MiB of document through a ~4x JSON expansion on a status
line. Each command therefore names an explicit bounded projection of the fields an operator needs, and the
document itself reaches stdout only through `export`'s raw byte channel, which writes `text` verbatim with
no expansion. This is a hard interface rule, not a size heuristic: `_emit` stays for non-document models.

**Test harness.** `tests/test_cli.py`'s runner JSON-decodes any stdout (`tests/test_cli.py:19-24`), which
cannot express raw bytes or a nonzero status carrying stdout. u4c1 replaces it with a runner returning
status, raw stdout text, decoded JSON where applicable, and stderr, and every later unit uses that one
runner.

## Decision 4 — `function verify` exits 6 when the set fails verification

Measured precedent, and it is the opposite of what u4c should do: root `verify` today returns a failing
report with exit 0. `System.verify` returns `VerificationReport` and raises nothing on a failed
verification (`src/cement_runtime/system.py:3696-3721`); `src/cement_runtime/cli.py:265-266` returns it and
`main` unconditionally emits then returns 0 (`src/cement_runtime/cli.py:339-360`). A scripted operator
therefore cannot distinguish a verified artifact from a failed one by exit status.

Ruling: `function verify` returns `_Outcome(payload=verification, status=0 if verification.passed else 6)`.
The projected verification payload — `passed`, `entries`, `function_hash`, and the ordered `checks`
vector, never the nested `document` — stays on **stdout**, not stderr, because the command executed successfully
and is reporting a negative verdict — it is not an error path, and the ordered check vector is exactly the
diagnostic an operator needs. This is the `diff` / `git diff --exit-code` convention: a distinct exit class
for "difference found", payload on stdout. Exit 6 is new and deliberately not folded into an existing class:
2 means the request was malformed, 3 not found, 4 a state conflict, 5 persisted corruption detected. A
failing P1–P6 vector is none of those.

Root `verify`'s exit-0 behavior is frozen and stays; changing it is outside u4c and outside M2's spine.
u5 owns documenting exit 6 alongside the existing codes.

## Decision 5 — three identities never swap

`show`, `export`, `verify`, `inspect`, `promote` touch three distinct objects and each command names exactly
one: the current committed snapshot (`verify_function`), the prospective union
(`inspect_function_promotion`), and an immutable historical receipt (`reconstruct_function_receipt`).
Exporting inspect output would publish unpromoted candidates. Live `export` is gated on `verify_function`
passing P1–P6, and a failed verification raises through to exit 5 rather than exporting a stale or
diagnostic document; `--receipt-id` selects the historical source and cross-checks the reconstructed
receipt's operation against the positional operation. Nested `function verify` / `function promote` never
route to the root per-artifact `verify` / `promote` at `src/cement_runtime/cli.py:98-105`.

## Decision 6 — offline eval: importing is not constructing

`function eval` is special-cased ahead of the `--db` / `--partition` gate at
`src/cement_runtime/cli.py:195-199`; the globals stay mandatory for every other leaf, including every other
`function` leaf. The handler never constructs `System`.

It cannot avoid *importing* it: `src/cement_runtime/function.py` imports only stdlib plus `.errors` and
`.json_value`, but any `import cement_runtime.function` first executes the package `__init__`, which imports
`.system`, which imports `.store` and `sqlite3`. Ledger-freedom here means no `System` instance, no database
path, and no connection — which is what the paragraph-1 claim actually needs. Making the import graph itself
lazy would touch `__init__.py`, outside u4c's write set, and buys nothing for the claim.

Bundle and evaluation input take separate channels. `_input`'s stdin path is capped at `DEFAULT_MAX_BYTES`
(1,048,576), 64× below `FUNCTION_MAX_BYTES` (67,108,864), so a bundle can never travel through it; `--bundle`
takes a path read by a dedicated strict-UTF-8 reader bounded at `FUNCTION_MAX_BYTES`, while `--input` keeps
the existing bounded JSON channel including `-`.

## Write set

Every sub-unit writes `src/cement_runtime/cli.py` and `tests/test_cli.py` only. `system.py`, `store.py`,
`models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/` stay byte-identical; u5 owns
every M2 documentation edit.

## Known limits, carried into the sub-units

- `evaluate` IS exported from `cement_runtime` (`__init__.py` imports it and lists it in `__all__`); an
  earlier draft of this record claimed otherwise, from a filtered export listing that dropped every name
  without `unction` in it. The offline evaluator is public; do not reintroduce the claim.

- `_function_receipt_from_row` converts receipt integer fields with bare `int(...)`, so a corrupt persisted
  scalar leaks raw `TypeError`/`ValueError` past callers written for `IntegrityError`, and numeric text
  (`'1'`) is accepted where an exact stored int is required. It is reachable from `show`, `receipts`,
  `verify` P6, and historical `export`. `system.py` is outside u4c's write set and `main` has no catch-all
  by design, so a corrupt ledger can still surface as a traceback rather than mapped JSON. No u4c test may
  claim the CLI is total over corrupt ledgers. Tracked in `.agent/polish.md`.
- Omitted-by-choice verbs from Decision 1 stay library-only for M2.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, for every
sub-unit.
