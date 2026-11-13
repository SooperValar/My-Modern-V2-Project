#!/usr/bin/env python3
"""New wall materials for MyV2, on the game's own wall block (32x64: a cap on top, the left face lit, the right face
in shade, like the Red / Grey Brick walls 1200 / 1214). Each material comes in 4 variants (the editor paints them at
random), numbered from 36000 (the "walls / brick / stone" block of the world sprite plan in HANDOFF.md).

    world_walls.py <client folder> [--out <folder>] [--sheet <png>] [--scene <png>]
"""
import math, os, random, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_ground as WG

FIRST = 36000
SHAPE = 1200          # the game's wall block whose outline and cap are used


# ---------------------------------------------------------------- the block: which pixel is cap / left face / right face
def geometry(block):
    """per pixel: ('cap', 0, 0) / ('L', u, v) / ('R', u, v) / None. u: 0..15 across the face, v: 0..~44 down it"""
    px = block.load(); cap = px[16, 8][:3]
    g = {}
    for y in range(64):
        for x in range(32):
            if px[x, y][3] == 0:
                continue
            if y <= 21 and all(abs(a - b) < 12 for a, b in zip(px[x, y][:3], cap)):
                g[x, y] = ('cap', 0, 0)
            elif x < 16:
                g[x, y] = ('L', x, y - 12 - x / 2.0)
            else:
                g[x, y] = ('R', x - 16, y - 20 + (x - 16) / 2.0)
    return g, cap


# ---------------------------------------------------------------- noise
class Noise:
    def __init__(self, seed):
        r = random.Random(seed); self.t = [r.random() for _ in range(4096)]

    def v(self, x, y):
        xi, yi = int(math.floor(x)), int(math.floor(y)); xf, yf = x - xi, y - yi
        h = lambda a, b: self.t[(a * 73 + b * 151) & 4095]
        s = lambda t: t * t * (3 - 2 * t)
        a, b, c, d = h(xi, yi), h(xi + 1, yi), h(xi, yi + 1), h(xi + 1, yi + 1)
        return (a + (b - a) * s(xf)) + ((c + (d - c) * s(xf)) - (a + (b - a) * s(xf))) * s(yf)

    def f(self, x, y, oct=3):
        return sum(self.v(x * 2 ** o, y * 2 ** o) / 2 ** o for o in range(oct)) / (2 - 2 ** (1 - oct))


