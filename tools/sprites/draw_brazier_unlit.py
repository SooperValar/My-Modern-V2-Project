#!/usr/bin/env python3
"""Unlit brazier for Lab 11: the 'Fire in Bowl' sprite 16510 with the fire put out
(flames removed, cold ash with a few embers in the bowl, rim darkened).
    draw_brazier_unlit.py <16510.png exported with export_sprites.py> <client gfx folder>
Writes gfx/18129.png."""
import os, sys
from PIL import Image

im = Image.open(sys.argv[1]).convert('RGBA'); px = im.load(); W, H = im.size
out = im.copy(); po = out.load()
for y in range(min(H, 38)):
    for x in range(W):
        r, g, b, a = px[x, y]
        if a == 0: continue
        lum = (r*3 + g*6 + b) / 10
        flame = r > 200 and g > 120
        inside = ((x-15.5)/13.5)**2 + ((y-31)/5.2)**2 < 1.0
        if flame and not inside: po[x, y] = (0, 0, 0, 0); continue
        if inside and r > b + 25:
            v = int(22 + lum*0.10); po[x, y] = (v+4, v+2, v, 255); continue
        if lum > 45:
            v = lum*0.45; po[x, y] = (int(v*1.15), int(v), int(v*0.85), 255)
for x, y in ((13, 31), (18, 32), (16, 30)):
    po[x, y] = (140, 50, 15, 255)
out.save(os.path.join(sys.argv[2], '18129.png'))
