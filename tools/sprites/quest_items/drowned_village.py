#!/usr/bin/env python3
"""Item pictures for the Drowned Village (Nov 16), sprites 44524-44533 into <client>/GFX:
    drowned_village.py <client folder> <3d Models folder>
44524 Drowned Sailor Head, 44525 Bog-man Head (cut from the monsters' own front-facing frame, 50000 / 50500),
44526 Captain Morrow's Compass, 44527 Maud's Hex-Doll, 44528 Silver Net, 44529 Maud's Herb Pouch, 44530 Ring of Tides,
44531 Fisher-King's Belt (the game's belt 16665 in sea colours), 44532 Draught of Clear Water."""
import os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); C, M = sys.argv[1], sys.argv[2]
G = os.path.join(C, 'GFX'); ICON = os.path.join(HERE, '..', 'item_icon.py')
R2 = os.path.join(M, 'RPG Pack 2', 'OBJ'); FP = os.path.join(M, 'Fantasy Props')
def icon(nr, model, *a):
    subprocess.run([sys.executable, ICON, model, os.path.join(G, '%05d.png' % nr)] + [str(x) for x in a], check=True)
def head(nr, src, frac):
    """the monster's head, cut from its front-facing frame: the top `frac` of the figure, only the columns of the head itself"""
    im = Image.open(os.path.join(G, '%05d.png' % src)).convert('RGBA'); bb = im.getbbox()
    top = im.crop((bb[0], bb[1], bb[2], bb[1] + max(6, int((bb[3] - bb[1]) * frac)))); px = top.load()
    rows = [[x for x in range(top.width) if px[x, y][3]] for y in range(top.height)]
    cx = sum(rows[1]) / max(1, len(rows[1])) if len(rows) > 1 and rows[1] else top.width / 2
    half = max(len(r) for r in rows[:max(2, top.height * 2 // 3)]) / 2 + 1
    top = top.crop((max(0, int(cx - half)), 0, min(top.width, int(cx + half) + 1), top.height)); top = top.crop(top.getbbox())
    k = min(24 / top.width, 26 / top.height); top = top.resize((max(1, round(top.width * k)), max(1, round(top.height * k))), Image.NEAREST)
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); ox, oy = (32 - top.width) // 2, 29 - top.height; out.alpha_composite(top, (ox, oy))
    px = out.load(); neck = [x for x in range(32) if px[x, 28][3]]
    for x in neck:                                        # a dark red cut under the neck
        px[x, 29] = (120, 22, 22, 255)
        if neck[0] < x < neck[-1]: px[x, 30] = (84, 14, 14, 255)
    out.save(os.path.join(G, '%05d.png' % nr))
head(44524, 50000 + 40, 0.17); head(44525, 50500 + 40, 0.24)
icon(44526, os.path.join(R2, 'Coin_Star.obj'), '--size', 17, '--yaw', 20, '--bright', 2, '--recol', 'Gold=c9a227')
icon(44527, os.path.join(FP, 'Dummy.gltf'), '--size', 26, '--yaw', 30)
icon(44528, os.path.join(FP, 'Rope_3.gltf'), '--size', 24, '--yaw', 30, '--tint', 'c8d2dc', '--mix', 0.85)
icon(44529, os.path.join(R2, 'Pouch.obj'), '--size', 20, '--yaw', 25, '--bright', 2)
icon(44530, os.path.join(R2, 'Ring2.obj'), '--size', 13, '--bright', 2.2, '--recol', 'Golden=5fa8d8')
icon(44532, os.path.join(R2, 'Potion2_Filled.obj'), '--size', 20, '--glass', '203050', '--liquid', '70c8ff')
# the belt, drawn: a coiled belt of grey-blue sealskin, lit from the upper left, a silver fish for a buckle
import math
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 12.5, (y - 19.5) / 7.5; r = math.hypot(dx, dy)
        if 0.62 <= r <= 1.0:
            lit = 0.72 + 0.30 * (-dx * 0.6 - dy * 0.8) / max(r, 0.01) * (0.5 if r < 0.8 else 1.0)
            if r > 0.93 or r < 0.67: lit *= 0.62                    # dark edges
            elif abs(r - 0.81) < 0.03 and (x + y) % 2 == 0: lit *= 1.35   # a line of stitching
            c = (58, 92, 112) if dy < 0 else (70, 108, 128)          # the far side of the loop a little darker
            px[x, y] = tuple(max(0, min(255, int(v * lit))) for v in c) + (255,)
FISH = ["..sss...s", ".sSSSs.ss", "sSSSSSsSs", ".sSSSs.ss", "..sss...s"]      # the buckle, on the front of the loop
for j_, row in enumerate(FISH):
    for i_, ch in enumerate(row):
        if ch != '.': px[11 + i_, 23 + j_] = (236, 240, 244, 255) if ch == 'S' else (150, 160, 172, 255)
px[13, 25] = (40, 50, 60, 255)                                              # its eye
im.save(os.path.join(G, '44531.png'))
print('done')
