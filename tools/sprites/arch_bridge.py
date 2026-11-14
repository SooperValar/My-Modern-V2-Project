#!/usr/bin/env python3
"""Arch bridges: one tile of straight arch top, to make the game's stone arches as wide as you like.

    arch_bridge.py <folder with the game's sprites as NNNNN.png, or the client folder> <out folder>

An arch is two halves, the second 4 tiles from the first:
  down-right (map x): 942 + 934                      -> bridge 36401
  up-right (map y):   36402 + 36403 (the same arch mirrored) -> bridge 36400
To widen an arch by N tiles: put N bridges on the tiles right after the first half and the second half N tiles
further (4 + N).
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
    """36401: bridge for the down-right arch 942 + 934 (64x128, the beam in its right half: it belongs three tiles
    further down-right than the tile it stands on, so bridges go on the tiles right after the first half).
    The up-right arch is the down-right one mirrored (the game's own up-right arch 937 + 944 can't be widened
    cleanly: its end isn't level): 36402 first half (934 mirrored), 36403 second half (942 mirrored), 36400 bridge."""
    bx = bridge(get(942), list(range(64, 80)), range(48, 64), lambda lx: 52 + (lx - 47) / 2.0, 29, 64, 128, 2)
    flip = lambda im: im.transpose(Image.FLIP_LEFT_RIGHT)
    by = Image.new('RGBA', bx.size, (0, 0, 0, 0))
    by.alpha_composite(flip(bx), (48, -24))      # mirrored, and moved so it too stands on the tiles right after the first half
    return {36401: bx, 36400: by, 36402: flip(get(934)), 36403: flip(get(942))}

NAMES = {36400: 'Arch bridge (up-right)', 36401: 'Arch bridge (down-right)', 36402: 'Arch up-right, first half', 36403: 'Arch up-right, second half'}

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
