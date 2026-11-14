#!/usr/bin/env python3
"""New ground tiles made from the game's own tiles: dirt paths and clear water, each with 4 variants and the
46 soft-edge grass tiles that blend grass into it (MyV2 world sprites, Nov 2026).

    world_ground.py <client folder> [--out <folder>] [--preview <png>]

Reads the source sprites from the client (gfx/NNNNN.png, then pnglib, then gx00, like the client), writes the new
sprites to <client>/gfx/NNNNN.png and the edge table to tools/sprites/world_ground.json (the MyV2 Editor reads it
to pick the right edge tile around painted ground).

Edge masks: which neighbours of a grass tile are the other ground. Bits: 1 = x+1, 2 = y+1, 4 = x-1, 8 = y-1 (the
four sides), 16 = x+1,y+1, 32 = x-1,y+1, 64 = x-1,y-1, 128 = x+1,y-1 (corners; a corner only counts when neither of
its two sides does, so 46 masks besides plain grass). Map x grows down-right on screen, y up-right.
"""
import colorsys, json, math, os, random, struct, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GRASS = [551, 552, 553, 554]
SETS = {   # name: first sprite, how it is made
    'path':       {'first': 35000, 'kind': 'earth', 'hsv': (0.083, 0.52, 0.56)},   # brown dirt path
    'dusty path': {'first': 35100, 'kind': 'earth', 'hsv': (0.09, 0.40, 0.66)},    # light dusty road
    'clear water': {'first': 35500, 'kind': 'water'},
    # desert sands (Nov 13; Cody: "I like those sands", all four)
    'pale sand':   {'first': 35200, 'kind': 'earth', 'hsv': (0.115, 0.38, 0.84), 'grain': 0.55},
    'golden sand': {'first': 35250, 'kind': 'earth', 'hsv': (0.11, 0.50, 0.80), 'grain': 0.6},
    'dune sand':   {'first': 35300, 'kind': 'earth', 'hsv': (0.112, 0.44, 0.82), 'grain': 0.45, 'ripples': 0.045},
    'red desert':  {'first': 35350, 'kind': 'earth', 'hsv': (0.075, 0.48, 0.74), 'grain': 0.6},
    # snow (Nov 14; Cody liked all three)
    'soft snow':   {'first': 35400, 'kind': 'earth', 'hsv': (0.60, 0.05, 0.93), 'grain': 0.35},
    'bluish snow': {'first': 35450, 'kind': 'earth', 'hsv': (0.58, 0.09, 0.90), 'grain': 0.45},
    'bright snow': {'first': 35600, 'kind': 'earth', 'hsv': (0.60, 0.03, 0.97), 'grain': 0.25},
}
SIDES = [(1, 0), (0, 1), (-1, 0), (0, -1)]
CORNERS = [(1, 1), (-1, 1), (-1, -1), (1, -1)]      # corner k lies between side k and side k+1


def canon(mask):
    m = mask & 15
    for k in range(4):
        if mask & (16 << k) and not (mask & (1 << k)) and not (mask & (1 << ((k + 1) % 4))):
            m |= 16 << k
    return m


def all_masks():
    return sorted({canon(m) for m in range(1, 256)} - {0})


def mask_of(neigh):
    """neigh(dx, dy) -> True if that neighbour is the other ground"""
    m = 0
    for k, (dx, dy) in enumerate(SIDES):
        if neigh(dx, dy):
            m |= 1 << k
    for k, (dx, dy) in enumerate(CORNERS):
        if neigh(dx, dy):
            m |= 16 << k
    return canon(m)


def gfx_dir(client):
    for d in ('GFX', 'gfx'):
        if os.path.isdir(os.path.join(client, d)):
            return os.path.join(client, d)
    return os.path.join(client, 'gfx')


