"""A Wavefront .obj (+ .mtl Kd colours) with glrender.Model's triangles() interface (Nov 16: Quaternius RPG packs)."""
import os, numpy as np
class ObjModel:
    def __init__(self, path):
        kd, cur = {}, None
        d = os.path.dirname(path); V, VN, P, N, C, MT = [], [], [], [], [], []; mat = ''
        col = np.array([.8, .8, .8])
        for ln in open(path):
            t = ln.split()
            if not t: continue
            if t[0] == 'mtllib':
                for m in open(os.path.join(d, ' '.join(t[1:]))):
                    u = m.split()
                    if u and u[0] == 'newmtl': cur = ' '.join(u[1:])
                    elif u and u[0] == 'Kd': kd[cur] = np.array(list(map(float, u[1:4])))
            elif t[0] == 'v': V.append(list(map(float, t[1:4])))
            elif t[0] == 'vn': VN.append(list(map(float, t[1:4])))
            elif t[0] == 'usemtl': mat = ' '.join(t[1:]); col = kd.get(mat, col)
            elif t[0] == 'f':
                vs = [x.split('/') for x in t[1:]]
                for k in range(1, len(vs) - 1):
                    tri = [vs[0], vs[k], vs[k + 1]]
                    P.append([V[int(a[0]) - 1] for a in tri])
                    if len(tri[0]) > 2 and tri[0][2]: N.append([VN[int(a[2]) - 1] for a in tri])
                    else:
                        p = np.array(P[-1]); n = np.cross(p[1] - p[0], p[2] - p[0]); N.append([n] * 3)
                    C.append([col] * 3); MT.append(mat)
        self.P, self.N, self.C = np.array(P, float), np.array(N, float), np.array(C, float)
        self.mat = np.array(MT); self.keep = None; self.recol = {}
        self.N /= np.maximum(1e-9, np.linalg.norm(self.N, axis=2, keepdims=True))
    def triangles(self, anim=None, t=0.0):
        k = np.ones(len(self.P), bool) if self.keep is None else self.keep
        C = self.C.copy()
        for m, c in self.recol.items(): C[self.mat == m] = c
        self.rest = self.P[k].copy(); return self.P[k].copy(), self.N[k].copy(), C[k]
