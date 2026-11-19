#!/usr/bin/env python3
"""The Monastery of the Still Hand (Nov 19; band D, Lieutenant Colonel), east of Stonehold. A mountain monastery gone
bad, spread over the whole box from the start (Cody, the Spires: the two goals at opposite ends, loops, dead ends):

  Pilgrims' Stair: long switchbacks, monk statues set into the rock along them, up from Stonehold's east gate road (681,855) to the gate landing (Brother Anselm; no
  monsters on the stair). The Cloister in the middle: a walled compound - courtyard and raked-stone garden, four monks'
  cells, the refectory, the chapel - doors west (the gate), north, south and east.
  NORTH route: north door -> the Training Yard (practice dummies, north-west) -> along the north cliffs -> the Hall of
  the Silent Hand (Master Kesh, the far north-east). SOUTH route: south door -> the Burial Terrace (tombstones,
  south-west) -> the gardens and the frozen Still Pond (walk on the ice) -> the Abbot's Sanctum (the far south-east).
  The outer TERRACE from the east door joins both ends the other way round (the Hall's second door, the Sanctum's
  second door): two loops. Dead ends: the Library (east), the collapsed cells (north-east of the cloister), the
  Hermit's Ledge (off the north route).
Granite cliffs on snow round everything, like Stonehold; deep rock nobody sees is left empty. North = smaller x,
west = smaller y. Pieces: tools/sprites/world_monastery.py (objects 38467-38478, ice 37528-37531).

    build_monastery.py <.dat folder>      (game stopped; tools/world/arealib.py)  -> made_terrain.json"""
import sys, os, random, math, json
from collections import deque
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1201); R = random.Random(1201)
X0, X1, Y0, Y1 = 650, 740, 855, 950
CLIFF, BOULDER = [1204, 1206], 1208
SNOW = [35400, 35401, 35402, 35403]; SNOWY = [36100, 36101, 36102, 36103]; SNOWPINE = [38154, 38155, 38156, 38157]
ICE = [37528, 37529, 37530, 37531]
DUMMY, BOOKCASE, BOOKSTAND, CANDLES, BENCH, POT = 38467, 38469, 38471, 38473, 38475, 38477
STATUE = {d: 38479 + 2 * k for k, d in enumerate(('W', 'E', 'N', 'S', 'NW', 'SW', 'NE', 'SE'))}   # stone monks (statues.py), the way each faces
# (the game's sprite order up, down, left, right... = DX_UP (y-1, west), DX_DOWN (y+1, east), DX_LEFT (x-1, north), DX_RIGHT (x+1, south))
PH = [R.random() * 6.28 for _ in range(6)]
inbox = lambda x, y: X0 <= x <= X1 and Y0 <= y <= Y1

def line(pts, w=1):
    out = set()
    for a, b in zip(pts, pts[1:]):
        n = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
        for i in range(n + 1):
            x, y = round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n)
            for dx in range(-w, w + 1):
                for dy in range(-w, w + 1):
                    if abs(dx) + abs(dy) <= w: out.add((x + dx, y + dy))
    return out
def blob(c, rx, ry, k=0.12):
    out = set()
    for x in range(int(c[0] - rx - 2), int(c[0] + rx + 3)):
        for y in range(int(c[1] - ry - 2), int(c[1] + ry + 3)):
            a = math.atan2((y - c[1]) / ry, (x - c[0]) / rx); f = 1 + k * math.sin(3 * a + PH[0]) + 0.6 * k * math.sin(5 * a + PH[1])
            if ((x - c[0]) / rx) ** 2 + ((y - c[1]) / ry) ** 2 <= f * f: out.add((x, y))
    return out
def box(x0, y0, x1, y1): return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

# ---------------------------------------------------------------- the shape
CLOISTER = (684, 888, 714, 920)
HALL = (651, 918, 664, 946)                     # far north-east
SANCTUM = (726, 925, 739, 948)                  # far south-east
LIBRARY = (700, 932, 712, 946)
RUIN = (686, 930, 694, 938)
P = {}
# the stair (Cody: 'more back and forth'): long legs north and south, each a step further east, two tiles of rock between
STAIR_PTS = [(681, 855), (681, 858), (673, 858), (673, 863), (697, 863), (697, 868), (673, 868), (673, 873), (697, 873), (697, 880)]
P['stair'] = line(STAIR_PTS, 1)
P['landing'] = box(696, 880, 702, 887)
P['north path'] = line([(683, 904), (677, 900), (672, 890), (669, 884)], 1) | line([(656, 883), (654, 895), (656, 905), (657, 917)], 1)
P['training yard'] = blob((661, 872), 8, 11)
P['hermit'] = line([(672, 890), (668, 896), (665, 899)], 1) | blob((663, 901), 2.4, 2.6)
P['south path'] = line([(715, 904), (720, 900), (726, 891), (729, 885)], 1) | line([(733, 884), (734, 893)], 1) | line([(732, 913), (731, 920), (731, 924)], 1)
P['burial terrace'] = blob((730, 873), 7, 11)
P['gardens'] = blob((729, 905), 7, 9)
P['terrace'] = line([(699, 921), (699, 925), (690, 926), (680, 928), (670, 930), (665, 930)], 1) | \
               line([(699, 925), (708, 927), (717, 926), (723, 932), (725, 935)], 1) | line([(699, 925), (699, 937)], 1) | line([(686, 927), (686, 929)], 0)
