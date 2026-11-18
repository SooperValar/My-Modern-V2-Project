#!/usr/bin/env python3
"""Fewer archmages in the Hatchery (Cody, Nov 17): three of the five Lizard Archmages in the big cave become Lizard
Knights, on the same spots (2 archmages and 11 knights in the Hatchery now; the Grotto keeps its 3 and its boss).
Run once, game stopped:   fewer_mages.py <.dat folder>       -> made.json updated"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1131); M = json.load(open(os.path.join(HERE, 'made.json')))
KT = ['The eggs are safe.', 'Intruder! Hsss - for the brood, %s!']; KD = 'A lizard knight of the hatcheries in scale armour, guarding the brood.'
for t in (2263, 2264, 2265):
    f = A.tc(t); assert f['name'] == 'Lizard Archmage', (t, f['name']); x, y = f['x'], f['y']
    n, msgs = A.W.apply([{'op': 'npcremove', 'x': x, 'y': y}], 'remove archmage')
    for m in msgs: print('  !', m)
    k = A.monster(406, 'Lizard Knight', 'Captain', x, y, items=[M['items']['head']], text=KT, desc=KD, group=36, pct=M['pct']['knight'])
    M['mages'].remove(t); M['knights'].append(k); print('archmage %d at %d,%d -> knight %d (%s)' % (t, x, y, k, A.rank_of(k)))
A.save(M, HERE)
