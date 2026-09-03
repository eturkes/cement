"""M3.5b obligation battery: one test per contract obligation clause D01-D28.

Seeded by `.agent/decisions/m3u5b-battery-validate.py --emit-stub` from the obligation
paragraphs in `m3u5b-contract.md`. Each docstring carries its obligation verbatim,
followed by every section 10 correction that overrides it and every section 11 gate-2
strengthening that binds its construction. The body is the work.

A CORRECTED obligation is encoded in its CORRECTED form. Section 10 supersedes the
bullet text above it, so encoding the literal bullet is a defect that goes red against
correct code.

Compound obligations D15, D18 and D22 carry one test PER CLAUSE, per contract X39. A
clause test asserts its own clause alone; a sibling clause is another test's work.

Replace each `self.fail` marker with real assertions. A body that asserts nothing is
graded ASSERTIONLESS, and a body that skips is graded SKIPPED. Both fail the validator.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import pathlib
import re
import runpy
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from cement_runtime import cli as cement_cli
from cement_runtime.function import FunctionMatch
from cement_runtime.models import FunctionCheck, FunctionResolution, FunctionVerification
from cement_runtime.system import System


ROOT = pathlib.Path(__file__).resolve().parents[1]
REMOVED_LEAVES = frozenset({"handle", "request"})
REMOVED_FLAGS = frozenset(
    {
        "--request-id",
        "--retry-failed",
        "--source-command",
        "--source-id",
        "--source-timeout",
    }
)
SURVIVING_LEAVES = frozenset(
    {
        "artifact list",
        "artifact show",
        "artifact suspend",
        "challenge",
        "compile",
        "events",
        "example list",
        "example revoke",
        "function eval",
        "function export",
        "function inspect",
        "function promote",
        "function receipts",
        "function show",
        "function verify",
        "function verify-drafts",
        "operation list",
        "operation register",
        "operation revise",
        "promote",
        "proposal list",
        "proposal review",
        "proposal show",
        "proposal submit",
        "report list",
        "report show",
        "resolve",
        "verify",
    }
)
ROOT_COMMANDS = frozenset(
    {
        "artifact",
        "challenge",
        "compile",
        "events",
        "example",
        "function",
        "operation",
        "promote",
        "proposal",
        "report",
        "resolve",
        "verify",
    }
)


def _subparsers(parser: argparse.ArgumentParser) -> list[argparse._SubParsersAction]:
    return [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]


def _parser_census(parser: argparse.ArgumentParser) -> tuple[set[str], int]:
    leaves: set[str] = set()
    nodes = 0

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        nonlocal nodes
        nodes += 1
        children = _subparsers(node)
        if not children:
            leaves.add(" ".join(path))
            return
        for action in children:
            for name, child in action.choices.items():
                visit(child, (*path, name))

    visit(parser, ())
    return leaves, nodes


def _leaf_parsers(
    parser: argparse.ArgumentParser,
) -> dict[tuple[str, ...], argparse.ArgumentParser]:
    leaves: dict[tuple[str, ...], argparse.ArgumentParser] = {}

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        children = _subparsers(node)
        if not children:
            leaves[path] = node
            return
        for action in children:
            for name, child in action.choices.items():
                visit(child, (*path, name))

    visit(parser, ())
    return leaves


def _parser_shape(parser: argparse.ArgumentParser) -> tuple[int, str]:
    shape: list[str] = []

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        shape.append("|".join((" ".join(path), "<node>", repr(bool(node.allow_abbrev)))))
        for action in sorted(node._actions, key=lambda item: item.dest):
            if isinstance(action, argparse._SubParsersAction):
                continue
            shape.append(
                "|".join(
                    (
                        " ".join(path),
                        action.dest,
                        ",".join(sorted(action.option_strings)),
                        repr(action.default),
                        repr(bool(action.required)),
                        repr(action.nargs),
                        type(action).__name__,
                    )
                )
            )
        for subparsers in _subparsers(node):
            for name, child in sorted(subparsers.choices.items()):
                visit(child, (*path, name))

    visit(parser, ())
    payload = "\n".join(shape).encode()
    return len(shape), hashlib.sha256(payload).hexdigest()[:16]


def _root_commands(parser: argparse.ArgumentParser) -> set[str]:
    actions = _subparsers(parser)
    if len(actions) != 1:
        raise AssertionError(f"root subparser actions: {len(actions)}")
    return set(actions[0].choices)


def _action_value(action: argparse.Action) -> str:
    if action.dest in {"input", "expected", "output"}:
        return "{}"
    if action.dest == "submission":
        return '{"input":{},"output":{}}'
    if action.choices:
        return str(next(iter(action.choices)))
    if action.type is int:
        return "1"
    if action.type is float:
        return "1.0"
    return "probe"


def _required_argv(path: tuple[str, ...], parser: argparse.ArgumentParser) -> list[str]:
    argv = list(path)
    for action in parser._actions:
        if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
            continue
        if not action.option_strings:
            if action.nargs not in ("?", "*"):
                argv.append(_action_value(action))
            continue
        if action.required:
            argv.append(action.option_strings[0])
            if action.nargs != 0:
                argv.append(_action_value(action))
    return argv


def _claimed_option(parser: argparse.ArgumentParser, token: str) -> argparse.Action | None:
    matches: dict[int, argparse.Action] = {}
    for action in parser._actions:
        for option in action.option_strings:
            if option == token or (parser.allow_abbrev and option.startswith(token)):
                matches[id(action)] = action
    if len(matches) == 1:
        return next(iter(matches.values()))
    return None


def _invalid_choices(message: str) -> set[str]:
    match = re.search(r"\(choose from (.+)\)$", message)
    if match is None:
        raise AssertionError(f"invalid-choice enumeration absent: {message!r}")
    return set(re.findall(r"'([^']+)'", match.group(1)))


def _parser_nodes(
    parser: argparse.ArgumentParser,
) -> dict[tuple[str, ...], argparse.ArgumentParser]:
    nodes: dict[tuple[str, ...], argparse.ArgumentParser] = {}

    def visit(node: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        nodes[path] = node
        for subparsers in _subparsers(node):
            for name, child in subparsers.choices.items():
                visit(child, (*path, name))

    visit(parser, ())
    return nodes


def _invoke(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        status = cement_cli.main(argv)
    return status, stdout.getvalue(), stderr.getvalue()


class _DispatchReached(Exception):
    pass


class _DispatchSystem:
    def __init__(self, candidate_source: object | None) -> None:
        self.candidate_source = candidate_source

    def __getattr__(self, name: str) -> object:
        def stop(*args: object, **kwargs: object) -> None:
            raise _DispatchReached(name)

        return stop


def _constructed_candidate_sources() -> dict[str, object | None]:
    parser = cement_cli._parser()
    leaves = {
        path: leaf
        for path, leaf in _leaf_parsers(parser).items()
        if " ".join(path) in SURVIVING_LEAVES
    }
    sources: dict[str, object | None] = {}
    with tempfile.TemporaryDirectory() as temporary:
        database = pathlib.Path(temporary) / "ledger.db"
        database.touch()
        for path, leaf in leaves.items():
            name = " ".join(path)
            if name == "function eval":
                continue
            constructor_calls: list[_DispatchSystem] = []

            def construct(*args: object, **kwargs: object) -> _DispatchSystem:
                positional_source = args[1] if len(args) > 1 else None
                source = kwargs.get("candidate_source", positional_source)
                instance = _DispatchSystem(source)
                constructor_calls.append(instance)
                return instance

            namespace = parser.parse_args(
                [
                    "--db",
                    str(database),
                    "--partition",
                    "partition",
                    *_required_argv(path, leaf),
                ]
            )
            with mock.patch.object(cement_cli, "System", side_effect=construct):
                try:
                    cement_cli._run(namespace, parser)
                except _DispatchReached:
                    pass
                else:
                    raise AssertionError(f"{name}: dispatch did not reach System")
            if len(constructor_calls) != 1:
                raise AssertionError(f"{name}: System constructions={len(constructor_calls)}")
            sources[name] = constructor_calls[0].candidate_source
    return sources


def _cli_tree() -> ast.Module:
    return ast.parse((ROOT / "src/cement_runtime/cli.py").read_text())


def _git_bytes(revision: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def _module_from_git(revision: str) -> types.ModuleType:
    name = f"cement_runtime._m3u5b_cli_{revision.replace('-', '_')}"
    module = types.ModuleType(name)
    module.__file__ = f"{revision}:src/cement_runtime/cli.py"
    module.__package__ = "cement_runtime"
    sys.modules[name] = module
    source = _git_bytes(revision, "src/cement_runtime/cli.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def _leaf_fingerprints(parser: argparse.ArgumentParser) -> dict[str, tuple[object, ...]]:
    fingerprints: dict[str, tuple[object, ...]] = {}
    for path, leaf in _leaf_parsers(parser).items():
        name = " ".join(path)
        if name not in SURVIVING_LEAVES:
            continue
        actions: list[tuple[object, ...]] = []
        for action in leaf._actions:
            action_type = None
            if action.type is not None:
                action_type = (
                    getattr(action.type, "__module__", None),
                    getattr(action.type, "__qualname__", repr(action.type)),
                )
            choices = None if action.choices is None else tuple(action.choices)
            actions.append(
                (
                    action.dest,
                    tuple(action.option_strings),
                    action.default,
                    choices,
                    action_type,
                    action.help,
                )
            )
        fingerprints[name] = (
            leaf.allow_abbrev,
            leaf.format_help(),
            tuple(actions),
        )
    return fingerprints


def _invoke_module(module: types.ModuleType, argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        status = module.main(argv)
    return status, stdout.getvalue(), stderr.getvalue()


def _payload_signature(status: int, stdout: str, stderr: str) -> tuple[object, ...]:
    if bool(stdout) == bool(stderr):
        raise AssertionError(f"status {status}: expected exactly one output channel")
    channel = "stdout" if stdout else "stderr"
    payload = json.loads(stdout or stderr)
    if type(payload) is dict:
        keys = frozenset(payload)
        kind = "dict"
    elif type(payload) is list:
        kind = "list"
        key_sets = {
            frozenset(item)
            for item in payload
            if type(item) is dict
        }
        if len(key_sets) != 1 or len(key_sets) != len({frozenset(item) for item in payload}):
            raise AssertionError("list payload does not carry one stable item key set")
        keys = next(iter(key_sets))
    else:
        raise AssertionError(f"unsupported payload type: {type(payload).__name__}")
    return status, channel, kind, keys


def _preserved_leaf_observations(module: types.ModuleType) -> dict[str, tuple[object, ...]]:
    observations: dict[str, tuple[object, ...]] = {}
    with tempfile.TemporaryDirectory() as temporary:
        database = pathlib.Path(temporary) / "ledger.db"
        base = ["--db", str(database), "--partition", "partition"]

        registered = _invoke_module(
            module,
            [
                *base,
                "operation",
                "register",
                "operation",
                "--min-confirmations",
                "2",
                "--min-reviewers",
                "1",
                "--min-span-seconds",
                "0",
            ],
        )
        if registered[0] != 0:
            raise AssertionError(f"operation registration failed: {registered!r}")

        submit_argv = [
            *base,
            "proposal",
            "submit",
            "operation",
            "--submission",
            '{"input":{},"output":{}}',
        ]
        submitted = _invoke_module(module, submit_argv)
        observations["proposal submit.success"] = _payload_signature(*submitted)
        proposal_id = json.loads(submitted[1])["proposal_id"]

        cases = {
            "proposal show.success": [*base, "proposal", "show", proposal_id],
            "proposal list.success": [*base, "proposal", "list"],
            "proposal review.success": [
                *base,
                "proposal",
                "review",
                proposal_id,
                "--reviewer",
                "reviewer",
                "--decision",
                "accept",
            ],
            "resolve.miss": [*base, "resolve", "operation", "--input", "{}"],
            "proposal submit.invalid": [
                *base,
                "proposal",
                "submit",
                "operation",
                "--submission",
                "{",
            ],
            "proposal show.missing": [*base, "proposal", "show", "missing"],
            "proposal list.invalid": [*base, "proposal", "list", "--limit", "0"],
            "proposal review.missing": [
                *base,
                "proposal",
                "review",
                "missing",
                "--reviewer",
                "reviewer",
                "--decision",
                "accept",
            ],
            "resolve.invalid": [*base, "resolve", "operation", "--input", "{"],
        }
        for label, argv in cases.items():
            observations[label] = _payload_signature(*_invoke_module(module, argv))

        hit = FunctionResolution(
            verification=FunctionVerification(
                True,
                1,
                None,
                "f" * 64,
                (FunctionCheck("check", True, "passed"),),
            ),
            match=FunctionMatch(matched=True, output={}, artifact_hash="a" * 64),
        )
        fake = mock.create_autospec(System, instance=True)
        fake.resolve.return_value = hit
        with mock.patch.object(module, "System", return_value=fake):
            observations["resolve.hit"] = _payload_signature(
                *_invoke_module(
                    module,
                    [*base, "resolve", "operation", "--input", "{}"],
                )
            )
    return observations


def _function_node(relative: str, name: str) -> ast.FunctionDef:
    tree = ast.parse((ROOT / relative).read_text())
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    exact = [node for node in functions if node.name == name]
    matches = exact or [node for node in functions if node.name.startswith(name)]
    if len(matches) != 1:
        raise AssertionError(f"{relative}:{name}: matches={len(matches)}")
    return matches[0]


def _executable_tree(function: ast.FunctionDef) -> ast.Module:
    body = function.body
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body = body[1:]
    return ast.Module(body=body, type_ignores=[])


def _code_strings(function: ast.FunctionDef) -> set[str]:
    return {
        node.value
        for node in ast.walk(_executable_tree(function))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _code(function: ast.FunctionDef) -> str:
    return ast.unparse(_executable_tree(function))


def _between(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


def _fenced_blocks(markdown: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip().lower(), match.group(2))
        for match in re.finditer(
            r"^```([^\n]*)\n(.*?)^```[ \t]*$",
            markdown,
            re.MULTILINE | re.DOTALL,
        )
    ]


def _shell_commands(markdown: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for language, block in _fenced_blocks(markdown):
        if language not in {"bash", "console", "sh", "shell"}:
            continue
        pending: list[str] = []
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if line.startswith("$ "):
                line = line[2:]
            if not line or (not pending and line.startswith("#")):
                continue
            continued = line.endswith("\\")
            pending.append(line[:-1].rstrip() if continued else line)
            candidate = "\n".join(pending)
            try:
                tokens = shlex.split(candidate, comments=True, posix=True)
            except ValueError:
                continue
            if continued:
                continue
            if tokens:
                commands.append(tokens)
            pending = []
        if pending:
            raise AssertionError(f"unterminated shell command: {pending!r}")
    return commands


def _cement_argv(command: list[str]) -> list[str] | None:
    try:
        start = command.index("cement") + 1
    except ValueError:
        return None
    argv: list[str] = []
    index = start
    while index < len(command):
        token = command[index]
        if token in {"&&", "||", ";", "|"}:
            break
        if token in {"<", ">", ">>", "1>", "2>", "2>>"}:
            index += 2
            continue
        if token.startswith(("<", ">")):
            index += 1
            continue
        argv.append(token)
        index += 1
    return argv


class RemovalObligationBatteryTests(unittest.TestCase):
    """One test per M3.5b contract obligation clause, encoded in its corrected form."""

    def test_d01_m3_5b_ships_system_handle_and_system_request_status_as(self) -> None:
        """D01 obligation

        CONTRACT:
        M3.5b ships `System.handle` and `System.request_status` as public methods with NO
        operator route. This is a ruled, temporary condition of the M3 track order, not a
        defect. State it once in the contract; do not state it in shipped prose, which
        describes what exists rather than what is scheduled.
        """
        self.assertTrue(callable(getattr(System, "handle", None)))
        self.assertTrue(callable(getattr(System, "request_status", None)))
        leaves, _ = _parser_census(cement_cli._parser())
        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertTrue(REMOVED_LEAVES.isdisjoint(leaves))

    def test_d02_the_census_collides_and_the_digest_discriminates_the_p(self) -> None:
        """D02 obligation

        CONTRACT:
        — THE CENSUS COLLIDES AND THE DIGEST DISCRIMINATES. The post-M3.5b census is **28
        leaves / 35 nodes**, numerically EQUAL to the pre-M3.5a census over a DIFFERENT set:
        `c8b82cd` holds `handle` and `request` and lacks `resolve` and `proposal submit`; the
        shipped state is the exact inverse. A census pin on leaf and node COUNTS alone
        therefore cannot distinguish "M3.5a and M3.5b both landed" from "neither landed". Every
        census obligation in this unit asserts the leaf-name SET, and any count assertion
        travels with its set assertion in the same test. `parser_shape` DOES separate the two
        states — 154 / `af19339c3995c97d` against 151 / `ebd2ac811bd9776d` — which is measured
        evidence for keeping the digest beside the census rather than a claim about it. The two
        instruments are not redundant: the census names WHICH leaf moved, and the digest is the
        only one of the pair that notices the state at all.
        """
        parser = cement_cli._parser()
        leaves, nodes = _parser_census(parser)
        pre_m35a = (SURVIVING_LEAVES - {"resolve", "proposal submit"}) | REMOVED_LEAVES

        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertEqual((len(leaves), nodes), (28, 35))
        self.assertEqual((len(pre_m35a), len(SURVIVING_LEAVES)), (28, 28))
        self.assertEqual(
            pre_m35a ^ SURVIVING_LEAVES,
            {"handle", "request", "resolve", "proposal submit"},
        )
        self.assertEqual(_parser_shape(parser), (151, "ebd2ac811bd9776d"))
        self.assertNotEqual(_parser_shape(parser), (154, "af19339c3995c97d"))

    def test_d03_the_work_list_is_17_frames_never_119_tests_103_of_stag(self) -> None:
        """D03 obligation

        CONTRACT:
        The work list is **17 frames**, never 119 tests. 103 of stage 1's 113 failures stand
        behind ONE frame, `tests/test_cli.py:193 in payload`, which asserts `status == 0` for
        three fixture helpers that seed state through the `handle` CLI route: `confirm`
        (`tests/test_cli.py:217`), `handle_once` (`:247`), `confirm_text` (`:2954`). Repairing
        those three helpers to seed through `proposal submit` is expected to clear the 103; the
        remaining 16 frames are named in section 5.

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)
        """
        burden = json.loads((ROOT / ".agent/decisions/m3u5b-burden.json").read_text())
        stage_2 = next(stage for stage in burden["stages"] if stage["stage"] == 2)
        expected_frames = {
            "tests/test_cli.py:193 in payload",
            "tests/test_cli.py:4754 in options",
            "tests/test_cli.py:480 in test_usage_errors_and_oversized_stdin_are_machine_readable",
            "tests/test_cli_channels.py:1395 in test_v27_the_parser_census_moves_28_to_30_leaves_and_35_to_37_nodes",
            "tests/test_cli_channels.py:1458 in test_v28_cross_leaf_option_isolation_holds_in_both_directions_for_b",
            "tests/test_cli_channels.py:1647 in test_x04_each_completed_resolve_dispatch_calls_system_resolve_once",
            "tests/test_cli_channels.py:1989 in test_x11_the_aggregate_transport_cap_is_derived_from_one_exported_p",
            "tests/test_cli_channels.py:2605 in test_x21_both_new_parser_nodes_omit_every_source_option_as_well_as",
            "tests/test_cli_channels.py:2643 in test_x22_all_twenty_eight_baseline_leaf_paths_survive_by_identity_r",
            "tests/test_cli_channels.py:2801 in test_x26_commandcandidatesource_remains_imported_and_the_existing_h",
            "tests/test_cli_channels.py:445 in test_v05_a_configured_candidate_source_is_never_called_by_either_ne",
            "tests/test_cli_channels_battery.py:1799 in test_d16_the_aggregate_cap_is_2_default_max_bytes_provenance_max_by",
            "tests/test_cli_channels_battery.py:2608 in test_d24_zero_source_calls_zero_system_propose_calls_and_zero_sourc",
            "tests/test_cli_channels_battery.py:2733 in test_d25_the_parser_census_moves_28_30_leaves_and_35_37_nodes_deriv",
            "tests/test_cli_channels_battery.py:2861 in test_d26_preserved_and_asserted_independently_store_py_byte_identic",
            "tests/test_cli_channels_battery.py:3059 in test_d27_b02_drops_cli_py_from_its_frozen_tuple_and_keeps_command_s",
            "tests/test_cli_channels_battery.py:571 in test_d03_dispatch_calls_system_resolve_exactly_once_and_reaches_no",
        }
        self.assertEqual(stage_2["distinct_frames"], 17)
        self.assertEqual(set(stage_2["frames"]), expected_frames)
        self.assertNotIn("tests/test_cli_channels_battery.py:139 in _leaf_parser", expected_frames)

        submission_tree = ast.parse((ROOT / "tests/test_submission_battery.py").read_text())
        prose_frames = [
            node
            for node in ast.walk(submission_tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_b02_")
        ]
        self.assertEqual(len(prose_frames), 1)

    def test_d04_the_implementation_reuses_that_anchored_edit_table_rat(self) -> None:
        """D04 obligation

        CONTRACT:
        The implementation reuses that anchored edit table rather than hand-editing, so the
        deletion re-derives from committed state and a moved anchor aborts loudly.
        """
        burden_path = ROOT / ".agent/decisions/m3u5b-burden.py"
        namespace = runpy.run_path(str(burden_path))
        edits = namespace["EDITS"]
        apply_stage = namespace["apply_stage"]
        self.assertEqual([edit[0] for edit in edits], [1, 1, 2, 2, 2, 2, 2])
        self.assertEqual({edit[1] for edit in edits}, {"src/cement_runtime/cli.py"})
        self.assertEqual([edit[4] for edit in edits], [1] * 7)

        baseline = subprocess.run(
            ["git", "show", "36f7890:src/cement_runtime/cli.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        with tempfile.TemporaryDirectory() as temporary:
            tree = pathlib.Path(temporary)
            cli_path = tree / "src/cement_runtime/cli.py"
            cli_path.parent.mkdir(parents=True)
            cli_path.write_bytes(baseline)
            applied = apply_stage(tree, 2)
            self.assertEqual(len(applied), 7)
            self.assertNotEqual(cli_path.read_bytes(), baseline)
            with self.assertRaises(SystemExit) as raised:
                apply_stage(tree, 2)
            self.assertIn("ANCHOR-MISS", str(raised.exception))

    def test_d05_subcommand_names_are_exact_match_at_both_levels_a_remo(self) -> None:
        """D05 obligation

        CONTRACT:
        Subcommand names are EXACT-MATCH at both levels. A removed LEAF is therefore pinnable
        as an invalid-choice `_UsageError` whose message enumerates the survivors, which is a
        complement assertion for free. A removed FLAG on a surviving leaf reports `unrecognized
        arguments`. The two shapes are distinct and both are pinned.
        """
        parser = cement_cli._parser()
        roots = _root_commands(parser)
        self.assertEqual(roots, set(ROOT_COMMANDS))

        for token in ("handle", "request", "hand", "reque"):
            with self.subTest(token=token), self.assertRaises(cement_cli._UsageError) as raised:
                parser.parse_args([token])
            message = str(raised.exception)
            self.assertIn(f"invalid choice: {token!r}", message)
            self.assertEqual(_invalid_choices(message), roots)

        with self.assertRaises(cement_cli._UsageError) as nested:
            parser.parse_args(["proposal", "sub"])
        self.assertIn("invalid choice: 'sub'", str(nested.exception))
        self.assertEqual(
            _invalid_choices(str(nested.exception)),
            {"submit", "show", "list", "review"},
        )

        with self.assertRaises(cement_cli._UsageError) as flag_error:
            parser.parse_args(
                [
                    "challenge",
                    "operation",
                    "--input",
                    "{}",
                    "--expected",
                    "{}",
                    "--reviewer",
                    "reviewer",
                    "--request-id",
                    "probe",
                ]
            )
        self.assertEqual(
            str(flag_error.exception),
            "unrecognized arguments: --request-id probe",
        )

    def test_d06_legacy_leaves_abbreviate_act_reaches_actor_so_flag_rem(self) -> None:
        """D06 obligation

        CONTRACT:
        Legacy leaves abbreviate (`--act` reaches `--actor`), so flag removal is NOT pinnable
        as absence. Every removed flag spelling AND every proper prefix of it must be refused
        by every surviving leaf, derived over `_parser()` rather than enumerated by hand.
        """
        parser = cement_cli._parser()
        leaves = {
            path: leaf
            for path, leaf in _leaf_parsers(parser).items()
            if " ".join(path) in SURVIVING_LEAVES
        }
        self.assertEqual({" ".join(path) for path in leaves}, set(SURVIVING_LEAVES))
        self.assertEqual(len(leaves), 28)

        legacy = parser.parse_args(["compile", "operation", "--act", "actor"])
        self.assertEqual(legacy.actor, "actor")

        prefix_cases = [
            (removed, removed[:length])
            for removed in sorted(REMOVED_FLAGS)
            for length in range(3, len(removed))
        ]
        self.assertTrue(prefix_cases)
        for path, leaf in leaves.items():
            base = _required_argv(path, leaf)
            parser.parse_args(base)
            for removed, token in prefix_cases:
                with self.subTest(leaf=" ".join(path), removed=removed, token=token):
                    claimed = _claimed_option(leaf, token)
                    argv = [*base, token]
                    if claimed is None:
                        argv.append("probe")
                        with self.assertRaises(cement_cli._UsageError) as raised:
                            parser.parse_args(argv)
                        self.assertEqual(
                            str(raised.exception),
                            f"unrecognized arguments: {token} probe",
                        )
                        continue

                    value = _action_value(claimed)
                    if claimed.nargs != 0:
                        argv.append(value)
                    namespace = parser.parse_args(argv)
                    expected = claimed.const if claimed.nargs == 0 else value
                    if claimed.type is not None and claimed.nargs != 0:
                        expected = claimed.type(value)
                    self.assertEqual(getattr(namespace, claimed.dest), expected)

    def test_d07_parser_exposes_no_handle_leaf_and_no_request_leaf_ceme(self) -> None:
        """D07 obligation

        CONTRACT:
        `_parser()` exposes no `handle` leaf and no `request` leaf. `cement handle ...` and
        `cement request ...` exit 2 through the `_UsageError` channel.
        """
        parser = cement_cli._parser()
        leaves, nodes = _parser_census(parser)
        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertEqual((len(leaves), nodes), (28, 35))

        invocations = {
            "handle": ["handle", "operation", "--input", "{}"],
            "request": ["request", "request-id"],
        }
        for removed, argv in invocations.items():
            with self.subTest(removed=removed):
                status, stdout, stderr = _invoke(argv)
                payload = json.loads(stderr)
                self.assertEqual((status, stdout, payload["error"]), (2, "", "invalid"))
                self.assertIn(f"invalid choice: {removed!r}", payload["message"])
                self.assertEqual(_invalid_choices(payload["message"]), set(ROOT_COMMANDS))

    def test_d08_cli_py_defines_no_source_symbol_and_imports_no_name_fr(self) -> None:
        """D08 obligation

        CONTRACT:
        `cli.py` defines no `_source` symbol and imports no name from `.source`. Asserted over
        the shipped module's AST, not over a text grep, so a renamed helper cannot satisfy it.

        GATE-2 STRENGTHENING, binding this test's construction:
        D08/D09 need a runtime assertion, not an AST pin alone. The literal conditions are
        satisfiable
        """
        tree = _cli_tree()
        definitions = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == "_source"
            )
            or (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Store)
                and node.id == "_source"
            )
        ]
        source_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module == "source"
            and node.names
        ]
        self.assertEqual(definitions, [])
        self.assertEqual(source_imports, [])

        sources = _constructed_candidate_sources()
        self.assertEqual(set(sources), set(SURVIVING_LEAVES) - {"function eval"})
        self.assertEqual(set(sources.values()), {None})

    def test_d09_cli_py_contains_no_args_command_handle_and_no_args_com(self) -> None:
        """D09 obligation

        CONTRACT:
        `cli.py` contains no `args.command == "handle"` and no `args.command == "request"`
        dispatch branch, and constructs `System` with no `candidate_source` argument on any
        path.

        GATE-2 STRENGTHENING, binding this test's construction:
        D08/D09 need a runtime assertion, not an AST pin alone. The literal conditions are
        satisfiable
        """
        tree = _cli_tree()

        def is_args_command(node: ast.AST) -> bool:
            return (
                isinstance(node, ast.Attribute)
                and node.attr == "command"
                and isinstance(node.value, ast.Name)
                and node.value.id == "args"
            )

        dispatch_branches: list[ast.Compare] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            for index, operator in enumerate(node.ops):
                if not isinstance(operator, ast.Eq):
                    continue
                left, right = operands[index : index + 2]
                literal = right if is_args_command(left) else left if is_args_command(right) else None
                if isinstance(literal, ast.Constant) and literal.value in REMOVED_LEAVES:
                    dispatch_branches.append(node)

        system_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "System"
        ]
        candidate_keywords = [
            keyword
            for call in system_calls
            for keyword in call.keywords
            if keyword.arg == "candidate_source"
        ]
        self.assertEqual(dispatch_branches, [])
        self.assertTrue(system_calls)
        self.assertEqual(candidate_keywords, [])

        sources = _constructed_candidate_sources()
        self.assertEqual(set(sources), set(SURVIVING_LEAVES) - {"function eval"})
        self.assertEqual(set(sources.values()), {None})

    def test_d10_the_removed_flag_spellings_request_id_retry_failed_sou(self) -> None:
        """D10 obligation

        CONTRACT:
        The removed flag spellings `--request-id`, `--retry-failed`, `--source-command`,
        `--source-id`, `--source-timeout` are refused by every surviving leaf, together with
        every proper prefix of each spelling that is not a prefix of a surviving flag on that
        leaf. Derived from `_parser()` per D06.
        """
        parser = cement_cli._parser()
        leaves = {
            path: leaf
            for path, leaf in _leaf_parsers(parser).items()
            if " ".join(path) in SURVIVING_LEAVES
        }
        self.assertEqual({" ".join(path) for path in leaves}, set(SURVIVING_LEAVES))
        self.assertEqual(len(leaves), 28)

        claimed_cells: set[tuple[str, str, str, str]] = set()
        for path, leaf in leaves.items():
            name = " ".join(path)
            base = _required_argv(path, leaf)
            for removed in sorted(REMOVED_FLAGS):
                takes_value = removed != "--retry-failed"
                for length in range(3, len(removed) + 1):
                    token = removed[:length]
                    with self.subTest(leaf=name, removed=removed, token=token):
                        claimed = _claimed_option(leaf, token)
                        argv = [*base, token]
                        if claimed is None:
                            if takes_value:
                                argv.append("probe")
                            with self.assertRaises(cement_cli._UsageError) as raised:
                                parser.parse_args(argv)
                            suffix = " probe" if takes_value else ""
                            self.assertEqual(
                                str(raised.exception),
                                f"unrecognized arguments: {token}{suffix}",
                            )
                            continue

                        claimed_cells.add((name, removed, token, claimed.dest))
                        value = _action_value(claimed)
                        if claimed.nargs != 0:
                            argv.append(value)
                        namespace = parser.parse_args(argv)
                        expected = claimed.const if claimed.nargs == 0 else value
                        if claimed.type is not None and claimed.nargs != 0:
                            expected = claimed.type(value)
                        self.assertEqual(getattr(namespace, claimed.dest), expected)

        r_claims = {
            "artifact suspend": "reason",
            "challenge": "reviewer",
            "example revoke": "reason",
            "function export": "receipt_id",
            "function show": "receipt_id",
            "proposal review": "reviewer",
        }
        expected_claims = {
            (leaf, removed, token, dest)
            for leaf, dest in r_claims.items()
            for removed in ("--request-id", "--retry-failed")
            for token in ("--r", "--re")
        }
        expected_claims |= {
            (leaf, removed, "--s", dest)
            for leaf, dest in {"proposal list": "status", "promote": "scope_hash"}.items()
            for removed in ("--source-command", "--source-id", "--source-timeout")
        }
        self.assertEqual(claimed_cells, expected_claims)

    def test_d11_no_cli_help_text_at_any_parser_node_names_handle_reque(self) -> None:
        """D11 obligation

        CONTRACT:
        No CLI help text at any parser node names `handle`, `request`, a request identifier, a
        retry, or a candidate source. Walk EVERY node, root and intermediates included: an
        `add_parser(help=...)` string renders in the PARENT's listing and never in the child's
        own `format_help()`.
        """
        parser = cement_cli._parser()
        nodes = _parser_nodes(parser)
        leaves, node_count = _parser_census(parser)
        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertEqual((len(leaves), node_count, len(nodes)), (28, 35, 35))

        forbidden = (
            r"\bhandle\b",
            r"\brequest(?:[-_ ]?id(?:entifier)?)?s?\b",
            r"\bretr(?:y|ies|ied|ying)\b",
            r"\bcandidate[- ]source\b",
            r"\bsource[- ](?:command|id|timeout)\b",
        )
        for path, node in nodes.items():
            help_text = node.format_help()
            for pattern in forbidden:
                with self.subTest(path=" ".join(path) or "<root>", pattern=pattern):
                    self.assertIsNone(re.search(pattern, help_text, re.IGNORECASE))

    def test_d12_the_surviving_leaf_name_set_equals_exactly_the_28_memb(self) -> None:
        """D12 obligation

        CONTRACT:
        The surviving leaf-name SET equals exactly the 28 members of the HEAD set minus
        `handle` and `request`. Asserted as SET EQUALITY (a complement), never as a forbidden
        list, and never as a count alone (D02).
        """
        entry_leaves = SURVIVING_LEAVES | REMOVED_LEAVES
        expected = entry_leaves - REMOVED_LEAVES
        parser = cement_cli._parser()
        leaves, nodes = _parser_census(parser)

        self.assertEqual(expected, SURVIVING_LEAVES)
        self.assertEqual(leaves, set(expected))
        self.assertEqual((len(leaves), nodes), (28, 35))

    def test_d13_the_12_surviving_root_commands_are_operation_resolve_p(self) -> None:
        """D13 obligation

        CONTRACT:
        The 12 surviving root commands are `operation`, `resolve`, `proposal`, `compile`,
        `verify`, `promote`, `challenge`, `example`, `artifact`, `report`, `function`,
        `events`.
        """
        parser = cement_cli._parser()
        commands = _root_commands(parser)
        self.assertEqual(commands, set(ROOT_COMMANDS))
        self.assertEqual(len(commands), 12)

    def test_d14_every_surviving_leaf_keeps_its_options_defaults_choice(self) -> None:
        """D14 obligation

        CONTRACT:
        Every surviving leaf keeps its options, defaults, choices, types and help
        byte-identical. Carried by the re-derived `parser_shape` digest (D16), which moves on
        any such change.

        CORRECTED-BY correction 5, superseding the text above:
        WRONG AS WRITTEN: the `parser_shape` digest carries choices, types and help -- CORRECT:
        it carries **none** of the three. It digests dest, option strings, default, required,
        nargs, class and `allow_abbrev`. Two D26 help rewrites left `151`/`ebd2ac811bd9776d`
        unmoved (A07, Y07, V15, X26)

        CORRECTED-BY correction 6, superseding the text above:
        WRONG AS WRITTEN: cites D16 as the parser-shape carrier -- CORRECT: **D17** defines the
        digest re-base; D16 specifies exit classes and payload key sets (Y01)
        """
        current = _leaf_fingerprints(cement_cli._parser())
        baseline_module = _module_from_git("36f7890")
        baseline = _leaf_fingerprints(baseline_module._parser())

        shared = set(current) & set(baseline)
        equal = {name for name in shared if current[name] == baseline[name]}
        different = shared - equal
        self.assertEqual(shared, set(SURVIVING_LEAVES))
        self.assertEqual(equal, set(SURVIVING_LEAVES))
        self.assertEqual(different, set())
        self.assertEqual((len(shared), len(equal)), (28, 28))

    def test_d15a_the_six_runtime_modules_stay_byte_identical_to_their_3(self) -> None:
        """D15a obligation

        CONTRACT:
        `src/cement_runtime/system.py`, `store.py`, `models.py`, `source.py`,
        `_command_supervisor.py`, `example_adapter.py` and every file under `examples/` stay
        byte-identical to `36f7890`. Asserted against git objects, so a scope breach fails
        rather than passes silently.

        THIS CLAUSE, and no sibling clause:
        the SIX runtime modules stay byte-identical to their `36f7890` git objects, each
        asserted individually

        CORRECTED-BY scope correction (D15's scope pin is short.), superseding the text above:
        Section 9.1's six-module blob omits the examples tree and six runtime
        """
        protected = (
            "src/cement_runtime/system.py",
            "src/cement_runtime/store.py",
            "src/cement_runtime/models.py",
            "src/cement_runtime/source.py",
            "src/cement_runtime/_command_supervisor.py",
            "src/cement_runtime/example_adapter.py",
        )
        self.assertEqual(len(protected), 6)
        for relative in protected:
            with self.subTest(relative=relative):
                self.assertEqual((ROOT / relative).read_bytes(), _git_bytes("36f7890", relative))

    def test_d15b_the_twelve_examples_files_stay_byte_identical_to_their(self) -> None:
        """D15b obligation

        CONTRACT:
        `src/cement_runtime/system.py`, `store.py`, `models.py`, `source.py`,
        `_command_supervisor.py`, `example_adapter.py` and every file under `examples/` stay
        byte-identical to `36f7890`. Asserted against git objects, so a scope breach fails
        rather than passes silently.

        THIS CLAUSE, and no sibling clause:
        the TWELVE `examples/` files stay byte-identical to their `36f7890` git objects, each
        asserted individually

        CORRECTED-BY scope correction (D15's scope pin is short.), superseding the text above:
        Section 9.1's six-module blob omits the examples tree and six runtime
        """
        baseline = set(
            subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", "36f7890", "--", "examples"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )
        tracked = set(
            subprocess.run(
                ["git", "ls-files", "--", "examples"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )
        self.assertEqual(tracked, baseline)
        self.assertEqual(len(baseline), 12)
        for relative in sorted(baseline):
            with self.subTest(relative=relative):
                self.assertEqual((ROOT / relative).read_bytes(), _git_bytes("36f7890", relative))

    def test_d16_proposal_submit_proposal_show_proposal_list_proposal_r(self) -> None:
        """D16 obligation

        CONTRACT:
        `proposal submit`, `proposal show`, `proposal list`, `proposal review` and `resolve`
        keep their exit classes and payload key sets from M3.5a's contract unchanged.
        """
        baseline = _preserved_leaf_observations(_module_from_git("36f7890"))
        current = _preserved_leaf_observations(cement_cli)
        proposal_keys = frozenset(
            {
                "created_at_us",
                "final_output",
                "id",
                "input",
                "operation",
                "operation_revision",
                "proposed_output",
                "provenance",
                "review_note",
                "reviewed_at_us",
                "reviewer",
                "sequence",
                "status",
            }
        )
        resolve_keys = frozenset(
            {
                "artifact_hash",
                "checks",
                "entries",
                "function_hash",
                "matched",
                "output",
                "passed",
            }
        )
        error_keys = frozenset({"error", "message"})
        expected = {
            "proposal submit.success": (0, "stdout", "dict", frozenset({"proposal_id"})),
            "proposal show.success": (0, "stdout", "dict", proposal_keys),
            "proposal list.success": (0, "stdout", "list", proposal_keys),
            "proposal review.success": (
                0,
                "stdout",
                "dict",
                frozenset({"example_id", "output", "proposal_id", "status"}),
            ),
            "resolve.miss": (6, "stdout", "dict", resolve_keys),
            "resolve.hit": (0, "stdout", "dict", resolve_keys),
            "proposal submit.invalid": (2, "stderr", "dict", error_keys),
            "proposal show.missing": (3, "stderr", "dict", error_keys),
            "proposal list.invalid": (2, "stderr", "dict", error_keys),
            "proposal review.missing": (3, "stderr", "dict", error_keys),
            "resolve.invalid": (2, "stderr", "dict", error_keys),
        }
        self.assertEqual(set(current), set(expected))
        self.assertEqual(baseline, expected)
        self.assertEqual(current, baseline)

    def test_d17_gate_4_agent_decisions_m3u5a_s2_probe_py_five_failing(self) -> None:
        """D17 obligation

        CONTRACT:
        — gate 4 (`.agent/decisions/m3u5a-s2-probe.py`), five failing checks, measured: | check
        | want at HEAD | want after | |---|---|---| | `parser_census.leaves` | 30 | 28 | |
        `parser_census.nodes` | 37 | 35 | | `parser_shape.actions` | 163 | 151 | |
        `parser_shape.digest` | `8b58b465c08aa693` | `ebd2ac811bd9776d` | |
        `parser_census.lost_baseline_leaves` | `[]` | `['handle', 'request']` |
        `BASELINE_LEAVES` keeps `handle` and `request` as members: the frozenset records the
        `c8b82cd` baseline, which is history and does not move. The EXPECTATION moves instead,
        from "nothing is lost" to "exactly these two are lost". Gate 4 must exit 0 over all 16
        checks after the re-base.

        CORRECTED-BY correction 1, superseding the text above:
        WRONG AS WRITTEN: "all 16 checks" -- CORRECT: gate 4 grades **19** checks; the roadmap
        already recorded 19 (A09, V19)
        """
        probe_path = ROOT / ".agent/decisions/m3u5a-s2-probe.py"
        completed = subprocess.run(
            [sys.executable, str(probe_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)
        check_lines = [line for line in completed.stderr.splitlines() if line.startswith("CHECK")]
        parser = cement_cli._parser()
        leaves, nodes = _parser_census(parser)

        self.assertEqual(len(check_lines), 19)
        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertEqual(
            report["parser_census"],
            {"leaf_names": sorted(leaves), "leaves": 28, "nodes": nodes},
        )
        self.assertEqual((len(leaves), nodes), (28, 35))
        self.assertEqual(report["parser_shape"], {"actions": 151, "digest": "ebd2ac811bd9776d"})
        self.assertEqual(_parser_shape(parser), (151, "ebd2ac811bd9776d"))

        historical = (SURVIVING_LEAVES - {"proposal submit", "resolve"}) | REMOVED_LEAVES
        self.assertEqual(historical - leaves, {"handle", "request"})
        self.assertEqual(leaves - historical, {"proposal submit", "resolve"})
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS    19 pinned facts hold", completed.stderr)

    def test_d18a_test_cli_py_193_in_payload_via_confirm_handle_once_con(self) -> None:
        """D18a obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli.py:193 in payload` via `confirm`/`handle_once`/`confirm_text` -- preserve:
        fixtures seed through `proposal submit`; the 103 assertions they shield stay unchanged

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        helpers = {
            name: _function_node("tests/test_cli.py", name)
            for name in ("confirm", "handle_once", "confirm_text")
        }
        submit = _function_node("tests/test_cli.py", "submit")
        submission = _function_node("tests/test_cli.py", "submission")

        submit_calls = 0
        for name, helper in helpers.items():
            strings = _code_strings(helper)
            calls = [
                node
                for node in ast.walk(_executable_tree(helper))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
                and node.func.attr == "submit"
            ]
            with self.subTest(helper=name):
                self.assertEqual(len(calls), 1)
                self.assertTrue(
                    {"handle", "--request-id", "--source-command"}.isdisjoint(strings)
                )
            submit_calls += len(calls)
        self.assertEqual(submit_calls, 3)
        self.assertTrue({"proposal", "submit", "--submission"}.issubset(_code_strings(submit)))
        self.assertTrue({"input", "output"}.issubset(_code_strings(submission)))
        acknowledgement_sets = {
            frozenset(element.value for element in node.elts)
            for node in ast.walk(_executable_tree(submit))
            if isinstance(node, ast.Set)
            and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)
        }
        self.assertIn(frozenset({"proposal_id"}), acknowledgement_sets)

    def test_d18b_test_cli_py_480_test_usage_errors_and_oversized_stdin(self) -> None:
        """D18b obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli.py:480 test_usage_errors_and_oversized_stdin_are_machine_readable` --
        preserve: usage errors stay machine-readable

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node(
            "tests/test_cli.py",
            "test_usage_errors_and_oversized_stdin_are_machine_readable",
        )
        strings = _code_strings(target)
        code = _code(target)
        register_calls = [
            node
            for node in ast.walk(_executable_tree(target))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
        ]

        self.assertTrue({"resolve", "--input", "-", "invalid", "stdin exceeds"}.issubset(strings))
        self.assertNotIn("handle", strings)
        self.assertEqual(len(register_calls), 1)
        self.assertEqual(ast.literal_eval(register_calls[0].args[0]), "echo")
        self.assertIn("run.status", code)
        self.assertIn("run.stdout", code)
        self.assertIn("stderr", code)

    def test_d18c_test_cli_py_4754_in_options_preserve_leaf_option_censu(self) -> None:
        """D18c obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli.py:4754 in options` -- preserve: leaf-option census

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node(
            "tests/test_cli.py",
            "test_function_eval_help_reuses_the_shipped_flag_register",
        )
        tree = _executable_tree(target)
        option_paths = {
            tuple(ast.literal_eval(argument) for argument in node.args)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "options"
            and all(isinstance(argument, ast.Constant) for argument in node.args)
        }
        strings = _code_strings(target)
        code = _code(target)

        self.assertEqual(option_paths, {("function", "eval"), ("resolve",)})
        self.assertNotIn(("handle",), option_paths)
        self.assertTrue(
            {"bundle", "input", "expected_function_hash", "help"}.issubset(strings)
        )
        self.assertIn("actions['bundle'].required", code)
        self.assertIn("actions['input'].required", code)
        self.assertIn("actions['expected_function_hash'].required", code)
        self.assertIn("options('resolve')['input'].help", code)

    def test_d18d_test_cli_channels_py_1395_v27_preserve_census_re_based(self) -> None:
        """D18d obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:1395 v27` -- preserve: census, re-based per D02 to a SET
        assertion

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_v27_")
        tree = _executable_tree(target)
        code = _code(target)
        string_sets = {
            frozenset(element.value for element in node.elts)
            for node in ast.walk(tree)
            if isinstance(node, ast.Set)
            and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)
        }
        count_pairs = [
            tuple(element.value for element in node.elts)
            for node in ast.walk(tree)
            if isinstance(node, ast.Tuple)
            and len(node.elts) == 2
            and all(isinstance(element, ast.Constant) and isinstance(element.value, int) for element in node.elts)
        ]

        self.assertIn(frozenset({"handle", "request"}), string_sets)
        self.assertIn(frozenset({"proposal submit", "resolve"}), string_sets)
        self.assertGreaterEqual(count_pairs.count((28, 35)), 2)
        self.assertNotIn((30, 37), count_pairs)
        self.assertIn("baseline_paths - current_paths", code)
        self.assertIn("current_paths - baseline_paths", code)

    def test_d18e_test_cli_channels_py_1458_v28_preserve_cross_leaf_opti(self) -> None:
        """D18e obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:1458 v28` -- preserve: cross-leaf option isolation

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_v28_")
        strings = _code_strings(target)
        code = _code(target)

        self.assertIn("self.assertEqual(len(leaves), 28)", code)
        self.assertNotIn("self.assertEqual(len(leaves), 30)", code)
        self.assertTrue(
            {
                "--submission",
                "--expected-function-hash",
                "unrecognized arguments: --submission ",
                "unrecognized arguments: --expected-function-hash ",
            }.issubset(strings)
        )
        self.assertIn("submission_owners, {('proposal', 'submit')}", code)
        self.assertIn("self.assertEqual(len(hash_owners), 4)", code)
        self.assertIn("self.assertIn(('resolve',), hash_owners)", code)
        self.assertIn("self.assertNotIn(('proposal', 'submit'), hash_owners)", code)

    def test_d18f_test_cli_channels_py_1647_x04_preserve_resolve_dispatc(self) -> None:
        """D18f obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:1647 x04` -- preserve: `resolve` dispatch calls `System.resolve`
        once

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_x04_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        counter_key_sets = {
            frozenset(key.value for key in node.keys if isinstance(key, ast.Constant))
            for node in ast.walk(tree)
            if isinstance(node, ast.Dict)
            and all(isinstance(key, ast.Constant) and isinstance(key.value, str) for key in node.keys)
        }
        # D19 INVERTS this frame: it names `_source` in order to DENY it, so a
        # token-absence check cannot separate an assertion that USES the symbol from
        # one that FORBIDS it. Assert the RUNTIME absence the frame actually proves.
        expected_counters = frozenset(
            {"System.resolve", "System.propose", "System.verify_function", "_source"}
        )

        self.assertIn(expected_counters, counter_key_sets)
        self.assertIn("_source", strings)
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", code)
        self.assertIn("self.assertEqual(run.status, 6)", code)
        self.assertIn("system.resolve.call_count", code)
        self.assertIn("system.propose.call_count", code)
        self.assertIn("system.verify_function.call_count", code)
        self.assertIn(
            "mock.call(PARTITION, OPERATION, 0, expected_function_hash=None)",
            code,
        )

    def test_d18g_test_cli_channels_py_1989_x11_preserve_aggregate_trans(self) -> None:
        """D18g obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:1989 x11` -- preserve: aggregate transport cap derived from one
        exported constant

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_x11_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        integers = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and type(node.value) is int
        }

        self.assertTrue({65_536, 34, 2_162_722}.issubset(integers))
        self.assertTrue(
            {"DEFAULT_MAX_BYTES", "PROVENANCE_MAX_BYTES", "_SUBMISSION_FRAMING"}.issubset(strings)
        )
        self.assertIn("self.assertEqual(len(cli_literals), 0)", code)
        self.assertIn("node.name == '_source'", code)
        self.assertIn("self.assertEqual(len(source_helpers), 0)", code)
        self.assertIn("self.assertEqual(system_uses, 3)", code)
        self.assertNotIn("next((node for node in ast.walk(cli_tree)", code)

    def test_d18h_test_cli_channels_py_2605_x21_preserve_both_new_leaves(self) -> None:
        """D18h obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:2605 x21` -- preserve: both new leaves omit every source option

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_x21_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        counter_key_sets = {
            frozenset(key.value for key in node.keys if isinstance(key, ast.Constant))
            for node in ast.walk(tree)
            if isinstance(node, ast.Dict)
            and all(isinstance(key, ast.Constant) and isinstance(key.value, str) for key in node.keys)
        }

        self.assertTrue(
            {"source_command", "source_id", "source_timeout"}.issubset(strings)
        )
        # D19 INVERTS this frame: `_source` is named only to be denied.
        self.assertIn("_source", strings)
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", code)
        self.assertIn("_parser_nodes(cement_cli._parser())", code)
        self.assertIn("self.assertEqual(len(leaves), 28)", code)
        self.assertIn("self.assertEqual(source_option_owners, set())", code)
        self.assertIn(
            frozenset({"System.propose", "source.propose"}),
            counter_key_sets,
        )
        self.assertIn("self.assertIn(resolved.status, (0, 6))", code)
        self.assertIn("self.assertEqual(submitted.status, 0)", code)

    def test_d18i_test_cli_channels_py_2643_x22_preserve_the_28_baseline(self) -> None:
        """D18i obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:2643 x22` -- preserve: the 28 baseline leaf paths — re-based to
        the surviving set

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_x22_")
        tree = _executable_tree(target)
        code = _code(target)
        string_sets = {
            frozenset(element.value for element in node.elts)
            for node in ast.walk(tree)
            if isinstance(node, ast.Set)
            and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)
        }
        integers = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and type(node.value) is int
        ]

        self.assertIn(frozenset({"handle", "request"}), string_sets)
        self.assertIn(frozenset({"proposal submit", "resolve"}), string_sets)
        self.assertIn(26, integers)
        self.assertGreaterEqual(integers.count(28), 2)
        self.assertNotIn(30, integers)
        self.assertIn("baseline_paths - current_paths", code)
        self.assertIn("current_paths - baseline_paths", code)
        self.assertIn("baseline_paths & current_paths", code)

    def test_d18j_test_cli_channels_py_2801_2811_x26_preserve_inverted_c(self) -> None:
        """D18j obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:2801/2811 x26` -- preserve: **inverted**:
        `CommandCandidateSource` is no longer imported

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_x26_")
        tree = _executable_tree(target)
        code = _code(target)
        zero_assertions = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assertEqual"
            and any(
                (isinstance(argument, ast.Constant) and argument.value == 0)
                or (isinstance(argument, ast.List) and not argument.elts)
                for argument in node.args
            )
        ]

        self.assertIn("ast.ImportFrom", code)
        self.assertIn("CommandCandidateSource", _code_strings(target))
        self.assertTrue(any("imports" in assertion for assertion in zero_assertions))
        self.assertTrue(
            any("helper" in assertion or "_source" in assertion for assertion in zero_assertions)
        )
        self.assertFalse(any("assertGreaterEqual" in assertion for assertion in zero_assertions))
        self.assertNotIn("self.assertEqual(len(imports), 1)", code)

    def test_d18k_test_cli_channels_py_445_v05_preserve_a_configured_can(self) -> None:
        """D18k obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels.py:445 v05` -- preserve: a configured candidate source is never
        called

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels.py", "test_v05_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        counter_key_sets = {
            frozenset(key.value for key in node.keys if isinstance(key, ast.Constant))
            for node in ast.walk(tree)
            if isinstance(node, ast.Dict)
            and all(isinstance(key, ast.Constant) and isinstance(key.value, str) for key in node.keys)
        }
        # D19 INVERTS this frame: `_source` stays a counter KEY bound to a denial.
        expected = frozenset(
            {
                "System.propose",
                "CandidateSource.propose",
                "System.resolve",
                "System.submit_proposal",
                "_source",
            }
        )

        self.assertIn(expected, counter_key_sets)
        self.assertIn("_source", strings)
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", code)
        self.assertIn("System(self.database, candidate_source=source)", code)
        self.assertIn("self.assertIn(resolved.status, (0, 6))", code)
        self.assertIn("self.assertEqual(submitted.status, 0)", code)
        self.assertIn("resolve.call_count", code)
        self.assertIn("submit.call_count", code)

    def test_d18l_test_cli_channels_battery_py_139_leaf_parser_preserve(self) -> None:
        """D18l obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:139 _leaf_parser` -- preserve: battery leaf-parser helper

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        helper = _function_node("tests/test_cli_channels_battery.py", "_leaf_parser")
        target = _function_node("tests/test_cli_channels_battery.py", "test_d26_")
        calls = [
            node
            for node in ast.walk(_executable_tree(target))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_leaf_parser"
        ]
        paths = [ast.literal_eval(call.args[2]) for call in calls]

        self.assertIn("case.assertIn", _code(helper))
        self.assertEqual(len(calls), 2)
        self.assertEqual(set(paths), {("resolve",), ("proposal", "submit")})
        self.assertNotIn(("handle",), paths)

    def test_d18m_test_cli_channels_battery_py_571_d03_preserve_dispatch(self) -> None:
        """D18m obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:571 d03` -- preserve: dispatch reaches no source

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d03_")
        strings = _code_strings(target)
        code = _code(target)

        # D19 INVERTS this frame: `_source` is named only to be denied.
        self.assertIn("_source", strings)
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", code)
        self.assertNotIn("source_builder", code)
        self.assertIn("constructor.call_args.args, (str(path),)", code)
        self.assertIn("constructor.call_args.kwargs, {}", code)
        self.assertIn("fake.resolve.assert_called_once_with", code)
        self.assertIn("fake.verify_function.assert_not_called()", code)
        self.assertIn("fake.propose.assert_not_called()", code)
        self.assertIn("self.assertEqual(_payload(stdout)['output'], {'answer': 12})", code)
        self.assertIn("candidate source reached", strings)

    def test_d18n_test_cli_channels_battery_py_1799_d16_preserve_aggrega(self) -> None:
        """D18n obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:1799 d16` -- preserve: aggregate cap derivation

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d16_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        assertions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assertEqual"
            and len(node.args) >= 2
        ]
        cli_literal_zero = [
            node
            for node in assertions
            if isinstance(node.args[1], ast.Constant)
            and node.args[1].value == 0
            and "cli_tree" in ast.unparse(node.args[0])
            and "65536" in ast.unparse(node.args[0])
        ]
        system_literal_one = [
            node
            for node in assertions
            if isinstance(node.args[1], ast.Constant)
            and node.args[1].value == 1
            and "system_tree" in ast.unparse(node.args[0])
            and "65536" in ast.unparse(node.args[0])
        ]

        self.assertEqual(len(cli_literal_zero), 1)
        self.assertEqual(len(system_literal_one), 1)
        self.assertTrue(
            {"DEFAULT_MAX_BYTES", "PROVENANCE_MAX_BYTES", "_SUBMISSION_FRAMING"}.issubset(strings)
        )
        self.assertIn("self.assertEqual(framing, 34)", code)
        self.assertIn("self.assertEqual(cap, 2162722)", code)
        self.assertIn("node.id == 'PROVENANCE_MAX_BYTES'", code)
        self.assertIn(
            "{'DEFAULT_MAX_BYTES', 'PROVENANCE_MAX_BYTES', '_SUBMISSION_FRAMING'}",
            code,
        )

    def test_d18o_test_cli_channels_battery_py_2608_2667_d24_preserve_re(self) -> None:
        """D18o obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:2608/2667 d24` -- preserve: **re-shaped**: the `_source`
        spy targets a deleted symbol

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d24_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        patch_targets = [
            ast.literal_eval(node.args[1])
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "object"
            and len(node.args) > 1
            and isinstance(node.args[1], ast.Constant)
        ]

        self.assertNotIn("_source", patch_targets)
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", code)
        self.assertNotIn("self.run_cli('handle'", code)
        self.assertIn("system.handle", code)
        self.assertTrue({"fallback_failed", "candidate_source_error"}.issubset(strings))
        self.assertIn("constructor.call_count, 2", code)
        self.assertIn("resolve.call_count, 1", code)
        self.assertIn("submit.call_count, 1", code)
        self.assertIn("propose.assert_not_called()", code)
        self.assertTrue({"events", "proposals", "requests"}.issubset(strings))

    def test_d18p_test_cli_channels_battery_py_2733_d25_preserve_census(self) -> None:
        """D18p obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:2733 d25` -- preserve: census, re-based per D02

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d25_")
        tree = _executable_tree(target)
        code = _code(target)
        string_sets = {
            frozenset(element.value for element in node.elts)
            for node in ast.walk(tree)
            if isinstance(node, ast.Set)
            and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)
        }
        count_pairs = [
            tuple(element.value for element in node.elts)
            for node in ast.walk(tree)
            if isinstance(node, ast.Tuple)
            and len(node.elts) == 2
            and all(isinstance(element, ast.Constant) and isinstance(element.value, int) for element in node.elts)
        ]

        self.assertIn(frozenset({"handle", "request"}), string_sets)
        self.assertIn(frozenset({"proposal submit", "resolve"}), string_sets)
        self.assertGreaterEqual(count_pairs.count((28, 35)), 2)
        self.assertNotIn((30, 37), count_pairs)
        self.assertIn("base_leaves & current_leaves", code)
        self.assertIn("abbreviation_map", code)
        self.assertIn("base_abbreviation", code)
        self.assertIn("current_abbreviation", code)
        self.assertIn("parsed_root.partition", code)
        self.assertIn("parsed_nested.bundle", code)

    def test_d18q_test_cli_channels_battery_py_2861_d26_preserve_preserv(self) -> None:
        """D18q obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:2861 d26` -- preserve: preserved-neighbour assertions

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d26_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        zero_assertions = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assertEqual"
            and any(
                (isinstance(argument, ast.Constant) and argument.value == 0)
                or (isinstance(argument, ast.List) and not argument.elts)
                for argument in node.args
            )
        ]
        leaf_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_leaf_parser"
        ]
        leaf_paths = {ast.literal_eval(call.args[2]) for call in leaf_calls}

        self.assertIn("SCHEMA_VERSION", code)
        self.assertTrue({"events", "proposals", "requests"}.issubset(strings))
        self.assertTrue(any("imports" in assertion for assertion in zero_assertions))
        self.assertTrue(
            any("source_function" in assertion or "helpers" in assertion for assertion in zero_assertions)
        )
        self.assertEqual(leaf_paths, {("resolve",), ("proposal", "submit")})
        self.assertIn("cement_cli._UsageError", code)
        self.assertIn("handle", strings)
        self.assertTrue({"--submission", "--expected-function-hash"}.issubset(strings))
        self.assertGreaterEqual(code.count("self.assertEqual((status, stdout), (2, ''))"), 2)

    def test_d18r_test_cli_channels_battery_py_3059_d27_preserve_b02_fro(self) -> None:
        """D18r obligation

        CONTRACT:
        The eleven remaining stage-1 and stage-2 frames, each re-based in place with its
        property preserved: | frame | property to preserve | |---|---| | `test_cli.py:193 in
        payload` via `confirm`/`handle_once`/`confirm_text` | fixtures seed through `proposal
        submit`; the 103 assertions they shield stay unchanged | | `test_cli.py:480
        test_usage_errors_and_oversized_stdin_are_machine_readable` | usage errors stay
        machine-readable | | `test_cli.py:4754 in options` | leaf-option census | |
        `test_cli_channels.py:1395 v27` | census, re-based per D02 to a SET assertion | |
        `test_cli_channels.py:1458 v28` | cross-leaf option isolation | |
        `test_cli_channels.py:1647 x04` | `resolve` dispatch calls `System.resolve` once | |
        `test_cli_channels.py:1989 x11` | aggregate transport cap derived from one exported
        constant | | `test_cli_channels.py:2605 x21` | both new leaves omit every source option
        | | `test_cli_channels.py:2643 x22` | the 28 baseline leaf paths — re-based to the
        surviving set | | `test_cli_channels.py:2801/2811 x26` | **inverted**:
        `CommandCandidateSource` is no longer imported | | `test_cli_channels.py:445 v05` | a
        configured candidate source is never called | | `test_cli_channels_battery.py:139
        _leaf_parser` | battery leaf-parser helper | | `test_cli_channels_battery.py:571 d03` |
        dispatch reaches no source | | `test_cli_channels_battery.py:1799 d16` | aggregate cap
        derivation | | `test_cli_channels_battery.py:2608/2667 d24` | **re-shaped**: the
        `_source` spy targets a deleted symbol | | `test_cli_channels_battery.py:2733 d25` |
        census, re-based per D02 | | `test_cli_channels_battery.py:2861 d26` |
        preserved-neighbour assertions | | `test_cli_channels_battery.py:3059 d27` | B02 frozen
        tuple |

        THIS CLAUSE, and no sibling clause:
        `test_cli_channels_battery.py:3059 d27` -- preserve: B02 frozen tuple

        CORRECTED-BY correction 2, superseding the text above:
        WRONG AS WRITTEN: three cardinalities for one work list: prose 11, table 18 rows,
        measurement 17 -- CORRECT: **17** code-coupled frames, plus **1** prose-coupled frame
        the census never scanned; the surplus table row `test_cli_channels_battery.py:139
        _leaf_parser` is not a distinct frame (A18, X02)

        CORRECTED-BY correction 3, superseding the text above:
        WRONG AS WRITTEN: "103 shielded assertions" -- CORRECT: `test_cli` showed **105**
        failures; the three re-based helpers cleared **102**; **3** were re-based in place
        (A10)
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d27_")
        tree = _executable_tree(target)
        strings = _code_strings(target)
        code = _code(target)
        path_tuples = [
            ast.literal_eval(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Tuple)
            and node.elts
            and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)
            and all(str(element.value).startswith("src/cement_runtime/") for element in node.elts)
        ]
        expected_paths = (
            "src/cement_runtime/_command_supervisor.py",
            "src/cement_runtime/example_adapter.py",
        )

        self.assertIn(expected_paths, path_tuples)
        self.assertNotIn("src/cement_runtime/cli.py", expected_paths)
        self.assertTrue({"D24", "D25", "D26"}.issubset(strings))
        self.assertTrue(any(value.startswith("f9b9755") for value in strings))
        self.assertIn("self.assertNotIn('strictly stronger', docstring.lower())", code)
        self.assertIn("parser_shape", code)
        self.assertIn("self.assertNotEqual(mutated, before)", code)

    def test_d19_x26_and_d24_invert_rather_than_move_x26_asserts_comman(self) -> None:
        """D19 obligation

        CONTRACT:
        `x26` and `d24` INVERT rather than move. `x26` asserts `CommandCandidateSource` remains
        imported; `d24` spies on `cli._source`, which ceases to exist, so `mock.patch.object`
        raises rather than fails. A pin left asserting the pre-removal property tests nothing
        after the removal, and a spy on a deleted symbol is an error rather than a verdict.
        Both are rewritten to assert the post-removal property directly.
        """
        x26 = _function_node("tests/test_cli_channels.py", "test_x26_")
        d24 = _function_node("tests/test_cli_channels_battery.py", "test_d24_")
        x26_tree = _executable_tree(x26)
        x26_code = _code(x26)
        d24_tree = _executable_tree(d24)
        d24_code = _code(d24)

        x26_zero_assertions = [
            ast.unparse(node)
            for node in ast.walk(x26_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assertEqual"
            and any(
                (isinstance(argument, ast.Constant) and argument.value == 0)
                or (isinstance(argument, ast.List) and not argument.elts)
                for argument in node.args
            )
        ]
        d24_patch_targets = [
            ast.literal_eval(node.args[1])
            for node in ast.walk(d24_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "object"
            and len(node.args) > 1
            and isinstance(node.args[1], ast.Constant)
        ]
        self.assertTrue(any("imports" in assertion for assertion in x26_zero_assertions))
        self.assertTrue(
            any("helper" in assertion or "_source" in assertion for assertion in x26_zero_assertions)
        )
        self.assertIn("hasattr(cement_cli, 'CommandCandidateSource')", x26_code)
        self.assertIn("hasattr(cement_cli, '_source')", x26_code)
        self.assertNotIn("_source", d24_patch_targets)
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", d24_code)

        cli_tree = _cli_tree()
        self.assertFalse(
            any(
                isinstance(node, ast.ImportFrom)
                and node.level == 1
                and node.module == "source"
                for node in ast.walk(cli_tree)
            )
        )
        self.assertFalse(
            any(
                isinstance(node, ast.FunctionDef) and node.name == "_source"
                for node in ast.walk(cli_tree)
            )
        )

    def test_d20_tests_test_submission_battery_py_b02_s_docstring_narra(self) -> None:
        """D20 obligation

        CONTRACT:
        `tests/test_submission_battery.py` B02's docstring narrates D25's "28 to 30 leaves and
        35 to 37 nodes" migration. That prose goes stale WITHOUT failing, because B02 asserts
        only `_command_supervisor.py` and `example_adapter.py` byte equality. Silent staleness
        is the defect class that has closed seven consecutive units; the docstring is corrected
        in this unit.

        GATE-2 STRENGTHENING, binding this test's construction:
        D20 must grade its own narrative. B02's docstring can carry any census numbers and stay
        green,
        """
        b02 = _function_node("tests/test_submission_battery.py", "test_b02_")
        docstring = ast.get_docstring(b02) or ""
        parser = cement_cli._parser()
        leaves, nodes = _parser_census(parser)
        expected_fragments = {f"30 to {len(leaves)}", f"37 to {nodes}", "handle", "request"}

        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertEqual((len(leaves), nodes), (28, 35))
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, docstring)
        self.assertNotIn("28 to 30", docstring)
        self.assertNotIn("35 to 37", docstring)
        self.assertNotIn("changed default, help string, payload or dispatch", docstring)
        self.assertNotIn("parser_shape` digest carries that remainder", docstring)

    def test_d21_the_battery_s_independent_parser_shape_oracle_is_delib(self) -> None:
        """D21 obligation

        CONTRACT:
        The battery's independent `parser_shape` oracle is DELIBERATE duplication — importing
        the graded function would make the check circular — and it carries a standing
        re-derivation cost. It is re-derived to 151 actions and `ebd2ac811bd9776d`, and the
        duplication stays.
        """
        target = _function_node("tests/test_cli_channels_battery.py", "test_d27_")
        nested = [
            node
            for node in target.body
            if isinstance(node, ast.FunctionDef) and node.name == "parser_shape"
        ]
        imported_oracle = [
            node
            for node in ast.walk(_executable_tree(target))
            if isinstance(node, ast.Name) and node.id == "probe_parser_shape"
        ]
        self.assertEqual(len(nested), 1)
        self.assertEqual(imported_oracle, [])

        module = ast.Module(body=[nested[0]], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace: dict[str, object] = {"argparse": argparse, "hashlib": hashlib}
        exec(compile(module, "<independent-parser-shape>", "exec"), namespace)
        oracle = namespace["parser_shape"]
        parser = cement_cli._parser()
        before = oracle(parser)
        self.assertEqual(before, (151, "ebd2ac811bd9776d"))
        self.assertEqual(before, _parser_shape(parser))

        events = _leaf_parsers(parser)[("events",)]
        limit = next(action for action in events._actions if action.dest == "limit")
        original = limit.default
        limit.default = 7
        try:
            mutated = oracle(parser)
        finally:
            limit.default = original
        self.assertNotEqual(mutated, before)

    def test_d22a_direction_cli_route_every_cli_route_locus_was_rewritte(self) -> None:
        """D22a obligation

        CONTRACT:
        — THE PROSE SPLITS BY ROUTE, AND BOTH DIRECTIONS OF ERROR ARE DEFECTS. CLI-route prose
        describes commands that cease to exist and MUST change. Library-API prose describes
        `System.handle`, which survives until M3.6a, and MUST NOT change here: deleting it
        breaks the track order and pre-empts M3.6a's own doc pass. | locus | route |
        disposition | |---|---|---| | `README.md` quick start, `uv run cement ... handle
        support.reply --request-id ...` | CLI | rewrite onto `proposal submit` | | `README.md`
        "Repeat with a distinct request ID until the confirmations satisfy the policy" | CLI |
        rewrite | | `README.md` `handle`/`request` return-state table (`in_progress`,
        `fallback_failed`, `rejected`, `reconciliation_required`) with `Poll request
        REQUEST_ID` advice | CLI | remove; no command reaches these states | | `README.md` "The
        ordinary `handle` result exposes a proposal ID" | CLI | rewrite | | `README.md`
        `System.handle(...)` API example and its `request_id=` argument | library | KEEP | |
        `README.md` "Only the `handle` and `request` route still carries a request identifier"
        | mixed | re-scope to the library route | | `docs/architecture.md` steps 1-3, "Steps 1
        to 3 describe `handle`, the request lifecycle" | library | KEEP | |
        `docs/threat-model.md:78` "`handle` request ID as an idempotency key" | library | KEEP
        | | `examples/hospital_ocr/README.md` `System.handle(...)` | library | KEEP | |
        `docs/adapter-protocol.md` | M3.7 | untouched |

        THIS CLAUSE, and no sibling clause:
        DIRECTION cli-route: every CLI-route locus was rewritten and names no removed command

        CORRECTED-BY correction 4, superseding the text above:
        WRONG AS WRITTEN: the `handle`/`request` return-state table dispositioned `remove` --
        CORRECT: **KEEP.** No command reaches those states, but `System.handle` and
        `System.request_status` both survive and both return all six, so the table is live
        library-API documentation. Removing it does what D22's own header forbids. Its
        CLI-shaped caller actions are re-scoped instead (X27, Y18)

        CORRECTED-BY scope correction (D22's locus table is a FLOOR, never a census.), superseding the text above:
        It omitted two CLI-route sentences in the
        """
        readme = (ROOT / "README.md").read_text()
        quick_start = _between(readme, "## Quick start", "### The function group")
        commands = [
            argv
            for command in _shell_commands(quick_start)
            if (argv := _cement_argv(command)) is not None
        ]
        parser = cement_cli._parser()
        parsed = [parser.parse_args(argv) for argv in commands]
        submissions = [
            namespace
            for namespace in parsed
            if namespace.command == "proposal" and namespace.proposal_command == "submit"
        ]

        self.assertEqual(len(submissions), 1)
        self.assertEqual(
            set(json.loads(submissions[0].submission)),
            {"input", "output", "provenance"},
        )
        self.assertEqual(
            [namespace.command for namespace in parsed if namespace.command in REMOVED_LEAVES],
            [],
        )
        self.assertTrue(REMOVED_FLAGS.isdisjoint(quick_start.split()))

        flat_readme = re.sub(r"\s+", " ", readme)
        stale_phrases = (
            "The ordinary `handle` result exposes a proposal ID",
            "Repeat with a distinct request ID",
            "Use it instead of `handle` when you generate the candidate yourself",
            "same `proposal review` command that the `handle` route uses",
            "Only the `handle` and `request` route still carries a request identifier",
            "It applies equally to `handle` and to all reads",
        )
        for phrase in stale_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, flat_readme)
        self.assertRegex(
            readme,
            r"System\.handle.{0,120}System\.request_status.{0,120}library route",
        )

    def test_d22b_direction_library_route_every_library_api_locus_is_byt(self) -> None:
        """D22b obligation

        CONTRACT:
        — THE PROSE SPLITS BY ROUTE, AND BOTH DIRECTIONS OF ERROR ARE DEFECTS. CLI-route prose
        describes commands that cease to exist and MUST change. Library-API prose describes
        `System.handle`, which survives until M3.6a, and MUST NOT change here: deleting it
        breaks the track order and pre-empts M3.6a's own doc pass. | locus | route |
        disposition | |---|---|---| | `README.md` quick start, `uv run cement ... handle
        support.reply --request-id ...` | CLI | rewrite onto `proposal submit` | | `README.md`
        "Repeat with a distinct request ID until the confirmations satisfy the policy" | CLI |
        rewrite | | `README.md` `handle`/`request` return-state table (`in_progress`,
        `fallback_failed`, `rejected`, `reconciliation_required`) with `Poll request
        REQUEST_ID` advice | CLI | remove; no command reaches these states | | `README.md` "The
        ordinary `handle` result exposes a proposal ID" | CLI | rewrite | | `README.md`
        `System.handle(...)` API example and its `request_id=` argument | library | KEEP | |
        `README.md` "Only the `handle` and `request` route still carries a request identifier"
        | mixed | re-scope to the library route | | `docs/architecture.md` steps 1-3, "Steps 1
        to 3 describe `handle`, the request lifecycle" | library | KEEP | |
        `docs/threat-model.md:78` "`handle` request ID as an idempotency key" | library | KEEP
        | | `examples/hospital_ocr/README.md` `System.handle(...)` | library | KEEP | |
        `docs/adapter-protocol.md` | M3.7 | untouched |

        THIS CLAUSE, and no sibling clause:
        DIRECTION library-route: every library-API locus is byte-identical, `System.handle`
        prose included, so this unit pre-empts no M3.6a doc work

        CORRECTED-BY correction 4, superseding the text above:
        WRONG AS WRITTEN: the `handle`/`request` return-state table dispositioned `remove` --
        CORRECT: **KEEP.** No command reaches those states, but `System.handle` and
        `System.request_status` both survive and both return all six, so the table is live
        library-API documentation. Removing it does what D22's own header forbids. Its
        CLI-shaped caller actions are re-scoped instead (X27, Y18)

        CORRECTED-BY scope correction (D22's locus table is a FLOOR, never a census.), superseding the text above:
        It omitted two CLI-route sentences in the
        """
        current_readme = (ROOT / "README.md").read_text()
        baseline_readme = _git_bytes("36f7890", "README.md").decode()
        current_architecture = (ROOT / "docs/architecture.md").read_text()
        baseline_architecture = _git_bytes("36f7890", "docs/architecture.md").decode()
        current_threat = (ROOT / "docs/threat-model.md").read_text()
        baseline_threat = _git_bytes("36f7890", "docs/threat-model.md").decode()
        current_hospital = (ROOT / "examples/hospital_ocr/README.md").read_text()
        baseline_hospital = _git_bytes("36f7890", "examples/hospital_ocr/README.md").decode()

        protected = {
            "readme_api": (
                _between(current_readme, "## Library API", "### Explicit proposal submission"),
                _between(baseline_readme, "## Library API", "### Explicit proposal submission"),
            ),
            "architecture_pipeline": (
                (
                    _between(current_architecture, "1. Canonicalize", "4. A separate review")
                    + _between(current_architecture, "Steps 1 to 3 describe", "Two CLI channels")
                ),
                (
                    _between(baseline_architecture, "1. Canonicalize", "4. A separate review")
                    + _between(baseline_architecture, "Steps 1 to 3 describe", "Two CLI channels")
                ),
            ),
            "threat_idempotency": (
                _between(current_threat, "- Treat results as plans.", "- Pass `cement proposal submit"),
                _between(baseline_threat, "- Treat results as plans.", "- Pass `cement proposal submit"),
            ),
            "hospital_pipeline": (
                _between(current_hospital, "### Pipeline", "### Scope and policy"),
                _between(baseline_hospital, "### Pipeline", "### Scope and policy"),
            ),
        }
        changed = [name for name, (current, baseline) in protected.items() if current != baseline]
        self.assertEqual(changed, [])
        self.assertEqual(len(protected), 4)
        self.assertEqual(
            (ROOT / "docs/adapter-protocol.md").read_bytes(),
            _git_bytes("36f7890", "docs/adapter-protocol.md"),
        )

        outcomes = _between(current_readme, "## Request outcomes", "## Examples")
        status_table = _between(
            outcomes,
            "| Status | Meaning | Caller action |",
            "\n\nReplaying a request ID",
        )
        statuses = {
            match.group(1)
            for line in status_table.splitlines()
            if (match := re.match(r"^\| `([^`]+)` \|", line))
        }
        self.assertEqual(
            statuses,
            {
                "resolved",
                "review_required",
                "in_progress",
                "fallback_failed",
                "rejected",
                "reconciliation_required",
            },
        )
        self.assertIn("System.handle", outcomes)
        self.assertIn("System.request_status", outcomes)
        self.assertIn("retry_failed=True", outcomes)
        self.assertNotIn("`request REQUEST_ID`", outcomes)
        self.assertNotIn("retry `handle` with `--retry-failed`", outcomes)

    def test_d22c_the_opening_text_handle_request_fence_is_protected_and(self) -> None:
        """D22c obligation

        CONTRACT:
        — THE PROSE SPLITS BY ROUTE, AND BOTH DIRECTIONS OF ERROR ARE DEFECTS. CLI-route prose
        describes commands that cease to exist and MUST change. Library-API prose describes
        `System.handle`, which survives until M3.6a, and MUST NOT change here: deleting it
        breaks the track order and pre-empts M3.6a's own doc pass. | locus | route |
        disposition | |---|---|---| | `README.md` quick start, `uv run cement ... handle
        support.reply --request-id ...` | CLI | rewrite onto `proposal submit` | | `README.md`
        "Repeat with a distinct request ID until the confirmations satisfy the policy" | CLI |
        rewrite | | `README.md` `handle`/`request` return-state table (`in_progress`,
        `fallback_failed`, `rejected`, `reconciliation_required`) with `Poll request
        REQUEST_ID` advice | CLI | remove; no command reaches these states | | `README.md` "The
        ordinary `handle` result exposes a proposal ID" | CLI | rewrite | | `README.md`
        `System.handle(...)` API example and its `request_id=` argument | library | KEEP | |
        `README.md` "Only the `handle` and `request` route still carries a request identifier"
        | mixed | re-scope to the library route | | `docs/architecture.md` steps 1-3, "Steps 1
        to 3 describe `handle`, the request lifecycle" | library | KEEP | |
        `docs/threat-model.md:78` "`handle` request ID as an idempotency key" | library | KEEP
        | | `examples/hospital_ocr/README.md` `System.handle(...)` | library | KEEP | |
        `docs/adapter-protocol.md` | M3.7 | untouched |

        THIS CLAUSE, and no sibling clause:
        the opening ` ```text ` `handle(request)` fence is PROTECTED and byte-identical; gate 5
        cannot reach it, so the battery asserts it directly

        CORRECTED-BY correction 4, superseding the text above:
        WRONG AS WRITTEN: the `handle`/`request` return-state table dispositioned `remove` --
        CORRECT: **KEEP.** No command reaches those states, but `System.handle` and
        `System.request_status` both survive and both return all six, so the table is live
        library-API documentation. Removing it does what D22's own header forbids. Its
        CLI-shaped caller actions are re-scoped instead (X27, Y18)

        CORRECTED-BY scope correction (D22's locus table is a FLOOR, never a census.), superseding the text above:
        It omitted two CLI-route sentences in the
        """
        current = [
            body
            for language, body in _fenced_blocks((ROOT / "README.md").read_text())
            if language == "text"
        ]
        baseline = [
            body
            for language, body in _fenced_blocks(_git_bytes("36f7890", "README.md").decode())
            if language == "text"
        ]
        self.assertTrue(current)
        self.assertTrue(baseline)
        self.assertEqual(current[0], baseline[0])
        self.assertIn("handle(request)", current[0])
        self.assertNotRegex(current[0], r"\bcement\s+")

    def test_d23_no_shipped_human_facing_surface_instructs_an_operator(self) -> None:
        """D23 obligation

        CONTRACT:
        No shipped human-facing surface instructs an operator to run a command that does not
        exist. Mechanical test: extract every `cement <command>` invocation from README,
        `docs/*.md` and `examples/*/README.md`, and require each to parse under `_parser()`.
        """
        surfaces = [
            ROOT / "README.md",
            *sorted((ROOT / "docs").glob("*.md")),
            *sorted(ROOT.glob("examples/*/README.md")),
        ]
        self.assertEqual(
            {path.relative_to(ROOT).as_posix() for path in surfaces},
            {
                "README.md",
                "docs/adapter-protocol.md",
                "docs/architecture.md",
                "docs/threat-model.md",
                "examples/hospital_ocr/README.md",
            },
        )

        parser = cement_cli._parser()
        leaves, nodes = _parser_census(parser)
        self.assertEqual(leaves, set(SURVIVING_LEAVES))
        self.assertEqual((len(leaves), nodes), (28, 35))
        invocations: list[tuple[str, list[str]]] = []
        failures: list[tuple[str, list[str], str]] = []
        removed_routes: list[tuple[str, list[str]]] = []
        for surface in surfaces:
            for command in _shell_commands(surface.read_text()):
                argv = _cement_argv(command)
                if argv is None:
                    continue
                relative = surface.relative_to(ROOT).as_posix()
                invocations.append((relative, argv))
                try:
                    namespace = parser.parse_args(argv)
                except BaseException as error:
                    failures.append((relative, argv, f"{type(error).__name__}: {error}"))
                    continue
                if namespace.command in REMOVED_LEAVES:
                    removed_routes.append((relative, argv))

        self.assertEqual(len(surfaces), 5)
        self.assertEqual(len(invocations), 18)
        self.assertEqual(failures, [])
        self.assertEqual(removed_routes, [])
        for removed in sorted(REMOVED_LEAVES):
            with self.subTest(control=removed), self.assertRaises(cement_cli._UsageError):
                parser.parse_args([removed])
        survivor = parser.parse_args(
            ["proposal", "submit", "operation", "--submission", "{}"]
        )
        self.assertEqual((survivor.command, survivor.proposal_command), ("proposal", "submit"))

    def test_d24_every_placeholder_a_shipped_command_block_consumes_has(self) -> None:
        """D24 obligation

        CONTRACT:
        Every placeholder a shipped command block consumes has a producing command earlier in
        the same block. The quick-start rewrite changes which command produces the proposal ID,
        so this is re-checked rather than assumed.
        """
        surfaces = [
            ROOT / "README.md",
            *sorted((ROOT / "docs").glob("*.md")),
            *sorted(ROOT.glob("examples/*/README.md")),
        ]
        placeholder = re.compile(
            r"\b(?:[A-Z][A-Z0-9_]*_FROM_[A-Z0-9_]+|[A-Za-z][A-Za-z0-9]*_REPLACE_ME)\b"
        )
        orphans: set[str] = set()
        found: set[str] = set()
        producer_families: set[str] = set()
        command_counts = {"resolve": 0, "proposal submit": 0}
        for surface in surfaces:
            for fence_index, (language, block) in enumerate(_fenced_blocks(surface.read_text()), 1):
                if language not in {"bash", "sh", "shell", "console"}:
                    continue
                produced: set[str] = set()
                for line_index, line in enumerate(block.splitlines(), 1):
                    assigned = {
                        match.group(1)
                        for match in re.finditer(r"\b([A-Z][A-Z0-9_]*)=", line)
                    }
                    consumed = set(placeholder.findall(line)) - assigned
                    found.update(consumed)
                    for token in consumed - produced:
                        orphans.add(
                            f"{surface.relative_to(ROOT)}:fence-{fence_index}:line-{line_index}:{token}"
                        )
                    lowered = " ".join(line.lower().split())
                    if "proposal list" in lowered or "proposal submit" in lowered:
                        produced.add("prop_REPLACE_ME")
                        producer_families.add("proposal")
                    if "function inspect" in lowered:
                        produced.add("HASH_FROM_INSPECT")
                        producer_families.add("inspect")
                    if "function verify" in lowered:
                        produced.add("HASH_FROM_VERIFY")
                        producer_families.add("verify")
                    produced.update(assigned)
                    if re.search(r"\bproposal\s+submit\b", lowered):
                        command_counts["proposal submit"] += 1
                    if re.search(r"(?:^|\s)resolve\s+\S+", lowered):
                        command_counts["resolve"] += 1

        self.assertEqual(orphans, set())
        self.assertTrue(
            {"prop_REPLACE_ME", "HASH_FROM_INSPECT", "HASH_FROM_VERIFY"}.issubset(found)
        )
        self.assertEqual(producer_families, {"proposal", "inspect", "verify"})
        self.assertGreaterEqual(command_counts["proposal submit"], 3)
        self.assertGreaterEqual(command_counts["resolve"], 2)

    def test_d25_rewritten_human_facing_prose_holds_the_project_registe(self) -> None:
        """D25 obligation

        CONTRACT:
        Rewritten human-facing prose holds the project register: instructions ≤20 words per
        sentence, descriptions ≤25, imperative steps, active voice, condition before command.
        """
        surfaces = [
            "README.md",
            "docs/adapter-protocol.md",
            "docs/architecture.md",
            "docs/threat-model.md",
            "examples/hospital_ocr/README.md",
        ]
        fence = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
        changed_paragraphs: list[str] = []
        for relative in surfaces:
            current = fence.sub("", (ROOT / relative).read_text())
            baseline = fence.sub("", _git_bytes("36f7890", relative).decode())
            baseline_units = {
                " ".join(paragraph.split())
                for paragraph in re.split(r"\n\s*\n", baseline)
                if paragraph.strip()
            }
            for paragraph in re.split(r"\n\s*\n", current):
                normalized = " ".join(paragraph.split())
                if normalized and normalized not in baseline_units:
                    changed_paragraphs.append(normalized)

        self.assertTrue(changed_paragraphs)
        register = "\n".join(changed_paragraphs)
        self.assertNotRegex(register.lower(), r"\b(?:simply|robust|seamlessly|leverage)\b")
        sentence_violations: list[tuple[int, str]] = []
        instruction_violations: list[tuple[int, str]] = []
        imperatives = {
            "call",
            "capture",
            "inspect",
            "list",
            "pass",
            "poll",
            "repeat",
            "review",
            "run",
            "submit",
            "use",
        }
        units: list[str] = []
        for paragraph in changed_paragraphs:
            if paragraph.startswith("|"):
                units.extend(cell.strip() for cell in paragraph.split("|") if cell.strip())
            else:
                units.extend(re.split(r"(?<=[.!?])\s+", paragraph))
        root_description = cement_cli._parser().description or ""
        units.append(root_description)
        for sentence in units:
            plain = re.sub(r"[`*_#|]", "", sentence).strip()
            words = re.findall(r"\b[\w-]+\b", plain)
            if words and len(words) > 25:
                sentence_violations.append((len(words), plain))
            if words and words[0].lower() in imperatives and len(words) > 20:
                instruction_violations.append((len(words), plain))
        self.assertEqual(sentence_violations, [])
        self.assertEqual(instruction_violations, [])

        polish = (ROOT / ".agent/polish.md").read_text()
        self.assertIn("port the human-facing register audit to committed state", polish)
        self.assertIn("flags a seeded 30-word instruction and a seeded `simply`", polish)

    def test_d26_root_help_describes_deterministic_resolution_plus_expl(self) -> None:
        """D26 obligation

        CONTRACT:
        Root help describes deterministic resolution plus explicit supervised proposal capture,
        and names no request lifecycle.

        GATE-2 STRENGTHENING, binding this test's construction:
        D26 asserts a capture VERB, not the noun. Keyword presence satisfies a naive reading
        while root
        """
        parser = cement_cli._parser()
        description = parser.description or ""
        root_help = parser.format_help()
        proposal_help = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ).choices["proposal"].format_help()

        self.assertRegex(description.lower(), r"\b(?:capture|submit|collect|record|receive)\w*\b")
        self.assertRegex(description.lower(), r"\bsupervised\b.{0,40}\bproposal\b")
        self.assertRegex(description.lower(), r"\b(?:deterministic|exact)\b")
        self.assertRegex(description.lower(), r"\b(?:answer|resolve)\w*\b")
        self.assertRegex(root_help.lower(), r"\bproposal\b.{0,80}\bsubmit\b")
        self.assertIn("resolve", root_help.lower())
        self.assertIn("proposal", proposal_help.lower())
        self.assertNotRegex(
            root_help.lower(),
            r"\b(?:handle|request|lifecycle|retry|candidate[- ]source)\b",
        )

    def test_d27_this_unit_supersedes_three_m3_5a_obligations_m3_5a_is(self) -> None:
        """D27 obligation

        CONTRACT:
        This unit supersedes three M3.5a obligations. M3.5a is DONE and its contract is
        history; the supersession is recorded HERE and the affected tests are re-based in
        place, so no M3.5a record is rewritten. | M3.5a obligation | superseded clause |
        replacement | |---|---|---| | D24 | zero `_source` calls from either new leaf |
        `_source` does not exist (D08) | | D25 | census 28 → 30 leaves, 35 → 37 nodes; all 28
        baseline leaf paths survive | census 30 → 28 / 37 → 35 as a SET (D02, D12); exactly
        `handle` and `request` are lost (D17) | | D27 | B02 narrates the 28 → 30 migration |
        B02's docstring records the 30 → 28 removal (D20) |

        CORRECTED-BY scope correction (D27's supersession table is short by one row.), superseding the text above:
        M3.5a **D26** is superseded too: its
        """
        historical_path = ".agent/decisions/m3u5a-contract.md"
        self.assertEqual(
            (ROOT / historical_path).read_bytes(),
            _git_bytes("36f7890", historical_path),
        )
        contract = (ROOT / ".agent/decisions/m3u5b-contract.md").read_text()
        superseded = set(
            re.findall(r"^\| (D(?:24|25|26|27)) \|", contract, re.MULTILINE)
        )
        self.assertEqual(superseded, {"D24", "D25", "D26", "D27"})

        d24 = _code(_function_node("tests/test_cli_channels_battery.py", "test_d24_"))
        d25 = _code(_function_node("tests/test_cli_channels_battery.py", "test_d25_"))
        d26 = _code(_function_node("tests/test_cli_channels_battery.py", "test_d26_"))
        b02 = _function_node("tests/test_submission_battery.py", "test_b02_")
        b02_docstring = ast.get_docstring(b02) or ""
        self.assertIn("self.assertFalse(hasattr(cement_cli, '_source'))", d24)
        self.assertIn("{'handle', 'request'}", d25)
        self.assertIn("{'proposal submit', 'resolve'}", d25)
        self.assertIn("self.assertEqual(imports, [])", d26)
        self.assertIn("30 to 28", b02_docstring)
        self.assertIn("37 to 35", b02_docstring)

    def test_d28_b02_keeps_cli_py_out_of_its_frozen_tuple_re_pinning_cl(self) -> None:
        """D28 obligation

        CONTRACT:
        B02 keeps `cli.py` OUT of its frozen tuple. Re-pinning `cli.py` to a fresh baseline
        stays rejected on M3.5a's own grounds: M3.6a and M3.7 are scheduled to edit it again,
        and a pin the plan commits to breaking reports its next scheduled break as a defect.

        CORRECTED-BY correction 7, superseding the text above:
        WRONG AS WRITTEN: "M3.6a and M3.7 are scheduled to edit `cli.py` again" -- CORRECT:
        **neither roadmap unit names `cli.py`**, and post-removal `cli.py` holds no lifecycle
        or source residue for either. The conclusion survives on the file's rate of change: two
        commits each from M3.5a and M3.5b, with M3.6b's refusal fixtures and M3.9a's
        documentation rewrite the plausible next editors (Y06)
        """
        b02 = _function_node("tests/test_submission_battery.py", "test_b02_")
        paths_assignment = next(
            node
            for node in b02.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "paths" for target in node.targets)
        )
        paths = ast.literal_eval(paths_assignment.value)
        expected = (
            "src/cement_runtime/_command_supervisor.py",
            "src/cement_runtime/example_adapter.py",
        )
        docstring = ast.get_docstring(b02) or ""

        self.assertEqual(paths, expected)
        self.assertNotIn("src/cement_runtime/cli.py", paths)
        for relative in paths:
            with self.subTest(relative=relative):
                self.assertEqual((ROOT / relative).read_bytes(), _git_bytes("f9b9755", relative))
        self.assertNotIn("M3.6a and M3.7", docstring)
        self.assertIn("M3.6b", docstring)
        self.assertIn("M3.9a", docstring)
        self.assertRegex(docstring.lower(), r"\b(?:rate of change|two commits)\b")


if __name__ == "__main__":
    unittest.main()
