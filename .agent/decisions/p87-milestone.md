# p87 milestone contract — deployment trust (planned, unbuilt)

Row (verbatim acceptance, `.agent/deferred.md` → `.agent/archive/deferred-closed.md`): planned as a
milestone whose contract names each property's enforcement point (who authenticates a switch actor,
which key signs a bundle and who verifies it, which rows a retention policy deletes) and the
`docs/threat-model.md` row each one changes.
Status: plan only. Building it = row p135 (an IMPLEMENT-sized milestone, routed by the owner).
Tier when built: `kernel` (authentication, erasure and signature checks have no downstream
re-check). Owner decisions D1-D7 bind the build; each names the default this plan recommends.

## Premises (measured at `61bca08`)

- P1 Fifteen public writes take an actor string, graded by `_text(…, maximum=256)` alone:
  `registered_by` (`register_operation`), `revised_by` (`revise_operation`), `reviewer` (`review`,
  `challenge`, `supersede_examples`), `compiled_by` (`compile`), `verified_by` (`verify_drafts`,
  `verify`), `promoted_by` (`promote_function`, `promote`), `revoked_by` (`revoke_example`),
  `suspended_by` (`suspend_artifact`), `actor` (`set_projection`, `set_switch`, `quarantine`).
  `submit_proposal` + `propose` take none (`source_id` names an observation, not a person).
- P2 Integrations: the Open WebUI action passes `open-webui:<user id>` after Open WebUI's own session
  login + role `admin` (`.claude/rules/open-webui.md`); the nucllei command passes the constant
  `nucllei-user`, because the jail carries no chat/message id and runs every user as uid 65534
  (`.claude/rules/nucllei.md`); the CLI passes its `--actor` text.
- P3 M3.1 removed the authority callback (`tests/test_authority_removal.py`): Cement decides no
  permission. Every property below keeps authorization (who may act) outside Cement.
- P4 `cement_runtime` is stdlib-only and ships embedded (Open WebUI paste-ins, nucllei
  `/ext/bin/cement`, no pip in either). The stdlib offers `hashlib`, `hmac`, `secrets`; no cipher, no
  public-key signature.
- P5 Content columns: `proposals` (input, proposed + final output, provenance, review note),
  `examples` (input, output, `receipt_json`), `artifacts` (input, output, `artifact_json`),
  `test_reports.details_json`, `artifact_tests.detail`; `events` payloads hold ids + digests.
  Delete-refusing triggers guard `examples`, `example_revocations`, `artifact_evidence`,
  `test_reports`, `artifact_tests`, `function_receipts`, `function_memberships`,
  `projection_programs`, `projection_settings`, `switch_settings`, `events`, `schema_metadata`;
  `proposals` + `operations` + `artifacts` rows carry none (artifact build fields + status
  transitions are trigger-guarded).
- P6 `function eval` is ledger-free and process-free by a child-process audit-hook test (README
  `Deployment boundary`); a verifier that spawns a process (`ssh-keygen -Y verify`) voids that claim.
- P7 The ledger file is the trust root: a process that can write it can insert rows with raw SQL and
  drop triggers. In nucllei the chat model reaches its user's ledger through `run_shell`
  (`/workspace/.cement/`), so a check that runs only when Cement writes is bypassable there.
- P8 FKs (`PRAGMA foreign_keys = ON`, `temp_store = MEMORY`): `examples.proposal_id UNIQUE
  REFERENCES proposals(id)`; `projection_programs` has no partition column and is shared by every
  partition whose settings, artifacts or receipts name its `program_hash`; `artifact_evidence`,
  `artifact_tests`, `test_reports`, `function_memberships`, `example_revocations` reach their
  partition only through a parent row.

## Properties (enforcement point · mechanism · Cement change · threat-model bullets changed)

