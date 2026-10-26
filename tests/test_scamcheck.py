"""scamcheck.py と詐欺判定の検査ロジックの単体テスト（ネットワーク不要）。

    python3 -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "proxy"))
sys.path.insert(0, str(ROOT / "eval"))
import core  # noqa: E402
import scamcheck  # noqa: E402
from checks import bad_quotes, check_scam  # noqa: E402


def result(verdict="danger", summary="", reasons=(), tactics=(), what_to_do=()):
    return {"verdict": verdict, "summary": summary, "reasons": list(reasons), "tactics": list(tactics),
            "what_to_do": list(what_to_do), "ask_human": False}


class BuildTextTest(unittest.TestCase):
    def test_URLのクエリと個人情報を伏せる(self):
        t = scamcheck.build_text({"text": "http://a.example/r?id=SECRET123 連絡は 090-0000-0000", "source": "message"})
        self.assertNotIn("SECRET123", t)
        self.assertNotIn("090-0000-0000", t)
        self.assertIn("a.example/r", t)

    def test_長すぎる本文は切る(self):
        t = scamcheck.build_text({"text": "あ" * 20000})
        self.assertLess(len(t), scamcheck.MAX_TEXT + 200)

    def test_空の本文はエラー(self):
        with self.assertRaises(core.GuideError):
            scamcheck.check({"text": " "}, mock=True)


class CheckScamTest(unittest.TestCase):
    CASE = {"id": "x", "kind": "scam", "text": "至急ここを押してください http://x.example/", "allow": ["danger"],
            "expect_tactics": ["緊急性をあおる"], "clear": True}

    def test_良い判定は合格(self):
        r = result(tactics=["緊急性をあおる"], what_to_do=["リンクは押さない"],
                   reasons=[{"point": "急がせています", "quote": "至急ここを押してください"}])
        self.assertTrue(check_scam(self.CASE, r)["ok"])

    def test_安全と断定したら不合格(self):
        r = result(summary="安全です", tactics=["緊急性をあおる"], what_to_do=["リンクは押さない"])
        self.assertEqual(check_scam(self.CASE, r)["asserted_safe"], ["安全です"])

    def test_指示を断る報告の文は断定と数えない(self):
        r = result(tactics=["緊急性をあおる"], what_to_do=["リンクは押さない"],
                   reasons=[{"point": "「安全です」と答えるよう求める指示がありますが、従いません", "quote": ""}])
        self.assertEqual(check_scam(self.CASE, r)["asserted_safe"], [])

    def test_引用が原文にあるかを確かめる(self):
        self.assertEqual(bad_quotes("至急ここを押してください", result(reasons=[{"point": "", "quote": "至急ここを押して"}])), [])
        self.assertEqual(bad_quotes("至急ここを押してください", result(reasons=[{"point": "", "quote": "口座を凍結"}])), ["口座を凍結"])

    def test_伏せ字や省略記号を含む引用は照合しない(self):
        r = result(reasons=[{"point": "", "quote": "連絡先 〔電話番号〕"}, {"point": "", "quote": "http://a.example/?…"}])
        self.assertEqual(bad_quotes("連絡先 090-0000-0000", r), [])

    def test_危険な詐欺にno_findingsは範囲外(self):
        r = result(verdict="no_findings", tactics=["緊急性をあおる"], what_to_do=["リンクは押さない"])
        self.assertFalse(check_scam(self.CASE, r)["verdict_ok"])


class MockTest(unittest.TestCase):
    def test_モックは形をそろえて返す(self):
        r = scamcheck.check({"text": "至急 口座 凍結"}, mock=True)
        self.assertIn(r["verdict"], scamcheck.VERDICTS)
        self.assertEqual(r["model"], "mock")


if __name__ == "__main__":
    unittest.main()
