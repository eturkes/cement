"""Command candidate source: run a trusted adapter executable for one candidate.

An optional example surface beside the core (`.agent/spec.md` Decisions, M3 seed (a)): the core
keeps only the `CandidateSource` protocol. The class below moved byte-identical from
`src/cement_runtime/source.py`; `_command_supervisor.py` sits beside it because the class launches
it by file name.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import signal
import subprocess
import sys
import threading
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

from cement_runtime import System
from cement_runtime.errors import (
    CandidateSourceError,
    CementError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    ValidationError,
)
from cement_runtime.json_value import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
    JSONValue,
    canonicalize,
    parse_json,
)
from cement_runtime.models import Candidate, CandidateRequest

SOURCE_PROTOCOL = "cement-candidate-v2"


class CommandCandidateSource:
    """Run a trusted adapter command with one JSON request on stdin.

    The command is invoked directly (``shell=False``). Its stdout must contain
    ``{"output": <json>, "provenance": <json-object>}``. Historical examples are
    intentionally absent from the request.
    """

    def __init__(
        self,
        argv: Sequence[str],
        *,
        source_id: str = "command-adapter",
        timeout_seconds: float = 60.0,
        max_output_bytes: int = 1_048_576,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if isinstance(argv, (str, bytes, bytearray)):
            raise ValidationError(
                "candidate command must be a sequence of non-empty, NUL-free strings"
            )
        try:
            command = tuple(argv)
        except TypeError as exc:
            raise ValidationError("candidate command must be a sequence of strings") from exc
        if not command:
            raise ValidationError(
                "candidate command must be a sequence of non-empty, NUL-free strings"
            )
        for argument in command:
            if type(argument) is not str or not argument or "\0" in argument:
                raise ValidationError(
                    "candidate command must be a sequence of non-empty, NUL-free strings"
                )
            try:
                argument.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValidationError(
                    "candidate command arguments must contain valid Unicode scalar values"
                ) from exc
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 3_600
        ):
            raise ValidationError("candidate timeout must be between zero and one hour")
        if type(max_output_bytes) is not int or not 1 <= max_output_bytes <= 16 * 1_048_576:
            raise ValidationError("candidate output limit must be between one byte and 16 MiB")
        if type(source_id) is not str or not source_id:
            raise ValidationError("source_id must be non-empty and at most 256 bytes")
        try:
            source_id_bytes = source_id.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationError("source_id must contain valid Unicode scalar values") from exc
        if len(source_id_bytes) > 256 or any(
            unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in source_id
        ):
            raise ValidationError("source_id must be control-free and at most 256 UTF-8 bytes")
        environment_items: tuple[tuple[str, str], ...] = ()
        if environment is not None:
            try:
                environment_items = tuple(environment.items())
            except AttributeError as exc:
                raise ValidationError("candidate environment must be a string mapping") from exc
            for key, value in environment_items:
                if (
                    type(key) is not str
                    or type(value) is not str
                    or not key
                    or "=" in key
                    or "\0" in key
                    or "\0" in value
                ):
                    raise ValidationError(
                        "candidate environment must contain non-empty string keys and string values"
                    )
                try:
                    key.encode("utf-8")
                    value.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValidationError(
                        "candidate environment must contain valid Unicode scalar values"
                    ) from exc
        self._argv = command
        self._source_id = source_id
        self._timeout = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._environment = dict(environment_items) if environment is not None else None

    def propose(self, request: CandidateRequest) -> Candidate:
        envelope: dict[str, JSONValue] = {
            "input": request.input,
            "operation": request.operation,
            "operation_revision": request.operation_revision,
            "partition": request.partition,
            "protocol": SOURCE_PROTOCOL,
        }
        # The envelope nests the input one level down beside its own keys: a value the library
        # accepted stays inside the protocol's limits.
        request_bytes = canonicalize(
            envelope,
            max_bytes=2_097_152,
            max_depth=DEFAULT_MAX_DEPTH + 1,
            max_items=DEFAULT_MAX_ITEMS + len(envelope),
        ).text.encode("utf-8")
        environment = None
        if self._environment is not None:
            # Explicit environments are exact: ambient credentials are excluded.
            environment = self._environment

        supervised = sys.platform.startswith("linux") and os.path.isdir("/proc")
        command: tuple[str, ...]
        timeout = self._timeout
        if supervised:
            encoded = base64.urlsafe_b64encode(
                json.dumps(self._argv, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            command = (
                sys.executable,
                str(Path(__file__).with_name("_command_supervisor.py")),
                encoded,
                repr(self._timeout),
                str(self._max_output_bytes),
            )
            # The supervisor owns the primary deadline and a bounded cleanup window.
            timeout += 10.0
        else:
            command = self._argv

        try:
            process = subprocess.Popen(  # noqa: S603 — argv list from the operator's own adapter config, no shell
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                env=environment,
                close_fds=True,
                start_new_session=os.name == "posix",
            )
        except (OSError, ValueError) as exc:
            raise CandidateSourceError("candidate command could not be started") from exc

        exceeded = threading.Event()
        raw = bytearray()

        def kill_tree() -> None:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    return
                except OSError:
                    pass
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass

        def write_request() -> None:
            assert process.stdin is not None  # noqa: S101 — narrowing only: Popen(..., PIPE)
            try:
                process.stdin.write(request_bytes)
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            finally:
                process.stdin.close()

        def read_bounded(stream: Any, *, capture: bool) -> None:
            total = 0
            try:
                while chunk := stream.read(65_536):
                    total += len(chunk)
                    if total > self._max_output_bytes:
                        exceeded.set()
                        kill_tree()
                        return
                    if capture:
                        raw.extend(chunk)
            except (OSError, ValueError):
                pass
            finally:
                stream.close()

        threads: tuple[threading.Thread, ...] = ()
        started: list[threading.Thread] = []
        timed_out = False
        setup_error: Exception | None = None
        cleanup_failed = False
        try:
            assert process.stdout is not None and process.stderr is not None  # noqa: S101 — narrowing only
            threads = (
                threading.Thread(target=write_request, daemon=True),
                threading.Thread(
                    target=read_bounded,
                    args=(process.stdout,),
                    kwargs={"capture": True},
                    daemon=True,
                ),
                threading.Thread(
                    target=read_bounded,
                    args=(process.stderr,),
                    kwargs={"capture": False},
                    daemon=True,
                ),
            )
            for thread in threads:
                thread.start()
                started.append(thread)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
        except (MemoryError, OSError, RuntimeError) as exc:
            setup_error = exc
        finally:
            # A one-shot adapter may not leave credential-bearing descendants.
            kill_tree()
            if process.poll() is None:
                try:
                    process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    cleanup_failed = True
            for thread in started:
                thread.join(timeout=2.0)
            cleanup_failed = (
                cleanup_failed
                or len(started) != len(threads)
                or any(thread.is_alive() for thread in started)
            )
        if setup_error is not None:
            raise CandidateSourceError(
                "candidate command supervision could not be started"
            ) from setup_error
        if cleanup_failed:
            raise CandidateSourceError("candidate command descendant cleanup failed")
        if timed_out:
            raise CandidateSourceError("candidate command timed out")
        if exceeded.is_set():
            raise CandidateSourceError("candidate command output exceeded its byte limit")
        if supervised and process.returncode == 124:
            raise CandidateSourceError("candidate command timed out")
        if supervised and process.returncode == 125:
            raise CandidateSourceError("candidate command output exceeded its byte limit")
        if supervised and process.returncode == 126:
            raise CandidateSourceError("candidate command could not be started")
        if supervised and process.returncode == 127:
            raise CandidateSourceError("candidate command descendant cleanup failed")
        if process.returncode != 0:
            # Adapter stderr can contain prompts, credentials, or model output.
            raise CandidateSourceError(f"candidate command exited with status {process.returncode}")

        try:
            # `output` + `provenance` sit one level down, beside their two keys; each keeps the
            # limits the library grades it by (provenance: at most 64 KiB, so fewer items).
            response = parse_json(
                bytes(raw).decode("utf-8"),
                max_bytes=self._max_output_bytes,
                max_depth=DEFAULT_MAX_DEPTH + 1,
                max_items=DEFAULT_MAX_ITEMS + 2 + 65_536,
            ).value
        except (UnicodeDecodeError, ValidationError) as exc:
            raise CandidateSourceError("candidate command returned invalid JSON") from exc
        if type(response) is not dict or set(response) != {"output", "provenance"}:
            raise CandidateSourceError(
                "candidate response must contain exactly 'output' and 'provenance'"
            )
        provenance = response["provenance"]
        if type(provenance) is not dict:
            raise CandidateSourceError("candidate provenance must be a JSON object")
        try:
            reported = canonicalize(provenance, max_bytes=65_536).value
        except ValidationError as exc:
            raise CandidateSourceError("candidate provenance is invalid or oversized") from exc
        if type(reported) is not dict:
            raise AssertionError("canonical provenance changed type")
        combined: dict[str, JSONValue] = {
            "adapter": "command",
            "reported": reported,
            "source_id": self._source_id,
        }
        return Candidate(output=response["output"], provenance=combined)


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _UsageError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="cement-command-source",
        allow_abbrev=False,
        description=(
            "Run a trusted adapter command for one input. Cement retains the candidate"
            " that the adapter returns as a pending proposal."
        ),
    )
    parser.add_argument("--db", default=os.environ.get("CEMENT_DB"), help="SQLite ledger path")
    parser.add_argument(
        "--partition",
        default=os.environ.get("CEMENT_PARTITION"),
        help="explicit tenant/workflow isolation key",
    )
    parser.add_argument("operation", help="a registered operation")
    parser.add_argument("--input", required=True, help="JSON text; '-' reads stdin")
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="seconds that the adapter can run"
    )
    parser.add_argument(
        "adapter", nargs="+", help="the adapter argv after '--'; Cement runs it without a shell"
    )
    return parser


def _input(value: str) -> JSONValue:
    if value == "-":
        # A text-only stream (an embedding host's StringIO) has no `buffer`; `parse_json` still
        # grades the UTF-8 byte size after this bounded read.
        stream = getattr(sys.stdin, "buffer", sys.stdin)
        try:
            raw = stream.read(DEFAULT_MAX_BYTES + 1)
        except OSError as exc:
            raise ValidationError("JSON stdin could not be read") from exc
        if len(raw) > DEFAULT_MAX_BYTES:
            unit = "bytes" if isinstance(raw, bytes) else "characters"
            raise ValidationError(f"JSON stdin exceeds {DEFAULT_MAX_BYTES} {unit}")
        try:
            value = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON stdin is not valid UTF-8") from exc
    return parse_json(value).value


def _emit(value: object, stream: Any) -> None:
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    """`cement-command-source`: propose one candidate through the adapter, as `System.propose`.

    stdout = `{"proposal_id": ...}`; a refusal = `{"error", "message"}` on stderr with the exit
    classes of `cement` (2 invalid, an adapter failure included; 3 not found; 4 conflict;
    5 integrity).
    """
    try:
        args = _parser().parse_args(argv)
        if not args.db:
            raise _UsageError("--db or CEMENT_DB is required")
        if not args.partition:
            raise _UsageError("--partition or CEMENT_PARTITION is required")
        source = CommandCandidateSource(args.adapter, timeout_seconds=args.timeout)
        input_value = _input(args.input)
        system = System(args.db, create=False, candidate_source=source)
        proposal_id = system.propose(args.partition, args.operation, input_value)
    except _UsageError as exc:
        _emit({"error": "invalid", "message": str(exc)}, sys.stderr)
        return 2
    except NotFoundError as exc:
        _emit({"error": "not_found", "message": str(exc)}, sys.stderr)
        return 3
    except (ConflictError, StateError) as exc:
        _emit({"error": "conflict", "message": str(exc)}, sys.stderr)
        return 4
    except IntegrityError as exc:
        _emit({"error": "integrity", "message": str(exc)}, sys.stderr)
        return 5
    except CementError as exc:
        _emit({"error": "invalid", "message": str(exc)}, sys.stderr)
        return 2
    _emit({"proposal_id": proposal_id}, sys.stdout)
    return 0
