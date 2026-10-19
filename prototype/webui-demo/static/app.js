"use strict";

/* Cement web UI demo. One render pass per state snapshot; the server holds all state. */

let STATE = null;
let BUSY = false;
let POLL = null;
/* Reset bumps RUN: story steps, responses + polls from an older run are dropped. */
let RUN = 0;
const INFLIGHT = new Set();
/* The operation whose source overlay is open, or "" for none. */
let SOURCE_OPEN = "";
let DRAWER = "";
let HISTORY = false;
/* Off = the plain explanation; on = per-message details, scanned text + operator view. */
let TECH = false;
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

const ACRONYMS = { mrn: "MRN", dob: "DOB", id: "ID" };
const humanKey = (key) => String(key).split("_")
  .map((word, index) => ACRONYMS[word] || (index ? word : word.replace(/^./, (c) => c.toUpperCase())))
  .join(" ");

/* A reply as a person reads it: one labelled row per field, lists as lines. */
function fieldsHtml(value) {
  if (Array.isArray(value)) {
    return value.map((item) => esc(item && typeof item === "object"
      ? Object.values(item).join(" \u2014 ") : item)).join("<br>");
  }
  if (value && typeof value === "object") {
    return `<dl class="fields">${Object.entries(value).map(([key, item]) =>
      `<dt>${esc(humanKey(key))}</dt><dd>${item && typeof item === "object"
        ? fieldsHtml(item) : item === "" || item === null ? "\u2014" : esc(item)}</dd>`).join("")}</dl>`;
  }
  return esc(value);
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
  const run = RUN;
  const abort = new AbortController();
  INFLIGHT.add(abort);
  BUSY = true;
  render();
  if (path !== "/api/reset") startPolling();
  try {
    const options = body === undefined
      ? { signal: abort.signal }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: abort.signal,
        };
    const response = await fetch(path, options);
    const payload = await response.json();
    if (run !== RUN) return null;
    if (!response.ok) {
      if (payload.state) STATE = payload.state;
      toast(payload.error || "request failed");
      return null;
    }
    STATE = payload;
    return payload;
  } catch (error) {
    if (error.name === "AbortError") return null;
    throw error;
  } finally {
    INFLIGHT.delete(abort);
    if (!INFLIGHT.size) {
      stopPolling();
      BUSY = false;
    }
    render();
  }
}

