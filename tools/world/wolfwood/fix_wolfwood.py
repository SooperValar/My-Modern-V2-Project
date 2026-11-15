#!/usr/bin/env python3
"""Nov 15, Cody's notes on the first Wolfwood: Brann's shed was cut by the trail (restored from the backup taken
before the build), the trail ran through a black void (floor 1008: now field like the east road), the grey and dire
wolves needed a border (a thick tree line across the wood, one gap the monsters can't cross, a warning sign; dire
wolves only beyond it), and a pile of bones instead of skulls in Greyfang's den.
    fix_wolfwood.py <.dat folder> <backup folder from before build_wolfwood.py>"""
import sys, os, random, json, math, importlib.util, struct
HERE = os.path.dirname(os.path.abspath(__file__))
DAT, BK = sys.argv[1], sys.argv[2]
random.seed(1116)
# ---- B: Brann's shed and the trail's first stretch back as they were (raw tiles; nothing there held an item)
old = open(os.path.join(BK, 'map.dat'), 'rb').read(); cur = bytearray(open(os.path.join(DAT, 'map.dat'), 'rb').read())
n = 0
for x in range(570, 593):
    for y in range(650, 701):
        o = (x + y * 1024) * 28
        if old[o:o + 28] != cur[o:o + 28] and struct.unpack_from('<I', old, o + 12)[0] == 0 and struct.unpack_from('<I', cur, o + 12)[0] == 0:
            cur[o:o + 28] = old[o:o + 28]; n += 1
open(os.path.join(DAT, 'map.dat'), 'wb').write(cur)
print('restored', n, 'tiles')
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
OPS = []
def op(**k): OPS.append(k)
def run(label):
    global OPS
    n, msgs = W.apply(OPS, label)
    for m in msgs[:5]: print('  !', m)
    OPS = []
FOREST, DIRT, VOID = 1118, 989, 1008
TREES = [1238, 1240, 1112, 1114, 880, 882]
X0, X1, Y0, Y1 = 545, 655, 772, 850
def zone(x, y):
    for x0, y0, x1, y1, nm, fl in W.areas:
        if x0 <= x <= x1 and y0 <= y <= y1: return nm
    return ''
# ---- D (first, to keep it free): the trail, west of Brann's shed, then over the field to the wood
trail = set()
for y in range(654, 779):
    if y <= 700: cx = 575
    else: cx = 575 + round(3 * (1 - math.cos(math.pi * min(1, (y - 700) / 50))) / 2)
    cx += int(round(0.8 * math.sin(y / 9.0)))
    for x in range(cx - 1, cx + 2): trail.add((x, y))
# ---- C: the void around the quarry and on the way to the wood becomes field
filled = 0
for x in range(540, 676):
    for y in range(600, 772):
        if W.tile(x, y)[0] != VOID: continue
        if zone(x, y) in ('Aston', 'Memorial Park', 'Aston Hall', 'Deep Quarry'): continue
        op(op='floor', x=x, y=y, s=DIRT if random.random() < 0.04 else FOREST, set=False); filled += 1
        if (x, y) not in trail and not (570 <= x <= 595 and 735 <= y <= 771) and random.random() < 0.035:
            op(op='object', x=x, y=y, s=random.choice(TREES), block=3)
    if x % 15 == 0: run('field')
run('field')
for x, y in sorted(trail):
    if 578 <= x <= 582 and 659 <= y <= 664: continue          # never through the shed
    op(op='floor', x=x, y=y, s=DIRT, set=False); op(op='erase', x=x, y=y)
run('trail')
print('field tiles', filled)
# ---- E: the border between the grey wolves (y < 811) and the dire wolves (y > 816)
GAP = set()
for y in range(810, 817):
    for x in range(595, 600): GAP.add((x, y))            # where the main path crosses
for x in range(X0, X1 + 1):
    for y in range(810, 817):
        if (x, y) in GAP:
            op(op='floor', x=x, y=y, s=DIRT, set=False); op(op='erase', x=x, y=y); op(op='flag', x=x, y=y, bit=5, mode=1)   # no monsters: neither side crosses
        elif random.random() < 0.93:
            op(op='object', x=x, y=y, s=random.choice(TREES), block=3)
run('border')
# a path from the gap on to the den side
for y in range(817, 822):
    for x in range(596, 600): op(op='floor', x=x, y=y, s=DIRT, set=False); op(op='erase', x=x, y=y)
run('path past the border')
SIGN = W.apply([{'op': 'itempnew', 'from': 841, 'name': 'Sign (Wolfwood)'}], 'sign') and W.made[1]
W.apply([{'op': 'itempset', 't': SIGN, 'fields': {'description': 'Dire wolves beyond this point. Turn back unless you are a Master Sergeant or better. - Edda'}}], 'sign')
op(op='erase', x=594, y=808); op(op='place', x=594, y=808, t=SIGN, fresh=1)
run('warning sign')
# dire wolves only beyond the border, grey wolves only before it
def free(x, y): return W.tile(x, y)[1] == 0 and not W.tile(x, y)[4] and not W.tile(x, y)[2]
pend = {p[2]: (p[0], p[1]) for p in W.pending()}
for t in M['dires']:
    x, y = pend.get(t, (0, 0))
    if y >= 822: continue
    while True:
        tx, ty = random.randint(X0 + 4, X1 - 4), random.randint(824, 846)
        if free(tx, ty): break
    print('  dire', t, (x, y), '->', (tx, ty), W.apply([{'op': 'npcmove', 'x': x, 'y': y, 'tx': tx, 'ty': ty}], 'dire wolf')[1])
for t in M['greys']:
    x, y = pend.get(t, (0, 0))
    if y <= 806: continue
    while True:
        tx, ty = random.randint(X0 + 4, X1 - 4), random.randint(778, 804)
        if free(tx, ty): break
    print('  grey', t, (x, y), '->', (tx, ty), W.apply([{'op': 'npcmove', 'x': x, 'y': y, 'tx': tx, 'ty': ty}], 'grey wolf')[1])
# ---- F: a pile of bones in the den instead of the skulls
BONES = W.apply([{'op': 'itempnew', 'from': 25, 'name': 'Pile of Bones'}], 'bones') and W.made[1]
W.apply([{'op': 'itempset', 't': BONES, 'fields': {'sprite': [418, 0], 'description': "Gnawed bones, deer and worse. Old Greyfang's pack has been eating well."}}], 'bones')
for x, y in [(607, 835), (613, 841), (614, 834), (606, 841), (611, 843)]: op(op='erase', x=x, y=y)
for x, y in [(607, 835), (613, 841), (614, 834), (606, 841), (611, 843), (604, 837)]: op(op='place', x=x, y=y, t=BONES, fresh=1)
run('bones')
M.update({'sign': SIGN, 'bones': BONES}); json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
print(W.save())
