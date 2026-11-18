#!/usr/bin/env python3
"""The Golem Foundry (Nov 17; band D, Major), west of Stonehold. Cody's choices: a snowy yard and one great hall, the
Brass Colossus in its own casting pit at the back; anvils and molten iron, nothing modern (tools/sprites/world_foundry.py).

  - the yard (east, by Stonehold's west road): snowy grass and snow, slag heaps (the game's lava rocks), ore, golem wrecks
  - the Foundry Hall: a great slate hall on flagstone, a row of stone furnaces along the north wall feeding a molten-iron
    channel, a branch running to the casting moulds, crucibles, ingots, and the Forgemaster's forge in the south-west
    corner (anvils, grindstone, quench buckets)
  - the Casting Pit (west, behind the hall): a round pit, a ring of molten iron round a stone floor, one bridge in
Everything else in the box is granite cliff, like Stonehold. North = smaller x, west = smaller y.

    build_foundry.py <.dat folder>      (game stopped; tools/world/arealib.py)  -> made_terrain.json"""
import sys, os, random, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.join(HERE, '..', '..', 'sprites')
sys.path.insert(0, SP); import world_ground as wg
FJ = json.load(open(os.path.join(SP, 'world_foundry.json'))); SJ = json.load(open(os.path.join(SP, 'world_snowgrass.json')))
WGJ = json.load(open(os.path.join(SP, 'world_ground.json')))
A = Area(sys.argv[1], seed=1140)
X0, X1, Y0, Y1 = 650, 740, 670, 765
CLIFF, BOULDER = [1204, 1206], 1208
SNOW = [35400, 35401, 35402, 35403]; SNOWY = SJ['grass_base']['snowy grass']['plain']
MOLTEN = FJ['molten']['plain']; O = FJ['objects']
LAVA_STONES = [517, 518, 519]                              # the game's lava rocks: cooled slag
def rough(cx, cy, rx, ry, k=0.10, seed=0):
    rnd = random.Random(seed); ph = rnd.random() * 6
    def inside(x, y):
        a = math.atan2((y - cy) / ry, (x - cx) / rx); f = 1 + k * math.sin(3 * a + ph) + k * 0.6 * math.sin(5 * a + 2 * ph)
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= f * f
    return inside
yard = rough(688, 747, 24, 17, 0.10, 3)
HALL = (663, 695, 707, 731)                               # x0, y0, x1, y1 (walls on the edge)
GATE = [(x, 731) for x in (683, 684, 685)]                 # the hall's great door, east, onto the yard
PIT_C, PIT_R = (685, 682), 8.5                             # the casting pit
pit = lambda x, y: math.hypot(x - PIT_C[0], (y - PIT_C[1]) * 1.0) <= PIT_R or (683 <= x <= 687 and PIT_C[1] < y < 695)   # the round pit + its passage to the hall
PIT_DOOR = [(x, 695) for x in (684, 685, 686)]             # from the hall into the pit (through the hall's west wall)
ring = lambda x, y: 5.2 <= math.hypot(x - PIT_C[0], y - PIT_C[1]) <= 7.0 and not (684 <= x <= 686 and y > PIT_C[1])   # the molten ring, the bridge left
road = set()
for y in range(732, 766):                                 # Stonehold's west road into the yard and to the gate
    xc = 684 + int(round(1.5 * math.sin((y - 732) / 6.0)))
    road |= {(xc + d, y) for d in (-1, 0, 1)}
