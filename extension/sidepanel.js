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
