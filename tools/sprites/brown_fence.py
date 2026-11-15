#!/usr/bin/env python3
"""The game's red Wooden Fence (1172-1183) recoloured to brown wood (Nov 14), keeping its shapes and shading:
each pixel's brightness picks a colour on a brown-wood ramp, with a faint grain. 40220-40231 in the game's
order: 40220 along y (from 1172), 40222 along x (1174), 40224-40230 the corners (1176, 1178, 1180, 1182), each
N+1 its hidden-walls copy (from the game's N+1). Adds the type to world_fences.json.
    brown_fence.py <client folder> [--out <folder>]"""
import json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FIRST, SRC = 40220, 1172
RAMP = ((34, 20, 8), (92, 60, 30), (146, 104, 60))


def ramp(t):
    d, m, l = RAMP
    if t < 0.5: k = t / 0.5; return tuple(int(d[i] + (m[i] - d[i]) * k) for i in range(3))
    k = (t - 0.5) / 0.5; return tuple(int(m[i] + (l[i] - m[i]) * k) for i in range(3))


def main():
    client = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(client, 'GFX')
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    r = random.Random(7)
    for k in range(12):
        im = load(SRC + k).convert('RGBA'); px = im.load()
        lum = [max(px[x, y][:3]) for y in range(im.height) for x in range(im.width) if px[x, y][3]]
        lo, hi = min(lum), max(lum)
        for y in range(im.height):
            for x in range(im.width):
                c = px[x, y]
                if not c[3]: continue
                t = (max(c[:3]) - lo) / max(1, hi - lo)
                t = 0.06 + 0.78 * t + 0.08 * (r.random() - 0.5) + 0.05 * ((y * 3 + x) % 4 == 0)
                px[x, y] = ramp(max(0, min(1, t))) + (255,)
        im.save(os.path.join(out, '%05d.png' % (FIRST + k)))
    p = os.path.join(HERE, 'world_fences.json'); f = json.load(open(p))
    f = [e for e in f if e[0] != FIRST] + [[FIRST, 'Brown Wooden Fence', 1, [FIRST + 2 * j for j in range(6)]]]
    json.dump(f, open(p, 'w')); print('brown fence %d-%d' % (FIRST, FIRST + 11))


if __name__ == '__main__':
    main()
