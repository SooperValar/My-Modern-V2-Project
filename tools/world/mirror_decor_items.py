#!/usr/bin/env python3
"""Item templates for the west-wall decorations (tools/sprites/mirror_decor.py, sprites 48000-48014): for each game
template that shows one of the mirrored pictures (Mirror, Shield-less: pictures, mirrors, bookshelves, skeletons in
chains), a copy named "<name> (west wall)" with the mirrored look (both looks, e.g. a bookshelf whose book can be
taken). One copy per distinct name + look, plain decorations only (driver 0), so the editor's Items palette has them.
    mirror_decor_items.py <.dat folder>      (the game stopped: stop-send; then update-world, reload-editor)
Not run yet (Nov 16): another session was building the world; run it when that is done."""
import sys, os, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, '..', 'sprites', 'mirror_decor.json')))
west = {v['from']: int(k) for k, v in M.items()}
done, made = set(), []
for t in range(1, me.MAXTITEM):
    it = W.itemp(t)
    if not it or it['driver'] != 0 or it['sprite'][0] not in west or (it['flags'] >> 2) & 1:
        continue
    key = (it['name'], it['sprite'][0])
    if key in done or it['name'].endswith('(west wall)'):
        continue
    done.add(key)
    W.apply([{'op': 'itempnew', 'from': t, 'name': it['name'] + ' (west wall)'}], 'west wall')
    n = W.made[1]
    s1 = it['sprite'][1]
    W.apply([{'op': 'itempset', 't': n, 'fields': {'sprite': [west[it['sprite'][0]], west.get(s1, s1) if s1 else 0]}, 'update_map': False}], 'west look')
    made.append((t, n, it['name']))
for t, n, name in made: print(t, '->', n, name, '(west wall)')
print(W.save())
