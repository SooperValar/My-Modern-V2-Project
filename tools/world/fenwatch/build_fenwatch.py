#!/usr/bin/env python3
"""Fenwatch (Nov 16): the marsh town east of the Wolfwood, hub of band C (Sergeant Major to Captain), and the Fen
Road to it from the Wolfwood road's east end (449,728).

    build_fenwatch.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)

This part makes the ground, the palisade, streets, buildings, the pond and the lights. NPCs, merchants and quests
come from place_fenwatch.py once the layout is settled. Map: x grows down-right (south), y up-right (east)."""
import sys, os, random, json, math, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
DAT = sys.argv[1]
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1116)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/MyV2/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
OPS = []
def op(**k): OPS.append(k)
def run(label):
    global OPS
    n, msgs = W.apply(OPS, label)
    for m in msgs: print('  !', m)
    OPS = []

GRASS = [551, 552, 553, 554]; PATH = [35000, 35001, 35002, 35003]
MARSH = [35700, 35701, 35702, 35703]; MUD = [35750, 35751, 35752, 35753]; WATER = [35800, 35801, 35802, 35803]   # tools/sprites/world_marsh.py
MT = json.load(open(os.path.join(HERE, '..', '..', 'sprites', 'world_marsh.json'))); REEDS = MT['reeds']
OAK = [37000, 37001, 37002, 37003]; DARKWOOD = [37010, 37011, 37012, 37013]; FLAG = [37020, 37021, 37022, 37023]
SETTS = [37060, 37061, 37062, 37063]
TIMBER = [36060, 36061, 36062, 36063]; STONE = [36070, 36071, 36072, 36073]; MOSSY = [36030, 36031, 36032, 36033]
WILLOW = [38140, 38141, 38142, 38143]; DEAD = [38160, 38161, 38162, 38163]; PINE = [38150, 38151, 38152, 38153]
OLDTREES = [1238, 1240, 1112, 1114, 880, 882]; STUMPS = [38164, 38165, 38166, 38167]
PAL = 40180                                   # Log Palisade: +0 along y, +2 along x, +4 left, +6 right, +8 top, +10 bottom corner
MX0, MX1, MY0, MY1 = 406, 494, 732, 852       # the marsh around the town
X0, X1, Y0, Y1 = 424, 476, 770, 834           # the palisade
RX, RY = (448, 449, 450), (800, 801, 802)     # the two streets (west-east along y, north-south along x)

street = set()
for y in range(726, MY1 - 3):                   # the Fen Road, the main street and its stub to the east
    w = 0 if Y0 <= y <= Y1 else int(round(1.2 * math.sin((y - 726) / 6.0)))
    for x in RX: street.add((x + w, y))
for x in range(MX0 + 4, MX1 - 3):
    w = 0 if X0 <= x <= X1 else int(round(1.2 * math.sin((x - X0) / 6.0)))
    for y in RY: street.add((x, y + w))
square = {(x, y) for x in range(443, 456) for y in range(794, 809)}
# buildings: box, wall, floor, door side, door spot
B = {
 'inn':     ((429, 774, 441, 787), TIMBER, OAK,      's', (441, 781)),
 'bounty':  ((432, 790, 440, 797), TIMBER, DARKWOOD, 'e', (436, 797)),
 'chapel':  ((428, 806, 440, 817), STONE,  FLAG,     'w', (434, 806)),
 'hall':    ((428, 821, 439, 831), STONE,  OAK,      's', (439, 826)),
 'store':   ((454, 775, 462, 783), TIMBER, OAK,      'n', (454, 779)),
 'smith':   ((454, 787, 462, 795), TIMBER, FLAG,     'n', (454, 791)),
 'rook':    ((466, 774, 473, 781), MOSSY,  DARKWOOD, 'e', (469, 781)),
 'house':   ((466, 788, 473, 796), TIMBER, OAK,      'w', (469, 788)),
 'joss':    ((454, 806, 460, 812), TIMBER, OAK,      'e', (457, 812)),
}
lanes = set()
def lane(x0, y0, x1, y1):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1): lanes.add((x, y))
lane(442, 781, 447, 781); lane(436, 798, 436, 799); lane(434, 803, 434, 805); lane(440, 826, 447, 826)
lane(451, 779, 453, 779); lane(451, 791, 453, 791); lane(451, 785, 469, 785); lane(469, 782, 469, 787)
lane(451, 814, 457, 814); lane(457, 813, 457, 822)
def pond(x, y): return ((x - 467) / 6.2) ** 2 + ((y - 823) / 8.2) ** 2 <= 1.0
jetty = {(x, y) for x in range(458, 468) for y in (822, 823)}
inbox = lambda b, x, y, pad=0: b[0] - pad <= x <= b[2] + pad and b[1] - pad <= y <= b[3] + pad
def built(x, y, pad=1): return any(inbox(b[0], x, y, pad) for b in B.values())

