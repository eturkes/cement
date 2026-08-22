# M3(a) LLM-runtime relocation map

## S1 SYMBOL INVENTORY

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S1-001 | README.md:52 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-002 | README.md:168 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-003 | README.md:173 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-004 | docs/adapter-protocol.md:1 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-005 | docs/adapter-protocol.md:3 | `CommandCandidateSource` | doc | relocate | documented symbol or candidate-runtime claim |
| S1-006 | docs/adapter-protocol.md:21 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-007 | docs/architecture.md:121 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-008 | docs/threat-model.md:49 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-009 | examples/hospital_ocr/README.md:38 | `CandidateSource` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-010 | examples/hospital_ocr/README.md:244 | `Candidate` | doc | core-keep | documented symbol or candidate-runtime claim |
| S1-011 | examples/hospital_ocr/plan_adapter.py:14 | `CandidateRequest` | example | core-keep | example adapter type/construction site |
| S1-012 | examples/hospital_ocr/plan_adapter.py:14 | `Candidate` | example | core-keep | example adapter type/construction site |
| S1-013 | examples/hospital_ocr/plan_adapter.py:25 | `CandidateRequest` | example | core-keep | example adapter type/construction site |
| S1-014 | examples/hospital_ocr/plan_adapter.py:25 | `Candidate` | example | core-keep | example adapter type/construction site |
| S1-015 | examples/hospital_ocr/plan_adapter.py:101 | `Candidate` | example | core-keep | example adapter type/construction site |
| S1-016 | examples/hospital_ocr/plan_adapter.py:155 | `CandidateRequest` | example | core-keep | example adapter type/construction site |
| S1-017 | examples/hospital_ocr/plan_adapter.py:169 | `CandidateRequest` | example | core-keep | example adapter type/construction site |
| S1-018 | examples/hospital_ocr/run_demo.py:22 | `Candidate` | example | core-keep | example adapter type/construction site |
| S1-019 | examples/hospital_ocr/run_demo.py:23 | `CandidateRequest` | example | core-keep | example adapter type/construction site |
| S1-020 | examples/hospital_ocr/run_demo.py:56 | `CandidateRequest` | example | core-keep | example adapter type/construction site |
| S1-021 | examples/hospital_ocr/run_demo.py:56 | `Candidate` | example | core-keep | example adapter type/construction site |
| S1-022 | src/cement_runtime/__init__.py:4 | `CandidateSourceError` | import | undecided-MAIN | module import edge |
| S1-023 | src/cement_runtime/__init__.py:28 | `Candidate` | import | core-keep | module import edge |
| S1-024 | src/cement_runtime/__init__.py:29 | `CandidateRequest` | import | core-keep | module import edge |
| S1-025 | src/cement_runtime/__init__.py:61 | `CandidateSource` | import | core-keep | module import edge |
| S1-026 | src/cement_runtime/__init__.py:61 | `CommandCandidateSource` | import | undecided-MAIN | module import edge |
| S1-027 | src/cement_runtime/__init__.py:65 | `Candidate` | export | core-keep | package-root public export |
| S1-028 | src/cement_runtime/__init__.py:66 | `CandidateRequest` | export | core-keep | package-root public export |
| S1-029 | src/cement_runtime/__init__.py:67 | `CandidateSource` | export | core-keep | package-root public export |
| S1-030 | src/cement_runtime/__init__.py:68 | `CandidateSourceError` | export | undecided-MAIN | package-root public export |
| S1-031 | src/cement_runtime/__init__.py:70 | `CommandCandidateSource` | export | undecided-MAIN | package-root public export |
| S1-032 | src/cement_runtime/cli.py:27 | `CommandCandidateSource` | import | rewrite | module import edge |
| S1-033 | src/cement_runtime/cli.py:268 | `CommandCandidateSource` | type | rewrite | signature/type boundary |
| S1-034 | src/cement_runtime/cli.py:275 | `CommandCandidateSource` | call | rewrite | CLI command-source construction |
| S1-035 | src/cement_runtime/errors.py:28 | `CandidateSourceError` | definition | undecided-MAIN | domain failure definition |
| S1-036 | src/cement_runtime/models.py:52 | `Candidate` | definition | core-keep | core result model definition |
| S1-037 | src/cement_runtime/models.py:60 | `CandidateRequest` | definition | core-keep | core request model definition |
| S1-038 | src/cement_runtime/source.py:18 | `CandidateSourceError` | import | relocate | module import edge |
| S1-039 | src/cement_runtime/source.py:20 | `CandidateRequest` | import | core-keep | module import edge |
| S1-040 | src/cement_runtime/source.py:20 | `Candidate` | import | core-keep | module import edge |
| S1-041 | src/cement_runtime/source.py:25 | `CandidateSource` | definition | core-keep | core structural protocol definition |
| S1-042 | src/cement_runtime/source.py:28 | `CandidateRequest` | type | core-keep | signature/type boundary |
| S1-043 | src/cement_runtime/source.py:28 | `Candidate` | type | core-keep | signature/type boundary |
| S1-044 | src/cement_runtime/source.py:31 | `CommandCandidateSource` | definition | relocate | command-backed implementation definition |
| S1-045 | src/cement_runtime/source.py:120 | `CandidateRequest` | type | core-keep | signature/type boundary |
| S1-046 | src/cement_runtime/source.py:120 | `Candidate` | type | core-keep | signature/type boundary |
| S1-047 | src/cement_runtime/source.py:168 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-048 | src/cement_runtime/source.py:257 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-049 | src/cement_runtime/source.py:259 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-050 | src/cement_runtime/source.py:261 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-051 | src/cement_runtime/source.py:263 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-052 | src/cement_runtime/source.py:265 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-053 | src/cement_runtime/source.py:267 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-054 | src/cement_runtime/source.py:269 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-055 | src/cement_runtime/source.py:271 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-056 | src/cement_runtime/source.py:274 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-057 | src/cement_runtime/source.py:279 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-058 | src/cement_runtime/source.py:281 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-059 | src/cement_runtime/source.py:286 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-060 | src/cement_runtime/source.py:290 | `CandidateSourceError` | call | relocate | command-runtime failure normalization |
| S1-061 | src/cement_runtime/source.py:298 | `Candidate` | call | core-keep | candidate result construction |
| S1-062 | src/cement_runtime/system.py:26 | `CandidateSourceError` | import | undecided-MAIN | module import edge |
| S1-063 | src/cement_runtime/system.py:54 | `CandidateRequest` | import | core-keep | module import edge |
| S1-064 | src/cement_runtime/system.py:87 | `CandidateSource` | import | core-keep | module import edge |
| S1-065 | src/cement_runtime/system.py:417 | `CandidateSource` | type | core-keep | signature/type boundary |
| S1-066 | src/cement_runtime/system.py:775 | `CandidateRequest` | call | core-keep | request construction |
| S1-067 | src/cement_runtime/system.py:787 | `CandidateSourceError` | call | undecided-MAIN | system converts source failure to retryable state |
| S1-068 | tests/test_cli.py:2252 | `Candidate` | test | core-keep | test import reference |
| S1-069 | tests/test_cli.py:2255 | `Candidate` | test | core-keep | test signature reference |
| S1-070 | tests/test_cli.py:2256 | `Candidate` | test | core-keep | test construction/result reference |
| S1-071 | tests/test_hospital_ocr_example.py:17 | `CandidateRequest` | test | core-keep | test import reference |
| S1-072 | tests/test_hospital_ocr_example.py:357 | `CandidateRequest` | test | core-keep | test signature reference |
| S1-073 | tests/test_hospital_ocr_example.py:358 | `CandidateRequest` | test | core-keep | test construction/result reference |
| S1-074 | tests/test_source.py:10 | `CandidateSourceError` | test | relocate | test import reference |
| S1-075 | tests/test_source.py:11 | `CandidateRequest` | test | core-keep | test import reference |
| S1-076 | tests/test_source.py:12 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-077 | tests/test_source.py:15 | `CommandCandidateSource` | test | relocate | compound test-class name; raw-grep-only naming reference |
| S1-078 | tests/test_source.py:16 | `CandidateRequest` | test | core-keep | test signature reference |
| S1-079 | tests/test_source.py:17 | `CandidateRequest` | test | core-keep | test construction/result reference |
| S1-080 | tests/test_source.py:30 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-081 | tests/test_source.py:40 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-082 | tests/test_source.py:43 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-083 | tests/test_source.py:49 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-084 | tests/test_source.py:53 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-085 | tests/test_source.py:55 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-086 | tests/test_source.py:58 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-087 | tests/test_source.py:62 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-088 | tests/test_source.py:66 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-089 | tests/test_source.py:68 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-090 | tests/test_source.py:72 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-091 | tests/test_source.py:80 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-092 | tests/test_source.py:83 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-093 | tests/test_source.py:88 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-094 | tests/test_source.py:89 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-095 | tests/test_source.py:90 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-096 | tests/test_source.py:91 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-097 | tests/test_source.py:92 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-098 | tests/test_source.py:93 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-099 | tests/test_source.py:94 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-100 | tests/test_source.py:95 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-101 | tests/test_source.py:96 | `CommandCandidateSource` | test | relocate | test import reference |
| S1-102 | tests/test_source.py:103 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-103 | tests/test_source.py:104 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-104 | tests/test_source.py:119 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-105 | tests/test_source.py:137 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-106 | tests/test_source.py:140 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-107 | tests/test_source.py:161 | `CommandCandidateSource` | test | relocate | test construction/result reference |
| S1-108 | tests/test_source.py:165 | `CandidateSourceError` | test | relocate | failure assertion reference |
| S1-109 | tests/test_system.py:25 | `Candidate` | test | core-keep | test import reference |
| S1-110 | tests/test_system.py:114 | `Candidate` | test | core-keep | test construction/result reference |
| S1-111 | tests/test_system.py:125 | `Candidate` | test | core-keep | test construction/result reference |
| S1-112 | tests/test_system.py:14822 | `Candidate` | test | core-keep | test construction/result reference |

