"""Session backend for the Cement web UI demo.

The session drives the shipped ``cement_runtime`` over one temporary SQLite ledger.
Only the provider is simulated: ``StubProvider`` samples a plan variant and a latency
instead of calling a model, so every artifact, digest, check, receipt and resolve
timing the page shows comes from the real system.

The demo enters the pipeline at ``submit_proposal``, the explicit-candidate seam.

Two seams, deliberately split. The operator's lifecycle runs as REAL ``cement``
subprocesses against this ledger, because the shipped control plane is a CLI and the
page must not read as a web console. Chat-side submit and resolve stay in-process:
a subprocess costs a flat ~105 ms of interpreter startup against a 0.9-4 ms resolve,
so routing the chat through it would report startup cost as the function's cost.
"""

from __future__ import annotations

from collections.abc import Callable
import copy
import hashlib
import json
from pathlib import Path
import random
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

from cement_runtime import (
    Candidate,
    CementError,
    CompilePolicy,
    System,
    evaluate,
    parse_function,
)
from cement_runtime.json_value import canonicalize


def _repo_root(start: Path) -> Path:
    """Find the checkout root by the marker file, not by a parent count."""

    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml above {start}")


ROOT = _repo_root(Path(__file__).resolve())
EXAMPLE_DIR = ROOT / "examples" / "hospital_ocr"
DOCUMENTS_DIR = EXAMPLE_DIR / "documents"

# The example owns the OCR corpus and the deterministic signature/extraction core.
# The prototype borrows both rather than forking a second copy that can drift.
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))
import pipeline  # noqa: E402

PARTITION = "example-hospital"
OPERATION = "document.extraction_plan"
REVIEWER = "records-supervisor"
PROMOTER = "informatics-lead"
DEMO_POLICY = CompilePolicy(min_confirmations=2, min_reviewers=1, min_span_seconds=0)
POLICY_VIEW = {
    "min_confirmations": 2,
    "min_reviewers": 1,
    "min_span_seconds": 0,
    "production_default": "3 confirmations, 2 reviewers, a 7-day span",
}
PROVIDER_NAME = "acme-vision/plan-extractor-4"
LATENCY_RANGE = (1.1, 3.4)

def _display(arguments: tuple[str, ...]) -> str:
    """The short form the page prints, runnable as spelled after the preamble.

    A JSON payload passed to `--output` or `--input` runs to hundreds of characters
    and buries the command it belongs to, so it prints as the shell variable a person
    would use. The expansion beside it carries the exact argv that ran. The bound
    clears a 64-character digest, because repeating that digest IS the point of
    `function promote`.
    """

    parts: list[str] = []
    previous = ""
    for argument in arguments:
        if len(argument) > 80 and previous.startswith("--"):
            parts.append('"$' + previous.lstrip("-").upper().replace("-", "_") + '"')
        else:
            parts.append(shlex.quote(argument))
        previous = argument
    return "cement " + " ".join(parts)


def _cement_entry_point() -> Path:
    """The console script beside the running interpreter, so subprocesses run this
    checkout. ``sys.executable`` stays unresolved on purpose: `.venv/bin/python` is a
    symlink into the uv-managed toolchain, and resolving it leaves the venv."""

    beside = Path(sys.executable).parent / "cement"
    return beside if beside.is_file() else ROOT / ".venv" / "bin" / "cement"


CEMENT = _cement_entry_point()

JSONValue = Any


def _canonical_bytes(value: JSONValue) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: JSONValue) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _label_value(text: str, *labels: str) -> str:
    for line in text.split("\n"):
        key, separator, value = line.partition(":")
        if separator and key.strip() in labels:
            return value.strip()
    return ""


def document_catalog() -> list[dict[str, JSONValue]]:
    """Read the corpus once: id, patient, OCR text and layout signature per file."""

    catalog: list[dict[str, JSONValue]] = []
    for path in sorted(DOCUMENTS_DIR.glob("layout_*.txt")):
        parts = path.stem.split("_")
        text = pipeline.ocr(path)
        signature = pipeline.layout_signature(text)
        catalog.append(
            {
                "id": parts[1].upper() + parts[-1],
                "layout": parts[1].upper(),
                "file": path.name,
                "title": text.split("\n", 1)[0].title(),
                "patient": _label_value(text, "Patient", "Name"),
                "text": text,
                "signature": signature,
                "input_hash": _digest(signature),
                "document_type": signature["document_type"],
            }
        )
    return catalog


# --- simulated provider ------------------------------------------------------


def _without(plan: JSONValue, name: str) -> JSONValue:
    copied = copy.deepcopy(plan)
    copied["fields"] = [item for item in copied["fields"] if item["name"] != name]
    return copied


def _renamed(plan: JSONValue, name: str, new_name: str) -> JSONValue:
    copied = copy.deepcopy(plan)
    for item in copied["fields"]:
        if item["name"] == name:
            item["name"] = new_name
    return copied


def _retargeted(plan: JSONValue, name: str, locator: JSONValue) -> JSONValue:
    copied = copy.deepcopy(plan)
    for item in copied["fields"]:
        if item["name"] == name:
            item["locator"] = locator
    return copied


