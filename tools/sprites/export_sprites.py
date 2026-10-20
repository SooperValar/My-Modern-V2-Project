#!/usr/bin/env python3
"""Export a character's sprite frames from the client's graphics files to PNGs.

    export_sprites.py <client folder> <first sprite> <out folder> [count]

Reads gfx/NNNNN.png, then pnglib, then gx00 (the same order the client uses),
writes <out folder>/NNNNN.png with the colour key (magenta) made transparent.
A character uses 448 sprite numbers (count, default 448); unused ones are skipped.
Used to make ORIGINAL folders for the V2 Sprite Recolor Tool.
"""
import os, struct, sys
from PIL import Image

def main():
    client, first, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    count = int(sys.argv[4]) if len(sys.argv) > 4 else 448
    os.makedirs(out, exist_ok=True)
    gidx = open(os.path.join(client, 'gx00.idx'), 'rb').read()
    gdat = open(os.path.join(client, 'gx00.dat'), 'rb')
    pidx = open(os.path.join(client, 'pnglib.idx'), 'rb').read()
    pdat = open(os.path.join(client, 'pnglib.dat'), 'rb')
    n_ok = 0
    for nr in range(first, first + count):
        name = os.path.join(out, '%05d.png' % nr)
        loose = os.path.join(client, 'gfx', '%05d.png' % nr)
        if os.path.exists(loose):
            Image.open(loose).convert('RGBA').save(name); n_ok += 1; continue
        if nr * 4 + 4 <= len(pidx):
            off = struct.unpack_from('<i', pidx, nr * 4)[0]
            if off:
                pdat.seek(off)
                Image.open(pdat).convert('RGBA').save(name); n_ok += 1; continue
        if nr < 40000:
            xs, ys, off = struct.unpack_from('<3i', gidx, nr * 12)
            if xs > 0:
                gdat.seek(off)
                px = struct.unpack('<%dH' % (xs * ys), gdat.read(xs * ys * 2))
                img = Image.new('RGBA', (xs, ys))
                img.putdata([(0, 0, 0, 0) if v == 0xF81F else
                             (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255) for v in px])
                img.save(name); n_ok += 1
    print('%d sprites written to %s' % (n_ok, out))

if __name__ == '__main__':
    main()
