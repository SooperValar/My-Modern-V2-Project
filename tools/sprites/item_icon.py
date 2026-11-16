#!/usr/bin/env python3
"""A 32x32 item picture from a glTF prop (Nov 15: the quest items), at the game's camera, lit like the wolf.
    item_icon.py <model.gltf> <out.png> [--yaw 35] [--tint rrggbb] [--size 22] [--mix 0.6] [--tilt 0]"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glrender import Model, render, fur
A = sys.argv
def opt(k, d): return type(d)(A[A.index(k) + 1]) if k in A else d
from objmodel import ObjModel
m = ObjModel(A[1]) if A[1].endswith('.obj') else Model(A[1])
P, N, C = m.triangles()
lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0); c = (lo + hi) / 2
tilt = opt('--tilt', 0.0)
def fix(P):
    Q = P - c
    if tilt:
        import math; a = math.radians(tilt); R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]); Q = Q @ R.T
    roll = opt('--roll', 0.0)
    if roll:
        import math; a = math.radians(roll); R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]]); Q = Q @ R.T
    return Q
# size: the biggest screen extent ~ size px
sc = opt('--size', 22) / max(hi - lo)
tint = opt('--tint', '')
bright = opt('--bright', 1.6)
orig0 = m.triangles
def trib(anim=None, t=0.0):
    P, N, C = orig0(anim, t); return P, N, np.clip(C ** 0.8 * bright, 0, 1)
m.triangles = trib
if tint:
    tc = np.array([int(tint[i:i + 2], 16) / 255 for i in (0, 2, 4)]); mix = opt('--mix', 0.6)
    orig = m.triangles
    def tri(anim=None, t=0.0):
        P, N, C = orig(anim, t); lum = C.mean(-1, keepdims=True); ref = max(1e-3, float(np.percentile(lum, 85)))
        return P, N, C * (1 - mix) + np.clip(lum / ref, 0.25, 1.3) * tc * mix
    m.triangles = tri
def go(): return render(m, None, 0, yaw=opt('--yaw', 35.0), scale=sc, size=32, ox=16, oy=17, fix=fix, tex=fur(9.0, 0.10))
glass = opt('--glass', '')     # .obj only: bottle glass drawn in this colour, the liquid and cork drawn over it
for kv in opt('--recol', '').split(','):
    if '=' in kv: k, v = kv.split('='); m.recol[k] = np.array([int(v[i:i + 2], 16) / 255 for i in (0, 2, 4)]) ** 2.2
liq = opt('--liquid', '')
if liq:
    for mm in set(m.mat):
        if mm.startswith('Liquid'): m.recol[mm] = np.array([int(liq[i:i + 2], 16) / 255 for i in (0, 2, 4)]) ** 2.2
if glass:
    m.recol['Glass'] = np.array([int(glass[i:i + 2], 16) / 255 for i in (0, 2, 4)]) ** 2.2
    a = go(); m.keep = m.mat != 'Glass'; b = go(); a.alpha_composite(b); a.save(A[2]); sys.exit()
im = render(m, None, 0, yaw=opt('--yaw', 35.0), scale=sc, size=32, ox=16, oy=17, fix=fix, tex=fur(9.0, 0.10))
im.save(A[2])
