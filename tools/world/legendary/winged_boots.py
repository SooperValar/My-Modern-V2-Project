#!/usr/bin/env python3
"""Winged Boots (template 907) as the first Legendary (Cody, Nov 27): fixed bonuses, item level 13.

Run on a STOPPED copy of the .dat folder (stop-send, run on Server/.dat, update-world):
    python3 winged_boots.py <.dat folder> [--dry]
Changes the template in titem.dat and every Winged Boots item in item.dat (same values; the
Seyan'Du Lord's pair and the Gargoyle's Nest chest's are copies of the template).
Item layout: server/data.h struct item (offsets as in tools/mapedit IT_FIELDS)."""
import struct, sys, os

TEMP = 907
SZ = 634
AT_BRAVE, AT_WILL, AT_INT, AT_AGIL, AT_STREN = range(5)
SK_STEALTH, SK_PERCEPT = 8, 9
TIER_LEGEND, LEVEL = 4, 13
IF_IDENTIFIED = 1 << 37
SPD_MOVE = 1                      # nibble 1 = high nibble of speedb[0]

STATS = {
    'armor': 6,
    'attrib': {AT_AGIL: 14},      # when worn; no attribute needed
    'skill': {SK_STEALTH: 10, SK_PERCEPT: 8},
    'hp': 35, 'end': 65,
    'move_speed': 3,
    'min_rank': LEVEL,
}

def patch(buf, o):
    struct.pack_into('2b', buf, o + 505, STATS['armor'], STATS['armor'])
    for a in range(5):            # [0] worn, [1] active, [2] needed
        struct.pack_into('3b', buf, o + 322 + a * 3, STATS['attrib'].get(a, 0), STATS['attrib'].get(a, 0), 0)
    for s in range(50):
        v = STATS['skill'].get(s, 0)
        struct.pack_into('3b', buf, o + 355 + s * 3, v, v, 0)
    struct.pack_into('<3h', buf, o + 337, STATS['hp'], STATS['hp'], 0)
    struct.pack_into('<3h', buf, o + 343, STATS['end'], STATS['end'], 0)
    struct.pack_into('<3h', buf, o + 349, 0, 0, 0)
    struct.pack_into('<2I', buf, o + 298, 0, 0)          # max_age: no wear
    struct.pack_into('<I', buf, o + 314, 0)              # max_damage: never breaks
    struct.pack_into('b', buf, o + 545, STATS['min_rank'])
    sp = STATS['move_speed'] & 15
    buf[o + 546] = (sp << 4) if SPD_MOVE & 1 else sp     # speedb[0]; [1], [2] stay 0
    buf[o + 547] = 0; buf[o + 548] = 0
    f3 = list(struct.unpack_from('<9i', buf, o + 549))
    f3[0:7] = [TIER_LEGEND, 0, LEVEL, 0, 0, 0, 0]       # tier, category, level, effect, prefix, suffix, base
    struct.pack_into('<9i', buf, o + 549, *f3)
    flags = struct.unpack_from('<Q', buf, o + 281)[0] | IF_IDENTIFIED
    struct.pack_into('<Q', buf, o + 281, flags)

def main():
    d, dry = sys.argv[1], '--dry' in sys.argv
    for fn, match in (('titem.dat', lambda b, o, i: i == TEMP), ('item.dat', lambda b, o, i: b[o] and struct.unpack_from('<H', b, o + 295)[0] == TEMP)):
        path = os.path.join(d, fn)
        buf = bytearray(open(path, 'rb').read())
        n = 0
        for i in range(len(buf) // SZ):
            o = i * SZ
            if match(buf, o, i):
                patch(buf, o); n += 1
        print('%s: %d changed' % (fn, n))
        if not dry and n:
            open(path + '.tmp', 'wb').write(buf)
            os.replace(path + '.tmp', path)

main()
