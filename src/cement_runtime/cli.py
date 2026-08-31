"""JSON-first operator CLI."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
import contextlib
from dataclasses import asdict, dataclass, field, is_dataclass
import json
import os
import pathlib
import stat
import sys
from typing import Any, Never, cast

from .errors import (
    CementError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    ValidationError,
)
from .function import FUNCTION_MAX_BYTES, FunctionDocument, evaluate, parse_function
from .json_value import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
    JSONValue,
    canonicalize,
    parse_json,
)
from .models import Candidate, CompilePolicy
from .system import PROVENANCE_MAX_BYTES, System, _name


class _UsageError(Exception):
    pass


class _Unverified(Exception):
    """A negative verification verdict carrying its finished stderr payload.

    Deliberately not a `CementError`: `main`'s residual clause catches that base
    and would downgrade a refused export to exit 2.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload["message"])
        self.payload = payload


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
        description=(
            "Supervised proposal capture that compiles confirmed behavior into"
            " exact deterministic artifacts, then answers inputs from the"
            " promoted function set"
        ),
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

    # Placed second because this is the operating verb: every other group
    # administers the function object, and this one answers from it.
    resolve = commands.add_parser(
        "resolve",
        help="verify the promoted function set, then answer one input from it",
        allow_abbrev=False,
    )
    resolve.add_argument("operation")
    resolve.add_argument("--input", required=True, help="JSON text; '-' reads stdin")
    resolve.add_argument(
        "--expected-function-hash", help="require the promoted set to hash to this digest"
    )

    proposal = commands.add_parser(
        "proposal", help="submit/inspect/review supervised proposals"
    )
    proposal_commands = proposal.add_subparsers(dest="proposal_command", required=True)
    proposal_submit = proposal_commands.add_parser("submit", allow_abbrev=False)
    proposal_submit.add_argument("operation")
    proposal_submit.add_argument(
        "--submission",
        required=True,
        help="JSON object {input, output, provenance?}; '-' reads stdin",
    )
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

    compile_command = commands.add_parser("compile", help="build eligible exact lookup drafts")
    compile_command.add_argument("operation")
    compile_command.add_argument("--actor", default="local-system")

    verify = commands.add_parser("verify", help="replay the full exact scope and boundaries")
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
    function_show.add_argument("--receipt-id", help="pin the anchor to one historical receipt")
    function_show.add_argument("--projection-limit", type=int, default=100)
    function_receipts = function_commands.add_parser("receipts")
    function_receipts.add_argument("operation")
    function_receipts.add_argument("--operation-revision", type=int)
    function_receipts.add_argument("--before-sequence", type=int)
    function_receipts.add_argument("--limit", type=int, default=100)
    function_verify_drafts = function_commands.add_parser("verify-drafts")
    function_verify_drafts.add_argument("operation")
    function_verify_drafts.add_argument("--actor", required=True)
    function_verify = function_commands.add_parser("verify")
    function_verify.add_argument("operation")
    function_verify.add_argument(
        "--expected-function-hash", help="require the committed set to hash to this digest"
    )
    function_inspect = function_commands.add_parser("inspect")
    function_inspect.add_argument("operation")
    function_promote = function_commands.add_parser("promote")
    function_promote.add_argument("operation")
    function_promote.add_argument(
        "--expected-function-hash",
        required=True,
        help="repeat the prospective digest `function inspect` reports",
    )
    function_promote.add_argument("--actor", required=True)
    function_export = function_commands.add_parser("export")
    function_export.add_argument("operation")
    function_export.add_argument(
        "--receipt-id", help="export one immutable historical receipt instead of the current set"
    )
    function_export.add_argument(
        "--out", help="write the bundle atomically to PATH instead of stdout"
    )
    function_eval = function_commands.add_parser("eval")
    function_eval.add_argument("--bundle", required=True, help="path of an exported bundle file")
    function_eval.add_argument("--input", required=True, help="JSON text; '-' reads stdin")
    function_eval.add_argument(
        "--expected-function-hash", help="require the bundle to hash to this digest"
    )

    events = commands.add_parser("events", help="read append-only audit projections")
    events.add_argument("--after", type=int, default=0)
    events.add_argument("--limit", type=int, default=1_000)
    return parser


