#!/usr/bin/env python3
"""New rings (Topaz, Amethyst, Diamond) and spell books (Initiate .. Archmage), recoloured from the game's own
sprites in art/rings_books/ (Golden Emerald rings 182/185/188/629 and the Huge ring's glow 1925-1929; the Book of
Wisdom 16912, its numeral replaced by a gold emblem).

    rings_books.py <client folder>      writes <client>/GFX/NNNNN.png

Numbers: Topaz 18240-18248, Amethyst 18250-18258, Diamond 18260-18268 (small, medium, big, huge, then the huge
ring's 5 glow frames); spell books 18270-18274 (red, yellow, green, blue, purple); the loose stones (from the
emeralds 236/235/234/632) Topaz 18276-18279, Amethyst 18280-18283, Diamond 18284-18287 (small, medium, big, huge).
"""
import colorsys, os, sys
from PIL import Image

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art', 'rings_books')
KEY = (255, 0, 255)
GEMS = [('topaz', 18240, 0.11, 1.0, 1.15), ('amethyst', 18250, 0.79, 0.85, 1.0), ('diamond', 18260, 0.58, 0.12, 1.35)]
RING_SRC = [182, 185, 188, 629, 1925, 1926, 1927, 1928, 1929]
GEM_SRC = [236, 235, 234, 632]
GEM_BASE = {'topaz': 18276, 'amethyst': 18280, 'diamond': 18284}
BOOKS = [(18270, 0.0, 1.0, 1.0), (18271, 0.14, 1.0, 1.55), (18272, 0.33, 0.9, 1.15), (18273, 0.61, 0.95, 1.25), (18274, 0.79, 0.8, 1.2)]


def load(n):
    return Image.open(os.path.join(ART, '%d.png' % n)).convert('RGBA')


def recolor(im, test, hue, sat, val):
    out = im.copy()
    px = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0 or (r, g, b) == KEY or not test(r, g, b):
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            r2, g2, b2 = colorsys.hsv_to_rgb(hue, min(1, s * sat), min(1, v * val))
            px[x, y] = (round(r2 * 255), round(g2 * 255), round(b2 * 255), a)
    return out


green = lambda r, g, b: g > r + 15 and g > b + 15
red = lambda r, g, b: r > g + 40 and r > b + 40


def main():
    gfx = os.path.join(sys.argv[1], 'GFX')
    os.makedirs(gfx, exist_ok=True)
    n = 0
    for name, base, hue, sat, val in GEMS:
        for k, src in enumerate(RING_SRC):
            recolor(load(src), green, hue, sat, val).save(os.path.join(gfx, '%05d.png' % (base + k))); n += 1
        for k, src in enumerate(GEM_SRC):
            recolor(load(src), green, hue, sat, val).save(os.path.join(gfx, '%05d.png' % (GEM_BASE[name] + k))); n += 1
    book = load(16912)
    px = book.load()
    for y in range(17, 21):                      # the numeral "I" -> cover colour
        for x in range(11, 16):
            px[x, y] = px[9, y]
    for base, hue, sat, val in BOOKS:
        im = recolor(book, red, hue, sat, val)
        p2 = im.load()
        for (x, y) in [(13, 16), (12, 17), (13, 17), (14, 17), (11, 18), (12, 18), (13, 18), (14, 18), (15, 18),
                       (12, 19), (13, 19), (14, 19), (13, 20)]:   # a small gold emblem (after the recolour)
            p2[x, y] = (255, 236, 140, 255) if (x, y) == (13, 18) else (226, 178, 52, 255)
        im.save(os.path.join(gfx, '%05d.png' % base)); n += 1
    print('%d sprites written to %s' % (n, gfx))


if __name__ == '__main__':
    main()
