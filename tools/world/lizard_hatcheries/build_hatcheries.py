#!/usr/bin/env python3
"""The Lizard Hatcheries (Nov 17): south of Fenwatch (its south gate's road), Captain. Fenwatch's marsh carried on: marsh
grass, mud flats, murky lakes (can't be walked on), reeds and willows, with rock outcrops, on both sides of the **through
road to Stonehold** (path, y ~801-809, leaving the area's south edge at x 595 open for the pass). Kept back from the road
(Cody, Nov 17): lakes, pits and caves start a good way off it.
West of the road, set well back from it: **the Hatchery**, a cave in the brown mine rock (wall 122, floor 116, dark inside,
cave lights: template 171 Earth Light II): a great hall with a warm pool, **the Broodmother's Nest** and three egg chambers off
it, a long tunnel out toward the road. East of the road: egg pits in the mud among the lakes, and at the far end the
**Archmage's Grotto**, a smaller cave entered from the north (its own path from the road). (Cody, Nov 17: the Broodmother is
the big cave's boss, the Archmage the small cave's.)

    build_hatcheries.py <.dat folder>      (game stopped; tools/world/arealib.py)      then place_hatcheries.py"""
import sys, os, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1], seed=1123)
X0, X1, Y0, Y1 = 495, 595, 757, 860            # (y from 757: the big cave was moved back from the road, Cody Nov 17)
ROCK, CAVEFLOOR, CAVE_TORCH = 122, 116, 171         # cave light: 'Earth Light II', a fire on a rock mound, always lit (the game's caves use it)
def road_y(x): return 801 + min(5, max(0, (x - 495) // 4)) + int(round(0.8 * math.sin(x / 7.0)))
road = {(x, road_y(x) + d) for x in range(486, X1 + 1) for d in (0, 1, 2)}
def road_dist(x, y): return min(abs(y - (road_y(xx) + 1)) + abs(x - xx) for xx in range(max(486, x - 3), min(X1, x + 3) + 1))
# ---- caves: chambers (centre x, y, radius x, y) joined by tunnels; walls are the rock around what is carved
def ellipse(cx, cy, rx, ry, rough=0.12):
    out = set(); ph = random.random() * 6
    for x in range(int(cx - rx - 2), int(cx + rx + 3)):
        for y in range(int(cy - ry - 2), int(cy + ry + 3)):
            a = math.atan2((y - cy) / ry, (x - cx) / rx); k = 1 + rough * math.sin(3 * a + ph) + rough * 0.6 * math.sin(5 * a + 2 * ph)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= k * k: out.add((x, y))
    return out
def tunnel(a, b, w=1):
    out = set(); n = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
    for i in range(n + 1):
        x, y = round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n)
        for dx in range(-w, w + 1):
            for dy in range(-w, w + 1):
                if abs(dx) + abs(dy) <= w: out.add((x + dx, y + dy))
    return out
S = -6                                               # the big cave sits 6 tiles further from the road than first drawn
HALL = (541, 781 + S, 7, 7); NEST = (521, 773 + S, 5, 5); EGGS = [(521, 788 + S, 4.5, 4.5), (561, 773 + S, 5, 4.5), (561, 789 + S, 4.5, 4.5)]
POOL_IN = ellipse(541, 781 + S, 3.2, 3.0, 0.08)
hatch = ellipse(*HALL) | ellipse(*NEST) | set().union(*(ellipse(*e) for e in EGGS))
for c in (NEST,) + tuple(EGGS): hatch |= tunnel((HALL[0], HALL[1]), (c[0], c[1]))
H_EXIT = [(541, 788 + S), (541, 795)]                # the tunnel out toward the road (longer now)
hatch |= tunnel(*H_EXIT)
GROTTO = (582, 842, 8, 9)                            # the Archmage's Grotto: the smaller cave; its tunnel opens north (Cody, Nov 17)
grotto = ellipse(*GROTTO) | tunnel((576, 842), (569, 842))
GROTTO_POOL = ellipse(585, 846, 3.0, 3.4, 0.1)
caves = hatch | grotto
def rock_ring(c, r=1):
    return {(x + dx, y + dy) for x, y in c for dx in range(-r, r + 1) for dy in range(-r, r + 1)} - c
walls = rock_ring(hatch) | rock_ring(grotto)
mouths = {(x, 797) for x in (540, 541, 542)} | {(567, y) for y in (841, 842, 843)}     # where each tunnel opens (no rock across)
walls -= mouths
caves |= mouths
# ---- outdoors: lakes and mud flats, kept back from the road
def blob(cx, cy, r, rough=0.35):
    out = set(); ph = random.random() * 6
    for x in range(int(cx - r - 3), int(cx + r + 4)):
        for y in range(int(cy - r - 3), int(cy + r + 4)):
            a = math.atan2(y - cy, x - cx); rr = r * (1 + rough * 0.5 * (math.sin(3 * a + ph) + 0.6 * math.sin(5 * a + 2 * ph)))
            if math.hypot(x - cx, y - cy) <= rr + random.uniform(-0.6, 0.6): out.add((x, y))
    return out
lakes, mud = set(), set()
for cx, cy, r in [(527, 840, 5.5), (550, 828, 4), (510, 852, 3.5), (556, 850, 4.5), (505, 777, 4), (580, 776, 4.5), (590, 790, 2.5)]: lakes |= blob(cx, cy, r, 0.3)
PITS = [(518, 826), (541, 846), (568, 824), (534, 818)]                   # egg pits: mud hollows
for cx, cy in PITS: mud |= blob(cx, cy, 3.6)
for cx, cy, r in [(510, 836, 3), (570, 858, 3), (500, 795, 2.5), (588, 815, 2.5), (548, 858, 3)]: mud |= blob(cx, cy, r)
grotto_path = tunnel((566, 842), (560, 842), 2) | tunnel((560, 842), (560, 812), 2)
lakes = {p for p in lakes if road_dist(*p) >= 6} - grotto_path; mud = {p for p in mud if road_dist(*p) >= 5} - lakes - grotto_path
OUTCROPS = [(500, 822), (529, 856), (575, 852), (593, 829), (503, 768), (586, 768), (566, 812)]   # rock outcrops, cave-like
outcrop = set()
for cx, cy in OUTCROPS: outcrop |= {p for p in blob(cx, cy, 1.6, 0.4) if road_dist(*p) >= 5} - grotto_path
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if (x, y) in road: continue
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0)              # the void here was flagged indoors
        if (x, y) in caves:
            A.op(op='floor', x=x, y=y, s=CAVEFLOOR, set=False); A.op(op='flag', x=x, y=y, bit=2, mode=1)
            if (x, y) in POOL_IN or (x, y) in GROTTO_POOL: A.op(op='floor', x=x, y=y, s=random.choice(MURK), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
            continue
        if (x, y) in walls or (x, y) in outcrop:
            A.op(op='floor', x=x, y=y, s=CAVEFLOOR, set=False); A.op(op='object', x=x, y=y, s=ROCK, block=3); continue
        if (x, y) in lakes:
            A.op(op='floor', x=x, y=y, s=random.choice(MURK), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1); continue
        if (x, y) in mud:
            A.op(op='floor', x=x, y=y, s=random.choice(MUD), set=False); continue
        A.op(op='floor', x=x, y=y, s=random.choice(MARSH), set=False)
        if any((x + dx, y + dy) in walls for dx in (-1, 0, 1) for dy in (-1, 0, 1)) or road_dist(x, y) <= 1: continue
        if any((x + dx, y + dy) in lakes for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))):
            if random.random() < 0.45: A.op(op='object', x=x, y=y, s=random.choice(REEDS), block=0)
            continue
        d = min(y - Y0, Y1 - y, X1 - x); r = random.random()
        gap = X1 - x <= 3 and abs(y - road_y(x) - 1) <= 4                  # the road leaves the area open here
        if d <= 2 and not gap:
            if r < 0.85: A.op(op='object', x=x, y=y, s=random.choice(WILLOW + DEAD), block=3)
        elif r < 0.020: A.op(op='object', x=x, y=y, s=random.choice(WILLOW), block=3)
        elif r < 0.034: A.op(op='object', x=x, y=y, s=random.choice(DEAD), block=1)
        elif r < 0.050 and road_dist(x, y) > 3: A.op(op='object', x=x, y=y, s=random.choice(REEDS), block=0)
