#!/usr/bin/env bash
# p34 two-wheel smoke: build `cement-runtime` + `cement-command-source` from the committed tree
# (each sdist, then its wheel from that sdist), install both offline into a fresh venv outside
# the repository, and run the provider end to end.
# Usage: .agent/decisions/p34-two-wheel-smoke.sh [TREE-ISH]  (default HEAD; an uncommitted state =
# `git add` + `git write-tree`). rc 0 = every check passed; 1 = a check failed.
set -euo pipefail

root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
fail=0
check() {  # check <label> <actual> <expected>
    if [[ "$2" == "$3" ]]; then
        echo "PASS $1"
    else
        echo "FAIL $1: got [$2] want [$3]"
        fail=1
    fi
}

git -C "$root" archive "${1:-HEAD}" | tar -x -C "$work" --one-top-level=tree
uv build -q --out-dir "$work/dist" "$work/tree"
uv build -q --out-dir "$work/dist" --build-constraints "$work/tree/examples/command_source/build-constraints.txt" \
    --require-hashes "$work/tree/examples/command_source"
uv venv -q --python 3.12 "$work/venv"
python="$work/venv/bin/python"
bin="$work/venv/bin"

uv pip install -q --python "$python" --no-index "$work"/dist/cement_runtime-*.whl
check "core alone: no runner command" "$(test -e "$bin/cement-command-source" && echo present || echo absent)" absent
uv pip install -q --python "$python" --no-index --find-links "$work/dist" "$work"/dist/cement_command_source-*.whl
check "installed distributions" "$(uv pip list -q --python "$python" --format freeze | sort | tr '\n' ' ')" \
    "cement-command-source==0.1.0 cement-runtime==0.2.0 "

wheel=$(echo "$work"/dist/cement_command_source-*.whl)
members=$("$python" -c 'import sys, zipfile
names = zipfile.ZipFile(sys.argv[1]).namelist()
print(" ".join(sorted(n for n in names if ".dist-info/" not in n)))' "$wheel")
check "wheel modules" "$members" "cement_command_source/_command_supervisor.py cement_command_source/command_source.py"
license=$("$python" -c 'import sys, zipfile
archive = zipfile.ZipFile(sys.argv[1])
(name,) = [n for n in archive.namelist() if n.endswith(".dist-info/licenses/LICENSE")]
sys.stdout.buffer.write(archive.read(name))' "$wheel" | sha256sum | cut -d' ' -f1)
check "wheel license = repository LICENSE" "$license" "$(sha256sum "$root/LICENSE" | cut -d' ' -f1)"

cd "$work"
loaded=$("$python" -I -c 'import contextlib, io, sys
import cement_runtime, cement_runtime.cli
with contextlib.redirect_stdout(io.StringIO()), contextlib.suppress(SystemExit):
    cement_runtime.cli.main(["--help"])
print(sorted(m for m in sys.modules if "command_source" in m))')
check "core loads no provider module" "$loaded" "[]"
check "core imports from the venv" "$("$python" -I -c 'import cement_runtime; print(cement_runtime.__file__.startswith(__import__("sys").prefix))')" True

export CEMENT_DB="$work/ledger.db" CEMENT_PARTITION=smoke
"$bin/cement" operation register echo >/dev/null
adapter=("$python" "$work/tree/examples/command_source/example_adapter.py")
set +e
out=$("$bin/cement-command-source" echo --input '{"domain": "value"}' -- "${adapter[@]}")
rc=$?
set -e
check "runner rc" "$rc" 0
proposal=$("$python" -c 'import json, sys; print(json.loads(sys.argv[1])["proposal_id"])' "$out")
shown=$("$bin/cement" proposal show "$proposal" | "$python" -c 'import json, sys
view = json.load(sys.stdin)
print(json.dumps([view["proposed_output"], view["provenance"]["adapter"]], sort_keys=True))')
check "proposal retained" "$shown" '[{"kind": "echo", "value": {"domain": "value"}}, "command"]'

set +e
err=$("$bin/cement-command-source" echo --input '{}' -- "$python" -c 'raise SystemExit(1)' 2>&1 >/dev/null)
rc=$?
set -e
check "adapter failure" "$rc $(echo "$err" | tr -d ' \n')" '2 {"error":"invalid","message":"candidatesourcefailed"}'
set +e
"$bin/cement-command-source" absent --input '{}' -- "${adapter[@]}" >/dev/null 2>&1
rc=$?
set -e
check "unregistered operation" "$rc" 3
count=$("$bin/cement" events | "$python" -c 'import json, sys
print(sum(e["kind"] == "proposal.created" for e in json.load(sys.stdin)))')
check "one proposal written" "$count" 1

if [[ $fail -ne 0 ]]; then
    echo "p34 smoke: FAIL"
    exit 1
fi
echo "p34 smoke: PASS"
