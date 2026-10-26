// 次に押す場所を1つだけ光らせて、理由を吹き出しで示す
(() => {
  const ROOT_ID = 'tnm-overlay-root';
  let raf = 0;

  const clear = () => {
    cancelAnimationFrame(raf);
    const root = document.getElementById(ROOT_ID);
    if (root) root.remove();
  };

  const highlight = (id, reason, caution) => {
    clear();
    const target = document.querySelector(`[data-tnm-id="${CSS.escape(id)}"]`);
    if (!target) return false;
    target.scrollIntoView({ block: 'center', behavior: 'smooth' });

    const root = document.createElement('div');
    root.id = ROOT_ID;
    root.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483647;';

    const frame = document.createElement('div');
    frame.style.cssText = [
      'position:fixed', 'border:5px solid #ff6a00', 'border-radius:10px',
      'box-shadow:0 0 0 9999px rgba(0,0,0,.35),0 0 18px 6px rgba(255,106,0,.8)',
      'pointer-events:none', 'transition:all .15s'
    ].join(';');

    const bubble = document.createElement('div');
    bubble.style.cssText = [
      'position:fixed', 'max-width:360px', 'padding:14px 16px', 'background:#fff', 'color:#222',
      'border:3px solid #ff6a00', 'border-radius:12px', 'font:bold 20px/1.5 sans-serif',
      'box-shadow:0 4px 14px rgba(0,0,0,.35)', 'pointer-events:auto'
    ].join(';');
    const msg = document.createElement('div');
    msg.textContent = reason;
    bubble.appendChild(msg);
    if (caution) {
      const c = document.createElement('div');
      c.textContent = '⚠ ' + caution;
      c.style.cssText = 'margin-top:8px;font-size:17px;color:#b00020;';
      bubble.appendChild(c);
    }
    const close = document.createElement('button');
    close.textContent = 'とじる';
    close.style.cssText = 'margin-top:10px;font-size:18px;padding:6px 18px;cursor:pointer;';
    close.addEventListener('click', clear);
    bubble.appendChild(close);

    root.append(frame, bubble);
    document.documentElement.appendChild(root);

    const place = () => {
      if (!document.getElementById(ROOT_ID)) return;
      const r = target.getBoundingClientRect();
      const pad = 6;
      frame.style.left = r.left - pad + 'px';
      frame.style.top = r.top - pad + 'px';
      frame.style.width = r.width + pad * 2 + 'px';
      frame.style.height = r.height + pad * 2 + 'px';
      const bh = bubble.offsetHeight;
      const below = r.bottom + 16 + bh < innerHeight;
      bubble.style.top = (below ? r.bottom + 16 : Math.max(8, r.top - 16 - bh)) + 'px';
      bubble.style.left = Math.min(Math.max(8, r.left), innerWidth - bubble.offsetWidth - 8) + 'px';
      raf = requestAnimationFrame(place);
    };
    place();
    return true;
  };

  window.__tnmHighlight = highlight;
  window.__tnmClear = clear;
})();
