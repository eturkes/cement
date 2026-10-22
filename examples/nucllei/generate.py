"""Generate `ext/bin/cement`: `cement_nucllei.py` with `cement_runtime` embedded, one file.

The nucllei sandbox jail has no network and no package installer, and llens deploys a jail
command as one file under `ext/bin/`. The embedding is the Open WebUI generator's. Run from any
directory:

    uv run python examples/nucllei/generate.py           # writes examples/nucllei/ext/bin/cement
    uv run python examples/nucllei/generate.py --check   # writes nothing; rc 1 when stale
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import stat
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "cement_nucllei.py"
TARGET = HERE / "ext" / "bin" / "cement"
SHEBANG = "#!/usr/bin/env python3\n"
MODE = 0o755


def _embedding() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "open_webui_generate", HERE.parent / "open_webui" / "generate.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("generate: examples/open_webui/generate.py is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected() -> str:
    embedding = _embedding()
    root = embedding._root()
    return SHEBANG + embedding.render(
        SOURCE.read_text(encoding="utf-8"),
        embedding.runtime_sources(root),
        embedding._version(root),
        generator="examples/nucllei/generate.py",
        refresh="copy ext/bin/cement from the repository again",
    )


def stale() -> bool:
    if not TARGET.is_file():
        return True
    return (
        TARGET.read_text(encoding="utf-8") != expected()
        or stat.S_IMODE(TARGET.stat().st_mode) != MODE
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the nucllei jail command.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when stale")
    args = parser.parse_args(argv)
    if args.check:
        if stale():
            sys.stderr.write("generate: ext/bin/cement is stale; run generate.py\n")
            return 1
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected(), encoding="utf-8")
    TARGET.chmod(MODE)
    sys.stdout.write(f"wrote {TARGET.relative_to(HERE.parent.parent)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
