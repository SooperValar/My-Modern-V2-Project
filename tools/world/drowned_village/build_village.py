#!/usr/bin/env python3
"""The Drowned Village (Nov 16): east of Fenwatch, Sergeant Major to Second Lieutenant. A sunken fishing village in
the marsh, Maud the Bog Witch's island in the bog (north-east), the flooded chapel (under water: MF_UWATER, breath
runs out; Swimming helps) and the shore with Captain Morrow's wreck (south-east).

    build_village.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)

Terrain only; the monsters, items and quests come from place_village.py. Map: x grows down-right (south), y up-right (east)."""
import sys, os, random, json, math, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1118)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/MyV2/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
MT = json.load(open(os.path.join(HERE, '..', '..', 'sprites', 'world_marsh.json'))); REEDS = MT['reeds']
OPS = []
def op(**k): OPS.append(k)
def run(label):
    global OPS
    n, msgs = W.apply(OPS, label)
    for m in msgs: print('  !', m)
    OPS = []
MARSH = [35700, 35701, 35702, 35703]; MUD = [35750, 35751, 35752, 35753]; WATER = [35800, 35801, 35802, 35803]
PATH = [35000, 35001, 35002, 35003]; SAND = [35200, 35201, 35202, 35203]; DEEP = [16933, 16957, 16958, 16959]
DARKWOOD = [37010, 37011, 37012, 37013]; OAK = [37000, 37001, 37002, 37003]; FLAG = [37020, 37021, 37022, 37023]
MOSSY = [36030, 36031, 36032, 36033]; CRACKED = [36040, 36041, 36042, 36043]; TIMBER = [36060, 36061, 36062, 36063]
WILLOW = [38140, 38141, 38142, 38143]; DEAD = [38160, 38161, 38162, 38163]; PINE = [38150, 38151, 38152, 38153]
OLDTREES = [1238, 1240, 1112, 1114, 880, 882]; STUMPS = [38164, 38165, 38166, 38167]
X0, X1, Y0, Y1 = 416, 504, 850, 950
def shore(x): return 924 + int(round(2.5 * math.sin(x / 6.0) + 1.5 * math.sin(x / 2.7)))      # the sea begins here
def sea(x, y): return y >= shore(x)
def beach(x, y): return shore(x) - 5 - int(round(1.5 * math.sin(x / 4.0 + 2))) <= y < shore(x)
ell = lambda x, y, cx, cy, rx, ry, w=0.25: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 + w * math.sin(x * 1.3 + y * 0.9)
CHAPEL = (454, 896, 468, 912)            # the flooded chapel's yard (low wall); the chapel itself inside
NAVE = (457, 899, 465, 910)
LANE = {(x, y) for x in (460, 461) for y in range(884, 897)}          # the sunken lane to it
def flooded(x, y): return (CHAPEL[0] < x < CHAPEL[2] and CHAPEL[1] < y < CHAPEL[3]) or (x, y) in LANE
ISLE = (433, 906, 6.5, 7.5)              # Maud's island
BOG = (434, 905, 15, 17)
HUT = (430, 903, 436, 909)
causeway = {(x, y) for x in range(440, 449) for y in range(893, 896)} | {(x, y) for x in range(438, 442) for y in range(895, 902)}
road = set()
for y in range(846, 884):
    w = int(round(1.3 * math.sin((y - 846) / 5.0)))
    for x in (448, 449, 450): road.add((x + w, y))
for x in range(450, 462):
    for y in (882, 883): road.add((x, y))
HOUSES = [(426, 858, 433, 866), (438, 860, 444, 868), (454, 857, 461, 864), (466, 860, 473, 868), (428, 874, 435, 882),
          (455, 870, 462, 877), (469, 876, 476, 884), (480, 864, 486, 871), (482, 890, 489, 898)]
inbox = lambda b, x, y, pad=0: b[0] - pad <= x <= b[2] + pad and b[1] - pad <= y <= b[3] + pad
pools = []
while len(pools) < 46:
    cx, cy = random.randint(X0 + 5, X1 - 5), random.randint(Y0 + 6, 916)
    if inbox(CHAPEL, cx, cy, 6) or ell(cx, cy, ISLE[0], ISLE[1], 9, 10, 0): continue
    pools.append((cx, cy, random.uniform(1.8, 5.0), random.uniform(1.8, 6.0)))
