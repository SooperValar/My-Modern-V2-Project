#!/usr/bin/env python3
"""The Old Quarry (Nov 14): a stone pit south of the east road, its Quarry Golems and their Overseer, and the Deep
Grolm caves in its far corner. Master Sergeant to First Sergeant.

    build_quarry.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)

Monster looks: the Quarry Golem is the Golem recoloured in sandstone (sprites 41000+), the Deep Grolm the Grolm in
cave slate (42100+): tools/sprites/recolor_creature.py. Writes made.json (template numbers) beside this script;
talk.py turns it into the npctalk.dat lines. Map: x grows down-right (south on screen), y up-right (east)."""
import sys, os, random, json, math, importlib.util, struct
HERE = os.path.dirname(os.path.abspath(__file__))
DAT = sys.argv[1]
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1115)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
OPS = []
def op(**k): OPS.append(k)
def run(label):
    global OPS
    n, msgs = W.apply(OPS, label)
    for m in msgs: print('  !', m)
    OPS = []
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]

FOREST, DIRT, CAVE = 1118, 989, 1014
SAND = [35100, 35101, 35102, 35103]                   # dusty path: the pit floor
OUTCROPS = [16352, 16360, 16368, 16376]                # rock pillars (the game's rock pieces)
TREES = [1238, 1240, 1112, 1114, 880, 882]
RIM = 122                     # the gold-brown rock wall (mine wall)
CAVEWALL = 124                # the dark rock wall
ROCKS = [1274, 1276, 1278]    # loose rocks (the editor's Cave brush)
SLABS = [101, 1201, 1215]     # cut stone blocks (the game's cut-down walls)
X0, X1, Y0, Y1 = 576, 644, 640, 744

def inside_pit(x, y):
    return ((x - 610) / 20.0) ** 2 + ((y - 676) / 28.0) ** 2 <= 1.0
def inside_cave(x, y):
    return ((x - 630) / 10.0) ** 2 + ((y - 724) / 12.0) ** 2 <= 1.0
def near(f, x, y, r=1):
    return any(f(x + dx, y + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1))

# the trail from the east road (533,652) to the quarry's mouth (588,652)
trail = set()
for x in range(533, 592):
    cy = 652 + int(round(1.0 * math.sin((x - 533) / 7.0)))
    for y in range(cy - 1, cy + 2): trail.add((x, y))
mouth_pit = {(x, y) for x in range(582, 602) for y in range(650, 656)}
mouth_cave = {(x, y) for x in range(624, 630) for y in range(688, 715)}
shed = (578, 659, 582, 664)

for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        pit, cave = inside_pit(x, y), inside_cave(x, y)
        if pit or (x, y) in mouth_pit:
            op(op='floor', x=x, y=y, s=random.choice(SAND), set=False); op(op='erase', x=x, y=y); continue
        if cave or (x, y) in mouth_cave:
            op(op='floor', x=x, y=y, s=CAVE, set=False); op(op='erase', x=x, y=y)
            if cave or (x, y) in mouth_cave: op(op='flag', x=x, y=y, bit=2, mode=1)
            continue
        rim = near(inside_pit, x, y, 2) or near(inside_cave, x, y, 2)
        op(op='floor', x=x, y=y, s=FOREST if not rim else CAVE, set=False)
        if (x, y) in trail or (x, y) in mouth_pit:
            op(op='erase', x=x, y=y); continue
        if rim:
            op(op='object', x=x, y=y, s=CAVEWALL if near(inside_cave, x, y, 2) and not near(inside_pit, x, y, 2) else RIM, block=3)
        else:
            edge = min(x - X0, X1 - x, y - Y0, Y1 - y)
            p = 0.9 if edge <= 1 and x > 590 else 0.12
            if x <= 585 and y < 670: p = 0.03
            if random.random() < p: op(op='object', x=x, y=y, s=random.choice(TREES), block=3)
            else: op(op='erase', x=x, y=y)
