#!/usr/bin/env python3
"""Elysium: turn the edited layout sheet into a build_lab spec.

    elysium_build.py <xlsx> <dump.tsv> <out.spec>

dump.tsv must be the dump the sheet was exported from (area_dump of the live map).
Only cells that differ from the hidden "Original" sheet are rebuilt; everything else keeps
its exact sprites, flags and items.

How changed cells get their look:
  rooms    the floor cells (anything walkable, tables included) split by walls, columns, gates
           and doors; each room is one area
  floor    a random plain floor sprite of the same room's unchanged floor (carpet pieces
           520-541 are never copied); its flags are the room's most common flags
           (indoors, no-expire, ...). A room with no unchanged floor gets plain stone,
           indoors, and is listed so its flags can be checked
  wall #   the wall sprite family nearest to it (unchanged walls within 3 tiles), else 100/102/104
  column c 106, gate g 976, table t corners 1242 / rest 1244 (blocks walking only)
  F T H D S  fire bowl, trash can, shrine, door (turned to its wall), shield (turned to its wall)
  M1-M10   god shop merchant moves there and faces away from the wall next to it
  n        the gallery NPCs, only as a whole block moved
  P / ?    a new portal or anything else: listed, built by hand
"""
import sys, random
from collections import Counter, deque
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import elysium as e
random.seed(106)
xlsx, tsv, out = sys.argv[1:4]
T = e.load(tsv)
old, new = e.read(xlsx, 'Original'), e.read(xlsx, 'Map')
STATIC = 0xffffffff & ~0x3          # map flags kept per room (not move/sight block)
CARPET = range(520, 542)
BLOCK = ('', '#', 'c', 'g', 'D')
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
spr_of = lambda k: int(T[k][2])
fs_of = lambda k: int(T[k][3])
fl_of = lambda k: int(T[k][4], 16)
notes = []

# --- rooms
room, rooms = {}, []
for k, v in new.items():
    if v in BLOCK or k in room:
        continue
    q, cells = deque([k]), []
    room[k] = len(rooms)
    while q:
        c = q.popleft(); cells.append(c)
        for dx, dy in N4:
            n = (c[0]+dx, c[1]+dy)
            if n in new and n not in room and new[n] not in BLOCK:
                room[n] = len(rooms); q.append(n)
    rooms.append(cells)
style = []
for i, cells in enumerate(rooms):
    plain = [k for k in cells if old[k] == new[k] and new[k] == '.' and fs_of(k) == 0 and spr_of(k) != 1008]
    sprites = [spr_of(k) for k in plain if spr_of(k) not in CARPET]
    flags = Counter(fl_of(k) & STATIC for k in plain)
    if not sprites:
        sprites = [142, 143, 144, 145]
    if flags:
        fl = flags.most_common(1)[0][0]
    else:
        fl = 0x4
        if any(old[k] != new[k] for k in cells):
            xs = [k[0] for k in cells]; ys = [k[1] for k in cells]
            notes.append('room x %d-%d y %d-%d is all new: plain stone, indoors - check its flags' % (min(xs), max(xs), min(ys), max(ys)))
    style.append((sprites, fl))


def floor_of(k):
    if k in room:
        sp, fl = style[room[k]]
        return random.choice(sp), fl
    best = None   # a wall or column: the flags of the room next to it
    for dx, dy in N4:
        n = (k[0]+dx, k[1]+dy)
        if n in room:
            best = style[room[n]]; break
    sp, fl = best or ([142, 143, 144, 145], 0x4)
    return random.choice(sp), fl


def wall(x, y):
    return new.get((x, y)) in ('#', 'c', 'g')


