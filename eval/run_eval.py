"""画面ガイドの正答率を測る評価スクリプト。

デモページを実際のChromiumで開き、拡張機能と同じ collector.js で要素を集め、
Claude（またはモック）に「次に押す場所」を答えさせて正解と比べる。

    .venv/bin/python eval/run_eval.py --model haiku
    .venv/bin/python eval/run_eval.py --model sonnet --shot
    .venv/bin/python eval/run_eval.py --mock          # APIなしで流れだけ確認
"""
import argparse
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "proxy"))
import core  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

COLLECTOR = ROOT / "extension" / "collector.js"
PAGES = ROOT / "demo_pages"


def launch_browser(p, chrome_path):
    """Playwright標準のChromiumを使う。無ければ手元の Chrome for Testing を探す。"""
    if chrome_path:
        return p.chromium.launch(executable_path=chrome_path)
    try:
        return p.chromium.launch()
    except Exception:
        cache = Path.home() / "Library/Caches/ms-playwright"
        found = sorted(cache.glob("chromium-*/chrome-mac-arm64/*.app/Contents/MacOS/*"))
        if not found:
            raise
        return p.chromium.launch(executable_path=str(found[-1]))


def apply_setup(page, setup):
    """入力済みの状態を再現する（ダミーデータのみ）。"""
    for step in setup:
        if "fill" in step:
            page.fill(step["fill"], step["value"])
        elif "check" in step:
            page.check(step["check"])
        elif "select" in step:
            page.select_option(step["select"], step["value"])


def run_one(page, sc, args):
    page.goto((PAGES / sc["page"]).as_uri())
    apply_setup(page, sc["setup"])
    page.add_script_tag(path=str(COLLECTOR))
    collected = page.evaluate("window.__tnmCollect()")

    shot = None
    if args.shot:
        raw = page.screenshot(type="jpeg", quality=60)
        shot = {"media_type": "image/jpeg", "data": base64.b64encode(raw).decode()}

    try:
        res = core.ask_guide(collected, goal=sc["goal"], model=args.model,
                             screenshot=shot, mock=args.mock)
    except core.GuideError as e:
        return {"id": sc["id"], "ok": False, "error": str(e)}

    ok = False
    chosen = ""
    if res["target_id"]:
        ok = any(page.evaluate(
            "([id, sel]) => { const el = document.querySelector(`[data-tnm-id=\"${id}\"]`);"
            " return !!el && el.matches(sel); }", [res["target_id"], sel]) for sel in sc["expected"])
        chosen = page.evaluate(
            "(id) => { const el = document.querySelector(`[data-tnm-id=\"${id}\"]`);"
            " return el ? (el.id || el.textContent.trim()).slice(0, 30) : ''; }", res["target_id"])
    caution_ok = (not sc["expect_caution"]) or bool(res["caution"].strip())
    return {
        "id": sc["id"], "ok": ok, "caution_ok": caution_ok, "chosen": chosen,
        "expected": sc["expected"], "reason": res["reason"], "confidence": res["confidence"],
        "caution": res["caution"], "ask_human": res["ask_human"],
        "latency": res["latency"], "usage": res["usage"], "n_elements": len(collected["elements"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku", help="haiku / sonnet")
    ap.add_argument("--shot", action="store_true", help="スクリーンショットも渡す")
    ap.add_argument("--mock", action="store_true", help="APIを呼ばない")
    ap.add_argument("--chrome", default="", help="使うChromeの実行ファイル（省略時はPlaywright標準、無ければ既存キャッシュ）")
    ap.add_argument("--only", default="", help="シナリオIDの前方一致（例: a_ ）")
    args = ap.parse_args()

    scenarios = json.loads((ROOT / "eval" / "scenarios.json").read_text(encoding="utf-8"))
    scenarios = [s for s in scenarios if s["id"].startswith(args.only)]

    results = []
    with sync_playwright() as p:
        browser = launch_browser(p, args.chrome)
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        for sc in scenarios:
            r = run_one(page, sc, args)
            results.append(r)
            mark = "○" if r.get("ok") else "×"
            detail = r.get("error") or f"選択={r['chosen']!r} 理由={r['reason']}"
            print(f"{mark} {r['id']:<16} {detail}", flush=True)
        browser.close()

    done = [r for r in results if "error" not in r]
    correct = sum(r["ok"] for r in done)
    cautions = [r for r, s in zip(results, scenarios) if s["expect_caution"] and "error" not in r]
    tin = sum(r["usage"]["input_tokens"] for r in done)
    tout = sum(r["usage"]["output_tokens"] for r in done)
    lat = sum(r["latency"] for r in done) / max(len(done), 1)
    mode = ("mock" if args.mock else args.model) + ("+shot" if args.shot else "")
    summary = {
        "mode": mode, "total": len(results), "errors": len(results) - len(done),
        "correct": correct, "accuracy": round(correct / max(len(done), 1), 3),
        "caution_ok": f"{sum(r['caution_ok'] for r in cautions)}/{len(cautions)}",
        "avg_latency_s": round(lat, 2), "input_tokens": tin, "output_tokens": tout,
    }
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))

    out = ROOT / "eval" / "results" / f"{datetime.now():%Y%m%d_%H%M%S}_{mode}.json"
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"結果: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