# the molten iron in the hall: along the furnaces (north), a branch to the casting moulds
FURN_X = 665
chanA = {(x, y) for x in (667, 668) for y in range(698, 729)}
chanB = {(x, y) for x in range(669, 690) for y in (712, 713)}
molten = chanA | chanB | {(x, y) for x in range(X0, X1 + 1) for y in range(Y0, 695) if pit(x, y) and ring(x, y)}
# ---------------------------------------------------------------- ground and cliffs
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        A.clear(x, y); A.op(op='flag', x=x, y=y, bit=2, mode=0); A.op(op='flag', x=x, y=y, bit=5, mode=0)
        inhall = HALL[0] <= x <= HALL[2] and HALL[1] <= y <= HALL[3]
        if (x, y) in road and not inhall: A.op(op='floor', x=x, y=y, s=random.choice(PATH), set=False); continue
        if yard(x, y) and not inhall: A.op(op='floor', x=x, y=y, s=random.choice(SNOW if random.random() < 0.12 else GRASS), set=False); continue
        if inhall or (pit(x, y) and y < HALL[1]): A.op(op='floor', x=x, y=y, s=random.choice(FLAGSTONE), set=False); A.op(op='flag', x=x, y=y, bit=2, mode=1); continue
        A.op(op='floor', x=x, y=y, s=random.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=random.choice(CLIFF), block=3)
