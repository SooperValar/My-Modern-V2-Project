#!/usr/bin/env python3
"""Lab 11, the Sunken Dark: layout, preview and build spec.
    lab11.py <out folder>     writes layout.json, preview.png and lab11.spec
Apply with:  build_lab <.dat folder> lab11.spec ; then "server pop" and "server light".

Layout codes: '#' wall, '.' dry floor, '~' water (drains), 'D' gate, 'B' brazier (light it),
'C' lit bowl, 'L' lectern, 'S' shelf with the book, 's' empty shelf, '|' bookshelf (wall),
'P' end portal, 'X' exit portal, 'H' offering shrine, 'A' arrival, 'm' monster,
'1'-'3' exploration points, 'k' shrine of Kwai, 'T' tavern backroom, 'c' counter,
'K' barkeeper, 'W' weapon merchant, 'R' armor merchant, 'e' entry hall floor."""
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

# ---- entry hall with the inn: dry, lit, no monsters
rect(2, 40, 21, 59, 'e'); put(10, 50, 'A')
rect(2, 40, 7, 44, 'T')                         # tavern backroom (log out here)
for x in range(2, 9): put(x, 45, '#')
for y in range(40, 45): put(8, y, '#')
put(5, 45, 'e')                                 # its doorway
for x in range(11, 16): put(x, 43, 'c')         # bar counter
put(13, 41, 'K')
put(6, 57, 'W'); put(15, 57, 'R')
put(20, 52, 'X'); put(20, 47, 'H')
for p in ((10, 41), (20, 41), (3, 58), (20, 58), (3, 47)): put(*p, 'C')
put(22, 50, 'e')                                # open way into the atrium

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
os.makedirs(sys.argv[1], exist_ok=True)
json.dump([''.join(r) for r in g], open(os.path.join(sys.argv[1], 'layout.json'), 'w'))

# ---- checks: every water tile belongs to exactly one section; reachability
for y in range(H):
    for x in range(W):
        if g[y][x] in '~1235k' or (g[y][x] in 'sS|' and g[y][x] != '.'):
            pass
inrect = lambda x, y, r: r[0] <= x <= r[2] and r[1] <= y <= r[3]
bad = 0
for y in range(H):
    for x in range(W):
        if g[y][x] == '~':
            n = sum(inrect(x, y, s[3]) for s in SECTIONS)
            if n != 1: bad += 1
print('water tiles outside / in two sections:', bad)
WALK = set('.~eATDC123k') - set('C')   # tiles a player can stand on
def walkable(c): return c in '.~eAD123kT'
def swim(start, goal_set, gates_open):
    """fewest consecutive water steps on the best path (0/1 BFS on water runs)"""
    best = {}
    dq = deque([(start, 0, 0)])
    worst = None
    while dq:
        (x, y), run, mx = dq.popleft()
        key = (x, y)
        if key in best and best[key] <= mx: continue
        best[key] = mx
        if key in goal_set: worst = mx if worst is None else min(worst, mx)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x+dx, y+dy
            c = g[ny][nx]
            if c == 'D' and (nx, ny) not in gates_open: continue
            if not walkable(c) and (nx, ny) not in goal_set: continue
            r = run+1 if c == '~' else 0
            dq.append(((nx, ny), r, max(mx, r)))
    return worst
def adj(p): return {(p[0]+dx, p[1]+dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))}
gates = set()
start = (10, 50)
for name, lec, gate, r, book in SECTIONS:
    a = swim(start, adj(book), gates); b = swim(start, adj(lec), gates)
    print('%-8s book: longest swim %s, lectern: %s' % (name, a, b))
    gates.add(gate)
print('end portal reachable:', swim(start, adj((10, 85)), gates) is not None)
for c in '123k':
    p = [(x, y) for y in range(H) for x in range(W) if g[y][x] == c][0]
    print('%s at %d,%d: swim %s (with all gates open)' % (c, OX+p[0], OY+p[1], swim(start, adj(p) | {p}, gates)))

