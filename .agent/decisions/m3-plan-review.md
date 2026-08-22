# M3 Plan Adversarial Review

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| F001 | .agent/memory.md:9 | `MAIN pays both halves from one window` | L1 | defect | Every analog uses one historical half; current MAIN owns implementation plus coordination. Split from combined cost, not one gauge. |
| F002 | .scratch/agents/plan-m3.md:201 | `A pre-open` | L1 | defect | Relocation diff and archive membership exist only after a prototype implements the move. Fund a separate prototype or split now. |
| F003 | .scratch/agents/plan-m3.md:205 | `both halves are below one half of the analog` | L1 | defect | M3.8 prod 75 is 64.7 percent of u5a changed prod 116, not below half. Recompute from churn. |
| F004 | .scratch/agents/plan-m3.md:53 | `130 prod / 220 test` | L1 | confirmed-sound | Current M3.5 table and sizing section agree; the earlier 330/260 versus 600/320 mismatch is gone after renumbering. |
| F005 | .scratch/agents/plan-m3.md:213 | `2,472 non-test lines / 2,146 test lines` | L1 | confirmed-sound | Nine row totals and all four track subtotals recompute exactly. |
| F006 | .scratch/agents/plan-m3.md:49 | `oracle` | L2 | defect | M3.1 is deletion plus preservation census; an independent deletion adds no differential signal. Remove tag. |
| F007 | .scratch/agents/plan-m3.md:53 | `oracle` | L2 | defect | M3.5 is parser forwarding over settled APIs; M2.u4c3 explicitly rejected an oracle for this shape. Remove tag. |
| F008 | .scratch/agents/plan-m3.md:54 | `oracle` | L2 | defect | M3.6 is structural deletion. Use schema census, real old-ledger fixtures, mutation, and artifact validation instead of a full reference implementation. |
| F009 | .scratch/agents/plan-m3.md:55 | `oracle, prod` | L2 | defect | Relocation has byte equality and archive tests as stronger oracles. Keep prod and remove oracle. |
| F010 | .scratch/agents/plan-m3.md:56 | `data` | L2 | confirmed-sound | Demo/transcript data is structurally validated and live-rechecked; data tier is correct. |
| F011 | .scratch/agents/plan-m3.md:7 | `strictly sequential` | L3 | defect | File overlap is not semantic dependency under worktree isolation. Replace the chain with a DAG. |
| F012 | .scratch/agents/plan-m3.md:55 | `M3.6` | L3 | defect | Relocation needs final CandidateRequest from M3.3 and CLI cut from M3.5, not request-table deletion. M3.6 and M3.7 can run concurrently. |
| F013 | .scratch/agents/plan-m3.md:56 | `M3.7` | L3 | defect | Hospital code has no owned-path overlap with relocation. After M3.6 it can run concurrently against the ruled destination path. |
| F014 | .scratch/agents/plan-m3.md:52 | `M3.3` | L3 | confirmed-sound | Proposal-only consumers genuinely require the submission/binding seam first. |
| F015 | .scratch/agents/plan-m3.md:25 | `1,095-line lower bound` | L4 | defect | Only 835 named method spans are exact; 260 lines are estimated, and rewrite spans are not changed-line lower bounds. Relabel as exposure estimate. |
| F016 | .scratch/agents/plan-m3.md:29 | `same-version transient schema` | L4 | defect | This rejects only one transient design. Delay all schema work to one final v3 cut and keep earlier checkpoints on unchanged v2. |
| F017 | .scratch/agents/plan-m3.md:25 | `proposal read/project methods 129` | L4 | confirmed-sound | The four named read/project methods sum to 129; `_proposal_content` adds an omitted 13-line exposure. |
| F018 | .scratch/agents/plan-m3.md:91 | `matching legacy request` | L4 | risk | Compatibility-FK and legacy-origin predicates are transient test work. A delayed schema cut avoids at least two disposable test families. |
| F019 | .scratch/agents/plan-m3.md:49 | `provenance is unchanged` | L5 | defect | Unquantified preservation passes after dropping one field and its test. Drive all former sites and compare exact row, receipt, hash, and event bindings. |
| F020 | .scratch/agents/plan-m3.md:50 | `enforced-read connection` | L5 | defect | Functional results do not prove enforcement. Require URI flags, error codes, authorizer coverage, snapshot lifetime, rollback/close, and byte equality. |
| F021 | .scratch/agents/plan-m3.md:51 | `fresh attempts` | L5 | defect | This omits exact scope/hash/FK bindings, source-error secrecy, acknowledgement shape, and sequential plus concurrent duplicate attempts. Promote the detailed seed. |
| F022 | .scratch/agents/plan-m3.md:52 | `proposal-owned bindings only` | L5 | defect | A lazy implementation can retain hidden request joins and updates. Require an SQL proxy that rejects every application statement naming requests. |
| F023 | .scratch/agents/plan-m3.md:53 | `pins every parser node and output channel` | L5 | defect | Parser census alone misses ledger creation, embedded-document emission, abbreviation survival, and exact exit/channel matrices. Add live route probes. |
| F024 | .scratch/agents/plan-m3.md:54 | `request table` | L5 | defect | Broad absence can miss one index, constructor field, export, event, or cache scalar. Require schema/import/signature/help/event censuses and artifact metadata checks. |
| F025 | .scratch/agents/plan-m3.md:55 | `preserve the full battery` | L5 | risk | Name byte equality, exact archive members, blocked reverse imports, wheel-only and sdist smokes, and the platform gap; ten current tests alone are insufficient. |
| F026 | .scratch/agents/plan-m3.md:56 | `regenerated masked transcript is exact` | L5 | defect | A dead helper or copied transcript can pass. Bind main-path calls, source counts, post-teardown timing, exact mask counts, and optimized-Python refusal. |
| F027 | .scratch/agents/plan-m3.md:57 | `Every M3 claim and command block` | L5 | defect | Broad prose is not replayable. Require a tracked 145-row ledger, live command/help/archive replay, zero orphan rows, and committed-state gate. |
| F028 | .scratch/agents/map-m3-3.md:245 | `S4-R23` | L6 | defect | No unit owns this README authorization wording; M3.5 and M3.9 both stop at R22. Add R23. |
| F029 | src/cement_runtime/errors.py:29 | `supervised fallback` | L6 | defect | Kept-public CandidateSourceError needs a request-free docstring, but no unit owns errors.py. Add it to M3.3. |
| F030 | .scratch/agents/plan-m3.md:55 | `examples/echo_adapter.py` | L6 | defect | M3.7 owns removed source paths but no new file under examples/command_candidate_source. Add the destination directory and files. |
| F031 | .scratch/agents/plan-m3.md:57 | `examples/hospital_ocr/README.md` | L6 | defect | Final replay claims relocated protocol rows but cannot edit the new command-source README. Add that README to M3.9. |
| F032 | .scratch/agents/plan-m3.md:97 | `source exceptions can leak arbitrary text` | L6 | defect | A named security risk has no exact error-normalization acceptance. M3.3 must rule CandidateSourceError and arbitrary Exception text. |
| F033 | .scratch/agents/map-m3-1.md:341 | `py.typed` | L6 | undecided-MAIN | Source-only packaging implies core-only typing, but the required ruling is not explicit. State it in M3.7. |
| F034 | .scratch/agents/res-m3-1.md:127 | `Changelog` | L6 | risk | Q3 requires a versioned breaking-change record; no path or equivalent release section is owned. Assign or explicitly reject. |
| F035 | .scratch/agents/plan-m3.md:113 | `--submission` | L6 | risk | Exact aggregate-envelope channel and bound are new plan inventions without map/probe comparison. Spike direct flags, stdin, and file channels first. |
| F036 | .scratch/agents/plan-m3.md:167 | `S4-R01-S4-R22` | L6 | defect | The claimed final ownership omits existing R23 and therefore owns 144 of 145 claim rows. Extend the range. |
| F037 | .scratch/agents/plan-m3.md:137 | `core types/JSON helpers` | L6 | risk | “May import” does not say whether private coupling is accepted or APIs become public. Record the compatibility boundary. |
| F038 | .scratch/agents/map-m3-1.md:288 | `direct-process-only hosts are not exercised` | L6 | risk | Relocated docs preserve this platform claim, but M3.7 does not add the recommended branch mock. Absorb it. |
| F039 | .agent/memory.md:14 | `.scratch/` | L7 | defect | Future units depend on gitignored maps and research. Copy binding claims and mechanisms into tracked decision state before roadmap landing. |
| F040 | CLAUDE.md:48 | `keep it minimal` | L7 | defect | A 50,625-byte draft cannot ride in roadmap every session. Keep executable summary there and move detail to tracked decisions. |
| F041 | CLAUDE.md:38 | `idempotent script replayable from a clean base` | L7 | defect | M3.8 names transcript regeneration but no updater. Add a replayable fenced-block rewrite and prove a second run byte-identical. |
| F042 | .scratch/agents/plan-m3.md:41 | `M3.2 must record cold/warm time and peak RSS` | L7 | defect | No tracked benchmark result path is owned. Give release-semantic performance evidence a durable destination. |
| F043 | .scratch/agents/plan-m3.md:219 | `each row is born with its close check` | L7 | confirmed-sound | Off-spine items have acceptance checks and duplicate existing rows by subsumption rather than blind append. |
| F044 | CLAUDE.md:37 | `committed state` | L7 | defect | Only later units explicitly name committed-state gates. Make post-commit rerun global for all durable unit claims. |
| F045 | .scratch/agents/plan-m3.md:11 | `measured 496-line` | L8 | defect | The figure combines 409 exact deleted method spans with about 87 forecast rewrite lines. Call it an estimate. |
| F046 | .scratch/agents/plan-m3.md:27 | `changed 765 production lines` | L8 | defect | u3b1 cumulative production churn is 785 additions plus deletions. Recompute under the declared metric. |
| F047 | .scratch/agents/plan-m3.md:27 | `changed 776 production lines` | L8 | defect | u4b cumulative production churn is 809; 776 counts additions only. |
| F048 | .scratch/agents/plan-m3.md:177 | `map gives the test count directly` | L8 | defect | The map gives 409 exact spans and about 87 estimated edits, not a direct 496 count. |
| F049 | .scratch/agents/plan-m3.md:181 | `1,159 test lines` | L8 | defect | u4a changed 1,163 test lines; 1,159 is net delta. |
| F050 | .scratch/agents/plan-m3.md:201 | `About 298 source lines` | L8 | risk | 298 is the entire module including the retained protocol; the relocating class spans 268. Measure moved imports separately. |
| F051 | .scratch/agents/plan-m3.md:209 | `170 claim rows` | L8 | defect | The three maps contain 145 rows. Correct the count and ownership range. |
| F052 | .scratch/agents/plan-m3.md:209 | `fewer than half the prior changed lines` | L8 | defect | 584 was u5b review exposure; actual changed markdown churn was 280, making 260 about 93 percent. |
| F053 | .scratch/agents/plan-m3.md:215 | `No unit's semantic implementation half approaches` | L8 | defect | “Semantic half” is undefined and unmeasured; it cannot close sizing while M3.7 remains explicitly red-flagged. |
| F054 | .scratch/agents/plan-m3.md:173 | `planning ranges, not promised diffs` | L8 | confirmed-sound | This caveat is sound for table forecasts; apply it consistently instead of later calling forecasts measured bounds or caps. |

