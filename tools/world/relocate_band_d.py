#!/usr/bin/env python3
"""Move the Monastery of the Still Hand 42 tiles north and the Gargoyle Spires 18 tiles north (Nov 19; Cody: "there
should be no walls within 25 tiles of a place a player can reach" in the Spires - the west wall, Bastion Road, is fine -
and "can the monastery move north to accommodate the extra space?", "can you not move the poles as well?").
Everything moves as it is, with the map editor's own copy / paste (floors, walls, objects, tile flags, items - each
exploration pole stays the SAME pole, so who found it keeps it found) and its NPC move (each NPC with its home spot and
its respawn): no new templates, quests and rewards unchanged. Afterwards, in this order (game stopped):

    relocate_band_d.py <.dat folder>
    gargoyle_spires/build_spires.py <.dat folder> --edges --shift -18     (Bastion Road's gate, and the drop all round)
    then relight

  Monastery: 650-740 x 855-950 -> 608-698; Stonehold's east gate road runs on to the new foot of Pilgrims' Stair.
  Spires: the islands (742-830 x 843-940) -> 724-812; the drop round them is made again by build_spires --edges.
  Zones moved with them. build_monastery.py / place_*.py still describe the old places (re-running them would build
  there): this script is the record of the move."""
import sys, os, json, struct, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1], seed=1210); W = A.W
MON, MON_DX = (650, 855, 740, 950), -42
SPI, SPI_DX = (742, 843, 830, 940), -18
SPI_NPC_BOX = (741, 843, 834, 965)

def npcs_in(b):
    out = []
    for x in range(b[0], b[2] + 1):
        for y in range(b[1], b[3] + 1):
            c = W.tile(x, y)[2]
            pl = c and W.is_player(c)
            if (c and not pl) or W._pending_at(x, y): out.append((x, y))
    return out

def move(box, dx, npc_box, label):
    who = sorted(npcs_in(npc_box))                         # west (smaller x) first: each moves onto a spot already left
    r = W.copy_area(*box); print('  %s: copied %dx%d, %d items, %d npcs, %d poles' % (label, r['w'], r['h'], r['items'], r['npcs'], r['poles']))
    n, msgs = W.apply([{'op': 'paste', 'x': box[0] + dx, 'y': box[1], 'poles': 'same'}], label + ' paste')
    for m in msgs: print('  !', m)
    bad = 0
    for x, y in who:
        n, msgs = W.apply([{'op': 'npcmove', 'x': x, 'y': y, 'tx': x + dx, 'ty': y}], label + ' npc')
        for m in msgs: print('  ! npc %d,%d:' % (x, y), m); bad += 1
    print('  %s: %d NPCs moved (%d failed)' % (label, len(who) - bad, bad))

move(MON, MON_DX, MON, 'monastery')
# what is left of the old Monastery east of its new place (699-740) is made over by build_spires --edges (the drop)
move(SPI, SPI_DX, SPI_NPC_BOX, 'spires')

# Stonehold's east gate road (x 680-682, to 855): on along the gap below the town to the stair's new foot (639,855)
STAIR = (681 + MON_DX, 855)
road = set()
def line(a, b):
    n = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
    for i in range(n + 1):
        x, y = round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if abs(dx) + abs(dy) <= 1: road.add((x + dx, y + dy))
line((681, 845), (681, 850)); line((681, 850), (STAIR[0], 850)); line((STAIR[0], 850), STAIR)
CLIFF = [1204, 1206]; SNOW = [35400, 35401, 35402, 35403]
for x, y in sorted(road):
    if y >= 855 and (x, y) != STAIR: continue
    A.op(op='erase', x=x, y=y); A.op(op='floor', x=x, y=y, s=random.choice(SETTS), set=False)
    for b in (0, 5): A.op(op='flag', x=x, y=y, bit=b, mode=0 if b == 0 else 1)          # walkable; no monsters on the road
for x in range(STAIR[0] - 3, 684):
    for y in range(846, 855):
        if (x, y) in road: continue
        if any((x + dx, y + dy) in road for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)) and (A.floor(x, y) == VOID or (680 <= x <= 682)):
            A.op(op='erase', x=x, y=y); A.op(op='floor', x=x, y=y, s=random.choice(SNOW), set=False); A.op(op='object', x=x, y=y, s=random.choice(CLIFF), block=3)
A.run('the road on to the stair')

A.save()
# zones: the Monastery's and the Spires' boxes move with them (after the save: zones.dat is written here directly)
qs_path = os.path.join(sys.argv[1], 'zones.dat'); lines = open(qs_path).read().split('\n'); out = []; moved = 0
MON_Z = {'Monastery of the Still Hand', "Pilgrims' Stair", 'Cloister', 'Training Yard', 'Hall of the Silent Hand', 'Burial Terrace',
         'Still Pond', "Abbot's Sanctum", 'Library'}
SPI_Z = {'Gargoyle Spires', 'Broken Causeway', 'Bell Spire', "Shrike's Eyrie"}
for l in lines:
    p = l.split(None, 5)
    if len(p) == 6 and not l.startswith('#') and (p[5].strip() in MON_Z or p[5].strip() in SPI_Z):
        dx = MON_DX if p[5].strip() in MON_Z else SPI_DX
        x0, y0, x1, y1 = map(int, p[:4]); l = '%d %d %d %d %s %s' % (x0 + dx, y0, x1 + dx, y1, p[4], p[5]); moved += 1
    out.append(l)
open(qs_path, 'w').write('\n'.join(out)); print('  zone boxes moved:', moved)
