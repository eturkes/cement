"""`/ext/bin/cement`: Cement for one nucllei user, run by the chat model through `run_shell`.

The nucllei sandbox jail has no network, a read-only root and one persistent `/workspace` per
user, and llens keeps patient data in that workspace alone, so each user's ledger lives there
(`CEMENT_HOME`, default `/workspace/.cement`). The model reads every line this command prints:
the text is Japanese in llens style, a refusal reads `中止: <fact>`, and the last line names the
next step after `次の手:`. `generate.py` embeds `cement_runtime` and writes `ext/bin/cement`.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import fcntl
import json
import os
import pathlib
import re
import secrets
import sys
import time
from collections.abc import Callable
from typing import Any, NoReturn

from cement_runtime import (
    Candidate,
    CementError,
    ConflictError,
    IntegrityError,
    NotFoundError,
    StateError,
    System,
    ValidationError,
)
from cement_runtime.function import evaluate
from cement_runtime.json_value import canonicalize, parse_json
from cement_runtime.learning import (
    REVIEWER,
    MergeInterruptedError,
    MergeRefusedError,
    cases,
    check_merge_ids,
    merge_case,
    publish,
    raw_inputs,
)
from cement_runtime.projection import draft_program
from cement_runtime.system import PROVENANCE_MAX_BYTES

COMMAND = "/ext/bin/cement"
HOME = "/workspace/.cement"
PARTITION = "nucllei"
CHAT = "nucllei-chat"
PERSON = "nucllei-user"
PAGE = 1_000
TICKET = re.compile(r"t_[0-9a-f]{16}")
TICKET_TTL_US = 24 * 3600 * 1_000_000
# A regenerated reply looks up and records the same input again within minutes; nucllei gives
# the jail no chat or message id that could tell it from a genuine repeat.
REGENERATION_US = 10 * 60 * 1_000_000
REASONS = {
    "absent": "学習済みの版がまだ無い",
    "off": "関数がオフ",
    "failed": "関数の検証が通らなかった",
    "unrecognized": "関数にこの入力の場合が無い",
}
MERGE_REFUSALS = {
    "not_a_list": "id は一覧で渡す。",
    "no_ids": "--proposals か --examples で 1 つの場合の id を渡していない。",
    "repeated_ids": "同じ id を 2 回渡している。",
    "not_one_case": "渡した id は 1 つの場合の未確認の提案・確認済みの例ではない。",
}
PUBLISH_REASONS = {
    "failed": "下書きの検証が通らなかった",
    "empty": "確認が 2 件そろった場合がまだ無い",
    "same": "最新の版が既に同じ中身を持つ",
}
NEXT = {
    2: "次の手: 引数か入力を直して流し直す。",
    3: "次の手: 名前・番号・控えを確かめて流し直す。",
    4: "次の手: 1 回だけ流し直す。続くなら、中止したことをユーザーに伝える。",
    5: "次の手: 流し直さない。Cement の台帳が壊れているとユーザーに伝える。",
}


class _RefusalError(Exception):
    def __init__(self, status: int, fact: str, next_step: str | None = None) -> None:
        super().__init__(fact)
        self.status = status
        self.next_step = next_step or NEXT[status]


def _clock_us() -> int:
    return time.time_ns() // 1_000


def _status(exc: CementError) -> int:
    if isinstance(exc, NotFoundError):
        return 3
    if isinstance(exc, (ConflictError, StateError)):
        return 4
    return 5 if isinstance(exc, IntegrityError) else 2


def _say(*lines: str) -> None:
    sys.stdout.write("\n".join(lines) + "\n")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _same(left: object, right: object) -> bool:
    return canonicalize(left).digest == canonicalize(right).digest


def _when(microseconds: int) -> str:
    moment = datetime.datetime.fromtimestamp(microseconds / 1_000_000).astimezone()
    return moment.strftime("%Y-%m-%d %H:%M")


# -- the user's place --------------------------------------------------------


def _home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("CEMENT_HOME") or HOME)


def _system() -> System:
    """The existing ledger; only `use` creates one."""

    if not (_home() / "ledger.db").is_file():
        raise _RefusalError(3, "Cement の台帳がまだ無い (まだ何も記録していない)。")
    return System(_home() / "ledger.db", create=False, clock_us=_clock_us)


def _write(path: pathlib.Path, value: object) -> None:
    # One whole file or none: a crash mid-write must not leave a ticket that record misreads.
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def _state() -> dict[str, Any]:
    try:
        state = json.loads((_home() / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _projectable_state(operation: str) -> bool | None:
    known = _state().get("projectable")
    value = known.get(operation) if isinstance(known, dict) else None
    return value if isinstance(value, bool) else None


def _remember(operation: str, projectable: bool) -> list[str]:
    """Store the pass's ruling; a failure follows durable writes, so it becomes a line.

    The read-modify-write holds an exclusive lock: two passes of one user (two chats) would
    otherwise both read the old file and the later write would drop the other's ruling."""

    try:
        with open(_home() / ".state.lock", "a", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = _state()
            known = state.get("projectable")
            rulings = known if isinstance(known, dict) else {}
            state["projectable"] = rulings | {operation: projectable}
            _write(_home() / "state.json", state)
    except OSError as exc:
        return [f"(用紙の形でまとめるかの判断は保存できなかった: {exc.__class__.__name__})"]
    return []


def _discard(path: pathlib.Path) -> list[str]:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        name = exc.__class__.__name__
        return [f"(控えのファイルを消せなかった: {name}。同じ控えは記録済みとして扱われる)"]
    return []


def _read(path: str | None) -> str:
    if path is None:
        return sys.stdin.read()
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise _RefusalError(2, f"ファイル {path} を読めない ({exc.__class__.__name__})。") from None


def _parse(text: str, what: str) -> object:
    # Cement's strict reader: a repeated key or an over-deep nest is a refusal, never a guess.
    try:
        return parse_json(text).value
    except ValidationError as exc:
        raise _RefusalError(2, f"{what}が JSON として読めない ({exc})。") from None


# -- reading the ledger ------------------------------------------------------


def _versions(system: System, operation: str, *, check: bool = False) -> list[Any]:
    """Every version, newest first: version N = the N-th promotion, so a number never moves."""

    versions: list[Any] = []
    before = None
    while True:
        page = system.function_versions(
            PARTITION, operation, before_sequence=before, limit=PAGE, check=check
        )
        versions += page.versions
        if page.next_before_sequence is None:
            return versions
        before = page.next_before_sequence


def _number(versions: list[Any], function_hash: str | None) -> int | None:
    for index, version in enumerate(versions):
        if version.receipt.function_hash == function_hash:
            return len(versions) - index
    return None


def _version(versions: list[Any], number: int) -> Any:
    if not 1 <= number <= len(versions):
        raise _RefusalError(3, f"版 {number} は無い (版は 1 から {len(versions)})。")
    return versions[len(versions) - number]


def _proposals(system: System, operation: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    after = 0
    while True:
        rows = system.proposals(PARTITION, status="all", after_sequence=after, limit=PAGE)
        found += [row for row in rows if row["operation"] == operation]
        if len(rows) < PAGE:
            return sorted(found, key=lambda row: (row["created_at_us"], row["id"]))
        after = int(rows[-1]["sequence"])


def _suspects(system: System, operation: str) -> set[str]:
    """Pending proposals recorded within minutes of an earlier one with the same input."""

    last: dict[str, int] = {}
    suspects: set[str] = set()
    for row in _proposals(system, operation):
        digest = canonicalize(row["input"]).digest
        earlier = last.get(digest)
        if (
            row["status"] == "pending"
            and earlier is not None
            and row["created_at_us"] - earlier <= REGENERATION_US
        ):
            suspects.add(str(row["id"]))
        last[digest] = row["created_at_us"]
    return suspects


def _newest(system: System, operation: str) -> Any:
    versions = _versions(system, operation)
    if not versions:
        return None
    return system.reconstruct_function_receipt(PARTITION, versions[0].receipt.id).document


def _learnable(system: System, operation: str, proposal_id: str, output: object) -> int:
    """Count of the new proposal's case when a learning pass would change something, else 0."""

    suspects = _suspects(system, operation)
    if proposal_id in suspects:
        return 0
    record = system.proposal(PARTITION, proposal_id)
    newest = _newest(system, operation)
    if newest is not None:
        match = evaluate(newest, input_json=canonicalize(record["input"]))
        if match.matched and _same(match.output, output):
            return 0
    (registered,) = [row for row in system.operations(PARTITION) if row["name"] == operation]
    minimum = int(registered["policy"]["min_confirmations"])
    groupings: list[object] = [None]
    if _projectable_state(operation) is not False:
        try:
            groupings.append(draft_program(raw_inputs(system, PARTITION, operation, pending=True)))
        except ValidationError:
            pass
    for program in groupings:
        for case in system.learning_cases(PARTITION, operation, program=program)["cases"]:
            if proposal_id in case["pending_proposal_ids"]:
                count = len(case["active_example_ids"]) + sum(
                    1 for p in case["pending_proposal_ids"] if p not in suspects
                )
                if count >= minimum:
                    return count
    return 0


# -- chat: use + record ------------------------------------------------------


def _registered(system: System, operation: str) -> None:
    if all(row["name"] != operation for row in system.operations(PARTITION)):
        try:
            system.register_operation(PARTITION, operation, registered_by=CHAT)
        except ConflictError:
            pass  # another run registered it first


def _lookup(system: System, operation: str, value: object) -> tuple[str, object, int | None]:
    resolution = system.resolve(PARTITION, operation, value)
    verification = resolution.verification
    versions = _versions(system, operation)
    if not versions:
        return "absent", None, None
    if resolution.switch.mode == "off" or verification is None:
        return "off", None, None
    if not verification.passed:
        return "failed", None, None
    if verification.entries == 0:
        return "absent", None, None
    match = resolution.match
    if match is not None and match.matched:
        return "hit", match.output, _number(versions, verification.function_hash)
    return "unrecognized", None, None


def _prune(tickets: pathlib.Path, now: int) -> None:
    for path in tickets.glob("t_*.json"):
        try:
            used = json.loads(path.read_text(encoding="utf-8"))["used_at_us"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(used, int) and now - used > TICKET_TTL_US:
            path.unlink(missing_ok=True)


def _use(args: argparse.Namespace) -> int:
    text = _read(args.input_file)
    value = {args.field: text.rstrip("\n")} if args.field else _parse(text, "入力")
    if args.field:
        _parse(json.dumps(value), "入力")
    if args.input_file is not None:
        handed = pathlib.Path(args.input_file)
        if handed.parent.resolve() == (_home() / "in").resolve():
            _discard(handed)  # the chat skill's hand-over copy; the ticket keeps the input
    try:
        _home().mkdir(parents=True, exist_ok=True)
        system = System(_home() / "ledger.db", clock_us=_clock_us)
        _registered(system, args.operation)
        reason, output, number = _lookup(system, args.operation, value)
    except ValidationError as exc:
        raise _RefusalError(2, str(exc)) from None
    except (CementError, OSError) as exc:
        # The chat never fails because Cement did: the model answers, and nothing is retained.
        _say(
            f"中止: Cement が使えない ({exc})。",
            "次の手: Cement を使わずに自分で答える。record は流さない。",
        )
        return _status(exc) if isinstance(exc, CementError) else 5
    if reason == "hit":
        _say(
            f"学習済みの関数が答えた ({args.operation} の版 {number})。",
            "出力:",
            _json(output),
            "次の手: この出力をそのまま使って返答を書く。record は流さない。",
        )
        return 0
    now = _clock_us()
    tickets = _home() / "tickets"
    ticket = f"t_{secrets.token_hex(8)}"
    try:
        tickets.mkdir(exist_ok=True)
        _prune(tickets, now)
        _write(
            tickets / f"{ticket}.json",
            {"operation": args.operation, "input": value, "used_at_us": now},
        )
    except OSError as exc:
        _say(
            f"中止: 控えを書けない ({exc.__class__.__name__})。",
            "次の手: Cement を使わずに自分で答える。record は流さない。",
        )
        return 5
    _say(
        f"学習済みの関数はこの頼みに答えない ({REASONS[reason]})。",
        f"控え: {ticket}",
        "次の手: 自分で答えの出力を作る。返答を書く前に、その出力 (JSON) を"
        f" {COMMAND} record {ticket} に渡して記録する。",
    )
    return 0


def _provenance(ticket: str, used_at_us: int, request: str | None) -> dict[str, Any]:
    """The ticket and the user's request, or the request's longest start within the bound."""

    base: dict[str, Any] = {"ticket": ticket, "used_at_us": used_at_us}
    if request is None:
        return base | {"request": None, "request_truncated": False}

    def fits(length: int) -> bool:
        candidate = base | {"request": request[:length], "request_truncated": length < len(request)}
        try:
            canonicalize(candidate, max_bytes=PROVENANCE_MAX_BYTES)
        except ValidationError:
            return False
        return True

    if fits(len(request)):
        return base | {"request": request, "request_truncated": False}
    low, high = 0, len(request)  # fits(low) holds; fits(high) does not
    while high - low > 1:
        middle = (low + high) // 2
        low, high = (middle, high) if fits(middle) else (low, middle)
    return base | {"request": request[:low], "request_truncated": True}


def _record(args: argparse.Namespace) -> int:
    if not TICKET.fullmatch(args.ticket):
        raise _RefusalError(
            2, f"控え {args.ticket!r} の形が違う (use が出した t_ で始まる控えを渡す)。"
        )
    path = _home() / "tickets" / f"{args.ticket}.json"
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
        operation, value, used = held["operation"], held["input"], held["used_at_us"]
    except FileNotFoundError:
        raise _RefusalError(
            3,
            f"控え {args.ticket} が無い (記録済みか、24 時間を過ぎた)。",
            "次の手: 記録は済んだものとして返答を書く。",
        ) from None
    except (OSError, ValueError, KeyError, TypeError):
        raise _RefusalError(
            5, f"控え {args.ticket} が読めない。", "次の手: 記録せずに返答を書く。"
        ) from None
    if not isinstance(used, int) or _clock_us() - used > TICKET_TTL_US:
        _discard(path)
        raise _RefusalError(
            3,
            f"控え {args.ticket} は 24 時間を過ぎた (記録しない)。",
            "次の手: 記録せずに返答を書く。",
        )
    output = _parse(_read(args.output_file), "出力")
    system = _system()
    try:
        proposal_id = system.submit_proposal(
            PARTITION,
            operation,
            value,
            candidate=Candidate(
                output=output, provenance=_provenance(args.ticket, used, args.request)
            ),
            source_id=f"nucllei:{args.ticket}",
        )
    except ConflictError:
        _say(f"控え {args.ticket} は記録済み。", *_discard(path), "次の手: 返答を書く。")
        return 0
    notes = _discard(path)
    try:
        count = _learnable(system, operation, proposal_id, output)
    except CementError:
        count = 0  # the proposal is retained; a later record or a requested pass learns it
    if count:
        _say(
            f"記録した ({operation} の提案 {proposal_id})。同じ場合の答えが {count} 件そろった。",
            *notes,
            "次の手: 返答を書く前に load_skill で cement-learn を読み込み、"
            f"{operation} の学習を済ませる。",
        )
    else:
        _say(f"記録した ({operation} の提案 {proposal_id})。", *notes, "次の手: 返答を書く。")
    return 0


# -- learning pass -----------------------------------------------------------


def _flag(text: str) -> bool:
    return text == "yes"


def _learn(args: argparse.Namespace) -> int:
    system = _system()
    projectable = _flag(args.projectable)
    try:
        work = cases(system, PARTITION, args.operation, projectable=projectable)
    except ValidationError as exc:
        raise _RefusalError(
            2,
            f"用紙の形でまとめられない ({exc})。",
            "次の手: --projectable no で一覧を出し直す。",
        ) from None
    suspects = _suspects(system, args.operation)
    listed = [
        {
            "key": case["key"],
            "key_hash": case["key_hash"],
            "support": case["support"],
            "pending_proposal_ids": case["pending_proposal_ids"],
            "active_example_ids": case["active_example_ids"],
            "regeneration_suspects": [p for p in case["pending_proposal_ids"] if p in suspects],
            "outputs": case["outputs"],
        }
        for case in work["cases"]
    ]
    shown: dict[str, Any] = {
        "operation": args.operation,
        "grouped_by": work["grouped_by"],
        "nothing_to_learn": work["nothing_to_learn"],
        "cases": listed,
        "unprojected": work["unprojected"],
        "stale_pending_proposal_ids": work["stale_pending_proposal_ids"],
    }
    if projectable:
        shown["layouts"] = [layout["title"] for layout in work["program"]["layouts"]]
    grouping = "用紙の形" if projectable else "入力そのもの"
    _say(f"{args.operation} の学習の作業一覧 (まとめ方: {grouping})。", _json(shown))
    return 0


def _show(args: argparse.Namespace) -> int:
    record = _system().proposal(PARTITION, args.proposal_id)
    shown = {
        key: record[key]
        for key in ("id", "operation", "status", "input", "proposed_output", "provenance")
    }
    _say(f"提案 {args.proposal_id}。", _json(shown))
    return 0


def _ids(text: str | None) -> list[str]:
    return [part.strip() for part in (text or "").split(",") if part.strip()]


def _merge(args: argparse.Namespace) -> int:
    projectable = _flag(args.projectable)
    try:
        # The id rules come first, before the output or the ledger is read.
        proposals, examples = check_merge_ids(_ids(args.proposals), _ids(args.examples))
        output = _parse(_read(args.output_file), "まとめた出力")
        done = merge_case(
            _system(),
            PARTITION,
            args.operation,
            output,
            note=f"{args.note} (nucllei)",
            proposal_ids=proposals,
            example_ids=examples,
            projectable=projectable,
        )
    except MergeRefusedError as exc:
        raise _RefusalError(2, MERGE_REFUSALS[exc.reason]) from None
    except MergeInterruptedError as exc:
        # Each write commits alone, so a later refusal must not hide the earlier ones.
        status = _status(exc.cause)
        _say(
            f"中止: 途中で止まった ({exc.cause})。ここまでに書いたもの:",
            _json(dataclasses.asdict(exc.completed)),
            NEXT[status],
        )
        return status
    # Only a pass that wrote rules on projectability; a refused or confused one rules nothing.
    _say(
        "場合をまとめた。", _json(dataclasses.asdict(done)), *_remember(args.operation, projectable)
    )
    return 0


def _reject(args: argparse.Namespace) -> int:
    result = _system().review(
        PARTITION,
        args.proposal_id,
        reviewer=REVIEWER,
        decision="reject",
        note=f"{args.note} (nucllei)",
    )
    _say(f"提案 {args.proposal_id} を退けた ({result.status})。")
    return 0


def _revoke(args: argparse.Namespace) -> int:
    suspended = _system().revoke_example(
        PARTITION, args.example_id, revoked_by=REVIEWER, reason=f"{args.reason} (nucllei)"
    )
    _say(
        f"例 {args.example_id} を取り下げた。これに頼る版は答えなくなる。",
        _json({"suspended_artifact_ids": list(suspended)}),
    )
    return 0


def _publish(args: argparse.Namespace) -> int:
    projectable = _flag(args.projectable)
    system = _system()
    operation = args.operation
    result = publish(system, PARTITION, operation, projectable=projectable)
    notes = _remember(operation, projectable) if result.published or result.reason == "same" else []
    if result.reason is not None:
        _say(
            f"版を作らなかった ({PUBLISH_REASONS[result.reason]})。",
            *notes,
            "次の手: 学習の結果をそのまま報告する。",
        )
        return 0
    versions = _versions(system, operation)
    serving = versions[0].selected
    lines = [
        (
            f"新しい版を作った: {operation} の版 {len(versions)} (場合 {result.entries} 件、"
            f"{str(result.function_hash)[:12]})。"
        )
    ]
    if result.layouts:
        lines.append(
            f"用紙の形: {'、'.join(result.layouts)} (同じ形なら同じ手順で読める、という前提)。"
        )
    lines.append(
        "スイッチが最新の版に追従しているので、この版がすぐに答える。"
        if serving
        else "この版は、ユーザーが /cement-switch でオンにするまで答えない。"
    )
    _say(*lines, *notes)
    return 0


def _list_versions(args: argparse.Namespace) -> int:
    system = _system()
    versions = _versions(system, args.operation, check=True)
    _say(
        f"{args.operation} の版 (新しい順):",
        *_version_lines(versions),
        _switch_line(system, args.operation, versions),
    )
    return 0


def _version_lines(versions: list[Any]) -> list[str]:
    lines = []
    for index, version in enumerate(versions):
        receipt = version.receipt
        notes = [
            f"場合 {receipt.member_count} 件",
            _when(receipt.promoted_at_us),
            receipt.function_hash[:12],
        ]
        if version.selected:
            notes.append("いま答えている")
        if version.servable is False:
            notes.append("検証が通らない")
        lines.append(f"- 版 {len(versions) - index}: {'、'.join(notes)}")
    return lines or ["- まだ版が無い"]


def _switch_line(system: System, operation: str, versions: list[Any]) -> str:
    state = system.switch(PARTITION, operation)
    if state.mode == "off":
        return "スイッチ: オフ (この種類の頼みにはモデルが答える)。"
    if state.mode == "follow":
        return "スイッチ: オン (最新の版に追従)。"
    return f"スイッチ: 版 {_number(versions, state.function_hash)} に固定。"


def _diff(args: argparse.Namespace) -> int:
    system = _system()
    versions = _versions(system, args.operation)
    old, new = _version(versions, args.old), _version(versions, args.new)
    diff = system.diff_versions(
        PARTITION,
        args.operation,
        from_hash=old.receipt.function_hash,
        to_hash=new.receipt.function_hash,
    )
    _say(
        f"{args.operation} の版 {args.old} → 版 {args.new}: 足した場合 {len(diff.added)} 件、"
        f"消えた場合 {len(diff.removed)} 件、出力が変わった場合 {len(diff.changed)} 件、"
        f"用紙の形の読み方は{'変わった' if diff.projection_changed else '同じ'}。"
    )
    return 0


def _read_version(args: argparse.Namespace) -> int:
    system = _system()
    versions = _versions(system, args.operation)
    if not versions:
        raise _RefusalError(3, f"{args.operation} にはまだ版が無い。")
    number = len(versions) if args.version is None else args.version
    receipt = _version(versions, number).receipt
    document = system.reconstruct_function_receipt(PARTITION, receipt.id).document
    lines = [
        (
            f"{args.operation} の版 {number} の中身 (場合 {len(document.entries)} 件、"
            f"{receipt.function_hash[:12]})。"
        ),
        (
            "Cement が持つのは、決まった入力と出力の組だけ (コードではない)。"
            "どの場合にも当たらない入力にはモデルが答える。"
        ),
    ]
    if document.projection is not None:
        titles = [str(layout["title"]) for layout in document.projection.canonical.value["layouts"]]
        lines.append(
            f"用紙の形でまとめている: {'、'.join(titles)}。同じ形の用紙には同じ出力を返す"
            " (同じ形なら同じ手順で読める、という前提)。"
        )
    keyed = " (用紙の形)" if document.projection is not None else ""
    for index, entry in enumerate(document.entries, start=1):
        lines += [
            f"場合 {index}:",
            f"  入力{keyed}: {json.dumps(entry.input.value, ensure_ascii=False)}",
            f"  出力: {json.dumps(entry.output.value, ensure_ascii=False)}",
        ]
    _say(*lines)
    return 0


# -- the person's switch -----------------------------------------------------


def _show_status(_args: argparse.Namespace) -> int:
    system = _system()
    lines = []
    for row in system.operations(PARTITION):
        versions = _versions(system, row["name"], check=True)
        lines += [
            f"{row['name']}:",
            *_version_lines(versions),
            _switch_line(system, row["name"], versions),
        ]
    _say(*(lines or ["まだ何も記録していない。"]))
    return 0


def _switch(args: argparse.Namespace) -> int:
    system = _system()
    versions = _versions(system, args.operation)
    function_hash = None
    if args.state == "pin":
        if args.version is None:
            raise _RefusalError(2, "pin には版の番号が要る (例: switch extraction_plan pin 2)。")
        function_hash = _version(versions, args.version).receipt.function_hash
    elif args.version is not None:
        raise _RefusalError(2, "版の番号は pin のときだけ渡す。")
    mode = {"off": "off", "follow": "follow", "pin": "pinned"}[args.state]
    state = system.set_switch(
        PARTITION, args.operation, mode=mode, actor=PERSON, function_hash=function_hash
    )
    if state.mode == "off":
        _say(f"{args.operation} をオフにした。この種類の頼みにはモデルが答える。")
    elif state.mode == "follow" and not versions:
        _say(f"{args.operation} をオンにした。まだ版が無いので、版が公開されるまでモデルが答える。")
    elif state.mode == "follow":
        _say(f"{args.operation} をオンにした。最新の版 (いまは版 {len(versions)}) が答える。")
    else:
        _say(f"{args.operation} を版 {args.version} に固定した。後の学習で版が増えても変わらない。")
    return 0


# -- command line ------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    """argparse with llens-style refusals: the model reads every line this command prints."""

    def error(self, message: str) -> NoReturn:
        _say(f"中止: コマンドの書き方が違う ({message})。", NEXT[2])
        sys.exit(2)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=COMMAND,
        description="nucllei の利用者 1 人の Cement: 学習した関数は /workspace/.cement に置く。",
        allow_abbrev=False,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    projectable = {"choices": ("yes", "no"), "required": True}

    def command(name: str, handler: Callable[[argparse.Namespace], int], text: str) -> Any:
        sub = commands.add_parser(name, help=text, description=text, allow_abbrev=False)
        sub.set_defaults(handler=handler)
        return sub

    use = command("use", _use, "オンの関数で頼みに 1 回答えるか、控えを出す")
    use.add_argument("operation")
    use.add_argument("--field", help="標準入力を、この入力欄 1 つの文として読む")
    use.add_argument("--input-file", help="入力を標準入力でなくこのファイルから読む")
    record = command("record", _record, "控えの頼みに答えた出力を記録する")
    record.add_argument("ticket")
    record.add_argument("--request", help="ユーザーの頼みの文 (書かれたとおり)")
    record.add_argument("--output-file", help="出力を標準入力でなくこのファイルから読む")
    learn = command("learn", _learn, "操作 1 つの学習の仕事を一覧にする")
    learn.add_argument("operation")
    learn.add_argument("--projectable", **projectable)
    show = command("show", _show, "記録した提案を 1 つ見せる")
    show.add_argument("proposal_id")
    merge = command("merge", _merge, "場合 1 つのまとめた出力を確定する")
    merge.add_argument("operation")
    merge.add_argument("--projectable", **projectable)
    # A model copies the flag of a case that has no ids of that kind, so a bare flag = no ids.
    merge.add_argument(
        "--proposals", nargs="?", const="", help="その場合の保留中の提案の ID (カンマ区切り)"
    )
    merge.add_argument(
        "--examples", nargs="?", const="", help="その場合の有効な例の ID (カンマ区切り)"
    )
    merge.add_argument("--note", required=True, help="まとめで残したものと足したもの")
    merge.add_argument("--output-file", help="まとめた出力をこのファイルから読む")
    reject = command("reject", _reject, "保留中の提案を 1 つ却下する")
    reject.add_argument("proposal_id")
    reject.add_argument("--note", required=True)
    revoke = command("revoke", _revoke, "確定した例のうち誤ったものを 1 つ取り下げる")
    revoke.add_argument("example_id")
    revoke.add_argument("--reason", required=True)
    publish = command("publish", _publish, "新しい版をコンパイルし、検証し、公開する")
    publish.add_argument("operation")
    publish.add_argument("--projectable", **projectable)
    versions = command("versions", _list_versions, "操作 1 つの版を一覧にする")
    versions.add_argument("operation")
    diff = command("diff", _diff, "版を 2 つ番号で比べる")
    diff.add_argument("operation")
    diff.add_argument("old", type=int)
    diff.add_argument("new", type=int)
    read = command("read", _read_version, "版 1 つの場合を見せる")
    read.add_argument("operation")
    read.add_argument("version", type=int, nargs="?")
    command("status", _show_status, "各操作のスイッチと版を見せる")
    switch = command("switch", _switch, "操作 1 つをオフ、オン (最新に追従)、または版の固定にする")
    switch.add_argument("operation")
    switch.add_argument("state", choices=("off", "follow", "pin"))
    switch.add_argument("version", type=int, nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except _RefusalError as refusal:
        _say(f"中止: {refusal}", refusal.next_step)
        return refusal.status
    except CementError as exc:
        _say(f"中止: {exc}", NEXT[_status(exc)])
        return _status(exc)
    except OSError as exc:
        _say(
            f"中止: ファイルを読み書きできない ({exc.__class__.__name__}: {exc})。",
            "次の手: 流し直さない。読み書きできなかったことをユーザーに伝える。",
        )
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
