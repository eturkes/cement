# M2.u4c5b acceptance contract — MAIN

Baseline `291e0e9`. Tier `kernel`. Write set = `src/cement_runtime/cli.py` + `tests/test_cli.py`; every
other tracked path stays byte-identical, `.agent/` records aside.

Scope = the second half of `function export`: the `--out PATH` atomic file channel. Decisions 1 and 3 of
`.agent/decisions/m2u4c5-design.md` bind unchanged; Decision 4 binds as amended in A.

## A — ordering ruling

Two spikes built the whole writer to a green gate and each self-rejected on a defect the other lacked:
validating the destination BEFORE any ledger call leaves a gate-wide TOCTOU window, while validating only
once the document is in hand burns unbounded reconstruction work on a trivially unusable path (≈1 s and
13 MiB per 1,000 entries, growing to tens of seconds at the 64 MiB cap). The ruling composes both.

1. The structural `--out` check runs BEFORE source selection, inside the export leaf and after `System`
   construction, so `--db` keeps its repo-wide precedence over every other argument.
2. The same structural check RERUNS immediately before `os.replace`.
3. `os.fchmod(descriptor, 0o600)` pins the written mode before the payload is written.
4. Each check is ONE `os.lstat`, never a chain of `Path` predicates.
5. The writer names its own temp and proves it distinct from the destination before creating anything.

Precedent for 1: `--db` with a missing parent exits 2 inside `Store.__init__` before any ledger work
(`store.py:467`), and a shell redirect (`{ …; exec cement …; } > missing/f`) fails before Cement runs at
all. A structurally impossible destination is repaired by no ledger change, so reporting the source
verdict first sends the operator down a repair path that terminates at the identical failure.

Rationale for 2: a recheck cannot CLOSE the race — `rename(2)` carries no target-identity predicate and
`RENAME_NOREPLACE` would forbid the overwrite this leaf exists to perform. It narrows the window from the
whole verification gate to one stat/replace pair. H claims exactly that and nothing more.

Rationale for 4: `Path.is_symlink()`, `Path.exists()` and `Path.is_file()` are three syscalls, so a link
installed between two of them is admitted by the very check meant to refuse it. `lstat` decides on one
coherent inode snapshot and does not follow the final component.

Rationale for 5: `tempfile.mkstemp` derives its name from a prefix alone, so a target whose own name
reproduces that prefix can be drawn as its own temp — with `prefix=f".{name[:64]}."` the destination
`"."*66 + <8 chars>` is reachable. The payload is then written straight through the destination name,
which appears as an empty file before the bundle exists, and `os.replace(path, path)` is a no-op.
Probability is not a safety argument for a kernel-tier guarantee.

AMENDS design Decision 4, whose two claims are false as written:
- "replacement takes the temp's inode, so the result is mode 0600" holds only under a restrictive umask —
  `mkstemp` requests `0600 & ~umask`, so `umask 0777` yields mode `000`. Ruling 3 makes 0600 unconditional
  and race-free.
- it maps only a MISSING parent to `export output directory does not exist`. A parent that exists as a
  regular file takes the same message: `Path.is_dir()` is false for it, and `store.py:467` uses that
  identical predicate and wording for the ledger's own parent.

Accepted cost of 1, deliberate rather than incidental: a structurally bad `--out` preempts source verdicts
6/3/3/5 as exit 2. It does NOT preempt operation grammar, which still runs first.

## B — surface

```
cement --db DB --partition P function export OPERATION [--receipt-id ID] [--out PATH]
```

- Parser slot: `function_export.add_argument("--out", help=…)` after the `--receipt-id` block and before
  the `events` parser. No `type=`, no default, so absent ⇒ `None`.
- `function export` is the only leaf that DEFINES `--out`; every leaf that defines neither `--out` nor a
  longer `--out…` option rejects it as an argparse usage error at exit 2. `proposal review` is the
  exception in the other direction: inherited `allow_abbrev` (unpinned since u4c2) makes `--out` an
  unambiguous abbreviation of its pre-existing `--output`, which predates this unit and stays untouched.
- `--out` is a PATH, never a stream selector: `--out -` writes a file literally named `-` in the cwd.
- `--out ""` reaches the leaf as the empty string. `pathlib.Path("")` is `Path(".")`, a directory, so the
  non-regular guard rejects it — the same exit-2 non-regular class `store.py` gives an empty `--db`, whose
  own message (`database path must identify a regular file`) stays distinct.