**Measured completeness.** Same scoped path list for every command. Raw `git grep -c <symbol> -- <paths>` totals versus inventory rows: `CandidateSource` = 64 raw / 6 rows (58 raw-only nested-name lines: `CommandCandidateSource` or `CandidateSourceError`); `CommandCandidateSource` = 29 / 29; `CandidateSourceError` = 30 / 30; `CandidateRequest` = 20 / 20; `Candidate` = 105 raw / 27 rows (78 raw-only compound-name lines). The gaps are substring collisions, not omitted exact-token references. `_command_supervisor.py` and `example_adapter.py` contain zero references to all five names.

## S2 BOUNDARY

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S2-001 | src/cement_runtime/source.py:16 | `Protocol` | import | core-keep | typing base for the structural protocol |
| S2-002 | src/cement_runtime/source.py:18 | `CandidateSourceError, ValidationError` | import | relocate | command implementation consumes both core error types; the retained protocol does not |
| S2-003 | src/cement_runtime/source.py:19 | `JSONValue, canonicalize, parse_json` | import | relocate | command implementation consumes core JSON types and validators |
| S2-004 | src/cement_runtime/source.py:20 | `Candidate, CandidateRequest` | import | core-keep | retained protocol names both core models; relocated implementation also needs them |
| S2-005 | src/cement_runtime/source.py:22 | `SOURCE_PROTOCOL = "cement-candidate-v1"` | definition | undecided-MAIN | wire-version constant is used only by the relocating command implementation, but seed (a) does not name it |
| S2-006 | src/cement_runtime/source.py:25 | `class CandidateSource(Protocol):` | definition | core-keep | sole protocol definition |
| S2-007 | src/cement_runtime/source.py:28 | `def propose(self, request: CandidateRequest) -> Candidate: ...` | type | core-keep | sole protocol method and full declared signature |
| S2-008 | src/cement_runtime/models.py:52 | `class Candidate:` | definition | core-keep | protocol return model: `output: object`, `provenance: Mapping[str, object]` |
| S2-009 | src/cement_runtime/models.py:60 | `class CandidateRequest:` | definition | core-keep | protocol request model: partition, operation, revision, request ID, bounded JSON input |
| S2-010 | src/cement_runtime/errors.py:28 | `class CandidateSourceError(CementError):` | definition | undecided-MAIN | operational source-failure type; not named by the protocol signature |
| S2-011 | src/cement_runtime/system.py:417 | `candidate_source: CandidateSource` | type | core-keep | core dependency-injection boundary |
| S2-012 | src/cement_runtime/system.py:429 | `getattr(candidate_source, "propose", None)` | call | core-keep | runtime admission checks only that `propose` is callable |
| S2-013 | src/cement_runtime/system.py:774 | `candidate = self.candidate_source.propose(` | call | core-keep | only core invocation edge; it targets the protocol instance, not the command implementation |
| S2-014 | src/cement_runtime/system.py:775 | `CandidateRequest(` | call | core-keep | core constructs the complete protocol request |
| S2-015 | src/cement_runtime/system.py:787 | `except CandidateSourceError:` | call | undecided-MAIN | explicit domain-error normalization to inert failure |
| S2-016 | src/cement_runtime/system.py:789 | `except Exception:` | call | core-keep | every ordinary custom-adapter exception is also normalized; `BaseException` is not |
| S2-017 | src/cement_runtime/source.py:31 | `class CommandCandidateSource:` | definition | relocate | structural protocol implementer; it does not inherit from `CandidateSource` |
| S2-018 | src/cement_runtime/source.py:120 | `def propose(self, request: CandidateRequest) -> Candidate:` | type | relocate | command implementation matches the retained signature |
| S2-019 | src/cement_runtime/source.py:168 | `raise CandidateSourceError("candidate command could not be started")` | call | relocate | representative command/protocol failure normalization; all command failure raises move with the implementation |
| S2-020 | src/cement_runtime/__init__.py:4 | `CandidateSourceError,` | import | undecided-MAIN | package-root error import changes only if MAIN moves or de-publicizes the error |
| S2-021 | src/cement_runtime/__init__.py:61 | `from .source import CandidateSource, CommandCandidateSource` | import | rewrite | retain only the protocol import; core cannot import the relocated implementation |
| S2-022 | src/cement_runtime/__init__.py:67 | `"CandidateSource",` | export | core-keep | retained package-root protocol export |
| S2-023 | src/cement_runtime/__init__.py:68 | `"CandidateSourceError",` | export | undecided-MAIN | conditional export fork tracks the error-type decision |
| S2-024 | src/cement_runtime/__init__.py:70 | `"CommandCandidateSource",` | export | undecided-MAIN | must disappear or become an explicit compatibility decision outside the no-core-import boundary |

