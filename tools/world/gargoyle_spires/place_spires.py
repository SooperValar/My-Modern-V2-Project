#!/usr/bin/env python3
"""The Gargoyle Spires' monsters, items and quests (Nov 19). Run after build_spires.py, game stopped:

    place_spires.py <.dat folder>          (tools/world/arealib.py)  -> made.json

Monsters (group 39), Brigadier Generals, every one with a Gargoyle Horn (Watch Sergeant Brann's bounty): Gargoyle Knights
(the game's Gargoyle Knight, 965, in frost-dusted granite: 62000) and Gargoyle Mages (967, dark slate with a pale blue glow:
62500) on the islands and some of the ridges and bridges, fewer near the gate, more deeper in.
  the Gargoyle Bellkeeper (a Brigadier General Gargoyle Mage in verdigris bronze, 63000) in the ruined tower of the Bell
  Spire (north end) beside the fallen bell, with the Spire Bell Clapper; two Knights and a Mage guard the island.
  Shrike, the Gargoyle Matriarch (Major General; the Knight 1.3x in storm-cloud purple-grey, 63500) on Shrike's Eyrie
  (south end), with Shrike's Eye; four Knights guard her.
Quests (Commander Rhea, Stonehold), Brigadier General (15)+, no gold: Spire Bell Clapper -> Warden's Girdle (+6 Bravery,
+70 hitpoints) 160,000 exp; Shrike's Eye -> Shrike's Eye Amulet (+6 Agility, +12 Perception) 230,000 exp.
Brann: Gargoyle Horns, any number, 16,000 exp + 80G each (a Brigadier General head: 10 = one standard quest; gold 1/200).
Item pictures 44551-44555 and the bell 38463 (tools/sprites/quest_items/gargoyle_spires.py)."""
import sys, os, random, json, math
from collections import deque
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1191); random.seed(1191); R = random.Random(1191)
T = json.load(open(os.path.join(HERE, 'made_terrain.json')))
KNIGHT, MAGE, BELT_SRC, AMULET_SRC = 965, 967, 2004, 191
GROUP, SK_PERC = 39, 9
BELL_OBJ = 38463
land = {(a, b): c for a, b, c in T['land']}; used = {tuple(p) for p in T['used']}; IS = T['islands']
GATE0 = (765, 846)
walk = {p for p in land if p not in used}
D = {GATE0: 0}; q = deque([GATE0])                                  # steps from the gate (straight steps)
while q:
    p = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (p[0] + dx, p[1] + dy)
        if n in walk and n not in D: D[n] = D[p] + 1; q.append(n)
FAR = max(D.values())
# ---------------------------------------------------------------- items
HORN = A.quest_item('Gargoyle Horn', 'A curved horn of frost-grey stone, broken from a gargoyle of the Spires. The Stonehold Watch pays for every one.', 44551)
CLAPPER = A.quest_item('Spire Bell Clapper', 'The great clapper of the Spire Bell: an iron rod and a bronze ball green with age. The Gargoyle Bellkeeper kept it. Commander Rhea of Stonehold wants it.', 44552)
EYE = A.quest_item("Shrike's Eye", "A red stone eye with a black slit, still warm and still watching. Shrike, the Gargoyle Matriarch, carried it. Commander Rhea of Stonehold wants it.", 44553)
GIRDLE = A.worn(BELT_SRC, "Warden's Girdle", 'A broad girdle of dark leather set with steel studs, the old wardens\' badge of the Spires on its buckle. Rhea gives it to those who silenced the bell.',
                44554, rank=15, value=26000, attrib={0: 6}, hp=70)
AMULET = A.worn(AMULET_SRC, "Shrike's Eye Amulet", "Shrike's red stone eye in a silver setting, made for Rhea by Hagar. Whoever wears it is quick, and nothing slips past them.",
                44555, rank=15, value=26000, attrib={3: 6}, skill={SK_PERC: 12})
# ---------------------------------------------------------------- where
def ok(x, y, parts=None, edge=True):
    p = (x, y)
    if p not in D or not A.free(x, y): return False
    if parts and land.get(p) not in parts: return False
    if edge and not all((x + dx, y + dy) in walk for dx in (-1, 0, 1) for dy in (-1, 0, 1)) and land.get(p) != 'way': return False
    return True
BOX = (742, 845, 830, 940)
KT = ['...', 'Ssstone remembers, %s!']
KD = 'A gargoyle of grey granite dusted with frost. It perches on the spires so still that it looks carved there - until it moves.'
MT = ['...', 'The wind carries your name, %s. It ends here.']
MD = 'A gargoyle of dark slate, a pale blue light moving behind its eyes. Cold sparks crawl over its claws.'
knights, mages = [], []
def add(kind, x, y):
    if kind == 'k':
        knights.append(A.monster(KNIGHT, 'Gargoyle Knight', 'Brigadier General', x, y, items=[HORN], text=KT, desc=KD, sprite=62000, group=GROUP,
                                 pct=(A.k_pct if knights else None))); A.k_pct = A.last_pct
    else:
        mages.append(A.monster(MAGE, 'Gargoyle Mage', 'Brigadier General', x, y, items=[HORN], text=MT, desc=MD, sprite=62500, group=GROUP,
                               pct=(A.m_pct if mages else None))); A.m_pct = A.last_pct
