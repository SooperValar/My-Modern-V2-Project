#!/usr/bin/env python3
"""Nov 15: Cody wants to make the Wolfwood area himself. Takes out everything build_wolfwood.py / fix_wolfwood.py added
to the map: the placed wolves, Greyfang and Edda (and their templates), Edda's quests, the zones, the placed items,
and the map tiles back as they were in the backup taken before the build. Kept: the item templates (heads, fang,
amulet, sign, bones) and the sprites.
    clear_wolfwood.py <.dat folder> <backup folder from before build_wolfwood.py>"""
import sys, os, json, importlib.util, struct
HERE = os.path.dirname(os.path.abspath(__file__)); DAT, BK = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
NPCS = M['greys'] + M['dires'] + [M['greyfang'], M['edda']]
RX0, RX1, RY0, RY1 = 536, 680, 596, 856
old = open(os.path.join(BK, 'map.dat'), 'rb').read()
# 1. the NPCs
where = {}
for x in range(RX0, RX1 + 1):
    for y in range(RY0, RY1 + 1):
        c = W.tile(x, y)[2]
        if c: where[c] = (x, y)
for t in NPCS:
    spots = [where[c] for c in W.living(t) if c in where] + [(p[0], p[1]) for p in W.pending() if p[2] == t]
    for x, y in spots: print('  remove', t, (x, y), W.apply([{'op': 'npcremove', 'x': x, 'y': y}], 'clear Wolfwood')[1])
for t in NPCS + [M['edda_dire'], M['edda_fang']]:
    if W.tchar[t * me.CHAR_SIZE + me.C_USED]: W.tchar[t * me.CHAR_SIZE + me.C_USED] = 0     # free the template
# 2. items the build placed: every tile in the region that holds an item now but held none before
ops = []
for x in range(RX0, RX1 + 1):
    for y in range(RY0, RY1 + 1):
        o = (x + y * 1024) * 28
        if W.tile(x, y)[4] and struct.unpack_from('<I', old, o + 12)[0] == 0: ops.append({'op': 'erase', 'x': x, 'y': y})
print('items erased', len(ops), W.apply(ops, 'clear Wolfwood items')[1][:3])
print(W.save())
# 3. Edda's quests, the zones
qs, npcs = W.talk_load()
for t in (M['edda'], M['edda_dire'], M['edda_fang']):
    for k in ('alias', 'order', 'qrew'): qs[k].pop(t, None)
    npcs.pop(t, None)
print(W.talk_save(qs, npcs))
zs, order = {}, []
for x0, y0, x1, y1, nm, fl in W.areas:
    if nm in ('Wolfwood', "Hunters' Lodge"): continue
    if nm not in zs: zs[nm] = {'name': nm, 'flag': fl, 'boxes': []}; order.append(nm)
    zs[nm]['boxes'].append([x0, y0, x1, y1])
print('zones:', W.zones_save([zs[n] for n in order]))
# 4. the map tiles as they were (raw; only tiles that hold no item in either version)
cur = bytearray(open(os.path.join(DAT, 'map.dat'), 'rb').read()); n = 0
for x in range(RX0, RX1 + 1):
    for y in range(RY0, RY1 + 1):
        o = (x + y * 1024) * 28
        if old[o:o + 28] != cur[o:o + 28] and struct.unpack_from('<I', old, o + 12)[0] == 0 and struct.unpack_from('<I', cur, o + 12)[0] == 0:
            keep = bytes(cur[o + 4:o + 12]); cur[o:o + 28] = old[o:o + 28]; cur[o + 4:o + 12] = keep; n += 1     # (whoever stands there now stays)
open(os.path.join(DAT, 'map.dat'), 'wb').write(cur)
print('tiles restored', n)
