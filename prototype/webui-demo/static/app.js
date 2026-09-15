"use strict";

/* Cement web UI demo. One render pass per state snapshot; the server holds all state. */

let STATE = null;
let BUSY = false;
let POLL = null;
/* The operation whose source overlay is open, or "" for none. */
let SOURCE_OPEN = "";
let OPEN_ALL = false;
/* Re-rendering the source collapses every open <details>, so redraw only on change. */
let SOURCE_KEY = "";

const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const short = (value, size = 12) =>
  value ? esc(String(value).slice(0, size)) + "\u2026" : "\u2014";
const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

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

const documentOf = (id) => STATE.documents.find((row) => row.id === id) || {};
const operationOf = (name) => STATE.operations.find((row) => row.name === name) || {};
const scenarioOf = (id) => STATE.scenarios.find((row) => row.id === id) || {};

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

const send = (id) => call("/api/send", { request_id: id });
const select = (id) => call("/api/select", { scenario: id });
const review = (proposalId, decision) =>
  call("/api/review", { proposal_id: proposalId, decision });
const revoke = (exampleId) => call("/api/revoke", { example_id: exampleId });
const lifecycle = (action) => call("/api/" + action, {});
const route = (enabled) => call("/api/route", { enabled });
const offline = (id, operation) =>
  call("/api/offline", { document_id: id, operation });

/* --- render --- */

function render() {
  if (!STATE) return;
  $("chip-partition").textContent = STATE.partition;
  $("policy-note").textContent =
    `promotes at ${STATE.policy.min_confirmations} confirmations, ` +
    `${STATE.policy.min_reviewers} reviewer`;
  renderChat();
  renderTray();
  renderTasks();
  renderTerminal();
  renderCategories();
  renderReview();
  renderFunctions();
  renderSource();
  renderRouting();
  renderMetrics();
  renderLog();
  /* Capture aid: a screenshot cannot click a disclosure open. Verbatim stdout stays
     shut, since five raw dumps bury the reading they belong to, and per-entry lineage
     stays as the overlay renders it: entry 1 open, the rest one click away. */
  if (OPEN_ALL) {
    for (const node of document.querySelectorAll(
      "details:not(.stdout):not(.origins)")) {
      node.open = true;
    }
  }
}

/* --- chat: a plain chat, and nothing else ---
   Every badge, id, digest and timing this pane once printed is machinery the
   deployment never shows. It moved under the disclosure, so the supervised answer
   and the cemented answer render identically. That identity is the point. */

