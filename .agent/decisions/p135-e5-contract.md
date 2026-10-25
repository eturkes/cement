# p135-e5 contract — bundle signatures verified inside `function eval` (revision 3)

Plan: `.agent/decisions/p87-milestone.md` E5. Owner rulings (`.agent/spec.md` `Decisions` Deployment
trust): D6 the person who switched a version on signs its export with their own SSH key; D7 FIDO
`sk-*` keys refused with the key type named; Ed25519 = Cement's own stdlib RFC 8032 code.
Tier `kernel`: a signature verdict has no downstream re-check. Revision 1 → 2 = the advisor's read
(MAIN-adopted; security vocabulary keeps teammates off this unit): fixture key custody, a two-way
differential with a named test signer, Trusted/Untrusted placement, the key-type recognizer, names.
Revision 2 → 3: G5 keeps the `_read_function_bundle(value: str) -> str` seam, binding since
`.agent/decisions/m2u4c6-contract.md` (tests patch it), and verifies over the text's UTF-8 encoding.

## Premises (measured at `331a3b4`)

- F1 `function eval` = `cli._run`'s first branch: input graded, `_read_function_bundle` (one
  `O_NONBLOCK` open, `fstat` regular, ≤ `FUNCTION_MAX_BYTES`, strict UTF-8 → `str`), `parse_function`,
  `evaluate`; no `System`, no SQLite. stdout keys `artifact_hash`, `function_hash`, `matched`,
  `output`; exit 0 hit, 6 miss, 5 `expected_function_hash` mismatch.
- F2 `tests/test_hospital_ocr_example.py` `test_the_eval_child_opens_no_database_file`: a child-installed
  audit hook records `open` + `sqlite3.connect`; eval opens the bundle, connects nothing and opens no
  other file in the bundle's directory.
- F3 Stdlib has `hashlib.sha256/sha512`, `binascii.a2b_base64(strict_mode=True)` (3.11+), no
  public-key signature. Spike `.scratch/p135/ed25519_spike.py` (strict policy below) over Wycheproof
  `testvectors_v1/ed25519_test.json` (C2SP/wycheproof `d17cc89`, sha256 `ea80ffeb…b74b3`): 210 tests,
  0 mismatches — 117 `valid` accepted, 64 `invalid` rejected, 29 `acceptable` rejected; 3.6 ms per
  verify.
- F4 OpenSSH 10.6p1: `ssh-keygen -Y sign -n <ns> -f <key> <file>` writes `<file>.sig`, armored, 70-char
  base64 lines; blob per PROTOCOL.sshsig (magic `SSHSIG`, uint32 version 1, string publickey, string
  namespace, string reserved, string hash_algorithm `sha512` default | `sha256` via `-O hashalg=`,
  string signature = string keytype + string 64 bytes). Signed data = `SSHSIG` + string namespace +
  string reserved + string hash_algorithm + string H(message). `sshsig.c`
  `parse_principals_key_and_options`: one malformed allowed-signers line fails the whole check;
  principals = a pattern-list (optionally double-quoted); options `cert-authority`, `namespaces=`,
  `valid-after=`, `valid-before=` (keywords case-insensitive).
- F5 A new `src/cement_runtime/*.py` enters the src censuses (`tests/test_authority_removal.py`
  `SOURCES`, `tests/test_lifecycle_removal_battery.py` `_tracked_src_paths`,
  `tests/test_outcome_removal_battery.py` `_src_paths`, `tests/test_relocation_battery.py` R3/R4) and the
  embedded copies (Open WebUI paste-ins, `examples/nucllei/ext/bin/cement`) ⇒ both generators rerun.
  `cement_runtime.__all__` stays unchanged (frozen pins); the verifier is imported as
  `cement_runtime.signature`, like `cement_runtime.learning`.

## Obligations

- G1 Ed25519 (`signature._ed25519_verify(public, message, signature) -> bool`, private): total over
  all `bytes` inputs (never raises); lengths 32/64; A and R decoded canonically (y < p; x recovered
  or refused; x = 0 with the sign bit set refused); S < L; A of prime order and not small order
  (`[8]A ≠ O` and `[L]A = O`); cofactorless `[S]B = R + [k]A`, k = SHA-512(R ‖ A ‖ M) mod L. Strict
  policy = Wycheproof `acceptable` (small/mixed-order keys) rejected. An honest key `[a]B` is of
  prime order, so the policy never refuses an `ssh-keygen` signature.
