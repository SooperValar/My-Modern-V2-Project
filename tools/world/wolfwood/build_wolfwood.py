#!/usr/bin/env python3
"""The Wolfwood and the Hunters' Lodge (Nov 15): a forest beyond Bandit Hollow and the Old Quarry, reached by a trail
from the quarry trail between the two. Grey Wolves (Sergeant), Dire Wolves (Master Sergeant) deeper in, Old Greyfang
(First Sergeant) in his den at the far end; Huntmaster Edda at the lodge buys wolf heads and dire wolf heads (forever)
and wants Old Greyfang's fang (once: the Greyfang Amulet).

    build_wolfwood.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)
Sprites: Grey Wolf 43000, Dire Wolf 43500, Old Greyfang 44000 (tools/sprites/make_creature.py), heads 44500 / 44501
(tools/sprites/head_icon.py). Map: x grows down-right (south on screen), y grows up-right (east)."""
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
    for m in msgs[:5]: print('  !', m)
    OPS = []
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]

FOREST, DIRT = 1118, 989
TREES = [1238, 1240, 1112, 1114, 880, 882]
TIMBER = [36060, 36061, 36062, 36063]; OAK = [37000, 37001, 37002, 37003]
X0, X1, Y0, Y1 = 545, 655, 772, 850          # the wood
DEN = (610, 838)                               # Old Greyfang's den (a clearing at the far end)
LODGE = (582, 756, 590, 764)                   # the Hunters' Lodge, door on its north wall (x0) at y 760
ENTRY = (578, 772)

# ---- the trail: from the quarry trail (577,653) between the Hollow and the quarry, past the lodge, into the wood
trail = []
for y in range(653, 779):
    cx = 577 + int(round(1.3 * math.sin((y - 653) / 11.0)))
    for x in range(cx - 1, cx + 2): trail.append((x, y))
for x, y in trail:
    op(op='floor', x=x, y=y, s=DIRT, set=False); op(op='erase', x=x, y=y)
run('Wolfwood: trail')

# ---- paths inside the wood (kept free of trees): entrance -> a winding way to the den, two side ways
free = set(trail)
def path(pts, w=1):
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(abs(bx - ax), abs(by - ay))
        for i in range(n + 1):
            x = round(ax + (bx - ax) * i / n); y = round(ay + (by - ay) * i / n)
            for dx in range(-w, w + 1):
                for dy in range(-w, w + 1): free.add((x + dx, y + dy))
MAIN = [ENTRY, (585, 785), (575, 798), (590, 810), (604, 818), (598, 828), DEN]
path(MAIN, 1)
path([(585, 785), (612, 790), (632, 800), (640, 815)], 1)
path([(575, 798), (560, 808), (556, 825), (570, 838)], 1)
CLEARINGS = [((600, 792), 5), ((628, 812), 6), ((560, 818), 5), ((582, 830), 4), (DEN, 7)]
def in_clear(x, y): return any((x - cx) ** 2 + (y - cy) ** 2 <= r * r for (cx, cy), r in CLEARINGS)
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        d = min(x - X0, X1 - x, y - Y0, Y1 - y)
        p = 0.95 if d <= 2 else 0.6 if d <= 4 else 0.20
        if (x, y) in free or in_clear(x, y): p = 0
        op(op='floor', x=x, y=y, s=DIRT if (x, y) in free and random.random() < 0.7 else (DIRT if random.random() < 0.06 else FOREST), set=False)
        if random.random() < p: op(op='object', x=x, y=y, s=random.choice(TREES), block=3)
        else: op(op='erase', x=x, y=y)
    if x % 20 == 0: run('Wolfwood: ground and trees')
run('Wolfwood: ground and trees')
# the den: dirt, bones
for x in range(DEN[0] - 7, DEN[0] + 8):
    for y in range(DEN[1] - 7, DEN[1] + 8):
        if (x - DEN[0]) ** 2 + (y - DEN[1]) ** 2 <= 36: op(op='floor', x=x, y=y, s=DIRT if random.random() < 0.6 else FOREST, set=False)
for t, x, y in [(443, 607, 835), (308, 613, 841), (443, 614, 834), (447, 606, 841), (443, 611, 843)]:
    op(op='place', x=x, y=y, t=t, fresh=1)
run('the den')

# ---- the Hunters' Lodge
x0, y0, x1, y1 = LODGE
for x in range(x0 - 3, x1 + 3):
    for y in range(y0 - 3, y1 + 3):
        if (x, y) not in free: op(op='erase', x=x, y=y)
        op(op='floor', x=x, y=y, s=FOREST if random.random() < 0.8 else DIRT, set=False)
run('lodge ground')
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        op(op='floor', x=x, y=y, s=random.choice(OAK), set=False); op(op='flag', x=x, y=y, bit=2, mode=1)
        if x in (x0, x1) or y in (y0, y1): op(op='object', x=x, y=y, s=random.choice(TIMBER), block=3)
        else: op(op='erase', x=x, y=y)
