#!/usr/bin/env python3
"""Nov 16: the Rat-Catcher's cellar - the small room in Underground I (886-891, 24-30) where the hole in the quest giver's
house (528,465, Aston, +360 -440) lands (888,25): two Young Ratlings (about Lance Corporal) and a Ratling Broodmother
(about Corporal), made from the Ratling (181): its attributes / skills / HP scaled down (65% / 80%: a Lance Corporal Thief has 11 where
the Ratling has 16), their points (exp, rank shown) set to 3,000 and 11,000.
    place_ratlings.py <.dat folder>      (the game stopped: stop-send; then update-world, reload-editor)"""
import sys, os, json, struct, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]
def rank(pts): return me.RANKS[me.points2rank(pts)]
def stats(src, pct, pts):
    f = me.tpl_read(W.tchar, src * me.CHAR_SIZE, me.CT_FIELDS)
    a = list(f['attrib']); hp = list(f['hp']); en = list(f['end']); mn = list(f['mana']); sk = list(f['skill'])
    for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
    hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
    for i in range(50): sk[i * 6] = min(255, round(sk[i * 6] * pct / 100))
    return {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': sk, 'points_tot': pts}
def ratling(name, pct, pts, x, y, desc, text):
    t = made({'op': 'ctempnew', 'from': 181, 'name': name})
    f = stats(181, pct, pts); b = me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)
    dd = list(b['data'])
    for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0     # no patrol, doors, lights of the original
    f.update({'data': dd, 'description': desc})
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': text, 'respawn': False}], name)
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': 4}], 'place')
    for m in msgs: print('  !', m, name, x, y)
    print(name, t, 'at', x, y, rank(f['points_tot']))
    return t
YOUNG = 'A young ratling, all teeth and twitching whiskers, not yet grown into its mangy fur.'
young = [ratling('Young Ratling', 65, 3000, x, y, YOUNG, ['', 'The young ratling squeaks at %s.']) for x, y in ((887, 28), (890, 25))]
mother = ratling('Ratling Broodmother', 80, 11000, 889, 29, 'A fat, scarred ratling sow, guarding her litter. Her long bald tail twitches angrily.',
                 ['', 'The Ratling Broodmother hisses at %s and bares yellow teeth.'])
print(W.save())
json.dump({'young': young, 'broodmother': mother}, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
