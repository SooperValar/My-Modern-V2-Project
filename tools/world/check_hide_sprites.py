#!/usr/bin/env python3
"""With "hide walls" on, the client draws every object drawn into a tile (not items) as sprite+1, its cut-down form
(engine.c hide_sprite; the game's trees use stumps 18190+). This lists the objects on the map whose sprite+1 is missing
("Sprite N is missing" in client.log).   check_hide_sprites.py <client folder> <server folder>
Fix: a <N+1>.png in the client's GFX (a cut-down form, or a copy), then publish the client."""
import sys, os, struct, collections
C, S = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], C, '/tmp']
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spritesheets.py')).read().split('ids=sorted')[0])
m = open(os.path.join(S, '.dat', 'map.dat'), 'rb').read()
TREE = {320, 356, 358, 360, 362, 880, 882, 884, 1112, 1114, 1116, 1238, 1240}
c = collections.Counter()
for i in range(0, len(m), 28):
    fs = struct.unpack_from('<H', m, i + 2)[0]
    if fs: c[fs] += 1
miss = []
for s, n in sorted(c.items()):
    if s in TREE or s - 1 in TREE: continue
    try: ok = load(s + 1)
    except Exception: ok = None
    if not ok: miss.append((s, n))
print('objects whose hidden form (sprite+1) is missing:', miss or 'none')