## C — channel

- WITHOUT `--out`: unchanged from u4c5a. `_Outcome(raw=document.text)` ⇒ raw UTF-8 bundle on stdout.
- WITH `--out`: the leaf returns a plain `dict`, so `main`'s existing tail emits it through `_emit` and
  returns 0. No `_Outcome` on this path, no new `main` branch — `_Outcome`, `_emit`, `main`'s channel
  branch and all six exception clauses stay byte-identical.
- Success payload, exactly three keys, `_emit`-sorted:

```python
{"out": str(resolved_target), "bytes": len(payload), "function_hash": document.function_hash}
```

- `out` = `target.parent.resolve() / target.name`. Only the parent chain resolves, because the final
  component is already guaranteed not to be a symlink; the reported path therefore names the file that
  received the bytes rather than the lexical argument.
- `bytes` = `len(document.text.encode("utf-8"))`, the exact count written, which exceeds the character
  count on a non-ASCII document.
- `function_hash` = `document.function_hash` on BOTH branches (`function.py:70`, type `str`), deliberately
  not `verification.function_hash` (`str | None`) nor `reconstruction.function_hash` (a delegation).
- The success object and Decision 1's failure object share no key, so shape alone distinguishes them.
- stderr is byte-empty on success; stdout is byte-empty on every failure path.

## D — the writer

```python
def _reject_export_target(target: pathlib.Path) -> None:
    try:
        mode = os.lstat(target).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return  # both belong to the parent, which the caller grades
    if not stat.S_ISREG(mode):
        raise ValidationError("export output path must identify a non-symlink regular file")


@contextlib.contextmanager
def _export_failures() -> Iterator[None]:
    try:
        yield
    except ValidationError:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValidationError("export output could not be written safely") from exc


_EXPORT_ATTEMPTS = 128


def _export_temporary(target: pathlib.Path) -> tuple[int, pathlib.Path]:
    for _ in range(_EXPORT_ATTEMPTS):
        candidate = target.with_name(f".{target.name[:64]}.{os.urandom(6).hex()}")
        if candidate == target:
            continue
        try:
            return os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), candidate
        except FileExistsError:
            continue
    raise ValidationError("export output could not be written safely")


def _export_target(value: str) -> pathlib.Path:
    target = pathlib.Path(value)
    with _export_failures():
        _reject_export_target(target)
        if not target.parent.is_dir():
            raise ValidationError("export output directory does not exist")
        return target.parent.resolve() / target.name


def _write_export(target: pathlib.Path, document: FunctionDocument) -> dict[str, Any]:
    payload = document.text.encode("utf-8")
    temporary: pathlib.Path | None = None
    try:
        with _export_failures():
            descriptor, temporary = _export_temporary(target)
            try:
                stream = os.fdopen(descriptor, "wb")
            except BaseException:
                os.close(descriptor)
                raise
            with stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            _reject_export_target(target)
            os.replace(temporary, target)
            temporary = None
    finally:
        if temporary is not None:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
    return {"out": str(target), "bytes": len(payload), "function_hash": document.function_hash}
```

Leaf ordering:

```python
_name(args.operation, "operation")
target = _export_target(args.out) if args.out is not None else None
<unchanged u4c5a source selection and verification gate, yielding `document`>
if target is None:
    return _Outcome(raw=document.text)
return _write_export(target, document)
```

- `_export_failures` wraps BOTH the precheck and the writer because `main` maps no bare `OSError`: the
  `Path`/`lstat` predicates raise `EACCES` on a search-denied ancestor and `ValueError`/`UnicodeError` on
  a NUL or lone surrogate, and every one of those has to reach the operator as this leaf's exit 2.
  `except ValidationError: raise` precedes the translating clause so the guard's own message survives.
- A dangling symlink is refused by `S_ISLNK` alone; a directory, FIFO, socket or device by the same
  non-regular test. `os.replace` onto a symlink replaces THE LINK, not its referent, and destroying the
  operator's link is what the guard prevents — hence ruling 2's placement adjacent to the replace.
- `.{target.name[:64]}.{12 hex}` — the leading dot hides a leftover from a plain `ls`, and the cap holds
  the whole name at 78 characters, inside `NAME_MAX` for target names up to the filesystem maximum.
  Uncapped, a legal maximum-length target name fails with `ENAMETOOLONG`. `_EXPORT_ATTEMPTS` exhaustion
  over a 2**48 name space means a hostile directory rather than a crowded one, and reports as any other
  write failure.
