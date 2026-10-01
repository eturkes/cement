#!/usr/bin/env bash
# Capture every story frame from ONE demo run, so every file shares the same ledger ids.
# Output = visual QA input, gitignored: $OUT (default .scratch/webui-demo-capture/).
#
# The story runs through the API here rather than through `?scene=N`: a scene replay
# always restarts at scene 0, so per-scene captures would each need their own ledger.
#
# Needs a running server and `webcap` (headless Chrome over CDP):
#   uv run python prototype/webui-demo/app.py &
#   prototype/webui-demo/capture.sh

set -euo pipefail

BASE=${BASE:-http://127.0.0.1:8765}
OUT=${OUT:-"$(cd "$(dirname "$0")/../.." && pwd)/.scratch/webui-demo-capture"}
mkdir -p "$OUT"

# Every height is MEASURED, never guessed: both columns scroll internally, so a block
# past the fold is simply absent and two frames can come out byte-identical. Each
# numbered frame is sized to its whole right column, measured immediately before the
# capture so a UI change cannot leave a stale number behind.
shot() { # shot <query> <file> [right|left|card]
  local height
  height=$(node "$(dirname "$0")/measure-height.mjs" "$BASE/?${1}" "${3:-right}")
  webcap "$BASE/?${1}" --png "$OUT/$2" --width 1600 --height "$height" \
    --wait 2500 --timeout 60000 >/dev/null
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
shot 'reset=1' 01-desk.png

ask q01
shot '' 02-answered.png

settle
turn q02
shot '' 03-evidence.png

seal
shot '' 04-cemented.png

post route '{"enabled":true}'
ask q03
shot '' 05-routed.png

turn q05
turn q06
seal
shot '' 06-reuse.png

turn q08
turn q09
seal
turn q10
turn q11
seal
turn q12
post compile
shot '' 07-blocked.png

post select '{"scenario":"file"}'
post offline '{"document_id":"A03","operation":"document.extraction_plan"}'
shot '' 08-bundle.png

# The overlay card is position: fixed, so it is measured as the card plus the .overlay
# 24 px padding on both edges.
shot 'source=document.extraction_plan&open=1' 09-source.png card
webcap "$BASE/?expand=1" --png "$OUT/story-full-page.png" --width 1600 --height 1000 \
  --full-page --wait 2500 --timeout 60000 >/dev/null
curl -sS "$BASE/api/transcript.txt" -o "$OUT/transcript.txt"

# The README cites both costs; each run prints its own.
{
  curl -sS "$BASE/api/state" | jq -r '
    (.terminal | map(.ms)) as $cli |
    "cement subprocess: \($cli | length) calls, \($cli | min)-\($cli | max) ms",
    "provider calls: \(.stats.provider_calls) · operations answered by a function: \(.stats.cement_answers) · reviews: \(.stats.reviews)"'
  grep -o '[0-9]\+\.[0-9] ms' "$OUT/transcript.txt" | sed 's/ ms//' | sort -g \
    | awk 'NR==1{min=$1} {max=$1; n++} END{printf "System.resolve: %d calls, %s-%s ms\n", n, min, max}'
} | tee "$OUT/timings.txt"

printf 'frames captured from one run into %s:\n' "$OUT"
file "$OUT"/*.png | sed 's/PNG image data, //'
