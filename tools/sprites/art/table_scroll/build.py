#!/usr/bin/env python3
"""Tables with a scroll on them: the open parchment scroll (18140) shrunk onto the four table sprites.
    build.py <client folder>   writes 182NN png files here and preview.png
"""
import os, sys
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {560: 18290, 562: 18291, 1242: 18292, 1244: 18293}   # table sprite -> new sprite
SCALE = 0.62
def load(n): return Image.open(os.path.join(HERE, 'orig', '%05d.png' % n)).convert('RGBA')
sc = load(18140); sc = sc.crop(sc.getbbox())
w, h = round(sc.width * SCALE), round(sc.height * SCALE)
small = sc.resize((w, h), Image.LANCZOS)
a = small.getchannel('A').point(lambda v: 255 if v > 110 else 0); small.putalpha(a)   # hard edge like the game's sprites
sh = Image.new('RGBA', small.size, (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: 90 if v else 0))
res = {}
for t, nr in OUT.items():
    im = load(t)
    bb = im.getbbox()
    cx, cy = 16, 27 + 8          # the middle of the table top (a 32x17 diamond from y 27)
    x, y = cx - w // 2, cy - h // 2 - 1
    im.alpha_composite(sh, (x + 1, y + 1)); im.alpha_composite(small, (x, y))
    im.save(os.path.join(HERE, '%d.png' % nr)); res[nr] = im
S = 5
pv = Image.new('RGBA', (32 * S * 8, 64 * S), (60, 60, 70, 255))
for k, t in enumerate(OUT):
    for j, im in enumerate((load(t), res[OUT[t]])):
        pv.alpha_composite(im.resize((32 * S, 64 * S), Image.NEAREST), ((k * 2 + j) * 32 * S, 0))
pv.save(os.path.join(HERE, 'preview.png'))
print('scroll', w, 'x', h)
