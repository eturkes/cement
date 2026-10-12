"use strict";

/* Cement web UI demo. One render pass per state snapshot; the server holds all state. */

let STATE = null;
let BUSY = false;
let POLL = null;
/* The operation whose source overlay is open, or "" for none. */
let SOURCE_OPEN = "";
let OPEN_ALL = false;
let DRAWER = "";
let HISTORY = false;
/* Re-rendering the source collapses every open <details>, so redraw only on change. */
let SOURCE_KEY = "";

const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const short = (value, size = 12) =>
  value ? esc(String(value).slice(0, size)) + "\u2026" : "\u2014";
const plural = (count, word) => `${count} ${count === 1 ? word : word === "entry" ? "entries" : word + "s"}`;

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
  if (DRAWER && !STATE.selected_operations.includes(DRAWER)) DRAWER = STATE.selected_operations[0];
  renderChat();
  renderTray();
  renderStory();
  renderTasks();
  renderReview();
  renderCategories();
  renderFunctions();
  renderTerminal();
  renderMetrics();
  renderLog();
  renderRouting();
  renderSource();
  $("drawer").hidden = !DRAWER;
  $("drawer-title").textContent = DRAWER ? operationOf(DRAWER).label : "";
  $("benefit").textContent = STATE.stats.cement_answers
    ? `${plural(STATE.stats.cement_answers, "operation")} answered without the model. The chat looks the same.`
    : "Repeated, checked answers can become exact deterministic entries.";
}

/* --- chat: a plain chat, and nothing else ---
   Every badge, id, digest and timing this pane once printed is machinery the
   deployment never shows. It moved under the disclosure, so the supervised answer
   and the cemented answer render identically. That identity is the point. */

function renderChat() {
  const chat = $("chat");
  /* A turn is one question, however many operations answer it. It shows the typing
     indicator while the model writes, and the reply lands in one bubble. The wait is
     the model's alone: no supervisor holds up a chat. */
  const previous = STATE.chat.slice(0, -2);
  const history = previous.length ? `<button class="button small" data-history="1">${HISTORY ? "Hide" : "Show"} ${plural(previous.length / 2, "earlier turn")}</button>${HISTORY ? previous.map(chatMessage).join("") : ""}` : "";
  const messages = history + STATE.chat.slice(-2).map(chatMessage).join("");
  const thinking = STATE.thinking
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
  /* The only other kind is `answer`, and one bubble carries every part of the turn. */
  const body = message.error
    ? `<div class="preview-error">${esc(message.error)}</div>`
    : message.render === "text"
      ? `<div>${esc(message.body)}</div>`
      : `<pre class="json">${jsonHtml(message.body)}</pre>`;
  return `<div class="msg assistant"><div class="avatar">AI</div>
    <div class="bubble">${body}</div></div>` + under(message);
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
  $("task-switch").innerHTML = STATE.scenarios.map(task =>
    `<button class="task-pill ${task.id === STATE.selected ? "on" : ""}" data-select="${esc(task.id)}" ${BUSY ? "disabled" : ""}>${esc(task.title)}</button>`).join("");
  const task = scenarioOf(STATE.selected);
  $("tray").innerHTML = `<details><summary>Choose a wording · ${esc(task.title)}</summary>
    ${task.requests.map(request => `<button class="ask-card" data-send="${esc(request.id)}" ${BUSY ? "disabled" : ""}>${esc(request.ask)}<small>${esc(request.document_id)} · ${esc(documentOf(request.document_id).patient || "")}</small></button>`).join("")}</details>`;
}

function renderTasks() {
  $("coverage-note").textContent = `${STATE.promoted_operations.length} of ${STATE.operations.length} jobs prepared`;
  $("coverage").innerHTML = STATE.operations.map(op => `<button class="operator-job button" data-operation-open="${esc(op.name)}">${esc(op.label)} · ${op.promoted ? "checked answer prepared" : op.blocked ? "not enough repeated evidence" : "still learning"}</button>`).join("");
  $("boundary-note").textContent = "Only the exact checked input matches. Other inputs return to the model.";
}

