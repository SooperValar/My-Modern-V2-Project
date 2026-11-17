#!/usr/bin/env python3
"""Lizard eggs (Nov 17, for the Lizard Hatcheries): world objects 38300, 38302, 38304, 38306 (32x64, drawn into the tile
like the reeds; each N+1 is its hide-walls form, the same egg). One large leathery egg a tile (Cody: one big egg, not a
clutch), in a small ring of mud and old reeds: cream, pale cream, greenish, and a hatched one with its top broken off.

    world_eggs.py <Client folder> [--out <folder>] [--sheet <png>]"""
import os, sys, math, random
from PIL import Image, ImageDraw
C = sys.argv[1]; OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(C, 'GFX')
EGGS = [38300, 38302, 38304, 38306]
S = 4                                     # drawn 4x, scaled down
CX, CY = 16 * S, 56 * S                   # the tile's centre in a 32x64 object sprite


def nest(d, seed, k=0.8):
    random.seed(seed)
    # a flat oval of dark mud with reed stalks round its rim (in the game's 2:1 view)
    d.ellipse((CX - 13 * k * S, CY - 6 * k * S, CX + 13 * k * S, CY + 6 * k * S), fill=(70, 54, 32, 255))
    d.ellipse((CX - 10.5 * k * S, CY - 4.6 * k * S, CX + 10.5 * k * S, CY + 4.4 * k * S), fill=(40, 30, 19, 255))
    for _ in range(30):
        a = random.uniform(0, 2 * math.pi); r = random.uniform(0.8, 1.05)
        x, y = CX + 11 * k * S * r * math.cos(a), CY + 5 * k * S * r * math.sin(a)
        b = a + math.pi / 2 + random.uniform(-0.5, 0.5); l = random.uniform(2.5, 4.5) * S
        col = random.choice([(120, 98, 52), (98, 80, 42), (138, 116, 64), (84, 70, 40)])
        d.line((x, y, x + l * math.cos(b), y + 0.5 * l * math.sin(b)), fill=col + (255,), width=S)


def egg(img, x, y, base, spots, seed, broken=False, size=1.0):
    """one egg standing a little tilted: an upright oval, lit from the upper left, with speckles"""
    random.seed(seed)
    w, h = 3.4 * S * size, 4.8 * S * size; tilt = random.uniform(-0.15, 0.15)
    ImageDraw.Draw(img).ellipse((x - w - S, y - h - S, x + w + S, y + h + S * 0.6), fill=(34, 26, 16, 255))      # a dark outline, so eggs read apart
    px = img.load()
    for yy in range(int(y - h - 2), int(y + h + 2)):
        for xx in range(int(x - w - 2), int(x + w + 2)):
            dx, dy = xx - x, yy - y
            rx = dx * math.cos(tilt) + dy * math.sin(tilt); ry = -dx * math.sin(tilt) + dy * math.cos(tilt)
            hh = h * (0.92 if ry < 0 else 1.0)                      # a little narrower at the top
            e = (rx / w) ** 2 + (ry / hh) ** 2
            if e > 1: continue
            if broken and ry < -h * 0.25: continue                   # the top is gone
            nz = math.sqrt(max(0, 1 - e))
            light = 0.55 + 0.55 * max(0, (-rx / w * 0.6 - ry / hh * 0.7 + nz * 0.6)) - 0.18 * (1 - nz)
            col = tuple(max(0, min(255, int(c * light))) for c in base)
            px[xx, yy] = col + (255,)
    d = ImageDraw.Draw(img)
    for k in range(int(w * h / (S * S) / 7)):                        # a few speckles
        a = random.uniform(0, 2 * math.pi); r = math.sqrt(random.random()) * 0.85
        sx, sy = x + w * r * math.cos(a), y + h * r * math.sin(a)
        if broken and sy < y - h * 0.25: continue
        if img.getpixel((int(sx), int(sy)))[3]: d.ellipse((sx - S * 0.7, sy - S * 0.6, sx + S * 0.7, sy + S * 0.6), fill=spots + (255,)) if random.random() < 0.8 else None
    if broken:                                                      # a jagged rim and the dark inside
        top = y - h * 0.25
        d.ellipse((x - w * 0.8, top - S * 1.6, x + w * 0.8, top + S * 1.6), fill=(30, 26, 18, 255))
        for k in range(7):
            t = x - w * 0.9 + k * w * 0.3
            d.polygon([(t, top), (t + w * 0.15, top - S * random.uniform(1.0, 2.2)), (t + w * 0.3, top)], fill=tuple(int(c * 0.95) for c in base) + (255,))
        px = img.load()                                              # nothing above the break: no outline there
        for yy in range(int(y - h - 2 * S), int(top - 2.3 * S)):
            for xx in range(int(x - w - 2 * S), int(x + w + 2 * S)): px[xx, yy] = (0, 0, 0, 0)


def clutch(spec, seed):
    img = Image.new('RGBA', (32 * S, 64 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    nest(d, seed)
    base, spots, broken = spec
    egg(img, CX, CY - 10 * S, base, spots, seed * 10, broken, size=2.8)
    small = img.resize((32, 64), Image.LANCZOS)
    a = small.split()[3].point(lambda v: 255 if v > 100 else 0); small.putalpha(a)
    return small


CREAM, CREAM2, GREEN, BROWN = (226, 214, 176), (210, 196, 150), (176, 190, 140), (120, 92, 58)
SPECS = [(CREAM, BROWN, False), (CREAM2, BROWN, False), (GREEN, (86, 96, 60), False), (CREAM, BROWN, True)]
out = {}
for k, nr in enumerate(EGGS):
    out[nr] = clutch(SPECS[k], 300 + k); out[nr + 1] = out[nr]
os.makedirs(OUT, exist_ok=True)
for nr, im in out.items(): im.save(os.path.join(OUT, '%05d.png' % nr))
print('lizard eggs:', ', '.join(str(n) for n in sorted(out)))
if '--sheet' in sys.argv:
    bg = os.path.join(C, 'GFX', '35750.png')
    tile = Image.open(bg).convert('RGBA') if os.path.exists(bg) else None
    sh = Image.new('RGBA', (4 * 104, 200), (40, 46, 34, 255))
    for k, nr in enumerate(EGGS):
        cell = Image.new('RGBA', (32, 64), (0, 0, 0, 0))
        if tile: cell.alpha_composite(tile, (0, 32))
        cell.alpha_composite(out[nr]); sh.alpha_composite(cell.resize((96, 192), Image.NEAREST), (k * 104 + 4, 4))
    sh.save(sys.argv[sys.argv.index('--sheet') + 1])
