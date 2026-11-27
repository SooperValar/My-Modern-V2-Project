#!/usr/bin/env python3
"""Amulet of Ankh (template 768) as a Legendary (Cody, Nov 27): fixed bonuses, item level 10, the effect
Ankh's Grace (hit points, endurance and mana regenerate while moving / fighting at half the standing rate).

Run on a STOPPED copy of the .dat folder (stop-send, run on Server/.dat, get, update-world):
    python3 ankh_amulet.py <.dat folder> [--dry]
Changes the template in titem.dat and every Amulet of Ankh item in item.dat. The Black Stronghold's
"Amulet of Ankh on Table" (427,339) gives copies of the template.
Item layout: server/data.h struct item (offsets as in tools/mapedit IT_FIELDS)."""
import struct, sys, os

TEMP = 768
SZ = 634
SK_LIGHT, SK_RESIST, SK_IMMUN = 14, 23, 32
TIER_LEGEND, LEVEL = 4, 10
TE_ANKHGRACE = 10                 # server data.h
IF_IDENTIFIED = 1 << 37

STATS = {
    'attrib': {a: 3 for a in range(5)},    # all five +3, when worn; no attribute needed
    'skill': {SK_RESIST: 12, SK_IMMUN: 8, SK_LIGHT: 10},
    'hp': 30, 'end': 30, 'mana': 30,
    'min_rank': LEVEL,
}

def patch(buf, o):
    for a in range(5):            # [0] worn, [1] active, [2] needed
        v = STATS['attrib'].get(a, 0)
        struct.pack_into('3b', buf, o + 322 + a * 3, v, v, 0)
    for s in range(50):
        v = STATS['skill'].get(s, 0)
        struct.pack_into('3b', buf, o + 355 + s * 3, v, v, 0)
    struct.pack_into('<3h', buf, o + 337, STATS['hp'], STATS['hp'], 0)
    struct.pack_into('<3h', buf, o + 343, STATS['end'], STATS['end'], 0)
    struct.pack_into('<3h', buf, o + 349, STATS['mana'], STATS['mana'], 0)
    struct.pack_into('<2I', buf, o + 298, 0, 0)          # max_age: no wear
    struct.pack_into('<I', buf, o + 314, 0)              # max_damage: never breaks
    struct.pack_into('b', buf, o + 545, STATS['min_rank'])
    buf[o + 546] = buf[o + 547] = buf[o + 548] = 0       # no speed bonuses
    f3 = list(struct.unpack_from('<9i', buf, o + 549))
    f3[0:7] = [TIER_LEGEND, 0, LEVEL, TE_ANKHGRACE, 0, 0, 0]   # tier, category, level, effect, prefix, suffix, base
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