def mix(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


# ---------------------------------------------------------------- materials: (u, v, face, variant noise/rng) -> rgb
def blocks(u, v, face, n, w, h, rowoff):
    """which stone block (bx, by) a face pixel is in, and whether it is on a joint"""
    row = int(v // h); off = (row % 2) * (w // 2) + rowoff
    uu = u + off + (16 if face == 'R' else 0)       # the two faces continue each other's courses
    col = int(uu // w)
    joint = (v % h) < 1 or (uu % w) < 1
    return col, row, joint


def m_sandstone(u, v, face, n, r):
    col, row, joint = blocks(u, v, face, n, 8, 7, r['off'])
    base = (196, 160, 112)
    t = 0.85 + 0.25 * n.f(u * 0.5 + col * 3.1, v * 0.35 + row * 1.7) + r['tone'].get((col, row), 0)
    c = tuple(x * t for x in base)
    if joint:
        c = tuple(x * 0.68 for x in base)
    return c


def m_temple(u, v, face, n, r):
    col, row, joint = blocks(u, v, face, n, 16, 11, r['off'])
    base = (232, 228, 214)
    t = 0.93 + 0.1 * n.f(u * 0.3, v * 0.3) + r['tone'].get((col, row), 0) * 0.4
    c = tuple(x * t for x in base)
    if joint:
        c = tuple(x * 0.78 for x in base)
    return c


def m_brick(u, v, face, n, r):
    col, row, joint = blocks(u, v, face, n, 6, 4, r['off'])
    base = (158, 66, 48)
    k = r['tone'].get((col, row), 0)
    t = 0.86 + 0.2 * n.f(u * 0.8, v * 0.8) + k
    c = tuple(x * t for x in base)
    if (col * 7 + row * 3) % 11 == 0:
        c = mix(c, (110, 50, 40), 0.5)      # a few darker bricks
    if joint:
        c = (176, 166, 150)
    return c


def m_mossy(u, v, face, n, r):
    col, row, joint = blocks(u, v, face, n, 8, 7, r['off'])
    base = (132, 132, 124)
    t = 0.82 + 0.28 * n.f(u * 0.5 + col, v * 0.4 + row) + r['tone'].get((col, row), 0)
    c = tuple(x * t for x in base)
    if joint:
        c = tuple(x * 0.62 for x in base)
    moss = n.f(u * 0.22 + r['mx'], v * 0.16 + r['my'], 4) + (v / 44.0) * 0.45 - 0.62     # more moss low down
    if moss > 0:
        c = mix(c, (64, 104, 44) if n.v(u * 1.3, v * 1.3) > 0.4 else (84, 124, 52), min(1, moss * 4))
    return c


def m_cracked(u, v, face, n, r):
    col, row, joint = blocks(u, v, face, n, 8, 7, r['off'])
    base = (150, 146, 138)
    t = 0.84 + 0.26 * n.f(u * 0.5, v * 0.4) + r['tone'].get((col, row), 0)
    c = tuple(x * t for x in base)
    if joint:
        c = tuple(x * 0.64 for x in base)
    if (face, int(u), int(v)) in r['cracks']:
        c = tuple(x * 0.42 for x in base)
    return c


def m_slate(u, v, face, n, r):
    layer = int((v + r['off']) // 3)
    base = (70, 76, 88)
    t = 0.82 + 0.3 * n.v(layer * 2.3, (u + (16 if face == 'R' else 0)) * 0.15 + layer) + 0.1 * n.f(u * 0.7, v * 0.7)
    c = tuple(x * t for x in base)
    if (v + r['off']) % 3 < 0.8:
        c = tuple(x * 0.6 for x in base)
    return c


def m_timber(u, v, face, n, r):
    plaster = (222, 210, 182); wood = (78, 52, 34)
    t = 0.92 + 0.12 * n.f(u * 0.4, v * 0.4)
    c = tuple(x * t for x in plaster)
    beam = u < 2 or v < 2 or v > 41 or abs(v - 21) < 1.5
    if r['brace'] and 2 < v < 20:      # a diagonal brace in the upper half
        beam = beam or abs(v - 2 - (u * 18 / 15.0 if face == 'L' else (15 - u) * 18 / 15.0)) < 1.4
    if beam:
        c = tuple(x * (0.9 + 0.2 * n.v(u * 2, v * 0.5)) for x in wood)
    return c


def m_fieldstone(u, v, face, n, r):
    """rounded irregular stones (nearest of jittered points), dark mortar between them"""
    uu = u + (16 if face == 'R' else 0)
    best = d1 = d2 = 99; bi = 0
    for i, (px, py) in enumerate(r['pts']):
        d = math.hypot((uu - px), (v - py) * 1.2)
        if d < d1:
            d2, d1, bi = d1, d, i
        elif d < d2:
            d2 = d
    base = r['cols'][bi]
    if d2 - d1 < 1.1:
        return (62, 58, 52)
    t = 0.8 + 0.35 * (1 - min(1, d1 / 5.0)) + 0.1 * n.f(u, v)
    return tuple(x * t for x in base)


MATERIALS = [   # name, function, cap tint (None = the game's grey cap)
    ('Sandstone Wall', m_sandstone, (160, 132, 96)),
    ('White Temple Wall', m_temple, (196, 192, 182)),
    ('Red Brick Wall', m_brick, (110, 74, 66)),
    ('Mossy Stone Wall', m_mossy, None),
    ('Cracked Stone Wall', m_cracked, None),
    ('Dark Slate Wall', m_slate, (54, 58, 66)),
    ('Timber-Framed Wall', m_timber, (90, 64, 44)),
    ('Fieldstone Wall', m_fieldstone, None),
]


def variant_rng(mat, k):
    r = random.Random(sum(map(ord, mat)) * 7 + k * 101)
    d = {'off': r.randrange(0, 8), 'tone': {}, 'mx': r.random() * 50, 'my': r.random() * 50, 'brace': k % 2 == 0}
    for c in range(-2, 12):
        for rw in range(-2, 16):
            d['tone'][c, rw] = r.uniform(-0.08, 0.08)
    d['cracks'] = set()
    for _ in range(2 + k):          # crack lines: random walks down the face
        face = r.choice('LR'); u = r.randrange(2, 14); v = r.randrange(2, 30)
        for _ in range(r.randrange(8, 18)):
            d['cracks'].add((face, u, v)); v += 1; u = max(0, min(15, u + r.choice((-1, 0, 0, 1))))
    d['pts'] = [(r.uniform(-2, 34), r.uniform(-2, 47)) for _ in range(34)]
    d['cols'] = []
    for _ in range(34):          # one brightness per stone (all channels together, so the stones stay grey / brown)
        f = r.uniform(0.8, 1.15); d['cols'].append(tuple(x * f for x in r.choice([(150, 140, 124), (128, 122, 112), (160, 150, 130), (118, 112, 104)])))
    return d


GRAIN = 0.16        # per-pixel grain, like the game's own painted walls (0 = clean)


def make_wall(geo, capcol, func, captint, n, r, grain=None):
    grain = GRAIN if grain is None else grain
    gr = random.Random(r['off'] * 977 + len(r['cracks']))
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load()
    for (x, y), (part, u, v) in geo.items():
        if part == 'cap':
            c = captint or capcol
            if grain:
                g = 1 + grain * 0.5 * (gr.random() - 0.5)
                c = tuple(a * g for a in c)
        else:
            c = func(u, v, part, n, r)
            c = tuple(x * (1.0 if part == 'L' else 0.84) for x in c)     # the right face in shade, as the game's walls
            c = tuple(x * (1 - 0.1 * max(0, v - 36) / 8.0) for x in c)    # a touch darker at the foot
            if grain:      # the grain: every pixel a little lighter or darker, a bit clumped
                g = 1 + grain * ((gr.random() - 0.5) * 1.2 + (n.v(x * 0.9 + 40, y * 0.9) - 0.5) * 0.8)
                c = tuple(a * g for a in c)
        px[x, y] = tuple(max(0, min(255, int(a))) for a in c[:3]) + (255,)
    return im


def build(client):
    S = WG.Sprites(client)
    geo, capcol = geometry(S.get(SHAPE))
    out, names = {}, []
    for m, (name, func, captint) in enumerate(MATERIALS):
        first = FIRST + m * 10        # clean: first..first+3, with grain: first+4..first+7 (Cody wants both)
        for k in range(4):
            out[first + k] = make_wall(geo, capcol, func, captint, Noise(first * 7 + k), variant_rng(name, k), grain=0)
            out[first + 4 + k] = make_wall(geo, capcol, func, captint, Noise(first * 7 + k), variant_rng(name, k), grain=GRAIN)
        names.append([first, name, [first + k for k in range(4)]])
        names.append([first + 4, name + ' (grain)', [first + 4 + k for k in range(4)]])
    return out, names


def scene(walls, names, client, path):
    """a few little buildings, one per material, on grass"""
    S = WG.Sprites(client); grass = [S.get(n) for n in WG.GRASS]; floor = S.get(133)
    N = 26; r = random.Random(5)
    W = {}
    for m, (first, name, vs) in enumerate([nm for nm in names if '(grain)' in nm[1]]):
        bx = 2 + (m % 4) * 6; by = 2 + (m // 4) * 12
        for x in range(bx, bx + 5):
            for y in range(by, by + 6):
                edge = x in (bx, bx + 4) or y in (by, by + 5)
                door = (x == bx + 4 and y == by + 2)
                W[x, y] = ('w', first) if edge and not door else ('f', 0)
    img = Image.new('RGBA', (32 * N + 64, 16 * N + 120), (0, 0, 0, 255))
    for x, y in sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1])):
        sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 70
        k, first = W.get((x, y), ('g', 0))
        img.alpha_composite(floor if k == 'f' else r.choice(grass), (sx - 16, sy - 24))
    for x, y in sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1])):
        k, first = W.get((x, y), ('g', 0))
        if k == 'w':
            sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 70
            img.alpha_composite(walls[first + r.randrange(4)], (sx - 16, sy - 56))
    img.save(path)