## L1 — Sizing realism

**Verdict: defect.** Every quoted `main=`/`impl=`/`mate=` gauge exists and the percentages are transcribed correctly. The fit inference is still invalid. `.agent/memory.md` states that every M2 measurement came from split authorship: MAIN paid coordination while a teammate paid implementation. Current MAIN pays both halves in one window. The draft compares each M3 estimate to one historical half, then declares a one-window fit. This is the exact apples-to-oranges comparison that memory forbids.

The changed-line citations also mix additions, deletions, net delta, estimates, and review surface despite S4 defining `prod` as changed/deleted lines. Re-derived cumulative diffs:

- u3b1 = 785 changed production lines and 4,421 changed test lines, not 765 production.
- u4a = 99 changed production and 1,163 changed test lines, not 1,159 test.
- u4b = 809 changed production lines, not 776.
- u4c1 = 46 changed production and 907 changed test lines; 500-740 was its estimate, not its landed contract.
- u5a = 116 changed non-test and 399 changed test lines, not 106/395.
- u1 = 423 changed non-test lines when its 26 export lines are counted, not only the 397-line new module.

The unit-table arithmetic itself is correct: 2,472 non-test / 2,146 test. The track subtotals also reconcile. The earlier M3.5 contradiction is gone: current M3.5 is consistently 130/220, while lifecycle deletion moved to M3.6 at 602/320. However, M3.8’s statement that both estimates are below one half of u5a is arithmetically false: 75 is 64.7% of u5a’s 116 changed non-test lines, or 70.8% of the draft’s own 106 figure.

