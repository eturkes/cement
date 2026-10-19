---
paths:
  - "prototype/**"
---

# Prototype `prototype/webui-demo`

- PROTOTYPE law for good (`ops.md` Template rulings (1)), outside every gate + census ⇒ a prototype-only revision owes no gate run; its check = `capture.sh` against a running server, plus `.agent/spec-lint` when `.agent/spec.md` changes. Rulings → `.agent/spec.md` `Decisions`; its README = human-facing.
- Server = `uv run python prototype/webui-demo/app.py` (port 8765). Static files serve fresh from disk; a `demo.py` / `app.py` edit needs a restart: kill the listener PIDs read from `pgrep -af 'webui-demo/ap[p].py'`, relaunch, poll `until curl -sf`.
- `capture.sh` drives the story through the API (send → learn → per-function switch), capturing 10 PNGs + `transcript.txt` + `timings.txt` (subprocess + resolve costs, also printed) from ONE ledger into gitignored `.scratch/webui-demo-capture/` (`OUT` overrides) — QA input read frame by frame, never tracked. Standing check: `sha256sum .scratch/webui-demo-capture/*.png | awk '{print $1}' | sort | uniq -d` = EMPTY; two byte-identical frames = a frame lost its claim.
- Every `shot` height is MEASURED: both columns scroll internally, so a block below the fold is absent from the file. `measure-height.mjs <url> [right|card]` reads the pane's own `scrollHeight` at a 1000 px viewport once content is RENDERED (`document.fonts.status` + a populated `#coverage`), never after a sleep, called immediately before each capture; `card` swaps the clipped `position: fixed` overlay body for its content. Chrome screenshots glitch above ~8192 px ⇒ never probe a height at a taller viewport. Webfonts land after first paint ⇒ `app.js` awaits `document.fonts.ready` before its first render.
- `density.mjs <url>` = words on the first 1600×1000 screen / rendered / visible buttons, graded at `?reset=1` and right after `capture.sh` (a `?reset=1` run wipes the story state, so measure story end first).
- The stand-in AI is deterministic (fixed scripts per case, seeded latencies) ⇒ the tour's Back replays to an identical state through `send(fast)`. driver.js = vendored `static/vendor/driver.js-1.10.2/` (MIT, no build step); its `highlight()` mode shows only the buttons a step lists itself.
- States `capture.sh` cannot reach (tour beats, Back, free clicks, 390 px) → a scratch ChromiumFish driver under `.scratch/`; inspect every frame.
