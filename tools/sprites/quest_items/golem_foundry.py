#!/usr/bin/env python3
"""Item pictures for the Golem Foundry (Nov 17), sprites 44542-44546 into <client>/GFX:
    golem_foundry.py <client folder> <3d Models folder>
44542 Golem Core (Mineral: dark iron, glowing orange crystals), 44543 Foundry Heart (Heart, hot iron glowing orange),
44544 Colossus Core (Mineral: brass, bright gold crystals), 44545 Forgefire Ring (Ring3: iron band, an ember-red stone),
44546 Belt of the Colossus (drawn: brass plates on dark leather, a heavy brass buckle)."""
import os, subprocess, sys, math
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); C, M = sys.argv[1], sys.argv[2]
G = os.path.join(C, 'GFX'); ICON = os.path.join(HERE, '..', 'item_icon.py'); R2 = os.path.join(M, 'RPG Pack 2', 'OBJ')
def icon(nr, model, *a): subprocess.run([sys.executable, ICON, model, os.path.join(G, '%05d.png' % nr)] + [str(x) for x in a], check=True)
icon(44542, os.path.join(R2, 'Mineral.obj'), '--size', 20, '--yaw', 25, '--bright', 2.0, '--recol', 'Grey=3c3e46,Pink=f0781c')
icon(44543, os.path.join(R2, 'Heart.obj'), '--size', 20, '--yaw', 20, '--bright', 2.4, '--recol', 'Red=d65a14')
icon(44544, os.path.join(R2, 'Mineral.obj'), '--size', 22, '--yaw', 60, '--bright', 2.0, '--recol', 'Grey=8a6a28,Pink=ffd868')
icon(44545, os.path.join(R2, 'Ring3.obj'), '--size', 20, '--yaw', 25, '--tilt', 30, '--bright', 1.8, '--recol', 'Golden=4a4c54,Red=e04a10')
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 12.5, (y - 19.5) / 7.5; r = math.hypot(dx, dy)
        if 0.60 <= r <= 1.0:
            lit = 0.72 + 0.30 * (-dx * 0.6 - dy * 0.8) / max(r, 0.01) * (0.5 if r < 0.8 else 1.0)
            if r > 0.93 or r < 0.66: lit *= 0.6
            ang = math.atan2(dy, dx); plate = int((ang + math.pi) / (2 * math.pi) * 14) % 2 == 0      # brass plates on leather
            c = (176, 128, 46) if plate else (70, 44, 26)
            px[x, y] = tuple(max(0, min(255, int(v * lit))) for v in c) + (255,)
BUCKLE = ["ooooooo", "oBBBBBo", "oB...Bo", "oB...Bo", "oBBBBBo", "ooooooo"]
for j_, row in enumerate(BUCKLE):
    for i_, ch in enumerate(row):
        if ch == 'o': px[12 + i_, 23 + j_] = (64, 42, 14, 255)
        elif ch == 'B': px[12 + i_, 23 + j_] = (240, 200, 104, 255) if i_ + j_ < 5 else (180, 132, 52, 255)
im.save(os.path.join(G, '44546.png'))
