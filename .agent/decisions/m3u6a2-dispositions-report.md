# M3.6a2 disposition repair report

## Verdicts

| id | module | test | disposition | one-line grounds | gate that proves it |
|---|---|---|---|---|---|
| R01 | tests/test_cli_channels_battery.py | test_d24_zero_source_calls_zero_system_propose_calls_and_zero_sourc | rebase | Subject = CLI `resolve`/`proposal submit` isolation from candidate-source reach. The deleted `handle` control is replaced by direct `System.propose`, which proves the configured exploding source remains reachable while both CLI leaves stay isolated. | G1 + G3 |
| R02 | tests/test_proposal_binding_battery.py | test_b30_the_six_owned_event_payloads_are_2 | rebase | Mixed subject: the `handle` request-ID payload is deleted, while proposal-created subject identity, empty payload, and `status_sequence` binding survive. The frame now drives `submit_proposal` and preserves those assertions unchanged in strength. | G1 + G3 |
| R03 | tests/test_resolve_battery.py | test_b04 | rebase | Mixed subject: the `handle`/FunctionResolution cross-wire half is deleted; the surviving half still proves `resolve` returns exact `FunctionResolution` and cannot reach a legacy `Resolved` constructor because the runtime module exposes none. | G1 + G3 |
| R04 | tests/test_submission_battery.py | test_d03_the_event_is_proposal_created_with | rebase | Subject = exact `proposal.created` kind, proposal subject, and empty request-free payload on direct and source proposal routes. `handle` only supplied a deleted normalization baseline, so both surviving routes are now compared directly. | G1 + G3 |
| R05 | tests/test_submission_battery.py | test_d23_the_eight_named_seams_still_expose | rebase | Mixed subject: `handle` and `request_status` exposure leave with the lifecycle; CandidateRequest trace identity and the request-free proposal/review/report surfaces survive. The frame now pins one exposed seam and five non-exposing seams. | G1 + G3 |
| R06 | tests/test_submission.py | test_handle_still_answers_on_a_system_that_submitted_directly | delete | Subject = interoperability from `submit_proposal` back into `System.handle`. The only asserted outcome is `ReviewRequired` from the deleted dispatcher; direct submission and review interoperability remain pinned by the adjacent surviving test. | G2 + G3 |
| R07 | tests/test_system.py | test_activation_requires_an_integrity_valid_promotion_receipt | rebase | Subject = integrity-invalid promotion receipts cannot remain usable. `handle` was only the driver; surviving `challenge` performs the same receipt validation, quarantines the artifact, raises, and preserves the suspension assertion. | G1 + G3 |
| R08 | tests/test_system.py | test_artifact_request_cache_is_bound_to_current_execution | delete | Subject = request-ID artifact-dispatch cache binding to the execution that produced its stored output. The cache row, `handle` replay, `request_status` polling, and reconciliation outcome are all deleted lifecycle behavior. | G2 + G3 |
| R09 | tests/test_system.py | test_confirmed_request_cache_is_bound_to_immutable_example | delete | Subject = request-ID confirmed-output cache validation against an immutable example through `request_status` and replayed `handle`. Both cache access paths and their reconciliation outcome leave with the lifecycle. | G2 + G3 |
| R10 | tests/test_system.py | test_dispatch_uses_sealed_promotion_receipt_without_rehashing_tests | delete | Subject = `handle` artifact dispatch trusting a sealed promotion receipt without rehashing child tests. Artifact dispatch has no successor; `resolve` deliberately pays full verification and therefore cannot preserve this fast-path assertion. | G2 + G3 |
| R11 | tests/test_system.py | test_expired_generation_poll_is_retryable_and_handle_reclaims | delete | Subject = generation-lease expiry, `request_status` polling, and `handle` reclamation with the same request ID. Every assertion belongs to the removed lease/retry lifecycle; no proposal-route property survives inside this frame. | G2 + G3 |
| R12 | tests/test_system.py | test_function_report_pending_proposals_bind_partition_operation_request_and_revision | rebase | Subject = `function_report` pending proposals bind partition, operation, private request row, and operation revision under collision probes. Proposal creation now uses `propose` with controlled internal request IDs; every report assertion remains. | G1 + G3 |
| R13 | tests/test_system.py | test_function_verification_rehashes_sealed_reports_off_dispatch | rebase | Mixed subject: function verification must rehash sealed report tests, while `handle` dispatch intentionally did not. The deleted dispatch half is replaced by `resolve`, whose full six-check vector repeats the sealed-report failure and returns no match. | G1 + G3 |
| R14 | tests/test_system.py | test_missing_or_broken_source_is_a_stored_inert_failure | rebase | Mixed subject: stored inert fallback replay is deleted, while missing and broken candidate-source classification survives. The frame now asserts exact `StateError`/`CandidateSourceError` channels and zero request or proposal writes. | G1 + G3 |
| R15 | tests/test_system.py | test_operation_revision_invalidates_every_old_request_path | rebase | Mixed subject: old request replay and polling are deleted; obsolete pending-proposal review, reject cleanup, private request-row revision binding, and revision-two generation survive. The frame now drives those properties through `propose`. | G1 + G3 |
| R16 | tests/test_system.py | test_public_scalar_validation_fails_with_domain_errors | rebase | Mixed census: the lease constructor and two `handle` scalar cases are deleted API members. Every surviving public scalar validation case remains unchanged, including collection cursors, review/promote inputs, clock configuration, and overflow. | G1 + G3 |
| R17 | tests/test_system.py | test_quarantined_artifact_cannot_replay_an_old_idempotency_key | delete | Subject = replaying one pre-quarantine `handle` request ID after artifact suspension and receiving `ReconciliationRequired`. Request-ID idempotency replay is deleted; surviving challenge/revocation quarantine is pinned by adjacent tests. | G2 + G3 |
| R18 | tests/test_system.py | test_request_idempotency_and_partition_isolation | rebase | Mixed subject: request-ID idempotency and conflict replay are deleted, while proposal non-idempotency and partition-exact lookup survive. The frame now proves distinct proposal IDs and bidirectional cross-partition `NotFoundError`. | G1 + G3 |
| R19 | tests/test_system.py | test_supervised_miss_to_exact_artifact_hit | rebase | Subject = supervised exact entry becoming a deterministic hit while a near input remains a miss. The frame now promotes a function, proves `resolve` hit/miss without source calls, then invokes `propose` explicitly for new supervision. | G1 + G3 |
| R20 | tests/test_system.py | test_terminal_build_does_not_block_safe_recompilation | rebase | Subject = a retired and revoked build does not block safe recompilation and renewed deterministic use. Only the final `handle` liveness driver was deleted; the frame now promotes the rebuilt function and proves an exact `resolve` hit. | G1 + G3 |
| R21 | tests/test_cli_channels_battery.py | test_d16_the_aggregate_cap_is_2_default_max_bytes_provenance_max_by | remeasure | Subject = aggregate submission-cap provenance-reference census; deleting `handle` removes its only cap reference, so the exact system-name total moves 4→3 while derivation and no-copy pins remain. | G1 + G3 |
| R22 | tests/test_cli_channels.py | test_x11_the_aggregate_transport_cap_is_derived_from_one_exported_p | remeasure | Subject = aggregate transport-cap load-site census; the removed `handle` branch owned one of three `PROVENANCE_MAX_BYTES` loads, so the surviving exact load total is 2 without weakening cap derivation. | G1 + G3 |
| R23 | tests/test_cli_removal_battery.py | test_d17_gate_4_agent_decisions_m3u5a_s2_probe_py_five_failing | remeasure | Subject = legacy M3.5a probe's pinned provenance-reference census. Diagnosis: the shown absent-path CHECK is healthy; the sole failing fact is `reference_sites`, which moves 4→3 when `handle` is deleted. | G1 + G3 |
| R24 | tests/test_proposal_binding_battery.py | test_b02_confinement_is_a_complement_assertion_over | remeasure | Subject = complement assertion over every lexical `requests` SQL owner. Four deleted lifecycle owners leave exactly `_persist_proposal`, `_proposal_bindings`, and `_write_proposal_request_status`; the full-set equality remains. | G1 + G3 |
| R25 | tests/test_proposal_binding_battery.py | test_b03_the_permitted_owner_set_is_exactly | remeasure | Subject = exact permitted-owner count plus M3.4 freed-path exclusion. The lifecycle deletion moves the permitted set from seven names to the same three surviving proposal-plumbing owners; the freed complement remains disjoint. | G1 + G3 |
| R26 | tests/test_proposal_binding.py | test_exactly_the_permitted_definitions_name_the_request_row | remeasure | Subject = shared permitted-request-namer set and its equality with shipped lexical owners. Re-derived membership is exactly three proposal-plumbing definitions, pinned positively before comparing the source census. | G1 + G3 |
| R27 | tests/test_read_capability_battery.py | test_b20_read_site_census_has_no_mutations | remeasure | Subject = exact read/write transaction and reached-helper census. Lifecycle deletion removes 1 read site, 3 write sites, and 1 reached helper; totals remeasure to 17/13/11 with proposal controls and zero violations intact. | G1 + G3 |
| R28 | tests/test_read_capability_census.py | test_the_census_still_finds_the_surface_it_was_measured_against | remeasure | Subject = anti-collapse floor for the independent transaction census. The removed lifecycle lowers real write sites from 15 to 13; positive floors remain read≥17, write≥13, helpers≥12 so an empty scan still fails. | G1 + G3 |
| R29 | tests/test_submission_battery.py | test_d28_the_census_counts_match_the_sites | remeasure | Subject = executable and AST-backed exact-total pin for B20's transaction census. Re-derived post-removal totals are 17 reads, 13 writes, and 11 reached helpers; named proposal-site controls remain required. | G1 + G3 |
| R30 | tests/test_submission_battery.py | test_d29_every_census_site_binds_a_simple | remeasure | Subject = meta-census that executes B20 and pins simple bindings plus an empty violation set. Its underlying exact totals move with deleted sites to 17 reads, 13 writes, and 11 reached helpers; all shape checks remain. | G1 + G3 |
| R31 | tests/test_system.py | test_concurrent_retry_observes_generation_lease | delete | Subject = concurrent duplicate `handle` calls returning `InProgress` while a generation lease is held. Request-ID idempotency, the lease, and the `InProgress` outcome are all on this unit's deletion set. | G2 + G3 |
| R32 | tests/test_system.py | test_revision_cancels_in_flight_old_generation | delete | Subject = revision cancellation of an in-flight `handle` generation and its `ReconciliationRequired` outcome. The frame asserts no independent revision-bump or artifact-retirement property, so its whole subject is deleted. | G2 + G3 |

