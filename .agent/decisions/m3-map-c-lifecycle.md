# M3 Track C — Request Lifecycle Removal Surface

## S1 INVENTORY

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S1-001 | src/cement_runtime/store.py:39 | `CREATE TABLE IF NOT EXISTS requests (` | schema | delete | Lifecycle aggregate; 18 columns below plus a composite primary key. |
| S1-002 | src/cement_runtime/store.py:40 | `id TEXT NOT NULL` | schema | delete | Caller-owned request ID. |
| S1-003 | src/cement_runtime/store.py:41 | `partition TEXT NOT NULL` | schema | delete | Request identity scope. |
| S1-004 | src/cement_runtime/store.py:42 | `operation TEXT NOT NULL` | schema | delete | Immutable request binding. |
| S1-005 | src/cement_runtime/store.py:43 | `operation_revision INTEGER NOT NULL` | schema | delete | Revision snapshot used for later reconciliation. |
| S1-006 | src/cement_runtime/store.py:44 | `input_json TEXT NOT NULL` | schema | delete | Cached request input. Explicit proposal rows still need their own input binding after redesign. |
| S1-007 | src/cement_runtime/store.py:45 | `input_hash TEXT NOT NULL` | schema | delete | Cached request-content binding. |
| S1-008 | src/cement_runtime/store.py:46 | `status TEXT NOT NULL CHECK (` | schema | delete | Persisted request state machine. |
| S1-009 | src/cement_runtime/store.py:49 | `output_json TEXT` | schema | delete | Cached resolved output. Pure `resolve` must derive, not persist, this answer. |
| S1-010 | src/cement_runtime/store.py:50 | `source_kind TEXT CHECK` | schema | delete | Cached artifact/confirmed provenance. |
| S1-011 | src/cement_runtime/store.py:51 | `artifact_id TEXT` | schema | delete | Cached artifact referent. |
| S1-012 | src/cement_runtime/store.py:52 | `proposal_id TEXT` | schema | delete | Request-to-proposal state link. |
| S1-013 | src/cement_runtime/store.py:53 | `example_id TEXT` | schema | delete | Request-to-confirmed-fixture state link. |
| S1-014 | src/cement_runtime/store.py:54 | `error_code TEXT` | schema | delete | Persisted source failure. |
| S1-015 | src/cement_runtime/store.py:55 | `lease_owner TEXT` | lease | delete | Generation ownership token. |
| S1-016 | src/cement_runtime/store.py:56 | `lease_until_us INTEGER` | lease | delete | Nullable recovery deadline. |
| S1-017 | src/cement_runtime/store.py:57 | `attempts INTEGER NOT NULL DEFAULT 1` | schema | delete | Reclaim/retry counter. |
| S1-018 | src/cement_runtime/store.py:58 | `created_at_us INTEGER NOT NULL` | schema | delete | Request creation time. |
| S1-019 | src/cement_runtime/store.py:59 | `updated_at_us INTEGER NOT NULL` | schema | delete | Request transition time. |
| S1-020 | src/cement_runtime/store.py:61 | `(status = 'generating'` | schema | delete | Five-way row-shape invariant spans lines 61-78; contains 5 of 7 store `lease` hits. |
| S1-021 | src/cement_runtime/store.py:80 | `PRIMARY KEY (partition, id)` | idempotency | delete | Partition-local request-ID uniqueness. |
| S1-022 | src/cement_runtime/store.py:250 | `CREATE INDEX IF NOT EXISTS requests_scope` | schema | delete | Request lookup/reconciliation index. |
| S1-023 | src/cement_runtime/store.py:86 | `request_id TEXT NOT NULL` | idempotency | rewrite | Proposal identity currently delegates to a request row. Explicit submission needs a direct proposal scope/input binding instead. |
| S1-024 | src/cement_runtime/store.py:108 | `UNIQUE (partition, request_id)` | idempotency | rewrite | Remove request-ID uniqueness; decide the replacement proposal deduplication contract. |
| S1-025 | src/cement_runtime/store.py:109 | `REFERENCES requests(partition, id)` | schema | rewrite | Removing `requests` requires a new proposal-to-scope representation. |
| S1-026 | src/cement_runtime/system.py:420 | `generation_lease_seconds: int = 120` | lease | delete | `System.__init__`: 5 lease hits configure and store the lease duration. |
| S1-027 | src/cement_runtime/system.py:447 | `self._lease_us` | lease | delete | `_now`: 2 hits reserve timestamp headroom for a future lease deadline. |
| S1-028 | src/cement_runtime/system.py:565 | `lease_owner = NULL` | lease | delete | `revise_operation`: 1 hit cancels old-revision generators. |
| S1-029 | src/cement_runtime/system.py:605 | `owner = _new_id("lease")` | lease | delete | `handle`: 14 hits acquire, reclaim, compare, and clear a generation lease. |
| S1-030 | src/cement_runtime/system.py:872 | `request["lease_owner"] != owner` | lease | delete | `_fail_generation`: 3 hits reject stale generator failure writes. |
| S1-031 | src/cement_runtime/system.py:993 | `request["lease_until_us"]` | lease | delete | `_outcome`: 2 hits project an active lease as `InProgress`. |
| S1-032 | src/cement_runtime/system.py:2943 | `is not a lease` | doc | keep | `verify_function`: one semantic disclaimer, not lease machinery. |
| S1-033 | src/cement_runtime/models.py:342 | `not a lease` | doc | keep | `FunctionVerification` disclaimer remains true. |
| S1-034 | src/cement_runtime/system.py:153 | `def _request_id(value: str) -> str:` | definition | keep | 2 hits define a generic entity-ID validator despite its lifecycle-shaped name; many M2 callers use it for non-request IDs. Rename is optional, not required by track (c). |
| S1-035 | src/cement_runtime/system.py:281 | `_request_id(row["id"])` | idempotency | keep | `_function_receipt_from_row`: generic receipt-ID validation; 1 hit. |
| S1-036 | src/cement_runtime/system.py:595 | `request_id: str` | idempotency | moves-to-caller | `handle`: 22 request-ID hits implement defaulting, immutable-content replay, insert, and result projection. |
| S1-037 | src/cement_runtime/system.py:862 | `request_id: str` | idempotency | delete | `_fail_generation`: 5 hits address and emit failure for a leased request. |
| S1-038 | src/cement_runtime/system.py:901 | `request_id = str(request["id"])` | idempotency | rewrite | `_outcome`: 10 hits turn a persisted request row into six lifecycle result types. Pure `resolve` needs a separate result projector. |
| S1-039 | src/cement_runtime/system.py:1068 | `def request_status(` | idempotency | delete | 3 hits expose lifecycle polling by partition/request ID. |
| S1-040 | src/cement_runtime/system.py:1087 | `_request_id(proposal_id)` | idempotency | rewrite | `get_proposal`: 4 hits include generic proposal-ID validation plus the bound request ID in the view. |
| S1-041 | src/cement_runtime/system.py:1128 | `_request_id(proposal_id)` | idempotency | rewrite | `proposal`: 3 hits include proposal-ID validation plus request-bound lookup. |
| S1-042 | src/cement_runtime/system.py:1171 | `r.id AS bound_request_id` | idempotency | rewrite | `proposals`: 2 hits join request state into proposal enumeration. |
| S1-043 | src/cement_runtime/system.py:1208 | `"request_id"` | idempotency | rewrite | `_proposal_record`: 1 hit publishes the bound request ID. |
| S1-044 | src/cement_runtime/system.py:1229 | `_request_id(proposal_id)` | idempotency | rewrite | `review`: 8 hits validate a proposal, inspect/update its request, and create request-bound evidence. |
| S1-045 | src/cement_runtime/system.py:2020 | `_request_id(membership["artifact_id"])` | type | keep | `_reconstruct_function_receipt`: 2 generic artifact/report ID validations. |
| S1-046 | src/cement_runtime/system.py:2325 | `_request_id(row["membership_artifact_id"])` | type | keep | `_function_report_member`: 4 generic artifact/report ID validations. |
| S1-047 | src/cement_runtime/system.py:2446 | `_request_id(row["id"])` | idempotency | rewrite | `_pending_proposal_gap_from_row`: 4 hits publish proposal and request IDs; the gap survives only if explicit submissions remain pending state. |
| S1-048 | src/cement_runtime/system.py:2496 | `_request_id(row["id"])` | type | keep | `_operation_report_artifact`: generic artifact-ID validation; 1 hit. |
| S1-049 | src/cement_runtime/system.py:2562 | `_request_id(receipt_id)` | idempotency | rewrite | `function_report`: 4 hits mix generic receipt IDs with pending proposal request IDs. |
| S1-050 | src/cement_runtime/system.py:2914 | `_request_id(receipt_id)` | type | keep | `reconstruct_function_receipt`: generic receipt-ID validation; 1 hit. |
| S1-051 | src/cement_runtime/system.py:3704 | `_request_id(artifact_id)` | type | keep | `verify`: generic artifact-ID validation; 1 hit. |
| S1-052 | src/cement_runtime/system.py:4466 | `_request_id(artifact_id)` | type | keep | `promote`: generic artifact-ID validation; 1 hit. |
| S1-053 | src/cement_runtime/system.py:4761 | `_request_id(example_id)` | type | keep | `revoke_example`: generic example-ID validation; 1 hit. |
| S1-054 | src/cement_runtime/system.py:4829 | `_request_id(artifact_id)` | type | keep | `suspend_artifact`: generic artifact-ID validation; 1 hit. |
| S1-055 | src/cement_runtime/system.py:4968 | `_request_id(artifact_id)` | type | keep | `artifact`: generic artifact-ID validation; 1 hit. |
| S1-056 | src/cement_runtime/system.py:5006 | `_request_id(report_id)` | type | keep | `report`: generic report-ID validation; 1 hit. |
| S1-057 | src/cement_runtime/system.py:5070 | `_request_id(artifact_id)` | type | keep | `reports`: generic artifact-ID validation; 1 hit. |
| S1-058 | src/cement_runtime/models.py:64 | `request_id: str` | type | rewrite | `CandidateRequest`: remove caller lifecycle identity from proposal generation input. |
| S1-059 | src/cement_runtime/models.py:70 | `request_id: str` | type | rewrite | `Resolved`: pure resolution can survive, but the request-ID field has no core referent. |
| S1-060 | src/cement_runtime/models.py:80 | `request_id: str` | type | rewrite | `ReviewRequired`: explicit submission may return a proposal ID, but not a stored request ID. |
| S1-061 | src/cement_runtime/models.py:87 | `request_id: str` | type | delete | `InProgress` exists only for lease polling. |
| S1-062 | src/cement_runtime/models.py:94 | `request_id: str` | type | delete | `FallbackFailed` exists only for stored generation failures. |
| S1-063 | src/cement_runtime/models.py:101 | `request_id: str` | type | delete | `Rejected` is a cached request outcome, distinct from the proposal review record. |
| S1-064 | src/cement_runtime/models.py:108 | `request_id: str` | type | delete | `ReconciliationRequired` exists only to invalidate a cached request answer. |
| S1-065 | src/cement_runtime/models.py:131 | `request_id: str` | type | rewrite | `ProposalView`: remove request binding; retain explicit proposal identity/content. |
| S1-066 | src/cement_runtime/models.py:247 | `request_id: str` | type | rewrite | `PendingProposalGap`: operation report cannot publish a removed request ID. |
| S1-067 | src/cement_runtime/cli.py:130 | `request.add_argument("request_id")` | idempotency | delete | `_parser`: request-status polling positional. |
| S1-068 | src/cement_runtime/cli.py:497 | `request_id=args.request_id` | idempotency | rewrite | `_run`: 2 hits route IDs into `handle` and `request_status`; former moves out, latter deletes. |
| S1-069 | src/cement_runtime/source.py:127 | `"request_id": request.request_id` | idempotency | rewrite | `CommandCandidateSource.propose`: adapter tracing/idempotency belongs to caller or optional wrapper, not the core proposal request. |
| S1-070 | src/cement_runtime/models.py:75 | `Literal["resolved"] = "resolved"` | status | rewrite | Survives as the successful pure-resolution status only if MAIN retains a tagged result instead of a match/miss type. |
| S1-071 | src/cement_runtime/models.py:82 | `Literal["review_required"] = "review_required"` | status | rewrite | May describe proposal submission, but must leave the read-only resolver. |
| S1-072 | src/cement_runtime/models.py:89 | `Literal["in_progress"] = "in_progress"` | status | delete | Lease-only public state. |
| S1-073 | src/cement_runtime/models.py:96 | `Literal["fallback_failed"] = "fallback_failed"` | status | delete | Stored source-failure state. |
| S1-074 | src/cement_runtime/models.py:103 | `Literal["rejected"] = "rejected"` | status | delete | Request replay state; proposal review still records `rejected` internally. |
| S1-075 | src/cement_runtime/models.py:112 | `Literal["reconciliation_required"] = "reconciliation_required"` | status | delete | Cached-answer invalidation state. |
| S1-076 | src/cement_runtime/store.py:47 | `status IN ('generating', 'pending', 'resolved', 'rejected', 'failed')` | status | delete | Entire persisted request-state vocabulary disappears with `requests`. |
| S1-077 | src/cement_runtime/system.py:596 | `retry_failed: bool = False` | idempotency | delete | `handle`: 4 hits validate and authorize reclaiming a stored failed request. |
| S1-078 | src/cement_runtime/cli.py:498 | `retry_failed=args.retry_failed` | call | delete | CLI forwards the retry control to `handle`. |
| S1-079 | src/cement_runtime/system.py:886 | `kind="request.fallback_failed"` | status | delete | Failure event has no lifecycle subject after caller ownership moves out. |
| S1-080 | examples/hospital_ocr/run_demo.py:133 | `"request_id"` | example | delete | `_print_event_trace`: 1 hit searches request identity in event projections. |
| S1-081 | examples/hospital_ocr/run_demo.py:182 | `request_id="a-note-01"` | example | rewrite | `main`: 7 request-ID arguments drive five proposal submissions and two promoted hits. |
| S1-082 | examples/hospital_ocr/plan_adapter.py:159 | `request_id="self-check-known-layout"` | example | rewrite | `_self_check`: 2 request-ID fields disappear from `CandidateRequest`. |
| S1-083 | src/cement_runtime/store.py:19 | `SCHEMA_VERSION = 2` | schema | rewrite | Version definition; final no-migration cut becomes 3. |
| S1-084 | src/cement_runtime/store.py:434 | `schema-v{SCHEMA_VERSION}` | schema | keep | `_validate_ledger`: 1 of 6 version hits derives the metadata key from the bumped constant. |
| S1-085 | src/cement_runtime/store.py:519 | `current not in (0, SCHEMA_VERSION)` | schema | keep | `_initialize`: 4 of 6 version hits reject old versions, render the error, write metadata, and set `user_version`. |
| S1-086 | src/cement_runtime/store.py:385 | `SCHEMA_FINGERPRINT = hashlib.sha256` | schema | keep | Fingerprint automatically changes when the SQL schema changes. |
| S1-087 | src/cement_runtime/store.py:438 | `fingerprint[0] != SCHEMA_FINGERPRINT` | schema | keep | Metadata digest mismatch fails closed before use. |
| S1-088 | src/cement_runtime/store.py:440 | `_schema_objects(connection) != _expected_schema()` | schema | keep | Independent live-object comparison catches a forged version/fingerprint over the wrong schema. |

