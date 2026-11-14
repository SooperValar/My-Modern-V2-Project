#!/usr/bin/env python3
"""Wagons for MyV2 (Nov 14): a farm wagon with sacks and a broken one (a wheel off, the bed sunk on that corner,
a split side board, planks on the ground), each lying along either map axis. The first block above 40000 ("props").

    40000 wagon along y (up-right on screen)   40002 wagon along x (down-right)
    40004 broken wagon along y                  40006 broken wagon along x
    each N+1 = its "hidden walls" form (the same picture: a wagon is low)

A wagon covers two tiles: the sprite stands on the FRONT tile (the anchor, drawn last) and reaches over the second
one, which only needs "blocks walking". Along y the second tile is anchor y+1, along x it is anchor x-1.
Drawn from a small 3D model in the game's projection (one tile: x -> (16,8), y -> (16,-8) on screen, z up 1 px),
lit from the upper left, with wood grain speckle.

    world_wagons.py <client folder> [--out <folder>] [--scene <png>]
"""
import math, os, random, sys
from PIL import Image, ImageDraw

FIRST = 40000
W, H = 128, 80                       # canvas; the anchor tile's bottom corner is at (W/2, H)

WOOD = (128, 86, 48); WOOD_DK = (88, 56, 30); IRON = (60, 60, 64); SACK = (196, 176, 132)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c) + (255,)


