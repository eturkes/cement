#!/usr/bin/env python
"""Re-derive the aggregate-envelope spike observations from this tree."""

from __future__ import annotations

import argparse
import errno
import hashlib
import inspect
import json
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / ".agent/decisions/.m3u5a-envelope-probes"
LAUNCHER = "import sys; from cement_runtime.cli import main; raise SystemExit(main(sys.argv[1:]))"
FIELD_MAX_BYTES = 1_048_576
PROVENANCE_MAX_BYTES = 65_536
AGGREGATE_MAX_BYTES = 2_162_722
RAW_LAUNCHER = """\
import json
import sys
from cement_runtime.cli import _parser, _run
parser = _parser()
try:
    _run(parser.parse_args(sys.argv[1:]), parser)
except Exception as exc:
    print(json.dumps({"class": type(exc).__name__, "message": str(exc)}, sort_keys=True))
else:
    print(json.dumps({"class": None, "message": None}, sort_keys=True))
"""


def _cli(*argv: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", LAUNCHER, *argv],
        cwd=ROOT,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )


def _exception(*argv: str) -> dict[str, object] | None:
    result = subprocess.run(
        [sys.executable, "-c", RAW_LAUNCHER, *argv],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        return None
    return payload if type(payload) is dict else None


def _database(row_id: str) -> pathlib.Path:
    database = WORK / f"{row_id.lower()}.sqlite"
    result = _cli("--db", str(database.relative_to(ROOT)), "--partition", "p", "operation", "register", "op")
    if result.returncode != 0:
        raise RuntimeError(f"{row_id} setup failed: {result.stderr.strip()}")
    return database


def _max_submission() -> str:
    input_value = json.dumps("i" * (FIELD_MAX_BYTES - 2), separators=(",", ":"))
    output = json.dumps("o" * (FIELD_MAX_BYTES - 2), separators=(",", ":"))
    provenance = '{"p":"' + ("p" * (PROVENANCE_MAX_BYTES - 8)) + '"}'
    source = (
        '{"input":'
        + input_value
        + ',"output":'
        + output
        + ',"provenance":'
        + provenance
        + "}"
    )
    if (
        len(input_value.encode()) != FIELD_MAX_BYTES
        or len(output.encode()) != FIELD_MAX_BYTES
        or len(provenance.encode()) != PROVENANCE_MAX_BYTES
        or len(source.encode()) != AGGREGATE_MAX_BYTES
    ):
        raise AssertionError("bound fixture construction moved")
    return source


def _inline_submission(size: int) -> str:
    prefix = '{"input":"'
    suffix = '","output":0,"provenance":{}}'
    source = prefix + ("i" * (size - len(prefix) - len(suffix))) + suffix
    if len(source.encode()) != size:
        raise AssertionError("inline fixture construction moved")
    return source


def _leaf_parsers() -> list[tuple[tuple[str, ...], argparse.ArgumentParser]]:
    from cement_runtime.cli import _parser

    leaves: list[tuple[tuple[str, ...], argparse.ArgumentParser]] = []

    def walk(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        nested = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if not nested:
            leaves.append((path, parser))
            return
        for action in nested:
            for name, child in action.choices.items():
                walk(child, (*path, name))

    walk(_parser(), ())
    return leaves


def _dummy(action: argparse.Action) -> str:
    if action.choices:
        return str(next(iter(action.choices)))
    if action.type in (int, float):
        return "1"
    return "x"


def _leaf_argv(path: tuple[str, ...], leaf: argparse.ArgumentParser) -> list[str]:
    argv = ["--db", "unused.sqlite", "--partition", "p", *path]
    for action in leaf._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        if not action.option_strings:
            if action.nargs not in ("?", "*"):
                argv.append(_dummy(action))
        elif action.required:
            argv.append(action.option_strings[0])
            if action.nargs != 0:
                argv.append(_dummy(action))
    return argv


def _error(result: subprocess.CompletedProcess[str]) -> dict[str, object] | None:
    try:
        payload = json.loads(result.stderr)
    except ValueError:
        return None
    return payload if type(payload) is dict else None


def _proposal_counts(database: pathlib.Path) -> tuple[int, int, int]:
    with sqlite3.connect(database) as connection:
        return (
            connection.execute("SELECT count(*) FROM requests").fetchone()[0],
            connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
            connection.execute(
                "SELECT count(*) FROM events WHERE kind = 'proposal.created'"
            ).fetchone()[0],
        )


def _probe_z01() -> tuple[bool, str]:
    database = _database("Z01")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":{"x":11},"output":{"y":12},"provenance":{"model":"probe"}}',
    )
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = None
    with sqlite3.connect(database) as connection:
        counts = (
            connection.execute("SELECT count(*) FROM requests").fetchone()[0],
            connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
            connection.execute(
                "SELECT count(*) FROM events WHERE kind = 'proposal.created'"
            ).fetchone()[0],
        )
    proposal_id = payload.get("proposal_id") if type(payload) is dict else None
    passed = (
        result.returncode == 0
        and result.stderr == ""
        and type(payload) is dict
        and set(payload) == {"proposal_id"}
        and type(proposal_id) is str
        and re.fullmatch(r"prop_[0-9a-f]{32}", proposal_id) is not None
        and counts == (1, 1, 1)
    )
    detail = (
        f"rc={result.returncode} stdout_keys="
        f"{sorted(payload) if type(payload) is dict else type(payload).__name__} "
        f"rows=request:{counts[0]},proposal:{counts[1]},created-event:{counts[2]}"
    )
    return passed, detail


def _probe_z02() -> tuple[bool, str]:
    database = _database("Z02")
    argv = (
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":{"x":11},"output":{"y":12},"provenance":{"model":"probe"}}',
    )
    results = (_cli(*argv), _cli(*argv))
    payloads = []
    for result in results:
        try:
            payloads.append(json.loads(result.stdout))
        except ValueError:
            payloads.append(None)
    ids = [payload.get("proposal_id") if type(payload) is dict else None for payload in payloads]
    counts = _proposal_counts(database)
    passed = (
        all(result.returncode == 0 and result.stderr == "" for result in results)
        and all(type(identifier) is str for identifier in ids)
        and ids[0] != ids[1]
        and counts == (2, 2, 2)
    )
    return passed, f"rcs={[result.returncode for result in results]} ids_distinct={ids[0] != ids[1]} rows={counts}"


def _probe_z03() -> tuple[bool, str]:
    database = _database("Z03")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
    )
    error = _error(result)
    counts = _proposal_counts(database)
    message = "the following arguments are required: --submission"
    passed = (
        result.returncode == 2
        and result.stdout == ""
        and error == {"error": "invalid", "message": message}
        and counts == (0, 0, 0)
    )
    return passed, f"rc={result.returncode} error={error!r} rows={counts}"


