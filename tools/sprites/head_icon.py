#!/usr/bin/env python3
"""A 32x32 item picture of a creature's head, cut from its glTF model (Nov 15: wolf heads for the Hunters' Lodge bounty).
    head_icon.py <model.gltf> <out.png> [--tint Main=rrggbb,...] [--front 0.22] [--above 0.5]"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glrender import Model, render, fur
A = sys.argv
front = float(A[A.index('--front') + 1]) if '--front' in A else 0.22
above = float(A[A.index('--above') + 1]) if '--above' in A else 0.5
class Head(Model):
    def triangles(self, anim=None, t=0.0):
        P, N, C = Model.triangles(self, anim, t)
        if self.cut is None: return P, N, C
        zc, yc = self.cut
        k = (P[..., 2].min(1) > zc) & (P[..., 1].min(1) > yc)
        self.rest = self.rest[k]; return P[k], N[k], C[k]
m = Head(A[1]); m.cut = None
for mat in m.J['materials']:
    pb = mat.setdefault('pbrMetallicRoughness', {}); pb['baseColorFactor'] = [c ** (1 / 2.2) for c in pb.get('baseColorFactor', [1, 1, 1, 1])[:3]] + [1]
if '--tint' in A:
    for kv in A[A.index('--tint') + 1].split(','):
        k, v = kv.split('=')
        for mat in m.J['materials']:
            if mat.get('name') == k: mat['pbrMetallicRoughness']['baseColorFactor'] = [int(v[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1]
P, _, _ = m.triangles('Idle', 0); z = P[..., 2]; y = P[..., 1]
m.cut = (z.max() - (z.max() - z.min()) * front, y.min() + (y.max() - y.min()) * above)
P, N, C = m.triangles('Idle', 0); lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0); c = (lo + hi) / 2
sc = 17 / max(hi - lo)
im = render(m, 'Idle', 0, yaw=-50, scale=sc, size=32, ox=16, oy=24, fix=lambda P: P - np.array([c[0], lo[1], c[2]]), tex=fur(3.0, 0.35))
a = np.array(im); sol = a[..., 3] == 255
bot = np.nonzero(sol.any(1))[0].max()
for x in np.nonzero(sol[bot])[0]: a[bot, x, :3] = (110, 18, 18)      # the cut
Image.fromarray(a).save(A[2])
