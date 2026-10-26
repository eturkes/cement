"""Shared structural engines; wave modules supply identities, fields and CLI dialects.

Historical dialects deliberately keep their validation order, placeholder rules and
reporting. Refactoring a grader must not change the artifact it accepts.
"""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

UNKNOWN = "unknown"


def fail(message: str) -> None:
    print(f"INVALID: {message}")
    raise SystemExit(1)


class StrictWave:
    """Fail-fast JSON tables: row identities + ordered cell checks + seed/report policy."""

    def __init__(
        self,
        tables,
        *,
        doc,
        main_owned,
        prose_min=20,
        report="rows",
        seed=True,
        anchor=None,
        cleared=None,
        citation=None,
        section_max=None,
    ):
        self.tables = tables
        self.doc = doc
        self.main_owned = main_owned
        self.prose_min = prose_min
        self.report = report
        self.can_seed = seed
        self.anchor = anchor
        self.cleared = cleared
        self.citation = citation
        self.section_max = section_max
        self.validators = {kind: self._validator(kind) for kind in tables}

    def _validator(self, kind):
        return lambda payload: self.validate(payload, kind)

    def rows(self, payload, table):
        key = table.get("key", "rows")
        raw = payload.get(key)
        if not isinstance(raw, list):
            fail(f"{key!r} must be a list")
        required = table["subjects"]
        extension = table.get("extension")
        immediate = table.get("extension_first", False)
        seen = {}
        for row in raw:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                prefix = f"every {key} row" if table.get("named_rows") else "every row"
                fail(f"{prefix} must be an object with a string id")
            if row["id"] in seen:
                fail(f"duplicate row id {row['id']!r}")
            if immediate and row["id"] not in required and extension.fullmatch(row["id"]) is None:
                fail(
                    f"row id {row['id']!r} is neither seeded nor a {table['extension_prefix']}nn extension row"
                )
            seen[row["id"]] = row
        missing = [identifier for identifier in required if identifier not in seen]
        extra = [
            identifier
            for identifier in seen
            if identifier not in required
            and (extension is None or extension.fullmatch(identifier) is None)
        ]
        if missing:
            fail(f"missing row ids: {missing}")
        if extra:
            qualifier = f" (extensions must match {extension.pattern})" if extension else ""
            fail(f"unexpected row ids{qualifier}: {extra}")
        return seen

    def prose(self, identifier, field, value, *, typed=True):
        if typed and not isinstance(value, str):
            fail(f"{identifier}.{field} must be a string")
        if len(value) < self.prose_min:
            fail(f"{identifier}.{field} is {len(value)} chars, under {self.prose_min}")

    def identity(self, identifier, row, table):
        fields = table["fields"]
        if set(row) != {"id", *fields}:
            fail(f"{identifier} must carry exactly id plus {list(fields)}")
        field = table["identity"]
        seeded = table["subjects"].get(identifier)
        if seeded is not None and row[field] != seeded:
            fail(f"{identifier}.{field} was rewritten; MAIN owns it, report the objection instead")
        if seeded is None:
            self.prose(identifier, field, row[field], typed=table.get("typed_identity", False))
        if table.get("section_pointer"):
            section = row["section"]
            if not isinstance(section, str):
                fail(f"{identifier}.section must be a string")
            if section != UNKNOWN:
                if self.citation.search(section) is None:
                    fail(
                        f"{identifier}.section {section!r} cites no contract locus; name at least one, "
                        "e.g. 'D12', 'D07, D11', '§13 S2 RULING' or 'Sections 8.3 and 12'"
                    )
                if len(section) > self.section_max:
                    fail(
                        f"{identifier}.section is {len(section)} chars, over {self.section_max}; it is a "
                        "pointer, so put the argument in the row's own prose fields"
                    )

    def strings(self, identifier, row, table):
        unknown = 0
        for field in table["strings"]:
            value = row[field]
            if not isinstance(value, str):
                fail(f"{identifier}.{field} must be a string")
            if value == UNKNOWN:
                if field not in self.main_owned:
                    unknown += 1
                continue
            choices = table.get("enums", {}).get(field)
            if choices is not None and value not in choices:
                fail(f"{identifier}.{field}={value!r} is not one of {sorted(choices)}")
            if (
                field == "anchor"
                and self.anchor is not None
                and self.anchor.fullmatch(value) is None
            ):
                fail(f"{identifier}.anchor {value!r} is neither path:line[-line] nor a SHA nor n/a")
            if (
                field in table.get("cleared_fields", ())
                and self.cleared.fullmatch(value) is not None
            ):
                continue
            if field in table.get("na_fields", ()) and value == "n/a":
                continue
            if (
                field == "acceptance_check"
                and table.get("cleared_acceptance")
                and row["severity"] == "cleared"
            ):
                continue
            if field in table.get("prose", ()):
                self.prose(identifier, field, value)
            if field == "test_name" and table.get("test_name") and not value.startswith("test_"):
                fail(f"{identifier}.test_name {value!r} must name the encoding test")
        return unknown

    def observation(self, identifier, row, table):
        outcome = row["outcome"]
        outcomes = table["outcomes"]
        if outcome not in outcomes:
            fail(f"{identifier}.outcome={outcome!r} is not one of {sorted(outcomes)}")
        if not isinstance(row["note"], str):
            fail(f"{identifier}.note must be a string")
        if outcome == UNKNOWN:
            return 1
        if not isinstance(row["observation"], dict) or not row["observation"]:
            fail(f"{identifier}.observation must be a non-empty object once outcome is filled")
        self.prose(identifier, "note", row["note"])
        return 0

    def cancelled_table(self, rows, table):
        unknown = cancelled = 0
        for identifier, row in sorted(rows.items()):
            values = {field: row.get(field) for field in table["fields"]}
            for field, value in values.items():
                if not isinstance(value, str):
                    fail(f"{identifier}.{field} must be a string")
            if all(value == "cancelled" for value in values.values()):
                cancelled += 1
                continue
            for field, value in values.items():
                if value == "cancelled":
                    fail(f"{identifier}.{field} is cancelled while siblings are not")
                if value == UNKNOWN:
                    if field not in self.main_owned:
                        unknown += 1
                    continue
                choices = table.get("enums", {}).get(field)
                if choices is not None and value not in choices:
                    fail(f"{identifier}.{field}={value!r} is not one of {sorted(choices)}")
                if field in table["prose"]:
                    self.prose(identifier, field, value)
            anchor = values.get("anchor") or values.get("section")
            if anchor not in (None, UNKNOWN) and self.anchor.fullmatch(anchor) is None:
                fail(f"{identifier} anchor {anchor!r} is neither §N nor path:line")
        return unknown, cancelled

    def validate(self, payload, kind):
        table = self.tables[kind]
        unknown = 0
        for field in table.get("top", ()):
            value = payload.get(field)
            if not isinstance(value, str) or not value:
                fail(f"top-level {field!r} must be a non-empty string")
            if value == UNKNOWN:
                unknown += 1
        if table.get("probe_object"):
            probes = payload.get("probes")
            if not isinstance(probes, dict):
                fail("'probes' must be an object")
            missing = [identifier for identifier in table["subjects"] if identifier not in probes]
            extra = [identifier for identifier in probes if identifier not in table["subjects"]]
            if missing:
                fail(f"missing probe ids: {missing}")
            if extra:
                fail(f"unexpected probe ids: {extra}")
            for identifier, probe in sorted(probes.items()):
                if not isinstance(probe, dict) or set(probe) != set(table["fields"]):
                    fail(f"{identifier} must be an object with keys {sorted(table['fields'])}")
                unknown += self.observation(identifier, probe, table)
            return unknown, 0
        rows = self.rows(payload, table)
        if table.get("cancelled"):
            return self.cancelled_table(rows, table)
        for identifier, row in sorted(rows.items()):
            self.identity(identifier, row, table)
            if table.get("outcomes"):
                unknown += self.observation(identifier, row, table)
                continue
            if table.get("severity_first"):
                severity = row["severity"]
                choices = table["enums"]["severity"]
                if severity not in choices:
                    if table.get("severity_value", True):
                        fail(f"{identifier}.severity={severity!r} is not one of {sorted(choices)}")
                    fail(f"{identifier}.severity must be one of {sorted(choices)}")
                if table.get("severity_count") and severity == UNKNOWN:
                    unknown += 1
            if table.get("paired") and row["divergent"] not in (True, False, UNKNOWN):
                fail(f"{identifier}.divergent must be true, false or {UNKNOWN!r}")
            unknown += self.strings(identifier, row, table)
            for field in table.get("string_tail", ()):
                if not isinstance(row[field], str):
                    fail(f"{identifier}.{field} must be a string")
            if table.get("paired"):
                divergent = row["divergent"]
                if divergent == UNKNOWN:
                    unknown += 1
                elif divergent is False and row["reading_b"] == row["reading_a"]:
                    fail(
                        f"{identifier} is marked non-divergent but its two readings are identical text"
                    )
        return unknown

    def seed(self, kind):
        table = self.tables[kind]
        payload = {"kind": kind, **{field: UNKNOWN for field in table.get("top", ())}}
        rows = []
        for identifier, subject in table["subjects"].items():
            row = {"id": identifier}
            for field in table["fields"]:
                row[field] = (
                    subject
                    if field == table["identity"]
                    else copy.deepcopy(table.get("defaults", {}).get(field, UNKNOWN))
                )
            rows.append(row)
        payload["rows"] = rows
        return payload

    def main(self, argv):
        if self.can_seed and len(argv) == 3 and argv[1] == "--emit-seed" and argv[2] in self.tables:
            print(json.dumps(self.seed(argv[2]), indent=2))
            return 0
        if len(argv) != 2:
            print(self.doc)
            return 1
        path = Path(argv[1])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fail(f"unreadable artifact: {exc}")
        if not isinstance(payload, dict):
            fail("artifact must be a JSON object")
        kind = payload.get("kind")
        if kind not in self.tables:
            fail(f"kind={kind!r} is not one of {sorted(self.tables)}")
        result = self.validate(payload, kind)
        unknown, cancelled = result if isinstance(result, tuple) else (result, 0)
        print(f"KIND: {kind}")
        if self.report == "cancelled":
            print(f"CANCELLED: {cancelled}")
        elif self.report == "extensions":
            seeded = self.tables[kind]["subjects"]
            extra = [row["id"] for row in payload["rows"] if row["id"] not in seeded]
            print(f"ROWS: {len(payload['rows'])} ({len(seeded)} seeded, {len(extra)} extension)")
            if extra:
                print(f"EXTENSION-ROWS: {sorted(extra)}")
            print(f"MAIN-OWNED-COLUMNS: {sorted(self.main_owned)} (exempt from UNKNOWN-CELLS)")
        else:
            print(f"ROWS: {len(payload['rows'])}")
            if self.report == "exempt":
                print(
                    f"EXEMPT-COLUMNS: {self.tables[kind]['exempt']} (MAIN-owned; a clean grade does NOT mean a closed table)"
                )
        print(f"UNKNOWN-CELLS: {unknown}")
        if unknown:
            print("INCOMPLETE: fill every cell, then rerun this validator LAST")
            return 1
        print("VALID: structurally sound with zero unfilled cells")
        return 0