def _input(value: str) -> JSONValue:
    if value != "-":
        return parse_json(value).value
    binary = getattr(sys.stdin, "buffer", None)
    # Both reads are host I/O, so a stream fault arrives as `OSError`. Every
    # leaf accepting `--input -` would otherwise lose the JSON-first contract
    # and hand automation a traceback instead of a status class.
    if binary is not None:
        try:
            raw = binary.read(DEFAULT_MAX_BYTES + 1)
        except OSError as exc:
            raise ValidationError("JSON stdin could not be read") from exc
        if len(raw) > DEFAULT_MAX_BYTES:
            raise ValidationError(f"JSON stdin exceeds {DEFAULT_MAX_BYTES} bytes")
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON stdin is not valid UTF-8") from exc
    else:
        # StringIO and embedding hosts expose text-only streams. The parser's
        # UTF-8 byte check remains authoritative after this bounded char read.
        try:
            source = sys.stdin.read(DEFAULT_MAX_BYTES + 1)
        except OSError as exc:
            raise ValidationError("JSON stdin could not be read") from exc
        if len(source) > DEFAULT_MAX_BYTES:
            raise ValidationError(f"JSON stdin exceeds {DEFAULT_MAX_BYTES} characters")
    return parse_json(source).value


_SUBMISSION_KEYS = ("input", "output", "provenance")
_SUBMISSION_REQUIRED = ("input", "output")
# `{` and `}`, one `,` between each adjacent pair, and `"<key>":` per key. The
# transport bound must admit every submission the library accepts, so it is
# DERIVED from the library's own two limits plus the exact cost of the envelope
# that carries them. A copied number is a second source of truth that drifts.
_SUBMISSION_FRAMING = (
    2 + (len(_SUBMISSION_KEYS) - 1) + sum(len(key) + 3 for key in _SUBMISSION_KEYS)
)
SUBMISSION_MAX_BYTES = 2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + _SUBMISSION_FRAMING


def _submission_stdin() -> str:
    """Read one aggregate frame, mirroring `_input`'s three failure families."""

    binary = getattr(sys.stdin, "buffer", None)
    if binary is None:
        # StringIO and embedding hosts expose text-only streams; the parser's
        # own UTF-8 check stays authoritative after this bounded char read.
        try:
            source = sys.stdin.read(SUBMISSION_MAX_BYTES + 1)
        except OSError as exc:
            raise ValidationError("submission stdin could not be read") from exc
        if len(source) > SUBMISSION_MAX_BYTES:
            raise ValidationError(
                f"submission stdin exceeds {SUBMISSION_MAX_BYTES} characters"
            )
        return source
    try:
        raw = binary.read(SUBMISSION_MAX_BYTES + 1)
    except OSError as exc:
        raise ValidationError("submission stdin could not be read") from exc
    if len(raw) > SUBMISSION_MAX_BYTES:
        raise ValidationError(f"submission stdin exceeds {SUBMISSION_MAX_BYTES} bytes")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("submission stdin is not valid UTF-8") from exc


def _submission(value: str) -> dict[str, JSONValue]:
    """Parse one aggregate submission envelope from inline text or stdin.

    One frame carries all three fields at their library maxima. Per-field flags
    cannot: `execve` refuses 131,072 argument bytes, and only one field can
    leave argv through stdin because a second `-` read finds a drained stream,
    so two of three fields would always be both truncated and world-readable in
    `/proc/<pid>/cmdline`.

    Strict parsing runs first, so a duplicate member fails inside the parser
    before any exact-key check can silently collapse it to one.
    """

    source = _submission_stdin() if value == "-" else value
    parsed = parse_json(
        source,
        max_bytes=SUBMISSION_MAX_BYTES,
        # The envelope nests each field one level deeper and adds three members.
        max_depth=DEFAULT_MAX_DEPTH + 1,
        max_items=3 * DEFAULT_MAX_ITEMS + 3,
    ).value
    if type(parsed) is not dict:
        raise ValidationError("submission must be a JSON object")
    unknown = sorted(set(parsed) - set(_SUBMISSION_KEYS))
    if unknown:
        raise ValidationError("submission has unknown keys: " + ", ".join(unknown))
    missing = sorted(set(_SUBMISSION_REQUIRED) - set(parsed))
    if missing:
        raise ValidationError("submission is missing required keys: " + ", ".join(missing))
    return parsed


