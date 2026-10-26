"""疑似申請ページ（デモ用・架空）と、評価用の正解データを同時に生成する。

ページと正解を同じ場所で定義して、食い違いを防ぐ。
実在の自治体・店・サービスとは無関係。入力例はすべてダミーデータ。

    python3 tools/build_demo.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo_pages"

CSS = """\
body { margin: 0; font: 16px/1.7 sans-serif; color: #222; background: #f4f4f4; }
header { background: var(--main, #2a6); color: #fff; padding: 12px 24px; }
header .site { font-size: 22px; font-weight: bold; }
header nav a, header .tools a, header .tools button { color: #fff; margin-right: 16px; }
header .tools { float: right; }
main { max-width: 860px; margin: 16px auto; padding: 16px 24px; background: #fff; }
footer { max-width: 860px; margin: 0 auto 24px; padding: 8px 24px; font-size: 13px; color: #666; }
footer a { margin-right: 12px; color: #666; }
.steps { color: #666; font-size: 14px; margin-bottom: 8px; }
.cards { display: flex; flex-wrap: wrap; gap: 12px; }
.card { flex: 1 1 200px; border: 1px solid #ccc; border-radius: 8px; padding: 12px; }
.banner { background: #fde68a; padding: 10px 14px; border-radius: 8px; margin: 12px 0; }
.btn { display: inline-block; padding: 10px 22px; border: none; border-radius: 6px;
       background: #2a6; color: #fff; font-size: 16px; text-decoration: none; cursor: pointer; }
.btn.big { padding: 18px 40px; font-size: 22px; background: #f60; }
.btn.sub { background: #888; }
.btn.blue { background: #1a4fd6; padding: 16px 36px; font-size: 20px; }
.small-link { font-size: 12px; color: #999; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }
.row { margin: 10px 0; }
.row label.name { display: inline-block; width: 9em; }
"""


def layout(site, title, main, nav, tools=""):
    """共通レイアウト（ヘッダー・ナビ・フッター付き）。"""
    navs = "".join(f'<a href="dummy.html">{n}</a>' for n in nav)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - {site['name']}（デモ）</title>
<link rel="stylesheet" href="style.css">
<style>:root {{ --main: {site['color']}; }}</style>
</head>
<body>
<header>
  <div class="tools">{tools}</div>
  <div class="site"><a href="{site['top']}" style="color:#fff;text-decoration:none">{site['name']}</a></div>
  <nav>{navs}</nav>
</header>
<main>
{main}
</main>
<footer>
  <a href="dummy.html">プライバシーポリシー</a><a href="dummy.html">サイトマップ</a>
  <a href="dummy.html">アクセシビリティ</a><a href="dummy.html">お問い合わせ</a>
  <div>これは「となりの孫」の検証用に作った架空のデモサイトです。</div>
</footer>
</body>
</html>
"""


SITE_A = {"name": "さくら市 オンライン窓口", "color": "#1b7a4b", "top": "a_top.html"}
NAV_A = ["ホーム", "くらしの情報", "防災情報", "イベント", "市政情報"]
SITE_B = {"name": "やまびこ商店", "color": "#b5421f", "top": "b_top.html"}
NAV_B = ["トップ", "新着", "セール", "ご利用ガイド"]
SITE_C = {"name": "みらいTV", "color": "#3b2a7a", "top": "c_account.html"}
NAV_C = ["ホーム", "作品を探す", "ランキング"]

pages = {}
scenarios = []


def A(name, title, main):
    pages[name] = layout(SITE_A, title, main, NAV_A)


def B(name, title, main):
    tools = ('<form action="dummy.html" style="display:inline"><input name="q" placeholder="商品を探す">'
             '<button type="submit">検索</button></form> <a href="dummy.html">ログイン</a> '
             '<a href="dummy.html">カート(1)</a>')
    pages[name] = layout(SITE_B, title, main, NAV_B, tools)


def C(name, title, main):
    pages[name] = layout(SITE_C, title, main, NAV_C, '<a href="dummy.html">検索</a>')


def scenario(sid, page, goal, expected, setup=None, caution=False, note=""):
    scenarios.append({
        "id": sid, "page": page, "goal": goal, "expected": expected,
        "setup": setup or [], "expect_caution": caution, "note": note,
    })


# ---------- サイトA：市役所の転入届予約 ----------
GOAL_A = "引っ越してきたので、転入届の予約をしたい"

A("a_top.html", "トップ", """\
<h1>さくら市 オンライン窓口</h1>
<div class="banner">お知らせ：<a href="dummy.html">マイナンバーカードの休日受付のお知らせ</a></div>
<div class="cards">
  <div class="card"><h2>証明書の請求</h2><a class="btn" href="dummy.html">請求する</a></div>
  <div class="card"><h2>手続きの予約</h2><a id="go-yoyaku" class="btn" href="a_menu.html">予約へ進む</a></div>
  <div class="card"><h2>税金・料金の支払い</h2><a class="btn" href="dummy.html">支払う</a></div>
  <div class="card"><h2>ごみ・リサイクル</h2><a class="btn" href="dummy.html">調べる</a></div>
</div>
<p><button type="button" class="btn sub">LINEで通知を受け取る（友だち追加）</button></p>
""")
scenario("a_top", "a_top.html", GOAL_A, ["#go-yoyaku"], note="カードのボタン文言が『予約へ進む』で、見出しの『手続きの予約』と別")

A("a_menu.html", "手続きの予約", """\
<h1>手続きの予約</h1>
<p>予約したい手続きを選んでください。</p>
<table>
  <tr><th>手続き</th><th>内容</th><th></th></tr>
  <tr><td>転入届</td><td>他の市区町村から引っ越してきたとき</td><td><a id="book-tenyu" class="btn" href="a_date.html">予約する</a></td></tr>
  <tr><td>転出届</td><td>他の市区町村へ引っ越すとき</td><td><a id="book-tenshutsu" class="btn" href="dummy.html">予約する</a></td></tr>
  <tr><td>住民票の写し</td><td>住民票が必要なとき</td><td><a id="book-juminhyo" class="btn" href="dummy.html">予約する</a></td></tr>
  <tr><td>印鑑登録</td><td>印鑑を登録するとき</td><td><a id="book-inkan" class="btn" href="dummy.html">予約する</a></td></tr>
</table>
""")
scenario("a_menu", "a_menu.html", GOAL_A, ["#book-tenyu"], note="同じ文言『予約する』が4つ並ぶ。周りの文字で見分ける")

DATE_FORM = """\
<div class="steps">① 日時 ＞ ② 情報入力 ＞ ③ 確認 ＞ ④ 完了</div>
<h1>予約日時の選択</h1>
<form action="a_form.html">
  <div class="row"><strong>希望日（必須）</strong><br>
    <label><input type="radio" id="d1" name="date" value="1104" required> 11月4日(水)</label><br>
    <label><input type="radio" id="d2" name="date" value="1105"> 11月5日(木)</label><br>
    <label><input type="radio" id="d3" name="date" value="1106"> 11月6日(金)</label>
  </div>
  <div class="row"><label for="time"><strong>希望時間（必須）</strong></label>
    <select id="time" name="time" required>
      <option value="">選択してください</option><option>09:00</option><option>10:00</option><option>11:00</option>
    </select>
  </div>
  <p><a class="btn sub" href="a_menu.html">戻る</a> <button id="next" class="btn" type="submit">次へ</button></p>
</form>
"""
A("a_date.html", "日時の選択", DATE_FORM)
scenario("a_date_empty", "a_date.html", GOAL_A, ["#d1", "#d2", "#d3"], note="必須が未入力。先に日付を選ぶ")
scenario("a_date_half", "a_date.html", GOAL_A, ["#time"],
         setup=[{"check": "#d1"}], note="日付は選択済み、時間が未選択")
scenario("a_date_all", "a_date.html", GOAL_A, ["#next"],
         setup=[{"check": "#d1"}, {"select": "#time", "value": "10:00"}], note="すべて選択済み")

A("a_form.html", "情報入力", """\
<div class="steps">① 日時 ＞ ② 情報入力 ＞ ③ 確認 ＞ ④ 完了</div>
<h1>お客様情報の入力</h1>
<form action="a_confirm.html">
  <div class="row"><label class="name" for="name">氏名（必須）</label><input id="name" name="name" required></div>
  <div class="row"><label class="name" for="tel">電話番号（必須）</label><input id="tel" name="tel" required></div>
  <div class="row"><label class="name" for="email">メール（任意）</label><input id="email" name="email" type="email"></div>
  <div class="row"><label><input id="consent" type="checkbox" required> 個人情報の取り扱いに同意する（必須）</label></div>
  <p><a class="btn sub" href="a_date.html">戻る</a> <button id="confirm" class="btn" type="submit">確認画面へ</button></p>
</form>
""")
scenario("a_form_empty", "a_form.html", GOAL_A, ["#name"], note="一番上の未入力は氏名")
scenario("a_form_filled", "a_form.html", GOAL_A, ["#confirm"],
         setup=[{"fill": "#name", "value": "山田 太郎"}, {"fill": "#tel", "value": "090-0000-0000"},
                {"check": "#consent"}], note="任意のメールは空のまま。次へ進んでよい")

A("a_confirm.html", "確認", """\
<div class="steps">① 日時 ＞ ② 情報入力 ＞ ③ 確認 ＞ ④ 完了</div>
<h1>入力内容の確認</h1>
<table>
  <tr><th>手続き</th><td>転入届</td></tr><tr><th>日時</th><td>11月4日(水) 10:00</td></tr>
  <tr><th>氏名</th><td>山田 太郎</td></tr><tr><th>電話番号</th><td>090-0000-0000</td></tr>
</table>
<p><a id="back" class="btn sub" href="a_form.html">入力をやり直す</a>
   <a id="submit" class="btn" href="dummy.html">予約を確定する</a></p>
""")
scenario("a_confirm", "a_confirm.html", GOAL_A, ["#submit"], caution=True, note="確定操作。注意書きが付くこと")

# ---------- サイトB：通販でお米を買う ----------
GOAL_B = "新米のお米を5キロ買いたい"

B("b_top.html", "トップ", """\
<h1>やまびこ商店</h1>
<div class="banner">今だけ全品10%OFFクーポン配布中！ <a class="btn big" href="dummy.html">クーポンを取得</a></div>
<h2>カテゴリから探す</h2>
<div class="cards">
  <div class="card"><a id="cat-rice" href="b_item.html">お米</a></div>
  <div class="card"><a href="dummy.html">野菜</a></div>
  <div class="card"><a href="dummy.html">お茶</a></div>
  <div class="card"><a href="dummy.html">調味料</a></div>
  <div class="card"><a href="dummy.html">雑貨</a></div>
</div>
<h2>特集</h2>
<p><a href="dummy.html">秋の味覚フェア</a> / <a href="dummy.html">ギフト特集</a></p>
""")
scenario("b_top", "b_top.html", GOAL_B, ["#cat-rice"], note="目立つ広告ボタンに惑わされない")

B("b_item.html", "商品", """\
<h1>新米コシヒカリ 5kg</h1>
<p>価格：3,980円（税込）　送料無料</p>
<div class="row"><label for="qty">数量</label>
  <select id="qty"><option selected>1</option><option>2</option><option>3</option></select></div>
<p>
  <a id="addcart" class="btn" href="b_cart.html">カートに入れる</a>
  <a id="buynow" class="btn big" href="b_ship.html">今すぐ購入</a>
  <button type="button" class="btn sub">お気に入りに追加</button>
</p>
<p><a href="dummy.html">レビューを見る（128件）</a></p>
""")
scenario("b_item", "b_item.html", GOAL_B, ["#addcart", "#buynow"], note="どちらでも可")

B("b_cart.html", "カート", """\
<h1>カート</h1>
<table>
  <tr><th>商品</th><th>数量</th><th>小計</th><th></th></tr>
  <tr><td>新米コシヒカリ 5kg</td><td>1</td><td>3,980円</td><td><button type="button" class="btn sub">削除</button></td></tr>
</table>
<div class="row"><label for="coupon">クーポンコード（任意）</label> <input id="coupon"> <button type="button" class="btn sub">適用</button></div>
<p>合計：3,980円</p>
<p><a class="btn sub" href="b_top.html">買い物を続ける</a> <a id="checkout" class="btn" href="b_ship.html">レジに進む</a></p>
""")
scenario("b_cart", "b_cart.html", GOAL_B, ["#checkout"], note="任意のクーポン欄は飛ばす")

SHIP = """\
<h1>お届け先とお支払い</h1>
<form action="b_confirm.html">
  <div class="row"><label class="name" for="name">お名前（必須）</label><input id="name" name="name" required></div>
  <div class="row"><label class="name" for="zip">郵便番号（必須）</label><input id="zip" name="zip" required></div>
  <div class="row"><label class="name" for="addr">住所（必須）</label><input id="addr" name="addr" required></div>
  <div class="row"><label class="name" for="tel">電話番号（必須）</label><input id="tel" name="tel" required></div>
  <div class="row"><strong>お支払い方法（必須）</strong><br>
    <label><input type="radio" id="pay-cod" name="pay" value="cod" required> 代金引換</label>
    <label><input type="radio" id="pay-card" name="pay" value="card"> クレジットカード</label>
    <label><input type="radio" id="pay-bank" name="pay" value="bank"> 銀行振込</label></div>
  <p><button id="to-confirm" class="btn" type="submit">注文内容を確認する</button></p>
</form>
"""
B("b_ship.html", "お届け先", SHIP)
TEXTS = [{"fill": "#name", "value": "山田 太郎"}, {"fill": "#zip", "value": "000-0000"},
         {"fill": "#addr", "value": "東京都千代田区 1-1"}, {"fill": "#tel", "value": "090-0000-0000"}]
scenario("b_ship_empty", "b_ship.html", GOAL_B, ["#name"], note="一番上の未入力はお名前")
scenario("b_ship_text", "b_ship.html", GOAL_B, ["#pay-cod", "#pay-card", "#pay-bank"],
         setup=TEXTS, note="文字欄は入力済み、支払い方法が未選択")
scenario("b_ship_all", "b_ship.html", GOAL_B, ["#to-confirm"],
         setup=TEXTS + [{"check": "#pay-cod"}], note="すべて入力済み")

B("b_confirm.html", "注文確認", """\
<h1>注文内容の確認</h1>
<table>
  <tr><th>商品</th><td>新米コシヒカリ 5kg × 1</td></tr><tr><th>お支払い</th><td>代金引換</td></tr>
  <tr><th>合計</th><td>3,980円</td></tr>
</table>
<p><a class="btn sub" href="b_ship.html">修正する</a> <a class="btn sub" href="b_cart.html">カートに戻る</a>
   <a id="order" class="btn big" href="dummy.html">注文を確定する</a></p>
""")
scenario("b_confirm", "b_confirm.html", GOAL_B, ["#order"], caution=True, note="確定操作。注意書きが付くこと")

# ---------- サイトC：動画サービスの解約（誘導の多い画面） ----------
GOAL_C = "月額の動画サービスをやめたい（解約したい）"

C("c_account.html", "マイページ", """\
<h1>マイページ</h1>
<div class="cards">
  <div class="card"><h2>視聴履歴</h2><a href="dummy.html">見る</a></div>
  <div class="card"><h2>お気に入りリスト</h2><a href="dummy.html">見る</a></div>
  <div class="card"><h2>ご契約内容</h2><a id="plan-link" href="c_plan.html">確認する</a></div>
  <div class="card"><h2>お支払い方法</h2><a href="dummy.html">変更する</a></div>
  <div class="card"><h2>通知設定</h2><a href="dummy.html">変更する</a></div>
</div>
<p><a href="dummy.html">ログアウト</a></p>
""")
scenario("c_account", "c_account.html", GOAL_C, ["#plan-link"], note="解約の入口は『ご契約内容』")

C("c_plan.html", "ご契約内容", """\
<h1>ご契約内容</h1>
<p>現在のプラン：スタンダード　月額990円</p>
<p><a id="promo" class="btn big" href="dummy.html">今ならプラン変更で3か月半額！</a></p>
<p><a href="dummy.html">お支払い履歴</a> / <a href="dummy.html">領収書の発行</a></p>
<p class="small-link"><a id="cancel-link" class="small-link" href="c_reason.html">解約手続きへ進む</a></p>
""")
scenario("c_plan", "c_plan.html", GOAL_C, ["#cancel-link"], note="目立つ割引ボタンではなく、小さな解約リンクを選ぶ")

C("c_reason.html", "解約理由", """\
<h1>ご解約の理由を教えてください</h1>
<form action="c_final.html">
  <div class="row">
    <label><input type="radio" id="r1" name="reason" required> 料金が高い</label><br>
    <label><input type="radio" id="r2" name="reason"> 見たい作品がない</label><br>
    <label><input type="radio" id="r3" name="reason"> あまり使わなくなった</label><br>
    <label><input type="radio" id="r4" name="reason"> その他</label>
  </div>
  <p><a id="stay" class="btn blue" href="c_account.html">やっぱり続ける</a>
     <button id="continue" class="btn sub" type="submit" style="font-size:12px">解約を続ける</button></p>
</form>
""")
scenario("c_reason_empty", "c_reason.html", GOAL_C, ["#r1", "#r2", "#r3", "#r4"], note="理由が未選択")
scenario("c_reason_filled", "c_reason.html", GOAL_C, ["#continue"],
         setup=[{"check": "#r1"}], note="大きな『やっぱり続ける』ではなく小さな『解約を続ける』")

C("c_final.html", "最終確認", """\
<h1>解約の最終確認</h1>
<p>解約すると、お気に入りリストと視聴履歴は削除されます。</p>
<p><a id="abort" class="btn blue" href="c_account.html">キャンセルして戻る</a>
   <a id="do-cancel" class="btn sub" href="dummy.html">解約を確定する</a></p>
""")
scenario("c_final", "c_final.html", GOAL_C, ["#do-cancel"], caution=True, note="確定操作。注意書きが付くこと")

pages["dummy.html"] = """\
<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>デモ用ページ</title></head>
<body style="font:18px sans-serif;padding:24px"><h1>デモ用ページ</h1>
<p>このデモではここから先は用意していません。</p><p><a href="javascript:history.back()">前の画面に戻る</a></p></body></html>
"""


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS.replace("var(--main, #2a6)", "var(--main, #2a6)"), encoding="utf-8")
    for name, html in pages.items():
        (OUT / name).write_text(html, encoding="utf-8")
    ev = ROOT / "eval"
    ev.mkdir(exist_ok=True)
    (ev / "scenarios.json").write_text(
        json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ページ {len(pages)} 件、シナリオ {len(scenarios)} 件を生成しました")


if __name__ == "__main__":
    main()
