#!/usr/bin/env python3
"""Item templates for the four-wall decorations (tools/sprites/wall_decor.py, sprites 48000-48025), plus two fixes:
- the framed Mirror (sprite 1246) hangs like the pictures (48000) - its template and every copy; the ones whose wall is
  to their north get the back (48006);
- one template per new look, "<name>, wall W" / "..., back, wall N" ..., copied from the game's template of the same
  thing (made plain: driver 0), so they are in the editor's Items palette.
Shrines (48020-48025) get no templates: a shrine works by its own data (which shrine it is), so change the Look of the
placed shrine instead.
    wall_decor_items.py <.dat folder>      (the game stopped: stop-send; then update-world, reload-editor)
Not run yet (Nov 16): another session was building the world."""
import sys, os, json, struct, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
J = {int(k): v for k, v in json.load(open(os.path.join(HERE, '..', 'sprites', 'wall_decor.json'))).items()}
def base_for(sprite):
    best = None
    for t in range(1, me.MAXTITEM):
        it = W.itemp(t)
        if it and it['sprite'][0] == sprite and not (it['flags'] >> 2) & 1:
            if it['driver'] == 0: return t
            best = best or t
    return best
# 1. the framed Mirror: hung like the pictures
MIRROR = base_for(1246)
if MIRROR:
    W.apply([{'op': 'itempset', 't': MIRROR, 'fields': {'sprite': [48000, 0]}, 'copies': 'all'}], 'Mirror hung up')
    for i in range(1, me.MAXITEM):
        o = i * me.ITEM_SIZE
        if W.item[o + me.I_USED] == me.USE_ACTIVE and W.it_u16(i, me.I_TEMP) == MIRROR and not W.it_u16(i, me.I_CARRIED):
            x, y = W.it_u16(i, me.I_X), W.it_u16(i, me.I_Y); n = W.tile(x, y - 1)
            if n[1] and n[7] & 1:                 # its wall is to the north: the back
                W._save_item(W.undo[-1] if W.undo else {}, i); struct.pack_into('<H', W.item, o + 537, 48006)
                print('  mirror at', x, y, 'gets its back')
# 2. the new looks
made = []
for n, v in sorted(J.items()):
    if n == 48000 or n == 48017 or 48020 <= n <= 48025: continue
    src = 16897 if v['from'] in (16910, 16908) else v['from']       # bookshelves: from the plain Bookshelf 1
    t = base_for(src)
    if not t: print('  no template shows', v['from']); continue
    W.apply([{'op': 'itempnew', 'from': t, 'name': v['name'][:39]}], 'wall decor'); nt = W.made[1]
    sp = [n, 48017 if n == 48016 else 0]
    W.apply([{'op': 'itempset', 't': nt, 'fields': {'sprite': sp, 'driver': 0, 'data': [0] * 10}, 'update_map': False}], 'wall decor look')
    made.append((nt, v['name']))
for t, name in made: print(t, name)
print(W.save())
