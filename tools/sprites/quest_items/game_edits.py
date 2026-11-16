#!/usr/bin/env python3
"""(Superseded for 44510-44514 / 44518 by the RPG Pack renders, see README.txt; 44521 by greyfang_amulet.py.)
Quest item pictures (Nov 15): the game's own item sprites reworked (colours, studs, a seal face, a fang),
and props from Quaternius's Fantasy Props MegaKit (CC0) rendered with item_icon.py. Out: 44510-44521."""
import numpy as np, colorsys, os, subprocess, sys
from PIL import Image
REF = (sys.argv[1] if len(sys.argv) > 1 else 'items_ref') + '/'   # the game's sprites, exported as <item>_<sprite>.png
def load(name):
    a = np.array(Image.open(REF + name).convert('RGBA')).astype(float)
    mag = (a[..., 0] > 240) & (a[..., 1] < 16) & (a[..., 2] > 240); a[mag, 3] = 0
    return a
def save(a, n): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save('out/%d.png' % n)
def recolor(a, sel, rgb, keep=0.15):    # pixels in sel: their brightness on a new colour
    lum = a[..., :3].mean(-1, keepdims=True) / 255; tc = np.array(rgb, float)
    a[sel, :3] = (np.clip(lum[sel] * 1.25, 0, 1.2) * tc * (1 - keep) + a[sel, :3] * keep)
    return a
op = lambda a: a[..., 3] > 0
def hue(a):
    h = np.zeros(a.shape[:2]); s = np.zeros(a.shape[:2])
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            r, g, b = a[y, x, :3] / 255; hh, ss, vv = colorsys.rgb_to_hsv(r, g, b); h[y, x] = hh; s[y, x] = ss
    return h, s
# 44514 stone axe: the game's axe, the head in slate, a darker haft
a = load('2013_1725.png'); h, s = hue(a)
head = op(a) & (s < 0.25); haft = op(a) & (s >= 0.25)
recolor(a, head, (112, 122, 140)); recolor(a, haft, (92, 66, 44)); save(a, 44514)
# 44516 moonwort: the game's flower, pale silver-blue
a = load('2003_1460.png'); h, s = hue(a)
petal = op(a) & ~((h > 0.17) & (h < 0.45) & (s > 0.3))
ys, xs = np.nonzero(op(a)); x0 = xs.min()
for (dy, dx) in [(-2,1),(-2,2),(-1,0),(-1,1),(-1,2),(-1,3),(0,0),(0,1),(0,2),(0,3),(1,1),(1,2),(1,0)]:
    y, x = 21 + dy, x0 + dx; a[y, x] = (205 + 10*(dy<0), 215 + 10*(dy<0), 245, 255)
a[19, x0+2, :3] = (250, 250, 255); a[20, x0+1, :3] = (250, 250, 255); save(a, 44516)
# 44517 Harlan's studded belt: iron studs along the band
a = load('2004_16665.png'); ys, xs = np.nonzero(op(a)); band = op(a)
cy = int(np.median(ys))
for x in range(xs.min() + 3, xs.max() - 2, 4):
    if band[cy, x] and not (abs(x - (xs.min() + xs.max()) / 2) < 4): a[cy, x, :3] = (215, 215, 220); a[cy - 1, x, :3] = (150, 150, 160)
save(a, 44517)
# 44518 merchant's signet: the gold ring, its red stone made a flat dark seal face
a = load('2005_181.png'); h, s = hue(a)
gem = op(a) & ((h < 0.05) | (h > 0.9)) & (s > 0.4)
a[gem, :3] = (200, 160, 50)
for x in range(14, 19): a[18, x] = (220, 180, 70, 255); a[19, x] = (60, 40, 25, 255); a[20, x] = (90, 60, 35, 255)
a[19, 13] = a[19, 19] = a[20, 13] = a[20, 19] = (200, 160, 50, 255); a[19, 16, :3] = (150, 110, 60)
save(a, 44518)
# 44519 quarryman's amulet: the amulet in grey stone
a = load('2014_1750.png'); recolor(a, op(a), (160, 150, 132)); save(a, 44519)
# 44520 greyfang's fang: the tooth, longer and yellowed
a = load('2018_334.png'); im = Image.fromarray(a.astype(np.uint8), 'RGBA')
bb = im.getbbox(); t = im.crop(bb); t = t.resize((t.width + 1, int(t.height * 1.7)), Image.NEAREST)
c = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); c.paste(t, (16 - t.width // 2, 26 - t.height), t)
a = np.array(c).astype(float); recolor(a, op(a), (236, 222, 170), 0.2); save(a, 44520)
fang = a.copy()
# 44521 greyfang amulet: the gold amulet with the fang hanging from it in place of its stone
a = load('2019_1380.png'); h, s = hue(a)
a[23:] = 0; a[22, 15:18] = (230, 190, 60, 255)
fang = np.clip(fang, 0, 255); fang[fang[...,3]==0]=0; fy, fx = np.nonzero(op(fang)); f = fang[fy.min():fy.max() + 1, fx.min():fx.max() + 1]
fi = Image.fromarray(f.astype(np.uint8), 'RGBA').resize((max(2, f.shape[1]), max(4, int(f.shape[0] * 0.6))), Image.NEAREST)
base = Image.fromarray(a.astype(np.uint8), 'RGBA'); gy = np.nonzero(op(a))[0].max()
fi = Image.fromarray(f.astype(np.uint8), 'RGBA').resize((f.shape[1], min(8, f.shape[0])), Image.NEAREST); base.paste(fi, (16 - fi.width // 2, 23), fi)
base.save('out/44521.png')
# rendered props
R = lambda *a: subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'item_icon.py'), *a], check=True)
R('Book_5.gltf', 'out/44510.png', '--tint', 'b07840', '--mix', '0.85', '--yaw', '25', '--size', '22', '--bright', '2.1')
R('Potion_1.gltf', 'out/44511.png', '--size', '20', '--tint', '40d060', '--mix', '0.6', '--bright', '2.2')
R('Potion_4.gltf', 'out/44512.png', '--tint', 'a8a49a', '--mix', '0.85', '--size', '20', '--bright', '1.9')
R('Coin.gltf', 'out/44513.png', '--size', '15', '--bright', '1.9', '--yaw', '20', '--tint', 'c08a40', '--mix', '0.5')
print('done')
