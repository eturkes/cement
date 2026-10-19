"""M3.6b closure probe: deleting each v3 constraint alone reds the battery test that owns it.

Usage (from a repo checkout): `uv run --no-project --python 3.13 python
.agent/decisions/m3u6b-constraint-probe.py` — copies `src/` + `tests/` to a temp dir, removes one
constraint at a time from the copy's `store.py`, runs the owning test, prints rc per probe, and
exits 1 unless every probe reds. The checkout is never modified.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
S2 = "test_s2_each_new_table_refuses_update_and_delete_on_a_present_row"
S3_PIN = "test_s3_a_pin_must_name_one_receipt_of_its_own_operation"
S3_CHECK = "test_s3_the_switch_check_refuses_every_half_populated_row"
SUPERSEDE = "test_s2_supersession_columns_bind_origin_and_supersede_each_example_once"


def _drop_trigger(text: str, name: str) -> str:
    head = f"CREATE TRIGGER IF NOT EXISTS {name}"
    start = text.index(head)
    end = text.index("END;", start) + len("END;")
    return text[:start] + text[end:]


def _cases(base: str) -> dict[str, tuple[str, str]]:
    check = re.search(r"    CHECK \(\n        \(mode = 'pinned'.*?\n    \),\n", base, re.S)
    assert check is not None
    fk = "    FOREIGN KEY (receipt_id, function_hash) REFERENCES function_receipts(id, function_hash)\n"
    return {
        "projection_programs_no_update": (_drop_trigger(base, "projection_programs_no_update"), S2),
        "projection_settings_no_update": (_drop_trigger(base, "projection_settings_no_update"), S2),
        "switch_settings_no_delete": (_drop_trigger(base, "switch_settings_no_delete"), S2),
        "switch_settings_pin_scope": (_drop_trigger(base, "switch_settings_pin_scope"), S3_PIN),
        "switch_check": (base.replace(check.group(0), ""), S3_CHECK),
        "switch_fk": (base.replace(",\n" + fk, "\n"), S3_PIN),
        "superseded_check": (
            base.replace(
                ",\n    CHECK ((origin = 'superseded') = (supersedes_example_id IS NOT NULL))", ""
            ),
            SUPERSEDE,
        ),
        "supersedes_unique": (
            base.replace(
                "supersedes_example_id TEXT UNIQUE REFERENCES",
                "supersedes_example_id TEXT REFERENCES",
            ),
            SUPERSEDE,
        ),
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cement-m3u6b-probe-") as directory:
        tree = pathlib.Path(directory)
        for name in ("src", "tests", "pyproject.toml"):
            source = ROOT / name
            (shutil.copytree if source.is_dir() else shutil.copy2)(source, tree / name)
        store = tree / "src/cement_runtime/store.py"
        base = store.read_text(encoding="utf-8")
        survivors = []
        for name, (text, test) in _cases(base).items():
            assert text != base, f"{name}: anchor not found"
            store.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "-k", test, "tests.test_schema_v3_battery"],
                cwd=tree,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            print(f"{name:32} rc={result.returncode} {result.stderr.strip().splitlines()[-1]}")
            if result.returncode == 0:
                survivors.append(name)
        store.write_text(base, encoding="utf-8")
    print(f"survivors: {survivors or 'none'}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
