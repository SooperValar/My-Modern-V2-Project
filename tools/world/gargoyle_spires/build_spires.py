#!/usr/bin/env python3
"""The Gargoyle Spires (Nov 19; band D, Brigadier General) east of the new pass from Stonehold to the Last Bastion, and
that pass. Cody: "like you're walking over a chasm". A gorge of mist and dark (the chasm ground 37400+, world_chasm.py,
blocks walking but not sight) with rock islands standing up out of it, each a ruined gargoyle spire, joined by narrow
snow ridges and old stone bridges (one of them broken: a false turn):

  the Ledges (the gate from the pass) -> the Broken Causeway's ridges and islands (a loop, dead ends) -> the Bell Spire
  (a ruined round tower, the Gargoyle Bellkeeper) -> one bridge -> Shrike's Eyrie in the far south-east corner.
The far side of the gorge is a rim of granite cliffs on snow all round the box (so the chasm never meets the empty map).
The pass: from Stonehold's south-east gate road (725,834) south past Elysium (walled off, west of it) to an open gap at
x 834 (the Last Bastion, not built yet); a canyon like Stonehold Pass. North = smaller x, west = smaller y.

    build_spires.py <.dat folder>      (game stopped; tools/world/arealib.py)  -> made_terrain.json"""
import sys, os, random, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.join(HERE, '..', '..', 'sprites')
CJ = json.load(open(os.path.join(SP, 'world_chasm.json')))
A = Area(sys.argv[1], seed=1190); R = random.Random(1190)
X0, X1, Y0, Y1 = 742, 830, 845, 940                        # the Spires (space plan 745-830; Cody: more to the north -> 742, the Monastery box ends at 740)
PX0, PX1, PY0, PY1 = 716, 834, 828, 842                    # the pass to the Last Bastion
YE = 965                                                   # Cody (Nov 19, live): 'you still easily see the square sides' - the gorge
AX0, AX1 = 741, 834                                        # runs on east to YE (a player sees 22 tiles); rock fills the strips
                                                           # to the Monastery (741) and toward the Last Bastion (831-834)
SH = int(sys.argv[sys.argv.index('--shift') + 1]) if '--shift' in sys.argv else 0   # Nov 19: the Spires moved 18 north (relocate_band_d.py): --shift -18
X0, X1 = X0 + SH, X1 + SH
EDGES = '--edges' in sys.argv                              # only the rock and the drop round the islands (the live world: islands,
                                                           # objects and monsters untouched)
CLIFF, BOULDER = [1204, 1206], 1208
SNOW = [35400, 35401, 35402, 35403]; SNOWY = [36100, 36101, 36102, 36103]
SNOWPINE = [38154, 38155, 38156, 38157]
CHASM = lambda m: CJ['base'] + 4 * m + R.randrange(4)
PH = [R.random() * 6.28 for _ in range(8)]

# ---------------------------------------------------------------- the pass
def pass_y(x): return 834 + int(round(1.1 * math.sin((x - PX0) / 8.0 + 0.6)))
road = {(x, pass_y(x) + d) for x in range(PX0, PX1 + 1) for d in (-1, 0, 1)}

# ---------------------------------------------------------------- the Spires: islands and the ways between them
# name -> (centre, radius, pinnacle radius: cliff blocks in the middle, a spire of rock)
# Cody (Nov 19): more spread out, more to the north; the two goals far apart (the Bell Spire at the north end, Shrike's
# Eyrie at the south end) - make the most of the space so it takes time to do it all. Two long branches from the gate,
# a middle loop, false turns (broken bridges) and dead ends.
IS = {'ledges': ((764 + SH, 852), 5.5, 0),
      # north branch -> the Bell Spire
      'n1': ((751 + SH, 866), 3.5, 0), 'n2': ((747 + SH, 883), 3.0, 1.1), 'n3': ((759 + SH, 896), 3.6, 1.4), 'n4': ((748 + SH, 909), 3.0, 0),
      'n hook': ((767 + SH, 916), 2.8, 1.0), 'bell': ((755 + SH, 927), 6.5, 0),
      # the middle: a loop and dead ends
      'm1': ((779 + SH, 889), 4.0, 0), 'm2': ((786 + SH, 911), 3.5, 1.2), 'm3': ((775 + SH, 932), 3.0, 1.0),
      # south branch -> Shrike's Eyrie
      's1': ((782 + SH, 858), 3.5, 0), 's2': ((797 + SH, 851), 2.8, 1.0), 's3': ((796 + SH, 872), 4.0, 0), 's4': ((812 + SH, 864), 3.2, 1.2),
      's5': ((822 + SH, 882), 3.2, 1.2), 's6': ((808 + SH, 897), 3.5, 0), 's7': ((822 + SH, 911), 3.0, 1.0), 'eyrie': ((815 + SH, 929), 6.6, 0)}
