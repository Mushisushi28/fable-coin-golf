#!/usr/bin/env python3
"""Generate the username dialog's raster art - original, build-time.

The development builds used raster art for three resources:

- `button_bg.9.png`   - the Save/Cancel button background (a 9-patch)
- `flourish_gold.png` - the dialog's gold corner ornaments
- `icon_background.png` - the adaptive launcher icon's background

That art was derived from the game's own menu art, so - like every
other game asset - it is NOT distributed in this repository. This
script generates original substitutes at build time, in the same
design language (the parchment/gold palette the dialog's own XML
drawable uses: parchment #F6E4B1, gold #C9A227, dark gold #8A6D1F):

- the button is a parchment panel with a double gold border, drawn as
  a true 9-patch (1px marker border; stretch regions along both axes;
  a full-size content box, so labels can never be clipped by padding);
- the flourish is a simple gold corner ornament (an L with a diamond);
- the icon background is a parchment field with a gold frame.

Pure standard library (zlib PNG encoder) - no Pillow required.

Usage: generate_dialog_art.py <Resources-dir>
Writes drawable/button_bg.9.png, drawable/flourish_gold.png and
mipmap-<density>/icon_background.png for the five standard densities.
"""
import os
import struct
import sys
import zlib

PARCHMENT = (246, 228, 177, 255)
PARCHMENT_EDGE = (232, 205, 145, 255)
GOLD = (201, 162, 39, 255)
GOLD_DARK = (138, 109, 31, 255)
TRANSPARENT = (0, 0, 0, 0)
BLACK = (0, 0, 0, 255)


class Canvas:
    def __init__(self, w, h, colour=TRANSPARENT):
        self.w, self.h = w, h
        self.px = bytearray(bytes(colour) * (w * h))

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            self.px[i:i + 4] = bytes(colour)

    def rect(self, x0, y0, x1, y1, colour):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, colour)

    def frame(self, x0, y0, x1, y1, width, colour):
        for i in range(width):
            self.rect(x0 + i, y0 + i, x1 - i, y0 + i, colour)
            self.rect(x0 + i, y1 - i, x1 - i, y1 - i, colour)
            self.rect(x0 + i, y0 + i, x0 + i, y1 - i, colour)
            self.rect(x1 - i, y0 + i, x1 - i, y1 - i, colour)

    def save(self, path):
        raw = b""
        stride = self.w * 4
        for y in range(self.h):
            raw += b"\x00" + bytes(self.px[y * stride:(y + 1) * stride])

        def chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw, 9))
               + chunk(b"IEND", b""))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(png)


def button_bg():
    # 407x114 including the 1px 9-patch marker border.
    c = Canvas(407, 114)
    # Art area: 1..405 x 1..112.
    c.rect(1, 1, 405, 112, PARCHMENT)
    c.frame(1, 1, 405, 112, 5, GOLD)
    c.frame(7, 7, 399, 106, 2, GOLD_DARK)
    # Slight top-light / bottom-shade bands inside the border.
    c.rect(9, 9, 397, 26, (250, 238, 199, 255))
    c.rect(9, 88, 397, 104, PARCHMENT_EDGE)
    c.frame(1, 1, 405, 112, 5, GOLD)  # border back on top of the bands
    # 9-patch markers: top = horizontal stretch, left = vertical stretch,
    # right/bottom = content box (kept generous: full interior).
    for x in range(30, 377):
        c.set(x, 0, BLACK)
    for y in range(24, 90):
        c.set(0, y, BLACK)
    for y in range(12, 102):
        c.set(406, y, BLACK)
    for x in range(12, 395):
        c.set(x, 113, BLACK)
    return c


def flourish():
    # 70x70 corner ornament for the bottom-left corner (the layout
    # mirrors it for the other three corners).
    c = Canvas(70, 70)
    # L: vertical bar up the left, horizontal bar along the bottom.
    c.rect(2, 18, 8, 67, GOLD)
    c.rect(2, 61, 52, 67, GOLD)
    c.rect(10, 26, 13, 60, GOLD_DARK)
    c.rect(10, 57, 44, 60, GOLD_DARK)
    # Diamond where the bars meet.
    cx, cy, r = 20, 44, 9
    for y in range(cy - r, cy + r + 1):
        span = r - abs(y - cy)
        c.rect(cx - span, y, cx + span, y, GOLD)
    c.set(cx, cy, GOLD_DARK)
    # Small dot finials at the bar ends.
    for (x, y) in [(5, 12), (58, 64)]:
        for dy in range(-3, 4):
            span = 3 - abs(dy)
            c.rect(x - span, y + dy, x + span, y + dy, GOLD)
    return c


def icon_background(size):
    c = Canvas(size, size, PARCHMENT)
    m = max(4, size // 24)
    c.frame(0, 0, size - 1, size - 1, m, GOLD)
    c.frame(m * 2, m * 2, size - 1 - m * 2, size - 1 - m * 2, max(2, m // 2), GOLD_DARK)
    return c


DENSITIES = {  # adaptive-icon canvas is 108dp
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    res = argv[1]
    button_bg().save(os.path.join(res, "drawable", "button_bg.9.png"))
    flourish().save(os.path.join(res, "drawable", "flourish_gold.png"))
    for folder, size in DENSITIES.items():
        icon_background(size).save(os.path.join(res, folder, "icon_background.png"))
    print(f"generated dialog + icon art -> {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
