#!/usr/bin/env python3
"""The Lizard Hatcheries' monsters, items and quests (Nov 17). Run after build_hatcheries.py, game stopped:

    place_hatcheries.py <.dat folder>          (tools/world/arealib.py)  -> made.json

Monsters (group 36; lizards aren't undead): Lizard Knights (406, Captain) out on the marsh and in the Hatchery, Lizard
Archmages (413 scaled down to Captain) in the caves, **the Broodmother** (1154 scaled to Major, dark red look 53000) in her
Nest in the Hatchery with the Broodmother's Crown, the **Hatchery Archmage** (413, a strong Captain) in the Archmage's
Grotto with the Archmage's Phial (Cody, Nov 17: the Broodmother rules the big cave, the Archmage the small one). Every
lizard carries a Lizard Head. Quests: Aldous (Crown -> Scaled Belt), Rook (Phial -> 2 Elixirs of the Good Moon), Bounty
Master Corwin (Lizard Heads, and the Lizard Eggs from the nests: build_hatcheries.py). Item pictures 44537-44541
(tools/sprites/quest_items/lizard_hatcheries.py)."""
import sys, os, random, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1124)
T = json.load(open(os.path.join(HERE, 'made_terrain.json'))); EGG_ITEM = T['egg_item']
GROUP, BROOD_LOOK = 36, 53000
# ---------------------------------------------------------------- items
HEAD = A.quest_item('Lizard Head', 'The scaly head of a hatchery lizard. The Fenwatch Bounty Office pays for these.', 44541)
CROWN = A.quest_item("Broodmother's Crown", 'A crown of dark bronze set with garnets, taken from the Broodmother of the hatcheries. Aldous of Fenwatch wants it.', 44537)
PHIAL = A.quest_item("Archmage's Phial", "A phial of glowing green liquor from the Hatchery Archmage's grotto. Rook of Fenwatch wants it.", 44538)
BELT = A.worn(2004, 'Scaled Belt', 'A belt of overlapping lizard scales with a bronze buckle, made by the reeve of Fenwatch from the Broodmother\'s hoard.',
              44539, rank=11, value=9000, attrib={4: 3}, armor=4)
ELIXIR = A.item(2015, 'Elixir of the Good Moon', 'A pale, moon-silver draught. For ten minutes a caster\'s spells are stronger, as under a full moon, and a Bad Moon does not weaken them.',
                sprite=[44540, 0], duration=10800, armor=[0, 0], data=[0, 65001] + [0] * 8, value=1500)
# ---------------------------------------------------------------- where (from the map: caves are indoor cave floor 116)
X0, X1, Y0, Y1 = 495, 595, 757, 860
def cave(x, y): t = A.tile(x, y); return t[0] == 116 and bool(t[7] & 4)
def near_road(x, y, r=3): return any(A.floor(x + dx, y + dy) in PATH for dx in range(-r, r + 1) for dy in range(-r, r + 1))
OUT = lambda x, y: not cave(x, y) and x >= 499 and not near_road(x, y) and not (A.tile(x, y)[7] & 1)
NEST_ROOM, GROTTO = (521, 767, 5), (582, 842, 8)
HATCH_CAVE = lambda x, y: cave(x, y) and x <= 572 and y <= 800
GROTTO_CAVE = lambda x, y: cave(x, y) and x >= 565 and y >= 830
not_nest = lambda x, y: abs(x - NEST_ROOM[0]) + abs(y - NEST_ROOM[1]) > 4
# ---------------------------------------------------------------- monsters
KT = ['The eggs are safe.', 'Intruder! Hsss - for the brood, %s!']; KD = 'A lizard knight of the hatcheries in scale armour, guarding the brood.'
MT = ['Feed it to the hatchlings.', 'The brood sees you, %s. Burn!']; MD = 'A robed lizard mage, its scales painted with old glyphs.'
PCT = {}
def mon(key, src, name, rank, x, y, text, desc, sprite=None, items=(HEAD,), d=None):
    t = A.monster(src, name, rank, x, y, d=d, items=list(items), text=text, desc=desc, sprite=sprite, group=GROUP, pct=PCT.get(key)); PCT[key] = A.last_pct; return t
