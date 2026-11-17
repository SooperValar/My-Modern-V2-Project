#!/usr/bin/env python3
"""Stonehold, the band D hub (Nov 17), and the pass up to it from the Lizard Hatcheries.

A mountain mining town in a hollow ringed by granite cliffs (the game's pale rock blocks 1204 / 1206),
houses of slate and fieldstone cut into the rock (the cliffs close in on them), a short fort wall and gatehouse closing the north entrance where the
pass comes in, cobbled streets to a square (its centre 682,810 is kept free for waypoint 7), the Watch barracks, an inn,
Hagar's forge, Varo's temple, the trader's house, two houses and an old mine adit cut into the south cliff. Snow patches
on the high meadow by the cliffs. Gates (gaps in the cliffs, roads ending open at the area's edge for areas still to come):
west -> Golem Foundry, east -> Monastery, south-west -> Ashen Fields, south-east -> the pass to the Last Bastion and the
Gargoyle Spires. At each way out a guard post: two guards beside the road facing away from town (Cody, Nov 17:
Warriors and Arch-Templars; placed by place_stonehold.py from made_terrain.json). North = smaller x.

    build_stonehold.py <.dat folder>      (game stopped; tools/world/arealib.py)      then place_stonehold.py"""
import sys, os, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1], seed=1125)
X0, X1, Y0, Y1 = 650, 715, 775, 845                       # the town (the space plan's box)
P0, P1 = 596, 649                                          # the pass, x
CLIFF = [1204, 1206]                                       # pale granite blocks (mixed with the dark 1210 they looked like a checkerboard)
BOULDER = 1208                                             # a lone rounded granite block
SNOW = [35400, 35401, 35402, 35403]
SQUARE = (682, 810)
def rough(cx, cy, rx, ry, k=0.10, seed=0):
    rnd = random.Random(seed); ph = rnd.random() * 6
    def inside(x, y):
        a = math.atan2((y - cy) / ry, (x - cx) / rx); f = 1 + k * math.sin(3 * a + ph) + k * 0.6 * math.sin(5 * a + 2 * ph)
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= f * f
    return inside
hollow = rough(683, 810, 25, 28, 0.08, 5)                  # the town's floor; everything else in the box is cliff (Cody: the
                                                           # cliffs close in, so the buildings stand cut into the rock)
def line(a, b, w=1):
    out = set(); n = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
    for i in range(n + 1):
        x, y = round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n)
        for dx in range(-w, w + 1):
            for dy in range(-w, w + 1):
                if abs(dx) + abs(dy) <= w: out.add((x, y + 0) if False else (x + dx, y + dy))
    return out
# ---- roads: the pass, the north gate, streets to the square and the four other gates (roads end open at the box's edge)
def pass_y(x): return 807 + int(round(1.2 * math.sin((x - P0) / 7.0)))
road = {(x, pass_y(x) + d) for x in range(P0, X0 + 7) for d in (-1, 0, 1)}
streets = set()
streets |= line((656, 807), SQUARE, 1)                      # north gate - square
streets |= line(SQUARE, (681, 775), 1) | line((681, 775), (681, 766), 1)      # west gate -> Golem Foundry
streets |= line(SQUARE, (681, 845), 1) | line((681, 845), (681, 854), 1)      # east gate -> Monastery
streets |= line(SQUARE, (712, 786), 1) | line((712, 786), (724, 784), 1)      # south-west gate -> Ashen Fields
streets |= line(SQUARE, (712, 834), 1) | line((712, 834), (724, 835), 1)      # south-east gate -> Last Bastion pass / Spires
square = {(x, y) for x in range(675, 690) for y in range(803, 818) if ((x - 682) / 6.8) ** 2 + ((y - 810) / 6.8) ** 2 <= 1}
inbox = lambda x, y, b: b[0] <= x <= b[2] and b[1] <= y <= b[3]
# a short path from each door out to the square, so no door opens onto rock
for b, wall, floor, door, side, name in [(b[0], 0, 0, b[3], b[4], b[5]) for b in [((657, 786, 666, 798), 0, 0, (666, 792), 's', 'Watch Barracks'),
        ((657, 816, 667, 830), 0, 0, (667, 823), 's', ''), ((671, 779, 679, 788), 0, 0, (679, 783), 's', ''), ((669, 831, 678, 840), 0, 0, (678, 835), 's', ''),
        ((692, 779, 699, 787), 0, 0, (692, 783), 'n', ''), ((699, 817, 706, 825), 0, 0, (699, 821), 'n', ''), ((693, 834, 700, 841), 0, 0, (693, 837), 'n', '')]]:
    out = (door[0] + 1, door[1]) if side == 's' else (door[0] - 1, door[1])
    streets |= {p for p in line(out, SQUARE, 1) if not inbox(p[0], p[1], b)}
