# p136-cmp contract — the per-operation comparator (revision 2)

Plan: `.agent/decisions/p88-milestone.md` (amended by the owner's T rulings, `.agent/spec.md`
`Decisions` Shadow sampling): T1 = agreement decided by a per-operation comparator the learning pass
writes; rules `ignore` a field, normalized `text` (trim, collapse whitespace, case-fold), `unordered`
list, numeric `tolerance`; every field no rule names compares exactly; none set = canonical JSON
equality; Cement checks grammar + consistency against the active examples and refuses a comparator
that ignores a whole output; `Read` shows it. Tier `kernel`: a comparator decides which LLM answers
become proposals (T3), and nothing downstream re-checks that verdict. Revision 1 → 2 = consultant-1's verdicts L1-L6 (`.scratch/p136/consultant-1/verdicts.md`, probes
at `723abe9`): an ABI-pinned text rule, a typed array edge, descent through `*` below `unordered`, typed
witnesses, a 64 KiB budget, capped paths, the comparator captured at admission (p136-store).

## Premises (measured at `723abe9`)

- C1 `cement-projection-v1` is the precedent: a constrained JSON IR Cement interprets itself, stored
  append-only per (partition, operation, operation revision) in `projection_settings` + a program
  table, set by the learning pass, verified against the revision's active examples, shown by
  `function read`.
- C2 Outputs are `cement-json-v1` values: null, booleans, strings, signed 64-bit integers, arrays,
  string-keyed objects; decimal quantities travel as application strings (README `## Outcomes`).
- C3 Schema v4 is unreleased until the phase close, so this unit amends it in place (fingerprint
  moves, `SCHEMA_VERSION` stays 4); a partition-bearing table joins `partition erase`.
- C4 `_text(value, label, maximum=256)` = the actor convention; `_name` = partition/operation names.

## Obligations

- M1 Grammar (`cement_runtime.comparator.parse_comparator(value) -> Comparator`, public): an object
  with exactly `abi` = `"cement-comparator-v1"` and `rules` = a list of at most 256 rule objects. A
  rule = `{"path": [...], "rule": "ignore" | "text" | "unordered"}` or `{"path": [...], "rule":
  "tolerance", "within": "<decimal>"}`, no other key. A path = a list of at most 32 segments, each a
  non-empty string of at most 256 characters; the segment `"*"` = every element of an array (a typed
  edge: an object member literally named `*` stays an ordinary key and no rule can name it), any other
  segment = one object key. The canonical document ≤ 65,536 bytes. `within` = `^(0|[1-9][0-9]*)(\.[0-9]+)?$`, at most 32 characters. Refused
  (`ValidationError`, the rule's index named): a repeated path; `ignore` at the root (`[]`); any rule
  under an `ignore`, `text` or `tolerance` path (a dead or ill-typed rule); a `tolerance` under an
  `unordered` path (no matching is defined there); a rule under an `unordered` path whose next segment
  is not `*` (it could never apply). `Comparator.comparator_hash` = SHA-256 over the
  canonical JSON of the comparator with its rules sorted by path; equal content → equal hash.
- M2 Comparison (`cement_runtime.comparator.compare(comparator: Comparator | None, expected, actual)
  -> Comparison(agreed: bool, paths: tuple[str, ...])`, total over two `cement-json-v1` values):
  `None` = canonical JSON equality. Otherwise, walking both values from the root with the rule at
  each path: `ignore` → agree, whatever either side holds (presence included); `text` → two strings
  agree when, after each run of U+0009-U+000D, U+0020, U+00A0, U+3000 becomes one space, the ends are
  trimmed and A-Z become a-z (explicit tables, never the host's Unicode data: `casefold` agrees on
  U+A7CB/U+0264 under 3.15 and not 3.12, measured), they are equal; anything else compares exactly; `unordered` →
  two arrays agree when their normalized elements (the rules below `*` applied, then canonical JSON)
  are equal as multisets, anything else compares exactly; `tolerance` → two values agree when both are
  integers or decimal strings (the `within` grammar with an optional leading `-`, at most 64 characters) and `|a − b| ≤
  within` (scaled integers; no rounding context), anything else compares exactly. No rule: two objects agree when
  their key sets are equal after removing keys whose path is ignored and every remaining value agrees;
  two arrays agree when their lengths are equal and the elements agree pairwise under `*`; anything
  else compares by canonical JSON. `paths` = the first 20 disagreeing paths in walk order (`$`,
  `$.key`, `$["a b"]`, `$[3]`; object keys sorted, a missing member at its own path, a type or length or
  multiset mismatch at its container), each capped at 256 characters, empty when `agreed`; `None`
  walks exactly like an empty rule list. Domain: two accepted `cement-json-v1` values (≤ 1 MiB each).
- M3 Storage (schema v4, in place): `comparator_settings(sequence, id UNIQUE, partition, operation,
  operation_revision, comparator_json, comparator_hash, set_by, set_at_us)` STRICT, FK operations,
  `comparator_settings_no_update` + `comparator_settings_no_delete` (the erase grant clause); `partition
  erase` deletes the partition's rows (count key `comparator_settings`).
- M4 `System.set_comparator(partition, operation, comparator, *, actor) -> ComparatorRecord`: grammar
  (M1); the operation registered; an equal hash to the current setting returns it before any revalidation (no clock, id or
  write); then, at set time only, applicability over the current revision's active examples (revoked +
  superseded excluded): every rule has a witness of its kind (`text` a string, `unordered` an array,
  `tolerance` an integer or decimal string, `ignore` anything; `ValidationError` naming the path), and
  no example output with at least one leaf (a scalar or an empty container) has every leaf ignored
  (`ValidationError` naming the example). These checks prove applicability, never that the kept values
  suffice: a huge tolerance or an ignored dose passes, and the docs say so; then one setting
  row + one `comparator.set` event (payload `actor`, `comparator_hash`, `previous_comparator_hash`,
  `operation_revision`). `System.
  comparator(partition, operation, *, operation_revision=None) -> ComparatorRecord | None` = the newest
  setting of that revision (default: current). `ComparatorRecord(comparator, comparator_hash,
  operation_revision, set_by, set_at_us, sequence)`; the stored JSON is re-parsed and re-hashed on read
  (`IntegrityError` on a mismatch). The comparator is revision-scoped mutable policy, not function
  content: p136-store captures JSON + hash + sequence (or `None`) at admission.