### Exact retained contract

`CandidateSource` is a structural `typing.Protocol` with exactly one member: `propose(self, request: CandidateRequest) -> Candidate`. It declares no exception type and no runtime-checkable marker. Its domain types are `CandidateRequest` and `Candidate`; both remain core. `Protocol` is only the typing base. `CandidateSourceError` is operational, not part of the declared signature. `System` accepts any object with a callable `propose`; it maps both `CandidateSourceError` and every other ordinary `Exception` from invocation or result canonicalization to `fallback_failed/candidate_source_error`. Thus the effective core failure boundary is broader than the named error. The relocated `CommandCandidateSource` constructor uses `ValidationError` for bad configuration, while its `propose` path uses `CandidateSourceError` for supervised command, cleanup, wire, and provenance failures.

### Post-move import direction

Core must import **nothing** from the optional example surface. Current core imports of the concrete runner are `src/cement_runtime/__init__.py:61` and `src/cement_runtime/cli.py:27`; both must be removed or rewritten. `System` already depends only on `CandidateSource`, `CandidateRequest`, `Candidate`, and the failure-normalization policy.

The relocated command implementation imports these core dependencies: `CandidateSourceError` and `ValidationError`; `JSONValue`, `canonicalize`, and `parse_json`; and `Candidate` plus `CandidateRequest`. It currently does not import or subclass `CandidateSource`; structural compatibility is sufficient. `_command_supervisor.py` and `example_adapter.py` import only the standard library. Whether `SOURCE_PROTOCOL` moves with the example or remains a core wire constant is an uncovered fork.

### Package-root exports

The mandatory `__init__.py` edits are the mixed import at line 61 and the `CommandCandidateSource` `__all__` entry at line 70. Removing the package-root `CommandCandidateSource` name breaks no current in-repo caller: CLI imports `.source`, and `tests/test_source.py` imports `cement_runtime.source`. It remains an external public-API break. `CandidateSource` stays imported/exported. `Candidate` and `CandidateRequest` stay exported and are used by the hospital example. `CandidateSourceError` import/export changes only if MAIN chooses to move or de-publicize that error; removing only its package-root export breaks no current in-repo caller, but removing the class also requires changes in `System`, the command implementation, and tests.

## S3 NORMATIVE CLAIMS