paved = streets | square
# guard posts: two guards beside the road at each way out, facing away from town (dir 1 north, 2 south, 3 east, 4 west)
def post(cross, axis, at, d):
    """the two tiles flanking the road where it crosses the line axis=at (axis 'x': a row x=at across y; 'y': a column)"""
    rd = sorted(p[1] if axis == 'x' else p[0] for p in streets if (p[0] if axis == 'x' else p[1]) == at and abs((p[1] if axis == 'x' else p[0]) - cross) <= 4)
    a, b = rd[0] - 1, rd[-1] + 1
    return [((at, a) if axis == 'x' else (a, at)) + (d,), ((at, b) if axis == 'x' else (b, at)) + (d,)]
WALL_X = 662
POSTS = {'north': [(WALL_X - 1, 804, 1), (WALL_X - 1, 810, 1)], 'west': post(681, 'y', 777, 4), 'east': post(681, 'y', 843, 3),
         'south-west': post(785, 'x', 713, 2), 'south-east': post(834, 'x', 713, 2)}
guard_spots = {(x, y) for v in POSTS.values() for x, y, d in v}
gates = {p for p in streets if not (X0 <= p[0] <= X1 and Y0 <= p[1] <= Y1) or not hollow(*p)}   # the cuts through the cliff
# ---- buildings: (box, wall, floor, door tile, side, name)
B = [((657, 786, 666, 798), W_SLATE, FLAGSTONE, (666, 792), 's', 'Watch Barracks'),
     ((657, 816, 667, 830), W_TIMBER, OAK, (667, 823), 's', 'the Granite Hearth'),
     ((671, 779, 679, 788), W_FIELDSTONE, FLAGSTONE, (679, 783), 's', "Hagar's Forge"),
     ((669, 831, 678, 840), W_FIELDSTONE, SETTS, (678, 835), 's', "Varo's Temple"),
     ((692, 779, 699, 787), W_SLATE, OAK, (692, 783), 'n', "Trader's House"),
     ((699, 817, 706, 825), W_SLATE, OAK, (699, 821), 'n', ''),
     ((693, 834, 700, 841), W_FIELDSTONE, OAK, (693, 837), 'n', '')]
MINE = (707, 806, 715, 812)                                # the old adit: a short tunnel into the south cliff
mine = {(x, y) for x in range(708, 716) for y in range(808, 811)}
snow = set()
for cx, cy, r in [(661, 800, 3), (662, 836, 3.5), (708, 793, 3.5), (707, 829, 3.5), (667, 779, 2.5), (689, 843, 3), (701, 792, 2.5), (686, 780, 2.5), (703, 842, 2.5), (670, 843, 2.5), (713, 818, 2)]:
    snow |= {(x, y) for x in range(int(cx - r - 1), int(cx + r + 2)) for y in range(int(cy - r - 1), int(cy + r + 2)) if math.hypot(x - cx, y - cy) <= r + random.uniform(-0.5, 0.4)}
# ---- the pass
for x in range(P0, X0):
    for y in range(797, 819):
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='flag', x=x, y=y, bit=5, mode=1)
        if (x, y) in road: A.op(op='floor', x=x, y=y, s=random.choice(PATH), set=False); continue
        d = abs(y - pass_y(x))
        wall = 6 + int(round(1.5 * math.sin(x / 4.0 + (0 if y < pass_y(x) else 2)) + random.uniform(-0.6, 0.6)))
        if d >= wall:
            A.op(op='floor', x=x, y=y, s=random.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=random.choice(CLIFF), block=3); continue
        A.op(op='floor', x=x, y=y, s=random.choice(SNOW if d >= wall - 1 and random.random() < 0.5 else GRASS), set=False)
        if d >= 3 and random.random() < 0.05: A.op(op='object', x=x, y=y, s=random.choice(DEAD + PINE), block=1)