Measured completeness (`git grep -c`, files named by the seed): `lease` = system 28 + store 7 + models 1; `request_id` = system 84 + models 9 + store 3 + CLI 3 + source 1 + demo 8 + plan adapter 2; `resolved` = system 7 + store 2 + models 1; `in_progress` = models 1; `fallback_failed` = system 1 + models 1; `reconciliation_required` = models 1; `retry_failed` = system 4 + CLI 1; `SCHEMA_VERSION` = store 6; `SCHEMA_FINGERPRINT` = store 3. Rows S1-026..S1-033 cover every `lease` scope, S1-034..S1-069 plus S1-080..S1-082 cover every requested `request_id` scope/consumer, S1-070..S1-079 cover the named status/retry vocabulary, and S1-083..S1-088 cover the version/fingerprint path. Repeated hits within one function are represented once with their measured count.

## S2 DISPATCH TRACE

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S2-H01 | src/cement_runtime/system.py:589 | `def handle(` | definition | rewrite | Current mixed route; split into pure `resolve` plus explicit proposal submission. Partition: neither at entry. |
| S2-H02 | src/cement_runtime/system.py:598 | `partition = _name(partition, "partition")` | call | keep | Validate partition and operation. Partition: neither. |
| S2-H03 | src/cement_runtime/system.py:602 | `request_id = _request_id` | idempotency | moves-to-caller | Generate/validate partition-local idempotency key. Partition: request-ID-dependent. |
| S2-H04 | src/cement_runtime/system.py:603 | `input_json = canonicalize(input_value)` | call | keep | Canonical bounded input is needed by both resolution and submission. Partition: neither. |
| S2-H05 | src/cement_runtime/system.py:605 | `owner = _new_id("lease")` | lease | delete | Allocate generation owner before the reservation transaction. Partition: lease-dependent. |
| S2-H06 | src/cement_runtime/system.py:609 | `SELECT * FROM requests WHERE partition = ? AND id = ?` | idempotency | delete | First write transaction starts with request-ID replay lookup. Partition: request-ID-dependent. |
| S2-H07 | src/cement_runtime/system.py:618 | `request_id is already bound to different immutable content` | idempotency | moves-to-caller | Enforce immutable operation/input binding for one ID. Partition: request-ID-dependent. |
| S2-H08 | src/cement_runtime/system.py:619 | `_request_revision_is_current` | idempotency | delete | Existing request may project reconciliation instead of dispatch. Partition: request-ID-dependent in this call site. |
| S2-H09 | src/cement_runtime/system.py:621 | `request["status"] == "generating"` | lease | delete | Reclaim an expired generator and increment attempts. Partition: both lease- and request-ID-dependent. |
| S2-H10 | src/cement_runtime/system.py:632 | `request["status"] == "failed" and retry_failed` | idempotency | delete | Retry stored failure under the original ID. Partition: request-ID-dependent; lease is reacquired. |
| S2-H11 | src/cement_runtime/system.py:647 | `SELECT * FROM operations WHERE partition = ? AND name = ?` | call | keep | Resolve the current operation revision for a new route. Partition: neither. |
| S2-H12 | src/cement_runtime/system.py:655 | `SELECT * FROM artifacts` | call | rewrite | Query promoted exact scope. This is the pure resolver's read spine. Partition: neither. |
| S2-H13 | src/cement_runtime/system.py:683 | `self._artifact_from_row(artifact_row)` | call | keep | Parse and validate the stored artifact document. Partition: neither. |
| S2-H14 | src/cement_runtime/system.py:684 | `self._validate_promoted(connection, artifact_row)` | call | keep | Recheck promotion receipt, policy, evidence, and active integrity. Partition: neither; currently may lead to quarantine writes in `handle`. |
| S2-H15 | src/cement_runtime/system.py:685 | `execution = execute(` | call | rewrite | Evaluate one artifact. M3's seed says the new resolver should target the M2 function evaluator instead. Partition: neither. |
| S2-H16 | src/cement_runtime/system.py:716 | `INSERT INTO requests(` | schema | delete | Persist an artifact hit as a resolved request row. Partition: request-ID-dependent. |
| S2-H17 | src/cement_runtime/system.py:744 | `return Resolved(` | status | rewrite | Immediate artifact-hit result survives without request identity or cache semantics. Partition: neither after field removal. |
| S2-H18 | src/cement_runtime/system.py:752 | `INSERT INTO requests(` | lease | delete | Persist miss as `generating` with owner/deadline before leaving the transaction. Partition: both lease- and request-ID-dependent. |
| S2-H19 | src/cement_runtime/system.py:771 | `self.candidate_source is None` | call | rewrite | Submission must expose source absence directly, without a stored failed request. Partition: neither. |
| S2-H20 | src/cement_runtime/system.py:774 | `self.candidate_source.propose(` | call | rewrite | Candidate generation deliberately occurs after the first transaction closes. Explicit submission should preserve this no-lock property. Partition: neither after `CandidateRequest.request_id` removal. |
| S2-H21 | src/cement_runtime/system.py:775 | `CandidateRequest(` | type | rewrite | Carries partition, operation, revision, request ID, and input; only request ID is lifecycle-only. Partition: request-ID-dependent today. |
| S2-H22 | src/cement_runtime/system.py:788 | `self._fail_generation(` | call | delete | Adapter errors become persisted `fallback_failed`. Caller-owned lifecycle requires a direct failure contract. Partition: both lease- and request-ID-dependent. |
| S2-H23 | src/cement_runtime/system.py:793 | `proposal_id = _new_id("prop")` | call | keep | Explicit submission still needs a durable proposal ID. Partition: neither. |
| S2-H24 | src/cement_runtime/system.py:797 | `SELECT * FROM requests WHERE partition = ? AND id = ?` | idempotency | delete | Second transaction reloads the reservation after generation. Partition: request-ID-dependent. |
| S2-H25 | src/cement_runtime/system.py:802 | `request["lease_owner"] != owner` | lease | delete | A stale generator cannot persist after another owner reclaimed the lease. Partition: both lease- and request-ID-dependent. |
| S2-H26 | src/cement_runtime/system.py:804 | `_request_revision_is_current` | call | rewrite | Optimistic current-revision recheck remains necessary across out-of-transaction generation, but no request row should carry it. Partition: neither semantically. |
| S2-H27 | src/cement_runtime/system.py:825 | `kind="proposal.created"` | call | rewrite | Proposal event survives; its payload and subject must stop referring to a request. Partition: request-ID-dependent only in current payload. |
| S2-H28 | src/cement_runtime/system.py:833 | `INSERT INTO proposals(` | schema | rewrite | Persist candidate/provenance as pending. New row must directly bind partition, operation, revision, canonical input, and hashes. Partition: request-ID-dependent structurally today, neither semantically. |
| S2-H29 | src/cement_runtime/system.py:852 | `UPDATE requests` | status | delete | Clear lease and transition reservation to pending. Partition: both lease- and request-ID-dependent. |
| S2-H30 | src/cement_runtime/system.py:859 | `return ReviewRequired(` | status | rewrite | Explicit submission may return the proposal ID; drop the request ID and keep this status out of `resolve`. Partition: request-ID-dependent today. |
| S2-H31 | src/cement_runtime/system.py:861 | `def _fail_generation(` | definition | delete | Failure helper only conditionally writes the leased request. Partition: both lease- and request-ID-dependent. |
| S2-H32 | src/cement_runtime/system.py:894 | `def _outcome(` | definition | delete | Six-way projector exists to replay persisted request state. The pure resolver needs a separate match/miss projector. Partition: request-ID-dependent; lease-dependent for generating rows. |
| S2-H33 | src/cement_runtime/system.py:902 | `not self._request_revision_is_current` | status | delete | Revision drift returns `ReconciliationRequired`. Partition: request-ID-dependent. |
| S2-H34 | src/cement_runtime/system.py:923 | `self._artifact_from_row(artifact_row)` | call | delete | Replay revalidates a cached artifact answer. Pure resolve evaluates current state directly, so this duplicate replay branch disappears. Partition: request-ID-dependent in context. |
| S2-H35 | src/cement_runtime/system.py:991 | `return ReviewRequired(` | status | delete | Cached pending-state projection. Partition: request-ID-dependent. |
| S2-H36 | src/cement_runtime/system.py:993 | `request["lease_until_us"]` | lease | delete | Project lease deadline to failure or `InProgress`. Partition: both lease- and request-ID-dependent. |
| S2-H37 | src/cement_runtime/system.py:1004 | `return FallbackFailed(` | status | delete | Project persisted source failure. Partition: request-ID-dependent. |
| S2-H38 | src/cement_runtime/system.py:1068 | `def request_status(` | definition | delete | Public polling entry is the read half of the request lifecycle. Partition: request-ID-dependent. |
| S2-C01 | tests/test_system.py:209 | `def confirm(` | test | rewrite | There is no production `System.confirm`; this fixture names the composed `handle` → `get_proposal` → `review` route. |
| S2-C02 | tests/test_system.py:218 | `outcome = self.system.handle(` | call | rewrite | Fixture asks the mixed route to generate a proposal. Partition: request-ID-dependent. |
| S2-C03 | tests/test_system.py:222 | `self.system.get_proposal` | call | rewrite | Fixture reads hidden proposed output before review. Proposal ID, not request ID, is the durable identity. Partition: neither. |
| S2-C04 | tests/test_system.py:225 | `return self.system.review(` | call | rewrite | Fixture accepts or corrects via the actual public confirmation entry. Partition: neither. |
| S2-C05 | src/cement_runtime/system.py:1218 | `def review(` | definition | rewrite | Production accept/correct/reject entry; confirmation is its accept/correct branches. |
| S2-C06 | src/cement_runtime/system.py:1232 | `decision not in {"accept", "correct", "reject"}` | call | keep | Validate review decision and corrected-output shape. Partition: neither. |
| S2-C07 | src/cement_runtime/system.py:1238 | `self._authorize(` | call | keep | Authority removal is M3 track (b), not request lifecycle; reviewer recording remains. Partition: neither. |
| S2-C08 | src/cement_runtime/system.py:1248 | `JOIN requests AS r` | schema | rewrite | Load proposal plus operation/input and assert proposal/request state lockstep. New proposal row must own these bindings. Partition: request-ID-dependent structurally. |
| S2-C09 | src/cement_runtime/system.py:1255 | `row["status"] != "pending"` | status | keep | Proposal lifecycle remains: only a pending proposal can be reviewed. Partition: neither. |
| S2-C10 | src/cement_runtime/system.py:1271 | `self._proposal_content(row)` | call | rewrite | Parse and digest-check input, proposal, provenance. Input currently comes from joined request; move it to proposal. Partition: neither semantically. |
| S2-C11 | src/cement_runtime/system.py:1273 | `decision == "reject"` | status | rewrite | Reject should update proposal audit state only; request rejection update/result disappear. Partition: request-ID-dependent only in current companion update. |
| S2-C12 | src/cement_runtime/system.py:1333 | `UPDATE proposals` | status | keep | Accept/correct seals final output and reviewer metadata. Partition: neither. |
| S2-C13 | src/cement_runtime/system.py:1351 | `INSERT INTO examples(` | schema | keep | Confirmation persists immutable evidence. Partition: neither. |
| S2-C14 | src/cement_runtime/system.py:1374 | `conflicting_artifacts = connection.execute(` | call | keep | New confirmed counterexamples quarantine conflicting promoted artifacts. Partition: neither. |
| S2-C15 | src/cement_runtime/system.py:1413 | `UPDATE requests` | status | delete | Cache confirmation as request `resolved`. Partition: request-ID-dependent. |
| S2-C16 | src/cement_runtime/system.py:1438 | `UPDATE proposals SET status_sequence` | call | keep | Bind proposal transition feed after the event insert. Partition: neither. |
| S2-C17 | src/cement_runtime/system.py:1443 | `return Resolved(` | status | rewrite | Review should return an evidence/review result, not a cached request outcome; exact replacement type is a MAIN fork. Partition: request-ID-dependent today. |
| S2-X01 | src/cement_runtime/system.py:4583 | `def challenge(` | definition | keep | Independent confirmation/counterexample route over an active artifact. No request lifecycle dependency. |
| S2-X02 | src/cement_runtime/system.py:4598 | `partition = _name(partition, "partition")` | call | keep | Validate scope/reviewer/note, authorize, canonicalize input and expected output. Partition: neither. |
| S2-X03 | src/cement_runtime/system.py:4619 | `SELECT * FROM artifacts` | call | keep | First write transaction finds current promoted rows. Partition: neither. |
| S2-X04 | src/cement_runtime/system.py:4627 | `self._artifact_from_row(row)` | call | keep | Validate each row and quarantine integrity-invalid artifacts before challenge. Partition: neither. |
| S2-X05 | src/cement_runtime/system.py:4650 | `if quarantined:` | status | keep | Fail and require review after the first transaction commits quarantine. Partition: neither. |
| S2-X06 | src/cement_runtime/system.py:4663 | `SELECT * FROM artifacts` | call | keep | Second write transaction re-reads current revision/scope. Partition: neither. |
| S2-X07 | src/cement_runtime/system.py:4673 | `execution = execute(` | call | rewrite | Resolve each active artifact and require exactly one match. Can share the new pure resolver only if that resolver exposes the evidence needed here. Partition: neither. |
| S2-X08 | src/cement_runtime/system.py:4682 | `len(matches) != 1` | status | keep | Challenge requires exactly one active match. Partition: neither. |
| S2-X09 | src/cement_runtime/system.py:4685 | `suspended = observed.text != expected.text` | call | keep | Compare observed and supervised expected output. Partition: neither. |
| S2-X10 | src/cement_runtime/system.py:4705 | `INSERT INTO examples(` | schema | keep | Persist challenge-origin evidence. Partition: neither. |
| S2-X11 | src/cement_runtime/system.py:4739 | `kind="artifact.counterexample" if suspended else "artifact.challenged"` | call | keep | Suspend on disagreement and append the corresponding event. Partition: neither. |
| S2-X12 | src/cement_runtime/system.py:4750 | `return example_id, suspended` | type | keep | Return evidence identity plus quarantine verdict. Partition: neither. |

