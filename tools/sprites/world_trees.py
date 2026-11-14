#!/usr/bin/env python3
"""New trees for MyV2 in the game's own style (soft speckled crowns lit from the upper left, thin trunks, a grass
tuft at the foot), 4 of each kind in mixed sizes (32x64, 32x96, 64x96), numbered from 38100 (the trees / plants
block of the world sprite plan; cacti are 38000-38006):

    38100-38103 autumn orange   38104-38107 autumn red    38108-38111 autumn yellow
    38120-38123 blossom         38130-38133 birch         38140-38143 willow
    38150-38153 pine            38154-38157 snowy pine    38160-38163 dead tree     38164-38167 stumps and logs

Leafy kinds (autumn, blossom, birch) are the game's own trees (1112 round, 1114 cone, 882 tall, 884 big) with
their leaves recoloured, so their shapes and speckle are the game's. Pines, willows, dead trees and stumps are drawn.

    world_trees.py <client folder or a folder with the game trees as NNNNN.png> [--out <folder>] [--sheet <png>] [--scene <png>]
"""
import colorsys, math, os, random, sys
from PIL import Image, ImageDraw

FIRST = 38100
SOURCES = [1112, 1114, 882, 884]            # round, cone, tall, big: the four variants of a recoloured kind
TRUNK = (139, 64, 0)


def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c[:3]) + (255,)


def crown_px(im):
    """(x, y) of the leaves: green pixels above the grass tuft at the foot"""
    W, H = im.size; p = im.load(); out = []
    for y in range(H - 8):
        for x in range(W):
            c = p[x, y]
            if c[3] and c[1] > c[0] + 8:
                out.append((x, y))
    return out


def recolor(im, palette, seed, mix=None, trunk=None):
    """leaves -> palette: keep each pixel's brightness (the game's shading and speckle) but take the hue from the
    palette; mix = [(palette, chance)] for speckles of other colours (autumn reds among oranges, green in blossom)"""
    im = im.copy(); p = im.load(); r = random.Random(seed)
    for x, y in crown_px(im):
        c = p[x, y]; v = c[1] / 140.0                      # the game's leaves: green 60..150
        pal = palette
        if mix:
            for alt, ch in mix:
                if r.random() < ch:
                    pal = alt
        p[x, y] = clamp(tuple(ch * (0.25 + 0.68 * v) for ch in pal))
    if trunk:
        W, H = im.size
        for y in range(H - 8):
            for x in range(W):
                c = p[x, y]
                if c[3] and c[0] > c[1] + 30:
                    p[x, y] = trunk(x, y, c)
    return im


