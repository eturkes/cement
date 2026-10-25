#!/usr/bin/env python3
"""p135-e5 gate 3: Cement's SSHSIG verifier vs `ssh-keygen -Y verify`, both directions.

Direction A: an ephemeral `ssh-keygen` key signs each variant → Cement must accept.
Direction B: `tests/ed25519_signer.py` (contract G8) signs each variant → `ssh-keygen` must accept.
Every variant with one flipped byte (data or an envelope field) → both must refuse.
rc 0 = every row agrees with its expectation; 1 = a disagreement; 2 = setup failure.
Usage: uv run python .agent/decisions/p135-e5-differential.py (needs ssh-keygen; no network)
"""

from __future__ import annotations

import base64
import pathlib
import subprocess
import sys
import tempfile


def _root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve().parent
    while not (here / "pyproject.toml").exists():
        here = here.parent
    return here


ROOT = _root()
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from cement_runtime import CementError  # noqa: E402
from cement_runtime.signature import verify_signature  # noqa: E402
from tests import ed25519_signer as signer  # noqa: E402

NAMESPACES = ("cement-function-v3", "file")
ALGORITHMS = ("sha512", "sha256")
DATA = (b"", b'{"abi":"cement-function-v3"}\n', bytes(range(256)) * 40)
SEED = bytes(range(7, 39))


def keygen_verify(work: pathlib.Path, allowed: str, namespace: str, data: bytes, armored: str) -> bool:
    (work / "allowed").write_text(allowed + "\n")
    (work / "check.sig").write_text(armored)
    run = subprocess.run(
        ["ssh-keygen", "-q", "-Y", "verify", "-f", str(work / "allowed"), "-I", "alice@x",
         "-n", namespace, "-s", str(work / "check.sig")],
        input=data, capture_output=True, check=False,
    )
    return run.returncode == 0


def cement_verify(allowed: str, namespace: str, data: bytes, armored: str) -> bool:
    try:
        verify_signature(data, armored, allowed, namespace=namespace, signer="alice@x")
    except CementError:
        return False
    return True


def blob(armored: str) -> bytes:
    return base64.b64decode("".join(l for l in armored.splitlines() if not l.startswith("-----")))


def flips(raw: bytes) -> list[tuple[str, bytes]]:
    """One flipped byte at the end of each envelope field's value."""

    out, at = [], 10
    for name in ("key", "namespace", "reserved", "hash_algorithm", "signature"):
        size = int.from_bytes(raw[at : at + 4], "big")
        if size:
            index = at + 4 + size - 1
            out.append((name, raw[:index] + bytes([raw[index] ^ 1]) + raw[index + 1 :]))
        at += 4 + size
    return out


def main() -> int:
    rows: list[tuple[str, bool, bool, bool]] = []  # label, expected, cement, ssh-keygen
    with tempfile.TemporaryDirectory() as name:
        work = pathlib.Path(name)
        try:
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "alice@x", "-f", str(work / "key")],
                check=True, stdin=subprocess.DEVNULL, capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"SETUP ssh-keygen unavailable: {exc}", file=sys.stderr)
            return 2
        public = (work / "key.pub").read_text().split()
        keygen_allowed = f"alice@x {public[0]} {public[1]}"
        test_allowed = signer.allowed_line("alice@x", SEED)
        for namespace in NAMESPACES:
            for algorithm in ALGORITHMS:
                for index, data in enumerate(DATA):
                    tag = f"{namespace}/{algorithm}/data{index}"
                    message = work / "message"
                    message.write_bytes(data)
                    subprocess.run(
                        ["ssh-keygen", "-q", "-Y", "sign", "-f", str(work / "key"), "-n", namespace,
                         "-O", f"hashalg={algorithm}", str(message)],
                        check=True, stdin=subprocess.DEVNULL, capture_output=True,
                    )
                    made = (work / "message.sig").read_text()
                    (work / "message.sig").unlink()
                    test_made = signer.armor(
                        signer.envelope(SEED, data, namespace=namespace.encode(),
                                        hash_algorithm=algorithm.encode(), reserved=b"")
                    )
                    for direction, allowed, armored in (
                        ("A ssh-keygen-signed", keygen_allowed, made),
                        ("B test-signed", test_allowed, test_made),
                    ):
                        rows.append((f"{direction} {tag}", True,
                                     cement_verify(allowed, namespace, data, armored),
                                     keygen_verify(work, allowed, namespace, data, armored)))
                        changed = data + b"x"
                        rows.append((f"{direction} {tag} data+1", False,
                                     cement_verify(allowed, namespace, changed, armored),
                                     keygen_verify(work, allowed, namespace, changed, armored)))
                        for field, raw in flips(blob(armored)):
                            tampered = signer.armor(raw)
                            rows.append((f"{direction} {tag} flip {field}", False,
                                         cement_verify(allowed, namespace, data, tampered),
                                         keygen_verify(work, allowed, namespace, data, tampered)))
    bad = [row for row in rows if not (row[1] == row[2] == row[3])]
    for label, expected, cement, keygen in rows:
        mark = "OK  " if expected == cement == keygen else "DIFF"
        print(f"{mark} expect={expected!s:5} cement={cement!s:5} ssh-keygen={keygen!s:5} {label}")
    print(f"RESULT: {len(rows)} rows, {len(bad)} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
