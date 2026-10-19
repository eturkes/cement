# M3.6a3 contract — delete the seven dead outcome types

Tier `kernel` (a removal: closes on a battery that fails when one obligation is undone or one
preserved invariant disappears — `.agent/spec.md` Decisions Assurance). Base = the gate-tooling
squash on `main` (`BASE` below, filled at open). Owner seed (c) of M3 (`Decisions` M3 seeds).

## 1. Deletion set (measured at BASE)

- `src/cement_runtime/models.py`: dataclasses `Resolved`, `ReviewRequired`, `InProgress`,
  `FallbackFailed`, `Rejected`, `ReconciliationRequired` + the `Outcome` alias = SEVEN definitions.
- `src/cement_runtime/__init__.py`: the six names in the `from .models import (...)` list and the
  six `__all__` entries (`Outcome` was never exported).
- `src/cement_runtime/system.py`: the one docstring sentence naming ``Resolved`` (the `resolve`
  return rule) reworded to name the plan, same rule.
- NOT deleted: `CandidateRequest` and its `request_id` (live on the `cement-source-v1` envelope;
  leaves with M3.6b's cut), `ReviewResult`, `ProposalView`, every other model.
- Static references at BASE (`grep -w` over `src/` + `tests/`): models.py 13, `__init__.py` 12,
  system.py 1; tests: lifecycle battery 23, proposal-binding battery 12, test_proposal_binding 6,
  test_system 5, test_resolve_battery 3, test_submission 1, test_migration_battery 1 (docstring),
  test_cli 1. Human-facing docs, examples, prototype: 0.

## 2. Obligations

- O1 absence by AST: no `ClassDef` or `Assign`/`AnnAssign` target named any of the seven in any
  tracked `src/**.py`; `cement_runtime` and `cement_runtime.models` expose none
  (`hasattr` False for all seven).
- O2 `__all__` at HEAD = `__all__` at BASE minus exactly the six exported names, order otherwise
  preserved (parsed lists compared; a seventh removal or an addition reds it).
- O3 residue: zero `tokenize` NAME tokens equal to any of the seven across tracked `src/**.py`;
  the reworded docstring states the same rule (pinned phrase: "applies a resolved plan only").
- O4 structural: `models.py`'s remaining top-level definitions = BASE's minus the seven, same
  order; each survivor's source span byte-identical to BASE (a rename that keeps a type alive
  under another name reds O1 + O4 together).
- O5 preserved ABI: `CandidateRequest`, `Candidate`, `ReviewResult`, `ProposalView` fields,
  annotation text and defaults equal BASE's (`dataclasses.fields` + annotation strings).
- O6 burden repairs (owner pin-repair approval): every frame the deletion reddens is either an
  intended inversion (it pinned the seven types' presence — now asserts their absence) or a
  closed-transition freeze re-scoped to git objects at its unit's close; each listed by id below
  after the burden run, none deleted or skipped.

## 3. Gates (numbered, rerun from the committed squash)

1. `uv run python -m unittest tests.test_outcome_removal_battery` (O1-O5).
2. `.agent/gate` full (format, lint, types, audit, secrets, skips, register, unittest with D28,
   build, spec-lint).
3. mutation credit for the O5 preservation pin: `uv run python .agent/mutate
   tests.test_outcome_removal_battery.OutcomeRemovalBattery.test_o5_preserved_models_keep_their_abi`
   — survivors named.

## 4. Burden (filled after the deletion run at BASE)

Measured on 629577d + the §1 src deletion alone (uncommitted tree; `git diff 629577d impl/m3u6a3
-- src | git apply`), `uv run python -m unittest discover -s tests -t .` → `Ran 635` (four modules
failed collection), failures=3, errors=18. Stage 2 = stage 1 + import-list repairs alone (the six
names dropped from each import) over the six reached modules → `Ran` all, failures=1, errors=7.
Failure SETS compared between stages, never counts.

| test id (module) | stage | disposition |
|---|---|---|
| `tests.test_proposal_binding_battery`, `tests.test_resolve_battery`, `tests.test_submission`, `tests.test_system` (collection) | 1 | import repair: the six names leave the import list; the modules collect + pass at stage 2 except the two B rows below |
| `test_cli.CLITests.test_function_inspect_emits_the_tail_beyond_one_hundred_entries` | 1 | import repair (local `from cement_runtime.models import Candidate`) |
| `test_proposal_binding.FrozenPublicShapeTests.test_handle_lifecycle_shapes_keep_their_request_identity` ×6 subtests | 1, 2 | inversion (D10's later unit = this one): asserts each type ABSENT; `CandidateRequest` keeps `request_id` |
| `test_lifecycle_removal_battery` `test_l12_six_package_exports_are_identical_model_bindings` ×6 + `test_l12_post_state_model_definition_export_import_vector` | 1 | re-scope: M3.6a2's closed transition read from git objects at its close SHA (pin-repair ruling) |
| `test_lifecycle_removal_battery` L23, L26, L31 | 1 | cascade (they load the uncollectable modules); green once the imports repair, no edit |
| `test_proposal_binding_battery.ProposalBindingBatteryTests.test_b10_y20_path_matrix_request_identity_is_2` + `test_b14_y12_export_census_alphabetical_all_position` | 2 | re-scope: M3.4's export census (`Outcome` members, `__all__` position) read from git objects at `77f44b0` |

None deleted, skipped or weakened.

## 5. Results at the squash

- Gate 1: the battery reds on the unfixed base — commit 621e614 (tag `archive/m3u6a3-red`) =
  BASE + the battery alone: `uv run python -m unittest tests.test_outcome_removal_battery` →
  `Ran 7`, failures=12 (O1 ×7 subtests + O1 AST, O2, O3 ×2, O4); O5 passes (preservation pin).
- Gate 3: `.agent/mutate <O5>` → 0 in-scope mutants (scope = src lines traced AFTER import; the
  models' dataclass definitions execute at import) ⇒ O5 UNCREDITED → p91. Closure controls
  instead (a closure instrument, never a credential): `.agent/decisions/m3u6a3-controls.py <root>
  controls` (reviewer-18) undoes each obligation in a read overlay — 14 reds, O5 on an annotation,
  a default and a `default_factory`; `… <root> red` = its 3 battery-gap probes, failures=3 at
  55588a8, OK after the fix.
