# -*- coding: utf-8 -*-
"""
ポケットカード配信サイトのビルドスクリプト。

保管庫直下の単一HTMLカード（＝正本）を読み、
  - manifest / theme-color / Service Worker 登録
  - ハブへ戻るバー
だけを注入して cards/ に書き出す。カードの中身そのものは一切書き換えない。

    python build.py

正本を編集したら必ずこれを再実行する（逆に cards/ を直接編集しない）。
"""
import hashlib
import io
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.dirname(ROOT)
CARDS_DIR = os.path.join(ROOT, "cards")

# ハブの構成。カードを増やすときは該当セクションに1行足すだけでよい。
# 各項目 = (出力ファイル名, 正本ファイル名, ハブでの表示名, 一言説明, 分野タグ)
SECTIONS = [
    ("ポケットカード", "ベッドサイドで開く要点まとめ", [
        ("nms.html",
         "NMS治療ポケットカード.html",
         "悪性症候群（NMS）治療",
         "確立した治療は原因薬中止と支持療法のみ。薬物療法はいずれもRCTがない。PHS型では逆に原因薬を再開する。",
         "神経・中毒"),
        ("ich-postop.html",
         "脳出血術後管理ポケットカード.html",
         "脳出血 術後管理",
         "開頭・内視鏡血腫除去後の全身管理。術後に特化したRCTは存在せず、推奨は全て他病態からの外挿。",
         "脳神経"),
        ("ich-targets.html",
         "脳出血術後管理 目標値カード.html",
         "脳出血 術後 目標値",
         "血圧・体温・血糖などの目標値を、根拠の質（ガイドライン／RCT／外挿／慣習）で色分けした一覧。",
         "脳神経"),
        ("nephrosclerosis.html",
         "高血圧性腎硬化症 降圧薬ポケットカード.html",
         "高血圧性腎硬化症の降圧薬",
         "ICUでの内服導入。第一選択は蛋白尿の有無で決まり、降圧効果と腎保護効果は別の軸として評価する。",
         "腎・循環"),
        ("chest-tube.html",
         "胸腔ドレーン管理ポケットカード.html",
         "胸腔ドレーン管理",
         "吸引とwater sealの使い分け、適正陰圧、air leakの切り分け、フルクチュエーション消失の鑑別、抜去基準。",
         "呼吸・外傷"),
        ("rtm.html",
         "リコモジュリン（rTM）ポケットカード.html",
         "リコモジュリン（rTM）",
         "適応はDICであって敗血症ではない。用量・禁忌・TATでの効果判定・やめどきと、SCARLETが陰性である事実。",
         "凝固・敗血症"),
        ("pcas.html",
         "PCAS（心拍再開後症候群）管理ポケットカード.html",
         "PCAS 心拍再開後の管理",
         "体温は深く冷やすより発熱予防（37.5℃以下）。神経学的予後予測は72時間以降・multimodal・偽陽性0%の所見でのみ行う。",
         "蘇生・集中治療"),
        ("sci-syndromes.html",
         "脊髄損傷症候群ポケットカード.html",
         "脊髄損傷症候群",
         "横断面の3本の走行路で局在が読める。円錐か馬尾かで初動は変わらない。馬尾は48時間、SCI全体は24時間。",
         "脊椎・外傷"),
        ("legionella.html",
         "レジオネラ肺炎ポケットカード.html",
         "レジオネラ肺炎",
         "尿中抗原は陰性でも否定できない（血清群1限定・軽症で感度37.9%）。予後を変えるのは薬剤選択でなく投与の早さ。",
         "感染症・呼吸"),
    ]),
    ("アプリ", "その場で計算・練習するもの", [
        ("respiratory-mechanics.html",
         "respiratory-mechanics-app.html",
         "呼吸メカニクス計算",
         "駆動圧・コンプライアンス・抵抗に加え、R/I ratio、decremental PEEP、神経筋駆動の評価まで。",
         "人工呼吸"),
        ("ncse-eeg-trainer.html",
         "ncse-eeg-trainer.html",
         "NCSE 脳波判読トレーナー",
         "合成脳波でNCSEの判読を練習する。Salzburg基準＋ACNS 2021、14パターン・4難易度。",
         "脳波・教育"),
    ]),
]

# 平坦化したカード一覧（生成処理はこちらを使う）
CARDS = [c for _title, _sub, items in SECTIONS for c in items]

