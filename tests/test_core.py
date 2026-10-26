"""core.py の単体テスト（ネットワーク不要）。

    python3 -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proxy"))
import core  # noqa: E402


class MaskPiiTest(unittest.TestCase):
    def test_電話番号を伏せる(self):
        self.assertEqual(core.mask_pii("連絡先 090-0000-0000 です"), "連絡先 〔電話番号〕 です")
        self.assertEqual(core.mask_pii("03-0000-0000"), "〔電話番号〕")

    def test_メールを伏せる(self):
        self.assertEqual(core.mask_pii("example@example.com へ"), "〔メール〕 へ")

    def test_郵便番号と12桁番号を伏せる(self):
        self.assertEqual(core.mask_pii("〒000-0000"), "〒〔郵便番号〕")
        self.assertEqual(core.mask_pii("番号 000000000000"), "番号 〔12桁の番号〕")

    def test_普通の文は変えない(self):
        self.assertEqual(core.mask_pii("11月4日(水) 10:00 に予約"), "11月4日(水) 10:00 に予約")


class PromptTest(unittest.TestCase):
    PAGE = {
        "title": "お客様情報の入力",
        "headings": ["お客様情報の入力"],
        "text": "電話は 090-0000-0000",
        "elements": [
            {"id": "e1", "kind": "入力欄", "label": "氏名（必須）", "required": True, "filled": False},
            {"id": "e2", "kind": "ボタン", "label": "確認画面へ", "area": "本文"},
            {"id": "e3", "kind": "ボタン", "label": "予約する", "context": "転入届 他の市区町村から"},
        ],
    }

    def test_要素の行にフラグが付く(self):
        line = core.format_element(self.PAGE["elements"][0])
        self.assertIn("必須", line)
        self.assertIn("未入力", line)

    def test_文脈が付く(self):
        self.assertIn("転入届", core.format_element(self.PAGE["elements"][2]))

    def test_本文は伏せて組み立てる(self):
        text = core.build_user_text(self.PAGE, goal="転入届の予約")
        self.assertNotIn("090-0000-0000", text)
        self.assertIn("転入届の予約", text)
        self.assertIn("e2", text)

    def test_やりたいこと未入力でも組み立てられる(self):
        self.assertIn("未入力", core.build_user_text(self.PAGE))


class MockTest(unittest.TestCase):
    def test_モックは目的の語に当たる要素を返す(self):
        page = {"elements": [
            {"id": "e1", "kind": "リンク", "label": "ホーム"},
            {"id": "e2", "kind": "ボタン", "label": "予約する", "context": "転入届"},
        ]}
        r = core.ask_guide(page, goal="転入届の予約", mock=True)
        self.assertEqual(r["target_id"], "e2")

    def test_要素がなければ判断しない(self):
        r = core.ask_guide({"elements": []}, goal="", mock=True)
        self.assertIsNone(r["target_id"])
        self.assertTrue(r["ask_human"])


if __name__ == "__main__":
    unittest.main()
