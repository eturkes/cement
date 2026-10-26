"use strict";

/* Japanese UI (owner-ruled): `?lang=ja` or the header link. Translates the page's own words —
   chrome, narration, tour — in the rendered DOM, so app.js keeps English literals. Contents
   (forms, requests, replies, script rows) match no key and stay English; SKIP fences the
   technical layer + the Read view's code, which stay English by ruling. A key = the rendered
   English text, whitespace collapsed ⇒ an app.js wording change needs its key changed here,
   else that string shows English under ?lang=ja. */

const LANG = new URLSearchParams(location.search).get("lang") === "ja" ? "ja" : "en";

const TASKS = {
  "File it into the record": "カルテに登録する",
  "Send it to an outside specialist": "外部の専門医に送る",
  "Check the form before I accept it": "受け付ける前にフォームを確認する",
  "Where does this go?": "これはどこに回す？",
  "Code it for billing": "請求用にコードを付ける",
};

const JA = new Map(Object.entries({
  ...TASKS,
  "Concept demo": "コンセプトデモ",
  "Turn repeated AI work into functions you switch on.": "繰り返されるAIの作業を、スイッチでオンにできる関数に。",
  "Play the story": "ストーリーを再生",
  "Reset": "リセット",
  "Ask": "質問する",
  "AI replies": "AIが回答",
  "Learn": "学習する",
  "an AI finds repeats": "AIが繰り返しを発見",
  "Switch on": "オンにする",
  "you decide": "決めるのはあなた",
  "Leave the story": "ストーリーを終了",
  "What users see": "ユーザーに見える画面",
  "AI simulated": "AIはシミュレーション",
  "Behind the scenes": "舞台裏",
  "hidden from users · learning simulated": "ユーザーには見えない · 学習はシミュレーション",
  "Show technical details": "技術的な詳細を表示",
  "Hide technical details": "技術的な詳細を隠す",
  "Close": "閉じる",
  "The function": "関数",
  "Functions": "関数",
  "not learned yet": "未学習",
  "never repeats": "繰り返しなし",
  "Read": "読む",
  "answers written by the AI": "AIが書いた回答",
  "answers from a learned function": "学習済みの関数による回答",
  "Pick a task, then a request.": "タスクを選び、次にリクエストを選んでください。",
  "working…": "作業中…",
  "Used": "使用",
  "Cement’s learned function answered this part. The AI was not called for it.":
    "この部分には Cement の学習済み関数が回答しました。AIは呼び出されていません。",
  "Form": "フォーム",
  "Reply": "回答",
  "AI script": "AIのスクリプト",
  "Function": "関数",
  "How to read this form": "このフォームの読み方",
  "Patient identifiers": "患者の識別情報",
  "Required fields": "必須項目",
  "Team for this form": "このフォームの担当チーム",
  "Billing codes": "請求コード",
  "Learn from chats": "チャットから学習",
  "Pick a task, then a request — or play the story.":
    "タスクを選び、次にリクエストを選んでください。ストーリーの再生もできます。",
  "A learned function answered. No AI.": "学習した関数が回答しました。AIは使っていません。",
  "A learned function did part. The AI did the rest.": "一部は学習した関数が、残りはAIが回答しました。",
  "An ordinary chatbot answer. A function exists but is switched off.":
    "通常のチャットボットの回答です。関数はありますが、オフになっています。",
  "An ordinary chatbot answer. Nothing reusable is learned for this yet.":
    "通常のチャットボットの回答です。まだ再利用できるものは学習されていません。",
  "On: matching forms are answered by the function.": "オン: 一致するフォームには関数が回答します。",
  "Off: the AI answers again.": "オフ: 再びAIが回答します。",
  "Going back…": "戻っています…",
  "That step did not finish. Select Reset, then try again.":
    "この手順は完了しませんでした。リセットを選んでから、もう一度試してください。",
  /* tour */
  "A normal AI chat.": "普通のAIチャットです。",
  "What Cement does. Users never see it.": "Cement の処理です。ユーザーには見えません。",
  "An ordinary answer": "通常の回答",
  "No change from an ordinary chatbot answer. Cement has nothing reusable for this yet.":
    "通常のチャットボットの回答と変わりません。Cement にはまだ再利用できるものがありません。",
  "The AI’s script": "AIのスクリプト",
  "To answer, the AI wrote a small script that reads this form.":
    "回答するために、AIはこのフォームを読む小さなスクリプトを書きました。",
  "A slight change from the last script": "前回のスクリプトから少しだけ変化",
  "Another progress note. This time the Provider field was needed, so the script also reads that line.":
    "別の経過記録です。今回は Provider の項目が必要だったので、スクリプトはその行も読みます。",
  "An AI pass (simulated here) read the chats, found the repeat, and merged both scripts into one function.":
    "AIによる学習（ここではシミュレーション）がチャットを読み、繰り返しを見つけ、2つのスクリプトを1つの関数にまとめました。",
  "One function": "1つの関数",
  "Shared rows came from both scripts; Provider from the one that needed it. It covers both requests.":
    "shared の行は両方のスクリプトから、Provider の行はそれを必要としたスクリプトから来ています。この関数は両方のリクエストに対応します。",
  "Your one decision. Matching forms now skip the AI.": "あなたが決めるのはこれだけです。一致するフォームは、もうAIを通りません。",
  "A tool call": "ツール呼び出し",
  "Reuse": "再利用",
  "A new job reuses the function. Learn added a second one for its new part.":
    "新しい仕事がこの関数を再利用します。新しい部分のために、学習が2つ目の関数を追加しました。",
  "Two more jobs": "さらに2つの仕事",
  "Never repeats": "繰り返しなし",
  "Every note’s words differ, so Learn finds no repeat. Billing stays with the AI.":
    "記録ごとに文面が違うので、学習は繰り返しを見つけません。請求はAIが回答し続けます。",
  "Done": "完了",
  "For experts": "専門家向け",
  "Real commands and evidence.": "実際のコマンドと証拠です。",
  "Next": "次へ",
  "Back": "戻る",
}));

