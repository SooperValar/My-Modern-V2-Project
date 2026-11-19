#!/usr/bin/env python3
"""The Monastery of the Still Hand's monsters, Brother Anselm, items and quests (Nov 19). Run after build_monastery.py,
game stopped:
    place_monastery.py <.dat folder>          (tools/world/arealib.py)  -> made.json

Monsters (group 40), Lieutenant Colonels, bare-handed (tools/sprites/unarmed_robes.py, the Mercenary without his sword):
**Fallen Monks** (melee: a copy of the Barbaric Fighter, 1004; saffron, 64000) and **Fallen Mystics** (casters: the
Spellcaster Lord, 249; grey, 64500) - in the cloister and its rooms, the Training Yard, the Burial Terrace, the gardens,
the terrace and the Library; none on Pilgrims' Stair.
  **Master Kesh** (Colonel; the fighter, black and red, 65000) in the Hall of the Silent Hand, with the Silent Hand Sash;
  four monks train with him.  **the Fallen Abbot** (Lieutenant Colonel; the caster, pale and gold, 45000) in the
  Abbot's Sanctum, with the Abbot's Prayer Beads; three mystics keep vigil.
**Brother Anselm** (friendly; plain undyed robes, 45500) at the foot of Pilgrims' Stair (Cody: closer to town). Quests, Lieutenant Colonel (13)+, no gold:
Abbot's Prayer Beads -> **Monk's Wrap** (+5 Agility, +40 endurance; Cody Nov 17, instead of Karate) 96,000 exp;
Silent Hand Sash -> **Amulet of the Still Mind** (+5 Willpower, +10 Meditate) 96,000 exp.
Item pictures 44556-44559 (tools/sprites/quest_items/monastery.py)."""
import sys, os, random, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1202); random.seed(1202)
T = json.load(open(os.path.join(HERE, 'made_terrain.json')))
FIGHTER, CASTER, BELT_SRC, AMULET_SRC = 1004, 249, 2004, 191
GROUP, SK_MEDIT = 40, 30
steps = {tuple(map(int, k.split(','))): v for k, v in T['steps'].items()}
part = {(a, b): c for a, b, c in T['part']}
inb = lambda p, b: b[0] < p[0] < b[2] and b[1] < p[1] < b[3]
def where(p):
    for n in ('hall', 'sanctum', 'library', 'ruin'):
        if inb(p, T[n]): return n
    if any(inb(p, c) for c in T['cells']): return 'cells'
    if inb(p, (707, 889, 713, 900)): return 'refectory'
    if inb(p, (704, 910, 713, 919)): return 'chapel'
    if inb(p, T['cloister']): return 'courtyard'
    return part.get(p)
def ok(x, y, parts):
    p = (x, y)
    if p not in steps or not A.free(x, y) or where(p) not in parts: return False
    return all((x + dx, y + dy) in steps for dx in (-1, 0, 1) for dy in (-1, 0, 1)) or where(p) in ('cells', 'refectory', 'chapel', 'library', 'north path', 'south path', 'terrace', 'hermit')
BOX = (650, 855, 740, 950)
# ---------------------------------------------------------------- items
BEADS = A.quest_item("Abbot's Prayer Beads", "A loop of dark wooden beads, worn smooth by a lifetime of prayer, a pale tassel at the knot. The Fallen Abbot carried them. Brother Anselm wants them.", 44556)
SASH = A.quest_item('Silent Hand Sash', "A black sash with red stripes at its ends, the mark of the Silent Hand's master. Master Kesh wore it. Brother Anselm wants it.", 44557)
WRAP = A.worn(BELT_SRC, "Monk's Wrap", 'A long sash of saffron cloth, wound round the waist and knotted, blessed by Brother Anselm. It moves with you.',
              44558, rank=13, value=16000, attrib={3: 5}, end=40)
AMULET = A.worn(AMULET_SRC, 'Amulet of the Still Mind', 'A disc of pale jade on a dark cord, from the monastery\'s old treasury. Holding it, the mind goes quiet.',
                44559, rank=13, value=16000, attrib={1: 5}, skill={SK_MEDIT: 10})
# ---------------------------------------------------------------- monsters
MT = ['...', 'Be still, %s. Forever.']
MD = 'A monk of the Still Hand in saffron robes, bare-handed, moving with a terrible calm. Whatever he serves now, it is not the Light.'
YT = ['...', 'The silence will have you, %s.']
YD = 'A grey-robed mystic of the monastery, his eyes gone white. He murmurs a prayer that is no longer a prayer.'
monks, mystics = [], []
def add(kind, x, y):
    if kind == 'm':
        monks.append(A.monster(FIGHTER, 'Fallen Monk', 'Lieutenant Colonel', x, y, text=MT, desc=MD, sprite=64000, group=GROUP, pct=(A.m_pct if monks else None))); A.m_pct = A.last_pct
    else:
        mystics.append(A.monster(CASTER, 'Fallen Mystic', 'Lieutenant Colonel', x, y, text=YT, desc=YD, sprite=64500, group=GROUP, pct=(A.y_pct if mystics else None))); A.y_pct = A.last_pct