- E1 Authenticated actor — the switch first, then every P1 write.
  - Who authenticates: the integration that receives the person's act — Open WebUI's session for the
    action, the OS login of the process for the CLI, the nucllei backend serving `/cement-switch`
    (outside the jail) for nucllei. Cement verifies; it never sees a password.
  - Mechanism: attestation = an SSHSIG signature (namespace `cement-actor-v1`, E5's envelope +
    verifier) over canonical JSON `{actor, action, partition, operation, scope, previous, nonce,
    expires_at_us}` (`scope` = a digest of the call's own arguments, e.g. mode + function hash for
    `set_switch`; `previous` = the digest of the switch row it supersedes, or none), made with the minting side's private key: the person's own key at the CLI
    (`ssh-keygen -Y sign`), the integration's key for Open WebUI + nucllei. Cement holds public keys
    alone (an `allowed-signers` file: principal → key + namespaces), so the verifier cannot mint —
    the nucllei command runs inside the jail the chat model reaches, so a shared HMAC key there
    would let the model mint its own switch token.
  - Cement change: `System(…, allowed_signers=None)`; with signers, every guarded write requires an
    attestation whose action + scope equal the call, unexpired, nonce unseen (UNIQUE nonce in a new
    `attestations` table, written in the call's own transaction) → the verified principal replaces
    the actor argument and the event records `attested`; a refusal writes nothing. The attestation is
    STORED with its row, and `serving` re-verifies the selected switch row's attestation on every
    cold call (P7: a row inserted by raw SQL carries no signature the model can make), so a
    deployment whose ledger is writable by the party it distrusts reads an unattested switch as
    `off`. The `allowed-signers` file then lives where that party cannot write (nucllei: a read-only
    `/ext` mount, never `/workspace`). Under `follow` a forged promotion would still serve the newest
    receipt, so there the safe mode is `pinned` (a pin names a content-bound function hash) unless
    promotions are attested and re-verified too (D2). `previous` refuses a copied older attested row
    while the history stays intact; where the distrusted party can also delete rows (drop the
    triggers), a rollback to an earlier attested state stays possible — only state outside its reach
    (the minting backend's own record) stops it, and the docs say so. Removing a key from `allowed-signers` makes
    every row it attested read as unattested: fail-closed, stated in the docs. Without signers:
    today's behavior, the event records `asserted`. Expiry compares the verifying host's clock, so
    the minting side keeps lifetimes short and the nonce, never the expiry, stops a replay. CLI:
    `--attestation FILE|-`. Authorization stays
    with the minting side (P3): the `allowed-signers` file is deployment configuration, and Cement
    applies no rule beyond "a listed key for this namespace signed exactly this call".
  - Threat model: `## Trusted` bullet 2 (`The CLI records identity strings but does not authenticate
    them`) → asserted vs attested; `## Untrusted` bullet 2 nucllei sentences (`The sandbox cannot
    tell who asked …`) → true only without signers; `## Untrusted` bullet `Frequency by itself,
    reviewer labels without deployment authentication …` → attested labels leave it; `## Enforced
    controls` bullet `A switched-off operation answers nothing. Only \`function switch\` changes the
    switch …` → plus the stored attestation re-verified on serving; `## Deployment obligations` bullet 1
    (`Authenticate and authorize every control-plane call`) → authentication by attestation where
    signers are set, authorization unchanged; `## Deliberately absent` `Remote API and
    authentication` → `Remote API`.
  - D1 public-key attestations (one verifier with E5; the verifier cannot mint) — recommended — vs a
    stdlib HMAC (the verifier holds the minting key: sound only where Cement runs in the minting
    side's own trust domain, e.g. inside Open WebUI). D2 guarded set: `set_switch` alone first (the
    one human gate, `Decisions`) — recommended — vs all fifteen — with `follow` safe only once promotions are attested too. D3 nucllei needs a backend change in
    llens (outside this repo: the backend signs, outside the jail) before its switch is attested.
- E2 Encryption at rest.
  - Enforcement point: the storage layer under every plaintext copy — an encrypted volume
    (dm-crypt/LUKS, fscrypt, the cloud disk's encryption; Open WebUI's data volume on such a disk)
    plus encrypted swap. Cement holds no key (P4).
  - Cement change: none in the runtime; README `Deployment boundary` + `docs/threat-model.md` name
    the mechanism and the files it must cover: `<ledger>`, `<ledger>-journal` (rollback journal =
    page images; `-wal` + `-shm` where an operator switched modes), the export's mode-0600 temporary
    file in the destination directory, every bundle, every backup. SQLite temp files stay in memory
    (`temp_store = MEMORY`, P8).
  - Threat model: `## Deployment obligations` bullet `Minimize, redact, encrypt, expire, and back up
    evidence …` → names volume encryption + the file list; `## Deliberately absent` `Encryption and key
    erasure` → `Field-level encryption; key erasure = destroying the volume key`.
  - D4 an optional field-encryption extra (`cryptography`, AES-GCM) breaks the paste-in + jail
    embeddings (P4) → not recommended.
- E3 Retention.
  - Rows a policy deletes: (a) `proposals` that no `examples` row references (P8: the FK refuses a
    referenced one), older than the policy's age (no trigger guards them, P5): `cement retention
    prune --older-than DAYS`; the age must exceed the learning cadence, since a pruned pending
    proposal no longer counts toward recurrence; `proposal.created` events keep the bare id. (b) every
    row of one partition in every table (tenant offboarding): `cement partition erase`, one
    transaction, each `*_no_delete` trigger gaining a grant clause (`WHEN NOT EXISTS (SELECT 1 FROM
    erasure_grants WHERE partition = <the row's partition>)`, reached through the parent row for the
    P8 child tables), the grant row inserted and deleted inside that transaction, one content-free
    tombstone in a new `erasures` table (partition digest, per-table counts, actor, time);
    `projection_programs` rows go only when no other partition names their hash (P8). Never: the
    confirmed evidence, artifacts and receipts of a live partition — they ARE its functions; a case
    leaves through `revoke_example` + the next promotion, its bytes through (b). Backups keep erased
    rows until the deployment's backup retention expires them (docs).
  - Bundles live outside the ledger: their retention = the deployment deletes the files.
  - Cement change: schema v4 (new tables + trigger clauses); D5 migration v3 → v4 (pre-1.0 the v3 cut
    shipped without one, `Decisions`).
  - Threat model: `## Enforced controls` bullet `Function receipt and membership rows are
    database-immutable …` → `… except inside a partition erasure`; `## Deployment obligations` bullet
    `Minimize, redact, encrypt, expire …` → names `retention prune` + `partition erase`.
- E4 Remote registry.
  - Enforcement point: none in Cement — the registry is any store the deployment runs (an OCI
    registry through ORAS, an object store, a git repository). Trust never comes from the registry:
    it comes from E5 + the expected hash at the consumer.
  - Cement change: none (no network code in `cement_runtime`, Intent: library + CLI); README recipe.
  - Threat model: `## Deliberately absent` gains `A registry service: store bundles anywhere; origin
    comes from signatures`.
- E5 Bundle signatures.
  - Key that signs: the deployment's release key of whoever publishes an exported version (D6
    recommends the person who switched it on), through OpenSSH `ssh-keygen -Y sign -n
    cement-function-v3 -f <key> <bundle>` (Ed25519; existing keys + agents; hardware-token keys = D7).
  - Who verifies: the consumer, inside `cement function eval --signature <file> --allowed-signers
    <file>` (library: one public verifier beside `parse_function`) BEFORE the bundle parses: Cement checks the SSHSIG envelope (namespace, hash algorithm,
    principal against `allowed-signers`) and the Ed25519 signature IN-PROCESS (pure-Python RFC 8032
    verify), so eval stays process-free (P6). Oracles: RFC 8032 test vectors + signatures produced by
    `ssh-keygen` itself.
  - Threat model: `## Enforced controls` bullet `… The hash is unkeyed, so neither mode proves origin
    or acts as a signature …` → a verified signature proves the allowed signer; `## Deployment
    obligations` last bullet (`If the database-file trust root is insufficient, protect or sign
    exported artifacts …`) → key custody + `allowed-signers` stay the deployment's; `## Deliberately
    absent` `External signatures …` → removed.
  - README `Deployment boundary` sentences each property changes: `CLI actor names are recorded
    assertions, not authentication` (E1); `Authentication, authorization, encryption, retention,
    signing, and tenant-aware API access all remain deployment responsibilities` (E1, E2, E3, E5);
    `The bundle is plaintext …` (E2, E5).
  - D6 signer = the switching person (recommended) vs a CI identity; D7 FIDO `sk-ssh-ed25519` keys
    (different signed data) supported or refused (recommended: refused, named in the error).

## Gates (the build's numbered list; rerun from committed state)

1. Red-first per property. E1: with signers, each guarded write refuses a missing, expired (adjacent
   expiry pair), wrong-action, wrong-scope, unlisted-signer and replayed attestation with zero writes; a switch
   row inserted by raw SQL (triggers intact) reads as `off` in `serving`, and so does a copy of an
   older attested row (its `previous` no longer matches); a key removed from
   `allowed-signers` turns its rows unattested; without signers,
   behavior byte-equal to today (`p32-differential.py` `SAME`). E3: prune deletes exactly the
   unreferenced proposals past the age (adjacent age pair, a referenced one kept); erase leaves zero
   rows of the partition in every table (set derived from `sqlite_master`) and a collision-pair
   partition (`tenant_a` / `tenantXa`) intact, a `projection_programs` row shared with it kept;
   every trigger still refuses a delete without a grant.
   E5: an `ssh-keygen`-made signature verifies; one flipped byte in bundle, signature, namespace or
   principal refuses before parse; RFC 8032 vectors pass; the eval audit-hook test stays green.
2. Full gate = CI gate (D28 included).
3. `docs/threat-model.md` + README `Deployment boundary` rewritten per bullet above; register +
   article audits rc 0; each changed claim re-derived against shipped code.

Order: E5 (the ledger-free path has no other origin check; builds the SSHSIG + Ed25519 verifier) → E1 (`set_switch`, reusing it) → E3 → E2 + E4 (docs).

```claims
21	uid 65534	unchecked	an external fact of nucllei-sandbox v20261020-01 recorded in `.claude/rules/nucllei.md` Jail facts; no committed artifact reproduces it	65534
81	bullet 2	unchecked	a position in `docs/threat-model.md` `## Trusted` at 93ff847, read by MAIN; positions are no counts	2
86	bullet 1	unchecked	a position in `docs/threat-model.md` `## Deployment obligations` at 93ff847, read by MAIN	1
115	SELECT 1	unchecked	an SQL literal inside a planned trigger clause, not a count	1
142	RFC 8032	unchecked	a document number, not a count	8032
```
