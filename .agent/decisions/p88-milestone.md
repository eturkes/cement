# p88 milestone contract — shadow sampling + drift telemetry (planned, unbuilt)

Row (verbatim acceptance, `.agent/deferred.md` → `.agent/archive/deferred-closed.md`): planned as a
milestone; its probe sends N matched requests to the LLM as well, records agreement without changing
the answer the caller receives, and reports a per-operation disagreement count.
Status: plan only. Building it = row p136 (an IMPLEMENT-sized milestone, routed by the owner).
Tier when built: `kernel` for the sampler's selection, observation identity and response isolation
and for Cement's agreement verdict + counts (no downstream re-check); `data` only for value payloads
Cement re-validates. Owner decisions T1-T9 bind the build; each names the default this plan
recommends.

## Premises (measured at `93ff847`; Open WebUI 0.12.3 from its installed wheel)

- Q1 Cement calls no LLM on the serving path: `resolve` + `serving` read the ledger; `propose` calls
  a configured `CandidateSource` only when asked. The integration owns every model call.
- Q2 Open WebUI runs a filter `outlet` after the model's generation but not after delivery: the
  non-streaming handler awaits it before it returns the response (`open_webui/utils/middleware.py`
  `await outlet_filter_handler(ctx)` ahead of `return response`), the streaming path awaits an
  outlet task around stream completion, and `/api/chat/completed` can run the outlet again. A hit =
  the chat model's `cement` tool call answered from the switched-on version; `cement_filter.py`
  `_tool_calls` exposes the current message's calls + results, while `_pairs` returns miss/record
  pairs only, so sampling needs its own matched-hit extractor. nucllei (an Open WebUI 0.6.5 fork)
  has no `outlet`; its `use` runs inside the user's turn (`.claude/rules/nucllei.md`).
- Q3 `docs/threat-model.md` `## Deliberately absent` lists `Active shadow sampling.`;
  `## Deployment obligations` asks the deployer to `Monitor promoted scopes` with no surface to do it.
- Q4 Cement's comparison vocabulary = canonical JSON byte equality (`canonicalize`), the case rule
  (`Decisions` trust boundary = exact lookup) — a chosen comparison, never a semantic oracle.
- Q5 A historical version's answer = the immutable receipt plus the memberships, artifacts, reports,
  tests and projection rows it references (`reconstruct_function_receipt`; CLI `function export
  --receipt-id`), uncached. p35's serving cache keys on the whole ledger (file identity +
  `data_version` + expected hash), so ANY commit to the ledger — a telemetry row included — makes the
  next `resolve` cold (consultant-1 probe: verifier counts `[1, 1, 2, 3]` for cold, warm, re-query with
  an expected hash, after a simulated `shadow.observed` commit). The p35 bench (50,000 entries: cold
  145,702 ms, warm 4,896 ms, loaded host) prices `resolve`, not a telemetry cycle.

## Obligations (the milestone)

- S1 Sample off the answer path. The `outlet` selects hits (a matched-hit extractor over
  `_tool_calls`) at a per-operation rate, enqueues a detached immutable descriptor per selected hit
  (stable observation id, operation, original input, the captured function hash, time) without
  awaiting any model or Cement work, and returns `body` unchanged. A bounded worker makes the model
  call + the Cement record; queue overflow, timeout, shutdown and a duplicate admission (a second
  `/api/chat/completed` run) each have a named outcome and a counter. The rate decision and the
  observation id are fixed before any model call. The shadow prompt = the operation's contract +
  the original input — never the Cement answer or the chat reply — and the shadow call reaches
  neither the Cement tools nor the sampler. Open WebUI internals load lazily by their full names
  (`replace_imports` leaves them intact).
- S2 Record into a separate telemetry store (its own SQLite file beside the ledger, T6), so a sample
  never invalidates p35's cache and the ledger's invalidation stays complete. `record_shadow(…,
  function_hash, input_value, llm_output, observation_id, model, prompt_revision, timing)` derives
  `agreed` from the CAPTURED version — never whichever version is current when the worker finishes
  — and the revision from its validated receipt: a fast path only where the served document passes
  with that exact hash, else historical reconstruction (switch off or a revision change included).
  It retains the bounded canonical original input + the output + model/prompt identity + timing,
  and refuses a malformed or oversized value, a corrupt reconstruction, a foreign scope, an input that
  version misses and a repeated observation id before any commit.
