#!/usr/bin/env bash
# p135-e5 fixtures: ssh-keygen-made SSHSIG signatures for tests/test_signature.py.
# Ephemeral keys sign in a private temporary directory; only public keys, the signed message,
# the signatures and allowed-signers files reach tests/fixtures/signature/ (no private key is
# ever committed). Rerunning changes every key + signature; the tests read them, never pin them.
# Usage: .agent/decisions/p135-e5-fixtures.sh  (from the repository root; needs ssh-keygen)
set -euo pipefail
out=tests/fixtures/signature
[ -d "$out" ] || mkdir -p "$out"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
ssh-keygen -q -t ed25519 -N '' -C alice@example.test -f "$work/alice"
ssh-keygen -q -t ed25519 -N '' -C bob@example.test -f "$work/bob"
ssh-keygen -q -t ecdsa -b 256 -N '' -C carol@example.test -f "$work/carol"
printf '{"abi":"cement-function-v3","note":"fixture \xc3\xa9"}\n' > "$work/message"
sign() { # key namespace hashalg output
  cp "$work/message" "$work/signing"
  ssh-keygen -q -Y sign -f "$work/$1" -n "$2" -O "hashalg=$3" "$work/signing" < /dev/null
  mv "$work/signing.sig" "$out/$4"
}
sign alice cement-function-v3 sha512 message.alice.sha512.sig
sign alice cement-function-v3 sha256 message.alice.sha256.sig
sign alice file sha512 message.alice.file.sig
sign bob cement-function-v3 sha512 message.bob.sig
sign carol cement-function-v3 sha512 message.carol.sig
cp "$work/message" "$out/message"
for name in alice bob carol; do cp "$work/$name.pub" "$out/$name.pub"; done
key() { cut -d' ' -f1,2 "$work/$1.pub"; }
{
  echo '# alice signs bundles only; bob signs anything under two names; carol is ECDSA.'
  printf 'alice@example.test namespaces="cement-function-v3" %s alice laptop\n' "$(key alice)"
  printf '"bob@example.test,builder@example.test" %s\n' "$(key bob)"
  printf 'carol@example.test %s\n' "$(key carol)"
} > "$out/allowed_signers"
# Each signature verifies under OpenSSH itself before the fixtures are kept.
check() { # signature principal namespace
  ssh-keygen -q -Y verify -f "$out/allowed_signers" -I "$2" -n "$3" -s "$out/$1" < "$out/message"
}
check message.alice.sha512.sig alice@example.test cement-function-v3
check message.alice.sha256.sig alice@example.test cement-function-v3
check message.bob.sig builder@example.test cement-function-v3
check message.carol.sig carol@example.test cement-function-v3
echo "p135-e5 fixtures written to $out"
