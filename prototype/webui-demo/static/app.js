"use strict";

/* Cement web UI demo. One render pass per state snapshot; the server holds all state. */

let STATE = null;
let BUSY = false;
let POLL = null;
let SOURCE_OPEN = false;
let OPEN_ALL = false;
/* Re-rendering the source collapses every open <details>, so redraw only on change. */
let SOURCE_KEY = "";

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

/* Pretty JSON whose continuation lines carry a code-block indent. */
function jsonBlock(value, pad) {
  return jsonHtml(value)
    .split("\n")
    .map((line, index) => (index ? pad + line : line))
    .join("\n");
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
    `promotes at ${STATE.policy.min_confirmations} confirmations, ` +
    `${STATE.policy.min_reviewers} reviewer`;
  renderChat();
  renderTray();
  renderTerminal();
  renderCategories();
  renderReview();
  renderFunction();
  renderSource();
  renderRouting();
  renderMetrics();
  renderLog();
  /* Capture aid: a screenshot cannot click a disclosure open. */
  if (OPEN_ALL) {
    for (const node of document.querySelectorAll("details")) node.open = true;
  }
}

/* --- chat: a plain chat, and nothing else ---
   Every badge, id, digest and timing this pane once printed is machinery the
   deployment never shows. It moved under the disclosure, so the supervised answer
   and the cemented answer render identically. That identity is the point. */

function renderChat() {
  const chat = $("chat");
  /* A held answer is a wait, not a message: it renders as the typing indicator
     until the review that releases it lands. */
  const settled = new Set(
    STATE.chat
      .filter((message) => message.kind === "released" || message.kind === "rejected")
      .map((message) => message.proposal_id));
  const waiting = STATE.thinking
    || STATE.chat.some((message) =>
      message.kind === "held" && !settled.has(message.proposal_id));
  const messages = STATE.chat.map(chatMessage).join("");
  const thinking = waiting
    ? `<div class="msg assistant"><div class="avatar">AI</div><div class="bubble">
         <div class="thinking"><span class="dots"><span></span><span></span><span></span></span>
         working\u2026</div></div></div>`
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
    return `<div class="msg user"><div class="bubble">
      <div class="attachment"><span class="clip" aria-hidden="true"></span>
        <span class="file">${esc(message.document_id)}.pdf</span>
        <span class="file-kind">${esc(message.title)}</span></div>
      <details class="ocr"><summary>scanned text</summary><pre>${esc(message.text)}</pre></details>
      <div class="ask">${esc(message.ask)}</div>
    </div></div>` + under(message);
  }
  if (message.kind === "released" || message.kind === "cement") {
    const body = message.error
      ? `<div class="preview-error">${esc(message.error)}</div>`
      : `<pre class="json">${jsonHtml(message.output)}</pre>`;
    return `<div class="msg assistant"><div class="avatar">AI</div>
      <div class="bubble">${body}</div></div>` + under(message);
  }
  if (message.kind === "rejected") {
    return `<div class="msg assistant"><div class="avatar">AI</div><div class="bubble">
      <div>I could not complete this request. Please try again.</div>
    </div></div>` + under(message);
  }
  /* `held` renders as the waiting indicator, and `miss` is invisible here by
     design: the request simply goes to the model, and the user waits. */
  return "";
}

/* The peel-back. It sits outside the bubble so the chat itself stays plain. */
function under(message) {
  const detail = message.under;
  if (!detail) return "";
  const rows = (detail.rows || [])
    .map(
      (row) => `<div class="under-row"><span class="k">${esc(row[0])}</span>
        <span class="v">${esc(row[1])}</span></div>`)
    .join("");
  const blocks = (detail.blocks || [])
    .map(
      (block) => `<div class="label-row" style="margin-top:10px">
         <span class="label">${esc(block.label)}</span></div>
       <pre class="json">${jsonHtml(block.json)}</pre>`)
    .join("");
  const diff = detail.diff
    ? (detail.diff.length
        ? `<div class="label-row" style="margin-top:10px">
             <span class="label">${esc(detail.diff_label || "difference")}</span></div>
           ${diffHtml(detail.diff)}`
        : `<div class="tiny dim" style="margin-top:10px">${esc(detail.diff_empty || "")}</div>`)
    : "";
  const commands = (detail.commands || []).length
    ? `<div class="label-row" style="margin-top:10px">
         <span class="label">${esc(detail.commands_label || "the command that ran")}</span>
         ${detail.commands_ran === false
            ? `<span class="label-note">not run by this page</span>`
            : ""}</div>
       ${detail.commands.map((line) =>
          `<pre class="shell ${detail.commands_ran === false ? "unrun" : ""}"
            >$ ${esc(line)}</pre>`).join("")}`
    : "";
  const note = detail.note
    ? `<div class="tiny dim" style="margin-top:10px">${esc(detail.note)}</div>`
    : "";
  return `<details class="under"><summary>what happened under this</summary>
    <div class="under-body">
      <div class="under-summary">${esc(detail.summary)}</div>
      <div class="under-rows">${rows}</div>
      ${blocks}${diff}${commands}${note}
    </div></details>`;
}