function startPolling() {
  if (POLL) return;
  POLL = setInterval(async () => {
    const run = RUN;
    const response = await fetch("/api/state");
    if (response.ok && run === RUN) {
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
const route = (enabled, operation) => call("/api/route", { enabled, operation });
const offline = (id, operation) =>
  call("/api/offline", { document_id: id, operation });

/* --- render --- */

function setTech(on) {
  TECH = on;
  document.body.classList.toggle("tech", on);
  $("tech").textContent = on ? "Hide technical details" : "Show technical details";
  $("tech").setAttribute("aria-pressed", String(on));
  $("operator-view").open = on;
}

function render() {
  if (!STATE) return;
  if (DRAWER && !STATE.selected_operations.includes(DRAWER)) DRAWER = STATE.selected_operations[0];
  renderChat();
  renderTray();
  renderAction();
  renderMechanism();
  renderFunctionsList();
  renderFnView();
  renderNarration();
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
    ? `${plural(STATE.stats.cement_answers, "operation")} answered without the model, each shown in the chat as a tool call.`
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
    : `<div class="empty">Pick a task, then a request.</div>`;
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
      : fieldsHtml(message.body);
  /* A promoted-function answer shows as a tool call, as a chat product shows any tool. */
  const tools = (message.tools || []).map((tool) => `<details class="tool-call">
    <summary><span class="tool-icon" aria-hidden="true">ƒ</span>Used <code>${esc(tool.operation)}</code><span class="tool-ms">${esc(tool.resolve_ms)} ms</span></summary>
    <p>Cement’s learned function answered this part. The AI was not called for it.</p></details>`).join("");
  return `<div class="msg assistant"><div class="avatar">AI</div>
    <div class="bubble">${tools}${body}</div></div>` + under(message);
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
  $("tray").innerHTML = `<div class="asks">
    ${task.requests.map(request => `<button class="ask-card" data-send="${esc(request.id)}" ${BUSY ? "disabled" : ""}>${esc(request.ask)}<small>${esc(request.document_id)} \u00b7 ${esc(documentOf(request.document_id).title || "")}</small></button>`).join("")}</div>`;
}

function renderTasks() {
  $("coverage-note").textContent = `${STATE.promoted_operations.length} of ${STATE.operations.length} jobs prepared`;
  $("coverage").innerHTML = STATE.operations.map(op => `<button class="operator-job button" data-operation-open="${esc(op.name)}">${esc(op.label)} · ${op.promoted ? "checked answer prepared" : op.blocked ? "not enough repeated evidence" : "still learning"}</button>`).join("");
  $("boundary-note").textContent = "Only the exact checked input matches. Other inputs return to the model.";
}

const cementable = () => STATE.selected_operations.filter((name) => operationOf(name).keyed_on !== "text");
const isLearned = (name) => STATE.promoted_operations.includes(name);
const isOn = (name) => STATE.routed_operations.includes(name);

function taskStage() {
  const turn = STATE.latest_turn;
  const ops = cementable();
  const learned = ops.length > 0 && ops.every(isLearned);
  const on = learned && ops.every(isOn);
  const step = !turn ? 1 : !learned ? 2 : 3;
  return { turn, learned, on, step };
}

/* The header strip doubles as this task's progress; the band holds its next action. */
function renderAction() {
  const s = taskStage();
  const billing = STATE.selected === "bill";
  document.querySelectorAll("#how li").forEach((li) => {
    const n = Number(li.dataset.step);
    li.classList.toggle("now", n === s.step);
    li.classList.toggle("done", n < s.step || (n === 3 && s.on));
    li.classList.toggle("blocked", billing && n === 3);
  });
  const button = (label, attr) => `<button class="button primary" ${attr} ${BUSY ? "disabled" : ""}>${label}</button>`;
  let html = "";
  if (STATE.pending.length) html += button("Learn from chats", 'data-learn="1"');
  if (s.learned && !s.on) html += button("Switch on", `data-switch="${esc(cementable().join(" "))}" data-on="1"`);
  $("band-actions").innerHTML = STORY_AT >= 0 ? "" : html;
  const st = STATE.stats;
  $("tally").innerHTML = `<span class="chip ai" title="answers written by the AI">AI ${st.provider_calls}</span><span class="chip fixed" title="answers from a learned function">Function ${st.cement_answers}</span>`;
}

/* One row per operation the selected task reaches: its learned function, its switch. */
function renderFunctionsList() {
  const rows = STATE.selected_operations.map((name) => {
    const fn = STATE.functions.find((row) => row.operation === name && row.promoted);
    if (!fn) {
      const never = operationOf(name).keyed_on === "text";
      return `<div class="fn-row muted"><span class="tool-icon" aria-hidden="true">ƒ</span><code>${esc(name)}</code>
        <span class="fn-note ${never ? "never" : ""}">${never ? "never repeats" : "not learned yet"}</span></div>`;
    }
    const on = isOn(name);
    return `<div class="fn-row"><span class="tool-icon" aria-hidden="true">ƒ</span><code>${esc(name)}</code>
      <span class="fn-note">${plural(fn.entries, "kind")} of form</span>
      <button class="button small" data-read="${esc(name)}">Read</button>
      <button class="switch ${on ? "on" : ""}" data-switch="${esc(name)}" data-on="${on ? "" : "1"}" aria-pressed="${on}" aria-label="${on ? "Switch off" : "Switch on"} ${esc(name)}" ${BUSY ? "disabled" : ""}><span class="knob"></span></button></div>`;
  });
  $("functions-list").innerHTML = `<div class="fn-list"><h3>Functions</h3>${rows.join("")}</div>`;
}

/* The function alone, as a person reads it before switching it on. */
let FN_OPEN = "";
function renderFnView() {
  const fn = STATE.functions.find((row) => row.operation === FN_OPEN && row.promoted && row.source);
  $("fnview").hidden = !fn;
  if (!fn) return;
  const lines = [`function ${fn.operation}(form):`];
  for (const entry of fn.source.entries) {
    lines.push(`  if form is a ${humanKey(entry.input.document_type || "form")}:`);
    const rows = METHOD[fn.operation][1](entry.output || {});
    const width = Math.max(...rows.map(([k]) => k.length));
    rows.forEach(([k, v]) => lines.push(`      ${k.padEnd(width)}  ←  ${v}`));
  }
  lines.push("  otherwise:", "      ask the AI");
  $("fnview-title").textContent = METHOD[fn.operation][0];
  $("fnview-sub").textContent = `${plural(fn.entries, "kind")} of form · ${isOn(fn.operation) ? "on" : "off"}`;
  $("fnview-body").textContent = lines.join("\n");
}

/* --- what happened to the latest request: document → method → reply ---
   The middle box is the point: Cement saves the METHOD for a kind of form, never one
   patient's values, so plain code can answer a new patient's form from it. */

const METHOD = {
  "document.extraction_plan": ["How to read this form", (o) => (o.fields || []).map((f) => [
    humanKey(f.name),
    f.locator && f.locator.kind === "section" ? `“${f.locator.heading}” section`
      : f.locator && f.locator.label ? `“${f.locator.label}:” line` : JSON.stringify(f.locator)])],
  "document.phi_locators": ["Patient identifiers", (o) =>
    (o.identifiers || []).map((r) => [humanKey(r.field), String(r.category).replace(/_/g, " ")])],
  "document.required_fields": ["Required fields", (o) => [
    ["Required", (o.required || []).map(humanKey).join(", ")],
    ["Optional", (o.optional || []).map(humanKey).join(", ") || "none"]]],
  "document.intake_queue": ["Team for this form", (o) => [
    ["Team", o.queue], ["Turnaround", `${o.sla_hours} hours`], ["Confirms receipt", o.acknowledge ? "yes" : "no"]]],
  "document.billing_codes": ["Billing codes", (o) =>
    (o.codes || []).map((c) => [c.code, c.description])],
};

function methodBox(part) {
  const fixed = part.source === "function";
  const rows = METHOD[part.operation][1](part.output || {})
    .map(([k, v]) => `<div class="method-row"><span>${esc(k)}</span><span>${esc(v)}</span></div>`).join("");
  return `<div class="method ${fixed ? "fixed" : "ai"}">
    <div class="method-head"><span class="chip ${fixed ? "fixed" : "ai"}">${fixed ? "Function" : "AI script"}</span></div>
    <h4>${esc(METHOD[part.operation][0])}</h4>${rows}</div>`;
}

function latestAnswer(turn) {
  return [...STATE.chat].reverse().find((m) => m.kind === "answer" && m.document_id === turn.document_id && m.scenario === STATE.selected);
}

function renderMechanism() {
  const turn = STATE.latest_turn;
  if (!turn) { $("mechanism").innerHTML = ""; return; }
  const doc = documentOf(turn.document_id);
  const excerpt = String(doc.text || "").split("\n").filter((line) => line.trim()).slice(0, 5).join("\n");
  const answer = latestAnswer(turn);
  const reply = !answer ? "…" : answer.error ? esc(answer.error)
    : answer.render === "text" ? esc(answer.body) : fieldsHtml(answer.body);
  $("mechanism").innerHTML = `<div class="mechanism">
    <div class="flow">
      <div class="flow-box"><span class="method-badge">Form</span><h4>${esc(doc.id)}.pdf</h4>
        <pre class="scan">${esc(excerpt)}</pre></div>
      <div class="flow-arrow" aria-hidden="true">→</div>
      <div class="flow-methods">${turn.parts.map(methodBox).join("")}</div>
      <div class="flow-arrow" aria-hidden="true">→</div>
      <div class="flow-box"><span class="method-badge">Reply</span><div class="reply">${reply}</div></div>
    </div></div>`;
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

/* --- narration: what just happened, after every action ---
   Free mode captions each click; story mode walks fixed steps with Next. */

let CAPTION = "Pick a task, then a request — or play the story.";
let STORY_AT = -1;

function renderNarration() {
  const story = STORY_AT >= 0;
  $("narration-text").textContent = CAPTION;
  $("narration-step").textContent = story ? `${STORY_AT + 1} / ${STORY.length}` : "";
  $("narration").classList.toggle("story", story);
  $("story-exit").hidden = !story;
}

function narrate(text) {
  CAPTION = text;
  renderNarration();
  renderAction();
}

const turnParts = () => (STATE.latest_turn ? STATE.latest_turn.parts : []);

function sentCaption() {
  const turn = STATE.latest_turn;
  if (!turn) return CAPTION;
  const parts = turnParts();
  const fixed = parts.filter((p) => p.source === "function").length;
  if (fixed === parts.length) return "A tool call to Cement answered. No AI.";
  if (fixed) return "A tool call to Cement did part. The AI did the rest.";
  return taskStage().learned && !taskStage().on
    ? "An ordinary chatbot answer. A function exists but is switched off."
    : "An ordinary chatbot answer. Cement has nothing reusable for this yet.";
}

async function learnNow() {
  const read = STATE.pending.length;
  const before = STATE.promoted_operations.length;
  await call("/api/learn", {});
  const added = STATE.promoted_operations.length - before;
  return `Learned from ${plural(read, "answer")}: ${added ? `${plural(added, "new function")}` : "no new function"}. Requests seen once stay with the AI.`;
}

async function switchTo(names, on) {
  for (const name of names) await route(on, name);
  return on ? "On: matching forms are answered by the function." : "Off: the AI answers again.";
}

const learnAll = async () => { await learnNow(); };
const switchAllOn = async () => { await switchTo(STATE.promoted_operations, true); };
const firstNote = () => (turnParts().find((p) => p.note) || {}).note || "made a mistake";
const patientOf = () => (STATE.latest_turn ? documentOf(STATE.latest_turn.document_id).patient : "");

/* Each step runs once, then shows its beats: a spotlight (driver.js) on one element with
   a short title + line, so the audience knows where to look. Next lives in the popover. */
const lastBubble = () => [...document.querySelectorAll("#chat .msg.assistant .bubble")].pop();
const lastTool = () => [...document.querySelectorAll("#chat .tool-call")].pop();
const STORY = [
  { beats: [
    { el: "#how", title: "Three steps", text: () => "Ask, learn, switch on.", side: "bottom" },
    { el: "#side-user", title: "What users see", text: () => "A normal AI chat.", side: "right" },
    { el: "#side-hidden", title: "Behind the scenes", text: () => "What Cement does. Users never see it.", side: "left" } ] },
  { run: async () => { await select("file"); await send("q01"); }, beats: [
    { el: lastBubble, title: "An ordinary answer", text: () => "No change from an ordinary chatbot answer. Cement has nothing reusable for this yet.", side: "right" },
    { el: "#mechanism .method", title: "The AI’s script", text: () => `To answer, the AI wrote a small script for this form. This one ${firstNote()}.`, side: "bottom" } ] },
  { run: () => send("q02"), beats: [
    { el: "#mechanism .method", title: "The same job again", text: () => "Another progress note. The AI wrote a slightly different script.", side: "bottom" } ] },
  { run: learnAll, beats: [
    { el: "#functions-list", title: "Learn", text: () => "An AI pass read the chats, found the repeat, and merged the scripts into one function.", side: "top" },
    { el: "#fnview .overlay-card", fn: "document.extraction_plan", title: "The function", text: () => "Readable. One branch per kind of form. Anything else goes to the AI.", side: "left" } ] },
  { run: () => switchTo(["document.extraction_plan"], true), beats: [
    { el: "#functions-list .switch", title: "Switch on", text: () => "Your one decision. Matching forms now skip the AI.", side: "top" } ] },
  { run: () => send("q03"), beats: [
    { el: lastTool, title: "A tool call", text: () => `Another progress note, for ${patientOf()}. The function answered. No AI.`, side: "right" } ] },
  { run: async () => { await send("q05"); await send("q06"); await learnAll(); await switchAllOn(); }, beats: [
    { el: "#functions-list", title: "Reuse", text: () => "A new job reuses the function. Learn added a second one for its new part.", side: "top" } ] },
  { run: async () => { for (const id of ["q08", "q09", "q10", "q11"]) await send(id); await learnAll(); await switchAllOn(); }, beats: [
    { el: "#tally", title: "Two more jobs", text: () => `Learned and switched on the same way. AI ${STATE.stats.provider_calls}, function ${STATE.stats.cement_answers}.`, side: "bottom" } ] },
  { run: async () => { await send("q12"); await learnAll(); }, beats: [
    { el: "#functions-list", title: "Never repeats", text: () => "Every note’s words differ, so Learn finds no repeat. Billing stays with the AI.", side: "top" } ] },
  { beats: [
    { el: "#tally", title: "Done", text: () => `AI ${STATE.stats.provider_calls}, function ${STATE.stats.cement_answers}. Same replies.`, side: "bottom" },
    { el: "#tech", title: "For experts", text: () => "Real commands and evidence.", side: "top" } ] },
];

let TOUR = null;
let BEAT = 0;

function tour() {
  if (!TOUR) {
    TOUR = window.driver.js.driver({
      animate: !matchMedia("(prefers-reduced-motion: reduce)").matches,
      overlayOpacity: 0.55,
      stagePadding: 8,
      stageRadius: 10,
      overlayClickBehavior: "none",
      popoverClass: "cement-pop",
      onNextClick: nextBeat,
      onCloseClick: leaveStory,
    });
  }
  return TOUR;
}

function showBeat() {
  const beats = STORY[STORY_AT].beats;
  const beat = beats[BEAT];
  FN_OPEN = beat.fn || "";
  renderFnView();
  const element = typeof beat.el === "function" ? beat.el() : document.querySelector(beat.el);
  const last = STORY_AT === STORY.length - 1 && BEAT === beats.length - 1;
  narrate(beat.text());
  tour().highlight({
    element: element || "#side-hidden",
    popover: {
      title: beat.title,
      description: beat.text(),
      side: beat.side,
      /* highlight() mode shows only the buttons a step lists itself. */
      showButtons: ["next", "close"],
      showProgress: true,
      progressText: `${STORY_AT + 1} / ${STORY.length}`,
      nextBtnText: last ? "Done" : "Next",
    },
  });
}

function nextBeat() {
  if (BUSY) return;
  if (BEAT < STORY[STORY_AT].beats.length - 1) { BEAT += 1; showBeat(); }
  else if (STORY_AT < STORY.length - 1) advanceStory(STORY_AT + 1);
  else leaveStory();
}

async function advanceStory(index) {
  const run = RUN;
  const step = STORY[index];
  STORY_AT = index;
  BEAT = 0;
  if (TOUR && TOUR.isActive()) TOUR.destroy();
  narrate("…");
  if (step.run) await step.run();
  if (run !== RUN) return;
  showBeat();
  document.body.dataset.sceneDone = String(index);
}

async function playStory(upTo = 0) {
  RUN += 1;
  await call("/api/reset", {});
  for (let index = 0; index <= upTo && index < STORY.length; index += 1) {
    await advanceStory(index);
  }
}

function leaveStory() {
  STORY_AT = -1;
  FN_OPEN = "";
  renderFnView();
  if (TOUR && TOUR.isActive()) TOUR.destroy();
  renderNarration();
  renderAction();
}

/* --- wiring --- */

document.addEventListener("click", (event) => {
  const target = event.target.closest(
    "[data-send],[data-review],[data-action],[data-offline],[data-revoke]," +
    "[data-source],[data-select],[data-operation-open],[data-history]," +
    "[data-learn],[data-read],[data-switch]");
  if (!target || BUSY) return;
  if (!target.dataset.history && STORY_AT >= 0) leaveStory();
  if (target.dataset.learn) {
    learnNow().then(narrate);
  } else if (target.dataset.read) {
    FN_OPEN = target.dataset.read;
    renderFnView();
  } else if (target.dataset.switch) {
    switchTo(target.dataset.switch.split(" "), Boolean(target.dataset.on)).then(narrate);
  } else if (target.dataset.history) { HISTORY = !HISTORY; render(); } else if (target.dataset.operationOpen) {
    DRAWER = target.dataset.operationOpen;
    const task = STATE.scenarios.find(t => t.id === STATE.selected && t.operations.includes(DRAWER)) || STATE.scenarios.find(t => t.operations.includes(DRAWER));
    select(task.id);
  } else if (target.dataset.send) send(target.dataset.send).then(() => narrate(sentCaption()));
  else if (target.dataset.select) {
    select(target.dataset.select).then(() => narrate(`${scenarioOf(STATE.selected).title}: pick a request.`));
  } else if (target.dataset.review) {
    review(target.dataset.proposal, target.dataset.review);
  }
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
$("tech").addEventListener("click", () => setTech(!TECH));
$("drawer-close").addEventListener("click", () => { DRAWER = ""; render(); });
$("overlay-close").addEventListener("click", () => setSource(""));
$("fnview-close").addEventListener("click", () => { FN_OPEN = ""; renderFnView(); });
$("overlay").addEventListener("click", (event) => {
  if (event.target === $("overlay")) setSource("");
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && SOURCE_OPEN) setSource("");
  if (event.key === "Escape" && FN_OPEN && STORY_AT < 0) { FN_OPEN = ""; renderFnView(); }
});

$("play").addEventListener("click", () => playStory(0));
$("story-exit").addEventListener("click", leaveStory);
$("reset").addEventListener("click", async () => {
  RUN += 1;
  for (const abort of INFLIGHT) abort.abort();
  stopPolling();
  delete document.body.dataset.sceneDone;
  SOURCE_OPEN = "";
  DRAWER = "";
  HISTORY = false;
  leaveStory();
  CAPTION = "Pick a task, then a request — or play the story.";
  await call("/api/reset", {});
});

(async function start() {
  const parameters = new URLSearchParams(location.search);
  if (parameters.has("expand")) document.body.classList.add("expanded");
  if (["open", "drawer", "source", "tech"].some(key => parameters.has(key))) setTech(true);
  if (parameters.has("drawer")) DRAWER = parameters.get("drawer");
  if (parameters.has("reset")) await call("/api/reset", {});
  STATE = await (await fetch("/api/state")).json();
  if (parameters.has("source")) SOURCE_OPEN = parameters.get("source");
  render();
  /* The webfonts load after the first paint and change every line height, so the
     scroll offsets computed above land short. Render again once they are in. */
  if (document.fonts) await document.fonts.ready.then(render);
  if (parameters.has("scene")) await playStory(Number(parameters.get("scene")));
})();
