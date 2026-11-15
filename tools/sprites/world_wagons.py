#!/usr/bin/env python3
"""Wagons for MyV2 (Nov 14): a farm wagon with sacks and a crate and a broken one (a wheel off, the bed sunk on
that corner, a split side board, planks on the ground), each lying along either map axis. The first block above
40000 ("props").

    40000 wagon along y (up-right on screen)   40002 wagon along x (down-right)
    40004 broken wagon along y                  40006 broken wagon along x
    each N+1 = its "hidden walls" form (the same picture: a wagon is low)

A wagon covers two tiles: the sprite stands on the FRONT tile (the anchor, drawn last) and reaches over the second
one, which only needs "blocks walking". Along y the second tile is anchor y+1, along x it is anchor x-1.

Drawn from a small 3D model in the game's projection (one tile: x -> (16,8), y -> (16,-8) on screen, z up 1 px).
To sit with the game's own art: no outlines, the game's dark saturated palette (the crate 176 / barrel 16882 woods),
every face textured with plank seams and noisy grain like the crate, lit from the upper left; open spoked wheels;
the load is the game's own crate, shrunk, and burlap sacks.

    world_wagons.py <client folder> [--out <folder>] [--scene <png>]
"""
import math, os, random, sys
from PIL import Image, ImageDraw

FIRST = 40000
W, H = 128, 80                     # canvas; the anchor tile's bottom corner is at (W/2, H)
# palettes (dark, mid, light) taken from the game's own wood
OAK = ((40, 30, 6), (92, 70, 24), (146, 112, 36))         # the crate's golden-olive wood
RED = ((38, 8, 4), (74, 24, 10), (112, 42, 14))           # the barrel's red-brown, for the frame and wheels
IRON = ((22, 22, 26), (52, 52, 58), (96, 96, 104))
BURLAP = ((70, 56, 30), (126, 104, 62), (170, 146, 96))


def lerp3(p, t):
    d, m, l = p
    if t < 0.5:
        k = t / 0.5; return tuple(d[i] + (m[i] - d[i]) * k for i in range(3))
    k = (t - 0.5) / 0.5; return tuple(m[i] + (l[i] - m[i]) * k for i in range(3))