if __name__ == '__main__':
    client = sys.argv[1]
    walls, names = build(client)
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else WG.gfx_dir(client)
    os.makedirs(out, exist_ok=True)
    for nr, im in walls.items():
        im.save(os.path.join(out, '%05d.png' % nr))
    print('%d walls written: %s' % (len(walls), ', '.join('%s %d-%d' % (n, f, f + 3) for f, n, v in names)))
    import json
    with open(os.path.join(HERE, 'world_walls.json'), 'w') as f:      # the editor's "New walls" (WORLD_WALLS)
        json.dump(names, f)
    if '--sheet' in sys.argv:
        sh = Image.new('RGBA', (4 * 104 + 230, len(names) * 200 + 10), (30, 30, 30, 255)); d = ImageDraw.Draw(sh)
        for i, (first, name, vs) in enumerate(names):
            d.text((8, i * 200 + 90), name, fill=(255, 220, 120, 255))
            for k in range(4):
                sh.alpha_composite(walls[first + k].resize((96, 192), Image.NEAREST), (230 + k * 104, i * 200 + 5))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
    if '--grain-sheet' in sys.argv:
        S = WG.Sprites(client); geo, capcol = geometry(S.get(SHAPE))
        levels = [('clean', 0.0), ('grain', GRAIN), ('strong grain', 0.28)]
        sh = Image.new('RGBA', (len(MATERIALS) * 104 + 130, len(levels) * 200 + 10), (30, 30, 30, 255)); d = ImageDraw.Draw(sh)
        for j, (lab, gv) in enumerate(levels):
            d.text((8, j * 200 + 90), lab, fill=(255, 220, 120, 255))
            for m, (name, func, captint) in enumerate(MATERIALS):
                first = FIRST + m * 10
                im = make_wall(geo, capcol, func, captint, Noise(first * 7), variant_rng(name, 0), grain=gv)
                sh.alpha_composite(im.resize((96, 192), Image.NEAREST), (130 + m * 104, j * 200 + 5))
        sh.save(sys.argv[sys.argv.index('--grain-sheet') + 1])
    if '--scene' in sys.argv:
        scene(walls, names, client, sys.argv[sys.argv.index('--scene') + 1])