- M5 CLI: `cement comparator set OPERATION --comparator JSON|- --actor NAME`, `cement comparator show
  OPERATION`; `function read` lists the comparator of the version's revision in its header, labelled the
  revision's current policy with its hash + setting sequence (a later setting replaces it), one line per
  rule, or that the revision has none; the no-match tail stays last. Help in the
  ASD-STE100 register.
- M6 Docs: README `### Comparing answers` (the rule kinds, exact by default, who writes it, what Cement
  checks, what it does not judge); `docs/architecture.md` (table + IR); threat model: a comparator is
  the learning pass's judgment, like a projection program (`## Untrusted` bullet 3).

## Gates (numbered; rerun from committed state)

1. New tests red at `723abe9`: grammar acceptance + each refusal by index (repeated path, root ignore,
   rule under ignore / text / tolerance, tolerance under unordered, 256 / 257 rules, 32 / 33 segments,
   256 / 257-character segment, `within` forms); hash invariant under rule order; compare: each rule
   kind agrees and disagrees on an adjacent pair (`within` exactly vs one unit above; whitespace +
   case vs one changed letter; reordered vs one changed element; an ignored key present on one side),
   nested `*` under `unordered`, an unnamed field still exact, `None` = canonical equality, non-string
   under `text` exact, `paths` order + the 20 cap; set: unwitnessed rule + wholly ignored output
   refused with zero writes, equal hash idempotent, revision scoping, erase deletes the rows; CLI
   exits; `function read` lines.
2. Full gate = CI gate (`.agent/ci-gate p136-cmp`).
3. Register + article audits rc 0; repaired pins named (table count 17 → 18, censuses, SHAPE).

```claims
9	Revision 1 → 2	unchecked	revision numbers of this contract, not counts	-
22	`SCHEMA_VERSION` stays 4	unchecked	the schema version constant, not a count	-
28	a list of at most 256 rule objects	unchecked	the grammar bound `MAX_RULES`, pinned by an adjacent-pair test	-
31	non-empty string of at most 256 characters	unchecked	the grammar bound `MAX_SEGMENT`, pinned by an adjacent-pair test	-
33	≤ 65,536 bytes	unchecked	the grammar bound `MAX_BYTES`, pinned by an adjacent-pair test	-
45	U+A7CB/U+0264 under 3.15 and not 3.12	unchecked	consultant-1's measured Unicode probe (scratch), code points not counts	-
48	at most 64 characters) and	unchecked	the operand bound `MAX_DECIMAL`, a constant	-
52	the first 20 disagreeing paths	unchecked	the cap `MAX_PATHS`, pinned by a test	-
54	each capped at 256 characters	unchecked	the cap `MAX_PATH_TEXT`, pinned by a test	-
55	(≤ 1 MiB each)	unchecked	the value bound of cement-json-v1 answers, a constant	-
82	(`## Untrusted` bullet 3)	unchecked	a position in the threat model, not a count	-
88	256 / 257-character segment	unchecked	adjacent bound pairs the gate pins	-
92	the 20 cap	unchecked	the cap `MAX_PATHS`	-
```

Erratum (closing review, reviewer-1 R4): `set_comparator` returns a `ComparatorChange`
(`changed`, `comparator_hash`, `operation_revision`), not the `ComparatorRecord` that `comparator` reads.
