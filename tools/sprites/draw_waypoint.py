#!/usr/bin/env python3
"""Draw the waypoint's 3x3 circle as nine see-through overlay tiles, dim and lit (blue).

    draw_waypoint.py <a flat floor tile png> <out folder> [first sprite number | -] [design]

The circle is drawn flat in world space and projected like the game does it
(screen x = 16(x+y), y = 8(x-y)), then cut into the nine tiles (the floor tile
only gives the tile's shape; the pieces are see-through and lie on any floor):
<out>/dim_<k>.png and lit_<k>.png, k = 0..8 = (dx+1)*3+(dy+1), or NNNNN.png
(dim first+k, lit first+10+k) when a first sprite number is given.
The PNGs hold colour multiplied by alpha, as the client reads them (dd_load_png).
Also writes sheet_dim.png / sheet_lit.png (the nine put together on that floor).
design: runes (rune rings, the waypoint: sprites 18300-18308 / 18310-18318) or
star (pentagram in a rune ring, kept for later: 18320-18328 / 18330-18338).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageFilter

SS = 6            # supersampling
R_OUT, R_IN, R_STAR = 1.36, 1.14, 1.12

def seg_dist(u, v, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((u - ax) * dx + (v - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(u - (ax + t * dx), v - (ay + t * dy))

def line(d, w):   # 1 inside the line, soft edge
    return np.clip((w / 2 - d) / 0.02 + 0.5, 0, 1)

def design(u, v, kind):
    r = np.hypot(u, v); ang = np.arctan2(v, u)
    I = np.maximum(line(np.abs(r - R_OUT), 0.085), line(np.abs(r - R_IN), 0.05))
    # rune marks between the rings: 20 cells, each a small glyph of strokes
    rng = np.random.RandomState(7)
    n = 20
    for k in range(n):
        a0 = 2 * math.pi * (k + 0.5) / n
        rot = lambda p, q: ((R_IN + R_OUT) / 2 * math.cos(a0) + p * -math.sin(a0) + q * math.cos(a0),
                            (R_IN + R_OUT) / 2 * math.sin(a0) + p * math.cos(a0) + q * math.sin(a0))
        pts = [(-0.06, -0.06), (0.06, -0.06), (-0.06, 0.06), (0.06, 0.06), (0, 0), (0, -0.07), (0, 0.07)]
        for _ in range(2 + rng.randint(2)):
            p, q = pts[rng.randint(len(pts))], pts[rng.randint(len(pts))]
            if p == q: continue
            I = np.maximum(I, line(seg_dist(u, v, rot(*p), rot(*q)), 0.035))
    if kind == 'star':
        # one point towards the top of the screen (world direction -x,+y)
        base = math.atan2(1, -1)
        P = [(R_STAR * math.cos(base + 2 * math.pi * k / 5), R_STAR * math.sin(base + 2 * math.pi * k / 5)) for k in range(5)]
        for k in range(5):
            I = np.maximum(I, line(seg_dist(u, v, P[k], P[(k + 2) % 5]), 0.06))
        I = np.maximum(I, line(np.abs(r - 0.2), 0.04))
    else:
        I = np.maximum(I, line(np.abs(r - 0.72), 0.05))
        I = np.maximum(I, line(np.abs(r - 0.56), 0.035))
        m = 8
        for k in range(m):
            a = 2 * math.pi * k / m + math.atan2(1, -1)
            I = np.maximum(I, line(seg_dist(u, v, (0.56 * math.cos(a), 0.56 * math.sin(a)),
                                            (0.16 * math.cos(a + 0.5), 0.16 * math.sin(a + 0.5))), 0.04))
        I = np.maximum(I, line(np.abs(r - 0.16), 0.04))
        for k in range(4):
            a = 2 * math.pi * k / 4 + math.atan2(1, -1)
            I = np.maximum(I, line(seg_dist(u, v, (0.72 * math.cos(a), 0.72 * math.sin(a)), (R_IN * math.cos(a), R_IN * math.sin(a))), 0.04))
    return I

def main():
    floor = Image.open(sys.argv[1]).convert('RGBA'); out = sys.argv[2]
    first = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != '-' else 0
    kind = sys.argv[4] if len(sys.argv) > 4 else 'runes'
    os.makedirs(out, exist_ok=True)
    fa = np.array(floor); mask = fa[..., 3] > 0
    ys = np.where(mask.any(1))[0]; top = np.where(mask[:, 15] | mask[:, 16])[0].min()
    cyt = (top + ys.max() + 1) / 2.0          # the tile's centre row inside the 32x32 sprite
    W, H = 96, 96; OX, OY = 48, 48            # canvas; world centre at (OX, OY)
    yy, xx = np.mgrid[0:H * SS, 0:W * SS]
    sx = (xx + 0.5) / SS - OX; sy = (yy + 0.5) / SS - OY
    u = (sx / 16 + sy / 8) / 2; v = (sx / 16 - sy / 8) / 2
    I = design(u, v, kind)
    Ilow = np.array(Image.fromarray((I * 255).astype(np.uint8)).resize((W, H), Image.BOX)) / 255.0
    Iwide = np.array(Image.fromarray((I * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * (SS // 2) + 1)).resize((W, H), Image.BOX)) / 255.0
    glow = np.array(Image.fromarray((I * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(SS * 1.2)).resize((W, H), Image.BOX)) / 255.0
    inner = np.array(Image.fromarray(((np.hypot(u, v) < R_OUT) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(SS * 3)).resize((W, H), Image.BOX)) / 255.0
    # the floor under it
    base = np.zeros((H, W, 4), np.uint8); pos = {}
    for dx in (-1, 0, 1):
        for dy in (1, 0, -1):
            px = int(OX + 16 * (dx + dy) - 16); py = int(round(OY + 8 * (dx - dy) - cyt))
            pos[dx, dy] = (px, py)
            sub = base[py:py + 32, px:px + 32]; sub[mask] = fa[mask]
    def over(dst, col, al):                   # put a colour layer (alpha al) over an RGBA float layer
        da = dst[..., 3:4]; al = al[..., None]; oa = al + da * (1 - al)
        dst[..., :3] = np.where(oa > 0, (np.array(col, float) * al + dst[..., :3] * da * (1 - al)) / np.maximum(oa, 1e-6), 0)
        dst[..., 3:4] = oa
    def state(lit):
        o = np.zeros((H, W, 4))
        if lit:
            over(o, (90, 150, 255), inner * 0.07)                          # a faint blue wash inside the circle
            over(o, (30, 110, 255), np.clip(glow * 1.2, 0, 1) * 0.16)      # a thin halo: more would fill the gaps between the lines
            over(o, (20, 60, 170), np.clip(Iwide - Ilow, 0, 1) * 0.55)     # a dark blue rim, so the lines stay sharp on light floors
            over(o, (60, 150, 255), Ilow)                                  # the lines themselves
            over(o, (190, 235, 255), np.clip(Ilow, 0, 1) ** 3 * 0.8)       # bright core
        else:
            over(o, (58, 66, 84), Ilow * 0.72)                             # carved, unlit
            sh = np.roll(Ilow, 1, 0)                                       # a thin light edge below each groove
            over(o, (255, 255, 255), np.clip(sh - Ilow, 0, 1) * 0.35)
        return o
    def png(o):                                # the client expects colour already multiplied by alpha
        q = np.zeros(o.shape, np.uint8); al = np.clip(o[..., 3], 0, 1)
        q[..., 3] = np.round(al * 255); q[..., :3] = np.round(np.clip(o[..., :3], 0, 255) * al[..., None])
        return q
    for name, lit in (('dim', 0), ('lit', 1)):
        o = state(lit); al = o[..., 3:4]
        prev = base.copy(); prev[..., :3] = np.clip(o[..., :3] * al + base[..., :3] * (1 - al), 0, 255)
        Image.fromarray(prev).save(os.path.join(out, 'sheet_%s.png' % name))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                k = (dx + 1) * 3 + (dy + 1); px, py = pos[dx, dy]
                t = png(o[py:py + 32, px:px + 32]); t[~mask] = 0
                fn = ('%05d.png' % (first + (10 if lit else 0) + k)) if first else '%s_%d.png' % (name, k)
                Image.fromarray(t).save(os.path.join(out, fn))
    print('written to', out)

if __name__ == '__main__':
    main()