### Ordered traces and dependency partition

**`handle` today:** H01-H05 validate and allocate lifecycle identity; H06-H10 replay/reclaim an existing request; H11-H17 resolve a promoted exact match and persist the hit; H18 reserves a miss; H19-H22 generate outside the transaction and convert failures; H23-H30 recheck ownership/revision, persist the proposal, transition request state, and return; H31-H38 back replay and polling. The candidate call at H20 is outside both write transactions. This no-lock boundary is valuable independently of leases.

**Confirmation today:** no public method is named `confirm`. Test helper C01 composes C02 (`handle`), C03 (`get_proposal`), and C04/C05 (`review`). The production accept/correct path validates at C06-C10, seals the proposal at C12, inserts evidence at C13, quarantines conflicts at C14, updates the request cache at C15, binds the event sequence at C16, and returns at C17. Reject follows C11 and updates both proposal and request today.

**`challenge` today:** X01-X05 validate/quarantine integrity failures in transaction one; X06-X09 re-read and resolve exactly one active match in transaction two; X10-X11 persist challenge evidence, optionally suspend the artifact, and emit an event; X12 returns. It neither reads nor writes `requests`, uses no request ID, and uses no generation lease.

**Lease-dependent steps:** H05, H09-H10 (reacquisition half), H18, H22, H25, H29, H31-H32 (generating branch), and H36. No C or X step is lease-dependent.

**Request-ID-dependent steps:** H03, H06-H10, H16, H18, H21-H22, H24-H25, H27-H30, H31-H38, C02, C08 structurally, C11's request companion transition, C15, and C17. H24/H26's *revision recheck* is semantically independent; only its current carrier is the request row. No X step is request-ID-dependent.