M3.7’s stop condition is not pre-open measurable. Byte equality and semantic churn require a completed relocation diff; archive membership requires a built prototype. Performing that prototype is implementation work and consumes the very window the stop is meant to protect. M3.2, M3.4, and M3.6 repeat the same shape with “if factoring/query/authored lines exceed … split before implementation”: those counts become known only after factoring or editing. Replace each with a static pre-open source-span budget plus a separately funded prototype/checkpoint, or split now.

Recommended sizing correction: remove non-differential oracle campaigns (L2), split M3.2 into Store enforcement and resolver composition, split M3.5 along the cheap CLI seam, stage lifecycle removal so the single schema cut is small (L4), and split docs authoring from final claim replay. Do not claim any remaining unit fits from a single historical half.

## L2 — Tier and tag assignment

**Verdict: defect.** The kernel/data/docs tiers are sound. The seven `oracle` tags are not. An oracle is valuable only when an independent implementation can make a materially different contract choice whose output can be compared. Deletion and relocation mostly yield absence or byte equality; an independent implementation adds campaign cost without a differential signal.

Per unit:

- M3.1: remove `oracle`. The contract is a structural deletion plus preservation census. A second deletion cannot reveal more than signature/reference counts, provenance probes, and mutation of surviving invariants.
- M3.2: keep `oracle`. Independent connection-helper structure can diverge on VFS mode, authorizer completeness, snapshot lifetime, missing-file behavior, and result grading.
- M3.3: keep `oracle`. Independent submission implementations can diverge on transaction boundaries, revision fencing, freshness, hash/scope binding, exception normalization, and returned shape.
- M3.4: keep `oracle`. Independent proposal projection/review/report implementations can diverge on joins, scalar validation, scope equality, event identity, and evidence creation.
- M3.5: remove `oracle`. This is parser/dispatch forwarding over settled public calls. M2.u4c3 explicitly declined `orc` for the same reason: a forwarding leaf’s reference implementation is the same forwarding code.
- M3.6: remove full-unit `oracle`; add `prod`. Request/schema/API deletion is closed better by exhaustive structural census, real v2/v3 refusal fixtures, schema-object comparison, and mutation of every surviving binding. A narrow independently derived final schema may be a probe, but it does not justify a reference implementation of the whole deletion unit. The package-version/build metadata requires artifact validation.
- M3.7: remove `oracle`, keep `prod`. Byte-preserving supervisor/stub relocation has `cmp` as its oracle. Archive membership, blocked reverse imports, wheel/sdist smokes, and the retained runner battery provide the meaningful signal. A separately rewritten process supervisor is actively worse evidence.
- M3.8: keep `prod` only.
- M3.9: keep `-`; use a consistency/claim reviewer.