run('lodge walls')
op(op='erase', x=x0, y=760); op(op='place', x=x0, y=760, t=1440, fresh=1)
for t, x, y in [(82, 587, 762), (741, 588, 758), (741, 584, 763), (764, 581, 758), (764, 581, 762)]:
    op(op='place', x=x, y=y, t=t, fresh=1)
for s_, x, y in [(16882, 589, 763), (16882, 589, 762), (38164, 586, 758)]:
    op(op='object', x=x, y=y, s=s_, block=1)
for x in range(x0 - 4, x1 + 4):
    for y in range(y0 - 4, y1 + 4): op(op='flag', x=x, y=y, bit=5, mode=1)        # no monsters at the lodge
run('lodge door, fire bowls, safe spot')

# ---- items
def item(src, name, desc, **f):
    t = made({'op': 'itempnew', 'from': src, 'name': name})
    f['flags'] = me.tpl_read(W.titem, t * me.ITEM_SIZE, me.IT_FIELDS)['flags'] & ~me.IF_LABYDESTROY   # (copied from a labyrinth item: it would vanish outside one); f['description'] = desc
    W.apply([{'op': 'itempset', 't': t, 'fields': f}], 'item'); return t
WHEAD = item(610, 'Wolf Head', 'The head of a grey wolf from the Wolfwood. Huntmaster Edda pays for these.', sprite=[44500, 0], value=30)
DHEAD = item(610, 'Dire Wolf Head', 'The head of a black dire wolf, twice the size of a grey one. Huntmaster Edda pays well for these.', sprite=[44501, 0], value=120)
FANG = item(206, "Greyfang's Fang", "A long yellowed fang, broken from the jaw of Old Greyfang, the pack leader of the Wolfwood.", value=0)
attr = [0] * 15; attr[0] = 2; attr[9] = 2           # +2 Bravery, +2 Agility
AMULET = item(105, 'Greyfang Amulet', "Old Greyfang's fang on a leather thong, set in silver by Huntmaster Edda. It gives its wearer the old wolf's nerve and speed.",
              attrib=attr, skill=[0] * 150, min_rank=7, value=4000)
print('items: wolf head %d, dire wolf head %d, fang %d, amulet %d' % (WHEAD, DHEAD, FANG, AMULET))

