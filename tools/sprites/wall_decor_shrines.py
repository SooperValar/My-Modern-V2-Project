"""Nov 16, third pass (wall_decor shrines, sprites 48020-48025): the game's light kept on every version. Needs fix3.py
import os
(the face regions, plain side, statue mask) next to it; run in the folder with the game sprites as NNNNN.png, writes out/."""
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wall_decor_shrines_base.py')).read().split("for i, s in enumerate((792, 914)):")[0])
def diamond(x, y): return abs(x - 15.5) * .5 + abs(y - 30) <= 8
def top_face_plain(a):
    out = a.copy()
    for y in range(64):
        for x in range(32):
            if TOP[y, x] and diamond(x, y):
                g = random.uniform(.85, 1.12); out[y, x] = (52 * g, 41 * g, 0, 255)
            elif TOP[y, x]: out[y, x] = 0
    return out
def objects(a):
    m = TOP & (a[..., 3] > 0)
    br = a[..., :3].sum(-1)
    obj = np.zeros_like(m)
    for y, x in zip(*np.nonzero(m)):
        if not diamond(x, y) or br[y, x] > 130: obj[y, x] = True
    cols = [x for x in range(32) if obj[:, x].any()]
    tall = [x for x in cols if obj[:23, x].any()]                 # the statue: what reaches high
    st = list(range(min(tall) - 1, max(tall) + 2))
    rest = [x for x in cols if x not in st]
    obj2 = obj.copy()
    return obj, [g for g in (rest, st) if g]
def turned_top(a, statue_dark=1.0, move=True):
    obj, groups = objects(a)
    out = top_face_plain(a)
    tallest = groups[-1]; tallest_set = set(tallest)
    # draw what is further back first: the bowl, then the statue
    for g in groups:
        x0, x1 = min(g), max(g); dx = ((31 - x1) - x0) if move else 0
        k = statue_dark if g is tallest else 1.0
        for y, x in zip(*np.nonzero(obj[:, x0:x1 + 1])):
            x += x0; nx = x + dx
            if g is not tallest and x in tallest_set: continue
            if 0 <= nx < 32: out[y, nx] = a[y, x]; out[y, nx, :3] = a[y, x, :3] * k
    return out
def dark_right2(a, relief):
    out = a.copy()
    for y, x in zip(*np.nonzero(RF & (a[..., 3] > 0))):
        c = np.array([26, 20, 0.])
        if relief is not None:
            sx = 31 - x; sy = int(round(y - (38 - .5 * (x - 16)) + 30 + .5 * sx))
            if 0 <= sy < 64 and LF[sy, sx] and relief[sy, sx, 3] > 0:
                c = np.clip(c + (relief[sy, sx, :3] - np.array([200, 170, 0])) * .4 + np.array([18, 14, 0]), 0, 255)
        out[y, x, :3] = c
    return out
for i, s in enumerate((792, 914)):
    a = ld(s)
    body = dark_right2(plain_left(a), a)
    w = turned_top(a); w[~TOP] = body[~TOP]; save(48020 + 3 * i, w)
    back = dark_right2(plain_left(a), None)
    n = turned_top(a, .55); n[~TOP] = back[~TOP]; save(48021 + 3 * i, n)
    e = turned_top(a, .55, move=False); e[~TOP] = back[~TOP]; save(48022 + 3 * i, e)
print('ok')