for x, y in road:
    if X0 - 9 <= x <= X1: A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='floor', x=x, y=y, s=random.choice(PATH), set=False)
spur = tunnel((541, 798), (541, road_y(541)), 1) | tunnel((566, 842), (560, 842), 1) | tunnel((560, 842), (560, road_y(560) + 2), 1)       # paths from the road to the cave mouths
for x, y in spur - road - caves:
    A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='floor', x=x, y=y, s=random.choice(PATH), set=False)
A.run('Lizard Hatcheries: marsh, lakes, caves, road')
for x in range(488, 496):                         # open Fenwatch marsh's south tree wall at the road; a no-monster strip there
    for y in range(796, 810):
        if abs(y - road_y(x) - 1) <= 3: A.op(op='erase', x=x, y=y)
for y in range(Y0, Y1 + 1):
    for x in (495, 496): A.op(op='flag', x=x, y=y, bit=5, mode=1)
A.run('open the tree wall, no-monster strip')
# cave torches along the cave walls (inside, on a floor tile next to the rock), a few apart; bones in the egg chambers
inner = [p for p in caves if p not in POOL_IN and p not in GROTTO_POOL and p not in mouths and any((p[0] + dx, p[1] + dy) in walls for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)))]
random.shuffle(inner); torches = []
for p in sorted(inner):
    if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= 9 for q in torches): torches.append(p)