# pools in the marsh outside the walls
pools = []
while len(pools) < 26:
    cx, cy = random.randint(MX0 + 6, MX1 - 6), random.randint(MY0 + 6, MY1 - 6)
    rx, ry = random.uniform(1.6, 4.5), random.uniform(1.6, 5.5)
    if inbox((X0, Y0, X1, Y1), cx, cy, 8): continue
    if any((cx + dx, cy + dy) in street for dx in range(-7, 8) for dy in range(-7, 8)): continue
    pools.append((cx, cy, rx, ry))
muds = []
while len(muds) < 34:
    cx, cy = random.randint(MX0 + 4, MX1 - 4), random.randint(MY0 + 4, MY1 - 4)
    intown = inbox((X0, Y0, X1, Y1), cx, cy, -3)
    if inbox((X0, Y0, X1, Y1), cx, cy, 2) and not intown: continue
    if intown and built(cx, cy, 3): continue
    muds.append((cx, cy, random.uniform(1.2, 2.4) if intown else random.uniform(1.5, 4.0), random.uniform(1.2, 2.6) if intown else random.uniform(1.5, 4.5)))
def mud(x, y):
    return any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 + 0.3 * math.sin(x * 1.7 + y * 1.1) for cx, cy, rx, ry in muds)
LAWNS = []      # (bright lawns in town were tried and dropped: too loud beside the marsh grass)
def lawn(x, y):
    return inbox((X0, Y0, X1, Y1), x, y, -1) and any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 + 0.3 * math.sin(x * 1.1 + y * 1.9) for cx, cy, rx, ry in LAWNS)
def pool(x, y):
    return any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 + 0.25 * math.sin(x * 1.3 + y * 0.7) for cx, cy, rx, ry in pools)

for x in range(MX0, MX1 + 1):
    for y in range(MY0, MY1 + 1):
        town = inbox((X0, Y0, X1, Y1), x, y)
        op(op='erase', x=x, y=y); op(op='flag', x=x, y=y, bit=0, mode=0)
        wet = (pond(x, y) and (x, y) not in jetty) if town else pool(x, y)
        if wet:
            op(op='floor', x=x, y=y, s=random.choice(WATER), set=False); op(op='flag', x=x, y=y, bit=0, mode=1); continue
        if (x, y) in jetty: op(op='floor', x=x, y=y, s=random.choice(OAK), set=False); continue
        if (x, y) in square and town: op(op='floor', x=x, y=y, s=random.choice(SETTS), set=False); continue
        if (x, y) in street or ((x, y) in lanes and town): op(op='floor', x=x, y=y, s=random.choice(PATH), set=False); continue
        op(op='floor', x=x, y=y, s=random.choice(MUD if mud(x, y) and not built(x, y, 0) else GRASS if lawn(x, y) else MARSH), set=False)
        if town:
            if x in (X0, X1) or y in (Y0, Y1) or built(x, y, 2) or mud(x, y): continue
            if any((x + dx, y + dy) in street or (x + dx, y + dy) in lanes or (x + dx, y + dy) in square for dx in (-1, 0, 1) for dy in (-1, 0, 1)): continue
            r = random.random()
            if r < 0.030: op(op='object', x=x, y=y, s=random.choice(WILLOW), block=3)
            elif r < 0.042: op(op='object', x=x, y=y, s=random.choice(STUMPS), block=1)
            continue
        if inbox((X0, Y0, X1, Y1), x, y, 2): continue
        d = min(x - MX0, MX1 - x, MY1 - y, (y - MY0) if not (440 <= x <= 458) else 99)
        near_road = any((x + dx, y + dy) in street for dx in range(-2, 3) for dy in range(-2, 3))
        if near_road: continue
        r = random.random()
        if d <= 2:
            if r < 0.92: op(op='object', x=x, y=y, s=random.choice(PINE + WILLOW + OLDTREES), block=3)
        elif r < 0.035: op(op='object', x=x, y=y, s=random.choice(WILLOW), block=3)
        elif r < 0.060: op(op='object', x=x, y=y, s=random.choice(DEAD), block=1)
        elif r < 0.070: op(op='object', x=x, y=y, s=random.choice(STUMPS), block=1)
        elif r < 0.080: op(op='object', x=x, y=y, s=random.choice(OLDTREES), block=3)
