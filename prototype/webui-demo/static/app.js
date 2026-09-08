"use strict";

/* Cement web UI demo. One render pass per state snapshot; the server holds all state. */

let STATE = null;
let BUSY = false;
let POLL = null;

const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const short = (value, size = 12) =>
  value ? esc(String(value).slice(0, size)) + "\u2026" : "\u2014";

function jsonHtml(value) {
  if (value === null || value === undefined) return "";
  const text = JSON.stringify(value, null, 2);
  return esc(text)
    .replace(/"([^"\\]*(?:\\.[^"\\]*)*)"(\s*:)?/g, (match, body, colon) =>
      colon
        ? `<span class="k">"${body}"</span>${colon}`
        : `<span class="s">"${body}"</span>`)
    .replace(/\b(true|false|null|-?\d+(?:\.\d+)?)\b/g, '<span class="p">$1</span>');
}

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 6000);
}

/* --- transport --- */

async function call(path, body) {
  BUSY = true;
  render();
  startPolling();
  try {
    const options = body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };
    const response = await fetch(path, options);
    const payload = await response.json();
    if (!response.ok) {
      if (payload.state) STATE = payload.state;
      toast(payload.error || "request failed");
      return null;
    }
    STATE = payload;
    return payload;
  } finally {
    stopPolling();
    BUSY = false;
    render();
  }
}

function startPolling() {
  if (POLL) return;
  POLL = setInterval(async () => {
    const response = await fetch("/api/state");
    if (response.ok) {
      STATE = await response.json();
      render();
    }
  }, 350);
}

function stopPolling() {
  if (POLL) clearInterval(POLL);
  POLL = null;
}

const send = (id) => call("/api/send", { document_id: id });
const review = (proposalId, decision) =>
  call("/api/review", { proposal_id: proposalId, decision });
const revoke = (exampleId) => call("/api/revoke", { example_id: exampleId });
const lifecycle = (action) => call("/api/" + action, {});
const route = (enabled) => call("/api/route", { enabled });
const offline = (id) => call("/api/offline", { document_id: id });

/* --- render --- */

function render() {
  if (!STATE) return;
  $("chip-partition").textContent = STATE.partition;
  $("chip-operation").textContent = STATE.operation;
  $("policy-note").textContent =
    `policy: ${STATE.policy.min_confirmations} confirmations, ` +
    `${STATE.policy.min_reviewers} reviewer`;
  renderChat();
  renderTray();
  renderCategories();
  renderReview();
  renderLifecycle();
  renderFunction();
  renderRouting();
  renderMetrics();
  renderLog();
}

function renderChat() {
  const chat = $("chat");
  const messages = STATE.chat.map(chatMessage).join("");
  const thinking = STATE.thinking
    ? `<div class="msg assistant"><div class="avatar">AI</div><div class="bubble">
         <div class="thinking"><span class="dots"><span></span><span></span><span></span></span>
         ${esc(STATE.thinking.provider)} is reading ${esc(STATE.thinking.document_id)}\u2026</div>
       </div></div>`
    : "";
  const empty = STATE.chat.length
    ? ""
    : `<div class="empty">The intake desk sends scanned documents here. Choose one below.</div>`;
  chat.innerHTML = empty + messages + thinking;
  const pane = chat.closest(".pane-body");
  if (pane && !document.body.classList.contains("expanded")) {
    pane.scrollTop = pane.scrollHeight;
  }
}