# (a, b, width 0 = one tile / 1 = two, kind: ridge (snow) | bridge (stone) | broken (a bridge with a gap in the middle))
WAYS = [('ledges', 'n1', 1, 'ridge'), ('n1', 'n2', 0, 'ridge'), ('n2', 'n3', 1, 'bridge'), ('n3', 'n4', 0, 'ridge'),
        ('n4', 'bell', 1, 'bridge'), ('n3', 'n hook', 0, 'ridge'),
        ('ledges', 's1', 1, 'ridge'), ('s1', 's2', 0, 'ridge'), ('s1', 's3', 1, 'bridge'), ('s3', 's4', 0, 'ridge'),
        ('s4', 's5', 1, 'ridge'), ('s5', 's6', 0, 'bridge'), ('s6', 's7', 0, 'ridge'), ('s7', 'eyrie', 1, 'bridge'),
        ('s3', 'm1', 1, 'ridge'), ('m1', 'n3', 0, 'ridge'), ('m1', 'm2', 1, 'bridge'), ('m2', 'm3', 0, 'ridge'),
        ('m2', 'bell', 1, 'broken'), ('s6', 'm2', 1, 'broken'), ('n hook', 'm2', 0, 'broken')]

def blob(c, r, x, y, k=0.16):
    a = math.atan2(y - c[1], x - c[0]); f = 1 + k * math.sin(3 * a + PH[0]) + 0.6 * k * math.sin(5 * a + PH[1])
    return math.hypot(x - c[0], y - c[1]) <= r * f

def way_tiles(a, b, w, seed):
    """a gently wandering line of tiles from a to b, w=0 one tile wide (a diagonal step still joins up), w=1 two"""
    r = random.Random(seed); (ax, ay), (bx, by) = a, b; n = int(max(abs(bx - ax), abs(by - ay)) * 2) + 1
    L = math.hypot(bx - ax, by - ay); px, py = -(by - ay) / L, (bx - ax) / L; amp = r.uniform(-1.6, 1.6); out = []
    last = None
    for i in range(n + 1):
        f = i / n; o = amp * math.sin(math.pi * f)
        p = (int(round(ax + (bx - ax) * f + px * o)), int(round(ay + (by - ay) * f + py * o)))
        if last and abs(p[0] - last[0]) == 1 and abs(p[1] - last[1]) == 1: out.append((p[0], last[1]))    # no corner-only steps
        out.append(p); last = p
        if w: out.append((p[0] + (1 if abs(by - ay) >= abs(bx - ax) else 0), p[1] + (0 if abs(by - ay) >= abs(bx - ax) else 1)))
    return out, f

land, part = set(), {}
for name, (c, r, _) in IS.items():
    for x in range(int(c[0] - r - 3), int(c[0] + r + 4)):
        for y in range(int(c[1] - r - 3), int(c[1] + r + 4)):
            if blob(c, r, x, y): land.add((x, y)); part[(x, y)] = name
bridge, gap = set(), set()
for i, (a, b, w, kind) in enumerate(WAYS):
    tiles, _ = way_tiles(IS[a][0], IS[b][0], w, 77 * i + 3)
    k = len(tiles)
    for j, p in enumerate(tiles):
        if p in part: continue                                  # the islands' own ground
        if kind == 'broken' and 0.42 * k <= j <= 0.58 * k: gap.add(p); continue
        land.add(p); part[p] = 'way'
        if kind in ('bridge', 'broken'): bridge.add(p)
