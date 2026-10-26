// 画面の操作対象を収集する（拡張機能と評価スクリプトで共用）
// 入力欄の「値」は収集しない。入力済みかどうか（真偽）だけを返す。
(() => {
  const SELECTOR = [
    'a[href]', 'button', 'input:not([type="hidden"])', 'select', 'textarea', 'summary',
    '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]', '[onclick]'
  ].join(',');
  const MAX_ELEMENTS = 80;
  const LABEL_LIMIT = 60;
  const CONTEXT_LIMIT = 50;
  const TEXT_LIMIT = 1500;

  const squash = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const clip = (s, n) => (s.length > n ? s.slice(0, n) + '…' : s);

  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const st = getComputedStyle(el);
    return st.visibility !== 'hidden' && st.display !== 'none' && st.opacity !== '0';
  };

  const inViewport = (el) => {
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
  };

  const labelOf = (el) => {
    const aria = el.getAttribute('aria-label');
    if (aria) return squash(aria);
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l) return squash(l.textContent);
    }
    const wrap = el.closest('label');
    if (wrap) return squash(wrap.textContent);
    const tag = el.tagName.toLowerCase();
    if (tag === 'input' && ['submit', 'button', 'reset'].includes(el.type)) return squash(el.value);
    const text = squash(el.innerText || el.textContent);
    if (text) return text;
    const img = el.querySelector('img[alt]');
    if (img) return squash(img.alt);
    return squash(el.placeholder || el.title || el.name || '');
  };

  const kindOf = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'リンク';
    if (tag === 'button') return 'ボタン';
    if (tag === 'select') return 'プルダウン';
    if (tag === 'textarea') return '入力欄';
    if (tag === 'input') {
      if (['submit', 'button', 'reset', 'image'].includes(el.type)) return 'ボタン';
      if (el.type === 'checkbox') return 'チェック';
      if (el.type === 'radio') return '選択肢';
      return '入力欄';
    }
    return el.getAttribute('role') === 'button' ? 'ボタン' : 'リンク';
  };

  // 入力済みか（値そのものは返さない）
  const filledOf = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'select') return el.selectedIndex > 0 && el.value !== '';
    if (tag === 'input' && el.type === 'checkbox') return el.checked;
    if (tag === 'input' && el.type === 'radio') {
      if (!el.name) return el.checked;
      return !!document.querySelector(`input[type="radio"][name="${CSS.escape(el.name)}"]:checked`);
    }
    return el.value !== '';
  };

  // 同じ文言のボタンが並ぶ表やカード用に、近くの文脈（行・カードの文字）を添える
  const contextOf = (el, label) => {
    const box = el.closest('tr, li, article, fieldset, .card');
    if (!box) return '';
    const t = squash(box.innerText);
    if (!t || t.length > 120) return '';
    const rest = squash(t.replace(label, ''));
    return rest ? clip(rest, CONTEXT_LIMIT) : '';
  };

  const areaOf = (el) => {
    const a = el.closest('header, nav, main, footer, aside');
    const map = { HEADER: 'ヘッダー', NAV: 'ナビ', MAIN: '本文', FOOTER: 'フッター', ASIDE: '脇' };
    return a ? map[a.tagName] : '';
  };

  const hrefPath = (el) => {
    try {
      const path = new URL(el.href, location.href).pathname;
      // file:// で開いたデモでは、ローカルのパス全体を送らずファイル名だけにする
      return location.protocol === 'file:' ? path.split('/').pop() : path;
    } catch (e) { return ''; }
  };

  const collect = () => {
    document.querySelectorAll('[data-tnm-id]').forEach((e) => e.removeAttribute('data-tnm-id'));
    let cands = [...document.querySelectorAll(SELECTOR)].filter((el) => {
      if (el.closest('#tnm-overlay-root')) return false;
      if (el.type === 'password') return false;
      return isVisible(el);
    });
    if (cands.length > MAX_ELEMENTS) {
      const vis = new Set(cands.filter(inViewport));
      const rest = cands.filter((e) => !vis.has(e));
      const keep = new Set([...vis, ...rest].slice(0, MAX_ELEMENTS));
      cands = cands.filter((e) => keep.has(e));
    }
    const elements = cands.map((el, i) => {
      const id = 'e' + (i + 1);
      el.setAttribute('data-tnm-id', id);
      const label = clip(labelOf(el), LABEL_LIMIT);
      const rec = { id, kind: kindOf(el), label };
      const ctx = contextOf(el, label);
      if (ctx) rec.context = ctx;
      const area = areaOf(el);
      if (area) rec.area = area;
      if (el.tagName.toLowerCase() === 'a') rec.href = hrefPath(el);
      if (['入力欄', 'プルダウン', 'チェック', '選択肢'].includes(rec.kind)) {
        rec.required = el.required;
        rec.filled = filledOf(el);
        if (rec.kind === '選択肢' && el.name) rec.group = el.name;
      }
      if (el.disabled) rec.disabled = true;
      if (!inViewport(el)) rec.offscreen = true;
      return rec;
    });
    const headings = [...document.querySelectorAll('h1, h2, h3')]
      .filter(isVisible).slice(0, 8).map((h) => clip(squash(h.innerText), 50));
    return {
      url: location.origin + location.pathname,
      title: document.title,
      headings,
      text: clip(squash(document.body.innerText), TEXT_LIMIT),
      elements,
      viewport: { w: innerWidth, h: innerHeight, scrollY: Math.round(scrollY) }
    };
  };

  window.__tnmCollect = collect;
})();
