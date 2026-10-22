#!/bin/bash
# nucllei contract gate 4: the generated /ext/bin/cement through one full cycle in a stand-in for
# the nucllei sandbox jail (python:3.12-slim-bookworm = Python 3.12 + SQLite 3.40.1; no network,
# read-only root, uid 65534, tmpfs /workspace, /ext/bin read-only). Host: run from the repo root
# with no argument; rc 0 = every step held. `inner` = the in-container half.
set -euo pipefail
if [ "${1:-}" != inner ]; then
  exec podman run --rm --network none --read-only --user 65534:65534 \
    --tmpfs /workspace:rw,mode=1777 --tmpfs /tmp:rw,mode=1777 \
    -e HOME=/workspace -e LANG=C.UTF-8 -e TZ=Asia/Tokyo -e PATH=/usr/local/bin:/usr/bin:/bin \
    -v "$PWD/examples/nucllei/ext/bin:/ext/bin:ro" -v "$PWD/.agent/decisions/nucllei-jail-smoke.sh:/smoke.sh:ro" \
    docker.io/library/python:3.12-slim-bookworm /smoke.sh inner
fi
C=/ext/bin/cement
expect() { grep -qF -- "$1" "$2" || { echo "FAIL: '$1' missing from $2"; cat "$2"; exit 1; }; }
python3 -c 'import sys,sqlite3;print("python",sys.version.split()[0],"sqlite",sqlite3.sqlite_version)'
printf 'PHYSICIAN PROGRESS NOTE\nPatient: Hana Sato\nMRN: 0001\n' > /tmp/a
printf 'PHYSICIAN PROGRESS NOTE\nPatient: Ken Ito\nMRN: 0002\n' > /tmp/b
printf 'PHYSICIAN PROGRESS NOTE\nPatient: Aiko Mori\nMRN: 0003\n' > /tmp/c
echo '{"fields": [{"name": "patient", "label": "Patient"}]}' > /tmp/plan
echo '{"fields": [{"name": "patient", "label": "Patient"}, {"name": "mrn", "label": "MRN"}]}' > /tmp/wide
ticket() { sed -n 's/^控え: //p' "$1"; }
$C use extraction_plan --field document < /tmp/a > /tmp/u1; expect '(学習済みの版がまだ無い)' /tmp/u1
$C record "$(ticket /tmp/u1)" --request 'どの項目を抜き出す?' < /tmp/plan > /tmp/r1; expect '次の手: 返答を書く。' /tmp/r1
$C use extraction_plan --field document < /tmp/b > /tmp/u2
$C record "$(ticket /tmp/u2)" < /tmp/wide > /tmp/r2; expect 'load_skill で cement-learn を読み込み' /tmp/r2
$C learn extraction_plan --projectable yes > /tmp/l; expect '"PHYSICIAN PROGRESS NOTE"' /tmp/l
ids=$(python3 -c 'import json;t=open("/tmp/l").read().split("\n",1)[1];print(",".join(json.loads(t)["cases"][0]["pending_proposal_ids"]))')
$C merge extraction_plan --projectable yes --proposals "$ids" --note union < /tmp/wide > /tmp/m; expect '場合をまとめた。' /tmp/m
$C publish extraction_plan --projectable yes > /tmp/p; expect 'の版 1 (場合 1 件、' /tmp/p; expect '/cement-switch でオンにするまで答えない' /tmp/p
$C use extraction_plan --field document < /tmp/c > /tmp/u3; expect '(関数がオフ)' /tmp/u3
$C switch extraction_plan follow > /tmp/s; expect 'をオンにした' /tmp/s
mkdir -p /workspace/.cement/in && cp /tmp/c /workspace/.cement/in/plan-1.txt
$C use extraction_plan --field document --input-file /workspace/.cement/in/plan-1.txt > /tmp/u4; expect '学習済みの関数が答えた (extraction_plan の版 1)。' /tmp/u4; expect '"mrn"' /tmp/u4
[ ! -e /workspace/.cement/in/plan-1.txt ] || { echo 'FAIL: the hand-over file was kept'; exit 1; }
$C status > /tmp/st; expect 'スイッチ: オン (最新の版に追従)。' /tmp/st
$C read extraction_plan > /tmp/rd; expect '"title": "PHYSICIAN PROGRESS NOTE"' /tmp/rd
echo "jail smoke: PASS"
