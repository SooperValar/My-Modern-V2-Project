#!/usr/bin/env python3
"""Two-handed axe sprites in the five metals of the two-handed swords, with damage states.
    axe2h_build.py <render.png> <out folder>
<render.png> is the full-size generated steel axe (back blade already enlarged) on a plain
background. Writes NNNNN.png for each sprite: per metal the perfect sprite and, like the swords,
four worse ones right after it (the server adds 1 to the sprite with every damage state).
Titanium items do not age, so it gets only the perfect sprite."""
import sys, os
import numpy as np
from PIL import Image
from collections import deque
from scipy import ndimage

SRC, OUT = sys.argv[1], sys.argv[2]
FIRST = {'bronze': 18145, 'steel': 18150, 'gold': 18155, 'crystal': 18160, 'titanium': 18165}
TIERS = {   # metal dark / mid / light, end cap colour, colour it ages towards
    'bronze':   ((100, 70, 34), (165, 118, 60), (232, 182, 108), (200, 160, 60), (64, 112, 72)),    # green patina
    'steel':    None,                                                                              # the render itself
    'gold':     ((70, 58, 10), (170, 146, 32), (255, 242, 120), (200, 160, 60), (112, 112, 40)),   # olive tarnish
    'crystal':  ((36, 40, 110), (92, 98, 200), (200, 205, 255), (80, 90, 230), (30, 32, 60)),      # clouds over, darkens
    'titanium': ((4, 4, 6), (30, 30, 36), (96, 96, 110), (28, 28, 32), None),
}
RUST = (150, 62, 38)            # steel rusts red, like the swords

a = np.array(Image.open(SRC).convert('RGB')).astype(int); H, W = a.shape[:2]
bgc = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
dist = np.sqrt(((a-bgc)**2).sum(-1))
bg = np.zeros((H, W), bool)
q = deque([(0, x) for x in range(W)]+[(H-1, x) for x in range(W)]+[(y, 0) for y in range(H)]+[(y, W-1) for y in range(H)])
while q:
    y, x = q.popleft()
    if bg[y, x] or dist[y, x] > 60: continue
    bg[y, x] = True
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y+dy, x+dx
        if 0 <= ny < H and 0 <= nx < W and not bg[ny, nx]: q.append((ny, nx))
obj = ~bg
r, g, b = a[..., 0], a[..., 1], a[..., 2]
obj &= ~((r > g+50) & (b > g+50))                       # magenta fringe
mx = a.max(-1); mn = a.min(-1); sat = (mx-mn)/(mx+1)
yy, xx = np.mgrid[0:H, 0:W]
ys, xs = np.nonzero(obj); diag = (xx-xs.min()) + (yy-ys.min()); span = diag[obj].max()
metal = obj & (sat < 0.18) & (diag < span*0.47)        # head and socket
cap = obj & (diag > span*0.88) & (r > g) & (r > 150)  # brass ring at the end of the haft
wood = obj & ~metal & ~cap
lum = a.mean(-1)
lo, hi = np.percentile(lum[metal], 5), np.percentile(lum[metal], 97)
edge_dist = ndimage.distance_transform_edt(obj)

rng = np.random.default_rng(7)
def noise(scale):                     # smooth blotchy noise 0..1
    n = rng.random((H//scale+2, W//scale+2))
    n = np.array(Image.fromarray((n*255).astype(np.uint8)).resize((W+2*scale, H+2*scale), Image.BICUBIC))[:H, :W]/255.0
    return n
N1, N2, N3 = noise(48), noise(20), noise(9)

def ramp(t, dk, md, lt):
    dk, md, lt = [np.array(c, float) for c in (dk, md, lt)]
    t = t[..., None]
    return np.where(t < 0.5, dk+(md-dk)*(t/0.5), md+(lt-md)*((t-0.5)/0.5))

def render(tier, state):
    img = a.astype(float).copy(); alive = obj.copy()
    t = np.clip((lum-lo)/(hi-lo), 0, 1)
    if TIERS[tier]:
        dk, md, lt, cp, age = TIERS[tier]
        img[metal] = ramp(t, dk, md, lt)[metal]
        img[cap] = (np.array(cp, float)*(0.5+0.7*np.clip(lum/255, 0, 1))[..., None])[cap]
    else:
        age = RUST
    if state:
        s = state/4.0
        # ageing: blotches of rust / patina / tarnish spread over the metal, the shine goes
        blot = (N1*0.6+N2*0.4) < (0.18+0.62*s)
        amt = np.where(blot, 0.35+0.45*s, 0.12*s)[..., None]
        m3 = metal[..., None]
        img = np.where(m3, img*(1-amt)+np.array(age, float)*amt, img)
        img = np.where(m3, img*(1-0.18*s), img)
        # chips out of the cutting edges, more each state
        if state >= 2:
            near = edge_dist < (10+14*state)
            chip = metal & near & (N3 < 0.12*(state-1)) & (diag < span*0.40)
            alive &= ~ndimage.binary_dilation(chip, iterations=3) | ~metal
        # the haft darkens and gets grimy
        w3 = wood[..., None]
        img = np.where(w3, img*(1-0.16*s), img)
    rgba = np.dstack([np.clip(img, 0, 255), alive*255]).astype(np.uint8)
    im = Image.fromarray(rgba, 'RGBA'); im = im.crop(Image.fromarray((obj*255).astype(np.uint8)).getbbox())
    fit = 30; sc = min(fit/im.width, fit/im.height)
    sm = im.resize((round(im.width*sc), round(im.height*sc)), Image.LANCZOS)
    ar = np.array(sm).astype(int); al = ar[..., 3]; ar[..., 3] = np.where(al > 100, 255, 0)
    fr = (al > 100) & (al < 220); ar[..., :3][fr] = (ar[..., :3][fr]*0.65).astype(int)
    ar[..., 0] = (ar[..., 0] >> 3) << 3; ar[..., 1] = (ar[..., 1] >> 2) << 2; ar[..., 2] = (ar[..., 2] >> 3) << 3
    sm = Image.fromarray(ar.clip(0, 255).astype(np.uint8), 'RGBA')
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); out.paste(sm, ((32-sm.width)//2, (32-sm.height)//2), sm)
    return out

os.makedirs(OUT, exist_ok=True)
for tier, first in FIRST.items():
    for state in (range(1) if tier == 'titanium' else range(5)):
        render(tier, state).save(os.path.join(OUT, '%05d.png' % (first+state)))
print('wrote', OUT)