A.run('the pass')
# ---- the town
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='flag', x=x, y=y, bit=5, mode=1)
        if (x, y) in guard_spots: A.op(op='floor', x=x, y=y, s=random.choice(FLAGSTONE), set=False); continue     # a guard post, cut into the rock
        if (x, y) in paved or (x, y) in road: A.op(op='floor', x=x, y=y, s=random.choice(SETTS), set=False); continue
        if (x, y) in mine: A.op(op='floor', x=x, y=y, s=116, set=False); A.op(op='flag', x=x, y=y, bit=2, mode=1); continue
        if not hollow(x, y) or (inbox(x, y, MINE) and (x, y) not in mine):
            A.op(op='floor', x=x, y=y, s=random.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=random.choice(CLIFF if not inbox(x, y, MINE) else [1210]), block=3); continue
        A.op(op='floor', x=x, y=y, s=random.choice(SNOW if (x, y) in snow else GRASS), set=False)
        if (x, y) not in snow and not any(inbox(x, y, (b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)) for b, *_ in B) and not any((x + dx, y + dy) in paved for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            r = random.random()
            if r < 0.018: A.op(op='object', x=x, y=y, s=random.choice(PINE), block=3)
            elif r < 0.026: A.op(op='object', x=x, y=y, s=BOULDER, block=3)
            elif r < 0.032: A.op(op='object', x=x, y=y, s=random.choice(DEAD), block=1)
for x, y in streets:
    if not (X0 <= x <= X1 and Y0 <= y <= Y1):                # the road stubs beyond the box, to the next areas
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='floor', x=x, y=y, s=random.choice(SETTS), set=False)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q not in streets: A.op(op='floor', x=q[0], y=q[1], s=random.choice(SNOW), set=False); A.op(op='object', x=q[0], y=q[1], s=random.choice(CLIFF), block=3)
A.run('Stonehold: ground, cliffs, streets')
# the fort wall across the north entrance, with a gatehouse (two towers) and the gate on the road
for y in range(780, 841):                                  # (WALL_X: where the entrance widens, so the wall is seen from the pass)
    if not hollow(WALL_X, y) or 805 <= y <= 809: continue
    A.op(op='erase', x=WALL_X, y=y); A.op(op='object', x=WALL_X, y=y, s=random.choice(W_FIELDSTONE), block=3)
for x, y in [(WALL_X, 803), (WALL_X, 804), (WALL_X + 1, 803), (WALL_X + 1, 804), (WALL_X, 810), (WALL_X, 811), (WALL_X + 1, 810), (WALL_X + 1, 811)]:   # the gatehouse towers
    A.op(op='erase', x=x, y=y); A.op(op='object', x=x, y=y, s=random.choice(W_FIELDSTONE), block=3)
A.run('north wall and gatehouse')
for b, wall, floor, door, side, name in B: A.house(b, wall, floor, door_side=side, door=door)
A.run('houses')
P = [(TORCH, WALL_X + 2, 805), (TORCH, WALL_X + 2, 809), (TORCH, 676, 809), (TORCH, 688, 811), (TORCH, 682, 777), (TORCH, 680, 843), (TORCH, 711, 789), (TORCH, 711, 831),
     (TORCH, 709, 807), (FIREBOWL, 674, 781), (FIREBOWL, 677, 786), (FIREBOWL, 672, 834), (FIREBOWL, 672, 837), (BARREL, 658, 818), (BARREL, 659, 818), (BARREL, 709, 811),
     (BONES, 713, 809)]
A.place(*P)
A.ground_edges((P0, 797, X1, Y1), kinds=['soft snow'])
for b, wall, floor, door, side, name in B:                 # zone flag 1 = "in the ...", 0 = "in ..." (area.c)
    if name: A.zone(b[0], b[1], b[2], b[3], name.replace('the ', ''), flag=0 if "'s " in name else 1)
A.zone(X0, Y0, X1, Y1, 'Stonehold', flag=0)
A.zone(P0, 797, X0 - 1, 818, 'Stonehold Pass')
import json; json.dump({'posts': POSTS, 'square': SQUARE}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'made_terrain.json'), 'w'), indent=1)
A.save(); print('guard posts', POSTS)