function chatMessage(message) {
  if (message.kind === "document") {
    return `<div class="msg clerk"><div class="avatar">IC</div><div class="bubble">
      <div class="bubble-head"><span class="who">Intake clerk</span>
        <span class="badge">layout ${esc(message.layout)}</span></div>
      <div class="doc-title">${esc(message.title)}</div>
      <div class="doc-meta">${esc(message.document_id)} \u00b7 ${esc(message.patient)}</div>
      <div class="ask">${esc(message.ask)}</div>
      <details class="ocr"><summary>scanned text</summary><pre>${esc(message.text)}</pre></details>
    </div></div>`;
  }
  if (message.kind === "held") {
    return assistant("held", `
      <div class="bubble-head"><span class="badge llm">provider \u00b7 held for review</span>
        <span>${esc(message.provider)}</span>
        <span>${esc(message.provider_ms)} ms simulated</span></div>
      <div class="held-body"><div class="lockbar"></div><div>
        <div>A supervisor must confirm this answer. The assistant releases no candidate.</div>
        <div class="answer-meta"><span>proposal ${esc(message.proposal_id)}</span>
          <span>review surface \u2192 control plane</span></div>
      </div></div>`);
  }
  if (message.kind === "released") {
    const body = message.error
      ? `<div class="preview-error">${esc(message.error)}</div>`
      : `<pre class="json">${jsonHtml(message.output)}</pre>`;
    return assistant("", `
      <div class="bubble-head"><span class="badge pass">supervised \u00b7 ${esc(message.status)}</span>
        <span>${esc(message.reviewer)}</span></div>
      ${body}
      <div class="answer-meta"><span>example ${esc(message.example_id)}</span>
        <span>the plan is now confirmed evidence for this layout</span></div>`);
  }
  if (message.kind === "cement") {
    const body = message.error
      ? `<div class="preview-error">${esc(message.error)}</div>`
      : `<pre class="json">${jsonHtml(message.output)}</pre>`;
    return assistant("cemented", `
      <div class="bubble-head"><span class="badge set">cement \u00b7 exact match</span>
        <span>no provider call</span></div>
      ${body}
      <div class="answer-meta">
        <span>resolve ${esc(message.resolve_ms)} ms</span>
        <span>entries ${esc(message.entries)}</span>
        <span>artifact ${short(message.artifact_hash)}</span>
        <span>function ${short(message.function_hash)}</span>
        <span>${message.checks.length} checks passed</span></div>`);
  }
  if (message.kind === "miss") {
    return assistant("miss", `
      <div class="bubble-head"><span class="badge warn">no exact match</span>
        <span>resolve ${esc(message.resolve_ms)} ms</span></div>
      <div>The promoted set holds no entry for layout ${esc(message.layout)}. The request
        returns to the supervised provider path. Cement widens nothing on its own.</div>`);
  }
  if (message.kind === "rejected") {
    return assistant("", `
      <div class="bubble-head"><span class="badge fail">rejected</span></div>
      <div>The supervisor rejected the candidate. The assistant released no answer, and
        the rejection stays as audit evidence only.</div>`);
  }
  return "";
}

const assistant = (extra, inner) =>
  `<div class="msg assistant ${extra}"><div class="avatar">AI</div>
   <div class="bubble">${inner}</div></div>`;

function renderTray() {
  $("tray").innerHTML = STATE.documents
    .map(
      (document_) => `<button class="doc-card" data-send="${esc(document_.id)}"
        ${BUSY ? "disabled" : ""}>
        <span class="id">${esc(document_.id)}</span>
        <span class="who2">${esc(document_.patient)}</span>
        <span class="kind">${esc(document_.document_type.replace(/_/g, " "))}</span>
      </button>`)
    .join("");
}

function categoryStatus(category) {
  if (category.promoted) return ["promoted", "set"];
  if (category.confirmations >= category.required) return ["ready to compile", "pass"];
  return ["gathering evidence", "llm"];
}

function renderCategories() {
  if (!STATE.categories.length) {
    $("categories").innerHTML =
      `<div class="empty">No category yet. A category appears when a layout signature
       arrives for the first time.</div>`;
    return;
  }
  $("categories").innerHTML = STATE.categories
    .map((category) => {
      const [label, tone] = categoryStatus(category);
      const percent = Math.min(100, (category.confirmations / category.required) * 100);
      const chips = category.examples
        .map(
          (example) => `<span class="example-chip">${esc(example.origin)}
            ${short(example.example_id, 10)}
            <span class="link" data-revoke="${esc(example.example_id)}"
              title="revoke this example">\u00d7</span></span>`)
        .join(" ");
      return `<div class="category ${category.promoted ? "promoted" : ""}">
        <div class="category-head">
          <span class="layout-tag">layout ${esc(category.layout)}</span>
          <span class="badge ${tone}">${label}</span>
        </div>
        <div class="category-type">${esc(category.document_type)} \u00b7
          input ${short(category.input_hash)}</div>
        <div class="meter ${percent >= 100 ? "full" : ""}"><i style="width:${percent}%"></i></div>
        <div class="category-facts">
          <span>${category.confirmations}/${category.required} confirmations</span>
          <span>${category.reviewers.length} reviewer${category.reviewers.length === 1 ? "" : "s"}</span>
          <span>${category.distinct_candidates} distinct provider plan${category.distinct_candidates === 1 ? "" : "s"}</span>
        </div>
        <div class="category-facts">${chips}</div>
      </div>`;
    })
    .join("");
}

