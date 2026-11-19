#!/usr/bin/env python3
"""The Ashen Fields (Nov 18; band D, Colonel), south-west of Stonehold. Cody's choice: an ash canyon high on the mountain
- "stick to the whole mountain top theme". One winding ravine of grey ash between granite cliffs, from Stonehold's
south-west gate road (726,785) down to the Flame Lord's lava cavern at the far south end:

  a maze of narrow ravines between small chambers (Cody: "more maze like... don't want it to be so easy to find the
  bosses"): a loop, false turns and dead-end pockets. Snow at the mouth; Ashra's Hollow at the end of the long north-west
  branch; the Smoking Steps (cinders, vents) in the east; the Ember Cavern (the Flame Lord, pools of molten rock) at the
  far south, reached only through the Smoking Steps.
The ground grows darker and hotter (more cinders) the deeper you go. Everything else in the box is granite cliff on snow,
like Stonehold and the Foundry. North = smaller x, west = smaller y.

    build_ashen.py <.dat folder>      (game stopped; tools/world/arealib.py)  -> made_terrain.json"""
import sys, os, random, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'sprites'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.join(HERE, '..', '..', 'sprites')
AJ = json.load(open(os.path.join(SP, 'world_ash.json'))); OJ = json.load(open(os.path.join(SP, 'world_ashen.json'))); FJ = json.load(open(os.path.join(SP, 'world_foundry.json')))
A = Area(sys.argv[1], seed=1180); R = random.Random(1180)
X0, X1, Y0, Y1 = 725, 815, 690, 787
CLIFF, BOULDER = [1204, 1206], 1208
SNOW = [35400, 35401, 35402, 35403]; SNOWY = [36100, 36101, 36102, 36103]
ASH, CIND = AJ['plain']['ash'], AJ['plain']['cinders']; LAVA = FJ['molten']['plain']                   # the Foundry's molten iron (Cody tried the game's lava: the molten iron looks better)

# ---------------------------------------------------------------- the shape: a maze of ravines
# chambers: name -> (centre, radius, depth 0..1). Cody (Nov 18): "a little more maze like... more than 3 little end rooms,
# don't want it to be so easy to find the bosses" - loops, false turns and dead-end pockets; Ashra and the Flame Lord
# each sit at the end of a long winding branch.
CH = {'mouth': ((727, 785), 0, 0.0), 'snowfall': ((741, 774), 4.5, 0.08), 'fork': ((751, 757), 4.0, 0.2),
      'ledge': ((737, 741), 5.0, 0.3), 'cold pocket': ((731, 714), 4.0, 0.3), 'crossing': ((757, 728), 4.5, 0.45),
      'cinder cut': ((766, 705), 3.5, 0.55), 'hollow': ((749, 697), 6.5, 0.6), 'basin': ((771, 762), 5.5, 0.4),
      'east pocket': ((783, 780), 4.0, 0.45), 'ash flats': ((782, 742), 5.5, 0.6), 'smoking steps': ((794, 726), 5.0, 0.75),
      'scorch': ((801, 752), 4.0, 0.7), 'deep pocket': ((809, 772), 4.0, 0.75), 'cavern': ((804, 702), 10.0, 1.0),
      'false turn': ((787, 703), 3.0, 0.85)}
RAV = [('mouth', 'snowfall'), ('snowfall', 'fork'), ('fork', 'ledge'), ('ledge', 'cold pocket'), ('ledge', 'crossing'),
       ('fork', 'basin'), ('basin', 'east pocket'), ('basin', 'ash flats'), ('crossing', 'ash flats'),       # a loop
       ('crossing', 'cinder cut'), ('cinder cut', 'hollow'), ('ash flats', 'scorch'), ('scorch', 'deep pocket'),
       ('ash flats', 'smoking steps'), ('smoking steps', 'false turn'), ('smoking steps', 'cavern')]
def wiggle(a, b, seed, amp=2.2, n=5):
    """a ravine from a to b that wanders (midpoints pushed sideways)"""
    r = random.Random(seed); (ax, ay), (bx, by) = a, b; L = math.hypot(bx - ax, by - ay); px, py = -(by - ay) / L, (bx - ax) / L
    pts = [a]
    for k in range(1, n):
        f = k / n; o = r.uniform(-amp, amp) * math.sin(math.pi * f) * min(1.0, L / 12)
        pts.append((ax + (bx - ax) * f + px * o, ay + (by - ay) * f + py * o))
    return pts + [b]
