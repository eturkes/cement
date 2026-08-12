"""JSON-first operator CLI."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field, is_dataclass
import json
import os
import sys
from typing import Any, Never

from .errors import (
    CementError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    ValidationError,
)
from .json_value import DEFAULT_MAX_BYTES, JSONValue, parse_json
from .models import CompilePolicy
from .source import CommandCandidateSource
from .system import System


class _UsageError(Exception):
    pass


class _JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise _UsageError(message)


_MISSING = object()


@dataclass(frozen=True, slots=True)
class _Outcome:
    """One command result carrying exactly one channel: JSON payload or raw text."""

    payload: Any = _MISSING
    status: int = field(default=0, kw_only=True)
    raw: str | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        if (self.payload is _MISSING) == (self.raw is None):
            raise AssertionError("_Outcome carries exactly one output channel")
        if type(self.status) is not int:
            raise AssertionError("_Outcome status must be an exact int")


def _parser() -> argparse.ArgumentParser:
    parser = _JSONArgumentParser(
        prog="cement",
        description="Supervised LLM fallback -> verified exact deterministic artifacts",
    )
    parser.add_argument("--db", default=os.environ.get("CEMENT_DB"), help="SQLite ledger path")
    parser.add_argument(
        "--partition",
        default=os.environ.get("CEMENT_PARTITION"),
        help="explicit tenant/workflow isolation key",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    operation = commands.add_parser("operation", help="manage versioned operation policy")
    operation_commands = operation.add_subparsers(dest="operation_command", required=True)
    for name in ("register", "revise"):
        action = operation_commands.add_parser(name)
        action.add_argument("operation")
        action.add_argument("--min-confirmations", type=int, default=3)
        action.add_argument("--min-reviewers", type=int, default=2)
        action.add_argument("--min-span-seconds", type=int, default=7 * 24 * 60 * 60)
        if name == "revise":
            action.add_argument("--actor", required=True)
        else:
            action.add_argument("--actor", default="local-system")
    operation_commands.add_parser("list")

    handle = commands.add_parser("handle", help="route or create an inert LLM proposal")
    handle.add_argument("operation")
    handle.add_argument("--input", required=True, help="JSON text; '-' reads stdin")
    handle.add_argument("--request-id")
    handle.add_argument("--retry-failed", action="store_true")
    handle.add_argument(
        "--source-command",
        help='JSON argv, e.g. \'["python","adapter.py"]\'; never run through a shell',
    )
    handle.add_argument("--source-id", default="command-adapter")
    handle.add_argument("--source-timeout", type=float, default=60.0)

    proposal = commands.add_parser("proposal", help="inspect/review supervised proposals")
    proposal_commands = proposal.add_subparsers(dest="proposal_command", required=True)
    proposal_show = proposal_commands.add_parser("show")
    proposal_show.add_argument("proposal_id")
    proposal_list = proposal_commands.add_parser("list")
    proposal_list.add_argument(
        "--status", choices=("all", "pending", "accepted", "corrected", "rejected"), default="pending"
    )
    proposal_list.add_argument("--after-sequence", type=int, default=0)
    proposal_list.add_argument("--limit", type=int, default=100)
    proposal_review = proposal_commands.add_parser("review")
    proposal_review.add_argument("proposal_id")
    proposal_review.add_argument("--reviewer", required=True)
    proposal_review.add_argument("--decision", choices=("accept", "correct", "reject"), required=True)
    proposal_review.add_argument("--output", help="corrected JSON; required for correct")
    proposal_review.add_argument("--note", default="")

    request = commands.add_parser("request", help="poll a request without resupplying input")
    request.add_argument("request_id")

    compile_command = commands.add_parser("compile", help="build eligible exact lookup drafts")
    compile_command.add_argument("operation")
    compile_command.add_argument("--actor", default="local-system")

    verify = commands.add_parser("verify", help="replay full exact scope + boundaries")
    verify.add_argument("artifact_id")
    verify.add_argument("--actor", default="local-system")

    promote = commands.add_parser("promote", help="atomically activate one tested scope")
    promote.add_argument("artifact_id")
    promote.add_argument("--scope-hash", required=True)
    promote.add_argument("--actor", required=True)

    challenge = commands.add_parser("challenge", help="confirm or counterexample an active artifact")
    challenge.add_argument("operation")
    challenge.add_argument("--input", required=True)
    challenge.add_argument("--expected", required=True)
    challenge.add_argument("--reviewer", required=True)
    challenge.add_argument("--note", default="")

    example = commands.add_parser("example", help="inspect/revoke confirmed fixtures")
    example_commands = example.add_subparsers(dest="example_command", required=True)
    example_list = example_commands.add_parser("list")
    example_list.add_argument("operation")
    example_list.add_argument("--include-revoked", action="store_true")
    example_list.add_argument("--after-sequence", type=int, default=0)
    example_list.add_argument("--limit", type=int, default=1_000)
    example_revoke = example_commands.add_parser("revoke")
    example_revoke.add_argument("example_id")
    example_revoke.add_argument("--actor", required=True)
    example_revoke.add_argument("--reason", required=True)

    artifact = commands.add_parser("artifact", help="inspect/quarantine deterministic builds")
    artifact_commands = artifact.add_subparsers(dest="artifact_command", required=True)
    artifact_list = artifact_commands.add_parser("list")
    artifact_list.add_argument("operation")
    artifact_list.add_argument("--after-sequence", type=int, default=0)
    artifact_list.add_argument("--limit", type=int, default=1_000)
    artifact_show = artifact_commands.add_parser("show")
    artifact_show.add_argument("artifact_id")
    artifact_suspend = artifact_commands.add_parser("suspend")
    artifact_suspend.add_argument("artifact_id")
    artifact_suspend.add_argument("--actor", required=True)
    artifact_suspend.add_argument("--reason", required=True)

    report = commands.add_parser("report", help="inspect immutable verification reports")
    report_commands = report.add_subparsers(dest="report_command", required=True)
    report_show = report_commands.add_parser("show")
    report_show.add_argument("report_id")
    report_show.add_argument("--after-test-key", default="")
    report_show.add_argument("--test-limit", type=int, default=1_000)
    report_list = report_commands.add_parser("list")
    report_list.add_argument("--artifact-id")
    report_list.add_argument("--after-sequence", type=int, default=0)
    report_list.add_argument("--limit", type=int, default=100)

    function = commands.add_parser("function", help="inspect the operation's function set")
    function_commands = function.add_subparsers(dest="function_command", required=True)
    function_show = function_commands.add_parser("show")
    function_show.add_argument("operation")
    function_show.add_argument("--projection-limit", type=int, default=100)

    events = commands.add_parser("events", help="read append-only audit projections")
    events.add_argument("--after", type=int, default=0)
    events.add_argument("--limit", type=int, default=1_000)
    return parser


def _input(value: str) -> JSONValue:
    if value != "-":
        return parse_json(value).value
    binary = getattr(sys.stdin, "buffer", None)
    if binary is not None:
        raw = binary.read(DEFAULT_MAX_BYTES + 1)
        if len(raw) > DEFAULT_MAX_BYTES:
            raise ValidationError(f"JSON stdin exceeds {DEFAULT_MAX_BYTES} bytes")
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON stdin is not valid UTF-8") from exc
    else:
        # StringIO and embedding hosts expose text-only streams. The parser's
        # UTF-8 byte check remains authoritative after this bounded char read.
        source = sys.stdin.read(DEFAULT_MAX_BYTES + 1)
        if len(source) > DEFAULT_MAX_BYTES:
            raise ValidationError(f"JSON stdin exceeds {DEFAULT_MAX_BYTES} characters")
    return parse_json(source).value


def _source(value: str | None, *, source_id: str, timeout: float) -> CommandCandidateSource | None:
    if value is None:
        return None
    parsed = parse_json(value, max_bytes=65_536).value
    if type(parsed) is not list or not parsed or any(type(item) is not str for item in parsed):
        raise ValidationError("--source-command must be a non-empty JSON array of strings")
    argv = [str(item) for item in parsed]
    return CommandCandidateSource(argv, source_id=source_id, timeout_seconds=timeout)


def _emit(value: Any, *, stream: Any = None) -> None:
    if stream is None:
        stream = sys.stdout
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Any:
    if not args.db:
        parser.error("--db or CEMENT_DB is required")
    if not args.partition:
        parser.error("--partition or CEMENT_PARTITION is required")
    source = None
    if args.command == "handle":
        source = _source(
            args.source_command,
            source_id=args.source_id,
            timeout=args.source_timeout,
        )
    system = System(args.db, candidate_source=source)

    if args.command == "operation":
        if args.operation_command == "list":
            return system.operations(args.partition)
        policy = CompilePolicy(
            min_confirmations=args.min_confirmations,
            min_reviewers=args.min_reviewers,
            min_span_seconds=args.min_span_seconds,
        )
        if args.operation_command == "register":
            revision = system.register_operation(
                args.partition,
                args.operation,
                policy=policy,
                registered_by=args.actor,
            )
        else:
            revision = system.revise_operation(
                args.partition,
                args.operation,
                policy=policy,
                revised_by=args.actor,
            )
        return {"operation": args.operation, "revision": revision}
    if args.command == "handle":
        return system.handle(
            args.partition,
            args.operation,
            _input(args.input),
            request_id=args.request_id,
            retry_failed=args.retry_failed,
        )
    if args.command == "proposal":
        if args.proposal_command == "show":
            return system.proposal(args.partition, args.proposal_id)
        if args.proposal_command == "list":
            return system.proposals(
                args.partition,
                status=args.status,
                after_sequence=args.after_sequence,
                limit=args.limit,
            )
        corrected: JSONValue | object = _MISSING
        if args.output is not None:
            corrected = _input(args.output)
        kwargs: dict[str, Any] = {
            "reviewer": args.reviewer,
            "decision": args.decision,
            "note": args.note,
        }
        if corrected is not _MISSING:
            kwargs["corrected_output"] = corrected
        return system.review(args.partition, args.proposal_id, **kwargs)
    if args.command == "request":
        return system.request_status(args.partition, args.request_id)
    if args.command == "compile":
        return system.compile(args.partition, args.operation, compiled_by=args.actor)
    if args.command == "verify":
        return system.verify(args.partition, args.artifact_id, verified_by=args.actor)
    if args.command == "promote":
        return system.promote(
            args.partition,
            args.artifact_id,
            scope_hash=args.scope_hash,
            promoted_by=args.actor,
        )
    if args.command == "challenge":
        example_id, suspended = system.challenge(
            args.partition,
            args.operation,
            _input(args.input),
            _input(args.expected),
            reviewer=args.reviewer,
            note=args.note,
        )
        return {"example_id": example_id, "suspended": suspended}
    if args.command == "example":
        if args.example_command == "list":
            return system.examples(
                args.partition,
                args.operation,
                include_revoked=args.include_revoked,
                after_sequence=args.after_sequence,
                limit=args.limit,
            )
        suspended = system.revoke_example(
            args.partition,
            args.example_id,
            revoked_by=args.actor,
            reason=args.reason,
        )
        return {"example_id": args.example_id, "suspended_artifact_ids": suspended}
    if args.command == "artifact":
        if args.artifact_command == "list":
            return system.artifacts(
                args.partition,
                args.operation,
                after_sequence=args.after_sequence,
                limit=args.limit,
            )
        if args.artifact_command == "show":
            return system.artifact(args.partition, args.artifact_id)
        system.suspend_artifact(
            args.partition,
            args.artifact_id,
            suspended_by=args.actor,
            reason=args.reason,
        )
        return {"artifact_id": args.artifact_id, "status": "suspended"}
    if args.command == "report":
        if args.report_command == "show":
            return system.report(
                args.partition,
                args.report_id,
                after_test_key=args.after_test_key,
                test_limit=args.test_limit,
            )
        return system.reports(
            args.partition,
            artifact_id=args.artifact_id,
            after_sequence=args.after_sequence,
            limit=args.limit,
        )
    if args.command == "function":
        if args.function_command == "show":
            return system.function_report(
                args.partition,
                args.operation,
                projection_limit=args.projection_limit,
            )
    if args.command == "events":
        return system.events(args.partition, after=args.after, limit=args.limit)
    raise AssertionError("argparse accepted an unknown command")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        result = _run(args, parser)
    except _UsageError as exc:
        _emit({"error": "invalid", "message": str(exc)}, stream=sys.stderr)
        return 2
    except NotFoundError as exc:
        _emit({"error": "not_found", "message": str(exc)}, stream=sys.stderr)
        return 3
    except (ConflictError, StateError) as exc:
        _emit({"error": "conflict", "message": str(exc)}, stream=sys.stderr)
        return 4
    except IntegrityError as exc:
        _emit({"error": "integrity", "message": str(exc)}, stream=sys.stderr)
        return 5
    except (ValidationError, CementError) as exc:
        _emit({"error": "invalid", "message": str(exc)}, stream=sys.stderr)
        return 2
    if isinstance(result, _Outcome):
        if result.raw is not None:
            binary = getattr(sys.stdout, "buffer", None)
            if binary is not None:
                binary.write(result.raw.encode("utf-8"))
            else:
                sys.stdout.write(result.raw)
        else:
            _emit(result.payload)
        return result.status
    _emit(result)
    return 0
