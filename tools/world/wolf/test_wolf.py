#!/usr/bin/env python3
"""Nov 15: the first 3D-rendered monster, a test Grey Wolf (sprites 43000-43447, tools/sprites/make_creature.py),
copied from the Spider (392, same strength), placed in the field by the east road.    test_wolf.py <.dat folder>
The wolf has the full animation set, so it is not "simple" (CF_SIMPLE, inherited from the spider, blocks pick up / drop / give / use)."""
import sys, os, json, importlib.util
DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
W.apply([{'op': 'ctempnew', 'from': 392, 'name': 'Grey Wolf'}], 'wolf'); t = W.made[1]
dd = list(me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['data'])
for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
flags = me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['flags'] & ~(1 << 27)
W.apply([{'op': 'ctempset', 't': t, 'fields': {'flags': flags, 'sprite': 43000, 'data': dd, 'description': 'A grey wolf, lean and hungry. Its yellow eyes never leave you.'},
          'text': [], 'respawn': False}], 'wolf')
free = lambda x, y: W.tile(x, y)[1] == 0 and not W.tile(x, y)[4]
spot = next((x, y) for x, y in [(536 + dx, 628 + dy) for dx in range(-4, 5) for dy in range(-4, 5)] if free(x, y))
n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': spot[0], 'y': spot[1], 'dir': 4}], 'place wolf')
print('template', t, 'at', spot, msgs)
json.dump({'wolf': t, 'at': spot}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'made.json'), 'w'))
print(W.save())
