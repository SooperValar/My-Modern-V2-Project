#!/usr/bin/env python3
"""Foundry pieces for the Golem Foundry (Nov 17; Cody: anvils and molten iron, nothing modern). DRAFT for Cody's look.

World objects (32x64, drawn into the tile like the eggs; each N+1 its hide-walls form, the same picture):
  38400 anvil on a log       38402 anvil on a granite block   38404 crucible of molten iron (glowing)
  38406 quench bucket        38408 grindstone                 38410 stack of iron ingots
  38412 casting mould (molten iron poured in)   38414 stone furnace (a bloomery, glowing mouth and top)
  38416 a toppled iron golem (wreck)            38418 wrecked golem limbs
Ground: molten iron 36300-36303 (glowing, crusted; to block walking like water).
3D props from Cody's "3d Models/Fantasy Props" and "RPG Pack 2" (glrender / objmodel), molten parts painted on.

    world_foundry.py <client folder> [--out <folder>] [--sheet <png>]"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import glrender as G, world_ground as wg
from objmodel import ObjModel
M3 = os.path.expanduser('~/mnt/MyV2/3d Models')
PPM = 25.0                          # pixels per metre (a man ~45 px, like the game's)
MAG = np.array([1.0, 0.0, 1.0])     # marker colour for painted-on surfaces

class Extra:
    """a model plus marker discs (molten iron, water) at given heights"""
    def __init__(self, m, discs=()):
        self.m, self.discs = m, discs
    def triangles(self, anim=None, t=0.0):
        P, N, C = self.m.triangles(anim, t); self.rest = getattr(self.m, 'rest', None)
        lo = P.reshape(-1, 3).min(0); hi = P.reshape(-1, 3).max(0); c = (lo + hi) / 2
        add = []
        for h, r in self.discs:
            for k in range(24):
                a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
                add.append([[c[0], lo[1] + h, c[2]], [c[0] + r * math.cos(a0), lo[1] + h, c[2] + r * math.sin(a0)], [c[0] + r * math.cos(a1), lo[1] + h, c[2] + r * math.sin(a1)]])
        if add:
            A = np.array(add, float); P = np.concatenate([P, A]); N = np.concatenate([N, np.tile([0, 1, 0], (len(A), 3, 1)).astype(float)])
            C = np.concatenate([C, np.tile(MAG, (len(A), 3, 1))])
        return P, N, C

def prop(model, yaw=45, shift=(0, 0), scale=1.0):
    P, _, _ = model.triangles(None, 0.0); lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0)
    c = (lo + hi) / 2
    fix = lambda P: P - np.array([c[0], lo[1], c[2]])
    im = G.render(model, yaw=yaw, scale=PPM * scale, size=64, ox=32 + shift[0], oy=57 + shift[1], fix=fix, shadow=0.45)
    return im.crop((16, 0, 48, 64))

def molten_px(r, x, y, base=0.0):
    n = 0.5 + 0.3 * math.sin(x * 0.9 + r[0]) * math.sin(y * 1.3 + r[1]) + 0.2 * math.sin((x + y) * 0.55 + r[2]) + base
    if n > 0.78: return (255, 236, 160)
    if n > 0.55: return (255, 168, 48)
    if n > 0.32: return (226, 92, 18)
    return (92, 30, 14)

def paint(im, fill):
    """replace the marker colour (lit magenta) with fill(x, y)"""
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            p = px[x, y]
            if p[3] and p[0] > 60 and p[2] > 60 and p[1] < 0.45 * min(p[0], p[2]):
                px[x, y] = fill(x, y) + (255,)
    return im

def glow(im, cx, cy, rad, col=(255, 120, 30), a=70):
    """a soft warm glow on the ground round a hot thing (only where the sprite is empty)"""
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            d = math.hypot((x - cx) / rad, (y - cy) / (rad * 0.5))
            if d < 1 and px[x, y][3] == 0:
                px[x, y] = col + (int(a * (1 - d) ** 1.5),)
    return im

def recol(m, rgb):
    for k in set(m.mat): m.recol[k] = np.array(rgb)
    return m

def mould(seed):
    """a sand casting bed with three ingot moulds of fresh molten iron"""
    S = 4; im = Image.new('RGBA', (32 * S, 64 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = random.Random(seed)
    def sc(xl, yl, z=0.0): return ((16 + 16 * (xl + yl)) * S, (56.5 + 7.5 * (xl - yl) - z) * S)
    def quad(a, b, c, e, col): d.polygon([a, b, c, e], fill=col)
    u0, u1, v0, v1, H = -0.42, 0.42, -0.36, 0.36, 3.0
    # sides (front faces), then the top
    quad(sc(u1, v0), sc(u1, v1), sc(u1, v1, H), sc(u1, v0, H), (112, 86, 52, 255))
    quad(sc(u0, v0), sc(u1, v0), sc(u1, v0, H), sc(u0, v0, H), (138, 108, 66, 255))
    quad(sc(u0, v0, H), sc(u1, v0, H), sc(u1, v1, H), sc(u0, v1, H), (170, 138, 90, 255))
    for k in range(3):
        a = -0.26 + 0.24 * k
        quad(sc(-0.3, a - 0.07, H), sc(0.3, a - 0.07, H), sc(0.3, a + 0.07, H), sc(-0.3, a + 0.07, H), (70, 26, 12, 255))
    im = im.resize((32, 64), Image.LANCZOS); px = im.load()
    rr = [r.random() * 6 for _ in range(3)]
    for y in range(64):                   # the slots (dark) become molten iron
        for x in range(32):
            p = px[x, y]
            if p[3] < 128: px[x, y] = (0, 0, 0, 0)
            elif p[0] < 100 and p[1] < 45: px[x, y] = molten_px(rr, x, y, 0.15) + (255,)
            elif p[3]: px[x, y] = p[:3] + (255,)
            else: px[x, y] = (0, 0, 0, 0)
    for _ in range(18):                   # sand grain
        x, y = r.randrange(32), r.randrange(40, 64)
        if px[x, y][3] and px[x, y][1] > 80: c = px[x, y]; px[x, y] = tuple(max(0, v - 18) for v in c[:3]) + (255,)
    return im                             # (no ground glow: round the low bed it read as an odd halo - Cody)

def molten_tile(seed):
    r = random.Random(seed); rr = [r.random() * 6.28 for _ in range(3)]
    t = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = t.load()
    crusts = [(r.uniform(-0.5, 0.5), r.uniform(-0.5, 0.5), r.uniform(0.06, 0.13)) for _ in range(r.randrange(3, 6))]
    for y in range(32):
        for x in range(32):
            if not wg.IN(x, y): continue
            xl, yl = wg.local(x, y)
            base = -sum(max(0, 0.7 * (1 - math.hypot(xl - a, yl - b) / c)) for a, b, c in crusts)
            n = 0.55 + 0.22 * math.sin(xl * 9 + rr[0]) * math.sin(yl * 8 + rr[1]) + 0.16 * math.sin((xl - yl) * 13 + rr[2]) + base + r.uniform(-0.05, 0.05)
            px[x, y] = ((255, 236, 160) if n > 0.8 else (255, 168, 48) if n > 0.56 else (226, 92, 18) if n > 0.34 else (92, 30, 14)) + (255,)
    return t

class Prim:
    """hand-built geometry: boxes and stacked stone rings (triangles, normals, colours), for glrender.render"""
    def __init__(self, seed=1):
        self.P, self.N, self.C = [], [], []; self.r = random.Random(seed); self.rest = None
    def tri(self, a, b, c, col):
        a, b, c = map(np.array, (a, b, c)); n = np.cross(b - a, c - a); n = n / max(1e-9, np.linalg.norm(n))
        self.P.append([a, b, c]); self.N.append([n, n, n]); self.C.append([np.array(col)] * 3)
    def quad(self, a, b, c, d, col): self.tri(a, b, c, col); self.tri(a, c, d, col)
    def box(self, c, size, yaw=0.0, roll=0.0, col=(0.4, 0.4, 0.4), jit=0.06):
        sx, sy, sz = [v / 2 for v in size]; cy_, sy_ = math.cos(yaw), math.sin(yaw); cr, sr = math.cos(roll), math.sin(roll)
        def T(x, y, z):
            x, y = x * cr - y * sr, x * sr + y * cr                     # roll (about z), then yaw (about y)
            return (c[0] + x * cy_ - z * sy_, c[1] + y, c[2] + x * sy_ + z * cy_)
        v = [T(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            k = 1 + self.r.uniform(-jit, jit); self.quad(*[v[i] for i in f], tuple(min(1, x * k) for x in col))
    def rings(self, r0, r1, h, rows, n, col, jit=0.10, y0=0.0):
        for i in range(rows):
            ya, yb = y0 + h * i / rows, y0 + h * (i + 1) / rows; ra, rb = r0 + (r1 - r0) * i / rows, r0 + (r1 - r0) * (i + 1) / rows
            off = 0.5 * (i % 2)
            for k in range(n):
                a0, a1 = 2 * math.pi * (k + off) / n, 2 * math.pi * (k + 1 + off) / n
                kk = 1 + self.r.uniform(-jit, jit)
                self.quad((ra * math.cos(a0), ya, ra * math.sin(a0)), (ra * math.cos(a1), ya, ra * math.sin(a1)),
                          (rb * math.cos(a1), yb, rb * math.sin(a1)), (rb * math.cos(a0), yb, rb * math.sin(a0)), tuple(min(1, x * kk) for x in col))
    def disc(self, y, r, col, c=(0, 0)):
        for k in range(20):
            a0, a1 = 2 * math.pi * k / 20, 2 * math.pi * (k + 1) / 20
            self.tri((c[0], y, c[1]), (c[0] + r * math.cos(a0), y, c[1] + r * math.sin(a0)), (c[0] + r * math.cos(a1), y, c[1] + r * math.sin(a1)), col)
    def triangles(self, anim=None, t=0.0):
        P = np.array(self.P, float); self.rest = P.copy(); return P, np.array(self.N, float), np.array(self.C, float)

def facing():
    """the angle (about y) of a surface that faces the viewer"""
    R = G.camera(45); return math.atan2(R[2][2], R[2][0])

def furnace():
    m = Prim(14); STONE = (0.56, 0.53, 0.50)
    m.rings(0.50, 0.30, 1.55, 7, 12, STONE, jit=0.22)
    m.rings(0.33, 0.33, 0.12, 1, 12, (0.36, 0.35, 0.34), y0=1.55)            # the rim
    m.disc(1.665, 0.24, tuple(MAG))                                          # fire showing at the top
    th = facing(); w = 0.34
    for i in range(6):                                                       # the mouth: an arch on the front, low down
        a0, a1 = th - w + 2 * w * i / 6, th - w + 2 * w * (i + 1) / 6
        top0 = 0.52 + 0.12 * math.cos((i / 6 - 0.5) * math.pi); top1 = 0.52 + 0.12 * math.cos(((i + 1) / 6 - 0.5) * math.pi)
        r = 0.505
        m.quad((r * math.cos(a0), 0.02, r * math.sin(a0)), (r * math.cos(a1), 0.02, r * math.sin(a1)),
               (0.47 * math.cos(a1), top1, 0.47 * math.sin(a1)), (0.47 * math.cos(a0), top0, 0.47 * math.sin(a0)), tuple(MAG))
    rr = [0.7, 1.9, 2.4]
    im = paint(prop(m), lambda x, y: molten_px(rr, x * 1.4, y * 1.4, 0.15))
    return glow(im, 16, 57, 15, a=75)

IRON, RUST = (0.30, 0.30, 0.33), (0.44, 0.26, 0.15)
def wreck(kind):
    m = Prim(16 + kind); r = m.r
    col = lambda: RUST if r.random() < 0.3 else IRON
    if kind == 0:     # a toppled golem: the torso on its side, the head knocked off, an arm beside it
        m.box((0.0, 0.22, 0.05), (0.78, 0.42, 0.52), yaw=0.5, roll=0.15, col=IRON)
        m.box((0.05, 0.47, 0.05), (0.50, 0.12, 0.40), yaw=0.5, roll=0.15, col=RUST)
        m.box((-0.38, 0.12, -0.30), (0.26, 0.24, 0.26), yaw=1.1, col=IRON)
        m.box((0.30, 0.09, -0.32), (0.55, 0.17, 0.18), yaw=-0.3, col=col())
        m.box((0.42, 0.08, 0.36), (0.20, 0.16, 0.20), yaw=0.2, col=col())
    else:             # limbs and plates lying about
        for _ in range(7):
            a, d = r.uniform(0, 6.28), r.uniform(0.10, 0.45)
            sz = (r.uniform(0.25, 0.55), r.uniform(0.10, 0.22), r.uniform(0.16, 0.26))
            m.box((d * math.cos(a), sz[1] / 2, d * math.sin(a)), sz, yaw=r.uniform(0, 3.14), roll=r.uniform(-0.2, 0.2), col=col())
    return prop(m)

def build():
    D = M3 + '/Fantasy Props/'; out = {}
    out[38400] = prop(G.Model(D + 'Anvil_Log.gltf'))
    # anvil on a granite block: the anvil raised on a drawn block
    blk = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(blk)
    d.polygon([(8, 52), (16, 48), (24, 52), (24, 60), (16, 64), (8, 60)], fill=(96, 96, 100, 255))
    d.polygon([(8, 52), (16, 56), (16, 64), (8, 60)], fill=(120, 120, 126, 255)); d.polygon([(16, 56), (24, 52), (24, 60), (16, 64)], fill=(78, 78, 84, 255))
    d.polygon([(8, 52), (16, 48), (24, 52), (16, 56)], fill=(146, 146, 150, 255))
    a = prop(G.Model(D + 'Anvil.gltf'), shift=(0, -6)); blk.alpha_composite(a); out[38402] = blk
    cr = prop(Extra(G.Model(D + 'Cauldron.gltf'), [(0.66, 0.40)])); rr = [1.3, 2.1, 0.4]
    out[38404] = glow(paint(cr, lambda x, y: molten_px(rr, x, y, 0.1)), 16, 57, 15, a=80)
    out[38406] = paint(prop(Extra(G.Model(D + 'Bucket_Metal.gltf'), [(0.30, 0.20)]), scale=1.5), lambda x, y: (40, 58, 70) if (x + y) % 5 else (70, 96, 110))
    out[38408] = prop(G.Model(D + 'Whetstone.gltf'))
    ing = recol(ObjModel(M3 + '/RPG Pack 2/OBJ/Gold_Ingots.obj'), (0.30, 0.31, 0.34)); out[38410] = prop(ing)
    out[38412] = mould(5)
    out[38414] = furnace()
    out[38416] = wreck(0); out[38418] = wreck(1)
    for k in range(4): out[36300 + k] = molten_tile(36300 + k)
    return out

def sheet(sp, path):
    objs = [n for n in sorted(sp) if n >= 38000]
    img = Image.new('RGBA', (len(objs) * 72 + 300, 170), (58, 58, 52, 255)); d = ImageDraw.Draw(img)
    for k, n in enumerate(objs):
        img.alpha_composite(sp[n].resize((64, 128), Image.NEAREST), (k * 72 + 4, 6)); d.text((k * 72 + 6, 150), str(n), fill=(255, 255, 255, 255))
    # a little scene: dark flagstone with a molten channel
    S2 = wg.Sprites(sys.argv[1]); flag = [S2.get(n) for n in (37020, 37021, 37022, 37023)]
    N = 7; sc = Image.new('RGBA', (32 * N + 32, 16 * N + 40), (0, 0, 0, 0)); r = random.Random(3)
    lava = lambda x, y: y == 3 or (x == 1 and y >= 3)
    for x, y in sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1])):
        if lava(x, y): t = sp[36300 + r.randrange(4)]
        else:
            m = wg.mask_of(lambda dx, dy: 0 <= x + dx < N and 0 <= y + dy < N and lava(x + dx, y + dy))
            t = wg.blend(r.choice(flag), sp[36300 + r.randrange(4)], m, seed=x * 31 + y) if m else r.choice(flag)
        sx = 16 * (x + y); sy = 8 * (x - y) + 8 * N
        sc.alpha_composite(t, (sx, sy))
    img.alpha_composite(sc.resize((sc.width * 1, sc.height * 1)), (len(objs) * 72 + 20, 10))
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST); img.save(path)

if __name__ == '__main__':
    sp = build()
    if '--out' in sys.argv:
        o = sys.argv[sys.argv.index('--out') + 1]; os.makedirs(o, exist_ok=True)
        for n, im in sp.items():
            im.save(os.path.join(o, '%05d.png' % n))
            if n >= 38000: im.save(os.path.join(o, '%05d.png' % (n + 1)))
    if '--sheet' in sys.argv: sheet(sp, sys.argv[sys.argv.index('--sheet') + 1])
