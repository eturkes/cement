#!/usr/bin/env python3
"""Regenerate the hospital README's sole transcript block; leave all other bytes intact."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MASKS = (
    (re.compile(r"art_[0-9a-f]{32}"), "art_<hex>", 1),
    (re.compile(r"[0-9a-f]{64}"), "<function-hash>", 1),
)
TRANSCRIPT = re.compile(r"(?m)^```text\n(?P<body>[\s\S]*?)^```(?:\n|$)")


def regenerate(readme: str, output: str) -> str:
    for pattern, replacement, expected in MASKS:
        count = len(pattern.findall(output))
        if count != expected:
            raise ValueError(f"mask {replacement}: expected {expected}, found {count}")
    for pattern, replacement, _ in MASKS:
        output = pattern.sub(replacement, output)
    blocks = list(TRANSCRIPT.finditer(readme))
    if len(blocks) != 1:
        raise ValueError(f"expected one transcript block, found {len(blocks)}")
    block = blocks[0]
    return readme[:block.start("body")] + output + readme[block.end("body"):]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without writing.")
    args = parser.parse_args()
    root = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").is_file())
    example = root / "examples/hospital_ocr"
    result = subprocess.run(
        [sys.executable, str(example / "run_demo.py")],
        cwd=root, check=True, capture_output=True, text=True,
    )
    if result.stderr:
        raise ValueError(f"demo wrote stderr: {result.stderr}")
    readme = example / "README.md"
    before = readme.read_bytes()
    after = regenerate(before.decode("utf-8"), result.stdout).encode("utf-8")
    if args.check:
        if after != before:
            print("Hospital transcript differs; run .agent/decisions/m3u8-transcript.py.", file=sys.stderr)
            return 1
    elif after != before:
        readme.write_bytes(after)
    print("Hospital transcript matches the demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
