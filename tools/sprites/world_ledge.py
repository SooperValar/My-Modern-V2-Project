#!/usr/bin/env python3
"""Lower ground under a ledge (Nov 19; Cody: "make walls work so it looks like a ledge is higher than one below it").
The chasm's trick with ground at the bottom: a LOWER tile is the game's own ground (picked at random, as the game's is)
seen below the ledge of the higher ground beside it. Where the higher ground lies behind it (map x-1, y+1: up the
screen) its earth face comes down onto the lower tile, with a shadow at the foot; where the higher ground lies in front
(x+1, y-1: down the screen) the lower tile gets a dark line along that edge, so the ledge reads from every side.

    world_ledge.py <client folder> <style> [--out <folder>]      style: grass | grass_cliff | grass_ramp

  mask = higher ground (anything that is not lower ground or a ramp, and not the black void) at (x-1,y)=1 (x,y+1)=2
  (x-1,y+1)=4 (x-2,y+1)=8 (x-1,y+2)=16 (x-2,y+2)=32 (x+1,y)=64 (x,y-1)=128; k = which of the game's 4 ground tiles.
  grass (a low ledge, 13 px): 48602 + 4*mask + k (48602-49625)
  grass_cliff (Cody: "a 2 square one", 26 px - as far as a tile can see up): mask 0 = 49626 + k, else 49629 + mask
    (one ground tile each, 49626-49884)
  The way up is a STEPS object (world_steps.py) on a lower tile, not a ground of its own.
Writes world_ledge_<style>.json beside this script."""
import json, math, os, random, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg
from world_chasm import screen_tile, NB

STYLES = {
    'grass': dict(base=48602, ground=(551, 552, 553, 554), wall=13.0, low=0.93,
                  sod=(46, 92, 30), earth=(122, 100, 72), dark=(70, 56, 40)),
    'grass_cliff': dict(base=49626, layout='cliff', ground=(551, 552, 553, 554), wall=26.0, low=0.88, shadow=4,
                        sod=(46, 92, 30), earth=(122, 100, 72), dark=(70, 56, 40), rock=(118, 114, 106)),
}


def tile(st, mask, k, grounds):
    hi = {(0, 0): False}
    for bit, n in ((1, 'N'), (2, 'E'), (4, 'NE'), (8, 'NNE'), (16, 'NEE'), (32, 'NNEE')):
        hi[NB[n]] = bool(mask & bit)
    H = st['wall']; r = random.Random(st['base'] + mask * 4 + k)
    src = grounds[k]; sp = src.load()
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
    for y in range(32):
        for x in range(32):
            if not wg.IN(x, y): continue
            base = sp[x, y]
            if not base[3]: continue
            col = [c * st['low'] for c in base[:3]]
            u, v = wg.local(x, y)
            # a higher ground in front (down the screen): a dark line along that edge
            edge = min(0.5 - u if mask & 64 else 9, v + 0.5 if mask & 128 else 9) * 22    # pixels from the edge
            if edge < 2.5:
                col = [c * (0.55 + 0.18 * edge) for c in col]
            d = 0.0
            while d < H + 8:
                d += 0.5
                tx, ty, tu, tv = screen_tile(x, y - d)
                if (tx, ty) == (0, 0): continue
                if hi.get((tx, ty)):
                    if 'steps' in st and (tx, ty) in ((-1, 0), (0, 1)):   # steps cut into the face right behind it
                        if d >= H: break
                        g = r.random()
                        n = st['steps']; q = (d / H) * n; band = q - int(q)
                        if band < 0.5: c0 = st['tread']                       # the tread: lit, walked on
                        elif band < 0.62: c0 = [k * 1.12 for k in st['tread']]  # the step's nose catches the light
                        else: c0 = st['riser']
                        col = [c0[i] * (1 - 0.15 * (d / H)) * (1 + 0.12 * (g - 0.5)) for i in range(3)]
                        side = 0.5 - abs(tv if (tx, ty) == (-1, 0) else tu)    # how far from the stair's sides
                        if side < 0.12:                                      # the cut walls at either side
                            col = [c * (0.5 + 3.5 * side) for c in col]
                        break
                    if d < H:
                        f = d / H; g = r.random()
                        if d <= 2.0:                                     # the turf hanging over the top
                            c0 = st['sod']; col = [c0[i] * (0.85 + 0.3 * g) for i in range(3)]
                        elif 'rock' in st and f > 0.3:                    # a tall cliff: earth over rock
                            w = min(1.0, (f - 0.3) / 0.15)
                            strata = 0.08 * math.sin(d * 1.2 + 0.4) + 0.05 * math.sin(d * 3.0 + 1.9)
                            rk = [st['rock'][i] * (1 + strata) for i in range(3)]
                            ea = st['earth']
                            col = [(ea[i] * (1 - w) + rk[i] * w) * (1 - 0.35 * f) * (1 + 0.24 * (g - 0.5)) for i in range(3)]
                            if g < 0.04: col = [c * 0.7 for c in col]
                            if f > 0.82: col = [col[i] + (st['dark'][i] - col[i]) * (f - 0.82) / 0.18 * 0.7 for i in range(3)]
                        else:
                            col = [st['earth'][i] * (1 - 0.35 * f) * (1 + 0.24 * (g - 0.5)) for i in range(3)]
                            if g < 0.05: col = [c * 0.65 for c in col]          # a stone in the earth
                            if f > 0.7: col = [col[i] + (st['dark'][i] - col[i]) * (f - 0.7) / 0.3 for i in range(3)]
                    else:                                                # the shadow at the foot
                        e = d - H; col = [c * (0.6 + 0.4 * min(1.0, e / st.get('shadow', 7))) for c in col]
                    break
                if (tx, ty) not in hi: break
            px[x, y] = tuple(max(0, min(255, int(c))) for c in col) + (255,)
    return im


def main():
    a = sys.argv[1:]; client, style = a[0], a[1]; st = STYLES[style]; BASE = st['base']
    out = a[a.index('--out') + 1] if '--out' in a else wg.gfx_dir(client)
    os.makedirs(out, exist_ok=True)
    S = wg.Sprites(client); grounds = [S.get(n) for n in st['ground']]
    lay = st.get('layout', 'ledge'); n = 0
    if lay == 'steps':
        for mask in range(64):
            tile(st, mask, mask % 4, grounds).save(os.path.join(out, '%d.png' % (BASE + mask))); n += 1
    elif lay == 'cliff':
        for mask in range(256):
            for k in (range(4) if mask == 0 else [mask % 4]):
                tile(st, mask, k, grounds).save(os.path.join(out, '%d.png' % (BASE + k if mask == 0 else BASE + 3 + mask))); n += 1
    else:
        for mask in range(256):
            for k in range(4):
                tile(st, mask, k, grounds).save(os.path.join(out, '%d.png' % (BASE + mask * 4 + k))); n += 1
    json.dump({'base': BASE, 'style': style, 'layout': lay, 'count': n, 'ground': st['ground'],
               'mask': 'higher at (x-1,y)=1 (x,y+1)=2 (x-1,y+1)=4 (x-2,y+1)=8 (x-1,y+2)=16 (x-2,y+2)=32 (x+1,y)=64 (x,y-1)=128; + k'},
              open(os.path.join(HERE, 'world_ledge_%s.json' % style), 'w'), indent=1)
    print(style, BASE, '-', BASE + n - 1, '->', out)


if __name__ == '__main__':
    main()
