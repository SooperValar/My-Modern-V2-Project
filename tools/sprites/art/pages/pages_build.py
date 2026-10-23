#!/usr/bin/env python3
"""Torn page sprites for Lab 11's drowned tome.

    pages_build.py <source image> <out dir> [first sprite=18170]

Cuts the page out of its plain background, tears it into four pieces along two
jagged lines (one roughly vertical, one roughly horizontal) and draws one
sprite for every combination of pieces a player can hold: the item's page mask
1..14 (bit 0 = page 1 ... bit 3 = page 4) uses sprite first+mask-1. Mask 15 is
the whole tome, which has its own item.

Pieces keep their place in the page, so collected pieces look like the page
coming back together; the torn edges get a thin pale fibre line.
"""
import sys, os
from collections import deque
import numpy as np
from PIL import Image, ImageFilter

src, outdir = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 18170
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(7)

# --- cut out the page (flood the background in from the edges) ---
a = np.array(Image.open(src).convert('RGB')).astype(int)
H, W = a.shape[:2]
bgc = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
dist = np.sqrt(((a - bgc) ** 2).sum(-1))
# the page is warm (red > blue); the background and its shadow are cool
warm = (a[..., 0] - a[..., 2]) > 25
bg = np.zeros((H, W), bool)
q = deque([(0, x) for x in range(W)] + [(H-1, x) for x in range(W)] + [(y, 0) for y in range(H)] + [(y, W-1) for y in range(H)])
while q:
    y, x = q.popleft()
    if bg[y, x] or warm[y, x] and dist[y, x] > 38:
        continue
    bg[y, x] = True
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y+dy, x+dx
        if 0 <= ny < H and 0 <= nx < W and not bg[ny, nx]:
            q.append((ny, nx))
page = ~bg
# drop specks
m = Image.fromarray((page*255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
page = np.array(m) > 127
ys, xs = np.nonzero(page)
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
a = a[y0:y1+1, x0:x1+1]; page = page[y0:y1+1, x0:x1+1]
H, W = page.shape

# --- two jagged tear lines through the middle ---
def tear(n, centre, amp):
    """random walk of n points around centre, jagged at two scales"""
    v = np.cumsum(rng.normal(0, 1.0, n)); v -= np.linspace(v[0], v[-1], n)
    v = v / (np.abs(v).max() + 1e-9) * amp
    # ragged at a scale that survives shrinking: smoothed noise, a few px of sprite
    jag = rng.normal(0, 1.0, n)
    k = np.hanning(41); jag = np.convolve(jag, k/k.sum(), 'same')
    jag = jag / (np.abs(jag).max() + 1e-9) * amp*0.45
    return centre + v + jag

# ink: thicken the writing so a few strokes survive at 32x32
lum = a.mean(-1)
ink = (lum < 95) & ((a[..., 0] - a[..., 2]) > 30)
inkm = Image.fromarray((ink*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(2))
inkw = np.array(inkm).astype(float)[..., None] / 255.0
# calm the stains a little so the paper reads as one sheet, then lay the ink on top
a = np.array(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.MedianFilter(9))).astype(int)
a = (a*0.75 + np.array([226, 200, 150])*0.25).astype(int)
a = (a*(1-0.85*inkw) + np.array([78, 40, 22])*0.85*inkw).astype(int)

cx, cy = W*0.5, H*0.5
vx = tear(H, cx, W*0.08)   # x of the vertical tear for each row
hy = tear(W, cy, H*0.08)   # y of the horizontal tear for each column
Y, X = np.mgrid[0:H, 0:W]
right = X > vx[Y]
lower = Y > hy[X]
piece = right.astype(int) + 2*lower.astype(int)   # 0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right
gap = (np.abs(X - vx[Y]) < 14) | (np.abs(Y - hy[X]) < 14)
fibre = ((np.abs(X - vx[Y]) < 30) | (np.abs(Y - hy[X]) < 30)) & ~gap

def compose(mask):
    keep = page & ~gap & np.isin(piece, [i for i in range(4) if mask & (1 << i)])
    rgb = a.copy()
    edge = keep & fibre
    rgb[edge] = (rgb[edge]*0.5 + np.array([240, 228, 200])*0.5).astype(int)   # pale torn fibres
    img = Image.fromarray(np.dstack([rgb.astype(np.uint8), (keep*255).astype(np.uint8)]), 'RGBA')
    return img

full_scale = 28 / max(W, H)
for mask in range(1, 15):
    img = compose(mask)
    bb = img.getbbox(); img = img.crop(bb)
    s = min(28 / max(img.width, img.height), full_scale*1.45)   # single pieces drawn a bit bigger
    sm = img.resize((max(1, round(img.width*s)), max(1, round(img.height*s))), Image.LANCZOS)
    ar = np.array(sm).astype(int)
    ar[..., 3] = np.where(ar[..., 3] > 110, 255, 0)
    ar[..., 0] = (ar[..., 0] >> 3) << 3; ar[..., 1] = (ar[..., 1] >> 2) << 2; ar[..., 2] = (ar[..., 2] >> 3) << 3
    sm = Image.fromarray(ar.astype(np.uint8), 'RGBA')
    c = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    c.paste(sm, ((32 - sm.width)//2, (32 - sm.height)//2), sm)
    c.save(os.path.join(outdir, '%d.png' % (first + mask - 1)))
    if mask == 14:
        compose(15).save(os.path.join(outdir, 'torn_full_preview.png'))
print('sprites %d-%d' % (first, first+13))
