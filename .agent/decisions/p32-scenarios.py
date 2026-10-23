#!/usr/bin/env python3
"""Contract-derived p32 corpus. Baseline behavior is the oracle, not a retyped answer table."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import dataclasses
import hashlib
import inspect
import itertools
import json
from pathlib import Path
import random
import shutil
import sqlite3
import tempfile
from unittest.mock import patch

from cement_runtime import Candidate, CompilePolicy, System
import cement_runtime.system as runtime


PARTITION = "tenant_a"
OPERATION = "answer"
ZERO = "0" * 64
PROGRAM = {
    "abi": "cement-projection-v1", "text": "document", "keep": ["fields"],
    "layouts": [{"name": "visit", "title": "VISIT", "entries": [
        {"label": "Patient"}, {"label": "Number"},
    ]}],
}
PROGRAM_TWO = {
    **PROGRAM,
    "layouts": [*PROGRAM["layouts"], {"name": "lab", "title": "LAB", "entries": [
        {"label": "Patient"}, {"label": "Result"},
    ]}],
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def jsonable(value):
    if dataclasses.is_dataclass(value):
        if type(value).__name__ == "FunctionVerification":
            return {
                "passed": value.passed, "entries": value.entries,
                "function_hash": value.function_hash,
                "checks": [dataclasses.asdict(check) for check in value.checks],
                "document_sha256": digest(value.document.text) if value.document else None,
            }
        return jsonable(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unserialized observable: {type(value).__name__}")


class Counters:
    def __init__(self):
        self.ids = 0
        self.time = 10_000_000

    def new_id(self, prefix):
        self.ids += 1
        # Reverse lexical order deliberately disagrees with arrival/sequence order.
        return f"{prefix}_{1_000_000 - self.ids:032x}"

    def clock(self):
        self.time += 1_000_000
        return self.time


class Fixture:
    def __init__(self, directory):
        self.path = directory / "seed.db"
        self.counters = Counters()
        self.system = System(self.path, clock_us=self.counters.clock)
        self.system.register_operation(PARTITION, OPERATION)
        self.artifacts = []
        self.reports = {}
        self.inputs = []
        self.receipt = None
        self.function_hash = ZERO
        self.scope_hashes = {}
        self.mode = None

    def confirmed(self, input_value, output, *, count=2):
        for _ in range(count):
            proposal = self.system.submit_proposal(
                PARTITION, OPERATION, input_value,
                candidate=Candidate(output, {"model": "deterministic-corpus"}),
                source_id=f"source:{self.counters.ids + 1}",
            )
            self.system.review(PARTITION, proposal, reviewer="learning-pass", decision="accept")
        if input_value not in self.inputs:
            self.inputs.append(input_value)

    def pending(self, input_value, output):
        return self.system.submit_proposal(
            PARTITION, OPERATION, input_value, candidate=Candidate(output, {"pending": True}),
            source_id=f"pending:{self.counters.ids + 1}",
        )

    def build(self, *, verify=True, promote=False):
        result = self.system.compile(PARTITION, OPERATION, compiled_by="learning-pass")
        self.artifacts.extend(a for a in result.created if a not in self.artifacts)
        if verify:
            self.system.verify_drafts(PARTITION, OPERATION, verified_by="learning-pass")
        self.refresh()
        if promote:
            manifest = self.system.inspect_function_promotion(PARTITION, OPERATION)
            result = self.system.promote_function(
                PARTITION, OPERATION, expected_function_hash=manifest.function_hash,
                promoted_by="learning-pass",
            )
            self.receipt = result.receipt_id
            self.function_hash = result.function_hash
        return result

    def refresh(self):
        with sqlite3.connect(self.path) as connection:
            for row in connection.execute("SELECT id, scope_hash, verified_report_id FROM artifacts ORDER BY sequence"):
                if row[0] not in self.artifacts:
                    self.artifacts.append(row[0])
                self.scope_hashes[row[0]] = row[1]
                if row[2]:
                    self.reports[row[0]] = row[2]

    def corrupt(self, mutations):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            original = [(row["name"], row["sql"]) for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY rowid"
            )]
            for name, _ in original:
                connection.execute(f'DROP TRIGGER "{name}"')
            for sql, values in mutations:
                cursor = connection.execute(sql, values)
                if cursor.rowcount <= 0:
                    raise AssertionError(f"corruption touched no rows: {sql}")
            for _, sql in original:
                connection.execute(sql)
            restored = [(row["name"], row["sql"]) for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY rowid"
            )]
            if original != restored:
                raise AssertionError("trigger DDL/order changed")
        # Reopen, exactly as a fresh process would; no schema-check bypass.
        self.system = System(self.path, clock_us=self.counters.clock)

    def update(self, table, key, row_id, **values):
        assignments = ", ".join(f'"{name}"=?' for name in values)
        self.corrupt([(f'UPDATE "{table}" SET {assignments} WHERE "{key}"=?',
                       (*values.values(), row_id))])

    def report_details(self, artifact_id, details):
        text = canonical(details)
        self.update("test_reports", "id", self.reports[artifact_id],
                    details_json=text, details_hash=digest(text))

    def clone(self, directory):
        target = directory / "probe.db"
        shutil.copyfile(self.path, target)
        counters = Counters()
        counters.ids, counters.time = self.counters.ids, self.counters.time
        return target, counters


def ledger(path):
    with sqlite3.connect(path) as connection:
        rows = {}
        for (table,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            content = connection.execute(f'SELECT * FROM "{table}"').fetchall()
            normalized = sorted(canonical(list(row)) for row in content)
            rows[table] = {"count": len(content), "sha256": digest("\n".join(normalized))}
        return {"tables": rows, "dump_sha256": digest("\n".join(connection.iterdump()))}


@contextmanager
def injected(mode):
    if mode is None:
        yield
    elif mode.startswith("capacity-"):
        with patch.object(runtime, "FUNCTION_MAX_ENTRIES", int(mode.split("-")[1])):
            yield
    elif mode in {"replay", "boundary", "structural"}:
        original_execute = runtime.execute
        original_project = runtime.project
        def execute(artifact, **kwargs):
            result = original_execute(artifact, **kwargs)
            if mode == "replay" and result.matched:
                return dataclasses.replace(result, output={"mutated": "replay"})
            if mode == "boundary" and not result.matched:
                return dataclasses.replace(result, matched=True, output=artifact.output.value)
            return result
        def project(program, value):
            result = original_project(program, value)
            if mode == "structural" and not result.matched and isinstance(value, dict):
                repaired = dict(value)
                repaired["document"] = str(repaired.get("document", "")) + "\nNumber: repaired"
                return original_project(program, repaired)
            return result
        with patch.object(runtime, "execute", execute), patch.object(runtime, "project", project):
            yield
    else:
        raise AssertionError(f"unrecognized injected boundary: {mode}")


class Recorder:
    def __init__(self, scenario):
        self.scenario = scenario
        self.counter = itertools.count(1)

    def probe(self, fixture, name, call, *, mode=None):
        probe = f"{self.scenario}.{next(self.counter)}.{name}"
        with tempfile.TemporaryDirectory(prefix="p32-probe-") as temporary:
            path, counters = fixture.clone(Path(temporary))
            record = {"probe": probe}
            # The outcome record exists before the call; exceptions are observable outcomes.
            with patch.object(runtime, "_new_id", counters.new_id), injected(mode or fixture.mode):
                try:
                    system = System(path, clock_us=counters.clock)
                    record["result"] = jsonable(call(system))
                except Exception as exc:
                    record["raises"] = [type(exc).__name__, str(exc)]
            # Preserve returned mapping order as well as list order and all scalar bytes.
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)
            state = ledger(path)
            state["calls"] = {
                "ids": counters.ids - fixture.counters.ids,
                "clock": (counters.time - fixture.counters.time) // 1_000_000,
            }
            print(json.dumps({"probe": f"{probe}.ledger", "result": state},
                             ensure_ascii=False, separators=(",", ":")), flush=True)

    def sweep(self, fixture, label, *, all_artifacts=False):
        p, o = PARTITION, OPERATION
        self.probe(fixture, label + ".verify_function", lambda s: s.verify_function(p, o))
        self.probe(fixture, label + ".verify_function.expected", lambda s: s.verify_function(p, o, expected_function_hash=fixture.function_hash))
        for limit in (1, 2, None):
            def report(s, limit=limit):
                kwargs = {} if limit is None else {"projection_limit": limit}
                return s.function_report(p, o, **kwargs)
            self.probe(fixture, label + f".function_report.{limit}", report)
        self.probe(fixture, label + ".latest_function_receipt", lambda s: s.latest_function_receipt(p, o))
        if fixture.receipt:
            self.probe(fixture, label + ".reconstruct_function_receipt", lambda s: s.reconstruct_function_receipt(p, fixture.receipt))
            self.probe(fixture, label + ".function_report.receipt", lambda s: s.function_report(p, o, receipt_id=fixture.receipt))
        for switch_mode in ("off", "follow", "pinned"):
            if switch_mode == "pinned" and not fixture.receipt:
                continue
            # Select modes without letting set_switch admission mask the corrupt read path.
            with tempfile.TemporaryDirectory(prefix="p32-switch-") as temporary:
                saved = Path(temporary) / "seed.db"
                shutil.copyfile(fixture.path, saved)
                ids, time = fixture.counters.ids, fixture.counters.time
                try:
                    with sqlite3.connect(fixture.path) as db:
                        setting = db.execute("SELECT id FROM switch_settings ORDER BY sequence DESC LIMIT 1").fetchone()
                        receipt = db.execute("SELECT function_hash FROM function_receipts WHERE id=?", (fixture.receipt,)).fetchone()
                        selected_hash = receipt[0] if receipt else fixture.function_hash
                    if setting:
                        fixture.update("switch_settings", "id", setting[0],
                                       mode=switch_mode,
                                       receipt_id=fixture.receipt if switch_mode == "pinned" else None,
                                       function_hash=selected_hash if switch_mode == "pinned" else None)
                    else:
                        fixture.system.set_switch(p, o, mode=switch_mode, actor="operator",
                                                  function_hash=selected_hash if switch_mode == "pinned" else None)
                    for suffix, value in (("hit", fixture.inputs[0] if fixture.inputs else {"case": 11}),
                                          ("miss", {"case": "absent"})):
                        self.probe(fixture, label + f".resolve.{switch_mode}.{suffix}",
                                   lambda s, value=value: s.resolve(p, o, value))
                finally:
                    shutil.copyfile(saved, fixture.path)
                    fixture.counters.ids, fixture.counters.time = ids, time
                    fixture.system = System(fixture.path, clock_us=fixture.counters.clock)
        self.probe(fixture, label + ".inspect_function_promotion", lambda s: s.inspect_function_promotion(p, o))
        self.probe(fixture, label + ".promote_function", lambda s: s.promote_function(p, o, expected_function_hash=fixture.function_hash, promoted_by="learning-pass"))
        def promote_current(s):
            manifest = s.inspect_function_promotion(p, o)
            return s.promote_function(p, o, expected_function_hash=manifest.function_hash, promoted_by="learning-pass")
        self.probe(fixture, label + ".promote_function.current", promote_current)
        self.probe(fixture, label + ".verify_drafts", lambda s: s.verify_drafts(p, o, verified_by="learning-pass"))
        self.probe(fixture, label + ".compile", lambda s: s.compile(p, o, compiled_by="learning-pass"))
        self.probe(fixture, label + ".learning_cases.current", lambda s: s.learning_cases(p, o))
        self.probe(fixture, label + ".learning_cases.candidate", lambda s: s.learning_cases(p, o, program=PROGRAM))
        self.probe(fixture, label + ".test_projection", lambda s: s.test_projection(p, o, PROGRAM))
        artifacts = fixture.artifacts if all_artifacts else fixture.artifacts[:1]
        for index, artifact in enumerate(artifacts):
            self.probe(fixture, label + f".verify.{index}", lambda s, artifact=artifact: s.verify(p, artifact, verified_by="learning-pass"))
            self.probe(fixture, label + f".promote.{index}", lambda s, artifact=artifact: s.promote(p, artifact, scope_hash=fixture.scope_hashes[artifact], promoted_by="learning-pass"))


@contextmanager
def fixture(*, count=3, promote=True, verify=True, forms=False):
    with tempfile.TemporaryDirectory(prefix="p32-fixture-") as directory:
        counters = Counters()
        with patch.object(runtime, "_new_id", counters.new_id):
            item = Fixture(Path(directory))
            # Construction's registration makes no id; all further calls share this counter.
            item.counters = counters
            item.system = System(item.path, clock_us=counters.clock)
            for index in range(count):
                value = form(index) if forms else {"case": 11 + index}
                output = {"answer": "layout"} if forms else {"answer": 11 + index}
                item.confirmed(value, output)
            if count:
                item.build(verify=verify, promote=promote)
            item.system.set_switch(PARTITION, OPERATION, mode="follow", actor="operator")
            yield item


def form(index):
    return {"document": f"VISIT\nPatient: person {index}\nNumber: {11 + index}", "fields": ["Patient", "Number"]}


def S01(recorder):
    with fixture() as item:
        recorder.sweep(item, "healthy", all_artifacts=True)
        public = ("verify_function", "resolve", "function_report", "reconstruct_function_receipt",
                  "latest_function_receipt", "inspect_function_promotion", "promote_function",
                  "promote", "verify", "verify_drafts", "compile", "learning_cases", "test_projection")
        recorder.probe(item, "public-signatures", lambda s: {name: str(inspect.signature(getattr(type(s), name))) for name in public})
        for index, invalid in enumerate((1.5, float("nan"), 2**63, -(2**63)-1, {1: "non-string key"})):
            recorder.probe(item, f"invalid-input.{index}", lambda s, invalid=invalid: s.resolve(PARTITION, OPERATION, invalid))
        for limit in (0, -1, True, "2"):
            recorder.probe(item, f"limit.{limit!r}", lambda s, limit=limit: s.function_report(PARTITION, OPERATION, projection_limit=limit))
        for partition, operation in (("tenantXa", OPERATION), ("Tenant_a", OPERATION), (PARTITION, "Answer"), (PARTITION, "absent")):
            recorder.probe(item, f"scope.{partition}.{operation}", lambda s, p=partition, o=operation: s.verify_function(p, o))
        recorder.probe(item, "expected.wrong", lambda s: s.verify_function(PARTITION, OPERATION, expected_function_hash=ZERO))
        recorder.probe(item, "expected.invalid", lambda s: s.verify_function(PARTITION, OPERATION, expected_function_hash="not-a-digest"))
        generated = [None, True, False, -(2**63), 2**63 - 1, "日本語", [], {}, [11, {"x": "é"}]]
        rng = random.Random(32033)
        generated.extend({"case": rng.randrange(-1000, 1000), "items": [rng.randrange(256) for _ in range(4)]} for _ in range(12))
        for index, value in enumerate(generated):
            recorder.probe(item, f"generated.{index}.resolve", lambda s, value=value: s.resolve(PARTITION, OPERATION, value))
    with fixture(count=0) as item:
        recorder.sweep(item, "empty")
        for value in generated:
            item.confirmed(value, {"answer": value})
        recorder.sweep(item, "uncompiled-examples")
        item.build(promote=True)
        recorder.sweep(item, "generated-promoted", all_artifacts=True)
        for index, value in enumerate(generated):
            recorder.probe(item, f"generated-hit.{index}.resolve", lambda s, value=value: s.resolve(PARTITION, OPERATION, value))


def policy_case(recorder, value, policy_hash=None):
    with fixture() as item:
        updates = {"policy_json": value}
        if policy_hash is not None:
            updates["policy_hash"] = policy_hash
        item.update("operations", "name", OPERATION, **updates)
        recorder.sweep(item, "policy")


def S02(recorder):
    policy_case(recorder, '{ "min_span_seconds":0, "min_confirmations":2, "min_reviewers":1 }', ZERO)


def S03(recorder):
    for value in ("[]", "null", '"policy"', "{malformed"):
        policy_case(recorder, value, digest(value))


def S04(recorder):
    for value in ({}, {"min_confirmations": 1, "min_reviewers": 1, "min_span_seconds": 0},
                  {"min_confirmations": 2, "min_reviewers": True, "min_span_seconds": 0},
                  {"min_confirmations": 2, "min_reviewers": 1, "min_span_seconds": -1}):
        text = canonical(value)
        policy_case(recorder, text, digest(text))


def S05(recorder):
    with fixture() as item:
        item.update("operations", "name", OPERATION, policy_hash=ZERO)
        recorder.sweep(item, "digest-only")


def S06(recorder):
    with fixture(count=7) as item:
        ids = item.artifacts
        item.update("artifacts", "id", ids[0], verified_report_id="report_absent")
        item.update("test_reports", "id", item.reports[ids[1]], passed=0)
        item.report_details(ids[2], {"scope_hash": ZERO, "tests": 8, "failures": [], "verified_by": "learning-pass"})
        item.update("test_reports", "id", item.reports[ids[3]], artifact_hash=ZERO)
        item.update("test_reports", "id", item.reports[ids[4]], build_hash=ZERO)
        item.update("artifacts", "id", ids[5], artifact_json="{")
        item.update("artifacts", "id", ids[6], operation_revision=2)
        recorder.sweep(item, "compound-seven", all_artifacts=True)
    for details in ([], {"scope_hash": ZERO}, {"scope_hash": "invalid"}):
        with fixture() as item:
            item.report_details(item.artifacts[-1], details)
            recorder.sweep(item, "details-shape")


def S07(recorder):
    for field, value in (("entry_seal", ZERO), ("input_hash", ZERO), ("ordinal", 11)):
        with fixture() as item:
            item.corrupt([(f"UPDATE function_memberships SET {field}=? WHERE receipt_id=? AND ordinal=2", (value, item.receipt))])
            recorder.sweep(item, f"membership-{field}")
    with fixture() as item:
        # Keep the composite FK valid; the self-bound receipt must reject this hash rewrite.
        item.corrupt([
            ("UPDATE function_memberships SET function_hash=? WHERE receipt_id=?", (ZERO, item.receipt)),
            ("UPDATE function_receipts SET function_hash=? WHERE id=?", (ZERO, item.receipt)),
        ])
        recorder.sweep(item, "membership-function-hash")
    with fixture() as item:
        item.corrupt([
            ("UPDATE function_memberships SET entry_seal=? WHERE receipt_id=? AND ordinal=0", (ZERO, item.receipt)),
            ("UPDATE function_memberships SET input_hash=? WHERE receipt_id=? AND ordinal=1", (ZERO, item.receipt)),
            ("UPDATE function_memberships SET ordinal=11 WHERE receipt_id=? AND ordinal=2", (item.receipt,)),
        ])
        recorder.sweep(item, "membership-compound")


def duplicate_draft(item, artifact):
    with sqlite3.connect(item.path) as db:
        db.row_factory = sqlite3.Row
        row = dict(db.execute("SELECT * FROM artifacts WHERE id=?", (artifact,)).fetchone())
    row.pop("sequence")
    row.update(id=item.counters.new_id("art"), status="draft", verified_report_id=None,
               promoted_by=None, promoted_at_us=None, promotion_hash=None, status_reason=None)
    columns = ",".join(f'"{name}"' for name in row)
    marks = ",".join("?" for _ in row)
    item.corrupt([(f"INSERT INTO artifacts ({columns}) VALUES ({marks})", tuple(row.values()))])
    item.system.verify(PARTITION, row["id"], verified_by="learning-pass")
    item.refresh()


def S08(recorder):
    with fixture(count=2, promote=False) as item:
        duplicate_draft(item, item.artifacts[0])
        recorder.sweep(item, "duplicate-candidates", all_artifacts=True)
    with fixture() as item:
        item.confirmed(item.inputs[1], {"answer": "contradiction"}, count=1)
        item.confirmed({"case": 30}, {"answer": "ineligible"}, count=1)
        recorder.sweep(item, "contradicted-retained")
    with fixture(count=2, forms=True) as item:
        item.confirmed({"document": "LAB\nPatient: A\nResult: 11", "fields": ["Patient", "Number"]}, {"answer": "lab"})
        item.build(promote=False)
        old = item.artifacts[-1]
        item.system.set_projection(PARTITION, OPERATION, PROGRAM_TWO, actor="learning-pass")
        item.build(promote=False)
        recorder.sweep(item, "program-transition", all_artifacts=True)
        # Legitimate setter retires old drafts; restore status to exercise a stale-program candidate.
        item.update("artifacts", "id", old, status="verified")
        item.update("artifacts", "id", item.artifacts[-1], build_hash=ZERO)
        recorder.sweep(item, "superseded-program-and-ineligible", all_artifacts=True)
    with fixture(count=2, forms=True) as item:
        item.system.set_projection(PARTITION, OPERATION, PROGRAM, actor="learning-pass")
        item.build(promote=True)
        old_projected = item.artifacts[-1]
        renamed_program = {**PROGRAM, "layouts": [{**PROGRAM["layouts"][0], "name": "same-key-new-program"}]}
        item.system.set_projection(PARTITION, OPERATION, renamed_program, actor="learning-pass")
        item.build(promote=False)
        item.update("artifacts", "id", old_projected, status="verified", promotion_hash=None)
        recorder.sweep(item, "superseded-program-candidate", all_artifacts=True)
    with fixture(count=3, promote=False) as item:
        item.update("artifacts", "id", item.artifacts[1], build_hash=ZERO)
        recorder.sweep(item, "ineligible-build")
        duplicate_draft(item, item.artifacts[0])
        recorder.sweep(item, "ineligible-and-duplicate")
    with fixture(count=2, forms=True) as item:
        item.system.set_projection(PARTITION, OPERATION, PROGRAM, actor="learning-pass")
        item.build(promote=True)
        old_projected = item.artifacts[-1]
        renamed_program = {**PROGRAM, "layouts": [{**PROGRAM["layouts"][0], "name": "compound-program"}]}
        item.system.set_projection(PARTITION, OPERATION, renamed_program, actor="learning-pass")
        item.build(promote=True)
        item.confirmed(form(20), {"answer": "contradiction"}, count=1)
        for index in range(3):
            value = {**form(30 + index), "fields": ["Patient", f"field-{index}"]}
            item.confirmed(value, {"answer": index})
        result = item.build(promote=False)
        candidates = list(result.created)
        if len(candidates) != 3:
            raise AssertionError("compound plan fixture did not create three candidates")
        duplicate_draft(item, candidates[0])
        item.update("artifacts", "id", candidates[-1], build_hash=ZERO)
        item.update("artifacts", "id", old_projected, status="verified", promotion_hash=None)
        recorder.sweep(item, "compound-all-four", all_artifacts=True)


def S09(recorder):
    with fixture() as item:
        for index in range(4):
            item.pending({"case": 100 + index}, {"pending": index})
        item.system.revise_operation(PARTITION, OPERATION, policy=CompilePolicy(), revised_by="operator")
        item.update("artifacts", "id", item.artifacts[-1], status="draft")
        tail = None
        for index in range(12):
            tail = item.pending({"case": 200 + index}, {"pending": index})
        item.confirmed({"case": 30}, {"answer": "ready"})
        item.confirmed({"case": 31}, {"answer": "blocked"}, count=1)
        item.build(promote=False)
        recorder.sweep(item, "stale-and-pending")
        item.update("proposals", "id", tail, input_hash=ZERO)
        recorder.sweep(item, "pending-tail-corrupt")


def S10(recorder):
    with fixture(count=3, forms=True) as item:
        item.pending(form(10), {"answer": "layout"})
        item.pending(form(11), {"answer": "different"})
        item.pending({"document": "unrecognized", "fields": ["Patient", "Number"]}, {"answer": "miss"})
        item.confirmed({"case": 99}, {"answer": "exact-only"}, count=1)
        recorder.sweep(item, "exact-and-candidate")
        item.system.set_projection(PARTITION, OPERATION, PROGRAM, actor="learning-pass")
        item.build(promote=False)
        recorder.sweep(item, "build-current")
        for name, candidate in (("unwitnessed", PROGRAM_TWO), ("invalid", {}), ("null", None)):
            recorder.probe(item, f"candidate.{name}.learning_cases", lambda s, candidate=candidate: s.learning_cases(PARTITION, OPERATION, program=candidate))
            recorder.probe(item, f"candidate.{name}.test_projection", lambda s, candidate=candidate: s.test_projection(PARTITION, OPERATION, candidate))


def S11(recorder):
    with fixture(promote=False, verify=False) as item:
        recorder.sweep(item, "draft-control")
        item.update("artifacts", "id", item.artifacts[1], evidence_snapshot_hash=ZERO)
        recorder.sweep(item, "snapshot-drift", all_artifacts=True)
    with fixture(promote=False, verify=False) as item:
        item.confirmed(item.inputs[1], {"answer": 12}, count=1)
        recorder.sweep(item, "active-evidence-drift", all_artifacts=True)
    for mode in ("replay", "boundary"):
        with fixture(promote=False, verify=False) as item:
            item.mode = mode
            recorder.sweep(item, f"interpreter-{mode}", all_artifacts=True)
    with fixture(count=2, promote=False, forms=True) as item:
        item.system.set_projection(PARTITION, OPERATION, PROGRAM, actor="learning-pass")
        item.build(verify=False)
        item.mode = "structural"
        recorder.sweep(item, "projection-structural", all_artifacts=True)


def S12(recorder):
    defects = ["missing", "failed", "scope", "details", "artifact_hash", "build_hash", "policy_hash", "evidence_snapshot_hash"]
    for defect in defects:
        with fixture(promote=False) as item:
            artifact = item.artifacts[-1]
            if defect == "missing":
                item.update("artifacts", "id", artifact, verified_report_id="report_absent")
            elif defect == "failed":
                item.update("test_reports", "id", item.reports[artifact], passed=0)
            elif defect == "scope":
                item.report_details(artifact, {"scope_hash": ZERO, "tests": 8, "failures": [], "verified_by": "learning-pass"})
            elif defect == "details":
                item.report_details(artifact, [])
            else:
                item.update("test_reports", "id", item.reports[artifact], **{defect: ZERO})
            recorder.sweep(item, f"bound-report-{defect}", all_artifacts=True)


def S13(recorder):
    with fixture(count=3) as item:
        for capacity in (3, 2):
            item.mode = f"capacity-{capacity}"
            recorder.sweep(item, f"capacity-{capacity}")


SCENARIOS = {name: value for name, value in list(globals().items()) if len(name) == 3 and name.startswith("S") and name[1:].isdigit()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--scenario", action="append", choices=sorted(SCENARIOS))
    args = parser.parse_args()
    for name in args.scenario or sorted(SCENARIOS):
        SCENARIOS[name](Recorder(name))


if __name__ == "__main__":
    main()