let CHECK_OPEN = false;

function storyStep(number, symbol, title, body, action = "", tone = "") {
  return `<section class="story-step ${tone}"><span class="story-number">${number}</span><div><div class="story-illustration" aria-hidden="true">${symbol}</div><h3>${title}</h3><p>${body}</p>${action}</div></section>`;
}

function renderStory() {
  const task = scenarioOf(STATE.selected);
  const turn = STATE.latest_turn;
  const parts = turn ? turn.parts : [];
  const model = parts.filter(p => p.source !== "function");
  const fixed = parts.filter(p => p.source === "function");
  const pending = STATE.pending.find(p => parts.some(part => part.proposal_id === p.proposal_id));
  const checked = model.filter(p => p.status === "corrected" || p.status === "accepted");
  const rejected = model.some(p => p.status === "rejected");
  const doc = turn ? documentOf(turn.document_id) : {};
  const categories = STATE.categories.filter(c => c.keyed_on === "text" ? c.document_id === doc.id : c.layout === doc.layout);
  const needed = STATE.selected_operations.filter(name => operationOf(name).keyed_on !== "text");
  const prepared = needed.length && needed.every(name => categories.some(c => c.operation === name && c.promoted) && STATE.functions.some(fn => fn.operation === name && fn.passed));
  const ready = prepared || (needed.length && needed.every(name => categories.some(c => c.operation === name && c.confirmations >= c.required)));
  const floor = STATE.policy.min_confirmations;
  const support = categories.filter(c => c.keyed_on !== "text").map(c => c.confirmations);
  const count = support.length ? Math.min(...support) : 0;
  const billing = STATE.selected === "bill";
  const button = (label, attr) => `<button class="button primary story-action" ${attr} ${BUSY ? "disabled" : ""}>${label}</button>`;
  let html = `<div class="story-heading"><span class="eyebrow">Behind this task</span><h3>${esc(task.title)}</h3>${turn ? `<p class="tiny dim">Most recent request for this task: ${esc(turn.document_id)}.pdf</p>` : ""}</div>`;
  html += storyStep(1, fixed.length && !model.length ? "✓ → reply" : "model → reply",
    !turn ? "First, the model answers." : !model.length ? "A checked answer replied. No model ran." : fixed.length ? "Part was automatic. The model answered the rest." : "The model wrote this answer.",
    !turn ? "Send a request on the left. The user gets the reply before anyone checks it." : "The chat looks the same either way. The user never waits for a supervisor.");
  let checkBody = !turn ? "A person checks the answer because a model can make mistakes." : !model.length ? "Earlier answers were checked before this work became automatic." : rejected ? "The supervisor rejected this answer. It cannot teach Cement anything." : checked.length ? `A supervisor ${model.some(p => p.status === "corrected") ? "fixed mistakes in" : "accepted"} the answer after the user received it.` : "A person must check what the model wrote before Cement can reuse it.";
  let checkAction = pending ? button("Check this answer", 'data-check-open="1"') : "";
  if (pending && CHECK_OPEN) {
    checkAction = `<div class="story-check"><p>What the model wrote</p><pre>${jsonHtml(pending.plan)}</pre><p>What the supervisor would change</p>${pending.diff.length ? diffHtml(pending.diff) : "<p>No changes needed.</p>"}<div class="actions">${button(pending.diff.length ? "Save the corrected answer" : "Confirm this answer", `data-review="${pending.diff.length ? "correct" : "accept"}" data-proposal="${esc(pending.proposal_id)}"`)}<button class="button" data-review="reject" data-proposal="${esc(pending.proposal_id)}">Discard this example</button></div><p>The reply already sent stays unchanged.</p></div>`;
  }
  html += storyStep(2, "reply → person → checked", "A person checks the answer.", checkBody, checkAction);
  const repeated = billing ? "The note’s words never repeat in this demo." : prepared ? "Checked answers are ready to reuse." : `${count} of ${floor} checks for this exact input.`;
  html += storyStep(3, billing ? "note A ≠ note B" : `${Math.min(count, floor)} / ${floor}`, repeated,
    billing ? "Billing depends on each note’s assessment words, not its form layout. Each different note starts over at one check." : `Cement needs ${floor} matching checks for each exact input. A different input still needs its own evidence.`,
    ready && !prepared && !pending ? button("Make this automatic", 'data-make-automatic="1"') : "", billing ? "story-boundary" : "");
  html += storyStep(4, billing ? "model → reply" : STATE.routed && prepared ? "checked → reply" : "person → switch",
    billing ? "Billing stays with the model." : STATE.routed && prepared ? "Matching work is now automatic." : prepared ? "You decide when to use it." : "Then you choose to make it automatic.",
    billing ? "Nothing repeats twice here, so there is no checked billing answer to reuse. Other parts of this task can be automatic." : STATE.routed && prepared ? "The next matching input uses the checked answer without a model call. Anything else goes back to the model." : "Preparing an answer does not switch the model off. A person must choose to use the checked answers.",
    prepared && !STATE.routed ? button("Use the checked answers", 'data-enable-automatic="1"') : "");
  if (!billing) html += `<p class="story-footnote">Why not billing? Every note has different assessment words. Nothing repeats, so the model keeps doing that work.</p>`;
  $("story").innerHTML = html;
}