PATHS = [(wiggle(CH[a][0], CH[b][0], 31 * i + 7), CH[a][2], CH[b][2]) for i, (a, b) in enumerate(RAV)]

def seg_d(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy or 1)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy), t

def along(path, p):
    """distance to the path and how far along it (0..1)"""
    L = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]; tot = sum(L) or 1; best = (1e9, 0); acc = 0
    for (a, b), l in zip(zip(path, path[1:]), L):
        d, t = seg_d(p, a, b)
        if d < best[0]: best = (d, (acc + t * l) / tot)
        acc += l
    return best

PH = [R.random() * 6.28 for _ in range(6)]
def wob(x, y, k=1.0): return k * (0.7 * math.sin(x * 0.37 + PH[0]) * math.sin(y * 0.29 + PH[1]) + 0.4 * math.sin((x + y) * 0.21 + PH[2]))
def blob(c, r, x, y, k=0.15):
    a = math.atan2(y - c[1], x - c[0]); f = 1 + k * math.sin(3 * a + PH[3]) + k * 0.6 * math.sin(5 * a + PH[4])
    return math.hypot(x - c[0], y - c[1]) <= r * f

def where(x, y):
    """(part, depth 0..1) of a canyon tile, or None for cliff"""
    for name, (c, r, t) in CH.items():
        if r and blob(c, r, x, y): return name, t
    for pts, t0, t1 in PATHS:
        d, f = along(pts, (x, y))
        if d <= 1.7 + 0.5 * wob(x, y): return 'ravine', t0 + (t1 - t0) * f
    return None

def centre_d(p):
    return min(along(pts, p)[0] for pts, _, _ in PATHS)

canyon = {}
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        p = where(x, y)
        if p: canyon[(x, y)] = p
# the gate road's end (725-726, 784-786) joins the mouth
for y in (784, 785, 786): canyon[(725, y)] = ('ravine', 0.0); canyon[(726, y)] = ('ravine', 0.0)
CAVERN_C, CAVERN_R = CH['cavern'][0], CH['cavern'][1]; HOLLOW_C, HOLLOW_R = CH['hollow'][0], CH['hollow'][1]
# lava: pools in the cavern (blocked, like the Foundry's molten iron)
POOLS = [((801, 698), 2.4), ((807, 707), 2.2), ((809, 697), 1.6), ((798, 707), 1.4)]
lava = {p for p in canyon if canyon[p][0] == 'cavern' and any(blob(c, r, *p, k=0.25) for c, r in POOLS)}

def ground(x, y):
    part, t = canyon[(x, y)]
    n = 0.5 + 0.35 * math.sin(x * 0.31 + PH[1]) * math.sin(y * 0.27 + PH[2]) + 0.2 * math.sin((x - y) * 0.23 + PH[3]) + R.uniform(-0.05, 0.05)
    if t < 0.03: return R.choice(SNOWY)
    if t < 0.30 and n > 0.78 - 0.6 * (0.30 - t): return R.choice(SNOW)          # snow lies near the mouth
    if part == 'cavern': return R.choice(CIND)
    if part in ('smoking steps', 'scorch', 'false turn'): return R.choice(CIND) if n > 0.5 else R.choice(ASH)
    if t > 0.5 and n > 1.2 - 0.7 * t: return R.choice(CIND)                      # cinders grow deeper in
    return R.choice(ASH)

# ---------------------------------------------------------------- ground and cliffs
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if A.floor(x, y) != VOID and (x, y) not in canyon: continue                # never touch what is already built
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='flag', x=x, y=y, bit=5, mode=0)
        if (x, y) in canyon: A.op(op='floor', x=x, y=y, s=ground(x, y), set=False); continue
        near = [(abs(dx) + abs(dy), canyon[(x + dx, y + dy)][1]) for dx in range(-3, 4) for dy in range(-3, 4) if (x + dx, y + dy) in canyon]
        if not near: continue                                                       # deep inside the mountain: left empty (Cody: no blocks nobody sees)
        cold = min(near)[1] < 0.42                                                  # snow at the cliff foot near the mouth, ash deeper in
                                                        # snow at the cliff foot near the mouth, ash deeper in
        A.op(op='floor', x=x, y=y, s=R.choice(SNOW if cold else ASH), set=False); A.op(op='object', x=x, y=y, s=R.choice(CLIFF), block=3)
