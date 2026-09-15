#!/usr/bin/env bash
# Regenerate proof/ from ONE demo run, so every file shares the same ledger ids.
#
# The story runs through the API here rather than through `?scene=N`: a scene replay
# always restarts at scene 0, so per-scene captures would each need their own ledger.
#
# Needs a running server and `webcap` (headless Chrome over CDP):
#   uv run python prototype/webui-demo/app.py &
#   prototype/webui-demo/capture-proof.sh

set -euo pipefail

BASE=${BASE:-http://127.0.0.1:8765}
OUT="$(cd "$(dirname "$0")" && pwd)/proof"

# Every height below is MEASURED off the rendered PNG, never guessed: both columns
# scroll internally, so a block past the fold is simply absent and two frames can come
# out byte-identical. Each numbered frame is sized to its whole right column.
shot() { # shot <query> <file> [height] [--full-page]
  webcap "$BASE/?${1}" --png "$OUT/$2" --width 1600 --height "${3:-1000}" \
    --wait 2500 --timeout 60000 "${@:4}" >/dev/null
}

post() { curl -sS -X POST -H 'Content-Type: application/json' -d "${2:-{\}}" \
  "$BASE/api/$1" >/dev/null; }

ask() { post send "{\"request_id\":\"$1\"}"; }

# A supervisor corrects what diverges and accepts what already matches. The first
# candidate for a scope always diverges, so a correction is always recorded.
settle() {
  local row
  while :; do
    row=$(curl -sS "$BASE/api/state" \
      | jq -r '.pending[0] | select(.) |
               "\(.proposal_id) \(if (.diff|length) > 0 then "correct" else "accept" end)"')
    [ -z "$row" ] && break
    # shellcheck disable=SC2086
    set -- $row
    post review "{\"proposal_id\":\"$1\",\"decision\":\"$2\"}"
  done
}

seal() { post compile; post verify; post promote; }

turn() { ask "$1"; settle; }

post reset
shot 'reset=1' 01-desk.png 1780

ask q01
shot '' 02-held.png 3080

settle
turn q02
shot '' 03-evidence.png 2280

seal
shot '' 04-cemented.png 2720

post route '{"enabled":true}'
ask q03
shot '' 05-routed.png 2720

turn q05
turn q06
seal
shot '' 06-reuse.png 3380

turn q08
turn q09
seal
turn q10
turn q11
seal
turn q12
post compile
shot '' 07-blocked.png 3140

post select '{"scenario":"file"}'
post offline '{"document_id":"A03","operation":"document.extraction_plan"}'
shot '' 08-bundle.png 3740

# The overlay card is position: fixed, so --full-page reports viewport height and
# cannot size it; the height below is the card's own plus the .overlay 24 px padding
# on both edges, measured off the rendered PNG.
shot 'source=document.extraction_plan&open=1' 09-source.png 6100
shot 'expand=1' story-full-page.png 1000 --full-page
curl -sS "$BASE/api/transcript.txt" -o "$OUT/transcript.txt"

printf 'proof regenerated from one run:\n'
file "$OUT"/*.png | sed 's/PNG image data, //'
