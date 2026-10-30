#!/usr/bin/env python3
"""A treasure chest drawn from a small 3D model, in the look of the game's own chest (sprites 220-223:
same size, palette and light from the upper left), so it can face any of the four directions.
    render_chest.py <out folder> [<folder with orig_220.png.. for a side-by-side check>]

Directions are where the lock points (north = smaller x = up-left on the screen):
  south  lock on the long side facing down-right (like 220/221)
  west   lock on the long side facing down-left  (like 222/223)
  north  the chest's back faces down-right: hinges instead of the lock; open, its lid stands at the front
  east   the same, facing down-left
"""
import os, sys
import numpy as np
from PIL import Image

# ---- the chest, in its own coordinates: u along the long side, v across (v = D is the lock side), z up
L, D, HB = 14.5, 8.6, 12.0      # length, depth, body height
RZ = 6.6                        # how high the lid's dome rises
WALL = 0.9                      # board thickness (open box, lid shell)
OPEN = np.radians(125)          # how far an open lid swings back (seen from behind, less hides the open box)

# palette ramps, dark to light, taken from 220-223
WOOD = [(32, 12, 0), (41, 16, 8), (49, 20, 8), (57, 24, 8), (65, 28, 16), (74, 32, 16), (82, 36, 16), (90, 40, 16),
        (98, 44, 24), (106, 48, 24), (115, 56, 32), (123, 64, 32), (131, 72, 41), (148, 80, 41)]
IRON = [(8, 12, 16), (16, 16, 16), (16, 20, 24), (24, 24, 24), (24, 28, 32), (32, 36, 41), (41, 44, 49), (49, 52, 57),
        (57, 60, 65), (74, 80, 90), (90, 89, 98), (140, 140, 150)]
LIGHT = np.array([-0.70, -0.40, 0.60]); LIGHT /= np.linalg.norm(LIGHT)   # world (a, b, z): from the upper left
CAM = np.array([1.0, -1.0, -1.0]); CAM /= np.linalg.norm(CAM)          # the view direction (into the screen)


def to_world(face):
    """local (u, v, z) -> world (a, b, z). world: a goes up-right on the screen, b down-right."""
    if face == 'south': return lambda u, v: (u, v)
    if face == 'north': return lambda u, v: (L - u, D - v)
    if face == 'west':  return lambda u, v: (D - v, u)
    if face == 'east':  return lambda u, v: (v, L - u)


def to_local(face):
    if face == 'south': return lambda a, b: (a, b)
    if face == 'north': return lambda a, b: (L - a, D - b)
    if face == 'west':  return lambda a, b: (b, D - a)
    if face == 'east':  return lambda a, b: (L - b, a)


def lid_frame(u, v, z, opened):
    """a point -> the closed lid's coordinates (the open lid turned back about the hinge at v=0, z=HB)"""
    if not opened: return v, z
    c, s = np.cos(OPEN), np.sin(OPEN)
    dv, dz = v, z - HB                       # turn by -OPEN: the open lid back to where it was closed
    return c * dv + s * dz, -s * dv + c * dz + HB


def solid(u, v, z, opened):
    """what is at each point: 0 nothing, 1 body (outside), 2 inside of the box, 3 lid outside, 4 lid inside"""
    out = np.zeros(u.shape, np.int8)
    inb = (u >= 0) & (u <= L) & (v >= 0) & (v <= D) & (z >= 0) & (z <= HB)
    if opened:
        hollow = (u > WALL) & (u < L - WALL) & (v > WALL) & (v < D - WALL) & (z > WALL)
        out[inb & ~hollow] = 1
    else:
        out[inb] = 1
    lv, lz = lid_frame(u, v, z, opened)
    e = ((lv - D / 2) / (D / 2)) ** 2 + ((lz - HB) / RZ) ** 2
    lid = (u >= 0) & (u <= L) & (lz >= HB) & (e <= 1)
    if opened:
        ei = ((lv - D / 2) / (D / 2 - WALL)) ** 2 + ((lz - HB) / (RZ - WALL)) ** 2
        lid &= ~((ei < 1) & (u > WALL) & (u < L - WALL))
    out[lid & (out == 0)] = 3
    return out


