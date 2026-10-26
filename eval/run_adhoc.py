"""実在の文書・メッセージで試すためのツール（正解データなし。人が結果を見て判断する）。

文章を UTF-8 のテキストファイルにして `samples/` に置く（samples/ は Git の管理対象外）。
機械的に確かめられる点だけを報告する。「正しいか」は、結果を読んで判断する。

    python3 eval/run_adhoc.py simplify samples/*.txt          # やさしい表示
    python3 eval/run_adhoc.py scam samples/*.txt              # 詐欺文面判定
    TNM_BACKEND=cli python3 eval/run_adhoc.py simplify samples/*.txt --model sonnet

注意（個人情報）:
- 氏名・住所・電話・番号・口座などが載った実物は使わない。伏せ字にしてから置く。
  送信前に電話・メール・郵便番号・12桁番号は自動で伏せるが、完全ではない。
- 結果は eval/results/adhoc_*.json に保存される（Git の管理対象外）。
- 公開されている文書（役所・企業の公開ページ）を保存して使うのが安全。
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
import simplify  # noqa: E402
from checks import (ASSERT_SAFE, bad_quotes, find_forbidden, missing_facts, scam_flatten)  # noqa: E402

NOTICE = ("※ 実在の文書を使うときは、個人情報（氏名・住所・電話・番号・口座）を含めないでください。"
          "結果は Git に入りません。")


def read_doc(path):
    text = Path(path).read_text(encoding="utf-8")
    return {"title": Path(path).stem, "text": text}


def run_simplify(path, model):
    doc = read_doc(path)
    res = simplify.simplify(doc, model=model)
    out_text = simplify.flatten(res)
    flags = {
        "原文にない数字": simplify.new_numbers(doc["text"], out_text),
        "原文にあるのに出力にない金額・日付": missing_facts(doc["text"], out_text),
        "形式": [m for m, bad in (
            (f"要約が長い（{len(res['summary'])}字）", len(res["summary"]) > 100),
            ("要点が6つ以上", len(res["key_points"]) > 5),
            ("やることが7つ以上", len(res["todo"]) > 6)) if bad],
    }
    print(f"  要約: {res['summary']}")
    for d in res["deadlines"]:
        print(f"  期限: {d['what']} → {d['when']}")
    for key, label in (("todo", "やること"), ("bring", "持ち物"), ("key_points", "要点"), ("cautions", "注意")):
        for x in res[key]:
            print(f"  {label}: {x}")
    if res["ask_human"]:
        print(f"  窓口へ: {res['human_note']}")
    return res, flags


def run_scam(path, model):
    doc = read_doc(path)
    source = "page" if doc["text"].startswith("# source: page") else "message"
    res = scamcheck.check({"text": doc["text"], "source": source}, model=model)
    flags = {
        "安全と断定": find_forbidden(ASSERT_SAFE, res, flatten=scam_flatten),
        "原文にない引用": bad_quotes(doc["text"], res),
    }
    print(f"  判定: {res['verdict']}　{res['summary']}")
    for r in res["reasons"]:
        print(f"  理由: {r['point']}" + (f"　〔文中: {r['quote']}〕" if r["quote"] else ""))
    print(f"  手口: {'、'.join(res['tactics']) or '（なし）'}")
    for x in res["what_to_do"]:
        print(f"  対処: {x}")
    return res, flags


def main():
    ap = argparse.ArgumentParser(description="実在の文書・メッセージで試す（正解データなし）")
    ap.add_argument("kind", choices=["simplify", "scam"])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--model", default="haiku", help="haiku / sonnet")
    args = ap.parse_args()

    print(NOTICE + "\n")
    runner = run_simplify if args.kind == "simplify" else run_scam
    records = []
    for path in args.files:
        print(f"■ {path}")
        try:
            res, flags = runner(path, args.model)
        except core.GuideError as e:
            print(f"  エラー: {e}\n")
            records.append({"file": path, "error": str(e)})
            continue
        for name, items in flags.items():
            if items:
                print(f"  ⚑ {name}: {'、'.join(items)}")
        print(f"  （{res['latency']}秒・入力{res['usage']['input_tokens']}／出力{res['usage']['output_tokens']}トークン）\n")
        records.append({"file": path, "flags": flags, "result": res})

    out = ROOT / "eval" / "results" / f"adhoc_{datetime.now():%Y%m%d_%H%M%S}_{args.kind}.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"結果: {out.relative_to(ROOT)}（Git 管理外）")


if __name__ == "__main__":
    main()
