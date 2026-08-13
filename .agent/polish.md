# Polish register

Deferred-perfection items, off the milestone spine. `/session-polish` = sole consumer; protocol lives
there. Rows are born at deferral with the acceptance check already written.

Gate for every row unless it says otherwise: `uv run python -m unittest discover -s tests -t .` plus
`uv build`. Scope sources, assurance tiers and the unit set stay fixed — a row needing any of those
changed is spine work, not polish.

- `pri=1` `size=M` — port the mutant replay driver to committed state. `.scratch/main-replay/replay.py`
  produced u4b's recorded mutation verdicts and is gitignored, so a gate backing a durable roadmap claim
  cannot rerun from a clean checkout. It survives on this workstation together with u4b's catalogue
  (`.scratch/agents/rev2b-m2u4b-mutants.jsonl`) and the wave's result sets
  (`.scratch/main-replay/final-*.jsonl`), so the port is a copy-and-harden while that holds — `.scratch/`
  is machine-local and unbacked, so treat the window as closing. Regeneration spec, should the sources go,
  is recorded in `.agent/memory.md`: N isolated clones of `src`/`tests`/`examples`,
  `PYTHONDONTWRITEBYTECODE=1` plus `__pycache__` purge, per-mutant proof that the interpreter loaded the
  mutated module from its clone, byte-exact restore, `--reanchor` over a `difflib` line map, `--control`
  pristine sweep at full worker count. Throughput reference: 61 mutants at 8 workers ≈ 13 min, 254 ≈ 50
  min. Acceptance: a committed dev tool runs a catalogue `.jsonl` from a clean checkout, its `--control`
  sweep is green, and a seeded known-live mutant reports as surviving while a seeded known-dead one
  reports as killed; where u4b's catalogue was recovered, replaying it reproduces 58 killed / 1 superseded
  / 2 surviving, those 2 being the reviewer's proved-equivalent pair.

- `pri=2` `size=M` — stored-scalar conversions in `system.py` are still unguarded in places, third recorded
  instance of one class. `_function_receipt_from_row` (`src/cement_runtime/system.py:277`) validates string
  fields inside a try translating `(IndexError, KeyError, TypeError, ValidationError)` that closes at
  `src/cement_runtime/system.py:309`, then converts six integer fields with bare `int(...)` at
  `src/cement_runtime/system.py:320-325`. A second unguarded site sits in `compile` itself —
  `revision = int(registered["revision"])` at `src/cement_runtime/system.py:1626` — probed to leak a raw
  `TypeError` on a NULL stored revision, while `verify_drafts`, `verify_function` and
  `inspect_function_promotion` all raise `IntegrityError` on the same corrupt row through exact-type
  guards, so the guarded pattern is already available and simply unapplied. Probed: `sequence`/`operation_revision`/`member_count`/
  `promoted_at_us` set to `NULL` or non-numeric text leak raw `TypeError`/`ValueError` instead of
  `IntegrityError`; separately, numeric text (`sequence='1'` and each sibling) is ACCEPTED where an exact
  stored int is required. Reachable from `latest_function_receipt`, `function_receipts`, `function_report`'s
  function anchor, `reconstruct_function_receipt`, and `verify_function` P6 — which catches `IntegrityError`
  only, so the leak escapes the check written to contain it. `main` has no catch-all, so the CLI surfaces
  this as a traceback rather than mapped JSON. Promotion planning adds two more reachable sites of the same
  class: the report and artifact-build conversions on the candidate and retained paths, both reachable from
  `inspect_function_promotion` and `promote_function`, so the corruption guarantee proved for the
  `artifact_json` recipe does not cover them and a corrupt row there leaks the raw conversion error. The
  standing rule in `.agent/memory.md` already requires every
  persisted-scalar conversion to translate `TypeError`/`ValueError`/`OverflowError` or to guard the exact
  stored type the way `_stored_int` does; u4a and u4b each paid for one violation, so fix the class, not the
  site. Acceptance: the audit in `.agent/decisions/m2u4c-surface.md` Section G lists every conversion site
  with its guard status; every site reachable from a public API either translates all three exception types
  to `IntegrityError` or rejects a non-`int` stored value outright; one committed probe per receipt integer
  field drives both `NULL` and numeric text and expects `IntegrityError`; suite green.