def _probe_z04() -> tuple[bool, str]:
    database = _database("Z04")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        "{",
    )
    error = _error(result)
    counts = _proposal_counts(database)
    message = (
        "invalid JSON: Expecting property name enclosed in double quotes: "
        "line 1 column 2 (char 1)"
    )
    passed = (
        result.returncode == 2
        and result.stdout == ""
        and error == {"error": "invalid", "message": message}
        and counts == (0, 0, 0)
    )
    return passed, f"rc={result.returncode} error={error!r} rows={counts}"


def _probe_z05() -> tuple[bool, str]:
    database = _database("Z05")
    prefix = (
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
    )
    unknown_key = _cli(
        *prefix,
        '{"input":11,"output":12,"provenance":{},"surplus":13}',
    )
    surplus_flag = _cli(
        *prefix,
        '{"input":11,"output":12,"provenance":{}}',
        "--surplus",
    )
    key_error = _error(unknown_key)
    flag_error = _error(surplus_flag)
    counts = _proposal_counts(database)
    passed = (
        unknown_key.returncode == surplus_flag.returncode == 2
        and unknown_key.stdout == surplus_flag.stdout == ""
        and key_error
        == {"error": "invalid", "message": "submission has unknown keys: surplus"}
        and flag_error == {"error": "invalid", "message": "unrecognized arguments: --surplus"}
        and counts == (0, 0, 0)
    )
    return passed, f"key_error={key_error!r} flag_error={flag_error!r} rows={counts}"


def _probe_z06() -> tuple[bool, str]:
    database = _database("Z06")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":11,"output":12}',
    )
    with sqlite3.connect(database) as connection:
        provenance = connection.execute("SELECT provenance_json FROM proposals").fetchone()[0]
    counts = _proposal_counts(database)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = None
    passed = (
        result.returncode == 0
        and result.stderr == ""
        and type(payload) is dict
        and set(payload) == {"proposal_id"}
        and provenance == "{}"
        and counts == (1, 1, 1)
    )
    return passed, f"rc={result.returncode} stored_provenance={provenance!r} rows={counts}"


def _probe_z07() -> tuple[bool, str]:
    shapes = (("list", "[]"), ("integer", "5"), ("string", '"t"'))
    observations = []
    passed = True
    for name, shape in shapes:
        database = _database(f"Z07-{name}")
        argv = (
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            f'{{"input":11,"output":12,"provenance":{shape}}}',
        )
        result = _cli(*argv)
        error = _error(result)
        raised = _exception(*argv)
        counts = _proposal_counts(database)
        expected = {"class": "ValidationError", "message": "candidate provenance must be a mapping"}
        passed = passed and (
            result.returncode == 2
            and result.stdout == ""
            and error == {"error": "invalid", "message": expected["message"]}
            and raised == expected
            and counts == (0, 0, 0)
        )
        observations.append(f"{name}:{raised!r}/rows={counts}")
    return passed, " ".join(observations)


