#!/usr/bin/env bash
# Capture every story frame from ONE demo run, so every file shares the same ledger ids.
# Output = visual QA input, gitignored: $OUT (default .scratch/webui-demo-capture/).
#
# The story runs through the API here rather than through `?scene=N`: a scene replay
# always restarts at scene 0, so per-scene captures would each need their own ledger.
#
# Needs a running server and the demo's own browser (README `Visual check`):
#   pnpm --dir prototype/webui-demo install
#   uv run python prototype/webui-demo/app.py &
#   prototype/webui-demo/capture.sh

set -euo pipefail

BASE=${BASE:-http://127.0.0.1:8765}
HERE=$(cd "$(dirname "$0")" && pwd)
[ -d "$HERE/node_modules/playwright" ] || {
  echo "capture.sh: run pnpm --dir prototype/webui-demo install (README \`Visual check\`)" >&2; exit 2; }
OUT=${OUT:-"$(cd "$(dirname "$0")/../.." && pwd)/.scratch/webui-demo-capture"}
mkdir -p "$OUT"

# Every height is MEASURED, never guessed: both columns scroll internally, so a block
# past the fold is simply absent and two frames can come out byte-identical. Each
# numbered frame is sized to its whole right column, measured immediately before the
# capture so a UI change cannot leave a stale number behind.
shot() { # shot <query> <file> [right|left|card]
  local height
  height=$(node "$HERE/measure-height.mjs" "$BASE/?${1}" "${3:-right}")
  node "$HERE/shot.mjs" "$BASE/?${1}" "$OUT/$2" "$height"
}

post() { curl -fsS -X POST -H 'Content-Type: application/json' -d "${2:-{\}}" \
  "$BASE/api/$1" >/dev/null; }

ask() { post send "{\"request_id\":\"$1\"}"; }

learn() { post learn; }

on() { post route "{\"enabled\":true${1:+,\"operation\":\"$1\"}}"; }

post reset
shot 'reset=1' 01-desk.png

ask q01
shot '' 02-answered.png

ask q02
shot '' 03-evidence.png

learn
shot '' 04-cemented.png

on document.extraction_plan
ask q03
shot '' 05-routed.png

ask q05
ask q06
learn
on
shot '' 06-reuse.png

for id in q08 q09 q10 q11; do ask "$id"; done
learn
on
ask q12
learn
shot '' 07-blocked.png

post select '{"scenario":"file"}'
post offline '{"document_id":"A03","operation":"document.extraction_plan"}'
shot 'drawer=document.extraction_plan' 08-bundle.png

# The overlay card is position: fixed, so it is measured as the card plus the .overlay
# 24 px padding on both edges.
shot 'source=document.extraction_plan&open=1' 09-source.png card
node "$HERE/shot.mjs" "$BASE/?expand=1" "$OUT/story-full-page.png" 1000 --full-page
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
