# M2 u4c5 design record — MAIN arbitration

Baseline `20aa81b`, gate green under MAIN's own run (`Ran 453 tests in 90.207s / OK`, `uv build` rc 0).
Tier `kernel`. Write set stays `src/cement_runtime/cli.py` + `tests/test_cli.py` per
`.agent/decisions/m2u4c-design.md`; no library delta, since both halves forward to shipped APIs.

Inputs, all inlined below rather than cited: an anchored fact map (268 anchors, validator rc 0, MAIN
rerun) and two full prototypes built to green gates in their own worktrees — INTEGRITY (`cli.py` +70) and
VERDICT (`cli.py` +45). Both prototypes and both reports are gitignored and travel nowhere, so every
number this record depends on is written out here.

## Decision 1 — a failed live verification is a verdict on stderr at exit 6, never a raised `IntegrityError`

Both prescriptions on record — `.agent/archive/m2.md` u4c5 and `m2u4c-design.md` Decision 5 — say a failed
live verification "raises through to exit 5". Both spikes self-rejected, on disjoint evidence, and their
two self-rejections do not overlap: each names a defect the other alternative does not have.

INTEGRITY (raise `IntegrityError` → exit 5, prose on stderr) self-rejected on TAXONOMY:

- `artifact suspend` alone drives a checkpointed set to `passed=False` through committed CLI commands.
  Measured vector `[T,T,T,T,T,F]`, sole failure `persisted-function-receipt: latest receipt does not bind
  the promoted snapshot`. Nothing is corrupt — the set drifted from its receipt and the remedy is a
  zero-candidate `function promote`. Reporting that as `{"error":"integrity"}` is false.
- The aggregate-limit vector is worse: it fails all six checks with detail `not evaluated because N
  promoted entries exceed FUNCTION_MAX_ENTRIES=50000`, i.e. a capacity bound, and `integrity` lies again.
  Reachability, ruled against VERDICT's contrary reading: the 50,000 cap binds `build_function` and set
  promotion, but `System.promote` (`system.py:4457`) — the legacy per-artifact path the CLI still
  exposes — references no aggregate count at all (`FUNCTION_MAX_ENTRIES` appears in `system.py` only at
  the receipt member-count guard and inside `verify_function`), so 50,001 promoted inputs are reachable
  through supported commands, impractically but really.
- Prose destroys the only discriminator. Six ordered checks collapse into one sentence, so no script can
  separate drift from corruption without re-running `function verify` and parsing it (measured: ≥8 lines
  plus `jq`, and still heuristic).

VERDICT (return `_Outcome(payload=verification, status=6)`) self-rejected on CHANNEL:

- `function export OP > f` after the same supported `artifact suspend` exits 6 and leaves `f` holding
  1,078 bytes of verdict JSON. The redirect creates and truncates `f` before Cement runs, so the operator
  ends with a file that parses as JSON, is not a bundle, and replaced a good bundle if one was there.
- stdout changes media type by verdict — bundle at 0, diagnostics at 6 — which is the one thing a
  byte-producing leaf must not do.

RULING, taking each spike's measured strength and neither's defect: a failed live verification produces
**no bundle bytes, an empty stdout, the ordered check vector on stderr, and exit 6**.

- Exit 6 keeps one meaning across the whole `function` group: a verification verdict came back negative.
  `verify` and `verify-drafts` put that verdict on stdout because their stdout is a JSON channel; `export`
  puts it on stderr because its stdout is the artifact channel. The exit class is the shared vocabulary;
  the channel follows the leaf's stdout contract.
- stderr payload is the standard two-key error object plus one additive key, so every existing consumer
  reading `.error` / `.message` keeps working:
  `{"error": "unverified", "message": "function verification failed; no bundle exported: <key>: <detail>;
  …", "checks": [{"key","passed","detail"} × 6]}`. `checks` is the FULL ordered vector, identical in shape
  and vocabulary to `function verify`'s stdout `checks`, so one `jq` path serves both.
- `error: "unverified"` is a new token, and the token↔exit bijection is preserved: `invalid`→2,
  `not_found`→3, `conflict`→4, `integrity`→5, `unverified`→6.
- `function_hash` and `entries` are deliberately absent from the failure object. A failed verification may
  still carry a diagnostic hash, and an error object with a bare hash and no `passed` field invites an
  operator to copy the identity of a set that did not verify. Every discriminator is already in `checks`,
  including the entry count inside the aggregate-limit detail.