| id | anchor | quote | falsified_by | note |
|---|---|---|---|---|
| S3-001 | README.md:89 | `Ask the registered operation to handle JSON.` | core CLI loses its concrete command-source path | The quick-start miss path needs an optional-example invocation or a library-injection example. |
| S3-002 | README.md:89 | `The bundled adapter is a deterministic protocol stub,` | `example_adapter.py` relocates | “bundled” becomes false for the core install/surface. |
| S3-003 | README.md:90 | `Replace its command with your provider wrapper.` | `CommandCandidateSource` relocates | Instruction depends on the departing core CLI runner. |
| S3-004 | README.md:96 | `--source-command '["python3","-m","cement_runtime.example_adapter"]'` | `CommandCandidateSource` and `example_adapter.py` relocate | Exact quick-start command and module path become stale. |
| S3-005 | README.md:244 | `for the command adapter protocol.` | `docs/adapter-protocol.md` relocates | Link target and ownership statement must follow the example surface. |
| S3-006 | README.md:285 | `Linux is the strongest command-adapter deployment target:` | subreaper/process-group supervisor relocates | Core deployment guidance becomes misplaced; qualify it as example-runner guidance. |
| S3-007 | README.md:286 | `This is lifecycle containment for a trusted provider wrapper, not` | subreaper/process-group supervisor relocates | Security qualification must move with the implementation. |
| S3-008 | README.md:287 | `If cleanup must survive simultaneous runtime/supervisor` | subreaper/process-group supervisor relocates | Crash-containment obligation must move with the implementation. |
| S3-009 | docs/architecture.md:169 | `The command adapter uses `subprocess` and `signal`.` | `CommandCandidateSource` and supervisor relocate | False as a statement about the core runtime/tooling after the split. |
| S3-010 | docs/threat-model.md:49 | `Candidate commands bypass the shell, have timeout/output limits, and run outside database locks.` | `CommandCandidateSource` relocates | No longer a core enforced control; move or scope to the optional example. |
| S3-011 | docs/threat-model.md:50 | `Linux, a child-subreaper kills and reaps detached descendants before accepting output.` | subreaper supervisor relocates | No longer a core enforced control. |
| S3-012 | docs/threat-model.md:51 | `mechanism is lifecycle containment for the trusted adapter, not a hostile-code sandbox.` | subreaper supervisor relocates | Qualification must accompany the optional runner. |
| S3-013 | docs/threat-model.md:52 | `watchdog covers unexpected supervisor exit for the shared process group.` | outer process-group watchdog relocates | Sentence about the watchdog must accompany the optional runner. |
| S3-014 | docs/threat-model.md:53 | `necessary to contain detached descendants across simultaneous supervisor/watchdog failure or OOM.` | subreaper/process-group supervisor relocates | Residual-risk claim must accompany the optional runner. |
| S3-015 | docs/threat-model.md:80 | `Deploy command adapters on Linux.` | command runner and supervisor relocate | Core deployment obligation becomes optional-example guidance. |
| S3-016 | docs/threat-model.md:80 | `If crash-resilient process-tree containment is required, add an` | command runner and supervisor relocate | Host-boundary obligation must move with the optional runner. |
| S3-017 | docs/adapter-protocol.md:1 | `# Candidate adapter protocol` | `docs/adapter-protocol.md` relocates | Document identity and path move as a unit. |
| S3-018 | docs/adapter-protocol.md:3 | `invokes a trusted executable directly with` | `CommandCandidateSource` relocates | Concrete runner claim belongs to its new optional surface. |
| S3-019 | docs/adapter-protocol.md:4 | `compact JSON object to stdin:` | `docs/adapter-protocol.md` relocates | Request framing contract moves with the runner. |
| S3-020 | docs/adapter-protocol.md:8 | `"input": {"domain": "value"},` | `docs/adapter-protocol.md` relocates | Normative request example moves with the protocol document. |
| S3-021 | docs/adapter-protocol.md:17 | `The command writes exactly one JSON object to stdout:` | `docs/adapter-protocol.md` relocates | Response framing contract moves with the runner. |
| S3-022 | docs/adapter-protocol.md:21 | `"output": {"kind": "reply", "text": "Candidate answer"},` | `docs/adapter-protocol.md` relocates | Normative response example moves with the protocol document. |
| S3-023 | docs/adapter-protocol.md:31 | `The response must contain both fields.` | `docs/adapter-protocol.md` relocates | Response schema claim moves. |
| S3-024 | docs/adapter-protocol.md:31 | `Additional top-level fields fail closed.` | `docs/adapter-protocol.md` relocates | Response schema claim moves. |
| S3-025 | docs/adapter-protocol.md:31 | `Cement bounds the` | `CommandCandidateSource` relocates | Bound is implemented by the optional runner, not retained protocol core. |
| S3-026 | docs/adapter-protocol.md:32 | `It rejects duplicate object keys, decimal/exponent and non-finite numbers, signed-64-bit` | `CommandCandidateSource` relocates | Runner parse/canonicalization claim moves. |
| S3-027 | docs/adapter-protocol.md:34 | `Encode domain decimals as strings.` | `docs/adapter-protocol.md` relocates | Wire-format obligation moves. |
| S3-028 | docs/adapter-protocol.md:34 | `Cement excludes` | `CommandCandidateSource` relocates | Stderr secrecy claim is runner behavior. |
| S3-029 | docs/adapter-protocol.md:35 | `Exit failure, timeout, malformed JSON,` | `CommandCandidateSource` relocates | Failure-normalization claim is runner behavior. |
| S3-030 | docs/adapter-protocol.md:38 | `On Linux with `/proc`, Cement launches the adapter beneath a private child-subreaper.` | subreaper supervisor relocates | Lifecycle implementation claim moves. |
| S3-031 | docs/adapter-protocol.md:39 | `enforces the primary timeout and the stdout/stderr limits.` | subreaper supervisor relocates | Timeout/output enforcement claim moves. |
| S3-032 | docs/adapter-protocol.md:39 | `It terminates the adapter.` | subreaper supervisor relocates | Lifecycle implementation claim moves. |
| S3-033 | docs/adapter-protocol.md:40 | `terminates descendants that detach into new sessions, then reaps them.` | subreaper supervisor relocates | Detached-descendant implementation claim moves. |
| S3-034 | docs/adapter-protocol.md:41 | `runtime only after that cleanup, and it stays alive throughout.` | subreaper supervisor relocates | Cleanup-before-output guarantee moves. |
| S3-035 | docs/adapter-protocol.md:42 | `the outer watchdog also kills the shared process group.` | outer watchdog relocates | Outer-watchdog guarantee moves. |
| S3-036 | docs/adapter-protocol.md:43 | `simultaneous watchdog and supervisor failure, including OOM.` | subreaper/process-group supervisor relocates | Residual-risk claim must accompany moved guarantees. |
| S3-037 | docs/adapter-protocol.md:43 | `Use a cgroup/container job boundary for` | subreaper/process-group supervisor relocates | Deployment obligation moves. |
| S3-038 | docs/adapter-protocol.md:44 | `Cleanup failure is inert.` | `CommandCandidateSource` relocates | Failure behavior moves. |
| S3-039 | docs/adapter-protocol.md:45 | `cleanup only.` | outer process-group watchdog relocates | Platform fallback guarantee moves. |
| S3-040 | docs/adapter-protocol.md:45 | `Hosts without that facility terminate only the direct process.` | outer process-group watchdog relocates | Platform fallback guarantee moves. |
| S3-041 | docs/adapter-protocol.md:46 | `containment matters, use Linux or an external job/container boundary.` | subreaper/process-group supervisor relocates | Deployment obligation moves. |
| S3-042 | docs/adapter-protocol.md:46 | `This mechanism controls` | subreaper/process-group supervisor relocates | Security scope claim moves. |
| S3-043 | docs/adapter-protocol.md:47 | `It does not make an untrusted executable safe.` | subreaper/process-group supervisor relocates | Security disclaimer must remain adjacent to the moved runner. |
| S3-044 | docs/adapter-protocol.md:49 | `The adapter receives no stored examples and cannot verify or promote its own proposal.` | `docs/adapter-protocol.md` relocates | Adapter authority contract moves. |
| S3-045 | docs/adapter-protocol.md:50 | `request fields as untrusted prompt content.` | `docs/adapter-protocol.md` relocates | Prompt-trust obligation moves. |
| S3-046 | docs/adapter-protocol.md:50 | `Keep system instructions and provider credentials outside` | `docs/adapter-protocol.md` relocates | Credential/prompt obligation moves. |
| S3-047 | docs/adapter-protocol.md:51 | `The command inherits the current environment by default, so it can access deliberately` | `CommandCandidateSource` relocates | Environment behavior is runner-specific. |
| S3-048 | docs/adapter-protocol.md:52 | `The Python API can instead pass an exact environment mapping.` | `CommandCandidateSource` relocates | Concrete constructor capability moves. |
| S3-049 | docs/adapter-protocol.md:54 | `Cement can invoke the adapter again after a failed request or an expired generation lease.` | `docs/adapter-protocol.md` relocates | Retry/idempotency guidance moves with the adapter protocol. |
| S3-050 | docs/adapter-protocol.md:55 | `calls must create no external effects.` | `docs/adapter-protocol.md` relocates | Provider purity obligation moves. |
| S3-051 | docs/adapter-protocol.md:55 | ``request_id` is partition-local and available for provider-side` | `docs/adapter-protocol.md` relocates | Idempotency/tracing guidance moves. |
| S3-052 | docs/adapter-protocol.md:56 | `Adapters that use a global idempotency namespace must key on` | `docs/adapter-protocol.md` relocates | Global idempotency guidance moves. |
| S3-053 | examples/hospital_ocr/README.md:244 | `Candidate adapter protocol` | `docs/adapter-protocol.md` relocates | Pointer must target the relocated document. |
| S3-054 | src/cement_runtime/cli.py:74 | `Supervised LLM fallback that compiles confirmed behavior` | core CLI may not import the optional command runner | Top-level `--help` overstates core CLI fallback after concrete runner removal. |
| S3-055 | src/cement_runtime/cli.py:100 | `route or create an inert LLM proposal` | core CLI may not import the optional command runner | `handle --help` needs a core-only description or relocation to an example entry point. |
| S3-056 | src/cement_runtime/cli.py:106 | `--source-command` | `CommandCandidateSource` relocates and core imports nothing from examples | Core `handle` option must be deleted or redesigned without a reverse dependency. |
| S3-057 | src/cement_runtime/cli.py:107 | `Cement runs it without a shell` | `CommandCandidateSource` relocates | Concrete runner guarantee cannot remain core help text. |
| S3-058 | src/cement_runtime/cli.py:109 | `--source-id` | `CommandCandidateSource` relocates | Runner-only option becomes stale. |
| S3-059 | src/cement_runtime/cli.py:110 | `--source-timeout` | `CommandCandidateSource` relocates | Runner-only option becomes stale. |

