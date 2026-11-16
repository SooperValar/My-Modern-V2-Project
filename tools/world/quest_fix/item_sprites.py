#!/usr/bin/env python3
"""Nov 16: the quest items get their own pictures (sprites 44510-44521, tools/sprites/quest_items/README.txt):
the item templates' sprite, and every copy of them (on the map, carried by NPCs or players) that still has the old one.
    item_sprites.py <.dat folder>      (the game stopped: stop-send; then update-world, reload-editor)"""
import sys, os, struct, importlib.util
DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
NEW = {2002: 44510, 2006: 44511, 2015: 44512, 2012: 44513, 2013: 44514, 2003: 44516, 2004: 44517, 2005: 44518,
       2014: 44519, 2018: 44520, 2019: 44521}
for t, s in NEW.items():
    it = W.itemp(t); old = it['sprite']
    W.apply([{'op': 'itempset', 't': t, 'fields': {'sprite': [s, old[1]]}}], 'item')
    n = 0
    for i in range(1, me.MAXITEM):
        o = i * me.ITEM_SIZE
        if W.item[o + me.I_USED] == me.USE_ACTIVE and W.it_u16(i, me.I_TEMP) == t:
            if struct.unpack_from('<H', W.item, o + 537)[0] == old[0]:
                struct.pack_into('<H', W.item, o + 537, s); n += 1
    print(t, it['name'], old[0], '->', s, 'copies', n)
print(W.save())
