"""となりの孫：ローカルプロキシ。

拡張機能にAPIキーを持たせないため、127.0.0.1 でだけ待ち受けて Claude API に中継する。
- Chrome拡張（Origin が chrome-extension://）以外からのリクエストは拒否する
- 画面の内容はログに残さない（メソッド・パス・結果・トークン数のみ）

使い方:
    python3 proxy/server.py            # 本番（APIキーが必要）
    python3 proxy/server.py --mock     # APIを呼ばない動作確認用
"""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
import scamcheck  # noqa: E402
import simplify  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787
MAX_BODY = 4 * 1024 * 1024  # スクリーンショット込みでも十分な上限


class Handler(BaseHTTPRequestHandler):
    mock = False

    def log_message(self, fmt, *args):  # 標準のアクセスログは出さない（自前で出す）
        pass

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        # 拡張機能、または Origin を持たない直接呼び出し（評価スクリプト等）だけ許可
        return origin is None or origin.startswith("chrome-extension://")

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self.headers.get("Origin")
        if origin and origin.startswith("chrome-extension://"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if not self._origin_ok():
            return self._send(403, {"error": "許可されていない呼び出し元です"})
        self.send_response(204)
        origin = self.headers.get("Origin", "")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self):
        if not self._origin_ok():
            return self._send(403, {"error": "許可されていない呼び出し元です"})
        if self.path == "/health":
            return self._send(200, {"ok": True, "mock": self.mock, "backend": core.backend(),
                                    "has_key": bool(core.load_api_key())})
        self._send(404, {"error": "見つかりません"})

    def _simplify(self, req, started):
        doc = {"title": str(req.get("title", ""))[:200], "text": str(req["text"])}
        result = simplify.simplify(doc, model=req.get("model", "haiku"), mock=self.mock)
        usage = result["usage"]
        print(f"POST /simplify 200 {time.time() - started:.1f}s "
              f"in={usage['input_tokens']} out={usage['output_tokens']} model={result['model']}", flush=True)
        self._send(200, result)

    def _scamcheck(self, req, started):
        doc = {"text": str(req["text"]), "source": str(req.get("source", ""))}
        result = scamcheck.check(doc, model=req.get("model", "haiku"), mock=self.mock)
        usage = result["usage"]
        print(f"POST /scamcheck 200 {time.time() - started:.1f}s verdict={result['verdict']} "
              f"in={usage['input_tokens']} out={usage['output_tokens']} model={result['model']}", flush=True)
        self._send(200, result)

    def do_POST(self):
        if not self._origin_ok():
            return self._send(403, {"error": "許可されていない呼び出し元です"})
        if self.path not in ("/guide", "/simplify", "/scamcheck"):
            return self._send(404, {"error": "見つかりません"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._send(413, {"error": "送られたデータの大きさが正しくありません"})
        started = time.time()
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            if self.path == "/simplify":
                return self._simplify(req, started)
            if self.path == "/scamcheck":
                return self._scamcheck(req, started)
            page = req["page"]
            if not isinstance(page.get("elements"), list):
                raise ValueError("elements がありません")
            result = core.ask_guide(
                page,
                goal=str(req.get("goal", ""))[:200],
                history=[str(h) for h in req.get("history", [])][-3:],
                model=req.get("model", "haiku"),
                screenshot=req.get("screenshot"),
                mock=self.mock,
            )
            usage = result["usage"]
            print(f"POST /guide 200 {time.time() - started:.1f}s "
                  f"in={usage['input_tokens']} out={usage['output_tokens']} model={result['model']}",
                  flush=True)
            self._send(200, result)
        except core.GuideError as e:
            print(f"POST {self.path} 502 {e}", flush=True)
            self._send(502, {"error": str(e)})
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"POST {self.path} 400 {type(e).__name__}", flush=True)
            self._send(400, {"error": "送られたデータの形が正しくありません"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="APIを呼ばずダミーで応答する")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    Handler.mock = args.mock
    server = ThreadingHTTPServer((HOST, args.port), Handler)
    if args.mock:
        mode = "モック"
    elif core.backend() == "cli":
        mode = "Claude CLI経由（サブスク）"
    else:
        mode = "APIキーあり" if core.load_api_key() else "APIキー未設定"
    print(f"となりの孫プロキシ: http://{HOST}:{args.port} ({mode})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
