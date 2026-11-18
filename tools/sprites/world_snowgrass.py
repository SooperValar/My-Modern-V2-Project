#!/usr/bin/env python3
"""Snowy grass for Stonehold (Nov 17; Cody: "a snowy grass look... towards the top of a mountain"): cold, pale alpine
grass with snow lying in patches, and its soft edges, made like world_marsh.py's marsh grass.

    world_snowgrass.py <client folder> [--out <folder>] [--sheet <png>]

  snowy grass 36100-36103 (4 variants) + 36104-36149: grass (551-554) blending into snowy grass
Edges on a SNOWY GRASS base (46 each, in the order of world_ground.all_masks()):
  soft snow (35400) 36150-36195, path (35000) 36196-36241, dusty path (35100) 36242-36287.
Writes tools/sprites/world_snowgrass.json beside this script."""
import colorsys, json, math, os, random, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg

FIRST = 36100
ON_SNOWY = {'soft snow': 36150, 'path': 36196, 'dusty path': 36242}

def snowy(grass, snow, seed, cover=0.30):
    """the grass tile's grain in a cold, pale olive-green, with snow from the soft snow tile lying in soft patches"""
    r = random.Random(seed); g = grass.load(); s = snow.load()
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = out.load()
    ph = [r.random() * 6.28 for _ in range(6)]
    blobs = [(r.uniform(-0.5, 0.5), r.uniform(-0.5, 0.5), r.uniform(0.07, 0.15)) for _ in range(r.randrange(3, 6))]
    for y in range(32):
        for x in range(32):
            if not wg.IN(x, y): continue
            rr, gg, bb = [c / 255 for c in g[x, y][:3]]
            h, sa, v = colorsys.rgb_to_hsv(rr, gg, bb)
            h, sa, v = 0.20 + (h - 0.25) * 0.4, sa * 0.42, min(1, v * 0.92 + 0.10)       # alpine: yellower, greyer, paler
            col = [int(c * 255) for c in colorsys.hsv_to_rgb(h, sa, v)]
            xl, yl = wg.local(x, y)
            n = 0.5 + 0.18 * math.sin(xl * 9 + ph[0]) * math.sin(yl * 11 + ph[1]) + 0.12 * math.sin((xl - yl) * 17 + ph[2])
            for bx, by, br in blobs:
                d = math.hypot(xl - bx, yl - by)
                n += max(0, 0.55 * (1 - d / br))
            k = n + r.uniform(-0.12, 0.12)
            if k > 1.0 - cover:                                       # snow
                col = list(s[x, y][:3])
            elif k > 0.92 - cover:                                    # frosted fringe: grass and snow mixed
                col = [int(a * 0.45 + b * 0.55) for a, b in zip(col, s[x, y][:3])]
            px[x, y] = tuple(col) + (255,)
    return out

def build(client):
    S = wg.Sprites(client); grass = [S.get(n) for n in wg.GRASS]; masks = wg.all_masks(); out = {}
    snow = [S.get(n) for n in (35400, 35401, 35402, 35403)]
    plain = [snowy(grass[k], snow[k], FIRST + k) for k in range(4)]
    for k, t in enumerate(plain): out[FIRST + k] = t
    table = {'masks': masks, 'grass_base': {}, 'snowy_base': {}}
    edges = {}
    for i, m in enumerate(masks):
        out[FIRST + 4 + i] = wg.blend(grass[i % 4], plain[(i // 4) % 4], m, seed=FIRST + m); edges[str(m)] = FIRST + 4 + i
    table['grass_base']['snowy grass'] = {'plain': [FIRST + k for k in range(4)], 'edges': edges}
    other = {'soft snow': snow, 'path': [S.get(n) for n in (35000, 35001, 35002, 35003)], 'dusty path': [S.get(n) for n in (35100, 35101, 35102, 35103)]}
    for name, first in ON_SNOWY.items():
        e = {}
        for i, m in enumerate(masks):
            out[first + i] = wg.blend(plain[i % 4], other[name][(i // 4) % 4], m, seed=first + m); e[str(m)] = first + i
        table['snowy_base'][name] = e
    return out, table

if __name__ == '__main__':
    client = sys.argv[1]
    sprites, table = build(client)
    gfx = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else wg.gfx_dir(client)
    os.makedirs(gfx, exist_ok=True)
    for nr, im in sorted(sprites.items()): im.save(os.path.join(gfx, '%05d.png' % nr))
    json.dump(table, open(os.path.join(HERE, 'world_snowgrass.json'), 'w'), indent=1)
    print('%d sprites written: %d-%d' % (len(sprites), min(sprites), max(sprites)))
