#!/usr/bin/env python3
"""Chests whose lock faces north and east (turned away from the camera), made from the game's own
chest sprites 220/221 (lock facing south) and 222/223 (lock facing west).
    draw_chest_back.py <folder with 220.png..223.png (or orig_220.png...)> <out folder>
Writes 18130 (north, closed), 18131 (north, open), 18132 (east, closed), 18133 (east, open).

Turned around, the lock is on the far side: the long side we see is the chest's back, so the lock
plate is painted over with the planks next to it. The open ones keep the game's lid at the back:
a first try with the lid standing over the front edge (lid_to_front, kept below) looked like one
box stacked on another in the game."""
import os, sys
from PIL import Image


def load(src, n):
    for f in (f'{n}.png', f'orig_{n}.png'):
        p = os.path.join(src, f)
        if os.path.exists(p):
            return Image.open(p).convert('RGBA')
    raise SystemExit(f'{n}.png not found in {src}')


def unlock(im, box, dx, dy):
    """paint the lock plate over with the planks next to it (on the same face: dx across, dy along the slope)"""
    im = im.copy(); px = im.load(); src = im.copy().load()
    x0, y0, x1, y1 = box
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if px[x, y][3]:
                px[x, y] = src[x + dx, y + dy]
    return im


def lid_to_front(open_, edge, shift):
    """cut the lid off above the far long edge and set it down on the near one"""
    (ax, ay), (bx, by) = edge
    line = lambda x: ay + (x - ax) * (by - ay) / (bx - ax)
    W, H = open_.size
    src = open_.load()
    body = open_.copy(); pb = body.load()
    lid = Image.new('RGBA', open_.size, (0, 0, 0, 0)); pl = lid.load()
    for y in range(H):
        for x in range(W):
            if src[x, y][3] and y < line(x) - 0.5:
                pl[x, y] = src[x, y]; pb[x, y] = (0, 0, 0, 0)
    out = body.copy()
    out.alpha_composite(lid, shift)
    return out


# 220/221: the lock on the long side that faces down-right (south)
LOCK = (21, 47, 25, 53)       # the lock plate on that side
DX, DY = 5, -2                # planks to paint it over with
EDGE = ((7, 45), (22, 37))    # 221: the far long edge, where the lid is hinged
SHIFT = (9, 4)                # from the far long edge to the near one


def north(closed, open_):
    c = unlock(closed, LOCK, DX, DY)
    o = unlock(open_, LOCK, DX, DY)
    return c, o


# 222/223: the same chest drawn mirrored (lock on the long side that faces down-left, west);
# 222 lines up with 220 mirrored, 223 with 221 mirrored and one column to the right
def mirror_x(x, off): return 31 - x + off


def east(closed, open_):
    l0, l1 = sorted((mirror_x(LOCK[0], 0), mirror_x(LOCK[2], 0)))
    c = unlock(closed, (l0, LOCK[1], l1, LOCK[3]), -DX, DY)
    l0, l1 = sorted((mirror_x(LOCK[0], 1), mirror_x(LOCK[2], 1)))
    edge = ((mirror_x(EDGE[0][0], 1), EDGE[0][1]), (mirror_x(EDGE[1][0], 1), EDGE[1][1]))
    o = unlock(open_, (l0, LOCK[1], l1, LOCK[3]), -DX, DY)
    return c, o


if __name__ == '__main__':
    SRC, OUT = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    c, o = north(load(SRC, 220), load(SRC, 221))
    c.save(os.path.join(OUT, '18130.png')); o.save(os.path.join(OUT, '18131.png'))
    c, o = east(load(SRC, 222), load(SRC, 223))
    c.save(os.path.join(OUT, '18132.png')); o.save(os.path.join(OUT, '18133.png'))