BACK_BAR_CSS = """
<style>
  /* ポケットカード系は --surface / 臨床アプリ系は --panel を持つ。両方に効くよう連鎖させる */
  .pc-backbar{position:sticky;top:0;z-index:9999;display:flex;align-items:center;gap:8px;
    padding:10px 14px;margin:0 0 4px;
    background:var(--surface,var(--panel,#fff));border-bottom:1px solid var(--line,#dde3ec);
    color:var(--accent,#0e7c86);font:600 14px/1.2 var(--sans,system-ui);
    text-decoration:none;-webkit-tap-highlight-color:transparent}
  .pc-backbar:active{background:var(--surface-2,var(--panel2,#f5f7fa))}
  .pc-backbar svg{flex:none}
  @supports (padding-top: env(safe-area-inset-top)){
    .pc-backbar{padding-top:calc(10px + env(safe-area-inset-top))}
  }
</style>
"""

BACK_BAR_HTML = """
<a class="pc-backbar" href="../index.html">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M15 18l-6-6 6-6"/>
  </svg>ポケットカード一覧
</a>
"""

HEAD_INJECT = """<link rel="manifest" href="../app.webmanifest">
<meta name="theme-color" content="#0e7c86" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#10141b" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../icons/icon-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="../icons/icon-180.png">
"""

SW_REGISTER = """<script>
if ('serviceWorker' in navigator) {
  addEventListener('load', function () {
    navigator.serviceWorker.register('../sw.js', { scope: '../' }).catch(function () {});
  });
}
</script>
"""


def build_card(out_name, src_name):
    src = os.path.join(VAULT, src_name)
    s = io.open(src, encoding="utf-8").read()

    if "<!doctype" not in s.lower():
        raise SystemExit("doctype がありません（正本が壊れています）: " + src_name)
    if re.search(r'(src|href)\s*=\s*["\']https?://', s):
        raise SystemExit("外部参照が混入しています（オフラインで壊れます）: " + src_name)

    # <head> の直後にメタ類、</head> の直前に戻るバーのCSS
    s = s.replace("<head>", "<head>\n" + HEAD_INJECT, 1)
    s = s.replace("</head>", BACK_BAR_CSS + "</head>", 1)
    # <body> の直後に戻るバー、</body> の直前に SW 登録
    s = s.replace("<body>", "<body>" + BACK_BAR_HTML, 1)
    s = s.replace("</body>", SW_REGISTER + "</body>", 1)

    io.open(os.path.join(CARDS_DIR, out_name), "w", encoding="utf-8", newline="\n").write(s)
    return len(s.encode("utf-8"))


def build_index():
    tpl = io.open(os.path.join(ROOT, "_index.template.html"), encoding="utf-8").read()
    blocks = []
    for sec_title, sec_sub, items in SECTIONS:
        rows = []
        for out_name, _src, title, desc, tag in items:
            rows.append(
                '      <a class="card" href="cards/{href}">\n'
                '        <span class="tag">{tag}</span>\n'
                '        <h2>{title}</h2>\n'
                '        <p>{desc}</p>\n'
                "      </a>".format(href=out_name, tag=tag, title=title, desc=desc)
            )
        blocks.append(
            '  <section>\n'
            '    <h2 class="sec">{t}<span>{s}</span></h2>\n'
            '    <div class="grid">\n{rows}\n    </div>\n'
            '  </section>'.format(t=sec_title, s=sec_sub, rows="\n".join(rows))
        )
    out = tpl.replace("<!--SECTIONS-->", "\n\n".join(blocks))
    io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8", newline="\n").write(out)


def build_sw():
    """全アセットの内容ハッシュをキャッシュ名に埋め、更新時に確実に入れ替わるようにする。"""
    assets = ["index.html", "app.webmanifest",
              "icons/icon-192.png", "icons/icon-512.png",
              "icons/icon-maskable-512.png", "icons/icon-180.png"]
    assets += ["cards/" + c[0] for c in CARDS]

    h = hashlib.sha256()
    for a in sorted(assets):
        h.update(a.encode("utf-8"))
        h.update(open(os.path.join(ROOT, a), "rb").read())
    version = h.hexdigest()[:12]

    tpl = io.open(os.path.join(ROOT, "_sw.template.js"), encoding="utf-8").read()
    out = (tpl.replace("__VERSION__", version)
              .replace("__ASSETS__",
                       ",\n  ".join('"./%s"' % a for a in assets)))
    io.open(os.path.join(ROOT, "sw.js"), "w", encoding="utf-8", newline="\n").write(out)
    return version


if __name__ == "__main__":
    if os.path.isdir(CARDS_DIR):
        shutil.rmtree(CARDS_DIR)
    os.makedirs(CARDS_DIR)

    for out_name, src_name, title, _d, _t in CARDS:
        n = build_card(out_name, src_name)
        print("  cards/%-26s %7d bytes  %s" % (out_name, n, title))

    build_index()
    print("  index.html")
    v = build_sw()
    print("  sw.js (cache v%s)" % v)
    print("\nビルド完了。git add -A && git commit && git push で公開されます。")