class Sprites:
    def __init__(self, client):
        self.client = client
        self.gidx = open(os.path.join(client, 'gx00.idx'), 'rb').read()
        self.gdat = open(os.path.join(client, 'gx00.dat'), 'rb')
        self.pidx = open(os.path.join(client, 'pnglib.idx'), 'rb').read()
        self.pdat = open(os.path.join(client, 'pnglib.dat'), 'rb')

    def get(self, nr):
        loose = os.path.join(gfx_dir(self.client), '%05d.png' % nr)
        if os.path.exists(loose):
            return Image.open(loose).convert('RGBA')
        if nr * 4 + 4 <= len(self.pidx):
            off = struct.unpack_from('<i', self.pidx, nr * 4)[0]
            if off:
                self.pdat.seek(off)
                return Image.open(self.pdat).convert('RGBA')
        xs, ys, off = struct.unpack_from('<3i', self.gidx, nr * 12)
        self.gdat.seek(off)
        px = struct.unpack('<%dH' % (xs * ys), self.gdat.read(xs * ys * 2))
        img = Image.new('RGBA', (xs, ys))
        img.putdata([(0, 0, 0, 0) if v == 0xF81F else (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255) for v in px])
        return img


DIAM = Image.new('L', (32, 32), 0)
for _y in range(17, 32):
    _w = [4, 8, 12, 16, 20, 24, 28, 32, 28, 24, 20, 16, 12, 8, 4][_y - 17]
    for _x in range(16 - _w // 2, 16 + _w // 2):
        DIAM.putpixel((_x, _y), 255)
IN = lambda x, y: 0 <= x < 32 and 0 <= y < 32 and DIAM.getpixel((x, y))


def earth(grass, hsv, grain=0.95, ripples=0.0, seed=0):
    """the grass tile's own pixel grain, recoloured to earth (no clumps, no stones, nothing brighter than the grass);
    ripples: soft wind ripples across the tile (dune sand)"""
    h, s, v0 = hsv
    ph = random.Random(seed).random() * 6.28
    g = grass.load()
    vs = [colorsys.rgb_to_hsv(*[c / 255 for c in g[x, y][:3]])[2] for y in range(32) for x in range(32) if IN(x, y)]
    vm = sum(vs) / len(vs)
    t = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = t.load()
    for y in range(32):
        for x in range(32):
            if IN(x, y):
                v = colorsys.rgb_to_hsv(*[c / 255 for c in g[x, y][:3]])[2]
                rel = (v - vm) / vm * grain
                if ripples:
                    xl, yl = local(x, y)
                    rel += ripples * math.sin(xl * 6.28 * 3 + ph + 0.8 * math.sin(yl * 5 + ph))
                vv = max(0, min(1, v0 * (1 + rel)))
                r, gg, b = colorsys.hsv_to_rgb(h, s, vv)
                px[x, y] = (int(r * 255), int(gg * 255), int(b * 255), 255)
    return t


def water(src, seed):
    """the game's dark water, lighter and clearer, with a few light wave lines"""
    from PIL import ImageOps, ImageEnhance, ImageDraw
    g = ImageOps.autocontrast(ImageOps.grayscale(src.convert('RGB')), cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(0.45); g = ImageEnhance.Brightness(g).enhance(0.9)
    rgb = (92, 160, 222)
    t = ImageOps.colorize(g, tuple(int(c * 0.25) for c in rgb), rgb, mid=tuple(int(c * 0.62) for c in rgb)).convert('RGBA')
    d = ImageDraw.Draw(t); r = random.Random(300 + seed)
    for _ in range(3):
        y = r.randrange(19, 30); x = r.randrange(4, 22); l = r.randrange(4, 8)
        d.line([(x, y), (x + l, y)], fill=(200, 230, 255, 255))
    t.putalpha(DIAM)
    return t


def local(px, py):
    dx = (px + 0.5 - 16) / 16.0; dy = (py + 0.5 - 24.5) / 7.5
    return (dx + dy) / 2.0, (dx - dy) / 2.0      # toward map x+1, toward map y+1; each -0.5..0.5


def blend(base, other, mask, seed, width=0.32):
    """grass tile `base` with the other ground creeping in from the sides / corners in `mask` (dithered, noisy,
    fully the other ground right at a shared side, so it joins the plain tiles without a seam)"""
    r = random.Random(seed); out = base.copy(); po = out.load(); pt = other.load()
    ph = [r.random() * 6.28 for _ in range(3)]
    for py in range(17, 32):
        for px in range(32):
            if not IN(px, py):
                continue
            xl, yl = local(px, py); w = 0.0
            n = 0.06 * math.sin(px * 0.9 + ph[0]) + 0.05 * math.sin(py * 1.7 + ph[1]) + 0.04 * math.sin((px + py) * 0.6 + ph[2])
            side = lambda d: max(0.0, min(1.0, 1 - (d + n * min(1, d * 4)) / width))
            dist = [0.5 - xl, 0.5 - yl, xl + 0.5, yl + 0.5]
            for k in range(4):
                if mask & (1 << k):
                    w = max(w, side(dist[k]))
            for k, (cx, cy) in enumerate(CORNERS):
                if mask & (16 << k):
                    w = max(w, side(math.hypot(0.5 - cx * xl, 0.5 - cy * yl)))
            if w > 0 and (r.random() < w * w * 1.15 or w > 0.8):
                po[px, py] = pt[px, py]
    return out


def build(client):
    S = Sprites(client)
    grass = [S.get(n) for n in GRASS]
    masks = all_masks()
    table = {'grass': GRASS, 'masks': masks, 'sets': {}}
    out = {}
    for name, cfg in SETS.items():
        if cfg['kind'] == 'earth':
            plain = [earth(grass[k], cfg['hsv'], cfg.get('grain', 0.95), cfg.get('ripples', 0.0), seed=cfg['first'] + k) for k in range(4)]
        else:
            plain = [water(S.get(n), k) for k, n in enumerate((16933, 16957, 16958, 16959))]
        first = cfg['first']
        for k, t in enumerate(plain):
            out[first + k] = t
        edges = {}
        for i, m in enumerate(masks):
            nr = first + 4 + i
            out[nr] = blend(grass[i % 4], plain[(i // 4) % 4], m, seed=first + m)
            edges[m] = nr
        table['sets'][name] = {'plain': [first + k for k in range(4)], 'edges': {str(m): nr for m, nr in edges.items()}}
    return out, table


def preview(sprites, table, path):
    """a small map painted with the new grounds, edges picked as the editor will"""
    M = ["gggggggggggggggggg", "gggggggggggggwwwgg", "ggggggppgggggwwwwg", "ggggggppggggwwwwwg", "ggggggppggggwwwwgg",
         "ggggggppgggggwwggg", "ggggggppgggggggggg", "ggggggpppppppppppp", "ggggggpppppppppppp", "ggggggppgggggggggg",
         "gggdddppgggggggggg", "ggddddppgggggggggg", "gddddddpgggggggggg", "gdddddddgggggggggg", "ggdddgppgggggggggg",
         "ggggggppgggggggggg", "ggggggppgggggggggg", "ggggggppgggggggggg"]
    N = len(M); key = {'p': 'path', 'd': 'dusty path', 'w': 'clear water'}
    at = lambda x, y: M[x][y] if 0 <= x < N and 0 <= y < N else 'g'
    r = random.Random(7); img = Image.new('RGBA', (32 * N + 64, 16 * N + 80), (0, 0, 0, 255))
    for x, y in sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1])):
        t = at(x, y)
        if t != 'g':
            nr = r.choice(table['sets'][key[t]]['plain'])
        else:
            nr = r.choice(GRASS)
            for o in 'wpd':     # the first ground found around it gives the edge (as the editor does)
                m = mask_of(lambda dx, dy: at(x + dx, y + dy) == o)
                if m:
                    nr = int(table['sets'][key[o]]['edges'][str(m)]); break
        im = sprites.get(nr) if nr in sprites else Sprites_cache[nr]
        sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 24
        img.alpha_composite(im, (sx - 16, sy - 24))
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(path)


Sprites_cache = {}

if __name__ == '__main__':
    client = sys.argv[1]
    sprites, table = build(client)
    S = Sprites(client)
    for n in GRASS:
        Sprites_cache[n] = S.get(n)
    gfx = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else gfx_dir(client)
    os.makedirs(gfx, exist_ok=True)
    for nr, im in sorted(sprites.items()):
        im.save(os.path.join(gfx, '%05d.png' % nr))
    with open(os.path.join(HERE, 'world_ground.json'), 'w') as f:
        json.dump(table, f, indent=1)
    print('%d sprites written (%s); edge table: %s' % (len(sprites), ', '.join('%s %d-%d' % (k, v['first'], v['first'] + 4 + len(table['masks']) - 1) for k, v in SETS.items()),
                                                       os.path.join(HERE, 'world_ground.json')))
    if '--preview' in sys.argv:
        preview(sprites, table, sys.argv[sys.argv.index('--preview') + 1])