- Real exceptions keep `main`'s existing map untouched: `NotFoundError`→3, `ConflictError`/`StateError`→4,
  `IntegrityError`→5, `ValidationError`→2.

Mechanics, inside the write set and without touching the frozen seam: `_run` raises a private
`_Unverified(Exception)` carrying the finished payload dict; `main` gains ONE appended `except` branch that
emits it to stderr and returns 6. `_Outcome`, `_emit`, `main`'s channel branch and every existing exception
mapping stay byte-identical, and no leaf writes a stream itself — all output stays in `main`. Rejected
alternatives: widening `_Outcome` with a stream or stderr field (u4c1 froze its exact shape, and a
subclass/field pin already guards it); `_emit(..., stream=sys.stderr)` from inside `_run` plus
`_Outcome(raw="", status=6)`, which works — `raw=""` is pinned to emit `b""` — but moves output out of
`main` and is exactly the private write Decision 3 forbids.

## Decision 2 — u4c5 splits two ways

Sizing recheck at the unit's open, as `.agent/archive/m2.md`'s M2 header requires. The arbitrated surface is larger than
the roadmap's pre-arbitration estimate of 46-67 production / 520-760 tests: INTEGRITY's prototype landed
+70 production carrying only the atomic writer and the prose disposition, and Decision 1 adds the private
exception, the `main` branch and the structured payload, while Decision 4 adds path validation. Estimate
now **80-100 production / 800-1,070 tests**, against u4c4's landed `+30 / +1,011` at `main=98%` — the
closest analog and the one that nearly overran. Under the current authorship split MAIN pays both halves
from one window, so a unit with 2.5x u4c4's production and comparable tests does not fit.

| unit | scope | est. production / tests |
| --- | --- | --- |
| u4c5a | source selection + verification gate + raw byte channel to stdout | 45-55 / 480-620 |
| u4c5b | `--out PATH` safe file channel | 35-45 / 320-450 |

The cut is by CHANNEL, not by source. Source selection (live vs `--receipt-id`) is one judgment surface
whose two branches share the verification/identity rulings and differ by ~10 production lines; splitting
there would separate rulings that decide each other. The file channel is the opposite: a self-contained
writer plus a hostile-path matrix that dominates its own test cost and shares no judgment with source
selection. u4c5a alone is shippable — `function export OP > bundle.json` and `function export OP
--receipt-id ID > bundle.json` both work end to end, and under Decision 1 a failed verification leaves the
redirect target empty rather than poisoned, which is precisely what makes the standalone half safe.

Order `u4c5a → u4c5b`; both depend on u4c1 + u4c2; u4c6 (`eval`) then depends on u4c5a for a bundle to
read. Decisions 1, 3 and 4 bind both sub-units and are not re-litigated per sub-unit.

## Decision 3 — identity, byte exactness, and the historical cross-check

- Two sources, never mixed, per `m2u4c-design.md` Decision 5: no flag = the current committed snapshot
  (`verify_function`); `--receipt-id ID` = one immutable historical receipt
  (`reconstruct_function_receipt`). The prospective union is not an export source at any flag value.
- `FunctionDocument.text` reaches stdout as `text.encode("utf-8")` through the existing raw channel, with
  nothing appended. The document is canonical JSON with no trailing newline and `ensure_ascii=False`, so a
  non-ASCII entry emits multibyte UTF-8 literally — the corpus needs one non-ASCII case, and the
  no-`.buffer` text host needs its own case.
- `reconstruct_function_receipt(partition, receipt_id)` takes no operation and its lookup predicates are
  `partition` + `id` only, so without a CLI cross-check a receipt of operation B exports successfully
  under positional operation A — measured on both prototypes. The cross-check is mandatory and raises
  `NotFoundError("function receipt does not exist for this operation")` → exit 3, reusing
  `function_report`'s exact string (`system.py:2621`) so `show` and `export` speak one vocabulary for one
  condition. A wrong partition and an unknown-but-well-formed ID also exit 3; a malformed ID exits 2 from
  the library's `_request_id` grammar.
- Historical failure keeps exit 5 and the asymmetry is deliberate: the live set is a current aggregate
  that legitimately drifts, so its negative is a verdict; a receipt is immutable, so a receipt that no
  longer reconstructs is corruption. `$?` separates them — 6 = the live snapshot evaluated negative, 5 =
  the selected history could not reconstruct — and both are pinned.
