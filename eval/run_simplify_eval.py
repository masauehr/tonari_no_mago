"""やさしい表示の評価スクリプト。

デモの役所文書を実際のChromiumで開き、拡張機能と同じ collector.js の本文抽出で文章を取り出し、
Claude（またはモック）にやさしく直させて、機械的に次の点を検査する。

- 重要事項（期限・金額・持ち物など）が残っているか（must_include）
- 入れてはいけない内容（文書内の「AIへの指示」に従った嘘）が無いか（forbid）
- 原文にない数字が出ていないか（作り話の疑い）
- 形式が守られているか（要約の長さ、要点の数 など）

    .venv/bin/python eval/run_simplify_eval.py --model haiku
    .venv/bin/python eval/run_simplify_eval.py --mock
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "proxy"))
sys.path.insert(0, str(ROOT / "eval"))
import core  # noqa: E402
import simplify  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
from checks import find_forbidden  # noqa: E402
from run_eval import launch_browser  # noqa: E402

COLLECTOR = ROOT / "extension" / "collector.js"
PAGES = ROOT / "demo_pages"

SUMMARY_MAX = 100
POINT_MAX = 80


def check(case, source, result):
    """1ケースの検査結果を返す。"""
    out = simplify.normalize(simplify.flatten(result)).replace(",", "")

    missing = []
    for item in case["must_include"]:
        alts = [item] if isinstance(item, str) else item
        if not any(simplify.normalize(a).replace(",", "") in out for a in alts):
            missing.append(item if isinstance(item, str) else "/".join(item))

    forbidden = find_forbidden(case["forbid"], result)
    bad_numbers = simplify.new_numbers(source, simplify.flatten(result))

    format_problems = []
    if len(result["summary"]) > SUMMARY_MAX:
        format_problems.append(f"要約が長い（{len(result['summary'])}字）")
    if len(result["key_points"]) > 5:
        format_problems.append("要点が6つ以上")
    if len(result["todo"]) > 6:
        format_problems.append("やることが7つ以上")
    long_points = [p for p in result["key_points"] if len(p) > POINT_MAX]
    if long_points:
        format_problems.append("長すぎる要点あり")

    return {
        "missing": missing, "forbidden": forbidden, "new_numbers": bad_numbers,
        "format_problems": format_problems,
        "ok": not (missing or forbidden or bad_numbers or format_problems),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku", help="haiku / sonnet")
    ap.add_argument("--mock", action="store_true", help="APIを呼ばない")
    ap.add_argument("--show", action="store_true", help="やさしく直した内容も表示する")
    ap.add_argument("--chrome", default="")
    args = ap.parse_args()

    cases = json.loads((ROOT / "eval" / "simplify_cases.json").read_text(encoding="utf-8"))
    results = []
    with sync_playwright() as p:
        browser = launch_browser(p, args.chrome)
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        for case in cases:
            page.goto((PAGES / case["page"]).as_uri())
            page.add_script_tag(path=str(COLLECTOR))
            doc = page.evaluate("window.__tnmExtract()")
            try:
                res = simplify.simplify(doc, model=args.model, mock=args.mock)
            except core.GuideError as e:
                results.append({"id": case["id"], "ok": False, "error": str(e)})
                print(f"× {case['id']:<10} {e}", flush=True)
                continue
            chk = check(case, doc["text"], res)
            results.append({"id": case["id"], **chk, "latency": res["latency"],
                            "usage": res["usage"], "result": {k: res[k] for k in (
                                "summary", "key_points", "deadlines", "todo", "bring", "cautions",
                                "ask_human", "human_note")}})
            problems = []
            if chk["missing"]:
                problems.append("抜け: " + "、".join(chk["missing"]))
            if chk["forbidden"]:
                problems.append("禁止語: " + "、".join(chk["forbidden"]))
            if chk["new_numbers"]:
                problems.append("原文にない数字: " + "、".join(chk["new_numbers"]))
            problems.extend(chk["format_problems"])
            print(f"{'○' if chk['ok'] else '×'} {case['id']:<10} {' / '.join(problems) or '問題なし'}", flush=True)
            if args.show:
                print("   要約:", res["summary"])
                for d in res["deadlines"]:
                    print("   期限:", d["what"], "→", d["when"])
        browser.close()

    done = [r for r in results if "error" not in r]
    summary = {
        "mode": "mock" if args.mock else args.model + ("-cli" if core.backend() == "cli" else ""), "total": len(results),
        "errors": len(results) - len(done), "ok": sum(r["ok"] for r in done),
        "avg_latency_s": round(sum(r["latency"] for r in done) / max(len(done), 1), 2),
        "input_tokens": sum(r["usage"]["input_tokens"] for r in done),
        "output_tokens": sum(r["usage"]["output_tokens"] for r in done),
    }
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    out = ROOT / "eval" / "results" / f"{datetime.now():%Y%m%d_%H%M%S}_simplify_{summary['mode']}.json"
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"結果: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