run('Old Quarry: ground, rim, caves')
for x, y in trail:      # across the field too
    op(op='floor', x=x, y=y, s=DIRT, set=False); op(op='erase', x=x, y=y)
run('trail')
# loose rocks and stacks of cut stone in the pit; torches in the caves
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        if inside_pit(x, y) and not near(lambda a, b: (a, b) in mouth_pit, x, y, 2) and not near(lambda a, b: (a, b) in mouth_cave, x, y, 1):
            r = random.random()
            if r < 0.022: op(op='object', x=x, y=y, s=random.choice(OUTCROPS), block=3)
for cx, cy in ((600, 662), (619, 688), (604, 694), (617, 658), (596, 680)):
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0))[:random.randint(3, 5)]:
        op(op='object', x=cx + dx, y=cy + dy, s=random.choice(SLABS), block=1)
run('rocks and stone')
PLACE = [(764, 623, 718), (764, 636, 720), (764, 624, 730), (764, 636, 731), (741, 611, 678), (2007, 580, 657), (2007, 580, 658)]
for t, x, y in PLACE: op(op='place', x=x, y=y, t=t, fresh=1)
run('torches, fire, barrels')
# Brann's shed by the mouth
x0, y0, x1, y1 = shed
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        if x in (x0, x1) or y in (y0, y1):
            op(op='object', x=x, y=y, s=random.choice([36060, 36061, 36062, 36063]), block=3); op(op='flag', x=x, y=y, bit=2, mode=1)
        else:
            op(op='erase', x=x, y=y); op(op='floor', x=x, y=y, s=random.choice([37000, 37001, 37002, 37003]), set=False); op(op='flag', x=x, y=y, bit=2, mode=1)
run('shed')
op(op='erase', x=x0, y=661); op(op='place', x=x0, y=661, t=1440, fresh=1)
for x in range(577, 586):
    for y in range(653, 666): op(op='flag', x=x, y=y, bit=5, mode=1)       # no monsters around Brann
run('shed door, safe spot')

# ---------------------------------------------------------------- items
def item(src, name, desc, **f):
    t = made({'op': 'itempnew', 'from': src, 'name': name})
    f['flags'] = me.tpl_read(W.titem, t * me.ITEM_SIZE, me.IT_FIELDS)['flags'] & ~me.IF_LABYDESTROY   # (copied from a labyrinth item: it would vanish outside one); f['description'] = desc
    W.apply([{'op': 'itempset', 't': t, 'fields': f}], 'item'); return t
SEAL = item(1270, "Foreman's Seal", "A brass seal on a chain, stamped with the quarry's mark. The Golem Overseer wore it.", sprite=[602, 0])
AXE = item(1270, "Chieftain's Stone Axe", 'A heavy axe of chipped slate, bound with gut. The Deep Grolm Chieftain carried it.', sprite=[1725, 0])
AMULET = item(191, "Quarryman's Amulet", "A plain stone amulet on a leather cord. Quarrymen wear them to work longer.",
              skill=[0] * 150, end=[20, 0, 0], min_rank=6, value=3000)
STONESKIN = item(224, 'Stoneskin Potion', 'A grey, gritty draught. For ten minutes your skin is as hard as quarry stone.',
                 attrib=[0] * 15, armor=[0, 8], duration=10800, sprite=[1705, 0], min_rank=7, value=2000)
print('items: seal %d axe %d amulet %d stoneskin %d' % (SEAL, AXE, AMULET, STONESKIN))