**Help coverage.** `cement --help`, all 13 top-level subcommand helps, and all 21 nested leaf helps ran with exit 0. Only the top-level description and `handle` exposed relocation-sensitive text; all other help surfaces had no `LLM`, candidate, adapter, fallback, or source-option text.

## S4 TEST BURDEN

| id | anchor | symbol | role | disposition | note |
|---|---|---|---|---|---|
| S4-001 | tests/test_source.py:25 | `test_json_protocol_and_provenance_binding` | test | relocate | move-to-example-test — request/response execution, output, source ID, and reported provenance binding |
| S4-002 | tests/test_source.py:39 | `test_nonzero_stderr_is_not_reflected` | test | relocate | move-to-example-test — nonzero status is normalized while secret stderr is absent from the error |
| S4-003 | tests/test_source.py:48 | `test_timeout_and_invalid_response_are_inert_failures` | test | relocate | move-to-example-test — timeout and wrong top-level response keys fail as `CandidateSourceError` |
| S4-004 | tests/test_source.py:61 | `test_stdout_and_stderr_are_stream_bounded` | test | relocate | move-to-example-test — either output stream crossing the shared byte cap kills/fails the command |
| S4-005 | tests/test_source.py:75 | `test_oversized_provenance_is_a_candidate_source_error` | test | relocate | move-to-example-test — provenance has its independent 65,536-byte canonical bound |
| S4-006 | tests/test_source.py:86 | `test_constructor_rejects_ambiguous_or_invalid_scalars` | test | relocate | move-to-example-test — argv, source ID, timeout, byte limit, environment, NUL, and Unicode constructor validation |
| S4-007 | tests/test_source.py:102 | `test_start_failure_is_a_domain_error` | test | relocate | move-to-example-test — missing executable is a domain failure, not raw `OSError` |
| S4-008 | tests/test_source.py:111 | `test_detached_descendants_are_killed_and_reaped` | test | relocate | move-to-example-test — Linux subreaper kills/reaps a new-session descendant before accepting output |
| S4-009 | tests/test_source.py:129 | `test_outer_watchdog_kills_adapter_if_supervisor_dies` | test | relocate | move-to-example-test — outer process-group watchdog kills the adapter after supervisor death |
| S4-010 | tests/test_source.py:150 | `test_unsupervised_inherited_stream_fails_inert` | test | relocate | move-to-example-test — non-Linux inherited output keeping reader threads alive becomes cleanup failure |
| S4-011 | tests/test_cli.py:378 | `test_full_operator_lifecycle` | test | rewrite | rewrite — only direct core CLI integration pin for `--source-command` plus `examples/echo_adapter.py`/installed stub |
| S4-012 | tests/test_cli.py:217 | `def confirm(self, operation: str, value: int, tag: str) -> None:` | test | rewrite | rewrite shared fixture — invokes `--source-command`; transitive dependency for the function CLI corpus |
| S4-013 | tests/test_cli.py:247 | `def handle_once(` | test | rewrite | rewrite shared fixture — invokes `--source-command` for one reviewed or pending proposal |
| S4-014 | tests/test_cli.py:2955 | `def confirm_text(self, operation: str, value: str, tag: str) -> None:` | test | rewrite | rewrite shared fixture — invokes `--source-command` for non-ASCII export fixtures |
| S4-015 | tests/test_cli.py:2251 | `test_function_inspect_emits_the_tail_beyond_one_hundred_entries` | test | core-keep | keep-in-core — a local structural source proves custom `propose` injection remains sufficient without the command runner |
| S4-016 | tests/test_system.py:260 | `test_supervised_miss_to_exact_artifact_hit` | test | core-keep | keep-in-core — miss invokes the structural source; exact hit bypasses it; near miss invokes it again |
| S4-017 | tests/test_system.py:292 | `test_candidate_never_appears_in_consumer_outcome_and_rejection_is_not_evidence` | test | core-keep | keep-in-core — source output remains hidden behind review and rejection creates no fixture |
| S4-018 | tests/test_system.py:517 | `test_request_idempotency_and_partition_isolation` | test | core-keep | keep-in-core — same request invokes source once; partition-local duplicate stays isolated |
| S4-019 | tests/test_system.py:572 | `test_concurrent_retry_observes_generation_lease` | test | core-keep | keep-in-core — blocking custom source runs outside the write lock while duplicate sees `InProgress` |
| S4-020 | tests/test_system.py:592 | `test_expired_generation_poll_is_retryable_and_handle_reclaims` | test | core-keep | keep-in-core — expired lease is inert/reclaimable and late first generator cannot overwrite the reclaimed result |
| S4-021 | tests/test_system.py:623 | `test_missing_or_broken_source_is_a_stored_inert_failure` | test | core-keep | keep-in-core — despite its name, the body pins only a missing source and stable stored failure, not a throwing source |
| S4-022 | tests/test_system.py:638 | `test_public_scalar_validation_fails_with_domain_errors` | test | core-keep | keep-in-core — `candidate_source` must expose callable `propose` |
| S4-023 | tests/test_system.py:702 | `test_receipt_can_bind_individually_valid_large_input_and_output` | test | core-keep | keep-in-core — custom source result passes through core candidate canonicalization at a large valid size |
| S4-024 | tests/test_system.py:777 | `test_operation_revision_invalidates_every_old_request_path` | test | core-keep | keep-in-core — stale requests do not reinvoke source and new `CandidateRequest` carries the current revision |
| S4-025 | tests/test_system.py:835 | `test_revision_cancels_in_flight_old_generation` | test | core-keep | keep-in-core — revision change defeats a late structural-source result |
| S4-026 | tests/test_hospital_ocr_example.py:366 | `test_known_layout_plans_match_reference_extraction_for_each_layout` | test | core-keep | keep-in-core — example `propose(CandidateRequest) -> Candidate` outputs match reference extraction |
| S4-027 | tests/test_hospital_ocr_example.py:384 | `test_propose_is_byte_deterministic_for_output_and_provenance` | test | core-keep | keep-in-core — deterministic example source output/provenance ignores request ID variation |
| S4-028 | tests/test_hospital_ocr_example.py:401 | `test_returned_known_plan_is_deep_copy_isolated` | test | core-keep | keep-in-core — caller mutation cannot alter later source output |
| S4-029 | tests/test_hospital_ocr_example.py:419 | `test_drifted_known_layout_falls_back_to_applicable_best_effort_plan` | test | core-keep | keep-in-core — example source handles known-layout drift defensively |
| S4-030 | tests/test_hospital_ocr_example.py:464 | `test_unknown_layout_best_effort_plan_preserves_structure_order` | test | core-keep | keep-in-core — example source preserves unknown-layout order |
| S4-031 | tests/test_hospital_ocr_example.py:495 | `test_colliding_normalized_field_names_are_stably_suffixed` | test | core-keep | keep-in-core — example source resolves normalized-name collisions deterministically |
| S4-032 | tests/test_hospital_ocr_example.py:518 | `test_whitespace_only_identifiers_are_rejected` | test | core-keep | keep-in-core — example source rejects blank semantic identifiers |
| S4-033 | tests/test_hospital_ocr_example.py:542 | `test_malformed_signatures_are_rejected_defensively` | test | core-keep | keep-in-core — example source validates malformed request inputs |
| S4-034 | tests/test_hospital_ocr_example.py:608 | `def _promoted_example_ledger(database: str) -> FunctionDocument:` | test | core-keep | keep-in-core fixture — injects `PlanProposer` structurally into `System` for downstream example integration tests |

