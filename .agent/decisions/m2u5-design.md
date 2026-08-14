# M2.u5 — split + offline-resolution fork

Arbitrated from two anchored maps (docs claim inventory 144 rows / 281 anchors; function-layer surface
map 279 anchors) plus two prototyped design spikes that each built the whole alternative to a green gate
in its own worktree and BOTH self-rejected on disjoint measured evidence.

Claim inventory + guarantee ledger → `.agent/decisions/m2u5-claims.md`. Spike worktrees and `wt/`
branches were removed at close, so every fact either side supplies is carried here or there.

## Decision 1 — u5 splits into u5a (example) then u5b (docs)

The roadmap scoped u5 with a standing instruction to recheck size against `main=` and split if it does
not fit. It does not fit, measured after arbitration when the surface is known:

- Docs half: 32 claim rows needing an edit (4 FALSE, 3 STALE, 20 INCOMPLETE, 5 UNPINNED), 33
  undocumented capabilities, 4 internal contradictions, spread over `README.md` (186 lines),
  `docs/architecture.md` (101), `docs/threat-model.md` (69), `examples/hospital_ocr/README.md` (228).
  Every replacement sentence is MAIN-authored normative prose carrying an evidence anchor.
- Example half: the winning shape measures +64 production and +97 test lines against a corpus that must
  be re-driven, with a design fork that consumed a full wave to settle.

Wave 1 alone cost MAIN 78% of one window before any contract line existed — the recorded pattern for a
unit whose fork needs spikes. The two halves share no judgment surface and carry different tiers, so the
cut is clean.

- **u5a** `tier=data` — the example resolves from an exported bundle with no ledger, adapter or LLM.
  Owns `examples/hospital_ocr/run_demo.py`, `tests/test_hospital_ocr_example.py`, and the
  `examples/hospital_ocr/README.md` delta its own code forces (transcript + the new phase).
- **u5b** `tier=docs` — the claim pass over `README.md`, `docs/architecture.md`, `docs/threat-model.md`
  and every remaining `examples/hospital_ocr/README.md` claim row. Owns every other M2 documentation
  edit. Depends on u5a, so the pass documents the finished system rather than a moving one.

## Decision 2 — inline LOCATION, library CHANNEL, with one CLI round-trip proved in the test

Both spikes self-rejected. Rule from the asymmetry, per the standing discriminator: prefer the
alternative whose defect is CONDITIONAL on a regime the loser cannot improve.

`standalone` (separate `resolve_offline.py`, shipped CLI as subprocesses, `run_demo.py` and the
transcript byte-identical) carries five UNCONDITIONAL defects, and its first is structural and
unfixable inside its own constraint: `run_demo.py` deletes its temporary ledger and never creates a
function receipt, so `function export` cannot run against what the walkthrough just built. The separate
script therefore teaches an unprinted setup path — the committed test must reconstruct the lifecycle and
insert a hidden set checkpoint. Its own author named this the deciding defect. The byte-frozen README
compounds it: the new 145-line entry point is undiscoverable and the transcript prints no hash, so
nothing binds the offline answer back to the walkthrough that produced it.

`inline` (final phase of `run_demo.py`, library `parse_function` + `evaluate`, transcript regenerated)
carries two UNCONDITIONAL defects. Location coupling is a size and readability cost — `main` grows
210→261 lines, the transcript 50→60 — not a teaching-integrity failure. Bundle instability is shared by
both alternatives and by any regeneration, so it discriminates nothing.

Inline's dominant CONDITIONAL defect is that the library channel exercises no shipped CLI behavior. That
is exactly what standalone's CHANNEL supplies, and both spikes independently identified the same
cross-composition — inline LOCATION plus CLI CHANNEL — as the shape that removes the disconnected-entry-point
defect while keeping shipped-command proof. Its measured cost is per-document process startup: seven
`function eval` invocations cost 2,136.001 ms against a demo that currently runs in 0.30 s.

Ruling takes the composition without that cost. The demo teaches through the library, staying fast and
readable; `tests/test_hospital_ocr_example.py` additionally proves the shipped operator route ONCE with a
single `function export --out` plus `function eval --bundle` subprocess pair over the example's own
bundle. Shipped-command proof is a property the suite must hold, not a property every demo line must pay
for. Rejected explicitly: shipping both entry points, which inline measured as additive rather than
synthesizing (+186 inline lines on top of every standalone line) and which leaves a reader two offline
entry points and two channels with no canonical path.

## Decision 3 — the exported bundle is NOT reproducible across clean runs

Measured independently by both spikes and load-bearing for every downstream choice.