def _absent_ledger(value: str) -> bool:
    """Report whether `value` is a path `Store` would CREATE: absent, under a directory.

    Deliberately narrower than `os.path.exists`, which follows the link and so reports a
    DANGLING SYMLINK as absent. Every path shape `System` already diagnoses precisely —
    dangling symlink, embedded NUL, missing parent, denied ancestor, non-regular file —
    returns False here and keeps its own `ValidationError` at exit 2, so this check never
    converts one of those verdicts into the caller-visible integrity class.
    """

    try:
        os.lstat(value)
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        return False
    else:
        return False
    try:
        return stat.S_ISDIR(os.stat(os.path.dirname(value) or ".").st_mode)
    except (OSError, ValueError):
        return False


def _emit(value: Any, *, stream: Any = None) -> None:
    if stream is None:
        stream = sys.stdout
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _reject_export_target(target: pathlib.Path) -> None:
    """Admit an absent name or a plain regular file, and nothing else.

    One `lstat` rather than a chain of `Path` predicates: each predicate is its
    own syscall, so a link installed between two of them is admitted by exactly
    the check meant to refuse it. `lstat` does not follow the final component,
    so a symlink answers `S_ISLNK` and `os.replace` never destroys the link.
    """
    try:
        mode = os.lstat(target).st_mode
    except (FileNotFoundError, NotADirectoryError):
        # Both belong to the parent, which the caller grades with its own message.
        return
    if not stat.S_ISREG(mode):
        raise ValidationError("export output path must identify a non-symlink regular file")


@contextlib.contextmanager
def _export_failures() -> Iterator[None]:
    """Collapse every OS-level `--out` failure into this leaf's own exit 2.

    The `Path` predicates raise `EACCES` on a search-denied ancestor and `main`
    maps no bare `OSError`, so the structural checks need the same translation
    the writer gives its syscalls.
    """
    try:
        yield
    except ValidationError:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValidationError("export output could not be written safely") from exc


# Draws from a 2**48 name space, so exhaustion means the directory is hostile
# rather than crowded, and the writer reports that as any other failure.
_EXPORT_ATTEMPTS = 128


def _export_temporary(target: pathlib.Path) -> tuple[int, pathlib.Path]:
    """Open a fresh 0600 file beside the destination, provably not the destination.

    `tempfile.mkstemp` derives its name from a prefix alone, so a target whose
    own name reproduces that prefix can be drawn as its own temp: the payload is
    then written straight through the destination name, which appears as an
    empty file before the bundle exists. Naming the candidate here keeps the two
    distinct before anything is created. The leading dot hides a leftover from a
    plain `ls`, and the cap keeps the whole name inside `NAME_MAX` for target
    names up to the filesystem maximum.
    """
    for _ in range(_EXPORT_ATTEMPTS):
        candidate = target.with_name(f".{target.name[:64]}.{os.urandom(6).hex()}")
        if candidate == target:
            continue
        try:
            return os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), candidate
        except FileExistsError:
            continue
    raise ValidationError("export output could not be written safely")


def _export_target(value: str) -> pathlib.Path:
    target = pathlib.Path(value)
    with _export_failures():
        # `Path` drops a trailing separator, so `name/` would grade as the plain
        # regular file `name` and replace it, discarding the directory the
        # caller asserted. `os.open` refuses that spelling and so does the
        # bundle reader, so refuse it here rather than diverge.
        if value.endswith(("/", os.sep)):
            raise ValidationError(
                "export output path must not end with a directory separator"
            )
        _reject_export_target(target)
        if not target.parent.is_dir():
            raise ValidationError("export output directory does not exist")
        return target.parent.resolve() / target.name