## Details

### R01

CLI isolation survives; lifecycle dispatch does not. The positive control now calls `System.propose` directly, reaches the exploding source through `CandidateSourceError`, and writes zero rows. Both CLI leaves still call neither the source nor `System.propose`.

### R02

The request-ID-bearing `handle` payload is deleted. The same frame now drives `submit_proposal` and retains proposal subject identity, the empty payload, and the proposal `status_sequence == event.sequence` binding.

### R03

The legacy `handle` cross-wire half is deleted. The frame retains exact `FunctionResolution` type identity and asserts that `cement_runtime.system` exposes no `Resolved` constructor.

### R05

The lifecycle removed two request-identity seams. `CandidateRequest` remains the one exposed adapter seam; proposal views, records, feeds, report gaps, and review results remain request-free.

### R07

`challenge` is the surviving integrity-quarantine driver. A forged promotion receipt still raises, suspends the artifact, and prevents an integrity-invalid promoted artifact from remaining usable.

### R10

No surviving route has the old no-rehash dispatch contract. `resolve` intentionally pays full verification per call, so translating this frame would invert its subject; deletion is the only faithful disposition.

### R12

The report join still needs a same-request-ID cross-partition collision. A local `_new_id` seam supplies controlled private request IDs while public proposal creation uses `propose`; the test proves both colliding rows exist before checking report membership and revision binding.

