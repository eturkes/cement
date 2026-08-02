# M2.u3b1 — MAIN arbitration of review findings

Sources: `.scratch/agents/rev-m2u3b1.md` (correctness/spec/CLAUDE.md lens, 7 findings) and
`.scratch/agents/rev2-m2u3b1.md` + `-mutants.jsonl` (independent mutation lens, 146 mutants: 93 killed,
40 coverage-gap survivors, 13 equivalent with proofs).

Council rule applied: a finding confirmed by both reviewers is accepted outright; a unique finding is
accepted only after MAIN reproduced it or verified it by direct code inspection.

MAIN's own replays, all reproduced against `.scratch/main-verify/tree` (worktree at `9e09f4c` +
`.scratch/m2u3b1.patch`):

| Mutation | Suite | Verdict |
|---|---|---|
| `LIMIT 1000` on the retained/promoted enumeration | 208 OK | survivor confirmed |
| `LIMIT 1000` on the candidate/verified enumeration | 208 OK | survivor confirmed |
| retired event projection replaced with `()` | 208 OK | survivor confirmed |
| verified-row `ORDER BY` removed | 208 OK | survivor confirmed |

MAIN's own probe of the empty-union authority bypass (`.scratch/main-verify/f1probe.py`), deny-all
callback after registration:

```text
EMPTY_UNION_ENTRIES = 0
DENY_ALL_PROMOTE = SUCCEEDED, receipt = fpr_d86cb0e91eb54d89a49d2ca7b5fee5d8
AUTHORITY_CALLS_DURING_PROMOTE = []
RECEIPTS = 1
FUNCTION_EVENTS = 1
```

## A. Production defects — fix the code (2)

**A1. Empty-union promotion bypasses the authority callback.** `promote_function` authorizes by looping
over prospective members, so an empty union performs zero authority calls yet allocates a receipt ID,
reads the clock, opens the write transaction, writes an immutable `function_receipts` row, and emits
`function.promoted`. MAIN reproduced it above; `README.md:178-179` claims the callback gates promotion.

**MAIN's decision: reject the empty union.** Raise `StateError` before any clock read, ID allocation, or
write when the prospective union has no entries. Rejected alternative: adding an operation-level authority
subject — it invents a new subject on a callback M3 is already approved to remove, and nothing needs an
empty receipt, since u3b2 keeps "empty set with no receipt → vacuous pass". A zero-candidate checkpoint
over a **nonempty retained** set stays legal and keeps authorizing every retained member; only the
entirely empty union is refused.

**A2. Plan identity omits the predecessor/retirement set.** The authorized-vs-locked comparison binds
operation revision, candidate IDs, and member IDs only. The manifest displays `replaces_artifact_id`, and
the roadmap claims the locked transaction "rechecks plan identity against what was authorized". rev
probed a real race: suspending a displayed predecessor inside the authority callback leaves revision,
candidate IDs, member IDs, and the function hash all unchanged, so promotion succeeds while retiring only
two of the three authorized predecessors.

**MAIN's decision: widen the identity tuple**, rather than narrowing the durable claim. Include the sorted
non-null `replaces_artifact_id` set in the authorized-vs-locked equality, so the retirement plan the
operator inspected is the retirement plan that commits.

## B. Coverage gaps — add committed pins (production code already correct)

Both reviewers independently confirmed B1 and B2; MAIN reproduced both.

**B1. Event transition sets not independently bound** (rev F4 + rev2 F9). Every event fixture has
`member IDs == candidate IDs` and an empty retired set, so cross-wiring or omission is undetectable.
Pin: one mixed growth+replacement fixture where member, candidate, and retired sets are all distinct;
assert each count, each first-100 lexical preview, and each independent full-set `cement-id-list-v1`
digest.

**B2. Candidate/skipped ordering unpinned** (rev F6 + rev2 F11). `skipped` enters `manifest.text` in SQL
order, and the fixtures' insertion order coincides with the requested order. Pin: ≥3 superseded rows
inserted in reverse `input_hash` order, independent `System` instances, and
`PRAGMA reverse_unordered_selects = ON`; assert the exact skipped tuple and byte-identical `manifest.text`.

Accepted from rev alone (MAIN reproduced):

**B3. Quantification is not pinned to the 50,000-entry contract** (rev F3). `LIMIT 1000` on either
enumeration leaves all 208 tests green. Pin: independent 1,001-row tail-sentinel tests for the retained
and candidate enumerations, exercising the real SQL, union, manifest count/hash, and final membership.
Direct valid fixture insertion plus patched expensive replay is acceptable; the enumeration itself must
be real.

**B4. Retire-all-before-activate-any is not pinned** (rev F5). A pairwise "retire this predecessor, then
activate its candidate" mutant stays green. Pin: a temporary trigger or instrumented connection that
rejects any `verified → promoted` update while any planned predecessor is still `promoted`, with ≥2
replacements.

Accepted from rev2 alone — each carries verbatim CURRENT-vs-WEAKENED probe output in its report; MAIN
verified A1/A2 and B1-B4 directly and accepts the following on that recorded evidence:

