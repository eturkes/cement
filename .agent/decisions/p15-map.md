# p15 probe map

Baseline = `95f75b6fea26a0ecaeadfe0e0f1475348b1b172e`. Verdicts = 17 subsumed / 8 gap / 3 obsolete.

Classification = behavioral conjuncts, not stale fixture syntax. All cited function bodies match HEAD byte-for-byte. Anchors = line numbers in the landing tree: re-anchored from `809e779` (where all 52 fenced anchors resolved) by an exact-line `difflib` map, 57 table + 52 fenced anchors, 0 misses; `uv run python .agent/validate-anchors .agent/decisions/p15-map.md` rc 0. `.scratch/` paths below = the mapping run's machine-local workspace; the 8 gap probes ship as `tests/test_cli.py` tests (MAINTAIN p15). Multiple shipped ids denote explicit compositional coverage; a gap names the uncovered conjunct, not a blanket absence of related tests.

P18 display substitutes `[absent]` for its original lookup-miss token because the required unfinished-cell grep also matches that token in the source method name. Probe order + P18 id are unchanged.

| id | probe | asserts (one line) | verdict | shipped test id | evidence |
|---|---|---|---|---|---|
| P01 | `test_parser_surface_appends_export_after_promote` | Parser accepts export + default receipt None; export is the final function leaf after promote. | obsolete | none | Old ordering retired: switch/versions/diff/eval follow export; `src/cement_runtime/cli.py:253`; root also gained projection/learn. Export grammar itself remains. |
| P02 | `test_missing_operation_is_usage_error` | Missing operation → exit 2, byte-empty stdout, exact invalid envelope. | subsumed | `tests.test_cli.CLITests.test_function_export_rejects_options_it_does_not_own` | `tests/test_cli.py:3811`; `tests/test_cli.py:3814` |
| P03 | `test_unsupported_leaf_flags_are_usage_errors` | --out/--expected-function-hash/--projection-limit are rejected with exact usage errors. | obsolete | none | --out is now the supported atomic-file channel: `src/cement_runtime/cli.py:251`. Remaining two rejections still pinned at `tests/test_cli.py:3808` |
| P04 | `test_missing_db_or_partition_is_usage_error` | Export requires db + partition, with exact usage envelopes and byte-empty stdout. | gap | none | Resolve-only global-gate coverage exists at `tests/test_cli_channels.py:520`; no shipped export invocation omits either global. Port p04. |
| P05 | `test_live_healthy_exports_exact_bytes_and_round_trips` | Live export is byte-exact/no BOM/no trailing newline, stderr-empty, hash-preserving and evaluable. | subsumed | `tests.test_cli.CLITests.test_function_export_writes_the_live_document_bytes_exactly`<br>`tests.test_cli.CLITests.test_function_export_round_trips_through_parse_function` | `tests/test_cli.py:3248`; `tests/test_cli.py:3407`; `tests/test_cli.py:3410`. Exact equality excludes BOM; extra miss asserted too. |
| P06 | `test_live_unicode_is_byte_exact_on_buffer_and_text_stdout` | Unicode export has identical literal UTF-8 bytes on binary and text-only stdout hosts. | gap | none | Unicode exactness pins binary only at `tests/test_cli.py:3425`; text-host pin uses integer fixtures at `tests/test_cli.py:3253`. Unicode × text-host unasserted. Port p06. |
| P07 | `test_live_empty_set_exports_real_document` | Registered empty live set exports the real empty document and its hash, without framing bytes. | subsumed | `tests.test_cli.CLITests.test_function_export_of_an_empty_promoted_set_exports_its_document` | `tests/test_cli.py:3433`; `tests/test_cli.py:3435`. Byte identity includes document hash + framing; ABI + operation also pinned. |
| P08 | `test_live_drift_emits_full_ordered_error_and_no_bytes` | Real drift → exit 6, byte-empty stdout, entire ordered check vector and exact pretty-JSON stderr. | gap | none | Shipped drift test pins keys/booleans + failing message, not every check detail or stderr serialization: `tests/test_cli.py:3464`. Port p08 retains purpose with HEAD's seventh projection check. |
| P09 | `test_injected_multi_failure_message_uses_only_failures_in_order` | Injected mixed verdict → failing-only ordered message plus every check's key/passed/detail, no extra fields. | gap | none | Shipped injection checks vector keys only: `tests/test_cli.py:3495`. Passed/detail preservation unasserted for the mixed injected vector. Port p09. |
| P10 | `test_unverified_exception_shape_and_exit_shadowing` | _Unverified is an Exception outside CementError; refused export stays exit 6/unverified. | subsumed | `tests.test_cli.CLITests.test_unverified_stays_outside_the_cement_error_hierarchy`<br>`tests.test_cli.CLITests.test_function_export_preserves_the_symbol_qualified_exit_map` | `tests/test_cli.py:3506`; `tests/test_cli.py:3535`; `tests/test_cli.py:3540` |
| P11 | `test_live_source_is_exclusive_and_forwards_exact_scope` | Live export calls public verify_function exactly once with exact scope and never reconstructs history. | obsolete | none | Live source replaced by switch-aware serving: `src/cement_runtime/cli.py:1098`. Public verify_function is not the export dispatch boundary; follow/pinned/off select the result. |
| P12 | `test_historical_source_is_exclusive_and_forwards_exact_scope` | Historical export reconstructs exactly once with partition + receipt only; never uses live verification. | gap | none | Forwarding pins only the final call args at `tests/test_cli.py:3687`; source exclusion at `tests/test_cli.py:3565`. Reconstruction call count unasserted. Port p12. |
| P13 | `test_export_never_inspects_prospective_union` | Neither live nor historical export calls inspect_function_promotion. | gap | none | No export test patches prospective inspection; shipped source-separation test only compares documents at `tests/test_cli.py:3699`. Port p13. |
| P14 | `test_unregistered_and_foreign_partition_live_scope_are_not_found` | Live lookup rejects absent + foreign scope, including underscore/case collisions, with exact not-found error. | gap | none | Shipped live export misses use ghost + tenant_other, not collision fixtures: `tests/test_cli.py:3547`. Library report/receipt collision tests target different queries. Port p14. |
| P15 | `test_historical_own_receipt_exports_exact_bytes_and_round_trips` | Own historical receipt exports exact reconstruction bytes, parses to its hash and evaluates a stored input. | subsumed | `tests.test_cli.CLITests.test_function_export_exports_one_historical_receipt`<br>`tests.test_cli.CLITests.test_function_export_round_trips_through_parse_function`<br>`tests.test_system.SystemTests.test_reconstruct_function_receipt_matches_promoted_manifest_bytes_hash_order_and_exclusion` | `tests/test_cli.py:3568`; `tests/test_system.py:10628`; `tests/test_cli.py:3410`. Composite: identical sealed document + public parse/evaluate boundary. |
| P16 | `test_historical_foreign_operation_uses_cross_check_message` | Foreign-operation receipt → exit 3, byte-empty stdout, exact operation-cross-check message. | subsumed | `tests.test_cli.CLITests.test_function_export_cross_checks_the_receipt_operation_exactly` | `tests/test_cli.py:3578`; `tests/test_cli.py:3584` |
| P17 | `test_historical_operation_cross_check_is_exact_and_like_safe` | Receipt operation equality is exact across underscore + case collisions, with an exact positive control. | subsumed | `tests.test_cli.CLITests.test_function_export_cross_checks_the_receipt_operation_exactly` | `tests/test_cli.py:3575`; `tests/test_cli.py:3574`. Collision direction reversed; same exact-comparison obligation + extra prefix/suffix cases. |
| P18 | `test_historical_[absent]_typo_and_wrong_partition_are_not_found` | Missing/malformed-looking/foreign-partition receipt ids → exact not-found; partition equality resists LIKE collisions. | subsumed | `tests.test_cli.CLITests.test_function_export_reports_a_missing_receipt_row_separately`<br>`tests.test_cli.CLITests.test_function_export_forwards_the_operator_scope_exactly`<br>`tests.test_system.SystemTests.test_reconstruct_function_receipt_partition_lookup_is_case_and_like_exact` | `tests/test_cli.py:3606`; `tests/test_system.py:13258`; `tests/test_cli.py:3687`. Composite: CLI exact forwarding/error + library collision isolation. |
| P19 | `test_receipt_id_bounds_are_adjacent_and_empty_is_invalid` | Receipt length 192 reaches lookup; empty/193 reject as invalid with exact bounded-id message. | subsumed | `tests.test_cli.CLITests.test_function_export_bounds_the_receipt_id_grammar`<br>`tests.test_cli.CLITests.test_function_export_reports_a_missing_receipt_row_separately` | `tests/test_cli.py:3612`; `tests/test_cli.py:3626`; `tests/test_cli.py:3628`. Missing-row test supplies the exact lookup message. |
| P20 | `test_historical_corruption_maps_to_integrity` | Corrupt receipt membership → exit 5/integrity, exact digest-mismatch message, byte-empty stdout. | subsumed | `tests.test_cli.CLITests.test_function_export_reports_a_corrupt_receipt_as_integrity` | `tests/test_cli.py:3639`; `tests/test_cli.py:3645` |
| P21 | `test_live_passed_without_document_maps_to_integrity` | Passing live verdict without a document → exact integrity envelope, exit 5, byte-empty stdout. | subsumed | `tests.test_cli.CLITests.test_function_export_guards_a_passing_verification_without_a_document` | `tests/test_cli.py:3659`; `tests/test_cli.py:3665` |
| P22 | `test_library_exception_exit_map_and_empty_stdout` | Each export source preserves Validation/NotFound/State/Integrity exits + exact error token/message, stdout empty. | gap | none | Shipped matrix patches live serving only and its non-6 token comparison is tautological: `tests/test_cli.py:3540`. Historical branch lacks the four-class injected matrix. Port p22. |
| P23 | `test_cross_revision_history_exports_old_bytes_while_live_moves` | After revision, history keeps old bytes/revision while live exports the new empty revision. | subsumed | `tests.test_cli.CLITests.test_function_export_serves_a_receipt_from_a_superseded_revision` | `tests/test_cli.py:3729`; `tests/test_cli.py:3733`. Exact document/round-trip properties supplied by P05/P15 coverage. |
| P24 | `test_historical_reconstructs_before_operation_cross_check` | Corrupt foreign receipt reports integrity before the requested-operation cross-check. | subsumed | `tests.test_cli.CLITests.test_function_export_reports_a_corrupt_receipt_as_integrity` | `tests/test_cli.py:3634`; `tests/test_cli.py:3639` |
| P25 | `test_old_receipt_and_live_source_diverge_after_new_promotion` | New promotion moves live bytes/hash but keeps the older receipt immutable. | subsumed | `tests.test_cli.CLITests.test_function_export_sources_never_mix`<br>`tests.test_cli.CLITests.test_function_export_writes_the_live_document_bytes_exactly` | `tests/test_cli.py:3700`; `tests/test_cli.py:3701`; `tests/test_cli.py:3704`. Different sealed entry tables imply distinct verified hashes; live exact bytes pinned by P05. |
| P26 | `test_historical_export_survives_current_live_drift` | Historical export survives a suspended member while the live set is refused. | subsumed | `tests.test_cli.CLITests.test_function_export_exports_one_historical_receipt`<br>`tests.test_cli.CLITests.test_function_export_refuses_a_drifted_set_with_the_whole_check_vector`<br>`tests.test_system.SystemTests.test_reconstruct_function_receipt_survives_revocation_of_every_member_evidence_row` | `tests/test_cli.py:3565`; `tests/test_system.py:11024`; `tests/test_system.py:11037`; `tests/test_cli.py:3446`. Composite: historical excludes serving; reconstruction survives suspension of every member; CLI live refusal. |
| P27 | `test_positive_paths_keep_stderr_empty_and_omit_trailing_newline` | Both successful stdout export sources emit nonempty bytes without newline and leave stderr empty. | subsumed | `tests.test_cli.CLITests.test_function_export_writes_the_live_document_bytes_exactly`<br>`tests.test_cli.CLITests.test_function_export_exports_one_historical_receipt` | `tests/test_cli.py:3249`; `tests/test_cli.py:3569`; both compare nonempty documents and stderr to empty. |
| P28 | `test_negative_paths_keep_stdout_byte_empty` | Absent/usage/negative-verdict/integrity export failures yield exits 3/2/6/5 with byte-empty stdout and stderr errors. | subsumed | `tests.test_cli.CLITests.test_function_export_rejects_an_unregistered_or_foreign_operation`<br>`tests.test_cli.CLITests.test_function_export_rejects_options_it_does_not_own`<br>`tests.test_cli.CLITests.test_function_export_preserves_the_symbol_qualified_exit_map`<br>`tests.test_cli.CLITests.test_function_export_reports_a_corrupt_receipt_as_integrity` | `tests/test_cli.py:3551`; `tests/test_cli.py:3811`; `tests/test_cli.py:3536`; `tests/test_cli.py:3640` |

