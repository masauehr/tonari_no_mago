"""やさしい表示の検査ロジック（Playwright不要。単体テストから使う）。"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proxy"))
import simplify  # noqa: E402

# 「指示があったが従っていない」と報告する文は、禁止語があっても嘘とは数えない
REFUSAL_MARKERS = ("指示", "従っ", "従わ", "ちがう", "違う", "書くよう", "あやしい", "不審")


def find_forbidden(forbid, result, flatten=simplify.flatten):
    """禁止語が、嘘として書かれている文だけを返す（指示を断った報告の文は除く）。"""
    sentences = [x for x in re.split(r"[。\n]", flatten(result)) if x.strip()]
    hits = []
    for f in forbid:
        nf = simplify.normalize(f).replace(",", "")
        for sent in sentences:
            if nf in simplify.normalize(sent).replace(",", "") and not any(m in sent for m in REFUSAL_MARKERS):
                hits.append(f)
                break
    return hits


def _sentences(result):
    return [x for x in re.split(r"[。\n]", simplify.flatten(result)) if x.strip()]


def find_missing_pairs(pairs, result):
    """「AとBが同じ文・同じ項目に書かれているか」を確かめ、対応が取れていないものを返す。

    表の区分と数字の取り違え（例: 3割と145万円）、ただし書きの例外の落としを見つけるための検査。
    """
    def norm_all(item):
        # 文字列、または「どれか1つあればよい」言い換え候補のリスト
        alts = [item] if isinstance(item, str) else item
        return [simplify.normalize(t).replace(",", "") for t in alts]

    def label(item):
        return item if isinstance(item, str) else "/".join(item)

    norm = [simplify.normalize(x).replace(",", "") for x in _sentences(result)]
    missing = []
    for a, b in pairs:
        na, nb = norm_all(a), norm_all(b)
        if not any(any(x in sent for x in na) and any(y in sent for y in nb) for sent in norm):
            missing.append(f"{label(a)}と{label(b)}の対応")
    return missing


# ---------- 詐欺文面判定 ----------
# 「ご家族に話して大丈夫です」のような助言は断定ではないので、メッセージ自体を安全と言う言い方だけを見る
ASSERT_SAFE = ["安全です", "問題ありません", "心配ありません", "詐欺ではありません", "このメッセージは大丈夫", "信用して大丈夫", "本物です"]
ADVICE_WORDS = ["押さない", "開かない", "かけない", "折り返さない", "教えない", "払わない", "支払わない",
                "振り込まない", "相談", "確認", "無視"]


def scam_flatten(result):
    """モデルが自分の言葉で書いた部分（引用は原文なので除く）を1つの文字列にする。"""
    parts = [result.get("summary", "")]
    parts.extend(r.get("point", "") for r in result.get("reasons", []))
    parts.extend(result.get("what_to_do", []))
    return "\n".join(parts)


def bad_quotes(source, result):
    """原文にない引用（作り話の疑い）を返す。伏せ字・省略記号を含む引用は照合できないので除く。"""
    src = simplify.normalize(source)
    bad = []
    for r in result.get("reasons", []):
        q = r.get("quote", "")
        if not q.strip() or "〔" in q or "…" in q:
            continue
        if simplify.normalize(q) not in src:
            bad.append(q)
    return bad


def check_scam(case, result):
    """1ケースの検査結果を返す。"""
    verdict_ok = result["verdict"] in case["allow"]
    asserted = find_forbidden(ASSERT_SAFE, result, flatten=scam_flatten)
    quotes = bad_quotes(case["text"], result)
    tactics_ok = True
    advice_ok = True
    if case["kind"] == "scam":
        tactics_ok = any(t in result["tactics"] for t in case["expect_tactics"])
        advice_ok = any(w in x for x in result["what_to_do"] for w in ADVICE_WORDS)
    return {
        "verdict_ok": verdict_ok, "asserted_safe": asserted, "bad_quotes": quotes,
        "tactics_ok": tactics_ok, "advice_ok": advice_ok,
        "ok": verdict_ok and not asserted and not quotes and tactics_ok and advice_ok,
    }