- `pri=3` `size=S` — port the report anchor validator to a committed dev tool. Every `map` brief makes its
  report's `path:line` claims machine-checkable through `.scratch/validate-anchors.py` (fenced ```anchors
  block, TAB-separated `path`/`line`/`exact fragment`, exit 0 only when every row resolves and no
  `TODO-FILL` cell remains), and u4c5's map passed 268 anchors under MAIN's rerun — but the validator is
  gitignored, so a brief naming it is unrunnable in any clone and the next wave silently loses the check.
  Acceptance: a tracked script under a dev-tools path takes `REPORT.md [--root DIR]`, reports
  `ANCHORS-CHECKED`/`ANCHORS-BAD`/`UNFILLED-CELLS` and exits nonzero on any bad anchor or unfilled cell,
  proven from a clean checkout by a committed fixture report carrying one resolving anchor, one stale
  anchor and one `TODO-FILL` cell; briefs cite the tracked path.

- `pri=2` `size=M` — port the seam mutation battery to a committed dev tool. u4c1's 9-mutant battery over
  `_Outcome`, `main`'s channel branch, the parser slot and limit forwarding killed 9/9, but it ran from
  `.scratch/mutants.sh` and died with the wave, so the claim outlives its driver (same defect as the u4b
  replay driver already tracked here). Acceptance: a tracked script takes a catalogue of
  `(file, anchor, old, new, test)` rows, asserts each patch changed the file, purges `__pycache__` with
  `PYTHONDONTWRITEBYTECODE=1`, runs the named test per mutant, restores byte-exactly (`cmp` proves it),
  and exits nonzero on any survivor; rerunning it from a clean checkout reproduces 9/9 without edits.

- `pri=2` `size=M` — bounded projections have no cursor, and two families page in opaque-id order.
  `function_report` clamps six detail lists with one `projection_limit`, but the only way to see a
  truncated remainder is to raise the limit toward 10,000; there is no offset, cursor or stable sort key
  exposed. Members project by `ordinal` and artifacts by `sequence DESC`, both canonical, while
  `pending_proposals` orders by `p.id` (`src/cement_runtime/system.py:2740`) and
  `stale_revision_anomalies` by artifact `id` (`src/cement_runtime/system.py:2846`) — random `prop_*`/
  `art_*` hex, so a truncated page of either is an arbitrary subset, stable per ledger but unrelated to
  insertion or content order. Probed: `pending-a` and `pending-b` swap places across runs at
  `--projection-limit 1`, which is what forced the CLI test to pin set membership plus per-ledger byte
  stability instead of insertion order. Affects every later `function` leaf that pages the same model.
  Acceptance: both queries order by a meaningful, documented key (creation time or input hash), one probe
  seeds three rows in each family and asserts the projected prefix at limits 1 and 2 is the canonical
  prefix of the limit-3 projection, and the report's docstring states the ordering guarantee per family.

- `pri=3` `size=S` — `stale_revision_anomalies` is unreachable through supported flows, so its projection
  path ships behaviorally untested except through out-of-band state. `operation revise`
  (`src/cement_runtime/system.py:509`) retires every artifact it strands, and no other command leaves a
  draft/verified/promoted artifact on a superseded revision; the CLI test reaches the family only by
  bumping `operations.revision` with a direct `UPDATE`. That is faithful to the family's purpose — it
  reports ledger corruption — but it means no test exercises the transition that would produce it in
  production. Acceptance: either a supported command can strand an artifact and a probe drives it, or the
  model documents the family as a corruption detector, and the CLI's own probe cites that documentation
  instead of asserting the state is otherwise reachable.

- `pri=3` `size=S` — `Candidate.provenance` contract unenforced at its sole consumer, `system.py:784` in
  `System.handle`. `Candidate` is a frozen dataclass typing `provenance: Mapping[str, object]` with no
  runtime check, and `canonicalize(dict(candidate.provenance), max_bytes=65_536)` is the only site that
  reads it. Probed: `[]` becomes `{}` and is stored as empty provenance; `'text'` escapes as a raw
  `ValueError`; `5` and `None` escape as raw `TypeError`. The `type(provenance.value) is not dict` guard
  on the following line never fires for any of them, because `dict()` normalizes or raises first. Same
  defect class memory already records twice for persisted scalars, here on an input path. Acceptance: one
  probe per shape (`[]`, `'text'`, `5`, `None`) raises `ValidationError` out of `handle`, with `[]`
  failing rather than silently becoming `{}`.

- `pri=4` `size=S` — `.agent/decisions/` input pointers read as live references but resolve nowhere except
  this workstation. Seven records open with `Inputs:` lines citing `.scratch/agents/*.md`, plus
  `.scratch/main-verify/tree`, `.scratch/main-verify/f1probe.py` and `.scratch/m2u3b1.patch`; `.scratch/`
  is gitignored, so all 14 resolve to nothing in any clone. Here 11 still resolve and 3 are gone outright
  (`m2u3b1.patch` and both `main-verify/` entries), so the substance behind most is still recoverable —
  rescue before the window closes. Acceptance: each record's inputs either carry the substance inline or
  are marked expired, and no tracked file cites a `.scratch/` path as though it were retrievable.

