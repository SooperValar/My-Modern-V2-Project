#!/usr/bin/env python3
"""Snowy grass over Stonehold and its pass (Nov 17; Cody: snowy grass, "towards the top of a mountain"). Every grass
tile becomes snowy grass (tools/sprites/world_snowgrass.py), and the soft edges where snow or a path meets the grass
become the matching edges on snowy grass, so Cody's painted snow and the roads blend into it. Game stopped:

    snowy_stonehold.py <.dat folder> [x0 y0 x1 y1]       (default: the pass and the town, 596-724 / 757-860)"""
import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'sprites')
WGJ = json.load(open(os.path.join(SP, 'world_ground.json'))); SNJ = json.load(open(os.path.join(SP, 'world_snowgrass.json')))
SNOWY = SNJ['grass_base']['snowy grass']['plain']
EDGE = {}                      # grass-base edge sprite -> its edge on snowy grass
for name, e in SNJ['snowy_base'].items():
    for m, s in WGJ['sets'][name]['edges'].items(): EDGE[s] = e[m]
A = Area(sys.argv[1], seed=1132)
X0, Y0, X1, Y1 = [int(v) for v in sys.argv[2:6]] if len(sys.argv) >= 6 else (596, 757, 724, 860)
n = e = 0
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        f = A.floor(x, y)
        if f in GRASS: A.op(op='floor', x=x, y=y, s=random.choice(SNOWY), set=False); n += 1
        elif f in EDGE: A.op(op='floor', x=x, y=y, s=EDGE[f], set=False); e += 1
A.run('snowy grass'); print(n, 'grass tiles -> snowy grass,', e, 'edges'); A.save()
