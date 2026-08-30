#!/usr/bin/env python
"""Re-derive M3.5a direct-flag spike observations from this tree."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from unittest import mock

from cement_runtime.cli import _UsageError, _input, _parser, _run, main
from cement_runtime.json_value import DEFAULT_MAX_BYTES
from cement_runtime.system import System


ROOT = next(
    parent for parent in pathlib.Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
)
ARTIFACT = ROOT / ".agent/decisions/m3u5a-spike-flags.json"
PARTITION = "tenant_a"
OPERATION = "echo_1"
PROVENANCE_MAX_BYTES = 65_536


class _RecordingBytes(io.BytesIO):
    def __init__(self, value: bytes) -> None:
        super().__init__(value)
        self.reads: list[dict[str, object]] = []

    def read(self, size: int = -1) -> bytes:
        value = super().read(size)
        self.reads.append(
            {"requested": size, "returned_hex": value.hex(), "returned_len": len(value)}
        )
        return value


def _invoke(
    arguments: list[str],
    *,
    stdin: str = "",
    stdin_stream: io.TextIOBase | None = None,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    source = stdin_stream if stdin_stream is not None else io.StringIO(stdin)
    with (
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
        mock.patch.object(sys, "stdin", source),
    ):
        status = main(arguments)
    return status, stdout.getvalue(), stderr.getvalue()


def _registered_ledger(directory: pathlib.Path) -> pathlib.Path:
    ledger = directory / "ledger.sqlite"
    status, stdout, stderr = _invoke(
        [
            "--db",
            str(ledger),
            "--partition",
            PARTITION,
            "operation",
            "register",
            OPERATION,
            "--actor",
            "operator-12",
        ]
    )
    if (status, stderr) != (0, ""):
        raise AssertionError((status, stdout, stderr))
    return ledger


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_string(size: int, token: str) -> str:
    value = '"' + token * (size - 2) + '"'
    if len(value.encode("utf-8")) != size:
        raise AssertionError((size, len(value.encode("utf-8"))))
    return value


def _json_object(size: int) -> str:
    value = '{"p":"' + "p" * (size - 8) + '"}'
    if len(value.encode("utf-8")) != size:
        raise AssertionError((size, len(value.encode("utf-8"))))
    return value


def _raised(arguments: list[str]) -> dict[str, str]:
    parser = _parser()
    namespace = parser.parse_args(arguments)
    try:
        _run(namespace, parser)
    except Exception as exc:  # probe records the exact leaf-raised domain class
        return {"class": type(exc).__name__, "message": str(exc)}
    raise AssertionError("probe expected the leaf to raise")


def _z01() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        status, stdout, stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--input",
                '{"case":12}',
                "--output",
                '{"answer":34}',
                "--provenance",
                '{"attempt":11,"source":"manual"}',
            ]
        )
        payload = json.loads(stdout)
        proposal_id = payload.get("proposal_id")
        if not isinstance(proposal_id, str) or re.fullmatch(r"prop_[0-9a-f]{32}", proposal_id) is None:
            raise AssertionError(payload)
        connection = sqlite3.connect(ledger)
        connection.row_factory = sqlite3.Row
        stored = connection.execute(
            """
            SELECT r.input_json, p.proposed_output_json, p.provenance_json
            FROM requests AS r JOIN proposals AS p ON p.request_id = r.id
            """
        ).fetchone()
        if stored is None:
            raise AssertionError("submission wrote no joined request/proposal row")
        observation = {
            "exit": status,
            "stderr": stderr,
            "stdout": {
                "keys": sorted(payload),
                "proposal_id": "prop_<32hex>",
                "status": payload.get("status"),
            },
            "rows": {
                "proposal.created": connection.execute(
                    "SELECT count(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0],
                "proposals": connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
                "requests": connection.execute("SELECT count(*) FROM requests").fetchone()[0],
            },
            "stored": dict(stored),
        }
        connection.close()
    return _compact(observation)


def _submit_arguments(
    ledger: pathlib.Path, *field_arguments: str, operation: str = OPERATION
) -> list[str]:
    return [
        "--db",
        str(ledger),
        "--partition",
        PARTITION,
        "proposal",
        "submit",
        operation,
        *field_arguments,
    ]


def _z02() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        arguments = _submit_arguments(
            ledger,
            "--input",
            '{"case":12}',
            "--output",
            '{"answer":34}',
            "--provenance",
            '{"attempt":11}',
        )
        observations = [_invoke(arguments), _invoke(arguments)]
        payloads = [json.loads(stdout) for _, stdout, _ in observations]
        ids = [payload["proposal_id"] for payload in payloads]
        if any(re.fullmatch(r"prop_[0-9a-f]{32}", value) is None for value in ids):
            raise AssertionError(ids)
        connection = sqlite3.connect(ledger)
        observation = {
            "distinct_ids": len(set(ids)) == 2,
            "exits": [status for status, _, _ in observations],
            "rows": {
                "proposal.created": connection.execute(
                    "SELECT count(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0],
                "proposals": connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
                "requests": connection.execute("SELECT count(*) FROM requests").fetchone()[0],
            },
            "stderrs": [stderr for _, _, stderr in observations],
            "statuses": [payload["status"] for payload in payloads],
        }
        connection.close()
    return _compact(observation)


def _z03() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        variants = {
            "both": (),
            "input": ("--output", '{"answer":34}'),
            "output": ("--input", '{"case":12}'),
        }
        observation: dict[str, object] = {}
        for name, fields in variants.items():
            status, stdout, stderr = _invoke(_submit_arguments(ledger, *fields))
            observation[name] = {
                "exit": status,
                "stderr": json.loads(stderr),
                "stdout": stdout,
            }
    return _compact(observation)


def _z04() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        variants = {
            "input": ("--input", "{", "--output", "null"),
            "output": ("--input", "null", "--output", "{"),
            "provenance": (
                "--input",
                "null",
                "--output",
                "null",
                "--provenance",
                "{",
            ),
        }
        observation: dict[str, object] = {}
        for name, fields in variants.items():
            status, stdout, stderr = _invoke(_submit_arguments(ledger, *fields))
            observation[name] = {
                "exit": status,
                "stderr": json.loads(stderr),
                "stdout": stdout,
            }
    return _compact(observation)


def _z05() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        unknown_status, unknown_stdout, unknown_stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--output",
                '{"answer":34}',
                "--surplus",
                "99",
            )
        )
        value_status, value_stdout, value_stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12,"surplus":99}',
                "--output",
                '{"answer":34}',
                "--provenance",
                '{"extra":13}',
            )
        )
        value_payload = json.loads(value_stdout)
        observation = {
            "domain_object_keys": {
                "exit": value_status,
                "proposal_id": "prop_<32hex>"
                if re.fullmatch(r"prop_[0-9a-f]{32}", value_payload["proposal_id"])
                else value_payload["proposal_id"],
                "status": value_payload["status"],
                "stderr": value_stderr,
            },
            "unknown_flag": {
                "exit": unknown_status,
                "stderr": json.loads(unknown_stderr),
                "stdout": unknown_stdout,
            },
        }
    return _compact(observation)


def _z06() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--output",
                '{"answer":34}',
            )
        )
        payload = json.loads(stdout)
        connection = sqlite3.connect(ledger)
        stored = connection.execute("SELECT provenance_json FROM proposals").fetchone()[0]
        count = connection.execute("SELECT count(*) FROM proposals").fetchone()[0]
        connection.close()
        observation = {
            "exit": status,
            "proposal_id": "prop_<32hex>"
            if re.fullmatch(r"prop_[0-9a-f]{32}", payload["proposal_id"])
            else payload["proposal_id"],
            "proposal_rows": count,
            "status": payload["status"],
            "stderr": stderr,
            "stored_provenance": stored,
        }
    return _compact(observation)


def _z07() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        variants = {"array": "[]", "integer": "5", "null": "null", "string": '"t"'}
        observation: dict[str, object] = {}
        for name, provenance in variants.items():
            arguments = _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--output",
                '{"answer":34}',
                "--provenance",
                provenance,
            )
            status, stdout, stderr = _invoke(arguments)
            observation[name] = {
                "exit": status,
                "raised": _raised(arguments),
                "stderr": json.loads(stderr),
                "stdout": stdout,
            }
        connection = sqlite3.connect(ledger)
        observation["proposal_rows"] = connection.execute(
            "SELECT count(*) FROM proposals"
        ).fetchone()[0]
        connection.close()
    return _compact(observation)


def _z08() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        observation: dict[str, object] = {}
        for name, output in (("array", "[]"), ("null", "null")):
            status, stdout, stderr = _invoke(
                _submit_arguments(
                    ledger,
                    "--input",
                    '{"case":12}',
                    "--output",
                    output,
                )
            )
            payload = json.loads(stdout)
            connection = sqlite3.connect(ledger)
            stored = connection.execute(
                "SELECT proposed_output_json FROM proposals WHERE id = ?",
                (payload["proposal_id"],),
            ).fetchone()[0]
            connection.close()
            observation[name] = {
                "exit": status,
                "proposal_id": "prop_<32hex>"
                if re.fullmatch(r"prop_[0-9a-f]{32}", payload["proposal_id"])
                else payload["proposal_id"],
                "status": payload["status"],
                "stderr": stderr,
                "stored_output": stored,
            }
    return _compact(observation)


def _binary_input(value: bytes) -> tuple[_RecordingBytes, io.TextIOWrapper]:
    binary = _RecordingBytes(value)
    return binary, io.TextIOWrapper(binary, encoding="utf-8")


def _z09() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        variants = {
            "input_only": (
                ("--input", "-", "--output", '{"answer":34}'),
                b'{"case":12}',
            ),
            "output_only": (
                ("--input", '{"case":12}', "--output", "-"),
                b'{"answer":34}',
            ),
            "provenance_only": (
                (
                    "--input",
                    '{"case":12}',
                    "--output",
                    '{"answer":34}',
                    "--provenance",
                    "-",
                ),
                b'{"attempt":11}',
            ),
        }
        observation: dict[str, object] = {}
        for name, (fields, source) in variants.items():
            binary, stream = _binary_input(source)
            status, stdout, stderr = _invoke(
                _submit_arguments(ledger, *fields), stdin_stream=stream
            )
            payload = json.loads(stdout)
            observation[name] = {
                "exit": status,
                "proposal_id": "prop_<32hex>"
                if re.fullmatch(r"prop_[0-9a-f]{32}", payload["proposal_id"])
                else payload["proposal_id"],
                "reads": binary.reads,
                "status": payload["status"],
                "stderr": stderr,
            }
            stream.detach()
        binary, stream = _binary_input(b'{"case":12}')
        fields = ("--input", "-", "--output", "-")
        status, stdout, stderr = _invoke(
            _submit_arguments(ledger, *fields), stdin_stream=stream
        )
        observation["two_dashes"] = {
            "exit": status,
            "reads": binary.reads,
            "stderr": json.loads(stderr),
            "stdout": stdout,
        }
        stream.detach()
        connection = sqlite3.connect(ledger)
        observation["proposal_rows"] = connection.execute(
            "SELECT count(*) FROM proposals"
        ).fetchone()[0]
        connection.close()
    return _compact(observation)


def _z10() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        directory = pathlib.Path(raw)
        ledger = _registered_ledger(directory)
        source_path = directory / "input.json"
        source_path.write_text('{"case":12}', encoding="utf-8")
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--input-file",
                str(source_path),
                "--output",
                '{"answer":34}',
            )
        )
        file_flag = {
            "exit": status,
            "stderr": {
                **json.loads(stderr),
                "message": json.loads(stderr)["message"].replace(str(source_path), "<path>"),
            },
            "stdout": stdout,
        }
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                f"@{source_path}",
                "--output",
                '{"answer":34}',
            )
        )
        at_path = {"exit": status, "stderr": json.loads(stderr), "stdout": stdout}
        binary, stream = _binary_input(source_path.read_bytes())
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                "-",
                "--output",
                '{"answer":34}',
            ),
            stdin_stream=stream,
        )
        redirected_payload = json.loads(stdout)
        redirected = {
            "exit": status,
            "proposal_id": "prop_<32hex>"
            if re.fullmatch(r"prop_[0-9a-f]{32}", redirected_payload["proposal_id"])
            else redirected_payload["proposal_id"],
            "reads": binary.reads,
            "stderr": stderr,
        }
        stream.detach()
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                source_path.read_text(encoding="utf-8"),
                "--output",
                '{"answer":34}',
            )
        )
        expanded_payload = json.loads(stdout)
        expanded = {
            "exit": status,
            "proposal_id": "prop_<32hex>"
            if re.fullmatch(r"prop_[0-9a-f]{32}", expanded_payload["proposal_id"])
            else expanded_payload["proposal_id"],
            "stderr": stderr,
        }
        observation = {
            "argv_expansion": expanded,
            "at_path": at_path,
            "file_flag": file_flag,
            "stdin_redirection": redirected,
        }
    return _compact(observation)


def _z11() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                _json_string(DEFAULT_MAX_BYTES, "i"),
                "--output",
                _json_string(DEFAULT_MAX_BYTES, "o"),
                "--provenance",
                _json_object(PROVENANCE_MAX_BYTES),
            )
        )
        payload = json.loads(stdout)
        connection = sqlite3.connect(ledger)
        stored = connection.execute(
            """
            SELECT length(CAST(r.input_json AS BLOB)),
                   length(CAST(p.proposed_output_json AS BLOB)),
                   length(CAST(p.provenance_json AS BLOB))
            FROM requests AS r JOIN proposals AS p ON p.request_id = r.id
            WHERE p.id = ?
            """,
            (payload["proposal_id"],),
        ).fetchone()
        connection.close()
        if stored is None:
            raise AssertionError("maximal submission was not stored")
        observation = {
            "aggregate_enforcer": None,
            "all_field_maxima": {
                "exit": status,
                "proposal_id": "prop_<32hex>"
                if re.fullmatch(r"prop_[0-9a-f]{32}", payload["proposal_id"])
                else payload["proposal_id"],
                "stderr": stderr,
                "stored_bytes": {
                    "input": stored[0],
                    "output": stored[1],
                    "provenance": stored[2],
                },
            },
            "field_caps": {
                "input": DEFAULT_MAX_BYTES,
                "output": DEFAULT_MAX_BYTES,
                "provenance": PROVENANCE_MAX_BYTES,
            },
            "max_canonical_sum": 2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES,
        }
    return _compact(observation)


def _z12() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        directory = pathlib.Path(raw)
        cases = {
            "input": {
                "accepted": _json_string(DEFAULT_MAX_BYTES, "i"),
                "column": "r.input_json",
                "rejected": _json_string(DEFAULT_MAX_BYTES + 1, "i"),
            },
            "output": {
                "accepted": _json_string(DEFAULT_MAX_BYTES, "o"),
                "column": "p.proposed_output_json",
                "rejected": _json_string(DEFAULT_MAX_BYTES + 1, "o"),
            },
            "provenance": {
                "accepted": _json_object(PROVENANCE_MAX_BYTES),
                "column": "p.provenance_json",
                "rejected": _json_object(PROVENANCE_MAX_BYTES + 1),
            },
        }
        observation: dict[str, object] = {}
        for name, case in cases.items():
            case_directory = directory / name
            case_directory.mkdir()
            ledger = _registered_ledger(case_directory)

            def arguments(value: str) -> list[str]:
                fields = {
                    "input": ("--input", value, "--output", "null"),
                    "output": ("--input", "null", "--output", value),
                    "provenance": (
                        "--input",
                        "null",
                        "--output",
                        "null",
                        "--provenance",
                        value,
                    ),
                }[name]
                return _submit_arguments(ledger, *fields)

            accepted_status, accepted_stdout, accepted_stderr = _invoke(
                arguments(str(case["accepted"]))
            )
            accepted_payload = json.loads(accepted_stdout)
            connection = sqlite3.connect(ledger)
            stored_bytes = connection.execute(
                f"""
                SELECT length(CAST({case['column']} AS BLOB))
                FROM requests AS r JOIN proposals AS p ON p.request_id = r.id
                WHERE p.id = ?
                """,
                (accepted_payload["proposal_id"],),
            ).fetchone()[0]
            rejected_arguments = arguments(str(case["rejected"]))
            rejected_status, rejected_stdout, rejected_stderr = _invoke(rejected_arguments)
            row_count = connection.execute("SELECT count(*) FROM proposals").fetchone()[0]
            connection.close()
            observation[name] = {
                "max": {
                    "exit": accepted_status,
                    "stderr": accepted_stderr,
                    "stored_bytes": stored_bytes,
                },
                "max_plus_one": {
                    "exit": rejected_status,
                    "raised": _raised(rejected_arguments),
                    "stderr": json.loads(rejected_stderr),
                    "stdout": rejected_stdout,
                },
                "proposal_rows": row_count,
            }
    return _compact(observation)


def _z13() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        between = _json_object(PROVENANCE_MAX_BYTES + 1)
        parsed = _input(between)
        parsed_bytes = len(_compact(parsed).encode("utf-8"))
        arguments = _submit_arguments(
            ledger,
            "--input",
            "null",
            "--output",
            "null",
            "--provenance",
            between,
        )
        status, stdout, stderr = _invoke(arguments)
        connection = sqlite3.connect(ledger)
        row_count = connection.execute("SELECT count(*) FROM proposals").fetchone()[0]
        connection.close()
        observation = {
            "between_bytes": parsed_bytes,
            "cli_source_cap": DEFAULT_MAX_BYTES,
            "library_provenance_cap": PROVENANCE_MAX_BYTES,
            "leaf": {
                "exit": status,
                "raised": _raised(arguments),
                "stderr": json.loads(stderr),
                "stdout": stdout,
            },
            "proposal_rows": row_count,
            "source_parser_accepted": type(parsed) is dict,
        }
    return _compact(observation)


def _z14() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        arguments = _submit_arguments(
            ledger,
            "--input",
            '{"case":12}',
            "--output",
            '{"answer":34}',
            operation="echoX1",
        )
        status, stdout, stderr = _invoke(arguments)
        connection = sqlite3.connect(ledger)
        observation = {
            "exit": status,
            "raised": _raised(arguments),
            "rows": {
                "proposal.created": connection.execute(
                    "SELECT count(*) FROM events WHERE kind = 'proposal.created'"
                ).fetchone()[0],
                "proposals": connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
                "requests": connection.execute("SELECT count(*) FROM requests").fetchone()[0],
            },
            "stderr": json.loads(stderr),
            "stdout": stdout,
        }
        connection.close()
    return _compact(observation)


def _z15() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = pathlib.Path(raw) / "absent.sqlite"
        before = ledger.exists()
        arguments = _submit_arguments(
            ledger,
            "--input",
            '{"case":12}',
            "--output",
            '{"answer":34}',
        )
        status, stdout, stderr = _invoke(arguments)
        after = ledger.exists()
        connection = sqlite3.connect(ledger)
        observation = {
            "after_exists": after,
            "before_exists": before,
            "exit": status,
            "raised": _raised(arguments),
            "rows": {
                "proposals": connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
                "requests": connection.execute("SELECT count(*) FROM requests").fetchone()[0],
            },
            "stderr": json.loads(stderr),
            "stdout": stdout,
            "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
        }
        connection.close()
    return _compact(observation)


def _z16() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        variants = {
            "input": (
                "--input",
                '{"case":12}',
                "--input",
                '{"case":13}',
                "--output",
                "null",
            ),
            "malformed_first": (
                "--input",
                "{",
                "--input",
                '{"case":14}',
                "--output",
                "null",
            ),
            "output": (
                "--input",
                "null",
                "--output",
                '{"answer":34}',
                "--output",
                '{"answer":35}',
            ),
            "provenance": (
                "--input",
                "null",
                "--output",
                "null",
                "--provenance",
                '{"attempt":11}',
                "--provenance",
                '{"attempt":12}',
            ),
        }
        observation: dict[str, object] = {}
        connection = sqlite3.connect(ledger)
        for name, fields in variants.items():
            status, stdout, stderr = _invoke(_submit_arguments(ledger, *fields))
            payload = json.loads(stdout)
            stored = connection.execute(
                """
                SELECT r.input_json, p.proposed_output_json, p.provenance_json
                FROM requests AS r JOIN proposals AS p ON p.request_id = r.id
                WHERE p.id = ?
                """,
                (payload["proposal_id"],),
            ).fetchone()
            observation[name] = {
                "exit": status,
                "stderr": stderr,
                "stored": {
                    "input": stored[0],
                    "output": stored[1],
                    "provenance": stored[2],
                },
            }
        observation["proposal_rows"] = connection.execute(
            "SELECT count(*) FROM proposals"
        ).fetchone()[0]
        connection.close()
    return _compact(observation)


def _cement_executable() -> str:
    executable = shutil.which("cement")
    if executable is not None:
        return executable
    candidate = ROOT / ".venv/bin/cement"
    if not candidate.is_file():
        raise AssertionError("cannot resolve the installed cement executable")
    return str(candidate)


def _real_launch(ledger: pathlib.Path, output: str) -> dict[str, object]:
    executable = _cement_executable()
    arguments = [
        executable,
        "--db",
        str(ledger),
        "--partition",
        PARTITION,
        "proposal",
        "submit",
        OPERATION,
        "--input",
        "null",
        "--output",
        output,
    ]
    try:
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {
            "errno": exc.errno,
            "launched": False,
            "strerror": exc.strerror,
        }
    payload = json.loads(completed.stdout) if completed.returncode == 0 else None
    return {
        "exit": completed.returncode,
        "launched": True,
        "stderr": completed.stderr,
        "stdout_keys": sorted(payload) if isinstance(payload, dict) else None,
    }


def _z17() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        accepted = 2
        rejected = DEFAULT_MAX_BYTES + 1
        while accepted + 1 < rejected:
            middle = (accepted + rejected) // 2
            result = _real_launch(ledger, _json_string(middle, "x"))
            if result.get("launched") is True and result.get("exit") == 0:
                accepted = middle
            else:
                rejected = middle
        observation = {
            "largest": {
                "argument_bytes": accepted,
                **_real_launch(ledger, _json_string(accepted, "x")),
            },
            "library_field_cap": DEFAULT_MAX_BYTES,
            "next": {
                "argument_bytes": accepted + 1,
                **_real_launch(ledger, _json_string(accepted + 1, "x")),
            },
        }
    return _compact(observation)


def _z18() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        marker = "DO_NOT_ECHO_CANDIDATE_29"
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--output",
                _compact({"secret_candidate_17": marker}),
            )
        )
        payload = json.loads(stdout)
        connection = sqlite3.connect(ledger)
        stored = connection.execute(
            "SELECT proposed_output_json FROM proposals WHERE id = ?",
            (payload["proposal_id"],),
        ).fetchone()[0]
        connection.close()
        observation = {
            "candidate_marker_echoed": marker in stdout,
            "exit": status,
            "stderr": stderr,
            "stdout_bytes": len(stdout.encode("utf-8")),
            "stdout_keys": sorted(payload),
            "stored_output": stored,
        }
    return _compact(observation)


def _action_value(action: argparse.Action) -> str:
    if action.choices:
        return str(next(iter(action.choices)))
    if action.type is int:
        return "12"
    if action.type is float:
        return "1.5"
    if action.dest in {"input", "output", "expected", "provenance"}:
        return "null"
    return "value"


def _required_arguments(parser: argparse.ArgumentParser) -> list[str]:
    arguments: list[str] = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction) or action.dest == "help":
            continue
        required = action.required if action.option_strings else action.nargs not in ("?", "*")
        if not required:
            continue
        if action.option_strings:
            arguments.append(action.option_strings[-1])
        count = 0 if action.nargs == 0 else action.nargs if isinstance(action.nargs, int) else 1
        arguments.extend(_action_value(action) for _ in range(count))
    return arguments


def _leaf_vectors(
    parser: argparse.ArgumentParser,
    *,
    arguments: tuple[str, ...] = (),
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], list[str], argparse.ArgumentParser]]:
    prefix = (*arguments, *_required_arguments(parser))
    subparsers = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if not subparsers:
        return [(path, list(prefix), parser)]
    if len(subparsers) != 1:
        raise AssertionError(f"{path}: expected one subparser action")
    result: list[tuple[tuple[str, ...], list[str], argparse.ArgumentParser]] = []
    for name, child in subparsers[0].choices.items():
        result.extend(
            _leaf_vectors(child, arguments=(*prefix, name), path=(*path, name))
        )
    return result


def _parser_nodes(parser: argparse.ArgumentParser) -> list[argparse.ArgumentParser]:
    result = [parser]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                result.extend(_parser_nodes(child))
    return result


def _z19() -> str:
    parser = _parser()
    vectors = _leaf_vectors(parser)
    submit = next(vector for vector in vectors if vector[0] == ("proposal", "submit"))
    other_accepts: list[str] = []
    other_rejections = 0
    for path, arguments, _ in vectors:
        parser.parse_args(arguments)
        if path == submit[0]:
            continue
        try:
            parser.parse_args([*arguments, "--provenance", "{}"])
        except _UsageError:
            other_rejections += 1
        else:
            other_accepts.append(" ".join(path))

    submit_options = {
        option
        for action in submit[2]._actions
        for option in action.option_strings
        if option.startswith("--")
    }
    excluded = {"--db", "--help", "--partition", *submit_options}
    foreign_actions: dict[str, argparse.Action] = {}
    for node in _parser_nodes(parser):
        for action in node._actions:
            for option in action.option_strings:
                if option.startswith("--") and option not in excluded:
                    foreign_actions.setdefault(option, action)
    accepted_foreign: dict[str, object] = {}
    rejected_foreign = 0
    for option, action in sorted(foreign_actions.items()):
        candidate = [*submit[1], option]
        if action.nargs != 0:
            candidate.append(_action_value(action))
        try:
            namespace = parser.parse_args(candidate)
        except _UsageError:
            rejected_foreign += 1
        else:
            accepted_foreign[option] = {
                "parsed_output": namespace.output,
                "proposal_command": namespace.proposal_command,
            }
    observation = {
        "foreign_options_on_submit": {
            "accepted": accepted_foreign,
            "rejected": rejected_foreign,
            "tested": len(foreign_actions),
        },
        "leaf_count": len(vectors),
        "provenance_on_other_leaves": {
            "accepted": other_accepts,
            "rejected": other_rejections,
            "tested": len(vectors) - 1,
        },
    }
    return _compact(observation)


def _y01() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        values = {
            "input": '{"input_secret_31":"INPUT_MARKER_31"}',
            "output": '{"output_secret_32":"OUTPUT_MARKER_32"}',
            "provenance": '{"provenance_secret_33":"PROVENANCE_MARKER_33"}',
        }
        lock = sqlite3.connect(ledger)
        lock.execute("BEGIN IMMEDIATE")
        process = subprocess.Popen(
            [
                _cement_executable(),
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "proposal",
                "submit",
                OPERATION,
                "--input",
                values["input"],
                "--output",
                values["output"],
                "--provenance",
                values["provenance"],
            ],
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        command_line = b""
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            command_line = pathlib.Path(f"/proc/{process.pid}/cmdline").read_bytes()
            if all(marker.encode("utf-8") in command_line for marker in values.values()):
                break
            time.sleep(0.01)
        lock.rollback()
        lock.close()
        stdout, stderr = process.communicate(timeout=15)
        payload = json.loads(stdout)
        observation = {
            "exit": process.returncode,
            "stderr": stderr,
            "stdout_keys": sorted(payload),
            "visible_in_proc_cmdline": {
                name: marker.encode("utf-8") in command_line
                for name, marker in values.items()
            },
        }
    return _compact(observation)


def _y02() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        ordered_fields = (
            "--output",
            '{"answer":34}',
            "--input",
            '{"case":12}',
        )
        with mock.patch("cement_runtime.cli._input", wraps=_input) as input_spy:
            status, stdout, stderr = _invoke(_submit_arguments(ledger, *ordered_fields))
        payload = json.loads(stdout)
        binary, stream = _binary_input(b'{"answer":35}')
        double_fields = ("--output", "-", "--input", "-")
        double_status, double_stdout, double_stderr = _invoke(
            _submit_arguments(ledger, *double_fields), stdin_stream=stream
        )
        stream.detach()
        connection = sqlite3.connect(ledger)
        row_count = connection.execute("SELECT count(*) FROM proposals").fetchone()[0]
        connection.close()
        observation = {
            "argv_field_order": ["output", "input"],
            "evaluation_sources": [call.args[0] for call in input_spy.call_args_list],
            "single_values": {
                "exit": status,
                "proposal_id": "prop_<32hex>"
                if re.fullmatch(r"prop_[0-9a-f]{32}", payload["proposal_id"])
                else payload["proposal_id"],
                "stderr": stderr,
            },
            "two_dashes": {
                "exit": double_status,
                "reads": binary.reads,
                "stderr": json.loads(double_stderr),
                "stdout": double_stdout,
            },
            "proposal_rows": row_count,
        }
    return _compact(observation)


def _y03() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        revise_status, revise_stdout, revise_stderr = _invoke(
            [
                "--db",
                str(ledger),
                "--partition",
                PARTITION,
                "operation",
                "revise",
                OPERATION,
                "--actor",
                "operator-13",
            ]
        )
        invalid_status, invalid_stdout, invalid_stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--output",
                '{"answer":34}',
                "--operation-revision",
                "1",
            )
        )
        status, stdout, stderr = _invoke(
            _submit_arguments(
                ledger,
                "--input",
                '{"case":12}',
                "--output",
                '{"answer":34}',
            )
        )
        payload = json.loads(stdout)
        connection = sqlite3.connect(ledger)
        stored_revision = connection.execute(
            """
            SELECT r.operation_revision
            FROM requests AS r JOIN proposals AS p ON p.request_id = r.id
            WHERE p.id = ?
            """,
            (payload["proposal_id"],),
        ).fetchone()[0]
        connection.close()
        observation = {
            "explicit_revision_flag": {
                "exit": invalid_status,
                "stderr": json.loads(invalid_stderr),
                "stdout": invalid_stdout,
            },
            "revision_change": {
                "exit": revise_status,
                "payload": json.loads(revise_stdout),
                "stderr": revise_stderr,
            },
            "submission": {
                "exit": status,
                "proposal_id": "prop_<32hex>"
                if re.fullmatch(r"prop_[0-9a-f]{32}", payload["proposal_id"])
                else payload["proposal_id"],
                "stderr": stderr,
                "stored_revision": stored_revision,
            },
        }
    return _compact(observation)


def _y04() -> str:
    with tempfile.TemporaryDirectory(prefix="cement-m3u5a-flags-") as raw:
        ledger = _registered_ledger(pathlib.Path(raw))
        submit_calls: list[dict[str, object]] = []
        original_submit = System.submit_proposal

        def submit_spy(
            system: System,
            partition: str,
            operation: str,
            input_value: object,
            *,
            candidate: object,
        ) -> str:
            submit_calls.append(
                {
                    "candidate_output": getattr(candidate, "output"),
                    "candidate_provenance": getattr(candidate, "provenance"),
                    "candidate_type": type(candidate).__name__,
                    "input": input_value,
                    "operation": operation,
                    "partition": partition,
                }
            )
            return original_submit(
                system,
                partition,
                operation,
                input_value,
                candidate=candidate,  # type: ignore[arg-type]
            )

        with (
            mock.patch.object(System, "submit_proposal", submit_spy),
            mock.patch.object(
                System, "propose", side_effect=AssertionError("source path reached")
            ) as propose,
            mock.patch(
                "cement_runtime.cli.CommandCandidateSource",
                side_effect=AssertionError("command source constructed"),
            ) as source_constructor,
        ):
            status, stdout, stderr = _invoke(
                _submit_arguments(
                    ledger,
                    "--input",
                    '{"case":12}',
                    "--output",
                    '{"answer":34}',
                    "--provenance",
                    '{"attempt":11}',
                )
            )
        payload = json.loads(stdout)
        observation = {
            "exit": status,
            "route_calls": {
                "CommandCandidateSource": source_constructor.call_count,
                "System.propose": propose.call_count,
                "System.submit_proposal": len(submit_calls),
            },
            "stderr": stderr,
            "submit_call": submit_calls[0],
            "stdout_keys": sorted(payload),
        }
    return _compact(observation)


def _z20() -> str:
    parser = _parser()
    root_help = parser.format_help()
    submit_parser = next(
        leaf for path, _, leaf in _leaf_vectors(parser) if path == ("proposal", "submit")
    )
    submit_help = submit_parser.format_help()
    register = {
        action.dest: action.help
        for action in submit_parser._actions
        if action.dest in {"input", "output", "provenance"}
    }
    observation = {
        "root": {
            "bytes": len(root_help.encode("utf-8")),
            "mentions_submit": "submit" in root_help,
            "proposal_line": next(
                line for line in root_help.splitlines() if line.strip().startswith("proposal ")
            ),
            "sha256": hashlib.sha256(root_help.encode("utf-8")).hexdigest(),
        },
        "submit": {
            "bytes": len(submit_help.encode("utf-8")),
            "lines": submit_help.splitlines(),
            "register": register,
        },
    }
    return _compact(observation)


CASES: dict[str, Callable[[], str]] = {
    "Y01": _y01,
    "Y02": _y02,
    "Y03": _y03,
    "Y04": _y04,
    "Z01": _z01,
    "Z02": _z02,
    "Z03": _z03,
    "Z04": _z04,
    "Z05": _z05,
    "Z06": _z06,
    "Z07": _z07,
    "Z08": _z08,
    "Z09": _z09,
    "Z10": _z10,
    "Z11": _z11,
    "Z12": _z12,
    "Z13": _z13,
    "Z14": _z14,
    "Z15": _z15,
    "Z16": _z16,
    "Z17": _z17,
    "Z18": _z18,
    "Z19": _z19,
    "Z20": _z20,
}


def run(case_ids: list[str]) -> int:
    document = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    expected = {row["id"]: row["alt"] for row in document["rows"]}
    failures = 0
    for case_id in case_ids:
        actual = CASES[case_id]()
        passed = actual == expected.get(case_id, "unknown")
        print(f"{case_id} {'PASS' if passed else 'MOVED'} {actual}")
        failures += not passed
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=sorted(CASES))
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    raise SystemExit(run(arguments.case or sorted(CASES)))
