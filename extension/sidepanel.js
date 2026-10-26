// サイドパネル：「困った」ボタン → 画面収集 → プロキシ → ハイライト
const PROXY = 'http://127.0.0.1:8787';

const $ = (id) => document.getElementById(id);
const history = [];

const activeTab = async () => {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab;
};

const show = (html) => { $('result').innerHTML = html; };
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// 画面の操作対象を集める（入力値は集めない）
const collect = async (tab) => {
  await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['collector.js', 'overlay.js'] });
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id }, func: () => window.__tnmCollect()
  });
  return result;
};

const captureShot = async (tab) => {
  const url = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'jpeg', quality: 60 });
  return { media_type: 'image/jpeg', data: url.split(',')[1] };
};

const askProxy = async (body) => {
  let res;
  try {
    res = await fetch(`${PROXY}/guide`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
  } catch (e) {
    throw new Error('中継プログラムに接続できません。ご家族に proxy/server.py の起動を確認してもらってください。');
  }
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || '案内を取得できませんでした。');
  return json;
};

const highlight = (tab, r) => chrome.scripting.executeScript({
  target: { tabId: tab.id },
  func: (id, reason, caution) => window.__tnmHighlight(id, reason, caution),
  args: [r.target_id, r.reason, r.caution]
});

$('help').addEventListener('click', async () => {
  const btn = $('help');
  btn.disabled = true;
  show('画面を見ています…');
  try {
    const tab = await activeTab();
    let page;
    try {
      page = await collect(tab);
    } catch (e) {
      throw new Error('このページでは使えません。ふつうのホームページで試してください。');
    }
    const body = {
      page,
      goal: $('goal').value.trim(),
      history,
      model: $('strong').checked ? 'sonnet' : 'haiku'
    };
    // 文字のないボタン（アイコン）があるときは、設定に関わらず画像も渡す
    if ($('shot').checked || page.unlabeled > 0) body.screenshot = await captureShot(tab);

    const r = await askProxy(body);
    if (r.target_id) {
      await highlight(tab, r);
      history.push(r.reason);
      show(`${esc(r.reason)}` +
        (r.caution ? `<div class="caution">⚠ ${esc(r.caution)}</div>` : '') +
        (r.confidence === 'low' ? '<div class="sub">自信がありません。念のため確認してください。</div>' : ''));
    } else {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => window.__tnmClear && window.__tnmClear() });
      show(esc(r.reason || '窓口やご家族に確認しましょう'));
    }
  } catch (e) {
    show(`<span class="error">${esc(e.message)}</span>`);
  } finally {
    btn.disabled = false;
  }
});

// やりたいことを変えたら、これまでの案内の履歴は捨てる
$('goal').addEventListener('input', () => { history.length = 0; });

// ---------- やさしく表示 ----------
const section = (title, inner, cls = '') => (inner ? `<h2>${esc(title)}</h2><div class="${cls}">${inner}</div>` : '');
const list = (tag, items) => (items.length ? `<${tag}>${items.map((x) => `<li>${esc(x)}</li>`).join('')}</${tag}>` : '');

const renderEasy = (r) => {
  const parts = [];
  if (r.ask_human) parts.push(`<div class="human">${esc(r.human_note || '窓口や専門家に相談しましょう')}</div>`);
  parts.push(`<div class="summary">${esc(r.summary)}</div>`);
  parts.push(section('いつまでに',
    r.deadlines.map((d) => `<div class="deadline">${esc(d.what)}：${esc(d.when)}</div>`).join('')));
  parts.push(section('やること', list('ol', r.todo)));
  parts.push(section('持っていくもの', list('ul', r.bring)));
  parts.push(section('大事なところ', list('ul', r.key_points)));
  parts.push(section('気をつけること', list('ul', r.cautions), 'cautions'));
  $('easy-body').innerHTML = parts.join('');
  $('easy').hidden = false;
};

// 読み上げ用の文章（見出しをつけて順に読む）
const speechText = (r) => [
  r.summary,
  r.deadlines.length ? 'いつまでに。' + r.deadlines.map((d) => `${d.what}は${d.when}`).join('。') : '',
  r.todo.length ? 'やること。' + r.todo.join('。') : '',
  r.bring.length ? '持っていくもの。' + r.bring.join('、') : '',
  r.cautions.length ? '気をつけること。' + r.cautions.join('。') : ''
].filter(Boolean).join('。\n');

let lastEasy = null;

