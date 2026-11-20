#!/usr/bin/env python3
"""Steps up a ledge or a cliff (Nov 19; Cody: the plain ramp "leaves a little to be desired"). A flight of steps cut
into the face right behind a lower tile T, from the low ground up to the rim, the cut's walls in shadow at either side.
The face behind T hangs over T and the tiles in front of it, so the steps come in PIECES: one object per tile they
cover, each drawn inside its own tile (so people and things on each tile are drawn in the right order). The editor's
Steps brush puts all the pieces down at once and keeps those tiles walkable.

    world_steps.py <client folder> [--out <folder>]

  37532-37567: the pieces of (earth, up toward x-1), (earth, up toward y+1), (stone 26 px, x-1), (stone, y+1), every
  mix of side-by-side flights (see main); world_steps.json: offsets and combos for each kind.
"""
import json, math, os, random, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg
from world_chasm import screen_tile

BASE = 37532
KINDS = [  # (direction, wall height, steps, tread, riser)
    ('N', 13.0, 3, (178, 152, 110), (84, 66, 46)),
    ('E', 13.0, 3, (178, 152, 110), (84, 66, 46)),
    ('N', 26.0, 6, (184, 180, 170), (88, 84, 78)),
    ('E', 26.0, 6, (184, 180, 170), (88, 84, 78)),
]


def make(kind, seed):
    """{(dx, dy): 32x32 piece}"""
    dr, H, n, tread, riser = kind
    r = random.Random(seed)
    behind = (-1, 0) if dr == 'N' else (0, 1)
    high = (lambda tx, ty: tx <= -1) if dr == 'N' else (lambda tx, ty: ty >= 1)
    pieces = {}
    for y in range(-24, 72):
        for x in range(-40, 72):
            tx0, ty0, _, _ = screen_tile(x, y)
            if high(tx0, ty0): continue                   # on the higher ground itself
            d = 0.0; hit = None
            while d < H:
                d += 0.5
                tx, ty, tu, tv = screen_tile(x, y - d)
                if high(tx, ty):
                    hit = (tx, ty, tu, tv); break
            if not hit or (hit[0], hit[1]) != behind: continue
            along = hit[3] if dr == 'N' else hit[2]
            side = 0.5 - abs(along)
            q = (d / H) * n; band = q - int(q)
            c0 = tread if band < 0.5 else [k * 1.12 for k in tread] if band < 0.62 else riser
            g = r.random()
            col = [c0[i] * (1 - 0.15 * (d / H)) * (1 + 0.12 * (g - 0.5)) for i in range(3)]
            if side < 0.12: col = [c * (0.5 + 3.5 * side) for c in col]          # the cut's walls
            lx, ly = x - 16 * (tx0 + ty0), y - 8 * (tx0 - ty0)                     # in that tile's own 32x32
            if not (0 <= lx < 32 and 0 <= ly < 32 and wg.IN(lx, ly)): continue
            im = pieces.setdefault((tx0, ty0), Image.new('RGBA', (32, 32), (0, 0, 0, 0)))
            im.putpixel((lx, ly), tuple(max(0, min(255, int(c))) for c in col) + (255,))
    return pieces


def main():
    """a wide flight (steps side by side along the rim) puts two flights' pieces on one tile, and a tile holds one object:
    so each piece is made for every mix of flights that can reach its tile. kinds[i]: offsets = where one flight's pieces
    lie from its own tile T; combos[bits] = the sprite for a tile reached by the flights at tile - offsets[j] for each
    bit j set."""
    a = sys.argv[1:]; client = a[0]
    out = a[a.index('--out') + 1] if '--out' in a else wg.gfx_dir(client)
    nr = BASE; table = []
    for i, k in enumerate(KINDS):
        ps = make(k, BASE + 100 + i)
        ps = {o: im for o, im in ps.items() if sum(1 for yy in range(32) for xx in range(32) if im.getpixel((xx, yy))[3]) >= 6}
        offs = sorted(ps); combos = {}
        for bits in range(1, 1 << len(offs)):
            im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            for j, o in enumerate(offs):
                if bits >> j & 1: im.alpha_composite(ps[o])
            im.save(os.path.join(out, '%d.png' % nr)); combos[bits] = nr; nr += 1
        table.append({'dir': k[0], 'wall': k[1], 'offsets': [list(o) for o in offs], 'combos': combos})
    json.dump({'base': BASE, 'kinds': table, 'next_free': nr}, open(os.path.join(HERE, 'world_steps.json'), 'w'), indent=1)
    print('steps', BASE, '-', nr - 1, '->', out)


if __name__ == '__main__':
    main()
