#!/usr/bin/env python3
"""No wolf on the road through the Eastern Forest (Cody, Nov 15): the road is its dirt (floor 989); every Grey Wolf
standing within 3 tiles of it moves (with its home) to a free spot further away.    off_road.py <.dat folder>"""
import sys, os, random, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]; random.seed(11)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
F = [a[:4] for a in W.areas if a[4] == 'Eastern Forest']
road = {(x, y) for x0, y0, x1, y1 in F for x in range(x0 - 3, x1 + 4) for y in range(y0 - 3, y1 + 4) if W.tile(x, y)[0] == 989}
def near_road(x, y, r=3): return any((x + dx, y + dy) in road for dx in range(-r, r + 1) for dy in range(-r, r + 1))
def free(x, y):
    t = W.tile(x, y); return t[1] == 0 and not t[4] and not t[2] and not (t[7] & 1) and not (t[7] & 32) and t[0] not in (0, 1008)
P = {p[2]: (p[0], p[1]) for p in W.pending()}
where = {}
for x0, y0, x1, y1 in F:
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if W.tile(x, y)[2]: where[W.tile(x, y)[2]] = (x, y)
def pos(t): return P.get(t) or next((where[c] for c in W.living(t) if c in where), None)
homes = [pos(t) for t in M['greys']]
cells = [(x, y) for x0, y0, x1, y1 in F for x in range(x0 + 1, x1) for y in range(y0 + 1, y1) if free(x, y) and not near_road(x, y)]
random.shuffle(cells)
for t, p in zip(M['greys'], homes):
    if not p or not near_road(*p): continue
    to = next(c for c in cells if all(abs(c[0] - a) + abs(c[1] - b) >= 7 for a, b in [h for h in homes if h]))
    cells.remove(to)
    print('  ', t, p, '->', to, W.apply([{'op': 'npcmove', 'x': p[0], 'y': p[1], 'tx': to[0], 'ty': to[1]}], 'wolf off the road')[1])
    homes[homes.index(p)] = to
print(W.save())
