# M4/M5 contract — schema v3, switch + versions, projection, learning pass, Open WebUI example

Status: REVISION 3 + implementation amendments (A1 receipt ABI name, A2 S7 read-side, A3
p50/p51 surface, A4 source_id submission key, A5 contradiction = state, A6 `--program` channel,
A7 build-current program read surface) —
consultant-1 rows C1-C8 + X1-X7 + its re-review of revision 2 ruled
(`.agent/review.md` M4/M5 contract section), owner rulings O1-O9 below. Every unit = tier `kernel` unless marked. Every predicate =
a test or a gate check; a unit closes on its numbered gate list rerun from committed state (§9).

## Owner rulings this contract implements (`.agent/spec.md` Intent + Decisions)

- O1 learning pass built now; the only reviewer (`learning-pass`); it compiles, verifies, promotes.
- O2 `CompilePolicy` defaults 2 / 1 / 0; the person's switch = the ONLY human gate.
- O3 switch per operation = `off` | `follow` | `pinned` (function hash); versions = promotion
  receipts; rollback = pin.
- O4 rollback reaches ANY earlier version, across operation revisions (resets) too, subject to the
  contrary-evidence checks of §3.
- O5 M4 built now: case = projected key; projection = constrained JSON IR authored by the learning
  pass, verified by Cement.
- O6 the LEARNING PASS decides whether an operation's answers depend only on structure (so a
  projection may apply); no operator flag; the Read view states the assumption at switch-on.
- O7 duplicate retention is prevented by Cement: a proposal may carry a source-observation id,
  unique per (partition, operation); a repeat is refused as a conflict (exit 4).
