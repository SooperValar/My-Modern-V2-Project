#!/usr/bin/env python3
"""Ash ground for the Ashen Fields (Nov 18; Cody: an ash canyon, "stick to the whole mountain top theme"): grey volcanic
ash with grit and charcoal flecks, dark cinders with glowing embers, and the soft edges on an ASH base, made like
world_snowgrass.py.

    world_ash.py <client folder> [--out <folder>] [--preview <png>]

  ash 37100-37103, cinders 37104-37107 (4 variants each)
Edges on an ASH base (46 each, in the order of world_ground.all_masks()):
  cinders 37108-37153, soft snow (35400) 37154-37199, snowy grass (36100) 37200-37245.
Edges on a CINDERS base: molten rock (the Foundry's molten iron 36300-36303) 37246-37291.   Next free: 37292
(36350-36399 is free too; 36400-36409 are the arches).
Writes tools/sprites/world_ash.json beside this script."""
import colorsys, json, math, os, random, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg

ASH, CINDERS = 37100, 37104
CIN_MOLTEN = 37246
ON_ASH = {'cinders': 37108, 'soft snow': 37154, 'snowy grass': 37200}


def specks(t, seed, n, cols):
    """small 1-2 pixel flecks (grit, charcoal, embers) scattered over the tile's diamond"""
    r = random.Random(seed); px = t.load()
    for _ in range(n):
        x, y = r.randrange(32), r.randrange(17, 32)
        if not wg.IN(x, y): continue
        c = r.choice(cols); px[x, y] = c + (255,)
        if r.random() < 0.25 and wg.IN(x, y + 1): px[x + 1, y] = tuple(int(v * 0.8) for v in c) + (255,)
    return t


def mottle(t, seed, amp, warm=0.0):
    """soft light and dark drifts across the tile (ash lies unevenly), seamless enough at this scale"""
    r = random.Random(seed + 3); px = t.load(); ph = [r.random() * 6.28 for _ in range(4)]
    for y in range(17, 32):
        for x in range(32):
            if not wg.IN(x, y): continue
            xl, yl = wg.local(x, y)
            n = math.sin(xl * 4 + ph[0]) * math.sin(yl * 3.5 + ph[1]) + 0.5 * math.sin((xl - yl) * 5 + ph[2]) + 0.3 * math.sin(xl * 11 + yl * 3 + ph[3])
            k = 1 + amp * n; c = px[x, y]
            px[x, y] = (min(255, int(c[0] * k + warm * n * 8)), min(255, int(c[1] * k)), min(255, int(c[2] * k - warm * n * 4)), 255)
    return t


def ash(grass, seed):
    t = mottle(wg.earth(grass, (0.07, 0.07, 0.46), grain=0.55, seed=seed), seed, 0.045, warm=0.5)
    return specks(t, seed, 18, [(62, 58, 55), (48, 45, 43), (160, 156, 150), (112, 104, 98), (86, 70, 60)])


def cinders(grass, seed):
    t = mottle(wg.earth(grass, (0.03, 0.15, 0.24), grain=0.8, seed=seed), seed, 0.18)
    r = random.Random(seed + 7); px = t.load()
    ph = [r.random() * 6.28 for _ in range(3)]
    for y in range(17, 32):                       # faint red glow in the cracks
        for x in range(32):
            if not wg.IN(x, y): continue
            xl, yl = wg.local(x, y)
            n = math.sin(xl * 13 + ph[0]) * math.sin(yl * 11 + ph[1]) + 0.5 * math.sin((xl + yl) * 21 + ph[2])
            if n > 0.95:
                c = px[x, y]; px[x, y] = (min(255, c[0] + 70), c[1] + 14, c[2], 255)
    return specks(t, seed, 14, [(255, 150, 40), (230, 90, 20), (255, 200, 90), (40, 34, 32)])