const onOff = (state) => (state === "on" ? "オン" : "オフ");
const PATTERNS = [
  [/^(Show|Hide) (\d+) earlier turns?$/, (verb, n) => `以前のやり取りを${n}件${verb === "Show" ? "表示" : "隠す"}`],
  [/^(\d+) kinds? of form$/, (n) => `${n}種類のフォーム`],
  [/^readable rendering · (\d+) kinds? of form · (on|off)$/, (n, state) => `読みやすく書き直した表示 · ${n}種類のフォーム · ${onOff(state)}`],
  [/^Function (\d+)$/, (n) => `関数 ${n}`],
  [/^Switch (on|off) (\S+)$/, (state, name) => `${name} を${onOff(state)}にする`],
  [/^(.+): pick a request\.$/, (task) => `${TASKS[task] || task}: リクエストを選んでください。`],
  [/^Learned from (\d+) answers?: (?:(\d+) new functions?|no new function)\. Requests seen once stay with the AI\.$/,
    (n, added) => `${n}件の回答から学習しました。${added ? `新しい関数は${added}件です` : "新しい関数はありません"}。一度だけのリクエストは、引き続きAIが回答します。`],
  [/^Another progress note, for (.+)\. The function answered\. No AI\.$/,
    (patient) => `${patient} さんの別の経過記録です。関数が回答しました。AIは使っていません。`],
  [/^Learned and switched on the same way\. AI (\d+), function (\d+)\.$/,
    (ai, fn) => `同じ手順で学習し、オンにしました。AI ${ai}件、関数 ${fn}件。`],
  [/^AI (\d+), function (\d+)\. Same replies\.$/, (ai, fn) => `AI ${ai}件、関数 ${fn}件。回答は同じです。`],
];

/* null = no translation for this text. */
function translated(text) {
  const key = String(text).replace(/\s+/g, " ").trim();
  if (!key) return null;
  if (JA.has(key)) return JA.get(key);
  for (const [pattern, to] of PATTERNS) {
    const match = key.match(pattern);
    if (match) return to(...match.slice(1));
  }
  return null;
}

/* Called by app.js where a string reaches a library that measures it (the tour popover). */
const tr = (text) => (LANG === "ja" && translated(text)) || text;

(function languageLink() {
  const params = new URLSearchParams(location.search);
  params.delete("reset"); // switching language keeps the demo's state
  params.delete("scene");
  if (LANG === "ja") params.delete("lang");
  else params.set("lang", "ja");
  const link = document.createElement("a");
  link.className = "button";
  const query = params.toString();
  link.href = location.pathname + (query ? `?${query}` : "");
  link.lang = LANG === "ja" ? "en" : "ja";
  link.textContent = LANG === "ja" ? "English" : "日本語";
  document.querySelector(".top .actions").append(link);
  if (LANG === "ja") document.querySelector(".brand").href = "/?lang=ja";
})();

if (LANG === "ja") {
  const SKIP = "#operator-view, #overlay, .under, .ocr, #fnview-body, pre, code, script, style";
  const ATTRS = ["title", "aria-label"];

  const text = (node) => {
    const value = translated(node.data);
    if (value === null) return;
    const [, lead, , tail] = node.data.match(/^(\s*)([\s\S]*?)(\s*)$/);
    node.data = lead + value + tail;
  };
  const attributes = (element) => {
    for (const name of ATTRS) {
      const value = element.getAttribute(name);
      const japanese = value && translated(value);
      if (japanese) element.setAttribute(name, japanese);
    }
  };
  const walk = (root) => {
    if (root.nodeType === Node.TEXT_NODE) {
      if (root.parentElement && !root.parentElement.closest(SKIP)) text(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE || root.closest(SKIP)) return;
    attributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => node.nodeType === Node.ELEMENT_NODE && node.matches(SKIP)
        ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === Node.TEXT_NODE) text(node);
      else attributes(node);
    }
  };

  document.documentElement.lang = "ja";
  document.title = "Cement · 繰り返されるAIの作業から学んだ関数";
  /* app.js re-renders on every state poll; each pass is translated before paint. Writes made
     while disconnected are not observed, so a translation never re-triggers itself. */
  const observer = new MutationObserver((records) => {
    observer.disconnect();
    for (const record of records) {
      if (record.type === "attributes") {
        if (!record.target.closest(SKIP)) attributes(record.target);
      } else if (record.type === "characterData") walk(record.target);
      else record.addedNodes.forEach(walk);
    }
    observe();
  });
  const observe = () => observer.observe(document.body, {
    childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS,
  });
  walk(document.body);
  observe();
}
