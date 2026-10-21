// Quality floor of one demo state (p80): reduced motion, 390 px reach, Tab focus ring, contrast.
//   [STATE=<query>] [TECH=<query>] node quality.mjs <base-url> <report.json>
// STATE (default ?reset=1) = the 390 px + Tab page; TECH (default ?tech=1) = the contrast page;
// the 390 px full-page frame lands beside the report. Passing = every .dots animation "none" under
// reduced motion, scroll_width <= 390 with 0 off-screen controls, every reached control ringed,
// 0 text pairs below 4.5:1.
import { writeFileSync } from "node:fs";
import { launch } from "./browser.mjs";
const [base, out] = process.argv.slice(2);
const browser = await launch();
const report = {};
const ready = (page) => page.waitForFunction(() => document.fonts.status === "loaded" && document.querySelector("#coverage")?.children.length > 0, null, { timeout: 60000 });
try {
  // 1. reduced motion: computed animation-name of the typing indicator dots
  {
    const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto(`${base}/`, { waitUntil: "load" }); await ready(page);
    report.reduced_motion = await page.evaluate(() => {
      const sheetRules = [...document.styleSheets].flatMap((s) => { try { return [...s.cssRules]; } catch { return []; } });
      const animated = sheetRules.filter((r) => r.style && r.style.animationName && r.style.animationName !== "none").map((r) => r.selectorText);
      return animated.map((selector) => {
        const host = document.createElement("div"); host.className = "probe-host"; document.body.append(host);
        // build an element that matches the selector's last compound
        const el = document.createElement("span");
        const classes = (selector.split(/[\s>+~]+/).pop().match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
        el.classList.add(...classes);
        // wrap with ancestors named in the selector
        let node = el;
        for (const part of selector.split(/[\s>+~]+/).slice(0, -1).reverse()) {
          const wrap = document.createElement("div");
          (part.match(/\.[\w-]+/g) || []).forEach((c) => wrap.classList.add(c.slice(1)));
          wrap.append(node); node = wrap;
        }
        host.append(node);
        const name = getComputedStyle(el).animationName;
        host.remove();
        return { selector, animation_name: name };
      });
    });
    await ctx.close();
  }
  // 2. 390 x 844: horizontal overflow + control reachability
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.goto(`${base}/${process.env.STATE ?? "?reset=1"}`, { waitUntil: "load" }); await ready(page);
    await page.waitForTimeout(800);
    report.mobile = await page.evaluate(() => {
      const controls = [...document.querySelectorAll("button, a[href], input, select, textarea, summary, [tabindex]")].filter((e) => e.getClientRects().length);
      const off = controls.filter((e) => { const r = e.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1; })
        .map((e) => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${[...e.classList].join(".")} [${(e.textContent || "").trim().slice(0, 30)}] ${Math.round(e.getBoundingClientRect().left)}..${Math.round(e.getBoundingClientRect().right)}`);
      const wide = [...document.querySelectorAll("body *")].filter((e) => e.getClientRects().length && e.getBoundingClientRect().right > innerWidth + 1)
        .slice(0, 12).map((e) => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${[...e.classList].join(".")} right=${Math.round(e.getBoundingClientRect().right)}`);
      return { scroll_width: document.documentElement.scrollWidth, inner_width: innerWidth, controls: controls.length, off_screen: off, wider_than_viewport: wide };
    });
    await page.screenshot({ path: out.replace(/\.json$/, "-390.png"), fullPage: true });
    await ctx.close();
  }
  // 3. Tab traversal at 1600: every focusable control gets focus + a visible ring
  {
    const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
    const page = await ctx.newPage();
    await page.goto(`${base}/${process.env.STATE ?? "?reset=1"}`, { waitUntil: "load" }); await ready(page);
    const total = await page.evaluate(() => [...document.querySelectorAll("button, a[href], input, select, textarea, summary, [tabindex]:not([tabindex='-1'])")].filter((e) => e.getClientRects().length && !e.disabled).length);
    const seen = new Map();
    for (let i = 0; i < total + 5; i++) {
      await page.keyboard.press("Tab");
      const info = await page.evaluate(() => {
        const e = document.activeElement; if (!e || e === document.body) return null;
        const cs = getComputedStyle(e);
        const ring = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || (cs.boxShadow && cs.boxShadow !== "none");
        return { key: `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${[...e.classList].join(".")}|${(e.textContent || e.getAttribute("aria-label") || "").trim().slice(0, 40)}`, ring };
      });
      if (info) seen.set(info.key, info.ring);
    }
    report.focus = { focusable_visible: total, reached: seen.size, without_ring: [...seen].filter(([, r]) => !r).map(([k]) => k) };
    await ctx.close();
  }
  // 4. contrast: every text node's color vs its effective background
  {
    const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
    const page = await ctx.newPage();
    await page.goto(`${base}/${process.env.TECH ?? "?tech=1"}`, { waitUntil: "load" }); await ready(page);
    await page.waitForTimeout(800);
    report.contrast = await page.evaluate(() => {
      const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
      const lum = ({ r, g, b }) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
      const blend = (top, bottom) => ({ r: top.r * top.a + bottom.r * (1 - top.a), g: top.g * top.a + bottom.g * (1 - top.a), b: top.b * top.a + bottom.b * (1 - top.a), a: 1 });
      const background = (el) => { const layers = []; for (let a = el; a; a = a.parentElement) { const c = parse(getComputedStyle(a).backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; } } let bg = { r: 255, g: 255, b: 255, a: 1 }; for (const l of layers.reverse()) bg = blend(l, bg); return bg; };
      const fails = new Map();
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let checked = 0;
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        if (!n.textContent.trim()) continue;
        const el = n.parentElement; if (!el || !el.getClientRects().length) continue;
        const cs = getComputedStyle(el); if (cs.visibility === "hidden" || parseFloat(cs.opacity) === 0) continue;
        let fg = parse(cs.color); const bg = background(el); fg = blend(fg, bg);
        const L1 = lum(fg), L2 = lum(bg); const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
        checked++;
        const large = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.66 && Number(cs.fontWeight) >= 700);
        if (ratio < 4.5) { const key = `${cs.color} on ${JSON.stringify(bg)} :: ${el.tagName.toLowerCase()}.${[...el.classList].join(".")}`; if (!fails.has(key)) fails.set(key, { ratio: Math.round(ratio * 100) / 100, large, sample: n.textContent.trim().slice(0, 40) }); }
      }
      return { text_nodes: checked, below_4_5: [...fails].map(([k, v]) => ({ pair: k, ...v })) };
    });
    await ctx.close();
  }
} finally { await browser.close(); }
writeFileSync(out, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ reduced_motion: report.reduced_motion, mobile: { scroll_width: report.mobile.scroll_width, off: report.mobile.off_screen.length, wide: report.mobile.wider_than_viewport.length }, focus: { total: report.focus.focusable_visible, reached: report.focus.reached, without_ring: report.focus.without_ring.length }, contrast_fail_pairs: report.contrast.below_4_5.length, text_nodes: report.contrast.text_nodes }));
