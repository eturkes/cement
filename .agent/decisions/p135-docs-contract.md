# p135-docs contract — encryption at rest (E2) + registry recipe (E4) (revision 1)

Plan: `.agent/decisions/p87-milestone.md` E2 + E4 + gate 3, amended by the owner's D4 ruling (`.agent/spec.md`
`Decisions`: encryption at rest = the deployment's volume encryption, named in docs; no field encryption).
Tier `docs` (consistency pass, MAIN alone): no runtime change; every claim is re-derived against shipped code.

## Premises (read at `8bf9dad`)

- F1 `Store._open` sets `PRAGMA journal_mode = DELETE` after identity + integrity (`store.py`); a
  write connection sets `temp_store = MEMORY` + `secure_delete = ON`; the shadow store does the same
  (`shadow.py`) and lives at `<ledger>.shadow` (`shadow_path`).
- F2 `function export --out` opens `.<target name[:64]>.<12 hex>` beside the destination with
  `O_CREAT | O_EXCL`, mode `0o600`, then `os.replace` (`cli.py` `_export_temporary`).
- F3 `cement_runtime` holds no key and opens no network connection; the paste-ins + `ext/bin/cement`
  embed the stdlib-only package (D4's reason against field encryption).
- F4 `oras push <ref> <file> <file>` + `oras pull <ref>` (pulls into the current directory) — ORAS
  command reference, `oras.land/docs/commands/oras_push` + the push/pull guide.

## Obligations

- G1 README `## Deployment boundary`: Cement does not encrypt; the volume-encryption mechanism + the
  file list: the ledger, `<ledger>-journal` (`-wal` + `-shm` after an operator switch), the shadow
  file + its journal, the export temporary file beside the destination, every bundle, every backup,
  swap; SQLite's other temporary data stays in memory; key erasure = destroying the volume key.
- G2 `docs/threat-model.md` `## Deployment obligations` evidence bullet names volume encryption + the
  same files; `## Deliberately absent` `Encryption and key erasure` → field-level encryption + the
  volume-key sentence; gains a registry line (origin comes from signatures).
- G3 README registry recipe: export → `ssh-keygen -Y sign` → `oras push`; consumer `oras pull` →
  `function eval --signature --allowed-signers`; the allowed signers file (and an expected hash, if
  pinned) never travels through the registry; Cement adds no network code.
- G4 No other claim moves: README `CLI actor names are recorded assertions, not authentication` stays
  (E1 deferred, p140).

## Gates (numbered; rerun from committed state)

1. `uv run python .agent/register-audit --gate`, `uv run python .agent/article-audit`,
   `uv run python .agent/decisions/m3u6a2-tripwires.py` → rc 0 / PASS.
2. Fast gate over the README + docs readers: `.agent/gate tests.test_cli_removal_battery
   tests.test_cli_channels_battery tests.test_lifecycle_removal_battery tests.test_authority_removal
   tests.test_submission_battery tests.test_cli_channels tests.test_proposal_binding_battery`.
3. Full gate = CI gate (`.agent/ci-gate p135-docs`).

```claims
37	`uv run python .agent/decisions/m3u6a2-tripwires.py` → rc 0 / PASS.	unchecked	a gate expectation, not a count	-
```