**B5. Retained and candidate enumerations are not pinned to partition/operation/revision** (rev2 F1, F4;
HIGH). Dropping a predicate imports foreign promoted/verified rows into the union — a foreign artifact can
become a member and be retired by ID. Pin: three target rows plus a decoy in each omitted dimension;
assert exact manifest/member/authority/receipt sets and that foreign rows stay byte-identical.

**B6. The expected-function-hash gate is not independently pinned** (rev2 F2; HIGH). Both a
preflight-value substitution and a 32-hex-prefix comparison survive all 208 tests, so the unit's central
operator-repeat control is unprotected. Pin: one same-ID locked-content-drift seam and one same-prefix
wrong-suffix digest; each must raise before any write and preserve the full `iterdump()`.

**B7. Retained-member authorization is not pinned** (rev2 F3; HIGH). Authorizing candidates only still
passes. Pin: ≥3 retained members, deny the **last**, assert the complete deterministic authority subject
sequence and full-dump equality.

**B8. Bound-report ownership is not pinned** (rev2 F5; HIGH). Dropping `artifact_id` from the bound-report
lookup lets one artifact borrow a sibling's coherent passing report. Pin: bind the **middle** of three
candidates to a passing report owned by a sibling artifact; require failure with no write.

**B9. The surviving semantic scope-digest comparison is unpinned** (rev2 F6; HIGH). The implementer's
deletion of the *outer* `artifact.scope_digest` comparison was safe — rev audited it and MAIN accepts the
deletion — but the *surviving* comparison inside `_artifact_from_row` is load-bearing and killed by no
test: with `artifact_json`, `artifact_hash`, report, and promotion seals all made coherent while
`scope_hash` stays divergent, current code rejects and the mutant accepts. Pin: corrupt the **middle** of
≥3 entries, recompute every enclosing hash, and leave this comparison as the sole rejecter. rev2's
`X02-inner-artifact-digest-removed` is genuinely equivalent (the preceding parsed-document digest check
already proves it) — do not add a pin for it.

**B10. Schema-v2 structural constraints are broadly under-pinned** (rev2 F7). Fifteen mutants across FK
presence/actions, membership uniqueness and ordinal keys, receipt scalar CHECKs, receipt-hash uniqueness,
and `STRICT` typing all stay green. Pin: exact `PRAGMA table_info` / `foreign_key_list` / index-and-key
assertions plus one behavioral insert-or-delete per constraint. For FK-action isolation, lift only the
unrelated immutability triggers inside the fixture so the membership FK is the sole defense.

**B11. Multi-digit integer encoding in the receipt ABIs is unpinned** (rev2 F8). Every fixture keeps
revision, counts, and ordinals below 10, where decimal and hexadecimal coincide, so five hex-encoding
mutants survive. Pin: a literal ABI label plus an independent unsigned-64-bit big-endian framing oracle,
with ordinal, revision, member count, candidate count, and retired count **each independently ≥10**.

**B12. Manifest byte/item acceptance boundaries are unpinned** (rev2 F10). The manifest wraps the function
and adds descriptors plus skipped diagnostics, so both cap directions are non-equivalent. Pin: boundary
constructions immediately below and above the 2x byte and item caps, including many skipped rows;
inspection must reject deterministically with no writes. rev2's depth-cap mutants are equivalent — no pin.

**B13. Active-only canonical input enumeration is unpinned** (rev2 F12). Admitting revoked examples turns
a fail-closed corruption path into a blocked/skipped one. Pin: revoke all evidence for the **middle** of
three verified rows, restore only its status through the corruption fixture, and require the
missing-canonical rejection.

## C. MAIN owns these (not for the fixer)

**C1. Durable provenance points at an ignored path** (rev F7). `.agent/roadmap.md` names
`.scratch/m2u3b-design-record.md`, but `.scratch/` is gitignored, so the binding receipt/membership ABI
and the u3b1/u3b2 interface would not survive a clone. The same defect exists on u3a's line. MAIN moves
both design records into a tracked `.agent/` path and repoints the roadmap.

**C2. Import ordering nit.** `src/cement_runtime/__init__.py` lists `FunctionSetPromotion` before
`FunctionCheck` in the `from .models import (...)` block, breaking that block's alphabetical order
(`__all__` itself is correct). Folded into the fixer's brief as a one-line tidy.

## D. Rejected / no action

- **Stale-revision verified rows are silently excluded** (MAIN's own question). rev ruled it a non-finding
  and MAIN accepts: Decision 4 scopes the "never silently omit" rule to active `promoted` rows, a stale
  `verified` row is inert and cannot enter promotion, and `revise_operation` already retires prior-revision
  rows. Broader corruption diagnostics would be new scope, not a missing stated guarantee.
- **Deletion of the outer `artifact.scope_digest` comparison.** Audited by rev and confirmed correct by
  rev2's own equivalence analysis. The surviving inner comparison needs a pin (B9), not restoration.
- **rev2's 13 equivalent survivors.** Each carries a proof in the report and sidecar; MAIN accepts them as
  equivalent and requires no pin.
