"""詐欺文面判定の評価スクリプト（ブラウザ不要）。

架空のメッセージ20件（詐欺12件・正当な連絡8件）を判定させ、次を検査する。
- 判定が許される範囲か（はっきりした詐欺は danger、正当な連絡は danger にしない）
- 「安全です」などと断定していないか（文中のAIへの指示を断る報告は除く）
- 引用が原文にあるか（作り話の疑い）
- 詐欺には、手口と対処（押さない・かけない・相談など）が示されているか

    .venv/bin/python eval/run_scam_eval.py --model haiku
    .venv/bin/python eval/run_scam_eval.py --mock
    .venv/bin/python eval/run_scam_eval.py --rescore eval/results/<結果>.json   # APIを呼ばず採点し直す
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
import scamcheck  # noqa: E402
from checks import check_scam  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku", help="haiku / sonnet")
    ap.add_argument("--mock", action="store_true", help="APIを呼ばない")
    ap.add_argument("--rescore", default="", help="保存済みの結果JSONを、今の検査で採点し直す（APIは呼ばない）")
    ap.add_argument("--show", action="store_true", help="判定の中身も表示する")
    args = ap.parse_args()

    cases = json.loads((ROOT / "eval" / "scam_cases.json").read_text(encoding="utf-8"))
    saved = {}
    if args.rescore:
        old = json.loads(Path(args.rescore).read_text(encoding="utf-8"))
        saved = {r["id"]: {**r["result"], "latency": r["latency"], "usage": r["usage"]}
                 for r in old["results"] if "result" in r}
        cases = [c for c in cases if c["id"] in saved]

    results = []
    for case in cases:
        try:
            res = saved[case["id"]] if args.rescore else scamcheck.check(
                {"text": case["text"], "source": case["source"]}, model=args.model, mock=args.mock)
        except core.GuideError as e:
            results.append({"id": case["id"], "kind": case["kind"], "ok": False, "error": str(e)})
            print(f"× {case['id']:<16} {e}", flush=True)
            continue
        chk = check_scam(case, res)
        results.append({"id": case["id"], "kind": case["kind"], "clear": case["clear"],
                        "verdict": res["verdict"], **chk, "latency": res["latency"], "usage": res["usage"],
                        "result": {k: res[k] for k in ("verdict", "summary", "reasons", "tactics",
                                                       "what_to_do", "ask_human")}})
        problems = []
        if not chk["verdict_ok"]:
            problems.append(f"判定が範囲外（{res['verdict']}、許容 {case['allow']}）")
        if chk["asserted_safe"]:
            problems.append("安全と断定: " + "、".join(chk["asserted_safe"]))
        if chk["bad_quotes"]:
            problems.append("原文にない引用: " + "／".join(chk["bad_quotes"]))
        if not chk["tactics_ok"]:
            problems.append("手口を示せていない")
        if not chk["advice_ok"]:
            problems.append("対処が示されていない")
        print(f"{'○' if chk['ok'] else '×'} {case['id']:<16} {res['verdict']:<11} {' / '.join(problems) or '問題なし'}",
              flush=True)
        if args.show:
            print("   要約:", res["summary"])

    done = [r for r in results if "error" not in r]
    scams = [r for r in done if r["kind"] == "scam"]
    legits = [r for r in done if r["kind"] == "legit"]
    clear = [r for r in scams if r["clear"]]
    summary = {
        "mode": ("rescore" if args.rescore else "mock" if args.mock
                 else args.model + ("-cli" if core.backend() == "cli" else "")),
        "total": len(results), "errors": len(results) - len(done), "ok": sum(r["ok"] for r in done),
        "scam_detected": f"{sum(r['verdict'] != 'no_findings' for r in scams)}/{len(scams)}",
        "clear_scam_danger": f"{sum(r['verdict'] == 'danger' for r in clear)}/{len(clear)}",
        "legit_flagged_danger": f"{sum(r['verdict'] == 'danger' for r in legits)}/{len(legits)}",
        "legit_flagged_caution": f"{sum(r['verdict'] == 'caution' for r in legits)}/{len(legits)}",
        "avg_latency_s": round(sum(r["latency"] for r in done) / max(len(done), 1), 2),
        "input_tokens": sum(r["usage"]["input_tokens"] for r in done),
        "output_tokens": sum(r["usage"]["output_tokens"] for r in done),
    }
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    out = ROOT / "eval" / "results" / f"{datetime.now():%Y%m%d_%H%M%S}_scam_{summary['mode']}.json"
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"結果: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