def render(face, opened, anchor, S=6, zoom=1):
    """anchor: screen position of the chest's lowest ground corner. Returns a 32x64 RGBA image."""
    tw, tl = to_world(face), to_local(face)
    # world extent of the footprint, and the lowest corner on the screen (smallest a, largest b)
    corners = [tw(u, v) for u in (0, L) for v in (0, D)]
    a0 = min(c[0] for c in corners); b1 = max(c[1] for c in corners)
    W, H = 32 * S * zoom, 64 * S * zoom
    ys, xs = np.mgrid[0:H, 0:W]
    sx = (xs + 0.5) / S / zoom - anchor[0]; sy = (ys + 0.5) / S / zoom - anchor[1]
    # screen: sx = (a - a0) + (b - b1), sy = -0.5 (a - a0) + 0.5 (b - b1) - z ; a point at z = 0:
    bb = (sx + 2 * sy) / 2; aa = sx - bb
    P = np.stack([aa + a0, bb + b1, np.zeros_like(aa)], -1).reshape(-1, 3)
    P = P - CAM * 40                         # start in front, toward the camera
    n = P.shape[0]
    hit = np.zeros(n, np.int8); where = np.zeros((n, 3))
    alive = np.ones(n, bool)
    step = 0.05
    for i in range(int(80 / step)):
        idx = np.nonzero(alive)[0]
        if not len(idx): break
        p = P[idx] + CAM * (i * step)
        u, v = tl(p[:, 0], p[:, 1]); z = p[:, 2]
        s = solid(u, v, z, opened)
        got = s > 0
        if got.any():
            gi = idx[got]
            hit[gi] = s[got]; where[gi] = np.stack([u[got], v[got], z[got]], -1)
            alive[gi] = False
    return shade(hit, where, face, opened, tw, S, W, H)


def normal_local(u, v, z, kind, opened):
    """the surface normal at a hit (local coordinates), from small differences of the solid"""
    e = 0.12
    g = np.zeros((len(u), 3))
    for k, (du, dv, dz) in enumerate(((e, 0, 0), (0, e, 0), (0, 0, e))):
        a = (solid(u + du, v + dv, z + dz, opened) > 0).astype(float)
        b = (solid(u - du, v - dv, z - dz, opened) > 0).astype(float)
        g[:, k] = b - a
    nn = np.linalg.norm(g, axis=1, keepdims=True)
    g = np.where(nn > 0, g / np.maximum(nn, 1e-9), np.array([0, 0, 1.0]))
    return g


