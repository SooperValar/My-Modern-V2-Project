#!/usr/bin/env python3
"""Dire wolves only beyond the border (y >= 822), grey wolves before it (y <= 806); also moves each one's home.
    move_wolves.py <.dat folder>"""
import sys, os, random, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]; random.seed(7)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
where = {}
for x in range(540, 662):
    for y in range(768, 856):
        c = W.tile(x, y)[2]
        if c: where[c] = (x, y)
for p in W.pending(): where[('p', p[2])] = (p[0], p[1])
def pos(t):
    for c in W.living(t):
        if c in where: return where[c]
    return where.get(('p', t))
def free(x, y): return W.tile(x, y)[1] == 0 and not W.tile(x, y)[4] and not W.tile(x, y)[2]
for group, lo, hi, bad in ((M['dires'], 824, 846, lambda y: y < 822), (M['greys'], 778, 804, lambda y: y > 806)):
    for t in group:
        p = pos(t)
        if not p: print('  ?', t, 'not found'); continue
        if not bad(p[1]): continue
        while True:
            tx, ty = random.randint(550, 650), random.randint(lo, hi)
            if free(tx, ty): break
        print('  ', t, p, '->', (tx, ty), W.apply([{'op': 'npcmove', 'x': p[0], 'y': p[1], 'tx': tx, 'ty': ty}], 'wolf')[1])
print(W.save())