def _retyped(plan: JSONValue, names: tuple[str, ...], value_type: str) -> JSONValue:
    copied = copy.deepcopy(plan)
    for item in copied["fields"]:
        if item["name"] in names:
            item["value_type"] = value_type
    return copied


def _variants(document_type: str) -> list[dict[str, JSONValue]]:
    """Build the plan candidates this provider can return for one layout."""

    reference = pipeline.reference_plan(document_type)
    if reference is None:
        raise ValueError(f"no reference plan for {document_type!r}")
    pool: list[dict[str, JSONValue]] = [
        {
            "key": "complete",
            "note": "returned a complete plan for every field of this layout",
            "plan": copy.deepcopy(reference),
        }
    ]
    if document_type == "physician_progress_note":
        pool += [
            {
                "key": "dropped-provider",
                "note": "omitted the Provider field",
                "plan": _without(reference, "provider"),
            },
            {
                "key": "wrong-section",
                "note": "pointed assessment at the Plan section",
                "plan": _retargeted(
                    reference, "assessment", {"kind": "section", "heading": "Plan"}
                ),
            },
            {
                "key": "invented-label",
                "note": "invented a Physician label that this layout does not carry",
                "plan": _retargeted(
                    reference, "provider", {"kind": "label", "label": "Physician"}
                ),
            },
        ]
    elif document_type == "patient_intake_form":
        pool += [
            {
                "key": "dropped-allergies",
                "note": "omitted the Allergies section",
                "plan": _without(reference, "allergies"),
            },
            {
                "key": "renamed-field",
                "note": "returned complaint instead of primary_complaint",
                "plan": _renamed(reference, "primary_complaint", "complaint"),
            },
        ]
    else:
        pool += [
            {
                "key": "float-decimals",
                "note": "typed the decimal results as plain strings",
                "plan": _retyped(reference, ("potassium", "creatinine"), "string"),
            },
            {
                "key": "dropped-interpretation",
                "note": "omitted the Interpretation section",
                "plan": _without(reference, "interpretation"),
            },
        ]
    return pool