### R13

The deleted branch asserted that dispatch skipped test rehashing. The surviving branch now calls `resolve` and repeats the six-check failure vector, the corrupt artifact detail, and the no-match result.

### R14

Stored inert fallback replay is gone. Missing and broken sources still have distinct exact error channels, and both failures now prove zero request and proposal writes.

### R15

Request replay and polling are deleted. The frame retains revision-one pending proposal rejection/acceptance behavior, reads the private request row directly, and proves the next source request binds revision two.

### R16

The constructor lease case and two `handle` cases leave with their APIs. Every surviving scalar-validation case remains in the same assertion loop; clock configuration and signed-64-bit overflow controls remain.

### R17

The sole assertions concerned replay of a pre-quarantine idempotency key. The frame did not independently assert quarantine state; adjacent challenge/revocation tests retain that surviving subject.

### R18

Request-ID deduplication and conflict replay are deleted. The same frame now pins proposal non-idempotency and bidirectional partition-exact lookup failures.

### R19

The new lifecycle is explicit: supervise and promote a function, resolve an exact hit without source calls, resolve a near miss without source calls, then call `propose` to obtain new supervision.

### R20

Compilation liveness survives unchanged through the third promotion. The final driver now promotes the rebuilt function and proves that `resolve` returns the rebuilt entry hash.

