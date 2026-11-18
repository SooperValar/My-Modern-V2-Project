#!/usr/bin/env python3
"""The Golem Foundry's monsters, items and quests (Nov 17). Run after build_foundry.py, game stopped:

    place_foundry.py <.dat folder>          (tools/world/arealib.py)  -> made.json

Monsters (group 37), all the game's Golem (template 323) recoloured (tools/sprites/recolor_creature.py):
  Iron Golems (Major; dark forged iron, 55000) in the yard and the hall; the Iron Golem Forgemaster (a strong Major; iron
  glowing hot, 56000) in his forge with the Foundry Heart; the Brass Colossus (Lieutenant Colonel; brass, 57000) in the
  Casting Pit with the Colossus Core. Every golem carries a Golem Core (Watch Sergeant Brann's bounty: 13,000 exp + 65G).
Quests (Hagar the smith, Stonehold): Foundry Heart -> Forgefire Ring (+4 Strength, +8 Enhance) 71,000 exp; Colossus Core
-> Belt of the Colossus (+50 hitpoints, +6 armor) 100,000 exp. Item pictures 44542-44546 (tools/sprites/quest_items/golem_foundry.py)."""
import sys, os, random, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1141)
T = json.load(open(os.path.join(HERE, 'made_terrain.json')))
GOLEM, GROUP, SK_ENHANCE = 323, 37, 18
HALL, FORGE, PIT = T['hall'], T['forge'], T['pit_centre']
# ---------------------------------------------------------------- items
CORE = A.quest_item('Golem Core', 'The glowing heart-stone that drives a foundry golem. The Stonehold Watch pays for every one.', 44542)
HEART = A.quest_item('Foundry Heart', "A fist-sized lump of iron that never cools, glowing like a coal. The Forgemaster's own core. Hagar of Stonehold wants it.", 44543)
CCORE = A.quest_item('Colossus Core', 'The great brass-and-gold core of the Brass Colossus, still warm and humming. Hagar of Stonehold wants it.', 44544)
RING = A.worn(338, 'Forgefire Ring', 'An iron band set with a stone that glows like an ember, forged by Hagar from the Foundry Heart. Steel bites deeper in the hand that wears it.',
              44545, rank=12, value=14000, attrib={4: 4}, skill={SK_ENHANCE: 8}, clear=(1 << 9) | (1 << 10), driver=0, data=[0] * 10)
BELT = A.worn(2004, 'Belt of the Colossus', "A wide belt of brass plates on dark leather, made by Hagar from the Colossus Core's housing. It sits heavy and sure.",
              44546, rank=12, value=18000, hp=50, armor=6)
# ---------------------------------------------------------------- where
inhall = lambda x, y: HALL[0] < x < HALL[2] and HALL[1] < y < HALL[3]
inforge = lambda x, y: FORGE[0] - 1 <= x <= FORGE[2] + 1 and FORGE[1] - 1 <= y <= FORGE[3] + 1
yard_ok = lambda x, y: y >= HALL[3] + 2 and A.tile(x, y)[0] not in PATH and not any(A.floor(x + dx, y + dy) in PATH for dx in (-1, 0, 1) for dy in (-1, 0, 1)) and y <= 762
hall_ok = lambda x, y: inhall(x, y) and x >= 670 and not inforge(x, y) and abs(y - HALL[3]) > 3 and not (A.tile(x, y)[7] & 1)   # x < 670: cut off behind the furnace channel
GT = ['Clank.', 'INTRUDER. %s. REMOVE.']
GD = 'A golem of dark forged iron, its joints glowing faintly. It still tends the forges - and breaks whatever comes in.'
golems = []
for x, y in A.spots(10, (652, HALL[3] + 2, 738, 762), ok=yard_ok, apart=5):
    golems.append(A.monster(GOLEM, 'Iron Golem', 'Major', x, y, items=[CORE], text=GT, desc=GD, sprite=55000, group=GROUP, pct=(A.last_pct if golems else None)))
for x, y in A.spots(12, (HALL[0] + 1, HALL[1] + 1, HALL[2] - 1, HALL[3] - 1), ok=hall_ok, apart=5):
    golems.append(A.monster(GOLEM, 'Iron Golem', 'Major', x, y, items=[CORE], text=GT, desc=GD, sprite=55000, group=GROUP, pct=A.last_pct))
FM = A.monster(GOLEM, 'the Iron Golem Forgemaster', 'Major', 702, 701, d=2, items=[HEART, CORE], group=GROUP, sprite=56000, nudge=40,
               text=['The work goes on.', 'You are not on the roster, %s. You will be melted down.'],
               desc='The master of the foundry: an iron golem glowing red-hot at every seam, a hammer for a hand. Something burns in its chest.')
COL = A.monster(GOLEM, 'the Brass Colossus', 'Lieutenant Colonel', PIT[0], PIT[1], d=2, items=[CCORE, CORE], group=GROUP, sprite=57000, nudge=30,
                text=['Cast. Cooled. Complete.', 'YOU WILL BE CAST INTO THE MOULD, %s.'],
                desc='The greatest work of the foundry, cast whole in brass in the pit where it still stands. A great core hums behind its chest-plate.')
for n, t in (('golem', golems[0]), ('forgemaster', FM), ('colossus', COL)): print('  %-11s %d %s' % (n, t, A.rank_of(t)))
# ---------------------------------------------------------------- quests (Stonehold, by name)
HAGAR, BRANN = A.by_name('Hagar'), A.by_name('Watch Sergeant Brann')
A.quest(HAGAR, HEART, 71000, give=RING, lim=1, rmin=12,
        greet="Mind the sparks, %s. West of the gate the old Foundry still roars, and its golems have turned on us. Its Forgemaster carries a Foundry Heart - bring it to me and I'll forge you a ring with fire in it. And if you're truly brave: the Brass Colossus in the casting pit has a core I could make a fine belt from.")
HAGAR_CORE = A.extra_quest(HAGAR, CCORE, 100000, give=BELT, lim=1, rmin=12)
A.quest(BRANN, CORE, 13000, gold=6500, lim=0, rmin=12,                              # bounty gold = 1/200 of the exp (Cody, Nov 17)
        greet='The Watch pays for what it does not have to fight itself, %s. Golem Cores from the Foundry west of town - 65 gold apiece, as many as you bring. Gargoyle horns, when the Spires are scouted.')
M = {'items': {'core': CORE, 'heart': HEART, 'colossus_core': CCORE, 'ring': RING, 'belt': BELT}, 'golems': golems, 'forgemaster': FM, 'colossus': COL,
     'quests': {'hagar_heart': HAGAR, 'hagar_core': HAGAR_CORE, 'brann_cores': BRANN}, 'pct': A.last_pct}
A.save(M, HERE); print(M)
