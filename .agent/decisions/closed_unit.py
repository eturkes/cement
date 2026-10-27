"""Closed-unit inputs from git for shape graders (p149, p152).

A grader that settled a unit's battery against its contract grades the git objects at the unit's
close: later units extend both files, so a working-tree read re-asks a question the unit no longer
owns (`.claude/rules/assurance.md` Tripwires). The live tree stays one named flag away.
"""

import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _commit(rev: str) -> None:
    if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{rev}^{{commit}}"],
                      capture_output=True, check=False).returncode != 0:
        raise SystemExit(f"ABORT   {rev} is not a commit in this clone")


def git_object(rev: str, relpath: str) -> str | None:
    """`relpath` as committed at `rev`; None when `rev` holds no such path; SystemExit if `rev` is unknown."""
    _commit(rev)
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{relpath}"],
                            capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else None


def read(rev: str | None, path: pathlib.Path) -> str:
    """`path` from the working tree (`rev` None) or as committed at `rev` (required to exist)."""
    if rev is None:
        return path.read_text(encoding="utf-8")
    relpath = path.relative_to(ROOT).as_posix()
    text = git_object(rev, relpath)
    if text is None:
        raise SystemExit(f"ABORT   {rev}:{relpath} does not exist")
    return text


def stage(rev: str, relpaths: list[str], into: pathlib.Path) -> pathlib.Path:
    """Write each `relpath` committed at `rev` under `into` (a path `rev` lacks stays absent)."""
    for relpath in relpaths:
        text = git_object(rev, relpath)
        if text is not None:
            target = into / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    return into


def archive(rev: str, pathspecs: list[str], into: pathlib.Path) -> pathlib.Path:
    """Extract the trees `pathspecs` name, as committed at `rev`, under `into` (directory censuses)."""
    _commit(rev)
    tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", rev, "--", *pathspecs],
                         capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(into)], input=tar, check=True)
    return into