Corrected tag set: M3.1 `-`; M3.2-M3.4 `oracle`; M3.5 `-`; M3.6 `prod`; M3.7-M3.8 `prod`; M3.9 `-`. This reduces seven reference campaigns to three without lowering kernel assurance.

## L3 — Dependency order and parallelism

**Verdict: defect.** Several semantic dependencies are real, but the nine-edge chain treats file overlap as dependency. Worktree isolation exists precisely to separate file ownership during implementation.

Real edges:

- M3.1 → M3.3: the new mutating submission seam must not acquire a short-lived callback gate.
- M3.3 → M3.4: proposal-owned/public bindings must exist before consumers move.
- M3.4 → M3.5: CLI review/submit output must consume final result shapes.
- M3.5 → M3.6: public callers must leave `handle`/`request` before their implementation and schema disappear.
- M3.6 → M3.8: the demo needs final request-free APIs/schema.
- all behavior/data units → M3.9: the claim pass must observe final code and transcript.

False or unnecessarily strong edges:

- M3.2 does not depend on M3.1. Resolver work is authority-free by contract and touches verifier/read paths, while callback removal touches constructor/mutation gates. They overlap only `system.py` and `test_system.py` and can run in isolated worktrees with a focused merge.
- M3.3 does not semantically depend on M3.2. They overlap five files, so concurrent implementation is integration-heavy and not recommended, but the roadmap should state a merge-order constraint rather than a false API dependency.
- M3.7 needs request-free `CandidateRequest` from M3.3 and CLI source removal from M3.5; it does not need M3.6’s request-table deletion. M3.6 and M3.7 overlap only `src/cement_runtime/__init__.py`, deleting disjoint export families, and can run concurrently after M3.5.
- M3.8 has no owned-path overlap with M3.7. Its only linkage is the already-ruled destination of the optional-runner README. After M3.6, implementation can run concurrently with M3.7 and integrate the link once the destination lands.

A safe execution DAG has seven sequential waves rather than nine: `{M3.1, M3.2}` → `M3.3` → `M3.4` → `M3.5` → `{M3.6, M3.7}` → `M3.8` → `M3.9`. The corrected split in L4/L7 adds units but preserves parallel waves.

## L4 — Two-bump schema decision

**Verdict: defect.** The seven exact spans remeasure as claimed: 271 + 32 + 116 + 14 + 129 + 231 + 42 = **835** lines. The 129 proposal read/project subtotal is `get_proposal` 38 + `proposal` 20 + `proposals` 43 + `_proposal_record` 28; it excludes `_proposal_content`’s 13 lines even though M3.4 owns that helper.

The claimed 1,095-line “measured lower bound” is not measured and is not a lower bound. It adds to 835: “about 90” schema lines, an inferred 70 model/export lines, and “at least 100” unenumerated integration lines. Full method spans for methods being locally rewritten are exposure, not changed-line lower bounds. The ~1,275 coarse total then adds another estimated 180. These figures can justify caution, but not the asserted necessity of two schema versions.

