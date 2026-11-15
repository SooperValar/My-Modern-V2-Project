#!/usr/bin/env python3
"""Nov 15: the NPCs for Cody's own Wolfwood (he made the zones): Huntmaster Edda (a woman) in "Wynn & Edda's Hut",
Grey Wolves through the "Eastern Forest", Dire Wolves through the "Deep Forest" and more of them in the "Dire Wolves
Den", Old Greyfang at 414,541; Edda's three item quests (Wolf Head, Dire Wolf Head: forever; Greyfang's Fang: once,
the Greyfang Amulet). Items from build_wolfwood.py (made.json). Every placed wolf is its own template (from the Spider,
392, not "simple"), with the strength of the Spider / Quarry Golem / Prime Golem.
    place_wolfwood.py <.dat folder> [--seed N]
Then off_road.py: no Grey Wolf within 3 tiles of the road (the dirt, floor 989) through the Eastern Forest."""
import sys, os, random, json, importlib.util, struct
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1117)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
WHEAD, DHEAD, FANG, AMULET = M['wolf_head'], M['dire_head'], M['fang'], M['amulet']
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]
def boxes(name): return [a[:4] for a in W.areas if a[4] == name]
def inside(bs, x, y): return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in bs)
FOREST, DEEP, DEN, HUT = boxes('Eastern Forest'), boxes('Deep Forest'), boxes('Dire Wolves Den'), boxes("Wynn & Edda's Hut")
assert FOREST and DEEP and DEN and HUT, 'zones missing'
taken = set()
def free(x, y):
    t = W.tile(x, y)
    return t[1] == 0 and not t[4] and not t[2] and not (t[7] & 1) and not (t[7] & 32) and t[0] not in (0, 1008)
def spots(n, ok, bs, gap):
    cells = [(x, y) for x0, y0, x1, y1 in bs for x in range(x0 + 1, x1) for y in range(y0 + 1, y1) if ok(x, y) and free(x, y)]
    random.shuffle(cells); out = []
    for c in cells:
        if all(abs(c[0] - a) + abs(c[1] - b) >= gap for a, b in list(taken) + out): out.append(c)
        if len(out) == n: break
    taken.update(out); return out
# ---- templates
def stats(src, pct):
    f = me.tpl_read(W.tchar, src * me.CHAR_SIZE, me.CT_FIELDS)
    a = list(f['attrib']); hp = list(f['hp']); en = list(f['end']); mn = list(f['mana']); sk = list(f['skill'])
    for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
    hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
    for i in range(50): sk[i * 6] = min(255, round(sk[i * 6] * pct / 100))
    return {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': sk, 'armor_bonus': f['armor_bonus'], 'weapon_bonus': f['weapon_bonus'],
            'points_tot': round(f['points_tot'] * pct / 100)}
def wolf(name, src, pct, sprite, items, x, y, text, desc):
    t = made({'op': 'ctempnew', 'from': 392, 'name': name})
    f = stats(src, pct); b = me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)
    dd = list(b['data'])
    for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
    dd[42] = dd[44] = 33
    f.update({'data': dd, 'sprite': sprite, 'flags': b['flags'] & ~(1 << 27), 'item': list(items) + [0] * (40 - len(items)), 'description': desc})
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': text, 'respawn': False}], 'wolf')
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': random.choice([1, 2, 3, 4])}], 'place')
    for m in msgs: print('  !', m, name, x, y)
    return t
GREY_D = 'A grey wolf, lean and hungry. Its yellow eyes never leave you.'
DIRE_D = 'A black dire wolf, as tall at the shoulder as a man at the hip. Its growl is felt more than heard.'
greys = [wolf('Grey Wolf', 392, random.choice([90, 100, 110]), 43000, [WHEAD], x, y, ['', 'The wolf bares its teeth at %s.'], GREY_D)
         for x, y in spots(24, lambda x, y: True, FOREST, 7)]
taken.add((414, 541))
den = [wolf('Dire Wolf', 2037, random.choice([95, 100, 108]), 43500, [DHEAD], x, y, ['', 'The dire wolf crouches, watching %s.'], DIRE_D)
       for x, y in spots(9, lambda x, y: True, DEN, 4)]