knights, mages = [], []
for x, y in A.spots(12, (X0, Y0, X1, Y1), ok=OUT, apart=6): knights.append(mon('knight', 406, 'Lizard Knight', 'Captain', x, y, KT, KD))
for x, y in A.spots(8, (505, 757, 572, 800), ok=lambda x, y: HATCH_CAVE(x, y) and not_nest(x, y), apart=4): knights.append(mon('knight', 406, 'Lizard Knight', 'Captain', x, y, KT, KD))
for x, y in A.spots(5, (505, 757, 572, 800), ok=lambda x, y: HATCH_CAVE(x, y) and not_nest(x, y), apart=4): mages.append(mon('mage', 413, 'Lizard Archmage', 'Captain', x, y, MT, MD))
for x, y in A.spots(3, (565, 830, 595, 860), ok=lambda x, y: GROTTO_CAVE(x, y) and abs(x - 579) + abs(y - 840) > 3, apart=3): mages.append(mon('mage', 413, 'Lizard Archmage', 'Captain', x, y, MT, MD))
BROOD = A.monster(1154, 'the Broodmother', 'Major', NEST_ROOM[0], NEST_ROOM[1], d=4, items=[CROWN, HEAD], sprite=BROOD_LOOK, group=GROUP,
                  text=['My children will feast.', 'You dare come into my nest, %s? Hsssss!'],
                  desc='The mother of the hatcheries, huge and dark red, a crown of bronze and garnets on her scaled brow.')
ARCHMAGE = A.monster(413, 'Hatchery Archmage', 'Captain', 579, 840, d=4, items=[PHIAL, HEAD], group=GROUP, nudge=40,
                     text=['Another for the phial.', 'Ssso, %s seeks my brew. Come, then.'],
                     desc='An old lizard archmage hunched over its brews in the grotto, a phial of green light at its belt.')
for n, t in (('knight', knights[0]), ('mage', mages[0]), ('broodmother', BROOD), ('archmage', ARCHMAGE), ('hatchling', T['hatchling'])): print('  %-11s %d %s' % (n, t, A.rank_of(t)))
# ---------------------------------------------------------------- quests (Fenwatch, by name)
ALDOUS, ROOK, CORWIN = A.by_name('Aldous'), A.by_name('Rook'), A.by_name('Bounty Master Corwin')
ALDOUS_CROWN = A.extra_quest(ALDOUS, CROWN, 52000, give=BELT, lim=1, rmin=11)
A.quest(ROOK, PHIAL, 52000, give=ELIXIR, n=2, lim=1, rmin=11,
        greet="Hm? Ah, %s. South of the gate, past the marsh, the lizards breed in the old caves - and an archmage of theirs brews something wonderful in a grotto there. Bring me its phial and I'll make you two Elixirs of the Good Moon from it.")
CORWIN_HEAD = A.extra_quest(CORWIN, HEAD, 5200, gold=26000, lim=0, rmin=11)
CORWIN_EGG = A.extra_quest(CORWIN, EGG_ITEM, 2600, gold=13000, lim=0, rmin=11)
A.W.apply([{'op': 'ctempset', 't': CORWIN, 'fields': {}, 'respawn': True, 'text': [None, None,
           "Fenwatch pays for what crawls out of the marsh, %s: drowned sailors' and bog-men's heads, and from the hatcheries south of town, lizard heads - and their eggs, before they hatch. As many as you bring."]}], 'Corwin greets')
A.W.apply([{'op': 'ctempset', 't': ALDOUS, 'fields': {}, 'respawn': True, 'text': [None, None,
           "Well met, %s. Two things trouble Fenwatch: the old king in the Barrow Hills to the north - bring me Ulfgar's torc - and the Broodmother in the hatcheries to the south. Bring me her crown and you'll have a belt fit for it."]}], 'Aldous greets')
M = {'items': {'head': HEAD, 'crown': CROWN, 'phial': PHIAL, 'belt': BELT, 'elixir': ELIXIR, 'egg': EGG_ITEM}, 'knights': knights, 'mages': mages,
     'broodmother': BROOD, 'archmage': ARCHMAGE, 'hatchling': T['hatchling'], 'quests': {'aldous_crown': ALDOUS_CROWN, 'rook': ROOK, 'corwin_head': CORWIN_HEAD, 'corwin_egg': CORWIN_EGG}, 'pct': PCT}
A.save(M, HERE); print(M['items'], M['quests'], len(knights), 'knights', len(mages), 'mages')
