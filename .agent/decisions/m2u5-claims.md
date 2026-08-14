# M2.u5 — documentation claim inventory + function-layer guarantee ledger

Executable work list for u5b, and the source of truth for every sentence u5a/u5b write. Produced by two
`map` teammates whose own reports were gitignored scratch; carried here verbatim so the record travels.
Both passed the anchor validator at production (281 and 279 anchors, 0 bad, 0 unfilled).

Verdicts: `TRUE` holds as stated; `FALSE` contradicted by shipped code; `STALE` true before M2 but now
the superseded-as-sole-route workflow; `INCOMPLETE` true but materially understating what M2 proves;
`UNPINNED` no committed test decides it; `SCOPE` accurate today and scheduled for removal by M3 (the
bundled LLM-invocation runtime, the `authority()` callback, the request-lifecycle machinery) or M4.
Tally: TRUE 75, SCOPE 37, INCOMPLETE 20, UNPINNED 5, FALSE 4, STALE 3. The 32 non-TRUE, non-SCOPE rows
are u5b's work list; the `SCOPE` rows are deliberately left for M3.

`T:` = committed test name. `S:` = source anchor, resolved in the anchor manifest at the end.

---

# Part 1 — documentation claim inventory

## Section A — README.md

| id | file:line | verbatim claim (elide past 25 words with …) | verdict | evidence anchor | note |
|---|---|---|---|---|---|
| A001 | README.md:3-6 | Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior. The goal is to aggregate repeated work into a regular, if large, function that … | TRUE | T:test_repeat_evaluation_is_byte_identical_and_mutation_isolated | The function document and evaluator now make the opening goal executable. |
| A002 | README.md:8-11 | The safety boundary is intentionally small: Cement compiles only exact lookups. A promoted artifact matches one canonical JSON input inside one partition and one operation … | TRUE | T:test_unknown_input_returns_no_match | A function is a set of exact entries, not a wider predicate. |
| A003 | README.md:13-25 | ```text handle(request) ├─ one promoted exact match → resolved JSON plan └─ no safe match → LLM proposal (hidden from consumer) ├─ reject → audit … | STALE | T:test_function_export_writes_the_live_document_bytes_exactly; T:test_function_eval_never_reaches_the_ledger_globals | It presents the superseded sole route and omits set verification, set promotion, export, and offline evaluation. |
| A004 | README.md:29 | - LLM output is inert until an explicit supervisor accepts or corrects it. | TRUE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | The consumer outcome never exposes an unreviewed candidate. |
| A005 | README.md:30-31 | - The ordinary `handle` result exposes a proposal ID, never the proposed output. Review uses a separate surface. | SCOPE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | This inline request and review machinery belongs to M3. |
| A006 | README.md:32-33 | - Confirmed examples bind partition, operation revision, canonical input, final output, reviewer, resolution, time, and receipt digest. | TRUE | T:test_correction_is_the_fixture_and_conflicts_block_compilation | Accepted or corrected content becomes the immutable fixture. |
| A007 | README.md:34 | - Compilation is deterministic and model-free. Conflicts block builds; no majority vote hides them. | TRUE | T:test_correction_is_the_fixture_and_conflicts_block_compilation | The compiler does not vote through conflicting final outputs. |
| A008 | README.md:35-36 | - Verification replays every active example in the exact scope plus partition, operation, revision, and input boundary probes. | INCOMPLETE | T:test_function_verification_matches_independent_scoped_membership | True per artifact, but M2 also verifies the complete promoted set and its persisted function receipt. |
| A009 | README.md:37-39 | - Promotion names the verified scope hash and atomically rechecks operation policy, artifact content, the complete evidence snapshot, and the sealed verification test set. Its … | INCOMPLETE | T:test_promote_function_persists_receipt_memberships_and_projected_event | True per artifact, but set promotion repeats one function hash and persists a receipt plus ordered memberships. |
| A010 | README.md:40-41 | - Counterexamples, evidence revocation, ambiguity, or runtime integrity failure quarantine affected artifacts before fallback. | TRUE | T:test_counterexample_and_revocation_quarantine; T:test_runtime_integrity_failure_quarantines_then_falls_back | The artifact lifecycle still fails closed. |
| A011 | README.md:42-43 | - Request IDs are partition-local idempotency keys bound to immutable operation and input content. Candidate generation runs outside database transactions under a recoverable lease. | SCOPE | T:test_request_idempotency_and_partition_isolation; T:test_concurrent_retry_observes_generation_lease | The inline request lifecycle and lease machinery belongs to M3. |
| A012 | README.md:45-46 | Cement returns data, not effects. The caller must run every resolved plan through current authentication, authorization, policy, and idempotent effect execution. Determinism is not permission. | TRUE | T:test_supervised_miss_to_exact_artifact_hit | Every resolution surface returns data; no effect executor exists in the runtime. |
| A013 | README.md:50 | Requirements: Python 3.11+ with SQLite 3.37+ and `uv` for the development workflow. | TRUE | S:pyproject-python; S:store-min-sqlite | The package metadata and runtime SQLite guard match. |
| A014 | README.md:52-56 | ```bash uv sync uv run cement --db demo.db --partition acme operation register support.reply \ --min-confirmations 2 --min-reviewers 1 --min-span-seconds 0 ``` | TRUE | S:cli-parser-operation | The command and every option remain accepted. |
| A015 | README.md:58-59 | The relaxed thresholds above are for a local demonstration. Defaults require three confirmations, two recorded reviewers, and a seven-day observation span. | TRUE | S:compile-policy-defaults | CompilePolicy still carries these exact defaults. |
| A016 | README.md:61-62 | Ask the registered operation to handle JSON. The bundled adapter is a deterministic protocol stub, not an LLM. Replace its command with your provider wrapper. | SCOPE | S:command-candidate-source | The bundled LLM-invocation runtime belongs to M3. |
| A017 | README.md:64-69 | ```bash uv run cement --db demo.db --partition acme handle support.reply \ --request-id ticket-001 \ --input '{"question":"Where is my invoice?"}' \ --source-command '["python3","-m","cement_runtime.example_adapter"]' ``` | SCOPE | S:cli-parser-handle | This inline request and source-command workflow belongs to M3. |
| A018 | README.md:71 | A miss returns `review_required` and a proposal ID. Only the review surface reveals the suggestion: | SCOPE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | The behavior is shipped, but the request-lifecycle surface belongs to M3. |
| A019 | README.md:73-78 | ```bash uv run cement --db demo.db --partition acme proposal list uv run cement --db demo.db --partition acme proposal show prop_REPLACE_ME uv run cement --db demo.db … | SCOPE | S:cli-parser-proposal | The proposal workflow belongs to M3. |
| A020 | README.md:80-81 | Repeat with a distinct request ID until the confirmations satisfy the operation policy. Then run the independently gated lifecycle: | STALE | T:test_function_verify_drafts_forwards_scope_positionally_and_actor_by_keyword; T:test_function_promote_forwards_hash_and_actor_verbatim | Batch verification and set promotion now remove the one-artifact-at-a-time requirement. |
| A021 | README.md:83-89 | ```bash uv run cement --db demo.db --partition acme compile support.reply uv run cement --db demo.db --partition acme verify art_REPLACE_ME uv run cement --db demo.db --partition … | STALE | T:test_function_verify_drafts_forwards_scope_positionally_and_actor_by_keyword; T:test_function_promote_forwards_hash_and_actor_verbatim | The shipped set workflow verifies drafts in batch and repeats one prospective function hash. |
| A022 | README.md:91-92 | Run `compile` periodically with a scheduler of your choice. It creates drafts and never verifies or promotes them automatically. | TRUE | T:test_supervised_miss_to_exact_artifact_hit | Batch verification and set promotion remain explicit operator actions. |
| A023 | README.md:96-116 | ```python from cement_runtime import Candidate, CompilePolicy, System class ProviderAdapter: def propose(self, request): # Call an LLM here; provenance should identify model/prompt/tool revisions. return Candidate( output={"kind": … | SCOPE | S:system-handle; S:candidate-source-protocol | The bundled invocation and inline request lifecycle belong to M3. |
| A024 | README.md:118-120 | Put every fact that can change the answer into the JSON input, including identity, locale, permissions, time, external-state revision, and policy revision. Cement cannot compile … | TRUE | T:test_unknown_input_returns_no_match | Exact canonical input is the complete dispatch key inside one scope. |
| A025 | README.md:124 | `handle` and `request` return explicit states: | SCOPE | S:outcome-type | The six-state inline request lifecycle belongs to M3. |
| A026 | README.md:126 | \| Status \| Meaning \| Caller action \| | TRUE | S:outcome-type | Formatting row; the model union supplies the listed status vocabulary. |
| A027 | README.md:127 | \|---\|---\|---\| | TRUE | N/A:format | Formatting only; it carries no product claim. |
| A028 | README.md:128 | \| `resolved` \| Current promoted artifact or still-valid confirmed fixture produced the output. \| Re-run live authorization/policy. Then apply the plan idempotently. \| | SCOPE | T:test_supervised_miss_to_exact_artifact_hit | The status is correct, but the inline request outcome belongs to M3. |
| A029 | README.md:129 | \| `review_required` \| A hidden candidate awaits supervision. \| Inspect the named proposal on the separate review surface. \| | SCOPE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | The status is correct, but the inline request outcome belongs to M3. |
| A030 | README.md:130 | \| `in_progress` \| This partition's generation lease is active. \| Poll `request REQUEST_ID`. While the lease is active, the input needs no resubmission. \| | SCOPE | T:test_concurrent_retry_observes_generation_lease | The lease and polling path belong to M3. |
| A031 | README.md:131 | \| `fallback_failed` \| The candidate source failed, or its generation lease expired, and Cement stored no output. \| For a stored source failure, retry `handle` … | SCOPE | T:test_timeout_and_invalid_response_are_inert_failures; T:test_concurrent_retry_observes_generation_lease | The candidate-source failure and lease lifecycle belong to M3. |
| A032 | README.md:132 | \| `rejected` \| A supervisor rejected the proposal. \| Use a new request ID to request another candidate. \| | SCOPE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | The request/proposal lifecycle belongs to M3. |
| A033 | README.md:133 | \| `reconciliation_required` \| A previously returned source lost validity through revocation, suspension, a failed integrity check, or an obsolete operation revision. Cement returns no cached … | SCOPE | T:test_quarantined_artifact_cannot_replay_an_old_idempotency_key; T:test_operation_revision_retires_old_artifacts | The reconciliation request state belongs to M3. |
| A034 | README.md:135-138 | Replaying a request ID is content-idempotent. It does not promise to replay an unsafe old output. Quarantine or an explicit operation revision can move a … | SCOPE | T:test_request_idempotency_and_partition_isolation; T:test_operation_revision_retires_old_artifacts | The inline request lifecycle belongs to M3. |
| A035 | README.md:140-143 | `cement-json-v1` accepts null, booleans, strings, signed 64-bit integers, arrays, and string-keyed objects. It rejects decimal and exponent numbers. Encode domain decimals as strings with a … | TRUE | T:test_object_order_is_erased_but_number_and_unicode_semantics_are_conservative; T:test_limit_configuration_requires_exact_integers | The canonicalizer and parser enforce the stated domain and bounds. |
| A036 | README.md:145-150 | Proposal and report feeds plus example and artifact insertion catalogs carry monotonic `sequence` values. To page them, pass the last observed value to `--after-sequence`. Example … | INCOMPLETE | T:test_function_receipts_enumerates_newest_first; T:test_usage_errors_and_oversized_stdin_are_machine_readable | M2 adds descending function-receipt pagination and exit 6 negative verdicts, neither described here. |
| A037 | README.md:152-154 | Read [docs/adapter-protocol.md](docs/adapter-protocol.md) for the command adapter protocol. Read [docs/architecture.md](docs/architecture.md) and [docs/threat-model.md](docs/threat-model.md) for the full state model and trust boundaries. | TRUE | N/A:links | All three committed targets exist. |
| A038 | README.md:158-159 | [Hospital OCR layout-learning](examples/hospital_ocr/README.md) - offline walkthrough of supervised per-layout extraction plans becoming deterministic reuse. | INCOMPLETE | T:test_every_document_in_one_layout_has_a_byte_identical_signature; T:test_function_eval_never_reaches_the_ledger_globals | It demonstrates per-artifact reuse but not the aggregate exportable function that M2 ships. |
| A039 | README.md:163-166 | ```bash uv run python -m unittest discover -s tests -v uv build ``` | FALSE | S:configured-gate | The configured gate is `uv run python -m unittest discover -s tests -t .`; the README substitutes `-v` and omits `-t .`. |
| A040 | README.md:168-169 | The project has no runtime package dependencies. It uses `uv_build` only to produce the wheel and source distribution. | TRUE | S:pyproject-dependencies; S:pyproject-build-backend | pyproject.toml declares an empty dependency list and uv_build backend. |
| A041 | README.md:173-177 | This release is a local control plane, not a network service or an ACL system. A new database starts with mode `0600`, but evidence is … | INCOMPLETE | T:test_function_export_out_keeps_mode_0600_under_a_permissive_umask; T:test_function_eval_opens_no_store_or_connection | A portable plaintext bundle is now a second deployment object and can execute without the ledger or authority callback. |
| A042 | README.md:179-186 | The callback gates operation registration/revision, proposal review, compilation, verification, promotion, challenge, evidence revocation, and artifact suspension. `handle` and read APIs assume the embedding service has … | SCOPE | T:test_authority_denial_precedes_control_plane_mutation; T:test_detached_descendants_are_killed_and_reaped | The callback, request lifecycle, and bundled command-adapter containment all belong to M3. |

## Section B — docs/architecture.md

