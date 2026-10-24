# Deferral queue

Off-path improvements, one entry + acceptance check each: a `p<nn>` row line plus the
indented lines directly under it. Nothing here reaches a session for free;
`.agent/spec.md` `Tasks` names the rows that block the current spine. `pri` 1 = highest.
p01-p61 came from the frozen `.agent/archive/polish.md`, which holds their full text,
evidence + grounds under the same `p<nn>` id; a row born here (p62 on) is absent from the
archive, so its own entry is its whole record and must carry every anchor a future
session needs.

Gate for every row unless the row says otherwise: the full gate `.agent/gate`
(`.claude/rules/ops.md`). A row needing a scope source, an assurance tier or the unit set
changed is spine work, not queue work.

Closing a row = its closing commit moves the entry verbatim into
`.agent/archive/deferred-closed.md`, `closed` (met by that commit) or `closed=<sha>` (met
at an earlier commit, an ancestor of HEAD) after `pri`, plus a `Closed:` line holding the
rerun acceptance evidence.

Grader: `uv run python .agent/decisions/m3-deferred-validate.py` (floor = archive ids | the ids
of every committed revision of this queue and of the closed ledger; each floor id open here or
closed there, never both and never neither; `unknown` cells, a missing `Accept:` or `Closed:`
and an unresolvable closure SHA red).

- `p52` `pri=4` — Only 6/55 `m3u5a-map.json` rows were re-derived; the other 49 are attention pointers whose filled cells/resolving anchors do not prove truth. Accept: Before any map row becomes a durable contract/doc/roadmap claim, re-derive it against HEAD and commit that evidence beside the claim.
  - Status (MAINTAIN queue runs 1 + 2): waiting on its trigger — the acceptance binds a map row only when it is about to become a durable contract, doc or roadmap claim; no unit of either run turns a `m3u5a-map.json` row into such a claim.
- `p135` `pri=4` — Build the deployment-trust milestone that p87 planned (`.agent/decisions/p87-milestone.md`: E1 attested actors with the attestation re-verified on serving, E2 encryption-at-rest obligations, E3 retention prune + partition erase on schema v4, E4 registry recipe, E5 SSHSIG + pure-Python Ed25519 bundle verification inside `function eval`). Several sessions of work with a schema cut and seven owner decisions (D1-D7) ⇒ an IMPLEMENT-sized milestone (`CLAUDE.md` `Session flow` Routing). Accept: D1-D7 ruled and recorded in `.agent/spec.md` `Decisions`; the plan's numbered gates 1-3 pass from committed state.
  - Status (MAINTAIN queue run 3 close): routed → IMPLEMENT (owner: "Route both to IMPLEMENT"); `.agent/spec.md` `Phase` quotes this row as the request, and the IMPLEMENT phase closes it by its acceptance.
- `p136` `pri=4` — Build the shadow-sampling + drift-telemetry milestone that p88 planned (`.agent/decisions/p88-milestone.md`: S1 an off-path sampler in the Open WebUI filter outlet with a bounded worker, S2 `record_shadow` into a separate telemetry store with the agreement derived from the captured version, S3 `drift` + `observations` + CLI + learning-tool reads, S4 passive, S5 the frozen-completion probe). Several sessions of work across the runtime, a new store and the Open WebUI example, with nine owner decisions (T1-T9) ⇒ an IMPLEMENT-sized milestone (`CLAUDE.md` `Session flow` Routing). Accept: T1-T9 ruled and recorded in `.agent/spec.md` `Decisions`; the plan's numbered gates 1-3 pass from committed state.
  - Status (MAINTAIN queue run 3 close): routed → IMPLEMENT (owner: "Route both to IMPLEMENT"); `.agent/spec.md` `Phase` quotes this row as the request, and the IMPLEMENT phase closes it by its acceptance.
- `p137` `pri=3` — The Open WebUI regimen's lock (`examples/open_webui/local-requirements.txt`) carries 127 distinct advisories (OSV via `.agent/owui-audit`: 125 at p131, 2 pillow advisories published since — CVE-2026-112398, CVE-2026-114501) in 15 packages that `open-webui==0.12.3` pins EXACTLY in its own metadata: accelerate 1.13.0, aiohttp 3.14.3, anthropic 0.86.0, black 26.5.1, brotli 1.2.0, brotlicffi 1.2.0.1, chromadb 1.5.9, cryptography 48.0.0, mcp 1.27.2, pillow 12.3.0, pyarrow 20.0.0, pyjwt 2.13.0, pypdf 6.7.5, sentence-transformers 5.5.1, transformers 5.5.4. 0.12.3 is both the latest release and the owner-ruled target that mirrors the production Kimi instance (`.agent/spec.md` `Decisions` Open WebUI deployment), so no in-repo change fixes them without diverging the regimen from production. Every finding is held on this row (`.agent/decisions/owui-audit-holds.json`). Re-open trigger: an Open WebUI release that moves these pins → the target bump (`pins.md`: `OPEN_WEBUI` + the lock's header command), then `.agent/owui-audit` without these holds. Accept: `.agent/owui-audit` rc 0 with no hold on this row.
