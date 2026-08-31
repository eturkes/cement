#!/usr/bin/env python3
"""Gate 5 (M3.5b D23): every `cement` invocation in shipped prose parses under `_parser()`.

The removal of the `handle` and `request` leaves makes shipped prose the surface that
can now instruct an operator to run a command that does not exist. Prose staleness is
silent: a README block naming a deleted leaf is a working document until a reader runs
it. This gate is the instrument that makes it loud.

Scope is the shipped human-facing set - `README.md`, `docs/*.md` and
`examples/*/README.md`. Every fenced shell block is walked line by line, logical
commands are rebuilt across backslash continuations AND across newlines held open by an
unterminated quote (the repo ships multi-line single-quoted JSON arguments), shell
redirection is cut at the operator, and what remains after the `cement` token is fed to
`_parser().parse_args`.

THREE CONTROLS keep a green run from being vacuous, because an extractor that finds
nothing also reports zero failures:

  1. A floor on the invocation count. A silent extractor regression trips it.
  2. Two synthetic REMOVED-leaf invocations that MUST fail. They prove the parser
     rejects what this unit deleted, so a pass is a verdict rather than an absence.
  3. One synthetic SURVIVING-leaf invocation that MUST parse. It proves the failures
     above are specific rather than universal.

Run: `uv run python .agent/decisions/m3u5b-doc-parse.py`
"""

from __future__ import annotations

import pathlib
import re
import shlex
import sys

from cement_runtime import cli as cement_cli

ROOT = pathlib.Path(__file__).resolve().parents[2]
SHELL_LANGUAGES = {"bash", "sh", "shell", "console"}
REDIRECTIONS = ("<", ">", ">>", "2>", "|", "&&", "||", ";")

# Measured over the shipped set at the M3.5b removal. A drop means the extractor
# stopped seeing blocks it used to see, which is the one failure mode a green run
# cannot otherwise distinguish from clean prose.
INVOCATION_FLOOR = 18

REMOVED = (
    "cement --db d --partition p handle support.reply --request-id t --input {}",
    "cement --db d --partition p request t",
)
SURVIVING = "cement --db d --partition p proposal submit support.reply --submission {}"


def shell_blocks(path: pathlib.Path):
    """Yield `(start_line, lines)` for each fenced block whose info string is a shell."""
    active = False
    is_shell = False
    marker = ""
    started = 0
    lines: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        opening = re.match(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_-]*)\s*$", line)
        if not active and opening:
            active = True
            marker = opening.group(1)
            is_shell = opening.group(2).lower() in SHELL_LANGUAGES
            started = number
            lines = []
            continue
        if active and re.match(rf"^\s*{re.escape(marker)}\s*$", line):
            if is_shell:
                yield started, list(lines)
            active = False
            is_shell = False
            marker = ""
            lines = []
            continue
        if active:
            lines.append(line)


def logical_commands(started: int, lines: list[str]):
    """Rebuild `(line_number, text)` across backslash and open-quote continuations."""
    buffer = ""
    origin = started
    for offset, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if not buffer:
            origin = started + offset
        continued = stripped.endswith("\\")
        buffer += stripped[:-1] + " " if continued else stripped
        if continued:
            continue
        try:
            shlex.split(buffer)
        except ValueError:
            # An unterminated quote holds the argument open across the newline.
            buffer += "\n"
            continue
        yield origin, buffer
        buffer = ""
    if buffer:
        yield origin, buffer


def parse_failure(text: str) -> str | None:
    """Return a reason string when `text` does not parse, or None when it does."""
    try:
        tokens = shlex.split(text)
    except ValueError as error:
        return f"unlexable: {error}"
    for stop in REDIRECTIONS:
        if stop in tokens:
            tokens = tokens[: tokens.index(stop)]
    if "cement" not in tokens:
        return None
    index = tokens.index("cement")
    if index and tokens[index - 1] == "-m":
        # `python3 -m cement_runtime...` style module invocations are not CLI leaves.
        return None
    try:
        cement_cli._parser().parse_args(tokens[index + 1 :])
    except SystemExit as error:
        return f"SystemExit {error.code}"
    except BaseException as error:  # noqa: BLE001 - any refusal is a failure here
        return f"{type(error).__name__}: {error}"
    return None


def main() -> int:
    surfaces = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*.md")),
        *sorted(ROOT.glob("examples/*/README.md")),
    ]
    invocations = 0
    failures: list[str] = []
    for path in surfaces:
        for started, lines in shell_blocks(path):
            for line_number, text in logical_commands(started, lines):
                stripped = text.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                try:
                    tokens = shlex.split(stripped)
                except ValueError:
                    tokens = []
                if "cement" not in tokens:
                    continue
                index = tokens.index("cement")
                if index and tokens[index - 1] == "-m":
                    continue
                invocations += 1
                reason = parse_failure(stripped)
                if reason is not None:
                    location = f"{path.relative_to(ROOT)}:{line_number}"
                    failures.append(f"{location} {reason} :: {stripped[:120]}")

    checks: list[tuple[str, bool, str]] = []
    checks.append(("shipped_prose.surfaces", len(surfaces) >= 5, f"got={len(surfaces)}"))
    checks.append(
        (
            "shipped_prose.invocations",
            invocations >= INVOCATION_FLOOR,
            f"want>={INVOCATION_FLOOR} got={invocations}",
        )
    )
    checks.append(
        ("shipped_prose.parse_failures", not failures, f"got={len(failures)}")
    )
    for text in REMOVED:
        leaf = text.split("partition p ", 1)[1].split(" ", 1)[0]
        checks.append(
            (
                f"control.removed[{leaf}]",
                parse_failure(text) is not None,
                "must not parse",
            )
        )
    checks.append(
        (
            "control.surviving[proposal submit]",
            parse_failure(SURVIVING) is None,
            "must parse",
        )
    )

    for name, ok, detail in checks:
        print(f"CHECK   {name} {'ok' if ok else 'FAIL'} {detail}")
    for failure in failures:
        print(f"  FAILURE {failure}")
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
