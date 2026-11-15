#!/usr/bin/env python3
"""Wagon item templates (Nov 14; sprites 40000-40007 from tools/sprites/world_wagons.py) and a broken wagon by
Tobias at Aston's east gate.     wagons.py <.dat folder>      (game stopped)
A wagon is an item on its FRONT tile (blocks walking, can be looked at); its second tile gets "blocks walking"
(east-west wagons: the tile at y+1; north-south wagons: the tile at x-1)."""
import sys, os, importlib.util, json
DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
KINDS = [(40000, 'Wagon (east-west)', 'A farm wagon loaded with sacks and a crate.'),
         (40002, 'Wagon (north-south)', 'A farm wagon loaded with sacks and a crate.'),
         (40004, 'Broken Wagon (east-west)', 'A wagon with a wheel torn off and its side split. Someone has been through its load.'),
         (40006, 'Broken Wagon (north-south)', 'A wagon with a wheel torn off and its side split. Someone has been through its load.')]
made = {}
for spr, name, desc in KINDS:
    W.apply([{'op': 'itempnew', 'from': 2007, 'name': name}], name); t = W.made[1]
    W.apply([{'op': 'itempset', 't': t, 'fields': {'sprite': [spr, 0], 'description': desc, 'flags': 0x11, 'driver': 0, 'data': [0] * 10}}], name)
    made[name] = t
# Tobias's wagon: east-west, front tile 542,610, second tile 542,611
ops = [{'op': 'erase', 'x': 542, 'y': 610}, {'op': 'erase', 'x': 542, 'y': 611},
       {'op': 'place', 'x': 542, 'y': 610, 't': made['Broken Wagon (east-west)'], 'fresh': 1},
       {'op': 'flag', 'x': 542, 'y': 611, 'bit': 0, 'mode': 1}]
n, msgs = W.apply(ops, "Tobias's wagon")
print(made, msgs); print(W.save())
json.dump(made, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wagons_made.json'), 'w'))