def wall_sprite(k):
    c = Counter()
    for d in range(1, 4):
        for dx in range(-d, d+1):
            for dy in range(-d, d+1):
                n = (k[0]+dx, k[1]+dy)
                if n in new and old[n] == new[n] == '#' and fs_of(n) not in (0, 106):
                    c[fs_of(n)] += 1
        if c:
            break
    if not c:
        return random.choice([102]*6 + [100]*2 + [104]*2)
    if set(c) <= {100, 102, 104}:   # the stone walls come as a mix
        return random.choice([102]*6 + [100]*2 + [104]*2)
    return c.most_common(1)[0][0]


# --- tiles
lines, tiles = [], 0
for k, v in sorted(new.items()):
    if old[k] == v:
        continue
    x, y = k
    if v == '':
        spr, fs, fl = 1008, 0, 0
    elif v in ('#', 'c', 'g'):
        spr, ffl = floor_of(k)
        fs = {'#': None, 'c': 106, 'g': 976}[v] or wall_sprite(k)
        fl = 3 | ffl
    elif v == 't':
        spr, ffl = floor_of(k)
        nb = sum(new.get((x+dx, y+dy)) == 't' for dx, dy in N4)
        fs, fl = (1242 if nb == 2 else 1244), 1 | ffl
    else:
        if old[k] not in BLOCK and old[k] != 't' and spr_of(k) != 1008 and fs_of(k) == 0:
            spr = spr_of(k)                    # was floor already: keep its sprite
            _, fl = floor_of(k)
        else:
            spr, fl = floor_of(k)
        fs = 0
    lines.append('tile %d %d %d %d %x' % (x, y, spr, fs, fl)); tiles += 1

# --- items
ITEM = {'F': 741, 'T': 1115, 'H': 603}
clears, places = [], []
shield_n = 0
for k, v in sorted(new.items()):
    if old[k] == v:
        continue
    x, y = k
    if T[k][5]:
        clears.append('clear %d %d %d %d' % (x, y, x, y))
    if v in ITEM:
        places.append('place %d %d %d' % (ITEM[v], x, y))
    elif v == 'D':
        places.append('place %d %d %d' % (738 if (wall(x, y-1) and wall(x, y+1)) else 737, x, y))
    elif v == 'S':
        t = (747, 749)[shield_n % 2] if (wall(x-1, y) or wall(x+1, y)) else (746, 748)[shield_n % 2]
        shield_n += 1
        places.append('place %d %d %d' % (t, x, y))
    elif v == 'P' or v.startswith('?') or v == 'i':
        notes.append('%d,%d: "%s" - build by hand' % (x, y, v))

# --- characters
chl, dirs = [], []
for k, v in sorted(new.items()):
    if v.upper().startswith('M') and v[1:].isdigit() and old[k] != v:
        x, y = k
        t = 1179 + int(v[1:])
        chl.append('ch %d pos %d %d' % (t, x, y))
        d = 1 if wall(x-1, y) else 2 if wall(x+1, y) else 3 if wall(x, y+1) else 4 if wall(x, y-1) else 0
        if d: dirs.append('dir %d %d' % (t, d))
on = sorted(k for k, v in old.items() if v == 'n')
nn = sorted(k for k, v in new.items() if v == 'n')
if on != nn:
    dx, dy = nn[0][0]-on[0][0], nn[0][1]-on[0][1]
    if sorted((x+dx, y+dy) for x, y in on) != nn:
        sys.exit('gallery NPCs: the new block is not the old one moved (%d old, %d new)' % (len(on), len(nn)))
    for (x, y) in on:
        chl.append('ch %d pos %d %d' % (int(T[x, y][9]), x+dx, y+dy))
moves = ['movenpc %s' % l.split()[1] for l in chl]

spec = ['# Elysium rebuild from elysium_layout.xlsx (elysium_build.py)'] + clears + lines + places + chl + moves + dirs
open(out, 'w').write('\n'.join(spec) + '\n')
print('%d tiles, %d clears, %d items, %d characters, %d rooms' % (tiles, len(clears), len(places), len(chl), len(rooms)))
for n in notes:
    print('NOTE', n)
