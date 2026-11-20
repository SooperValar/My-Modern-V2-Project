#!/usr/bin/env python3
"""Water below the ground (Nov 19; Cody: "make this work with a water look" - sea cliffs first, then low banks and a stone
canal; "pull from the game's existing water tiles, and semi randomized so it doesn't look so tiled"). The same trick as
world_chasm.py: a water tile looks up the screen for the ground behind it (map x-1 and y+1 face the viewer) and draws that
ground's side going down to the water. The water itself IS the game's water: each tile is built on one of the game's four
water tiles (picked at random when painted, as the game's own water is), so open water looks exactly like the game's.

    world_water.py <client folder> <style> [--out <folder>]      style: sea (banks and canal to come)

  BASE + 16*mask + 4*(x % 4) + (y % 4): the water is one picture 4 x 4 tiles big (Cody: "the water itself is still a bit
  repetitive"): the game's water tiles under a light-and-shade and ripple pattern that runs on across tile edges, so each
  tile's sprite depends on where it lies (the editor picks it from the map position). mask as the chasm: (x-1,y)=1
  (x,y+1)=2 (x-1,y+1)=4 (x-2,y+1)=8 (x-1,y+2)=16 (x-2,y+2)=32. 1024 sprites a style.
  sea 46000-47023; banks 48026-49049 (free 48026-49999); canal: a free block still to pick. 37532-37659: an early try, unused.
Writes world_water_<style>.json beside this script. The tiles block walking (the editor sets it, like the chasm)."""
import json, math, os, random, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg
from world_chasm import screen_tile, NB

GAME_WATER = (16933, 16957, 16958, 16959)          # the game's deep blue water (about 7,000 tiles of the world)
STYLES = {
    # sea cliffs: tall grey rock down to the game's water, wet dark rock and weed at the bottom, a broken line of foam,
    # the cliff's shadow on the water
    'sea': dict(base=46000, wall=23.0, lip=(176, 174, 168), rock=(132, 130, 124), wet=(58, 62, 62), weed=(46, 66, 46),
                foam=(214, 228, 240), shade=0.5),
}
T = 2 * math.pi
def wave(u, v, ph):
    """seamless (whole-number frequencies in u, v) but irregular: a few waves of different directions"""
    return (math.sin(T * (u + 2 * v) + ph[0]) + 0.7 * math.sin(T * (3 * u - v) + ph[1]) + 0.5 * math.sin(T * (2 * u + 3 * v) + ph[2])
            + 0.35 * math.sin(T * (5 * u + v) + ph[3])) / 2.55


P4 = 4                      # the water picture repeats every 4 x 4 tiles