def shade(hit, where, face, opened, tw, S, W, H):
    rng = np.random.default_rng(7)
    u, v, z = where[:, 0], where[:, 1], where[:, 2]
    nl = normal_local(u, v, z, hit, opened)
    # local normal -> world normal
    o = np.array(tw(0.0, 0.0)); ex = np.array(tw(1.0, 0.0)) - o; ey = np.array(tw(0.0, 1.0)) - o
    nw = np.stack([nl[:, 0] * ex[0] + nl[:, 1] * ey[0], nl[:, 0] * ex[1] + nl[:, 1] * ey[1], nl[:, 2]], -1)
    lam = np.clip(nw @ LIGHT, 0, 1)
    lit = 0.14 + 0.76 * lam ** 0.75
    lv, lz = lid_frame(u, v, z, opened)
    onlid = hit == 3
    inside = (hit == 1) & opened & (u > WALL - 0.05) & (u < L - WALL + 0.05) & (v > WALL - 0.05) & (v < D - WALL + 0.05) & (z > WALL - 0.05)
    # the lid's inner side (its underside, seen when open)
    lid_in = onlid & opened & ((((lv - D / 2) / (D / 2 - WALL)) ** 2 + ((lz - HB) / (RZ - WALL)) ** 2) < 1.25) & (u > WALL - 0.05) & (u < L - WALL + 0.05)
    lid_in |= onlid & opened & (np.abs(lz - HB) < 0.25)
    # iron: corner posts, top and bottom rims, the lid's end bands, middle band and rim, lock, hinges
    iron = np.zeros(len(u), bool)
    body = hit == 1
    BW = 1.55                                               # iron band width (about 2 pixels, as in the game's chest)
    edge_u = (u < BW) | (u > L - BW); edge_v = (v < BW) | (v > D - BW)
    iron |= body & edge_u & edge_v
    iron |= body & ~inside & ((z > HB - BW) | (z < 0.8))
    cap = onlid & (np.abs(nl[:, 0]) > 0.6)                  # the lid's flat ends
    ecap = ((lv - D / 2) / (D / 2)) ** 2 + ((lz - HB) / RZ) ** 2
    iron |= onlid & ~cap & ((u < BW) | (u > L - BW) | (np.abs(u - L / 2) < 0.8))
    iron |= cap & (ecap > 0.45) & ~lid_in                   # the band around each end's arch
    iron |= onlid & (np.abs(lz - HB) < 1.0) & ~lid_in
    # an open lid seen from behind faces away from the light: lift its outside a little so it reads as a lid
    lit = np.where(onlid & opened & ~lid_in, np.maximum(lit, 0.30 + 0.5 * lit), lit)
    front = body & (v > D - 0.05) & ~inside
    back = body & (v < 0.05) & ~inside
    lock = front & (np.abs(u - L / 2) < 1.25) & (z > HB - 5.2) & (z < HB - 0.9)
    keyhole = lock & (np.abs(u - L / 2) < 0.35) & (z > HB - 4.2) & (z < HB - 2.6)
    hinge_u = (np.abs(u - L * 0.27) < 0.7) | (np.abs(u - L * 0.73) < 0.7)
    hinge = back & hinge_u & (z > HB - 4.0)
    hinge |= onlid & hinge_u & (lv < 1.6)
    iron |= lock | hinge
    # wood: boards with darker seams and a little grain
    seam = np.zeros(len(u), bool)
    seam |= body & ~iron & ~inside & (np.mod(z, 2.9) < 0.45)
    ang = np.arctan2((lz - HB) / RZ, (lv - D / 2) / (D / 2))
    seam |= onlid & ~iron & (np.mod(ang, 0.62) < 0.11)
    grain = rng.integers(-1, 2, len(u))
    wi = np.clip(np.round(lit * (len(WOOD) - 1)) + grain - seam * 3, 0, len(WOOD) - 1).astype(int)
    dark = inside | lid_in
    wi = np.where(dark, np.clip((wi * 0.45).astype(int) + grain, 0, 5), wi)
    ii = np.clip(np.round(lit * (len(IRON) - 2)), 0, len(IRON) - 2).astype(int)
    ii = np.where(keyhole, 0, ii)
    ii = np.where(hinge & (lit > 0.7), ii + 1, ii)
    ii = np.where(iron & (lit > 0.9) & (grain > 0), len(IRON) - 3, ii)    # a few glints on lit iron, as in the game's art
    col = np.where(iron[:, None], np.array(IRON)[ii], np.array(WOOD)[wi])
    img = np.zeros((len(u), 4), np.uint8)
    img[:, :3] = col; img[:, 3] = np.where(hit > 0, 255, 0)
    big = img.reshape(H, W, 4)
    # one sample per pixel (the middle one): crisp, like hand-placed pixels
    small = big[S // 2::S, S // 2::S].copy()
    # a dark outline where the chest meets the background
    a = small[:, :, 3] > 0
    edge = a & ~(np.roll(a, 1, 0) & np.roll(a, -1, 0) & np.roll(a, 1, 1) & np.roll(a, -1, 1))
    small[edge, :3] = np.minimum(small[edge, :3], np.array(IRON[1]))
    return Image.fromarray(small, 'RGBA')


SETS = {   # number: (face, open, anchor = lowest corner on the screen, as in the game's own sprites)
    18130: ('north', False, (16.5, 61.0)), 18131: ('north', True, (16.5, 61.0)),
    18132: ('east', False, (16.5, 61.0)), 18133: ('east', True, (16.5, 61.0)),
}

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for nr, (f, o, an) in SETS.items():
        render(f, o, an).save(os.path.join(out, f'{nr}.png'))
    for f, o, an, nm in (('south', False, (16.5, 61.0), 's0'), ('south', True, (16.5, 61.0), 's1'),
                         ('west', False, (16.5, 61.0), 'w0'), ('west', True, (16.5, 61.0), 'w1')):
        render(f, o, an).save(os.path.join(out, f'check_{nm}.png'))
