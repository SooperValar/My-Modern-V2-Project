#!/usr/bin/env python3
"""Item pictures for the Ashen Fields (Nov 18), sprites 44547-44550 into <client>/GFX:
    ashen_fields.py <client folder> <3d Models folder>
44547 Ember of the First Flame (Crystal1: a glowing amber-orange crystal), 44548 Ashra's Ash-Veil (drawn: a folded grey
veil, its hem singed orange), 44549 Ring of Embers (Ring6: a soot-dark band, an ember stone), 44550 Fireward Draught
(Potion7: a flask of fiery orange)."""
import os, subprocess, sys, math, random
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); C, M = sys.argv[1], sys.argv[2]
G = os.path.join(C, 'GFX'); ICON = os.path.join(HERE, '..', 'item_icon.py'); R2 = os.path.join(M, 'RPG Pack 2', 'OBJ')
def icon(nr, model, *a): subprocess.run([sys.executable, ICON, model, os.path.join(G, '%05d.png' % nr)] + [str(x) for x in a], check=True)
icon(44547, os.path.join(R2, 'Crystal1.obj'), '--size', 20, '--yaw', 30, '--bright', 3.0, '--recol', 'Purple=ff4a0a')
icon(44549, os.path.join(R2, 'Ring6.obj'), '--size', 14, '--yaw', 25, '--bright', 2.2, '--recol', 'Golden=4a4242,Green=ff6418')
icon(44550, os.path.join(R2, 'Potion7_Filled.obj'), '--size', 20, '--glass', '203050', '--liquid', 'e8501c')
# ---- 44548 Ashra's Ash-Veil: a folded veil of grey gauze lying on the ground, soft folds, the hem singed orange-black
r = random.Random(44548); im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 13.0, (y - 20.0) / 8.5
        edge = 1 + 0.10 * math.sin(math.atan2(dy, dx) * 5 + 1.3)
        rr = math.hypot(dx, dy)
        if rr > edge: continue
        fold = 0.5 + 0.5 * math.sin((x - y * 0.6) * 0.9)                     # diagonal folds
        lit = 0.72 + 0.28 * fold - 0.15 * dy
        g = int(150 * lit); c = [g + 4, g + 2, g]
        if rr > edge - 0.16:                                                  # the singed hem
            c = [200, 90, 30] if r.random() < 0.45 else [60, 40, 34]
        px[x, y] = tuple(max(0, min(255, v)) for v in c) + (215 if rr < edge - 0.16 else 255,)
im.save(os.path.join(G, '44548.png'))