The rejection tests only a same-version transient schema after M3.3 has already changed schema. It misses a better one-bump ordering:

1. Keep schema v2 while adding request-free `submit_proposal`/`generate_proposal`; use one private fresh request row per attempt as temporary storage plumbing. Expose no request ID, lease, replay, or polling contract.
2. Move public proposal/read/review/report models onto request-free shapes through one internal binding seam while the seam still aliases current request joins.
3. Cut CLI callers from `handle`/`request`.
4. Delete public lifecycle methods, lease logic, result models, and exports while retaining only the private compatibility plumbing needed by the unchanged schema.
5. In one final schema-v3 unit, add direct proposal bindings, swap the internal seam, delete `requests`/its index/companion updates, and bump package metadata.

Only step 5 changes `SCHEMA`. No same-version fingerprint lies. Public tests from steps 1-4 survive the cut. Static size bounds stay below cited analog surfaces: the schema-neutral lifecycle deletion is 433 exact method-span lines plus constructor/model cleanup; the final schema unit owns the current 74-line request/proposal/index schema region plus localized insert/query/version changes, not the entire 835-line consumer surface.

The draft does not specify test-method granularity, so an exact method count would be invented. Its contract nevertheless creates at least **two wholly disposable transient test families**—legacy inserts populating compatibility columns and legacy-origin proposal parity—and **two mid-milestone rewrites**—nullable/FK v3 shape and fresh-v3 fingerprint/version expectations. The delayed one-bump ordering creates **zero** new transient-schema test families; existing v2 refusal tests update once to final v3. MAIN should prototype this ordering before accepting the dual bump.

## L5 — Gate coverage and acceptance strength

**Verdict: defect, highest-value lens.** Every table row ends with the gate, but the gate can stay green after deleting both behavior and its pin. The detailed seeds are much better than the table; make their quantified predicates normative acceptance rather than optional “seed” text.

- **M3.1 weak:** “`authority` is absent” and “provenance is unchanged” are unquantified. Lazy pass: remove the constructor keyword and delete authority tests while leaving renamed/dead gates or dropping one actor field. **Replace with:** exact zero census for `AuthorityCheck`, constructor `authority`, `_authority`, `_authorize`, and 11 former calls; frozen remaining constructor shape; drive every former mutation with distinct labels and read each row/receipt/event; one-plan call counts; empty-union before clock/ID/write; wrong expected hash still rejected; schema/version/SQL/fingerprint byte-equal to parent.
- **M3.2 weak:** functional hit/miss tests can pass on an ordinary read-write connection. **Replace with:** actual `file:` URI + `mode=ro` + `uri=True`; `query_only==1`; authorizer installed before SQL; injected row/DDL/PRAGMA/virtual-table/attach/detach operations fail `SQLITE_AUTH`; authorizer/query-only-disabled main write still fails `SQLITE_READONLY`; one transaction remains live through the last helper then rolls back/closes; missing path creates nothing; pre/post digest and dump equal; all P1-P6 first/middle/last corruptions; measured 1/1,000/50,000 record with no extra full pass/cache.
- **M3.3 weak:** the table does not close direct-field integrity, source-failure secrecy, acknowledgement shape, or duplicate attempts. **Replace with:** exact schema/object bindings; every digest and scope/FK comparison mutation killed; source observes no transaction; revision recheck under lock; source failures produce the ruled exact domain error with no proposal/event and no secret text; equal sequential and concurrent calls produce distinct proposals; acknowledgement contains only proposal ID/tag; candidate mutation after return cannot alter stored bytes; v2 refusal is byte/dump/version/sidecar stable if the dual bump survives L4.
- **M3.4 weak:** “use proposal-owned bindings” can be asserted while hidden request joins/updates remain. **Replace with:** an application-SQL proxy rejects every statement naming `requests`; all read/review/report paths still pass; accept/correct/reject exact row/event/evidence transitions; no companion request update; exact public signatures and field sets; no request ID in any event; 10,001-tail count, bounded detail, reverse-order and `=`/case/underscore isolation; every selected persisted scalar translated fail-closed.
- **M3.5 weak:** parser census alone does not prove read-only routing or channel semantics. **Replace with:** live matrix for hit/miss/unverified/corrupt/unknown/missing ledger with exact status/stdout/stderr/key sets; missing resolve never creates a file; custom projection never serializes the embedded document; exact four-key submission envelope and max/max+1; every removed leaf/flag fails even under abbreviation; import trace shows no `CommandCandidateSource`; all parser nodes/help blocks and shown commands execute.
- **M3.6 weak:** broad absence prose can miss one index, constructor field, export, event, cache field, or metadata artifact. **Replace with:** sqlite-master/schema-string/public-import/signature/help/event vocabulary censuses; all removed imports fail; same-candidate attempts remain independent; fresh final schema metadata/fingerprint exact; real v2 and transient-v3 ledgers reject through library and CLI before byte/dump/version/sidecar change; built wheel metadata and lock root both equal 0.2.0; package description contains no fallback/lifecycle claim.
- **M3.7 mostly strong, but incomplete:** “full battery” and “preserve” need byte/artifact identities. **Replace with:** `cmp` supervisor and stub against pre-move bodies after normalized import/envelope edits; blocked reverse-import trace; exact structural protocol shape; ten runner tests plus exact request/environment/platform gaps; sibling `__file__`; exact wheel/sdist member sets; wheel-only core import and sdist runner smoke; no dependency/metadata churn except the prior package version.
- **M3.8 weak against dead helper/faked transcript:** **Replace with:** main-path spies bind `resolve`, `generate_proposal`, `review`, `parse_function`, and `evaluate`; exact five-generation/two-hit call counts; promoted hits make zero source calls; miss remains inert until explicit generation; mask counts exactly one each; transcript byte-equal after masking; offline calls occur after the exact temporary directory is absent; `-O`/`-OO` fail.
- **M3.9 broad and non-replayable as written:** **Replace with:** a tracked claim ledger whose every row has final PASS/removed/replaced disposition; replay all live command blocks and help nodes; inspect final archives; run v2/final-version refusal, demo transcript, link/one-H1 diagnostics, register audit, and paragraph-1 `cmp`; zero unowned rows and zero stale command tokens; rerun the sole gate from committed state.

