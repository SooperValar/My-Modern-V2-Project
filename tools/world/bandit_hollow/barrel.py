#!/usr/bin/env python3
"""A plain decorative Barrel (Nov 14): item template copied from "barrel (portal)" (1100) without its portal driver
(blocks walking, can be looked at). The 7 barrels of Bandit Hollow (drawn into their tiles) become this item.
    barrel.py <.dat folder>      (game stopped)"""
import sys, os, importlib.util
DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
W.apply([{'op': 'itempnew', 'from': 1100, 'name': 'Barrel'}], 'barrel'); B = W.made[1]
W.apply([{'op': 'itempset', 't': B, 'fields': {'driver': 0, 'data': [0] * 10, 'flags': 0x11, 'reference': 'barrel',
                                              'description': 'A sturdy wooden barrel.'}}], 'barrel')
spots = [(525, 701), (525, 702), (524, 708), (546, 708), (515, 711), (516, 719), (553, 726)]
ops = []
for x, y in spots:
    ops += [{'op': 'erase', 'x': x, 'y': y}, {'op': 'place', 'x': x, 'y': y, 't': B, 'fresh': 1}]
n, msgs = W.apply(ops, 'Bandit Hollow barrels as items')
print('Barrel template', B, msgs); print(W.save())
