#!/usr/bin/env python3
"""The Ashen Fields (Nov 18; band D, Colonel), south-west of Stonehold. Cody's choice: an ash canyon high on the mountain
- "stick to the whole mountain top theme". One winding ravine of grey ash between granite cliffs, from Stonehold's
south-west gate road (726,785) down to the Flame Lord's lava cavern at the far south end:

  - the mouth: snow lingers on the ash, snowy grass at the very start (by the gate road)
  - Ashra's Hollow: a side ravine to the north-west ending in a round hollow (Ashra the Cinder Witch)
  - the Smoking Steps: a side ravine to the east, a dead end of cinders and vents (Ash Gargoyles)
  - the Ember Cavern: a round cavern at the south end, cinders round pools of molten rock (the Flame Lord)
The ground grows darker and hotter (more cinders) the deeper you go. Everything else in the box is granite cliff on snow,
like Stonehold and the Foundry. North = smaller x, west = smaller y.

    build_ashen.py <.dat folder>      (game stopped; tools/world/arealib.py)  -> made_terrain.json"""
import sys, os, random, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'sprites'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.join(HERE, '..', '..', 'sprites')
AJ = json.load(open(os.path.join(SP, 'world_ash.json'))); FJ = json.load(open(os.path.join(SP, 'world_foundry.json')))
A = Area(sys.argv[1], seed=1180); R = random.Random(1180)
X0, X1, Y0, Y1 = 725, 815, 690, 787
CLIFF, BOULDER = [1204, 1206], 1208
SNOW = [35400, 35401, 35402, 35403]; SNOWY = [36100, 36101, 36102, 36103]
ASH, CIND = AJ['plain']['ash'], AJ['plain']['cinders']; MOLTEN = FJ['molten']['plain']
LAVA_STONES = [517, 518, 519]

# ---------------------------------------------------------------- the shape
MAIN = [(726, 785), (733, 782), (741, 776), (747, 767), (750, 757), (752, 747), (757, 739), (765, 733), (774, 730),
        (783, 728), (791, 723), (797, 716)]
HOLLOW_PATH = [(751, 752), (746, 744), (741, 736), (738, 729)]
STEPS_PATH = [(774, 731), (780, 740), (786, 749), (789, 759), (792, 768)]
HOLLOW_C, HOLLOW_R = (737, 722), 8.0
CAVERN_C, CAVERN_R = (803, 707), 10.5
STEPS_C, STEPS_R = (793, 769), 6.0

def seg_d(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy), t

def along(path, p):
    """distance to the path and how far along it (0..1)"""
    L = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]; tot = sum(L); best = (1e9, 0); acc = 0
    for (a, b), l in zip(zip(path, path[1:]), L):
        d, t = seg_d(p, a, b)
        if d < best[0]: best = (d, (acc + t * l) / tot)
        acc += l
    return best

PH = [R.random() * 6.28 for _ in range(6)]
def wob(x, y, k=1.0): return k * (0.9 * math.sin(x * 0.37 + PH[0]) * math.sin(y * 0.29 + PH[1]) + 0.6 * math.sin((x + y) * 0.21 + PH[2]))
def blob(c, r, x, y, k=0.13):
    a = math.atan2(y - c[1], x - c[0]); f = 1 + k * math.sin(3 * a + PH[3]) + k * 0.6 * math.sin(5 * a + PH[4])
    return math.hypot(x - c[0], y - c[1]) <= r * f

def where(x, y):
    """(part, depth 0..1) of a canyon tile, or None for cliff"""
    d, t = along(MAIN, (x, y)); w = (2.6 if t < 0.06 else 4.0 + 1.3 * math.sin(t * 9 + PH[5])) + wob(x, y)
    if blob(CAVERN_C, CAVERN_R, x, y): return 'cavern', 1.0
    if blob(HOLLOW_C, HOLLOW_R, x, y): return 'hollow', 0.55
    if blob(STEPS_C, STEPS_R, x, y): return 'steps', 0.8
    if d <= w: return 'main', t
    d2, t2 = along(HOLLOW_PATH, (x, y))
    if d2 <= 2.3 + 0.6 * wob(x, y): return 'hollow', 0.45 + 0.1 * t2
    d3, t3 = along(STEPS_PATH, (x, y))
    if d3 <= 2.6 + 0.7 * wob(y, x): return 'steps', 0.6 + 0.2 * t3
    return None

canyon = {}
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        p = where(x, y)
        if p: canyon[(x, y)] = p
# the gate road's end (726,784-786) joins the mouth
for y in (784, 785, 786): canyon[(725, y)] = ('main', 0.0); canyon[(726, y)] = ('main', 0.0)
# lava: pools in the cavern (blocked, like the Foundry's molten iron)
POOLS = [((800, 703), 2.6), ((806, 712), 2.2), ((808, 701), 1.8), ((797, 711), 1.5)]
lava = {p for p in canyon if canyon[p][0] == 'cavern' and any(blob(c, r, *p, k=0.25) for c, r in POOLS)}