async function makeAutomatic() {
  for (const action of ["compile", "verify", "promote"]) {
    if (!await lifecycle(action)) return;
  }
}

/* --- terminal: real `cement` invocations, condensed, verbatim one click away --- */

function commandHtml(row) {
  return `<details class="cmd"><summary>${esc(row.display.split(" ").slice(0, 3).join(" "))} · exit ${esc(row.rc)}</summary>
    <pre class="shell">$ ${esc(row.display)}</pre>
    ${(row.reading || []).map(pair => `<div class="row"><span>${esc(pair[0])}</span><span>${esc(pair[1])}</span></div>`).join("")}
    <details class="stdout"><summary>Exact argv + stdout · ${esc(row.bytes)} bytes · ${esc(row.ms)} ms</summary><pre>${esc(JSON.stringify(row.argv))}
${esc(row.stdout)}</pre></details></details>`;
}

function renderTerminal() {
  const rows = STATE.terminal || [];
  $("terminal-count").textContent = rows.length
    ? `${rows.length} command${rows.length === 1 ? "" : "s"} have run`
    : "";
  if (!$("commands-details").open) { $("terminal").innerHTML = ""; return; }
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
  $("categories").innerHTML = STATE.categories.filter(c => !DRAWER || c.operation === DRAWER)
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
  $("inbox-note").textContent = `${plural(STATE.pending.length, "answer")} in this task’s inbox. Users already have their replies.`;
  $("review").innerHTML = STATE.pending.map(p => `<div class="proposal"><div class="proposal-head">${esc(p.document_id)} · ${esc(p.scope_label)}</div>
    <details><summary>Compare the model answer and correction</summary><p>Model answer</p><pre>${jsonHtml(p.plan)}</pre>${p.preview_error ? `<p>${esc(p.preview_error)}</p>` : ""}<p>Supervisor changes</p>${diffHtml(p.diff)}</details>
    <div class="actions">${["accept", "correct", "reject"].map(d => `<button class="button small" data-review="${d}" data-proposal="${esc(p.proposal_id)}">${d}</button>`).join("")}</div></div>`).join("");
}

const row = (key, value) =>
  `<div class="row"><span class="k">${esc(key)}</span><span class="v">${esc(value)}</span></div>`;

/* --- one card per operation this task reaches ---
   A task that reaches an already-sealed operation lands on the SAME card, and the
   card names every task that calls it. That is what reuse looks like from here. */