function renderReview() {
  if (!STATE.pending.length) {
    $("review").innerHTML =
      `<div class="empty">No pending proposal. A held answer appears here for the
       supervisor.</div>`;
    return;
  }
  $("review").innerHTML = STATE.pending
    .map((proposal) => {
      const preview = proposal.preview_error
        ? `<div class="preview-error">This plan does not apply to the document:
             ${esc(proposal.preview_error)}</div>`
        : `<pre class="json">${jsonHtml(proposal.preview)}</pre>`;
      const diff = proposal.diff.length
        ? `<div class="diff">${proposal.diff
            .map(
              (row) => `<div class="diff-row ${esc(row.kind)}">
                <span class="tag">${esc(row.kind)}</span>
                <span>${esc(row.field)}</span>
                <span class="dim">${esc(row.detail)}</span></div>`)
            .join("")}</div>`
        : `<div class="tiny dim" style="margin-top:8px">The candidate matches the
           supervisor's plan for this layout.</div>`;
      return `<div class="proposal">
        <div class="proposal-head">
          <span class="badge llm">pending</span>
          <span class="hash">${esc(proposal.proposal_id)}</span>
          <span class="tiny dim">${esc(proposal.document_id)} \u00b7 layout ${esc(proposal.layout)}</span>
        </div>
        <div class="note">The provider ${esc(proposal.note)}.</div>
        <div class="label-row" style="margin-top:10px">
          <span class="label">What this plan extracts</span></div>
        ${preview}
        <div class="label-row" style="margin-top:10px">
          <span class="label">Difference from the supervisor's correction</span></div>
        ${diff}
        <details class="ocr" style="margin-top:10px"><summary>candidate plan</summary>
          <pre class="json">${jsonHtml(proposal.plan)}</pre></details>
        <div class="actions">
          <button class="button small accept" data-review="accept"
            data-proposal="${esc(proposal.proposal_id)}">accept</button>
          <button class="button small correct" data-review="correct"
            data-proposal="${esc(proposal.proposal_id)}">correct</button>
          <button class="button small reject" data-review="reject"
            data-proposal="${esc(proposal.proposal_id)}">reject</button>
        </div>
      </div>`;
    })
    .join("");
}

function renderLifecycle() {
  const rows = [];
  for (const draft of STATE.drafts) {
    rows.push(row(
      `layout ${draft.layout} \u00b7 ${draft.status}`,
      `${draft.tests ? draft.tests + " tests \u00b7 " : ""}${short(draft.artifact_id, 14)}`));
  }
  for (const blocked of STATE.blocked || []) {
    rows.push(row(
      `layout ${blocked.layout} \u00b7 blocked`,
      (blocked.reasons || []).join("; ")));
  }
  $("lifecycle").innerHTML = rows.length
    ? rows.join("")
    : `<div class="empty">Compile groups confirmed examples by exact scope. It creates
       drafts, and it never promotes them.</div>`;
}

const row = (key, value) =>
  `<div class="row"><span class="k">${esc(key)}</span><span class="v">${esc(value)}</span></div>`;

function renderFunction() {
  const target = $("function");
  if (!STATE.function) {
    target.innerHTML =
      `<div class="empty">No promoted set yet. The operator promotes a verified draft,
       and the whole promoted set becomes one function.</div>`;
    return;
  }
  const fn = STATE.function;
  const checks = fn.checks
    .map(
      (check) => `<div class="check ${check.passed ? "" : "failed"}">
        <span class="dot"></span><span>${esc(check.key)}</span>
        <span class="detail">${esc(check.detail)}</span></div>`)
    .join("");
  const offlineResult = STATE.offline
    ? `<div class="label-row" style="margin-top:12px">
         <span class="label">Answer from the bundle alone</span></div>
       ${STATE.offline.matched
          ? `<pre class="json">${jsonHtml(STATE.offline.output)}</pre>
             <div class="answer-meta"><span>${esc(STATE.offline.document_id)} matched</span>
               <span>artifact ${short(STATE.offline.artifact_hash)}</span>
               <span>no ledger read</span></div>`
          : `<div class="tiny dim">${esc(STATE.offline.document_id)}: the bundle holds no
             entry for layout ${esc(STATE.offline.layout)}, so it reports a miss.</div>`}`
    : "";
  target.innerHTML = `
    ${row("entries", fn.entries)}
    ${row("verdict", fn.passed ? "verified" : "failed")}
    ${row("receipt", fn.receipt_id)}
    ${row("bundle", fn.bundle_bytes + " bytes")}
    <div class="row"><span class="k">function_hash</span></div>
    <div class="hash">${esc(fn.function_hash)}</div>
    <div class="checks">${checks}</div>
    <div class="actions">
      <button class="button small" data-offline="A03">answer A03 from the bundle</button>
      <a class="button small" href="/api/bundle.json" download="function.json">download bundle</a>
    </div>
    ${offlineResult}`;
}

function renderRouting() {
  const on = STATE.routed;
  $("routing").innerHTML = `
    <div class="switch-row">
      <button class="switch ${on ? "on" : ""}" id="switch" aria-pressed="${on}">
        <span class="knob"></span></button>
      <div class="switch-labels">
        <span class="switch-state ${on ? "on" : "off"}">
          ${on ? "requests resolve from the function" : "every request goes to the provider"}</span>
        <span class="tiny dim">${on
          ? "An input outside the promoted set returns to the supervised path."
          : "Turn this on when the operator decides the category is ready."}</span>
      </div>
    </div>`;
  $("switch").addEventListener("click", () => route(!on));
}