### R23

The recorded symptom displayed stderr from its first healthy check: `absent_path_construction.exists_before ... got=False`. The sole failing fact was `provenance_literal.reference_sites`, which moved from four to three because `handle` owned the removed reference.

## GATES

### G1 — focused repaired-frame gate

Command:

```text
uv run python -m unittest tests.test_system tests.test_submission tests.test_submission_battery tests.test_proposal_binding tests.test_proposal_binding_battery tests.test_resolve_battery tests.test_read_capability_battery tests.test_read_capability_census tests.test_cli_channels tests.test_cli_channels_battery tests.test_cli_removal_battery
```

Exact tail:

```text
Ran 677 tests in 41.433s

OK
```

### G2 — lifecycle-removal battery

Command:

```text
uv run python -m unittest tests.test_lifecycle_removal_battery
```

Exact tail:

```text
Ran 59 tests in 202.984s

OK
```

### G3 — disposition grader

Command:

```text
uv run python .agent/decisions/m3u6a2-dispositions-validate.py
```

Exact output:

```text
ROWS: 32 RULED: 32 UNRULED: 0
DELETED: 8
REBASED: 14
REMEASURED: 10
RESULT: PASS (0 findings)
```

### G4 — closure instrument

Command:

```text
uv run python .agent/decisions/m3u6a2-closure.py
```

Exact output:

```text
CHECK L09 dangling_references ok names={'handle': 0, 'request_status': 7, '_outcome': 0, '_fail_generation': 0, '_request_revision_is_current': 0, '_lease_us': 0} want={'handle': 0, 'request_status': 7, '_outcome': 0, '_fail_generation': 0, '_request_revision_is_current': 0, '_lease_us': 0} computed_attribute_names=[]
CHECK L10 models_import_delta ok dropped=['FallbackFailed', 'InProgress', 'Outcome', 'ReconciliationRequired', 'Rejected', 'Resolved', 'ReviewRequired'] want=['FallbackFailed', 'InProgress', 'Outcome', 'ReconciliationRequired', 'Rejected', 'Resolved', 'ReviewRequired'] added=[]
CHECK L11 event_kind_vocabulary ok kinds=16 calls=14 unsupported=[] request_prefixed=[] missing=[] extra=[]
CHECK L13 requests_site_inventory ok lines=7 multiplicity=[1] owners={'_proposal_bindings': 4, '_write_proposal_request_status': 2, '_persist_proposal': 1} kinds={'_proposal_bindings': 'function', '_write_proposal_request_status': 'function', '_persist_proposal': 'method'} verbs={'SELECT': 4, 'UPDATE': 2, 'INSERT': 1}
CHECK L12/L14/L15 byte_identity ok exports=57 findings=[]
RESULT: PASS (0/5 checks failed)
```

### G5 — full discovery

Command:

```text
uv run python -m unittest discover -s tests -t .
```

Exact tail:

```text
Ran 1030 tests in 1558.706s

FAILED (failures=29)
```

All 29 top-level failures are in `tests/test_migration_battery.py`, which this task forbids editing. No other top-level module failed. Failure headers:

