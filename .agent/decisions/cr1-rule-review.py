#!/usr/bin/env python3
"""cr1-rule-review — enter the code review's rulings into `.agent/review.md` (idempotent patcher).

Section = `## Code review (MAINTAIN, request)`; its 430-row check set was committed with every cell
`unknown`. This patcher owns two things there: each row's verdict + basis, and the `### Findings`
register after the table (one row per finding: severity, anchor, proof, fix, status).
  (no flag)  write the rulings; a row whose cells hold another ruling refuses (rc 2), never overwrites
  --check    rc 0 iff the section holds exactly these rulings + this register, else rc 1 + each diff
  --ledger P grade or write P instead (a scratch copy)
Verdicts: `pass` | `finding <ids>` | `excluded (<reason>)`. A pass basis that cites a reviewer = that
teammate's report scope, MAIN's own check = the report read + every lead it raised rerun.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".agent/review.md"
HEAD = "## Code review (MAINTAIN, request)"
REGISTER = "### Findings (code review)"

# Fix commits by stack position; the closing commit (`ledger`) lands this table.
FIX = {
    "c1": "7ce5447", "c2": "98ea105", "c3": "a7f9bc4", "c4": "11f657b", "c5": "d42467e",
    "c6": "117e90a", "c7": "37a1a62", "c8": "78362fa", "c9": "82d31a4", "c10": "d14ad45",
    "c11": "dc55023", "c12": "d47fd36", "c13": "93bdd75", "c14": "110aa60", "c15": "1eb7570",
    "c16": "8959e51", "c17": "c77a051", "c18": "5e7d596", "c19": "1f3b491", "c20": "b7b27ec",
    "c21": "dbae3cc", "c22": "b0418f8", "c23": "dd853b9", "c24": "0699e05", "c25": "d551bff",
    "c26": "afa2298", "c27": "3a717f3", "c28": "374750b", "c29": "6a70852",
    "ledger": "the commit landing this table",
    # general-purpose-2's gate-tooling commits (cherry-picked); the tests-integrity class waits on the owner.
    "g2": "4bb5304", "g3": "7ce9c0f", "g9": "bd203c8", "g5": "51683f7", "g8": "2cefd87", "g7": "5e2db62", "g6": "41fd3e5",
    # the tests-integrity class, owner-approved at the closing question (`Land all`)
    "wire": "ad0b5b2", "billing": "8669977",
    "t1": "f1a9470", "t2": "9d50ba2", "t3": "dcbda01", "t4": "0db6dcf",
}


def fix(key: str) -> str:
    return f"fixed `{FIX[key]}`" if key != "ledger" else f"fixed in {FIX[key]}"


# id, severity, anchor (`file:line` at the review base), proof, status
FINDINGS: list[tuple[str, str, str, str, str]] = [
    ("SEC-1", "minor", "src/cement_runtime/store.py:557", "out-of-band trigger `sqliteXhidden` passed the live-schema census (`LIKE 'sqlite_%'`: `_` = any char)", fix("c1")),
    ("reviewer-3-F1", "major", "src/cement_runtime/system.py:4906", "pinned-version program load outside `_pin_checks`' containment: `resolve` + `function versions` raised IntegrityError", fix("c2")),
    ("reviewer-2-F1", "major", "src/cement_runtime/system.py:650", "`_structural_edit_leaves` on a full-width-only v2 layout → `max()` of an empty sequence", fix("c3")),
    ("reviewer-5-F1", "major", "src/cement_runtime/projection.py:327", "`draft_program` emitted layouts its own parser refuses (single-line input; U+0130 title)", fix("c3")),
    ("reviewer-4-F1", "major", "src/cement_runtime/system.py:520", "stored malformed JSON surfaced as ValidationError / exit 2, not IntegrityError / exit 5 (20 stored-row sites)", fix("c4")),
    ("reviewer-4-F3", "major", "src/cement_runtime/store.py:734", "existing-only open under a missing parent → exit 2", "retired: D13 pins exit 2 for that open (contract)"),
    ("reviewer-4-F2", "major", "src/cement_runtime/store.py:718", "relative ledger path re-resolved per open → one System read + wrote a second ledger after `chdir` (+ `shadow.py:232`)", fix("c5")),
    ("reviewer-6-F1", "minor", "src/cement_runtime/shadow.py:246", "new shadow file + ledger created `0600 & ~umask`, no `fchmod` (+ `store.py:742`)", fix("c6")),
    ("reviewer-1-F1", "major", "src/cement_runtime/system.py:2067", "receipt envelope consumed the depth/item budget: legal boundary values refused at review (+ challenge, supersession, reader)", fix("c7")),
    ("reviewer-7-F2", "minor", "src/cement_runtime/cli.py:656", "export temporary name passed NAME_MAX for a legal 244-byte basename", fix("c7")),
    ("reviewer-9-F2", "major", "examples/command_source/command_source.py:138", "protocol wrapper consumed the input's depth/item budget (= reviewer-1-F1 class)", fix("c7")),
    ("reviewer-1-F3", "minor", "src/cement_runtime/system.py:1533", "`revise_operation` at the maximum revision → OverflowError", fix("c8")),
    ("reviewer-7-F1", "major", "src/cement_runtime/cli.py:897", "`function read` said a suspended selected version answers (resolve exits 6)", fix("c9") + "; its test repair owner-approved"),
    ("reviewer-15-F1", "major", "src/cement_runtime/cli.py:989", "projected `function read` omitted the program + the structure-only assumption (Decision M4)", fix("c10")),
    ("reviewer-2-F2", "major", "src/cement_runtime/system.py:6645", "`learning_cases` reported `nothing_to_learn` while a republish would restore `follow`", fix("c11")),
    ("reviewer-1-F2", "minor", "src/cement_runtime/system.py:2141", "`review` re-loaded + re-parsed the projection program per member (12 loads vs 1)", fix("c12")),
    ("reviewer-6-F2", "minor", "src/cement_runtime/signature.py:357", "a non-ASCII namespace raised UnicodeEncodeError, not ValidationError", fix("c13")),
    ("reviewer-8-F1", "major", "examples/open_webui/cement_filter.py:366", "a duplicate admit returned before finishing a `prepared` disagreement", fix("c14")),
    ("reviewer-8-F2", "major", "examples/open_webui/local.py:235", "`provision` overwrote saved shadow valves on each `serve`", fix("c15")),
    ("reviewer-9-F1", "major", "examples/nucllei/cement_nucllei.py:161", "concurrent passes lost one operation's projectability ruling (state-file read-modify-write)", fix("c16")),
    ("reviewer-15-F2", "minor", "examples/nucllei/cement_nucllei.py:756", "argparse help + usage errors English (Decision: model-facing output Japanese)", fix("c17")),
    ("reviewer-9-F3", "minor", "examples/nucllei/cement_nucllei.py:747", "`follow` with no published version said `版 0 が答える`", fix("c17")),
    ("SEC-3", "major", "examples/nucllei/skills/cement.md:36", "model answers passed through heredocs: an answer line equal to the delimiter ends it and runs the rest in the user's jail (+ `cement-learn.md:43`)", fix("c18")),
    ("L.nucllei.7", "minor", "examples/nucllei/cement_nucllei.py:334", "catalogue mutant L.nucllei.7 (`use` keeps its hand-over file) survived all 47 `tests.test_nucllei_example` tests", fix("c18")),
    ("L.open-webui.2", "minor", "examples/open_webui/generate.py:27", "catalogue mutant L.open-webui.2 (no `import importlib.machinery`) survived W1 + N7", fix("c19")),
    ("SEC-2", "info", "src/cement_runtime/signature.py:107", "comment misstated which keys satisfy the cofactorless equation (code refuses them correctly)", fix("c20")),
    ("reviewer-3-F2", "minor", "src/cement_runtime/system.py:4088", "`resolve` docstring cited the pre-cache cost as current", fix("c20")),
    ("reviewer-4-F4", "minor", "src/cement_runtime/system.py:7496", "stale comment `other records are joined.`", fix("c20")),
    ("reviewer-4-F5", "minor", "src/cement_runtime/store.py:576", "`never raised to callers` vs `_ReadOnlyViolation` escaping `Store.transaction`", fix("c20")),
    ("reviewer-4-F6", "minor", "src/cement_runtime/models.py:1", "`Small immutable public values` vs plain dict records", fix("c20")),
    ("reviewer-5-F2", "minor", "src/cement_runtime/errors.py:16", "ConflictError doc omitted the identical source-id repeat", fix("c20")),
    ("reviewer-6-F3", "minor", "src/cement_runtime/comparator.py:4", "`single walk` vs nested `unordered` revisits", fix("c20")),
    ("reviewer-6-F4", "minor", "src/cement_runtime/learning.py:245", "publish `rerun … without new rows` vs a failed rerun adding a report + event", fix("c20")),
    ("reviewer-6-F5", "minor", "src/cement_runtime/shadow.py:915", "`every stored field` omitted `artifact_hash` + `comparator_json`", fix("c20")),
    ("reviewer-7-F3", "minor", "src/cement_runtime/cli.py:939", "comparator readout `letter case ignored` without the ASCII-only qualifier", fix("c20")),
    ("reviewer-11-F1", "major", "skills/cement-learn/SKILL.md:27", "exit 2/3 `wrote nothing` vs `learn merge` exit 3 after a committed review", fix("c21")),
    ("reviewer-11-F2", "major", "README.md:543", "retention + erase `one transaction` vs two files (+ `docs/threat-model.md:88`)", fix("c21")),
    ("reviewer-11-F3", "minor", "README.md:606", "every write `one event` + every refusal `writes nothing` vs compile + commit-then-raise", fix("c21")),
    ("reviewer-11-F4", "major", "examples/open_webui/README.md:8", "paste-in path omitted Python ≥3.12 (paste-ins SyntaxError on 0.12.3's stock 3.11)", fix("c21")),
    ("reviewer-11-F5", "minor", "examples/open_webui/README.md:11", "`about 370 KB` vs 504-526 kB (= reviewer-8 register)", fix("c21")),
    ("reviewer-11-F8", "minor", "README.md:349", "`an argument list above 131,071 bytes` = the per-argument bound", fix("c21")),
    ("reviewer-1-R1", "minor", "README.md:678", "`cannot make it fail` unqualified vs `expected_revision`", fix("c21")),
    ("reviewer-8-F3", "major", "examples/open_webui/cement-learn/SKILL.md:16", "`a refusal wrote nothing` vs publish committing before refusing", fix("c21")),
    ("reviewer-8-F4", "minor", "examples/open_webui/cement_learning.py:245", "`never answers until a person switches it on` vs `follow` (= reviewer-2 register)", fix("c21")),
    ("reviewer-15-F5", "minor", "examples/nucllei/README.md:60", "`less than 10 minutes` vs the inclusive bound (= reviewer-9-F4)", fix("c21")),
    ("SEC-4", "minor", ".gitignore:11", "`<ledger>.shadow` + `-journal` (plaintext inputs + answers) not ignored", fix("c22")),
    ("reviewer-4-R1", "minor", ".claude/rules/runtime.md:23", "law said an authorizer denial lands as IntegrityError / exit 5; code raises `_ReadOnlyViolation`", fix("c22")),
    ("SEC-5", "minor", "examples/nucllei/cement_nucllei.py:706", "pre-switch `read` listing printed C1/bidi/zero-width characters raw", fix("c23")),
    ("operator-2-F1", "minor", "prototype/webui-demo/static/app.js:817", "reload reset the band narration despite a populated session", fix("c24")),
    ("operator-2-F3", "minor", "prototype/webui-demo/static/app.js:845", "default band named Cement beyond the p95 ruling (= reviewer-15-F4)", fix("c24")),
    ("reviewer-15-F3", "minor", "prototype/webui-demo/static/app.js:795", "`six-check verification and caches nothing` = an unlabelled false runtime claim (+ `demo.py:1437`)", fix("c24")),
    ("operator-2-F2", "major", "prototype/webui-demo/demo.py:1256", "billing q12 resent → support 2 → promoted, vs the Decision `every scope stays at support 1` + UI `never repeats`", fix("billing") + " (owner-ruled: the Decision + UI wording moves, the runtime stays)"),
    ("F-pins-1", "minor", "examples/open_webui/local-requirements.txt", "`.agent/pins` rc 1: 3 lock transitives BEHIND with no queue row", fix("c25")),
    ("reviewer-10-F1", "major", ".agent/skip-census:69", "`_aliases` oscillated forever on a cross-module alias collision (gate step never ends)", fix("c26")),
    ("reviewer-10-F4", "major", ".agent/decisions/m3-deferred-validate.py:124", "an unfinished acceptance on a continuation line passed", fix("c27")),
    ("reviewer-10-F2", "major", ".agent/survivor-triage:239", "kills credited without a pristine control run (+ `.agent/kill-check:73`)", fix("g2")),
    ("reviewer-10-F3", "major", ".agent/survivor-triage:66", "class subjects dropped decorator + field lines from scope", fix("g3")),
    ("reviewer-10-F5", "major", ".agent/decisions/m3u5a-battery-validate.py:199", "4 battery graders accepted comment-only assertions (+ `m3u5a-suite-validate.py:131`, `m3u5b-battery-validate.py:397`, `m3u6a1-battery-validate.py:273`)", fix("g5")),
    ("reviewer-10-F6", "major", ".agent/decisions/wave_validate.py:656", "`ColumnTables` never enforced its seed floor", fix("g6")),
    ("reviewer-10-F7", "major", ".agent/decisions/m3u6a2-battery-validate.py:144", "self-test credited a zero counter", fix("g7")),
    ("reviewer-10-F8", "minor", ".agent/validate-anchors:55", "files reread per row (+ `m3u5a-suite-validate.py:127`)", fix("g8")),
    ("reviewer-10-F9", "minor", ".agent/seeds:7", "`every recorded recipe` vs the groups' actual coverage", fix("g9")),
    ("reviewer-12-F1", "minor", "tests/test_system.py:4877", "lock-order test sampled `time.monotonic()` after each call returned: a permitted schedule failed it", fix("t4") + " (owner-approved)"),
    ("reviewer-12-F2", "minor", "tests/test_system.py:15630", "one-snapshot report test delegated commit/cursor/batch calls + allowed transaction control: a mid-report commit passed", fix("t2") + " (owner-approved)"),
    ("reviewer-13-F1", "minor", "tests/test_cli.py:3541", "export exit-map token assertion compared the actual value with itself for exits 2-5", fix("t1") + " (owner-approved)"),
    ("reviewer-13-F2", "major", "tests/test_read_capability_census.py:173", "read censuses classified SQL by its first token: a write behind a SELECT, comment or CTE passed (+ `:209`, `test_read_capability_battery.py:792`)", fix("t2") + " (owner-approved)"),
    ("reviewer-13-F3", "minor", "tests/test_retention_battery.py:406", "`if False` disabled the expected prune digest", fix("t1") + " (owner-approved)"),
    ("reviewer-13-F4", "major", "tests/test_proposal_binding_battery.py:154", "SQL recorder returned raw cursors: a chained query ran unrecorded (class sweep: D13 + D17 recorders)", fix("t2") + " (owner-approved)"),
    ("reviewer-14-F1", "minor", "tests/test_function.py:741", "entry-cap pin repeated ONE entry: a cap loosened by one still raised as a duplicate", fix("t3") + " (owner-approved)"),
    ("L-ondemand", "minor", ".claude/rules/ops.md:14", "p03, p76, p94, p10 + `m3-deferred-validate.py` fire on planted input yet no gate step runs them (an unkeyed departure from `CLAUDE.md` `Engineering`: a purpose-built check is wired into the gate); p76 went red at this review's stack tip (M87) with the gate green", fix("wire") + " (owner-approved; p10 waits on p143)"),
    ("L-census", "minor", "CLAUDE.md + .claude/rules (6 clauses)", "frontmatter quoting + live globs, `@` imports, project settings, dangling links, machine paths, suppression reasons: tool-decidable, no check; no proof a gate run leaves the tree clean", fix("c28")),
    ("operator-1-F1", "minor", "examples/open_webui/cement-learn/SKILL.md:79", "live pass reported `support 1` for a case at 2: the skill's support came from the pre-merge listing (+ nucllei skill)", fix("c29") + "; live rerun = deferred row"),
    ("F-ledger-1", "minor", ".agent/review.md:489", "`## Security review 2 (MAINTAIN, request)` heading lost in `686e86e`'s splice", fix("ledger")),
    ("reviewer-11-F6", "minor", ".agent/deferred.md:27", "p137 `0.12.3 is both the latest release` vs p144 (0.12.4 released)", fix("ledger")),
    ("reviewer-11-F7", "minor", ".agent/deferred.md:29", "p142 `cold resolve plus the capture's cold verification` vs capture reusing resolve's entry", fix("ledger")),
]

R = "MAIN: report read, its leads rerun"


def rv(n: int, scope: str) -> str:
    return f"reviewer-{n} pass ({scope}); {R}"


ROWS: dict[str, tuple[str, str]] = {
    "B1": ("pass", "CI run 40276994772 on `686e86e`: both legs, every step rc 0, Ran 1621 (3.15) / 1620 (3.12), D28 39 revisions / 3 replayed; the closing commit's full gate = section close line"),
    "B2": ("pass", "import-and-call smoke at the package boundary: register → propose → review → compile → verify_drafts → inspect + promote → set_switch → resolve hit, rc 0"),
    "B3": ("pass", "`uv run cement --help` + README quick start end to end in a temp dir (signed `function eval` included), every leaf rc as documented"),
    "B4": ("pass", "every `Artifacts`-named leaf driven in a temp dir; `function drift`/`observations` without a shadow file → exit 3 as documented"),
    "B5": ("pass", "fresh `claude -p` + the skill alone: 1 version `promoted_by learning-pass`, 0 `function.switched`, injected proposal rejected, support-1 case kept"),
    "B6": ("pass", "`All checks passed.`; `m3u8-transcript.py --check` rc 0"),
    "B7": ("pass", "`generate.py --check` rc 0 (paste-ins fresh)"),
    "B8": ("finding operator-1-F1", "operator-1: setup (0.12.3 / CPython 3.12.15) → serve → provision → 2 retained notes → learning pass promotes (support 2) → admin action `follow` → covered note answered by the function, no proposal; the learning reply misstated support"),
    "B9": ("pass", "`.agent/owui-audit` rc 0: 127 findings held on p137"),
    "B10": ("pass", "operator-1: `m5u3-smoke.py` 6/6 cases"),
    "B11": ("pass", "nucllei `generate.py --check` rc 0 + mode 755; `nucllei-jail-smoke.sh` PASS (Python 3.12.15, SQLite 3.40.1)"),
    "B12": ("pass", "`tests.test_outbox_example` 5 OK + `outbox.py` run"),
    "B13": ("pass", "gate step `wheels` rc 0 on both CI legs (B1)"),
    "B14": ("finding operator-2-F1 operator-2-F2 operator-2-F3", "operator-2: capture rc 0 (10 distinct frames), density story 245/16 + reset 156/13, quality floor rc 0 both states, Japanese census pass"),
    "C1": ("finding reviewer-1-F1 reviewer-1-F3", R),
    "C2": ("finding reviewer-2-F1 reviewer-2-F2", R),
    "C3": ("finding reviewer-3-F1", R + "; MAIN's own read of `_pin_checks` confirmed"),
    "C4": ("finding reviewer-4-F1", R),
    "C5": ("finding reviewer-4-F2 SEC-1", R + "; reviewer-4-F3 retired against D13"),
    "C6": ("pass", rv(4, "models")),
    "C7": ("pass", rv(5, "function")), "C8": ("pass", rv(5, "artifacts")), "C9": ("pass", rv(5, "json_value")),
    "C10": ("pass", rv(5, "pkg")), "C11": ("pass", rv(5, "source")),
    "C12": ("finding reviewer-5-F1", R),
    "C13": ("pass", rv(6, "comparator")), "C14": ("pass", rv(6, "learning")),
    "C15": ("finding reviewer-6-F1", R), "C16": ("finding reviewer-6-F2", R),
    "C17": ("finding reviewer-7-F1 reviewer-7-F2", R),
    "C18": ("finding reviewer-8-F1", R), "C19": ("finding reviewer-8-F2", R),
    "C20": ("finding reviewer-9-F1 SEC-5", R + "; SEC-5 = MAIN (security, worked alone)"),
    "C21": ("pass", rv(9, "ocr")), "C22": ("pass", rv(9, "outbox")),
    "C23": ("finding reviewer-9-F2", R),
    "C24": ("pass", rv(10, "g-chain")),
    "C25": ("finding reviewer-10-F1", R),
    "C26": ("finding reviewer-10-F2 reviewer-10-F3 reviewer-10-F4 reviewer-10-F5 reviewer-10-F6 reviewer-10-F7", R),
    "C27": ("finding SEC-4", "reviewer-10 lead (pass with a `.gitignore` note); MAIN: `git check-ignore x.db.shadow` rc 1"),
    "K1": ("finding reviewer-1-F2", R),
    "A1": ("finding reviewer-1-F1 reviewer-1-F2", R),
    "S1": ("pass", rv(1, "sys-intake docstrings + error text")),
    "K2": ("pass", rv(2, "sys-build")),
    "A2": ("finding reviewer-2-F1 reviewer-2-F2", R),
    "S2": ("finding reviewer-2-F1 reviewer-2-F2", R),
    "K3": ("pass", rv(3, "sys-serve")), "A3": ("pass", rv(3, "sys-serve")),
    "S3": ("finding reviewer-3-F2", R),
    "K4": ("pass", rv(4, "sys-config")), "K5": ("pass", rv(4, "store")), "K6": ("pass", rv(4, "models")),
    "A4": ("finding reviewer-4-F1", R),
    "A5": ("pass", rv(4, "store")), "A6": ("pass", rv(4, "models")),
    "S4": ("finding reviewer-4-F4", R),
    "S5": ("finding reviewer-4-F5", R + "; reviewer-4-F3 retired against D13"),
    "S6": ("finding reviewer-4-F6", R),
    "S7": ("pass", rv(5, "function")), "S8": ("pass", rv(5, "artifacts")), "S9": ("pass", rv(5, "json_value")),
    "S10": ("finding reviewer-5-F2", R), "S11": ("pass", rv(5, "source")),
    "S12": ("finding reviewer-5-F1", R),
    "S13": ("finding reviewer-6-F3", R), "S14": ("finding reviewer-6-F4", R), "S15": ("finding reviewer-6-F5", R),
    "S16": ("finding reviewer-6-F2 SEC-2", R),
    "S17": ("finding reviewer-7-F1 reviewer-7-F2 reviewer-7-F3", R),
    "S18": ("finding reviewer-8-F3 reviewer-8-F4", R),
    "S19": ("pass", rv(8, "owui-gen")),
    "S20": ("finding reviewer-9-F3 reviewer-15-F5", R + " (reviewer-9-F4 = reviewer-15-F5)"),
    "S21": ("pass", rv(9, "ocr")), "S22": ("pass", rv(9, "outbox")), "S23": ("pass", rv(9, "cmdsrc")),
    "S24": ("pass", rv(10, "g-chain")),
    "S25": ("finding reviewer-10-F1", R),
    "S26": ("finding reviewer-10-F2 reviewer-10-F4 reviewer-10-F5 reviewer-10-F6 reviewer-10-F7 reviewer-10-F9", R),
    "S27": ("pass", rv(10, "config")),
    "S28": ("finding reviewer-11-F1", R),
    "S29": ("finding reviewer-11-F2 reviewer-11-F3 reviewer-11-F8 reviewer-1-R1", R),
    "S30": ("finding reviewer-11-F2", R),
    "S31": ("finding reviewer-11-F4 reviewer-11-F5", R),
    "S32": ("pass", rv(11, "artifacts-spec")),
    "S33": ("pass", rv(7, "59 help pages, 76 CLI calls") + "; MAIN B3/B4 drove the leaves"),
    "S34": ("finding reviewer-11-F6 reviewer-11-F7 F-ledger-1", R),
    "V1": ("finding reviewer-12-F1 reviewer-12-F2", R),
    "V2": ("finding reviewer-13-F1", R),
    "V3": ("finding reviewer-13-F2 reviewer-13-F3 reviewer-13-F4", R + "; class sweep adds D13 + D17 recorders"),
    "V4": ("finding reviewer-14-F1", R),
    "V5": ("pass", rv(14, "every example test module")),
    "V6": ("pass", rv(14, "16 modules, AST census") + "; MAIN census: no unittest/pytest/sys.modules/env branch in src"),
    "V7": ("pass", rv(14, "15 example modules") + "; MAIN census over examples"),
    "V8": ("finding reviewer-10-F5 reviewer-10-F6 reviewer-10-F7 L.nucllei.7 L.open-webui.2", "MAIN: `.agent/seeds` S02-S23 at `6992036` 124/125 MATCH (S23 `shipped` = F-pins-1; 8/8 at the stack tip), S01 fast cases MATCH + full table = B1; checks that did not fire = the listed findings"),
}
for n in range(7, 13):
    ROWS.setdefault(f"K{n}", ("pass", rv(5, ["function", "artifacts", "json_value", "pkg", "source", "projection"][n - 7])))
    ROWS.setdefault(f"A{n}", ("pass", rv(5, ["function", "artifacts", "json_value", "pkg", "source", "projection"][n - 7])))
for n, scope in zip(range(13, 17), ("comparator", "learning", "shadow", "signature")):
    ROWS.setdefault(f"K{n}", ("pass", rv(6, scope)))
    ROWS.setdefault(f"A{n}", ("pass", rv(6, scope)))
ROWS.update({
    "K17": ("pass", rv(7, "cli")), "A17": ("finding reviewer-7-F1", R),
    "K18": ("pass", rv(8, "owui-src")), "K19": ("pass", rv(8, "owui-gen")),
    "A18": ("pass", rv(8, "owui-src")), "A19": ("pass", rv(8, "owui-gen")),
    "K20": ("pass", rv(9, "nucllei")), "K21": ("pass", rv(9, "ocr")), "K22": ("pass", rv(9, "outbox")), "K23": ("pass", rv(9, "cmdsrc")),
    "A20": ("pass", rv(9, "nucllei")), "A21": ("pass", rv(9, "ocr")), "A22": ("pass", rv(9, "outbox")),
    "A23": ("finding reviewer-9-F2", R),
    "K24": ("pass", rv(10, "g-chain")), "K25": ("pass", rv(10, "g-steps")),
    "K26": ("finding reviewer-10-F8", R), "K27": ("pass", rv(10, "config")),
    "A24": ("pass", rv(10, "g-chain")), "A25": ("pass", rv(10, "g-steps")),
    "A26": ("finding reviewer-10-F3 reviewer-10-F5 reviewer-10-F6", R),
})
SPEC = {11: "reviewer-15-F1", 14: "reviewer-15-F2", 21: "reviewer-15-F5", 22: "reviewer-15-F3 operator-2-F2 operator-2-F3"}
for n in range(1, 23):
    ROWS[f"F{n}"] = (f"finding {SPEC[n]}", R) if n in SPEC else ("pass", "reviewer-15 pass (its Intent + Decisions obligation map for this module); " + R)

# --- L rows: one per bullet of `CLAUDE.md` + `.claude/rules/*.md` (T = a tool decides, J = judged on the lens rows named)
X_CONV = "excluded (conversation/collaboration: binds no tracked file)"
X_PROC = "excluded (session process: binds no tracked file)"
X_HIST = "excluded (history/commit-message law: binds no tracked file)"
X_TEAM = "excluded (teammate mechanics: binds no tracked file)"
X_SEC = "excluded (security: owner body `Security review`; security defects met here worked by MAIN)"
X_METH = "excluded (unit-closure / campaign method: binds the work, not a tracked file)"
LAW = "T: law-census (gate step `law`, seeds S24) — no check existed"
for i in (1, 2, 3, 4):
    ROWS[f"L.cl.{i}"] = (X_CONV, "")
for i in (6, 7, 8, 12, 13, 36, 37, 40, 41, 42, 43, 44, 57, 58, 62, 63, 64, 65, 66, 67):
    ROWS[f"L.cl.{i}"] = (X_PROC, "")
for i in range(46, 54):
    ROWS[f"L.cl.{i}"] = (X_TEAM, "")
for i in (26, 27, 28, 29, 30, 31):
    ROWS[f"L.cl.{i}"] = ("pass", "J: code diff lenses — judged on the C/K/A rows")
ROWS.update({
    "L.cl.5": ("pass", "J: installs project-local — gate tools in gitignored `.tools/` (`.agent/fetch-tool`), `.venv`, `.open-webui/`; judged on C27/K27"),
    "L.cl.9": ("finding SEC-4 L-census", "commit law = history; `.gitignore` current = T: `git check-ignore x.db.shadow` rc 1 (SEC-4) + no proof a gate run leaves the tree clean → CI clean-tree step after each leg"),
    "L.cl.10": ("pass", "T: `.agent/gate` prints rc + seconds + `Slowest test durations` — seeds S01 (`missing-module` rc 1, `durations`) + CI step tables"),
    "L.cl.11": ("pass", "T: `.agent/ci-gate` wrong arg count / dirty tree → rc 2; green run deleted `ci/cr`, red run 40280902361 kept it (rc 1)"),
    "L.cl.14": ("pass", "process part excluded; T: tracked dangling links = law-census `symlinks` (0; self-test plant fires)"),
    "L.cl.15": ("pass", "prototype UI under PROTOTYPE law (Template ruling (1)); quality floor `quality.mjs` rc 0 at reset + story (B14)"),
    "L.cl.16": ("pass", "T: no chart or figure tracked (`git ls-files` image census 0) ⇒ palette gate vacuous"),
    "L.cl.17": ("pass", "J: agent-optimized text — judged on the K/S rows + rules upkeep"),
    "L.cl.18": ("pass", "J: rules upkeep pass at this close (no dates, provenance or origin story added)"),
    "L.cl.19": ("pass", "J: rules + skills state actions positively (rules upkeep pass)"),
    "L.cl.20": ("pass", "J: `.claude/agents/` = template copies (fixes upstream); briefs = process"),
    "L.cl.21": ("pass", "T: register-audit prints sentence length, never grades it (seeds S13)"),
    "L.cl.22": ("finding L-census", LAW + " (`portable`: home-directory paths in live law, config, code + docs)"),
    "L.cl.23": ("finding L-census", LAW + " (`frontmatter`: quoting + every glob matches a tracked file)"),
    "L.cl.24": ("finding L-census", LAW + " (`imports`: each `@` line names a tracked file)"),
    "L.cl.25": ("pass", "T: filler ban = seeds S13 + S19 (register) + S17 (articles); register = J on S29-S31"),
    "L.cl.32": ("pass", "T: `.agent/seeds` refuses a bullet count ≠ group count; S01-S23 fired"),
    "L.cl.33": ("pass", "J: test scope — judged on the V rows"),
    "L.cl.34": (X_PROC, "the B rows drove each runnable artifact"),
    "L.cl.35": ("pass", "T: skip set = seeds S12; J rest on V1-V8"),
    "L.cl.38": ("finding p143", "T: `p10-scratch-census.py` rc 1 (5 unmarked = open p143); stays on demand until p143 closes (owner)"),
    "L.cl.39": ("pass", "T: W1 + N7 + `generate.py --check` rc 0 (B7, B11); catalogue L.nucllei.1 + L.open-webui.1 killed"),
    "L.cl.45": (X_SEC, ""),
    "L.cl.54": ("pass", "T: `.agent/spec-lint` (seeds S03); `Phase` = `MAINTAIN — whole product`"),
    "L.cl.55": ("pass", "T: spec-lint gate step + seeds S03"),
    "L.cl.56": ("pass", "J: `Artifacts` records `prototype/webui-demo/` (S32)"),
    "L.cl.59": ("pass", "T: spec-lint (seeds S03); no routed state open"),
    "L.cl.60": ("pass", "T: template fidelity = `copy-template --check` in the agents repo (template-refresh section R1); no portable in-repo gate (another repo)"),
    "L.cl.61": ("pass", "J: rules upkeep at this close"),
    "L.cl.68": ("finding SEC-4 L-census", "= L.cl.9 `.gitignore` half"),
})
for i in (2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 16, 18, 20, 23, 24, 25, 26, 34, 35, 36, 37, 44, 45, 47, 48, 49, 50, 51, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62):
    ROWS[f"L.assurance.{i}"] = (X_METH, "")
for i in (1, 10, 15, 17, 19, 28, 29, 30, 31, 32, 33, 38, 39, 40, 41, 42, 43, 46, 52):
    ROWS[f"L.assurance.{i}"] = ("pass", "J: judged on the V rows (V1-V8)")
ROWS.update({
    "L.assurance.9": ("pass", "T: no `tests/` module names `prototype/`; wheel = `cement_runtime` alone, sdist excludes prototype (`uv build` in B1; `test_publication_metadata`)"),
    "L.assurance.13": ("pass", "T: gate step `skips` rc 0 (B1); seeds S12 5/5 (planted shapes); its loop defect = reviewer-10-F1"),
    "L.assurance.21": ("pass", "T: replay-mutants / mutate / survivor-triage / kill-check set PYTHONDONTWRITEBYTECODE + purge; this review's 40 replays restored every clone"),
    "L.assurance.22": ("pass", "T: seeds S14 `anchor-miss` rc 2"),
    "L.assurance.27": ("pass", "T: seeds S14 embed seed; this review's replays regenerated the copies (L.nucllei.7 survived honestly, no phantom W1/N7 kill)"),
    "L.ops.1": ("pass", "T: no runtime dependency (`test_publication_metadata`) + `ext/bin/cement` under `python -I -S` (N7); `uv run` everywhere = J"),
    "L.ops.2": ("pass", "T: seeds S01 (missing-module rc 1, durations, full table) + CI step tables"),
    "L.ops.3": ("pass", "T: seeds S01 fast form `.agent/gate tests.<module>`"),
    "L.ops.4": ("finding L-census", "T: seeds S09 format/lint/types (+RUF100), S10 audit, S11 gitleaks, S21 zizmor, S22 shellcheck fire; a suppression's REASON had no check → law-census `reasons` (85 in scope, 0 violations)"),
    "L.ops.5": ("pass", "T: seeds S12; CI outer skipped none"),
    "L.ops.6": ("pass", "T: seeds bullet-count guard + S01-S23"),
    "L.ops.7": ("pass", "T: L24 / authority / submission censuses green with this review's new tests (suite)"),
    "L.ops.8": ("finding L-ondemand", "T: `m3-deferred-validate.py` fires (seeds S04 23/23) yet ran on demand only → owner-approved: gate step `queue`; retired-name sweep = D25 battery"),
    "L.ops.9": ("pass", "T: (1) prototype outside gates (L.assurance.9); (2) scanners in the gate (B1 steps); (5) ci-gate firing (L.cl.11); (3) = this ledger"),
    "L.ops.10": (X_HIST, ""),
    "L.ops.11": (X_PROC, ""),
    "L.ops.12": ("finding L-ondemand", "T: each fires on a planted input — p03 `int(row[...])` rc 1, p94 revision outside HEAD's history rc 1, p76 organically (M87 at the stack tip), p10 rc 1 (p143), p46 `--self-test`; none ran in the gate → owner-approved: gate steps `stored-ints`, `anchors`, `revisions` + seeds S25; p10 waits on p143"),
    "L.ops.13": (X_PROC, ""),
    "L.ops.14": ("finding L-census", LAW + " (`settings`: no tracked project `.claude/settings.json`)"),
    "L.ops.15": (X_HIST, ""),
    "L.ops.16": (X_PROC, ""),
})
for i in (1, 3, 5, 8, 9, 10, 13, 15, 16, 17, 18, 19, 20, 21, 24, 26, 30, 31, 36, 37, 39, 40, 41, 42):
    ROWS[f"L.runtime.{i}"] = ("pass", f"T: catalogue mutant L.runtime.{i} killed (`.agent/decisions/cr1-*.jsonl`, replay-mutants rc 0)")
for i in (4, 6, 7, 14, 22, 23, 25, 27, 28, 29, 33, 34, 35, 38):
    ROWS[f"L.runtime.{i}"] = ("pass", "J: judged on the C/S rows of `src/`")
ROWS.update({
    "L.runtime.2": ("pass", "T: `p03-stored-int-census.py` rc 0 + fires on a planted `int(row[...])` (on demand; L.ops.12)"),
    "L.runtime.11": ("finding reviewer-4-R1", "T: catalogue mutant L.runtime.11 killed; the clause's denial path was stale (`_ReadOnlyViolation`, not IntegrityError)"),
    "L.runtime.12": ("pass", "T: read-capability battery VACUUM parity test (suite)"),
    "L.runtime.32": ("pass", "T: X23 + parser-shape digest census (`tests/test_cli_channels.py`); the clause prescribes test design (catalogue note)"),
})
for i in range(1, 24):
    ROWS[f"L.gate-checks.{i}"] = ("pass", f"T: seeds group S{i:02d} MATCH at `6992036`")
ROWS["L.gate-checks.1"] = ("pass", "T: seeds S01 `missing-module` + `durations` MATCH; full table = CI B1")
ROWS["L.gate-checks.23"] = ("pass", "T: seeds S23 firing cases 7/7 MATCH at `6992036`; `shipped` DIFF = F-pins-1 (8/8 at the stack tip)")
ROWS.update({
    "L.history-gates.1": ("pass", "T: D28 in CI's full leg (`D28: 51 revisions, 1 replayed`); every stack commit's suite replayed by D28"),
    "L.history-gates.2": ("pass", "T: seeds S05 6/6 (a planted red never recorded) + `D28VerdictCacheTests`"),
    "L.history-gates.3": ("pass", "J/T: ci-gate + offload launch under SIG_DFL (seeds S05/S07 ran)"),
    "L.history-gates.4": (X_PROC, ""),
    "L.history-gates.5": ("pass", "T: CI full leg = one `discover` with D28; split leg named (`suite: SPLIT RUN — omits …`)"),
    "L.history-gates.6": ("pass", "T: seeds S07 4/4 pairing"),
    "L.history-gates.7": ("pass", "T: `WorktreeOrphanTests` (suite)"),
    "L.history-gates.8": ("pass", "T: `m3u6a2-tripwires.py` PASS after each prose fix"),
    "L.history-gates.9": ("pass", "T: seeds S08 4/4 `SWAPPED_ROOTS` purge"),
    "L.human-facing.1": ("pass", "J: claims re-derived against shipped code on S29-S31 (findings there)"),
    "L.human-facing.2": ("pass", "J: publication claims on S29 (absent shadow file → exit 3 documented, B4)"),
    "L.human-facing.3": ("pass", "J/T: D23 parses shell blocks for placeholders (suite); quick start placeholders produced earlier in each block (B3)"),
    "L.human-facing.4": ("pass", "J: threat-model Trusted list read (S30)"),
    "L.human-facing.5": ("pass", "J: unqualified-form sweep with each S fix"),
    "L.human-facing.6": ("finding reviewer-3-F2", "J: `resolve` docstring cited the pre-cache cost as current; README qualified it"),
    "L.human-facing.7": ("pass", "T: gate step `register` + seeds S13/S19"),
    "L.human-facing.8": ("pass", "T: gate step `articles` + seeds S17"),
    "L.human-facing.9": ("pass", "T: register-audit splits bullets + table cells (seeds S13)"),
    "L.nucllei.1": ("pass", "T: catalogue L.nucllei.1 killed (N7 freshness + mode)"),
    "L.nucllei.2": ("pass", "T: `nucllei-jail-smoke.sh` PASS (B11)"),
    "L.nucllei.3": ("finding reviewer-15-F2", "T/J: llens-style Japanese — argparse help + usage errors were English"),
    "L.nucllei.4": ("pass", "T: catalogue L.nucllei.4 killed (N6 AST pin)"),
    "L.nucllei.5": ("pass", "T: catalogue L.nucllei.5 killed (N8)"),
    "L.nucllei.6": ("pass", "T: tripwires `DOCS` + D23 `added_surfaces` (suite)"),
    "L.nucllei.7": ("finding L.nucllei.7 SEC-3", "T: catalogue mutant L.nucllei.7 survived; the skills' heredoc hand-over = SEC-3"),
    "L.nucllei.8": ("pass", "owner-deferred (p142); no tracked nucllei shadow code"),
    "L.nucllei.9": ("pass", "J: bookkeeping in `cement_runtime.learning` (C14); reviewer-9-F1 = the command's own state file"),
    "L.open-webui.1": ("pass", "T: catalogue L.open-webui.1 killed (W1 refusals)"),
    "L.open-webui.2": ("finding L.open-webui.2", "T: catalogue mutant L.open-webui.2 survived W1 + N7"),
    "L.open-webui.3": ("pass", "T: item ids pinned by `tests.test_open_webui_local` plan tests + live provision (B8)"),
    "L.open-webui.4": ("pass", "T: catalogue L.open-webui.4 killed (W2)"),
    "L.open-webui.5": ("pass", "T: catalogue L.open-webui.5 killed (W3 AST pin)"),
    "L.open-webui.6": ("pass", "T: catalogue L.open-webui.6 killed (`_loggable`); the recovery defect = reviewer-8-F1"),
    "L.open-webui.7": ("pass", "J: learning tool division held in the live pass (B8)"),
    "L.open-webui.8": ("pass", "J: measured-live facts reproduced in B8 (`search_tools`, action dialog)"),
    "L.open-webui.9": ("pass", "T: catalogue L.open-webui.9 killed (`test_s1_*`); the valve overwrite = reviewer-8-F2"),
    "L.open-webui.10": ("pass", "T: W1/W2/W3 firing re-proven by catalogue kills (L.open-webui.1/.4/.5)"),
    "L.pins.1": ("finding F-pins-1", "T: `.agent/pins` rc 1 — 3 lock transitives BEHIND, no queue row"),
    "L.pins.2": ("pass", "J: each pin's home read against its file"),
    "L.pins.3": ("pass", "T: `test_p128_the_lock_pins_the_target_and_hashes_every_package` (suite)"),
    "L.pins.4": ("pass", "T: `.agent/pins` grades each Python line (3.15 full, 3.12 split, Open WebUI 3.12, jail 3.12)"),
    "L.pins.5": (X_PROC, "a fact about D28 keys; `uv.lock` untouched by this review"),
    "L.prototype.1": ("pass", "T: no `tests/` module names the prototype; prototype-only revisions owe no gate"),
    "L.prototype.2": ("pass", "T: server readiness via `until curl -sf` (B14)"),
    "L.prototype.3": ("pass", "T: `capture.sh` rc 0, 10 PNGs, duplicate-hash count 0 (positive control 1)"),
    "L.prototype.4": ("pass", "T: measured-height frames complete (B14)"),
    "L.prototype.5": ("pass", "T: `quality.mjs` rc 0 at reset + story (B14)"),
    "L.prototype.6": ("pass", "T: `density.mjs` story 245/16, reset 156/13 (B14)"),
    "L.prototype.7": ("pass", "J: Back checkpoints exercised along the story only (operator-2 coverage note)"),
    "L.prototype.8": ("pass", "T: the pinned headless shell via `browser.mjs` (B14)"),
    "L.prototype.9": (X_PROC, ""),
    "L.prototype.10": ("pass", "T: `?lang=ja` Latin-node census pass (B14)"),
    "L.example-demo.4": ("pass", "J: demo teardown order — B6 `All checks passed.`"),
    "L.example-demo.5": ("pass", "J: self-consistent bundle loop (`OfflineBundleTests`)"),
    "L.example-demo.8": ("pass", "T: `tests/test_hospital_ocr_example.py` holds the demo pins (suite)"),
    "L.example-demo.9": (X_PROC, "probe-authoring method"),
})
for i in (1, 2, 3, 6, 7):
    ROWS[f"L.example-demo.{i}"] = ("pass", f"T: catalogue mutant L.example-demo.{i} killed")

ROW = re.compile(r"^\| (?P<id>[A-Za-z0-9.-]+) \| (?P<lens>[A-Z]) \| (?P<target>.*) \| (?P<verdict>[^|]*) \| (?P<basis>[^|]*) \|$")


def cell(text: str) -> str:
    return text.replace("|", "\\|") if text else "—"


# The closing commit's full gate; filled by amending that commit once its CI run is green.
CLOSE_RUN = "CI run 40333517498 on the commit landing this table (both legs, every step rc 0; Ran 1651 / 1650)"


def register() -> list[str]:
    verdicts = [verdict.split(" ")[0] for verdict, _ in ROWS.values()]
    statuses = [row[4].split(" ")[0] for row in FINDINGS]
    close = (f"Close: {len(ROWS)}/{len(ROWS)} rows adjudicated (pass {verdicts.count('pass')}, finding "
             f"{verdicts.count('finding')}, excluded {verdicts.count('excluded')}); {len(FINDINGS)} findings "
             f"(fixed {statuses.count('fixed')}, retired {statuses.count('retired:')}); full gate = {CLOSE_RUN}.")
    lines = [REGISTER, "", close, "", "| id | sev | anchor | proof | status |", "|---|---|---|---|---|"]
    lines += [f"| {i} | {s} | `{a}` | {cell(p)} | {cell(t)} |" for i, s, a, p, t in FINDINGS]
    return [*lines, ""]


def section(lines: list[str]) -> tuple[int, int]:
    start = lines.index(next(line for line in lines if line.startswith(HEAD)))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end


def render(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    start, end = section(lines)
    body = lines[start:end]
    if REGISTER in body:
        cut = body.index(REGISTER)
        body = body[:cut]
        while body and not body[-1]:
            body.pop()
        body.append("")
    seen: set[str] = set()
    out, conflicts = [], []
    for line in body:
        match = ROW.match(line)
        if match and match["id"] in ROWS:
            seen.add(match["id"])
            verdict, basis = ROWS[match["id"]]
            new = f"| {match['id']} | {match['lens']} | {match['target']} | {verdict} | {cell(basis)} |"
            if (match["verdict"], match["basis"]) != ("unknown", "unknown") and line != new:
                conflicts.append(f"{match['id']}: holds `{match['verdict']}`")
            out.append(new)
        else:
            out.append(line)
    missing = sorted(set(ROWS) - seen) + [f"unruled {m['id']}" for m in map(ROW.match, out) if m and m["verdict"] == "unknown"]
    return lines[:start] + out + register() + lines[end:], conflicts, missing


def main(argv: list[str]) -> int:
    ledger = pathlib.Path(argv[argv.index("--ledger") + 1]) if "--ledger" in argv else LEDGER
    old = ledger.read_text(encoding="utf-8").split("\n")
    new, conflicts, missing = render(old)
    referenced = {word for verdict, _ in ROWS.values() if verdict.startswith("finding") for word in verdict.split()[1:]}
    listed = {row[0] for row in FINDINGS}
    retired = {row[0] for row in FINDINGS if row[4].startswith("retired")}
    gaps = sorted(referenced - listed - {"p143"}) + [f"unreferenced {i}" for i in sorted(listed - referenced - retired)]
    for problem in [*missing, *gaps]:
        print(f"GAP {problem}")
    if "--check" in argv:
        changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b] or ([len(old)] if len(old) != len(new) else [])
        for i in changed[:20]:
            print(f"DIFF line {i + 1}")
        print(f"cr1-rule-review: {len(ROWS)} rows, {len(FINDINGS)} findings, {len(changed)} differing lines")
        return 1 if changed or missing or gaps else 0
    pending = [key for key, sha in FIX.items() if sha == "PENDING"]
    if pending:
        print(f"PENDING fix commits: {pending}")
    if conflicts or missing or gaps or pending:
        for conflict in conflicts:
            print(f"CONFLICT {conflict}")
        return 2
    ledger.write_text("\n".join(new), encoding="utf-8")
    print(f"cr1-rule-review: wrote {len(ROWS)} rows + {len(FINDINGS)} findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