A.run('foundry: ground and cliffs')
A.house(HALL, W_SLATE, FLAGSTONE)                          # the hall's walls (no door: the gate is an open arch)
for x, y in GATE + PIT_DOOR: A.op(op='erase', x=x, y=y); A.op(op='floor', x=x, y=y, s=random.choice(FLAGSTONE), set=False)
for x in range(X0, X1 + 1):                                # the pit: a wall round it where it meets the cliff (slate, like the hall)
    for y in range(Y0, HALL[1]):
        inh = lambda a, b: HALL[0] <= a <= HALL[2] and HALL[1] <= b <= HALL[3]
        if pit(x, y) and not all(pit(x + dx, y + dy) or inh(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            A.op(op='object', x=x, y=y, s=random.choice(W_SLATE), block=3)
A.run('gate and pit walls')
for x, y in molten:
    A.op(op='floor', x=x, y=y, s=random.choice(MOLTEN), set=False); A.op(op='flag', x=x, y=y, bit=0, mode=1)
A.run('molten iron')
# soft edges: molten iron creeping into the flagstone round it
edges = FJ['molten']['edges']; fl = set(FJ['floor'])
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if A.floor(x, y) not in fl: continue
        m = wg.mask_of(lambda dx, dy: (x + dx, y + dy) in molten)
        if m and str(m) in edges: A.op(op='floor', x=x, y=y, s=edges[str(m)], set=False)
A.run('molten edges')
# ---------------------------------------------------------------- the pieces
def obj(name, x, y, block=1): A.op(op='object', x=x, y=y, s=O[name], block=block)
furn = [(FURN_X, y) for y in range(699, 729, 4)]
for x, y in furn: obj('stone furnace', x, y, 3)
for y in (701, 709, 717, 725): obj('crucible', 669, y)                           # crucibles by the channel
for y in (705, 721): obj('iron ingots', 670, y)
for x, y in [(691, 710), (691, 712), (691, 714), (692, 711), (692, 713)]: obj('casting mould', x, y)   # moulds at the branch's end
for x, y in [(694, 709), (694, 715), (689, 716)]: obj('iron ingots', x, y)
# the Forgemaster's forge (south-west corner of the hall)
FORGE = (699, 697, 706, 706)
for x, y, n in [(700, 699, 'anvil on a log'), (703, 699, 'anvil on a block'), (700, 702, 'anvil on a block'), (705, 698, 'grindstone'),
                (701, 698, 'quench bucket'), (704, 701, 'quench bucket'), (706, 703, 'iron ingots'), (706, 705, 'iron ingots'), (698, 698, 'stone furnace')]:
    obj(n, x, y, 3 if n == 'stone furnace' else 1)
for x, y, n in [(677, 724, 'anvil on a log'), (680, 724, 'anvil on a log'), (677, 727, 'quench bucket'), (690, 726, 'grindstone'), (673, 718, 'toppled golem'),
                (683, 702, 'anvil on a block'), (686, 702, 'anvil on a log'), (683, 699, 'quench bucket'), (688, 699, 'iron ingots'), (680, 699, 'crucible'),
                (672, 722, 'casting mould'), (673, 726, 'casting mould'), (675, 722, 'iron ingots')]:
    obj(n, x, y)
# the golem works (south-east of the hall): unfinished and broken golems laid out in a row, limbs and plates beside them
for k, x in enumerate(range(694, 705, 3)):
    obj('toppled golem' if k % 2 == 0 else 'golem limbs', x, 726); obj('golem limbs' if k % 2 == 0 else 'iron ingots', x, 729)
for x, y in [(697, 718), (701, 718), (704, 721)]: A.op(op='place', x=x, y=y, t=random.choice(LAVA_STONES), fresh=1)   # slag inside too
A.run('foundry pieces')
# the yard: slag heaps, ore, wrecks, a few snowy pines and boulders
yt = [(x, y) for x in range(X0, X1 + 1) for y in range(732, Y1 + 1) if yard(x, y) and (x, y) not in road and not any((x + dx, y + dy) in road for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
random.shuffle(yt); k = 0; used = set()
def far(p): return all(abs(p[0] - a) + abs(p[1] - b) >= 3 for a, b in used)
for kind, n in (('slag', 14), ('toppled golem', 4), ('golem limbs', 6), ('rock', 6), ('pine', 6), ('boulder', 4)):
    c = 0
    for p in yt:
        if c >= n: break
        if p in used or not far(p): continue
        used.add(p); c += 1
        if kind == 'slag': A.op(op='place', x=p[0], y=p[1], t=random.choice(LAVA_STONES), fresh=1)
        elif kind == 'rock': A.op(op='object', x=p[0], y=p[1], s=random.choice(ROCKS), block=3)
        elif kind == 'pine': A.op(op='object', x=p[0], y=p[1], s=random.choice([38154, 38155, 38156, 38157]), block=3)
        elif kind == 'boulder': A.op(op='object', x=p[0], y=p[1], s=BOULDER, block=3)
        else: obj(kind, *p)
A.run('the yard')
# light: fire bowls along the hall walls, by the gate and in the pit; torches at the gate outside
L = [(FIREBOWL, x, y) for x, y in [(664, 697), (664, 729), (706, 697), (706, 729), (680, 730), (688, 730), (672, 696), (696, 696), (690, 706), (690, 720), (675, 710), (675, 716)]]
L += [(FIREBOWL, x, y) for x, y in [(679, 677), (691, 677), (679, 688), (691, 688)]]
L += [(TORCH, 682, 733), (TORCH, 686, 733)]
A.place(*L)
# snowy grass in the yard: soft edges, then everything grass -> snowy grass (as snowy_stonehold.py)
A.ground_edges((X0, 732, X1, Y1), kinds=['soft snow', 'path'])
EDGE = {}
for name, e in SJ['snowy_base'].items():
    for m, s in WGJ['sets'][name]['edges'].items(): EDGE[s] = e[m]
for x in range(X0, X1 + 1):
    for y in range(732, Y1 + 1):
        f = A.floor(x, y)
        if f in GRASS: A.op(op='floor', x=x, y=y, s=random.choice(SNOWY), set=False)
        elif f in EDGE: A.op(op='floor', x=x, y=y, s=EDGE[f], set=False)
A.run('snowy yard')
A.zone(X0, Y0, X1, Y1, 'Golem Foundry', flag=1)
A.zone(HALL[0], HALL[1], HALL[2], HALL[3], 'Foundry Hall', flag=1)
A.zone(int(PIT_C[0] - PIT_R), int(PIT_C[1] - PIT_R), int(PIT_C[0] + PIT_R), HALL[1] - 1, 'Casting Pit', flag=1)
A.zone(FORGE[0], FORGE[1], FORGE[2], FORGE[3], "Forgemaster's Forge", flag=0)
json.dump({'hall': HALL, 'gate': GATE, 'pit_centre': PIT_C, 'forge': FORGE, 'molten': sorted(molten)}, open(os.path.join(HERE, 'made_terrain.json'), 'w'))
A.save()