run('Fenwatch: marsh, pools, streets')
for x in range(446, 453):                      # join the Wolfwood road: clear its last trees
    for y in range(726, 733):
        if (x, y) in street or True:
            pass
for (x, y) in [p for p in street if p[1] < MY0]:
    op(op='erase', x=x, y=y); op(op='floor', x=x, y=y, s=989, set=False)
run('Fen Road joins the Wolfwood road')

# soft edges (the editor only knows grass-based edges of its own grounds): marsh grass with water / path / mud
# creeping in, and grass with marsh grounds creeping in, placed here from world_marsh.json
import struct
def fl(x, y): return W.tile(x, y)[0]
KIND = {}
for s_ in MARSH: KIND[s_] = 'marsh grass'
for s_ in MUD: KIND[s_] = 'marsh mud'
for s_ in WATER: KIND[s_] = 'murky water'
for s_ in PATH + [989] + SETTS: KIND[s_] = 'path'
SIDES = [(1, 0), (0, 1), (-1, 0), (0, -1)]; CORN = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
def mask(x, y, kind):
    m = 0
    for k, (dx, dy) in enumerate(SIDES):
        if KIND.get(fl(x + dx, y + dy)) == kind: m |= 1 << k
    for k, (dx, dy) in enumerate(CORN):
        if KIND.get(fl(x + dx, y + dy)) == kind and not m & (1 << k) and not m & (1 << ((k + 1) % 4)): m |= 16 << k
    return m
edges = []
for x in range(MX0, MX1 + 1):
    for y in range(MY0, MY1 + 1):
        f = fl(x, y)
        if f in MARSH:
            for kind in ('murky water', 'path', 'marsh mud'):
                m = mask(x, y, kind)
                if m: edges.append((x, y, MT['marsh_base'][kind][str(m)])); break
        elif f in GRASS:
            for kind in ('murky water', 'marsh grass', 'marsh mud'):
                m = mask(x, y, kind)
                if m: edges.append((x, y, MT['grass_base'][kind]['edges'][str(m)])); break
