#!/usr/bin/env python3
"""Item pictures for the Lizard Hatcheries (Nov 17), sprites 44536-44541 into <client>/GFX:
    lizard_hatcheries.py <client folder> <3d Models folder>
44536 Lizard Egg (drawn, like the nest eggs 38300), 44537 Broodmother's Crown (Crown2, dark bronze and garnet),
44538 Archmage's Phial (Potion5, green), 44539 Scaled Belt (drawn: green-brown scales, a bronze buckle),
44540 Elixir of the Good Moon (Potion10, pale moon-silver), 44541 Lizard Head (cut from the lizard's front frame, 13264 + 48)."""
import os, subprocess, sys, math
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); C, M = sys.argv[1], sys.argv[2]
G = os.path.join(C, 'GFX'); ICON = os.path.join(HERE, '..', 'item_icon.py'); R2 = os.path.join(M, 'RPG Pack 2', 'OBJ')
def icon(nr, model, *a): subprocess.run([sys.executable, ICON, model, os.path.join(G, '%05d.png' % nr)] + [str(x) for x in a], check=True)
icon(44537, os.path.join(R2, 'Crown2.obj'), '--size', 20, '--yaw', 20, '--bright', 2, '--recol', 'Gold=8a6630,Red=8c1a1e')
icon(44538, os.path.join(R2, 'Potion5_Filled.obj'), '--size', 20, '--glass', '203050', '--liquid', '58c040')
icon(44540, os.path.join(R2, 'Potion10_Filled.obj'), '--size', 20, '--glass', '303850', '--liquid', 'd8e4ff')
def save(im, nr): im.save(os.path.join(G, '%05d.png' % nr))
# ---- 44536 Lizard Egg: one leathery egg, lit from the upper left, a few brown speckles, a dark outline
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
cx, cy, w, h = 15.5, 17.0, 7.2, 10.0
for y in range(32):
    for x in range(32):
        hh = h * (0.92 if y < cy else 1.0); e = ((x - cx) / w) ** 2 + ((y - cy) / hh) ** 2
        if e <= 1.0:
            nz = math.sqrt(1 - e); lit = 0.55 + 0.55 * max(0, (-(x - cx) / w * 0.6 - (y - cy) / hh * 0.7 + nz * 0.6)) - 0.18 * (1 - nz)
            px[x, y] = tuple(max(0, min(255, int(c * lit))) for c in (226, 214, 176)) + (255,)
        elif e <= 1.35: px[x, y] = (34, 26, 16, 255)
for x, y in ((13, 12), (18, 15), (15, 20), (19, 22), (12, 18), (16, 24), (20, 18)): px[x, y] = (120, 92, 58, 255)
save(im, 44536)
# ---- 44539 Scaled Belt: a coiled belt of lizard scales (green-brown, scale rows), a square bronze buckle
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 12.5, (y - 19.5) / 7.5; r = math.hypot(dx, dy)
        if 0.62 <= r <= 1.0:
            lit = 0.72 + 0.30 * (-dx * 0.6 - dy * 0.8) / max(r, 0.01) * (0.5 if r < 0.8 else 1.0)
            if r > 0.93 or r < 0.67: lit *= 0.6                             # dark edges
            elif (x + 2 * y) % 4 == 0: lit *= 0.78                          # the scale pattern
            elif (x + 2 * y) % 4 == 1: lit *= 1.18
            c = (66, 84, 40) if dy < 0 else (82, 100, 48)
            px[x, y] = tuple(max(0, min(255, int(v * lit))) for v in c) + (255,)
BUCKLE = ["oooooo", "oBBBBo", "oB..Bo", "oB..Bo", "oBBBBo", "oooooo"]
for j_, row in enumerate(BUCKLE):
    for i_, ch in enumerate(row):
        if ch == 'o': px[13 + i_, 23 + j_] = (60, 40, 18, 255)
        elif ch == 'B': px[13 + i_, 23 + j_] = (196, 146, 66, 255) if i_ + j_ < 5 else (150, 104, 44, 255)
save(im, 44539)
# ---- 44541 Lizard Head: cut from the lizard's front-facing frame (the game's sprite 13264 + 48)
sys.argv = [sys.argv[0], C, '/tmp']
exec(open(os.path.join(HERE, '..', '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
im = load(13264 + 48).convert('RGBA')
im.putdata([(0, 0, 0, 0) if (p[0] > 240 and p[1] < 16 and p[2] > 240) else p for p in im.get_flattened_data()])
bb = im.getbbox(); frac = 0.19
top = im.crop((bb[0], bb[1], bb[2], bb[1] + max(6, int((bb[3] - bb[1]) * frac)))); px = top.load()
rows = [[x for x in range(top.width) if px[x, y][3]] for y in range(top.height)]
cx = sum(rows[1]) / max(1, len(rows[1])) if len(rows) > 1 and rows[1] else top.width / 2
half = max(len(r) for r in rows[:max(2, top.height * 2 // 3)]) / 2 + 1
top = top.crop((max(0, int(cx - half)), 0, min(top.width, int(cx + half) + 1), top.height)); top = top.crop(top.getbbox())
k = min(24 / top.width, 26 / top.height); top = top.resize((max(1, round(top.width * k)), max(1, round(top.height * k))), Image.NEAREST)
out = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); ox, oy = (32 - top.width) // 2, 29 - top.height; out.alpha_composite(top, (ox, oy))
px = out.load(); neck = [x for x in range(32) if px[x, 28][3]]
for x in neck:
    px[x, 29] = (120, 22, 22, 255)
    if neck[0] < x < neck[-1]: px[x, 30] = (84, 14, 14, 255)
save(out, 44541)
print('done: 44536-44541')