class ObservationTables(SimpleNamespace):
    """Accumulating identity, observation and review checks."""

    def _load_probe_subjects(self) -> dict[str, str]:
        path = self.ROOT / ".agent" / "decisions" / "m3u3-probes.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {row["id"]: row["probe"] for row in payload["rows"]}

    def _fail(self, message: str) -> None:
        print(f"INVALID: {message}")

    def _rows(
        self, payload: dict, required: dict[str, str], fields: tuple[str, ...]
    ) -> tuple[dict[str, dict], int]:
        rows = payload.get("rows")
        if not isinstance(rows, list):
            self._fail("payload has no 'rows' list")
            return ({}, 1)
        problems = 0
        seen: dict[str, dict] = {}
        for row in rows:
            if not isinstance(row, dict) or "id" not in row:
                self._fail(f"row is not an object with an id: {row!r:.80}")
                problems += 1
                continue
            identifier = row["id"]
            if identifier in seen:
                self._fail(f"duplicate row id {identifier}")
                problems += 1
                continue
            if identifier not in required and (not self.EXTENSION.match(str(identifier))):
                self._fail(f"row id {identifier} is neither seeded nor an extension row Z<nn>")
                problems += 1
                continue
            subject = fields[0]
            if identifier in required and row.get(subject) != required[identifier]:
                self._fail(
                    f"{identifier}: '{subject}' is MAIN-owned row identity and was rewritten"
                )
                problems += 1
            missing = [field for field in fields if field not in row]
            if missing:
                self._fail(f"{identifier}: missing field(s) {missing}")
                problems += 1
            seen[identifier] = row
        for identifier in required:
            if identifier not in seen:
                self._fail(f"seeded row {identifier} is absent")
                problems += 1
        return (seen, problems)

    def _prose(self, identifier: str, field: str, value: object) -> int:
        if value == self.UNKNOWN:
            return 0
        if not isinstance(value, str) or len(value.strip()) < self.PROSE_MIN:
            self._fail(
                f"{identifier}: '{field}' must be at least {self.PROSE_MIN} characters of prose"
            )
            return 1
        return 0

    def _count_unknown(self, row: dict, fields: tuple[str, ...]) -> int:
        return sum(
            (
                1
                for field in fields
                if field not in self.MAIN_OWNED and row.get(field) == self.UNKNOWN
            )
        )

    def _validate_divergences(self, payload: dict) -> tuple[int, int]:
        required = self._load_probe_subjects()
        rows, problems = self._rows(payload, required, self.DIVERGENCE_FIELDS)
        unknown = 0
        for identifier, row in sorted(rows.items()):
            verdict = row.get("verdict")
            if verdict not in self.VERDICTS:
                self._fail(f"{identifier}: 'verdict' must be one of {sorted(self.VERDICTS)}")
                problems += 1
            for field in ("main_observation", "oracle_observation"):
                value = row.get(field)
                if value != self.UNKNOWN and (not isinstance(value, (dict, str))):
                    self._fail(
                        f"{identifier}: '{field}' must be the recorded observation object or prose"
                    )
                    problems += 1
            divergence = row.get("divergence")
            if (
                verdict == "identical"
                and divergence not in (self.UNKNOWN, None)
                and (not self.CLEARED.match(str(divergence)))
            ):
                self._fail(
                    f"{identifier}: an identical verdict states 'no divergence: <why the join is exact>'"
                )
                problems += 1
            if verdict == "differs":
                problems += self._prose(identifier, "divergence", divergence)
            unknown += self._count_unknown(row, self.DIVERGENCE_FIELDS)
        return (unknown, problems)

    def _validate_review(self, payload: dict) -> tuple[int, int]:
        rows, problems = self._rows(payload, self.REVIEW_LENSES, self.REVIEW_FIELDS)
        unknown = 0
        for identifier, row in sorted(rows.items()):
            severity = row.get("severity")
            if severity not in self.SEVERITIES:
                self._fail(f"{identifier}: 'severity' must be one of {sorted(self.SEVERITIES)}")
                problems += 1
            finding = row.get("finding")
            if (
                severity == "cleared"
                and finding != self.UNKNOWN
                and (not self.CLEARED.match(str(finding)))
            ):
                self._fail(
                    f"{identifier}: a cleared lens states 'no defect: <what was checked and why it holds>'"
                )
                problems += 1
            for field in ("finding", "evidence", "acceptance_check"):
                problems += self._prose(identifier, field, row.get(field))
            unknown += self._count_unknown(row, self.REVIEW_FIELDS)
        return (unknown, problems)

    def _seed(self, kind: str) -> dict:
        if kind == "divergences":
            subjects, fields = (self._load_probe_subjects(), self.DIVERGENCE_FIELDS)
        else:
            subjects, fields = (self.REVIEW_LENSES, self.REVIEW_FIELDS)
        rows = []
        for identifier, subject in subjects.items():
            row = {"id": identifier, fields[0]: subject}
            row.update({field: self.UNKNOWN for field in fields[1:]})
            rows.append(row)
        return {"kind": kind, "implementation": self.UNKNOWN, "rows": rows}

    def main(self, argv: list[str]) -> int:
        if len(argv) == 2 and argv[0] == "--emit-seed":
            kind = argv[1]
            if kind not in self.VALIDATORS:
                self._fail(f"unknown kind {kind}; expected one of {sorted(self.VALIDATORS)}")
                return 2
            print(json.dumps(self._seed(kind), indent=2))
            return 0
        if len(argv) != 1:
            self._fail(self.documentation.splitlines()[2].strip())
            return 2
        path = Path(argv[0])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            self._fail(f"cannot read {path}: {error}")
            return 2
        kind = payload.get("kind")
        if kind not in self.VALIDATORS:
            self._fail(f"top-level 'kind' must be one of {sorted(self.VALIDATORS)}, got {kind!r}")
            return 2
        unknown, problems = self.VALIDATORS[kind](payload)
        if payload.get("implementation") == self.UNKNOWN:
            unknown += 1
        print(f"KIND: {kind}")
        print(f"MAIN-OWNED-COLUMNS: {sorted(self.MAIN_OWNED)} (exempt from UNKNOWN-CELLS)")
        print(f"UNKNOWN-CELLS: {unknown}")
        print(f"STRUCTURAL-PROBLEMS: {problems}")
        ok = not unknown and (not problems)
        print("RESULT: PASS" if ok else "RESULT: FAIL")
        return 0 if ok else 1