# ---------------------------------------------------------------- NPCs
def scaled(src, pct):
    f = me.tpl_read(W.tchar, src * me.CHAR_SIZE, me.CT_FIELDS)
    a = list(f['attrib']); hp = list(f['hp']); en = list(f['end']); mn = list(f['mana']); sk = list(f['skill'])
    for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
    hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
    for i in range(50): sk[i * 6] = min(255, round(sk[i * 6] * pct / 100))
    return {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': sk}
def npc(src, name, pct, x, y, d=4, items=(), text=None, extra=None, desc=None, sprite=None, group=None):
    t = made({'op': 'ctempnew', 'from': src, 'name': name})
    f = scaled(src, pct) if pct != 100 else {}
    dd = list(me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['data'])
    for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
    if group: dd[42] = dd[44] = group
    for k, v in (extra or {}).items(): dd[k] = v
    f['data'] = dd
    if items is not None: f['item'] = list(items) + [0] * (40 - len(items))
    if desc is not None: f['description'] = desc
    if sprite: f['sprite'] = sprite
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': text or [], 'respawn': False}], 'npc')
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d}], 'place')
    for m in msgs: print('  !', m)
    return t
def rank_of(t):
    return me.RANKS[me.points2rank(struct.unpack_from('<i', W.tchar, t * me.CHAR_SIZE + 709)[0])]
GOLEM_TXT = ['The stone settles.', 'Intruder. Remove.']
def free(x, y): return W.tile(x, y)[1] == 0 and not W.tile(x, y)[4]
golem_spots = []
while len(golem_spots) < 10:
    x, y = random.randint(592, 628), random.randint(650, 702)
    if inside_pit(x, y) and free(x, y) and abs(x - 610) + abs(y - 676) > 4 and all(abs(x - a) + abs(y - b) > 5 for a, b, _ in golem_spots):
        golem_spots.append((x, y, 82))
golems = [npc(323, 'Quarry Golem', p, x, y, d=random.choice([1, 2, 3, 4]), text=GOLEM_TXT, sprite=41000, group=31, items=[],
              desc='A golem of sandstone, cut from the quarry itself. It still works the stone, and everything that walks in.') for x, y, p in golem_spots]
OVERSEER = npc(323, 'Golem Overseer', 100, 610, 676, d=2, items=[SEAL], text=['Order restored.', 'Work halts for no one, %s.'], sprite=41000, group=31,
               desc="The biggest of the quarry's golems. A brass seal hangs from its neck.")
GROLM_TXT = ['Meat for the deep!', 'Up from the dark - kill, %s!']
grolm_spots = [(625, 717, 140), (630, 715, 140), (634, 721, 140), (626, 727, 140), (631, 728, 140), (622, 722, 140), (637, 726, 140)]
grolms = [npc(123, 'Deep Grolm', p, x, y, d=random.choice([1, 2, 3, 4]), text=GROLM_TXT, sprite=42100, group=32, items=[],
              desc='A grolm from the deep caves, grey as slate, eyes pale from the dark.') for x, y, p in grolm_spots]
CHIEF = npc(123, 'Deep Grolm Chieftain', 170, 635, 731, d=3, items=[AXE], text=['The deep keeps you now.', 'You come into MY dark, %s?'], sprite=42100, group=32,
            desc='A huge slate-grey grolm with a stone axe. The other Deep Grolms fall silent around him.')
BRANN = npc(25, 'Brann', 100, 582, 657, d=4, items=[], extra={49: SEAL, 37: 1, 50: 0, 51: 0, 72: 0},
            text=['Ha!', 'Get off my quarry!', "Careful, %s - the golems we cut to work the stone have turned on us, and grolms came up from the deep caves. Talk to me if you want work."],
            desc='The foreman of the Old Quarry, grey with stone dust.')
print('npcs: golems %s overseer %d grolms %s chieftain %d brann %d' % (golems, OVERSEER, grolms, CHIEF, BRANN))
for t in (golems[0], OVERSEER, grolms[0], CHIEF): print('  %d %s' % (t, rank_of(t)))
print(W.save())
json.dump({'seal': SEAL, 'axe': AXE, 'amulet': AMULET, 'stoneskin': STONESKIN, 'golems': golems, 'overseer': OVERSEER,
           'grolms': grolms, 'chief': CHIEF, 'brann': BRANN}, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
