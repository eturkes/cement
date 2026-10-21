// One PNG of one demo state at a 1600 px wide viewport.
//   node shot.mjs <url> <png> <height> [--full-page]
// Waits for load + 2.5 s, the settle time every frame has used.
import { launch } from "./browser.mjs";

const [url, png, height, mode] = process.argv.slice(2);
if (!url || !png || !height) {
  process.stderr.write("usage: shot.mjs <url> <png> <height> [--full-page]\n");
  process.exit(2);
}
const browser = await launch();
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: Number(height) } });
  await page.goto(url, { waitUntil: "load", timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: png, fullPage: mode === "--full-page", timeout: 60000 });
} finally {
  await browser.close();
}
