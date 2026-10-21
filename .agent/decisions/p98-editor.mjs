// p98: Open WebUI 0.12.3 editor load + save time for one tool/function paste-in (run against
// `examples/open_webui/local.py serve`; each run appends a `# p98 run N` comment line and saves).
//   node .agent/decisions/p98-editor.mjs <base> <tools|functions> <id> <runs> <shot.png>
const { launch } = await import(new URL("../../prototype/webui-demo/browser.mjs", import.meta.url).href);
const [base, kind, id, runs = "5", shot] = process.argv.slice(2);
const url = kind === "tools" ? `${base}/workspace/tools/edit?id=${id}` : `${base}/admin/functions/edit?id=${id}`;
const browser = await launch();
const results = [];
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  // warm-up: first app load compiles + caches the SPA bundle
  await page.goto(`${base}/`, { waitUntil: "load", timeout: 120000 }); await page.waitForTimeout(5000);
  for (let i = 0; i < Number(runs); i++) {
    const t0 = Date.now();
    await page.goto(url, { waitUntil: "load", timeout: 120000 });
    await page.waitForFunction(() => {
      const lines = document.querySelectorAll(".cm-content .cm-line");
      return lines.length > 10;
    }, null, { timeout: 120000 });
    const tLoad = Date.now() - t0;
    const docChars = await page.evaluate(() => {
      const view = document.querySelector(".cm-content")?.cmView?.view ?? document.querySelector(".cm-editor")?.cmView?.view;
      return view ? view.state.doc.length : null;
    });
    if (i === 0 && shot) await page.screenshot({ path: shot });
    await page.locator(".cm-content").click();
    await page.keyboard.press("Control+End");
    await page.keyboard.type(`\n# p98 run ${i + 1}`);
    const save = page.getByRole("button", { name: /^Save$/ }).last();
    await save.waitFor({ state: "visible" });
    await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent.trim() === "Save" && !b.disabled), null, { timeout: 30000 });
    const t1 = Date.now();
    const [response] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && r.url().includes(`/id/${id}/update`), { timeout: 120000 }),
      save.click(),
    ]);
    const tSave = Date.now() - t1;
    results.push({ run: i + 1, load_ms: tLoad, save_ms: tSave, status: response.status(), doc_chars: docChars });
  }
} finally { await browser.close(); }
console.log(JSON.stringify({ url, results }));
