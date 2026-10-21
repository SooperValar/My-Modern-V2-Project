"""The original procedural Lab 11 layout (single-character codes), used once to make lab11_layout.xlsx."""
import json, random, sys, os
from collections import deque
from PIL import Image, ImageDraw

OX, OY = 180, 900            # map position of the layout's 0,0
TICKS = 18
random.seed(11)
W, H = 120, 100
g = [['#']*W for _ in range(H)]
def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1+1):
        for x in range(x0, x1+1): g[y][x] = c
def put(x, y, c): g[y][x] = c
def islands(x0, y0, x1, y1, step=7, size=3, braz=True, mons=True):
    k = 0
    for y in range(y0+2, y1-1, step):
        for x in range(x0+2, x1-1, step):
            rect(x, y, min(x+size-1, x1-1), min(y+size-1, y1-1), '.')
            k += 1
            if braz and k % 2 == 0: put(x+1, y+1, 'B')
            elif mons and k % 3 == 0: put(x+1, y+1, 'm')

# ---- entry hall with the inn: dry, lit, no monsters (layout after Cody's sketch)
#   north: the bar (counter, barkeeper behind it) | tavern strip | armor shop
#   west wall: the portal you arrive by and leave by; south-west: offering shrine
#   south-east: weapon shop; east wall open in the middle to the Atrium
rect(2, 37, 21, 61, 'e')
for y in range(37, 42): put(9, y, '#'); put(12, y, '#')     # walls beside the tavern strip
rect(10, 37, 11, 41, 'T')                                   # tavern floor (log out here)
for x in list(range(2, 7)) + list(range(13, 17)) + list(range(19, 22)): put(x, 42, '#')
for x in range(3, 8): put(x, 39, 'c')                       # bar counter
put(5, 38, 'K')
put(17, 39, 'R'); put(14, 38, 'C'); put(21, 38, 'C')        # armor shop
for x in list(range(14, 17)) + list(range(19, 22)): put(x, 56, '#')
for y in range(56, 62): put(13, y, '#')                     # weapon shop walls
put(18, 60, 'W'); put(14, 60, 'C'); put(21, 60, 'C')
put(5, 60, 'H'); put(3, 60, 'C'); put(7, 60, 'C')           # offering shrine
put(2, 49, 'X'); put(4, 49, 'A')                            # entry/exit portal, arrival
for y in range(48, 53): put(22, y, 'e')                     # open east wall into the Atrium
# ---- section 1: flooded atrium with alcoves
rect(23, 30, 57, 69, '~'); islands(23, 30, 57, 69)
rect(23, 48, 26, 52, '.'); put(24, 49, 'C')     # landing by the entry
for i, (ax, ay) in enumerate(((28, 24), (38, 24), (48, 24))):
    rect(ax, ay, ax+5, ay+5, '~')
    put(ax+2, ay+2, 'S' if i == 1 else 's')     # book 1 in the middle north alcove
put(32, 25, '1')                                # exploration point 1 in the west alcove
rect(53, 47, 57, 53, '.'); put(55, 50, 'L'); put(54, 48, 'C'); put(58, 50, 'D')

# ---- section 2: flooded library, shelf rows
rect(59, 30, 93, 69, '~')
for y in range(34, 67, 6):
    for x in range(62, 91):
        if (x-62) % 10 not in (4, 5): put(x, y, '|')
islands(59, 30, 93, 69, step=6, size=2, braz=True, mons=True)
for y in range(34, 67, 6):
    for x in range(62, 91):
        if (x-62) % 10 not in (4, 5) and g[y][x] == '.': put(x, y, '|')
shelves = [(66, 40), (76, 46), (86, 52), (66, 58), (86, 40), (76, 64)]
for i, (x, y) in enumerate(shelves): put(x, y, 'S' if i == 4 else 's')
put(92, 32, '2')                                # exploration point 2, far corner
put(75, 67, 'k')                                # shrine of Kwai
rect(89, 47, 93, 53, '.'); put(91, 50, 'L'); put(90, 48, 'C'); put(94, 50, 'D')

# ---- section 3: sunken crypt, narrow winding tunnels north and south
rect(95, 48, 99, 52, '.')
def tunnel(path):
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        for x in range(min(x0, x1), max(x0, x1)+1):
            for y in range(min(y0, y1), max(y0, y1)+1):
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if g[y+dy][x+dx] == '#': g[y+dy][x+dx] = '~'
north = [(100, 50), (110, 50), (110, 40), (100, 40), (100, 30), (114, 30), (114, 18), (100, 18), (100, 8)]
south = [(97, 52), (97, 62), (112, 62), (112, 74), (100, 74), (100, 86), (106, 86), (106, 93), (96, 93)]
tunnel(north); tunnel(south)
pockets = [(110, 45), (105, 40), (100, 35), (107, 30), (114, 24), (107, 18), (100, 13), (97, 57), (105, 62), (112, 68), (106, 74), (100, 80), (103, 86)]
for x, y in pockets: rect(x-1, y-1, x, y, '.')
rect(98, 5, 103, 9, '.'); put(100, 6, 'S'); put(102, 6, 'B')   # book 3 at the far north end
put(97, 49, 'L'); put(96, 48, 'C')                              # lectern 3 by the crypt entrance
for x, y in ((110, 40), (100, 30), (114, 18), (97, 62), (112, 74)): put(x, y, 'm')
put(94, 93, 'D'); put(93, 93, '.'); put(92, 93, '.')

# ---- section 4: dark cistern along the bottom, few braziers
rect(23, 72, 91, 97, '~'); rect(86, 90, 91, 96, '.'); put(88, 91, 'C')
for y in range(75, 96, 5):
    for x in range(27, 88, 9): rect(x, y, x, y, '#')            # pillars
k = 0
for y in range(74, 96, 7):
    for x in range(30, 84, 8):
        rect(x, y, x+2, y+2, '.'); k += 1
        if k % 5 == 0: put(x+1, y+1, 'B')
        elif k % 3 == 0: put(x+1, y+1, 'm')
rect(23, 82, 27, 88, '.'); put(25, 85, 'S'); put(24, 83, 'C')  # book 4 at the far west end
put(25, 87, 'L'); put(22, 85, 'D')
put(25, 96, '3')                                # exploration point 3, far south-west

# ---- vault with the end portal
rect(2, 72, 21, 97, '.'); put(10, 85, 'P')
for p in ((3, 73), (20, 73), (3, 96), (20, 96)): put(*p, 'C')

# ---------------------------------------------------------------------------
SECTIONS = [  # name, lectern, gate, water rectangle, book shelf
    ('Atrium',  (55, 50), (58, 50), (23, 24, 57, 69), (40, 26)),
    ('Library', (91, 50), (94, 50), (59, 30, 93, 69), (86, 40)),
    ('Crypt',   (97, 49), (94, 93), (95, 1, 118, 98), (100, 6)),
    ('Cistern', (25, 87), (22, 85), (23, 70, 91, 98), (25, 85)),
]