### Direct versus fixture-only reach

`tests/test_source.py` owns all ten direct concrete-runner tests. Outside it, only `test_full_operator_lifecycle` directly exercises the core CLI command runner. Three CLI fixture helpers (`confirm`, `handle_once`, and `confirm_text`) also invoke `--source-command`. A transitive AST call-graph measurement finds 103 CLI test methods reaching those helpers. Those 102 non-lifecycle callers pin function/report/export/eval behavior, not command-runner behavior; rewriting the three helpers preserves the callers without per-test edits. `promoted_operation`, `compile_drafts`, `receipt_history`, and `exported_bundle` are intermediate fan-out helpers. The local source in the 121-entry inspect test and the hospital `PlanProposer` tests are positive evidence that the core protocol remains useful without `CommandCandidateSource`.

### Coverage that the move can unpin

`.agent/memory.md` says example self-checks run only by hand, so every behavior worth protecting must remain under `tests/` and the configured discovery gate.

1. **Wire execution and provenance binding.** Moving or deleting `test_json_protocol_and_provenance_binding` loses the only concrete-runner happy-path pin. Cheapest replacement: keep the same test under `tests/`, importing the relocated class.
2. **Secret-safe and inert failures.** Moving the stderr, timeout/schema, stream-bound, provenance-bound, start-failure, and inherited-stream tests outside discovery loses all runner failure pins. Cheapest replacement: retain those six tests unchanged apart from the import.
3. **Constructor boundary.** Moving the scalar-validation test outside discovery unpins argv/environment/source-ID/limit validation. Cheapest replacement: retain its table-driven test against the relocated class.
4. **Linux descendant containment.** Moving the two Linux tests outside discovery unpins both subreaper cleanup and the outer watchdog. Cheapest replacement: retain both platform-gated tests in `tests/`; a hand-run example self-check is insufficient.
5. **CLI-to-example integration.** Rewriting `test_full_operator_lifecycle` only to seed data through the library would leave the relocated runner plus stub unwired. Cheapest replacement: one focused test in `tests/` invokes the relocated runner against the relocated stub, while the core lifecycle test uses a core-safe fixture path.
6. **The wrapper path.** `examples/echo_adapter.py` imports `cement_runtime.example_adapter`; relocation breaks every command-backed CLI fixture. Cheapest replacement: either delete the wrapper with the departing CLI route, or update it and pin one subprocess/import smoke test from `tests/`.
7. **Core/example dependency direction.** No current test proves that core imports no optional example module. Cheapest replacement: one isolated import test blocks example-module imports, imports `cement_runtime`, and asserts success/no blocked import.
8. **Public-surface disposition.** No test freezes `CandidateSource`/`CommandCandidateSource`/`CandidateSourceError` package-root exposure. Cheapest replacement: once MAIN rules the export fork, one `__all__`/attribute test pins the chosen surface.
9. **Core exception normalization.** The misleadingly named missing/broken-source test has no throwing custom source. If `CandidateSourceError` remains a core contract, its distinction is otherwise unpinned after command tests relocate. Cheapest replacement: one structural source raises `CandidateSourceError` and another raises `RuntimeError`; both must produce the same inert stored code without leaking text.

Existing gaps should not be promoted into relocation claims: the current happy-path test does not assert the exact request-envelope key set or protocol value; no runner test proves an exact environment excludes ambient variables; and direct-process-only hosts are not exercised. If the relocated document continues to promise those behaviors, the cheapest pins are one echo-the-request subprocess, one exact-environment subprocess, and one platform-branch mock respectively.

### Does the hospital-example pattern transfer?

Yes. `tests/test_hospital_ocr_example.py:21-27` computes the example directory, prepends it to `sys.path`, imports the example modules, and leaves all assertions in the normal `tests/` discovery tree. The command-runner example can use the same shape: keep the relocated implementation and its sibling supervisor together, import it from a test under `tests/`, and run the existing behavior battery there. If generic module names could collide, load by an explicit module spec instead of a global bare import. Either form preserves the only configured gate and avoids relying on a hand-invoked self-check.

## S5 ARCHAEOLOGY