def _probe_z08() -> tuple[bool, str]:
    shapes = (("null", "null"), ("list", "[]"))
    observations = []
    passed = True
    for name, output in shapes:
        database = _database(f"Z08-{name}")
        result = _cli(
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            f'{{"input":11,"output":{output},"provenance":{{}}}}',
        )
        with sqlite3.connect(database) as connection:
            stored = connection.execute(
                "SELECT proposed_output_json FROM proposals"
            ).fetchone()[0]
        counts = _proposal_counts(database)
        passed = passed and (
            result.returncode == 0
            and result.stderr == ""
            and stored == output
            and counts == (1, 1, 1)
        )
        observations.append(f"{name}:rc={result.returncode}/stored={stored!r}/rows={counts}")
    return passed, " ".join(observations)


def _probe_z09() -> tuple[bool, str]:
    database = _database("Z09")
    source = '{"input":11,"output":12,"provenance":{}}\n'
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        "-",
        stdin=source,
    )
    counts = _proposal_counts(database)
    passed = (
        len(source.encode("utf-8")) == 41
        and result.returncode == 0
        and result.stderr == ""
        and counts == (1, 1, 1)
    )
    return passed, f"stdin_bytes={len(source.encode('utf-8'))} rc={result.returncode} rows={counts}"


def _probe_z10() -> tuple[bool, str]:
    database = _database("Z10")
    source = '{"input":11,"output":12,"provenance":{}}'
    submission_file = WORK / "z10.json"
    submission_file.write_text(source, encoding="utf-8")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        f"@{submission_file.relative_to(ROOT)}",
    )
    counts = _proposal_counts(database)
    passed = (
        submission_file.stat().st_size == 40
        and result.returncode == 0
        and result.stderr == ""
        and counts == (1, 1, 1)
    )
    return passed, f"file_bytes={submission_file.stat().st_size} rc={result.returncode} rows={counts}"


def _probe_z11() -> tuple[bool, str]:
    database = _database("Z11")
    submission_file = WORK / "z11-max.json"
    submission_file.write_text(_max_submission(), encoding="utf-8")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        f"@{submission_file.relative_to(ROOT)}",
    )
    counts = _proposal_counts(database)
    passed = (
        submission_file.stat().st_size == AGGREGATE_MAX_BYTES
        and result.returncode == 0
        and result.stderr == ""
        and counts == (1, 1, 1)
    )
    return passed, f"cap={submission_file.stat().st_size} rc={result.returncode} rows={counts}"


def _probe_z12() -> tuple[bool, str]:
    source = _max_submission().encode()
    max_file = WORK / "z12-max.json"
    over_file = WORK / "z12-over.json"
    max_file.write_bytes(source)
    over_file.write_bytes(source + b" ")
    results = []
    counts = []
    for name, path in (("max", max_file), ("over", over_file)):
        database = _database(f"Z12-{name}")
        result = _cli(
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            f"@{path.relative_to(ROOT)}",
        )
        results.append(result)
        counts.append(_proposal_counts(database))
    max_result, over_result = results
    over_error = _error(over_result)
    passed = (
        max_file.stat().st_size == AGGREGATE_MAX_BYTES
        and over_file.stat().st_size == AGGREGATE_MAX_BYTES + 1
        and max_result.returncode == 0
        and max_result.stderr == ""
        and counts[0] == (1, 1, 1)
        and over_result.returncode == 2
        and over_result.stdout == ""
        and over_error
        == {
            "error": "invalid",
            "message": f"submission file exceeds {AGGREGATE_MAX_BYTES} bytes",
        }
        and counts[1] == (0, 0, 0)
    )
    return passed, (
        f"sizes={max_file.stat().st_size}/{over_file.stat().st_size} "
        f"rcs={max_result.returncode}/{over_result.returncode} "
        f"over_error={over_error!r} rows={counts}"
    )


def _probe_z13() -> tuple[bool, str]:
    database = _database("Z13")
    input_value = json.dumps("i" * (FIELD_MAX_BYTES - 1), separators=(",", ":"))
    source = f'{{"input":{input_value},"output":0,"provenance":{{}}}}'
    submission_file = WORK / "z13-field-over.json"
    submission_file.write_text(source, encoding="utf-8")
    argv = (
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        f"@{submission_file.relative_to(ROOT)}",
    )
    result = _cli(*argv)
    error = _error(result)
    raised = _exception(*argv)
    counts = _proposal_counts(database)
    expected = {
        "class": "ValidationError",
        "message": f"canonical JSON exceeds {FIELD_MAX_BYTES} bytes",
    }
    passed = (
        len(input_value.encode()) == FIELD_MAX_BYTES + 1
        and submission_file.stat().st_size == 1_048_614
        and submission_file.stat().st_size < AGGREGATE_MAX_BYTES
        and result.returncode == 2
        and result.stdout == ""
        and error == {"error": "invalid", "message": expected["message"]}
        and raised == expected
        and counts == (0, 0, 0)
    )
    return passed, (
        f"frame={submission_file.stat().st_size} field={len(input_value.encode())} "
        f"aggregate_cap={AGGREGATE_MAX_BYTES} raised={raised!r} rows={counts}"
    )


