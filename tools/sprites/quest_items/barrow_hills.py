#!/usr/bin/env python3
"""Barrow Hills item pictures (Nov 17), drawn (the RPG Pack necklaces are thin chains, the parchment is no stone):
    44533 Rune-Carved Tablet   a grey stone slab with a rounded top, carved runes
    44534 Ulfgar's Torc        a thick open neck-ring of twisted gold with knob ends (the quest item and the amulet share it)

    barrow_hills.py <Client folder> [--out <folder>]"""
import os, sys, math, random
from PIL import Image, ImageDraw, ImageFilter
C = sys.argv[1]; OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(C, 'GFX')
S = 4; N = 32 * S


def finish(big, nr):
    """4x drawing -> 32x32 with a soft dark outline, like the game's items"""
    im = big.resize((32, 32), Image.LANCZOS)
    a = im.split()[3].point(lambda v: 255 if v > 90 else 0)
    im.putalpha(a)
    ring = a.filter(ImageFilter.MaxFilter(3))
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    edge = Image.new('RGBA', (32, 32), (20, 14, 8, 255)); out.paste(edge, (0, 0), ring)
    out.alpha_composite(im)
    out.save(os.path.join(OUT, '%05d.png' % nr)); print(nr, out.getbbox())


def shade(base, k):
    return tuple(max(0, min(255, int(c * k))) for c in base) + (255,)


def tablet():
    random.seed(7)
    big = Image.new('RGBA', (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    # the slab: front face leaning back a little, a thickness on the right
    x0, x1, top, bot, r = 34, 86, 22, 112, 26
    th = 12
    def face(dx, dy, col):
        d.rectangle((x0 + dx, top + r + dy, x1 + dx, bot + dy), fill=col)
        d.pieslice((x0 + dx, top + dy, x1 + dx, top + 2 * r + dy + 1), 180, 360, fill=col)
    face(th, -th // 2, (74, 76, 80, 255))              # back / side
    stone = (132, 134, 138)
    face(0, 0, stone + (255,))
    px = big.load()
    for y in range(N):                                  # stone grain and light from the upper left
        for x in range(N):
            p = px[x, y]
            if p[3] and p[:3] == stone:
                k = 1.12 - 0.35 * (x - x0) / (x1 - x0) - 0.15 * (y - top) / (bot - top) + random.uniform(-0.07, 0.07)
                px[x, y] = shade(stone, k)
    for k in range(5):                                  # chips on the edge
        cx, cy = random.choice([(x0, random.randint(top + r, bot)), (x1, random.randint(top + r, bot))]); d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(0, 0, 0, 0))
    # runes: angular strokes in rows, cut dark with a light lower edge
    rows = [44, 60, 76, 92]
    for ry in rows:
        x = x0 + 8
        while x < x1 - 10:
            w = random.choice([6, 8, 10]); h = 11
            strokes = random.choice([[(0, 0, 0, h), (0, 0, w, h // 2)], [(0, 0, w, h), (w, 0, 0, h)], [(w // 2, 0, w // 2, h), (0, 3, w, 3)],
                                     [(0, 0, 0, h), (0, h // 2, w, 0), (0, h // 2, w, h)], [(0, h, w // 2, 0), (w // 2, 0, w, h)]])
            for a, b, c, e in strokes:
                d.line((x + a, ry + b + 1, x + c, ry + e + 1), fill=(186, 188, 192, 255), width=2)
                d.line((x + a, ry + b, x + c, ry + e), fill=(36, 38, 44, 255), width=3)
            x += w + 7
    finish(big, 44533)


def torc():
    big = Image.new('RGBA', (N, N), (0, 0, 0, 0)); px = big.load()
    cx, cy, rx, ry = 64, 66, 44, 26            # the ring seen from above at the game's angle
    gap = 0.55                                  # the opening, at the front (bottom)
    gold = (206, 150, 52)
    pts = []
    for i in range(1400):
        t = i / 1400 * 2 * math.pi
        if abs(((t - math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < gap: continue      # skip the front
        pts.append(t)
    # draw back half first, then the front half over it
    for front in (False, True):
        for t in pts:
            if (math.sin(t) > 0) != front: continue
            x, y = cx + rx * math.cos(t), cy + ry * math.sin(t)
            thick = 8.5
            twist = 0.5 + 0.5 * math.sin(t * 22)          # the twisted strands
            for oy in range(-10, 11):
                for ox in range(-10, 11):
                    dd = math.hypot(ox, oy)
                    if dd > thick: continue
                    lx = -(ox + oy) / (thick * 1.414)        # light from the upper left
                    k = 0.62 + 0.55 * max(0, lx) + 0.25 * (1 - dd / thick) - 0.22 * twist * (dd / thick) - (0.18 if not front else 0)
                    X, Y = int(x + ox), int(y + oy)
                    if 0 <= X < N and 0 <= Y < N: px[X, Y] = shade(gold, k)
    # knob ends either side of the gap
    for s in (-1, 1):
        t = math.pi / 2 + s * gap
        x, y = cx + rx * math.cos(t), cy + ry * math.sin(t)
        for oy in range(-14, 15):
            for ox in range(-14, 15):
                dd = math.hypot(ox, oy)
                if dd > 12: continue
                k = 0.7 + 0.6 * max(0, -(ox + oy) / 17) + 0.3 * (1 - dd / 12)
                X, Y = int(x + ox), int(y + oy)
                if 0 <= X < N and 0 <= Y < N: px[X, Y] = shade((196, 136, 44), k)
        d = ImageDraw.Draw(big); d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(140, 22, 26, 255)); d.ellipse((x - 3, y - 3, x - 1, y - 1), fill=(236, 120, 110, 255))   # a garnet in each end
    finish(big, 44534)


tablet(); torc()
