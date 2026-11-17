#!/usr/bin/env python3
"""Wall decorations for all four walls (Nov 16, Cody). The game draws items at full height even with hide-walls (F6), so a
picture on the far side of a wall (wall to the north or east of its tile) shows up there: it needs its back. Directions
are named by where the WALL is, as the game places them: S = wall to the south (the picture on the tile's upper-right
edge, seen from the front), W = wall to the west (upper-left edge, front), N = wall to the north (lower-left edge, seen
from behind), E = wall to the east (lower-right edge, from behind). N and E are hidden behind the wall in normal view.
The game already has: pictures / framed mirror S only; round mirrors 16553 S, 16552 W; shields 16554 / 16556 S,
16555 / 16557 W; bookshelves 16908 / 16909 S, 16897 / 16898 / 16910 / 16911 W; Skeletons in Chains all four (620 S,
622 W, 624 E, 626 N). Shrines (temple 792, Seyan'Du 914): a box; their statue faces S.
Made here (48000-48025, Claude's range): the framed mirror 1246 raised to hang like the pictures; W pictures; N / E backs
of pictures, mirrors, shields, bookshelves (plain back panel); bookshelves 16910 / 16911 for S; shrines W / N / E.
    wall_decor.py <folder with the game's sprites as NNNNN.png> <out folder>"""
import sys, json, random, os
import numpy as np
from PIL import Image, ImageOps
SRC, OUT = sys.argv[1], sys.argv[2]
random.seed(16)
def ld(n): return np.array(Image.open(os.path.join(SRC, '%05d.png' % n)).convert('RGBA')).astype(float)
def shift(a, dx, dy, w=None):
    """move the picture by dx, dy inside a canvas w wide (centred on the old one), same height, bottom kept"""
    h, ow = a.shape[:2]; w = w or ow
    out = np.zeros((h, w, 4)); ox = (w - ow) // 2 + dx
    for y in range(h):
        ty = y + dy
        if not 0 <= ty < h: continue
        for x in range(ow):
            tx = x + ox
            if 0 <= tx < w and a[y, x, 3] > 0: out[ty, tx] = a[y, x]
    return out
mirror = lambda a: a[:, ::-1].copy()
op = lambda a: a[..., 3] > 0
def edge(m):
    e = np.zeros_like(m)
    e[1:-1, 1:-1] = m[1:-1, 1:-1] & ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
    return e | (m & (np.pad(~m, 1)[1:-1, 1:-1]))
def board(a, base=(92, 62, 36), rim=(58, 38, 22), stripe='v'):
    """the back of a flat thing: its outline, a wooden backboard, a darker rim, plank seams"""
    m = op(a); out = np.zeros_like(a); e = edge(m)
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        c = np.array(base, float) * random.uniform(.9, 1.06)
        if (x - xs.min()) % 5 == 0: c *= .78            # plank seams
        out[y, x, :3] = c; out[y, x, 3] = 255
    out[e, :3] = rim
    return out
S = {}
def save(n, a, name):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, '%05d.png' % n)); S[n] = name
N0 = 48000
# --- the framed mirror 1246 hung like the pictures (572: x 14-31, y 8-47)
m1246 = shift(ld(1246), 8, -16); save(N0, m1246, 'Mirror (framed), hung like the pictures, wall S')
pics = [(572, ld(572), 'Picture of Misty Plains'), (580, ld(580), 'Picture of Sunset'), (1246, m1246, 'Mirror (framed)')]
k = N0 + 1
for s, a, name in pics: save(k, mirror(a), name + ', wall W'); k += 1                       # 48001-48003
for s, a, name in pics: save(k, shift(board(a), -16, 8, 64), name + ', back, wall N'); k += 1  # 48004-48006
for s, a, name in pics: save(k, shift(board(mirror(a)), 16, 8, 64), name + ', back, wall E'); k += 1  # 48007-48009
# --- round mirrors: the frame stays, the glass becomes the backboard
def mirror_back(a):
    out = a.copy(); m = op(a)
    hsv = np.array(Image.fromarray(a.astype(np.uint8), 'RGBA').convert('RGB').convert('HSV')).astype(float)
    glass = m & (hsv[..., 1] < 60)
    out[glass, :3] = np.array([70, 48, 30]) * np.random.uniform(.85, 1.05, (glass.sum(), 1))
    return out
