#!/usr/bin/env python3
"""Greenling Eye Collectors already in the world (half-full ones have template 0, so they are found by their driver
17 and their result): make them turn into the Greenling Eye Collection (1408) instead of the essence (833).
Server stopped: fix_collectors.py <.dat folder> [write]"""
import sys, os, struct
ITEM_SIZE, I_USED, I_DRIVER, I_DATA = 634, 0, 593, 594
p = os.path.join(sys.argv[1], 'item.dat'); w = len(sys.argv) > 2 and sys.argv[2] == 'write'
n = 0
with open(p, 'r+b' if w else 'rb') as f:
    d = bytearray(f.read())
    for i in range(len(d) // ITEM_SIZE):
        o = i * ITEM_SIZE
        if d[o + I_USED] and d[o + I_DRIVER] == 17 and struct.unpack_from('<i', d, o + I_DATA + 36)[0] == 833:
            n += 1
            if w: f.seek(o + I_DATA + 36); f.write(struct.pack('<i', 1408))
print('%d Greenling Eye Collector(s) %s' % (n, 'changed' if w else 'found (add "write" to change them)'))