def _probe_z14() -> tuple[bool, str]:
    database = _database("Z14")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "missing",
        "--submission",
        '{"input":11,"output":12,"provenance":{}}',
    )
    error = _error(result)
    counts = _proposal_counts(database)
    passed = (
        result.returncode == 3
        and result.stdout == ""
        and error
        == {"error": "not_found", "message": "operation is not registered in this partition"}
        and counts == (0, 0, 0)
    )
    return passed, f"rc={result.returncode} error={error!r} rows={counts}"


def _probe_z15() -> tuple[bool, str]:
    database = WORK / "z15-absent.sqlite"
    existed_before = database.exists()
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":11,"output":12,"provenance":{}}',
    )
    exists_after = database.exists()
    error = _error(result)
    counts = _proposal_counts(database) if exists_after else (-1, -1, -1)
    passed = (
        not existed_before
        and exists_after
        and result.returncode == 3
        and result.stdout == ""
        and error
        == {"error": "not_found", "message": "operation is not registered in this partition"}
        and counts == (0, 0, 0)
    )
    return passed, (
        f"existed_before={existed_before} rc={result.returncode} "
        f"exists_after={exists_after} error={error!r} rows={counts}"
    )


def _probe_z16() -> tuple[bool, str]:
    database = _database("Z16")
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":{"first":11},"output":{"first":12},"provenance":{}}',
        "--submission",
        '{"input":{"second":21},"output":{"second":22},"provenance":{}}',
    )
    with sqlite3.connect(database) as connection:
        stored_input = connection.execute("SELECT input_json FROM requests").fetchone()[0]
        stored_output = connection.execute(
            "SELECT proposed_output_json FROM proposals"
        ).fetchone()[0]
    counts = _proposal_counts(database)
    passed = (
        result.returncode == 0
        and result.stderr == ""
        and stored_input == '{"second":21}'
        and stored_output == '{"second":22}'
        and counts == (1, 1, 1)
    )
    return passed, (
        f"rc={result.returncode} input={stored_input!r} output={stored_output!r} rows={counts}"
    )


def _probe_z17() -> tuple[bool, str]:
    database = _database("Z17")
    database_arg = str(database.relative_to(ROOT))
    observations: dict[int, tuple[bool, object]] = {}

    def launch(size: int) -> bool:
        if size in observations:
            return observations[size][0]
        source = _inline_submission(size)
        try:
            result = _cli(
                "--db",
                database_arg,
                "--partition",
                "p",
                "proposal",
                "submit",
                "missing",
                "--submission",
                source,
            )
        except OSError as exc:
            observations[size] = (False, (exc.errno, str(exc)))
            return False
        error = _error(result)
        started = (
            result.returncode == 3
            and result.stdout == ""
            and error
            == {
                "error": "not_found",
                "message": "operation is not registered in this partition",
            }
        )
        observations[size] = (started, (result.returncode, error))
        return started

    low, high = 120_000, 140_000
    lower_started = launch(low)
    upper_started = launch(high)
    while low <= high:
        middle = (low + high) // 2
        if launch(middle):
            low = middle + 1
        else:
            high = middle - 1
    largest = high
    largest_started = launch(largest)
    next_started = launch(largest + 1)
    next_observation = observations[largest + 1][1]
    accepted_hash = hashlib.sha256(_inline_submission(largest).encode()).hexdigest()
    rejected_hash = hashlib.sha256(_inline_submission(largest + 1).encode()).hexdigest()
    counts = _proposal_counts(database)
    passed = (
        lower_started
        and not upper_started
        and largest == 131_071
        and largest_started
        and not next_started
        and type(next_observation) is tuple
        and next_observation[0] == errno.E2BIG
        and counts == (0, 0, 0)
    )
    return passed, (
        f"largest={largest} sha256={accepted_hash} next={largest + 1} "
        f"next_sha256={rejected_hash} next_observation={next_observation!r} rows={counts}"
    )


