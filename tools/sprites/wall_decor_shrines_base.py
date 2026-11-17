"""Nov 16, third pass (Cody: the shrines looked like poor recolours; the plain back, lit like the game, is right):
every shrine version keeps the game's light - the face seen down-left bright, the one seen down-right dark.
W: the decorated front on the dark side (its relief faint in the shade), a plain bright gold side, the statue moved
to the other corner (moved, not mirrored, so its own light stays). Backs (N, E): plain gold sides, the statue in shadow."""
import random, numpy as np
from PIL import Image
random.seed(7)
def ld(n): return np.array(Image.open('%05d.png' % n).convert('RGBA')).astype(float)
def save(n, a): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save('out/%05d.png' % n)
def regions():
    L = np.zeros((64, 32), bool); R = np.zeros((64, 32), bool); T = np.zeros((64, 32), bool)
    for x in range(32):
        if x < 16: yf, yb = 30 + .5 * x, 56 + .5 * x
        else: yf, yb = 38 - .5 * (x - 16), 64 - .5 * (x - 16)
        for y in range(64):
            if y < yf: T[y, x] = True
            elif y < yb: (L if x < 16 else R)[y, x] = True
    return L, R, T
LF, RF, TOP = regions()
def plain_left(a):
    out = a.copy()
    for y, x in zip(*np.nonzero(LF & (a[..., 3] > 0))):
        yf, yb = 30 + .5 * x, 56 + .5 * x
        rim = x < 1 or y < yf + 2 or y > yb - 2 or x > 14
        g = random.uniform(.93, 1.03)
        out[y, x, :3] = (160, 136, 0) if rim else (212 * g, 182 * g, 0)
    return out
def dark_right(a, relief):
    """the dark side; relief: the decorated front's pattern (from the bright face), faint"""
    out = a.copy()
    for y, x in zip(*np.nonzero(RF & (a[..., 3] > 0))):
        base = np.array([22, 16, 0.])
        if relief is not None:
            sx, sy = 31 - x, y - 8 + int(round(.5 * ((31 - x) - x) * 0))      # the left face's pixel at the mirrored spot
            sy = int(round(y - (38 - .5 * (x - 16)) + 30 + .5 * sx))
            if 0 <= sy < 64 and LF[sy, sx] and relief[sy, sx, 3] > 0:
                base = base + (relief[sy, sx, :3] - np.array([200, 170, 0])) * .22
        out[y, x, :3] = np.clip(base, 0, 255)
    return out
def statue_mask(a):
    m = TOP & (a[..., 3] > 0); m[26:] = False        # what stands up above the box (not the top face, not the bowl)
    ys, xs = np.nonzero(m)
    # keep the tallest connected part: the statue's columns
    cols = [x for x in range(32) if m[:, x].any() and np.nonzero(m[:, x])[0].min() < 20]
    sm = np.zeros_like(m)
    if cols:
        x0, x1 = min(cols) - 1, max(cols) + 1
        sm[:, x0:x1 + 1] = TOP[:, x0:x1 + 1] & (a[:, x0:x1 + 1, 3] > 0); sm[30:] = False
    return sm
def move_statue(a, dark=1.0):
    """the statue (and anything at its corner) moved to the mirrored corner, keeping its own light"""
    out = a.copy(); sm = statue_mask(a)
    ys, xs = np.nonzero(sm)
    if not len(xs): return out
    # what lies under it: the top face, from the mirrored top (the bowl / top face are near-symmetric)
    mi = a[:, ::-1]
    out[sm] = mi[sm] if True else out[sm]
    out[sm & ~(mi[..., 3] > 0)] = 0
    dx = (31 - xs.max()) - xs.min()
    for y, x in zip(ys, xs):
        nx = x + dx
        if 0 <= nx < 32:
            out[y, nx] = a[y, x]; out[y, nx, :3] = a[y, x, :3] * dark
    return out
def darken_statue(a, k):
    out = a.copy(); sm = statue_mask(a); out[sm, :3] *= k; return out
for i, s in enumerate((792, 914)):
    a = ld(s)
    w = move_statue(dark_right(plain_left(a), a))
    save(48020 + 3 * i, w)
    back = dark_right(plain_left(a), None)
    save(48021 + 3 * i, move_statue(back, .55))
    save(48022 + 3 * i, darken_statue(back, .55))
print('ok')
