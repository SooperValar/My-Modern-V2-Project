#!/usr/bin/env python3
"""Clear the trees around Tobias's wagon (x 539-546, y 607-614) so it can be seen.   wagon_clearing.py <.dat>"""
import sys, os, struct, importlib.util
DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.path.expanduser('~/mnt/Server/mapedit.py'))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
TREES = {320, 356, 358, 360, 362, 880, 882, 884, 1112, 1114, 1116, 1238, 1240}
ops = []
for x in range(539, 547):
    for y in range(607, 615):
        t = W.tile(x, y)
        if t[1] in TREES: ops.append({'op': 'object', 'x': x, 'y': y, 's': 0, 'block': 0})
print(len(ops), 'trees'); print(W.apply(ops, 'clearing')); print(W.save())