| id | sha | subject | relevance |
|---|---|---|---|
| S5-001 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | `src/cement_runtime/source.py` only history entry; introduced protocol and concrete command runner together. |
| S5-002 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | `src/cement_runtime/_command_supervisor.py` only history entry; introduced all subreaper/process-group logic. |
| S5-003 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | `src/cement_runtime/example_adapter.py` only history entry; introduced installed deterministic stub. |
| S5-004 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | Introduced `docs/adapter-protocol.md` and its original 55-line command contract. |
| S5-005 | c69cc24 | docs: bring every human-facing surface onto the ASD-STE100 register | Only later commit on `docs/adapter-protocol.md`; prose-only register rewrite to 57 lines. |
| S5-006 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | `tests/test_source.py` only history entry; all ten runner/supervisor tests arrived with implementation. |
| S5-007 | 3b7769b | feat(runtime): compile supervised behavior into exact artifacts | Also introduced CLI flags, package exports, error/models, `examples/echo_adapter.py`, and every original normative claim; relocation is the first architectural split of this initial monolith. |
| S5-008 | bcbb8cb | example (M1.2): in-process plan proposer adapter (CandidateSource) | M1 first exercised the retained structural protocol with a provider-neutral in-process example; no concrete command runner dependency. |
| S5-009 | dffc065 | example (M1.3): hospital OCR lifecycle demo driver | M1 integrated `CandidateRequest`/`Candidate` through `System(candidate_source=PlanProposer())`. |
| S5-010 | 86eda68 | example (M1.4): hospital OCR walkthrough README + root pointer | M1 documented `cement_runtime.CandidateSource` compatibility and linked the command protocol. |
| S5-011 | 6f4f260 | example (M1 review): fix layout signature canonicalization + gate-cover the example | Created `tests/test_hospital_ocr_example.py`; establishes the transferable pattern of importing example code from the configured test tree. |
| S5-012 | 376373e | cli (M2.4c1): function show over the _Outcome seam later sub-units inherit | M2 CLI tests began the large transitive fanout through command-backed `confirm`/`promoted_operation` fixtures; runner itself unchanged. |
| S5-013 | 3edfb3b | cli (M2.4c2): receipt enumeration and historical show over one frozen seam | Expanded transitive CLI fixture dependence; runner itself unchanged. |
| S5-014 | f964c6d | cli (M2.4c3): batch draft verification and aggregate verify at exit 6 | Expanded transitive CLI fixture dependence; runner itself unchanged. |
| S5-015 | 9e088a4 | cli (M2.4c4): prospective-union inspection and one-hash set promotion | Expanded transitive CLI fixture dependence and later custom structural-source setup; runner itself unchanged. |
| S5-016 | 291e0e9 | cli (M2.4c5a): export the function bundle from either source | Expanded transitive CLI fixture dependence; runner itself unchanged. |
| S5-017 | ec79bf8 | cli (M2.4c5b): write the function bundle through an atomic file channel | Expanded transitive CLI fixture dependence; runner itself unchanged. |
| S5-018 | 9179dae | cli (M2.4c6): answer one bundled function offline, a miss as exit 6 | Expanded transitive CLI fixture dependence; runner itself unchanged. |
| S5-019 | ce006f2 | example (M2.5a): resolve a layout offline from the exported bundle | M2 retained `CandidateSource`/`CandidateRequest` example integration while extending the ledger-free phase. |
| S5-020 | e5ff481 | docs (M2.5b): repair four false claims and document the function layer | M2 claim pass added the now-relocation-sensitive architecture sentence that the command adapter uses `subprocess`/`signal`; retained README/threat links and claims. |
| S5-021 | 83198e1 | function (M2 review): close M2 with four fixes and one claim pass | Latest M2 changes touched CLI/tests/example docs but did not alter any of the five scoped runtime files. |
| S5-022 | bbac234 | agent: 166 KB rides every session → archive M1/M2 detail behind roadmap summaries | Closest surface-split precedent: detailed roadmap material moved to `.agent/archive/` while compact core summaries and references remained. |
| S5-023 | 151c22c | chore(agent): move dev harness from Codex to Claude | Tracked rename precedent: `AGENTS.md` moved to `CLAUDE.md` and neighboring configuration/references changed in the same commit. |
| S5-024 | cd0ddb6 | chore(agent): reconcile upstream ops refresh with the teammate context gauge | Tracked executable rename precedent: `.agent/context.sh` moved to `context-gauge.sh` with all known documentation/command references updated. |

**Precedent finding.** `git log --summary --diff-filter=R --all` finds only the two tracked renames above. No prior commit relocates installed package implementation into `examples/` or splits one module across core and optional surfaces. `bbac234` is a documentation-ownership analogue, not a packaging/code precedent.

## S6 HAZARDS + OPEN FORKS

Seed (a) fixes one directional boundary: the core retains `CandidateSource`; the concrete command runner, its process supervisor, the installed stub, and their protocol document leave core. The resulting dependency graph must be acyclic: **optional example → core types/validation is allowed; core → optional example is forbidden**. The current graph violates that target in package exports and CLI wiring.

1. **MATERIAL DESIGN FORK — packaging location of the relocated code.** Alternatives: (A) source-only `examples/command_adapter/`, available from a checkout and the sdist; (B) an installed `cement_runtime.examples.command_adapter` subpackage in the core wheel but never imported by core; (C) a second installed namespace/distribution such as `cement_runtime_command_example`; or (D) a nested standalone example project with its own `pyproject.toml` and a dependency on `cement-runtime`. Measurement: build wheel and sdist, enumerate members, install each artifact in a clean environment, run the stub/runner smoke test, and trace imports while importing `cement_runtime`. The phrase “optional example surface” plus M3's trim objective favors A or D, but MAIN must define whether “optional” means optional to install or only optional to import.

2. **MATERIAL DESIGN FORK — `CommandCandidateSource` public exposure.** Alternatives: (A) remove `cement_runtime.CommandCandidateSource` and `cement_runtime.source.CommandCandidateSource`, exposing the class only from the example; (B) retain a deprecation/compatibility shim in core; or (C) expose a new optional-package namespace while dropping the old names immediately. An eager or lazy core re-export that imports the example violates the required dependency direction. Measurement: repository callers are zero for the package-root name and all current direct callers are internal CLI/tests; external compatibility is therefore the only reason for B. MAIN must apply the pre-1.0 API policy and pin the selected `__all__`/attribute surface.

3. **MATERIAL DESIGN FORK — core CLI behavior and M3 sequencing.** Alternatives: (A) remove `handle --source-command`, `--source-id`, and `--source-timeout` in track (a), leaving core CLI unable to create a proposal from a miss; (B) move that operator route to an example-owned CLI/console script; or (C) land track (a) together with M3(c), which replaces `handle`/request lifecycle and avoids a short-lived crippled bridge. A plugin loader in core is a fourth design, but it recreates an invocation runtime and reverse dependency rather than trimming it. Measurement: map which command remains consumable after each unit, count temporary code/test churn before M3(c), and run the complete CLI leaf census. `src/cement_runtime/cli.py:27`, `:106-110`, `:268-275`, and `:462-467` all require a ruling.

4. **MATERIAL DESIGN FORK — subreaper/process-group semantics after relocation.** Alternatives: (A) move `_command_supervisor.py` byte-for-byte beside the class and preserve Linux subreaping, the outer watchdog, stream bounds, and cleanup failure codes; (B) simplify the example to process-group/direct-process cleanup; or (C) require an external cgroup/container and delete internal descendant discovery. Seed (a) says the supervisor “relocates,” not that its guarantees weaken, so A is the only seed-conforming default absent an owner override. Measurement: retain all ten `test_source` behaviors, run the two Linux `/proc` tests, run a detached-new-session probe, and compare every surviving threat/document claim. Any weakening requires an explicit threat-model change.

5. **MATERIAL DESIGN FORK — `CandidateSourceError` ownership.** Alternatives: (A) keep it core and public as the conventional source-domain failure imported by the example; (B) keep it core but remove the package-root export; or (C) move/delete it with the concrete runner and let core normalize all `Exception` uniformly. `System` already maps `CandidateSourceError` and arbitrary `Exception` to the same stored code, so the class has no distinct runtime outcome. Measurement: add throwing structural-source probes, inspect intended external adapter ergonomics, and co-design with M3(c), where `System` may stop invoking sources. If A/B wins, rewrite its “supervised fallback” docstring to describe the retained protocol rather than the departing command runtime.