P = [(CAVE_TORCH, x, y) for x, y in torches]
for cx, cy, rx, ry in EGGS: P += [(BONES, round(cx) + 1, round(cy) - 1)]
P += [(BONES, 579, 838), (BONES, 586, 839), (BONES, 523, 771 + S)]
for x, y in PITS: P += [(BONES, x + 1, y - 1)]
A.place(*P)
# lizard eggs (tools/sprites/world_eggs.py: 38300-38306, one big egg a tile; Cody: 3-4 a chamber): the Nest, the egg chambers, the pits
EGG = [38300, 38302, 38304, 38300, 38302, 38304, 38306]          # whole eggs mostly, now and then a hatched one
def clutches(n, ok, box, apart=3):
    got = 0
    for p in sorted(set((random.randint(box[0], box[2]), random.randint(box[1], box[3])) for _ in range(400))):
        if got >= n: break
        t = A.tile(*p)
        if ok(*p) and not t[1] and not t[4] and not (t[7] & 1) and all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= apart for q in placed):
            A.op(op='object', x=p[0], y=p[1], s=random.choice(EGG), block=1); placed.append(p); got += 1
placed = []
inside = lambda b: (lambda x, y: (x, y) in caves and ((x - b[0]) / b[2]) ** 2 + ((y - b[1]) / b[3]) ** 2 <= 0.7)
clutches(4, inside(NEST), (NEST[0] - 5, NEST[1] - 5, NEST[0] + 5, NEST[1] + 5))
for e in EGGS: clutches(random.choice([3, 4]), inside(e), (int(e[0] - 5), int(e[1] - 5), int(e[0] + 5), int(e[1] + 5)))
for cx, cy in PITS: clutches(random.choice([2, 3]), lambda x, y: (x, y) in mud, (cx - 3, cy - 3, cx + 3, cy + 3))
A.run('lizard eggs'); print(len(placed), 'eggs')
A.marsh_edges((X0 - 2, Y0, X1, Y1))
A.zone(505, 757, 570, 797, 'the Hatchery')
A.zone(512, 762, 527, 774, "Broodmother's Nest")
A.zone(565, 832, 592, 853, "Archmage's Grotto")
A.zone(X0, Y0, X1, Y1, 'Lizard Hatcheries')
A.save(); print(len(torches), 'cave lights')
