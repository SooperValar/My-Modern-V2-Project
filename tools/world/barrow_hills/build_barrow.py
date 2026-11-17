#!/usr/bin/env python3
"""The Barrow Hills (Nov 16): north of Fenwatch (its north gate's road), First Lieutenant. Dry grass upland with a ring
of standing stones, six small barrows, the Scribe's barrow and the King's Barrow (round tombs of dark rock, dark inside).
A dead end: the way on to Stonehold is south, through the Lizard Hatcheries (TODO "Space and routes").

    build_barrow.py <.dat folder>      (game stopped; tools/world/arealib.py)      then place_barrow.py"""
import sys, os, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1], seed=1120)
X0, X1, Y0, Y1 = 320, 409, 768, 852
def edge(y): return 404 + int(round(2.5 * math.sin(y / 5.0) + 1.5 * math.sin(y / 2.1 + 1)))       # grass north of this, Fenwatch's marsh south
road = set()
for x in range(372, 424):
    w = int(round(1.2 * math.sin((x - 372) / 6.0))) if x < 410 else 0
    for y in (800, 801, 802): road.add((x, y + w))
CIRCLE = (366, 805)                               # the standing stones
BARROWS = [  # centre x, y, radius x, y, door side ('s' = toward Fenwatch ...), name
    (337, 806, 10, 12, 's', 'king'), (352, 782, 6, 7, 'e', 'scribe'),
    (384, 782, 4, 5, 's', ''), (392, 822, 4, 5, 'w', ''), (374, 836, 5, 4, 'w', ''), (350, 834, 4, 5, 'n', ''), (336, 778, 4, 4, 's', ''), (380, 812, 4, 4, 'n', '')]
ell = lambda x, y, cx, cy, rx, ry: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
def barrow_at(x, y, pad=0.0):
    for cx, cy, rx, ry, side, name in BARROWS:
        e = ell(x, y, cx, cy, rx + pad, ry + pad)
        if e <= 1.0: return (cx, cy, rx, ry, side, name)
    return None
def door(b):
    cx, cy, rx, ry, side, name = b
    return {'s': [(cx + rx, cy), (cx + rx - 1, cy)], 'n': [(cx - rx, cy), (cx - rx + 1, cy)], 'e': [(cx, cy + ry), (cx, cy + ry - 1)], 'w': [(cx, cy - ry), (cx, cy - ry + 1)]}[side]
doors = {p for b in BARROWS for p in door(b)}
paths = set(road)
def trail(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(n + 1):
        x, y = round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)
        for d in ((0, 0), (1, 0), (0, 1)): paths.add((x + d[0], y + d[1]))
trail(372, 801, 349, 806); trail(366, 800, 358, 790); trail(358, 790, 353, 790)
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if x > edge(y) and (x, y) not in road: continue                 # Fenwatch's marsh stays
        A.clear(x, y)
        b = barrow_at(x, y)
        if b and (x, y) not in doors:
            inside = ell(x, y, b[0], b[1], b[2] - 1.2, b[3] - 1.2) <= 1.0
            A.op(op='floor', x=x, y=y, s=CAVE, set=False)
            if inside: A.op(op='flag', x=x, y=y, bit=2, mode=1)
            else: A.op(op='object', x=x, y=y, s=124, block=3)           # the dark rock wall
            continue
        if (x, y) in doors: A.op(op='floor', x=x, y=y, s=CAVE, set=False); continue
        if (x, y) in paths: A.op(op='floor', x=x, y=y, s=random.choice(PATH if (x, y) in road or random.random() < 0.8 else GRASS), set=False); continue
        A.op(op='floor', x=x, y=y, s=random.choice(GRASS), set=False)
        if barrow_at(x, y, 2.5) or abs(x - CIRCLE[0]) + abs(y - CIRCLE[1]) < 9: continue
        d = min(x - X0, y - Y0, Y1 - y); r = random.random()
        near_path = any((x + dx, y + dy) in paths for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if near_path: continue
        if d <= 2:
            if r < 0.92: A.op(op='object', x=x, y=y, s=random.choice(PINE + OLDTREES), block=3)
        elif r < 0.020: A.op(op='object', x=x, y=y, s=random.choice(DEAD), block=1)
        elif r < 0.032: A.op(op='object', x=x, y=y, s=random.choice(OLDTREES + PINE), block=3)
        elif r < 0.050: A.op(op='object', x=x, y=y, s=random.choice(ROCKS), block=3)
        elif r < 0.058: A.op(op='object', x=x, y=y, s=random.choice(STUMPS), block=1)
A.run('Barrow Hills: ground, barrows, trees')
for x in range(402, 412):                         # open Fenwatch marsh's north tree wall at the road, thin it elsewhere
    for y in range(797, 806): A.op(op='erase', x=x, y=y)
for x in range(404, 410):
    for y in range(Y0, Y1 + 1):
        t = A.tile(x, y)
        if t[1] in PINE + WILLOW + OLDTREES and random.random() < 0.7: A.op(op='erase', x=x, y=y)
        if x in (407, 408): A.op(op='flag', x=x, y=y, bit=5, mode=1)       # no-monster strip toward Fenwatch
A.run('open the tree wall, no-monster strip')
for k in range(10):                               # the standing stones: a ring of rock pillars, a gap toward the road
    a = k * math.pi / 5 + 0.3; x, y = round(CIRCLE[0] + 5.2 * math.sin(a)), round(CIRCLE[1] + 5.2 * math.cos(a))
    if (x, y) not in paths: A.op(op='object', x=x, y=y, s=ROCKS[k % 4], block=3)
A.run('standing stones')
P = [(FIREBOWL, 337, 800), (FIREBOWL, 337, 812), (FIREBOWL, 331, 806), (BONES, 340, 803), (BONES, 334, 810), (BONES, 352, 780), (TORCH, 352, 784), (BONES, 366, 805),
     (TOMBSTONE, 362, 812), (TOMBSTONE, 371, 797), (TOMBSTONE, 389, 795), (TOMBSTONE, 396, 812), (TOMBSTONE, 345, 822), (TOMBSTONE, 328, 792), (TOMBSTONE, 360, 842), (BONES, 384, 782), (BONES, 392, 822)]
A.place(*P)
A.marsh_edges((398, Y0, 412, Y1))
for b in BARROWS:
    if b[5]: A.zone(b[0] - b[2], b[1] - b[3], b[0] + b[2], b[1] + b[3], "King's Barrow" if b[5] == 'king' else "Scribe's Barrow")
A.zone(X0, Y0, 403, Y1, 'Barrow Hills')
A.save()