- `passed=True` structurally implies a document: the capacity path returns `document=None` with
  `passed=False`, and the normal return computes `document if passed else None` (`system.py:3377`). The
  CLI still guards it and raises `IntegrityError("function verification passed without an exportable
  document")` → exit 5, pinned by injection at the library boundary, never by patching `cli._run`. An
  `AssertionError` here would escape `main` as a traceback and is rejected.
- An operation with nothing promoted verifies vacuously and exports a real 304-byte document with
  `"entries":[]`. That is the honest state and exits 0. `promote`'s refusal to seal an empty union does
  not transfer: `promote` writes, `export` reports.

## Decision 4 — `--out` writes atomically or not at all (binds u4c5b)

Measured: a direct `open(path,"wb")` truncates a good destination and leaves a partial file on mid-write
failure — 17 bytes in one prototype, a 100-byte prefix in the other. `store.py:469` is the repo's only
create precedent (`os.open(O_CREAT|O_EXCL|O_WRONLY, 0o600)`) and solves identity, not content, so the
writer is new work:

```python
descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=parent)   # 0600
with os.fdopen(descriptor, "wb") as stream:                                # write, flush,
    ...                                                                    # os.fsync(fileno)
os.replace(temporary, target)                                              # atomic overwrite
# finally: close a leaked descriptor, unlink a surviving temp
```

- Overwrite is atomic replacement, so the destination is the old bytes or the new bytes and never a
  prefix; a failed rename leaves the previous file visible and removes the temp (measured).
- Replacement takes the temp's inode, so the result is mode 0600 and an existing destination's mode is
  not preserved. Stated, pinned, and consistent with the ledger file's own mode.
- The target is rejected before any write when it exists and is a symlink or not a regular file:
  `ValidationError("export output path must identify a non-symlink regular file")`, mirroring
  `store.py:472`. `os.replace` would otherwise replace the symlink itself rather than its target, silently
  destroying the operator's link.
- A missing parent directory reports `ValidationError("export output directory does not exist")` ahead of
  the attempt, mirroring `store.py:467`; every other `OSError`/`ValueError`/`UnicodeError` maps to
  `ValidationError("export output could not be written safely")`, mirroring `store.py:474`. Both exit 2.
  This translation is mandatory, not stylistic: `main` has no catch-all, and an injected bare `OSError`
  was measured escaping it with both streams empty.
- `--out` emits `{"out": <resolved absolute target>, "bytes": <UTF-8 length written>, "function_hash":
  <hex>}` on stdout at exit 0 — the frozen seam carries payload XOR raw, so a silent success is not
  expressible. `out` makes a log line identify the file independently of cwd, `bytes` lets a script assert
  the write completed at the expected length, `function_hash` binds the exported identity without
  reparsing up to 64 MiB. The success object and the Decision 1 failure object share no key, so shape
  alone distinguishes them.
- Nothing is written on any failure path: an absent destination stays absent and a pre-existing file stays
  byte-identical at exit 6, 3 and 5 (measured on both prototypes). This is the whole reason `--out` exists
  beside `>`: the shell redirect creates and truncates its target before Cement runs, and a failed export
  leaves a 0-byte file (measured).
- No directory fsync after `os.replace`, so a crash between replace and the parent directory's own
  writeback can leave the old name resolving to the old inode. Content durability of the new file is
  guaranteed by its fsync; rename durability is out of scope and recorded as a known limit.

## Known limits carried into both sub-units

- Exit 6 now names three objects across three leaves — failed drafts, a failed committed set, and a
  refused export — one meaning, three payload shapes, distinguished by command and channel.
- Neither half claims total error mapping over corrupt ledgers. `_function_receipt_from_row`-class
  stored-scalar conversions still leak raw `TypeError`/`ValueError`/`OverflowError` past `main`, and
  historical export reaches them; the audit stays the tracked `.agent/polish.md` item, widened by u4c5a to
  name the reconstruction path.
- The aggregate-limit vector is reachable only by promoting 50,001 inputs through the legacy per-artifact
  path, so it stays a reasoned branch: no test builds it, and any surrogate patches the cap rather than
  the ledger.
- `--out` failure classes collapse to exit 2 for every filesystem cause (ENOENT, EISDIR, EACCES, ENOSPC),
  matching `store.py`'s own posture; `errno` is not surfaced.

## Gates

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, for each
sub-unit.