- O8 Open WebUI capture = a `record_answer` tool (the model's structured output per call) + a
  filter keeping the final reply as provenance and flagging a miss with no record.
- O9 the example ships the Tool path only; a Pipe mode is out of scope (no queue row).

## 0. Terms + guarantees

- **case key** — the canonical JSON one entry matches: the canonical input (exact mode, unchanged)
  or `P(input)` under projection P.
- **projection program** — a `cement-projection-v1` document (§4). Content identity =
  `program_hash` (sha256 of its canonical JSON). A **projection setting** = one append-only row
  naming the program that NEW builds of one (partition, operation, revision) use.
- **version** — one promotion receipt = one function snapshot, named by `function_hash`; a version
  OWNS its projection (the receipt binds `projection_hash`, the document embeds the program).
- **switch** — per (partition, operation), append-only settings; current = newest; none ⇒ `off`.
- **source observation** — one retained request: deployment + chat + user message + call input;
  its id makes a repeat delivery a refused duplicate (O7).

Guarantees published (README + docs, M3.9a), stated separately (C2):
- G1 grammar: a projected input was fully recognized by the declared grammar; anything else gets no
  key and goes to the LLM.
- G2 consistency: every confirmed example under a key agreed on its output when the version was
  built, and no active contrary evidence exists when a version answers (§3).
- G3 NOT guaranteed: semantic correctness. A projection ASSUMES the answer depends only on the
  form's structure, never its values; the learning pass decides that (O6) and the Read view says
  "answers every form with this layout the same way, whatever its values". Two normal lab slips
  confirmed as `{"abnormal": false}` would let an abnormal slip receive the same answer — the
  documented residual risk the person's switch accepts. A wrongly merged output is likewise only as
  correct as the learning pass's confirmation (README already disclaims domain correctness).

## 1. Schema v3 (M3.6b, the single cut; v3 stays unreleased until the phase close — S5)

Prose pins re-targeted in M3.6b under the standing pin-repair approval: every pinned sentence
stating that Cement gives no idempotency (e.g. `test_d23_there_is_no_idempotency_two_byte_identical_
submissions_ret`, README "Two identical submissions write two proposals") becomes "without a
source id" — the burden run lists them by id.

Kept from the M3.6b plan: proposals get direct `operation`, `operation_revision`, `input_json`,
`input_hash` columns; `requests` + `requests_scope` deleted; refusal of v2 ledgers; package
0.2.0; p04 receipts index; p50 existing-only read-only construction = keyword-only
`System(path, create=False)` / `Store(path, create=False)` (missing ledger → `IntegrityError`
before any connection, validation on the read-only connection, nothing written); p51 = ONLY
`operation register` constructs `create=True`, after grading partition, operation, actor and
policy, so no other leaf creates a ledger from a typo'd `--db` (exit 5).

New or changed, all STRICT, append-only where marked (no-update + no-delete triggers):
- `proposals.source_id` TEXT NULL (1-512 chars, no control characters) + partial UNIQUE INDEX
  `(partition, operation, source_id) WHERE source_id IS NOT NULL` (O7).
- `examples`: `origin` CHECK gains `'superseded'`; `supersedes_example_id` TEXT NULL UNIQUE
  REFERENCES examples(id) (each example superseded at most once); `source_id` TEXT NULL copied
  from its proposal (or from the superseded example). Examples stay immutable.
- `projection_programs` (`program_hash` TEXT PRIMARY KEY, `program_json` TEXT, `abi` TEXT) —
  append-only; insert-or-ignore by hash; a stored row whose JSON does not hash to its key is
  refused ON READ (`IntegrityError`) — SQLite triggers cannot compute sha256, so S7 is a read-side
  check owned by the M4.2 battery.
- `projection_settings` (`sequence` PK AUTOINCREMENT, `id` UNIQUE, `partition`, `operation`,
  `operation_revision` ≥ 1, `program_hash` REFERENCES projection_programs, `set_by`,
  `set_at_us`) — append-only; index (partition, operation, operation_revision, sequence).
- `switch_settings` (`sequence` PK AUTOINCREMENT, `id` UNIQUE, `partition`, `operation`, `mode`,
  `receipt_id` NULL, `function_hash` NULL, `set_by`, `set_at_us`) — append-only; CHECK
  `(mode = 'pinned' AND receipt_id IS NOT NULL AND function_hash IS NOT NULL) OR (mode IN
  ('off','follow') AND receipt_id IS NULL AND function_hash IS NULL)`; composite FOREIGN KEY
  `(receipt_id, function_hash) REFERENCES function_receipts(id, function_hash)`; a trigger refuses
  a pinned row whose receipt belongs to another (partition, operation).
- `artifacts.projection_hash` TEXT NULL REFERENCES projection_programs (NULL = exact mode);
  joins the immutable build fields and `build_hash`.
- `function_receipts.projection_hash` TEXT NULL; the receipt hash covers it (receipt hash format
  `cement-function-promotion-v2`). The function ABI moves with the cut: from M3.6b on, a v3 ledger builds
  `cement-function-v3` documents only (exact mode = `projection: null`), so every v3-ledger receipt
  binds a v3 function hash and reconstruction never needs the v2 builder; the v2 READER stays for
  external bundles (L6). M4.2 fills `projection`.
- `function_receipts` index (partition, operation, sequence) (p04).

Predicates:
- S1 `SCHEMA_VERSION` 3 + `SCHEMA_FINGERPRINT` move together; a v2 ledger refuses to open
  (library `IntegrityError` class, CLI exit 5), the message naming the reset.
- S2 each append-only table refuses UPDATE + DELETE (positive control: the row exists).
- S3 `switch_settings` CHECK: every half-populated combination refused — (off, r, NULL),
  (off, NULL, h), (follow, r, NULL), (follow, NULL, h), (pinned, r, NULL), (pinned, NULL, h) —
  beside accepted (off, NULL, NULL), (follow, NULL, NULL), (pinned, r, h); a receipt/hash pair
  that is not one receipt's refused by the composite FK; a foreign-operation receipt refused.
- S4 `requests` absent from `sqlite_schema`; residue census over `src/` (tokenize) + a structural
  pin that no query names it.
- S5 a later unit needing a v3 column amends v3 in place and records it under §1 (fingerprint
  moves, `SCHEMA_VERSION` stays 3).
- S6 `source_id` uniqueness: a second proposal with the same (partition, operation, source_id) →
  `ConflictError` naming the existing proposal id, nothing written; same source_id under another
  operation or partition → accepted; `source_id` NULL → no uniqueness (manual submissions).
- S7 `projection_programs` refuses a row whose JSON does not hash to its key.

## 2. Supersession + source observations (M3.6b schema, behavior in M5.2)

- `System.supersede_examples(partition, operation, *, example_ids, output, reviewer, note)` — one
  write: per old example a new example (same partition, operation, revision, input, source_id;
  `output` = the new merged output; origin `superseded`; `supersedes_example_id` = old). Refused
  (nothing written) for: a revoked or already-superseded example; examples of another operation;
  an empty id list; an output equal to the old one.
- Active example = confirmed, not revoked, not superseded. Compile, conflict and support use active
  examples OF THE CURRENT REVISION ⇒ one support credit per source observation however many times
  it is re-merged; pin checks (§3) read the receipt's own revision.
- Follow-mode window: between a supersession (or any new conflicting confirmation) and the next
  promotion, the live set fails verification on contrary evidence → resolve = failed verdict → the
  caller asks the LLM. The skill therefore runs supersede → compile → verify → promote in one pass.
- Predicates: X1a first pass confirms `{fields:[patient]}` ×2 → promoted v1; a later request needs
  `provider`; supersede both old examples to `{fields:[patient,provider]}` + confirm the new
  proposal with it → compile builds ONE artifact, support 3 (the consultant's repro, now green);
  X1b supersession never raises support (support before = after for the superseded set); X1c a
  superseded example still validates v1 when v1 is pinned (it is a revised judgment, not contrary
  evidence); X1d refusal cases write nothing (row + event counts unchanged).
- `submit_proposal(..., source_id=None)` (≤ `SOURCE_ID_MAX_BYTES` = 512 UTF-8 bytes, control-free);
  CLI channel = an optional `source_id` key of the `--submission` object (no flag: the submit
  grammar stays one positional + one option), `SUBMISSION_MAX_BYTES` derived with it; pinned by
  `tests/test_schema_v3_battery.py` S6. Supersession receipts = `cement-supersession-v1`.

## 3. Switch + versions (M5.1)

Library:
- `System.set_switch(partition, operation, *, mode, actor, function_hash=None) -> SwitchState`:
  `pinned` names any receipt of this (partition, operation), ANY revision (O4) — the newest receipt
  bearing the hash binds `receipt_id`; `off`/`follow` take no hash. One write: one row + one
  `function.switched` event (mode, function_hash, receipt_id, previous mode + hash). Refusals
  (nothing written): unregistered operation (`NotFoundError`); unknown hash, a hash of another
  operation, hash with off/follow, pinned without hash (`ValidationError`).
- `System.switch(partition, operation) -> SwitchState` (read-only; no row → `off`).
- `System.function_versions(partition, operation, *, limit=100, before_sequence=None)` → receipts
  page; each row: receipt fields + `projection_hash` + `revision_current: bool` + `selected: bool`.
  `selected` = the receipt the switch names (pinned) or the newest receipt of the current revision
  (follow); none when off or when follow has no receipt yet. Eligibility (would it serve right
  now) = a separate field `servable: bool | None` computed only when asked (`--check`), since it
  costs a verification.
- `System.diff_versions(partition, operation, *, from_hash, to_hash)` → scope (revision, policy
  hash), projection (hashes + program changed: bool + the two programs) and entries (added /
  removed / changed by case key). Read-only.
- Selected-version serving — `resolve` and `function export` (no `--receipt-id`) read switch +
  receipt + program + evidence in ONE read transaction (C5):
  - `off` → no function verification; result: `switch="off"`, `passed=None`, `matched=None`,
    `output=None`, `artifact_hash=None`, `function_hash=None`, `entries=None`, `checks=[]`. A
    supplied `expected_function_hash` is validated for syntax only. CLI exit 6.
  - `follow` → the newest receipt of the CURRENT revision must be the live promoted set
    (`verify_function`'s seven checks, §5) + lookup. No receipt → verified absence of a function:
    `passed=True`, `entries=0`, `matched=False`.
  - `pinned` → reconstruct the pinned receipt (as `function export --receipt-id` does) + pin checks
    (C3, X7): P-a the reconstruction binds the receipt; P-b no member's evidence example is
    revoked; P-c no member artifact is suspended; P-d no EXPLICIT NEGATIVE JUDGMENT on a member's key:
    no `challenge`-origin counterexample whose raw input maps (under the receipt's OWN projection)
    to a member's key. A newer different output is a REVISION, not a contradiction: a supersession
    or a fresh conflicting confirmation blocks new follow-mode builds (the conflict rule) but never
    unpins a version — a deliberate pin is exactly the rollback a person chose (O3/O4). Wrong
    evidence is retired by REVOKING it (P-b); a wrong historical member is invalidated by
    SUSPENDING it, which v3 allows for `retired` artifacts too (`retired → suspended` joins the
    lifecycle trigger) — the explicit route for a pin after a reset or a supersession. Review no
    longer auto-suspends: a confirmation that conflicts with a promoted artifact makes the LIVE set
    fail verification (follow → failed verdict → LLM) and leaves every artifact's status alone, so a
    pin on a still-promoted v1 survives it. Contrary evidence is a ledger STATE, never corruption:
    read surfaces (`artifact show`, `function_report`) and `challenge` grade a promoted artifact's
    integrity alone; the promotion plan refuses (`StateError`, exit 4) while a contradicted member
    has no verified replacement, naming supersede, revoke or suspend as the remedies. Any failure →
    failed verdict, never an answer.
    P-d's per-call cost (projecting the revision's challenge examples) is measured at 1 / 1,000 /
    50,000 entries and cited, never called cheap.
  - `expected_function_hash` must equal the selected version's hash, else a failed verdict.
- `function eval` unchanged (a bundle = one version; deploying it is the operator's act).

CLI: `cement function switch <op> --mode off|follow|pinned [--function-hash H] --actor A`;
`cement function versions <op> [--check]`; `cement function diff <op> --from H --to H`. `resolve`
prints eight keys in every state: today's seven + `switch`. Exit: 0 = matched; 6 = off, verified
absence or failed verdict (`switch` + `passed` + `matched` separate them).

Predicates:
- W1 default off: a promoted function answers nothing until switched on; off reads the switch +
  operation rows alone (cursor proxy: no artifact, receipt or example table read).
- W2 follow serves the newest version of the current revision with no further switch write.
- W3 pinned keeps serving the pinned version after a newer promotion (rollback).
- W4 pinned across a reset: pin a version of revision 1, revise the operation, resolve still serves
  it (O4); then a revocation of a member's evidence → failed verdict.
- W5 pin checks: the consultant's repro (v1 retired, a later conflicting confirmation, zero
  revocations) → pinned v1 still serves (a revision, not a contradiction); the same + a revocation
  of a v1 member's evidence → failed verdict; a `challenge` counterexample on a v1 key → failed
  verdict; a supersession of v1's evidence → v1 still serves (X1c); W5b v1 still PROMOTED +
  pinned + a fresh conflicting confirmation → pinned v1 serves, follow → failed verdict, no artifact
  status changes; W5c post-reset: pin a revision-1 version, revise, suspend its retired member →
  failed verdict.
- W6 every refusal of `set_switch` writes nothing; each success = one row + one event.
- W7 `versions` across the full history (all pages joined): exactly one `selected` in pinned, one in
  follow with ≥ 1 current-revision receipt, none otherwise.
- W8 `diff`: added/removed/changed by key; a projection change with identical entries reports
  `projection.changed = true` (X4); identical hashes → empty.
- W9 export without `--receipt-id` follows the switch; off → exit 6, empty stdout.
- W10 one snapshot: a switch write committed between two reads of one resolve cannot be observed
  (interleaving probe with a blocking proxy at the second read).
- W11 the hospital example, the prototype and every existing resolve test switch on explicitly
  (behavior changed by ruling); each changed test id listed in the unit's commit body.

## 4. Projection IR `cement-projection-v1` (M4.1) — pure interpreter; `tester` differential oracle

Grounds = `.agent/decisions/m45-research-projection.md` (researcher-2, copied tracked).

Program schema (exact keys and types at every node; anything else = program invalid):
```json
{"abi": "cement-projection-v1",
 "text": "document",
 "keep": ["fields"],
 "layouts": [
   {"name": "progress note",
    "title": "PHYSICIAN PROGRESS NOTE",
    "entries": [{"label": "Patient"}, {"label": "MRN"}, {"label": "Date"},
                {"label": "Provider"}, {"section": "Subjective"}, {"section": "Objective"},
                {"section": "Assessment"}, {"section": "Plan"}]}]}
```
- `text`: a field name (1-128 chars, `[A-Za-z0-9_.-]`). `keep`: sorted, unique field names, ≤ 32,
  `text` ∉ keep. `layouts`: 1-1,000. Each layout: `name` (display only), `title`, `entries` 1-256,
  each exactly `{"label": K}` or `{"section": H}`. Literals 1-256 Unicode scalars; no U+0000-U+001F,
  U+007F-U+009F, U+2028, U+2029; no leading or trailing ASCII space or tab (a literal that could
  never match normalized input is invalid); `label` and `section` literals contain no `:`.
  Program canonical JSON ≤ 64 KiB. Layout identity = (title, normalized entries) — two layouts
  with equal identity = invalid, whatever their names.
- Normalized entry = `{"label": K}` → `["label", K]`, `{"section": H}` → `["section", H]`.

`project(program, input) -> Key | NoMatch(reason)`, total over valid programs + canonical JSON
inputs (an invalid program is refused at validation, never executed):
1. `input`: an object whose key set EQUALS `{text} ∪ keep`, with `input[text]` a string.
   Else `NoMatch("input")`.
2. Normalize `input[text]`: CRLF then CR → LF; split on LF; strip trailing ASCII space + tab per
   line; drop leading + trailing blank lines; collapse blank-line runs to one. A normalized line
   holding any forbidden character above EXCEPT TAB → `NoMatch("text")` (ruling AM2: TAB is
   ordinary text inside input lines — the grammar trims and partitions around it; literals still
   refuse it). Nothing else changes (no NFKC, casefold, Unicode
   whitespace class — research Q7-Q8: UCD 14.0.0 → 16.0.0 across Python 3.11-3.14).
3. Blocks = split on blank lines. Block 0 = title line + label lines. Block k ≥ 1 = a section
   (first line `H:` whose remainder is empty after ASCII trim, then ≥ 1 body lines, no body line
   containing `:`) or a label block (every line a label line). Label line = partition at the FIRST
   `:`; key = left part ASCII-trimmed, non-empty; the remainder = value (opaque, may be empty). A
   line that fits neither → `NoMatch("text")`.
4. Structure = ordered `[kind, key]` pairs; match the layout whose title equals block 0 line 0 and
   whose normalized entries equal the structure. None → `NoMatch("layout")`.
5. Key = `{"form": {"title": T, "structure": [[kind, key], ...]}, "keep": {f: input[f]}}`,
   canonicalized under the canonical-JSON caps (1 MiB, depth 64, 100,000 items); exceeding any →
   `NoMatch("key")` (a valid depth-64 or 1 MiB input can wrap past them), never an exception.
   Values never enter the key; `name` never enters the key.
6. Work: a counter of characters scanned + lines + entries compared, exposed to tests; bound =
   `4 * len(text) + 2 * lines + entries(program)` checked by I7.

API (module `cement_runtime.projection`, stdlib only, importing `cement_runtime.json_value` and
`cement_runtime.errors` alone):
- `PROJECTION_ABI = "cement-projection-v1"`.
- `parse_program(value: object) -> ProjectionProgram` — validates the program object (not text);
  any rule violation → `ValidationError` naming the rule. `ProjectionProgram` = frozen dataclass:
  `text: str`, `keep: tuple[str, ...]`, `layouts: tuple[Layout, ...]`, `canonical: CanonicalJSON`
  (the program's canonical form), `program_hash: str` (= `canonical.digest`).
  `Layout` = frozen: `name: str`, `title: str`, `entries: tuple[tuple[str, str], ...]` (normalized
  pairs).
- `project(program: ProjectionProgram, value: JSONValue) -> Projection` — total; never raises for a
  `value` that `canonicalize` accepts. `Projection` = frozen: `matched: bool`, `key: CanonicalJSON |
  None` (set iff matched), `reason: Literal["input", "text", "layout", "key"] | None` (set iff not
  matched), `work: int` (the §4 step 6 counter).
- `structure(text: str) -> tuple[str, tuple[tuple[str, str], ...]] | None` — steps 2-4 alone (title
  + structure pairs, `None` where the grammar refuses), exposed for the verification probes (§5).

Readings ruled after the diff-blind tester (`archive/m4u1-test`, AM1-AM6): AM1 a block k ≥ 1 led
by an empty-remainder label IS a section (no label-block fallback; body required, colon-free);
AM2 TAB legal in input lines (above); AM3 ASCII space/tab around a label/heading key is an
equivalence; AM4 `work` = any honest counter of characters, lines and compared entries within
the bound, never one algorithm's exact count; AM5 `structure` is grammar-only (no layout registry);
AM6 3.12 + 3.14 byte identity = the CI legs.

Predicates:
- I1 differential (tester): over the seven fixture documents the keys' `form.structure` equals the
  shipped `layout_signature(...)["structure"]` as pairs, and `form.title` equals the documents'
  raw first line under a FIXED fixture map (`layout_a_*` → `PHYSICIAN PROGRESS NOTE`, `layout_b_*`
  → `PATIENT INTAKE FORM`, `layout_c_*` → `LAB RESULT SLIP`); byte-identical keys on 3.11-3.14.
- I2 grammar-preserving value substitution keeps the key: a header-block label remainder replaced
  by any string without forbidden characters or LF; a remainder in a block k ≥ 1 replaced by any
  string NON-BLANK after ASCII trim (declared grammar quirk, mirroring the legacy parser: a block's first line
  with an empty remainder IS a section heading); a section body line replaced by any colon-free
  string that stays non-blank after the trailing ASCII trim.
- I3 a change outside the equivalences (normalization + the ASCII space/tab trim around label and
  heading keys, ruling AM3) never keeps the key: delete, duplicate or
  reorder one structural line (title, label or heading); add an unknown label line; change one
  literal character of the title, a label key or a heading (case included). Trailing ASCII space +
  tab, CRLF/CR and blank-run edits ARE equivalences and keep the key (pinned as such).
- I4 each NoMatch class (`input`, `text`, `layout`, `key`) reachable by an adjacent accept/reject pair.
- I5 program validation: every rule above as an accept/reject pair (`max` beside `max + 1`).
- I6 purity: no filesystem, clock, randomness or ledger (patched `open`, `time.time`, `os.urandom`,
  `sqlite3.connect` raise); repeated calls equal.
- I7 linear work: the work counter stays within its bound for every fixture and for synthetic
  inputs up to 1 MiB / 50,000 lines on matching AND rejecting paths; canonical-JSON cost is
  outside this claim (separate layer).

## 5. Projection lifecycle (M4.2)

- Identities (C5): build-current program = the newest `projection_settings` row of the current
  revision; a version's program = its receipt's `projection_hash`. Setting a program never
  reinterprets an existing version.
- `System.test_projection(partition, operation, program) -> ProjectionReport` — read-only: per
  active example + pending proposal its key or NoMatch reason; per key support, distinct outputs,
  readiness; unwitnessed layouts. A preview only.
- `System.projection(partition, operation) -> {operation_revision, program, program_hash} | None`
  + CLI `projection show <op>` (A7) — read-only: the build-current program (`None` = exact mode).
  The skill's resume rule reads it: an earlier pass's `program.json` that `projection show` does
  not return = a pass stopped before `projection set`.
- `System.set_projection(partition, operation, program, *, actor) -> ProjectionSetting` — ONE write
  transaction: validate (V1); V2 every layout witnessed by ≥ 1 active example of the current
  revision; V3 no key groups active examples with different outputs; V4 ≥ 1 active example
  projects; then insert-or-ignore the program, append the setting + one `projection.set` event,
  and retire (reason `projection superseded`) every draft/verified artifact of the revision whose
  `projection_hash` differs. Canonical-identical to the current setting → no-op returning the
  current setting, nothing written (X3). Promoted artifacts stay (they belong to served versions).
- compile under program P: group active examples by `P(input)`; NoMatch examples excluded and
  reported (`blocked` reason `unprojected` + count); existing gates per key; draft
  `input_json` = key, `projection_hash` = P's hash; build identity includes the hash. Compile reuses
  a LIVE (draft / verified / promoted) artifact with an equal build hash and NEVER revives a retired
  or suspended row: after A→B→A it creates fresh artifacts with A's build hash (content reuse, not
  row reuse) (X3).
- per-artifact verification under P: every supporting example replays `P(input) == key` + output;
  boundary probes partition / operation / revision / input (perturbing the key); plus one
  structural probe per supporting example: deleting its LAST structural line (always exists: every
  layout has ≥ 1 entry) must not project to the key.
- contrary-evidence paths are projection-aware (X7): review-time conflict detection (which now
  invalidates the live set without suspending — §3), `challenge`, and the live promoted-set validation evaluate raw examples under the artifact's OWN `projection_hash` when
  matching them to keys. Predicate X7a: a new confirmation under the same projected key with a
  different output is detected on each of the three paths.
- `cement-function-v3` = v2 + root `projection` (the program JSON, or null) + `projection_hash`
  (or null); entries' `input` = case key; `function_hash` covers both. `evaluate(doc, raw)` projects
  first; NoMatch → `FunctionMatch(matched=False)`. v2 documents still parse + evaluate (L6).
- `verify_function` = seven ordered checks: the six + `projection-uniform` (C4): exact-mode members
  all null, or every member's `projection_hash` equal to the set's; the program row exists,
  validates and hashes to its key; scope/revision match; the receipt binds the same hash; the
  document embeds the program byte-identically. Tests pin the complete ordered vector.
- set promotion: prospective set = members + candidates under the build-current program; members
  under another program are replaced, never mixed. Per-artifact `promote` under a projection is
  refused (`StateError`) — set promotion is the only route that keeps one program per set.

Predicates:
- L1 hospital loop: 7 raw documents → 3 layouts → reviewed + projection set + compile + verify +
  promote + switch follow → a NEW progress note with fresh values resolves to the progress-note
  plan; an intake form with one extra label line → verified absence (NoMatch → miss).
- L2 V2 / V3 / V4 each refuse with nothing written (row, event, artifact-status counts unchanged).
- L3 a program change retires stale drafts/verified (status + reason), keeps promoted; served
  versions keep their own program (pinned P1 version after P2 promotion still projects with P1).
- L4 `unprojected` count exact. L5 bundle evaluation ledger-free (patched `System` +
  `sqlite3.connect` raise) agrees with resolve on every fixture. L6 a committed v2 bundle fixture
  parses + evaluates. L7 `projection-uniform` reds on a fabricated mixed set (labelled fabricated).
- L8 X3: P1 promoted → set identical P1 again = no-op; the full cycle A promoted → B set + promoted
  (A's members retired) → A set again → compile creates fresh rows (no retired row changes status)
  → verify + promote + resolve succeed.
- L9 interleavings (C5): projection set between inspect and promote → promote rejects or plans the
  now-current set; switch / revise / revoke between reads of one resolve unobservable (W10).

## 6. Learning pass (M5.2)

- `CompilePolicy()` defaults 2 / 1 / 0 (O2); bounds unchanged.
- `System.learning_cases(partition, operation, *, program=None)` + `cement learn cases <op>
  [--program JSON|-]` (read-only; the same input channel as `projection test|set`): groups pending proposals AND active examples by case key under
  `program` (a candidate — X1 bootstrap), else the build-current program, else exact input hash.
  Per case: pending proposal ids, active example ids, distinct outputs each with the ids carrying
  it, support, readiness; plus `unprojected` proposals; plus duplicate warnings (same source_id
  can no longer arise — S6 — but proposals without one are listed with their provenance).
- `System.supersede_examples` (§2) + CLI `cement example supersede <op> --output - --reviewer R
  --note N <example_id>...`.
- Skill `skills/cement-learn/` (Agent Skills: `SKILL.md` with `name: cement-learn`, `description`,
  `license: Apache-2.0`; `references/projection.md` = §4 for agents; `references/workflow.md`),
  operator-invoked, CLI only. Workflow:
  1. `learn cases <op>`: it reports pending proposals AND unfinished publication work (cases ready
     to compile, drafts awaiting verification, verified artifacts awaiting set promotion, the live
     receipt). Nothing pending and nothing unfinished → report "nothing to learn" and stop; nothing
     pending but unfinished work → resume at step 4 or 5 (an interrupted pass), adding no support.
  2. Decide projectability (O6): only when every output is a procedure over the input (a plan or
     script that READS values) and contains no value; never for answers interpreted from values.
     If projectable: draft or extend the program from layouts seen in raw inputs only, and rerun
     `learn cases --program -` to group by the candidate keys BEFORE confirming (X1 bootstrap).
  3. Per case: merge the scripts into one output covering every request's needs (union of rows,
     request-driven differences kept, no patient value). Review each pending proposal (`accept`
     when equal, `correct --output` otherwise, `reject` when unusable; reviewer `learning-pass`,
     note = run id + model). Earlier active examples whose output differs from the merge:
     NARROWER (the merge extends them) → `example supersede` to the merge; WRONG (the merge
     contradicts them) → `example revoke` with the reason, which also stops pinned versions built
     on them from answering.
  4. If projectable: `projection test`, then `projection set`.
  5. `compile`; `function verify-drafts --actor learning-pass`; `function inspect`; `function
     promote --expected-function-hash <inspect's> --actor learning-pass`.
  6. Report: the new version hash, `function diff` against the previous (none on a first promotion
     = all added), what was learned, the projectability assumption. NEVER `function switch`.
  Stop and report on any refusal; never retry a write blindly (no idempotency) — enumerate first.
- LP0 resumability: interrupt after the reviews, and again after a supersession; the rerun
  finishes compile → verify → promote with support unchanged; a third run is a no-op.
- Predicates: LP1 a scripted CLI run of the workflow (no LLM; merges = reference plans; the first
  pass deliberately partial, the second expanded — X1's hard case) reaches a promoted version with
  the switch still off, support counted once per observation; LP2 `learn cases` grouping under no
  program / build-current / candidate; LP3 a committed checker validates the skill frontmatter
  (name = directory, 1-64 lowercase/digit/single-hyphen; description ≤ 1024; license) and that
  every CLI command the skill names parses against `_parser()` (red on a misspelled leaf);
  LP4 defaults pinned by signature + ABI test.

## 7. Open WebUI example (M5.3) — capture binding `kernel` (X6), the rest `data`

Grounds = `.agent/decisions/m45-research-openwebui.md` (researcher-1, copied tracked). Open WebUI
0.12.3 (2026-10-16), Python 3.11-3.12, native function calling.
- `examples/open_webui/cement_tools.py` — `class Tools` + `Valves` (ledger path, partition,
  deployment id, allowed operations). Two tools:
  - `use_learned_function(operation, input)` → read-only resolve on the M3.6b existing-only
    constructor: switched-on match → `{"covered": true, "output": ..., "function_hash": ...}`;
    else `{"covered": false, "reason": "off" | "absent" | "failed" | "unrecognized"}` + an
    instruction: answer directly AND call `record_answer` with the structured output you used.
  - `record_answer(operation, input, output)` validates its arguments (operation allowed, input +
    output canonical JSON) and returns `{"accepted": true}` — it WRITES NOTHING (C7): a record is
    evidence only once the response completes and the filter validates it.
- `examples/open_webui/cement_filter.py` — `class Filter`, the SINGLE writer; `outlet(body)` runs
  after the response completed: in the CURRENT assistant message (`message.id == body.id`), pair
  each `use_learned_function` call that returned `covered: false` with the `record_answer` call of
  the same (operation, input), by their call ids; per valid pair submit ONE proposal —
  `source_id=<deployment>:<chat id>:<user message id>:<input hash>`, output = the record's
  `output`, provenance = the final reply text, model, assistant message id, both call ids, chat id.
  A duplicate delivery → the conflict (S6) is logged, not raised. A record paired with a covered
  call, an unpaired record, or a malformed one → no proposal + a `notification`; a miss without a
  record → a `notification`. An interrupted response never reaches outlet → nothing retained. Never
  raises into Open WebUI: failures are logged and the body returned unchanged.
- Exact Open WebUI metadata keys (chat id, user message id) are read from 0.12.3 source during the
  unit and pinned by the smoke; anything not confirmed there is marked UNCONFIRMED in the README.
- README guarantee (O9): a covered call makes the TOOL RESULT deterministic; the chat model still
  writes the reply around it.
- Tests `tests/test_open_webui_example.py` (minimal `pydantic` stub): E1 covered → output, each
  uncovered reason → its `reason`; E2 `record_answer` writes nothing; the outlet writes one proposal per valid
  pair and the repeated delivery writes none; E3 a covered-call record, an unpaired record and a
  malformed one write nothing and notify; E4 outlet pairs by
  current message only (history messages ignored), flags a miss without a record, never raises.
- Smoke (kernel capture binding, recorded in the commit body): isolated venv `open-webui==0.12.3`
  + this repo; a deterministic OpenAI-compatible stub model; the researcher's R8 API recipe; cases
  hit, miss + record, off, duplicate delivery (`/api/chat/completed` after inline outlet),
  regeneration (new response, same user message → duplicate refused), two calls in one response.

## 8. Order

M3.6a3 → M3.6b (§1, §2 schema) → M3.7 → M5.1 (§3) → M4.1 (§4) → M4.2 (§5) → M5.2 (§2 behavior, §6)
→ M5.3 (§7) → M3.8 → prototype → M3.9a/b.

## 9. Gates (numbered; each unit's contract section in its commit restates the exact commands)

1. the unit's battery module(s): `uv run python -m unittest tests.test_<unit>_battery` —
   module names fixed when the unit opens and recorded here before code.
2. `.agent/gate` full, from the unit's committed squash (D28 included).
3. mutation credit: `uv run python .agent/mutate <pin id>` for every preservation pin the unit
   cites; scope + survivors in the commit body; each survivor ruled.
4. the unit's smoke where §3-§7 names one (L1, LP1, §7 smoke), output recorded.
