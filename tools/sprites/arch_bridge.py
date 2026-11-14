#!/usr/bin/env python3
"""Arch bridges: one tile of straight arch top, to make the game's stone arches as wide as you like.

    arch_bridge.py <folder with the game's sprites as NNNNN.png, or the client folder> <out folder>

The game's arches come in two halves that meet when the second half stands a fixed number of tiles away:
  along map y (screen up-right):   937 + 944 (or 945) five tiles further   -> bridge 36400
  along map x (screen down-right): 942 (or 943) + 934 (or 935) four tiles further -> bridge 36401
To widen an arch by N tiles: move the second half N tiles further and put a bridge on each of the N tiles just
before it (the tiles it stood on and the ones after).
Each beam column is cut from the original piece's own stone near the join and resampled into a straight band, so it
matches the arch. (Geometry worked out from the pieces; see the scene test in the Nov 13 notes.)
"""
import os, sys
from PIL import Image

def column(src, sx):
    p = src.load(); run = [y for y in range(src.size[1]) if p[sx, y][3]]
    t0 = run[0]; t1 = t0
    while t1 + 1 in run: t1 += 1        # first opaque run from the top = the beam (not a pillar below it)
    return [p[sx, y] for y in range(t0, t1 + 1)]

def bridge(src, cols, xs, top_fn, thick, w, h, seed):
    """each row of the band takes the stone of the same depth in the beam, from a random source column: the beam's
    light-to-dark shading stays, the copied columns don't make stripes"""
    import random
    r = random.Random(seed)
    cs = [column(src, x) for x in cols]
    rows = [[c[min(len(c) - 1, k * len(c) // thick)] for c in cs] for k in range(thick)]
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); op = out.load()
    for lx in xs:
        y0 = int(round(top_fn(lx)))
        for k in range(thick):
            op[lx, y0 + k] = r.choice(rows[k])
    return out

def build(get):
    # along y: 32x96, beam in the left half only (the right half is the next piece's), top 26 at x 0, rising 1 in 2
    by = bridge(get(937), list(range(128, 144)), range(16), lambda lx: 26 - lx / 2.0, 26, 32, 96, 1)
    # along x: 96x128, beam at x 16..31 (it belongs one tile further back than the tile it stands on, so a bridge
    # can stand on the tiles just before the second half), top 28.5 at x 16, falling 1 in 2
    bx = bridge(get(942), list(range(64, 80)), range(16, 32), lambda lx: 28 + (lx - 15) / 2.0, 29, 96, 128, 2)
    return {36400: by, 36401: bx}

NAMES = {36400: 'Arch bridge (up-right)', 36401: 'Arch bridge (down-right)'}

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    if os.path.exists(os.path.join(src, 'gx00.idx')):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import world_ground as WG
        S = WG.Sprites(src); get = S.get
    else:
        get = lambda n: Image.open(os.path.join(src, '%05d.png' % n)).convert('RGBA')
    os.makedirs(out, exist_ok=True)
    for nr, im in build(get).items():
        im.save(os.path.join(out, '%05d.png' % nr))
    print('arch bridges written: 36400 36401')