Add one global rule: each unit’s acceptance battery and configured gate rerun from that unit’s committed checkpoint. A prose assertion plus a green suite is never closure for removal.

## L6 — Missed scope

**Verdict: defect.** All **40 numbered forks** do have a ruling; the misses are in normative rows and mechanical hazards.

Fork census:

- map-m3-1 forks 1-12 → M3.7; cross-owners are M3.5 for CLI sequencing, M3.3 for final `CandidateRequest`/source errors, and M3.6/M3.9 for compatibility/release communication.
- map-m3-2 forks 1-14 → M3.1; M3.9 performs the final documentation replay.
- map-m3-3 forks 1-14 → M3.2-M3.8; repair/quarantine is explicitly deferred with an acceptance check.

Unowned or incompletely owned scope:

1. **Orphan claim S4-R23.** map-m3-3 has 23 README rows, but M3.5 stops at R22 and M3.9’s “all” range is also R01-R22. The claim “`handle` and read APIs assume …” has no unit. Add R23 to M3.5 and M3.9.
2. **`errors.py` is missing from ownership.** The chosen keep-public `CandidateSourceError` ruling requires rewriting its current “supervised fallback” docstring. No unit owns `src/cement_runtime/errors.py`. Add it to M3.3, where the direct source error contract changes.
3. **The relocation destination is not owned.** M3.7’s table lists only the source files being removed. It does not own any new path under `examples/command_candidate_source/`, despite requiring an implementation, sibling supervisor, stub, and README there. Add the destination directory/files explicitly.
4. **The final claim pass cannot repair its claimed surface.** M3.9 claims all relocated protocol/security rows but does not own `examples/command_candidate_source/README.md`. Add it. If final help replay can produce fixes, define a reopen path to M3.5 or give the help-only edit its own kernel unit; a docs unit must not silently edit `cli.py`.
5. **Source-failure secrecy remains a named risk, not a contract.** M3.3 says broken sources raise `CandidateSourceError` directly while warning that source exceptions can leak arbitrary text. Specify normalization for `CandidateSourceError` and arbitrary `Exception`, exact public text, and no durable row/event. Assign to M3.3.
6. **Three relocation hazards remain implicit:** whether the source-only example knowingly depends on private JSON helpers; whether `py.typed` covers core only; and the documented direct-process-only platform branch, which has no test. State the private-API/typing disposition and add the platform-branch mock in M3.7.
7. **Release-note recommendation dropped.** Research Q3 requires a versioned 0.2.0 `Removed`/`Changed` record naming every break. The repo has no `CHANGELOG.md`, and no unit owns an equivalent versioned release note. MAIN must either add it to M3.9 or explicitly reject it in favor of a named README release section.

Reverse unsupported obligation: M3.5 invents the exact `--submission` aggregate JSON channel, four-key envelope, and framing bound. The maps select explicit submission but do not measure or compare this CLI channel. Keep the decision only after a small channel spike against direct flags/stdin/file alternatives and exact error behavior.

Claim-count check: map-m3-1 has 59 rows, map-m3-2 has 28, and map-m3-3 has 58: **145 total**, not 170. The current M3.9 range owns only 144 because it drops R23.

