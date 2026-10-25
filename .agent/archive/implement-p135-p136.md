# IMPLEMENT p135 + p136 — closed Tasks rows + the routed request (moved from `.agent/spec.md` at the phase close)

Phase line: `IMPLEMENT — deployment trust (p135) + shadow sampling and drift telemetry (p136)`; request = the two routed rows, now closed in `.agent/archive/deferred-closed.md`. Review fixes 1b0d823 (`.agent/review.md` "Phase close review"); nucllei sampling deferred 8bf9dad (p142).

- [x] cd0d2cf p135-e5 — bundle signatures: `cement_runtime.signature` (SSHSIG + allowed-signers + RFC 8032 verify) + `function eval --signature --allowed-signers`; D7 refusal.
- [x] 723abe9 p135-e3 — schema v4 + `retention prune` + `partition erase` over the ledger.
- [x] 6af77ce p136-cmp — comparator IR + `set_comparator` (v4 table, amended in place) + `Read`/CLI views.
- [x] a1686ad p136-store — telemetry store + admit / `record_shadow` (captured version, comparator, disagreement → proposal) + `drift` + `observations` + CLI; prune + erase cover it.
- [x] cb6c82c p136-learn — `cement_runtime.learning` + `skills/cement-learn/`: shadow proposals, comparator authoring, drift reads.
- [x] 220fb55 p136-owui — Open WebUI: matched-hit extractor + bounded worker + shadow model call + valves + learning-tool reads; S5 probe; paste-ins regenerated; live regimen run.
- [x] eb5cc4d p135-docs — tier `docs`: E2 + E4 + threat model + README `Deployment boundary` per both plans.
  - Every unit: tier `kernel` unless named; contract `.agent/decisions/<unit>-contract.md` before code; red-first tests (parent + detached-worktree command in the commit body); its own `.agent/review.md` pass; human-facing docs for what it ships.
- [x] (this commit) Phase close — closing-diff reviewers (one per lens) + MAINTAIN's security lens; `.agent/review.md` no open row; CI gate; p135 + p136 closed by acceptance; `Phase: MAINTAIN`.
  - Also owed here: package 0.2.0 → 0.3.0 (the v4 cut) with `uv.lock`, the provider wheel's `cement-runtime` range + the two-wheel smoke, and v4's frozen schema digest — the lock change re-keys every D28 verdict, so it lands once, at the close.
