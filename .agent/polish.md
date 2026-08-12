# Polish register

Deferred-perfection items, off the milestone spine. `/session-polish` = sole consumer; protocol lives
there. Rows are born at deferral with the acceptance check already written.

Gate for every row unless it says otherwise: `uv run python -m unittest discover -s tests -t .` plus
`uv build`. Scope sources, assurance tiers and the unit set stay fixed — a row needing any of those
changed is spine work, not polish.

- `pri=1` `size=M` — port the mutant replay driver to committed state. `.scratch/main-replay/replay.py`
  produced u4b's recorded mutation verdicts and is gone with `.scratch/`, so a gate backing a durable
  roadmap claim cannot rerun from a clean checkout, and the next campaign rebuilds it from scratch.
  Regeneration spec is recorded in `.agent/memory.md`: N isolated clones of `src`/`tests`/`examples`,
  `PYTHONDONTWRITEBYTECODE=1` plus `__pycache__` purge, per-mutant proof that the interpreter loaded the
  mutated module from its clone, byte-exact restore, `--reanchor` over a `difflib` line map, `--control`
  pristine sweep at full worker count. Throughput reference: 61 mutants at 8 workers ≈ 13 min, 254 ≈ 50
  min. Acceptance: a committed dev tool runs a catalogue `.jsonl` from a clean checkout, its `--control`
  sweep is green, and a seeded known-live mutant reports as surviving while a seeded known-dead one
  reports as killed. u4b's own catalogue died with `.scratch/` and is not a recovery target.

- `pri=2` `size=S` — `Candidate.provenance` contract unenforced at its sole consumer, `system.py:784` in
  `System.handle`. `Candidate` is a frozen dataclass typing `provenance: Mapping[str, object]` with no
  runtime check, and `canonicalize(dict(candidate.provenance), max_bytes=65_536)` is the only site that
  reads it. Probed: `[]` becomes `{}` and is stored as empty provenance; `'text'` escapes as a raw
  `ValueError`; `5` and `None` escape as raw `TypeError`. The `type(provenance.value) is not dict` guard
  on the following line never fires for any of them, because `dict()` normalizes or raises first. Same
  defect class memory already records twice for persisted scalars, here on an input path. Acceptance: one
  probe per shape (`[]`, `'text'`, `5`, `None`) raises `ValidationError` out of `handle`, with `[]`
  failing rather than silently becoming `{}`.

- `pri=3` `size=S` — `.agent/decisions/` input pointers are dead. Seven records open with `Inputs:` lines
  citing `.scratch/agents/*.md`, plus `.scratch/main-verify/tree`, `.scratch/main-verify/f1probe.py` and
  `.scratch/m2u3b1.patch`; `.scratch/` no longer exists, so every one resolves to nothing while reading
  as a live reference. Acceptance: each record's inputs either carry the substance inline or are marked
  expired, and no tracked file cites a `.scratch/` path as though it were retrievable.

- `pri=4` `size=M` — 166 Pyright `reportAttributeAccessIssue` errors across `tests/test_system.py` lines
  221-1192, pre-existing at `d0b7e93`: unnarrowed union member access in baseline outcome assertions.
  Type noise only, no behavior at stake, and Pyright is not a configured gate. Acceptance: that region
  narrows its unions explicitly, an ad-hoc `uvx pyright tests/test_system.py` reports zero
  `reportAttributeAccessIssue`, and the suite stays green.