A.run('ashen fields: ground and cliffs')
for x, y in lava:
    A.op(op='floor', x=x, y=y, s=R.choice(LAVA), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
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
# lava creeping into the cinders round the pools
for x, y in [p for p in canyon if p not in lava]:
    if A.floor(x, y) not in CIND: continue
    m = wg.mask_of(lambda dx, dy: (x + dx, y + dy) in lava)
    if m: A.op(op='floor', x=x, y=y, s=AJ['cinders_base']['molten'][str(m)], set=False)
A.run('lava edges')

# ---------------------------------------------------------------- rocks, charred trees, slag and smoking vents
CHARRED, STUMPS = OJ['charred tree'], OJ['charred stump']
VENT_T = [A.item(741, 'Smoking Vent', 'A crack in the rock, breathing hot smoke. Something burns far below.', sprite=[s, 0], light=[110, 0])
          for s in OJ['vent'][0:4:2]]          # two looks, from the fire bowl (it gives light)
ROCK_T = [A.item(src, 'Cinder Rock', 'A lump of cooled lava, grey with ash. It is still warm.', sprite=[s, 0], value=0)
          for src, s in zip((517, 518, 519), OJ['cinder rock'])]          # the lava stones in the ash's greys (Cody)
free = [p for p in canyon if p not in lava and canyon[p][1] > 0.04 and not any((p[0] + dx, p[1] + dy) not in canyon for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
R.shuffle(free); used = set()
def far(p, k=3): return all(abs(p[0] - a) + abs(p[1] - b) >= k for a, b in used)
def path_clear(p):  # keep the middle of every ravine walkable
    return centre_d(p) > 1.3
counts = {'boulder': 20, 'rock': 22, 'dead': 30, 'stump': 12, 'vent': 10, 'slag': 22}
for kind, n in counts.items():
    c = 0
    for p in free:
        if c >= n: break
        if p in used or not far(p) or not path_clear(p): continue
        part, t = canyon[p]
        if kind == 'slag' and t < 0.4: continue
        if kind in ('dead', 'stump', 'boulder', 'rock') and part == 'cavern': continue        # the cavern stays open for the fight
        if kind == 'vent' and t < 0.35: continue
        used.add(p); c += 1
        if kind == 'boulder': A.op(op='object', x=p[0], y=p[1], s=BOULDER, block=3)
        elif kind == 'rock': A.op(op='object', x=p[0], y=p[1], s=16376, block=3)          # the grey rock (the others are sandstone)
        elif kind == 'dead': A.op(op='object', x=p[0], y=p[1], s=R.choice(CHARRED), block=1)
        elif kind == 'stump': A.op(op='object', x=p[0], y=p[1], s=R.choice(STUMPS), block=1)
        elif kind == 'vent': A.op(op='place', x=p[0], y=p[1], t=R.choice(VENT_T), fresh=1)
        else: A.op(op='place', x=p[0], y=p[1], t=R.choice(ROCK_T), fresh=1)
A.run('rocks, charred trees, slag, vents')
rim = [p for p in canyon if p not in lava and p not in used and canyon[p][0] == 'cavern' and any((p[0] + dx, p[1] + dy) in lava for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
R.shuffle(rim); k = 0
for p in rim:
    if k >= 4: break
    if not far(p, 4): continue
    used.add(p); k += 1; A.op(op='place', x=p[0], y=p[1], t=R.choice(VENT_T), fresh=1)
A.run('vents by the lava')

A.zone(X0, Y0, X1, Y1, 'Ashen Fields', flag=1)
A.zone(int(HOLLOW_C[0] - HOLLOW_R - 1), int(HOLLOW_C[1] - HOLLOW_R - 1), int(HOLLOW_C[0] + HOLLOW_R + 1), int(HOLLOW_C[1] + HOLLOW_R + 1), "Ashra's Hollow", flag=1)
A.zone(int(CAVERN_C[0] - CAVERN_R - 1), int(CAVERN_C[1] - CAVERN_R - 1), min(X1, int(CAVERN_C[0] + CAVERN_R + 1)), int(CAVERN_C[1] + CAVERN_R + 1), 'the Ember Cavern', flag=1)
c = CH['smoking steps'][0]; A.zone(c[0] - 6, c[1] - 6, c[0] + 6, c[1] + 6, 'the Smoking Steps', flag=1)
json.dump({'vent_templates': VENT_T, 'rock_templates': ROCK_T, 'canyon': sorted([list(p) + [v[0], round(v[1], 3)] for p, v in canyon.items()]), 'lava': sorted(lava), 'used': sorted(used),
           'chambers': {k: [v[0], v[1], v[2]] for k, v in CH.items()}}, open(os.path.join(HERE, 'made_terrain.json'), 'w'))
A.save()
print('canyon tiles', len(canyon), 'lava', len(lava))
