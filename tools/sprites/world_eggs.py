#!/usr/bin/env python3
"""Lizard eggs (Nov 17, for the Lizard Hatcheries): world objects 38300, 38302, 38304, 38306 (32x64, drawn into the tile
like the reeds; each N+1 is its hide-walls form, the same egg). One large leathery egg a tile (Cody: one big egg, not a
clutch), in a nest of mud, twigs, reeds and straw heaped round its foot: cream, pale cream, greenish, and a hatched one
(a jagged zig-zag break, the dark hollow inside, cracks, shell pieces in the nest).

    world_eggs.py <Client folder> [--out <folder>] [--sheet <png>]"""
import os, sys, math, random
from PIL import Image, ImageDraw
C = sys.argv[1]; OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(C, 'GFX')
EGGS = [38300, 38302, 38304, 38306]
S = 4                                     # drawn 4x, scaled down
CX, CY = 16 * S, 56 * S                   # the tile's centre in a 32x64 object sprite


STALK = [(120, 98, 52), (98, 80, 42), (138, 116, 64), (84, 70, 40), (156, 132, 76), (70, 56, 30)]


def stalks(d, seed, k, front, n):
    """twigs, reed stalks and straw heaped round the egg's foot; front=True: only those in front of it (drawn after the egg)"""
    random.seed(seed + (1000 if front else 0))
    for _ in range(n):
        a = random.uniform(0, math.pi) if front else random.uniform(math.pi, 2 * math.pi)
        r = random.uniform(0.55, 1.1)
        x, y = CX + 12.5 * k * S * r * math.cos(a), CY + 5.6 * k * S * r * math.sin(a)
        b = a + math.pi / 2 + random.uniform(-0.7, 0.7); l = random.uniform(3, 7.5) * S
        lift = random.uniform(0.0, 2.6) * S if front else random.uniform(0.0, 4.0) * S        # the rim stands up a little
        x0, y0, x1, y1 = x - l / 2 * math.cos(b), y - l / 4 * math.sin(b) - lift * random.random(), x + l / 2 * math.cos(b), y + l / 4 * math.sin(b) - lift
        d.line((x0, y0, x1, y1), fill=random.choice(STALK) + (255,), width=random.choice([S, S, int(S * 1.5)]))
        if random.random() < 0.25:                                     # a forked twig
            d.line((x1, y1, x1 + random.uniform(-2, 2) * S, y1 - random.uniform(1, 2.5) * S), fill=random.choice(STALK) + (255,), width=S)


def nest(d, seed, k=0.8):
    random.seed(seed)
    d.ellipse((CX - 14 * k * S, CY - 6.4 * k * S, CX + 14 * k * S, CY + 6.4 * k * S), fill=(62, 48, 28, 255))      # the mud bed
    d.ellipse((CX - 10.5 * k * S, CY - 4.6 * k * S, CX + 10.5 * k * S, CY + 4.4 * k * S), fill=(40, 30, 19, 255))
    for _ in range(26):                                                # straw scattered on the bed
        x, y = CX + random.uniform(-12, 12) * k * S, CY + random.uniform(-5, 5) * k * S
        if ((x - CX) / (13 * k * S)) ** 2 + ((y - CY) / (6 * k * S)) ** 2 > 1: continue
        b = random.uniform(0, math.pi); l = random.uniform(1.5, 3.5) * S
        d.line((x, y, x + l * math.cos(b), y + 0.5 * l * math.sin(b)), fill=random.choice(STALK) + (255,), width=S)
    stalks(d, seed, k, False, 44)