wet = lambda x, y: fl(x, y) in WATER
for x, y, s_ in edges: op(op='floor', x=x, y=y, s=s_, set=False)
for x in range(MX0 + 1, MX1):                    # reeds along the water
    for y in range(MY0 + 1, MY1):
        t = W.tile(x, y)
        if t[1] or t[4] or (x, y) in street or (x, y) in lanes or (x, y) in jetty or built(x, y, 1): continue
        shore = any(wet(x + dx, y + dy) != wet(x, y) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        near = any(wet(x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3))
        r = random.random()
        if (shore and r < (0.22 if wet(x, y) else 0.50)) or (near and not wet(x, y) and r < 0.15) or (not near and not inbox((X0, Y0, X1, Y1), x, y) and r < 0.012):
            op(op='object', x=x, y=y, s=random.choice(REEDS), block=0)
run('soft marsh edges, reeds')

# the palisade and its four gates
gates = {(x, Y0) for x in RX} | {(x, Y1) for x in RX} | {(X0, y) for y in RY} | {(X1, y) for y in RY}
for x in range(X0 + 1, X1):
    for y in (Y0, Y1):
        if (x, y) not in gates: op(op='object', x=x, y=y, s=PAL + 2, block=3)
for y in range(Y0 + 1, Y1):
    for x in (X0, X1):
        if (x, y) not in gates: op(op='object', x=x, y=y, s=PAL, block=3)
for (x, y), s in {(X0, Y0): PAL + 4, (X1, Y1): PAL + 6, (X0, Y1): PAL + 8, (X1, Y0): PAL + 10}.items():
    op(op='object', x=x, y=y, s=s, block=3)
run('palisade')

def walls(box, wall, floor, side, door):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            op(op='erase', x=x, y=y); op(op='floor', x=x, y=y, s=random.choice(floor), set=False); op(op='flag', x=x, y=y, bit=2, mode=1)
            if x in (x0, x1) or y in (y0, y1): op(op='object', x=x, y=y, s=random.choice(wall), block=3)
    run('walls')
    op(op='erase', x=door[0], y=door[1]); op(op='place', x=door[0], y=door[1], t=1440 if side in ('n', 's') else 1441, fresh=1)
    run('door')
for name, b in B.items(): walls(*b)
x0, y0, x1, y1 = B['inn'][0]
for x in range(x0 + 1, x1):
    for y in range(y0 + 1, y1): op(op='flag', x=x, y=y, bit=7, mode=1)        # tavern: players can log out here
for x in range(X0 - 2, X1 + 3):
    for y in range(Y0 - 2, Y1 + 3): op(op='flag', x=x, y=y, bit=5, mode=1)    # no monsters in town
run('tavern, no monsters')

PLACE = [(764, 447, 768), (764, 451, 768), (764, 447, 836), (764, 451, 836), (764, 422, 799), (764, 422, 803), (764, 478, 799), (764, 478, 803),
         (764, 443, 794), (764, 455, 794), (764, 443, 808), (764, 455, 808), (764, 457, 821),
         (82, 432, 776), (82, 432, 780), (83, 437, 777), (83, 437, 784), (82, 432, 784), (741, 435, 781),          # inn
         (82, 435, 792), (1350, 433, 795),                                                                          # bounty office
         (268, 430, 808), (268, 430, 815), (1050, 431, 811), (1055, 438, 808), (1055, 438, 815),                    # chapel
         (298, 433, 826), (1350, 429, 823), (1351, 429, 825), (1352, 429, 827), (741, 436, 829),                    # reeve's hall
         (82, 458, 777), (83, 458, 781), (298, 458, 789), (741, 460, 793),                                          # store, smith
         (1352, 467, 776), (1353, 467, 778), (299, 470, 777), (1130, 471, 779),                                     # Rook
         (82, 469, 792), (82, 457, 808),                                                                            # house, Joss
         (2007, 453, 776), (2007, 453, 777), (2007, 463, 790), (2007, 453, 793), (2007, 456, 813), (2007, 442, 778),
         (2008, 445, 774)]
for t, x, y in PLACE: op(op='place', x=x, y=y, t=t, fresh=1)
for x in range(463, 466):                      # Rook's herb plot
    for y in range(775, 781):
        if random.random() < 0.6: op(op='place', x=x, y=y, t=random.choice([16, 45, 137, 138, 139]), fresh=1)
for y in range(807, 817, 2): op(op='place', x=426, y=y, t=170, fresh=1)      # the chapel's graves
for t, x, y in ((82, 445, 796), (83, 445, 806), (2007, 444, 797), (2007, 444, 805), (2007, 453, 796)): op(op='place', x=x, y=y, t=t, fresh=1)   # market tables
op(op='flag', x=445, y=775, bit=0, mode=1)
run('lights and furniture')
print(W.save())