const diffHtml = (rows) =>
  `<div class="diff">${rows
    .map(
      (row) => `<div class="diff-row ${esc(row.kind)}">
        <span class="tag">${esc(row.kind)}</span>
        <span>${esc(row.field)}</span>
        <span class="dim">${esc(row.detail)}</span></div>`)
    .join("")}</div>`;

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

/* --- terminal: real `cement` invocations, condensed, verbatim one click away --- */

function commandHtml(row) {
  const reading = (row.reading || [])
    .map(
      (pair) => `<div class="read-row"><span class="rk">${esc(pair[0])}</span>
        <span class="rv">${esc(pair[1])}</span></div>`)
    .join("");
  return `<div class="cmd ${row.rc === 0 ? "" : "failed"}">
    <div class="cmd-line">$ ${esc(row.display)}</div>
    <div class="cmd-read">${reading}</div>
    <details class="stdout"><summary>stdout ${esc(row.bytes)} bytes
      \u00b7 exit ${esc(row.rc)} \u00b7 ${esc(row.ms)} ms</summary>
      <pre class="raw">${esc((row.argv || []).join(" "))}\n\n${esc(row.stdout)}</pre>
    </details>
  </div>`;
}

function renderTerminal() {
  const rows = STATE.terminal || [];
  $("terminal-count").textContent = rows.length
    ? `${rows.length} command${rows.length === 1 ? "" : "s"} have run`
    : "";
  if (!rows.length) {
    $("terminal").innerHTML =
      `<div class="empty">No command yet. Every operator action below runs the real
       <code>cement</code> binary against this ledger.</div>`;
    return;
  }
  const preamble = (STATE.ledger.preamble || [])
    .map((line) => `<div class="cmd-line preamble">$ ${esc(line)}</div>`)
    .join("");
  $("terminal").innerHTML =
    `<div class="cmd preamble-block">${preamble}</div>` +
    rows.map(commandHtml).join("");
  const node = $("terminal");
  if (!document.body.classList.contains("expanded")) node.scrollTop = node.scrollHeight;
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
       supervisor, and nowhere else.</div>`;
    return;
  }
  $("review").innerHTML = STATE.pending
    .map((proposal) => {
      const preview = proposal.preview_error
        ? `<div class="preview-error">This plan does not apply to the document:
             ${esc(proposal.preview_error)}</div>`
        : `<pre class="json">${jsonHtml(proposal.preview)}</pre>`;
      const diff = proposal.diff.length
        ? diffHtml(proposal.diff)
        : `<div class="tiny dim" style="margin-top:8px">The candidate matches the
           supervisor's plan for this layout.</div>`;
      return `<div class="proposal">
        <div class="proposal-head">
          <span class="badge llm">held</span>
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
        <div class="tiny dim" style="margin-top:9px">Each button runs the real command:</div>
        <pre class="shell">$ cement proposal review ${esc(proposal.proposal_id)} \\
    --reviewer ${esc(STATE.reviewer)} --decision &lt;accept|correct|reject&gt;</pre>
      </div>`;
    })
    .join("");
}

const row = (key, value) =>
  `<div class="row"><span class="k">${esc(key)}</span><span class="v">${esc(value)}</span></div>`;

