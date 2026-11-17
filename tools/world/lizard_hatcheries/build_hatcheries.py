#!/usr/bin/env python3
"""The Lizard Hatcheries (Nov 17): south of Fenwatch (its south gate's road), Captain. A warm lowland of grass, golden sand
and clear pools on both sides of the **through road to Stonehold** (dusty path, y ~801-809, leaving the area's south edge
at x 595 open for the pass). West of the road: the Hatchery, a sandstone compound (courtyard with a warm pool, three egg
chambers, the Archmage's sanctum). East of the road: egg pits on the sand among the pools, and at the far end the
Broodmother's Chamber (temple stone).

    build_hatcheries.py <.dat folder>      (game stopped; tools/world/arealib.py)      then place_hatcheries.py"""
import sys, os, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1], seed=1122)
X0, X1, Y0, Y1 = 495, 595, 765, 860
GOLD = [35250, 35251, 35252, 35253]; WATER = [35500, 35501, 35502, 35503]
COMPOUND = (512, 768, 572, 797)                 # the Hatchery (x0, y0, x1, y1)
COURT = (530, 779, 556, 796)                    # its open courtyard
POOL_IN = (539, 783, 547, 790)
ROOMS = [((512, 768, 529, 783), (529, 775), 'sanctum'), ((512, 783, 529, 797), (529, 790), 'eggs'),
         ((556, 768, 572, 783), (556, 775), 'eggs'), ((556, 783, 572, 797), (556, 790), 'eggs')]   # box, door gap (on the courtyard side), kind
