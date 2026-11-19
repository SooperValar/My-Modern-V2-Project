#!/usr/bin/env python3
"""Objects for the Ashen Fields (Nov 18): charred dead trees and their stumps, and smoking vents.

    world_ashen.py <client folder> [--out <folder>] [--preview <png>]

  charred trees 38448, 38450, 38452, 38454 (the MyV2 dead trees 38160-38163, burnt black with a few embers),
  each followed by its charred stump (38449 ...: what hide mode shows, sprite + 1)
  smoking vents 38456-38459 (a low mound of dark rock, glowing cracks, a wisp of smoke)
  cinder rocks 38460-38462 (the game's lava stones 678 / 682 / 674 in the ash's greys, faint embers: Cody, the black and
  red ones stood out on the grey ash)      Next free: 38463
Writes tools/sprites/world_ashen.json beside this script."""
import colorsys, json, math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_ground as wg

TREES, VENTS, ROCKS = 38448, 38456, 38460


def char(im, seed, embers=6):
    """burn a sprite: near-black charcoal keeping its shading, a faint warm tint, a few glowing ember pixels"""
    r = random.Random(seed); out = im.copy(); px = out.load(); w, h = out.size; solid = []
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if c[3] == 0 or (c[0] > 235 and c[1] < 25 and c[2] > 235): continue
            v = colorsys.rgb_to_hsv(*[k / 255 for k in c[:3]])[2]
            g = 18 + int(v * 70)
            px[x, y] = (g + 6, g + 2, g, c[3]); solid.append((x, y))
    # embers: on the lower trunk mostly
    low = [p for p in solid if p[1] > h * 0.55] or solid
    for _ in range(embers):
        x, y = r.choice(low); px[x, y] = r.choice([(255, 140, 40), (230, 80, 20), (255, 190, 80)]) + (255,)
    # a light dusting of ash on top-facing pixels
    for x, y in solid:
        if y > 0 and px[x, y - 1][3] == 0 and r.random() < 0.35:
            c = px[x, y]; px[x, y] = (min(255, c[0] + 60), min(255, c[1] + 58), min(255, c[2] + 56), c[3])
    return out


def ashrock(im, seed):
    """a lava stone in the ash's greys: charcoal shading, ash on top, its red veins dimmed to a faint ember glow"""
    r = random.Random(seed); out = im.copy(); px = out.load(); w, h = out.size
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if c[3] == 0 or (c[0] > 235 and c[1] < 25 and c[2] > 235): continue
            hh, ss, v = colorsys.rgb_to_hsv(*[k / 255 for k in c[:3]])
            if ss > 0.5 and v > 0.45 and (hh < 0.08 or hh > 0.92) and r.random() < 0.6:    # the red veins as embers
                px[x, y] = (170, 70, 28, c[3]) if r.random() < 0.6 else (225, 110, 40, c[3]); continue
            g = 46 + int(v * 95)
            px[x, y] = (g + 6, g + 3, g, c[3])
    for y in range(1, h):
        for x in range(w):
            if px[x, y][3] and not px[x, y - 1][3] and r.random() < 0.6:
                c = px[x, y]; px[x, y] = (min(255, c[0] + 40), min(255, c[1] + 39), min(255, c[2] + 37), c[3])
    return out


def vent(seed):
    """a low mound of dark rock with glowing cracks and a wisp of smoke; 32 x 64, standing on the tile's diamond"""
    r = random.Random(seed); im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load()
    cx, cy, rx, ry, hgt = 16, 56, 11 + r.randrange(-1, 2), 5, 7 + r.randrange(0, 3)
    for y in range(64):
        for x in range(32):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1 or (abs(dx) < 1 and cy - hgt * (1 - dx * dx) ** 0.5 <= y + 0.5 <= cy):
                top = cy - hgt * max(0, 1 - dx * dx) ** 0.5
                sh = 0.55 + 0.35 * (-dx * 0.6 + (cy - y) / (hgt + 6) * 0.5) + r.uniform(-0.08, 0.08)
                g = int(40 + 50 * max(0, min(1, sh)))
                px[x, y] = (g + 4, g, g - 2, 255)
                if y < top + 1.5: px[x, y] = (g + 30, g + 28, g + 26, 255)        # ash on the rim
    # the glowing mouth and cracks
    mx, my = cx + r.randrange(-1, 2), int(cy - hgt + 1)
    for dx in range(-3, 4):
        for dy in range(-1, 2):
            if abs(dx) + abs(dy) * 2 <= 3 and px[mx + dx, my + dy][3]:
                px[mx + dx, my + dy] = ((255, 200, 90) if abs(dx) <= 1 and dy == 0 else (240, 110, 30)) + (255,)
    for _ in range(3):
        x, y = mx, my
        for _ in range(r.randrange(4, 8)):
            x += r.choice((-1, 0, 1)); y += r.choice((0, 1, 1))
            if 0 <= x < 32 and 0 <= y < 64 and px[x, y][3]: px[x, y] = (230, 90, 20, 255)
    # smoke: soft grey puffs rising and drifting
    smoke = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(smoke)
    x, y = mx, my - 2
    for k in range(7):
        rad = 2 + k * 0.7; a = int(150 - k * 18)
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(150, 146, 142, a))
        x += r.uniform(-1.2, 1.8); y -= 4.2
    smoke = smoke.filter(ImageFilter.GaussianBlur(1.1))
    return Image.alpha_composite(smoke, im) if False else Image.alpha_composite(im, smoke)


def build(client):
    S = wg.Sprites(client); out = {}
    for k in range(4):
        out[TREES + 2 * k] = char(S.get(38160 + k), TREES + k)
        out[TREES + 2 * k + 1] = char(S.get(38164 + k), TREES + 10 + k, embers=3)
    for k in range(4): out[VENTS + k] = vent(VENTS + k)
    for k, n in enumerate((678, 682, 674)): out[ROCKS + k] = ashrock(S.get(n), ROCKS + k)
    table = {'charred tree': [TREES + 2 * k for k in range(4)], 'charred stump': [TREES + 2 * k + 1 for k in range(4)],
             'vent': [VENTS + k for k in range(4)], 'cinder rock': [ROCKS + k for k in range(3)]}
    return out, table


def preview(sp, path):
    ks = sorted(sp); W = sum(sp[k].width for k in ks) + 4 * len(ks); H = max(sp[k].height for k in ks)
    im = Image.new('RGBA', (W, H + 8), (120, 116, 112, 255)); x = 0
    for k in ks: im.alpha_composite(sp[k], (x, H - sp[k].height + 4)); x += sp[k].width + 4
    im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(path)


if __name__ == '__main__':
    client = sys.argv[1]; sp, table = build(client)
    if '--preview' in sys.argv: preview(sp, sys.argv[sys.argv.index('--preview') + 1]); print('preview only'); sys.exit()
    gfx = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else wg.gfx_dir(client)
    for n, im in sp.items(): im.save(os.path.join(gfx, '%05d.png' % n))
    json.dump(table, open(os.path.join(HERE, 'world_ashen.json'), 'w'), indent=1)
    print('%d sprites written: %d-%d' % (len(sp), min(sp), max(sp)))