# the gate: the ledges reach west to the pass's east wall
GATE = [(x, y) for x in range(764 + SH, 768 + SH) for y in range(843, 849)]
for p in GATE: land.add(p); part.setdefault(p, 'ledges')
# lone rock pillars standing up out of the gorge, out of reach (scenery: the drop needs something to measure it by)
pillars = set(); tries = 0
while len([1 for _ in pillars]) < 95 and tries < 4000:
    tries += 1; c = (R.uniform(X0 + 5, X1 - 5), R.uniform(Y0 + 5, Y1 - 5)); r = R.uniform(0.7, 1.9)
    near = [(x, y) for x in range(int(c[0]) - 5, int(c[0]) + 6) for y in range(int(c[1]) - 5, int(c[1]) + 6)]
    if any(p in land or p in gap or p in pillars for p in near if math.hypot(p[0] - c[0], p[1] - c[1]) <= r + 3.2): continue
    for x, y in near:
        if math.hypot(x - c[0], y - c[1]) <= r: pillars.add((x, y))
R2 = random.Random(1194); tries = 0; n0 = len(pillars)
while len(pillars) < n0 + 45 and tries < 4000:
    tries += 1; c = (R2.uniform(X0 + 6, X1 - 6), R2.uniform(Y1 - 2, YE - 5)); r = R2.uniform(0.7, 2.0)
    near = [(x, y) for x in range(int(c[0]) - 5, int(c[0]) + 6) for y in range(int(c[1]) - 5, int(c[1]) + 6)]
    if any(p in land or p in gap or p in pillars for p in near if math.hypot(p[0] - c[0], p[1] - c[1]) <= r + 3.2): continue
    for x, y in near:
        if math.hypot(x - c[0], y - c[1]) <= r: pillars.add((x, y))
# Cody (Nov 19): no walls within 25 tiles of anywhere a player can reach, except Bastion Road's on the west. The drop
# runs from x CX0 to CX1 (26+ tiles past the islands north and south; the Monastery, moved north, ends at 698; the Last
# Bastion's space starts at 835) and on east to YE; the far rim is a thin line of rock beyond that, out of sight.
LX0, LX1 = min(p[0] for p in land), max(p[0] for p in land)
CX0, CX1 = max(699, LX0 - 27), min(834, LX1 + 27)
AX0, AX1 = CX0, CX1
R3 = random.Random(1195); tries = 0; n0 = len(pillars)
while len(pillars) < n0 + 70 and tries < 6000:          # lone pillars in the wider drop north and south too
    tries += 1; c = (R3.uniform(CX0 + 4, CX1 - 4), R3.uniform(Y0 + 6, YE - 5)); r = R3.uniform(0.7, 2.0)
    if X0 + 3 < c[0] < X1 - 3: continue
    near = [(x, y) for x in range(int(c[0]) - 5, int(c[0]) + 6) for y in range(int(c[1]) - 5, int(c[1]) + 6)]
    if any(p in land or p in gap or p in pillars for p in near if math.hypot(p[0] - c[0], p[1] - c[1]) <= r + 3.2): continue
    for x, y in near:
        if math.hypot(x - c[0], y - c[1]) <= r: pillars.add((x, y))
def rim(x, y):
    n = 0.5 + 0.5 * math.sin(x * 0.09 + PH[2]) * math.sin(y * 0.08 + PH[3])
    if x <= CX0 + 1 or x >= CX1 - 1 or YE - y < 2: return True                 # the far side, out of sight
    return y - Y0 < 1.5 + 2.5 * max(0.0, n) and (x, y) not in land               # along Bastion Road (the west): a ragged foot
inbox = lambda x, y: AX0 <= x <= AX1 and Y0 <= y <= YE

