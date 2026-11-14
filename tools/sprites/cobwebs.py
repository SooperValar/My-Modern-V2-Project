#!/usr/bin/env python3
"""Cobwebs for MyV2: cobwebbed + lightly dusty copies of the game's walls, doors and furniture, and loose webs to
place on their own. New numbers from 39000 (the "cobwebbed versions" block of the world sprite plan); the originals
are never changed.

    cobwebs.py <client folder or a folder with the sources as NNNNN.png> [--out <folder>] [--sheet <png>]

Writes cobwebs.json next to this script: [[new, source, name, kind], ...] for the editor.
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST = 39000

WEB = (214, 214, 208)          # thread colour on an empty background
WEB_ON = 0.5                  # how far a thread pulls an existing pixel toward WEB

# ---------------------------------------------------------------- what gets a cobwebbed copy
WALLS = [  # (sprite, name): 32x64 wall blocks
    (1200, 'Brick wall'), (1210, 'Dark stone wall'), (930, 'Dark stone wall II'), (400, 'Black stone wall'),
    (1156, 'Marble wall'), (556, 'Red brick wall'), (1214, 'Grey brick wall'),
    (1260, 'Dark red wall'), (16718, 'Green stone wall'),   # (1244 is a rug, not a wall)
    (36000, 'Sandstone wall'), (36010, 'White temple wall'), (36020, 'Red brick wall II'), (36030, 'Mossy stone wall'),
    (36040, 'Cracked stone wall'), (36050, 'Dark slate wall'), (36060, 'Timber-framed wall'), (36070, 'Fieldstone wall'),
]
DOORS = [  # (closed, open, name)
    (1216, 1217, 'Door I'), (1212, 1213, 'Door II'), (514, 516, 'Marble door'), (502, 504, 'White door'),
    (564, 566, 'Red door'), (568, 570, 'Red door II'), (1284, 1286, 'Earth door'), (980, 982, 'Iron gate door'),
    (972, 974, 'Iron gate door II'),
    (36500, 36501, 'Oak door I'), (36502, 36503, 'Oak door II'),
    (36510, 36511, 'Dark wood door I'), (36512, 36513, 'Dark wood door II'),
    (36520, 36521, 'Iron-bound door I'), (36522, 36523, 'Iron-bound door II'),
    (36530, 36531, 'Iron door I'), (36532, 36533, 'Iron door II'),
    (36540, 36541, 'Temple door I'), (36542, 36543, 'Temple door II'),
    (36550, 36551, 'Sandstone door I'), (36552, 36553, 'Sandstone door II'),
    (36560, 36561, 'Iron gate I'), (36562, 36563, 'Iron gate II'),
    (36570, 36571, 'Curtain I'), (36572, 36573, 'Curtain II'),
]
FURNITURE = [
    (220, 'Chest'), (221, 'Chest (open)'), (222, 'Chest II'), (223, 'Chest II (open)'),
    (16897, 'Bookshelf'), (16898, 'Bookshelf II'), (16908, 'Bookshelf III'), (16909, 'Bookshelf IV'),
    (16910, 'Bookshelf V'), (16911, 'Bookshelf VI'),
    (16895, 'Marble table'), (16907, 'Table with vase'), (16918, 'Table'), (16644, 'Red table'), (18293, 'Table with scroll'),
    (460, 'Candle'), (591, 'Red candle'), (592, 'Candle holder'), (1102, 'Golden candlestick'), (1162, 'Golden candle'),
    (1132, 'Purple candle'), (1198, 'Purple candle II'), (16422, 'Black candle'), (16428, 'Candle holder II'),
    (16900, 'Marble candlestick'),
]


# ---------------------------------------------------------------- drawing
def put(px, x, y, mask, W, H, keep=1.0, r=None):
    x, y = int(round(x)), int(round(y))
    if not (0 <= x < W and 0 <= y < H) or (mask is not None and not mask[x, y]):
        return
    if r and r.random() > keep:
        return
    c = px[x, y]
    if c[3]:
        lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
        to = WEB if lum < 165 else (128, 128, 124)       # on white stone a grey thread, or it can't be seen
        px[x, y] = tuple(int(c[i] + (to[i] - c[i]) * WEB_ON) for i in range(3)) + (255,)
    else:
        px[x, y] = WEB + (255,)


def line(px, a, b, mask, W, H, r, keep=0.92, sag=0.0):
    """a thread from a to b, sagging by `sag` (pixels, downward on screen) in the middle; a few pixels left out"""
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 1.4) + 1
    for i in range(n + 1):
        t = i / n
        x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t + sag * 4 * t * (1 - t)
        put(px, x, y, mask, W, H, keep, r)


def corner_web(px, mask, W, H, at, a0, a1, R, r, rings=3, spokes=5):
    """a web in a corner: spokes from `at` between angles a0..a1 (radians, screen y down), arcs between them"""
    angs = [a0 + (a1 - a0) * (k + r.uniform(-0.12, 0.12)) / (spokes - 1) for k in range(spokes)]
    lens = [R * r.uniform(0.75, 1.0) for _ in angs]
    pts = lambda f: [(at[0] + math.cos(a) * l * f, at[1] + math.sin(a) * l * f) for a, l in zip(angs, lens)]
    for p in pts(1.0):
        line(px, at, p, mask, W, H, r, keep=0.85)
    for k in range(1, rings + 1):                 # a few loose arcs, wide apart, the outer ones sagging most
        f = (k + 0.4) / (rings + 0.5) + r.uniform(-0.05, 0.05)
        ps = pts(f)
        for p, q in zip(ps, ps[1:]):
            line(px, p, q, mask, W, H, r, keep=0.75, sag=0.5 + f * 2.0)


def orb(px, mask, W, H, to_screen, r, spokes=9, rings=6, R=1.0):
    """a round orb web in a plane; to_screen(u, v) maps plane coords (-1..1) to the sprite"""
    angs = [2 * math.pi * k / spokes + r.uniform(-0.15, 0.15) for k in range(spokes)]
    for a in angs:
        line(px, to_screen(0, 0), to_screen(math.cos(a) * R, math.sin(a) * R), mask, W, H, r, keep=0.95)
    for k in range(1, rings + 1):
        f = R * k / (rings + 0.5)
        for a, b in zip(angs, angs[1:] + angs[:1]):
            line(px, to_screen(math.cos(a) * f, math.sin(a) * f), to_screen(math.cos(b) * f, math.sin(b) * f), mask, W, H, r, keep=0.85)


def dust(im, amount=0.22):
    """old and dusty: a bit greyer and duller"""
    im = im.copy(); px = im.load(); W, H = im.size
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            if c[3]:
                g = (c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11)
                px[x, y] = tuple(int((c[i] * (1 - amount) + g * amount) * 0.94 + 150 * 0.06) for i in range(3)) + (255,)
    return im


def opaque_mask(im):
    return {(x, y): 1 for y in range(im.size[1]) for x in range(im.size[0]) if im.getpixel((x, y))[3]}


class Mask:
    def __init__(self, s):
        self.s = s

    def __getitem__(self, k):
        return k in self.s


def hull_mask(im, grow=0):
    """the convex hull of the sprite (webs may span gaps between legs, from a candle to its plate...)"""
    pts = [(x, y) for (x, y) in opaque_mask(im)]
    pts = sorted(set(pts))
    if len(pts) < 3:
        return Mask(set(pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    hull = lo[:-1] + hi[:-1]
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).polygon(hull, fill=255, outline=255)
    mp = m.load()
    return Mask({(x, y) for y in range(im.size[1]) for x in range(im.size[0]) if mp[x, y]}), hull


# ---------------------------------------------------------------- the three kinds
def drape(px, mask, W, H, A, B, r, depth):
    """a web hanging from an edge between A and B: threads sagging deeper and deeper, a few spokes into the middle"""
    for k in range(1, 5):
        line(px, A, B, mask, W, H, r, keep=0.72, sag=depth * k / 4 + r.uniform(-0.5, 0.5))
    M = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2 + depth)
    for f in (0.3, 0.7):
        P = (A[0] + (B[0] - A[0]) * f, A[1] + (B[1] - A[1]) * f)
        line(px, P, (M[0] + (P[0] - M[0]) * 0.2, M[1]), mask, W, H, r, keep=0.85)


def wall_webbed(im, variant, seed):
    """32x64 wall block: cap diamond on top, lit left face (x 0-15), shaded right face (16-31). Webs hang from the
    middle of a face's top edge or sit on the middle of its bottom edge, never at the block's side edges, so walls
    side by side still join cleanly (Cody: a web in the corner looked wrong next to another wall)"""
    im = dust(im); px = im.load(); W, H = im.size; r = random.Random(seed)
    base = H - 64
    left = Mask({(x, y) for x in range(0, 16) for y in range(base + 13 + x // 2, H) if im.getpixel((x, y))[3]})
    right = Mask({(x, y) for x in range(16, 32) for y in range(base + 13 + (31 - x) // 2, H) if im.getpixel((x, y))[3]})
    top_l = lambda x: (x, base + 13 + x / 2.0)
    top_r = lambda x: (x, base + 13 + (31 - x) / 2.0)
    bot_l = lambda x: (x, H - 8 + x / 2.0)
    bot_r = lambda x: (x, H - 1 - (x - 16) / 2.0)

    def hang(face, edge, x0, x1):
        drape(px, face, W, H, edge(x0), edge(x1), r, r.uniform(6, 9))

    def floor_web(face, edge, xm):
        x, y = edge(xm); P = (x, y - r.uniform(7, 10))
        corner_web(px, face, W, H, P, math.pi * 0.2, math.pi * 0.8, 12, r, rings=2, spokes=5)

    if variant % 3 == 0:
        hang(left, top_l, r.randrange(2, 4), r.randrange(12, 15))
    elif variant % 3 == 1:
        hang(right, top_r, r.randrange(17, 20), r.randrange(27, 30)); floor_web(left, bot_l, r.randrange(6, 10))
    else:
        hang(left, top_l, r.randrange(2, 5), r.randrange(11, 14)); floor_web(right, bot_r, r.randrange(22, 26))
    return im


CANDLES = {460, 591, 592, 1102, 1162, 1132, 1198, 16422, 16428, 16900}


def foot_webbed(im, seed):
    """candles and candlesticks: dusty, a web at the foot, from the stem down to the plate (Cody)"""
    im = dust(im); px = im.load(); W, H = im.size; r = random.Random(seed)
    m, hull = hull_mask(im)
    ys = [y for x, y in hull]; ytop = min(ys); ybot = max(ys); h = ybot - ytop
    cx = sum(x for x, y in hull) / len(hull)
    for side in (-1, 1):
        P = (cx + side * 0.5, ybot - max(5, h * 0.3))
        a = math.pi / 2 - side * 0.75
        corner_web(px, m, W, H, P, a - 0.55, a + 0.55, max(6, h * 0.35), r, rings=2, spokes=4)
    return im


def object_webbed(im, seed, big=True):
    """doors and furniture: dusty, a web at one or both upper corners of the silhouette, spanning gaps inside it"""
    im = dust(im); px = im.load(); W, H = im.size; r = random.Random(seed)
    m, hull = hull_mask(im)
    ys = [y for x, y in hull]; ytop = min(ys); ybot = max(ys); band = ytop + (ybot - ytop) * 0.35
    top = [p for p in hull if p[1] <= band] or hull
    lft = min(top, key=lambda p: (p[0], p[1])); rgt = max(top, key=lambda p: (p[0], -p[1]))
    cx = sum(x for x, y in hull) / len(hull); cy = sum(y for x, y in hull) / len(hull)
    size = max(6, min(14, (ybot - ytop) * 0.45, (rgt[0] - lft[0] + 2) * 0.9))
    for at, use in ((lft, True), (rgt, big or r.random() < 0.5)):
        if not use:
            continue
        a = math.atan2(cy - at[1], cx - at[0])
        corner_web(px, m, W, H, at, a - 0.9, a + 0.9, size * r.uniform(0.95, 1.2), r, rings=2 if size < 9 else 3, spokes=4 if size < 9 else 5)
    return im


def loose_webs():
    """webs to place on their own (32x64 object sprites)"""
    out = []
    def blank():
        return Image.new('RGBA', (32, 64), (0, 0, 0, 0))
    # a web hanging in a vertical plane along the map's x (screen down-right) and along y (screen up-right)
    for k, (dx, dy) in enumerate(((16, 8), (16, -8))):
        im = blank(); px = im.load(); r = random.Random(500 + k)
        cx, cy = 16, 30
        ts = lambda u, v, dx=dx, dy=dy: (cx + u * dx * 0.9, cy + u * dy * 0.9 + v * 14)
        orb(px, None, 32, 64, ts, r, spokes=8, rings=4)
        for s in (-1, 1):   # anchor threads up to the sides and down to the ground
            line(px, ts(s * 0.9, -0.9), (cx + s * dx, cy + s * dy - 26), None, 32, 64, r)
            line(px, ts(s * 0.7, 0.9), (cx + s * dx * 0.6, 56 + s * dy * 0.6 * 0.5), None, 32, 64, r)
        out.append((im, 'Hanging web ↘' if k == 0 else 'Hanging web ↗'))
    # webs on the floor: an orb flat on the ground, and torn scraps
    for k in range(2):
        im = blank(); px = im.load(); r = random.Random(520 + k)
        ts = lambda u, v: (16 + 14 * (u + v) / 2 * 1.0, 56 + 7 * (u - v) / 2 * 1.0 - 8 * 0)
        if k == 0:
            orb(px, None, 32, 64, lambda u, v: (16 + 12 * (u + v) / 1.4, 52 + 6 * (u - v) / 1.4), r, spokes=8, rings=3)
            out.append((im, 'Web on the floor'))
        else:
            for _ in range(5):
                a = (r.uniform(4, 28), r.uniform(48, 60)); b = (a[0] + r.uniform(-8, 8), a[1] + r.uniform(-3, 3))
                line(px, a, b, None, 32, 64, r, keep=0.8, sag=r.uniform(-1, 1))
            out.append((im, 'Torn web scraps'))
    # a big web with a spider
    im = blank(); px = im.load(); r = random.Random(540)
    ts = lambda u, v: (16 + u * 13, 32 + v * 16)
    orb(px, None, 32, 64, ts, r, spokes=10, rings=5)
    line(px, ts(0, -1), (16, 4), None, 32, 64, r); line(px, ts(0, 1), (16, 58), None, 32, 64, r)
    sx, sy = 19, 35
    for (x, y) in ((sx, sy), (sx + 1, sy), (sx, sy + 1), (sx + 1, sy + 1), (sx, sy + 2), (sx + 1, sy + 2), (sx, sy - 1)):
        px[x, y] = (24, 20, 18, 255)
    for lx, ly in ((-2, -1), (-2, 1), (-2, 3), (3, -1), (3, 1), (3, 3), (-1, -2), (2, -2)):
        px[sx + lx, sy + ly] = (40, 34, 30, 255)
    out.append((im, 'Web with a spider'))
    return out


def build(get):
    out, names = {}, []
    n = FIRST
    for k, (s, name) in enumerate(WALLS):          # 39000+: walls, 3 web variants each
        src = get(s)
        vs = []
        for v in range(3):
            out[n] = wall_webbed(src, v, s * 7 + v); vs.append(n); n += 1
        names.append([vs[0], 'Cobwebbed ' + name, 'wall', vs, s])
    n = FIRST + 100                                   # 39100+: doors (closed, open)
    for c, o, name in DOORS:
        out[n] = object_webbed(get(c), c * 3); out[n + 1] = object_webbed(get(o), c * 3)   # same webs on both
        names.append([n, 'Cobwebbed ' + name, 'door', [n, n + 1], c]); n += 2
    n = FIRST + 200                                   # 39200+: furniture
    for s, name in FURNITURE:
        out[n] = foot_webbed(get(s), s * 5) if s in CANDLES else object_webbed(get(s), s * 5)
        names.append([n, 'Cobwebbed ' + name.lower() if name[0].islower() else 'Cobwebbed ' + name, 'furniture', [n], s]); n += 1
    n = FIRST + 300                                   # 39300+: loose webs
    for im, name in loose_webs():
        out[n] = im; names.append([n, name, 'web', [n], 0]); n += 1
    return out, names


if __name__ == '__main__':
    src = sys.argv[1]
    if os.path.exists(os.path.join(src, 'gx00.idx')):
        sys.path.insert(0, HERE); import world_ground as WG
        S = WG.Sprites(src); get = S.get; gfx = WG.gfx_dir(src)
    else:
        get = lambda n: Image.open(os.path.join(src, '%05d.png' % n)).convert('RGBA'); gfx = src
    sprites, names = build(get)
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else gfx
    os.makedirs(out, exist_ok=True)
    for nr, im in sprites.items():
        im.save(os.path.join(out, '%05d.png' % nr))
    with open(os.path.join(HERE, 'cobwebs.json'), 'w') as f:
        json.dump(names, f)
    print('%d cobweb sprites written: walls 39000-%d, doors 39100-, furniture 39200-, loose webs 39300-' % (len(sprites), FIRST + 3 * len(WALLS) - 1))
    if '--sheet' in sys.argv:
        items = [(e[4], e[3]) for e in names]
        per = 8; CW, CH = 150, 110
        sh = Image.new('RGBA', (per * CW, ((len(items) + per - 1) // per) * CH), (40, 90, 40, 255)); d = ImageDraw.Draw(sh)
        for i, (s, vs) in enumerate(items):
            x = (i % per) * CW; y = (i // per) * CH
            row = ([get(s)] if s else []) + [sprites[v] for v in vs]
            cx = x + 2
            for im in row:
                sh.alpha_composite(im, (cx, y + CH - im.size[1] - 2)); cx += im.size[0] + 2
            d.text((x + 2, y + 1), str(vs[0]), fill=(255, 230, 120, 255))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
