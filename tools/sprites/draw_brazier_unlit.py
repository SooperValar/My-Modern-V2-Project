#!/usr/bin/env python3
"""Unlit brazier for Lab 11: the 'Fire in Bowl' sprite 16510 with the fire put out
(flames removed, cold ash with a few embers in the bowl, rim darkened).
    draw_brazier_unlit.py <16510.png exported with export_sprites.py> <client gfx folder>
Writes gfx/18129.png.
The flames covered the back of the bowl; removing them left a bite out of it (the floor showed
through). So the back rim is drawn across again at row 22 and everything below it that the lit
bowl covered is filled with the bowl's dark inside."""
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

# the back of the bowl: rim at row 22, nothing above it (leftover flame tips), ash below
RIM = 22
rimL, rimR = po[9, RIM], po[20, RIM]
for x in range(10, 21):
    for y in range(18, RIM):
        po[x, y] = (0, 0, 0, 0)
    t = (x - 10) / 10
    if po[x, RIM][3] == 0:
        po[x, RIM] = tuple(int(rimL[i]*(1-t) + rimR[i]*t) for i in range(3)) + (255,)
for y in range(RIM + 1, H):
    for x in range(W):
        if po[x, y][3] == 0 and px[x, y][3] > 0:
            v = (x*7 + y*3) % 3 - 1
            po[x, y] = (43 + v*2, 41 + v*2, 38 + v*2, 255)
out.save(os.path.join(sys.argv[2], '18129.png'))
