#!/usr/bin/env python3
"""Snowy pines in Stonehold and its pass (Cody, Nov 17): each green pine (38150-38153) becomes the snowy pine of the same
shape (38154-38157), on the same tile. Game stopped:   snowy_pines.py <.dat folder> [x0 y0 x1 y1]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1])
X0, Y0, X1, Y1 = [int(v) for v in sys.argv[2:6]] if len(sys.argv) >= 6 else (596, 757, 724, 860)
n = 0
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        t = A.tile(x, y)
        if 38150 <= t[1] <= 38153:
            A.op(op='object', x=x, y=y, s=t[1] + 4, block=t[7] & 3); n += 1
A.run('snowy pines'); print(n, 'pines -> snowy pines'); A.save()