save(k, shift(mirror_back(ld(16553)), -16, 8, 64), 'Mirror (round), back, wall N'); k += 1    # 48010
save(k, shift(mirror_back(ld(16552)), 16, 8, 64), 'Mirror (round), back, wall E'); k += 1     # 48011
# --- shields: the rim from the front, a leather back with two straps
def shield_back(a):
    m = op(a); out = np.zeros_like(a); e = edge(m)
    lum = a[..., :3].mean(-1) / 255
    ys, xs = np.nonzero(m); cy = (ys.min() + ys.max()) / 2
    for y, x in zip(ys, xs):
        c = np.array([88, 60, 38]) * (.75 + .5 * lum[y, x])
        if abs(y - (cy - 5)) < 1.2 or abs(y - (cy + 5)) < 1.2: c = np.array([52, 34, 20])     # straps
        out[y, x, :3] = c; out[y, x, 3] = 255
    out[e] = a[e]                                                                                 # the metal rim
    return out
for s, name in ((16554, 'Shield (black)'), (16556, 'Shield (gold)')):
    save(k, shift(shield_back(ld(s)), -16, 8, 64), name + ', back, wall N'); k += 1
    save(k, shift(shield_back(ld(s + 1)), 16, 8, 64), name + ', back, wall E'); k += 1           # 48012-48015
# --- bookshelves: S for the two W-only ones; the back panel (no books) for N and E
save(k, mirror(ld(16910)), 'Bookshelf (book of wisdom), wall S'); k += 1                       # 48016
save(k, mirror(ld(16911)), 'Bookshelf (book of wisdom taken), wall S'); k += 1                 # 48017
def plain(a, face):
    """the face with the books (mask) becomes plain marble, from the bright pixels of the shelf itself"""
    out = a.copy(); m = op(a); e = edge(m)
    lum = a[..., :3].mean(-1); sat = a[..., :3].max(-1) - a[..., :3].min(-1)
    marble = [tuple(a[y, x, :3]) for y, x in zip(*np.nonzero(m & (lum > 175) & (sat < 25)))]
    ys, xs = np.nonzero(face & m & ~e)
    for y, x in zip(ys, xs):
        if lum[y, x] < 175 or sat[y, x] > 25: out[y, x, :3] = random.choice(marble)
    return out
s_shelf = ld(16908); fx = np.zeros(s_shelf.shape[:2], bool); fx[:, 9:25] = True; fx[:4] = False
save(k, shift(plain(s_shelf, fx), -9, 4), 'Bookshelf, back, wall N'); k += 1                   # 48018
w_shelf = ld(16897); fx = np.zeros(w_shelf.shape[:2], bool); fx[:, 7:23] = True; fx[:4] = False
save(k, shift(plain(w_shelf, fx), 9, 4), 'Bookshelf, back, wall E'); k += 1                    # 48019
# --- shrines: the box stays (lit from the upper left like everything), what stands on top turns
def top_mask(a):
    h, w = a.shape[:2]; t = np.zeros((h, w), bool)
    for x in range(w):
        yf = 30 + 0.5 * x if x < 16 else 38 - 0.5 * (x - 16)      # the box's top front edges
        t[:int(yf), x] = True
    return t
for s, name in ((792, 'Shrine (temple)'), (914, "Seyan'Du Shrine")):
    a = ld(s); t = top_mask(a); mi = mirror(a)
    w_ = a.copy(); w_[t] = mi[t]
    save(k, w_, name + ', facing W'); k += 1
    back = mi.copy(); stat = t & op(mi); stat[22:] = False
    back[stat, :3] *= .62
    nb = a.copy(); nb[t] = back[t]; save(k, nb, name + ', from behind (wall N)'); k += 1
    eb = a.copy(); dk = a.copy(); st2 = t & op(a); st2[22:] = False; dk[st2, :3] *= .62
    eb[t] = dk[t]; save(k, eb, name + ', from behind (wall E)'); k += 1                            # 48020-48025
json.dump({str(n): v for n, v in S.items()}, open(os.path.join(OUT, 'wall_decor.json'), 'w'), indent=1)
print(len(S), min(S), max(S))