muds = [(random.randint(X0 + 4, X1 - 4), random.randint(Y0 + 4, 918), random.uniform(1.5, 4), random.uniform(1.5, 4.5)) for _ in range(40)]
def pool(x, y):
    if ell(x, y, *BOG) and not ell(x, y, *ISLE) and (x, y) not in causeway: return True
    return any(ell(x, y, *p) for p in pools)
def mud(x, y): return any(ell(x, y, *p, 0.3) for p in muds) or (x, y) in causeway
wreck = lambda x, y: ((x - 490) / 3.2) ** 2 + ((y - 917) / 7.5) ** 2 <= 1.0

for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        op(op='erase', x=x, y=y); op(op='flag', x=x, y=y, bit=0, mode=0); op(op='flag', x=x, y=y, bit=3, mode=0); op(op='flag', x=x, y=y, bit=5, mode=0)
        if wreck(x, y): op(op='floor', x=x, y=y, s=random.choice(DARKWOOD), set=False); continue
        if sea(x, y): op(op='floor', x=x, y=y, s=random.choice(DEEP), set=False); op(op='flag', x=x, y=y, bit=0, mode=1); continue
        if beach(x, y): op(op='floor', x=x, y=y, s=random.choice(SAND), set=False); continue
        if flooded(x, y):                                                                  # under water: you can walk here, but breath runs out
            op(op='floor', x=x, y=y, s=random.choice(DEEP), set=False); op(op='flag', x=x, y=y, bit=3, mode=1); continue
        if inbox(CHAPEL, x, y): op(op='floor', x=x, y=y, s=random.choice(MARSH), set=False); continue
        if (x, y) in road and random.random() < 0.82: op(op='floor', x=x, y=y, s=random.choice(PATH), set=False); continue
        if ell(x, y, *ISLE) or inbox(HUT, x, y, 1): op(op='floor', x=x, y=y, s=random.choice(MUD if random.random() < 0.25 else MARSH), set=False); continue
        house = next((h for h in HOUSES if inbox(h, x, y)), None)
        if pool(x, y) and (x, y) not in road and not (house and random.random() < 0.55):
            op(op='floor', x=x, y=y, s=random.choice(WATER), set=False); op(op='flag', x=x, y=y, bit=0, mode=1); continue
        if house and random.random() < 0.7: op(op='floor', x=x, y=y, s=random.choice(DARKWOOD), set=False); continue
        op(op='floor', x=x, y=y, s=random.choice(MUD if mud(x, y) else MARSH), set=False)
for x in range(446, 453):                        # open Fenwatch marsh's east tree wall at the road, and thin the rest of it
    for y in range(846, 853): op(op='erase', x=x, y=y)
run('Drowned Village: ground, water, sea')
for x in range(X0, X1 + 1):
    for y in range(848, 853):
        t = W.tile(x, y)
        if t[1] in PINE + WILLOW + OLDTREES and random.random() < 0.7: op(op='erase', x=x, y=y)
for x in range(X0, X1 + 1):
    for y in (849, 850): op(op='flag', x=x, y=y, bit=5, mode=1)       # no-monster strip: the village's monsters stay out of the Fenwatch marsh
run('thin the old tree wall, no-monster strip')

def ruin(box, wall, keep):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if (x in (x0, x1) or y in (y0, y1)) and random.random() < keep and W.tile(x, y)[0] not in WATER:
                op(op='object', x=x, y=y, s=random.choice(wall), block=3)
for k, h in enumerate(HOUSES): ruin(h, MOSSY if k % 3 == 0 else TIMBER, 0.55)
run('ruined houses')
# the flooded chapel: a low wall around the yard (gap where the lane comes in), the nave of cracked stone, door gap on its west end
LOW = 40160                                      # Low Fieldstone Wall: +0 along y, +2 along x, +4 left, +6 right, +8 top, +10 bottom corner
x0, y0, x1, y1 = CHAPEL
for x in range(x0 + 1, x1):
    for y in (y0, y1):
        if not (y == y0 and x in (460, 461)): op(op='object', x=x, y=y, s=LOW + 2, block=1)
for y in range(y0 + 1, y1):
    for x in (x0, x1): op(op='object', x=x, y=y, s=LOW, block=1)
for (x, y), s in {(x0, y0): LOW + 4, (x1, y1): LOW + 6, (x0, y1): LOW + 8, (x1, y0): LOW + 10}.items(): op(op='object', x=x, y=y, s=s, block=1)
x0, y0, x1, y1 = NAVE
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        op(op='flag', x=x, y=y, bit=2, mode=1)
        if (x in (x0, x1) or y in (y0, y1)) and not (y == y0 and x in (460, 461)) and random.random() < 0.93: op(op='object', x=x, y=y, s=random.choice(CRACKED), block=3)