**Neither:** H02, H04, H11-H15, H19-H20 after the request field is removed, H23, H26's semantic revision guard, C03-C07, C09-C10 after proposal schema repair, C12-C14, C16, and every X step. These are the reusable spine: canonical scope validation, current-revision lookup/recheck, promoted-set validation/evaluation, out-of-transaction candidate generation, proposal/evidence persistence, conflict quarantine, and audit events.

## S3 RESULT/MODEL SURFACE

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S3-001 | src/cement_runtime/models.py:52 | `class Candidate:` | type | keep | Candidate-source result; fields = `output`, `provenance`; no status. It survives on the explicit submission path, not `resolve`. |
| S3-002 | src/cement_runtime/models.py:60 | `class CandidateRequest:` | type | rewrite | Candidate-source input, included because it is the boundary paired with S3-001; fields = `partition`, `operation`, `operation_revision`, `request_id`, `input`. Only `request_id` is lifecycle-only. |
| S3-003 | src/cement_runtime/models.py:69 | `class Resolved:` | type | rewrite | Fields = `request_id`, `output`, `source`, `artifact_id`, `example_id`, `status`; status = `resolved`. `request_id` is lifecycle-only. `source="confirmed"` and `example_id` exist for cached request replay. A pure current-function resolver retains the output/match concept, not this shape unchanged. |
| S3-004 | src/cement_runtime/models.py:75 | `Literal["resolved"] = "resolved"` | status | rewrite | Tag is optional if `resolve` returns existing `FunctionMatch`; retain only if MAIN deliberately wants a tagged hit type. |
| S3-005 | src/cement_runtime/models.py:79 | `class ReviewRequired:` | type | rewrite | Fields = `request_id`, `proposal_id`, `status`; status = `review_required`. `request_id` is lifecycle-only. It has no referent in pure `resolve`; an explicit submission acknowledgement may retain only `proposal_id`. |
| S3-006 | src/cement_runtime/models.py:82 | `Literal["review_required"] = "review_required"` | status | rewrite | Must move to submission-only vocabulary if retained. |
| S3-007 | src/cement_runtime/models.py:86 | `class InProgress:` | type | delete | Fields = `request_id`, `retry_after_seconds`, `status`; status = `in_progress`. Every field exists to poll a generation lease. No referent after caller-owned lifecycle. |
| S3-008 | src/cement_runtime/models.py:89 | `Literal["in_progress"] = "in_progress"` | status | delete | Lease status has no pure resolver or proposal-review meaning. |
| S3-009 | src/cement_runtime/models.py:93 | `class FallbackFailed:` | type | delete | Fields = `request_id`, `code`, `status`; status = `fallback_failed`. It reports a persisted source failure and retry eligibility. No referent after direct submission failure. |
| S3-010 | src/cement_runtime/models.py:96 | `Literal["fallback_failed"] = "fallback_failed"` | status | delete | Candidate-source exceptions need their own direct error contract, not a durable request state. |
| S3-011 | src/cement_runtime/models.py:100 | `class Rejected:` | type | delete | Fields = `request_id`, `proposal_id`, `status`; status = `rejected`. Proposal rows still record rejection, but this request-outcome projection has no referent. |
| S3-012 | src/cement_runtime/models.py:103 | `Literal["rejected"] = "rejected"` | status | delete | Keep the proposal-table literal; delete only this public request result literal. |
| S3-013 | src/cement_runtime/models.py:107 | `class ReconciliationRequired:` | type | delete | Fields = `request_id`, `reason`, `artifact_id`, `example_id`, `status`; status = `reconciliation_required`. All fields explain why a cached prior request answer is unsafe. A pure resolver returns current hit/miss and caches nothing. |
| S3-014 | src/cement_runtime/models.py:112 | `Literal["reconciliation_required"] = "reconciliation_required"` | status | delete | Caller reconciles its own effects and stale cache; Cement no longer materializes this state. |
| S3-015 | src/cement_runtime/models.py:115 | `Outcome: TypeAlias = (` | type | delete | Mixed union joins resolution, submission, polling, failure, rejection, and reconciliation. Split methods need method-specific return types. |
| S3-016 | src/cement_runtime/models.py:126 | `class ProposalView:` | type | rewrite | Review-surface result; fields = `id`, `partition`, `operation`, `operation_revision`, `request_id`, `input`, `proposed_output`, `provenance`, `created_at_us`. Only `request_id` is lifecycle-only; the remaining direct scope/input fields survive. |
| S3-017 | src/cement_runtime/function.py:76 | `class FunctionMatch:` | type | keep | Existing M2 pure evaluator result; fields = `matched`, `output`, `artifact_hash`; no status or request identity. This is the natural `resolve` result unless ledger resolution needs an additional provenance wrapper. |
| S3-018 | src/cement_runtime/function.py:381 | `def evaluate(` | call | keep | Pure exact lookup returns S3-017 hit/miss without a ledger write. The M3 seed explicitly sequences this track after M2's evaluator. |
| S3-019 | src/cement_runtime/system.py:4583 | `def challenge(` | type | keep | Reachable governance result is a plain `tuple[str, bool]`, not a dataclass: `example_id`, `suspended`. It has no lifecycle-only field. |
| S3-020 | src/cement_runtime/__init__.py:77 | `"FallbackFailed"` | export | delete | Definite public export removal. Its import at line 35 must disappear too. |
| S3-021 | src/cement_runtime/__init__.py:98 | `"InProgress"` | export | delete | Definite public export removal. Its import at line 47 must disappear too. |
| S3-022 | src/cement_runtime/__init__.py:107 | `"ReconciliationRequired"` | export | delete | Definite public export removal. Its import at line 54 must disappear too. |
| S3-023 | src/cement_runtime/__init__.py:108 | `"Rejected"` | export | delete | Definite request-result export removal. Proposal records continue to use rejection internally. Its import at line 55 must disappear too. |
| S3-024 | src/cement_runtime/__init__.py:66 | `"CandidateRequest"` | export | rewrite | Public symbol survives only with its request-ID field removed. |
| S3-025 | src/cement_runtime/__init__.py:109 | `"Resolved"` | export | undecided-MAIN | Delete if `System.resolve` returns S3-017 directly; otherwise rewrite as a request-free ledger match result. It cannot survive unchanged. |
| S3-026 | src/cement_runtime/__init__.py:110 | `"ReviewRequired"` | export | undecided-MAIN | Delete if submission returns `ProposalView`/proposal ID; otherwise rewrite as a request-free submission result. It cannot remain a resolver outcome. |
| S3-027 | src/cement_runtime/__init__.py:106 | `"ProposalView"` | export | rewrite | Retain after removing `request_id` and making proposal rows own scope/input directly. |
| S3-028 | src/cement_runtime/__init__.py:88 | `"FunctionMatch"` | export | keep | Already-public target result for pure exact evaluation. |

**Survival verdict:** `Candidate` and a request-free `CandidateRequest` survive explicit submission. A request-free `ProposalView` survives review. `FunctionMatch` survives pure `resolve` unchanged. `Resolved` survives only as a concept and must either map to `FunctionMatch` or become a new request-free wrapper. `ReviewRequired` can survive only on submission. `InProgress`, `FallbackFailed`, request-result `Rejected`, `ReconciliationRequired`, and the cross-method `Outcome` union have no referent afterwards. Definite `__init__.py` removals are S3-020..S3-023; S3-025..S3-026 are explicit MAIN forks rather than hidden design assumptions.

## S4 NORMATIVE CLAIMS

