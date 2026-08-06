# 臨床ポケットカード（配信サイト）

保管庫直下の単一HTMLポケットカードを、スマホから開けるように GitHub Pages で配信するための一式。
Android Chrome で「アプリをインストール」するとホーム画面のアイコンから起動でき、
Service Worker により**電波の無い場所でも全カードが開く**。

**公開URL: <https://kingrokoroko.github.io/pocket-cards/>**

## 構成

```
_index.template.html   ハブ（一覧）のテンプレート。カード一覧は build.py が流し込む
_sw.template.js        Service Worker のテンプレート。バージョンは build.py が埋める
build.py               正本カード → cards/ を生成し、index.html と sw.js を書き出す
make_icons.py          アプリアイコンを生成（デザインを変えた時だけ実行）
app.webmanifest        PWA マニフェスト
.nojekyll              GitHub Pages の Jekyll 処理を無効化
index.html   sw.js   cards/   icons/      ← すべて生成物。直接編集しない
```

## 正本はどこか

カードの中身の正本は **保管庫直下の HTML**（このフォルダの1つ上）。

| 出力 | 正本 |
|---|---|
| `cards/nms.html` | `../NMS治療ポケットカード.html` |
| `cards/ich-postop.html` | `../脳出血術後管理ポケットカード.html` |
| `cards/ich-targets.html` | `../脳出血術後管理 目標値カード.html` |
| `cards/nephrosclerosis.html` | `../高血圧性腎硬化症 降圧薬ポケットカード.html` |

`build.py` は正本に対して manifest / theme-color / SW登録 / 戻るバーを**注入するだけ**で、
カードの中身は書き換えない。したがって：

- **正本を編集 → `python build.py` → commit & push** の順を必ず守る
- `cards/` を直接編集しない（次のビルドで消える）

カードを増やすときは `build.py` の `CARDS` に1行足すだけでよい（ハブにも自動で並ぶ）。

## 更新のしかた

```
python build.py
git add -A && git commit -m "update" && git push
```

`build.py` は全アセットの内容ハッシュを Service Worker のキャッシュ名に埋め込むので、
push すれば端末側のキャッシュは自動で入れ替わる（手動でキャッシュ削除する必要はない）。

ビルド時に以下を検査し、引っかかれば中断する：

- `<!doctype>` の欠落（無いとスマホで文字化け・デスクトップ幅表示になる）
- `http(s)://` を指す `src` / `href` の混入（オフラインで壊れる）

## 免責

個人の学習用まとめ。患者情報は含まない。
