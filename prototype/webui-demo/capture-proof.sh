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

shot() { # shot <query> <file> [height] [--full-page]
  webcap "$BASE/?${1}" --png "$OUT/$2" --width 1600 --height "${3:-1000}" \
    --wait 2500 --timeout 60000 "${@:4}" >/dev/null
}

post() { curl -sS -X POST -H 'Content-Type: application/json' -d "${2:-{\}}" \
  "$BASE/api/$1" >/dev/null; }

pending() { curl -sS "$BASE/api/state" | jq -r '.pending[0].proposal_id'; }

review() { post review "{\"proposal_id\":\"$(pending)\",\"decision\":\"$1\"}"; }

post reset
shot 'reset=1' 01-desk.png

post send '{"document_id":"A01"}'
shot '' 02-held.png

review correct
post send '{"document_id":"A02"}'
review accept
shot '' 03-evidence.png

post compile
post verify
post promote
shot '' 04-cemented.png

post route '{"enabled":true}'
post send '{"document_id":"A03"}'
shot '' 05-routed.png

post send '{"document_id":"C01"}'
review accept
post compile
shot '' 06-boundary.png

post offline '{"document_id":"A03"}'
shot '' 07-bundle.png

shot 'source=1&open=1' 08-source.png 2600
shot 'expand=1' story-full-page.png 1000 --full-page
curl -sS "$BASE/api/transcript.txt" -o "$OUT/transcript.txt"

printf 'proof regenerated from one run:\n'
file "$OUT"/*.png | sed 's/PNG image data, //'
