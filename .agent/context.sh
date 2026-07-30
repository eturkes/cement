#!/bin/sh
# Context gauge → "N% used/240K" from an assistant turn's usage sum (input+cache_creation+cache_read
# +output) = the CLI's own compaction input. High reads = normal: sys/tools/CLAUDE.md + redacted thinking
# bill from cached input the .jsonl omits; server-tool turns (ToolSearch) bill per internal iteration.
# 240K = auto-compaction point (ACW 273K − 33K; raw 1M = informational); warn 220K. Teammates share it.
# Usage: context.sh [-p] [<teammate>]
#   (no arg)   → MAIN, last turn = live occupancy: this session id, else this project's newest transcript
#   <teammate> → spawned role name (`name` in agent-*.meta.json) or raw agent id, at any depth under this
#                project's sessions (plain + workflow nestings) — newest match wins, so a live teammate
#                always resolves. Reports the HIGH-WATER turn, the number unit sizing needs: compaction
#                resets occupancy, and a stopped/dead teammate trails stripped
#                `{input_tokens:0,output_tokens:0}` turns that read as 0%.
#   -p         → print the resolved transcript path instead of the gauge; marker polling reads that
#                transcript's LAST assistant text (a raw grep also hits the spawn prompt + every
#                `SendMessage` body carrying the marker)
[ "$1" = "-p" ] && { path_only=1; shift; }
root="$HOME/.claude/projects"
proj="$root/$(pwd -P | tr '/.' '-')"
if [ -n "$1" ]; then
  agent=true # every subagent turn carries isSidechain=true
  f=$({ find "$proj" -type f -name '*.meta.json' -exec jq -r --arg n "$1" 'select((.name//"")==$n)|input_filename' {} + 2>/dev/null |
    sed 's/\.meta\.json$/.jsonl/'; find "$proj" -type f -name "*$1*.jsonl" 2>/dev/null; } |
    sort -u | xargs -r ls -t 2>/dev/null | head -1)
else
  agent=false
  f=$(find "$root" -mindepth 2 -maxdepth 2 -type f -name "$CLAUDE_CODE_SESSION_ID.jsonl" -print -quit 2>/dev/null)
  # fallback (no session id): newest transcript in THIS project's dir only, scoped to this project alone
  [ -n "$f" ] || f=$(find "$proj" -maxdepth 1 -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -nr | cut -d ' ' -f 2- | head -1)
fi
[ -n "$path_only" ] && { [ -n "$f" ] && printf '%s\n' "$f"; exit; }
u=$(jq -n --argjson a "$agent" '[inputs|select(.type=="assistant" and ($a or .isSidechain!=true) and .message.model!="<synthetic>" and (.message.usage|type)=="object" and (.message.usage.cache_read_input_tokens|type)=="number")|.message.usage|.input_tokens+.cache_creation_input_tokens+.cache_read_input_tokens+.output_tokens]|select(length>0)|if $a then max else .[-1] end' "$f" 2>/dev/null)
w=240000
awk -v u="$u" -v w="$w" '
function h(n){ if(n>=1000000){s=sprintf("%.1fM",n/1000000);sub(/\.0M$/,"M",s);return s}
              return sprintf("%dK",int(n/1000+0.5)) }
BEGIN{ if(u==""){ print "? ?/" h(w); exit }
       print int(u*100/w+0.5) "% " h(u) "/" h(w) }'