6. **MATERIAL DESIGN FORK — wire constant and example-to-core dependencies.** `SOURCE_PROTOCOL` is used only by the relocating class, but seed (a) does not name it. Alternatives: (A) move the constant with the example and import core internals (`Candidate`, `CandidateRequest`, errors, `JSONValue`, `canonicalize`, `parse_json`); (B) retain a public core wire-ABI constant/API while implementation moves; or (C) make the example standalone by duplicating the bounded JSON implementation. Measurement: decide whether `cement-candidate-v1` is a core contract or merely an example protocol, then compare duplicate-code/semantic-drift cost against expanding the public API. Core must import nothing back. The current relative imports at `source.py:18-20` fail if copied verbatim outside the package.

7. **MATERIAL DESIGN FORK — `pyproject.toml` and distribution metadata.** Alternatives follow fork 1: source-only relocation can use existing `source-include = ["docs/**", "examples/**", "tests/**"]`; an installed second package, extra, or console script requires metadata changes; a nested distribution needs its own metadata and lock policy. `module-name = "cement_runtime"` currently describes one installed package, and `cement = "cement_runtime.cli:main"` points at the core CLI. Measurement: `uv build`, archive-member assertions, clean wheel-only and sdist installs, `importlib.metadata` checks, console-script smoke tests, and a `git diff --stat` guard against accidental lock churn. MAIN must also rule whether the optional example is typed and covered by the existing `py.typed` marker.

8. **MATERIAL DESIGN FORK — stub/wrapper topology.** `src/cement_runtime/example_adapter.py` is the installed stub, while `examples/echo_adapter.py:4` is only a wrapper importing it. Alternatives: (A) move the stub and update the wrapper; (B) collapse both into one executable example; or (C) delete the wrapper and point all examples/tests at the relocated module. Measurement: run one real subprocess through the relocated `CommandCandidateSource`, assert exact output/provenance, and verify the documented command from both a checkout and the chosen built artifact. Leaving the wrapper unchanged produces an immediate import failure.

9. **MATERIAL DESIGN FORK — test ownership.** Alternatives: (A) keep the concrete battery in `tests/` and import the example by path; (B) put self-checks beside the example only; or (C) duplicate tests. `.agent/memory.md` rules out B as sufficient. Measurement: the sole configured discovery gate must collect and pass the ten concrete-runner tests plus one end-to-end stub test. The hospital-example import pattern transfers, so A has an existing low-cost precedent.

10. **MATERIAL DESIGN FORK — documentation destination and claim ownership.** Alternatives: (A) move the protocol to `examples/command_adapter/README.md`; (B) retain an example-focused page under `docs/examples/`; or (C) package docs with a standalone optional distribution. Every security guarantee must live beside the code that enforces it; core architecture/threat docs may link to, but must not list optional behavior as a core enforced control. Measurement: run Markdown diagnostics/link validation, the human-register audit, every CLI help surface, and the exact commands in README. Update both root and hospital pointers atomically with the move.

11. **MATERIAL DESIGN FORK — protocol shape versus M3(c).** The retained signature names `CandidateRequest`, whose `request_id` and operation-revision fields belong to the request lifecycle that M3(c) later removes. Alternatives: (A) preserve the current protocol unchanged through (a), then redesign it in (c); (B) co-design the final submission/proposal contract now; or (C) retain the current request envelope as provider-facing metadata even after core request state disappears. Measurement: write the post-M3 call sequence first, identify the protocol's actual consumer after `System.handle` goes away, and count throwaway API/tests under A. MAIN must avoid claiming a stable retained protocol while scheduling an immediate incompatible signature rewrite.

12. **MATERIAL DESIGN FORK — compatibility horizon.** Alternatives: immediate pre-1.0 break, one-release deprecation shim, or a separately versioned example package that begins without compatibility promises. Measurement: current repository callers, release policy, any published package/API commitments, and whether a shim can obey the no-core-import rule. This decision controls error messages, release notes, and whether old quick-start commands fail as unknown arguments or point users to the example.

### Mechanical hazards that the unit plan must bind

- `source.py:146` locates `_command_supervisor.py` as a sibling of `__file__`. The destination must preserve that relationship or replace the launch mechanism and test installed-artifact execution.
- The command implementation imports private core modules. Moving it outside `cement_runtime` requires absolute imports and knowingly couples the example to internal APIs unless those APIs become public.
- A package-root compatibility import can create a cycle: importing any `cement_runtime` submodule executes `__init__.py`, which imports `System`; an optional example importing core while core re-exports the example reverses the edge.
- The default environment intentionally passes ambient credentials; an explicit mapping excludes them. Preserve or consciously delete that security behavior and its documentation.
- Stdout and stderr share one byte limit, stderr is discarded, and cleanup precedes accepted stdout. A “simpler example” can silently lose secrecy or containment while still passing the happy path.
- Linux tests skip elsewhere. Platform-conditional green does not prove the moved supervisor file is included in a built artifact.
- `tests/test_cli.py` has 103 transitive tests fed by three command-backed helpers. Rewrite helpers once; do not misclassify 102 unrelated function tests as runner tests or delete their coverage.
- `docs/adapter-protocol.md` is included in the sdist through `source-include`, while an installed package module lives in the wheel. The destination changes which artifact carries the contract.
- The current core has zero third-party runtime dependencies. A provider SDK or packaging helper added to the optional surface must not leak into core dependencies.
- The exact `CandidateSource` protocol is structural and is not `runtime_checkable`. Do not replace it with inheritance or registration merely because the example moves.
- External consumers are unmeasured. In-repo zero-use proves migration cost only for this repository, not public compatibility.

### Seed (a) omissions requiring MAIN rulings

Seed (a) does not state the destination path/package name; installability; wheel versus sdist presence; optional console command; public export/deprecation policy; `CandidateSourceError` ownership; `SOURCE_PROTOCOL` ownership; use of private core JSON APIs; preservation level for supervisor semantics; fate of `examples/echo_adapter.py`; removal or relocation of CLI source flags; sequencing against M3(c); final `CandidateRequest` fields; whether `Candidate`/`CandidateRequest` remain package-root exports; typing/`py.typed` treatment; metadata/lock changes; test filenames and discovery mechanism; documentation destination/link paths; or the compatibility horizon. It also does not cover the necessary rewrites in `README.md`, `docs/architecture.md`, `docs/threat-model.md`, `src/cement_runtime/__init__.py`, `src/cement_runtime/cli.py`, `src/cement_runtime/errors.py`, `examples/echo_adapter.py`, `tests/test_cli.py`, and any packaging manifest selected by fork 1.

