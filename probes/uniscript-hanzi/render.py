#!/usr/bin/env python3
"""Renders composed hanzi from Uniscript Hanzi beside the real glyphs of Noto Sans CJK, headlessly with hb-view.

  python3 probes/uniscript-hanzi/render.py [ot|coretext]   → probes/uniscript-hanzi/*.png
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
HANZI = os.path.join(HERE, "../../fonts/dist/UniscriptHanzi-Regular.otf")
NOTO = os.path.expanduser("~/Library/Fonts/NotoSansCJK-Regular.ttf")
LABEL_FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"  # Latin and CJK, for labels showing IDS
SIZE = 150
CELL = 200
REFERENCES = [("界", "⿱田介"), ("林", "⿰木木"), ("狗", "⿰犭句"), ("草", "⿱艹早"), ("思", "⿱田心"), ("国", "⿴囗玉"), ("连", "⿺辶车")]
INVENTED = [  # none of these is a Unicode character (checked against cjkvi-ids)
    ("⿱艹猫", "<:above 艹 猫>", "catnip"),
    ("⿴囗猫", "raw IDS", "cat in a box"),
    ("⿰木电", "<:beside 木 电>", "electric tree"),
    ("⿰鱼电", "<:beside 鱼 电>", "electric eel"),
    ("⿸广猫", "raw IDS", "cat house"),
    ("⿰讠尤", "<:beside 讠 尤>", "the user's first try"),
    ("⿱艹⿰氵火", "<:above 艹 ⿰氵火>", "nested: only the 50 most used parts nest"),
    ("⿰火⿱日月", "<:beside 火 ⿱日月>", "nested"),
]


def shape_image(font, text, shaper):
    path = os.path.join(HERE, "cell.png")
    subprocess.run(["hb-view", "--shapers=" + shaper, "--font-size=%d" % SIZE, "--margin=10", "-o", path, font, text], check=True)
    return Image.open(path).convert("L")


def naive_halves(sequence):
    """What plain scaling gives: both parts squeezed into exact halves, strokes thinned with them."""
    operator, first, second = sequence
    a, b = (shape_image(NOTO, part, "ot") for part in (first, second))
    width, height = a.size
    if operator == "⿰":
        parts, boxes = [a.resize((width // 2, height)), b.resize((width // 2, height))], [(0, 0), (width // 2, 0)]
    else:
        parts, boxes = [a.resize((width, height // 2)), b.resize((width, height // 2))], [(0, 0), (0, height // 2)]
    canvas = Image.new("L", (width, height), 255)
    for part, box in zip(parts, boxes):
        canvas.paste(part, box)
    return canvas


def sheet(rows, columns, name):
    label = ImageFont.truetype(LABEL_FONT, 22)
    image = Image.new("L", (CELL * len(columns), (CELL + 40) * (len(rows) + 1)), 255)
    draw = ImageDraw.Draw(image)
    for y, cells in enumerate(rows):
        for x, cell in enumerate(cells):
            top = 40 + y * (CELL + 40)
            if isinstance(cell, str):
                draw.text((x * CELL + 10, top + CELL // 2), cell, font=label, fill=0)
            else:
                image.paste(cell, (x * CELL + (CELL - cell.width) // 2, top + (CELL - cell.height) // 2))  # same scale everywhere
    for x, title in enumerate(columns):  # last, so tall cells do not cover it
        draw.rectangle((x * CELL, 0, (x + 1) * CELL, 38), fill=255)
        draw.text((x * CELL + 10, 10), title, font=label, fill=0)
    path = os.path.join(HERE, name)
    image.save(path)
    print("wrote", path)


def main(shaper="ot"):
    sheet([[shape_image(NOTO, real, "ot"), shape_image(HANZI, ids, shaper), naive_halves(ids) if len(ids) == 3 and ids[0] in "⿰⿱" else "",
            "%s = %s" % (real, ids)] for real, ids in REFERENCES],
          ["Noto (real)", "composed", "naive halves", ""], "reference_%s.png" % shaper)
    sheet([[shape_image(HANZI, ids, shaper), ids, typed, meaning] for ids, typed, meaning in INVENTED],
          ["composed", "IDS", "uniscript", ""], "invented_%s.png" % shaper)
    os.remove(os.path.join(HERE, "cell.png"))


if __name__ == "__main__":
    main(*sys.argv[1:])