class FieldTables(SimpleNamespace):
    """Known columns plus an exact placeholder-value census."""

    def grade(self, kind: str, path: Path) -> int:
        seed, fields, exempt = self.KINDS[kind]
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            print(f"UNREADABLE {path}: {error}", file=sys.stderr)
            return 1
        problems: list[str] = []
        if document.get("kind") != kind:
            problems.append(f"kind must be {kind!r}, found {document.get('kind')!r}")
        rows = document.get("rows")
        if not isinstance(rows, list) or not rows:
            print(f"NO ROWS in {path}", file=sys.stderr)
            return 1
        identifiers = [row.get("id") for row in rows]
        if len(set(identifiers)) != len(identifiers):
            problems.append("duplicate row ids")
        missing = sorted(set(seed) - set(identifiers))
        if missing:
            problems.append(f"seeded rows absent (the seed is a floor): {missing}")
        for identifier in identifiers:
            if identifier not in seed and (not str(identifier).startswith("X")):
                problems.append(f"unseeded row {identifier!r} must take an X-prefixed id")
        unknown = 0
        for row in rows:
            for field in fields:
                if field not in row:
                    problems.append(f"{row.get('id')}: field {field!r} absent")
                    unknown += 1
                elif row[field] in self.UNFILLED:
                    unknown += 1
            for field in row:
                if field not in fields and field not in exempt:
                    problems.append(f"{row.get('id')}: unexpected field {field!r}")
        print(f"kind={kind} rows={len(rows)} seeded={len(seed)} extensions={len(rows) - len(seed)}")
        print(f"EXEMPT-COLUMNS (MAIN fills, not graded here): {list(exempt)}")
        for problem in problems:
            print(f"PROBLEM {problem}")
        print(f"UNKNOWN-CELLS: {unknown}")
        print("PASS" if unknown == 0 and (not problems) else "FAIL")
        return 0 if unknown == 0 and (not problems) else 1

    def main(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(description=self.documentation)
        parser.add_argument("--kind", required=True, choices=sorted(self.KINDS))
        parser.add_argument(
            "--emit-stub", action="store_true", help="print the all-unknown skeleton"
        )
        parser.add_argument("path", nargs="?")
        arguments = parser.parse_args(argv)
        seed, fields, _ = self.KINDS[arguments.kind]
        if arguments.emit_stub:
            rows = [
                {
                    field: identifier
                    if field == "id"
                    else subject
                    if field == "subject"
                    else "unknown"
                    for field in fields
                }
                for identifier, subject in seed.items()
            ]
            print(json.dumps({"kind": arguments.kind, "rows": rows}, indent=2))
            return 0
        if not arguments.path:
            parser.error("a path is required unless --emit-stub is given")
        return self.grade(arguments.kind, Path(arguments.path))


class ColumnTables(SimpleNamespace):
    """Graded/exempt columns with an optional differential projection."""

    def _fail(self, message: str) -> None:
        print(f"INVALID: {message}")

    def emit_seed(self, kind: str) -> int:
        spec = self.SPEC[kind]
        subjects = {
            "probes": self.PROBE_SUBJECTS,
            "review": self.REVIEW_SUBJECTS,
            "mutants": self.MUTANT_SUBJECTS,
        }[kind]
        columns = tuple(spec["graded"]) + tuple(spec["exempt"])
        rows = []
        for identifier, section, locus in subjects:
            row: dict[str, object] = {"id": identifier, "section": section, "locus": locus}
            for column in columns:
                row[column] = None if column in spec["exempt"] else self.UNKNOWN
            rows.append(row)
        path = Path(str(spec["path"]))
        path.write_text(
            json.dumps({"kind": kind, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"WROTE: {path.relative_to(self.ROOT)} ({len(rows)} rows)")
        return 0

    def grade(self, path: Path, *, differential: bool = False) -> int:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self._fail(f"{path} is unreadable: {error}")
            return 2
        kind = document.get("kind")
        if kind not in self.SPEC:
            self._fail(f"kind must be one of {sorted(self.SPEC)}, got {kind!r}")
            return 2
        spec = self.SPEC[kind]
        rows = document.get("rows")
        if not isinstance(rows, list) or not rows:
            self._fail("rows must be a nonempty list")
            return 2
        promoted = tuple(spec["differential"]) if differential else ()
        if differential and (not promoted):
            self._fail(f"kind {kind} has no differential columns; drop --differential")
            return 2
        graded = tuple(spec["graded"]) + promoted
        exempt = tuple((column for column in spec["exempt"] if column not in promoted))
        prose = set(spec["prose"])
        unknown_cells = 0
        problems: list[str] = []
        seen: set[str] = set()
        for index, row in enumerate(rows):
            identifier = row.get("id") or f"row[{index}]"
            if identifier in seen:
                problems.append(f"{identifier}: duplicate id")
            seen.add(identifier)
            for column in ("id", "section", "locus", *graded):
                if column not in row:
                    problems.append(f"{identifier}: missing column {column}")
            for column in graded:
                value = row.get(column)
                if value is None or (
                    isinstance(value, str) and value.strip().lower() == self.UNKNOWN
                ):
                    unknown_cells += 1
                    continue
                if not isinstance(value, str) or not value.strip():
                    problems.append(f"{identifier}.{column}: must be a nonempty string")
                    continue
                if column in prose and len(value.strip()) < self.PROSE_MIN:
                    problems.append(
                        f"{identifier}.{column}: {len(value.strip())} chars, needs {self.PROSE_MIN}"
                    )
            if kind == "review":
                severity = row.get("severity")
                if (
                    isinstance(severity, str)
                    and severity not in self.SEVERITY
                    and (severity != self.UNKNOWN)
                ):
                    problems.append(f"{identifier}.severity: must be one of {self.SEVERITY}")
            if kind == "mutants":
                result = row.get("result")
                if isinstance(result, str) and result not in self.RESULT:
                    problems.append(f"{identifier}.result: must be one of {self.RESULT}")
            if "differs" in promoted:
                differs = row.get("differs")
                if isinstance(differs, str) and differs not in self.DIFFERS:
                    problems.append(f"{identifier}.differs: must be one of {self.DIFFERS}")
        subjects = {
            "probes": self.PROBE_SUBJECTS,
            "review": self.REVIEW_SUBJECTS,
            "mutants": self.MUTANT_SUBJECTS,
        }[kind]
        seeded = len(subjects)
        missing = {identifier for identifier, _, _ in subjects} - seen
        problems.extend(f"missing seeded id {identifier}" for identifier in sorted(missing))
        for problem in problems:
            self._fail(problem)
        print(f"KIND: {kind}")
        print(f"ROWS: {len(rows)} (seeded {seeded}, extension {max(0, len(rows) - seeded)})")
        print(f"GRADED-COLUMNS: {', '.join(graded)}")
        print(f"GRADED-MODE: {('differential' if differential else 'production')}")
        print(f"EXEMPT-COLUMNS: {', '.join(exempt) or '(none)'} (MAIN-owned, never graded here)")
        print(f"UNKNOWN-CELLS: {unknown_cells}")
        ok = not problems and unknown_cells == 0
        print("RESULT: PASS" if ok else "RESULT: FAIL")
        return 0 if ok else 1

    def main(self, argv: list[str]) -> int:
        parser = argparse.ArgumentParser(description=self.documentation)
        parser.add_argument(
            "--emit-seed", choices=sorted(self.SPEC), help="write the all-unknown seed"
        )
        parser.add_argument(
            "--differential",
            action="store_true",
            help="also grade the differential columns a re-derivation against MAIN's code fills",
        )
        parser.add_argument("table", nargs="?", help="the table to grade")
        args = parser.parse_args(argv)
        if args.emit_seed:
            return self.emit_seed(args.emit_seed)
        if not args.table:
            parser.error("give a table to grade or --emit-seed <kind>")
        return self.grade(Path(args.table), differential=args.differential)


class SurfaceTables(SimpleNamespace):
    """Source-anchored maps and baseline/alternative spike evidence."""

    def _root(self, override: str | None) -> pathlib.Path:
        if override:
            return pathlib.Path(override).resolve()
        here = pathlib.Path(self.source_path).resolve()
        for candidate in (here, *here.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
        raise SystemExit("cannot locate repository root by upward pyproject.toml search")

    def _stub(self, kind: str) -> dict[str, Any]:
        if kind == "map":
            rows = [
                {
                    "id": rid,
                    "locus": locus,
                    **{f: self.UNKNOWN for f in self.MAP_FIELDS},
                    "main_verdict": self.UNKNOWN,
                }
                for rid, locus in self.MAP_SEED
            ]
            return {"kind": "map", "rows": rows}
        rows = [
            {
                "id": rid,
                "locus": locus,
                **{f: self.UNKNOWN for f in self.SPIKE_FIELDS},
                "main_verdict": self.UNKNOWN,
            }
            for rid, locus in self.SPIKE_SEED
        ]
        return {"kind": "spike", **{f: self.UNKNOWN for f in self.SPIKE_HEADER}, "rows": rows}

    def _load(self, path: pathlib.Path) -> dict[str, Any]:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"unreadable artifact: {exc}")
        if type(document) is not dict:
            raise SystemExit("artifact must be a JSON object")
        return document

    def _check_anchor(self, root: pathlib.Path, anchor: str, symbol: str) -> str | None:
        match = re.fullmatch("([^:]+):(\\d+)", anchor.strip())
        if match is None:
            return f"anchor {anchor!r} is not path:line"
        target = root / match.group(1)
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except OSError:
            return f"anchor path {match.group(1)!r} does not resolve"
        index = int(match.group(2))
        if not 1 <= index <= len(lines):
            return f"anchor {anchor!r} is past end of file ({len(lines)} lines)"
        token = symbol.strip().strip("`")
        if token and token not in lines[index - 1]:
            return f"symbol {token!r} is absent from {anchor}"
        return None

    def validate(self, path: pathlib.Path, root: pathlib.Path) -> int:
        document = self._load(path)
        kind = document.get("kind")
        if kind not in ("map", "spike"):
            raise SystemExit("kind must be 'map' or 'spike'")
        seed = self.MAP_SEED if kind == "map" else self.SPIKE_SEED
        fields = self.MAP_FIELDS if kind == "map" else self.SPIKE_FIELDS
        extension = "X" if kind == "map" else "Y"
        rows = document.get("rows")
        if type(rows) is not list or not rows:
            raise SystemExit("rows must be a non-empty array")
        problems: list[str] = []
        unknown = 0
        anchors_bad = 0
        deltas = 0
        if kind == "spike":
            for name in self.SPIKE_HEADER:
                value = document.get(name, self.UNKNOWN)
                if type(value) is not str or value.strip() in ("", self.UNKNOWN):
                    unknown += 1
                    continue
                if name == "head_sha" and re.fullmatch("[0-9a-f]{7,40}", value.strip()) is None:
                    problems.append(f"head_sha {value!r} is not a git object name")
                if name == "diff_stat":
                    stat = re.fullmatch("\\+(\\d+)/-(\\d+)", value.strip())
                    if stat is None:
                        problems.append(f"diff_stat {value!r} must read +N/-M")
                    elif int(stat.group(1)) < self.ADDITIONS_FLOOR:
                        problems.append(
                            f"diff_stat additions {stat.group(1)} < {self.ADDITIONS_FLOOR}: this alternative was never implemented"
                        )
                if name == "driver" and (not (root / value.strip()).is_file()):
                    problems.append(f"driver {value!r} does not resolve under the root")
        seen: list[str] = []
        for row in rows:
            if type(row) is not dict:
                problems.append("every row must be an object")
                continue
            rid = str(row.get("id", "")).strip()
            seen.append(rid)
            if not re.fullmatch(f"(?:M|Z|{extension})\\d{{2,3}}", rid):
                problems.append(f"row id {rid!r} is not a seeded or extension id")
            if "locus" not in row or not str(row.get("locus", "")).strip():
                problems.append(f"{rid}: locus must name the row's subject")
            for name in fields:
                value = row.get(name, self.UNKNOWN)
                if type(value) is not str or value.strip() in ("", self.UNKNOWN):
                    unknown += 1
                    continue
                text = value.strip()
                if name in ("finding", "bearing", "delta") and len(text) < self.PROSE_FLOOR:
                    problems.append(f"{rid}.{name}: {len(text)} chars < {self.PROSE_FLOOR}")
                if name == "verdict" and text.split(":")[0].strip() not in self.VERDICTS:
                    problems.append(f"{rid}.verdict must open with one of {self.VERDICTS}")
            if kind == "map":
                anchor = str(row.get("anchor", self.UNKNOWN)).strip()
                symbol = str(row.get("symbol", self.UNKNOWN)).strip()
                if self.UNKNOWN not in (anchor, symbol) and anchor and symbol:
                    reason = self._check_anchor(root, anchor, symbol)
                    if reason is not None:
                        anchors_bad += 1
                        problems.append(f"{rid}: {reason}")
            else:
                baseline = str(row.get("baseline", self.UNKNOWN)).strip()
                alt = str(row.get("alt", self.UNKNOWN)).strip()
                if self.UNKNOWN not in (baseline, alt) and baseline != alt:
                    deltas += 1
        missing = [rid for rid, _ in seed if rid not in seen]
        if missing:
            problems.append(f"seeded ids absent: {', '.join(missing)}")
        duplicates = sorted({rid for rid in seen if seen.count(rid) > 1})
        if duplicates:
            problems.append(f"duplicate ids: {', '.join(duplicates)}")
        if kind == "spike" and unknown == 0 and (deltas < self.DELTA_FLOOR):
            problems.append(
                f"only {deltas} rows separate baseline from alt (floor {self.DELTA_FLOOR}): a corpus answerable against baseline alone forces no implementation"
            )
        print(f"KIND: {kind}")
        print(f"ROWS: {len(rows)} ({len(seed)} seeded, {len(rows) - len(seed)} extension)")
        print(f"UNKNOWN-CELLS: {unknown}")
        print(f"EXEMPT-FIELDS: {', '.join(self.EXEMPT)} (MAIN-owned; never graded here)")
        if kind == "map":
            print(f"ANCHORS-BAD: {anchors_bad}")
        else:
            print(f"DELTA-ROWS: {deltas}")
        for problem in problems:
            print(f"PROBLEM: {problem}")
        if unknown or problems:
            print("FAIL")
            return 1
        print("PASS")
        return 0

    def main(self) -> int:
        parser = argparse.ArgumentParser(description=self.documentation)
        parser.add_argument("artifact", nargs="?")
        parser.add_argument("--emit-stub", choices=("map", "spike"))
        parser.add_argument("--root")
        args = parser.parse_args()
        if args.emit_stub:
            print(json.dumps(self._stub(args.emit_stub), ensure_ascii=False, indent=2))
            return 0
        if not args.artifact:
            parser.error("give an artifact path or --emit-stub")
        return self.validate(pathlib.Path(args.artifact), self._root(args.root))


class AttackTable(SimpleNamespace):
    """Contract-attack rows reported as independent defect counters."""

    def _contract_ids(self, root: pathlib.Path) -> set[str]:
        lines = (
            (root / ".agent" / "decisions" / self.CONTRACT_NAME)
            .read_text(encoding="utf-8")
            .splitlines()
        )
        found = {match.group(1) for line in lines if (match := self.OBLIGATION.match(line))}
        found |= {match.group(1) for line in lines if (match := self.CORRECTION.match(line))}
        return found | set(self.EXTRA_ANCHORS)

    def emit_seed(self, root: pathlib.Path) -> str:
        rows = [
            {
                "id": row_id,
                "section": section,
                "locus": locus,
                "claim": self.UNKNOWN,
                "attack": self.UNKNOWN,
                "reproduction": self.UNKNOWN,
                "severity": self.UNKNOWN,
                "verdict": self.UNKNOWN,
                "disposition": self.UNKNOWN,
                "main_note": self.UNKNOWN,
            }
            for row_id, section, locus in self.SEED
        ]
        document = {
            "unit": "M3.6a1",
            "artifact": "contract attack + evasion matrix",
            "seeded_rows": len(rows),
            "rows": rows,
        }
        return json.dumps(document, indent=2, ensure_ascii=False) + "\n"

    def grade(self, table: pathlib.Path, root: pathlib.Path) -> int:
        if not table.exists():
            print(f"ABSENT: {table}")
            print("RESULT: FAIL")
            return 1
        try:
            document = json.loads(table.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"MALFORMED: {error}")
            print("RESULT: FAIL")
            return 1
        rows = document.get("rows", [])
        anchors = self._contract_ids(root)
        unknown_cells: list[str] = []
        unresolved: list[str] = []
        bad_severity: list[str] = []
        short_attack: list[str] = []
        unreproduced: list[str] = []
        duplicates: list[str] = []
        bad_id: list[str] = []
        seen: set[str] = set()
        for row in rows:
            row_id = str(row.get("id", "?"))
            if row_id in seen:
                duplicates.append(row_id)
            seen.add(row_id)
            if not re.fullmatch("[AY]\\d{2,}", row_id):
                bad_id.append(row_id)
            for field in self.TEAMMATE_FIELDS:
                value = str(row.get(field, "")).strip()
                if not value or value == self.UNKNOWN:
                    unknown_cells.append(f"{row_id}.{field}")
            if str(row.get("section", "")) not in anchors:
                unresolved.append(f"{row_id}:{row.get('section')}")
            if str(row.get("severity", "")) not in self.SEVERITIES:
                bad_severity.append(f"{row_id}:{row.get('severity')}")
            attack = str(row.get("attack", ""))
            if attack != self.UNKNOWN and len(attack) < self.MIN_ATTACK_CHARS:
                short_attack.append(row_id)
            repro = str(row.get("reproduction", ""))
            if repro != self.UNKNOWN and len(repro) < self.MIN_REPRO_CHARS:
                unreproduced.append(row_id)
        seeded = {row_id for row_id, _, _ in self.SEED}
        dropped = sorted(seeded - seen)
        print(
            f"ROWS: {len(rows)} (seed {len(self.SEED)}, extension {max(0, len(rows) - len(self.SEED))})"
        )
        print(f"UNKNOWN-CELLS: {len(unknown_cells)} {sorted(unknown_cells)[:8]}")
        print(f"SEED-DROPPED: {len(dropped)} {dropped}")
        print(f"UNRESOLVED-SECTION: {len(unresolved)} {sorted(unresolved)}")
        print(f"BAD-SEVERITY: {len(bad_severity)} {sorted(bad_severity)}")
        print(f"BAD-ID: {len(bad_id)} {sorted(bad_id)}")
        print(f"DUPLICATE-ID: {len(duplicates)} {sorted(duplicates)}")
        print(f"SHORT-ATTACK: {len(short_attack)} {sorted(short_attack)}")
        print(f"UNREPRODUCED: {len(unreproduced)} {sorted(unreproduced)}")
        failures = (
            len(unknown_cells)
            + len(dropped)
            + len(unresolved)
            + len(bad_severity)
            + len(bad_id)
            + len(duplicates)
            + len(short_attack)
            + len(unreproduced)
        )
        print(f"RESULT: {('PASS' if failures == 0 else 'FAIL')}")
        return 0 if failures == 0 else 1

    def _fill(self, seed: str) -> str:
        document = json.loads(seed)
        for row in document["rows"]:
            row["claim"] = "the contract asserts X at this locus"
            row["attack"] = "a" * (self.MIN_ATTACK_CHARS + 10)
            row["reproduction"] = "b" * (self.MIN_REPRO_CHARS + 10)
            row["severity"] = "cleared"
            row["verdict"] = "holds"
        return json.dumps(document, indent=2, ensure_ascii=False) + "\n"

    def _run(self, root: pathlib.Path, table: pathlib.Path) -> tuple[int, str]:
        result = subprocess.run(
            [
                sys.executable,
                str(self.HERE / pathlib.Path(self.source_path).name),
                "--table",
                str(table),
                "--root",
                str(root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return (result.returncode, result.stdout)

    def self_test(self) -> int:
        failures = 0
        with tempfile.TemporaryDirectory() as raw:
            stage = pathlib.Path(raw)
            decisions = stage / ".agent" / "decisions"
            decisions.mkdir(parents=True)
            shutil.copy2(
                self.ROOT / ".agent" / "decisions" / self.CONTRACT_NAME,
                decisions / self.CONTRACT_NAME,
            )
            table = stage / self.TABLE_RELPATH
            seed = self.emit_seed(stage)
            filled = self._fill(seed)

            def check(label: str, text: str, expect_rc: int, expect: list[str]) -> None:
                nonlocal failures
                table.write_text(text, encoding="utf-8")
                code, out = self._run(stage, table)
                ok = code == expect_rc and all((line in out for line in expect))
                print(f"{('OK  ' if ok else 'FAIL')} {label}: rc={code} expect={expect_rc}")
                if not ok:
                    failures += 1
                    print(out)

            check(
                "seed graded red",
                seed,
                1,
                [
                    f"UNKNOWN-CELLS: {len(self.SEED) * len(self.TEAMMATE_FIELDS) - 2 * len(self.SEED)}"
                ],
            )
            check("filled graded green", filled, 0, ["RESULT: PASS", "SEED-DROPPED: 0"])

            def mutate(fn) -> str:
                document = json.loads(filled)
                fn(document)
                return json.dumps(document, indent=2, ensure_ascii=False) + "\n"

            check(
                "control dropped seed row -> SEED-DROPPED",
                mutate(lambda d: d["rows"].pop(0)),
                1,
                ["SEED-DROPPED: 1"],
            )
            check(
                "control unresolvable section -> UNRESOLVED-SECTION",
                mutate(lambda d: d["rows"][0].__setitem__("section", "D99")),
                1,
                ["UNRESOLVED-SECTION: 1"],
            )
            check(
                "control bad severity -> BAD-SEVERITY",
                mutate(lambda d: d["rows"][0].__setitem__("severity", "critical")),
                1,
                ["BAD-SEVERITY: 1"],
            )
            check(
                "control short attack -> SHORT-ATTACK",
                mutate(lambda d: d["rows"][0].__setitem__("attack", "too short")),
                1,
                ["SHORT-ATTACK: 1"],
            )
            check(
                "control empty reproduction -> UNREPRODUCED",
                mutate(lambda d: d["rows"][0].__setitem__("reproduction", "ran it")),
                1,
                ["UNREPRODUCED: 1"],
            )
            check(
                "control blanked cell -> UNKNOWN-CELLS",
                mutate(lambda d: d["rows"][0].__setitem__("verdict", "")),
                1,
                ["UNKNOWN-CELLS: 1"],
            )
            check(
                "control duplicate id -> DUPLICATE-ID",
                mutate(lambda d: d["rows"].append(dict(d["rows"][0]))),
                1,
                ["DUPLICATE-ID: 1"],
            )
            check(
                "control bad extension id -> BAD-ID",
                mutate(lambda d: d["rows"].append({**d["rows"][0], "id": "Z1"})),
                1,
                ["BAD-ID: 1"],
            )
            check("control malformed table -> FAIL", "{not json", 1, ["MALFORMED", "RESULT: FAIL"])
            table.unlink()
            code, out = self._run(stage, table)
            ok = code == 1 and "ABSENT" in out
            print(f"{('OK  ' if ok else 'FAIL')} control absent table -> ABSENT: rc={code}")
            if not ok:
                failures += 1
        print(
            f"SELF-TEST: {('PASS' if failures == 0 else 'FAIL')} ({failures} control(s) not firing)"
        )
        return 0 if failures == 0 else 1

    def main(self, argv: list[str]) -> int:
        parser = argparse.ArgumentParser(description=self.documentation)
        parser.add_argument("--emit-seed", action="store_true")
        parser.add_argument("--self-test", action="store_true")
        parser.add_argument("--table", type=pathlib.Path, default=None)
        parser.add_argument("--root", type=pathlib.Path, default=None)
        args = parser.parse_args(argv)
        root = (args.root or self.ROOT).resolve()
        if args.self_test:
            return self.self_test()
        if args.emit_seed:
            sys.stdout.write(self.emit_seed(root))
            return 0
        table = args.table or root / self.TABLE_RELPATH
        return self.grade(table.resolve(), root)


class ContractTables(SimpleNamespace):
    """Citation-resolving verdict/attack tables with per-field prose floors."""

    def _contract_text(self) -> str:
        return self.CONTRACT.read_text(encoding="utf-8")

    def contract_tokens(self, text: str) -> set[str]:
        return set(re.findall("[A-Za-z0-9_-]+", text))

    def contract_sections(self, text: str) -> set[str]:
        return set(re.findall("^## (\\d{1,2})\\.", text, flags=re.MULTILINE))

    def contract_gates(self, text: str) -> set[str]:
        """Gate ids are the numbered list under section 6, so `G7` resolves only while gate 7 exists."""
        block = re.search(
            rf"^## {self.gate_section}\..*?(?=^## \d)", text, flags=re.MULTILINE | re.DOTALL
        )
        return (
            set(re.findall("^(\\d+)\\. ", block.group(0), flags=re.MULTILINE)) if block else set()
        )

    def emit_stub(self, kind: str) -> str:
        seed = self.VERDICT_SEED if kind == "verdicts" else self.ATTACK_SEED
        rows = []
        for identifier, section, subject in seed:
            if kind == "verdicts":
                rows.append(
                    {
                        "id": identifier,
                        "section": section,
                        "locus": subject,
                        "probe": self.UNKNOWN,
                        "reading": self.UNKNOWN,
                        "baseline": self.UNKNOWN,
                        "expected": self.UNKNOWN,
                        "divergent": self.UNKNOWN,
                        "main_verdict": None,
                        "action": None,
                    }
                )
            else:
                rows.append(
                    {
                        "id": identifier,
                        "section": section,
                        "lens": subject,
                        "attack": self.UNKNOWN,
                        "evidence": self.UNKNOWN,
                        "severity": self.UNKNOWN,
                        "disposition": None,
                        "main_note": None,
                    }
                )
        document = {
            "kind": kind,
            "unit": self.unit,
            "note": self.seed_note.format(
                extensions="X01, X02, ..." if kind == "verdicts" else "Y01, Y02, ..."
            ),
            "rows": rows,
        }
        return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    def grade(self, path: pathlib.Path) -> list[str]:
        findings: list[str] = []
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [f"UNREADABLE: {exc}"]
        kind = document.get("kind")
        if kind not in self.FIELDS:
            return [f"BAD-KIND: {kind!r} is not verdicts or attack"]
        rows = document.get("rows")
        if not isinstance(rows, list) or not rows:
            return ["NO-ROWS: rows must be a non-empty list"]
        text = self._contract_text()
        tokens = self.contract_tokens(text)
        sections = self.contract_sections(text)
        gates = self.contract_gates(text)
        seed = self.VERDICT_SEED if kind == "verdicts" else self.ATTACK_SEED
        seen: set[str] = set()
        unknown_cells = 0
        concrete_rows = 0
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                findings.append(f"row {index}: not an object")
                continue
            identifier = str(row.get("id", ""))
            if not self.ROW_ID[kind].match(identifier):
                findings.append(
                    f"row {index}: id {identifier!r} must match {self.ROW_ID[kind].pattern}"
                )
                continue
            if identifier in seen:
                findings.append(f"{identifier}: duplicate id")
            seen.add(identifier)
            for field in self.FIELDS[kind]:
                if field not in row:
                    findings.append(f"{identifier}: missing field {field}")
                    continue
                value = row[field]
                if not isinstance(value, str) or not value.strip():
                    findings.append(f"{identifier}.{field}: must be a non-empty string")
                    continue
                if value.strip().lower() == self.UNKNOWN:
                    unknown_cells += 1
                    continue
                floor = self.MIN_PROSE.get(field)
                if floor is not None and len(value.strip()) < floor:
                    findings.append(
                        f"{identifier}.{field}: {len(value.strip())} chars, floor {floor}"
                    )
            citation = str(row.get("section", "")).strip()
            if citation and citation.lower() != self.UNKNOWN:
                for element in (part.strip() for part in citation.split(",")):
                    head = element.split()[0] if element.split() else ""
                    if not self.CITATION.match(head):
                        findings.append(f"{identifier}.section: {head!r} is not a citation form")
                    elif head.startswith("S"):
                        if head[1:] not in sections:
                            findings.append(
                                f"{identifier}.section: contract has no section {head[1:]}"
                            )
                    elif self.gate_section is not None and head.startswith("G"):
                        if head[1:] not in gates:
                            findings.append(
                                f"{identifier}.section: contract has no gate {head[1:]}"
                            )
                    elif head not in tokens:
                        findings.append(
                            f"{identifier}.section: {head} resolves nowhere in the contract"
                        )
            if kind == "verdicts":
                divergent = str(row.get("divergent", "")).strip().lower()
                if divergent not in (self.UNKNOWN, "yes", "no"):
                    findings.append(f"{identifier}.divergent: {divergent!r} must be yes or no")
                expected = str(row.get("expected", ""))
                if expected.strip().lower() != self.UNKNOWN and self.CONCRETE.search(expected):
                    concrete_rows += 1
                elif expected.strip().lower() != self.UNKNOWN:
                    findings.append(
                        f"{identifier}.expected: names no concrete observable (exit code, quoted string, key set, or number)"
                    )
            else:
                severity = str(row.get("severity", "")).strip().lower()
                if severity not in (self.UNKNOWN, *self.SEVERITY):
                    findings.append(
                        f"{identifier}.severity: {severity!r} must be one of {self.SEVERITY}"
                    )
        missing = [identifier for identifier, _, _ in seed if identifier not in seen]
        if missing:
            findings.append(f"SEED-ROWS-MISSING: {', '.join(missing)}")
        print(f"KIND: {kind}")
        print(f"ROWS: {len(rows)} ({len(seed)} seeded, {len(rows) - len(seed)} extension)")
        print(f"UNKNOWN-CELLS: {unknown_cells}")
        print(f"EXEMPT-COLUMNS (MAIN-owned, NOT graded): {', '.join(self.EXEMPT[kind])}")
        if kind == "verdicts":
            print(f"CONCRETE-EXPECTATIONS: {concrete_rows}")
        if unknown_cells:
            findings.append(f"UNFILLED: {unknown_cells} cells still read unknown")
        return findings

    def self_test(self) -> int:
        """Grade the grader both ways on a temporary file: the stub FAILS, a filled copy PASSES."""
        import contextlib
        import io
        import tempfile

        silent: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            for kind in ("verdicts", "attack"):
                path = pathlib.Path(directory) / f"{kind}.json"
                path.write_text(self.emit_stub(kind), encoding="utf-8")
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    stub_findings = self.grade(path)
                if not any((f.startswith("UNFILLED") for f in stub_findings)):
                    silent.append(f"{kind}: the all-unknown stub did not report UNFILLED")
                document = json.loads(path.read_text(encoding="utf-8"))
                for row in document["rows"]:
                    for field in self.FIELDS[kind]:
                        if row.get(field) == self.UNKNOWN:
                            row[field] = (
                                "exit 0 and the key set `{a, b}` filled to clear the floor of characters"
                                if field == "expected"
                                else "no"
                                if field == "divergent"
                                else "cleared"
                                if field == "severity"
                                else "filled placeholder text long enough to clear every prose floor here"
                            )
                path.write_text(json.dumps(document), encoding="utf-8")
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    filled_findings = self.grade(path)
                if filled_findings:
                    silent.append(f"{kind}: a filled table reported {filled_findings}")
                broken = json.loads(path.read_text(encoding="utf-8"))
                broken["rows"][0]["section"] = "L99"
                path.write_text(json.dumps(broken), encoding="utf-8")
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    cited = self.grade(path)
                if not any(("resolves nowhere" in f for f in cited)):
                    silent.append(f"{kind}: an unresolvable citation was accepted")
                dropped = json.loads(path.read_text(encoding="utf-8"))
                dropped["rows"] = dropped["rows"][1:]
                path.write_text(json.dumps(dropped), encoding="utf-8")
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    missing = self.grade(path)
                if not any((f.startswith("SEED-ROWS-MISSING") for f in missing)):
                    silent.append(f"{kind}: a dropped seed row was accepted")
        for line in silent:
            print(f"SILENT: {line}")
        print(f"CONTROLS: {8 - len(silent)}/8 firing")
        return 1 if silent else 0

    def main(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(description=f"grade an {self.unit} wave-2 table")
        parser.add_argument("path", nargs="?")
        parser.add_argument("--emit-stub", choices=("verdicts", "attack"))
        if self.has_self_test:
            parser.add_argument("--self-test", action="store_true")
        args = parser.parse_args(argv)
        if self.has_self_test and args.self_test:
            return self.self_test()
        if args.emit_stub:
            sys.stdout.write(self.emit_stub(args.emit_stub))
            return 0
        if not args.path:
            parser.error("a table path is required unless --emit-stub is given")
        findings = self.grade(pathlib.Path(args.path))
        for finding in findings:
            print(finding)
        print("PASS" if not findings else f"FAIL ({len(findings)} findings)")
        return 1 if findings else 0