# ---------------------------------------------------------------- write it
for x in range(726, PX1 + 1):                                 # the pass (Stonehold's own ground and gate road end at 725)
    for y in range(PY0, Y0):                                  # to 844: the strip up to the Spires' box
        A.clear(x, y)
        for b in range(2, 15): A.op(op='flag', x=x, y=y, bit=b, mode=0)          # old map flags off (Nov 18 rule)
        A.op(op='flag', x=x, y=y, bit=5, mode=1)                                  # no monsters on the road (like Stonehold Pass)
        if (x, y) in GATE: A.op(op='floor', x=x, y=y, s=R.choice(SNOW), set=False); continue
        if (x, y) in road: A.op(op='floor', x=x, y=y, s=R.choice(PATH), set=False); continue
        d = abs(y - pass_y(x)); wall = 3 + int(round(1.2 * math.sin(x / 4.0 + (0 if y < pass_y(x) else 2)) + R.uniform(-0.5, 0.5)))
        if (x, y) in GATE or (y > pass_y(x) and 763 + SH <= x <= 768 + SH and y <= 842): wall = 99                  # the opening to the Spires
        if d >= wall:
            A.op(op='floor', x=x, y=y, s=R.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3); continue
        A.op(op='floor', x=x, y=y, s=R.choice(SNOWY if d < wall - 1 or R.random() < 0.5 else SNOW), set=False)
        if d >= 2 and R.random() < 0.05: A.op(op='object', x=x, y=y, s=R.choice(SNOWPINE), block=1)
A.run('the pass')
for x in range(AX0, AX1 + 1):
    for y in range(Y0, YE + 1):
        if EDGES and (x, y) in land: continue
        A.clear(x, y)
        for b in range(2, 15): A.op(op='flag', x=x, y=y, bit=b, mode=0)
        if (x, y) in land:
            A.op(op='floor', x=x, y=y, s=R.choice(FLAGSTONE if (x, y) in bridge else SNOW), set=False)
        elif rim(x, y) or (x, y) in pillars:
            A.op(op='floor', x=x, y=y, s=R.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3)
        elif False:
            A.op(op='floor', x=x, y=y, s=R.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3)
A.run('spires: islands, ways, rim, pillars')
solid = lambda x, y: (x, y) in land or (x, y) in pillars or rim(x, y) if inbox(x, y) else A.floor(x, y) != VOID
chasm = [(x, y) for x in range(AX0, AX1 + 1) for y in range(Y0, YE + 1) if (x, y) not in land and (x, y) not in pillars and not rim(x, y)]
for x, y in chasm:
    m = solid(x - 1, y) * 1 + solid(x, y + 1) * 2 + solid(x - 1, y + 1) * 4 + solid(x - 2, y + 1) * 8 + solid(x - 1, y + 2) * 16
    A.op(op='floor', x=x, y=y, s=CHASM(m), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
A.run('the chasm')
# Cody (Nov 19): no empty map in sight. Every empty tile within a player's view (22) of the Spires' islands becomes
# mountain (snow under granite) - the Monastery's empty margin and the strip by Bastion Road included; never the space
# reserved for the Last Bastion / Barbarian Highlands (x 835 on), never anything already built (only VOID tiles)
from collections import deque
far = {p: 0 for p in land}; q = deque(land)
while q:
    p = q.popleft()
    if far[p] >= 22: continue
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (p[0] + dx, p[1] + dy)
        if n not in far and 640 <= n[0] <= 834 and 820 <= n[1] <= YE + 6: far[n] = far[p] + 1; q.append(n)
filled = 0
for (x, y) in far:
    if inbox(x, y) or A.floor(x, y) != VOID: continue
    A.op(op='floor', x=x, y=y, s=R2.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=R2.choice(CLIFF), block=3); filled += 1
A.run('mountain round the Spires'); print('  mountain filled', filled)
if EDGES:
    A.zone(CX0, Y0, CX1, YE, 'Gargoyle Spires', flag=1); A.save()
    print('edges only: chasm', len(chasm), 'pillar tiles', len(pillars)); sys.exit(0)

# ---------------------------------------------------------------- spires, the Bell Spire's tower, the Eyrie's crags
used = set()
for name, (c, r, pr) in IS.items():
    if not pr: continue
    for (x, y) in [p for p in land if part.get(p) == name]:
        if blob(c, pr, x, y, k=0.3): A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3); used.add((x, y))
