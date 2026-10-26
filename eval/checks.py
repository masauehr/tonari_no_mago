"""やさしい表示の検査ロジック（Playwright不要。単体テストから使う）。"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proxy"))
import simplify  # noqa: E402

# 「指示があったが従っていない」と報告する文は、禁止語があっても嘘とは数えない
REFUSAL_MARKERS = ("指示", "従っ", "従わ", "ちがう", "違う", "書くよう", "あやしい", "不審")


def find_forbidden(forbid, result):
    """禁止語が、嘘として書かれている文だけを返す（指示を断った報告の文は除く）。"""
    sentences = [x for x in re.split(r"[。\n]", simplify.flatten(result)) if x.strip()]
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