class Water:
    """one seamless water picture 4 x 4 tiles big in the game's water colours: the game's four water tiles give the
    colours (the same mix of dark and light), smooth random noise at a few sizes and per-pixel grain give the pattern,
    and a few short light ripples lie here and there. Nothing in it lines up with the tile edges."""
    def __init__(self, waters, seed):
        cols = [w.getpixel((x, y))[:3] for w in waters for y in range(w.height) for x in range(w.width) if w.getpixel((x, y))[3]]
        self.pal = sorted(cols, key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
        R = random.Random(seed)
        self.oct = []
        for res, wgt in ((1, 0.22), (2, 0.28), (4, 0.25), (8, 0.25)):         # lattice cells per tile, weight
            n = P4 * res
            self.oct.append((res, n, wgt, [[R.random() for _ in range(n)] for _ in range(n)]))
        self.grain = random.Random(seed + 1)
        # ripples: (X, Y) centres and lengths in screen pixels
        self.rip = [(R.uniform(0, P4), R.uniform(0, P4), R.choice((4, 5, 6, 7, 9))) for _ in range(22)]

    def noise(self, X, Y):
        v = 0.0
        for res, n, wgt, g in self.oct:
            fx, fy = X * res, Y * res
            ix, iy = math.floor(fx), math.floor(fy); ax, ay = fx - ix, fy - iy
            ax = ax * ax * (3 - 2 * ax); ay = ay * ay * (3 - 2 * ay)
            a = g[ix % n][iy % n]; b = g[(ix + 1) % n][iy % n]; c = g[ix % n][(iy + 1) % n]; d = g[(ix + 1) % n][(iy + 1) % n]
            v += wgt * ((a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay)
        return v

    def at(self, X, Y, r):
        v = 0.72 * self.noise(X, Y) + 0.28 * r.random()
        v = min(0.999, max(0.0, (v - 0.5) * 1.9 + 0.5))                         # spread back out to the game's contrast
        col = list(self.pal[int(v * len(self.pal))])
        sx, sy = 16 * (X + Y), 8 * (X - Y)
        for cx, cy, ln in self.rip:
            for ox in (-P4, 0, P4):
                for oy in (-P4, 0, P4):
                    rx, ry = 16 * (cx + ox + cy + oy), 8 * (cx + ox - cy - oy)
                    if abs(sy - ry) < 0.5 and abs(sx - rx) < ln / 2:
                        return [col[i] * 0.3 + (110, 150, 235)[i] * 0.7 for i in range(3)]
        return col


def tile(st, mask, pos, waters):
    land = {(0, 0): False}
    for bit, n in ((1, 'N'), (2, 'E'), (4, 'NE'), (8, 'NNE'), (16, 'NEE'), (32, 'NNEE')):
        land[NB[n]] = bool(mask & bit)
    H = st['wall']
    r = random.Random(st['base'] + mask * 16 + pos[0] * 4 + pos[1])
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
    for y in range(17, 32):
        for x in range(32):
            if not wg.IN(x, y): continue
            u, v = wg.local(x, y)
            col = WATER.at(pos[0] + u, pos[1] + v, r)
            if mask == 0:
                px[x, y] = tuple(max(0, min(255, int(c))) for c in col) + (255,); continue
            d = 0.0
            while d < H + 12:
                d += 0.5
                tx, ty, tu, tv = screen_tile(x, y - d)
                if (tx, ty) == (0, 0): continue
                if land.get((tx, ty)):
                    if d < H:                                          # the cliff face
                        f = d / H
                        # the rock's look depends on where along the cliff (tu, tv) and how deep (d): the same on both sides
                        # of a tile edge, so the face runs on without seams; the grain is per pixel (no pattern to repeat)
                        strata = 0.08 * math.sin(d * 1.15 + 1.0) + 0.05 * math.sin(d * 2.9 + 2.3)
                        g = r.random()                                  # grain, with now and then a dark pit or a light fleck
                        lit = (1 - 0.32 * f) * (1 + strata) * (1 + 0.16 * (g - 0.5)) * (0.72 if g < 0.04 else 1.18 if g > 0.97 else 1.0)
                        rock = [st['rock'][i] * lit for i in range(3)]
                        if f > 0.6:                                    # wet rock, and weed in patches, near the water
                            w = min(1.0, (f - 0.6) / 0.25)
                            low = st['weed'] if wave(tu, tv, (4.0, 1.1, 0.2, 5.5)) > 0.15 else st['wet']
                            rock = [rock[i] + (low[i] * (1 + 0.15 * (r.random() - 0.5)) - rock[i]) * w for i in range(3)]
                        if d <= 1.5: rock = list(st['lip'])            # a light rim on top (no snow: any ground)
                        col = rock
                    else:                                              # the water at its foot: foam, then the cliff's shadow
                        e = d - H
                        sh = st['shade'] * max(0.0, 1 - e / 10)
                        col = [c * (1 - sh) for c in col]
                        fw = wave(tu, tv, (1.7, 3.2, 0.5, 4.4))       # where the foam is thick (-1..1)
                        fo = max(0.0, 1 - e / (1.8 + 1.6 * max(0.0, fw))) * (0.55 + 0.45 * fw)
                        if r.random() < 0.18 * max(0.0, 1 - e / 6) * (1 + fw): fo = max(fo, 0.6)     # loose flecks
                        col = [col[i] + (st['foam'][i] - col[i]) * max(0.0, min(1.0, fo)) for i in range(3)]
                    break
                if (tx, ty) not in land: break
            px[x, y] = tuple(max(0, min(255, int(c))) for c in col) + (255,)
    return im


def main():
    a = sys.argv[1:]; client, style = a[0], a[1]; st = STYLES[style]; BASE = st['base']
    out = a[a.index('--out') + 1] if '--out' in a else wg.gfx_dir(client)
    os.makedirs(out, exist_ok=True)
    S = wg.Sprites(client); waters = [S.get(n) for n in GAME_WATER]
    global WATER; WATER = Water(waters, BASE)
    for mask in range(64):
        for a_ in range(4):
            for b_ in range(4):
                tile(st, mask, (a_, b_), waters).save(os.path.join(out, '%d.png' % (BASE + mask * 16 + a_ * 4 + b_)))
    json.dump({'base': BASE, 'style': style, 'stride': 16, 'count': 1024, 'water': GAME_WATER,
               'mask': 'N=1 E=2 NE=4 (x-2,y+1)=8 (x-1,y+2)=16 (x-2,y+2)=32; + 4*(x%4) + (y%4)'},
              open(os.path.join(HERE, 'world_water_%s.json' % style), 'w'), indent=1)
    print(style, BASE, '-', BASE + 1023, '->', out)


if __name__ == '__main__':
    main()
