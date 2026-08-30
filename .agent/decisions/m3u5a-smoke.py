#!/usr/bin/env python
"""End-to-end smoke probe for M3.5a's two CLI channels, against a real ledger.

    uv run python .agent/decisions/m3u5a-smoke.py

Prints one `OK`/`BAD` line per probe and exits nonzero on any `BAD`. This audits
the CONTRACT, not only the code: it drives the shipped `main` entry point over a
ledger built by ordinary commands, so a claim the suite states in fixtures gets
one independent reading. Every probe names its contract obligation.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cement_runtime.cli import SUBMISSION_MAX_BYTES, _parser, main  # noqa: E402
from cement_runtime.json_value import (  # noqa: E402
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
)
from cement_runtime.system import PROVENANCE_MAX_BYTES  # noqa: E402

FAILURES: list[str] = []


def check(label: str, obligation: str, actual: object, expected: object) -> None:
    verdict = "OK " if actual == expected else "BAD"
    if actual != expected:
        FAILURES.append(f"{label}: expected {expected!r}, got {actual!r}")
    print(f"{verdict} {obligation:5s} {label}")


class _BinaryStdin(io.StringIO):
    """A host stream exposing a byte channel, as a real terminal does."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.buffer = io.BytesIO(text.encode("utf-8"))


def binary_stdin(text: str) -> _BinaryStdin:
    return _BinaryStdin(text)