def ground(x, y):
    part, t = canyon[(x, y)]
    n = 0.5 + 0.35 * math.sin(x * 0.31 + PH[1]) * math.sin(y * 0.27 + PH[2]) + 0.2 * math.sin((x - y) * 0.23 + PH[3]) + R.uniform(-0.05, 0.05)
    if t < 0.03: return R.choice(SNOWY)
    if t < 0.30 and n > 0.78 - 0.6 * (0.30 - t): return R.choice(SNOW)          # snow lies near the mouth
    if part == 'cavern': return R.choice(CIND)
    if part == 'steps': return R.choice(CIND) if n > 0.55 else R.choice(ASH)
    if t > 0.5 and n > 1.2 - 0.7 * t: return R.choice(CIND)                      # cinders grow deeper in
    return R.choice(ASH)

# ---------------------------------------------------------------- ground and cliffs
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if A.floor(x, y) != VOID and (x, y) not in canyon: continue                # never touch what is already built
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='flag', x=x, y=y, bit=5, mode=0)
        if (x, y) in canyon: A.op(op='floor', x=x, y=y, s=ground(x, y), set=False); continue
        near = [(abs(dx) + abs(dy), canyon[(x + dx, y + dy)][1]) for dx in range(-4, 5) for dy in range(-4, 5) if (x + dx, y + dy) in canyon]
        if not near: continue                                                       # deep inside the mountain: leave it empty
        cold = min(near)[1] < 0.42                                                  # snow at the cliff foot near the mouth, ash deeper in
        A.op(op='floor', x=x, y=y, s=R.choice(SNOW if cold else ASH), set=False); A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3)
A.run('ashen fields: ground and cliffs')
for x, y in lava:
    A.op(op='floor', x=x, y=y, s=R.choice(MOLTEN), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
A.run('lava pools')
# soft edges on the ash: cinders, snow or snowy grass creeping in (as the editor's _autoedge)
import world_ground as wg
KIND = {**{s: 'cinders' for s in CIND}, **{s: 'soft snow' for s in SNOW}, **{s: 'snowy grass' for s in SNOWY}}
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if A.floor(x, y) not in ASH: continue
        for name in ('cinders', 'soft snow', 'snowy grass'):
            m = wg.mask_of(lambda dx, dy: KIND.get(A.floor(x + dx, y + dy)) == name)
            if m: A.op(op='floor', x=x, y=y, s=AJ['ash_base'][name][str(m)], set=False); break
A.run('ash edges')
# molten rock creeping into the cinders round the pools
for x, y in [p for p in canyon if p not in lava]:
    if A.floor(x, y) not in CIND: continue
    m = wg.mask_of(lambda dx, dy: (x + dx, y + dy) in lava)
    if m: A.op(op='floor', x=x, y=y, s=AJ['cinders_base']['molten'][str(m)], set=False)
A.run('lava edges')

# ---------------------------------------------------------------- rocks and dead trees (charred trees and vents come later)
free = [p for p in canyon if p not in lava and canyon[p][1] > 0.04 and not any((p[0] + dx, p[1] + dy) not in canyon for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
R.shuffle(free); used = set()
def far(p, k=3): return all(abs(p[0] - a) + abs(p[1] - b) >= k for a, b in used)
def path_clear(p):  # keep the middle of the main ravine walkable
    d, t = along(MAIN, p); return d > 1.6 or canyon[p][0] != 'main'
counts = {'boulder': 18, 'rock': 22, 'dead': 26, 'slag': 30}
for kind, n in counts.items():
    c = 0
    for p in free:
        if c >= n: break
        if p in used or not far(p) or not path_clear(p): continue
        part, t = canyon[p]
        if kind == 'slag' and t < 0.4: continue
        if kind == 'dead' and part == 'cavern': continue
        used.add(p); c += 1
        if kind == 'boulder': A.op(op='object', x=p[0], y=p[1], s=BOULDER, block=3)
        elif kind == 'rock': A.op(op='object', x=p[0], y=p[1], s=16376, block=3)          # the grey rock (the others are sandstone)
        elif kind == 'dead': A.op(op='object', x=p[0], y=p[1], s=R.choice(DEAD), block=1)
        else: A.op(op='place', x=p[0], y=p[1], t=R.choice(LAVA_STONES), fresh=1)
A.run('rocks, dead trees, slag')

A.zone(X0, Y0, X1, Y1, 'Ashen Fields', flag=1)
A.zone(int(HOLLOW_C[0] - HOLLOW_R), int(HOLLOW_C[1] - HOLLOW_R), int(HOLLOW_C[0] + HOLLOW_R), int(HOLLOW_C[1] + HOLLOW_R), "Ashra's Hollow", flag=1)
A.zone(int(CAVERN_C[0] - CAVERN_R - 1), int(CAVERN_C[1] - CAVERN_R - 1), int(CAVERN_C[0] + CAVERN_R + 1), int(CAVERN_C[1] + CAVERN_R + 1), 'the Ember Cavern', flag=1)
A.zone(780, 742, 799, 776, 'the Smoking Steps', flag=1)
json.dump({'canyon': sorted([list(p) + [v[0], round(v[1], 3)] for p, v in canyon.items()]), 'lava': sorted(lava), 'used': sorted(used),
           'hollow': HOLLOW_C, 'cavern': CAVERN_C, 'steps': STEPS_C}, open(os.path.join(HERE, 'made_terrain.json'), 'w'))
A.save()
print('canyon tiles', len(canyon), 'lava', len(lava))