skip = ('bell', 'eyrie')
# the islands and ways: none within 12 steps of the gate; outer half 14, inner half 20; 2 knights to 1 mage
k = 0
for n, lo, hi in ((14, 12, FAR * 0.45), (20, FAR * 0.45, FAR)):
    for x, y in A.spots(n, BOX, ok=lambda x, y: ok(x, y) and land[(x, y)] not in skip and lo <= D[(x, y)] < hi, apart=5):
        add('m' if k % 3 == 2 else 'k', x, y); k += 1
# the Bell Spire: the Bellkeeper by the fallen bell, inside the ruined tower
bc = tuple(IS['bell'][0]); bell_t = [p for p in walk if land[p] == 'bell']
bx, by = min((p for p in bell_t if ok(*p, parts=('bell',), edge=False)), key=lambda p: abs(p[0] - bc[0]) + abs(p[1] - bc[1]))
obj = min((p for p in bell_t if ok(*p, parts=('bell',)) and 2 <= abs(p[0] - bx) + abs(p[1] - by) <= 3), key=lambda p: abs(p[0] - bc[0] - 1) + abs(p[1] - bc[1] - 1))
A.op(op='object', x=obj[0], y=obj[1], s=BELL_OBJ, block=3); A.run('the fallen bell'); A.used.add(obj)
KEEPER = A.monster(MAGE, 'Gargoyle Bellkeeper', 'Brigadier General', bx, by, d=3, items=[CLAPPER, HORN], group=GROUP, sprite=63000, nudge=40,
                   text=['The bell will ring again.', 'I TOLL FOR YOU, %s!'],
                   desc='An old gargoyle gone green as bronze, its wings folded like a bell\'s lip. It hums one low note, over and over. An iron clapper hangs from its belt.')
for i, (x, y) in enumerate(A.spots(3, (bc[0] - 7, bc[1] - 7, bc[0] + 7, bc[1] + 7), ok=lambda x, y: ok(x, y, parts=('bell',)) and abs(x - bx) + abs(y - by) >= 3, apart=3)):
    add('m' if i == 2 else 'k', x, y)
# Shrike's Eyrie: Shrike at the middle, four knights
ec = tuple(IS['eyrie'][0]); ey_t = [p for p in walk if land[p] == 'eyrie']
sx, sy = min((p for p in ey_t if ok(*p, parts=('eyrie',))), key=lambda p: abs(p[0] - ec[0]) + abs(p[1] - ec[1]))
SHRIKE = A.monster(KNIGHT, 'Shrike', 'Major General', sx, sy, d=2, items=[EYE, HORN], group=GROUP, sprite=63500, nudge=30,
                   text=['My brood will feast.', 'I HAVE WATCHED YOU CLIMB, %s. NOW FALL.'],
                   desc='Shrike, the Gargoyle Matriarch: larger than any of her brood, storm-dark, with one burning red eye. The other socket is empty - the eye she plucked out is set in her brow.')
for x, y in A.spots(4, (ec[0] - 8, ec[1] - 8, ec[0] + 8, ec[1] + 8), ok=lambda x, y: ok(x, y, parts=('eyrie',)) and abs(x - sx) + abs(y - sy) >= 4, apart=3):
    add('k', x, y)
for n, t in (('knight', knights[0]), ('mage', mages[0]), ('bellkeeper', KEEPER), ('shrike', SHRIKE)): print('  %-10s %d %s' % (n, t, A.rank_of(t)))
print('  knights', len(knights), 'mages', len(mages), 'steps gate -> bellkeeper', D[(bx, by)], '-> shrike', D[(sx, sy)])
# ---------------------------------------------------------------- quests (Stonehold, by name)
RHEA, BRANN = A.by_name('Commander Rhea'), A.by_name('Watch Sergeant Brann')
A.quest(RHEA, CLAPPER, 160000, give=GIRDLE, lim=1, rmin=15,
        greet="Gargoyles hold the Spires east of Bastion Road, %s. Their Bellkeeper, at the north end, has the bell's clapper. Bring it to me.")
RHEA_EYE = A.extra_quest(RHEA, EYE, 230000, give=AMULET, lim=1, rmin=15)
BRANN_HORNS = A.extra_quest(BRANN, HORN, 16000, gold=8000, lim=0, rmin=15)        # bounty gold = 1/200 of the exp
greet = 'The Watch pays for what it does not have to fight, %s: Golem Cores from the Foundry, 65 gold each; Gargoyle Horns from the Spires, 80.'
assert len(greet) <= 150, len(greet)
A.W.apply([{'op': 'ctempset', 't': BRANN, 'fields': {}, 'text': [None, None, greet], 'respawn': True}], 'brann greeting')
M = {'items': {'horn': HORN, 'clapper': CLAPPER, 'eye': EYE, 'girdle': GIRDLE, 'amulet': AMULET}, 'knights': knights, 'mages': mages,
     'bellkeeper': KEEPER, 'shrike': SHRIKE, 'bell': list(obj),
     'quests': {'rhea_clapper': RHEA, 'rhea_eye': RHEA_EYE, 'brann_horns': BRANN_HORNS}}
A.save(M, HERE); print(M)