def egg(img, x, y, base, spots, seed, broken=False, size=1.0):
    """one egg standing a little tilted: an upright oval, lit from the upper left, with speckles"""
    random.seed(seed)
    w, h = 3.4 * S * size, 4.8 * S * size; tilt = random.uniform(-0.15, 0.15)
    cut = {}
    if broken:                                                         # the break: a zig-zag of shell points, lower on one side
        lvl = y - h * 0.1; xs = []; hs = []; k = 0; xx = x - w - 2 * S
        while xx <= x + w + 2 * S + 2.2 * S:
            xs.append(xx); hs.append(lvl + (xx - x) * 0.3 + (-random.uniform(1.6, 3.6) * S if k % 2 else random.uniform(0.2, 1.4) * S))
            xx += random.uniform(1.6, 2.6) * S; k += 1
        for c in range(int(x - w - 2 * S), int(x + w + 2 * S)):
            for n in range(len(xs) - 1):
                if xs[n] <= c <= xs[n + 1]:
                    t = (c - xs[n]) / (xs[n + 1] - xs[n]); cut[c] = hs[n] + (hs[n + 1] - hs[n]) * t; break
    ImageDraw.Draw(img).ellipse((x - w - S, y - h - S, x + w + S, y + h + S * 0.6), fill=(34, 26, 16, 255))      # a dark outline, so eggs read apart
    if broken:
        px0 = img.load()
        for xx, c in cut.items():
            for yy in range(int(y - h - 2 * S), int(c - S)):
                if 0 <= xx < img.width and 0 <= yy < img.height: px0[xx, yy] = (0, 0, 0, 0)
    px = img.load()
    for yy in range(int(y - h - 2), int(y + h + 2)):
        for xx in range(int(x - w - 2), int(x + w + 2)):
            dx, dy = xx - x, yy - y
            rx = dx * math.cos(tilt) + dy * math.sin(tilt); ry = -dx * math.sin(tilt) + dy * math.cos(tilt)
            hh = h * (0.92 if ry < 0 else 1.0)                      # a little narrower at the top
            e = (rx / w) ** 2 + (ry / hh) ** 2
            if e > 1: continue
            if broken and yy < cut.get(xx, y - h * 0.25): continue     # above the ragged break: gone
            nz = math.sqrt(max(0, 1 - e))
            light = 0.55 + 0.55 * max(0, (-rx / w * 0.6 - ry / hh * 0.7 + nz * 0.6)) - 0.18 * (1 - nz)
            col = tuple(max(0, min(255, int(c * light))) for c in base)
            px[xx, yy] = col + (255,)
    d = ImageDraw.Draw(img)
    for k in range(int(w * h / (S * S) / 7)):                        # a few speckles
        a = random.uniform(0, 2 * math.pi); r = math.sqrt(random.random()) * 0.85
        sx, sy = x + w * r * math.cos(a), y + h * r * math.sin(a)
        if broken and sy < cut.get(int(sx), 0) + S: continue
        if img.getpixel((int(sx), int(sy)))[3]: d.ellipse((sx - S * 0.7, sy - S * 0.6, sx + S * 0.7, sy + S * 0.6), fill=spots + (255,)) if random.random() < 0.8 else None
    if broken:
        px = img.load()
        for xx, c in cut.items():                                      # the hollow: dark inside the shell just under the break
            for yy in range(int(c) + 1, int(y - h * 0.1 + 4.5 * S)):
                ex, ey = (xx - x) / (w * 0.8), (yy - (y - h * 0.1 + 1.5 * S)) / (h * 0.3)
                if 0 <= xx < img.width and 0 <= yy < img.height and px[xx, yy][3] and ex * ex + ey * ey <= 1:
                    k = max(0.0, min(1.0, (yy - c) / (4.5 * S))); px[xx, yy] = (int(26 + 34 * k), int(20 + 26 * k), int(14 + 16 * k), 255)
        for xx, c in cut.items():                                      # the shell's broken edge: a pale line along the break
            if 0 <= xx < img.width and px[xx, int(c)][3]:
                for yy in (int(c), int(c) + 1):
                    px[xx, yy] = tuple(min(255, int(v * 1.12)) for v in base) + (255,)
        for _ in range(3):                                             # cracks running down from the break
            cx0 = x + random.uniform(-0.6, 0.6) * w; cy0 = cut.get(int(cx0), y) + S; pts = [(cx0, cy0)]
            for k in range(random.randint(3, 5)):
                cx0 += random.uniform(-1.6, 1.6) * S; cy0 += random.uniform(1.2, 2.4) * S; pts.append((cx0, cy0))
            pts = [p for p in pts if 0 <= int(p[0]) < img.width and 0 <= int(p[1]) < img.height and px[int(p[0]), int(p[1])][3]]
            if len(pts) > 1: d.line(pts, fill=(70, 58, 40, 255), width=max(1, S // 2 + 1))


def shards(img, base, seed):
    """broken shell pieces lying in the nest in front of a hatched egg"""
    random.seed(seed); d = ImageDraw.Draw(img)
    for _ in range(4):
        sx, sy = CX + random.uniform(-9, 9) * S, CY + random.uniform(0.5, 4) * S
        pts = [(sx + random.uniform(-2.2, 2.2) * S, sy + random.uniform(-1.1, 1.1) * S) for _ in range(4)]
        d.polygon(pts, fill=(34, 26, 16, 255)); d.polygon([(px + 0.4 * (CX - px) / 10, py) for px, py in pts], fill=tuple(int(c * 0.9) for c in base) + (255,))


def clutch(spec, seed):
    img = Image.new('RGBA', (32 * S, 64 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    nest(d, seed)
    base, spots, broken = spec
    egg(img, CX, CY - 10 * S, base, spots, seed * 10, broken, size=2.8)
    stalks(d, seed, 0.8, True, 30)                                     # the front of the nest, over the egg's foot
    if broken: shards(img, base, seed)
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