# ---------------------------------------------------------------- drawn trees
def foliage(px, mask, W, H, ramp, seed, light=(0.3, 0.25)):
    """fill a crown mask with the game-like speckle: brightness from the upper left, darker toward the lower right and
    the edges, random per pixel; ragged edge pixels dropped"""
    r = random.Random(seed)
    xs = [x for x, y in mask]; ys = [y for x, y in mask]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys); ms = set(mask)
    for x, y in mask:
        edge = sum((x + dx, y + dy) not in ms for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge and r.random() < 0.35:
            continue
        u = (x - x0) / max(1, x1 - x0); v = (y - y0) / max(1, y1 - y0)
        b = 1.0 - 0.55 * math.hypot(u - light[0], v - light[1]) - 0.12 * edge + r.uniform(-0.22, 0.22)
        b = max(0, min(0.999, b))
        px[x, y] = clamp(ramp[int(b * len(ramp))])


def trunk_draw(px, cx, top, bottom, w, col, dark):
    for y in range(top, bottom + 1):
        for x in range(cx - w // 2, cx - w // 2 + w):
            px[x, y] = clamp(col if x < cx else dark)


def tuft(px, cx, H, r):
    for (dx, dy) in ((-3, -6), (-2, -6), (-1, -6), (0, -6), (1, -6), (2, -6), (-4, -5), (-3, -5), (-2, -5), (-1, -5), (0, -5),
                     (1, -5), (2, -5), (3, -5)):
        if r.random() < 0.85:
            px[cx + dx, H + dy] = clamp(r.choice([(0, 105, 16), (0, 121, 8), (0, 89, 0)]))


GREEN_DARK = [(8, 40, 24), (12, 52, 30), (16, 62, 36), (20, 74, 42), (26, 86, 48), (34, 98, 56), (44, 112, 64)]


def pine(seed, W, H, snowy=False, tiers=4):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); px = im.load(); r = random.Random(seed)
    cx = W // 2; foot = H - 7; ttop = foot - r.randrange(5, 8)
    trunk_draw(px, cx, ttop, foot, 3, (120, 70, 30), (84, 48, 20))
    top = r.randrange(4, 10) + (H - 64) // 3
    half = min(W // 2 - 2, 13 + (W - 32) // 4)
    span = ttop + 2 - top; th = span / tiers * 1.5
    masks = []
    for t in range(tiers):                     # tiers from the top: each a triangle, the lower ones wider
        ty0 = top + t * span / tiers; ty1 = ty0 + th; hw = half * (0.45 + 0.55 * (t + 1) / tiers)
        m = []
        for y in range(int(ty0), min(int(ty1), ttop + 2)):
            k = (y - ty0) / th
            w = hw * k + r.uniform(-0.8, 0.8)
            for x in range(int(cx - w), int(cx + w) + 1):
                if 0 <= x < W:
                    m.append((x, y))
        if snowy and m:                      # a soft, ragged lower edge (Cody): each column ends 0-2 pixels early or
            yb = max(y for x, y in m)        # hangs one pixel lower
            cut = {x: yb - r.choice((0, 0, 1, 1, 2)) for x, y in m}
            m = [(x, y) for x, y in m if y <= cut[x]]
            m += [(x, yb + 1) for x in set(cut) if cut[x] == yb and r.random() < 0.3 and abs(x - cx) < hw * 0.9]
        masks.append(m)
    for t, m in (reversed(list(enumerate(masks))) if snowy else enumerate(masks)):   # snowy: the bottom tier first, each tier above over the one below (Cody); plain: the top tier first (Cody liked it)
        if m:
            foliage(px, m, W, H, GREEN_DARK, seed * 10 + t)
            if snowy:                           # snow over most of each tier: thick on top, thinning toward the
                ys = [y for x, y in m]; y0 = min(ys); y1 = max(ys)      # tier's lower edge, shaded blue on the right
                xs = [x for x, y in m]; xl, xr = min(xs), max(xs)
                for x, y in m:
                    if not px[x, y][3]:
                        continue
                    v = (y - y0) / max(1, y1 - y0); u = (x - xl) / max(1, xr - xl)
                    if t == 0:                    # the top tier: white all over (Cody)
                        a = 1.0 + r.uniform(-0.12, 0.05)
                    else:                         # the tiers below: whitening from the bottom up (Cody)
                        a = 0.05 + 1.0 * v ** 1.1 + r.uniform(-0.2, 0.2)
                    if a > 0:
                        a = min(1.0, a)
                        sh = 1.0 - 0.22 * u - 0.12 * v + r.uniform(-0.03, 0.03)
                        snow = (232 * sh, 238 * sh, 246 * sh + 6 * u)
                        g = px[x, y]
                        px[x, y] = clamp(tuple(g[i] * (1 - a) + snow[i] * a for i in range(3)))
    tuft(px, cx, H, r) if not snowy else None
    return im


WILLOW = [(40, 80, 20), (52, 96, 26), (66, 112, 32), (82, 126, 40), (100, 140, 50), (118, 156, 62), (136, 170, 74)]


def willow(seed, W, H):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); px = im.load(); r = random.Random(seed)
    cx = W // 2; foot = H - 7
    trunk_draw(px, cx, foot - (H // 2), foot, 4 if W > 32 else 3, (122, 92, 60), (86, 62, 40))
    rx = W // 2 - 2; top = 4 + (H - 64) // 4; dome_h = int((foot - top) * 0.42)
    cy = top + dome_h
    m = set()
    for y in range(top, cy + 1):               # a rounded crown
        k = (cy - y) / dome_h; w = rx * math.sqrt(max(0, 1 - k * k))
        for x in range(int(cx - w), int(cx + w) + 1):
            m.add((x, y))
    # curtains of hanging twigs: they start inside the crown at uneven heights and the crown's underside thins out
    # into them over a few pixels (no hard line between cap and curtain); thin gaps show the trunk
    for sx in range(cx - rx, cx + rx + 1):
        k = abs(sx - cx) / rx
        start = cy - int(dome_h * 0.35 * r.random())
        for y in range(start, cy + 9):           # the fringe: denser near the crown
            if r.random() < 1.0 - (y - cy) / 10.0:
                m.add((sx, y))
        if (abs(sx - cx) <= 2 and r.random() < 0.6) or r.random() < 0.25:
            continue
        y1 = foot - 2 - r.randrange(0, 8) - int(10 * (1 - k) * r.random())
        for y in range(start, y1):
            m.add((sx + (1 if r.random() < 0.08 else 0), y))
    foliage(px, list(m), W, H, WILLOW, seed, light=(0.3, 0.1))
    tuft(px, cx, H, r)
    return im


def branch(d, x, y, ang, ln, w, depth, r, col):
    if depth == 0 or ln < 2:
        return
    x2 = x + math.cos(ang) * ln; y2 = y - math.sin(ang) * ln
    d.line([(x, y), (x2, y2)], fill=col, width=max(1, int(w)))
    for s in (-1, 1):
        if r.random() < 0.85:
            branch(d, x2, y2, ang + s * r.uniform(0.3, 0.7), ln * r.uniform(0.6, 0.78), w * 0.6, depth - 1, r, col)


def dead(seed, W, H):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = random.Random(seed)
    cx = W // 2; foot = H - 7
    col = (96, 84, 72, 255)
    for y in range(int(foot - H * 0.35), foot + 1):      # the trunk, wider at the foot
        w = (3 if W == 32 else 4) + (1 if y > foot - 6 else 0)
        d.line([(cx - w // 2, y), (cx - w // 2 + w - 1, y)], fill=col)
    branch(d, cx, foot - H * 0.35, math.pi / 2 + r.uniform(-0.15, 0.15), H * 0.22, 3 if W == 32 else 4, 6, r, col)
    for _ in range(3):
        branch(d, cx, foot - H * r.uniform(0.2, 0.34), math.pi / 2 + r.choice((-1, 1)) * r.uniform(0.5, 0.9), H * 0.15, 2, 4, r, col)
    px = im.load()                               # lit from the left: pixels with an empty neighbour to the right darker
    for y in range(H):
        for x in range(W):
            if px[x, y][3]:
                rt = x + 1 < W and px[x + 1, y][3]
                lf = x > 0 and px[x - 1, y][3]
                f = 1.18 if not lf else (0.72 if not rt else 0.95)
                f *= r.uniform(0.9, 1.08)
                px[x, y] = clamp(tuple(c * f for c in col))
    return im


def stump(seed, kind):
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load(); d = ImageDraw.Draw(im); r = random.Random(seed)
    bark, dark, wood, ring = (110, 76, 44), (72, 48, 26), (196, 160, 110), (150, 112, 70)
    if kind in ('stump', 'mossy', 'tall'):
        h = 7 if kind != 'tall' else 18; cx = 16; base = 57; rx, ry = 7, 3
        for y in range(base - h, base + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 <= 1:
                    u = (x - cx + rx) / (2 * rx)
                    px[x, y] = clamp(tuple(c * (1.2 - 0.6 * u) * r.uniform(0.88, 1.1) for c in bark))
        top = base - h
        if kind == 'tall':                    # a jagged broken top
            for x in range(cx - rx, cx + rx + 1):
                for y in range(top - r.randrange(0, 6), top):
                    if ((x - cx) / rx) ** 2 <= 1:
                        px[x, y] = clamp(tuple(c * r.uniform(0.8, 1.1) for c in bark))
        else:                                 # the cut face with rings
            for y in range(top - ry, top + ry + 1):
                for x in range(cx - rx, cx + rx + 1):
                    e = ((x - cx) / rx) ** 2 + ((y - top) / ry) ** 2
                    if e <= 1:
                        c = ring if 0.25 < e < 0.4 or e > 0.8 else wood
                        px[x, y] = clamp(tuple(v * r.uniform(0.92, 1.06) for v in c))
        if kind == 'mossy':
            for _ in range(40):
                x = r.randrange(cx - rx, cx + rx + 1); y = r.randrange(top - ry, base)
                if px[x, y][3]:
                    px[x, y] = clamp(r.choice([(70, 120, 40), (90, 140, 50), (56, 100, 34)]))
    else:                                      # a fallen log lying along the map's x (screen down-right)
        for t in range(-4, 5):
            for s in range(-10, 11):
                x = 16 + s + 0; y = 50 + s // 2 + t
                if 0 <= x < 32 and 0 <= y < 64 and abs(t) <= 4:
                    f = 1.15 - 0.08 * (t + 4)
                    px[x, y] = clamp(tuple(c * f * r.uniform(0.88, 1.1) for c in bark))
        for t in range(-4, 5):                 # the cut end facing the viewer
            for k in range(-2, 3):
                x = 26 + k; y = 55 + t
                if (k / 2.5) ** 2 + (t / 4.5) ** 2 <= 1:
                    px[x, y] = clamp(wood if abs(t) > 1 or abs(k) > 0 else ring)
    return im


def birch_trunk(x, y, c):
    r = random.Random(x * 131 + y * 7)
    if r.random() < 0.18:
        return clamp((40, 38, 36))
    return clamp((230, 228, 220) if r.random() < 0.6 else (196, 194, 188))


def build(get):
    src = [get(n) for n in SOURCES]
    out, names = {}, []
    ORANGE, RED, YELLOW = (226, 120, 30), (196, 50, 30), (222, 182, 40)
    kinds = [
        (38100, 'Autumn tree (orange)', lambda k: recolor(src[k], ORANGE, k, [(RED, 0.15), (YELLOW, 0.15)])),
        (38104, 'Autumn tree (red)', lambda k: recolor(src[k], RED, 10 + k, [(ORANGE, 0.2), ((140, 30, 30), 0.15)])),
        (38108, 'Autumn tree (yellow)', lambda k: recolor(src[k], YELLOW, 20 + k, [(ORANGE, 0.15), ((160, 170, 40), 0.12)])),
        (38120, 'Blossom tree', lambda k: recolor(src[k], (246, 160, 196), 30 + k, [((255, 236, 244), 0.3), ((90, 150, 50), 0.12)])),
        (38130, 'Birch', lambda k: recolor(src[k], (104, 168, 56), 40 + k, [((140, 186, 70), 0.2)], trunk=birch_trunk)),
        (38140, 'Willow', lambda k: willow(50 + k, *((32, 64), (32, 96), (64, 96), (64, 96))[k])),
        (38150, 'Pine', lambda k: pine(60 + k, *((32, 64), (32, 96), (32, 96), (64, 96))[k], tiers=(3, 4, 5, 5)[k])),
        (38154, 'Snowy pine', lambda k: pine(60 + k, *((32, 64), (32, 96), (32, 96), (64, 96))[k], snowy=True, tiers=(3, 4, 5, 5)[k])),
        (38160, 'Dead tree', lambda k: dead(70 + k, *((32, 64), (32, 96), (64, 96), (64, 96))[k])),
        (38164, 'Stump / log', lambda k: stump(80 + k, ('stump', 'mossy', 'tall', 'log')[k])),
    ]
    for first, name, make in kinds:
        for k in range(4):
            out[first + k] = make(k)
        names.append([first, name, [first + k for k in range(4)]])
    return out, names


def scene(trees, names, path, grass):
    N = 18; r = random.Random(3)
    img = Image.new('RGBA', (32 * N + 64, 16 * N + 160), (0, 0, 0, 255))
    order = sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1]))
    O = lambda x, y: (16 * (x + y) + 32, 8 * (x - y) + 8 * N + 120)
    for x, y in order:
        sx, sy = O(x, y); img.alpha_composite(r.choice(grass), (sx - 16, sy - 24))
    allt = [n for f, nm, vs in names for n in vs]
    spots = [(x, y) for x in range(1, N - 1, 2) for y in range(1, N - 1, 2)]
    pick = {s: allt[i % len(allt)] for i, s in enumerate(spots)}
    for x, y in order:
        if (x, y) in pick:
            sx, sy = O(x, y); im = trees[pick[(x, y)]]
            img.alpha_composite(im, (sx - im.size[0] // 2, sy + 8 - im.size[1]))
    img.save(path)


if __name__ == '__main__':
    src = sys.argv[1]
    if os.path.exists(os.path.join(src, 'gx00.idx')):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import world_ground as WG
        S = WG.Sprites(src); get = S.get; gfx = WG.gfx_dir(src)
    else:
        get = lambda n: Image.open(os.path.join(src, '%05d.png' % n)).convert('RGBA'); gfx = src
    trees, names = build(get)
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else gfx
    os.makedirs(out, exist_ok=True)
    for nr, im in trees.items():
        im.save(os.path.join(out, '%05d.png' % nr))
    print('%d trees written: %s' % (len(trees), ', '.join('%s %d-%d' % (n, f, f + 3) for f, n, v in names)))
    if '--sheet' in sys.argv:
        rows = len(names); sh = Image.new('RGBA', (4 * 74 + 170, rows * 104 + 10), (40, 90, 40, 255)); d = ImageDraw.Draw(sh)
        for i, (first, name, vs) in enumerate(names):
            d.text((6, 10 + i * 104 + 44), name, fill=(255, 230, 120, 255))
            for k, n in enumerate(vs):
                im = trees[n]; sh.alpha_composite(im, (170 + k * 74 + (64 - im.size[0]) // 2, 10 + i * 104 + 96 - im.size[1]))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
    if '--scene' in sys.argv:
        scene(trees, names, sys.argv[sys.argv.index('--scene') + 1], [get(n) for n in (551, 552, 553, 554)])
