// Report the viewport height one capture needs, so capture-proof.sh measures instead
// of guessing. Both columns scroll inside the page, so a block past the fold is simply
// absent from the PNG and a frame silently loses the claim it is named for.
//
//   node measure-height.mjs <url> [right|card]
//
// Needs the chromiumfish workspace `webcap` runs on, the same dependency the capture
// script already declares.
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const WORKSPACE = join(homedir(), ".local/share/chromiumfish/node_modules");
const { ChromiumFish } = await import(
  `${pathToFileURL(join(WORKSPACE, "chromiumfish")).href}/dist/index.js`
);

const [url, which = "right"] = process.argv.slice(2);
if (!url) {
  process.stderr.write("usage: measure-height.mjs <url> [right|card]\n");
  process.exit(2);
}

const browser = await ChromiumFish({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
let height;
try {
  await page.goto(url, { waitUntil: "load", timeout: 60000 });
  // Wait for rendered content, not a sleep: app.js renders after document.fonts.ready
  // and webfonts change every line height, so a sleep can measure an empty pane and
  // undersize the frame, which is the failure that silently drops a claim.
  await page.waitForFunction((target) => (
    document.fonts.status === "loaded"
    && document.querySelector("#coverage")?.children.length > 0
    && (target !== "card"
      || document.querySelector(".overlay-body")?.children.length > 0)
  ), which, { timeout: 60000 });
  await page.waitForTimeout(500);
  height = await page.evaluate((target) => {
    if (target === "card") {
      const card = document.querySelector(".overlay-card");
      const body = document.querySelector(".overlay-body");
      if (!card || document.querySelector("#overlay").hidden) {
        throw new Error("no open overlay to measure");
      }
      // The card is position: fixed and its body scrolls inside it, so the card's own
      // scrollHeight reports the viewport. Swap the clipped body for its content.
      return card.offsetHeight - body.clientHeight + body.scrollHeight + 48;
    }
    const pane = document.querySelector("#side-hidden .pane-body");
    const box = pane.getBoundingClientRect();
    return box.top + pane.scrollHeight + (window.innerHeight - box.bottom);
  }, which);
} finally {
  await browser.close();
}
// Round up to the next ten: a frame may be taller than its column, never shorter.
process.stdout.write(String(Math.ceil(height / 10) * 10) + "\n");
