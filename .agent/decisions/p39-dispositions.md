# p39 — dispositions + falsifiers for M3.1's governing claims (map-b S3 KEEP rows + rewritten source contracts)

Rows = `.agent/decisions/m3-map-b-authority.md` S3-001/004/005 (README claims M3.1 kept) + S1-009/010/138
(source docstrings M3.1 rewrote). Anchors re-derived at the p39 commit's parent. Pins live in
`tests/test_authority_removal.py` `GoverningClaimTests`: presence (`test_the_governing_boundary_claims_survive`,
whitespace-normalized) + attribution (`test_no_surface_attributes_access_control_to_cement`: any sentence in
README, `docs/*.md`, `examples/*/README.md` or a `src` docstring whose subject is Cement / the runtime / the
library / System / the CLI / a callback or hook, with an access-control verb and no negation, fails).

| id | claim | anchor at HEAD | disposition | falsifier | pin |
|---|---|---|---|---|---|
| S3-001 | `Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior.` | gone: README paragraph 1 was rewritten to `Intent` in M3.9a (owner-ruled); the learning pass is now the only reviewer | DELETE (superseded by the M3.9a rewrite) | n/a — README paragraph 1 is graded against `Intent` by its own unit | none (superseded) |
| S3-004 | `This release is a local control plane, not a network service or an ACL system.` | README `## Deployment boundary`, line 1 | KEEP | the sentence leaves README, or Cement grows an internal principal-permission decision (attribution check) | presence + attribution |
| S3-005 | `CLI actor names are recorded assertions, not authentication.` | README `## Deployment boundary` | KEEP | an actor/reviewer flag is authenticated internally or no longer recorded | presence + attribution |
| S1-009 | `A caller applies a resolved plan only after its own live authorization/policy gate.` | `System` class docstring | REWRITE (done in M3.1) → KEEP | the docstring credits Cement or a callback with the gate | presence + attribution |
| S1-010 | `Cement makes no principal or permission decision.` (+ `Actor and reviewer arguments are recorded assertions only.`) | `System` class docstring; README `## Deployment boundary` | REWRITE (done in M3.1) → KEEP | either sentence leaves its surface | presence + attribution |
| S1-138 | `Promote the locked prospective union in one immediate transaction.` | `System.promote_function` docstring | REWRITE (done in M3.1) → KEEP | the docstring changes or re-introduces authorization terminology | exact docstring + attribution |