POND = blob((729, 905), 3.0, 4.2, k=0.2)
houses = box(*CLOISTER) | box(*HALL) | box(*SANCTUM) | box(*LIBRARY) | box(*RUIN)
part = {}
for name in ('terrace', 'stair', 'landing', 'north path', 'south path', 'hermit', 'training yard', 'burial terrace', 'gardens'):
    for p in P[name]:
        if inbox(*p) and p not in houses: part[p] = name
outdoor = set(part)

# ---------------------------------------------------------------- ground and cliffs
near = lambda x, y, k: any((x + dx, y + dy) in outdoor or (x + dx, y + dy) in houses for dx in range(-k, k + 1) for dy in range(-k, k + 1))
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if A.floor(x, y) != VOID and (x, y) not in outdoor and (x, y) not in houses: continue
        A.clear(x, y)
        for b in range(2, 15): A.op(op='flag', x=x, y=y, bit=b, mode=0)
        p = (x, y); pt = part.get(p)
        if pt:
            if pt in ('stair', 'north path', 'south path', 'terrace', 'landing'): s = R.choice(PATH if R.random() < 0.8 else SNOW)
            elif pt == 'gardens': s = R.choice(ICE) if p in POND else R.choice(SNOWY)
            elif pt == 'training yard': s = R.choice(SETTS if R.random() < 0.7 else SNOW)
            else: s = R.choice(SNOW)
            A.op(op='floor', x=x, y=y, s=s, set=False)
            if pt in ('stair', 'landing'): A.op(op='flag', x=x, y=y, bit=5, mode=1)          # no monsters on the stair
        elif p in houses: pass
        elif near(x, y, 3):
            A.op(op='floor', x=x, y=y, s=R.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3)
A.run('monastery: ground and cliffs')

# ---------------------------------------------------------------- the buildings
WALL = W_SLATE
def door(x, y, side): A.op(op='erase', x=x, y=y); A.op(op='place', x=x, y=y, t=DOOR_I if side in ('n', 's') else DOOR_II, fresh=1)
A.house(CLOISTER, WALL, FLAGSTONE, door_side='w', door=(699, 888), indoors=False)              # the gate
for d in (((684, 904), 'n'), ((714, 904), 's'), ((699, 920), 'e')): door(*d[0], d[1])
A.run('cloister doors')
CELLS = [(685, 889, 690, 894), (685, 895, 690, 900), (685, 908, 690, 913), (685, 914, 690, 919)]     # four cells, a passage to the north door between
for i, c in enumerate(CELLS): A.house(c, WALL, DARKWOOD, door_side='s', door=(690, c[1] + 2 + (i % 2)))
A.house((707, 889, 713, 900), WALL, OAK, door_side='n', door=(707, 894))                       # the refectory
A.house((704, 910, 713, 919), W_TEMPLE, FLAGSTONE, door_side='n', door=(704, 914))             # the chapel
GARDEN_IN = box(694, 899, 702, 908)
for x, y in GARDEN_IN: A.op(op='floor', x=x, y=y, s=R.choice(SAND), set=False)
for x, y in ((696, 901), (700, 906), (699, 902)): A.op(op='object', x=x, y=y, s=BOULDER, block=3)
A.run('the raked garden')
A.house(HALL, WALL, DARKWOOD, door_side='w', door=(658, 918))
door(664, 930, 's'); A.run('hall: second door')
for x in (655, 660):                                                                             # two rows of pillars
    for y in range(922, 944, 5): A.op(op='object', x=x, y=y, s=R.choice(WALL), block=3)
A.house(SANCTUM, W_TEMPLE, FLAGSTONE, door_side='w', door=(731, 925))
door(726, 935, 'n'); A.run('sanctum: second door')
A.house(LIBRARY, WALL, OAK, door_side='n', door=(700, 938))
A.house(RUIN, WALL, DARKWOOD, door_side='w', door=None, keep=0.45, indoors=False)               # the collapsed cells
for y in (929, 930, 931): A.op(op='erase', x=686, y=y)
A.run('ruin entrance')