- S3 Report + inspect. `drift(partition, operation, *, since_us=None)` counts every retained
  observation in one snapshot, grouped by distinct function hash (several receipts can share one),
  with an inclusive cutoff on the observation time, a defined zero result, a fixed order, preview
  limits applied after aggregation, and the dropped/failed attempts beside the agreements; the
  per-operation disagreement count = the sum over its hashes. `observations(…)` pages each
  observation (input, LLM output, function answer, hash, model/prompt identity, timing). CLI
  `cement function drift OPERATION [--since …]`; the Open WebUI learning tool + skill read both.
- S4 Never act. No sampler, record or report path calls `challenge` or changes a switch, function,
  projection or proposal; a disagreement is evidence for a separately run learning pass, whose
  later `challenge` is its own deliberate mutation (re-checked against the current revision).
- S5 Probe (the row's acceptance, run by the build): one frozen primary completion replayed at rate 0
  and rate 1 (two fresh chats differ — `examples/open_webui/README.md`), comparing the serialized
  caller-visible content; N > 0 distinct observations with mixed agreement plus all-agree and
  all-disagree controls → model calls = N, rows = N, `drift` = N − k disagreements for that hash and
  0 elsewhere; rate 0 → no call, no write; a duplicate `/api/chat/completed` run → one observation;
  a blocked shadow call → the response completes first; a failed or invalid model output → a counted
  failure, no row; a version change between hit and record → the captured hash still decides.

## Threat model + docs changes

- `## Deliberately absent` `Active shadow sampling.` → the supported scope: Open WebUI, off by
  default (per-operation rate); nucllei excluded (T4).
- `## Deployment obligations` `Monitor promoted scopes. …` → `function drift` + `observations` as the
  monitor, the learning pass's deliberate `challenge` as the response; agreement with one stochastic
  model is no correctness oracle, and an observation is no proof that a production request happened.
- `## Untrusted` bullet 2 (LLM candidate output) → covers the shadow answer: evidence, never an
  instruction.
- `## Deployment obligations` `Minimize, redact, encrypt, expire …` → the telemetry store holds
  plaintext inputs + outputs: its own classification + retention under the operator's management
  (p87 E3's prune = a future integration, not a guarantee here).
- README + the Open WebUI example README: the surfaces, the valves, sampling/drop behavior, the
  observation-id replay rule, the learning tool's reads, and the measured cost of `resolve → record
  → resolve` (no cost claim before that measurement).

## Owner decisions

- T1 comparison = canonical JSON (recommended) vs a per-operation comparator.
- T2 store the LLM output (recommended) vs its hash alone.
- T3 a disagreement stays telemetry (recommended) vs entering the learning pass as a proposal.
- T4 nucllei excluded (recommended) vs a separate batch job over its ledger.
- T5 a per-operation rate (recommended) vs a call budget per time window.
- T6 execution + storage = a bounded asynchronous worker + a separate telemetry store (recommended)
  vs inline work or the ledger itself (both rejected by Q2 + Q5).
- T7 observation identity = the chat message + tool-call id, admitted once before model work
  (recommended).
- T8 comparison context = a fixed base model + a versioned operation/output prompt without Cement
  answers or tools (recommended).
- T9 diagnostic data = the original input + output + model/prompt + timing per observation
  (recommended) vs a resolvable locator.

## Gates (the build's numbered list; rerun from committed state)

1. Red-first: S5 in full; `record_shadow`'s refusals with zero writes (adjacent pairs: a receipt of
   the operation vs one of another; a hit vs a miss; a fresh vs a repeated observation id); `agreed`
   follows the captured hash after a newer promotion; `drift` exact across two hashes sharing
   receipts, the cutoff edge and an empty window; `resolve` + `serving` unchanged with telemetry
   present (`p32-differential.py` `SAME`) and p35's cache still warm after a recorded sample.
2. Full gate = CI gate (D28 included).
3. `docs/threat-model.md` + README + the Open WebUI example README per the list above; register +
   article audits rc 0; the `resolve → record → resolve` cost measured with per-point provenance.

```claims
33	50,000 entries	unchecked	the p35 bench point `n50000` in `.agent/decisions/p35-resolve-bench.json` (entries 50000)	50000
34	145,702 ms	unchecked	rounded from p35-resolve-bench.json `points.n50000.median_cold_ms` 145702.38599 and `median_warm_ms` 4896.178618 (a float the grader's kinds do not read)	145702
68	rate 1	unchecked	a planned probe setting, not a measurement	1
71	rate 0	unchecked	a planned probe setting, not a measurement	0
82	bullet 2	unchecked	a position in `docs/threat-model.md` `## Untrusted` at 93ff847, read by MAIN; positions are no counts	2
116	rc 0	unchecked	a gate expectation of the unbuilt milestone	0
```
