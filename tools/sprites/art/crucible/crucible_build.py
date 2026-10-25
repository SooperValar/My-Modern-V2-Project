#!/usr/bin/env python3
"""Soul Crucible sprites from one generated picture (source_crucible.png).

    crucible_build.py <source> <out dir> [first=18220]

Three ranks x three states:  sprite = first + rank*3 + state
  rank  0 Lesser (pale blue), 1 Soul Crucible (violet), 2 Greater (gold)
  state 0 empty (the bowl dark, the star only tinted), 1 one stone in (faint glow), 2 full (bright)
The background (warm, plain) is cut away; the steam above the bowl goes with it.
The glow inside the bowl and the carved star are found by colour (both bluish) and
recoloured per rank.
"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src, out = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 18220
os.makedirs(out, exist_ok=True)

a = np.array(Image.open(src).convert('RGB')).astype(float)
H, W = a.shape[:2]
r, g, b = a[..., 0], a[..., 1], a[..., 2]

# object: everything not warm (the background and its shadow are orange/brown)
obj = (r - b) < 45
obj = ndimage.binary_opening(obj, iterations=3)
lab, n = ndimage.label(obj)
sizes = ndimage.sum(obj, lab, range(1, n+1))
obj = lab == (1 + int(np.argmax(sizes)))          # the crucible only (no steam, no specks)
obj = ndimage.binary_fill_holes(obj)

# cut the steam: nothing above the rim (the first row where the crucible is wide)
widths = obj.sum(1)
rim = int(np.argmax(widths > 0.6 * widths.max()))
obj[: max(0, rim - int(0.02 * H))] = False
lab, n = ndimage.label(obj)
sizes = ndimage.sum(obj, lab, range(1, n+1))
obj = lab == (1 + int(np.argmax(sizes)))

ys, xs = np.nonzero(obj)
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()

# the bowl's inside: bluish and bright, in the upper part
lum = a.mean(-1)
blue = (b - r) > 10
top = np.zeros_like(obj); top[: y0 + int((y1 - y0) * 0.30)] = True
bowl = obj & top & blue & (lum > 70)
bowl = ndimage.binary_closing(bowl, iterations=10)
bowl = ndimage.binary_fill_holes(bowl) & obj & top
glow_w = np.clip((lum - 80) / 120, 0, 1) * bowl     # how strongly each bowl pixel glows

# the carved star: bluish dark-ish, around the middle of the body
mid = np.zeros_like(obj)
mid[y0 + int((y1 - y0) * 0.35): y0 + int((y1 - y0) * 0.85), x0 + int((x1 - x0) * 0.25): x1 - int((x1 - x0) * 0.25)] = True
star = obj & mid & ((b - r) > 12) & (lum < 120)
star = ndimage.binary_opening(star, iterations=1)
lab, n = ndimage.label(star)
if n:
    sizes = ndimage.sum(star, lab, range(1, n+1))
    star = lab == (1 + int(np.argmax(sizes)))
star = ndimage.binary_dilation(star, iterations=2) & obj

COLORS = [(150, 205, 255), (195, 125, 255), (255, 205, 80)]
STATES = [0.0, 0.4, 1.0]

def make(rank, state):
    c = np.array(COLORS[rank], float)
    s = STATES[state]
    grey = a.mean(-1, keepdims=True)
    img = grey * 0.85 + a * 0.15            # neutral grey stone (no blue cast, fits every glow colour)
    # bowl: dark and grey when empty, the rank colour when filled
    w = glow_w[..., None]
    dark = grey * 0.30
    lit = dark + (c * (0.45 + 0.55 * w)) * s + 0 * img
    bw = bowl[..., None]
    img = np.where(bw, dark * (1 - s) + lit * 1.0 if s else dark, img)
    if s:
        img = np.where(bw, np.clip(dark + c * (0.35 + 0.65 * w) * s, 0, 255), img)
    # star: dull stone when empty, glowing rank colour otherwise
    sw = star[..., None]
    if s:
        img = np.where(sw, np.clip(grey * 0.4 + c * (0.35 + 0.65 * s), 0, 255), img)
    else:
        img = np.where(sw, np.clip(grey * 0.55 + c * 0.30, 0, 255), img)   # a faint hint of the rank colour
    rgba = np.dstack([img.clip(0, 255).astype(np.uint8), (obj * 255).astype(np.uint8)])
    im = Image.fromarray(rgba, 'RGBA').crop((x0, y0, x1 + 1, y1 + 1))
    sc = 28 / max(im.width, im.height)
    sm = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
    ar = np.array(sm).astype(int)
    ar[..., 3] = np.where(ar[..., 3] > 110, 255, 0)
    ar[..., 0] = (ar[..., 0] >> 3) << 3; ar[..., 1] = (ar[..., 1] >> 2) << 2; ar[..., 2] = (ar[..., 2] >> 3) << 3
    sm = Image.fromarray(ar.astype(np.uint8), 'RGBA')
    cv = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    cv.paste(sm, ((32 - sm.width) // 2, 32 - sm.height - 1), sm)   # standing on the bottom
    return cv, Image.fromarray(rgba, 'RGBA').crop((x0, y0, x1 + 1, y1 + 1))

big = []
for rank in range(3):
    for state in range(3):
        cv, full = make(rank, state)
        cv.save(os.path.join(out, '%d.png' % (first + rank * 3 + state)))
        big.append(full)
# preview of the big versions (checks the masks)
pw = Image.new('RGBA', (3 * 260, 3 * 260), (40, 44, 52, 255))
for k, im in enumerate(big):
    t = im.copy(); t.thumbnail((250, 250))
    pw.paste(t, ((k % 3) * 260 + 5, (k // 3) * 260 + 5), t)
pw.save(os.path.join(out, 'preview_big.png'))
print('sprites %d-%d; bowl px %d, star px %d' % (first, first + 8, bowl.sum(), star.sum()))