PLAN = [  # (parts, how many, every n-th a mystic (0 = none))
    (('courtyard',), 5, 3), (('cells', 'refectory', 'chapel'), 4, 2), (('training yard',), 5, 0), (('north path', 'hermit'), 2, 0),
    (('burial terrace',), 4, 2), (('gardens',), 3, 3), (('terrace',), 3, 3), (('library',), 2, 1), (('ruin',), 1, 0)]
for parts, n, every in PLAN:
    for i, (x, y) in enumerate(A.spots(n, BOX, ok=lambda x, y: ok(x, y, parts), apart=4)):
        add('y' if every and i % every == every - 1 else 'm', x, y)
H, S = T['hall'], T['sanctum']
hc = ((H[0] + H[2]) // 2, (H[1] + H[3]) // 2 + 4); sc = ((S[0] + S[2]) // 2, (S[1] + S[3]) // 2 + 3)
kx, ky = min((p for p in steps if inb(p, H) and A.free(*p)), key=lambda p: abs(p[0] - hc[0]) + abs(p[1] - hc[1]))
KESH = A.monster(FIGHTER, 'Master Kesh', 'Colonel', kx, ky, d=1, items=[SASH], group=GROUP, sprite=65000, nudge=30,
                 text=['Stillness is strength.', 'Show me your stance, %s. It will be your last.'],
                 desc='The master of the Silent Hand, in black with a red sash. He stands utterly still until he strikes, and then he is everywhere at once.')
for x, y in A.spots(4, H, ok=lambda x, y: ok(x, y, ('hall',)) and abs(x - kx) + abs(y - ky) >= 4, apart=4): add('m', x, y)
ax, ay = min((p for p in steps if inb(p, S) and A.free(*p)), key=lambda p: abs(p[0] - sc[0]) + abs(p[1] - sc[1]))
ABBOT = A.monster(CASTER, 'Fallen Abbot', 'Lieutenant Colonel', ax, ay, d=1, items=[BEADS], group=GROUP, sprite=45000, nudge=40,
                  text=['Silence...', 'Kneel, %s. The Still Hand closes.'],
                  desc='The old abbot in pale robes trimmed with gold, his face serene and terrible. Dark wooden prayer beads click through his fingers.')
for x, y in A.spots(3, S, ok=lambda x, y: ok(x, y, ('sanctum',)) and abs(x - ax) + abs(y - ay) >= 4, apart=3): add('y', x, y)
for n, t in (('monk', monks[0]), ('mystic', mystics[0]), ('kesh', KESH), ('abbot', ABBOT)): print('  %-7s %d %s' % (n, t, A.rank_of(t)))
print('  monks', len(monks), 'mystics', len(mystics), 'steps -> kesh', steps.get((kx, ky)), '-> abbot', steps.get((ax, ay)))
# ---------------------------------------------------------------- Brother Anselm (the gate landing) and his quests
lx, ly = 682, 858                                     # Cody: at the foot of Pilgrims' Stair, closer to town (a corner off the way up)
ANSELM = A.person('Brother Anselm', 25, lx, ly, 1,
                  "My brothers up this stair have fallen, %s. Bring me the Fallen Abbot's prayer beads, from the Sanctum at the far south end.",
                  'A gentle old monk in plain undyed wool, his hands folded. His eyes keep straying up the stair behind him.', shout='Help! Help!')
A.W.apply([{'op': 'ctempset', 't': ANSELM, 'fields': {'sprite': 45500}, 'text': [], 'respawn': True}], 'anselm look')
A.quest(ANSELM, BEADS, 96000, give=WRAP, lim=1, rmin=13,
        greet="My brothers up this stair have fallen, %s. Bring me the Fallen Abbot's prayer beads, from the Sanctum at the far south end.")
ANSELM_SASH = A.extra_quest(ANSELM, SASH, 96000, give=AMULET, lim=1, rmin=13)
M = {'items': {'beads': BEADS, 'sash': SASH, 'wrap': WRAP, 'amulet': AMULET}, 'monks': monks, 'mystics': mystics, 'kesh': KESH, 'abbot': ABBOT,
     'anselm': ANSELM, 'quests': {'anselm_beads': ANSELM, 'anselm_sash': ANSELM_SASH}}
A.save(M, HERE); print(M)
