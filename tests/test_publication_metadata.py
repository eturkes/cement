"""p90: publication metadata for an index release.

PyPI renders README.md as the long description outside the repository, so a relative link or a
bare in-page anchor resolves against pypi.org instead; every link names the repository instead,
and a `blob/main/<path>` target names a tracked file. Both distributions name the repository and
their docs in `[project.urls]`.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/eturkes/cement"
LINK = re.compile(r"\]\(([^)\s]+)\)")


class PublicationMetadataTests(unittest.TestCase):
    def test_both_distributions_name_the_repository_and_their_docs(self) -> None:
        expected = {
            "pyproject.toml": f"{REPOSITORY}/tree/main/docs",
            "examples/command_source/pyproject.toml": f"{REPOSITORY}/tree/main/examples/command_source",
        }
        for path, documentation in expected.items():
            with self.subTest(path=path):
                urls = tomllib.loads((ROOT / path).read_text(encoding="utf-8"))["project"]["urls"]
                self.assertEqual(urls, {"Repository": REPOSITORY, "Documentation": documentation})
                self.assertTrue((ROOT / documentation.removeprefix(f"{REPOSITORY}/tree/main/")).is_dir())

    def test_every_readme_link_is_absolute_and_names_a_tracked_file(self) -> None:
        tracked = set(
            subprocess.run(
                ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
            ).stdout.splitlines()
        )
        for readme in ("README.md", "examples/command_source/README.md"):
            text = (ROOT / readme).read_text(encoding="utf-8")
            for target in LINK.findall(text):
                with self.subTest(readme=readme, target=target):
                    self.assertTrue(target.startswith(f"{REPOSITORY}/") or target.startswith(f"{REPOSITORY}#"))
                    if "/blob/main/" in target:
                        self.assertIn(target.split("/blob/main/", 1)[1], tracked)
        self.assertGreaterEqual(len(LINK.findall((ROOT / "README.md").read_text(encoding="utf-8"))), 10)


if __name__ == "__main__":
    unittest.main()