# ---- preview
col = {'#': (30, 30, 34), '.': (120, 116, 108), '~': (40, 90, 140), 'D': (200, 120, 40), 'B': (255, 170, 40), 'C': (255, 220, 120),
       'L': (230, 60, 230), 'S': (60, 230, 90), 's': (40, 110, 60), 'P': (120, 220, 255), 'X': (255, 255, 255), 'H': (255, 230, 120),
       'A': (255, 60, 60), 'm': (200, 30, 30), '|': (90, 60, 40), 'e': (110, 60, 50), 'T': (160, 90, 60), 'c': (70, 40, 30),
       'K': (255, 255, 0), 'W': (255, 255, 0), 'R': (255, 255, 0), '1': (0, 255, 255), '2': (0, 255, 255), '3': (0, 255, 255), 'k': (255, 255, 255)}
S = 8; im = Image.new('RGB', (W*S, H*S)); d = ImageDraw.Draw(im)
for y in range(H):
    for x in range(W):
        d.rectangle((x*S, y*S, x*S+S-1, y*S+S-1), fill=col[g[y][x]])
for t, (x, y) in (('ENTRY / INN', (3, 37)), ('1 ATRIUM', (32, 32)), ('2 LIBRARY', (66, 31)), ('3 CRYPT', (104, 2)), ('4 CISTERN', (50, 77)), ('VAULT', (7, 79))):
    d.text((x*S, y*S), t, fill=(255, 255, 255))
im.save(os.path.join(sys.argv[1], 'preview.png'))

# ---- build spec ------------------------------------------------------------
T_SHRINE, T_POLE, T_BOOK, T_SHELFB, T_SHELFE, T_LECT, T_GATE, T_BRAZ, T_PORTAL = 1330, 1331, 1334, 1338, 1342, 1343, 1347, 1348, 1349
C_KEEPER, C_BAR, C_WEAP, C_ARM, C_MON = 1200, 1201, 1202, 1203, 1210
out = []
o = out.append
o('# Lab 11, the Sunken Dark - generated by tools/world/lab11/lab11.py (map %d,%d - %d,%d)' % (OX, OY, OX+W-1, OY+H-1))
o('# Lab 10 fix: its shrine of Kwai was placed with template number 0')
o('settemp 80 831 1298')
o('# ---- item templates')
o('it %d copy 673' % T_SHRINE); o('it %d name Shrine in Sunken Dark' % T_SHRINE); o('it %d d 0 2097152' % T_SHRINE)
for i, bit in enumerate((262144, 524288, 1048576)):
    t = T_POLE+i
    o('it %d copy 1316' % t); o('it %d name Explotation Point 0/0/%d' % (t, bit)); o('it %d d 2 %d' % (t, bit)); o('it %d d 4 50000' % t)
vols = ('I', 'II', 'III', 'IV'); bookspr = (1061, 1067, 1073, 1078)
for i in range(4):
    t = T_BOOK+i
    o('it %d copy %d' % (t, bookspr[i])); o('it %d name Drowned Tome, Volume %s' % (t, vols[i])); o('it %d ref a drowned tome' % t)
    o('it %d desc A swollen, dripping book. Its pages still glow faintly. It belongs on a lectern.' % t)
    s = T_SHELFB+i
    o('it %d copy 1060' % s); o('it %d name Bookshelf' % s); o('it %d desc A waterlogged bookshelf. One book still looks whole.' % s)
    o('it %d d 0 %d' % (s, t)); o('it %d dur %d' % (s, TICKS*60))
