#!/usr/bin/env python3
"""Emerald armor had no "special" sprite (the old modded armor used the other piece's
picture by mistake). Copy the red gem emblem from the crystal pieces' special sprites
onto the emerald helmet and armor:  18210 emerald helmet, 18211 emerald armor.
Run from tools/world (uses sprload.py's loader from ~/tq); writes into the client GFX folder."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/tq'))
from sprload import load
import numpy as np
from PIL import Image
out = os.path.expanduser('~/mnt/Client/GFX')
for base, plain_c, special_c, new in ((16780, 1540, 850, 18210), (16775, 1555, 855, 18211)):
    A = np.array(load(plain_c)).astype(int); B = np.array(load(special_c)).astype(int)
    emb = (np.abs(A[..., :3] - B[..., :3]).sum(-1) > 30) & (B[..., 3] > 0)
    ys, xs = np.nonzero(emb)
    y0, y1, x0, x1 = ys.min()-1, ys.max()+1, xs.min()-1, xs.max()+1   # the emblem and its rim
    E = np.array(load(base)).copy()
    box = np.zeros_like(emb); box[y0:y1+1, x0:x1+1] = True
    m = box & (np.abs(A[..., :3] - B[..., :3]).sum(-1) > 10) & (B[..., 3] > 0)
    E[m] = B[m].astype(np.uint8)
    Image.fromarray(E, 'RGBA').save(os.path.join(out, '%d.png' % new))
    print(new, 'from', base, 'emblem pixels', int(m.sum()))
