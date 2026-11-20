#!/usr/bin/env python3
"""Water below the ground (Nov 19; Cody: "make this work with a water look" - sea cliffs first, then low banks and a stone
canal; "pull from the game's existing water tiles, and semi randomized so it doesn't look so tiled"). The same trick as
world_chasm.py: a water tile looks up the screen for the ground behind it (map x-1 and y+1 face the viewer) and draws that
ground's side going down to the water. The water itself IS the game's water: each tile is built on one of the game's four
water tiles (picked at random when painted, as the game's own water is), so open water looks exactly like the game's.

    world_water.py <client folder> <style> [--out <folder>]      style: sea (banks and canal to come)

  BASE + P*P*mask + P*(x % P) + (y % P) (P: sea 4, banks and canal 3): the water is one picture P x P tiles big (Cody: "the water itself is still a bit
  repetitive"): the game's water tiles under a light-and-shade and ripple pattern that runs on across tile edges, so each
  tile's sprite depends on where it lies (the editor picks it from the map position). mask as the chasm: (x-1,y)=1
  (x,y+1)=2 (x-1,y+1)=4 (x-2,y+1)=8 (x-1,y+2)=16 (x-2,y+2)=32.
  sea 46000-47023 (1024), canal 47024-47599 (576), banks 48026-48601 (576). 37532-37659: an early try, unused.
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
    'sea': dict(base=46000, period=4, ripples=22, face='rock', wall=23.0, lip=(176, 174, 168), rock=(132, 130, 124),
                wet=(58, 62, 62), weed=(46, 66, 46), foam=(214, 228, 240), shade=0.5),
    # low banks: a short earth bank (a dark sod edge, brown soil, wet at the foot) down to the water; little foam
    'banks': dict(base=48026, period=3, ripples=12, face='earth', wall=8.0, lip=(62, 54, 36), rock=(116, 88, 60),
                  wet=(58, 46, 34), weed=(52, 64, 40), foam=(150, 182, 214), shade=0.32),
    # a stone canal / moat: courses of fitted stone with a pale coping on top, green-black at the waterline; still water
    'canal': dict(base=47024, period=3, ripples=6, face='stone', wall=14.0, lip=(192, 188, 178), rock=(146, 142, 134),
                  wet=(50, 60, 50), weed=(46, 62, 42), foam=(170, 196, 220), shade=0.45),
}
T = 2 * math.pi
def wave(u, v, ph):
    """seamless (whole-number frequencies in u, v) but irregular: a few waves of different directions"""
    return (math.sin(T * (u + 2 * v) + ph[0]) + 0.7 * math.sin(T * (3 * u - v) + ph[1]) + 0.5 * math.sin(T * (2 * u + 3 * v) + ph[2])
            + 0.35 * math.sin(T * (5 * u + v) + ph[3])) / 2.55




class Water:
    """one seamless water picture 4 x 4 tiles big in the game's water colours: the game's four water tiles give the
    colours (the same mix of dark and light), smooth random noise at a few sizes and per-pixel grain give the pattern,
    and a few short light ripples lie here and there. Nothing in it lines up with the tile edges."""
    def __init__(self, waters, seed, P=4, nrip=22):
        self.P = P
        cols = [w.getpixel((x, y))[:3] for w in waters for y in range(w.height) for x in range(w.width) if w.getpixel((x, y))[3]]
        self.pal = sorted(cols, key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
        R = random.Random(seed)
        self.oct = []
        for res, wgt in ((1, 0.22), (2, 0.28), (4, 0.25), (8, 0.25)):         # lattice cells per tile, weight
            n = P * res
            self.oct.append((res, n, wgt, [[R.random() for _ in range(n)] for _ in range(n)]))
        self.grain = random.Random(seed + 1)
        # ripples: (X, Y) centres and lengths in screen pixels
        self.rip = [(R.uniform(0, P), R.uniform(0, P), R.choice((4, 5, 6, 7, 9))) for _ in range(nrip)]

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
            for ox in (-self.P, 0, self.P):
                for oy in (-self.P, 0, self.P):
                    rx, ry = 16 * (cx + ox + cy + oy), 8 * (cx + ox - cy - oy)
                    if abs(sy - ry) < 0.5 and abs(sx - rx) < ln / 2:
                        return [col[i] * 0.3 + (110, 150, 235)[i] * 0.7 for i in range(3)]
        return col


def face(st, d, H, c, tu, tv, r):
    """the side of the bank (earth) or the canal wall (stone), d pixels below the top; c = where along the edge (0-1 a tile)"""
    f = d / H; g = r.random()
    if st['face'] == 'earth':
        if d <= 1.5: return [k * (0.9 + 0.2 * g) for k in st['lip']]       # the sod's dark edge
        col = [k * (1 - 0.25 * f) * (1 + 0.22 * (g - 0.5)) * (0.8 if g < 0.06 else 1.0) for k in st['rock']]
        if r.random() < 0.05: col = [k * 0.7 + 30 for k in col]             # a pebble
        if f > 0.55:
            w = min(1.0, (f - 0.55) / 0.3)
            col = [col[i] + (st['wet'][i] - col[i]) * w for i in range(3)]
        return col
    # stone: courses 4 px high under a 2 px coping, two blocks a tile along the edge, every other course shifted half
    if d <= 2.0: return [k * (0.94 + 0.12 * g) for k in st['lip']]
    row = int((d - 2.0) // 4); q = (c % 1.0) * 2 + 0.5 * (row % 2)
    if (d - 2.0) % 4 < 0.8 or (q % 1.0) < 0.07: return [k * 0.42 for k in st['rock']]        # mortar
    blk = random.Random(1000 + row * 7 + int(q % 2)).random()                                  # each block its own shade
    col = [k * (1 - 0.22 * f) * (0.88 + 0.22 * blk) * (1 + 0.12 * (g - 0.5)) for k in st['rock']]
    if f > 0.7:
        w = min(1.0, (f - 0.7) / 0.22)
        low = st['weed'] if wave(tu, tv, (4.0, 1.1, 0.2, 5.5)) > 0.2 else st['wet']
        col = [col[i] + (low[i] - col[i]) * w for i in range(3)]
    return col


def tile(st, mask, pos, waters):
    land = {(0, 0): False}
    for bit, n in ((1, 'N'), (2, 'E'), (4, 'NE'), (8, 'NNE'), (16, 'NEE'), (32, 'NNEE')):
        land[NB[n]] = bool(mask & bit)
    H = st['wall']
    P = st['period']; r = random.Random(st['base'] + mask * P * P + pos[0] * P + pos[1])
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
    for y in range(17, 32):
        for x in range(32):
            if not wg.IN(x, y): continue
            u, v = wg.local(x, y)
            col = WATER.at(pos[0] + u, pos[1] + v, r)
            if mask == 0:
                px[x, y] = tuple(max(0, min(255, int(c))) for c in col) + (255,); continue
            d = 0.0; prev = (0, 0)
            while d < H + 12:
                d += 0.5
                tx, ty, tu, tv = screen_tile(x, y - d)
                if (tx, ty) == (0, 0): prev = (tx, ty); continue
                if land.get((tx, ty)):
                    if d < H and st['face'] != 'rock':
                        col = face(st, d, H, tu if prev[0] != tx + 1 else tv, tu, tv, r)
                    elif d < H:                                          # the cliff face
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
                        if st['face'] != 'rock': fo *= 0.45 if st['face'] == 'earth' else 0.3       # banks and canal: calm water
                        col = [col[i] + (st['foam'][i] - col[i]) * max(0.0, min(1.0, fo)) for i in range(3)]
                    break
                if (tx, ty) not in land: break
                prev = (tx, ty)
            px[x, y] = tuple(max(0, min(255, int(c))) for c in col) + (255,)
    return im


def main():
    a = sys.argv[1:]; client, style = a[0], a[1]; st = STYLES[style]; BASE = st['base']
    out = a[a.index('--out') + 1] if '--out' in a else wg.gfx_dir(client)
    os.makedirs(out, exist_ok=True)
    S = wg.Sprites(client); waters = [S.get(n) for n in GAME_WATER]
    P = st['period']
    global WATER; WATER = Water(waters, BASE, P, st['ripples'])
    for mask in range(64):
        for a_ in range(P):
            for b_ in range(P):
                tile(st, mask, (a_, b_), waters).save(os.path.join(out, '%d.png' % (BASE + mask * P * P + a_ * P + b_)))
    json.dump({'base': BASE, 'style': style, 'period': P, 'stride': P * P, 'count': 64 * P * P, 'water': GAME_WATER,
               'mask': 'N=1 E=2 NE=4 (x-2,y+1)=8 (x-1,y+2)=16 (x-2,y+2)=32; + P*(x%P) + (y%P)'},
              open(os.path.join(HERE, 'world_water_%s.json' % style), 'w'), indent=1)
    print(style, BASE, '-', BASE + 64 * P * P - 1, '->', out)


if __name__ == '__main__':
    main()