| id | anchor | quote | falsified_by | note |
|---|---|---|---|---|
| S4-R01 | README.md:14 | `handle(request)` | split API | Opening diagram must show separate `resolve(input)` hit/miss and explicit proposal submission. |
| S4-R02 | README.md:16 | `no safe match → LLM proposal` | pure resolver | A miss becomes inert; it cannot invoke a source or write a proposal. |
| S4-R03 | README.md:37 | The ordinary `handle` result exposes a proposal ID | no `handle` mixed result | Replace with a submission-only visibility claim. `resolve` exposes no proposal. |
| S4-R04 | README.md:49 | `runtime integrity failure quarantine affected` | pure read-only resolve | Resolver cannot quarantine in-band. The doc must separate fail-closed read verdict from a later mutating quarantine/governance action. |
| S4-R05 | README.md:51 | `Request IDs are partition-local idempotency keys bound to immutable operation and input content.` | caller-owned lifecycle | **Load-bearing deletion:** Cement no longer supplies this key namespace, uniqueness, content binding, or replay. |
| S4-R06 | README.md:52 | `Candidate generation runs outside database transactions under a recoverable lease.` | lease removal | Preserve “outside database transactions” for submission; delete “under a recoverable lease.” |
| S4-R07 | README.md:93 | `uv run cement --db demo.db --partition acme handle support.reply \` | CLI split | Quick start needs a `resolve` miss followed by an explicit proposal-submission command. |
| S4-R08 | README.md:94 | `--request-id ticket-001 \` | caller-owned lifecycle | Flag disappears. If an adapter needs tracing/idempotency, its wrapper owns that input. |
| S4-R09 | README.md:99 | A miss returns `review_required` and a proposal ID. | pure resolver | Honest result is an inert miss. Proposal creation requires a separate explicit action. |
| S4-R10 | README.md:108 | `Repeat with a distinct request ID` | no core request ID | Repeat explicit proposal submission as needed; caller deduplicates attempts. |
| S4-R11 | README.md:181 | `outcome = system.handle(` | library API split | Example must call `resolve` and proposal submission separately. |
| S4-R12 | README.md:185 | `request_id="ticket-123/attempt-1"` | request field removal | Remove from core API. Caller may retain the token in its own effect/request layer. |
| S4-R13 | README.md:195 | `handle` and `request` return explicit states: | deleted methods/union | Replace the six-state request table with separate resolve and proposal-submission/review result contracts. |
| S4-R14 | README.md:199 | `Current promoted artifact or still-valid confirmed fixture produced the output.` | no cached confirmed-request replay | Pure resolve answers only from the current promoted function. A confirmed fixture remains evidence, not a direct cached answer. |
| S4-R15 | README.md:200 | `A hidden candidate awaits supervision.` | split API | Retain only as submission/review semantics, not a resolver outcome. |
| S4-R16 | README.md:201 | `This partition's generation lease is active.` | lease removal | Delete row and polling instruction. |
| S4-R17 | README.md:202 | `The candidate source failed, or its generation lease expired` | direct failure | Delete durable status/retry directions; define the submission call's direct error/rollback behavior. |
| S4-R18 | README.md:203 | `Use a new request ID to request another candidate.` | no core request ID | Proposal rejection remains audit state; caller decides whether and how to submit again. |
| S4-R19 | README.md:204 | `Cement returns no cached output.` | no cached request output | Delete `reconciliation_required`; caller owns stale effects/caches and sees only current hit/miss. |
| S4-R20 | README.md:206 | `Replaying a request ID is content-idempotent.` | no replay surface | Delete the paragraph. No weaker wording may imply core deduplication. |
| S4-R21 | README.md:207 | move a prior request to `reconciliation_required` | no request state machine | Replace with current-state resolver behavior and caller reconciliation obligation. |
| S4-R22 | README.md:208 | `Another partition can` | no request namespace | The cross-partition request-ID independence claim disappears with the namespace. |
| S4-R23 | README.md:282 | `handle` and read APIs assume | renamed/split API | Name `resolve` and proposal submission explicitly; both still rely on embedding-service partition authorization unless track (b) changes the surrounding wording. |
| S4-A01 | docs/architecture.md:9 | `Resolve only one integrity-valid promoted artifact` | M2 function evaluator target | Keep the exact-scope intent; update “artifact” to current promoted function/match if `resolve` aggregates M2 entries. |
| S4-A02 | docs/architecture.md:11 | `Otherwise reserve the idempotent request` | pure resolver | Rewrite step 3: resolver returns a miss; a separate explicit submission invokes the candidate source and stores a pending proposal. |
| S4-A03 | docs/architecture.md:12 | `and store a pending proposal.` | split action | Still true only for the explicit submission method. |
| S4-A04 | docs/architecture.md:70 | `Request IDs are unique within a partition` | caller-owned lifecycle | Delete uniqueness/content-binding contract. |
| S4-A05 | docs/architecture.md:71 | `A revision invalidates every older request path.` | no request paths | Replace with current-revision resolution and proposal-review rules. |
| S4-A06 | docs/architecture.md:72 | `withholds cached output and cancels generators` | no cache/lease | Delete. Resolver never returns an old cached answer; caller cancels its own work. |
| S4-A07 | docs/architecture.md:73 | `Callers reconcile prior effects and use a new request ID` | caller owns both | Retain reconciliation obligation, but remove the prescribed Cement request ID. |
| S4-A08 | docs/architecture.md:121 | `Candidate generation holds no lock.` | submission no-lock boundary | Keep and bind explicitly to proposal submission. |
| S4-A09 | docs/architecture.md:121 | `A lease permits recovery after a crashed generator` | lease removal | Delete; crash recovery and duplicate suppression move to caller. |
| S4-A10 | docs/architecture.md:122 | `generator cannot overwrite a proposal claimed by another lease owner.` | no owner fencing | Replace only if submission gains a different optimistic revision/content guard; do not imply stale-worker fencing unless measured and implemented. |
| S4-T01 | docs/threat-model.md:75 | `Treat results as plans.` | unaffected | Keep. Both pure resolution and offline evaluation return data, not effects. |
| S4-T02 | docs/threat-model.md:76 | `request ID as an idempotency key.` | no Cement request ID | Say “Use a caller-owned idempotency key for effect execution.” Cement no longer stores or validates it. |
| S4-T03 | docs/threat-model.md:76 | `Stop for reconciliation after uncertain effect commit state.` | unaffected obligation | Keep, but make clear that Cement no longer emits a reconciliation status. |
| S4-T04 | docs/threat-model.md:77 | `Model calls can repeat after timeout or lease recovery.` | caller-owned retries | Replace lease recovery with caller retry/crash recovery; purity requirement remains. |
| S4-P01 | docs/adapter-protocol.md:13 | `"request_id": "ticket-123"` | CandidateRequest field removal | Remove from core envelope. Track (a) relocates this document, but relocated examples must not preserve a false core field. |
| S4-P02 | docs/adapter-protocol.md:36 | becomes an inert `fallback_failed` request. | direct submission error | Replace with the explicit submission error contract. |
| S4-P03 | docs/adapter-protocol.md:54 | `expired generation lease` | lease removal | Delete core retry/recovery language. |
| S4-P04 | docs/adapter-protocol.md:55 | `request_id` is partition-local | no core namespace | Delete provider-side core idempotency/tracing promise. Optional wrappers may define their own token. |
| S4-P05 | docs/adapter-protocol.md:57 | `(partition, request_id)`. | no core envelope field | Delete or relocate as wrapper-specific guidance with a wrapper-owned field. |
| S4-E01 | examples/hospital_ocr/README.md:20 | `System.handle(...)` | API split | Diagram must show `resolve` miss, then explicit proposal submission. |
| S4-E02 | examples/hospital_ocr/README.md:33 | `System.handle(...)` either returns | pure resolver | Split teaching step 3 into read resolution and proposal submission. |
| S4-E03 | examples/hospital_ocr/README.md:174 | `adapter proposed a plan; records-supervisor review is required.` | changed driver/control flow | Meaning can survive, but text must be regenerated from the new explicit submission path. |
| S4-E04 | examples/hospital_ocr/README.md:176 | `the same layout recurred; its plan again requires supervision.` | no request IDs, same evidence requirement | Semantic claim likely survives; transcript still changes if command/event wording changes. |
| S4-E05 | examples/hospital_ocr/README.md:185 | `unseen intake-form layout used the same supervised fallback.` | no automatic fallback | Must say the miss triggered a separate explicit submission. |
| S4-E06 | examples/hospital_ocr/README.md:208 | `09. request.resolved_by_artifact` | deleted request event | Pinned transcript loses this event, and the second occurrence at line 216. |
| S4-E07 | examples/hospital_ocr/README.md:235 | `enters supervised fallback` | no automatic fallback | Replace with “returns a miss, then enters explicit proposal submission.” |
| S4-E08 | examples/hospital_ocr/README.md:246 | `lifecycle driver` | caller-owned request lifecycle | Rename/rewrite pointer description; the demo remains a supervision/compile/function driver. |
| S4-C01 | src/cement_runtime/cli.py:74 | `Supervised LLM fallback that compiles confirmed behavior` | no mixed fallback command | Root help must describe supervised proposal capture plus deterministic resolution, not automatic fallback. |
| S4-C02 | src/cement_runtime/cli.py:100 | `route or create an inert LLM proposal` | split commands | Replace `handle` with distinct resolver and submission leaves. |
| S4-C03 | src/cement_runtime/cli.py:103 | `handle.add_argument("--request-id")` | no core request ID | Delete option/help usage. |
| S4-C04 | src/cement_runtime/cli.py:104 | `handle.add_argument("--retry-failed"` | no stored failures | Delete option/help usage. |
| S4-C05 | src/cement_runtime/cli.py:129 | `poll a request without resupplying input` | no polling surface | Delete `request` command. |
| S4-C06 | src/cement_runtime/cli.py:130 | `request.add_argument("request_id")` | no request command | Delete positional/help usage. |
| S4-C07 | src/cement_runtime/cli.py:112 | `inspect/review supervised proposals` | explicit proposal path | Keep; ensure new submission command points here. |
| S4-C08 | src/cement_runtime/cli.py:145 | `confirm or counterexample an active artifact` | independent challenge | Keep; challenge has no request/lease dependency. |

### Load-bearing replacement claim

The current README guarantee at S4-R05/R06 gives callers seven bundled services: (1) a partition-scoped ID namespace; (2) immutable operation/input binding; (3) content-idempotent replay; (4) concurrent candidate suppression; (5) crash recovery through lease expiry/reclaim; (6) stale-generator write fencing; and (7) persisted polling, retry, cached-result, and reconciliation states. Track (c) removes all seven. Provider-side tracing/idempotency via the same ID also disappears. The caller must not infer any of them from proposal IDs or SQLite transactions.

An honest replacement must say substantially: **“`resolve` reads one current promoted-function snapshot and returns one exact match or an inert miss without mutating the ledger. Proposal submission is a separate explicit action. Candidate generation holds no database transaction. Cement does not allocate, bind, deduplicate, lease, poll, retry, cache, or reconcile caller requests. The caller owns request/effect idempotency, concurrent-attempt suppression, retry/backoff, crash recovery, cancellation, provider tracing, and reconciliation of uncertain effects.”** The proposal action may additionally promise an optimistic operation-revision recheck, but only after its exact behavior is selected and tested.

CLI help audit: invoked `--help` at every parser node: root, all intermediate groups, and every leaf (**35 surfaces**); all returned exit 0. Request/lease semantics occur only on root, `handle`, and `request`, captured by S4-C01..S4-C06. Proposal/challenge review wording is request-independent and captured by S4-C07..S4-C08. The other 32 surfaces expose no request/lease contract; they need only command-census or cross-reference updates after the split.

## S5 TEST BURDEN

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S5-F01 | tests/test_system.py:209 | `def confirm(` | test | rewrite | Category (ii) fixture: `handle` → proposal read → accept/correct. Transitive fan-out = 29 tests / 824 source lines. |
| S5-F02 | tests/test_system.py:236 | `def mature_and_promote(` | test | rewrite | Category (ii) fixture above the confirmation helper. Fan-out = 8 tests / 171 lines. |
| S5-F03 | tests/test_system.py:1369 | `def _confirm_scope(` | test | rewrite | Category (ii) M2 fixture: explicit scope confirmation through `handle`. Fan-out = 192 tests / 11,440 lines. |
| S5-F04 | tests/test_system.py:1402 | `def _promote_scope(` | test | rewrite | Category (ii) helper transitively reaches `_confirm_scope`; fan-out = 40 tests / 2,329 lines. |
| S5-F05 | tests/test_system.py:1659 | `def _promote_three_as_function(` | test | rewrite | Category (ii) helper transitively reaches `_confirm_scope`; fan-out = 86 tests / 5,279 lines. |
| S5-F06 | tests/test_system.py:1673 | `def _promote_scope_as_function(` | test | rewrite | Category (ii) helper transitively reaches `_confirm_scope`; fan-out = 3 tests / 169 lines. |
| S5-F07 | tests/test_cli.py:217 | `def confirm(` | test | rewrite | Category (ii) CLI fixture invokes `handle --request-id --source-command`, then review. Fan-out = 100 tests / 2,298 lines. |
| S5-F08 | tests/test_cli.py:247 | `def handle_once(` | test | rewrite | Category (ii) CLI fixture creates one pending/reviewed proposal through `handle`; fan-out = 4 tests / 212 lines. |
| S5-F09 | tests/test_cli.py:299 | `def promoted_operation(` | test | rewrite | Subset of F07; fan-out = 85 tests / 1,895 lines. |
| S5-F10 | tests/test_cli.py:307 | `def compile_drafts(` | test | rewrite | Subset of F07; fan-out = 13 tests / 338 lines. |
| S5-F11 | tests/test_cli.py:2955 | `def confirm_text(` | test | rewrite | Category (ii) non-ASCII confirmation fixture; fan-out = 2 tests / 28 lines. |
| S5-F12 | tests/test_hospital_ocr_example.py:353 | `def request(` | test | rewrite | Category (ii) fixture for 8 `PlanAdapterTests`; remove `CandidateRequest.request_id`. |
| S5-F13 | tests/test_hospital_ocr_example.py:628 | `request_id=f"seed-{index:02d}"` | test | rewrite | Category (ii) promoted-ledger fixture for all 6 `OfflineBundleTests` plus the shipped CLI round-trip. |
| S5-D01 | tests/test_system.py:325 | `test_confirmed_request_cache_is_bound_to_immutable_example` | test | delete | Category (i): corrupts cached request output and expects reconciliation; 29 lines. |
| S5-D02 | tests/test_system.py:355 | `test_artifact_request_cache_is_bound_to_current_execution` | test | delete | Category (i): validates cached artifact answer replay; 39 lines. |
| S5-D03 | tests/test_system.py:474 | `test_quarantined_artifact_cannot_replay_an_old_idempotency_key` | test | delete | Category (i): request-ID replay invalidation; 19 lines. Current `resolve` safety needs a different read-only test. |
| S5-D04 | tests/test_system.py:517 | `test_request_idempotency_and_partition_isolation` | test | delete | Category (i): pins ID content binding, deduplication, and partition-local namespace; 18 lines. |
| S5-D05 | tests/test_system.py:572 | `test_concurrent_retry_observes_generation_lease` | test | delete | Category (i): pins `InProgress` and concurrent generator suppression; 19 lines. |
| S5-D06 | tests/test_system.py:592 | `test_expired_generation_poll_is_retryable_and_handle_reclaims` | test | delete | Category (i): pins polling, expiry, reclaim, and stale-worker result equality; 30 lines. |
| S5-D07 | tests/test_system.py:623 | `test_missing_or_broken_source_is_a_stored_inert_failure` | test | delete | Category (i): pins durable `fallback_failed` replay; 9 lines. New direct submission error tests replace it. |
| S5-D08 | tests/test_system.py:685 | `test_unknown_resolved_source_kind_fails_closed_at_storage` | test | delete | Category (i): corrupts the removed request cache's source tag; 16 lines. |
| S5-D09 | tests/test_system.py:777 | `test_operation_revision_invalidates_every_old_request_path` | test | delete | Category (i): 57-line request-state matrix. Preserve its obsolete-proposal-review subclaim in a narrower category-(ii) replacement. |
| S5-D10 | tests/test_system.py:835 | `test_revision_cancels_in_flight_old_generation` | test | delete | Category (i): revision-driven lease cancellation and reconciliation result; 26 lines. |
| S5-D11 | tests/test_system.py:1177 | `test_review_rejects_cross_table_state_corruption` | test | delete | Category (i): pins proposal/request lockstep that cannot exist after schema split; 19 lines. |
| S5-R01 | tests/test_system.py:260 | `test_supervised_miss_to_exact_artifact_hit` | test | rewrite | Category (ii) representative: keep end-to-end supervision and exact hit, but assert `resolve` miss separately from submission. |
| S5-R02 | tests/test_system.py:279 | `test_dispatch_uses_sealed_promotion_receipt_without_rehashing_tests` | test | rewrite | Category (ii): pins dispatch integrity through `handle`; retarget to pure `resolve`. |
| S5-R03 | tests/test_system.py:292 | `test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence` | test | rewrite | Category (ii): safety claim survives; split resolver result from submission/review result. |
| S5-R04 | tests/test_system.py:304 | `test_proposal_content_hashes_fail_closed_on_storage_mutation` | test | rewrite | Category (ii): proposal integrity survives after scope/input move onto `proposals`. |
| S5-R05 | tests/test_system.py:433 | `test_counterexample_and_revocation_quarantine` | test | rewrite | Category (ii): quarantine survives, automatic fallback does not. Assert a later read-only miss/failure verdict. |
| S5-R06 | tests/test_system.py:536 | `test_monotonic_feeds_survive_transitions_and_clock_rollback` | test | rewrite | Category (ii): feed guarantee survives, request event vocabulary changes. |
| S5-R07 | tests/test_system.py:638 | `test_public_scalar_validation_fails_with_domain_errors` | test | rewrite | Category (ii): remove lease/retry/request cases and retain unrelated validation cases. |
| S5-R08 | tests/test_system.py:702 | `test_receipt_can_bind_individually_valid_large_input_and_output` | test | rewrite | Category (ii): receipt bound survives through new submission fixture. |
| S5-R09 | tests/test_system.py:716 | `test_runtime_integrity_failure_quarantines_then_falls_back` | test | rewrite | Category (ii): pure resolver forbids in-band mutation; separate verdict and quarantine behavior. |
| S5-R10 | tests/test_system.py:761 | `test_operation_revision_retires_old_artifacts` | test | rewrite | Category (ii): retirement survives; final `handle` assertion becomes `resolve` miss. |
| S5-R11 | tests/test_system.py:1125 | `test_authority_denial_precedes_control_plane_mutation` | test | rewrite | Category (ii): proposal creation fixture changes; track (b) separately removes authority. |
| S5-R12 | tests/test_system.py:13773 | `test_function_report_public_shape_is_exact_frozen_slotted_and_exported` | test | rewrite | Category (ii): remove `PendingProposalGap.request_id` and pin replacement shape. |
| S5-R13 | tests/test_system.py:15298 | `test_function_report_pending_proposals_bind_partition_operation_request_and_revision` | test | rewrite | Category (ii): preserve exact partition/operation/revision isolation while replacing request binding with direct proposal scope/input binding. |
| S5-R14 | tests/test_system.py:15388 | `test_function_report_pending_count_reaches_the_10001_tail_with_bounded_detail` | test | rewrite | Category (ii): 10,001-row sentinel directly inserts both request and proposal rows; regenerate against proposal-only schema. |
| S5-R15 | tests/test_system.py:17069 | `test_function_report_pending_rows_validate_middle_and_last_scalars_and_bindings` | test | rewrite | Category (ii): mutation probes move from joined request scalars to proposal-owned scalars. |
| S5-R16 | tests/test_system.py:17180 | `test_function_report_pending_request_join_is_like_and_case_exact` | test | rewrite | Category (ii): retain `=`-not-`LIKE` scope-isolation probes without a request join. |
| S5-R17 | tests/test_cli.py:378 | `test_full_operator_lifecycle` | test | rewrite | Category (ii): whole CLI spine survives, but `handle`/`request` split and result payloads change. |
| S5-R18 | tests/test_cli.py:462 | `test_usage_errors_and_oversized_stdin_are_machine_readable` | test | rewrite | Category (ii): retain bounded stdin on the new input-taking leaf. |
| S5-R19 | tests/test_cli.py:586 | `test_function_show_projects_every_detail_family_under_limit` | test | rewrite | Category (ii): pending projection loses `request_id`. `_PENDING_KEYS` changes. |
| S5-R20 | tests/test_cli.py:2251 | `test_function_inspect_emits_the_tail_beyond_one_hundred_entries` | test | rewrite | Category (ii): direct `System.handle` fixture becomes explicit submission. |
| S5-R21 | tests/test_hospital_ocr_example.py:366 | `test_known_layout_plans_match_reference_extraction_for_each_layout` | test | rewrite | Category (ii) representative for all 8 `PlanAdapterTests`; only their shared request factory should need structural edits. |
| S5-R22 | tests/test_hospital_ocr_example.py:686 | `class OfflineBundleTests` | test | rewrite | Category (ii): all 6 tests pin offline behavior through a class fixture that first builds evidence with `handle`; offline assertions themselves remain. |
| S5-R23 | tests/test_hospital_ocr_example.py:806 | `class ShippedCommandRoundTripTests` | test | rewrite | Category (ii): one test consumes the same promoted-ledger fixture. |
| S5-R24 | tests/test_hospital_ocr_example.py:913 | `class DemoTranscriptTests` | test | rewrite | Category (ii): all 3 tests execute the rewritten demo; one pins exact masked transcript and one pins post-teardown ordering. |
| S5-K01 | tests/test_system.py:1197 | `test_schema_version_without_matching_schema_fails_at_open` | test | keep | Category (iii) representative: schema failure behavior remains, though its fixture's expected version value may bump. Classified unaffected by request/lease behavior. |
| S5-K02 | tests/test_cli.py:455 | `test_machine_readable_error` | test | keep | Category (iii) representative: unrelated CLI error mapping. |
| S5-K03 | tests/test_hospital_ocr_example.py:149 | `class SignatureCanonicalizationTests` | test | keep | Category (iii): 6 signature tests. |
| S5-K04 | tests/test_hospital_ocr_example.py:226 | `class ExtractionTests` | test | keep | Category (iii): 4 extraction tests. |
| S5-K05 | tests/test_hospital_ocr_example.py:332 | `class CementJSONV1Tests` | test | keep | Category (iii): 1 canonical-JSON test. |
| S5-X01 | tests/test_system.py:256 | `promoted_by="release-manager"` | test | keep | Raw `lease` substring false positive. The surrounding method is category (ii) for another reason. |
| S5-X02 | tests/test_system.py:4018 | `release = threading.Event()` | test | keep | Raw `lease` substring is a local synchronization name, unrelated to generation leases. |
| S5-X03 | tests/test_cli.py:295 | `promoted_by="release-manager"` | test | keep | All 26 CLI `lease` hits are `release-manager`/`release manager` false positives. |
| S5-X04 | tests/test_cli.py:733 | `_request_id` | test | keep | One of 5 CLI `request_id` hits names the generic entity-ID validator, not lifecycle behavior. |
| S5-X05 | tests/test_cli.py:3239 | `request_id must be a bounded ASCII identifier` | test | keep | Second generic-validator false positive; receipt-ID grammar test need not change unless MAIN renames the helper/message. |

### Measured classification and rewrite estimate

Classification unit = every `test_*` method in the three requested test files, with class fixtures propagated transitively. Category (i) means delete; category (ii) means the test protects surviving behavior through a lifecycle fixture/schema/result and must be rewritten; category (iii) means unaffected by track (c).

- `tests/test_system.py`: **11 (i), 228 (ii), 57 (iii) = 296**. The affected transitive closure is 239 methods / 13,316 source lines. Category-(i) methods are exhaustively S5-D01..S5-D11 and total exactly **281 lines**. Category (ii) is the remaining affected closure rooted at F01..F06 plus the direct families represented by R01..R16. Category (iii) is the 57-method complement.
- `tests/test_cli.py`: **0 (i), 104 (ii), 82 (iii) = 186**. The raw closure was 106; S5-X04/X05 are generic-validator false positives. F07-F11 plus direct split-command tests cover category (ii).
- `tests/test_hospital_ocr_example.py`: **0 (i), 18 (ii), 11 (iii) = 29**. Category (ii) = 8 adapter tests + 6 offline tests + 1 shipped-command test + 3 demo tests. Category (iii) = K03-K05.
- **Combined three-count line: (i) 11; (ii) 350; (iii) 150; total 511 methods.**

Raw required census: `request_id` = system **95** + CLI **5** lines. All 95 system hits feed category (i)/(ii). CLI has 3 real pending-proposal/fixture hits and the 2 generic-validator false positives S5-X04/X05. Raw `lease` = system **59** + CLI **26** lines. Only four system lines are semantic generation-lease references (test name at 572, constructor at 598, expiry code at 614, constructor validation at 640); the other 55 system lines and all 26 CLI lines are `release-manager`, `release`, or synchronization-name collisions.

Rewrite-size evidence: category-(ii) dependency exposure is **15,926 test source lines** (13,035 system after category-(i) subtraction + 2,451 CLI after false-positive subtraction + 440 example). Fixture reuse prevents equal textual churn. There are **230 direct lifecycle anchor lines** across the files. Budget **780-1,130 changed/deleted test lines**: exact 281-line deletion set plus roughly 500-850 lines to rewrite fixtures, direct result/status assertions, proposal-only bulk rows, CLI command payloads, and the pinned example. This is the milestone's dominant implementation cost even though most of the 350 category-(ii) methods should remain byte-stable after their shared fixture changes.

## S6 ARCHAEOLOGY

| id | sha | subject | relevance |
|---|---|---|---|
| S6-001 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | Root commit. Lifecycle lands whole: `requests`, lease columns, partition-local request-ID replay, `handle`, `_fail_generation`, `_outcome`, `request_status`, request-bound `review`, and `challenge`. No earlier commit exists. |
| S6-002 | bcbb8cb | example (M1.2): in-process plan proposer adapter (CandidateSource) | M1 adds the hospital example's source adapter only. Core dispatch bytes do not change. It becomes a consumer that track (c) must update. |
| S6-003 | dffc065 | example (M1.3): hospital OCR lifecycle demo driver | M1 adds `run_demo.py` calls to `handle`/review. Core dispatch bytes do not change. This is the main example rewrite surface. |
| S6-004 | 6f4f260 | example (M1 review): fix layout signature canonicalization + gate-cover the example | M1 closes with example/pipeline/test fixes. `system.py` has no M1 commit at all. |
| S6-005 | 71c5eab | roadmap (M2 plan): reconcile the project to README paragraph 1 | Planning predecessor. It schedules function-as-object before later trims; no dispatch code change. |
| S6-006 | a5c8494 | function (M2.1): cement-function-v1 document, hash, and pure evaluator | Adds `FunctionDocument`, `FunctionMatch`, and pure `evaluate`; this is the replacement resolver target. It does not touch `system.py`, `store.py`, or `handle`. |
| S6-007 | 84cb9c6 | function (M2.2): read-only set-level verification of the promoted function | First M2 commit touching `system.py`; adds set verification adjacent to runtime dispatch. `handle` and its called validation helpers remain byte-identical. |
| S6-008 | 9e09f4c | function (M2.3a): pre-promotion entry identity, draft eligibility, batch verify | Adds entry identity and batch verification. M2 archive explicitly records `cement-promotion-v2`'s dispatch fast path as untouched. No lifecycle-path byte changes. |
| S6-009 | b3159a6 | function (M2.3b1): persisted set promotion core, plus its review findings | Bumps schema 1 → 2 and adds function receipts/memberships. The `requests` table remains byte-identical. Adds promotion core, not request dispatch. |
| S6-010 | cf274a4 | function (M2.3b1): close the promotion core on its accepted review findings | Fixes set-promotion defects only. No lifecycle-path byte changes. |
| S6-011 | b87dde0 | function (M2.3b2): persisted receipt verification and historical reconstruction | Adds receipt validation/reconstruction. No lifecycle-path byte changes. |
| S6-012 | d0b7e93 | function (M2.4a): receipt discovery, plus the u4 three-way split | Adds read discovery. No lifecycle-path byte changes. |
| S6-013 | 62e6d09 | function (M2.4b): coverage + gap report core over both temporal anchors | Adds `function_report`, including pending-proposal joins through `requests`; this materially expands track (c)'s consumer/test rewrite, but does not alter `handle`, review, challenge, or request schema. |
| S6-014 | ce006f2 | example (M2.5a): resolve a layout offline from the exported bundle | Proves the M2 evaluator in the hospital example and creates `resolve_offline`. It changes example control flow, not core request dispatch. |
| S6-015 | e5ff481 | docs (M2.5b): repair four false claims and document the function layer | Documents M2 function behavior. No dispatch code change; several request-lifecycle claims remain for M3. |
| S6-016 | 83198e1 | function (M2 review): close M2 with four fixes and one claim pass | M2 close changes CLI/example/tests/docs only. Core lifecycle path remains unchanged. |

### Verdict on the roadmap assertion

**REFUTE, if “M2 reshapes the dispatch path” means the current core `handle`/confirmation/challenge implementation.** Byte extraction from five snapshots (`3b7769b`, `6f4f260`, `71c5eab`, `83198e1`, `HEAD`) found identical SHA-256 prefixes and lengths for all ten path functions:

- `handle` `cd60036faf5c` / 12,867 bytes;
- `_fail_generation` `15a6f8a31a97` / 1,360;
- `_outcome` `383d388c280a` / 5,926;
- `_request_revision_is_current` `1b01e2c5dbde` / 450;
- `_proposal_content` `7363258da122` / 742;
- `_validate_proposal_shape` `ae8e7bac0d34` / 1,314;
- `review` `6f9a8e65ca68` / 10,223;
- `challenge` `c59921bc7e27` / 6,999;
- `_validate_promoted` `7d86caf1ff7a` / 3,674;
- `_artifact_from_row` `b33b98de7743` / 1,901.

The `requests` table is also byte-identical at all five snapshots: `97190cf406eaa75e` / 2,265 bytes. `git log -L` assigns `handle` and `_validate_promoted` only to root SHA `3b7769b`; `git log -- system.py` shows no M1 touches and seven M2 adjacent additions (S6-007..S6-013), none in the path bytes.

**The scheduling conclusion is still correct for a different reason.** M2 added the pure `FunctionMatch`/`evaluate` target at `a5c8494`, persisted the promoted function at `b3159a6`, and expanded pending-proposal reporting at `62e6d09`. Track (c) should therefore happen after M2 to reuse the evaluator and must rewrite M2's report consumers. The unit plan should correct the causal wording: “M2 supplies the resolver target and adds request-bound report consumers,” not “M2 reshaped `handle`.”

## S7 HAZARDS + OPEN FORKS

A unit plan must settle the following forks explicitly. Each item names the alternatives and the deciding measurement.

1. **“Pure read-only” must mean write-impossible plus one snapshot, not `write=False`.** `Store.transaction(write=False)` opens ordinary `BEGIN` at `src/cement_runtime/store.py:555` and unconditionally commits at `src/cement_runtime/store.py:562`; SQLite can upgrade that transaction after an injected write. The repo already has four useful mechanisms: (a) one `write=False` transaction around `verify_function` at `src/cement_runtime/system.py:2971`; (b) SQLite write-opcode denial through `connection.set_authorizer(authorize)` at `tests/test_system.py:11187` and `tests/test_system.py:15977`; (c) full-ledger byte/logical comparison through `tuple(connection.iterdump())` at `tests/test_system.py:198`; and (d) one-snapshot lifetime pins through `connection.in_transaction` at `tests/test_system.py:10965` and `tests/test_system.py:15941`. Alternatives: **A**, install a write-denying authorizer only inside `System.resolve`; **B**, add a reusable enforced-read transaction in `Store` and use it for every strong read-only claim; **C**, rely on code review plus dump comparison only. Recommend B because the guarantee is structural and reusable; C is insufficient. Decide with a live mutation battery that injects `INSERT`, `UPDATE`, `DELETE`, DDL, `_event`, and a mid-method `commit`: every write must be denied, the full pre/post dump must match, `transaction(write=False)` must be called once, and every read/helper must observe `connection.in_transaction is True`. `PRAGMA query_only` or a separate URI `mode=ro` connection are possible new mechanisms, but neither exists in this repo today; spike them only if authorizer coverage or connection behavior fails the battery.

2. **Choose what ledger snapshot `resolve` evaluates.** M2 offers `verify_function` at `src/cement_runtime/system.py:2929`, which builds a `FunctionDocument` and returns it only when all six checks pass, including the persisted function receipt. `evaluate` at `src/cement_runtime/function.py:381` then returns `FunctionMatch`. Alternatives: **A**, `resolve` calls the full six-check verifier and evaluates only a passing document; **B**, project current promoted rows through a smaller private helper and evaluate without requiring P6; **C**, reconstruct/evaluate the latest persisted receipt, which intentionally answers historical sealed content rather than current live state. A best matches “built and verified function” and reuses M2 once, but it changes current per-artifact promotion behavior and has whole-set cost. B most closely preserves current `handle` hits but risks a second, weaker function-validity contract. C is deterministic but not “current resolve.” Decide with three probes: a per-artifact-promoted scope before a set checkpoint, a checkpoint drift/revocation case, and a 50,000-entry time/RSS benchmark. The contract must name whether no current passing function is a miss, a negative verdict, or `IntegrityError`.

3. **Separate a read verdict from quarantine.** Current `handle` writes artifact suspension/events on ambiguity or integrity failure before fallback (`src/cement_runtime/system.py:655-711`). A pure resolver cannot do that. Alternatives: **A**, raise `IntegrityError` on corrupt/ambiguous current state; **B**, return an inert miss with a structured reason; **C**, return a dedicated negative result and expose a separate mutating repair/quarantine action. Silent plain miss hides corruption, so B is acceptable only if diagnostics remain observable. Decide by deleting every `UPDATE artifacts` and `_event` reachable from the resolver, then run corruption/ambiguity probes and confirm that callers can distinguish “no exact case” from “ledger failed closed” without any ledger delta.

4. **Define “explicit proposal submission.”** The seed for track (a) keeps `CandidateSource` in core, while track (c) removes implicit fallback. Alternatives: **A**, `submit_proposal(partition, operation, input)` explicitly calls the configured source; **B**, `submit_proposal(..., candidate)` accepts caller-generated output/provenance and never invokes a source; **C**, ship both a pure `record_proposal` boundary and a convenience source-backed `propose` wrapper. A is the smallest change from current `handle`; B most completely leaves invocation lifecycle to the caller; C preserves the protocol boundary without conflating generation and persistence. Decide from owner intent plus an API spike: count source invocations, transactions held during the call, error surfaces, and whether a custom source can repeat without duplicated durable rows. Whatever wins, candidate generation must remain outside a database transaction as it is at `src/cement_runtime/system.py:774`.

5. **Replace lease fencing with an explicit optimistic revision rule.** Candidate generation can race `operation revise`. Current owner/request checks at `src/cement_runtime/system.py:797-824` fence stale generators and mark the request failed. Without a lease, alternatives are: **A**, capture revision before generation, re-read it in the proposal write transaction, and raise `StateError` with no proposal if it changed; **B**, persist an obsolete proposal that can only be rejected; **C**, let caller pass an expected revision and reject mismatch before source invocation. A keeps obsolete candidates out and preserves the valuable second check. B retains audit evidence but spends review attention on known-stale output. C is strongest for callers that already snapshot operations, but enlarges API burden. Decide with a blocking source plus concurrent revision: measure source calls, durable proposal/event rows, and exact retry behavior. No alternative may imply stale-worker or duplicate-attempt fencing unless it implements one.

6. **Make proposals own their scope and input.** Removing `requests` breaks the join at `src/cement_runtime/system.py:1248`, `_proposal_content` at `src/cement_runtime/system.py:1025`, the FK at `src/cement_runtime/store.py:109`, and pending gaps. Alternatives: **A**, add `operation`, `operation_revision`, `input_json`, and `input_hash` directly to `proposals`, then remove `request_id`, its uniqueness rule, and FK; **B**, add a separate immutable proposal-submission table; **C**, retain a renamed request-like table. C violates the trim. A is the KISS seam and makes review/report queries direct. B only wins if measured duplication or immutable-event requirements justify another relation. Decide by implementing both SQL projections as scratch queries over 10,001 proposals and comparing schema bytes, join count, query plan, peak RSS, and the category-(ii) rewrite size in S5-R13..R16. Preserve proposal-ID uniqueness and pending/accepted/corrected/rejected review state regardless.

7. **Choose method-specific result shapes and names.** The mixed `Outcome` union cannot survive. Resolver alternatives: existing `FunctionMatch`; a request-free `Resolved`; or a richer ledger verdict carrying function hash/check detail. Submission alternatives: proposal ID; request-free `ReviewRequired`; or full `ProposalView`. Review alternatives: proposal view plus optional example ID; a new `ReviewResult`; or the current `Resolved`/`Rejected` split without request fields. CLI naming alternatives include root `resolve` plus `proposal submit`, or `resolve` plus `propose`. Decide with an API/CLI shape table and the direct consumer count: README, CLI, hospital demo, 239 system tests, 104 CLI tests, and 18 example tests. Prefer existing `FunctionMatch` unless a caller requirement proves that ledger resolution needs more provenance than `matched/output/artifact_hash`.

8. **The caller inherits concrete lifecycle obligations.** The replacement docs/API must list all of these, without implying that proposal IDs satisfy them:
   1. allocate and durably bind any caller request key to partition, operation/revision, and canonical input;
   2. suppress or tolerate concurrent duplicate source calls and proposal submissions;
   3. own retry, backoff, timeout, cancellation, and crash recovery;
   4. fence or safely ignore stale workers after caller retry or operation revision;
   5. expose any polling/status UI and preserve its own attempt history;
   6. provide provider-side idempotency/tracing tokens when needed;
   7. cache resolved plans only under a caller-defined invalidation policy and re-resolve against current state;
   8. decide whether rejection permits another submission and whether duplicate proposals are acceptable;
   9. re-run live authentication, authorization, and policy before effects;
   10. execute effects idempotently and reconcile uncertain effect commits.

   Alternatives are either to state all ten as deployment obligations or to add selected services back as optional caller libraries. The milestone seed chooses the first. Decide completeness by adversarially mapping every deleted field/status/test in S1/S3/S5 to one owner; no deleted responsibility may be ownerless.

9. **Schema bump is a fail-closed replacement, not a migration.** Current mechanics: `SCHEMA_VERSION = 2` at `src/cement_runtime/store.py:19`; `SCHEMA_FINGERPRINT` hashes the entire SQL string at `src/cement_runtime/store.py:385`; open reads metadata key `schema-v2` and compares the digest at lines 434-439; it independently compares all live schema objects at line 440; `_initialize` accepts only user version 0 or the exact runtime version at lines 519-522; a new database writes metadata and `PRAGMA user_version` at lines 537-539. CLI maps any resulting `IntegrityError` to JSON `integrity` and **exit 5** at `src/cement_runtime/cli.py:711-713`. The final cut therefore requires: delete `requests` and its index; rewrite `proposals`; set version **3**; accept the new automatically derived fingerprint; update schema/version/shape tests and architecture docs; and ship no upgrader. An existing v2 ledger must fail before mutation with `database schema 2 is unsupported; expected 3`; a forged v3/old schema must fail fingerprint/live-schema validation. Alternatives are one final v3 cut or multiple intermediate schema versions. Prefer one cut. Decide with byte-exact pre/post files for a rejected v2 open, fresh-v3 construction, user-version/fingerprint assertions, and CLI exit/channel probes.

10. **The hospital example and its transcript must change.** `run_demo.py` has 8 `request_id` hits: one event-detail key at `examples/hospital_ocr/run_demo.py:133` plus seven `handle` calls at lines 182, 198, 232, 252, 267, 296, and 316. Known-layout reads at lines 232 and 296 become pure `resolve`; the five evidence-producing misses become explicit submissions. The two `request.resolved_by_artifact` events printed in the README at `examples/hospital_ocr/README.md:208` and line 216 disappear. `plan_adapter.py` has two self-check fields at lines 159 and 173; remove them from `CandidateRequest`. Alternatives: **A**, regenerate the honest transcript and narration; **B**, synthesize old request events/output to keep bytes stable. B is false teaching and must be rejected. Decide by rerunning `uv run python examples/hospital_ocr/run_demo.py`, then the pinned transcript test. Per `.agent/memory.md`, the mask contract is strict: exactly one `art_<32hex>` and one 64-hex function hash. Preserve both occurrence-count assertions, rerun the `-O` refusal test, and retain the post-ledger-teardown offline resolve pin.

11. **Audit/event/report consumers need an explicit vocabulary cut.** Delete `request.resolved_by_artifact` and `request.fallback_failed`; remove `request_id` from `proposal.created`; decide whether a source failure emits no event or a proposal-submission failure event with no durable proposal. `PendingProposalGap` and `function_report` currently expose request ID and join request state. Alternatives for gap identity are proposal ID + operation revision + input hash (smallest), or a new caller-supplied opaque correlation value that Cement records without granting idempotency semantics. Decide with the event-feed and 10,001-tail tests: exact event order, monotonic sequence, projection keys, partition/operation equality-vs-`LIKE` probes, and bounded materialization must remain explicit. Do not call an opaque correlation value `request_id` unless its non-idempotent semantics are impossible to misread.

12. **Coordinate M3 tracks (a) and (b) at overlapping signatures.** Track (c) changes `CandidateRequest` and source error flow in `models.py`/`source.py`; track (a) relocates `CommandCandidateSource` and adapter docs. Track (c) adds resolver/submission methods in `System`; track (b) removes `_authorize` calls from review/challenge and potentially the new submission action. Alternatives are sequential ownership or one merged mega-unit. Use sequential ownership: land the track-(c) API contract first, then let (a)/(b) conform. Decide order by a symbol-level overlap diff; no parallel units should own `system.py`, `models.py`, `__init__.py`, or `cli.py` simultaneously.

13. **Natural unit-split seams, with file ownership.** Recommended spine:
   1. **c1 — pure resolver + proof:** `src/cement_runtime/system.py`, reuse-only `src/cement_runtime/function.py`, `src/cement_runtime/models.py`/`__init__.py` only if a new result is chosen, and focused `tests/test_system.py`. Add beside `handle`; require authorizer + full-dump + one-snapshot gates.
   2. **c2 — one schema/API cut:** `src/cement_runtime/store.py`, `system.py`, `models.py`, `__init__.py`, `source.py`, and `tests/test_system.py`. Add direct proposal submission, rewrite review/report, delete request/lease machinery and result types, bump schema once. This is necessarily sequential after c1 because both own giant `system.py`/`test_system.py`.
   3. **c3 — CLI cut:** `src/cement_runtime/cli.py`, `tests/test_cli.py`, and root command examples in `README.md`. Replace `handle`/`request`, result payloads, help census, and exit mappings.
   4. **c4 — example + claims:** `examples/hospital_ocr/run_demo.py`, `plan_adapter.py`, its README, `tests/test_hospital_ocr_example.py`, root `README.md`, `docs/architecture.md`, `docs/threat-model.md`, and the relocated/deleted adapter protocol as track (a) dictates. Regenerate the transcript last.

   Alternative: split c2 into “proposal ownership” then “request deletion.” That gives a smaller code review but requires either two schema versions or a transient schema whose same version/fingerprint rejects the previous checkpoint. Because this project ships no migration and `system.py`/`test_system.py` reread cost dominates, prefer the coarse one-cut c2. Decide after a line-level contract: if c2 exceeds roughly 1,200 changed production lines or the full test gate cannot stay green at one checkpoint, split sequentially with explicit schema version 3 then 4; never run the halves concurrently.

14. **Verification scope and performance are release semantics.** A full `verify_function` inside every resolve re-hashes reports/evidence and materializes the complete set before one exact lookup. A private cached or narrower resolver could be faster but risks stale or weaker validation. Alternatives: full six-check per call; per-snapshot projection without child-set rehash; or caller-held exported bundle evaluation. Decide with cold/warm benchmarks at 1, 1,000, and 50,000 entries plus corruption mutations of the first/middle/last rows. Record which safety checks execute on every call. Never claim “pure” as a synonym for “cheap,” and never add an in-process cache without a tested invalidation identity.
