# -*- coding: utf-8 -*-
"""
アプリアイコンを生成する（Pillow 必須）。デザインを変えた時だけ実行すればよい。

    python make_icons.py
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "icons")
TEAL = (14, 124, 134, 255)
WHITE = (255, 255, 255, 255)
SS = 4  # スーパーサンプリング倍率（縁のジャギーを消す）


def draw_cross(d, s, cx, cy, span, thick):
    """角丸の十字（医療のマーク）を描く。"""
    r = thick / 2.0
    d.rounded_rectangle([cx - thick / 2, cy - span / 2, cx + thick / 2, cy + span / 2],
                        radius=r, fill=WHITE)
    d.rounded_rectangle([cx - span / 2, cy - thick / 2, cx + span / 2, cy + thick / 2],
                        radius=r, fill=WHITE)


def make(size, maskable=False, opaque=False):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if maskable or opaque:
        d.rectangle([0, 0, s, s], fill=TEAL)          # 全面（マスクで削られる前提）
    else:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.22, fill=TEAL)

    # maskable は内側80%のセーフゾーンに収める
    span = s * (0.44 if maskable else 0.58)
    thick = s * (0.148 if maskable else 0.195)
    draw_cross(d, s, s / 2.0, s / 2.0, span, thick)

    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    specs = [
        ("icon-192.png", 192, False, False),
        ("icon-512.png", 512, False, False),
        ("icon-maskable-512.png", 512, True, False),
        ("icon-180.png", 180, False, True),
    ]
    for name, size, maskable, opaque in specs:
        p = os.path.join(OUT, name)
        make(size, maskable, opaque).save(p, "PNG", optimize=True)
        print("  icons/%-24s %5d bytes" % (name, os.path.getsize(p)))