class Canvas:
    def __init__(self, along, seed):
        self.im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); self.px = self.im.load(); self.d = ImageDraw.Draw(self.im)
        self.along = along; self.rng = random.Random(seed)
        self.noise = [[self.rng.random() for _ in range(64)] for _ in range(64)]

    def P(self, u, v, z):
        x, y = (v, u) if self.along == 'y' else (-u, v)
        return (W / 2 + 16 * (x + y), H - 8 + 8 * (x - y) - z)

    def depth(self, u, v):
        x, y = (v, u) if self.along == 'y' else (-u, v)
        return x - y

    def face(self, p0, pa, pb, pal, k, plank=4.0, seed=0):
        """a parallelogram face: p0 corner, pa the end along its grain, pb the end across; textured like game wood"""
        s0, sa, sb = self.P(*p0), self.P(*pa), self.P(*pb)
        ax, ay = sa[0] - s0[0], sa[1] - s0[1]; bx, by = sb[0] - s0[0], sb[1] - s0[1]
        det = ax * by - ay * bx
        if abs(det) < 0.5: return
        la = math.dist(p0[:2], pa[:2]) * 32 + abs(pa[2] - p0[2]); lb = math.dist(p0[:2], pb[:2]) * 32 + abs(pb[2] - p0[2])
        xs = [s0[0], sa[0], sb[0], sa[0] + bx]; ys = [s0[1], sa[1], sb[1], sa[1] + by]
        for yy in range(int(min(ys)), int(math.ceil(max(ys))) + 1):
            for xx in range(int(min(xs)), int(math.ceil(max(xs))) + 1):
                if not (0 <= xx < W and 0 <= yy < H): continue
                dx, dy = xx + 0.5 - s0[0], yy + 0.5 - s0[1]
                a = (dx * by - dy * bx) / det; b = (ax * dy - ay * dx) / det
                if not (-0.01 <= a <= 1.01 and -0.01 <= b <= 1.01): continue
                ap, bp = a * la, b * lb
                pl = int(bp / plank); seam = (bp % plank) < 0.9 and plank < 50
                n1 = self.noise[(int(ap) + 7 * pl + seed) % 64][(int(bp * 3) + seed) % 64]
                streak = 0.5 + 0.5 * math.sin(ap * 0.7 + pl * 2.1 + n1 * 2.5)
                t = 0.42 + 0.18 * streak + 0.30 * (n1 - 0.5) + 0.08 * ((pl * 37 + seed) % 5 - 2) / 2
                if seam: t -= 0.32
                t = max(0, min(1, t * k))
                self.px[xx, yy] = tuple(int(c) for c in lerp3(pal, t)) + (255,)

    def box(self, u0, u1, v0, v1, z0, z1, pal, tilt=None, plank=4.0, seed=0):
        t = tilt or (lambda u, v: 0)
        c = lambda u, v, z: (u, v, z + t(u, v))
        vside = v1 if self.depth(0, 1) > self.depth(0, 0) else v0
        uside = u1 if self.depth(1, 0) > self.depth(0, 0) else u0
        def lit(du, dv):
            x0, _ = self.P(0, 0, 0); x1, _ = self.P(du, dv, 0)
            return 0.95 if x1 < x0 else 0.68
        # the long side (grain along u), the end (grain along v), then the top
        self.face(c(u0, vside, z0), c(u1, vside, z0), c(u0, vside, z1), pal, lit(0, 1 if vside == v1 else -1), plank, seed)
        self.face(c(uside, v0, z0), c(uside, v1, z0), c(uside, v0, z1), pal, lit(1 if uside == u1 else -1, 0), plank, seed + 5)
        self.face(c(u0, v0, z1), c(u1, v0, z1), c(u0, v1, z1), pal, 1.22, plank, seed + 11)

    def wheel(self, u, v, zc, r, flat=False):
        n = 28
        def pt(a, rr):
            if flat: return (u + rr / 16 * math.cos(a), v + rr / 16 * math.sin(a), 1)
            return (u + rr / 16 * math.cos(a), v, zc + rr * math.sin(a))
        angs = [2 * math.pi * i / n for i in range(n + 1)]
        for i in range(n):          # the rim: a band of small quads, lit by which way it faces
            a0, a1 = angs[i], angs[i + 1]
            q = [self.P(*pt(a0, r)), self.P(*pt(a1, r)), self.P(*pt(a1, r - 2)), self.P(*pt(a0, r - 2))]
            k = 0.55 + 0.35 * max(0, math.sin(a0 + 2.2))
            self.d.polygon(q, fill=tuple(int(c) for c in lerp3(RED, k)) + (255,))
        for i in range(0, n, n // 8):     # spokes
            self.d.line([self.P(*pt(angs[i], 1.5)), self.P(*pt(angs[i], r - 1.5))], fill=tuple(int(c) for c in lerp3(RED, 0.62)) + (255,))
        hub = [self.P(*pt(a, 2.2)) for a in angs]
        self.d.polygon(hub, fill=tuple(int(c) for c in lerp3(IRON, 0.55)) + (255,))
        self.px[int(self.P(*pt(0, 0))[0]), int(self.P(*pt(0, 0))[1])] = tuple(int(c) for c in lerp3(IRON, 0.95)) + (255,)

    def sack(self, u, v, z, h=10):
        cx, cy = self.P(u, v, z)
        for yy in range(int(cy - h - 3), int(cy + 3)):
            for xx in range(int(cx - 7), int(cx + 8)):
                ex = (xx + 0.5 - cx) / 6.5; ey = (yy + 0.5 - (cy - h / 2)) / (h / 2 + 2.5)
                if ex * ex + ey * ey > 1 or not (0 <= xx < W and 0 <= yy < H): continue
                lt = 0.62 - 0.35 * ex - 0.25 * ey + 0.18 * (self.rng.random() - 0.5)
                if abs(xx - cx) < 0.6 and yy < cy - h + 1: lt -= 0.35       # the tied neck
                self.px[xx, yy] = tuple(int(c) for c in lerp3(BURLAP, max(0, min(1, lt)))) + (255,)

    def paste_crate(self, crate, u, v, z):
        if crate is None: return
        cx, cy = self.P(u, v, z)
        self.im.alpha_composite(crate, (int(cx - crate.width / 2), int(cy + 4 - crate.height)))


def wagon(along, broken, seed, crate):
    cv = Canvas(along, seed)
    U0, U1 = -0.42, 1.42
    V0, V1 = -0.36, 0.36
    tilt = (lambda u, v: -10 * max(0, (u - 0.6) / 0.75)) if broken else None
    far = 'v0' if cv.depth(0, 1) > cv.depth(0, 0) else 'v1'
    farv, nearv = (V0 - 0.07, V1 + 0.07) if far == 'v0' else (V1 + 0.07, V0 - 0.07)
    if broken:                    # the lost wheel and planks on the ground first
        cv.wheel(1.6, nearv + 0.55 * (1 if nearv > 0 else -1), 0, 9, flat=True)
        cv.box(U0 - 0.95, U0 - 0.30, 0.40, 0.52, 0, 2, OAK, plank=60, seed=3)
        cv.box(0.15, 0.85, -0.62 if nearv < 0 else 0.55, -0.55 if nearv < 0 else 0.62, 0, 2, OAK, plank=60, seed=9)
    for u in (0.0, 1.05):
        cv.wheel(u, farv, 10, 10)
    cv.box(-0.85, U0, -0.03, 0.03, 6, 8, RED, plank=60)             # the shaft and its crossbar
    cv.box(-0.92, -0.82, -0.26, 0.26, 6, 8, RED, plank=60)
    for u in (0.0, 1.05):
        cv.box(u - 0.035, u + 0.035, V0 - 0.07, V1 + 0.07, 7, 9, IRON, tilt, plank=60)
    cv.box(U0, U1, V0, V1, 11, 13, RED, tilt, plank=60)            # frame
    sides = [(U0, U1, V0, V0 + 0.05), (U0, U1, V1 - 0.05, V1), (U0, U0 + 0.05, V0, V1), (U1 - 0.05, U1, V0, V1)]
    near_long = 1 if nearv > 0 else 0
    def side(i):
        a_, b_, c_, d_ = sides[i]
        if broken and i == near_long:
            cv.box(a_, 0.40, c_, d_, 13, 25, OAK, tilt, seed=i * 13); return
        if broken and i == 3:
            cv.box(a_, b_, c_, d_, 13, 17, OAK, tilt, seed=i * 13); return
        cv.box(a_, b_, c_, d_, 13, 25, OAK, tilt, seed=i * 13)
    cv.box(U0, U1, V0, V1, 13, 14, OAK, tilt, seed=21)             # the bed's floor
    mid = cv.depth(0.5, 0)
    dep = lambda i: cv.depth((sides[i][0] + sides[i][1]) / 2, (sides[i][2] + sides[i][3]) / 2)
    for i in sorted([i for i in range(4) if dep(i) <= mid], key=dep): side(i)
    load = [(0.95, 0.0, 'crate'), (0.0, -0.1, 's'), (0.35, 0.1, 's'), (0.5, -0.12, 's')] if not broken else [(0.05, 0.0, 's'), (0.35, 0.06, 's')]
    for u, v, kind in sorted(load, key=lambda p: cv.depth(p[0], p[1])):
        z = 14 + (tilt(u, v) if tilt else 0)
        if kind == 'crate': cv.paste_crate(crate, u, v, z)
        else: cv.sack(u, v, z)
    for i in sorted([i for i in range(4) if dep(i) > mid], key=dep): side(i)
    if broken:
        cv.wheel(0.0, nearv, 10, 10)
    else:
        for u in (0.0, 1.05): cv.wheel(u, nearv, 10, 10)
    return cv.im


def main():
    a = sys.argv[1:]
    client = a[0]
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(client, 'GFX')
    scene = a[a.index('--scene') + 1] if '--scene' in a else None
    os.makedirs(out, exist_ok=True)
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    crate = load(176)
    if crate:
        crate = crate.crop(crate.getbbox()); crate = crate.resize((max(1, crate.width * 13 // 20), max(1, crate.height * 13 // 20)), Image.LANCZOS)
        p = crate.load()
        for yy in range(crate.height):
            for xx in range(crate.width):
                r, g, b, al = p[xx, yy]; p[xx, yy] = (r, g, b, 255 if al > 110 else 0)
    made = {}
    for k, (along, broken) in enumerate((('y', False), ('x', False), ('y', True), ('x', True))):
        im = wagon(along, broken, 40 + k, crate)
        n = FIRST + 2 * k
        for m in (n, n + 1): im.save(os.path.join(out, '%05d.png' % m))
        made[n] = im
        print(n, 'along', along, 'broken' if broken else 'whole', 'bbox', im.getbbox())
    if scene:
        S = Image.new('RGBA', (400, 210), (0, 0, 0, 255))
        def scr(x, y): return 200 + 16 * (x + y), 105 + 8 * (x - y)
        g = load(1118)
        for x in range(-5, 6):
            for y in range(-5, 6):
                sx, sy = scr(x, y); S.alpha_composite(g, (sx - g.width // 2, sy + 8 - g.height))
        items = [((-2, -3), 40000), ((2, -2), 40002), ((-2, 2), 40004), ((3, 2), 40006), ((0, 0), 'man'), ((1, -4), 176), ((-3, 0), 16882)]
        for (x, y), n in sorted(items, key=lambda t: t[0][0] - t[0][1]):
            sp = load(5072 + 48) if n == 'man' else made.get(n) or load(n)
            if n == 16882:
                sp = sp.copy(); pp = sp.load()
                for yy in range(sp.height):
                    for xx in range(sp.width):
                        r, gg, b, al = pp[xx, yy]
                        if r > 240 and gg < 10 and b > 240: pp[xx, yy] = (0, 0, 0, 0)
            sx, sy = scr(x, y); S.alpha_composite(sp, (sx - sp.width // 2, sy + 8 - sp.height))
        S = S.resize((S.width * 3, S.height * 3), Image.NEAREST)
        S.convert('RGB').save(scene); print('scene', scene)


if __name__ == '__main__':
    main()
