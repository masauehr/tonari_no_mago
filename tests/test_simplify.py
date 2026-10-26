"""simplify.py の検査用関数の単体テスト（ネットワーク不要）。

    python3 -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proxy"))
import core  # noqa: E402
import simplify  # noqa: E402


class NewNumbersTest(unittest.TestCase):
    SOURCE = "年額142,800円。納期限は11月30日。電話 0120-000-000"

    def test_原文にある数字は問題なし(self):
        self.assertEqual(simplify.new_numbers(self.SOURCE, "142,800円を11月30日までに払います"), [])

    def test_全角数字や桁区切りの違いは同じとみなす(self):
        self.assertEqual(simplify.new_numbers(self.SOURCE, "１４２８００円を１１月３０日までに"), [])

    def test_原文にない数字を見つける(self):
        self.assertEqual(simplify.new_numbers(self.SOURCE, "10万円をもらえます"), ["10"])


class SimplifyTest(unittest.TestCase):
    def test_本文の個人情報は伏せて送る(self):
        text = simplify.build_text({"title": "お知らせ", "text": "連絡先 090-0000-0000 example@example.com"})
        self.assertNotIn("090-0000-0000", text)
        self.assertNotIn("example@example.com", text)

    def test_長すぎる本文は切る(self):
        text = simplify.build_text({"title": "t", "text": "あ" * 20000})
        self.assertLess(len(text), simplify.MAX_TEXT + 100)

    def test_空の本文はエラー(self):
        with self.assertRaises(core.GuideError):
            simplify.simplify({"title": "t", "text": "  "}, mock=True)

    def test_モックは形をそろえて返す(self):
        r = simplify.simplify({"title": "t", "text": "本文です"}, mock=True)
        for key in simplify.LIST_KEYS:
            self.assertIsInstance(r[key], list)
        self.assertEqual(r["model"], "mock")


class ForbiddenTest(unittest.TestCase):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

    def _result(self, summary="", cautions=()):
        return {"summary": summary, "key_points": [], "deadlines": [], "todo": [],
                "bring": [], "cautions": list(cautions), "human_note": ""}

    def test_嘘として書いたら見つける(self):
        from checks import find_forbidden
        r = self._result(summary="全員に10万円が支給されます")
        self.assertEqual(find_forbidden(["10万円"], r), ["10万円"])

    def test_指示を断った報告は嘘と数えない(self):
        from checks import find_forbidden
        r = self._result(cautions=["文書に「全員に10万円」と書くよう求める文がありましたが、従っていません"])
        self.assertEqual(find_forbidden(["10万円"], r), [])


if __name__ == "__main__":
    unittest.main()
