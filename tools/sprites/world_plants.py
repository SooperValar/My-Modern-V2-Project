#!/usr/bin/env python3
"""Desert plants for MyV2: cacti drawn as 32x64 object sprites like the game's trees (base around y=58, lit from
the left), with dark spines (Cody's pick, Nov 13).

    world_plants.py <out folder> [--sheet <png>]

Writes NNNNN.png from 38000 (the "trees / plants" block of the world sprite plan in HANDOFF.md) into <out folder>
(normally the client's GFX folder).
"""
import math, os, random, sys
from PIL import Image, ImageDraw

FIRST = 38000
SPINE = (28, 26, 22, 255)        # near black (Cody's pick)
SPINE_ALT = (214, 220, 180, 255)  # the light spines of the first draft (not used)


def cyl(px, x0, x1, y0, y1, col, seed, ribs=True, rnd=True, spines=True):
    """an upright stem from x0..x1, y0..y1: lit from the left, ribs every 3 pixels, rounded top, spines"""
    r = random.Random(seed); w = x1 - x0 + 1
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            u = (x - x0 + 0.5) / w
            if rnd and y == y0 and (u < 0.2 or u > 0.8):
                continue
            sh = 1.15 - 0.75 * u + 0.25 * math.sin(u * 3.14)
            if ribs and w >= 5 and (x - x0) % 3 == 2:
                sh *= 0.82
            sh *= 1 + r.uniform(-0.06, 0.06)
            px[x, y] = tuple(max(0, min(255, int(c * sh))) for c in col) + (255,)
    if spines and y1 > y0:
        for _ in range(max(2, (y1 - y0) * w // 14)):
            x = r.randrange(x0, x1 + 1); y = r.randrange(y0 + 1, y1 + 1)
            if r.random() < 0.5:
                px[x, y] = SPINE


def saguaro(seed, arms, col=(58, 116, 64)):
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load(); r = random.Random(seed)
    top = r.randrange(8, 14)
    cyl(px, 13, 19, top, 58, col, seed)
    if 'L' in arms:
        ay = r.randrange(top + 12, top + 22); ah = r.randrange(8, 13)
        cyl(px, 7, 11, ay - ah, ay + 3, col, seed + 1); cyl(px, 9, 13, ay + 1, ay + 4, col, seed + 2, ribs=False, rnd=False, spines=False)
    if 'R' in arms:
        ay = r.randrange(top + 10, top + 20); ah = r.randrange(8, 14)
        cyl(px, 21, 25, ay - ah, ay + 3, col, seed + 3); cyl(px, 19, 23, ay + 1, ay + 4, col, seed + 4, ribs=False, rnd=False, spines=False)
    return im


def barrel(seed, col=(70, 128, 70), flower=True):
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load(); r = random.Random(seed)
    for y in range(44, 59):
        hw = int(7 * math.sqrt(max(0, 1 - ((y - 51.5) / 8.0) ** 2))) + 1
        cyl(px, 16 - hw, 15 + hw, y, y, col, seed + y, rnd=False, spines=False)
    for _ in range(14):
        x = r.randrange(9, 23); y = r.randrange(45, 58)
        if px[x, y][3]:
            px[x, y] = SPINE
    if flower:
        for (x, y) in ((14, 44), (16, 43), (18, 44), (15, 43), (17, 44)):
            px[x, y] = r.choice([(230, 80, 110, 255), (250, 170, 60, 255)])
    return im


def pear(seed, col=(84, 140, 66)):
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); r = random.Random(seed)
    for (cx, cy, rx, ry) in [(16, 50, 6, 8), (10, 42, 5, 7), (21, 40, 5, 7), (15, 34, 4, 6)]:
        m = Image.new('L', (32, 64), 0); ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        tile = Image.new('RGBA', (32, 64)); tp = tile.load()
        for y in range(64):
            for x in range(32):
                u = (x - (cx - rx)) / (2 * rx + 1); sh = (1.15 - 0.6 * u) * (1 + r.uniform(-0.07, 0.07))
                tp[x, y] = tuple(max(0, min(255, int(c * sh))) for c in col) + (255,)
        im.paste(tile, (0, 0), m)
        for _ in range(5):
            x = r.randrange(cx - rx + 1, cx + rx); y = r.randrange(cy - ry + 1, cy + ry)
            if im.getpixel((x, y))[3]:
                im.putpixel((x, y), SPINE)
    for (x, y) in ((8, 35), (13, 28), (23, 33)):
        im.putpixel((x, y), (190, 50, 90, 255)); im.putpixel((x + 1, y), (160, 40, 80, 255))
    return im


# number: (name, image)
PLANTS = [
    ('Saguaro', lambda: saguaro(1, 'LR')),
    ('Saguaro (left arm)', lambda: saguaro(2, 'L')),
    ('Saguaro (right arm)', lambda: saguaro(3, 'R')),
    ('Saguaro (no arms)', lambda: saguaro(4, '')),
    ('Barrel cactus (flowers)', lambda: barrel(5)),
    ('Barrel cactus', lambda: barrel(6, flower=False)),
    ('Prickly pear', lambda: pear(7)),
]

if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    ims = []
    for k, (name, make) in enumerate(PLANTS):
        im = make(); im.save(os.path.join(out, '%05d.png' % (FIRST + k))); ims.append((FIRST + k, name, im))
    print('%d plants written: %d-%d' % (len(ims), FIRST, FIRST + len(ims) - 1))
    if '--sheet' in sys.argv:
        sh = Image.new('RGBA', (len(ims) * 110 + 10, 230), (30, 30, 30, 255)); d = ImageDraw.Draw(sh)
        for n, (nr, name, im) in enumerate(ims):
            sh.alpha_composite(im.resize((96, 192), Image.NEAREST), (10 + n * 110, 30)); d.text((10 + n * 110, 8), str(nr), fill=(255, 220, 120, 255))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
