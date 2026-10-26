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


class MissingFactsTest(unittest.TestCase):
    SOURCE = "年額142,800円。納期限は11月30日。第1期から第10期。受付は午前8時30分まで。"

    def test_落ちた金額と日付を見つける(self):
        from checks import missing_facts
        got = missing_facts(self.SOURCE, "年額142,800円を払います")
        self.assertIn("11月30日", got)
        self.assertNotIn("142800円", got)

    def test_全角や桁区切りの違いは同じとみなす(self):
        from checks import missing_facts
        self.assertEqual(missing_facts("納付額は14,280円です", "１４２８０円を納めます"), [])

    def test_数字つきの言葉がなければ空(self):
        from checks import source_facts
        self.assertEqual(source_facts("お知らせです。窓口にお越しください。"), [])


class PairsTest(unittest.TestCase):
    def _result(self, points):
        return {"summary": "", "key_points": list(points), "deadlines": [], "todo": [],
                "bring": [], "cautions": [], "human_note": ""}

    def test_同じ文に両方あれば対応が取れている(self):
        from checks import find_missing_pairs
        r = self._result(["現役並み所得者（課税所得145万円以上）は3割です"])
        self.assertEqual(find_missing_pairs([("3割", "145万円")], r), [])

    def test_別の項目に分かれていたら対応なし(self):
        from checks import find_missing_pairs
        r = self._result(["3割の方がいます", "145万円という基準があります"])
        self.assertEqual(find_missing_pairs([("3割", "145万円")], r), ["3割と145万円の対応"])

    def test_言い換え候補のどれかがあればよい(self):
        from checks import find_missing_pairs
        r = self._result(["二重に申し込むと無効になります"])
        self.assertEqual(find_missing_pairs([("無効", ["重複", "二重"])], r), [])
        self.assertEqual(find_missing_pairs([("無効", ["重複"])], r), ["無効と重複の対応"])

    def test_桁区切りや全角の違いは同じとみなす(self):
        from checks import find_missing_pairs
        r = self._result(["外来は１８，０００円です"])
        self.assertEqual(find_missing_pairs([("18,000円", "外来")], r), [])


if __name__ == "__main__":
    unittest.main()