o('it %d copy 1060' % T_SHELFE); o('it %d name Bookshelf' % T_SHELFE); o('it %d desc A waterlogged bookshelf. One book still looks whole.' % T_SHELFE)
o('it %d spr 16910 16910' % T_SHELFE); o('it %d flags 613' % T_SHELFE); o('it %d d 0 2' % T_SHELFE); o('it %d dur 0' % T_SHELFE)
for i, (name, lec, gate, r, book) in enumerate(SECTIONS):
    t = T_LECT+i
    o('it %d copy 1052' % t); o('it %d name Lectern' % t); o('it %d ref the lectern' % t)
    o('it %d desc A lectern of swollen wood, its top shaped for a large book.' % t)
    o('it %d spr 16895 16918' % t); o('it %d flags 1000000611' % t); o('it %d light 0 0' % t); o('it %d dur 0' % t)
    vals = [1, T_BOOK+i, (OX+gate[0])+(OY+gate[1])*1024, OX+r[0], OY+r[1], OX+r[2], OY+r[3], TICKS*600, 0, 0]
    for j, v in enumerate(vals): o('it %d d %d %d' % (t, j, v))
o('it %d copy 732' % T_GATE); o('it %d name Sunken Gate' % T_GATE); o('it %d ref the gate' % T_GATE)
o('it %d desc Rusted bars. There is no lock - the water behind it holds it shut.' % T_GATE)
o('it %d flags 611' % T_GATE); o('it %d dur 0' % T_GATE)
for j, v in enumerate((3, 0, 0, 0, 0, 0, 0, 0, 0, 0)): o('it %d d %d %d' % (T_GATE, j, v))
o('it %d copy 741' % T_BRAZ); o('it %d name Brazier' % T_BRAZ); o('it %d ref the brazier' % T_BRAZ)
o('it %d desc A cold brazier, still holding a little dry coal.' % T_BRAZ)
o('it %d spr 18129 16510' % T_BRAZ); o('it %d status 0 16' % T_BRAZ); o('it %d flags 400211' % T_BRAZ); o('it %d light 0 175' % T_BRAZ); o('it %d dur %d' % (T_BRAZ, TICKS*300))
o('it %d copy 1299' % T_PORTAL); o('it %d name Magic Portal (Lab 11 End)' % T_PORTAL)
for j, v in enumerate((33, 597, 11, 210000)): o('it %d d %d %d' % (T_PORTAL, j, v))

# ---- character templates
def chbase(t, frm, name, x, y, scale=None, monster=True):
    o('ch %d copy %d' % (t, frm)); o('ch %d name %s' % (t, name))
    for i in list(range(10, 24))+[31, 32, 33, 34, 35, 60, 73]: o('ch %d d %d 0' % (t, i))
    if x: o('ch %d pos %d %d' % (t, x, y))
    if scale: o('ch %d scale %d' % (t, scale))
    if monster:
        for i, v in ((42, 1101), (43, 1101), (44, 1), (45, 0), (46, 0), (59, 1101)): o('ch %d d %d %d' % (t, i, v))
        o('ch %d setflags 10000' % t)      # sees in the dark
chbase(C_KEEPER, 423, 'Drowned Lord', 0, 0, 115)
o('ch %d ref the Drowned Lord' % C_KEEPER); o('ch %d clrflags 10' % C_KEEPER); o('ch %d pos 0 0' % C_KEEPER)
pos = {c: [(x, y) for y in range(H) for x in range(W) if g[y][x] == c] for c in 'KWR'}
x, y = pos['K'][0]; chbase(C_BAR, 1083, 'Barkeeper', OX+x, OY+y, monster=False)
x, y = pos['W'][0]; chbase(C_WEAP, 1091, 'Merchant', OX+x, OY+y, monster=False)
o('ch %d items 28 32 36 29 33 37 30 34 38 523 524 125' % C_WEAP)
x, y = pos['R'][0]; chbase(C_ARM, 1092, 'Merchant', OX+x, OY+y, monster=False)
o('ch %d items 63 64 65 66 67 68 69 70 71 72 73 74 981 982 983 984 985 986 75 76 77 78 79 80' % C_ARM)
kinds = {  # section -> list of (base template, name, scale)
    'Atrium':  [(423, 'Drowned Sailor', 112)],
    'Library': [(997, 'Gargoyle Archivist', 103)],
    'Crypt':   [(423, 'Crypt Lord', 115), (1154, 'Drowned Knight', 106)],
    'Cistern': [(1158, 'Sea Golem', 106), (1150, 'Marsh Shaman', 109)],
}
mons = [(x, y) for y in range(H) for x in range(W) if g[y][x] == 'm']
t = C_MON; count = {}
for i, (x, y) in enumerate(mons):
    sec = [s[0] for s in SECTIONS if inrect(x, y, s[3])][0]
    k = kinds[sec][count.get(sec, 0) % len(kinds[sec])]; count[sec] = count.get(sec, 0)+1
    chbase(t, k[0], k[1], OX+x, OY+y, k[2]); t += 1
