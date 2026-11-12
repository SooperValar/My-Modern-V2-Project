#!/usr/bin/env python3
"""The two stock pictures of the waypoint travel window (64x32):
18340 "not found yet" (grey, a question mark) and 18341 a found waypoint without a picture of its own.

    draw_waypoint_pics.py <folder with the circle pieces (18310-18318)> <out folder>
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def circle(src, lit=True):          # the nine lit pieces put together (96x48)
    im = Image.new('RGBA', (96, 64), (0, 0, 0, 0))
    for dx in (-1, 0, 1):
        for dy in (1, 0, -1):
            t = np.array(Image.open(os.path.join(src, '%05d.png' % (18310 + (dx + 1) * 3 + dy + 1)))).astype(float)
            a = t[..., 3:4]; t[..., :3] = np.where(a > 0, t[..., :3] * 255 / np.maximum(a, 1), 0)   # un-multiply
            im.alpha_composite(Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)), (48 + 16 * (dx + dy) - 16, 24 + 8 * (dx - dy) - 16))
    return im.crop((0, 8, 96, 56))

def main():
    src, out = sys.argv[1], sys.argv[2]
    rs = np.random.RandomState(4)
    c = circle(src)
    # 18341: the lit circle on dark stone
    g = (rs.rand(32, 64) * 14 + 22).astype(np.uint8)
    im = Image.fromarray(np.dstack([g, g, (g * 1.25).astype(np.uint8)]), 'RGB').convert('RGBA')
    im.alpha_composite(c.resize((60, 30), Image.LANCZOS), (2, 1))
    im.convert('RGB').save(os.path.join(out, '18341.png'))
    # 18340: grey, the circle barely there, a question mark
    g = (rs.rand(32, 64) * 16 + 34).astype(np.uint8)
    im = Image.fromarray(np.dstack([g, g, g]), 'RGB').convert('RGBA')
    d = c.resize((60, 30), Image.LANCZOS).convert('LA').convert('RGBA'); d.putalpha(d.getchannel('A').point(lambda v: v // 4))
    im.alpha_composite(d, (2, 1))
    dr = ImageDraw.Draw(im)
    try: f = ImageFont.load_default(size=30)
    except TypeError: f = ImageFont.load_default()
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)): dr.text((32 + ox, 15 + oy), '?', font=f, fill=(20, 20, 20, 255), anchor='mm')
    dr.text((32, 15), '?', font=f, fill=(235, 235, 235, 255), anchor='mm')
    im.convert('RGB').save(os.path.join(out, '18340.png'))

if __name__ == '__main__':
    main()
