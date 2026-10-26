"""CLI方式（Claude Code CLI 経由）の単体テスト。本物の claude は呼ばず、偽のコマンドで検証する。

    python3 -m unittest discover -s tests
"""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proxy"))
import core  # noqa: E402

PAGE = {"elements": [{"id": "e1", "kind": "ボタン", "label": "予約する"}]}


class FakeClaude:
    """PATH の先頭に偽の claude を置く。script は bash の本文。"""

    def __init__(self, script):
        self.script = script

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        path = Path(self.dir.name) / "claude"
        path.write_text("#!/bin/bash\n" + self.script + "\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        self.saved = {k: os.environ.get(k) for k in ("PATH", "TNM_BACKEND", "TNM_CLI_TIMEOUT")}
        os.environ["PATH"] = self.dir.name + os.pathsep + os.environ["PATH"]
        os.environ["TNM_BACKEND"] = "cli"
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.dir.cleanup()


RESULT = ('{"type":"result","is_error":false,"structured_output":{"target_id":"e1","reason":"予約するを押します",'
          '"confidence":"high","caution":"","ask_human":false},'
          '"usage":{"input_tokens":3,"cache_creation_input_tokens":100,"cache_read_input_tokens":50,"output_tokens":20}}')


class CliBackendTest(unittest.TestCase):
    def test_構造化出力を読み取る(self):
        with FakeClaude(f"cat >/dev/null; echo '{RESULT}'"):
            r = core.ask_guide(PAGE, goal="予約")
        self.assertEqual(r["target_id"], "e1")
        self.assertEqual(r["usage"], {"input_tokens": 153, "output_tokens": 20})

    def test_警告行が混ざっても読める(self):
        with FakeClaude(f"cat >/dev/null; echo '[claude-code:unrecognized_model] x' >&2; echo 'warning'; echo '{RESULT}'"):
            self.assertEqual(core.ask_guide(PAGE, goal="予約")["target_id"], "e1")

    def test_存在しないIDは採用しない(self):
        bad = RESULT.replace('"e1","reason"', '"e99","reason"')
        with FakeClaude(f"cat >/dev/null; echo '{bad}'"):
            r = core.ask_guide(PAGE, goal="予約")
        self.assertIsNone(r["target_id"])
        self.assertTrue(r["ask_human"])

    def test_エラー結果は利用者向けのエラーにする(self):
        err = '{"type":"result","is_error":true,"result":"usage limit reached"}'
        with FakeClaude(f"cat >/dev/null; echo '{err}'"):
            with self.assertRaises(core.GuideError) as cm:
                core.ask_guide(PAGE, goal="予約")
        self.assertIn("usage limit", str(cm.exception))

    def test_時間切れは孫プロセスごと止めてエラーにする(self):
        with FakeClaude("( sleep 30 ) & sleep 30"):
            os.environ["TNM_CLI_TIMEOUT"] = "1"
            with self.assertRaises(core.GuideError) as cm:
                core.ask_guide(PAGE, goal="予約")
        self.assertIn("応答がありません", str(cm.exception))

    def test_コマンドが無ければ案内する(self):
        saved = {k: os.environ.get(k) for k in ("PATH", "TNM_BACKEND")}
        os.environ["PATH"] = "/nonexistent"
        os.environ["TNM_BACKEND"] = "cli"
        try:
            with self.assertRaises(core.GuideError) as cm:
                core.ask_guide(PAGE, goal="予約")
            self.assertIn("見つかりません", str(cm.exception))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