# ---- NPCs: the test Grey Wolf (2057) becomes the forest's first wolf; every placed wolf is its own template
GROUP = 33
BASE = 2057
def stats(src, pct):
    f = me.tpl_read(W.tchar, src * me.CHAR_SIZE, me.CT_FIELDS)
    a = list(f['attrib']); hp = list(f['hp']); en = list(f['end']); mn = list(f['mana']); sk = list(f['skill'])
    for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
    hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
    for i in range(50): sk[i * 6] = min(255, round(sk[i * 6] * pct / 100))
    out = {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': sk}
    for k in ('armor_bonus', 'weapon_bonus', 'points_tot'):
        if k in f: out[k] = f[k] if k != 'points_tot' else round(f[k] * pct / 100)
    return out
def setup(t, name, src, pct, sprite, items, text, desc):
    f = stats(src, pct)
    dd = list(me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['data'])
    for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
    dd[42] = dd[44] = GROUP
    f.update({'data': dd, 'sprite': sprite, 'item': list(items) + [0] * (40 - len(items)), 'description': desc, 'name': name})
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': text, 'respawn': True}], 'npc')
def npc(name, src, pct, sprite, items, x, y, text, desc):
    t = made({'op': 'ctempnew', 'from': BASE, 'name': name})
    setup(t, name, src, pct, sprite, items, text, desc)
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': random.choice([1, 2, 3, 4])}], 'place')
    for m in msgs: print('  !', m, name, x, y)
    return t
def spot_free(x, y): return W.tile(x, y)[1] == 0 and not W.tile(x, y)[4] and X0 + 3 < x < X1 - 3 and Y0 + 3 < y < Y1 - 3
def spots(n, ylo, yhi, used):
    out = []
    while len(out) < n:
        x, y = random.randint(X0 + 4, X1 - 4), random.randint(ylo, yhi)
        if spot_free(x, y) and all(abs(x - a) + abs(y - b) > 5 for a, b in used + out): out.append((x, y))
    return out
WOLF_DESC = 'A grey wolf, lean and hungry. Its yellow eyes never leave you.'
WOLF_TXT = ['', 'The wolf bares its teeth at %s.']
DIRE_DESC = 'A black dire wolf, as tall at the shoulder as a man at the hip. Its growl is felt more than heard.'
used = [DEN]
setup(BASE, 'Grey Wolf', 392, 100, 43000, [WHEAD], WOLF_TXT, WOLF_DESC)
first = spots(1, 776, 806, used); used += first
c = W.living(BASE)
if c:
    cx, cy = next((x, y) for x in range(500, 570) for y in range(590, 660) if W.tile(x, y)[2] == c[0])
    n, msgs = W.apply([{'op': 'npcmove', 'x': cx, 'y': cy, 'tx': first[0][0], 'ty': first[0][1]}], 'move the test wolf'); print('  moved test wolf', msgs)
greys = [BASE] + [npc('Grey Wolf', 392, random.choice([90, 100, 110]), 43000, [WHEAD], x, y, WOLF_TXT, WOLF_DESC) for x, y in spots(15, 776, 815, used)]
used += []
dires = [npc('Dire Wolf', 2037, random.choice([95, 100, 108]), 43500, [DHEAD], x, y, ['', 'The dire wolf crouches, watching %s.'], DIRE_DESC)
         for x, y in spots(9, 812, 846, used)]
GREYFANG = npc('Old Greyfang', 2047, 112, 44000, [FANG], DEN[0], DEN[1], ['', 'Old Greyfang lifts his scarred muzzle and howls at %s.'],
               'The pack leader of the Wolfwood: huge, grey-white and scarred, with one fang longer than the rest.')
# ---- Huntmaster Edda and her two extra quests (dire wolf heads, the fang)
EDDA = made({'op': 'ctempnew', 'from': 25, 'name': 'Huntmaster Edda'})
dd = list(me.tpl_read(W.tchar, EDDA * me.CHAR_SIZE, me.CT_FIELDS)['data'])
dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = WHEAD, 0, 63, 0, 1, 0
for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
W.apply([{'op': 'ctempset', 't': EDDA, 'fields': {'data': dd, 'item': [0] * 40,
          'description': 'The huntmaster of the lodge, in a coat of wolf pelts, a bow over her shoulder.'},
          'text': ['Ha!', 'You picked the wrong hunter, %s!', "Welcome to the Hunters' Lodge, %s. I pay for every wolf head, more for dire wolves. Bring me Old Greyfang's fang and you'll have something special."],
          'respawn': False}], 'Edda')
n, msgs = W.apply([{'op': 'npcplace', 't': EDDA, 'x': 586, 'y': 760, 'dir': 1}], 'place Edda'); print(msgs)
def extra(want, exp, give):
    t = made({'op': 'ctempnew', 'from': EDDA, 'name': 'Huntmaster Edda'})
    d2 = list(dd); d2[49], d2[51], d2[66] = want, exp, give
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': d2}, 'text': [None, None, ''], 'respawn': False}], 'Edda extra')
    return t
EDDA_DIRE = extra(DHEAD, 240, 0)
EDDA_FANG = extra(FANG, 14000, AMULET)
qs, npcs = W.talk_load()
qs['alias'][EDDA_DIRE] = EDDA; qs['alias'][EDDA_FANG] = EDDA
top = max([v for v in qs['order'].values() if v > 0] or [0])
for k, t in enumerate((EDDA, EDDA_DIRE, EDDA_FANG)): qs['order'][t] = top + 1 + k
qs['qrew'][EDDA] = {'lim': 0, 'first': 0, 'gold': 300, 'st': [], 'rmin': 4, 'rmax': -1, 'n': 1}
qs['qrew'][EDDA_DIRE] = {'lim': 0, 'first': 0, 'gold': 200, 'st': [], 'rmin': 6, 'rmax': -1, 'n': 1}
qs['qrew'][EDDA_FANG] = {'lim': 1, 'first': 0, 'gold': 70000, 'st': [], 'rmin': 7, 'rmax': -1, 'n': 1}
print(W.talk_save(qs, npcs))
# ---- zones
zs, order = {}, []
for x0_, y0_, x1_, y1_, nm, fl in W.areas:
    if nm not in zs: zs[nm] = {'name': nm, 'flag': fl, 'boxes': []}; order.append(nm)
    zs[nm]['boxes'].append([x0_, y0_, x1_, y1_])
for nm, fl, box in (('Wolfwood', 1, [X0, Y0, X1, Y1]), ("Hunters' Lodge", 0, list(LODGE))):
    if nm not in zs: zs[nm] = {'name': nm, 'flag': fl, 'boxes': [box]}; order.append(nm)
print('zones:', W.zones_save([zs[n] for n in order]))
def rank_of(t): return me.RANKS[me.points2rank(struct.unpack_from('<i', W.tchar, t * me.CHAR_SIZE + 709)[0])]
print('grey wolves', greys, rank_of(greys[1])); print('dire wolves', dires, rank_of(dires[0])); print('greyfang', GREYFANG, rank_of(GREYFANG))
print('edda', EDDA, 'extras', EDDA_DIRE, EDDA_FANG)
print(W.save())
json.dump({'wolf_head': WHEAD, 'dire_head': DHEAD, 'fang': FANG, 'amulet': AMULET, 'greys': greys, 'dires': dires, 'greyfang': GREYFANG,
           'edda': EDDA, 'edda_dire': EDDA_DIRE, 'edda_fang': EDDA_FANG}, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