| id | file:line | verbatim claim (elide past 25 words with …) | verdict | evidence anchor | note |
|---|---|---|---|---|---|
| B001 | docs/architecture.md:5 | Cement is a pure decision-plan router plus a local control plane: | INCOMPLETE | T:test_function_eval_never_reaches_the_ledger_globals | M2 also ships a portable capability-free function document and ledger-free evaluator. |
| B002 | docs/architecture.md:7-8 | 1. Canonicalize bounded JSON with `cement-json-v1`. It uses signed 64-bit integers and string decimal quantities, so binary-float rounding cannot widen an exact scope. | TRUE | T:test_object_order_is_erased_but_number_and_unicode_semantics_are_conservative | The canonicalizer preserves this exact numeric boundary. |
| B003 | docs/architecture.md:9-10 | 2. Resolve only one integrity-valid promoted artifact whose partition, operation revision, and exact canonical input all match. | TRUE | T:test_supervised_miss_to_exact_artifact_hit; T:test_unknown_input_returns_no_match | System.handle still dispatches only an exact current artifact. |
| B004 | docs/architecture.md:11-12 | 3. Otherwise reserve the idempotent request, call the candidate source outside the SQLite transaction, and store a pending proposal. | SCOPE | T:test_concurrent_retry_observes_generation_lease | The inline request and candidate-generation machinery belongs to M3. |
| B005 | docs/architecture.md:13-14 | 4. A separate review action accepts, corrects, or rejects the candidate. Accept/correct creates an immutable replay fixture; reject remains audit evidence only. | SCOPE | T:test_correction_is_the_fixture_and_conflicts_block_compilation | The supervision principle remains, but this request/proposal mechanism belongs to M3. |
| B006 | docs/architecture.md:15-16 | 5. A scheduled compiler groups active fixtures by exact scope. It requires the operation's configured support, distinct-reviewer, time-span, and zero-conflict gates. | TRUE | T:test_correction_is_the_fixture_and_conflicts_block_compilation; T:test_verification_recomputes_build_stability_metadata | The per-scope compiler contract remains active. |
| B007 | docs/architecture.md:17-18 | 6. The compiler emits `cement-exact-lookup-v1`, a capability-free JSON document with only `exact` and `return` operations. | INCOMPLETE | T:test_function_v1_document_is_explicitly_rejected; T:test_entry_reordering_keeps_one_hash_and_canonical_document | M2 additionally builds the aggregate cement-function-v2 document from verified exact entries. |
| B008 | docs/architecture.md:19-20 | 7. Verification binds artifact, policy, runtime/canonicalizer ABI, and the complete evidence snapshot. It replays the finite scope and negative boundaries into a sealed, content-addressed test … | INCOMPLETE | T:test_function_verification_matches_independent_scoped_membership | M2 adds six ordered promoted-set checks and a whole-function hash over the committed snapshot. |
| B009 | docs/architecture.md:21-23 | 8. Promotion explicitly repeats the tested scope hash and rechecks every binding in one immediate transaction. Its activation receipt binds the artifact, policy, evidence, report … | INCOMPLETE | T:test_promote_function_persists_receipt_memberships_and_projected_event | M2 adds atomic whole-set promotion, one repeated function hash, ordered memberships, and an immutable function receipt. |
| B010 | docs/architecture.md:25-26 | The LLM proposes instance behavior. It never chooses scope, confirms examples, runs verification, or activates artifacts. | TRUE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | All governance remains outside candidate output. |
| B011 | docs/architecture.md:30 | Scope identity is: | TRUE | T:test_audit_events_and_learning_are_partition_exact | The tuple remains the exact per-entry scope. |
| B012 | docs/architecture.md:32-34 | ```text (partition, operation, operation_revision, canonical_input) ``` | TRUE | T:test_function_verification_matches_independent_scoped_membership | Each function entry preserves the same exact scope dimensions. |
| B013 | docs/architecture.md:36-42 | `partition` is mandatory to prevent accidental cross-tenant/workflow learning. Every explicit operation revision retires prior builds, including a revision that keeps the same numeric thresholds. Request … | SCOPE | T:test_operation_revision_retires_old_artifacts; T:test_request_idempotency_and_partition_isolation | Revisioned artifact scope remains, but the request invalidation lifecycle belongs to M3. |
| B014 | docs/architecture.md:44-46 | Confirmed receipt data and artifact evidence edges are immutable. Revocation is a separate tombstone; it suspends every non-retired dependent build. Artifact suspension and retirement are … | FALSE | T:test_reconstruct_function_receipt_survives_middle_member_supersession_and_p6_selects_latest; T:test_reconstruct_function_receipt_survives_operation_revision_retirement_and_p6_ignores_prior_revision; T:test_reconstruct_function_receipt_survives_revocation_of_every_member_evidence_row | Contradiction: historical function receipts reconstruct byte-identically after supersession, revision retirement, and evidence revocation. Only legacy artifact-receipt replay lacks a public reconstruction surface. |
| B015 | docs/architecture.md:50-53 | A scope is recurring when it has enough distinct, idempotent confirmations. It is stable when those confirmations span the configured observation interval without conflicting final … | INCOMPLETE | T:test_function_verification_pass_is_read_only_and_authority_free | The definitions remain true per entry, but M2 also verifies the aggregate promoted-set snapshot. |
| B016 | docs/architecture.md:55-57 | These are operational gates, not proof that supervisors were correct. Exact matching makes the coverage claim honest: the artifact's match set contains one canonical value. … | TRUE | T:test_unknown_input_returns_no_match | The function layer aggregates exact entries without widening any entry predicate; wider projection remains M4. |
| B017 | docs/architecture.md:61-64 | SQLite uses foreign keys, STRICT tables, rollback journaling, `synchronous=EXTRA`, a busy timeout, defensive connection configuration when available, and explicit `BEGIN IMMEDIATE` write transitions. Candidate generation … | SCOPE | T:test_concurrent_retry_observes_generation_lease | SQLite durability remains, but candidate generation and lease recovery belong to M3. |
| B018 | docs/architecture.md:66-78 | Initialization adopts only a schema-empty SQLite database. It creates the schema atomically and runs SQLite integrity and foreign-key checks. It then validates the database metadata … | INCOMPLETE | T:test_function_promotion_schema_v2_is_reference_only_and_immutable | The immutable list and schema description omit schema v2 function_receipts and function_memberships. |
| B019 | docs/architecture.md:80-82 | The database file is the integrity and confidentiality trust root in this release. Cement content-addresses artifact content, policies, receipts, snapshots, scopes, and builds, so accidental … | FALSE | T:test_function_eval_opens_no_store_or_connection; T:test_function_export_round_trips_through_parse_function | Contradiction: an exported bundle can be evaluated without the database, and an independently held function hash can bind its identity. Neither mechanism proves origin. |
| B020 | docs/architecture.md:86-90 | The runtime uses Python 3.11+ and the standard-library `sqlite3`, JSON, subprocess, typing, and unittest modules. This exact-lookup envelope needs no expression engine or provider SDK. … | FALSE | S:function-module-imports; S:runtime-source-tree | The runtime does not import unittest, and M2 adds bisect and dataclasses among other omitted standard-library modules. The dependency conclusion remains true. |
| B021 | docs/architecture.md:92-96 | Packaging uses the pure-Python [`uv_build` backend](https://docs.astral.sh/uv/concepts/build-backend/). The backend validates the `src/` layout, and `pyproject.toml` bounds its version. There are zero runtime package dependencies. SQLite's own … | TRUE | S:pyproject-build-backend; S:pyproject-dependencies; S:store-schema-version | The package and store configuration match. |
| B022 | docs/architecture.md:98-101 | The project evaluated Go plus CEL for future generalized artifacts. CEL offers a constrained expression runtime, and Go offers a single binary. It is unnecessary … | UNPINNED | N/A:no-committed-test | No committed test or executable decision record decides the historical evaluation claim. |

## Section C — docs/threat-model.md

| id | file:line | verbatim claim (elide past 25 words with …) | verdict | evidence anchor | note |
|---|---|---|---|---|---|
| C001 | docs/threat-model.md:5-6 | - The host, Python/SQLite runtime, database file permissions, Cement interpreter, and deployment's authority callback or external access control. | INCOMPLETE | T:test_function_eval_never_reaches_the_ledger_globals | Offline evaluation trusts a bundle plus optional independently held function hash and needs no database or authority callback. |
| C002 | docs/threat-model.md:7-8 | - Supervisors and release managers only within the authority and context represented by their partition. The CLI records identity strings but does not authenticate them. | SCOPE | T:test_authority_requires_the_exact_boolean_true | The authority callback belongs to M3. |
| C003 | docs/threat-model.md:9 | - The provider adapter process as a credential-bearing transport. Its model output remains untrusted. | SCOPE | T:test_json_protocol_and_provenance_binding | The bundled command-adapter runtime belongs to M3. |
| C004 | docs/threat-model.md:13 | - Request JSON, including prompt injection. | TRUE | T:test_object_order_is_erased_but_number_and_unicode_semantics_are_conservative | All incoming JSON is parsed and bounded before use. |
| C005 | docs/threat-model.md:14 | - LLM candidate output and self-reported provenance. | TRUE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence | Candidate content cannot enter deterministic evidence before review. |
| C006 | docs/threat-model.md:15 | - Stored input/output content when rendered by another system. | TRUE | T:test_proposal_content_hashes_fail_closed_on_storage_mutation | Cement validates storage integrity but does not make rendered content safe. |
| C007 | docs/threat-model.md:16 | - Frequency by itself, reviewer labels without deployment authentication, and any inferred scope. | TRUE | T:test_correction_is_the_fixture_and_conflicts_block_compilation; T:test_authority_requires_the_exact_boolean_true | Recurrence does not override conflicts or authenticate identity. |
| C008 | docs/threat-model.md:20-22 | - Strict bounded JSON; duplicate keys, decimal/non-finite numbers, non-string keys, deep/large containers, and signed-64-bit overflow fail closed. Decimal quantities use application-defined strings. Cement preserves Unicode … | TRUE | T:test_object_order_is_erased_but_number_and_unicode_semantics_are_conservative; T:test_limit_configuration_requires_exact_integers | The parser and canonicalizer enforce these controls. |
| C009 | docs/threat-model.md:23-24 | - Partition, operation revision, and byte-stable canonical equality control scope. Unknown or near-match input falls back. | INCOMPLETE | T:test_unknown_input_returns_no_match; T:test_function_eval_miss_is_exit_six_with_the_same_identity | System.handle falls back, while offline function evaluation returns an inert matched=false verdict and invokes no fallback. |
| C010 | docs/threat-model.md:25-26 | - Artifacts are inert data: no code, templates, loops, filesystem, process, network, environment, clock, randomness, or external effects. | TRUE | S:artifact-validator; S:function-module-doc | Both exact artifacts and function bundles contain only bounded JSON data. |
| C011 | docs/threat-model.md:27-31 | - Candidate commands bypass the shell, have timeout/output limits, and run outside database locks. On Linux, a child-subreaper kills and reaps detached descendants before accepting … | SCOPE | T:test_detached_descendants_are_killed_and_reaped; T:test_outer_watchdog_kills_adapter_if_supervisor_dies | The bundled command-adapter containment belongs to M3. |
| C012 | docs/threat-model.md:32-33 | - Proposed output is visible only through the review API. Accepted output can differ, and the final edited value is the fixture. | TRUE | T:test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence; T:test_correction_is_the_fixture_and_conflicts_block_compilation | The supervision boundary remains enforced. |
| C013 | docs/threat-model.md:34-35 | - Evidence conflicts block compilation. Evidence snapshots and policy/artifact digests block stale verification and promotion. | INCOMPLETE | T:test_function_verification_matches_independent_scoped_membership; T:test_promote_function_persists_receipt_memberships_and_projected_event | M2 adds whole-set verification, one prospective hash, and a persisted function-receipt check. |
| C014 | docs/threat-model.md:36 | - Counterexample, revocation, ambiguity, and integrity failure quarantine builds. | TRUE | T:test_counterexample_and_revocation_quarantine; T:test_runtime_integrity_failure_quarantines_then_falls_back | Artifact quarantine remains fail-closed. |
| C015 | docs/threat-model.md:40-41 | - Authenticate and authorize proposal review, operation revision, promotion, challenge, revocation, suspension, database access, and audit access. | SCOPE | T:test_authority_denial_precedes_control_plane_mutation | The embedded authority callback belongs to M3; deployment authorization remains external. |
| C016 | docs/threat-model.md:42-43 | - Put every mutable answer dependency into the input, including identity, permissions, locale, policy revision, and external-state revision. Exclude behavior with hidden context from compilation. | TRUE | T:test_unknown_input_returns_no_match | The exact canonical key cannot safely include unstated context; projection remains M4. |
| C017 | docs/threat-model.md:44-45 | - Minimize, redact, encrypt, expire, and back up evidence according to its data classification. The ledger is plaintext and a blind copy of a live … | INCOMPLETE | T:test_function_export_writes_the_live_document_bytes_exactly | Exported function bundles also contain plaintext inputs and outputs and need the same handling policy. |
| C018 | docs/threat-model.md:46-47 | - Treat results as plans. Re-run live policy and authorization immediately before an effect. Use the request ID as an idempotency key. Stop for reconciliation … | SCOPE | T:test_quarantined_artifact_cannot_replay_an_old_idempotency_key | The request-ID and reconciliation lifecycle belongs to M3; plan-only output remains a deployment rule. |
| C019 | docs/threat-model.md:48 | - Keep provider wrappers pure. Model calls can repeat after timeout or lease recovery. | SCOPE | T:test_timeout_and_invalid_response_are_inert_failures; T:test_concurrent_retry_observes_generation_lease | The bundled invocation and lease machinery belongs to M3. |
| C020 | docs/threat-model.md:49-50 | - Monitor promoted scopes. When policy or expected behavior changes, challenge them. Revise the operation instead of overwriting contradictory history. | TRUE | T:test_late_review_counterexample_quarantines_promoted_scope; T:test_operation_revision_retires_old_artifacts | The challenge and semantic-revision controls remain active. |
| C021 | docs/threat-model.md:51-52 | - Deploy command adapters on Linux. If crash-resilient process-tree containment is required, add an external cgroup/job/container boundary on every platform. | SCOPE | T:test_detached_descendants_are_killed_and_reaped | The bundled command-adapter runtime belongs to M3. |
| C022 | docs/threat-model.md:53 | - If the database-file trust root is insufficient, protect or sign exported artifacts. | INCOMPLETE | T:test_function_export_round_trips_through_parse_function; T:test_function_eval_forwards_the_expected_hash_unvalidated | M2 defines an official bundle with embedded self-hash and optional caller-held expected hash, but neither establishes origin or signature. |
| C023 | docs/threat-model.md:57 | This local release excludes: | TRUE | S:runtime-source-tree | The following absences remain visible in the shipped code and schema. |
| C024 | docs/threat-model.md:59 | - Remote API and authentication. | TRUE | S:cli-parser-root | The shipped surface is a local library and CLI; no network server or authenticator exists. |
| C025 | docs/threat-model.md:60 | - Encryption and key erasure. | TRUE | S:store-schema | Ledger and bundle content are plaintext, and no key-management surface exists. |
| C026 | docs/threat-model.md:61 | - External signatures. | TRUE | S:function-validate-docstring | Function hashes provide integrity binding only and explicitly do not prove origin. |
| C027 | docs/threat-model.md:62 | - Arbitrary code sandboxing. | TRUE | T:test_detached_descendants_are_killed_and_reaped | Process cleanup is lifecycle containment for a trusted executable, not a sandbox. |
| C028 | docs/threat-model.md:63 | - Generalized-rule synthesis. | TRUE | S:artifact-validator; S:function-abi | Both shipped formats remain finite exact lookup data. |
| C029 | docs/threat-model.md:64 | - Domain schemas and oracles. | SCOPE | S:runtime-source-tree | Projection verification and domain contracts belong to M4. |
| C030 | docs/threat-model.md:65 | - Active shadow sampling. | TRUE | S:runtime-source-tree | No sampler or production drift telemetry surface exists. |
| C031 | docs/threat-model.md:66 | - Quotas across principals. | TRUE | S:store-schema | The schema contains no principal quota model. |
| C032 | docs/threat-model.md:67 | - Distributed consensus. | TRUE | S:store-module-doc | The runtime is a local SQLite control plane. |
| C033 | docs/threat-model.md:69 | The exact artifact format leaves those gaps visible. It does not imply that Cement solves them. | INCOMPLETE | S:function-abi; S:artifact-abi | M2 now has two exact formats, cement-exact-lookup-v1 and cement-function-v2; the singular wording hides the aggregate bundle. |

## Section D — docs/adapter-protocol.md

| id | file:line | verbatim claim (elide past 25 words with …) | verdict | evidence anchor | note |
|---|---|---|---|---|---|
| D001 | docs/adapter-protocol.md:3-4 | `CommandCandidateSource` invokes a trusted executable directly with `shell=False`. Cement writes one compact JSON object to stdin: | SCOPE | T:test_json_protocol_and_provenance_binding | The bundled command-adapter runtime belongs to M3. |
| D002 | docs/adapter-protocol.md:6-15 | ```json { "input": {"domain": "value"}, "operation": "support.reply", "operation_revision": 1, "partition": "tenant-42", "protocol": "cement-candidate-v1", "request_id": "ticket-123" } ``` | SCOPE | T:test_json_protocol_and_provenance_binding | The protocol is accurate but belongs to the M3 adapter surface. |
| D003 | docs/adapter-protocol.md:17 | The command writes exactly one JSON object to stdout: | SCOPE | T:test_json_protocol_and_provenance_binding | The protocol is accurate but belongs to the M3 adapter surface. |
| D004 | docs/adapter-protocol.md:19-29 | ```json { "output": {"kind": "reply", "text": "Candidate answer"}, "provenance": { "model": "provider/model", "model_revision": "provider revision when available", "prompt_revision": "content digest", "tools": [] } } ``` | SCOPE | T:test_json_protocol_and_provenance_binding | The protocol is accurate but belongs to the M3 adapter surface. |
| D005 | docs/adapter-protocol.md:31-36 | The response must contain both fields. Additional top-level fields fail closed. Cement bounds the output. It rejects duplicate object keys, decimal/exponent and non-finite numbers, signed-64-bit … | SCOPE | T:test_nonzero_stderr_is_not_reflected; T:test_timeout_and_invalid_response_are_inert_failures; T:test_stdout_and_stderr_are_stream_bounded | The adapter failure and request outcome surface belongs to M3. |
| D006 | docs/adapter-protocol.md:38-47 | On Linux with `/proc`, Cement launches the adapter beneath a private child-subreaper. The supervisor enforces the primary timeout and the stdout/stderr limits. It terminates the … | SCOPE | T:test_detached_descendants_are_killed_and_reaped; T:test_outer_watchdog_kills_adapter_if_supervisor_dies | The bundled command-adapter containment belongs to M3. |
| D007 | docs/adapter-protocol.md:49-52 | The adapter receives no stored examples and cannot verify or promote its own proposal. Treat all request fields as untrusted prompt content. Keep system instructions … | SCOPE | T:test_json_protocol_and_provenance_binding; S:command-candidate-source | The command-adapter runtime belongs to M3. |
| D008 | docs/adapter-protocol.md:54-57 | Cement can invoke the adapter again after a failed request or an expired generation lease. Provider calls must create no external effects. `request_id` is partition-local … | SCOPE | T:test_timeout_and_invalid_response_are_inert_failures; T:test_request_idempotency_and_partition_isolation | The invocation retry and request-ID machinery belongs to M3. |

## Section E — examples/hospital_ocr/README.md

| id | file:line | verbatim claim (elide past 25 words with …) | verdict | evidence anchor | note |
|---|---|---|---|---|---|
| E001 | examples/hospital_ocr/README.md:3 | Hospital document layouts often lead to a new throwaway LLM extraction script for each run. This offline example turns that per-layout work into a durable … | INCOMPLETE | T:test_every_document_in_one_layout_has_a_byte_identical_signature; T:test_propose_is_byte_deterministic_for_output_and_provenance | It demonstrates per-artifact reuse but not M2 aggregate export and ledger-free evaluation. |
| E002 | examples/hospital_ocr/README.md:7 | Cement does not learn a parser or generalize across layouts. It resolves one integrity-valid promoted artifact for an exact `(partition, operation, operation revision, canonical input)` … | TRUE | T:test_every_document_in_one_layout_has_a_byte_identical_signature; T:test_signatures_exclude_all_real_patient_values | The signature tests prove patient variation is excluded. |
| E003 | examples/hospital_ocr/README.md:9 | After promotion, a known patient-independent signature returns its confirmed extraction plan without calling the proposal adapter or an LLM. A genuinely new or changed layout … | TRUE | T:test_drifted_known_layout_falls_back_to_applicable_best_effort_plan; T:test_supervised_miss_to_exact_artifact_hit | The example and runtime retain exact-layout isolation. |
| E004 | examples/hospital_ocr/README.md:11 | The example parser recognizes only its explicit block grammar and fails closed otherwise. A known signature never certifies extraction correctness. | TRUE | T:test_unrecognized_block_shape_fails_closed; T:test_duplicate_section_heading_is_rejected_rather_than_guessed | Parser structure and semantic correctness remain separate. |
| E005 | examples/hospital_ocr/README.md:13 | Cement guarantees deterministic plan return only inside that exact valid scope. It does not guarantee that the plan extracts every future document correctly, or that … | TRUE | T:test_unknown_input_returns_no_match; T:test_known_layout_plans_match_reference_extraction_for_each_layout | The runtime guarantees dispatch, while the example separately tests its reference plans. |
| E006 | examples/hospital_ocr/README.md:19-24 | ``` ocr(path) -> layout_signature(ocr_text) -> System.handle(...) promoted exact signature -> confirmed plan miss -> PlanProposer.propose(...) -> supervisor review confirmed plan + ocr_text -> apply_plan(...) -> … | INCOMPLETE | T:test_every_document_in_one_layout_has_a_byte_identical_signature; T:test_reference_plans_extract_complete_expected_objects | The diagram omits export of the aggregate function and evaluation after the ledger and adapter are gone. |
| E007 | examples/hospital_ocr/README.md:26 | `pipeline.py` supplies the deterministic document path: | TRUE | S:hospital-pipeline-module | The module owns OCR normalization, signatures, and plan application. |
| E008 | examples/hospital_ocr/README.md:28 | 1. `ocr(path)` reads simulated OCR text and normalizes line endings and blank lines. | TRUE | S:hospital-ocr-function | The implementation performs these transformations. |
| E009 | examples/hospital_ocr/README.md:29 | 2. `layout_signature(ocr_text)` records the document type plus one ordered list of label and section keys. It uses block position, not the presence of filled values. … | TRUE | T:test_patient_colon_prose_does_not_change_or_leak_into_signature; T:test_signatures_exclude_all_real_patient_values | Committed tests cover the exclusion and ordering boundary. |
| E010 | examples/hospital_ocr/README.md:30 | 3. `System.handle(...)` either returns the promoted exact-scope plan or asks `PlanProposer.propose(...)` for a supervised candidate. | TRUE | T:test_supervised_miss_to_exact_artifact_hit | The example uses the same runtime dispatch contract. |
| E011 | examples/hospital_ocr/README.md:31 | 4. `apply_plan(plan, ocr_text)` applies label and section locators and returns extracted strings. | TRUE | T:test_reference_plans_extract_complete_expected_objects; T:test_section_locators_keep_colon_lines_and_stop_before_field_blocks | The locator behavior is committed-test pinned. |
| E012 | examples/hospital_ocr/README.md:33 | `plan_adapter.py` defines `PlanProposer`, a `cement_runtime.CandidateSource`-compatible deterministic stand-in for a production provider adapter. It deliberately does not call an LLM. `run_demo.py` drives review, compilation, verification, promotion, … | INCOMPLETE | T:test_propose_is_byte_deterministic_for_output_and_provenance; S:hospital-run-demo | The driver stops before function verification, export, and ledger-free evaluation. |
| E013 | examples/hospital_ocr/README.md:37 | - Partition: `mercy-general` - learning remains isolated to this hospital. | TRUE | S:hospital-run-demo-partition | The driver uses the stated partition for every runtime action. |
| E014 | examples/hospital_ocr/README.md:38 | - Operation: `document.extraction_plan` - all layouts use one operation; each distinct signature is a separate canonical input and exact scope. | TRUE | T:test_every_document_in_one_layout_has_a_byte_identical_signature; T:test_moving_a_label_into_a_section_changes_the_signature | Structural changes produce distinct exact keys. |
| E015 | examples/hospital_ocr/README.md:39 | - Demo compile policy: `CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)`. | TRUE | S:hospital-run-demo-policy | The driver constructs CompilePolicy with these values. |
| E016 | examples/hospital_ocr/README.md:40 | - Reviewer: `records-supervisor`. | TRUE | S:hospital-run-demo-reviewer | The driver uses this identity for each review. |
| E017 | examples/hospital_ocr/README.md:41 | - Promoter: `informatics-lead`. | TRUE | S:hospital-run-demo-promoter | The driver uses this identity for artifact promotion. |
| E018 | examples/hospital_ocr/README.md:42 | - Corpus: seven files - layout A has three progress notes, layout B has two intake forms, and layout C has two lab slips. | TRUE | S:hospital-document-corpus | The committed corpus has the stated distribution. |
| E019 | examples/hospital_ocr/README.md:44 | Production defaults are stricter: three confirmations, two reviewers, and a seven-day observation span. | TRUE | S:compile-policy-defaults | CompilePolicy defines these exact defaults. |
| E020 | examples/hospital_ocr/README.md:48 | Generated by `layout_signature(ocr(layout_a_progress_note_01.txt))`: | TRUE | T:test_every_document_in_one_layout_has_a_byte_identical_signature | The fixture generates the same patient-free layout-A structure. |
| E021 | examples/hospital_ocr/README.md:50-88 | ```json { "document_type": "physician_progress_note", "structure": [ { "kind": "label", "key": "Patient" }, { "kind": "label", "key": "MRN" }, { "kind": "label", "key": "Date" }, { … | TRUE | T:test_every_document_in_one_layout_has_a_byte_identical_signature; T:test_signatures_exclude_all_real_patient_values | The committed expected signature matches this structure and excludes values. |
| E022 | examples/hospital_ocr/README.md:92 | Generated by `reference_plan("physician_progress_note")`: | TRUE | T:test_reference_plans_extract_complete_expected_objects | The reference plan is exercised against the corpus. |
| E023 | examples/hospital_ocr/README.md:94-141 | ```json { "document_type": "physician_progress_note", "layout": "A", "fields": [ { "name": "patient_name", "locator": { "kind": "label", "label": "Patient" }, "value_type": "string" }, { "name": "mrn", "locator": … | TRUE | T:test_reference_plans_extract_complete_expected_objects | Those locators produce the committed expected patient objects. |
| E024 | examples/hospital_ocr/README.md:143 | Both objects obey `cement-json-v1`: null, booleans, strings, signed 64-bit integers, arrays, and string-keyed objects only. Decimal and exponent numbers are excluded. | TRUE | T:test_signatures_reference_plans_and_outputs_are_cement_json_v1 | The committed test canonicalizes all signatures, plans, and outputs. |
| E025 | examples/hospital_ocr/README.md:147 | Requirements match the repository: Python 3.11+, SQLite 3.37+, and the `uv` development workflow. From the repository root, after `uv sync`: | TRUE | S:pyproject-python; S:store-min-sqlite | Repository metadata and the store guard match. |
| E026 | examples/hospital_ocr/README.md:149-151 | ```bash uv run python examples/hospital_ocr/run_demo.py ``` | TRUE | LIVE:F | The exact command exited zero twice. |
| E027 | examples/hospital_ocr/README.md:153 | The driver uses the Python standard library plus `cement_runtime`, creates a temporary SQLite ledger, performs no network access, and exits zero with `All checks passed.` | UNPINNED | LIVE:F; S:hospital-run-demo | The live run confirms it, but no committed test executes the driver. |
| E028 | examples/hospital_ocr/README.md:157 | Act 1 shows two reviewed confirmations for layout A, then deterministic compilation, verification, and explicit promotion. Act 2 sends a third patient's document through the … | UNPINNED | LIVE:F | The live transcript matches, but no committed test decides this prose or sequence. |
| E029 | examples/hospital_ocr/README.md:159 | The demo generates the layout-A artifact ID per run. The block masks its 32-hex suffix as `art_<hex>`. Every other line is byte-stable. | UNPINNED | LIVE:F | Two live runs produced one distinct ID each and became byte-identical after one mask; no committed test pins it. |
| E030 | examples/hospital_ocr/README.md:161-212 | ```text Hospital OCR layout-learning demo (offline; no LLM or network). Cement receives patient-independent layout signatures and returns reviewed extraction plans; the deterministic pipeline applies each … | UNPINNED | LIVE:F | Both masked live diffs were empty; no committed test pins the block. |
| E031 | examples/hospital_ocr/README.md:216 | - Canonicalize before learning. The exact recurring input is an ordered layout structure with no patient values. Structural position determines the signature, not the presence … | TRUE | T:test_blank_label_value_keeps_the_same_structural_kind; T:test_signatures_exclude_all_real_patient_values | The regression tests pin both structural properties. |
| E032 | examples/hospital_ocr/README.md:217 | - Keep decimal quantities as strings. `cement-json-v1` rejects decimal and exponent numbers. Layout C marks `potassium` and `creatinine` as `decimal_string` and extracts values such as … | TRUE | T:test_signatures_reference_plans_and_outputs_are_cement_json_v1 | Layout C outputs decimal strings and canonicalize successfully. |
| E033 | examples/hospital_ocr/README.md:218 | - Treat layout drift as an explicit edge case. A changed layout is a new canonical input, enters supervised fallback, and solidifies through the same … | TRUE | T:test_drifted_known_layout_falls_back_to_applicable_best_effort_plan; T:test_moving_a_label_into_a_section_changes_the_signature | Changed structure produces a new exact key. |
| E034 | examples/hospital_ocr/README.md:219 | - Isolate learning by partition. `mercy-general` scopes this evidence and its promoted artifacts to one hospital. | TRUE | S:hospital-run-demo-partition | Every demo system call uses this partition. |
| E035 | examples/hospital_ocr/README.md:220 | - Keep demonstration policy visibly relaxed. Production defaults require more confirmations, more reviewers, and a real observation span. | TRUE | S:hospital-run-demo-policy; S:compile-policy-defaults | The driver and default model values differ exactly as stated. |
| E036 | examples/hospital_ocr/README.md:224 | - [Repository overview](../../README.md) | TRUE | N/A:link | The target exists. |
| E037 | examples/hospital_ocr/README.md:225 | - [Architecture](../../docs/architecture.md) - state model, exact-scope guarantees, and trust boundary | TRUE | N/A:link | The target exists and contains those sections, although its M2 claims need repair. |
| E038 | examples/hospital_ocr/README.md:226 | - [Candidate adapter protocol](../../docs/adapter-protocol.md) - candidate request, output, and failure contract | SCOPE | N/A:link | The target exists, but the bundled adapter surface belongs to M3. |
| E039 | examples/hospital_ocr/README.md:228 | Read `run_demo.py` for the lifecycle driver, `pipeline.py` for signature and extraction mechanics, and `plan_adapter.py` for the deterministic candidate source. | TRUE | S:hospital-run-demo; S:hospital-pipeline-module; S:hospital-plan-adapter | The three modules retain these roles. |

## Section F — Run the demo

- Exact command: `uv run python examples/hospital_ocr/run_demo.py`
- Run 1: exit 0; stderr empty; one `art_[0-9a-f]{32}` match; masked diff empty.
- Run 2: exit 0; stderr empty; one different `art_[0-9a-f]{32}` match; masked diff empty.
- Masked run-to-run diff: empty.
- Mask sufficiency: confirmed. Replacing `art_[0-9a-f]{32}` with `art_<hex>` made both runs byte-identical.
- Transcript verdict: accurate in the working tree, but `UNPINNED` because no committed test executes or compares the transcript.

Masked diff for each run:

```diff
```

## Section G — Gaps

| capability | destination file + section | why it belongs there | evidence anchor |
|---|---|---|---|
| A portable `cement-function-v2` document makes the promoted operation set one first-class object. | README.md — Guarantees; docs/architecture.md — Contract | This is the M2 object that gives the opening “function” a concrete referent. | T:test_entry_reordering_keeps_one_hash_and_canonical_document |
| Each entry carries full input/output plus artifact, evidence, report, and entry-seal governance digests. | docs/architecture.md — Contract | Readers need the exact content covered by whole-function identity. | T:test_function_verification_matches_independent_scoped_membership |
| Function identity is verified-content identity; `entry_seal` excludes promoter and promotion time while the ledger receipt retains them. | docs/architecture.md — Contract; Storage and transactions | This distinction explains pre-promotion hashing and keeps activation provenance separate. | T:test_entry_seal_timing_is_invariant_through_promotion_and_function_verify |
| Entry order is normalized by input hash, one embedded function hash binds content, and an independent expected hash binds caller-held identity. | README.md — Guarantees; docs/threat-model.md — Enforced controls | These are the portable document’s deterministic identity and trust rules. | T:test_entry_reordering_keeps_one_hash_and_canonical_document; T:test_function_eval_expected_hash_binds_caller_held_identity |
| The function format is bounded at 64 MiB, 50,000 entries, one million items, and depth 67. | docs/architecture.md — Contract; docs/threat-model.md — Enforced controls | The new attack and capacity surface needs explicit limits. | T:test_declared_limits_and_inclusive_document_boundaries; T:test_per_value_boundaries_and_depth_67_embedding |
| `verify_drafts` selects every current-build draft, reports superseded rows, and verifies the batch in one locked transaction. | README.md — Quick start; docs/architecture.md — Contract | This replaces one-artifact-at-a-time verification in the operator workflow. | T:test_verify_drafts_uses_shared_projection_and_one_locked_batch; T:test_verify_drafts_selects_current_middle_build_and_reports_skipped |
| `verify_function` is read-only and returns six ordered checks over one coherent promoted-set snapshot. | README.md — Guarantees; docs/architecture.md — Contract | This is the aggregate verification guarantee, distinct from artifact replay verification. | T:test_function_verification_pass_is_read_only_and_authority_free; T:test_function_verification_race_returns_one_coherent_snapshot |
| Function verification can bind an operator-held expected hash and detects set growth or drift. | README.md — Quick start; docs/architecture.md — Contract | Scripts can pin the exact committed set they intend to consume. | T:test_function_verification_expected_hash_detects_set_growth |
| `function inspect` deterministically previews retained members, verified candidates, replacements, skipped rows, and the prospective hash. | README.md — Quick start; docs/architecture.md — Contract | It is the inspectable source of the hash that set promotion requires. | T:test_function_promotion_manifest_is_deterministic_read_only_and_complete |
| `promote_function` atomically retires predecessors, activates candidates, and writes one set receipt plus ordered memberships. | README.md — Guarantees; docs/architecture.md — Contract | This is the whole-function activation transaction. | T:test_promote_function_persists_receipt_memberships_and_projected_event; T:test_promote_function_retires_three_predecessors_before_activation |
| Set promotion retains established entries during growth and permits a zero-candidate checkpoint over a nonempty retained set. | docs/architecture.md — Contract | Operators can add entries without dropping history and can restore a current receipt after legacy drift. | T:test_promote_function_growth_retains_the_complete_existing_set; T:test_promote_function_zero_candidate_checkpoints_legacy_set |
| Schema version 2 adds immutable reference-only `function_receipts` and `function_memberships` tables. | docs/architecture.md — Storage and transactions | The current immutable-record list and schema description omit both tables. | T:test_function_promotion_schema_v2_is_reference_only_and_immutable |
| The API exposes the latest current-revision receipt and paged receipt history across revisions. | README.md — Quick start; docs/architecture.md — Storage and transactions | Receipt discovery is required before historical show, export, or reconstruction. | T:test_function_receipts_enumerates_all_revisions_by_sequence_not_timestamp; T:test_function_receipts_cursor_is_exclusive_across_first_middle_and_last_pages |
| Historical receipt reconstruction is status-independent and survives supersession, revision retirement, and revocation of every member’s evidence. | docs/architecture.md — Isolation and revisioning; docs/threat-model.md — Enforced controls | This directly reverses the current “cannot replay” claim for function receipts. | T:test_reconstruct_function_receipt_survives_middle_member_supersession_and_p6_selects_latest; T:test_reconstruct_function_receipt_survives_operation_revision_retirement_and_p6_ignores_prior_revision; T:test_reconstruct_function_receipt_survives_revocation_of_every_member_evidence_row |
| The sixth set check requires the latest persisted receipt to bind the live promoted snapshot. | README.md — Guarantees; docs/architecture.md — Contract | Legacy per-artifact changes can leave individually valid artifacts without a valid set checkpoint. | T:test_verify_function_p6_nonempty_legacy_three_member_set_without_receipt_fails_only_p6 |
| `function_report` places immutable receipt membership beside current operation state without conflating the two anchors. | README.md — Guarantees; docs/architecture.md — Stability and verification claims | Readers need frozen membership and moving operational coverage in separate number spaces. | T:test_function_report_projects_both_anchors_with_exact_counts_and_ordering; T:test_function_report_keeps_historical_build_and_current_evidence_anchors_distinct |
| The current-state report counts ready and blocked scopes, pending proposals, artifact statuses, and stale-revision anomalies with bounded detail. | README.md — Quick start; docs/architecture.md — Stability and verification claims | This is the shipped coverage and gap report. | T:test_function_report_reaches_every_compiler_block_reason_through_public_apis; T:test_function_report_pending_count_reaches_the_10001_tail_with_bounded_detail; T:test_function_report_stale_anomalies_cover_three_active_statuses_at_revision_ten |
| The CLI `function` group has eight leaves: show, receipts, verify-drafts, verify, inspect, promote, export, and eval. | README.md — Quick start | No human-facing surface currently tells operators that the group exists. | S:cli-function-parser |
| `function show` can anchor to the current receipt or one historical receipt and exposes truncation through exact counts. | README.md — Quick start | It is the CLI coverage and receipt-inspection surface. | T:test_function_show_without_receipt_reports_current_anchor_only; T:test_function_show_receipt_id_reaches_a_superseded_revision; T:test_function_show_projection_limit_truncates_visibly |
| Exit 6 means a function command completed correctly but returned a negative verdict; payload channel depends on the leaf. | README.md — Request outcomes | Scripts need the new status class and its stdout-versus-stderr rules. | T:test_function_verdicts_preserve_the_symbol_qualified_exit_map; T:test_function_eval_exit_six_names_the_miss_and_nothing_else |
| `function export` emits exact UTF-8 bundle bytes for a passing live set or an immutable historical receipt. | README.md — Quick start; docs/architecture.md — Contract | This is the portable handoff from the ledger control plane. | T:test_function_export_writes_the_live_document_bytes_exactly; T:test_function_export_exports_one_historical_receipt |
| `function export --out` writes atomically through a mode-0600 temporary file and refuses non-regular destinations. | README.md — Deployment boundary; docs/threat-model.md — Enforced controls | The file channel adds concrete filesystem and confidentiality behavior. | T:test_function_export_out_never_exposes_a_partial_destination; T:test_function_export_out_keeps_mode_0600_under_a_permissive_umask; T:test_function_export_out_rejects_unusable_destinations |
| Live export refuses a drifted set, emits no bundle bytes, and reports the complete failed check vector on stderr. | README.md — Quick start; docs/threat-model.md — Enforced controls | A redirect must never receive verdict JSON in place of a bundle. | T:test_function_export_refuses_a_drifted_set_with_the_whole_check_vector |
| `function eval` parses and evaluates a bundle without constructing `System`, opening SQLite, calling an adapter, or invoking an LLM. | README.md — Deployment boundary; docs/architecture.md — Contract | This is the ledger-free deterministic runtime that changes the deployment boundary. | T:test_function_eval_never_reaches_the_ledger_globals; T:test_function_eval_opens_no_store_or_connection |
| Offline evaluation canonicalizes the input, returns an inert miss, and reports matched, output, artifact hash, and function hash. | README.md — Quick start; docs/architecture.md — Contract | Consumers need exact hit/miss semantics and answer provenance. | T:test_function_eval_lookup_is_canonical_not_textual; T:test_function_eval_payload_covers_every_match_field; T:test_function_eval_miss_is_exit_six_with_the_same_identity |
| The bundle reader requires strict UTF-8 regular-file input and enforces the 64 MiB bound independently from the 1 MiB evaluation input bound. | README.md — Deployment boundary; docs/threat-model.md — Enforced controls | The offline file channel has different bounds and object-identity rules from stdin JSON. | T:test_function_eval_requires_a_regular_file; T:test_function_eval_bundle_size_bound_is_an_adjacent_pair; T:test_function_eval_input_keeps_the_default_channel_bounds |
| An embedded hash proves normalized self-consistency; only an independently obtained expected hash binds identity; neither proves origin or signature. | docs/threat-model.md — Enforced controls; Deliberately absent | The current trust model names neither hash mode nor its limit. | T:test_function_eval_expected_hash_binds_caller_held_identity; S:function-validate-docstring |
| A bundle is plaintext and contains exact inputs, outputs, and governance digests. | README.md — Deployment boundary; docs/threat-model.md — Deployment obligations | Export creates a new data-classification, retention, and disclosure surface outside the ledger. | T:test_function_export_writes_the_live_document_bytes_exactly; S:function-entry-fields |
| Set promotion emits `function.promoted` with bounded ID projections while the membership table remains authoritative. | README.md — Request outcomes; docs/architecture.md — Storage and transactions | Event consumers need the new event kind and projection semantics. | T:test_promote_function_persists_receipt_memberships_and_projected_event |
| A historical receipt can be exported from a superseded operation revision. | README.md — Quick start; docs/architecture.md — Isolation and revisioning | Historical portability is stronger than current-revision inspection alone. | T:test_function_export_serves_a_receipt_from_a_superseded_revision |
| The Hospital OCR walkthrough can export the learned layout function and evaluate a known signature after deleting access to the ledger and adapter. | examples/hospital_ocr/README.md — Expected output; Teaching points | The example is the clearest end-to-end proof of portable deterministic reuse. | T:test_function_eval_never_reaches_the_ledger_globals; T:test_every_document_in_one_layout_has_a_byte_identical_signature |
| Historical member support and reviewer counts are frozen at build time, while active evidence and policy state remain current. | docs/architecture.md — Stability and verification claims | This prevents misleading complements or ratios across immutable and moving anchors. | T:test_function_report_keeps_historical_build_and_current_evidence_anchors_distinct |
| An empty promoted set verifies vacuously, exports a real empty function document, and evaluates every input as a miss. | README.md — Guarantees; docs/architecture.md — Contract | The zero-entry boundary is a supported function, not an error placeholder. | T:test_function_verification_empty_set_passes_vacuously; T:test_function_export_of_an_empty_promoted_set_exports_its_document; T:test_function_eval_answers_an_empty_exported_function |

## Section H — Internal consistency

| claim A | claim B | inconsistency | evidence anchor |
|---|---|---|---|
| README opening: a verified function is deterministic. | README guarantees and outcomes: revocation, suspension, or integrity failure can remove a prior result. | The docs never distinguish mutable ledger dispatch from the immutable exported bundle that makes the opening claim literal. | T:test_function_eval_never_reaches_the_ledger_globals; T:test_quarantined_artifact_cannot_replay_an_old_idempotency_key |
| README opening: one regular function covers many situations. | Architecture contract: the lifecycle produces one cement-exact-lookup-v1 artifact for one canonical input. | The aggregate referent is missing, so “function” alternates between one entry and the whole set. | T:test_entry_reordering_keeps_one_hash_and_canonical_document |
| Architecture: artifact suspension and retirement are terminal. | Architecture: therefore Cement cannot replay a historical promotion receipt. | The implication is invalid for immutable function receipts, whose reconstruction ignores member lifecycle status. | T:test_reconstruct_function_receipt_survives_middle_member_supersession_and_p6_selects_latest; T:test_reconstruct_function_receipt_survives_operation_revision_retirement_and_p6_ignores_prior_revision |
| Architecture: the database file is the release integrity trust root. | Threat model: deployments may protect or sign exported artifacts. | M2 makes the tension concrete: an exported bundle plus independent expected hash can execute without the database, but no doc defines that trust transfer. | T:test_function_eval_opens_no_store_or_connection; T:test_function_eval_expected_hash_binds_caller_held_identity |



---

# Part 2 — function-layer facts the new prose must match

Ordered check vector, CLI leaves with exit codes and the exit-6 bijection, the schema-v2 delta, the
guarantee ledger (positive and negative guarantees, each with the exact limit it must carry and its pin
status), and the ledger-free eval path. The five `DIVERGENCE —` rows in the guarantee ledger are
historical roadmap-ledger entries that later units already superseded; MAIN ruled them out of scope.

## S4 `verify_function` check vector

| Position | Check ID | Rejects | Pass proves | Pass does not prove | Empty-set behavior |
|---:|---|---|---|---|---|
| P1 | `duplicate-input-digests` | Two or more promoted rows with the same stored `input_hash`; aggregate overflow also forces a failed, unevaluated result. | Every promoted row in this snapshot has a unique stored input digest. | Canonical input validity, digest collision resistance, report validity, or projection correctness. | Passes: zero digests are unique. |
| P2 | `abi-canonicalizer-uniform` | An artifact document that cannot be parsed as an object or whose artifact ABI / scope canonicalizer is not current; aggregate overflow forces failure. | Every promoted row is individually compatible with current `cement-exact-lookup-v1` and `cement-json-v1`. | Relational row bindings, full artifact validity, report validity, equal semantics, or aggregate identity. | Passes vacuously with an explicit zero-entry compatibility detail. |
| P3 | `sealed-passing-reports` | Missing/non-passing bound report; malformed full report or child set; scope mismatch; artifact/build/policy/evidence binding mismatch; aggregate overflow. | Every promoted row carries a passing, fully validated report bound to its artifact and full child-test set. | That tests were replayed now, promotion is current, the entry seal is correct, or the aggregate hash is correct. | Passes with `0 entries carry passing full-seal reports`. |
| P4 | `current-promotion-receipts` | Invalid operation policy binding; invalid artifact; stale revision/policy; invalid recomputed `cement-promotion-v2` receipt; aggregate overflow. | The operation policy is canonical and every promoted row has a valid current activation receipt, including promoter/time provenance. | Passing report completeness, function projection/hash, or persisted set receipt. | Passes for zero rows only if the operation policy itself is valid. |
| P5 | `function-hash-matches-snapshot` | Any row cannot project exactly; normalized document ABI/canonicalizer/scope/count/entry differs; self-check changes; optional expected hash differs; aggregate overflow. | One normalized `cement-function-v2` document and hash exactly represent every current promoted row in the read snapshot. | Persisted receipt, origin/signature, semantic replay, domain coverage, lease, or future state. | Builds and passes a real empty function unless an expected hash or operation-policy binding disagrees. |
| P6 | `persisted-function-receipt` | A nonempty set lacks a current-revision receipt; latest receipt cannot fully reconstruct; live document is unavailable; reconstructed text differs; aggregate overflow. | The latest current-revision persisted receipt fully reconstructs and byte-binds the P5 live document. | Earlier receipt validity as a set, permanence after the transaction, or cross-revision/current-status continuity. | No receipt + zero entries passes vacuously; an existing receipt must reconstruct and equal the empty live document. |

The returned vector is always P1→P6. `passed` is the conjunction of all six checks. On `entry_count > FUNCTION_MAX_ENTRIES`, all six are present and fail without member materialization.

```anchors
src/cement_runtime/system.py	3092	key="duplicate-input-digests",
src/cement_runtime/system.py	3235	"abi-canonicalizer-uniform",
src/cement_runtime/system.py	3246	"sealed-passing-reports",
src/cement_runtime/system.py	3251	"current-promotion-receipts",
src/cement_runtime/system.py	3349	key="function-hash-matches-snapshot",
src/cement_runtime/system.py	2213	key="persisted-function-receipt",
src/cement_runtime/system.py	3366	duplicate_check,
src/cement_runtime/system.py	3367	abi_check,
src/cement_runtime/system.py	3368	report_check,
src/cement_runtime/system.py	3369	receipt_check,
src/cement_runtime/system.py	3370	hash_check,
src/cement_runtime/system.py	3371	persisted_receipt_check,
src/cement_runtime/system.py	3373	passed = all(check.passed for check in checks)
src/cement_runtime/system.py	3021	checks = (
src/cement_runtime/system.py	3023	key="duplicate-input-digests",
src/cement_runtime/system.py	3051	key="persisted-function-receipt",
src/cement_runtime/system.py	2178	if entry_count == 0:
src/cement_runtime/system.py	2187	detail="nonempty promoted set has no current-revision function receipt",
src/cement_runtime/system.py	2210	detail="latest receipt does not bind the promoted snapshot",
```

## S5 CLI `function` group

| Leaf | Exact invocation | Flags and defaults | Stdout | Stderr | Exit codes |
|---|---|---|---|---|---|
| `show` | `cement --db DB --partition PARTITION function show OPERATION [--receipt-id ID] [--projection-limit N]` | `--receipt-id=None`; `--projection-limit=100`, library range `1..10,000`; globals can come from `CEMENT_DB` / `CEMENT_PARTITION` | JSON newline. Top keys: `function_anchor`, `operation`, `operation_now`, `partition`. Anchor: `null` or `{member_count,members,receipt}`. Current-state object carries revision/policy/projection limit plus ready, blocked, pending, status, and stale-anomaly counts and arrays. | Empty on success. Errors use the standard two-key JSON object `{error,message}`. | `0` report returned; `2` usage/name/ID/limit invalid or globals absent; `3` operation or requested receipt absent in scope; `5` ledger/report/member/current-state integrity failure. |
| `receipts` | `cement --db DB --partition PARTITION function receipts OPERATION [--operation-revision N] [--before-sequence N] [--limit N]` | revision `None`, cursor `None`, `limit=100`; revision `1..2^63-1`; cursor `0..2^63-1`; limit `1..10,000` | JSON newline: `{next_before_sequence,receipts}`. Each receipt has all 16 `FunctionReceipt` fields. Unknown/no-row scopes return `{receipts: [], next_before_sequence: null}`. | Standard `{error,message}` only. | `0` page returned, including empty; `2` usage/name/bound invalid or globals absent; `5` a returned receipt row fails self-binding. No exit 3 for an unknown operation. |
| `verify-drafts` | `cement --db DB --partition PARTITION function verify-drafts OPERATION --actor ACTOR` | `--actor` required; no default | JSON newline: whole `DraftVerification` `{entries,operation_revision,passed,skipped}`. Each entry is `{artifact_id,entry_seal,input_hash,report}`; each report is the seven-field `VerificationReport`. | Standard `{error,message}` for 2/3/4/5; none for verdict 6 because the negative model remains on stdout. | `0` every attempted report passed; `2` usage/name/actor invalid or globals absent; `3` operation absent; `4` authority denial or eligibility/state changed; `5` ledger/report integrity failure; `6` batch completed but at least one attempted report failed. |
| `verify` | `cement --db DB --partition PARTITION function verify OPERATION [--expected-function-hash HEX]` | expected hash `None`; when present, 64 lowercase hexadecimal characters | JSON newline, exactly `{checks,entries,function_hash,passed}`. Each check is `{detail,key,passed}`. The nested document never reaches stdout. | Standard `{error,message}` for 2/3/5; none for verdict 6 because the negative check vector remains on stdout. | `0` all P1–P6 pass; `2` usage/name/hash invalid or globals absent; `3` operation absent; `5` top-level ledger corruption that cannot be represented as a check; `6` one or more ordered checks fail, including an expected-hash mismatch. |
| `inspect` | `cement --db DB --partition PARTITION function inspect OPERATION` | no leaf flags | JSON newline, exactly `{entries,function_hash,operation_revision,skipped}`. Each entry is `{artifact_hash,artifact_id,disposition,entry_seal,input_hash,output_hash,replaces_artifact_id}`. `text` and `document` are omitted. | Standard `{error,message}` only. | `0` prospective manifest projected; `2` usage/name invalid or globals absent; `3` operation absent; `4` a candidate no longer qualifies as required state; `5` ledger, artifact, report, seal, policy, or manifest integrity failure. |
| `promote` | `cement --db DB --partition PARTITION function promote OPERATION --expected-function-hash HEX --actor ACTOR` | both flags required; no defaults | JSON newline: `{candidate_artifact_ids,function_hash,member_artifact_ids,operation_revision,promoted_at_us,receipt_hash,receipt_id,retired_artifact_ids}`. | Standard `{error,message}` only. | `0` atomic set promotion committed; `2` usage/name/hash/actor invalid or globals absent; `3` operation absent; `4` empty union, authority denial, authorization/locked-plan drift, predecessor/candidate drift, or repeated hash conflict; `5` ledger/report/artifact/receipt integrity failure. |
| `export` | `cement --db DB --partition PARTITION function export OPERATION [--receipt-id ID] [--out PATH]` | receipt `None` selects the live verified set; out `None` selects stdout | Without `--out`: exact UTF-8 bytes of `FunctionDocument.text`, with no appended newline. With `--out`: atomic 0600 file plus JSON newline `{bytes,function_hash,out}` on stdout. | Standard `{error,message}` for 2/3/5. A live negative verdict uses `{error:"unverified",message,checks}`; stdout stays empty and no bundle bytes are written. | `0` live verified or historical document emitted; `2` usage/name/path/type/write validation failure or globals absent; `3` live operation absent, receipt absent/foreign, or receipt-operation mismatch; `5` live/historical integrity failure; `6` live set verification completed but failed. No historical path uses 6. |
| `eval` | `cement function eval --bundle PATH --input JSON [--expected-function-hash HEX]` | both channels required; expected hash `None`; `--input -` reads stdin; no ledger globals required | JSON newline, exactly `{artifact_hash,function_hash,matched,output}` on both verdicts. A JSON `null` hit remains `matched:true`, distinct from a miss. | Standard `{error,message}` for 2/5; no stderr for miss 6. | `0` exact input matched; `2` usage/input/bundle path/type/read/UTF-8/size/shape validation failure; `5` bundle value digest, embedded hash, or expected hash mismatch; `6` valid bundle and input, but no exact case matched. |

### Exit-6 bijection

Exit 6 always means that the command completed correctly and its answer is negative. The command and channel identify the object:

| Leaf | Exit-6 named object |
|---|---|
| `verify-drafts` | The completed `DraftVerification` batch has `passed=false`; its full model is on stdout. |
| `verify` | The current promoted-set `FunctionVerification` has at least one failed P1–P6 check; its four-key projection is on stdout. |
| `export` | The live current function is unverified, so no media bytes exist; the P1–P6 refusal object is on stderr. |
| `eval` | The validated function has no exact case for the canonical input; its four-key miss payload is on stdout. |

All JSON output is sorted, indented, UTF-8 text with one trailing newline. Raw export bytes are the sole exception. These are the mapped exits. Out-of-band stored-scalar corruption can still raise an unmapped conversion exception instead of returning an exit code.

```anchors
src/cement_runtime/cli.py	190	function_show = function_commands.add_parser("show")
src/cement_runtime/cli.py	193	function_show.add_argument("--projection-limit", type=int, default=100)
src/cement_runtime/cli.py	194	function_receipts = function_commands.add_parser("receipts")
src/cement_runtime/cli.py	198	function_receipts.add_argument("--limit", type=int, default=100)
src/cement_runtime/cli.py	199	function_verify_drafts = function_commands.add_parser("verify-drafts")
src/cement_runtime/cli.py	201	function_verify_drafts.add_argument("--actor", required=True)
src/cement_runtime/cli.py	202	function_verify = function_commands.add_parser("verify")
src/cement_runtime/cli.py	207	function_inspect = function_commands.add_parser("inspect")
src/cement_runtime/cli.py	209	function_promote = function_commands.add_parser("promote")
src/cement_runtime/cli.py	216	function_promote.add_argument("--actor", required=True)
src/cement_runtime/cli.py	217	function_export = function_commands.add_parser("export")
src/cement_runtime/cli.py	225	function_eval = function_commands.add_parser("eval")
src/cement_runtime/cli.py	226	function_eval.add_argument("--bundle", required=True, help="path of an exported bundle file")
src/cement_runtime/cli.py	420	if args.command == "function" and args.function_command == "eval":
src/cement_runtime/cli.py	575	if args.function_command == "show":
src/cement_runtime/cli.py	582	if args.function_command == "receipts":
src/cement_runtime/cli.py	590	if args.function_command == "verify-drafts":
src/cement_runtime/cli.py	596	return _Outcome(drafts, status=0 if drafts.passed else 6)
src/cement_runtime/cli.py	597	if args.function_command == "verify":
src/cement_runtime/cli.py	611	status=0 if verification.passed else 6,
src/cement_runtime/cli.py	613	if args.function_command == "inspect":
src/cement_runtime/cli.py	626	if args.function_command == "promote":
src/cement_runtime/cli.py	633	if args.function_command == "export":
src/cement_runtime/cli.py	655	raise _Unverified(
src/cement_runtime/cli.py	673	return _Outcome(raw=document.text)
src/cement_runtime/cli.py	674	return _write_export(target, document)
src/cement_runtime/cli.py	274	stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
src/cement_runtime/cli.py	685	except _UsageError as exc:
src/cement_runtime/cli.py	687	return 2
src/cement_runtime/cli.py	688	except NotFoundError as exc:
src/cement_runtime/cli.py	690	return 3
src/cement_runtime/cli.py	691	except (ConflictError, StateError) as exc:
src/cement_runtime/cli.py	693	return 4
src/cement_runtime/cli.py	694	except IntegrityError as exc:
src/cement_runtime/cli.py	696	return 5
src/cement_runtime/cli.py	700	except _Unverified as exc:
src/cement_runtime/cli.py	702	return 6
src/cement_runtime/cli.py	437	status=0 if match.matched else 6,
```

## S6 Schema

| Object | Name | Definition / columns | Structural or immutability guarantee |
|---|---|---|---|
| schema version | `SCHEMA_VERSION` | `2` | Existing nonzero schemas other than 2 are rejected. Version 0 is initialized only when the SQLite database is otherwise empty and unrecognized. |
| table | `function_receipts` | `sequence`; unique `id`; scope revision/policy; `function_hash`; `membership_hash`; member count; candidate/retired count+digest; promoter/time; unique `receipt_hash`; unique `(id,function_hash)` | One immutable, self-bound activation/checkpoint receipt. It stores transition ID sets only as counts and digests. It has no foreign key to `operations`. |
| table | `function_memberships` | `receipt_id`; nonnegative `ordinal`; `function_hash`; `artifact_id`; `report_id`; `input_hash`; `entry_seal`; PK `(receipt_id,ordinal)`; unique receipt+artifact and receipt+input | Authoritative exact member list, canonical ordinal order, and one artifact/input per receipt. Contiguity is validated in code, not encoded by SQL. |
| index | `function_receipts_scope` | `(partition, operation, operation_revision, sequence)` | Supports latest-current-revision lookup and descending scoped pagination. |
| index | `function_receipts_hash` | `(function_hash, sequence)` | Supports function-hash-oriented receipt lookup/audit. |
| index | `function_memberships_artifact` | `(artifact_id, receipt_id)` | Supports reverse membership lookup and retains efficient artifact history. |
| trigger | `function_memberships_sealed_insert` | Reject insert when a receipt row with `NEW.receipt_id` already exists. | Promotion must insert the whole membership set before its receipt; no member can be appended afterward. |
| trigger | `function_memberships_no_update` | Reject every membership update. | Membership rows are database-immutable. |
| trigger | `function_memberships_no_delete` | Reject every membership delete. | Membership rows are retained for historical reconstruction. |
| trigger | `function_receipts_no_update` | Reject every receipt update. | Receipt identity, counts, digests, actor, and time are database-immutable. |
| trigger | `function_receipts_no_delete` | Reject every receipt delete. | Receipt rows are retained permanently inside the ledger. |
| foreign-key structure | membership → artifact/report | `artifact_id REFERENCES artifacts(id)`; `report_id REFERENCES test_reports(id)` | With `PRAGMA foreign_keys=ON`, referenced artifacts and reports cannot disappear while a membership exists. SQL does not bind the selected report to that artifact; reconstruction verifies that relation. |
| foreign-key structure | membership → receipt+hash | deferred composite FK `(receipt_id,function_hash) REFERENCES function_receipts(id,function_hash)` | Every committed membership names an existing receipt and exactly its `function_hash`; deferral permits memberships-before-receipt insertion in one transaction. |
| immutable row set | receipts and memberships | Receipt rows reject update/delete. Membership rows reject update/delete and become insert-sealed once the receipt exists. | The historical member projection survives later artifact status transitions. Artifact lifecycle state itself remains mutable. |

M2's complete schema delta is two tables, three indexes, five triggers, and `SCHEMA_VERSION` 1→2. It includes no migration runner for a version-1 ledger; initialization rejects that version.

```anchors
src/cement_runtime/store.py	19	SCHEMA_VERSION = 2
src/cement_runtime/store.py	205	CREATE TABLE IF NOT EXISTS function_receipts (
src/cement_runtime/store.py	222	UNIQUE (id, function_hash)
src/cement_runtime/store.py	225	CREATE TABLE IF NOT EXISTS function_memberships (
src/cement_runtime/store.py	233	PRIMARY KEY (receipt_id, ordinal),
src/cement_runtime/store.py	234	UNIQUE (receipt_id, artifact_id),
src/cement_runtime/store.py	235	UNIQUE (receipt_id, input_hash),
src/cement_runtime/store.py	237	REFERENCES function_receipts(id, function_hash) DEFERRABLE INITIALLY DEFERRED
src/cement_runtime/store.py	261	CREATE INDEX IF NOT EXISTS function_receipts_scope
src/cement_runtime/store.py	263	CREATE INDEX IF NOT EXISTS function_receipts_hash
src/cement_runtime/store.py	265	CREATE INDEX IF NOT EXISTS function_memberships_artifact
src/cement_runtime/store.py	345	CREATE TRIGGER IF NOT EXISTS function_memberships_sealed_insert
src/cement_runtime/store.py	351	CREATE TRIGGER IF NOT EXISTS function_memberships_no_update
src/cement_runtime/store.py	355	CREATE TRIGGER IF NOT EXISTS function_memberships_no_delete
src/cement_runtime/store.py	359	CREATE TRIGGER IF NOT EXISTS function_receipts_no_update
src/cement_runtime/store.py	363	CREATE TRIGGER IF NOT EXISTS function_receipts_no_delete
src/cement_runtime/store.py	496	connection.execute("PRAGMA foreign_keys = ON")
src/cement_runtime/store.py	519	if current not in (0, SCHEMA_VERSION):
src/cement_runtime/system.py	4373	INSERT INTO function_memberships(
src/cement_runtime/system.py	4393	INSERT INTO function_receipts(
```

## S7 Guarantee ledger

| Candidate guarantee / negative guarantee | Verdict | Evidence | Exact limit that must accompany it | Pin status |
|---|---|---|---|---|
| The same admissible function content produces the same canonical bytes and `function_hash`, independent of entry order and process. | TRUE-as-stated | `test_entry_reordering_keeps_one_hash_and_canonical_document`; `test_cross_process_build_is_byte_identical`; S7-A01..A03 | Exact canonical JSON only. Overall and per-value bounds apply; decimals are invalid. | PINNED |
| Evaluation is deterministic exact lookup; repeated hits return detached output, and unknown inputs return an inert miss. | TRUE-as-stated | `test_repeat_evaluation_is_byte_identical_and_mutation_isolated`; `test_unknown_input_returns_no_match`; S7-A04 | It covers only exact canonical inputs. It does not infer, generalize, or prove domain coverage. | PINNED |
| The embedded hash self-checks normalized content; an independently obtained expected hash additionally pins caller-held identity. | TRUE-as-stated | `test_rewritten_content_with_recomputed_hash_is_a_new_function`; S7-A05..A07 | The hash is unkeyed. Copying the expected hash from the same untrusted bundle adds no trust; neither mode proves origin. | PINNED |
| A function hash binds its scope, normalized cases, artifact/evidence digests, report digests, and each supplied entry seal. | TRUE-as-stated | `test_every_document_field_fails_closed_with_typed_errors`; S7-A08 | Portable validation checks `entry_seal` syntax, not ledger truth. Only system verification/reconstruction recomputes the 14-field seal. | PINNED for document binding; seal provenance is system-only |
| Function identity is verified-content identity, not activation identity. Promoter and promotion time do not change the function hash. | TRUE-as-stated | `test_entry_seal_timing_is_invariant_through_promotion_and_function_verify`; entry-seal field list S7-A09; promotion persists actor/time separately S7-A10 | Activation provenance remains in `cement-promotion-v2` and `FunctionReceipt`; never attribute it to `function_hash`. | PINNED |
| A passing `verify_function` result binds the complete current promoted snapshot to all ordered P1–P6 checks and the latest current-revision receipt. | TRUE-as-stated | `test_function_verification_pass_is_read_only_and_authority_free`; `test_reconstruct_function_receipt_matches_promoted_manifest_bytes_hash_order_and_exclusion`; S7-A11 | The binding lasts for one read transaction. It is not a lease, signature, semantic replay, or future-state guarantee. | PINNED |
| `verify_function` is read-only and authority-free. | TRUE-as-stated | `test_function_verification_pass_is_read_only_and_authority_free`; `test_reconstruct_function_receipt_and_p6_are_read_only_by_authorizer_and_full_dump`; S7-A12 | Sets at or below 50,000 rows are materialized before byte/item bounds; the result can be expensive and is never a lease. | PINNED |
| `inspect_function_promotion` returns one deterministic prospective union and does not mutate, authorize, or read the clock. | TRUE-as-stated | `test_function_promotion_manifest_is_deterministic_read_only_and_complete`; S7-A13 | It is unpaged, can emit tens of MiB, takes no lock, and can become stale before promotion. | PINNED |
| `promote_function` repeats the prospective hash under a write lock and atomically retires predecessors, activates candidates, and writes sealed memberships plus a receipt. | TRUE-as-stated | `test_promote_function_persists_receipt_memberships_and_projected_event`; `test_promote_function_late_event_failure_rolls_back_every_write`; S7-A14..A16 | Live activation can later drift. CLI actors are recorded but not authenticated because the CLI constructs the default `System`. | PINNED |
| Historical receipt reconstruction returns the exact promoted document after member supersession, revision retirement, or evidence revocation. | TRUE-as-stated | `test_reconstruct_function_receipt_survives_middle_member_supersession_and_p6_selects_latest`; `...survives_operation_revision_retirement...`; `...survives_revocation_of_every_member_evidence_row`; S7-A17 | Reconstruction is O(members + joined reports/tests), depends on structural retention, and does not claim current status. | PINNED |
| Receipt discovery returns immutable, self-bound rows in descending sequence order. | TRUE-as-stated | `test_function_receipts_enumerates_all_revisions_by_sequence_not_timestamp`; `...cursor_is_exclusive...`; S7-A18 | Discovery never reconstructs memberships. Unknown operations and zero-receipt operations both return an empty page. Each page is a separate transaction. | PINNED |
| `function_report` places its immutable anchor projection and current operation state in one read snapshot. | TRUE-as-stated | `test_function_report_is_one_read_only_snapshot_with_exact_limit_materialization`; S7-A19 | Returned details are bounded by `projection_limit`; unselected members and rows are counted but not validated. Ready/blocked counts require a full current-build pass. | PINNED |
| A live export emits bytes only after all six checks pass; a historical export emits bytes only after full receipt reconstruction. | TRUE-as-stated | `test_function_export_writes_the_live_document_bytes_exactly`; `...refuses_a_drifted_set_with_the_whole_check_vector`; `...exports_one_historical_receipt`; S7-A20 | Raw stdout has no newline. File output is 0600 and old-or-new absent external mutation, but has no directory fsync and retains a final target race. | PINNED for source gate and bytes; crash/race limits UNPINNED |
| `function eval` needs no `System`, store, database path, or SQLite connection. | TRUE-as-stated | `test_function_eval_opens_no_store_or_connection`; S7-A21 | Package import still loads `sqlite3`. Bundle input must be one regular file; no `/dev/stdin` route. The reader takes no lock, admits unusual regular files, and provides no timeout guarantee. Input is canonicalized twice; stdin `OSError` is untranslated. | PINNED for ledger freedom |
| A successfully exported bundle evaluates deterministically without the ledger, adapter, or LLM, even after live ledger state changes. | TRUE-as-stated | Exact export bytes + capability-free evaluator + immutable private lookup state; `test_function_export_round_trips_through_parse_function`; `test_repeat_evaluation_is_byte_identical_and_mutation_isolated`; S7-A20, S7-A21 | The bundle is intentionally sealed from later revocations, policy revisions, and evidence changes. Deploy a newly verified export when those changes must take effect. | PINNED |
| Function receipt and membership rows are immutable and structurally retained by foreign keys. | TRUE-as-stated | `test_function_promotion_schema_v2_is_reference_only_and_immutable`; S7-A22 | Artifact lifecycle status remains mutable. Receipts have no foreign key to operations. SQL does not itself bind `report_id` to `artifact_id`; reconstruction checks it. | PINNED |
| `verify_drafts` verifies the authorized current-build batch in one write transaction and returns every attempted report plus benign skips. | TRUE-as-stated | `test_verify_drafts_uses_shared_projection_and_one_locked_batch`; `test_function_verify_drafts_exits_six_when_the_middle_of_three_entries_fails`; S7-A23 | The negative branch is reachable only from corrupted state under supported flows. Exit 6 commits reports/events, and rerunning writes another report/event. | PINNED behavior; supported-flow unreachability UNPINNED |
| The portable builder accepts exactly 50,000 minimal valid entries and rejects the 50,001st. | TRUE-as-stated | `test_entry_count_accepts_maximum_and_rejects_one_past`; S7-A24 | Per-value 1 MiB / 100,000-item / depth-64 limits and aggregate 64 MiB / 1,000,000-item / depth-67 limits can reject richer sets earlier. | PINNED |
| A function hash proves activation actor or activation time. | FALSE-as-stated | Seal fields exclude both; receipt/promotion fields carry both; S7-A09, S7-A10 | Say instead: `function_hash` identifies verified content. `cement-promotion-v2` and the function receipt identify activation provenance. | PINNED |
| `function_report(..., projection_limit=N)` reconstructs or validates all members beyond N. | FALSE-as-stated | Bounded membership SQL and `test_function_report_member_projection_is_sql_bounded_and_validates_middle_and_last`; S7-A25 | It validates only returned members. Use `reconstruct_function_receipt` for all members. | PINNED |
| Truncated pending-proposal and stale-anomaly details preserve insertion or sequence order. | FALSE-as-stated | The report orders those projections by opaque proposal/artifact IDs; S7-A25B | The order is stable for one unchanged ledger but arbitrary relative to insertion. Compare sets, or compare a bounded page with the same ledger's unbounded prefix. | UNPINNED as an ordering guarantee |
| Cursor traversal of `function receipts` is snapshot-consistent across pages. | FALSE-as-stated | Each call opens a new transaction; the cursor is `sequence < boundary`; S7-A26 | Static pages are ordered and duplicate-free. A receipt inserted mid-walk above the boundary is omitted from that traversal. | UNPINNED |
| A portable bundle proves origin, signature, or ledger governance from its bytes alone. | FALSE-as-stated | `validate_function` checks content digests; `entry_seal` is only syntax-checked; S7-A27 | An independently trusted expected hash pins identity, not origin. Ledger governance requires `verify_function` or receipt reconstruction before export. | UNPINNED as a negative trust claim |
| The function object proves coverage outside its enumerated exact inputs or generalizes across similar inputs. | FALSE-as-stated | `evaluate` compares both canonical digest and text and otherwise returns a miss; S7-A28 | M2 is a finite exact-lookup set. Projection/domain verification remains outside this milestone. | PINNED for exact misses; broad coverage negative UNPINNED |
| A receipt can recover the complete candidate and retired artifact ID sets. | FALSE-as-stated | Receipt schema stores only count+digest; S7-A29 | The immediate return value and bounded event projection expose IDs at promotion time. Historical receipt reconstruction cannot recover those full transition sets. | PINNED |
| Receipt enumeration proves that the named operation exists. | FALSE-as-stated | `test_function_receipts_unknown_operation_is_empty_without_operations_lookup`; S7-A30 | It proves only that no matching receipt row was returned. `latest_function_receipt` performs the operation lookup. | PINNED |
| Verification or a live report freezes later activation state. | FALSE-as-stated | Verifier docstring and one-transaction implementation; S7-A31 | Treat every result as one committed snapshot, never a lease. Exported bytes stay deterministic; the live ledger can later revise, suspend, revoke, replace, or checkpoint. | UNPINNED as a future-state negative |
| Every stored-scalar corruption on function paths becomes `IntegrityError` / CLI exit 5. | FALSE-as-stated | Raw `int(...)` remains in receipt, report, promotion, and artifact validators; S7-A32 | Out-of-band type corruption can still leak `TypeError`, `ValueError`, or `OverflowError` past `main`. This is a tracked audit limit, not a supported state. | UNPINNED; live gap |
| CLI payload and status guarantees survive a failing stdout/stderr stream. | FALSE-as-stated | `_emit` writes but does not flush or translate stream failures; S7-A33 | Channel/status claims assume healthy standard streams. `_input` also leaves stdin `OSError` untranslated. | UNPINNED |
| DIVERGENCE — roadmap: “default canonicalizer walls admit only ~1,600 entries.” | FALSE-as-current-state | Current committed `test_entry_count_accepts_maximum_and_rejects_one_past` builds and evaluates 50,000 minimal entries; S7-A24, S7-D01 | Replace the obsolete approximation with the exact layered limits. Rich entries can still hit byte/item limits before 50,000. | DIVERGENCE; current test decides it |
| DIVERGENCE — roadmap u3a: “not operator-complete, since the operator-visible set hash needs u3b's union.” | FALSE-as-current-state | `inspect_function_promotion` now exposes the prospective hash and `promote_function` consumes it; S7-D02 | Historical unit limit is resolved. Current limit: inspect is read-only, unlocked, and unpaged. | DIVERGENCE; resolved by committed APIs/tests |
| DIVERGENCE — roadmap u3b1: “`verify_function` still exposes P1-P5 only.” | FALSE-as-current-state | Current vector appends `persisted-function-receipt` as P6; `test_function_verification_empty_set_passes_vacuously`; S7-D03 | State the exact six-check vector. | DIVERGENCE; resolved by committed test |
| DIVERGENCE — roadmap u4c3: “Exit 6 now means two different objects across two leaves.” | FALSE-as-current-state | Later export and eval leaves add two more negative objects; S7-D04 | State one meaning across four leaves: execution completed and the command-specific answer is negative. | DIVERGENCE; resolved by later committed leaves |
| DIVERGENCE — roadmap u4c5a: “exit 6 now names three objects across three leaves.” | FALSE-as-current-state | `function eval` adds the fourth object, an exact-lookup miss; S7-D04 | State the same four-leaf rule. | DIVERGENCE; resolved by committed CLI tests |

### Assurance-only limits confirmed

- `_function_promotion_page_fixture` is one 1,001-entry fixture shared by the retained-tail and candidate-tail tests. Weakening it couples multiple enumeration and authorization pins.
- `test_function_receipts_enumerates_maximum_page_and_tail_sentinel` is one 10,001-row fixture. It jointly pins the maximum page, order, lookahead cursor, and tail traversal.
- `test_function_receipt_discovery_public_signatures_are_exact` jointly pins model fields, required defaults, type hints, keyword-only parameters, and return annotations.
- Scratch mutation catalogues and unmerged diff-blind worktrees are not committed evidence. This ledger credits only current source and committed tests; every broader negative claim is marked `UNPINNED`.

```anchors
src/cement_runtime/function.py	226	normalized.sort(key=lambda item: item[0])
tests/test_function.py	131	def test_entry_reordering_keeps_one_hash_and_canonical_document(self) -> None:
tests/test_function.py	555	def test_cross_process_build_is_byte_identical(self) -> None:
tests/test_function.py	91	def test_repeat_evaluation_is_byte_identical_and_mutation_isolated(self) -> None:
tests/test_function.py	124	def test_unknown_input_returns_no_match(self) -> None:
src/cement_runtime/function.py	348	if embedded_hash != normalized.content.digest:
src/cement_runtime/function.py	352	if expected != normalized.content.digest:
tests/test_function.py	738	def test_rewritten_content_with_recomputed_hash_is_a_new_function(self) -> None:
src/cement_runtime/function.py	228	content: dict[str, JSONValue] = {
src/cement_runtime/system.py	205	str(artifact["id"]),
src/cement_runtime/system.py	218	str(report["passed"]),
src/cement_runtime/system.py	4367	"promoted_by": promoted_by,
src/cement_runtime/system.py	4368	"promoted_at_us": now,
src/cement_runtime/system.py	3366	duplicate_check,
src/cement_runtime/system.py	3371	persisted_receipt_check,
src/cement_runtime/system.py	2971	with self.store.transaction(write=False) as connection:
tests/test_system.py	2546	def test_function_verification_pass_is_read_only_and_authority_free(self) -> None:
tests/test_system.py	11137	def test_reconstruct_function_receipt_and_p6_are_read_only_by_authorizer_and_full_dump(self) -> None:
src/cement_runtime/system.py	4177	with self.store.transaction(write=False) as connection:
tests/test_system.py	6625	def test_function_promotion_manifest_is_deterministic_read_only_and_complete(self) -> None:
src/cement_runtime/system.py	4201	with self.store.transaction(write=False) as connection:
src/cement_runtime/system.py	4238	with self.store.transaction(write=True) as connection:
src/cement_runtime/system.py	4273	if locked.manifest.function_hash != expected_function_hash:
src/cement_runtime/system.py	4373	INSERT INTO function_memberships(
src/cement_runtime/system.py	4393	INSERT INTO function_receipts(
tests/test_system.py	6710	def test_promote_function_persists_receipt_memberships_and_projected_event(self) -> None:
tests/test_system.py	7538	def test_promote_function_late_event_failure_rolls_back_every_write(self) -> None:
tests/test_system.py	11074	def test_reconstruct_function_receipt_matches_promoted_manifest_bytes_hash_order_and_exclusion(self) -> None:
tests/test_system.py	11362	def test_reconstruct_function_receipt_survives_middle_member_supersession_and_p6_selects_latest(self) -> None:
tests/test_system.py	11418	def test_reconstruct_function_receipt_survives_operation_revision_retirement_and_p6_ignores_prior_revision(self) -> None:
tests/test_system.py	11455	def test_reconstruct_function_receipt_survives_revocation_of_every_member_evidence_row(self) -> None:
src/cement_runtime/system.py	2293	with self.store.transaction(write=False) as connection:
src/cement_runtime/system.py	2298	ORDER BY sequence DESC LIMIT ?
tests/test_system.py	10176	def test_function_receipts_enumerates_all_revisions_by_sequence_not_timestamp(self) -> None:
tests/test_system.py	10276	def test_function_receipts_cursor_is_exclusive_across_first_middle_and_last_pages(self) -> None:
src/cement_runtime/system.py	2570	with self.store.transaction(write=False) as connection:
src/cement_runtime/system.py	2653	ORDER BY m.ordinal LIMIT ?
tests/test_system.py	15839	def test_function_report_is_one_read_only_snapshot_with_exact_limit_materialization(self) -> None:
src/cement_runtime/cli.py	653	verification = system.verify_function(args.partition, args.operation)
src/cement_runtime/cli.py	654	if not verification.passed:
src/cement_runtime/cli.py	673	return _Outcome(raw=document.text)
tests/test_cli.py	3008	def test_function_export_writes_the_live_document_bytes_exactly(self) -> None:
tests/test_cli.py	3059	def test_function_export_refuses_a_drifted_set_with_the_whole_check_vector(self) -> None:
tests/test_cli.py	3178	def test_function_export_exports_one_historical_receipt(self) -> None:
src/cement_runtime/cli.py	420	if args.command == "function" and args.function_command == "eval":
tests/test_cli.py	4693	def test_function_eval_opens_no_store_or_connection(self) -> None:
src/cement_runtime/store.py	345	CREATE TRIGGER IF NOT EXISTS function_memberships_sealed_insert
src/cement_runtime/store.py	359	CREATE TRIGGER IF NOT EXISTS function_receipts_no_update
src/cement_runtime/store.py	237	REFERENCES function_receipts(id, function_hash) DEFERRABLE INITIALLY DEFERRED
tests/test_system.py	5839	def test_function_promotion_schema_v2_is_reference_only_and_immutable(self) -> None:
src/cement_runtime/system.py	3663	with self.store.transaction(write=True) as connection:
tests/test_system.py	4137	def test_verify_drafts_uses_shared_projection_and_one_locked_batch(self) -> None:
tests/test_cli.py	1488	def test_function_verify_drafts_exits_six_when_the_middle_of_three_entries_fails(self) -> None:
tests/test_cli.py	1508	def test_function_verify_drafts_repeats_a_negative_verdict_for_the_same_corrupt_ledger(self) -> None:
tests/test_function.py	657	def test_entry_count_accepts_maximum_and_rejects_one_past(self) -> None:
tests/test_system.py	16041	def test_function_report_pending_projection_validates_middle_and_last_but_not_tail(self) -> None:
src/cement_runtime/system.py	2289	predicates.append("sequence < ?")
src/cement_runtime/function.py	174	entry_seal = _digest(
src/cement_runtime/function.py	342	trust. Neither mode is a signature or establishes origin.
src/cement_runtime/function.py	388	index = bisect_left(bundle.input_hashes, input_json.digest)
src/cement_runtime/function.py	392	if entry.input.text != input_json.text:
src/cement_runtime/store.py	215	candidate_artifact_ids_hash TEXT NOT NULL,
src/cement_runtime/store.py	217	retired_artifact_ids_hash TEXT NOT NULL,
tests/test_system.py	10498	def test_function_receipts_unknown_operation_is_empty_without_operations_lookup(self) -> None:
src/cement_runtime/system.py	2943	is not a lease, signature, persisted report, semantic replay, or
src/cement_runtime/system.py	320	sequence = int(integers["sequence"])
src/cement_runtime/system.py	5184	test_count = int(row["test_count"])
src/cement_runtime/system.py	5307	support=int(row["support"]),
src/cement_runtime/cli.py	274	stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
src/cement_runtime/cli.py	253	source = sys.stdin.read(DEFAULT_MAX_BYTES + 1)
src/cement_runtime/system.py	4168	def inspect_function_promotion(
src/cement_runtime/system.py	4184	def promote_function(
src/cement_runtime/system.py	3371	persisted_receipt_check,
tests/test_system.py	2110	def _function_promotion_page_fixture(self, *, promoted: bool):
tests/test_system.py	9009	def test_function_promotion_enumerates_retained_page_tail(self) -> None:
tests/test_system.py	9109	def test_function_promotion_enumerates_candidate_page_tail(self) -> None:
tests/test_system.py	10843	def test_function_receipts_enumerates_maximum_page_and_tail_sentinel(self) -> None:
tests/test_system.py	9979	def test_function_receipt_discovery_public_signatures_are_exact(self) -> None:
tests/test_system.py	5753	def test_entry_seal_timing_is_invariant_through_promotion_and_function_verify(self) -> None:
tests/test_system.py	14405	def test_function_report_member_projection_is_sql_bounded_and_validates_middle_and_last(self) -> None:
src/cement_runtime/system.py	2741	ORDER BY p.id LIMIT ?
src/cement_runtime/system.py	2852	ORDER BY id LIMIT ?
src/cement_runtime/system.py	409	the embedding application's access control. Without it, database access is the
src/cement_runtime/cli.py	437	status=0 if match.matched else 6,
```

## S8 Ledger-free eval path

| Question | Exact answer | Evidence / proof technique |
|---|---|---|
| Needs `System`? | No. The eval branch returns before `System(...)` construction. | S8-A01, S8-A02 |
| Needs a database path? | No. It bypasses the `--db` / `CEMENT_DB` gate. | S8-A01, S8-A03 |
| Opens a database connection? | No. The eval branch reads, parses, and evaluates only the supplied files and JSON input. | S8-A01, S8-A04, S8-A05 |
| Import chain still pulling `sqlite3` | Yes. Package initialization imports `System`; `system.py` imports `Store`; `store.py` imports `sqlite3`. Ledger-free means capability-free execution, not import-free execution. | S8-A11..S8-A13 |
| Reader byte bound | It reads at most `FUNCTION_MAX_BYTES + 1` bytes and rejects materialized content above `FUNCTION_MAX_BYTES` = 67,108,864 bytes. The size precheck is advisory. | S8-A06, S8-A07, S8-A08 |
| Payload keys | Exactly `artifact_hash`, `function_hash`, `matched`, and `output` on hits and misses. | S8-A09 |
| Miss verdict | Exit 6; stdout carries the four-key JSON payload with `matched: false`, `output: null`, and `artifact_hash: null`. | S8-A10 |
| Committed ledger-freedom test | `test_function_eval_opens_no_store_or_connection` | It patches both `System.__init__` and `sqlite3.connect` to raise, then proves a real hit still returns the normal successful bytes. This distinguishes ledger freedom from the import chain that still loads `sqlite3`. |

```anchors
src/cement_runtime/cli.py	420	if args.command == "function" and args.function_command == "eval":
src/cement_runtime/cli.py	439	if not args.db:
src/cement_runtime/cli.py	441	if not args.partition:
src/cement_runtime/cli.py	424	input_json = canonicalize(_input(args.input))
src/cement_runtime/cli.py	425	document = parse_function(
src/cement_runtime/cli.py	397	if info.st_size > FUNCTION_MAX_BYTES:
src/cement_runtime/cli.py	404	raw = stream.read(FUNCTION_MAX_BYTES + 1)
src/cement_runtime/function.py	26	FUNCTION_MAX_BYTES = 64 * DEFAULT_MAX_BYTES
src/cement_runtime/cli.py	432	"artifact_hash": match.artifact_hash,
src/cement_runtime/cli.py	433	"function_hash": document.function_hash,
src/cement_runtime/cli.py	434	"matched": match.matched,
src/cement_runtime/cli.py	435	"output": match.output,
src/cement_runtime/cli.py	437	status=0 if match.matched else 6,
src/cement_runtime/__init__.py	62	from .system import System
src/cement_runtime/system.py	88	from .store import Store
src/cement_runtime/store.py	15	import sqlite3
tests/test_cli.py	4693	def test_function_eval_opens_no_store_or_connection(self) -> None:
tests/test_cli.py	4700	System, "__init__", side_effect=AssertionError("System constructed")
tests/test_cli.py	4702	sqlite3, "connect", side_effect=AssertionError("connection opened")
```



---

# Part 3 — anchor manifest for Part 1

## Anchor manifest

```anchors
README.md	3	Cement turns repeatedly supervised LLM answers into narrowly scoped deterministic behavior.
README.md	8	The safety boundary is intentionally small: Cement compiles only exact lookups. A promoted artifact
README.md	13	```text
README.md	29	- LLM output is inert until an explicit supervisor accepts or corrects it.
README.md	30	- The ordinary `handle` result exposes a proposal ID, never the proposed output. Review uses a
README.md	32	- Confirmed examples bind partition, operation revision, canonical input, final output, reviewer,
README.md	34	- Compilation is deterministic and model-free. Conflicts block builds; no majority vote hides them.
README.md	35	- Verification replays every active example in the exact scope plus partition, operation, revision,
README.md	37	- Promotion names the verified scope hash and atomically rechecks operation policy, artifact content,
README.md	40	- Counterexamples, evidence revocation, ambiguity, or runtime integrity failure quarantine affected
README.md	42	- Request IDs are partition-local idempotency keys bound to immutable operation and input content.
README.md	45	Cement returns data, not effects. The caller must run every resolved plan through current
README.md	50	Requirements: Python 3.11+ with SQLite 3.37+ and `uv` for the development workflow.
README.md	52	```bash
README.md	58	The relaxed thresholds above are for a local demonstration. Defaults require three confirmations,
README.md	61	Ask the registered operation to handle JSON. The bundled adapter is a deterministic protocol stub,
README.md	64	```bash
README.md	71	A miss returns `review_required` and a proposal ID. Only the review surface reveals the suggestion:
README.md	73	```bash
README.md	80	Repeat with a distinct request ID until the confirmations satisfy the operation policy. Then run the
README.md	83	```bash
README.md	91	Run `compile` periodically with a scheduler of your choice. It creates drafts and never verifies or
README.md	96	```python
README.md	118	Put every fact that can change the answer into the JSON input, including identity, locale,
README.md	124	`handle` and `request` return explicit states:
README.md	126	| Status | Meaning | Caller action |
README.md	127	|---|---|---|
README.md	128	| `resolved` | Current promoted artifact or still-valid confirmed fixture produced the output. | Re-run live authorization/policy. Then apply the plan idempotently. |
README.md	129	| `review_required` | A hidden candidate awaits supervision. | Inspect the named proposal on the separate review surface. |
README.md	130	| `in_progress` | This partition's generation lease is active. | Poll `request REQUEST_ID`. While the lease is active, the input needs no resubmission. |
README.md	131	| `fallback_failed` | The candidate source failed, or its generation lease expired, and Cement stored no output. | For a stored source failure, retry `handle` with `--retry-failed` or use a new ID. For `generation_lease_expired`, resubmit the original `handle` input and request ID to reclaim the lease. |
README.md	132	| `rejected` | A supervisor rejected the proposal. | Use a new request ID to request another candidate. |
README.md	133	| `reconciliation_required` | A previously returned source lost validity through revocation, suspension, a failed integrity check, or an obsolete operation revision. Cement returns no cached output. | Reconcile any effects already attempted. Then submit a new request ID. |
README.md	135	Replaying a request ID is content-idempotent. It does not promise to replay an unsafe old output.
README.md	140	`cement-json-v1` accepts null, booleans, strings, signed 64-bit integers, arrays, and string-keyed
README.md	145	Proposal and report feeds plus example and artifact insertion catalogs carry monotonic `sequence`
README.md	152	Read [docs/adapter-protocol.md](docs/adapter-protocol.md) for the command adapter protocol. Read
README.md	158	[Hospital OCR layout-learning](examples/hospital_ocr/README.md) - offline walkthrough of supervised
README.md	163	```bash
README.md	168	The project has no runtime package dependencies. It uses `uv_build` only to produce the wheel and
README.md	173	This release is a local control plane, not a network service or an ACL system. A new database starts
README.md	179	The callback gates operation registration/revision, proposal review, compilation, verification,
docs/architecture.md	5	Cement is a pure decision-plan router plus a local control plane:
docs/architecture.md	7	1. Canonicalize bounded JSON with `cement-json-v1`. It uses signed 64-bit integers and string decimal
docs/architecture.md	9	2. Resolve only one integrity-valid promoted artifact whose partition, operation revision, and exact
docs/architecture.md	11	3. Otherwise reserve the idempotent request, call the candidate source outside the SQLite transaction,
docs/architecture.md	13	4. A separate review action accepts, corrects, or rejects the candidate. Accept/correct creates an
docs/architecture.md	15	5. A scheduled compiler groups active fixtures by exact scope. It requires the operation's configured
docs/architecture.md	17	6. The compiler emits `cement-exact-lookup-v1`, a capability-free JSON document with only `exact` and
docs/architecture.md	19	7. Verification binds artifact, policy, runtime/canonicalizer ABI, and the complete evidence snapshot.
docs/architecture.md	21	8. Promotion explicitly repeats the tested scope hash and rechecks every binding in one immediate
docs/architecture.md	25	The LLM proposes instance behavior. It never chooses scope, confirms examples, runs verification, or
docs/architecture.md	30	Scope identity is:
docs/architecture.md	32	```text
docs/architecture.md	36	`partition` is mandatory to prevent accidental cross-tenant/workflow learning. Every explicit
docs/architecture.md	44	Confirmed receipt data and artifact evidence edges are immutable. Revocation is a separate tombstone;
docs/architecture.md	50	A scope is recurring when it has enough distinct, idempotent confirmations. It is stable when those
docs/architecture.md	55	These are operational gates, not proof that supervisors were correct. Exact matching makes the coverage
docs/architecture.md	61	SQLite uses foreign keys, STRICT tables, rollback journaling, `synchronous=EXTRA`, a busy timeout,
docs/architecture.md	66	Initialization adopts only a schema-empty SQLite database. It creates the schema atomically and runs
docs/architecture.md	80	The database file is the integrity and confidentiality trust root in this release. Cement
docs/architecture.md	86	The runtime uses Python 3.11+ and the standard-library `sqlite3`, JSON, subprocess, typing, and unittest
docs/architecture.md	92	Packaging uses the pure-Python [`uv_build` backend](https://docs.astral.sh/uv/concepts/build-backend/).
docs/architecture.md	98	The project evaluated Go plus CEL for future generalized artifacts. CEL offers a constrained
docs/threat-model.md	5	- The host, Python/SQLite runtime, database file permissions, Cement interpreter, and deployment's
docs/threat-model.md	7	- Supervisors and release managers only within the authority and context represented by their
docs/threat-model.md	9	- The provider adapter process as a credential-bearing transport. Its model output remains untrusted.
docs/threat-model.md	13	- Request JSON, including prompt injection.
docs/threat-model.md	14	- LLM candidate output and self-reported provenance.
docs/threat-model.md	15	- Stored input/output content when rendered by another system.
docs/threat-model.md	16	- Frequency by itself, reviewer labels without deployment authentication, and any inferred scope.
docs/threat-model.md	20	- Strict bounded JSON; duplicate keys, decimal/non-finite numbers, non-string keys, deep/large
docs/threat-model.md	23	- Partition, operation revision, and byte-stable canonical equality control scope. Unknown or
docs/threat-model.md	25	- Artifacts are inert data: no code, templates, loops, filesystem, process, network, environment,
docs/threat-model.md	27	- Candidate commands bypass the shell, have timeout/output limits, and run outside database locks. On
docs/threat-model.md	32	- Proposed output is visible only through the review API. Accepted output can differ, and the final
docs/threat-model.md	34	- Evidence conflicts block compilation. Evidence snapshots and policy/artifact digests block stale
docs/threat-model.md	36	- Counterexample, revocation, ambiguity, and integrity failure quarantine builds.
docs/threat-model.md	40	- Authenticate and authorize proposal review, operation revision, promotion, challenge, revocation,
docs/threat-model.md	42	- Put every mutable answer dependency into the input, including identity, permissions, locale, policy
docs/threat-model.md	44	- Minimize, redact, encrypt, expire, and back up evidence according to its data classification. The
docs/threat-model.md	46	- Treat results as plans. Re-run live policy and authorization immediately before an effect. Use the
docs/threat-model.md	48	- Keep provider wrappers pure. Model calls can repeat after timeout or lease recovery.
docs/threat-model.md	49	- Monitor promoted scopes. When policy or expected behavior changes, challenge them. Revise the
docs/threat-model.md	51	- Deploy command adapters on Linux. If crash-resilient process-tree containment is required, add an
docs/threat-model.md	53	- If the database-file trust root is insufficient, protect or sign exported artifacts.
docs/threat-model.md	57	This local release excludes:
docs/threat-model.md	59	- Remote API and authentication.
docs/threat-model.md	60	- Encryption and key erasure.
docs/threat-model.md	61	- External signatures.
docs/threat-model.md	62	- Arbitrary code sandboxing.
docs/threat-model.md	63	- Generalized-rule synthesis.
docs/threat-model.md	64	- Domain schemas and oracles.
docs/threat-model.md	65	- Active shadow sampling.
docs/threat-model.md	66	- Quotas across principals.
docs/threat-model.md	67	- Distributed consensus.
docs/threat-model.md	69	The exact artifact format leaves those gaps visible. It does not imply that Cement solves them.
docs/adapter-protocol.md	3	`CommandCandidateSource` invokes a trusted executable directly with `shell=False`. Cement writes one
docs/adapter-protocol.md	6	```json
docs/adapter-protocol.md	17	The command writes exactly one JSON object to stdout:
docs/adapter-protocol.md	19	```json
docs/adapter-protocol.md	31	The response must contain both fields. Additional top-level fields fail closed. Cement bounds the
docs/adapter-protocol.md	38	On Linux with `/proc`, Cement launches the adapter beneath a private child-subreaper. The supervisor
docs/adapter-protocol.md	49	The adapter receives no stored examples and cannot verify or promote its own proposal. Treat all
docs/adapter-protocol.md	54	Cement can invoke the adapter again after a failed request or an expired generation lease. Provider
examples/hospital_ocr/README.md	3	Hospital document layouts often lead to a new throwaway LLM extraction script for each run. This offline example turns that per-layout work into a durable pipeline. It derives a patient-independent layout signature. A supervisor reviews the extraction plan proposed for that signature. Cement then returns the promoted plan deterministically whenever the same layout recurs. The demo uses no LLM or network.
examples/hospital_ocr/README.md	7	Cement does not learn a parser or generalize across layouts. It resolves one integrity-valid promoted artifact for an exact `(partition, operation, operation revision, canonical input)` scope. Here the canonical input is a layout signature, not the patient document. A01, A02, and A03 contain different patients and values but produce one byte-identical signature, so Cement reuses the promoted plan across patients. The demo is more than a lookup of byte-identical patient OCR.
examples/hospital_ocr/README.md	9	After promotion, a known patient-independent signature returns its confirmed extraction plan without calling the proposal adapter or an LLM. A genuinely new or changed layout produces a different canonical input and therefore a new scope. It follows the gated fallback path instead of silently receiving a plan for another layout. There is no cross-layout generalization.
examples/hospital_ocr/README.md	11	The example parser recognizes only its explicit block grammar and fails closed otherwise. A known signature never certifies extraction correctness.
examples/hospital_ocr/README.md	13	Cement guarantees deterministic plan return only inside that exact valid scope. It does not guarantee that the plan extracts every future document correctly, or that a supervisor accepted a semantically correct plan. Confirmation counts, reviewer counts, observation spans, replay verification, and explicit promotion are operational gates. Plan quality remains the adapter and reviewer's responsibility.
examples/hospital_ocr/README.md	19	```
examples/hospital_ocr/README.md	26	`pipeline.py` supplies the deterministic document path:
examples/hospital_ocr/README.md	28	1. `ocr(path)` reads simulated OCR text and normalizes line endings and blank lines.
examples/hospital_ocr/README.md	29	2. `layout_signature(ocr_text)` records the document type plus one ordered list of label and section keys. It uses block position, not the presence of filled values. Patient values and section body text never enter the signature, including prose with colons.
examples/hospital_ocr/README.md	30	3. `System.handle(...)` either returns the promoted exact-scope plan or asks `PlanProposer.propose(...)` for a supervised candidate.
examples/hospital_ocr/README.md	31	4. `apply_plan(plan, ocr_text)` applies label and section locators and returns extracted strings.
examples/hospital_ocr/README.md	33	`plan_adapter.py` defines `PlanProposer`, a `cement_runtime.CandidateSource`-compatible deterministic stand-in for a production provider adapter. It deliberately does not call an LLM. `run_demo.py` drives review, compilation, verification, promotion, exact resolution, extraction, and audit output.
examples/hospital_ocr/README.md	37	- Partition: `mercy-general` - learning remains isolated to this hospital.
examples/hospital_ocr/README.md	38	- Operation: `document.extraction_plan` - all layouts use one operation; each distinct signature is a separate canonical input and exact scope.
examples/hospital_ocr/README.md	39	- Demo compile policy: `CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)`.
examples/hospital_ocr/README.md	40	- Reviewer: `records-supervisor`.
examples/hospital_ocr/README.md	41	- Promoter: `informatics-lead`.
examples/hospital_ocr/README.md	42	- Corpus: seven files - layout A has three progress notes, layout B has two intake forms, and layout C has two lab slips.
examples/hospital_ocr/README.md	44	Production defaults are stricter: three confirmations, two reviewers, and a seven-day observation span.
examples/hospital_ocr/README.md	48	Generated by `layout_signature(ocr(layout_a_progress_note_01.txt))`:
examples/hospital_ocr/README.md	50	```json
examples/hospital_ocr/README.md	92	Generated by `reference_plan("physician_progress_note")`:
examples/hospital_ocr/README.md	94	```json
examples/hospital_ocr/README.md	143	Both objects obey `cement-json-v1`: null, booleans, strings, signed 64-bit integers, arrays, and string-keyed objects only. Decimal and exponent numbers are excluded.
examples/hospital_ocr/README.md	147	Requirements match the repository: Python 3.11+, SQLite 3.37+, and the `uv` development workflow. From the repository root, after `uv sync`:
examples/hospital_ocr/README.md	149	```bash
examples/hospital_ocr/README.md	153	The driver uses the Python standard library plus `cement_runtime`, creates a temporary SQLite ledger, performs no network access, and exits zero with `All checks passed.`
examples/hospital_ocr/README.md	157	Act 1 shows two reviewed confirmations for layout A, then deterministic compilation, verification, and explicit promotion. Act 2 sends a third patient's document through the same patient-free signature. Cement returns the promoted plan while adapter calls stay flat. Then `apply_plan` emits patient JSON. Act 3 shows that genuinely new layout B does not inherit layout A's plan. Layout B follows its own supervised lifecycle before it resolves without the adapter. Act 4 leaves layout C at one confirmation and reports the policy gate instead of promoting it. The final trace records the complete control-plane sequence.
examples/hospital_ocr/README.md	159	The demo generates the layout-A artifact ID per run. The block masks its 32-hex suffix as `art_<hex>`. Every other line is byte-stable.
examples/hospital_ocr/README.md	161	```text
examples/hospital_ocr/README.md	216	- Canonicalize before learning. The exact recurring input is an ordered layout structure with no patient values. Structural position determines the signature, not the presence of a filled field. Distinct patients can therefore share one scope safely.
examples/hospital_ocr/README.md	217	- Keep decimal quantities as strings. `cement-json-v1` rejects decimal and exponent numbers. Layout C marks `potassium` and `creatinine` as `decimal_string` and extracts values such as `"4.2"` and `"0.9"`.
examples/hospital_ocr/README.md	218	- Treat layout drift as an explicit edge case. A changed layout is a new canonical input, enters supervised fallback, and solidifies through the same lifecycle. Act 4 exposes the recurrence gate as `support 1 is below required 2` rather than applying an old template silently.
examples/hospital_ocr/README.md	219	- Isolate learning by partition. `mercy-general` scopes this evidence and its promoted artifacts to one hospital.
examples/hospital_ocr/README.md	220	- Keep demonstration policy visibly relaxed. Production defaults require more confirmations, more reviewers, and a real observation span.
examples/hospital_ocr/README.md	224	- [Repository overview](../../README.md)
examples/hospital_ocr/README.md	225	- [Architecture](../../docs/architecture.md) - state model, exact-scope guarantees, and trust boundary
examples/hospital_ocr/README.md	226	- [Candidate adapter protocol](../../docs/adapter-protocol.md) - candidate request, output, and failure contract
examples/hospital_ocr/README.md	228	Read `run_demo.py` for the lifecycle driver, `pipeline.py` for signature and extraction mechanics, and `plan_adapter.py` for the deterministic candidate source.
tests/test_system.py	870	def test_audit_events_and_learning_are_partition_exact(self) -> None:
tests/test_system.py	1125	def test_authority_denial_precedes_control_plane_mutation(self) -> None:
tests/test_system.py	1164	def test_authority_requires_the_exact_boolean_true(self) -> None:
tests/test_hospital_ocr_example.py	185	def test_blank_label_value_keeps_the_same_structural_kind(self) -> None:
tests/test_system.py	292	def test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence(self) -> None:
tests/test_system.py	572	def test_concurrent_retry_observes_generation_lease(self) -> None:
tests/test_system.py	395	def test_correction_is_the_fixture_and_conflicts_block_compilation(self) -> None:
tests/test_system.py	433	def test_counterexample_and_revocation_quarantine(self) -> None:
tests/test_function.py	599	def test_declared_limits_and_inclusive_document_boundaries(self) -> None:
tests/test_source.py	111	def test_detached_descendants_are_killed_and_reaped(self) -> None:
tests/test_hospital_ocr_example.py	403	def test_drifted_known_layout_falls_back_to_applicable_best_effort_plan(self) -> None:
tests/test_hospital_ocr_example.py	293	def test_duplicate_section_heading_is_rejected_rather_than_guessed(self) -> None:
tests/test_function.py	131	def test_entry_reordering_keeps_one_hash_and_canonical_document(self) -> None:
tests/test_system.py	5753	def test_entry_seal_timing_is_invariant_through_promotion_and_function_verify(self) -> None:
tests/test_hospital_ocr_example.py	134	def test_every_document_in_one_layout_has_a_byte_identical_signature(self) -> None:
tests/test_cli.py	4432	def test_function_eval_answers_an_empty_exported_function(self) -> None:
tests/test_cli.py	4262	def test_function_eval_bundle_size_bound_is_an_adjacent_pair(self) -> None:
tests/test_cli.py	4394	def test_function_eval_exit_six_names_the_miss_and_nothing_else(self) -> None:
tests/test_cli.py	4102	def test_function_eval_expected_hash_binds_caller_held_identity(self) -> None:
tests/test_cli.py	4655	def test_function_eval_forwards_the_expected_hash_unvalidated(self) -> None:
tests/test_cli.py	4312	def test_function_eval_input_keeps_the_default_channel_bounds(self) -> None:
tests/test_cli.py	4072	def test_function_eval_lookup_is_canonical_not_textual(self) -> None:
tests/test_cli.py	4015	def test_function_eval_miss_is_exit_six_with_the_same_identity(self) -> None:
tests/test_cli.py	4511	def test_function_eval_never_reaches_the_ledger_globals(self) -> None:
tests/test_cli.py	4693	def test_function_eval_opens_no_store_or_connection(self) -> None:
tests/test_cli.py	4457	def test_function_eval_payload_covers_every_match_field(self) -> None:
tests/test_cli.py	4202	def test_function_eval_requires_a_regular_file(self) -> None:
tests/test_cli.py	3178	def test_function_export_exports_one_historical_receipt(self) -> None:
tests/test_cli.py	3048	def test_function_export_of_an_empty_promoted_set_exports_its_document(self) -> None:
tests/test_cli.py	3657	def test_function_export_out_keeps_mode_0600_under_a_permissive_umask(self) -> None:
tests/test_cli.py	3475	def test_function_export_out_never_exposes_a_partial_destination(self) -> None:
tests/test_cli.py	3579	def test_function_export_out_rejects_unusable_destinations(self) -> None:
tests/test_cli.py	3059	def test_function_export_refuses_a_drifted_set_with_the_whole_check_vector(self) -> None:
tests/test_cli.py	3021	def test_function_export_round_trips_through_parse_function(self) -> None:
tests/test_cli.py	3322	def test_function_export_serves_a_receipt_from_a_superseded_revision(self) -> None:
tests/test_cli.py	3008	def test_function_export_writes_the_live_document_bytes_exactly(self) -> None:
tests/test_cli.py	2651	def test_function_promote_forwards_hash_and_actor_verbatim(self) -> None:
tests/test_system.py	6625	def test_function_promotion_manifest_is_deterministic_read_only_and_complete(self) -> None:
tests/test_system.py	5839	def test_function_promotion_schema_v2_is_reference_only_and_immutable(self) -> None:
tests/test_system.py	10276	def test_function_receipts_cursor_is_exclusive_across_first_middle_and_last_pages(self) -> None:
tests/test_system.py	10176	def test_function_receipts_enumerates_all_revisions_by_sequence_not_timestamp(self) -> None:
tests/test_cli.py	850	def test_function_receipts_enumerates_newest_first(self) -> None:
tests/test_system.py	14184	def test_function_report_keeps_historical_build_and_current_evidence_anchors_distinct(self) -> None:
tests/test_system.py	15370	def test_function_report_pending_count_reaches_the_10001_tail_with_bounded_detail(self) -> None:
tests/test_system.py	14002	def test_function_report_projects_both_anchors_with_exact_counts_and_ordering(self) -> None:
tests/test_system.py	14801	def test_function_report_reaches_every_compiler_block_reason_through_public_apis(self) -> None:
tests/test_system.py	15654	def test_function_report_stale_anomalies_cover_three_active_statuses_at_revision_ten(self) -> None:
tests/test_cli.py	554	def test_function_show_projection_limit_truncates_visibly(self) -> None:
tests/test_cli.py	1122	def test_function_show_receipt_id_reaches_a_superseded_revision(self) -> None:
tests/test_cli.py	500	def test_function_show_without_receipt_reports_current_anchor_only(self) -> None:
tests/test_function.py	149	def test_function_v1_document_is_explicitly_rejected(self) -> None:
tests/test_cli.py	1885	def test_function_verdicts_preserve_the_symbol_qualified_exit_map(self) -> None:
tests/test_system.py	2380	def test_function_verification_empty_set_passes_vacuously(self) -> None:
tests/test_system.py	3247	def test_function_verification_expected_hash_detects_set_growth(self) -> None:
tests/test_system.py	3419	def test_function_verification_matches_independent_scoped_membership(self) -> None:
tests/test_system.py	2546	def test_function_verification_pass_is_read_only_and_authority_free(self) -> None:
tests/test_system.py	4007	def test_function_verification_race_returns_one_coherent_snapshot(self) -> None:
tests/test_cli.py	1780	def test_function_verify_drafts_forwards_scope_positionally_and_actor_by_keyword(self) -> None:
tests/test_source.py	25	def test_json_protocol_and_provenance_binding(self) -> None:
tests/test_hospital_ocr_example.py	350	def test_known_layout_plans_match_reference_extraction_for_each_layout(self) -> None:
tests/test_system.py	494	def test_late_review_counterexample_quarantines_promoted_scope(self) -> None:
tests/test_json_value.py	50	def test_limit_configuration_requires_exact_integers(self) -> None:
tests/test_hospital_ocr_example.py	159	def test_moving_a_label_into_a_section_changes_the_signature(self) -> None:
tests/test_source.py	39	def test_nonzero_stderr_is_not_reflected(self) -> None:
tests/test_json_value.py	8	def test_object_order_is_erased_but_number_and_unicode_semantics_are_conservative(self) -> None:
tests/test_system.py	761	def test_operation_revision_retires_old_artifacts(self) -> None:
tests/test_source.py	129	def test_outer_watchdog_kills_adapter_if_supervisor_dies(self) -> None:
tests/test_hospital_ocr_example.py	172	def test_patient_colon_prose_does_not_change_or_leak_into_signature(self) -> None:
tests/test_function.py	625	def test_per_value_boundaries_and_depth_67_embedding(self) -> None:
tests/test_system.py	7015	def test_promote_function_growth_retains_the_complete_existing_set(self) -> None:
tests/test_system.py	6710	def test_promote_function_persists_receipt_memberships_and_projected_event(self) -> None:
tests/test_system.py	7090	def test_promote_function_retires_three_predecessors_before_activation(self) -> None:
tests/test_system.py	7157	def test_promote_function_zero_candidate_checkpoints_legacy_set(self) -> None:
tests/test_system.py	304	def test_proposal_content_hashes_fail_closed_on_storage_mutation(self) -> None:
tests/test_hospital_ocr_example.py	368	def test_propose_is_byte_deterministic_for_output_and_provenance(self) -> None:
tests/test_system.py	474	def test_quarantined_artifact_cannot_replay_an_old_idempotency_key(self) -> None:
tests/test_system.py	11362	def test_reconstruct_function_receipt_survives_middle_member_supersession_and_p6_selects_latest(self) -> None:
tests/test_system.py	11418	def test_reconstruct_function_receipt_survives_operation_revision_retirement_and_p6_ignores_prior_revision(self) -> None:
tests/test_system.py	11455	def test_reconstruct_function_receipt_survives_revocation_of_every_member_evidence_row(self) -> None:
tests/test_hospital_ocr_example.py	211	def test_reference_plans_extract_complete_expected_objects(self) -> None:
tests/test_function.py	91	def test_repeat_evaluation_is_byte_identical_and_mutation_isolated(self) -> None:
tests/test_system.py	517	def test_request_idempotency_and_partition_isolation(self) -> None:
tests/test_system.py	716	def test_runtime_integrity_failure_quarantines_then_falls_back(self) -> None:
tests/test_hospital_ocr_example.py	256	def test_section_locators_keep_colon_lines_and_stop_before_field_blocks(self) -> None:
tests/test_hospital_ocr_example.py	202	def test_signatures_exclude_all_real_patient_values(self) -> None:
tests/test_hospital_ocr_example.py	317	def test_signatures_reference_plans_and_outputs_are_cement_json_v1(self) -> None:
tests/test_source.py	61	def test_stdout_and_stderr_are_stream_bounded(self) -> None:
tests/test_system.py	260	def test_supervised_miss_to_exact_artifact_hit(self) -> None:
tests/test_source.py	48	def test_timeout_and_invalid_response_are_inert_failures(self) -> None:
tests/test_function.py	124	def test_unknown_input_returns_no_match(self) -> None:
tests/test_hospital_ocr_example.py	194	def test_unrecognized_block_shape_fails_closed(self) -> None:
tests/test_cli.py	462	def test_usage_errors_and_oversized_stdin_are_machine_readable(self) -> None:
tests/test_system.py	955	def test_verification_recomputes_build_stability_metadata(self) -> None:
tests/test_system.py	4491	def test_verify_drafts_selects_current_middle_build_and_reports_skipped(self) -> None:
tests/test_system.py	4137	def test_verify_drafts_uses_shared_projection_and_one_locked_batch(self) -> None:
tests/test_system.py	11499	def test_verify_function_p6_nonempty_legacy_three_member_set_without_receipt_fails_only_p6(self) -> None:
src/cement_runtime/artifacts.py	18	ARTIFACT_ABI = "cement-exact-lookup-v1"
src/cement_runtime/artifacts.py	68	def validate_artifact(value: Any) -> ArtifactDocument:
src/cement_runtime/source.py	25	class CandidateSource(Protocol):
src/cement_runtime/cli.py	188	function = commands.add_parser("function", help="inspect the operation's function set")
src/cement_runtime/cli.py	100	handle = commands.add_parser("handle", help="route or create an inert LLM proposal")
src/cement_runtime/cli.py	86	operation = commands.add_parser("operation", help="manage versioned operation policy")
src/cement_runtime/cli.py	112	proposal = commands.add_parser("proposal", help="inspect/review supervised proposals")
src/cement_runtime/cli.py	71	parser = _JSONArgumentParser(
src/cement_runtime/source.py	31	class CommandCandidateSource:
src/cement_runtime/models.py	15	min_confirmations: int = 3
src/cement_runtime/models.py	16	min_reviewers: int = 2
src/cement_runtime/models.py	17	min_span_seconds: int = 7 * 24 * 60 * 60
.agent/memory.md	5	Sole configured gate = `uv run python -m unittest discover -s tests -t .`
src/cement_runtime/function.py	24	FUNCTION_ABI = "cement-function-v2"
src/cement_runtime/function.py	38	class FunctionEntry:
src/cement_runtime/function.py	1	"""Portable, capability-free exact-function document and evaluator."""
src/cement_runtime/function.py	5	from bisect import bisect_left
src/cement_runtime/function.py	7	from dataclasses import dataclass
src/cement_runtime/function.py	342	Neither mode is a signature or establishes origin.
examples/hospital_ocr/run_demo.py	110	_document("layout_a_progress_note_01.txt")
examples/hospital_ocr/run_demo.py	182	_document("layout_b_intake_form_01.txt")
examples/hospital_ocr/run_demo.py	246	_document("layout_c_lab_slip_01.txt")
examples/hospital_ocr/pipeline.py	146	def ocr(path: str | Path) -> str:
examples/hospital_ocr/pipeline.py	1	"""Deterministic OCR-to-JSON core for the synthetic hospital corpus.
examples/hospital_ocr/plan_adapter.py	19	class PlanProposer:
examples/hospital_ocr/run_demo.py	85	def main() -> None:
examples/hospital_ocr/run_demo.py	31	PARTITION = "mercy-general"
examples/hospital_ocr/run_demo.py	34	DEMO_POLICY = CompilePolicy(
examples/hospital_ocr/run_demo.py	158	promoted_by="informatics-lead",
examples/hospital_ocr/run_demo.py	128	reviewer="records-supervisor",
src/cement_runtime/models.py	115	Outcome: TypeAlias = (
pyproject.toml	14	build-backend = "uv_build"
pyproject.toml	7	dependencies = []
pyproject.toml	6	requires-python = ">=3.11"
src/cement_runtime/__init__.py	64	__all__ = [
pyproject.toml	10	cement = "cement_runtime.cli:main"
src/cement_runtime/store.py	20	MIN_SQLITE = (3, 37, 0)
src/cement_runtime/store.py	1	"""SQLite durability boundary.
src/cement_runtime/store.py	22	SCHEMA = r"""
src/cement_runtime/store.py	19	SCHEMA_VERSION = 2
src/cement_runtime/system.py	589	def handle(
```

