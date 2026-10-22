"""JSON-first operator CLI."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import pathlib
import stat
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Never, cast

from . import learning
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
from .system import PROVENANCE_MAX_BYTES, SOURCE_ID_MAX_BYTES, System, _name, _text


class _UsageError(Exception):
    pass


class _Unverified(Exception):  # noqa: N818 — a verdict carrier mapped to exit 6, not an error
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
            "Retain recorded LLM answers as proposals. A learning pass confirms the"
            " cases that recur and compiles them into exact deterministic functions."
            " Cement answers matching inputs from the version that a person switches on"
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
    policy = CompilePolicy()
    for name in ("register", "revise"):
        action = operation_commands.add_parser(name)
        action.add_argument("operation")
        action.add_argument("--min-confirmations", type=int, default=policy.min_confirmations)
        action.add_argument("--min-reviewers", type=int, default=policy.min_reviewers)
        action.add_argument("--min-span-seconds", type=int, default=policy.min_span_seconds)
        if name == "revise":
            action.add_argument("--actor", required=True)
        else:
            action.add_argument("--actor", default="local-system")
    operation_commands.add_parser("list")

    # Placed second because this is the operating verb: every other group
    # administers the function object, and this one answers from it.
    resolve = commands.add_parser(
        "resolve",
        help="verify the version that the switch selects, then answer one input from it",
        allow_abbrev=False,
    )
    resolve.add_argument("operation")
    resolve.add_argument("--input", required=True, help="JSON text; '-' reads stdin")
    resolve.add_argument(
        "--expected-function-hash", help="require the served version to hash to this digest"
    )

    proposal = commands.add_parser("proposal", help="submit/inspect/review retained proposals")
    proposal_commands = proposal.add_subparsers(dest="proposal_command", required=True)
    proposal_submit = proposal_commands.add_parser("submit", allow_abbrev=False)
    proposal_submit.add_argument("operation")
    proposal_submit.add_argument(
        "--submission",
        required=True,
        help="JSON object {input, output, provenance?, source_id?}; '-' reads stdin",
    )
    proposal_show = proposal_commands.add_parser("show")
    proposal_show.add_argument("proposal_id")
    proposal_list = proposal_commands.add_parser("list")
    proposal_list.add_argument(
        "--status",
        choices=("all", "pending", "accepted", "corrected", "rejected"),
        default="pending",
    )
    proposal_list.add_argument("--after-sequence", type=int, default=0)
    proposal_list.add_argument("--limit", type=int, default=100)
    proposal_review = proposal_commands.add_parser("review")
    proposal_review.add_argument("proposal_id")
    proposal_review.add_argument("--reviewer", required=True)
    proposal_review.add_argument(
        "--decision", choices=("accept", "correct", "reject"), required=True
    )
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

    challenge = commands.add_parser(
        "challenge", help="confirm or counterexample an active artifact"
    )
    challenge.add_argument("operation")
    challenge.add_argument("--input", required=True)
    challenge.add_argument("--expected", required=True)
    challenge.add_argument("--reviewer", required=True)
    challenge.add_argument("--note", default="")

    example = commands.add_parser("example", help="inspect, revoke or supersede confirmed fixtures")
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
    example_supersede = example_commands.add_parser("supersede", allow_abbrev=False)
    example_supersede.add_argument("operation")
    example_supersede.add_argument("example_ids", nargs="+")
    example_supersede.add_argument("--output", required=True)
    example_supersede.add_argument("--reviewer", required=True)
    example_supersede.add_argument("--note", default="")

    artifact = commands.add_parser("artifact", help="inspect/suspend deterministic builds")
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

    function = commands.add_parser(
        "function", help="inspect, promote, switch and export the operation's function"
    )
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
    function_switch = function_commands.add_parser("switch", allow_abbrev=False)
    function_switch.add_argument("operation")
    function_switch.add_argument("--mode", required=True, choices=("off", "follow", "pinned"))
    function_switch.add_argument("--function-hash", help="the version a pinned switch serves")
    function_switch.add_argument("--actor", required=True)
    function_versions = function_commands.add_parser("versions", allow_abbrev=False)
    function_versions.add_argument("operation")
    function_versions.add_argument("--before-sequence", type=int)
    function_versions.add_argument("--limit", type=int, default=100)
    function_versions.add_argument(
        "--check", action="store_true", help="also report whether each version would serve now"
    )
    function_diff = function_commands.add_parser("diff", allow_abbrev=False)
    function_diff.add_argument("operation")
    function_diff.add_argument("--from", dest="from_hash", required=True)
    function_diff.add_argument("--to", dest="to_hash", required=True)
    function_read = function_commands.add_parser(
        "read",
        help="read one version as its cases and the proposals behind each case",
        allow_abbrev=False,
    )
    function_read.add_argument("operation")
    function_read.add_argument("--receipt-id", help="read one historical version instead")
    function_read.add_argument("--json", action="store_true", help="print the listing as JSON")
    function_eval = function_commands.add_parser("eval")
    function_eval.add_argument("--bundle", required=True, help="path of an exported bundle file")
    function_eval.add_argument("--input", required=True, help="JSON text; '-' reads stdin")
    function_eval.add_argument(
        "--expected-function-hash", help="require the bundle to hash to this digest"
    )

    projection = commands.add_parser(
        "projection", help="test, set or show the program that maps raw input to case keys"
    )
    projection_commands = projection.add_subparsers(dest="projection_command", required=True)
    projection_test = projection_commands.add_parser("test", allow_abbrev=False)
    projection_test.add_argument("operation")
    projection_test.add_argument("--program", required=True, help="JSON text; '-' reads stdin")
    projection_set = projection_commands.add_parser("set", allow_abbrev=False)
    projection_set.add_argument("operation")
    projection_set.add_argument("--program", required=True, help="JSON text; '-' reads stdin")
    projection_set.add_argument("--actor", required=True)
    projection_show = projection_commands.add_parser("show", allow_abbrev=False)
    projection_show.add_argument("operation")

    learn = commands.add_parser(
        "learn", help="run the learning pass: read its work, merge one case, publish a version"
    )
    learn_commands = learn.add_subparsers(dest="learn_command", required=True)
    learn_cases = learn_commands.add_parser("cases", allow_abbrev=False)
    learn_cases.add_argument("operation")
    candidate = learn_cases.add_mutually_exclusive_group()
    candidate.add_argument(
        "--program", help="group by this candidate program (JSON text; '-' reads stdin)"
    )
    candidate.add_argument(
        "--projectable",
        action="store_true",
        help="group by a program derived from the raw inputs: one layout per form structure",
    )
    learn_merge = learn_commands.add_parser(
        "merge",
        help="confirm the merged output of one case: review its proposals, supersede its examples",
        allow_abbrev=False,
    )
    learn_merge.add_argument("operation")
    learn_merge.add_argument(
        "--output", required=True, help="the merged output (JSON text; '-' reads stdin)"
    )
    learn_merge.add_argument("--note", required=True, help="what the merge kept or added")
    # A bare flag means no ids: a case without examples still has a flag a model copies.
    learn_merge.add_argument(
        "--proposals", nargs="*", default=[], help="the case's pending proposal ids"
    )
    learn_merge.add_argument(
        "--examples", nargs="*", default=[], help="the case's active example ids"
    )
    learn_merge.add_argument(
        "--projectable",
        action="store_true",
        help="group the cases as `learn cases --projectable` does",
    )
    learn_merge.add_argument("--reviewer", default=learning.REVIEWER)
    learn_publish = learn_commands.add_parser(
        "publish",
        help="compile, verify and promote a new version; the switch decides whether it answers",
        allow_abbrev=False,
    )
    learn_publish.add_argument("operation")
    learn_publish.add_argument(
        "--projectable",
        action="store_true",
        help="first set the program derived from the confirmed inputs",
    )
    learn_publish.add_argument("--actor", default=learning.REVIEWER)

    events = commands.add_parser("events", help="read append-only audit projections")
    events.add_argument("--after", type=int, default=0)
    events.add_argument("--limit", type=int, default=1_000)
    # p49 (owner-ruled): no node accepts an abbreviated option, so a removed flag never stays
    # reachable through a surviving flag's prefix and a new flag cannot collide with one.
    _no_abbreviation(parser)
    return parser


def _no_abbreviation(parser: argparse.ArgumentParser) -> None:
    parser.allow_abbrev = False
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                _no_abbreviation(child)


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


_SUBMISSION_KEYS = ("input", "output", "provenance", "source_id")
_SUBMISSION_REQUIRED = ("input", "output")
# `{` and `}`, one `,` between each adjacent pair, and `"<key>":` per key. The
# transport bound must admit every submission the library accepts, so it is
# DERIVED from the library's own limits plus the exact cost of the envelope
# that carries them. A copied number is a second source of truth that drifts.
_SUBMISSION_FRAMING = (
    2 + (len(_SUBMISSION_KEYS) - 1) + sum(len(key) + 3 for key in _SUBMISSION_KEYS)
)
# A source id holds at most SOURCE_ID_MAX_BYTES UTF-8 bytes; JSON text spells each byte in at
# most 3 (a 4-byte scalar as a 12-byte surrogate-pair escape), inside two quotes.
_SOURCE_ID_WIRE_BYTES = 3 * SOURCE_ID_MAX_BYTES + 2
SUBMISSION_MAX_BYTES = (
    2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + _SOURCE_ID_WIRE_BYTES + _SUBMISSION_FRAMING
)


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
            raise ValidationError(f"submission stdin exceeds {SUBMISSION_MAX_BYTES} characters")
        return source
    try:
        raw: bytes = binary.read(SUBMISSION_MAX_BYTES + 1)
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

    One frame carries every field at its library maximum, the optional source id
    included. Per-field flags
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
        # The envelope nests each field one level deeper and adds four members.
        max_depth=DEFAULT_MAX_DEPTH + 1,
        max_items=3 * DEFAULT_MAX_ITEMS + 4,
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
            raise ValidationError("export output path must not end with a directory separator")
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
            # rename(2) is durable only once the directory entry reaches the disk.
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
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


def _policy(args: argparse.Namespace) -> CompilePolicy:
    return CompilePolicy(
        min_confirmations=args.min_confirmations,
        min_reviewers=args.min_reviewers,
        min_span_seconds=args.min_span_seconds,
    )


# The function report projects at most this many members; a larger version lists its later
# cases without their proposals and says so.
_LISTING_MEMBERS = 10_000


def _function_listing(
    system: System, partition: str, operation: str, *, receipt_id: str | None
) -> dict[str, Any]:
    """One version's cases with the confirmed proposals behind each, from public reads alone.

    The version is always an immutable receipt: `--receipt-id`, else the pinned one, else the
    newest, so a person reads a version before switching it on. Case values come from the rebuilt
    bundle; each case's proposals come from its artifact's evidence, joined to proposals through
    their review events.
    """
    _name(operation, "operation")
    state = system.switch(partition, operation)
    newest: str | None
    try:
        newest = system.latest_function_receipt(partition, operation).id
    except NotFoundError:
        newest = None
    if receipt_id is None:
        receipt_id = state.receipt_id if state.mode == "pinned" else newest
        if receipt_id is None:
            raise NotFoundError("the operation has no promoted version to read")
    reconstruction = system.reconstruct_function_receipt(partition, receipt_id)
    receipt = reconstruction.receipt
    if receipt.operation != operation:
        raise NotFoundError("function receipt does not exist for this operation")
    report = system.function_report(
        partition, operation, receipt_id=receipt.id, projection_limit=_LISTING_MEMBERS
    )
    anchor = report.function_anchor
    members = {
        member.input_hash: member.artifact_id for member in (anchor.members if anchor else ())
    }
    examples: dict[str, dict[str, Any]] = {}
    after = 0
    while page := system.examples(
        partition, operation, include_revoked=True, after_sequence=after, limit=1000
    ):
        examples.update((str(row["id"]), row) for row in page)
        after = int(cast(int, page[-1]["sequence"]))
    proposal_of: dict[str, str] = {}
    after = 0
    while events := system.events(partition, after=after, limit=1000):
        for event in events:
            if event["kind"] in ("proposal.accepted", "proposal.corrected"):
                payload = cast(dict[str, Any], event["payload"])
                proposal_of[str(payload["example_id"])] = str(event["subject_id"])
        after = int(cast(int, events[-1]["sequence"]))
    cases: list[dict[str, Any]] = []
    for entry in cast(list[dict[str, Any]], reconstruction.document.value["entries"]):
        artifact_id = members.get(str(entry["input_hash"]))
        behind: list[dict[str, Any]] = []
        unproposed: list[dict[str, Any]] = []
        if artifact_id is not None:
            for example_id in cast(
                list[str], system.artifact(partition, artifact_id)["evidence_ids"]
            ):
                # A superseding example carries no proposal; the one it replaced may.
                source, seen = example_id, {example_id}
                while source not in proposal_of:
                    replaced = examples.get(source, {}).get("supersedes_example_id")
                    if replaced is None or replaced in seen:
                        break
                    source = str(replaced)
                    seen.add(source)
                proposal_id = proposal_of.get(source)
                if proposal_id is None:
                    row = examples.get(example_id, {})
                    unproposed.append(
                        {"example_id": example_id, "origin": row.get("origin")}
                        | {"sequence": row.get("sequence", 0)}
                    )
                    continue
                proposal = system.proposal(partition, proposal_id)
                behind.append(
                    {
                        "proposal_id": proposal_id,
                        "decision": proposal["status"],
                        "proposed_output": proposal["proposed_output"],
                        "final_output": proposal["final_output"],
                        "superseded_by": None if source == example_id else example_id,
                        "sequence": proposal["sequence"],
                    }
                )
        # Arrival order, whatever order the artifact's evidence lists them in.
        for listed in (behind, unproposed):
            listed.sort(key=lambda item: int(item.pop("sequence")))
        cases.append(
            {
                "case": entry["input"],
                "output": entry["output"],
                "artifact_id": artifact_id,
                "proposals": behind,
                "examples_without_proposal": unproposed,
            }
        )
    answers = receipt.id == (state.receipt_id if state.mode == "pinned" else newest)
    return {
        "operation": operation,
        "operation_revision": receipt.operation_revision,
        "receipt_id": receipt.id,
        "function_hash": receipt.function_hash,
        "projection_hash": reconstruction.document.projection_hash,
        "switch": state.mode,
        "answers": answers and state.mode != "off",
        "newest": receipt.id == newest,
        "cases": cases,
    }


def _render_listing(listing: dict[str, Any]) -> str:
    """The human reading of `_function_listing`: one guarded branch per case, then the miss."""

    def text(value: Any) -> str:
        return canonicalize(value).text

    if listing["answers"]:
        serving = "this version answers matching inputs"
    elif listing["switch"] == "off":
        serving = "no version answers yet" + (
            "; this is the newest version" if listing["newest"] else ""
        )
    else:
        serving = "a different version answers"
    lines = [
        f"# function {listing['operation']}, version {listing['function_hash']}",
        f"# receipt {listing['receipt_id']}, operation revision {listing['operation_revision']}",
        f"# switch {listing['switch']}: {serving}",
        "# Cement seals exact cases and runs no code; this listing renders them.",
    ]
    if listing["projection_hash"] is not None:
        lines.append(
            f"# Each input maps to its case through projection {listing['projection_hash']}."
        )
    lines.append("")
    for case in listing["cases"]:
        lines += [f"if case == {text(case['case'])}:", f"    answer {text(case['output'])}"]
        for proposal in case["proposals"]:
            if proposal["decision"] == "corrected":
                outcome = f"corrected to {text(proposal['final_output'])}"
            else:
                outcome = str(proposal["decision"])
            if proposal["superseded_by"] is not None:
                outcome += f", later superseded by example {proposal['superseded_by']}"
            lines.append(
                f"    # proposal {proposal['proposal_id']}: proposed "
                f"{text(proposal['proposed_output'])}, {outcome}"
            )
        for example in case["examples_without_proposal"]:
            lines.append(
                f"    # example {example['example_id']}: "
                + (
                    "from a challenge"
                    if example["origin"] == "challenge"
                    else f"origin {example['origin']}"
                )
                + ", no proposal"
            )
        if case["artifact_id"] is None:
            lines.append(f"    # proposals not listed: past the first {_LISTING_MEMBERS} cases")
    lines += ["otherwise:", "    ask the LLM", ""]
    return "\n".join(lines)


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
    creating = args.command == "operation" and args.operation_command == "register"
    if creating:
        # The one leaf that creates a ledger grades every value first, so a malformed
        # argument never leaves a new ledger behind (p51).
        _name(args.partition, "partition")
        _name(args.operation, "operation")
        _text(args.actor, "registered_by", maximum=256)
        _policy(args)
    # Every other leaf needs an existing ledger, so a typo'd --db creates nothing and
    # exits 5 before any value is parsed (p50).
    system = System(args.db, create=creating)

    if args.command == "operation":
        if args.operation_command == "list":
            return system.operations(args.partition)
        policy = _policy(args)
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
        answer = resolution.match
        # One fixed key set across all four states (off, verified miss, failed verdict,
        # answer), so they stay distinguishable under their shared exit 6. The nested
        # FunctionDocument never reaches stdout.
        matched = None if answer is None else answer.matched
        return _Outcome(
            {
                "artifact_hash": None if answer is None else answer.artifact_hash,
                "checks": [] if verification is None else [asdict(c) for c in verification.checks],
                "entries": None if verification is None else verification.entries,
                "function_hash": None if verification is None else verification.function_hash,
                "matched": matched,
                "output": None if answer is None else answer.output,
                "passed": None if verification is None else verification.passed,
                "switch": resolution.switch.mode,
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
                    source_id=cast(Any, envelope.get("source_id")),
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
        if args.example_command == "supersede":
            created = system.supersede_examples(
                args.partition,
                args.operation,
                example_ids=args.example_ids,
                output=_input(args.output),
                reviewer=args.reviewer,
                note=args.note,
            )
            return {"example_ids": list(created), "superseded_example_ids": args.example_ids}
        suspended_ids = system.revoke_example(
            args.partition,
            args.example_id,
            revoked_by=args.actor,
            reason=args.reason,
        )
        return {"example_id": args.example_id, "suspended_artifact_ids": suspended_ids}
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
        if args.function_command == "switch":
            return asdict(
                system.set_switch(
                    args.partition,
                    args.operation,
                    mode=args.mode,
                    actor=args.actor,
                    function_hash=args.function_hash,
                )
            )
        if args.function_command == "versions":
            return asdict(
                system.function_versions(
                    args.partition,
                    args.operation,
                    before_sequence=args.before_sequence,
                    limit=args.limit,
                    check=args.check,
                )
            )
        if args.function_command == "read":
            listing = _function_listing(
                system, args.partition, args.operation, receipt_id=args.receipt_id
            )
            return listing if args.json else _Outcome(raw=_render_listing(listing))
        if args.function_command == "diff":
            return asdict(
                system.diff_versions(
                    args.partition,
                    args.operation,
                    from_hash=args.from_hash,
                    to_hash=args.to_hash,
                )
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
                state, served = system.serving(args.partition, args.operation)
                if served is None:
                    raise _Unverified(
                        {
                            "error": "switched_off",
                            "message": "the operation's function is switched off; no bundle "
                            "exported (switch it on, or pass --receipt-id)",
                            "switch": state.mode,
                        }
                    )
                verification = served
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
    if args.command == "projection":
        if args.projection_command == "test":
            return system.test_projection(args.partition, args.operation, _input(args.program))
        if args.projection_command == "set":
            return system.set_projection(
                args.partition, args.operation, _input(args.program), actor=args.actor
            )
        return {"projection": system.projection(args.partition, args.operation)}
    if args.command == "learn":
        if args.learn_command == "merge":
            try:
                return learning.merge_case(
                    system,
                    args.partition,
                    args.operation,
                    _input(args.output),
                    note=args.note,
                    proposal_ids=args.proposals,
                    example_ids=args.examples,
                    projectable=args.projectable,
                    reviewer=args.reviewer,
                )
            except learning.MergeInterruptedError as exc:
                # stdout lists the writes that returned; `main` reports the cause on stderr.
                _emit(exc.completed)
                raise exc.cause from None
        if args.learn_command == "publish":
            publication = learning.publish(
                system,
                args.partition,
                args.operation,
                projectable=args.projectable,
                actor=args.actor,
            )
            return _Outcome(publication, status=6 if publication.reason == "failed" else 0)
        if args.projectable:
            return learning.cases(system, args.partition, args.operation, projectable=True)
        return system.learning_cases(
            args.partition,
            args.operation,
            program=None if args.program is None else _input(args.program),
        )
    if args.command == "events":
        return system.events(args.partition, after=args.after, limit=args.limit)
    raise AssertionError("argparse accepted an unknown command")


def entry() -> int:
    """The process entry (`cement`, `python -m cement_runtime`): `main` plus interrupt handling.

    SIGINT surfaces as `KeyboardInterrupt` from wherever the command waits; a host embedding
    `main` keeps it, while the process reports it as JSON with the shell's status. A write the
    interrupt stopped never committed: `Store.transaction` closes its connection uncommitted.
    """
    try:
        return main()
    except KeyboardInterrupt:
        _emit(
            {"error": "interrupted", "message": "interrupted before completion"},
            stream=sys.stderr,
        )
        return 130


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
