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
def head(nr, src):
    im = Image.open(os.path.join(G, '%05d.png' % src)).convert('RGBA'); bb = im.getbbox()
    w = bb[2] - bb[0]; top = im.crop((bb[0], bb[1], bb[2], bb[1] + max(8, int((bb[3] - bb[1]) * 0.24)))); bb2 = top.getbbox(); top = top.crop(bb2)
    k = min(26 / top.width, 26 / top.height); top = top.resize((max(1, int(top.width * k)), max(1, int(top.height * k))), Image.NEAREST)
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); out.alpha_composite(top, ((32 - top.width) // 2, 31 - top.height - 1))
    px = out.load()                                     # a dark red stump under the neck
    for x in range(32):
        if px[x, 29][3] or px[x, 28][3]: px[x, 30] = (110, 20, 20, 255)
    out.save(os.path.join(G, '%05d.png' % nr))
head(44524, 50000 + 40); head(44525, 50500 + 40)
icon(44526, os.path.join(R2, 'Coin_Star.obj'), '--size', 17, '--yaw', 20, '--bright', 2, '--recol', 'Gold=c9a227')
icon(44527, os.path.join(FP, 'Dummy.gltf'), '--size', 26, '--yaw', 30)
icon(44528, os.path.join(FP, 'Rope_3.gltf'), '--size', 24, '--yaw', 30, '--tint', 'c8d2dc', '--mix', 0.85)
icon(44529, os.path.join(R2, 'Pouch.obj'), '--size', 20, '--yaw', 25, '--bright', 2)
icon(44530, os.path.join(R2, 'Ring2.obj'), '--size', 13, '--bright', 2.2, '--recol', 'Golden=5fa8d8')
icon(44532, os.path.join(R2, 'Potion2_Filled.obj'), '--size', 20, '--glass', '203050', '--liquid', '70c8ff')
# the belt: the game's studded belt picture (Harlan's, 44517), leather in sea green
im = Image.open(os.path.join(G, '44517.png')).convert('RGBA'); px = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, a = px[x, y]
        if a and r > g > b and r - b > 25: l = (r + g + b) / 3 / 255; px[x, y] = (int(40 + 60 * l), int(90 + 150 * l), int(100 + 150 * l), a)
im.save(os.path.join(G, '44531.png'))
print('done')
