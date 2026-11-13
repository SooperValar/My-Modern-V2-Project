#!/usr/bin/env python3
"""New floor tiles for MyV2 (32x32, the game's diamond: 32 wide, 15 high at the bottom), each in 4 variants, clean and
with grain like the new walls; numbered from 37000 (the "floors" block of the world sprite plan in HANDOFF.md):
material m is 37000 + 10*m, clean variants +0..+3, with grain +4..+7.

    world_floors.py <client folder> [--out <folder>] [--sheet <png>] [--scene <png>]

Patterns run along the map's axes (tile space: u toward map x+1, v toward map y+1, 0..16 a tile), so planks and tile
joints continue from one tile to the next.
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_ground as WG
from world_walls import Noise, mix

FIRST = 37000
GRAIN = 0.14
T = 16.0      # texels across a tile


def tile_uv(px, py):
    xl, yl = WG.local(px, py)          # -0.5..0.5 each
    return (xl + 0.5) * T, (yl + 0.5) * T


# ---------------------------------------------------------------- materials: (u, v, noise, variant) -> rgb
def planks(u, v, n, r, base, count=4):
    w = T / count; k = int(v // w); vv = v % w
    joint_at = r['joints'][k % len(r['joints'])]
    seam = vv < 0.7 or abs(u - joint_at) < 0.45
    tone = r['tone'][k % len(r['tone'])]
    grain = 0.9 + 0.2 * n.v(u * 0.35 + k * 9.1, vv * 3.0 + k)          # long grain along the plank
    c = tuple(x * (1 + tone) * grain for x in base)
    if seam:
        c = tuple(x * 0.55 for x in base)
    return c


def m_oak(u, v, n, r):
    return planks(u, v, n, r, (176, 128, 80))


def m_darkwood(u, v, n, r):
    return planks(u, v, n, r, (102, 66, 42))


def m_flagstone(u, v, n, r):
    best = d1 = d2 = 99; bi = 0
    for i, (qx, qy) in enumerate(r['pts']):     # the points repeat every tile, so the stones join up
        for ox in (-T, 0, T):
            for oy in (-T, 0, T):
                d = math.hypot(u - qx - ox, v - qy - oy)
                if d < d1:
                    d2, d1, bi = d1, d, i
                elif d < d2:
                    d2 = d
    if d2 - d1 < 0.8:
        return (70, 66, 60)
    base = r['cols'][bi]
    return tuple(x * (0.9 + 0.15 * n.f(u * 0.6, v * 0.6)) for x in base)


def m_checker(u, v, n, r):
    a = int(u // (T / 2)) + int(v // (T / 2))
    joint = (u % (T / 2)) < 0.5 or (v % (T / 2)) < 0.5
    base = (226, 222, 212) if a % 2 == 0 else (46, 46, 52)
    vein = n.f(u * 0.4 + r['mx'], v * 0.4 + r['my'], 4)
    c = tuple(x * (0.94 + 0.12 * vein) for x in base)
    if joint:
        c = (120, 118, 112)
    return c


def m_terracotta(u, v, n, r):
    joint = (u % (T / 2)) < 0.6 or (v % (T / 2)) < 0.6
    k = int(u // (T / 2)) * 2 + int(v // (T / 2))
    base = (186, 98, 62)
    c = tuple(x * (0.92 + r['tone'][k % len(r['tone'])] + 0.1 * n.f(u * 0.5, v * 0.5)) for x in base)
    if joint:
        c = (196, 184, 160)
    return c


def m_marble(u, v, n, r):
    base = (232, 230, 224)
    t = n.f(u * 0.18 + r['mx'], v * 0.18 + r['my'], 4)
    vein = abs(math.sin((u * 0.35 + v * 0.22 + t * 6) * 1.3))
    c = tuple(x * (0.95 + 0.06 * t) for x in base)
    if vein < 0.12:
        c = mix(c, (140, 140, 148), 0.6 * (1 - vein / 0.12))
    if (u % T) < 0.4 or (v % T) < 0.4:        # one slab a tile, a fine joint
        c = tuple(x * 0.82 for x in c)
    return c


def m_carpet(u, v, n, r):
    base = (148, 34, 40)
    c = tuple(x * (0.9 + 0.14 * n.f(u * 0.9, v * 0.9)) for x in base)
    # a small repeating diamond motif in gold, one per tile
    du, dv = abs(u - T / 2), abs(v - T / 2)
    if 3.2 < du + dv < 4.4:
        c = (196, 156, 72)
    elif du + dv < 1.2:
        c = (196, 156, 72)
    return c


def m_cobble(u, v, n, r):
    """small square setts in rows (a dungeon / old street floor)"""
    w = T / 4; row = int(v // w); uu = u + (w / 2 if row % 2 else 0)
    joint = (v % w) < 0.7 or (uu % w) < 0.7
    k = (int(uu // w) * 7 + row * 3) % len(r['tone'])
    base = (118, 114, 108)
    c = tuple(x * (0.88 + r['tone'][k] * 1.5 + 0.14 * n.f(u * 0.8, v * 0.8)) for x in base)
    if joint:
        c = (58, 56, 52)
    return c


MATERIALS = [
    ('Oak Planks', m_oak), ('Dark Wood Planks', m_darkwood), ('Flagstone', m_flagstone), ('Checkered Marble', m_checker),
    ('Terracotta Tiles', m_terracotta), ('White Marble', m_marble), ('Stone Setts', m_cobble),   # (red carpet: dropped, Cody Nov 13)
]


def variant(name, k):
    r = random.Random(sum(map(ord, name)) * 13 + k * 97)
    d = {'joints': [r.uniform(1, 15) for _ in range(8)], 'tone': [r.uniform(-0.07, 0.07) for _ in range(16)],
         'mx': r.random() * 40, 'my': r.random() * 40,
         'pts': [(r.uniform(0, T), r.uniform(0, T)) for _ in range(5)]}
    d['cols'] = []
    for _ in range(5):
        f = r.uniform(0.85, 1.12); d['cols'].append(tuple(x * f for x in r.choice([(150, 144, 132), (136, 132, 124), (160, 152, 136)])))
    return d


def make_floor(func, n, r, grain):
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load(); gr = random.Random(int(r['mx'] * 1000))
    for py in range(32):
        for px_ in range(32):
            if not WG.IN(px_, py):
                continue
            u, v = tile_uv(px_, py)
            c = func(u, v, n, r)
            if grain:
                g = 1 + grain * ((gr.random() - 0.5) * 1.2 + (n.v(px_ * 0.9 + 40, py * 0.9) - 0.5) * 0.8)
                c = tuple(a * g for a in c)
            px[px_, py] = tuple(max(0, min(255, int(a))) for a in c[:3]) + (255,)
    return im


def build():
    out, names = {}, []
    for m, (name, func) in enumerate(MATERIALS):
        first = FIRST + m * 10
        for k in range(4):
            r = variant(name, k)
            out[first + k] = make_floor(func, Noise(first * 5 + k), r, 0)
            out[first + 4 + k] = make_floor(func, Noise(first * 5 + k), r, GRAIN)
        names.append([first, name, [first + k for k in range(4)]])
        names.append([first + 4, name + ' (grain)', [first + 4 + k for k in range(4)]])
    return out, names


def scene(floors, names, client, path, grained):
    """a room of each floor, walled with the new walls (if they are in the client)"""
    S = WG.Sprites(client); grass = [S.get(n) for n in WG.GRASS]
    try:
        wall = [S.get(36024 + k) for k in range(4)]
    except Exception:
        wall = [S.get(1200)]
    N = 26; r = random.Random(4); W = {}
    sets = [nm for nm in names if ('(grain)' in nm[1]) == grained]
    for m, (first, name, vs) in enumerate(sets):
        bx = 1 + (m % 4) * 6; by = 1 + (m // 4) * 12
        for x in range(bx, bx + 5):
            for y in range(by, by + 7):
                W[x, y] = ('w', 0) if (x == bx or y == by + 6) else ('f', vs)      # walls on two sides only, to see in
    img = Image.new('RGBA', (32 * N + 64, 16 * N + 120), (0, 0, 0, 255))
    order = sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1]))
    for x, y in order:
        sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 70
        k, vs = W.get((x, y), ('g', 0))
        img.alpha_composite(floors[r.choice(vs)] if k == 'f' else r.choice(grass), (sx - 16, sy - 24))
    for x, y in order:
        k, vs = W.get((x, y), ('g', 0))
        if k == 'w':
            sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 70
            img.alpha_composite(r.choice(wall), (sx - 16, sy - 56))
    img.save(path)


if __name__ == '__main__':
    client = sys.argv[1]
    floors, names = build()
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else WG.gfx_dir(client)
    os.makedirs(out, exist_ok=True)
    for nr, im in floors.items():
        im.save(os.path.join(out, '%05d.png' % nr))
    with open(os.path.join(HERE, 'world_floors.json'), 'w') as f:      # the editor's floor sets
        json.dump(names, f)
    print('%d floors written: %s' % (len(floors), ', '.join('%s %d-%d' % (n, f, f + 3) for f, n, v in names)))
    if '--sheet' in sys.argv:
        sh = Image.new('RGBA', (8 * 72 + 190, len(MATERIALS) * 60 + 20), (30, 30, 30, 255)); d = ImageDraw.Draw(sh)
        d.text((190, 2), 'clean', fill=(200, 200, 200, 255)); d.text((190 + 4 * 72, 2), 'grain', fill=(200, 200, 200, 255))
        for i, (name, func) in enumerate(MATERIALS):
            first = FIRST + i * 10
            d.text((8, 20 + i * 60 + 26), name, fill=(255, 220, 120, 255))
            for k in range(8):
                sh.alpha_composite(floors[first + k].resize((64, 64), Image.NEAREST), (190 + k * 72, 20 + i * 60 - 30))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
    if '--scene' in sys.argv:
        p = sys.argv[sys.argv.index('--scene') + 1]
        scene(floors, names, client, p, False)
        scene(floors, names, client, p.replace('.png', '_grain.png'), True)
