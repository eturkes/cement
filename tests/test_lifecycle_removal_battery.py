"""M3.6a2 acceptance battery — one test per obligation in `m3u6a2-contract.md` section 3.

Authored against the contract alone. Every test must be RED at `da70a56` unless its obligation
asserts a PRESERVED invariant (L12, L14, L15, L16, L17, L18), which is legitimately green there.

Regenerate the stub set with `.agent/decisions/m3u6a2-seed-battery.py`; grade coverage with
`.agent/decisions/m3u6a2-battery-validate.py`.
"""
import unittest


class LifecycleRemovalBattery(unittest.TestCase):

    def test_l01_system_has_no_handle_attribute_and_system_py_contains_no(self) -> None:
        """L01. `System` has no `handle` attribute, and `system.py` contains no `def handle`."""

        self.skipTest("SEED STUB: L01 has no predicate yet")

    def test_l02_system_has_no_request_status_attribute(self) -> None:
        """L02. `System` has no `request_status` attribute."""

        self.skipTest("SEED STUB: L02 has no predicate yet")

    def test_l03_system_has_no__outcome__fail_generation_or(self) -> None:
        """L03. `System` has no `_outcome`, `_fail_generation` or `_request_revision_is_current` attribute."""

        self.skipTest("SEED STUB: L03 has no predicate yet")

    def test_l04_system___init___s_signature_is_exactly_self_database(self) -> None:
        """L04. `System.__init__`'s signature is exactly `self, database, *, candidate_source, clock_us`. `System(db, generation_lease_seconds=1)` raises `TypeError`. Derive the parameter list from `inspect.signature`, never from source text."""

        self.skipTest("SEED STUB: L04 has no predicate yet")

    def test_l05__lease_us_has_zero_occurrences_under_src(self) -> None:
        """L05. `_lease_us` has zero occurrences under `src/`."""

        self.skipTest("SEED STUB: L05 has no predicate yet")

    def test_l06__now_s_upper_bound_carries_no_lease_term_a_clock_returning(self) -> None:
        """L06. `_now`'s upper bound carries no lease term: a clock returning `_MAX_SQLITE_INTEGER` is ACCEPTED, `_MAX_SQLITE_INTEGER + 1` is REJECTED, and the `StateError` message does not contain `lease-safe`. Probe both sides of the boundary in one test so the assertion cannot pass by rejecting everything."""

        self.skipTest("SEED STUB: L06 has no predicate yet")

    def test_l07_revise_operation_performs_no_requests_write_its_source(self) -> None:
        """L07. `revise_operation` performs no `requests` write: its source contains no `UPDATE requests`, and a revision executed while a `generating` request row exists at the previous revision leaves that row's `status`, `error_code`, `lease_owner` and `lease_until_us` unchanged."""

        self.skipTest("SEED STUB: L07 has no predicate yet")

    def test_l08_the_operation_revised_event_payload_has_exactly_the_keys(self) -> None:
        """L08. the `operation.revised` event payload has EXACTLY the keys `previous_revision`, `policy_hash`, `revised_by`. Assert the whole key set, not the absence of one key: this payload had zero pins before this unit, so an over-narrow assertion here leaves the same blind spot the deletion exposed."""

        self.skipTest("SEED STUB: L08 has no predicate yet")

    def test_l09_zero_dangling_references_handle_request_status__outcome(self) -> None:
        """L09. zero dangling references. `handle`, `request_status`, `_outcome`, `_fail_generation`, `_request_revision_is_current` and `_lease_us` each have zero occurrences under `src/`. Count over the whole package, not over `system.py`."""

        self.skipTest("SEED STUB: L09 has no predicate yet")

    def test_l10_system_py_s_from_models_import_list_loses_exactly(self) -> None:
        """L10. `system.py`'s `from .models import (...)` list loses exactly `FallbackFailed`, `InProgress`, `Outcome`, `ReconciliationRequired`, `Rejected`, `Resolved`, `ReviewRequired` — seven names — and no other import moves. Compare the parsed import list, not the source text."""

        self.skipTest("SEED STUB: L10 has no predicate yet")

    def test_l11_the_emitted_event_kind_vocabulary_is_exactly_the_thirteen(self) -> None:
        """L11. the emitted event-kind vocabulary is EXACTLY the thirteen surviving kinds — `artifact.ambiguity_quarantined`, `artifact.compiled`, `artifact.counterexample`, `artifact.integrity_quarantined`, `artifact.promoted`, `artifact.suspended`, `artifact.verified`, `example.revoked`, `function.promoted`, `operation.registered`, `operation.revised`, `proposal.created`, `proposal.rejected` — and the `request.` prefix is gone from the namespace. Assert the whole SET, not the absence of the two deleted kinds: an absence assertion passes while a third kind is invented, and the project's own rule is to pin the complete vector rather than a derivative of it. `request.resolved_by_artifact` (`handle:1208`) and `request.fallback_failed` (`_fail_generation:1356`) are the only two emission sites either kind ever had."""

        self.skipTest("SEED STUB: L11 has no predicate yet")

    def test_l12_src_cement_runtime_models_py_is_byte_identical_to_its(self) -> None:
        """L12. `src/cement_runtime/models.py` is byte-identical to its `da70a56` blob and `src/cement_runtime/__init__.py`'s `__all__` is unchanged. The seven models survive without producers; deleting them is M3.6a3's and doing it here would take that unit's measurement with it."""

        self.skipTest("SEED STUB: L12 has no predicate yet")

    def test_l13_the_surviving_requests_sites_in_system_py_are_exactly(self) -> None:
        """L13. the surviving `requests` sites in `system.py` are exactly eleven, in `_proposal_bindings`, `_write_proposal_request_status` and `_persist_proposal`. Pin the count AND the owning method names: a count alone passes when a site moves between methods."""

        self.skipTest("SEED STUB: L13 has no predicate yet")

    def test_l14_schema_version_stays_2_and_src_cement_runtime_store_py_is(self) -> None:
        """L14. `SCHEMA_VERSION` stays 2 and `src/cement_runtime/store.py` is byte-identical to its `da70a56` blob."""

        self.skipTest("SEED STUB: L14 has no predicate yet")

    def test_l15_propose_submit_proposal_get_proposal_review_and_resolve(self) -> None:
        """L15. `propose`, `submit_proposal`, `get_proposal`, `review` and `resolve` are byte-identical to their `da70a56` spans, under the whole-line `lineno..end_lineno` convention with trailing newlines stripped. That convention is M3.3's P06 convention; a column-offset slice measures four bytes shorter and is a different claim."""

        self.skipTest("SEED STUB: L15 has no predicate yet")

    def test_l16_the_proposal_round_trip_still_ends_with_the_private(self) -> None:
        """L16. the proposal round trip still ends with the private request row `resolved`: propose, review-accept, then read the row through the store and assert `status = 'resolved'` with its `output_json` and `example_id` set. `_write_proposal_request_status` is untouched by this unit and this is the probe that proves it."""

        self.skipTest("SEED STUB: L16 has no predicate yet")

    def test_l17_revise_operation_still_bumps_the_revision_by_one_and_still(self) -> None:
        """L17. `revise_operation` still bumps the revision by one and still retires `draft`, `verified` and `promoted` artifacts at the previous revision with `status_reason = 'operation revised'`."""

        self.skipTest("SEED STUB: L17 has no predicate yet")

    def test_l18__now_still_rejects_a_non_int_a_bool_a_negative_value_and_a(self) -> None:
        """L18. `_now` still rejects a non-`int`, a `bool`, a negative value and a non-callable `clock_us`, and every surviving caller of `_now` is unchanged."""

        self.skipTest("SEED STUB: L18 has no predicate yet")

    def test_l19_readme_md_names_neither_handle_nor_request_status_carries(self) -> None:
        """L19. `README.md` names neither `handle` nor `request_status`, carries no poll-state table and no lease configuration, and its request-route section describes the proposal route instead."""

        self.skipTest("SEED STUB: L19 has no predicate yet")

    def test_l20_docs_architecture_md_steps_1_3_describe_propose_review_the(self) -> None:
        """L20. `docs/architecture.md` steps 1-3 describe `propose`/`review`; the lease paragraph is gone."""

        self.skipTest("SEED STUB: L20 has no predicate yet")

    def test_l21_docs_adapter_protocol_md_names_no_deleted_surface_m3_7(self) -> None:
        """L21. `docs/adapter-protocol.md` names no deleted surface. M3.7 relocates this file under byte equality, so it must be correct HERE."""

        self.skipTest("SEED STUB: L21 has no predicate yet")

    def test_l22_docs_threat_model_md_no_longer_claims_a_handle_request_id(self) -> None:
        """L22. `docs/threat-model.md` no longer claims a `handle` request ID as an idempotency key and no longer describes lease recovery; whatever replaces each claim describes surviving behaviour."""

        self.skipTest("SEED STUB: L22 has no predicate yet")

    def test_l23_all_15_census_pins_in_section_5_are_green_after_the(self) -> None:
        """L23. all 15 census pins in section 5 are green after the rewrite, each either satisfied by the new prose or re-scoped with grounds recorded in section 8."""

        self.skipTest("SEED STUB: L23 has no predicate yet")

    def test_l24_no_human_facing_surface_gains_a_new_claim_about_a_deleted(self) -> None:
        """L24. no human-facing surface gains a NEW claim about a deleted surface. Re-run the census (`gate 3`) against the rewritten documents and require the owned hit count to be zero for every vocabulary token naming a deleted surface."""

        self.skipTest("SEED STUB: L24 has no predicate yet")

    def test_l25_m3_5b_s_d15a_tests_test_cli_removal_battery_py_1131(self) -> None:
        """L25. M3.5b's D15a (`tests/test_cli_removal_battery.py:1131`, assertion `:1158`) is re-scoped to the closed range `36f7890..1146421`, exactly as M3.6a1 re-scoped its siblings D15b (`:1160`) and D22b (`:2766`). The repair is a family repair: after it, no D15/D22 clause reads the working tree for a runtime module."""

        self.skipTest("SEED STUB: L25 has no predicate yet")

    def test_l26_the_four_p06_span_freezes_are_retired_with_their_history(self) -> None:
        """L26. the four P06 span freezes are RETIRED with their history preserved, not re-based: they freeze the bytes of a method that no longer exists. Each retirement records the frozen figures it carried (`12,866 B / 1182130a2b3a`, `12,867 B / cd60036faf5c`, `12,862 B / c27e71b0b4c7`) so the claim stays checkable against history, and L15 is what replaces their protective value for the methods that survive."""

        self.skipTest("SEED STUB: L26 has no predicate yet")

    def test_l27_m3_5b_s_d01_tests_test_cli_removal_battery_py_608(self) -> None:
        """L27. M3.5b's D01 (`tests/test_cli_removal_battery.py:608`, assertions `:617` + `:618`) is INVERTED: it asserted `System.handle` and `System.request_status` still ship as library methods; it now asserts their absence. An inverted pin keeps the obligation and reverses the predicate; deleting it would delete the behaviour's only pin along with the behaviour."""

        self.skipTest("SEED STUB: L27 has no predicate yet")

    def test_l28_tests_test_authority_removal_py_118(self) -> None:
        """L28. `tests/test_authority_removal.py:118 test_system_constructor_shape` is rewritten to the three-parameter signature and keeps asserting defaults for the parameters that remain."""

        self.skipTest("SEED STUB: L28 has no predicate yet")

    def test_l29_m3u6a2_tripwires_py_s__freezes_detector_is_widened_to_see(self) -> None:
        """L29. `m3u6a2-tripwires.py`'s `_freezes()` detector is widened to see the P06 family, behind a self-test control that FIRES on a P06 frame. Today it requires the literal `cement_runtime/system.py` or `System.handle` AND one of `read_bytes()`/`getsource`/`_git_bytes(`, while the four P06 frames reach the same source through `cement_runtime.system.__file__`, `inspect.getsourcefile(System)` and a `_source(ROOT, path)` helper — so the instrument reported `FREEZES: 4` over a set DISJOINT from the four freezes this unit actually inverts, and its 6/6 self-test covered none of that negative space. If widening proves to over-report, record the exclusion with grounds instead; what is not acceptable is leaving a detector whose name promises the family it cannot see."""

        self.skipTest("SEED STUB: L29 has no predicate yet")

    def test_l30_m3_6a1_s_d16_tests_test_migration_battery_py_993_is_re(self) -> None:
        """L30. M3.6a1's D16 (`tests/test_migration_battery.py:993`) is re-scoped to the CLOSED range `6fb4d92..dc4ab5e` — M3.6a1's baseline and its own DONE tip — on BOTH halves: the expected path set and the per-path byte comparison, which read `HEAD` and the working tree respectively. Read against `HEAD`, D16 asserted that M3.6a1's surgery script reproduces every LATER unit's `tests/` and `examples/` edits, which no script pinned to an earlier baseline can do. It is the same family as D15a (L25), and it is stricter: D15a inverts when this unit EDITS a runtime module, while D16 inverts when this unit ADDS ANY FILE under `tests/` or `examples/` — the battery seed alone tripped it. Its repair therefore lands BEFORE every other edit rather than beside them."""

        self.skipTest("SEED STUB: L30 has no predicate yet")
