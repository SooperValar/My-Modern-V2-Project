#!/usr/bin/env python3
"""More wolves (Cody, Nov 15): more Grey Wolves all through the Eastern Forest (off its road), and more Dire Wolves the
closer to Old Greyfang (414,541): spots in the Deep Forest / Dire Wolves Den are picked with a weight that falls with
the distance to him, and may stand closer together near him.
    add_wolves.py <.dat folder> <grey wolves to add> <dire wolves to add> [--seed N]"""
import sys, os, random, json, math, importlib.util, struct
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]; NG, ND = int(sys.argv[2]), int(sys.argv[3])
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1118)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
GF = (414, 541)
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]
def boxes(name): return [a[:4] for a in W.areas if a[4] == name]
FOREST, DEEP, DEN = boxes('Eastern Forest'), boxes('Deep Forest'), boxes('Dire Wolves Den')
road = {(x, y) for x0, y0, x1, y1 in FOREST for x in range(x0 - 3, x1 + 4) for y in range(y0 - 3, y1 + 4) if W.tile(x, y)[0] == 989}
def near_road(x, y, r=3): return any((x + dx, y + dy) in road for dx in range(-r, r + 1) for dy in range(-r, r + 1))
def free(x, y):
    t = W.tile(x, y); return t[1] == 0 and not t[4] and not t[2] and not (t[7] & 1) and not (t[7] & 32) and t[0] not in (0, 1008)
# where every wolf lives now (spawn points or where it stands)
P = {p[2]: (p[0], p[1]) for p in W.pending()}
stand = {}
for x0, y0, x1, y1 in FOREST + DEEP:
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if W.tile(x, y)[2]: stand[W.tile(x, y)[2]] = (x, y)
def pos(t): return P.get(t) or next((stand[c] for c in W.living(t) if c in stand), None)
taken = [p for p in (pos(t) for t in M['greys'] + M['dires'] + [M['greyfang']]) if p]
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
def far(c, gap): return all(abs(c[0] - a) + abs(c[1] - b) >= gap for a, b in taken)
# grey wolves: evenly, off the road
cells = [(x, y) for x0, y0, x1, y1 in FOREST for x in range(x0 + 1, x1) for y in range(y0 + 1, y1) if free(x, y) and not near_road(x, y)]
random.shuffle(cells); greys = []
for gap in (6, 5, 4):
    for c in cells:
        if len(greys) == NG: break
        if far(c, gap):
            taken.append(c)
            greys.append(wolf('Grey Wolf', 392, random.choice([90, 100, 110]), 43000, [M['wolf_head']], c[0], c[1],
                              ['', 'The wolf bares its teeth at %s.'], 'A grey wolf, lean and hungry. Its yellow eyes never leave you.'))
# dire wolves: weighted towards Old Greyfang; near him they may stand closer together
cells = list({(x, y) for x0, y0, x1, y1 in DEEP + DEN for x in range(x0 + 1, x1) for y in range(y0 + 1, y1) if free(x, y)})
dires = []
while len(dires) < ND and cells:
    w = [1.0 / (3 + math.hypot(x - GF[0], y - GF[1])) ** 1.6 for x, y in cells]
    c = random.choices(cells, weights=w)[0]; cells.remove(c)
    d = math.hypot(c[0] - GF[0], c[1] - GF[1])
    if d < 2.5 or not far(c, 3 if d < 15 else 5 if d < 30 else 7): continue
    taken.append(c)
    dires.append(wolf('Dire Wolf', 2037, random.choice([95, 100, 108]), 43500, [M['dire_head']], c[0], c[1],
                      ['', 'The dire wolf crouches, watching %s.'], 'A black dire wolf, as tall at the shoulder as a man at the hip. Its growl is felt more than heard.'))
print('added grey wolves', len(greys), 'dire wolves', len(dires))
alld = [p for p in (pos(t) for t in M['dires']) if p] + [taken[-len(dires) + i] for i in range(len(dires))] if dires else []
for r0, r1 in ((0, 10), (10, 20), (20, 35), (35, 80)):
    print('  dire wolves %d-%d tiles from Greyfang: %d' % (r0, r1, sum(1 for x, y in alld if r0 <= math.hypot(x - GF[0], y - GF[1]) < r1)))
print(W.save())
M['greys'] += greys; M['dires'] += dires
json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