- The temp is created through `target.with_name`, so it lands in the RESOLVED parent: temp and destination
  always share a filesystem and `os.replace` is a true atomic rename.
- `os.fdopen` ownership: on failure the descriptor is closed explicitly and re-raised; on success the
  `with` owns it. No double close, no leak. A discarded colliding candidate is never opened, so it leaks
  nothing.
- The `finally` attempts to unlink a surviving temp on every failure path, best-effort: the suppressed
  `OSError` keeps a cleanup failure from masking the failure the operator has to act on, and a parent that
  refuses the unlink keeps the leftover. `temporary = None` after a successful replace states the intent;
  it is not load-bearing, since the temp name no longer exists after the rename.
- `contextlib`, `pathlib` and `stat` are new imports, plus `Iterator` and `FunctionDocument` for
  annotations. `tempfile` is deliberately absent.

Error map, all `ValidationError` ⇒ exit 2 through `main`'s existing `(ValidationError, CementError)`
clause. Argparse usage errors reach the same code through the distinct `_UsageError` clause, so `$?` alone
cannot separate the two.

| condition | OS result | message |
| --- | --- | --- |
| parent missing | `FileNotFoundError` | `export output directory does not exist` |
| parent is a regular file | `NotADirectoryError` | `export output directory does not exist` |
| target is a symlink (live or dangling) | `S_ISLNK` | `export output path must identify a non-symlink regular file` |
| target is a directory | `S_ISDIR` | same |
| target is a FIFO/socket/device | non-regular mode | same |
| ancestor is search-denied | `PermissionError` at `lstat` — `pathlib`'s `_ignore_error` covers only ENOENT/ENOTDIR/EBADF/ELOOP, so this raises on every supported Python | `export output could not be written safely` |
| NUL in path | `ValueError` at `lstat` | same |
| lone surrogate in path | `UnicodeEncodeError` at `lstat` | same |
| name > `NAME_MAX` | `OSError` ENAMETOOLONG | same |
| parent mode 0500 | `PermissionError` at `mkstemp` | same |
| ENOSPC at write/fsync | `OSError` ENOSPC | same |
| `os.replace` fails after a good write | `PermissionError` | same |

## E — probe corpus (expected outcomes are contract, not suggestion)

Fixtures reuse the committed helpers `promoted_operation` (`test_cli.py:291`), `register`, `confirm`,
`confirm_text`, `promote_set`, `corrupt_receipt_membership`. Tests run with cwd = the repo root and
`setUp` creates `TemporaryDirectory(dir=".")` there, so every `--out` uses an absolute path inside
`self.temporary.name` unless it deliberately probes relative resolution. `run_cli` takes no new kwarg; its
introspection pin at `test_cli.py:1941-1955` stays green.

Success:

| invocation | exit | destination | payload |
| --- | --- | --- | --- |
| `--out` absent (all u4c5a cases) | unchanged | untouched | raw bundle on stdout |
| `--out NEW`, healthy set | 0 | created, bytes == `document.text.encode()`, mode 0600 | `{bytes, function_hash, out}`, stderr empty |
| `--out EXISTING` (mode 0644, different bytes) | 0 | replaced atomically, mode 0600 | same |
| `--out NEW --receipt-id <own receipt>` | 0 | historical document bytes | `function_hash` = the historical hash |
| `--out NEW`, non-ASCII corpus | 0 | exact UTF-8, zero `\uXXXX` escapes | `bytes` > character count |
| `--out NEW`, registered, nothing promoted | 0 | the real `"entries":[]` document | `bytes` == its length |
| `--out <name of length PC_NAME_MAX>` | 0 | created | prefix cap keeps the temp inside `NAME_MAX` |
| `--out NEW` under `umask 0o777` | 0 | mode 0600 | `os.fchmod` pin |
| `--out -` | 0 | a file named `-` in cwd | never stdout |
| `--out relative/name` | 0 | created relative to cwd | `out` is absolute |
| `--out <through a symlinked parent dir>` | 0 | created in the resolved directory | `out` is resolved, not the alias |

Additional success pins: after any success the parent's `.*` glob is empty; `parse_function(<file bytes>)`
yields the payload's `function_hash` and `evaluate` on a promoted input returns `matched=True`; the file
bytes equal the raw channel's stdout bytes for the same operation.

