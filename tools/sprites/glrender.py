#!/usr/bin/env python3
"""A small glTF renderer for game sprites (no Blender, no GPU): reads .glb / .gltf, plays a skinned animation at a
time t, and draws the model with an orthographic camera at the game's angle (30 degrees down, the tile diamond is 2:1)
into a 64x64 sprite, rendered 4x larger and boxed down.

    from glrender import Model, render
    m = Model('Wolf.gltf'); img = render(m, anim='Walk', t=0.3, yaw=45)
"""
import json, struct, os, math
import numpy as np
from PIL import Image

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def q2m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(a, b, t):
    d = np.dot(a, b)
    if d < 0: b, d = -b, -d
    if d > 0.9995: r = a + t * (b - a); return r / np.linalg.norm(r)
    th = math.acos(d); s = math.sin(th)
    return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / s


class Model:
    def __init__(self, path):
        self.dir = os.path.dirname(os.path.abspath(path))
        raw = open(path, 'rb').read()
        if raw[:4] == b'glTF':
            L = struct.unpack_from('<I', raw, 12)[0]
            self.J = json.loads(raw[20:20 + L])
            o = 20 + L
            bl = struct.unpack_from('<I', raw, o)[0]
            self.bufs = [raw[o + 8:o + 8 + bl]]
        else:
            self.J = json.loads(raw)
            self.bufs = []
            for b in self.J.get('buffers', []):
                u = b['uri']
                if u.startswith('data:'):
                    import base64; self.bufs.append(base64.b64decode(u.split(',', 1)[1]))
                else:
                    self.bufs.append(open(os.path.join(self.dir, u), 'rb').read())
        J = self.J
        self.nodes = J['nodes']
        self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get('children', []): self.parent[c] = i
        self.anims = {a.get('name', str(k)): a for k, a in enumerate(J.get('animations', []))}
        self.texcache = {}
        self.acc = {}
        # the meshes to draw: (node index, mesh index, skin index or None)
        self.draw = [(i, n['mesh'], n.get('skin')) for i, n in enumerate(self.nodes) if 'mesh' in n]

    def a(self, k):
        if k in self.acc: return self.acc[k]
        A = self.J['accessors'][k]; bv = self.J['bufferViews'][A['bufferView']]
        buf = self.bufs[bv['buffer']]; off = bv.get('byteOffset', 0) + A.get('byteOffset', 0)
        n, c, dt = A['count'], NC[A['type']], CT[A['componentType']]
        isz = np.dtype(dt).itemsize
        stride = bv.get('byteStride') or isz * c
        if stride == isz * c:
            arr = np.frombuffer(buf, dt, n * c, off).reshape(n, c)
        else:
            arr = np.stack([np.frombuffer(buf, dt, c, off + i * stride) for i in range(n)])
        arr = arr.astype(np.float64) if dt == np.float32 else arr
        if A.get('normalized') and dt != np.float32:
            arr = arr.astype(np.float64) / np.iinfo(dt).max
        self.acc[k] = arr
        return arr

    def anim_length(self, name):
        a = self.anims[name]
        return max(self.a(s['input']).max() for s in a['samplers'])

    def pose(self, anim=None, t=0.0):
        """local TRS of every node at time t of animation anim"""
        T = [np.array(n.get('translation', [0, 0, 0]), float) for n in self.nodes]
        R = [np.array(n.get('rotation', [0, 0, 0, 1]), float) for n in self.nodes]
        S = [np.array(n.get('scale', [1, 1, 1]), float) for n in self.nodes]
        if anim:
            a = self.anims[anim]
            for ch in a['channels']:
                s = a['samplers'][ch['sampler']]; tg = ch['target']; node = tg.get('node'); path = tg['path']
                if node is None or path == 'weights': continue
                ti = self.a(s['input'])[:, 0]; vo = self.a(s['output'])
                cubic = s.get('interpolation') == 'CUBICSPLINE'
                if cubic: vo = vo.reshape(len(ti), 3, -1)[:, 1]
                tt = min(max(t, ti[0]), ti[-1])
                j = int(np.searchsorted(ti, tt, side='right')) - 1; j = max(0, min(j, len(ti) - 1))
                if j >= len(ti) - 1 or s.get('interpolation') == 'STEP':
                    v = vo[j]
                else:
                    f = (tt - ti[j]) / max(1e-9, ti[j + 1] - ti[j])
                    v = slerp(vo[j] / np.linalg.norm(vo[j]), vo[j + 1] / np.linalg.norm(vo[j + 1]), f) if path == 'rotation' else vo[j] * (1 - f) + vo[j + 1] * f
                {'translation': T, 'rotation': R, 'scale': S}[path][node] = np.array(v, float)
        L = []
        for i in range(len(self.nodes)):
            n = self.nodes[i]
            if 'matrix' in n and not anim:
                L.append(np.array(n['matrix'], float).reshape(4, 4).T); continue
            M = np.eye(4); M[:3, :3] = q2m(R[i]) * S[i]; M[:3, 3] = T[i]; L.append(M)
        G = [None] * len(self.nodes)
        def g(i):
            if G[i] is None: G[i] = (g(self.parent[i]) @ L[i]) if i in self.parent else L[i]
            return G[i]
        for i in range(len(self.nodes)): g(i)
        return G

    def tex(self, ti):
        if ti in self.texcache: return self.texcache[ti]
        tx = self.J['textures'][ti]; im = self.J['images'][tx['source']]
        if 'bufferView' in im:
            bv = self.J['bufferViews'][im['bufferView']]; o = bv.get('byteOffset', 0)
            import io; img = Image.open(io.BytesIO(self.bufs[bv['buffer']][o:o + bv['byteLength']]))
        else:
            img = Image.open(os.path.join(self.dir, im['uri']))
        arr = np.asarray(img.convert('RGB'), np.float64) / 255.0
        self.texcache[ti] = arr
        return arr

    def triangles(self, anim=None, t=0.0):
        """world-space triangles: positions (n,3,3), normals (n,3,3), colours (n,3,3)"""
        G = self.pose(anim, t)
        P, N, C, Q = [], [], [], []
        for ni, mi, si in self.draw:
            if si is not None:
                sk = self.J['skins'][si]
                ib = self.a(sk['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1) if 'inverseBindMatrices' in sk else np.tile(np.eye(4), (len(sk['joints']), 1, 1))
                JM = np.stack([G[j] for j in sk['joints']]) @ ib
            for pr in self.J['meshes'][mi]['primitives']:
                if pr.get('mode', 4) != 4: continue
                at = pr['attributes']
                pos = self.a(at['POSITION'])[:, :3]; rest = pos.copy()
                nor = self.a(at['NORMAL'])[:, :3] if 'NORMAL' in at else None
                if si is not None and 'JOINTS_0' in at:
                    jn = self.a(at['JOINTS_0']).astype(int); w = self.a(at['WEIGHTS_0'])
                    w = w / np.maximum(1e-9, w.sum(1, keepdims=True))
                    M = np.einsum('vk,vkij->vij', w, JM[jn])
                    pos = np.einsum('vij,vj->vi', M[:, :3, :3], pos) + M[:, :3, 3]
                    if nor is not None: nor = np.einsum('vij,vj->vi', M[:, :3, :3], nor)
                else:
                    M = G[ni]; pos = pos @ M[:3, :3].T + M[:3, 3]
                    if nor is not None: nor = nor @ M[:3, :3].T
                idx = self.a(pr['indices'])[:, 0].astype(int).reshape(-1, 3) if 'indices' in pr else np.arange(len(pos)).reshape(-1, 3)
                mat = self.J['materials'][pr['material']] if 'material' in pr else {}
                pb = mat.get('pbrMetallicRoughness', {})
                base = np.array(pb.get('baseColorFactor', [1, 1, 1, 1])[:3], float)
                col = np.tile(base, (len(pos), 1))
                if 'COLOR_0' in at: col = col * self.a(at['COLOR_0'])[:, :3]
                if 'baseColorTexture' in pb and 'TEXCOORD_0' in at:
                    tx = self.tex(pb['baseColorTexture']['index']); uv = self.a(at['TEXCOORD_0'])
                    h, wd = tx.shape[:2]
                    u = (uv[:, 0] % 1.0) * (wd - 1); v = (uv[:, 1] % 1.0) * (h - 1)
                    col = col * tx[v.astype(int), u.astype(int)]
                if nor is None:
                    tri = pos[idx]; fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
                    N.append(np.repeat(fn[:, None], 3, 1))
                else:
                    N.append(nor[idx])
                P.append(pos[idx]); C.append(col[idx]); Q.append(rest[idx])
        P, N, C = np.concatenate(P), np.concatenate(N), np.concatenate(C)
        self.rest = np.concatenate(Q)
        N = N / np.maximum(1e-9, np.linalg.norm(N, axis=2, keepdims=True))
        return P, N, C


def camera(yaw_deg, pitch_deg=30.0, depth=1.0):
    """rotation: model yaw (0 = facing the viewer, + = turned to screen right), then the camera's 30 degree tilt.
    Returns R mapping model coords (y up, +z forward) to view coords (x right, y up, z towards the viewer)."""
    y = math.radians(yaw_deg); p = math.radians(pitch_deg)
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    D = np.diag([1.0, 1.0, depth])      # depth < 1: the ground squeezed towards the viewer (long animals keep all feet near the shadow)
    return Rx @ D @ Ry


LIGHT = np.array([-0.55, 0.75, 0.45]); LIGHT = LIGHT / np.linalg.norm(LIGHT)   # view space: from the upper left, in front


def raster(P, N, C, W, H, Q=None, tex=None):
    """P: view-space triangles already in pixels (x right, y down, z towards viewer); returns rgb (H,W,3), mask"""
    img = np.zeros((H, W, 3)); zb = np.full((H, W), -1e9); msk = np.zeros((H, W), bool)
    for k in range(len(P)):
        p = P[k]
        x0, x1 = int(max(0, math.floor(p[:, 0].min()))), int(min(W - 1, math.ceil(p[:, 0].max())))
        y0, y1 = int(max(0, math.floor(p[:, 1].min()))), int(min(H - 1, math.ceil(p[:, 1].max())))
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p[0, :2], p[1, :2], p[2, :2]
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12: continue
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not ins.any(): continue
        z = w0 * p[0, 2] + w1 * p[1, 2] + w2 * p[2, 2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        upd = ins & (z > sub)
        if not upd.any(): continue
        n = w0[..., None] * N[k, 0] + w1[..., None] * N[k, 1] + w2[..., None] * N[k, 2]
        n = n / np.maximum(1e-9, np.linalg.norm(n, axis=-1, keepdims=True))
        if n[..., 2].mean() < 0: n = -n          # two-sided
        c = w0[..., None] * C[k, 0] + w1[..., None] * C[k, 1] + w2[..., None] * C[k, 2]
        if tex is not None:
            q = w0[..., None] * Q[k, 0] + w1[..., None] * Q[k, 1] + w2[..., None] * Q[k, 2]
            c = c * tex(q)[..., None]
        lam = np.clip((n * LIGHT).sum(-1), 0, 1)
        sh = 0.42 + 0.78 * lam
        col = c * sh[..., None]
        sub[upd] = z[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = col[upd]
        msk[y0:y1 + 1, x0:x1 + 1][upd] = True
    return img, msk


def render(model, anim=None, t=0.0, yaw=0.0, scale=30.0, size=64, ox=32.0, oy=56.0, ss=4, fix=None, outline=True, tex=None, depth=1.0, shadow=0.0):
    """one sprite: scale = pixels per model unit; (ox, oy) = where the model's origin (on the ground) lands.
    fix: an optional function on the posed triangles (e.g. to centre / normalise the model)."""
    P, N, C = model.triangles(anim, t)
    if fix: P = fix(P)
    R = camera(yaw, depth=depth)
    V = P @ R.T; Nn = N @ camera(yaw).T
    S = scale * ss
    X = V[..., 0] * S + ox * ss; Y = -V[..., 1] * S + oy * ss; Z = V[..., 2]
    img, m = raster(np.stack([X, Y, Z], -1), Nn, C, size * ss, size * ss, model.rest, tex)
    # box down: colour = mean of the covered sub-pixels, solid where at least 40% is covered
    a = m.reshape(size, ss, size, ss).mean((1, 3))
    s = (img * m[..., None]).reshape(size, ss, size, ss, 3).sum((1, 3))
    col = s / np.maximum(1e-9, m.reshape(size, ss, size, ss).sum((1, 3)))[..., None]
    solid = a >= 0.4
    sha = None
    if shadow:      # its own shadow: the body pressed flat onto the ground (light from above, a little from the upper left)
        F = P.copy(); h = F[..., 1].copy(); F[..., 1] = 0; F[..., 0] += h * 0.25; F[..., 2] -= h * 0.10
        Vf = F @ R.T
        Xf = Vf[..., 0] * S + ox * ss; Yf = -Vf[..., 1] * S + oy * ss; Zf = Vf[..., 2]
        _, ms = raster(np.stack([Xf, Yf, Zf], -1), Nn, C, size * ss, size * ss)
        cov = ms.reshape(size, ss, size, ss).mean((1, 3))
        k = np.array([0.25, 0.5, 0.25]); cov = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 0, cov)
        cov = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, cov)
        sha = np.clip(cov * 1.6, 0, 1) * shadow
    out = np.zeros((size, size, 4), np.uint8)
    out[..., :3] = np.clip(col * 255, 0, 255).astype(np.uint8)
    out[..., 3] = np.where(solid, 255, 0)
    if sha is not None:
        sh = (~solid) & (sha > 0.06)
        out[sh, :3] = 0; out[sh, 3] = (sha[sh] * 255).astype(np.uint8)
    if outline:     # a dark edge where the sprite meets the background, as the game's renders have
        e = solid & ~(np.roll(solid, 1, 0) & np.roll(solid, -1, 0) & np.roll(solid, 1, 1) & np.roll(solid, -1, 1))
        out[e, :3] = (out[e, :3] * 0.55).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def fur(freq=9.0, amp=0.28, seed=7):
    """speckled fur / grain: value noise on the model's rest pose, so it sticks to the body while it moves"""
    rng = np.random.default_rng(seed); tbl = rng.random(1 << 16)
    def h(i, j, k): return tbl[((i * 73856093) ^ (j * 19349663) ^ (k * 83492791)) & 0xffff]
    def f(q):
        p = q * freq; i = np.floor(p).astype(np.int64); fr = p - i; u = fr * fr * (3 - 2 * fr)
        v = 0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = (u[..., 0] if dx else 1 - u[..., 0]) * (u[..., 1] if dy else 1 - u[..., 1]) * (u[..., 2] if dz else 1 - u[..., 2])
                    v = v + w * h(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz)
        g = h(np.floor(q[..., 0] * freq * 3.1).astype(np.int64), np.floor(q[..., 1] * freq * 3.1).astype(np.int64), np.floor(q[..., 2] * freq * 3.1).astype(np.int64))
        return 1 + amp * ((v - 0.5) * 1.4 + (g - 0.5) * 0.8)
    return f
