#!/usr/bin/env python3
"""Item pictures for the Monastery of the Still Hand (Nov 19), sprites 44556-44559 into <client>/GFX (all drawn):
    monastery.py <client folder>
44556 Abbot's Prayer Beads (a loop of dark wooden beads, a pale tassel), 44557 Silent Hand Sash (a folded black sash,
red stripes at its ends), 44558 Monk's Wrap (a coiled belt of saffron cloth), 44559 Amulet of the Still Mind (a pale
jade disc with a hole, on a dark cord)."""
import os, sys, math
from PIL import Image
C = sys.argv[1]; G = os.path.join(C, 'GFX')
def clamp(c, a=255): return tuple(max(0, min(255, int(v))) for v in c) + (a,)
def outline(im, col=(20, 18, 16)):
    px = im.load(); W, H = im.size; e = []
    for y in range(H):
        for x in range(W):
            if px[x, y][3]: continue
            if any(0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy][3] > 128 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))): e.append((x, y))
    for x, y in e: px[x, y] = col + (255,)
    return im
def new(): return Image.new('RGBA', (32, 32), (0, 0, 0, 0))

# 44556 prayer beads
im = new(); px = im.load()
for i in range(18):
    a = 2 * math.pi * i / 18; bx, by = 15.5 + 9 * math.cos(a), 17 + 6 * math.sin(a)
    for y in range(32):
        for x in range(32):
            d = math.hypot(x - bx, (y - by) * 1.1)
            if d <= 1.7:
                lit = 1.0 - 0.45 * d / 1.7 + (0.3 if (x - bx) < 0 and (y - by) < 0 else 0)
                px[x, y] = clamp([110 * lit, 66 * lit, 34 * lit])
for y in range(23, 31):                                                     # the tassel
    for x in range(14, 18):
        if y > 25 or x in (15, 16): px[x, y] = clamp([228, 214, 180] if (x + y) % 2 else [200, 184, 150])
outline(im).save(os.path.join(G, '44556.png'))

# 44557 the sash, folded in three
im = new(); px = im.load()
for y in range(32):
    for x in range(32):
        for k in range(3):
            y0 = 12 + k * 4 - (x - 4) * 0.12
            if 4 <= x <= 27 and y0 <= y <= y0 + 4.5:
                lit = 0.8 + 0.35 * (1 - (y - y0) / 4.5) - 0.08 * k
                c = [34, 32, 38]
                if x < 7 or x > 24: c = [170, 28, 24] if (x % 3) else [120, 20, 18]
                px[x, y] = clamp([v * lit for v in c])
outline(im).save(os.path.join(G, '44557.png'))

# 44558 the Monk's Wrap: a coil of saffron cloth, folds across it
im = new(); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 12.5, (y - 19.5) / 7.5; r = math.hypot(dx, dy)
        if 0.6 <= r <= 1.0:
            lit = 0.75 + 0.3 * (-dx * 0.6 - dy * 0.8) / max(r, 0.01) * (0.5 if r < 0.8 else 1.0)
            a = math.atan2(dy, dx); fold = 0.88 if int((a + 4) * 5) % 2 else 1.0
            if r > 0.94 or r < 0.66: lit *= 0.65
            c = (196, 104, 28) if dy < 0 else (226, 132, 40)
            px[x, y] = clamp([v * lit * fold for v in c])
for y in range(21, 30):                                                     # the knot and its two ends
    for x in range(13, 19):
        if abs(x - 15.5) + abs(y - 24) * 0.7 < 3.5: px[x, y] = clamp([236, 150, 52] if x < 16 else [190, 100, 26])
for x, y in ((12, 29), (12, 30), (19, 29), (20, 30)): px[x, y] = clamp([210, 118, 34])
outline(im).save(os.path.join(G, '44558.png'))

# 44559 Amulet of the Still Mind: a pale jade disc with a hole, a dark cord
im = new(); px = im.load()
for i in range(70):
    a = 2 * math.pi * i / 70
    if math.sin(a) > 0.9: continue
    x, y = 15.5 + 9 * math.cos(a), 13 + 7 * math.sin(a); px[int(round(x)), int(round(y))] = clamp([60, 44, 30])
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 6.0, (y - 23.5) / 5.4; r = math.hypot(dx, dy)
        if 0.3 <= r <= 1.0:
            lit = 0.85 + 0.3 * max(0, -dx * 0.6 - dy * 0.8) - 0.15 * r
            px[x, y] = clamp([140 * lit, 196 * lit, 160 * lit])
for y in (18, 19): px[15, y] = clamp([60, 44, 30]); px[16, y] = clamp([60, 44, 30])
outline(im).save(os.path.join(G, '44559.png'))
print('monastery pictures 44556-44559')