function renderMetrics() {
  const stats = STATE.stats;
  const distinct = STATE.categories.reduce(
    (best, category) => Math.max(best, category.distinct_candidates), 0);
  $("metrics").innerHTML = `
    <div class="compare">
      <div class="compare-cell llm">
        <h4>Provider path</h4>
        <div class="stat">${stats.provider_calls}</div>
        <div class="stat-note">answers, each held for a supervisor</div>
        <div class="stat">${stats.provider_ms_mean === null ? "\u2014" : (stats.provider_ms_mean / 1000).toFixed(1) + " s"}</div>
        <div class="stat-note">mean wait, simulated</div>
        <div class="stat">${distinct}</div>
        <div class="stat-note">distinct plans for one layout</div>
      </div>
      <div class="compare-cell set">
        <h4>Cement path</h4>
        <div class="stat">${stats.cement_answers}</div>
        <div class="stat-note">answers, no supervision needed</div>
        <div class="stat">${stats.resolve_ms_median === null ? "\u2014" : stats.resolve_ms_median + " ms"}</div>
        <div class="stat-note">median resolve, measured</div>
        <div class="stat">1</div>
        <div class="stat-note">output per entry, byte-identical</div>
      </div>
    </div>
    <div class="tiny dim" style="margin-top:9px">
      ${stats.provider_calls_avoided} provider call${stats.provider_calls_avoided === 1 ? "" : "s"}
      avoided \u00b7 ${stats.reviews} review${stats.reviews === 1 ? "" : "s"} recorded.
      Every resolve runs the full six-check verification and caches nothing.
    </div>`;
}

function renderLog() {
  $("log").innerHTML = STATE.log
    .map(
      (entry) => `<div class="log-line">
        <span class="at">${entry.at.toFixed(2)}s</span>
        <span class="kind">${esc(entry.kind)}</span>
        <span class="text">${esc(entry.text)}
          ${entry.detail ? `<span class="detail">\u2014 ${esc(entry.detail)}</span>` : ""}</span>
      </div>`)
    .join("");
  const log = $("log");
  if (!document.body.classList.contains("expanded")) log.scrollTop = log.scrollHeight;
}

/* --- the story --- */

const SCENES = [
  { name: "desk", steps: [] },
  { name: "held", steps: [() => send("A01")] },
  {
    name: "evidence",
    steps: [
      () => review(STATE.pending[0].proposal_id, "correct"),
      () => send("A02"),
      () => review(STATE.pending[0].proposal_id, "accept"),
    ],
  },
  {
    name: "cemented",
    steps: [
      () => lifecycle("compile"),
      () => lifecycle("verify"),
      () => lifecycle("promote"),
    ],
  },
  { name: "routed", steps: [() => route(true), () => send("A03")] },
  {
    name: "boundary",
    steps: [
      () => send("C01"),
      () => review(STATE.pending[0].proposal_id, "accept"),
      () => lifecycle("compile"),
    ],
  },
  { name: "bundle", steps: [() => offline("A03")] },
];

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function runStory(upTo) {
  $("play").disabled = true;
  for (let index = 0; index <= upTo && index < SCENES.length; index += 1) {
    const scene = SCENES[index];
    document.body.dataset.scene = scene.name;
    for (const step of scene.steps) {
      await step();
      await pause(420);
    }
    document.body.dataset.sceneDone = String(index);
  }
  $("play").disabled = false;
}

/* --- wiring --- */

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-send],[data-review],[data-action],[data-offline],[data-revoke]");
  if (!target || BUSY) return;
  if (target.dataset.send) send(target.dataset.send);
  else if (target.dataset.review) review(target.dataset.proposal, target.dataset.review);
  else if (target.dataset.action) lifecycle(target.dataset.action);
  else if (target.dataset.offline) offline(target.dataset.offline);
  else if (target.dataset.revoke) revoke(target.dataset.revoke);
});

$("play").addEventListener("click", () => runStory(SCENES.length - 1));
$("reset").addEventListener("click", async () => {
  await call("/api/reset", {});
  delete document.body.dataset.sceneDone;
  delete document.body.dataset.scene;
});

(async function start() {
  const parameters = new URLSearchParams(location.search);
  if (parameters.has("expand")) document.body.classList.add("expanded");
  if (parameters.has("reset")) await call("/api/reset", {});
  STATE = await (await fetch("/api/state")).json();
  render();
  if (parameters.has("scene")) await runStory(Number(parameters.get("scene")));
})();
