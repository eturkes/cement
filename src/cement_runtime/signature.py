"""Bundle signatures: OpenSSH SSHSIG envelopes over Ed25519, verified in pure Python.

Cement never signs: a person signs an exported bundle with ``ssh-keygen -Y sign -n
cement-function-v3``, and a consumer checks it against an allowed-signers file before the bundle
parses. Verification reads only public data (the key, the signature, the signed bytes), so no branch
depends on a secret and constant-time arithmetic buys nothing; that is why stdlib big integers
suffice. The Ed25519 check is RFC 8032 section 5.1.7 under a strict policy: canonical encodings,
``S < L``, a prime-order key, and the cofactorless equation.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass

from .errors import IntegrityError, ValidationError

FUNCTION_NAMESPACE = "cement-function-v3"
SIGNATURE_MAX_BYTES = 65_536
ALLOWED_SIGNERS_MAX_BYTES = 1_048_576

# edwards25519 (RFC 8032 section 5.1); points in extended coordinates (X, Y, Z, T).
_P = 2**255 - 19
_D = -121665 * pow(121666, -1, _P) % _P
_L = 2**252 + 27742317777372353535851937790883648493
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)

type _Point = tuple[int, int, int, int]

_IDENTITY: _Point = (0, 1, 1, 0)

_ED25519 = b"ssh-ed25519"
_FIDO = frozenset({b"sk-ssh-ed25519@openssh.com", b"sk-ecdsa-sha2-nistp256@openssh.com"})
_HASHES = frozenset({b"sha256", b"sha512"})
_BEGIN = "-----BEGIN SSH SIGNATURE-----"
_END = "-----END SSH SIGNATURE-----"
_PATTERN = frozenset("*?!")


def _add(left: _Point, right: _Point) -> _Point:
    x1, y1, z1, t1 = left
    x2, y2, z2, t2 = right
    a = (y1 - x1) * (y2 - x2) % _P
    b = (y1 + x1) * (y2 + x2) % _P
    c = 2 * t1 * t2 * _D % _P
    d = 2 * z1 * z2 % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _multiply(scalar: int, point: _Point) -> _Point:
    result = _IDENTITY
    while scalar:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(left: _Point, right: _Point) -> bool:
    return (left[0] * right[2] - right[0] * left[2]) % _P == 0 and (
        left[1] * right[2] - right[1] * left[2]
    ) % _P == 0


def _decode_point(raw: bytes) -> _Point | None:
    """A canonical 32-byte encoding, or ``None`` (RFC 8032 section 5.1.3)."""

    if len(raw) != 32:
        return None
    y = int.from_bytes(raw, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _P:
        return None
    square = (y * y - 1) * pow(_D * y * y + 1, -1, _P) % _P
    if square == 0:
        return None if sign else (0, y, 1, 0)
    x = pow(square, (_P + 3) // 8, _P)
    if (x * x - square) % _P:
        x = x * _SQRT_M1 % _P
    if (x * x - square) % _P:
        return None
    if x & 1 != sign:
        x = _P - x
    return (x, y, 1, x * y % _P)


_BX = 15112221349535400772501151409588531511454012693041857206046113283949847762202
_BY = 46316835694926478169428394003475163141307993866256225615783033603165251855960
_BASE: _Point = (_BX, _BY, 1, _BX * _BY % _P)


def _ed25519_verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """RFC 8032 Ed25519 verification under the strict policy; never raises on bytes input."""

    if len(public) != 32 or len(signature) != 64:
        return False
    key = _decode_point(public)
    r = _decode_point(signature[:32])
    if key is None or r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    # A small-order key lets one signature verify many messages (the identity key accepts any
    # R = [S]B), and a mixed-order key makes cofactored and cofactorless verifiers disagree; an
    # honest key [a]B has prime order L, so refusing both never refuses an ssh-keygen signature.
    if _equal(_multiply(8, key), _IDENTITY) or not _equal(_multiply(_L, key), _IDENTITY):
        return False
    k = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % _L
    return _equal(_multiply(s, _BASE), _add(r, _multiply(k, key)))


class _Wire:
    """RFC 4251 ``uint32`` + ``string`` reader over one buffer."""

    def __init__(self, data: bytes, label: str) -> None:
        self.data = data
        self.at = 0
        self.label = label

    def _take(self, size: int) -> bytes:
        if self.at + size > len(self.data):
            raise ValidationError(f"{self.label} is truncated")
        chunk = self.data[self.at : self.at + size]
        self.at += size
        return chunk

    def uint32(self) -> int:
        return int.from_bytes(self._take(4), "big")

    def string(self) -> bytes:
        return self._take(self.uint32())

    def end(self) -> None:
        if self.at != len(self.data):
            raise ValidationError(f"{self.label} has trailing bytes")


def _string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _shown(value: bytes) -> str:
    return value[:64].decode("ascii", "replace")


def _ed25519_key(blob: bytes, label: str, prefix: str = "") -> bytes:
    """The 32-byte key of an ``ssh-ed25519`` key blob; ``prefix`` locates a refusal."""

    wire = _Wire(blob, prefix + label)
    name = wire.string()
    if name in _FIDO:
        raise ValidationError(
            f"{prefix}{_shown(name)} is a FIDO security key type; Cement verifies ssh-ed25519"
            " keys only"
        )
    if name != _ED25519:
        raise ValidationError(f"{prefix}key type {_shown(name)} is unsupported; use ssh-ed25519")
    key = wire.string()
    wire.end()
    if len(key) != 32:
        raise ValidationError(f"{prefix}{label} is not a 32-byte Ed25519 key")
    return key


@dataclass(frozen=True, slots=True)
class _Envelope:
    key_blob: bytes
    key: bytes
    namespace: bytes
    reserved: bytes
    hash_algorithm: bytes
    signature: bytes


def _read_sshsig(text: str) -> _Envelope:
    """One armored SSHSIG envelope (PROTOCOL.sshsig), read strictly."""

    lines = [line.removesuffix("\r") for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) < 3 or lines[0] != _BEGIN or lines[-1] != _END:
        raise ValidationError("signature is not an armored SSH signature")
    try:
        blob = binascii.a2b_base64("".join(lines[1:-1]).encode("ascii"), strict_mode=True)
    except (binascii.Error, UnicodeEncodeError):
        raise ValidationError("signature armor is not valid base64") from None
    if blob[:6] != b"SSHSIG":
        raise ValidationError("signature is not an SSHSIG envelope")
    wire = _Wire(blob[6:], "signature")
    version = wire.uint32()
    if version != 1:
        raise ValidationError(f"SSH signature version {version} is unsupported")
    key_blob = wire.string()
    key = _ed25519_key(key_blob, "signature public key")
    namespace = wire.string()
    if not namespace:
        raise ValidationError("signature namespace is empty")
    reserved = wire.string()
    hash_algorithm = wire.string()
    if hash_algorithm not in _HASHES:
        raise ValidationError(f"signature hash algorithm {_shown(hash_algorithm)} is unsupported")
    signature = _Wire(wire.string(), "signature value")
    wire.end()
    if signature.string() != _ED25519:
        raise ValidationError("signature key type differs from its public key")
    value = signature.string()
    signature.end()
    if len(value) != 64:
        raise ValidationError("signature value is not 64 bytes")
    return _Envelope(key_blob, key, namespace, reserved, hash_algorithm, value)


@dataclass(frozen=True, slots=True)
class _Signer:
    principals: tuple[str, ...]
    namespaces: tuple[str, ...] | None
    key: bytes


def _token(line: str, at: int, number: int) -> tuple[str, int]:
    """The next whitespace-delimited token; double quotes protect spaces (no escapes)."""

    while at < len(line) and line[at] in " \t":
        at += 1
    start, quoted = at, False
    while at < len(line) and (quoted or line[at] not in " \t"):
        quoted ^= line[at] == '"'
        at += 1
    if quoted:
        raise ValidationError(f"allowed signers line {number}: a quote is not closed")
    return line[start:at], at


def _split(text: str) -> list[str]:
    """Comma-separated parts; commas inside double quotes stay in their part."""

    parts: list[str] = []
    start, quoted = 0, False
    for at, character in enumerate(text):
        if character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            parts.append(text[start:at])
            start = at + 1
    parts.append(text[start:])
    return parts


def _names(text: str, what: str, number: int) -> tuple[str, ...]:
    names = tuple(text.split(","))
    if any(not name for name in names):
        raise ValidationError(f"allowed signers line {number}: an empty {what}")
    if any(_PATTERN & set(name) for name in names):
        raise ValidationError(
            f"allowed signers line {number}: {what} patterns are unsupported; list exact names"
        )
    return names


def _is_key_type(token: str) -> bool:
    return token.startswith(("ssh-", "ecdsa-sha2-", "sk-")) or token.endswith(
        "-cert-v01@openssh.com"
    )


def _options(text: str, number: int) -> tuple[str, ...] | None:
    namespaces: tuple[str, ...] | None = None
    for option in _split(text):
        keyword, _, value = option.partition("=")
        if keyword.lower() != "namespaces":
            raise ValidationError(
                f"allowed signers line {number}: option {keyword[:64]} is unsupported"
            )
        if namespaces is not None:
            raise ValidationError(f"allowed signers line {number}: namespaces is repeated")
        if len(value) < 2 or value[0] != '"' or value[-1] != '"':
            raise ValidationError(f"allowed signers line {number}: namespaces must be quoted")
        namespaces = _names(value[1:-1], "namespace", number)
    return namespaces


def _read_allowed_signers(text: str) -> tuple[_Signer, ...]:
    """The ``ssh-ed25519`` lines of an allowed-signers file (``ssh-keygen(1)``, a strict subset)."""

    signers: list[_Signer] = []
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.removesuffix("\r")
        stripped = line.lstrip(" \t")
        if not stripped or stripped.startswith("#"):
            continue
        principals, at = _token(line, 0, number)
        if len(principals) >= 2 and principals[0] == principals[-1] == '"':
            principals = principals[1:-1]
        names = _names(principals, "principal", number)
        token, at = _token(line, at, number)
        namespaces = None
        if token and not _is_key_type(token):
            namespaces = _options(token, number)
            token, at = _token(line, at, number)
        if not _is_key_type(token):
            raise ValidationError(f"allowed signers line {number}: no key type")
        encoded, at = _token(line, at, number)
        if not encoded:
            raise ValidationError(f"allowed signers line {number}: no key")
        if token != _ED25519.decode():
            continue  # never trusted, so skipping it cannot accept anything
        try:
            blob = binascii.a2b_base64(encoded.encode("ascii"), strict_mode=True)
        except (binascii.Error, UnicodeEncodeError):
            raise ValidationError(f"allowed signers line {number}: the key is not base64") from None
        key = _ed25519_key(blob, "the key", f"allowed signers line {number}: ")
        signers.append(_Signer(names, namespaces, key))
    return tuple(signers)


@dataclass(frozen=True, slots=True)
class SignatureVerification:
    """A verified signature: the allowed principals of its key, the key's fingerprint as
    ``ssh-keygen`` prints it, and the hash algorithm the signer chose."""

    principals: tuple[str, ...]
    fingerprint: str
    hash_algorithm: str


def verify_signature(
    data: bytes,
    signature: str,
    allowed_signers: str,
    *,
    namespace: str,
    signer: str | None = None,
) -> SignatureVerification:
    """Verify an armored SSHSIG ``signature`` over ``data`` against ``allowed_signers``.

    Refusals: malformed or unsupported input → ``ValidationError``; a namespace, signer or
    signature that does not match → ``IntegrityError``. A key that ``allowed_signers`` lists without
    a ``namespaces`` option is allowed for every namespace. ``data`` is hashed whole, so the caller
    bounds it.
    """

    if type(data) is not bytes:
        raise ValidationError("signed data must be bytes")
    if type(signature) is not str or type(allowed_signers) is not str:
        raise ValidationError("signature and allowed signers must be text")
    if type(namespace) is not str or not namespace:
        raise ValidationError("namespace must be non-empty text")
    try:
        expected_namespace = namespace.encode("utf-8")
    except UnicodeEncodeError:  # a lone surrogate: text that no signature can carry
        raise ValidationError("namespace must be valid Unicode text") from None
    if signer is not None and (type(signer) is not str or not signer):
        raise ValidationError("signer must be non-empty text")
    signers = _read_allowed_signers(allowed_signers)
    envelope = _read_sshsig(signature)
    if envelope.namespace != expected_namespace:
        raise IntegrityError(
            f"signature namespace is {_shown(envelope.namespace)}, expected {namespace}"
        )
    principals = sorted(
        {
            principal
            for listed in signers
            if listed.key == envelope.key
            and (listed.namespaces is None or namespace in listed.namespaces)
            for principal in listed.principals
        }
    )
    if not principals:
        raise IntegrityError(f"the signing key is not an allowed signer for {namespace}")
    if signer is not None and signer not in principals:
        raise IntegrityError("the signing key is not allowed for that signer")
    digest = hashlib.new(envelope.hash_algorithm.decode(), data).digest()
    signed = b"SSHSIG" + b"".join(
        _string(part)
        for part in (envelope.namespace, envelope.reserved, envelope.hash_algorithm, digest)
    )
    if not _ed25519_verify(envelope.key, signed, envelope.signature):
        raise IntegrityError("signature does not verify")
    fingerprint = base64.b64encode(hashlib.sha256(envelope.key_blob).digest()).rstrip(b"=")
    return SignatureVerification(
        principals=tuple(principals),
        fingerprint="SHA256:" + fingerprint.decode(),
        hash_algorithm=envelope.hash_algorithm.decode(),
    )
