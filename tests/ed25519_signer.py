"""Test-only Ed25519 signer + SSHSIG armorer (p135-e5 contract G8).

Its curve arithmetic is written apart from `cement_runtime.signature` (affine coordinates with
modular inverses, RFC 8032 section 5.1.6 signing), so one shared encoding bug cannot make the
signer and the verifier agree with each other alone; `test_signature` pins it against the
RFC 8032 section 7.1 signatures, which are deterministic.
"""

from __future__ import annotations

import base64
import hashlib

P = 2**255 - 19
D = -121665 * pow(121666, -1, P) % P
L = 2**252 + 27742317777372353535851937790883648493
BASE = (
    15112221349535400772501151409588531511454012693041857206046113283949847762202,
    46316835694926478169428394003475163141307993866256225615783033603165251855960,
)


def _add(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    (x1, y1), (x2, y2) = a, b
    t = D * x1 * x2 * y1 * y2 % P
    return (
        (x1 * y2 + x2 * y1) * pow(1 + t, -1, P) % P,
        (y1 * y2 + x1 * x2) * pow(1 - t, -1, P) % P,
    )


def _scale(scalar: int, point: tuple[int, int]) -> tuple[int, int]:
    result = (0, 1)
    for bit in bin(scalar)[2:]:
        result = _add(result, result)
        if bit == "1":
            result = _add(result, point)
    return result


def _encode(point: tuple[int, int]) -> bytes:
    x, y = point
    return (y | (x & 1) << 255).to_bytes(32, "little")


def _expand(seed: bytes) -> tuple[int, bytes]:
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], "little")
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, digest[32:]


def public_key(seed: bytes) -> bytes:
    return _encode(_scale(_expand(seed)[0], BASE))


def sign(seed: bytes, message: bytes) -> bytes:
    scalar, prefix = _expand(seed)
    public = _encode(_scale(scalar, BASE))
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % L
    encoded_r = _encode(_scale(r, BASE))
    k = int.from_bytes(hashlib.sha512(encoded_r + public + message).digest(), "little") % L
    return encoded_r + ((r + k * scalar) % L).to_bytes(32, "little")


def string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def key_blob(seed: bytes, key_type: bytes = b"ssh-ed25519") -> bytes:
    return string(key_type) + string(public_key(seed))


def allowed_line(principals: str, seed: bytes, options: str = "") -> str:
    key = base64.b64encode(key_blob(seed)).decode()
    return " ".join(part for part in (principals, options, "ssh-ed25519", key) if part)


def envelope(
    seed: bytes,
    data: bytes,
    *,
    namespace: bytes = b"cement-function-v3",
    reserved: bytes = b"",
    hash_algorithm: bytes = b"sha512",
) -> bytes:
    """The SSHSIG blob `ssh-keygen -Y sign` would write for this key (PROTOCOL.sshsig)."""

    digest = hashlib.new(hash_algorithm.decode(), data).digest()
    signed = b"SSHSIG" + string(namespace) + string(reserved) + string(hash_algorithm)
    signed += string(digest)
    value = string(b"ssh-ed25519") + string(sign(seed, signed))
    return (
        b"SSHSIG"
        + (1).to_bytes(4, "big")
        + string(key_blob(seed))
        + string(namespace)
        + string(reserved)
        + string(hash_algorithm)
        + string(value)
    )


def armor(blob: bytes) -> str:
    encoded = base64.b64encode(blob).decode()
    lines = [encoded[at : at + 70] for at in range(0, len(encoded), 70)]
    return "\n".join(["-----BEGIN SSH SIGNATURE-----", *lines, "-----END SSH SIGNATURE-----"]) + "\n"