deep = [wolf('Dire Wolf', 2037, random.choice([95, 100, 108]), 43500, [DHEAD], x, y, ['', 'The dire wolf crouches, watching %s.'], DIRE_D)
        for x, y in spots(6, lambda x, y: not inside(DEN, x, y), DEEP, 9)]
gx, gy = 414, 541
if not free(gx, gy): gx, gy = next((x, y) for r in range(1, 6) for x in range(414 - r, 415 + r) for y in range(541 - r, 542 + r) if free(x, y))
GREYFANG = wolf('Old Greyfang', 2047, 112, 44000, [FANG], gx, gy, ['', 'Old Greyfang lifts his scarred muzzle and howls at %s.'],
                'The pack leader of the Wolfwood: huge, grey-white and scarred, with one fang longer than the rest.')
# ---- Huntmaster Edda: a woman (Inga's look and kind), in the hut
inga = me.tpl_read(W.tchar, 50 * me.CHAR_SIZE, me.CT_FIELDS)
EDDA = made({'op': 'ctempnew', 'from': 25, 'name': 'Huntmaster Edda'})
dd = list(me.tpl_read(W.tchar, EDDA * me.CHAR_SIZE, me.CT_FIELDS)['data'])
for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = WHEAD, 0, 160, 0, 1, 0
W.apply([{'op': 'ctempset', 't': EDDA, 'fields': {'data': dd, 'item': [0] * 40, 'sprite': inga['sprite'], 'kindred': inga['kindred'], 'alignment': 10000,
          'description': 'The huntmaster of the Wolfwood, a weathered woman in a coat of wolf pelts, a bow over her shoulder.'},
          'text': ['Ha!', 'You picked the wrong hunter, %s!', "Welcome, %s. I pay for every wolf head, more for dire wolves. Bring me Old Greyfang's fang and you'll have something special."],
          'respawn': False}], 'Edda')
ex, ey = spots(1, lambda x, y: True, HUT, 1)[0]
print('Edda at', (ex, ey), W.apply([{'op': 'npcplace', 't': EDDA, 'x': ex, 'y': ey, 'dir': 1}], 'place Edda')[1])
def extra(want, exp, give):
    t = made({'op': 'ctempnew', 'from': EDDA, 'name': 'Huntmaster Edda'})
    d2 = list(dd); d2[49], d2[51], d2[66] = want, exp, give
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': d2}, 'text': [None, None, ''], 'respawn': False}], 'Edda extra'); return t
EDDA_DIRE, EDDA_FANG = extra(DHEAD, 600, 0), extra(FANG, 14000, AMULET)
qs, npcs = W.talk_load()
qs['alias'][EDDA_DIRE] = EDDA; qs['alias'][EDDA_FANG] = EDDA
top = max([v for v in qs['order'].values() if v > 0] or [0])
for k, t in enumerate((EDDA, EDDA_DIRE, EDDA_FANG)): qs['order'][t] = top + 1 + k
qs['qrew'][EDDA] = {'lim': 0, 'first': 0, 'gold': 800, 'st': [], 'rmin': 4, 'rmax': -1, 'n': 1}
qs['qrew'][EDDA_DIRE] = {'lim': 0, 'first': 0, 'gold': 3000, 'st': [], 'rmin': 6, 'rmax': -1, 'n': 1}
qs['qrew'][EDDA_FANG] = {'lim': 1, 'first': 0, 'gold': 70000, 'st': [], 'rmin': 7, 'rmax': -1, 'n': 1}
print(W.talk_save(qs, npcs))
def rank_of(t): return me.RANKS[me.points2rank(struct.unpack_from('<i', W.tchar, t * me.CHAR_SIZE + 709)[0])]
print('grey wolves', len(greys), rank_of(greys[0]), '| dire wolves: den', len(den), 'deep forest', len(deep), rank_of(den[0]), '| greyfang', GREYFANG, (gx, gy), rank_of(GREYFANG))
print('edda', EDDA, EDDA_DIRE, EDDA_FANG)
print(W.save())
M.update({'greys': greys, 'dires': den + deep, 'greyfang': GREYFANG, 'edda': EDDA, 'edda_dire': EDDA_DIRE, 'edda_fang': EDDA_FANG})
json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