class StubProvider:
    """Stand in for an LLM: a sampled plan variant and a sampled latency.

    The first candidate for a layout always diverges from the reference plan, so the
    supervisor's correction is visible. Later candidates favour the complete plan.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._pools: dict[str, list[dict[str, JSONValue]]] = {}
        self._served: dict[str, int] = {}

    def latency_seconds(self) -> float:
        return self._rng.uniform(*LATENCY_RANGE)

    def candidate(self, document_type: str) -> dict[str, JSONValue]:
        pool = self._pools.setdefault(document_type, _variants(document_type))
        served = self._served.get(document_type, 0)
        self._served[document_type] = served + 1
        if served == 0:
            return copy.deepcopy(self._rng.choice(pool[1:]))
        if self._rng.random() < 0.6:
            return copy.deepcopy(pool[0])
        return copy.deepcopy(self._rng.choice(pool[1:]))


def plan_diff(proposed: JSONValue, reference: JSONValue) -> list[dict[str, str]]:
    """Compare two plans field by field for the review surface."""

    def index(plan: JSONValue) -> dict[str, JSONValue]:
        return {item["name"]: item for item in plan.get("fields", [])}

    left, right = index(proposed), index(reference)
    rows: list[dict[str, str]] = []
    for name in right:
        if name not in left:
            rows.append({"kind": "missing", "field": name, "detail": "not in the candidate"})
        elif left[name] != right[name]:
            rows.append(
                {
                    "kind": "changed",
                    "field": name,
                    "detail": json.dumps(left[name]["locator"], sort_keys=True),
                }
            )
    for name in left:
        if name not in right:
            rows.append({"kind": "extra", "field": name, "detail": "not in the confirmed plan"})
    return rows


# --- session -----------------------------------------------------------------


class Session:
    """One demo run: one ledger, one chat, one control plane."""

    def __init__(self, seed: int = 20260908) -> None:
        self.seed = seed
        self._lock = threading.RLock()
        self._temporary = tempfile.TemporaryDirectory(prefix="cement-demo-")
        self.database = str(Path(self._temporary.name) / "cement.db")
        self.system = System(self.database)
        self.system.register_operation(PARTITION, OPERATION, policy=DEMO_POLICY)
        self.documents = document_catalog()
        self.provider = StubProvider(seed)
        self.chat: list[dict[str, JSONValue]] = []
        self.log: list[dict[str, JSONValue]] = []
        # Every real `cement` invocation, in order, with its exact argv and stdout.
        self.terminal: list[dict[str, JSONValue]] = []
        self.categories: dict[str, dict[str, JSONValue]] = {}
        self.pending: dict[str, dict[str, JSONValue]] = {}
        # Keyed by scope. An entry's value is unreadable without the per-request plans
        # that produced it, and `pending` drops a proposal the moment it is reviewed.
        self.lineage: dict[str, list[dict[str, JSONValue]]] = {}
        self.drafts: dict[str, dict[str, JSONValue]] = {}
        self.function: dict[str, JSONValue] | None = None
        self.bundle_text: str | None = None
        self.offline: dict[str, JSONValue] | None = None
        self.routed = False
        self.thinking: dict[str, JSONValue] | None = None
        self.started = time.time()
        self._sequence = 0
        self.stats = {
            "provider_calls": 0,
            "provider_seconds": 0.0,
            "reviews": 0,
            "cement_answers": 0,
            "provider_calls_avoided": 0,
            "resolve_ms": [],
        }
        self._note(
            "ledger",
            f"temporary ledger created; operation {OPERATION} registered "
            f"in partition {PARTITION}",
            f"policy: {POLICY_VIEW['min_confirmations']} confirmations, "
            f"{POLICY_VIEW['min_reviewers']} reviewer, no minimum span",
        )

    # -- plumbing --

    def close(self) -> None:
        self._temporary.cleanup()

    def _next(self) -> int:
        self._sequence += 1
        return self._sequence

    def _note(self, kind: str, text: str, detail: str = "") -> None:
        self.log.append(
            {
                "seq": self._next(),
                "at": round(time.time() - self.started, 2),
                "kind": kind,
                "text": text,
                "detail": detail,
            }
        )

    def _say(self, role: str, kind: str, **fields: JSONValue) -> dict[str, JSONValue]:
        message = {"seq": self._next(), "role": role, "kind": kind, **fields}
        self.chat.append(message)
        return message

    def _cli(
        self,
        *arguments: str,
        stdin: str | None = None,
        reading: Callable[[JSONValue], list[list[str]]] | None = None,
        check: bool = True,
        sink: list[dict[str, JSONValue]] | None = None,
    ) -> JSONValue:
        """Run one real ``cement`` command against this ledger and record it.

        The page shows the command, its exit code and a short reading of the bytes
        this call actually returned; the verbatim stdout stays attached for the
        reader who opens it. Nothing here is rendered from anywhere else.
        """

        argv = [str(CEMENT), "--db", self.database, "--partition", PARTITION]
        argv.extend(arguments)
        started = time.perf_counter()
        completed = subprocess.run(  # noqa: S603
            argv, input=stdin, capture_output=True, text=True
        )
        elapsed = round((time.perf_counter() - started) * 1000)
        stdout = completed.stdout or completed.stderr
        value: JSONValue = None
        if stdout.strip():
            try:
                value = json.loads(stdout)
            except json.JSONDecodeError:
                value = None
        rows: list[list[str]] = []
        if reading is not None and completed.returncode == 0:
            rows = reading(value)
        elif completed.returncode != 0:
            message = value.get("message") if isinstance(value, dict) else None
            rows = [["error", str(message or f"exit {completed.returncode}")]]
        rows_sink = self.terminal if sink is None else sink
        rows_sink.append(
            {
                "seq": self._next(),
                "at": round(time.time() - self.started, 2),
                "display": _display(arguments),
                "argv": argv,
                "rc": completed.returncode,
                "ms": elapsed,
                "stdout": stdout,
                "bytes": len(stdout.encode("utf-8")),
                "reading": rows,
            }
        )
        if check and completed.returncode != 0:
            # Recorded first: a failing command belongs on the terminal the page reads.
            raise RuntimeError(rows[0][1] if rows else f"exit {completed.returncode}")
        return value

    def _ledger_preamble(self) -> list[str]:
        """The two lines that make every printed command runnable as spelled."""

        return [
            f"export CEMENT_DB={shlex.quote(self.database)}",
            "alias cement='cement --db \"$CEMENT_DB\" "
            f"--partition {shlex.quote(PARTITION)}'",
        ]

    def _document(self, document_id: str) -> dict[str, JSONValue]:
        for document in self.documents:
            if document["id"] == document_id:
                return document
        raise KeyError(f"unknown document {document_id!r}")

    def _category(self, document: dict[str, JSONValue]) -> dict[str, JSONValue]:
        key = document["input_hash"]
        category = self.categories.get(key)
        if category is None:
            category = {
                "input_hash": key,
                "layout": document["layout"],
                "document_type": document["document_type"],
                "signature": document["signature"],
                "candidates": [],
                "promoted": False,
                "artifact_id": None,
            }
            self.categories[key] = category
            self._note(
                "category",
                f"layout {document['layout']} signature seen for the first time",
                f"input_hash {key[:12]}… · {len(document['signature']['structure'])} "
                "structural keys, no patient values",
            )
        return category

    # -- chat --

    def send(self, document_id: str) -> None:
        """Send one document from the intake desk into the assistant."""

        with self._lock:
            document = self._document(document_id)
            category = self._category(document)
            self._say(
                "clerk",
                "document",
                document_id=document["id"],
                title=document["title"],
                patient=document["patient"],
                layout=document["layout"],
                text=document["text"],
                ask="Extract the record fields as JSON.",
                under={
                    "summary": "what Cement keys this request on",
                    "rows": [
                        ["layout", str(document["layout"])],
                        ["input digest", str(document["input_hash"])],
                        [
                            "structural keys",
                            str(len(document["signature"]["structure"])),
                        ],
                    ],
                    "blocks": [
                        {
                            "label": "the signature, holding no patient values",
                            "json": document["signature"],
                        },
                    ],
                    "note": "Documents for different patients share this signature. "
                    "That is what makes them one category.",
                },
            )
            if self.routed and self.function is not None:
                if self._answer_from_function(document):
                    return
            self.thinking = {
                "document_id": document["id"],
                "provider": PROVIDER_NAME,
                "started": time.time(),
            }
            delay = self.provider.latency_seconds()
            candidate = self.provider.candidate(document["document_type"])

        time.sleep(delay)

        with self._lock:
            self.thinking = None
            self.stats["provider_calls"] += 1
            self.stats["provider_seconds"] = round(
                float(self.stats["provider_seconds"]) + delay, 2
            )
            proposal_id = self.system.submit_proposal(
                PARTITION,
                OPERATION,
                document["signature"],
                candidate=Candidate(
                    output=candidate["plan"],
                    provenance={
                        "model": PROVIDER_NAME,
                        "variant": candidate["key"],
                        "simulated": "true",
                    },
                ),
            )
            digest = _digest(candidate["plan"])
            if digest not in category["candidates"]:
                category["candidates"].append(digest)
            reference = pipeline.reference_plan(document["document_type"])
            preview, error = self._preview(candidate["plan"], document["text"])
            self.pending[proposal_id] = {
                "proposal_id": proposal_id,
                "document_id": document["id"],
                "input_hash": document["input_hash"],
                "layout": document["layout"],
                "variant": candidate["key"],
                "note": candidate["note"],
                "plan": candidate["plan"],
                "correction": reference,
                "diff": plan_diff(candidate["plan"], reference),
                "preview": preview,
                "preview_error": error,
                "provider_ms": round(delay * 1000),
            }
            self._say(
                "assistant",
                "held",
                document_id=document["id"],
                proposal_id=proposal_id,
                provider=PROVIDER_NAME,
                provider_ms=round(delay * 1000),
            )
            self._note(
                "proposal",
                f"{document['id']}: provider candidate stored as {proposal_id}",
                f"{PROVIDER_NAME} {round(delay * 1000)} ms simulated · the candidate "
                "stays hidden until review",
            )

    def _answer_from_function(self, document: dict[str, JSONValue]) -> bool:
        """Answer one document from the promoted set. Return False on a miss."""

        start = time.perf_counter()
        resolution = self.system.resolve(PARTITION, OPERATION, document["signature"])
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        self.stats["resolve_ms"].append(elapsed)
        verification = resolution.verification
        match = resolution.match
        if verification.passed and match is not None and match.matched:
            extracted, error = self._preview(match.output, document["text"])
            self.stats["cement_answers"] += 1
            self.stats["provider_calls_avoided"] += 1
            self._say(
                "assistant",
                "cement",
                document_id=document["id"],
                output=extracted,
                error=error,
                plan=match.output,
                artifact_hash=match.artifact_hash,
                function_hash=verification.function_hash,
                entries=verification.entries,
                resolve_ms=elapsed,
                checks=[check.key for check in verification.checks],
                under={
                    "summary": "no model ran; the promoted function answered",
                    "rows": [
                        ["resolve", f"{elapsed} ms, measured"],
                        ["matched entry", str(match.artifact_hash)],
                        ["function", str(verification.function_hash)],
                        [
                            "checks",
                            f"{len(verification.checks)} passed over "
                            f"{verification.entries} entry(ies), on this call",
                        ],
                    ],
                    "blocks": [
                        {
                            "label": "the sealed plan this entry returns",
                            "json": match.output,
                        },
                    ],
                    "commands": [
                        f"cement resolve {OPERATION} --input "
                        + shlex.quote(json.dumps(document["signature"])),
                    ],
                    "commands_ran": False,
                    "commands_label": "the deployment calls System.resolve in "
                    "process, and this command makes the same call from a shell",
                    "note": "Every resolve runs the full six-check verification and "
                    "caches nothing. A shell adds about 105 ms of interpreter "
                    "startup, which is why the page calls the library here.",
                },
            )
            self._note(
                "resolve",
                f"{document['id']}: answered from the promoted set in {elapsed} ms",
                f"six checks passed over {verification.entries} entries · "
                "no provider call",
            )
            return True
        self._say(
            "assistant",
            "miss",
            document_id=document["id"],
            layout=document["layout"],
            resolve_ms=elapsed,
            entries=verification.entries,
            passed=verification.passed,
        )
        self._note(
            "resolve",
            f"{document['id']}: no promoted entry for this layout ({elapsed} ms)",
            "the request falls back to the supervised provider path",
        )
        return False

    @staticmethod
    def _preview(plan: JSONValue, text: str) -> tuple[JSONValue, str]:
        try:
            return pipeline.apply_plan(plan, text), ""
        except (ValueError, TypeError) as error:
            return None, str(error)

    # -- review surface --

    def review(self, proposal_id: str, decision: str) -> None:
        with self._lock:
            record = self.pending.get(proposal_id)
            if record is None:
                raise KeyError(f"no pending proposal {proposal_id!r}")
            document = self._document(str(record["document_id"]))
            arguments = [
                "proposal",
                "review",
                proposal_id,
                "--reviewer",
                REVIEWER,
                "--decision",
                decision,
            ]
            if decision == "correct":
                arguments += [
                    "--output",
                    json.dumps(record["correction"], separators=(",", ":")),
                    "--note",
                    "corrected to the confirmed layout plan",
                ]
            result = self._cli(
                *arguments,
                reading=lambda value: [
                    ["status", str(value["status"])],
                    ["example", str(value["example_id"] or "none created")],
                ],
            )
            del self.pending[proposal_id]
            self.stats["reviews"] += 1

            if result["status"] == "rejected":
                self._say(
                    "assistant",
                    "rejected",
                    document_id=document["id"],
                    proposal_id=proposal_id,
                    under={
                        "summary": "a person refused the model's answer",
                        "rows": [
                            ["answered by", f"{PROVIDER_NAME} (simulated)"],
                            ["held as", str(proposal_id)],
                            ["reviewer", f"{REVIEWER} rejected it"],
                            ["confirmed example", "none created"],
                        ],
                        "blocks": [
                            {
                                "label": "the plan the model wrote, released to nobody",
                                "json": record["plan"],
                            },
                        ],
                        "commands": [self.terminal[-1]["display"]],
                        "commands_label": "the command the review surface ran",
                    },
                )
                self._note(
                    "review",
                    f"{document['id']}: {REVIEWER} rejected {proposal_id}",
                    "audit evidence only; the rejection creates no example",
                )
                return

            extracted, error = self._preview(result["output"], document["text"])
            diff = plan_diff(record["plan"], result["output"])
            self.lineage.setdefault(str(record["input_hash"]), []).append(
                {
                    "document_id": document["id"],
                    "proposal_id": proposal_id,
                    "layout": record["layout"],
                    "provider": PROVIDER_NAME,
                    "provider_ms": record["provider_ms"],
                    "variant": record["variant"],
                    "note": record["note"],
                    "provider_plan": record["plan"],
                    "confirmed_plan": result["output"],
                    "diff": diff,
                    "status": result["status"],
                    "reviewer": REVIEWER,
                    "example_id": result["example_id"],
                }
            )
            self._say(
                "assistant",
                "released",
                document_id=document["id"],
                proposal_id=proposal_id,
                status=result["status"],
                reviewer=REVIEWER,
                output=extracted,
                error=error,
                plan=result["output"],
                example_id=result["example_id"],
                under={
                    "summary": "a model answered, and a person confirmed it",
                    "rows": [
                        ["answered by", f"{PROVIDER_NAME} (simulated)"],
                        ["model took", f"{record['provider_ms']} ms (simulated)"],
                        ["held as", str(proposal_id)],
                        ["reviewer", f"{REVIEWER} {result['status']} it"],
                        ["confirmed example", str(result["example_id"])],
                    ],
                    "blocks": [
                        {"label": "the plan the model wrote", "json": record["plan"]},
                    ],
                    "diff": diff,
                    "diff_label": "what the supervisor changed",
                    "diff_empty": "The supervisor kept the model's plan byte for byte.",
                    "commands": [self.terminal[-1]["display"]],
                    "commands_label": "the command the review surface ran",
                },
            )
            self._note(
                "review",
                f"{document['id']}: {REVIEWER} {result['status']} {proposal_id}",
                f"confirmed example {result['example_id']} binds the layout signature "
                "to this exact plan",
            )

    def revoke(self, example_id: str) -> None:
        with self._lock:
            self._cli(
                "example",
                "revoke",
                example_id,
                "--actor",
                REVIEWER,
                "--reason",
                "withdrawn in the demo",
                reading=lambda value: [
                    ["revoked", str(value["example_id"])],
                    [
                        "suspended artifacts",
                        str(len(value["suspended_artifact_ids"])),
                    ],
                ],
            )
            self._note(
                "evidence",
                f"{REVIEWER} revoked example {example_id}",
                "the example leaves the active evidence set for the next compile",
            )

    # -- lifecycle --

    def compile(self) -> None:
        with self._lock:
            result = self._cli(
                "compile",
                OPERATION,
                reading=lambda value: [
                    ["created", str(len(value["created"])) + " draft(s)"],
                ]
                + [
                    [
                        "blocked",
                        f"layout {self._layout_of(str(row['input_hash']))} - "
                        + "; ".join(str(reason) for reason in row["reasons"]),
                    ]
                    for row in value["blocked"]
                ],
            )
            for artifact_id in result["created"]:
                summary = self.system.artifact(PARTITION, artifact_id)
                self.drafts[artifact_id] = {
                    "artifact_id": artifact_id,
                    "input_hash": summary["input_hash"],
                    "layout": self._layout_of(str(summary["input_hash"])),
                    "status": "draft",
                    "support": summary["support"],
                    "tests": None,
                    "scope_hash": summary["scope_hash"],
                }
            blocked = [
                {
                    "input_hash": row.get("input_hash"),
                    "layout": self._layout_of(str(row.get("input_hash"))),
                    "support": row.get("support"),
                    "reasons": row.get("reasons"),
                }
                for row in result["blocked"]
            ]
            self._note(
                "compile",
                f"compile created {len(result['created'])} draft(s), "
                f"{len(result['blocked'])} scope(s) blocked",
                "; ".join(
                    f"layout {row['layout']}: "
                    + ", ".join(str(reason) for reason in (row["reasons"] or []))
                    for row in blocked
                )
                or "grouped active examples by exact scope; no model runs here",
            )
            self.blocked = blocked

    def verify(self) -> None:
        with self._lock:
            verification = self._cli(
                "function",
                "verify-drafts",
                OPERATION,
                "--actor",
                PROMOTER,
                reading=lambda value: [
                    [
                        "verdict",
                        "passed" if value["passed"] else "failed",
                    ],
                    [
                        "replayed",
                        f"{sum(row['report']['tests'] for row in value['entries'])} "
                        f"sealed test(s) over {len(value['entries'])} draft(s)",
                    ],
                ],
            )
            for entry in verification["entries"]:
                draft = self.drafts.get(entry["artifact_id"])
                if draft is None:
                    continue
                report = entry["report"]
                draft["status"] = "verified" if report["passed"] else "failed"
                draft["tests"] = report["tests"]
                draft["scope_hash"] = report["scope_hash"]
            tests = sum(row["report"]["tests"] for row in verification["entries"])
            self._note(
                "verify",
                f"verify-drafts replayed {tests} sealed test(s) "
                f"over {len(verification['entries'])} draft(s)",
                "every active example in the exact scope, plus partition, operation, "
                "revision and input boundary probes",
            )

    def promote(self) -> None:
        with self._lock:
            promoted: list[str] = []
            for draft in self.drafts.values():
                if draft["status"] != "verified":
                    continue
                self._cli(
                    "promote",
                    str(draft["artifact_id"]),
                    "--scope-hash",
                    str(draft["scope_hash"]),
                    "--actor",
                    PROMOTER,
                    reading=lambda value: [
                        ["promoted", str(value["artifact_id"])],
                        ["replaced", str(len(value["replaced_artifact_ids"]))],
                    ],
                )
                draft["status"] = "promoted"
                promoted.append(str(draft["artifact_id"]))
                category = self.categories.get(str(draft["input_hash"]))
                if category is not None:
                    category["promoted"] = True
                    category["artifact_id"] = draft["artifact_id"]
            if promoted:
                self._note(
                    "promote",
                    f"{PROMOTER} promoted {len(promoted)} artifact(s) "
                    "against the verified scope hash",
                    ", ".join(promoted),
                )
            self._checkpoint()

    def _checkpoint(self) -> None:
        manifest = self._cli(
            "function",
            "inspect",
            OPERATION,
            reading=lambda value: [
                ["verified entries", str(len(value["entries"]))],
                ["prospective hash", str(value["function_hash"])],
            ],
        )
        if not manifest["entries"]:
            self._note("function", "no verified entries to seal into a function", "")
            return
        function_hash = str(manifest["function_hash"])
        # `function promote` refuses unless the operator repeats the digest `inspect`
        # reported, so the demo passes the value it just read rather than a flag.
        promotion = self._cli(
            "function",
            "promote",
            OPERATION,
            "--expected-function-hash",
            function_hash,
            "--actor",
            PROMOTER,
            reading=lambda value: [
                ["receipt", str(value["receipt_id"])],
                ["members", f"{len(value['member_artifact_ids'])} artifact(s)"],
            ],
        )
        verification = self._cli(
            "function",
            "verify",
            OPERATION,
            "--expected-function-hash",
            function_hash,
            reading=lambda value: [
                ["verdict", "passed" if value["passed"] else "failed"],
                [
                    "checks",
                    f"{sum(1 for check in value['checks'] if check['passed'])}/"
                    f"{len(value['checks'])} over {value['entries']} entry(ies)",
                ],
            ],
        )
        self._cli(
            "function",
            "export",
            OPERATION,
            reading=lambda value: [
                ["abi", str(value["abi"])],
                ["sealed entries", str(len(value["entries"]))],
            ],
        )
        self.bundle_text = str(self.terminal[-1]["stdout"])
        self.function = {
            "function_hash": verification["function_hash"],
            "entries": verification["entries"],
            "passed": verification["passed"],
            "checks": verification["checks"],
            "receipt_id": promotion["receipt_id"],
            "members": list(promotion["member_artifact_ids"]),
            "bundle_bytes": len(self.bundle_text.encode("utf-8")),
            "source": self._source_view(function_hash),
        }
        self.offline = None
        self._note(
            "function",
            f"set promotion sealed {verification['entries']} entry(ies) "
            f"under receipt {promotion['receipt_id']}",
            f"function_hash {function_hash[:16]}… · "
            f"{len(verification['checks'])} ordered checks passed",
        )

    def _hops(
        self, artifact_id: str, shared: list[dict[str, JSONValue]]
    ) -> tuple[list[dict[str, JSONValue]], list[dict[str, JSONValue]]]:
        """Walk one promoted entry back to the requests behind it, through the CLI.

        Four leaves and a join the caller performs by hand: no command prints an
        entry beside its originals, and `events` carries no example filter, so this
        scans the whole stream and matches `payload.example_id` itself. The cost is
        the point, and every row here is a command that ran.
        """

        rows = list(shared)
        artifact = self._cli(
            "artifact",
            "show",
            artifact_id,
            reading=lambda value: [
                ["evidence", ", ".join(value["evidence_ids"])],
                [
                    "support",
                    f"{value['support']} example(s), "
                    f"{value['reviewer_count']} reviewer(s)",
                ],
            ],
            sink=rows,
        )
        wanted = set(artifact["evidence_ids"])

        def matched(stream: JSONValue) -> list[tuple[str, str]]:
            return [
                (str(row["subject_id"]), str(row["payload"]["example_id"]))
                for row in stream
                if row["subject_type"] == "proposal"
                and isinstance(row.get("payload"), dict)
                and row["payload"].get("example_id") in wanted
            ]

        events = self._cli(
            "events",
            "--limit",
            "200",
            reading=lambda value: [
                ["scanned", f"{len(value)} event(s); no example filter exists"],
                [
                    "matched",
                    ", ".join(pair[0] for pair in matched(value)) or "none",
                ],
            ],
            sink=rows,
        )
        by_proposal = {
            str(row["proposal_id"]): row
            for group in self.lineage.values()
            for row in group
        }
        originals: list[dict[str, JSONValue]] = []
        for proposal_id, example_id in matched(events):
            shown = self._cli(
                "proposal",
                "show",
                proposal_id,
                reading=lambda value: [
                    ["status", f"{value['status']} by {value['reviewer']}"],
                    ["proposed_output", "what the model wrote"],
                    ["final_output", "what the supervisor kept"],
                ],
                sink=rows,
            )
            session_row = by_proposal.get(proposal_id, {})
            provenance = shown.get("provenance") or {}
            originals.append(
                {
                    "proposal_id": proposal_id,
                    "example_id": example_id,
                    "document_id": session_row.get("document_id", "-"),
                    "provider": provenance.get("model", PROVIDER_NAME),
                    "provider_ms": session_row.get("provider_ms"),
                    "variant": provenance.get("variant", "-"),
                    "note": session_row.get("note", ""),
                    "provider_plan": shown["proposed_output"],
                    "confirmed_plan": shown["final_output"],
                    "diff": plan_diff(shown["proposed_output"], shown["final_output"]),
                    "status": shown["status"],
                    "reviewer": shown["reviewer"],
                }
            )
        return rows, originals

    def _source_view(self, function_hash: str) -> dict[str, JSONValue]:
        """Project the exported bundle into the entries a reader can read.

        Parsed back out of the bundle rather than rebuilt from the ledger: the reader
        must see the artifact that travels, not a second rendering of the same rows.
        """

        document = parse_function(
            str(self.bundle_text), expected_function_hash=function_hash
        )
        scope: JSONValue = document.value["scope"]
        sealed: JSONValue = document.value["entries"]
        # Hop 1 answers every entry at once, so it runs here and prefixes each walk.
        shared: list[dict[str, JSONValue]] = []
        manifest = self._cli(
            "function",
            "inspect",
            OPERATION,
            reading=lambda value: [
                [
                    "entries",
                    ", ".join(str(row["artifact_id"]) for row in value["entries"]),
                ],
            ],
            sink=shared,
        )
        by_artifact_hash = {
            str(row["artifact_hash"]): str(row["artifact_id"])
            for row in manifest["entries"]
        }
        entries: list[dict[str, JSONValue]] = []
        for index, entry in enumerate(sealed, start=1):
            input_hash = str(entry["input_hash"])
            artifact_id = by_artifact_hash.get(str(entry["artifact_hash"]), "")
            hops, originals = (
                self._hops(artifact_id, shared) if artifact_id else ([], [])
            )
            entries.append(
                {
                    "index": index,
                    "layout": self._layout_of(input_hash),
                    "input": entry["input"],
                    "output": entry["output"],
                    "input_hash": input_hash,
                    "artifact_hash": entry["artifact_hash"],
                    "artifact_id": artifact_id,
                    "entry_seal": entry["entry_seal"],
                    "confirmations": len(originals),
                    "reviewers": sorted({str(row["reviewer"]) for row in originals}),
                    "originals": originals,
                    "hops": hops,
                }
            )
        return {
            "partition": scope["partition"],
            "operation": scope["operation"],
            "revision": scope["operation_revision"],
            "entries": entries,
        }

    def route(self, enabled: bool) -> None:
        with self._lock:
            self.routed = bool(enabled)
            self._note(
                "routing",
                f"operator routing {'enabled' if self.routed else 'disabled'} "
                f"for {OPERATION}",
                "matching requests resolve from the promoted set; every other input "
                "keeps the supervised provider path"
                if self.routed
                else "every request returns to the supervised provider path",
            )

    def evaluate_offline(self, document_id: str) -> None:
        """Answer one document from the exported bytes, with no ledger read."""

        with self._lock:
            if self.bundle_text is None or self.function is None:
                raise RuntimeError("no verified function to export")
            document = self._document(document_id)
            expected = str(self.function["function_hash"])
            function = parse_function(self.bundle_text, expected_function_hash=expected)
            match = evaluate(function, input_json=canonicalize(document["signature"]))
            extracted, error = (
                self._preview(match.output, document["text"])
                if match.matched
                else (None, "")
            )
            self.offline = {
                "document_id": document["id"],
                "layout": document["layout"],
                "matched": match.matched,
                "output": extracted,
                "error": error,
                "artifact_hash": match.artifact_hash,
                "function_hash": function.function_hash,
            }
            self._note(
                "bundle",
                f"{document['id']}: the exported bundle "
                f"{'returned the confirmed plan' if match.matched else 'reported a miss'}",
                f"{len(self.bundle_text.encode('utf-8'))} bytes parsed against the "
                "operator's own hash; no ledger read",
            )

    # -- read model --

    def _layout_of(self, input_hash: str) -> str:
        category = self.categories.get(input_hash)
        if category is not None:
            return str(category["layout"])
        for document in self.documents:
            if document["input_hash"] == input_hash:
                return str(document["layout"])
        return "?"

    def _evidence(self) -> dict[str, list[dict[str, JSONValue]]]:
        grouped: dict[str, list[dict[str, JSONValue]]] = {}
        for row in self.system.examples(PARTITION, OPERATION):
            # `examples` returns the values, not their digests; the ledger groups by
            # the same canonical-JSON digest the compiler uses for a scope.
            grouped.setdefault(_digest(row["input"]), []).append(
                {
                    "example_id": row["id"],
                    "reviewer": row["reviewer"],
                    "origin": row["origin"],
                    "output_hash": _digest(row["output"])[:12],
                }
            )
        return grouped

    def state(self) -> dict[str, JSONValue]:
        with self._lock:
            evidence = self._evidence()
            categories = []
            for key, category in self.categories.items():
                rows = evidence.get(key, [])
                categories.append(
                    {
                        **{
                            name: value
                            for name, value in category.items()
                            if name != "candidates"
                        },
                        "examples": rows,
                        "confirmations": len(rows),
                        "reviewers": sorted({str(row["reviewer"]) for row in rows}),
                        "distinct_candidates": len(category["candidates"]),
                        "required": POLICY_VIEW["min_confirmations"],
                    }
                )
            resolve_ms = list(self.stats["resolve_ms"])
            function = self.function
            if function is not None:
                # Read time, not promotion time: a category can miss the floor after
                # the promotion that sealed the function.
                function = {
                    **function,
                    "excluded": [
                        {
                            "layout": category["layout"],
                            "document_type": category["document_type"],
                            "confirmations": len(evidence.get(key, [])),
                            "required": POLICY_VIEW["min_confirmations"],
                        }
                        for key, category in self.categories.items()
                        if not category["promoted"]
                    ],
                }
            return {
                "partition": PARTITION,
                "operation": OPERATION,
                "reviewer": REVIEWER,
                "promoter": PROMOTER,
                "provider": PROVIDER_NAME,
                "policy": POLICY_VIEW,
                "documents": [
                    {
                        name: value
                        for name, value in document.items()
                        if name != "signature"
                    }
                    for document in self.documents
                ],
                "chat": self.chat,
                "log": self.log,
                "terminal": self.terminal,
                "ledger": {
                    "path": self.database,
                    "preamble": self._ledger_preamble(),
                },
                "categories": sorted(categories, key=lambda row: str(row["layout"])),
                "pending": list(self.pending.values()),
                "drafts": list(self.drafts.values()),
                "blocked": getattr(self, "blocked", []),
                "function": function,
                "offline": self.offline,
                "routed": self.routed,
                "thinking": self.thinking,
                "stats": {
                    **{
                        name: value
                        for name, value in self.stats.items()
                        if name != "resolve_ms"
                    },
                    "resolve_ms_last": resolve_ms[-1] if resolve_ms else None,
                    "resolve_ms_median": _median(resolve_ms),
                    "provider_ms_mean": round(
                        float(self.stats["provider_seconds"])
                        * 1000
                        / max(1, int(self.stats["provider_calls"]))
                    )
                    if self.stats["provider_calls"]
                    else None,
                },
            }

    def transcript(self) -> str:
        """Render the control-plane log as plain text for the proof directory."""

        with self._lock:
            lines = [
                "Cement web UI demo - control-plane transcript",
                f"partition {PARTITION} · operation {OPERATION} · seed {self.seed}",
                f"policy {POLICY_VIEW['min_confirmations']} confirmations, "
                f"{POLICY_VIEW['min_reviewers']} reviewer, no minimum span "
                f"(production default: {POLICY_VIEW['production_default']})",
                "",
            ]
            for row in self.log:
                lines.append(f"[{row['at']:>7.2f}s] {row['kind']:<9} {row['text']}")
                if row["detail"]:
                    lines.append(f"{'':>10}  {'':<9} {row['detail']}")
            return "\n".join(lines) + "\n"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 1)
    return round((ordered[middle - 1] + ordered[middle]) / 2, 1)


__all__ = ["CementError", "Session", "document_catalog"]
