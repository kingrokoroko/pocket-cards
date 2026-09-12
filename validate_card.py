# -*- coding: utf-8 -*-
"""
ポケットカードの「正本を作る → SECTIONS に登録 → build.py → push」の取りこぼしを検出する。

カードの仕様は build.py の SECTIONS が唯一の正であり、このスクリプトはそれを import して
参照するだけ。カード一覧をここに書き写さないこと（二重管理になり必ず腐る）。

    python validate_card.py               # 保管庫直下のカードを全部検査
    python validate_card.py <path> ...    # 指定ファイルだけ検査
    python validate_card.py --hook        # Claude Code の PostToolUse フックから呼ばれる

終了コード: 0 = 問題なし / 2 = 配信が壊れる欠陥あり
"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402  （SECTIONS / VAULT / CARDS_DIR を借りる）

ROOT = build.ROOT
VAULT = build.VAULT
CARDS_DIR = build.CARDS_DIR

# 正本ファイル名 -> (出力名, 表示名)
REGISTERED = {src: (out, title) for out, src, title, _d, _t in build.CARDS}

# 意図的に GitHub Pages へ出していないもの。増やすときはここに理由付きで足す。
UNPUBLISHED = {
    "meal-training-tracker.html":        "食事・トレーニング記録（個人データ前提のため非配信）",
    "キャッシュフローシミュレーター.html": "家計シミュレータ（個人資産情報のため非配信）",
    "respiratory-mechanics.html":        "PC版。配信しているのは respiratory-mechanics-app.html",
    "respiratory-mechanics-mobile.html": "スマホ版の旧系統。配信は -app 版",
}

NEWLINE = chr(10)

EXTERNAL_REF = re.compile(r'(src|href)\s*=\s*["\']https?://', re.I)
CHARSET = re.compile(r'<meta[^>]+charset', re.I)
VIEWPORT = re.compile(r'<meta[^>]+name\s*=\s*["\']viewport["\']', re.I)


def _utf8_stdio():
    """Windows の cp932 コンソールへ日本語を出すと落ちるので UTF-8 に固定する。"""
    for stream in ("stdout", "stderr"):
        s = getattr(sys, stream)
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


def is_card_source(path):
    """保管庫直下の、バックアップでない .html だけを対象にする。"""
    path = os.path.abspath(path)
    if not path.lower().endswith(".html"):
        return False
    if os.path.dirname(path) != os.path.abspath(VAULT):
        return False
    if ".backup-" in os.path.basename(path):
        return False
    return True


def check_file(src_name, verbose_unpublished=True):
    """1ファイルを検査して (errors, notices) を返す。"""
    errors, notices = [], []
    path = os.path.join(VAULT, src_name)
    if not os.path.exists(path):
        return ["ファイルが存在しません: " + src_name], []

    s = io.open(path, encoding="utf-8", errors="replace").read()

    # --- 構造チェック（無いとスマホで壊れる。PCでは気づけない） ---
    if "<!doctype" not in s.lower():
        errors.append("<!doctype html> がありません → スマホで互換モードになり表示が崩れます")
    if not CHARSET.search(s):
        errors.append('<meta charset="utf-8"> がありません → スマホで文字化けします')
    if not VIEWPORT.search(s):
        errors.append('<meta name="viewport"> がありません → スマホでデスクトップ幅になります')
    m = EXTERNAL_REF.search(s)
    if m:
        line = s[:m.start()].count("\n") + 1
        errors.append("外部参照があります（%d行目付近）→ オフラインの病院端末で壊れます" % line)

    # --- 配信チェーンのチェック ---
    if src_name in UNPUBLISHED:
        if verbose_unpublished:
            notices.append("配信対象外として登録済み（%s）" % UNPUBLISHED[src_name])
        return errors, notices

    if src_name not in REGISTERED:
        errors.append(
            "build.py の SECTIONS に未登録 → ビルドされず、ハブにも並ばず、スマホから開けません。\n"
            "      pocket-cards-site/build.py の SECTIONS に1行足してください"
            "（臨床カード＝「ポケットカード」節／計算・練習ツール＝「アプリ」節）")
        return errors, notices

    out_name, _title = REGISTERED[src_name]
    out_path = os.path.join(CARDS_DIR, out_name)
    if not os.path.exists(out_path):
        notices.append("cards/%s が未生成 → build.py を実行してください" % out_name)
    elif os.path.getmtime(path) > os.path.getmtime(out_path):
        notices.append("正本が cards/%s より新しい → build.py の再実行が必要です" % out_name)

    return errors, notices


def git_state():
    """生成物が commit / push 済みかを見る。正本は git 管理外なので対象外。"""
    def run(args):
        return subprocess.run(["git"] + args, cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    notices = []
    st = run(["status", "--porcelain"])
    if st.returncode != 0:
        return []
    if st.stdout.strip():
        n = len(st.stdout.strip().splitlines())
        notices.append("pocket-cards-site に未コミットの変更が %d件 → commit && push で配信されます" % n)
    else:
        ahead = run(["rev-list", "--count", "@{u}..HEAD"])
        if ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0"):
            notices.append("未 push のコミットが %s件 → push で配信されます"
                           % ahead.stdout.strip())
    return notices


def report(targets, include_git, verbose_unpublished=True):
    all_errors, all_notices = [], []
    for src_name in targets:
        errors, notices = check_file(src_name, verbose_unpublished)
        for e in errors:
            all_errors.append("%s\n      %s" % (src_name, e))
        for n in notices:
            all_notices.append("%s: %s" % (src_name, n))
    if include_git:
        all_notices += git_state()
    return all_errors, all_notices


def main_cli(argv):
    if argv:
        targets = [os.path.basename(os.path.abspath(a)) for a in argv]
        include_git = False
    else:
        targets = sorted(f for f in os.listdir(VAULT)
                         if is_card_source(os.path.join(VAULT, f)))
        include_git = True

    errors, notices = report(targets, include_git,
                             verbose_unpublished=bool(argv))

    print("検査対象: %d ファイル" % len(targets))
    if errors:
        print("\n■ 欠陥（配信が壊れます）")
        for e in errors:
            print("  ✗ " + e)
    if notices:
        print("\n■ 残り作業")
        for n in notices:
            print("  ・" + n)
    if not errors and not notices:
        print("\n問題なし。全カードが登録・ビルド・push 済みです。")
    return 2 if errors else 0


def read_hook_payload():
    """Claude Code は UTF-8 で JSON を渡すが、Windows の sys.stdin は cp932 で
    デコードしようとして落ちる。必ずバイト列で受けて自前で decode する。"""
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception as e:
        sys.stderr.write("validate_card: フック入力を読めませんでした: %r\n" % (e,))
        return None


def main_hook():
    """PostToolUse フック。触られたファイルだけを見て、無関係なら黙って終わる。"""
    payload = read_hook_payload()
    if payload is None:
        return 0
    path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not path or not is_card_source(path):
        return 0

    src_name = os.path.basename(os.path.abspath(path))
    errors, notices = report([src_name], include_git=False)

    if errors:
        sys.stderr.write(
            "ポケットカードの検証に失敗しました。配信すると壊れます。\n\n"
            + "\n".join("  ✗ " + e for e in errors)
            + "\n\n修正してから build.py を実行してください。\n")
        return 2

    if notices:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext":
                "ポケットカードの配信チェーンに残作業があります:\n"
                + "\n".join("  ・" + n for n in notices)
                + "\n同じターンで build.py の実行と push まで完走してください"
                  "（push は dangerouslyDisableSandbox: true で）。",
        }}, ensure_ascii=False))
    return 0


def main_stop():
    """Stop フック。ターンを終える前に配信チェーン全体を見る。

    Write/Edit を通さず Bash で書いたカードはこちらでしか捕まらない。
    未 commit / 未 push は止めない（作業途中の通常状態なので止めると邪魔になる）。
    """
    payload = read_hook_payload() or {}
    if payload.get("stop_hook_active"):
        return 0  # 無限ループ防止：一度差し戻した後は止めない

    targets = sorted(f for f in os.listdir(VAULT)
                     if is_card_source(os.path.join(VAULT, f)))
    errors, notices = report(targets, include_git=False, verbose_unpublished=False)
    blocking = errors + [n for n in notices if "build.py" in n]
    if not blocking:
        return 0

    sys.stderr.write(
        "ポケットカードの配信チェーンが完走していません。"
        "このまま終わるとスマホ側に反映されません。" + NEWLINE * 2
        + NEWLINE.join("  ・" + b for b in blocking) + NEWLINE * 2
        + "修正 → python pocket-cards-site/build.py → 実機確認 → commit && push "
          "（push は dangerouslyDisableSandbox: true）まで進めてください。" + NEWLINE)
    return 2


if __name__ == "__main__":
    _utf8_stdio()
    if "--stop" in sys.argv:
        sys.exit(main_stop())
    if "--hook" in sys.argv:
        sys.exit(main_hook())
    sys.exit(main_cli([a for a in sys.argv[1:] if not a.startswith("--")]))
