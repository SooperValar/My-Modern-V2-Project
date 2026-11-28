#!/usr/bin/env python3
"""The two belts that were both just "Belt" get their own names (Cody, Nov 27): template 113 (the gold one, a quest
item from the Haunted Castle) is "Gold Belt", template 1106 (the green one, a chest reward) is "Green Belt".

Run on a STOPPED copy of the .dat folder (stop-send, run on Server/.dat, update-world):
    python3 name_belts.py <.dat folder> [--dry]
Changes the templates in titem.dat and every item made from them in item.dat (name and reference).
Item layout: server/data.h struct item (offsets as in tools/mapedit IT_FIELDS)."""
import struct, sys, os

SZ = 634
NAMES = {113: 'Gold Belt', 1106: 'Green Belt'}

def patch(buf, o, name):
    struct.pack_into('40s', buf, o + 1, name.encode('latin1'))
    struct.pack_into('40s', buf, o + 41, name.lower().encode('latin1'))

def main():
    d, dry = sys.argv[1], '--dry' in sys.argv
    for fn, temp_of in (('titem.dat', lambda b, o, i: i), ('item.dat', lambda b, o, i: struct.unpack_from('<H', b, o + 295)[0] if b[o] else 0)):
        path = os.path.join(d, fn)
        buf = bytearray(open(path, 'rb').read())
        n = 0
        for i in range(len(buf) // SZ):
            o = i * SZ
            t = temp_of(buf, o, i)
            if t in NAMES and buf[o + 1:o + 41].split(b'\0')[0] == b'Belt':
                patch(buf, o, NAMES[t]); n += 1
        print('%s: %d changed' % (fn, n))
        if not dry and n:
            open(path + '.tmp', 'wb').write(buf)
            os.replace(path + '.tmp', path)

main()
