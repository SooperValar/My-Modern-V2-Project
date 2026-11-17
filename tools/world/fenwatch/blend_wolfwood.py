#!/usr/bin/env python3
"""Fenwatch (Nov 16): soften the straight border between the Wolfwood (forest floor 1118, ends at y 731) and the
Fenwatch marsh (starts at y 732): a wavy border, the marsh's tree wall there thinned to a loose mix of forest trees
and willows, "forest floor creeping into marsh grass" edge tiles (35650-35695), and a no-monster strip (y 732-733)
so the wolves stay in the wood and the marsh's monsters (later) in the marsh.

    blend_wolfwood.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)"""
import sys, os, random, json, math, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1117)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/MyV2/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
MT = json.load(open(os.path.join(HERE, '..', '..', 'sprites', 'world_marsh.json')))
MARSH = [35700, 35701, 35702, 35703]; MUD = [35750, 35751, 35752, 35753]; WATER = [35800, 35801, 35802, 35803]
PATH = [35000, 35001, 35002, 35003]; FOREST = 1118
MEDGE = {s for e in MT['marsh_base'].values() for s in e.values()}
WILLOW = [38140, 38141, 38142, 38143]; DEAD = [38160, 38161, 38162, 38163]; PINE = [38150, 38151, 38152, 38153]
OLDTREES = [1238, 1240, 1112, 1114, 880, 882]
OPS = []
def op(**k): OPS.append(k)
def run(label):
    global OPS
    n, msgs = W.apply(OPS, label)
    for m in msgs: print('  !', m)
    OPS = []
def fl(x, y): return W.tile(x, y)[0]
def b(x): return 731 + max(-5, min(6, int(round(3.0 * math.sin(x / 5.0) + 2.2 * math.sin(x / 2.3 + 1.0)))))    # the new border: forest up to y = b(x)
road = lambda x: 444 <= x <= 454
for x in range(411, 495):
    if road(x): continue
    for y in range(724, 740):
        f = fl(x, y)
        if y <= 731 and y > b(x) and f == FOREST: op(op='floor', x=x, y=y, s=random.choice(MARSH), set=False)
        elif y >= 732 and y <= b(x) and (f in MARSH or f in MEDGE): op(op='floor', x=x, y=y, s=FOREST, set=False)
run('wavy border')
for x in range(406, 495):                      # thin the marsh's tree wall, then a loose mix across the border
    for y in range(732, 735):
        t = W.tile(x, y)
        if not road(x) and t[1] in PINE + WILLOW + OLDTREES and random.random() < 0.7: op(op='erase', x=x, y=y)
run('thin the tree wall')
for x in range(411, 495):
    for y in range(727, 742):
        t = W.tile(x, y)
        if t[1] or t[2] or t[4] or road(x) or t[0] in WATER or t[0] in PATH or t[0] == 989: continue
        if random.random() < 0.09:
            op(op='object', x=x, y=y, s=random.choice(OLDTREES if t[0] == FOREST else WILLOW + OLDTREES + DEAD), block=3)
run('mixed trees')
KIND = {FOREST: 'forest floor', 989: 'path'}
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
todo = []
for x in range(407, 495):
    for y in range(722, 742):
        f = fl(x, y)
        if f in MARSH or f in MEDGE:
            new = None
            for kind in ('murky water', 'path', 'marsh mud', 'forest floor'):
                m = mask(x, y, kind)
                if m: new = MT['marsh_base'][kind][str(m)]; break
            if new is None and f in MEDGE: new = random.choice(MARSH)
            if new is not None and new != f: todo.append((x, y, new))
for x, y, s_ in todo: op(op='floor', x=x, y=y, s=s_, set=False)
for x in range(406, 495):
    for y in (732, 733): op(op='flag', x=x, y=y, bit=5, mode=1)
run('soft edges, no-monster strip')
print(len(todo), 'edge tiles;', W.save())
