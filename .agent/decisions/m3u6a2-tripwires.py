"""Enumerate M3.6a2's tripwires and its shipped-prose work list, then grade both.

A removal unit's tripwires are cheaper to measure than to map, and a burden staged over
SOURCE deletions cannot see a frame that pins shipped PROSE: `m3u6a-burden.py` deletes
definitions and never touches a document, so every doc-pinning frame stays green there and
re-emerges mid-implementation as a regression. This is that separate scan, plus the freeze
census the source stage does reach.

Two measured populations, one file:

  PINS   - every `tests/` function that reads a shipped document or a frozen git object AND
           names vocabulary this unit deletes. Each carries its SCOPE, derived from the
           function's own source: GIT-RANGE (both endpoints are git objects, so the pin
           asserts a closed historical diff and survives this unit) or WORKING-TREE (one
           endpoint is the live tree, so the pin inverts the moment this unit edits it).
           A scope pin read against the working tree expires; only a range-scoped assertion
           survives the next unit.

  PROSE  - every hit line in the shipped human-facing documents, with its owning unit ruled
           by MAIN. The mechanical half is enumeration and vocabulary attribution; ownership
           is judgment and is recorded with grounds, never derived.

Counts travel with their convention. VOCAB below IS the convention for every number this
file emits, and it is deliberately wider than M3.5b's D22 deferral table - that table
counted `handle` loci, this one counts every line naming a surface M3.6a2 removes, so the
two numbers are not comparable and neither corrects the other.

Usage:
    uv run python .agent/decisions/m3u6a2-tripwires.py --emit    # write the table
    uv run python .agent/decisions/m3u6a2-tripwires.py           # grade it
    uv run python .agent/decisions/m3u6a2-tripwires.py --self-test
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TABLE = pathlib.Path(__file__).resolve().with_name("m3u6a2-tripwires.json")

DOCS: tuple[str, ...] = (
    "README.md",
    "docs/architecture.md",
    "docs/adapter-protocol.md",
    "docs/threat-model.md",
    "examples/hospital_ocr/README.md",
)

# The convention. Every count in the emitted table is taken under exactly this pattern.
#
# `ambigu` is here because `artifact.ambiguity_quarantined` is emitted at `handle:1143` and NOWHERE
# else in `src/`, so ambiguity quarantine dies with the method: two shipped lines claim a behaviour
# this unit removes and no other token reaches them (contract C05, C06).
#
# `idempot` was measured and EXCLUDED: it adds 11 lines of which 9 correctly describe the SURVIVING
# proposal API ("Cement gives no idempotency here"). A token whose hits cannot legitimately reach
# zero makes L24's owned-hit-count predicate unsatisfiable, so the deleted idempotency claims are
# reached by L22 naming them and by the owned hit at README:52 instead.
VOCAB = re.compile(
    r"\bhandle\b|request_status|retry_failed|invalidated_generators|resolved_by_artifact"
    r"|\brequests?\b|\blease\b|in_progress|fallback_failed|reconciliation_required"
    r"|[Aa]mbigu\w*"
)

# A frame qualifies as a PIN when it reads one of these AND matches VOCAB.
READS_DOC = re.compile(r"README\.md|architecture\.md|threat-model\.md|adapter-protocol\.md")
READS_TREE = re.compile(r"ROOT\s*/\s*\w|\(ROOT / relative\)|ROOT\.joinpath")
GIT_OBJECT = re.compile(r"_git_bytes\(|git_bytes\(|\"[0-9a-f]{7,40}\"|'[0-9a-f]{7,40}'")

# A FREEZE has two shapes. The MODULE shape names a runtime path and re-reads it. The SPAN
# shape reaches `system.py` INDIRECTLY - `cement_runtime.system.__file__`,
# `inspect.getsourcefile(System)`, a `_source(ROOT, path)` helper - and slices one deleted
# method out of it. A literal-path scan sees only the first, so the P06 family sat in the
# detector's negative space while its name promised the family.
FREEZE_PATH = re.compile(r"cement_runtime/system\.py|System\.handle")
FREEZE_READ = re.compile(r"read_bytes\(\)|getsource|_git_bytes\(")
LIVE_SYSTEM_SOURCE = re.compile(
    r"cement_runtime\.system\.__file__|getsourcefile\(\s*System\b|_source\(\s*ROOT\s*,"
)
# The discriminator. The same acquisition selecting a PRESERVED method freezes nothing this
# unit moves, so naming the deleted method is what separates a freeze from a source read.
DELETED_SPAN = re.compile(r"System\.handle|name\s*==\s*[\"']handle[\"']")

# Control fixtures for `_is_freeze`, frozen and synthetic so no repair to a real frame can
# quietly retire the control. The two differ in the METHOD NAME alone: a detector keying on the
# acquisition passes the positive and fails the negative, which is the over-report this pair buys.
P06_FIXTURE_POSITIVE = (
    'def test_span(self):\n'
    '    source = pathlib.Path(inspect.getsourcefile(System)).read_text(encoding="utf-8")\n'
    '    node = next(item for item in ast.parse(source).body if item.name == "handle")\n'
    '    self.assertEqual(len(ast.get_source_segment(source, node)), 12_866)\n'
)
P06_FIXTURE_NEGATIVE = P06_FIXTURE_POSITIVE.replace('"handle"', '"propose"')

# MAIN's ownership ruling per document, with grounds. Keyed by document; a document whose
# every hit belongs to one unit needs no per-line ruling, which is why this is not a line map.
OWNERS: dict[str, tuple[str, str]] = {
    "README.md": (
        "M3.6a2",
        "the poll-state table, both lifecycle method names and the request-route section all "
        "describe surfaces this unit deletes; no line names a result model by class name",
    ),
    "docs/architecture.md": (
        "M3.6a2",
        "steps 1-3 describe `handle`; the lease paragraph describes the knob this unit deletes",
    ),
    "docs/adapter-protocol.md": (
        "M3.6a2",
        "M3.7 relocates this document with BYTE EQUALITY, so it never rewrites a claim - "
        "leaving false `handle` prose here would relocate the defect instead of fixing it",
    ),
    "docs/threat-model.md": (
        "M3.6a2",
        "`handle` request ID as an idempotency key, and lease recovery, both cease to exist",
    ),
    "examples/hospital_ocr/README.md": (
        "M3.6a1",
        "already rewritten by M3.6a1's D22-D23 transcript regeneration; the surviving hit is "
        "the demo's own prose and names no deleted surface",
    ),
}


# This unit's OWN battery is excluded from both scanners. Its docstrings quote the contract's
# obligation text verbatim, so every prose obligation registers as a pin and L29's obligation
# registers as a freeze - the census would then count its own instrument and drift on every battery
# edit. Measured: committing the seed alone took PINS 15 -> 18 and FREEZES 4 -> 5, and gate 3 was
# red from that commit onward (contract C06).
SELF = "test_lifecycle_removal_battery.py"


def _frame_scope(segment: str) -> str:
    """Classify a pin by which endpoints it reads."""
    tree = bool(READS_TREE.search(segment))
    git = bool(GIT_OBJECT.search(segment))
    if git and not tree:
        return "GIT-RANGE"
    if tree and git:
        return "MIXED"
    return "WORKING-TREE"


def _is_freeze(segment: str) -> bool:
    """True when a frame re-reads bytes this unit moves, by either shape above."""
    module_shape = bool(FREEZE_PATH.search(segment)) and bool(FREEZE_READ.search(segment))
    span_shape = bool(LIVE_SYSTEM_SOURCE.search(segment)) and bool(DELETED_SPAN.search(segment))
    return module_shape or span_shape


def _pins() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted((ROOT / "tests").glob("*.py")):
        if path.name == SELF:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            segment = ast.get_source_segment(source, node) or ""
            if not (READS_DOC.search(segment) and VOCAB.search(segment)):
                continue
            rows.append(
                {
                    "locus": f"tests/{path.name}:{node.lineno}",
                    "test": node.name,
                    "scope": _frame_scope(segment),
                    "vocabulary": sorted(set(VOCAB.findall(segment))),
                    "lines": len(segment.splitlines()),
                }
            )
    return rows


def _freezes() -> list[dict[str, object]]:
    """Frames freezing a runtime module or method span this unit edits, by construction."""
    rows: list[dict[str, object]] = []
    for path in sorted((ROOT / "tests").glob("*.py")):
        if path.name == SELF:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            segment = ast.get_source_segment(source, node) or ""
            if not _is_freeze(segment):
                continue
            rows.append(
                {
                    "locus": f"tests/{path.name}:{node.lineno}",
                    "test": node.name,
                    "scope": _frame_scope(segment),
                    "lines": len(segment.splitlines()),
                }
            )
    return rows


def _prose() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for relative in DOCS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        hits = [
            {"line": index, "tokens": sorted(set(VOCAB.findall(line)))}
            for index, line in enumerate(text.splitlines(), start=1)
            if VOCAB.search(line)
        ]
        owner, grounds = OWNERS[relative]
        rows.append(
            {
                "document": relative,
                "total_lines": len(text.splitlines()),
                "hit_lines": len(hits),
                "owner": owner,
                "grounds": grounds,
                "hits": hits,
            }
        )
    return rows


def emit() -> dict[str, object]:
    head = subprocess.check_output(("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True).strip()
    pins = _pins()
    prose = _prose()
    return {
        "unit": "M3.6a2",
        "head": head,
        "vocabulary": VOCAB.pattern,
        "excluded": [f"tests/{SELF}"],
        "convention": (
            "hit_lines counts DOCUMENT LINES matching `vocabulary`, not `handle` loci; "
            "M3.5b's D22 deferral table counted the latter, so the two are incomparable"
        ),
        "pins": pins,
        "freezes": _freezes(),
        "prose": prose,
        "totals": {
            "pins": len(pins),
            "pins_working_tree": sum(1 for row in pins if row["scope"] != "GIT-RANGE"),
            "prose_hit_lines": sum(int(row["hit_lines"]) for row in prose),
            "prose_documents_owned": sum(1 for row in prose if row["owner"] == "M3.6a2"),
        },
    }


def validate(table: dict[str, object]) -> int:
    failures: list[str] = []
    live = emit()
    for key in ("pins", "freezes", "prose"):
        if json.dumps(table[key], sort_keys=True) != json.dumps(live[key], sort_keys=True):
            failures.append(f"DRIFT: committed `{key}` disagrees with a fresh measurement")
    if table["vocabulary"] != VOCAB.pattern:
        failures.append("VOCAB-DRIFT: the table was emitted under a different convention")
    unowned = [row["document"] for row in table["prose"] if row["owner"] == "unknown"]
    if unowned:
        failures.append(f"UNRULED: {unowned}")
    ungrounded = [row["document"] for row in table["prose"] if not str(row["grounds"]).strip()]
    if ungrounded:
        failures.append(f"UNGROUNDED: {ungrounded}")
    # A pin asserting a closed historical range survives this unit; a working-tree pin does not.
    # The unit is UNSTARTED while every working-tree pin is still green, so this is the red-at-
    # baseline credential: at least one must exist, or the census found nothing to protect.
    leaked = sorted(
        str(row["locus"]) for key in ("pins", "freezes") for row in table[key]
        if SELF in str(row["locus"])
    )
    if leaked:
        failures.append(f"SELF-REFERENCE: this unit's own battery entered the census: {leaked}")
    if int(table["totals"]["pins_working_tree"]) == 0:
        failures.append("NO-TRIPWIRE: no working-tree pin found; the scan is not discriminating")
    for label in ("pins", "prose_hit_lines"):
        if int(table["totals"][label]) == 0:
            failures.append(f"EMPTY: `{label}` measured zero")
    for line in failures:
        print(line)
    print(f"EXCLUDED: {', '.join(table.get('excluded', ())) or 'none'}")
    print(f"PINS: {table['totals']['pins']}")
    print(f"PINS-WORKING-TREE: {table['totals']['pins_working_tree']}")
    print(f"FREEZES: {len(table['freezes'])}")
    print(f"PROSE-HIT-LINES: {table['totals']['prose_hit_lines']}")
    print(f"PROSE-DOCUMENTS-OWNED: {table['totals']['prose_documents_owned']}")
    print(f"RESULT: {'FAIL' if failures else 'PASS'}")
    return 1 if failures else 0


def self_test() -> int:
    """Grade the grader both ways: every control must fire."""
    base = emit()
    controls: list[tuple[str, dict[str, object], str]] = []

    dropped = json.loads(json.dumps(base))
    dropped["pins"] = dropped["pins"][1:]
    controls.append(("dropped pin row", dropped, "DRIFT"))

    unruled = json.loads(json.dumps(base))
    unruled["prose"][0]["owner"] = "unknown"
    controls.append(("unruled document", unruled, "UNRULED"))

    ungrounded = json.loads(json.dumps(base))
    ungrounded["prose"][0]["grounds"] = "   "
    controls.append(("blank grounds", ungrounded, "UNGROUNDED"))

    vocab = json.loads(json.dumps(base))
    vocab["vocabulary"] = r"\bhandle\b"
    controls.append(("foreign vocabulary", vocab, "VOCAB-DRIFT"))

    rescoped = json.loads(json.dumps(base))
    for row in rescoped["pins"]:
        row["scope"] = "GIT-RANGE"
    rescoped["totals"]["pins_working_tree"] = 0
    controls.append(("every pin range-scoped", rescoped, "NO-TRIPWIRE"))

    empty = json.loads(json.dumps(base))
    empty["prose"] = [dict(row, hits=[], hit_lines=0) for row in empty["prose"]]
    empty["totals"]["prose_hit_lines"] = 0
    controls.append(("no prose hits", empty, "EMPTY"))

    mirror = json.loads(json.dumps(base))
    mirror["pins"] = mirror["pins"] + [
        {"locus": f"tests/{SELF}:1", "test": "test_l19_x", "scope": "WORKING-TREE",
         "vocabulary": ["handle"], "lines": 3}
    ]
    controls.append(("battery counted as a pin", mirror, "SELF-REFERENCE"))

    silent: list[str] = []
    # The last control grades the DETECTOR rather than a table: `validate` compares two tables and
    # is blind to a `_is_freeze` that reports nothing, so a table-only battery would credit a
    # detector that lost the span shape entirely.
    detector = [
        label
        for label, expected, segment in (
            ("span-shape freeze unseen", True, P06_FIXTURE_POSITIVE),
            ("preserved-method read over-reported", False, P06_FIXTURE_NEGATIVE),
        )
        if _is_freeze(segment) is not expected
    ]
    total = len(controls) + 1
    if detector:
        silent.append(f"`_is_freeze` fixture pair -> {', '.join(detector)}")

    for label, mutated, expected in controls:
        import io
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            validate(mutated)
        if expected not in buffer.getvalue():
            silent.append(f"{label} -> expected {expected}")
    buffer = __import__("io").StringIO()
    with __import__("contextlib").redirect_stdout(buffer):
        clean = validate(base)
    if clean != 0:
        silent.append("filled table does not grade PASS")
    for line in silent:
        print(f"SILENT: {line}")
    print(f"CONTROLS: {total - len(silent)}/{total} firing")
    print(f"RESULT: {'FAIL' if silent else 'PASS'}")
    return 1 if silent else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enumerate and grade M3.6a2's tripwires.")
    parser.add_argument("--emit", action="store_true", help="write the table")
    parser.add_argument("--self-test", action="store_true", help="grade the grader both ways")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.emit:
        TABLE.write_text(json.dumps(emit(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"WROTE: {TABLE.relative_to(ROOT)}")
        return 0
    if not TABLE.is_file():
        print(f"MISSING: {TABLE.relative_to(ROOT)}; run --emit first")
        return 1
    return validate(json.loads(TABLE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    sys.exit(main())
