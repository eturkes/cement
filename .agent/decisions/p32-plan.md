# p32 + p33 split plan (MAIN draft, for consultant review)

Rows (verbatim acceptance, `.agent/deferred.md`):
- p32: Public facade unchanged; policy normalization + artifact/report/member validation each have one owner; depth stays explicit; no E/F-rated function method; suite, build, lifecycle + degraded/recovery matrices unchanged.
- p33: One helper/normalized record owns each binding family; callers explicitly select row-only, bounded projection or full reconstruction; receipt discovery, limits, degraded scenarios + suite remain unchanged.
Constraint (binding): every observable stays byte-identical — exception class + message at every raise site, every FunctionCheck key/passed/detail + vector order, every JSON payload; the suite pins ~10 of the divergent messages, and changing a pinned expected value = a grading-check change needing owner approval ⇒ OUT of scope. Transaction ownership unchanged: helpers take the caller's `connection`, never open one. Read-capability census (`tests/test_read_capability_census.py`: every `transaction(write=False)` block SELECT-only) + event-kind census unaffected (no new SQL kinds, no event moves).

## E/F inventory (radon cc, HEAD 0f9b04c) — target: every System method <= D (CC <= 30)
| method | lines | CC |
|---|---|---|
| `_verify_function_snapshot` | 2982-3397 | F 70 |
| `_function_promotion_plan` | 4739-4959 | E 37 |
| `learning_cases` | 5539-5746 | E 35 |
| `function_report` | 2602-2925 | E 34 |
| `_run_verification` | 4483-4693 | E 31 |
(`cli._run` F 70 is outside p32's `System` scope.)

## Binding family A — operation policy (stored `operations` row → revision, policy_json, policy_hash, CompilePolicy)
Six sites, six depths today (messages pinned where marked *):
1. `_project_current_build` (:1344): str() casts; parse; DIGEST only → IntegrityError("operation policy digest mismatch")*.
2. `function_report` (:2652): `_stored_int(rev, min 1)`; `_digest(hash)`; parse; canonical text; digest → IntegrityError "stored operation policy is invalid"* | "stored operation policy is not canonical"* | "operation policy digest mismatch"*.
3. `_verify_function_snapshot` (:3023): type(rev) int / hash str / json str → raise ("stored operation revision is invalid" | "... policy hash is invalid" | "... policy JSON is invalid"); parse/canonical/digest → COLLECTED check failures "operation policy is invalid: {exc}" | "operation policy JSON is not canonical" | "operation policy digest does not match policy_hash"*.
4. `test_projection` (:3561): `_stored_int(rev, min 1)`; `_policy_from_text(str(json))`, no binding check.
5. `_run_verification` (:4520): artifact row's policy_json parsed; binding = equality with the registered row (`current_ok`).
6. `_function_promotion_plan` (:4762): type checks as (3) → raise; parse; text OR digest → IntegrityError("operation policy binding mismatch").
Proposal: `_OperationPolicyRow` record + ONE detector `_operation_policy_problems(policy_json, policy_hash) -> (CompilePolicy | None, tuple[_PolicyProblem, ...])`, problems typed `invalid(exc)` | `not-canonical` | `digest-mismatch`, detection order fixed (parse → text → digest, all evaluated as each site does today). Each site keeps its own depth by an explicit call (`depth=` argument or distinct thin wrappers named for the depth: `row-only` = (4)(5), `digest` = (1), `bound` = (2)(3)(6)) and maps problems to its own vocabulary. Open question Q1: is a per-caller message map an "owner" in p33's sense, or does p33 require one vocabulary (which needs owner approval for the pinned strings)?

## Binding family B — bound report (artifact row ↔ its passing test report)
Four sites:
1. `_reconstruct_function_receipt` (:2043): passed==1 → "bound report is not passing"*; `_validate_report(verify_test_set=True)`; details dict → "bound report details are not an object"; scope_hash → "bound report scope mismatch"*; 4 fields → "bound report {field} mismatch"; wrapped "function receipt member {ordinal} report is invalid: {exc}".
2. `_function_report_member` (:2386): identity + artifact_id checks first; same as (1) with verify_test_set=False; NO details-dict check (cast); wrapped "function report member {n} report is invalid: {exc}" over a wider except tuple.
3. `_verify_function_snapshot` per-row (:3170): "missing passing bound report"*; verify_test_set=True; "report details are not an object"; "report scope binding mismatch"*; "report {field} binding mismatch"; collected as "{artifact_id}: {exc}".
4. `_function_promotion_entry` (:4695): "{id} has no passing bound report"; verify_test_set=True; dict-or-scope combined → "{id} report scope binding mismatch"; "{id} report {field} binding mismatch".
Proposal: ONE detector `_bound_report_problem(connection, report_row, artifact_row, *, verify_test_set) -> _ReportProblem | None` (kinds: not-passing | details-not-object | scope | field(name)), each site formats its vocabulary. Depth explicit via `verify_test_set` (bounded projection = False at site 2, full reconstruction = True at 1/3/4).

## Family C — FunctionEntry from (artifact document, artifact row, report row)
Three identical constructions (:2169, :3213, :4729) → `_function_entry(artifact, row, report, *, entry_seal=None)`.

## Decomposition (CC) after families
- `_verify_function_snapshot`: `_over_capacity_verification(entry_count, policy_failures)`; `_duplicate_digest_check(rows, entry_count)`; per-row `_snapshot_member(...) -> _MemberFindings` (abi/report/receipt/projection failures + projected tuple), itself split into `_artifact_abi_failure(row)`, family B, `_member_scope_failures(row, revision, policy_hash, policy_json)`; `_function_hash_check(...)` = the build + P5 block (p28 pins it).
- `function_report`: family A; `_report_function_anchor(connection, receipt_row, limit)`; `_report_compile_scopes(connection, operation_row, limit)`; `_report_artifact_statuses(...)`; `_report_stale_anomalies(...)`.
- `_function_promotion_plan`: family A; `_retained_members(...)`; `_promotion_candidates(...)`; `_promotion_manifest(...)`.
- `learning_cases`: `_learning_case_groups(...)` (pending + examples → cases); `_learning_case_list(...)`; `_learning_work(...)`.
- `_run_verification`: `_structural_probe(program, example, input_json)`; `_boundary_probes(artifact, partition, operation, revision, input_json)`.

## Verification
Full gate (suite 1302 + D28 + build); `uvx radon cc -s -n E src/cement_runtime/system.py` → only none; exact-message census: every IntegrityError/StateError/ValidationError/NotFoundError literal + every FunctionCheck detail literal in system.py before == after (AST string-literal multiset over raise/FunctionCheck args, plus f-string templates); `tests/test_authority_removal.py` promote_function source pins untouched (promote_function not edited).
Q2: anything in this decomposition that silently changes evaluation order (e.g., per-row failure-list interleaving, short-circuit on first failure) the suite would not see?
Q3: should p33 land as its own unit after p32 (p32 = decomposition only), or does p32's "each have one owner" force the family helpers into p32 (then p33 closes `closed=<p32 sha>`)?
