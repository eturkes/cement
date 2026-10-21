// Density grade for one demo state: the words a visitor faces without clicking.
//   node density.mjs <url> [settle-ms]  → JSON {viewport_words, rendered_words, visible_buttons}
// viewport = text nodes whose box meets the 1600x1000 first screen, clipped by every
// scrolling ancestor; rendered = every laid-out text node, inner-scroll overflow included.
// Closed <details> bodies count as hidden: Chrome lays them out (content-visibility), so
// their rects alone would report them visible.
// Needs the demo's own browser: `pnpm --dir prototype/webui-demo install` (README `Visual check`).
import { launch } from "./browser.mjs";
const [url, settle = "2500"] = process.argv.slice(2);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
try {
  await page.goto(url, { waitUntil: "load", timeout: 60000 });
  await page.waitForFunction(() => document.fonts.status === "loaded", null, { timeout: 60000 });
  await page.waitForTimeout(Number(settle));
  const out = await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let viewport = 0, rendered = 0;
    const words = (s) => (s.match(/\S+/g) || []).length;
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const text = n.textContent;
      if (!text.trim()) continue;
      const el = n.parentElement;
      if (!el || !el.getClientRects().length) continue; // display:none
      const shut = el.closest("details:not([open])");
      if (shut && !el.closest("summary")?.parentElement?.isSameNode(shut)) continue;
      if (getComputedStyle(el).visibility === "hidden") continue;
      const r = document.createRange();
      r.selectNodeContents(n);
      const rects = [...r.getClientRects()];
      if (!rects.length) continue;
      const w = words(text);
      rendered += w;
      // clip by every scrolling ancestor + window
      let visible = rects.some((b) => b.bottom > 0 && b.top < innerHeight && b.right > 0 && b.left < innerWidth);
      for (let a = el; visible && a; a = a.parentElement) {
        const cs = getComputedStyle(a);
        if (/(auto|scroll|hidden)/.test(cs.overflowY + cs.overflowX)) {
          const c = a.getBoundingClientRect();
          visible = rects.some((b) => b.bottom > c.top && b.top < c.bottom);
        }
      }
      if (visible) viewport += w;
    }
    const buttons = [...document.querySelectorAll("button, a.button")]
      .filter((b) => b.getClientRects().length).length;
    return { viewport_words: viewport, rendered_words: rendered, visible_buttons: buttons };
  });
  process.stdout.write(JSON.stringify(out) + "\n");
} finally {
  await browser.close();
}