function renderFunction() {
  const target = $("function");
  if (!STATE.function) {
    const drafts = (STATE.drafts || [])
      .map((draft) => row(
        `layout ${draft.layout} \u00b7 ${draft.status}`,
        `${draft.tests ? draft.tests + " tests \u00b7 " : ""}${short(draft.artifact_id, 14)}`))
      .join("");
    target.innerHTML = drafts
      ? drafts + `<div class="tiny dim" style="margin-top:9px">A draft is not a
          function. Promotion is a separate, explicit act.</div>`
      : `<div class="empty">No promoted set yet. Compile groups confirmed examples by
         exact scope, and it never promotes them.</div>`;
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
      <button class="button small primary" data-source="open">read the function</button>
      <button class="button small" data-offline="A03">answer A03 from the bundle</button>
      <a class="button small" href="/api/bundle.json" download="function.json">download bundle</a>
    </div>
    ${offlineResult}`;
}

/* --- function source --- */

function renderSource() {
  const overlay = $("overlay");
  const fn = STATE.function;
  if (!SOURCE_OPEN || !fn || !fn.source) {
    overlay.hidden = true;
    return;
  }
  const key = [fn.function_hash]
    .concat((fn.excluded || []).map((row) => row.layout + ":" + row.confirmations))
    .join("|");
  if (overlay.hidden || key !== SOURCE_KEY) {
    $("source").innerHTML = sourceHtml(fn);
    SOURCE_KEY = key;
  }
  overlay.hidden = false;
}

function sourceHtml(fn) {
  const src = fn.source;
  const count = src.entries.length;
  const passed = fn.checks.filter((check) => check.passed).length;
  const head = [
    `# cement \u00b7 ${src.partition} \u00b7 ${src.operation} @ revision ${src.revision}`,
    `# function_hash ${fn.function_hash}`,
    `# ${count} entr${count === 1 ? "y" : "ies"} \u00b7 ${passed}/${fn.checks.length} ` +
      `checks passed \u00b7 receipt ${fn.receipt_id} \u00b7 ${fn.bundle_bytes} bytes`,
    "# a reading of the exported cement-function-v2 bundle; Cement seals exact " +
      "entries, and it emits no code",
  ]
    .map((line) => `<span class="c">${esc(line)}</span>`)
    .join("\n");
  const tail = [
    `    <span class="kw">raise</span> <span class="fn">NoMatch</span>   ` +
      `<span class="c">${esc("# outside the verified boundary \u2192 the supervised path")}</span>`,
  ];
  for (const row of fn.excluded || []) {
    if (tail.length === 1) tail.push("", `<span class="c">${esc("# not in this function:")}</span>`);
    tail.push(`<span class="c">${esc(
      `#   layout ${row.layout} \u00b7 ${row.document_type} \u00b7 ` +
      `${row.confirmations}/${row.required} confirmations \u00b7 still supervised`)}</span>`);
  }
  const name = String(src.operation).replace(/[^A-Za-z0-9]+/g, "_");
  return `<pre class="code">${head}\n\n<span class="kw">def</span> ` +
    `<span class="fn">${esc(name)}</span>(input):</pre>` +
    src.entries.map((entry) => entryHtml(entry, count)).join("") +
    `<pre class="code">${tail.join("\n")}</pre>`;
}

/* One-line stand-in for a value: scalars verbatim, containers by size. */
function elide(value) {
  if (Array.isArray(value)) {
    return `[<span class="p">${value.length} item${value.length === 1 ? "" : "s"}</span>]`;
  }
  if (value && typeof value === "object") {
    const size = Object.keys(value).length;
    return `{<span class="p">${size} key${size === 1 ? "" : "s"}</span>}`;
  }
  return jsonHtml(value);
}

function elideTop(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return elide(value);
  return "{" + Object.keys(value)
    .map((key) => `<span class="k">${esc(JSON.stringify(key))}</span>: ${elide(value[key])}`)
    .join(", ") + "}";
}

function entryHtml(entry, total) {
  const meta =
    `    # entry ${entry.index}/${total} \u00b7 layout ${entry.layout} \u00b7 ` +
    `artifact ${String(entry.artifact_hash).slice(0, 12)}\u2026 \u00b7 ` +
    `${entry.confirmations} confirmation${entry.confirmations === 1 ? "" : "s"}` +
    (entry.reviewers.length ? ` \u00b7 ${entry.reviewers.join(", ")}` : "");
  /* The signature is bulky and the plan is the point, so the guard opens elided. The
     exact bytes stay one click away: they are what the entry actually matches on. */
  const guard =
    `<details class="exact"><summary>    <span class="kw">if</span> input == ` +
    `${elideTop(entry.input)}:<span class="hint">exact input</span></summary>` +
    `<pre class="code">        <span class="c">${esc(
      "# the exact canonical JSON this entry matches, byte for byte")}</span>\n` +
    `        ${jsonBlock(entry.input, "        ")}</pre></details>`;
  const origins = entry.originals.length
    ? `<details class="origins"><summary>the ${entry.originals.length} supervised
         request${entry.originals.length === 1 ? "" : "s"} behind this entry</summary>
       <div class="hop-note">No command prints an entry beside its originals, and
         <code>events</code> carries no example filter. These
         ${entry.hops.length} commands ran to rebuild the lineage:</div>
       <div class="hops">${entry.hops.map(commandHtml).join("")}</div>
       ${entry.originals.map(originHtml).join("")}</details>`
    : `<div class="tiny dim" style="margin:10px 0 0 32px">This session holds no request
         record for this entry.</div>`;
  return `<div class="entry">
    <pre class="code"><span class="c">${esc(meta)}</span></pre>
    ${guard}
    <pre class="code">        <span class="kw">return</span> ` +
    `${jsonBlock(entry.output, "        ")}</pre>
    ${origins}
  </div>`;
}