Failure — path (every row: exit 2, stdout `b""`, destination unchanged or absent, no leftover temp):

| invocation | message |
| --- | --- |
| parent missing | `export output directory does not exist` |
| parent is a regular file | `export output directory does not exist` |
| target is a directory | `export output path must identify a non-symlink regular file` |
| target is a symlink to a regular file | same — link intact, referent byte-identical |
| target is a dangling symlink | same — link intact and still dangling |
| target is a FIFO | same |
| `--out ""` | same |
| parent mode 0500 | `export output could not be written safely` |
| ancestor directory mode 0000 | same |
| path containing NUL | same |
| path containing a lone surrogate | same |
| name of length `PC_NAME_MAX + 1` | same |
| `os.fsync` injected `OSError(ENOSPC)` | same, pre-existing destination byte-identical |
| `os.replace` injected `OSError(EACCES)` after a good write | same, destination holds the OLD bytes |

Failure — source, with a GOOD `--out` (destination absent afterwards, stdout `b""`, stderr identical to
the same invocation without `--out`):

| state | exit | stderr |
| --- | --- | --- |
| set drifted by `artifact suspend` | 6 | the full six-check `unverified` object, unchanged from u4c5a |
| operation unregistered | 3 | `operation is not registered in this partition` |
| `--receipt-id` unknown well-formed id | 3 | `function receipt does not exist in this partition` |
| `--receipt-id` receipt of another operation | 3 | `function receipt does not exist for this operation` |
| `--receipt-id` corrupted receipt | 5 | `function receipt membership digest mismatch` |
| injected `passed=True, document=None` | 5 | `function verification passed without an exportable document` |

Failure — DOUBLE FAULT, the deliberate preemption set. Every row exits 2 with the path message, not the
source verdict:

| path fault | source fault | exit (vs. without `--out`) |
| --- | --- | --- |
| parent missing | drifted set | 2 (vs 6) |
| target is a symlink | drifted set | 2 (vs 6) |
| ancestor search-denied | drifted set | 2 (vs 6) |
| parent missing | operation unregistered | 2 (vs 3) |
| target is a symlink | unknown receipt id | 2 (vs 3) |
| parent missing | corrupted receipt | 2 (vs 5) |
| parent missing | malformed operation | 2, with the OPERATION GRAMMAR message and payload |

Behavioral pins beyond the tables:

1. THE RECHECK PIN. The destination becomes a symlink between the precheck and the write, injected by
   patching `System.verify_function` (library boundary, never `cli._run`) with a side effect that creates
   the link. Expected: exit 2, the non-regular message, the symlink still a symlink, its referent
   byte-identical, no leftover temp. Without the recheck the case exits 0 and `os.replace` removes the
   symlink name, so this is the sole committed proof of ruling 2.
2. ONE STAT PER CHECK. `os.lstat` is wrapped by a counting delegate; one successful export performs
   exactly two lstats of the destination. This is the committed form of ruling 4 — a predicate chain
   spends several syscalls per check and admits a link installed between two of them.
3. ATOMIC OVERWRITE. A pre-existing destination is never observed as a prefix: injected at `os.replace`, a
   wrapper reads the destination and finds the OLD bytes with the payload already written and fsynced;
   after a successful run it holds the whole new document.
4. NEVER THE DESTINATION'S OWN NAME. The destination is `"." * 66 + <12 hex>` and `os.urandom` is patched
   so the FIRST draw returns exactly the colliding bytes. Expected: two draws, the destination ABSENT at
   `os.replace` time, and the final bytes equal the document. This is the committed form of ruling 5 —
   under a prefix-derived temp name the same fixture creates the destination empty before the payload.
5. TEMP CENSUS. Every failure row asserts the parent's `.*` glob is empty, so a leaked temp is a red test.
6. MODE IS UNCONDITIONAL. The umask row runs under `os.umask(0o777)` restored in cleanup and asserts
   `stat.S_IMODE(...) == 0o600`; without `os.fchmod` the result is `0o000`.
7. `--out` DOES NOT ALTER THE NO-`--out` PATH. The u4c5a raw-channel tests stay green unchanged, and one
   test asserts both channels carry byte-identical content for the same operation.
8. EXIT MAP, symbol-qualified and patched at the library boundary: with a good `--out`,
   `ValidationError`→2, `NotFoundError`→3, `StateError`→4, `IntegrityError`→5, negative verdict→6, and for
   every nonzero code both `stdout_bytes == b""` and the destination absent.