for t, x, y in ((1050, 461, 908), (268, 459, 908), (268, 463, 908), (170, 455, 898), (170, 455, 903), (170, 467, 905), (170, 466, 909)): op(op='place', x=x, y=y, t=t, fresh=1)
run('the flooded chapel')
# Maud's hut on the island
x0, y0, x1, y1 = HUT
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        op(op='floor', x=x, y=y, s=random.choice(DARKWOOD), set=False); op(op='flag', x=x, y=y, bit=2, mode=1)
        if x in (x0, x1) or y in (y0, y1): op(op='object', x=x, y=y, s=random.choice(MOSSY), block=3)
run('hut'); op(op='erase', x=x1, y=906); op(op='place', x=x1, y=906, t=1440, fresh=1)
for t, x, y in ((1148, 439, 904), (741, 432, 905), (299, 432, 907), (2021, 438, 908), (2021, 428, 911), (2021, 437, 900)): op(op='place', x=x, y=y, t=t, fresh=1)
run('hut door, fire, bones')
# the wreck: ribs along both sides, barrels and a broken wagon's worth of cargo on the sand
FEN = 40220
for y in range(911, 924):
    for x in (487, 493):
        if wreck(x + (1 if x == 487 else -1), y) and random.random() < 0.8: op(op="object", x=x, y=y, s=FEN, block=1)
for t, x, y in ((2007, 485, 913), (2007, 484, 915), (2007, 495, 912), (2010, 481, 917), (2021, 489, 909), (2007, 490, 915), (1148, 480, 910)): op(op='place', x=x, y=y, t=t, fresh=1)
run('the wreck')

# soft edges on marsh grass, reeds, trees
def fl(x, y): return W.tile(x, y)[0]
KIND = {}
for s_ in MUD: KIND[s_] = 'marsh mud'
for s_ in WATER: KIND[s_] = 'murky water'
for s_ in PATH: KIND[s_] = 'path'
SIDES = [(1, 0), (0, 1), (-1, 0), (0, -1)]; CORN = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
def mask(x, y, kind):
    m = 0
    for k, (dx, dy) in enumerate(SIDES):
        if KIND.get(fl(x + dx, y + dy)) == kind: m |= 1 << k
    for k, (dx, dy) in enumerate(CORN):
        if KIND.get(fl(x + dx, y + dy)) == kind and not m & (1 << k) and not m & (1 << ((k + 1) % 4)): m |= 16 << k
    return m
MEDGE = {s for e in MT['marsh_base'].values() for s in e.values()}
for x in range(X0, X1 + 1):
    for y in range(846, Y1 + 1):
        f = fl(x, y)
        if f in MARSH or f in MEDGE:
            new = None
            for kind in ('murky water', 'path', 'marsh mud'):
                m = mask(x, y, kind)
                if m: new = MT['marsh_base'][kind][str(m)]; break
            if new is None and f in MEDGE: new = random.choice(MARSH)
            if new is not None and new != f: op(op='floor', x=x, y=y, s=new, set=False)
run('soft edges')
wet = lambda x, y: fl(x, y) in WATER
for x in range(X0 + 1, X1):
    for y in range(Y0 + 1, 922):
        t = W.tile(x, y)
        if t[1] or t[4] or (x, y) in road or flooded(x, y) or inbox(CHAPEL, x, y) or inbox(HUT, x, y, 1) or t[0] in SAND + DARKWOOD + DEEP: continue
        edge = min(x - X0, X1 - x)
        shore_ = any(wet(x + dx, y + dy) != wet(x, y) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        r = random.random()
        if edge <= 2 and not wet(x, y):
            if r < 0.92: op(op='object', x=x, y=y, s=random.choice(PINE + WILLOW + OLDTREES + DEAD), block=3)
        elif shore_ and r < (0.20 if wet(x, y) else 0.45): op(op='object', x=x, y=y, s=random.choice(REEDS), block=0)
        elif wet(x, y): continue
        elif r < 0.035: op(op='object', x=x, y=y, s=random.choice(DEAD), block=1)
        elif r < 0.050: op(op='object', x=x, y=y, s=random.choice(WILLOW), block=3)
        elif r < 0.060: op(op='object', x=x, y=y, s=random.choice(STUMPS), block=1)
        elif r < 0.085: op(op='object', x=x, y=y, s=random.choice(REEDS), block=0)
run('reeds and trees')
print(W.save())