- `pri=5` `size=M` — 166 Pyright `reportAttributeAccessIssue` errors across `tests/test_system.py` lines
  221-1192, pre-existing at `d0b7e93`: unnarrowed union member access in baseline outcome assertions.
  Type noise only, no behavior at stake, and Pyright is not a configured gate. Acceptance: that region
  narrows its unions explicitly, an ad-hoc `uvx pyright tests/test_system.py` reports zero
  `reportAttributeAccessIssue`, and the suite stays green.

## M2.u4c4 deferrals

- pri=2 `size=S` — the locked-recheck race is pinned only by injection, though it is real behavior. A
  default-constructed `System` re-reads the locked prospective function inside `promote_function` and
  raises `StateError` when it moved between `inspect` and `promote`; the CLI maps that to exit 4 with
  `error: "conflict"`, and u4c4 drives it through `main`'s exit map with a patched `System.promote_function`
  rather than through a real ledger. Exit 4 is the one exit class where retry IS the intended recovery
  (`.agent/memory.md`), so the branch an operator's wrapper depends on is the one no end-to-end probe
  reaches. Acceptance: a committed probe drives two CLI invocations against one ledger with a supported
  command changing the prospective union between the hash read and the promote, observes exit 4 plus the
  `expected_function_hash does not match the locked prospective function` message with no patching, and
  asserts the ledger is unchanged by the rejected call.
- pri=3 `size=S` — `--actor` grammar is nearly unpinned on the promote leaf. The merged suite carries a
  single occurrence exercising the value's validation, so the accept/reject PAIR the memory rule requires
  at every bound is absent here: an empty actor, an over-long actor and one carrying illegal characters
  all ride on the library's `_name` behavior with no CLI-side pin, and `--actor` is what the promotion
  receipt attributes activation to. Acceptance: one probe per shape (empty, boundary-length accepted,
  boundary+1 rejected, illegal character) asserts the exit code and the mapped message, and the accepted
  boundary value is read back out of the promotion receipt.

## M2.u4c3 deferrals

- pri=2 `size=S` — port the agent-report anchor validator to a committed dev tool. u4c3 gated every
  Wave-1 and Wave-2 report on `.scratch/validate-anchors.py`, which parses fenced ```anchors blocks of
  TAB-separated `path<TAB>line<TAB>fragment` rows, resolves each against a `--root`, and exits nonzero on
  any bad anchor or leftover `TODO-FILL` sentinel. It caught a surface map whose own claims were 12/25
  wrong, which is exactly the failure a reported-but-unverified number hides. Gitignored, so no clone
  reruns it — third instance of this class alongside the replay driver and the seam battery. Acceptance:
  a tracked dev tool validates a report from a clean checkout, a seeded bad anchor exits nonzero with the
  offending line printed, a seeded `TODO-FILL` exits nonzero, and a clean report exits 0.
- pri=3 `size=S` — `verify_drafts` reruns are not idempotent on a failing draft. A failed row hits none
  of the status transitions at `src/cement_runtime/system.py:3582-3600`, so it stays `draft`, stays
  eligible, and every rerun commits a fresh report plus `artifact.verification_failed` event with a
  distinct report ID. Harmless today because the negative branch needs out-of-band corruption, but exit 6
  makes an automated retry-on-nonzero wrapper amplify it. Acceptance: either a failed row carries a
  status or reason that makes it ineligible until the operator clears it, or the model documents
  unbounded report growth per rerun and a probe pins the `+1 report / +1 event` invariant per invocation.

## M2.u4c2 deferrals

- pri=2 `function receipts` / historical `show`: merge the diff-blind teammate's 13 contract-derived
  tests. They passed 35/35 against the landed implementation but were never merged, and the worktree
  died with the wave. Acceptance: re-derive from `.agent/decisions/m2u4c2-contract.md` Decision 8/9 and
  keep only probes MAIN's 17 do not already reach — repeated-flag last-wins, Unicode decimal digits
  reaching `type=int`, cross-leaf flag isolation in both directions, and surplus-positional rejection
  are the named non-overlapping ones. Gate: suite green, no existing test weakened.
- pri=2 `--receipt-id` inherits a repo-wide message vocabulary leak: `_request_id` reports the label
  `request_id` for `proposal_id` (`system.py:1087,1128,1229`), `artifact_id` (`3704,4466,4829,4968`),
  `example_id` (`4761`), `report_id` (`5006`) and now the receipt id. Pre-existing, pinned as-is by
  u4c2 because fixing it means editing `system.py` (outside the CLI write set) or duplicating library
  validation in the CLI. Acceptance: one label parameter threaded through `_request_id`, every caller
  naming its own field, existing message pins updated in one pass.