def run(argv: list[str], *, stdin: str | io.StringIO | None = None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    saved = sys.stdin
    if stdin is not None:
        sys.stdin = io.StringIO(stdin) if isinstance(stdin, str) else stdin
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main(argv)
    finally:
        sys.stdin = saved
    return status, out.getvalue(), err.getvalue()


def payload(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"__unparsed__": text}


def main_probe() -> int:
    with tempfile.TemporaryDirectory() as directory:
        ledger = str(pathlib.Path(directory) / "ledger.db")
        absent = str(pathlib.Path(directory) / "absent.db")
        base = ["--db", ledger, "--partition", "t1"]

        # --- D13: the read verb refuses an absent ledger and creates no file ---
        status, out, err = run(["--db", absent, "--partition", "t1", "resolve", "op", "--input", "1"])
        check("absent ledger exit", "D13", status, 5)
        check("absent ledger stderr", "D13", payload(err), {
            "error": "integrity", "message": "ledger file is missing or unreadable",
        })
        check("absent ledger stdout empty", "D13", out, "")
        check("absent ledger stays absent", "D13", os.path.exists(absent), False)

        # --- D13 ordering: a malformed input on an absent ledger creates nothing ---
        status, _, _ = run(["--db", absent, "--partition", "t1", "resolve", "op", "--input", "{"])
        check("malformed input on absent ledger exit", "D13", status, 5)
        check("malformed input creates no ledger", "D13", os.path.exists(absent), False)

        # Shipped policy floors reject `--min-confirmations 1`, and a rejected
        # registration would leave every later probe reporting `not_found`.
        registered, _, register_error = run([*base, "operation", "register", "op"])
        check("registration succeeds", "D22", (registered, register_error), (0, ""))

        # --- D12/D15: unregistered operation is not_found on both leaves ---
        status, _, err = run([*base, "resolve", "nosuch", "--input", "1"])
        check("resolve unregistered exit", "D12", status, 3)
        check("resolve unregistered error", "D12", payload(err).get("error"), "not_found")

        # --- D07/D09/D10: an empty promoted set is a VERIFIED MISS, not a failure ---
        status, out, _ = run([*base, "resolve", "op", "--input", "1"])
        body = payload(out)
        check("empty-set exit", "D10", status, 6)
        check("empty-set on stdout", "D10", isinstance(body, dict) and "passed" in body, True)
        check("empty-set key set", "D07", sorted(body), [
            "artifact_hash", "checks", "entries", "function_hash", "matched", "output", "passed",
        ])
        check("empty-set matched", "D09", body.get("matched"), False)
        check("empty-set passed", "D08", body.get("passed"), True)
        check("empty-set output null", "D09", body.get("output"), None)
        check("empty-set artifact_hash null", "D09", body.get("artifact_hash"), None)
        check("empty-set entries", "D08", body.get("entries"), 0)
        check("checks are ordered triples", "D08",
              sorted({key for check_ in body.get("checks", []) for key in check_}),
              ["detail", "key", "passed"])
        check("no document key reaches stdout", "D11",
              [key for key in body if key in ("document", "text", "verification", "match")], [])

        # --- D05: a mismatched expected hash is library-graded ---
        status, out, err = run([*base, "resolve", "op", "--input", "1",
                                "--expected-function-hash", "00" * 32])
        check("expected-hash mismatch exit", "D05", status, 6)
        check("expected-hash mismatch key set", "D07", sorted(payload(out)), [
            "artifact_hash", "checks", "entries", "function_hash", "matched", "output", "passed",
        ])
        status, _, err = run([*base, "resolve", "op", "--input", "1",
                              "--expected-function-hash", "not-a-digest"])
        check("expected-hash malformed exit", "D05", status, 2)
        check("expected-hash malformed message", "D05", payload(err).get("message"),
              "expected_function_hash must be a SHA-256 hex digest")

        # --- D01: no option prefix resolves as an alias on the new leaf ---
        # Two distinct argparse outcomes, both exit 2 and neither an alias. With
        # the required option supplied the prefix is leftover; when the prefix
        # IS the required option, argparse reports the missing option first,
        # because the required check runs inside `parse_known_args` and the
        # leftover check runs after it.
        for flag in ("--in", "--inp", "--exp", "--expected", "--expected-function"):
            status, _, err = run([*base, "resolve", "op", "--input", "1", flag, "1"])
            check(f"resolve {flag} is leftover", "D01",
                  (status, payload(err).get("message", "").split(":")[0]),
                  (2, "unrecognized arguments"))
        status, _, err = run([*base, "resolve", "op", "--in", "1"])
        check("resolve --in alone reports the missing required option", "D01",
              (status, payload(err).get("message")),
              (2, "the following arguments are required: --input"))

        # --- D14: no option prefix resolves on the submit leaf ---
        status, _, err = run([*base, "proposal", "submit", "op", "--sub", "{}"])
        check("submit --sub rejected", "D14", status, 2)
        status, _, err = run([*base, "proposal", "sub", "op", "--submission", "{}"])
        check("`proposal sub` is an invalid choice", "D14", status, 2)
        check("`proposal sub` message", "D14",
              "invalid choice" in payload(err).get("message", ""), True)

        # --- D20/D21: success is one key ---
        envelope = json.dumps({"input": {"a": 1}, "output": {"b": 2}})
        status, out, err = run([*base, "proposal", "submit", "op", "--submission", envelope])
        first = payload(out)
        check("submit exit", "D20", status, 0)
        check("submit key set", "D20", sorted(first), ["proposal_id"])
        check("submit id shape", "D20", str(first.get("proposal_id", "")).startswith("prop_"), True)
        check("submit echoes no candidate byte", "D21",
              [key for key in ("input", "output", "provenance", "request_id") if key in out], [])

        # --- D15: the same envelope through stdin ---
        status, out, _ = run([*base, "proposal", "submit", "op", "--submission", "-"],
                             stdin=envelope)
        check("submit via stdin exit", "D15", status, 0)

        # --- D23: no idempotency ---
        status, out2, _ = run([*base, "proposal", "submit", "op", "--submission", envelope])
        check("identical submissions differ", "D23",
              payload(out2)["proposal_id"] != first["proposal_id"], True)
        _, listing, _ = run([*base, "proposal", "list", "--status", "pending"])
        check("three pending proposals", "D23", len(payload(listing)), 3)

        # --- D17/D18: envelope grammar ---
        cases = (
            ("D17", '{"input":1,"input":2,"output":3}', 2, "duplicate JSON object key: 'input'"),
            ("D18", '{"input":1,"output":2,"extra":3,"also":4}', 2,
             "submission has unknown keys: also, extra"),
            ("D18", '{"output":2}', 2, "submission is missing required keys: input"),
            ("D18", '{}', 2, "submission is missing required keys: input, output"),
            ("D18", '[1,2]', 2, "submission must be a JSON object"),
            ("D19", '{"input":1,"output":2,"provenance":[1]}', 2,
             "candidate provenance must be a mapping"),
        )
        for obligation, text, want_status, want_message in cases:
            status, _, err = run([*base, "proposal", "submit", "op", "--submission", text])
            check(f"envelope {text[:28]!r} exit", obligation, status, want_status)
            check(f"envelope {text[:28]!r} message", obligation,
                  payload(err).get("message"), want_message)

        # --- D18: provenance defaults to a durable empty mapping ---
        identifier = payload(run([*base, "proposal", "submit", "op",
                                  "--submission", envelope])[1])["proposal_id"]
        _, shown, _ = run([*base, "proposal", "show", identifier])
        check("default provenance is durable", "D18", payload(shown).get("provenance"), {})

        # --- D22: unregistered operation on submit is not_found ---
        status, _, err = run([*base, "proposal", "submit", "nosuch", "--submission", envelope])
        check("submit unregistered exit", "D22", status, 3)
        check("submit unregistered error", "D22", payload(err).get("error"), "not_found")

        # --- D16: the cap is derived, and its adjacent pair holds ---
        check("cap value", "D16", SUBMISSION_MAX_BYTES, 2_162_722)
        check("cap derivation", "D16", SUBMISSION_MAX_BYTES,
              2 * DEFAULT_MAX_BYTES + PROVENANCE_MAX_BYTES + 34)
        # The pair must pin the TRANSPORT, so the at-cap frame has to be one the
        # library accepts: every field at its own maximum simultaneously, which
        # is exactly the submission per-field flags can never carry. A frame
        # spending the whole cap on one field is rejected by the library's
        # per-field limit and would pin nothing about the transport.
        maximal_field = '"' + "x" * (DEFAULT_MAX_BYTES - 2) + '"'
        maximal_provenance = '{"k":"' + "x" * (PROVENANCE_MAX_BYTES - 8) + '"}'
        at_cap = (
            '{"input":' + maximal_field
            + ',"output":' + maximal_field
            + ',"provenance":' + maximal_provenance + "}"
        )
        check("frame at cap is the cap", "D16", len(at_cap.encode()), SUBMISSION_MAX_BYTES)
        status, _, err = run([*base, "proposal", "submit", "op", "--submission", "-"],
                             stdin=binary_stdin(at_cap))
        check("cap accepted", "D16", (status, payload(err).get("message")), (0, None))
        over = at_cap[:-2] + 'x"}'
        check("frame at cap + 1 is one byte more", "D16",
              len(over.encode()), SUBMISSION_MAX_BYTES + 1)
        status, _, err = run([*base, "proposal", "submit", "op", "--submission", "-"],
                             stdin=binary_stdin(over))
        check("cap + 1 rejected on the byte stream", "D16",
              (status, payload(err).get("message")),
              (2, f"submission stdin exceeds {SUBMISSION_MAX_BYTES} bytes"))
        # A text-only host stream has no byte channel, so the same overrun
        # reports characters, mirroring `_input`'s own two spellings.
        status, _, err = run([*base, "proposal", "submit", "op", "--submission", "-"],
                             stdin=over)
        check("cap + 1 rejected on a text stream", "D16",
              (status, payload(err).get("message")),
              (2, f"submission stdin exceeds {SUBMISSION_MAX_BYTES} characters"))
        # Inline text takes the parser's own bound, not the reader's.
        status, _, err = run([*base, "proposal", "submit", "op", "--submission", over])
        check("cap + 1 inline rejected by the parser", "D16",
              (status, payload(err).get("message")),
              (2, f"JSON source exceeds {SUBMISSION_MAX_BYTES} bytes"))

        # --- D17: the envelope's depth and item maxima admit library maxima ---
        check("depth maximum", "D17", DEFAULT_MAX_DEPTH + 1, 65)
        check("item maximum", "D17", 3 * DEFAULT_MAX_ITEMS + 3, 300_003)

        # --- D25: the census is derived, never transcribed ---
        def census(parser: object) -> tuple[int, int]:
            children = [
                child
                for action in getattr(parser, "_actions", ())
                # Only a subparsers action maps names to parsers; `choices` on an
                # ordinary option is a tuple of strings, and on a positional None.
                if isinstance(getattr(action, "choices", None), dict)
                for child in action.choices.values()
            ]
            if not children:
                return 1, 1
            leaves, nodes = 0, 1
            for child in children:
                child_leaves, child_nodes = census(child)
                leaves += child_leaves
                nodes += child_nodes
            return leaves, nodes

        leaves, nodes = census(_parser())
        check("leaf census", "D25", leaves, 30)
        check("node census", "D25", nodes, 37)

    for failure in FAILURES:
        print(f"FAIL {failure}")
    print(f"{'PASS' if not FAILURES else 'FAIL'} ({len(FAILURES)} failures)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main_probe())
