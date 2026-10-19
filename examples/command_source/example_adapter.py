"""Installed protocol stub for local exploration. This is deliberately not an LLM."""

import json
import sys


def main() -> None:
    request = json.load(sys.stdin)
    json.dump(
        {
            "output": {"kind": "echo", "value": request["input"]},
            "provenance": {"adapter": "example-stub", "model": None},
        },
        sys.stdout,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


if __name__ == "__main__":
    main()