- G2 SSHSIG reader (`signature._read_sshsig(text) -> _Envelope`, private), strict: first line exactly
  `-----BEGIN SSH SIGNATURE-----`, last non-empty line exactly `-----END SSH SIGNATURE-----`, body
  lines joined + `a2b_base64(strict_mode=True)`; blob = magic, version 1 (other → refused, the version
  named), publickey, non-empty namespace, reserved (kept; it enters the signed data), hash algorithm
  ∈ {`sha256`, `sha512`}, signature, no trailing bytes; the signature's key type equals the public
  key's. `ssh-ed25519` = 32-byte key + 64-byte signature. FIDO types (`sk-ssh-ed25519@openssh.com`,
  `sk-ecdsa-sha2-nistp256@openssh.com`) → `ValidationError` naming the type as a FIDO security key
  type (D7); any other type → `ValidationError` naming it.
- G3 Allowed signers (`signature._read_allowed_signers(text) -> tuple[_Signer, ...]`, private): a
  blank line or one whose first non-space character is `#` is skipped; else fields = principals
  (one token, or one double-quoted token), optional options, key type, base64 key, optional comment.
  A token is a key type when it starts with `ssh-`, `ecdsa-sha2-` or `sk-`, or ends with
  `-cert-v01@openssh.com` (OpenSSH's key names); the token after the principals is the key type when
  it is one, else the options, and then the next token must be a key type. Principals: comma-separated, each non-empty; `*`, `?` or `!` → refused (Cement matches exact
  principals; a pattern would widen trust silently). Options: comma-separated outside quotes,
  keyword case-insensitive; `namespaces="a,b"` = an exact namespace list (pattern characters
  refused); `cert-authority`, `valid-after`, `valid-before` and any other keyword → refused (ignoring
  a restriction would widen trust). Key type `ssh-ed25519`: the blob decodes to that type + 32 bytes
  with no trailing bytes; any other key type: the line is skipped (Cement never trusts it, so no
  false acceptance follows). Every refusal = `ValidationError` naming its 1-based line number; one
  malformed line refuses the file (F4).
- G4 `signature.verify_signature(data: bytes, signature: str, allowed_signers: str, *, namespace:
  str, signer: str | None = None) -> SignatureVerification` (public). Arguments type-checked first
  (`ValidationError`). Order: allowed signers parsed (G3), envelope parsed (G2), namespace equal
  (`IntegrityError` naming both), signing key listed on ≥ 1 line admitting `namespace` (no
  `namespaces=` option = every namespace) → principals = the union over those lines, sorted; none →
  `IntegrityError`; `signer` given and absent from them → `IntegrityError`; Ed25519 over the signed
  data (F4) false → `IntegrityError`. `SignatureVerification(principals, fingerprint, hash_algorithm)`,
  `fingerprint` = `SHA256:` + unpadded base64 of SHA-256 over the key blob (the form `ssh-keygen`
  prints). Data is hashed whole; the caller bounds it.
- G5 CLI `function eval --signature FILE --allowed-signers FILE [--signer PRINCIPAL]`: the two files
  together or neither, `--signer` only with them → exit 2 (usage) otherwise. Reads: the bundle through
  `_read_function_bundle` (strict UTF-8 text; strict decoding is a bijection, so its UTF-8 encoding
  = the file's exact bytes), the signature (regular file, ≤ 65,536 bytes, strict
  UTF-8), allowed signers (regular file, ≤ 1,048,576 bytes, strict UTF-8). Order: input graded,
  bundle read, signature + allowed signers read, `verify_signature(…, namespace="cement-function-v3")`
  over that encoding, then `parse_function` + `evaluate`. Verifying adds stdout keys
  `signers` (the principals) + `signing_key` (the fingerprint); a refusal = exit 2 (malformed or
  unsupported) or 5 (verdict), stdout empty, nothing parsed. Without the flags, stdout, stderr and
  exit are byte-identical to `331a3b4`.
- G6 Ledger-free + process-free: with the flags, the eval child opens exactly the bundle, the signature
  and the allowed-signers file, connects no SQLite and raises no process-creation audit event
  (`subprocess.Popen`, `os.exec`, `os.posix_spawn`, `os.fork`, `os.system`).
- G7 Docs: README `### Answering one input from the ledger` neighbourhood → a signing + verifying recipe
  (`ssh-keygen -Y sign -n cement-function-v3`, the allowed-signers subset, D6's signer), the
  `## Outcomes` table rows for the new refusals, `## Deployment boundary` E5 sentences; the threat
  model E5 bullets (`## Enforced controls` hash bullet, `## Deployment obligations` last bullet,
  `## Deliberately absent` `External signatures` removed); `## Trusted` gains the allowed-signers file
  (the trust root of a verified eval, beside the channel that delivers an expected hash);
  `## Untrusted` gains the signature file (parsed as untrusted input, beside exported bundles).
- G8 Instruments: `tests/ed25519_signer.py` = a test-only RFC 8032 signer + SSHSIG armorer that the
  suite uses for variants no committed fixture provides (namespace, reserved, hash algorithm,
  bound sizes); it never enters `src/`. Fixtures `tests/fixtures/signature/` come from
  `.agent/decisions/p135-e5-fixtures.sh`: an ephemeral `ssh-keygen` key signs, and only the public
  key, the signed files, the signatures and the allowed-signers files are committed — no private key
  enters the repository (the `secrets` step), and a regeneration changes the fixtures, never that custody.

## Gates (numbered; rerun from committed state)

1. New tests red at `331a3b4` (detached worktree + these test files): RFC 8032 §7.1 TEST 1, 2, 3,
   1024, SHA(abc) verify and each with one flipped bit refuses; Wycheproof (fixture = the F3 file
   verbatim): every `valid` accepted, every `invalid` rejected, every `acceptable` rejected, counts
   117/64/29; `ssh-keygen` fixtures (sha512, sha256, `namespaces=` option, quoted principals) verify;
   one flipped byte in the bundle or in each envelope field (key, namespace, reserved, hash
   algorithm, signature) refuses before parse (spy: `parse_function` not called); namespace and
   principal mismatch refuse; each G3 refusal names its line, another key type is skipped; FIDO + RSA
   key types refused by name; adjacent pairs at 65,536 / 65,537 and 1,048,576 / 1,048,577 bytes; CLI
   exit classes + empty stdout + the two keys; flag pairing exit 2; G6 by audit hook.
2. Full gate = CI gate (`.agent/ci-gate p135-e5`).
3. `p32-differential.py --base 331a3b4` → `SAME`; the two-way differential
   `.agent/decisions/p135-e5-differential.py` (rc 0): every `ssh-keygen`-made variant → Cement accepts,
   every G8-signer-made variant → `ssh-keygen -Y verify` accepts, and each flipped-byte variant → both
   refuse; register + article audits rc 0.

```claims
1	(revision 3)	unchecked	the contract's own revision number, not a count	2
5	own stdlib RFC 8032 code	unchecked	a document number, not a count	8032
6	Revision 1 → 2	unchecked	revision numbers of this contract, not counts	1
9	Revision 2 → 3	unchecked	revision numbers of this contract, not counts	2
17	exit 0 hit	unchecked	CLI exit classes read from `cli._run` at 331a3b4 by MAIN, not counts	0
23	): 210 tests,	unchecked	the spike's run over the Wycheproof file (scratch); gate 1 reruns it as a committed test	210
24	117 `valid` accepted	unchecked	the spike's tally (scratch); gate 1 pins 117/64/29 in a committed test	117
29	string keytype + string 64 bytes	unchecked	the Ed25519 signature length (RFC 8032), not a repo count	64
51	version 1 (other	unchecked	the SSHSIG version constant (PROTOCOL.sshsig), not a count	1
66	that type + 32 bytes	unchecked	the Ed25519 public-key length (RFC 8032), not a count	32
73	≥ 1 line admitting	unchecked	a quantifier in the obligation, not a measured count	1
80	→ exit 2 (usage)	unchecked	an exit class (`.claude/rules/runtime.md`), not a count	2
86	a refusal = exit 2	unchecked	exit classes (`.claude/rules/runtime.md`), not counts	2
99	a test-only RFC 8032 signer	unchecked	a document number, not a count	8032
108	TEST 1, 2, 3,	unchecked	RFC 8032 §7.1 vector names, not counts	1
119	differential.py` (rc 0)	unchecked	a gate expectation of the unbuilt unit	0
121	audits rc 0.	unchecked	a gate expectation of the unbuilt unit	0
```