9. `bytes` IS THE WRITTEN LENGTH: the non-ASCII row asserts `bytes == len(file_bytes)` and
   `bytes > len(document_text)`.
10. `out` IS RESOLVED: the symlinked-parent row asserts the reported path is the resolved directory's and
   differs from `os.path.abspath` of the argument.
11. NAME BOUND, derived not hardcoded: `os.pathconf(parent, "PC_NAME_MAX")` supplies both sides —
    that length succeeds, `+1` exits 2 with the safe-write message. A hardcoded 250 proves nothing here,
    where `PC_NAME_MAX` is 512.

## F — invariant surfaces

- `git diff --name-only 291e0e9..<unit commit>` touches exactly `src/cement_runtime/cli.py`,
  `tests/test_cli.py` and `.agent/` records.
- `system.py`, `store.py`, `models.py`, `function.py`, `__init__.py`, `README.md`, `docs/`, `examples/`
  stay byte-identical: no library delta, the writer is CLI-local.
- `_Outcome`, `_emit`, `main`'s six exception clauses and its `_Outcome` channel branch stay
  byte-identical, and the 26 pre-existing `_run` leaves keep their returns, exit codes and stdout bytes.

## G — gate identity

`uv run python -m unittest discover -s tests -t .` and `uv build`, both from the repo root, rerun by MAIN
from committed state at close.

## H — known limits

- The recheck NARROWS the destination TOCTOU window; it does not close it. A destination replaced between
  the final `lstat` and `os.replace` is still replaced. The guarantee: a destination that is a symlink or
  a non-regular file AT EITHER CHECK'S SINGLE STAT is refused.
- Content guarantee, scoped to this writer: Cement publishes by one atomic `os.replace` onto a name it has
  proved is not its own temp, so absent external mutation each lookup of the destination resolves to the
  complete old inode or the complete new one, never a prefix and never an empty placeholder. A concurrent
  external writer owns its own effects; this leaf synchronizes nothing.
- Temp cleanup is best-effort. The `finally` attempts the unlink on every failure path and suppresses its
  own `OSError` so a cleanup failure cannot mask the failure the operator has to act on. A parent that
  refuses the unlink keeps a `.<name>.<hex>` leftover at mode 0600; the committed census rows assert the
  empty glob for every failure the corpus injects, none of which refuses the unlink.
- A structurally bad `--out` preempts source verdicts 6/3/3/5 as exit 2, and the preemption set is exactly
  what one `lstat` plus the parent test can see: symlink/non-regular target, missing or non-directory
  parent, search-denied ancestor, NUL, surrogate, `NAME_MAX`. Write-time causes — parent 0500, ENOSPC,
  replace failure — surface after the gate and preempt nothing.
- The file and the receipt are not one transaction. `os.replace` installs the destination and `main` then
  emits the JSON receipt, so a stdout that fails afterwards (`/dev/full`, a closed pipe) leaves a complete
  export behind a nonzero exit — Python's exit-time flush failure reports 120. "Writes nothing on failure"
  scopes to failures reached BEFORE the replace; nothing can make a file and a pipe atomic together.
- Malformed path components fault at the same stage regardless of position: `os.lstat` raises for a NUL,
  a lone surrogate or an over-length component in the FINAL or any PARENT position alike, so all six
  shapes preempt with the safe-write message rather than the directory message.
- No directory fsync after `os.replace`. The new file's content is durable via its own fsync; a crash
  between the rename and the parent's writeback can leave the old name resolving to the old inode.
- Every filesystem cause collapses to exit 2 with `errno` unsurfaced, matching `store.py`'s posture:
  three messages cover twelve causes.
- Mode is unconditionally 0600 and an existing destination's mode is NOT preserved, because replacement
  installs the temp's inode. An operator needing a group-readable export chmods after the fact.
- The document is materialized whole in memory and written in one call — up to 64 MiB and 50,000 entries.
  No streaming, no cursor, by construction: a bundle is meaningless in fragments.
- The aggregate-limit vector remains reachable only through the legacy per-artifact `System.promote`, so
  its `--out` interaction stays reasoned rather than built, exactly as in u4c5a.
- Stored-scalar conversions reachable through the reconstruction path can still leak raw
  `TypeError`/`ValueError`/`OverflowError` past `main`; that audit stays the tracked `.agent/polish.md`
  item and is not widened here.
