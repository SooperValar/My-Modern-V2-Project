#!/usr/bin/env python3
"""Marsh sprites for Fenwatch (Nov 16): three new grounds with soft edges into grass (made like world_ground.py's),
soft edges on a marsh-grass base, and reeds.

    world_marsh.py <client folder> [--out <folder>] [--sheet <png>]

Grounds (4 plain variants + 46 edge tiles that blend GRASS into them, as in world_ground.py):
  marsh grass 35700-35749 (dark, wet olive grass), marsh mud 35750-35799, murky water 35800-35849.
Edges on a MARSH GRASS base (46 each, in the order of world_ground.all_masks()):
  murky water creeping in 35850-35895, marsh mud 35900-35945, path (35000) 35950-35995.
Reeds: 38200, 38202, 38204, 38206 (32x64, drawn into the tile, block nothing), each N+1 its cut-down form for
"hide walls". Writes tools/sprites/world_marsh.json (the tables) beside this script."""
import json, math, os, random, sys
from PIL import Image, ImageOps, ImageEnhance, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_ground as wg

GROUNDS = {'marsh grass': (35700, 'earth', (0.205, 0.58, 0.36)), 'marsh mud': (35750, 'earth', (0.085, 0.50, 0.30)),
           'murky water': (35800, 'water', (78, 128, 112))}
ON_MARSH = {'murky water': 35850, 'marsh mud': 35900, 'path': 35950}
REEDS = [38200, 38202, 38204, 38206]

def murky(src, seed, rgb):
    g = ImageOps.autocontrast(ImageOps.grayscale(src.convert('RGB')), cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(0.40); g = ImageEnhance.Brightness(g).enhance(0.85)
    t = ImageOps.colorize(g, tuple(int(c * 0.28) for c in rgb), rgb, mid=tuple(int(c * 0.62) for c in rgb)).convert('RGBA')
    d = ImageDraw.Draw(t); r = random.Random(900 + seed)
    for _ in range(2):
        y = r.randrange(19, 30); x = r.randrange(4, 22); l = r.randrange(3, 7)
        d.line([(x, y), (x + l, y)], fill=(150, 190, 165, 255))
    for _ in range(3):                                   # duckweed specks
        x, y = r.randrange(6, 26), r.randrange(19, 30); d.point((x, y), fill=(96, 150, 70, 255))
    t.putalpha(wg.DIAM)
    return t

def reed(seed, cut=False):
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load(); r = random.Random(seed)
    stalks = []
    for k in range(r.randrange(10, 15)):
        bx = r.uniform(9, 23); by = r.uniform(54, 59.5); h = r.uniform(3, 6) if cut else r.uniform(13, 32)
        lean = r.uniform(-0.22, 0.22); stalks.append((by, bx, h, lean, k))
    for by, bx, h, lean, k in sorted(stalks):
        base = r.choice([(74, 118, 52), (92, 132, 58), (116, 140, 70), (150, 150, 84), (64, 100, 48)])
        head = (not cut) and h > 18 and r.random() < 0.55
        n = int(h)
        for i in range(n + 1):
            x = int(round(bx + lean * i + 0.012 * lean * i * i)); y = int(round(by - i))
            if not (0 <= x < 32 and 0 <= y < 64): continue
            sh = 0.78 + 0.35 * i / max(1, n) + (0.10 if x < 16 else -0.06)
            px[x, y] = tuple(max(0, min(255, int(c * sh))) for c in base) + (255,)
            if head and n - 8 <= i <= n - 3:             # the cattail: a dark brown head, two pixels wide
                for xx, c in ((x, (104, 66, 34)), (x + 1, (74, 46, 24))):
                    if 0 <= xx < 32: px[xx, y] = c + (255,)
    return im

def build(client):
    S = wg.Sprites(client); grass = [S.get(n) for n in wg.GRASS]; masks = wg.all_masks(); out = {}
    table = {'masks': masks, 'grass_base': {}, 'marsh_base': {}, 'reeds': REEDS}
    plain = {}
    for name, (first, kind, col) in GROUNDS.items():
        if kind == 'earth': plain[name] = [wg.earth(grass[k], col, 0.95, 0.0, seed=first + k) for k in range(4)]
        else: plain[name] = [murky(S.get(n), k, col) for k, n in enumerate((16933, 16957, 16958, 16959))]
        for k, t in enumerate(plain[name]): out[first + k] = t
        edges = {}
        for i, m in enumerate(masks):
            out[first + 4 + i] = wg.blend(grass[i % 4], plain[name][(i // 4) % 4], m, seed=first + m); edges[str(m)] = first + 4 + i
        table['grass_base'][name] = {'plain': [first + k for k in range(4)], 'edges': edges}
    plain['path'] = [S.get(n) for n in (35000, 35001, 35002, 35003)]
    for name, first in ON_MARSH.items():
        edges = {}
        for i, m in enumerate(masks):
            out[first + i] = wg.blend(plain['marsh grass'][i % 4], plain[name][(i // 4) % 4], m, seed=first + m); edges[str(m)] = first + i
        table['marsh_base'][name] = edges
    for k, nr in enumerate(REEDS):
        out[nr] = reed(7000 + k); out[nr + 1] = reed(7000 + k, cut=True)
    return out, table

if __name__ == '__main__':
    client = sys.argv[1]
    sprites, table = build(client)
    gfx = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else wg.gfx_dir(client)
    os.makedirs(gfx, exist_ok=True)
    for nr, im in sorted(sprites.items()): im.save(os.path.join(gfx, '%05d.png' % nr))
    json.dump(table, open(os.path.join(HERE, 'world_marsh.json'), 'w'), indent=1)
    print('%d sprites written: %d-%d' % (len(sprites), min(sprites), max(sprites)))
    if '--sheet' in sys.argv:
        sh = Image.new('RGBA', (8 * 100, 220), (30, 30, 30, 255))
        for n, nr in enumerate(REEDS + [r + 1 for r in REEDS]): sh.alpha_composite(sprites[nr].resize((96, 192), Image.NEAREST), (n * 100, 14))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