class Canvas:
    def __init__(self, along, seed):
        self.im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
        self.along = along; self.rng = random.Random(seed)

    def P(self, u, v, z):
        """model point (u along the wagon, v across, z height in px) -> image pixel"""
        x, y = (v, u) if self.along == 'y' else (-u, v)
        return (W / 2 + 16 * (x + y), H - 8 + 8 * (x - y) - z)

    def depth(self, u, v):
        x, y = (v, u) if self.along == 'y' else (-u, v)
        return x - y

    def poly(self, pts, col, grain=0.10):
        pp = [self.P(*p) for p in pts]
        self.d.polygon(pp, fill=col)
        if grain:     # speckle: darker / lighter pixels inside the face
            xs = [p[0] for p in pp]; ys = [p[1] for p in pp]
            mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).polygon(pp, fill=255)
            mk = mask.load(); px = self.im.load()
            for yy in range(int(min(ys)), int(max(ys)) + 1):
                for xx in range(int(min(xs)), int(max(xs)) + 1):
                    if 0 <= xx < W and 0 <= yy < H and mk[xx, yy] and self.rng.random() < 0.35:
                        k = 1 + self.rng.uniform(-grain, grain)
                        r, g, b, a = px[xx, yy]; px[xx, yy] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), a)

    def box(self, u0, u1, v0, v1, z0, z1, col, tilt=None):
        """an axis box; tilt(u, v) -> extra z (the broken wagon's sunk corner). Faces seen from the viewer."""
        t = tilt or (lambda u, v: 0)
        c = lambda u, v, z: (u, v, z + t(u, v))
        top = [c(u0, v0, z1), c(u1, v0, z1), c(u1, v1, z1), c(u0, v1, z1)]
        faces = [(top, 1.18)]
        # the faces toward the viewer: along y the +v side (screen down-right) and the -u end (down-left);
        # along x the +u end... -> pick by depth: the side whose outward normal raises x - y
        sides = {'v1': [c(u0, v1, z0), c(u1, v1, z0), c(u1, v1, z1), c(u0, v1, z1)],
                 'v0': [c(u0, v0, z0), c(u1, v0, z0), c(u1, v0, z1), c(u0, v0, z1)],
                 'u0': [c(u0, v0, z0), c(u0, v1, z0), c(u0, v1, z1), c(u0, v0, z1)],
                 'u1': [c(u1, v0, z0), c(u1, v1, z0), c(u1, v1, z1), c(u1, v0, z1)]}
        vside = 'v1' if self.depth(0, 1) > self.depth(0, 0) else 'v0'
        uside = 'u1' if self.depth(1, 0) > self.depth(0, 0) else 'u0'
        # light from the upper left: the face whose normal points screen-left is brighter
        def lit(side):
            du, dv = {'v1': (0, 1), 'v0': (0, -1), 'u0': (-1, 0), 'u1': (1, 0)}[side]
            x0, y0 = self.P(0, 0, 0); x1, y1 = self.P(du, dv, 0)
            return 0.92 if x1 < x0 else 0.70
        for side in (uside, vside):
            faces.append((sides[side], lit(side)))
        for pts, k in faces[1:] + faces[:1]:
            self.poly(pts, shade(col, k))

    def wheel(self, u, v, zc, r, flat=False):
        """a spoked wheel standing in the plane v = const (or lying flat on the ground)"""
        n = 20
        if flat:
            ring = [(u + r / 16 * math.cos(a), v + r / 16 * math.sin(a), 1) for a in (2 * math.pi * i / n for i in range(n))]
            hub = [(u + 2 / 16 * math.cos(a), v + 2 / 16 * math.sin(a), 2) for a in (2 * math.pi * i / n for i in range(n))]
        else:
            ring = [(u + r / 16 * math.cos(a), v, zc + r * math.sin(a)) for a in (2 * math.pi * i / n for i in range(n))]
            hub = [(u + 2 / 16 * math.cos(a), v, zc + 2 * math.sin(a)) for a in (2 * math.pi * i / n for i in range(n))]
        self.poly(ring, shade(WOOD_DK, 0.75), 0.05)
        pp = [self.P(*p) for p in ring]
        self.d.line(pp + pp[:1], fill=shade(IRON, 1.0), width=1)
        inner = [((p[0] - u) * 0.72 + u, (p[1] - v) * 0.72 + v if flat else v, (p[2] - zc) * 0.72 + zc if not flat else p[2]) for p in ring]
        self.poly(inner, shade(WOOD_DK, 0.5), 0)
        cu, cv, cz = (u, v, 2) if flat else (u, v, zc)
        for i in range(0, n, n // 6):
            q = inner[i]; self.d.line([self.P(cu, cv, cz), self.P(*q)], fill=shade(WOOD, 1.05), width=1)
        self.poly(hub, shade(IRON, 1.2), 0)

    def sack(self, u, v, z, rx=0.16, h=9):
        n = 14
        base = [(u + rx * math.cos(a), v + rx * 0.8 * math.sin(a), z) for a in (2 * math.pi * i / n for i in range(n))]
        pp = [self.P(*p) for p in base]
        cx = sum(p[0] for p in pp) / n; cy = sum(p[1] for p in pp) / n
        top = (cx, cy - h)
        self.d.polygon(pp, fill=shade(SACK, 0.8))
        self.d.ellipse([cx - 6, cy - h - 3, cx + 6, cy + 2], fill=shade(SACK, 0.95))
        self.d.ellipse([cx - 5, cy - h - 3, cx + 1, cy - 1], fill=shade(SACK, 1.12))
        self.d.line([(cx, top[1] - 1), (cx, top[1] + 2)], fill=shade(SACK, 0.6))


def wagon(along, broken, seed):
    cv = Canvas(along, seed)
    U0, U1 = -0.35, 1.35          # bed from the front tile to the back one
    V0, V1 = -0.30, 0.30
    tilt = (lambda u, v: -10 * max(0, (u - 0.6) / 0.75) * max(0, (v + 0.3) / 0.6)) if broken else None
    # wheels on the far side first
    far = 'v0' if cv.depth(0, 1) > cv.depth(0, 0) else 'v1'
    farv, nearv = (V0 - 0.06, V1 + 0.06) if far == 'v0' else (V1 + 0.06, V0 - 0.06)
    if broken:                    # the lost wheel and planks on the ground first
        cv.wheel(1.6, nearv + 0.55 * (1 if nearv > 0 else -1), 0, 9, flat=True)
        cv.box(U0 - 0.95, U0 - 0.25, 0.42, 0.52, 0, 2, WOOD)
        cv.box(0.2, 0.9, 0.55, 0.62, 0, 2, WOOD_DK)
    for u in (0.05, 1.0):
        cv.wheel(u, farv, 9, 9)
    # tongue (shaft) out of the front
    cv.box(-0.75, U0, -0.03, 0.03, 6, 8, WOOD_DK)
    cv.box(-0.80, -0.70, -0.22, 0.22, 6, 8, WOOD_DK)
    # axles
    for u in (0.05, 1.0):
        cv.box(u - 0.03, u + 0.03, V0 - 0.06, V1 + 0.06, 7, 9, IRON, tilt)
    # bed and sides
    cv.box(U0, U1, V0, V1, 11, 13, WOOD, tilt)
    sides = [(U0, U1, V0, V0 + 0.05), (U0, U1, V1 - 0.05, V1), (U0, U0 + 0.05, V0, V1), (U1 - 0.05, U1, V0, V1)]
    near_long = 1 if nearv > 0 else 0
    def side(i):
        a_, b_, c_, d_ = sides[i]; z1 = 21
        if broken and i == near_long:          # the near side split: only its front part stands
            cv.box(a_, 0.40, c_, d_, 12, z1, WOOD, tilt); return
        if broken and i == 3:
            cv.box(a_, b_, c_, d_, 12, 16, WOOD, tilt); return
        cv.box(a_, b_, c_, d_, 12, z1, WOOD, tilt)
    mid = cv.depth(0.5, 0)
    dep = lambda i: cv.depth((sides[i][0] + sides[i][1]) / 2, (sides[i][2] + sides[i][3]) / 2)
    back = [i for i in range(4) if dep(i) <= mid]; front = [i for i in range(4) if dep(i) > mid]
    for i in sorted(back, key=dep): side(i)
    loads = [(0.0, -0.1), (0.3, 0.12), (0.62, -0.08), (1.0, 0.1)] if not broken else [(0.05, 0.0), (0.4, 0.05)]
    for u, v in sorted(loads, key=lambda p: cv.depth(*p)):
        cv.sack(u, v, 12 + (tilt(u, v) if tilt else 0))
    for i in sorted(front, key=dep): side(i)
    # near wheels
    if broken:
        cv.wheel(0.05, nearv, 9, 9)
    else:
        for u in (0.05, 1.0):
            cv.wheel(u, nearv, 9, 9)
    return cv.im


def main():
    a = sys.argv[1:]
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(a[0], 'GFX')
    scene = a[a.index('--scene') + 1] if '--scene' in a else None
    os.makedirs(out, exist_ok=True)
    made = {}
    for k, (along, broken) in enumerate((('y', False), ('x', False), ('y', True), ('x', True))):
        im = wagon(along, broken, 40 + k)
        bb = im.getbbox()
        n = FIRST + 2 * k
        for m in (n, n + 1):
            im.save(os.path.join(out, '%05d.png' % m))
        made[n] = im
        print(n, 'along', along, 'broken' if broken else 'whole', 'bbox', bb)
    if scene:
        sys.argv = [sys.argv[0], a[0], '/tmp']
        exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
        S = Image.new('RGBA', (400, 210), (0, 0, 0, 255))
        def scr(x, y): return 200 + 16 * (x + y), 105 + 8 * (x - y)
        g = load(1118)
        for x in range(-5, 6):
            for y in range(-5, 6):
                sx, sy = scr(x, y); S.alpha_composite(g, (sx - g.width // 2, sy + 8 - g.height))
        items = [((-2, -3), 40000), ((2, -2), 40002), ((-2, 2), 40004), ((3, 2), 40006), ((0, 0), 'man')]
        man = load(5072 + 48)
        for (x, y), n in sorted(items, key=lambda t: t[0][0] - t[0][1]):
            sp = man if n == 'man' else made[n]
            sx, sy = scr(x, y); S.alpha_composite(sp, (sx - sp.width // 2, sy + 8 - sp.height))
        S = S.resize((S.width * 3, S.height * 3), Image.NEAREST)
        S.convert('RGB').save(scene); print('scene', scene)


if __name__ == '__main__':
    main()