function originHtml(row) {
  const verdict = row.diff.length
    ? `<span class="badge set">corrected</span>`
    : `<span class="badge pass">accepted unchanged</span>`;
  const change = row.diff.length
    ? `<div class="label-row" style="margin-top:10px">
         <span class="label">What the supervisor changed</span></div>
       ${diffHtml(row.diff)}`
    : `<div class="tiny dim" style="margin-top:10px">The entry holds this plan byte for
         byte.</div>`;
  return `<div class="origin">
    <div class="origin-head">
      <span class="badge llm">request ${esc(row.document_id)}</span>
      ${verdict}
      <span class="tiny dim">${esc(row.provider)} \u00b7 ${esc(row.provider_ms)} ms
        simulated \u00b7 variant ${esc(row.variant)}</span>
    </div>
    <div class="note">The provider ${esc(row.note)}.</div>
    <div class="label-row" style="margin-top:10px">
      <span class="label">proposed_output \u2014 the plan the model wrote</span></div>
    <pre class="json">${jsonHtml(row.provider_plan)}</pre>
    ${change}
    <div class="answer-meta">
      <span>proposal ${esc(row.proposal_id)}</span>
      <span>example ${esc(row.example_id)}</span>
      <span>${esc(row.status)} by ${esc(row.reviewer)}</span></div>
  </div>`;
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
  const wait = stats.provider_ms_mean === null
    ? "\u2014"
    : (stats.provider_ms_mean / 1000).toFixed(1) + " s";
  const resolve = stats.resolve_ms_median === null
    ? "\u2014"
    : stats.resolve_ms_median + " ms";
  $("metrics").innerHTML = `
    ${row("answers held for a supervisor", stats.provider_calls)}
    ${row("answers needing no supervision", stats.cement_answers)}
    ${row("mean model wait, simulated", wait)}
    ${row("median resolve, measured", resolve)}
    ${row("distinct model plans for one layout", distinct)}
    ${row("outputs per entry, byte-identical", 1)}
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
  const target = event.target.closest(
    "[data-send],[data-review],[data-action],[data-offline],[data-revoke],[data-source]");
  if (!target || BUSY) return;
  if (target.dataset.send) send(target.dataset.send);
  else if (target.dataset.review) review(target.dataset.proposal, target.dataset.review);
  else if (target.dataset.action) lifecycle(target.dataset.action);
  else if (target.dataset.offline) offline(target.dataset.offline);
  else if (target.dataset.revoke) revoke(target.dataset.revoke);
  else if (target.dataset.source) setSource(true);
});

function setSource(open) {
  SOURCE_OPEN = open;
  render();
}

$("overlay-close").addEventListener("click", () => setSource(false));
$("overlay").addEventListener("click", (event) => {
  if (event.target === $("overlay")) setSource(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && SOURCE_OPEN) setSource(false);
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
  if (parameters.has("source")) SOURCE_OPEN = true;
  if (parameters.has("open")) OPEN_ALL = true;
  if (parameters.has("reset")) await call("/api/reset", {});
  STATE = await (await fetch("/api/state")).json();
  render();
  if (parameters.has("scene")) await runStory(Number(parameters.get("scene")));
})();