function renderFunctions() {
  $("functions").innerHTML = STATE.functions.filter(fn => fn.operation === DRAWER).map(functionCard).join("");
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
  const title = `<h3>${esc(fn.label)} · ${fn.promoted ? "sealed" : "not sealed"}</h3><p>${esc(fn.decides)}</p><p class="fn-callers">Called by ${esc(fn.callers.join(", "))}.</p>`;
  if (!fn.promoted) return `<div class="fn-card">${title}${unpromotedBody(fn)}</div>`;
  const document_ = offlineDocument(fn);
  return `<div class="fn-card">${title}<p>${fn.entries} exact entries · ${fn.passed ? "verified" : "failed"}</p>
    <div class="actions"><button class="button primary" data-source="${esc(fn.operation)}">Read the function</button>
    ${document_ ? `<button class="button" data-offline="${esc(document_)}" data-operation="${esc(fn.operation)}">Test the bundle alone</button>` : ""}
    <a class="button" href="/api/bundle.json?operation=${encodeURIComponent(fn.operation)}" download>Download</a></div>
    ${STATE.offline && STATE.offline.operation === fn.operation ? offlineHtml(STATE.offline) : ""}
    <details><summary>Identity + verification</summary>${row("function_hash", fn.function_hash)}${row("receipt", fn.receipt_id)}${row("bundle", fn.bundle_bytes + " bytes")}${fn.checks.map(c => row(c.key, `${c.passed ? "passed" : "failed"} · ${c.detail}`)).join("")}${excludedHtml(fn)}</details></div>`;
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
    ${row("turns the model answered", stats.provider_calls)}
    ${row("operations answered by a function", stats.cement_answers)}
    ${row("operations sealed", STATE.promoted_operations.length)}
    ${row("mean model wait, simulated", wait)}
    ${row("median resolve, measured", resolve)}
    ${row("distinct model answers for one scope", distinct)}
    <div class="tiny dim" style="margin-top:9px">
      ${plural(stats.reviews, "review")} recorded.
      Every resolve runs the full six-check verification and caches nothing.
    </div>`;
}

function renderLog() {
  if (!$("events-details").open) { $("log").innerHTML = ""; return; }
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
  { name: "answered", steps: [() => send("q01")] },
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
    "[data-source],[data-select],[data-operation-open],[data-history]," +
    "[data-check-open],[data-make-automatic],[data-enable-automatic]");
  if (!target || BUSY) return;
  if (target.dataset.checkOpen) { CHECK_OPEN = !CHECK_OPEN; renderStory(); }
  else if (target.dataset.makeAutomatic) makeAutomatic();
  else if (target.dataset.enableAutomatic) route(true);
  else if (target.dataset.history) { HISTORY = !HISTORY; render(); } else if (target.dataset.operationOpen) {
    DRAWER = target.dataset.operationOpen;
    const task = STATE.scenarios.find(t => t.id === STATE.selected && t.operations.includes(DRAWER)) || STATE.scenarios.find(t => t.operations.includes(DRAWER));
    select(task.id);
  } else if (target.dataset.send) send(target.dataset.send);
  else if (target.dataset.select) select(target.dataset.select);
  else if (target.dataset.review) { CHECK_OPEN = false; review(target.dataset.proposal, target.dataset.review); }
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

$("commands-details").addEventListener("toggle", renderTerminal);
$("events-details").addEventListener("toggle", renderLog);
$("drawer-close").addEventListener("click", () => { DRAWER = ""; render(); });
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
  if (parameters.has("drawer")) { DRAWER = parameters.get("drawer"); $("operator-view").open = true; }
  if (parameters.has("reset")) await call("/api/reset", {});
  STATE = await (await fetch("/api/state")).json();
  if (parameters.has("source")) SOURCE_OPEN = parameters.get("source");
  render();
  /* The webfonts load after the first paint and change every line height, so the
     scroll offsets computed above land short. Render again once they are in. */
  if (document.fonts) await document.fonts.ready.then(render);
  if (parameters.has("scene")) await runStory(Number(parameters.get("scene")));
})();