```text
FAIL: test_d01_m3u6a1_census_py_reports_surviving_migrate_0_with_unruled (tests.test_migration_battery.MigrationBatteryTests.test_d01_m3u6a1_census_py_reports_surviving_migrate_0_with_unruled)
FAIL: test_d02_m3u6a1_rule_census_py_check_reports_in_sync (tests.test_migration_battery.MigrationBatteryTests.test_d02_m3u6a1_rule_census_py_check_reports_in_sync)
FAIL: test_d03_no_definition_ruled_retain_is_edited_to_remove_its (tests.test_migration_battery.MigrationBatteryTests.test_d03_no_definition_ruled_retain_is_edited_to_remove_its)
FAIL: test_d04_system_handle_and_system_request_status_still_ship (tests.test_migration_battery.MigrationBatteryTests.test_d04_system_handle_and_system_request_status_still_ship)
FAIL: test_d05_the_surviving_lifecycle_consumers_after_this_unit_are (tests.test_migration_battery.MigrationBatteryTests.test_d05_the_surviving_lifecycle_consumers_after_this_unit_are)
FAIL: test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss (tests.test_migration_battery.MigrationBatteryTests.test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss) (site='tests/test_submission.py::test_handle_still_answers_on_a_system_that_submitted_directly')
FAIL: test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss (tests.test_migration_battery.MigrationBatteryTests.test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss) (site='tests/test_system.py::test_supervised_miss_to_exact_artifact_hit')
FAIL: test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss (tests.test_migration_battery.MigrationBatteryTests.test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss) (site='tests/test_system.py::test_confirmed_request_cache_is_bound_to_immutable_example')
FAIL: test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss (tests.test_migration_battery.MigrationBatteryTests.test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss) (site='tests/test_system.py::test_concurrent_retry_observes_generation_lease')
FAIL: test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss (tests.test_migration_battery.MigrationBatteryTests.test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss) (site='tests/test_system.py::test_expired_generation_poll_is_retryable_and_handle_reclaims')
FAIL: test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss (tests.test_migration_battery.MigrationBatteryTests.test_d08_no_factory_site_gains_a_resolve_call_a_verified_miss) (site='tests/test_system.py::test_revision_cancels_in_flight_old_generation')
FAIL: test_d09_m3u6a1_fallback_py_reruns_from_committed_state_and_reports (tests.test_migration_battery.MigrationBatteryTests.test_d09_m3u6a1_fallback_py_reruns_from_committed_state_and_reports)
FAIL: test_d10_tests_test_system_py_confirm_loses_its_request_id (tests.test_migration_battery.MigrationBatteryTests.test_d10_tests_test_system_py_confirm_loses_its_request_id)
FAIL: test_d14a_tests_test_system_py_holds_two_definitions_named_confirm (tests.test_migration_battery.MigrationBatteryTests.test_d14a_tests_test_system_py_holds_two_definitions_named_confirm)
FAIL: test_d15_the_migration_lands_through_one_idempotent_script_m3u6a1 (tests.test_migration_battery.MigrationBatteryTests.test_d15_the_migration_lands_through_one_idempotent_script_m3u6a1)
FAIL: test_d24_tests_test_proposal_binding_battery_py_test_b30_and_the (tests.test_migration_battery.MigrationBatteryTests.test_d24_tests_test_proposal_binding_battery_py_test_b30_and_the) (site='tests/test_proposal_binding_battery.py::test_b30_the_six_owned_event_payloads_are_2')
FAIL: test_d24_tests_test_proposal_binding_battery_py_test_b30_and_the (tests.test_migration_battery.MigrationBatteryTests.test_d24_tests_test_proposal_binding_battery_py_test_b30_and_the) (site='tests/test_submission_battery.py::test_d03_the_event_is_proposal_created_with')
FAIL: test_d26_m3_5b_s_d01_pin_at_tests_test_cli_removal_battery_py_617 (tests.test_migration_battery.MigrationBatteryTests.test_d26_m3_5b_s_d01_pin_at_tests_test_cli_removal_battery_py_617)
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='3c832ee0c29751d40dd44d41a68fd900d8d60376')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='ea5fa430330885b315fec1fdcf43bf8c807d6f88')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='97b5d7a347ba7a55beac4175ec9f3cc4f70924e5')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='384795cb11958c998f8ae64c9653eafcf18ee564')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='2edd6dfd0993aa756fe4f3f4c3d486680b1ac635')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='294366b90495c49c764257b103b1e342f332f49e')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='cfbbe9c5a36652582932eadb35d9d010ee40f076')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='cb6e0e2dc0e6e615ae54e6c2a48a0c3f1a1d83df')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='75de6612a493b2963a993063f036b82c965bfe54')
FAIL: test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last (tests.test_migration_battery.MigrationBatteryTests.test_d28_gate_1_stays_green_at_every_commit_never_only_at_the_last) (revision='7fc7ca5bcf66e1e26f53f2583487cc051ae51258')
FAIL: test_d29_m3u6a1_premise_py_grades_its_two_premises_rather_than (tests.test_migration_battery.MigrationBatteryTests.test_d29_m3u6a1_premise_py_grades_its_two_premises_rather_than)
```