## L7 — CLAUDE.md conformance

**Verdict: mixed; four defects, three confirmed-sound areas.**

Defects:

1. **Durable scratch dependency.** Unit detail tells future work to replay exact rows from `.scratch/agents/map-m3-*.md` and relies on `.scratch/agents/res-m3-1.md`. Project memory explicitly says that gitignored scratch pointers are dead in every clone and that binding claim inventories/interfaces must be copied into tracked state. Before roadmap landing, move the compact claim ledger, fork rulings, resolver mechanism, and release obligations into a tracked `.agent/decisions/` record; roadmap units may point there.
2. **Attached-state bloat.** The draft is 50,625 bytes. If copied into `.agent/roadmap.md`, it violates “attached state rides every session whole → keep it minimal.” Keep decisions, DAG, unit rows, stop conditions, and acceptance predicates in roadmap. Put probe corpora, historical analog arithmetic, and per-claim replay detail in tracked decision records.
3. **One-window and committed-gate rules.** L1 shows that the one-window fit is not established. L5 shows that only M3.7/M3.9 explicitly name committed-state validation. Add a global committed-checkpoint rerun and split before dispatch using static predicates, not post-edit line counts.
4. **Generated transcript regeneration is not re-derivable.** M3.8 changes a generated README transcript but names no idempotent regeneration script/path. Add one replayable updater or a deterministic command that rewrites only the fenced transcript, and prove a second run is byte-identical.
5. **Benchmark evidence has no durable owner.** D5 says the release must publish 1/1,000/50,000 timing/RSS, but M3.2 owns no tracked result record. Give the benchmark protocol/result a tracked path and archive it after M3; do not leave a durable cost claim backed only by terminal output.

Confirmed sound:

- Tier assignments satisfy the assurance rule: M3.1-M3.7 are judgment-bearing kernel code, M3.8 is consumer-revalidated data with a structural transcript validator/live run, and M3.9 is docs consistency.
- MVP-spine discipline is strong. The nine off-spine items each carry a close check. Existing `_request_id` and oversized-function-layer polish rows are explicitly subsumed rather than duplicated.
- README paragraph 1 remains the fixed scope source, and M3.9 explicitly requires byte equality rather than narrowing it to fit the implementation.

Authoring risk: this is an agent artifact, but much of S3/S4 repeats provenance and explanatory narrative. Compress it into rules/measurements. Keep rejected-alternative rationale only where a future unit needs it to avoid reopening a settled fork.

## L8 — Claim soundness

**Verdict: defect.** The “planning ranges, not promised diffs” caveat is valid for the nine table estimates and explicit `about`/`roughly` forecasts. Elsewhere the draft promotes those same estimates into measured facts, lower bounds, caps, and fit proof.

Unsound measured/arithmetic claims:

- D1’s “measured 496-line” track-b test edit is 409 measured method-span lines plus about 87 estimated rewrite lines.
- D3’s 1,095-line “measured lower bound” is 835 exact method spans plus 260 estimated/inferred lines; rewritten method spans are not changed-line lower bounds. The ~1,275 figure is therefore a coarse estimate only.
- D3 calls 780-1,130 “measured test churn”; map-m3-3 labels it a budget derived from 281 exact deletion lines plus estimated fixture/result rewrites.
- M3.1 says the map gives 496 directly and that its 500-740 u4c1 test contract was landed evidence. The landed u4c1 diff is 907 changed test lines.
- M3.2 uses u4a’s net +1,159 tests as changed lines; actual churn is 1,163.
- M3.3 says u3b1 changed 765 production lines; cumulative churn is 785.
- M3.4 says u4b changed 776 production lines; cumulative churn is 809.
- M3.7 says about 298 source lines move, but `CommandCandidateSource` itself spans 268; the 298 is the entire current module, including the protocol that stays.
- M3.8 cites u5a net 106/395 instead of changed 116/399, then falsely says 75/180 are both below half.
- M3.9 says the maps contain 170 claim rows; they contain 145. It compares a 260-line changed estimate to u5b’s 584-line **review surface**, then calls that “fewer than half the prior changed lines.” u5b’s actual changed markdown churn is 280, so 260 is about 93%, not under half.
- “No unit’s semantic implementation half approaches” past peaks has no measured semantic-line definition or coordination model and contradicts the red-flag/stop clauses.

Unsupported causal inferences:

- A 212-anchor map does not prove that fork discovery—the claimed dominant u4c1 cost—has disappeared.
- File overlap does not prove a semantic dependency or rule out worktree parallelism.
- A post-relocation diff/archive prototype cannot be called a pre-open measurement unless it receives a separately budgeted implementation wave.
- “Two green checkpoints require two versions” is true only after choosing to change schema twice; it does not refute delaying schema until the final cut.

