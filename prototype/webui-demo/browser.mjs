// The demo's own pinned Chromium for capture.sh, measure-height.mjs and density.mjs.
// Install once: `pnpm --dir prototype/webui-demo install` (postinstall downloads the browser
// into node_modules, so nothing outside this directory is read or written).
// PLAYWRIGHT_BROWSERS_PATH=0 = "the browsers inside node_modules"; it must be set before
// Playwright loads, hence the dynamic import.
process.env.PLAYWRIGHT_BROWSERS_PATH = "0";
const { chromium } = await import("playwright");

export const launch = () => chromium.launch({ headless: true });
