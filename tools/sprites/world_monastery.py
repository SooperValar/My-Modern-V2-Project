#!/usr/bin/env python3
"""Pieces for the Monastery of the Still Hand (Nov 19), from Cody's "3d Models/Fantasy Props" (glrender, like
world_foundry.py), and frozen-pond ice.

World objects (32x64; each N+1 its hide-walls form, the same picture):
  38467 practice dummy (Kesh's hall)    38469 bookcase (the library)    38471 book stand with an open book
  38473 triple candlestick (the chapel, the sanctum)    38475 bench (refectory, chapel)    38477 pot (the cells)
Ground: ice 37528-37531 (the Still Pond, frozen: pale blue-white with cracks and frost; walkable).  Next free: 37532,
objects 38479.

    world_monastery.py <client folder> [--out <folder>] [--sheet <png>]"""
import math, os, random, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import glrender as G, world_ground as wg
from world_foundry import prop
D = os.path.join(os.path.expanduser('~/mnt/MyV2/3d Models'), 'Fantasy Props') + os.sep
OBJ = {38467: ('Dummy', 30, 1.0), 38469: ('Bookcase_2', 45, 0.85), 38471: ('BookStand', 35, 1.0),
       38473: ('CandleStick_Triple', 20, 1.8), 38475: ('Bench', 45, 0.55), 38477: ('Pot_1', 20, 1.0)}


def ice(seed):
    r = random.Random(seed); im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
    ph = [r.random() * 6.28 for _ in range(4)]
    for y in range(17, 32):
        for x in range(32):
            if not wg.IN(x, y): continue
            u, v = wg.local(x, y)
            n = 0.5 + 0.25 * math.sin(6.28 * u + ph[0]) * math.sin(6.28 * v + ph[1]) + 0.15 * math.sin(6.28 * (u + v) + ph[2])
            c = (168 + 50 * n, 196 + 40 * n, 222 + 28 * n)
            if r.random() < 0.06: c = (240, 248, 255)                                      # frost glints
            px[x, y] = tuple(int(min(255, k)) for k in c) + (255,)
    d = ImageDraw.Draw(im)
    for _ in range(2):                                                                      # cracks
        x, y = r.uniform(4, 28), r.uniform(19, 30)
        for _ in range(5):
            nx, ny = x + r.uniform(-4, 4), y + r.uniform(-2, 2)
            if wg.IN(int(nx), int(ny)) and wg.IN(int(x), int(y)): d.line([(x, y), (nx, ny)], fill=(120, 150, 180, 255))
            x, y = nx, ny
    return im


def main():
    a = sys.argv[1:]; client = a[0]
    out = a[a.index('--out') + 1] if '--out' in a else wg.gfx_dir(client)
    os.makedirs(out, exist_ok=True); made = {}
    for n, (name, yaw, sc) in OBJ.items():
        im = prop(G.Model(D + name + '.gltf'), yaw=yaw, scale=sc)
        for k in (n, n + 1): im.save(os.path.join(out, '%d.png' % k))
        made[n] = im
    for k in range(4): ice(37528 + k).save(os.path.join(out, '%d.png' % (37528 + k)))
    if '--sheet' in a:
        sh = Image.new('RGBA', (len(made) * 40 + 4 * 40, 80), (205, 212, 220, 255))
        for i, im in enumerate(made.values()): sh.alpha_composite(im, (i * 40 + 4, 8))
        for k in range(4): sh.alpha_composite(Image.open(os.path.join(out, '%d.png' % (37528 + k))).convert('RGBA'), ((len(made) + k) * 40 + 4, 40))
        sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(a[a.index('--sheet') + 1])
    print('monastery pieces: objects 38467-38478, ice 37528-37531')


if __name__ == '__main__':
    main()