Confirmed sound measurements: all quoted gauge percentages; the seven exact method spans totaling 835; 511 affected test methods; ten concrete-runner tests; 2,472/2,146 table totals and track subtotals; Q4’s measured SQLite mechanism behavior. Preserve these, relabel every forecast, and recompute analogs from additions + deletions under one metric.

## Recommended corrected unit table

| unit | tier/tags | depends | correction |
|---|---|---|---|
| M3.1 | kernel / `-` | none | Remove callback and only callback-owned scaffolds; exact provenance/schema preservation census. |
| M3.2a | kernel / `oracle` | none | Add existing-only `mode=ro` Store enforcement and the full capability-denial battery. Run parallel with M3.1. |
| M3.2b | kernel / `oracle` | M3.2a | Factor one-snapshot P1-P6 verification, add `FunctionResolution`, and publish durable 1/1k/50k measurements. |
| M3.3 | kernel / `oracle` | M3.1 | Add request-free direct/source submission over unchanged schema v2; use private fresh request rows only as temporary storage plumbing. Run parallel with M3.2b. |
| M3.4 | kernel / `oracle` | M3.3 | Freeze request-free proposal/read/review/report/event public seams behind one internal binding adapter while schema stays v2. |
| M3.5a | kernel / `-` | M3.2b, M3.4 | Spike and add `resolve` plus `proposal submit` channels with exact exit/payload contracts. |
| M3.5b | kernel / `-` | M3.5a | Remove `handle`/`request`/source grammar, imports, fixtures, help, and operator prose. |
| M3.6a | kernel / `-` | M3.5b | Delete public lifecycle methods, leases, result models, exports, and lifecycle-only tests; retain only private v2 binding plumbing. |
| M3.6b | kernel / `prod` | M3.6a | Make the sole schema cut v2→v3: direct proposal columns, binding-adapter swap, request table/index deletion, refusal fixtures, package 0.2.0/build metadata. |
| M3.7 | kernel / `prod` | M3.3, M3.5b | Relocate command runtime with explicit destination ownership, byte equality, archive/import smokes, typing/private-API rulings, and no oracle. Run alongside M3.6. |
| M3.8 | data / `prod` | M3.6b | Regenerate demo/transcript through an idempotent updater; it may run alongside M3.7 against the ruled link path. |
| M3.9a | docs / `-` | M3.6b, M3.7, M3.8 | Rewrite the tracked 145-row claim ledger, all core/example/optional-runner docs, release record, and recovery guidance. |
| M3.9b | docs / `-` | M3.9a | Independent final claim/command/help/archive/link/register replay; fix docs or reopen the owning kernel unit, then rerun committed gate. |

This table trades nine unsupported one-window assertions for smaller static seams, one schema bump, three meaningful oracle campaigns, and explicit parallel waves.

## VERDICT

**Do not execute the draft unchanged.** Its architectural decisions are mostly recoverable, but feasibility, closure, and durable ownership are not yet executable.

Ranked defects, most important first:

1. **CRITICAL — removal acceptance is non-closing:** F019-F024, F026-F027. A green gate can follow deletion of both behavior and its test. Promote quantified seeds into mandatory committed predicates.
2. **CRITICAL — one-window proof is invalid:** F001-F003, F053. Every analog split implementation from coordination, stop conditions are post-implementation, and two arithmetic claims are false.
3. **HIGH — dual schema bump is not forced:** F015-F016. The 1,095 lower bound is not measured; a delayed one-cut ordering removes transient schema/test churn.
4. **HIGH — oracle over-tagging:** F006-F009. Four campaigns cannot produce meaningful differential evidence and materially worsen fit.
5. **HIGH — orphaned security/release/ownership scope:** F028-F032, F036. R23, `errors.py`, relocation destinations, final optional-runner docs, and source-error normalization lack owners.
6. **HIGH — project-process violations:** F039-F042, F044. Scratch dependencies, roadmap bloat, non-idempotent transcript repair, missing benchmark record, and non-global committed gates violate durable workflow rules.
7. **MEDIUM — false serial dependencies:** F011-F013. Safe worktree pairs reduce critical-path depth and separate unrelated tracks.
8. **MEDIUM — measured-claim corruption:** F045-F049, F051-F052. The draft mixes churn, net delta, estimates, and reviewed surface, including a 145→170 claim-count error.

Risks requiring explicit MAIN rulings: F018, F025, F033-F035, F037-F038, F050. Confirmed-sound results: F004-F005, F010, F014, F017, F043, F054.

**Single most important correction:** make each removal unit fail when one real obligation remains or one preserved invariant disappears, independently of the broad suite. Without that, the plan can delete the pin beside the feature and report success.