$('easy-btn').addEventListener('click', async () => {
  const btn = $('easy-btn');
  btn.disabled = true;
  show('文章を読んでいます…');
  speechSynthesis.cancel();
  try {
    const tab = await activeTab();
    let doc;
    try {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['collector.js'] });
      [{ result: doc }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id }, func: () => window.__tnmExtract()
      });
    } catch (e) {
      throw new Error('このページでは使えません。ふつうのホームページで試してください。');
    }
    const res = await fetch(`${PROXY}/simplify`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: doc.title, text: doc.text, model: $('strong').checked ? 'sonnet' : 'haiku' })
    }).catch(() => { throw new Error('中継プログラムに接続できません。ご家族に proxy/server.py の起動を確認してもらってください。'); });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || 'やさしい表示を作れませんでした。');
    lastEasy = json;
    renderEasy(json);
    show(doc.truncated ? '<span class="sub">長い文章なので、最初の部分だけ読みました。</span>' : '');
  } catch (e) {
    show(`<span class="error">${esc(e.message)}</span>`);
  } finally {
    btn.disabled = false;
  }
});

// 文字サイズ（16〜40px）
let easySize = 20;
const applySize = () => $('easy').style.setProperty('--easy-size', easySize + 'px');
$('font-plus').addEventListener('click', () => { easySize = Math.min(40, easySize + 4); applySize(); });
$('font-minus').addEventListener('click', () => { easySize = Math.max(16, easySize - 4); applySize(); });

// 読み上げ（もう一度押すと止まる）
$('speak').addEventListener('click', () => {
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
  if (!lastEasy) return;
  const u = new SpeechSynthesisUtterance(speechText(lastEasy));
  u.lang = 'ja-JP';
  u.rate = 0.9;
  speechSynthesis.speak(u);
});

// ---------- あやしいか調べる ----------
const VERDICT_TEXT = {
  danger: ['あぶない可能性が高いです', ''],
  caution: ['注意してください', ''],
  no_findings: ['あやしい点は見つかりませんでした', 'ただし、安全とは言い切れません。迷ったら、下の相談先に聞いてください。']
};

const renderScam = (r) => {
  const [title, note] = VERDICT_TEXT[r.verdict] || VERDICT_TEXT.caution;
  const html = [`<div class="verdict ${esc(r.verdict)}">${esc(title)}${note ? `<small>${esc(note)}</small>` : ''}</div>`];
  if (r.summary) html.push(`<p>${esc(r.summary)}</p>`);
  if (r.ask_human) {
    html.push('<div class="urgent">すでにお金を払った、番号を教えた、入力してしまったときは、すぐに銀行や警察に連絡してください。</div>');
  }
  if (r.reasons.length) {
    html.push('<h3>そう思った理由</h3><ul>' + r.reasons.map((x) =>
      `<li>${esc(x.point)}${x.quote ? `<span class="quote">文中: 「${esc(x.quote)}」</span>` : ''}</li>`).join('') + '</ul>');
  }
  if (r.tactics.length) html.push('<h3>よくある手口</h3><div class="chips">' + r.tactics.map((t) => `<span>${esc(t)}</span>`).join('') + '</div>');
  if (r.what_to_do.length) html.push('<h3>どうすればよいか</h3><ul>' + r.what_to_do.map((x) => `<li>${esc(x)}</li>`).join('') + '</ul>');
  html.push('<div class="help">迷ったら、まずご家族に相談しましょう。<br>消費者ホットライン <b>188</b>／警察相談専用電話 <b>#9110</b></div>');
  $('scam-result').innerHTML = html.join('');
};

const runScam = async (button, getDoc) => {
  const buttons = [$('scam-msg-btn'), $('scam-page-btn')];
  buttons.forEach((b) => { b.disabled = true; });
  $('scam-result').textContent = '調べています…';
  try {
    const doc = await getDoc();
    const res = await fetch(`${PROXY}/scamcheck`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: doc.text, source: doc.source, model: $('strong').checked ? 'sonnet' : 'haiku' })
    }).catch(() => { throw new Error('中継プログラムに接続できません。ご家族に proxy/server.py の起動を確認してもらってください。'); });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || '調べられませんでした。');
    renderScam(json);
  } catch (e) {
    $('scam-result').innerHTML = `<span class="error">${esc(e.message)}</span>`;
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
  }
};

$('scam-msg-btn').addEventListener('click', () => runScam($('scam-msg-btn'), async () => {
  const text = $('scam-text').value.trim();
  if (!text) throw new Error('調べたいメッセージを、上の枠に貼り付けてください。');
  return { text, source: 'message' };
}));

$('scam-page-btn').addEventListener('click', () => runScam($('scam-page-btn'), async () => {
  const tab = await activeTab();
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['collector.js'] });
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id }, func: () => window.__tnmExtract()
    });
    return { text: `${result.title}\n${result.text}`, source: 'page' };
  } catch (e) {
    throw new Error('このページでは使えません。ふつうのホームページで試してください。');
  }
}));