print('monsters:', count, 'templates %d-%d' % (C_MON, t-1))

# ---- tiles and items
SEAWEED = (340, 342, 348, 350, 352, 354)
FL_IN, FL_UW, FL_NOM, FL_TAV, FL_MB, FL_SB = 0x4, 0x8, 0x20, 0x80, 0x1, 0x2
items = []
for y in range(H):
    for x in range(W):
        c = g[y][x]; X, Y = OX+x, OY+y
        if c == '#':
            edge = any(0 <= x+dx < W and 0 <= y+dy < H and g[y+dy][x+dx] != '#' for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if edge: o('tile %d %d 1100 1214 %x' % (X, Y, FL_MB | FL_SB | FL_IN | FL_NOM))
            else: o('tile %d %d 1008 0 %x' % (X, Y, FL_MB | FL_SB | FL_NOM))
        elif c in '~1235k|sS' and not (c in 'sS' and g[y][x] == '.'):
            water = c != 'S' or not any(inrect(x, y, s[3]) and s[4] == (25, 85) for s in SECTIONS)
            if c == 'S' and (x, y) in ((100, 6), (25, 85)): water = False
            if water:
                fs = random.choice(SEAWEED) if c == '~' and random.random() < 0.04 else 0
                o('tile %d %d 1008 %d %x' % (X, Y, fs, FL_IN | FL_UW | FL_NOM))
            else:
                o('tile %d %d 1100 0 %x' % (X, Y, FL_IN))
        elif c in 'eAKWRXHT' or (c == 'C' and x < 23 and 40 <= y <= 59):
            fl = FL_IN | FL_NOM | (FL_TAV if c == 'T' else 0)
            o('tile %d %d 558 0 %x' % (X, Y, fl))
        elif c == 'c':
            o('tile %d %d 558 176 %x' % (X, Y, FL_IN | FL_NOM | FL_MB))
        else:   # dry floor: '.', 'D', 'B', 'C', 'L', 'P', 'm'
            fl = FL_IN | (FL_NOM if c in 'DLP' or x < 23 else 0)
            o('tile %d %d 1100 0 %x' % (X, Y, fl))
        tmp = {'B': T_BRAZ, 'C': 741, 'D': T_GATE, 'P': T_PORTAL, 'X': 661, 'H': 603, 'k': T_SHRINE,
               '1': T_POLE, '2': T_POLE+1, '3': T_POLE+2, 's': T_SHELFE}.get(c)
        if c == '|': tmp = random.choice((1053, 1054, 1058, 1059))
        if c == 'L': tmp = T_LECT+[s[1] for s in SECTIONS].index((x, y))
        if c == 'S': tmp = T_SHELFB+[s[4] for s in SECTIONS].index((x, y))
        if tmp: items.append('place %d %d %d' % (tmp, X, Y))
out += items
open(os.path.join(sys.argv[1], 'lab11.spec'), 'w').write('\n'.join(out)+'\n')
print('spec lines:', len(out), 'items:', len(items))