def _probe_z18() -> tuple[bool, str]:
    database = _database("Z18")
    secret = "SENSITIVE-OUTPUT-Z18"
    result = _cli(
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        f'{{"input":18,"output":"{secret}","provenance":{{}}}}',
    )
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = None
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT proposed_output_json FROM proposals"
        ).fetchone()[0]
    counts = _proposal_counts(database)
    passed = (
        result.returncode == 0
        and result.stderr == ""
        and secret not in result.stdout
        and type(payload) is dict
        and set(payload) == {"proposal_id"}
        and stored == json.dumps(secret)
        and counts == (1, 1, 1)
    )
    return passed, (
        f"rc={result.returncode} stdout_keys="
        f"{sorted(payload) if type(payload) is dict else None} echoed={secret in result.stdout} "
        f"stored={stored!r} rows={counts}"
    )


def _probe_z19() -> tuple[bool, str]:
    from cement_runtime.cli import _UsageError, _parser

    leaves = _leaf_parsers()
    submit_path = ("proposal", "submit")
    other_rejections = 0
    for path, leaf in leaves:
        if path == submit_path:
            continue
        try:
            _parser().parse_args([*_leaf_argv(path, leaf), "--submission", "{}"])
        except _UsageError:
            other_rejections += 1

    foreign: dict[str, argparse.Action] = {}
    for path, leaf in leaves:
        if path == submit_path:
            continue
        for action in leaf._actions:
            for option in action.option_strings:
                if option.startswith("--") and option != "--help":
                    foreign.setdefault(option, action)
    submit_base = [
        "--db",
        "unused.sqlite",
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":19,"output":20,"provenance":{}}',
    ]
    foreign_rejections = 0
    for option, action in foreign.items():
        argv = [*submit_base, option]
        if action.nargs != 0:
            argv.append(_dummy(action))
        try:
            _parser().parse_args(argv)
        except _UsageError:
            foreign_rejections += 1

    other_result = _cli(
        "--db",
        str((WORK / "z19-other.sqlite").relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "show",
        "prop_x",
        "--submission",
        "{}",
    )
    submit_result = _cli(
        "--db",
        str((WORK / "z19-submit.sqlite").relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":19,"output":20,"provenance":{}}',
        "--reviewer",
        "r",
    )
    passed = (
        len(leaves) == 29
        and other_rejections == 28
        and len(foreign) == 32
        and foreign_rejections == 32
        and other_result.returncode == submit_result.returncode == 2
        and _error(other_result)
        == {"error": "invalid", "message": "unrecognized arguments: --submission {}"}
        and _error(submit_result)
        == {"error": "invalid", "message": "unrecognized arguments: --reviewer r"}
        and not (WORK / "z19-other.sqlite").exists()
        and not (WORK / "z19-submit.sqlite").exists()
    )
    return passed, (
        f"leaves={len(leaves)} other_rejections={other_rejections} "
        f"foreign_flags={len(foreign)} foreign_rejections={foreign_rejections} "
        f"representative_rcs={other_result.returncode}/{submit_result.returncode}"
    )


def _probe_z20() -> tuple[bool, str]:
    submit = _cli("proposal", "submit", "--help")
    root = _cli("--help")
    expected_submit = """\
usage: cement proposal submit [-h] --submission SUBMISSION operation

positional arguments:
  operation

options:
  -h, --help            show this help message and exit
  --submission SUBMISSION
                        JSON object with input, output, and optional
                        provenance; '-' reads stdin; '@PATH' reads a file
"""
    root_line = "    proposal            submit/inspect/review supervised proposals"
    passed = (
        submit.returncode == root.returncode == 0
        and submit.stderr == root.stderr == ""
        and submit.stdout == expected_submit
        and root_line in root.stdout.splitlines()
    )
    return passed, (
        f"submit_rc={submit.returncode} submit_exact={submit.stdout == expected_submit} "
        f"root_rc={root.returncode} root_line_present={root_line in root.stdout.splitlines()}"
    )


def _probe_y01() -> tuple[bool, str]:
    import cement_runtime.cli as cli

    database = _database("Y01")
    parser = cli._parser()
    args = parser.parse_args(
        [
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            '{"input":31,"output":32,"provenance":{}}',
        ]
    )
    with (
        mock.patch.object(cli, "_source", side_effect=AssertionError("source reached")) as source,
        mock.patch.object(
            cli, "CommandCandidateSource", side_effect=AssertionError("source constructed")
        ) as constructor,
        mock.patch.object(
            cli.System, "propose", side_effect=AssertionError("System.propose reached")
        ) as propose,
    ):
        result = cli._run(args, parser)
    counts = _proposal_counts(database)
    passed = (
        type(result) is dict
        and set(result) == {"proposal_id"}
        and source.call_count == constructor.call_count == propose.call_count == 0
        and counts == (1, 1, 1)
    )
    return passed, (
        f"result_keys={sorted(result) if type(result) is dict else None} "
        f"source_calls={source.call_count}/{constructor.call_count}/{propose.call_count} "
        f"rows={counts}"
    )


def _probe_y02() -> tuple[bool, str]:
    database = _database("Y02")
    argv = (
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"operation_revision":2,"input":31,"output":32,"provenance":{}}',
    )
    result = _cli(*argv)
    error = _error(result)
    raised = _exception(*argv)
    counts = _proposal_counts(database)
    expected = {
        "class": "ValidationError",
        "message": "submission has unknown keys: operation_revision",
    }
    passed = (
        result.returncode == 2
        and result.stdout == ""
        and error == {"error": "invalid", "message": expected["message"]}
        and raised == expected
        and counts == (0, 0, 0)
    )
    return passed, f"rc={result.returncode} raised={raised!r} rows={counts}"


def _probe_y03() -> tuple[bool, str]:
    shapes = (("list", "[]"), ("integer", "5"), ("string", '"t"'), ("null", "null"))
    observations = []
    passed = True
    for name, shape in shapes:
        database = _database(f"Y03-{name}")
        argv = (
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            shape,
        )
        result = _cli(*argv)
        error = _error(result)
        raised = _exception(*argv)
        counts = _proposal_counts(database)
        expected = {
            "class": "ValidationError",
            "message": "submission must be a JSON object",
        }
        passed = passed and (
            result.returncode == 2
            and result.stdout == ""
            and error == {"error": "invalid", "message": expected["message"]}
            and raised == expected
            and counts == (0, 0, 0)
        )
        observations.append(f"{name}:{raised!r}/rows={counts}")
    return passed, " ".join(observations)


def _probe_y04() -> tuple[bool, str]:
    cases = (
        ("input", '{"output":32}', "submission is missing keys: input"),
        ("output", '{"input":31}', "submission is missing keys: output"),
        ("both", "{}", "submission is missing keys: input, output"),
    )
    observations = []
    passed = True
    for name, source, message in cases:
        database = _database(f"Y04-{name}")
        argv = (
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            source,
        )
        result = _cli(*argv)
        error = _error(result)
        raised = _exception(*argv)
        counts = _proposal_counts(database)
        expected = {"class": "ValidationError", "message": message}
        passed = passed and (
            result.returncode == 2
            and result.stdout == ""
            and error == {"error": "invalid", "message": message}
            and raised == expected
            and counts == (0, 0, 0)
        )
        observations.append(f"{name}:{raised!r}/rows={counts}")
    return passed, " ".join(observations)


def _probe_y05() -> tuple[bool, str]:
    database = _database("Y05")
    argv = (
        "--db",
        str(database.relative_to(ROOT)),
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":31,"input":32,"output":33,"provenance":{}}',
    )
    result = _cli(*argv)
    error = _error(result)
    raised = _exception(*argv)
    counts = _proposal_counts(database)
    expected = {
        "class": "ValidationError",
        "message": "duplicate JSON object key: 'input'",
    }
    passed = (
        result.returncode == 2
        and result.stdout == ""
        and error == {"error": "invalid", "message": expected["message"]}
        and raised == expected
        and counts == (0, 0, 0)
    )
    return passed, f"rc={result.returncode} raised={raised!r} rows={counts}"


def _probe_y06() -> tuple[bool, str]:
    missing_file = WORK / "y06-missing.json"
    invalid_file = WORK / "y06-invalid.json"
    invalid_file.write_bytes(b"\xff")
    cases = (
        ("empty", "@", "submission file path is empty"),
        (
            "missing",
            f"@{missing_file.relative_to(ROOT)}",
            "submission file could not be read: [Errno 2] No such file or directory: "
            f"'{missing_file.relative_to(ROOT)}'",
        ),
        (
            "invalid-utf8",
            f"@{invalid_file.relative_to(ROOT)}",
            "submission file is not valid UTF-8",
        ),
    )
    observations = []
    passed = not missing_file.exists() and invalid_file.read_bytes() == b"\xff"
    for name, channel, message in cases:
        database = _database(f"Y06-{name}")
        argv = (
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            channel,
        )
        result = _cli(*argv)
        error = _error(result)
        raised = _exception(*argv)
        counts = _proposal_counts(database)
        expected = {"class": "ValidationError", "message": message}
        passed = passed and (
            result.returncode == 2
            and result.stdout == ""
            and error == {"error": "invalid", "message": message}
            and raised == expected
            and counts == (0, 0, 0)
        )
        observations.append(f"{name}:{raised!r}/rows={counts}")
    return passed, " ".join(observations)


def _probe_y07() -> tuple[bool, str]:
    database = _database("Y07")
    database_arg = str(database.relative_to(ROOT))
    flag_prefix = _cli(
        "--db",
        database_arg,
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--sub",
        '{"input":41,"output":42,"provenance":{}}',
    )
    flag_surplus = _cli(
        "--db",
        database_arg,
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":41,"output":42,"provenance":{}}',
        "--sub",
        '{"input":51,"output":52,"provenance":{}}',
    )
    leaf_prefix = _cli(
        "--db",
        database_arg,
        "--partition",
        "p",
        "proposal",
        "sub",
        "op",
        "--submission",
        '{"input":41,"output":42,"provenance":{}}',
    )
    flag_error = _error(flag_prefix)
    surplus_error = _error(flag_surplus)
    leaf_error = _error(leaf_prefix)
    counts = _proposal_counts(database)
    passed = (
        flag_prefix.returncode == flag_surplus.returncode == leaf_prefix.returncode == 2
        and flag_prefix.stdout == flag_surplus.stdout == leaf_prefix.stdout == ""
        and flag_error
        == {"error": "invalid", "message": "the following arguments are required: --submission"}
        and surplus_error
        == {
            "error": "invalid",
            "message": "unrecognized arguments: --sub {\"input\":51,\"output\":52,\"provenance\":{}}",
        }
        and leaf_error
        == {
            "error": "invalid",
            "message": "argument proposal_command: invalid choice: 'sub' "
            "(choose from 'submit', 'show', 'list', 'review')",
        }
        and counts == (0, 0, 0)
    )
    return passed, (
        f"flag_error={flag_error!r} surplus_error={surplus_error!r} "
        f"leaf_error={leaf_error!r} rows={counts}"
    )


def _probe_y08() -> tuple[bool, str]:
    database = _database("Y08")
    database_arg = str(database.relative_to(ROOT))
    revise = _cli(
        "--db",
        database_arg,
        "--partition",
        "p",
        "operation",
        "revise",
        "op",
        "--actor",
        "revision-probe",
    )
    submit = _cli(
        "--db",
        database_arg,
        "--partition",
        "p",
        "proposal",
        "submit",
        "op",
        "--submission",
        '{"input":41,"output":42,"provenance":{}}',
    )
    try:
        revision_payload = json.loads(revise.stdout)
    except ValueError:
        revision_payload = None
    with sqlite3.connect(database) as connection:
        stored_revision = connection.execute(
            "SELECT operation_revision FROM requests"
        ).fetchone()[0]
    counts = _proposal_counts(database)
    passed = (
        revise.returncode == submit.returncode == 0
        and revise.stderr == submit.stderr == ""
        and revision_payload == {"operation": "op", "revision": 2}
        and stored_revision == 2
        and counts == (1, 1, 1)
    )
    return passed, (
        f"revise_rc={revise.returncode} submit_rc={submit.returncode} "
        f"revision_payload={revision_payload!r} stored_revision={stored_revision} rows={counts}"
    )


def _probe_y09() -> tuple[bool, str]:
    result = _cli("--help")
    stale = (
        "Supervised LLM fallback that compiles confirmed behavior into exact\n"
        "deterministic artifacts"
    )
    proposal_line = "    proposal            submit/inspect/review supervised proposals"
    passed = (
        result.returncode == 0
        and result.stderr == ""
        and stale in result.stdout
        and proposal_line in result.stdout.splitlines()
    )
    return passed, (
        f"rc={result.returncode} stale_description={stale in result.stdout} "
        f"submit_line={proposal_line in result.stdout.splitlines()}"
    )


def _probe_y10() -> tuple[bool, str]:
    import cement_runtime.cli as cli
    from cement_runtime.system import System

    candidate_source = inspect.getsource(System._canonical_candidate)
    private_literal_count = candidate_source.count("max_bytes=65_536")
    passed = (
        cli._SUBMISSION_PROVENANCE_MAX_BYTES == PROVENANCE_MAX_BYTES
        and cli._SUBMISSION_MAX_BYTES == AGGREGATE_MAX_BYTES
        and private_literal_count == 1
    )
    return passed, (
        f"cli_provenance_cap={cli._SUBMISSION_PROVENANCE_MAX_BYTES} "
        f"aggregate_cap={cli._SUBMISSION_MAX_BYTES} "
        f"system_private_literal_count={private_literal_count}"
    )


def _probe_y11() -> tuple[bool, str]:
    database = _database("Y11")
    database_arg = str(database.relative_to(ROOT))
    sources = (
        '{"provenance":{"z":44},"output":{"b":43},"input":{"a":42}}',
        '{"input":{"a":42},"output":{"b":43},"provenance":{"z":44}}',
    )
    results = [
        _cli(
            "--db",
            database_arg,
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            source,
        )
        for source in sources
    ]
    payloads = []
    for result in results:
        try:
            payloads.append(json.loads(result.stdout))
        except ValueError:
            payloads.append(None)
    with sqlite3.connect(database) as connection:
        inputs = [row[0] for row in connection.execute("SELECT input_json FROM requests ORDER BY rowid")]
        outputs = [
            row[0]
            for row in connection.execute(
                "SELECT proposed_output_json FROM proposals ORDER BY rowid"
            )
        ]
        provenance = [
            row[0]
            for row in connection.execute("SELECT provenance_json FROM proposals ORDER BY rowid")
        ]
    identifiers = [
        payload.get("proposal_id") if type(payload) is dict else None for payload in payloads
    ]
    counts = _proposal_counts(database)
    passed = (
        all(result.returncode == 0 and result.stderr == "" for result in results)
        and all(type(identifier) is str for identifier in identifiers)
        and identifiers[0] != identifiers[1]
        and inputs == ['{"a":42}', '{"a":42}']
        and outputs == ['{"b":43}', '{"b":43}']
        and provenance == ['{"z":44}', '{"z":44}']
        and counts == (2, 2, 2)
    )
    return passed, (
        f"rcs={[result.returncode for result in results]} ids_distinct={identifiers[0] != identifiers[1]} "
        f"inputs={inputs!r} outputs={outputs!r} provenance={provenance!r} rows={counts}"
    )


def _probe_y12() -> tuple[bool, str]:
    max_provenance = '{"p":"' + ("p" * (PROVENANCE_MAX_BYTES - 8)) + '"}'
    over_provenance = '{"p":"' + ("p" * (PROVENANCE_MAX_BYTES - 7)) + '"}'
    prefix = '{"input":1,"output":2,"provenance":'
    max_file = WORK / "y12-max.json"
    over_file = WORK / "y12-over.json"
    max_file.write_text(prefix + max_provenance + "}", encoding="utf-8")
    over_file.write_text(prefix + over_provenance + "}", encoding="utf-8")
    results = []
    counts = []
    raised = None
    for name, path in (("max", max_file), ("over", over_file)):
        database = _database(f"Y12-{name}")
        argv = (
            "--db",
            str(database.relative_to(ROOT)),
            "--partition",
            "p",
            "proposal",
            "submit",
            "op",
            "--submission",
            f"@{path.relative_to(ROOT)}",
        )
        result = _cli(*argv)
        results.append(result)
        counts.append(_proposal_counts(database))
        if name == "over":
            raised = _exception(*argv)
    max_result, over_result = results
    over_error = _error(over_result)
    expected = {
        "class": "ValidationError",
        "message": f"canonical JSON exceeds {PROVENANCE_MAX_BYTES} bytes",
    }
    passed = (
        len(max_provenance.encode()) == PROVENANCE_MAX_BYTES
        and len(over_provenance.encode()) == PROVENANCE_MAX_BYTES + 1
        and over_file.stat().st_size < AGGREGATE_MAX_BYTES
        and max_result.returncode == 0
        and max_result.stderr == ""
        and counts[0] == (1, 1, 1)
        and over_result.returncode == 2
        and over_result.stdout == ""
        and over_error == {"error": "invalid", "message": expected["message"]}
        and raised == expected
        and counts[1] == (0, 0, 0)
    )
    return passed, (
        f"provenance_sizes={len(max_provenance.encode())}/{len(over_provenance.encode())} "
        f"frame_sizes={max_file.stat().st_size}/{over_file.stat().st_size} "
        f"rcs={max_result.returncode}/{over_result.returncode} raised={raised!r} rows={counts}"
    )


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir()
    try:
        probes = (
            ("Z01", _probe_z01),
            ("Z02", _probe_z02),
            ("Z03", _probe_z03),
            ("Z04", _probe_z04),
            ("Z05", _probe_z05),
            ("Z06", _probe_z06),
            ("Z07", _probe_z07),
            ("Z08", _probe_z08),
            ("Z09", _probe_z09),
            ("Z10", _probe_z10),
            ("Z11", _probe_z11),
            ("Z12", _probe_z12),
            ("Z13", _probe_z13),
            ("Z14", _probe_z14),
            ("Z15", _probe_z15),
            ("Z16", _probe_z16),
            ("Z17", _probe_z17),
            ("Z18", _probe_z18),
            ("Z19", _probe_z19),
            ("Z20", _probe_z20),
            ("Y01", _probe_y01),
            ("Y02", _probe_y02),
            ("Y03", _probe_y03),
            ("Y04", _probe_y04),
            ("Y05", _probe_y05),
            ("Y06", _probe_y06),
            ("Y07", _probe_y07),
            ("Y08", _probe_y08),
            ("Y09", _probe_y09),
            ("Y10", _probe_y10),
            ("Y11", _probe_y11),
            ("Y12", _probe_y12),
        )
        failures = 0
        for row_id, probe in probes:
            passed, detail = probe()
            print(f"{row_id} {'PASS' if passed else 'FAIL'} {detail}")
            failures += not passed
        return int(failures != 0)
    finally:
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