## Verification + coverage limits

- Seed checks: unfinished-cell scan = 28 rows, rc 0; anchor validator = no anchors, rc 4. Expected negatives.
- Search: all shipped test modules inventoried; export-bearing modules searched; relevant CLI/shared-error/receipt/switch bodies read. No full-suite claim. Shipped comparison = source assertions, not a full run.
- Port = `.scratch/p15/ported.py`, own-method load_tests = eight tests only; setUp owns scratch-local temporary ledgers. Original handle fixture replaced by proposal submission; live mocks target serving + follow enabled; drift uses seven current checks. Preservation probes, not red-first regression credentials; mutation credit not run.
- Port result: `PYTHONDONTWRITEBYTECODE=1 uv run python .scratch/p15/ported.py` → rc 0, 8 tests, 3.256 s, OK; skipped none. Log = `.scratch/p15/ported.log`. Final checks: unfinished-cell grep → no output/rc 1; anchor validator → rc 0, 52 checked/0 bad/0 unfilled. No full suite or gate run.
- No suspected production defect. P22's existing non-6 token assertion is tautological; tracked test left unchanged. Superseded historical vector/order/flag assumptions are not proposed as new requirements.

```anchors
src/cement_runtime/cli.py	251	"--out", help="write the bundle atomically to PATH instead of stdout"
src/cement_runtime/cli.py	253	function_switch = function_commands.add_parser("switch", allow_abbrev=False)
src/cement_runtime/cli.py	1098	state, served = system.serving(args.partition, args.operation)
tests/test_cli.py	3248	self.assertEqual(run.stdout_bytes, expected)
tests/test_cli.py	3249	self.assertFalse(run.stdout_bytes.endswith(b"\n"))
tests/test_cli.py	3253	self.assertEqual(text_host.stdout_bytes, expected)
tests/test_cli.py	3407	self.assertEqual(parsed.function_hash, verification.function_hash)
tests/test_cli.py	3410	self.assertEqual(match.output, {"kind": "echo", "value": {"x": 1}})
tests/test_cli.py	3425	self.assertEqual(run.stdout_bytes, self.live_document("unicode").encode("utf-8"))
tests/test_cli.py	3433	self.assertEqual(run.stdout_bytes, self.live_document("empty").encode("utf-8"))
tests/test_cli.py	3435	self.assertEqual(document["entries"], [])
tests/test_cli.py	3446	self.assertEqual(run.status, 6)
tests/test_cli.py	3464	self.assertEqual([check["passed"] for check in checks], [True] * 5 + [False, True])
tests/test_cli.py	3495	self.assertEqual([check["key"] for check in checks], ["first", "second", "third"])
tests/test_cli.py	3506	self.assertFalse(issubclass(_Unverified, CementError))
tests/test_cli.py	3535	self.assertEqual(run.status, expected)
tests/test_cli.py	3536	self.assertEqual(run.stdout_bytes, b"")
tests/test_cli.py	3540	"unverified" if expected == 6 else self.error(run)["error"],
tests/test_cli.py	3547	(("function", "export", "echo_1"), "tenant_other"),
tests/test_cli.py	3551	self.assertEqual(run.stdout_bytes, b"")
tests/test_cli.py	3565	self.assertEqual(never.call_count, 0)
tests/test_cli.py	3568	self.assertEqual(run.stdout_bytes, reconstruction.document.text.encode("utf-8"))
tests/test_cli.py	3569	self.assertFalse(run.stdout_bytes.endswith(b"\n"))
tests/test_cli.py	3574	self.assertEqual(accepted.status, 0)
tests/test_cli.py	3575	for operation in ("echoX1", "ECHO_1", "echo", "echo_12"):
tests/test_cli.py	3578	self.assertEqual(run.status, 3)
tests/test_cli.py	3584	"message": "function receipt does not exist for this operation",
tests/test_cli.py	3606	"message": "function receipt does not exist in this partition",
tests/test_cli.py	3612	for receipt_id in ("", "a" * 193, "fpr_x!y"):
tests/test_cli.py	3626	accepted = self.run_cli("function", "export", "echo", "--receipt-id", "a" * 192)
tests/test_cli.py	3628	self.assertEqual(self.error(accepted)["error"], "not_found")
tests/test_cli.py	3634	for operation in ("beta", "echo_1"):
tests/test_cli.py	3639	self.assertEqual(run.status, 5)
tests/test_cli.py	3640	self.assertEqual(run.stdout_bytes, b"")
tests/test_cli.py	3645	"message": "function receipt membership digest mismatch",
tests/test_cli.py	3659	self.assertEqual(run.status, 5)
tests/test_cli.py	3665	"message": "function verification passed without an exportable document",
tests/test_cli.py	3687	self.assertEqual(historical.call_args.args[1:], ("tenant", receipt))
tests/test_cli.py	3699	self.assertNotEqual(live.stdout_bytes, historical.stdout_bytes)
tests/test_cli.py	3700	self.assertEqual(len(json.loads(historical.stdout_text)["entries"]), 2)
tests/test_cli.py	3701	self.assertEqual(len(json.loads(live.stdout_text)["entries"]), 3)
tests/test_cli.py	3704	self.assertEqual(again.stdout_bytes, historical.stdout_bytes)
tests/test_cli.py	3729	self.assertEqual(after.stdout_bytes, historical.stdout_bytes)
tests/test_cli.py	3733	self.assertEqual(json.loads(live.stdout_text)["scope"]["operation_revision"], 2)
tests/test_cli.py	3808	self.assertEqual(self.error(run), {"error": "invalid", "message": message})
tests/test_cli.py	3811	self.assertEqual(missing.stdout_bytes, b"")
tests/test_cli.py	3814	{"error": "invalid", "message": "the following arguments are required: operation"},
tests/test_cli_channels.py	520	self.assertEqual((input_.call_count, system.call_count), (0, 0))
tests/test_system.py	10628	self.assertEqual(rebuilt.document, manifest.document)
tests/test_system.py	11024	self.assertEqual(rebuilt.text, manifest.document.text)
tests/test_system.py	11037	self.assertEqual(statuses, ("suspended", "suspended", "suspended"))
tests/test_system.py	13258	("tenantXpublic", "tenant_public", "like-public"),
```

general-purpose-1-DONE-1
