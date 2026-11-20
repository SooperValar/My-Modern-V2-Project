#!/usr/bin/env python3
"""Chasm ground for the Gargoyle Spires (Nov 19; Cody: "like you're walking over a chasm"). A chasm tile is a hole: you
look down past the cliff walls of the land behind it (north = map x-1 and east = map y+1 face the viewer) into a dark
drop with drifting mist. Each pixel is worked out like a ray: from the pixel, go up the screen d pixels; the first land
met is a cliff wall seen d pixels below its rim (bright granite with a snow lip at the top, darker the deeper); no land
within reach = the misty dark below. So the walls join up across tiles by themselves.

    world_chasm.py <client folder> [--out <folder>] [--preview <png>]

  37400 + 4*mask + variant, mask = land at N (1) / E (2) / NE (4) / x-2,y+1 (8) / x-1,y+2 (16): 128 sprites, 37400-37527
  (mask 0 = only the drop: 37400-37403; bits 8 and 16 let a wall run a second tile deep).   Next free: 37528
The tiles block walking (map flag bit 0, set by the build script). Writes world_chasm.json beside this script."""
import json, math, os, random, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg

BASE = 37400
H = 26.0                       # how far down (screen pixels) the walls can be seen before the dark takes them
ROCK = (150, 150, 152)         # the game's granite cliffs (1204 / 1206 average ~140 grey)
SNOW = (226, 231, 238)         # soft snow 35400
DEEP = (10, 13, 19)
MIST = (70, 82, 100)
NB = {'N': (-1, 0), 'E': (0, 1), 'NE': (-1, 1), 'NNE': (-2, 1), 'NEE': (-1, 2)}      # map tiles that can show a wall in this tile


def screen_tile(px, py):
    """which map tile (dx, dy relative to this one) a screen pixel (relative to this tile's 32x32 image) lies on"""
    u, v = wg.local(px, py)            # toward x+1, toward y+1 (-0.5..0.5 inside this tile)
    return math.floor(u + 0.5), math.floor(v + 0.5), u, v


def periodic(u, v, ph, k=1):
    t = 2 * math.pi
    return (math.sin(t * k * u + ph[0]) * math.sin(t * k * v + ph[1]) + 0.6 * math.sin(t * (u + v) * k + ph[2])
            + 0.4 * math.sin(t * (2 * u - v) + ph[3]))


def tile(mask, var):
    land = {(0, 0): False}
    for bit, k in ((1, 'N'), (2, 'E'), (4, 'NE'), (8, 'NNE'), (16, 'NEE')):
        land[NB[k]] = bool(mask & bit)
    r = random.Random(BASE + mask * 4 + var); ph = [r.random() * 6.28 for _ in range(8)]
    cracks = [r.uniform(0, 32) for _ in range(5)]
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
    for y in range(17, 32):
        for x in range(32):
            if not wg.IN(x, y): continue
            u, v = wg.local(x, y)
            # the drop: near-black with faint mist drifting (periodic in u, v: seamless)
            m = 0.5 + 0.5 * periodic(u, v, ph[:4]) / 2.0                  # soft wisps, no grain
            m = max(0.0, m - 0.45) * 0.45 + 0.012 * r.random()
            col = tuple(DEEP[i] + (MIST[i] - DEEP[i]) * m for i in range(3))
            # a wall? go up the screen
            d = 0.0
            while d < H + 6:
                d += 0.5
                tx, ty, _, _ = screen_tile(x, y - d)
                if (tx, ty) == (0, 0): continue
                if land.get((tx, ty)):
                    f = d / H                                           # 0 at the rim, 1 where it is gone in the mist
                    if f >= 1: break
                    # Cody (Nov 19): the walls' bottoms showed as jagged teeth (they follow the rim's tile corners): the
                    # rock now melts into the drop below - the mist itself, not black - so there is no line where it ends
                    strata = 0.10 * math.sin(d * 1.3 + ph[4]) + 0.06 * math.sin(d * 3.1 + ph[5])
                    crack = min(abs(x - c) for c in cracks)
                    lit = (1.0 - 0.35 * f) * (1 + strata) * (0.8 if crack < 0.8 else 1.0) * (1 + 0.08 * (r.random() - 0.5))
                    k = (1 - f) ** 1.2                                        # how much rock shows (a long, even fade)
                    rock = tuple(ROCK[i] * lit * k + col[i] * (1 - k) for i in range(3))
                    if d <= 1.5: rock = SNOW                                # snow lip on the rim
                    elif d <= 2.5: rock = tuple(0.5 * SNOW[i] + 0.5 * rock[i] for i in range(3))
                    col = rock
                    break
                if (tx, ty) not in land: break          # beyond the neighbours we know: treat as drop
            px[x, y] = tuple(max(0, min(255, int(c))) for c in col) + (255,)
    return im


def main():
    a = sys.argv[1:]; client = a[0]
    out = a[a.index('--out') + 1] if '--out' in a else wg.gfx_dir(client)
    os.makedirs(out, exist_ok=True); table = {}
    for mask in range(32):
        for var in range(4):
            n = BASE + mask * 4 + var; tile(mask, var).save(os.path.join(out, '%d.png' % n))
        table[str(mask)] = BASE + mask * 4
    json.dump({'base': BASE, 'mask': 'N=1 E=2 NE=4 (x-2,y+1)=8 (x-1,y+2)=16', 'by_mask': table, 'next_free': BASE + 128},
              open(os.path.join(HERE, 'world_chasm.json'), 'w'), indent=1)
    if '--preview' in a:
        sh = Image.new('RGBA', (32 * 40, 4 * 40), (40, 40, 40, 255))
        for mask in range(32):
            for var in range(4):
                sh.paste(Image.open(os.path.join(out, '%d.png' % (BASE + mask * 4 + var))), (mask * 40 + 4, var * 40 + 4))
        sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(a[a.index('--preview') + 1])
    print('chasm sprites', BASE, '-', BASE + 127, '->', out)


if __name__ == '__main__':
    main()
