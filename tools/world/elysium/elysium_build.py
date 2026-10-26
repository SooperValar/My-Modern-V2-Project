#!/usr/bin/env python3
"""Elysium: turn the edited layout sheet into a build_lab spec.

    elysium_build.py <xlsx> <dump.tsv> <out.spec>

Only cells that differ from the hidden "Original" sheet are rebuilt (plus the vault floors,
which all get the no-expire flag). Styles per region:
  gallery  x778-791 y796-805   red gallery walls (126), gallery floor 950-958, indoors
  vaults   x808-820 y792-814   stone floor, indoors + no-expire (items never decay)
  east     x792-808 y812-824   the old north hall moved here: its floor 141-145, open sky
  elsewhere: copies the floor of the unchanged neighbours; walls 100/102/104, lone walls are columns (106)
"""
import sys, random
from collections import Counter
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import elysium as e
random.seed(106)
xlsx, tsv, out = sys.argv[1:4]
T = e.load(tsv)
old, new = e.read(xlsx, 'Original'), e.read(xlsx, 'Map')
INDOORS, NOEXPIRE = 0x4, 0x2000
FLOORISH = lambda v: v not in ('', '#')
inr = lambda r, x, y: r[0] <= x <= r[1] and r[2] <= y <= r[3]
GAL, VAULT, EAST = (778, 791, 796, 805), (808, 820, 792, 814), (792, 808, 812, 824)
FAM = {'gal': ([950, 951, 952, 953, 954, 955, 956, 957, 958], INDOORS),
       'vault': ([142, 143, 144, 145], INDOORS | NOEXPIRE),   # plain stone (520-530 are carpet pieces)
       'east': ([142, 143, 144, 145], 0),          # the old north hall's stone (141 is its brown border)
       'main': ([142, 143, 144, 145], INDOORS)}
WALLS = [102]*6 + [100]*2 + [104]*2
lines, notes = [], []


def region(x, y):
    if inr(GAL, x, y): return 'gal'
    if inr(VAULT, x, y): return 'vault'
    if inr(EAST, x, y): return 'east'
    return None


def floor_of(x, y):
    """sprite and flags for a floor tile at x,y"""
    r = region(x, y)
    if r:
        fam, fl = FAM[r]
        return random.choice(fam), fl
    c = Counter()
    for d in range(1, 4):
        for dx in range(-d, d+1):
            for dy in range(-d, d+1):
                k = (x+dx, y+dy)
                if k in T and k in new and old[k] == new[k] and FLOORISH(new[k]) and int(T[k][3]) == 0 and int(T[k][2]) != 1008:
                    c[(int(T[k][2]), int(T[k][4], 16) & (INDOORS | NOEXPIRE))] += 1
        if c: break
    if not c:
        fam, fl = FAM['main']; return random.choice(fam), fl
    spr = random.choice([s for (s, f), n in c.items() for _ in range(n)])
    return spr, c.most_common(1)[0][0][1]


def wall(x, y):
    return new.get((x, y)) == '#'


# --- tiles
tiles = 0
for (x, y), v in sorted(new.items()):
    o = old[x, y]
    cur = T[x, y]; cs, cf, cfl = int(cur[2]), int(cur[3]), int(cur[4], 16)
    vault_fix = region(x, y) == 'vault' and FLOORISH(v) and not (cfl & NOEXPIRE)
    if o == v and not vault_fix:
        continue
    if v == '':
        spr, fs, fl = 1008, 0, 0
    elif v == '#':
        spr, ffl = floor_of(x, y)
        if region(x, y) == 'gal':
            fs = 126
        elif not any(wall(x+dx, y+dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            fs = 106
        else:
            fs = random.choice(WALLS)
        fl = 3 | (ffl & INDOORS)
    else:
        if o == v or (FLOORISH(o) and cs != 1008 and cf == 0 and region(x, y) is None):
            spr, fl = cs, cfl          # was floor already: keep its look
            if region(x, y) == 'vault': fl |= INDOORS | NOEXPIRE
        else:
            spr, fl = floor_of(x, y)
        fs = 0
        fl = (cfl & ~(0x1 | 0x2 | INDOORS | NOEXPIRE)) | fl if cs != 1008 else fl
    lines.append('tile %d %d %d %d %x' % (x, y, spr, fs, fl)); tiles += 1

# --- items
ITEM = {'F': 741, 'T': 1115, 'H': 603}
had_item = lambda f: bool(f[5])
clears, places = [], []
shield_n = 0
for (x, y), v in sorted(new.items()):
    o = old[x, y]
    if o == v:
        continue
    if had_item(T[x, y]):
        clears.append('clear %d %d %d %d' % (x, y, x, y))
    if v in ITEM:
        places.append('place %d %d %d' % (ITEM[v], x, y))
    elif v == 'D':
        t = 738 if (wall(x, y-1) and wall(x, y+1)) else 737
        places.append('place %d %d %d' % (t, x, y))
    elif v == 'S':
        if wall(x-1, y) or wall(x+1, y): t = (747, 749)[shield_n % 2]
        else: t = (746, 748)[shield_n % 2]
        shield_n += 1
        places.append('place %d %d %d' % (t, x, y))
    elif v == 'P':
        places.append('place %d %d %d' % (1376 if y < 804 else 1377, x, y))

# --- characters: merchants by code, gallery NPCs by the move of the whole gallery
chl = []
for (x, y), v in sorted(new.items()):
    if v.upper().startswith('M') and v[1:].isdigit() and old[x, y] != v:
        t = 1179 + int(v[1:])
        chl += ['ch %d pos %d %d' % (t, x, y)]
on = sorted(k for k, v in old.items() if v == 'n')
nn = sorted(k for k, v in new.items() if v == 'n')
dx, dy = nn[0][0]-on[0][0], nn[0][1]-on[0][1]
if sorted((x+dx, y+dy) for x, y in on) != nn:
    sys.exit('gallery NPCs: the new block is not the old one moved (%d old, %d new)' % (len(on), len(nn)))
for (x, y) in on:
    t = int(T[x, y][9])
    chl.append('ch %d pos %d %d' % (t, x+dx, y+dy))
moves = ['movenpc %s' % l.split()[1] for l in chl]

spec = ['# Elysium rebuild from elysium_layout.xlsx (elysium_build.py)',
        'it 1376 copy 179', 'it 1376 name Portal to Staffers Corner', 'it 1376 ref portal to Staffers Corner',
        'it 1376 desc A magic portal. It leads to the Staffers Corner.', 'it 1376 d 0 838', 'it 1376 d 1 160',
        'it 1377 copy 179', 'it 1377 name Portal to the Temple of Skua', 'it 1377 ref portal to the Temple of Skua',
        'it 1377 desc A magic portal. It leads to the Temple of Skua.', 'it 1377 d 0 512', 'it 1377 d 1 512',
        ] + clears + lines + places + chl + moves
open(out, 'w').write('\n'.join(spec) + '\n')
print('%d tiles, %d clears, %d items, %d characters (gallery moved by %d,%d)' % (tiles, len(clears), len(places), len(chl), dx, dy))
xs = [k[0] for k, v in new.items() if v]; ys = [k[1] for k, v in new.items() if v]
print('built area x %d-%d y %d-%d' % (min(xs), max(xs), min(ys), max(ys)))