GATE = [(541, 797), (542, 797), (543, 797)]      # the compound's gate, toward the road
BROOD = (572, 822, 592, 848)                     # the Broodmother's Chamber
BROOD_DOOR = [(581, 822), (582, 822), (583, 822)]
def road_y(x): return 801 + min(5, max(0, (x - 495) // 4)) + int(round(0.8 * math.sin(x / 7.0)))
road = {(x, road_y(x) + d) for x in range(486, X1 + 1) for d in (0, 1, 2)}
spur = {(x, y) for x in (541, 542, 543) for y in range(797, road_y(542) + 1)}
paths = road | spur
def blob(cx, cy, r, rough=0.35):
    out = set(); ph = random.random() * 6
    for x in range(int(cx - r - 2), int(cx + r + 3)):
        for y in range(int(cy - r - 2), int(cy + r + 3)):
            a = math.atan2(y - cy, x - cx); rr = r * (1 + rough * 0.5 * (math.sin(3 * a + ph) + 0.6 * math.sin(5 * a + 2 * ph)))
            if math.hypot(x - cx, y - cy) <= rr + random.uniform(-0.7, 0.7): out.add((x, y))      # a ragged rim
    return out
inbox = lambda x, y, b: b[0] <= x <= b[2] and b[1] <= y <= b[3]
near = lambda x, y, b, p: b[0] - p <= x <= b[2] + p and b[1] - p <= y <= b[3] + p
# outdoor ground: sand patches and pools east of the road, a few west of the compound
sand, water = set(), set()
for cx, cy, r in [(520, 828, 6), (538, 845, 7), (553, 826, 5), (562, 851, 5), (507, 846, 4), (584, 812, 3.5), (503, 780, 4), (580, 772, 4)]: sand |= blob(cx, cy, r)
for cx, cy, r in [(528, 838, 3.5), (546, 831, 3), (515, 852, 2.5), (558, 840, 3), (570, 812, 2.2), (588, 783, 2.5)]: water |= blob(cx, cy, r, 0.25)
PITS = [(520, 828), (538, 845), (553, 826), (562, 851)]                  # egg pits: in the middle of the big sand patches
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if (x, y) in paths: continue
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0)              # the void here was flagged indoors
        if near(x, y, COMPOUND, 0) or near(x, y, BROOD, 0): continue
        if (x, y) in water:
            A.op(op='floor', x=x, y=y, s=random.choice(WATER), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1); continue
        if (x, y) in sand:
            A.op(op='floor', x=x, y=y, s=random.choice(GOLD), set=False)
            if random.random() < 0.015 and all(abs(x - a) + abs(y - b) > 4 for a, b in PITS): A.op(op='object', x=x, y=y, s=random.choice(STUMPS), block=1)
            continue
        A.op(op='floor', x=x, y=y, s=random.choice(GRASS), set=False)
        if near(x, y, COMPOUND, 2) or near(x, y, BROOD, 2): continue
        if any((x + dx, y + dy) in paths or (x + dx, y + dy) in water for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            if (x + 1, y) in water or (x, y + 1) in water or (x - 1, y) in water or (x, y - 1) in water:
                if random.random() < 0.35: A.op(op='object', x=x, y=y, s=random.choice(REEDS), block=0)
            continue
        d = min(y - Y0, Y1 - y, X1 - x); r = random.random()
        gap = X1 - x <= 3 and abs(y - road_y(x) - 1) <= 4                  # the road leaves the area open here
        if d <= 2 and not gap:
            if r < 0.9: A.op(op='object', x=x, y=y, s=random.choice(WILLOW + OLDTREES), block=3)
        elif r < 0.022: A.op(op='object', x=x, y=y, s=random.choice(WILLOW + OLDTREES), block=3)
        elif r < 0.030: A.op(op='object', x=x, y=y, s=random.choice(DEAD), block=1)
for x, y in paths:
    if X0 - 9 <= x <= X1: A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='floor', x=x, y=y, s=random.choice(DUSTY), set=False)
A.run('Lizard Hatcheries: ground, pools, road')
for x in range(488, 496):                         # open Fenwatch marsh's south tree wall at the road; a no-monster strip there
    for y in range(796, 810):
        if abs(y - road_y(x) - 1) <= 3: A.op(op='erase', x=x, y=y)
for y in range(Y0, Y1 + 1):
    for x in (495, 496): A.op(op='flag', x=x, y=y, bit=5, mode=1)
A.run('open the tree wall, no-monster strip')
# the Hatchery: sandstone outer wall, temple-stone rooms, an open courtyard with a warm pool
A.house(COMPOUND, W_SANDSTONE, FLAGSTONE)
for b, door, kind in ROOMS: A.house(b, W_TEMPLE, SETTS if kind == 'sanctum' else FLAGSTONE)
for x in range(COMPOUND[0], COMPOUND[2] + 1):     # the outside stays sandstone all round
    for y in range(COMPOUND[1], COMPOUND[3] + 1):
        if (x in (COMPOUND[0], COMPOUND[2]) or y in (COMPOUND[1], COMPOUND[3])) and (x, y) not in GATE:
            A.op(op='erase', x=x, y=y); A.op(op='object', x=x, y=y, s=random.choice(W_SANDSTONE), block=3)
for x, y in GATE: A.op(op='erase', x=x, y=y)
for b, door, kind in ROOMS:
    for dy in (-1, 0, 1): A.op(op='erase', x=door[0], y=door[1] + dy)
for x in range(COURT[0], COURT[2]):
    for y in range(COURT[1], COURT[3] + 1):
        A.op(op='flag', x=x, y=y, bit=2, mode=0)
        if inbox(x, y, POOL_IN): A.op(op='floor', x=x, y=y, s=random.choice(WATER), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
        else: A.op(op='floor', x=x, y=y, s=random.choice(GOLD), set=False)                     # a sand courtyard round the pool
A.run('the Hatchery')
# the Broodmother's Chamber
A.house(BROOD, W_TEMPLE, SETTS)
for x, y in BROOD_DOOR: A.op(op='erase', x=x, y=y)
for x in range(578, 588):
    for y in range(836, 845):
        if ((x - 582.5) / 4.2) ** 2 + ((y - 840) / 3.6) ** 2 <= 1: A.op(op='floor', x=x, y=y, s=random.choice(WATER), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
A.run("the Broodmother's Chamber")
P = [(FIREBOWL, 538, 781), (FIREBOWL, 548, 781), (FIREBOWL, 538, 792), (FIREBOWL, 548, 792),
     (FIREBOWL, 575, 826), (FIREBOWL, 589, 826), (FIREBOWL, 575, 845), (FIREBOWL, 589, 845),
     (TORCH, 520, 771), (BONES, 516, 787), (BONES, 524, 793), (BONES, 560, 772), (BONES, 566, 790), (BONES, 586, 831), (BONES, 577, 834)]
for x, y in PITS: P += [(BONES, x + 2, y - 1), (BONES, x - 2, y + 2)]
A.place(*P)
A.ground_edges((X0, Y0, X1, Y1))
A.zone(COMPOUND[0], COMPOUND[1], COMPOUND[2], COMPOUND[3], 'the Hatchery')
A.zone(BROOD[0], BROOD[1], BROOD[2], BROOD[3], "Broodmother's Chamber")
A.zone(X0, Y0, X1, Y1, 'Lizard Hatcheries')
A.save()