bc = IS['bell'][0]; tower = set()
for (x, y) in [p for p in land if part.get(p) == 'bell']:
    d = math.hypot(x - bc[0], y - bc[1])
    if d <= 4.6: A.op(op='floor', x=x, y=y, s=R.choice(FLAGSTONE), set=False)
    if 3.9 <= d <= 4.6:
        a = math.degrees(math.atan2(y - bc[1], x - bc[0])) % 360
        dirs = [math.degrees(math.atan2(IS[o][0][1] - bc[1], IS[o][0][0] - bc[0])) % 360 for w in WAYS for o in w[:2] if 'bell' in w[:2] and o != 'bell']
        door = min(min(abs(a - t), 360 - abs(a - t)) for t in dirs) < 34      # gaps toward every way in (wide enough to walk straight in)
        if not door and R.random() < 0.72: A.op(op='object', x=x, y=y, s=R.choice(W_CRACKED), block=3); tower.add((x, y))
used |= tower
ec = IS['eyrie'][0]
for (x, y) in [p for p in land if part.get(p) == 'eyrie']:
    d = math.hypot(x - ec[0], y - ec[1])
    if d >= 5.6 and R.random() < 0.55 and not any((x + dx, y + dy) in bridge for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)):
        A.op(op='object', x=x, y=y, s=R.choice(CLIFF + [BOULDER]), block=3); used.add((x, y))
A.run('spires, tower, crags')
# a few boulders and snowy pines on the bigger islands, kept off the ways and their ends
open_ = [p for p in land if part.get(p) not in ('bell', 'eyrie', 'way', None) and p not in used
         and all((p[0] + dx, p[1] + dy) in land and part.get((p[0] + dx, p[1] + dy)) != 'way' for dx in (-1, 0, 1) for dy in (-1, 0, 1))
         and p not in GATE]
R.shuffle(open_); n = 0
for p in open_:
    if n >= 20: break
    if any(abs(p[0] - a) + abs(p[1] - b) < 4 for a, b in used): continue
    s = R.choice([BOULDER] + SNOWPINE); A.op(op='object', x=p[0], y=p[1], s=s, block=3 if s == BOULDER else 1); used.add(p); n += 1
A.run('boulders and pines')
# no closed pockets: walk the islands from the gate (straight steps only); while a walkable tile can't be reached, take away
# a tower wall / crag / boulder between it and the reached ground
from collections import deque
GATE0 = (765 + SH, 846)
def reach():
    walk = {p for p in land if p not in used}; D = {GATE0}; q = deque([GATE0])
    while q:
        p = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (p[0] + dx, p[1] + dy)
            if n in walk and n not in D: D.add(n); q.append(n)
    return walk, D
opened = 0
while True:
    walk, D = reach(); lost = walk - D
    if not lost: break
    cut = None
    for p in sorted(used & set(land)):
        nb = [(p[0] + dx, p[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        if any(n in D for n in nb) and any(n in lost for n in nb) and part.get(p) in ('bell', 'eyrie') or (any(n in D for n in nb) and any(n in lost for n in nb) and p not in pillars):
            cut = p; break
    if not cut: print('  ! closed pockets left:', len(lost)); break
    A.op(op='erase', x=cut[0], y=cut[1]); A.run('open a pocket'); used.discard(cut); tower.discard(cut); opened += 1
print('pockets opened', opened)

A.zone(726, PY0, PX1, Y0 - 1, 'Bastion Road', flag=1)
A.zone(CX0, Y0, CX1, YE, 'Gargoyle Spires', flag=1)
A.zone(771 + SH, 880, 793 + SH, 937, 'Broken Causeway', flag=1)
A.zone(bc[0] - 7, bc[1] - 7, bc[0] + 7, bc[1] + 7, 'Bell Spire', flag=1)
A.zone(ec[0] - 8, ec[1] - 8, min(X1, ec[0] + 8), min(Y1, ec[1] + 8), "Shrike's Eyrie", flag=0)     # no "the" before a name with 's
json.dump({'land': sorted([list(p) + [part[p]] for p in land]), 'bridge': sorted(bridge), 'used': sorted(used), 'tower': sorted(tower),
           'islands': {k: [v[0], v[1], v[2]] for k, v in IS.items()}, 'road': sorted(road)}, open(os.path.join(HERE, 'made_terrain.json'), 'w'))
A.save()
print('land', len(land), 'pillar tiles', len(pillars), 'chasm', len(chasm), 'bridge', len(bridge), 'gap', len(gap))
