"""M3.6a2 acceptance battery — one test per obligation in `m3u6a2-contract.md` section 3.

Authored against the contract alone. Every test must be RED at `da70a56` unless its obligation
asserts a PRESERVED invariant (L12, L14, L15, L16, L17, L18), which is legitimately green there.

Regenerate the stub set with `.agent/decisions/m3u6a2-seed-battery.py`; grade coverage with
`.agent/decisions/m3u6a2-battery-validate.py`.
"""
import unittest


class LifecycleRemovalBattery(unittest.TestCase):

    def test_l01_system_has_no_handle_attribute_under_every_access_route(self) -> None:
        """L01. `System` has no `handle` attribute under EVERY access route — `hasattr`, `getattr`, `dir()`, `inspect.getmembers` — neither `System` nor its metaclass defines `__getattr__`, and `system.py` holds no `FunctionDef` named `handle` at any scope. PLUS the structural subtraction (A01): the post-state `System` method-name set EQUALS its `da70a56` set minus exactly `{handle, request_status, _outcome, _fail_generation, _request_revision_is_current}`. A text predicate grades the spelling; only the set subtraction grades the subtraction, and renaming the 271-line body satisfies every text half."""

        self.skipTest("SEED STUB: L01 has no predicate yet")

    def test_l02_system_has_no_request_status_attribute_under_the_same_four(self) -> None:
        """L02. `System` has no `request_status` attribute under the same four routes and no `FunctionDef` named `request_status` at any scope. The surviving `_ProposalBinding.request_status` field and the six other proposal-plumbing identifiers are a DIFFERENT subject and must remain (X01, L15)."""

        self.skipTest("SEED STUB: L02 has no predicate yet")

    def test_l03_system_has_no__outcome__fail_generation_or(self) -> None:
        """L03. `System` has no `_outcome`, `_fail_generation` or `_request_revision_is_current` attribute, and `system.py` holds zero `FunctionDef` of each name at any scope — module level, class body and nested closure alike (V02)."""

        self.skipTest("SEED STUB: L03 has no predicate yet")

    def test_l04_system___init___s_signature_is_exactly_self_database(self) -> None:
        """L04. `System.__init__`'s signature is exactly `self, database, *, candidate_source, clock_us`. `System(db, generation_lease_seconds=1)` raises `TypeError`. Derive the parameter list from `inspect.signature`, never from source text."""

        self.skipTest("SEED STUB: L04 has no predicate yet")

    def test_l05__lease_us_has_zero_raw_byte_occurrences_across_the_git(self) -> None:
        """L05. `_lease_us` has zero RAW BYTE occurrences across the git-tracked `src/` file set — the contract says occurrences, so strings, comments and docstrings count, and git-tracked scope excludes `__pycache__` (V05). Baseline 5, all in `system.py` at 702, 709, 1099, 1110, 1235. Token absence alone is satisfied by a rename, so L05 carries the AST SHAPE pin that a rename cannot (A03): `_now`'s comparator is exactly `now > _MAX_SQLITE_INTEGER` — the right operand is a bare `Name`, not a `BinOp` — and `__init__` binds no attribute whose value derives from a lease parameter. `generation_lease_seconds` likewise reaches zero raw occurrences across tracked `src/` (X03; baseline 5), since `inspect.signature` cannot see a dead literal or comment."""

        self.skipTest("SEED STUB: L05 has no predicate yet")

    def test_l06__now_s_upper_bound_carries_no_lease_term_a_clock_returning(self) -> None:
        """L06. `_now`'s upper bound carries no lease term: a clock returning `_MAX_SQLITE_INTEGER` is ACCEPTED and reaches a real write, `_MAX_SQLITE_INTEGER + 1` is REJECTED, and the `StateError` message is EXACTLY `clock must return a signed 64-bit microsecond timestamp`. Probe both sides of the boundary in one test so the assertion cannot pass by rejecting everything. The positive text pin is MAIN's own wording, not a diff-blind paraphrase, and it exists because a forbidden-substring predicate cannot see a silent re-wording (V07, V22). The dead `lease-safe` literal must also be absent from tracked `src/` (X27)."""

        self.skipTest("SEED STUB: L06 has no predicate yet")

    def test_l07_revise_operation_performs_no_requests_write_the_source(self) -> None:
        """L07. `revise_operation` performs no `requests` write. The source half scans AST string constants case-insensitively and rejects every spelling — `UPDATE`/`update`, arbitrary whitespace, a multiline split, and `` `requests` ``, `"requests"`, `[requests]`, `main.requests`, `temp.requests` (V10). The behavioural half executes a revision while a `generating` request row exists at the previous revision and asserts that row's `status`, `error_code`, `lease_owner` and `lease_until_us` are unchanged. THAT ROW IS FABRICATED LEGACY STATE and is labelled as such: after this unit no supported route produces `generating`, so the probe seeds it through `Store.transaction(write=True)`, modelling a ledger left by an older release at surviving schema v2 (V09, X28). The probe MUST assert the row exists at `status='generating'` BEFORE the revision — a zero-row UPDATE raises nothing, so an unguarded preservation probe is green-and-empty rather than red (A05)."""

        self.skipTest("SEED STUB: L07 has no predicate yet")

    def test_l08_the_operation_revised_event_payload_read_back_from_the(self) -> None:
        """L08. the `operation.revised` event payload, read back from the persisted `events.payload_json`, has EXACTLY the keys `previous_revision`, `policy_hash`, `revised_by` AND each key's VALUE is bound: `previous_revision` == the operation's pre-revision integer, `policy_hash` == the canonical policy digest, `revised_by` == the actor the caller supplied. Assert the whole key set, not the absence of one key, and assert the values, not just the keys: a three-key set assertion passes while all three values are wrong (A06), and `revise_operation` returns only the new revision, so the return value cannot evidence the payload. This payload had zero pins before this unit. `invalidated_generators` additionally reaches zero RAW occurrences across tracked `src/` — baseline 3, being one assignment, one payload key STRING and one value identifier, which is why the census's `2` (NAME tokens) is not the closure number (X04)."""

        self.skipTest("SEED STUB: L08 has no predicate yet")

    def test_l09_zero_dangling_references_counted_as_tokenize_name_equality(self) -> None:
        """L09. zero dangling references, counted as `tokenize` NAME equality over tracked `src/` `.py` files so `handler` and `unhandled` never count. The expected post-state vector is `{handle: 0, request_status: 7, _outcome: 0, _fail_generation: 0, _request_revision_is_current: 0, _lease_us: 0}` (X02, X24; baseline `1, 8, 7, 4, 4, 5`). `request_status` IS NOT ZERO and cannot be: MAIN measured eight identifiers at `da70a56`, of which deleting the method removes line 1546 alone, leaving SEVEN proposal-plumbing identifiers at 458, 503, 1529, 1532, 1535, 1542 and 1579 — the last inside `get_proposal`, which L15 freezes byte-for-byte. The original `zero occurrences` reading was false-by-construction against L15 and is corrected by C09; L02 carries the `System`-attribute claim instead. Dynamic reach is closed by a bounded, MEASURED pin (A07): tracked `src/` holds ZERO `getattr`/`setattr`/`hasattr`/`delattr` calls whose name argument is not a string `Constant`, which rejects `getattr(self, '_out' + 'come')` by construction. Count over the whole package, not over `system.py`."""

        self.skipTest("SEED STUB: L09 has no predicate yet")

    def test_l10_system_py_s_from_models_import_list_loses_exactly(self) -> None:
        """L10. `system.py`'s `from .models import (...)` list loses exactly `FallbackFailed`, `InProgress`, `Outcome`, `ReconciliationRequired`, `Rejected`, `Resolved`, `ReviewRequired` — seven names — and no other import moves. Compare the parsed import list, not the source text."""

        self.skipTest("SEED STUB: L10 has no predicate yet")

    def test_l11_the_emitted_event_kind_vocabulary_is_exactly_the_sixteen(self) -> None:
        """L11. the emitted event-kind vocabulary is EXACTLY the SIXTEEN surviving kinds — `artifact.challenged`, `artifact.compiled`, `artifact.counterexample`, `artifact.integrity_quarantined`, `artifact.promoted`, `artifact.suspended`, `artifact.verification_failed`, `artifact.verified`, `example.revoked`, `function.promoted`, `operation.registered`, `operation.revised`, `proposal.accepted`, `proposal.corrected`, `proposal.created`, `proposal.rejected` — and the `request.` prefix is gone from the namespace. Assert the whole SET, not the absence of the deleted kinds: an absence assertion passes while a further kind is invented, and the project's own rule is to pin the complete vector rather than a derivative of it. Corrected by C05; the count and three of the members moved. THE DERIVATION IS TOTAL, NOT BEST-EFFORT (A09, X05): every `_event` call's `kind` argument must match one of the three ruled AST forms and must expand non-empty, and an unsupported form FAILS the check rather than being skipped. Set equality alone stays green when a fourth form (`kind=event_kind`) ships a new runtime kind, because the recognized set is unchanged. THE VOCABULARY HAS THREE SPELLINGS AND A RULE READING ONE IS BLIND TO THE REST. Every event is written by the module-level `_event(connection, *, kind=..., ...)` helper (`system.py:380`), called NINETEEN times at `da70a56` — 16 `Constant`, 2 `IfExp`, 1 `JoinedStr`, falling to FOURTEEN post-state — and its `kind` argument takes three forms: a plain string constant; an `IfExp` whose two branches are both constants (`kind="artifact.verified" if passed else "artifact.verification_failed"` at `_verify_row:4065`, `kind="artifact.counterexample" if suspended else "artifact.challenged"` at `challenge:5129`); and one `JoinedStr`, `kind=f"proposal.{proposal_status}"` at `review:1881`, whose interpolation is annotated `Literal["accepted", "corrected"]` at `system.py:1770` and is resolved from THAT lexical function, never from a module-wide same-name search (X29). Derive the set from all three; a scan reading only the first reports 13 of the 16 and is what C05 corrects. C05's own supporting count of `20` was wrong and is corrected by C08: 19 static calls, the textual `_event(` count of 20 including the DEFINITION line. The 16-kind SET is unaffected because it was derived per call site, and the call count is REPORTED separately rather than used as a completeness control. Each of the three removed kinds loses its unique producer independently (X32). THREE KINDS LOSE THEIR ONLY PRODUCER HERE, not two. `request.resolved_by_artifact` (`handle:1208`), `request.fallback_failed` (`_fail_generation:1356`) AND `artifact.ambiguity_quarantined` (`handle:1143`) are each emitted at exactly one site, all three inside deleted spans. Ambiguity quarantine is therefore a behaviour this unit removes, which section 2's deletion set and the prose census both now record."""

        self.skipTest("SEED STUB: L11 has no predicate yet")

    def test_l12_src_cement_runtime_models_py_is_byte_identical_to_its(self) -> None:
        """L12. `src/cement_runtime/models.py` is byte-identical to its `da70a56` blob (sha256 `6dd45cfb6b078636dcdd8ae2d89b35603b727f53cc8ca32a3574647db0838289`) and `src/cement_runtime/__init__.py`'s `__all__` — compared as the PARSED ordered list of 57 names, not as source text — is unchanged (V16). PLUS binding identity (A08): each of the six exported model names resolves in `cement_runtime` to the SAME OBJECT as in `cement_runtime.models`, which an aliasing re-export (`from .models import Resolved as _Resolved`) breaks while `__all__` stays AST-equal. The post-state vector is six names at `(models=True, __all__=True, package=True, system=False)` and `Outcome` at `(True, False, False, False)` — SEVEN definitions, SIX exports (X06, X34, C10). The models survive without producers; deleting them is M3.6a3's and doing it here would take that unit's measurement with it."""

        self.skipTest("SEED STUB: L12 has no predicate yet")

    def test_l13_the_surviving_requests_sites_in_system_py_are_exactly(self) -> None:
        """L13. the surviving `requests` sites in `system.py` are exactly SEVEN — `_proposal_bindings` 4, `_write_proposal_request_status` 2, `_persist_proposal` 1 — pinned by THREE instruments whose disagreement is the finding: hit LINES (7), standalone WORD occurrences (7, per-line multiplicity 1, so a second reference cannot be packed onto an existing line — X20), and parsed SQL string CONSTANTS with their verbs (`SELECT` x4, `UPDATE` x2, `INSERT` x1), which excludes comments and docstrings and follows a statement moved to a new line (X30). Ownership binds to the NEAREST lexical `FunctionDef`, never to an outer `ast.walk`, and the pin compares the exact multiset `{owner: count}` PLUS owner KIND, so a site relocated into a newly nested helper fails instead of being attributed to the expected outer function (A12). Corrected by C04 from `eleven`, which contradicted section 1's own inventory. Corrected again by C09: `_proposal_bindings` and `_write_proposal_request_status` are module-level FUNCTIONS but `_persist_proposal` is a `System` METHOD, so a class-body-only scan sees ONE surviving site, not zero."""

        self.skipTest("SEED STUB: L13 has no predicate yet")

    def test_l14_schema_version_stays_2_and_src_cement_runtime_store_py_is(self) -> None:
        """L14. `SCHEMA_VERSION` stays 2 and `src/cement_runtime/store.py` is byte-identical to its `da70a56` blob."""

        self.skipTest("SEED STUB: L14 has no predicate yet")

    def test_l15_propose_submit_proposal_get_proposal_review_and_resolve(self) -> None:
        """L15. `propose`, `submit_proposal`, `get_proposal`, `review` and `resolve` are byte-identical to their `da70a56` spans, under the whole-line `lineno..end_lineno` convention with trailing newlines stripped. That convention is M3.3's P06 convention; a column-offset slice measures four bytes shorter and is a different claim. TWO PRECONDITIONS BIND BEFORE THE COMPARISON. First, definition CARDINALITY: exactly one `FunctionDef` per name, asserted first, because a name-keyed span map silently drops a duplicate and compares the base-identical copy while Python binds the other (X36). Second, the span STARTS AT `min(decorator lineno, def lineno)` and the baseline decorator vector — EMPTY for all five — is asserted: `FunctionDef.lineno` points at `def`, so adding `@staticmethod` leaves every compared byte identical while changing the runtime binding (A13)."""

        self.skipTest("SEED STUB: L15 has no predicate yet")

    def test_l16_the_proposal_round_trip_still_ends_with_the_private(self) -> None:
        """L16. the proposal round trip still ends with the private request row `resolved`: propose, review-accept, then read the row through the store and assert `status = 'resolved'` with its `output_json` and `example_id` set. The row must be the CONFIRMED variant — `source_kind = 'confirmed'`, `artifact_id` NULL, `proposal_id` bound to the reviewed proposal, `example_id` bound to the `ReviewResult` — or the three named fields pass on a malformed artifact-shaped row (X35). A REJECT round trip is required beside it (A14): `_write_proposal_request_status` has a dedicated rejection branch that the accept path never executes, so an accept-only probe leaves half the helper unobserved and the claim `this is the probe that proves it` false for that half."""

        self.skipTest("SEED STUB: L16 has no predicate yet")

    def test_l17_revise_operation_still_bumps_the_revision_by_one_and_still(self) -> None:
        """L17. `revise_operation` still bumps the revision by one and still retires `draft`, `verified` and `promoted` artifacts at the previous revision with `status_reason = 'operation revised'`."""

        self.skipTest("SEED STUB: L17 has no predicate yet")

    def test_l18__now_still_rejects_a_non_int_a_bool_a_negative_value_all(self) -> None:
        """L18. `_now` still rejects a non-`int`, a `bool`, a negative value (all three `StateError`, with L06's exact replacement text) and a non-callable `clock_us` (`ValidationError`, message `clock_us must be callable`, raised by `__init__` before `_now` runs). The surviving-caller half is stated as an exact CALL-SITE set, never as caller identity: the methods calling `self._now()` are EXACTLY the twelve remaining after `handle`, `_fail_generation` and `request_status` go — `register_operation`, `revise_operation`, `_persist_proposal`, `review`, `compile`, `verify_drafts`, `verify`, `promote_function`, `promote`, `challenge`, `revoke_example`, `suspend_artifact` — and each holds exactly one call spelled `self._now()`. The original wording (`every surviving caller of _now is unchanged`) was SELF-CONTRADICTORY, because `revise_operation` is both a surviving caller and an L07/L08 edit target whose body legitimately shrinks; whole-method equality is NOT expected for it (A15, X08). MAIN measured 15 callers at `da70a56`."""

        self.skipTest("SEED STUB: L18 has no predicate yet")

    def test_l19_mechanical_readme_md_contains_zero_standalone_handle_words(self) -> None:
        """L19. MECHANICAL: `README.md` contains zero standalone `handle` words (baseline 8) and zero `request_status` substrings (baseline 4), counting code fences, links and inline code, all of which ship to readers (V23); zero Markdown tables whose `Status`-headed column carries any frozen lifecycle poll state (`resolved`, `review_required`, `in_progress`, `fallback_failed`, `rejected`, `reconciliation_required`) — that structural shape IS the poll-state table, so a renamed heading does not evade it; zero generation/request LEASE claims, while the two truthful `a verification snapshot is not a lease` statements SURVIVE, so the ban is context-classed rather than a global word ban that would delete correct prose to reach zero (X25); and the surviving Library API region still names `System.submit_proposal`, `System.propose`, `System.review` and `proposal_id` at least once each — L19 is CONJUNCTIVE, and deleting the lifecycle section is necessary, never sufficient (X09). RULED: that the replacement request-route prose teaches the proposal route correctly."""

        self.skipTest("SEED STUB: L19 has no predicate yet")

    def test_l20_mechanical_docs_architecture_md_s_contract_h2_ordered_list(self) -> None:
        """L20. MECHANICAL: `docs/architecture.md`'s Contract H2 ordered-list items 1-3, identified structurally so later list text stays free, contain `propose` >= 1 AND `review` >= 1 (MAIN rules the implicit question YES — both, not either) and `handle` == 0; zero paragraphs match `candidate generation` together with a standalone `lease` (V24). RULED: that steps 1-3 describe the surviving flow in the right order."""

        self.skipTest("SEED STUB: L20 has no predicate yet")

    def test_l21_mechanical_docs_adapter_protocol_md_matches_zero_deleted(self) -> None:
        """L21. MECHANICAL: `docs/adapter-protocol.md` matches zero deleted-surface tokens across prose, code fences and examples; `fallback_failed` reaches 0. TWO RETENTIONS bind, because M3.7 relocates this file under BYTE EQUALITY and a wrong deletion here is permanent too. First, the `"request_id"` JSON wire key SURVIVES (X16), described as an opaque per-call tracing identifier — `CandidateRequest.request_id` is M3.6a3's and byte-frozen `propose` still constructs it; the `\brequests?\b` ban never reaches it because `_` is a word character. Second, `System.propose`'s failure contract survives (X26): the document still names `CandidateSourceError` and one concrete no-write observable (proposal count 0, event count 0), while `handle`'s inert fallback branch goes. RULED: that the rewritten protocol description is true of the surviving adapter path."""

        self.skipTest("SEED STUB: L21 has no predicate yet")

    def test_l22_mechanical_docs_threat_model_md_matches_zero_standalone(self) -> None:
        """L22. MECHANICAL: `docs/threat-model.md` matches zero standalone `handle` or `lease` lines (baseline 78 and 90); the ambiguity claim at line 61 goes while the three surviving quarantine causes stay (X17). RULED, and this obligation is MOSTLY semantic: the replacement states an application-owned idempotency key because Cement supplies none, at-most-once source invocation per `System.propose` call, and enumerate-pending recovery rather than retry (V26)."""

        self.skipTest("SEED STUB: L22 has no predicate yet")

    def test_l23_all_16_census_pins_in_section_5_are_green_after_the(self) -> None:
        """L23. all 16 census pins in section 5 are green after the rewrite, each either satisfied by the new prose or re-scoped with grounds recorded in section 8. Sixteen, not fifteen, by C06. ANTI- WEAKENING (A17): each of the 14 working-tree pins keeps its assertion body BYTE-IDENTICAL to its `da70a56` blob unless section 8 PERMITS the delta, and every permitted delta is enumerated there. Without this, `all pins green` is satisfiable by making a pin tautological — a test with an unreachable document read and `assertIn('handle', 'handle')` scores `reads-doc True`, `vocab True`, stays in the census and keeps gate 1 green. The pins are additionally EXECUTED by id, not merely counted (X10)."""

        self.skipTest("SEED STUB: L23 has no predicate yet")

    def test_l24_no_human_facing_surface_gains_a_new_claim_about_a_deleted(self) -> None:
        """L24. no human-facing surface gains a NEW claim about a deleted surface. Re-run the census (gate 3) against the rewritten documents. THE PREDICATE BINDS A NAMED TOKEN SUBSET, not the whole vocabulary (A18, V27): owned hits must reach ZERO for `handle`, `request_status`, `retry_failed`, `invalidated_generators`, `resolved_by_artifact`, `in_progress`, `fallback_failed`, `reconciliation_required` and every ambiguity-quarantine promise. The literal all-token reading is UNSATISFIABLE and MAIN reproduced why: M3.5b's D25 requires at least two shipped paragraphs containing `request row stays internal`, measurement finds exactly two (`README.md`, `docs/architecture.md`), and the census `\brequests?\b` matches both — so a green D25 and a zero `requests` count cannot hold together. Every surviving generic hit (`request`, `requests`, `lease`, `ambigu`) therefore carries explicit GROUNDS as private-table prose or a non-generation-lease statement. SCANNER COVERAGE IS ITSELF PINNED (X18): the census `DOCS` tuple must EQUAL the tracked human-facing Markdown set (`README.md`, `docs/*.md`, `examples/*/README.md`, five paths at `da70a56`), so a document added during implementation cannot become an unscanned home for a deleted claim. THIS PARAGRAPH IS GATE 3'S INDEPENDENT ORACLE (A22): the expectation lives in the contract, which `--emit` cannot rewrite, so re-emitting after a bad rewrite now contradicts a number MAIN authored rather than blessing the tree."""

        self.skipTest("SEED STUB: L24 has no predicate yet")

    def test_l25_m3_5b_s_d15a_tests_test_cli_removal_battery_py_1131(self) -> None:
        """L25. M3.5b's D15a (`tests/test_cli_removal_battery.py:1131`, assertion `:1158`) is re-scoped to the closed range `36f7890..1146421`, exactly as M3.6a1 re-scoped its siblings D15b (`:1160`) and D22b (`:2766`). The repair is a family repair: after it, no D15/D22 clause reads the working tree for a runtime module."""

        self.skipTest("SEED STUB: L25 has no predicate yet")

    def test_l26_the_four_p06_span_freezes_are_retired_with_their_history(self) -> None:
        """L26. the four P06 span freezes are RETIRED with their history preserved, not re-based: they freeze the bytes of a method that no longer exists. Retirement DERIVES all three figures (`12,866 B / 1182130a2b3a`, `12,867 B / cd60036faf5c`, `12,862 B / c27e71b0b4c7`) from git object `3b7769b` on EVERY RUN and compares them; recording them as prose leaves a copied typo satisfying a text-presence assertion while disagreeing with history, and the only executable recomputers today are the frames being retired (A19). All FOUR test identities stay DISCOVERABLE — one aggregate replacement erases three independent tripwire records even where the figures appear once (X21) — and none reads the working-tree `System.handle` span. L15 replaces their protective value for the methods that survive."""

        self.skipTest("SEED STUB: L26 has no predicate yet")

    def test_l27_m3_5b_s_d01_tests_test_cli_removal_battery_py_608(self) -> None:
        """L27. M3.5b's D01 (`tests/test_cli_removal_battery.py:608`, assertions `:617` + `:618`) is INVERTED: it asserted `System.handle` and `System.request_status` still ship as library methods; it now asserts their absence. An inverted pin keeps the obligation and reverses the predicate; deleting it would delete the behaviour's only pin along with the behaviour. The inversion PAIRS absence with positive identity controls in the same test — `System.__module__ == 'cement_runtime.system'` and `callable(System.propose)` — or both negative assertions pass against an empty dummy class (X12), and D01's existing CLI leaf-set complement stays green beside them, which is the two non-overlapping subproperties that make retention worth more than deletion (A20)."""

        self.skipTest("SEED STUB: L27 has no predicate yet")

    def test_l28_tests_test_authority_removal_py_118(self) -> None:
        """L28. `tests/test_authority_removal.py:118 test_system_constructor_shape` is rewritten to the three-parameter signature and keeps asserting defaults for the parameters that remain."""

        self.skipTest("SEED STUB: L28 has no predicate yet")

    def test_l29_m3u6a2_tripwires_py_s__freezes_detector_is_widened_to_see(self) -> None:
        """L29. `m3u6a2-tripwires.py`'s `_freezes()` detector is widened to see the P06 family, behind a self-test control that FIRES on a P06 frame. Today it requires the literal `cement_runtime/system.py` or `System.handle` AND one of `read_bytes()`/`getsource`/`_git_bytes(`, while the four P06 frames reach the same source through `cement_runtime.system.__file__`, `inspect.getsourcefile(System)` and a `_source(ROOT, path)` helper — so the instrument reported `FREEZES: 4` over a set DISJOINT from the four freezes this unit actually inverts, and its 6/6 self-test covered none of that negative space. THE CONTROL RUNS AGAINST AN IMMUTABLE SYNTHETIC P06 SOURCE FIXTURE, never a live frame, because L26 empties the live positive set in this same unit — after retirement a working detector and one returning no P06 rows are otherwise indistinguishable (A21). Detection is factored into a `_is_freeze(segment)` seam so it can be probed directly, and the control is a PAIR: the P06 shape must be INCLUDED, and the same source acquisition selecting a PRESERVED method (`propose`) must be EXCLUDED, or over-reporting satisfies the positive half alone (X14, V30). Live `_freezes()` stays 4 and `--self-test` goes 8/8. If widening proves to over-report, record the exclusion with grounds instead; what is not acceptable is leaving a detector whose name promises the family it cannot see. The battery's own file stays excluded from both scanners (C06, X22)."""

        self.skipTest("SEED STUB: L29 has no predicate yet")

    def test_l30_m3_6a1_s_d16_tests_test_migration_battery_py_993_is_re(self) -> None:
        """L30. M3.6a1's D16 (`tests/test_migration_battery.py:993`) is re-scoped to the CLOSED range `6fb4d92..dc4ab5e` — M3.6a1's baseline and its own DONE tip — on BOTH halves: the expected path set and the per-path byte comparison, which read `HEAD` and the working tree respectively. Read against `HEAD`, D16 asserted that M3.6a1's surgery script reproduces every LATER unit's `tests/` and `examples/` edits, which no script pinned to an earlier baseline can do. It is the same family as D15a (L25), and it is stricter: D15a inverts when this unit EDITS a runtime module, while D16 inverts when this unit ADDS ANY FILE under `tests/` or `examples/` — the battery seed alone tripped it. Its repair therefore lands NO LATER THAN the first commit that adds a file under `tests/` or `examples/`. `Before` was the wrong word (X33, C11): git has no intra-commit ordering, and `7cfc748` both repaired D16 and added the seed, which satisfies the practical reading and needs no history rewrite. D16's closed expected-path set is an exact eight-member historical delta, not merely a nonempty one (X23), and BOTH halves use `6fb4d92..dc4ab5e` (X15)."""

        self.skipTest("SEED STUB: L30 has no predicate yet")

    def test_l31_ambiguity_quarantine_is_removed_as_a_behaviour_not_merely(self) -> None:
        """L31. AMBIGUITY QUARANTINE IS REMOVED AS A BEHAVIOUR, not merely as an event spelling (A10). After this unit no code path suspends an artifact with reason `ambiguous active scope`: that reason string has zero occurrences in `src/`, and a probe that drives the duplicate-promotion condition leaves BOTH artifacts `promoted` with their promotion receipts intact and emits ZERO ambiguity events. `tests/test_system.py`'s surviving assertion is INVERTED to that post-state rather than deleted (V15). This obligation exists because C05 reclassified the quarantine as a deleted behaviour while L11 pinned only its vocabulary — a renamed private path could keep the storage mutation, emit an allowed kind and satisfy the sixteen-kind set — and because section 2.1 gave the clock widening its own obligation on exactly this reasoning."""

        self.skipTest("SEED STUB: L31 has no predicate yet")