Two clean demo runs export bundles of the same 3,341 bytes with different SHA-256 values
(`bc4bb14a…` vs `98461575…`; `38f25144…` vs `9c778a53…`). No random identifier appears verbatim in
either bundle: the demo's per-run `art_<32hex>` never reaches the text. The instability is indirect —
run-specific evidence IDs feed `evidence_snapshot_hash`, verification example IDs feed
`report.test_set_hash`, and both feed `entry_seal`, which moves the root `function_hash`.

Consequences, all binding on u5a:

- No committed bundle fixture may be byte-compared against a fresh export. A committed bundle is a
  captured sample, never a reproducible generated artifact.
- The demo transcript now carries a SECOND per-run dynamic value. The existing mask
  `art_[0-9a-f]{32}` is insufficient; the function hash needs its own mask.
- The test proves the loop self-consistently: export in-process, then evaluate the bytes just written.
  Cross-run byte equality is not a property the system has.
- This is honest behavior, not a defect. Function identity is verified-content identity, and the content
  legitimately includes per-run evidence provenance.

## Decision 4 — implementation spec for u5a

The corpus, drawn independently by both spikes and agreeing exactly:

- Exported entries = 2. Layout A `physician_progress_note`, layout B `patient_intake_form`. Layout C
  `lab_result_slip` is reviewed but never promoted, so it is absent — the miss case is free and real.
- Layout C through the library returns `FunctionMatch(matched=False, output=None, artifact_hash=None)`;
  through the CLI it is exit 6 with the four-key payload `{artifact_hash: null, function_hash: <hex>,
  matched: false, output: null}` on stdout and empty stderr.
- `pipeline.apply_plan` consumes the resolved plan with no ledger and produces the real extraction JSON,
  closing the loop: `{"assessment": …, "encounter_date": "2026-02-21", "mrn": "MG-100913",
  "patient_name": "Sofia Patel", "provider": "Dr. Amina Shah"}` for A03.
- Bundle size 3,341 bytes for this corpus.

Required shape:

- A `resolve_offline(bundle_text, ocr_text)` helper returning the function hash beside the match, so the
  demo can assert the parsed bundle's hash equals the hash it printed before the ledger went away. That
  assertion is the only thing linking an offline answer to the verified set; without it the phase proves
  ledger-freedom but not provenance.
- The demo prints the verified/exported function hash BEFORE offline use, then resolves with the ledger
  unreachable.
- Ledger-freedom proof standard, unchanged from the committed precedent
  (`tests/test_cli.py:4693 test_function_eval_opens_no_store_or_connection`): patch `System.__init__`
  AND `sqlite3.connect` to raise, then resolve successfully anyway. Import-freedom is never the claim —
  the package `__init__` imports `.system` → `.store` → `sqlite3` regardless. For the subprocess leg the
  same hook installs through `sitecustomize`, which is strong for an ordinary launch and does not cover
  `python -S`; state that limit rather than overclaiming it.
- Reference test names, validated green in the inline spike's worktree:
  `test_resolution_constructs_no_system_and_closes_the_extraction_loop`,
  `test_resolution_returns_the_library_miss_for_unexported_layout_c`,
  `test_demo_output_matches_the_pinned_readme_transcript`.

The third one is a real gain beyond the deliverable: the example README transcript is currently pinned
by NO test (claim rows E027-E030 are UNPINNED, and the standing memory rule is to rerun the demo and
re-diff by hand whenever either side moves). Pinning it inside u5a retires that manual obligation, and
u5b inherits a transcript a gate defends. Both dynamic values must be masked for it to hold.

## Decision 5 — u5b folds in the tracked exit-6 documentation row

`.agent/polish.md` carries an M2.u4c5a deferral whose remaining acceptance is that `README.md`/`docs/`
state the exit-6 contract once. u5b writes that sentence as part of its own claim pass — README's
paging/exit paragraph is already INCOMPLETE for omitting the class (row A036), and the alternative is a
second pass over the same paragraph by a different consumer. Folding it in is not scope creep: the
sentence has to be written either way, and u5 owns every M2 documentation edit. Close the polish row at
u5b's close rather than leaving `/session-polish` to re-derive it.

## Measurements retained

| Alternative | production | test | suite | demo wall | verdict |
|---|---:|---:|---:|---:|---|
| `inline` (library, demo phase) | +64 `run_demo.py`, +14 example README | +97 | 535 → 538 | 0.17 s | SELF-REJECT |
| `standalone` (CLI, separate script) | +145 `resolve_offline.py` | +196 | 535 → 536 | 1.976 s | SELF-REJECT |

CLI leg costs, measured warm on this host through `[sys.executable, "-m", "cement_runtime"]`: export
331.379 ms; seven evals 2,136.001 ms total (264.808–355.727 ms each). One export plus one eval in the
suite is therefore ≈0.6 s, which is the price Decision 2 accepts.