def build(client):
    S = wg.Sprites(client); grass = [S.get(n) for n in wg.GRASS]; masks = wg.all_masks(); out = {}
    plain_ash = [ash(grass[k], ASH + k) for k in range(4)]
    plain_cin = [cinders(grass[(k + 1) % 4], CINDERS + k) for k in range(4)]
    for k in range(4): out[ASH + k] = plain_ash[k]; out[CINDERS + k] = plain_cin[k]
    other = {'cinders': plain_cin, 'soft snow': [S.get(n) for n in (35400, 35401, 35402, 35403)],
             'snowy grass': [S.get(n) for n in (36100, 36101, 36102, 36103)]}
    table = {'masks': masks, 'plain': {'ash': [ASH + k for k in range(4)], 'cinders': [CINDERS + k for k in range(4)]}, 'ash_base': {}}
    for name, first in ON_ASH.items():
        e = {}
        for i, m in enumerate(masks):
            out[first + i] = wg.blend(plain_ash[i % 4], other[name][(i // 4) % 4], m, seed=first + m, width=0.42); e[str(m)] = first + i
        table['ash_base'][name] = e
    molten = [S.get(n) for n in (36300, 36301, 36302, 36303)]; e = {}
    for i, m in enumerate(masks):
        out[CIN_MOLTEN + i] = wg.blend(plain_cin[i % 4], molten[(i // 4) % 4], m, seed=CIN_MOLTEN + m, width=0.36); e[str(m)] = CIN_MOLTEN + i
    table['cinders_base'] = {'molten': e}
    return out, table


def preview(sprites, table, S, path, scale=2):
    """a small canyon floor: ash with a cinder patch, a snow drift and snowy grass at the mouth, edges as the editor makes them"""
    N = 18; g = [['ash'] * N for _ in range(N)]
    for x in range(N):
        for y in range(N):
            if (x - 6) ** 2 + (y - 11) ** 2 < 10: g[x][y] = 'cinders'
            if (x - 13) ** 2 * 1.5 + (y - 5) ** 2 < 9: g[x][y] = 'soft snow'
            if x + y < 6: g[x][y] = 'snowy grass'
    r = random.Random(1); img = Image.new('RGBA', (16 * 2 * N + 32, 8 * 2 * N + 48), (20, 20, 24, 255))
    get = lambda n: sprites.get(n) or S.get(n)
    for x in range(N):
        for y in range(N - 1, -1, -1):
            k = g[x][y]
            if k == 'ash':
                n = None
                for name in ('cinders', 'soft snow', 'snowy grass'):
                    m = wg.mask_of(lambda dx, dy: 0 <= x + dx < N and 0 <= y + dy < N and g[x + dx][y + dy] == name)
                    if m: n = int(table['ash_base'][name][str(m)]); break
                n = n or r.choice(table['plain']['ash'])
            elif k == 'cinders': n = r.choice(table['plain']['cinders'])
            elif k == 'soft snow': n = 35400 + r.randrange(4)
            else: n = 36100 + r.randrange(4)
            sx, sy = 16 * (x + y), 8 * (x - y) + 8 * N
            img.alpha_composite(get(n), (sx, sy))
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    sheet = Image.new('RGBA', (8 * 34 * scale, 34 * scale), (20, 20, 24, 255))
    for i, n in enumerate(table['plain']['ash'] + table['plain']['cinders']):
        sheet.alpha_composite(sprites[n].resize((32 * scale, 32 * scale), Image.NEAREST), (i * 34 * scale, 0))
    full = Image.new('RGBA', (max(img.width, sheet.width), img.height + sheet.height + 10), (20, 20, 24, 255))
    full.alpha_composite(sheet, (0, 0)); full.alpha_composite(img, (0, sheet.height + 10)); full.save(path)


if __name__ == '__main__':
    client = sys.argv[1]
    sprites, table = build(client)
    if '--preview' in sys.argv:
        preview(sprites, table, wg.Sprites(client), sys.argv[sys.argv.index('--preview') + 1]); print('preview only'); sys.exit()
    gfx = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else wg.gfx_dir(client)
    os.makedirs(gfx, exist_ok=True)
    for nr, im in sorted(sprites.items()): im.save(os.path.join(gfx, '%05d.png' % nr))
    json.dump(table, open(os.path.join(HERE, 'world_ash.json'), 'w'), indent=1)
    print('%d sprites written: %d-%d' % (len(sprites), min(sprites), max(sprites)))