# ---------------------------------------------------------------- furniture and details
used = set()
def put(s, x, y, block=3): A.op(op='object', x=x, y=y, s=s, block=block); used.add((x, y))
def place(t, x, y): A.op(op='place', x=x, y=y, t=t, fresh=1); used.add((x, y))
yard = sorted(p for p in P['training yard'] if p in outdoor and all((p[0] + dx, p[1] + dy) in outdoor for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
R.shuffle(yard); k = 0
for p in yard:
    if k >= 8: break
    if any(abs(p[0] - a) + abs(p[1] - b) < 4 for a, b in used): continue
    put(DUMMY, *p, block=1); k += 1
for x, y in ((653, 925), (653, 940), (662, 925), (662, 940)): put(DUMMY, x, y, block=1)              # Kesh's hall
for y in range(934, 946, 2): put(BOOKCASE, 701, y); put(BOOKCASE, 711, y)                          # the library
put(BOOKSTAND, 706, 940, block=1)
for c in CELLS: put(POT, c[0] + 1, c[1] + 1, block=1)
for y in range(891, 899, 3): put(BENCH, 710, y, block=1)                                           # refectory
for x, y in ((711, 912), (711, 917)): put(CANDLES, x, y, block=1)                                  # chapel
put(BOOKSTAND, 710, 914, block=1)
for x, y in ((737, 928), (737, 945), (729, 945), (733, 937)): put(CANDLES, x, y, block=1)          # sanctum
A.run('furniture')
# statues (Cody): set into the stair's east wall, facing the path (west); two by the raked garden, a pair at each goal's door
for (ya, xa, xb) in ((858, 675, 679), (863, 676, 694), (868, 676, 694), (873, 676, 694)):
    for x in range(xa, xb + 1, 4):
        if (x, ya + 2) not in outdoor and inbox(x, ya + 2): put(STATUE['W'], x, ya + 2)
for x, y, d in ((693, 900, 'S'), (693, 907, 'S'), (703, 900, 'N'), (703, 907, 'N'),
                (656, 916, 'W'), (660, 916, 'W'), (729, 923, 'W'), (733, 923, 'W')):
    put(STATUE[d], x, y)
A.run('statues')
graves = sorted(p for p in P['burial terrace'] if p in outdoor and all((p[0] + dx, p[1] + dy) in outdoor for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
R.shuffle(graves); k = 0
bur = {p for p in P['burial terrace'] | P['south path'] if p in outdoor}
def bur_ok(block):
    w = bur - used - set(block); s0 = (729, 885); S = {s0}; qq = deque([s0])
    while qq:
        p = qq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (p[0] + dx, p[1] + dy)
            if n in w and n not in S: S.add(n); qq.append(n)
    return len(S) == len(w)
for p in graves:
    if k >= 12: break
    if any(abs(p[0] - a) + abs(p[1] - b) < 3 for a, b in used) or abs(p[1] - 873) <= 1 or not bur_ok([p]): continue
    place(TOMBSTONE, *p); k += 1
A.run('the burial terrace')
gard = sorted(p for p in P['gardens'] if p in outdoor and p not in POND and all((p[0] + dx, p[1] + dy) in outdoor for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
R.shuffle(gard); k = 0
for p in gard:
    if k >= 7: break
    if any(abs(p[0] - a) + abs(p[1] - b) < 3 for a, b in used): continue
    put(R.choice(SNOWPINE), *p, block=1); k += 1
A.run('garden pines')

# ---------------------------------------------------------------- no closed pockets (straight steps from the stair's foot)
walls = set()
for p in houses:
    t = A.tile(*p)
    if t[1] or (t[7] & 1): walls.add(p)
walk = {p for p in (outdoor | houses) if p not in walls and p not in used}
S = (681, 856); D = {S: 0}; q = deque([S])
while q:
    p = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (p[0] + dx, p[1] + dy)
        if n in walk and n not in D:
            t = A.tile(*n)
            if t[1] and not t[4]: continue
            D[n] = D[p] + 1; q.append(n)
lost = [p for p in walk if p not in D]
print('walkable', len(walk), 'not reached', len(lost), sorted(lost)[:12])

A.zone(X0, Y0, X1, Y1, 'Monastery of the Still Hand', flag=1)
A.zone(676, 855, 703, 887, "Pilgrims' Stair", flag=0)
A.zone(*CLOISTER, 'Cloister', flag=1)
A.zone(652, 860, 670, 884, 'Training Yard', flag=1)
A.zone(*HALL, 'Hall of the Silent Hand', flag=1)
A.zone(722, 861, 738, 885, 'Burial Terrace', flag=1)
A.zone(721, 895, 737, 915, 'Still Pond', flag=1)
A.zone(*SANCTUM, "Abbot's Sanctum", flag=1)
A.zone(*LIBRARY, 'Library', flag=1)
json.dump({'part': sorted([list(p) + [v] for p, v in part.items()]), 'pond': sorted(POND), 'used': sorted(used),
           'cloister': CLOISTER, 'hall': HALL, 'sanctum': SANCTUM, 'library': LIBRARY, 'ruin': RUIN, 'cells': CELLS,
           'garden_in': sorted(GARDEN_IN), 'steps': {'%d,%d' % p: v for p, v in D.items()}}, open(os.path.join(HERE, 'made_terrain.json'), 'w'))
A.save()
print('outdoor', len(outdoor))