def _write_export(target: pathlib.Path, document: FunctionDocument) -> dict[str, Any]:
    payload = document.text.encode("utf-8")
    temporary: pathlib.Path | None = None
    try:
        with _export_failures():
            descriptor, temporary = _export_temporary(target)
            try:
                stream = os.fdopen(descriptor, "wb")
            except BaseException:
                os.close(descriptor)
                raise
            with stream:
                # `os.open`'s mode is masked by the umask, so a permissive one
                # would otherwise publish a world-readable bundle.
                os.fchmod(stream.fileno(), 0o600)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            # Rerun the guard here, not only at selection time: rename(2) carries
            # no target-identity predicate, so this is the narrowest window
            # available.
            _reject_export_target(target)
            os.replace(temporary, target)
            temporary = None
    finally:
        if temporary is not None:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
    return {"out": str(target), "bytes": len(payload), "function_hash": document.function_hash}


def _read_function_bundle(value: str) -> str:
    """Read one bounded regular file as strict UTF-8 text.

    `O_NONBLOCK` keeps the identity check reachable on a FIFO with no writer,
    which a plain open would wait on with no timeout to end the wait. The
    `fstat` size test only shortens the oversize path; the bounded read is the
    gate that still holds when a regular file grows between the two.
    """
    try:
        descriptor = os.open(value, os.O_RDONLY | os.O_NONBLOCK)
    except (OSError, ValueError) as exc:
        raise ValidationError("function bundle could not be read") from exc
    try:
        try:
            # Identity is graded on the descriptor, before any buffered stream:
            # `fdopen` refuses a directory itself, which would report a read
            # failure where the honest verdict is the file type.
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode):
                raise ValidationError("function bundle path must identify a regular file")
            if info.st_size > FUNCTION_MAX_BYTES:
                raise ValidationError(f"function bundle exceeds {FUNCTION_MAX_BYTES} bytes")
            stream = os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)
            raise
        with stream:
            raw = stream.read(FUNCTION_MAX_BYTES + 1)
    except ValidationError:
        # `ValidationError` subclasses `ValueError`, so the residual clause below
        # would otherwise rewrite this helper's own two verdicts as a read failure.
        raise
    except (OSError, ValueError) as exc:
        raise ValidationError("function bundle could not be read") from exc
    if len(raw) > FUNCTION_MAX_BYTES:
        raise ValidationError(f"function bundle exceeds {FUNCTION_MAX_BYTES} bytes")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("function bundle is not valid UTF-8") from exc


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Any:
    if args.command == "function" and args.function_command == "eval":
        # Ahead of the ledger gate and constructing no System: the bundle is the
        # whole evaluation domain. The input is graded first because it costs no
        # filesystem work, and a bundle read costs up to 64 MiB.
        input_json = canonicalize(_input(args.input))
        document = parse_function(
            _read_function_bundle(args.bundle),
            expected_function_hash=args.expected_function_hash,
        )
        match = evaluate(document, input_json=input_json)
        return _Outcome(
            {
                "artifact_hash": match.artifact_hash,
                "function_hash": document.function_hash,
                "matched": match.matched,
                "output": match.output,
            },
            status=0 if match.matched else 6,
        )
    if not args.db:
        parser.error("--db or CEMENT_DB is required")
    if not args.partition:
        parser.error("--partition or CEMENT_PARTITION is required")
    if args.command == "resolve" and _absent_ledger(args.db):
        # Constructing `System` on an absent path creates a 208,896-byte ledger
        # and then answers a read verb out of it. This forwards the library's
        # own verdict for the same condition rather than inventing vocabulary.
        # Stated as it behaves: a check, not a read-only construction mode. A
        # path deleted between this check and construction is still recreated by
        # `Store`, which is the shipped behaviour, so the check improves for a
        # stably absent path; in the inverse race a ledger appearing between the
        # two turns a would-be success into this exit 5. It is also what makes
        # the input ordering safe: on an absent ledger nothing is constructed,
        # so a malformed `--input` rejected after construction can only ever
        # touch a ledger that already existed.
        raise IntegrityError("ledger file is missing or unreadable")
    system = System(args.db)

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
    if args.command == "resolve":
        resolution = system.resolve(
            args.partition,
            args.operation,
            _input(args.input),
            expected_function_hash=args.expected_function_hash,
        )
        verification = resolution.verification
        match = resolution.match
        # One fixed key set across all three states, so a verified miss and a
        # failed verdict stay distinguishable under their shared exit 6. The
        # nested FunctionDocument never reaches stdout.
        matched = None if match is None else match.matched
        return _Outcome(
            {
                "artifact_hash": None if match is None else match.artifact_hash,
                "checks": [asdict(check) for check in verification.checks],
                "entries": verification.entries,
                "function_hash": verification.function_hash,
                "matched": matched,
                "output": None if match is None else match.output,
                "passed": verification.passed,
            },
            status=0 if matched is True else 6,
        )
    if args.command == "proposal":
        if args.proposal_command == "submit":
            envelope = _submission(args.submission)
            # The bare identifier `submit_proposal` returns renders as a bare
            # JSON string with no key to bind, so the acknowledgement names it.
            # It echoes no candidate byte and carries no request identity.
            return {
                "proposal_id": system.submit_proposal(
                    args.partition,
                    args.operation,
                    envelope["input"],
                    candidate=Candidate(
                        output=envelope["output"],
                        # Provenance shape stays library-graded; no CLI-only
                        # coercion is added.
                        provenance=cast(Any, envelope.get("provenance", {})),
                    ),
                )
            }
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
                receipt_id=args.receipt_id,
                projection_limit=args.projection_limit,
            )
        if args.function_command == "receipts":
            return system.function_receipts(
                args.partition,
                args.operation,
                operation_revision=args.operation_revision,
                before_sequence=args.before_sequence,
                limit=args.limit,
            )
        if args.function_command == "verify-drafts":
            drafts = system.verify_drafts(
                args.partition,
                args.operation,
                verified_by=args.actor,
            )
            return _Outcome(drafts, status=0 if drafts.passed else 6)
        if args.function_command == "verify":
            verification = system.verify_function(
                args.partition,
                args.operation,
                expected_function_hash=args.expected_function_hash,
            )
            # The result nests a FunctionDocument, which never reaches stdout.
            return _Outcome(
                {
                    "passed": verification.passed,
                    "entries": verification.entries,
                    "function_hash": verification.function_hash,
                    "checks": [asdict(check) for check in verification.checks],
                },
                status=0 if verification.passed else 6,
            )
        if args.function_command == "inspect":
            manifest = system.inspect_function_promotion(
                args.partition,
                args.operation,
            )
            # `text` and `document` carry the whole function document; u4c5's
            # export owns those bytes, so the manifest reaches stdout projected.
            return {
                "operation_revision": manifest.operation_revision,
                "function_hash": manifest.function_hash,
                "entries": [asdict(entry) for entry in manifest.entries],
                "skipped": list(manifest.skipped),
            }
        if args.function_command == "promote":
            return system.promote_function(
                args.partition,
                args.operation,
                expected_function_hash=args.expected_function_hash,
                promoted_by=args.actor,
            )
        if args.function_command == "export":
            # The historical branch passes the operation to no library call, so
            # without this the same positional is graded by grammar on one
            # branch and by receipt membership on the other.
            _name(args.operation, "operation")
            # The destination is graded before any ledger work: a structurally
            # unusable path is repaired by no ledger change, and a shell redirect
            # preempts the producer the same way.
            target = _export_target(args.out) if args.out is not None else None
            if args.receipt_id is not None:
                # Reconstruction keys on partition + receipt ID alone, so the
                # positional operation is checked here or not at all.
                reconstruction = system.reconstruct_function_receipt(
                    args.partition,
                    args.receipt_id,
                )
                if reconstruction.receipt.operation != args.operation:
                    raise NotFoundError("function receipt does not exist for this operation")
                document = reconstruction.document
            else:
                verification = system.verify_function(args.partition, args.operation)
                if not verification.passed:
                    raise _Unverified(
                        {
                            "error": "unverified",
                            "message": "function verification failed; no bundle exported: "
                            + "; ".join(
                                f"{check.key}: {check.detail}"
                                for check in verification.checks
                                if not check.passed
                            ),
                            "checks": [asdict(check) for check in verification.checks],
                        }
                    )
                if verification.document is None:
                    raise IntegrityError(
                        "function verification passed without an exportable document"
                    )
                document = verification.document
            if target is None:
                return _Outcome(raw=document.text)
            return _write_export(target, document)
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
    except _Unverified as exc:
        _emit(exc.payload, stream=sys.stderr)
        return 6
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