function renderChat() {
  const chat = $("chat");
  /* A turn is one question, however many operations answer it. It shows the typing
     indicator until every part settles, and the reply lands in one bubble. */
  const settled = new Set(
    STATE.chat
      .filter((message) => message.kind === "answer" || message.kind === "refused")
      .map((message) => message.turn));
  const waiting = STATE.thinking
    || STATE.chat.some((message) =>
      message.kind === "held" && !settled.has(message.turn));
  const messages = STATE.chat.map(chatMessage).join("");
  const thinking = waiting
    ? `<div class="msg assistant"><div class="avatar">AI</div><div class="bubble">
         <div class="thinking"><span class="dots"><span></span><span></span><span></span></span>
         working\u2026</div></div></div>`
    : "";
  const empty = STATE.chat.length
    ? ""
    : `<div class="empty">Staff send the assistant a document and a request. Pick one
       below; the wording varies on purpose.</div>`;
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
  if (message.kind === "answer") {
    const body = message.error
      ? `<div class="preview-error">${esc(message.error)}</div>`
      : message.render === "text"
        ? `<div>${esc(message.body)}</div>`
        : `<pre class="json">${jsonHtml(message.body)}</pre>`;
    return `<div class="msg assistant"><div class="avatar">AI</div>
      <div class="bubble">${body}</div></div>` + under(message);
  }
  if (message.kind === "refused") {
    return `<div class="msg assistant"><div class="avatar">AI</div><div class="bubble">
      <div>I could not complete this request. Please try again.</div>
    </div></div>` + under(message);
  }
  /* `held` renders as the waiting indicator above: the user simply waits. */
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
      ${blocks}${commands}${note}
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

/* --- the tray: one heading per task, the rewordings under it ---
   The rewordings are the point. Cement never sees them: the model reads each one,
   names the same operation, and Cement answers that operation and an exact input. */

function renderTray() {
  $("tray").innerHTML = STATE.scenarios
    .map((task) => {
      const cards = task.requests
        .map((request) => {
          const document_ = documentOf(request.document_id);
          return `<button class="ask-card" data-send="${esc(request.id)}"
            ${BUSY ? "disabled" : ""}>
            <span class="ask-text">${esc(request.ask)}</span>
            <span class="ask-doc">${esc(request.document_id)} \u00b7
              ${esc(document_.patient || "")}</span>
          </button>`;
        })
        .join("");
      return `<div class="task-group ${task.id === STATE.selected ? "on" : ""}">
        <div class="task-head">
          <span class="task-title">${esc(task.title)}</span>
          <span class="task-intent">${esc(task.intent)}</span>
        </div>
        <div class="task-asks">${cards}</div>
      </div>`;
    })
    .join("");
}

/* --- the task switch and the operation map --- */

function operationStatus(operation) {
  if (operation.promoted) {
    const count = operation.entries;
    return ["set", `sealed \u00b7 ${count} ${count === 1 ? "entry" : "entries"}`];
  }
  if (operation.keyed_on === "text") return ["warn", "stays supervised"];
  if (operation.blocked) return ["llm", "below the floor"];
  return ["", "no evidence yet"];
}

function renderTasks() {
  $("task-switch").innerHTML = STATE.scenarios
    .map(
      (task) => `<button class="task-pill ${task.id === STATE.selected ? "on" : ""}"
        data-select="${esc(task.id)}" ${BUSY ? "disabled" : ""}>
        <span class="pill-title">${esc(task.title)}</span>
        <span class="pill-ops">${task.operations.length === 1
          ? "1 operation" : task.operations.length + " operations"}</span>
      </button>`)
    .join("");
  const promoted = STATE.promoted_operations.length;
  $("coverage-note").textContent =
    `${promoted} of ${STATE.operations.length} sealed`;
  $("coverage").innerHTML = STATE.operations
    .map((operation) => {
      const [tone, label] = operationStatus(operation);
      const callers = operation.callers.length === 1
        ? "1 task calls it"
        : `${operation.callers.length} tasks call it`;
      return `<div class="op-row ${operation.selected ? "on" : ""}">
        <div class="op-main">
          <span class="op-name">${esc(operation.name)}</span>
          <span class="badge ${tone}">${esc(label)}</span>
        </div>
        <div class="op-decides">${esc(operation.decides)}</div>
        <div class="op-callers" title="${esc(operation.callers.join(" \u00b7 "))}">
          ${esc(callers)}: ${esc(operation.callers.join(" \u00b7 "))}</div>
      </div>`;
    })
    .join("");
  const names = STATE.selected_operations.join(", ");
  $("lifecycle-note").textContent =
    `Each button runs once per operation this task reaches: ${names}.`;
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
  if (category.keyed_on === "text") return ["never repeats", "warn"];
  if (category.confirmations >= category.required) return ["ready to compile", "pass"];
  return ["gathering evidence", "llm"];
}

function renderCategories() {
  if (!STATE.categories.length) {
    $("categories").innerHTML =
      `<div class="empty">No scope yet for this task. A scope appears when an exact
       input arrives for the first time.</div>`;
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
      const scope = category.keyed_on === "text"
        ? `assessment text of ${esc(category.document_id)}`
        : `layout ${esc(category.layout)}`;
      return `<div class="category ${category.promoted ? "promoted" : ""}">
        <div class="category-head">
          <span class="layout-tag">${esc(category.operation_label)} \u00b7 ${scope}</span>
          <span class="badge ${tone}">${label}</span>
        </div>
        <div class="category-type">${esc(category.operation)} \u00b7
          input ${short(category.input_hash)}</div>
        <div class="meter ${percent >= 100 ? "full" : ""}"><i style="width:${percent}%"></i></div>
        <div class="category-facts">
          <span>${category.confirmations}/${category.required} confirmations</span>
          <span>${plural(category.reviewers.length, "reviewer")}</span>
          <span>${category.distinct_candidates} distinct model
            answer${category.distinct_candidates === 1 ? "" : "s"}</span>
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
        : proposal.preview
          ? `<div class="label-row" style="margin-top:10px">
               <span class="label">What this plan pulls out of ${esc(proposal.document_id)}</span>
             </div><pre class="json">${jsonHtml(proposal.preview)}</pre>`
          : "";
      const diff = proposal.diff.length
        ? diffHtml(proposal.diff)
        : `<div class="tiny dim" style="margin-top:8px">The candidate matches the
           supervisor's answer for this scope.</div>`;
      return `<div class="proposal">
        <div class="proposal-head">
          <span class="badge llm">held</span>
          <span class="hash">${esc(proposal.proposal_id)}</span>
          <span class="tiny dim">${esc(proposal.document_id)} \u00b7
            ${esc(proposal.scope_label)}</span>
        </div>
        <div class="proposal-op">${esc(proposal.operation)} \u2014
          ${esc(proposal.decides)}</div>
        <div class="note">The model ${esc(proposal.note)}.</div>
        <div class="label-row" style="margin-top:10px">
          <span class="label">The answer the model wrote</span></div>
        <pre class="json">${jsonHtml(proposal.plan)}</pre>
        ${preview}
        <div class="label-row" style="margin-top:10px">
          <span class="label">Difference from the supervisor's correction</span></div>
        ${diff}
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

/* --- one card per operation this task reaches ---
   A task that reaches an already-sealed operation lands on the SAME card, and the
   card names every task that calls it. That is what reuse looks like from here. */

function renderFunctions() {
  $("functions").innerHTML = STATE.functions.map(functionCard).join("");
}

function callerLine(fn) {
  const others = fn.callers.filter((title) => title !== scenarioOf(STATE.selected).title);
  if (!others.length) {
    return `<div class="fn-callers">Only this task calls it.</div>`;
  }
  return `<div class="fn-callers">Also answers
    ${esc(others.join(", "))} \u2014 one function, ${plural(fn.callers.length, "caller")}.
    </div>`;
}

function functionCard(fn) {
  const head = `<div class="fn-head">
      <span class="fn-name">${esc(fn.operation)}</span>
      <span class="badge ${fn.promoted ? "set" : fn.keyed_on === "text" ? "warn" : "llm"}"
        >${fn.promoted ? "promoted" : fn.keyed_on === "text"
          ? "never cements" : "not promoted"}</span>
    </div>
    <div class="fn-decides">${esc(fn.decides)}</div>
    ${callerLine(fn)}`;
  if (!fn.promoted) return `<div class="fn-card">${head}${unpromotedBody(fn)}</div>`;
  const checks = fn.checks
    .map(
      (check) => `<div class="check ${check.passed ? "" : "failed"}">
        <span class="dot"></span><span>${esc(check.key)}</span>
        <span class="detail">${esc(check.detail)}</span></div>`)
    .join("");
  const document_ = offlineDocument(fn);
  const result = STATE.offline && STATE.offline.operation === fn.operation
    ? offlineHtml(STATE.offline)
    : "";
  return `<div class="fn-card promoted">${head}
    ${row("entries", fn.entries)}
    ${row("verdict", fn.passed ? "verified" : "failed")}
    ${row("receipt", fn.receipt_id)}
    ${row("bundle", fn.bundle_bytes + " bytes")}
    <div class="row"><span class="k">function_hash</span></div>
    <div class="hash">${esc(fn.function_hash)}</div>
    <div class="checks">${checks}</div>
    ${excludedHtml(fn)}
    <div class="actions">
      <button class="button small primary" data-source="${esc(fn.operation)}"
        >read the function</button>
      ${document_ ? `<button class="button small" data-offline="${esc(document_)}"
        data-operation="${esc(fn.operation)}">answer ${esc(document_)} from the
        bundle</button>` : ""}
      <a class="button small" href="/api/bundle.json?operation=${encodeURIComponent(fn.operation)}"
        download="${esc(fn.operation)}.json">download bundle</a>
    </div>
    ${result}</div>`;
}

function unpromotedBody(fn) {
  const drafts = (STATE.drafts || [])
    .filter((draft) => draft.operation === fn.operation)
    .map((draft) => row(
      `layout ${draft.layout} \u00b7 ${draft.status}`,
      `${draft.tests ? draft.tests + " tests \u00b7 " : ""}${short(draft.artifact_id, 14)}`))
    .join("");
  const blocked = (fn.blocked || [])
    .map((scope) => `<div class="blocked-row">
      <span class="badge warn">blocked</span>
      <span>${esc(scope.label)} \u2014
        ${esc((scope.reasons || []).join("; "))}</span></div>`)
    .join("");
  const reason = fn.keyed_on === "text"
    ? `<div class="tiny dim" style="margin-top:9px">This operation is keyed on the
       note's own words, and no second note repeats them. Every scope stays at one
       confirmation, so the compiler blocks it forever and the model keeps answering
       under supervision. That is the design, not a gap.</div>`
    : `<div class="tiny dim" style="margin-top:9px">A draft is not a function.
       Promotion is a separate, explicit act.</div>`;
  const empty = drafts || blocked
    ? ""
    : `<div class="empty">No promoted set yet. Compile groups confirmed examples by
       exact scope, and it never promotes them.</div>`;
  return drafts + blocked + empty + reason;
}

function excludedHtml(fn) {
  if (!(fn.excluded || []).length) return "";
  return `<div class="label-row" style="margin-top:12px">
      <span class="label">Outside this function</span></div>
    ${fn.excluded.map((scope) => `<div class="blocked-row">
      <span class="badge warn">${scope.confirmations}/${scope.required}</span>
      <span>${esc(scope.label)} \u2014 still supervised</span></div>`).join("")}`;
}

/* A document in a sealed scope that no confirmed example came from, so the bundle
   answers a page the function has never been shown. */
function offlineDocument(fn) {
  const entries = (fn.source && fn.source.entries) || [];
  const scopes = new Set(entries.map((entry) => entry.input_hash));
  const seen = new Set(
    entries.flatMap((entry) => entry.originals.map((origin) => origin.document_id)));
  const pool = STATE.documents.filter((document_) => scopes.has(document_.input_hash));
  const fresh = pool.find((document_) => !seen.has(document_.id));
  return (fresh || pool[0] || {}).id || "";
}

function offlineHtml(result) {
  return `<div class="label-row" style="margin-top:12px">
      <span class="label">Answer from the bundle alone</span></div>
    ${result.matched
      ? `<pre class="json">${jsonHtml(result.output)}</pre>
         <div class="answer-meta"><span>${esc(result.document_id)} matched</span>
           <span>artifact ${short(result.artifact_hash)}</span>
           <span>no ledger read</span></div>`
      : `<div class="tiny dim">${esc(result.document_id)}: the bundle holds no entry for
         this input, so it reports a miss.</div>`}`;
}

/* --- function source --- */

function renderSource() {
  const overlay = $("overlay");
  const fn = STATE.functions.find(
    (row_) => row_.operation === SOURCE_OPEN && row_.promoted);
  if (!fn || !fn.source) {
    overlay.hidden = true;
    return;
  }
  const key = [fn.operation, fn.function_hash]
    .concat((fn.excluded || []).map((scope) => scope.label + ":" + scope.confirmations))
    .join("|");
  if (overlay.hidden || key !== SOURCE_KEY) {
    $("overlay-title").textContent = fn.source.label;
    $("overlay-sub").textContent =
      `${fn.operation} \u00b7 every supervised answer, condensed into one function`;
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
    `# called by ${fn.callers.join(", ")}`,
    "# a reading of the exported cement-function-v2 bundle; Cement seals exact " +
      "entries, and it emits no code",
  ]
    .map((line) => `<span class="c">${esc(line)}</span>`)
    .join("\n");
  const tail = [
    `    <span class="kw">raise</span> <span class="fn">NoMatch</span>   ` +
      `<span class="c">${esc("# outside the verified boundary \u2192 the supervised path")}</span>`,
  ];
  for (const scope of fn.excluded || []) {
    if (tail.length === 1) tail.push("", `<span class="c">${esc("# not in this function:")}</span>`);
    tail.push(`<span class="c">${esc(
      `#   ${scope.label} \u00b7 ${scope.confirmations}/${scope.required} ` +
      "confirmations \u00b7 still supervised")}</span>`);
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
    return `[<span class="p">${plural(value.length, "item")}</span>]`;
  }
  if (value && typeof value === "object") {
    const size = Object.keys(value).length;
    return `{<span class="p">${plural(size, "key")}</span>}`;
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
    `    # entry ${entry.index}/${total} \u00b7 ${entry.label} \u00b7 ` +
    `artifact ${String(entry.artifact_hash).slice(0, 12)}\u2026 \u00b7 ` +
    `${plural(entry.confirmations, "confirmation")}` +
    (entry.reviewers.length ? ` \u00b7 ${entry.reviewers.join(", ")}` : "");
  /* The input is bulky and the answer is the point, so the guard opens elided. The
     exact bytes stay one click away: they are what the entry actually matches on. */
  const guard =
    `<details class="exact"><summary>    <span class="kw">if</span> input == ` +
    `${elideTop(entry.input)}:<span class="hint">exact input</span></summary>` +
    `<pre class="code">        <span class="c">${esc(
      "# the exact canonical JSON this entry matches, byte for byte")}</span>\n` +
    `        ${jsonBlock(entry.input, "        ")}</pre></details>`;
  /* The first entry opens its lineage, because an entry with no visible history is
     the very thing this view exists to fix. The rest stay one click away. */
  const origins = entry.originals.length
    ? `<details class="origins" ${entry.index === 1 ? "open" : ""}><summary>the
         ${entry.originals.length} supervised
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

function originHtml(origin) {
  const verdict = origin.diff.length
    ? `<span class="badge set">corrected</span>`
    : `<span class="badge pass">accepted unchanged</span>`;
  const change = origin.diff.length
    ? `<div class="label-row" style="margin-top:10px">
         <span class="label">What the supervisor changed</span></div>
       ${diffHtml(origin.diff)}`
    : `<div class="tiny dim" style="margin-top:10px">The entry holds this answer byte for
         byte.</div>`;
  return `<div class="origin">
    <div class="origin-head">
      <span class="badge llm">request ${esc(origin.document_id)}</span>
      ${verdict}
      <span class="tiny dim">${esc(origin.provider)} \u00b7 ${esc(origin.provider_ms)} ms
        simulated \u00b7 variant ${esc(origin.variant)}</span>
    </div>
    <div class="note">The model ${esc(origin.note)}.</div>
    <div class="label-row" style="margin-top:10px">
      <span class="label">proposed_output \u2014 what the model wrote</span></div>
    <pre class="json">${jsonHtml(origin.provider_plan)}</pre>
    ${change}
    <div class="answer-meta">
      <span>proposal ${esc(origin.proposal_id)}</span>
      <span>example ${esc(origin.example_id)}</span>
      <span>${esc(origin.status)} by ${esc(origin.reviewer)}</span></div>
  </div>`;
}

function renderRouting() {
  const on = STATE.routed;
  const count = STATE.promoted_operations.length;
  $("routing").innerHTML = `
    <div class="switch-row">
      <button class="switch ${on ? "on" : ""}" id="switch" aria-pressed="${on}">
        <span class="knob"></span></button>
      <div class="switch-labels">
        <span class="switch-state ${on ? "on" : "off"}">
          ${on
            ? `${plural(count, "operation")} resolve${count === 1 ? "s" : ""} from a function`
            : "every request goes to the model"}</span>
        <span class="tiny dim">${on
          ? "One switch covers every promoted operation. An input outside a promoted set returns to the supervised path."
          : "Turn this on when the operator decides the evidence is ready."}</span>
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
    ${row("turns held for a supervisor", stats.provider_calls)}
    ${row("answers needing no supervision", stats.cement_answers)}
    ${row("operations sealed", STATE.promoted_operations.length)}
    ${row("mean model wait, simulated", wait)}
    ${row("median resolve, measured", resolve)}
    ${row("distinct model answers for one scope", distinct)}
    <div class="tiny dim" style="margin-top:9px">
      ${plural(stats.provider_calls_avoided, "model call")}
      avoided \u00b7 ${plural(stats.reviews, "review")} recorded.
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

/* --- the story: cement every cementable task, and show the one that cannot --- */

/* A supervisor corrects what diverges and accepts what already matches. The first
   candidate for a scope always diverges, so a correction is always visible. */
async function settle() {
  while (STATE.pending.length) {
    const proposal = STATE.pending[0];
    await review(proposal.proposal_id, proposal.diff.length ? "correct" : "accept");
    await pause(320);
  }
}

const seal = () => [
  () => lifecycle("compile"),
  () => lifecycle("verify"),
  () => lifecycle("promote"),
];

const turn = (request) => [() => send(request), () => settle()];

const SCENES = [
  { name: "desk", steps: [] },
  { name: "held", steps: [() => send("q01")] },
  { name: "evidence", steps: [() => settle(), ...turn("q02")] },
  { name: "cemented", steps: seal() },
  { name: "routed", steps: [() => route(true), () => send("q03")] },
  { name: "reuse", steps: [...turn("q05"), ...turn("q06"), ...seal()] },
  {
    name: "covered",
    steps: [
      ...turn("q08"), ...turn("q09"), ...seal(),
      ...turn("q10"), ...turn("q11"), ...seal(),
    ],
  },
  { name: "blocked", steps: [...turn("q12"), () => lifecycle("compile")] },
  {
    name: "bundle",
    steps: [() => select("file"), () => offline("A03", "document.extraction_plan")],
  },
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
    "[data-send],[data-review],[data-action],[data-offline],[data-revoke]," +
    "[data-source],[data-select]");
  if (!target || BUSY) return;
  if (target.dataset.send) send(target.dataset.send);
  else if (target.dataset.select) select(target.dataset.select);
  else if (target.dataset.review) review(target.dataset.proposal, target.dataset.review);
  else if (target.dataset.action) lifecycle(target.dataset.action);
  else if (target.dataset.offline) {
    offline(target.dataset.offline, target.dataset.operation);
  } else if (target.dataset.revoke) revoke(target.dataset.revoke);
  else if (target.dataset.source) setSource(target.dataset.source);
});

function setSource(operation) {
  SOURCE_OPEN = operation;
  render();
}

$("overlay-close").addEventListener("click", () => setSource(""));
$("overlay").addEventListener("click", (event) => {
  if (event.target === $("overlay")) setSource("");
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && SOURCE_OPEN) setSource("");
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
  if (parameters.has("open")) OPEN_ALL = true;
  if (parameters.has("reset")) await call("/api/reset", {});
  STATE = await (await fetch("/api/state")).json();
  if (parameters.has("source")) SOURCE_OPEN = parameters.get("source");
  render();
  /* The webfonts load after the first paint and change every line height, so the
     scroll offsets computed above land short. Render again once they are in. */
  if (document.fonts) await document.fonts.ready.then(render);
  if (parameters.has("scene")) await runStory(Number(parameters.get("scene")));
})();
