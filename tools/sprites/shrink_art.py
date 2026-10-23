#!/usr/bin/env python3
"""Turn a large generated image (one object on a plain background) into a game sprite.

    shrink_art.py <source image> <out.png> [size=32] [fit=28] [tolerance=38]

- cuts out the background by flooding in from the image edges (any plain colour works,
  magenta or not; dark parts inside the object are kept),
- shrinks the object to fit a <fit> x <fit> box with high-quality filtering,
- makes the edge hard (no half-transparent pixels, like the original sprites),
- rounds the colours to the client's 16-bit (RGB565) palette,
- centres it on a transparent <size> x <size> canvas.
Writes an RGBA PNG; put it in the client's gfx folder as NNNNN.png under a free number.
Small details vanish at this size, so ask the generator for bold, chunky shapes.
"""
import sys
from collections import deque
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
size = int(sys.argv[3]) if len(sys.argv) > 3 else 32
fit = int(sys.argv[4]) if len(sys.argv) > 4 else 28
tol = float(sys.argv[5]) if len(sys.argv) > 5 else 38

a = np.array(Image.open(src).convert('RGB')).astype(int)
H, W = a.shape[:2]
bgc = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
dist = np.sqrt(((a - bgc) ** 2).sum(-1))
bg = np.zeros((H, W), bool)
q = deque([(0, x) for x in range(W)] + [(H-1, x) for x in range(W)] + [(y, 0) for y in range(H)] + [(y, W-1) for y in range(H)])
while q:
    y, x = q.popleft()
    if bg[y, x] or dist[y, x] > tol:
        continue
    bg[y, x] = True
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y+dy, x+dx
        if 0 <= ny < H and 0 <= nx < W and not bg[ny, nx]:
            q.append((ny, nx))
img = Image.fromarray(np.dstack([a.astype(np.uint8), np.where(bg, 0, 255).astype(np.uint8)]), 'RGBA')
img = img.crop(img.getbbox())
s = min(fit / img.width, fit / img.height)
sm = img.resize((max(1, round(img.width*s)), max(1, round(img.height*s))), Image.LANCZOS)
ar = np.array(sm).astype(int)
ar[..., 3] = np.where(ar[..., 3] > 110, 255, 0)
ar[..., 0] = (ar[..., 0] >> 3) << 3
ar[..., 1] = (ar[..., 1] >> 2) << 2
ar[..., 2] = (ar[..., 2] >> 3) << 3
sm = Image.fromarray(ar.astype(np.uint8), 'RGBA')
canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
canvas.paste(sm, ((size - sm.width)//2, (size - sm.height)//2), sm)
canvas.save(out)
print('%s: %dx%d object on %dx%d' % (out, sm.width, sm.height, size, size))
