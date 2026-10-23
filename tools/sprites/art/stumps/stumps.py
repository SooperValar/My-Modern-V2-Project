#!/usr/bin/env python3
"""Low "hidden" versions of the trees for the client's Hide mode (F6), like the walls'
low blocks: the tree is cut down to a short stump with a pale cut face; leaves go.
    stumps.py <out dir> <first sprite> <tree sprite>...
Writes <first+k>.png for the k-th tree, same canvas size as the tree so it lines up."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/tq'))
from sprload import load
import numpy as np
from PIL import Image
out, first, trees = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3:]]
os.makedirs(out, exist_ok=True)
STUMP = 7          # stump height in pixels above the trunk's lowest pixel
for k, n in enumerate(trees):
    a = np.array(load(n).convert('RGBA')).astype(int)
    al = a[..., 3] > 0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    wood = al & (r >= g) & (r > b + 10)                  # brown trunk, not green leaves
    ys, xs = np.nonzero(wood)
    if len(ys) == 0: print(n, 'no trunk?'); continue
    base = ys.max()
    # trunk columns at the base
    low = wood & (np.arange(a.shape[0])[:, None] >= base - 2)
    cx = np.nonzero(low.any(0))[0]
    x0, x1 = cx.min(), cx.max()
    keep = np.zeros_like(al)
    top = base - STUMP
    for y in range(top, base + 1):
        for x in range(max(0, x0 - 1), min(a.shape[1], x1 + 2)):
            if wood[y, x]: keep[y, x] = True
    # make the stump at least 3 wide and solid: fill gaps between its left and right edge per row
    for y in range(top, base + 1):
        c = np.nonzero(keep[y])[0]
        if len(c):
            l, rr = c.min(), c.max()
            if rr - l < 2: l, rr = l - 1, rr + 1
            col = a[y, c].mean(0)
            for x in range(l, rr + 1):
                if not keep[y, x]: a[y, x] = col; keep[y, x] = True
    o = np.zeros_like(a)
    o[keep] = a[keep]
    # cut face: the top two rows of the stump, pale wood
    c = np.nonzero(keep[top])[0]
    for x in c:
        o[top, x] = (214, 180, 120, 255)
    c2 = np.nonzero(keep[top + 1])[0]
    for x in c2[1:-1]:
        o[top + 1, x] = (176, 136, 80, 255)
    # a little dark ground shadow left of the stump so it sits on the ground
    for x in range(max(0, c.min() - 3), c.min()):
        if o[base, x, 3] == 0: o[base, x] = (40, 34, 24, 255)
    o[..., 0] = (o[..., 0] >> 3) << 3; o[..., 1] = (o[..., 1] >> 2) << 2; o[..., 2] = (o[..., 2] >> 3) << 3
    Image.fromarray(o.astype(np.uint8), 'RGBA').save(os.path.join(out, '%d.png' % (first + k)))
    print(n, '->', first + k, 'trunk x', x0, x1, 'base', base)
