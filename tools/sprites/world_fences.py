#!/usr/bin/env python3
"""New fence types for MyV2 (Nov 14, Cody: "a few different fence types"), on the game's own fence layout
(the red Wooden Fence 1172-1183): a 32x32 sprite, the fence on the tile's middle line; six pieces a type, each
followed by its hidden-walls copy (N+1, the same picture, as the game does for its fences):

    +0  along y (runs up-right on screen)      +2  along x (runs down-right)
    +4  corner: the -y and -x halves (left)    +6  corner: the +y and +x halves (right)
    +8  corner: the -x and +y halves (top)     +10 corner: the -y and +x halves (bottom)

Types, from 40100, 20 numbers each:
    40100 split-rail fence (weathered posts and two rails)   40120 wattle fence (woven sticks between stakes)
    40140 wrought iron fence (black bars with spear tips)    40160 low fieldstone wall (knee-high, dry stone)
    40180 log palisade (sharpened logs, man-high)            40200 hedge (trimmed, waist-high)
Drawn from a small 3D model in the game's projection, textured and lit from the upper left like the wagons.
Writes the PNGs and world_fences.json (the editor's WORLD_FENCES: [first, name, blocks, [the six pieces]]).

    world_fences.py <client folder> [--out <folder>] [--scene <png>]
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
FIRST = 40100
CX, CY = 16, 24                     # the tile's centre in the 32x32 sprite (its bottom corner is at 16,32)
SHAPES = [((0, -1), (0, 1)), ((-1, 0), (1, 0)), ((0, -1), (-1, 0)), ((0, 1), (1, 0)), ((-1, 0), (0, 1)), ((0, -1), (1, 0))]

def lerp3(p, t):
    d, m, l = p
    if t < 0.5: k = t / 0.5; return tuple(d[i] + (m[i] - d[i]) * k for i in range(3))
    k = (t - 0.5) / 0.5; return tuple(m[i] + (l[i] - m[i]) * k for i in range(3))


class C:
    def __init__(self, seed, h=32):
        self.H = h; self.im = Image.new('RGBA', (32, h), (0, 0, 0, 0)); self.px = self.im.load(); self.d = ImageDraw.Draw(self.im)
        self.rng = random.Random(seed); self.noise = [[self.rng.random() for _ in range(64)] for _ in range(64)]
        self.prims = []

    def P(self, x, y, z):
        return (CX + 16 * (x + y), CY + (self.H - 32) + 8 * (x - y) - z)

    def face(self, p0, pa, pb, pal, k, tex):
        s0, sa, sb = self.P(*p0), self.P(*pa), self.P(*pb)
        ax, ay = sa[0] - s0[0], sa[1] - s0[1]; bx, by = sb[0] - s0[0], sb[1] - s0[1]
        det = ax * by - ay * bx
        if abs(det) < 0.3: return
        la = math.dist(p0[:2], pa[:2]) * 22 + abs(pa[2] - p0[2]); lb = math.dist(p0[:2], pb[:2]) * 22 + abs(pb[2] - p0[2])
        xs = [s0[0], sa[0], sb[0], sa[0] + bx]; ys = [s0[1], sa[1], sb[1], sa[1] + by]
        for yy in range(int(min(ys)) - 1, int(math.ceil(max(ys))) + 1):
            for xx in range(int(min(xs)) - 1, int(math.ceil(max(xs))) + 1):
                if not (0 <= xx < 32 and 0 <= yy < self.H): continue
                dx, dy = xx + 0.5 - s0[0], yy + 0.5 - s0[1]
                a = (dx * by - dy * bx) / det; b = (ax * dy - ay * dx) / det
                if not (-0.02 <= a <= 1.02 and -0.02 <= b <= 1.02): continue
                t = tex(self, a * la, b * lb, xx, yy) * k
                self.px[xx, yy] = tuple(int(c) for c in lerp3(pal, max(0, min(1, t)))) + (255,)

    def box(self, x0, x1, y0, y1, z0, z1, pal, tex):
        """an axis box; the faces the viewer sees: -y (lit), +x (shade), top"""
        self.prims.append((max(x0, x1) - min(y0, y1), lambda: (
            self.face((x0, y0, z0), (x1, y0, z0), (x0, y0, z1), pal, 0.95, tex),
            self.face((x1, y0, z0), (x1, y1, z0), (x1, y0, z1), pal, 0.70, tex),
            self.face((x0, y0, z1), (x1, y0, z1), (x0, y1, z1), pal, 1.15, tex))))

    def spike(self, x, y, z, h, col):
        """a pointed top (2 px wide at its foot)"""
        self.prims.append((x - y + 0.001, lambda: self._spike(x, y, z, h, col)))

    def _spike(self, x, y, z, h, col):
        sx, sy = self.P(x, y, z)
        for i in range(int(h)):
            w = 1 if i < h - 1 else 0
            for xx in range(int(sx) - w, int(sx) + 1):
                if 0 <= xx < 32 and 0 <= int(sy) - i < self.H: self.px[xx, int(sy) - i] = col

    def draw(self):
        for _, f in sorted(self.prims, key=lambda p: p[0]): f()
        return self.im


# ---------------------------------------------------------------- textures (u along the face, v down/across it, in px)
def grain(c, u, v, xx, yy):
    n = c.noise[int(u) % 64][int(v * 2 + yy) % 64]
    return 0.48 + 0.16 * math.sin(v * 1.7 + n * 3) + 0.28 * (n - 0.5)

def stones(c, u, v, xx, yy):
    row = int(v // 3.5); off = (row % 2) * 2.5; col = int((u + off) // 5)
    seam = (v % 3.5) < 0.8 or ((u + off) % 5) < 0.8
    n = c.noise[(col * 7 + row * 3) % 64][(xx + yy) % 64]
    t = 0.5 + 0.25 * (c.noise[(col * 13) % 64][(row * 5) % 64] - 0.5) + 0.2 * (n - 0.5)
    return t - 0.35 if seam else t

def leaves(c, u, v, xx, yy):
    n = c.noise[(xx * 5 + yy * 3) % 64][(xx * 11 + yy * 7) % 64]
    return 0.42 + 0.45 * (n - 0.5) + 0.12 * math.sin(xx * 1.3 + yy * 0.9)

def iron(c, u, v, xx, yy):
    return 0.45 + 0.1 * (c.noise[xx % 64][yy % 64] - 0.5)

def woven(c, u, v, xx, yy):
    band = int(v // 2.5); s = math.sin(u * 0.9 + band * math.pi)
    n = c.noise[int(u) % 64][(yy * 3) % 64]
    t = 0.45 + 0.22 * s + 0.2 * (n - 0.5)
    return t - 0.3 if (v % 2.5) < 0.6 else t

WOOD = ((44, 30, 16), (96, 70, 40), (140, 108, 66))       # weathered wood
DARKWOOD = ((30, 18, 8), (72, 46, 22), (112, 78, 42))
WICKER = ((54, 40, 18), (110, 86, 46), (160, 130, 78))
IRONP = ((10, 10, 12), (36, 36, 40), (82, 82, 92))
STONEP = ((52, 50, 46), (112, 106, 96), (164, 158, 146))
HEDGE = ((12, 40, 8), (36, 98, 26), (92, 160, 58))


def half_points(d, s0, s1):
    """the box range of a half line from s0 to s1 (0 = centre, 0.5 = tile edge) in direction d, plus half width w"""
    return d


def fence(kind, shape, seed):
    tall = kind == 'palisade'
    c = C(seed, 48 if tall else 32)
    hs = shape
    def seg(d, s0, s1, w, z0, z1, pal, tex):
        dx, dy = d
        if dx:
            a, b = sorted((dx * s0, dx * s1)); c.box(a, b, -w, w, z0, z1, pal, tex)
        else:
            a, b = sorted((dy * s0, dy * s1)); c.box(-w, w, a, b, z0, z1, pal, tex)
    def at(d, s): return (d[0] * s, d[1] * s)
    if kind == 'rail':
        c.box(-0.06, 0.06, -0.06, 0.06, 0, 17, WOOD, grain)
        for d in hs:
            for z in (6, 12): seg(d, 0.06, 0.5, 0.03, z, z + 2, WOOD, grain)
    elif kind == 'wattle':
        for d in hs:
            seg(d, 0.0, 0.5, 0.04, 0, 13, WICKER, woven)
            x, y = at(d, 0.3); c.box(x - 0.03, x + 0.03, y - 0.03, y + 0.03, 0, 16, DARKWOOD, grain)
        c.box(-0.04, 0.04, -0.04, 0.04, 0, 16, DARKWOOD, grain)
    elif kind == 'iron':
        for d in hs:
            seg(d, 0.0, 0.5, 0.015, 3, 4, IRONP, iron); seg(d, 0.0, 0.5, 0.015, 14, 15, IRONP, iron)
            for k in range(1, 8):
                x, y = at(d, k / 16.0)
                c.box(x - 0.015, x + 0.015, y - 0.015, y + 0.015, 0, 17, IRONP, iron)
                c.spike(x, y, 17, 3, (40, 40, 46, 255))
        c.box(-0.035, 0.035, -0.035, 0.035, 0, 19, IRONP, iron); c.spike(0, 0, 19, 3, (70, 70, 80, 255))
    elif kind == 'stone':
        for d in hs: seg(d, 0.0, 0.5, 0.11, 0, 9, STONEP, stones)
        c.box(-0.11, 0.11, -0.11, 0.11, 0, 9, STONEP, stones)
    elif kind == 'palisade':
        r = random.Random(seed)
        for d in hs:
            for k in range(0, 5):
                s = k / 10.0 + 0.05
                x, y = at(d, s); h = 26 + r.randrange(-2, 3)
                c.box(x - 0.045, x + 0.045, y - 0.045, y + 0.045, 0, h, DARKWOOD, grain)
                c.spike(x + 0.02, y - 0.02, h, 4, (60, 38, 18, 255))
        c.box(-0.045, 0.045, -0.045, 0.045, 0, 27, DARKWOOD, grain); c.spike(0.02, -0.02, 27, 4, (60, 38, 18, 255))
    elif kind == 'hedge':
        for d in hs: seg(d, 0.0, 0.5, 0.13, 0, 15, HEDGE, leaves)
        c.box(-0.13, 0.13, -0.13, 0.13, 0, 15, HEDGE, leaves)
    return c.draw()


TYPES = [('rail', 'Split-Rail Fence', 1), ('wattle', 'Wattle Fence', 1), ('iron', 'Wrought Iron Fence', 1),
         ('stone', 'Low Fieldstone Wall', 1), ('palisade', 'Log Palisade', 3), ('hedge', 'Hedge', 1)]
PIECES = ['along y', 'along x', 'corner left', 'corner right', 'corner top', 'corner bottom']


def build():
    out, names = {}, []
    for t, (kind, name, blk) in enumerate(TYPES):
        first = FIRST + 20 * t
        for j, shape in enumerate(SHAPES):
            im = fence(kind, shape, first + j)
            out[first + 2 * j] = im; out[first + 2 * j + 1] = im
        names.append([first, name, blk, [first + 2 * j for j in range(6)]])
    return out, names


def scene(out, names, client, path):
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    g = load(1118); N = 30
    S = Image.new('RGBA', (32 * N + 64, 16 * N + 160), (0, 0, 0, 255))
    def scr(x, y): return 16 * (x + y) + 32, 8 * (x - y) + 8 * N + 100
    cells = {}
    for t, (first, name, blk, pcs) in enumerate(names):
        bx = 2 + (t % 3) * 9; by = 2 + (t // 3) * 12
        x0, x1, y0, y1 = bx, bx + 5, by, by + 7
        for x in range(x0 + 1, x1): cells[x, y0] = pcs[1]; cells[x, y1] = pcs[1]
        for y in range(y0 + 1, y1): cells[x0, y] = pcs[0]; cells[x1, y] = pcs[0]
        cells[x0, y0] = pcs[3]; cells[x1, y1] = pcs[2]; cells[x0, y1] = pcs[5]; cells[x1, y0] = pcs[4]
    order = sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0]))
    for x, y in order:
        sx, sy = scr(x, y); S.alpha_composite(g, (sx - 16, sy + 8 - g.height))
    man = load(5072 + 48)
    for x, y in order:
        if (x, y) in cells:
            im = out[cells[x, y]]; sx, sy = scr(x, y); S.alpha_composite(im, (sx - 16, sy + 8 - im.height))
        if (x, y) in ((5, 6), (14, 15)):
            sx, sy = scr(x, y); S.alpha_composite(man, (sx - man.width // 2, sy + 8 - man.height))
    S = S.resize((S.width * 2, S.height * 2), Image.NEAREST); S.convert('RGB').save(path)


if __name__ == '__main__':
    client = sys.argv[1]
    dst = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(client, 'GFX')
    sc = sys.argv[sys.argv.index('--scene') + 1] if '--scene' in sys.argv else None
    out, names = build()
    os.makedirs(dst, exist_ok=True)
    for n, im in out.items(): im.save(os.path.join(dst, '%05d.png' % n))
    json.dump(names, open(os.path.join(HERE, 'world_fences.json'), 'w'))
    print('%d sprites %d-%d' % (len(out), min(out), max(out)))
    if sc: scene(out, names, client, sc)
